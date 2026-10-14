#!/usr/bin/env python3
"""Fresh v2 extraction of 10.1039_d0cp03358h (key yim20): writes paper/sample/condition/series/value/coverage CSVs here.

    python3 psed_v2/schema_pilot/v2/10.1039_d0cp03358h/build.py

Everything is typed below by hand from the element texts, the table and figure images; points come from
cases/points.json and the accepted v1 points (schema_pilot/v1_points.json, v1_points_check.csv)."""
import csv, json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent.parent
V2 = PILOT.parent
PID, K = "10.1039_d0cp03358h", "yim20"
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
s_ = lambda x: f"{K}:{x}"

# ---------------------------------------------------------------- Table 1 as read (columns checked against the page image)
# value columns c7..c15 = S_I, S_IIb, S_I/N, S_IIb/N, x50% (um), x~50%, slope d(S/N)/dx~ (nm), slope dtheta/dx~, R^2
TAB1 = {  # sample: (table rows, series letters, sequence, H nm, layout, N, magnification, values c7..c15)
    1: ([1], "A", "0.1-4.0-0.1-4.0", 500, "v1a", 500, 50, ["49.8", "53.3", "0.100", "0.107", "140", "280", "-0.0013", "-0.013", "0.983"]),
    2: ([2], "A", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 50, ["49.6", "54.5", "0.0993", "0.109", "140", "280", "-0.0013", "-0.011", "0.991"]),
    3: ([3], "A", "0.1-4.0-0.1-4.0", 500, "v2a", 500, 50, ["50.5", "53.4", "0.101", "0.107", "110", "220", "-0.0018", "-0.018", "0.997"]),
    4: ([4], "B", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 50, ["47.4", "47.8", "0.0949", "0.0956", "105", "208", "-0.0018", "-0.019", "0.993"]),
    5: ([5], "B", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 10, ["49.1", "50.0", "0.0983", "0.100", "103", "208", "-0.0015", "-0.015", "0.998"]),
    6: ([6], "B", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 5, ["51.4", "52.9", "0.103", "0.106", "109", "214", "-0.00087", "-0.0083", "0.998"]),
    7: ([7], "C", "0.1-4.0-0.1-4.0", 100, "v1b", 500, 50, [None, "47.8", None, "0.0955", "10", "100", "-0.00048", "-0.0050", "0.995"]),
    8: ([8, 11], "CD", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 50, ["46.7", "51.1", "0.0934", "0.102", "106", "214", "-0.0020", "-0.019", "0.993"]),
    9: ([9], "C", "0.1-4.0-0.1-4.0", 2000, "v1b", 500, 50, ["45.3", "48.8", "0.0906", "0.0976", "375", "188", "-0.0046", "-0.047", "0.995"]),
    10: ([10], "D", "0.1-4.0-0.1-4.0", 500, "v1b", 250, 50, ["24.3", "26.0", "0.0970", "0.104", "115", "230", "-0.0022", "-0.021", "0.982"]),
    11: ([12], "D", "0.1-4.0-0.1-4.0", 500, "v1b", 1000, 50, ["94.7", "99.3", "0.0947", "0.0993", "95", "190", "-0.00099", "-0.010", "0.996"]),
    12: ([13, 17], "EF", "0.1-4.0-0.1-4.0", 500, "v1b", 500, 50, ["47.5", "50.2", "0.0951", "0.100", "96", "192", "-0.0021", "-0.021", "0.971"]),
    13: ([14], "E", "0.2-4.0-0.1-4.0", 500, "v1b", 500, 50, ["48.2", "49.8", "0.0962", "0.100", "133", "266", "-0.0014", "-0.014", "0.996"]),
    14: ([15], "E", "0.4-4.0-0.1-4.0", 500, "v2a", 500, 50, ["48.6", "51.0", "0.0972", "0.102", "197", "386", "-0.00045", "-0.0044", "0.996"]),
    15: ([16], "F", "0.1-1.0-0.1-1.0", 500, "v1b", 500, 50, ["50.4", "51.9", "0.101", "0.104", "99", "198", "-0.0017", "-0.016", "0.983"]),
    16: ([18], "F", "0.1-10.0-0.1-10.0", 500, "v1b", 500, 50, ["44.8", "48.9", "0.0897", "0.0978", "109", "218", "-0.0017", "-0.018", "0.999"]),
}
cells = lambda n, c: ", ".join(f"tab1.r{r}c{c}" for r in TAB1[n][0])
ALL16 = [s_(f"S{n}") for n in range(1, 17)]
H500 = [s_(f"S{n}") for n in TAB1 if TAB1[n][3] == 500] + [s_("SX")]

# ---------------------------------------------------------------- samples
def sample(sid, kind, label="u", parent="", members="", dims="", width="H", note="", ev="", material="Al2O3", precursor="TMA",
           coreactant="H2O", mode="thermal", reactor="Picosun R-150", sclass="lateral channel (PillarHall-3)"):
    if kind == "group":
        material = precursor = coreactant = mode = reactor = sclass = ""
        width = width if dims else "none"
    T["sample"].append(dict(sample_id=s_(sid), paper_id=PID, kind=kind, label_as_printed=label, parent_sample=parent and s_(parent),
                            members=";".join(members), material=material, precursor=precursor, coreactant=coreactant,
                            process_mode=mode, reactor=reactor, structure_class=sclass, structure_dims=dims, width_kind=width,
                            note=note, evidence=ev))

sample("runA", "run", note="the single ALD run in which samples 1-3 (one wafer, three pillar layouts) were coated",
       dims="H 500 nm design; one wafer with layouts v1a, v1b, v2a", ev="s6.p2; Methods, Series A grown in one run on one wafer")
for n, (rows, ser, seq, H, lay, N, mag, vals) in TAB1.items():
    note = f"Table 1 sample code {n} (traceable codes in ESI Table S3); Series {', '.join(ser)}"
    ev = f"{cells(n, 1)}, {cells(n, 3)}, {cells(n, 4)}; Table 1 sample {n} code, design height, pillar layout"
    if n == 7:
        note += "; thickness outside the channel (Region I) not measured for the 100 nm design"
        ev = f"tab1.r7c1, tab1.r7c3, tab1.r7c4, tab1.r7c7, tab1.r7c9, s3.p9; Table 1 sample 7 code, height, layout, dashes for Region I (footnote e)"
    if n in (8, 12):
        note += f"; listed twice in Table 1 (rows {rows[0]} and {rows[1]}) as the shared member of two series"
    sample(f"S{n}", "piece", label=str(n), parent="runA" if n <= 3 else "",
           dims=f"H {H} nm design; pillar layout {lay}; chip with channels of L 0.1 to 5 mm", note=note, ev=ev.replace(";", ", s20.p3;", 1) + "; channel lengths from conclusions")
sample("SX", "piece", dims="H 500 nm design", note="AFM sample of Fig. 6; its details are only in ESI Table S4; not one of the Table 1 samples",
       ev="fig6.cap; Fig. 6 caption, AFM sample with details in the supplement")
for L in ("0.1", "0.5", "1", "5"):
    sample(f"S8-L{L}", "channel", label=f"L {L} mm", parent="S8", dims=f"H 500 nm design; pillar layout v1b; L {L} mm",
           note="channel of sample 8 scanned repeatedly (Fig. 8a legend)", ev="fig8a, s7.p5; Fig. 8a legend lateral length; Methods, repeats on each lateral length")
