# Five unseen generalization papers — selection and rationale

Selected from the 40 live corpus papers that are not already in the four-paper pilot.
Scores in `candidate_matrix.csv`; every number there is computed from local artifacts.

---

## The binding constraint: PDF availability

Part XX requires a PDF ground-truth review of each selected paper. **Only 10 of the 40
candidates have a local PDF**; the other 30 exist in the corpus only as Docling output.

Reviewing a paper against its own `document.md` would be circular — that artifact is
precisely the thing whose failures this pilot exists to detect, and three of the four
original papers had a defect in it. So the pool was restricted to the 10 papers whose PDF
is present.

This is a real narrowing and is recorded as scope escalation E1. It is not a retreat to
easy papers: the pool still contains the corpus's largest simulation paper, its
fit-richest paper, and two of its three non-planar-geometry papers.

**Candidate pool actually available for selection (10):**
`cremers2019`, `10.1039_c7ra13417g`, `10.1039_d0ra09876k`, `10.1039_c5ta00205b`,
`10.1021_acs.langmuir.6b03119`, `10.1039_c4nr05049e`, `10.1039_d0ra01602k`,
`10.1039_c3ra42928h`, `10.1039_c3ta01665j`, `10.1063_1.2338776`.

---

## What the original four already cover

| dim | | covered by |
|---|---|---|
| A | cross-figure same-case | am.2016.182 (Fig 2a/2b/2c) |
| B | conditions from methods, not captions | c7ta03257a |
| C | multiple deposited materials | 2.067203jes (2) |
| D | substrate / support / template / stack | 2.067203jes, c7ta03257a |
| E,F | multiple geometries, planar + HAR | 2.067203jes |
| G | sweeps with explicit x values | am.2016.182 |
| H | measurement-setting variation | Yim Series B |
| I,J | sample codes, repeated nominal runs | Yim |
| K,L | characterisation, device data | c7ta03257a, am Fig 4 |
| M | raw / scaled / normalized | Yim Fig 9 |
| N | experiment + simulation | Yim Fig 10 |
| P | text/image-supported cases | c7ta03257a, 2.067203jes Fig 8 |
| Q | multi-output from one sample | Yim sample 11 |
| R,S | ambiguous linkage, author series | c7ta03257a, Yim |
| **O** | **fits / calculated representations** | **not covered** |
| **T** | **imported literature mixed with original data** | **not covered** |

The selection deliberately closes O and T, and re-tests the covered dimensions on papers
whose structure differs from the paper that first exercised them.

---

## 1. `cremers2019` — simulation-dominant, three materials, fits

**Live shape.** 6 Experiments but **93 entities**: 71 `ModelSweep`, 15 `SimulationRun`,
6 `ExperimentalProfile`, 1 `Fit`. 3 materials (Al2O3, HfO2, SiO2). 8 non-primary
representations. 9 printed figures. Sample and run textual signals both present. 257
aspect-ratio/HAR mentions. `geometry.json` has **no class at all**.

**Why selected.** The inverse of every paper studied so far: Yim's simulation was a clean
minority (31 of 70); here model output is **92 %** of the entities and the experiment is
the minority. If the simulation boundary holds anywhere it must hold here.

**Failure modes it stresses.** N (experiment/simulation separation under simulation
dominance), O (fits), C (three deposited materials in one paper), M (representation
variants), I/J (sample and run signals), E (a paper with no geometry class).

**What could fail.** A model sweep leaking into `ExperimentalCase`; three materials
producing cross-material merges; the missing geometry class producing a `None` default the
report cannot label honestly.

## 2. `10.1039_d0ra09876k` — fit-richest paper in the corpus

**Live shape.** 50 Experiments from 34 entities. **6 `Fit` entities** (the most of any
corpus paper), 8 `UnresolvedSourceEntity`, 9 `MultiOutputMeasurement`, 7 independent
sweeps, 1 simulation entity, 10 device mentions. Y2O3, planar.

**Why selected.** Closes dimension **O**. A `Fit` is a calculated curve drawn over a
measured one; it must attach to the measurement it describes and must never mint a
deposition case. No paper in the original four has more than a token number of them.

**Failure modes it stresses.** O (fits), K (characterisation-only), Q (multi-output),
G (7 sweeps needing per-case values), R (8 unresolved entities), L (device data).

**What could fail.** A fit becoming its own case; the 50-from-34 ratio revealing sweep
over-splitting; the 8 unresolved entities losing their material context.

## 3. `10.1039_c5ta00205b` — characterisation-heavy Pt on a porous support

**Live shape.** 20 Experiments, 21 entities of which **9 are `UnresolvedSourceEntity`**,
4 `MultiOutputMeasurement`, 3 sweeps, 11 device mentions, 9 printed figures.
`geometry_class = porous_material`. Pt deposited on a porous anodic oxide (TiO2) support.

