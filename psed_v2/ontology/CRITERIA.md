# PSED v2 — Ontology v0 Criteria

Managed in the chat, like `PSED_v2_Plan.md`. Claude Code reads it and never edits it.
Ground rule for everything below: **simple is best**. When in doubt, leave it out and record it as native.

## 0. What to build

```
psed_v2/ontology/
  CRITERIA.md       this file (from the chat)
  ontology.yaml     the ontology: one file, every entry, every relation, every deviation from the base
  unmapped.csv      gold-paper labels that did not become entries, with the reason
  make_report.py    one command: ontology.yaml + unmapped.csv -> report.html
  report.html       completion report with visualization (generated; committed separately)
  sources/          base inputs, not in git: 2 review PDFs + schema-miner JSON
```

The ontology is the vocabulary of a future knowledge graph. Every entry becomes a graph node, and every relation in Sec. 9 becomes an edge. Gold-table rows (experiments, series, conditions, points) will later be instance nodes that point to these ids. Nothing in this task builds the graph itself.

## 1. Two layers

**Base layer.** The starting point, not the truth. It comes from three sources, fixed by version:

| Source | Version | Contributes |
|---|---|---|
| schema-miner ALD **experimental** schema | `sciknoworg/schema-miner` commit `13c47dc`, `results/Ideal Schema/Atomic-Layer-Deposition/experimental-ideal-schema.json` | field names and the list of process and film fields |
| Cremers 2019 (Appl. Phys. Rev. 6, 021302) | published | conformality definitions: Sec. I, Sec. II A–H, Sec. III + Table I, column headers of Tables II–V and VII, Sec. V A |
| Popov 2025 (JVST A 43, 030801) | published | Reactant A/B naming (Table I), material classes (Fig. 5, Sec. II B), precursor ligand classes (Figs. 7–8), source temperature (Sec. IV) |

Not used: the schema-miner simulation schema, the ALE schemas, and schema-miner's QUDT mappings. No species, structures, or processes are taken from any review table.

**Extension layer.** Entries the three gold papers need as data that the base does not provide:

- Yim 2020 (`10.1039_d0cp03358h`)
- Ylilammi 2018 (`10.1063_1.5028178`)
- Werbrouck 2021 (`10.1116_6.0001094`)

Gold PDFs are in `psed_v2/gold/pdf/`.

**Precedence.**
- Definitions: Cremers / Popov > gold papers > schema-miner.
- Names: schema-miner first, unless a definition problem or ambiguity requires another name.
- Every departure from a base source is recorded (Sec. 3).

## 2. Entry fields

```yaml
- id:         snake_case, unique across the whole file, never renamed
  type:       quantity | categorical | species | structure | model
  origin:     base | extension
  role:       condition | output | model_parameter | coordinate     # quantities and categoricals
  category:   a leaf node id of the hierarchy (Sec. 17)             # quantities, categoricals, models
  definition: one or two sentences; review wording where a review defines it
  symbol:     as in Cremers, if defined there
  dimension:  e.g. temperature, length, length_per_cycle, dimensionless
  unit:       canonical unit (Sec. 6)
  qualifiers: [keys from Sec. 5]
  aliases:    [exact strings seen in the five papers or the base JSON]
  base:       {source, path or section}          # where the entry came from; empty for extension
  deviation:  {type, reason}                     # only if it differs from its base source
  evidence:   [gold locations where it carries data, e.g. "Yim2020 Fig. 9c"]
```

`evidence` empty means the entry is defined but not used. It is not an extraction target and is not scored.

Categorical entries (values are text or ids, no unit) are `type: categorical`: process_mode, material, reactant_A, reactant_B, carrier_gas, reactor, delivery_method, structure, plasma_configuration, reactor_type, crystallinity (role output). They are not counted as quantities. Each categorical adds `values_from` (Sec. 6, value canonicalization).

