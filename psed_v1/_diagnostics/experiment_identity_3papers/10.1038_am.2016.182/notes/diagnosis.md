# 10.1038/am.2016.182 — diagnosis

## Phase A/B (PDF ground truth, read before any PSED artifact)
Low-temperature Pt ALD (HDMP + O2, N2 carrier/purge), compared against MeCpPtMe3.
Seven deposition cases (`tables/pdf_deposition_cases.csv`), 17 reported measurements
(`tables/pdf_measurements.csv`).

The decisive caption is **Figure 2(c)**: *"X-ray photoelectron spectroscopy spectra of Pt
films grown by ALD with the HDMP precursor at the temperatures of 100 and 300 °C."*
Those are the same temperatures swept in Fig 2(a) (GPC) and Fig 2(b) (resistivity). The
paper therefore supports one **deposition-condition case per temperature**, characterised
three different ways. It does *not* state that the XPS specimen is literally the same
physical wafer as the GPC specimen, so the strongest defensible level is
`SAME_DEPOSITION_CONDITION_CASE`, not `SAME_PHYSICAL_SPECIMEN`.

Figure 4 (device) is known-missing downstream and was reconstructed from the PDF.

## Phase C (current PSED)
54 Experiments from 16 result entities. Per printed figure/panel:
Fig1a 10 · Fig1b 12 · Fig1h 7 · Fig2a 11 · Fig2b 10 · Fig2c 2 · Fig3e 1 · Fig3f 1.

`physical_case_id` is minted as `<paper>__Fig<N><panel>__exp<NN>`. **Zero** physical case
ids span more than one printed figure.

## Phase D (comparison)
* Splitting a temperature sweep into one Experiment per point is **CORRECT** — the PDF
  supports separate films per temperature.
* Splitting *across measurements of the same case* is **OVER_SPLIT**: the T=100 °C case
  appears as one Experiment in Fig2a, another in Fig2b and another in Fig2c, with three
  different physical_case_ids and no relation between them. The conditions are recorded
  (`deposition_temperature=100/300`), so the information needed to group them exists —
  identity simply is not derived from it.
* Figure 4's five device measurements are **UNLINKED** (absent entirely).

## Answer to the paper-specific question
Yes: the resolver over-splits one Pt deposition-condition case into several Experiments,
one per figure panel. It does so *without* losing the conditions — the grouping key is
figure/panel, not process state.