GROUPS = {
    "serA": (["S1", "S2", "S3"], "Series A: pillar layout varied (v1a, v1b, v2a), one ALD run", "tab1.r1c0, tab1.r2c0, tab1.r3c0, s3.p9, s6.p2; Table 1 Series A column and footnote a"),
    "serB": (["S4", "S5", "S6"], "Series B: reflectometer magnification varied (x50, x10, x5); L 5 mm channel data used", "tab1.r4c0, tab1.r5c0, tab1.r6c0, s3.p9, s7.p5; Table 1 Series B and footnotes a, f"),
    "serC": (["S7", "S8", "S9"], "Series C: design channel height varied (100, 500, 2000 nm)", "tab1.r7c0, tab1.r8c0, tab1.r9c0, s3.p9; Table 1 Series C and footnote a"),
    "serD": (["S10", "S8", "S11"], "Series D: ALD cycles varied (250, 500, 1000)", "tab1.r10c0, tab1.r11c0, tab1.r12c0, s3.p9; Table 1 Series D and footnote a"),
    "serE": (["S12", "S13", "S14"], "Series E: TMA pulse time varied (0.1, 0.2, 0.4 s); S14 uses layout v2a", "tab1.r13c0, tab1.r14c0, tab1.r15c0, s3.p9; Table 1 Series E and footnote a"),
    "serF": (["S15", "S12", "S16"], "Series F: both purge times varied (1, 4, 10 s); GPC drops and PD50% rises slightly with longer purge, "
             "GPC outside the channel drops faster than inside (attributed to reversible water adsorption and re-adsorption in the channel)",
             "tab1.r16c0, tab1.r17c0, tab1.r18c0, s3.p9, s14.x1, s18.p2, s18.p4, s18.p5, s18.p6; Table 1 Series F; results text on Fig. 11b; purge-time discussion"),
    "tab1": ([f"S{n}" for n in range(1, 17)], "all samples of Table 1 (reflectometer line scans)", "tab1.cap; Table 1 caption"),
    "all_exp": ([f"S{n}" for n in range(1, 17)] + ["SX"], "every experimental sample of the paper (Table 1 samples and the AFM sample)", "s6.p1, fig6.cap; Methods ALD; Fig. 6 caption"),
    "H500": ([x.split(":")[1] for x in H500], "samples on 500 nm design channels; the authors judge H 500 nm with layout v1b the most reliable design",
             "s16.p6, s5.p2; Discussion, most reliable design; Methods, 500 nm channels"),
    "H100": (["S7"], "samples on 100 nm design channels (only sample 7)", "tab1.r7c3; Table 1 design height 100 nm"),
    "H2000": (["S9"], "samples on 2000 nm design channels (only sample 9)", "tab1.r9c3; Table 1 design height 2000 nm"),
    "repro": (["S2", "S4", "S8", "S12"], "samples 2, 4, 8, 12: nominally identical runs used for reproducibility and for the c_TMA average",
              "s16.p10, s18.p3, fig8b; Discussion reproducibility set; Table 2 footnote f; Fig. 8b legend"),
}
for g, (m, note, ev) in GROUPS.items():
    sample(g, "group", members=[s_(x) for x in m], note=note, ev=ev)

# model runs (Fig. 10)
MH = [100, 200, 500, 1000, 2000]
MN = [100, 250, 500, 1000, 2000]
def mid(h=500, n=500):
    return "M-H500" if (h, n) == (500, 500) else (f"M-H{h}" if n == 500 else f"M-N{n}")
for h in MH:
    sample(mid(h), "model_run", label=f"{h} nm" + (" / 500 cycles" if h == 500 else ""), dims=f"H {h} nm", reactor="",
           sclass="lateral channel (model, no pillars)", note="Ylilammi diffusion-reaction model (MATLAB re-implementation)"
           + ("; the same run is assumed to serve as '500 nm' in panels a-c and '500 cycles' in panels d-f (identical inputs)" if h == 500 else ""),
           ev="fig10.cap, fig10a; Fig. 10 caption and panel a legend")
for n in MN:
    if n != 500:
        sample(mid(n=n), "model_run", label=f"{n} cycles", dims="H 500 nm", reactor="", sclass="lateral channel (model, no pillars)",
               note="Ylilammi diffusion-reaction model (MATLAB re-implementation)", ev="fig10.cap, fig10d; Fig. 10 caption and panel d legend")
sample("MG-H", "group", members=[s_(mid(h)) for h in MH], note="simulated channel-height series, 500 cycles", ev="fig10.cap; Fig. 10 top row")
sample("MG-N", "group", members=[s_(mid(n=n)) for n in MN], note="simulated cycle series, H 500 nm", ev="fig10.cap; Fig. 10 bottom row")
sample("MG-all", "group", members=sorted({s_(mid(h)) for h in MH} | {s_(mid(n=n)) for n in MN}),
       note="all simulations; MATLAB ODE23 solver of the Ylilammi model with a lagged collision rate", ev="s8.p1, fig10.cap; Methods simulation; Fig. 10 parameters")

# literature reference samples (Table 2 and introduction)
REFS = {
    "ref31": ("Dendooven et al. 2009 (ref. 31)", "macroscopic rectangular LHAR", "H 100 um; max AR 200:1", "home-built", "tab2.r1c1, tab2.r1c2, tab2.r1c3, tab2.r1c5, tab2.r1c8, s2.p10; Table 2 row 1 structure and reactor; intro, macroscopic channels of hundreds of um"),
    "ref41": ("Schwille et al. 2016 (ref. 41)", "microscopic centrosymmetric LHAR cavity", "H 4.5 um (limiting gap); max AR ~100:1 (order of magnitude); footnote: cavity 5 um high, 2000 um long, single access hole 4-100 um across",
              "single-wafer cross-flow hot-wall reactor", "tab2.r2c1, tab2.r2c2, tab2.r2c3, tab2.r2c5, tab2.r2c8, s18.p3, s2.p10; Table 2 row 2 and footnote a; intro, 4.5 um gap"),
    "ref60": ("Vandalon et al. 2016 (ref. 60)", "planar Si(100) wafer, no LHAR", "planar", "home-built", "tab2.r3c1, tab2.r3c2, tab2.r3c3, tab2.r3c5, tab2.r3c8, s18.p3; Table 2 row 3 and footnote c"),
    "vandalon2017": ("Vandalon et al. 2017 (follow-up of ref. 60, not numbered)", "planar", "planar", "", "s18.p3; Table 2 footnote d, follow-up work"),
    "ref33": ("Ylilammi et al. 2018 (ref. 33)", "microscopic rectangular PillarHall-3", "H 0.50 um; max AR 2000:1", "Picosun R-150", "tab2.r4c1, tab2.r4c2, tab2.r4c3, tab2.r4c5, tab2.r4c8; Table 2 row 4"),
    "ref36": ("Arts et al. 2019 (ref. 36)", "microscopic rectangular PillarHall-3", "H 0.50 um; max AR 10 000:1", "Oxford Instruments OpAL", "tab2.r5c1, tab2.r5c2, tab2.r5c3, tab2.r5c5, tab2.r6c5, tab2.r5c8; Table 2 row 5 (reactor name split over two parsed rows)"),
    "ref40": ("Gao et al. (ref. 40), PillarHall-1", "microscopic LHAR cavity (PillarHall-1: Si bottom, polysilicon roof, SiO2 pillars)", "design cavity height 200, 500 or 1000 nm; AR above 10 000:1", "", "s2.p10, s5.p1; intro, PillarHall-1 description; Methods, process modified from it"),
}
for r, (lab, sc, dims, reac, ev) in REFS.items():
    w = "none" if dims == "planar" else "H"
    sample(r, "reference", label=lab, dims=dims, width=w, reactor=reac, sclass=sc, mode="thermal",
           precursor="TMA" if r != "ref40" else "TMA; TiCl4", coreactant="H2O", material="Al2O3" if r != "ref40" else "Al2O3; TiO2",
           note="literature work quoted by this paper", ev=ev)

