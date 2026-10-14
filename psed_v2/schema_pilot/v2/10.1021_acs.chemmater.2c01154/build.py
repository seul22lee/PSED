#!/usr/bin/env python3
"""Fresh v2 extraction of 10.1021_acs.chemmater.2c01154 (key mat22): writes paper/sample/condition/series/value/coverage.csv.

Heat-map cells of Fig. 7b and Fig. 8 were read against the colour bars from the figure images (nearest colour-bar pixel in RGB,
then the bar's tick positions); see notes.md. Those readings are typed in GRID below; nothing is read at run time."""
import csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PID = "10.1021_acs.chemmater.2c01154"
K = "mat22"
ROOT = HERE.parents[2]  # psed_v2

COLS = {
    "paper": ["paper_id", "year", "topic"],
    "sample": ["sample_id", "paper_id", "kind", "label_as_printed", "parent_sample", "members", "material", "precursor", "coreactant",
               "process_mode", "reactor", "structure_class", "structure_dims", "width_kind", "note", "evidence"],
    "condition": ["condition_id", "sample_id", "kind", "quantity", "label_as_printed", "qualifiers", "value", "unit", "data_kind",
                  "applies_when", "note", "evidence"],
    "series": ["series_id", "sample_id", "kind", "figure", "panel", "method", "x_id", "x_qualifiers", "x_label", "y_id", "y_qualifiers",
               "y_label", "z_id", "z_label", "data_kind", "link_status", "points_source", "points", "reused_from", "note", "evidence"],
    "value": ["value_id", "sample_id", "from_series", "quantity", "label_as_printed", "qualifiers", "value", "value_min", "value_max",
              "censor", "unit", "data_kind", "method", "relation", "regime", "cited_ref", "note", "evidence"],
}
T = {t: [] for t in COLS}

MO = "Mo(NtBu)2(NMe2)2"
CO = "H2S/H2/Ar remote plasma"
PM = "PEALD (remote ICP)"
RE = "Oxford Instruments FlexAL"


def sid(x):
    return f"{K}:{x}"


def S(x, kind, ev, label="u", members=(), material="MoS2", precursor=MO, coreactant=CO, pm=PM, reactor=RE, note="", parent=""):
    T["sample"].append(dict(sample_id=sid(x), paper_id=PID, kind=kind, label_as_printed=label, parent_sample=parent,
                            members=";".join(sid(m) for m in members), material=material, precursor=precursor, coreactant=coreactant,
                            process_mode=pm, reactor=reactor, structure_class="planar", structure_dims="", width_kind="none",
                            note=note, evidence=ev))


def C(s, kind, q, value, unit, ev, label="", qual="", dk="stated", when="", note=""):
    cid = f"{K}:c{len(T['condition']) + 1:03d}"
    T["condition"].append(dict(condition_id=cid, sample_id=s if s == "*" else sid(s), kind=kind, quantity=q, label_as_printed=label,
                               qualifiers=qual, value=value, unit=unit, data_kind=dk, applies_when=when, note=note, evidence=ev))
    return cid


def SER(x, s, kind, fig, panel, method, ev, xid="", xl="", yid="", yl="", zid="", zl="", dk="measured", link="stated", ps="", pts=None,
        note="", xq="", yq="", reused=""):
    T["series"].append(dict(series_id=sid(x), sample_id=sid(s) if s else "", kind=kind, figure=fig, panel=panel, method=method, x_id=xid,
                            x_qualifiers=xq, x_label=xl, y_id=yid, y_qualifiers=yq, y_label=yl, z_id=zid, z_label=zl, data_kind=dk,
                            link_status=link, points_source=ps, points=json.dumps(pts) if pts else "", reused_from=reused, note=note,
                            evidence=ev))
    return sid(x)


def V(s, q, value, unit, dk, method, ev, label="", fs="", qual="", vmin="", vmax="", censor="", rel="", regime="", cited="", note=""):
    if q == "composition" and "S/Mo" in label:        # a ratio of two elements, not an atomic fraction: quantity other
        q, qual = "other", ""
    vid = f"{K}:v{len(T['value']) + 1:03d}"
    T["value"].append(dict(value_id=vid, sample_id=sid(s) if s else "", from_series=fs, quantity=q, label_as_printed=label,
                           qualifiers=qual, value=value, value_min=vmin, value_max=vmax, censor=censor, unit=unit, data_kind=dk,
                           method=method, relation=rel, regime=regime, cited_ref=cited, note=note, evidence=ev))
    return vid


# ------------------------------------------------------------------ the grid (Figs. 2, 4, 7b, 8)
TEMPS = [450, 350, 300, 250, 200, 150, 100, 50]
RATIOS = {450: ["0.20", "0.80"], 350: ["0.20", "0.50", "0.80"], 300: ["0.20"],
          250: ["0", "0.20", "0.35", "0.50", "0.65", "0.80", "0.94"], 200: ["0", "0.20", "0.50", "0.65", "0.80", "0.94"],
          150: ["0", "0.20", "0.50", "0.65", "0.80", "0.94"], 100: ["0.20", "0.50", "0.65", "0.80", "0.94"], 50: ["0.20", "0.80"]}
# Fig. 2 class (c/a), Fig. 4 printed S/Mo, Fig. 7b GPC read from colour (Å/cycle), Fig. 8 log10 resistivity read from colour (None = >dl)
GRID = {
    (450, "0.20"): ("c", "2.0", 1.25, 2.30), (450, "0.80"): ("c", "1.9", 1.65, -0.30),
    (350, "0.20"): ("c", "2.1", 0.82, 1.31), (350, "0.50"): ("c", "2.2", 1.26, 1.90), (350, "0.80"): ("c", "1.9", 1.44, 0.75),
    (300, "0.20"): ("c", "2.3", 0.82, 1.20),
    (250, "0"): ("a", "2.8", 0.57, 2.46), (250, "0.20"): ("a", "2.7", 0.63, 1.85), (250, "0.35"): ("a", "2.5", 0.77, 0.86),
    (250, "0.50"): ("c", "2.2", 0.87, 0.15), (250, "0.65"): ("c", "2.1", 1.08, -0.04), (250, "0.80"): ("c", "1.9", 1.34, 0.04),
    (250, "0.94"): ("c", "1.3", 0.63, -2.46),
    (200, "0"): ("a", "3.1", 0.59, None), (200, "0.20"): ("a", "3.0", 0.63, None), (200, "0.50"): ("a", "2.5", 0.85, 0.75),
    (200, "0.65"): ("c", "2.2", 1.05, -0.15), (200, "0.80"): ("c", "1.9", 1.31, -0.04), (200, "0.94"): ("c", "1.3", 0.67, -2.15),
    (150, "0"): ("a", "3.6", 0.69, None), (150, "0.20"): ("a", "3.5", 0.71, None), (150, "0.50"): ("a", "3.0", 0.82, 3.03),
    (150, "0.65"): ("c", "2.1", 1.04, -0.32), (150, "0.80"): ("c", "1.9", 1.29, -0.44), (150, "0.94"): ("c", "1.3", 0.67, -2.07),
    (100, "0.20"): ("a", "4.6", 1.08, None), (100, "0.50"): ("a", "3.6", 1.18, None), (100, "0.65"): ("a", "2.2", 1.16, 0.35),
    (100, "0.80"): ("c", "1.8", 1.34, -0.72), (100, "0.94"): ("c", "1.4", 0.68, -1.85),
    (50, "0.20"): ("a", "7.3", 1.75, None), (50, "0.80"): ("a", "2.0", 1.35, -0.46),
}
assert len(GRID) == 32 and all((t, r) in GRID for t in TEMPS for r in RATIOS[t])


def g(t, r):
    return f"g{t:03d}_{r.replace('.', '').ljust(3, '0')}"


grid = [g(t, r) for t in TEMPS for r in RATIOS[t]]
GEV = "fig2 fig4 fig7b fig8"

# ------------------------------------------------------------------ samples
for t in TEMPS:
    for r in RATIOS[t]:
        S(g(t, r), "run", f"{GEV}; grid cell at {t} °C and H2 flow ratio {r}, present in all four heat maps",
          note="one cell of the temperature x H2-flow-ratio grid; material named MoS2 for the process even where the film is a-MoS2+x")
cryst = [g(t, r) for (t, r), v in GRID.items() if v[0] == "c" and r != "0.94"]
amor = [g(t, r) for (t, r), v in GRID.items() if v[0] == "a"]
amor150 = [g(t, r) for (t, r), v in GRID.items() if v[0] == "a" and t >= 150]
r094 = [g(t, "0.94") for t in (250, 200, 150, 100)]
c080 = [g(t, "0.80") for t in (450, 350, 250, 200, 150, 100)]
g150 = [g(150, r) for r in RATIOS[150]]
hall_low = [g(250, "0.50"), g(250, "0.65"), g(250, "0.80"), g(200, "0.65"), g(200, "0.80"), g(150, "0.65"), g(150, "0.80"), g(100, "0.80")]
hall_ref = [g(350, "0.20"), g(450, "0.20")]
S("grid", "group", f"{GEV} s5.p7; the 32 runs of the temperature x H2-flow-ratio grid", members=grid,
  note="32 cells, identical in position across Figs. 2, 4, 7b and 8")
