# Checklist: 10.1039_d0cp03358h (yim20)

Value ids are in value.csv; condition rows are in condition.csv. The ESI (Tables S1-S5, Figs. S1-S17) is not in the corpus, so anything given only there is marked "not read (ESI)".

| Quantity | Status |
|---|---|
| Structure: class | PillarHall-3 lateral channel, a polysilicon membrane roof on pillars over Si (sample.csv) |
| Structure: channel height H | Design 100, 500 and 2000 nm per sample (sample.csv, from Table 1). Tolerances ±10, 20 and 30 nm: v158-v160. Membrane deflection about 25, 25 and 40 nm: v165-v167. Entrance nanostep 2-5 nm: v157 |
| Structure: channel length L | 0.1-5 mm (v180). Maximum AR 10000:1 at L 5000 µm (v179). AR per channel is in ESI Table S1, not read (ESI) |
| Structure: pillars | Layout per sample (condition pillar_layout). Diameter 4 µm and spacing 49 µm (v163, v164). Effect on PD below 1% (v162). Layout details are in ESI Table S2, not read (ESI) |
| Structure: opening width W | Not stated. The hydraulic diameter of 1.0 µm (v174) implies W >> H |
| Deposition temperature | 300 °C (condition `*`) |
| Process pressure | About 3 hPa total (condition `*`). The TMA and H2O partial pressures of the experiments are not stated |
| Exposure (pressure × time) per step | Not stated for the experiments; only the pulse times are given. Model: p_A0 = 65 Pa (v184) × t_p = 0.10 s (v183), both chosen inputs |
| Pulse / purge times | Per sample, four rows each (condition.csv): TMA pulse 0.1/0.2/0.4 s, H2O pulse 0.1 s, purges 1/4/10 s |
| Source temperatures | Not stated in the paper |
| Carrier flow | N2 150 sccm through four lines; whether this is the total or per line is not said (condition `*`) |
| Cycles | Per sample 250/500/1000 (condition.csv). u1 (AFM sample): 500 |
| Planar GPC | GPC_I per sample, 0.0897-0.103 nm/cycle (Table 1 rows, e.g. v003). Not measured for sample 7. Model gpc_sat 0.098 (v192) |
| GPC inside the channel | GPC_IIb per sample (e.g. v004) |
| Film thickness | S_I and S_IIb per sample (e.g. v001, v002). SD of S_IIb 2.8 nm (v171). Thickness that plugs the 100 nm entrance: 50 nm (v156) |
| Profile | 81 series rows. Points from points.json for 9 series (Fig. 9c ×3, 9f ×3, 10c ×3). All other curves not read (no points.json entry) |
| PD50 | Per sample (e.g. v005), with x~50 (e.g. v006). Read from points: v210-v215 measured, v216-v218 model. 104.8/213.1/188.6/230.3/190.8 vs the Table's 100/214/188/230/190. Visual extents: v143, v144. EDS extent: v145. SD 19.4 µm (v169) |
| Front slope / width | d(S/N)/dx~ and dθ/dx~ with R², per sample (e.g. v007-v009). SD (v170). Front width about 30 µm (v149) |
| Sticking coefficient | c_TMA 4e-3 (v177, mean over samples 2, 4, 8 and 12). c_H2O 3e-4 (v178, sample 14). Model c_TMA 0.012 (v196). Literature: v219-v226, v228, v229 |
| Sticking-coefficient check (this pilot, not stored as values) | 13.9·(dθ/dx~)² from Table 1 gives 1.7e-3, 5.0e-3, 5.0e-3 and 6.1e-3 for samples 2, 4, 8 and 12 (mean 4.5e-3), and 2.7e-4 for sample 14. This agrees with Table 2. The per-sample spread is 3.6× |
| Mean free path / Knudsen number | TMA 40 µm, H2O 100 µm (v172, v173). Kn 40 and 100 (v175, v176) |
| Channel filling | 10/20/40% for 250/500/1000 cycles (v153-v155). Recommended below 10% (v181) |
| Recombination probability | Not applicable (thermal process) |
| Step coverage | Not stated (a profile is given instead) |
| Composition | Not stated. The EDS O/Al/Si intensities (Fig. 5b) are a signal, not a composition. ESI Fig. S8 not read (ESI) |
| Crystallinity | Not stated |
| Roughness | Described in words only (Region IIa waviness, Fig. 6). The AFM Z range of 3.081 µm (v147) includes membrane remnants, so it is not a roughness value. The AFM line scan is in ESI Fig. S6, not read (ESI) |
| Resistivity | Not stated |
| Film density | Model input 3.1 g/cm3 (v193). Ylilammi 2018's 4.0 g/cm3 (v227) |
| Measurement uncertainty | Scan positioning about 2 µm (v168). PD sensitivity to H: 1.5%/% (v161). Spot sizes v150-v152 |

Standard-deviation note: the PD50 SD of 19.4 µm and the S_IIb SD of 2.8 nm match the sample SD (n−1). The slope SD of 0.0003 nm matches the population SD (0.00031); the sample SD would be 0.00036.