Species add `kind` (molecule | material | atom), `formula`, and `material_class, n_elements, ligand_class` (only when a review states the class). Structures add `class`. Models add `model_type, parameters, reference`. Do not add any other field.

## 3. Deviations from the base

Seven deviation types: `renamed, redefined, split, merged, role_changed, unit_changed, dropped`.

Every one of the 30 leaf fields of the schema-miner experimental schema must end up in exactly one of three places:
- an entry with `base.path` and no deviation,
- an entry with `base.path` and a deviation,
- the `excluded_base` list with a reason.

Expected mapping. Claude Code confirms each row or reports why not.

| schema-miner path | Our entry | Deviation |
|---|---|---|
| ALDSystem/ALDMethod | process_mode (categorical) | renamed |
| ALDSystem/MaterialDeposited | material (categorical) | renamed |
| ReactantSelection/Precursor | reactant_A (categorical) | renamed: Popov Table I, Cremers Sec. I |
| ReactantSelection/CoReactant | reactant_B (categorical) | renamed: same |
| ReactantSelection/CarrierGas | carrier_gas (categorical) | — |
| ProcessParameters/Reactor/Name | reactor (categorical) | merged with Manufacturer |
| ProcessParameters/Reactor/Manufacturer | reactor | merged |
| ProcessParameters/DeliveryMethod | delivery_method (categorical) | — |
| ProcessParameters/Temperature | deposition_temperature | renamed: several temperatures exist (Sec. 7) |
| ProcessParameters/Pressure | process_pressure + partial_pressure | split: Cremers Sec. II D, reactant partial pressure sets exposure |
| ThicknessControl/GrowthPerCycle | growth_per_cycle | role_changed: an outcome, not a process parameter |
| ThicknessControl/saturation | excluded_base | dropped: a judgment, not data |
| ThicknessControl/nucleationPeriod | nucleation_period | role_changed: outcome |
| ThicknessControl/DosingTime/{Precursor, CoReactant} | pulse_time{step} | renamed: Cremers and all gold papers say "pulse time"; the two fields become one entry with a qualifier |
| ThicknessControl/PurgeTime/{Precursor, CoReactant} | purge_time{step} | merged into one entry with a qualifier |
| OpticalProperties/RefractiveIndex | refractive_index | — |
| OpticalProperties/AbsorptionCoefficient | absorption_coefficient | redefined: unit 1/m (their QUDT kind, Transmittance, is a different quantity) |
| ElectricalProperties/Resistivity | resistivity | — |
| ElectricalProperties/CarrierDensity | carrier_density | redefined: number density, 1/m³ (not charge density) |
| ElectricalProperties/Mobility | mobility | — |
| Uniformity/Variation | thickness_nonuniformity | renamed; definition from Cremers Sec. II A (uniformity on a planar substrate) |
| Conformality/AspectRatio | aspect_ratio + coated_aspect_ratio | split: Cremers Sec. II G–H, structure AR ≠ AR reached by the coating |
| MaterialProperties/ChemicalComposition | composition{element} | redefined: a quantity in at.%, not free text |
| MaterialProperties/Crystallinity | crystallinity (categorical: amorphous, crystalline) | — |
| MaterialProperties/FilmDensity | film_density | — |
| OtherAspects/Safety, FilmStability, Reproducibility | excluded_base | dropped: not data in papers |
| all QUDT annotations | not used | dropped: several are wrong (GrowthPerCycle → Length, AbsorptionCoefficient → Transmittance) |
| all fixed per-field units (e.g. ms) | canonical unit + raw unit kept | unit_changed |

The same rule applies to Cremers and Popov: if we do not follow a review's definition, record a deviation.

## 4. Inclusion gate and the distinguishing rule

**A new extension entry needs all four:**
1. It is a physical quantity (value with a dimension, or a defined ratio).
2. It carries data in a gold paper (plotted axis, table column, or condition with a value).
3. A competency question (Plan CQ1–11) needs it, directly or as transform context.
4. No existing entry plus a qualifier already covers it.

