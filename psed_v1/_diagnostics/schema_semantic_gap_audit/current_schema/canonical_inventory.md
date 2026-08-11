# Canonical inventory (read-only)

`curve_id = <doi>::F<printed_figure>::<panel>::<series_index>::f<fi>p<pi>`
(the trailing slot was added to remove a 5-way collision; see the earlier release audit).

## What canonical preserves
* source slice provenance (`paper_id`, `figure`, `figure_index`, `panel`, `series`,
  `json_pointer`, `source_checksum`) - **KEEP**
* `data_source` = measured / simulated - **KEEP**
* raw points and canonical axis values, with `TransformationExecution` linkage - **KEEP**
* `linked_experiment_ids` back to resolved cases - **KEEP**

## What canonical does not carry
* no sample, run or measurement identity (it never sees one)
* no representation relation: Yim Fig 9a/9b/9c become three unrelated curves with three
  `curve_id`s and no statement that they share underlying data
* material and geometry arrive pre-collapsed from resolve

## Responsibility boundary
Canonical is an **axis/unit normalisation and comparability layer**. It is the wrong place
to reconstruct sample or case identity: it receives one curve at a time and has no
paper-level view. Identity belongs to resolve; canonical should consume it.

Marking canonical `KEEP` / `CORRECT_AS_IS` for its own responsibility.
