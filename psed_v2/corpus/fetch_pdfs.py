#!/usr/bin/env python3
"""Stage 0 of psed_v2: resolve open-access PDFs for the corpus manifest and download them.

Usage
    python3 fetch_pdfs.py --lookup      # OpenAlex lookup only; fills oa_* / pdf_url and title/authors/journal
    python3 fetch_pdfs.py --metadata    # OpenAlex lookup of title/authors/journal only; leaves OA columns alone
    python3 fetch_pdfs.py --download    # download rows that have a pdf_url and no file in raw/
    python3 fetch_pdfs.py               # lookup + download, in that order
    add --new to any of the above to act only on rows never looked up (blank oa_status),
    e.g. rows just appended to the manifest; earlier failed downloads are not retried

Manifest columns written by this script
    title, authors, journal
                OpenAlex title, authorships (display names joined by "; "), primary_location source
    year        OpenAlex publication_year, only when the manifest year is blank
    oa_status   OpenAlex open_access.oa_status (gold/green/hybrid/bronze/diamond/closed),
                or not_found when the DOI is unknown to OpenAlex
    license     best_oa_location.license (may be empty even when a PDF is available)
    oa_version  best_oa_location.version (publishedVersion / acceptedVersion / submittedVersion)
    pdf_url     best_oa_location.pdf_url (or the alternate location that actually worked)
    pdf_status  ok          raw/<paper_id>.pdf exists and starts with %PDF
                manual      no pdf_url, or the download did not yield a PDF; fetch by hand
                missing_doi the manifest row has no DOI
                (blank)     pdf_url known, download not attempted yet
    pdf_source  where the file in raw/ came from:
                openalex      best_oa_location.pdf_url, downloaded by this script
                openalex_alt  another OpenAlex `locations` entry (one-off pass, 2026-09-30)
                v1_copy       copied from the pre-purge psed_v1 checkout (one-off pass, 2026-09-30)
                (blank)       not collected

raw/<paper_id>.pdf (next to this script) is gitignored: paper_id is the DOI with "/" -> "_", lowercased.
Set OPENALEX_MAILTO to join the OpenAlex polite pool (optional).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
MANUAL_LIST = HERE / "manual_list.csv"
RAW = HERE / "raw"

OPENALEX = "https://api.openalex.org/works"
BATCH = 50
DOWNLOAD_INTERVAL = 1.0  # seconds between publisher requests
RETRIES = 4
TIMEOUT = 60
UA = "PSED-research (mailto:seullee2029@u.northwestern.edu)"

NEW_COLS = ["oa_status", "license", "oa_version", "pdf_url", "pdf_status",
            "title", "authors", "journal", "pdf_source"]


# ----------------------------------------------------------------------------- manifest io

def read_manifest() -> tuple[list[dict], list[str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    for c in NEW_COLS:
        if c not in fields:
            fields.append(c)
    for r in rows:
        for c in NEW_COLS:
            r.setdefault(c, "")
        r["doi"] = r["doi"].strip()
    return rows, fields


def write_manifest(rows: list[dict], fields: list[str]) -> None:
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MANIFEST)


def write_manual_list(rows: list[dict]) -> int:
    keep = ["popov", "cremers", "cremers_citing", "popov_ref", "cremers_ref", "paper_id", "doi", "year", "citation", "oa_status", "pdf_url", "pdf_status"]
    manual = [r for r in rows if r["pdf_status"] in ("manual", "missing_doi")
              and r.get("in_scope") == "yes"]   # in_scope is set by make_report.py
    with MANUAL_LIST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep, extrasaction="ignore")
        w.writeheader()
        w.writerows(manual)
    return len(manual)


def pdf_path(row: dict) -> Path:
    return RAW / f"{row['paper_id']}.pdf"


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


# ----------------------------------------------------------------------------- http helpers

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = UA
    return session


def get_with_retry(session: requests.Session, url: str, **kw) -> requests.Response | None:
    """GET with backoff on 429 and 5xx. Returns None when every attempt fails."""
    for attempt in range(RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT, **kw)
        except requests.RequestException as e:
            print(f"    request error ({e.__class__.__name__}); attempt {attempt + 1}/{RETRIES}", file=sys.stderr)
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = resp.headers.get("Retry-After")
            delay = float(wait) if wait and wait.isdigit() else 2 ** (attempt + 1)
            print(f"    HTTP {resp.status_code}; retrying in {delay:.0f}s", file=sys.stderr)
            resp.close()
            time.sleep(delay)
            continue
        return resp
    return None


# ----------------------------------------------------------------------------- openalex

def normalise_doi(doi: str) -> str:
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def openalex_works(session: requests.Session, rows: list[dict], select: str) -> dict[str, dict]:
    """Query OpenAlex for the rows' DOIs in batches of BATCH. Returns {normalised doi: work}."""
    params_base = {"per-page": BATCH, "select": select}
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params_base["mailto"] = mailto
    found: dict[str, dict] = {}
    n_batches = (len(rows) + BATCH - 1) // BATCH
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        params = dict(params_base, filter="doi:" + "|".join(r["doi"] for r in chunk))
        resp = get_with_retry(session, OPENALEX, params=params)
        if resp is None or resp.status_code != 200:
            code = resp.status_code if resp is not None else "no response"
            print(f"  batch {i // BATCH + 1}: OpenAlex failed ({code}); rows left untouched", file=sys.stderr)
            continue
        results = resp.json().get("results", [])
        for work in results:
            if work.get("doi"):
                found[normalise_doi(work["doi"])] = work
        print(f"  batch {i // BATCH + 1}/{n_batches}: {len(chunk)} queried, {len(results)} returned")
        time.sleep(0.2)
    return found


