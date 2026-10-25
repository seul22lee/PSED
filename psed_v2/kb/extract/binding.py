#!/usr/bin/env python3
"""P177b (user): the binding regression. kb/reports/binding_regression.csv holds compile.bind()'s outcome for every item of every
compiled paper (compile.binding_rows: paper, panel, item, kind, unit, origin, role, how, reason). Every later apply re-checks it
(grow.py apply_here): an item the file binds to a unit must still be bound to that unit; an item it lists unbound may since be bound
(that is no failure). No model call.

    python3 psed_v2/kb/extract/binding.py --check     # exit 1 and the differences when an item lost its unit
    python3 psed_v2/kb/extract/binding.py --write     # the file anew from the compiled papers
"""
import csv
import sys

import common as C
import compile as K

FILE = C.V2 / "kb" / "reports" / "binding_regression.csv"
FIELDS = ["paper", "panel", "item", "kind", "unit", "origin", "role", "how", "reason"]


def current():
    """The outcome rows of every paper with records and compiled facts."""
    out = []
    for pid in C.E.PAPERS:
        if (C.RECORDS / f"{pid}.jsonl").exists() and (K.OUT / f"{pid}.facts.csv").exists():
            run = K.Run(pid)
            run.read()
            out += K.binding_rows(pid, run.binding)
    return out


def check(rows):
    """The items the file binds that are now unbound or bound to another unit."""
    if not FILE.exists():
        return []
    now = {(r["paper"], r["item"]): r for r in rows}
    bad = []
    for r in csv.DictReader(FILE.open(encoding="utf-8")):
        if not r["unit"]:
            continue
        n = now.get((r["paper"], r["item"]))
        if n is None or n["unit"] != r["unit"]:
            bad.append(f"{r['paper']} {r['item']}: was {r['unit']} ({r['how']}), now " + (f"{n['unit'] or 'unbound: ' + n['reason']}" if n else "no such item"))
    return bad


def write(rows):
    """P195 (user) A7a: the file's fields only (binding_rows also gives unit_fact_id, P184, which this file never carried), written to a
    temporary file that then replaces the file (a failure leaves the file as it was)."""
    import os
    tmp = FILE.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, FILE)


def main(argv):
    rows = current()
    if "--check" in argv:
        bad = check(rows)
        for b in bad:
            print(b)
        print(f"binding regression: {len(rows)} items, {len(bad)} lost their unit")
        return 1 if bad else 0
    if "--write" in argv:
        write(rows)
        print(f"binding regression: {len(rows)} items written to {FILE}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
