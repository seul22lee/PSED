# PDF ground-truth review — the five unseen generalization papers

Each paper was read from its original PDF after the semantic output was generated, not
before. No expected case count was written down in advance.

---

## `cremers2019` — Cremers, Puurunen & Dendooven, *Appl. Phys. Rev.* **6**, 021302 (2019)

### What the PDF says

"Conformality in atomic layer deposition: Current status overview of analysis and
modelling", **44 pages**. The paper states its own nature outright: *"In this work, we aim
to **review** the current status of knowledge about the conformality of ALD processes."*
"review" occurs 102 times. It carries **19 explicit reproduction statements** —
"Reproduced / Adapted / Reprinted with permission from …, Copyright …" — one on nearly
every data figure. Fig 9 is Elam's ZnO-in-AAO data; Fig 18 is Knoops's Monte-Carlo
simulation. **The paper performs no depositions of its own.**

### What the pilot produced, and what changed

| | before the fix | after |
|---|---|---|
| ExperimentalCases | 6 (4 with **zero** case-defining conditions) | **1** |
| Measurements | 9 | 9 |
| ResultSeries | 93 | 93 |
| SimulationRuns | 86 | 86 |

The first run minted six deposition cases for a review article — five of them attributed to
HfO2 purely because a reproduced figure mentioned it. That is a genuine semantic failure,
and it is the single most valuable finding of this generalization test.

**Generic correction made** (`pilot_evidence.imported_from`): a figure whose caption
attributes its data to another work is an **imported observation**. Its ResultSeries are
preserved in full with both attributions kept, and it mints no current-paper case. Two
forms are recognised: the journal's copyright line, and a narrative attribution whose
source looks like a work (surname + "et al." or a year) rather than an instrument.

### Verdict, dimension by dimension

- **Correct merges:** none needed; none made.
- **Correct splits:** the 86 model entities stay entirely out of the case layer.
- **Incorrect residue:** the one surviving case comes from printed Fig 11, whose caption
  describes a TMA/H2O process on two test structures **without** an attribution line
  (the attribution is carried by superscript reference markers 67 and 86 that the caption
  text does not spell out). Under "explicit evidence only" the pilot keeps it. The
  scientifically ideal answer for this paper is **0 cases**; the pilot reaches 1.
- **Geometry — a genuine success.** This paper's `geometry.json` has **no class at all**,
  yet the pilot reads `porous_material` and `lateral_channel` from individual figure
  captions. Case-level geometry generalised to a paper with no paper-level geometry.
- **A preserved upstream inconsistency:** 9 of the 86 model entities carry a curve
  `data_source` that is not `simulated` — three empty, six `measured`, including a panel
  where the series labelled "Simulation" and the series labelled "Experiment" are both
  marked `measured`. The pilot preserves `data_source` bit-identically and flags the
  disagreement rather than overriding either side. Recorded in
  `logs/incidental_findings.md`.

**PASS** on measurement separation, sample, run, representation, condition roles, geometry.
**PARTIAL** on case identity, material roles, characterisation provenance, simulation
provenance.

---

## `10.1039_d0ra09876k` — ALD of dielectric Y2O3 from a yttrium formamidinate

### What the PDF says

10 pages. A single-material process-development paper: Y2O3 from Y(DPfAMD)3 + water.
The PDF states a saturation study at **Ts = 300 °C** with "5 s of precursor pulse and 10 s
precursor purge", and an ALD window explored across deposition temperatures. Printed Fig 3
is a four-panel process study: (a) GPC vs temperature, (b) thickness vs number of cycles
including a linear fit, (c) GPC vs precursor pulse length, and purge.

### What the pilot produced

