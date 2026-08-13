# Nine-paper pilot — code changes

The implementation was copied verbatim from the frozen four-paper baseline
(`24f4b282bdcda91153b39c3ea745e9a9d7b9e540`). Three generic changes were then required by
the unseen papers. Per Part XXXIX, **all nine papers and all 85 tests were rerun after
each one**; the four controls reproduce the frozen baseline exactly.

---

## 1. Curve→entity join lost 56 of 93 curves on a panel-qualified figure

**Found by** `cremers2019` (93 curves → 37) and `10.1039_c5ta00205b` (21 → 20).

**Cause.** The canonical layer keeps the printed panel label — `"a (Without bottom)"`,
`"a (With bottom)"` — while the resolver normalises the same panel to `"a"`. The slice
join compared the two whole strings, so it never matched, and two entities sharing
`(figure, "a", series)` could only claim one curve between them.

**Fix** (`pilot_semantics.build`). The join now runs in four tiers, and each ResultSeries
records which one attached it in a new `join_method` field:

| tier | key | used |
|---|---|---|
| `linked_experiment_id` | the canonical layer's own link | 162 |
| `source_slice` | figure + panel **letter** + series label | 105 |
| `source_slice_ordered` | the same key covering N curves and N entities, zipped in source order | 56 |
| `panel_unique` | a (figure, panel) scope holding exactly one unjoined curve and one unjoined entity | 1 |

The ordered tier is a provenance attachment, not a scientific claim: both sides are
enumerated from the same `figure_data.json` in the same order, and it only runs when the
counts agree exactly. The `panel_unique` tier exists because a canonical curve may carry a
drawn legend (`"Pt"`) where the resolver recorded `<single>`.

**Generic because** it keys on panel-letter normalisation and count agreement, not on any
paper. **Result:** all nine papers now preserve 100 % of their source curves and points.

## 2. A review article minted six deposition cases

**Found by** `cremers2019`, a 44-page review with 19 "Reproduced / Adapted / Reprinted with
permission from …" statements and no depositions of its own.

**Fix** (`pilot_evidence.imported_from`, consumed in `pilot_semantics.build`). A figure
whose caption attributes its data to another work is an imported observation: its
ResultSeries are preserved in full with `originally_reported_in` recorded, and it mints no
current-paper ExperimentalCase. Two forms are recognised — the journal copyright line, and
a narrative attribution.

**Generic because** it reads an attribution statement, which any paper may carry. It is
also the ontology's own declared `ImportedLiteratureObservation` semantics.

**Result:** cremers2019 6 cases → 1. No control changed.

## 3. The narrative attribution form matched an instrument

**Found by** the control `10.1149_2.067203jes`, which dropped 23 → 22 cases immediately
after change 2.

**Cause.** `as (reported|measured|…) by X` matched *"as measured by in situ spectroscopic
ellipsometry"* — a method statement, not an attribution — and moved a paper's own figure
into imported literature.

**Fix.** The narrative form now requires the attributed source to look like a WORK: a
capitalised surname followed by "et al." or a year, matched case-sensitively. The strong
copyright form is unchanged.

**Result:** JES restored to 23 cases; 85/85 tests pass. This is exactly what the control
papers are for — the regression was caught by a control, not by inspection.

---

## Not changed

`pilot_ranges`, `pilot_roles`, `pilot_cases`, `pilot_sample_table`, `pilot_supplements`
and `run_pilot` are byte-identical to the frozen baseline apart from the count fields.
`build_dashboard.py` is new and is presentation only — it recomputes no semantics.

## Test changes

`tests/test_pilot_semantics.py` now reads its paper list from `pilot_papers.json` and
exposes `CONTROLS` / `UNSEEN`, so the generic invariants run over all nine while the
PDF-ground-truth anchors stay scoped to the four controls. No anchor was weakened; none
was added for the unseen five, because Part XIX forbids writing expectations before
reading the PDF and the review was performed after generation.