# ---------------------------------------------------------------- conditions
def cond(sid, kind, q, label, quals, value, unit, ev, dk="stated", note="", when=""):
    T["condition"].append(dict(condition_id=f"{K}:c{len(T['condition']) + 1:03d}", sample_id=s_(sid), kind=kind, quantity=q,
                               label_as_printed=label, qualifiers=quals, value=value, unit=unit, data_kind=dk, applies_when=when,
                               note=note, evidence=ev))

cond("all_exp", "process", "deposition_temperature", "ALD temperature", "kind=set_point", "300", "°C",
     "s6.p1, tab1.cap, s2.p13, fig4.cap, fig6.cap, fig9.cap, fig11.cap, s20.p1; Methods ALD temperature; Table 1 and figure captions")
cond("all_exp", "process", "process_pressure", "process pressure", "", "300", "Pa", "s6.p1, s12.p1; Methods, pressure ca. 3 hPa",
     note="printed ca. 3 hPa")
cond("all_exp", "process", "carrier_gas", "carrier and purge gas", "", "N2", "", "s6.p1; Methods, carrier and purge gas",
     note="through four reactant lines")
cond("all_exp", "process", "precursor_purity", "nitrogen purity", "species=N2", "6.0", "", "s6.p1; Methods, nitrogen grade")
cond("all_exp", "process", "gas_flow_rate", "carrier flow", "gas=N2", "150", "sccm", "s6.p1; Methods, constant nitrogen flow")
cond("all_exp", "process", "other", "target film thickness", "", "50", "nm", "s6.p1, s16.p8; Methods, typical target ca. 50 nm; Discussion, film of ca. 50 nm",
     note="typical target, ca.; made in 500 cycles")
cond("all_exp", "process", "reactor_type", "ALD reactor", "", "Picosun R-150", "", "s6.p1, tab2.r7c5; Methods reactor; Table 2 this-work reactor")
cond("all_exp", "substrate_prep", "substrate", "starting substrate", "", "Si(100) wafer, 150 mm, low-doped", "", "s5.p1; Methods, starting wafers")
cond("all_exp", "substrate_prep", "other", "channel-defining layer", "", "thermal SiO2 grown to the channel height, removed by HF vapour etch", "",
     "s5.p1; Methods, oxide to target H and HF vapour release", note="furnaces Centrotherm E1200 HT 260-4; etcher Primaxx MEMS-CET")
cond("all_exp", "substrate_prep", "other", "membrane", "", "polysilicon from SiH4, several steps; plug-up process", "", "s5.p1; Methods, membrane deposition",
     note="lithography: SUSS MA150 contact aligner and Canon FPA3000-i4 stepper")
cond("all_exp", "substrate_prep", "other", "chip size", "", "15 x 20", "mm", "s5.p1; Methods, optional dicing", note="dicing optional")
cond("all_exp", "measurement", "other", "top membrane removal before analysis", "", "adhesive tape", "", "s7.p1, fig6.cap; Methods, membrane peeled off",
     note="unless stated otherwise; optical microscopy before and after peeling")
# per-sample Table 1 conditions
for n, (rows, ser, seq, H, lay, N, mag, vals) in TAB1.items():
    a, pa, b, pb = seq.split("-")
    ev = f"{cells(n, 2)}; Table 1 sample {n} pulse-purge sequence"
    cond(f"S{n}", "process", "pulse_time", "TMA pulse", "step=reactant_A;species=TMA", a, "s", ev)
    cond(f"S{n}", "process", "purge_time", "purge after TMA", "step=purge_A", pa, "s", ev)
    cond(f"S{n}", "process", "pulse_time", "water pulse", "step=reactant_B;species=H2O", b, "s", ev)
    cond(f"S{n}", "process", "purge_time", "purge after water", "step=purge_B", pb, "s", ev)
    cond(f"S{n}", "process", "cycle_number", "ALD cycles N", "", str(N), "", f"{cells(n, 5)}" + (", fig5.cap" if n == 11 else "") + (", s13.p1" if n in (8, 10, 11) else "") + f"; Table 1 sample {n} cycles")
    cond(f"S{n}", "measurement", "other", "reflectometer magnification", "", str(mag), "", f"{cells(n, 6)}; Table 1 sample {n} objective")
    spot = {50: "5-6", 10: "25", 5: "50"}[mag]
    cond(f"S{n}", "measurement", "probe_resolution", "estimated spot size", "", spot, "µm",
         f"{cells(n, 6)}, s7.p5" + (", s11.x1" if n in (4, 5, 6) else "") + f"; spot size of the x{mag} objective stated in Methods"
         + ("; results text on Fig. 7" if n in (4, 5, 6) else ""),
         note="estimated by the authors" + ("; x50 chosen as smaller than the ca. 30 um front width" if mag == 50 else ""))
cond("serB", "measurement", "other", "channel length used for Table 1 values", "", "5", "mm", "s7.p5, s3.p9; Methods and footnote f, L 5 mm data for Series B",
     note="footnote f prints 5 nm, a misprint for 5 mm")
cond("tab1", "measurement", "other", "Table 1 values averaged over channels", "", "L 0.1 to 5 mm channels, scanned several times, outliers excluded", "",
     "s7.p5, s3.p9, tab1.r0c3; Methods, averaging; footnote f (prints nm for mm)", note="not for Series B (5 mm only)")
cond("tab1", "measurement", "other", "reflectometer", "", "FilmTek 2000M", "", "s7.p5; Methods, instrument")
cond("tab1", "measurement", "other", "wavelength range", "", "380-800", "nm", "s7.p5; Methods, reflectometer wavelengths")
cond("tab1", "measurement", "other", "scan start before channel entry", "", "13", "µm", "s7.p5; Methods, scan starts in Region I", note="ca.")
cond("tab1", "measurement", "other", "scan length", "", "198 or 398", "µm", "s7.p5; Methods, total scan length")
cond("tab1", "measurement", "other", "scan step", "", "2", "µm", "s7.p5; Methods, step")
cond("tab1", "measurement", "other", "points per scan", "", "100-200", "", "s7.p5; Methods, number of points")
cond("tab1", "measurement", "other", "scan direction to channel entry", "", "90", "deg", "s16.p7; Discussion, perpendicular scan placement",
     note="samples placed by hand at the entry seen in the microscope")
cond("tab1", "measurement", "other", "optical model", "", "roughness-free dielectric film with ALD Al2O3 (300 °C) properties on Si", "",
     "s16.p7, s3.p9; Discussion, optical model; footnote c, native oxide included")
cond("S11", "measurement", "other", "SEM-EDS instrument", "", "Tescan Mira3 with Thermo Scientific EDS", "", "s7.p2; Methods, SEM-EDS")
cond("S11", "measurement", "other", "accelerating voltage", "", "5", "kV", "s7.p2, s10.x2; Methods, line scan voltage; results text on Fig. 5",
     note="interaction volume exceeds the film, so Si is seen throughout")
cond("S11", "measurement", "other", "EDS line length", "", "500", "µm", "s7.p3; Methods, line length")
cond("S11", "measurement", "other", "EDS point spacing", "", "1", "µm", "s7.p3; Methods, interval")
cond("S11", "measurement", "other", "EDS scans averaged", "", "5", "", "s7.p3; Methods, average of five; outliers at pillars and edges removed")
cond("S11", "substrate_prep", "other", "storage before SEM", "", "ambient air, no anti-charging preparation", "", "s7.p2, s7.p3; Methods, sample stored in air")
cond("SX", "process", "cycle_number", "ALD cycles", "", "500", "", "fig6.cap; Fig. 6 caption")
cond("SX", "measurement", "other", "AFM", "", "PSIA XE-100, non-contact mode, standard tips", "", "s7.p4; Methods, AFM")
cond("SX", "measurement", "other", "AFM scan area", "", "10x10 to 90x90", "µm", "s7.p4; Methods, AFM area range", note="Fig. 6 itself is 90 x 90 um")
cond("SX", "measurement", "other", "AFM resolution", "", "1024 x 256", "pixel", "s7.p4; Methods, AFM pixels", note="tilt and drift removed by line-wise first-order fit")
# model inputs that act as process settings
cond("MG-all", "process", "deposition_temperature", "T", "kind=set_point", "300", "°C", "fig10.cap; Fig. 10 parameters")
cond("MG-all", "process", "pulse_time", "t_p", "step=reactant_A;species=TMA", "0.10", "s", "fig10.cap; Fig. 10 parameters")
cond("MG-all", "process", "partial_pressure", "p_A0", "species=TMA", "65", "Pa", "fig10.cap; Fig. 10 parameters, input TMA pressure")
cond("MG-all", "process", "partial_pressure", "p_B", "species=N2", "300", "Pa", "fig10.cap; Fig. 10 parameters, carrier pressure")
for h in MH:
    cond(mid(h), "process", "cycle_number", "N", "", "500", "", "fig10.cap, fig10a; Fig. 10 top row, N 500")