50 cases (same as PSED's 50), 33 Measurements, 34 ResultSeries, 6 `Fit` entities, 32
unresolved links.

- **41 of the 50 cases come from 7 genuine independent process sweeps**, and each now
  carries its own discriminator — `deposition_temperature = 100 / 125 / 150 °C`, pulse and
  purge times — instead of `case00 / case01 / case02`. This is the sweep-normalisation
  requirement working on a paper it was never tuned against.
- **All 6 `Fit` entities are preserved as Measurements and none mints a case.** Dimension O
  generalises.
- Reactant-specific pulse times stay separate by species: a case carries
  `pulse_time = 10 s` and `pulse_time = 30 s (H2O)` without conflict.
- 12 characterisation measurements (XPS, XRD, AFM, capacitance) are correctly left
  `CASE_UNRESOLVED` — the paper does not say which deposition each characterised film came
  from.

**Correct merges:** none claimed, none needed. **Incorrect merges:** none.
**Over-splits:** the 50 cases are not reduced relative to PSED, but the paper genuinely
runs 7 separate parameter sweeps, so a large case count is the right answer here.
**Verdict: PASS**, with geometry PARTIAL (planar from the paper default throughout).

---

## `10.1039_c5ta00205b` — nanoporous Pt by ALD, Assaud *et al.*

### What the PDF says

9 pages. Pt deposited by ALD onto nanoporous anodic-oxide supports. The paper's own
case-defining variable is stated explicitly: *"the … is adjusted by varying the number of
'**micropulses**' within the half-cycle from **1 to 8**"*. Electrochemical
characterisation (cyclic voltammetry, turnover) follows on the resulting electrodes.

### What the pilot produced

**20 PSED Experiments → 7 ExperimentalCases.** 21 Measurements, 21 ResultSeries,
15 unresolved links.

- The micropulse sweep is recognised as a genuine case-defining process variable.
- **Pt is asserted as DEPOSITED and the porous support is not read as a co-deposit** —
  the support-role machinery generalises from `c7ta03257a`'s silica template to this
  paper's anodic oxide.
- `porous_material` geometry, with **2 of the 7 cases taking it from their own figure
  caption** rather than the paper default.
- **10 electrochemical measurements are left `CASE_UNRESOLVED`.** This is correct: the PDF
  does not state which Pt deposition each measured electrode came from. It is the same
  situation as `c7ta03257a` Fig 7, and the pilot behaves the same way — which is the point.

**Correct splits:** 20 → 7 removes panel-level over-splitting without merging anything the
source does not link. **Incorrect merges:** none.
**Verdict: PASS**, characterisation provenance PARTIAL by the source's own silence.

---

## `10.1021_acs.langmuir.6b03119` — Al2O3 ALD into TiO2 nanotube layers, Zazpe *et al.*

### What the PDF says

8 pages. *"The ALD process consisted of **200 cycles at a deposition temperature of
200 °C**, with TMA and H2O as precursors in alternating pulses."* One nominal process, with
TMA exposure varied between 10 s and 0.5 s. In-situ QCM measures the mass increment per
cycle; Fig 3 reports Al2O3 thickness against tube depth and diameter.

### What the pilot produced

12 cases (same as PSED's 12), 12 Measurements, 12 ResultSeries, 2 representations,
12 unresolved links — all `CONDITION_ONLY_NO_POSITIVE_LINK`.

- **This is the clearest remaining over-split in the nine.** The PDF describes essentially
  **two** process variants (10 s and 0.5 s TMA exposure); the pilot reports 12 cases,
  one per drawn curve.
- The reason is visible in the output and is the intended behaviour, not a silent failure:
  all 12 unresolved links are of the class `CONDITION_ONLY_NO_POSITIVE_LINK` — the
  case-defining conditions agree, but no caption or body sentence states that two curves
  are the same film, the same sample or the same run. Under "missing ≠ same" the pilot
  declines to merge and says so.
- **Correct behaviour elsewhere:** Al2O3 is DEPOSITED; the TiO2 nanotube layer is *not*
  read as a co-deposited material; TMA and H2O pulse times are kept apart by species.
- **Geometry PARTIAL:** the whole paper is about high-aspect-ratio nanotubes, yet every
  case reports `planar` from the paper-level default. No figure caption states a geometry
  in the vocabulary the pilot recognises. This is the geometry gap in its clearest form.
- **Dimension T not exercised.** This paper was selected to cover imported literature and
  turns out to have **zero** `ImportedLiteratureObservation` entities — a scoring error
  documented in `selection/selected_5.md`. (Imported literature was nonetheless exercised,
  by `cremers2019`, which nobody selected it for.)

**Verdict: PARTIAL** — case identity over-split by the source's silence; everything else PASS.

---

## `10.1039_d0ra01602k` — room-temperature SiO2 ALD, Arl *et al.*

### What the PDF says

9 pages. SiO2 grown by a pure ALD route **at room temperature**, with a growth rate near
2 Å per cycle. Heavy XPS characterisation across many panels.

### What the pilot produced

**53 PSED Experiments → 20 ExperimentalCases.** 37 Measurements, 36 ResultSeries,
25 unresolved links.

- **The multi-output grouping is the headline result.** This paper has 27
  `MultiOutputMeasurement` entities — nine times Yim's three. Several elemental channels of
  one XPS panel are one measurement on one specimen, and the pilot collapses them
  correctly at that scale: 53 → 20.
- **18 cases carry `planar` from the paper default; 2 carry `porous_material` read from
  their own figure caption** — geometry locality working again on an unseen paper.
- SiO2 is asserted on all 20 cases from local evidence.
- 17 of the 25 unresolved links are `SOURCE_TRULY_UNSPECIFIED` — measurements whose
  producing deposition the paper never identifies.

**Correct splits:** 53 → 20. **Incorrect merges:** none. **Verdict: PASS.**

---

## Summary across the five

| | cremers2019 | d0ra09876k | c5ta00205b | langmuir | d0ra01602k |
|---|---|---|---|---|---|
| PSED Experiments → pilot Cases | 6 → **1** | 50 → 50 | 20 → **7** | 12 → 12 | 53 → **20** |
| unsupported merges | 0 | 0 | 0 | 0 | 0 |
| obvious remaining over-split | — | — | — | **yes (12 → ~2)** | — |
| fits kept out of cases | 1/1 | 6/6 | — | — | — |
| imported literature routed | **19 statements** | — | — | — | — |
| geometry from a figure caption | **2 classes** | — | 2 cases | — | 2 cases |
| verdict | PARTIAL | PASS | PASS | PARTIAL | PASS |

**Unsupported merges across all five: zero.** Every merge in the nine-paper run (15 total)
carries a recorded evidence id, and 4 merges were blocked on contradictory conditions.

**One generic correction was made during this review** — imported-literature routing — and
per Part XXXIX all nine papers and all 85 tests were rerun afterwards. The four controls
reproduce their frozen baseline exactly.
