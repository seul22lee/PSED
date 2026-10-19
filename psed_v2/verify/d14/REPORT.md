# P131b: ontology v1 (Directive 12)

Done criterion: the accepted pending entries live in ontology.yaml, every printed label is an alias or a listed exception, the five
accepted free labels are re-keyed, check.py exits 0, the 26 questions are unchanged, and ontology-v1 is tagged with its hash.

Reproduce from d9df13c: add `inverse_time` to the units: block, then
`pending_decide.py --labels "b_film;wall temperature;wavelength range;base pressure;k;p_d"` → `merge_pending.py` →
`alias_audit.py --apply` → `export.py` → the 12 `<pid>.facts.py` → `alias_audit.py`. The whole chain was rebuilt from a clean checkout of
the inputs each time a rule changed (scratch rebuild.sh), and the yaml header and hash were written last.

## Entries by kind (ontology.yaml `entries:`)

| kind | before (d9df13c) | after (v1) |
|---|---|---|
| quantity | 79 | 91 (+7 pending accepted, +5 step 3) |
| species | 27 | 37 |
| method | 0 | 8 (pending methods are entries now; vocabularies.measurement_method stays 27) |
| structure | 4 | 9 |
| mechanism | 36 | 37 |
| model | 4 | 4 |
| categorical | 15 | 15 |
| total | 165 | 201 |

pending.csv went from 39 rows to 8: the 31 accepted rows plus the 5 from step 3 moved out. The 8 still pending are elam_monte_carlo,
pore_density, porous_sphere/cylinder/slab, model_reactant, tortuosity and pore_volume. Their rows now carry an `evidence` column;
tortuosity and pore_volume show hei24 abs.g3 abs.g4 s12.p3, where their HEAD decision rows still said "no record names it". Each merged
entry records its P98 rule in `deviation.reason`. `kind=estimated` now has evidence: gre23:s9.p6#12 and #13. vocab.py against
d9df13c: PENDING −31, five new concepts with labels and names, the `cq` of 29 merged entries now filled, the 1/s unit, `FROM_OTHER`,
and the audit's new aliases.

## Step 3, the six labels (decisions.md)

The six labels were b_film, wall temperature, wavelength range, base pressure, P_d and k. The first five were accepted by rule (a),
records in ≥ 2 papers: ids `b_film`, `wall_temperature`, `wavelength_range`, `base_pressure` and `p_d`. **k stopped**: the folded
label joins ela03 `k` (s^-1/2, a √t fit) and yim20 `K` (Pa-1, already an alias of `adsorption_equilibrium_constant`), which is two
concepts. `chip size` (yim20, gao15) is a seventh multi-paper label and was not decided.

## Alias audit (verify/d14/alias_audit.csv; one row per distinct entry, printed form and paper)

| | matched | missing | unlocated | spread |
|---|---|---|---|---|
| before (after the merge, before `--apply`) | 120 | 87 | 180 | 6 |
| after (final facts) | 203 | 16 | 175 | 6 |

The run added 68 aliases to 33 entries, each with an evidence line `alias '<form>': <paper> <element>`. **Missing is 16, not 0.** Every
remaining row is stopped by rule, because adding the form would put one word in two entries (make_report check 4):
- `L`: feature_depth ×4 and body_thickness ×1, each already a name of the other.
- `thickness`: body_thickness ×2, already a name of film_thickness.
- `S`, `a`, `d`, `R`: already names of film_thickness/specific_surface_area, reactant_A, body_diameter and recombination_probability.
- `sticking probability`: an ambiguous alias.
- `Zn (metallic) Wt. %`: phase and phase_fraction.
- `gap height` (gao15): gre23 carries it as `other[gap height]`, so the P78 slot rule would re-key that record (the gap under a quartz boat) to
  feature_width.
- `base pressure`: keyed to **process_pressure** in mat23 and zou23, while mat22 and ela03 now go to `base_pressure`. This needs a re-key
  decision.

Two deviations from the directive's wording. Records with a `stat=` qualifier are listed as `spread`: their label names the statistic,
not the quantity. Printed forms match up to case, subscript underscores and spaces (`fold()`). A first run that matched case only
added `S_I/N (GPC_I)` next to the existing `SI/N (GPCI)` on growth_per_cycle, and that broke check.py's search probe
'growth per cycle temperature' (P64). With the fold, the probe passes and the duplicate is not added.

## Re-keyed records (by `facts.rekey_from_other()`; only the quantity column changed)

