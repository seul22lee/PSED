# Semantic pilot — active set review (8 experimental papers)

Generated from the existing `papers/*/semantic/` outputs. The semantic pipeline was NOT
rerun for this document and no resolver behaviour changed.

## Active set

| paper | role |
|---|---|
| `10.1038_am.2016.182` | original_control |
| `10.1149_2.067203jes` | original_control |
| `10.1039_c7ta03257a` | original_control |
| `10.1039_d0cp03358h` | original_control |
| `10.1039_d0ra09876k` | development_validation |
| `10.1039_c5ta00205b` | development_validation |
| `10.1021_acs.langmuir.6b03119` | development_validation |
| `10.1039_d0ra01602k` | development_validation |

**`cremers2019` has been removed from the pilot entirely.** It is a review paper: its
figures reproduce other groups' work, so its plotted data is predominantly model output
and imported observations rather than experiments the paper performed, which makes it
unfit for experimental validation. Its previously generated files remain on disk under
`papers/cremers2019/` but are not loaded, counted, displayed, tested or profiled by this
workflow. Earlier documents in `comparison/` that describe a nine-paper set are
historical records of superseded passes.

## Counts

| paper | designs | unique DesignBranches | branch appearances | cases | samples | runs | meas | RS | reps | sims | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `10.1038_am.2016.182` | 3 | 19 | 31 | **25** | 0 | 0 | 19 | 16 | 0 | 2 | 7 |
| `10.1149_2.067203jes` | 9 | 48 | 56 | **57** | 0 | 0 | 41 | 38 | 14 | 0 | 19 |
| `10.1039_c7ta03257a` | 0 | 0 | 0 | **2** | 0 | 0 | 5 | 4 | 2 | 0 | 3 |
| `10.1039_d0cp03358h` | 6 | 18 | 18 | **11** | 16 | 1 | 44 | 70 | 53 | 31 | 20 |
| `10.1039_d0ra09876k` | 3 | 20 | 37 | **47** | 0 | 0 | 33 | 34 | 0 | 1 | 17 |
| `10.1039_c5ta00205b` | 0 | 0 | 0 | **5** | 0 | 0 | 21 | 21 | 0 | 0 | 16 |
| `10.1021_acs.langmuir.6b03119` | 0 | 0 | 0 | **7** | 0 | 0 | 13 | 12 | 2 | 0 | 6 |
| `10.1039_d0ra01602k` | 0 | 0 | 0 | **20** | 0 | 0 | 37 | 36 | 0 | 0 | 17 |
| **total** | 21 | 105 | 142 | **174** | 16 | 1 | 213 | 231 | 71 | 34 | 105 |

## Source preservation

| paper | curves old → pilot | points old → pilot | status |
|---|---|---|---|
| `10.1038_am.2016.182` | 16 → 16 | 112 → 112 | ✅ |
| `10.1149_2.067203jes` | 38 → 38 | 624 → 624 | ✅ |
| `10.1039_c7ta03257a` | 4 → 4 | 160 → 160 | ✅ |
| `10.1039_d0cp03358h` | 70 → 70 | 1221 → 1221 | ✅ |
| `10.1039_d0ra09876k` | 34 → 34 | 601 → 601 | ✅ |
| `10.1039_c5ta00205b` | 21 → 21 | 622 → 622 | ✅ |
| `10.1021_acs.langmuir.6b03119` | 12 → 12 | 156 → 156 | ✅ |
| `10.1039_d0ra01602k` | 36 → 36 | 531 → 531 | ✅ |

**100% of curves and points preserved** across the active set.

## Tests

`8 papers: 262 passed, 0 failed` — PDF-ground-truth anchors, structural invariants
S1–S15, condition-precedence and case-threshold regressions, and preservation checks.

## Runtime

| set | seconds |
|---|---|
| **Active set, 8 papers** | **58.5** |

Measured once by `code/profile_pilot.py`. The earlier 458.2 s figure covered a
nine-paper set that included the now-excluded review paper and does not describe this
workflow. See `comparison/performance_profile.md`.

## Provisional, not validated

- **`10.1038_am.2016.182`** — 25 cases from 16 curves; the source-positive cross-panel identity audit has not been run.
- **`10.1039_d0ra09876k`** — 20 unique DesignBranches and 37 branch appearances; its non-branch case objects are not audited figure by figure.
- **`10.1149_2.067203jes` Figs 11 and 12** — the PDF anchors 2 and 7 deposited-structure branches, but those thicknesses are not extracted as case-defining conditions, so they resolve UNRESOLVED.
- Cases marked `INDISTINGUISHABLE_FROM_SIBLING` share every represented case-defining dimension and are flagged rather than merged or split.

