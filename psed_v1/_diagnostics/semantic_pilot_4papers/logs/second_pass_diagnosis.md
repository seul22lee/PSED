# Second-pass diagnosis — wrong output → PDF evidence → responsible rule → minimal fix

Written before any code was changed. Every "responsible rule" was located by reading the
current pilot implementation, not inferred.

---

## A. Numeric ranges parsed as negative scalars

**Current wrong output** — `papers/10.1149_2.067203jes/semantic/experimental_cases.json`

```
CASE-10.114-001  pulse_time    = -120  ms      provenance = directly_stated
CASE-10.114-002  pulse_time    = -120  ms      provenance = directly_stated
CASE-10.114-008  cycle_number  = -40   cycle   provenance = directly_stated
```

**PDF ground truth**

> "…the precursor was introduced into the reactor by ultrashort doses **(10-120 ms)** using
> fast ALD valves."
> "…alternating layers of ALD Al2O3 and ALD SiO2 deposited using **10-40 cycles** each."

Both are positive intervals. A dose of −120 ms is not a physical quantity.

**Responsible rule.** Not the pilot's own parser: the values arrive already negative on
`entity["bound_conditions"]`, whose `raw_evidence` is literally `'doses (10-120 ms'` and
`'-40 cycles'`. Production's `pipeline/canonical/conditions.py` reads the hyphen as a sign.
The pilot then copies the value through `pilot_cases.entity_conditions()`, which preserves
`value` verbatim. **The pilot has no numeric sanity layer at all**, so it launders a
production defect into a scientific claim.

**Minimal generic correction.** A new `code/pilot_ranges.py`:
* re-parse each inherited condition's own `raw_evidence` for a range written with a hyphen,
  en dash, em dash or the word "to"; when found, emit an explicit interval
  (`value_lower` / `value_upper` / `value_kind = "range"`) instead of a scalar;
* a physical-sign check — a duration, a cycle count, an absolute pressure, a length or a
  Celsius deposition temperature cannot be negative; a genuinely signed quantity
  (potential, slope, binding energy) still can;
* when the sign check fails and no range is recoverable, the value is dropped with its
  evidence, never silently kept.

---

## B. Paper-wide material inventory leaking into a local scope

**Current wrong output**

```
CASE-10.114-001  figures ['1']  deposited_material=None
                 context_materials  ['Al2O3','SiO2']
                 material_roles     {Al2O3: DEPOSITED, SiO2: DEPOSITED}
                 multi_material_context = true
```

**PDF ground truth** — printed Figure 1 caption:

> "Vapor pressure of the H2Si[N(C2H5)2]2 (SAM.24) precursor **used for ALD of SiO2** as a
> function of the temperature. The vapor pressure is compared to the one of Al(CH3)3 (TMA).
> **This precursor is commonly used for ALD of Al2O3.**"

This figure plots a *precursor property*. No film is deposited in it and no stack exists.
The resolver itself already refuses: both Fig 1 entities carry `material = None`,
`material_scope_level = unresolved`.

**Responsible rule.** `pilot_roles._ROLE_PATTERNS`, the DEPOSITED pattern
`(?:ALD|atomic layer deposition|…)\s+(?:of\s+|the\s+)?…({M})`. It fires on
"ALD **of SiO2**" and "ALD **of Al2O3**" inside a sentence about what each precursor is
*used for*. `pilot_semantics.build()` then copies the result into `scope_materials` on every
candidate of that scope, and `_case()` unions it into `context_materials` / `material_roles`.

Two independent defects:
1. a purpose clause ("used for ALD of M") is read as a deposition;
2. a scope that reports no film result is allowed to assert a material at all.

**Minimal generic correction.**
* Guard the DEPOSITED patterns against governing purpose phrases (`used for`,
  `commonly used for`, `suitable for`, `can be used for`, `typically used`) — a statement
  about what a chemical is *for* is not a record of a deposition.
* Assert figure-scope materials only when the scope reports a **film-or-process result**.
  A measurand that is a property of a *species* rather than of a *film*
  (`vapor_pressure`, `molar_mass`, `molecular_diameter`, …) marks a precursor-property
  scope; such a scope contributes material **candidates**, never asserted roles.
