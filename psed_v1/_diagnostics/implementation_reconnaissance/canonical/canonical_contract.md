# What the canonical layer actually promises

Producer: `pipeline/canonical/build_canonical.py` `build_curve()` / `build_paper()`.
Output: `papers/<doi>/canonical/curves.json`.

## Row granularity

**One row per SOURCE CURVE**, enumerated by `sources.iter_curves(doi)` from
`figure_data.json` slices `/figures/{fi}/panels/{pi}/series/{si}`.

- Not per scientific result.
- Not per representation (a scaled panel is its own source curve, so it is its own row —
  but the row exists because it is a drawn series, not because it is a representation).
- Not per Experiment. 1042 canonical curves vs 1127 experiments vs 1044 entities.

## `curve_id`

```python
"%s::F%s::%s::%d::%s" % (doi, figure_number, panel or "-", series_index, slot)
#  slot = "f{fi}p{pi}" from the json_pointer, else "i{figure}"
```

Its docstring is explicit: *"Deterministic across rebuilds AND unique per source series."*
The `f{fi}p{pi}` suffix exists because printed figure + panel + series index collapsed 833
rows into 828 ids. It identifies a **source slice**, and nothing else. It does not read
`entity_id`, `exp_id`, material, geometry or any condition.

## Experiment references

`source.linked_experiment_ids = [c["experiment_id"]] if c.get("experiment_id") else []`

A **list field**, populated from the record's linked experiment. Structurally it already
permits zero, one or many.

| question | answer |
|---|---|
| can multiple curves refer to one ExperimentalCase | yes — nothing prevents the same id appearing in several rows' lists |
| can one curve refer to multiple cases | yes structurally (a list); today it is populated with 0 or 1 element |
| can canonical represent `Sample` or `Measurement` references without schema change | yes — the row is a dict literal built in `build_curve()`; there is no schema class and `validate_curve` (`canonical/validate.py:112`) checks the axis/transformation/raw structure, not the `source` block's key set |
| does canonical enforce one material | it has **no material field at all** |
| does canonical enforce one geometry | it has **no geometry field at all** |
| does canonical care about Experiment count | no |

## Fields whose semantics must remain stable for existing consumers

| field | consumer |
|---|---|
| `curve_id` | `build_kg.py` (`Curve` nodes), `build_core_kg.py` (`canonical_curve_ids` provenance), `canonical/validate.py`, release audit |
| `source.data_source` | `build_core_kg.py:165-167` and `:255-257` — the `ResultSeries.source` field; falls back to `"unknown"`, never to `"measured"` |
| `source.json_pointer` + `source_checksum` | `validate_raw_unchanged` (`canonical/validate.py:241`) |
| `raw.points` | `validate_raw_unchanged` — asserted byte-identical to `figure_data.json` |
| `source.linked_experiment_ids` | `build_core_kg.py:112` join key |
| `transformations`, `projections`, `canonical` | comparability layer, KG `TransformationExecution`/`RawQuantityValue` |
| `source.figure_index`, `panel`, `series` | `build_core_kg.curves_for` slice join |