21 records: mat22 2, ela03 1, yim20 3, yim22 10, yli18 2, mat23 3 (base_pressure 2, wall_temperature 2, wavelength_range 3, b_film 4,
p_d 10). No record was renamed. check.py exits 0 and questions.py answers 26 of 26, with questions.csv unchanged.

## Hashes

- kb preamble: 9cfc90c50d690fc4 (d9df13c, written to verify/d13/prompt_size.txt) → **90f1459ac13f8154**. The tool descriptions now
  name the settings `base pressure`, `wall temperature`, `p d` and `b film`. kb system prompt: 2,580 → 2,588 tokens.
- ontology v1: **356a86b4bd1349213c2f9321ec8f1c441c279028d23d48ca858136dd3f56ebd1** (ontology_v1.txt; also in the yaml header,
  `version: 1`).

## What stopped or fails (for the user)

1. make_report check 5: there are 53 extension quantities against a cap of 45. The cap is a Sec. 18.8 tripwire and was not raised.
2. make_report check 4: `d_A`/`dA` (molecule_diameter) against `D_A`/`DA` (gas_phase_diffusion_coefficient). These symbols differ only
   by case and came verbatim from two accepted pending rows. Sec. 11 rule 6 would move them to ambiguous_aliases.
3. `k`, the 16 missing aliases, and `chip size`, as above.
4. units.yaml gained the row `1/s` (inverse_time), which P_d needed. Rule-made fields to check by eye:
   - ids and names `p d` and `b film`
   - definitions of the form "<label>: the free label of N records…"
   - category `measurement` for all five step-3 entries
   - sicl4's formula `SICL4` and the `dimension: dimensionless` on merged species and methods. Both are what export already emitted, and
     the merge keeps them verbatim.
5. Not run: ontology/report.html (generated output, left at d9df13c) and apply_external_ids.py, so the merged entries have no QUDT or
   PubChem lines.

## 12b: fix-up (Directive 12b)

Rebuilt from the d9df13c inputs with the same chain, plus `chip size;gap height` on the --labels list and an export and facts pass before
the audit (so the audit sees the base-pressure re-key). The yaml header and hash were written last.

1. **Cap:** make_report `EXTENSION_CAP` 45 → 60. CRITERIA Sec. 11 gains the line "cap is reset at each growth round to count + 10 %".
   Check 5 passes with 53.
2. **Rule 6:** `alias_audit.move_ambiguous()` adds a form to vocabularies.ambiguous_aliases with every entry it would match and removes it
   from all entries' aliases.
   - From the merge: `d_A`/`dA`/`D_A`/`DA` were dropped from molecule_diameter and gas_phase_diffusion_coefficient. One key, `d_A`, lists
     both entries; concept.norm folds case and underscores, so all four spellings resolve to it, each with both candidates.
   - From the audit: `L` (body_thickness, feature_depth), `R` (feature_depth, recombination_probability), `S` (film_thickness,
     initial_sticking_coefficient, specific_surface_area), `a` (aspect_ratio, reactant_A), `d` (body_diameter, feature_width), `thickness`
     (body_thickness, film_thickness), `Zn (metallic) Wt. %` (phase, phase_fraction). `sticking probability` was already a key.
   - As a result `thickness` and the one-letter labels no longer resolve to a single entry.
   - `gap height` is the alias of nothing. It became the pending row `gap_height` (gre23 only, rule none); gre23:s9.p1#3 keeps
     `other[gap height]`.
   - `base pressure` was not made ambiguous: step 3 resolves it.
   - New audit statuses: ambiguous, pending. Missing counts forms that are none of alias, ambiguous or pending.
3. **base pressure:** `facts.rekey_from_other()` now keys any record whose printed label is a `from_other` label, not only `other[...]`.
   It changes exactly two records against d814cb1: zou23:s5.p1#2 (1e-8 hPa) and mat23:s7.p1#2 (7e-6 hPa), both setting,
   process_pressure → base_pressure. Against d9df13c: 23 records (mat22 2, ela03 1, yim20 3, yim22 10, yli18 2, mat23 4, zou23 1).
4. **chip size:** stopped, two concepts (yim20 mm vs gao15 no unit), not accepted. See decisions.md.
5. **The five entries:**
   - `name` is the printed form: `b_film`, `wall temperature`, `wavelength range`, `base pressure`, `P_d`.
   - `definition_status: template`: the pending rows held only the candidate() template, no definition of their own.
   - `category_status: provisional` (category `measurement` unchanged).
   - verify/d14/five_entries.md (written by five_entries.py) has 5 entries and 23 records, each with the verbatim text of its evidence
     elements. **It is not committed**: it holds paper text (CLAUDE.md: full text lives outside git). Re-create it with
     `python3 psed_v2/verify/d14/five_entries.py`.
