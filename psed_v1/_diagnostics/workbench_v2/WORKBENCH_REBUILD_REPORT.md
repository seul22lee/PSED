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

---

# Final hardening: graph and range semantics

A second original-code review found five narrower defects. Four were places where the
first repair had fixed the visible symptom and left the mechanism, and the fifth was a
set of validation metrics that were not validating anything.

## A. Numeric range facets threw the species away

The model already carried qualified condition keys — `pulse_time@TMA`, `pulse_time@H2O`,
`precursor_pulse_time@TMA` — and `range_fields()` reduced each to `key.split("@")[0]`.
The browser then found its field with `k === r.id || k.indexOf(r.id + "@") === 0`, so one
box labelled "Pulse time" addressed *whichever qualified key the object happened to yield
first*. This is precisely the ambiguity the frozen condition-comparability layer exists to
prevent, reintroduced one layer above it.

It is not hypothetical here. **42 Condition Cases carry more than one species for the same
base quantity**, and 3 base quantities are split by species (`pulse_time`, `purge_time`,
`exposure_time`).

A range field is now the exact condition key and carries its own identity:

```
field_id          precursor_pulse_time@TMA
quantity_id       precursor_pulse_time
species_or_role   TMA
display_label     TMA precursor pulse time
canonical_unit    s
```

19 fields are offered, **10 of them species-qualified**. A quantity enters on coverage and
brings every qualified sibling with it, because offering an H2O pulse time without its TMA
counterpart is its own kind of misleading. An unqualified field standing beside qualified
siblings is labelled *(species unattributed)* rather than posing as all of them. The
browser addresses `vals[field_id]` through `hasOwnProperty` — no prefix, no first match —
and nothing in the builder or the page splits a condition key on `@` any more.

## B. Multi-case ResultSeries were still anchored to a case

The first repair stopped duplicating a sweep under all ten of its cases by choosing the
lowest case id as a "home". That trades one wrong claim for another: **no Condition Case
is primary** for a curve that traverses several, and nothing in the data says otherwise.

Placement is now decided in the model, and there are three populations, because these are
three different scientific situations:

| placement | series | where it appears |
|---|---|---|
| `CASE_LOCAL` | 88 | inside its one Condition Case |
| `MULTI_CASE_SWEEP` | 22 | the dedicated sweep section, owned by no case |
| `NO_CASE` | 121 | results whose producer carries no case link |

`placement_case_id` is non-null **only** when `n_cases == 1`. A traversed case shows a
*Related sweep results* cross-reference, never a card.

`case_ids` on a ResultSeries was renamed **`all_case_ids`**, because the name is half the
defence: there is no other kind of case list, and a field called `case_ids` invites
`[0]`.

## C. Matching cases are distinguished from traversed cases

A sweep may match a filter because *one* of its cases satisfies it. The page now computes
`matchingCases()` per series from the cases themselves, and shows both:

> Sweep result `RS::10.1039_d0ra09876k::F3::a::0::f1p0` — spans 10 cases,
> **4 match filters**, 6 more traversed

with every case listed and labelled `matches` or `traversed only`. Under *Deposition
temperature ≥ 500 K*, cases 001–006 (373–498 K) read *traversed only* and cases 007–010
(523–598 K) read *matches*. Point-to-case mapping remains unresolved and is stated as such;
nothing infers which points came from which case.

The comparison table gained the same discipline. A condition that differs across a sweep's
span is reported as **varies**, with the compact set or range — `deposition_temperature:
varies 100 °C … 325 °C (10 values)` — rather than one case's value standing in for the
whole curve.

## D. Per-case producer counts conflated the two kinds

