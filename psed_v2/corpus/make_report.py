#!/usr/bin/env python3
"""Write corpus/report.csv, a reader-facing view of manifest.csv.

Columns: doi, title, authors, journal, year, collected (yes/no), pdf_source.
collected is "yes" when pdf_status is ok, i.e. raw/<paper_id>.pdf exists and is a PDF.

    python3 psed_v2/corpus/make_report.py
"""
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
REPORT = HERE / "report.csv"
COLUMNS = ["doi", "title", "authors", "journal", "year", "collected", "pdf_source"]


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        collected = r.get("pdf_status", "") == "ok"
        out.append({
            "doi": r.get("doi", ""),
            "title": r.get("title", ""),
            "authors": r.get("authors", ""),
            "journal": r.get("journal", ""),
            "year": r.get("year", ""),
            "collected": "yes" if collected else "no",
            "pdf_source": r.get("pdf_source", "") if collected else "",
        })
    with REPORT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    by_source = Counter(r["pdf_source"] or "(not collected)" for r in out)
    print(f"{REPORT.relative_to(HERE.parent.parent)}: {len(out)} rows")
    for k, v in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<18} {v}")


if __name__ == "__main__":
    main()
