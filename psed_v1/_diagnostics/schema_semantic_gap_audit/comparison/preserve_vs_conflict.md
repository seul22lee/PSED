# Preserve / clarify / conflict

Classification of every element examined. "Conflict" means the current design actively
contradicts the target semantics, not merely that it is silent about them.

## PRESERVE — correct, do not touch in any future repair

| element | why |
|---|---|
| `SimulationRun`, `ModelSweep`, `Model`, `ModelFamily`, `model_consumes`, `in_family` | model results are already first-class and separated from measurement; 112 + 95 instances; Yim Fig 10 correct |
| `data_source` on every canonical curve, never defaulted | the B2 release fix; the single most load-bearing provenance flag in the corpus |
| `ImportedLiteratureObservation`, `originally_reported_in`, non-corpus Paper nodes | third-party data is not attributed to the citing paper |
| `TransformationRule` / `TransformationExecution` / `RawQuantityValue` / `derived_from_value` | full numeric provenance, 2126 executions |
| `curve_id` scheme `{doi}::F{fig}::{panel}::{i}::f{fi}p{pi}` | an honest *source* identity; unique 1042/1042 |
| `QuantityKind` (181) and the unit-normalization fields | the measurement vocabulary is sound |
| `Fit` (23), `ComparisonGroup` (11), `ContextBinding` (42) | small but correctly scoped |
| figure provenance / disposition layer | out of scope here, and it is the layer that currently works |

## CLARIFY — keep the element, fix its documented meaning or its level

| element | problem | clarification needed |
|---|---|---|
| `Experiment` | means "a sweep point minted from a figure panel" but is read as "a deposition case" | either rename to `ObservedCaseRecord` or make it actually case-scoped; **do not** keep both readings |
| `ExperimentSeries` | means "a sweep within one figure", is read as "the author's study series" | separate the two; `case_in_series` already exists for the second |
| `physical_case_id` | promises a specimen, delivers a panel-local group | rename to `measurement_event_group_id`, or make it genuinely cross-figure |
| `material` on Experiment | correct field, wrong scope level | `material_scope_level` already records the scope; let it win |
| `geometry_class` on Experiment | correct field, stamped paper-wide by `tag_experiments` | move the decision to the case |
| `MultiOutputMeasurement` / `ExperimentalProfile` / `ContinuousTrace` | these are *result shapes*, not measurement acts | keep as shape classes; do not let them stand in for `Measurement` |

## CONFLICT — active contradiction

| conflict | statement A | statement B | which is right |
|---|---|---|---|
| C1 | ontology: `PlotSeries` is "NEVER an Experiment" | resolver mints an Experiment per plot series | ontology |
| C2 | ontology: `ExperimentalCase` = "one supported condition set" | `entity_id` = paper + figure + panel | ontology |
| C3 | ontology: `PlotRepresentation` = "one depiction ... of an underlying measurement" | `representation` is baked into `entity_key`, guaranteeing separate identities | ontology |
| C4 | ontology: `Sample` = "carried between measurements" | `physical_case_id` never crosses a figure (608/608 single-figure) | ontology |
| C5 | `material_scope_level` distinguishes paper-level from panel-level attribution | the paper-level value is applied regardless | the field |
| C6 | `represents_same_as` is declared `PlotRepresentation -> Measurement` | its 64 instances run `(SimulationRun\|ExperimentalProfile\|MultiOutputMeasurement\|ContinuousTrace\|Unresolved) -> PlotSeries` | the declaration |
| C7 | full onto KG: 44 live papers, 1127 Experiments | core KG: 32 papers, 851 Experiments | neither — the core KG is simply stale |

C7 is a build-currency defect, not a schema defect: `knowledge_graph_core_flat.json` and
`knowledge_graph_core_series.json` (mtime 12:32) predate `knowledge_graph_onto.json`
(14:01) and are missing all 12 expansion papers. Recorded here because any reader
comparing the two graphs would otherwise read it as a modelling disagreement.

## KNOWN EXTRACTION ISSUE — OUTSIDE THIS AUDIT

- `am.2016.182`: printed Figure 4 missing due to caption grammar.
- `c7ta03257a`: Fig 8b missing due to a Docling PictureItem gap.

Neither is a schema question and neither is repaired or counted here.
