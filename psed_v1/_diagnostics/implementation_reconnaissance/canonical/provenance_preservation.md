# Provenance preservation constraints

Five provenance kinds are distinguished today. For each: resolver class, canonical marker,
KG representation, attribution, tests, and dependence on Experiment ids.

| kind | resolver class | canonical marker | KG | source attribution | tests | depends on Experiment ids? |
|---|---|---|---|---|---|---|
| measured experimental | `ContinuousTrace` 118, `ExperimentalProfile` 71, `MultiOutputMeasurement` 377, `ExperimentSeries` 327 | `source.data_source = "measured"` | typed entity node + `Experiment` node + `depicted_by` | current paper | `test_stage0_regression`, `test_granularity_and_axes` | yes — the `Experiment` node label is `exp_id` |
| simulated / model | `SimulationRun` 112, `ModelSweep` 95 | `source.data_source = "simulated"` | `SimulationRun` / `ModelSweep` nodes; `model_consumes` 23, `in_family` 20 | current paper, model attribution via `Model`/`ModelFamily` | `test_figure_provenance` (panel-source resolution) | **no** — never enters `experiments.json`, so no `exp_id` exists |
| imported literature | `ImportedLiteratureObservation` 10 | `data_source` from the panel flag | `originally_reported_in` edge to a `cite::` `Paper` node with `cited_work=True`; the full KG carries `Arts 2019`, `Ylilammi 2018`, `Ylivaara 2020` as non-corpus Paper nodes | **both** papers (`reported_in` + `originally_reported_in`) | — | no |
| fitted / calculated | `Fit` 23 | — | `Fit` node; `fit_of_entity` points at the measured sibling's `entity_id` | current paper | — | **yes** — `fit_of_entity` stores a resolved `entity_id` (`to_kb.py:1203`, remapped at L1244) |
| transformed / derived | `DerivedRepresentation` 2 | `transformations[]` + `projections{}` | `TransformationExecution` 2126, `TransformationRule` 8, `RawQuantityValue` 2084, `CanonicalQuantityValue` 677, `derived_from_value` 2803 | rule id + `code_version` + `build_timestamp` | `tests/canonical_layer/test_provenance.py`, `test_rules.py` | no |

## The invariants that must not be disturbed

1. `panel_source_for` never returns `"measured"` as a default (`figure_extract.py:367-387`).
2. `build_canonical` copies `data_source`; it does not infer it.
3. `CLASS_MODEL[...]["is_experiment"] is False` for simulation, model sweep, imported
   literature, fit, derived representation, conceptual figure and unknown — the two gates at
   `to_kb.py:1039` and `:1127`.
4. `raw.points` byte-identical to `figure_data.json` (`validate_raw_unchanged`).
5. `pipeline/canonical/schema.py` raises `RuntimeError` at import if any `Status` value or
   the comparability layer is absent from the compiled ontology.

## The one identity coupling inside provenance

`fit_of_entity` is the only provenance field that stores a resolved entity id. It is set at
`to_kb.py:1203` from `_by_panel_label[(fig_docling_index, panel_key, series_label)]` and
remapped through `remap` at L1244 when ids are rewritten. 23 instances.
