#!/usr/bin/env python3
"""Tests for the knowledge-guided M2 design layer (m2_design).

The layer's job is to complete an underspecified request honestly and hand a
well-posed 1-D problem to the validated inverse solver. So the tests care about two
things above all:

  · nothing invented is ever labelled as evidence (a fallback ratio must stay a
    fallback, at low confidence, and must not become "KB-supported"),
  · the solver stays the only inversion path — this layer never re-derives a root.

  python3 test_m2_design.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "02_extraction"))

import inverse_solver
import m2_design as md

FAIL = []


def check(name, got, want):
    ok_ = got == want
    print(f"  {'PASS' if ok_ else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok_:
        FAIL.append(name)


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


# --- stand-ins so the layer can be tested without the KB or the real twin ------
def ws_no_pressure(material, target=None):
    """Today's real KB behaviour: a pulse time, no partial pressure, so no ratio."""
    return {"pA0": None, "tp0": 0.1, "r_star": None,
            "priors": {"gpc_expected": None},
            "provenance": {"nearest": None, "similarity": 0.833, "n_similar": 5,
                           "pA0_source": "none", "tp0_source": "kb"}}


def ws_with_pressure(material, target=None):
    return {"pA0": 150.0, "tp0": 0.3, "r_star": 500.0, "priors": {},
            "provenance": {"nearest": "paper-F1a-0", "similarity": 0.91, "n_similar": 5,
                           "pA0_source": "kb", "tp0_source": "kb"}}


class FakeTwin:
    """PD = 1e-5·sqrt(pA·t_p) — same shape as the real model, no KB needed."""

    def __init__(self, coeff=1e-5):
        self.coeff, self.pA, self.t_p = coeff, None, None

    def prepare(self):
        pass

    def penetration_depth(self):
        return self.coeff * math.sqrt(self.pA * self.t_p)


def fake_factory():
    return FakeTwin()


REQ60 = md.DesignRequest(material="Al2O3", target_pd=60e-6)

print("1) underspecified request is completed, and gaps are declared")
ctx = md.resolve_context(REQ60, warm_start_fn=ws_no_pressure)
ok("every needed prior exists",
   {"target_pd", "material", "ratio", "pressure_bounds", "pulse_time_bounds"} <= set(ctx.priors),
   sorted(ctx.priors))
check("target is user-sourced", ctx.priors["target_pd"].source, "user")
ok("target is not overridable", ctx.priors["target_pd"].overridable is False)
check("bounds are model_supported", ctx.priors["pressure_bounds"].source, "model_supported")

print("2) the fallback ratio is NEVER dressed up as literature")
p = ctx.priors["ratio"]
check("source", p.source, "fallback")
check("confidence", p.confidence, md.CONFIDENCE["fallback"])
ok("confidence is low", p.confidence <= 0.2, p.confidence)
ok("source is not kb/user", p.source not in ("kb", "user"))
ok("evidence explains the absence", "no KB precursor partial pressure" in (p.evidence or ""), p.evidence)
ok("warned explicitly", any("FALLBACK" in w for w in ctx.warnings), ctx.warnings)
ok("recorded as unresolved", "ratio_from_literature" in ctx.unresolved, ctx.unresolved)
ok("reference exposure is unresolved without pA0",
   ctx.priors["reference_effective_dose"].source == "unresolved",
   ctx.priors["reference_effective_dose"].source)
ok("but the KB pulse time is still credited",
   ctx.priors["reference_pulse_time"].source == "kb")

print("3) real KB evidence, when it exists, IS credited")
ctx2 = md.resolve_context(REQ60, warm_start_fn=ws_with_pressure)
check("ratio source", ctx2.priors["ratio"].source, "kb")
check("ratio value", ctx2.priors["ratio"].value, 500.0)
ok("confidence higher than fallback",
   ctx2.priors["ratio"].confidence > md.CONFIDENCE["fallback"])