S("grid_c", "group", "fig4 s3.p11; c-MoS2 region of the heat maps (crystalline in Fig. 2, ratio up to 0.80)", members=cryst)
S("grid_a150", "group", "s3.p11 fig2; amorphous grid films deposited at 150 °C or above", members=amor150)
S("grid_094", "group", "fig4 fig8 s3.p38; runs with H2 flow ratio 0.94 (Mo/c-MoS2 region)", members=r094)
S("grid_c080", "group", "s3.p35 fig8; crystalline runs with H2 flow ratio 0.80", members=c080)
S("set150", "group", "fig1a fig5a fig6 fig7a s3.p22; the six 150 °C grid runs (ratios 0-0.94) shown in Figs. 1a, 5, 6a and 7a",
  members=g150)
S("hall_lowT", "group", "s3.p36 s3.p37; c-MoS2 films made with ratio 0.50-0.80 at 100-250 °C (the grid runs in that range)", members=hall_low,
  note="which of these runs (or companion films on fused SiO2) were Hall-measured is given only in the SI")
S("hall_ref", "group", "s3.p37; reference c-MoS2 films at 350-450 °C with ratio 0.20 (grid runs at 350 and 450 °C)", members=hall_ref,
  note="the paper says 350-450 °C; the grid has 350 and 450 °C at ratio 0.20")
# other MoS2 runs
for c, th in ((10, "0.9"), (20, "1.6"), (30, "2.6"), (50, "4.8")):
    S(f"f1b_{c}c", "run", f"fig1b; legend entry {c} cyc ({th} nm)", label=f"{c} cyc ({th} nm)")
S("f1b_set", "group", "fig1b s3.p5; the four thickness-series films of Fig. 1b", members=[f"f1b_{c}c" for c in (10, 20, 30, 50)])
S("sub_ref", "reference", "fig1b; legend entry for the bare substrate spectrum", label="SiO2/Si", material="SiO2/Si (bare)", precursor="",
  coreactant="", pm="", reactor="", note="uncoated substrate")
S("wafer", "run", "fig1c s5.p11 s3.p6; MoS2 film on a 4 inch wafer mapped by SE", note="about 5 nm film; also called a 5 nm film in Methods")
S("wafer_bare", "reference", "s5.p11; bare 450 nm SiO2/Si substrate mapped as reference", material="SiO2/Si (bare)", precursor="",
  coreactant="", pm="", reactor="", note="no data shown")
S("pet", "run", "fig1d s3.p6 s5.p2; MoS2 film on PET foil (photograph)",
  note="uncoated and Al2O3-coated PET gave similar results; treated as one sample")
S("fet100", "run", "fig3 s3.p8 s3.p43 s5.p18; sub-5 nm film at 100 °C used for TEM (Fig. 3a) and the FET",
  note="s5.p18 says the thin 100 and 350 °C TEM samples went through transistor patterning, so the TEM film and the FET film are one sample")
S("fet350", "run", "fig3 s3.p10 s3.p43 s5.p18; reference film at 350 °C (Sharma et al. condition) for TEM (Fig. 3b) and the FET",
  note="reference recipe of ref 36")
for r in ("020", "065", "080"):
    S(f"rbs{r}", "run", f"tab1.cap s3.p19 s3.p21; ~50 nm film on glassy carbon at 150 °C, ratio 0.{r[1:]}, analysed by RBS/ERD and XPS",
      note="Table 1 film; its cycle number is not stated")
S("rbs_set", "group", "tab1.cap s3.p21; the three Table 1 films", members=["rbs020", "rbs065", "rbs080"])
S("tem065", "run", "fig6 s3.p26 s5.p18; ~50 nm film at 150 °C, ratio 0.65, 500 cycles, TEM cross-section (Fig. 6b)",
  note="on SiO2 (visible in the TEM image); may or may not be the same deposition as rbs065 (that one is on glassy carbon)")
S("h2plasma", "run", "s3.p52; ratio 0.20 plasma step at 150 °C followed by an extra H2 plasma step each cycle",
  note="extra step per cycle; results in SI Table S8")
S("h2gas", "run", "s3.p52; ratio 0.20 plasma step at 150 °C followed by an extra H2 gas (no plasma) step each cycle")
S("lowH2S_250", "run", "s3.p53; 250 °C, no H2, reduced H2S flow (Fig. S22a)", note="flows only in SI")
S("lowH2S_150", "run", "s3.p53; 150 °C, no H2, reduced H2S flow (Fig. S22b)", note="flows only in SI")
mos2_tab2 = grid + [f"f1b_{c}c" for c in (10, 20, 30, 50)] + ["wafer", "pet", "fet100", "fet350", "rbs020", "rbs065", "rbs080", "tem065",
                                                              "h2plasma", "h2gas"]
S("mos2_tab2", "group", "s5.p4 tab2.cap; MoS2 runs whose plasma gas flows follow Table 2", members=mos2_tab2)
S("mos2_all", "group", "s5.p1 s5.p6; all MoS2 PEALD runs of the paper (standard cycle)", members=mos2_tab2 + ["lowH2S_250", "lowH2S_150"],
  note="the low-H2S runs keep the cycle but not the Table 2 flows")
S("dep100", "group", "s3.p44; films deposited at 100 °C", members=[g(100, r) for r in RATIOS[100]] + ["fet100", "pet"])
# other TMDCs
WP, TP = "W(NtBu)2(NMe2)2", "Ti(NMe2)4"
S("ws2_000", "run", "fig9a s3.p46; WSx at 150 °C without H2", material="WS2", precursor=WP, coreactant="H2S/Ar remote plasma", reactor="",
  note="published WS2 PEALD process (ref 52) run at 150 °C; reactor not restated")
S("ws2_080", "run", "fig9a s3.p46 s5.p8; WS2 at 150 °C with ratio 0.80", material="WS2", precursor=WP, coreactant=CO, reactor="",
  note="ref 52 process with the H2 flow ratio changed")
S("tis2_000", "run", "fig9b; TiSx at 100 °C without H2", material="TiS2", precursor=TP, coreactant="H2S/Ar remote plasma", reactor="",
  note="published TiS2 PEALD process (ref 53) at 100 °C")
S("tis2_050", "run", "fig9b s3.p48 s5.p8; TiS2 at 100 °C with ratio 0.50", material="TiS2", precursor=TP, coreactant=CO, reactor="")
S("tis2_080", "run", "s3.p48; TiS2 with ratio 0.80, S-poor (not shown)", material="TiS2", precursor=TP, coreactant=CO, reactor="",
  note="not shown; temperature not stated")
S("tis2_thermal", "run", "fig9b s5.p8; thermal TiSx recipe (ref 80) used for comparison", label="Thermal ALD", material="TiS2", precursor=TP,
  coreactant="", pm="thermal ALD", reactor="", note="coreactant of the thermal recipe not stated in this paper (ref 80)")

# ------------------------------------------------------------------ conditions
# deposition temperature per grid run
for t in TEMPS:
    for r in RATIOS[t]:
        C(g(t, r), "process", "deposition_temperature", str(t), "°C", f"{GEV} s5.p1; y position of the cell",
          qual="kind=set_point",
          note="substrate table temperature; actual substrate temperature lower than the table for 200-450 °C" if t >= 200
          else "walls and table at the same value; difference to the real temperature negligible")
        C(g(t, r), "process", "other", r, "", f"{GEV} eq1; x position of the cell", label="H2 flow ratio")
# cycles by temperature (s5.p7) on the grid group
for n, when in (("100", "deposition_temperature = 450 °C"), ("120", "deposition_temperature = 50, 300 or 350 °C"),
                ("140", "deposition_temperature = 100-250 °C")):
    C("grid", "process", "cycle_number", n, "", "s5.p7 fig2.cap fig4.cap fig8.cap; cycles by temperature", when=when,
      note="stated for most depositions, unless otherwise noted; chosen to give ~10 nm at ratio 0.20 (50-100 °C: no such data); captions say 100-140")
# 150 °C set: 140 cycles stated in captions (consistent with the rule)
C("set150", "process", "cycle_number", "140", "", "fig1.cap fig5.cap fig6.cap; 150 °C films with 140 cycles",
  note="also follows from the s5.p7 rule")
# Fig 1b set
C("f1b_set", "process", "deposition_temperature", "150", "°C", "fig1b s3.p5; 150 °C label on panel", qual="kind=set_point")
C("f1b_set", "process", "other", "0.80", "", "s3.p5; optimized ratio used for the thickness series", label="H2 flow ratio")
for c in (10, 20, 30, 50):
    C(f"f1b_{c}c", "process", "cycle_number", str(c), "", f"fig1b; legend {c} cyc")
C("f1b_set", "substrate_prep", "substrate", "SiO2/Si", "", "fig1b; reference spectrum labelled SiO2/Si; intensity normalised to Si",
  dk="assumed", note="450 nm SiO2/Si per s5.p2 for most depositions")
C("sub_ref", "substrate_prep", "substrate", "SiO2/Si", "", "fig1b; bare substrate spectrum")
# wafer
C("wafer", "process", "deposition_temperature", "150", "°C", "fig1.cap fig1c; map film at 150 °C", qual="kind=set_point")
C("wafer", "process", "other", "0.80", "", "fig1.cap fig1c; ratio of the map film", label="H2 flow ratio")
C("wafer", "process", "cycle_number", "50", "", "fig1.cap fig1c; 50 cycles")
C("wafer", "substrate_prep", "substrate", "450 nm SiO2/Si(100), 4 inch wafer", "", "fig1c s5.p11; 4 inch 450 nm SiO2/Si wafer")
C("wafer", "measurement", "other", "1.2-3.3", "eV", "s5.p11; ex situ mapping SE spectral range (M-2000 with mapping stage)",
  label="SE mapping spectral range", note="circular pattern excluding the wafer edge; MoS2 and SiO2 thickness fitted with fixed optical constants")
