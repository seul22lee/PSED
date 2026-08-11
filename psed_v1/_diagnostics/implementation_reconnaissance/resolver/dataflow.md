# End-to-end dataflow for one experimental plotted result

Traced from code. Line numbers are as of HEAD 3848481.

## Stage map

```
extracted/figure_data.json  (vision)      extracted/records.json  (flattened curves)
        |                                          |
        +------------------+-----------------------+
                           v
  pipeline/resolve/to_kb.py  main() -> per-record loop (~L1690-1900)
                           |   mints  e{} ("exp" dict) + provisional exp_id
                           v
  to_kb.resolve_source_entities()  (L831-1278)     <== ALL scientific identity is minted here
      _entity_context()      L530-594   figure/panel/caption/representation context
      csid.resolve_panel()   L856       measured vs calculated, per panel
      caxis.resolve_axis()   L865-875   x/y axis semantics
      cgran.classify()       L876       granularity
      centities.classify()   L898       entity class (11-way)
      ekey  = ...            L901-903   entity_key
      eid   = pid-E%03d      L904       provisional entity id
      ccond.* + ccond.bind() L911-960   condition assertions -> bound/ambiguous
      case minting           L1037-1101 experimental_case_count / _status
      series minting         L1104-1122 ExperimentSeries
      case records           L1127-1187 one dict per case  (record_kind=ExperimentalCase)
      fit linking            L1193-1203 (fig, panel_key, series_label)
      _events grouping       L1210-1230 (fig, panel_key, granularity_kind)
      assign_experiment_ids  L1236      entity_id := pid__Fig7a[__expNN]
      physical_case_id       L1265-1268
      measurement_event_id   L1270-1273
                           v
  resolved/{entities,experiments,series,assertions,results}.json
                           v
  pipeline/canonical/build_canonical.py  build_curve() -> canonical/curves.json
                           v
  pipeline/review/build_kg.py  (full onto KG)   pipeline/review/build_core_kg.py (core KG)
                           v
  twin/twin_validation.py  _targets()  -- reads resolved/experiments.json only
```

## Transition table

| # | from -> to | file:function | inputs | outputs / IDs minted | copied | transformed | discarded | defaulted | semantic assumption |
|---|---|---|---|---|---|---|---|---|---|
| 1 | figure_data + records -> `e{}` | `to_kb.py` per-record loop L1690-1900 | vision record: coordinate, measurand, points, provenance{figure,panel}, series_kind/value, material | `exp_id = f"{pid}-{fig}{panel}-{len(exps)}"` (L1737, provisional) | points, measurand, coordinate | units normalised (`_norm_unit`), material resolved via `cschem.resolve_material` ladder | — | `geometry_class` from paper `geometry.json` via `_geom_for` | one vision record = one curve = one prospective experiment |
| 2 | `e{}` -> `ctx` | `to_kb._entity_context` L530-594 | figure_data figure/panel, records, structure | ctx dict incl. `representation`, `panel_key`, `source_series` | caption, panel conditions, panel series labels | `_representation(caption, panel)` L764 derives as_measured/scaled/normalized/inset/primary | — | `panel_key = panel or "#<ordinal>" or "-"` | the panel is the unit of measurement identity |
| 3 | `ctx` -> class | `entities.classify` L297-600 | caption, body, series label, source flags, coordinate, granularity | classification (11 classes), confidence, evidence, `signal_families`, `signals`, `supported_setting_count` | — | 8 signal families voted | **`signals`, `votes`, `supported_setting_count`, `supported_setting_evidence` are NOT written to the entity** | class `unknown` -> `UnresolvedSourceEntity` | class determines whether anything is an experiment |
| 4 | class -> case count | `to_kb` L1037-1101 | `CLASS_MODEL[cls]`, `granularity_kind`, distinct x values | `experimental_case_count`, `_status`, `_reason`, `_lower_bound` | — | sweeps expand to N cases | — | `case=1` for trace/profile/multi_output **unconditionally** | a profile panel is exactly one deposition case |
| 5 | case count -> case records | `to_kb` L1127-1187 | `e{}`, bound conditions | `exp_id = eid` or `eid-C%02d` | **`json.loads(json.dumps(e))` — a full deep copy per case** | `entity_class`/`record_kind` := `"ExperimentalCase"`; granularity remapped | — | `figure_slug = None` (comment says "filled by assign_experiment_ids"; it never is — 1127/1127 None) | the N cases of a sweep are interchangeable copies |
| 6 | entities -> final ids | `to_kb.assign_experiment_ids` L793-828 | `printed_figure_number`, `panel` | `experiment_id = pid__Fig7a[__expNN]` | — | `entity_id` **overwritten** by `experiment_id` (L1242); old kept as `provisional_entity_id` | — | slug `FigIdx<n>` or `NoFig` when the printed number is unresolved | the printed figure is the durable name of a record |
| 7 | entities -> case/event grouping | `to_kb` L1210-1273 | `(fig_docling_index, panel_key, granularity_kind)` | `physical_case_id`, `measurement_event_id`, `shares_physical_case_with` | — | first member of a `multi_output_measurement` group holds the case; the rest get `count=0` | — | `physical_case_id = None` when count 0 and not sharing (370/1044) | one physical case never spans two panels |
| 8 | resolved -> canonical | `build_canonical.build_curve` L64-160 | figure_data slice, `experiment_id` | `curve_id = doi::F{fig}::{panel}::{i}::f{fi}p{pi}` | raw points verbatim | axis canonicalisation + TransformationExecutions | — | `data_source = panel_source or source`, never "measured" | a canonical row is one **source curve**, not one result |
| 9 | resolved -> full KG | `build_kg.py` L376-580 | experiments.json, entities.json, series.json | `e::{pid}:{i}`, `ps::`, `ent::`, `es::`, `ca::` | node attrs | `_ENTITY_NODE` hard-coded 10-entry map (L262-273) | — | unknown entity_class -> `"UnresolvedSourceEntity"` **silently** (L304) | node type name == ontology class id (`ONTO_IRI.get(type)`, L583) |
| 10 | resolved -> twin | `twin_validation._targets` L416-423 | experiments.json | candidate list | — | filter on relevance/measurand/coordinate/points | — | — | one Experiment row = one comparable case |

## Where information is lost, precisely

- **Transition 3.** `classify()` computes `signals` (with the matched sample/run text) and
  `supported_setting_count`; `to_kb` copies only `signal_families` (the letters) and
  `classification_evidence` (4 strings). 268 entities across 24 papers carry family `I`
  (the sample/run/`Series X` identifier match) with the matched text dropped.
- **Transition 5.** The N case records of a sweep are byte-identical deep copies except
  `exp_id`/`case_index`. **408 of 561 swept cases do not carry their own swept quantity as
  a controlled condition** — the x value that defines the case never becomes a condition.
- **Transition 6.** `entity_id` is destructively overwritten. Nothing downstream can see the
  pre-figure-anchored id except via `provisional_entity_id`.
- **Transition 9.** A resolved entity class the KG map does not know becomes
  `UnresolvedSourceEntity` with no warning.
