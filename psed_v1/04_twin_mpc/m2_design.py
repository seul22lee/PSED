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
    """What a user actually asks for — deliberately underspecified."""
    material: str = "Al2O3"
    target_pd: float = None                       # m
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

    def value(self, name, default=None):
        p = self.priors.get(name)
        return default if p is None or p.value is None else p.value

    def to_dict(self):
        return {"request": self.request.to_dict() if self.request else None,
                "priors": {k: v.to_dict() for k, v in self.priors.items()},
                "warnings": self.warnings, "unresolved": self.unresolved}


@dataclass
class Candidate:
    """One operating family, inverted. `solution` is the solver's DoseSolution."""
    family: str
    ratio: float
    ratio_source: str
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
# inversion the solver already handles. These are model-supported operating
# archetypes, NOT literature values — sources say so.
OPERATING_FAMILIES = (
    ("long_low_pressure", 100.0, "low pA, long pulse — gentle, precursor-lean"),
    ("balanced", 1000.0, "reference operating family (also the ratio fallback)"),
    ("short_high_pressure", 10000.0, "high pA, short pulse — throughput-oriented"),
)

PA_BOUNDS_DEFAULT, TP_BOUNDS_DEFAULT = (1.0, 200.0), (0.01, 5.0)


def resolve_context(request, warm_start_fn=None):
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

    # --- pA/tp ratio -----------------------------------------------------------
    w = None
    if "ratio" in c and c["ratio"]:
        ctx.priors["ratio"] = Prior.make("ratio", float(c["ratio"]), "Pa/s", "user",
                                         evidence="explicit user constraint")
    else:
        try:
            w = (warm_start_fn or kb_bridge.warm_start)(request.material,
                                                        target={"aspect_ratio": 30})
        except Exception as e:                       # KB unavailable is not fatal
            ctx.warnings.append(f"warm start unavailable ({type(e).__name__}: {e})")
            w = None
        r_star = (w or {}).get("r_star")
        if r_star:
            prov = (w or {}).get("provenance", {})
            ctx.priors["ratio"] = Prior.make(
                "ratio", float(r_star), "Pa/s", "kb",
                evidence=f"pA0/tp0 from {prov.get('nearest')} (similarity {prov.get('similarity')})")
        else:
            # The KB resolves no precursor partial pressure, so no ratio can be
            # derived from literature. Say so rather than dressing the default up.
            prov = (w or {}).get("provenance", {})
            ctx.priors["ratio"] = Prior.make(
                "ratio", 1000.0, "Pa/s", "fallback",
                evidence=("no KB precursor partial pressure for this query "
                          f"(pA0_source={prov.get('pA0_source', 'none')}, "
                          f"tp0_source={prov.get('tp0_source', 'none')}); "
                          "using the reference operating-family default"))
            ctx.warnings.append(
                "pA/tp ratio is a FALLBACK operating-family default, not literature-derived")
            ctx.unresolved.append("ratio_from_literature")

    # --- reference exposure (literature, when available) -----------------------
    pA0, tp0 = (w or {}).get("pA0"), (w or {}).get("tp0")
    if pA0 and tp0:
        ctx.priors["reference_effective_dose"] = Prior.make(
            "reference_effective_dose", pA0 * tp0, "Pa·s", "kb",
            evidence=f"pA0={pA0} Pa x tp0={tp0} s from the KB warm start")
    else:
        ctx.priors["reference_effective_dose"] = Prior.make(
            "reference_effective_dose", None, "Pa·s", "unresolved",
            evidence=f"needs both pA0 and tp0 (have pA0={pA0!r}, tp0={tp0!r})")
        if tp0 and not pA0:
            ctx.priors["reference_pulse_time"] = Prior.make(
                "reference_pulse_time", tp0, "s", "kb",
                evidence="KB pulse-time estimate; no matching partial pressure")

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
    model = model or _model(ctx.value("material"))
    ratio = ctx.value("ratio")
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
    ratio_prior = ctx.priors["ratio"]
    if ratio_prior.source == "user":
        families = (("user_specified", ratio_prior.value, "ratio pinned by the caller"),)

    out = []
    for name, ratio, _desc in families:
        src = "user" if ratio_prior.source == "user" else (
            "kb" if (ratio_prior.source == "kb" and abs(ratio - ratio_prior.value) < 1e-12)
            else "model_supported")
        cand = Candidate(family=name, ratio=float(ratio), ratio_source=src)
        if tgt is None:
            cand.rejected = "no target_pd resolved"
            out.append(cand); continue
        cand.solution = inverse_solver.solve_target_dose(
            mk(), tgt, float(ratio),
            dose_bounds=ctx.value("effective_dose_bounds"),
            pressure_bounds=ctx.value("pressure_bounds"),
            pulse_time_bounds=ctx.value("pulse_time_bounds"),
            reference={"effective_dose": ctx.value("reference_effective_dose")},
            provenance={"ratio_source": src, "family": name,
                        "bounds_source": ctx.priors["pressure_bounds"].source})
        if not cand.solution.feasible:
            cand.rejected = f"{cand.solution.status}: {cand.solution.reason}"
        out.append(cand)
    return out


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


