#!/usr/bin/env python3
"""Works citing Cremers 2019 (OpenAlex) against the conformality keyword rule.

    python3 citing_filter.py        # fetches from OpenAlex, writes cremers_citing_all.csv, prints a report

Reads manifest.csv to mark which works are already there; never writes to it.

Keyword rule (title + OpenAlex abstract):
  - text lowercased; every hyphen character (ASCII hyphen-minus, any Unicode dash, the
    soft hyphen and the minus sign) and every run of whitespace become one space;
  - a keyword may have any prefix and may end in s, es or ly, followed by a word boundary;
  - the 10 keywords are KEYWORDS below (matched_keywords lists them in that order, "; "-joined,
    as cites_cremers_keywords does in the manifest).

Output cremers_citing_all.csv, one row per citing work:
    doi, title, year, type, has_abstract, matched_keywords, passed (yes/no),
    in_manifest (yes/no, by DOI, any origin), fetched_on (date of this run)

The printed report classifies the passing works that are not in the manifest:
    new since 2026-10-01   OpenAlex created_date after the first pull (2026-10-01)
    unicode hyphen         passes only because a non-ASCII hyphen was normalised
    other                  anything else (e.g. a preprint whose article is in the manifest)
and lists the manifest's cremers_citing rows that now fail or are no longer citing works.
"""

import csv
import datetime as dt
import os
import re
import sys
import unicodedata
from pathlib import Path

from fetch_pdfs import OPENALEX, get_with_retry, make_session, normalise_doi

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
OUT = HERE / "cremers_citing_all.csv"

CREMERS_2019 = "W2931684697"          # OpenAlex id of doi:10.1063/1.5060967
FIRST_PULL = "2026-10-01"             # date of the pull behind the manifest's cremers_citing rows
KEYWORDS = ["conformality", "conformal", "high-aspect-ratio", "aspect ratio", "LHAR", "PillarHall",
            "step coverage", "trench", "penetration depth", "saturation profile"]
SELECT = "id,doi,title,publication_year,type,abstract_inverted_index,created_date"
FIELDS = ["doi", "title", "year", "type", "has_abstract", "matched_keywords", "passed",
          "in_manifest", "fetched_on"]


# ----------------------------------------------------------------------------- keyword rule

def is_hyphen(ch: str) -> bool:
    return unicodedata.category(ch) == "Pd" or ch in "­−"


def normalise(text: str, all_hyphens: bool = True) -> str:
    """Lowercase; hyphens (all of them, or only the ASCII one) and whitespace -> one space."""
    text = text.lower()
    text = "".join(" " if (is_hyphen(c) if all_hyphens else c == "-") else c for c in text)
    return re.sub(r"\s+", " ", text).strip()


PATTERNS = [(k, re.compile(re.escape(normalise(k)) + r"(?:s|es|ly)?\b")) for k in KEYWORDS]


def matched(text: str) -> list[str]:
    return [k for k, p in PATTERNS if p.search(text)]


# ----------------------------------------------------------------------------- openalex

def abstract_text(inverted: dict | None) -> str:
    if not inverted:
        return ""
    words = sorted((pos, w) for w, positions in inverted.items() for pos in positions)
    return " ".join(w for _, w in words)


def fetch_citing(session) -> list[dict]:
    params = {"filter": f"cites:{CREMERS_2019}", "per-page": 200, "select": SELECT, "cursor": "*"}
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params["mailto"] = mailto
    works: list[dict] = []
    while params["cursor"]:
        resp = get_with_retry(session, OPENALEX, params=params)
        if resp is None or resp.status_code != 200:
            sys.exit(f"OpenAlex request failed ({resp.status_code if resp else 'no response'})")
        data = resp.json()
        works.extend(data["results"])
        params["cursor"] = data["meta"].get("next_cursor")
    return works


# ----------------------------------------------------------------------------- main

def main() -> None:
    today = dt.date.today().isoformat()
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest = {normalise_doi(r["doi"]): r for r in csv.DictReader(f) if r["doi"].strip()}
    citing_in_manifest = {d for d, r in manifest.items() if r["cremers_citing"] == "O"}
    manifest_titles = {normalise(r["title"]): d for d, r in manifest.items() if r["title"]}

    works = fetch_citing(make_session())
    recs = []   # (csv row, OpenAlex work, passes with the ASCII hyphen alone)
    for w in works:
        doi = normalise_doi(w["doi"]) if w.get("doi") else ""
        title = w.get("title") or ""
        abstract = abstract_text(w.get("abstract_inverted_index"))
        text = f"{title} {abstract}"
        kws = matched(normalise(text))
        row = {"doi": doi, "title": title, "year": w.get("publication_year") or "", "type": w.get("type") or "",
               "has_abstract": "yes" if abstract else "no", "matched_keywords": "; ".join(kws),
               "passed": "yes" if kws else "no", "in_manifest": "yes" if doi in manifest else "no",
               "fetched_on": today}
        recs.append((row, w, bool(matched(normalise(text, all_hyphens=False)))))
    recs.sort(key=lambda t: (t[0]["doi"] == "", t[0]["doi"], t[0]["title"]))
    rows = [r for r, _, _ in recs]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)

    passed = [r for r in rows if r["passed"] == "yes"]
    print(f"citing works: {len(rows)} (no DOI: {sum(1 for r in rows if not r['doi'])}); "
          f"pass: {len(passed)}; of these in manifest: {sum(1 for r in passed if r['in_manifest'] == 'yes')}")
    print("passing, not in manifest:")
    for row, w, ascii_pass in recs:
        if row["passed"] == "no" or row["in_manifest"] == "yes":
            continue
        created = w.get("created_date", "")[:10]
        if created > FIRST_PULL:
            why = f"new since {FIRST_PULL} (created {created})"
        elif not ascii_pass:
            why = "unicode hyphen"
        elif normalise(row["title"]) in manifest_titles:
            why = f"other: same title as manifest row {manifest_titles[normalise(row['title'])]} (created {created})"
        else:
            why = f"other (created {created}, type {row['type']})"
        print(f"  {row['doi'] or '(no doi)'} | {row['year']} | {row['matched_keywords']} | {why}")
    by_doi = {r["doi"]: r for r in rows if r["doi"]}
    print("manifest cremers_citing rows that now fail:")
    for doi in sorted(citing_in_manifest):
        if doi not in by_doi:
            print(f"  {doi} | no longer among the citing works")
        elif by_doi[doi]["passed"] == "no":
            print(f"  {doi} | manifest keywords: {manifest[doi]['cites_cremers_keywords']}")
    differ = [d for d in sorted(citing_in_manifest) if d in by_doi
              and by_doi[d]["matched_keywords"] != manifest[d]["cites_cremers_keywords"]]
    print(f"manifest cremers_citing rows whose keyword list differs: {len(differ)}")
    for d in differ:
        print(f"  {d} | manifest: {manifest[d]['cites_cremers_keywords']} | now: {by_doi[d]['matched_keywords']}")


if __name__ == "__main__":
    main()
