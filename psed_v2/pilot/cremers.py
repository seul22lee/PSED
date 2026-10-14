#!/usr/bin/env python3
"""Cremers 2019 (Appl. Phys. Rev. 6, 021302) read as data, for Case 8 of the cases view.

    python3 psed_v2/pilot/cremers.py

Part 1 (transcribe): Tables II-VII typed in by hand and checked against the page images -> cremers_conformality.csv and
cremers_parameters.csv. Every value is data_kind cited; blank cells stay blank; footnote markers go to `note`, never into a number.
Row format, conformality: table | film | precursor/coreactant | plasma_config | structure | EAR | T_C | exposure (10^3 L) | method | coated EAR as printed | ref | note
Row format, parameters:   table | species | surface or material | method | T_C | value as printed | ref | note
Part 2 (analysis): reads those two CSVs and the hand-checked lists below; writes cremers_source_checks.csv, cremers_new_rows.csv,
cremers_profiles.csv, cremers_values_hand_obtained.csv and cremers_wanted_pdfs.csv, and builds the SVG plots (pa, pc, pr, ps)
that cases.py shows in Case 8 (cases.py loads this file with runpy, which skips part 1). The findings and ideas are in HANDOFF.md.
"""
import csv, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent

C = """
II|Al2O3|TMA/H2O||Macro lateral|100|200|9|SE|50* (D)|67|
II|Al2O3|TMA/H2O||Trench|5|300||SEM|5|134|
II|Al2O3|TMA/H2O||AAO|8.5|200|300|SEM/TEM|8.5|135|
II|Al2O3|TMA/H2O||Nanorods (ZnO)||300|560|TEM|Conformal|99|substrate footnote 136
II|Al2O3|TMA/H2O||Pillars (Si)||125||TEM|Conformal|93|substrate footnote 137
II|Al2O3|TMA/H2O||AAO|1750|177||SEM/TEM|1750|96|
II|Al2O3|TMA/H2O||AAO|770|177|4500|SEM|770|65|
II|Al2O3|TMA/H2O||LHAR|10-12500|300||Reflectometry, optical/IR microscopy, SEM|75* (D)|86|
II|Al2O3|TMA/H2O||LHAR|10-12500|300||Reflectometry|130* (D)|77|
II|Al2O3|TMA/H2O||Trench|11|||SEM|11|138|
II|Al2O3|TMA/H2O||Macro lateral|5|75|18|SEM/EDX|2.5* (D)|69|
II|Al2O3|TMA/H2O||Hole|17|200|370|SEM|17|139|
II|TiO2|TiCl4/H2O||Pillars (Si)||110||TEM|Conformal|93|substrate footnote 137
II|TiO2|TiCl4/H2O||AAO|7.5|200||SEM/TEM|7.5|140|
II|TiO2|TiCl4/H2O||LHAR|10-12500|110||Reflectometry IR microscopy|90* (D)|77|
II|TiO2|TiCl4/H2O||LHAR|10-12500|110||Reflectometry|65* (D)|86|
II|TiO2|TiCl4/H2O||AAO|7000|100||SEM/TEM/EDAX|7000|96|
II|TiO2|TiCl4/H2O||Opal||70||FE-SEM|Conformal|101|
II|TiO2|TiCl4/H2O||Opal||80||SEM||141|
II|TiO2|TTIP/H2O||VACNT||225||SEM|(D)|100|substrate footnote 142
II|V2O5|VOTP/H2O2||AAO|7000|100||SEM/TEM/EDAX|7000|96|
II|Fe2O3|Fe2(OtBu)6/H2O||AAO|100|140||SEM/TEM|100|143|
II|Fe3O4|Fe(Cp)2/O2||AAO||400||SEM/TEM||144|
II|ZnO|DEZ/H2O||AAO|700|177|2000|EPMA|700 (D)|65|
II|ZnO|DEZ/H2O||AAO|5000|177|600000|EPMA|5000 (D)|65|exposure printed as 6 00 000
II|ZnO|DEZ/H2O||Opal||85||SEM||102|
II|ZnO|DEZ/H2O||Trench|3|250||SEM|3|90|
II|ZnO|DEZ/H2O||Nanowire (CuO)||150||SEM/TEM|Conformal|146|substrate footnote 145
II|Y2O3|(CpCH3)3Y/H2O||Trench|35|300|50000|TEM|15*|89|
II|ZrO|Zr(NMe2)4/H2O||Elliptical holes|36||6|SEM|36|78|film printed as ZrO
II|ZrO|Zr(NEtMe)4/H2O||Elliptical holes|36||6|SEM|36|78|film printed as ZrO
II|ZrO|Zr(NEt2)4/H2O||Elliptical holes|36||6|SEM|36|78|film printed as ZrO
II|RuO2|Ru(od)3/O2||CNT||300||SEM/TEM|Conformal|148|substrate footnote 147
II|SnOx|SnCl4/H2O||Porous silicon|140|500||TEM/SIMS|140 (D)|107|
II|HfO2|HfCl4/H2O||Trench|35|300|2000|TEM|22*|89|
II|HfO2|Hf(NMe2)4/H2O||Holes|36|150|9|SEM|36|62|
II|HfO2|Hf(NMe2)4/H2O||Elliptical holes|36||6|SEM|36|78|
II|HfO2|Hf(NEtMe)4/H2O||Elliptical holes|36||6|SEM|36|78|
II|HfO2|Hf(NEt2)4/H2O||Elliptical holes|36||6|SEM|36|78|
II|BN|BBr3/NH3||AAO|10000|750||SEM|20|149|
II|AlN|TMA/NH3||Trench|17.5|420||SEM|17.5|150|
II|TiN|TiCl4/Zn/NH3||Trench|5|500||SEM|5|134|
II|TaN|TBTDET/NH3||Trench|11|||SEM|11|138|
II|WN|(tBuN)2(Me2N)2W/NH3||Silica capillary tube|1000|300|110|Optical microscopy|210|85|
II|Ru|(iPr-Me-Be)Ru(CHD)/O2||Hole|4.6|225, 270, and 310||TEM|4.6|151|
II|Ru|(iPr-Me-Be)Ru(CHD)/O2||Hole|25|270||TEM|25|151|coated EAR footnote 152
II|Ru|(iPr-Me-Be)Ru(CHD)/O2||Hole|24|220||XTEM|24|153|
II|Ru|(EtCp)Ru(DMPD)/O2||AAO|20|280||TEM|20|154|
II|Ru|(EtCp)Ru(DMPD)/O2||Hole|17|250||SEM|17|156|coated EAR footnote 155
II|Ru|(Et-Be)Ru(CHD)/O2||Trench|2.25|225||TEM|2.25|157|
II|Ru|(Et-Be)Ru(Et-CHD)/O2||Hole|32|225 and 270||XTEM|32|158|
II|Ru|Ru(Me-Me2-CHD)2/O2||AAO|166|300||TEM|100|159|
II|Ru|(EtCp)Ru(Py)/O2||Hole|20|275||SEM|20*|160|
II|Ru|(EtCp)Ru(Py)/O2||Trench|11|||SEM|11|138|
II|Ru|Ru(EtCp)2/O2||Trench|4|270||SEM|4|161|
II|Ru|Ru(EtCp)2/O2||AAO|10|300||SEM/TEM|10|162|
II|Ru|RuO4/H2||Pillars (Si)|10|100||SEM/EDX|Conformal (D)|94|substrate footnote 163
II|Pd|Pd(hfac)2/formalin||AAO|1500|200||SEM/EDX electrical conductivity|1500|164|
II|W|Si2H6/WF6||AAO|1750|200|6000000|SEM/EDX|1750 (D)|166|exposure printed as 60 00 000 with footnote 165
II|Ir|Ir(acac)3/O2/H2||LHAR|10-12500|250||EDX optical microscopy|20* (D)|87|
II|Ir|Ir(acac)3/O2||LHAR|10-12500|250||EDX optical microscopy|15* (D)|87|
II|Ir|Ir(acac)3/O2||Hole|142|300|||Ref. 167|168|
II|Ir|Ir(acac)3/O2||Trench||370||SEM||169|
II|Pt|MeCpPtMe3/O2||AAO|8.5|250|405|SEM/TEM|8.5|135|
II|Pt|MeCpPtMe3/O2||AAO|150|250||SEM/EDX/SANS|110* (D)|171|coated EAR footnote 170
II|Pt|MeCpPtMe3/O2||AAO|200|300||SEM|94|172|
II|Pt|MeCpPtMe3/O2||Trench|6|300||TEM|6|79|
II|Pt|MeCpPtMe3/O2||AAO|200|300||SEM/TEM|50|173|
II|Pt|MeCpPtMe3/O2||Hole|90|300||SEM/TEM|30|173|
II|PtIr alloy|MeCpPtMe3/O2/Ir(acac)3/O2||AAO|7.1|300||SEM|7.1|172|
II|PtIr alloy|MeCpPtMe3/O2/Ir(acac)3/O2||Trench|9.5|300||SEM|9.5|174|
III|Al2O3|TMA/O3||Trench|||||Ref. 175|176|the running text gives 20:1 for this process, citing 176
III|SiO2|[H2N(CH2)3Si(OCH2CH3)3]/H2O/O3||AAO|400|||SEM/TEM|400|177|
III|TiO2|TDMAT/O3||Hole|20|180||TEM|20* (D)|178|
III|TiO2|TDMAT/O3||CNT||100|4500|TEM/SEM/EDX||98|substrate footnote 179
III|TiO2|Cp*Ti(OMe)3/O3||Hole|15.3|270||SEM/TEM|(D)|180|
III|V2O5|VOTP/O3||AAO|100|||SEM/EDX|100|150|the running text cites 78 for this value
III|V2O5|VOTP/O3||AAO|185|170||SEM/TEM|44|159|
III|Fe2O3|Fe(Cp)2/O3||Trench|2|250||SEM|2|181|
III|Fe2O3|Fe(Cp)2/O3||Silica aerogel|150|250||SEM/EDX|150 (D)|181|
III|Fe2O3|CpFeC5H4CHN(CH3)2/O3||Nanowire (TiO2)||230||TEM/EDX|Conformal|182|
III|Co3O4|CoCp2/O3||Anodisc|375|167||SEM/EDX|375 (D)|184|substrate footnote 183
III|NiO|Ni(CpEt)2/O3||AAO|70|250||TEM/SEM/EDX|70|185|
III|NiO|NiCp2/O3||AAO|238|300||TEM/SEM|238|186|
III|ZnO|DEZ/O3||AAO|250|50||SEM/EDX|250 (D)|187|
III|ZnO|DEZ/O3||Hole|2|85||SEM|2|189|substrate footnote 188
III|HfO2|TEMAHf/O3||Hole|15.3|180||SEM/TEM|9.6* (D)|180|
III|IrO2|Ir(acac)3/O3||LHAR|10-12500|185||EDX optical microscopy|15* (D)|87|method footnote 190
III|PtOx|Pt(acac)2/O3||Trench|3.5|120||FE-SEM|3.5|191|
III|PtOx|MeCpPtMe3/O3||Trench|5|120||SEM|5|192|
III|Ru|Ru(EtCp)2/O3||Hole|16|275||TEM|16|194|coated EAR footnote 193
III|Ir|Ir(acac)3/O3/H2||LHAR|10-12500|185||EDX optical microscopy|45* (D)|87|
III|Ir|Ir(acac)3/O3/H2||Trench||165||FE-SEM||192|
III|Pt|MeCpPtMe3/O3||AAO|150|150||SEM/EDX|35* (D)|195|
III|Pt|Pt(acac)2/O3||AAO|120|150||SEM|50|196|
IV|Al2O3|TMA/O2*|RI|Macro lateral|10|200|27|SE|10 (D)|70|
IV|Al2O3|TMA/O2*|RI|Hole|8|200||SEM|8|197|
IV|Al2O3|TMA/O2*|RC|Trench|13.5|250||SEM|13.5|198|
IV|Al2O3|TMA/O2*|RI|Macro lateral|5|75|5|EDX|0.75* (D)|69|substrate footnote 199
IV|Al2O3|TMA/O2*||Hole|10|225|30|FE-SEM|10|200|
IV|Al2O3|TMA/O2*|C|Trench|2|250||TEM|2|201|
IV|Al2O3|TMA/O2*|R|Trench|15|||SEM|15*|202|
IV|SiO2|3DMAS/O2*|RC|Trench|30|250||SEM|30|198|
IV|SiO2|H2Si[N(C2H5)2]2/O2*|R|Trench|15|||SEM|15|202|
IV|SiO2|H2Si[N(C2H5)2]2/O2*||Hole|50|75||TEM|(D)|203|
IV|TiO2|TTIP/O2*|RC|Trench|13.5|150||SEM|13.5|198|
IV|TiO2|TTIP/O2*||Hole|8.7|225||TEM|8.7 (D)|204|
IV|Ti|TiCl4/O2*|RI|Trench|4.5|200|75|FE-SEM/FEI|4.5|205|film printed as Ti, in the oxides block
IV|HfO2|TEMAHf/O2*|RC|Trench|30|250||SEM|30|198|
IV|Ta2O5|Ta(OEt)5/O*|RE|Trench|2.5|150-250||SEM|2.5|206|
IV|Ta2O5|Ta(OEt)5/O*|RE|Trench|5|150-250||SEM|5|206|
IV|Ta2O5|Ta(OEt)5/O2*|RC|Trench|10|200||SEM|10|198|
IV|AlN|TMA/NH3*|RI|Macro lateral|10|200|40|SE|2.5* (D)|70|exposure footnote 207
IV|SiNx|Si2Cl6/NH3*|C|Trench|2.5|400||TEM|2.5|208|
IV|SiNx|DTDN2-H2/N2*||Trench|2.75|300||TEM|Ref. 209|81|
IV|TiN|TDMAT/NH3*|R|Hole|10|250||FE-SEM/AES|10|210|
IV|TiN|TDMAT/NH3/H2*|C|Trench|10|180||FE-SEM|10|80|
IV|TiN|TDMAT/H2*|R|Hole|10|250||FE-SEM/AES|10|210|
IV|TiN|TDMAT/N2*|R|Hole|10|250||FE-SEM/AES|10|210|
IV|TiN|TDMAT/N2*||AAO|14|200||FE-SEM|14|211|
IV|TiN|TiCl4/H2*+N2*|C|Hole|6|350||SEM|6|201|
IV|TiN|TiCl4/H2*+N2*|R|Nanotube (TiO2)||200||FE-SEM||212|
IV|TiN|TiCl4/H2*+N2*|RI|Trench|10.5|400||SEM|10.5|213|
IV|Mo2N|Mo(NtBu)2(StBu)2/H2*||Nanotrench|2.25|300||XTEM|Ref. 214|215|
IV|TaN|TBTDET/H2*|C|Hole|10|260||SEM|10|216|
IV|TaN|TBTDET/H2*||Trench|2|||TEM|2|97|
IV|TaN|TBTEMAT/H2*||Hole|7|250|||7|217|
IV|TaNx|PDMAT/H2*||Trench|5|250||TEM|5|218|
IV|Co|(C5H5)2Co/NH3*|HW|Trench|5.5|300|20|FE-SEM|5.5|220|coated EAR footnote 219; HW is not among the configurations the caption defines
IV|Ni|Ni(Cp)2/H2O/H2*|C|Hole (TaN)|3.3|165||SEM|3.3|221|
IV|Cu|Cu(acac)2/H2*|C|Trench (SiO2)|1.75|85||SEM|1.75|222|
IV|Cu|Cu(acac)2/H2*|||2.5|85|||2.5|222|structure, configuration and method cells empty (continuation row)
IV|Cu|Cu(acac)2/H2*|||4.5|85|||4.5|222|structure, configuration and method cells empty (continuation row)
IV|Ru|Ru(EtCp)2/NH3*||Trench Si,Si/TaN|2|290||TEM|2|97|coated EAR footnote 223
IV|Ag|Ag(fod)(PEt3)/H2*|RC|Trench (SiO2/TiN)|30|120||FE-SEM|5|198|coated EAR footnote 224
IV|Ag|(Ag(O2CtBu)(PEt3))/H*|RE|Trench|4.5|140||SEM|4.5|225|
IV|Ir|Ir(acac)3/O2*|I|Hole (elongated)||370||SEM||226|
IV|Ir|Ir(acac)3/O2*||Trench||370||SEM||169|
IV|Pt|MeCpPtMe3/O2*|I|Trench|17|300||SEM|17 (D)|228|process footnote 227
IV|Ta|TaCl5/H2*|I|Trench|3|250||SEM|3|229|
"""

