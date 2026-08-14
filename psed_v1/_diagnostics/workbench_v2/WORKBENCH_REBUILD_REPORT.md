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

---

# Hardening: scientific overlay semantics and numeric filtering

An external review of the rebuilt workbench found four defects. All four shared a shape:
the page was *structurally* right and *semantically* wrong, so nothing looked broken.

## A. A shared axis was decided by a key, not by a meaning

Every ResultSeries carries a representation called `native`, and the common-representation
calculation intersected representation **keys**. Every selection therefore had `native` in
common, so a film thickness in nm and a growth-per-cycle in nm/cycle were offered one
axis and drawn on it.

The corpus makes the size of this concrete: among series with a plottable native Y there
are **two distinct native Y meanings** (`film_thickness [nm]`, 37 series;
`growth_per_cycle [nm/cycle]`, 22 series), and the old intersection treated them as one.

Every representation now carries a `target_id` — `axis | quantity | normalization |
dimension | unit` — computed in Python from the frozen layers. A target is offered only
when every selected series can materialise *that signature*, and only when every selected
pair also carries `physical_overlay_allowed`, which the model derives from the frozen
comparability verdict (`DIRECT_PROFILE` / `TRANSFORMABLE_PROFILE`; `SHAPE_ONLY_PROFILE`
remains an explicit opt-in). Axis labels and tooltips are stated in the target's quantity
and unit rather than one series' local label.

When no shared target survives, the page does not fail quietly: every option is disabled
and the reason is stated once per axis box, with the overlay panel repeating why.

## B. One curve was counted as several results

A sweep ResultSeries belongs to every Condition Case it traverses — up to ten in this
corpus, 22 series in total. The results column pushed each series under *every* one of its
cases, so one measurement read as ten results.

Each ResultSeries now has exactly one primary entry, under its lowest-id case, and carries
an expandable **Spans N Condition Cases** list. The other cases it traverses show an
*Also traversed by* cross-reference instead of a repeat, and the header counts the two
populations separately (`N condition cases · M more traversed by a matching series`) —
because a case reached only through a traversing sweep is not a case with a matching
result, and counting them together overstated the answer to every condition filter.

## C. Numeric ranges compared raw numbers

`rangeOk()` read `v.raw`, so a filter compared the number the paper printed rather than
the magnitude it denotes: 80 °C and 353.15 K are the same condition and 500 ms and 0.5 s
are the same time, but raw comparison sees three different numbers. It now reads
`v.canonical`, and a value with no canonical magnitude does not silently pass.

The range controls are no longer hardcoded in the page. The model emits `range_fields`
(top numeric quantities by case coverage) with the unit the comparison actually runs in,
and a field whose raw units do not share one dimension is not offered at all. The UI
states both: *Deposition temperature [K] — canonical magnitude · reported as °C*.

`units.base_symbol()` was added to the canonical layer for this: a caller holding
`value*factor+offset` needs to be able to say which unit that number is in.

## D. Simulations were counted as measurements

`SimulationRun`-produced series contributed to a count labelled "measurement acts". The
header and every per-case count now partition by producer kind: **201 measurement acts,
34 simulation runs**.

One honest observation this surfaced: `data_source == "simulated"` is a *series* label and
does not imply a SimulationRun producer. Six XPS MeasurementActs in `10.1039_d0ra09876k`
produce series labelled simulated — most likely fitted peak components. The counts follow
the producer, which is why the two numbers do not coincide.

## Visual review

Six states were captured at 2× and inspected, not merely asserted:
initial page, active facets with a canonical range, an expanded Condition Case, a
compatible two-series overlay, an incompatible selection, and an expanded multi-case sweep.
Reproduce with `python3 _diagnostics/workbench_v2/capture_review_screenshots.py <outdir>`.

Three defects were found by looking that no assertion had caught:

1. a ≥400 K filter listed 50 °C cases — correct series matching (a sweep does reach 400 K)
   presented as if those cases had matching results. Fixed by splitting the header count.
2. every disabled option repeated the same forbidding sentence; the reason is now stated
   once per box.
3. an unresolved canonical unit rendered as `[]`, which claims a dimensionless quantity.
   172 of 231 series have an unresolved canonical unit on some axis; they now read
   *unit unresolved*.

## Tests

`tests/test_workbench_v2.py`: **149 assertions**, up from 99. New sections:

- **N1–N7** (static, on the built artifact): every representation carries a target
  identity; `native` is demonstrably not universal; the intersection is on `target_id`;
  overlay eligibility follows the frozen verdict; one primary entry per ResultSeries;
  range filtering is canonical and its units are model-declared; simulations are excluded
  from the act count.
- **O** (Chromium): two series with different native Y meanings produce no common target,
  every option disabled, nothing drawn, and a stated reason; two compatible series overlay
  on one axis whose label and tooltips are in the target unit; a 10-case curve appears
  exactly once with its span expandable and cross-references elsewhere; a canonical band
  matches while the same number read as the raw unit does not; the header counts are the
  producer-kind partition, recomputed in the test rather than trusted.

Project suite: unchanged. The four pre-existing failures in `tests/canonical_layer` were
confirmed identical at the baseline commit via a read-only worktree — they are extraction
debt, not drift from this change.
