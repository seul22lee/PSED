# Entity model — what a generated record means

Every generated entity must correspond to a scientifically defensible unit supported
by the source paper. This document is the contract; `02_extraction/canonical/entities.py`
implements it and `canonical/tests/test_stage0_regression.py` enforces it.

## The rule that drives everything

> **A drawn curve is evidence, not an experiment. Its digitised points are
> observations. A point becomes an experimental case only when the paper says that
> setting was separately performed.**

The digitiser reads ~50 points along a curve regardless of how many depositions the
authors made (`05_figure_extract.py::VISION_SCHEMA`). Any count derived from point
density is therefore a count of pixels, not of experiments.

## Classes

| class | meaning | cases it yields |
|---|---|--:|
| `continuous_trace` | one run monitored continuously (in-situ SE/QCM, kinetics, depth profile) | 1 |
| `experimental_profile` | one specimen sampled along a spatial coordinate | 1 |
| `multi_output_measurement` | one specimen, several observable channels (elements, peak components) | 1 |
| `discrete_experimental_sweep` | separately prepared settings → an `ExperimentalSeries` | only settings the paper enumerates |
| `simulation` | a `SimulationRun` | 0 |
| `model_sweep` | a `ModelSweep`; its points are `ModelPrediction`s | 0 |
| `imported_literature_data` | re-plotted from a cited work; keeps `reported_in` AND `originally_reported_in` | 0 |
| `fit` | a fitted/derived line linked to its inputs | 0 |
| `derived_representation` | scaled / normalized / inset redraw of another entity | 0 |
| `unknown` | evidence insufficient — preserved whole, never split, never promoted | 0 |

## How a class is decided

Two **independent signal families** must agree, except where one family is
definitional (an explicit `Model`/author-year label, a `simulated` source flag, a
spatial-coordinate x axis).

`M` caption/body modality · `Me` methods modality · `R` explicit run-structure
statement · `I` sample/run identifier · `L` series-label semantics · `F` extraction
source flag · `T` table linkage · `X` axis/series-axis structure.

Point count, curve smoothness and axis type are stored in `weak_signals_not_used_alone`
and never vote.

Two gates run before the vote:

1. **Provenance gate** — a simulated or cited curve can never be reclassified as an
   experimental sweep because its x axis happens to be swept.
2. **Coordinate-axis gate** — a spatial-coordinate x axis means the curve is one
   specimen's profile. Membership of a swept family is a *between-curve* fact and is
   recorded in `between_curve_condition`, not as a competing class.

## Sweeps and the setting count

A sweep's cases are minted only from an **enumerated** list of prepared samples
(`samples 12, 13 and 14`). Loose prose enumerations are rejected — during the audit
they matched unrelated values. When nothing enumerates the settings:

```json
"experimental_case_count": 0,
"experimental_case_status": "unresolved_settings",
"experimental_case_lower_bound": 2,
"observation_count_unresolved_as_cases": 17
```

Marker spacing was tested as an alternative source of evidence and **rejected**: the
coefficient of variation of Δx cannot separate evenly-spaced real settings from an
evenly-resampled line (a genuine 6-temperature sweep and a 41-point interpolated
curve both score 0.00).

## Condition assertions

An **assertion** is "the paper says X, with this status, over this scope". A
**binding** is "this entity is covered by that scope". They are separate acts.

Scopes, narrowest first: `series → panel → figure → method → paper`. Conflicting
candidates at the winning scope are returned as `ambiguous_conditions` and bound to
nothing — never resolved by list order.

Three assertion sources beyond captions and legends:

* **methods** — paper-scope process conditions;
* **reference-scoped** — adopted/estimated inputs stated per *cited work*
  ("For Ylilammi et al. [9] … we estimate p_A = 325 mTorr"). These sit nowhere near a
  "Fig. N" mention, so proximity cannot find them; the governing scope is the
  reference name, which the figure's series labels carry.
* **Mathematical-Italic folding** — docling writes `p_A` as `U+1D45D U+1D434`. Without
  folding `U+1D400–U+1D7FF` to ASCII the symbolic pressures are invisible.

## Pressure

`working_pressure`, `precursor_partial_pressure`, `co_reactant_partial_pressure`,
`carrier_gas_partial_pressure`, `base_pressure`, `bubbler_pressure` and
`generic_pressure` are distinct quantities. A **dose product** (`mTorr*s`) is
`exposure`, never a pressure.

`assertion_status` ∈ direct | approximate | estimated | assumed | fitted | derived.
`evidence_kind` ∈ experimental_condition | model_input | literature_condition, so an
estimated model input is never presented as a measured condition.

Species come from the **symbol definition** (`p_A0 = 65 Pa (A = TMA)` → TMA) or the
sentence — never from the nearest numeric token.

## Outputs per paper

```
02_extraction/output/{doi}/resolved/
  entities.json     every source entity: class, evidence, observations, bound conditions
  experiments.json  ONLY current-paper experimental cases
  series.json       ExperimentalSeries with supported/lower-bound case counts
  assertions.json   every ConditionAssertion with scope, status and evidence
  counts.json       differentiated counts (never one "experiment count")
```

## Reading the counts

Never quote a single experiment number. Report the differentiated block, and where a
paper does not enumerate its settings report the supported count **and** the
lower bound. See `reports/entity_model/count_reconciliation.md`.
