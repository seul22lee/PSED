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
  corpus/make_report.py     # tracked: sets in_scope in manifest.csv (the scope rule lives here) and derives report.csv
  corpus/report.csv         # tracked: reader-facing view: metadata, in_scope, collected, origins and evidence, decisions
  corpus/manual_list.csv    # tracked: in-scope rows that need a hand-fetched PDF (derived from manifest)
  corpus/raw/<paper_id>.pdf # gitignored: paper_id = DOI with "/" -> "_", lowercased
  ingest/parse_docling.py   # tracked: Docling for equations only (--formulas: CodeFormula on R1/R2 crops -> equations.json; conda env psed310) and the OpenAlex abstract fetch
  ingest/docling/<paper_id>/ # gitignored: equations.json (paper-derived)
  ingest/parse_marker.py    # tracked: Marker 2.0 parse (force_ocr) of the same PDFs (conda env psed_marker), writes the manifest `marker` column; --bands repairs captions/abstracts drawn as images
  ingest/marker/<paper_id>/  # gitignored: document.md + images, blocks.json, bands.json, structure.json, table crops (paper-derived)
  ingest/structure_marker.py # tracked: structure.json from Marker's blocks (captions, tables with rule check, equations, abstract)
  ingest/merge.py           # tracked: one output per paper from both tools -> ingest/final/<paper_id>/ (runs line_numbers.py, body_check.py, body_repair.py)
  ingest/line_numbers.py    # tracked: margin line numbers of a line-numbered manuscript removed from document.md
  ingest/body_check.py      # tracked: body-number check, decoded text layer vs document.md per paragraph -> body_flags
  ingest/body_repair.py     # tracked: countermeasures on document.md (a number replaced from the text layer, a dropped line restored) -> body_repairs
  ingest/glyph_codes.json   # tracked: per-font decoding tables for the PDF text layer, with evidence
  ingest/final/<paper_id>/   # gitignored: document.md, structure.json (Marker body/abstract/figures/tables + paired equations), figures/
  ingest/reports/           # gitignored: review HTML reports (e.g. the Docling-vs-Marker disagreement report)
  ingest/INGEST.md, ERRORS.md # tracked: what ingest extracts and how; the remaining errors per item
```

## Environments

- `psed310`: Docling (and pdfplumber). `psed_marker`: marker-pdf 2.0.0 only. Kept separate
  because Docling pins transformers <5 and huggingface_hub <1 while Marker needs newer, and the
  pillow pins conflict. Use `~/miniconda3/bin/conda` (the `conda` on PATH is broken).
- Marker runs with the llama.cpp backend: `SURYA_INFERENCE_BACKEND=llamacpp`,
  `LLAMA_CPP_BINARY=~/opt/llama.cpp/llama-b11574/llama-server`, and both llama.cpp folders
  (`~/opt/llama.cpp/llama-b11574`, `~/opt/llama.cpp/cudart-llama-b11574-bin-ubuntu-cuda-12.8-x64`)
  on `LD_LIBRARY_PATH`.
- Marker output is not deterministic across runs (llama.cpp backend, no fixed seed or temperature): run once per
  paper and keep the result; the 44 outputs are not reproducible bit for bit.

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
python3 psed_v2/corpus/make_report.py             # recompute in_scope, regenerate corpus/report.csv
```

Origin columns, each `O` or empty; a paper can have several. Each has its evidence column(s):
- `popov`: `popov_ref`, the reference number in Popov 2025 Table I.
- `cremers`: `cremers_ref`, the reference number in Cremers 2019, and `cremers_context`, where
  Cremers cites it.
- `cremers_citing`: `cites_cremers_keywords`, the conformality keywords matched in the title or
  abstract of a paper that cites Cremers 2019 in OpenAlex (pulled 2026-10-01; preprints that
  duplicate a published article were dropped).
- added by hand: no flag column; `extra_reason` says why.
`processes` merges both reviews' process lists with ` | `.

`status` is `excluded`, `included`, or blank (no decision recorded), with a one-line `reason`,
`decision` (`auto` = rule applied by script, `manual` = judged by the user) and `decided_on` (date).
Excluded rows stay in the manifest and keep their PDFs. Exclusion rules applied so far:
- not ALD: found only through the Cremers-citing search, and neither title nor abstract
  mentions "atomic layer" or "ALD" (auto), plus two judged by title and two judged by the
  parsed full text (manual);
- `type`: the OpenAlex work type is not `article` or `letter` (auto, reason "type: <type>");
- review by title/journal (auto): the title has the whole word review, perspective, survey,
  overview or tutorial, or the journal is Chemical Reviews, Chemical Society Reviews, Applied
  Physics Reviews, Annual Review of *, Progress in Materials Science, Materials Science and
  Engineering R, Nature Reviews *, or Coordination Chemistry Reviews;
- no DOI: Cremers footnotes and notes that are not publications (auto), and books, patents,
  theses and proceedings (manual). The four Popov rows without a DOI are undecided;
- review by full text (manual): the parsed text carries a review label or calls itself a review,
  or its figures and captions show it is an overview of other work.

### Scope

Current scope is conformality only. `in_scope` (yes/no) is computed by one rule, kept in one
place: `SCOPE_ORIGINS` / `in_scope()` in `corpus/make_report.py`:

    in_scope = (cremers or cremers_citing or extra) and status != excluded

Popov-only papers are out of scope but are not marked excluded, so the scope can be widened by
changing that constant and rerunning `make_report.py`. Rerun it after any change to the origin
columns or to `status`; it rewrites `in_scope` in the manifest. `corpus/raw/` keeps every PDF,
in scope or not. `manual_list.csv` and `ingest/parse_marker.py` cover in-scope papers only.

`pdf_status` is `ok` (file in raw/), `manual` (no OA PDF or download failed; see
`corpus/manual_list.csv`), or `missing_doi`. Rows already present in `raw/` are skipped.

`pdf_source` records where a collected file came from: `openalex` (best_oa_location URL,
downloaded by fetch_pdfs.py), `openalex_alt` (another OpenAlex location, one-off pass on
2026-09-30), `v1_copy` (copied from psed_v1 PDFs on local disk, one-off passes on
2026-09-30), or blank when not collected.

`marker` is `ok` (ingest/marker/<paper_id>/ written), `failed`, or blank (not run). `parse_marker.py`
writes it after each paper and skips rows already `ok` (`--redo` to overwrite). The other ingest steps
(`structure_marker.py`, `parse_docling.py --formulas`, `merge.py`) write no manifest column.

After each Marker run, check the newly parsed papers for review signs in the first pages of their
document.md (about the first 3,000 characters): an article-type label such as Review, Review Article,
Minireview, Perspective, Feature Article, Highlight, Tutorial or Account, or a self-description such as
"this review", "in this perspective", "we review". List each hit (paper_id, title, matched text) for the
user to check; do not exclude on your own.

Ingest (Marker, Docling equations, what is extracted, change log): see ingest/INGEST.md; the remaining errors: ingest/ERRORS.md.
