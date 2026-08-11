# `physical_case_id` and `shares_physical_case_with`

## Production chain

```
centities.classify(ctx)                       -> classification
CLASS_MODEL[classification]["case"]           -> n_cases        (to_kb L1039-1073)
_events[(fig_docling_index, panel_key, granularity_kind)]        (to_kb L1210-1214)
    shared = (granularity_kind == "multi_output_measurement" and len(members) > 1)
    holder = members[0]
    for i, ent in enumerate(members):
        if shared and i:  ent["_shares_with"] = holder          (L1222-1230)
...
ent["shares_physical_case_with"] = holder["entity_id"]           (L1263)
ent["physical_case_id"] = (shares_physical_case_with or entity_id)
                          if (experimental_case_count or shares_physical_case_with)
                          else None                              (L1265-1268)
```

## Determinations

| question | answer | evidence |
|---|---|---|
| which function produces `shares_physical_case_with` | `to_kb.resolve_source_entities`, the `_events` loop | L1210-1230, assigned L1263 |
| what evidence is required | `granularity_kind == "multi_output_measurement"` **and** more than one entity in the same `(fig_docling_index, panel_key, granularity_kind)` bucket | L1216 |
| can only sibling channels/panels reference one another | **only sibling channels of the same panel.** Not even sibling panels: `panel_key` is part of the grouping key | L1212-1213 |
| are arbitrary cross-figure ids technically allowed | the field is a plain string with no validator; nothing rejects a cross-figure value. **No code produces one.** | grep: only L1263 assigns it |
| does the schema permit them | there is no schema for resolved JSON — no dataclass, no JSON Schema, no pydantic model. It is a free-form dict | `pipeline/canonical/schema.py` covers the canonical layer only |
| does serialization permit them | yes; `json.dumps` of the entity dict | |
| do later stages assume same-figure locality | no stage tests locality. `build_core_kg.py:267` passes it through as a provenance field. `to_kb` L1431-1438 and L1530-1534 only count `len(set(...))` | |
| do tests assume the current format | no test parses the string. Two tests assert **cardinality**: `test_granularity_and_axes.py:266` (`len({physical_case_id}) == 1` per figure) and `:355` (`len(s["physical_case_ids"])`); `test_stage0_regression.py:416` asserts presence | |
| does any code parse the string form | **no.** No `split`, regex, or prefix test is applied to `physical_case_id` anywhere | grep across `pipeline/ twin/ scripts/ tests/ ontology/` |

## Complete consumer list

| consumer | use |
|---|---|
| `to_kb.py:1367,1370` | writes it into `results.json` rows |
| `to_kb.py:1431-1436` | paper summary: `physical_case_ids` (sorted set), `physical_process_runs` (count) |
| `to_kb.py:1530-1531` | figure-level summary: same |
| `build_core_kg.py:267` | passes into `ResultSeries` node provenance |
| `scripts/validate_granularity.py:72,130` | orphan check — a referenced id must exist |
| `tests/canonical_layer/test_granularity_and_axes.py:266,355` | cardinality assertions |
| `tests/canonical_layer/test_stage0_regression.py:416` | presence assertion |

Seven sites, none of which depends on the value's internal structure.

## Measured shape (live corpus)

```
entities                                     1044
physical_case_id present                      674
physical_case_id None                         370
distinct physical_case_id groups              608
groups spanning >1 printed figure               0
groups spanning exactly 1 printed figure      608
shares_physical_case_with set                  66
measurement_event_id present                 1044 / 1044
```

The 608/608 single-figure result is not a property of the corpus; it is entailed by the
grouping key at L1212, which contains `fig_docling_index`.

## Name vs behaviour

`physical_case_id` is, by construction, `entity_id` for any entity that mints at least one
case, and the holder's `entity_id` for the non-first channels of a multi-output panel. It
therefore denotes *"the entity that owns the case for this panel-local measurement group"*.
It carries no physical-specimen evidence of any kind.
