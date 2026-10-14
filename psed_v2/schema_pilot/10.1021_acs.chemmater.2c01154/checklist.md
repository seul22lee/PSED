# Checklist: 10.1021_acs.chemmater.2c01154 (mat22)

Planar films only; the paper has no test structure. Supporting Information is not in document.md, so anything only in Figs. S1-S22 or Tables S1-S8 is "not in document".

| Quantity | Status |
|---|---|
| Structure dims / feature width | not applicable (planar). Substrate pieces 1x1 to 3x3 cm2 (condition `substrate_size`), 4 inch wafer (W1), 15x15 cm PET (PET) |
| Deposition temperature | found: 50-450 °C table setpoint per sample (sample.csv temperature_C). Exp. section notes the real substrate is cooler at >=200 °C (condition `temperature_reported_as`) |
| Exposure / partial pressure x time, step A | not stated as exposure or partial pressure. Found: 6 s pulse at 200 mTorr total (set by the valve), source at 50 °C, 50 sccm Ar carrier (condition rows, step A) |
| Exposure, plasma step | not stated. Found: 20 s at 100 W, about 6 mTorr, flows per H2 ratio from Table 2 (per-sample gas_flow_rate rows) |
| Purge times | found: 10 s after A (6 s flow + 4 s pump), 6 s after plasma, 300 sccm Ar; cycle 51 s |
| Cycles | found: per sample (100/120/140 rule for the grid; 10-500 for named samples); RBS films: not stated |
| Planar GPC | found: 32 grid cells read from the Fig. 7b colour scale (mat22:v065-v096, ±0.03 Å/cycle; checked against Fig. 7a at 150 °C). Mo atoms per cycle by RBS (v190-v192). Saturation curves (Fig. S1): not in document |
| Film thickness | found: Fig. 1b legend (v140-v143), wafer mean/sd (v144, v145), Fig. 7a at 140 cycles read by eye (v134-v139), ~50 nm RBS/TEM films (v173, v181, v189, v196), ~5 nm PET/FET films (v147, v150...) |
| Thickness profile / PD50 / step coverage | not applicable (no 3D structure) |
| Uniformity | found: 3.3% sigma over 4 inch wafer (v146); map points from points.json (series s1c_map) |
| Sticking / reaction probability | not stated |
| Recombination probability | not stated (OES only qualitative: H, S, S+, S2, SH+, H2S+ seen; Fig. S20-S21 not in document) |
| Composition | found: S/Mo by XPS for all 32 grid cells (Fig. 4, v033-v064), Fig. 5 labels (v129-v133), RBS/ERD Table 1 (v166-v189), WS2/TiS2 ratios (v247ff). Table S1/S7: not in document |
| Crystallinity | found: 32 grid cells (Fig. 2, v001-v032) and named samples; XRD (Fig. S2) not in document |
| Roughness | found: Rq for 6 ratios at 150 °C (Fig. 6a, v198-v208), 0.75 nm for the 100 °C TEM/FET film (v154) |
| Density | found: Table 1 (v168, v176, v184), bulk literature value 5.06 (v195) |
| Resistivity | found: 32 cells read from the Fig. 8 log colour scale (v097-v128; checked against the text values 15, 220, 2 Ω cm and 4 mΩ cm), text values (v225-v230), PET 0.3 Ω cm (v148), WS2 4 Ω cm. Table S2: not in document |
| Carrier density / mobility | found as text ranges (v231-v239, v194); per-sample Hall data (Sec. S10) not in document |
| XPS binding energies | found (v210-v221) |
| Raman peak positions | not read (only peak labels in Figs. 1, 9; no numbers printed) |
| FET metrics | on/off 3-4, current ratio >10, contact behaviour, interface layer thickness (v157-v165); the curves (Fig. S13) are not in the document |