def apply_metadata(row: dict, work: dict) -> None:
    row["title"] = (work.get("title") or "").strip()
    row["authors"] = "; ".join(
        (a.get("author") or {}).get("display_name") or "" for a in work.get("authorships") or []
    ).strip("; ")
    loc = work.get("primary_location") or {}
    source = loc.get("source") or {}
    row["journal"] = source.get("display_name") or loc.get("raw_source_name") or ""
    if not row.get("year") and work.get("publication_year"):
        row["year"] = str(work["publication_year"])


def apply_oa(row: dict, work: dict) -> None:
    oa = work.get("open_access") or {}
    best = work.get("best_oa_location") or {}
    row["oa_status"] = oa.get("oa_status") or ""
    row["license"] = best.get("license") or ""
    row["oa_version"] = best.get("version") or ""
    row["pdf_url"] = best.get("pdf_url") or ""


def lookup(rows: list[dict], fields: list[str], scope: list[dict] | None = None) -> None:
    session = make_session()
    scope = rows if scope is None else scope
    with_doi = [r for r in scope if r["doi"]]
    for r in scope:
        if not r["doi"]:
            r["pdf_status"] = "missing_doi"

    found = openalex_works(session, with_doi,
                           "doi,title,publication_year,authorships,primary_location,open_access,best_oa_location")
    for r in with_doi:
        work = found.get(normalise_doi(r["doi"]))
        collected = is_pdf(pdf_path(r))
        if work is None:
            r["oa_status"] = "not_found"
            if not collected:
                r["license"] = r["oa_version"] = r["pdf_url"] = ""
        else:
            apply_metadata(r, work)
            if not collected:  # keep the url/license that actually produced the file
                apply_oa(r, work)
            else:
                r["oa_status"] = (work.get("open_access") or {}).get("oa_status") or ""
        if collected:
            r["pdf_status"] = "ok"
        elif not r["pdf_url"]:
            r["pdf_status"] = "manual"
        else:
            r["pdf_status"] = ""  # pending download
    write_manifest(rows, fields)


def metadata(rows: list[dict], fields: list[str], scope: list[dict] | None = None) -> None:
    session = make_session()
    with_doi = [r for r in (rows if scope is None else scope) if r["doi"]]
    found = openalex_works(session, with_doi, "doi,title,publication_year,authorships,primary_location")
    n = 0
    for r in with_doi:
        work = found.get(normalise_doi(r["doi"]))
        if work is not None:
            apply_metadata(r, work)
            n += 1
    print(f"  metadata filled for {n}/{len(with_doi)} rows with DOI")
    write_manifest(rows, fields)


