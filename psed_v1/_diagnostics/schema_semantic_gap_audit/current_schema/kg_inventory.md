# KG inventory (read-only)

Full graph `papers/_corpus/knowledge_graph_onto.json`: 13323 nodes / 38055 edges (44 papers).
Core prototypes `knowledge_graph_core_flat.json` (1877/7243) and
`knowledge_graph_core_series.json` (1948/7385) also exist.

## Capability vs actual population
| requirement | schema capable? | current graph does it? | note |
|---|---|---|---|
| Paper -> Experiment | yes | yes (1127 Experiment nodes) | but Experiment is result-local |
| ExperimentCase as node | **yes** (`ExperimentalCase`) | **no (0 nodes)** | class defined, never emitted |
| Sample as node | **yes** (`Sample`) | **no (0 nodes)** | `produced_by_run`, `performed_on` unused |
| Measurement as node | **yes** (`Measurement`) | **no (0 nodes)** | `measures_case` unused |
| ResultSeries | yes (`PlotSeries` 1044, `Curve` 1042) | yes | **two node types for one object** |
| Representation | yes (`PlotRepresentation`) | **no (0)**; `DerivedRepresentation` only 2 | Yim Fig 9 triples instead |
| StudySeries membership many-to-many | multigraph permits it | **no** - `ExperimentSeries` is figure/table scoped | `case_in_series` unused |
| Material shared node | yes (25 Material nodes) | yes, but one material per paper upstream | level problem, not KG problem |
| Geometry | yes (`GeometryClass` in core prototypes) | stamped paper-level | level problem |
| Simulation separation | yes | **yes** - SimulationRun 112, ModelSweep 95, distinct from Experiment | **CORRECT** |
| Provenance reification | yes | yes - ConditionAssertion 3451, TransformationExecution 2126, Raw/CanonicalQuantityValue, ContextBinding 42 | KEEP, but see below |

## Node explosion
`ConditionAssertion` (3451), `TransformationExecution` (2126), `RawQuantityValue`,
`CanonicalQuantityValue` and `ContextBinding` together dominate the full graph. They are
correct **audit** objects and wrong **reading** objects. The existing two-layer direction
(full provenance graph + core scientific graph) remains valid and is independent of the
semantic gaps found here.

## Duplication
`PlotSeries` (1044) and `Curve` (1042) are two representations of one scientific object -
the result series - differing only in which layer emitted them. Flagged `DUPLICATED`.