for n in MN:
    if n != 500:
        cond(mid(n=n), "process", "cycle_number", "N", "", str(n), "", "fig10.cap, fig10d; Fig. 10 bottom row legend")
# literature conditions (Table 2)
LIT_T = {"ref31": ("200", "tab2.r1c0"), "ref41": ("200", "tab2.r2c0"), "ref60": ("100-300", "tab2.r3c0"), "ref33": ("300", "tab2.r4c0"), "ref36": ("275", "tab2.r5c0")}
for r, (v, c) in LIT_T.items():
    cond(r, "process", "deposition_temperature", "Temperature", "kind=set_point", v, "°C", f"{c}; Table 2 temperature", note="as quoted in Table 2")
for r, v, c in (("ref31", "150", "tab2.r1c4"), ("ref33", "500", "tab2.r4c4"), ("ref36", "400", "tab2.r5c4")):
    cond(r, "process", "cycle_number", "Number of cycles", "", v, "", f"{c}; Table 2 cycles", note="as quoted in Table 2")
for g, v_, ev in (("serA", "pillar layout", "s3.p9, s6.p2"), ("serB", "reflectometer magnification", "s3.p9"), ("serC", "design channel height", "s3.p9"),
                  ("serD", "ALD cycles", "s3.p9"), ("serE", "TMA pulse time", "s3.p9"), ("serF", "purge time (both purges)", "s3.p9"),
                  ("MG-H", "channel height H", "fig10.cap"), ("MG-N", "number of cycles N", "fig10.cap")):
    cond(g, "process", "other", "parameter varied in the series", "", v_, "", f"{ev}; footnote a of Table 1 or Fig. 10 caption, varied parameter")

# ---------------------------------------------------------------- series
v1 = json.load(open(PILOT / "v1_points.json", encoding="utf-8"))["series"]
cp = [s for s in json.load(open(V2 / "cases/points.json", encoding="utf-8"))["series"] if s["paper"] == PID and s["case"] == 9]
def cpts(fig, panel, start):
    return [s for s in cp if s["figure"] == fig and s["panel"] == panel and s["series"].startswith(start)][0]["points"]

def ser(sid, sample_id, kind, fig, panel, method, x=("", "", ""), y=("", "", ""), z=("", ""), dk="measured", link="stated",
        pts=None, src="", reused="", note="", ev=""):
    if pts is None and s_(sid) in v1:
        pts, src = v1[s_(sid)]["points"], "v1 checked"
    T["series"].append(dict(series_id=s_(sid), sample_id=s_(sample_id) if sample_id else "", kind=kind, figure=str(fig), panel=panel,
                            method=method, x_id=x[0], x_qualifiers=x[1], x_label=x[2], y_id=y[0], y_qualifiers=y[1], y_label=y[2],
                            z_id=z[0], z_label=z[1], data_kind=dk, link_status=link, points_source=src if pts else "",
                            points=json.dumps(pts) if pts else "", reused_from=reused and s_(reused), note=note, evidence=ev))

XD = ("distance", "origin=entrance", "Distance inside the channel x (µm)")
XT = ("dimensionless_distance", "by=H", "Dimensionless distance x~")
YS = ("film_thickness", "", "Film thickness S (nm)")
YG = ("growth_per_cycle", "position=local", "Thickness/cycles S/N (nm)")
YN = ("normalized_thickness", "reference=plateau", "Normalized thickness (-)")
ser("F1", "all_exp", "image", 1, "", "schematic", dk="schematic", link="inferred",
    note="LHAR channel before coating, after coating and after roof removal, side and top view; H height, L length; typical LHAR L:H at least 200:1, here up to 10 000:1",
    ev="fig1.cap, fig1, s2.p4, s2.p9; Fig. 1 caption and drawing; intro, roof removal for top-view analysis")
ser("F2a", "all_exp", "plot", 2, "a", "schematic", ("distance", "origin=entrance", "Distance x (µm)"), ("other", "", "Total growth (nm, ng, nm-2, ...)"),
    dk="schematic", link="inferred", note="as-measured saturation profile, generic sketch without numbers", ev="fig2.cap, fig2, s3.p2; Fig. 2a; classification text")
ser("F2b", "all_exp", "plot", 2, "b", "schematic", XT, ("other", "", "Growth/cycles (nm, ng, nm-2, ...)"), dk="schematic", link="inferred",
    note="scaled saturation profile (growth per cycle against x/H), generic sketch", ev="fig2.cap, fig2, s3.p3, s3.p4; Fig. 2b; scaled profile definition")
ser("F2c", "all_exp", "plot", 2, "c", "schematic", XT, ("normalized_thickness", "reference=entrance", "Normalized growth (-)"), dk="schematic", link="inferred",
    note="Type 1 normalized profile (entrance growth set to one, may be read as coverage theta)", ev="fig2.cap, fig2, s3.p5; Fig. 2c; Type 1 definition")
ser("F2d", "all_exp", "plot", 2, "d", "schematic", ("other", "", "Normalized distance xi = x/L (-)"), ("normalized_thickness", "reference=entrance", "Normalized growth (-)"),
    dk="schematic", link="inferred", note="Type 2 normalized profile (x divided by channel length L)", ev="fig2.cap, fig2, s3.p5; Fig. 2d; Type 2 definition")
ser("F3a", "all_exp", "plot", 3, "a", "schematic", XT, ("other", "", "Growth/cycles (nm, ng, nm-2, ...)"), dk="schematic", link="inferred",
    note="ideal simulated scaled profile with Regions I-IV, knee (1), PD50% (2), slope at PD50% (3), leading edge (4); no scale",
    ev="fig3.cap, fig3, s3.p6, s3.p7; Fig. 3a; region definitions")
ser("F3b", "all_exp", "plot", 3, "b", "schematic", XT, ("other", "", "Growth/cycles (nm, ng, nm-2, ...)"), dk="schematic", link="inferred",
    note="trace of an experimental Al2O3 scaled profile (sample not named) with subregions IIa-IIc, nanostep (5) and spikes (6); no scale",
    ev="fig3.cap, fig3, s3.p8, s17.p1; Fig. 3b; subregions and nanostep; spikes")
for p, n in (("a", 1), ("b", 2), ("c", 3)):
    ser(f"F4{p}", f"S{n}", "image", 4, p, "photograph",
        note=f"optical micrograph, top view after membrane removal, channel L 1 mm, layout {TAB1[n][4]}; brown = coated; "
             + ("straight front parallel to the entry" if n < 3 else "wavy front, membrane likely hangs lower between pillars"),
        ev=f"fig4.cap, fig4, s10.x1, s10.p1; Fig. 4 panel {p}; results text on Fig. 4; visual penetration")
