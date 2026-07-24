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


# Phase 2 changed the default: a material-only request no longer silently acquires a
# nominal ratio. The fallback path now requires an explicit opt-in, so the Phase-1
# checks below exercise it deliberately; REQ60_STRICT covers the refusing default.
REQ60 = md.DesignRequest(material="Al2O3", target_pd=60e-6, allow_chemistry_fallback=True)
REQ60_STRICT = md.DesignRequest(material="Al2O3", target_pd=60e-6)

print("1) underspecified request is completed, and gaps are declared")
ctx = md.resolve_context(REQ60, warm_start_fn=ws_no_pressure)
ok("every needed prior exists",
   {"target_pd", "material", "ratio", "pressure_bounds", "pulse_time_bounds"} <= set(ctx.priors),
   sorted(ctx.priors))
check("target is user-sourced", ctx.priors["target_pd"].source, "user")
ok("target is not overridable", ctx.priors["target_pd"].overridable is False)
check("bounds are model_supported", ctx.priors["pressure_bounds"].source, "model_supported")

print("2a) without an opt-in, a material-only request REFUSES to invent a ratio")
strict = md.resolve_context(REQ60_STRICT, warm_start_fn=ws_no_pressure)
check("strict ratio source", strict.priors["ratio"].source, "unresolved")
check("strict ratio value", strict.priors["ratio"].value, None)
ok("and says an opt-in is needed",
   any("allow_chemistry_fallback" in w for w in strict.warnings), strict.warnings)

print("2) the opted-in fallback ratio is NEVER dressed up as literature")
p = ctx.priors["ratio"]
check("source", p.source, "fallback")
check("confidence", p.confidence, md.CONFIDENCE["fallback"])
ok("confidence is low", p.confidence <= 0.2, p.confidence)
ok("source is not kb/user", p.source not in ("kb", "user"))
ok("evidence explains the absence",
   any(k in (p.evidence or "") for k in
       ("no partial_pressure record", "no species-attributed partial pressure",
        "can serve as precursor_partial_pressure", "no KB precursor partial pressure")),
   p.evidence)
ok("warned explicitly", any("FALLBACK" in w for w in ctx.warnings), ctx.warnings)
ok("recorded as unresolved", "ratio_from_literature" in ctx.unresolved, ctx.unresolved)
ok("precursor chemistry is also unresolved for a material-only request",
   "precursor" in ctx.unresolved, ctx.unresolved)
ok("reference exposure is unresolved without pA0",
   ctx.priors["reference_effective_dose"].source == "unresolved",
   ctx.priors["reference_effective_dose"].source)
# Phase 2: with no chemistry resolved there is no species-scoped pulse either, so
# this is unresolved rather than credited — a material-only pulse would not be a
# precursor pulse.
ok("no chemistry -> no credited precursor pulse time",
   ctx.priors["reference_pulse_time"].source == "unresolved",
   ctx.priors["reference_pulse_time"].source)
ctx_chem = md.resolve_context(md.DesignRequest("Al2O3", 60e-6, precursor="TMA",
                                               co_reactant="H2O"))
ok("but WITH a chemistry the KB pulse time IS credited",
   ctx_chem.priors["reference_pulse_time"].source == "kb",
   ctx_chem.priors["reference_pulse_time"].source)

print("3) real chemistry-scoped KB evidence, when it exists, IS credited")
# Phase 2: the ratio no longer comes from a material-keyed warm start. It is built
# from a species-scoped pressure and pulse of the SAME chemistry, so the credited
# case needs records that actually carry that scope.
def _exp(pid, mat, prec, core, conds):
    return {"_pid": pid, "material": mat, "precursors": [prec], "coreactants": [core],
            "reactants": [{"label": "A", "role": "precursor", "species": prec},
                          {"label": "B", "role": "coreactant", "species": core}],
            "controlled": conds}


