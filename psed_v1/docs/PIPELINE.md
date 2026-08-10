# PSED pipeline — the one live workflow

**This is the authoritative execution document.** Where an older README disagrees
with this file, this file is correct; the stale ones are marked in §6.

---

## 1. Live data flow

```
03_corpus/pdfs/ , data/pdfs/
  │
  ├─ 03_corpus/scripts/03_docling.py        → extracted/{doi}/document.md, structure.json, figures/*.png
  ├─ 03_corpus/scripts/04_extract.py        → extracted/{doi}/scout.json, card.json
  ├─ 03_corpus/scripts/09_geometry.py       → extracted/{doi}/geometry.json
  ├─ 03_corpus/scripts/10_pressure.py       → extracted/{doi}/pressure.json
  ├─ 03_corpus/scripts/05_figure_extract.py → extracted/{doi}/figure_data.json, records.json   [vision LLM]
  │
  ├─ 01_ontology/build_ontology.py          → ald_ontology.{json,yaml}   (+ ontology HTML)
  │
  ├─ 02_extraction/canonical/recover_axis_semantics.py   → extracted/{doi}/recovery/axis_semantics_v1.json
  │                                                        reports/canonical/reextraction_candidates.json
  ├─ 02_extraction/canonical/reextract_figures.py        → extracted/{doi}/recovery/figure_semantics_v1.json  [vision LLM, selective]
  │
  ├─ 03_corpus/scripts/06_to_kb.py          → output/{doi}/resolved/entities.json      (typed source entities)
  │                                           output/{doi}/resolved/experiments.json   (experimental cases ONLY)
  │                                           output/{doi}/resolved/series.json
  │                                           output/{doi}/resolved/assertions.json
  │                                           output/{doi}/resolved/counts.json
  ├─ 02_extraction/canonical/build_canonical.py → output/{doi}/canonical/curves.json
  ├─ 02_extraction/canonical/audit.py       → reports/canonical/*.json|csv
  ├─ 02_extraction/canonical/validate.py    → reports/canonical/validation.json
  ├─ 02_extraction/canonical/kb_migration_diff.py → reports/canonical/kb_migration_summary.json
  │
  ├─ 02_extraction/build_kg.py              → output/knowledge_graph_onto.json, kg_viewer.html
  ├─ 02_extraction/build_analysis.py        → analysis_dashboard.html
  ├─ 02_extraction/build_dashboard.py       → experiment_dashboard.html
  └─ 04_twin_mpc/*                          consumes resolved/experiments.json via kb_bridge.py
```

**Dependency order matters.** `06_to_kb.py` reads the recovery files (for verbatim
axis labels); `build_canonical.py` reads the resolved experiments (for context).
Run them in the order below.

## 2. Full run

```bash
cd psed_v1

# 0. ontology (fails loudly on any dangling comparability reference)
python3 01_ontology/build_ontology.py
python3 01_ontology/validate.py

# 1. synthetic tests — must be green before touching the corpus
cd 02_extraction && python3 -m unittest discover -s canonical/tests -t . -v && cd ..

# 2. recover axis semantics from local text; produce the re-extraction work list
python3 02_extraction/canonical/recover_axis_semantics.py --all

# 3. selective figure re-extraction (axis METADATA only; needs psed310 + API key)
/home/ftk3187/miniconda3/envs/psed310/bin/python \
    02_extraction/canonical/reextract_figures.py --priority high

# 4. live extraction → KB (units, coordinate units, axis-role granularity, series)
/home/ftk3187/miniconda3/envs/psed310/bin/python \
    03_corpus/scripts/06_to_kb.py --all --resolve-only

# 5. canonical comparison layer
python3 02_extraction/canonical/build_canonical.py --all

# 6. audits + validation gate
python3 02_extraction/canonical/audit.py --all
python3 02_extraction/canonical/validate.py --all
python3 02_extraction/canonical/kb_migration_diff.py

# 7. knowledge graph + dashboards
python3 02_extraction/build_kg.py
python3 02_extraction/build_analysis.py
python3 02_extraction/build_dashboard.py
```

### Interpreters

