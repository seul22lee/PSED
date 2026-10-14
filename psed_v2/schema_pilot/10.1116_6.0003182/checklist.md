# Checklist: 10.1116_6.0003182 (gre23)

Core list (the 14 quantity_matrix columns plus saturation_checked). Status: found (ids in the tables) / not stated / not in document (SI) / not read. Ids are found in the final tables by rule; the reason column says what a status means here.

| Core item | Status | Ids | Note |
|---|---|---|---|
| measured_profile | found | gre23:s6a_SE, gre23:s6a_Al, gre23:s6a_Zn, gre23:s6b_SE, gre23:s6b_Al, gre23:s6b_Zn, gre23:s6c_SE, gre23:s6c_Al (+1) |  |
| pd50_or_coated_ar | found | gre23:v083, gre23:v084, gre23:v085 | no front: the compacts are coated through, coated AR = full AR |
| structure_class | found | gre23:120, gre23:160, gre23:120/160 (+10) |  |
| structure_dims | found | gre23:v001, gre23:v002, gre23:v007, gre23:v008, gre23:v090, gre23:v092, gre23:v093, gre23:v096 (+2) |  |
| exposure_or_pp_and_pulse | found | gre23:c046, gre23:c049, gre23:c053, gre23:c054, gre23:c055, gre23:c056 |  |
| deposition_temperature | found | gre23:c001, gre23:c003, gre23:c005, gre23:c007, gre23:c009, gre23:c011, gre23:c013, gre23:c015 (+11) |  |
| cycles | found | gre23:c002, gre23:c004, gre23:c006, gre23:c008, gre23:c010, gre23:c012, gre23:c014, gre23:c016 (+6) |  |
| planar_gpc | not stated | gre23:v020, gre23:v026, gre23:v032, gre23:v038, gre23:v102, gre23:v106, gre23:v121 | no planar witness; growth per cycle only inside the compacts, from mass gain |
| sticking_or_reaction_prob | not in document (SI) | — | design inputs of Eq. 1 are in Note S1 |
| recombination_prob | not stated | — | thermal process |
| step_coverage | not stated | — | EDS signal ratio only (not a thickness) |
| front_slope_or_width | not stated | — | no front |
| pore_or_channel_width | found | gre23:v007, gre23:v093, gre23:v097 |  |
| process_mode | found | gre23:120, gre23:160, gre23:120/160 (+10) |  |
| saturation_checked | found | — | static holds sized by a diffusion design (Sec. II B); pressure traces show completion |

## Paper-specific extras (from the first pass)

| Key quantity | Status | Where |
|---|---|---|
| Porosity, initial and final | found | v004 (50.5 %); final per run v019, v025, v031 |
| Purge times and flows | found | condition.csv purge_time 2880 s (both), purge flow sequence, 20 sccm |
| Film thickness | found (from mass gain, not measured directly) | v039 (4.73 nm, 120 C), v040 (4.28 nm, 120/160); not given for 160 C |
| Composition / phases | found (XRD wt%) | v043-v054; phases v056-v058 |
| Crystallinity / crystallite size | found | v044, v048, v050, v053; corundum grain v009 |
| Resistivity | found (one prism per run) | v046, v051, v055; current v059 |
| Roughness | not stated | |
| Colour | found | v060-v063 |
| In-situ reaction data (Δn_g, ȳ, terminal slope) | found (table values); per-cycle curves not read | v022/v028/v034, v023/v029/v035, v066-v073; series s3b_*, s3c_* (not read) |
| Purge model (Eq. 2) | found | v012 (theta_f), v013 (nu), v014/v015 (360 / 11 min), v016 (48 min chosen); E_des not stated in main text |
| XPS composition | not read: atomic % are in supplementary Figs. S3-S4, not in main text | |