C("wafer_bare", "substrate_prep", "substrate", "450 nm SiO2/Si(100), 4 inch wafer", "", "s5.p11; bare reference wafer")
# PET
C("pet", "process", "deposition_temperature", "100", "°C", "fig1.cap fig1d s3.p6; 100 °C on PET", qual="kind=set_point")
C("pet", "process", "other", "0.80", "", "fig1.cap s3.p6; ratio 0.80", label="H2 flow ratio")
C("pet", "process", "cycle_number", "50", "", "fig1.cap; 50 cycles")
C("pet", "substrate_prep", "substrate", "PET foil (Melinex ST504), 125 µm, 15 x 15 cm", "", "s5.p2 fig1.cap fig1d; PET foil type, thickness and size",
  note="both uncoated and ALD Al2O3-coated PET used, similar results")
C("pet", "substrate_prep", "other", "50", "cycles", "s5.p2; optional Al2O3 coating of PET (AlMe3/H2O)", label="Al2O3 coating cycles on PET",
  note="applies to the coated PET variant only")
# FET / TEM films
C("fet100", "process", "deposition_temperature", "100", "°C", "fig3.cap s3.p8 s3.p43; 100 °C", qual="kind=set_point")
C("fet100", "process", "other", "0.80", "", "fig3.cap s3.p8 s3.p43; ratio 0.80", label="H2 flow ratio")
C("fet100", "process", "cycle_number", "50", "", "fig3.cap s3.p8; 50 cycles")
C("fet350", "process", "deposition_temperature", "350", "°C", "fig3.cap s3.p10 s3.p43; 350 °C", qual="kind=set_point",
  note="table temperature; actual substrate temperature lower")
C("fet350", "process", "other", "0.20", "", "fig3.cap s3.p10 s3.p43; ratio 0.20", label="H2 flow ratio")
C("fet350", "process", "cycle_number", "60", "", "fig3.cap; 60 cycles")
for s_ in ("fet100", "fet350"):
    C(s_, "substrate_prep", "substrate", "90 nm SiO2/Si", "", "s5.p2; substrate for the transistor samples",
      note="Ni contacts; Au/Ni metal deposition and channel patterning before FIB (s5.p18)")
# RBS films
for r in ("020", "065", "080"):
    C(f"rbs{r}", "process", "other", f"0.{r[1:]}", "", f"tab1.r{'123'[('020', '065', '080').index(r)]}c0 s3.p21; ratio of the Table 1 row",
      label="H2 flow ratio")
C("rbs_set", "process", "deposition_temperature", "150", "°C", "s3.p19 s3.p21; Table 1 films at 150 °C", qual="kind=set_point")
C("rbs_set", "substrate_prep", "substrate", "glassy carbon", "", "s3.p19; Table 1 films grown on glassy carbon")
C("tem065", "process", "deposition_temperature", "150", "°C", "fig6.cap s3.p26; 150 °C", qual="kind=set_point")
C("tem065", "process", "other", "0.65", "", "fig6.cap fig6; ratio 0.65 (panel label 0.65 H2)", label="H2 flow ratio")
C("tem065", "process", "cycle_number", "500", "", "fig6.cap; 500 cycles")
C("tem065", "substrate_prep", "substrate", "SiO2/Si", "", "fig6 s3.p26; SiO2 visible under the film in the TEM image")
# H2 step experiments
for s_ in ("h2plasma", "h2gas"):
    C(s_, "process", "deposition_temperature", "150", "°C", "s3.p52; 150 °C", qual="kind=set_point")
    C(s_, "process", "other", "0.20", "", "s3.p52; ratio of the H2S/H2/Ar plasma step", label="H2 flow ratio")
C("h2plasma", "process", "other", "H2 plasma", "", "s3.p52; separate H2 plasma step after the H2S/H2/Ar plasma", label="extra step after plasma")
C("h2gas", "process", "other", "H2 gas", "", "s3.p52; separate H2 gas step after the H2S/H2/Ar plasma", label="extra step after plasma")
C("lowH2S_250", "process", "deposition_temperature", "250", "°C", "s3.p53; 250 °C", qual="kind=set_point")
C("lowH2S_150", "process", "deposition_temperature", "150", "°C", "s3.p53; 150 °C", qual="kind=set_point")
for s_ in ("lowH2S_250", "lowH2S_150"):
    C(s_, "process", "other", "0", "", "s3.p53; no H2 added, H2S flow reduced (values in SI)", label="H2 flow ratio")
# MoS2 recipe (s5.p1, s5.p4, s5.p6)
A = "mos2_all"
C(A, "process", "reactor_type", "Oxford Instruments FlexAL, 13.56 MHz remote ICP", "", "s5.p1; reactor and plasma source")
C(A, "process", "other", "13.56", "MHz", "s5.p1; ICP source frequency", label="ICP frequency")
C(A, "process", "other", "1.33e-4", "Pa", "s5.p1; turbo pump base pressure", label="base pressure", note="printed 10^-6 Torr")
C(A, "process", "other", "same as deposition temperature", "", "s5.p1; walls and substrate set equal for 50-150 °C",
  label="reactor wall temperature", when="deposition_temperature = 50-150 °C")
C(A, "process", "other", "150", "°C", "s5.p1; walls at 150 °C while the table is heated to 200-450 °C", label="reactor wall temperature",
  when="deposition_temperature = 200-450 °C")
C(A, "process", "pulse_time", "6", "s", "s5.p6; Mo precursor dose", qual="step=reactant_A")
C(A, "process", "purge_time", "10", "s", "s5.p6; purge after precursor", qual="step=purge_A", note="6 s with 300 sccm Ar then 4 s pumping without flow")
C(A, "process", "gas_flow_rate", "300", "sccm", "s5.p6; Ar into chamber during the first 6 s of purge A and during purge B",
  qual="step=purge_A;gas=Ar")
C(A, "process", "pulse_time", "20", "s", "s5.p6; H2S/H2/Ar plasma exposure", qual="step=plasma")
C(A, "process", "other", "100", "W", "s5.p6; ICP power", label="plasma power", qual="step=plasma")
C(A, "process", "purge_time", "6", "s", "s5.p6; purge after plasma with 300 sccm Ar", qual="step=purge_B")
C(A, "process", "gas_flow_rate", "300", "sccm", "s5.p6; Ar during purge B", qual="step=purge_B;gas=Ar")
C(A, "process", "source_temperature", "50", "°C", "s5.p6; precursor canister temperature")
C(A, "process", "other", "70", "°C", "s5.p6; heated delivery lines", label="delivery line temperature")
C(A, "process", "carrier_gas", "Ar", "", "s5.p6; Ar carries the precursor", note="50 sccm")
C(A, "process", "gas_flow_rate", "50", "sccm", "s5.p6; Ar carrier flow with the precursor", qual="step=reactant_A;gas=Ar")
C(A, "process", "other", "4", "s", "s5.p6; stabilisation step before the precursor pulse", label="pressure/flow stabilisation time",
  qual="step=reactant_A")
C(A, "process", "other", "5", "s", "s5.p6; stabilisation step before the plasma pulse", label="pressure/flow stabilisation time",
  qual="step=plasma")
C(A, "process", "cycle_time", "51", "s", "s5.p6; total cycle length")
C(A, "process", "process_pressure", "26.7", "Pa", "s5.p6; pressure set by the APC valve during the precursor pulse", qual="step=reactant_A",
  note="printed 200 mTorr")
C(A, "process", "process_pressure", "0.8", "Pa", "s5.p6 s5.p4; pressure with APC valve open during plasma", qual="step=plasma",
  note="printed approximately 6 mTorr")
C(A, "process", "precursor_purity", "98", "%", "s5.p6; Mo precursor purity", qual="species=Mo_precursor", note="Mo(NtBu)2(NMe2)2 from Strem")
for gas, p in (("H2S", "99.5"), ("H2", "99.999"), ("Ar", "99.999")):
    C(A, "process", "precursor_purity", p, "%", f"s5.p4; {gas} gas purity", qual=f"species={gas}")
C(A, "process", "other", "verified: no S deposition by plasma alone; no precursor condensation", "", "s5.p7; ALD-regime checks for 50-100 °C",
  label="ALD regime check", note="SE data not shown; ref 87 for condensation")
# Table 2 flows (plasma step) on mos2_tab2
T2 = [("0", "10", "0", "40", 1), ("0.20", "8", "2", "40", 2), ("0.35", "6.5", "3.5", "40", 3), ("0.50", "5", "5", "40", 4),
      ("0.65", "3.5", "6.5", "40", 5), ("0.80", "2", "8", "40", 6), ("0.94", "2", "30", "18", 7)]
C("mos2_tab2", "process", "gas_flow_rate", "50", "sccm", "s5.p4 s5.p5 tab2.cap; total flow through the ICP tube during the plasma",
  qual="step=plasma", note="H2S + H2 = 10 sccm except at ratio 0.94 (s5.p4, s3.p51)")
