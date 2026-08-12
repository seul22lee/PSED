# Second-pass scientific review — four papers, ten semantic dimensions

Verdicts are against the ORIGINAL PDFs, not against the test suite. A dimension is PASS
only when the pilot output matches what the paper says; PARTIAL and FAIL carry the exact
remaining reason.

Legend: **PASS** correct · **PARTIAL** correct but incomplete · **FAIL** wrong.

| dimension | `am.2016.182` | `2.067203jes` | `c7ta03257a` | Yim 2020 |
|---|---|---|---|---|
| ExperimentalCase identity | PARTIAL | PASS | PASS | PASS |
| Measurement separation | PASS | PASS | PASS | PASS |
| Sample identity | PARTIAL | PARTIAL | PARTIAL | PASS |
| Run identity | PARTIAL | PARTIAL | PARTIAL | PASS |
| Representation handling | PASS | PASS | PASS | PASS |
| Condition roles | PASS | PASS | PASS | PASS |
| Material roles | PASS | PASS | PASS | PASS |
| Geometry | PARTIAL | PASS | PARTIAL | PASS |
| Characterisation provenance | PARTIAL | PASS | PASS | PASS |
| Simulation provenance | PASS | PASS | PASS | PASS |

---

## `10.1038_am.2016.182` — Pt ALD on textile fibres

- **ExperimentalCase identity — PARTIAL.** The intended join is achieved: Fig 2a GPC,
  Fig 2b resistivity and Fig 2c XPS combine into Pt/HDMP cases at 100 °C and at 300 °C,
  and two merges are blocked because the precursor contradicts (HDMP vs MeCpPtMe3).
  **Remaining reason:** 50 cases for 16 curves. Most of the paper's sweeps carry no
  cross-figure linkage statement, so each swept setting stays its own case. That is the
  correct behaviour under "missing ≠ same", but the paper almost certainly reports fewer
  distinct depositions than 50.
- **Sample identity — PARTIAL.** 0 Samples. **Remaining reason:** the paper names no
  specimen anywhere — no sample table, no sample codes in captions. Nothing to bind.
- **Run identity — PARTIAL.** 0 runs, 0 run-evidence groups. **Remaining reason:** the
  paper makes no run statement of any kind.
- **Geometry — PARTIAL.** All cases are `planar` from the paper-level default.
  **Remaining reason:** the fibre/textile substrate is described in prose but no figure
  scope states a geometry the pilot's vocabulary recognises, so the default stands. It is
  labelled `paper-level default`, so the reader can see it was not observed.
- **Characterisation provenance — PARTIAL.** Printed Figure 4's five device panels
  (capacitive response, load response, 10 000-cycle stability, array mapping) are recovered
  as caption-only Measurements with `data_recovered: false`, and correctly mint **no**
  deposition case. **Remaining reason:** the PDF connects the sensor to "the Pt ALD
  conductive fibers" but names no deposition temperature, so the device results are not
  attached to a specific case. Forcing that link would be a guess.
- **Condition roles, Representation, Simulation — PASS.** No measurement setting reaches a
  case; the 2 SimulationRun entities stay simulated with `data_source` unchanged.

## `10.1149_2.067203jes` — ALD SiO2, planar and high-aspect-ratio

- **ExperimentalCase identity — PASS.** 23 cases. Printed Fig 1 no longer mints any: it
  plots the vapour pressure of the SAM.24 precursor, a property of a chemical, and the
  pilot now records it as a Measurement + ResultSeries with no case and no material role.