| Step | Interpreter | Why |
|---|---|---|
| everything except 3 and 4 | system `python3` (3.8) | no third-party deps beyond PyYAML |
| 3 (`reextract_figures.py`), 4 (`06_to_kb.py`) | `psed310` (3.11) | `google-genai`, Pillow |

All canonical-layer code is Python 3.8 compatible and runs under both.

## 3. Entity model (supersedes the granularity rules below)

`06_to_kb.py` now emits a typed entity layer: a drawn curve is a `PlotSeries`, its
points are `Observation`s, and an `ExperimentalCase` is minted only where the paper
supports the setting. Simulations, model sweeps, fits, imported literature and
derived representations are not current-paper experiments. See
[ENTITY_MODEL.md](ENTITY_MODEL.md) and
`reports/entity_model/count_reconciliation.md`.

## 3b. Experiment granularity (historical — superseded by the entity model)

Decided from the **ontology axis role**, never from the point count.

| x-axis role | representation | KG |
|---|---|---|
| coordinate (position, depth, dimensionless distance) | one **profile** Experiment holding the ordered points | `Experiment --varies--> QuantityKind` |
| condition (temperature, cycles, pulse time, exposure, pressure, aspect ratio, feature size) | one Experiment **per point** + an **ExperimentSeries** | `Experiment --in_series--> ExperimentSeries --series_varies--> QuantityKind` |
| output vs output | **correlation** (neither axis is an input) | no `varies` edge |
| unresolved | `unresolved`, reported, not guessed | — |

Split ids are deterministic: `{pid}-{fig}{panel}-S{n}` for the series,
`…-S{n}-P{ppp}` for each point experiment.

## 4. Units in the KB

Resolved experiments carry both representations:

```json
"measurand": {"quantity": "growth_per_cycle", "unit": "nm/cycle",
              "raw_unit": "Å/cyc", "unit_conversion": {...}},
"coordinate_unit": "um", "coordinate_unit_normalized": "µm",
"coordinate_unit_status": "resolved",
"points": [[...raw...]], "points_canonical": [[...converted...]]
```

`points` is the untouched digitized data. `points_canonical` is the converted
copy. A coordinate is never stored without a unit unless
`coordinate_unit_status == "unresolved"`, which carries a reason.

## 5. Onboarding a new paper

1. Drop the PDF in `03_corpus/pdfs/`, run `03_docling.py`, `04_extract.py`,
   `09_geometry.py`, `10_pressure.py`, `05_figure_extract.py` for that paper.
2. Run steps 2–7 above (all accept `--paper <doi>` as well as `--all`).
3. Read `reports/canonical/manual_review_queue.json` for that paper.

Before scaling to ~80 papers, see §22 of the implementation report and
[DATA_RECOVERY.md](DATA_RECOVERY.md) §6.

## 6. Deprecated / stale documents and code

| Path | Status |
|---|---|
| `02_extraction/README.md` | **stale** — describes the old `0706_pipeline` / `0604_kg` layout. Use this file. |
| `02_extraction/config.py`, `pipeline.py`, `run_all.py` | **dead** — reference `0604_kg/`, which does not exist in this repo. Not part of any live command. |
| `02_extraction/stages/s06_*.py, s07_*.py, s08_resolve.py, s09_kg.py` | **dead** — `stages/lib.py:KG0604` points at a missing directory, so `papers()` raises. The *correct* granularity logic that lived unused in `s08_resolve.py` now runs in the live path via `canonical/live.py`. |
| `02_extraction/stages/lib.py` | **partly live** — its ontology helpers (`canon_*`, `family`, `species_prop`) are imported by `06_to_kb.py`. Its paper-registry functions are dead. |
| `03_corpus/extracted/cremers2019/` | **stale** — docling leftover, not in the manifest, no `figure_data.json`. |
| `docs/COMPARABILITY_STRATEGY.md` | **superseded** by `CANONICALIZATION.md` for P2/P3. |
| `old/` | historical; not referenced by any live command. |

Nothing in the "dead" rows was deleted in this change: they are marked, and the
live workflow above does not touch them.