* Precedence made explicit and enforced in one place:
  `figure/panel/result-local > explicit sample/case text > local section >
  paper-wide inventory (CANDIDATE only)`.

---

## C. `deposited_material = null` while DEPOSITED roles are asserted

**Current wrong output.** 6 of 26 JES cases are in this state (see B).

**Responsible rule.** `pilot_semantics._case()` computes `mats` from the members'
`deposited_material` but computes `roles` from `context_materials`, which is the union of
`mats` **and** `scope_named`. The two are never reconciled, so a case with no resolved
deposit can still publish `{M: DEPOSITED}`.

**Minimal generic correction.** `_case()` gains one reconciliation step: a role is
**asserted** only for a material with local evidence of the required strength; everything
else moves to `material_candidates` with `material_status = CANDIDATE_ONLY`. When no
material is asserted, `deposited_material` stays `None`, `material_roles` is empty, and
`material_status = UNRESOLVED` carries the reason.

---

## D. Author-declared Series definitions overridden by a column heuristic

**Current wrong output**

```
Series E  varied_variable = pillar_layout            role = UNRESOLVED
Series F  varied_variable = pulse_purge_sequence     role = CASE_DEFINING
```

**PDF ground truth** — Table 1 footnote a:

> "Different pillar layout design for **Series A**; reflectometer magnification for
> **Series B**; design channel height for **Series C**; ALD cycles for **Series D**;
> **TMA pulse time for Series E**; and **purge time for Series F**."

**Responsible rule.** `pilot_semantics.table_series_variable()` decides a series' variable
by finding the one tabulated column that differs across its members, and returns
`(None, UNRESOLVED, …)` when more than one differs. Series E's specimens 12/13/14 differ in
BOTH the pulse-purge sequence and the pillar layout (specimen 14 is `v2a`), so the heuristic
abstains — and the abstention overrides an explicit author statement. Series F resolves to
the composite `pulse_purge_sequence` string rather than to the purge time.

**Minimal generic correction.** A new `series_definitions_from_text()` parsing the generic
construction `<variable phrase> for Series <X>`, semicolon-separated, from the document.
Precedence becomes **author definition > caption/prose > column differencing**. The column
heuristic is retained but demoted, and any column that varies without being the declared
variable is preserved separately as `co_varying_context` — Series E keeps its pillar-layout
co-variation without losing its declared primary variable.

---

## E. Value-joinable specimen mapping left unmade

**Current wrong output** — all three Fig 7 measurements bind to one specimen:

```
Fig7a exp01  series 'X5 (50 µm)'   performed_on  S::…::6
Fig7a exp02  series 'X10 (25 µm)'  performed_on  S::…::6
Fig7a exp03  series 'X50 (5 µm)'   performed_on  S::…::6
```

**PDF ground truth** — Table 1's reflectometer-magnification column: specimen 4 = 50,
specimen 5 = 10, specimen 6 = 5. The curve legends name the objective outright:
`X50`, `X10`, `X5`. The methods add the spot sizes: 50× → 5–6 µm, 10× → 25 µm, 5× → 50 µm.

The first pass called this "guessing by list order". It is not: the legend carries the
**value**, and the value identifies the row.

**Responsible rule.** `pilot_semantics.build()` binds specimens with
`PE.sample_codes(clause) or PE.sample_codes(preamble)`, i.e. only by an explicit code. The
caption names 4, 5 and 6 collectively, so all three attach to every curve and
`performed_on` is then overwritten to the last one. There is no value-based join anywhere.

**Minimal generic correction.** `value_join_specimen()`: extract the numbers a legend
carries (`X50` → 50, `(5 µm)` → 5) and match them against the specimen-table column for the
series' declared variable. A join is accepted only when it is **unique and total** — one
specimen per curve, every curve distinct. Ambiguity leaves the binding unresolved, as
before. The magnification value and its methods-derived spot size are attached as
`MEASUREMENT_SETTING`s.

---

## F. Run-distinctness evidence counted as DepositionRun instances

**Current wrong output**

```
deposition_runs = 3
  RUN::…::01     SHARED_RUN     samples ['1','2','3']     <- a real run
  RUNSET::…::02  DISTINCT_RUNS  samples []                <- an assertion, not a run
  RUNSET::…::03  DISTINCT_RUNS  samples []                <- an assertion, not a run
```

