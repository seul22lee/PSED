"""Write the six schema-pilot tables for 10.1116_6.0003182 (Greenberg 2023, key gre23)."""
import csv, json, os, sys

P = "10.1116_6.0003182"
REPO = "/home/ftk3187/github/PSED/psed_v2"
OUT = os.path.join(REPO, "schema_pilot", P, "draft")
K = "gre23"
R120, R160, RCYC = f"{K}:120", f"{K}:160", f"{K}:120/160"
RUNS = [R120, R160, RCYC]
RUNNAME = {R120: "T held at 120 C", R160: "T held at 160 C", RCYC: "T cycled 120/160 C"}


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            assert len(r) == len(header), (name, r)
            w.writerow(r)
    return len(rows)


counts = {}
# ---------------------------------------------------------------- paper
counts["paper.csv"] = write("paper.csv", ["paper_id", "year", "topic"], [[
    P, "2023",
    "Static-dose thermal ZnO ALD (DEZ/H2O, 20 cycles, ~17000 Torr s per step) inside pressed Al2O3 nanoparticle "
    "compacts (AR 7800 on the half-thickness); three temperature schedules (120 C, 160 C, 120 C with 160 C H2O purge) "
    "compared by mass gain, chamber pressure traces, XRD, resistivity and cross-section SEM-EDS"]])

# ---------------------------------------------------------------- samples
DIMS = ("pressed Al2O3 NP compact disc: thickness 1.55 mm (half-thickness L 0.78 mm), diameter 11.43 mm, "
        "d_NP 100 nm, d_pore ~ d_NP, porosity 50.5 %, AR 7800 (on L)")
COMMON = ["ZnO", "DEZ", "H2O", "thermal", "ALD NanoSolutions (Forge Nano) custom RX-series", "porous", DIMS, "d"]
samples = []
for rid, lab, t, ev in [
    (R120, "120", "120", "Sec. II B, 3rd para, run (1); Table I/II row '120'; Fig. 1b"),
    (R160, "160", "160", "Sec. II B, 3rd para, run (2); Table I/II row '160'; Fig. 1b"),
    (RCYC, "120/160", "120 (160 during H2O purge)", "Sec. II B, 3rd para, run (3); Table I/II row '120/160'; Fig. 1b"),
]:
    samples.append([rid, P, lab, ""] + COMMON + [t, "20",
                    ev + "; run outcome: a pair of NPCs coated together, the paper's 'sample' in Tables I-II"])
pair = {R120: ("u1", "u2"), R160: ("u3", "u4"), RCYC: ("u5", "u6")}
for rid, (a, b) in pair.items():
    for n, u in enumerate((a, b), 1):
        samples.append([f"{K}:{u}", P, "u", rid] + COMMON[:5] + ["porous", DIMS, "d", samples[RUNS.index(rid)][12], "20",
                        f"Sec. III A, 1st para: two NPCs weighed per run (NPC {n} of the pair, {RUNNAME[rid]}); Table I caption: +- is variability within the pair"])
for rid, u in zip(RUNS, ("u7", "u8", "u9")):
    samples.append([f"{K}:{u}", P, "u", rid] + COMMON[:5] + ["porous",
                    "prism ~6 x 3 x 1.6 mm cut from a coated NPC, Ti 20 nm / Au 200 nm on top and bottom faces", "none",
                    samples[RUNS.index(rid)][12], "20",
                    f"Sec. II C, 2nd para (prisms cut after Ti/Au); Sec. III B, 3rd para: one NPC measured per condition ({RUNNAME[rid]}); which NPC of the pair not stated"])
samples.append([f"{K}:u10", P, "Before ALD", "", "Al2O3 (uncoated)", "", "", "", "", "porous", DIMS, "d", "", "0",
                "Fig. 4a: uncoated NPC photographed before ALD; whether it is one of the later-coated NPCs not stated"])
samples.append([f"{K}:u11", P, "u", "", "ZnO", "DEZ", "H2O", "thermal", "ALD NanoSolutions (Forge Nano) custom RX-series", "", "", "none",
                "120 (160 during H2O purge)", "",
                "Fig. 2 caption (d): separate test run under the same conditions as the cycled run, boat temperature logged by a contact thermocouple; substrate and cycle count not stated"])
counts["sample.csv"] = write("sample.csv", ["sample_id", "paper_id", "label_as_printed", "parent_sample", "material", "precursor",
                                            "coreactant", "process_mode", "reactor", "structure_class", "structure_dims", "width_kind",
                                            "temperature_C", "cycles", "evidence"], samples)

# ---------------------------------------------------------------- conditions
C = []
def c(s, q, step, v, u, kind, ev):
    C.append([s, q, step, v, u, kind, ev])

