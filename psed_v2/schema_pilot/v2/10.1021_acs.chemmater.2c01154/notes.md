# mat22 (10.1021_acs.chemmater.2c01154): v2 extraction notes

`build.py` writes all tables. 69 samples / 212 conditions / 60 series / 245 values; 213 inventory elements in coverage.csv (161 covered, 52 no knowledge).
Supporting Information is not in the document; values that exist only there (Raman spectra behind Fig. 2, Table S2 resistivities, Hall data, Table S7/S8) are not extracted.

## Decisions
- **Grid**: 32 runs `g<T>_<ratio>` with the group `mat22:grid`. Each run has its own deposition_temperature{kind=set_point} and H2 flow ratio conditions (other, "H2 flow ratio"). Cycles follow the s5.p7 rule. It is stated once on the group with applies_when (100 at 450 °C; 120 at 50/300/350 °C; 140 at 100–250 °C).
- **Table 2 flows** are 21 gas_flow_rate conditions on `mos2_tab2` with applies_when "H2 flow ratio = x". The recipe (pulse and purge times, pressures, power, source temperature) is on `mos2_all`. The two low-H2S runs (s3.p53) are in mos2_all but not in mos2_tab2, because their flows differ and are only in the SI.
- **Measurement settings** (SE, Raman, XPS, AFM, SEM, RBS, TEM, Hall) are `*` conditions with applies_when "measured by …".
- **Links that are not stated:** Figs. 1a, 5, 6a and 7a show 150 °C films at the same ratios and cycle count as the grid. Their series point to the 150 °C grid runs with link_status=inferred. Two checks support the link. The S/Mo values printed in Fig. 5 equal the Fig. 4 cells. Thickness at 100 cycles in Fig. 7a divided by 100 matches the Fig. 7b GPC cells within 0.03 Å/cycle for all six ratios.
- **Same sample for TEM and FET:** Fig. 3 TEM films and FET films are one sample each (fet100, fet350), because s5.p18 says the thin 100/350 °C TEM samples went through transistor patterning.
- **Table 1 films are separate from the Fig. 6b film:** the Table 1 films (rbs020/065/080) are on glassy carbon; tem065 (Fig. 6b) is on SiO2. They are kept separate; co-deposition is possible but not stated.

## Heat maps read against the colour bar (Figs. 7b and 8)
Each cell was read as the median RGB of its centre (about 13×15 px). It was matched to the nearest pixel of the colour-bar column. That position was converted using the tick pixels: Fig. 7b is linear, 0.50–1.75 Å/cycle; Fig. 8 is log, 35.5 px per decade, 1e-3 to 1e3 Ω cm, with a black ">dl" band at the top. The RGB match distance was 5 or less for almost all cells. Stated uncertainty: ±0.03 Å/cycle and ±0.15 in log10 ρ.
- The seven black Fig. 8 cells are stored as censor=">dl" with value 1000, the detection limit stated in s3.p34.
- Fig. 7b cell 50 °C/0.20 is black, at the top of the bar. It is stored as 1.75 and may be clipped.
- The readings agree with the text: 15 Ω cm (300 °C/0.20), 220 Ω cm (450 °C/0.20), 2 Ω cm (100 °C/0.65) and 4 mΩ cm (0.94).
- Fig. 2 classes and the Fig. 4 printed S/Mo values are exact. Fig. 4 shows the same 32 cells.

## Points
- Fig. 1c: points from cases/points.json.
- v1 points accepted after the check: Figs. 1a (0.94/0.80/0.65), 1b substrate, 5a (5 spectra), 7a (6 curves) and 9a/9b (4 spectra). The clipped Si point at 518 cm-1 was dropped from Fig. 1a.
- Rejected v1 sets have no points: Fig. 1b films, 5b, and the heat maps.

## Source problems and conflicts
- WS2 composition: WS2.1 in s3.p46 but WS2.2 in the conclusions (s4.p1). Both are stored, each with a note.
- c-MoS2 S/Mo range: 1.8–2.3 in s3.p11 but 1.8–2.2 in s3.p39. Both are stored.
- The 150 °C/0.20 film: a-MoS3.4 in s3.p52 (equal to the Table 1 XPS value of the ~50 nm film), while the Fig. 4 cell prints 3.5.
- Fig. 6a prints Rq 4.0 nm at 0.94 and 3.1 nm at 0.80. The text calls 0.80 the roughest ratio overall.
- Mo atoms per cycle (0.6/1.6/2.2 at/nm²/cycle): the films are not named. These values are assigned to the 150 °C RBS films. The hole concentration of rbs065 (~2e21 cm-3) is derived as 6e21/3 from s3.p39.
- s3.x1–x7 are body copies of the captions. They are cited wherever the matching caption is cited.
- The abstract was checked against the body and adds nothing new. Introduction numbers are background (no knowledge), except earlier PEALD temperatures, which are kept as literature values.
