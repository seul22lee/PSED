# Second-pass change log

One row per corrected bug. "Generic" means the rule names no paper, DOI or figure —
`tests/test_pilot_semantics.py` invariant 16 checks that mechanically over `code/`.

---

## A — a numeric range read as a negative scalar

**PDF.** "…ultrashort doses **(10-120 ms)**…"; "…alternating layers … deposited using
**10-40 cycles** each."
**Old.** `pulse_time = -120 ms`, `cycle_number = -40 cycle`, both `directly_stated`.
**New.** `value_kind: range`, `value_lower/upper = 10/120` and `10/40`, the misread scalar
kept as `superseded_value` with a `value_repair` note.
**Changed.** New `code/pilot_ranges.py` (`parse_interval`, `sign_is_physical`,
`repair_condition`, `repair_all`, `quantities_from_text`); `pilot_semantics.build` repairs
every inherited condition; `_case` prefers a repaired interval over a scalar of the same key.
**Generic because** it re-reads each condition's OWN evidence and applies a sign rule
driven by a whitelist of genuinely signed quantities — a potential of −0.5 V still parses.
**Tests.** invariant 17; `jes: a stated interval is carried as an interval…`;
`jes: no negative pulse time or cycle count survives`.

## B — paper-wide material inventory leaking into a local scope

**PDF.** Printed Fig 1 is the vapour pressure of the SAM.24 precursor, "used for ALD of
SiO2 … commonly used for ALD of Al2O3". No film is grown in it.
**Old.** Two cases, `context_materials ['Al2O3','SiO2']`, both `DEPOSITED`,
`multi_material_context = true`.
**New.** No case, no material role; the curves survive as Measurements + ResultSeries.
**Changed.** `pilot_roles._is_purpose_clause` guards the DEPOSITED patterns;
`pilot_roles.is_species_property` marks a scope that measures a property of a chemical;
`pilot_semantics.build` skips case minting and material assertion for such a scope.
**Generic because** the guard is a purpose-phrase test and a measurand test, not a figure
number. It also stops a device-cycling caption from contributing an ALD cycle count.
**Tests.** `jes: printed Fig 1 … is not a deposition case`; `jes: Fig 1 is still preserved
as Measurements`; invariant 19.

## C — `deposited_material = null` while DEPOSITED roles asserted

**Old.** 6 of 26 JES cases published `{Al2O3: DEPOSITED, SiO2: DEPOSITED}` with a null
deposit.
**New.** `_case` separates **asserted** roles (local evidence) from **candidates**
(paper-wide inventory only) and publishes `material_status` ∈ ASSERTED / CANDIDATE_ONLY /
UNRESOLVED with its reason. A stack legitimately has no single deposit and says so.
**Changed.** `pilot_semantics._case`.
**Generic because** the split is by evidence scope, not by material name.
**Tests.** invariants 18 and 19.

## D — author-declared Series overridden by a column heuristic

**PDF.** Table 1 footnote a: "…**TMA pulse time for Series E**; and **purge time for
Series F**."
**Old.** Series E `pillar_layout` / UNRESOLVED; Series F the composite
`pulse_purge_sequence`.
**New.** E → `pulse_time`, F → `purge_time`, both `varied_variable_source:
author_declaration`. E keeps `co_varying_context: [pulse_purge_sequence, pillar_layout]`.
**Changed.** New `series_definitions_from_text` and `table_co_variation`; the series block
applies author > prose > column differencing.
**Generic because** it parses the construction `<variable phrase> for Series <X>`.
**Tests.** six `yim: Series X primary variable…` anchors, plus the source and co-variation
anchors.

## E — a value-joinable specimen mapping left unmade

**PDF.** Table 1: specimen 4 = 50×, 5 = 10×, 6 = 5×. Fig 7 legends: X50, X10, X5.
**Old.** All three measurements bound to specimen 6.
**New.** X50 → 4, X10 → 5, X5 → 6, `specimen_binding: value_join`; each carries its
magnification as a MEASUREMENT_SETTING plus the methods spot size (5–6 / 25 / 50 µm).
**Changed.** New `legend_values`, `value_join_specimens`, `build_value_joins`,
`instrument_setting_map`; `_clean` now maps the `/C2` glyph to `×`.
**Generic because** it matches the legend's VALUE against the table column of the series'
declared variable, ignores legend numbers carrying a unit the column does not use, and
accepts only a unique total assignment. Not list order.
**Tests.** three `yim: Fig 7 X… maps to specimen …`; `that mapping is a value join, not
list order`; the settings and spot-size anchors.