c(R120, "deposition_temperature", "none", "120", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b; held for all steps")
c(R160, "deposition_temperature", "none", "160", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b; held for all steps")
c(RCYC, "deposition_temperature", "A", "120", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b (DEZ dose)")
c(RCYC, "deposition_temperature", "purge", "120", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b (DEZ purge)")
c(RCYC, "deposition_temperature", "B", "120", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b (H2O dose)")
c(RCYC, "deposition_temperature", "purge", "160", "°C", "stated", "Sec. II B, 3rd para; Fig. 1b (H2O purge: ramped up to 160 C then back to 120 C before the next DEZ pulse)")
c(RCYC, "temperature_ramp_time (new)", "purge", "33.5", "min", "stated", "Sec. IV, 3rd para: chamber heating ramp 120 to 160 C during H2O purge")
c("*", "deposition_temperature_definition (new)", "none", "boat interior surface temperature at steady state under 20 sccm N2, rounded to nearest 10 C", "", "stated", "Sec. II B, 3rd para; Fig. 2 caption")
c("*", "deposition_temperature_spread (new)", "none", "±5", "°C", "stated", "Sec. II B, 3rd para: spread among calibration runs at the same exterior setpoint")
c("*", "chamber_wall_temperature (new)", "none", "≈T", "°C", "stated", "Sec. II B, 3rd para: main chamber inner wall about equal to boat T in all runs")
c("*", "line_temperature (new)", "none", "100-130 (external surface)", "°C", "stated", "Sec. II B, 3rd para: 1/4 in. and KF25 tubing heated by tape")
c("*", "line_temperature (new)", "none", "~90-120 (internal surface)", "°C", "assumed", "Sec. II B, 3rd para: expected internal temperature of the taped lines")
c("*", "unheated_surface_temperature (new)", "none", "<90 possible", "°C", "assumed", "Sec. II B, 3rd para: quartz/sapphire windows not directly heated")
c("*", "cycle_number", "none", "20", "cycle", "stated", "Sec. I, last para; Sec. II B, 2nd para")
c("*", "substrate_pretreatment (new)", "B", "one H2O half-cycle before cycle 1 to hydroxylate Al2O3", "", "stated", "Sec. II B, 3rd para; Fig. 2 caption")
c("*", "degas_time (new)", "none", ">=2", "h", "stated", "Sec. II B, 3rd para: NPC degassing in the ALD chamber before the H2O half-cycle")
c(R120, "degas_temperature (new)", "none", "120", "°C", "stated", "Sec. II B, 3rd para: degassing at the initial T (120 or 160 C)")
c(R160, "degas_temperature (new)", "none", "160", "°C", "stated", "Sec. II B, 3rd para: degassing at the initial T (120 or 160 C)")
c(RCYC, "degas_temperature (new)", "none", "120", "°C", "assumed", "Sec. II B, 3rd para: 'initial T (120 or 160 C)'; 120 C taken for the cycled run (DEZ steps at 120 C)")
c("*", "pulse_time", "A", "10-14", "s", "stated", "Sec. II B, 2nd para; varied by hand to keep the dose pressure steady")
c("*", "hold_time (new)", "A", "1920", "s", "stated", "Sec. II B, 2nd para; Sec. I last para (32 min); pump and ALD valves closed (static dose)")
c("*", "purge_time", "purge", "2880", "s", "stated", "Sec. II B, 2nd para: DEZ purge 48 min")
c("*", "pulse_time", "B", "8-11", "s", "stated", "Sec. II B, 2nd para")
c("*", "hold_time (new)", "B", "1920", "s", "stated", "Sec. II B, 2nd para")
c("*", "purge_time", "purge", "2880", "s", "stated", "Sec. II B, 2nd para: H2O purge 48 min; Sec. II B, 4th para: chosen so that theta_f < 5e-3 at 120/160 and 160 C")
c("*", "cycle_time (new)", "none", "~160", "min", "stated", "Sec. II B, 2nd para")
c("*", "partial_pressure", "A", "~9", "Torr", "stated", "Sec. I last para; Sec. II B, 2nd para (fluctuated; Fig. S2); Fig. 2")
c("*", "partial_pressure", "B", "~9", "Torr", "stated", "Sec. I last para; Sec. II B, 2nd para; Fig. 2")
c("*", "exposure", "A", "~17000", "Torr s", "stated", "Sec. I last para (~9 Torr x 1920 s); abstract '>10^4 Torr s'")
c("*", "exposure", "B", "~17000", "Torr s", "stated", "Sec. I last para; abstract")
c("*", "delivery_method", "none", "static dosing: pulse then zero-flow hold with chamber isolated", "", "stated", "Sec. II B, 2nd para")
c("*", "isolation_valve_state (new)", "A", "pump isolation valve closed during pulse and hold; ALD valves also closed during hold", "", "stated", "Sec. II B, 2nd para")
c("*", "isolation_valve_state (new)", "B", "pump isolation valve closed during pulse and hold; ALD valves also closed during hold", "", "stated", "Sec. II B, 2nd para")
c("*", "source_temperature", "A", "37", "°C", "stated", "Sec. II B, 2nd para: stainless cylinders, metering valves")
c("*", "source_temperature", "B", "37", "°C", "stated", "Sec. II B, 2nd para")
c("*", "precursor_purity (new)", "A", "DEZ min. 95 % (Strem)", "", "stated", "Sec. II B, 2nd para")
c("*", "precursor_purity (new)", "B", "de-ionized H2O", "", "stated", "Sec. II B, 2nd para")
c("*", "reactor", "none", "ALD NanoSolutions (Forge Nano) custom RX-series", "", "stated", "Sec. II B, 1st para")
c("*", "chamber_geometry (new)", "none", "approx. horizontal cylinder ~20 cm long x 10 cm ID, MKS LoPro isolation valve to pump", "", "stated", "Sec. II B, 1st para")
c("*", "chamber_volume (new)", "none", "2.17", "L", "stated", "Sec. II B, 2nd para: total isolated volume from pressure-vs-flow studies")
c("*", "carrier_gas", "purge", "N2", "", "stated", "Sec. II B, 2nd para")
c("*", "purge_flow_sequence (new)", "purge", "30 s no flow; 30 s 10 sccm through the half of the manifold just used; 2790 s 10 sccm through both halves; 30 s no flow", "", "stated", "Sec. II B, 2nd para")
c("*", "gas_flow_rate", "purge", "20", "sccm", "stated", "Sec. II B, 2nd para: 10 sccm per half, 20 sccm total in the main purge segment")
c("*", "pressure_gauge (new)", "none", "two Baratron 728A, full scale 10 and 1000 Torr, heated to 100 C", "", "stated", "Sec. II B, 1st para (cont.)")
c("*", "pressure_offset (new)", "none", "0.26", "Torr", "stated", "Sec. II B, 1st para (cont.): base pressure set to 0 at 120 C")
c("*", "pressure_resolution (new)", "none", "10", "mTorr", "stated", "Sec. III A, 4th para: resolution of recorded pressure data")
c("*", "sample_mounting (new)", "none", "NPCs in rounded quartz boat, only bottom circular edge touching, gap up to ~1 mm under bottom face; reactants enter both faces", "", "stated", "Sec. II B, 1st para; Fig. 1a; Sec. I last para")
c("*", "npc_per_run (new)", "none", "2", "", "stated", "Sec. III A, 1st para; Table I caption")
c("*", "substrate_powder (new)", "none", "BMA15 deagglomerated alpha-Al2O3 nanopowder (Baikowski), BET 15 m2/g", "", "stated", "Sec. II A")
c("*", "pressing_powder_mass (new)", "none", "0.320 ± 0.005", "g", "stated", "Sec. II A")
c("*", "pressing_pressure (new)", "none", "481", "MPa", "stated", "Sec. II A: 12 ton manual press (Carver), 11.4 mm WC die, ambient atmosphere")
c("*", "pressing_hold_time (new)", "none", "<1", "min", "stated", "Sec. II A")
c("*", "ambient_exposure (new)", "none", "coated NPCs exposed to air before (and for XRD/resistivity during) characterization", "", "stated", "Sec. II C, 1st para")
# characterization settings (all coated runs)
for q, v, u, ev in [
    ("xrd_source (new)", "Cu K-alpha1, rotating anode, 50 kV, 200 mA (Rigaku)", "", "Sec. II C, 1st para"),
    ("xrd_scan (new)", "2theta 20-80 deg at 1 deg/min, 0.02 deg step", "", "Sec. II C, 1st para"),
    ("xrd_geometry (new)", "one exterior face scanned, then fractured interior rescanned (no significant difference)", "", "Sec. II C, 1st para"),
    ("xrd_analysis (new)", "ICDD cards 04-002-5941 (Al2O3), 04-001-7297 (ZnO), 00-004-0831 (Zn); Rietveld + Halder-Wagner in JADE 9", "", "Sec. II C, 1st para"),
    ("electrode (new)", "e-beam Ti 20 nm / Au 200 nm blanket films on top and bottom faces, at 1e-6 Torr", "", "Sec. II C, 2nd para"),
    ("resistivity_method (new)", "two-point through the thickness, probe on top, conductive stage below, resistance at 10 V, film areas for conversion", "", "Sec. II C, 2nd para"),
    ("sem_prep (new)", "sectioned, epoxy-mounted, ground, polished, conductive coat (Note S2)", "", "Sec. II C, 3rd para"),
    ("eds_beam (new)", "30 kV, 63 nA, 50 um aperture, 10 mm WD, 0.96 us amp time (Quattro S ESEM, EDAX)", "", "Sec. II C, 3rd para"),
    ("eds_map (new)", "~1.5 x 1 mm area, 200 us dwell, 32 frames", "", "Sec. II C, 3rd para (cont.)"),
    ("eds_linescan (new)", "100 points along centre line through thickness, 100 um width, 20 ms dwell per point, 512 frames", "", "Sec. II C, 3rd para (cont.)"),
    ("xps_settings (new)", "mono Al K-alpha 1486.7 eV, 125 um spot, flood gun; 1 keV Ar etch 15 s and 30 s; survey 1 eV/200 eV pass; high-res 0.1 eV/20 eV pass; C 1s 284.8 eV reference", "", "Sec. II C, 4th para"),
]:
    c("*", q, "none", v, u, "stated", ev)
counts["condition.csv"] = write("condition.csv", ["sample_id", "quantity", "step", "value", "unit", "data_kind", "evidence"], C)

# ---------------------------------------------------------------- series
pts = json.load(open(os.path.join(REPO, "cases", "points.json")))["series"]
pts = {(s["figure"], s["panel"]): s for s in pts if s["paper"] == P}
S = []
def s(sid, samp, fig, pan, meth, xid, xby, yid, yref, kind, ev, pkey=None):
    if pkey and pkey in pts:
        S.append([sid, samp, fig, pan, meth, xid, xby, yid, yref, kind, "from points.json", json.dumps(pts[pkey]["points"]), "cases/points.json", ev])
    else:
        S.append([sid, samp, fig, pan, meth, xid, xby, yid, yref, kind, "not read", "", "", ev])

for pan, rid in zip("abc", RUNS):
    s(f"{K}:s2{pan}", rid, "2", pan, "chamber pressure gauge (Baratron)", "time (new: run time)", "start of the first logged step (pre-run H2O half-cycle)",
      "process_pressure", "offset 0.26 Torr subtracted (base = 0 at 120 C)", "measured", f"Fig. 2 caption ({pan}); first five cycles plus pre-run H2O half-cycle")
s(f"{K}:s2d", f"{K}:u11", "2", "d", "contact thermocouple on quartz boat", "time (new: run time)", "start of the first logged step",
  "deposition_temperature", "absolute", "measured", "Fig. 2 caption (d): test run under the conditions of (c)")
for rid, col in zip(RUNS, ("blue", "red", "green")):
    k = rid.split(":")[1].replace("/", "")
    s(f"{K}:s3a_{k}", rid, "3", "a", "chamber pressure gauge (10 Torr; 1000 Torr for the noisier part of the 160 C trace)", "time",
      "start of the DEZ hold, cycle 15", "pressure_change (new)", "pressure at start of hold (~9 Torr) subtracted", "measured", f"Fig. 3 caption (a), {col}")
for rid, col in zip(RUNS, ("blue", "red", "green")):
    k = rid.split(":")[1].replace("/", "")
    s(f"{K}:s3b_{k}", rid, "3", "b", "pressure trace analysis (leak and pulse corrections, Note S3)", "cycle_number", "cycle index 1-20",
      "gas_moles_gain (new)", "net change over DEZ hold, from Delta p and chamber volume", "calculated", f"Fig. 3 caption (b), {col}")
for rid, col in zip(RUNS, ("blue", "red", "green")):
    k = rid.split(":")[1].replace("/", "")
    s(f"{K}:s3c_{k}", rid, "3", "c", "pressure trace analysis", "cycle_number", "cycle index 1-20",
      "terminal_slope (new)", "mean dp/dt over last 10 min of DEZ hold", "calculated", f"Fig. 3 caption (c), {col}")
for pan, rid in zip("abcd", [f"{K}:u10"] + RUNS):
    s(f"{K}:s4{pan}", rid, "4", pan, "photograph (top surface)", "none", "", "none (colour)", "", "measured", f"Fig. 4 caption ({pan}); Sec. III B, 1st para")
for rid, col in zip(RUNS, ("blue, top", "red, middle", "green, bottom")):
    k = rid.split(":")[1].replace("/", "")
    s(f"{K}:s5_{k}", rid, "5", "", "XRD (Cu K-alpha1), top surface", "two_theta (new)", "deg", "xrd_intensity (new)", "normalized counts, offset stacked", "measured", f"Fig. 5 caption ({col} pattern); Sec. III B, 2nd para")
for ref in ("Zn", "ZnO", "Al2O3"):
    s(f"{K}:s5_ref_{ref}", "", "5", "", f"reference powder pattern ({ref}, ICDD card)", "two_theta (new)", "deg", "xrd_intensity (new)", "relative stick height", "cited", f"Fig. 5 caption; Sec. II C 1st para (ICDD card numbers)")
for pan, rid in zip("abc", RUNS):
    k = rid.split(":")[1].replace("/", "")
    for img, meth in (("SE", "SEM secondary-electron image"), ("Al", "EDS map, Al K-alpha"), ("Zn", "EDS map, Zn K-alpha")):
        s(f"{K}:s6{pan}_{img}", rid, "6", pan, meth + " (cross-section)", "distance (lateral, mm)", "image frame; scale bar 0.5 mm",
          "distance (through thickness)" if img == "SE" else "eds_counts (new: map intensity)", "", "measured", f"Fig. 6 caption ({pan})")
for pan, rid in zip("def", RUNS):
    for el in ("Al", "Zn", "O", "C"):
        s(f"{K}:s6{pan}_{el}", rid, "6", pan, f"SEM-EDS line scan, {el} K-alpha, centre line through thickness", "eds_normalized_counts (new)",
          "K-alpha counts normalized to total counts over all elements and positions (axes as printed: counts on x)",
          "distance", "position through thickness from top of section (mm, printed on y); two-sided, faces at 0 and ~1.5 mm",
          "measured", f"Fig. 6 caption (d)-(f); Sec. III C 1st para" + ("; 160 C section incomplete above ~0.42 mm" if pan == "e" else ""),
          ("6", pan) if el == "Zn" else None)
counts["series.csv"] = write("series.csv", ["series_id", "sample_ids", "figure", "panel", "method", "x_id", "x_by", "y_id", "y_reference", "data_kind",
                                            "points_status", "points", "reused_from", "evidence"], S)

# ---------------------------------------------------------------- values
V = []
def v(samp, ser, q, qual, val, unit, kind, meth, rel, reg, ev):
    V.append([f"{K}:v{len(V)+1:03d}", samp, ser, q, qual, val, unit, kind, meth, rel, reg, ev])

# substrate geometry (all NPCs)
v("*", "", "feature_depth", "full thickness 2L", "1.55 ± 0.05", "mm", "measured", "electronic calipers", "", "", "Sec. II A; abstract")
v("*", "", "feature_depth", "half-thickness L (reactants enter both faces)", "0.78 ± 0.02", "mm", "calculated", "", "L = thickness/2", "", "Sec. I last para; Sec. IV")
v("*", "", "disc_diameter (new)", "", "11.43 ± 0.02", "mm", "measured", "electronic calipers", "", "", "Sec. II A; Fig. 1a and 4a (~11.4 mm written)")
v("*", "", "porosity (new)", "initial, phi_i", "50.5 ± 0.3", "%", "measured", "not stated (from mass and dimensions, presumably)", "", "", "Sec. II A; abstract; Table I caption")
v("*", "", "particle_diameter (new)", "Al2O3 NP, d_NP", "100", "nm", "calculated", "from BET specific surface area (manufacturer spec)", "", "", "Sec. II A")
v("*", "", "specific_surface_area (new)", "Al2O3 powder BET", "15", "m2/g", "literature", "manufacturer spec (BET)", "", "", "Sec. II A")
v("*", "", "feature_width", "pore diameter d_pore ~ d_NP", "~100", "nm", "assumed", "", "d_pore ~ d_NP at ~50 % porosity", "", "Sec. I last para; Sec. II A")
v("*", "", "aspect_ratio", "AR = L/d_pore on half-thickness", "7800 ± 200", "1", "calculated", "", "AR = L/d_pore", "", "abstract; Sec. I last para; Sec. IV")
v("*", "", "corundum_grain_size (new)", "Al2O3, XRD", "90-100", "nm", "fit", "Rietveld / Halder-Wagner (JADE 9)", "", "", "Sec. II C, 1st para")
v("*", "", "rietveld_residual (new)", "all three samples", "~15 (within 1 point)", "%", "fit", "Rietveld whole-pattern fit", "", "", "Sec. II C, 1st para")
v("*", "", "high_density_band_width (new)", "Al2O3 denser band near bottom of each section", "~0.3-0.5", "mm", "measured", "SEM, Al K-alpha maps/line scans", "", "", "Sec. III C, 1st para")
# design model
v("", "", "surface_coverage", "target final H2O coverage theta_f after purge", "5e-3", "1", "chosen input", "", "Eq. 2", "", "Sec. II B, 4th para (from Cendejas et al. ref. 8)")
v("", "", "desorption_prefactor (new)", "nu, H2O desorption", "1e13", "1/s", "literature", "", "Eq. 2", "", "Sec. II B, 4th para (ref. 21)")
v("", "", "purge_time", "required H2O purge, T = 120 C", "360", "min", "calculated", "", "Eq. 2: t_purge = ln(1/theta_f)/(nu exp(-E_des/RT))", "", "Sec. II B, 4th para")
v("", "", "purge_time", "required H2O purge, T = 160 C", "11", "min", "calculated", "", "Eq. 2", "", "Sec. II B, 4th para")
v("", "", "purge_time", "chosen purge (both reactants)", "48", "min", "chosen input", "", "", "", "Sec. II B, 4th para; Sec. III C (DEZ purge set equal to H2O purge, not optimized)")
v("", "", "hold_time (new)", "design relation", "", "s", "chosen input", "", "Eq. 1: t_hold = L_pore^2/(D gamma), Knudsen D", "Knudsen diffusion", "Sec. II B, 4th para (inputs in Note S1, not in main text)")
# Table I
TI = {R120: ("28.4 ± 0.1", "36.7 ± 0.1", "2.37 ± 0.02", "150", "59.3", "1.395"),
      R160: ("36.4 ± 1.6", "30.6 ± 1.4", "3.48 ± 0.26", "217", "191", "1.880"),
      RCYC: ("26.4 ± 0.1", "38.0 ± 0.1", "2.14 ± 0.01", "139", "50.8", "1.365")}
for rid, (mg, pf, gpc, ns, ng, y) in TI.items():
    row = f"Table I row '{rid.split(':')[1]}'"
    v(rid, "", "mass_gain (new)", "NPC mass gain, pair mean, +- within pair", mg, "%", "measured", "weighing before/after ALD", "", "", row + "; Sec. III A 1st para")
    v(rid, "", "porosity (new)", "final, phi_f, assuming uniform coating", pf, "%", "calculated", "from mass gain", "", "", row + " (text Sec. III A lists them in a different order, see notes)")
    v(rid, "", "growth_per_cycle", "average over 20 cycles, from mass gain (mean of spherical-NP and spherical-pore models), assumes pure ZnO", gpc, "Å/cycle", "calculated", "mass gain to porosity to thickness", "", "", row + "; Sec. III A 1st para")
    v(rid, "", "solid_moles_per_cycle (new)", "Delta n_s bar, pair total, assumes ZnO", ns, "µmol/cycle", "calculated", "from GPC", "", "", row)
    v(rid, "", "gas_moles_gain (new)", "Delta n_g bar, cycle-averaged, DEZ hold, pair total", ng, "µmol/cycle", "calculated", "pressure trace analysis", "", "", row + "; Fig. 3b")
    v(rid, "", "gas_solid_ratio (new)", "y bar = Delta n_g/Delta n_s + 1 (printed as y; parser renders nu)", y, "1", "calculated", "", "Eqs. 6-8", "", row + "; Sec. III A, after Eq. 8")
v("*", "", "gas_moles_gain (new)", "measurement uncertainty of Delta n_s and Delta n_g", "±0.1", "µmol/cycle", "measured", "", "", "", "Table I caption")
v("*", "", "gas_solid_ratio (new)", "measurement uncertainty", "±0.001", "1", "measured", "", "", "", "Table I caption; Sec. III A")
v(RCYC, "", "growth_per_cycle", "abstract rounding", "~2.1", "Å/cycle", "calculated", "from mass gain", "", "", "abstract")
v(R120, "", "film_thickness", "ZnO coating thickness inferred from mass gain", "4.73 ± 0.03", "nm", "calculated", "from mass gain", "", "", "Sec. III B, 2nd para (cont.)")
v(RCYC, "", "film_thickness", "ZnO coating thickness inferred from mass gain", "4.28 ± 0.03", "nm", "calculated", "from mass gain", "", "", "Sec. III B, 2nd para (cont.)")
v(R120, "", "film_thickness", "excess deposition vs cycled run", "0.4-0.5", "nm", "calculated", "", "", "", "Sec. III C, after Table II")
v(R160, "", "dez_moles_relative (new)", "DEZ moles per pulse vs 120 C at equal pressure", "~10 % fewer", "", "calculated", "", "ideal gas, same pressure, higher T", "", "Sec. III C, 3rd para")
# Table II
TII = {R120: ("23.3 ± 0.2", "6.0 ± 1.1", "not detected", "—", "1.3 ± 0.2 × 10^7"),
       R160: ("17.1 ± 0.2", "6.0 ± 1.5", "12.5 ± 0.7", "57 ± 42", "8.3 ± 1.0 × 10^3"),
       RCYC: ("17.7 ± 0.1", "5.1 ± 1.1", "not detected", "—", "1.2 ± 0.1 × 10^7")}
for rid, (zw, zs, mw, ms, rho) in TII.items():
    row = f"Table II row '{rid.split(':')[1]}'"
    xs = f"{K}:s5_{rid.split(':')[1].replace('/', '')}"
    v(rid, xs, "composition", "phase wt% ZnO (zincite), top surface, +- fit error", zw, "wt%", "fit", "XRD Rietveld", "", "", row)
    v(rid, xs, "crystallite_size (new)", "ZnO (zincite), +- fit error", zs, "nm", "fit", "XRD Halder-Wagner", "", "", row)
    v(rid, xs, "composition", "phase wt% metallic Zn", mw, "wt%", "fit", "XRD Rietveld", "", "", row)
    if ms != "—":
        v(rid, xs, "crystallite_size (new)", "metallic Zn", ms, "nm", "fit", "XRD Halder-Wagner", "", "", row)
    prism = {R120: "u7", R160: "u8", RCYC: "u9"}[rid]
    v(f"{K}:{prism}", "", "resistivity", "through-thickness, +- from electrode area (flaking)", rho, "Ω cm", "measured", "two-point I-V at 10 V, Ti/Au electrodes", "", "", row + "; Sec. III B 3rd para (~8e3 and ~1e7 in text)")
for rid in RUNS:
    v(rid, f"{K}:s5_{rid.split(':')[1].replace('/', '')}", "crystallinity", "phases seen", "corundum + broad zincite" + (" + metallic Zn" if rid == R160 else ""), "", "measured", "XRD", "", "", "Sec. III B, 2nd para; Fig. 5")
v("*", "", "vertical_current (new)", "all three samples, at 10 V", ">= ~300", "nA", "measured", "two-point I-V", "", "", "Sec. III B, 3rd para (six orders above noise floor: percolating network)")
# colours
for rid, col in ((R120, "slight yellowing, surface and interior"), (R160, "charcoal gray, surface and interior"), (RCYC, "top surface light gray; interior like 120 C")):
    v(rid, f"{K}:s4" + {R120: "b", R160: "c", RCYC: "d"}[rid], "colour (new)", "", col, "", "measured", "photograph / by eye", "", "", "Sec. III B 1st para; Fig. 4 caption")
v(f"{K}:u10", f"{K}:s4a", "colour (new)", "before ALD", "white", "", "measured", "photograph", "", "", "Sec. III B 1st para; Fig. 4a")
# pressure-trace scalars
v("*", "", "process_pressure", "pulse peak, both reactants", "~9", "Torr", "measured", "Baratron", "", "", "Sec. III A, 2nd para; Fig. 2")
v("*", "", "pressure_spike (new)", "purge, N2 feed-line drops", "~1", "Torr", "measured", "Baratron", "", "", "Fig. 2 caption")
v(RCYC, f"{K}:s3a_120160", "pressure_change (new)", "DEZ hold cycle 15, plateau", "~450", "mTorr", "measured", "pressure trace", "", "", "Sec. III A, 4th para")
v(RCYC, f"{K}:s3a_120160", "time_to_max_pressure_change (new)", "DEZ hold cycle 15, rise duration", "~10", "min", "measured", "pressure trace", "", "", "Sec. III A, 4th para")
v(RCYC, f"{K}:s3a_120160", "terminal_slope (new)", "DEZ hold cycle 15, last ~10 min", "~-2", "mTorr/min", "calculated", "slope of trace", "", "leak-dominated", "Sec. III A, 4th para")
v(R120, f"{K}:s3a_120", "pressure_change (new)", "DEZ hold cycle 15, maximum", "~500", "mTorr", "measured", "pressure trace", "", "", "Sec. III A, 4th para")
v(R120, f"{K}:s3a_120", "time_to_max_pressure_change (new)", "DEZ hold cycle 15", "~15", "min", "measured", "pressure trace", "", "", "Sec. III A, 4th para")
v(R120, f"{K}:s3a_120", "terminal_slope (new)", "DEZ hold cycle 15", "~-1", "mTorr/min", "calculated", "slope of trace", "", "leak-dominated", "Sec. III A, 4th para")
v(R160, f"{K}:s3a_160", "terminal_slope (new)", "DEZ hold cycle 15", "~80", "mTorr/min", "calculated", "slope of trace", "", "reaction ongoing (non-self-limiting)", "Sec. III A, 4th para (cont.)")
v(R160, f"{K}:s3a_160", "pressure_change (new)", "DEZ hold cycle 15, at end of hold", "~2.7", "Torr", "measured", "pressure trace", "", "", "Sec. III A, 4th para (cont.)")
# reaction parameter literature
v("", "", "reaction_parameter_x (new)", "ZnO ALD on silica powder, 80 C", "~1", "1", "literature", "", "Eqs. 4-5", "", "Sec. III A, after Eq. 5 (ref. 10)")
v("", "", "reaction_parameter_x (new)", "ZnO ALD on QCM, 177 C", "1.37", "1", "literature", "QCM", "Eqs. 4-5", "", "Sec. III A, after Eq. 5 (ref. 28)")
v("", "", "reaction_parameter_x (new)", "ZnO ALD on QCM, 80-250 C", "~1.4-1.6", "1", "literature", "QCM", "Eqs. 4-5", "", "Sec. III A, after Eq. 5 (ref. 27)")
# EDS profile
v(R120, f"{K}:s6d_Zn", "zn_profile_shape (new)", "EDS signal, not thickness: Zn K-alpha flat through thickness except within ~0.2 mm of faces", "essentially constant", "", "measured", "SEM-EDS line scan", "", "", "Sec. III C, 1st para")
v(RCYC, f"{K}:s6f_Zn", "zn_profile_shape (new)", "EDS signal, not thickness: Zn K-alpha flat through thickness except within ~0.2 mm of faces", "essentially constant", "", "measured", "SEM-EDS line scan", "", "", "Sec. III C, 1st para")
v(R120, f"{K}:s6d_Zn", "depletion_zone_depth (new)", "Zn decrease near top and bottom faces (XPS: thinner ZnO)", "~0.2", "mm", "measured", "SEM-EDS + XPS", "", "", "Sec. III C 1st-2nd para; Sec. IV")
v(RCYC, f"{K}:s6f_Zn", "depletion_zone_depth (new)", "Zn decrease near top and bottom faces", "~0.2", "mm", "measured", "SEM-EDS + XPS", "", "", "Sec. III C 1st-2nd para; abstract; Sec. IV")
v(R120, "", "eds_zn_ratio (new)", "normalized Zn K-alpha, 120 C vs 120/160 C", "+12", "%", "measured", "SEM-EDS", "", "", "Sec. III C 1st para (vs 10 % higher mass gain)")
v(R160, f"{K}:s6e_Zn", "zn_profile_shape (new)", "EDS signal: Zn K-alpha", "dip near centre of the section", "", "measured", "SEM-EDS line scan", "", "non-self-limiting Zn deposition", "Sec. III C, 3rd para")
v(R120, "", "coated_aspect_ratio", "full thickness infiltrated", "7800", "1", "calculated", "SEM-EDS", "coated AR = structure AR for full coverage", "", "Sec. III C 1st para; abstract; quantity_matrix pd50_or_coated_ar")
v(RCYC, "", "coated_aspect_ratio", "full thickness infiltrated", "7800", "1", "calculated", "SEM-EDS", "coated AR = structure AR for full coverage", "", "Sec. III C 1st para; abstract; Sec. IV")
v(R160, "", "coated_aspect_ratio", "coating spans thickness, non-uniform", "7800", "1", "calculated", "SEM-EDS", "coated AR = structure AR for full coverage", "", "Sec. III C 1st para ('all NPCs infiltrated'); Sec. III B 3rd para (percolating)")
for rid, ser in ((R120, "s6d_Zn"), (R160, "s6e_Zn"), (RCYC, "s6f_Zn")):
    p = pts[("6", {"s6d_Zn": "d", "s6e_Zn": "e", "s6f_Zn": "f"}[ser])]
    v(rid, f"{K}:{ser}", "eds_normalized_counts (new)", f"Zn K-alpha {p['reference']} level", str(p["reference_value"]), "1", "measured", "read by eye (points.json)", "", "", "Fig. 6" + ser[2] + "; cases/points.json reference_value")
v(R160, f"{K}:s6e_Zn", "eds_normalized_counts (new)", "ratio: centre minimum / maximum of Zn K-alpha counts, 0.5-1.4 mm (signal, not thickness)", "0.89", "1", "calculated", "from points.json (5.1/5.7)", "", "", "Fig. 6e; points read by eye")
# literature in introduction
for ev, q, qual, val, unit in [
    ("Sec. I, 1st para", "aspect_ratio", "NP thin films, typical", "~100 or less", "1"),
    ("Sec. I, 1st para", "porosity (new)", "NP thin films, typical", "~0.3-0.5", "1"),
    ("Sec. I, 1st para", "feature_depth", "NP thin films, L", "~100 nm - ~1 um", ""),
    ("Sec. I, 1st para", "feature_width", "NP thin films, d_pore", "~5-20", "nm"),
    ("Sec. I, 1st para", "exposure", "NP thin films, sufficient", "~1 Torr for ~1 s or less", ""),
    ("Sec. I, 2nd para (ref. 9, Gayle)", "porosity (new)", "silica aerogel monolith", "0.95", "1"),
    ("Sec. I, 2nd para (ref. 9)", "aspect_ratio", "silica aerogel monolith, on half-thickness", ">60000", "1"),
    ("Sec. I, 2nd para (ref. 9)", "feature_width", "aerogel d_pore", "~20", "nm"),
    ("Sec. I, 2nd para (ref. 9)", "feature_depth", "aerogel half-thickness", "~1.25", "mm"),
    ("Sec. I, 2nd para (ref. 9)", "exposure", "TMA, 12 doses total, full infiltration", ">1e4", "Torr s"),
    ("Sec. I, 3rd para (ref. 10, Ingale)", "deposition_temperature", "ZnO on mesoporous SiO2 powder", "80", "°C"),
    ("Sec. I, 3rd para (ref. 10)", "specific_surface_area (new)", "mesoporous SiO2", "505", "m2/g"),
    ("Sec. I, 3rd para (ref. 10)", "growth_per_cycle", "ZnO, powder bed", "~1", "Å/cycle"),
    ("Sec. I, 3rd para (ref. 11, Ferguson)", "deposition_temperature", "ZnO on ZrO2 NP powder", "177", "°C"),
    ("Sec. I, 3rd para (ref. 11)", "specific_surface_area (new)", "ZrO2 NP", "20.2", "m2/g"),
    ("Sec. I, 3rd para (ref. 11)", "particle_diameter (new)", "ZrO2 NP", "50", "nm"),
    ("Sec. I, 3rd para (ref. 11)", "growth_per_cycle", "ZnO by TEM", "~2.2", "Å/cycle"),
    ("Sec. I, 3rd para (ref. 11)", "exposure", "DEZ, maximum used", "900", "Torr s"),
    ("Sec. I, 3rd para (ref. 12, Libera)", "specific_surface_area (new)", "silica gel", "100", "m2/g"),
    ("Sec. I, 3rd para (ref. 12)", "exposure", "DEZ, held constant", "22.5", "Torr s"),
    ("Sec. I, 3rd para (ref. 12)", "cycle_number", "ZnO on silica gel", "10", "cycle"),
    ("Sec. I, 3rd para (ref. 12)", "deposition_temperature", "range scanned", "150-200", "°C"),
    ("Sec. I, 3rd para (ref. 12)", "deposition_temperature", "onset of Zn XRD peaks", "155", "°C"),
    ("Sec. I, 3rd para (ref. 12)", "exposure", "no Zn at 200 C below", "<10", "Torr s"),
    ("Sec. I, 3rd para (refs. 4, 6-8)", "deposition_temperature", "ZnO in NP thin films, no Zn", "180", "°C"),
    ("Sec. I, 3rd para (refs. 4, 6-8)", "exposure", "ZnO in NP thin films, DEZ", "<1", "Torr s"),
    ("Abstract", "exposure", "DEZ range giving Zn metal at ~180 C", "10-1e3", "Torr s"),
    ("Sec. I, 4th para (refs. 13-14)", "deposition_temperature", "below this ZnO resistivity often rises with T", "~170", "°C"),
    ("Sec. III B, 3rd para (refs. 13-14)", "film_thickness", "typical ALD ZnO films for electrical work", "~100", "nm"),
    ("Sec. III B, 3rd para (refs. 13-14)", "resistivity", "typical ALD ZnO films", "~1e-2", "Ω cm"),
    ("Sec. I, 4th para (ref. 15)", "purge_time", "H2O desorption rate vs T", "exponential in T", ""),
    ("Sec. III A, 1st para (refs. 14, 25)", "growth_per_cycle", "conventional ZnO ALD on flat substrates, upper end", "~2.1", "Å/cycle"),
    ("Sec. III C, 3rd para", "absorption_edge (new)", "Zn L edge", "~1.2", "keV"),
    ("Sec. III C, 3rd para", "absorption_edge (new)", "Al K edge", "~1.6", "keV"),
    ("Sec. IV, 3rd para (ref. 42)", "temperature_jump (new)", "flash lamp on Si within 5 s", "up to ~400", "°C"),
    ("Sec. IV, 3rd para (ref. 43)", "temperature_jump (new)", "resistive heater on sapphire within 15 s", "up to ~800", "°C"),
]:
    v("", "", q, qual, val, unit, "literature", "", "", "", ev)
counts["value.csv"] = write("value.csv", ["value_id", "sample_id", "from_series", "quantity", "qualifiers", "value", "unit", "data_kind",
                                          "method", "relation", "regime", "evidence"], V)

# ---------------------------------------------------------------- links
L = []
def l(samp, fig, pan, kind, so, ev):
    L.append([samp, fig, pan, kind, so, ev])
for rid in RUNS:
    l(rid, "1", "b", "table", "stated", "Fig. 1b: schedule box labelled with the run name")
    l(rid, "1", "a", "image", "inferred", "Fig. 1a: generic schematic of the NPC in the boat, no run named")
for pan, rid in zip("abc", RUNS):
    l(rid, "2", pan, "plot", "stated", f"Fig. 2 caption ({pan}) names the temperature schedule")
l(f"{K}:u11", "2", "d", "plot", "stated", "Fig. 2 caption (d): test run under the conditions of (c)")
l(RCYC, "2", "d", "plot", "inferred", "Fig. 2d is the temperature programme of the cycled schedule, measured on a separate test run")
for pan in "abc":
    for rid in RUNS:
        l(rid, "3", pan, "plot", "stated", "Fig. 3 caption: colour per schedule (blue 120, red 160, green 120/160)")
l(f"{K}:u10", "4", "a", "image", "stated", "Fig. 4 caption (a) before ALD")
for pan, rid in zip("bcd", RUNS):
    l(rid, "4", pan, "image", "stated", f"Fig. 4 caption ({pan})")
for rid in RUNS:
    l(rid, "5", "", "spectrum", "stated", "Fig. 5 caption: colour/position per schedule")
for pan, rid in zip("abc", RUNS):
    l(rid, "6", pan, "map", "stated", f"Fig. 6 caption ({pan})")
for pan, rid in zip("def", RUNS):
    l(rid, "6", pan, "plot", "stated", "Fig. 6 caption (d)-(f) 'corresponding' to (a)-(c)")
for rid in RUNS:
    l(rid, "Table I", "", "table", "stated", "Table I row by schedule")
    l(rid, "Table II", "", "table", "stated", "Table II row by schedule")
for rid, (a, b) in pair.items():
    for u in (a, b):
        l(f"{K}:{u}", "Table I", "", "table", "stated", "Table I caption: values are pair means/totals, +- is within-pair variability; individual NPC values not given")
for rid, u in zip(RUNS, ("u7", "u8", "u9")):
    l(f"{K}:{u}", "Table II", "", "table", "stated", "Table II resistivity column; Sec. III B: one NPC measured per condition")
counts["link.csv"] = write("link.csv", ["sample_id", "figure", "panel", "kind", "stated_or_inferred", "evidence"], L)

json.dump(counts, sys.stdout, indent=1)
