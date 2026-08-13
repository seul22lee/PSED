# Nine-paper semantic generalization pilot

Tests whether the corrected four-paper semantic architecture generalizes to papers it has
never seen. **Production untouched, 0 API calls, nothing migrated.**

    4 original controls     regression: their frozen behaviour must reproduce exactly
    5 unseen generalization selected from the live 44-paper corpus, frozen before running

Frozen four-paper baseline: `24f4b282bdcda91153b39c3ea745e9a9d7b9e540`
(branch `figure-provenance-repair`).

## Run it

    python3 code/run_pilot.py            # rebuild all nine + comparison artifacts
    python3 tests/test_pilot_semantics.py # 20 generic invariants + 65 PDF anchors
    python3 code/build_dashboard.py       # visual report
    open  report/index.html

## Result

**85 / 85 tests pass. All four controls reproduce the frozen baseline exactly.** Every
source curve and every digitised point is preserved on all nine papers, and
measured/simulated provenance is bit-identical to production.

Three generic defects surfaced, all found by the unseen papers, all fixed generically and
all followed by a full nine-paper rerun (`logs/9paper_code_changes.md`):

1. the curve→entity join lost 56 of 93 curves where the printed panel label carries a
   qualifier (`"a (With bottom)"`) that the resolver normalises away;
2. a 44-page **review article** minted six deposition cases — figures reproduced from other
   works are now routed to imported literature, cutting it to one;
3. the narrative-attribution pattern for (2) initially matched *"as measured by in situ
   spectroscopic ellipsometry"* and cost a control one case — caught by the control.

## Verdict

**READY WITH LIMITED REPAIR** for a 44-paper migration. Zero unsupported merges, zero
Sample/Run hallucinations, zero simulation contamination. Four things must be settled
first: linkage-evidence coverage, geometry defaults, PDF availability for 30 of 44 corpus
papers, and restating downstream count semantics.
See `comparison/9paper_generalization_review.md`.

## Layout

    selection/candidate_matrix.csv    40 candidates × 20 stress dimensions
    selection/selected_5.md           why these five, and one corrected scoring error
    pilot_papers.json                 the frozen nine, with roles
    code/                             copied from the frozen baseline + build_dashboard.py
    papers/<id>/{source,extracted,resolved,semantic,diagnostics}
    tests/                            generic invariants + PDF-ground-truth anchors
    comparison/                       old_vs_pilot, unresolved taxonomy, reviews, verdicts
    logs/                             api_calls (empty), code changes, supplements,
                                      incidental findings, scope escalations
    report/index.html                 the visual dashboard

## The dashboard

Graph-first, not table-first. Per paper: a Case → Measurement → ResultSeries →
Representation node-link graph with the model branch drawn separately; a Figure × Case
matrix; a categorical condition fingerprint that distinguishes stated / range / inherited /
unknown; material-role and run/sample graphs; representation grouping; and an unresolved
flow view. Across papers: a nine-card landing grid that separates controls from unseen, a
ten-dimension scientific-review matrix, PSED-vs-pilot bars, and unresolved taxonomy plots.
Text tables are collapsed behind the visuals.
