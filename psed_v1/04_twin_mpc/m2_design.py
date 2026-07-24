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

import inverse_solver
from channel_model import channelModel
import kb_bridge
import kb_service
import m2_chemistry as chem

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
    if _EXPERIMENTS_FN is not None:
        return _EXPERIMENTS_FN()
    try:
        return kb_service._load()
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
    pp = chem.scoped_condition_prior(
        exps, "precursor_partial_pressure", "pressure", "A", request.material,
        chem_ctx.precursor_identity, chem_ctx.co_reactant_identity,
        temperature=request.temperature, reactor_type=request.reactor_type)
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
    return channelModel.from_kb(material)


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

    # Twin-parameter gate: chemistry-scoped priors are not enough. If the twin's
    # kinetics were pooled over every chemistry of the material, the prediction is
    # generic and must not be sold as chemistry-validated or compared across
    # chemistries.
    try:
        twin_compat = chem.assess_twin_compatibility(
            ctx.chemistry, getattr(mk(), "kb_provenance", {}), (experiments_fn or _experiments)())
    except Exception as e:
        twin_compat = chem.TwinChemistryCompatibility(
            evidence=f"twin unavailable: {type(e).__name__}: {e}")

    # No ratio -> no inversion. Refuse rather than invent one.
    if ctx.value("ratio") is None:
        cov0 = knowledge_coverage(ctx, best=None)
        cov0["twin_compatibility"] = twin_compat.to_dict()
        status = ("chemistry_ambiguous"
                  if ctx.chemistry_resolution_status in ("ambiguous", "material_only")
                  else "chemistry_unsupported"
                  if ctx.chemistry_resolution_status == "unsupported"
                  else "ratio_unresolved")
        return {"context": ctx, "feasibility": None, "candidates": [], "best": None,
                "selection": selection_summary([], near_tie_threshold),
                "coverage": cov0, "family_ranges": [], "twin_compatibility": twin_compat,
                "global_achievable": {"pd_min": None, "pd_max": None},
                "reference_context_status": "unknown",
                "global_design_space_status": "unknown", "status": status}
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
    cov["chemistry_ambiguous"] = ctx.chemistry_resolution_status in ("ambiguous", "material_only")
    cov["chemistry_incomplete"] = ctx.chemistry_resolution_status != "fully_specified"
    cov["twin_chemistry_unverified"] = not twin_compat.compatible
    cov["safe_for_quantitative_use"] = bool(
        twin_compat.safe_for_quantitative_comparison and not cov["fallback_dependent_result"])
    return {"context": ctx, "twin_compatibility": twin_compat, "feasibility": feas, "candidates": ranked, "best": best,
            "selection": sel, "coverage": cov,
            "family_ranges": fam_ranges,
            "global_achievable": {"pd_min": g_lo, "pd_max": g_hi},
            "reference_context_status": reference_context_status,
            "global_design_space_status": global_design_space_status,
            "status": "designed" if best else "no_feasible_candidate"}



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


