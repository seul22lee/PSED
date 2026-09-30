# psed_v2

Second-generation PSED corpus, built stage by stage. Stage 0 (`corpus/`) turns the
reference lists of two reviews, Popov 2025 (Table I) and Cremers 2019, into one manifest
of open-access PDFs.
`psed_v1/` is frozen; nothing here reads from or writes to it.

## Layout

```
psed_v2/
  CLAUDE.md
  corpus/manifest.csv       # tracked: one row per paper, deduped by DOI (Popov 2025 + Cremers 2019)
  corpus/fetch_pdfs.py      # tracked: OpenAlex lookup + PDF download, writes back to manifest.csv
  corpus/make_report.py     # tracked: derives corpus/report.csv from manifest.csv
  corpus/report.csv         # tracked: doi, title, authors, journal, year, collected, pdf_source, refs, source
  corpus/manual_list.csv    # tracked: rows that need a hand-fetched PDF (derived from manifest)
  corpus/raw/<paper_id>.pdf # gitignored: paper_id = DOI with "/" -> "_", lowercased
```

## Rules

- **`corpus/raw/` never goes into git.** It holds copyrighted publisher PDFs. It is listed
  in the repo `.gitignore` (`psed_v2/corpus/raw/`, on top of the global `*.pdf` rule). Do not
  add an exception, do not `git add -f`, do not copy its contents anywhere tracked.
- `manifest.csv` is the single source of truth for corpus membership. Add or drop papers
  there, never by adding or deleting files in `raw/`.
- `paper_id` is derived from the DOI and is the file stem in `raw/`; keep them in sync.

## Stage 0 workflow

```
python3 psed_v2/corpus/fetch_pdfs.py --lookup     # fill oa_status / license / oa_version / pdf_url + title / authors / journal
python3 psed_v2/corpus/fetch_pdfs.py --metadata   # refresh title / authors / journal only
python3 psed_v2/corpus/fetch_pdfs.py --download   # ~1 req/s, retries on 429/5xx, keeps only %PDF files
python3 psed_v2/corpus/fetch_pdfs.py --new        # lookup + download only for rows never looked up
python3 psed_v2/corpus/make_report.py             # regenerate corpus/report.csv
```

`popov_ref` / `cremers_ref` are the reference numbers in each review (blank if not cited there).
`source` is `popov`, `cremers`, `popov;cremers`, or `extra` (added by hand). `processes` merges
both reviews' process lists with ` | `; `cremers_context` says where Cremers cites the paper.

`pdf_status` is `ok` (file in raw/), `manual` (no OA PDF or download failed; see
`corpus/manual_list.csv`), or `missing_doi`. Rows already present in `raw/` are skipped.

`pdf_source` records where a collected file came from: `openalex` (best_oa_location URL,
downloaded by fetch_pdfs.py), `openalex_alt` (another OpenAlex location, one-off pass on
2026-09-30), `v1_copy` (copied from psed_v1 PDFs on local disk, one-off passes on
2026-09-30), or blank when not collected.
