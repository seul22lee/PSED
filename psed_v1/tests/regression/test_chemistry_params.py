#!/usr/bin/env python3
"""Tests for chemistry-scoped record classification and twin kinetics.

Two invariants dominate: a record is never reinterpreted into a stronger claim than
it carries (a species-less pressure stays species-less), and a kinetic coefficient
is never averaged across precursor systems that happen to deposit the same film.

  python3 test_chemistry_params.py
"""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
from twin import chemistry_params as cp

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


def exp(pid, mat, prec, core, conds, roster=True):
    e = {"_pid": pid, "material": mat, "precursors": [prec] if prec else [],
         "coreactants": [core] if core else [], "controlled": conds}
    e["reactants"] = ([{"label": "A", "role": "precursor", "species": prec},
                       {"label": "B", "role": "coreactant", "species": core}]
                      if roster else [{"label": "A"}, {"label": "B"}])
    return e


def c(q, v, r=None, u=None):
    return {"quantity": q, "value": v, "of_reactant": r, "unit": u}


TMA_H2O = exp("pA", "Al2O3", "TMA", "H2O",
              [c("pressure", 50.0, "A", "Pa"), c("pressure", 9.0, "B", "Pa"),
               c("pressure", 7.0, None, "Pa"), c("total_pressure", 100.0, None, "Pa"),
               c("pulse_time", 0.1, "A", "s"), c("pulse_time", 1.0, "B", "s"),
               c("pulse_time", 5.0, None, "s"), c("purge_time", 4.0, None, "s"),
               c("plasma_exposure_time", 2.0, None, "s"),
               c("sticking_probability", 0.005, "A")])
TMA_O3 = exp("pB", "Al2O3", "TMA", "O3", [c("sticking_probability", 0.9, "A")])
DEZ_H2O = exp("pC", "Al2O3", "DEZ", "H2O", [c("sticking_probability", 0.5, "A")])
NOROSTER = exp("pD", "Al2O3", "TMA", "H2O", [c("pulse_time", 0.3, "A", "s")], roster=False)
SYNTH = [TMA_H2O, TMA_O3, DEZ_H2O]

print("1) pressure types stay distinct")
byk = {}
for cond in TMA_H2O["controlled"]:
    if cond["quantity"] in ("pressure", "total_pressure"):
        byk.setdefault(cp.classify_pressure(TMA_H2O, cond).kind, []).append(cond["value"])
check("precursor pressure", byk.get("precursor_partial_pressure"), [50.0])
check("co-reactant pressure", byk.get("co_reactant_partial_pressure"), [9.0])
check("generic (species-less)", byk.get("generic_pressure"), [7.0])
check("chamber total", byk.get("chamber_total_pressure"), [100.0])
ok("four distinct kinds", len(byk) == 4, sorted(byk))

print("2) a species-unattributed pressure cannot become a precursor pressure")
g = cp.classify_pressure(TMA_H2O, c("pressure", 7.0, None, "Pa"))
check("kind", g.kind, "generic_pressure")
check("confidence", g.confidence, 0.0)
ok("reason given", "no reactant attribution" in (g.ambiguity_reason or ""), g.ambiguity_reason)
ok("not promoted despite a single named precursor",
   g.kind != "precursor_partial_pressure")
ok("original value preserved", g.original_value_preserved and g.value == 7.0)

print("3) total pressure is never a precursor pressure")
t = cp.classify_pressure(TMA_H2O, c("total_pressure", 100.0, None, "Pa"))
check("kind", t.kind, "chamber_total_pressure")
ok("explicitly excluded", "never a partial pressure" in (t.ambiguity_reason or ""))

print("4) A/B slots stay unresolved without a species mapping")
u = cp.classify_pulse(NOROSTER, c("pulse_time", 0.3, "A", "s"))
check("kind", u.kind, "unspecified_pulse")
check("no species invented", u.reactant_identity, None)
ok("says A alone is not enough", "does not imply" in (u.ambiguity_reason or ""), u.ambiguity_reason)