def rank_candidates(cands, ctx):
    """Score feasible candidates. Every term is physically motivated and reported:

      accuracy    residual against the target (should be ~0 for all — a tie-breaker
                  only, kept so a degraded solve cannot silently win)
      margin      distance of pA / t_p / exposure from their bounds (log-space)
      robustness  insensitivity of the achieved PD to ±10 % exposure and ratio error
      throughput  shorter pulses are cheaper per cycle
      confidence  how well-grounded the ratio behind this candidate is
    """
    W = {"accuracy": 0.15, "margin": 0.25, "robustness": 0.25,
         "throughput": 0.15, "confidence": 0.20}
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
        conf = CONFIDENCE.get(c.ratio_source, 0.0)
        c.scores = {"accuracy": acc, "margin": margin, "robustness": robust,
                    "throughput": thr, "confidence": conf, "weights": W}
        c.total_score = sum(W[k] * c.scores[k] for k in W)
    return sorted(cands, key=lambda c: (-c.total_score, c.family))


def design(request, model_factory=None, warm_start_fn=None, families=OPERATING_FAMILIES):
    """Full pipeline. Returns a dict carrying every stage's output."""
    ctx = resolve_context(request, warm_start_fn=warm_start_fn)
    mk = model_factory or (lambda: _model(ctx.value("material")))
    feas = assess_feasibility(ctx, model=mk())
    cands = generate_candidates(ctx, families=families, model_factory=mk)
    for c in cands:
        c.robustness = analyse_robustness(c, ctx, model_factory=mk)
    ranked = rank_candidates(cands, ctx)
    best = next((c for c in ranked if c.feasible), None)
    return {"context": ctx, "feasibility": feas, "candidates": ranked, "best": best,
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


def render_report(result, out_path=None, title="M2 · knowledge-guided design"):
    """Write the provenance-rich HTML report. Every number states where it came from;
    nothing is presented as literature-derived unless its prior says so."""
    ctx, feas = result["context"], result["feasibility"]
    cands, best = result["candidates"], result["best"]

    prows = "".join(
        f"<tr><td class=mono>{html.escape(k)}</td><td class=mono>{_fmt(p.value)}</td>"
        f"<td class=mut>{html.escape(p.unit or '')}</td><td>{_tag(p.source)}</td>"
        f"<td class=mono>{p.confidence:.1f}</td>"
        f"<td class=mut>{html.escape(p.evidence or '')}</td>"
        f"<td class=mut>{'yes' if p.overridable else 'no'}</td></tr>"
        for k, p in ctx.priors.items())

    def crow(c):
        if not c.feasible:
            return (f"<tr><td class=mono>{html.escape(c.family)}</td>"
                    f"<td class=mono>{_fmt(c.ratio)}</td><td>{_tag(c.ratio_source)}</td>"
                    f"<td colspan=7 class=bad>rejected — {html.escape(c.rejected or '')}</td></tr>")
        s, rb = c.solution, c.robustness
        star = " ★" if c is best else ""
        return (f"<tr><td class=mono><b>{html.escape(c.family)}{star}</b></td>"
                f"<td class=mono>{_fmt(c.ratio)}</td><td>{_tag(c.ratio_source)}</td>"
                f"<td class=mono>{_fmt(s.effective_dose)}</td><td class=mono>{_fmt(s.pA)}</td>"
                f"<td class=mono>{_fmt(s.pulse_time)}</td>"
                f"<td class=mono>{s.achieved_pd*1e6:.3f}</td>"
                f"<td class=mono>{(s.residual or 0)*1e9:+.2g}</td>"
                f"<td class=mono>{rb.get('dose_sensitivity', float('nan')):.3f}</td>"
                f"<td class=mono><b>{c.total_score:.3f}</b></td></tr>")

    crows = "".join(crow(c) for c in cands)
    sc = ("".join(f"<tr><td class=mono>{html.escape(c.family)}</td>" +
                  "".join(f"<td class=mono>{c.scores.get(k, 0):.3f}</td>"
                          for k in ("accuracy", "margin", "robustness", "throughput", "confidence"))
                  + f"<td class=mono><b>{c.total_score:.3f}</b></td></tr>"
                  for c in cands if c.feasible)) or \
         '<tr><td colspan=7 class=mut>no feasible candidate</td></tr>'

    warn_html = "".join(f'<div class=note><span class=warn>⚠</span> {html.escape(w)}</div>'
                        for w in ctx.warnings)
    unres = (f'<div class=note><span class=bad>unresolved:</span> '
             f'<span class=mono>{html.escape(", ".join(ctx.unresolved))}</span></div>'
             if ctx.unresolved else "")

    tgt = feas["target_pd"]
    verdict_cls = {"within_range": "ok", "above_range": "bad",
                   "below_range": "bad", "unknown": "warn"}[feas["verdict"]]
    # the resolved-ratio verdict and the candidate outcome can legitimately disagree
    cross_note = ""
    if feas["verdict"] != "within_range" and best is not None:
        cross_note = (f' <span class=ok>Here that happened:</span> the target is outside the range at '
                      f'r = {feas["ratio"]:.4g} Pa/s, but the <span class=mono>'
                      f'{html.escape(best.family)}</span> family reaches it.')
    elif feas["verdict"] == "within_range" and best is None:
        cross_note = (' <span class=bad>Note:</span> the target is inside the resolved-ratio range, '
                      'yet no family produced a feasible recipe within its own operating bounds.')
    best_html = (
        f'<div class=bar>'
        f'<div class=stat><b>{best.solution.effective_dose:.4g}</b><span>effective dose (Pa·s) = pA · t_p</span></div>'
        f'<div class=stat><b>{best.solution.pA:.4g}</b><span>precursor partial pressure (Pa)</span></div>'
        f'<div class=stat><b>{best.solution.pulse_time:.4g}</b><span>pulse time (s)</span></div>'
        f'<div class=stat><b>{best.solution.achieved_pd*1e6:.3f}</b><span>predicted PD50 (µm)</span></div>'
        f'<div class=stat><b>{best.family}</b><span>operating family</span></div>'
        f'</div>'
        if best else
        f'<div class=note><span class=bad>No feasible candidate.</span> '
        f'Every operating family was rejected — see the table.</div>')

    body = f"""<title>{html.escape(title)}</title><style>{_CSS}</style>
<div class=wrap>
<div class=eyebrow>PSED · M2</div>
<h1>{html.escape(title)}</h1>
<div class=sub>An underspecified request is completed from priors, checked against the digital twin,
inverted into candidate recipes, ranked, and stress-tested. The physics inversion is done by
<span class=mono>inverse_solver.solve_target_dose</span> — a bracketed root solve on the real channel
twin — once per operating family.</div>

<div class=card><h2>1 · Request &amp; resolved design context</h2>
<table><tr><th>prior</th><th>value</th><th>unit</th><th>source</th><th>conf</th><th>evidence</th><th>overridable</th></tr>
{prows}</table>{warn_html}{unres}
<div class=note><b>Reading the sources.</b> <span class="tag s-user">user</span> stated in the request ·
<span class="tag s-kb">kb</span> retrieved from the knowledge base ·
<span class="tag s-model_supported">model_supported</span> an operating-envelope default ·
<span class="tag s-fallback">fallback</span> nothing was retrieved, a default is standing in ·
<span class="tag s-unresolved">unresolved</span> no value at all. A fallback is <b>not</b> evidence.</div></div>

<div class=card><h2>2 · Digital-twin feasibility</h2>
<div class=bar>
 <div class=stat><b>{feas['pd_min']*1e6:.2f} – {feas['pd_max']*1e6:.2f}</b><span>achievable PD50 (µm) at r = {feas['ratio']:.4g} Pa/s</span></div>
 <div class=stat><b>{(tgt*1e6 if tgt else float('nan')):.2f}</b><span>target PD50 (µm)</span></div>
 <div class=stat><b class={verdict_cls}>{feas['verdict']}</b><span>verdict</span></div>
 <div class=stat><b>{_fmt(feas['effective_dose_bounds'])}</b><span>effective-dose bounds (Pa·s)</span></div>
</div>
<div class=note>The range is measured by evaluating the twin at both ends of the effective-dose bracket,
before any solving. A target outside it is reported as infeasible rather than iterated at.
<b>This verdict is for the resolved ratio only.</b> Each operating family has its own bracket and its
own achievable range, so section 3 may still find a feasible recipe at a different ratio — that is the
point of generating candidates rather than inverting once.{cross_note}</div></div>

<div class=card><h2>3 · Inverse candidates (one solve per operating family)</h2>
<table><tr><th>family</th><th>r (Pa/s)</th><th>ratio src</th><th>eff. dose (Pa·s)</th><th>pA (Pa)</th>
<th>t_p (s)</th><th>PD50 (µm)</th><th>resid (nm)</th><th>dose sens.</th><th>score</th></tr>
{crows}</table>
<div class=note>An operating family fixes r = pA/t_p, which is what makes the inversion one-dimensional.
The families are model-supported archetypes, not literature recipes. <b>dose sens.</b> is
d ln PD / d ln(effective dose) at ±10 %: lower is a more forgiving recipe.</div></div>

<div class=card><h2>4 · Ranking &amp; robustness</h2>
<table><tr><th>family</th><th>accuracy</th><th>margin</th><th>robustness</th><th>throughput</th>
<th>confidence</th><th>total</th></tr>{sc}</table>
<div class=note><b>accuracy</b> residual vs target · <b>margin</b> distance of pA / t_p / exposure from
their bounds · <b>robustness</b> insensitivity to ±10 % error in exposure and in the assumed ratio ·
<b>throughput</b> shorter pulses preferred · <b>confidence</b> how well-grounded that family's ratio is.
Weights: {html.escape(json.dumps({k: v for k, v in (cands[0].scores.get('weights', {}) if cands and cands[0].scores else {}).items()}))}</div></div>

<div class=card><h2>5 · Recommended operating point</h2>{best_html}
<div class=note>This is a <b>model-inverted</b> recipe under a
{_tag(ctx.priors['ratio'].source)} pressure-to-pulse ratio. It is not a literature recipe, and it is
only as good as the priors in section 1 — the ratio in particular.</div></div>
</div>"""
    out = Path(out_path or (HERE / "m2_design_report.html"))
    out.write_text(body)
    return out


def main():
    """Primary knowledge-guided example (60 µm) plus the infeasible-report path (200 µm)."""
    res = design(DesignRequest(material="Al2O3", target_pd=60e-6))
    out = render_report(res)
    ctx, f, best = res["context"], res["feasibility"], res["best"]
    print(f"wrote {out}")
    print(f"  context: ratio={ctx.value('ratio'):.4g} Pa/s [{ctx.priors['ratio'].source}] "
          f"| unresolved={ctx.unresolved or 'none'}")
    print(f"  feasibility: PD {f['pd_min']*1e6:.2f}–{f['pd_max']*1e6:.2f} µm, "
          f"target {f['target_pd']*1e6:.1f} µm -> {f['verdict']}")
    for c in res["candidates"]:
        if c.feasible:
            s = c.solution
            print(f"  {c.family:20} score={c.total_score:.3f} effective_dose={s.effective_dose:.4g} Pa·s "
                  f"pA={s.pA:.4g} Pa t_p={s.pulse_time:.4g} s -> PD {s.achieved_pd*1e6:.3f} µm "
                  f"({s.model_evaluations} evals)")
        else:
            print(f"  {c.family:20} rejected: {c.rejected}")
    if best:
        print(f"  recommended: {best.family} "
              f"(effective_dose={best.solution.effective_dose:.5g} Pa·s, "
              f"pA={best.solution.pA:.4g} Pa, t_p={best.solution.pulse_time:.4g} s)")
    inf = design(DesignRequest(material="Al2O3", target_pd=200e-6))
    print(f"\n  infeasible path (200 µm): status={inf['status']}, "
          f"verdict={inf['feasibility']['verdict']}, "
          f"statuses={[c.solution.status for c in inf['candidates'] if c.solution]}")
    render_report(inf, out_path=HERE / "m2_design_report_infeasible.html",
                  title="M2 · knowledge-guided design (infeasible target)")


if __name__ == "__main__":
    main()
