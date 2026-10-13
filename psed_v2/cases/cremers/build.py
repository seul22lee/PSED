#!/usr/bin/env python3
"""Exploration: Cremers 2019 read as data. Reads conformality.csv / parameters.csv (transcribe.py) and the hand-checked
lists below; writes source_checks.csv, new_rows.csv, profiles.csv, wanted_pdfs.csv and CREMERS.md. The plots (SVG strings pa, pc, pr, ps)
are used by ../make_cases.py for Case 8 of cases.html; this script writes no HTML.

    python3 psed_v2/cases/cremers/transcribe.py && python3 psed_v2/cases/cremers/build.py
"""
import csv, html, math, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent.parent
E = html.escape
rd = lambda p: list(csv.DictReader(open(p, newline="", encoding="utf-8")))
CONF, PAR = rd(HERE / "conformality.csv"), rd(HERE / "parameters.csv")
MAN = {r["doi"]: r for r in rd(V2 / "corpus/manifest.csv")}


def wr(name, rows):
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def md(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"

# ----------------------------------------------------------------------------- step 2: source checks (by hand)
SC = [  # table, row as in the review, ref, paper_id, verdict, where in the source, remark
 ("II", "Al2O3 TMA/H2O, LHAR, 300 °C, coated 130* (D)", "77", "10.1063_1.5028178", "agree", "Fig. 6, Table I", "half thickness at about 133 µm (by eye) in a 0.5 µm gap gives 133 with the trench formula; the 300 °C is not in the parsed text; the printed EAR 10-12500 is the chip family, the sample has L 1 mm (AR 2000)"),
 ("II", "TiO2 TiCl4/H2O, LHAR, 110 °C, coated 90* (D)", "77", "10.1063_1.5028178", "agree", "Fig. 7", "half of the entrance thickness at about 90 µm (by eye); the profile has no plateau; the 110 °C is not in the parsed text"),
 ("III", "TiO2 TDMAT/O3, CNT, 100 °C, exposure 4500", "98", "10.1039_c3ra42928h", "agree", "experimental section", "0.3 mbar for 20 s is 4.5 Torr s, i.e. 4500 × 10^3 L; the review computed the exposure, the source does not print it"),
 ("II", "TiO2 TTIP/H2O, VACNT, 225 °C, (D)", "100", "10.3762_bjnano.5.25", "agree", "methods, Fig. 6b", "225 °C, TTIP and water, thickness against depth; no aspect ratio in the source either"),
 ("II", "TiO2 TiCl4/H2O, AAO, EAR 7.5, 200 °C, coated 7.5", "140", "10.1186_s11671-015-0872-9", "agree", "abstract, methods", "500 nm deep, 67 nm pores, 7.5:1, filled"),
 ("II", "Fe3O4 Fe(Cp)2/O2, AAO, 400 °C", "144", "10.1038_srep18401", "agree", "methods", "ferrocene and oxygen at 400 °C; no pore dimensions found, as in the review"),
 ("II", "Ir Ir(acac)3/O2, trench, 370 °C (thermal table)", "169", "10.1016_j.mee.2018.01.027", "not found", "process section", "precursors agree; 370 °C is not in the parsed text; the source says oxygen can be supplied thermally or through the plasma and does not say which was used, and gives a 30 µm depth the review leaves out"),
 ("IV", "Ir Ir(acac)3/O2*, trench, 370 °C (plasma table)", "169", "10.1016_j.mee.2018.01.027", "not found", "process section", "same paper listed in both tables; mode not stated in the source"),
 ("II", "Pt MeCpPtMe3/O2, AAO, EAR 200, coated 50", "173", "10.1007_s12274-010-0066-9", "differ", "text on AAO templates, Fig. 2", "60 µm thick with 250 to 300 nm pores gives 200 to 240; the source gives a penetration that saturates near 20 µm (about 70 to 80) and tubes 15 µm long (about 50 to 60): the review took the tube length"),
 ("II", "Pt MeCpPtMe3/O2, hole, EAR 90, coated 30", "173", "10.1007_s12274-010-0066-9", "agree", "Fig. 3e-f", "30 µm of a 90 µm pore of 1 µm; the same figure shows 90 µm reached with added exposure time, which the review does not list"),
 ("III", "Pt Pt(acac)2/O3, AAO, EAR 120, 150 °C, coated 50", "196", "10.1039_c5ta00205b", "differ", "abstract, text at Fig. 6", "coated 50 agrees; the structure value 120 was not found (the abstract says 70); both 130 and 150 °C were used"),
 ("IV", "Al2O3 TMA/O2*, trench, EAR 15, coated 15*", "202", "10.1149_2.067203jes", "differ", "conformality paragraph, Fig. 8", "the source tests SiO2 only; the alumina in that trench is an underlayer for contrast, and no half-thickness depth is given"),
 ("IV", "SiO2 H2Si[N(C2H5)2]2/O2*, trench, EAR 15, coated 15", "202", "10.1149_2.067203jes", "agree", "conformality paragraph, Fig. 8", "aspect ratio about 30 for a trench is 15; 95 to 100% bottom to top"),
 ("IV", "Ir Ir(acac)3/O2*, hole (elongated), 370 °C, I", "226", "10.1016_j.mee.2018.01.033", "agree", "methods", "370 °C, oxygen plasma, inductively coupled"),
 ("V", "Al(CH3)3 on Al2O3, continuum model, 300 °C, 0.00572", "77", "10.1063_1.5028178", "agree", "Table I, Eq. for the adsorption rate", "c = 0.00572; c multiplies (1 − θ), so it is an initial (bare-surface) value, called a lumped sticking coefficient"),
 ("V", "TiCl4 on TiN, continuum model, 110 °C, 0.1", "77", "10.1063_1.5028178", "differ", "Table I", "value agrees (0.10) but the source deposits TiO2; TiN is carried over from the line above in the table"),
]
SC2 = [  # added 2026-10-13 with the 15 PDFs obtained by hand
 ("II", "Al2O3 TMA/H2O, macro lateral, EAR 100, 200 °C, exposure 9, coated 50* (D)", "67", "10.1149_1.3072694", "agree", "experimental section, Fig. 5", "0.3 Pa for 4 s is 1.2 Pa s, i.e. 9.0 × 10^3 L; aspect ratio 100 by the source's perimeter definition; half thickness near 11 of 20 mm (by eye) gives 55"),
 ("II", "Al2O3 TMA/H2O, AAO, EAR 770, 177 °C, exposure 4500, coated 770", "65", "10.1021_cm0303080", "agree", "Sec. III A, Fig. 3", "65 nm x 50 um gives 769; 0.15 Torr for 30 s is 4500 × 10^3 L. The source coats the membrane already at 3 s (450) and the pores are open at both ends: the review lists the largest exposure used and the full length"),
 ("II", "ZnO DEZ/H2O, AAO, EAR 700, 177 °C, exposure 2000, coated 700 (D)", "65", "10.1021_cm0303080", "differ", "Sec. III B, Fig. 5", "exposure agrees (0.068 Torr for 30 s); the membrane is the same 65 nm x 50 um one that the Al2O3 row lists as 770"),
 ("II", "ZnO DEZ/H2O, AAO, EAR 5000, 177 °C, exposure 600000, coated 5000 (D)", "65", "10.1021_cm0303080", "agree", "Sec. III B, Fig. 7", "19 nm x 92 um; 5 Torr for 120 s"),
 ("II", "Al2O3 TMA/H2O, LHAR, 300 °C, coated 75* (D)", "86", "10.1116_1.4903941", "agree", "Fig. 4, Fig. 5a", "film to 65 um in a 500 nm gap (AR 130, stated), half thickness near 70 um by eye: 65 to 70 with the trench formula; EAR range 10 to 12500 matches half of the Fig. 1 table"),
 ("II", "TiO2 TiCl4/H2O, LHAR, 110 °C, coated 65* (D)", "86", "10.1116_1.4903941", "agree", "text to Fig. 5b", "50% of the entrance value at AR 130, stated; the profile has no plateau"),
 ("II", "Al2O3 TMA/H2O, macro lateral, EAR 5, 75 °C, exposure 18, coated 2.5* (D)", "69", "10.1016_j.surfcoat.2012.02.038", "agree", "Sec. 2, Fig. 5", "0.08 Pa for 30 s is 18 × 10^3 L; half value at 27 mm of a 1 cm wide hole. The hole is filled with a fibre non-woven, which the row does not say: its EAR is not that of an empty hole"),
 ("II", "HfO2 Hf(NMe2)4/H2O, holes, EAR 36, 150 °C, exposure 9, coated 36", "62", "10.1002_cvde.200390005", "agree", "Sec. 4, Sec. 6", "elliptical holes 0.17 x 0.30 x 7.3 um, aspect ratio 36 by the source; 9 × 10^3 L is the calculated minimum, the fully coated sample had 30"),
 ("III", "TiO2 TDMAT/O3, hole, EAR 20, 180 °C, coated 20* (D)", "178", "10.1016_j.apsusc.2009.02.055", "differ", "Sec. 2, Fig. 3", "the source writes AR = 20 for holes of 130 nm x 2 um, which is 15.4 (the review uses 15.3 for the same holes in the ref. 180 rows); the profile falls only to 70% of its top value, so no half-thickness depth exists"),
 ("III", "TiO2 Cp*Ti(OMe)3/O3, hole, EAR 15.3, 270 °C, (D)", "180", "10.1016_j.apsusc.2010.01.025", "agree", "Sec. 3, Fig. 3", ""),
 ("III", "HfO2 TEMAHf/O3, hole, EAR 15.3, 180 °C, coated 9.6* (D)", "180", "10.1016_j.apsusc.2010.01.025", "agree", "Fig. 1a", "half of 18.8 nm near 1250 nm, over 130 nm; the 230 and 270 °C profiles of the same figure are not listed"),
 ("IV", "Al2O3 TMA/O2*, macro lateral, EAR 10, 200 °C, RI, exposure 27, coated 10 (D)", "70", "10.1149_1.3301664", "differ", "experimental section, Fig. 2b", "structure, temperature and coating agree (thickness falls to about 75% at the end, above one half); the exposure does not reproduce: 0.3 Pa for 9 s is 20, for 18 s it is 40"),
 ("IV", "Al2O3 TMA/O2*, macro lateral, EAR 5, 75 °C, RI, exposure 5, coated 0.75* (D)", "69", "10.1016_j.surfcoat.2012.02.038", "differ", "Fig. 10", "exposure agrees as the TMA exposure (0.08 Pa for 8 s); the plasma profile is at half its entrance value near 3 mm, i.e. about 0.3, not 0.75"),
 ("IV", "Al2O3 TMA/O2*, hole, EAR 10, 225 °C, exposure 30, coated 10", "200", "10.1063_1.2714685", "agree", "Sec. IV, Fig. 7", "0.3 um holes of aspect ratio 10; 0.01 Torr for 3 s is 30 × 10^3 L, a TMA exposure"),
 ("IV", "TiO2 TTIP/O2*, hole, EAR 8.7, 225 °C, coated 8.7 (D)", "204", "10.1149_1.2789802", "agree", "experimental conditions, Fig. 2b, Fig. 4", "full coverage needs a long TTIP pulse; at 5 s the bottom has 52% (Fig. 4, 5)"),
 ("IV", "AlN TMA/NH3*, macro lateral, EAR 10, 200 °C, RI, exposure 40, coated 2.5* (D)", "70", "10.1149_1.3301664", "agree", "Fig. 5b", "0.3 Pa for 18 s is 40 × 10^3 L; half thickness at 4 to 5 of 20 mm"),
 ("IV", "Pt MeCpPtMe3/O2*, trench, EAR 17, 300 °C, I, coated 17 (D)", "228", "10.1063_1.4972120", "agree", "Table II, Fig. 5", "trench aspect ratio 34, conformality 92 ± 8%"),
 ("V", "Al(CH3)3, Monte Carlo model, 177 °C, 0.001", "65", "10.1021_cm0303080", "differ", "Sec. IV D", "the value is quoted there from an earlier paper and used as an input; it is not derived with the Monte Carlo model"),
 ("V", "Al(CH3)3, ballistic model, 225 °C, 0.026", "200", "10.1063_1.2714685", "agree", "Sec. IV, Fig. 8", "an initial sticking probability, fitted, for TMA in the TMA/O2 plasma process"),
 ("V", "Al(CH3)3, semi-analytical model, 200 °C, 0.1", "67", "10.1149_1.3072694", "differ", "text to Fig. 6", "0.1 is a value chosen for the simulation; the source says a fit would need the pressure to 0.01 Pa and does not make one"),
 ("V", "Al(CH3)3, Monte Carlo model, 200 °C, 0.02", "128", "10.1116_1.4971196", "agree", "Sec. IV A 3", "fitted; range 0.009 to 0.02"),
 ("V", "Hf(NEtMe)4, Monte Carlo model, 180-270 °C, 0.03-0.6", "180", "10.1016_j.apsusc.2010.01.025", "agree", "Fig. 1", "0.031, 0.15, 0.56 at 180, 230, 270 °C"),
 ("V", "Ti(NMe2)4, Monte Carlo model, 180 °C, 0.02 ± 0.005", "178", "10.1016_j.apsusc.2009.02.055", "agree", "Fig. 4", "from four thickness points"),
 ("V", "Ti(OiPr)4, ballistic model, 125-225 °C, 0.04-0.1", "204", "10.1149_1.2789802", "agree", "Fig. 7b, Table II", "initial sticking probability with an adsorption order"),
 ("V", "Cp*Ti(OMe)3, Monte Carlo model, 270 °C, 0.01", "180", "10.1016_j.apsusc.2010.01.025", "agree", "Fig. 3", "range 0.006 to 0.018"),
 ("V", "ZnEt2, Monte Carlo model, 177 °C, 0.007", "65", "10.1021_cm0303080", "not found", "Sec. IV C", "0.007 is the value used in the simulations; how it was obtained was not found"),
 ("V", "SiCl4, Monte Carlo model, 10^-8", "65 and 239", "10.1021_cm0303080", "agree", "Sec. III C, IV D", "quoted there from the second reference"),
 ("V", "H2Si[N(C2H5)2]2, Monte Carlo model, 300 °C, 3 × 10^-5", "128", "10.1116_1.4971196", "agree", "Sec. IV B 3", "fitted; range 3 to 5 × 10^-5"),
 ("VII", "O on alumina, 0.0097 ± 0.0019", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K, ± 20%, on a sintered ceramic in an air plasma at 110 Pa; 0.061 at 773 K"),
 ("VII", "O on titania, 0.014 ± 0.003", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K; 0.031 at 773 K"),
 ("VII", "O on iron(II, III) oxide, 0.015 ± 0.003", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K"),
 ("VII", "O on cobalt oxide, 0.029 ± 0.006", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "CoO at 300 K"),
]
SC1, SC = SC, SC + SC2
wr("source_checks.csv", [dict(table=a, row=b, ref=c, paper_id=d, verdict=e, where=f, remark=g) for a, b, c, d, e, f, g in SC])

# ----------------------------------------------------------------------------- idea 3: draft rows from the post-2019 papers
NR = [  # same columns as conformality.csv, plus paper_id and source
 ("II", "Al2O3", "TMA", "H2O", "", "LHAR", "2000", "300", "", "Reflectometry", "107 (S8, 500 cycles) to 193 (S14, 0.4 s pulse)", "", "PD50", "D", "10.1039_d0cp03358h", "Table 1 (x50% in µm over 2H); Fig. 9, 11", "16 samples; values computed here from the table's depths with the trench formula"),
 ("II", "AlN", "TMA", "NH3", "", "Trench", "9", "", "", "SEM", "9", "9", "complete", "", "10.1021_acs.jpclett.4c03545", "Fig. 1", "18:1 trench; step coverage 1"),
 ("II", "AlN", "TMA", "NH3 with Kr", "", "Trench", "9", "", "", "SEM", "9", "9", "complete", "", "10.1021_acs.jpclett.4c03545", "Fig. 2", "step coverage 1.6: thicker at the bottom, which the table format cannot say"),
 ("II", "AlN", "TMA", "NH3", "", "LHAR", "75-150", "", "", "SEM", "42", "42", "", "", "10.1021_acs.jpclett.4c03545", "body text, Fig. 3", "deposition depth 42 µm in a 0.5 µm gap; not a half-thickness depth"),
 ("II", "TiO2", "TDMAT", "", "", "Hole (tapered)", "16", "", "", "TEM", "16 (D)", "16", "complete", "D", "10.1038_s41467-022-35428-6", "Fig. 4a-b", "1600 nm deep, 100 nm opening; co-reactant not on the figures read"),
 ("II", "ZnO", "DEZ", "H2O", "", "Nanoparticle compact", ">1000", "120", "", "SEM/EDX", "(D)", "", "", "D", "10.1116_6.0003182", "abstract, Fig. 6d", "aspect ratio given only as greater than 10^3; uniform through the thickness"),
 ("II", "Al2O3", "TMA", "H2O", "", "VACNT", "", "", "", "SEM", "(D)", "", "", "D", "10.1021_acs.chemmater.1c03164", "Fig. 9", "diameter against depth"),
 ("II", "ZrO2", "TEMAZ", "", "", "Porous ceramic", "", "", "", "SEM", "(D)", "", "", "D", "10.1116_1.4892385", "Fig. 5", "published 2015, not in the review's tables"),
 ("II", "Mo", "MoCl2O2", "atomic H (hot wire)", "", "Trench", "1.5", "", "", "STEM", "1.5", "1.5", "complete", "", "10.1116_6.0002804", "Fig. 9a, body text", "3:1 trench; 95% sidewall, 90% bottom; whether this belongs in the thermal or the plasma table is open"),
 ("IV", "WCx", "(N-methylpyrrolidine)W(CO)5", "H2*", "", "Trench", "0.75", "250", "", "TEM", "0.75", "0.75", "complete", "", "10.1021_acs.chemmater.6c00816", "Fig. 4a", "aspect ratio about 1.5; 20 nm top, 16 nm bottom"),
 ("IV", "Al2O3", "TMA", "O2*", "I", "Macro lateral", "10", "100; 120", "", "SE", "(D)", "", "", "D", "10.1116_6.0001094", "Fig. 11, 12; body text", "eleven profiles; no half-thickness depth stated"),
 ("IV", "SiO2", "", "O2*", "I", "LHAR", "", "200", "", "Reflectometry", "165* to 435* (D)", "", "PD50", "D", "10.1021_acs.jpcc.9b08176", "Fig. 2A", "half-thickness aspect ratios 330, 570, 730, 870 for 3.8 to 120 s, halved here"),
 ("IV", "TiO2", "", "O2*", "I", "LHAR", "", "200", "", "Reflectometry", "225*; 390* (D)", "", "PD50", "D", "10.1021_acs.jpcc.9b08176", "Fig. 2A", "450 and 780 for 12 and 120 s, halved"),
 ("IV", "Al2O3", "", "O2*", "I", "LHAR", "", "200", "", "Reflectometry", "40* (D)", "40", "PD50", "D", "10.1021_acs.jpcc.9b08176", "Fig. 2A", "80 at 120 s, halved"),
 ("IV", "HfO2", "", "O2*", "I", "LHAR", "", "200", "", "Reflectometry", "20* (D)", "20", "PD50", "D", "10.1021_acs.jpcc.9b08176", "Fig. 2A", "40 at 120 s, halved"),
 ("IV", "SiO2", "", "O2/N2* (atmospheric)", "", "LHAR", "", "100", "", "SE", "37* (D)", "37", "PD50", "D", "10.1063_5.0168768", "body text, Fig. 2a", "73.5 at 0.73 s, halved; the source itself converts to an equivalent aspect ratio"),
 ("IV", "TiO2", "", "O2/N2* (atmospheric)", "", "LHAR", "", "100", "", "SE", "109* (D)", "109", "PD50", "D", "10.1063_5.0168768", "body text, Fig. 2b", "218.5 at 0.73 s, halved"),
 ("IV", "IrOx", "(EtCp)Ir(CHD)", "O2/N2* (atmospheric)", "", "LHAR", "", "", "13-26", "Optical microscopy", "3.5* to 7.8* (D)", "", "PD50", "D", "10.1021_acs.jpcc.5c06502", "Table 1, Fig. 10b", "four samples; equivalent aspect ratios and precursor exposure in L are printed in the source"),
 ("IV", "Ni", "NiCp2", "H2O/H2*", "", "Nanowires (GaAs)", "", "170", "", "STEM-EDS", "", "", "", "", "10.1021_acsami.0c06879", "Fig. S2", "step coverage ratios on the figure, not read"),
]
NR += [
 ("IV", "SiO2", "BDEAS", "O2*", "I", "LHAR", "", "100-240", "", "Reflectometry", "about 235* to 450* (D)", "", "PD50", "D", "10.1021_acs.jpcc.1c01505", "Fig. 2, Fig. 4", "half-thickness aspect ratios of about 470 to 900 at 12 s plasma across temperature and pressure, read by eye and halved"),
 ("IV", "TiO2", "TDMAT", "O2*", "I", "LHAR", "", "100-240", "", "Reflectometry", "about 225* to 350* (D)", "", "PD50", "D", "10.1021_acs.jpcc.1c01505", "Fig. 3", "about 450 to 700 at 12 s plasma, read by eye and halved; at the highest temperature the precursor step limits the depth"),
]
NRF = ["table", "film", "precursor", "coreactant", "plasma_config", "structure", "EAR", "T_C", "exposure_printed", "method", "coated_ear_printed", "coated_ear_value", "coated_ear_basis", "profile", "paper_id", "source", "note"]
wr("new_rows.csv", [dict(zip(NRF, r)) for r in NR])

# ----------------------------------------------------------------------------- ideas 8 and 9: measured profiles, by eye
PR = [  # paper, figure, series, points total, points in the 80-20% region, plateau, fit for s0, growth type by shape, feature used, remark
 ("10.1063_1.5028178", "6", "Al2O3, 500 cycles", "about 85", "about 8", "yes", "yes", "diffusion-limited", "flat, then a front of about 20 µm", ""),
 ("10.1063_1.5028178", "7", "TiO2, 1000 cycles", "about 70", "about 35", "no", "no: no plateau", "cannot decide", "falls from the entrance on", "looks reaction-limited, but the authors' fit gives a high sticking coefficient (0.1) with weak reversible adsorption"),
 ("10.1039_d0cp03358h", "7", "spot 5 µm", "about 90", "10 to 15", "yes", "yes", "diffusion-limited", "flat, then a sharp front", ""),
 ("10.1039_d0cp03358h", "7", "spot 25 and 50 µm", "about 90 each", "15 to 25", "yes", "no: spot wider than the front", "diffusion-limited", "front smeared by the instrument", "more points, but the slope is the instrument's"),
 ("10.1039_d0cp03358h", "8a, 8b", "repeats and four runs", "about 90 each", "10 to 15", "yes", "yes", "diffusion-limited", "flat, then a sharp front", "fronts of nominally equal runs differ by tens of µm"),
 ("10.1039_d0cp03358h", "9a-c", "H 500 nm", "about 90", "10 to 15", "yes", "yes", "diffusion-limited", "flat, then a sharp front", ""),
 ("10.1039_d0cp03358h", "9a-c", "H 100 nm", "about 30 in the channel", "about 8", "no", "no: no plateau, channel closing", "cannot decide", "falls from the entrance on", "the shape of a reaction-limited profile, caused here by film growth narrowing a 100 nm channel"),
 ("10.1039_d0cp03358h", "9a-c", "H 2000 nm", "about 90", "about 10, curve cut at one third", "yes", "marginal", "diffusion-limited", "flat, then a front", "gas-phase collisions matter at this height"),
 ("10.1039_d0cp03358h", "9d-f", "250, 500, 1000 cycles", "about 90 each", "10 to 15", "yes", "yes", "diffusion-limited", "flat, then a sharp front", ""),
 ("10.1039_d0cp03358h", "11a-b", "pulse and purge series", "about 90 each", "10 to 25", "yes", "yes", "diffusion-limited", "flat, then a front; broader at 0.4 s", ""),
 ("10.1116_6.0001094", "11", "six power and pulse pairs", "10 each", "3 to 6; most never reach 20%", "partly", "no", "cannot decide", "gradual decline over the whole 20 mm", "the authors state diffusion-limited conditions; in a structure of aspect ratio 20 the three types look alike"),
 ("10.1116_6.0001094", "12", "five pressures", "10 each", "2 to 5; none reaches 20%", "partly", "no", "cannot decide", "gradual decline", "same"),
 ("10.1021_acs.jpcc.9b08176", "2B", "SiO2, four plasma times", "40 to 90 each", "about 10", "yes", "yes, for a recombination probability", "recombination-limited", "long shallow decline, then a front; depth grows with the logarithm of time", "the time series, not one profile, is what identifies the type"),
 ("10.1021_acs.jpcc.9b08176", "2B", "TiO2, Al2O3, HfO2", "10 to 80 each", "5 to 8", "no", "marginal", "recombination-limited", "decline from the entrance on", "from one profile alone this cannot be told from reaction-limited growth"),
 ("10.1063_5.0168768", "2a", "SiO2, three plasma times", "about 35 each", "3 to 4", "yes, short", "no", "recombination-limited", "front moves with the logarithm of time", "type stated by the authors"),
 ("10.1063_5.0168768", "2b", "TiO2, three plasma times", "about 35 each", "6 to 8", "no", "marginal", "recombination-limited", "decline from the entrance, then a front", ""),
 ("10.1021_acs.jpcc.5c06502", "10b", "samples A to D", "continuous traces", "many, from image grey levels", "no", "no: thickness scale is indirect", "recombination-limited", "depth set by plasma time, not precursor dose", "type stated by the authors from the comparison of four samples"),
 ("10.1038_s41467-022-35428-6", "4b", "four inhibitor treatments", "about 12 each", "0: no front", "not applicable", "no", "none of the three", "thinner at the top than at the bottom", "inhibitor-controlled growth is outside the scheme"),
 ("10.1116_1.4892385", "5", "ZrO2, 1135 cycles", "17", "about 9, scattered", "no", "marginal", "reaction-limited", "decline from the surface on; fitted probability 2e-4", ""),
 ("10.3762_bjnano.5.25", "6b", "400 cycles", "13", "about 6", "yes", "marginal", "diffusion-limited", "flat to 12 µm, then a slope", "the slope reflects exposure not scaled as tubes thicken"),
 ("10.3762_bjnano.5.25", "6b", "200 cycles", "12", "2 to 3", "yes", "no", "diffusion-limited", "flat to 30 µm, then a drop", ""),
 ("10.3762_bjnano.5.25", "6c", "three series", "8 to 10 each", "3 to 5", "yes", "no", "diffusion-limited", "flat, then a slope", ""),
]
PR0 = len(PR)
PR += [
 ("10.1149_1.3072694", "5", "aspect ratio 100", "about 20", "3 to 4", "yes", "marginal", "diffusion-limited", "flat, then a front 2 mm wide", "the authors decline to fit: the result depends on the pressure to 0.01 Pa"),
 ("10.1149_1.3072694", "5", "aspect ratio 33 and 50", "about 20 each", "0 to 2", "yes", "no: coated to the end", "diffusion-limited", "no front inside the structure", ""),
 ("10.1149_1.3301664", "2a, 6a", "thermal, aspect ratio 50", "about 30", "about 8", "yes, with a slow early decline", "marginal", "diffusion-limited", "decline, then a front", "the authors suspect a CVD-like part in the early decline"),
 ("10.1149_1.3301664", "2b, 3, 4b, 5a, 9a", "plasma Al2O3, about 20 profiles", "about 30 each", "5 to 15", "partly", "no: two reactions overlap", "cannot decide", "gradual decline with a kink and a tail", "the authors attribute the tail to water formed in the plasma step: recombination-limited growth with a thermal side reaction"),
 ("10.1149_1.3301664", "5b", "plasma AlN, three plasma times", "about 30 each", "5 to 8", "no", "no", "recombination-limited", "falls from the entrance on within 5 mm", "the film composition changes with depth"),
 ("10.1149_1.3301664", "10", "plasma CoOx", "about 30", "about 4", "yes, short", "marginal", "cannot decide", "flat to 3 mm, then a sharp front", "a plasma process with the shape of a diffusion-limited profile"),
 ("10.1016_j.surfcoat.2012.02.038", "5, 7", "thermal, three pulse times, two densities", "5 to 8 each", "2 to 4", "partly", "no", "diffusion-limited", "front moves in with pulse time", "an X-ray signal with wide error bars; type stated by the authors"),
 ("10.1016_j.surfcoat.2012.02.038", "10", "plasma", "9", "3", "no", "no", "recombination-limited", "falls from the entrance on, depth six times less than thermal", "type from the comparison with the thermal run, not from the shape"),
 ("10.1116_1.4903941", "5a", "Al2O3, 300 °C", "about 50", "about 10", "yes", "yes", "diffusion-limited", "flat to 52 um, then a front", "the tail below 30 nm is not reliable (stated)"),
 ("10.1116_1.4903941", "5b", "TiO2, 110 °C, three gaps", "30 to 45 each", "10 to 20", "no", "no: no plateau", "cannot decide", "falls from the entrance on, in two slopes", "same behaviour as the TiO2 profile of 10.1063_1.5028178"),
 ("10.1116_1.4971196", "8, 9", "Al2O3, four access holes", "about 100 each", "8 to 10 per edge", "yes, with growth above the planar level near the hole", "yes", "diffusion-limited", "flat, then an edge about 100 um wide", "the authors fit 0.02 (0.009 to 0.02); the reference level is chosen"),
 ("10.1116_1.4971196", "11, 12", "SiO2, four access holes", "about 100 each", "the whole scan", "no", "yes, for a low value", "reaction-limited", "smooth decline over the whole cavity", "the authors fit 3e-5; a low value is fixed by the overall shape"),
 ("10.1016_j.apsusc.2009.02.055", "3", "TiO2, one sample", "4", "0: never below 70%", "one point", "no: four points", "cannot decide", "gentle decline", "the authors fit 0.02 ± 0.005 from these four points"),
 ("10.1016_j.apsusc.2010.01.025", "1", "HfO2 at 180, 230, 270 °C", "4 to 5 each", "2 to 3", "one point", "no: too few points", "cannot decide", "front steepens with temperature", "the authors fit 0.031, 0.15, 0.56; shape goes from reaction- to diffusion-limited"),
 ("10.1016_j.apsusc.2010.01.025", "3", "TiO2, 270 °C", "5", "0", "no", "no", "reaction-limited", "nearly flat decline", "only a range, 0.006 to 0.018"),
 ("10.1149_1.2789802", "4", "TiO2, one hole", "7 values at three heights", "about 3", "no", "no", "cannot decide", "thinner toward the bottom", "the model is fitted to top and bottom values against pulse time, not to this profile"),
 ("10.1063_1.4972120", "5, 7", "Pt, four trenches; one trench by TEM", "6 each; 160", "0: no front", "yes, all of it", "no: saturated", "none of the three", "flat to the bottom", "a fully coated structure carries no kinetic information"),
 ("10.1021_cm0303080", "5a, 6a", "ZnO, four exposure times, three pore sizes", "about 25 each", "5 to 10", "yes, short", "marginal", "diffusion-limited", "front moves in with the square root of time", "probe of 3 to 5 um against fronts of 5 to 10 um; type stated by the authors"),
 ("10.1021_cm0303080", "7b", "ZnO, aspect ratio 5000", "about 100", "0: no front", "yes", "no: saturated", "none of the three", "coated through, with a slope across the membrane", ""),
 ("10.1021_acs.jpcc.1c01505", "2A, 4A", "SiO2, four temperatures, five pressures", "50 to 100 each", "about 10", "a slow decline, then a front", "yes, for a recombination probability", "recombination-limited", "depth grows with the logarithm of plasma time", "type from the time series"),
 ("10.1021_acs.jpcc.1c01505", "3A", "TiO2, three temperatures", "50 to 100 each", "10 to 20", "no", "marginal", "recombination-limited", "declines from the entrance on", "at the highest temperature the precursor step limits the depth (stated), which the shape does not show"),
]
PRF = ["paper_id", "figure", "series", "points_total", "points_80_to_20", "plateau", "fit_for_sticking", "growth_type_by_shape", "feature_used", "remark"]
wr("profiles.csv", [dict(zip(PRF, r)) for r in PR])

# ----------------------------------------------------------------------------- step 3
num = lambda s: float(s) if s.replace(".", "", 1).isdigit() else None
T = ("II", "III", "IV")
a_cov = [[t, sum(1 for r in CONF if r["table"] == t), sum(1 for r in CONF if r["table"] == t and r["exposure_printed"])] for t in T]
tma = [r for r in CONF if r["table"] == "II" and r["precursor"] == "TMA" and r["coreactant"] == "H2O"]
a_tma = [[r["structure"], r["EAR"], r["T_C"], r["exposure_printed"] or "—", r["coated_ear_printed"], {"complete": "lower bound", "PD50": "measured (PD50%)", "conformal": "no number"}.get(r["coated_ear_basis"], "—"), r["ref"]] for r in tma]

b_ear = [
 ("10.1186_s11671-015-0872-9 (ref. 140)", "hole, 500 nm deep, 67 nm wide", "L/w", "7.5", "7.5", "agree"),
 ("10.1007_s12274-010-0066-9 (ref. 173)", "hole, 90 µm deep, 1 µm wide", "L/w", "90", "90", "agree"),
 ("10.1007_s12274-010-0066-9 (ref. 173)", "AAO, 60 µm thick, 250 to 300 nm pores", "L/w", "200 to 240", "200", "agree"),
 ("10.1149_2.067203jes (ref. 202)", "trench, 18.5 µm deep, 0.6 µm wide", "L/(2w)", "15", "15", "agree"),
 ("10.1063_1.5028178 (ref. 77)", "lateral channel, half thickness at about 133 µm, gap 0.5 µm", "L/(2w)", "about 133", "130 (coated)", "agree"),
 ("10.1039_c5ta00205b (ref. 196)", "AAO; dimensions of the coated membrane not found", "L/w", "—", "120", "cannot check"),
 ("10.1116_6.0001094 (not a review row)", "trench, 20 mm deep, 1 mm opening", "L/(2w)", "10", "10 (stated by the source)", "agree"),
 ("10.1021_acs.jpcc.5c06502 (not a review row)", "lateral channel, PD50% 4.4 µm, gap 0.5 µm", "L/(2w)", "4.4", "4.4 (stated by the source)", "agree"),
 ("review's own example, Sec. II D (ref. 62, not in the 44)", "holes 7.3 µm deep, 0.17 µm wide", "L/w", "43", "36 (Table II, 'Holes')", "differ; 36 would follow from the elongated-hole formula with a second width near 0.25 µm"),
]
b_ear = [r for r in b_ear if not r[0].startswith("review's own example")]
b_ear += [
 ("10.1002_cvde.200390005 (ref. 62)", "elliptical holes 0.17 x 0.30 um, 7.3 um deep", "L(w+z)/(2wz)", "34", "36", "agree (the source computes 36 from the true perimeter)"),
 ("10.1149_1.3072694 (ref. 67)", "rectangular hole 5 x 20 mm, 0.1 mm high (height from the review's Fig. 22)", "L(w+z)/(2wz)", "102", "100", "agree"),
 ("10.1149_1.3301664 (ref. 70)", "rectangular hole 5 x 20 mm, spacer 3.9, 1.3, 0.5 mm", "L(w+z)/(2wz)", "4.6; 9.7; 22", "10 (the row used)", "agree"),
 ("10.1021_cm0303080 (ref. 65)", "pores 65 nm x 50 um; 19 nm x 92 um", "L/w", "769; 4840", "770 and 700 for the first; 5000", "agree, but one membrane has two values; pores open at both ends, so the diffusion length is half"),
 ("10.1016_j.apsusc.2009.02.055 and 2010.01.025 (refs 178, 180)", "holes 130 nm x 2 um, the same in both papers", "L/w", "15.4", "20 (ref. 178 row); 15.3 (ref. 180 rows)", "differ for ref. 178: 20 is the number the source writes, not what its dimensions give"),
 ("10.1063_1.2714685 (ref. 200)", "holes 0.3 um, aspect ratio 10 stated", "L/w", "10", "10", "agree"),
 ("10.1149_1.2789802 (ref. 204)", "holes 0.15 um, aspect ratio 8.7 stated", "L/w", "8.7", "8.7", "agree"),
 ("10.1063_1.4972120 (ref. 228)", "trenches, aspect ratio up to 34", "L/(2w)", "17", "17", "agree"),
 ("10.1116_1.4903941 (ref. 86)", "lateral channels, aspect ratio 20 to 25000 (Fig. 1 table)", "L/(2w)", "10 to 12500", "10-12500", "agree"),
 ("10.1016_j.surfcoat.2012.02.038 (ref. 69)", "hole 1 x 1 x 5 cm filled with fibres", "L/w", "5 for the empty hole", "5", "agree as a hole; the fibre filling is not in the number"),
]
# Gordon's minimum exposure for full coverage, applied to TMA at 200 °C (ref. 62, Eq. 15): Pt = S sqrt(2 pi m k T) (1 + 19a/4 + 3a^2/2)
GORDON_S = 4.5e18          # TMA molecules per m2 per cycle, taken from the saturation value of 10.1063_1.2714685 (4.47e18)
def gordon_L(a, T=473.0, m_amu=72.0):
    flat = GORDON_S * math.sqrt(2 * math.pi * m_amu * 1.6605e-27 * 1.380649e-23 * T)      # Pa s on a flat surface
    return flat * (1 + 4.75 * a + 1.5 * a * a) * 7500.6                                    # langmuir
def gordon_a(L_):
    lo, hi = 0.1, 1e5
    for _ in range(80):
        mid = math.sqrt(lo * hi); lo, hi = (mid, hi) if gordon_L(mid) < L_ else (lo, mid)
    return lo
A_SRC = [  # source-side points for TMA/H2O: exposure (10^3 L), coated EAR or bound, kind, label, where
 (9, 33, "lower", "macro hole, aspect ratio 33, fully coated", "10.1149_1.3072694 Fig. 5"),
 (9, 49, "measured", "macro hole, aspect ratio 50, half thickness near the end (by eye)", "10.1149_1.3072694 Fig. 5"),
 (9, 55, "measured", "macro hole, aspect ratio 100, half thickness at 11 mm (by eye)", "10.1149_1.3072694 Fig. 5"),
 (450, 385, "lower", "AAO 65 nm x 50 um, coated from both ends at 3 s", "10.1021_cm0303080 Fig. 3"),
 (150, 385, "upper", "the same membrane at 1 s: centre not coated", "10.1021_cm0303080 Fig. 3"),
]
# c. join Table IV to Table VII
MAP = {"Al2O3": ("O", "Alumina", "O2 plasma; the growing surface is alumina"), "SiO2": ("O", "Silica", "O2 plasma; silica"), "TiO2": ("O", "Titania", "O2 plasma; titania"),
       "Ni": ("H", "Nickel", "H2 plasma on a nickel film"), "Cu": ("H", "Copper", "H2 plasma on a copper film")}
NOMAP = [("HfO2, Ta2O5", "no hafnia or tantala surface in Table VII"), ("Ti (TiCl4/O2*)", "film printed as Ti; unclear whether metal or oxide"),
         ("AlN, SiNx, TiN, Mo2N, TaN", "Table VII has N and H on metals, silicon, silica and steel, but on no nitride"), ("Co, Ru (NH3*)", "no cobalt or ruthenium surface for H or N"),
         ("Ag, Ta (H2*)", "no silver or tantalum surface"), ("Ir, Pt (O2*)", "no noble-metal surface for O atoms in Table VII (Table VI has ozone on Pt only)")]
rv = collections.defaultdict(list)
for p in PAR:
    if p["table"] == "VII": rv[(p["species"], p["surface_or_material"])].append(p)
c_rows = []
for r in CONF:
    if r["table"] == "IV" and r["film"] in MAP and r["coated_ear_value"]:
        sp, surf, why = MAP[r["film"]]
        vals = [float(p["value_printed"].split("±")[0]) for p in rv[(sp, surf)]]
        c_rows.append(dict(film=r["film"], proc=r["precursor"] + "/" + r["coreactant"], struct=r["structure"] or "(trench)", ear=r["EAR"], coated=float(r["coated_ear_value"]), basis=r["coated_ear_basis"], sp=sp, surf=surf, rlo=min(vals), rhi=max(vals), ref=r["ref"]))
LH = [  # r from the parsed papers: surface, r, regime, paper, where
 ("Silica", 6e-5, "50 mTorr, 200 °C", "10.1021_acs.jpcc.9b08176", "Fig. 3"), ("Titania", 7e-5, "50 mTorr, 200 °C", "10.1021_acs.jpcc.9b08176", "Fig. 3"),
 ("Alumina", (1e-3, 1e-2), "50 mTorr, 200 °C; a range", "10.1021_acs.jpcc.9b08176", "text, Table 1"), ("Hafnia", (1e-3, 1e-1), "50 mTorr, 200 °C; a range", "10.1021_acs.jpcc.9b08176", "text, Table 1"),
 ("Silica", 4e-4, "atmospheric, 100 °C", "10.1063_5.0168768", "Fig. 3, Table I"), ("Titania", 6e-5, "atmospheric, 100 °C", "10.1063_5.0168768", "Fig. 3, Table I"),
 ("Silica", 9e-5, "low pressure, 100 °C, cited there", "10.1063_5.0168768", "Table I"), ("Titania", 4e-5, "low pressure, 100 °C, cited there", "10.1063_5.0168768", "Table I"),
 ("Iridium oxide", 3e-3, "atmospheric", "10.1021_acs.jpcc.5c06502", "body text"),
]
LH += [
 ("Silica", (3e-5, 1e-4), "50 mTorr, 100 to 240 °C; falls with temperature", "10.1021_acs.jpcc.1c01505", "Fig. 5A"),
 ("Silica", (2e-5, 2e-4), "180 °C, 12 to 130 mTorr; falls with pressure", "10.1021_acs.jpcc.1c01505", "Fig. 5B"),
 ("Titania", (1e-5, 4e-5), "50 mTorr, 100 to 240 °C; upper limit at 240 °C", "10.1021_acs.jpcc.1c01505", "Fig. 5A"),
 ("Alumina", (9.7e-3, 6.1e-2), "sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature", "10.1016_j.cattod.2003.11.022", "Table 1"),
 ("Titania", (1.4e-2, 3.1e-2), "sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature", "10.1016_j.cattod.2003.11.022", "Table 1"),
 ("Silica", (4e-3, 9.3e-3), "oxidized SiC, 110 Pa air plasma, 300 to 773 K", "10.1016_j.cattod.2003.11.022", "Table 1"),
 ("Silica", 2e-4, "literature value, cited", "10.1149_1.3491381", "Table II"),
 ("Alumina", 2.1e-3, "literature value, cited (the same as Table VII)", "10.1149_1.3491381", "Table II"),
]
LH = [x for x in LH if "cited there" not in x[2]] + [
 ("Silica", 9e-5, "low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 1e-4)", "10.1063_5.0168768", "Table I"),
 ("Titania", 4e-5, "low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 4e-5)", "10.1063_5.0168768", "Table I")]
# d. same film, different oxidant: pairs with the same structure type
D = [
 ("Al2O3", "macro lateral, EAR 5, 75 °C, one paper (ref. 69)", "2.5 PD50 at 18", "—", "0.75 PD50 at 5", "best match in the tables: same structure, temperature and paper; exposures differ by 3.6"),
 ("Al2O3", "macro lateral, 200 °C (refs 67, 70)", "50 PD50 at 9 (EAR 100)", "—", "10 complete at 27 (EAR 10)", "plasma value is a lower bound capped by the structure"),
 ("Al2O3", "maximum per table", "1750 complete", "none in the table (text: 20)", "15 PD50; 13.5 complete", "the 30 often quoted for plasma is SiO2 and HfO2"),
 ("TiO2", "hole", "—", "20 PD50 (EAR 20)", "8.7 complete (EAR 8.7)", "no exposure in either"),
 ("HfO2", "hole", "36 complete at 6 to 9", "9.6 PD50 (EAR 15.3)", "— (trench: 30 complete)", "ozone row has no exposure"),
 ("Pt", "AAO, EAR 150", "110 PD50, 250 °C", "35 PD50, 150 °C", "—", "same structure value; temperatures differ; no exposure"),
 ("Ir / IrO2", "LHAR, one paper (ref. 87)", "15 and 20 PD50, 250 °C", "15 and 45 PD50, 185 °C", "—", "same structure and paper; no exposure"),
 ("V2O5", "AAO", "7000 complete", "100 complete; 44 of 185", "—", "no exposure"),
 ("ZnO", "AAO", "700 and 5000 complete at 2000 and 600000", "250 complete", "—", "ozone row has no exposure"),
 ("Ru", "hole", "4.6 to 32 complete; 20 PD50", "16 complete", "— (trench: 2 complete)", "all but one are lower bounds"),
]
D += [
 ("Al2O3", "fibre-filled macro hole, 75 °C, same TMA exposure of 4.8, one paper (10.1016_j.surfcoat.2012.02.038 Fig. 10; from the source, by eye)", "about 1.8 PD50", "—", "about 0.3 PD50", "the matched pair the review rows miss: its thermal row is the 30 s run (18), its plasma row the 8 s run (5)"),
 ("Al2O3", "empty macro hole, aspect ratio 22, 200 °C, same exposures, one paper (10.1149_1.3301664 Fig. 2; from the source, by eye)", "22 complete", "—", "about 14 PD50", "stated by the source to differ only in the pump time; the review pairs a ref. 67 row with a ref. 70 row of another structure"),
]
# e. sticking values
SV = [  # species, value lo, hi, method/model, data_kind, s or s0, source, in review
 ("TMA", 1e-3, 1e-3, "Monte Carlo model (value quoted from an earlier paper and used as input)", "cited", "s (reactive sticking coefficient)", "review Table V, ref. 65 = 10.1021_cm0303080", 1), ("TMA", 0.026, 0.026, "ballistic model with re-emission, adsorption order 1.9; TMA/O2 plasma process", "fit", "s0 (checked in the source)", "review Table V, ref. 200 = 10.1063_1.2714685", 1),
 ("TMA", 0.1, 0.1, "conductance model; value chosen, no fit made", "simulation input", "s0 (checked in the source)", "review Table V, ref. 67 = 10.1149_1.3072694", 1), ("TMA", 0.1, 0.9, "DFT", "calculated", "not checked", "review Table V, ref. 176", 1),
 ("TMA", 5.72e-3, 5.72e-3, "continuum (diffusion-reaction) model", "fit", "s0 (checked in the source)", "review Table V, ref. 77 = 10.1063_1.5028178", 1), ("TMA", 9e-3, 0.02, "Monte Carlo model of a cavity, best value 0.02", "fit", "s0 (checked in the source)", "review Table V, ref. 128 = 10.1116_1.4971196", 1),
 ("TMA", 2e-3, 5e-3, "sum-frequency generation", "measured", "not checked", "review Table V, ref. 237", 1), ("TMA", 0.01, 0.01, "Auger electron spectroscopy", "measured", "not checked", "review Table V, ref. 235", 1),
 ("TMA", 4e-3, 4e-3, "slope at half thickness", "calculated", "s0", "10.1039_d0cp03358h Table 2", 0), ("TMA", 5e-4, 2e-3, "slope at half thickness (Arts 2019)", "cited", "s0", "quoted in 10.1039_d0cp03358h Table 2 and 10.1016_j.sse.2022.108584 Table 2", 0),
 ("TMA", 7.5e-3, 7.5e-3, "diffusion with evaporation flux, fitted by hand", "fit", "s0", "10.1016_j.sse.2022.108584 Table 2", 0), ("TMA", 0.012, 0.012, "diffusion-reaction model", "simulation input", "s0", "10.1039_d0cp03358h Fig. 10", 0),
 ("TMA", 0.01, 0.01, "diffusion-reaction model, baseline", "simulation input", "s0", "10.1039_d1cp04758b Table 1", 0), ("TMA", 8e-4, 2e-3, "literature range", "cited", "not stated", "quoted in 10.1116_6.0001094", 0),
 ("H2O", 3e-4, 3e-4, "slope at half thickness, one sample", "calculated", "s0", "10.1039_d0cp03358h Table 2", 0), ("H2O", 5e-5, 1.9e-4, "diffusion with evaporation flux, 150 to 310 °C", "fit", "s0", "10.1016_j.sse.2022.108584 Table 1", 0),
 ("O radical (TMA/O2* process)", 0.172, 0.316, "Markov chain model, recombination held fixed", "fit", "s0", "10.1116_6.0001094 Sec. III D", 0), ("TEMAZ", 2e-4, 2e-4, "diffusion model in a porous body", "fit", "s0", "10.1116_1.4892385 Fig. 5", 0),
]
SV += [
 ("TMA", 0.01, 0.01, "one-dimensional Monte Carlo in a fibre plug, 75 °C; picked by comparing simulations", "fit", "s0", "10.1016_j.surfcoat.2012.02.038 Sec. 4.2", 0),
 ("TMA", 0.1, 0.1, "Monte Carlo of a macro hole", "simulation input", "s0", "10.1149_1.3301664 Fig. 6b", 0),
 ("H2O", 0.05, 0.05, "Monte Carlo of a macro hole", "simulation input", "s0", "10.1149_1.3301664 Fig. 9", 0),
 ("TDMAT (with O3)", 0.015, 0.025, "Monte Carlo of a hole, four thickness points, 180 °C", "fit", "s0", "review Table V, ref. 178 = 10.1016_j.apsusc.2009.02.055", 1),
 ("TEMAHf (with O3)", 0.031, 0.56, "Monte Carlo of a hole, 180 to 270 °C; activation energy 0.62 eV", "fit", "s0", "review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025", 1),
 ("Cp*Ti(OMe)3 (with O3)", 0.006, 0.018, "Monte Carlo of a hole, 270 °C, best value 0.01", "fit", "s0", "review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025", 1),
 ("TTIP (O2 plasma process)", 0.04, 0.1, "ballistic model with re-emission, 125 to 225 °C", "fit", "s0", "review Table V, ref. 204 = 10.1149_1.2789802", 1),
 ("BDEAS (with O3)", 3e-5, 5e-5, "Monte Carlo model of a cavity, 300 °C", "fit", "s0", "review Table V, ref. 128 = 10.1116_1.4971196", 1),
 ("DEZ", 7e-3, 7e-3, "Monte Carlo of a pore; origin of the value not found", "simulation input", "s", "review Table V, ref. 65 = 10.1021_cm0303080", 1),
 ("SiCl4", 1e-8, 1e-8, "quoted from another paper", "cited", "s", "review Table V, ref. 65 = 10.1021_cm0303080", 1),
 ("Hf(NMe2)4", 0.07, 1.0, "microbalance, a lower limit of 0.07", "cited", "s", "10.1002_cvde.200390005 Sec. 3.1", 0),
]
f_cnt = [[t] + [sum(1 for r in CONF if r["table"] == t and (r["coated_ear_basis"] or "blank") == b) for b in ("complete", "PD50", "conformal", "blank")] for t in T]
unmarked = [r for r in CONF if "not marked" in r["note"]]
pd_eq = [r for r in CONF if r["coated_ear_basis"] == "PD50" and r["EAR"] == r["coated_ear_value"]]
g_rows = []
for ref in sorted({r["ref"] for r in CONF if r["profile"]}, key=int):
    rr = [r for r in CONF if r["ref"] == ref and r["profile"]]; m = MAN.get(rr[0]["doi"], {})
    g_rows.append([ref, rr[0]["doi"], "; ".join(sorted({f"{r['film']} ({'II III IV'.split()[T.index(r['table'])]})" for r in rr})), m.get("year", ""), "have it" if m.get("pdf_status") == "ok" else "to collect", m.get("oa_status", "")])

# ----------------------------------------------------------------------------- ideas
IDEAS = [
 ("1. One process across several test structures", "doable partly",
  [("Sec. VII says a benchmark across test structures would be useful", "true", "outlook, p. 021302-30"), ("Sec. IV A: TMA/H2O coated EAR from 5 to 1750", "true", "p. 021302-15"),
   ("Table II has 12 TMA/H2O rows, 6 with an exposure", "true", "Table II"), ("the record row (AAO, 1750) has no exposure", "true", "Table II, ref. 96"),
   ("1 Pa·s is about 7500 L", "true", "but the review prints it the wrong way round, see 3b"), ("Fig. 17 shows Monte Carlo curves for the exposure needed", "true", "caption of Fig. 17; the a² scaling itself was not checked")],
  "Needs exposure for each row. Have: 6 of 12 in the review; three of those sources are now read (refs 65, 67, 69) and confirm the printed exposures. With them the square-law of ref. 62 can be tested for TMA: see 3a. The ref. 86 source is read too and gives no partial pressure, so its blank cannot be filled; ref. 77 gives a fitted, not measured, pressure. Missing: refs 134, 93, 96, 138 (no PDF). Joins Case 1, Case 8 and candidate A1."),
 ("2. Automatic EAR conversion", "doable partly",
  [("formulas for hole, trench, elongated hole; pillars from Monte Carlo", "true", "Sec. II G"), ("Werbrouck 2021 states AR 20 and EAR 10", "true", "its Sec. II D")],
  f"Needs L, w and the structure type from each source. Have: {len(b_ear)} checks; {sum(1 for r in b_ear if r[5].startswith('agree'))} agree. Three things a transform would have caught: one membrane listed as 770 and as 700, one hole type listed as 20 and as 15.3, and pores open at both ends counted at full length. The earlier finding that the review's worked example gives 43 against a table value of 36 is withdrawn: the source's holes are elliptical (0.17 by 0.30 um), 36 is the source's own number, and 43 is its value after coating. Missing: the sources of the other rows. Joins N9 and Case 8."),
 ("3. Continuing the tables after 2019", "doable now",
  [("Mo trench 100/95/90%", "true", "10.1116_6.0002804 Fig. 9a"), ("WCx step coverage about 80%", "true", "10.1021_acs.chemmater.6c00816 Fig. 4"), ("AlN with Kr, step coverage 1.6", "true", "10.1021_acs.jpclett.4c03545 Fig. 2"), ("PD50% in three plasma LHAR papers", "true", "Fig. 2A; body text; Table 1")],
  f"new_rows.csv holds {len(NR)} draft rows from 16 papers, each with its source (two added from 10.1021_acs.jpcc.1c01505). Exposure is blank in all but one. Three things do not fit the review's columns: a step coverage above 1, a profile thicker at the bottom, and atmospheric plasma. Adds a new case (a living table); uses Case 7 for the values written on images."),
 ("4. Recombination probability against coated EAR", "doable partly",
  [("the review explains the lower EAR of metals only in words; largest 30 for oxides, 17 for metals", "true", "p. 021302-19"), ("O on alumina: 0.0021 and 0.0097", "true", "Table VII, refs 250 and 251")],
  f"Have: {len(c_rows)} Table IV rows with a fair surface match, {sum(1 for r in c_rows if r['basis'] != 'PD50')} of them lower bounds. The order of the largest values follows r (silica, then alumina and titania, then copper and nickel), but lower bounds capped by the structure cannot test it. Missing: profiles for these rows. Two matched rows fail the source check (ref. 69: about 0.3, not 0.75; ref. 70: exposure). The Table VII values for alumina and titania are now traced to their source (ref. 251): sintered ceramics at 300 K in a 110 Pa air plasma, where r rises with temperature; on ALD films in lateral channels r is 200 to 1000 times lower for titania and falls with temperature and pressure. So Table VII values cannot stand in for the growth surface. Joins Case 2 and Case 8."),
 ("5. Same film, different oxidant", "doable partly",
  [("Al2O3 largest coated EAR about 1750, 20, 30 for thermal, ozone, plasma", "wrong in part", "1750 is right; 20 is in the running text only, the table cell says 'Ref. 175'; 30 is SiO2 and HfO2, the largest plasma Al2O3 value is 15 (PD50%) or 13.5"),
   ("TiO2, HfO2, Ru, Pt, ZnO also have pairs", "true", "plus V2O5, Fe2O3, Ir, SiO2, AlN, TiN, TaN"), ("the review compares maxima without matching", "true", "Sec. IV B")],
  "Have: 10 pairs from the tables with the same structure type, none matched in exposure, and now two matched pairs taken from the sources (refs 69 and 70): at equal exposure, structure and temperature the plasma process coats about 6 times and about 1.6 times less deep than the thermal one. Missing: exposure in every ozone row but one. Joins Case 8."),
 ("6. Why sticking probabilities scatter", "doable now",
  [("TMA has 8 values from 0.001 to 0.1, DFT 0.1 to 0.9", "true", "Table V"), ("the review only suggests the methods differ", "true", "p. 021302-16"),
   ("Ylilammi's 0.00572 is an initial sticking coefficient", "true", "source: c multiplies (1 − θ); the review's Sec. VI B 3 calls it initial, its Table V header says sticking probability")],
  f"Have: the 27 Table V rows and {sum(1 for s in SV if not s[7])} values outside the table, each with model and data kind. Of the 16 Table V rows now checked in a source, 2 are not results of the method named: the TMA value of ref. 65 is quoted from an earlier paper and that of ref. 67 is a chosen input. With those two removed and DFT set aside, the fitted TMA values run from 0.0005 to 0.026. Every checked value is an initial (bare-surface) one. Joins Case 4, Case 8 and N1."),
 ("7. Many coated EAR values are lower bounds", "doable now",
  [("coated EAR equals the structure EAR when fully coated, PD50% otherwise", "true", "captions of Tables II to IV"), ("'75 (D)' is a measured value", "true", "printed as 75* (D)")],
  f"Counts are in 3f. The rule is not applied evenly: {len(unmarked)} rows have a coated value below the structure value without the PD50% mark, and {len(pd_eq)} carry the mark although the two values are equal. One marked row is contradicted by its source (ref. 178: the profile never falls to one half). Supports a basis qualifier on coated_aspect_ratio; joins N3 and Case 8."),
 ("8. The (D) mark as a collection list", "doable partly",
  [("(D) means a thickness profile was reported", "true", "captions"), ("Sec. VI B 3: dense points in the slope region are needed (Fig. 22)", "true", "p. 021302-31")],
  f"Have: {len(g_rows)} references marked D, {sum(1 for g in g_rows if g[4] == 'have it')} with a PDF after the 15 obtained by hand. The point count now covers {len(PR)} measured profile groups ({len(PR) - PR0} new, profiles.csv). The rest of the list is in wanted_pdfs.csv."),
 ("9. Growth type classification", "doable partly",
  [("three growth types told apart by profile shape", "true", "Sec. II F, Fig. 4")],
  "Shape separates diffusion-limited profiles (plateau and front) well. It cannot separate reaction- from recombination-limited growth, or either from channel closing or reversible adsorption; those need a time or dose series. The new papers add three more cases where shape misleads: a plasma profile with a sharp front (CoOx), plasma profiles shaped by a thermal side reaction (Al2O3), and a precursor-limited plasma profile (TiO2 at the highest temperature). Ref. 66, now read, is where the third type was introduced; its regime diagram needs r and the aspect ratio, not the shape. Joins N7."),
]
fit_yes = sum(1 for r in PR if r[6].startswith("yes")); fit_m = sum(1 for r in PR if r[6] == "marginal")
gt = collections.Counter(r[7] for r in PR)

# ----------------------------------------------------------------------------- CREMERS.md
sc_cnt = collections.Counter(s[4] for s in SC); sc2 = collections.Counter(s[4] for s in SC2)
out = [f"""# Cremers 2019 read as data

Exploration, 2026-10-13. The review is Cremers, Puurunen and Dendooven, Appl. Phys. Rev. 6, 021302 (2019). Its Tables II to VII were typed in by hand (`transcribe.py`) and every row was compared with the page image. All values are data_kind cited; blank cells stay blank; footnote markers are in `note`.

Files: `conformality.csv` ({len(CONF)} rows), `parameters.csv` ({len(PAR)} rows), `source_checks.csv`, `new_rows.csv`, `profiles.csv`, `build.py`. Plots: Case 8 of `../reports/cases.html` (not tracked).

Updated the same day after 15 PDFs were obtained by hand (refs 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228, 251 and 10.1021/acs.jpcc.1c01505). `in_corpus` (was `in_44`) marks rows whose source has a PDF; `value_from_source` holds what the source gives for cells the review leaves blank, and never replaces a transcribed value. What the new sources changed is said under each result.

## Step 1. Transcription

{md(["Table", "Content", "Rows", "Rows whose source is in the corpus"], [[t, c, sum(1 for r in rows if r["table"] == t), sum(1 for r in rows if r["table"] == t and r["in_corpus"] == "yes")] for t, c, rows in (("II", "thermal ALD", CONF), ("III", "ozone-based ALD", CONF), ("IV", "plasma ALD", CONF), ("V", "sticking probabilities", PAR), ("VI", "ozone recombination", PAR), ("VII", "atom recombination", PAR))])}
Things seen while typing that a reader of the tables should know:
- The PD50% mark is an asterisk. It is lost in the PDF text layer, so it was read from the page images.
- Five reference numbers, in seven rows, have no DOI in the manifest (150, 168, 176, 201, 213).
- Table IV uses a plasma configuration "HW" that its caption does not define.
- Table V lists the ref. 77 value for TiCl4 on a line whose material cell is empty under "TiN"; the source deposits TiO2.
- The running text and the tables disagree in three places: ozone Al2O3 (text 20:1, table "Ref. 175"), the reference for ozone V2O5 (text 78, table 150), and O on Pyrex (text 0.000094, table 0.000045).

## Step 2. Source checks

{len(SC)} rows point to a paper in the corpus: {sc_cnt['agree']} agree, {sc_cnt['differ']} differ, {sc_cnt['not found']} not found. Of these, {len(SC1)} were checked against the first 44 papers and {len(SC2)} against the 15 added ({sc2['agree']} agree, {sc2['differ']} differ, {sc2['not found']} not found). `value_from_source` is filled in {sum(1 for r in CONF if r['value_from_source'])} rows: 5 give a value the review lacks, 6 record that the source does not state the exposure either.

{md(["Table", "Row in the review", "Ref.", "Paper", "Verdict", "Where", "Remark"], SC)}
## Step 3. Computed

### a. Exposure coverage

{md(["Table", "Rows", "Rows with an exposure"], a_cov)}
TMA/H2O, coated EAR against exposure (10^3 L):

{md(["Structure", "EAR", "T (°C)", "Exposure", "Coated EAR as printed", "Reading", "Ref."], a_tma)}
Of the six rows with an exposure, two are measured depths, three are lower bounds and one has no number. The two measured ones do not order by exposure (50 at 9, 2.5 at 18): the second is a hole filled with fibres at 75 °C (ref. 69, now read).

What the new sources add. From the sources, at the same exposures:

{md(["Exposure (10^3 L)", "Coated EAR", "Reading", "Structure", "Where"], [[x, y, {"lower": "lower bound", "measured": "measured, by eye", "upper": "upper bound"}[k], lab, wh] for x, y, k, lab, wh in A_SRC])}
The kinetic model of ref. 62 gives the exposure for full coverage as a flat-surface exposure times (1 + 19a/4 + 3a²/2). For TMA at 200 °C with {GORDON_S:.1e} molecules per m² per cycle (the saturation value of 10.1063_1.2714685, an assumption here) the flat-surface exposure is {gordon_L(0) :.1f} L, and 9 × 10^3 L should coat an aspect ratio of {gordon_a(9e3):.0f}. Ref. 67 measures 49 to 55 at that exposure. For the 65 nm by 50 µm membrane of ref. 65 the model asks for {gordon_L(385) / 1e3:.0f} × 10^3 L when the pores are entered from both ends (aspect ratio 385) and {gordon_L(769) / 1e3:.0f} × 10^3 L if they were entered from one; the source finds the centre uncoated at 150 and coated at 450. So the square law holds over these two structures, a factor of 50 in exposure, but only when the membrane is counted at half its length; the review's 770 at 4500 is a fully coated structure with ten times the needed exposure. The blanks of refs 86 and 77 cannot be filled from their sources.

### b. EAR check and the unit conversion

{md(["Source", "Dimensions", "Formula", "Computed", "Printed", "Result"], b_ear)}
What the new sources changed: ten checks added. The earlier "inconsistency" between the review's worked example (holes 0.17 µm wide and 7.3 µm deep, which would give 43) and its table value of 36 is withdrawn: ref. 62 describes elliptical holes of 0.17 by 0.30 µm with an aspect ratio of 36, and 43 is their value after coating. The review's text only leaves out the second axis.

The conversion in Sec. II D is printed as "1 L = 10^6 Torr s = 7500 Pa s". Both parts are wrong as printed: 1 L is 10^-6 Torr s, which is 1.33 × 10^-4 Pa s, and it is 1 Pa s that equals 7500 L. The tables use the correct relation: the review's own Fig. 22 gives 0.27 Pa for 4 s, which is 8100 L against the 9 × 10^3 L of the first row of Table II, and the ref. 98 row reproduces from the source's pressure and pulse time.

### c. Recombination probability against coated EAR (Table IV with Table VII)

Mappings used: {"; ".join(f"{k} → {v[0]} on {v[1].lower()} ({v[2]})" for k, v in MAP.items())}.
Left out: {"; ".join(f"{a} ({b})" for a, b in NOMAP)}.

{md(["Film", "Process", "Structure", "EAR", "Coated EAR", "Reading", "r from Table VII", "Ref."], [[r["film"], r["proc"], r["struct"], r["ear"], f"{r['coated']:g}", "measured (PD50%)" if r["basis"] == "PD50" else "lower bound", f"{r['rlo']:g}" + (f" to {r['rhi']:g}" if r["rhi"] != r["rlo"] else ""), r["ref"]] for r in c_rows])}
r of O atoms in the parsed papers, beside Table VII:

{md(["Surface", "Table VII", "From the parsed papers", "Conditions", "Paper", "Where"], [[s, "; ".join(p["value_printed"] for p in rv[("O", s)]) or "—", (f"{v[0]:g} to {v[1]:g}" if isinstance(v, tuple) else f"{v:g}"), reg, pid, wh] for s, v, reg, pid, wh in LH])}
What the new sources changed. The Table VII values of ref. 251 are confirmed, and their conditions are now known: sintered oxide discs at 300 K in an air plasma at 110 Pa, measured by emission actinometry, with r rising with temperature (alumina 0.0097 to 0.061, titania 0.014 to 0.031 between 300 and 773 K). The lateral-channel values of 10.1021_acs.jpcc.1c01505 are for the growing ALD film at 50 mTorr: titania about 4e-5 at 100 to 180 °C and below 1e-5 at 240 °C, falling with temperature. The titania gap is therefore a factor of about 350 at the low end and above 3000 near 500 K, with opposite temperature trends. Ref. 66 is the table that Table VII was updated from; it is a literature table itself. Ref. 228 quotes 0.01 for O on platinum, a surface Table VII lacks. Two of the fifteen matched rows change on the source check: ref. 69 (0.3 instead of 0.75) and ref. 70 (exposure).

### d. Same film, different oxidant

{md(["Film", "Structure matched on", "Thermal", "Ozone", "Plasma", "Remark"], D)}
What the new sources changed: the last two rows. They are the only pairs with the same structure, temperature and exposure, and both come from reading the source, not from the review's rows.

### e. Sticking values

{md(["Species", "Value", "Method or model", "data_kind", "s or s0", "Source", "In Table V"], [[a, f"{lo:g}" + (f" to {hi:g}" if hi != lo else ""), m, dk, ss, src, "yes" if inr else "no"] for a, lo, hi, m, dk, ss, src, inr in SV])}
What the new sources changed. Seven Table V sources are now read (refs 65, 67, 128, 178, 180, 200, 204; 11 rows). For TMA, the two ends of the non-DFT range are not results: 0.001 (ref. 65) is quoted from an earlier paper and 0.1 (ref. 67) is a chosen input. The fitted TMA values are 0.0005 to 0.0075 from lateral channels (after 2019), 0.009 to 0.02 from a cavity (ref. 128), 0.026 for the plasma process in holes (ref. 200) and 0.01 in a fibre plug at 75 °C. The hole-based fits of refs 178 and 180 rest on four or five thickness points each.

### f. Censoring

{md(["Table", "complete (lower bound)", "PD50% (measured)", "conformal (no number)", "blank or other"], f_cnt)}
In the blank column, {len(unmarked)} rows have a coated value below the structure value without the mark: {"; ".join(f"{r['film']} {r['coated_ear_value']} of {r['EAR']} (ref. {r['ref']})" for r in unmarked)}. {len(pd_eq)} rows carry the mark with equal values: {"; ".join(f"{r['film']} {r['EAR']} (ref. {r['ref']})" for r in pd_eq)}.

### g. Profiles: the references marked D

{md(["Ref.", "DOI", "Films (table)", "Year", "PDF", "Open access"], g_rows)}
## Ideas

"""]
for title, verdict, claims, body in IDEAS:
    out.append(f"### {title}\n- **Verdict: {verdict}.**\n" + "".join(f"- Claim: {c}. **{v}** ({w}).\n" for c, v, w in claims) + f"- {body}\n\n")
out.append(f"""### Idea 8, tried: calibration fitness of the measured profiles

Threshold used: at least 5 points between 80% and 20% of the reference level, a plateau or a stated reference to normalize by, and a probe smaller than the front. Reason: a front is described by two numbers, its position and its slope; with fewer than five points there are fewer than three left to judge the fit, and the review's Fig. 22 shows that sparse points in the slope region cannot tell sticking values apart. Counts are by eye.

Of {len(PR)} series groups: {fit_yes} fit, {fit_m} marginal, {len(PR) - fit_yes - fit_m} not fit.

{md(["Paper", "Fig.", "Series", "Points", "Points 80 to 20%", "Plateau", "Fit for a sticking value", "Remark"], [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[9]] for r in PR])}
### Idea 9, tried: growth type by shape

Counts: {", ".join(f"{k} {v}" for k, v in gt.most_common())}.

{md(["Paper", "Fig.", "Series", "Type by shape", "Feature used", "Where shape alone cannot decide"], [[r[0], r[1], r[2], r[7], r[8], r[9]] for r in PR])}
""")
(HERE / "CREMERS.md").write_text("".join(out), encoding="utf-8")

# ----------------------------------------------------------------------------- cremers.html
def loglog(w, h, xr, yr, xl, yl, title, xt, yt):
    L, R, Tp, B = 62, 20, 32, 46
    X = lambda v: L + (math.log10(v) - math.log10(xr[0])) / (math.log10(xr[1]) - math.log10(xr[0])) * (w - L - R)
    Y = lambda v: h - B - (math.log10(v) - math.log10(yr[0])) / (math.log10(yr[1]) - math.log10(yr[0])) * (h - Tp - B)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}"><text x="{L}" y="16" class="pt">{E(title)}</text>']
    for v in yt: e.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{L - 8}" y="{Y(v) + 4:.1f}" class="tk" text-anchor="end">{v:g}</text>')
    for v in xt: e.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{Tp}" y2="{h - B}" class="grid"/><text x="{X(v):.1f}" y="{h - B + 16}" class="tk" text-anchor="middle">{v:g}</text>')
    e.append(f'<text x="{(L + w - R) / 2}" y="{h - 8}" class="al" text-anchor="middle">{E(xl)}</text><text transform="translate(14 {(Tp + h - B) / 2}) rotate(-90)" class="al" text-anchor="middle">{E(yl)}</text>')
    return e, X, Y


def mark(e, x, y, slot, lower, tip, label="", dx=10, dy=4):
    c = f"var(--s{slot})"
    if lower:   # lower bound: open triangle pointing up with a stem
        e.append(f'<path d="M{x - 6:.1f} {y + 5:.1f} L{x + 6:.1f} {y + 5:.1f} L{x:.1f} {y - 7:.1f} Z" fill="var(--surface)" stroke="{c}" stroke-width="2"><title>{E(tip)}</title></path><line x1="{x:.1f}" x2="{x:.1f}" y1="{y - 7:.1f}" y2="{y - 20:.1f}" stroke="{c}" stroke-width="2"/>')
    else:
        e.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{c}" stroke="var(--surface)" stroke-width="1.5"><title>{E(tip)}</title></circle>')
    if label: e.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" class="tk" style="font-size:11.5px">{E(label)}</text>')

# plot a
e, X, Y = loglog(760, 400, (3, 2e4), (1, 3000), "exposure (10³ L, as printed)", "coated EAR", "TMA/H2O: coated EAR against exposure (Table II and its sources)", (10, 100, 1000, 10000), (1, 10, 100, 1000))
for r in tma:
    if r["exposure_printed"] and r["coated_ear_value"]:
        mark(e, X(float(r["exposure_printed"])), Y(float(r["coated_ear_value"])), 1, r["coated_ear_basis"] != "PD50", f"{r['structure']}, {r['T_C']} °C, ref. {r['ref']}: {r['coated_ear_printed']}", f"{r['structure']}, {r['T_C']} °C, ref. {r['ref']}")
for x_, y_, k_, lab_, wh_ in A_SRC:
    if k_ == "upper":
        xx, yy = X(x_), Y(y_)
        e.append(f'<path d="M{xx - 6:.1f} {yy - 5:.1f} L{xx + 6:.1f} {yy - 5:.1f} L{xx:.1f} {yy + 7:.1f} Z" fill="var(--surface)" stroke="var(--s2)" stroke-width="2"><title>{E(lab_ + " (" + wh_ + ")")}</title></path><line x1="{xx:.1f}" x2="{xx:.1f}" y1="{yy + 7:.1f}" y2="{yy + 20:.1f}" stroke="var(--s2)" stroke-width="2"/>')
    else:
        mark(e, X(x_), Y(y_), 2, k_ == "lower", lab_ + " (" + wh_ + ")")
gl = " ".join(f"{'M' if i == 0 else 'L'}{X(gordon_L(a_) / 1e3):.1f} {Y(a_):.1f}" for i, a_ in enumerate(a_ for a_ in [30, 50, 100, 200, 500, 1000, 2000] if 3 <= gordon_L(a_) / 1e3 <= 2e4))
e.append(f'<path d="{gl}" fill="none" stroke="var(--text2)" stroke-width="1.5" stroke-dasharray="5 4"/><text x="{X(9000):.1f}" y="{Y(2000):.1f}" class="warn" text-anchor="end">square law of ref. 62 for TMA (calculated)</text>')
e.append(f'<text x="{X(11):.1f}" y="{Y(100):.1f}" class="tk" style="font-size:11.5px">ref. 67: 33, 49, 55</text><text x="{X(130):.1f}" y="{Y(560):.1f}" class="tk" style="font-size:11.5px" text-anchor="middle">ref. 65 at half length: between 150 and 450</text>')
e.append(f'<text x="70" y="{Y(1.6):.1f}" class="warn">blue: Table II rows (6 of 12 have no exposure); orange: read in the sources; triangles are bounds</text>')
pa = "".join(e) + "</svg>"
# plot c
e, X, Y = loglog(760, 420, (1e-4, 1), (0.5, 50), "recombination probability r of the matched surface (Table VII)", "coated EAR (Table IV)", "Plasma ALD: coated EAR against r of the deposited surface", (1e-4, 1e-3, 1e-2, 1e-1, 1), (1, 3, 10, 30))
slot = {"SiO2": 1, "Al2O3": 2, "TiO2": 3, "Cu": 4, "Ni": 5}
seenf = set()
for r in c_rows:
    xm = math.sqrt(r["rlo"] * r["rhi"]); y = Y(r["coated"])
    if r["rhi"] != r["rlo"]: e.append(f'<line x1="{X(r["rlo"]):.1f}" x2="{X(r["rhi"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--s{slot[r["film"]]})" stroke-width="1.5" opacity=".55"/>')
    lab = "" if r["film"] in seenf else r["film"]; seenf.add(r["film"])
    mark(e, X(xm), y, slot[r["film"]], r["basis"] != "PD50", f"{r['film']} {r['proc']}, {r['struct']}, EAR {r['ear']}, coated {r['coated']:g}, ref. {r['ref']}; r {r['rlo']:g} to {r['rhi']:g}", lab, dx=-10 - 7 * len(lab), dy=-12)
pc = "".join(e) + "</svg>"
# dot plots
def dots(title, rows, xr, xt, xl, w=860, lab=380):
    h = 60 + 26 * len(rows); R = 150
    X = lambda v: lab + (math.log10(v) - math.log10(xr[0])) / (math.log10(xr[1]) - math.log10(xr[0])) * (w - lab - R)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}"><text x="12" y="16" class="pt">{E(title)}</text>']
    for v in xt: e.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="28" y2="{h - 34}" class="grid"/><text x="{X(v):.1f}" y="{h - 20}" class="tk" text-anchor="middle">{v:g}</text>')
    e.append(f'<text x="{(lab + w - R) / 2}" y="{h - 5}" class="al" text-anchor="middle">{E(xl)}</text>')
    for i, (label, lo, hi, s, filled, note) in enumerate(rows):
        y = 42 + i * 26; c = f"var(--s{s})"
        e.append(f'<text x="{lab - 10}" y="{y + 4}" class="tk" text-anchor="end" style="font-size:11.5px">{E(label)}</text>')
        if hi != lo: e.append(f'<line x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="5" stroke-linecap="round"><title>{E(label)}: {lo:g} to {hi:g}</title></line>')
        elif filled: e.append(f'<circle cx="{X(lo):.1f}" cy="{y}" r="5.5" fill="{c}"><title>{E(label)}: {lo:g}</title></circle>')
        else: e.append(f'<rect x="{X(lo) - 5:.1f}" y="{y - 5}" width="10" height="10" fill="var(--surface)" stroke="{c}" stroke-width="2.5"><title>{E(label)}: {lo:g}</title></rect>')
        e.append(f'<text x="{X(hi) + 11:.1f}" y="{y + 4}" class="tk" style="font-size:11px">{E(note)}</text>')
    return "".join(e) + "</svg>"
rrows = []
for surf, key in (("Alumina", "Alumina"), ("Silica", "Silica"), ("Titania", "Titania")):
    for p in rv[("O", key)]:
        v = float(p["value_printed"].split("±")[0]); rrows.append((f"{surf}: Table VII, ref. {p['ref']}", v, v, 1, True, f"{v:g} · cited"))
    for s, v, reg, pid, wh in LH:
        if s == surf:
            lo, hi = v if isinstance(v, tuple) else (v, v); rrows.append((f"{surf}: {pid}, {reg}", lo, hi, 2, True, (f"{lo:g} to {hi:g}" if hi != lo else f"{lo:g}") + (" · cited" if "cited" in reg else " · measured" if "ceramic" in reg or "SiC" in reg else " · fit")))
pr = dots("r of O atoms: Table VII against values in the parsed papers", rrows, (5e-6, 0.1), (1e-5, 1e-4, 1e-3, 1e-2, 1e-1), "recombination probability r (log scale)", lab=660, w=1140)
srows = [(f"{src}", lo, hi, 1 if inr else 2, dk in ("fit", "measured", "calculated"), (f"{lo:g} to {hi:g}" if hi != lo else f"{lo:g}") + f" · {dk}") for sp, lo, hi, m, dk, ss, src, inr in SV if sp == "TMA"]
ps = dots("Sticking value of TMA: Table V and values in the parsed papers", srows, (3e-4, 1.2), (1e-3, 1e-2, 1e-1, 1), "sticking value (log scale)", lab=660, w=1140)

# ----------------------------------------------------------------------------- wanted PDFs
BYREF = {}
for r in MAN.values():
    for n in __import__("re").split(r"[;,]", r["cremers_ref"]):
        if n.strip(): BYREF[n.strip()] = r
WANT = [  # ref number or DOI, why; ranked by hand
 ("10.1116/1.5093620", "Cases 1, 4, 8e: the third TMA/water lateral-channel data set and the slope-method sticking values for TMA and water; still needed in candidates A1, A2, N1"),
 ("96", "Case 8a, idea 1: the record rows (TMA/H2O 1750, TiO2 and V2O5 7000), all without exposure"),
 ("87", "Case 8d, ideas 5 and 8: Ir and IrO2 in lateral channels with four co-reactants in one paper, four profiles"),
 ("250", "Case 8c: source of eight O-atom values of Table VII, among them alumina 0.0021"),
 ("198", "Case 8c and 8d: five plasma rows in one paper, among them the two largest (SiO2 and HfO2 at 30)"),
 ("237", "Case 8e: TMA sticking measured directly (sum-frequency generation), 0.002 to 0.005"),
 ("238", "Case 8e: water sticking measured directly at two temperatures"),
 ("135", "Case 8a and 8d: Al2O3 and Pt in the same pores, both with an exposure"),
 ("89", "Case 8a, 8f: Y2O3 and HfO2 trench rows with exposure and a half-thickness depth"),
 ("171", "idea 8: Pt profile in pores (D) with a half-thickness depth"),
 ("195", "Case 8d, idea 8: Pt with ozone in the same pore type as ref. 171 (D)"),
 ("166", "idea 8, Case 8a: W in pores of aspect ratio 1750 with the largest exposure in the tables (D)"),
 ("187", "idea 8, Case 8d: ZnO with ozone in pores (D), the ozone partner of the ref. 65 ZnO rows"),
 ("181", "idea 8: Fe2O3 with ozone in an aerogel (D)"),
 ("184", "idea 8: Co3O4 with ozone in pores (D)"),
 ("107", "idea 8: SnOx in porous silicon (D)"),
 ("94", "idea 8: Ru on pillars (D)"),
 ("203", "idea 8, Case 8c: plasma SiO2 in holes of aspect ratio 50 (D), no coated value in the table"),
 ("139", "Case 8a: TMA/H2O hole row with an exposure"),
 ("99", "Case 8a: TMA/H2O row with an exposure and no coated value"),
 ("85", "Case 8a, 8f: WN in a capillary with exposure; coated 210 of 1000 without the PD50% mark"),
 ("78", "Case 8e: zirconium and hafnium amide rows and a microbalance sticking value"),
 ("236", "Case 8e: TiCl4, H and N sticking values by microbalance"),
 ("235", "Case 8e: TMA and water sticking by Auger spectroscopy"),
 ("220", "Case 8e: Co precursor sticking, and a plasma row with exposure"),
 ("252", "Case 8c: O on silica, the value used for SiO2 in the join"),
 ("259", "Case 8c: source of six H-atom values, among them nickel and copper"),
 ("241", "Case 8c: ozone recombination on ALD surfaces (Table VI)"),
 ("10.1016/j.apsadv.2021.100102", "Cases 1, 3, 7: lateral-channel profile by X-ray microanalysis, a second method on the same structure type"),
 ("10.1021/am505107s", "candidate A5: alumina on millimetre-tall nanotube forests"),
 ("10.1021/la300045z", "candidate A10: in-situ porosimetry during ALD in mesopores"),
 ("10.1021/jp111314b", "candidate A10: in-situ X-ray fluorescence during ALD in mesopores"),
]
want = []
for key, why in WANT:
    r = BYREF.get(key) or next((x for x in MAN.values() if x["doi"].lower() == key.lower()), None)
    if r is None:
        print("wanted: no manifest row for", key); continue
    if r["pdf_status"] == "ok" or r["in_scope"] != "yes":
        print("wanted: skipped", key, r["pdf_status"], r["in_scope"]); continue
    want.append(dict(rank=len(want) + 1, ref=r["cremers_ref"] or "citing", doi=r["doi"], first_author=(r["authors"].split(";")[0].strip() or ""), year=r["year"], journal=r["journal"], why=why, pdf_status=r["pdf_status"], oa_status=r["oa_status"]))
wr("wanted_pdfs.csv", want)
print("source checks", dict(sc_cnt), "| new rows", len(NR), "| profile groups", len(PR), "fit", fit_yes, "marginal", fit_m, "| matched c rows", len(c_rows), "lower bounds", sum(1 for r in c_rows if r["basis"] != "PD50"))
print("growth types", dict(gt), "| D refs", len(g_rows), "| wanted", len(want), "| unmarked", len(unmarked), "| PD50 equal", len(pd_eq))
