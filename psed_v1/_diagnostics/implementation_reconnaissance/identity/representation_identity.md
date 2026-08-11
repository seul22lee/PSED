# Representation handling

## Where the label comes from

`to_kb._representation(caption, panel)` L764-774:

```python
_REPR = [(r"as[- ]measured","as_measured"), (r"\bscaled\b","scaled"),
         (r"normali[sz]ed","normalized"), (r"\binset\b","inset")]

def _representation(caption, panel):
    clause = ""                       # the caption text from "(<panel>)" to the next "(x)"
    if panel:
        m = re.search(r"\(\s*%s\s*\)" % re.escape(panel), caption or "", re.I)
        if m:
            nxt = re.search(r"\(\s*[a-h]\s*\)", caption[m.end():], re.I)
            clause = caption[m.start(): m.end() + (nxt.start() if nxt else 200)]
    for rx, lab in _REPR:
        if clause and rx.search(clause): return lab
    return "primary"
```

It is **source metadata**: a keyword match inside this panel's caption clause. It asserts
nothing about the relationship between two panels.

Corpus: `primary` 960, `scaled` 33, `normalized` 30, `as_measured` 20, `inset` 1 (1044/1044
populated).

## Where it goes

| sink | file:line | effect |
|---|---|---|
| `entity_key` field 6 | `to_kb.py:903` | part of the key string |
| `entity.representation` | `to_kb.py:985` | persisted |
| KG `PlotSeries` node attribute | `build_kg.py:289` | display only |
| KG `represents_same_as` edge | `build_kg.py:327-329` | emitted when representation is `scaled`/`normalized`/`inset` |
| Experiment minting | — | **nowhere. No branch reads `representation`.** |

## The `represents_same_as` edge as implemented

```python
# build_kg.py:326-329
if e.get("representation") in ("scaled", "normalized", "inset"):
    node(uid, ntype or "DerivedRepresentation", nodes[uid]["label"])
    link(uid, ps, "represents_same_as")
```

- Endpoints are `entity -> its own PlotSeries`, i.e. the entity and its own depiction. The
  ontology declares `represents_same_as: PlotRepresentation -> Measurement`.
- The `node(uid, ...)` retype on the preceding line is a **no-op**: `node()` returns early
  when the id already exists (`build_kg.py:403-405`), and `uid` was created at L304.
- 64 instances corpus-wide, with source types `SimulationRun | ExperimentalProfile |
  MultiOutputMeasurement | ContinuousTrace | UnresolvedSourceEntity`.
- No edge ever links two different entities.

## Empirical: does representation split identities?

Measured over all 1044 entities, grouping `entity_key` on its first five fields (dropping
representation):

```
groups that differ ONLY by representation:  0   (0 entities)
```

`representation` is derived from the panel's own caption clause, so within a fixed
`(figure, panel, series)` it is constant. **Including it in `entity_key` changes no
identity in this corpus.** The split is produced by `panel_key` being in `entity_key` and
by `panel` being in `figure_slug` -> `experiment_id`.

## Yim Fig 9 trace

18 entities, 18 cases, 18 canonical curves.

| entity_id suffix | panel | representation | classification | case count | status |
|---|---|---|---|---|---|
| `Fig9a__exp01..03` | a | `as_measured` | `experimental_profile` | 1 each | `supported` |
| `Fig9b__exp01..03` | b | `scaled` | `experimental_profile` | 1 each | `supported` |
| `Fig9c__exp01..03` | c | `normalized` | `experimental_profile` | 1 each | `supported` |
| `Fig9d__exp01..03` | d | `as_measured` | `experimental_profile` | 1 each | `supported` |
| `Fig9e__exp01..03` | e | `scaled` | `experimental_profile` | 1 each | `supported` |
| `Fig9f__exp01..03` | f | `normalized` | `experimental_profile` | 1 each | `supported` |

The representation label is **detected correctly on every panel**. Duplication arises at
`to_kb.py:1040` — `CLASS_MODEL["experimental_profile"]["case"] == 1` mints one case
unconditionally, with no branch consulting `representation`. It is then carried into
`assign_experiment_ids` (which sees only figure and panel) and into `curve_id` (which sees
only the source pointer).

## Transformation provenance and representations

`TransformationExecution` (2126 instances) is produced by the canonical axis layer
(`canonicalize_axis`) and records unit/axis conversions of **one curve**, with
`derived_from_value` back to a `RawQuantityValue`. It is per-axis-of-one-curve. It carries
no source-curve -> target-curve relation, so it cannot express "panel b is panel a scaled".
Transformations are reconstructed from declared rules (`quantity_relations.transformation_rules`
in the compiled ontology), not from equations recovered from the paper.

`DerivedRepresentation` exists as an entity class (`entities.py:661-662`, reached by
classifications `derived_representation` and `conceptual_figure`) and has 2 instances.
`PlotRepresentation` has no producer in any pipeline module.
