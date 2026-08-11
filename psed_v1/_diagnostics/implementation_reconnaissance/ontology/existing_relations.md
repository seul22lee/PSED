# Ontology relations — declaration vs emission

75 relations declared. Emission is entirely by explicit `link(...)` / `links.append(...)`
calls in `build_kg.py` and `build_core_kg.py`; there is no generic relation walker.

## Declared relations on the target classes — all zero-instance

| relation | domain -> range | emitted anywhere? |
|---|---|---|
| `case_in_series` | `ExperimentalCase -> ExperimentSeries` | no |
| `performed_on` | `Measurement -> Sample` | no |
| `measures_case` | `Measurement -> ExperimentalCase` | no |
| `produced_by_run` | `Sample -> DepositionRun` | no |
| `has_observation` | `Measurement -> Observation` | no |
| `predicted_by` | `ModelPrediction -> ModelSweep` | no |
| `derived_representation_of` | `DerivedRepresentation -> Entity` | no |
| `on_substrate` | `Experiment -> Substrate` | no |

## Declared and emitted

| relation | domain -> range | emitter | instances |
|---|---|---|---|
| `from_paper` | `Experiment -> Paper` | `build_kg.py:428`, `:292`, `:316` | 4418 |
| `deposits` | `Experiment -> Material` | `build_kg.py:432` | 1072 |
| `uses_precursor` | `Experiment -> Precursor` | `build_kg.py:443` | 825 |
| `with_coreactant` | `Experiment -> Coreactant` | `build_kg.py:437` | 790 |
| `varies` | `Experiment -> QuantityKind` | `build_kg.py:448` | 1127 |
| `measures` | `Experiment -> QuantityKind` | `build_kg.py:451` | 1127 |
| `controls` | (undeclared pair) | `build_kg.py:453` | 6042 |
| `shown_in` | `Experiment -> Figure` | `build_kg.py:295` | 2776 |
| `depicted_by` | `Entity -> PlotSeries` | `build_kg.py:315`, `:334` | 2171 |
| `in_series` | `Experiment -> ExperimentSeries` | series block | — |
| `series_varies` | `ExperimentSeries -> QuantityKind` | series block | 161 |
| `represents_same_as` | **declared** `PlotRepresentation -> Measurement` | `build_kg.py:329` | 64, with endpoints `(SimulationRun\|ExperimentalProfile\|MultiOutputMeasurement\|ContinuousTrace\|UnresolvedSourceEntity) -> PlotSeries` |
| `asserts_condition` / `assertion_of_kind` | assertion layer | `build_kg.py:360-361` | 3451 / 2601 |
| `originally_reported_in` | imported literature | `build_kg.py:324` | — |
| `carrier_gas`, `used_rule`, `has_raw_value`, `derived_from_value`, `of_kind`, `produced_by`, `in_comparison_group`, `used_context`, `context_of_kind`, `has_normalization_definition`, `model_consumes`, `in_family`, `in_category` | various | canonical/comparability layers | see kg_inventory |

## Emission mechanism

```python
# build_kg.py:403-407
def node(nid, ntype, label, **extra):
    if nid not in nodes: nodes[nid] = {"id": nid, "type": ntype, "label": label, **extra}
    return nodes[nid]
def link(s, t, etype):
    if s in nodes and t in nodes: links.append({"s": s, "t": t, "e": etype})
```

- `etype` is an **arbitrary string**. Nothing validates it against the declared relation set.
- `link()` **silently drops** an edge whose endpoints do not both already exist.
- `node()` is first-write-wins: a second `node()` call on an existing id changes nothing
  (this is why the `DerivedRepresentation` retype at L328 is a no-op).
- `onto_class` is attached at serialization by `ONTO_IRI.get(n.get("type"))`
  (`build_kg.py:583`) — a **generic lookup keyed on the node type string**. Any node whose
  type string equals an ontology class id automatically receives the right IRI. 3983 nodes
  currently serialize with an empty `onto_class` because their type is not a declared class
  id (`RawQuantityValue`, `CanonicalQuantityValue`, `Curve`, `Dependent`, `Condition`, ...).
