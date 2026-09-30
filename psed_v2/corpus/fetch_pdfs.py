#!/usr/bin/env python3
"""Stage 0 of psed_v2: resolve open-access PDFs for the corpus manifest and download them.

Usage
    python3 fetch_pdfs.py --lookup      # OpenAlex lookup only; fills oa_* / pdf_url columns
    python3 fetch_pdfs.py --download    # download rows that have a pdf_url and no file in raw/
    python3 fetch_pdfs.py               # both, in that order

Manifest columns written by this script
    oa_status   OpenAlex open_access.oa_status (gold/green/hybrid/bronze/diamond/closed),
                or not_found when the DOI is unknown to OpenAlex
    license     best_oa_location.license (may be empty even when a PDF is available)
    oa_version  best_oa_location.version (publishedVersion / acceptedVersion / submittedVersion)
    pdf_url     best_oa_location.pdf_url
    pdf_status  ok          raw/<paper_id>.pdf exists and starts with %PDF
                manual      no pdf_url, or the download did not yield a PDF; fetch by hand
                missing_doi the manifest row has no DOI
                (blank)     pdf_url known, download not attempted yet

raw/<paper_id>.pdf is gitignored: paper_id is the DOI with "/" -> "_", lowercased.
Set OPENALEX_MAILTO to join the OpenAlex polite pool (optional).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
MANUAL_LIST = HERE / "manual_list.csv"
RAW = HERE.parent / "raw"

OPENALEX = "https://api.openalex.org/works"
BATCH = 50
DOWNLOAD_INTERVAL = 1.0  # seconds between publisher requests
RETRIES = 4
TIMEOUT = 60
UA = "PSED-research (mailto:seullee2029@u.northwestern.edu)"

NEW_COLS = ["oa_status", "license", "oa_version", "pdf_url", "pdf_status"]


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
    keep = ["ref_no", "paper_id", "doi", "year", "citation", "oa_status", "pdf_url", "pdf_status"]
    manual = [r for r in rows if r["pdf_status"] in ("manual", "missing_doi")]
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


# ----------------------------------------------------------------------------- lookup

def normalise_doi(doi: str) -> str:
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def lookup(rows: list[dict], fields: list[str]) -> None:
    session = requests.Session()
    session.headers["User-Agent"] = UA
    params_base = {"per-page": BATCH, "select": "doi,open_access,best_oa_location"}
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params_base["mailto"] = mailto

    with_doi = [r for r in rows if r["doi"]]
    for r in rows:
        if not r["doi"]:
            r["pdf_status"] = "missing_doi"

    found: dict[str, dict] = {}
    for i in range(0, len(with_doi), BATCH):
        chunk = with_doi[i:i + BATCH]
        params = dict(params_base, filter="doi:" + "|".join(r["doi"] for r in chunk))
        resp = get_with_retry(session, OPENALEX, params=params)
        if resp is None or resp.status_code != 200:
            code = resp.status_code if resp is not None else "no response"
            print(f"  batch {i // BATCH + 1}: OpenAlex failed ({code}); leaving rows untouched", file=sys.stderr)
            continue
        for work in resp.json().get("results", []):
            if work.get("doi"):
                found[normalise_doi(work["doi"])] = work
        print(f"  batch {i // BATCH + 1}/{(len(with_doi) + BATCH - 1) // BATCH}: "
              f"{len(chunk)} queried, {len(resp.json().get('results', []))} returned")
        time.sleep(0.2)

    for r in with_doi:
        work = found.get(normalise_doi(r["doi"]))
        if work is None:
            r["oa_status"] = "not_found"
            r["license"] = r["oa_version"] = r["pdf_url"] = ""
        else:
            oa = work.get("open_access") or {}
            best = work.get("best_oa_location") or {}
            r["oa_status"] = oa.get("oa_status") or ""
            r["license"] = best.get("license") or ""
            r["oa_version"] = best.get("version") or ""
            r["pdf_url"] = best.get("pdf_url") or ""
        # status: keep an existing ok only if the file is really there
        if is_pdf(pdf_path(r)):
            r["pdf_status"] = "ok"
        elif not r["pdf_url"]:
            r["pdf_status"] = "manual"
        else:
            r["pdf_status"] = ""  # pending download

    write_manifest(rows, fields)


# ----------------------------------------------------------------------------- download

def download(rows: list[dict], fields: list[str]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    session.headers["Accept"] = "application/pdf,*/*;q=0.8"

    todo = [r for r in rows if r["doi"] and r["pdf_url"] and r["pdf_status"] != "ok"]
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
        code = resp.status_code if resp is not None else "no response"
        print(f"  [{n}/{len(todo)}] {r['paper_id']}: {'ok' if ok else f'manual ({code})'}")
        if n % 25 == 0:
            write_manifest(rows, fields)

    write_manifest(rows, fields)


# ----------------------------------------------------------------------------- report

def report(rows: list[dict]) -> None:
    from collections import Counter

    def show(title: str, counter: Counter) -> None:
        print(f"\n{title}")
        for k, v in sorted(counter.items(), key=lambda kv: -kv[1]):
            print(f"  {k or '(blank)':<22} {v}")

    show("pdf_status", Counter(r["pdf_status"] for r in rows))
    show("oa_status", Counter(r["oa_status"] for r in rows))
    show("license", Counter(r["license"] for r in rows))
    show("oa_version", Counter(r["oa_version"] for r in rows))
    n_manual = write_manual_list(rows)
    size = sum(p.stat().st_size for p in RAW.glob("*.pdf")) if RAW.exists() else 0
    n_pdf = len(list(RAW.glob("*.pdf"))) if RAW.exists() else 0
    print(f"\nraw/: {n_pdf} files, {size / 1e6:.1f} MB")
    print(f"manual list ({n_manual} rows): {MANUAL_LIST.relative_to(HERE.parent.parent)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lookup", action="store_true", help="OpenAlex lookup only")
    ap.add_argument("--download", action="store_true", help="download only (needs a prior lookup)")
    args = ap.parse_args()
    do_lookup = args.lookup or not args.download
    do_download = args.download or not args.lookup

    rows, fields = read_manifest()
    if do_lookup:
        print(f"lookup: {len(rows)} rows")
        lookup(rows, fields)
    if do_download:
        print("download")
        download(rows, fields)
    report(rows)


if __name__ == "__main__":
    main()
