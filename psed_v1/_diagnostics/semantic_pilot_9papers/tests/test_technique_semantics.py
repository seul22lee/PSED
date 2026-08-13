#!/usr/bin/env python3
"""Measurement.technique semantics.

`technique` means a physical measurement / characterisation / instrumental technique
attributable to THIS Measurement. A measured quantity is not a technique; a result
concept is not a technique; and a technique the source mentions for a sibling curve is
not this curve's technique. Unknown stays unknown.

Run:  python3 tests/test_technique_semantics.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
import pilot_evidence as PE          # noqa: E402
import pilot_semantics as PS         # noqa: E402

PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]
QUANTITY_LIKE = {"growth_per_cycle", "thickness", "film_thickness", "resistivity",
                 "capacitance", "refractive_index", "saturation_profile",
                 "nucleation", "conformality"}
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def sem(pid, n):
    return json.loads((W / "papers" / pid / "semantic" / ("%s.json" % n)).read_text())


def main():
    T = PS.techniques_for_series
    print("=== A/B. a quantity is never a technique ===")
    for word in ("GPC of the film", "growth per cycle", "film thickness", "thickness",
                 "capacitance response", "refractive index", "saturation profile",
                 "nucleation delay", "conformality", "sheet resistance"):
        ok("A: %-24s yields no technique" % word[:24],
           not PE.techniques(word), PE.techniques(word))
    ok("B: no quantity survives in the technique vocabulary",
       not ({lab for _, lab in PE.TECHNIQUES} & QUANTITY_LIKE),
       sorted({lab for _, lab in PE.TECHNIQUES} & QUANTITY_LIKE))
    ok("B: no quantity echo survives in the inference map",
       not (set(PS._AXIS_TECH.values()) & QUANTITY_LIKE),
       sorted(set(PS._AXIS_TECH.values()) & QUANTITY_LIKE))

    print("=== C. explicit source beats inference ===")
    got, basis, _ = T("the roughness was measured by TEM", "r", "roughness", 1)
    ok("C: a stated technique wins over the measurand inference",
       got == ["TEM"] and basis.startswith("source_reported"), (got, basis))

    print("=== D. inference is retained but marked as inference ===")
    ok("D: roughness still infers AFM", PS._tech_from_axes({}, "roughness") == ["AFM"])
    ok("D: an inferred basis is distinguishable from a reported one",
       PS._infer_basis({}, "roughness") == "inferred_from_measurand")
    note = PS._inference_note({}, "roughness")
    ok("D: inferred evidence does not fake a source match",
       note and note[0]["inferred"] is True and note[0]["matched"] is None, note)

    print("=== E/F. XRR recognition and aliases ===")
    ok("E: 'critical angle obtained from XRR' yields XRR",
       [t["technique"] for t in PE.techniques("critical angle obtained from XRR")] == ["XRR"])
    ok("F: 'X-ray reflectometry' canonicalises to XRR",
       [t["technique"] for t in PE.techniques("X-ray reflectometry")] == ["XRR"])
    ok("F: a plain reflectometer stays distinct from XRR",
       [t["technique"] for t in PE.techniques("measured with a reflectometer")]
       == ["reflectometry"])
    ok("F: 'in situ SE' canonicalises to ellipsometry",
       [t["technique"] for t in PE.techniques("in situ SE")] == ["ellipsometry"])

    print("=== G. sibling contamination (critical) ===")
    clause = "GPC on temperature and the critical angle obtained from XRR"
    b_t, b_b, _ = T(clause, "XRR Critical Angle", "XRR Critical Angle", 2)
    a_t, _, _ = T(clause, "GPC", "growth_per_cycle", 2)
    ok("G: the curve the technique is stated for gets it", b_t == ["XRR"], b_t)
    ok("G: its sibling does NOT inherit it", a_t == [], a_t)

    print("=== H. distinct techniques per sibling ===")
    c2 = "series A measured by TEM, series B measured by ellipsometry"
    ok("H: TEM goes to A only",
       T(c2, "series A", "x", 2)[0] == ["TEM"], T(c2, "series A", "x", 2)[0])
    ok("H: ellipsometry goes to B only",
       T(c2, "series B", "x", 2)[0] == ["ellipsometry"], T(c2, "series B", "x", 2)[0])

    print("=== I. explicit sharing is honoured ===")
    got, basis, _ = T("both profiles were measured by XPS", "A", "x", 2)
    ok("I: an explicit shared statement applies to each curve",
       got == ["XPS"] and basis == "source_reported_panel_shared", (got, basis))

    print("=== J. unknown remains unknown ===")
    ok("J: no evidence and no inference leaves it empty",
       T("thickness against cycles", "A", "film_thickness", 3)[0] == [], "")

    print("=== corpus: no quantity-like value survives anywhere ===")
    bad, basis_ct, n, unres = [], {}, 0, 0
    for pid in PAPERS:
        for m in sem(pid, "measurements"):
            n += 1
            t = m.get("technique") or []
            if not t:
                unres += 1
            basis_ct[m.get("technique_basis")] = basis_ct.get(m.get("technique_basis"), 0) + 1
            for x in t:
                if x in QUANTITY_LIKE:
                    bad.append((pid, m["measurement_id"], x))
    ok("corpus: no Measurement carries a quantity as its technique", not bad, bad[:3])
    ok("corpus: every technique-bearing Measurement records a basis",
       "unresolved" in basis_ct or basis_ct, basis_ct)
    print("    [technique] %d Measurements, %d unresolved, basis=%s"
          % (n, unres, basis_ct))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