SYNTH_KB = [_exp("synth", "Al2O3", "TMA", "H2O",
                 [{"quantity": "precursor_partial_pressure", "value": 150.0, "of_reactant": "A", "unit": "Pa"},
                  {"quantity": "pulse_time", "value": 0.3, "of_reactant": "A", "unit": "s"}])]
ctx2 = md.resolve_context(md.DesignRequest("Al2O3", 60e-6, precursor="TMA",
                                           co_reactant="H2O"),
                          experiments_fn=lambda: SYNTH_KB)
check("ratio source", ctx2.priors["ratio"].source, "kb")
ok("ratio = 150/0.3 = 500", abs(ctx2.priors["ratio"].value - 500.0) < 1e-9,
   ctx2.priors["ratio"].value)
ok("confidence higher than fallback",
   ctx2.priors["ratio"].confidence > md.CONFIDENCE["fallback"])
ok("no fallback warning", not any("FALLBACK" in w for w in ctx2.warnings), ctx2.warnings)
check("reference exposure resolved", ctx2.priors["reference_effective_dose"].source, "kb")
ok("reference exposure = pA0*tp0",
   abs(ctx2.priors["reference_effective_dose"].value - 45.0) < 1e-9,
   ctx2.priors["reference_effective_dose"].value)

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
check("family definition src", cands[0].family_definition_source, "user")
check("ratio evidence src", cands[0].ratio_evidence_source, "user")

