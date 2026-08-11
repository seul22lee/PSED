# Identity generator inventory

Every place an id is minted. Nothing here is a recommendation.

| identifier | file:function | exact inputs | deterministic? | document-coordinate inputs | semantic inputs | downstream consumers | collision handling | stability expectation |
|---|---|---|---|---|---|---|---|---|
| `exp_id` (provisional, per record) | `to_kb.py:1737` main record loop | `pid`, `fig` (`provenance.figure`, "Fig 7"->"F7"), `panel` letter, `len(exps)` | yes, given record order | figure, panel | none | only used to stamp `origin.experiment_id` on conditions before the final id exists | none — positional index | throwaway; overwritten at L1255 |
| `eid` (provisional entity) | `to_kb.py:904` `resolve_source_entities` | `pid`, loop index `idx` | yes, given record order | none | none | internal only; kept as `provisional_entity_id` | positional index | throwaway; overwritten at L1242 |
| `entity_key` | `to_kb.py:901-903` | `pid` \| `fig_docling_index` \| `printed_figure_number` \| `panel_key` \| `source_series` \| `representation` | yes | **4 of 6 fields** | `source_series` (a legend label), `representation` | stamped on every ConditionAssertion as `source_entity`; carried onto series records | **none — 41 duplicate values covering 89 entities; 996 unique for 1044 entities** | not enforced anywhere |
| `experiment_id` = final `entity_id` | `to_kb.py:793-828` `assign_experiment_ids` | `pid`, `printed_figure_number`, `panel`, group ordinal | yes | **all of them** | none | entities.json, experiments.json, series.json, results.json, KG `ent::`/`ps::`, core KG, canonical `linked_experiment_ids` | suffix `__exp%02d` when a figure/panel group has >1 member | treated as stable; 1044/1044 unique |
| `exp_id` (case record, final) | `to_kb.py:1130` + `1251-1255` | final `entity_id` + `__case%02d` when N>1 | yes | inherited | none | KG `Experiment` label, twin, dashboards, reports | index within the entity | 1127/1127 unique |
| `physical_case_id` | `to_kb.py:1265-1268` | `shares_physical_case_with` **or** `entity_id`; `None` when case count 0 and not sharing | yes | inherited from `entity_id` | `experimental_case_count` gates whether it exists at all | `results.json`, `build_core_kg.py:267`, `scripts/validate_granularity.py`, 2 tests | none | not enforced |
| `shares_physical_case_with` | `to_kb.py:1263` (set), `1221` (cleared) | `_events[(fig_docling_index, panel_key, granularity_kind)]` group, first member | yes | **key is entirely document coordinates** | `granularity_kind == "multi_output_measurement"` | same as above | none | not enforced |
| `measurement_event_id` | `to_kb.py:1270-1273` | `members[0].entity_id` + `"__meas"` when group >1 | yes | inherited | granularity kind | `results.json`, core KG, 2 tests | none | not enforced |
| `result_series_id` | `to_kb.py:1264` | `= entity_id` verbatim | yes | inherited | none | `results.json`, core KG `ResultSeries` | n/a | aliased to entity_id |
| `experimental_series_id` / `series_id` | `to_kb.py:1105` then `1277` | `pid-S%03d` then rewritten to `{entity_id}__series` | yes | inherited after rewrite | none | series.json, KG `es::` | positional | rewritten mid-build |
| `series_id` (alternate) | `canonical/live.py:155` | `pid`, `fig`, `panel`, `index` | yes | all | none | **no live caller found in `pipeline/`** | none | dormant helper |
| `point_experiment_id` | `canonical/live.py:160` | base series id + point index | yes | inherited | none | **no live caller found in `pipeline/`** | none | dormant helper |
| `curve_id` | `canonical/build_canonical.py:41-59` | `doi`, `figure_number`, `panel`, `series_index`, `f{fi}p{pi}` from `json_pointer` | yes | all | none | canonical/curves.json, KG `Curve`, core KG `ResultSeries` | **`json_pointer` slot appended precisely to break the 833->828 collision** | explicitly documented as "deterministic across rebuilds" |
| KG node ids | `build_kg.py` `e::`/`ps::`/`ent::`/`es::`/`ca::`/`q::`/`m::` | resolved ids or vocabulary strings | yes | inherited | vocabulary for `m::`/`q::` | KG JSON + viewers | `node()` is idempotent-by-first-write (L403-405) | rebuilt each run |
| `TransformationExecution` ids | `canonical/` rules layer | rule id + curve + axis | yes | inherited | rule identity | canonical, KG | — | rebuilt each run |

## Direct answers to the questions asked

- **Which IDs contain paper/figure/panel?** `entity_key`, `experiment_id`/final `entity_id`,
  case `exp_id`, `physical_case_id`, `shares_physical_case_with`, `measurement_event_id`,
  `result_series_id`, the rewritten `series_id`, `curve_id`, and every KG node id derived
  from them. Also the provisional `exp_id` (L1737).
- **Which IDs include representation?** `entity_key` only. It reaches no other identifier.
- **Which IDs include sweep index?** case `exp_id` (`__case%02d`), and the provisional
  `eid`/`exp_id` positional indices.
- **Which IDs include actual conditions?** **None.** No condition value enters any identifier
  at any layer.
- **Which IDs include material?** **None.**
- **Which IDs include geometry?** **None.**
- **Which are treated as persistent external identity?** `curve_id` (docstring states it),
  `experiment_id`/`entity_id` and case `exp_id` (referenced from canonical
  `source.linked_experiment_ids`, both KGs, twin, and dashboards).
- **Which could change without breaking canonical/source provenance?** `entity_key`,
  `physical_case_id`, `shares_physical_case_with`, `measurement_event_id`,
  `result_series_id`, `experimental_series_id`, and the two provisional ids. `curve_id` is
  computed from `json_pointer` + printed figure/panel and does not read `entity_id`; the only
  coupling is `source.linked_experiment_ids`, a list field.
- **Which are referenced across papers/artifacts/tests?** `exp_id` and `entity_id` (KG, twin,
  core KG, dashboards); `curve_id` (canonical validation, KG); `physical_case_id` and
  `measurement_event_id` (`tests/canonical_layer/test_granularity_and_axes.py:266,355,357`,
  `tests/canonical_layer/test_stage0_regression.py:110,416`,
  `scripts/validate_granularity.py:72,130`, `build_core_kg.py:266-267`).

## Measured uniqueness (live corpus, 44 papers)

```
entity_id             1044 / 1044  unique
provisional_entity_id 1044 / 1044  unique
exp_id (cases)        1127 / 1127  unique
entity_key             996 / 1044  unique   <-- 41 duplicate keys, 89 entities
curve_id              1042 / 1042  unique
```
