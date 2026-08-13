# Scope escalations — nine-paper pilot

## E1 — the candidate pool was constrained by PDF availability

**Requirement.** Part XX requires a PDF ground-truth review of each selected paper; Part 0
sets the original PDF as the first source of truth.

**Blocker.** Only **10 of the 40** candidate papers have a local PDF. Reviewing the other
30 would mean reviewing the pilot against `document.md` — the very artifact whose failures
this pilot exists to detect, and the one that had a defect in three of the four original
papers. That review would be circular.

**What was done.** The selection pool was restricted to the 10 papers with PDFs, and the
restriction is stated at the head of `selection/selected_5.md`. All nine papers in the
final set have a PDF.

**Cost.** Real. Several structurally interesting papers were excluded, notably
`10.1016_j.sse.2022.108584` — the **only** corpus paper with
`ImportedLiteratureObservation` entities (10 of them). Dimension T was therefore not
covered by design; it was exercised by accident, through `cremers2019`'s review-article
structure.

**Minimum broader change required.** Acquire the 30 missing PDFs, which is a corpus
acquisition task outside this pilot.

## E2 — one unseen paper's over-split cannot be closed without new evidence

**Requirement.** Part XIX asks whether obvious same-case over-splits remain.

**Blocker.** `10.1021_acs.langmuir.6b03119` reports 12 cases where the PDF describes about
two process variants. Closing the gap needs a positive linkage statement, and the paper
makes none — its captions never say two curves are the same film, sample or run. The only
ways to merge would be condition equality alone (forbidden by the identity rule) or a
paper-specific exception (forbidden by Part 5).

**What was done.** The 12 pairs are recorded as `CONDITION_ONLY_NO_POSITIVE_LINK` in
`comparison/unresolved_links.csv` and shown in the report's unresolved view. No merge was
forced.

**Minimum broader change apparently required.** A same-figure rule of the form "curves in
one panel that share every case-defining condition and differ only in a plotted coordinate
are one case" — a genuine semantic decision that belongs to the architecture review, not
to this pilot.

## E3 — the one surviving cremers2019 case cannot be removed on explicit evidence

**Requirement.** A review article should mint no current-paper deposition cases.

**Blocker.** After imported-literature routing, one case survives: printed Fig 11, whose
caption describes a TMA/H2O process on two test structures **without** an attribution
line. The attribution lives in superscript reference markers (67, 86) that the caption text
does not spell out. Removing it would require either treating a whole paper as a review
(a document-level classification this pilot does not do) or reading superscript citation
markers out of the caption.

**What was done.** The case is kept and the residue is stated in
`comparison/new5_scientific_review.md`. The scientifically ideal answer is 0; the pilot
reaches 1.