for r, h2s, h2, ar, i in T2:
    for gas, v, c_ in (("H2S", h2s, 1), ("H2", h2, 2), ("Ar", ar, 3)):
        C("mos2_tab2", "process", "gas_flow_rate", v, "sccm", f"tab2.r{i}c{c_} tab2.r{i}c0 tab2.r0c{c_} eq1 s3.p51; Table 2 row ratio {r}, {gas} flow",
          qual=f"step=plasma;gas={gas}", when=f"H2 flow ratio = {r}")
# other TMDC runs
C("ws2_000", "process", "deposition_temperature", "150", "°C", "fig9.cap fig9a s3.p46; 150 °C", qual="kind=set_point")
C("ws2_080", "process", "deposition_temperature", "150", "°C", "fig9.cap s3.p46 s5.p8; 150 °C", qual="kind=set_point")
C("ws2_000", "process", "other", "0", "", "fig9a s3.p46; no H2", label="H2 flow ratio")
C("ws2_080", "process", "other", "0.80", "", "fig9a s3.p46 s5.p8; ratio 0.80", label="H2 flow ratio")
C("tis2_000", "process", "deposition_temperature", "100", "°C", "fig9.cap fig9b; 100 °C", qual="kind=set_point")
C("tis2_050", "process", "deposition_temperature", "100", "°C", "fig9.cap s3.p48 s5.p8; 100 °C", qual="kind=set_point")
C("tis2_thermal", "process", "deposition_temperature", "100", "°C", "fig9.cap fig9b; all TiSx spectra at 100 °C", qual="kind=set_point",
  dk="assumed", note="caption puts all Fig. 9b films at 100 °C")
C("tis2_000", "process", "other", "0", "", "fig9b s3.p45; no H2 (published process)", label="H2 flow ratio")
C("tis2_050", "process", "other", "0.50", "", "fig9b s3.p48 s5.p8; ratio 0.50", label="H2 flow ratio")
C("tis2_080", "process", "other", "0.80", "", "s3.p48; ratio 0.80 found too high", label="H2 flow ratio")
# whole-paper conditions
C("*", "substrate_prep", "other", "used as received; cut; blown with N2", "", "s5.p3; substrate handling", label="substrate cleaning")
C("*", "substrate_prep", "other", "1x1 to 3x3", "cm2", "s5.p3; typical substrate size", label="substrate size")
C("*", "process", "other", "8", "inch", "s5.p3; substrates loaded on a carrier wafer", label="carrier wafer diameter")
C("*", "process", "other", "1.33", "Pa", "s5.p3; load lock pumped below this before transfer", label="load-lock pressure", note="printed less than 10^-2 Torr")
C("*", "process", "other", "10", "min", "s5.p3; equilibration under Ar before deposition", label="temperature equilibration time")
C("*", "process", "process_pressure", "26.7", "Pa", "s5.p3; Ar pressure during equilibration", qual="step=none", note="printed 200 mTorr")
C("grid", "substrate_prep", "substrate", "450 nm SiO2/Si(100)", "", "s5.p2; substrate of most depositions", dk="assumed",
  note="most depositions; some Hall films on fused SiO2 (s5.p2, s5.p13)")
# measurement settings (whole paper, by method)
M = [("ellipsometry", "other", "SE spectral range", "0.8-5.0", "eV", "s5.p9; in situ M-2000FI range", "in situ SE with M-2000FI"),
     ("ellipsometry", "other", "SE fitting range", "0.8-4.0", "eV", "s5.p9; range typically used for fitting", "in situ SE with M-2000FI"),
     ("ellipsometry", "other", "SE spectral range", "1.2-5.0", "eV", "s5.p9; in situ M-2000F range", "in situ SE with M-2000F"),
     ("ellipsometry", "other", "SE measurement interval", "10", "cycles", "s5.p9; one spectrum every 10 cycles (typical)", "in situ SE"),
     ("ellipsometry", "other", "SE optical model", "MoSx (B-spline)/SiO2/interlayer/Si", "", "s5.p9; CompleteEASE 5.1 model", "SE"),
     ("ellipsometry", "other", "EMA void fraction of roughness layer", "50", "%", "s5.p9; roughness layer of crystalline films",
      "SE of crystalline MoS2"),
     ("ellipsometry", "other", "reported thickness", "dense layer + half of roughness layer", "", "s5.p9; thickness definition", "SE"),
     ("ellipsometry", "probe_resolution", "", "a few", "mm2", "s5.p10; analysis area averaging many grains", "SE"),
     ("ellipsometry", "other", "SE fitting sequence", "SiO2 and T from pre-deposition spectrum; optical constants from last spectrum; "
      "thickness only in between", "", "s5.p10; fitting procedure", "in situ SE"),
     ("ellipsometry", "other", "SE spectral range", "1.2-6.5", "eV", "s5.p11; ex situ M-2000U", "ex situ SE"),
     ("ellipsometry", "other", "SE angles of incidence", "65, 75, 85", "deg", "s5.p11; variable-angle stage", "ex situ SE"),
     ("electrical", "other", "resistivity definition", "sheet resistance x in situ SE thickness", "", "s5.p12; four-point probe", "four-point probe"),
     ("electrical", "other", "Hall sample size", "1x1", "cm2", "s5.p13; van der Pauw samples, approximately", "Hall"),
     ("electrical", "other", "Hall method", "AC Hall, van der Pauw, repeated measurements", "", "s5.p13; Lakeshore 8404", "Hall"),
     ("sem", "other", "acceleration voltage", "3", "kV", "s5.p14; Zeiss Sigma, InLens detector", "SEM"),
     ("afm", "other", "probe spring constant", "0.4", "N/m", "s5.p14; ScanAsyst-air probes", "AFM"),
     ("afm", "other", "tip radius", "2", "nm", "s5.p14; nominal", "AFM"),
     ("afm", "other", "Rq image size", "500 x 500", "nm2", "s5.p14; first-order flattening before Rq", "AFM"),
     ("raman", "other", "laser wavelength", "514", "nm", "s5.p15; Renishaw inVia", "Raman"),
     ("raman", "other", "objective", "50x, NA 0.75", "", "s5.p15", "Raman"),
     ("raman", "other", "grating", "1800", "lines/mm", "s5.p15", "Raman"),
     ("raman", "other", "accumulation", "6 x 10", "s", "s5.p15; six 10 s spectra per measurement", "Raman"),
     ("raman", "other", "laser power on sample", "0.6", "mW", "s5.p15; 100 mW laser with 1% ND filter (estimate)", "Raman"),
     ("xps", "other", "X-ray energy", "1486.6", "eV", "s5.p16; monochromatic Al Ka, K-Alpha", "XPS"),
     ("xps", "probe_resolution", "", "400", "µm", "s5.p16; X-ray spot diameter", "XPS"),
     ("xps", "other", "binding energy reference", "284.8", "eV", "s5.p16; adventitious C 1s", "XPS"),
     ("xps", "other", "pass energy", "50", "eV", "s5.p16; survey spectra", "XPS survey"),
     ("xps", "other", "pass energy", "20", "eV", "s5.p16; high-resolution spectra", "XPS high resolution"),
     ("xps", "other", "peak fitting", "Gaussian-Lorentzian sum, Shirley background", "", "s5.p16; Avantage", "XPS"),
     ("xps", "other", "sputter ion energy", "500", "eV", "s5.p16; Ar+ depth profiling (not shown)", "XPS depth profile"),
     ("xps", "other", "sputter interval", "30", "s", "s5.p16; spectrum after every 30 s", "XPS depth profile"),
     ("rbs", "other", "ion beam", "2 MeV He+", "", "s5.p17; RBS for atoms, ERD for H (Detect 99)", "RBS/ERD"),
     ("tem", "other", "acceleration voltage", "200", "kV", "s5.p18; JEOL ARM 200F, FIB lift-out with C/Pt or SiO2 mask", "TEM")]
for meth, q, lab, v, u, ev, when in M:
    C("*", "measurement", q, v, u, ev, label=lab, when=f"measured by {when}", note=f"method {meth}")

# ------------------------------------------------------------------ series
v1 = json.load(open(ROOT / "schema_pilot/v1_points.json"))["series"]
pj = json.load(open(ROOT / "cases/points.json"))["series"]


def v1pts(k, drop=()):
    return [p for p in v1[k]["points"] if p[0] not in drop]


RS = ("other", "Raman shift (cm-1)")
SER("f1a_sketch", "mos2_all", "image", "1", "a", "schematic", "fig1a fig1.cap s3.p1; process cycle and plasma-species sketch", dk="schematic",
    note="ALD cycle (precursor, Ar purge, plasma, Ar purge) and high/low H2 ratio plasma species")
for r, k in (("0.94", "s1a_R094"), ("0.80", "s1a_R080"), ("0.65", "s1a_R065"), ("0.50", None), ("0.20", None), ("0", None)):
    SER(f"f1a_{r.replace('.', '')}", g(150, r), "spectrum", "1", "a", "raman", f"fig1a fig1.cap s3.p4; Fig. 1a legend {r}",
        xid="other", xl="Raman shift (cm-1)", yid="other", yl="Intensity (Arb. units)", link="inferred",
        ps="v1 checked" if k else "", pts=v1pts(f"{K}:{k}", drop=(518.0,)) if k else None,
        note="150 °C, 140 cycles, same ratio as the grid run; offset curves, unnumbered y axis" +
             ("; v1 point at 518 cm-1 dropped (clipped Si peak)" if k else ""))
