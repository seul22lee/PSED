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