**Never an entry (stays native):**

| Kind | Examples |
|---|---|
| Interpretations, regimes | diffusion / reaction / recombination limited; molecular / viscous flow; Yim Regions I–IV, nanostep, knee |
| Instrument settings | reflectometer magnification, spot size, integration time, accelerating voltage |
| Molecule properties | molar mass, molecular diameter, mean free path, vapor pressure |
| Derived dimensionless groups | Knudsen, Damköhler, Thiele |
| Plasma internals | electron temperature, OES intensities and ratios, ion energy, m/z counts |
| Fit quality | R², rms error |
| Signals without a quantity | counts/s, a.u., EDS intensity |
| Model internals not in Sec. 8 | Ylilammi q, Pd, pB; Werbrouck dimensionless exposure Ψ, s0 site area |
| Equipment details and sample codes | pillar layout, gas inlet position, sample numbers |

**Same entry, qualifier, or new entry.** Two labels are the same quantity if and only if the definition, the dimension, and the reference are all the same.

| Situation | Decision | Example |
|---|---|---|
| Same definition, different wording | add alias | "pulse length" = pulse_time |
| Differs only in which species / step / position / reference | qualifier | pulse_time{step: reactant_A} |
| Same word, different definition | separate entries; the word goes to `ambiguous_aliases` | "coverage" |
| Different dimension | separate, always | Werbrouck Ψ (dimensionless) ≠ exposure (Pa·s) |
| Model parameter vs. the observed quantity | separate | saturation_growth_per_cycle ≠ growth_per_cycle (Ylilammi Eq. 46) |
| Value obtained by a fit | same entry; `data_kind = fit` in the gold table | Werbrouck p_O → partial_pressure{species: O} |

Never put a species, a step, or a position in an id (no `tma_pulse_time`, `gpc_inside`).

## 5. Qualifiers (closed lists; adding a value is allowed and is logged)

| Key | Values | Source |
|---|---|---|
| step | reactant_A, purge_A, reactant_B, purge_B | Cremers Sec. I four steps; Popov Reactant A/B |
| species, gas | species ids | — |
| element | element symbols | composition |
| position | planar, top, sidewall, bottom | Cremers Fig. 7. LHAR: outside the channel = planar; channel entrance = top |
| reference | top, planar, assumed_saturation | normalized_thickness denominator |
| level | 50%, 80% | Cremers PD50%, PD80% |
| basis | AR, EAR | Cremers Sec. II G |
| surface | material ids | recombination depends on the surface |

`process_pressure` takes `step` when a paper gives different pressures per step (Werbrouck: TMA step vs plasma step).

For a plasma step, `pulse_time{step: reactant_B}` is the plasma-on time. Gas-only sub-steps are native.

## 6. Units, canonicalization, normalization

**Units**
1. The gold tables always keep `raw_value` and `raw_unit` exactly as printed. Conversion happens only in the pipeline's `normalize` step, never in extraction.
2. Never infer a missing unit.
3. Canonical units:

| Dimension | Canonical | Accepted |
|---|---|---|
| temperature | °C | °C, K (affine: °C = K − 273.15) |
| time | s | ms, s, min |
| pressure | Pa | Pa, hPa, mbar, Torr, mTorr |
| exposure | Pa·s | Pa·s, Torr·s, L (1 L = 10⁻⁶ Torr·s = 1.333×10⁻⁴ Pa·s, Cremers Sec. II D) |
| film thickness | nm | pm, Å, nm, µm |
| position, geometry | µm | nm, µm, mm, cm, m |
| growth per cycle | nm/cycle | pm/cycle, Å/cycle, nm/cycle; "/cycle" is never dropped |
| power | W | W |
| gas flow | sccm | sccm |
| ratio, fraction, composition | 1 | 1, %, at.% |
| density | g/cm³ | g/cm³, kg/m³ |
| resistivity | Ω·m | Ω·m, Ω·cm, µΩ·cm |
| inverse pressure | 1/Pa | 1/Pa, 1/mbar |

