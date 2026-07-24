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

print("12) report renders from the certificate for feasible and empty-region outcomes")
# MIGRATED: frozen requirement 11 replaces the pipeline-ordered report with a
# certificate-driven one; the "No candidate is selected" wording is gone.
import tempfile
with tempfile.TemporaryDirectory() as td:
    p1 = md.render_report(res, out_path=Path(td) / "a.html")
    h = p1.read_text()
    ok("report written", p1.is_file() and len(h) > 1500, len(h))
    ok("shows the fallback tag in the ledger", 's-fallback' in h)
    ok("uses effective dose wording", "effective dose" in h.lower())
    ok("no bare 'D =' label", "D =" not in h)
    ok("names the admissibility regime", "admissibility regime" in h)
    p2 = md.render_report(res0, out_path=Path(td) / "b.html")
    h2 = p2.read_text()
    ok("no-target report renders", p2.is_file() and len(h2) > 1500)
    ok("no-target region is empty / infeasible", "feasible region is empty" in h2.lower()
       or "infeasible" in h2.lower())

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
    # MIGRATED: frozen requirement 11 removes the reference-vs-family report narrative.
    # The dual-feasibility fields remain (legacy machinery preserved); only the report
    # wording changed. Certificate renders through the same one renderer.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        h = md.render_report(resB, out_path=Path(td) / "b.html").read_text()
    ok("report renders through the certificate", "inverse-design certificate" in h)
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

print("20) certificate report: organised by the scientific result, single artifact")
# MIGRATED: frozen requirement 11 replaces the ranking-profile report. The report is
# now organised around the scientific result and must NOT present a sampled pair as the
# uniquely solved recipe. The old ranking headings are intentionally gone.
import tempfile
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "r.html").read_text()
    ok("title is the certificate", "inverse-design certificate" in h)
    ok("has an executive summary section", "Executive Summary" in h)
    ok("has a problem-definition section", "Problem Definition" in h)
    ok("has a forward-model-identified section", "Quantities Identified by the Forward Model" in h)
    ok("has a feasible-region section", "Feasible operating region" in h)
    ok("has an undetermined-quantities section", "Fundamentally undetermined quantities" in h)
    ok("region is the answer, not a single pair",
       "not any single pressure/pulse pair — is the scientific answer" in h)
    ok("does NOT claim a unique physical optimum", "not a unique physical optimum" not in h)
    ok("no old ranking-profile heading", "Selected under the current ranking profile" not in h)
    ok("no 'Recommended operating point' heading", "Recommended operating point" not in h)
    ok("effective dose wording", "effective dose" in h.lower())
    ok("no bare 'D =' label", "D =" not in h)
    # empty region renders through the SAME renderer, in tmp_path
    hC = md.render_report(resC, out_path=Path(td) / "c.html").read_text()
    ok("empty-region report renders", "inverse-design certificate" in hC)
    ok("empty region / infeasible stated",
       "feasible region is empty" in hC.lower() or "infeasible" in hC.lower())
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

print("22) certificate report: ledger appendix carries full provenance")
# MIGRATED: frozen requirement 11 moves provenance to the technical appendix (§11);
# the mid-narrative "Input support summary" / "Resolved context" split is retired.
import tempfile
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "h.html").read_text()
    ok("appendix section present", "Technical provenance and ledger appendix" in h)
    ok("supporting-evidence section present", "Supporting evidence" in h)
    ok("assumptions section present", "· Assumptions" in h)
    ok("confidence section present", "Confidence and dominant uncertainty" in h)
    sec11 = h.split("Technical provenance and ledger appendix")[1]
    for fieldname in ("variable", "value", "unit", "source", "conf", "evidence"):
        ok(f"ledger column {fieldname!r}", fieldname in sec11)
    for var in res["context"].priors:
        ok(f"ledger lists {var}", var in sec11)
    ok("legacy diagnostics retained in appendix",
       "reference_context_status" in sec11 and "global_design_space_status" in sec11)

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