ser("F5a", "S11", "map", 5, "a", "sem_eds", z=("other", "Al-K alpha X-ray counts (red overlay)"),
    note="top-view SEM with Al map; image label reads W80 L0.5mm (channel)", ev="fig5.cap, fig5a, s10.x2; Fig. 5a; results text on Fig. 5")
for el in ("O", "Al", "Si"):
    ser(f"F5b-{el}", "S11", "plot", 5, "b", "sem_eds", ("distance", "origin=opening_centre", "Distance [µm]"), ("other", f"element={el}", "Intensity [a.u.]"),
        note="EDS line scan across the opening (0 at its middle) into channels on both sides; Region I about -40 to 40 um",
        ev="fig5.cap, fig5b, s10.p2; Fig. 5b legend; line-scan description")
ser("F6", "SX", "map", 6, "", "afm", ("other", "", "X Range: 90 µm"), ("other", "", "Y Range: 90 µm"), z=("other", "height (Z range 3.081 µm)"),
    note="AFM near the entry after roof removal: membrane remnants white, pulled-out pillar holes black; nanostep at the entry (IIa), roughness and curtain-like waviness from there on",
    ev="fig6.cap, fig6, s10.x3; Fig. 6; results text on Fig. 6")
for sid, n, lab in (("F7-x5", 6, "X5 (50 µm)"), ("F7-x10", 5, "X10 (25 µm)"), ("F7-x50", 4, "X50 (5 µm)")):
    ser(sid, f"S{n}", "plot", 7, "", "reflectometry", ("distance", "origin=entrance", "Distance x (µm)"), YS,
        note=f"legend {lab}; larger spots widen the entry bump and the front" + ("; v1 points rejected" if n == 4 else ""),
        ev="fig7.cap, fig7, s11.x1; Fig. 7 legend; results text on Fig. 7")
for L, nscan in (("0.1", 3), ("0.5", 3), ("1", 2), ("5", 1)):
    for k in range(1, nscan + 1):
        ser(f"F8a-L{L}-scan{k}", f"S8-L{L}", "plot", 8, "a", "reflectometry", XD, YS,
            note=f"repeat scan {k} of {nscan} on the L {L} mm channel; scans overlap up to the front; tail peaks near 170 um are spikes near pillar remnants"
                 + ("; v1 merged the three 0.1 mm scans (rejected)" if L == "0.1" else ""),
            ev="fig8.cap, fig8a, s12.x1, s7.p5, s17.p2; Fig. 8a legend; results text on Fig. 8a; spikes near remnants")
for n, prev in ((2, ""), (4, ""), (8, ""), (12, "")):
    ser(f"F8b-S{n}", f"S{n}", "plot", 8, "b", "reflectometry", XD, YS,
        note="run-to-run reproducibility, 500 cycles, H 500 nm, layout v1b; chips differ in thickness and penetration",
        ev="fig8.cap, fig8b, s12.x2, s16.p10; Fig. 8b legend; results text on Fig. 8b; Discussion")
ser("FS4-S1", "S1", "plot", "S4", "", "reflectometry", XD, YS, note="ESI figure, not available here; scans behind Table 1 Series A (v1a and v1b overlap, v2a shallower)",
    ev="s10.p1; text points to Fig. S4 for layout profiles")
ser("FS4-S2", "S2", "plot", "S4", "", "reflectometry", XD, YS, note="ESI figure, not available here", ev="s10.p1; Fig. S4 reference")
ser("FS4-S3", "S3", "plot", "S4", "", "reflectometry", XD, YS, note="ESI figure, not available here", ev="s10.p1; Fig. S4 reference")
for p, x, y in (("a", XD, YS), ("b", XT, YG), ("c", XT, YN)):
    for H, n in ((100, 7), (500, 8), (2000, 9)):
        yy = ("normalized_thickness", "reference=entrance", y[2]) if (p == "c" and H == 100) else y
        pts, src = (cpts(9, "c", f"H {H} nm, 500 cycles"), "cases/points.json") if p == "c" else (None, "")
        reused = {("a", 500): "F8b-S8", ("c", 100): ""}.get((p, H), "")
        ser(f"F9{p}-H{H}", f"S{n}", "plot", 9, p, "reflectometry", x, yy, pts=pts, src=src, reused=reused,
            note={("a", 100): "no flat region: entry plugged by a ca. 50 nm film during growth",
                  ("a", 500): "same sample as Fig. 8b sample 8; looks like the same scan (inferred)",
                  ("c", 100): "authors normalise to the entrance value (no plateau); v1 points rejected, case 9 points used"}.get((p, H), "")
                 + ("; tail peak near 175 um is a spike (s17)" if (p, H) == ("a", 500) else ""),
            ev=f"fig9.cap, fig9{p}, s13.x1" + (", s17.p1" if (p, H) == ("a", 500) else "") + f"; Fig. 9{p} legend; results text on Fig. 9a-c")
    for N, n in ((250, 10), (500, 8), (1000, 11)):
        q = {"a": "d", "b": "e", "c": "f"}[p]
        pts, src = (cpts(9, "f", f"H 500 nm, {N} cycles"), "cases/points.json") if q == "f" else (None, "")
        ser(f"F9{q}-N{N}", f"S{n}", "plot", 9, q, "reflectometry", x, y, pts=pts, src=src, reused=f"F9{p}-H500" if N == 500 else "",
            note=("same sample 8 as the 500 nm series of the top row" if N == 500 else "")
                 + {("d", 1000): "v1 points rejected", ("e", 250): "v1 points rejected", ("e", 1000): "v1 points rejected"}.get((q, N), ""),
            ev=f"fig9.cap, fig9{q}, s13.x2, s13.p1; Fig. 9{q} legend; results text on Fig. 9d-f; cycles discussion")
for p, x, y in (("a", XD, YS), ("b", XT, YG), ("c", XT, YN)):
    for H in MH:
        ser(f"F10{p}-H{H}", mid(H), "plot", 10, p, "simulation", x, ("normalized_thickness", "reference=entrance", y[2]) if (p == "c" and H == 100) else y,
            dk="simulation", note="v1 points rejected" if (p, H) == ("a", 1000) else "", ev=f"fig10.cap, fig10{p}, s13.p2; Fig. 10{p} legend; simulation text")
    q = {"a": "d", "b": "e", "c": "f"}[p]
    for N in MN:
        ser(f"F10{q}-N{N}", mid(n=N), "plot", 10, q, "simulation", x, y, dk="simulation", reused=f"F10{p}-H500" if N == 500 else "",
            note=("same run as the 500 nm curve of the top row (inferred)" if N == 500 else "") + ("v1 points rejected" if N == 2000 else "")
                 + ("v1 points copy the 250-cycle curve (accepted with a note)" if N == 100 and q != "d" else ""),
            ev=f"fig10.cap, fig10{q}, s13.p2; Fig. 10{q} legend; simulation text")
for sid, n, lab, reused, note in (("F11a-0.1s", 12, "0.1 s", "F8b-S12", "same sample 12 as Fig. 8b (inferred same scan); TMA-dose-limited shape"),
                                  ("F11a-0.2s", 13, "0.2 s", "", "TMA-dose-limited shape"),
                                  ("F11a-0.4s", 14, "0.4 s", "", "front much broader: growth judged water-dose limited")):
    ser(sid, f"S{n}", "plot", 11, "a", "reflectometry", XD, YS, reused=reused, note=f"legend TMA pulse {lab}; {note}",
        ev="fig11.cap, fig11a, s14.p1, s18.p1; Fig. 11a legend; pulse-time results; TMA- vs water-limited shapes")
for sid, n, lab, reused in (("F11b-1s", 15, "1 s", ""), ("F11b-4s", 12, "4 s", "F11a-0.1s"), ("F11b-10s", 16, "10 s", "")):
    ser(sid, f"S{n}", "plot", 11, "b", "reflectometry", XD, YS, reused=reused,
        note=f"legend purge {lab} (both purges)" + ("; same sample 12 as Fig. 11a 0.1 s" if n == 12 else ""),
        ev="fig11.cap, fig11b, s14.x1, s18.p4; Fig. 11b legend; results text on Fig. 11b; purge discussion")