for c, th in ((50, "4.8"), (30, "2.6"), (20, "1.6"), (10, "0.9")):
    SER(f"f1b_{c}c", f"f1b_{c}c", "spectrum", "1", "b", "raman", f"fig1b s3.p5; legend {c} cyc ({th} nm)", xid="other",
        xl="Raman shift (cm-1)", yid="other", yl="Intensity (Normalized to Si)", note="E2g shifts down and A1g up with thickness")
SER("f1b_sub", "sub_ref", "spectrum", "1", "b", "raman", "fig1b; legend SiO2/Si", xid="other", xl="Raman shift (cm-1)", yid="other",
    yl="Intensity (Normalized to Si)", ps="v1 checked", pts=v1pts(f"{K}:s1b_sub"), note="flat line; y scale of the reader")
p6 = [p for p in pj if p.get("paper") == PID and p.get("figure") == "1" and p.get("panel") == "c"][0]
SER("f1c_map", "wafer", "map", "1", "c", "ellipsometry", "fig1c fig1.cap s3.p6 s5.p11; thickness map over the 4 inch wafer", xid="other",
    xl="wafer position (mm, read off the map)", yid="film_thickness", yq="position=planar", yl="Thickness (nm), colour scale",
    zid="film_thickness", zl="Thickness (nm)", ps="cases/points.json", pts=p6["points"],
    note="points = thickness along the vertical diameter read from the dot colours (+-0.05 nm); colour bar 4.7-5.3 nm")
SER("f1d_photo", "pet", "image", "1", "d", "photograph", "fig1d fig1.cap; photo of coated PET foil held bent")
SER("f2_map", "grid", "map", "2", "", "raman", "fig2 fig2.cap s3.p7; crystallinity class per run", xid="other", xl="H2 flow ratio",
    yid="deposition_temperature", yl="T deposition (°C)", zid="crystallinity", zl="Crystallinity (Amorphous/Crystalline)",
    note="32 cells; classed from Raman spectra in SI Fig. S5")
SER("f3a_tem", "fet100", "image", "3", "a", "tem", "fig3 fig3.cap s3.p8 s3.p9; cross-section, 100 °C 0.80")
SER("f3b_tem", "fet350", "image", "3", "b", "tem", "fig3 fig3.cap s3.p10; cross-section, 350 °C 0.20")
SER("f4_map", "grid", "map", "4", "", "xps", "fig4 fig4.cap s3.p11; S/Mo ratio printed in every cell", xid="other", xl="H2 flow ratio",
    yid="deposition_temperature", yl="T deposition (°C)", zid="other", zl="XPS S/Mo ratio",
    note="dotted lines separate a-MoS2+x, c-MoS2 and Mo/c-MoS2 regions")
F5 = [("0.94", "1.3"), ("0.80", "1.9"), ("0.65", "2.1"), ("0.50", "3.0"), ("0.20", "3.5")]
for r, smo in F5:
    rr = r.replace(".", "")
    SER(f"f5a_{rr}", g(150, r), "spectrum", "5", "a", "xps", f"fig5a fig5.cap s3.p14; Mo 3d/S 2s data, ratio {r} (MoS{smo})",
        xid="other", xl="Binding energy (eV)", yid="other", yl="Intensity (arb. units)", link="inferred", ps="v1 checked",
        pts=v1pts(f"{K}:s5a_R{rr}_data"), note="150 °C, 140 cycles; printed S/Mo equals the Fig. 4 cell; stacked, unnumbered y")
    SER(f"f5a_{rr}_fit", g(150, r), "spectrum", "5", "a", "xps", f"fig5a s3.p15; fit envelope and components, ratio {r}", xid="other",
        xl="Binding energy (eV)", yid="other", yl="Intensity (arb. units)", dk="fit", link="inferred",
        note="Mo4+, Mo5+, Mo6+, Mo(4-d)+ (crystalline), metallic Mo (0.94) and two S 2s components")
    SER(f"f5b_{rr}", g(150, r), "spectrum", "5", "b", "xps", f"fig5b fig5.cap s3.p17; S 2p data, ratio {r}", xid="other",
        xl="Binding energy (eV)", yid="other", yl="Intensity (arb. units)", link="inferred", note="v1 points rejected (wrong shape)")
    SER(f"f5b_{rr}_fit", g(150, r), "spectrum", "5", "b", "xps", f"fig5b s3.p18; S 2p fit components, ratio {r}", xid="other",
        xl="Binding energy (eV)", yid="other", yl="Intensity (arb. units)", dk="fit", link="inferred",
        note="S2- (and S2^2- terminal) doublet; bridging S2^2-/apical S2- doublet; electron-rich S2- for crystalline")
for r in RATIOS[150]:
    SER(f"f6a_{r.replace('.', '')}", g(150, r), "image", "6", "a", "sem", f"fig6 fig6.cap s3.p22; SEM top view, ratio {r}", link="inferred",
        note="150 °C, 140 cycles, 8-20 nm films; Rq printed on the image is from AFM")
SER("f6b_tem", "tem065", "image", "6", "b", "tem", "fig6 fig6.cap s3.p26; cross-section of ~50 nm film, inset magnified",
    note="smoothing filter applied")
F7 = {"0": "s7a_R000", "0.20": "s7a_R020", "0.50": "s7a_R050", "0.65": "s7a_R065", "0.80": "s7a_R080", "0.94": "s7a_R094"}
for r, k in F7.items():
    SER(f"f7a_{r.replace('.', '')}", g(150, r), "plot", "7", "a", "ellipsometry", f"fig7a fig7.cap s3.p27 s3.p28; legend {r}",
        xid="cycle_number", xl="Number of ALD cycles", yid="film_thickness", yq="position=planar", yl="Thickness (nm)", link="inferred",
        ps="v1 checked", pts=v1pts(f"{K}:{k}"),
        note="in situ SE at 150 °C; thickness at 100 cycles / 100 matches the Fig. 7b cell within 0.03 A/cycle")
SER("f7b_map", "grid", "map", "7", "b", "ellipsometry", "fig7b fig7.cap s3.p29; GPC averaged over the first 100 cycles", xid="other",
    xl="H2 flow ratio", yid="deposition_temperature", yl="T deposition (°C)", zid="growth_per_cycle", zl="GPCaverage (Å/cycle)",
    note="colour scale 0.50-1.75 A/cycle, linear")
SER("f8_map", "grid", "map", "8", "", "electrical", "fig8 fig8.cap s3.p33; resistivity per run, four-point probe", xid="other",
    xl="H2 flow ratio", yid="deposition_temperature", yl="T deposition (°C)", zid="resistivity", zl="Resistivity (Ωcm)",
    note="log colour scale 1e-3 to 1e3 Ω cm, top band >dl")
SER("f9a_080", "ws2_080", "spectrum", "9", "a", "raman", "fig9a fig9.cap s3.p46; legend 0.80", xid="other", xl="Raman shift (cm-1)",
    yid="other", yl="Intensity (Arb. units)", ps="v1 checked", pts=v1pts(f"{K}:s9a_R080"), note="ZA, LA, 2LA/E2g, A1g and Si peaks")
SER("f9a_000", "ws2_000", "spectrum", "9", "a", "raman", "fig9a fig9.cap s3.p46; legend 0", xid="other", xl="Raman shift (cm-1)",
    yid="other", yl="Intensity (Arb. units)", ps="v1 checked", pts=v1pts(f"{K}:s9a_R000"), note="featureless; Si peak hidden behind the 0.80 curve")
SER("f9b_050", "tis2_050", "spectrum", "9", "b", "raman", "fig9b fig9.cap s3.p48; legend 0.50", xid="other", xl="Raman shift (cm-1)",
    yid="other", yl="Intensity (Arb. units)", ps="v1 checked", pts=v1pts(f"{K}:s9b_R050"), note="Eg, A1g and shoulder Sh")
SER("f9b_000", "tis2_000", "spectrum", "9", "b", "raman", "fig9b fig9.cap; legend 0", xid="other", xl="Raman shift (cm-1)",
    yid="other", yl="Intensity (Arb. units)", note="nearly flat")
SER("f9b_thermal", "tis2_thermal", "spectrum", "9", "b", "raman", "fig9b fig9.cap; legend Thermal ALD", xid="other",
    xl="Raman shift (cm-1)", yid="other", yl="Intensity (Arb. units)", ps="v1 checked", pts=v1pts(f"{K}:s9b_thermal"),
    note="weak Eg and A1g")
SER("tab1", "rbs_set", "table", "", "", "rbs", "tab1.cap tab1.r0c0 tab1.r0c1 tab1.r0c2 tab1.r0c3 tab1.r0c4 tab1.r0c5 tab1.r0c6 tab1.r0c7 "
    "s3.p19; Table 1 composition of the three ~50 nm films", note="RBS (Mo, S, C, N, O), ERD (H), XPS S/Mo; header cells carried by the values")
SER("tab2", "mos2_tab2", "table", "", "", "tabulated", "tab2.cap tab2.r0c0 tab2.r0c1 tab2.r0c2 tab2.r0c3 s5.p4 s5.p5; Table 2 gas flows",
    note="carried by the gas_flow_rate conditions")

