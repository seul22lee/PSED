# psed_v2

Second-generation PSED corpus, built stage by stage. Stage 0 (`corpus/`) turns the
reference lists of two reviews, Popov 2025 (Table I) and Cremers 2019, into one manifest
of open-access PDFs.
`psed_v1/` is frozen; nothing here reads from or writes to it.

## Layout

```
psed_v2/
  CLAUDE.md
  PSED_v2_Plan.md           # tracked: the v2 plan; user-edited only (see Rules)
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
- **`PSED_v2_Plan.md` is edited only by the user, outside Claude Code.** Never modify it.
  Read it for context; commit and push it only when the user asks.

### Working rules for Claude Code

These rules go into `CLAUDE.md` so that every session starts from them.

- Simplest solution first.
- PDFs, full text, and figure crops live outside git.
- One unit of work has one goal and one commit. The done criterion is written in one line before starting.
- Tests are the gold score plus about 10 invariants taken from v1 failure cases. No tests that pin counts.
- Before any LLM call, state the expected number of calls. Results are cached.
- The corpus is re-run once, at the end of a phase. Generated outputs are committed separately from code.
- Earlier commits, old reports, and v1 diagnostics are not re-audited.
- An investigation that reaches no conclusion in 20 minutes ends with two options and a question.
- A report back is 15 lines or fewer: what changed, how the score moved, what is left.
- Each unit starts a new session; `CLAUDE.md` supplies the context.

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
