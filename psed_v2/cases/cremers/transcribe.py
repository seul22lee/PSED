#!/usr/bin/env python3
"""Exploration: Tables II-VII of Cremers 2019 (Appl. Phys. Rev. 6, 021302) typed in by hand and checked against the page images.

    python3 psed_v2/cases/cremers/transcribe.py      # writes conformality.csv and parameters.csv next to this file

Every value is data_kind cited. Blank cells of the review stay blank. Footnote markers go to `note`, never into a number.
Row format, conformality: table | film | precursor/coreactant | plasma_config | structure | EAR | T_C | exposure (10^3 L) | method | coated EAR as printed | ref | note
Row format, parameters:   table | species | surface or material | method | T_C | value as printed | ref | note
"""
import csv, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent.parent

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
 ("II", "67", "Al2O3", "Macro lateral", "100", "200"): "all cells filled. From the source: at the same exposure, aspect ratio 33 fully coated and 50 coated to about 49 (Fig. 5, by eye)",
 ("IV", "69", "Al2O3", "Macro lateral", "5", "75"): "all cells filled. From the source: half of the entrance signal at about 3 mm of a 10 mm wide hole, i.e. about 0.3 (Fig. 10, by eye)",
 ("IV", "70", "Al2O3", "Macro lateral", "10", "200"): "all cells filled. From the source: 0.3 Pa for 9 s is 20 (10^3 L), for 18 s it is 40 (Experimental; Fig. 3 table)",
}


def num(s):
    try:
        return float(s)
    except ValueError:
        return None


def main():
    R = refs()
    have = {r["paper_id"] for r in R.values() if r["pdf_status"] == "ok"}   # in_corpus = the paper has a PDF in corpus/raw
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
                         coated_ear_value=val, coated_ear_basis=basis, profile="D" if "(D)" in coated else "", ref=ref, doi=doi, in_corpus=inn,
                         value_from_source=FILL.get((t, ref, film, struct, ear, T), ""), note=note))
    with (HERE / "conformality.csv").open("w", newline="", encoding="utf-8") as f:
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
        prm.append(dict(table=t, species=sp, surface_or_material=surf, method=meth, T_C=T, value_printed=v, value_low=f"{lo:.3g}" if lo != "" else "", value_high=f"{hi:.3g}" if hi != "" else "", ref=ref, doi=doi, in_corpus=inn, note=note))
    with (HERE / "parameters.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(prm[0])); w.writeheader(); w.writerows(prm)
    import collections
    print("conformality rows", dict(collections.Counter(r["table"] for r in rows)), "| in_corpus", sum(r["in_corpus"] == "yes" for r in rows))
    print("parameters rows", dict(collections.Counter(r["table"] for r in prm)), "| in_corpus", sum(r["in_corpus"] == "yes" for r in prm))
    print("value_from_source rows:", sum(1 for r in rows if r["value_from_source"]))
    print("basis", {t: dict(collections.Counter(r["coated_ear_basis"] or "blank" for r in rows if r["table"] == t)) for t in ("II", "III", "IV")})


if __name__ == "__main__":
    main()
