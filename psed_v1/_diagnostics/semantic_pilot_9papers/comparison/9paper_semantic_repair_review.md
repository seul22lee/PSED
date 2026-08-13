> **SUPERSEDED.** This document describes a nine-paper set that included
> `cremers2019`, a review paper since removed from the pilot as out of scope.
> It is kept as a historical record. The active-set report is
> [`8paper_semantic_review.md`](8paper_semantic_review.md).

# Nine-paper semantic repair review

Two generic repairs this cycle, all nine papers rerun, 0 API calls, production untouched.

## The two repairs

**1. Condition specificity precedence.** Every condition now records how specific its
source is — specimen table > figure-local > methods default > paper-wide default. When two
sources give different values for the same quantity, the more specific one wins, the other
is kept under `superseded`, and the disagreement is no longer reported as a scientific
contradiction. Equally specific values that disagree still contradict, as they should.

**2. Case-minting evidence threshold.** A result anchors a deposition ExperimentalCase only
on positive deposition identity: a named specimen, an author-defined table row or design
branch, a local synthesis description, or an explicit label. An image, a technique, a
plotted result or an inherited default recipe are not sufficient. Results that fail the
threshold keep their Measurement and ResultSeries; their case link is recorded UNRESOLVED.

Two smaller generic fixes followed from testing these: a covering layer ("the SiO2 was
covered by an Al2O3 film") is now a STACK_COMPONENT rather than a second deposit, and an
image-supported case carries every material role its caption states, not only the deposited
one.

## Counts

| paper | designs | branch obs | unique branches | cases | samples | runs | meas | RS | reps | sims | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `10.1038_am.2016.182` | 6 | 31 | 22 | **25** | 0 | 0 | 19 | 16 | 0 | 2 | 7 |
| `10.1149_2.067203jes` | 10 | 56 | 56 | **57** | 0 | 0 | 41 | 38 | 14 | 0 | 44 |
| `10.1039_c7ta03257a` | 0 | 0 | 0 | **2** | 0 | 0 | 5 | 4 | 2 | 0 | 3 |
| `10.1039_d0cp03358h` | 0 | 0 | 0 | **11** | 16 | 1 | 44 | 70 | 53 | 31 | 20 |
| `cremers2019` | 0 | 0 | 0 | **1** | 0 | 0 | 9 | 93 | 25 | 86 | 8 |
| `10.1039_d0ra09876k` | 6 | 37 | 20 | **47** | 0 | 0 | 33 | 34 | 0 | 1 | 52 |
| `10.1039_c5ta00205b` | 0 | 0 | 0 | **5** | 0 | 0 | 21 | 21 | 0 | 0 | 17 |
| `10.1021_acs.langmuir.6b03119` | 0 | 0 | 0 | **7** | 0 | 0 | 13 | 12 | 2 | 0 | 18 |
| `10.1039_d0ra01602k` | 0 | 0 | 0 | **20** | 0 | 0 | 37 | 36 | 0 | 0 | 25 |

## Case-count changes vs the pre-repair snapshot

| paper | before | after | Δ | semantic reason |
|---|---|---|---|---|
| `10.1038_am.2016.182` | 27 | 25 | -2 | Two figure-shaped cases rested only on inherited defaults with no specimen, branch or local synthesis statement. Preserved as Measurements, case link UNRESOLVED. |
| `10.1149_2.067203jes` | 52 | 57 | +5 | Fig 7's TEM caption is a local synthesis description (7.0 nm ALD SiO2 on Si, capped with Al2O3), which now anchors a case and carries its stack roles; Fig 6's FTIR spectra likewise state film thicknesses. Fig 4 = 40 and Fig 5 = 8 are unchanged. |
| `10.1039_c7ta03257a` | 2 | 2 | +0 | No change. Both cases come from explicit synthesis statements. |
| `10.1039_d0cp03358h` | 14 | 11 | -3 | Sample 11's Fig 5 result now merges into its tabulated 1000-cycle case instead of standing alone (repair 1); Fig 3 (a terminology figure) and Fig 6 (AFM of the default process) no longer mint cases (repair 2). Result: exactly the 11 nominal cases Table 1 defines. |
| `cremers2019` | 1 | 1 | +0 | No change. Its single case comes from an explicit attribution. |
| `10.1039_d0ra09876k` | 100 | 47 | -53 | 53 of the 53 removed cases are the Fig 2 thermogravimetry ramp: a thermal-analysis instrument sweeps its own abscissa, so those points are one substance through a ramp, not 53 depositions. The measurements are preserved. |
| `10.1039_c5ta00205b` | 7 | 5 | -2 | Two electrochemical characterisation results carried only inherited defaults and no deposition identity. |
| `10.1021_acs.langmuir.6b03119` | 12 | 7 | -5 | Five of the twelve figure-shaped cases rested on the paper-wide recipe alone. This is the over-split flagged in the previous review; the threshold removes the unsupported half rather than merging on absent evidence. |
| `10.1039_d0ra01602k` | 20 | 20 | +0 | No change. Its cases come from multi-output panel grouping with recorded evidence. |

## Preservation

| paper | curves old → pilot | points old → pilot | status |
|---|---|---|---|
| `10.1038_am.2016.182` | 16 → 16 | 112 → 112 | ✅ |
| `10.1149_2.067203jes` | 38 → 38 | 624 → 624 | ✅ |
| `10.1039_c7ta03257a` | 4 → 4 | 160 → 160 | ✅ |
| `10.1039_d0cp03358h` | 70 → 70 | 1221 → 1221 | ✅ |
| `cremers2019` | 93 → 93 | 1086 → 1086 | ✅ |
| `10.1039_d0ra09876k` | 34 → 34 | 601 → 601 | ✅ |
| `10.1039_c5ta00205b` | 21 → 21 | 622 → 622 | ✅ |
| `10.1021_acs.langmuir.6b03119` | 12 → 12 | 156 → 156 | ✅ |
| `10.1039_d0ra01602k` | 36 → 36 | 531 → 531 | ✅ |

**100% preserved** — every source curve and every digitised point is preserved on all nine papers.

## Gold anchors held

- **Yim**: 16 samples, 11 nominal cases, BASE = {2,4,5,6,8,12}, Fig 9 = 5, Fig 11 = 5, samples 1 and 3 recovered as table-only cases, Fig 6 mints nothing.
- **JES**: Fig 4 = 40 source branch observations across 8 designs; Fig 5 = 8 unique temperature branches with two outputs each; 46 cross-design merges blocked on material, step or quantity.
- **d0ra09876k**: 0 deposition branches from the Fig 2 thermogravimetry.

## Remaining, not validated

- **am.2016.182** — 25 cases from 16 curves. The source-positive cross-panel identity audit has not been run; the count is provisional.
- **d0ra09876k** — 47 cases, 38 of them Fig 3 design branches. The remaining whole-curve cases are not audited figure by figure.
- **JES Figs 11 and 12** — gold anchors 2 and 7 deposited-structure branches. Those structures are stated as film thicknesses in the legends, which the extraction never surfaces as case-defining conditions, so they resolve UNRESOLVED. The earlier count of 7 matched gold only by minting one case per curve.
- Nothing was migrated to production; nothing was committed.

## Tests

`126 passed, 0 failed` — including all PDF-ground-truth anchors, the 20 structural
invariants, and the new regression tests for condition precedence, the case-minting
threshold, the Yim reconciliation and source preservation.

