# Four-paper semantic pilot — summary

Sandboxed test of the revised PSED experimental semantics. Production untouched, 0 API
calls, 0 pipeline stages re-run. Counts below are diagnostic; the change classes are the
result.

## Per paper

| | `am.2016.182` | `2.067203jes` | `c7ta03257a` | Yim 2020 `d0cp03358h` |
|---|---|---|---|---|
| **current PSED** Experiments | 54 | 32 | 0 | 39 |
| current entities / canonical curves | 16 / 16 | 38 / 38 | 4 / 4 | 70 / 70 |
| **pilot ExperimentalCases** | 50 | 26 | **2** | **18** |
| Measurements (of which caption-only) | 19 (5) | 38 (0) | 5 (1) | 43 (4) |
| ResultSeries | 16 | 38 | 4 | 70 |
| PlotRepresentations | 0 | 11 | 2 | 53 |
| Samples | 0 | 0 | 0 | **16** |
| DepositionRuns | 0 | 0 | 0 | **3** |
| StudySeries | 0 | 0 | 0 | **6** |
| SimulationRuns | 2 | 0 | 0 | **31** |
| merges / blocked merges | 4 / **2** | 0 / 0 | 0 / 0 | 7 / 0 |
| unresolved links | 15 | 12 | 5 | 41 |

`c7ta03257a` gains its first two experimental cases — PSED currently reports none for it.
Yim's 39 Experiments become 18 cases with 16 specimens, 3 runs and 6 series behind them.

## The fifteen questions

**1. Did the new semantics work on all four papers?** Yes. All four build end to end and
**51 of 51** checks pass — 16 generic invariants plus 35 four-paper acceptance anchors.

**2. Which same-case cross-figure links were recovered?**

- `am.2016.182` — GPC (Fig 2a), resistivity (Fig 2b) and XPS (Fig 2c) join into two
  deposition cases, Pt/HDMP at 100 °C and at 300 °C. Evidence: Fig 2c's caption enumerates
  "the temperatures of 100 and 300 °C", which the 2a/2b sweeps also report. Strength
  SUPPORTED.
- Yim — Fig 3 and Fig 5 join on specimen 11; Fig 7's three curves join because their study
  series varies only the reflectometer objective; Fig 8a's five repeat measurements stay one
  case; Fig 9's 18 panels collapse to the 6 measurements behind them.

**3. Which links remained unresolved, and why?** 73 in total.
- `c7ta03257a`: all four CV/impedance measurements, plus the recovered Fig 8(b) — the paper
  never states which Pt deposition produced the electrode that was measured.
- Yim: 41, mostly candidate pairs whose case-defining conditions agree while the source
  states no specimen or run linkage.
- `am.2016.182`: 15; `2.067203jes`: 12 — same pattern.
These are the intended outcome. Missing information was never read as sameness.

**4. Were any unsupported merges produced?** No. Every one of the 11 merges carries a
recorded evidence id (invariant: `every_merge_has_evidence.without_evidence = 0` for all
four papers). No merge rests on unknown-on-one-side alone.

**5. Were clearly identical cases still over-split?** Yes, in two places, both reported
rather than papered over. `am.2016.182` keeps 50 cases for 16 curves because most of its
sweeps have no cross-figure linkage statement. `2.067203jes` keeps 26. In both, the
splitting reflects genuine absence of linkage evidence in the source.

**6. Did measurement settings incorrectly create cases anywhere?** No. Invariant 4 holds:
no `MEASUREMENT_SETTING` appears among any case's case-defining conditions. Yim's Series B —
three specimens differing only in the reflectometer objective — yields ONE case carrying
three measurements.

**7. Did representations incorrectly create cases anywhere?** No. Invariant 5 holds. Yim
Fig 9's 18 declared representation panels produce 6 cases; the 12 scaled/normalized panels
link to their as-measured sibling through `derived_representation_of`.

**8. Were Sample and DepositionRun instantiated only where supported?** Yes; invariants 9
and 10 report zero without evidence. Only Yim yields any: 16 specimens, all from the
paper's own specimen table, and 3 runs — one SHARED_RUN holding exactly specimens 1, 2, 3
("All of the films were grown in the same ALD run", Series A) and two DISTINCT_RUNS markers
from explicit reproducibility statements. The other three papers name no specimen and no
run, so they get none.

**9. Could multi-material and mixed-geometry cases be represented?** Multi-material: yes —
`2.067203jes` produces 6 cases naming both SiO2 and Al2O3 with `STACK_COMPONENT` roles, and
2 more naming both as `DEPOSITED`. Mixed geometry: the mechanism works (geometry is resolved
per figure scope and `geometry_source` records whether a paper-level default was used) but
could not be **demonstrated** on this paper — its high-aspect-ratio figures are absent from
the extracted set entirely. See `logs/scope_escalations.md` E1.

**10. Could characterization results stay scientific results without being deposition
Experiments?** Yes — this is `c7ta03257a`'s whole point. Two Pt deposition cases exist from
prose alone (250 cycles, one vs three precursor exposures per cycle) with no x-y process
curve. The CV and impedance curves are Measurements with their material (Pt) and cycle count
(250) preserved, and their case linkage left UNRESOLVED because the source does not state it.

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
1. Cross-figure linking depends on explicit statements. Papers that state none keep
   figure-shaped cases — `am.2016.182` still reports 50, `2.067203jes` 26. The pilot is
   honest about it, but a corpus-wide run would leave many cases unlinked.
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
