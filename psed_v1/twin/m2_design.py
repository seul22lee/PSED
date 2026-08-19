"""
m2_design.py — knowledge-guided M2 design layer.
-------------------------------------------------
Sits ABOVE the validated scalar inverse solver (inverse_solver.solve_target_dose),
which stays the only physics-inversion backend. Nothing here re-derives a root.

    underspecified request
        -> constraint & prior resolution      (resolve_context)
        -> completed design context           (DesignContext)
        -> digital-twin feasibility           (assess_feasibility)
        -> inverse candidate generation       (generate_candidates)   <- calls the solver
        -> candidate ranking                  (rank_candidates)
        -> robustness analysis                (analyse_robustness)
        -> provenance-rich HTML report        (render_report)

The point of the layer is that a real request ("deposit Al2O3 60 µm into the
channel") does not name a pressure-to-pulse-time ratio, operating bounds, or a
model configuration — yet the 1-D inversion needs all of them. Every value the
layer has to supply is therefore a `Prior`: it carries where it came from, how much
that source is worth, and whether a caller may override it. A number without that
context is exactly how the old M2 came to report a hard-coded 100 Pa as if it were
literature.

NAMING — two different quantities, deliberately never sharing a name:
  · `effective_dose`  = pA · pulse_time  [Pa·s]   the recipe-level exposure this
        layer and the solver invert for.
  · `D` inside channel_model.approx()    an internal TRANSPORT coefficient with
        entirely different units. It is never called `D` here.

The ratio prior is currently a FALLBACK. The KB resolves no precursor partial
pressure for the M2 query, so pA0 is None, r_star is None, and the operating-family
default is what actually runs. It is labelled `fallback`, given low confidence, and
must not be described as literature-derived.
"""
from dataclasses import dataclass, field, asdict
import html
import json
import math
from pathlib import Path

import numpy as np

from twin import inverse_solver
from twin.channel_model import channelModel
from twin import kb_bridge
from twin import m2_chemistry as chem
from twin import chemistry_params

HERE = Path(__file__).parent

# Confidence is ordinal, not a probability: it ranks how much a resolved value is
# worth when two candidates otherwise tie, and it is shown in the report.
CONFIDENCE = {"user": 1.0, "kb": 0.8, "model_supported": 0.4, "fallback": 0.2, "unresolved": 0.0}
SOURCE_ORDER = ("user", "kb", "model_supported", "fallback", "unresolved")


@dataclass
class Prior:
    """One resolved input to the design problem, with its origin."""
    name: str
    value: object = None
    unit: str = None
    source: str = "unresolved"          # user | kb | model_supported | fallback | unresolved
    confidence: float = 0.0
    evidence: str = None
    overridable: bool = True

    @classmethod
    def make(cls, name, value, unit, source, evidence=None, overridable=True):
        return cls(name=name, value=value, unit=unit, source=source,
                   confidence=CONFIDENCE.get(source, 0.0), evidence=evidence,
                   overridable=overridable)

    def to_dict(self):
        return asdict(self)


@dataclass
class DesignRequest:
    """What a user actually asks for — deliberately underspecified.

    `material` is the DEPOSITED FILM and does NOT determine the chemistry: Al2O3
    alone appears under TMA/H2O, DEZ/H2O and a plasma system in this corpus.
    `precursor` / `co_reactant` name the process chemistry when the caller knows it;
    neither is ever inferred from the film. `allow_chemistry_fallback` is the
    explicit opt-in required before a design proceeds on an unresolved chemistry —
    off by default, so a material-only request cannot silently acquire a
    chemistry-flavoured ratio."""
    material: str = "Al2O3"                       # deposited film
    target_pd: float = None                       # m
    precursor: str = None                         # metal-bearing / film-forming reactant
    co_reactant: str = None                       # oxidant / nitridant / reductant / plasma
    temperature: float = None
    reactor_type: str = None
    allow_chemistry_fallback: bool = False
    allow_cross_chemistry_ranking: bool = False
    geometry_class: str = None                    # feature geometry (model-validity context)
    secondary_objective: str = None               # external preference that may select ONE point
    constraints: dict = field(default_factory=dict)   # user overrides, e.g. {"ratio": 500.0}

    def to_dict(self):
        return asdict(self)


@dataclass
class DesignContext:
    """The completed problem: everything the inversion needs, each with provenance."""
    request: DesignRequest = None
    priors: dict = field(default_factory=dict)     # name -> Prior
    warnings: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    chemistry: object = None                       # ProcessChemistryContext
    chemistry_resolution_status: str = "material_only"
    chemistry_alternatives: list = field(default_factory=list)
    chemistry_priors: dict = field(default_factory=dict)   # name -> ScopedPrior
    ratio_status: str = None

    def value(self, name, default=None):
        p = self.priors.get(name)
        return default if p is None or p.value is None else p.value

    def to_dict(self):
        return {"request": self.request.to_dict() if self.request else None,
                "priors": {k: v.to_dict() for k, v in self.priors.items()},
                "warnings": self.warnings, "unresolved": self.unresolved}


@dataclass
class Candidate:
    """One operating family, inverted. `solution` is the solver's DoseSolution.

    TWO provenance axes, deliberately never merged into one label:

      family_definition_source  where the ARCHETYPE came from (always a
            model-supported operating archetype — a way of spending exposure).
      ratio_evidence_source     what supports the NUMBER actually used. This is the
            one that must never read `kb` when nothing was retrieved.

    Collapsing them is what previously let a fallback 1000 Pa/s appear as
    `model_supported` in the candidate table while the context called it `fallback`."""
    family: str
    ratio: float
    family_definition_source: str = "model_supported_archetype"
    ratio_evidence_source: str = "unresolved"
    ratio_evidence_confidence: float = 0.0
    ratio_evidence: str = None
    base_ratio_source: str = None
    ratio_multiplier: float = 1.0
    solution: object = None
    scores: dict = field(default_factory=dict)
    robustness: dict = field(default_factory=dict)
    total_score: float = 0.0
    rejected: str = None

    @property
    def feasible(self):
        return bool(self.solution is not None and self.solution.feasible)

    def to_dict(self):
        d = {k: v for k, v in asdict(self).items() if k != "solution"}
        d["solution"] = self.solution.to_dict() if self.solution else None
        return d


# --- operating families -------------------------------------------------------
# A "family" is a way of spending the same exposure: the SAME effective_dose can be
# delivered as a short high-pressure pulse or a long low-pressure one. Each family
# fixes the ratio r = pA/t_p, which turns the 2-D (pA, t_p) problem into the 1-D
# inversion the solver already handles.
#
# Families are MULTIPLIERS of the resolved reference ratio, not free-standing numbers.
# That keeps the dependency honest: if the reference ratio is a fallback, so is every
# family ratio derived from it — none of them acquires independent support by being
# multiplied by ten. The archetype is model-supported; the NUMBER is not.
OPERATING_FAMILIES = (
    ("long_low_pressure", 0.1, "low pA, long pulse — gentle, precursor-lean"),
    ("balanced", 1.0, "the resolved reference ratio itself"),
    ("short_high_pressure", 10.0, "high pA, short pulse — throughput-oriented"),
)

# A derived ratio inherits its base evidence but adds an unevidenced scaling, so it can
# never be MORE credible than the base it came from.
DERIVED_CONFIDENCE_FACTOR = 0.5

RANKING_PROFILE = "balanced_default"
RANKING_WEIGHTS = {"accuracy": 0.15, "margin": 0.25, "robustness": 0.25,
                   "throughput": 0.15, "confidence": 0.20}
# Explicitly opt-in-only stand-in ratio. It is NOT a chemistry prior: it exists so a
# material-only demonstration can still run, and it is always reported as `fallback`.
RATIO_FALLBACK = 1000.0
NEAR_TIE_THRESHOLD = 0.05          # score gap below which no decisive winner is claimed

PA_BOUNDS_DEFAULT, TP_BOUNDS_DEFAULT = (1.0, 200.0), (0.01, 5.0)


_EXPERIMENTS_FN = None          # tests inject synthetic records here


def _experiments():
    """M2's literature: the PRODUCTION semantic corpus (declared 41-paper
    manifest; canonical chemistry; per-condition evidence classes), through
    twin.semantic_evidence. Tests inject synthetic records via _EXPERIMENTS_FN."""
    if _EXPERIMENTS_FN is not None:
        return _EXPERIMENTS_FN()
    try:
        from twin import semantic_evidence as SE
        return SE.case_records()
    except Exception:
        return []


