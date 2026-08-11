# Backward-compatibility archaeology

Every place that depends on an identifier's string format.

## Sites that PARSE an identifier

| site | parse | depends on |
|---|---|---|
| `pipeline/review/build_core_kg.py:112` | `eid.split("__case")[0]` | the `__case%02d` case suffix |
| `pipeline/review/build_core_kg.py:123-129` | `source_series_id.split("\|")`, then `parts[0], parts[1], parts[3], parts[4]` | **`entity_key`'s 6-field pipe layout**, positionally |
| `pipeline/resolve/to_kb.py:1251` | `re.search(r"-C(\d+)$", exp_id)` | the provisional `-C%02d` suffix, during the rename |
| `pipeline/resolve/to_kb.py:1508-1515` | rebuilds a slug from `figure_slug` or `printed_figure_number` + panel | the `FigNa` slug shape |
| `pipeline/canonical/build_canonical.py:37` | `_PTR = /figures/(\d+)/panels/(\d+)/series/(\d+)` on `json_pointer` | the **extraction** pointer format, not a resolved id |
| `pipeline/canonical/build_core_kg.py:98-103` `_lab` | normalises `<single>`/`None`/`primary` to `""` | the series-label placeholders |
| `tests/canonical_layer/test_granularity_and_axes.py` "ids use the printed figure number" | asserts the id is anchored on the printed number, not the docling index | the `Fig<printed>` prefix |

Explicitly **not** parsed anywhere: `physical_case_id`, `shares_physical_case_with`,
`measurement_event_id`, `result_series_id`, `curve_id`. `to_kb.py:1133-1135` carries a
comment warning against parsing the paper out of an id, because
`exp_id.split("-")[0]` previously broke on `10.1007_s11671-010-9676-0`.

## Classification of every identifier

| identifier | internal implementation | persisted stable | externally surfaced | cross-stage foreign key |
|---|---|---|---|---|
| provisional `exp_id` (L1737) | **yes** | no | no | no |
| provisional `eid` (L904) | **yes** (kept as `provisional_entity_id`) | no | no | no |
| `entity_key` | **yes** | written to `results.json` as `source_series_id` | no | **yes** — the core KG canonical join |
| `experiment_id` / final `entity_id` | no | **yes** | **yes** — KG node labels, dashboards, reports | **yes** — canonical `linked_experiment_ids`, both KGs, twin |
| case `exp_id` | no | **yes** | **yes** — the `Experiment` node label users see | **yes** |
| `physical_case_id` | **yes** | written to `results.json` | no | weak — provenance attribute only |
| `shares_physical_case_with` | **yes** | written | no | orphan-checked by `validate_granularity.py` |
| `measurement_event_id` | **yes** | written | no | provenance attribute only |
| `result_series_id` | **yes** (aliased to `entity_id`) | written | no | **yes** — core KG `ResultSeries` id |
| `experimental_series_id` / `series_id` | partly | written | KG `es::` nodes | **yes** |
| `curve_id` | no | **yes, explicitly** | **yes** — canonical, KG `Curve`, core KG provenance | **yes** |
| `fit_of_entity` | no | written | no | **yes** — stores a resolved `entity_id` |
| KG node ids (`e::`, `ps::`, `ent::`, `exp::`, `rs::`) | **yes** | rebuilt each run | viewers | within one build only |

## Reports, dashboards and URLs

`reports/*.html` are generated wholesale by `build_dashboard.py`, `build_analysis.py`,
`corpus_dashboard.py`, `build_recipes.py`, `corpus_status.py`, `kg_viewer.html` and
`build_core_kg.py`'s embedded viewer. They display `exp_id` / `entity_id` / `curve_id` as
text and as in-page anchors. No file path or external URL is derived from an identifier —
paper directories are named by DOI slug, which no identity work touches.

## Filename generation

`paths.py` builds paths from the paper id only (`papers/<pid>/{extracted,resolved,canonical}`).
No file is named after an entity, experiment, case, series or curve id.
