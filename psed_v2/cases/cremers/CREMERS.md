# Cremers 2019 read as data

Exploration, 2026-10-13. The review is Cremers, Puurunen and Dendooven, Appl. Phys. Rev. 6, 021302 (2019). Its Tables II to VII were typed in by hand (`transcribe.py`) and every row was compared with the page image. All values are data_kind cited; blank cells stay blank; footnote markers are in `note`.

Files: `conformality.csv` (140 rows), `parameters.csv` (68 rows), `source_checks.csv`, `new_rows.csv`, `profiles.csv`, `build.py`. Plots: Case 8 of `../reports/cases.html` (not tracked).

Updated the same day after 15 PDFs were obtained by hand (refs 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228, 251 and 10.1021/acs.jpcc.1c01505). `in_corpus` (was `in_44`) marks rows whose source is in scope and has a PDF; `source_scope` says "out of scope, cited source" for rows whose source is excluded (the Table VII sources, refs 250 to 263, and ref. 134), whose values are kept only as cited data; `value_from_source` holds what the source gives for cells the review leaves blank, and never replaces a transcribed value. What the new sources changed is said under each result.

## Step 1. Transcription

| Table | Content | Rows | Rows whose source is in scope with a PDF |
| --- | --- | --- | --- |
| II | thermal ALD | 71 | 16 |
| III | ozone-based ALD | 24 | 5 |
| IV | plasma ALD | 45 | 10 |
| V | sticking probabilities | 27 | 13 |
| VI | ozone recombination | 6 | 0 |
| VII | atom recombination | 35 | 0 |

Things seen while typing that a reader of the tables should know:
- The PD50% mark is an asterisk. It is lost in the PDF text layer, so it was read from the page images.
- Five reference numbers, in seven rows, have no DOI in the manifest (150, 168, 176, 201, 213).
- Table IV uses a plasma configuration "HW" that its caption does not define.
- Table V lists the ref. 77 value for TiCl4 on a line whose material cell is empty under "TiN"; the source deposits TiO2.
- The running text and the tables disagree in three places: ozone Al2O3 (text 20:1, table "Ref. 175"), the reference for ozone V2O5 (text 78, table 150), and O on Pyrex (text 0.000094, table 0.000045).

## Step 2. Source checks

48 rows point to a paper with a PDF (four of them to ref. 251, out of scope and kept as a cited source): 35 agree, 10 differ, 3 not found. Of these, 16 were checked against papers parsed before 2026-10-13 and 32 against the papers whose PDFs were obtained by hand that day (25 agree, 6 differ, 1 not found). `value_from_source` is filled in 11 rows: 5 give a value the review lacks, 6 record that the source does not state the exposure either.

