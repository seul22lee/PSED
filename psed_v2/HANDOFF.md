# Handoff (2026-10-14)

For a new session on branch `v2`. Read `psed_v2/CLAUDE.md` first; this page adds what the last sessions built and learned.

## What matters now
- **`psed_v2/ingest/final/<paper_id>/`** (untracked, absolute path `/home/ftk3187/github/PSED/psed_v2/ingest/final/`, 59 folders):
  document.md, structure.json, figures/. Every case and pilot script reads it, so it must exist. It is produced by the ingest
  pipeline (see ingest/INGEST.md) and is not rebuilt casually.
- **`psed_v2/cases/`**: case studies on the 58 in-scope papers with a PDF. `figures.csv` (figure inventory), `points.json` (points
  read by eye, illustrative), `quantity_matrix.csv` (+ `.py`; 41 papers read by hand), `paper_case.csv` (+ `paper_case.py`; paper ×
  case, used/excluded with reasons in `case_decisions.csv`), the CSVs behind Cases 9–13, `CANDIDATES.md`, `cremers/` (the 2019 review
  typed in), `make_cases.py` and `make_matrix_html.py`.
- **`psed_v2/schema_pilot/`**: a five-table schema (paper, sample, condition, series, value) tried on three papers. First pilot: per-paper
  folders with final CSVs, `draft/`, `checklist.md`, `notes.md`, `build.py`; `convert.py`, `validate.py`, `checklist.py`,
  `make_report.py`, `SCHEMA.md`. `lists.py` holds the controlled lists (quantities, qualifier keys and values, methods, canonical units,
  enums). `v1_points_check.csv` records which v1 curves were checked against their figure and accepted; `v1_points.json` holds those points.
  **`v2/`** is the re-extraction grounded in element ids: `inventory.py`, per-paper `inventory.csv`, `coverage.csv`, tables and `build.py`,
  `validate.py`, `compare.py` (→ `compare.md`), `kg.py` (→ `kg/graph.json`, `kg/graph.graphml`), `make_reports.py`.
- **Reports** (untracked, rebuilt by scripts): `cases/reports/cases.html`, `cases/reports/matrix.html`, `schema_pilot/reports/pilot.html`,
  `schema_pilot/reports/kg.html`.

## Standing rules
- No LLM API calls; read papers yourself (subagents are fine).
- Own words only. Tracked files hold no copied text; evidence is an element id (v2 ids: abs.gN, sN.pM, sN.xK, figN.cap, figN<panel>,
  tabN.rIcJ, eqN) plus a short locator.
- No changes to `corpus/` or `ingest/` unless asked. Never edit `PSED_v2_Plan.md`. Touch nothing outside `psed_v2/`.
- `corpus/raw/`, `ingest/final/` (and marker/, docling/) and every `reports/` folder stay untracked.
- Simple is best; one goal per commit; report briefly; commit lines end with the Co-Authored-By line given in the session.

## v1
v1 lives on branch `figure-provenance-repair` under `psed_v1/papers/<paper_id>/` (read with `git show figure-provenance-repair:<path>`;
do not check it out over v2). Useful for its digitized points (`extracted/figure_data.json`, mapped by `canonical/curves.json`): they
were checked against the figures for two papers (75 of 121 curves accepted, `schema_pilot/v1_points_check.csv`). Its resolved results
are not reliable: whole tables missing, axes misread, sentinel numbers stored as values.

## What the schema pilot taught
1. Sample or experiment as the one container loses knowledge: values about groups, structures, model runs and literature have no single
   sample, and v1 dropped such results wholesale (all 142 Table 1 cells of one paper).
2. Counts mixed kinds: groups, pieces, references and model runs inflate "samples"; count by sample kind.
3. Linking a figure to its specimen needs the whole paper (methods define runs, captions name them, tables carry their results).
4. Citing element ids with a coverage table makes gaps visible (it exposed an inventory bug); colour-bar reads do not reproduce.

## How to run
```
python3 psed_v2/cases/quantity_matrix.py && python3 psed_v2/cases/paper_case.py   # matrix, then the paper × case table
python3 psed_v2/cases/make_cases.py && python3 psed_v2/cases/make_matrix_html.py  # cases.html (needs corpus/raw review PDF and pdftoppm), matrix.html
python3 psed_v2/schema_pilot/convert.py && python3 psed_v2/schema_pilot/validate.py && python3 psed_v2/schema_pilot/checklist.py && python3 psed_v2/schema_pilot/make_report.py
python3 psed_v2/schema_pilot/v2/inventory.py && python3 psed_v2/schema_pilot/v2/validate.py   # must pass; prints coverage shares
python3 psed_v2/schema_pilot/v2/compare.py && python3 psed_v2/schema_pilot/v2/kg.py && python3 psed_v2/schema_pilot/v2/make_reports.py
python3 psed_v2/ingest/regression.py                                              # ingest output against the answer set
```
`v2/inventory.py --text DIR` writes the element texts (for reading only) to a directory outside the repo.