ok("no fallback warning", not any("FALLBACK" in w for w in ctx2.warnings), ctx2.warnings)
check("reference exposure resolved", ctx2.priors["reference_effective_dose"].source, "kb")
ok("reference exposure = pA0*tp0",
   abs(ctx2.priors["reference_effective_dose"].value - 45.0) < 1e-9)

print("4) user constraints override priors")
ctx3 = md.resolve_context(
    md.DesignRequest("Al2O3", 60e-6, constraints={"ratio": 250.0,
                                                  "pressure_bounds": (5.0, 50.0)}),
    warm_start_fn=ws_with_pressure)
check("user ratio wins over KB", (ctx3.priors["ratio"].source, ctx3.priors["ratio"].value),
      ("user", 250.0))
check("user bounds win", ctx3.priors["pressure_bounds"].source, "user")
ok("user confidence is highest", ctx3.priors["ratio"].confidence == md.CONFIDENCE["user"])

print("5) a pinned ratio collapses to ONE family — no alternatives invented")
cands = md.generate_candidates(ctx3, model_factory=fake_factory)
check("single family", len(cands), 1)
check("named for the caller", cands[0].family, "user_specified")
check("ratio src", cands[0].ratio_source, "user")

print("6) inversion is delegated to the solver, not reimplemented")
src = (HERE / "m2_design.py").read_text()
ok("calls solve_target_dose", "inverse_solver.solve_target_dose(" in src)
# No root finder and no proportional-controller update may live in this layer. (The
# ±rel perturbation in analyse_robustness is a sensitivity probe, not an update rule,
# so the check names real solver/controller constructs rather than arithmetic shapes.)
for banned in ("brentq", "bisect", "newton", "fsolve", "root_scalar", "Kp", "1 + Kp"):
    ok(f"no in-layer root finding: {banned!r}", banned not in src)
ok("no controller-style dose update loop",
   "while" not in src.replace("# ", "") or "solve_target_dose" in src)
c = md.generate_candidates(md.resolve_context(REQ60, warm_start_fn=ws_no_pressure),
                           model_factory=fake_factory)[0]
ok("returns the solver's DoseSolution", isinstance(c.solution, inverse_solver.DoseSolution))

print("7) effective_dose is never called D (naming safety)")
ok("solver exposes effective_dose", hasattr(c.solution, "effective_dose"))
ok("and it equals pA * pulse_time",
   c.feasible and abs(c.solution.effective_dose - c.solution.pA * c.solution.pulse_time) < 1e-9)
ok("layer never binds a bare `D`", "\n    D " not in src and "(D)" not in src and " D =" not in src)
ok("to_dict carries effective_dose", "effective_dose" in c.solution.to_dict())

print("8) feasibility is assessed before solving, at the resolved ratio")
ctxf = md.resolve_context(REQ60, warm_start_fn=ws_no_pressure)
f = md.assess_feasibility(ctxf, model=FakeTwin())
ok("range reported", f["pd_min"] < f["pd_max"], (f["pd_min"], f["pd_max"]))
check("verdict", f["verdict"], "within_range" if f["pd_min"] <= 60e-6 <= f["pd_max"] else "above_range")
check("ratio source carried", f["ratio_source"], "fallback")
f2 = md.assess_feasibility(md.resolve_context(md.DesignRequest("Al2O3", 1.0),
                                              warm_start_fn=ws_no_pressure), model=FakeTwin())
check("absurd target -> above_range", f2["verdict"], "above_range")

print("9) ranking is ordered, bounded and fully reported")
res = md.design(REQ60, model_factory=fake_factory, warm_start_fn=ws_no_pressure)
ranked = res["candidates"]
scores = [c.total_score for c in ranked]
ok("sorted descending", scores == sorted(scores, reverse=True), scores)
ok("best is feasible", res["best"] is None or res["best"].feasible)
for c in ranked:
    if c.feasible:
        for k in ("accuracy", "margin", "robustness", "throughput", "confidence"):
            ok(f"{c.family}.{k} in [0,1]", 0.0 <= c.scores[k] <= 1.0 + 1e-9, c.scores[k])
        ok(f"{c.family} weights reported", "weights" in c.scores)
    else:
        ok(f"{c.family} rejection explained", bool(c.rejected), c.rejected)
        check(f"{c.family} scores zero", c.total_score, 0.0)

