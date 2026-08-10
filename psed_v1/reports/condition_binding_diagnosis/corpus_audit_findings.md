# Corpus audit findings — 31 papers, 2457 records

> **SUPERSEDED IN PART.** Ten corrections were applied after review; the entity
> classifications, confidence intervals, pressure-loss rate and baseline attribution
> in this file are revised in `corrections_and_qualifications.md`, which takes
> precedence. The population counts and targeted-set counts here remain valid.

Frozen at git `e67378503bae` (working tree dirty:
True, 375 modified paths).
Random seed **20260803**, sample **n = 120**, papers
represented **31/31**.

## Population

| | |
|---|--:|
| papers | 31 |
| experiment-like records | 2457 |
| series | 173 |
| curves | 659 |
| model-labelled records | 335 |
| experimental-labelled records | 2122 |
| unresolved records | 267 |

Population kinds: {'series_member_experiment': 1967, 'correlation_record': 24, 'unresolved_experiment_record': 267, 'profile_experiment': 188, 'paper_level_record': 4, 'single_experiment': 7}

## Headline estimates (random sample only)

| question | answer |
|---|---|
| supported as a physical experiment | **9.2% (11/120, CI 5.2–15.7%)** |
| NOT a physical experiment | **62.5% (75/120, CI 53.6–70.7%)** |
| uncertain (needs the paper) | 28.3% (34/120, CI 21.0–37.0%) |
| one digitised point of a single curve | **40.8% (49/120, CI 32.5–49.8%)** |
| model / simulation | 15.0% (18/120, CI 9.7–22.5%) |
| derived / duplicate representation | 6.7% (8/120, CI 3.4–12.6%) |
| ≥1 source-supported condition missing | 31.7% (38/120, CI 24.0–40.5%) |
| ≥1 over-broadcast condition attached | 32.5% (39/120, CI 24.8–41.3%) |
| affected by point-level splitting | 66.7% (80/120, CI 57.8–74.5%) |
| pressure available but lost | 26.7% (32/120, CI 19.6–35.2%) |
| deterministically repairable from existing evidence | **64.2% (77/120, CI 55.3–72.2%)** |
| needs image/PDF review | 10.0% (12/120, CI 5.8–16.7%) |
| needs re-digitisation | **0.0% (0/120, CI 0.0–3.1%)** |

Only **11 of 120**
sampled records are defensible as separately conducted physical experiments.

## Why the count grew from 663 to 2457

| driver | records | share of the +1794 |
|---|--:|--:|
| point-level splitting of condition-axis curves | +1967 created, 173 curves consumed | ~100 % of the growth |
| of which: continuous in-situ / kinetic traces wrongly split | dominant (36.7 % of the random sample) | — |
| of which: genuine parameter sweeps, correctly split | minority but real | — |

The increase is **almost entirely** point-level splitting. Verified: 173 curves were
replaced by 1967 point records; no other mechanism adds records. The split is
justified only where each point is a separately prepared sample; the random sample
puts that at a minority of cases.

## Root-cause frequency (random sample)

| code | cause | n | share | 95 % CI |
|---|---|--:|--:|---|
| P | Curve point incorrectly promoted to Experiment | 44 | 36.7% | 28.6–45.6% |
| — | no failure detected | 31 | 25.8% | 18.8–34.3% |
| S | Model or simulation data stored as Experiment | 17 | 14.2% | 9.0–21.5% |
| I | Hidden or replaced by fallback / dedup | 9 | 7.5% | 4.0–13.6% |
| C | Wrong quantity classification / axis role unresolved | 8 | 6.7% | 3.4–12.6% |
| J | Incorrect paper-level broadcast | 5 | 4.2% | 1.8–9.4% |
| A | Mention not extracted | 4 | 3.3% | 1.3–8.3% |
| H | Field dropped downstream | 2 | 1.7% | 0.5–5.9% |

## Targeted diagnostic set (separate from the estimates above)

4454 cases:

| case type | n |
|---|--:|
| pressure_in_source_not_in_output | 1680 |
| conflicting_context | 852 |
| legend_condition_without_structured_binding | 603 |
| empty_conditions_despite_numeric_caption | 471 |
| figure_geometry_broadcast_across_figures | 465 |
| model_point_became_experiment | 335 |
| largest_series | 20 |
| largest_experiment_growth | 10 |
| granularity.mixed_roles | 9 |
| granularity.profile_split | 9 |

**Full-paper audit triggered for 24 / 31 papers.**

## Random sample vs targeted set

The random sample measures *how often* each failure occurs; the targeted set shows
*how bad the worst instances are*. They agree on the ranking (splitting > model
records > pressure/scope) and disagree on magnitude: the targeted set is dominated by
`pressure_in_source_not_in_output` (1680 record-level hits) because a single missing
`pressure.json` propagates to every record in that paper — which is exactly why the
random sample, not the targeted set, must drive the repair priority.

## Pressure

16 / 31 papers (52 %) end with **zero** usable pressure on any record.
13 / 31 have a pressure in `document.md` and an empty `pressure.json`
(first loss: `10_pressure.py`, a pilot that was never run corpus-wide).
3 / 31 have entries in `pressure.json` that never reach a record
(first loss: `_dedup_pressures` + paper-scope ambiguity).

## Confidence and limits

* Entity verdicts are rule-based with a quoted caption span each; **34/120 remain
  `uncertain`** and are flagged `manual_review_required`. Treat the 9.2 % "physical
  experiment" figure as a **lower bound** — some uncertain records are genuine sweeps.
* `source_pdf_page` is not recoverable: docling output carries no page index. Layer-1
  verification used `document.md` + captions + figure images, not PDF pages.
* The case-matrix "present" verdict uses a ±5 % / ×10ⁿ value match, so a broadcast
  value that coincidentally matches an expected one can read as "present". Two SSE
  geometry rows are affected; both are broadcast, not correctly scoped.