4. a.u. and counts are not convertible.
5. "ca.", "~", "about" → `condition_status = approximated`. Ranges → min and max.

**Canonicalization** = mapping a printed label to an entry id. It happens by definition, not by string. An alias match is only a candidate. Words in `ambiguous_aliases` always need the definition from the paper.

**Value canonicalization** = mapping a printed categorical value to a canonical value. Every categorical names where its values come from:

| Categorical | values_from | Current values |
|---|---|---|
| material | species with kind = material | al2o3, tio2 |
| reactant_A, reactant_B, carrier_gas | species with kind = molecule | tma, ticl4, h2o, o2, n2 |
| structure | structure entries | pillarhall_3, macroscopic_lateral_trench, planar |
| process_mode, plasma_configuration, reactor_type, crystallinity | fixed list + `value_aliases` (Sec. 12) | see Sec. 12 |
| reactor | free text, written as "manufacturer model" or "home-built" | Picosun R-150, home-built |
| delivery_method | free text; no gold evidence yet | — |

Value aliases live with the value, never with the key: species and structure aliases are in their entries; fixed-list aliases are in `value_aliases`. A key's `aliases` holds only names of the key ("Precursor", "CoReactant").

Matching rule, nothing else:
1. Normalize both strings: lowercase; remove spaces, hyphens, ®, ™; subscript digits → digits; "aluminium" → "aluminum".
2. Map only on an exact match with an alias. No fuzzy or similarity matching. Formula variants are listed as aliases (AlMe3, Me3Al, (CH3)3Al), never derived by parsing formulas.
3. No match → keep the raw text and flag it `unmatched_value`. A new species or structure is added only when a gold paper uses it (Sec. 11).
4. One alias may set two fields when the paper's notation joins them: "O2*", "O2 plasma" → reactant_B = o2 and process_mode = plasma. These are listed in `value_aliases.joint`.

**Normalization** = the transforms in Sec. 9. A transform runs only when every input it needs is stated for the same experiment. Otherwise the value stays as reported.

## 7. Temperature

Exactly one temperature entry carries data: `deposition_temperature`. Definition: the substrate/reactor temperature during film growth (Cremers Eq. 3 and Table II "T"). Bare "temperature" or "T" maps to it only when the sentence is about the deposition.

| Temperature | Decision |
|---|---|
| deposition temperature | entry (gold: all three) |
| precursor source temperature (bubbler, canister) | base entry `source_temperature` (Popov Sec. IV), no gold evidence |
| ALD window | not an entry; a min/max range of deposition_temperature |
| model input temperature (Ylilammi T = 500 K, Yim Fig. 10 T = 300 °C) | deposition_temperature on the simulation series |
| gas temperature, electron temperature | native |
| measurement, annealing, decomposition temperature | native; only via Sec. 11 |

## 8. Species, structures, models

**Species**: only those in the gold papers.
- Identity is formula plus names. `kind`: molecule (gas-phase reactants and gases), material (deposited films), atom (plasma species such as O).
- Aliases cover every spelling in the five papers plus the standard variants of the same name and formula (e.g. tma: TMA, trimethylaluminum, trimethylaluminium, Al(CH3)3, AlMe3, Me3Al, (CH3)3Al; al2o3: Al2O3, alumina, aluminum oxide, aluminium oxide).
- **Role (reactant_A, reactant_B, carrier_gas, purge_gas) is a categorical condition, not a species property.**
- O2 plasma = species O2 + `process_mode = plasma`.
- Plasma species (O) become species only when a gold value is attributed to them.
- `material_class` (Popov Fig. 5): oxide, chalcogenide, element, pnictogenide, halide, carbon_group, boron_group.
- `n_elements` (Popov Sec. II B): element, binary, ternary, quaternary.
- `ligand_class` (Popov Figs. 7–8): metal precursors only. TMA → alkyl, TiCl4 → halide.