**PDF ground truth.** Only one process execution is identifiable: "All of the films were
grown in the same ALD run…(Series A in Table 1)". Fig 8b's "reproducibility of ALD runs …
on various LHAR channels" asserts that several runs exist but names none of them.

**Responsible rule.** `pilot_semantics.deposition_runs()` emits one object per linkage
statement and puts both kinds in the same list; `run_pilot.pilot_counts()` reports
`len(o["deposition_runs"])` as `deposition_runs`.

**Minimal generic correction.** Split the output: `deposition_runs.json` holds only
identifiable executions (those with at least one specimen or an explicit run designator);
a new `run_evidence.json` holds distinctness assertions. Counts, comparison artifacts and
the HTML report the two separately, so "3 runs" can no longer be read off a mixed list.

---

## G. Characterization disconnected despite explicit produced-sample provenance

**Current wrong output.** All five c7ta measurements have `measures_case = []`.

**PDF ground truth** — multi-electrode array section:

> "The **tubular** Pt Zeotile-4 replica was dispersed in demineralized water … The resulting
> suspension **was deposited on the test electrodes** … by micropipetting 1 µL drops five
> times per electrode."

followed by impedance spectroscopy and cyclic voltammetry on that array (printed Fig 8). The
chain is stated: tubular-replica synthesis → replica material → coated electrode → Fig 8.

For printed Fig 7 (HER) the source says only "**The** replica was deposited on precleaned
platinum support", without distinguishing the full from the tubular protocol.

**Responsible rule.** There is no provenance-chain mechanism at all. `discover_links()` has
three rules — shared specimen code, explicit same-statement citing a figure, enumerated
caption settings — and none links a characterisation result to a synthesis case through a
produced material.

**Minimal generic correction.** `produced_material_chain()`: find sentences stating a
produced material being placed on a measurement substrate/electrode/support, take the
qualifier identifying WHICH product ("tubular"), and match it against the labels of the
text-supported cases. The link is made only when the qualifier identifies exactly one case;
otherwise the chain is recorded and the final hop stays `PROVENANCE_CHAIN_INCOMPLETE`.
Series legends naming a bare/uncoated/reference condition are typed `REFERENCE` and are
never attached to a deposition case.

---

## H. Measurement-only figures minting deposition cases

**Current wrong output.** JES printed Fig 1 (precursor vapor pressure) yields two
ExperimentalCases; the same class of error is what makes am's Fig 4 device panels a risk.

**Responsible rule.** `pilot_semantics.build()` mints a case candidate for every entity
whose class is not in `NON_EXPERIMENTAL`, regardless of whether the result reports anything
about a deposited film.

**Minimal generic correction.** A scope that measures a **species property** rather than a
film or process outcome yields a Measurement and a ResultSeries but no case candidate, with
the reason recorded. This is the same gate that fixes B, applied to case minting as well as
to material assertion.

---

## I. High-aspect-ratio geometry recoverable after all (first-pass escalation E1)

**First-pass conclusion.** "No per-case geometry evidence in the snapshot" — the HAR figures
were said to be absent from the extracted set.

**PDF ground truth** — printed Figure 8 caption:

> "High-resolution SEM images of a **high-aspect ratio trench** in Si coated by **830 cycles**
> of ALD SiO2. The SiO2 was deposited on top of thermal SiO2/ALD Al2O3 layers for optical
> contrast. The depth and average width of the trench were **18.5** and **0.6 µm**,
> respectively, resulting in an **aspect ratio of ~30**."

That is a complete deposition case: material, cycle count, geometry class and geometry
quantities — carried by an SEM image rather than an x-y curve.

**Responsible rule.** `pilot_supplements.missing_panels()` rejects any clause matching
`_NON_PLOT` ("SEM images"), so an image-only figure can never contribute anything. The
first-pass escalation was therefore a limitation of the supplement rule, not of the source.

**Minimal generic correction.** Extend the supplement path: a caption that reports a
**deposition on a described structure** with at least one case-defining condition yields an
image-supported ExperimentalCase plus a characterisation Measurement, with
`data_recovered: false` and no invented points. Geometry comes from the
`pilot_roles.geometry_in_scope()` already in place; geometry quantities (depth, width,
aspect ratio) are parsed by the new range/scalar parser.