def render_report(result, out_path=None):
    """The single canonical M2 report. One renderer, one schema, all result states:
    feasible reference + feasible global, infeasible reference + feasible global, and
    globally infeasible. `out_path` lets tests render in memory / tmp_path without
    creating a second committed artifact."""
    ctx, feas, cov = result["context"], result["feasibility"], result["coverage"]
    if feas is None:                       # chemistry unresolved: nothing was inverted
        feas = {"pd_min": None, "pd_max": None, "ratio": None, "verdict": "unknown",
                "effective_dose_bounds": None, "target_pd": ctx.value("target_pd"),
                "ratio_source": "unresolved"}
    cands, best, sel = result["candidates"], result["best"], result["selection"]
    ref_status, glob_status = result["reference_context_status"], result["global_design_space_status"]
    g = result["global_achievable"]
    tgt = ctx.value("target_pd")

    fb_dep = cov["fallback_dependent_result"]
    subtitle = (f"Current execution: {cov['level']} knowledge coverage, "
                f"{'fallback-dependent' if fb_dep else 'not fallback-dependent'}")

    # 1 request
    req = ctx.request
    s1 = (f"<table><tr><th>field</th><th>value</th></tr>"
          f"<tr><td class=mono>material</td><td class=mono>{html.escape(str(req.material))}</td></tr>"
          f"<tr><td class=mono>target_pd</td><td class=mono>{_pd(tgt)} µm</td></tr>"
          f"<tr><td class=mono>constraints</td><td class=mono>"
          f"{html.escape(json.dumps(req.constraints or {}))}</td></tr></table>")

    # 2 deposited material vs process chemistry ------------------------------
    cc = ctx.chemistry
    tc = result.get("twin_compatibility")
    alt_rows = "".join(
        f"<tr><td class=mono>{html.escape(a['label'])}</td>"
        f"<td class=mono>{a['n_experiments']}</td>"
        f"<td class=mut>{html.escape(', '.join(a['papers']) or '—')}</td>"
        f"<td>{'<span class=ok>resolved</span>' if a['resolved'] else '<span class=bad>no chemistry identified</span>'}</td></tr>"
        for a in (ctx.chemistry_alternatives or []))
    st_cls = {"fully_specified": "ok", "partially_specified": "warn",
              "ambiguous": "bad", "material_only": "bad", "unsupported": "bad"}.get(
        ctx.chemistry_resolution_status, "warn")
    tc_level = tc.compatibility_level if tc else "unknown"
    schem = (f"<div class=note><b>The deposited material does not uniquely determine the "
             f"precursor chemistry.</b> Partial pressure, pulse time, the pressure-to-pulse "
             f"relationship and the kinetic parameters belong to the CHEMISTRY, not to the "
             f"film. Priors below are scoped accordingly, and evidence from different "
             f"precursor/co-reactant systems is never combined.</div>"
             f"<div class=bar>"
             f"<div class=stat><b>{html.escape(str(ctx.value('deposited_material')))}</b>"
             f"<span>deposited material (the film)</span></div>"
             f"<div class=stat><b>{html.escape(str(cc.precursor_identity or '—'))}</b>"
             f"<span>precursor {_tag(ctx.priors['precursor'].source)}</span></div>"
             f"<div class=stat><b>{html.escape(str(cc.co_reactant_identity or '—'))}</b>"
             f"<span>co-reactant {_tag(ctx.priors['co_reactant'].source)}</span></div>"
             f"<div class=stat><b class={st_cls}>{html.escape(ctx.chemistry_resolution_status)}</b>"
             f"<span>chemistry_resolution_status</span></div>"
             f"<div class=stat><b class={'ok' if tc_level=='exact_chemistry' else 'bad'}>"
             f"{html.escape(tc_level)}</b><span>twin-chemistry compatibility</span></div>"
             f"</div>"
             f"<table><tr><th>KB chemistry alternative for this film</th><th>experiments</th>"
             f"<th>papers</th><th>status</th></tr>{alt_rows}</table>"
             + (f"<div class=note><b>Chemistry-scoped operating priors</b><table>"
                f"<tr><th>prior</th><th>value</th><th>species</th><th>source</th>"
                f"<th>match quality</th><th>evidence</th></tr>"
                + "".join(
                    f"<tr><td class=mono>{html.escape(k)}</td><td class=mono>{_fmt(v.value)}</td>"
                    f"<td class=mono>{html.escape(str(v.species_scope))}</td>"
                    f"<td>{_tag(v.source)}</td><td class=mono>{html.escape(v.match_quality)}</td>"
                    f"<td class=mut>{html.escape(v.evidence or '')}</td></tr>"
                    for k, v in (ctx.chemistry_priors or {}).items())
                + "</table></div>")
             + (f"<div class=note><span class=warn>⚠</span> ratio status: "
                f"<span class=mono>{html.escape(str(ctx.ratio_status))}</span></div>"
                if ctx.ratio_status else "")
             + (f"<div class=note><span class=bad>Twin parameterisation:</span> "
                f"{html.escape(tc.evidence or '')} — <b>safe for quantitative "
                f"cross-chemistry comparison: {'yes' if tc.safe_for_quantitative_comparison else 'no'}"
                f"</b>.</div>" if tc else ""))

    # 3 input support SUMMARY — aggregate + risk only. No per-variable ledger here;
    # that is section 3's job, and duplicating it was what made the two sections
    # indistinguishable to a reader.
    lvl_cls = {"complete": "ok", "substantial": "ok",
               "partial": "warn", "insufficient": "bad"}.get(cov["level"], "warn")
    crit = cov["critical_by_source"]

    def crit_line(bucket, label, cls):
        items = crit.get(bucket) or []
        if not items:
            return ""
        names = ", ".join(f"<span class=mono>{html.escape(c['name'])}</span>" for c in items)
        return f"<tr><td>{_tag(bucket)}</td><td>{names}</td><td class=mut>{label}</td></tr>"

    crit_rows = "".join([
        crit_line("user", "stated in the request", "ok"),
        crit_line("kb", "retrieved evidence", "ok"),
        crit_line("model_supported", "operating-envelope default", "warn"),
        crit_line("fallback", "stand-in — no evidence retrieved", "bad"),
        crit_line("unresolved", "no value at all", "bad")])
    weak_rows = "".join(
        f"<li><span class=mono>{html.escape(c['name'])}</span> — {html.escape(c['why'])}</li>"
        for c in cov["critical_weak"]) or "<li>none</li>"
    s2 = (f"<div class=note>This summary highlights the evidence gaps that affect the design. "
          f"The following ledger records every resolved input and its provenance.</div>"
          f"<div class=bar>"
          f"<div class=stat><b class={lvl_cls}>{cov['level']}</b><span>overall input support</span></div>"
          f"<div class=stat><b class={'bad' if fb_dep else 'ok'}>{'yes' if fb_dep else 'no'}</b>"
          f"<span>fallback-dependent result</span></div>"
          f"<div class=stat><b>{cov['counts']['user']} · {cov['counts']['kb']} · "
          f"{cov['counts']['model_supported']} · {cov['counts']['fallback']} · "
          f"{cov['counts']['unresolved']}</b>"
          f"<span>all resolved inputs — user · KB · model · fallback · unresolved</span></div>"
          f"</div>"
          f"<div class=note><b>Decision-critical inputs</b> — those that materially affect the "
          f"selected family, the solved pressure and pulse time, the effective dose, feasibility "
          f"or the ranking. A raw source count does not capture this: an input can be "
          f"KB-supported and still never reach the solve.</div>"
          f"<table><tr><th>support</th><th>decision-critical inputs</th><th></th></tr>"
          f"{crit_rows}</table>"
          f"<div class=note><b>Unsupported or fallback-supported where it matters:</b>"
          f"<ul>{weak_rows}</ul></div>"
          + (f"<div class=note><span class=bad>critical unresolved:</span> <span class=mono>"
             f"{html.escape(', '.join(cov['critical_unresolved']))}</span></div>"
             if cov["critical_unresolved"] else "")
          + f"<div class=note><b>{html.escape(cov['interpretation'])}</b></div>")

    # 3 the ONE detailed ledger: every resolved input, with provenance and downstream use
    def use_of(name):
        if name in DECISION_CRITICAL:
            return DECISION_CRITICAL[name]
        return NON_CRITICAL_NOTE.get(name, "")

    prows = "".join(
        f"<tr><td class=mono>{html.escape(k)}</td><td class=mono>{_fmt(p.value)}</td>"
        f"<td class=mut>{html.escape(p.unit or '')}</td><td>{_tag(p.source)}</td>"
        f"<td class=mono>{p.confidence:.1f}</td>"
        f"<td>{'<b>critical</b>' if k in DECISION_CRITICAL else '<span class=mut>context</span>'}</td>"
        f"<td class=mut>{html.escape(use_of(k))}</td>"
        f"<td class=mut>{html.escape(p.evidence or '')}</td>"
        f"<td class=mut>{'yes' if p.overridable else 'no'}</td></tr>"
        for k, p in ctx.priors.items())
    s34 = (f"<div class=note>The complete audit record — every value that entered the "
           f"calculation and where it came from. The summary above reports only the gaps that "
           f"change the design.</div>"
           f"<table><tr><th>variable</th><th>value</th><th>unit</th><th>source</th><th>conf</th>"
           f"<th>role</th><th>downstream use</th><th>evidence</th><th>overridable</th></tr>"
           f"{prows}</table>"
           + "".join(f'<div class=note><span class=warn>⚠</span> {html.escape(w)}</div>'
                     for w in ctx.warnings)
           + (f'<div class=note><b>Unresolved inputs (complete list):</b> <span class=mono>'
              f'{html.escape(", ".join(ctx.unresolved))}</span></div>' if ctx.unresolved else "")
           + '<div class=note><span class="tag s-user">user</span> stated in the request · '
             '<span class="tag s-kb">kb</span> retrieved from the knowledge base · '
             '<span class="tag s-model_supported">model_supported</span> operating-envelope default · '
             '<span class="tag s-fallback">fallback</span> nothing retrieved, a stand-in · '
             '<span class="tag s-unresolved">unresolved</span> no value at all.</div>')

    # 5 reference-context feasibility
    ref_cls = "ok" if ref_status == "feasible" else "bad"
    ratio_lbl = (f"{feas['ratio']:.4g} Pa/s" if feas.get("ratio") else "— (unresolved)")
    s5 = (f"<div class=bar>"
          f"<div class=stat><b class={ref_cls}>{ref_status}</b><span>reference_context_status</span></div>"
          f"<div class=stat><b>{_pd(feas['pd_min'])} – {_pd(feas['pd_max'])}</b>"
          f"<span>achievable PD50 (µm) at the reference ratio {ratio_lbl}</span></div>"
          f"<div class=stat><b>{_pd(tgt)}</b><span>target PD50 (µm)</span></div></div>"
          f"<div class=note>Feasibility of the <b>resolved reference ratio alone</b>. It is not the "
          f"design's verdict — see the status across evaluated families below.</div>")

    # 6 global operating-family feasibility
    frows = "".join(
        f"<tr><td class=mono>{html.escape(r['family'])}</td><td class=mono>{r['ratio']:.4g}</td>"
        f"<td class=mono>{_pd(r['pd_min'])}</td><td class=mono>{_pd(r['pd_max'])}</td>"
        f"<td class=mono>{_fmt(r['bounds'])}</td>"
        f"<td class={'ok' if (tgt is not None and r['pd_min'] is not None and r['pd_min'] <= tgt <= r['pd_max']) else 'bad'}>"
        f"{'reaches target' if (tgt is not None and r['pd_min'] is not None and r['pd_min'] <= tgt <= r['pd_max']) else 'cannot reach'}</td></tr>"
        for r in result["family_ranges"])
    glob_cls = "ok" if glob_status == "feasible" else "bad"
    cross = ""
    if ref_status != "feasible" and glob_status == "feasible":
        cross = ('<div class=note><span class=ok><b>The resolved reference context cannot reach the '
                 'target, but at least one alternative operating family can.</b></span> The design is '
                 'therefore <b>feasible across the evaluated operating families</b>; the '
                 'alternative family expands the achievable envelope beyond the reference '
                 'ratio\'s own range.</div>')
    elif glob_status.startswith("infeasible"):
        cross = ('<div class=note><span class=bad><b>None of the evaluated operating families reaches the '
                 'target.</b>'
                 '</span> The binding constraints are the pressure and pulse-time bounds, which cap the '
                 'effective dose available at every ratio — see the per-family brackets above.</div>')
    s6 = (f"<div class=note>This is the union over the <b>{len(result['family_ranges'])} operating "
          f"families evaluated here</b> — a finite set of fixed pA/t_p ratios. The continuous "
          f"pressure x pulse-time domain has <b>not</b> been searched; a ratio between or beyond "
          f"these families could widen the envelope.</div>"
          f"<div class=bar>"
          f"<div class=stat><b class={glob_cls}>{glob_status}</b>"
          f"<span>status across evaluated families "
          f"(field: <span class=mono>global_design_space_status</span>)</span></div>"
          f"<div class=stat><b>{_pd(g['pd_min'])} – {_pd(g['pd_max'])}</b>"
          f"<span>achievable PD50 envelope (µm) across the evaluated operating families</span></div></div>"
          f"<table><tr><th>family</th><th>r (Pa/s)</th><th>PD min (µm)</th><th>PD max (µm)</th>"
          f"<th>effective-dose bracket (Pa·s)</th><th>vs target</th></tr>{frows}</table>{cross}")

    # 7 candidates
    def crow(c):
        prov = (f"<td>{_tag(c.family_definition_source)}</td>"
                f"<td>{_tag(c.ratio_evidence_source)}</td>"
                f"<td class=mono>{c.ratio_evidence_confidence:.2f}</td>")
        if not c.feasible:
            return (f"<tr><td class=mono>{html.escape(c.family)}</td><td class=mono>{c.ratio:.4g}</td>"
                    f"{prov}<td colspan=6 class=bad>rejected — {html.escape(c.rejected or '')}</td></tr>")
        s, rb = c.solution, c.robustness
        star = " ★" if c is best else ""
        return (f"<tr><td class=mono><b>{html.escape(c.family)}{star}</b></td>"
                f"<td class=mono>{c.ratio:.4g}</td>{prov}"
                f"<td class=mono>{_fmt(s.effective_dose)}</td><td class=mono>{_fmt(s.pA)}</td>"
                f"<td class=mono>{_fmt(s.pulse_time)}</td><td class=mono>{_pd(s.achieved_pd)}</td>"
                f"<td class=mono>{(s.residual or 0)*1e9:+.2g}</td>"
                f"<td class=mono><b>{c.total_score:.3f}</b></td></tr>")
    crow_all = "".join(crow(c) for c in cands)
    s7 = (f"<table><tr><th>family</th><th>r (Pa/s)</th><th>family definition</th>"
          f"<th>ratio evidence</th><th>ratio conf</th><th>effective dose (Pa·s)</th><th>pA (Pa)</th>"
          f"<th>t_p (s)</th><th>PD50 (µm)</th><th>resid (nm)</th><th>score</th></tr>{crow_all}</table>"
          f"<div class=note><b>Two separate provenance columns, on purpose.</b> "
          f"<i>family definition</i> is where the operating archetype came from; "
          f"<i>ratio evidence</i> is what supports the actual number. A family scaled off the "
          f"reference ratio reads <span class=mono>derived_from_…</span> and can never be more "
          f"credible than its base — multiplying a fallback by ten does not create evidence.</div>")

    # 8 + 9 + 10 ranking, selection, trade-off
    wrow = " · ".join(f"{k} {v:g}" for k, v in sel["weights"].items())
    srows = "".join(
        f"<tr><td class=mono>{html.escape(c.family)}</td>" +
        "".join(f"<td class=mono>{c.scores.get(k, 0):.3f}</td>"
                for k in ("accuracy", "margin", "robustness", "throughput", "confidence")) +
        f"<td class=mono><b>{c.total_score:.3f}</b></td></tr>"
        for c in cands if c.feasible) or '<tr><td colspan=7 class=mut>no feasible candidate</td></tr>'
    trades = "".join(
        f"<li><b>{html.escape(t['label'])}</b> favours <span class=mono>{html.escape(t['favours'])}</span>"
        f" ({t['best']:.3f} vs {t['runner_up']:.3f})</li>" for t in sel["trade_offs"])
    tie = ('<div class=note><span class=warn>⚠ near-tie</span> — the top two scores differ by '
           f'{sel["score_gap"]:.3f}, below the {sel["near_tie_threshold"]:.2f} threshold. '
           'Treat these as equally preferred; the ordering is not decisive.</div>'
           if sel["near_tie"] else "")
    s89 = (f"<div class=note><b>Ranking profile:</b> <span class=mono>{html.escape(sel['profile'])}</span>"
           f" — weights: <span class=mono>{html.escape(wrow)}</span></div>"
           f"<table><tr><th>family</th><th>accuracy</th><th>margin</th><th>robustness</th>"
           f"<th>throughput</th><th>confidence</th><th>total</th></tr>{srows}</table>{tie}")

    if best:
        s10 = (f"<div class=bar>"
               f"<div class=stat><b>{best.solution.effective_dose:.4g}</b>"
               f"<span>effective dose (Pa·s) = pA · t_p</span></div>"
               f"<div class=stat><b>{best.solution.pA:.4g}</b><span>precursor partial pressure (Pa)</span></div>"
               f"<div class=stat><b>{best.solution.pulse_time:.4g}</b><span>pulse time (s)</span></div>"
               f"<div class=stat><b>{_pd(best.solution.achieved_pd)}</b><span>predicted PD50 (µm)</span></div>"
               f"<div class=stat><b>{html.escape(best.family)}</b><span>operating family</span></div></div>"
               f"<div class=note><b>Runner-up:</b> "
               f"<span class=mono>{html.escape(str(sel['runner_up']))}</span>"
               + (f", score gap {sel['score_gap']:.3f}." if sel["score_gap"] is not None
                  else " — none (only one feasible candidate).")
               + (f"<ul>{trades}</ul>" if trades else "")
               + f"<b>{html.escape(sel['note'])}</b></div>"
               f"<div class=note>This is a <b>model-inverted</b> recipe under a "
               f"{_tag(ctx.priors['ratio'].source)} pressure-to-pulse relationship. "
               f"{'It is not a literature recipe.' if fb_dep else ''}</div>")
    else:
        near = max((r for r in result["family_ranges"] if r["pd_max"] is not None),
                   key=lambda r: r["pd_max"], default=None)
        s10 = ('<div class=note><span class=bad><b>No candidate is selected.</b></span> '
               'No operating family reaches the target, so there is no recipe to recommend.</div>'
               + (f'<div class=note>Closest attainable boundary: family '
                  f'<span class=mono>{html.escape(near["family"])}</span> tops out at '
                  f'<b>{_pd(near["pd_max"])} µm</b> — <span class=bad>this does NOT satisfy the '
                  f'target</span> and is shown only to indicate how far short the design space '
                  f'falls.</div>' if near else ""))

    # 11 robustness
    rrows = "".join(
        f"<tr><td class=mono>{html.escape(c.family)}</td>"
        f"<td class=mono>{c.robustness.get('dose_sensitivity', float('nan')):.3f}</td>"
        f"<td class=mono>{c.robustness.get('ratio_sensitivity', float('nan')):.3f}</td>"
        f"<td class=mono>{c.robustness.get('pressure_margin', float('nan')):.3f}</td>"
        f"<td class=mono>{c.robustness.get('pulse_time_margin', float('nan')):.3f}</td>"
        f"<td class=mono>{c.robustness.get('dose_margin', float('nan')):.3f}</td>"
        f"<td class=mono>{_pd(c.robustness.get('pd_at_minus'))} / {_pd(c.robustness.get('pd_at_plus'))}</td></tr>"
        for c in cands if c.feasible) or '<tr><td colspan=7 class=mut>no feasible candidate</td></tr>'
    s11 = (f"<table><tr><th>family</th><th>d ln PD / d ln dose</th><th>ratio sensitivity</th>"
           f"<th>pA margin</th><th>t_p margin</th><th>dose margin</th>"
           f"<th>PD at ∓10 % dose (µm)</th></tr>{rrows}</table>"
           f"<div class=note>Margins are distance from the operating bounds in log space "
           f"(0 = on a bound, 1 = centred). Sensitivities are local, at ±10 %.</div>")

    # 12 reproducibility / solver diagnostics
    drows = "".join(
        f"<tr><td class=mono>{html.escape(c.family)}</td>"
        f"<td class=mono>{html.escape(c.solution.status)}</td>"
        f"<td class=mono>{html.escape(str(c.solution.method or '—'))}</td>"
        f"<td class=mono>{c.solution.model_evaluations}</td>"
        f"<td class=mono>{_fmt(c.solution.effective_dose_bounds)}</td>"
        f"<td class=mono>{c.solution.tolerance_pd:.1g}</td>"
        f"<td class=mut>{html.escape((c.solution.reason or '')[:90])}</td></tr>"
        for c in cands if c.solution)
    s12 = (f"<table><tr><th>family</th><th>solver status</th><th>method</th><th>model evals</th>"
           f"<th>effective-dose bracket (Pa·s)</th><th>PD tol (m)</th><th>reason</th></tr>{drows}</table>"
           f"<div class=note>Physics inversion is performed exclusively by "
           f"<span class=mono>inverse_solver.solve_target_dose</span> — one bracketed root solve per "
           f"family on the real channel twin. This layer adds no solver of its own.</div>")

    def card(n, title, body):
        return f"<div class=card><h2>{n} · {html.escape(title)}</h2>{body}</div>"

    body = f"""<title>M2 · knowledge-aware inverse design</title><style>{_CSS}</style>
<div class=wrap>
<div class=eyebrow>PSED · M2</div>
<h1>M2 · knowledge-aware inverse design</h1>
<div class=sub>{html.escape(subtitle)}</div>
{card(1, "Design request", s1)}
{card(2, "Deposited material vs process chemistry", schem)}\n{card(3, "Input support summary", s2)}
{card(4, "Resolved context and provenance ledger", s34)}
{card(5, "Reference-context feasibility", s5)}
{card(6, "Feasibility across evaluated operating families", s6)}
{card(7, "Candidate recipes", s7)}
{card(8, "Ranking profile and weights", s89)}
{card(9, "Selected under the current ranking profile", s10)}
{card(10, "Robustness analysis", s11)}
{card(11, "Reproducibility and solver diagnostics", s12)}
</div>"""
    if out_path is None:
        out_path = HERE / CANONICAL_REPORT
    out = Path(out_path)
    out.write_text(body)
    return out


