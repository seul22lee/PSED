# 10.1149/2.067203jes — diagnosis

## Phase A/B (PDF ground truth)
Plasma ALD of SiO2 (SAM.24 + O2 plasma) on HF-cleaned Si(100), Tdep 50–400 °C. Six cases
(`tables/pdf_deposition_cases.csv`), 12 measurements (`tables/pdf_measurements.csv`).

Three facts matter:
1. **Al2O3 is independently deposited** — *"To allow for direct comparison, Al2O3 was
   synthesized in the same reactor using Al(CH3)3 as the metal precursor and O2 plasma as
   the oxidant"* — and is also used as an ultrathin capping layer.
2. **A genuine HAR case exists** — *"high conformality (95–100%) for trenches with aspect
   ratios of ~30"*, *"The SiO2 film was deposited using 830 cycles."*
3. **Figs 11–12 measure two different material contexts** — single-layer SiO2 *and*
   SiO2/Al2O3 stacks.

## Phase C (current PSED)
32 Experiments, 38 entities, all `material=SiO2`, all `geometry_class=planar`.
Fig4 contributes 8 Experiments (one per panel); Fig11b contributes 9.

## Phase D (comparison)
* **OVER_SPLIT**: the single saturation study of Fig 4 becomes 8 Experiments, one per
  printed panel, although the PDF presents them as one self-limiting characterisation.
* **OVER_MERGED (material)**: Al2O3 has no Experiment at all, and stack measurements are
  labelled SiO2. A paper-level single-material assignment cannot express
  "SiO2 film", "Al2O3 capping" and "SiO2/Al2O3 stack" as distinct contexts.
* **OVER_MERGED (geometry)**: the paper contains both planar process development and an
  HAR trench case, yet carries one paper-level `geometry_class=planar`. The HAR case is
  the one experiment a conformality model would want, and it is invisible.
* Fig 1 (precursor vapour pressure) is correctly **NOT_A_DEPOSITION_EXPERIMENT** in
  substance, though PSED does mint Experiments for it.

## Answer to the paper-specific questions
1. Yes — distinct material contexts are over-merged.
2. Yes — measurements of one saturation study are over-split by panel.
3. Geometry belongs at the Experiment (or deposition-case) level; this paper is a
   counter-example to paper-level geometry.
4. No — the planar/HAR distinction is not preserved anywhere.
