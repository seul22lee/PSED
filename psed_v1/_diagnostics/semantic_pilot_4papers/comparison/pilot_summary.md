# Four-paper semantic pilot — summary

Sandboxed test of the revised PSED experimental semantics. Production untouched, 0 API
calls, 0 pipeline stages re-run. Counts below are diagnostic; the change classes are the
result.

## Per paper

| | `am.2016.182` | `2.067203jes` | `c7ta03257a` | Yim 2020 `d0cp03358h` |
|---|---|---|---|---|
| **current PSED** Experiments | 54 | 32 | 0 | 39 |
| current entities / canonical curves | 16 / 16 | 38 / 38 | 4 / 4 | 70 / 70 |
| **pilot ExperimentalCases** | 50 | 23 | **2** | **18** |
| Measurements (of which caption/image-only) | 19 | 40 | 5 | 44 |
| ResultSeries | 16 | 38 | 4 | 70 |
| PlotRepresentations | 0 | 11 | 2 | 53 |
| Samples | 0 | 0 | 0 | **16** |
| **identified DepositionRuns** | 0 | 0 | 0 | **1** |
| run-evidence groups (NOT runs) | 0 | 0 | 0 | **2** |
| StudySeries | 0 | 0 | 0 | **6** |
| SimulationRuns | 2 | 0 | 0 | **31** |
| provenance chains | 0 | 2 | **1** | 0 |
| merges / blocked merges | 4 / **2** | 3 / 2 | 0 / 0 | 8 / 0 |
| unresolved links | 15 | 14 | 3 | 62 |

`c7ta03257a` gains its first two experimental cases — PSED currently reports none for it.
Yim's 39 Experiments become 18 cases with 16 specimens, **one identified deposition run**
(plus 2 run-distinctness assertions counted separately) and 6 author-declared series.

> Counts changed in the second pass because several were wrong, not because the rules were
> loosened. See `second_pass_scientific_review.md` and `logs/second_pass_changes.md`.

## The fifteen questions

**1. Did the new semantics work on all four papers?** Yes, after the second-pass
corrections. All four build end to end and **85 of 85** checks pass — 20 generic
invariants plus 65 PDF-ground-truth anchors. The second pass replaced every paper anchor
with one read from the original PDF; see `second_pass_scientific_review.md` for the
verdict per paper and dimension, which is NOT derived from the test count.

**2. Which same-case cross-figure links were recovered?**

- `am.2016.182` — GPC (Fig 2a), resistivity (Fig 2b) and XPS (Fig 2c) join into two
  deposition cases, Pt/HDMP at 100 °C and at 300 °C. Evidence: Fig 2c's caption enumerates
  "the temperatures of 100 and 300 °C", which the 2a/2b sweeps also report. Strength
  SUPPORTED.
- Yim — Fig 3 and Fig 5 join on specimen 11; Fig 7's three curves join because their study
  series varies only the reflectometer objective; Fig 8a's five repeat measurements stay one
  case; Fig 9's 18 panels collapse to the 6 measurements behind them.

**3. Which links remained unresolved, and why?** 94, now classified by reason
(`comparison/unresolved_links_second_pass.csv`):

| reason class | n | resolvable from the source? |
|---|---|---|
| CONDITION_ONLY_NO_POSITIVE_LINK | 54 | no — by design |
| PROVENANCE_CHAIN_INCOMPLETE | 30 | no — the source names no protocol |
| SOURCE_TRULY_UNSPECIFIED | 6 | no |
| MEASUREMENT_ONLY_FIGURE | 2 | no — reports no deposition |
| REFERENCE_BY_DESIGN | 2 | no — a control, never attributed |

None is of a class the source could resolve: the two classes the second pass targeted —
value-joinable specimen links and available provenance chains — are now **zero**, because
both were resolved. `CONDITION_ONLY_NO_POSITIVE_LINK` remains and should.

**4. Were any unsupported merges produced?** No. Every one of the 11 merges carries a
recorded evidence id (invariant: `every_merge_has_evidence.without_evidence = 0` for all
four papers). No merge rests on unknown-on-one-side alone.

**5. Were clearly identical cases still over-split?** Yes, in `am.2016.182` (50 cases for
16 curves) and `2.067203jes` (23), because most of their sweeps carry no cross-figure
linkage statement. That is correct under "missing ≠ same" but it is not the number of
depositions those papers performed.

**6. Did measurement settings incorrectly create cases anywhere?** No. Invariant 4 holds:
no `MEASUREMENT_SETTING` appears among any case's case-defining conditions. Yim's Series B —
three specimens differing only in the reflectometer objective — yields ONE case carrying
three measurements.

**7. Did representations incorrectly create cases anywhere?** No. Invariant 5 holds. Yim
Fig 9's 18 declared representation panels produce 6 cases; the 12 scaled/normalized panels
link to their as-measured sibling through `derived_representation_of`.

**8. Were Sample and DepositionRun instantiated only where supported?** Yes, and the
second pass corrected what "a run" counts as. Only Yim yields any: 16 specimens from the
paper's own table, and **one identified DepositionRun** holding specimens 1, 2, 3 ("All of
the films were grown in the same ALD run", Series A). The two reproducibility statements
are **run-evidence groups**, not runs — the first pass reported "3 runs" by counting one
run and two assertions together. Every DepositionRun now names at least one specimen
(invariant 20).

