#!/usr/bin/env python3
"""The not-ALD rule, for Cremers 2019 references and for the works citing Cremers 2019.

    python3 ald_filter.py        # fetches abstracts from OpenAlex, prints the rows; writes nothing

Rule (title + OpenAlex abstract, every hyphen character read as "-"): a row has an ALD term when
the text matches atomic[\\s-]layer (case-insensitive) or \\bALD\\b (case-sensitive).
A row is tested when
  - cremers = O, unless cremers_context has a table tag (II-V, VIII, IX): Cremers lists those as ALD data;
  - cremers_citing = O and no other origin.
A tested row without an ALD term is listed:
    exclude (auto)   it has an abstract
    judge by hand    it has no abstract (the title alone decides nothing)
The manifest's status, decision and reason are printed beside each row; this script never writes them.
"""

import csv
import re
from pathlib import Path

from citing_filter import abstract_text, is_hyphen
from fetch_pdfs import make_session, normalise_doi, openalex_works

MANIFEST = Path(__file__).resolve().parent / "manifest.csv"
ALD_TERMS = [re.compile(r"atomic[\s-]layer", re.I), re.compile(r"\bALD\b")]


def has_ald_term(text: str) -> bool:
    text = "".join("-" if is_hyphen(c) else c for c in text)
    return any(p.search(text) for p in ALD_TERMS)


def source(row: dict) -> str:
    """Which list the rule tests the row under ("" = not tested)."""
    if row["cremers"] == "O":
        return "" if row["cremers_context"] not in ("", "text") else "cremers"
    if row["cremers_citing"] == "O" and not (row["popov"] or row["extra_reason"]):
        return "cremers_citing"
    return ""


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["doi"].strip() and source(r)]
    works = openalex_works(make_session(), rows, select="doi,abstract_inverted_index")
    listed = {}   # (source, verdict) -> rows
    for r in rows:
        abstract = abstract_text(works.get(normalise_doi(r["doi"]), {}).get("abstract_inverted_index"))
        if has_ald_term(f"{r['title']} {abstract}"):
            continue
        verdict = "exclude (auto)" if abstract else "judge by hand"
        listed.setdefault((source(r), verdict), []).append(r)
    for (src, verdict), group in sorted(listed.items()):
        print(f"\n{src}, no ALD term, {verdict}: {len(group)}")
        for r in group:
            now = f"{r['status'] or 'undecided'} ({r['decision']}): {r['reason']}" if r["status"] else "undecided"
            print(f"  {r['cremers_ref'] or '-':>4} | {r['doi']} | {r['title'][:70]} | {now}")


if __name__ == "__main__":
    main()
