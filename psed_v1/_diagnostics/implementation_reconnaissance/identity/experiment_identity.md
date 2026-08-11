# Experiment minting — branch table

Producer: `to_kb.resolve_source_entities`, L1037-1101 (count) and L1127-1187 (records).

## The gate

```python
# L1039
if model["is_experiment"]:            # model = centities.CLASS_MODEL[classification]
    if model["case"] == 1: n_cases, case_status = 1, "supported"
    elif model["case"] == "from_evidence": ...
# L1127
if model["is_experiment"] and n_cases >= 1:
    for k in range(n_cases): ...      # one deep copy of e{} per case
```

`experimental_case_status` is an **output label describing the branch taken**, not an input.
The gate is `model["is_experiment"] and n_cases >= 1`. Status and count are co-determined in
the same block, so the status does correlate perfectly with minting — but no code reads the
status to decide anything.

## Branch table

| classification | `is_experiment` | `case` | branch | n_cases | resulting status | observed |
|---|---|---|---|---|---|---|
| `continuous_trace` | True | `1` | unconditional | 1 | `supported` | 118 entities |
| `experimental_profile` | True | `1` | unconditional | 1 | `supported` | 71 |
| `multi_output_measurement` | True | `1` | unconditional, then possibly zeroed by the `_events` pass | 1 or 0 | `supported` / `shared_measurement_event` | 377 |
| `discrete_experimental_sweep` | True | `from_evidence` | see sub-branches | 0..N | 5 statuses | 327 |
| `simulation` | False | 0 | rejected | 0 | `not_an_experiment` | 112 |
| `model_sweep` | False | 0 | rejected | 0 | `not_an_experiment` | 95 |
| `imported_literature_data` | False | 0 | rejected | 0 | `not_an_experiment` | 10 |
| `fit` | False | 0 | rejected | 0 | `not_an_experiment` | 23 |
| `derived_representation` | False | 0 | rejected | 0 | `not_an_experiment` | 2 |
| `conceptual_figure` | False | 0 | rejected | 0 | `not_an_experiment` | 0 |
| `unknown` | False | 0 | rejected | 0 | `not_an_experiment` | 70 |

### `from_evidence` sub-branches (L1042-1073)

| condition | n_cases | status |
|---|---|---|
| `granularity_kind != "independent_process_sweep"` | 0 | `not_an_independent_sweep` (31) |
| `< 2` distinct x values | 1 | `single_setting_only` (5) |
| `2..MAX_UNENUMERATED_SETTINGS` distinct x | that count | `independent_process_sweep` (103) |
| more than the cap | 0 | `unresolved_settings` (27) |
| classified as sweep but <=1 observation (L1091) | 1 or 0 | `single_setting_only` |
| channel `i>0` of a `multi_output_measurement` group (L1222-1229) | forced to 0 | `shared_measurement_event` (66) |

Corpus totals: `supported` 500, `not_an_experiment` 312, `independent_process_sweep` 103,
`shared_measurement_event` 66, `not_an_independent_sweep` 31, `unresolved_settings` 27,
`single_setting_only` 5.

## Answers to the specific questions

- **How are conditions attached?** `ccond.bind()` (L959) produces `bound` and `ambiguous`;
  L1157-1178 copies each bound assertion with a value into `c["controlled"]`, preserving
  `source_kind`, `bound_at_scope`, `species`, `raw_evidence` and `evidence_locator`. Every
  case of a sweep receives the **same** bound list.
- **Do x-axis values become case conditions?** **No.** The N case records are
  `json.loads(json.dumps(e))` deep copies (L1129) carrying the identical full `points` array;
  only `exp_id` and `case_index` differ. Measured: **561 swept cases, 153 carry the swept
  quantity in `controlled` (from an unrelated source), 408 do not.** Top absent quantities:
  `deposition_temperature` 109, `exposure_time` 52, `pulse_time` 46, `feature_height` 43,
  `cycle_number` 42.
- **Cross-result deduplication?** None. There is no pass that compares two entities' conditions.
- **Can experiments from different entities merge?** No. Every merge-like mechanism in the
  file (`_by_panel_label` L1193, `_events` L1210) is keyed on `fig_docling_index` and
  `panel_key`, so it cannot reach across a panel boundary.
- **Is Experiment identity consulted after creation?** Only for renaming (L1237-1259) and
  for `origin.experiment_id` rewrites on conditions. No semantic decision reads it.
- **`figure_slug` on case records** is set to `None` at L1140 with the comment "filled by
  assign_experiment_ids"; that function iterates `entities`, not `cases`. Measured:
  **`None` on all 1127 case records.**