P = """
V|Al(CH3)3|Al2O3|Monte Carlo model|177|0.001|65|
V|Al(CH3)3|Al2O3|Ballistic model|225|0.026|200|
V|Al(CH3)3|Al2O3|Semi-Analytical model|200|0.1|67|
V|Al(CH3)3|Al2O3|DFT||0.1-0.9|176|
V|Al(CH3)3|Al2O3|Continuum model|300|0.00572|77|
V|Al(CH3)3|Al2O3|Monte Carlo model|200|0.02|128|
V|Al(CH3)3|Al2O3|Sum-frequency generation|100-300|0.002-0.005|237|
V|Al(CH3)3|Al2O3|Auger electron spectroscopy|25|0.01|235|
V|Hf(NEtMe)4|HfO2|Monte Carlo model|180-270|0.03-0.6|180|
V|Ti(NMe2)4|TiO2|Monte Carlo model|180|0.02 ± 0.005|178|
V|Ti(OiPr)4|TiO2|Ballistic model|125-225|0.04-0.1|204|
V|Cp*Ti(OMe)3|TiO2|Monte Carlo model|270|0.01|180|
V|TiCl4|TiN|QCM|25-125|0.006 ± 0.002|236|
V|TiCl4|TiN|Continuum model|110|0.1|77|deposited material cell empty on this line; TiN carries over from the line above, the source deposits TiO2
V|ZnEt2|ZnO|Monte Carlo model|177|0.007|65|
V|SiCl4|SiO2|Monte Carlo model||10^-8|65 and 239|
V|H2Si[N(C2H5)2]2|SiO2|Monte Carlo model|300|3 × 10^-5|128|
V|Zr(NMe2)4|ZrO|QCM|200|0.07|78|
V|Co(C5H5)2|Co|Monte Carlo model|300|0.002|220|
V|H2O|Al2O3|DFT||0.01-0.1|176|
V|H2O|Al2O3|Sum-frequency generation|100|0.000001|238|
V|H2O|Al2O3|Sum-frequency generation|300|0.0001|238|
V|H2O|Al2O3|Auger electron spectroscopy|25|0.25; 0.009|235|value footnote 240; two values
V|O3|Al2O3|DFT||0.001-0.01|176|
V|O*|Al2O3|DFT||0.1-0.9|176|
V|H*|TiN|QCM|25-125|0.0003 ± 0.0001|236|
V|N*|TiN|QCM|25-125|0.01 ± 0.002|236|
VI|O3|Al2O3|transmission through capillaries (table reprinted from Knoops 2011)|100-200|<10^-6|241|reference is the one named in the caption
VI|O3|ZnO|transmission through capillaries (table reprinted from Knoops 2011)|100|<10^-6|241|
VI|O3|ZnO|transmission through capillaries (table reprinted from Knoops 2011)|150|(5 ± 2) × 10^-5|241|
VI|O3|ZnO|transmission through capillaries (table reprinted from Knoops 2011)|200|>10^-3|241|
VI|O3|Pt|transmission through capillaries (table reprinted from Knoops 2011)|100|>10^-3|241|
VI|O3|MnOx|transmission through capillaries (table reprinted from Knoops 2011)|100|>10^-3|241|
VII|O|Alumina|||0.0021|250|
VII|O|Alumina|||0.0097 ± 0.0019|251|
VII|O|Silica|||0.0004|252|
VII|O|Titania|||0.014 ± 0.003|251|
VII|O|Iron(III)oxide|||0.0052|250|
VII|O|Iron(II, III)oxide|||0.015 ± 0.003|251|
VII|O|Cobalt oxide|||0.0049|250|
VII|O|Cobalt oxide|||0.029 ± 0.006|251|
VII|O|Oxidized cobalt|||0.085 ± 0.005|253|
VII|O|Nickel oxide|||0.0089|250|
VII|O|Oxidized nickel|||0.27 ± 0.04|254|
VII|O|Copper (II) oxide|||0.043|250|
VII|O|Oxidized copper|||0.225|253|
VII|O|Zinc oxide|||0.00044|250|
VII|O|Pyrex|||0.000045|250|the running text quotes 0.000094 for O on Pyrex
VII|O|Pyrex|||0.0020 ± 0.0005|255|
VII|O|Stainless steel|||0.0702 ± 0.009|256|printed as 0.0702± 0.009
VII|N|Aluminum|||0.0018|257|
VII|N|Silicon|||0.0016|257|
VII|N|Silica|||0.00021 ± 0.00003|258|
VII|N|Stainless steel|||0.0063|257|
VII|H|Aluminum|||0.29|259|
VII|H|Oxidized aluminum|||0.0018 ± 0.0003|260|
VII|H|Oxidized aluminum|||0.0017 ± 0.0002|261|
VII|H|Silicon|||0.8|262|
VII|H|Silicon|||0.66|263|
VII|H|Oxidized silicon|||0.0030 ± 0.0003|260|
VII|H|Titanium|||0.35|259|
VII|H|Nickel|||0.25|259|
VII|H|Nickel|||0.18 ± 0.03|260|
VII|H|Copper|||0.14|259|
VII|H|Pyrex|||0.0058 ± 0.0018|259|
VII|H|Pyrex|||0.00094 ± 0.0004|261|
VII|H|Stainless steel|||0.030 ± 0.014|260|
VII|H|Oxidized stainless steel|||0.0022 ± 0.0002|261|
"""


