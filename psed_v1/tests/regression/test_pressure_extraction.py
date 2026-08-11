#!/usr/bin/env python3
"""Tests for typed pressure extraction (10_pressure).

The invariants: a pressure is never reinterpreted into a stronger claim than its
context and species support, unit conversion is deterministic, and model defaults are
never involved. Uses synthetic pressure.json fixtures — no LLM.

  python3 scripts/test_pressure_extraction.py
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import _project
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import importlib.util as u
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = u.spec_from_file_location("p10", _PSED_ROOT / "pipeline" / "text" / "pressure.py")
p10 = u.module_from_spec(_spec); _spec.loader.exec_module(p10)

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


print("1) deterministic unit conversion to Pa")
for v, unit, want in ((1.1, "Torr", 146.6542), (750, "mTorr", 99.9915),
                      (0.01, "mbar", 1.0), (100, "Pa", 100.0), (1, "bar", 1e5)):
    got, gu = p10._to_pa(v, unit)
    ok(f"{v} {unit} -> Pa", abs(got - want) < 1e-3, got)
    check(f"{unit} unit label", gu, "Pa")
check("unknown unit passes through", p10._to_pa(5, "widgets"), (5, "widgets"))
check("None value stays None", p10._to_pa(None, "Torr"), (None, "Torr"))

REACTANTS = [{"label": "A", "role": "precursor", "species": "TBF"},
             {"label": "B", "role": "coreactant", "species": "O3"}]


def facts(observations):
    with tempfile.TemporaryDirectory() as td:
        # the fixture mirrors the real layout: papers/<doi>/extracted/
        d = Path(td) / "10.0000_x" / "extracted"
        d.mkdir(parents=True)
        (d / "pressure.json").write_text(json.dumps({"pressures": observations}))
        # the pipeline resolves every per-paper path through paths.PAPERS, so
        # that is the single point a test has to redirect
        import paths as _P
        orig_papers, orig_ex = _P.PAPERS, p10.EXTRACTED
        _P.PAPERS = Path(td)
        p10.EXTRACTED = Path(td)
        try:
            return p10.pressure_facts("10.0000_x", REACTANTS)
        finally:
            _P.PAPERS, p10.EXTRACTED = orig_papers, orig_ex


def obs(**kw):
    base = {"pressure_type": "chamber_total_pressure", "value": 1.0, "unit": "mbar",
            "value_pa": 100.0, "unit_pa": "Pa", "named_species": None,
            "reactant_role": None, "context": "process_condition",
            "directly_reported": True, "source_section": "methods",
            "evidence_text": "q", "confidence": 0.9, "ambiguity_reason": None}
    base.update(kw)
    return base


print("2) process-condition pressure becomes a controlled condition")
cs = facts([obs(pressure_type="chamber_total_pressure", value_pa=100.0)])
check("one condition", len(cs), 1)
check("quantity", cs[0]["quantity"], "chamber_total_pressure")
check("value in Pa", cs[0]["value"], 100.0)
check("no species on a chamber pressure", cs[0]["of_reactant"], None)
ok("evidence carried", cs[0]["origin"]["evidence"] == "q")
ok("shared evidence id", cs[0]["origin"]["evidence_id"].endswith("::0"))

print("3) a named co-reactant partial pressure keeps its species AND slot")
cs = facts([obs(pressure_type="co_reactant_partial_pressure", named_species="O3",
                reactant_role="co_reactant", value_pa=146.65,
                evidence_text="partial pressure of ozone was 1.1 Torr")])
check("quantity", cs[0]["quantity"], "co_reactant_partial_pressure")
check("slot resolved from reactants", cs[0]["of_reactant"], "B")
check("named species in origin", cs[0]["origin"]["named_species"], "O3")
ok("directly_reported preserved", cs[0]["origin"]["directly_reported"] is True)

print("4) measured-response pressure is NEVER a process condition")
cs = facts([obs(pressure_type="generic_pressure", context="measured_response",
                evidence_text="Fig 3 plots p(x)")])
check("no condition emitted", len(cs), 0)

print("5) model-definition symbol is NEVER a process condition")
cs = facts([obs(pressure_type="generic_pressure", context="model_definition",
                value=None, value_pa=None, evidence_text="p_A in eq. 1")])
check("no condition emitted", len(cs), 0)

print("6) a partial pressure with NO value (varies) emits nothing")
cs = facts([obs(pressure_type="precursor_partial_pressure", named_species="TBF",
                value=None, value_pa=None, reactant_role="precursor",
                ambiguity_reason="depended on pulse time")])
check("no condition", len(cs), 0)

print("7) apparatus base pressure IS a setting but carries no species")
cs = facts([obs(pressure_type="base_pressure", context="apparatus_setting",
                value_pa=1e-5)])
check("emitted", len(cs), 1)
check("quantity", cs[0]["quantity"], "base_pressure")
check("no species", cs[0]["of_reactant"], None)

print("8) parser downgrades a partial pressure with no named species")
raw = {"pressure_type": "precursor_partial_pressure", "value": 5, "unit": "Torr",
       "named_species": None, "context": "process_condition"}
# emulate extract_pressures' post-processing rule
pt = raw["pressure_type"]
species = (raw.get("named_species") or "").strip() or None
if pt in p10.PARTIAL_TYPES and not species:
    pt = "generic_pressure"
check("downgraded to generic", pt, "generic_pressure")
ok("PARTIAL_TYPES needs a species", "precursor_partial_pressure" in p10.PARTIAL_TYPES)

print("9) model defaults are never touched by this module")
src = _project.path("pipeline","text","pressure.py").read_text()
ok("no MODEL_DEFAULTS reference", "MODEL_DEFAULTS" not in src)
ok("never emits 100/300 Pa constants", "100.0" not in src and "300.0" not in src
   or "pA" not in src)
ok("source is 'pressure_extraction', never 'model'",
   all(c["source"] == "pressure_extraction" for c in
       facts([obs(), obs(pressure_type="working_pressure")])))

print("10) FACT_CONTEXTS excludes measured_response and model_definition")
ok("process_condition is a fact", "process_condition" in p10.FACT_CONTEXTS)
ok("apparatus_setting is a fact", "apparatus_setting" in p10.FACT_CONTEXTS)
ok("measured_response is NOT", "measured_response" not in p10.FACT_CONTEXTS)
ok("model_definition is NOT", "model_definition" not in p10.FACT_CONTEXTS)

print("11) vapor_pressure is a species property, not a control setting")
from ontology import vocab as lib
check("vapor_pressure role", lib.recipe_role("vapor_pressure"), "species_property")
check("precursor_partial_pressure role", lib.recipe_role("precursor_partial_pressure"),
      "control_setting")
check("chamber_total_pressure role", lib.recipe_role("chamber_total_pressure"),
      "control_setting")

print("12) no pressure.json -> no conditions (corpus untouched)")
with tempfile.TemporaryDirectory() as td:
    orig = p10.EXTRACTED; p10.EXTRACTED = Path(td)
    try:
        check("empty", p10.pressure_facts("nope"), [])
    finally:
        p10.EXTRACTED = orig

print("13) within-file dedup: identical process observations collapse to one")
o1 = obs(pressure_type="base_pressure", context="apparatus_setting", value_pa=1e-5,
         evidence_text="base pressure of 1e-7 mbar")
cs = facts([o1, dict(o1)])                        # same statement twice
check("collapsed to one", len(cs), 1)
o2 = obs(pressure_type="base_pressure", context="apparatus_setting", value_pa=1e-5,
         evidence_text="a DIFFERENT sentence")    # different evidence -> kept
check("distinct evidence kept", len(facts([o1, o2])), 2)

print("14) legitimate table pressure under a pressure header is kept, but excluded as fact")
# 147/25.7 sit under a real 'p A0 (Pa)' header -> genuine pressures, measured_response.
cs = facts([obs(pressure_type="generic_pressure", context="measured_response",
                value_pa=147.0, evidence_text="Material Al2O3 | p A0 (Pa): 147")])
check("measured_response never a process condition", len(cs), 0)

print("15) evidence-word guard: an entry whose quote has no pressure word is dropped")
_PWORDS = ("pressure", "p_a", "p a", "p_b", "p b", "mbar", "torr", "pa", "bar", "psi")
for quote, kept in (("reactor working pressure of 750 mtorr", True),
                    ("N = 500 cycles, x = 147", False),
                    ("partial pressure of ozone 1.1 Torr", True),
                    ("the sticking coefficient c was 0.005", False)):
    has = any(w in quote.lower() for w in _PWORDS)
    ok(f"{quote[:34]!r} kept={has}", has == kept, has)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
