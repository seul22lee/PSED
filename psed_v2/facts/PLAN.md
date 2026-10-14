# Facts layer: plan

Goal: a knowledge layer built from facts, each tied to the paper elements that state it, shown on three pilot papers
(yim20 = 10.1039_d0cp03358h, mat22 = 10.1021_acs.chemmater.2c01154, gre23 = 10.1116_6.0003182). Papers are read by
hand (no LLM API calls), every row cites element ids, and statements are written in our own words.

## Stages
1. **Elements** (`elements.py` → `elements.csv`): every abstract sentence group, body paragraph, heading, caption, figure
   panel (plots, images, maps, spectra, schematics), table cell and equation, with a stable id and locator. The ids are
   those of `schema_pilot/v2/inventory.csv`, and panels are split as seen on the crop.
2. **Facts per element** (`<paper>/build.py` → `facts.csv`, `coverage.csv`, `points/`): what each element itself states,
   one row per piece of knowledge, typed setting / observation / derived / model / definition / claim / cited. Local
   only: mentions are copied as printed ("sample 8", "H 500 nm"), with no decision on what they refer to. Values and
   units are kept as printed. Every element is covered or marked "no knowledge" with a reason (`check.py`).
3. **Anchors** (a separate, paper-wide step): list the depositions (one reactor process each), specimens, simulations,
   structure designs, methods and cited works, taken from the methods, tables and text. Link each fact's mentions to
   anchors with status stated / inferred / unresolved and the evidence for the link. Merge facts that state the same
   thing.
4. **Relations** between facts: derived_from, shown_in, same_data_as, uses_model, supports. Units are converted to the
   canonical units and quantity ids are standardized (`lists.py`).
5. **Views and demo** (below).

## Files (per paper, under `facts/<paper_id>/`)
`elements.csv`, `facts.csv`, `points/` (stages 1–2); `anchors.csv`, `fact_anchor.csv` (stage 3); `fact_links.csv`
(stage 4). These files are the source. The KG and every page are rebuilt from them and are never edited by hand.
Reports go to `facts/reports/` (untracked).

## Demo: seven views
1. Coverage: each element coloured covered / no knowledge / missed, to show nothing is lost.
2. Facts by type, with counts and filters.
3. Experiment view: per deposition, its conditions, measurements and results, coloured by link status.
4. Figure view: each panel's crop next to its facts.
5. Evidence trace: a claim → derived → observation → the crop or table cell.
6. Cross-paper comparison: one quantity across papers, compared only where qualifiers and data_kind match.
7. v1 comparison, per fact type.
The KG is these files as a graph; it serves the trace and cross-paper views.

## Order
Stages 1–2, then 3, then 4, then 5, with a short report after each. Stage 1–2 views (1, 2, 4) are in
`reports/facts.html` (`make_report.py`).
