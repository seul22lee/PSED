# Checklist: 10.1021_acs.chemmater.2c01154 (mat22)

Core list (the 14 quantity_matrix columns plus saturation_checked). Status: found (ids in the tables) / not stated / not in document (SI) / not read. Ids are found in the final tables by rule; the reason column says what a status means here.

| Core item | Status | Ids | Note |
|---|---|---|---|
| measured_profile | not stated | mat22:s1c_map | planar films only; the series shown is a lateral thickness map over a 4 inch wafer, not a depth profile |
| pd50_or_coated_ar | not stated | — | planar films only |
| structure_class | found | mat22:uT250R000, mat22:uT200R000, mat22:uT150R000 (+54) |  |
| structure_dims | not stated | — | planar substrates (Si with thermal SiO2, glassy carbon, PET foil); no 3D structure |
| exposure_or_pp_and_pulse | found | mat22:c361, mat22:c371 | pulse times and pressures of the cycle recipe; no precursor partial pressure |
| deposition_temperature | found | mat22:c001, mat22:c003, mat22:c005, mat22:c007, mat22:c009, mat22:c011, mat22:c013, mat22:c015 (+47) |  |
| cycles | found | mat22:c002, mat22:c004, mat22:c006, mat22:c008, mat22:c010, mat22:c012, mat22:c014, mat22:c016 (+79) |  |
| planar_gpc | found | mat22:v065, mat22:v066, mat22:v067, mat22:v068, mat22:v069, mat22:v070, mat22:v071, mat22:v072 (+24) |  |
| sticking_or_reaction_prob | not stated | — |  |
| recombination_prob | not stated | — | H2S/H2/Ar plasma; no radical loss reported |
| step_coverage | not stated | — | planar films only |
| front_slope_or_width | not stated | — | planar films only |
| pore_or_channel_width | not stated | — | planar films only |
| process_mode | found | mat22:uT250R000, mat22:uT200R000, mat22:uT150R000 (+52) |  |
| saturation_checked | not in document (SI) | — | saturation curves stated to be in SI Figure S1 (Results, Concept para) |

## Paper-specific extras (from the first pass)

| Key quantity | Status | Where |
|---|---|---|
| Quantity | Status |
| Purge times | found: 10 s after A (6 s flow + 4 s pump), 6 s after plasma, 300 sccm Ar; cycle 51 s |
| Film thickness | found: Fig. 1b legend (v140-v143), wafer mean/sd (v144, v145), Fig. 7a at 140 cycles read by eye (v134-v139), ~50 nm RBS/TEM films (v173, v181, v189, v196), ~5 nm PET/FET films (v147, v150...) |
| Uniformity | found: 3.3% sigma over 4 inch wafer (v146); map points from points.json (series s1c_map) |
| Composition | found: S/Mo by XPS for all 32 grid cells (Fig. 4, v033-v064), Fig. 5 labels (v129-v133), RBS/ERD Table 1 (v166-v189), WS2/TiS2 ratios (v247ff). Table S1/S7: not in document |
| Crystallinity | found: 32 grid cells (Fig. 2, v001-v032) and named samples; XRD (Fig. S2) not in document |
| Roughness | found: Rq for 6 ratios at 150 °C (Fig. 6a, v198-v208), 0.75 nm for the 100 °C TEM/FET film (v154) |
| Density | found: Table 1 (v168, v176, v184), bulk literature value 5.06 (v195) |
| Resistivity | found: 32 cells read from the Fig. 8 log colour scale (v097-v128; checked against the text values 15, 220, 2 Ω cm and 4 mΩ cm), text values (v225-v230), PET 0.3 Ω cm (v148), WS2 4 Ω cm. Table S2: not in document |
| Carrier density / mobility | found as text ranges (v231-v239, v194); per-sample Hall data (Sec. S10) not in document |
| XPS binding energies | found (v210-v221) |
| Raman peak positions | not read (only peak labels in Figs. 1, 9; no numbers printed) |
| FET metrics | on/off 3-4, current ratio >10, contact behaviour, interface layer thickness (v157-v165); the curves (Fig. S13) are not in the document |
