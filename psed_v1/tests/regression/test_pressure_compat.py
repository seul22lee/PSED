#!/usr/bin/env python3
"""Regression: typed precursor pressure now reaches M2 (ratio) and M3 (twin pA), and
forbidden pressure types never do.

The §6 fixture is one Al2O3/TMA/H2O experiment carrying precursor_partial_pressure =
40 Pa (species A) and a precursor pulse of 0.1 s. It must feed the ratio and the twin;
switching that one condition to working_/generic_/chamber_ pressure must reject it.

  python3 test_pressure_compat.py
"""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

from twin import pressure_compat as pc
from twin import m2_chemistry as mc
from twin import m2_design as md
from twin import twin_validation as tv

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


def fixture(pressure_quantity):
    """One TMA/H2O experiment whose precursor pressure is stored under the given
    quantity name (40 Pa, slot A) plus a 0.1 s precursor pulse."""
    return [{
        "_pid": "synthetic_pp", "exp_id": "synthetic_pp-F1a-0", "material": "Al2O3",
        "precursors": ["TMA"], "coreactants": ["H2O"],
        "reactants": [{"label": "A", "role": "precursor", "species": "TMA"},
                      {"label": "B", "role": "coreactant", "species": "H2O"}],
        "controlled": [{"quantity": pressure_quantity, "value": 40.0, "of_reactant": "A",
                        "unit": "Pa", "source": "pressure_extraction"},
                       {"quantity": "pulse_time", "value": 0.1, "of_reactant": "A", "unit": "s"}],
    }]


def _exp(q):
    return fixture(q)[0]


print("1) adapter precedence + allow-list")
check("precursor precedence", pc.PRECURSOR_PRESSURE_QUANTITIES,
      ("precursor_partial_pressure", "reactant_A_partial_pressure", "partial_pressure"))
for bad in ("working_pressure", "chamber_total_pressure", "base_pressure",
            "generic_pressure", "delivery_line_pressure", "bubbler_pressure",
            "unknown_pressure_type", "vapor_pressure"):
    ok(f"{bad} is forbidden", bad in pc.FORBIDDEN_FOR_PARTIAL)
    ok(f"{bad} not read as precursor pressure", pc.precursor_pressure(_exp(bad))[0] is None)
check("typed precursor pressure is read", pc.precursor_pressure(_exp("precursor_partial_pressure"))[0], 40.0)
check("legacy partial_pressure still read", pc.precursor_pressure(_exp("partial_pressure"))[0], 40.0)
check("legacy reactant_A_partial_pressure read",
      pc.precursor_pressure(_exp("reactant_A_partial_pressure"))[0], 40.0)

print("2) precedence order: typed beats legacy when both present")
both = _exp("precursor_partial_pressure")
both["controlled"].append({"quantity": "partial_pressure", "value": 999.0,
                           "of_reactant": "A", "unit": "Pa"})
check("typed wins", pc.precursor_pressure(both)[0], 40.0)

print("3) M3 twin reads the typed precursor pressure (40 Pa)")
twin, *_rest = tv.build_twin(_exp("precursor_partial_pressure"))
prov = _rest[-1] if _rest and isinstance(_rest[-1], dict) else {}
check("twin.pA = 40", twin.pA, 40.0)
check("provenance is extracted", prov.get("pA"), "extracted")

print("4) M3 twin REJECTS forbidden pressure types (stays model default)")
for bad in ("working_pressure", "generic_pressure", "chamber_total_pressure", "base_pressure"):
    twin, *_r = tv.build_twin(_exp(bad))
    prov = _r[-1] if _r and isinstance(_r[-1], dict) else {}
    ok(f"{bad}: twin.pA stays default 100", twin.pA == 100, twin.pA)
    ok(f"{bad}: provenance is default", prov.get("pA") == "default")

print("5) M2 reads the typed precursor pressure into the ratio")
r = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O"),
              experiments_fn=lambda: fixture("precursor_partial_pressure"))
rp = r["context"].priors["ratio"]
check("ratio source", rp.source, "kb")
ok("ratio = 40 / 0.1 = 400", abs(r["context"].value("ratio") - 400.0) < 1e-9,
   r["context"].value("ratio"))
check("ratio_status chemistry-supported", r["context"].ratio_status, "chemistry_supported")

print("6) M2 REJECTS forbidden pressure types (ratio stays fallback/unresolved)")
for bad in ("working_pressure", "generic_pressure", "chamber_total_pressure", "base_pressure"):
    r = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                                   allow_chemistry_fallback=True),
                  experiments_fn=lambda q=bad: fixture(q))
    rp = r["context"].priors["ratio"]
    ok(f"{bad}: ratio NOT kb-supported", rp.source != "kb", rp.source)
    ok(f"{bad}: not safe for quantitative use",
       r["coverage"]["safe_for_quantitative_use"] is False)

print("7) co_reactant partial pressure never becomes a precursor pressure")
cx = _exp("precursor_partial_pressure")
cx["controlled"] = [{"quantity": "co_reactant_partial_pressure", "value": 146.65,
                     "of_reactant": "B", "unit": "Pa"},
                    {"quantity": "pulse_time", "value": 0.1, "of_reactant": "A", "unit": "s"}]
check("precursor pressure absent", pc.precursor_pressure(cx)[0], None)
twin, *_r = tv.build_twin(cx)
check("twin.pA falls to default", twin.pA, 100)
r = md.design(md.DesignRequest("Al2O3", 60e-6, precursor="TMA", co_reactant="H2O",
                               allow_chemistry_fallback=True),
              experiments_fn=lambda: [cx])
ok("M2 ratio not kb from a co-reactant pressure",
   r["context"].priors["ratio"].source != "kb", r["context"].priors["ratio"].source)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
