# Ontology inventory (read-only)

Source: `ontology/ald_ontology.json` (compiled from `core.yaml`, `core_extensions.yaml`,
`geometry_classes.yaml`). 226 classes, 75 relations, 181 quantity kinds.

## Headline finding
**The ontology already defines almost the entire target semantic model.** The gap is
instantiation, not vocabulary.

| concept | ontology class | documented meaning | resolved entities | KG nodes | status |
|---|---|---|---|---|---|
| ExperimentCase | `ExperimentalCase` | "A physically distinct experimental case performed under one supported condition set" | **0** | **0** | UNUSED_OR_UNINSTANTIATED |
| DepositionRun | `DepositionRun` | "An ExperimentalCase that is a film-growth run" | **0** | **0** | UNUSED_OR_UNINSTANTIATED |
| Sample | `Sample` | "A physical specimen produced by one or more deposition runs and **carried between measurements**" | **0** | **0** | UNUSED_OR_UNINSTANTIATED |
| Measurement | `Measurement` | "One measurement performed on a Sample or ExperimentalCase" | **0** | **0** | UNUSED_OR_UNINSTANTIATED |
| Representation | `PlotRepresentation` | "One depiction (as-measured / scaled / normalized / inset) of an underlying measurement" | **0** | **0** | UNUSED_OR_UNINSTANTIATED |
| Representation (derived) | `DerivedRepresentation` | "A transformation or redraw of another entity's data" | 2 | 2 | UNDER-INSTANTIATED |
| Experiment | `Experiment` | "One run at a unique combination of controlled conditions" | n/a (not an entity_class) | 1127 | OVERLOADED |
| StudySeries | `ExperimentSeries` | "A group of experiments **from one figure/table** that sweep a single condition (the per-point case)" | 166 | 327 | MISNAMED_OR_MISLEADING |
| ResultSeries | `PlotSeries` | "A drawn curve. **NEVER an Experiment**" | n/a | 1044 | KEEP |
| ModelRun | `SimulationRun` | "One execution of a model with a stated input set. **Not a current-paper Experiment**" | 112 | 112 | CORRECT_AS_IS |
| ModelSweep | `ModelSweep` | "A family of model evaluations... points are ModelPredictions, **not Experiments**" | 95 | 95 | CORRECT_AS_IS |
| ModelPrediction | `ModelPrediction` | "One predicted value... **Never an Experiment**" | 0 | 0 | UNUSED |
| Transformation | `TransformationRule` / `TransformationExecution` | reusable rule + one application | n/a | 8 / 2126 | KEEP (PROVENANCE_ONLY) |
| Conditions | `ConditionAssertion` | "One condition stated somewhere in a paper, with value, evidence, assertion status and scope" | n/a | 3451 | KEEP (PROVENANCE_ONLY) |

## Relations — the linking predicates all exist and are almost all unused
| relation | domain -> range | instantiated |
|---|---|---|
| `performed_on` | Measurement -> Sample | **no** |
| `measures_case` | Measurement -> ExperimentalCase | **no** |
| `produced_by_run` | Sample -> DepositionRun | **no** |
| `case_in_series` | ExperimentalCase -> ExperimentSeries | **no** |
| `derived_representation_of` | DerivedRepresentation -> Entity | **no** |
| `observation_of_kind` | Observation -> QuantityKind | **no** |
| `measured_by` | Experiment -> MeasurementMethod | **no** |
| `represents_same_as` | PlotRepresentation -> Measurement | yes (64) - but between *entity* and PlotSeries, not PlotRepresentation |
| `depicted_by` | Entity -> PlotSeries | yes (2171) |
| `assertion_of_kind` / `of_kind` / `produced_by` / `derived_from_value` | provenance | yes |

`represents_same_as` is instantiated with endpoint types
`(SimulationRun|ExperimentalProfile|MultiOutputMeasurement|ContinuousTrace|Fit|Unresolved) -> PlotSeries`,
i.e. it is used as "entity is depicted by this curve", **not** as the declared
`PlotRepresentation -> Measurement`. The declared domain is unused.

## Geometry
`geometry_classes` defines six classes (lateral_channel, vertical_structure,
porous_material, nanostructure_array, planar, cavity). The vocabulary is adequate; the
level at which it is applied is the problem (see `concept_audits/geometry.md`).