# ---------------------------------------------------------------- values
def val(sid, q, label, value="", unit="", dk="measured", method="", fs="", quals="", vmin="", vmax="", censor="", rel="", regime="",
        ref="", note="", ev=""):
    T["value"].append(dict(value_id=f"{K}:v{len(T['value']) + 1:03d}", sample_id=s_(sid) if sid else "", from_series=fs and s_(fs),
                           quantity=q, label_as_printed=label, qualifiers=quals, value=value, value_min=vmin, value_max=vmax,
                           censor=censor, unit=unit, data_kind=dk, method=method, relation=rel, regime=regime, cited_ref=ref,
                           note=note, evidence=ev))
ten = lambda s: str(Decimal(s).scaleb(1))
ASM = {1: "FS4-S1", 2: "FS4-S2", 3: "FS4-S3", 4: "F7-x50", 5: "F7-x10", 6: "F7-x5", 7: "F9a-H100", 8: "F9a-H500", 9: "F9a-H2000",
       10: "F9d-N250", 11: "F9d-N1000", 12: "F11a-0.1s", 13: "F11a-0.2s", 14: "F11a-0.4s", 15: "F11b-1s", 16: "F11b-10s"}
SCALED = {7: "F9b-H100", 8: "F9b-H500", 9: "F9b-H2000", 10: "F9e-N250", 11: "F9e-N1000"}
NORM = {7: "F9c-H100", 8: "F9c-H500", 9: "F9c-H2000", 10: "F9f-N250", 11: "F9f-N1000"}
REG = {12: "TMA-dose limited", 13: "TMA-dose limited", 14: "water-dose limited"}
for n, (rows, ser_, seq, H, lay, N, mag, v) in TAB1.items():
    S, fs, rg = f"S{n}", ASM[n], REG.get(n, "")
    E = lambda c, what, extra="": f"{cells(n, c)}{extra}; Table 1 sample {n} {what}"
    if v[0]:
        val(S, "film_thickness", "Thickness outside S_I", v[0], "nm", method="reflectometry", fs=fs, quals="position=outside",
            note="Region I; includes native oxide", ev=E(7, "thickness outside (Region I), footnote c", ", s3.p9"))
    val(S, "film_thickness", "Initial thickness S_IIb", v[1], "nm", method="reflectometry", fs=fs, quals="position=plateau",
        rel="mean of the first five points of Region IIb" if n != 7 else "first point of the constant region (100 nm design)",
        note="includes native oxide", ev=E(8, "initial thickness S_IIb, footnote c", ", s3.p9"))
    if v[2]:
        val(S, "growth_per_cycle", "S_I/N (GPC_I)", ten(v[2]), "Å", dk="calculated", method="calculation", fs=fs, quals="position=outside",
            rel="S_I divided by N", note=f"printed {v[2]} nm", ev=E(9, "S_I/N"))
    val(S, "growth_per_cycle", "S_IIb/N (GPC_IIb)", ten(v[3]), "Å", dk="calculated", method="calculation", fs=fs, quals="position=plateau",
        rel="S_IIb divided by N", note=f"printed {v[3]} nm", ev=E(10, "S_IIb/N"))
    val(S, "penetration_depth", "x_50% (PD^50%)", v[4], "µm", method="reflectometry", fs=fs, quals="level=50%;origin=entrance", regime=rg,
        ev=E(11, "PD50% (the first of the two x50% headers)"))
    val(S, "dimensionless_distance", "x~_50%", v[5], "", dk="calculated", method="calculation", fs=SCALED.get(n, fs), quals="level=50%;by=H",
        rel="x_50% divided by the design H", regime=rg, ev=E(12, "x~50% (values sit one column left of the parsed header)"))
    val(S, "front_slope", "Slope d(S/N)/dx~", v[6], "nm", dk="fit", method="calculation", fs=SCALED.get(n, fs), quals="level=50%;by=H",
        rel="best linear fit of the Region III front of the scaled profile", regime=rg, ev=E(13, "slope d(S/N)/dx~, footnote d", ", s3.p9"))
    val(S, "front_slope", "Slope dθ/dx~", v[7], "", dk="fit", method="calculation", fs=NORM.get(n, fs), quals="level=50%;by=H;reference=plateau",
        rel="linear fit of the front of the Type 1 normalized profile", regime=rg, ev=E(14, "slope dtheta/dx~"))
    val(S, "other", "Linear fitting residual R^2", v[8], "", dk="fit", method="calculation", fs=SCALED.get(n, fs), rel="R^2 of the front fit",
        ev=E(15, "R^2 of the linear fit"))
# text values
val("S1", "penetration_depth", "penetration depth (visual)", "140", "µm", method="photograph", fs="F4a", quals="origin=entrance",
    note="ca.; from the colour boundary; layouts v1a and v1b", ev="s10.p1; visual penetration for v1a and v1b")
val("S2", "penetration_depth", "penetration depth (visual)", "140", "µm", method="photograph", fs="F4b", quals="origin=entrance",
    note="ca.; from the colour boundary", ev="s10.p1; visual penetration for v1a and v1b")
val("S3", "penetration_depth", "penetration depth (visual)", "100", "µm", method="photograph", fs="F4c", quals="origin=entrance",
    note="ca.; wavy front", ev="s10.p1; visual penetration for v2a")
val("S11", "penetration_depth", "penetration under the membrane (Al map)", "125", "µm", method="sem_eds", fs="F5a", quals="origin=entrance",
    note="ca.; from the Al X-ray map (also Fig. S5)", ev="s10.x2; results text on Fig. 5, Al map")
val("S11", "other", "extent of constant signal in front of the channel (Region I)", "", "µm", method="sem_eds", fs="F5b-Al", vmin="-40", vmax="40",
    note="ca.; then a slightly higher plateau (IIb, IIc), knee and drop to zero", ev="s10.p2; line-scan regions")
val("serB", "other", "width of the adsorption front", "30", "µm", method="reflectometry", fs="F7-x50",
    note="ca.; the reason x50 (5 um spot) was used henceforth", ev="s11.x1; results text on Fig. 7, front width")
val("S7", "film_thickness", "film that plugs the 100 nm entry", "50", "nm", method="reflectometry", fs="F9a-H100", quals="position=entrance",
    note="ca.; explains the missing flat region", ev="s13.x1; results text on Fig. 9a-c, 100 nm entry")
for n, f in ((10, "10"), (8, "20"), (11, "40")):
    val(f"S{n}", "other", "fraction of the channel filled by the film", f, "%", dk="calculated", method="calculation", fs=ASM[n],
        rel="film thickness relative to H", note="ca.; restricts penetration at higher cycle numbers", ev="s13.p1; channel filling per cycle number")
val("MG-H", "other", "channel filling below which scaled profiles converge", "20", "%", dk="calculated", method="simulation", fs="F10b-H500", censor="<",
    note="'20% or less' (fingerprint profile)", ev="s13.p2; simulated height series")
val("all_exp", "other", "recommended channel filling", "10", "%", dk="assumed", method="calculation", censor="<",
    note="recommendation of the conclusions (preferably less than 10%) together with Knudsen regime", ev="s20.p2; Conclusions, favourable conditions")
val("all_exp", "other", "nanostep height at the channel entrance", "", "nm", method="afm", vmin="2", vmax="5", fs="F6",
    note="ca.; PillarHall-3 entrance", ev="s16.p3, s10.x3; Discussion uncertainty (iv); results text on Fig. 6")
