> **SUPERSEDED.** This document describes a nine-paper set that included
> `cremers2019`, a review paper since removed from the pilot as out of scope.
> It is kept as a historical record. The active-set report is
> [`8paper_semantic_review.md`](8paper_semantic_review.md).

# Nine-paper generalization review

Four original controls, five unseen papers from the live corpus, one generic resolver,
0 API calls, production untouched.

| | PSED Exp | cases | meas | RS | reps | samples | runs | run-ev | sims | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|
| `am.2016.182` ᶜ | 54 | 50 | 19 | 16 | 0 | 0 | 0 | 0 | 2 | 15 |
| `2.067203jes` ᶜ | 32 | 23 | 40 | 38 | 11 | 0 | 0 | 0 | 0 | 14 |
| `c7ta03257a` ᶜ | 0 | 2 | 5 | 4 | 2 | 0 | 0 | 0 | 0 | 3 |
| `d0cp03358h` ᶜ | 39 | 18 | 44 | 70 | 53 | 16 | 1 | 2 | 31 | 62 |
| `cremers2019` ᵘ | 6 | **1** | 9 | 93 | 25 | 0 | 0 | 1 | 86 | 8 |
| `d0ra09876k` ᵘ | 50 | 50 | 33 | 34 | 0 | 0 | 0 | 0 | 1 | 32 |
| `c5ta00205b` ᵘ | 20 | **7** | 21 | 21 | 0 | 0 | 0 | 0 | 0 | 15 |
| `langmuir.6b03119` ᵘ | 12 | 12 | 12 | 12 | 2 | 0 | 0 | 0 | 0 | 12 |
| `d0ra01602k` ᵘ | 53 | **20** | 37 | 36 | 0 | 0 | 0 | 0 | 0 | 25 |

ᶜ original control ᵘ unseen generalization

---

**1. Did the corrected architecture reproduce the original four papers?**
Yes, exactly. 50 / 23 / 2 / 18 cases, identical to the frozen baseline `24f4b28`, with the
same 16 / 38 / 4 / 70 source curves and 112 / 624 / 160 / 1221 points. All 85 tests pass,
including all 65 PDF-ground-truth anchors. One control (`2.067203jes`) caught a regression
introduced while fixing an unseen paper — which is precisely what controls are for.

**2. Did it generalize to the five unseen papers without paper-specific logic?**
Yes. `tests` invariant 16 checks mechanically that no DOI, paper id or figure number
appears in any executable module under `code/`; the work list lives in
`pilot_papers.json`. Three generic changes were needed (§13 below), all triggered by
structures the four originals never contained, and all rerun across the full nine.

**3. How many unsupported merges were found?**
**Zero.** All 15 merges across nine papers carry a recorded evidence id
(`every_merge_has_evidence.without_evidence = 0` for every paper), and 4 merges were
blocked on contradictory case-defining conditions.

**4. How many obvious same-case over-splits remained?**
**One clear case**: `10.1021_acs.langmuir.6b03119`, 12 cases where the PDF describes about
two process variants. A second, milder one persists in the control `am.2016.182` (50 cases
for 16 curves). Both have the same cause and both are visible rather than silent: every
such pair is recorded as `CONDITION_ONLY_NO_POSITIVE_LINK`.

