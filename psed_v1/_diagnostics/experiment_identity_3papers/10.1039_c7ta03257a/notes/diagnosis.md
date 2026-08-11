# 10.1039/c7ta03257a — diagnosis

## Phase A/B (PDF ground truth)
Pt ALD (MeCpPtMe3 + O3, static exposure, 30 s per half-cycle) into a Zeotile-4 mesoporous
silica template, followed by HF digestion to leave a 3-D Pt replica.

**Two distinct deposition-condition cases are stated explicitly:**
* CASE_A — *"For the creation of the full replica (Fig. 3), the MeCpPtMe3 precursor
  exposure was repeated 3 times for one O3 exposure during each ALD cycle."*
* CASE_B — *"For the creation of the micron-long mesoporous Pt tubes (Fig. 6), only one
  precursor pulse was applied."*
* Both: *"In both cases, 250 ALD cycles were applied."*

The electrode is then built from that material: *"An amount of 15 µg of Pt replica powder
was deposited from suspension by micropipetting on each 1.9 mm² electrode."* Fig 7 (CV),
Fig 8a (impedance) and Fig 8b (CV, missing from extraction) measure that electrode.

## Phase C (current PSED)
0 Experiments. 4 entities, all `UnresolvedSourceEntity`, all `physical_case_id=None`,
reasons `"conflicting signals"` and `"only one signal family (continuous_trace)"`.

## Phase D (comparison)
* **0 deposition Experiments is defensible for the CV/impedance curves**: neither axis is
  an ALD process variable, so under the current process-condition ↔ outcome rule they are
  correctly not deposition Experiments (`NOT_A_DEPOSITION_EXPERIMENT`).
* **But the paper does establish the link** the data lacks. CASE_A/CASE_B are fully
  specified (precursor, co-reactant, exposure scheme, 250 cycles, template), and the
  electrode is explicitly made from that replica powder. So the missing connection is a
  representational gap, not an evidential one — `UNLINKED`.
* Two clearly distinct ALD condition cases produce **no** Experiment at all, because their
  evidence is imaging-only (Figs 3, 5, 6). Experiment minting is driven by digitisable
  x-y results, so a fully-specified deposition with only micrographs is invisible.

## Answer to the paper-specific questions
1. Yes, 0 Experiment is reasonable **for those curves**.
2. Yes, they are correctly not separate deposition Experiments.
3. Yes — the PDF traces them to CASE_A (and the replica it produced).
4. Missing: any node/relation expressing "this measurement characterises material produced
   by that deposition case".
5. No, the absence is not unavoidable — the paper supplies the link.