# ------------------------------------------------------------------ values: grid
for t in TEMPS:
    for r in RATIOS[t]:
        cl, smo, gpc, lr = GRID[(t, r)]
        s_ = g(t, r)
        V(s_, "crystallinity", "crystalline" if cl == "c" else "amorphous", "", "measured", "raman",
          f"fig2; cell {t} °C / {r}" + (" s3.p4" if t == 150 else "") + (" s3.p7" if (t, r) in ((100, "0.80"), (300, "0.20")) else ""),
          fs=sid("f2_map"), note="colour class read from Fig. 2")
        ev = f"fig4; printed value in cell {t} °C / {r}"
        if t == 150 and r != "0":
            ev = f"fig4 fig5a fig5b; printed in cell {t} °C / {r} and on the Fig. 5 spectrum"
        if (t, r) == (150, "0.50"):
            ev = "fig4 fig5a s3.p18; printed 3.0; text calls it a-MoS3.0"
        if (t, r) == (100, "0.65"):
            ev = "fig4 s3.p34 s3.p13; printed 2.2; text: MoS2.2 amorphous film at 100 °C"
        if (t, r) == (50, "0.80"):
            ev = "fig4 s3.p13; printed 2.0; amorphous though near MoS2"
        V(s_, "composition", smo, "", "measured", "xps", ev, label="XPS S/Mo ratio", fs=sid("f4_map"), qual="element=S",
          note="S/Mo atomic ratio printed in the heat-map cell")
        ev = f"fig7b; colour of cell {t} °C / {r} against the colour bar"
        if t == 250 and r in ("0.35", "0.50"):
            ev += " s3.p32"
        V(s_, "growth_per_cycle", f"{gpc:.2f}", "Å", "measured", "ellipsometry", ev, fs=sid("f7b_map"), qual="position=planar",
          rel="average over the first 100 cycles",
          note="read from the colour (+-0.03 A/cycle); black cell at the top of the bar, may be clipped" if (t, r) == (50, "0.20")
          else "read from the colour against the linear bar (+-0.03 A/cycle)")
        ev = f"fig8; colour of cell {t} °C / {r} against the log colour bar"
        extra = {(300, "0.20"): " s3.p35", (450, "0.20"): " s3.p35", (100, "0.65"): " s3.p34", (250, "0.94"): " s3.p35"}
        ev += extra.get((t, r), "")
        if lr is None:
            V(s_, "resistivity", "1000", "Ω cm", "measured", "electrical", ev + " s3.p34", fs=sid("f8_map"), censor=">dl",
              note="black cell = above the four-point-probe detection limit (order of 1000 Ω cm for 10 nm films); value is the limit")
        else:
            val = 10 ** lr
            V(s_, "resistivity", f"{val:.2g}" if val >= 0.01 else f"{val:.1g}", "Ω cm", "measured", "electrical", ev, fs=sid("f8_map"),
              note=f"read from the colour against the log bar: log10 = {lr:+.2f} (+-0.15)")

# 150 °C set and Fig 7a thickness at 140 cycles
F7T = {"0": 9.5, "0.20": 10.9, "0.50": 11.4, "0.65": 14.9, "0.80": 20.2, "0.94": 10.8}
for r, th in F7T.items():
    V(g(150, r), "film_thickness", f"{th}", "nm", "measured", "ellipsometry", f"fig7a; last marker (140 cycles) of curve {r}",
      fs=sid(f"f7a_{r.replace('.', '')}"), qual="position=planar", rel="at 140 cycles", note="read from the v1-checked points")
V("set150", "film_thickness", "", "nm", "measured", "ellipsometry", "fig6.cap s3.p22; 8-20 nm films for morphology", vmin="8", vmax="20",
  qual="position=planar")
V("grid", "film_thickness", "", "nm", "measured", "ellipsometry", "s3.p5; films mainly discussed are 10-20 nm thick, 100-140 cycles",
  vmin="10", vmax="20", qual="position=planar", note="approximate range stated for the films of the article")
RQ = {"0": "0.4", "0.20": "0.7", "0.50": "0.4", "0.65": "0.9", "0.80": "3.1", "0.94": "4.0"}
for r, rq in RQ.items():
    V(g(150, r), "other", rq, "nm", "measured", "afm", f"fig6 fig6.cap s3.p22; Rq printed on SEM image {r}", label="Rq (RMS roughness)",
      note="printed on the SEM tile, measured by AFM" + ("; 0.94 rougher than 0.80 here although text calls 0.80 the roughest across temperatures" if r == "0.94" else ""))
# crystallinity thresholds
V("grid", "other", "0.65", "", "measured", "raman", "s3.p4 fig1a; at 150 °C crystalline from ratio 0.65 (0-0.50 amorphous)",
  label="minimum H2 flow ratio for crystalline MoS2", fs=sid("f2_map"), regime="deposition_temperature = 150 °C")
V("grid", "other", "0.80", "", "measured", "raman", "s3.p7; at 100 °C ratio 0.80 needed", label="minimum H2 flow ratio for crystalline MoS2",
  fs=sid("f2_map"), regime="deposition_temperature = 100 °C")
V("grid", "other", "0.20", "", "measured", "raman", "s3.p7; at 300 °C and above even 0.20 crystallises",
  label="minimum H2 flow ratio for crystalline MoS2", fs=sid("f2_map"), regime="deposition_temperature >= 300 °C",
  note="lowest ratio tested at those temperatures")
# composition ranges
V("grid_c", "composition", "", "", "measured", "xps", "s3.p11; majority of crystalline films between MoS1.8 and MoS2.3",
  label="XPS S/Mo ratio", qual="element=S", vmin="1.8", vmax="2.3", fs=sid("f4_map"))
V("grid_c", "composition", "", "", "measured", "xps", "s3.p39; c-MoS2 films MoS1.8 to MoS2.2 by XPS", label="XPS S/Mo ratio",
  qual="element=S", vmin="1.8", vmax="2.2", fs=sid("f4_map"), note="s3.p11 gives 2.3 as the upper end (300 °C / 0.20 cell prints 2.3)")
V("grid_a150", "composition", "", "", "measured", "xps", "s3.p11; amorphous films at 150 °C or above MoS2.5 to MoS3.6",
  label="XPS S/Mo ratio", qual="element=S", vmin="2.5", vmax="3.6", fs=sid("f4_map"))
V("grid", "composition", "2.2", "", "measured", "xps", "s4.p1; low-temperature crystalline MoS2.2 named in the conclusions",
  label="XPS S/Mo ratio", qual="element=S", note="no single run named; consistent with Fig. 4 cells of 2.1-2.2")
# XPS binding energies (150 °C)
for lab, be in (("Mo 3d5/2 BE, Mo(4-d)+", "228.9"), ("Mo 3d5/2 BE, Mo4+", "229.6"), ("Mo 3d5/2 BE, Mo5+", "231.1"), ("Mo 3d5/2 BE, Mo6+", "232.9")):
    V(g(150, "0.80"), "other", be, "eV", "fit", "xps", "s3.p16 fig5a; component positions of the 0.80 film", label=lab, fs=sid("f5a_080_fit"))
V("", "other", "229.3", "eV", "literature", "cited", "s3.p16; average literature BE for MoS2", label="Mo 3d5/2 BE, MoS2", cited="63",
  note="+-0.5 eV")
V("", "other", "232.7", "eV", "literature", "cited", "s3.p16; average literature BE for MoO3", label="Mo 3d5/2 BE, MoO3", cited="63",
  note="+-0.3 eV")
V(g(150, "0.80"), "other", "162.4", "eV", "fit", "xps", "s3.p17 fig5b; S2- doublet of the 0.80 film", label="S 2p3/2 BE, S2-",
  fs=sid("f5b_080_fit"))
V(g(150, "0.80"), "other", "-0.9", "eV", "fit", "xps", "s3.p17 fig5b; electron-rich S2- doublet about 0.9 eV below S2-",
  label="S 2p BE shift of electron-rich S2- doublet", fs=sid("f5b_080_fit"), note="approximate")
V(g(150, "0.50"), "other", "161.9", "eV", "fit", "xps", "s3.p18 fig5b; lower-BE doublet of the 0.50 film", label="S 2p3/2 BE, lower doublet",
  fs=sid("f5b_050_fit"))
V(g(150, "0.50"), "other", "163.1", "eV", "fit", "xps", "s3.p18 fig5b; higher-BE doublet of the 0.50 film", label="S 2p3/2 BE, higher doublet",
  fs=sid("f5b_050_fit"))
V(g(150, "0.50"), "other", "1", "", "fit", "xps", "s3.p18 s3.p20; the two S 2p doublets have about equal areas",
  label="S 2p area ratio higher/lower doublet", fs=sid("f5b_050_fit"), note="approximate; ratio grows for S-richer films")
# Table 1
TAB = {"020": (1, "3.7", "3.4", "3.2", "6.4", "0.5", "0.8", ("0.1", "0.2", "0.5", "0.2", "0.2")),
       "065": (2, "2.1", "2.1", "4.0", "11.7", "1.5", "0.5", ("0.1", "0.1", "0.9", "0.4", "0.1")),
       "080": (3, "1.8", "1.9", "3.1", "22", "1.0", "5", ("0.1", "0.1", "2", "0.3", "2"))}
