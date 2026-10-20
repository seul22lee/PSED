#!/usr/bin/env python3
"""P83: one line per ingested paper in ontology/absorption.csv, the saturation-curve data of the vocabulary: how the paper's records
map to the ontology (records, direct, alias, qualifier, new_pending, attribute, dropped, unmapped), computed from <pid>.facts.csv.

    python3 psed_v2/pilot/absorption.py <paper_id>      # appends or replaces the paper's row

records = facts with a quantity, a method, a material, a reactant or a structure value; direct = a quantity that is a live entry used
without qualifiers; alias = a quantity whose label_as_printed is an alias of the entry (the ontology's own wording); qualifier = an
entry plus qualifiers; new_pending = records whose quantity, method, species or structure id is a pending entry; attribute = an
attribute entry; dropped = quantity other (a free label); unmapped = anything else (0 when the check passes).
"""
import csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import vocab as V  # noqa: E402

OUT = HERE.parent.parent / "ontology" / "absorption.csv"
COLS = ["paper", "records", "direct", "alias", "qualifier", "new_pending", "attribute", "dropped", "unmapped"]


def row(pid):
    c = dict.fromkeys(COLS, 0); c["paper"] = pid
    aliases = {a.lower(): i for i, e in L.ENTRIES.items() for a in e.get("aliases", [])}
    for f in csv.DictReader((HERE / f"{pid}.facts.csv").open(encoding="utf-8")):
        if "#" not in f["fact_id"] or f["type"] in ("claim", "caveat", "definition") and not f["quantity"]:
            continue
        q, m = f["quantity"], f["method"]
        if not (q or m):
            continue
        c["records"] += 1
        if q in V.PENDING or m in V.PENDING or f["value_text"] in V.PENDING:
            c["new_pending"] += 1
        elif q == "other":
            c["dropped"] += 1
        elif q in L.ATTRIBUTES:
            c["attribute"] += 1
        elif q and f["qualifiers"].strip():
            c["qualifier"] += 1
        elif q and f["label_as_printed"].lower() in aliases and aliases[f["label_as_printed"].lower()] == q:
            c["alias"] += 1
        elif q in L.ENTRIES or (not q and m in L.METHODS):
            c["direct"] += 1
        else:
            c["unmapped"] += 1
    return c


def write(pid):
    rows = [r for r in csv.DictReader(OUT.open(encoding="utf-8"))] if OUT.exists() else []
    rows = [r for r in rows if r["paper"] != pid] + [row(pid)]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    return rows[-1]


if __name__ == "__main__":
    print(write(sys.argv[1]))
