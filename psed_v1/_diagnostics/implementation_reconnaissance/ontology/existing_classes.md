# Ontology classes — declaration vs instantiation

Compiled ontology: `ontology/ald_ontology.json`, 226 classes, 75 relations, 181 quantity kinds.

## The six zero-instance target classes

| class | parent | definition (verbatim, truncated) | instances |
|---|---|---|---|
| `ExperimentalCase` | `Experiment` | "A physically distinct experimental case performed under one supported condition set. Created only when the sou..." | 0 |
| `DepositionRun` | `ExperimentalCase` | "An ExperimentalCase that is a film-growth run (as opposed to a post-growth treatment or characterisation-only ..." | 0 |
| `Sample` | `Entity` | "A physical specimen produced by one or more deposition runs and carried between measurements." | 0 |
| `Measurement` | `Entity` | "One measurement performed on a Sample or ExperimentalCase, producing observations, a profile, or several obser..." | 0 |
| `PlotRepresentation` | `SourceEntity` | "One depiction (as-measured / scaled / normalized / inset) of an underlying measurement. Several representation..." | 0 |
| `ModelPrediction` | `Entity` | "One predicted value from a model. Never an Experiment." | 0 |

Each class carries only `id`, `iri`, `label`, `definition` and a parent. There are no
declared required properties, no cardinality constraints, and no property lists.

## Related declared classes

| class | parent | definition (truncated) | instances |
|---|---|---|---|
| `Experiment` | `Entity` | "One run at a unique combination of controlled conditions. A profile plot (thickness vs depth) is ONE experimen..." | 1127 |
| `PlotSeries` | `SourceEntity` | "A drawn curve. NEVER an Experiment: it is the depiction of some underlying case, measurement, simulation or im..." | 1044 |
| `ExperimentSeries` | `Entity` | "A group of experiments from one figure/table that sweep a single condition (the per-point case)." | 327 |
| `DerivedRepresentation` | `Entity` | "A transformation or redraw of another entity's data (scaled/normalized panel, ratio plot). Adds no new experim..." | 2 |

Note `ExperimentalCase` is a **subclass of** `Experiment`, and `DepositionRun` a subclass of
`ExperimentalCase`. The resolver already writes `entity_class = "ExperimentalCase"` and
`record_kind = "ExperimentalCase"` on every case record (`to_kb.py:1141-1142`), and the full
KG carries `record_kind: "ExperimentalCase"` on all 1127 `Experiment` nodes — while typing
the node `Experiment`, whose `onto_class` IRI is `...#Experiment`.

## Instantiated entity classes (corpus)

```
MultiOutputMeasurement 377   ExperimentSeries 327   ContinuousTrace 118
SimulationRun          112   ModelSweep        95   ExperimentalProfile 71
UnresolvedSourceEntity  70   Fit               23   ImportedLiteratureObservation 10
DerivedRepresentation    2
```

Source of truth for which of these can exist: `entities.py:657-668` `ENTITY_CLASS`, an
11-entry dict mapping classification -> class name. A class not in that dict cannot be
produced by the resolver.

## Repository-wide symbol search

| symbol | occurrences outside the ontology files |
|---|---|
| `ExperimentalCase` | `to_kb.py:1141-1142` (string literals for `entity_class`/`record_kind`); `entities.py` docstrings |
| `DepositionRun` | `to_kb.py:1191` (a comment: "it never mints a DepositionRun or a Sample of its own"); `to_kb.py:1990` `"deposition_runs"` summary key computed from cases |
| `Sample` | `entities.py:69-73` `SAMPLE_ID`/`SAMPLE_LIST` regexes; `samples_are` field; comments |
| `Measurement` | `CLASS_MODEL["discrete_experimental_sweep"]["measurement"] = "Measurement"` (`entities.py:637`) — a **string written into `measurement_class`**, never a node type |
| `PlotRepresentation` | ontology only |
| `ModelPrediction` | ontology only; `samples_are: "model_predictions"` is a different string |

`measurement_class` is worth isolating: `CLASS_MODEL` assigns
`ContinuousTrace | ExperimentalProfile | MultiOutputMeasurement | Measurement | None`, and
`"Measurement"` is used for `discrete_experimental_sweep`. It reaches the KG only as the
`measurement_class` display attribute on `Experiment` nodes (`build_kg.py:418`).