| Table | Row in the review | Ref. | Paper | Verdict | Where | Remark |
| --- | --- | --- | --- | --- | --- | --- |
| II | Al2O3 TMA/H2O, LHAR, 300 °C, coated 130* (D) | 77 | 10.1063_1.5028178 | agree | Fig. 6, Table I | half thickness at about 133 µm (by eye) in a 0.5 µm gap gives 133 with the trench formula; the 300 °C is not in the parsed text; the printed EAR 10-12500 is the chip family, the sample has L 1 mm (AR 2000) |
| II | TiO2 TiCl4/H2O, LHAR, 110 °C, coated 90* (D) | 77 | 10.1063_1.5028178 | agree | Fig. 7 | half of the entrance thickness at about 90 µm (by eye); the profile has no plateau; the 110 °C is not in the parsed text |
| III | TiO2 TDMAT/O3, CNT, 100 °C, exposure 4500 | 98 | 10.1039_c3ra42928h | agree | experimental section | 0.3 mbar for 20 s is 4.5 Torr s, i.e. 4500 × 10^3 L; the review computed the exposure, the source does not print it |
| II | TiO2 TTIP/H2O, VACNT, 225 °C, (D) | 100 | 10.3762_bjnano.5.25 | agree | methods, Fig. 6b | 225 °C, TTIP and water, thickness against depth; no aspect ratio in the source either |
| II | TiO2 TiCl4/H2O, AAO, EAR 7.5, 200 °C, coated 7.5 | 140 | 10.1186_s11671-015-0872-9 | agree | abstract, methods | 500 nm deep, 67 nm pores, 7.5:1, filled |
| II | Fe3O4 Fe(Cp)2/O2, AAO, 400 °C | 144 | 10.1038_srep18401 | agree | methods | ferrocene and oxygen at 400 °C; no pore dimensions found, as in the review |
| II | Ir Ir(acac)3/O2, trench, 370 °C (thermal table) | 169 | 10.1016_j.mee.2018.01.027 | not found | process section | precursors agree; 370 °C is not in the parsed text; the source says oxygen can be supplied thermally or through the plasma and does not say which was used, and gives a 30 µm depth the review leaves out |
| IV | Ir Ir(acac)3/O2*, trench, 370 °C (plasma table) | 169 | 10.1016_j.mee.2018.01.027 | not found | process section | same paper listed in both tables; mode not stated in the source |
| II | Pt MeCpPtMe3/O2, AAO, EAR 200, coated 50 | 173 | 10.1007_s12274-010-0066-9 | differ | text on AAO templates, Fig. 2 | 60 µm thick with 250 to 300 nm pores gives 200 to 240; the source gives a penetration that saturates near 20 µm (about 70 to 80) and tubes 15 µm long (about 50 to 60): the review took the tube length |
| II | Pt MeCpPtMe3/O2, hole, EAR 90, coated 30 | 173 | 10.1007_s12274-010-0066-9 | agree | Fig. 3e-f | 30 µm of a 90 µm pore of 1 µm; the same figure shows 90 µm reached with added exposure time, which the review does not list |
| III | Pt Pt(acac)2/O3, AAO, EAR 120, 150 °C, coated 50 | 196 | 10.1039_c5ta00205b | differ | abstract, text at Fig. 6 | coated 50 agrees; the structure value 120 was not found (the abstract says 70); both 130 and 150 °C were used |
| IV | Al2O3 TMA/O2*, trench, EAR 15, coated 15* | 202 | 10.1149_2.067203jes | differ | conformality paragraph, Fig. 8 | the source tests SiO2 only; the alumina in that trench is an underlayer for contrast, and no half-thickness depth is given |
| IV | SiO2 H2Si[N(C2H5)2]2/O2*, trench, EAR 15, coated 15 | 202 | 10.1149_2.067203jes | agree | conformality paragraph, Fig. 8 | aspect ratio about 30 for a trench is 15; 95 to 100% bottom to top |
| IV | Ir Ir(acac)3/O2*, hole (elongated), 370 °C, I | 226 | 10.1016_j.mee.2018.01.033 | agree | methods | 370 °C, oxygen plasma, inductively coupled |
| V | Al(CH3)3 on Al2O3, continuum model, 300 °C, 0.00572 | 77 | 10.1063_1.5028178 | agree | Table I, Eq. for the adsorption rate | c = 0.00572; c multiplies (1 − θ), so it is an initial (bare-surface) value, called a lumped sticking coefficient |
| V | TiCl4 on TiN, continuum model, 110 °C, 0.1 | 77 | 10.1063_1.5028178 | differ | Table I | value agrees (0.10) but the source deposits TiO2; TiN is carried over from the line above in the table |
| II | Al2O3 TMA/H2O, macro lateral, EAR 100, 200 °C, exposure 9, coated 50* (D) | 67 | 10.1149_1.3072694 | agree | experimental section, Fig. 5 | 0.3 Pa for 4 s is 1.2 Pa s, i.e. 9.0 × 10^3 L; aspect ratio 100 by the source's perimeter definition; half thickness at about 10.7 of 20 mm (by eye) gives 53 |
| II | Al2O3 TMA/H2O, AAO, EAR 770, 177 °C, exposure 4500, coated 770 | 65 | 10.1021_cm0303080 | agree | Sec. III A, Fig. 3 | 65 nm x 50 um gives 769; 0.15 Torr for 30 s is 4500 × 10^3 L. The source coats the membrane already at 3 s (450) and the pores are open at both ends: the review lists the largest exposure used and the full length |
| II | ZnO DEZ/H2O, AAO, EAR 700, 177 °C, exposure 2000, coated 700 (D) | 65 | 10.1021_cm0303080 | differ | Sec. III B, Fig. 5 | exposure agrees (0.068 Torr for 30 s); the membrane is the same 65 nm x 50 um one that the Al2O3 row lists as 770 |
| II | ZnO DEZ/H2O, AAO, EAR 5000, 177 °C, exposure 600000, coated 5000 (D) | 65 | 10.1021_cm0303080 | agree | Sec. III B, Fig. 7 | 19 nm x 92 um; 5 Torr for 120 s |
| II | Al2O3 TMA/H2O, LHAR, 300 °C, coated 75* (D) | 86 | 10.1116_1.4903941 | agree | Fig. 4, Fig. 5a | film to 65 um in a 500 nm gap (AR 130, stated), half thickness near 70 um by eye: 65 to 70 with the trench formula; EAR range 10 to 12500 matches half of the Fig. 1 table |
| II | TiO2 TiCl4/H2O, LHAR, 110 °C, coated 65* (D) | 86 | 10.1116_1.4903941 | agree | text to Fig. 5b | 50% of the entrance value at AR 130, stated; the profile has no plateau |
| II | Al2O3 TMA/H2O, macro lateral, EAR 5, 75 °C, exposure 18, coated 2.5* (D) | 69 | 10.1016_j.surfcoat.2012.02.038 | agree | Sec. 2, Fig. 5 | 0.08 Pa for 30 s is 18 × 10^3 L; half value at 27 mm of a 1 cm wide hole. The hole is filled with a fibre non-woven, which the row does not say: its EAR is not that of an empty hole |
| II | HfO2 Hf(NMe2)4/H2O, holes, EAR 36, 150 °C, exposure 9, coated 36 | 62 | 10.1002_cvde.200390005 | agree | Sec. 4, Sec. 6 | elliptical holes 0.17 x 0.30 x 7.3 um, aspect ratio 36 by the source; 9 × 10^3 L is the calculated minimum, the fully coated sample had 30 |
| III | TiO2 TDMAT/O3, hole, EAR 20, 180 °C, coated 20* (D) | 178 | 10.1016_j.apsusc.2009.02.055 | differ | Sec. 2, Fig. 3 | the source writes AR = 20 for holes of 130 nm x 2 um, which is 15.4 (the review uses 15.3 for the same holes in the ref. 180 rows); the profile falls only to 70% of its top value, so no half-thickness depth exists |
| III | TiO2 Cp*Ti(OMe)3/O3, hole, EAR 15.3, 270 °C, (D) | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Sec. 3, Fig. 3 |  |
| III | HfO2 TEMAHf/O3, hole, EAR 15.3, 180 °C, coated 9.6* (D) | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 1a | half of 18.8 nm near 1250 nm, over 130 nm; the 230 and 270 °C profiles of the same figure are not listed |
| IV | Al2O3 TMA/O2*, macro lateral, EAR 10, 200 °C, RI, exposure 27, coated 10 (D) | 70 | 10.1149_1.3301664 | differ | experimental section, Fig. 2b | structure, temperature and coating agree (thickness falls to about 75% at the end, above one half); the exposure does not reproduce: 0.3 Pa for 9 s is 20, for 18 s it is 40 |
| IV | Al2O3 TMA/O2*, macro lateral, EAR 5, 75 °C, RI, exposure 5, coated 0.75* (D) | 69 | 10.1016_j.surfcoat.2012.02.038 | differ | Fig. 10 | exposure agrees as the TMA exposure (0.08 Pa for 8 s); the plasma profile is at half its entrance value near 3 mm, i.e. about 0.3, not 0.75 |
| IV | Al2O3 TMA/O2*, hole, EAR 10, 225 °C, exposure 30, coated 10 | 200 | 10.1063_1.2714685 | agree | Sec. IV, Fig. 7 | 0.3 um holes of aspect ratio 10; 0.01 Torr for 3 s is 30 × 10^3 L, a TMA exposure |
| IV | TiO2 TTIP/O2*, hole, EAR 8.7, 225 °C, coated 8.7 (D) | 204 | 10.1149_1.2789802 | agree | experimental conditions, Fig. 2b, Fig. 4 | full coverage needs a long TTIP pulse; at 5 s the bottom has 52% (Fig. 4, 5) |
| IV | AlN TMA/NH3*, macro lateral, EAR 10, 200 °C, RI, exposure 40, coated 2.5* (D) | 70 | 10.1149_1.3301664 | agree | Fig. 5b | 0.3 Pa for 18 s is 40 × 10^3 L; half thickness at 4 to 5 of 20 mm |
| IV | Pt MeCpPtMe3/O2*, trench, EAR 17, 300 °C, I, coated 17 (D) | 228 | 10.1063_1.4972120 | agree | Table II, Fig. 5 | trench aspect ratio 34, conformality 92 ± 8% |
| V | Al(CH3)3, Monte Carlo model, 177 °C, 0.001 | 65 | 10.1021_cm0303080 | differ | Sec. IV D | the value is quoted there from an earlier paper and used as an input; it is not derived with the Monte Carlo model |
| V | Al(CH3)3, ballistic model, 225 °C, 0.026 | 200 | 10.1063_1.2714685 | agree | Sec. IV, Fig. 8 | an initial sticking probability, fitted, for TMA in the TMA/O2 plasma process |
| V | Al(CH3)3, semi-analytical model, 200 °C, 0.1 | 67 | 10.1149_1.3072694 | differ | text to Fig. 6 | 0.1 is a value chosen for the simulation; the source says a fit would need the pressure to 0.01 Pa and does not make one |
| V | Al(CH3)3, Monte Carlo model, 200 °C, 0.02 | 128 | 10.1116_1.4971196 | agree | Sec. IV A 3 | fitted; range 0.009 to 0.02 |
| V | Hf(NEtMe)4, Monte Carlo model, 180-270 °C, 0.03-0.6 | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 1 | 0.031, 0.15, 0.56 at 180, 230, 270 °C |
| V | Ti(NMe2)4, Monte Carlo model, 180 °C, 0.02 ± 0.005 | 178 | 10.1016_j.apsusc.2009.02.055 | agree | Fig. 4 | from four thickness points |
| V | Ti(OiPr)4, ballistic model, 125-225 °C, 0.04-0.1 | 204 | 10.1149_1.2789802 | agree | Fig. 7b, Table II | initial sticking probability with an adsorption order |
| V | Cp*Ti(OMe)3, Monte Carlo model, 270 °C, 0.01 | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 3 | range 0.006 to 0.018 |
| V | ZnEt2, Monte Carlo model, 177 °C, 0.007 | 65 | 10.1021_cm0303080 | not found | Sec. IV C | 0.007 is the value used in the simulations; how it was obtained was not found |
| V | SiCl4, Monte Carlo model, 10^-8 | 65 and 239 | 10.1021_cm0303080 | agree | Sec. III C, IV D | quoted there from the second reference |
| V | H2Si[N(C2H5)2]2, Monte Carlo model, 300 °C, 3 × 10^-5 | 128 | 10.1116_1.4971196 | agree | Sec. IV B 3 | fitted; range 3 to 5 × 10^-5 |
| VII | O on alumina, 0.0097 ± 0.0019 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K, ± 20%, on a sintered ceramic in an air plasma at 110 Pa; 0.061 at 773 K |
| VII | O on titania, 0.014 ± 0.003 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K; 0.031 at 773 K |
| VII | O on iron(II, III) oxide, 0.015 ± 0.003 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K |
| VII | O on cobalt oxide, 0.029 ± 0.006 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | CoO at 300 K |

## Step 3. Computed

### a. Exposure coverage

| Table | Rows | Rows with an exposure |
| --- | --- | --- |
| II | 71 | 20 |
| III | 24 | 1 |
| IV | 45 | 6 |

TMA/H2O, coated EAR against exposure (10^3 L):

| Structure | EAR | T (°C) | Exposure | Coated EAR as printed | Reading | Ref. |
| --- | --- | --- | --- | --- | --- | --- |
| Macro lateral | 100 | 200 | 9 | 50* (D) | measured (PD50%) | 67 |
| Trench | 5 | 300 | — | 5 | lower bound | 134 |
| AAO | 8.5 | 200 | 300 | 8.5 | lower bound | 135 |
| Nanorods (ZnO) |  | 300 | 560 | Conformal | no number | 99 |
| Pillars (Si) |  | 125 | — | Conformal | no number | 93 |
| AAO | 1750 | 177 | — | 1750 | lower bound | 96 |
| AAO | 770 | 177 | 4500 | 770 | lower bound | 65 |
| LHAR | 10-12500 | 300 | — | 75* (D) | measured (PD50%) | 86 |
| LHAR | 10-12500 | 300 | — | 130* (D) | measured (PD50%) | 77 |
| Trench | 11 |  | — | 11 | lower bound | 138 |
| Macro lateral | 5 | 75 | 18 | 2.5* (D) | measured (PD50%) | 69 |
| Hole | 17 | 200 | 370 | 17 | lower bound | 139 |

Of the six rows with an exposure, two are measured depths, three are lower bounds and one has no number. The two measured ones do not order by exposure (50 at 9, 2.5 at 18): the second is a hole filled with fibres at 75 °C (ref. 69, now read).

What the new sources add. From the sources, at the same exposures:

| Exposure (10^3 L) | Coated EAR | Reading | Structure | Where |
| --- | --- | --- | --- | --- |
| 9 | 33 | lower bound | macro hole, aspect ratio 33, fully coated | 10.1149_1.3072694 Fig. 5 |
| 9 | 47 | measured, by eye | macro hole, aspect ratio 50, half thickness at about 19 of 20 mm (by eye) | 10.1149_1.3072694 Fig. 5 |
| 9 | 53 | measured, by eye | macro hole, aspect ratio 100, half thickness at about 10.7 mm (by eye) | 10.1149_1.3072694 Fig. 5 |
| 450 | 385 | lower bound | AAO 65 nm x 50 um, coated from both ends at 3 s | 10.1021_cm0303080 Fig. 3 |
| 150 | 385 | upper bound | the same membrane at 1 s: centre not coated | 10.1021_cm0303080 Fig. 3 |

The kinetic model of ref. 62 gives the exposure for full coverage as a flat-surface exposure times (1 + 19a/4 + 3a²/2). For TMA at 200 °C with 4.5e+18 molecules per m² per cycle (the saturation value of 10.1063_1.2714685, an assumption here) the flat-surface exposure is 2.4 L, and 9 × 10^3 L should coat an aspect ratio of 49. Ref. 67 measures 47 to 53 at that exposure. For the 65 nm by 50 µm membrane of ref. 65 the model asks for 530 × 10^3 L when the pores are entered from both ends (aspect ratio 385) and 2106 × 10^3 L if they were entered from one; the source finds the centre uncoated at 150 and coated at 450. Two sources test the square law of ref. 62 for TMA and water. For ref. 67 it predicts a coated aspect ratio of 49 at 9 × 10³ L, against 47 and 53 read by eye and one fully coated structure of 33 (a lower bound), so it matches. For ref. 65 it asks for 530 × 10³ L, while the centre of the membrane was already coated by an exposure between 150 and 450 × 10³ L, so there the model overestimates the need by about 1.2 to 3.5 times. The ref. 65 comparison counts the membrane at half its length, which the source supports: it states that the top and bottom of the membrane are both directly exposed to the precursors in the flow tube (Sec. III A), and its model has the pores entered from both ends at equal rates, over half their length (Sec. IV A). The review's 770 at 4500 is a fully coated structure at about eight times the predicted need. The blanks of refs 86 and 77 cannot be filled from their sources.

### b. EAR check and the unit conversion

| Source | Dimensions | Formula | Computed | Printed | Result |
| --- | --- | --- | --- | --- | --- |
| 10.1186_s11671-015-0872-9 (ref. 140) | hole, 500 nm deep, 67 nm wide | L/w | 7.5 | 7.5 | agree |
| 10.1007_s12274-010-0066-9 (ref. 173) | hole, 90 µm deep, 1 µm wide | L/w | 90 | 90 | agree |
| 10.1007_s12274-010-0066-9 (ref. 173) | AAO, 60 µm thick, 250 to 300 nm pores | L/w | 200 to 240 | 200 | agree |
| 10.1149_2.067203jes (ref. 202) | trench, 18.5 µm deep, 0.6 µm wide | L/(2w) | 15 | 15 | agree |
| 10.1063_1.5028178 (ref. 77) | lateral channel, half thickness at about 133 µm, gap 0.5 µm | L/(2w) | about 133 | 130 (coated) | agree |
| 10.1039_c5ta00205b (ref. 196) | AAO; dimensions of the coated membrane not found | L/w | — | 120 | cannot check |
| 10.1116_6.0001094 (not a review row) | trench, 20 mm deep, 1 mm opening | L/(2w) | 10 | 10 (stated by the source) | agree |
| 10.1021_acs.jpcc.5c06502 (not a review row) | lateral channel, PD50% 4.4 µm, gap 0.5 µm | L/(2w) | 4.4 | 4.4 (stated by the source) | agree |
| 10.1002_cvde.200390005 (ref. 62) | elliptical holes 0.17 x 0.30 um, 7.3 um deep | L(w+z)/(2wz) | 34 | 36 | agree (the source computes 36 from the true perimeter) |
| 10.1149_1.3072694 (ref. 67) | rectangular hole 5 x 20 mm, 0.1 mm high (height from the review's Fig. 22) | L(w+z)/(2wz) | 102 | 100 | agree |
| 10.1149_1.3301664 (ref. 70) | rectangular hole 5 x 20 mm, spacer 3.9, 1.3, 0.5 mm | L(w+z)/(2wz) | 4.6; 9.7; 22 | 10 (the row used) | agree |
| 10.1021_cm0303080 (ref. 65) | pores 65 nm x 50 um; 19 nm x 92 um | L/w | 769; 4840 | 770 and 700 for the first; 5000 | agree, but one membrane has two values; pores open at both ends, so the diffusion length is half |
| 10.1016_j.apsusc.2009.02.055 and 2010.01.025 (refs 178, 180) | holes 130 nm x 2 um, the same in both papers | L/w | 15.4 | 20 (ref. 178 row); 15.3 (ref. 180 rows) | differ for ref. 178: 20 is the number the source writes, not what its dimensions give |
| 10.1063_1.2714685 (ref. 200) | holes 0.3 um, aspect ratio 10 stated | L/w | 10 | 10 | agree |
| 10.1149_1.2789802 (ref. 204) | holes 0.15 um, aspect ratio 8.7 stated | L/w | 8.7 | 8.7 | agree |
| 10.1063_1.4972120 (ref. 228) | trenches, aspect ratio up to 34 | L/(2w) | 17 | 17 | agree |
| 10.1116_1.4903941 (ref. 86) | lateral channels, aspect ratio 20 to 25000 (Fig. 1 table) | L/(2w) | 10 to 12500 | 10-12500 | agree |
| 10.1016_j.surfcoat.2012.02.038 (ref. 69) | hole 1 x 1 x 5 cm filled with fibres | L/w | 5 for the empty hole | 5 | agree as a hole; the fibre filling is not in the number |

The conversion in Sec. II D is printed as "1 L = 10^6 Torr s = 7500 Pa s". Both parts are wrong as printed: 1 L is 10^-6 Torr s, which is 1.33 × 10^-4 Pa s, and it is 1 Pa s that equals 7500 L. The tables use the correct relation: the review's own Fig. 22 gives 0.27 Pa for 4 s, which is 8100 L against the 9 × 10^3 L of the first row of Table II, and the ref. 98 row reproduces from the source's pressure and pulse time.

### c. Recombination probability against coated EAR (Table IV with Table VII)

Mappings used: Al2O3 → O on alumina (O2 plasma; the growing surface is alumina); SiO2 → O on silica (O2 plasma; silica); TiO2 → O on titania (O2 plasma; titania); Ni → H on nickel (H2 plasma on a nickel film); Cu → H on copper (H2 plasma on a copper film).
Left out: HfO2, Ta2O5 (no hafnia or tantala surface in Table VII); Ti (TiCl4/O2*) (film printed as Ti; unclear whether metal or oxide); AlN, SiNx, TiN, Mo2N, TaN (Table VII has N and H on metals, silicon, silica and steel, but on no nitride); Co, Ru (NH3*) (no cobalt or ruthenium surface for H or N); Ag, Ta (H2*) (no silver or tantalum surface); Ir, Pt (O2*) (no noble-metal surface for O atoms in Table VII (Table VI has ozone on Pt only)).

| Film | Process | Structure | EAR | Coated EAR | Reading | r from Table VII | Ref. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Al2O3 | TMA/O2* | Macro lateral | 10 | 10 | lower bound | 0.0021 to 0.0097 | 70 |
| Al2O3 | TMA/O2* | Hole | 8 | 8 | lower bound | 0.0021 to 0.0097 | 197 |
| Al2O3 | TMA/O2* | Trench | 13.5 | 13.5 | lower bound | 0.0021 to 0.0097 | 198 |
| Al2O3 | TMA/O2* | Macro lateral | 5 | 0.75 | measured (PD50%) | 0.0021 to 0.0097 | 69 |
| Al2O3 | TMA/O2* | Hole | 10 | 10 | lower bound | 0.0021 to 0.0097 | 200 |
| Al2O3 | TMA/O2* | Trench | 2 | 2 | lower bound | 0.0021 to 0.0097 | 201 |
| Al2O3 | TMA/O2* | Trench | 15 | 15 | measured (PD50%) | 0.0021 to 0.0097 | 202 |
| SiO2 | 3DMAS/O2* | Trench | 30 | 30 | lower bound | 0.0004 | 198 |
| SiO2 | H2Si[N(C2H5)2]2/O2* | Trench | 15 | 15 | lower bound | 0.0004 | 202 |
| TiO2 | TTIP/O2* | Trench | 13.5 | 13.5 | lower bound | 0.014 | 198 |
| TiO2 | TTIP/O2* | Hole | 8.7 | 8.7 | lower bound | 0.014 | 204 |
| Ni | Ni(Cp)2/H2O/H2* | Hole (TaN) | 3.3 | 3.3 | lower bound | 0.18 to 0.25 | 221 |
| Cu | Cu(acac)2/H2* | Trench (SiO2) | 1.75 | 1.75 | lower bound | 0.14 | 222 |
| Cu | Cu(acac)2/H2* | (trench) | 2.5 | 2.5 | lower bound | 0.14 | 222 |
| Cu | Cu(acac)2/H2* | (trench) | 4.5 | 4.5 | lower bound | 0.14 | 222 |

r of O atoms in the parsed papers, beside Table VII:

| Surface | Table VII | From the parsed papers | Conditions | Paper | Where |
| --- | --- | --- | --- | --- | --- |
| Silica | 0.0004 | 6e-05 | 50 mTorr, 200 °C | 10.1021_acs.jpcc.9b08176 | Fig. 3 |
| Titania | 0.014 ± 0.003 | 7e-05 | 50 mTorr, 200 °C | 10.1021_acs.jpcc.9b08176 | Fig. 3 |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.001 to 0.01 | 50 mTorr, 200 °C; a range | 10.1021_acs.jpcc.9b08176 | text, Table 1 |
| Hafnia | — | 0.001 to 0.1 | 50 mTorr, 200 °C; a range | 10.1021_acs.jpcc.9b08176 | text, Table 1 |
| Silica | 0.0004 | 0.0004 | atmospheric, 100 °C | 10.1063_5.0168768 | Fig. 3, Table I |
| Titania | 0.014 ± 0.003 | 6e-05 | atmospheric, 100 °C | 10.1063_5.0168768 | Fig. 3, Table I |
| Iridium oxide | — | 0.003 | atmospheric | 10.1021_acs.jpcc.5c06502 | body text |
| Silica | 0.0004 | 3e-05 to 0.0001 | 50 mTorr, 100 to 240 °C; falls with temperature | 10.1021_acs.jpcc.1c01505 | Fig. 5A |
| Silica | 0.0004 | 2e-05 to 0.00025 | 180 °C, 12 to 130 mTorr; falls with pressure | 10.1021_acs.jpcc.1c01505 | Fig. 5B |
| Titania | 0.014 ± 0.003 | 1e-05 to 4e-05 | 50 mTorr, 100 to 240 °C; upper limit at 240 °C | 10.1021_acs.jpcc.1c01505 | Fig. 5A |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.0097 to 0.061 | out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Titania | 0.014 ± 0.003 | 0.014 to 0.031 | out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Silica | 0.0004 | 0.004 to 0.0093 | out of scope, cited source: oxidized SiC, 110 Pa air plasma, 300 to 773 K | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Silica | 0.0004 | 0.0002 | literature value, cited | 10.1149_1.3491381 | Table II |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.0021 | literature value, cited (the same as Table VII) | 10.1149_1.3491381 | Table II |
| Silica | 0.0004 | 9e-05 | low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 1e-4) | 10.1063_5.0168768 | Table I |
| Titania | 0.014 ± 0.003 | 4e-05 | low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 4e-5) | 10.1063_5.0168768 | Table I |