**5. Which semantic patterns generalized well?**
- **Multi-output grouping** — the strongest result. `d0ra01602k` has 27 multi-output
  panels (9× Yim's 3) and collapses 53 PSED experiments to 20 correctly.
- **Sweep value normalization** — `d0ra09876k`'s 7 independent sweeps produce 41 cases each
  carrying its own `deposition_temperature` / pulse / purge value.
- **Fits** — 7 `Fit` entities across two unseen papers, all preserved as Measurements,
  none minting a case. A dimension the original four never exercised.
- **Case-level geometry** — worked on a paper (`cremers2019`) whose `geometry.json` has no
  class at all, and gave `porous_material` and `lateral_channel` from figure captions.
  Also 2 cases each in `c5ta00205b` and `d0ra01602k`.
- **Material locality** — the porous support in `c5ta00205b` and the TiO2 nanotube layer in
  `langmuir` are both correctly excluded from the deposited material.
- **Conservative Sample/Run** — four of five unseen papers name no specimen and make no run
  statement, and the pilot asserts none. Zero hallucinations.

**6. Which patterns still require improvement?**
- **Cross-figure case linking** depends on an explicit statement. Papers that make none
  keep figure-shaped cases (§4).
- **Geometry defaults**: `langmuir` is entirely about high-aspect-ratio nanotubes yet every
  case reports `planar`, because no caption states a geometry in the recognised vocabulary.
- **Document-level classification**: a review article is recognised figure by figure via
  attribution lines, not as a document. One `cremers2019` case survives because its caption
  carries the citation as a superscript marker the text does not spell out.

**7. Which unresolved links are scientifically appropriate?**
184 of 186. `CONDITION_ONLY_NO_POSITIVE_LINK` (90) is the identity rule working as
designed. `SOURCE_TRULY_UNSPECIFIED` (32) and `PROVENANCE_CHAIN_INCOMPLETE` (60) are the
source not saying which deposition produced a characterised specimen — the honest answer.
`REFERENCE_BY_DESIGN` (2) are comparison controls that must never be attributed.

**8. Which unresolved links appear to be resolver failures?**
`MEASUREMENT_ONLY_FIGURE` (2) is arguably a mislabel rather than a failure — a
precursor-property figure has no case to link to. The 12 `langmuir` entries are a resolver
*limitation* rather than a failure: the evidence the rule requires genuinely is not in the
paper. **No unresolved link was traced to a parsing bug after the three fixes.**

**9. Did local material semantics generalize?** Yes. Every unseen paper asserts its
deposited material from local evidence; no paper-wide inventory leaked into a case; and
supports, templates and nanotube scaffolds were never read as co-deposits.

**10. Did case-level geometry generalize?** Yes, and further than expected — it worked on a
paper with no paper-level geometry at all. It remains PARTIAL where the source states
geometry only in prose.

**11. Did Sample/Run evidence behave conservatively?** Yes, strictly. Sixteen specimens and
one identified run across nine papers, every one from an explicit source statement; zero
Samples or Runs without evidence; run-distinctness assertions counted separately from
runs (`cremers2019` contributes one such assertion, no run).

**12. Did characterization provenance generalize?** Partly. Results are never discarded:
`c5ta00205b`'s 10 electrochemical measurements and `d0ra09876k`'s 12 characterisation
measurements are preserved with their material and conditions, and left `CASE_UNRESOLVED`
because the source does not identify the producing deposition. The chain machinery from
`c7ta03257a` did not fire on the unseen papers — none of them contains an equivalent
"the product was placed on the measured device" statement.

**13. Did representation grouping generalize?** Yes where representations exist:
`cremers2019` declares 25 and `langmuir` 2, none of which mints a case. The three other
unseen papers declare none, correctly.

**14. Was simulation provenance preserved?** Yes. `data_source` is bit-identical to
production on all nine papers; zero SimulationRuns are marked as cases; `cremers2019`'s 86
model entities stay entirely out of the case layer. One upstream inconsistency was found
and preserved rather than overridden (`logs/incidental_findings.md` #1).

**15. Did any new correction damage the original four controls?**
One did, and it was caught immediately: the narrative-attribution pattern initially matched
"as measured by in situ spectroscopic ellipsometry" and cost `2.067203jes` a case. Tightened
in the same pass; the controls are byte-identical to the frozen baseline afterwards.

---

## 16. Is the semantic approach ready for a 44-paper production migration?

# READY WITH LIMITED REPAIR

**Why not NOT READY.** The architecture held on five papers it had never seen, including
one structurally unlike anything in the training set (a 44-page review whose data is 92 %
model output and almost entirely reproduced from other works). Zero unsupported merges,
zero Sample or Run hallucinations, zero simulation contamination, and 100 % preservation of
source curves, points and measured/simulated provenance on all nine. Three defects surfaced
and all three were fixable generically in a few lines each.

**Why not READY.** Four things must be settled first, and none is a small edit:

1. **Cross-figure linking coverage.** The identity rule is correct but the *evidence
   extractors* are narrow. Papers that state linkage in ways the pilot does not yet read
   keep figure-shaped cases. On this sample that is 2 of 9 papers; corpus-wide it would
   leave a large fraction of cases unlinked, and the reported case count would be closer to
   the current Experiment count than to the science.
2. **Geometry defaults.** `langmuir` shows a paper reporting `planar` for an entirely
   high-aspect-ratio study. The mechanism is right, the vocabulary and the evidence sources
   are not yet broad enough.
3. **PDF coverage.** 30 of 44 corpus papers have no local PDF. A migration validated only
   against Docling output would be validated against the artifact whose failures this work
   exists to catch.
4. **Counts are not comparable across the boundary.** A PSED "Experiment" and a pilot
   "ExperimentalCase" are different objects. Every consumer that reports experiment counts —
   the dashboards, `evaluate_kb.py`, `similarity.py`, the twin — needs its unit restated
   before, not after.

**The limited repair, in dependency order.** (i) broaden the linkage-evidence extractors
and re-measure over-split rates; (ii) broaden geometry evidence beyond figure captions;
(iii) acquire the missing PDFs and re-validate; (iv) restate downstream count semantics.
Items (i) and (ii) are resolver work of the same size as the three fixes made here;
(iii) is acquisition; (iv) is a decision, not code.

**Not attempted here, and deliberately.** Nothing was migrated to production, and no
corpus-wide run was made.

---

## Dimension coverage achieved

Of the 20 stress dimensions, **19 were exercised** across the nine papers. **T (imported
literature)** was not covered by design — the only corpus paper with
`ImportedLiteratureObservation` entities has no PDF — but was exercised in substance by
`cremers2019`'s 19 reproduction statements, which is what produced the single most
valuable correction of this pass.
