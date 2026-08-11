# Scientific vs provenance nodes

## Full onto KG — 13323 nodes

| node type | n | role |
|---|---|---|
| `ConditionAssertion` | 3451 | provenance (an assertion, with evidence + locator) |
| `TransformationExecution` | 2126 | provenance |
| `RawQuantityValue` | 2084 | provenance |
| `Experiment` | 1127 | **scientific** |
| `PlotSeries` | 1044 | source/document |
| `Curve` | 1042 | canonical numeric |
| `CanonicalQuantityValue` | 677 | provenance |
| `MultiOutputMeasurement` | 377 | **scientific** (result shape) |
| `ExperimentSeries` | 327 | **scientific** |
| `Figure` | 217 | document |
| `ContinuousTrace` | 118 | **scientific** (result shape) |
| `SimulationRun` | 112 | **scientific** |
| `ModelSweep` | 95 | **scientific** |
| `Condition` | 78 | vocabulary (QuantityKind by role) |
| `ExperimentalProfile` | 71 | **scientific** (result shape) |
| `UnresolvedSourceEntity` | 70 | **scientific, untyped** |
| `Dependent` | 54 | vocabulary |
| `Paper` | 47 | document (44 corpus + 3 cited works) |
| `ContextBinding` | 42 | provenance |
| `Material` | 25 | vocabulary |
| `Precursor` 24, `Fit` 23, `ComparisonGroup` 11, `ImportedLiteratureObservation` 10, `Model` 4, `ModelFamily` 1, `TransformationRule` 8 | | |

Edges: `controls` 6042, `from_paper` 4418, `asserts_condition` 3451, `derived_from_value`
2803, `shown_in` 2776, `assertion_of_kind` 2601, `of_kind` 2355, `depicted_by` 2171,
`used_rule` 2126, `has_raw_value` 2084, `varies` 1127, `measures` 1127, `deposits` 1072,
`uses_precursor` 825, `with_coreactant` 790, `in_comparison_group` 677, `produced_by` 677,
`carrier_gas` 418, `series_varies` 161, `in_category` 64, `represents_same_as` 64,
`has_normalization_definition` 43, `used_context` 42, `context_of_kind` 42,
`model_consumes` 23, `in_family` 20.

## `PlotSeries` 1044 vs `Curve` 1042 — layer separation or duplication?

**Both, depending on the projection.** They are produced by different layers from different
sources and are not joined by any edge:

| | `PlotSeries` | `Curve` |
|---|---|---|
| producer | `build_kg._add_entity_layer` L286 from `entities.json` | comparability layer from `canonical/curves.json` |
| id | `ps::<entity_id>` | canonical `curve_id` |
| identifies | the resolved entity's depiction | the canonical source slice |
| carries | figure/panel/series/representation/observation count | raw + canonical points, transformations, projections |
| n | 1044 (one per entity) | 1042 (one per source curve) |
| edge between them | **none** | |

The 2-row difference is not a mismatch of the same population: entities and canonical curves
are enumerated independently (entities from resolved records, curves from `figure_data.json`
slices). In the **core KG** both collapse into a single `ResultSeries` (835), with
`canonical_curve_ids` as an attribute — so the core projection treats them as one object and
the full projection treats them as two.

## The 370 entities with `physical_case_id = None`

They still appear as `PlotSeries` + typed-entity nodes with their condition assertions. They
are absent only from `experiments.json`, the core KG, and the twin.