What the new sources changed. The Table VII values of ref. 251 (out of scope as not an ALD paper, kept as a cited source) are confirmed, and their conditions are now known: sintered oxide discs at 300 K in an air plasma at 110 Pa, measured by emission actinometry, with r rising with temperature (alumina 0.0097 to 0.061, titania 0.014 to 0.031 between 300 and 773 K). The lateral-channel values of 10.1021_acs.jpcc.1c01505 are for the growing ALD film at 50 mTorr: titania about 4e-5 at 100 to 180 °C and below 1e-5 at 240 °C, falling with temperature. The titania gap is therefore a factor of about 350 at the low end and above 3000 near 500 K, with opposite temperature trends. Ref. 66 is the table that Table VII was updated from; it is a literature table itself. Ref. 228 quotes 0.01 for O on platinum, a surface Table VII lacks. Two of the fifteen matched rows change on the source check: ref. 69 (0.3 instead of 0.75) and ref. 70 (exposure).

### d. Same film, different oxidant

| Film | Structure matched on | Thermal | Ozone | Plasma | Remark |
| --- | --- | --- | --- | --- | --- |
| Al2O3 | macro lateral, EAR 5, 75 °C, one paper (ref. 69) | 2.5 PD50 at 18 | — | 0.75 PD50 at 5 | best match in the tables: same structure, temperature and paper; exposures differ by 3.6 |
| Al2O3 | macro lateral, 200 °C (refs 67, 70) | 50 PD50 at 9 (EAR 100) | — | 10 complete at 27 (EAR 10) | plasma value is a lower bound capped by the structure |
| Al2O3 | maximum per table | 1750 complete | none in the table (text: 20) | 15 PD50; 13.5 complete | the 30 often quoted for plasma is SiO2 and HfO2 |
| TiO2 | hole | — | 20 PD50 (EAR 20) | 8.7 complete (EAR 8.7) | no exposure in either |
| HfO2 | hole | 36 complete at 6 to 9 | 9.6 PD50 (EAR 15.3) | — (trench: 30 complete) | ozone row has no exposure |
| Pt | AAO, EAR 150 | 110 PD50, 250 °C | 35 PD50, 150 °C | — | same structure value; temperatures differ; no exposure |
| Ir / IrO2 | LHAR, one paper (ref. 87) | 15 and 20 PD50, 250 °C | 15 and 45 PD50, 185 °C | — | same structure and paper; no exposure |
| V2O5 | AAO | 7000 complete | 100 complete; 44 of 185 | — | no exposure |
| ZnO | AAO | 700 and 5000 complete at 2000 and 600000 | 250 complete | — | ozone row has no exposure |
| Ru | hole | 4.6 to 32 complete; 20 PD50 | 16 complete | — (trench: 2 complete) | all but one are lower bounds |
| Al2O3 | fibre-filled macro hole, 75 °C, same TMA exposure of 4.8, one paper (10.1016_j.surfcoat.2012.02.038 Fig. 10; from the source, by eye) | about 1.8 PD50 | — | about 0.3 PD50 | the matched pair the review rows miss: its thermal row is the 30 s run (18), its plasma row the 8 s run (5) |
| Al2O3 | empty macro hole, aspect ratio 22, 200 °C, same exposures, one paper (10.1149_1.3301664 Fig. 2; from the source, by eye) | 22 complete | — | about 14 PD50 | stated by the source to differ only in the pump time; the review pairs a ref. 67 row with a ref. 70 row of another structure |

What the new sources changed: the last two rows. They are the only pairs with the same structure, temperature and exposure, and both come from reading the source, not from the review's rows.

### e. Sticking values