- **Material roles — PASS.** The Fig 1 leakage is gone — a purpose clause ("this precursor
  is commonly used for ALD of Al2O3") is no longer read as a deposition. The SiO2/Al2O3
  stack cases of printed Fig 12 carry both constituents as `STACK_COMPONENT`; the Fig 8
  underlayer is typed `SUBSTRATE`, not a second deposit. No case asserts a DEPOSITED role
  while its deposited material is null.
- **Geometry — PASS.** Planar and HAR now coexist: printed Figure 8 yields a case with
  `vertical_structure` taken **from the figure caption**, carrying aspect ratio ~30,
  830 ALD cycles, trench depth 18.5 µm and width 0.6 µm — all read from the caption, with
  no x-y points claimed. 22 other cases remain `planar` and are labelled `paper-level
  default`.
- **Condition roles — PASS.** The `(10-120 ms)` precursor dose is carried as the interval
  10–120 ms with `value_kind: range` and the misread `-120` retained as
  `superseded_value`; the `10-40 cycles` stack caption likewise. No unphysical negative
  survives anywhere in the paper.
- **Sample / Run identity — PARTIAL.** 0 of each. **Remaining reason:** the paper tabulates
  RBS/ERD results but names no specimen codes and makes no run statement.
- **Characterisation provenance — PASS.** Every result is preserved; nothing is discarded
  for lacking a case.

## `10.1039_c7ta03257a` — Pt ALD replicas of a silica template

- **ExperimentalCase identity — PASS.** Two cases, both from prose with no x-y process
  curve, now named by what they create: **"full replica"** (precursor exposure repeated 3×
  per O3 exposure, 250 cycles) and **"micron-long mesoporous Pt tubes"** (one precursor
  pulse per cycle, 250 cycles).
- **Characterisation provenance — PASS.** The chain the PDF states is now represented:
  *tubular Pt replica → dispersed → deposited on the test electrodes → impedance / CV*.
  Printed Fig 8's coated impedance and Fig 8(b) CV carry `PROVENANCE_CHAIN` provenance to
  the tubular case. The bare/uncoated series are typed `REFERENCE` and are attached to no
  case. Printed Fig 7's coated HER result stays **UNRESOLVED**, because its section says
  only "the replica" and never says which protocol — the chain is shown stopping there.
- **Measurement separation — PASS.** CV and impedance remain Measurements; neither is an
  ExperimentalCase.
- **Sample / Run identity — PARTIAL.** No Sample object is created for the coated
  electrode. **Remaining reason:** the pilot links the measurement to the case directly
  through the chain; an intermediate device object would be new machinery, and §21 asks for
  the smallest representation that works. The chain record carries the device name
  ("test electrodes") explicitly.
- **Geometry — PARTIAL.** `porous_material` at paper level. **Remaining reason:** no figure
  scope states a geometry for the individual cases.
- **Fig 8(b)** is represented with `recovery_cause: panel_absent_from_crop` and a locally
  rendered PDF page as evidence; no points are claimed.

## Yim 2020 `10.1039_d0cp03358h` — the semantic control

- **ExperimentalCase identity — PASS.** 18 cases from 39 PSED Experiments.
- **Sample identity — PASS.** All 16 specimens recovered from the paper's own Table 1,
  with their tabulated conditions. Specimen 11 carries several Measurements; specimens 8
  and 12 each belong to two study series.
- **Run identity — PASS.** Exactly **one identified DepositionRun**, holding specimens
  1/2/3 ("All of the films were grown in the same ALD run", Series A). The two
  reproducibility statements are now **run-evidence groups**, not runs — the earlier
  "3 runs" was one run and two assertions counted together.
- **Series semantics — PASS.** All six series take their variable from the author's own
  Table 1 footnote: A pillar layout, B reflectometer magnification, C channel height,
  D ALD cycles, **E TMA pulse time**, **F purge time**. Series E additionally retains its
  pillar-layout co-variation as `co_varying_context` without losing its declared variable.
- **Fig 7 specimen mapping — PASS.** X50 → specimen 4, X10 → specimen 5, X5 → specimen 6,
  by **value join** against Table 1's magnification column, not by list order. Each
  measurement carries its magnification as a `MEASUREMENT_SETTING` plus the spot size the
  methods give for it (5–6 µm, 25 µm, 50 µm). The three curves yield **one** deposition
  case.
- **Representation handling — PASS.** Fig 9's 18 panels remain 18 representations and 6
  cases; the 12 scaled/normalized panels link to their as-measured sibling.
- **Fig 8a / 8b — PASS.** 8a's repeat measurements stay one case; 8b's distinct-run
  evidence is preserved without fabricating run identities.
- **Simulation provenance — PASS.** Fig 10's 31 SimulationRuns are untouched; 39 measured
  / 31 simulated, identical to PSED.

---

## Cross-cutting preservation (all four papers)

| check | result |
|---|---|
| source curve ids preserved | 16/16, 38/38, 4/4, 70/70 |
| digitised points preserved | 112, 624, 160, 1221 — identical |
| measured/simulated provenance | bit-identical to PSED |
| merges without evidence | 0 |
| Samples / Runs without evidence | 0 |
| unphysical negative conditions | 0 |
| DOI or figure branch in `code/` | 0 |

## What the verdicts are NOT based on

The test suite passes 85/85, and that is not why any dimension above is marked PASS. Every
PASS was checked against the PDF text quoted in `logs/second_pass_diagnosis.md`; the tests
exist to keep those readings from regressing.
