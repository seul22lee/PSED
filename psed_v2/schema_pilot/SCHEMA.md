# Schema pilot: five tables

Three papers read by hand (no LLM API calls): 10.1039_d0cp03358h (yim20, 16 samples in Table 1, profiles, fits and model runs),
10.1021_acs.chemmater.2c01154 (mat22, outside conformality: a 32-run temperature × H2-ratio grid seen by four figures),
10.1116_6.0003182 (gre23, three runs each followed by pressure traces, mass gain, XRD and EDS). Evidence is a locator with a
few words of paraphrase, never copied text.

Per paper folder: `paper/sample/condition/series/value.csv` (final), `checklist.md`, `notes.md` and `checklist_draft.md` (first pass),
`draft/` (the first six tables) and `build.py` (writes `draft/`). Shared: `lists.py` (the lists below), `convert.py` (draft → final),
`validate.py` (must pass), `checklist.py`, `make_report.py` (→ `reports/pilot.html`, untracked), `v1_points_check.csv` and
`v1_points.json` (v1 points checked against the figures).

## Tables

- **paper**: paper_id, year, topic
- **sample** (identity only): sample_id, paper_id, kind (run | piece | channel | reference | group | model_run), label_as_printed (`u` if
  none), parent_sample, members (groups: `;`-list), material, precursor, coreactant, process_mode, reactor, structure_class,
  structure_dims, width_kind (H | d | w | none), note, evidence
- **condition**: condition_id, sample_id (a sample, a group, or `*` = the whole paper), kind (process | measurement | substrate_prep),
  quantity, label_as_printed (when quantity = other), qualifiers, value, unit, data_kind (stated | calculated | assumed),
  applies_when, note, evidence. Temperature and cycles live here (`deposition_temperature{kind=set_point}`, `cycle_number`).
- **series**: series_id, sample_id (sample or group; empty only for cited reference patterns), kind (plot | image | map | spectrum | table),
  figure, panel, method, x_id, x_qualifiers, x_label, y_id, y_qualifiers, y_label, z_id, z_label, data_kind (measured | fit |
  simulation | calculated | cited | schematic), link_status (stated | inferred), points_source, points, reused_from, note, evidence.
  An image, a map without read cells, or a table is a series row without points. There is no link table.
- **value**: value_id, sample_id (sample, group or model_run; empty only for literature values), from_series, quantity,
  label_as_printed, qualifiers, value, value_min, value_max, censor (< | > | <dl | >dl), unit, data_kind (measured | fit | chosen input |
  literature | assumed | calculated), method, relation, regime, cited_ref, note, evidence

## Lists (lists.py)

- **quantity**: aspect_ratio, carrier_gas, coated_aspect_ratio, composition, crystallinity, cycle_number, cycle_time, deposition_temperature,
  dimensionless_distance, distance, equivalent_aspect_ratio, exposure, feature_depth, feature_width, film_density, film_thickness, front_slope,
  gas_flow_rate, growth_per_cycle, initial_sticking_coefficient, knudsen_number, lumped_sticking_coefficient, mean_free_path,
  normalized_exposure, normalized_thickness, open_fraction, partial_pressure, penetration_depth, precursor_purity, probe_resolution,
  process_pressure, pulse_time, purge_time, reactor_type, recombination_probability, resistivity, saturation_density, source_temperature,
  step_coverage, substrate, surface_coverage, thickness_nonuniformity; else `other` with label_as_printed (the ids of cases 1 to 13
  plus those needed by two or more of the three papers).
- **qualifiers** (key=value, `;`-separated; free text goes to note): step = reactant_A | purge_A | reactant_B | purge_B | plasma | hold_A |
  hold_B | none; position = planar | local | top | sidewall | bottom | entrance | plateau | outside; kind = set_point | measured; reference =
  plateau | entrance | maximum | stated | planar | assumed_saturation; by = H | 2H | d | w | lambda | none; origin = entrance | top_face |
  hole_centre | nearer_face | opening_centre; level = 50% | front_start | front_end; basis = AR | EAR; species, gas, element = a chemical token.
- **method**: reflectometry, ellipsometry, sem, sem_eds, tem, xps, raman, xrd, afm, electrical, rbs, process_monitor, gravimetry, photograph,
  simulation, calculation, cited, schematic, tabulated. Settings (spot size, magnification, kV, laser) are condition rows with kind = measurement.

## Decisions

1. **Sweep plot, one run per point**: one sample per point; a group sample names the members; the series points to the group; each point that is
   a result is a value with `from_series`. mat22: 32 grid cells, group `mat22:grid`, one map series per figure, one value per cell.
2. **One sample, several methods**: one sample, one series per method; measured pieces are child samples. gre23 run 120: pressure trace,
   hold analysis, mass gain (Table I), XRD, EDS map and line scan; compacts and the resistivity prism are pieces of the run.
3. **A value read from or fitted to a series**: a value with `from_series`, its data_kind and relation. yim20: x̃ at one half read from the
   Fig. 9c profile (measured), the front slope fitted by the authors (fit), c = 13.9·slope² (calculated) on the group of samples 2, 4, 8, 12.
4. **A condition stated once**: `sample_id = *`; a rule that depends on another condition gets `applies_when` (mat22 cycles by temperature).
5. **Values about several runs or the whole structure** (tolerances, Hall ranges, a computed purge per temperature) point to a group
   defined by the stated range; simulations and model inputs point to a `model_run` sample; literature values carry `cited_ref`.

## Result

| Paper | sample | condition | series | value | link (dropped) | validator |
|---|---|---|---|---|---|---|
| yim20 | 22 → 31 | 136 → 178 | 81 → 106 | 235 → 235 | 64 → 0 | pass |
| mat22 | 57 → 69 | 281 → 380 | 67 → 81 | 264 → 264 | 170 → 0 | pass |
| gre23 | 14 → 16 | 64 → 90 | 44 → 66 | 125 → 125 | 48 → 0 | pass |

Samples grow by groups and model runs, conditions by temperature and cycles moved from sample, series by links not covered by a series.
Points: 13 series from cases/points.json; v1's 121 curves were checked against the figures, 75 accepted and 46 rejected (sketch panels,
heat maps taken as curves, fronts shifted by more than a marker, spectra with a wrong shape, a merged legend entry); 69 imported (the
other accepted ones already had our points). 165 quantity labels remain as `other`, most from one paper each (XPS, Raman, EDS axes,
the mat22 grid variables h2_flow_ratio and atomic_ratio, the gre23 hold analysis).

v1 against the pilot (details in each notes.md and the report): yim20 v1 has no result values (all 142 Table 1 cells, the sticking values
and the literature table missing) and counts each curve as a case; mat22 v1 misreads the Fig. 4 axis, stores "above the detection limit" as
5000, has two Fig. 8 cells that contradict the text and misses Fig. 7b, the wafer map, Tables 1 and 2 and the H2S plasma; gre23 has no v1 output.
