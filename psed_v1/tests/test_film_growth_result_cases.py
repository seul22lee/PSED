#!/usr/bin/env python3
"""Production counts: `film_growth_result_cases`.

This metric counts ExperimentalCases whose REPORTED MEASURAND belongs to the film-growth
result set. It is a result-type tally, not a count of physical depositions: the predicate
consults no run identity, no Sample, and no same-run evidence, so a case leaves the tally
merely by reporting a different measurand.

It was previously called `deposition_runs`, which invited exactly that misreading -- a
y-axis correction on one figure moved the number by ten while every ExperimentalCase,
producer mapping and condition set stayed byte-identical. Explicit physical DepositionRun
objects are NOT modelled in production; the semantic pilot models them separately from
positive source evidence, and nothing here should be compared against them.

Run:  python3 tests/test_film_growth_result_cases.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.resolve.to_kb import _counts  # noqa: E402

#: the quantity set the tally is defined over
FILM_GROWTH = ("film_thickness", "growth_per_cycle", "growth_rate",
               "normalized_thickness", "step_coverage")

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def case(q):
    return {"measurand": {"quantity": q} if q is not None else None}


def count(cases):
    return _counts([], cases, [])["film_growth_result_cases"]


def main():
    print("=== A. name ===")
    c = _counts([], [case("growth_per_cycle")], [])
    ok("A: generated counts expose 'film_growth_result_cases'",
       "film_growth_result_cases" in c, sorted(c)[:5])
    ok("A: the misleading 'deposition_runs' key is gone",
       "deposition_runs" not in c)

    print("=== B. predicate behaviour ===")
    for q in FILM_GROWTH:
        ok("B: %-22s is counted" % q, count([case(q)]) == 1)
    for q in ("XRR Critical Angle Θ_c", "intensity", "resistivity",
              "capacitance", "vapor_pressure", "impurity_content"):
        ok("B: %-22s is NOT counted" % q[:22], count([case(q)]) == 0)
    ok("B: a case with no measurand is not counted", count([case(None)]) == 0)
    ok("B: an unsupported quantity (canonical None) is not counted",
       count([{"measurand": {"quantity": None, "unit": "deg"}}]) == 0)
    ok("B: mixed cases count only the film-growth ones",
       count([case("growth_per_cycle"), case("intensity"),
              case("film_thickness"), case("XRR Critical Angle Θ_c")]) == 2)

    print("=== C. this is a result-type tally, not a run count ===")
    # Two cases reporting the same film-growth measurand count twice even though nothing
    # says they were grown in different runs. That is correct FOR THIS METRIC and is why
    # it must not be read as a physical run count.
    ok("C: the tally counts result cases, not distinct physical runs",
       count([case("growth_per_cycle"), case("growth_per_cycle")]) == 2)
    # Changing only the reported measurand changes the tally, with no run/sample change.
    ok("C: changing only the measurand moves the tally",
       count([case("growth_per_cycle")]) == 1
       and count([case("XRR Critical Angle Θ_c")]) == 0)

    print("=== D. persisted production artifacts ===")
    files = sorted((W / "papers").glob("*/resolved/counts.json"))
    old, new, mism = [], 0, []
    for f in files:
        d = json.loads(f.read_text())
        if "deposition_runs" in d:
            old.append(f.parts[-3])
        if "film_growth_result_cases" in d:
            new += 1
            ej = f.parent / "experiments.json"
            if ej.exists():
                exps = json.loads(ej.read_text())
                want = sum(1 for c in exps
                           if (c.get("measurand") or {}).get("quantity") in FILM_GROWTH)
                if d["film_growth_result_cases"] != want:
                    mism.append((f.parts[-3], d["film_growth_result_cases"], want))
    ok("D: no persisted production counts still carry the old key", not old, old[:3])
    ok("D: every persisted counts.json carries the new key", new == len(files),
       (new, len(files)))
    ok("D: every persisted value equals the predicate over that paper's experiments",
       not mism, mism[:3])

    print("=== E. generic aggregation still works ===")
    # the repo's only counts.json reader sums all integer keys generically
    tot = {}
    for f in files:
        for k, v in json.loads(f.read_text()).items():
            if isinstance(v, int):
                tot[k] = tot.get(k, 0) + v
    ok("E: generic integer-key aggregation includes the renamed key",
       "film_growth_result_cases" in tot and tot["film_growth_result_cases"] > 0,
       tot.get("film_growth_result_cases"))
    ok("E: aggregation no longer sees the old key", "deposition_runs" not in tot)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
