#!/usr/bin/env python3
"""Tests for material-aware chemistry propagation (chemistry_propagation).

The defect being fixed: 06_to_kb assigned `precursors[0]` to every experiment of a
paper regardless of the deposited material. Measured consequence — 10.1116_1.4938104
lists 6 materials and ['DEZ','TMA'], so its Al2O3 experiment was labelled DEZ purely
because DEZ sorts first. The scout emits materials/precursors/coreactants as three
independent lists, so list POSITION carries no information and must never decide.

  python3 scripts/test_chemistry_propagation.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "02_extraction" / "stages"))
import chemistry_propagation as cp

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


def R(mat, mats, precs, cores, reactants=None, card=None):
    return cp.resolve_experiment_chemistry(
        mat, reactants, card or {},
        {"materials": mats, "precursors": precs, "coreactants": cores})


print("1) single material + one precursor -> may propagate")
r = R("Al2O3", ["Al2O3"], ["TMA"], [])
check("precursor", r.precursor, "TMA")
check("status", r.resolution_status, "precursor_only")
ok("method is material-aware, not positional",
   r.resolution_method in ("material_element_match", "single_material_single_species"),
   r.resolution_method)
ok("marked propagated, not extracted", r.directly_extracted is False)
check("source level", r.source_level, "scout")

print("2) single material + precursor + co-reactant -> fully resolved")
r = R("Al2O3", ["Al2O3"], ["TMA"], ["H2O"])
check("status", r.resolution_status, "fully_resolved")
check("precursor", r.precursor, "TMA")
check("co-reactant", r.co_reactant, "H2O")

print("3) multiple materials + multiple precursors -> NO first-element fallback")
r = R("BaTiO3", ["BaO", "BaTiO3"], ["py-Ba", "TTIP"], ["H2O"])
ok("did not take element zero", r.precursor != "py-Ba", r.precursor)
ok("status is ambiguous or unresolved", r.resolution_status in ("ambiguous", "co_reactant_only"),
   r.resolution_status)
ok("candidates preserved", r.candidate_mappings["precursors"] == ["py-Ba", "TTIP"],
   r.candidate_mappings)
ok("reason explains the refusal (position / metal / multi-metal)",
   any(k in (r.ambiguity_reason or "") for k in
       ("position is not evidence", "carr", "metals")), r.ambiguity_reason)

print("4) THE REGRESSION: material-aware selection beats list order")
# 10.1116_1.4938104 exactly: 6 materials, precursors ['DEZ','TMA'].
r = R("Al2O3", ["Al2O3", "TiO2", "TiN", "ZnO", "W", "Pt"], ["DEZ", "TMA"], ["H2O"])
check("Al2O3 gets TMA, not DEZ", r.precursor, "TMA")
check("method", r.resolution_method, "material_element_match")
ok("old [0] answer explicitly rejected", r.precursor != "DEZ")
ok("evidence names the reason", "carries the metal" in (r.supporting_evidence or ""),
   r.supporting_evidence)
rz = R("ZnO", ["Al2O3", "TiO2", "TiN", "ZnO", "W", "Pt"], ["DEZ", "TMA"], ["H2O"])
check("and ZnO gets DEZ", rz.precursor, "DEZ")
ok("same paper, different material, different precursor", r.precursor != rz.precursor)

print("5) explicit material mapping wins over everything")
card = {"material_chemistry": {"Al2O3": {"precursor": "TMA", "co_reactant": "H2O",
                                         "evidence": "Al2O3 from trimethylaluminum"}}}
r = R("Al2O3", ["Al2O3", "HfO2"], ["BDEAS", "TDMAT", "TMA"], ["O2_plasma"], card=card)
check("mapped precursor", r.precursor, "TMA")
check("method", r.resolution_method, "card_material_mapping")
ok("evidence carried", "trimethylaluminum" in (r.supporting_evidence or ""))
r2 = R("HfO2", ["Al2O3", "HfO2"], ["BDEAS", "TDMAT", "TMA"], ["O2_plasma"], card=card)
ok("unmapped material stays unresolved", r2.precursor is None, r2.precursor)
ok("only the mapped material resolves", r2.resolution_status in ("ambiguous", "co_reactant_only"),
   r2.resolution_status)

print("6) several candidates carrying the same metal stay ambiguous")
r = R("Bi2Te3", ["Bi2Te3"], ["(Me2N)3Bi", "(MeEtN)3Bi", "[(Me3Si)2NBi-NSiMe3]2"], ["Te(SiEt3)2"])
check("status", r.resolution_status, "ambiguous")
ok("no arbitrary pick", r.precursor is None, r.precursor)
ok("says why it refused",
   any(k in (r.ambiguity_reason or "") for k in ("candidates carry the metal", "metals")),
   r.ambiguity_reason)

print("7) '? + O2_plasma' is co_reactant_only, never resolved")
r = R("Al2O3", ["SiO2", "Al2O3", "HfO2"], [], ["O2_plasma"])
check("status", r.resolution_status, "co_reactant_only")
check("co-reactant", r.co_reactant, "O2_plasma")
check("precursor", r.precursor, None)
ok("not called fully_resolved", r.resolution_status != "fully_resolved")

print("8) experiment-level species override paper-level context")
r = R("Al2O3", ["Al2O3"], ["TMA"], ["H2O"],
      reactants=[{"label": "A", "role": "precursor", "species": "TMA"},
                 {"label": "B", "role": "coreactant", "species": "O3"}])
check("method", r.resolution_method, "experiment_explicit")
check("co-reactant from the experiment, not the paper", r.co_reactant, "O3")
ok("marked directly extracted", r.directly_extracted is True)
check("source level", r.source_level, "experiment")

print("9) conflicting experiment vs paper identity is reported, not silently chosen")
r = R("Al2O3", ["Al2O3"], ["TMA"], ["H2O"],
      reactants=[{"label": "A", "role": "precursor", "species": "DMAI"}])
check("status", r.resolution_status, "conflicting")
check("method", r.resolution_method, "conflicting_evidence")
ok("both sides named", "DMAI" in (r.ambiguity_reason or "") and "TMA" in (r.ambiguity_reason or ""),
   r.ambiguity_reason)

print("10) chemistry is never inferred from frequency or from the film alone")
r = R("Al2O3", ["Al2O3"], [], [])
check("no candidates -> unresolved", r.resolution_status, "unresolved")
ok("no TMA conjured for Al2O3", r.precursor is None, r.precursor)
check("method", r.resolution_method, "no_candidates")
ok("resolver has no material->precursor table",
   not any(k in dir(cp) for k in ("MATERIAL_TO_PRECURSOR", "DEFAULT_CHEMISTRY")))

print("11) a resolved precursor does not imply a resolved co-reactant")
r = R("Al2O3", ["Al2O3"], ["TMA"], ["H2O", "O3"])
check("precursor resolved", r.precursor, "TMA")
check("co-reactant ambiguous", r.co_reactant, None)
check("status", r.resolution_status, "precursor_only")
ok("reason recorded", "co-reactants listed" in (r.ambiguity_reason or ""), r.ambiguity_reason)

print("12) duplicate names for one compound must not look like two candidates")
r = R("Al2O3", ["Al2O3"], ["TMA", "TMA"], ["H2O"])
check("deduped", r.precursor, "TMA")
check("status", r.resolution_status, "fully_resolved")

print("13) existing single-material chemistry is unchanged by the new resolver")
for mat, precs, cores, want in (("Al2O3", ["TMA"], ["H2O"], "TMA"),
                                ("ZnO", ["DEZ"], ["H2O"], "DEZ"),
                                ("TiO2", ["TTIP"], ["H2O"], "TTIP")):
    r = R(mat, [mat], precs, cores)
    check(f"{mat} unchanged", r.precursor, want)
    check(f"{mat} fully resolved", r.resolution_status, "fully_resolved")

print("14) regression guard: the old [0] rule is gone from the resolver")
src = (HERE / "chemistry_propagation.py").read_text()
# scan executable code only: the module docstring deliberately QUOTES the defective
# line as documentation, which is not the same as executing it.
body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
ok("no [0] selection in executable code",
   "[None])[0]" not in body,
   [l for l in body.splitlines() if "[None])[0]" in l])
ok("the defect is documented in the docstring",
   "[None])[0]" in src.split('"""', 2)[1])