**Structures**: only those in the gold papers. `class` follows Cremers Sec. III / Table I: lateral, vertical, porous, planar.
- pillarhall_3 → lateral
- macroscopic_lateral_trench → lateral
- planar → planar

**Models** (`model_type`: analytical | computational, Cremers Sec. V A):

| id | type | parameters | used in |
|---|---|---|---|
| ylilammi_diffusion_reaction | analytical (Cremers Sec. V A 1) | initial_sticking_coefficient, adsorption_equilibrium_constant, saturation_growth_per_cycle, partial_pressure | Ylilammi Figs. 2–7, Yim Fig. 10 |
| gordon_plug_flow | analytical | — | Ylilammi Fig. 5 |
| yanguas_gil_markov_chain | computational | initial_sticking_coefficient, recombination_probability | Werbrouck Figs. 11–14 |
| arts_slope | analytical | initial_sticking_coefficient | Yim Table 2 |

## 9. Relations between entries (compact; these are the only edges)

| Edge | From → to | Written as |
|---|---|---|
| derives | input quantities → output quantity | `transforms` |
| parameter_of | quantity → model | model `parameters` |
| qualified_by | quantity → qualifier key | quantity `qualifiers` |
| member_of | species / structure → class value | `material_class`, `ligand_class`, `class` |
| deviates_from | entry → base path | `base` + `deviation` |

Transforms (the variable relations; each names its inputs, so the graph edge is explicit):

```yaml
transforms:
  - {id: unit_conversion,     inputs: [any],                       output: same,                   formula: "unit table, Sec. 6"}
  - {id: thickness_to_gpc,    inputs: [film_thickness, cycle_number], output: growth_per_cycle,    formula: "d / N"}
  - {id: x_over_width,        inputs: [distance, feature_width],   output: dimensionless_distance, formula: "x / w"}
  - {id: normalize_thickness, inputs: [film_thickness, film_thickness{position=reference}], output: normalized_thickness, formula: "d(x) / d_ref"}
  - {id: aspect_ratio,        inputs: [feature_depth, feature_width], output: aspect_ratio,        formula: "L / w  (Cremers Eq. 11)"}
  - {id: coated_ar,           inputs: [penetration_depth, feature_width], output: coated_aspect_ratio{basis=AR}, formula: "PD / w"}
  - {id: exposure,            inputs: [partial_pressure, pulse_time], output: exposure,            formula: "p * t  (Cremers Sec. II D)"}
  - {id: step_coverage,       inputs: [film_thickness{position=bottom}, film_thickness{position=top}], output: step_coverage, formula: "d_bottom / d_top"}
```

EAR is never computed. It is recorded as reported (its formula depends on the geometry).

**Geometry naming** (Cremers w, L, z for every structure):

| id | Cremers | LHAR (Yim, Ylilammi) | Werbrouck trench | vertical trench | hole |
|---|---|---|---|---|---|
| feature_width | w | channel height H | opening height 1 mm | width | diameter |
| feature_depth | L | channel length L | depth 20 mm | depth | depth |
| feature_extent | z | channel width W | width 10 mm | trench length | — |

`distance` is measured from the feature entrance, positive inward; outside the feature it is negative (Yim Region I).

## 10. Expected entries

Claude Code confirms each with evidence or reports why not. `ev` = has gold evidence.

**Base, from schema-miner**
- With gold evidence: deposition_temperature, process_pressure, pulse_time, purge_time, growth_per_cycle, aspect_ratio, coated_aspect_ratio.
- Without gold evidence: nucleation_period, refractive_index, absorption_coefficient, resistivity, carrier_density, mobility, thickness_nonuniformity, composition, film_density.