**Why selected.** The closest structural parallel to `c7ta03257a` — Pt on a porous
template — but with 20 experiments instead of zero. It tests whether the provenance-chain
and support-role machinery generalises to a paper where the deposition IS plotted.

**Failure modes it stresses.** K (post-deposition characterisation), D (support vs
deposited material role), E (non-planar geometry), L (device/electrochemical data),
R (nearly half its entities unresolved today).

**What could fail.** The TiO2 support being typed DEPOSITED; the characterisation results
either losing their case link or acquiring one they do not deserve.

## 4. `10.1021_acs.langmuir.6b03119` — imported literature mixed with original data

**Live shape.** 12 Experiments, 12 entities, **2 `ImportedLiteratureObservation`**,
2 non-primary representations, 5 device mentions, 2 printed figures. Al2O3 deposited into
TiO2 nanotube layers.

**Why selected.** Chosen to close dimension **T** — and that intention turned out to be
based on a scoring error, corrected here rather than hidden.

> **Correction, made after selection was frozen.** The `imported_literature` column of
> `candidate_matrix.csv` sums `ImportedLiteratureObservation` ENTITIES and the count of
> "taken from / adapted from / from the literature" TEXT mentions. This paper's score of 2
> is entirely text mentions: it has **zero** imported-literature entities. The only corpus
> paper that has any is `10.1016_j.sse.2022.108584` (10 of them), and that paper has **no
> local PDF**, so it could not be selected under the PDF constraint above.
>
> **Dimension T is therefore NOT covered by this nine-paper pilot.** The selection was not
> changed, because Part IV freezes it and because swapping a paper after seeing its output
> is exactly the bias this pilot is meant to avoid. The gap is carried into
> `9paper_generalization_review.md` as an untested dimension.

The paper remains a useful selection for its other properties: 12 Experiments from 12
entities with QCM in-situ mass data, 2 non-primary representations, and Al2O3 deposited
into a TiO2 nanotube layer.

**Failure modes it stresses.** D (template/support role), M (representations),
C (Al2O3 into a TiO2 structure), Q.

**What could fail.** The TiO2 nanotube layer being read as a co-deposited material; the QCM
mass-per-area curves being read as deposition sweeps.

## 5. `10.1039_d0ra01602k` — multi-output at scale, largest over-split risk

**Live shape.** 53 Experiments from 36 entities — **27 of them
`MultiOutputMeasurement`**, the second-highest count in the corpus. 3 sweeps, 7 printed
figures, SiO2, planar.

**Why selected.** The over-splitting stress test. 27 multi-output measurements means 27
panels whose several channels are one measurement on one specimen; Yim exercised this with
3. If the multi-output grouping generalises, it must hold at this scale.

**Failure modes it stresses.** Q (multi-output from one sample, at 9× Yim's scale),
G (sweeps), A (7 figures likely measuring shared conditions).

**What could fail.** Each channel of each panel minting its own case (53 from 36 already
suggests expansion); measurement channels being read as separate depositions.

---

## Why this set beats "the five with the most curves"

The five largest candidates by curve count are `cremers2019` (93),
`10.1021_acs.chemmater.2c01154` (51), `10.1039_c6dt03571j` (46),
`10.1021_acs.chemmater.2c02292` (44) and `10.1039_d3ra05217f` (41). Four of those five have
**no local PDF**, so four of five could not be ground-truth reviewed at all — the review
would reduce to checking the pilot against the same Docling text the pilot consumes.

Beyond that, size and semantic diversity are different axes. The two `chemmater` papers are
structurally similar sweep-heavy papers; taking both would spend two of five slots on one
pattern. The selected set instead spans:

| | cremers2019 | d0ra09876k | c5ta00205b | langmuir.6b03119 | d0ra01602k |
|---|---|---|---|---|---|
| simulation-dominant | ● | | | | |
| fits | ● | ●● | | | |
| imported literature | | | | ● | |
| characterisation-only | | ● | ●● | | |
| multi-output at scale | | ● | | | ●● |
| non-planar geometry | | | ● | | |
| support / template role | | | ● | ● | |
| ≥3 deposited materials | ● | | | | |
| device / performance data | ● | ● | ● | ● | |
| representation variants | ● | | | ● | |
| imported literature | | | | ✗ (scoring error) | |
| sweeps needing per-case values | | ● | ● | | ● |

Every one of the 20 stress dimensions is exercised by at least one of the nine papers, and
the two dimensions the original four missed entirely — fits and imported literature — are
now covered twice and once respectively.

## Frozen

These five are frozen as of this document. Per Part IV they will not be swapped out if one
turns out to be difficult; difficulty is the point of the exercise.
