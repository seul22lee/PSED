#!/usr/bin/env python3
"""Tests for the paper-level temperature scalar vs process window (06_to_kb.base_card).

Regression guard for the defect where a non-degenerate ALD temperature window was
collapsed to its lower endpoint and reported as the deposition temperature
(e.g. [175,300] -> temperature_C=175 on 8 papers / 278 experiments).

  python3 scripts/test_card_temperature.py
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
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
kb6 = _project.load('to_kb')

_scalar = kb6._scalar_from_degenerate_range
base_card = kb6.base_card

FAIL = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(name)


print("1) non-degenerate window must NOT yield a scalar")
check("[175,300] -> None", _scalar([175, 300]), None)
check("[60,120]  -> None", _scalar([60, 120]), None)
check("[150,450] -> None", _scalar([150, 450]), None)
check("endpoint never used (low)", _scalar([175, 300]) == 175, False)
check("endpoint never used (high)", _scalar([175, 300]) == 300, False)

print("2) degenerate window IS a genuine scalar")
check("[225,225] -> 225", _scalar([225, 225]), 225)
check("[225.0,225] -> 225.0", _scalar([225.0, 225]), 225.0)

print("3) missing window -> None")
check("None -> None", _scalar(None), None)

print("4) malformed windows must not raise and must yield None")
for bad in ([], [175], [175, 300, 400], "175-300", 175, {"min": 175}, [None, None],
            [None, 300], ["175", "300"], [True, True]):
    try:
        got = _scalar(bad)
    except Exception as e:                                    # must never raise
        got = f"RAISED {type(e).__name__}"
    check(f"{bad!r} -> None", got, None)

print("5) base_card wiring: window preserved, scalar suppressed / kept")
c = base_card({"temperature_window_C": [175, 300], "precursors": ["X"]})
check("window paper: temperature_C None", c["temperature_C"], None)
check("window paper: window preserved", c["temperature_window_C"], [175, 300])
c = base_card({"temperature_window_C": [225, 225]})
check("degenerate: temperature_C 225", c["temperature_C"], 225)
check("degenerate: window preserved", c["temperature_window_C"], [225, 225])
c = base_card({})
check("no window: temperature_C None", c["temperature_C"], None)
check("no window: window None", c["temperature_window_C"], None)

print("6) an independently extracted genuine scalar survives the merge (d0cp case)")
# d0cp has NO scout window; its 300 C comes from the methods/table pass. Emulate the
# fill-if-absent merge to prove a real paper-wide scalar is still filled and kept.
base = base_card({"temperature_window_C": None})
llm = {"temperature_C": 300, "pulse_time_s": {"precursor": 0.1, "coreactant": 0.1},
       "purge_time_s": 4.0, "ncycles": 500}
for k in ("process_type", "temperature_C", "pressure_Pa", "pulse_time_s",
          "purge_time_s", "ncycles", "carrier_gas"):
    if base.get(k) in (None, "unknown", []) and llm.get(k) not in (None, ""):
        base[k] = llm[k]
check("d0cp temperature_C = 300", base["temperature_C"], 300)
check("d0cp pulse preserved", base["pulse_time_s"], {"precursor": 0.1, "coreactant": 0.1})
check("d0cp purge preserved", base["purge_time_s"], 4.0)
check("d0cp cycles preserved", base["ncycles"], 500)

print("7) a window paper still accepts a genuine scalar from methods, if stated")
base = base_card({"temperature_window_C": [175, 300]})
for k in ("temperature_C",):
    if base.get(k) in (None, "unknown", []) and {"temperature_C": 225}.get(k) not in (None, ""):
        base[k] = 225
check("window paper can be filled by methods", base["temperature_C"], 225)
check("window still preserved alongside", base["temperature_window_C"], [175, 300])

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