for r, (i, rbs, xps, dens, h, n, o, u) in TAB.items():
    s_ = f"rbs{r}"
    V(s_, "composition", rbs, "", "measured", "rbs", f"tab1.r{i}c1 tab1.r{i}c0 s3.p21; RBS S/Mo, ratio 0.{r[1:]}", label="S/Mo ratio (RBS)",
      qual="element=S", fs=sid("tab1"), note=f"+-{u[0]}")
    V(s_, "composition", xps, "", "measured", "xps", f"tab1.r{i}c2 tab1.r{i}c0" + (" s3.p52" if r == "020" else "") +
      f"; XPS S/Mo, ratio 0.{r[1:]}", label="S/Mo ratio (XPS)", qual="element=S", fs=sid("tab1"),
      note=f"+-{u[1]}" + ("; s3.p52 calls the 150 °C / 0.20 plasma product a-MoS3.4" if r == "020" else ""))
    V(s_, "film_density", dens, "g/cm3", "calculated", "rbs", f"tab1.r{i}c3 tab1.r{i}c0 s3.p19 s5.p17; density, ratio 0.{r[1:]}",
      fs=sid("tab1"), rel="RBS areal atom density / SE thickness", note="low value for 0.80 linked to rough morphology (s3.p21)" if r == "080" else "")
    V(s_, "composition", h, "at.%", "measured", "rbs", f"tab1.r{i}c4 tab1.r{i}c0 s3.p21 s3.p39; H content by ERD, ratio 0.{r[1:]}",
      label="H (at. %)", qual="element=H", fs=sid("tab1"), note=f"+-{u[2]}; ERD" + ("; text rounds to 6" if r == "020" else "; text rounds to 12" if r == "065" else ""))
    V(s_, "composition", "7", "at.%", "measured", "rbs", f"tab1.r{i}c5 tab1.r{i}c0 s3.p19; C below detection limit", label="C (at. %)",
      qual="element=C", fs=sid("tab1"), censor="<dl", note="detection limit about 7 at.% on glassy carbon; value is the limit")
    V(s_, "composition", n, "at.%", "measured", "rbs", f"tab1.r{i}c6 tab1.r{i}c0 s3.p21; N content", label="N (at. %)", qual="element=N",
      fs=sid("tab1"), note=f"+-{u[3]}; text range 0.5-1.5 at.%")
    V(s_, "composition", o, "at.%", "measured", "rbs", f"tab1.r{i}c7 tab1.r{i}c0 s3.p21; O content", label="O (at. %)", qual="element=O",
      fs=sid("tab1"), note=f"+-{u[4]}" + ("; text: below 1 at.%" if r != "080" else "; text: 5 at.%, surface oxidation of rough film"))
V("", "film_density", "5.06", "g/cm3", "literature", "cited", "s3.p19; bulk MoS2 density", cited="66")
for r, mo in (("020", "0.6"), ("065", "1.6"), ("080", "2.2")):
    V(f"rbs{r}", "other", mo, "at/nm2/cycle", "calculated", "rbs", ("s3.p30" if r != "080" else "s3.p32") + "; Mo atoms deposited per cycle from RBS",
      label="Mo atoms deposited per cycle", fs=sid("tab1"), rel="RBS Mo areal density / number of cycles",
      note="the films are not named; assigned to the 150 °C RBS films (the only RBS films of the paper)")
V("rbs065", "other", "6e21", "cm-3", "calculated", "calculation", "s3.p39; 12 at.% H converted to an H atom density",
  label="H atom density", fs=sid("tab1"), rel="H at.% x atom density")
V("rbs065", "other", "2e21", "cm-3", "calculated", "electrical", "s3.p39; H density is three times the measured carrier density of this film",
  label="hole concentration", note="derived as 6e21/3; the Hall value itself is in the SI")
# single-sample text values
V("f1b_10c", "film_thickness", "0.9", "nm", "measured", "ellipsometry", "fig1b s3.p5; legend 10 cyc; about 1 nm with Raman modes visible",
  qual="position=planar", note="ex situ SE")
for c, th in ((20, "1.6"), (30, "2.6"), (50, "4.8")):
    V(f"f1b_{c}c", "film_thickness", th, "nm", "measured", "ellipsometry", f"fig1b fig1.cap; legend {c} cyc", qual="position=planar",
      note="ex situ SE")
V("wafer", "film_thickness", "5.1", "nm", "measured", "ellipsometry", "fig1c; mean printed above the map", fs=sid("f1c_map"),
  qual="position=planar", note="+-0.2 nm (standard deviation)")
V("wafer", "thickness_nonuniformity", "3.3", "%", "calculated", "ellipsometry", "fig1c s3.p6; sigma over the 4 inch wafer",
  fs=sid("f1c_map"), rel="standard deviation / mean")
V("pet", "film_thickness", "5", "nm", "measured", "ellipsometry", "fig1.cap s3.p6; approximately 5 nm", qual="position=planar",
  note="approximate; method of thickness not stated")
V("pet", "resistivity", "0.3", "Ω cm", "measured", "electrical", "s3.p6; resistivity of film on PET, unchanged after repeated bending",
  note="transparent film")
V("fet100", "film_thickness", "5", "nm", "measured", "tem", "s3.p8 s3.p43 s5.p18; sub-5 nm / approximately 5 nm", censor="<",
  qual="position=planar", note="text: below 5 nm (s3.p8), approximately 5 nm (s3.p43, s5.p18)")
V("fet100", "other", "", "", "measured", "tem", "s3.p9 fig3; 4-5 monolayers thick nanocrystallites", label="number of MoS2 monolayers",
  fs=sid("f3a_tem"), vmin="4", vmax="5")
V("fet100", "other", "", "nm", "measured", "tem", "s3.p9 fig3; crystallites about 5-10 nm wide", label="nanocrystallite width",
  fs=sid("f3a_tem"), vmin="5", vmax="10")
V("fet100", "other", "0.75", "nm", "measured", "afm", "s3.p10; RMS roughness of the 100 °C film", label="Rq (RMS roughness)")
V("fet350", "other", "", "", "measured", "tem", "s3.p10 fig3; 5-6 monolayer film", label="number of MoS2 monolayers", fs=sid("f3b_tem"),
  vmin="5", vmax="6")
V("fet350", "film_thickness", "5", "nm", "measured", "tem", "s3.p43 s5.p18; similar thickness to the 100 °C film, ~5 nm", qual="position=planar",
  note="approximate")
for s_ in ("fet100", "fet350"):
    V(s_, "other", "", "", "measured", "electrical", "s3.p43; current on/off ratio of the FET about 3-4", label="FET on/off current ratio",
      vmin="3", vmax="4", note="p-type conduction; curves in SI Fig. S13")
V("fet100", "other", "10", "", "measured", "electrical", "s3.p43; output current more than an order of magnitude above the 350 °C FET",
  label="output current ratio 100 °C FET / 350 °C FET", censor=">")
V("fet100", "other", "", "nm", "measured", "tem", "s3.p44; amorphous interface layer between MoS2 and Ni about 2-3 nm",
  label="contact interface layer thickness", vmin="2", vmax="3", note="non-linear I-V (Schottky-like) contacts; TEM in SI")
V("fet350", "other", "1", "nm", "measured", "tem", "s3.p44; interface layer about 1 nm", label="contact interface layer thickness",
  note="contacts close to Ohmic")
V("tem065", "film_thickness", "50", "nm", "measured", "tem", "fig6.cap s3.p26 s5.p18; ~50 nm film", fs=sid("f6b_tem"), qual="position=planar",
  note="approximate")
V("tem065", "other", "5", "nm", "measured", "tem", "s3.p26 fig6; first ~5 nm with layers parallel to the substrate, random above",
  label="thickness of substrate-parallel layer", fs=sid("f6b_tem"), note="approximate")
V("dep100", "other", "150", "°C", "measured", "xps", "s3.p44; films from 100 °C begin to oxidise when annealed in air at 150 °C",
  label="air-anneal oxidation onset", note="details in SI Sections S11-S12; method not stated")
V("grid_c", "other", "300", "°C", "measured", "electrical", "s3.p40; no major change of electrical properties on annealing up to 300 °C",
  label="anneal temperature without electrical change", censor="", vmax="300", note="SI Section S12; films not named")
# resistivity / Hall summaries
V("grid_c080", "resistivity", "", "Ω cm", "measured", "electrical", "s3.p35 s4.p1; lowest c-MoS2 resistivities 0.1-1 Ω cm at ratio 0.80",
  vmin="0.1", vmax="1", fs=sid("f8_map"), note="order of magnitude; lowest at 100-150 °C; Fig. 8 cells at 300-450 °C are higher")
V("grid_094", "resistivity", "0.004", "Ω cm", "measured", "electrical", "s3.p35; as low as 4 mΩ cm at ratio 0.94", fs=sid("f8_map"),
  rel="lowest value", note="printed 4 mΩ cm; attributed to metallic Mo phase")
V("grid", "other", "1000", "Ω cm", "measured", "electrical", "s3.p34; four-point probe detection limit for 10 nm films",
  label="resistivity detection limit", note="order of magnitude; S/Mo >= 3 films exceed it")
V("hall_lowT", "other", "", "cm2 V-1 s-1", "measured", "electrical", "s3.p36; Hall mobility 0.001-0.01", label="Hall mobility",
  vmin="0.001", vmax="0.01", note="order of magnitude; SI Section S10")
V("hall_lowT", "other", "1e21", "cm-3", "measured", "electrical", "s3.p36 s4.p2; hole concentration on the order of 1e21",
  label="hole concentration", note="p-type; order of magnitude")
V("hall_ref", "other", "", "cm-3", "measured", "electrical", "s3.p37; carrier density 1e17 to 1e18", label="hole concentration",
  vmin="1e17", vmax="1e18")
V("hall_ref", "other", "0.01", "cm2 V-1 s-1", "measured", "electrical", "s3.p37; mobility on the order of 0.01", label="Hall mobility",
  note="order of magnitude")