| Species | Value | Method or model | data_kind | s or s0 | Source | In Table V |
| --- | --- | --- | --- | --- | --- | --- |
| TMA | 0.001 | Monte Carlo model (value quoted from an earlier paper and used as input) | cited | s (reactive sticking coefficient) | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| TMA | 0.026 | ballistic model with re-emission, adsorption order 1.9; TMA/O2 plasma process | fit | s0 (checked in the source) | review Table V, ref. 200 = 10.1063_1.2714685 | yes |
| TMA | 0.1 | conductance model; value chosen, no fit made | simulation input | s0 (checked in the source) | review Table V, ref. 67 = 10.1149_1.3072694 | yes |
| TMA | 0.1 to 0.9 | DFT | calculated | not checked | review Table V, ref. 176 | yes |
| TMA | 0.00572 | continuum (diffusion-reaction) model | fit | s0 (checked in the source) | review Table V, ref. 77 = 10.1063_1.5028178 | yes |
| TMA | 0.009 to 0.02 | Monte Carlo model of a cavity, best value 0.02 | fit | s0 (checked in the source) | review Table V, ref. 128 = 10.1116_1.4971196 | yes |
| TMA | 0.002 to 0.005 | sum-frequency generation | measured | not checked | review Table V, ref. 237 | yes |
| TMA | 0.01 | Auger electron spectroscopy | measured | not checked | review Table V, ref. 235 | yes |
| TMA | 0.004 | slope at half thickness | calculated | s0 | 10.1039_d0cp03358h Table 2 | no |
| TMA | 0.0005 to 0.002 | slope at half thickness (Arts 2019) | cited | s0 | quoted in 10.1039_d0cp03358h Table 2 and 10.1016_j.sse.2022.108584 Table 2 | no |
| TMA | 0.0075 | diffusion with evaporation flux, fitted by hand | fit | s0 | 10.1016_j.sse.2022.108584 Table 2 | no |
| TMA | 0.012 | diffusion-reaction model | simulation input | s0 | 10.1039_d0cp03358h Fig. 10 | no |
| TMA | 0.01 | diffusion-reaction model, baseline | simulation input | s0 | 10.1039_d1cp04758b Table 1 | no |
| TMA | 0.0008 to 0.002 | literature range | cited | not stated | quoted in 10.1116_6.0001094 | no |
| H2O | 0.0003 | slope at half thickness, one sample | calculated | s0 | 10.1039_d0cp03358h Table 2 | no |
| H2O | 5e-05 to 0.00019 | diffusion with evaporation flux, 150 to 310 °C | fit | s0 | 10.1016_j.sse.2022.108584 Table 1 | no |
| O radical (TMA/O2* process) | 0.172 to 0.316 | Markov chain model, recombination held fixed | fit | s0 | 10.1116_6.0001094 Sec. III D | no |
| TEMAZ | 0.0002 | diffusion model in a porous body | fit | s0 | 10.1116_1.4892385 Fig. 5 | no |
| TMA | 0.01 | one-dimensional Monte Carlo in a fibre plug, 75 °C; picked by comparing simulations | fit | s0 | 10.1016_j.surfcoat.2012.02.038 Sec. 4.2 | no |
| TMA | 0.1 | Monte Carlo of a macro hole | simulation input | s0 | 10.1149_1.3301664 Fig. 6b | no |
| H2O | 0.05 | Monte Carlo of a macro hole | simulation input | s0 | 10.1149_1.3301664 Fig. 9 | no |
| TDMAT (with O3) | 0.015 to 0.025 | Monte Carlo of a hole, four thickness points, 180 °C | fit | s0 | review Table V, ref. 178 = 10.1016_j.apsusc.2009.02.055 | yes |
| TEMAHf (with O3) | 0.031 to 0.56 | Monte Carlo of a hole, 180 to 270 °C; activation energy 0.62 eV | fit | s0 | review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025 | yes |
| Cp*Ti(OMe)3 (with O3) | 0.006 to 0.018 | Monte Carlo of a hole, 270 °C, best value 0.01 | fit | s0 | review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025 | yes |
| TTIP (O2 plasma process) | 0.04 to 0.1 | ballistic model with re-emission, 125 to 225 °C | fit | s0 | review Table V, ref. 204 = 10.1149_1.2789802 | yes |
| BDEAS (with O3) | 3e-05 to 5e-05 | Monte Carlo model of a cavity, 300 °C | fit | s0 | review Table V, ref. 128 = 10.1116_1.4971196 | yes |
| DEZ | 0.007 | Monte Carlo of a pore; origin of the value not found | simulation input | s | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| SiCl4 | 1e-08 | quoted from another paper | cited | s | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| Hf(NMe2)4 | 0.07 to 1 | microbalance, a lower limit of 0.07 | cited | s | 10.1002_cvde.200390005 Sec. 3.1 | no |

What the new sources changed. Seven Table V sources are now read (refs 65, 67, 128, 178, 180, 200, 204; 11 rows). For TMA, the two ends of the non-DFT range are not results: 0.001 (ref. 65) is quoted from an earlier paper and 0.1 (ref. 67) is a chosen input. The fitted TMA values are 0.0005 to 0.0075 from lateral channels (after 2019), 0.009 to 0.02 from a cavity (ref. 128), 0.026 for the plasma process in holes (ref. 200) and 0.01 in a fibre plug at 75 °C. The hole-based fits of refs 178 and 180 rest on four or five thickness points each.

### f. Censoring

| Table | complete (lower bound) | PD50% (measured) | conformal (no number) | blank or other |
| --- | --- | --- | --- | --- |
| II | 40 | 12 | 7 | 12 |
| III | 12 | 5 | 1 | 6 |
| IV | 35 | 3 | 0 | 7 |

In the blank column, 9 rows have a coated value below the structure value without the mark: BN 20 of 10000 (ref. 149); WN 210 of 1000 (ref. 85); Ru 100 of 166 (ref. 159); Pt 94 of 200 (ref. 172); Pt 50 of 200 (ref. 173); Pt 30 of 90 (ref. 173); V2O5 44 of 185 (ref. 159); Pt 50 of 120 (ref. 196); Ag 5 of 30 (ref. 198). 3 rows carry the mark with equal values: Ru 20 (ref. 160); TiO2 20 (ref. 178); Al2O3 15 (ref. 202).

### g. Profiles: the references marked D

| Ref. | DOI | Films (table) | Year | PDF | Open access |
| --- | --- | --- | --- | --- | --- |
| 65 | 10.1021/cm0303080 | ZnO (II) | 2003 | have it | closed |
| 67 | 10.1149/1.3072694 | Al2O3 (II) | 2009 | have it | bronze |
| 69 | 10.1016/j.surfcoat.2012.02.038 | Al2O3 (II); Al2O3 (IV) | 2012 | have it | closed |
| 70 | 10.1149/1.3301664 | Al2O3 (IV); AlN (IV) | 2010 | have it | bronze |
| 77 | 10.1063/1.5028178 | Al2O3 (II); TiO2 (II) | 2018 | have it | green |
| 86 | 10.1116/1.4903941 | Al2O3 (II); TiO2 (II) | 2015 | have it | closed |
| 87 | 10.1021/acs.langmuir.6b03007 | Ir (II); Ir (III); IrO2 (III) | 2016 | to collect | closed |
| 94 | 10.1039/C4TC01961J | Ru (II) | 2015 | to collect | closed |
| 100 | 10.3762/bjnano.5.25 | TiO2 (II) | 2014 | have it | diamond |
| 107 | 10.1149/1.1836500 | SnOx (II) | 1996 | to collect | closed |
| 166 | 10.1063/1.2245216 | W (II) | 2006 | to collect | closed |
| 171 | 10.1116/1.4904398 | Pt (II) | 2015 | to collect | closed |
| 178 | 10.1016/j.apsusc.2009.02.055 | TiO2 (III) | 2009 | have it | closed |
| 180 | 10.1016/j.apsusc.2010.01.025 | HfO2 (III); TiO2 (III) | 2010 | have it | closed |
| 181 | 10.1021/jp110203x | Fe2O3 (III) | 2011 | to collect | closed |
| 184 | 10.1002/cvde.201006891 | Co3O4 (III) | 2011 | to collect | closed |
| 187 | 10.1116/1.4937728 | ZnO (III) | 2016 | to collect | closed |
| 195 | 10.1021/jp403455a | Pt (III) | 2013 | to collect | closed |
| 203 | 10.7567/JJAP.57.06JB03 | SiO2 (IV) | 2018 | to collect | bronze |
| 204 | 10.1149/1.2789802 | TiO2 (IV) | 2007 | have it | bronze |
| 228 | 10.1063/1.4972120 | Pt (IV) | 2017 | have it | green |

## Values read from the papers obtained by hand on 2026-10-13

Every value used above from those papers, with where it was read, whether the ingest checks now cover that unit, and whether it was compared with the page image (`values_hand_obtained.csv`). 19 are covered by the body or table check without a flag, 13 are figure values or values in a flagged table that were compared with the page image, 0 are neither. Two readings changed on that comparison (last column).

