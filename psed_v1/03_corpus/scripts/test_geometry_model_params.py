#!/usr/bin/env python3
"""Tests for geometry + model-parameter extraction (structure_type, aspect_ratio,
feature_width, sticking_probability, adsorption_rate_constant).

These five were present in the legacy 0604_kg pipeline and absent from the current KB.
The guards here encode the two failure modes that caused that:
  · structure/geometry_class were patched into experiments.json AFTER resolve, so every
    re-resolve erased them (all 672 experiments carried structure=None);
  · semantically different quantities were flattened onto one name (the legacy pipeline
    mapped an adsorption EQUILIBRIUM constant onto adsorption_rate_constant, and collapsed
    precursor A and B partial pressures onto a single key, keeping only the last).

  python3 scripts/test_geometry_model_params.py
"""
import importlib.util as u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT.parent / "02_extraction" / "output"

spec = u.spec_from_file_location("kb6", HERE / "06_to_kb.py")
kb6 = u.module_from_spec(spec); spec.loader.exec_module(kb6)
sys.path.insert(0, str(ROOT.parent / "02_extraction" / "stages"))
import lib

FAIL = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(name)


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


print("1) alias normalisation -> canonical quantity")
for raw, want in (("sticking coefficient", "sticking_probability"),
                  ("sticking probability", "sticking_probability"),
                  # the ontology distinguishes the INITIAL coefficient (s0/beta_0) from a
                  # lumped sticking probability — collapsing them would lose Arts' s0
                  ("initial sticking probability", "initial_sticking_coefficient"),
                  ("initial sticking coefficient", "initial_sticking_coefficient"),
                  ("adsorption rate constant", "adsorption_rate_constant"),
                  ("adsorption equilibrium constant", "adsorption_equilibrium_constant"),
                  ("equilibrium constant of adsorption", "adsorption_equilibrium_constant"),
                  ("structural aspect ratio", "aspect_ratio"),
                  ("aspect ratio", "aspect_ratio"),
                  ("channel width", "feature_width"),
                  ("trench width", "feature_width"),
                  ("channel height", "feature_height")):
    check(f"{raw!r}", lib.canon_quantity(raw), want)

print("2) semantic separation — near-miss concepts must NOT collapse")
pairs = [("sticking_probability", "reaction_probability"),
         ("sticking_probability", "recombination_probability"),
         ("sticking_probability", "initial_sticking_coefficient"),
         ("adsorption_rate_constant", "adsorption_equilibrium_constant"),
         ("feature_width", "feature_height"),
         ("feature_width", "feature_length"),
         ("feature_width", "penetration_depth")]
for a, b in pairs:
    ca, cb = lib.canon_quantity(a), lib.canon_quantity(b)
    ok(f"{a} != {b}", ca != cb and ca is not None and cb is not None, f"{ca} vs {cb}")
ok("total pressure is not an adsorption constant",
   lib.canon_quantity("total pressure") not in ("adsorption_rate_constant",
                                                "adsorption_equilibrium_constant"),
   lib.canon_quantity("total pressure"))

print("3) recipe_role placement (geometry vs model parameter vs control setting)")
for q, want in (("aspect_ratio", "structure"), ("feature_width", "structure"),
                ("sticking_probability", "model_parameter"),
                ("adsorption_rate_constant", "model_parameter"),
                ("adsorption_equilibrium_constant", "model_parameter")):
    check(f"recipe_role({q})", lib.recipe_role(q), want)

print("4) units — lengths normalise to nm, dimensionless/model units are untouched")
check("feature_width 0.1 mm -> nm", kb6._norm_unit("feature_width", 0.1, "mm"), (1e5, "nm"))
check("feature_width 1 µm -> nm", kb6._norm_unit("feature_width", 1, "µm"), (1e3, "nm"))
check("feature_height 500 nm stays", kb6._norm_unit("feature_height", 500, "nm"), (500.0, "nm"))
check("feature_length 1 m -> nm", kb6._norm_unit("feature_length", 1, "m"), (1e9, "nm"))
check("aspect_ratio stays dimensionless", kb6._norm_unit("aspect_ratio", 2000, None), (2000, None))
check("sticking_probability dimensionless", kb6._norm_unit("sticking_probability", 1e-4, None), (1e-4, None))
check("adsorption constant keeps Pa^-1",
      kb6._norm_unit("adsorption_equilibrium_constant", 219, "Pa^-1"), (219, "Pa^-1"))