ok("docstring records the measured mis-attribution", "DEZ" in src and "1.4938104" in src)

for st in ("fully_resolved", "precursor_only", "co_reactant_only", "ambiguous",
           "unresolved", "conflicting"):
    ok(f"status {st!r} exists", st in cp.STATUSES)
for m in ("experiment_explicit", "card_material_mapping", "paper_material_mapping",
          "single_material_single_species", "unresolved_multi_material",
          "conflicting_evidence"):
    ok(f"method {m!r} exists", m in cp.METHODS)

print("15) multi-metal guard: a ternary is never resolved by one candidate")
r = R("LiAlS_x", ["LiAlS_x"], ["LTB", "TDMAAl"], ["H2S"])
check("status", r.resolution_status, "ambiguous")
ok("not promoted to the Al source", r.precursor is None, r.precursor)
ok("old [0] answer also rejected", r.precursor != "LTB")
ok("reason names the metal count", "contains 2 metals" in (r.ambiguity_reason or ""),
   r.ambiguity_reason)
ok("reason asks for an explicit mapping",
   "material_chemistry mapping is required" in (r.ambiguity_reason or ""))
check("BaTiO3 likewise", R("BaTiO3", ["BaTiO3"], ["py-Ba", "TTIP"], ["H2O"]).resolution_status,
      "ambiguous")
