# Four-paper semantic pilot

A sandboxed implementation of the revised PSED experimental semantics on four papers.
**Production is untouched**: everything here was built from a read-only snapshot, with
0 API calls and 0 pipeline stages re-run. Nothing here is applied back to production.

    10.1038_am.2016.182     cross-figure same-case linkage; recovered printed Figure 4
    10.1149_2.067203jes     multi-material / must-not-merge regression
    10.1039_c7ta03257a      deposition cases with no x-y process curve; recovered Fig 8(b)
    10.1039_d0cp03358h      Yim 2020 — the semantic control

## Run it

    python3 code/run_pilot.py            # build the semantic layer + comparison artifacts
    python3 tests/test_pilot_semantics.py # 16 invariants + 35 acceptance anchors
    open  report/index.html              # self-contained human-review report

## What the model says

`ExperimentalCase` is a scientifically distinguishable deposition case. A figure, a panel,
a curve, a plot representation and a measurement setting never define one. `Measurement` is
an observing act; several may belong to one case. `ResultSeries` holds the numbers and keeps
`curve_id` and the source pointer. `Sample` and `DepositionRun` are instantiated only where
the source states them. `SimulationRun` is never a case.

The identity rule, applied without exception:

    POSITIVE LINKAGE EVIDENCE + COMPATIBLE CASE-DEFINING CONDITIONS + NO CONTRADICTION

**Missing is not the same as same.** An unresolved link is preferred to an unsupported
merge, and 73 pairs across the four papers are recorded as unresolved for exactly that
reason.

## Results

51 of 51 checks pass. All source curves and points are preserved exactly
(16/16, 38/38, 4/4, 70/70 curves; 112, 624, 160, 1221 points). Measured/simulated
provenance is bit-identical to PSED. Every merge carries an evidence id; no Sample or
DepositionRun exists without source evidence.

Headline outcomes: Yim's 39 Experiments become 18 cases with 16 specimens, 3 runs and 6
study series; Fig 9's 18 representation panels collapse to the 6 measurements behind them;
`c7ta03257a` gains its first two experimental cases, both from prose, with its CV and
impedance curves preserved as Measurements whose case link is honestly UNRESOLVED.

See `comparison/pilot_summary.md` for all fifteen answers.

## Layout

    pilot_papers.json               the work list — in config, so no module names a paper
    production_snapshot_manifest.json  SHA256 of every production file copied in
    git_status_before.txt / after   integrity proof

    code/       pilot_evidence  pilot_roles  pilot_cases  pilot_semantics
                pilot_sample_table  pilot_supplements  run_pilot  build_report
                pilot_inventory / pilot_entities  (unmodified production references)
    ontology/   read-only copy of the compiled ontology
    papers/<id>/source|extracted|resolved|semantic|diagnostics
    tests/      16 generic invariants + 35 four-paper acceptance anchors
    logs/       api_calls.json (empty)  pilot_code_changes  incidental_findings
                scope_escalations
    report/     index.html — self-contained
    comparison/ old_vs_pilot.{json,csv}  unresolved_links.csv
                semantic_invariants.json  pilot_summary.md

## Scope boundaries honoured

No production file was edited, staged or committed. No API was called
(`logs/api_calls.json` is `[]`). Extraction, resolution, canonical and KG stages were not
re-run. Seven incidental production defects were recorded and left unfixed
(`logs/incidental_findings.md`); three requirements that would have needed production
changes were stopped and documented (`logs/scope_escalations.md`).