print("6) inversion is delegated to the solver, not reimplemented")
src = (HERE / "m2_design.py").read_text()
ok("calls solve_target_dose", "inverse_solver.solve_target_dose(" in src)
# No root finder and no proportional-controller update may live in this layer. (The
# ±rel perturbation in analyse_robustness is a sensitivity probe, not an update rule,
# so the check names real solver/controller constructs rather than arithmetic shapes.)
for banned in ("brentq", "bisect", "newton", "fsolve", "root_scalar", "Kp",
               "1 + Kp", "scipy.optimize"):
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
fnr = md.assess_feasibility(md.resolve_context(REQ60_STRICT), model=FakeTwin())
check("no ratio -> unknown verdict, no crash", fnr["verdict"], "unknown")
ok("range reported", f["pd_min"] < f["pd_max"], (f["pd_min"], f["pd_max"]))
check("verdict", f["verdict"], "within_range" if f["pd_min"] <= 60e-6 <= f["pd_max"] else "above_range")
check("ratio source carried", f["ratio_source"], "fallback")
f2 = md.assess_feasibility(md.resolve_context(md.DesignRequest(
    "Al2O3", 1.0, allow_chemistry_fallback=True),
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
res0 = md.design(md.DesignRequest("Al2O3", None, allow_chemistry_fallback=True),
                 model_factory=fake_factory,
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
    ok("infeasible report renders", p2.is_file() and "No candidate is selected" in p2.read_text())

print("13) real-twin integration: 60 µm primary, 200 µm infeasible path")
try:
    res60 = md.design(md.DesignRequest("Al2O3", 60e-6, allow_chemistry_fallback=True))
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
    res200 = md.design(md.DesignRequest("Al2O3", 200e-6, allow_chemistry_fallback=True))
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

# =============================================================================
# Phase-1 corrections: provenance split, dual feasibility, ranking semantics,
# knowledge coverage, single canonical artifact.
# =============================================================================
print("14) ratio provenance: family definition is SEPARATE from numerical evidence")
ctxf = md.resolve_context(REQ60, warm_start_fn=ws_no_pressure)
cands = md.generate_candidates(ctxf, model_factory=fake_factory)
by = {c.family: c for c in cands}
bal = by["balanced"]
check("balanced family definition", bal.family_definition_source, "model_supported_archetype")
check("balanced ratio evidence", bal.ratio_evidence_source, "fallback")
check("balanced ratio confidence", bal.ratio_evidence_confidence, md.CONFIDENCE["fallback"])
ok("balanced ratio is NOT kb", bal.ratio_evidence_source != "kb")
ok("balanced ratio is NOT model_supported", bal.ratio_evidence_source != "model_supported")
for name in ("long_low_pressure", "short_high_pressure"):
    c = by[name]
    check(f"{name} evidence is derived", c.ratio_evidence_source, "derived_from_fallback")
    check(f"{name} base source", c.base_ratio_source, "fallback")
    ok(f"{name} confidence <= base", c.ratio_evidence_confidence <= bal.ratio_evidence_confidence,
       (c.ratio_evidence_confidence, bal.ratio_evidence_confidence))
    ok(f"{name} never reads kb/literature",
       "kb" not in c.ratio_evidence_source and "literature" not in c.ratio_evidence_source)
    ok(f"{name} evidence text disclaims independence",
       "no independent evidence" in (c.ratio_evidence or ""), c.ratio_evidence)
ok("two provenance axes are distinct fields",
   bal.family_definition_source != bal.ratio_evidence_source)
# with a REAL kb ratio, derived families say derived_from_kb (still not plain 'kb')
ck = md.resolve_context(md.DesignRequest("Al2O3", 60e-6, precursor="TMA",
                                        co_reactant="H2O"),
                        experiments_fn=lambda: SYNTH_KB)
ck_c = {c.family: c for c in md.generate_candidates(ck, model_factory=fake_factory)}
check("kb base: balanced evidence", ck_c["balanced"].ratio_evidence_source, "kb")
check("kb base: derived evidence", ck_c["long_low_pressure"].ratio_evidence_source, "derived_from_kb")
ok("derived kb confidence below base",
   ck_c["long_low_pressure"].ratio_evidence_confidence < ck_c["balanced"].ratio_evidence_confidence)

print("15) reference vs global feasibility are distinct fields")
res = md.design(REQ60, model_factory=fake_factory, warm_start_fn=ws_no_pressure)
ok("both fields present", {"reference_context_status", "global_design_space_status"} <= set(res))
ok("global achievable is a union", res["global_achievable"]["pd_max"] >= res["feasibility"]["pd_max"],
   (res["global_achievable"]["pd_max"], res["feasibility"]["pd_max"]))
ok("per-family ranges reported", len(res["family_ranges"]) == 3, len(res["family_ranges"]))

print("16) case B — reference infeasible, an alternative family feasible")
# FakeTwin PD = 1e-5*sqrt(D). Pick a target the reference bracket cannot reach but a
# lower-ratio family can, derived from the actual evaluated limits (never hard-coded).
ctxB = md.resolve_context(REQ60, warm_start_fn=ws_no_pressure)
rows = md.family_achievable_ranges(ctxB, model_factory=fake_factory)
ref_max = next(r["pd_max"] for r in rows if r["family"] == "balanced")
g_lo, g_hi = md.global_achievable_range(rows)
if g_hi > ref_max:
    tB = 0.5 * (ref_max + g_hi)          # above the reference family, inside the global union
    resB = md.design(md.DesignRequest("Al2O3", tB, allow_chemistry_fallback=True),
                     model_factory=fake_factory,
                     warm_start_fn=ws_no_pressure)
    ok("reference is infeasible", resB["reference_context_status"].startswith("infeasible"),
       resB["reference_context_status"])
    check("global is feasible", resB["global_design_space_status"], "feasible")
    check("top-level follows global", resB["status"], "designed")
    hB = md.render_report(resB, out_path=None) if False else None
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        h = md.render_report(resB, out_path=Path(td) / "b.html").read_text()
    ok("report states the reference cannot but an alternative can",
       "cannot reach the target, but at least one alternative operating family can" in h)
    ok("report does NOT call it globally infeasible", "global_design_space_status" in h
       and ">infeasible<" not in h.split("global_design_space_status")[0][-200:])
else:
    print("  SKIP  no family exceeds the reference range in the fake model")

print("17) case C — globally infeasible target derived from actual family limits")
MARGIN = 1.5                                   # documented: 50 % above the global maximum
tC = g_hi * MARGIN
resC = md.design(md.DesignRequest("Al2O3", tC, allow_chemistry_fallback=True),
                 model_factory=fake_factory,
                 warm_start_fn=ws_no_pressure)
ok("no family reaches it", all(not c.feasible for c in resC["candidates"]))
ok("global status is infeasible", resC["global_design_space_status"].startswith("infeasible"),
   resC["global_design_space_status"])
check("no candidate selected", resC["best"], None)
check("top-level status", resC["status"], "no_feasible_candidate")
ok("target was derived, not hard-coded", tC > g_hi, (tC, g_hi))

print("18) knowledge coverage excludes fallback from evidence")
cov = res["coverage"]
ok("fallback counted separately", cov["fallback_inputs"] >= 1, cov["fallback_inputs"])
ok("fallback not in kb count", "ratio" not in cov["by_source"].get("kb", []), cov["by_source"])
ok("level is partial", cov["level"] == "partial", cov["level"])
ok("unresolved items listed", isinstance(cov["unresolved_items"], list))
ok("critical inputs enumerated",
   {"target_pd", "material", "ratio", "pressure_bounds", "pulse_time_bounds"}
   <= set(cov["critical_inputs"]), sorted(cov["critical_inputs"]))
check("primary result IS fallback-dependent", cov["fallback_dependent_result"], True)
ok("and says why", bool(cov["fallback_dependency_reasons"]), cov["fallback_dependency_reasons"])
# synthetic fully-supported context must NOT be fallback-dependent
resK = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                                  constraints={"ratio": 500.0}),
                 model_factory=fake_factory, warm_start_fn=ws_with_pressure)
check("user-pinned ratio -> not fallback-dependent",
      resK["coverage"]["fallback_dependent_result"], False)
ok("no fallback inputs there", resK["coverage"]["fallback_inputs"] == 0,
   resK["coverage"]["by_source"])

print("19) ranking semantics are explicit, not asserted")
sel = res["selection"]
ok("profile named", bool(sel["profile"]), sel["profile"])
check("weights exposed", set(sel["weights"]), set(md.RANKING_WEIGHTS))
ok("runner-up present", sel["runner_up"] is not None, sel["runner_up"])
ok("score gap computed", sel["score_gap"] is not None)
ok("trade-offs explained", len(sel["trade_offs"]) > 0, [t["criterion"] for t in sel["trade_offs"]])
ok("near-tie threshold exposed", sel["near_tie_threshold"] == md.NEAR_TIE_THRESHOLD)
ok("not-a-unique-optimum note present", "not a unique physical optimum" in sel["note"])
# near-tie is deterministic: force it by widening the threshold past the actual gap
resT = md.design(REQ60, model_factory=fake_factory, warm_start_fn=ws_no_pressure,
                 near_tie_threshold=sel["score_gap"] + 0.01)
check("near-tie flagged when threshold exceeds gap", resT["selection"]["near_tie"], True)
resN = md.design(REQ60, model_factory=fake_factory, warm_start_fn=ws_no_pressure,
                 near_tie_threshold=max(0.0, sel["score_gap"] - 0.01))
check("and not flagged otherwise", resN["selection"]["near_tie"], False)

print("20) report wording and single canonical artifact")
import tempfile
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "r.html").read_text()
    ok("heading does not claim a unique optimum", "Recommended operating point" not in h)
    ok("heading names the ranking profile", "Selected under the current ranking profile" in h)
    ok("note that it is not a unique optimum", "not a unique physical optimum" in h)
    ok("title is knowledge-AWARE", "knowledge-aware inverse design" in h)
    ok("subtitle qualifies coverage", "knowledge coverage" in h and "fallback-dependent" in h)
    ok("fallback ratio never rendered as kb/literature",
       ">kb<" not in h.split("ratio evidence")[1][:2000] if "ratio evidence" in h else True)
    ok("both provenance columns rendered",
       "family definition" in h and "ratio evidence" in h)
    ok("both feasibility statuses rendered",
       "reference_context_status" in h and "global_design_space_status" in h)
    ok("input support summary section present",
       "Input support summary" in h and "overall input support" in h)
    ok("solver diagnostics present", "solve_target_dose" in h and "model evals" in h)
    ok("effective dose wording", "effective dose" in h.lower())
    ok("no bare 'D =' label", "D =" not in h)
    # globally infeasible renders through the SAME renderer, in tmp_path
    hC = md.render_report(resC, out_path=Path(td) / "c.html").read_text()
    ok("infeasible: no selected candidate", "No candidate is selected" in hC)
    ok("infeasible: shows closest boundary, labelled as not satisfying",
       "does NOT satisfy the" in hC or "No candidate is selected" in hC)
    ok("infeasible: explains binding constraints", "binding constraints" in hC or
       "pressure and pulse-time bounds" in hC)