def main():
    """Canonical M2 run: the 60 µm primary example -> m2_report.html (the ONE artifact)."""
    # Canonical example: chemistry is stated explicitly, because the deposited
    # material alone does not identify it. The fallback opt-in is required because the
    # corpus has no species-attributed precursor pressure — the report says so.
    res = design(DesignRequest(material="Al2O3", target_pd=60e-6,
                               precursor="TMA", co_reactant="H2O",
                               allow_chemistry_fallback=True))
    out = render_report(res)
    ctx, cov, sel = res["context"], res["coverage"], res["selection"]
    print(f"wrote {out}   (canonical M2 report)")
    cc, tc = ctx.chemistry, res["twin_compatibility"]
    print(f"  chemistry                 = {cc.label} [{ctx.chemistry_resolution_status}] "
          f"src={cc.chemistry_source}")
    print(f"  ratio                     = {ctx.priors['ratio'].source} "
          f"(ratio_status={ctx.ratio_status})")
    print(f"  twin chemistry compat     = {tc.compatibility_level} "
          f"(safe for quantitative use: {cov.get('safe_for_quantitative_use')})")
    print(f"  reference_context_status  = {res['reference_context_status']}")
    print(f"  global_design_space_status= {res['global_design_space_status']}")
    print(f"  global achievable PD      = {_pd(res['global_achievable']['pd_min'])}"
          f"–{_pd(res['global_achievable']['pd_max'])} µm")
    print(f"  knowledge coverage        = {cov['level']} "
          f"(kb={cov['kb_supported']} user={cov['user_provided']} "
          f"model={cov['model_supported_defaults']} fallback={cov['fallback_inputs']}); "
          f"fallback-dependent={cov['fallback_dependent_result']}")
    for c in res["candidates"]:
        tag = (f"{c.family_definition_source}/{c.ratio_evidence_source}"
               f"@{c.ratio_evidence_confidence:.2f}")
        if c.feasible:
            s = c.solution
            print(f"  {c.family:20} r={c.ratio:<9.4g} [{tag:48}] score={c.total_score:.3f} "
                  f"effective_dose={s.effective_dose:.4g} pA={s.pA:.4g} t_p={s.pulse_time:.4g} "
                  f"-> {s.achieved_pd*1e6:.3f} µm")
        else:
            print(f"  {c.family:20} r={c.ratio:<9.4g} [{tag:48}] rejected: {c.solution.status}")
    print(f"  selected={sel['selected']} runner_up={sel['runner_up']} "
          f"gap={sel['score_gap'] if sel['score_gap'] is None else round(sel['score_gap'], 4)} "
          f"near_tie={sel['near_tie']} profile={sel['profile']}")


if __name__ == "__main__":
    main()