**Base, from Cremers / Popov**
- With gold evidence: film_thickness, penetration_depth, equivalent_aspect_ratio, initial_sticking_coefficient, recombination_probability, partial_pressure, surface_coverage, feature_width, feature_depth, feature_extent.
- Without gold evidence: exposure, step_coverage, source_temperature.

**Extension (gold)**: cycle_number, plasma_power, gas_flow_rate, normalized_thickness, adsorption_equilibrium_constant, saturation_growth_per_cycle, distance, dimensionless_distance, time.

Cap: extension ≤ 15. Base entries are exactly the ones listed here plus the categorical keys in Sec. 12. Anything else is a stop-and-report.

Note on initial_sticking_coefficient: Ylilammi's "lumped sticking coefficient c" multiplies (1 − θ) (Eq. 11), so it equals Cremers s0 (Eq. 5). Check Yim cTMA and Werbrouck's fitted sticking probability against their equations, and report any mismatch.

## 11. Decision procedure for a later technical paper

For each label carrying data:
1. Matches an entry by definition → map it; add an alias if the wording is new.
2. Differs only by a qualifier → existing entry + qualifier value.
3. Matches a base entry without evidence → add the evidence (it becomes an extraction target). Log it.
4. In the "never an entry" table → native.
5. Otherwise → native. Promote to a new extension entry only if it carries data in ≥ 2 papers, a CQ needs it, a definition can be cited, and the expert approves.
6. A word that now has two definitions → move it to `ambiguous_aliases`.

Ids are frozen from the start of the Ylilammi gold pilot (the v0 rename gap → feature_width is the last rename). After that, ids are never renamed or deleted; a merged entry gets `replaced_by: <id>`.

## 12. Fixed vocabularies

```yaml
panel_type:        [plot, image, schematic, table]
data_kind:         [measured, simulation, calculated, fit, cited]
  # first match wins: adjusted to measured data -> fit; any equation solved numerically -> simulation;
  # closed form evaluated -> calculated
series_structure:  [curve, per_point, image]
experiment_kind:   [sample, in_situ_run, plasma_measurement, cited]   # experiment count = sample + in_situ_run
condition_source:  [caption, methods, table, body]
condition_status:  [stated, approximated, inferred]
process_mode:      [thermal, ozone, plasma]                            # Cremers Sec. IV
plasma_configuration: [capacitive, inductive, remote, radical_enhanced] # Cremers Table IV
reactor_type:      [pump_type, flow_type, atmospheric]                 # Cremers Sec. II C
measurement_method: [reflectometry, spectroscopic_ellipsometry, xrr, optical_microscopy, sem, sem_eds, afm, oes, eqp]
categorical_conditions: [material, reactant_A, reactant_B, carrier_gas, structure, process_mode,
                         plasma_configuration, reactor_type, reactor, delivery_method]
value_aliases:
  process_mode:
    thermal: [thermal ALD, thermal]
    plasma:  [PEALD, PE-ALD, plasma-enhanced ALD, plasma-assisted ALD, plasma ALD]
    ozone:   [ozone-based ALD, O3-based]
  plasma_configuration:
    inductive: [ICP, inductively coupled, inductively coupled plasma]
    capacitive: [CCP, capacitively coupled]
    remote:    [remote plasma, remote]
  reactor_type:
    pump_type: [pump-type, vacuum-type]
    flow_type: [flow-type]
    atmospheric: [atmospheric pressure, AP-type]
  joint:
    "O2*":       {reactant_B: o2, process_mode: plasma}
    "O2 plasma": {reactant_B: o2, process_mode: plasma}
ambiguous_aliases:
  coverage:               [surface_coverage, normalized_thickness]   # Ylilammi Fig. 3 vs Werbrouck Figs. 11-12
  depth:                  [distance, feature_depth]                  # Werbrouck axis vs "depth 20 mm"
  temperature:            [deposition_temperature, native]
  pressure:               [process_pressure, partial_pressure]
  power:                  [plasma_power, native]
  sticking probability:   [initial_sticking_coefficient, native]     # Cremers Eq. 5: s vs s0
```