def resolve_context(request, warm_start_fn=None, experiments_fn=None):
    """Underspecified request -> completed design context.

    Resolution order per field: explicit user constraint > retrieved KB evidence >
    model-supported default > fallback. Every outcome is recorded as a Prior, so the
    report can state which inputs were actually grounded."""
    ctx = DesignContext(request=request)
    c = request.constraints or {}

    if request.target_pd is None:
        ctx.unresolved.append("target_pd")
        ctx.warnings.append("no target penetration depth given — nothing to invert for")
    ctx.priors["target_pd"] = Prior.make(
        "target_pd", request.target_pd, "m", "user" if request.target_pd else "unresolved",
        evidence="requested by the caller" if request.target_pd else None, overridable=False)
    ctx.priors["material"] = Prior.make("material", request.material, None, "user",
                                        evidence="requested by the caller")

    # --- process chemistry (BEFORE any chemistry-dependent prior) --------------
    # The deposited material is not the chemistry. Resolve which precursor system we
    # are actually designing for first; every chemistry-dependent prior below is then
    # scoped to it, and refused when the scope cannot be established.
    exps = (experiments_fn or _experiments)()
    chem_ctx, chem_status, alts, chem_notes = chem.resolve_chemistry(
        exps, request.material, precursor=request.precursor,
        co_reactant=request.co_reactant, temperature=request.temperature,
        reactor_type=request.reactor_type)
    ctx.chemistry, ctx.chemistry_resolution_status = chem_ctx, chem_status
    ctx.chemistry_alternatives = alts
    ctx.warnings.extend(chem_notes)
    ctx.priors["deposited_material"] = Prior.make(
        "deposited_material", request.material, None, "user",
        evidence="the film requested; does NOT determine the precursor chemistry")
    for nm, val, lbl in (("precursor", chem_ctx.precursor_identity, "precursor"),
                         ("co_reactant", chem_ctx.co_reactant_identity, "co-reactant")):
        ctx.priors[nm] = Prior.make(
            nm, val, None, chem_ctx.chemistry_source if val else "unresolved",
            evidence=(chem_ctx.chemistry_evidence if val else
                      f"{lbl} not resolved — the deposited material does not imply it"))
        if not val:
            ctx.unresolved.append(nm)

    # chemistry-scoped operating priors
    # Typed precursor partial pressure by precedence (precursor_partial_pressure >
    # reactant_A_partial_pressure > partial_pressure). A chamber/working/base/generic
    # pressure is NOT queried, so it can never be mistaken for a precursor pressure; if
    # no typed precursor pressure exists the prior stays unresolved (the previous
    # generic_pressure query resolved to species_ambiguous, i.e. also unresolved).
    from twin import pressure_compat as _pc
    pp = None
    for _pq in _pc.PRECURSOR_PRESSURE_QUANTITIES:
        pp = chem.scoped_condition_prior(
            exps, "precursor_partial_pressure", _pq, "A", request.material,
            chem_ctx.precursor_identity, chem_ctx.co_reactant_identity,
            temperature=request.temperature, reactor_type=request.reactor_type)
        if pp.resolved:
            break
    pt = chem.scoped_condition_prior(
        exps, "precursor_pulse_time", "pulse_time", "A", request.material,
        chem_ctx.precursor_identity, chem_ctx.co_reactant_identity,
        temperature=request.temperature, reactor_type=request.reactor_type)
    ctx.chemistry_priors = {"precursor_partial_pressure": pp, "precursor_pulse_time": pt}

    # --- pA/tp ratio -----------------------------------------------------------
    w = None
    if "ratio" in c and c["ratio"]:
        ctx.priors["ratio"] = Prior.make("ratio", float(c["ratio"]), "Pa/s", "user",
                                         evidence="explicit user constraint")
    else:
        ratio_prior, ratio_status, why = chem.build_ratio(
            pp, pt, allow_fallback=request.allow_chemistry_fallback,
            fallback_value=RATIO_FALLBACK,
            fallback_reason="no chemistry-supported ratio could be constructed")
        ctx.ratio_status = ratio_status
        if ratio_prior.source == "kb":
            ctx.priors["ratio"] = Prior.make(
                "ratio", ratio_prior.value, "Pa/s", "kb", evidence=ratio_prior.evidence)
            ctx.priors["ratio"].confidence = ratio_prior.confidence
        elif ratio_prior.source == "fallback":
            ctx.priors["ratio"] = Prior.make(
                "ratio", ratio_prior.value, "Pa/s", "fallback", evidence=ratio_prior.evidence)
            ctx.warnings.append(
                "pA/tp ratio is a FALLBACK operating-family default, not literature-derived "
                f"(opted in via allow_chemistry_fallback; reason: {ratio_status})")
            ctx.unresolved.append("ratio_from_literature")
        else:
            # No opt-in: refuse to invent a ratio. The design will report
            # chemistry_unresolved rather than produce a recipe on a fiction.
            ctx.priors["ratio"] = Prior.make(
                "ratio", None, "Pa/s", "unresolved", evidence=why)
            ctx.warnings.append(
                f"no chemistry-supported pA/t_p ratio ({ratio_status}); set "
                "allow_chemistry_fallback=True to proceed on an explicit fallback")
            ctx.unresolved.append("ratio")

    # --- reference exposure (chemistry-scoped, when available) -----------------
    if pp.resolved and pt.resolved:
        ctx.priors["reference_effective_dose"] = Prior.make(
            "reference_effective_dose", pp.value * pt.value, "Pa·s", "kb",
            evidence=f"{pp.evidence} x {pt.evidence}")
    else:
        ctx.priors["reference_effective_dose"] = Prior.make(
            "reference_effective_dose", None, "Pa·s", "unresolved",
            evidence=("needs a species-scoped precursor pressure AND pulse time; "
                      f"pressure: {pp.evidence}"))
    ctx.priors["reference_pulse_time"] = Prior.make(
        "reference_pulse_time", pt.value if pt.resolved else None, "s",
        "kb" if pt.resolved else "unresolved", evidence=pt.evidence)
    if pt.resolved:
        ctx.priors["reference_pulse_time"].confidence = pt.confidence

    # --- operating bounds ------------------------------------------------------
    for key, default, unit, why in (
            ("pressure_bounds", PA_BOUNDS_DEFAULT, "Pa", "reactor-plausible pA window"),
            ("pulse_time_bounds", TP_BOUNDS_DEFAULT, "s", "reactor-plausible pulse window")):
        if key in c and c[key]:
            ctx.priors[key] = Prior.make(key, tuple(c[key]), unit, "user",
                                         evidence="explicit user constraint")
        else:
            ctx.priors[key] = Prior.make(key, default, unit, "model_supported",
                                         evidence=f"{why}; demonstration default, not extracted")
    if c.get("effective_dose_bounds"):
        ctx.priors["effective_dose_bounds"] = Prior.make(
            "effective_dose_bounds", tuple(c["effective_dose_bounds"]), "Pa·s", "user",
            evidence="explicit user constraint")
    return ctx


def _model(material):
    return channelModel.from_kb(material, corpus=_experiments())


def assess_feasibility(ctx, model=None):
    """Achievable PD50 range at the resolved ratio, and where the target sits."""
    ratio = ctx.value("ratio")
    if ratio is None:
        # No chemistry-supported ratio and no opt-in fallback: there is nothing to
        # evaluate the twin at. Report that, rather than crashing or inventing one.
        return {"pd_min": None, "pd_max": None, "effective_dose_bounds": None,
                "target_pd": ctx.value("target_pd"), "verdict": "unknown",
                "ratio": None,
                "ratio_source": ctx.priors["ratio"].source if "ratio" in ctx.priors
                else "unresolved"}
    model = model or _model(ctx.value("deposited_material") or ctx.value("material"))
    pd_min, pd_max, bounds = inverse_solver.achievable_pd_range(
        model, ratio, ctx.value("effective_dose_bounds"),
        ctx.value("pressure_bounds"), ctx.value("pulse_time_bounds"))
    tgt = ctx.value("target_pd")
    verdict = ("unknown" if tgt is None else
               "within_range" if pd_min <= tgt <= pd_max else
               "above_range" if tgt > pd_max else "below_range")
    return {"pd_min": pd_min, "pd_max": pd_max, "effective_dose_bounds": bounds,
            "target_pd": tgt, "verdict": verdict, "ratio": ratio,
            "ratio_source": ctx.priors["ratio"].source}


def generate_candidates(ctx, families=OPERATING_FAMILIES, model_factory=None):
    """One inverse solve per operating family. The solver is the ONLY inversion path;
    a family merely fixes the ratio that makes the problem one-dimensional.

    If the user pinned a ratio, that single family is used and no alternatives are
    invented."""
    mk = model_factory or (lambda: _model(ctx.value("material")))
    tgt = ctx.value("target_pd")
    rp = ctx.priors["ratio"]
    base_ratio, base_src, base_conf = rp.value, rp.source, rp.confidence
    if base_src == "user":
        families = (("user_specified", 1.0, "ratio pinned by the caller"),)

    out = []
    for name, mult, _desc in families:
        ratio = float(base_ratio) * float(mult)
        if abs(mult - 1.0) < 1e-12:
            # this family IS the resolved reference ratio — same evidence, same weight
            ev_src, ev_conf = base_src, base_conf
            ev = rp.evidence
        else:
            # scaled off the base: inherits its evidence class, never outranks it
            ev_src = f"derived_from_{base_src}"
            ev_conf = round(base_conf * DERIVED_CONFIDENCE_FACTOR, 4)
            ev = (f"{mult:g} x the resolved reference ratio "
                  f"({base_ratio:.4g} Pa/s, source {base_src}); the multiplier is an "
                  f"operating archetype and carries no independent evidence")
        cand = Candidate(family=name, ratio=ratio,
                         family_definition_source=("user" if base_src == "user"
                                                   else "model_supported_archetype"),
                         ratio_evidence_source=ev_src, ratio_evidence_confidence=ev_conf,
                         ratio_evidence=ev, base_ratio_source=base_src,
                         ratio_multiplier=float(mult))
        if tgt is None:
            cand.rejected = "no target_pd resolved"
            out.append(cand); continue
        cand.solution = inverse_solver.solve_target_dose(
            mk(), tgt, ratio,
            dose_bounds=ctx.value("effective_dose_bounds"),
            pressure_bounds=ctx.value("pressure_bounds"),
            pulse_time_bounds=ctx.value("pulse_time_bounds"),
            reference={"effective_dose": ctx.value("reference_effective_dose")},
            provenance={"family": name, "family_definition_source": cand.family_definition_source,
                        "ratio_evidence_source": ev_src, "base_ratio_source": base_src,
                        "bounds_source": ctx.priors["pressure_bounds"].source})
        if not cand.solution.feasible:
            cand.rejected = f"{cand.solution.status}: {cand.solution.reason}"
        out.append(cand)
    return out


def family_achievable_ranges(ctx, families=OPERATING_FAMILIES, model_factory=None):
    """(family, ratio, pd_min, pd_max, bounds) for every allowed family — the union of
    these is the GLOBAL achievable region, which is strictly wider than the reference
    family's own range."""
    mk = model_factory or (lambda: _model(ctx.value("material")))
    base = ctx.value("ratio")
    rows = []
    for name, mult, _d in families:
        r = float(base) * float(mult)
        try:
            lo_pd, hi_pd, bounds = inverse_solver.achievable_pd_range(
                mk(), r, ctx.value("effective_dose_bounds"),
                ctx.value("pressure_bounds"), ctx.value("pulse_time_bounds"))
        except Exception as e:
            rows.append({"family": name, "ratio": r, "pd_min": None, "pd_max": None,
                         "bounds": None, "error": f"{type(e).__name__}: {e}"})
            continue
        rows.append({"family": name, "ratio": r, "pd_min": lo_pd, "pd_max": hi_pd,
                     "bounds": bounds, "error": None})
    return rows


def global_achievable_range(rows):
    """Union of the family ranges. Used to construct a genuinely globally-infeasible
    target dynamically, instead of hard-coding a threshold that geometry changes
    silently invalidate."""
    lo = [r["pd_min"] for r in rows if r["pd_min"] is not None]
    hi = [r["pd_max"] for r in rows if r["pd_max"] is not None]
    return (min(lo) if lo else None), (max(hi) if hi else None)


def analyse_robustness(cand, ctx, model_factory=None, rel=0.10):
    """How much does the achieved PD50 move if the realised exposure or the assumed
    ratio is off by ±`rel`? A candidate sitting on a steep part of the curve, or hard
    against an operating bound, is a worse recipe than one that is not — even when
    both hit the target exactly."""
    if not cand.feasible:
        return {}
    mk = model_factory or (lambda: _model(ctx.value("material")))
    s = cand.solution
    ev = inverse_solver._Evaluator(mk(), cand.ratio)
    lo, hi = s.effective_dose_bounds

    def pd_at(dose):
        return ev(min(max(dose, lo), hi))

    d_lo, d_hi = pd_at(s.effective_dose * (1 - rel)), pd_at(s.effective_dose * (1 + rel))
    dose_sens = abs(d_hi - d_lo) / (2 * rel) / max(s.achieved_pd, 1e-30)   # d ln PD / d ln dose

    ev2 = inverse_solver._Evaluator(mk(), cand.ratio * (1 + rel))
    pd_r = ev2(s.effective_dose)
    ratio_sens = abs(pd_r - s.achieved_pd) / rel / max(s.achieved_pd, 1e-30)

    # headroom: how close the operating point sits to its bounds, in log-space
    pa_lo, pa_hi = ctx.value("pressure_bounds")
    tp_lo, tp_hi = ctx.value("pulse_time_bounds")
    def margin(v, a, b):
        return min(math.log(v / a), math.log(b / v)) / math.log(b / a) if v > 0 and b > a else 0.0
    return {"dose_sensitivity": dose_sens, "ratio_sensitivity": ratio_sens,
            "pd_at_minus": d_lo, "pd_at_plus": d_hi, "perturbation": rel,
            "pressure_margin": margin(s.pA, pa_lo, pa_hi),
            "pulse_time_margin": margin(s.pulse_time, tp_lo, tp_hi),
            "dose_margin": margin(s.effective_dose, lo, hi)}


