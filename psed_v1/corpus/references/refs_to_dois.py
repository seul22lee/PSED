#!/usr/bin/env python3
"""
01_refs_to_dois.py — review DOIs → reference DOI lists (Crossref).

For each seed review:
  · GET https://api.crossref.org/works/{doi}  (polite pool: mailto in UA + param)
  · parse the `reference` array; keep Crossref-deposited DOIs directly
  · for refs without a DOI, resolve via Crossref bibliographic search
    (query.bibliographic, rows=1); accept only if score >= 60, else 'unresolved'
    (no guessing)
Outputs:
  · refsets/{review}_refs.csv   (per review)
  · refsets/merged_refs.csv     (DOI-deduplicated, with cited_by)
  · refsets/{review}_crossref.json   (raw snapshot, provenance)

Email is read from $UNPAYWALL_EMAIL / $CROSSREF_EMAIL (not hardcoded).
Rate-limited ~1 req/s on the search endpoint.
"""
import paths as P
import csv, json, os, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
REFSETS = ROOT / "refsets"
REFSETS.mkdir(parents=True, exist_ok=True)

REVIEWS = {"cremers2019": "10.1063/1.5060967", "popov2025": "10.1116/6.0004320"}
SEARCH_MIN_SCORE = 60.0
SEARCH_SLEEP_S = 1.0                       # ~1 req/s on the search endpoint
COLUMNS = ["review", "ref_index", "doi", "resolution_method", "match_score",
           "article_title", "journal", "year", "unstructured"]

def _email():
    """Resolved at RUN time, not import time -- importing this module used to
    kill the process when no email was configured."""
    e = os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("CROSSREF_EMAIL")
    if not e:
        cfg = P.RESOURCES / "config" / "corpus" / "email.txt"
        e = cfg.read_text().strip() if cfg.exists() else None
    if not e:
        sys.exit("Set $UNPAYWALL_EMAIL (or resources/config/corpus/email.txt) "
                 "for the Crossref polite pool.")
    return e


EMAIL = None
UA = {"User-Agent": f"PSED-corpus/0.1 (https://github.com/psed; mailto:{_email()})"}
SESSION = requests.Session()
SESSION.headers.update(UA)


def _norm_doi(d):
    if not d:
        return None
    d = str(d).strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d or None


def get_work(doi):
    r = SESSION.get(f"https://api.crossref.org/works/{doi}",
                    params={"mailto": _email()}, timeout=30)
    r.raise_for_status()
    return r.json()["message"]


def biblio_query(ref):
    """A bibliographic query string from a no-DOI reference; None if too sparse."""
    if ref.get("unstructured"):
        return ref["unstructured"]
    parts = [ref.get(k) for k in ("article-title", "author", "journal-title",
                                  "volume", "first-page", "year")]
    q = " ".join(str(p) for p in parts if p).strip()
    return q if len(q) >= 8 else None      # e.g. a bare 'year' is not resolvable


def resolve_bibliographic(ref):
    """(doi, score) via Crossref search; (None, score_or_None) if below threshold."""
    q = biblio_query(ref)
    if not q:
        return None, None
    time.sleep(SEARCH_SLEEP_S)
    try:
        r = SESSION.get("https://api.crossref.org/works",
                        params={"query.bibliographic": q, "rows": 1, "mailto": _email()},
                        timeout=30)
        if r.status_code != 200:
            return None, None
        items = r.json()["message"].get("items", [])
    except requests.RequestException:
        return None, None
    if not items:
        return None, None
    it = items[0]
    score = float(it.get("score", 0.0))
    doi = _norm_doi(it.get("DOI"))
    return (doi, score) if (doi and score >= SEARCH_MIN_SCORE) else (None, score)


def _first(x):
    return x[0] if isinstance(x, list) and x else (x or "")


def process_review(name, review_doi):
    print(f"[{name}] fetching {review_doi} …")
    msg = get_work(review_doi)
    (REFSETS / f"{name}_crossref.json").write_text(json.dumps(msg, indent=1))
    refs = msg.get("reference", [])
    print(f"[{name}] {len(refs)} references")
    rows, n_dep, n_bib, n_un = [], 0, 0, 0
    for i, ref in enumerate(refs):
        doi = _norm_doi(ref.get("DOI"))
        if doi:
            method, score = "crossref_deposited", ""
            n_dep += 1
        else:
            rdoi, sc = resolve_bibliographic(ref)
            if rdoi:
                doi, method, score = rdoi, "bibliographic_search", round(sc, 1)
                n_bib += 1
            else:
                method, score = "unresolved", (round(sc, 1) if sc is not None else "")
                n_un += 1
        rows.append({"review": name, "ref_index": i, "doi": doi or "",
                     "resolution_method": method, "match_score": score,
                     "article_title": _first(ref.get("article-title")),
                     "journal": _first(ref.get("journal-title")),
                     "year": ref.get("year", ""),
                     "unstructured": ref.get("unstructured", "")})
    out = REFSETS / f"{name}_refs.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader(); w.writerows(rows)
    print(f"[{name}] deposited={n_dep} bibliographic={n_bib} unresolved={n_un} "
          f"→ {out.relative_to(ROOT)}")
    return rows


def write_merged(all_rows):
    """DOI-deduplicated across reviews, with a pipe-joined cited_by column."""
    by_doi = {}
    for r in all_rows:
        if not r["doi"]:
            continue
        d = r["doi"]
        if d not in by_doi:
            by_doi[d] = {"doi": d, "cited_by": set(), "resolution_method": r["resolution_method"],
                         "article_title": r["article_title"], "journal": r["journal"],
                         "year": r["year"]}
        by_doi[d]["cited_by"].add(r["review"])
    rows = sorted(by_doi.values(), key=lambda x: (x["journal"] or "", x["year"] or ""))
    out = REFSETS / "merged_refs.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "cited_by", "resolution_method",
                                          "article_title", "journal", "year"])
        w.writeheader()
        for x in rows:
            x = dict(x); x["cited_by"] = "|".join(sorted(x["cited_by"]))
            w.writerow(x)
    both = sum(1 for x in by_doi.values() if len(x["cited_by"]) > 1)
    print(f"[merged] {len(rows)} unique DOIs ({both} cited by both) → {out.relative_to(ROOT)}")


def main():
    all_rows = []
    for name, doi in REVIEWS.items():
        all_rows += process_review(name, doi)
    write_merged(all_rows)


if __name__ == "__main__":
    main()
