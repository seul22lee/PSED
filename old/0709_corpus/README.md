# 0709_corpus — paper-collection pipeline

Bootstrap the ALD corpus by mining the bibliographies of conformality/ALD **review
papers** into a DOI list, then fetching open-access PDFs, then handing new PDFs to the
extraction pipeline. Addresses the data-breadth weakness (the KB was ~1 chemistry).

Seed reviews (Crossref DOIs):
- `cremers2019` — 10.1063/1.5060967  (Appl. Phys. Rev. 6, 021302)  — 265 refs
- `popov2025`   — 10.1116/6.0004320  (JVST A 43, 030801)          — 745 refs

## Layout
- `scripts/01_refs_to_dois.py` — review DOI → reference DOIs (Crossref).
- `scripts/02_fetch_pdfs.py`   — DOI → OA PDF (Unpaywall).
- `refsets/` — per-review + merged DOI CSVs, raw Crossref JSON snapshots.
- `pdfs/`    — downloaded PDFs (filename = DOI with /,: → _).
- `config/`  — local config (email etc.); email also read from env.

## Run
    export UNPAYWALL_EMAIL=you@example.com     # Crossref polite pool + Unpaywall
    python3 scripts/01_refs_to_dois.py
    python3 scripts/02_fetch_pdfs.py           # after step 1

Steps 3–4 (Zotero / Better BibTeX) deferred. Step 5 (`make ingest`) after 1–2 verified.