# The inputs the ledger reports on. "Critical" below is a NARROWER set.
CRITICAL_INPUTS = ("target_pd", "material", "ratio", "pressure_bounds", "pulse_time_bounds",
                   "reference_effective_dose", "reference_pulse_time")

# --- decision criticality -----------------------------------------------------
# A raw source count is misleading on its own: today the corpus supplies exactly one
# KB-backed input (`reference_pulse_time`) and exactly one fallback (`ratio`) — but the
# KB one never enters the solve, while the fallback one sets pA and t_p for every
# candidate. Counting them as one-each would suggest a balance that does not exist.
#
# Criticality is therefore an explicit, documented classification of the current M2
# design variables rather than an invented score. An input is decision-critical when
# it materially affects the selected family, the solved pressure, the solved pulse
# time, the effective dose, feasibility, or the ranking:
DECISION_CRITICAL = {
    "ratio": "sets pA and t_p for every candidate, and scales every family",
    "target_pd": "is the root the solver matches",
    "material": "selects the twin's geometry, temperature and species parameters",
    "pressure_bounds": "binds the effective-dose bracket and can make a family infeasible",
    "pulse_time_bounds": "binds the effective-dose bracket and can make a family infeasible",
}
# Deliberately NOT critical — recorded in the ledger, but they do not reach the solve:
NON_CRITICAL_NOTE = {
    "reference_effective_dose": "reported for comparison only; the root does not depend on it",
    "reference_pulse_time": "reported for comparison only; not consumed by the inversion",
}


def knowledge_coverage(ctx, best=None):
    """How much of this design rests on retrieved knowledge versus stand-ins.

    A fallback is explicitly NOT evidence: it is counted in its own bucket and never
    folded into the KB total. `fallback_dependent_result` is structural — it asks
    whether a fallback materially reaches the recipe, not whether one merely exists
    somewhere in the context."""
    buckets = {k: [] for k in ("user", "kb", "model_supported", "fallback", "unresolved")}
    for name, p in ctx.priors.items():
        buckets.setdefault(p.source, []).append(name)
    critical = {n: {"source": ctx.priors[n].source,
                    "confidence": ctx.priors[n].confidence,
                    "value": ctx.priors[n].value,
                    "unit": ctx.priors[n].unit}
                for n in CRITICAL_INPUTS if n in ctx.priors}

    # material dependence: the ratio decides pA and t_p for every candidate, so a
    # fallback ratio makes the whole recipe fallback-dependent even if the solve is exact
    ratio_src = ctx.priors["ratio"].source if "ratio" in ctx.priors else "unresolved"
    dep_reasons = []
    if ratio_src == "fallback" or ratio_src.startswith("derived_from_fallback"):
        dep_reasons.append("the pressure-to-pulse ratio is a fallback, and it sets pA and t_p")
    if best is not None and str(best.ratio_evidence_source).endswith("fallback"):
        dep_reasons.append(f"the selected family '{best.family}' uses a "
                           f"{best.ratio_evidence_source} ratio")
    if best is None and ratio_src == "fallback":
        dep_reasons.append("candidate generation itself ran on a fallback ratio")

    n_kb, n_user = len(buckets["kb"]), len(buckets["user"])
    n_fb, n_unres = len(buckets["fallback"]), len(buckets["unresolved"])

    # decision-critical inputs, grouped by how well each is actually supported. This is
    # what the summary leads with — a count over ALL inputs hides which ones matter.
    crit_by_source = {k: [] for k in ("user", "kb", "model_supported", "fallback", "unresolved")}
    for name, why in DECISION_CRITICAL.items():
        p = ctx.priors.get(name)
        if p is None:
            crit_by_source["unresolved"].append({"name": name, "why": why, "confidence": 0.0})
            continue
        crit_by_source.setdefault(p.source, []).append(
            {"name": name, "why": why, "confidence": p.confidence,
             "value": p.value, "unit": p.unit})
    weak = crit_by_source["fallback"] + crit_by_source["unresolved"]
    critical_unresolved = [c["name"] for c in crit_by_source["unresolved"]]

    # Four-way support level. Same computed meaning as before (complete / partial /
    # nothing-supported), with `substantial` separating "gaps exist, but none of them
    # touch a decision-critical input" from "a gap sits on a critical input".
    if n_unres == 0 and n_fb == 0:
        level = "complete"
    elif (n_kb + n_user) == 0:
        level = "insufficient"
    elif not weak:
        level = "substantial"
    else:
        level = "partial"

    lead = []
    for c in crit_by_source["fallback"]:
        lead.append(f"{c['name']} is fallback-supported and {c['why']}")
    for c in crit_by_source["unresolved"]:
        lead.append(f"{c['name']} is unresolved and {c['why']}")
    interpretation = (
        "All decision-critical inputs are evidence-supported."
        if not lead else
        "The design is only partially evidence-supported because "
        + "; ".join(lead) + ".")

    return {"level": level, "counts": {k: len(v) for k, v in buckets.items()},
            "by_source": buckets, "critical_inputs": critical,
            "critical_by_source": crit_by_source,
            "critical_weak": weak, "critical_unresolved": critical_unresolved,
            "interpretation": interpretation,
            "kb_supported": n_kb, "user_provided": n_user,
            "model_supported_defaults": len(buckets["model_supported"]),
            "fallback_inputs": n_fb, "unresolved_items": buckets["unresolved"],
            "kb_supported_critical": [c["name"] for c in crit_by_source["kb"]],
            "fallback_dependent_result": bool(dep_reasons),
            "fallback_dependency_reasons": dep_reasons}


def rank_candidates(cands, ctx):
    """Score feasible candidates. Every term is physically motivated and reported:

      accuracy    residual against the target (should be ~0 for all — a tie-breaker
                  only, kept so a degraded solve cannot silently win)
      margin      distance of pA / t_p / exposure from their bounds (log-space)
      robustness  insensitivity of the achieved PD to ±10 % exposure and ratio error
      throughput  shorter pulses are cheaper per cycle
      confidence  how well-grounded the ratio behind this candidate is
    """
    W = dict(RANKING_WEIGHTS)
    feas = [c for c in cands if c.feasible]
    if feas:
        tps = [c.solution.pulse_time for c in feas]
        t_lo, t_hi = min(tps), max(tps)
    for c in cands:
        if not c.feasible:
            c.total_score = 0.0
            continue
        s, rb = c.solution, c.robustness or {}
        acc = 1.0 - min(1.0, abs(s.residual or 0.0) / max(1e-12, 0.01 * (s.target_pd or 1.0)))
        margin = min(rb.get("pressure_margin", 0.0), rb.get("pulse_time_margin", 0.0),
                     rb.get("dose_margin", 0.0))
        margin = max(0.0, min(1.0, margin * 2))            # 0.5 of the span == full marks
        sens = max(rb.get("dose_sensitivity", 0.0), rb.get("ratio_sensitivity", 0.0))
        robust = 1.0 / (1.0 + max(0.0, sens))
        thr = 1.0 if t_hi <= t_lo else 1.0 - (s.pulse_time - t_lo) / (t_hi - t_lo)
        conf = c.ratio_evidence_confidence
        c.scores = {"accuracy": acc, "margin": margin, "robustness": robust,
                    "throughput": thr, "confidence": conf, "weights": W,
                    "profile": RANKING_PROFILE}
        c.total_score = sum(W[k] * c.scores[k] for k in W)
    return sorted(cands, key=lambda c: (-c.total_score, c.family))


def selection_summary(ranked, near_tie_threshold=NEAR_TIE_THRESHOLD):
    """Selected candidate, runner-up, score gap, near-tie flag, and the actual
    trade-off between the top two — so the ordering reads as a preference model and
    not as a physical law."""
    feas = [c for c in ranked if c.feasible]
    best = feas[0] if feas else None
    runner = feas[1] if len(feas) > 1 else None
    gap = (best.total_score - runner.total_score) if runner else None
    trade = []
    if best and runner:
        for key, label, better_is in (("throughput", "shorter pulse time", "higher"),
                                      ("margin", "operating margin from the bounds", "higher"),
                                      ("robustness", "insensitivity to exposure/ratio error", "higher"),
                                      ("confidence", "ratio evidence", "higher")):
            b, r = best.scores.get(key, 0.0), runner.scores.get(key, 0.0)
            if abs(b - r) < 1e-9:
                continue
            winner = best if b > r else runner
            trade.append({"criterion": key, "label": label, "favours": winner.family,
                          "best": b, "runner_up": r, "delta": b - r})
        trade.sort(key=lambda t: -abs(t["delta"]))
    return {"profile": RANKING_PROFILE, "weights": dict(RANKING_WEIGHTS),
            "selected": best.family if best else None,
            "runner_up": runner.family if runner else None,
            "score_gap": gap, "near_tie_threshold": near_tie_threshold,
            "near_tie": bool(gap is not None and gap < near_tie_threshold),
            "trade_offs": trade,
            "note": ("This selection reflects the active decision weights and is not a "
                     "unique physical optimum.")}


# =============================================================================
# Design certificate — the frozen-spec deliverable, assembled AROUND the existing
# solver / chemistry / evidence code. Every scientific quantity it emits carries an
# `origin` tag. Nothing here re-derives a root or re-pools chemistry.
# =============================================================================
# origin classification for every emitted scientific quantity
ORIGIN_DET = "determined_by_physics"
ORIGIN_PREF = "selected_by_preference"
ORIGIN_ASSUMED = "assumed_condition"
ORIGIN_UNDET = "structurally_undetermined"
ORIGIN_EV_UNC = "evidence_uncertain"
ORIGIN_EVIDENCE = "retrieved_evidence"

# The active forward model (Ylilammi channel) is a HIGH-ASPECT-RATIO transport model.
# Its validity domain is a property of the model, not of M2.
GEOMETRY_APPLICABILITY = {"lateral_channel": "valid", "vertical_structure": "valid",
                          "porous_material": "out_of_domain", "planar": "trivial"}
ADMISSIBILITY_REGIMES = ("quantitative", "exploratory", "infeasible", "refuse")
# secondary objectives that may select ONE point on the feasible locus (all are
# external preferences, never physics)
SECONDARY_OBJECTIVES = {
    "minimize_pulse_time": ("t_p", "min", "shortest pulse (throughput)"),
    "minimize_pressure": ("pA", "min", "lowest precursor partial pressure"),
    "maximize_pressure": ("pA", "max", "highest precursor partial pressure"),
    "maximize_bound_distance": (None, None, "maximum distance from the operating bounds"),
    "minimize_sensitivity": (None, None, "least sensitive point (bound-distance proxy)"),
}


