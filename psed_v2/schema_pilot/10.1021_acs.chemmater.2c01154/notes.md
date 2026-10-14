# Notes: 10.1021_acs.chemmater.2c01154 (mat22)

**(a) Sweep plots where each point is a separate run.** Figs. 2, 4, 7b and 8 are the same 32-cell grid: H2 flow ratio by deposition temperature, each cell one deposition. I made **one sample per cell** (`mat22:uT150R080` = 150 °C, ratio 0.80) and **one series per heat map** with `sample_ids` = the group "grid". Each cell is a row in value.csv with `from_series` set. One sample therefore carries crystallinity (Fig. 2), S/Mo (Fig. 4), GPC (Fig. 7b) and resistivity (Fig. 8). The cycle number per cell comes from the Exp. rule (100/120/140 by temperature). The captions only say "100-140", so the rule is applied, not confirmed per cell.

**(b) One sample measured by several methods.** `mat22:uT150R080` has Raman (Fig. 1a), XPS spectra and binding energies (Fig. 5, text), SEM/AFM Rq (Fig. 6a), in situ SE (Fig. 7a), GPC and resistivity (Figs. 7b, 8). Only the grid cell is a stated link. That the 150 °C, 140-cycle films in Figs. 1a, 5, 6a and 7a are those same runs is *inferred* in link.csv. `mat22:F100` (100 °C, 0.80, 50 cycles) has TEM, AFM, FET and four-point probe data; the Exp. TEM paragraph states the link.

**(c) A value read from or fitted to a series.** Fig. 7b and Fig. 8 cells were read by a script that compares each cell colour to the colour bar (scratch heat.py). The reads were checked against the paper: at 150 °C, Fig. 7a thickness at 100 cycles divided by 100 matches Fig. 7b within 0.02 Å/cycle. Fig. 8 reproduces the text values: 16 vs 15 Ω cm, 2.2e2 vs 220, 2.3 vs 2, and 3.7e-3 vs 4e-3. The Fig. 7a endpoints at 140 cycles were read by eye (v134-v139). The Fig. 1c map points come from points.json.

**(d) A condition stated once for the whole paper.** The cycle recipe (6 s / 10 s / 20 s at 100 W / 6 s, 51 s total), source 50 °C, 200 mTorr and 6 mTorr, and the reactor are `sample_id = *` rows. Table 2 maps the H2 ratio to H2S/H2/Ar flows. I repeated those flows on every sample whose ratio is known (3 rows per sample), because condition.csv has no way to say "this row applies to all samples with ratio X".

**(e) What did not fit, and the smallest fix.**
- Conditional paper-wide rules ("100 cycles at 450 °C, 120 at 50/300/350 °C, 140 at 100-250 °C"; flows per ratio): add an optional `applies_when` column to condition.csv.
- condition.csv has no qualifier column, so I wrote `gas_flow_rate{gas=H2S}` into `quantity`. Add `qualifiers` as value.csv has.
- Sample groups (the grid) have no table. Add a `group.csv` (group_id, member sample_ids, rule).
- Ranges, bounds and categories ("0.1-1", ">dl", "<dl (~7)", "p-type") sit in `value` as text. Add `value_min`/`value_max`/`censor` columns.
- Values tied to a condition range rather than one sample (Hall: "0.50-0.80 at 100-250 °C") have an empty sample_id with the range in qualifiers.
- Measurement settings (Raman 514 nm, 0.6 mW; XPS pass energies; SE models; AFM tips) are not process conditions and were left out. A `method.csv` would hold them.
- The Table 1 RBS films (~50 nm on glassy carbon, cycles not stated) are separate samples from the grid. Their link to the Mo-atoms-per-cycle values is inferred.
- The S/Mo ratio is not `composition` (atomic fraction), so `atomic_ratio (new)` was added.
- New ids:
  - h2_flow_ratio, raman_shift, raman_intensity, xps_intensity
  - binding_energy, binding_energy_shift, peak_area_ratio, atomic_ratio
  - surface_roughness_rq, monolayer_count, crystallite_width, oriented_layer_thickness
  - metal_atoms_per_cycle, hydrogen_density
  - on_off_ratio, output_current_ratio, contact_behaviour, interface_layer_thickness, conduction_type
  - wafer_position, wall_temperature, base_pressure, plasma_frequency, cycle_time, stabilization_time, delivery_line_temperature
  - substrate, substrate_prep, substrate_size, substrate_carrier, substrate_precoat, loadlock_pressure, preheat_time
  - gas_purity, precursor_purity, extra_step, post_process
  - crystallinity_threshold, h2_flow_ratio_upper_bound, h2_flow_ratio_reference, alds_regime_check, temperature_reported_as
  - anneal_stability, oxidation_onset_temperature, optical_transparency
- The text says WS2.1 and the Conclusions print WS2.2. Both are kept in their evidence.

**(f) Row counts.** paper 1, sample 57, condition 281, series 67, value 264, link 170.

**(g) Comparison with v1.** v1 has 51 entities, 34 experiments, 17 series, 51 results and 173 assertions. This pilot has 57 samples, 67 series, 264 values and 281 conditions.
- **Fig. 4 x axis is wrong.** v1 mapped it to `partial_pressure`; it is the H2 flow ratio. The 300 °C row is in the entities but missing from series.json.
- **Fig. 8 is wrong in v1.**
  - A "35 °C" row exists; it should be 50 °C.
  - ">dl" is coded as the number 5000.
  - The reads contradict the text: 0.20/300 °C is 100 in v1 vs 15 Ω cm stated, and 0.20/450 °C is 800 vs 220 stated. 0.20/250 °C is 500 in v1 vs 74 read here.
- **Fig. 7b is absent from v1** (32 GPC cells). So are the Fig. 1c wafer map and sigma = 3.3%, all of Table 1 (RBS/ERD S/Mo, density, H/N/O), and Table 2 flows per ratio.
- **v1 records no recipe and no text scalars.** Its assertions are only temperature and cycle number: no pulse, purge or plasma times, power, or source temperature. v1 also lacks binding energies, Hall data, and the resistivities in the text.
- **v1 misidentifies the chemistry.** Precursors are empty and the co-reactant is "H2" only, not H2S/H2/Ar plasma.
- **v1 Fig. 7a, ratio 0.20:** the last points (9.7 at 130 cycles, 10.9 at 140) look like they were taken from the 0.94 curve. The figure gives ~9.6 at 140.
- **v1 has what I did not read:** full point lists for the Fig. 1a/1b/9 Raman spectra and the Fig. 7a curves (15 points each). I recorded only the 140-cycle endpoints and left the spectra "not read".
- **v1 treats each figure curve as an "experiment".** It has no link between the Fig. 1a/5/6a/7a 150 °C films and the grid cells, and no named samples (wafer, PET, FET/TEM films, RBS films).
