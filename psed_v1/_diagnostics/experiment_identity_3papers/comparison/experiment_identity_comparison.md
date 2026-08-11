# Experiment identity / physical sample audit — three papers

Read-only. **0 API calls.** PDF ground truth was reconstructed before any PSED artifact
was opened (Phases A→B→C→D, in that order).

| paper | strongest PDF identity level | PDF cases | PSED Experiments | same-case multi-measurement | correct | over-split | over-merged | unlinked | sample identity represented | current Experiment semantics | conf |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.1038/am.2016.182 | condition case | 7 | 54 | yes | 23 | 24 | 0 | 5 | **no** | result-curve + conditions | HIGH |
| 10.1149/2.067203jes | condition case | 6 | 32 | yes | 5 | 14 | 9 | 1 | **no** | result-curve + conditions | HIGH |
| 10.1039/c7ta03257a | condition case | 3 | 0 | yes | 0 | 0 | 0 | 4 | **no** | (none minted) | HIGH |

## What `Experiment` empirically means

**C/D hybrid: an extracted result curve, or one point of a sweep inside it, plus inferred
conditions.** It is *not* a physical deposition run, and only accidentally a condition case.

The mechanism is visible in the identifier itself:
`physical_case_id = shares_physical_case_with or entity_id`, and `entity_id` is
`<paper>__Fig<N><panel>__exp<NN>`. Identity is therefore **figure/panel-derived**.
Corpus-wide, `shares_physical_case_with` is set for 66 of 1044 entities and only ever
within a single multi-channel measurement event — **0 physical case ids span two printed
figures** in either paper that has them.

## Ten concrete mappings

1. `am.2016.182` CASE_C at 100 °C → GPC (Fig2a) + resistivity (Fig2b) + XPS (Fig2c).
   PSED: three Experiments, three physical_case_ids. **OVER_SPLIT.**
2. `am.2016.182` temperature series 100…300 °C → 11 Experiments in Fig2a. **CORRECT.**
3. `am.2016.182` CASE_G device (Fig4 b,c,d,e,g) → none. **UNLINKED** (Figure 4 absent).
4. `2.067203jes` one saturation study (Fig4 a–h) → 8 Experiments, one per panel. **OVER_SPLIT.**
5. `2.067203jes` Fig11 mixes SiO2-only and SiO2/Al2O3 → 9 Experiments, all `material=SiO2`. **OVER_MERGED.**
6. `2.067203jes` Al2O3 deposited in the same reactor → no Al2O3 Experiment. **OVER_MERGED.**
7. `2.067203jes` HAR trench AR≈30, 830 cycles → paper-level `geometry_class=planar`. **OVER_MERGED.**
8. `c7ta03257a` 250 cycles, 3× vs 1× precursor pulse → 0 Experiments. **UNLINKED.**
9. `c7ta03257a` Fig7 CV + Fig8a impedance → 4 `UnresolvedSourceEntity`, `physical_case_id=None`.
   **NOT_A_DEPOSITION_EXPERIMENT** *and* **UNLINKED**.
10. `am.2016.182` Fig2c Experiments do carry `deposition_temperature=100/300` — the grouping
    information exists; identity just is not derived from it. **OVER_SPLIT.**

## Direct answers

1. **What is `Experiment`?** A result curve (or sweep point) plus inferred conditions.
2. **One physical deposition run?** No. Nothing in the data models a run.
3. **A deposition-condition case?** Closer, and correct *within* a sweep, but broken across figures.
4. **Multiple measurements on one film under one Experiment?** **No** — they become separate Experiments.
5. **Same-case measurements over-split?** Yes: 24/54 and 14/32.
6. **Distinct cases over-merged?** Yes, in `2.067203jes` — by material and by geometry.
7. **Sweeps physically meaningful?** Largely yes; per-point Experiments match separately prepared films.
8. **Characterisation linked to its deposition?** No.
9. **Usable sample identity?** No. `physical_case_id` is figure-panel scoped.
10. **Recoverable identity level?** Condition case reliably; run/batch occasionally; specimen rarely.
11. **Is `Experiment = one sample-producing deposition run/case` supported?** The *case* half is
    supported by all three PDFs; the *run* half generally is not recoverable. Current PSED
    implements neither.
12. **Gaps:** no sample/run node; no "characterises material produced by" relation; paper-level
    material; paper-level geometry; Experiment minting requires a digitisable x-y result, so
    imaging-only depositions vanish entirely.

## Scope
Diagnosis only. No repair proposed or implemented.