val("H100", "other", "channel height tolerance (oxide thickness)", "10", "nm", method="process_monitor",
    note="± value; from oxide thickness during fabrication (ESI Table S5)", ev="s16.p4; tolerance per design height")
val("H500", "other", "channel height tolerance (oxide thickness)", "20", "nm", method="process_monitor", note="± value; ESI Table S5", ev="s16.p4; tolerance per design height")
val("H2000", "other", "channel height tolerance (oxide thickness)", "30", "nm", method="process_monitor", note="± value; ESI Table S5", ev="s16.p4; tolerance per design height")
val("H500", "other", "relative PD error per relative channel-height error", "1.5", "", dk="calculated", method="calculation",
    note="1% height error gives roughly 1.5% PD error (ESI Fig. S10)", ev="s16.p4, s16.p5; Discussion, height sensitivity")
val("H500", "other", "effect of pillars on penetration depth", "1", "%", dk="calculated", method="calculation", censor="<",
    note="for pillar diameter 4 um, spacing 49 um, triangular (ESI 3.2)", ev="s16.p5; Discussion (ii)")
val("H500", "other", "pillar diameter", "4", "µm", dk="assumed", note="typical value used in the pillar analysis", ev="s16.p5; Discussion (ii)")
val("H500", "other", "pillar interdistance", "49", "µm", dk="assumed", note="typical value, triangular arrangement", ev="s16.p5; Discussion (ii)")
val("H500", "other", "membrane bending displacement", "25", "nm", method="afm", note="ca.; ESI Fig. S13a", ev="s16.p5; Discussion (iii)")
val("H2000", "other", "membrane bending displacement", "25", "nm", method="afm", note="stated as about the same as for the 500 nm design", ev="s16.p5; Discussion (iii)")
val("H100", "other", "membrane bending displacement", "40", "nm", method="afm", note="ca.; ESI Fig. S13b", ev="s16.p5; Discussion (iii)")
val("tab1", "other", "positioning uncertainty of the scan start", "2", "µm", dk="assumed", method="reflectometry", note="order of magnitude estimate",
    ev="s16.p7; Discussion (i)")
val("repro", "other", "standard deviation of PD50%", "19.4", "µm", dk="calculated", method="calculation", rel="standard deviation over samples 2, 4, 8, 12 of Table 1",
    ev="s16.p10; Discussion, reproducibility")
val("repro", "other", "standard deviation of the slope at PD50%", "0.0003", "nm", dk="calculated", method="calculation", rel="standard deviation over samples 2, 4, 8, 12 (d(S/N)/dx~)",
    ev="s16.p10; Discussion, reproducibility")
val("repro", "other", "standard deviation of the initial thickness S_IIb", "2.8", "nm", dk="calculated", method="calculation", rel="standard deviation over samples 2, 4, 8, 12",
    ev="s16.p10; Discussion, reproducibility")
val("all_exp", "mean_free_path", "mean free path of TMA", "40", "µm", dk="calculated", method="calculation", quals="species=TMA",
    rel="eqn (3) of ref. 1 at 300 °C and the process conditions", ev="s19.p3; Sticking section, mean free paths")
val("all_exp", "mean_free_path", "mean free path of water", "100", "µm", dk="calculated", method="calculation", quals="species=H2O",
    rel="eqn (3) of ref. 1 at 300 °C and the process conditions", ev="s19.p3; Sticking section, mean free paths")
val("H500", "other", "hydraulic diameter h", "1.0", "µm", dk="calculated", method="calculation", rel="h = 2/(1/H + 1/W) for H 500 nm",
    ev="s19.p3; hydraulic diameter")
val("H500", "knudsen_number", "Kn for TMA", "40", "", dk="calculated", method="calculation", quals="species=TMA", rel="Kn = lambda/h",
    note="Arts method judged valid", ev="s19.p2, s19.p3; Knudsen condition and values")
val("H500", "knudsen_number", "Kn for water", "100", "", dk="calculated", method="calculation", quals="species=H2O", rel="Kn = lambda/h",
    ev="s19.p2, s19.p3; Knudsen condition and values")
val("H500", "aspect_ratio", "maximum AR (L 5000 um, H 500 nm)", "10000", "", dk="calculated", method="calculation", rel="L/H of the longest channel",
    note="design value; abstract says beyond 10 000:1", ev="s5.p2, fig1.cap, tab2.r6c3, tab2.r6c1, tab2.r6c2; Methods; Fig. 1 caption; Table 2 this-work row (parsed one row early)")
val("repro", "lumped_sticking_coefficient", "c_TMA (this work)", "4e-3", "", dk="calculated", method="calculation", quals="species=TMA",
    fs="F9c-H500", rel="Arts eqn (3): |dtheta/dx~| = sqrt(c/13.9), from the Table 1 dtheta/dx~ slopes of samples 2, 4, 8, 12, averaged",
    regime="TMA-dose limited", note="from_series stands for one of the four profiles (sample 8); 300 °C, 500 cycles, Picosun R-150",
    ev="tab2.cap, tab2.r7c6, tab2.r6c0, tab2.r6c4, s18.p3, s19.p1, s19.p4; Table 2 this-work c_TMA and footnote f; text value")
val("S14", "lumped_sticking_coefficient", "c_H2O (this work)", "3e-4", "", dk="calculated", method="calculation", quals="species=H2O",
    fs="F11a-0.4s", rel="Arts eqn (3) from the dtheta/dx~ slope of sample 14", regime="water-dose limited",
    ev="tab2.r7c7, s18.p3, s19.p4, tab2.r7c8; Table 2 this-work c_H2O and footnote g; text value")
# model inputs (Fig. 10 caption) and simulation settings
for lab, q, v_, u, quals, ref, note in (
        ("M_A", "other", "0.075", "kg/mol", "species=TMA", "", "molar mass of TMA"), ("M_B", "other", "0.028", "kg/mol", "species=N2", "", "molar mass of N2"),
        ("d_A", "other", "591", "pm", "species=TMA", "33", "molecular diameter of TMA"), ("d_B", "other", "374", "pm", "species=N2", "", "molecular diameter of N2"),
        ("b_film", "other", "2", "", "", "", "metal atoms per film formula unit"), ("b_TMA", "other", "1", "", "", "", "metal atoms per TMA molecule"),
        ("gpc_sat", "growth_per_cycle", "0.98", "Å", "", "", "printed 0.098 nm"), ("rho", "film_density", "3.1", "g/cm3", "", "51", "printed 3100 kg m-3"),
        ("q", "saturation_density", "3.6", "nm-2", "species=TMA", "", "adsorption density of TMA at saturation"),
        ("K", "other", "1000.0", "1/Pa", "", "", "adsorption equilibrium constant"),
        ("c_TMA", "lumped_sticking_coefficient", "0.012", "", "species=TMA", "", "three times the value extracted from the experiments (4e-3)"),
        ("P_d", "other", "0.043", "1/s", "", "", "desorption probability per unit time")):
    val("MG-all", q, lab, v_, u, dk="chosen input", method="simulation", quals=quals, ref=ref, note=note, ev="fig10.cap; Fig. 10 parameter list")
val("MG-all", "mean_free_path", "lambda_TMA in the simulated conditions", "40", "µm", dk="calculated", method="simulation", quals="species=TMA",
    note="ca.", ev="s8.p1; Methods simulation")
val("MG-all", "other", "ODE23 relative tolerance", "1e-3", "", dk="chosen input", method="simulation", ev="s8.p1; solver settings")
val("MG-all", "other", "ODE23 absolute tolerance", "1e-5", "", dk="chosen input", method="simulation",
    note="authors also correct ref. 33 eqn (1): both right-hand terms need Avogadro's number", ev="s8.p1; solver settings")