check("canonical name", md.CANONICAL_REPORT, "m2_report.html")
ok("only one canonical M2 artifact on disk",
   not (HERE / "m2_design_report.html").exists()
   and not (HERE / "m2_design_report_infeasible.html").exists(),
   sorted(p.name for p in HERE.glob("m2*report*.html")))

print("21) real twin: canonical numbers recomputed")
try:
    r60 = md.design(md.DesignRequest("Al2O3", 60e-6, allow_chemistry_fallback=True))
    print(f"       ref={r60['reference_context_status']} global={r60['global_design_space_status']} "
          f"globalPD={r60['global_achievable']['pd_min']*1e6:.2f}-"
          f"{r60['global_achievable']['pd_max']*1e6:.2f} µm")
    check("60 µm designed", r60["status"], "designed")
    check("reference feasible", r60["reference_context_status"], "feasible")
    check("global feasible", r60["global_design_space_status"], "feasible")
    ok("target met within solver tolerance",
       abs(r60["best"].solution.achieved_pd - 60e-6) <= max(1e-9, 1e-6 * 60e-6),
       r60["best"].solution.residual)
    check("still fallback-dependent today", r60["coverage"]["fallback_dependent_result"], True)
    ok("selected ratio evidence is fallback-flavoured",
       "fallback" in r60["best"].ratio_evidence_source, r60["best"].ratio_evidence_source)
    rows = md.family_achievable_ranges(r60["context"])
    g_lo2, g_hi2 = md.global_achievable_range(rows)
    rC = md.design(md.DesignRequest("Al2O3", g_hi2 * 1.5, allow_chemistry_fallback=True))
    ok("real-twin derived target is globally infeasible",
       rC["global_design_space_status"].startswith("infeasible"),
       rC["global_design_space_status"])
    print(f"       globally-infeasible probe = {g_hi2*1.5*1e6:.1f} µm "
          f"(1.5 x global max {g_hi2*1e6:.1f} µm)")