def resolve_geometry(request, experiments):
    """Feature geometry is a DESIGN INPUT and the model-validity context — never
    inferred from the corpus majority (most ALD is planar; that says nothing about the
    feature being designed). Stated → user; otherwise the model's native HAR channel is
    ASSUMED and recorded as such."""
    if request.geometry_class:
        gc, src, ev = request.geometry_class, "user", "geometry class stated in the request"
    else:
        gc, src, ev = ("lateral_channel", "assumed",
                       "no geometry class stated; assumed the model's native high-aspect-ratio "
                       "lateral-channel geometry (recorded as an assumption)")
    appl = GEOMETRY_APPLICABILITY.get(gc, "unknown")
    seen = any(e.get("material") == request.material and e.get("geometry_class") == gc
               for e in (experiments or []))
    return {"geometry_class": gc, "applicability": appl, "model_valid": appl == "valid",
            "source": src, "evidence": ev, "corpus_precedent": seen}


def classify_admissibility(chem_status, geometry, bundle, reachable, uncertainty):
    """The regime that decides what KIND of answer is honest. Built from the existing
    compatibility/evidence signals — never hidden inside a coverage score."""
    reasons = []
    appl = geometry["applicability"]
    level = getattr(bundle, "compatibility_level", "unresolved")
    if appl == "out_of_domain":
        reasons.append({"code": "geometry_out_of_domain",
                        "detail": f"{geometry['geometry_class']} is outside the channel model's "
                                  "validated high-aspect-ratio regime"})
        return {"regime": "refuse", "reasons": reasons, "model_valid": False,
                "kinetics_level": level, "reachable": reachable}
    if appl == "trivial":
        reasons.append({"code": "geometry_trivial",
                        "detail": f"{geometry['geometry_class']} conformality is trivial; the "
                                  "transport-limited channel model does not apply"})
        return {"regime": "refuse", "reasons": reasons, "model_valid": False,
                "kinetics_level": level, "reachable": reachable}
    if chem_status == "unsupported":
        reasons.append({"code": "chemistry_unsupported",
                        "detail": "the requested chemistry has no evidence in the corpus"})
        return {"regime": "refuse", "reasons": reasons, "model_valid": True,
                "kinetics_level": level, "reachable": reachable}
    if not reachable:
        reasons.append({"code": "target_unreachable",
                        "detail": "no operating point within the pressure/pulse bounds meets the target"})
        return {"regime": "infeasible", "reasons": reasons, "model_valid": True,
                "kinetics_level": level, "reachable": False}
    caps = []
    if level != "exact_chemistry":
        caps.append({"code": "kinetics_not_chemistry_specific",
                     "detail": f"twin kinetics are '{level}'; the sticking / adsorption / GPC "
                               "coefficients are not resolved for this exact chemistry"})
    if uncertainty.get("withheld"):
        caps.append({"code": "kinetic_uncertainty_withheld",
                     "detail": uncertainty.get("note", "kinetic uncertainty is unavailable")})
    if appl == "unknown":
        caps.append({"code": "geometry_assumed",
                     "detail": f"geometry '{geometry['geometry_class']}' validity is unverified"})
    if caps:
        return {"regime": "exploratory", "reasons": caps, "model_valid": True,
                "kinetics_level": level, "reachable": True}
    return {"regime": "quantitative",
            "reasons": [{"code": "chemistry_specific_reachable",
                         "detail": "chemistry-specific kinetics, valid geometry, a reachable target "
                                   "and propagated evidence uncertainty"}],
            "model_valid": True, "kinetics_level": level, "reachable": True}


def determined_quantities(region, dose_solution, uncertainty):
    """The coordinate(s) the model actually identifies. For this model that is the
    effective dose; the pressure/pulse split is NOT here (it is undetermined). The band
    is evidence-based and may be withheld; the dose invariance is MEASURED off the
    region, not assumed."""
    if not region or region.get("empty"):
        return {"quantities": [], "note": "feasible region empty — no quantity is determined"}
    doses = region["dose_values"]
    d_region = sum(doses) / len(doses)
    d_val = dose_solution.effective_dose if (dose_solution and dose_solution.feasible) else d_region
    band = uncertainty.get("dose_band")
    band_basis = ("evidence" if uncertainty.get("kinetic_uncertainty")
                  else "geometry_temperature_only" if band else "withheld")
    return {"quantities": [{
        "name": "effective_dose", "symbol": "pA·t_p", "unit": "Pa·s",
        "origin": ORIGIN_DET, "value": d_val,
        "band": list(band) if band else None, "band_basis": band_basis,
        "model_invariance": {
            "dose_spread_frac": region["dose_spread_frac"],
            "detail": f"the effective dose (pA·t_p) varies by only {region['dose_spread_frac']*100:.2f}% "
                      "across the representative feasible operating points — measured against the "
                      "active model, not assumed"}}]}


def undetermined_quantities(region):
    """Coordinates the inverse problem leaves free. Structural (the model does not
    determine them) vs contingent (evidence-limited) are kept distinct. Verified from
    the region trace, never asserted."""
    out = []
    if region and region.get("split_structural"):
        pr, tr = region["pressure_range"], region["pulse_range"]
        out.append({
            "name": "pressure_pulse_split", "origin": ORIGIN_UNDET, "kind": "structural",
            "free_coordinate_count": region["free_coordinate_count"],
            "detail": (f"penetration depth stays on target (max deviation ≤ "
                       f"{region['pd_max_abs_residual']:.1e} m) while precursor pressure spans "
                       f"{pr[0]:.3g}–{pr[1]:.3g} Pa and pulse time spans {tr[0]:.3g}–{tr[1]:.3g} s; the "
                       "model does not determine which operating point within the feasible region to use"),
            "resolvable_by": "a secondary objective or an equipment constraint"})
    return {"undetermined": out}


def branch_assumptions(ctx, geometry, uncertainty, bundle, objective):
    """One consolidated assumption set; every entry states which conclusion depends on it."""
    a = []
    if geometry["source"] == "assumed":
        a.append({"name": "geometry_class", "value": geometry["geometry_class"],
                  "origin": ORIGIN_ASSUMED,
                  "affects": "model validity and therefore the entire admissibility verdict"})
    for key, what in (("pressure_bounds", "the extent of the feasible region and its clipping"),
                      ("pulse_time_bounds", "the extent of the feasible region and its clipping")):
        p = ctx.priors.get(key)
        if p and p.source == "model_supported":
            a.append({"name": key, "value": list(p.value) if p.value else None,
                      "origin": ORIGIN_ASSUMED, "affects": what})
    rp = ctx.priors.get("ratio")
    if rp and (rp.source == "fallback" or str(rp.source).startswith("fallback")):
        a.append({"name": "pA_tp_ratio", "value": rp.value, "origin": ORIGIN_ASSUMED,
                  "affects": "the reference sample point and the uncertainty probe only — NOT the "
                             "feasible region or the determined effective dose"})
    weak = [p for p, lvl in (getattr(bundle, "chemistry_match_levels", {}) or {}).items()
            if lvl in ("model_default", "material_generic", "unresolved")]
    if weak:
        a.append({"name": "kinetic_parameters", "value": weak, "origin": ORIGIN_ASSUMED,
                  "affects": "the absolute effective-dose value; caps the admissibility regime at "
                             "exploratory"})
    if uncertainty.get("withheld"):
        a.append({"name": "kinetic_uncertainty", "value": "withheld", "origin": ORIGIN_EV_UNC,
                  "affects": "target-hit credibility, which cannot be quantified from the evidence"})
    if objective:
        a.append({"name": "secondary_objective", "value": objective, "origin": ORIGIN_ASSUMED,
                  "affects": "which single operating point (if any) is recommended"})
    return a


