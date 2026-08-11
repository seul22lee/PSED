# Semantic invariants already available for reuse

Machinery that exists and could be read by any future check, listed as fact.

## Conservation accounting

| invariant | where computed | shape |
|---|---|---|
| series <-> records <-> points | `tests/canonical_layer/test_extraction_coverage.py`, release audit | Horvitz-Thompson-style |
| `n_observations == len(observations)` | `test_stage0_regression.py:80` | per entity |
| `physical_process_runs == len(physical_case_ids)` | `to_kb.py:1431-1436` summary, asserted at `test_granularity_and_axes.py:355` | per paper |
| `measurement_events == len(measurement_event_ids)` | `to_kb.py:1433-1437`, asserted at `:357` | per paper |
| `unresolved_granularity == len(unresolved_granularity_ids)` | same | per paper |
| `raw.points` byte-identical to `figure_data.json` | `canonical/validate.py:241` `validate_raw_unchanged` | per curve |
| curve_id uniqueness | canonical build + release audit | 1042/1042 |

## Refusal machinery (the model already declines rather than guessing)

| refusal | site |
|---|---|
| `material = None` when a multi-material paper gives no local evidence | `chemistry_scope.resolve_material` rung 7 |
| `case_status = "unresolved_settings"` when x density exceeds the cap | `to_kb.py:1066` |
| `classification = "unknown"` when signals conflict or only one family votes | `entities.py:~600` |
| `panel_source = "unresolved"` rather than `"measured"` | `figure_extract.py:387` |
| `ResultSeries.source = "unknown"` when the canonical join fails | `build_core_kg.py:257` |
| `temperature_C = None` for a non-degenerate window | `to_kb._scalar_from_degenerate_range` |
| `ambiguous_conditions` kept separately from `bound_conditions` | `conditions.bind()` |

## Evidence already attached to every record

`classification_evidence` (4 strings), `classification_method`, `classification_confidence`,
`material_evidence`, `material_scope_level`, `material_candidates`,
`material_ambiguity_reason`, `granularity_evidence`, `granularity_review_reason`,
`series_source_evidence`, `experimental_case_reason`, `chemistry_provenance`
(with `resolution_status`, `resolution_method`, `confidence`, `source_level`,
`supporting_evidence`), and per-condition `raw_evidence` + `evidence_locator`.

## Determinism guarantees

`code_version()` (git short SHA + dirty flag) and `build_timestamp()` are stamped on every
canonical document and every `TransformationExecution`. `validate_ontology_determinism`
(`canonical/validate.py:91`) checks the compiled ontology is reproducible.