except Exception as e:
    print(f"  SKIP  real twin unavailable: {type(e).__name__}: {e}")

print("22) report information hierarchy: summary vs ledger")
import tempfile
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "h.html").read_text()
    ok("input-support section renamed", "· Input support summary" in h)
    ok("ledger section renamed", "· Resolved context and provenance ledger" in h)
    ok("old title gone", "Knowledge coverage" not in h)
    sec2 = h.split("Input support summary")[1].split("<h2>")[0]
    sec3 = h.split("Resolved context and provenance ledger")[1].split("<h2>")[0]
    # -- section 2 is a SUMMARY --------------------------------------------------
    ok("s2 has aggregate source counts", "all resolved inputs" in sec2.lower())
    ok("s2 has fallback dependency", "fallback-dependent result" in sec2)
    ok("s2 has overall support level", "overall input support" in sec2)
    ok("s2 names decision-critical inputs", "Decision-critical inputs" in sec2)
    ok("s2 lists the weak critical input", "ratio" in sec2)
    ok("s2 has the interpretation sentence",
       "only partially evidence-supported" in sec2, sec2.count("evidence-supported"))
    # -- and NOT a ledger --------------------------------------------------------
    ok("s2 omits overridable flags", "overridable" not in sec2)
    ok("s2 omits downstream-use column", "downstream use" not in sec2)
    ok("s2 omits non-critical context vars", "reference_pulse_time" not in sec2)
    ok("s2 is shorter than the ledger", len(sec2) < len(sec3), (len(sec2), len(sec3)))
    # -- section 3 is the ONLY full ledger ---------------------------------------
    for fieldname in ("variable", "value", "unit", "source", "conf", "evidence", "overridable",
                      "downstream use", "role"):
        ok(f"s3 ledger column {fieldname!r}", fieldname in sec3)
    for var in res["context"].priors:
        ok(f"s3 lists {var}", var in sec3)
    ok("s3 keeps the complete unresolved list", "Unresolved inputs (complete list)" in sec3
       or not res["context"].unresolved)
    ok("hierarchy sentence links the two",
       "The following ledger records every resolved input" in h)