def refs():
    out = {}
    with (V2 / "corpus/manifest.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for n in re.split(r"[;,]", r["cremers_ref"]):
                if n.strip():
                    out[n.strip()] = r
    return out


# Cells the review leaves blank (exposure, EAR, coated EAR), looked up in the source paper. Key: (table, ref, film, structure, EAR, T_C).
# The transcribed cells are never changed; "not stated" means the source was read and does not give the value.
FILL = {
 ("II", "86", "Al2O3", "LHAR", "10-12500", "300"): "exposure: not stated (0.1 s pulses, reactor at 1 to 2 mbar, no partial pressure; Sec. II). EAR of the sample: 1000, from a 500 nm gap and 1000 um length class (Fig. 1 table); coated: half thickness near 70 um, i.e. 70 (Fig. 5a, by eye)",
 ("II", "86", "TiO2", "LHAR", "10-12500", "110"): "exposure: not stated (Sec. II). Coated: 50% of the entrance value at aspect ratio 130, i.e. 65, stated in the text to Fig. 5b",
 ("III", "178", "TiO2", "Hole", "20", "180"): "exposure: not stated (source at about 1 mbar vapour pressure, pulse 0.5 to 3 s; Sec. 3). EAR from the stated dimensions (130 nm x 2 um): 15.4; the source itself writes AR = 20 (Sec. 2)",
 ("III", "180", "TiO2", "Hole", "15.3", "270"): "exposure: not stated (Sec. 3). Coated EAR: no half-thickness depth; 12 of 13.5 nm left at 1250 nm, so above 9.6 (Fig. 3)",
 ("III", "180", "HfO2", "Hole", "15.3", "180"): "exposure: not stated (pulse 1 s, process pressure 1 mbar; Sec. 3)",
 ("IV", "204", "TiO2", "Hole", "8.7", "225"): "exposure: about 1.8 (10^3 L) for the 5 s case, computed here from the fitted flux of 3.3e20 m-2 s-1 (Table II), i.e. 0.047 Pa; not printed by the source",
 ("IV", "228", "Pt", "Trench", "17", "300"): "exposure: not stated (3 s precursor pulse without carrier gas, 3 s O2 plasma at 7.5 mTorr; Sec. IV)",
 ("II", "65", "Al2O3", "AAO", "770", "177"): "all cells filled. From the source: coated already at 3 s, i.e. 450 (10^3 L), not at 1 s (150) (Fig. 3); the pores are open at both ends, so the diffusion length is half of 50 um",
 ("II", "67", "Al2O3", "Macro lateral", "100", "200"): "all cells filled. From the source: at the same exposure, aspect ratio 33 fully coated, 50 coated to about 47 and 100 to about 53 (Fig. 5, by eye)",
 ("IV", "69", "Al2O3", "Macro lateral", "5", "75"): "all cells filled. From the source: half of the entrance signal at about 3 mm of a 10 mm wide hole, i.e. about 0.3 (Fig. 10, by eye)",
 ("IV", "70", "Al2O3", "Macro lateral", "10", "200"): "all cells filled. From the source: 0.3 Pa for 9 s is 20 (10^3 L), for 18 s it is 40 (Experimental; Fig. 3 table)",
}


def num(s):
    try:
        return float(s)
    except ValueError:
        return None


def transcribe():
    R = refs()
    have = {r["paper_id"] for r in R.values() if r["pdf_status"] == "ok" and r["in_scope"] == "yes"}   # in_corpus = in scope with a PDF
    def scope(ref):
        rs = [R[n] for n in re.findall(r"\d+", ref) if n in R]
        return "out of scope, cited source" if rs and all(r["in_scope"] != "yes" for r in rs) else ""
    def link(ref):
        ds, inn = [], "no"
        for n in re.findall(r"\d+", ref):
            r = R.get(n)
            if r:
                ds.append(r["doi"]); inn = "yes" if r["paper_id"] in have else inn
        return "; ".join(ds), inn
    rows = []
    for line in C.strip().splitlines():
        t, film, proc, cfg, struct, ear, T, expo, meth, coated, ref, note = [x.strip() for x in line.split("|")]
        prec, _, co = proc.partition("/")
        m = re.match(r"[\d.]+", coated); val = m.group() if m else ""
        e = num(ear)
        if "*" in coated: basis = "PD50"
        elif coated.startswith("Conformal"): basis = "conformal"
        elif val and e is not None and float(val) == e: basis = "complete"
        else:
            basis = ""
            if val and e is not None and float(val) < e: note = (note + "; " if note else "") + "coated EAR below the structure EAR but not marked as PD50%"
            elif coated.startswith("Ref"): note = (note + "; " if note else "") + "coated EAR cell points to another reference"
        doi, inn = link(ref)
        rows.append(dict(table=t, film=film, precursor=prec, coreactant=co, plasma_config=cfg, structure=struct, EAR=ear, T_C=T, exposure_printed=expo, method=meth, coated_ear_printed=coated,
                         coated_ear_value=val, coated_ear_basis=basis, profile="D" if "(D)" in coated else "", ref=ref, doi=doi, in_corpus=inn, source_scope=scope(ref),
                         value_from_source=FILL.get((t, ref, film, struct, ear, T), ""), note=note))
    with (HERE / "cremers_conformality.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    prm = []
    for line in P.strip().splitlines():
        t, sp, surf, meth, T, v, ref, note = [x.strip() for x in line.split("|")]
        x = v.replace("×", "*").replace(" ", "")
        lo = hi = ""
        try:
            if "±" in v:
                m = re.match(r"\(?([\d.]+)±([\d.]+)\)?(?:\*10\^(-?\d+))?", x); k = 10 ** int(m.group(3) or 0)
                lo, hi = (float(m.group(1)) - float(m.group(2))) * k, (float(m.group(1)) + float(m.group(2))) * k
            elif v.startswith("<"): hi = float(x[1:].replace("10^", "1e"))
            elif v.startswith(">"): lo = float(x[1:].replace("10^", "1e"))
            elif ";" in v: a = sorted(float(q) for q in v.split(";")); lo, hi = a[0], a[-1]
            elif re.fullmatch(r"[\d.]+-[\d.]+", v): lo, hi = map(float, v.split("-"))
            else: lo = hi = float(x.replace("*10^", "e").replace("10^", "1e"))
        except Exception:
            pass
        doi, inn = link(ref)
        prm.append(dict(table=t, species=sp, surface_or_material=surf, method=meth, T_C=T, value_printed=v, value_low=f"{lo:.3g}" if lo != "" else "", value_high=f"{hi:.3g}" if hi != "" else "", ref=ref, doi=doi, in_corpus=inn, source_scope=scope(ref), note=note))
    with (HERE / "cremers_parameters.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(prm[0])); w.writeheader(); w.writerows(prm)
    import collections
    print("conformality rows", dict(collections.Counter(r["table"] for r in rows)), "| in_corpus", sum(r["in_corpus"] == "yes" for r in rows))
    print("parameters rows", dict(collections.Counter(r["table"] for r in prm)), "| in_corpus", sum(r["in_corpus"] == "yes" for r in prm))
    print("value_from_source rows:", sum(1 for r in rows if r["value_from_source"]))
    print("basis", {t: dict(collections.Counter(r["coated_ear_basis"] or "blank" for r in rows if r["table"] == t)) for t in ("II", "III", "IV")})


if __name__ == "__main__":
    transcribe()

# ============================================================================= part 2: analysis
import html, math, collections
E = html.escape
rd = lambda p: list(csv.DictReader(open(p, newline="", encoding="utf-8")))
CONF, PAR = rd(HERE / "cremers_conformality.csv"), rd(HERE / "cremers_parameters.csv")
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
# the eight in-corpus papers the review cites outside Tables II-VII (text, captions, Table VIII), checked on 2026-10-14
SC_CITED = [
 ('text', 'text', '50', '10.1016_j.ijpharm.2017.04.031', 'not in a table', 'abstract, experimental section', 'Sec. I lists pharmaceuticals among uses of ALD on 3D substrates; agree: the source coats acetaminophen drug powder with oxide films (TMA, TiCl4 or TTIP with water) in a rotary reactor near 100 °C; it reports no conformality figure, so nothing is tabulated'),
 ('VIII', 'Knoops, Monte Carlo, molecular flow, s,r constant, cosine re-emission, 2D, trench, simulate PE-ALD, recombination limited growth type', '66', '10.1149_1.3491381', 'agree', 'Monte Carlo Simulations section, Fig. 1, Figs. 8-9', "2D trench, particles one at a time (high Knudsen number), one reaction probability s and one loss probability r held constant, cosine-distributed emission and re-emission, three regimes with the recombination-limited one new; the 's,r constant' cell carries ref 291 rather than 66; the row leaves out that the change of AR during growth is neglected"),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section', 'Sec. II E, kinetics simplified to irreversible Langmuir adsorption [65-67]; agree: each surface interval reacts once with a fixed probability s, no desorption'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'section on recombination loss probability, Table II', 'Sec. II E, recombination probability r as the chance that a species recombines per wall collision [66,69,70]; agree: the source calls it the loss probability r, after which the species no longer contributes to growth'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'deposition regimes paragraph, Fig. 8', 'Sec. II F and Fig. 4 (adapted from this paper): Knoops et al. introduced a recombination limited growth type, saturation set by radical loss on the side walls; agree: the source names it as new, growth everywhere with a rate falling toward the bottom; Fig. 4 matches the three sketches of Fig. 8'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section', 'Sec. V A 2c, listed among Monte Carlo models; agree'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section, Fig. 1a', 'Sec. V B 1, feature scale only, no reactor-scale transport [51,62,66,275]; agree: particles start at the trench entrance and nothing outside it is modelled'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section', 'Sec. V C 1, molecular flow assumed by the Monte Carlo models; agree: feature small against the mean free path, no particle-particle interaction'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section', "Sec. V C 3, 'other models use a 2D structure'; agree: a fully 2D trench, chosen for speed"),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section, Fig. 1b', 'Sec. V C 5, cosine re-emission used in ALD models; agree: reflected particles leave in a cosine-distributed direction'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Monte Carlo Simulations section', 'Sec. V C 6, only one ALD reaction simulated, the profile read as a multi-cycle thickness; agree: one half-reaction at a time with the other assumed saturated, valid while the film is thin against the trench width'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Fig. 3', "Sec. V D 2 and Fig. 18(a), trench of EAR 50:1 simulated by Monte Carlo (reprinted from this paper); agree: the only AR-100 profile in the source is Fig. 3 (s = 1 and 0.05, r = 0), and depth/width 100 is EAR 50 by the review's L/(2w) for trenches; the reprinted panel itself was not compared"),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'particle diffusion section, Fig. 7', 'Sec. V D 3, models giving the pressure profile in the structure [66,114]; agree in substance: the source gives the wall-collision count along the depth (the particle distribution), not a pressure'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'results with r > 0, Figs. 4-6', 'Sec. VI, the effect of recombination probability on the profile was discussed by Knoops et al.; agree'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Figs. 3 and 5, conclusion', 'Sec. VI B, profiles without an initial plateau at very low sticking, also seen by Knoops et al.; agree: unsaturated reaction-limited profiles are flat and lower s gives a shallower front'),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Fig. 2', "Sec. VI B 4 and Fig. 23, exposure against EAR for several s0, similar results by Knoops et al.; agree: saturation dose against AR for s 0.001-1, dose set by s at low AR and the curves merge at high AR (e.g. AR 100); the source's AR is depth/width of a trench, twice the EAR"),
 ('text', 'text', '66', '10.1149_1.3491381', 'not in a table', 'Fig. 3, Fig. 8 caption', 'Sec. VI B 5, faster coverage of the bottom of the feature seen in other Monte Carlo simulations [51,66]; differ: the source does not report it; its AR-100 profile (Fig. 3) has a low tail to the bottom with no rise, the Fig. 8 caption only says a small bottom growth from few-collision particles was left out of the sketch, and with recombination the bottom saturates last'),
 ('text', 'text', '115', '10.1039_c4nr05049e', 'not in a table', 'experimental section', 'Sec. III C, Dendooven et al. [106,115] used mesoporous SiO2 and TiO2 films on Si; agree for this source: an 80 nm mesoporous titania film spin-coated on Si; the silica film is from ref. 106'),
 ('text', 'text', '115', '10.1039_c4nr05049e', 'not in a table', 'results (electron tomography, EP), Fig. 4b, Table 1', 'Sec. III C, titania pores are ink-bottle shaped, spherical cages 4-7 nm joined by 3-5 nm necks; differ: the source finds ellipsoidal pores (axes about 3.8 and 7.1 nm, anisotropy 2) and necks of about 3 nm from the EP desorption branch; the 3-5 nm may come from ref. 106'),
 ('text', 'text', '115', '10.1039_c4nr05049e', 'not in a table', 'results, Figs. 5-8', 'Sec. III C, remaining porosity followed by in situ GISAXS; agree: critical angle (film density) and scattered intensity (internal surface area) tracked over 40 TDMAT/H2O cycles at 200 °C, both level off at 23-24 cycles, matching in situ XRF'),
 ('text', 'text', '115', '10.1039_c4nr05049e', 'not in a table', 'discussion', 'Sec. III C, pore size tuned to near molecular size, limited by the reactant size (TDMAT about 0.7 nm, cited to ref. 130); agree: 1.25 nm on each side of a 3 nm neck leaves 0.5 nm, below the TDMAT size of about 7 Å that the source also gives'),
 ('text', 'Fig. 8(i) caption', '115', '10.1039_c4nr05049e', 'not in a table', 'Fig. 2', 'Fig. 8(i), mesoporous titania film, credited to Dendooven et al., Nanoscale 6(24) (this paper); agree: the source shows tomography of that film; the panel image was not compared'),
 ('text', 'text', '122', '10.1021_acs.langmuir.6b03119', 'not in a table', 'introduction, experimental section, Figs. 1-4', "Sec. III A, anodic TiO2 nanotube layers, diameter 110 nm, EAR 180:1, tube layer on a QCM crystal for in situ uptake; agree: AR about 180 = 20 µm layer over the 110 nm inner diameter at the top (EAR = AR for tubes), free-standing tube layers glued onto QCM crystals; the tubes narrow with depth, so 110 nm is the top value; the source's Al2O3 TMA/H2O run (200 °C, 50 Pa, TMA 0.5-10 s, tubes coated to the bottom, thinner there at 0.5 and 2 s) is not in Table II"),
 ('text', 'text', '131', '10.1039_c7ta03257a', 'not in a table', 'methods, results, Fig. 1', 'Sec. III C, ALD infiltration in mesoporous Zeotile-4 powder [111,131], Fig. 8(j); agree: Pt from MeCpPtMe3/O3 at 200 °C with static 30 s exposures into Zeotile-4 (about 11 nm channels, particles 2-3 µm by 0.5-1 µm), giving a full replica, for catalysis (HER); the Fig. 8(j) image is credited to Sree et al., Chem. Mater. 24 (2012), not to this paper'),
 ('text', 'text', '232', '10.1021_acsnano.5b03429', 'not in a table', 'abstract, Fig. 5', 'Sec. IV A, one of few studies on conformality of sulfides [231,232]; agree: Co9S8 from Co(amd)2/H2S at 130 °C into NU-1000 MOF crystallites, EDS line scan uniform in Co and S across a crystallite; no depth profile or aspect ratio given, and no sulfide row appears in Tables II-IV'),
 ('text', 'text', '248', '10.1063_1.2338776', 'not in a table', 'abstract, introduction', 'Sec. IV C, lower deposition temperature of PE-ALD useful for polymers [248,249]; agree: plasma Al2O3 (TMA/O2 plasma) from room temperature to 100 °C on PEN as a moisture barrier, room temperature giving the best WVTR'),
 ('VIII', 'Keuter, continuum, based on Yanguas-Gil model, second-order kinetics, 1D, porous substrate, predict thickness profile', '294', '10.1116_1.4892385', 'agree', 'Sec. III A-B, Fig. 5', 'diffusion-reaction equations after Yanguas-Gil and Elam with second-order kinetics, showerhead-to-substrate transport left out, pores described by mean porosity, tortuosity, pore size and a Knudsen diffusion coefficient, only unshielded sites counted, 1D in depth, SOFC anode substrate; the row does not say that the profile was compared with ZrO2 (TEMAZ/O2, 200 °C) and that the reaction probability (2e-4) was fitted, a value not in Table V'),
]
SC2 = [  # added 2026-10-13 with the 15 PDFs obtained by hand
 ("II", "Al2O3 TMA/H2O, macro lateral, EAR 100, 200 °C, exposure 9, coated 50* (D)", "67", "10.1149_1.3072694", "agree", "experimental section, Fig. 5", "0.3 Pa for 4 s is 1.2 Pa s, i.e. 9.0 × 10^3 L; aspect ratio 100 by the source's perimeter definition; half thickness at about 10.7 of 20 mm (by eye) gives 53"),
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
 ("VII", "O on alumina, 0.0097 ± 0.0019 (out of scope, cited source)", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K, ± 20%, on a sintered ceramic in an air plasma at 110 Pa; 0.061 at 773 K"),
 ("VII", "O on titania, 0.014 ± 0.003 (out of scope, cited source)", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K; 0.031 at 773 K"),
 ("VII", "O on iron(II, III) oxide, 0.015 ± 0.003 (out of scope, cited source)", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "at 300 K"),
 ("VII", "O on cobalt oxide, 0.029 ± 0.006 (out of scope, cited source)", "251", "10.1016_j.cattod.2003.11.022", "agree", "Table 1", "CoO at 300 K"),
]
SC1, SC = SC, SC + SC2
wr("cremers_source_checks.csv", [dict(table=a, row=b, ref=c, paper_id=d, verdict=e, where=f, remark=g) for a, b, c, d, e, f, g in SC + SC_CITED])

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
wr("cremers_new_rows.csv", [dict(zip(NRF, r)) for r in NR])

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
wr("cremers_profiles.csv", [dict(zip(PRF, r)) for r in PR])

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
]
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
 (9, 47, "measured", "macro hole, aspect ratio 50, half thickness at about 19 of 20 mm (by eye)", "10.1149_1.3072694 Fig. 5"),
 (9, 53, "measured", "macro hole, aspect ratio 100, half thickness at about 10.7 mm (by eye)", "10.1149_1.3072694 Fig. 5"),
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
 ("Silica", (2e-5, 2.5e-4), "180 °C, 12 to 130 mTorr; falls with pressure", "10.1021_acs.jpcc.1c01505", "Fig. 5B"),
 ("Titania", (1e-5, 4e-5), "50 mTorr, 100 to 240 °C; upper limit at 240 °C", "10.1021_acs.jpcc.1c01505", "Fig. 5A"),
 ("Alumina", (9.7e-3, 6.1e-2), "out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature", "10.1016_j.cattod.2003.11.022", "Table 1"),
 ("Titania", (1.4e-2, 3.1e-2), "out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature", "10.1016_j.cattod.2003.11.022", "Table 1"),
 ("Silica", (4e-3, 9.3e-3), "out of scope, cited source: oxidized SiC, 110 Pa air plasma, 300 to 773 K", "10.1016_j.cattod.2003.11.022", "Table 1"),
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
fit_yes = sum(1 for r in PR if r[6].startswith("yes")); fit_m = sum(1 for r in PR if r[6] == "marginal")
gt = collections.Counter(r[7] for r in PR)

# ----------------------------------------------------------------------------- values read from the papers obtained by hand on 2026-10-13
# Where each value was read, whether the ingest checks now cover that unit, and whether it was compared with the page image.
V15 = [  # paper, value as used, where read, token in document.md (body) or table number, compared with the page image, correction
 ("10.1002_cvde.200390005", "holes 0.17 x 0.30 um, 7.3 um deep, aspect ratio 36 (43 after coating)", "body", "7.3", "no", ""),
 ("10.1002_cvde.200390005", "150 °C; minimum exposure 9 × 10^3 L; 30 × 10^3 L for full coverage", "body", "150", "no", ""),
 ("10.1021_cm0303080", "pores 65 nm x 50 um and 19 nm x 92 um; 177 °C", "body", "177", "no", ""),
 ("10.1021_cm0303080", "TMA at 0.15 Torr; exposure times 1, 3, 10, 30 s", "body", "0.15", "no", ""),
 ("10.1021_cm0303080", "DEZ at 0.068 Torr; 5 Torr for 120 s in the quasi-static run", "body", "0.068", "no", ""),
 ("10.1021_cm0303080", "both faces directly exposed; pores entered from both ends", "body", "both ends", "no", ""),
 ("10.1021_cm0303080", "middle of the membrane uncoated at 1 s, coated at 3 s", "figure 3", "", "yes", ""),
 ("10.1021_cm0303080", "sticking 1e-3 for TMA (quoted) and 7e-3 for DEZ", "body", "10^{-3}", "no", ""),
 ("10.1149_1.3072694", "TMA about 0.3 Pa, 4 s, 200 °C, 150 cycles; s0 = 0.1 chosen", "body", "0.35", "no", ""),
 ("10.1149_1.3072694", "half thickness: aspect ratio 50 at about 19 mm, 100 at about 10.7 mm", "figure 5", "", "yes", "corrected from 49 and 55 to 47 and 53"),
 ("10.1016_j.surfcoat.2012.02.038", "TMA 0.08 Pa, 75 °C, 500 cycles; S0 = 0.01", "body", "0.08", "no", ""),
 ("10.1016_j.surfcoat.2012.02.038", "Table 2 parameters (0.08 Pa, 8 s, S0 0.01)", "table", "2", "no", ""),
 ("10.1016_j.surfcoat.2012.02.038", "half values: thermal 2, 8, 30 s at about 15, 18, 27.5 mm; plasma at about 2.8 mm", "figures 5, 10", "", "yes", ""),
 ("10.1149_1.3301664", "spacers 3.9, 1.3, 0.5 mm; TMA about 0.2 Pa, reactant 0.3 Pa; 9 s; 200 °C", "body", "3.9", "no", ""),
 ("10.1149_1.3301664", "sticking inputs 0.1 (TMA, at 0.12 Pa) and 5% (water)", "body", "0.12", "no", ""),
 ("10.1149_1.3301664", "aspect ratio 22: thermal complete, plasma half at about 12.5 mm (about 14)", "figure 2", "", "yes", ""),
 ("10.1116_1.4903941", "gap 500 nm; film to 65 um; aspect ratio 130 at half the entrance value (TiO2)", "body", "130", "no", ""),
 ("10.1116_1.4903941", "Al2O3 half thickness near 70 um", "figure 5a", "", "yes", ""),
 ("10.1116_1.4971196", "TMA 0.02 (0.009 to 0.02); BDEAS 3e-5 (3 to 5e-5); 200 and 300 °C", "body", "0.02", "no", ""),
 ("10.1016_j.apsusc.2009.02.055", "holes 130 nm x 2 um, written as AR = 20; SC 0.02 ± 0.005; 180 °C", "body", "130", "no", ""),
 ("10.1016_j.apsusc.2009.02.055", "profile never below 70% of its top value", "figure 3", "", "yes", ""),
 ("10.1016_j.apsusc.2010.01.025", "SC 0.032, 0.15, 0.56 at 180, 230, 270 °C; Cp*Ti(OMe)3 0.006 to 0.018", "body", "0.56", "no", ""),
 ("10.1016_j.apsusc.2010.01.025", "HfO2 half thickness near 1250 nm at 180 °C", "figure 1a", "", "yes", ""),
 ("10.1063_1.2714685", "holes 0.3 um, aspect ratio 10; TMA 0.01 Torr; 225 °C; S(0) = 0.026", "body", "0.026", "no", ""),
 ("10.1149_1.2789802", "holes 0.15 um, aspect ratio 8.7; step coverage 52% at 500 cycles", "body", "8.7", "yes", "none: compared with the page image (p. H1010 and the conclusion on p. H1013); the same values stand in the abstract and conclusion"),
 ("10.1149_1.2789802", "S(0) 0.1 and 0.052; flux 3.282e20 m-2 s-1", "table", "II", "yes", ""),
 ("10.1063_1.4972120", "trench aspect ratio up to 34; conformality 92 ± 8%", "table", "II", "no", ""),
 ("10.1063_1.4972120", "O2 plasma 7.5 mTorr; r of O on Pt 0.01 (quoted)", "body", "7.5", "no", ""),
 ("10.1149_1.3491381", "r of O on silica 0.0002, alumina 0.0021 (a literature table)", "table", "II", "yes", ""),
 ("10.1021_acs.jpcc.1c01505", "r of SiO2 about 1e-4 to 3e-5 (temperature) and 2.5e-4 to 2e-5 (pressure); TiO2 about 4e-5, below 1e-5 at 240 °C", "figure 5", "", "yes", "corrected: upper pressure value from 2e-4 to 2.5e-4"),
 ("10.1021_acs.jpcc.1c01505", "half-thickness depths over cavity height", "figures 2-4", "", "yes", ""),
 ("10.1016_j.cattod.2003.11.022", "out of scope, cited source: γ of O on Al2O3 9.7e-3 (300 K) to 61e-3 (773 K), TiO2 14e-3 to 31e-3, SiC/SiO2 4e-3 to 9.3e-3", "table", "1", "yes", ""),
]


def v15_check(pid, where, tok):
    st = json.load(open(V2 / f"ingest/final/{pid}/structure.json"))
    if where == "table":
        t = next((c for c in st["captions"] if c["kind"] == "table" and str(c["number"]) == tok), None)
        return f"table check: {t.get('check', 'none') if t else 'table not found'}"
    if where != "body":
        return "not checked (figure)"
    doc = (V2 / f"ingest/final/{pid}/document.md").read_text(encoding="utf-8")
    if tok not in doc:
        return "body: token not found in document.md"
    hit = [f for f in st["body_flags"] if tok in (f.get("output_sentence") or "") + (f.get("layer_line") or "")]
    return "body check: covered, no flag" if not hit else "body check: flagged (" + "; ".join(sorted({f["kind"] for f in hit})) + ")"


import json
v15 = [dict(paper=p, value=v, where_read=w, check=v15_check(p, w, t), compared_with_page_image=c, correction=x) for p, v, w, t, c, x in V15]
wr("cremers_values_hand_obtained.csv", v15)
v15n = collections.Counter("checked" if r["check"].startswith(("body check: covered", "table check: ok")) else "compared" if r["compared_with_page_image"] == "yes" else "neither" for r in v15)

sc_cnt = collections.Counter(s[4] for s in SC); sc2 = collections.Counter(s[4] for s in SC2)

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
e.append(f'<text x="{X(11):.1f}" y="{Y(100):.1f}" class="tk" style="font-size:11.5px">ref. 67: 33, 47, 53</text><text x="{X(130):.1f}" y="{Y(560):.1f}" class="tk" style="font-size:11.5px" text-anchor="middle">ref. 65 at half length: between 150 and 450</text>')
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
            lo, hi = v if isinstance(v, tuple) else (v, v); rrows.append((f"{surf}: {pid}, {reg}", lo, hi, 2, True, (f"{lo:g} to {hi:g}" if hi != lo else f"{lo:g}") + (" · cited" if "cited" in reg and "ceramic" not in reg and "SiC" not in reg else " · measured" if "ceramic" in reg or "SiC" in reg else " · fit")))
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
wr("cremers_wanted_pdfs.csv", want)
print("values hand-obtained", dict(v15n), [ (r["paper"][-10:], r["check"]) for r in v15 if not r["check"].startswith(("body check: covered","table check: ok","not checked"))]); print("source checks", dict(sc_cnt), "| new rows", len(NR), "| profile groups", len(PR), "fit", fit_yes, "marginal", fit_m, "| matched c rows", len(c_rows), "lower bounds", sum(1 for r in c_rows if r["basis"] != "PD50"))
print("growth types", dict(gt), "| D refs", len(g_rows), "| wanted", len(want), "| unmarked", len(unmarked), "| PD50 equal", len(pd_eq))