## 13. How to work

1. Read CRITERIA.md, the base JSON, and the listed review sections.
2. Build the base entries and the deviation records (Sec. 3).
3. Go through each gold paper figure by figure and table by table. For every label carrying data, apply Sec. 11:
   - add evidence to the matching entry,
   - or add an extension entry,
   - or write a row to `unmapped.csv`: `paper, location, label, unit, reason` (reason = a row name from the Sec. 4 table).
4. Run the checks (Sec. 15).
5. Write `make_report.py` and generate `report.html`.

No LLM API calls. Read the PDFs directly. Do not guess QUDT names or IRIs.

## 14. report.html

One self-contained HTML file (no external scripts, fonts, or network), generated by `python make_report.py`.

1. **Summary**: counts by type, origin, and with/without evidence; the extension cap; checks passed or failed.
2. **Graph** (inline SVG, drawn by the script, no library):
   - Quantity nodes in four columns by role (condition | coordinate | output | model_parameter).
   - Model nodes on the right.
   - Edges: `derives` (transforms) and `parameter_of`.
   - Fill: base = one color, extension = another. Entries without evidence are drawn faded.
   - Hovering a node shows its definition (SVG `<title>`).
2b. **Hierarchy**: the tree of Sec. 17 as an indented list; each node shows its definition, its review citation, and its entries.
3. **Entries**: one table grouped by category, with id, type, role, unit, origin, qualifiers, evidence, deviation. In the graph, nodes inside each role column are ordered by category, and the node label shows the category.
3b. **Values**: every categorical with its values_from, current values and value aliases.
4. **schema-miner diff**: all 30 leaf paths → entry and deviation type and reason, plus `excluded_base`.
5. **Units**: canonical unit per dimension and accepted units.
6. **Unmapped**: `unmapped.csv` grouped by reason, with counts.

Keep the script short. No styling beyond basic readable CSS.

## 15. Checks

1. Every schema-miner leaf path appears exactly once (as an entry `base.path` or in `excluded_base`).
2. Every entry has a definition. Where Cremers or Popov defines the term, the definition follows the review and cites it.
3. Every extension entry has gold evidence.
4. No alias in two entries. Ambiguous words appear only in `ambiguous_aliases`.
5. Extension ≤ 15. Base = the Sec. 10 list plus the Sec. 12 categorical keys.
6. Every transform input and output, and every model parameter, is an existing id.
7. No species, structure, or process taken from a review table.
8. Every quantity, categorical and model has exactly one category, and it is a leaf node of the hierarchy. Every hierarchy node has a definition and a review citation, and is not empty.
9. Every categorical has `values_from`; every species has `kind`; no value alias appears under two values (after the Sec. 6 normalization).
10. No orphan: every entry and every hierarchy node has at least one edge (Sec. 9 edges plus member_of and child_of).

## 16. Report back (≤ 15 lines)

Counts; every deviation from Sec. 3 or Sec. 10 that was not expected, with its reason; the initial_sticking_coefficient check result; the unmapped count by reason; the path to report.html.

## 17. Hierarchy (redesign task)

Entries are grouped under a small hierarchy so that every concept sits in one clear place and is linked to its neighbors. Design it yourself from the reviews. The tree below is **an example only**: use it to see the intended level of detail, not as the answer.

### What to read for this task

Read these closely (more than for Sec. 1):
- Cremers 2019 Sec. I–IV in full: the ALD cycle, every concept in Sec. II, the structure classification in Sec. III, and how Sec. IV and Tables II–IV describe one experiment (their columns).
- Cremers Sec. V C–D (model assumptions and outputs).
- Popov 2025 Sec. I–IV (what a "process" is, reactant naming, precursor requirements, source and deposition temperature).
- The schema-miner experimental schema's grouping (ALDSystem, ReactantSelection, ProcessParameters, MaterialProperties), as a reference to agree or disagree with.

