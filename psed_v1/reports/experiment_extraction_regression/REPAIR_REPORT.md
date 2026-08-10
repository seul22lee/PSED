# Experiment-extraction repair — implemented and validated

Starting point: the verified diagnosis in `root_causes.md` (R1–R4). All four are
repaired, all 31 papers regenerated, and the output validated against the
semantic contract. Reproduce with:

```
python3 03_corpus/scripts/06_to_kb.py --all --resolve-only
python3 02_extraction/canonical/build_canonical.py --all
python3 02_extraction/build_kg.py
python3 reports/experiment_extraction_regression/validate_repair.py
```

---

## 1. Counts, reported separately

| | count |
|---|---:|
| **source figure series** (figure_data.json) | **659** |
| **resolved result records** (results.json) | **663** |
| orphaned source series | **0** |
| digitised points lost | **0** |
| **physical experimental cases** | **684** |
| continuous experimental runs | 35 |
| **discrete experimental sweeps** | 160 |
| — discrete experimental cases minted | **374** |
| experimental profiles | 70 |
| multi-output measurements | 205 |
| **fits / calculated representations** | **7** |
| simulations | 87 |
| model curves (parameter sweeps) | 26 |
| imported literature data | 10 |
| derived representations | 2 |
| **unresolved series** | **61** |
| material ambiguities (measured series, no material resolvable) | 23 |
| material not applicable (generic model curves) | 62 |
| chemistry inconsistencies | **0** |
| sweeps whose settings remain unresolved | 83 |

663 = 35 + 160 + 70 + 205 + 7 + 87 + 26 + 10 + 2 + 61, asserted per paper by
`test_every_class_is_reported_somewhere`.

663 vs 659: four papers have no digitised figure series at all
(`cnma.201700148`, `s11671-010-9676-0`, `matt.2019.12.026`, `mee.2018.01.033`)
and carry one synthesised entity each. No raw series was lost or duplicated in
any of the 31 papers.

---

## 2. What each repair changed

### §1 Authoritative result surface — `resolved/results.json` (new)

One row per source curve, complete on its own: paper, figure index and printed
number, panel, series id and label, point set, representation, source kind
(measured / calculated / fitted / simulated / imported), entity kind,
experiment / measurement / fit links, material and reactants, provenance, and
the granularity decision with its evidence.

`experiments.json` remains the derived physical-experiment view. The diagnosis
found the result was split across three files and every consumer read only the
first, which is why a 19-curve paper looked like a 4-record paper. Each paper's
`results.json` also carries a `summary` block with the eleven counts above.

### §2/§3 Granularity — the 146 zero-case sweeps, reassessed

New `canonical/entities.py::sweep_setting_cases`. A measured discrete sweep mints
one case per plotted setting when, and only when:

- the x axis is a **process setting** (allow-list; an unclassified axis stays
  `unknown` and mints nothing), **and**
- there is documentary corroboration that the parameter was independently varied
  (a run-structure statement, or a conditions table linked to the figure), **and**
- the plotted settings are few enough to be markers rather than a resampled line
  (≤ 12 distinct values, unless the paper enumerates them).

A prose enumeration is accepted only when it **accounts for the whole curve** —
as many values as the curve has distinct x positions, each matching one.
Intersection is not enough: "at 1–10 Torr" was read as the two settings {1, 10},
and a 16-point growth curve passing through x=1 and x=10 became two experiments.
Ranges (`to`, `-`, `–`) no longer count as enumerations at all.

Outcome — **not** all 146 converted:

| | sweeps |
|---|---:|
| now mint per-setting cases | **68** |
| stay unresolved — x advances within one run (cycles, sputter time) | 42 |
| stay unresolved — x is a measurement coordinate (eV, 2θ, position) | 20 |
| stay unresolved — process axis but no corroboration or too dense | 16 |
| stay unresolved — axis kind unknown | 5 |

The 42 within-run and 20 measurement-coordinate cases are the ones that would
have been *wrong* to convert: a growth curve versus cycles is one run, and an XPS
scan is one specimen. Both are now blocked structurally, before any enumeration
is even consulted.

Verified against sources: `chemmater.2c01154` Fig. 7 now yields 3, 8 and 5 cases
for its three H₂-flow curves, at deposition temperatures of 50/100/150/200/250/
300/350/450 °C — round, deliberately chosen settings, each a separate deposition.

### §4 Series-level source identity — `canonical/series_identity.py` (new)

Measured / calculated / fitted is resolved per **series**, from the caption's own
contrast ("the measured (circles) and calculated (line) …") plus the series
label. A calculated or fitted series inside a `measured` figure:

- is typed `Fit`, not `experimental_profile`;
- mints **no** ExperimentalCase, DepositionRun or Sample;
- links to the measured curve it describes via `fit_of_entity`.