# literature values
L_ = lambda sid, q, lab, ev, **kw: val(sid, q, lab, dk="literature", **kw, ev=ev)
L_("ref31", "lumped_sticking_coefficient", "c_TMA", "tab2.r1c6; Table 2 Dendooven c_TMA", value="0.1", quals="species=TMA", ref="31")
L_("ref41", "lumped_sticking_coefficient", "c_TMA", "tab2.r2c6; Table 2 Schwille c_TMA", value="2e-2", quals="species=TMA", ref="41")
L_("ref60", "lumped_sticking_coefficient", "c_TMA", "tab2.r3c6, s18.p3; Table 2 Vandalon c_TMA, footnote d", value="1e-3", quals="species=TMA", ref="60", note="order of magnitude; planar wafer")
L_("ref60", "lumped_sticking_coefficient", "c_H2O", "tab2.r3c7, s18.p3; Table 2 Vandalon c_H2O, footnote d", value="1e-4", quals="species=H2O", ref="60", note="order of magnitude; planar wafer")
L_("vandalon2017", "lumped_sticking_coefficient", "c_H2O at 300 °C", "s18.p3; footnote d", value="1e-4", quals="species=H2O", ref="Vandalon et al. 2017", note="at 300 °C")
L_("vandalon2017", "lumped_sticking_coefficient", "c_H2O at 100 °C", "s18.p3; footnote d", value="1e-6", quals="species=H2O", ref="Vandalon et al. 2017", note="at 100 °C")
L_("vandalon2017", "lumped_sticking_coefficient", "c_TMA", "s18.p3; footnote d", value="2e-3", quals="species=TMA", ref="Vandalon et al. 2017", note="temperature independent")
L_("ref33", "lumped_sticking_coefficient", "c_TMA", "tab2.r4c6, s19.p4; Table 2 Ylilammi c_TMA (footnote e)", value="5.72e-3", quals="species=TMA", ref="33",
   note="obtained with film density 4000 kg m-3 (this work 3100)")
L_("ref33", "film_density", "alumina density used", "s18.p3; footnote e", value="4.0", unit="g/cm3", ref="33", note="printed 4000 kg m-3, not reported in the original")
L_("ref36", "lumped_sticking_coefficient", "c_TMA", "tab2.r5c6; Table 2 Arts c_TMA", vmin="0.5e-3", vmax="2e-3", quals="species=TMA", ref="36")
L_("ref36", "lumped_sticking_coefficient", "c_H2O", "tab2.r5c7, tab2.r6c6; Table 2 Arts c_H2O (exponent on the next parsed row)", vmin="0.8e-4", vmax="2e-4", quals="species=H2O", ref="36")
for r, v_, c in (("ref31", "200", "tab2.r1c3"), ("ref41", "100", "tab2.r2c3"), ("ref33", "2000", "tab2.r4c3"), ("ref36", "10000", "tab2.r5c3")):
    L_(r, "aspect_ratio", "Max. AR", f"{c}; Table 2 maximum AR", value=v_, ref=r[3:], note="order of magnitude estimate (footnote a)" if r == "ref41" else "")
L_("ref40", "aspect_ratio", "AR of PillarHall-1", "s2.p10; intro, Gao et al.", value="10000", censor=">", ref="40")
L_("ref40", "feature_width", "design cavity height", "s2.p10; intro, Gao et al.", vmin="200", vmax="1000", unit="nm", ref="40", note="200, 500 or 1000 nm")
L_("ref41", "feature_width", "limiting gap height", "s2.p10, tab2.r2c2; intro and Table 2", value="4500", unit="nm", ref="41", note="printed 4.5 um; footnote a gives a 5 um cavity")
L_("", "other", "number of published ALD processes", "s2.p10; intro", value="700", censor=">", ref="45")
L_("", "purge_time", "purge time range over which GPC decreased", "s18.p4; Discussion, Ylivaara et al.", vmin="1", vmax="4", unit="s", ref="51")

# ---------------------------------------------------------------- coverage
inv = list(csv.DictReader(open(HERE / "inventory.csv", encoding="utf-8")))
cited = {}
for t in ("sample", "condition", "series", "value"):
    idk = {"sample": "sample_id", "condition": "condition_id", "series": "series_id", "value": "value_id"}[t]
    for r in T[t]:
        for e in r["evidence"].split(";")[0].split(","):
            cited.setdefault(e.strip(), []).append(r[idk])
REASON = {
    "abstract": "abstract: checked against the body, nothing new",
    "abs.g2": "abstract: checked against the body; it says 'beyond 10 000:1' where the body says 'up to 10 000:1' (s5.p2, fig1.cap)",
    "heading": "heading", "s0.p1": "citation line", "s1.p1": "author list", "s1.p2": "dates", "s1.p3": "DOI", "s1.p4": "journal link",
    "s2.p1": "background (history of ALD)", "s2.p2": "background", "s2.p3": "background", "s2.p5": "affiliation", "s2.p6": "affiliation",
    "s2.p7": "ESI pointer", "s2.p8": "author note", "s2.p11": "background (literature methods)", "s2.p12": "background (literature methods)",
    "s2.p13": "aims", "s3.p1": "section introduction", "s3.p2": "terminology (profile classes), no data",
    "s3.p3": "terminology (scaled profile)", "s3.p4": "terminology", "s3.p5": "terminology (Type 1 and Type 2 normalization)",
    "s3.p6": "terminology (Regions I-IV)", "s3.p7": "terminology", "s3.p8": "terminology (subregions, nanostep)",
    "s12.p1": "list of uncertainty sources, no data", "s16.p1": "discussion outline", "s16.p2": "discussion outline",
    "s16.p9": "discussion of process fluctuations, no data", "s17.p1": "qualitative (spikes); carried in series notes",
    "s20.p1": "conclusions restating the work", "s20.p3": "conclusions restating results",
    "s21.p1": "funding", "s22.p1": "notation statement", "s23.p1": "conflicts of interest", "s24.p1": "acknowledgement", "s24.p2": "acknowledgement (conference history, data repository)",
    "tab1.r0c12": "header: duplicate x50% header from the parser; the page has no such column (values c11-c15 sit under headers c11, c13-c16)",
    "tab2.r1c7": "dash: no c_H2O reported for this work", "tab2.r2c7": "dash: no c_H2O reported for this work", "tab2.r4c7": "dash: no c_H2O reported for this work",
    "tab2.r2c4": "dash: cycles not reported in the cited work (footnote b, s18.p3)", "tab2.r3c4": "dash: cycles not reported in the cited work (footnote b, s18.p3)",
    "tab2.r6c7": "parser artefact: no such cell on the page (the this-work row has c_H2O 3e-4 in tab2.r7c7)",
}
cov = []
for e in inv:
    eid = e["element_id"]
    if eid in cited:
        cov.append(dict(element_id=eid, status="covered", rows=";".join(dict.fromkeys(cited[eid])), reason=""))
    else:
        rs = REASON.get(eid) or REASON.get(e["kind"]) or ("header: meaning carried by the value rows of its column" if eid.startswith("tab") and ".r0c" in eid else "")
        if not rs:
            raise SystemExit(f"no coverage for {eid}")
        cov.append(dict(element_id=eid, status="no knowledge", rows="", reason=rs))
bad = [e for e in cited if e not in {i["element_id"] for i in inv}]
if bad:
    raise SystemExit(f"evidence ids not in inventory: {bad}")

T["paper"] = [dict(paper_id=PID, year="2020", topic="saturation profiles of TMA-water ALD Al2O3 in PillarHall-3 lateral high-aspect-ratio channels: "
                   "layout, spot size, repeatability, channel height, cycles, pulse and purge time; simulation; lumped sticking coefficients")]
for t, cols in COLS.items():
    with open(HERE / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(T[t])
with open(HERE / "coverage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["element_id", "status", "rows", "reason"]); w.writeheader(); w.writerows(cov)
print({t: len(T[t]) for t in COLS}, "coverage", len(cov))
