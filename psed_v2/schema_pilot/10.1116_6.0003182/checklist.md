# Checklist: 10.1116_6.0003182 (gre23, Greenberg et al. 2023)

| Key quantity | Status | Where |
|---|---|---|
| Structure dims: thickness, half-thickness L, diameter | found | v001 (1.55 mm), v002 (L 0.78 mm), v003 (11.43 mm) |
| Pore width / particle size | found (pore width assumed equal to NP diameter) | v007 (d_pore ~100 nm, assumed), v005 (d_NP 100 nm, from BET) |
| Porosity, initial and final | found | v004 (50.5 %); final per run v019, v025, v031 |
| Aspect ratio | found | v008 (7800 ± 200 on the half-thickness) |
| Deposition temperature | found, per run and per step for the cycled run | condition.csv deposition_temperature rows; ±5 C spread; Fig. 2d trace (series s2d, not read) |
| Partial pressure × time per step | found | condition.csv partial_pressure A/B ~9 Torr, hold_time A/B 1920 s, exposure A/B ~17000 Torr s; pulse 10-14 s (A), 8-11 s (B) |
| Purge times and flows | found | condition.csv purge_time 2880 s (both), purge flow sequence, 20 sccm |
| Source temperatures | found | condition.csv source_temperature A/B 37 C |
| Cycles | found | condition.csv cycle_number 20 |
| Planar GPC | not stated for this process (no planar witness). Only GPC inside the compacts from mass gain | v020, v026, v032 (2.37 / 3.48 / 2.14 Å/cyc, compact, pure-ZnO assumption); literature flat-substrate ~2.1 upper end (literature row) |
| Film thickness | found (from mass gain, not measured directly) | v039 (4.73 nm, 120 C), v040 (4.28 nm, 120/160); not given for 160 C |
| Thickness profile | EDS signal profile only (not thickness) | series s6d/e/f (4 elements each); Zn series from points.json; v077, v078, v082 (shape), v079/v080 (~0.2 mm depletion at faces) |
| PD50 / coated AR | PD50 not defined (no front); coated AR = full AR for all three | v083-v085 (calculated from "full thickness infiltrated") |
| Step coverage | not stated; centre/max EDS ratio for 160 C computed from points (signal, not thickness) | v089 (0.89) |
| Sticking / reaction probability | not stated | Eq. 1 design inputs (D, gamma, L_pore) are in Note S1, not in the main text: v017 |
| Recombination | not applicable (thermal process) | |
| Composition / phases | found (XRD wt%) | v043-v054; phases v056-v058 |
| Crystallinity / crystallite size | found | v044, v048, v050, v053; corundum grain v009 |
| Resistivity | found (one prism per run) | v046, v051, v055; current v059 |
| Roughness | not stated | |
| Colour | found | v060-v063 |
| In-situ reaction data (Δn_g, ȳ, terminal slope) | found (table values); per-cycle curves not read | v022/v028/v034, v023/v029/v035, v066-v073; series s3b_*, s3c_* (not read) |
| Purge model (Eq. 2) | found | v012 (theta_f), v013 (nu), v014/v015 (360 / 11 min), v016 (48 min chosen); E_des not stated in main text |
| XPS composition | not read: atomic % are in supplementary Figs. S3-S4, not in main text | |
| Supplementary pressure traces (all 20 cycles), Note S3 raw data | not read: supplementary material not in corpus | |