| Paper | Value as used | Where read | Check now | Compared with page image | Correction |
| --- | --- | --- | --- | --- | --- |
| 10.1002_cvde.200390005 | holes 0.17 x 0.30 um, 7.3 um deep, aspect ratio 36 (43 after coating) | body | body check: covered, no flag | no |  |
| 10.1002_cvde.200390005 | 150 °C; minimum exposure 9 × 10^3 L; 30 × 10^3 L for full coverage | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | pores 65 nm x 50 um and 19 nm x 92 um; 177 °C | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | TMA at 0.15 Torr; exposure times 1, 3, 10, 30 s | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | DEZ at 0.068 Torr; 5 Torr for 120 s in the quasi-static run | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | both faces directly exposed; pores entered from both ends | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | middle of the membrane uncoated at 1 s, coated at 3 s | figure 3 | not checked (figure) | yes |  |
| 10.1021_cm0303080 | sticking 1e-3 for TMA (quoted) and 7e-3 for DEZ | body | body check: covered, no flag | no |  |
| 10.1149_1.3072694 | TMA about 0.3 Pa, 4 s, 200 °C, 150 cycles; s0 = 0.1 chosen | body | body check: covered, no flag | no |  |
| 10.1149_1.3072694 | half thickness: aspect ratio 50 at about 19 mm, 100 at about 10.7 mm | figure 5 | not checked (figure) | yes | corrected from 49 and 55 to 47 and 53 |
| 10.1016_j.surfcoat.2012.02.038 | TMA 0.08 Pa, 75 °C, 500 cycles; S0 = 0.01 | body | body check: covered, no flag | no |  |
| 10.1016_j.surfcoat.2012.02.038 | Table 2 parameters (0.08 Pa, 8 s, S0 0.01) | table | table check: ok | no |  |
| 10.1016_j.surfcoat.2012.02.038 | half values: thermal 2, 8, 30 s at about 15, 18, 27.5 mm; plasma at about 2.8 mm | figures 5, 10 | not checked (figure) | yes |  |
| 10.1149_1.3301664 | spacers 3.9, 1.3, 0.5 mm; TMA about 0.2 Pa, reactant 0.3 Pa; 9 s; 200 °C | body | body check: covered, no flag | no |  |
| 10.1149_1.3301664 | sticking inputs 0.1 (TMA, at 0.12 Pa) and 5% (water) | body | body check: covered, no flag | no |  |
| 10.1149_1.3301664 | aspect ratio 22: thermal complete, plasma half at about 12.5 mm (about 14) | figure 2 | not checked (figure) | yes |  |
| 10.1116_1.4903941 | gap 500 nm; film to 65 um; aspect ratio 130 at half the entrance value (TiO2) | body | body check: covered, no flag | no |  |
| 10.1116_1.4903941 | Al2O3 half thickness near 70 um | figure 5a | not checked (figure) | yes |  |
| 10.1116_1.4971196 | TMA 0.02 (0.009 to 0.02); BDEAS 3e-5 (3 to 5e-5); 200 and 300 °C | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2009.02.055 | holes 130 nm x 2 um, written as AR = 20; SC 0.02 ± 0.005; 180 °C | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2009.02.055 | profile never below 70% of its top value | figure 3 | not checked (figure) | yes |  |
| 10.1016_j.apsusc.2010.01.025 | SC 0.032, 0.15, 0.56 at 180, 230, 270 °C; Cp*Ti(OMe)3 0.006 to 0.018 | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2010.01.025 | HfO2 half thickness near 1250 nm at 180 °C | figure 1a | not checked (figure) | yes |  |
| 10.1063_1.2714685 | holes 0.3 um, aspect ratio 10; TMA 0.01 Torr; 225 °C; S(0) = 0.026 | body | body check: covered, no flag | no |  |
| 10.1149_1.2789802 | holes 0.15 um, aspect ratio 8.7; step coverage 52% at 500 cycles | body | body check: flagged (not checkable) | yes | none: compared with the page image (p. H1010 and the conclusion on p. H1013); the same values stand in the abstract and conclusion |
| 10.1149_1.2789802 | S(0) 0.1 and 0.052; flux 3.282e20 m-2 s-1 | table | table check: flag | yes |  |
| 10.1063_1.4972120 | trench aspect ratio up to 34; conformality 92 ± 8% | table | table check: ok | no |  |
| 10.1063_1.4972120 | O2 plasma 7.5 mTorr; r of O on Pt 0.01 (quoted) | body | body check: covered, no flag | no |  |
| 10.1149_1.3491381 | r of O on silica 0.0002, alumina 0.0021 (a literature table) | table | table check: flag | yes |  |
| 10.1021_acs.jpcc.1c01505 | r of SiO2 about 1e-4 to 3e-5 (temperature) and 2.5e-4 to 2e-5 (pressure); TiO2 about 4e-5, below 1e-5 at 240 °C | figure 5 | not checked (figure) | yes | corrected: upper pressure value from 2e-4 to 2.5e-4 |
| 10.1021_acs.jpcc.1c01505 | half-thickness depths over cavity height | figures 2-4 | not checked (figure) | yes |  |
| 10.1016_j.cattod.2003.11.022 | out of scope, cited source: γ of O on Al2O3 9.7e-3 (300 K) to 61e-3 (773 K), TiO2 14e-3 to 31e-3, SiC/SiO2 4e-3 to 9.3e-3 | table | table check: flag | yes |  |

## Ideas

### 1. One process across several test structures
- **Verdict: doable partly.**
- Claim: Sec. VII says a benchmark across test structures would be useful. **true** (outlook, p. 021302-30).
- Claim: Sec. IV A: TMA/H2O coated EAR from 5 to 1750. **true** (p. 021302-15).
- Claim: Table II has 12 TMA/H2O rows, 6 with an exposure. **true** (Table II).
- Claim: the record row (AAO, 1750) has no exposure. **true** (Table II, ref. 96).
- Claim: 1 Pa·s is about 7500 L. **true** (but the review prints it the wrong way round, see 3b).
- Claim: Fig. 17 shows Monte Carlo curves for the exposure needed. **true** (caption of Fig. 17; the a² scaling itself was not checked).
- Needs exposure for each row. Have: 6 of 12 in the review; three of those sources are now read (refs 65, 67, 69) and confirm the printed exposures. With them the square law of ref. 62 can be tested for TMA on two sources: it matches ref. 67 and overestimates the need for ref. 65 by about 1.2 to 3.5 times (3a). The ref. 86 source is read too and gives no partial pressure, so its blank cannot be filled; ref. 77 gives a fitted, not measured, pressure. Missing: refs 134, 93, 96, 138 (no PDF). Joins Case 1, Case 8 and candidate A1.

### 2. Automatic EAR conversion
- **Verdict: doable partly.**
- Claim: formulas for hole, trench, elongated hole; pillars from Monte Carlo. **true** (Sec. II G).
- Claim: Werbrouck 2021 states AR 20 and EAR 10. **true** (its Sec. II D).
- Needs L, w and the structure type from each source. Have: 18 checks; 16 agree. Three things a transform would have caught: one membrane listed as 770 and as 700, one hole type listed as 20 and as 15.3, and pores open at both ends counted at full length. Missing: the sources of the other rows. Joins N9 and Case 8.

### 3. Continuing the tables after 2019
- **Verdict: doable now.**
- Claim: Mo trench 100/95/90%. **true** (10.1116_6.0002804 Fig. 9a).
- Claim: WCx step coverage about 80%. **true** (10.1021_acs.chemmater.6c00816 Fig. 4).
- Claim: AlN with Kr, step coverage 1.6. **true** (10.1021_acs.jpclett.4c03545 Fig. 2).
- Claim: PD50% in three plasma LHAR papers. **true** (Fig. 2A; body text; Table 1).
- new_rows.csv holds 21 draft rows from 16 papers, each with its source (two added from 10.1021_acs.jpcc.1c01505). Exposure is blank in all but one. Three things do not fit the review's columns: a step coverage above 1, a profile thicker at the bottom, and atmospheric plasma. Adds a new case (a living table); uses Case 7 for the values written on images.

### 4. Recombination probability against coated EAR
- **Verdict: doable partly.**
- Claim: the review explains the lower EAR of metals only in words; largest 30 for oxides, 17 for metals. **true** (p. 021302-19).
- Claim: O on alumina: 0.0021 and 0.0097. **true** (Table VII, refs 250 and 251).
- Have: 15 Table IV rows with a fair surface match, 13 of them lower bounds. The order of the largest values follows r (silica, then alumina and titania, then copper and nickel), but lower bounds capped by the structure cannot test it. Missing: profiles for these rows. Two matched rows fail the source check (ref. 69: about 0.3, not 0.75; ref. 70: exposure). The Table VII values for alumina and titania are now traced to their source (ref. 251): sintered ceramics at 300 K in a 110 Pa air plasma, where r rises with temperature; on ALD films in lateral channels r is 200 to 1000 times lower for titania and falls with temperature and pressure. So Table VII values cannot stand in for the growth surface. Joins Case 2 and Case 8.

### 5. Same film, different oxidant
- **Verdict: doable partly.**
- Claim: Al2O3 largest coated EAR about 1750, 20, 30 for thermal, ozone, plasma. **wrong in part** (1750 is right; 20 is in the running text only, the table cell says 'Ref. 175'; 30 is SiO2 and HfO2, the largest plasma Al2O3 value is 15 (PD50%) or 13.5).
- Claim: TiO2, HfO2, Ru, Pt, ZnO also have pairs. **true** (plus V2O5, Fe2O3, Ir, SiO2, AlN, TiN, TaN).
- Claim: the review compares maxima without matching. **true** (Sec. IV B).
- Have: 10 pairs from the tables with the same structure type, none matched in exposure, and now two matched pairs taken from the sources (refs 69 and 70): at equal exposure, structure and temperature the plasma process coats about 6 times and about 1.6 times less deep than the thermal one. Missing: exposure in every ozone row but one. Joins Case 8.

### 6. Why sticking probabilities scatter
- **Verdict: doable now.**
- Claim: TMA has 8 values from 0.001 to 0.1, DFT 0.1 to 0.9. **true** (Table V).
- Claim: the review only suggests the methods differ. **true** (p. 021302-16).
- Claim: Ylilammi's 0.00572 is an initial sticking coefficient. **true** (source: c multiplies (1 − θ); the review's Sec. VI B 3 calls it initial, its Table V header says sticking probability).
- Have: the 27 Table V rows and 14 values outside the table, each with model and data kind. Of the 16 Table V rows now checked in a source, 2 are not results of the method named: the TMA value of ref. 65 is quoted from an earlier paper and that of ref. 67 is a chosen input. With those two removed and DFT set aside, the fitted TMA values run from 0.0005 to 0.026. Every checked value is an initial (bare-surface) one. Joins Case 4, Case 8 and N1.

