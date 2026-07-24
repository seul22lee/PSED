#!/usr/bin/env python3
"""Tests for the chemistry-aware M2 context (m2_chemistry + m2_design wiring).

The rule these encode: a deposited material does not determine a precursor system.
Al2O3 in this corpus appears under TMA/H2O, DEZ/H2O and a plasma system, and a
material-keyed prior silently pools them. Evidence from different chemistries must
never be averaged, and a value with no species attribution must never be promoted
into one that has.

Synthetic KB records are injected rather than editing the corpus.

  python3 test_m2_chemistry.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "02_extraction"))

import m2_chemistry as mc
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


def exp(pid, material, prec, core, conds):
    return {"_pid": pid, "material": material,
            "precursors": [prec] if prec else [], "coreactants": [core] if core else [],
            "reactants": [{"label": "A", "role": "precursor", "species": prec},
                          {"label": "B", "role": "coreactant", "species": core}],
            "controlled": conds}


def cond(q, v, r=None, u=None):
    return {"quantity": q, "value": v, "of_reactant": r, "unit": u}


# Two chemistries for ONE film, each with its own operating evidence.
SYNTH = [
    exp("paperA", "Al2O3", "TMA", "H2O",
        [cond("precursor_partial_pressure", 50.0, "A", "Pa"), cond("pulse_time", 0.10, "A", "s"),
         cond("pulse_time", 1.0, "B", "s")]),
    exp("paperB", "Al2O3", "TMA", "O3",
        [cond("precursor_partial_pressure", 200.0, "A", "Pa"), cond("pulse_time", 2.0, "A", "s")]),
    exp("paperC", "Al2O3", None, None, [cond("generic_pressure", 7.0, None, "Pa")]),
]

print("1) deposited material and precursor identity are separate fields")
c = mc.ProcessChemistryContext(deposited_material="Al2O3", precursor_identity="TMA",
                               co_reactant_identity="H2O")
check("film", c.deposited_material, "Al2O3")
check("precursor", c.precursor_identity, "TMA")
check("co-reactant", c.co_reactant_identity, "H2O")
ok("material is not an alias for precursor", c.deposited_material != c.precursor_identity)
check("chemistry key", c.chemistry_key, ("TMA", "H2O"))

print("2) same material, different precursors -> distinct branches (Case 1)")
alts = mc.chemistry_alternatives(SYNTH, "Al2O3")
labels = [a["label"] for a in alts]
ok("TMA+H2O present", "TMA + H2O" in labels, labels)
ok("TMA+O3 present", "TMA + O3" in labels, labels)
ok("kept separate", len([a for a in alts if a["resolved"]]) == 2, labels)
ok("unresolved chemistry kept apart, not merged",
   any(not a["resolved"] for a in alts), labels)

print("3) material-only input does not silently pick a precursor (Case 1)")
ctx, st, alts, notes = mc.resolve_chemistry(SYNTH, "Al2O3")
check("status", st, "ambiguous")
check("no precursor chosen", ctx.precursor_identity, None)
check("no co-reactant chosen", ctx.co_reactant_identity, None)
ok("explains why", any("does not determine the precursor" in n for n in notes), notes)

print("4) explicit chemistry filters evidence (Case 2)")
ctx2, st2, _, _ = mc.resolve_chemistry(SYNTH, "Al2O3", precursor="TMA", co_reactant="H2O")
check("status", st2, "fully_specified")
check("source", ctx2.chemistry_source, "user")
pp = mc.scoped_condition_prior(SYNTH, "precursor_partial_pressure", "precursor_partial_pressure", "A",
                               "Al2O3", "TMA", "H2O")
pt = mc.scoped_condition_prior(SYNTH, "precursor_pulse_time", "pulse_time", "A",
                               "Al2O3", "TMA", "H2O")
check("pressure is the TMA/H2O one", pp.value, 50.0)
check("pulse is the TMA/H2O one", pt.value, 0.10)
ok("TMA/O3 evidence excluded", pp.value != 200.0 and pt.value != 2.0)
ok("prior records its chemistry scope", (pp.precursor, pp.co_reactant) == ("TMA", "H2O"))
ok("prior records its species scope", pp.species_scope == "A")
ok("matched dimensions reported", "precursor" in pp.matched_dimensions, pp.matched_dimensions)
ok("missing dimensions reported", "reactor_type" in pp.missing_dimensions, pp.missing_dimensions)
check("match quality", pp.match_quality, "exact_chemistry")

print("5) co-reactant pulse is never used as the precursor pulse")
ptB = mc.scoped_condition_prior(SYNTH, "co_reactant_pulse_time", "pulse_time", "B",
                                "Al2O3", "TMA", "H2O")
check("B pulse", ptB.value, 1.0)
ok("A and B pulses stay distinct", ptB.value != pt.value)

print("6) ratio from one chemistry is valid; across chemistries is refused (Case 6)")
r, status, why = mc.build_ratio(pp, pt)
check("same-chemistry ratio ok", status, "chemistry_supported")
ok("value = pA/tp", abs(r.value - 500.0) < 1e-9, r.value)
check("source", r.source, "kb")
ppO3 = mc.scoped_condition_prior(SYNTH, "precursor_partial_pressure", "precursor_partial_pressure", "A",
                                 "Al2O3", "TMA", "O3")
r2, st_mix, why2 = mc.build_ratio(ppO3, pt)          # TMA/O3 pressure + TMA/H2O pulse
check("cross-chemistry rejected", st_mix, "chemistry_mismatch")
check("no value produced", r2.value, None)
ok("not labelled kb", r2.source != "kb", r2.source)
ok("reason names both systems", "O3" in why2 and "H2O" in why2, why2)

print("7) generic pressure with no species is not a precursor pressure (Case 4)")
ppC = mc.scoped_condition_prior(SYNTH, "precursor_partial_pressure", "generic_pressure", "A",
                                "Al2O3", None, None)
ok("refused", not ppC.resolved, ppC.value)
ok("reported as species-ambiguous or material-rejected",
   ppC.match_quality in ("species_ambiguous", "material_only_rejected"), ppC.match_quality)
ok("never claims 7.0 Pa as the precursor pressure", ppC.value != 7.0)

print("8) pulse-only evidence does not create a KB-supported ratio (Case 3)")
NOPRESS = [exp("p", "Al2O3", "TMA", "H2O", [cond("pulse_time", 0.1, "A", "s")])]
pp3 = mc.scoped_condition_prior(NOPRESS, "precursor_partial_pressure", "precursor_partial_pressure", "A",
                                "Al2O3", "TMA", "H2O")
pt3 = mc.scoped_condition_prior(NOPRESS, "precursor_pulse_time", "pulse_time", "A",
                                "Al2O3", "TMA", "H2O")
ok("pulse IS kb-supported", pt3.source == "kb", pt3.source)
r3, st3, _ = mc.build_ratio(pp3, pt3)
check("ratio unresolved", st3, "pressure_unresolved")
ok("ratio is not kb", r3.source != "kb", r3.source)
r4, st4, _ = mc.build_ratio(pp3, pt3, allow_fallback=True, fallback_value=1000.0)
check("opt-in fallback is labelled fallback", r4.source, "fallback")
ok("fallback confidence is low", r4.confidence <= 0.2, r4.confidence)
ok("fallback is never called kb/literature",
   "kb" not in r4.source and "literature" not in (r4.evidence or ""))

print("9) unresolved-reason states are distinguished, not collapsed")
seen = {st3, st_mix,
        mc.build_ratio(ppC, pt)[1]}
ok("distinct reasons", len(seen) >= 2, seen)
ok("species-ambiguity is its own state",
   "pressure_species_ambiguous" in seen or "pressure_unresolved" in seen, seen)

print("10) unsupported chemistry is reported, not silently corrected (Case 2 variant)")
_, st5, _, n5 = mc.resolve_chemistry(SYNTH, "Al2O3", precursor="AlCl3", co_reactant="H2O")
check("status", st5, "unsupported")
ok("names what IS known", any("TMA + H2O" in n for n in n5), n5)

print("11) twin chemistry compatibility is assessed and is not overclaimed (Case 5)")
tc = mc.assess_twin_compatibility(ctx2, {"K": {"source": "kb"}, "c": {"source": "kb"}}, SYNTH)
ok("level is generic/unknown, never exact",
   tc.compatibility_level in ("generic_model", "unknown"), tc.compatibility_level)
check("not compatible", tc.compatible, False)
check("not safe for quantitative comparison", tc.safe_for_quantitative_comparison, False)
ok("explains the pooling", "chemistr" in (tc.evidence or "").lower(), tc.evidence)
tc2 = mc.assess_twin_compatibility(ctx2, {}, SYNTH)
check("no KB params -> unknown", tc2.compatibility_level, "unknown")
ok("missing parameters listed", set(tc2.missing_parameters) >= {"K", "c"}, tc2.missing_parameters)

print("12) design layer: material-only refuses to invent a chemistry ratio")
res = md.design(md.DesignRequest("Al2O3", 60e-6), experiments_fn=lambda: SYNTH,
                model_factory=lambda: _FakeTwin())
check("status", res["status"], "chemistry_ambiguous")
check("no candidate", res["best"], None)
check("ratio unresolved", res["context"].priors["ratio"].value, None)
ok("chemistry flagged ambiguous",
   res["context"].chemistry_resolution_status == "ambiguous",
   res["context"].chemistry_resolution_status)
ok("precursor listed unresolved", "precursor" in res["context"].unresolved,
   res["context"].unresolved)


class _FakeTwin:
    def __init__(self):
        self.pA = self.t_p = None
        self.kb_provenance = {}

    def prepare(self):
        pass

    def penetration_depth(self):
        import math
        return 1e-5 * math.sqrt(self.pA * self.t_p)


print("13) design layer: fallback requires an explicit opt-in and stays visible")
res2 = md.design(md.DesignRequest("Al2O3", 60e-6, allow_chemistry_fallback=True),
                 experiments_fn=lambda: SYNTH, model_factory=lambda: _FakeTwin())
check("now designs", res2["status"], "designed")
check("ratio source", res2["context"].priors["ratio"].source, "fallback")
ok("fallback-dependent", res2["coverage"]["fallback_dependent_result"])
ok("chemistry still ambiguous", res2["coverage"]["chemistry_ambiguous"])
ok("not safe for quantitative use", res2["coverage"]["safe_for_quantitative_use"] is False)
ok("twin unverified", res2["coverage"]["twin_chemistry_unverified"])

print("14) design layer: explicit chemistry scopes the priors")
res3 = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O"),
                 experiments_fn=lambda: SYNTH, model_factory=lambda: _FakeTwin())
check("chemistry fully specified", res3["context"].chemistry_resolution_status, "fully_specified")
check("ratio is chemistry-supported", res3["context"].priors["ratio"].source, "kb")
ok("ratio = 50/0.1", abs(res3["context"].value("ratio") - 500.0) < 1e-9,
   res3["context"].value("ratio"))
ok("designs", res3["status"] == "designed", res3["status"])
ok("chemistry NOT ambiguous", not res3["coverage"]["chemistry_ambiguous"])
ok("but twin still unverified -> not quantitatively safe",
   res3["coverage"]["safe_for_quantitative_use"] is False)

print("15) certificate report identifies precursor / co-reactant and branch comparison")
# MIGRATED: frozen requirement 11 reorganises the report. The chemistry information now
# lives in the branch-comparison (§6) and supporting-evidence (§7) sections; the
# material-only case renders one independently-evaluated branch per chemistry.
import tempfile
with tempfile.TemporaryDirectory() as td:
    h = md.render_report(res3, out_path=Path(td) / "c.html").read_text()
    ok("branch-comparison section present", "Chemistry alternatives and branch comparison" in h)
    ok("supporting-evidence section present", "Supporting evidence" in h)
    ok("shows precursor", "TMA" in h)
    ok("shows co-reactant", "H2O" in h)
    ok("shows twin-kinetics compatibility level", "compatibility" in h)
    ok("states cross-chemistry comparison safety", "cross-chemistry comparison" in h)
    h2 = md.render_report(res, out_path=Path(td) / "a.html").read_text()
    ok("material-only renders a branch comparison table",
       "Chemistry alternatives and branch comparison" in h2)
    ok("branch comparison names both systems", "TMA + H2O" in h2 and "TMA + O3" in h2)
    ok("branch comparison states independent evaluation (no pooling)",
       "evaluated" in h2 and "independently" in h2)
check("one canonical artifact name", md.CANONICAL_REPORT, "m2_report.html")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
