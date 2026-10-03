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
  ingest/parse_docling.py   # tracked: Docling parse of in-scope corpus/raw/ PDFs (conda env psed310), writes the manifest `docling` column
  ingest/docling/<paper_id>/ # gitignored: docling.json, figures/pic_K.png, document.md, structure.json (paper-derived)
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
  mentions "atomic layer" or "ALD" (auto), plus two judged by title (manual);
- `type`: the OpenAlex work type is not `article` or `letter` (auto, reason "type: <type>");
- review by title/journal (auto): the title has the whole word review, perspective, survey,
  overview or tutorial, or the journal is Chemical Reviews, Chemical Society Reviews, Applied
  Physics Reviews, Annual Review of *, Progress in Materials Science, Materials Science and
  Engineering R, Nature Reviews *, or Coordination Chemistry Reviews;
- no DOI: Cremers footnotes and notes that are not publications (auto), and books, patents,
  theses and proceedings (manual). The four Popov rows without a DOI are undecided;
- review by full text (manual): the parsed text carries a review label or calls itself a review.

### Scope

Current scope is conformality only. `in_scope` (yes/no) is computed by one rule, kept in one
place: `SCOPE_ORIGINS` / `in_scope()` in `corpus/make_report.py`:

    in_scope = (cremers or cremers_citing or extra) and status != excluded

Popov-only papers are out of scope but are not marked excluded, so the scope can be widened by
changing that constant and rerunning `make_report.py`. Rerun it after any change to the origin
columns or to `status`; it rewrites `in_scope` in the manifest. `corpus/raw/` keeps every PDF,
in scope or not. `manual_list.csv` and `ingest/parse_docling.py` cover in-scope papers only.

`pdf_status` is `ok` (file in raw/), `manual` (no OA PDF or download failed; see
`corpus/manual_list.csv`), or `missing_doi`. Rows already present in `raw/` are skipped.

`pdf_source` records where a collected file came from: `openalex` (best_oa_location URL,
downloaded by fetch_pdfs.py), `openalex_alt` (another OpenAlex location, one-off pass on
2026-09-30), `v1_copy` (copied from psed_v1 PDFs on local disk, one-off passes on
2026-09-30), or blank when not collected.

`docling` is `ok` (ingest/docling/<paper_id>/ written), `failed`, or blank (not run).
`parse_docling.py` writes it after each paper and skips rows already `ok`.

A full parse saves Docling's own output (`docling.json`, images as placeholders, plus one crop
per picture in `figures/pic_K.png`). Caption binding and the text repairs then run from those
files. **When only the binding rules change, use `parse_docling.py --rebind --all`** (seconds
per paper, no Docling); rerun Docling only when the conversion itself changes.

After each Docling run, check the newly parsed papers for review signs in their first pages
(about the first 3,000 characters of document.md): an article-type label such as Review,
Review Article, Minireview, Perspective, Feature Article, Highlight, Tutorial or Account, or
a self-description such as "this review", "in this perspective", "we review". List each hit
(paper_id, title, matched text) for the user to check; do not exclude on your own.

## Docling stage: known limits (accepted, do not fix without a new decision)
- Figure binding was checked by hand on 8 sampled papers: 74 of 75 figures exact.
- Docling-side misses: a few captions are absent from Docling output (image-only PDF, caption drawn as image) or two side-by-side figures are merged into one crop. Seen in 10.1002_admi.202000318, 10.1039_d1dt03543f, 10.1186_s11671-015-0872-9, 10.1116_6.0002804.
- Captions split across two columns keep only the first part. Captions split across pages are joined.
- A non-figure image (equation, banner whose copy differs slightly) on a figure's page can attach to that figure as an extra image.
- Tables: caption binding is not validated. Known issues: shift by one when Docling reads a table before its caption, tables Docling does not detect, captions placed inside the table's first row.
- Broken glyphs from PDF fonts (e.g. "/C14" for °, "/C0" for −, "¼" for =, private-use characters) are not fixed yet. Fixed: "/uniXXXX" and "/uXXXXX" glyph names; a digit standing for a degree sign ("300 1 C") is marked "[?]" where the PDF font shows it.
- Equations are not decoded.
- 10.1146_annurev-chembioeng-060816-101547 is a review paper; whether it belongs in the corpus is a corpus question.
- Docling occasionally reads a caption before its picture although the caption is below it; the picture then goes to the next caption (seen: 10.1002_pssa.201532305 Figure 8 went to Figure 9).
- Repeated journal logos whose copies differ slightly are not caught as decoration and can attach to a figure (seen: pssa Figures 1 and 4).
- A paper that prints the same figure number twice keeps one caption; the other figure can lose its image (seen: 10.1021_acsaelm.3c00245 Figure 10).
- Manuscripts that list all captions together and put the figures at the end cannot be bound by position (seen: 10.1116_1.5116136).
- Docling sometimes labels a body sentence as a caption, which then replaces the real one (seen: 10.1021_acs.chemmater.9b05116 Figure 10).
