# `experimental_case_status` and the classification gates

## Assignment sites

| status | site | trigger |
|---|---|---|
| `not_an_experiment` | `to_kb.py:1038` (initialiser) | never overwritten because `model["is_experiment"]` is False |
| `supported` | L1041 | `CLASS_MODEL[cls]["case"] == 1` |
| `not_an_independent_sweep` | L1050 | `granularity_kind != "independent_process_sweep"` |
| `single_setting_only` | L1055, L1094 | fewer than 2 distinct x values, or a sweep with <=1 observation |
| `independent_process_sweep` | L1058 | 2..`MAX_UNENUMERATED_SETTINGS` distinct x |
| `unresolved_settings` | L1066 | more distinct x than the cap |
| `shared_measurement_event` | L1225 | non-first channel of a multi-output panel group |

Allowed values are not declared anywhere — there is no enum, no validator, no schema. The
seven strings above are the complete observed set.

## Evidence source

`classification` (from `entities.classify`, 8 voting signal families) and `granularity_kind`
(from `granularity.classify`, using x-axis role, source kind, caption, methods, body, panel
labels, point count). Neither reads the paper's own statement about how many samples were
made, except via `supported_setting_count`, which is computed and discarded.

## Consumers

| consumer | reads it as |
|---|---|
| `build_kg.py:314` | `case_status=` node attribute on the typed entity node (display) |
| `to_kb.py` summaries L1431-1438, L1530-1534 | counted only indirectly, via `physical_case_id` presence |
| `to_kb.py:1265-1268` | `physical_case_id` is `None` unless `experimental_case_count` is truthy — this is the count, not the status |
| everything else | not read |

**Which branches ignore it:** all of them. No `if ... experimental_case_status ...` exists
in the repository outside `to_kb.py`'s own assignment block.

**Does it affect Experiment count?** Not causally. The gate at L1127 is
`model["is_experiment"] and n_cases >= 1`. `case_status` is written in the same block that
computes `n_cases`, so the two always agree, but the status string is a description of the
branch, not a condition on it.

**Does it affect `entity_class`?** No. `entity_class = ENTITY_CLASS[classification]`
(L971), which is upstream of the status.

**Does it survive into canonical/KG?** Not into canonical. Into the full KG only as the
`case_status` display attribute on the `ent::` node (`build_kg.py:314`). The core KG does
not carry it.

## Worked examples

| case | paper | entity | classification | status | count |
|---|---|---|---|---|---|
| `not_an_experiment` | `10.1039_c7ta03257a` | `Fig7a__exp01` | `unknown` (`UnresolvedSourceEntity`) | `not_an_experiment` | 0 |
| experimental case | `10.1039_d0cp03358h` | `Fig9a__exp01` | `experimental_profile` | `supported` | 1 |
| simulation/model | `10.1039_d0cp03358h` | Fig 10 entities | `simulation` | `not_an_experiment` | 0 |
| characterization | `10.1039_c7ta03257a` | `Fig8a__exp01/02` | `unknown` | `not_an_experiment` | 0 |
| shared channel | multi-output panels | non-first channels | (parent class kept) | `shared_measurement_event` | forced 0 |

## Name vs behaviour

The name reads as a judgement about whether the source supports an experimental case. The
behaviour is: *"which branch of the case-count computation this entity took"*. Where a
paper states its own sample count, `supported_setting_count` captures it and then no status
uses it.