**9. Could multi-material and mixed-geometry cases be represented?** Both, now.
Multi-material: `2.067203jes`'s printed Fig 12 stack cases carry SiO2 and Al2O3 as
`STACK_COMPONENT`, and the Fig 8 underlayer is typed `SUBSTRATE` rather than a second
deposit. Crucially, printed Fig 1 (precursor vapour pressure) no longer acquires a stack
context from the paper-wide inventory. Mixed geometry: **demonstrated** — printed Fig 8
yields a `vertical_structure` case taken from its own caption (AR ~30, 830 cycles, trench
18.5 × 0.6 µm) alongside 22 `planar` cases, each labelled with whether its geometry was
observed or defaulted. The first pass's escalation E1 is resolved.

**10. Could characterization results stay scientific results without being deposition
Experiments?** Yes, and the second pass added the provenance the first pass withheld. Two
Pt deposition cases exist from prose alone, now named by what they create: **"full
replica"** and **"micron-long mesoporous Pt tubes"**. CV and impedance remain Measurements.
Fig 8's coated results now carry an explicit chain — *tubular Pt replica → test electrodes
→ impedance / CV* — while the bare/uncoated series are typed `REFERENCE` and attached to
nothing, and Fig 7's coated result stays UNRESOLVED because its section says only "the
replica".

**11. Was simulation provenance preserved exactly?** Yes. `data_source` counts are
bit-identical to PSED for all four papers (Yim: 39 measured / 31 simulated, before and
after). Zero SimulationRuns are marked as cases. Yim's Fig 10 remains 31 SimulationRuns.

**12. Were all source curves, points and provenance preserved?** Yes, exactly.
16/16, 38/38, 4/4, 70/70 curves; 112, 624, 160, 1221 points — identical on both sides.
Every ResultSeries keeps its `curve_id`, `json_pointer` and `source_checksum`.

**13. Which implementation changes were actually required?**
- a caption/panel grammar that accepts `( a )`, `(a-c)` and `(panels a-c)`;
- a condition role axis (CASE_DEFINING vs MEASUREMENT_SETTING);
- per-case sweep values (`case00` → `deposition_temperature = 100 °C`);
- an evidence-gated identity resolver with an explicit contradiction test;
- representation grouping by series legend within a printed figure;
- a specimen-table reader working from PDF reading order;
- material roles and figure-scope geometry;
- a curve→entity source-slice fallback join.

Added by the second pass:
- a numeric range parser and a physical sign check;
- a purpose-clause guard and a species-property gate on material assertion;
- author-declared series definitions outranking column differencing, with co-variation kept;
- a value-based specimen join (legend value ↔ specimen-table column);
- identified runs separated from run-distinctness evidence;
- a produced-material provenance chain with reference-series typing;
- image-supported deposition cases.

**14. Which suspected changes turned out NOT to be necessary?**
- **Forking `to_kb.py`.** The pilot is a post-resolve layer; the 2019-line resolver was
  never copied. Every source identity survives by construction.
- **Replacing the resolver's granularity decision.** Its `experimental_case_status` /
  `experimental_case_count` verdict is reused verbatim; only the missing per-case VALUE was
  added.
- **New ontology classes.** `ExperimentalCase`, `DepositionRun`, `Sample`, `Measurement`,
  `PlotRepresentation` and the relations `performed_on` / `measures_case` /
  `produced_by_run` / `case_in_series` / `derived_representation_of` were already declared;
  the pilot instantiates them.
- **Touching the simulation branch.** It needed no change at all.
- **Any API call.** Everything was recoverable from local artifacts and the PDFs.
- **Removing `entity_key` / `physical_case_id`.** They are carried through untouched as
  source provenance and simply not used as scientific identity.

**15. Limitations before a 44-paper migration could be considered.**
See `logs/second_pass_remaining_limits.md` for the current list. In brief:

1. Cross-figure linking still depends on explicit statements — `am.2016.182` reports 50
   cases for 16 curves, `2.067203jes` 23.
2. Specimen identity depends on a machine-readable specimen table or a legend/caption code.
   Only 1 of the 4 pilot papers has one; the other three produce zero Samples.
3. Case-level geometry is implemented but unproven — no pilot paper carries per-figure
   geometry evidence in its extracted set (E1).
4. Sample-to-curve binding fails when a caption lists N specimens for N curves without
   saying which is which (E3). The pilot refuses rather than guessing by order.
5. `text_cases` recognises one contrastive construction (per-cycle process repetition).
   Other papers will state variants differently.
6. Two upstream extraction defects were worked around, not fixed: the caption grammar and
   the missing Docling crop (`logs/incidental_findings.md` #1, #2).
7. The condition-role instrument lexicon is a keyword list. It is generic but not complete,
   and a quantity with no ontology `recipe_role` and no instrument term stays UNRESOLVED.
8. Counts are not comparable across the boundary: a PSED "Experiment" and a pilot
   "ExperimentalCase" are different objects, so every downstream consumer that reports
   experiment counts would need its unit restated.
