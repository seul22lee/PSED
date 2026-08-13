#!/usr/bin/env python3
"""Per-series axis override: representation and propagation.

A panel states its primary axes; a series may additionally carry its own `x`/`y` when the
figure shows that curve against a different axis. These tests fix the SELECTION rule and
the backward-compatible fallback, and they guard the far more common case -- many curves
sharing one axis -- against being reinterpreted as a multi-axis plot.

Run:  python3 tests/test_series_axis_override.py
"""
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.figures.figure_extract import effective_axis  # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


PANEL_Y = {"quantity": "growth_per_cycle", "unit": "Å", "log": False,
           "label_raw": "GPC (Å)", "unit_raw": "Å", "is_normalized": False,
           "normalization_expression": None, "normalization_denominator_symbol": None}
PANEL_X = {"quantity": "deposition_temperature", "unit": "°C", "log": False,
           "label_raw": "Temperature (°C)", "unit_raw": "°C"}


def series(label, **kw):
    s = {"label": label, "points": [[1, 2], [3, 4]]}
    s.update(kw)
    return s


def main():
    print("=== A. single axis, one series ===")
    ax, ovr = effective_axis(PANEL_Y, series("Thickness").get("y"))
    ok("A: a series with no override inherits the panel y",
       ax is PANEL_Y and not ovr, (ax, ovr))

    print("=== B. single axis, multiple series ===")
    got = [effective_axis(PANEL_Y, series(l).get("y")) for l in ("O", "Al", "Si")]
    ok("B: every element series inherits one intensity axis",
       all(a is PANEL_Y and not o for a, o in got))

    print("=== C. same quantity, different channels ===")
    got = [effective_axis(PANEL_Y, series(l).get("y")) for l in ("m/z = 18", "m/z = 44")]
    ok("C: m/z channels share the panel signal axis",
       all(a is PANEL_Y and not o for a, o in got))

    print("=== D. same quantity, provenance distinction ===")
    got = [effective_axis(PANEL_Y, series(l).get("y")) for l in ("Measured", "Simulated")]
    ok("D: measured and simulated share one axis",
       all(a is PANEL_Y and not o for a, o in got))

    print("=== E. same quantity, different techniques ===")
    got = [effective_axis(PANEL_Y, series(l).get("y")) for l in ("TEM", "SE")]
    ok("E: two techniques measuring one plotted quantity share one axis",
       all(a is PANEL_Y and not o for a, o in got))

    print("=== F. dual y axis ===")
    sec = {"quantity": "some_other_quantity", "unit": "deg", "label_raw": "Θ (deg)"}
    a1, o1 = effective_axis(PANEL_Y, series("A").get("y"))
    a2, o2 = effective_axis(PANEL_Y, series("B", y=sec).get("y"))
    ok("F: the series without an override keeps the panel axis", a1 is PANEL_Y and not o1)
    ok("F: the series with an override gets its own axis",
       a2 is sec and o2 and a2["quantity"] == "some_other_quantity", (a2, o2))

    print("=== G. several series sharing secondary semantics ===")
    b, _ = effective_axis(PANEL_Y, series("B", y=dict(sec)).get("y"))
    c, _ = effective_axis(PANEL_Y, series("C", y=dict(sec)).get("y"))
    ok("G: duplicated overrides both resolve, no axis identity needed",
       b["quantity"] == c["quantity"] == "some_other_quantity" and b is not c)

    print("=== H. secondary axis quantity unresolved ===")
    raw_only = {"quantity": None, "unit": None, "label_raw": "Θ_c (°)"}
    ax, ovr = effective_axis(PANEL_Y, series("X", y=raw_only).get("y"))
    ok("H: a raw label alone is real axis evidence", ovr is True, ovr)
    ok("H: the raw label is preserved", ax.get("label_raw") == "Θ_c (°)", ax)
    ok("H: an unresolved secondary quantity does NOT fall back to the panel quantity",
       ax.get("quantity") != PANEL_Y["quantity"], ax.get("quantity"))

    print("=== I. optional x override ===")
    sx = {"quantity": "cycle_number", "unit": "cycles", "label_raw": "Cycles"}
    ax, ovr = effective_axis(PANEL_X, series("B", x=sx).get("x"))
    ok("I: the same mechanism works for x", ovr and ax["quantity"] == "cycle_number")
    ok("I: x with no override still inherits the panel x",
       effective_axis(PANEL_X, series("A").get("x")) == (PANEL_X, False))

    print("=== J. empty / non-evidence overrides ===")
    for name, val in (("missing key", None), ("empty dict", {}),
                      ("nulls only", {"quantity": None, "unit": None, "label_raw": None}),
                      ("defaults only", {"log": False, "is_normalized": False}),
                      ("empty strings", {"quantity": "", "unit": "", "label_raw": ""}),
                      ("not a dict", "y")):
        ax, ovr = effective_axis(PANEL_Y, val)
        ok("J: %s falls back to the panel axis" % name, ax is PANEL_Y and not ovr, ax)

    print("=== safety: the panel axis is never mutated ===")
    before = dict(PANEL_Y)
    effective_axis(PANEL_Y, {"quantity": "x"})
    ok("panel axis object is not mutated", PANEL_Y == before)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
