# KG builder contract

Two builders. Neither derives nodes generically from the ontology.

## `pipeline/review/build_kg.py` — full ontology-aligned KG (13323 nodes / 38055 edges)

```python
# L403-407 — the entire node/edge API
def node(nid, ntype, label, **extra):
    if nid not in nodes: nodes[nid] = {"id": nid, "type": ntype, "label": label, **extra}
    return nodes[nid]
def link(s, t, etype):
    if s in nodes and t in nodes: links.append({"s": s, "t": t, "e": etype})
```

Properties of this API:

- Node creation is **explicit, class-by-class, hard-coded** at each call site.
- `ntype` is an arbitrary string; nothing checks it against the ontology.
- `etype` is an arbitrary string; nothing checks it either.
- `link()` **silently discards** an edge whose endpoints do not both already exist.
- `node()` is first-write-wins — a later `node()` on the same id is a no-op (which is why
  the `DerivedRepresentation` retype at L328 has no effect).
- `onto_class` is attached **generically** at serialization: `ONTO_IRI.get(n.get("type"))`
  (L583). Any node whose type string matches a declared class id gets the correct IRI with
  zero code change. 3983 of 13323 nodes currently serialize with an empty `onto_class`.

### The one closed dictionary

```python
# L262-273
_ENTITY_NODE = {"ContinuousTrace", "ExperimentalProfile", "MultiOutputMeasurement",
                "ExperimentSeries", "SimulationRun", "ModelSweep",
                "ImportedLiteratureObservation", "Fit", "DerivedRepresentation",
                "UnresolvedSourceEntity"}     # (dict, identity mapping)
# L297,304
ntype = _ENTITY_NODE.get(e.get("entity_class"))
node(uid, ntype or "UnresolvedSourceEntity", ...)
```

A resolved entity carrying an `entity_class` outside these 10 becomes an
`UnresolvedSourceEntity` node **with no warning and no error**.

### Node creation sites

| node type | site |
|---|---|
| `Experiment` | L417 (from `experiments.json`) |
| `Paper` | L428, L291, L323 (`cite::` for cited works) |
| `Material` | L432 |
| `Precursor` / `Coreactant` / `Carrier` | L436-444 |
| `Condition` / `Dependent` (QuantityKind roles) | L448-453, L344, L365 |
| `PlotSeries` | L286 |
| typed source entity | L304 |
| `Figure` | L294 |
| `ExperimentSeries` | series block |
| `ConditionAssertion` | L352, L369 |
| `Curve`, `RawQuantityValue`, `CanonicalQuantityValue`, `TransformationExecution`, `TransformationRule`, `ContextBinding`, `ComparisonGroup`, `Model`, `ModelFamily` | comparability layer, `_add_comparability_layer` L92 and `_emit_tbox` L45 |

## `pipeline/review/build_core_kg.py` — core KG (1877 / 7243 flat; 1948 / 7385 series)

Same `node`/`link` idiom, 11 node types: `Experiment` 851, `ResultSeries` 835,
`QuantityKind` 95, `Paper` 32, `Material` 25, `Precursor` 19, `Coreactant` 8,
`GeometryClass` 4, `Model` 4, `ProcessType` 3, `ModelFamily` 1 (+`ExperimentSeries` 71 in
the series variant).

It collapses `ConditionAssertion` into `fixed_conditions` node attributes and `varies` edges,
and collapses `PlotSeries` + `Curve` into `ResultSeries`.

**The core KG is currently stale**: 32 papers / 851 Experiments against the full graph's
44 / 1127 — it predates the 12-paper expansion (`knowledge_graph_core_flat.json` mtime
12:32 vs `knowledge_graph_onto.json` 14:01). Build currency, not a modelling difference.

## Which declared classes could appear without KG code changes

| class | full KG | reason |
|---|---|---|
| any class reached through `_ENTITY_NODE` | needs a dict entry | closed 10-entry map, silent fallback |
| a node created by a **new explicit `node()` call** | works immediately; `onto_class` resolves automatically via `ONTO_IRI` | generic IRI lookup |
| a new **edge type** between two existing nodes | works immediately; `etype` is unvalidated | but the edge vanishes silently if either endpoint is missing |

So: **`onto_class` assignment is generic; node typing is not.** `ExperimentalCase`,
`DepositionRun`, `Sample`, `Measurement`, `PlotRepresentation` and `ModelPrediction` would
all receive correct IRIs the moment a node of that type existed — and none can arise through
the entity path without editing `_ENTITY_NODE`.