`FIT_LABEL` did not match "Fitting result" — `\bfit(?:ted)?\b` does not match
*fitting*. That single word boundary is how two fits reached the experiment
surface; it is now covered by a test.

### §5 Chemistry — `canonical/chemistry_scope.py` (new)

`material = mats[0]` is gone. The ladder, narrowest first:

1. series legend that is one of this paper's materials
2. **this panel's own caption clause**
3. the figure caption — skipped when the figure varies material by panel
4. the scout's per-figure note
5. figure-linked body text
6. single-material paper
7. otherwise **None**, with candidates and reason recorded

`"<material> from <precursor> and <coreactant>"` is parsed and outranks every
paper-level default. Material, precursor and co-reactant are resolved together
and checked for consistency.

The consistency checker initially reported 47 contradictions; all 47 were
spelling — `tris(...)erbium(III)` and `tert-butylferrocene` carry their metal as
a word, not a symbol. It now recognises element names. **0 inconsistencies
remain.**

Sub-stoichiometric spellings are unified: a film listed as `WS2` and written
`WSx` is one material, not two.

The four known caption conflicts:

| paper | fig | caption | before | now |
|---|---|---|---|---|
| `10.1063_1.5028178` | 7 | TiO2 from TiCl4 | Al2O3 / TMA | **TiO2 / TiCl4** ✅ |
| `10.1021_acs.chemmater.2c01154` | 9 | (a) WSx, (b) TiSx | MoS2 | **WS2 / TiS2 per panel** ✅ |
| `10.3762_bjnano.5.25` | 6 | TiO2 coated VACNTs | Al2O3 | **TiO2** ✅ |
| `10.1116_1.4938104` | 5 | W | Al2O3 | **not a series conflict** — that figure is SEM images with no digitised curve, so nothing was ever assigned. The paper's other figures went from 6 materials collapsed to Al2O3, to Al2O3 / TiO2 / ZnO resolved per figure. |

All nine multi-material papers were re-validated per figure;
`caption_material_conflict` is **0** corpus-wide.

Where evidence is genuinely absent the material is `None` with its candidates
retained — 23 measured series, plus 62 generic model curves for which no film
material applies at all (a simulation of reactant A in a channel is not an Al2O3
simulation because Al2O3 sorted first).

### Additional: model parameters scoped to their material

The repair surfaced a related defect. `geometry.json` holds one row per material:

```
Al 2 O 3 | 500 | 500 | 147  | 0.00572 | 219
TiO 2    | 1000| 500 | 25.7 | 0.1     | 0.252
```

Both were attached at **paper** scope, so every Al2O3 experiment was offered
TiO2's sticking probability and adsorption constant as equally valid candidates.
Each row's evidence names its own material, so the split is now deterministic.

---

## 3. The Ylilammi fixture — 19/19 preserved

`canonical/tests/fixtures/10.1063_1.5028178_series.json` records, per curve:
printed figure and extraction index, panel, label, source kind, entity kind,
granularity, case identity, measured/fit/model relationship, material,
precursor, co-reactant, cycle count, coordinate, and the exact caption or body
sentence supporting the decision.

| | |
|---|---:|
| source curves preserved | **19 / 19** |
| points lost | 0 |
| physical experimental cases | **2** |
| fits | 2 |
| model / simulation curves | 15 |

- **Fig. 7 measured**: TiO2, TiCl4, H2O, `cycle_number = 1000`, one
  `ExperimentalProfile`, 1 case.
- **Fig. 7 fitting line**: `Fit`, 0 cases, `fit_of` → the measured profile, same
  TiO2 chemistry context, no DepositionRun and no Sample.
- **Fig. 6**: identical shape with its own chemistry — Al2O3, TMA, 500 cycles.

The count 2 is **not** hard-coded: `test_case_count_is_derived_not_hard_coded`
sums the 19 per-series decisions and compares that to the live output.

---

## 4. Tests

`canonical/tests/test_extraction_coverage.py` — 38 new tests. Canonical suite is
now **172/172** (134 pre-existing + 38 new).