check("model param 'm' unit is NOT length-converted",
      kb6._norm_unit("site_density", 5e18, "m^-2"), (5e18, "m^-2"))

print("5) only reported/derived values become facts; inferred ones do not")
check("FACTUAL_STATUS", sorted(kb6.FACTUAL_STATUS),
      ["derived_from_reported_dimensions", "directly_reported"])
ok("inferred_from_context is excluded", "inferred_from_context" not in kb6.FACTUAL_STATUS)

print("6) geometry_facts: structure + class survive resolve, conditions carry evidence")
st, gc, cs = kb6.geometry_facts("10.1063_1.5028178")
check("Ylilammi structure", st, "pillarhall_lhar")
check("Ylilammi geometry_class", gc, "lateral_channel")
ok("emits conditions", len(cs) > 0, len(cs))
for c in cs:
    ok(f"origin present on {c['quantity']}", bool(c.get("origin")))
    ok(f"evidence id on {c['quantity']}", bool((c.get("origin") or {}).get("evidence_id")))
    ok(f"status is factual on {c['quantity']}",
       (c.get("origin") or {}).get("status") in kb6.FACTUAL_STATUS)
st2, gc2, _ = kb6.geometry_facts("does_not_exist_doi")
check("missing geometry.json degrades gracefully", (st2, gc2), (None, None))

print("7) shared evidence id — paper-level fan-out is not independent evidence")
E = json.loads((OUT / "10.1063_1.5028178" / "resolved" / "experiments.json").read_text())
ar = [c for e in E for c in (e.get("controlled") or []) if c.get("quantity") == "aspect_ratio"]
if ar:
    ids = {(c.get("origin") or {}).get("evidence_id") for c in ar}
    ok("aspect_ratio fan-out shares ONE evidence id", len(ids) == 1, f"{len(ar)} copies, {len(ids)} id(s)")
    ok("aspect_ratio is paper-level", {(c.get("origin") or {}).get("level") for c in ar} == {"paper"})
else:
    print("  SKIP  aspect_ratio not yet resolved into experiments")

print("8) target-paper regression (not order-dependent)")


def conds(doi):
    p = OUT / doi / "resolved" / "experiments.json"
    if not p.is_file():
        return None
    E = json.loads(p.read_text())
    return E, {c.get("quantity") for e in E for c in (e.get("controlled") or [])}


for doi, want_struct, want_class, want_q in (
        ("10.1063_1.5028178", "pillarhall_lhar", "lateral_channel",
         {"aspect_ratio", "feature_width", "sticking_probability"}),
        ("10.1021_acs.jpcc.9b08176", None, None,
         {"aspect_ratio", "initial_sticking_coefficient", "recombination_probability"}),
        ("10.1039_d0cp03358h", "pillarhall_lhar", "lateral_channel", {"feature_height"})):
    r = conds(doi)
    if r is None:
        print(f"  SKIP  {doi} not resolved"); continue
    E, qs = r
    if want_struct:
        ok(f"{doi} structure", {e.get("structure") for e in E} == {want_struct},
           {e.get("structure") for e in E})
        ok(f"{doi} geometry_class", {e.get("geometry_class") for e in E} == {want_class},
           {e.get("geometry_class") for e in E})
    missing = want_q - qs
    ok(f"{doi} carries {sorted(want_q)}", not missing, f"missing {sorted(missing)}")

print("9) Yim reports only aspect-ratio RANGES — none may be asserted as a scalar")
g = json.loads((ROOT / "extracted" / "10.1039_d0cp03358h" / "geometry.json").read_text())
ars = [q for q in (g.get("quantities") or []) if q["quantity"] == "aspect_ratio"]
ok("no fabricated aspect_ratio for Yim", not ars, ars)
r = conds("10.1039_d0cp03358h")
if r:
    ok("and none reached its experiments", "aspect_ratio" not in r[1])

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