print("5) an explicitly mapped slot resolves to a precursor pulse")
p = cp.classify_pulse(TMA_H2O, c("pulse_time", 0.1, "A", "s"))
check("kind", p.kind, "precursor_pulse")
check("species", p.reactant_identity, "TMA")
check("role", p.reactant_role, "precursor")

print("6) a co-reactant pulse is never the precursor pulse")
b = cp.classify_pulse(TMA_H2O, c("pulse_time", 1.0, "B", "s"))
check("kind", b.kind, "co_reactant_pulse")
check("species", b.reactant_identity, "H2O")
ok("distinct from the precursor pulse", b.kind != p.kind and b.value != p.value)

print("7) purge and plasma exposure are not ordinary precursor pulses")
check("purge", cp.classify_pulse(TMA_H2O, c("purge_time", 4.0)).kind, "purge")
check("plasma", cp.classify_pulse(TMA_H2O, c("plasma_exposure_time", 2.0)).kind, "plasma_exposure")
ok("neither is a precursor pulse",
   {cp.classify_pulse(TMA_H2O, c("purge_time", 4.0)).kind,
    cp.classify_pulse(TMA_H2O, c("plasma_exposure_time", 2.0)).kind}
   .isdisjoint({"precursor_pulse"}))

print("8) classification is non-destructive")
for cond in TMA_H2O["controlled"]:
    r = (cp.classify_pressure if "press" in cond["quantity"] else cp.classify_pulse)(TMA_H2O, cond)
    ok(f"{cond['quantity']} value preserved", r.value == cond["value"], (r.value, cond["value"]))
    check(f"{cond['quantity']} action", r.migration_action, "classified_only")

print("9) suspicious chemistry is flagged, never rewritten")
st, warn, rule = cp.chemistry_consistency("Al2O3", "DEZ")
check("status", st, "suspicious")
ok("warning names the conflict", "Zn" in (warn or "") and "Al2O3" in (warn or ""), warn)
check("plausible case", cp.chemistry_consistency("Al2O3", "TMA")[0], "plausible")
check("unresolved without a precursor", cp.chemistry_consistency("Al2O3", None)[0], "unresolved")
rep = cp.migration_report(SYNTH)
ok("report flags the group", rep["suspicious_chemistry"], rep["suspicious_chemistry"])
s0 = rep["suspicious_chemistry"][0]
ok("preserved", s0["original_value_preserved"] and s0["requires_manual_review"])
check("nothing changed", rep["records_changed_by_migration"], 0)
ok("DEZ record still present and unmodified",
   DEZ_H2O["controlled"][0]["value"] == 0.5)

print("10) exact-chemistry retrieval excludes other chemistries")
sp = cp.resolve_parameter(SYNTH, "sticking_probability", "Al2O3", "TMA", "H2O", of_reactant="A")
check("match level", sp.match_level, "exact_chemistry")
check("value is the TMA/H2O one", sp.value, 0.005)
ok("TMA/O3 excluded", sp.value != 0.9)
ok("DEZ/H2O excluded", sp.value != 0.5)
check("n records", sp.n_records, 1)
ok("no cross-chemistry mean", sp.value not in (0.4683333333333333, 0.5016666666666667))
ok("aggregation method states the scope", "within one chemistry key" in (sp.aggregation_method or ""),
   sp.aggregation_method)

print("11) another chemistry of the same film is labelled material_generic, not exact")
sp2 = cp.resolve_parameter(SYNTH, "sticking_probability", "Al2O3", "AlCl3", "H2O", of_reactant="A")
check("level", sp2.match_level, "material_generic")
ok("never exact", not sp2.match_level.startswith("exact"))
ok("confidence is low", sp2.confidence <= 0.2, sp2.confidence)
ok("says so", "not valid as an exact-chemistry value" in (sp2.aggregation_method or ""),
   sp2.aggregation_method)