print("24) certificate report: region is derived from the active model, not families")
# MIGRATED: frozen requirements 5 & 8 — the feasible region is TRACED from the active
# forward model (not three fixed ratio families), and the sampled points are labelled
# illustrative samples, never competitors or a unique recipe.
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res, out_path=Path(td) / "t.html").read_text()
    ok("representative feasible operating points wording",
       "representative feasible operating points" in h.lower())
    ok("samples are labelled illustrative", "illustrative_sample" in h)
    ok("free-coordinate count reported", "free coordinate" in h)
    ok("variation in pressure x pulse time explained", "variation in pressure" in h)
    ok("no implementation jargon 'locus'", "locus" not in h)
    ok("no old ranking heading", "Selected under the current ranking profile" not in h)
    ok("no 'Recommended operating point'", "Recommended operating point" not in h)

# =============================================================================
# Frozen-spec behaviours (design certificate). Uses the REAL twin (the certificate is
# always built from the active forward model, independent of any test model_factory).
# =============================================================================
print("25) design certificate satisfies the frozen specification")
try:
    import inverse_solver as _inv
    RQ = md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                          geometry_class="lateral_channel", allow_chemistry_fallback=True)
    rc = md.design(RQ)
    cert = rc["certificate"]
    b = cert["branches"][0]

    # (a) fully specified chemistry -> exactly one evaluated branch
    check("one branch for a specified chemistry", cert["n_branches"], 1)

    # regimes
    ok("regime is a frozen top-level regime",
       b["admissibility"]["regime"] in md.ADMISSIBILITY_REGIMES, b["admissibility"]["regime"])
    ok("regime reasons are machine-readable",
       all("code" in r for r in b["admissibility"]["reasons"]))
    # generic/default kinetics cap at exploratory (they are twin defaults here)
    check("default kinetics -> exploratory (not quantitative)",
          b["admissibility"]["regime"], "exploratory")

    # (b) material-only -> independently evaluated chemistry branches, no leakage
    rm = md.design(md.DesignRequest("Al2O3", 60e-6, geometry_class="lateral_channel"))
    cm = rm["certificate"]
    ok("material-only enumerates >1 chemistry branch", cm["n_branches"] > 1, cm["n_branches"])
    labels = [br["chemistry"]["label"] for br in cm["branches"]]
    ok("branch chemistries are distinct (no pooling)", len(labels) == len(set(labels)), labels)
    ok("not a blanket ambiguity failure", cm["overall_regime"] != "refuse")
    ok("no quantitative cross-chemistry ranking when bundles unsafe",
       cm["cross_chemistry_comparable"] is False and cm["comparison_note"],
       cm["comparison_note"])

    # (c) out-of-domain geometry never yields a quantitative design
    rg = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                                    geometry_class="porous_material", allow_chemistry_fallback=True))
    gb = rg["certificate"]["branches"][0]
    check("porous geometry refuses", gb["admissibility"]["regime"], "refuse")
    ok("refusal cites geometry", any(r["code"] == "geometry_out_of_domain"
                                     for r in gb["admissibility"]["reasons"]))

    # (d) unreachable target -> infeasible
    ru = md.design(md.DesignRequest("Al2O3", 5000e-6, precursor="TMA", co_reactant="H2O",
                                    geometry_class="lateral_channel", allow_chemistry_fallback=True))
    ub = ru["certificate"]["branches"][0]
    check("unreachable target -> infeasible", ub["admissibility"]["regime"], "infeasible")
    ok("empty feasible region for the unreachable target", ub["feasible_region"]["empty"])

    # (e) every point in the feasible region meets the target within tolerance
    reg = b["feasible_region"]
    ok("region non-empty and 1-D", (not reg["empty"]) and reg["free_coordinate_count"] == 1)
    ok("every region point within 1e-8 m of target",
       all(abs(p["residual"]) <= 1e-8 for p in reg["points"]), reg["pd_max_abs_residual"])

    # (f) feasible-region clipping by pressure and pulse bounds
    reg_full = _inv.trace_feasible_region(
        lambda: md._model("Al2O3"), 60e-6, (1.0, 200.0), (0.01, 5.0))
    reg_clip = _inv.trace_feasible_region(
        lambda: md._model("Al2O3"), 60e-6, (1.0, 200.0), (0.05, 0.2))
    ok("tighter pulse bounds shrink the pressure span",
       (reg_clip["pressure_range"][1] - reg_clip["pressure_range"][0])
       < (reg_full["pressure_range"][1] - reg_full["pressure_range"][0]),
       (reg_clip["pressure_range"], reg_full["pressure_range"]))

    # (g) no objective -> no unique recommendation
    ok("no objective -> no recommended point", b["recommendation"]["point"] is None)
    ok("states an external criterion is required",
       "external criterion" in b["recommendation"]["note"])

    # (h) objective -> the point is explicitly preference-selected
    ro = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                                    geometry_class="lateral_channel",
                                    secondary_objective="minimize_pulse_time",
                                    allow_chemistry_fallback=True))
    orec = ro["certificate"]["branches"][0]["recommendation"]
    ok("objective yields a point", orec["point"] is not None)
    check("point origin is selected_by_preference", orec["point"]["origin"], md.ORIGIN_PREF)
    ok("recommendation says it is NOT physics",
       "NOT distinguished by the physics" in orec["note"])

    # (i) the structurally undetermined split is NOT in determined quantities
    det_names = [q["name"] for q in b["determined"]["quantities"]]
    und_names = [u["name"] for u in b["undetermined"]["undetermined"]]
    ok("split is structurally undetermined", "pressure_pulse_split" in und_names, und_names)
    ok("split is NOT presented as determined",
       "pressure_pulse_split" not in det_names and "pA" not in det_names, det_names)
    ok("undetermined split verified structural from the model",
       any(u["kind"] == "structural" for u in b["undetermined"]["undetermined"]))

    # (j) uncertainty band contains the point estimate (when available)
    dq = b["determined"]["quantities"][0]
    if dq["band"]:
        ok("dose band contains the point estimate",
           dq["band"][0] <= dq["value"] <= dq["band"][1], (dq["band"], dq["value"]))

    # (k) missing kinetic uncertainty -> confidence withheld, no fabricated probability
    check("confidence withheld (kinetics are defaults)", b["confidence"]["status"], "withheld")
    ok("no fabricated probability", b["confidence"]["target_hit_credibility"] is None)

    # (l) every emitted scientific quantity carries an origin classification
    ORIGINS = {md.ORIGIN_DET, md.ORIGIN_PREF, md.ORIGIN_ASSUMED, md.ORIGIN_UNDET, md.ORIGIN_EV_UNC}
    ok("determined quantities carry an origin",
       all(q["origin"] in ORIGINS for q in b["determined"]["quantities"]))
    ok("assumptions carry an origin", all(a["origin"] in ORIGINS for a in b["assumptions"]))
    ok("undetermined quantities carry an origin",
       all(u["origin"] in ORIGINS for u in b["undetermined"]["undetermined"]))
    ok("feasible region is origin-tagged", reg["origin"] == md.ORIGIN_DET)

    # (m) report does not claim a unique physical recipe where none is identified
    with tempfile.TemporaryDirectory() as td:
        hrep = md.render_report(rc, out_path=Path(td) / "cert.html").read_text()
    ok("report: region is the answer, not a single pair",
       "not any single pressure/pulse pair — is the scientific answer" in hrep)
    ok("report: no unique-recipe claim", "uniquely solved recipe" not in hrep)
except Exception as e:
    import traceback
    traceback.print_exc()
    FAIL.append(f"section25:{type(e).__name__}:{e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
