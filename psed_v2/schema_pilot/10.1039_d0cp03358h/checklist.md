# Checklist: 10.1039_d0cp03358h (yim20)

Core list (the 14 quantity_matrix columns plus saturation_checked). Status: found (ids in the tables) / not stated / not in document (SI) / not read. Ids are found in the final tables by rule; the reason column says what a status means here.

| Core item | Status | Ids | Note |
|---|---|---|---|
| measured_profile | found | yim20:F3b-exp, yim20:F5a-AlKa-map, yim20:F5b-O, yim20:F5b-Al, yim20:F5b-Si, yim20:F6-AFM-map, yim20:F7-x5, yim20:F7-x10 (+38) |  |
| pd50_or_coated_ar | found | yim20:v005, yim20:v006, yim20:v014, yim20:v015, yim20:v023, yim20:v024, yim20:v032, yim20:v033 (+37) |  |
| structure_class | found | yim20:1, yim20:2, yim20:3 (+19) |  |
| structure_dims | found | yim20:v158, yim20:v159, yim20:v160, yim20:v179, yim20:v180, yim20:v200, yim20:v201, yim20:v202 (+5) |  |
| exposure_or_pp_and_pulse | found | yim20:c067, yim20:c069, yim20:c074, yim20:c076, yim20:c081, yim20:c083, yim20:c088, yim20:c090 (+24) | pulse and purge times per sample; partial pressure only as a model input (Fig. 10) |
| deposition_temperature | found | yim20:c001, yim20:c003, yim20:c005, yim20:c007, yim20:c009, yim20:c011, yim20:c013, yim20:c015 (+14) |  |
| cycles | found | yim20:c002, yim20:c004, yim20:c006, yim20:c008, yim20:c010, yim20:c012, yim20:c014, yim20:c016 (+30) |  |
| planar_gpc | found | yim20:v003, yim20:v004, yim20:v012, yim20:v013, yim20:v021, yim20:v022, yim20:v030, yim20:v031 (+23) |  |
| sticking_or_reaction_prob | found | yim20:v177, yim20:v178, yim20:v196, yim20:v219, yim20:v220, yim20:v221, yim20:v222, yim20:v223 (+5) |  |
| recombination_prob | not stated | — | thermal process; no radicals |
| step_coverage | not stated | — | profiles and PD50 instead of a step coverage |
| front_slope_or_width | found | yim20:v007, yim20:v008, yim20:v016, yim20:v017, yim20:v025, yim20:v026, yim20:v034, yim20:v035 (+25) |  |
| pore_or_channel_width | found | yim20:v158, yim20:v159, yim20:v160, yim20:v200, yim20:v201, yim20:v202, yim20:v203, yim20:v204 (+2) |  |
| process_mode | found | yim20:1, yim20:2, yim20:3 (+19) |  |
| saturation_checked | found | — | Series E pulse 0.1/0.2/0.4 s and purge series (Fig. 11, Table 1 samples 12-16); planar S1/N nearly constant |

## Paper-specific extras (from the first pass)

| Key quantity | Status | Where |
|---|---|---|
| Quantity | Status |
| Structure: class | PillarHall-3 lateral channel, a polysilicon membrane roof on pillars over Si (sample.csv) |
| Structure: channel height H | Design 100, 500 and 2000 nm per sample (sample.csv, from Table 1). Tolerances ±10, 20 and 30 nm: v158-v160. Membrane deflection about 25, 25 and 40 nm: v165-v167. Entrance nanostep 2-5 nm: v157 |
| Structure: channel length L | 0.1-5 mm (v180). Maximum AR 10000:1 at L 5000 µm (v179). AR per channel is in ESI Table S1, not read (ESI) |
| Structure: pillars | Layout per sample (condition pillar_layout). Diameter 4 µm and spacing 49 µm (v163, v164). Effect on PD below 1% (v162). Layout details are in ESI Table S2, not read (ESI) |
| Structure: opening width W | Not stated. The hydraulic diameter of 1.0 µm (v174) implies W >> H |
| Process pressure | About 3 hPa total (condition `*`). The TMA and H2O partial pressures of the experiments are not stated |
| Pulse / purge times | Per sample, four rows each (condition.csv): TMA pulse 0.1/0.2/0.4 s, H2O pulse 0.1 s, purges 1/4/10 s |
| Carrier flow | N2 150 sccm through four lines; whether this is the total or per line is not said (condition `*`) |
| GPC inside the channel | GPC_IIb per sample (e.g. v004) |
| Film thickness | S_I and S_IIb per sample (e.g. v001, v002). SD of S_IIb 2.8 nm (v171). Thickness that plugs the 100 nm entrance: 50 nm (v156) |
| Mean free path / Knudsen number | TMA 40 µm, H2O 100 µm (v172, v173). Kn 40 and 100 (v175, v176) |
| Channel filling | 10/20/40% for 250/500/1000 cycles (v153-v155). Recommended below 10% (v181) |
| Composition | Not stated. The EDS O/Al/Si intensities (Fig. 5b) are a signal, not a composition. ESI Fig. S8 not read (ESI) |
| Crystallinity | Not stated |
| Roughness | Described in words only (Region IIa waviness, Fig. 6). The AFM Z range of 3.081 µm (v147) includes membrane remnants, so it is not a roughness value. The AFM line scan is in ESI Fig. S6, not read (ESI) |
| Resistivity | Not stated |
| Film density | Model input 3.1 g/cm3 (v193). Ylilammi 2018's 4.0 g/cm3 (v227) |
| Measurement uncertainty | Scan positioning about 2 µm (v168). PD sensitivity to H: 1.5%/% (v161). Spot sizes v150-v152 |