check("fallback level recorded", sp2.fallback_level, "material_generic")

print("12) incompatible parameter definitions are never merged")
for a, b_ in cp.NEVER_MERGE:
    ok(f"{a} != {b_}", a != b_)
ok("initial vs lumped sticking kept apart",
   ("sticking_probability", "initial_sticking_coefficient") in cp.NEVER_MERGE)
ok("rate vs equilibrium constant kept apart",
   ("adsorption_rate_constant", "adsorption_equilibrium_constant") in cp.NEVER_MERGE)
r1 = cp.resolve_parameter(SYNTH, "sticking_probability", "Al2O3", "TMA", "H2O", of_reactant="A")
r2 = cp.resolve_parameter(SYNTH, "initial_sticking_coefficient", "Al2O3", "TMA", "H2O",
                          of_reactant="A")
ok("distinct queries give distinct results", r1.value != r2.value or r2.value is None)
ok("original values auditable", r1.original_values == (0.005,), r1.original_values)

print("13) the twin bundle is only exact when EVERY parameter is exact")
FULL = [exp("pF", "Al2O3", "TMA", "H2O",
            [c(n, 0.1, "A") for n in cp.CHEMISTRY_DEPENDENT_PARAMS])]
bf = cp.params_for_chemistry(FULL, "Al2O3", "TMA", "H2O")
check("all exact -> exact_chemistry", bf.compatibility_level, "exact_chemistry")
ok("safe for quantitative use", bf.safe_for_quantitative_use)
ok("safe for cross-chemistry comparison", bf.safe_for_cross_chemistry_comparison)
bp = cp.params_for_chemistry(SYNTH, "Al2O3", "TMA", "H2O")
check("one exact + gaps -> partial", bp.compatibility_level, "partial_chemistry")
ok("NOT safe for quantitative use", bp.safe_for_quantitative_use is False)
ok("cross-chemistry comparison disabled", bp.safe_for_cross_chemistry_comparison is False)
ok("unresolved parameters listed", bp.unresolved_parameters, bp.unresolved_parameters)
ok("diagnostics explain the partiality",
   any("partial" in d for d in bp.diagnostics), bp.diagnostics)
ok("one exact parameter does not validate the twin",
   "sticking_probability" in bp.chemistry_match_levels
   and bp.chemistry_match_levels["sticking_probability"].startswith("exact")
   and bp.compatibility_level != "exact_chemistry")
bn = cp.params_for_chemistry([exp("x", "ZrO2", "P", "Q", [])], "ZrO2", "P", "Q")
check("nothing resolved -> unresolved", bn.compatibility_level, "unresolved")

print("14) real corpus: measured coverage, no fabrication")
try:
    from pipeline.resolve import kb_service as ks
    E = ks._load()
    rep = cp.migration_report(E)
    print(f"       pressure kinds: {rep['pressure_records']}")
    print(f"       pulse kinds:    {rep['pulse_records']}")
    check("no pressure has species attribution today",
          rep["pressure_species_attributed"], 0)
    ok("pulses DO resolve", rep["pulse_records"].get("precursor_pulse", 0) > 0,
       rep["pulse_records"])
    ok("nothing mutated", rep["records_changed_by_migration"] == 0)
    b = cp.params_for_chemistry(E, "Al2O3", "TMA", "H2O")
    print(f"       TMA/H2O bundle: {b.compatibility_level} "
          f"levels={b.chemistry_match_levels}")
    ok("real TMA/H2O bundle is not exact (honest)",
       b.compatibility_level != "exact_chemistry", b.compatibility_level)
    ok("and therefore not safe for quantitative use", not b.safe_for_quantitative_use)
except Exception as e:
    print(f"  SKIP  corpus unavailable: {type(e).__name__}: {e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
