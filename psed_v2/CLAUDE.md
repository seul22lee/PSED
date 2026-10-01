# psed_v2

Second-generation PSED corpus, built stage by stage. Stage 0 (`corpus/`) turns the
reference lists of two reviews, Popov 2025 (Table I) and Cremers 2019, plus the papers that
cite Cremers 2019 on conformality topics, into one manifest of open-access PDFs.
`psed_v1/` is frozen; nothing here reads from or writes to it.

## Layout

```
psed_v2/
  CLAUDE.md
  PSED_v2_Plan.md           # tracked: the v2 plan; user-edited only (see Rules)
  corpus/manifest.csv       # tracked: one row per paper, deduped by DOI (Popov 2025 + Cremers 2019 + papers citing Cremers)
  corpus/fetch_pdfs.py      # tracked: OpenAlex lookup + PDF download, writes back to manifest.csv
  corpus/make_report.py     # tracked: derives corpus/report.csv from manifest.csv
  corpus/report.csv         # tracked: doi, title, authors, journal, year, collected, pdf_source, refs, source
  corpus/manual_list.csv    # tracked: rows that need a hand-fetched PDF (derived from manifest)
  corpus/raw/<paper_id>.pdf # gitignored: paper_id = DOI with "/" -> "_", lowercased
  corpus/parse_docling.py   # tracked: Docling parse of raw/ PDFs (conda env psed310), writes the `docling` column
  corpus/docling/<paper_id>/ # gitignored: document.md, structure.json, figures/ (paper-derived)
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

`source` is a semicolon list of `popov`, `cremers`, `cremers_citing`, `extra`; a paper can have
several. Each source has its evidence column(s):
- `popov`: `popov_ref`, the reference number in Popov 2025 Table I.
- `cremers`: `cremers_ref`, the reference number in Cremers 2019, and `cremers_context`, where
  Cremers cites it.
- `cremers_citing`: `cites_cremers_keywords`, the conformality keywords matched in the title or
  abstract of a paper that cites Cremers 2019 in OpenAlex (pulled 2026-10-01; preprints that
  duplicate a published article were dropped).
- `extra`: `extra_reason`, why the paper was added by hand.
`processes` merges both reviews' process lists with ` | `.

`pdf_status` is `ok` (file in raw/), `manual` (no OA PDF or download failed; see
`corpus/manual_list.csv`), or `missing_doi`. Rows already present in `raw/` are skipped.

`pdf_source` records where a collected file came from: `openalex` (best_oa_location URL,
downloaded by fetch_pdfs.py), `openalex_alt` (another OpenAlex location, one-off pass on
2026-09-30), `v1_copy` (copied from psed_v1 PDFs on local disk, one-off passes on
2026-09-30), or blank when not collected.

`docling` is `ok` (corpus/docling/<paper_id>/ written), `failed`, or blank (not run).
`parse_docling.py` writes it after each paper and skips rows already `ok`.

## Docling stage: known limits (accepted, do not fix without a new decision)
- Figure binding was checked by hand on 8 sampled papers: 74 of 75 figures exact.
- Docling-side misses: a few captions are absent from Docling output (image-only PDF, caption drawn as image) or two side-by-side figures are merged into one crop. Seen in 10.1002_admi.202000318, 10.1039_d1dt03543f, 10.1186_s11671-015-0872-9, 10.1116_6.0002804.
- Captions split across two columns keep only the first part. Captions split across pages are joined.
- A non-figure image (equation, banner whose copy differs slightly) on a figure's page can attach to that figure as an extra image.
- Tables: caption binding is not validated. Known issues: shift by one when Docling reads a table before its caption, tables Docling does not detect, captions placed inside the table's first row.
- Broken glyphs from PDF fonts (e.g. "/C14" for °, "/C0" for −, "¼" for =) are not fixed yet.
- Equations are not decoded.
- 10.1146_annurev-chembioeng-060816-101547 is a review paper; whether it belongs in the corpus is a corpus question.
- Docling occasionally reads a caption before its picture although the caption is below it; the picture then goes to the next caption (seen: 10.1002_pssa.201532305 Figure 8 went to Figure 9).
- Repeated journal logos whose copies differ slightly are not caught as decoration and can attach to a figure (seen: pssa Figures 1 and 4).
- A paper that prints the same figure number twice keeps one caption; the other figure can lose its image (seen: 10.1021_acsaelm.3c00245 Figure 10).
