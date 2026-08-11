# Test dependency inventory

31 test modules. Only those touching identity, counts or semantics are listed.

| test | assumption | semantic or incidental | likely affected by identity work | protects correct behaviour | freezes old behaviour |
|---|---|---|---|---|---|
| `test_stage0_regression.py:61` no experiment count from point count | a spatial/measurement axis yields <=1 case | **semantic** | no | **yes** | no |
| `:72` a PlotSeries is never an Experiment | non-experimental classes have `is_current_paper_experiment` False and 0 cases | **semantic** | no | **yes** | no |
| `:78` observations are not experiments | `n_observations == len(observations)`, `observations_are_experiments` False | **semantic** | no | **yes** | no |
| `:85` continuous traces are one case | `experimental_case_count == 1`, `measurement_class == "ContinuousTrace"` | **semantic + count** | **yes** — pins one-case-per-trace | partly | partly |
| `:92` profiles are measurements not point experiments | `== 1` and `measurement_class == "ExperimentalProfile"` | **semantic + count** | **yes** — this is the assertion Yim Fig 9 satisfies while triple-counting | partly | partly |
| `:99` multi-output does not create one experiment per channel | per shared group, `sum(case_count) <= 1` | **semantic** | **yes** — the assertion is written on the `(fig, panel, gran)` group | **yes** | no |
| `:123` imported literature keeps both papers | `reported_in` and `originally_reported_in` both set | **semantic** | no | **yes** | no |
| `:131` unknown entities preserved unsplit | `case_count == 0`, `unresolved_reason` set, class `UnresolvedSourceEntity` | **semantic** | **yes** if characterization linkage changes the class | **yes** | partly |
| `:141` representations do not duplicate the underlying case | `experimental_case_count <= 1` **per entity** | **semantic, but per-entity** | **yes** — it is satisfied today by Yim Fig 9's 18 one-case entities | intent correct, scope too narrow | **yes** — its per-entity scope is what lets 18 entities pass |
| `:148` no observation was lost | conservation | **semantic** | no | **yes** | no |
| `:416` orphan check on `shares_physical_case_with` | referenced holder must exist | incidental | no | yes | no |
| `test_granularity_and_axes.py:266` pssa XPS channels share one sample | `len({physical_case_id}) == 1` per figure, `sum(case_count) == 1` | **semantic** | **yes** — pins figure-local case grouping | **yes** for this paper | the *figure* scope is incidental |
| `:255` independent sweep has `case_count > 1` | count | **semantic** | **yes** | yes | no |
| `:~340` ids use the printed figure number | `exp_id` anchored on printed, not docling, number | **incidental (format)** | **yes** | yes — it guards a real past defect | **yes** — it pins the id format |
| `:355,357` summary counts auditable | `physical_process_runs == len(physical_case_ids)`, `measurement_events == len(measurement_event_ids)` | incidental (self-consistency) | no | yes | no |
| `test_extraction_coverage.py` | series/record/point conservation | **semantic** | no | **yes** | no |
| `test_provenance.py` / `canonical_layer/test_provenance.py` | card-field provenance, window-never-endpoint, transformation chain | **semantic** | no | **yes** | no |
| `test_figure_provenance.py` (~20 sections) | caption grammar, dispositions, identity separation, split-crop guard, stale invalidation, idempotency, panel normalisation, panel-source resolution, corpus DRILL anchor, scout union | **semantic** | no — upstream of resolve | **yes** | no |
| `test_twin_validation.py:63,65` | `len(STATUS) >= 15`, `len(LOCI) == 6` | incidental | no | partly | **yes** |
| `test_twin_validation.py` (candidate count) | a fixed expected candidate count | **count snapshot** | **yes** | no | **yes** — already known brittle (the 26/27 issue) |
| `test_rules.py`, `test_units.py`, `test_context.py`, `test_semantics.py` | canonical transformation/unit/context behaviour | **semantic** | no | **yes** | no |
| `test_ontology_relationships.py` | ontology internal consistency | **semantic** | no | **yes** | no |
| `test_report_freshness.py` | reports newer than inputs | incidental | **yes** — any regeneration | no | no |
| `scripts/validate_granularity.py:72,130` | orphan check on `shares_physical_case_with` / `physical_case_id` | incidental | no | yes | no |

## Tests that parse identifier strings

`tests/canonical_layer/test_granularity_and_axes.py` ("ids use the printed figure number"),
`tests/canonical_layer/test_provenance.py`, `test_extraction_coverage.py`,
`test_live_and_comparison.py`, `test_stage0_regression.py`,
`tests/regression/test_provenance.py`, `test_pressure_compat.py`,
`tests/integration/validate_layout.py` all reference `exp_id`/`entity_id`/`curve_id` by
name; only the printed-figure-number test asserts anything about their internal format.

## Note on the test harness

`cli.py validate` references a non-existent `test_layout.py`, and
`tests/integration/validate_layout.py` imports a removed `paper_layout` module. Both are
pre-existing and unrelated to identity.