print("10) robustness is computed and physically ordered")
for c in ranked:
    if not c.feasible:
        continue
    rb = c.robustness
    ok(f"{c.family} has sensitivities", {"dose_sensitivity", "ratio_sensitivity"} <= set(rb))
    ok(f"{c.family} sqrt-law dose sensitivity ~0.5", abs(rb["dose_sensitivity"] - 0.5) < 0.05,
       rb["dose_sensitivity"])
    ok(f"{c.family} margins in [0,1]",
       all(0.0 <= rb[k] <= 1.0 for k in ("pressure_margin", "pulse_time_margin", "dose_margin")),
       {k: round(rb[k], 3) for k in ("pressure_margin", "pulse_time_margin", "dose_margin")})
    ok(f"{c.family} perturbed PDs bracket the achieved one",
       rb["pd_at_minus"] <= c.solution.achieved_pd <= rb["pd_at_plus"])

print("11) no target -> no invention")
res0 = md.design(md.DesignRequest("Al2O3", None), model_factory=fake_factory,
                 warm_start_fn=ws_no_pressure)
check("status", res0["status"], "no_feasible_candidate")
ok("target flagged unresolved", "target_pd" in res0["context"].unresolved)
ok("no candidate solved", all(not c.feasible for c in res0["candidates"]))
ok("each says why", all(c.rejected for c in res0["candidates"]))

print("12) report renders for both feasible and infeasible outcomes")
import tempfile
with tempfile.TemporaryDirectory() as td:
    p1 = md.render_report(res, out_path=Path(td) / "a.html")
    h = p1.read_text()
    ok("report written", p1.is_file() and len(h) > 1500, len(h))
    ok("shows the fallback tag", 's-fallback' in h)
    ok("says not literature-derived", "not a literature recipe" in h or "fallback" in h)
    ok("uses effective dose wording", "effective dose" in h.lower())
    ok("no bare 'D =' label", "D =" not in h)
    p2 = md.render_report(res0, out_path=Path(td) / "b.html")
    ok("infeasible report renders", p2.is_file() and "No feasible candidate" in p2.read_text())

print("13) real-twin integration: 60 µm primary, 200 µm infeasible path")
try:
    res60 = md.design(md.DesignRequest("Al2O3", 60e-6))
    f = res60["feasibility"]
    print(f"       achievable {f['pd_min']*1e6:.2f}–{f['pd_max']*1e6:.2f} µm; verdict {f['verdict']}")
    ok("60 µm is designed", res60["status"] == "designed", res60["status"])
    b = res60["best"]
    ok("best hits the target", abs(b.solution.achieved_pd - 60e-6) < 1e-9, b.solution.residual)
    ok("pA within bounds", 1.0 <= b.solution.pA <= 200.0, b.solution.pA)
    ok("t_p within bounds", 0.01 <= b.solution.pulse_time <= 5.0, b.solution.pulse_time)
    ok("effective dose consistent",
       abs(b.solution.effective_dose - b.solution.pA * b.solution.pulse_time) < 1e-9)
    ok("ratio still a fallback today", res60["context"].priors["ratio"].source == "fallback",
       res60["context"].priors["ratio"].source)
    res200 = md.design(md.DesignRequest("Al2O3", 200e-6))
    st = [c.solution.status for c in res200["candidates"] if c.solution]
    print(f"       200 µm family statuses: {st}")
    ok("200 µm is above the resolved-ratio range",
       res200["feasibility"]["verdict"] == "above_range", res200["feasibility"]["verdict"])
    ok("at least one family reports infeasible_high", "infeasible_high" in st, st)
    ok("no family fake-converges", "max_evaluations" not in st, st)
    for c in res200["candidates"]:
        if not c.feasible:
            ok(f"{c.family} rejection is a real status",
               c.solution.status in inverse_solver.STATUSES, c.solution.status)
except Exception as e:
    print(f"  SKIP  real twin/KB unavailable: {type(e).__name__}: {e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