### 7. Many coated EAR values are lower bounds
- **Verdict: doable now.**
- Claim: coated EAR equals the structure EAR when fully coated, PD50% otherwise. **true** (captions of Tables II to IV).
- Claim: '75 (D)' is a measured value. **true** (printed as 75* (D)).
- Counts are in 3f. The rule is not applied evenly: 9 rows have a coated value below the structure value without the PD50% mark, and 3 carry the mark although the two values are equal. One marked row is contradicted by its source (ref. 178: the profile never falls to one half). Supports a basis qualifier on coated_aspect_ratio; joins N3 and Case 8.

### 8. The (D) mark as a collection list
- **Verdict: doable partly.**
- Claim: (D) means a thickness profile was reported. **true** (captions).
- Claim: Sec. VI B 3: dense points in the slope region are needed (Fig. 22). **true** (p. 021302-31).
- Have: 21 references marked D, 11 with a PDF. The point count now covers 43 measured profile groups (21 new, profiles.csv). The rest of the list is in wanted_pdfs.csv.

### 9. Growth type classification
- **Verdict: doable partly.**
- Claim: three growth types told apart by profile shape. **true** (Sec. II F, Fig. 4).
- Shape separates diffusion-limited profiles (plateau and front) well. It cannot separate reaction- from recombination-limited growth, or either from channel closing or reversible adsorption; those need a time or dose series. The new papers add three more cases where shape misleads: a plasma profile with a sharp front (CoOx), plasma profiles shaped by a thermal side reaction (Al2O3), and a precursor-limited plasma profile (TiO2 at the highest temperature). Ref. 66, now read, is where the third type was introduced; its regime diagram needs r and the aspect ratio, not the shape. Joins N7.

### Idea 8, tried: calibration fitness of the measured profiles

Threshold used: at least 5 points between 80% and 20% of the reference level, a plateau or a stated reference to normalize by, and a probe smaller than the front. Reason: a front is described by two numbers, its position and its slope; with fewer than five points there are fewer than three left to judge the fit, and the review's Fig. 22 shows that sparse points in the slope region cannot tell sticking values apart. Counts are by eye.

Of 43 series groups: 11 fit, 10 marginal, 22 not fit.

| Paper | Fig. | Series | Points | Points 80 to 20% | Plateau | Fit for a sticking value | Remark |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 6 | Al2O3, 500 cycles | about 85 | about 8 | yes | yes |  |
| 10.1063_1.5028178 | 7 | TiO2, 1000 cycles | about 70 | about 35 | no | no: no plateau | looks reaction-limited, but the authors' fit gives a high sticking coefficient (0.1) with weak reversible adsorption |
| 10.1039_d0cp03358h | 7 | spot 5 µm | about 90 | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 7 | spot 25 and 50 µm | about 90 each | 15 to 25 | yes | no: spot wider than the front | more points, but the slope is the instrument's |
| 10.1039_d0cp03358h | 8a, 8b | repeats and four runs | about 90 each | 10 to 15 | yes | yes | fronts of nominally equal runs differ by tens of µm |
| 10.1039_d0cp03358h | 9a-c | H 500 nm | about 90 | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 9a-c | H 100 nm | about 30 in the channel | about 8 | no | no: no plateau, channel closing | the shape of a reaction-limited profile, caused here by film growth narrowing a 100 nm channel |
| 10.1039_d0cp03358h | 9a-c | H 2000 nm | about 90 | about 10, curve cut at one third | yes | marginal | gas-phase collisions matter at this height |
| 10.1039_d0cp03358h | 9d-f | 250, 500, 1000 cycles | about 90 each | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 11a-b | pulse and purge series | about 90 each | 10 to 25 | yes | yes |  |
| 10.1116_6.0001094 | 11 | six power and pulse pairs | 10 each | 3 to 6; most never reach 20% | partly | no | the authors state diffusion-limited conditions; in a structure of aspect ratio 20 the three types look alike |
| 10.1116_6.0001094 | 12 | five pressures | 10 each | 2 to 5; none reaches 20% | partly | no | same |
| 10.1021_acs.jpcc.9b08176 | 2B | SiO2, four plasma times | 40 to 90 each | about 10 | yes | yes, for a recombination probability | the time series, not one profile, is what identifies the type |
| 10.1021_acs.jpcc.9b08176 | 2B | TiO2, Al2O3, HfO2 | 10 to 80 each | 5 to 8 | no | marginal | from one profile alone this cannot be told from reaction-limited growth |
| 10.1063_5.0168768 | 2a | SiO2, three plasma times | about 35 each | 3 to 4 | yes, short | no | type stated by the authors |
| 10.1063_5.0168768 | 2b | TiO2, three plasma times | about 35 each | 6 to 8 | no | marginal |  |
| 10.1021_acs.jpcc.5c06502 | 10b | samples A to D | continuous traces | many, from image grey levels | no | no: thickness scale is indirect | type stated by the authors from the comparison of four samples |
| 10.1038_s41467-022-35428-6 | 4b | four inhibitor treatments | about 12 each | 0: no front | not applicable | no | inhibitor-controlled growth is outside the scheme |
| 10.1116_1.4892385 | 5 | ZrO2, 1135 cycles | 17 | about 9, scattered | no | marginal |  |
| 10.3762_bjnano.5.25 | 6b | 400 cycles | 13 | about 6 | yes | marginal | the slope reflects exposure not scaled as tubes thicken |
| 10.3762_bjnano.5.25 | 6b | 200 cycles | 12 | 2 to 3 | yes | no |  |
| 10.3762_bjnano.5.25 | 6c | three series | 8 to 10 each | 3 to 5 | yes | no |  |
| 10.1149_1.3072694 | 5 | aspect ratio 100 | about 20 | 3 to 4 | yes | marginal | the authors decline to fit: the result depends on the pressure to 0.01 Pa |
| 10.1149_1.3072694 | 5 | aspect ratio 33 and 50 | about 20 each | 0 to 2 | yes | no: coated to the end |  |
| 10.1149_1.3301664 | 2a, 6a | thermal, aspect ratio 50 | about 30 | about 8 | yes, with a slow early decline | marginal | the authors suspect a CVD-like part in the early decline |
| 10.1149_1.3301664 | 2b, 3, 4b, 5a, 9a | plasma Al2O3, about 20 profiles | about 30 each | 5 to 15 | partly | no: two reactions overlap | the authors attribute the tail to water formed in the plasma step: recombination-limited growth with a thermal side reaction |
| 10.1149_1.3301664 | 5b | plasma AlN, three plasma times | about 30 each | 5 to 8 | no | no | the film composition changes with depth |
| 10.1149_1.3301664 | 10 | plasma CoOx | about 30 | about 4 | yes, short | marginal | a plasma process with the shape of a diffusion-limited profile |
| 10.1016_j.surfcoat.2012.02.038 | 5, 7 | thermal, three pulse times, two densities | 5 to 8 each | 2 to 4 | partly | no | an X-ray signal with wide error bars; type stated by the authors |
| 10.1016_j.surfcoat.2012.02.038 | 10 | plasma | 9 | 3 | no | no | type from the comparison with the thermal run, not from the shape |
| 10.1116_1.4903941 | 5a | Al2O3, 300 °C | about 50 | about 10 | yes | yes | the tail below 30 nm is not reliable (stated) |
| 10.1116_1.4903941 | 5b | TiO2, 110 °C, three gaps | 30 to 45 each | 10 to 20 | no | no: no plateau | same behaviour as the TiO2 profile of 10.1063_1.5028178 |
| 10.1116_1.4971196 | 8, 9 | Al2O3, four access holes | about 100 each | 8 to 10 per edge | yes, with growth above the planar level near the hole | yes | the authors fit 0.02 (0.009 to 0.02); the reference level is chosen |
| 10.1116_1.4971196 | 11, 12 | SiO2, four access holes | about 100 each | the whole scan | no | yes, for a low value | the authors fit 3e-5; a low value is fixed by the overall shape |
| 10.1016_j.apsusc.2009.02.055 | 3 | TiO2, one sample | 4 | 0: never below 70% | one point | no: four points | the authors fit 0.02 ± 0.005 from these four points |
| 10.1016_j.apsusc.2010.01.025 | 1 | HfO2 at 180, 230, 270 °C | 4 to 5 each | 2 to 3 | one point | no: too few points | the authors fit 0.031, 0.15, 0.56; shape goes from reaction- to diffusion-limited |
| 10.1016_j.apsusc.2010.01.025 | 3 | TiO2, 270 °C | 5 | 0 | no | no | only a range, 0.006 to 0.018 |
| 10.1149_1.2789802 | 4 | TiO2, one hole | 7 values at three heights | about 3 | no | no | the model is fitted to top and bottom values against pulse time, not to this profile |
| 10.1063_1.4972120 | 5, 7 | Pt, four trenches; one trench by TEM | 6 each; 160 | 0: no front | yes, all of it | no: saturated | a fully coated structure carries no kinetic information |
| 10.1021_cm0303080 | 5a, 6a | ZnO, four exposure times, three pore sizes | about 25 each | 5 to 10 | yes, short | marginal | probe of 3 to 5 um against fronts of 5 to 10 um; type stated by the authors |
| 10.1021_cm0303080 | 7b | ZnO, aspect ratio 5000 | about 100 | 0: no front | yes | no: saturated |  |
| 10.1021_acs.jpcc.1c01505 | 2A, 4A | SiO2, four temperatures, five pressures | 50 to 100 each | about 10 | a slow decline, then a front | yes, for a recombination probability | type from the time series |
| 10.1021_acs.jpcc.1c01505 | 3A | TiO2, three temperatures | 50 to 100 each | 10 to 20 | no | marginal | at the highest temperature the precursor step limits the depth (stated), which the shape does not show |