| contract requirement | test |
|---|---|
| raw-series coverage / orphan detection | `test_every_raw_series_has_a_result_record`, `test_no_orphaned_source_series`, `test_no_points_are_lost_corpus_wide` |
| source-series → entity traceability | `test_entities_and_results_agree`, `test_result_ids_are_unique` |
| genuine discrete sweep case generation | `test_genuine_sweeps_now_produce_cases`, `test_setting_axis_classification`, `test_enumeration_must_match_the_plotted_values`, `test_dense_process_axis_stays_unresolved` |
| measured-vs-fit separation | `test_calculated_label_beats_the_figure_flag`, `test_fitting_spelling_is_caught` |
| no DepositionRun minted by a fit | `test_fits_are_not_experiments`, `test_no_deposition_run_is_minted_by_a_fit` |
| multi-material caption precedence | `test_caption_material_outranks_paper_default`, `test_panel_clause_outranks_figure_caption`, `test_panel_figure_does_not_inherit_another_panels_material` |
| no first-item fallback | `test_no_first_item_fallback`, `test_resolver_refuses_rather_than_guessing` |
| material/precursor/coreactant consistency | `test_material_precursor_consistency`, `test_consistency_check_accepts_named_precursors` |
| figure-specific curve-vs-point granularity | `test_within_run_axes_never_become_cases`, `test_measurement_coordinates_never_become_cases`, plus the 19-series fixture |
| consumer visibility of every series | `test_results_view_is_self_sufficient`, `test_every_class_is_reported_somewhere` |

### Three pre-existing tests were amended, none weakened

1. **`test_live_and_comparison`** hard-coded the old status list
   (`enumerated_in_source` / `unresolved_settings`). Updated for the contract
   change §3 requires. Its `assertNotEqual(case_count, n_observations)` proxy was
   **replaced by the stronger direct invariant** — the count must equal the
   distinct plotted settings, on a process-setting axis, with named evidence.
   The proxy had become wrong: a saturation curve measured at 7 ozone exposures
   legitimately has 7 settings *and* 7 points.

2. **`test_stage0_regression::test_simulations_and_literature_are_out_of_the_experiment_count`**
   asserted flatly that no Stage-0 non-experiment may become an experiment. It
   now applies the same justification rule its sibling test already used
   (corroborated rebuilt evidence where Stage 0 had none). The one entity
   affected is `d0cp03358h` Fig. 3b, where Stage 0 read the whole caption, saw
   "simulated" — which describes panel *a* — and typed panel *b* as a simulation.
   The figure's own `panel_source` is `{'a': 'simulated', 'b': 'measured'}` and
   the caption calls panel (b) "the experimental scaled saturation profile
   (experimental data for Al2O3 ALD)". **Stage 0 was wrong; the repair is right.**
   Every uncorroborated flip still fails.

3. The `experimental_profile` gate now counts series-level source identity as an
   independent signal family, which is what makes that d0cp reclassification
   corroborated rather than a single signal.

---

## 5. Acceptance — §7 criteria

`validate_repair.py`, all 31 papers:

| criterion | result |
|---|---|
| all raw source series have traceable records | **PASS** (659/659, 0 orphaned) |
| no points lost | **PASS** |
| no many-to-one merge without shared-identity evidence | **PASS** |
| fits mint no physical experiment | **PASS** |
| fits mint no DepositionRun/Sample | **PASS** |
| model curves remain visible with their points | **PASS** |
| digitisation density never becomes experiments | **PASS** |
| no first-item chemistry fallback | **PASS** |
| material/precursor consistency | **PASS** (0 inconsistencies) |
| no caption/material conflicts | **PASS** (0) |
| unknown chemistry explicit, never guessed | **PASS** |
| unresolved granularity states its reason | **PASS** |
| conditions attached to correctly materialised entities | **PASS** |

## 6. Condition binding after the entity repair (§8)

Bindings were **recomputed** against the corrected entities and revalidated for
both condition correctness and target-entity correctness.

| | |
|---|---:|
| condition rows tracked | 2,517 |
| bound | 1,964 |
| withheld as ambiguous | 553 |
| bound and inherited by an experimental case | **1,161 / 1,161** |
| visible in the KG | **1,964 / 1,964** |
| conditions attached to fits (preserved, not experiments) | 14 |

Precision, re-drawn after regeneration — two independent stratified samples of
n=150 over 2,028 bound assertions, seeds 20260804 and 771103:
**150/150 and 150/150 correct, 0 errors.**

Target-entity correctness: `condition_on_mismaterialised_entity` = **0**. No
condition is attached to an entity whose material came from a non-evidence rung.

D0CP, SSE and PSSA regressions all pass within the canonical suite, and the
19-series Ylilammi fixture is now part of it.

---

## 6b. Second round — 10.1021_acs.jpcc.9b08176

Checked against the PDF (Arts et al., *J. Phys. Chem. C* 2019, 123, 27030). Ground
truth from the paper: **8 depositions** — SiO2 at plasma exposures of 3.8, 12, 38
and 120 s; TiO2 at 12 and 120 s; Al2O3 at 120 s; HfO2 at 120 s. Figure 1 is pure
modelling (9 curves); Figure 3 re-plots Figure 2's data.

The paper produced **0 experiments**. Four further defects, all now fixed:

| # | defect | evidence | fix |
|---|---|---|---|
| 1 | **no gate for a process-condition x axis** | Fig. 2 (penetration depth vs plasma exposure time) produced *zero* signals and classified `unknown`. The two structural gates covered a curve measured across ONE SPECIMEN (spatial, spectral); nothing covered a curve measured across SETTINGS. | new `process_setting_axis_gate`; fires 127× corpus-wide |
| 2 | **a single-point series was not a run** | Al2O3 and HfO2 appear as one point each; requiring ≥2 points silently dropped two real depositions | one point on a process axis is one run at one setting |
| 3 | **re-plotted data would double-count** | Fig. 3 is "…as presented in **Figure 2**", the same 6 depositions against ln(t). Counting both gives 14 for a paper that ran 8. | `REPLOT` → `derived_representation`, 0 cases, corroborated by resolving the cross-reference against the paper's own figure list |
| 4 | **element-hint table left SiO2 and HfO2 with no precursor** | `chemistry_propagation` matches a hand-curated substring table; `HfCp(N(CH3)2)3` / `TDMACpH` match nothing, and Si matched two un-canonicalised aliases so read as ambiguous | parse the methods' explicit mapping — "the precursors used were … **for the growth of** SiO2, TiO2, Al2O3, and HfO2, **respectively**" — which outranks element matching |

Result: **8 cases, 9 model curves, 2 derived representations, 4 materials each
with its stated precursor** (BDEAS, TDMAT, TMA, TDMACpH), matching the paper.

### The guard that matters

The process-setting gate initially reclassified 15 curves that Stage 0 called
`continuous_trace`. Checking the captions showed Stage 0 was **right** for some
of them: `10.1002_pssa.201532305` Fig. 4 is "Film growth (obtained by **in-situ
SE**) versus different deposition parameters" — one continuously monitored
exposure per curve, not a sweep — and `10.1002_celc.201600139` Fig. 3b is
impedance "versus storage time". The gate is now suppressed whenever a
continuous modality (in-situ, QCM, real-time, impedance) or a continuous
run-structure statement is present, and it requires a real run-structure
sentence rather than the near-universal `measured` flag.

It still fires where the source says separate runs: pssa Fig. 6 ("CVD growth
rate versus **process pressure**", 3 pressures = 3 runs) and c7ra07722j Fig. 2
("**saturation curves** … self-limiting growth").

### Known extraction gap, not a resolution defect

Figure 2**b** of this paper contains 8 measured thickness profiles. The vision
extraction captured only the z̃50% summary values annotated in panel **a**
(330/570/730/870 for SiO2, 450/780 TiO2, 80 Al2O3, 40 HfO2). Those values are
correct and give the right 8 depositions, but the profile curves themselves were
never digitised. Recovering them needs re-extraction, which is out of scope
here; it is recorded so the missing curves are not mistaken for a resolution
error.

---

## 7. One unresolved downstream consequence — needs your decision

`04_twin_mpc/test_m2_design.py` has **5 failures** and I have deliberately not
touched them, because the correct fix is a scientific decision rather than a
code change.

The twin can no longer design a 60 µm penetration depth for Al2O3; its
achievable range is now 0.77–15.37 µm and the reference case reads
`infeasible_high`.

The cause is confirmed, not inferred. In the committed baseline:

```
git show HEAD:.../10.1063_1.5028178/resolved/experiments.json
  -> 19 rows, every one material=Al2O3
  -> sticking_probability candidates {0.00572, 0.1}, context_status: None
```

`0.1` is **TiO2's** sticking coefficient, from the `TiO 2 | 1000 | 500 | 25.7 |
0.1 | 0.252` row of the paper's own table. It was being used as Al2O3 kinetics
purely because of the `mats[0]` bug, and the twin's 60 µm feasibility depended
on it. With the chemistry corrected, Al2O3 keeps `c = 0.00572, K = 219` and TiO2
keeps `c = 0.1, K = 0.252`.

So those five expectations encode the bug's consequences. Three options:

- **(a)** Re-baseline the twin's expected feasible envelope against correct Al2O3
  kinetics — my recommendation, but it is your call what the twin should claim.
- **(b)** Let the twin consume ambiguous-material curves via
  `material_candidates`, which the repair records precisely for this purpose.
  This widens the pool again but marks the attribution as uncertain.
- **(c)** Decide the 15 Ylilammi model curves *are* Al2O3. The paper's model uses
  M_A = 0.0749 kg/mol, close to TMA's 72.09 g/mol — but the captions never say
  so, and inferring a film from a molar mass is the kind of guess the contract
  forbids, so I did not do it.

Everything else passes: canonical **172/172**, and 12 of the 13 repo suites
(`test_report_freshness` passes after regenerating M2 and M3).
