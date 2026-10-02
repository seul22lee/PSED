#!/usr/bin/env python3
"""Set in_scope in manifest.csv and write corpus/report.csv, a reader-facing view of it.

    python3 psed_v2/corpus/make_report.py

Run it after any change to the origin columns (popov, cremers, cremers_citing, extra_reason)
or to status. Every other script reads the in_scope column this one writes.

report.csv columns: doi, title, authors, journal, type, year, in_scope, collected (yes/no),
pdf_source, popov, cremers, cremers_citing, popov_ref, cremers_ref, cremers_context,
cites_cremers_keywords, extra_reason, status, reason, decision, decided_on.
collected is "yes" when pdf_status is ok, i.e. raw/<paper_id>.pdf exists and is a PDF.
"""
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
REPORT = HERE / "report.csv"

# The scope rule lives here and nowhere else. Current scope: conformality only.
# A paper is in scope if it comes from one of these origins and is not excluded.
# To widen the scope (e.g. to all of Popov), add the origin column name here and rerun.
SCOPE_ORIGINS = ("cremers", "cremers_citing", "extra_reason")
SCOPE_RULE = "(cremers or cremers_citing or extra) and status != excluded"

COLUMNS = ["doi", "title", "authors", "journal", "type", "year", "in_scope", "collected", "pdf_source",
           "popov", "cremers", "cremers_citing", "popov_ref", "cremers_ref", "cremers_context",
           "cites_cremers_keywords", "extra_reason", "status", "reason", "decision", "decided_on"]


def in_scope(row: dict) -> bool:
    return any(row.get(c, "").strip() for c in SCOPE_ORIGINS) and row.get("status", "") != "excluded"


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    if "in_scope" not in fields:
        fields.append("in_scope")
    for r in rows:
        r["in_scope"] = "yes" if in_scope(r) else "no"
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MANIFEST)

    out = []
    for r in rows:
        collected = r.get("pdf_status", "") == "ok"
        row = {c: r.get(c, "") for c in COLUMNS}
        row["collected"] = "yes" if collected else "no"
        row["pdf_source"] = r.get("pdf_source", "") if collected else ""
        out.append(row)
    with REPORT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)

    scope = Counter(r["in_scope"] for r in rows)
    print(f"scope rule: {SCOPE_RULE}")
    print(f"{MANIFEST.relative_to(HERE.parent.parent)}: {len(rows)} rows, in_scope yes {scope['yes']}, no {scope['no']}")
    print(f"{REPORT.relative_to(HERE.parent.parent)}: {len(out)} rows")
    for k, v in sorted(Counter(r["pdf_status"] for r in rows if r["in_scope"] == "yes").items(), key=lambda kv: -kv[1]):
        print(f"  in scope, pdf_status {k or '(blank)':<12} {v}")


if __name__ == "__main__":
    main()