### Idea 9, tried: growth type by shape

Counts: diffusion-limited 18, cannot decide 10, recombination-limited 9, none of the three 3, reaction-limited 3.

| Paper | Fig. | Series | Type by shape | Feature used | Where shape alone cannot decide |
| --- | --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 6 | Al2O3, 500 cycles | diffusion-limited | flat, then a front of about 20 µm |  |
| 10.1063_1.5028178 | 7 | TiO2, 1000 cycles | cannot decide | falls from the entrance on | looks reaction-limited, but the authors' fit gives a high sticking coefficient (0.1) with weak reversible adsorption |
| 10.1039_d0cp03358h | 7 | spot 5 µm | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 7 | spot 25 and 50 µm | diffusion-limited | front smeared by the instrument | more points, but the slope is the instrument's |
| 10.1039_d0cp03358h | 8a, 8b | repeats and four runs | diffusion-limited | flat, then a sharp front | fronts of nominally equal runs differ by tens of µm |
| 10.1039_d0cp03358h | 9a-c | H 500 nm | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 9a-c | H 100 nm | cannot decide | falls from the entrance on | the shape of a reaction-limited profile, caused here by film growth narrowing a 100 nm channel |
| 10.1039_d0cp03358h | 9a-c | H 2000 nm | diffusion-limited | flat, then a front | gas-phase collisions matter at this height |
| 10.1039_d0cp03358h | 9d-f | 250, 500, 1000 cycles | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 11a-b | pulse and purge series | diffusion-limited | flat, then a front; broader at 0.4 s |  |
| 10.1116_6.0001094 | 11 | six power and pulse pairs | cannot decide | gradual decline over the whole 20 mm | the authors state diffusion-limited conditions; in a structure of aspect ratio 20 the three types look alike |
| 10.1116_6.0001094 | 12 | five pressures | cannot decide | gradual decline | same |
| 10.1021_acs.jpcc.9b08176 | 2B | SiO2, four plasma times | recombination-limited | long shallow decline, then a front; depth grows with the logarithm of time | the time series, not one profile, is what identifies the type |
| 10.1021_acs.jpcc.9b08176 | 2B | TiO2, Al2O3, HfO2 | recombination-limited | decline from the entrance on | from one profile alone this cannot be told from reaction-limited growth |
| 10.1063_5.0168768 | 2a | SiO2, three plasma times | recombination-limited | front moves with the logarithm of time | type stated by the authors |
| 10.1063_5.0168768 | 2b | TiO2, three plasma times | recombination-limited | decline from the entrance, then a front |  |
| 10.1021_acs.jpcc.5c06502 | 10b | samples A to D | recombination-limited | depth set by plasma time, not precursor dose | type stated by the authors from the comparison of four samples |
| 10.1038_s41467-022-35428-6 | 4b | four inhibitor treatments | none of the three | thinner at the top than at the bottom | inhibitor-controlled growth is outside the scheme |
| 10.1116_1.4892385 | 5 | ZrO2, 1135 cycles | reaction-limited | decline from the surface on; fitted probability 2e-4 |  |
| 10.3762_bjnano.5.25 | 6b | 400 cycles | diffusion-limited | flat to 12 µm, then a slope | the slope reflects exposure not scaled as tubes thicken |
| 10.3762_bjnano.5.25 | 6b | 200 cycles | diffusion-limited | flat to 30 µm, then a drop |  |
| 10.3762_bjnano.5.25 | 6c | three series | diffusion-limited | flat, then a slope |  |
| 10.1149_1.3072694 | 5 | aspect ratio 100 | diffusion-limited | flat, then a front 2 mm wide | the authors decline to fit: the result depends on the pressure to 0.01 Pa |
| 10.1149_1.3072694 | 5 | aspect ratio 33 and 50 | diffusion-limited | no front inside the structure |  |
| 10.1149_1.3301664 | 2a, 6a | thermal, aspect ratio 50 | diffusion-limited | decline, then a front | the authors suspect a CVD-like part in the early decline |
| 10.1149_1.3301664 | 2b, 3, 4b, 5a, 9a | plasma Al2O3, about 20 profiles | cannot decide | gradual decline with a kink and a tail | the authors attribute the tail to water formed in the plasma step: recombination-limited growth with a thermal side reaction |
| 10.1149_1.3301664 | 5b | plasma AlN, three plasma times | recombination-limited | falls from the entrance on within 5 mm | the film composition changes with depth |
| 10.1149_1.3301664 | 10 | plasma CoOx | cannot decide | flat to 3 mm, then a sharp front | a plasma process with the shape of a diffusion-limited profile |
| 10.1016_j.surfcoat.2012.02.038 | 5, 7 | thermal, three pulse times, two densities | diffusion-limited | front moves in with pulse time | an X-ray signal with wide error bars; type stated by the authors |
| 10.1016_j.surfcoat.2012.02.038 | 10 | plasma | recombination-limited | falls from the entrance on, depth six times less than thermal | type from the comparison with the thermal run, not from the shape |
| 10.1116_1.4903941 | 5a | Al2O3, 300 °C | diffusion-limited | flat to 52 um, then a front | the tail below 30 nm is not reliable (stated) |
| 10.1116_1.4903941 | 5b | TiO2, 110 °C, three gaps | cannot decide | falls from the entrance on, in two slopes | same behaviour as the TiO2 profile of 10.1063_1.5028178 |
| 10.1116_1.4971196 | 8, 9 | Al2O3, four access holes | diffusion-limited | flat, then an edge about 100 um wide | the authors fit 0.02 (0.009 to 0.02); the reference level is chosen |
| 10.1116_1.4971196 | 11, 12 | SiO2, four access holes | reaction-limited | smooth decline over the whole cavity | the authors fit 3e-5; a low value is fixed by the overall shape |
| 10.1016_j.apsusc.2009.02.055 | 3 | TiO2, one sample | cannot decide | gentle decline | the authors fit 0.02 ± 0.005 from these four points |
| 10.1016_j.apsusc.2010.01.025 | 1 | HfO2 at 180, 230, 270 °C | cannot decide | front steepens with temperature | the authors fit 0.031, 0.15, 0.56; shape goes from reaction- to diffusion-limited |
| 10.1016_j.apsusc.2010.01.025 | 3 | TiO2, 270 °C | reaction-limited | nearly flat decline | only a range, 0.006 to 0.018 |
| 10.1149_1.2789802 | 4 | TiO2, one hole | cannot decide | thinner toward the bottom | the model is fitted to top and bottom values against pulse time, not to this profile |
| 10.1063_1.4972120 | 5, 7 | Pt, four trenches; one trench by TEM | none of the three | flat to the bottom | a fully coated structure carries no kinetic information |
| 10.1021_cm0303080 | 5a, 6a | ZnO, four exposure times, three pore sizes | diffusion-limited | front moves in with the square root of time | probe of 3 to 5 um against fronts of 5 to 10 um; type stated by the authors |
| 10.1021_cm0303080 | 7b | ZnO, aspect ratio 5000 | none of the three | coated through, with a slope across the membrane |  |
| 10.1021_acs.jpcc.1c01505 | 2A, 4A | SiO2, four temperatures, five pressures | recombination-limited | depth grows with the logarithm of plasma time | type from the time series |
| 10.1021_acs.jpcc.1c01505 | 3A | TiO2, three temperatures | recombination-limited | declines from the entrance on | at the highest temperature the precursor step limits the depth (stated), which the shape does not show |