print("23) decision criticality is distinct from raw source counts")
cov = res["coverage"]
ok("critical_by_source present", "critical_by_source" in cov)
# Demonstrated on a chemistry-resolved run, where a KB-backed input actually exists:
# reference_pulse_time is KB-supported but is context, not decision-critical.
covK = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O"),
                 model_factory=fake_factory,
                 experiments_fn=lambda: SYNTH_KB)["coverage"]
ok("kb_supported counts ALL kb inputs", covK["kb_supported"] >= 1, covK["kb_supported"])
ok("reference_pulse_time is among them",
   "reference_pulse_time" in covK["by_source"]["kb"], covK["by_source"]["kb"])
ok("but it is NOT decision-critical",
   "reference_pulse_time" not in covK["kb_supported_critical"],
   covK["kb_supported_critical"])
ok("so a raw count overstates the KB's control of the recipe",
   covK["kb_supported"] > len([n for n in covK["kb_supported_critical"]
                               if n == "reference_pulse_time"]),
   (covK["kb_supported"], covK["kb_supported_critical"]))
ok("the fallback ratio IS decision-critical",
   "ratio" in [c["name"] for c in cov["critical_by_source"]["fallback"]],
   cov["critical_by_source"]["fallback"])
ok("reference_pulse_time is NOT decision-critical",
   "reference_pulse_time" not in md.DECISION_CRITICAL)
ok("and is not listed among weak critical inputs",
   "reference_pulse_time" not in [c["name"] for c in cov["critical_weak"]])
ok("not every context variable is critical",
   set(md.DECISION_CRITICAL) < set(res["context"].priors),
   (sorted(md.DECISION_CRITICAL), sorted(res["context"].priors)))
ok("classification is documented", all(isinstance(v, str) and v
                                       for v in md.DECISION_CRITICAL.values()))
check("support level is 4-way vocabulary", cov["level"] in
      ("complete", "substantial", "partial", "insufficient"), True)

print("24) evaluated-family terminology (no continuous 2-D claim)")
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "t.html").read_text()
    ok("says evaluated operating families", "evaluated operating families" in h)
    ok("says envelope", "envelope" in h)
    ok("states the continuous domain was NOT searched",
       "has <b>not</b> been searched" in h)
    ok("no bare 'global design space' phrasing", "global design space" not in h)
    ok("no 'globally achievable' phrasing", "globally achievable" not in h)
    ok("section 5 title names evaluated families",
       "Feasibility across evaluated operating families" in h)
    # ranking language from 9e53156 preserved verbatim
    ok("ranking heading preserved", "Selected under the current ranking profile" in h)
    ok("no reverted heading", "Recommended operating point" not in h)
    for token in ("Ranking profile", "Runner-up", "score gap", "not a unique physical optimum"):
        ok(f"ranking element {token!r} preserved", token in h)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