V("", "other", "0.01", "cm2 V-1 s-1", "literature", "cited", "s3.p37; comparable mobility of reference films by Vandalon et al.",
  label="Hall mobility", cited="69", note="order of magnitude")
V("", "other", "10", "at.%", "literature", "cited", "s3.p37; Al doping of MoS2 at 450 °C with comparable carrier density",
  label="Al content of doped MoS2", cited="69", note="deposited at 450 °C")
V(g(450, "0.20"), "other", "1e17", "cm-3", "measured", "electrical", "s3.p38; 450 °C ratio 0.20", label="hole concentration",
  note="order of magnitude")
V(g(450, "0.80"), "other", "1e20", "cm-3", "measured", "electrical", "s3.p38; 450 °C ratio 0.80, three orders above 0.20",
  label="hole concentration", note="order of magnitude")
V("grid_094", "other", "1e22", "cm-3", "measured", "electrical", "s3.p38; ratio 0.94 gives order of 1e22", label="hole concentration",
  note="order of magnitude; partly metallic Mo")
V("", "other", "", "cm-3", "literature", "cited", "s3.p38; carrier concentration of Mo thin films", label="carrier concentration of Mo films",
  vmin="5e22", vmax="1e23", cited="70;71")
# H2 step and low-H2S experiments
V("h2plasma", "crystallinity", "crystalline", "", "measured", "raman", "s3.p52; extra H2 plasma removes excess S, c-MoS2",
  note="SI Table S8")
V("h2plasma", "composition", "2", "", "measured", "xps", "s3.p52; film becomes c-MoS2", label="S/Mo ratio", qual="element=S",
  note="named MoS2 in the text; exact value in SI")
V("h2gas", "crystallinity", "amorphous", "", "measured", "raman", "s3.p52; H2 gas step changes neither crystallinity nor stoichiometry")
V("h2gas", "composition", "3.4", "", "measured", "xps", "s3.p52; stays a-MoS3.4 like the plain 0.20 process", label="S/Mo ratio",
  qual="element=S", note="text gives the 0.20 / 150 °C product as MoS3.4; H2 gas did not change it")
V("lowH2S_250", "crystallinity", "crystalline", "", "measured", "raman", "s3.p53; reduced H2S flow gives crystalline film at 250 °C without H2")
V("lowH2S_150", "crystallinity", "amorphous", "", "measured", "raman", "s3.p53; at 150 °C H2 still needed for c-MoS2",
  note="inferred from 'addition of H2 was necessary'")
# other TMDCs
V("ws2_000", "composition", "4.0", "", "measured", "xps", "s3.p46; WS4.0 by XPS", label="S/W ratio", qual="element=S")
V("ws2_000", "crystallinity", "amorphous", "", "measured", "raman", "s3.p46 fig9a; amorphous, highly resistive", fs=sid("f9a_000"))
V("ws2_080", "composition", "2.1", "", "measured", "xps", "s3.p46; WS2.1 by XPS", label="S/W ratio", qual="element=S",
  note="conclusions (s4.p1) say WS2.2")
V("ws2_080", "composition", "2.2", "", "measured", "xps", "s4.p1; conclusions name WS2.2", label="S/W ratio", qual="element=S",
  note="conflicts with WS2.1 in s3.p46")
V("ws2_080", "crystallinity", "crystalline", "", "measured", "raman", "s3.p46 fig9a; crystalline WS2", fs=sid("f9a_080"))
V("ws2_080", "resistivity", "4", "Ω cm", "measured", "electrical", "s3.p46; 4 Ω cm")
V("tis2_050", "crystallinity", "crystalline", "", "measured", "raman", "s3.p48 fig9b; improved crystallinity over the thermal process",
  fs=sid("f9b_050"))
V("tis2_050", "composition", "2.2", "", "measured", "xps", "s4.p1; conclusions name TiS2.2", label="S/Ti ratio", qual="element=S",
  note="stoichiometry table in SI (Table S7); method assumed XPS")
V("tis2_080", "composition", "", "", "measured", "xps", "s3.p48; S-poor films at ratio 0.80 (not shown)", label="S/Ti ratio", qual="element=S",
  censor="<", vmax="2", note="only 'S-poor' stated; upper bound 2 is the stoichiometric ratio")
V("tis2_thermal", "crystallinity", "crystalline", "", "measured", "raman", "fig9b s3.p48; weak TiS2 modes", fs=sid("f9b_thermal"),
  note="poorer than the 0.50 PEALD film")
# literature numbers quoted as comparisons
V("", "deposition_temperature", "300", "°C", "literature", "cited", "s3.p46 s2.p9; lowest crystalline WS2 temperature of the earlier process",
  qual="kind=set_point", cited="52;67;79")
V("", "deposition_temperature", "150", "°C", "literature", "cited", "s3.p48 s2.p9; earlier TiS2 PEALD crystalline from 150 °C, a-TiS3 at 100 °C",
  qual="kind=set_point", cited="53")
V("", "deposition_temperature", "100", "°C", "literature", "cited", "s3.p48; thermal TiS2 with Ti(NMe2)4 crystalline down to 100 °C",
  qual="kind=set_point", cited="80;81")
V("", "deposition_temperature", "300", "°C", "literature", "cited", "s2.p9 s3.p31; earlier MoS2/WS2 PEALD good at 300 °C and above",
  qual="kind=set_point", cited="36;52", note="lower bound")
V("", "gas_flow_rate", "8", "sccm", "literature", "cited", "s5.p4; Sharma et al. H2S flow (corrected)", qual="step=plasma;gas=H2S", cited="36",
  note="ref 36 printed the flows swapped; ratio 0.20")
V("", "gas_flow_rate", "2", "sccm", "literature", "cited", "s5.p4; Sharma et al. H2 flow (corrected)", qual="step=plasma;gas=H2", cited="36")

# ------------------------------------------------------------------ write tables
T["paper"].append(dict(paper_id=PID, year="2022", topic="PEALD of MoS2 (and WS2, TiS2) at 50-450 °C with H2 added to an H2S/Ar plasma; "
                                                        "outside conformality"))
# body copies of captions (s3.x1-x7, same text as the caption elements): cited wherever the caption is cited
XCAP = {"fig2.cap": "s3.x1", "fig4.cap": "s3.x2", "fig5.cap": "s3.x3", "tab1.cap": "s3.x4", "fig6.cap": "s3.x5", "fig7.cap": "s3.x6",
        "fig9.cap": "s3.x7"}
for t in ("sample", "condition", "series", "value"):
    for r in T[t]:
        ids, _, loc = r["evidence"].partition(";")
        ids = ids.split()
        ids += [XCAP[i] for i in ids if i in XCAP and XCAP[i] not in ids]
        r["evidence"] = " ".join(ids) + ";" + loc
for t, cols in COLS.items():
    with open(HERE / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(T[t])

# ------------------------------------------------------------------ coverage
inv = list(csv.DictReader(open(HERE / "inventory.csv", encoding="utf-8")))
cite = {e["element_id"]: [] for e in inv}
for t, k in (("sample", "sample_id"), ("condition", "condition_id"), ("series", "series_id"), ("value", "value_id")):
    for r in T[t]:
        ids = r["evidence"].split(";")[0].split()
        for i in ids:
            assert i in cite, (r[k], i)
            cite[i].append(r[k])
NK = {}
for e in inv:
    i = e["element_id"]
    if i.startswith("abs."):
        NK[i] = "abstract (check only: nothing new against the body)"
    elif i in ("s1.h", "s2.h", "s3.h", "s4.h", "s5.h", "s6.h", "s7.h"):
        NK[i] = "heading"
    elif i in ("s1.p1", "s7.p3", "s7.p4", "s7.p5", "s7.p6", "s7.p7", "s7.p8", "s7.p9", "s7.p2"):
        NK[i] = "author list / affiliations"
    elif i in ("s1.p2", "s1.p3", "s1.p4", "s1.p5", "s1.p6", "s1.p7", "s2.p5", "s2.p6", "s2.p7", "s7.p1", "s7.p10", "s7.p11"):
        NK[i] = "publisher front matter / dates / notes"
    elif i == "s1.p8":
        NK[i] = "duplicate of the abstract (check only)"
    elif i == "s7.p12":
        NK[i] = "acknowledgement"
    elif i in ("s2.p1", "s2.p2", "s2.p3", "s2.p4", "s2.p8", "s2.p10", "s2.p11"):
        NK[i] = "background / introduction (literature context and aims; numbers are not results of this paper)"
    elif i in ("s3.p2", "s3.p3"):
        NK[i] = "definition text (H2 flow ratio defined by eq1; carried by the ratio conditions)"
    elif i in ("s3.p23", "s3.p24", "s3.p25", "s3.p41", "s3.p42", "s3.p47", "s3.p49", "s3.p50"):
        NK[i] = "discussion / mechanism without values of this paper (citations, interpretation)"
    elif i == "s3.p12":
        NK[i] = "continuation of interpretation (plasma vs surface chemistry), no values"
    elif i in ("s3.p31",):
        NK[i] = "interpretation; cited earlier result"
    else:
        NK[i] = ""
with open(HERE / "coverage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["element_id", "status", "rows", "reason"])
    for e in inv:
        i = e["element_id"]
        if cite[i]:
            w.writerow([i, "covered", ";".join(cite[i]), ""])
        else:
            w.writerow([i, "no knowledge", "", NK[i] or "UNASSIGNED"])
print({t: len(v) for t, v in T.items()})