# ----------------------------------------------------------------------------- download

def download(rows: list[dict], fields: list[str], scope: list[dict] | None = None) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    session = make_session()
    session.headers["Accept"] = "application/pdf,*/*;q=0.8"

    todo = [r for r in (rows if scope is None else scope)
            if r["doi"] and r["pdf_url"] and r["pdf_status"] != "ok"]
    print(f"  {len(todo)} rows to download")
    last_request = 0.0
    for n, r in enumerate(todo, 1):
        target = pdf_path(r)
        if target.exists():
            if is_pdf(target):
                r["pdf_status"] = "ok"
                continue
            target.unlink()  # stale non-PDF leftover

        wait = DOWNLOAD_INTERVAL - (time.monotonic() - last_request)
        if wait > 0:
            time.sleep(wait)
        last_request = time.monotonic()

        resp = get_with_retry(session, r["pdf_url"], stream=True, allow_redirects=True)
        ok = False
        if resp is not None and resp.status_code == 200:
            tmp = target.with_suffix(".part")
            with tmp.open("wb") as f:
                for chunk in resp.iter_content(1 << 16):
                    f.write(chunk)
            resp.close()
            if is_pdf(tmp):
                tmp.replace(target)
                ok = True
            else:
                tmp.unlink()
        elif resp is not None:
            resp.close()
        r["pdf_status"] = "ok" if ok else "manual"
        if ok:
            r["pdf_source"] = "openalex"
        code = resp.status_code if resp is not None else "no response"
        print(f"  [{n}/{len(todo)}] {r['paper_id']}: {'ok' if ok else f'manual ({code})'}")
        if n % 25 == 0:
            write_manifest(rows, fields)

    write_manifest(rows, fields)


# ----------------------------------------------------------------------------- report

def report(rows: list[dict]) -> None:
    def show(title: str, counter: Counter) -> None:
        print(f"\n{title}")
        for k, v in sorted(counter.items(), key=lambda kv: -kv[1]):
            print(f"  {k or '(blank)':<22} {v}")

    show("pdf_status", Counter(r["pdf_status"] for r in rows))
    show("pdf_source", Counter(r["pdf_source"] for r in rows))
    show("oa_status", Counter(r["oa_status"] for r in rows))
    show("license", Counter(r["license"] for r in rows))
    show("oa_version", Counter(r["oa_version"] for r in rows))
    n_manual = write_manual_list(rows)
    pdfs = list(RAW.glob("*.pdf")) if RAW.exists() else []
    size = sum(p.stat().st_size for p in pdfs)
    print(f"\nraw/: {len(pdfs)} files, {size / 1e6:.1f} MB")
    print(f"manual list ({n_manual} rows): {MANUAL_LIST.relative_to(HERE.parent.parent)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lookup", action="store_true", help="OpenAlex lookup only (OA columns + metadata)")
    ap.add_argument("--metadata", action="store_true", help="OpenAlex title/authors/journal only")
    ap.add_argument("--download", action="store_true", help="download only (needs a prior lookup)")
    ap.add_argument("--new", action="store_true", help="only rows never looked up (blank oa_status)")
    args = ap.parse_args()
    explicit = args.lookup or args.metadata or args.download

    rows, fields = read_manifest()
    scope = [r for r in rows if not r["oa_status"]] if args.new else None
    if scope is not None:
        print(f"--new: {len(scope)} rows never looked up ({sum(1 for r in scope if r['doi'])} with DOI)")
    if args.lookup or not explicit:
        print(f"lookup: {len(rows)} rows")
        lookup(rows, fields, scope)
    if args.metadata:
        print(f"metadata: {len(rows)} rows")
        metadata(rows, fields, scope)
    if args.download or not explicit:
        print("download")
        download(rows, fields, scope)
    report(rows)


if __name__ == "__main__":
    main()