### Rules

1. **Grounded.** Every node cites the review passage that uses that grouping (section, table, or a quoted phrase). Prefer the review's own term as the node name. Example grounding: Cremers lists "T, P_TMA, P_H2O, 1000 ALD cycles, pulse/pump times" together as "the process parameters" (Sec. III B), so these belong under one node.
2. **Small.** At most 2 levels below the root, at most 8 top-level nodes. Create a sub-node only if it groups at least 2 entries and the reviews distinguish it.
3. **One place.** Every quantity, categorical and model belongs to exactly one leaf node. Species and structures are values (reached through `values_from`), not categorized.
4. **Category is not role.** A category says what the value is about; `role` says how it is used in data. Do not encode role in the hierarchy (no "outputs" node that duplicates role = output).
5. **Placement test.**
   - Set by the experimenter for a run → recipe side.
   - A property of the equipment → reactor side.
   - A property of the test structure → substrate side.
   - Observed after deposition → result side.
   - A parameter of a surface-reaction model → kinetics side.
   - A plot axis is not a category (that is role = coordinate). Place it by what it measures: position along a feature → test structure side; time within a pulse → cycle side.
6. **Disagreement is recorded.** If you place an entry against a review's own grouping, write the reason in the node or entry. Example: Cremers calls plasma configuration a process parameter, but it is equipment.
7. **Links.** Hierarchy edges are `child_of` (node → parent) and `member_of` (entry → leaf node). Together with the Sec. 9 edges, every entry must be connected (check 10).

### Example (not the answer)

```
recipe                 Cremers "process parameters" + "ALD process"
  process              material, reactant_A, reactant_B, process_mode       (Popov Table I; Cremers Sec. IV)
  cycle                pulse_time, purge_time, partial_pressure, exposure, plasma_power, time   (Cremers Sec. I, per step)
  run                  deposition_temperature, process_pressure, cycle_number, carrier_gas, gas_flow_rate, source_temperature
reactor                reactor, reactor_type, delivery_method, plasma_configuration       (Cremers Sec. II C, Table IV)
substrate              structure, feature_width, feature_depth, feature_extent, aspect_ratio, equivalent_aspect_ratio,
                       distance, dimensionless_distance
result
  growth               film_thickness, growth_per_cycle, nucleation_period, thickness_nonuniformity
  conformality         normalized_thickness, penetration_depth, coated_aspect_ratio, step_coverage
  film_properties      refractive_index, ..., crystallinity
surface_kinetics       initial_sticking_coefficient, recombination_probability, adsorption_equilibrium_constant,
                       saturation_growth_per_cycle, surface_coverage, and the models
```
(time, the time within a reactant pulse, goes with the cycle settings.)

### What may change, and what may not

- **May change:** the hierarchy; every entry's `category`; definitions, roles, qualifiers, units, aliases and transforms, where the closer reading of the reviews shows they are wrong or imprecise. Each such change cites the review.
- **May not change:** entry ids. Do not add or remove entries either. If the reviews show that a concept is missing, duplicated, or wrongly split or merged, write it as a proposal (`proposals` in ontology.yaml: what, why, citation). Proposals are reviewed in the chat, not applied. Each proposal carries `decision: open | accepted | rejected` and `decision_reason`; only the chat changes `decision`.
- Keep it simple. A clear tree with exact links is the goal, not more nodes.

### Report additions

- In report.html: the hierarchy tree (Sec. 14, 2b) and a Proposals table.
- In the report back (up to 25 lines for this task): the top-level nodes with one-line justifications, every place you departed from the example and why, every changed definition / role / qualifier, and the number of proposals.
