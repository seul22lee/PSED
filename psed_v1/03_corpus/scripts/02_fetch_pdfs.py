#!/usr/bin/env python3
"""
02_fetch_pdfs.py — DOI → open-access PDF via Unpaywall.

For each DOI in refsets/merged_refs.csv (or a single review's CSV via --review):
  · GET https://api.unpaywall.org/v2/{doi}?email=$UNPAYWALL_EMAIL
  · if is_oa and best_oa_location.url_for_pdf → download to
    pdfs/{safe_doi}.pdf   (safe = DOI with / : and other specials → _)
  · validate: HTTP 200, body starts with %PDF-, size > 10 KB
Statuses: downloaded / already_have / not_oa / oa_no_pdf_url / http_error / not_found

Writes:
  · refsets/download_log.csv  (every DOI, its status + details)
  · refsets/manual_todo.csv   (failures only, sorted by journal, with a clickable
                               https://doi.org/{doi} column for batch manual download)

Resumable: DOIs whose PDF already exists (>10 KB) are marked already_have and skipped.
Drop manually-downloaded PDFs into pdfs/ using the same filename rule, then re-run.

  python3 scripts/02_fetch_pdfs.py                 # all merged DOIs
  python3 scripts/02_fetch_pdfs.py --review cremers2019
  python3 scripts/02_fetch_pdfs.py --limit 20      # test on the first 20
"""
import argparse, csv, os, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
REFSETS = ROOT / "refsets"
PDFS = ROOT / "pdfs"
PDFS.mkdir(parents=True, exist_ok=True)
MIN_PDF_BYTES = 10 * 1024
SLEEP_S = 1.0

EMAIL = os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("CROSSREF_EMAIL")
if not EMAIL:
    cfg = ROOT / "config" / "email.txt"
    EMAIL = cfg.read_text().strip() if cfg.exists() else None
if not EMAIL:
    sys.exit("Set $UNPAYWALL_EMAIL (or config/email.txt) — Unpaywall requires an email.")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"PSED-corpus/0.1 (mailto:{EMAIL})"})

LOG_COLS = ["doi", "cited_by", "journal", "status", "oa_status", "pdf_url", "file", "detail"]
TODO_COLS = ["doi", "doi_url", "journal", "status", "article_title", "year", "cited_by"]


def safe_doi(doi):
    return re.sub(r"[^A-Za-z0-9._-]", "_", doi.strip().lower())


def pdf_path(doi):
    return PDFS / f"{safe_doi(doi)}.pdf"


def load_rows(review):
    src = REFSETS / (f"{review}_refs.csv" if review else "merged_refs.csv")
    if not src.exists():
        sys.exit(f"{src} not found — run 01_refs_to_dois.py first.")
    rows, seen = [], set()
    for r in csv.DictReader(src.open()):
        doi = (r.get("doi") or "").strip().lower()
        if not doi or doi in seen:
            continue
        seen.add(doi)
        rows.append({"doi": doi, "cited_by": r.get("cited_by") or r.get("review", ""),
                     "journal": r.get("journal", ""), "article_title": r.get("article_title", ""),
                     "year": r.get("year", "")})
    return rows, src


def unpaywall(doi):
    try:
        r = SESSION.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": EMAIL}, timeout=30)
    except requests.RequestException as e:
        return None, f"request_error:{type(e).__name__}"
    if r.status_code == 404:
        return None, "not_found"
    if r.status_code != 200:
        return None, f"http_{r.status_code}"
    return r.json(), None


def download(url, dest):
    try:
        r = SESSION.get(url, timeout=60, stream=True, allow_redirects=True)
    except requests.RequestException as e:
        return False, f"download_error:{type(e).__name__}"
    if r.status_code != 200:
        return False, f"http_{r.status_code}"
    data = r.content
    if not data[:5].startswith(b"%PDF-"):
        return False, "not_a_pdf"
    if len(data) < MIN_PDF_BYTES:
        return False, f"too_small_{len(data)}b"
    dest.write_bytes(data)
    return True, f"{len(data)}b"


def fetch_one(row):
    doi = row["doi"]
    dest = pdf_path(doi)
    if dest.exists() and dest.stat().st_size > MIN_PDF_BYTES:
        return {"status": "already_have", "oa_status": "", "pdf_url": "",
                "file": dest.name, "detail": "exists"}
    data, err = unpaywall(doi)
    if err:
        return {"status": ("not_found" if err == "not_found" else "http_error"),
                "oa_status": "", "pdf_url": "", "file": "", "detail": err}
    oa = data.get("oa_status", "")
    if not data.get("is_oa"):
        return {"status": "not_oa", "oa_status": oa, "pdf_url": "", "file": "", "detail": ""}
    loc = data.get("best_oa_location") or {}
    url = loc.get("url_for_pdf")
    if not url:
        return {"status": "oa_no_pdf_url", "oa_status": oa, "pdf_url": "", "file": "",
                "detail": loc.get("url", "")}
    ok, detail = download(url, dest)
    if ok:
        return {"status": "downloaded", "oa_status": oa, "pdf_url": url,
                "file": dest.name, "detail": detail}
    return {"status": "http_error", "oa_status": oa, "pdf_url": url, "file": "", "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="cremers2019 | popov2025 (default: merged)")
    ap.add_argument("--limit", type=int, help="only the first N DOIs (testing)")
    args = ap.parse_args()

    rows, src = load_rows(args.review)
    if args.limit:
        rows = rows[:args.limit]
    print(f"[fetch] {len(rows)} DOIs from {src.name}")

    log, todo, counts = [], [], {}
    for i, row in enumerate(rows, 1):
        res = fetch_one(row)
        counts[res["status"]] = counts.get(res["status"], 0) + 1
        rec = {"doi": row["doi"], "cited_by": row["cited_by"], "journal": row["journal"], **res}
        log.append(rec)
        if res["status"] not in ("downloaded", "already_have"):
            todo.append({"doi": row["doi"], "doi_url": f"https://doi.org/{row['doi']}",
                         "journal": row["journal"], "status": res["status"],
                         "article_title": row["article_title"], "year": row["year"],
                         "cited_by": row["cited_by"]})
        if res["status"] not in ("already_have",):
            time.sleep(SLEEP_S)                       # polite only when we hit the API
        if i % 25 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)}  " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    with (REFSETS / "download_log.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS); w.writeheader(); w.writerows(log)
    todo.sort(key=lambda r: (r["journal"] or "~", r["doi"]))
    with (REFSETS / "manual_todo.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TODO_COLS); w.writeheader(); w.writerows(todo)

    got = counts.get("downloaded", 0) + counts.get("already_have", 0)
    print(f"\n[fetch] {got}/{len(rows)} have PDFs "
          f"({got*100//max(len(rows),1)}%). status: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"  → refsets/download_log.csv (all), refsets/manual_todo.csv ({len(todo)} to fetch manually)")


if __name__ == "__main__":
    main()
