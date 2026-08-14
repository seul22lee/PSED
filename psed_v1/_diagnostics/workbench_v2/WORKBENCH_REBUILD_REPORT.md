# Scientific Comparison Workbench — rebuild report

Rebuilt from the frozen semantic layers rather than patched. The previous candidate
(`075182f`) is superseded: its data model treated a Condition Case as an experiment,
collapsed a ResultSeries' case membership to the first element, and let a Y control change
an axis title while the plotted values stayed raw.

## Semantic model consumed

| layer | freeze |
|---|---|
| entity identity | `fadd925` |
| result/profile comparability | `849c377` |
| condition comparability | `600320a` |
| ontology readiness | `14bff7b` |

## Entity counts

| entity | count |
|---|---|
| Condition Cases | 182 |
| Measurement records | 213 |
| MeasurementActs | 201 |
| SimulationRuns | 34 |
| ResultSeries (persisted = searchable) | 231 |
| profile series | 71 |
| multi-case ResultSeries | 22 (max 10 cases) |
| multi-member MeasurementActs | 6 (max 3 members) |
| source Sample records | 16 |
| physical specimens resolved | 0 |
| known DepositionRuns | 1 |
| indexed comparability pairs | 1485 |

Nothing is excluded. A series whose measurand does not resolve to an ontology quantity is
admitted with `measurand_status = UNRESOLVED_MEASURAND`: it stays visible and keeps its
full case membership, and is simply not comparable. Dropping such series would have
deleted one of the 22 multi-case relations (an XRR critical-angle curve spanning ten
cases) and quietly shrunk the denominator.

## Filter semantics

OR within a facet, AND across facets, options computed leave-one-out so a selection never
collapses its own list. Facet scopes are explicit in the UI:

- **Condition Case**: material, precursor, co-reactant, geometry, paper, and the numeric
  ranges (deposition temperature, working pressure, cycle count) compared on canonical
  numeric values rather than text.
- **MeasurementAct**: technique.
- **ResultSeries**: result quantity, coordinate, normalization basis, result type.

Matching runs over ResultSeries and then groups upward, so a technique constraint and a
quantity constraint are satisfied by the same scientific path rather than by two unrelated
measurements in one case.

## Comparison semantics

Pair verdicts, per-axis reasons and missing-context parameters are computed in Python by
the frozen comparability runtime and embedded. The browser reads them. It does not infer
comparability from labels, units or the fact that two axes are dimensionless.

## Transform behaviour

Every representation a series can reach arrives with its coordinates **already computed**.
An option that cannot be materialised is shown disabled with the reason; an option that is
offered necessarily moves the curve, because the page has no path to render a target
without its values. `t_over_t_max` is computed from the series' own maximum with recorded
provenance; `t_over_t_entrance` and `t_over_t_planar` are offered as disabled, because
their reference is not resolved for any series in this corpus.

A note on evidence: `y/max` is a *linear* transform, so under an auto-ranged axis the pixel
geometry is unchanged. The regression therefore asserts on the plotted values and tooltip
contents, not on polyline coordinates — the latter cannot witness this class of transform.

## Known unresolved evidence

- physical specimen identity: **unresolved corpus-wide** (0 traceable identifiers)
- deposition runs: 1 known, sample-scoped; 13 of 16 samples have none
- point-to-case mapping for sweeps: not persisted, reported unresolved
- `critical_angle`, `flow_ratio`: deferred ontology debt

These are evidence-completeness states, not defects, and the UI shows them as such.

## Validation cases

- **CASE-10.103-002** — one Condition Case, 6 source sample records, physical specimen
  identity unresolved, 1 run reached through a single sample, 15 MeasurementActs,
  15 ResultSeries. Not one experiment, not one physical run.
- **22 multi-case ResultSeries** — asserted exhaustively, not sampled.
- **6 multi-member MeasurementActs** — shown as one act with several representations.

## Tests

99 assertions in `tests/test_workbench_v2.py`, of which the browser half drives the real
page in Chromium via Playwright: load without console errors, facet open/click/auto-close,
chips, result narrowing, add to tray, tray persistence across a filter change, clear-all,
Y and X transforms changing plotted values, multi-case provenance, tray clearing.
Full project suite: 1331 passing.