Global counts were already split; per-case headings still said "N acts" and *Measurement
acts with matching results*. Each case now partitions its producers by **entity kind**
(never by the series' `data_source` label) into **Measurements** and **Simulations**
sections, each shown only when non-empty.

One corpus fact this rests on, reported rather than assumed: **no Condition Case in this
corpus is linked to a SimulationRun** — all 34 simulation-produced series carry no case
link. The partition is therefore exercised by injecting a SimulationRun into a real case's
producer lists in the live page and re-rendering the real code path; the screenshot
carries a banner saying so. No corpus claim is made by it.

The six XPS MeasurementActs in `10.1039_d0ra09876k` whose series are *labelled* simulated
remain MeasurementActs. That is a provenance question about the extraction, not a
workbench one, and conflating the two would bury it.

## E. Validation metrics were literal zeros

`false_common_native_targets = 0` and its neighbours were assignments. A metric that
cannot be non-zero measures nothing. Each is now derived by replaying the page's own
decision rule in Python and checking the invariant it is supposed to guarantee:

| metric | how it is computed | value |
|---|---|---|
| `false_common_native_targets` | every series pair the UI would offer a target to, checked for identical `(quantity, normalization, dimension, unit, axis)` | **0** |
| `key_based_false_common_targets` | the same sweep under the *pre-repair* key intersection | **1784** |
| `incompatible_plotted_pair_violations` | pairs offered an overlay whose frozen verdict is not `DIRECT_PROFILE`/`TRANSFORMABLE_PROFILE` | **0** |
| `multi_series_target_violations` | every trio within every target's member set — 25 622 sets, not one example | **0** |
| `duplicate_primary_entries` | the UI grouping rebuilt in Python, series counted | **0** |
| `multi_case_series_with_primary_case` | multi-case series carrying a `placement_case_id` | **0** |
| `qualified_range_fields_losing_qualifier` | fields whose id does not encode the species their entries carry | **0** |
| `ambiguous_first_match_range_lookups` | (field, case) pairs a lookup could resolve two ways | **0** |
| `prefix_match_ambiguous_lookups_avoided` | the same under the *pre-repair* prefix rule | **42** |

The two counterfactuals matter: 1784 and 42 are what the old algorithms would have
produced on this corpus, which is the evidence that the zeros are results rather than
tautologies.

Every one of these is a **build gate**, not a report. `main()` exits non-zero when any
invariant fails — and the test proves that by breaking the model three ways (anchoring a
sweep to a case, duplicating an entry, stripping a species) and asserting each is counted
and each fails the build.

## The static audit was broken

The no-first-case test stripped JavaScript comments with `re.sub(r"//.*|/\*.*?\*/", "",
src, flags=re.S)`. Under `re.S` the `//.*` branch matches across newlines, so the first
line comment consumed the rest of the file and the audit passed by having nothing left to
inspect. Block comments now use DOTALL and line comments explicitly do not
(`//[^\n]*`), the audit runs over the builder, the template **and the generated HTML**,
and a control asserts that the old pattern demonstrably destroys the source.

The remaining `cs[0]` occurrences are classified by an AST pass rather than by eye: both
sit inside `if len(cs) == 1`, which is a genuine singleton, and any unguarded zero
subscript of a case collection fails the test. **Scientific first-case occurrences: 0.**
The browser tests no longer navigate by `all_case_ids[0]` either; they locate a sweep by
its own id in `sweep_series_ids` and by `data-sweep` / `data-case` attributes.

## Tests

`tests/test_workbench_v2.py`: **280 assertions**, up from 149.

- **N8–N12** (static): species-qualified field identity and the corpus facts behind it;
  no qualifier stripping anywhere; placement semantics and the sweep population; per-case
  producer partition including the six preserved XPS acts; computed metrics with the
  build gate proven by breaking it; matching-vs-traversed semantics.
- **Q** (Chromium): TMA and H2O pulse-time facets shown separately and no bare ambiguous
  box; a controlled fixture proving 0.1 s / 2 s and 500 ms / 2 s filter independently by
  species and canonically by unit; a sweep under a partial filter showing 4 matches and
  6 traversed-only with no owner; the sweep condition summary reading *varies*; a
  fixture case rendering separate Measurements and Simulations headings with the
  SimulationRun card under the latter; tray persistence for a multi-case series.

## Visual review

Nine states captured at 2× and inspected. Three defects were found by looking:

1. the facet UI rendered `label` instead of `display_label`, so the ambiguous bare
   **Pulse time** box was still on screen even though the model had split it;
2. the sweep section rendered before the condition cases, burying 71 cases behind 22
   sweep cards — reordered to cases first;
3. `1 measurement acts` / `0 simulation runs` — pluralisation fixed, and a zero
   simulation count is now omitted rather than printed on all 71 cards.

## Scientific drift

Compared field-by-field against `25f725b`: ExperimentalCase ids, `case_id` values, nominal
conditions, MeasurementAct ids/kinds/members, ResultSeries ids, case membership, native x
and y points, every representation's `target_id` and values, every pair verdict and
overlay eligibility, samples, runs and measurements — all **UNCHANGED**. The four
`tests/canonical_layer` failures were confirmed identical at `25f725b`:
**PRE_EXISTING / UNCHANGED / NOT WORKBENCH DRIFT**.

---

# Case-scoped filter conjunction repair

One defect remained, and it was the root of two symptoms.

## The defect

Filters were declared with scopes — Condition Case, MeasurementAct, ResultSeries — but the
case-scoped ones were not evaluated together on a case. `facetsOk()` tested every facet,
*including* the case-scoped ones, against the precomputed **series** index; `rangeOk()`
conjoined numeric bands on one case. The two never met:

```
old:   geometry satisfied because case A has it        (series-level index)
       temperature satisfied because case B is hot     (any-case existential)
       -> the ResultSeries matched a combination no single case ever had
```

For a sweep spanning `A: LHAR, 400 K` and `B: planar, 550 K`, a user asking for
*LHAR and ≥ 500 K* got the series back. No experiment in it was ever both.

The same root cause fed the facet counts: `facetOptions()` counted **every case traversed
by a candidate series**, so a case excluded by the active filters still incremented the
number next to an option.

## The repair

Scope is now model metadata (`facet_defs`), and the algorithm iterates on scope, never on
a facet name — adding a facet is a metadata change. One predicate is the authority:

```js
caseMatchesFilters(cid, skipFacet, skipRange, candidate)
    every Condition Case-scoped facet:  OR within, AND across, on THIS cid
    every active numeric range:         exact field_id, canonical magnitude, on THIS cid
```

`matchingCases()` is that predicate mapped over `all_case_ids`, and series eligibility is
defined *from it* — `matchingCases(s).length > 0` — so the results column and the sweep
card's own "N match filters" cannot disagree. `rangeOk()` is gone; its logic lives inside
the one predicate. `nonCaseFacetsOk()` keeps ResultSeries- and MeasurementAct-scoped
facets on the series index, which is correct for them and preserves technique + quantity
describing one act → series path.

`hasActiveCaseFilters()` is asked explicitly, so "no case filters" never silently becomes
"must have a Condition Case": the 121 results with no case link stay visible until a
case-scoped constraint is actually set, and are then excluded rather than passed through
as wildcards.

Facet option counts changed meaning to **eligible Condition Cases** — cases that satisfy
the candidate option *together with* every other active case-scoped constraint, on the
same case, with the facet's own selections lifted for leave-one-out. Cases and series are
deduplicated independently.

## What the corpus can and cannot prove

**REAL CORPUS.** Under *Deposition temperature ≥ 500 K*, the `Deposited material` counts:

| option | old (traversed cases) | new (eligible cases) |
|---|---|---|
| Y2O3 | 29 | **17** |
| Pt | 11 | **5** |
| SiO2 | 9 | **5** |
| Al2O3 | 9 | 9 |

The 10-case sweep still reports `all_case_ids = 10`, `matching_case_ids = 4`,
6 traversed-only, and remains eligible because 4 > 0.

**The corpus cannot exhibit the cross-case false positive.** All **22** of its multi-case
sweeps are categorically homogeneous — every case a sweep traverses carries the same
material, geometry, paper, precursor and co-reactant; only numeric conditions vary. The
exhaustive builder metric therefore has an **empty universe**, and reports it:

```
cross_case_constraint_universe                       0
cross_case_constraint_false_positive_violations      0     (vacuous - empty universe)
cross_case_false_positives_under_series_level_rule   0     (vacuous - empty universe)
multi_case_series_with_varying_case_facets           0     <- why the universe is empty
```

A zero over an empty universe is not evidence. The behavioural proof is therefore a
**CONTROLLED FILTER-SCOPE FIXTURE** injected into the live page, driving the real
predicate:

```
FIXTURE  case A: geometry A, 400 K      case B: geometry B, 550 K
         geometry A + >= 500 K  ->  excluded, matching_case_ids = []
         geometry B + >= 500 K  ->  included, matching_case_ids = [B]
         each constraint alone  ->  still matches
FIXTURE  material on A + geometry on B  ->  rejected
         both on A                      ->  accepted
         material A OR B + geometry B   ->  accepted via B   (OR within, AND across)
```

The defect is latent rather than absent: any future paper whose sweep crosses a geometry
or material would have triggered it.

**REAL CORPUS**, exhaustive over every case-scoped facet option, bare and paired with a
temperature band (46 filter states):

```
matching_series_with_zero_matching_cases_under_case_filters   0
facet_case_count_leakage_violations                           0
```

## Generalizability

The filter engine contains no DOI, Condition Case id, ResultSeries id, material, geometry
or species literal, no branch on a facet name, and no branch on a corpus cardinality; its
only `sort` orders options for display. Asserted by test, over the builder, the template
and the generated HTML.
