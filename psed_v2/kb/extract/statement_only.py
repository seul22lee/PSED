#!/usr/bin/env python3
"""P132c: the statement-only setting and observation records of the 12 gold pilot/<paper_id>.facts.csv, classified by join only (report).

    python3 psed_v2/scripts/statement_only.py      # writes verify/d15/statement_only.csv and statement_only_summary.txt

A statement-only record is of type setting or observation with no quantity, value, value_text or qualifiers. Each is keyed on its
parent node (an activity, comparison, entity or derived row) and the parent's other value-bearing children (quantity present):
covered (one of them has the record's method: the link and the measurement are already data), covered_other_method (value-bearing
children, none with this method), uncovered (no value-bearing children). no_method: method empty; the rule then ignores the method.
mention_matches: yes when a mention equals the label_as_printed of an entity row of the same paper.
"""
import collections
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "verify" / "d15"
GOLD = sorted((ROOT / "pilot").glob("10.*.facts.csv"))
EMPTY = ["quantity", "value", "value_text", "qualifiers"]
CLASSES = ["covered", "covered_other_method", "uncovered"]


def classify(rec, siblings):
    vb = [s for s in siblings if s["quantity"] and s["fact_id"] != rec["fact_id"]]
    if not vb:
        return "uncovered"
    if not rec["method"] or any(s["method"] == rec["method"] for s in vb):
        return "covered"
    return "covered_other_method"


def main():
    out = []
    for path in GOLD:
        pid = path.name[: -len(".facts.csv")]
        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        byid = {r["fact_id"]: r for r in rows}
        children = collections.defaultdict(list)
        for r in rows:
            children[r["parent"]].append(r)
        labels = {r["label_as_printed"] for r in rows if r["type"] == "entity" and r["label_as_printed"]}
        for r in rows:
            if r["type"] not in ("setting", "observation") or any(r[c] for c in EMPTY):
                continue
            out.append(dict(pid=pid, fact_id=r["fact_id"], type=r["type"], method=r["method"], mentions=r["mentions"], evidence=r["evidence"],
                            **{"class": classify(r, children[r["parent"]])}, no_method="yes" if not r["method"] else "no",
                            parent_type=byid.get(r["parent"], {}).get("type", "missing"), parent_id=r["parent"],
                            mention_matches="yes" if any(m.strip() in labels for m in r["mentions"].split(";") if m.strip()) else "no",
                            statement=r["statement"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "statement_only.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    def table(title, key, cols):
        c = collections.Counter((x["class"], x[key]) for x in out)
        L = [title, "  " + f"{'':22s}" + "".join(f"{k[:12]:>13s}" for k in cols) + f"{'total':>8s}"]
        for cl in CLASSES:
            L.append("  " + f"{cl:22s}" + "".join(f"{c[(cl, k)]:13d}" for k in cols) + f"{sum(c[(cl, k)] for k in cols):8d}")
        return L + [""]

    L = [f"P132c statement-only records (setting/observation without {', '.join(EMPTY)}): {len(out)} in {len(GOLD)} gold facts.csv",
         f"no_method (rule applied with the method ignored): {sum(x['no_method'] == 'yes' for x in out)}; "
         f"mention_matches yes: {sum(x['mention_matches'] == 'yes' for x in out)}", ""]
    L += table("class x type:", "type", ["setting", "observation"])
    L += table("class x parent_type:", "parent_type", sorted({x["parent_type"] for x in out}))
    L += ["by paper (covered / covered_other_method / uncovered / no_method):"]
    for pid in sorted({x["pid"] for x in out}):
        xs = [x for x in out if x["pid"] == pid]
        L.append(f"  {pid:32s} " + " / ".join(str(sum(x["class"] == cl for x in xs)) for cl in CLASSES) + f" / {sum(x['no_method'] == 'yes' for x in xs)}")
    (OUT / "statement_only_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