## F — run-distinctness evidence counted as DepositionRun instances

**PDF.** One identifiable execution ("All of the films were grown in the same ALD run",
Series A). Fig 8b asserts several runs and names none.
**Old.** `deposition_runs = 3`.
**New.** `deposition_runs = 1` (specimens 1/2/3) and a separate `run_evidence.json` with 2
assertions. Counts, comparison artifacts and the HTML report the two separately.
**Changed.** `pilot_semantics.build` splits the list; `run_pilot.pilot_counts` reports
`identified_deposition_runs` and `run_evidence_groups`; `build_report` renders them apart.
**Generic because** the test is structural: a DepositionRun must name at least one specimen.
**Tests.** invariant 20; `yim: exactly one IDENTIFIED DepositionRun exists`;
`run-distinctness assertions are NOT counted as runs`.

## G — characterisation disconnected despite explicit produced-sample provenance

**PDF.** "The **tubular** Pt Zeotile-4 replica was dispersed … The resulting suspension was
deposited on the **test electrodes** … by micropipetting". Fig 7's section says only
"**The** replica".
**Old.** All five c7ta measurements had `measures_case = []`.
**New.** Fig 8 coated impedance and Fig 8(b) CV → the tubular case; bare/uncoated →
`REFERENCE`, attached to nothing; Fig 7 coated → `CASE_UNRESOLVED`, chain shown stopping.
**Changed.** New `produced_material_chain`, `is_reference_series`,
`_figures_naming_product`, `_stem`, `_sentences`; a `provenance_chains.json` output;
text cases gained a `synthesis_label` from their "for the creation of X" phrase.
**Generic because** a chain applies only to figures whose OWN caption names the product
(material + form), and only when the qualifier identifies exactly one synthesis case.
**Tests.** the seven `cta:` provenance anchors.

## H — measurement-only figures minting deposition cases

Same fix as B: a species-property scope yields a Measurement and a ResultSeries but no
case. **Tests.** `jes: printed Fig 1 …`; `am: Figure 4 device characterisation mints no
deposition case`.

## I — high-aspect-ratio geometry (first-pass escalation E1, now resolved)

**PDF.** "High-resolution SEM images of a **high-aspect ratio trench** in Si coated by
**830 cycles** of ALD SiO2 … depth and average width … **18.5** and **0.6 µm** …
**aspect ratio of ~30**."
**Old.** No case; the first pass concluded the evidence was absent.
**New.** An image-supported case with `geometry: vertical_structure` **from the figure
caption**, SiO2 DEPOSITED, 830 cycles, AR 30, depth 18.5 µm, width 0.6 µm,
`data_recovered: false`, zero points claimed.
**Changed.** `pilot_supplements.image_supported_cases` + `DEPOSITION_HINTS`;
`pilot_ranges.quantities_from_text` rewritten to prefer the tail and to handle the
"A and B … were x and y, respectively" construction; the number boundary fixed so a
trailing full stop no longer hides a value ("~ 30.").
**Generic because** the rule is: a caption reporting a deposition on a described structure,
with a deposited material and at least one process condition. The material requirement is
what stops a device-cycling caption ("stability … for over 10 000 cycles") from becoming
an ALD case.
**Tests.** the six `jes:` HAR anchors, plus `planar and HAR contexts coexist`.

---

## Also changed, in service of the above

| file | what | why |
|---|---|---|
| `pilot_semantics._sentences` | abbreviation-aware sentence splitting | "For the creation of the full replica (Fig. 3), …" was torn in two at "Fig.", separating a process variant from the product it makes |
| `pilot_semantics._clean` | `/C2` → `×` | the objective magnification is written "50 /C2" in the markdown export |
| `pilot_semantics` unresolved records | `reason_class` on every record | an unresolved link is a classified state, not a failure count |
| `run_pilot` | `unresolved_links_second_pass.csv`, `identified_deposition_runs`, `run_evidence_groups`, `provenance_chains` | §27 and §38 |
| `build_report` | PDF-ground-truth check block, material-provenance cell, condition value-kind/provenance tags, run split, provenance-chain view, series source + co-variation columns | §32–§38 |
| `tests/test_pilot_semantics.py` | 4 new generic invariants; the paper anchors rewritten against the PDFs | §28 |

## Preserved untouched

Source ids, `curve_id`, point counts, `data_source`, SimulationRun separation,
imported-literature and transformation provenance, "missing ≠ same", contradiction blocks
merge, positive-evidence requirement, ExperimentalCase/Measurement/PlotRepresentation
separation, optional Sample and DepositionRun, the self-contained HTML approach.