def _region_samples(region):
    """Three labelled illustrative samples taken FROM the true locus (low / mid / high
    pressure). They are samples, never competitors, and never substitute for the region."""
    pts = sorted(region["points"], key=lambda p: p["pA"]) if region and region["points"] else []
    if not pts:
        return []
    idx = sorted(set([0, len(pts) // 2, len(pts) - 1]))
    names = {0: "low_pressure_long_pulse", len(pts) // 2: "balanced", len(pts) - 1: "high_pressure_short_pulse"}
    return [{**pts[i], "label": names.get(i, "sample"), "role": "illustrative_sample"} for i in idx]


def _bound_distance(pt, pab, tpb):
    def m(v, a, b):
        return min(math.log(v / a), math.log(b / v)) / math.log(b / a) if (v > 0 and b > a) else 0.0
    return min(m(pt["pA"], *pab), m(pt["t_p"], *tpb))


def recommend_operating_point(region, objective, pressure_bounds, pulse_time_bounds):
    """The feasible region is the answer. A single point is returned ONLY when an
    external preference selects it, or the bounds collapse the region to a singleton.
    A preference-selected point is tagged selected_by_preference, never determined."""
    if not region or region.get("empty"):
        return {"point": None, "is_unique": False, "chosen_by": None, "origin": None,
                "note": "no feasible region — nothing to recommend", "samples": []}
    pts = region["points"]
    samples = _region_samples(region)
    if region["free_coordinate_count"] == 0 and region["n_points"] == 1:
        return {"point": {**pts[0], "origin": ORIGIN_DET}, "is_unique": True,
                "chosen_by": "constraints_reduce_region_to_singleton", "origin": ORIGIN_DET,
                "note": "the operating bounds reduce the feasible region to a single point",
                "samples": samples}
    if not objective:
        return {"point": None, "is_unique": False, "chosen_by": None, "origin": None,
                "note": ("The feasible region is the scientific answer. Selecting a single operating "
                         "point requires an external criterion (a secondary objective or an equipment "
                         "limit); none was supplied."),
                "samples": samples}
    if objective not in SECONDARY_OBJECTIVES:
        return {"point": None, "is_unique": False, "chosen_by": None, "origin": None,
                "note": f"unknown secondary objective {objective!r}; the region is returned without a "
                        "selected point", "samples": samples}
    attr, how, label = SECONDARY_OBJECTIVES[objective]
    if attr is None:                       # bound-distance family
        pick = max(pts, key=lambda p: _bound_distance(p, pressure_bounds, pulse_time_bounds))
    else:
        pick = (min if how == "min" else max)(pts, key=lambda p: p[attr])
    return {"point": {**pick, "origin": ORIGIN_PREF}, "is_unique": False,
            "chosen_by": objective, "objective_label": label, "origin": ORIGIN_PREF,
            "note": (f"This point is SELECTED BY PREFERENCE ({label}). It is one of infinitely many "
                     "within the feasible operating region and is NOT distinguished by the physics."),
            "samples": samples}


def branch_confidence(admissibility, uncertainty):
    """Confidence is a property OF the deliverable. We never fabricate a probability:
    target_hit_credibility stays None and we report the evidence band + dominant
    contributor, or explicitly withhold."""
    if uncertainty.get("withheld"):
        return {"target_hit_credibility": None, "status": "withheld",
                "dose_band": None, "dominant_uncertainty": uncertainty.get("dominant"),
                "note": uncertainty.get("note"), "regime": admissibility["regime"]}
    return {"target_hit_credibility": None, "status": "band_available",
            "dose_band": list(uncertainty["dose_band"]) if uncertainty.get("dose_band") else None,
            "sigma_dose": uncertainty.get("sigma_dose"),
            "dominant_uncertainty": uncertainty.get("dominant"),
            "note": uncertainty.get("note"), "regime": admissibility["regime"]}


def evaluate_branch(request, precursor, co_reactant, geometry, experiments):
    """Evaluate ONE chemistry independently — the reusable core: resolve → retrieve →
    trace region → admissibility → determined/undetermined/uncertainty/recommendation.
    Evidence is never pooled across chemistries (each call is scoped to one)."""
    br = DesignRequest(material=request.material, target_pd=request.target_pd,
                       precursor=precursor, co_reactant=co_reactant,
                       temperature=request.temperature, reactor_type=request.reactor_type,
                       allow_chemistry_fallback=True, geometry_class=request.geometry_class,
                       secondary_objective=request.secondary_objective,
                       constraints=dict(request.constraints or {}))
    ctx = resolve_context(br, experiments_fn=lambda: experiments)
    mk = lambda: _model(ctx.value("deposited_material") or request.material)
    try:
        bundle = chemistry_params.params_for_chemistry(
            experiments, request.material, precursor, co_reactant,
            process_mode=(request.constraints or {}).get("process_mode"),
            temperature=request.temperature, reactor_family=request.reactor_type)
    except Exception as e:
        bundle = chemistry_params.TwinParameterBundle(
            requested_chemistry=(request.material, precursor, co_reactant, None),
            compatibility_level="unresolved", diagnostics=[f"bundle unavailable: {e}"])
    tgt = ctx.value("target_pd")
    pab, tpb = ctx.value("pressure_bounds"), ctx.value("pulse_time_bounds")
    ratio = ctx.value("ratio")
    prov = getattr(mk(), "kb_provenance", {})

    if tgt is None:
        region = {"empty": True, "n_points": 0, "points": [], "reason": "no target penetration depth",
                  "split_structural": False, "free_coordinate_count": 0, "pressure_range": None,
                  "pulse_range": None, "dose_values": [], "dose_range": None,
                  "dose_spread_frac": None, "pd_max_abs_residual": None}
    else:
        region = inverse_solver.trace_feasible_region(mk, tgt, pab, tpb)
    reachable = (tgt is not None) and (not region.get("empty"))

    dose_sol = None
    if ratio and tgt is not None:
        dose_sol = inverse_solver.solve_target_dose(mk(), tgt, ratio, pressure_bounds=pab,
                                                    pulse_time_bounds=tpb)
    if ratio and tgt is not None:
        uncertainty = inverse_solver.propagate_dose_uncertainty(
            mk, tgt, ratio, prov, pressure_bounds=pab, pulse_time_bounds=tpb)
    else:
        uncertainty = {"withheld": True, "dose_band": None, "kinetic_uncertainty": False,
                       "dominant": None, "contributions": {},
                       "note": "no ratio/target to propagate uncertainty through"}

    adm = classify_admissibility(ctx.chemistry_resolution_status, geometry, bundle, reachable, uncertainty)
    det = determined_quantities(region, dose_sol, uncertainty)
    undet = undetermined_quantities(region)
    assumptions = branch_assumptions(ctx, geometry, uncertainty, bundle, request.secondary_objective)
    rec = recommend_operating_point(region, request.secondary_objective, pab, tpb)
    conf = branch_confidence(adm, uncertainty)
    evidence = {
        "chemistry": ctx.chemistry.to_dict(),
        "chemistry_priors": {k: v.to_dict() for k, v in (ctx.chemistry_priors or {}).items()},
        "twin_parameter_bundle": bundle.to_dict(),
        "safe_for_cross_chemistry_comparison": bool(
            getattr(bundle, "safe_for_cross_chemistry_comparison", False)),
        "ledger": {k: v.to_dict() for k, v in ctx.priors.items()}}
    infeasibility = None
    if tgt is not None and region.get("empty"):
        infeasibility = {"reason": region.get("reason"), "target_pd": tgt}

    region_public = {k: region[k] for k in ("n_points", "empty", "pressure_range", "pulse_range",
                                            "dose_range", "dose_spread_frac", "free_coordinate_count",
                                            "pd_max_abs_residual", "split_structural") if k in region}
    region_public["points"] = region.get("points", [])
    region_public["target_pd"] = tgt
    region_public["origin"] = ORIGIN_DET
    return {"chemistry": {"precursor": precursor, "co_reactant": co_reactant,
                          "label": ctx.chemistry.label, "status": ctx.chemistry_resolution_status,
                          "source": ctx.chemistry.chemistry_source},
            "admissibility": adm, "determined": det, "feasible_region": region_public,
            "recommendation": rec, "undetermined": undet, "assumptions": assumptions,
            "confidence": conf, "evidence": evidence, "infeasibility": infeasibility,
            "ratio_status": ctx.ratio_status}


def build_certificate(request, experiments):
    """Assemble the design certificate: problem framing → geometry → per-chemistry
    branches → cross-branch policy. Material-only / ambiguous requests are evaluated by
    chemistry branch (never a blanket ambiguity failure), unless NONE can be evaluated."""
    geometry = resolve_geometry(request, experiments)
    problem = {
        "target_observable": "penetration_depth_pd50",
        "target_value": request.target_pd, "target_unit": "m",
        "controllable_variables": ["precursor_partial_pressure_pA", "pulse_time_tp"],
        "fixed_conditions": {"temperature": request.temperature,
                             "reactor_type": request.reactor_type},
        "operating_bounds": {"pressure_bounds": list(PA_BOUNDS_DEFAULT),
                             "pulse_time_bounds": list(TP_BOUNDS_DEFAULT)},
        "geometry": geometry,
        "secondary_objective": request.secondary_objective,
        "requested_chemistry": {"precursor": request.precursor, "co_reactant": request.co_reactant},
        "unresolved_inputs": [] if request.target_pd is not None else ["target_pd"]}

    chem_ctx, chem_status, alts, notes = chem.resolve_chemistry(
        experiments, request.material, precursor=request.precursor,
        co_reactant=request.co_reactant, temperature=request.temperature,
        reactor_type=request.reactor_type)

    if chem_status == "unsupported":
        return {"problem": problem, "geometry": geometry, "chemistry_status": chem_status,
                "chemistry_notes": notes, "branches": [], "n_branches": 0,
                "overall_regime": "refuse",
                "refusal": {"code": "chemistry_unsupported",
                            "detail": (notes[0] if notes else "requested chemistry has no evidence")},
                "cross_chemistry_comparable": False, "comparison_note": None, "status": "refused"}

    if chem_status in ("material_only", "ambiguous"):
        resolved = [a for a in alts if a["resolved"]]
        if not resolved:
            return {"problem": problem, "geometry": geometry, "chemistry_status": chem_status,
                    "chemistry_notes": notes, "branches": [], "n_branches": 0,
                    "overall_regime": "refuse",
                    "refusal": {"code": "no_evaluable_chemistry",
                                "detail": f"no resolved chemistry for {request.material} to evaluate"},
                    "cross_chemistry_comparable": False, "comparison_note": None, "status": "refused"}
        specs = [(a["precursor"], a["co_reactant"]) for a in resolved]
    else:
        specs = [(chem_ctx.precursor_identity, chem_ctx.co_reactant_identity)]

    branches = [evaluate_branch(request, p, c, geometry, experiments) for (p, c) in specs]
    multi = len(branches) > 1
    comparable = multi and all(b["evidence"]["safe_for_cross_chemistry_comparison"] for b in branches)
    comparison_note = None
    if multi:
        comparison_note = ("branches share cross-chemistry-safe bundles; quantitative comparison is "
                           "permitted" if comparable else
                           "branches are evaluated independently; their kinetic bundles are NOT safe "
                           "for cross-chemistry comparison, so no defensible quantitative ranking is "
                           "offered")
    overall = (branches[0]["admissibility"]["regime"] if not multi else "branches_evaluated")
    return {"problem": problem, "geometry": geometry, "chemistry_status": chem_status,
            "chemistry_notes": notes, "branches": branches, "n_branches": len(branches),
            "overall_regime": overall, "refusal": None,
            "cross_chemistry_comparable": bool(comparable), "comparison_note": comparison_note,
            "status": "certified"}


def design(request, model_factory=None, warm_start_fn=None, families=OPERATING_FAMILIES,
           near_tie_threshold=NEAR_TIE_THRESHOLD, experiments_fn=None):
    """Full pipeline.

    Two feasibility concepts are kept apart and BOTH reported:
      reference_context_status   can the resolved reference ratio reach the target?
      global_design_space_status can ANY allowed operating family reach it?
    The top-level status follows the GLOBAL result — a reference family that cannot
    reach the target does not make the design infeasible if another family can."""
    ctx = resolve_context(request, warm_start_fn=warm_start_fn,
                          experiments_fn=experiments_fn)
    mk = model_factory or (lambda: _model(ctx.value("deposited_material")
                                          or request.material))

    _exps = (experiments_fn or _experiments)()

    # Twin-parameter gate: chemistry-scoped priors are not enough. If the twin's
    # kinetics were pooled over every chemistry of the material, the prediction is
    # generic and must not be sold as chemistry-validated or compared across
    # chemistries.
    try:
        _bundle = chemistry_params.params_for_chemistry(
            _exps, ctx.value("deposited_material") or request.material,
            ctx.chemistry.precursor_identity, ctx.chemistry.co_reactant_identity,
            process_mode=request.constraints.get("process_mode"),
            temperature=request.temperature, reactor_family=request.reactor_type)
        twin_compat = chem.assess_twin_compatibility(
            ctx.chemistry, getattr(mk(), "kb_provenance", {}), _exps, bundle=_bundle)
    except Exception as e:
        _bundle = None
        twin_compat = chem.TwinChemistryCompatibility(
            evidence=f"twin unavailable: {type(e).__name__}: {e}")

    # The design certificate is the frozen-spec deliverable; it is assembled around the
    # same solver/chemistry/evidence code and is the ONLY thing the report renders.
    certificate = build_certificate(request, _exps)

    # No ratio -> the legacy 1-D family pipeline cannot run; the certificate still does
    # (it traces the region directly). Return the certificate PLUS legacy-compatible
    # fields so existing consumers keep working during migration.
    if ctx.value("ratio") is None:
        cov0 = knowledge_coverage(ctx, best=None)
        cov0["twin_compatibility"] = twin_compat.to_dict()
        status = ("chemistry_ambiguous"
                  if ctx.chemistry_resolution_status in ("ambiguous", "material_only")
                  else "chemistry_unsupported"
                  if ctx.chemistry_resolution_status == "unsupported"
                  else "ratio_unresolved")
        return _with_certificate(
            {"context": ctx, "feasibility": None, "candidates": [], "best": None,
             "selection": selection_summary([], near_tie_threshold),
             "coverage": cov0, "family_ranges": [], "twin_compatibility": twin_compat,
             "global_achievable": {"pd_min": None, "pd_max": None},
             "reference_context_status": "unknown",
             "global_design_space_status": "unknown", "status": status},
            certificate)
    feas = assess_feasibility(ctx, model=mk())
    fam_ranges = family_achievable_ranges(ctx, families=families, model_factory=mk)
    g_lo, g_hi = global_achievable_range(fam_ranges)
    cands = generate_candidates(ctx, families=families, model_factory=mk)
    for c in cands:
        c.robustness = analyse_robustness(c, ctx, model_factory=mk)
    ranked = rank_candidates(cands, ctx)
    sel = selection_summary(ranked, near_tie_threshold)
    best = next((c for c in ranked if c.feasible), None)

    reference_context_status = (
        "unknown" if feas["verdict"] == "unknown" else
        "feasible" if feas["verdict"] == "within_range" else
        "infeasible_high" if feas["verdict"] == "above_range" else "infeasible_low")
    global_design_space_status = "feasible" if best is not None else "infeasible"
    tgt = ctx.value("target_pd")
    if best is None and tgt is not None and g_hi is not None:
        global_design_space_status = ("infeasible_high" if tgt > g_hi else
                                      "infeasible_low" if (g_lo is not None and tgt < g_lo)
                                      else "infeasible")
    cov = knowledge_coverage(ctx, best=best)
    cov["twin_compatibility"] = twin_compat.to_dict()
    cov["twin_parameter_bundle"] = _bundle.to_dict()
    cov["chemistry_ambiguous"] = ctx.chemistry_resolution_status in ("ambiguous", "material_only")
    cov["chemistry_incomplete"] = ctx.chemistry_resolution_status != "fully_specified"
    cov["twin_chemistry_unverified"] = not twin_compat.compatible
    cov["safe_for_quantitative_use"] = bool(
        twin_compat.safe_for_quantitative_comparison and not cov["fallback_dependent_result"])
    return _with_certificate(
        {"context": ctx, "twin_compatibility": twin_compat, "feasibility": feas,
         "candidates": ranked, "best": best, "selection": sel, "coverage": cov,
         "family_ranges": fam_ranges,
         "global_achievable": {"pd_min": g_lo, "pd_max": g_hi},
         "reference_context_status": reference_context_status,
         "global_design_space_status": global_design_space_status,
         "status": "designed" if best else "no_feasible_candidate"},
        certificate)


def _with_certificate(legacy, certificate):
    """Merge the design certificate into a legacy result dict and mirror the primary
    branch's sections at top level, so both the report and programmatic callers read the
    certificate without digging into `branches`."""
    out = dict(legacy)
    out["certificate"] = certificate
    out["problem"] = certificate["problem"]
    out["geometry"] = certificate["geometry"]
    out["branches"] = certificate["branches"]
    out["overall_regime"] = certificate["overall_regime"]
    primary = certificate["branches"][0] if certificate["branches"] else None
    if primary is not None:
        for key in ("admissibility", "determined", "feasible_region", "recommendation",
                    "undetermined", "assumptions", "confidence"):
            out[key] = primary[key]
    else:
        out["admissibility"] = {"regime": certificate["overall_regime"],
                                "reasons": [certificate.get("refusal") or {}]}
    return out



# =============================================================================
# provenance-rich report
# =============================================================================
_CSS = """
body{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media(prefers-color-scheme:dark){body{background:#131417;color:#eceef2}
 .card{background:#1c1e22 !important;border-color:#2b2e34 !important}
 th{color:#a8adb7 !important} td{border-color:#2b2e34 !important} .mut{color:#8b919b !important}}
.wrap{max-width:1080px;margin:0 auto;padding:26px 22px 60px}
h1{font-size:22px;margin:0 0 2px}h2{font-size:14px;margin:0 0 10px}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}
.sub{color:#565c66;margin-bottom:18px}
.card{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{text-align:left;padding:6px 8px;border-bottom:1px solid #e6e8ec;color:#565c66;font-size:10.5px;
   text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid #eef0f3;vertical-align:top}
.tag{display:inline-block;font-size:9.5px;padding:1px 6px;border-radius:6px;font-weight:700;letter-spacing:.02em}
.s-user{background:rgba(27,175,122,.18);color:#1baf7a}
.s-kb{background:rgba(42,120,214,.18);color:#2a78d6}
.s-model_supported{background:rgba(74,58,167,.16);color:#4a3aa7}
.s-fallback{background:rgba(237,161,0,.20);color:#b37a00}
.s-unresolved{background:rgba(227,73,72,.16);color:#e34948}
.ok{color:#1baf7a;font-weight:700}.bad{color:#e34948;font-weight:700}.warn{color:#b37a00;font-weight:700}
.mut{color:#8b919b}.bar{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px}
.stat{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:9px 14px}
@media(prefers-color-scheme:dark){.stat{background:#1c1e22;border-color:#2b2e34}}
.stat b{font-size:18px;display:block}.stat span{font-size:11px;color:#8b919b}
.note{font-size:12px;color:#565c66;margin-top:10px}
"""


def _tag(src):
    return f'<span class="tag s-{html.escape(str(src))}">{html.escape(str(src))}</span>'


def _fmt(v, n=4):
    if v is None:
        return '<span class="mut">—</span>'
    if isinstance(v, float):
        return f"{v:.{n}g}"
    if isinstance(v, (tuple, list)):
        return ", ".join(_fmt(x, n) for x in v)
    return html.escape(str(v))



def _pd(v, n=3):
    return "—" if v is None else f"{v*1e6:.{n}f}"


CANONICAL_REPORT = "m2_report.html"      # the ONE committed M2 artifact


def _regime_badge(regime):
    cls = {"quantitative": "ok", "exploratory": "warn", "infeasible": "bad",
           "refuse": "bad", "branches_evaluated": "warn"}.get(regime, "warn")
    return f'<b class={cls}>{html.escape(str(regime))}</b>'


# origin -> reused source-tag colour (determined=blue like kb, preference=purple,
# assumed=amber like fallback, undetermined=red, evidence_uncertain=amber)
_ORIGIN_CLASS = {ORIGIN_DET: "kb", ORIGIN_PREF: "model_supported", ORIGIN_ASSUMED: "fallback",
                 ORIGIN_UNDET: "unresolved", ORIGIN_EV_UNC: "fallback", ORIGIN_EVIDENCE: "kb"}


def _otag(origin):
    return (f'<span class="tag s-{_ORIGIN_CLASS.get(origin, "unresolved")}">'
            f'{html.escape(str(origin))}</span>')


def _pt(p, n=4):
    return "—" if not p else f"pA={p['pA']:.4g} Pa · t_p={p['t_p']:.4g} s"


def render_report(result, out_path=None):
    """The single canonical M2 report, rendered FROM the design certificate and
    organised around the scientific result (frozen-spec section order), not the internal
    pipeline. It presents the FEASIBLE REGION as the answer and never a single sampled
    pressure/pulse pair as the uniquely solved recipe. `out_path` lets tests render to
    tmp_path without touching the committed artifact."""
    cert = result["certificate"]
    ctx = result["context"]
    problem = cert["problem"]
    geom = cert["geometry"]
    branches = cert["branches"]
    primary = branches[0] if branches else None
    tgt = problem["target_value"]
    material = ctx.value("deposited_material") or ctx.value("material") or "—"

    def card(n, title, body):
        return f"<div class=card><h2>{n} · {html.escape(title)}</h2>{body}</div>"

    # ---- 1 Executive Summary -------------------------------------------------
    # Leads with everything a reader needs to know what the report is about and how it
    # came out: target, outcome, chemistry, geometry, reachability, classification.
    if primary is None:                     # refusal
        ref = cert.get("refusal") or {}
        s1 = (f"<div class=bar>"
              f"<div class=stat><b>{_pd(tgt)} µm</b><span>requested penetration depth</span></div>"
              f"<div class=stat>{_regime_badge(cert['overall_regime'])}<span>outcome classification</span></div>"
              f"<div class=stat><b>{html.escape(str(material))}</b><span>material</span></div>"
              f"<div class=stat><b class={'ok' if geom['model_valid'] else 'bad'}>"
              f"{html.escape(geom['geometry_class'])}</b><span>geometry</span></div></div>"
              f"<div class=note><span class=bad>Refused.</span> "
              f"{html.escape(ref.get('detail', 'no evaluable design'))} "
              f"(<span class=mono>{html.escape(ref.get('code', 'refuse'))}</span>).</div>")
    else:
        adm = primary["admissibility"]
        reasons = "".join(
            f"<li><span class=mono>{html.escape(r.get('code', ''))}</span> — "
            f"{html.escape(r.get('detail', ''))}</li>" for r in adm["reasons"])
        reg = primary["feasible_region"]
        outcome_line = (
            f"A feasible operating region was found" if not reg.get("empty")
            else "No feasible operating region was found")
        s1 = (f"<div class=bar>"
              f"<div class=stat><b>{_pd(tgt)} µm</b><span>requested penetration depth</span></div>"
              f"<div class=stat>{_regime_badge(adm['regime'])}<span>outcome classification (admissibility regime)</span></div>"
              f"<div class=stat><b>{html.escape(str(material))}</b><span>material</span></div>"
              f"<div class=stat><b>{html.escape(primary['chemistry']['label'])}</b><span>chemistry</span></div>"
              f"<div class=stat><b class={'ok' if geom['model_valid'] else 'bad'}>"
              f"{html.escape(geom['geometry_class'])}</b><span>geometry (model {'valid' if geom['model_valid'] else 'INVALID'})</span></div>"
              f"<div class=stat><b>{'reachable' if adm['reachable'] else 'unreachable'}</b>"
              f"<span>target reachability</span></div></div>"
              f"<div class=note><b>{outcome_line}</b> for depositing "
              f"{html.escape(str(material))} to a {_pd(tgt)} µm penetration depth in a "
              f"{html.escape(geom['geometry_class'])} feature using {html.escape(primary['chemistry']['label'])}. "
              f"The design is classified <b>{html.escape(adm['regime'])}</b>.</div>"
              f"<div class=note><b>Why this classification:</b><ul>{reasons}</ul></div>"
              + ("<div class=note>A <b>quantitative</b> design requires chemistry-specific "
                 "kinetics, a valid geometry, a reachable target and propagated evidence "
                 "uncertainty. Anything less is reported as <b>exploratory</b> — the same "
                 "structured result, with quantitative confidence withheld.</div>"
                 if adm['regime'] == 'exploratory' else ""))

    subtitle = (f"{cert['overall_regime']} · "
                + (f"{cert['n_branches']} chemistry branch(es)" if cert["n_branches"] else "refused"))

    # ---- 2 Problem Definition -----------------------------------------------
    # Explicitly defines the inverse-design problem, including material and chemistry.
    fixed = problem["fixed_conditions"]
    rq = problem["requested_chemistry"]
    chem_label = (primary["chemistry"]["label"] if primary
                  else f"{rq.get('precursor') or '?'} + {rq.get('co_reactant') or '?'}")
    s2 = (f"<div class=note>The inverse-design problem this report solves: find operating "
          f"conditions that achieve the target observable for the stated material, chemistry and "
          f"geometry.</div>"
          f"<table>"
          f"<tr><th>element</th><th>value</th></tr>"
          f"<tr><td class=mono>target observable</td><td class=mono>{html.escape(problem['target_observable'])}</td></tr>"
          f"<tr><td class=mono>target value</td><td class=mono>{_pd(tgt)} µm</td></tr>"
          f"<tr><td class=mono>material (deposited film)</td><td class=mono>{html.escape(str(material))}</td></tr>"
          f"<tr><td class=mono>chemistry (precursor + co-reactant)</td><td class=mono>{html.escape(chem_label)}</td></tr>"
          f"<tr><td class=mono>geometry</td><td class=mono>{html.escape(geom['geometry_class'])} "
          f"{_tag(geom['source'])} <span class=mut>{html.escape(geom['evidence'])}</span></td></tr>"
          f"<tr><td class=mono>decision variables</td><td class=mono>{html.escape(', '.join(problem['controllable_variables']))}</td></tr>"
          f"<tr><td class=mono>fixed conditions</td><td class=mono>T={_fmt(fixed['temperature'])} · reactor={_fmt(fixed['reactor_type'])}</td></tr>"
          f"<tr><td class=mono>operating bounds</td><td class=mono>pA {_fmt(problem['operating_bounds']['pressure_bounds'])} Pa · "
          f"t_p {_fmt(problem['operating_bounds']['pulse_time_bounds'])} s</td></tr>"
          f"<tr><td class=mono>secondary objective</td><td class=mono>{_fmt(problem['secondary_objective'])}</td></tr>"
          f"<tr><td class=mono>unresolved inputs</td><td class=mono>{_fmt(problem['unresolved_inputs']) if problem['unresolved_inputs'] else '—'}</td></tr>"
          f"</table>")

    if primary is None:
        body = f"""<title>M2 · inverse-design certificate</title><style>{_CSS}</style>
<div class=wrap><div class=eyebrow>PSED · M2</div>
<h1>M2 · inverse-design certificate</h1><div class=sub>{html.escape(subtitle)}</div>
{card(1, "Executive Summary", s1)}
{card(2, "Problem Definition", s2)}
{card(3, "Literature evidence source (production semantic corpus)", _corpus_card(ctx))}
</div>"""
        out = Path(out_path) if out_path else HERE / CANONICAL_REPORT
        out.write_text(body)
        _publish_report(out)
        return out

    det = primary["determined"]
    region = primary["feasible_region"]
    rec = primary["recommendation"]
    undet = primary["undetermined"]["undetermined"]
    conf = primary["confidence"]
    ev = primary["evidence"]
    bundle = ev["twin_parameter_bundle"]

    # ---- 3 Quantities Identified by the Forward Model -----------------------
    drows = "".join(
        f"<tr><td class=mono>{html.escape(q['name'])} ({html.escape(q['symbol'])})</td>"
        f"<td class=mono>{_fmt(q['value'])}</td><td class=mono>{html.escape(q['unit'])}</td>"
        f"<td class=mono>{_fmt(q['band']) if q['band'] else '—'}</td>"
        f"<td class=mono>{html.escape(q['band_basis'])}</td>"
        f"<td>{_otag(q['origin'])}</td></tr>" for q in det["quantities"]) \
        or "<tr><td colspan=6 class=mut>no identified quantity (empty region)</td></tr>"
    inv = det["quantities"][0]["model_invariance"] if det["quantities"] else None
    s3 = ("<div class=note>The quantities below are the ones the <b>currently active forward "
          "model</b> (a diffusion–Langmuir channel model) can pin down from the target. For this "
          "model that quantity is the <b>effective dose</b> (precursor pressure × pulse time). "
          "This is a property of the active model, <b>not</b> a claim that effective dose is "
          "universally the fundamental process variable — a different forward model could identify "
          "a different quantity.</div>"
          f"<table><tr><th>quantity</th><th>value</th><th>unit</th><th>band</th>"
          f"<th>band basis</th><th>origin</th></tr>{drows}</table>"
          + (f"<div class=note><b>Consistency across the feasible region (measured, not assumed):</b> "
             f"{html.escape(inv['detail'])}</div>" if inv else "")
          + "<div class=note>Precursor pressure and pulse time are <b>not</b> identified separately by "
            "this model — only their combination (the effective dose) is. How the dose is split between "
            "them is left open (see §10).</div>")

    # ---- 4 feasible operating region ----------------------------------------
    samp = rec.get("samples") or []
    srows = "".join(
        f"<tr><td class=mono>{html.escape(s['label'])}</td><td class=mono>{s['pA']:.4g}</td>"
        f"<td class=mono>{s['t_p']:.4g}</td><td class=mono>{s['effective_dose']:.4g}</td>"
        f"<td class=mono>{_pd(s['achieved_pd'])}</td>"
        f"<td class=mut>illustrative_sample</td></tr>" for s in samp)
    pr, tr = region.get("pressure_range"), region.get("pulse_range")
    if region.get("empty"):
        s4 = ("<div class=note><span class=bad><b>The feasible region is empty.</b></span> "
              "No operating conditions within the pressure and pulse-time ranges meet the target — see "
              "the infeasibility explanation.</div>")
    else:
        s4 = (f"<div class=bar>"
              f"<div class=stat><b>{region['n_points']}</b><span>representative feasible operating points</span></div>"
              f"<div class=stat><b>{region['free_coordinate_count']}</b><span>free coordinate(s)</span></div>"
              f"<div class=stat><b>{pr[0]:.3g} – {pr[1]:.3g}</b><span>precursor pressure range (Pa)</span></div>"
              f"<div class=stat><b>{tr[0]:.3g} – {tr[1]:.3g}</b><span>pulse-time range (s)</span></div>"
              f"<div class=stat><b>{region['dose_spread_frac']*100:.2f}%</b><span>variation in pressure × pulse time</span></div></div>"
              f"<div class=note>The feasible region is the <b>set of operating conditions that achieve the "
              f"target</b>, computed from the active forward model and limited to the allowed pressure and "
              f"pulse-time ranges. Every representative point below meets the target to within "
              f"{region['pd_max_abs_residual']:.1e} m (numerically exact). <b>This region — not any single "
              f"pressure/pulse pair — is the scientific answer.</b></div>"
              f"<div class=note>Across these points, the effective dose (precursor pressure × pulse time) "
              f"varies by only <b>{region['dose_spread_frac']*100:.2f}%</b>: the same total exposure reaches "
              f"the target regardless of how it is divided between a higher pressure with a shorter pulse or "
              f"a lower pressure with a longer pulse.</div>"
              f"<div class=note><b>Representative feasible operating points</b> (examples spanning the "
              f"region, not competing recipes):</div>"
              f"<table><tr><th>example</th><th>precursor pressure (Pa)</th><th>pulse time (s)</th>"
              f"<th>effective dose (Pa·s)</th><th>PD50 (µm)</th><th>role</th></tr>{srows}</table>")

    # ---- 5 recommendation ----------------------------------------------------
    if rec.get("point"):
        p = rec["point"]
        s5 = (f"<div class=bar><div class=stat><b>{_pt(p)}</b>"
              f"<span>selected operating point</span></div>"
              f"<div class=stat>{_otag(rec['origin'])}<span>origin</span></div>"
              f"<div class=stat><b>{html.escape(str(rec.get('chosen_by')))}</b><span>chosen by</span></div></div>"
              f"<div class=note><b>{html.escape(rec['note'])}</b></div>")
    else:
        s5 = (f"<div class=note><span class=warn><b>No unique recommendation.</b></span> "
              f"{html.escape(rec['note'])}</div>"
              f"<div class=note>Supported external criteria: "
              f"<span class=mono>{html.escape(', '.join(SECONDARY_OBJECTIVES))}</span>.</div>")

    # ---- 6 chemistry alternatives / branch comparison -----------------------
    if cert["n_branches"] > 1:
        brows = "".join(
            f"<tr><td class=mono>{html.escape(b['chemistry']['label'])}</td>"
            f"<td>{_regime_badge(b['admissibility']['regime'])}</td>"
            f"<td class=mono>{b['admissibility']['kinetics_level']}</td>"
            f"<td class=mono>{'yes' if b['admissibility']['reachable'] else 'no'}</td></tr>"
            for b in branches)
        s6 = (f"<div class=note>The deposited material does not determine the chemistry; each "
              f"candidate chemistry is evaluated <b>independently</b> (no evidence is pooled).</div>"
              f"<table><tr><th>chemistry</th><th>regime</th><th>kinetics level</th>"
              f"<th>reachable</th></tr>{brows}</table>"
              f"<div class=note><span class={'ok' if cert['cross_chemistry_comparable'] else 'warn'}>"
              f"{html.escape(cert['comparison_note'] or '')}</span></div>")
    else:
        s6 = (f"<div class=note>Chemistry <b>{html.escape(primary['chemistry']['label'])}</b> evaluated "
              f"as a single branch (status <span class=mono>{html.escape(primary['chemistry']['status'])}</span>). "
              f"Twin-kinetics compatibility level: <b class="
              f"{'ok' if bundle['compatibility_level']=='exact_chemistry' else 'bad'}>"
              f"{html.escape(bundle['compatibility_level'])}</b>.</div>")

    # ---- 7 supporting evidence ----------------------------------------------
    cp_rows = "".join(
        f"<tr><td class=mono>{html.escape(k)}</td><td class=mono>{_fmt(v.get('value'))}</td>"
        f"<td class=mono>{html.escape(str(v.get('species_scope')))}</td>"
        f"<td>{_tag(v.get('source'))}</td><td class=mono>{html.escape(str(v.get('match_quality')))}</td>"
        f"<td class=mut>{html.escape(str(v.get('evidence') or ''))}</td></tr>"
        for k, v in (ev["chemistry_priors"] or {}).items())
    ratio_status = primary.get("ratio_status")
    s7 = (f"<div class=note>This section is about <b>the evidence behind the design, not the design "
          f"outputs</b>. The values in the table are <b>literature-derived operating priors</b> "
          f"(conditions reported in prior experiments) and reference inputs — they are <b>not</b> the "
          f"optimized pressure or pulse: a value such as a precursor pulse time here is an input drawn "
          f"from the literature, not a recommended operating point (the design outputs are the feasible "
          f"region in §4).</div>"
          f"<div class=note><b>Chemistry-scoped operating evidence</b> (never pooled across "
          f"chemistries) — source <span class=mono>kb</span> = from literature, "
          f"<span class=mono>model_supported</span> = model default, "
          f"<span class=mono>unresolved</span> = no evidence found:</div>"
          f"<table><tr><th>prior (literature input)</th><th>value</th><th>species</th><th>source</th>"
          f"<th>match quality</th><th>evidence / status</th></tr>{cp_rows}</table>"
          f"<div class=note>Twin parameter bundle: compatibility "
          f"<b>{html.escape(bundle['compatibility_level'])}</b>; "
          f"safe for cross-chemistry comparison: "
          f"<b>{'yes' if ev['safe_for_cross_chemistry_comparison'] else 'no'}</b>. The kinetic "
          f"coefficients (sticking, adsorption, growth-per-cycle) come from the model defaults here, "
          f"not from chemistry-specific measurements — which is why this branch is exploratory.</div>"
          + (f"<div class=note><span class=warn>⚠</span> ratio status: "
             f"<span class=mono>{html.escape(str(ratio_status))}</span> — <b>no species-attributed "
             f"precursor partial-pressure value has been extracted for this chemistry in the evidence "
             f"processed so far</b> (full pressure extraction is not yet complete, so this is not a "
             f"corpus-wide conclusion). The pressure records processed to date are chamber-total or "
             f"unspecified, and the A/B reactant pressures shown in recipes are model assumptions "
             f"(source=model), not measurements.</div>"
             if ratio_status else "")
          + "<div class=note>The full provenance ledger is in the appendix (§11).</div>")

    # ---- 8 assumptions -------------------------------------------------------
    arows = "".join(
        f"<tr><td class=mono>{html.escape(a['name'])}</td><td class=mono>{_fmt(a['value'])}</td>"
        f"<td>{_otag(a['origin'])}</td><td class=mut>{html.escape(a['affects'])}</td></tr>"
        for a in primary["assumptions"]) or "<tr><td colspan=4 class=mut>none</td></tr>"
    s8 = (f"<div class=note>Every default, fallback, generic parameter and assumed condition the "
          f"result rests on — each states which conclusion depends on it.</div>"
          f"<table><tr><th>assumption</th><th>value</th><th>origin</th><th>affects</th></tr>{arows}</table>")

    # ---- 9 confidence and dominant uncertainty ------------------------------
    if conf["status"] == "withheld":
        s9 = (f"<div class=bar><div class=stat><b class=warn>withheld</b><span>target-hit credibility</span></div>"
              f"<div class=stat><b>{_fmt(conf.get('dominant_uncertainty'))}</b><span>dominant contributor</span></div></div>"
              f"<div class=note><span class=warn><b>Confidence withheld.</b></span> "
              f"{html.escape(conf.get('note') or '')} No probability is fabricated.</div>")
    else:
        s9 = (f"<div class=bar><div class=stat><b>{_fmt(conf.get('dose_band'))}</b>"
              f"<span>effective-dose band (Pa·s)</span></div>"
              f"<div class=stat><b>{_fmt(conf.get('dominant_uncertainty'))}</b><span>dominant contributor</span></div></div>"
              f"<div class=note>{html.escape(conf.get('note') or '')}</div>")

    # ---- 10 fundamentally undetermined quantities ---------------------------
    urows = "".join(
        f"<tr><td class=mono>{html.escape(u['name'])}</td><td>{_otag(u['origin'])}</td>"
        f"<td class=mono>{html.escape(u['kind'])}</td>"
        f"<td class=mut>{html.escape(u['detail'])}</td>"
        f"<td class=mut>{html.escape(u.get('resolvable_by', ''))}</td></tr>" for u in undet) \
        or "<tr><td colspan=5 class=mut>none — the target determines every operating coordinate</td></tr>"
    s10 = (f"<div class=note>Coordinates the inverse problem leaves free. <b>Structural</b> = the model "
           f"and target do not determine them (no evidence can); <b>contingent</b> = evidence-limited. "
           f"None of these appears in the determined-quantities section (§3).</div>"
           f"<table><tr><th>coordinate</th><th>origin</th><th>kind</th><th>evidence</th>"
           f"<th>resolvable by</th></tr>{urows}</table>")

    # ---- 11 technical provenance / ledger appendix --------------------------
    prows = "".join(
        f"<tr><td class=mono>{html.escape(k)}</td><td class=mono>{_fmt(p.value)}</td>"
        f"<td class=mut>{html.escape(p.unit or '')}</td><td>{_tag(p.source)}</td>"
        f"<td class=mono>{p.confidence:.1f}</td>"
        f"<td class=mut>{html.escape(p.evidence or '')}</td></tr>"
        for k, p in ctx.priors.items())
    s11 = (f"<div class=note>Complete provenance ledger — every value that entered the calculation and "
           f"where it came from. Legacy diagnostics: "
           f"<span class=mono>reference_context_status={html.escape(str(result.get('reference_context_status')))}</span>, "
           f"<span class=mono>global_design_space_status={html.escape(str(result.get('global_design_space_status')))}</span>.</div>"
           f"<table><tr><th>variable</th><th>value</th><th>unit</th><th>source</th><th>conf</th>"
           f"<th>evidence</th></tr>{prows}</table>"
           + "".join(f'<div class=note><span class=warn>⚠</span> {html.escape(w)}</div>'
                     for w in ctx.warnings)
           + '<div class=note><span class="tag s-user">user</span> stated · '
             '<span class="tag s-kb">kb</span> retrieved · '
             '<span class="tag s-model_supported">model_supported</span> envelope default · '
             '<span class="tag s-fallback">fallback</span> stand-in · '
             '<span class="tag s-unresolved">unresolved</span> no value.</div>')

    body = f"""<title>M2 · inverse-design certificate</title><style>{_CSS}</style>
<div class=wrap>
<div class=eyebrow>PSED · M2</div>
<h1>M2 · inverse-design certificate</h1>
<div class=sub>{html.escape(subtitle)}</div>
{card(1, "Executive Summary", s1)}
{card(2, "Problem Definition", s2)}
{card(3, "Quantities Identified by the Forward Model", s3)}
{card(4, "Feasible operating region", s4)}
{card(5, "Recommendation and its objective", s5)}
{card(6, "Chemistry alternatives and branch comparison", s6)}
{card(7, "Supporting evidence", s7)}
{card(8, "Assumptions", s8)}
{card(9, "Confidence and dominant uncertainty", s9)}
{card(10, "Fundamentally undetermined quantities", s10)}
{card(11, "Technical provenance and ledger appendix", s11)}
{card(12, "Literature evidence source (production semantic corpus)", _corpus_card(ctx))}
</div>"""
    out = Path(out_path) if out_path else HERE / CANONICAL_REPORT
    out.write_text(body)
    _publish_report(out)
    return out


def _corpus_card(ctx):
    """Where the literature evidence came from: the declared production corpus,
    with the Case/paper provenance behind each chemistry-scoped prior."""
    try:
        from twin import semantic_evidence as SE
        meta = SE.corpus_meta()
        recs = _experiments()
    except Exception as exc:                              # synthetic-test injection
        return f"<div class=note>corpus metadata unavailable: {html.escape(str(exc))}</div>"
    n_papers = len({r.get("_pid") for r in recs})
    rows = ""
    for name, sp in (ctx.chemistry_priors or {}).items():
        refs = ", ".join(sp.refs) if getattr(sp, "refs", None) else "—"
        rows += (f"<tr><td>{html.escape(name)}</td><td>{html.escape(str(sp.value))} "
                 f"{html.escape(sp.unit or '')}</td>"
                 f"<td>{sp.n_records}</td><td class=m>{html.escape(refs)}</td></tr>")
    return (
        f"<div class=note>All literature evidence in this certificate is retrieved from "
        f"the <b>production semantic corpus</b>: {meta['included_papers']} papers declared "
        f"by <span class=m>{html.escape(meta['manifest'])}</span> "
        f"({len(recs)} ExperimentalCases across {n_papers} papers; canonical chemical "
        f"identities; per-condition evidence classes). Excluded reviews "
        f"({html.escape(', '.join(meta['excluded_reviews']))}) are never read. "
        f"Representation identity is the Workbench authority "
        f"(build {html.escape(str(meta['workbench_head_sha']))} / "
        f"code {html.escape(str(meta['workbench_code_sha']))}).</div>"
        f"<table><tr><th>chemistry-scoped prior</th><th>value</th><th>n records</th>"
        f"<th>supporting papers (Case provenance in the ledger)</th></tr>{rows}</table>")


def _publish_report(out):
    """Copy the freshly generated canonical artifact to the numbered reports/ name."""
    import shutil
    dst = HERE.parent / "reports" / "04_twin_mpc__m2_report.html"
    if Path(out).resolve() == (HERE / CANONICAL_REPORT).resolve():
        shutil.copyfile(out, dst)
        print(f"copied -> {dst}")


def main():
    """Canonical M2 run: the 60 µm primary example -> m2_report.html (the ONE artifact)."""
    # Canonical example: chemistry is stated explicitly, because the deposited
    # material alone does not identify it. The fallback opt-in is required because the
    # corpus has no species-attributed precursor pressure — the report says so.
    res = design(DesignRequest(material="Al2O3", target_pd=60e-6,
                               precursor="TMA", co_reactant="H2O",
                               geometry_class="lateral_channel",
                               allow_chemistry_fallback=True))
    out = render_report(res)
    print(f"wrote {out}   (canonical M2 inverse-design certificate)")

    # Lead with the certificate — the frozen-spec deliverable.
    b = res["certificate"]["branches"][0]
    adm, det, reg = b["admissibility"], b["determined"], b["feasible_region"]
    conf, rec = b["confidence"], b["recommendation"]
    print(f"  admissibility regime      = {adm['regime']}  "
          f"({', '.join(r['code'] for r in adm['reasons'])})")
    print(f"  chemistry / geometry      = {b['chemistry']['label']} / "
          f"{res['geometry']['geometry_class']} (model_valid={res['geometry']['model_valid']})")
    for q in det["quantities"]:
        band = f" band={tuple(round(x, 3) for x in q['band'])} [{q['band_basis']}]" if q["band"] else " band=—"
        print(f"  determined                = {q['name']} = {q['value']:.4g} {q['unit']}{band}; "
              f"pA·t_p varies only {reg['dose_spread_frac']*100:.2f}% across the feasible points")
    if not reg["empty"]:
        print(f"  feasible region           = {reg['n_points']} pts, {reg['free_coordinate_count']} free "
              f"coord; pA {reg['pressure_range'][0]:.3g}–{reg['pressure_range'][1]:.3g} Pa, "
              f"t_p {reg['pulse_range'][0]:.3g}–{reg['pulse_range'][1]:.3g} s")
    for u in b["undetermined"]["undetermined"]:
        print(f"  undetermined              = {u['name']} ({u['kind']}) — resolvable by {u['resolvable_by']}")
    print(f"  recommendation            = {'—' if rec['point'] is None else rec['point']} "
          f"(chosen_by={rec['chosen_by']}; region is the answer)")
    print(f"  confidence                = {conf['status']} (dominant={conf.get('dominant_uncertainty')})")
    print(f"  assumptions               = {', '.join(a['name'] for a in b['assumptions'])}")


if __name__ == "__main__":
    main()