6. **sicl4:** formula `SiCl4`. export.pending_entry derived it from the id (`r["id"].upper()` when the row had no aliases). It now takes
   the first formula-like alias, else the row definition's "(formula X" verbatim; no other species changed.
7. export → vocab.py (`--check` up to date); make_report 15/15 pass; check.py exits 0; questions.py 26/26 answered, questions.csv unchanged.

Audit (alias_audit.csv):

| | matched | missing | unlocated | spread | ambiguous | pending |
|---|---|---|---|---|---|---|
| 12a final | 203 | 16 | 175 | 6 | – | – |
| 12b final | 205 | **0** | 175 | 6 | 13 | 1 |

Hashes:
- kb preamble: 90f1459ac13f8154 → **0ea67d562f985c3a** (2,588 tokens). The tool descriptions carry the new names and the 9th pending
  entry.
- ontology v1: 356a86b4… (d814cb1) → **befb9ad2027f0b6addd092f96d76492c56605e287f60fefbba72fc19caa4b701**. Tag ontology-v1 moved.

## 12c: definitions of the five entries (Directive 12c)

`ontology/entry_definitions.py` holds the user's table and writes it. It removed definition_status and category_status, and checked
every paper quote by substring match against the element text (LaTeX wrapper removed); all matched. Categories are the ones the user
chose in the chat: `model_parameter` is a role and `setting` a record type, and neither is a hierarchy leaf (make_report check 8).

| id | name | category | source | definition |
|---|---|---|---|---|
| b_film | metal atoms per film formula unit | surface_kinetics | paper | b_film is the number of metal atoms in the formula unit of the deposited film |
| p_d | desorption probability (per unit time) | surface_kinetics | paper | desorption probability, P_d |
| wall_temperature | reactor wall temperature | deposition_run | user | temperature at which the reactor or chamber walls are held during deposition, as distinct from the substrate or table temperature |
| base_pressure | reactor base pressure | ald_reactor | user | lowest pressure the pumped reactor reaches with no gas flowing (ultimate vacuum), stated before deposition |
| wavelength_range | measurement wavelength range | measurement | user | wavelength interval covered by an optical measurement (reflectometry, transmittance) |

- **Quotes in evidence:**
  - b_film: `quote yli18 s5.p18`. The element prints `$b_{\text{film}}$`.
  - p_d: `quote yim22 fig4.cap`, plus the yli18 sentence with P_d and "desorption", verbatim: s6.p6 "where $\theta$ is the surface
    coverage, $q$ the saturation adsorption density, and $P_d$ the desorption probability in unit time."
- **b_film's leaf:** the user asked for the leaf of gpc_sat, q and rho. gpc_sat (`saturation_growth_per_cycle`) and q
  (`saturation_density`) are in surface_kinetics, but film density rho (`film_density`) is in film_properties, as an output. b_film went
  to surface_kinetics, with the two model parameters of the group.
- **wavelength_range:** the schema has a category for instrument and measurement settings (`measurement`: "Settings of the
  characterization…"), so no provisional flag.
- **Units and roles unchanged:** p_d stays 1/s, b_film has no unit, and roles are as before.
- **ela03 re-key:** ela03:s3.p26#3 is no longer a base pressure. Its printed label in 10.1021_cm0303080.facts.py is now
  `evacuated below`, printed in s3.p26 ("the flow tube was first evacuated below 0.035 Torr"). The facts.write() rule no longer keys it,
  so it stays `other[evacuated below]`; it is the only record that changed.
  - `pending_decide.py --labels "evacuated below"` made the pending row `evacuated_below` (ela03, rule none).
  - base_pressure's evidence is now mat22 s5.p1, mat23 s7.p1, zou23 s5.p1, and its citation lists those three records. Its
    deviation.reason still records the P131b decision as it was made (rule a, papers ela03 mat22).
- **Audit:** matched 204, missing 0, unlocated 175, spread 6, ambiguous 13, pending 1.
- **Hashes:**
  - kb preamble: 0ea67d562f985c3a → **b267b30d2286615c**.
  - ontology v1: befb9ad2… → **dd5ad1454c153446cc4dc60103b7c3a2ce9f5614ec10c37404d8a9327c16145a**.