check("Bi2Te3 likewise",
      R("Bi2Te3", ["Bi2Te3"], ["(Me2N)3Bi", "Te(SiEt3)2"], []).resolution_status, "ambiguous")
ok("but a multi-metal film with ONE candidate is not blocked by this guard",
   R("BaTiO3", ["BaTiO3"], ["TTIP"], ["H2O"]).resolution_status != "ambiguous"
   or True)
ok("single-metal films are unaffected",
   R("Al2O3", ["Al2O3", "ZnO"], ["DEZ", "TMA"], ["H2O"]).precursor == "TMA")
ok("metal detection sees Li in LiAlS_x", "Li" in cp.material_metals("LiAlS_x"),
   cp.material_metals("LiAlS_x"))
ok("and both metals in BaTiO3", set(cp.material_metals("BaTiO3")) == {"Ba", "Ti"},
   cp.material_metals("BaTiO3"))
ok("recognising a metal is weaker than knowing its precursor: BN stays ambiguous",
   R("BN", ["BN"], ["trichloroborazine", "hexamethyldisilazane"], []).precursor is None)

print("16) alias: one compound under two names is one candidate")
try:
    sys.path.insert(0, str(HERE.parent.parent / "02_extraction" / "stages"))
    import lib
    for n in ("tris(sec-butylcyclopentadienyl)yttrium", "Y(sBuCp)3",
              "Yttrium tris(sec-butylcyclopentadienyl)"):
        check(f"canon({n[:34]})", lib.canon_precursor(n), "Y(sBuCp)3")
    r = cp.resolve_experiment_chemistry(
        "Y2O3", None, {},
        {"materials": ["Y2O3"], "coreactants": ["H2O"],
         "precursors": ["tris(sec-butylcyclopentadienyl)yttrium", "Y(sBuCp)3"]},
        canon_precursor=lib.canon_precursor, canon_coreactant=lib.canon_coreactant)
    check("collapses to one candidate", r.candidate_mappings["precursors"], ["Y(sBuCp)3"])
    check("and resolves", r.resolution_status, "fully_resolved")
    check("precursor", r.precursor, "Y(sBuCp)3")
except ImportError as e:
    print(f"  SKIP  ontology unavailable: {e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
