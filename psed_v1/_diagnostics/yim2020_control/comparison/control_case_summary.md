# Yim 2020 control-case summary

Yim et al., *"Saturation profile based conformality analysis for atomic layer deposition:
aluminum oxide in lateral high-aspect-ratio channels"*, PCCP 2020, 22, 23107-23120,
DOI 10.1039/d0cp03358h. **0 API calls.** The paper is already corpus member
`papers/10.1039_d0cp03358h`, so current PSED behaviour was **observed**, not predicted.

## Observed PSED state (read-only)
39 Experiments · 70 entities (36 ExperimentalProfile, 31 SimulationRun, 3 MultiOutputMeasurement)
· **0 series** · 37 distinct `physical_case_id`, **0 spanning more than one printed figure**
· 39 measured / 31 simulated records · geometry `lateral_channel` · material `Al2O3`.

## Control table
See `semantic_entities.csv`. Summary of verdicts:

| case | ground truth | observed PSED | verdict |
|---|---|---|---|
| Series A (1,2,3) | 1 run, 3 samples, 1 recipe | 3 Experiments, no run link | RUN_IDENTITY_LOSS |
| Series B (4,5,6) | measurement condition varied | Fig 7a -> 3 Experiments | **WRONG_LEVEL** |
| Sample 11 | 1 specimen, 3+ techniques | Fig 5b -> 3 Experiments | OVER_SPLIT / SAMPLE_IDENTITY_LOSS |
| Sample 8 | member of Series C *and* D | separate figure-local entities | SERIES_MEMBERSHIP_LOSS |
| Sample 12 | member of Series E *and* F | separate figure-local entities | SERIES_MEMBERSHIP_LOSS |
| Fig 8a | repeated measurement, one sample | 4 Experiments | SAMPLE_IDENTITY_LOSS |
| Fig 8b | different runs, one nominal case | 4 Experiments | RUN_IDENTITY_LOSS |
| Fig 9 a-c | 3 measurements x 3 representations | 9 Experiments | **DUPLICATE_REPRESENTATION** |
| Fig 9 d-f | 3 measurements x 3 representations | 9 Experiments | **DUPLICATE_REPRESENTATION** |
| Fig 10 | simulation | 31 SimulationRun, labelled simulated | **CORRECT** |
| Fig 11a | 3 TMA-pulse cases | 3 Experiments | CORRECT |
| Fig 11b | 3 purge cases | 3 Experiments | CORRECT |

## Which object should "Experiment" be?
* **A. exact physical sample** - succeeds for sample 11 and Fig 8a; fails Series B (three
  sample codes differing only in how they were measured) and cannot express Series A's
  shared run.
* **B. deposition run** - succeeds for Series A's control; fails immediately, because one
  run holds three scientifically different samples (x50% 140 vs 110 um).
* **C. deposition-condition case** - succeeds for Series C/D/E/F and Fig 11, and correctly
  merges Fig 8b's replicate runs; needs sample/run as separate provenance for Series A,
  and needs geometry in the case key for Series A/C.
* **D. measurement** - fails: multiplies sample 11 into 3-4 units and cannot express that
  Fig 8a repeats one measurement.
* **E. result curve** - fails hardest: triples Fig 9 and is what PSED does today.

**Best fit: C, deposition-condition case, with DepositionRun and Sample as separate,
evidence-dependent provenance.**

## Final semantic test
Proposed definition - *Experiment = one scientifically distinguishable deposition-condition
case, which may have multiple Measurements/Results, with DepositionRun and Sample as
separate optional provenance* - is **SUPPORTED_WITH_LIMITATIONS**.

Supported by: Series C, D, E, F; Fig 11; Fig 8b; sample 11; Fig 9.
Limitations: (i) geometry (pillar layout, channel height) must be part of the case key or
Series A and C collapse; (ii) measurement conditions must be excluded from the case key or
Series B creates false cases; (iii) "optional" understates it - where the paper states run
or specimen identity, discarding it loses real published evidence.

## Are Sample and DepositionRun optional or fundamental?
**C - semantically distinct and necessary whenever evidence exists.** Not required for
every Experiment (most papers never state them), but not mere metadata either: in this
paper they carry the experimental control itself. Series A's entire validity rests on
"same ALD run", and Fig 8a/8b is *only* interpretable through the sample/run distinction.
