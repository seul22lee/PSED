#!/usr/bin/env python3
"""Fresh v2 extraction of 10.1116_6.0003182 (gre23). Writes the five tables + coverage.csv into schema_pilot/v2/<paper_id>/."""
import csv, json, sys
from pathlib import Path

PID = "10.1116_6.0003182"
K = "gre23"
OUT = Path("/home/ftk3187/github/PSED/psed_v2/schema_pilot/v2") / PID
V2 = Path("/home/ftk3187/github/PSED/psed_v2")
TORR = 133.322

def pa(torr):
    v = torr * TORR
    return f"{v:.4g}" if v < 1e5 else f"{v:.3e}".replace("e+0", "e").replace("e+", "e")

samples, conds, series, values = [], [], [], []

# ---------------------------------------------------------------- samples
SC = ["sample_id", "paper_id", "kind", "label_as_printed", "parent_sample", "members", "material", "precursor", "coreactant",
      "process_mode", "reactor", "structure_class", "structure_dims", "width_kind", "note", "evidence"]
def S(sid, kind, label="u", parent="", members="", material="", precursor="", coreactant="", process_mode="", reactor="",
      structure_class="", structure_dims="", width_kind="", note="", evidence=""):
    samples.append(dict(sample_id=f"{K}:{sid}", paper_id=PID, kind=kind, label_as_printed=label,
                        parent_sample=f"{K}:{parent}" if parent else "",
                        members=";".join(f"{K}:{m}" for m in members) if members else "", material=material,
                        precursor=precursor, coreactant=coreactant, process_mode=process_mode, reactor=reactor,
                        structure_class=structure_class, structure_dims=structure_dims, width_kind=width_kind, note=note,
                        evidence=evidence))

REACTOR = "ALD NanoSolutions (Forge Nano) custom RX-series; roughly horizontal cylindrical chamber about 20 cm long, 10 cm ID, isolation valve to pump"
NPC_DIMS = "pressed alpha-Al2O3 NP disc: thickness 2L = 1.55 mm (L = 0.78 mm), diameter 11.43 mm, d_NP ~ d_pore ~ 100 nm, initial porosity 50.5%, AR = L/d_pore = 7800; precursors enter both faces"
RUN = dict(material="ZnO", precursor="DEZ (diethylzinc)", coreactant="H2O", process_mode="thermal ALD, static dosing (pulse then closed-chamber hold)",
           reactor=REACTOR, structure_class="nanoparticle compact", structure_dims=NPC_DIMS, width_kind="d")
RUNS = [("R120", "120", "T held at 120 C for every step", "tabI.r1c0, tabII.r1c0, tabI.r0c0, tabII.r0c0, s9.p6, fig1; run (1) of three, sample label 120 in both tables, schedule in Fig. 1b"),
        ("R160", "160", "T held at 160 C for every step", "tabI.r2c0, tabII.r2c0, s9.p6, fig1; run (2), label 160 in both tables, Fig. 1b schedule"),
        ("R120-160", "120/160", "T cycled: 120 C for all steps, ramped to 160 C and back during each H2O purge",
         "tabI.r3c0, tabII.r3c0, s9.p6, fig1; run (3), label 120/160 in both tables, Fig. 1b schedule")]
TAG = {"R120": "120", "R160": "160", "R120-160": "cyc"}
for rid, lab, note, ev in RUNS:
    S(rid, "run", lab, note=f"20-cycle ZnO run; {note}; two NPCs coated together", evidence=ev, **RUN)
for rid, lab, _, _ in RUNS:
    for n in (1, 2):
        S(f"{rid}-NPC{n}", "piece", "u", parent=rid, material="ZnO on Al2O3 NPs", structure_class="nanoparticle compact",
          structure_dims=NPC_DIMS, width_kind="d",
          note=f"one of the two NPCs of run {lab}, weighed before and after ALD; which of the pair went to XRD, EDS and the photograph is not stated",
          evidence="s12.p1, s9.p3, tabI.cap; two NPCs per run, all weighed; Table I values are per pair")
    S(f"{rid}-pair", "group", "u", members=[f"{rid}-NPC1", f"{rid}-NPC2"],
      note=f"the pair of NPCs coated in run {lab}; mass gain and derived values are pair averages (+/- = spread within the pair)",
      evidence="tabI.cap, s12.p1; pair of NPCs per run, +/- = sample-to-sample spread")
    S(f"{rid}-prism", "piece", "u", parent=rid, material="ZnO on Al2O3 NPs, Ti/Au faces", structure_class="nanoparticle compact",
      structure_dims="prism about 6 x 3 x 1.6 mm cut from one coated NPC after Ti/Au deposition on top and bottom faces", width_kind="d",
      note=f"resistivity piece of run {lab}; only one NPC per run was measured", evidence="s10.p2, s13.p4; prism cut from Ti/Au-coated NPC, one per condition")
S("Rtest", "run", "u", material="ZnO", precursor="DEZ (diethylzinc)", coreactant="H2O", process_mode=RUN["process_mode"], reactor=REACTOR,
  note="ZnO ALD test run under the same conditions as the 120/160 run, logged with a thermocouple touching the boat (Fig. 2d); whether NPCs were loaded is not stated",
  evidence="fig2d, fig2.cap; boat temperature logged in a separate test run with the cycled schedule")
S("bare", "reference", "Before ALD", material="Al2O3", structure_class="nanoparticle compact", structure_dims=NPC_DIMS, width_kind="d",
  note="uncoated Al2O3 NPC photographed before ALD (Fig. 4a); white", evidence="fig4, fig4.cap; panel a, compact before ALD")
S("runs", "group", "u", members=["R120", "R160", "R120-160"], note="the three 20-cycle ZnO runs", evidence="s9.p6, s6.p8; three 20-cycle runs")
S("lowT", "group", "u", members=["R120", "R120-160"], note="the 120 and 120/160 runs, for statements made about both",
  evidence="s14.p1, s13.p4; statements made jointly for 120 and 120/160")
S("compacts", "group", "u", members=[f"{r}-NPC{n}" for r, *_ in RUNS for n in (1, 2)] + ["bare"],
  note="all pressed Al2O3 NPCs of the paper (same pressing recipe)", evidence="s8.p1; pressing recipe for all NPCs")
S("prisms", "group", "u", members=["R120-prism", "R160-prism", "R120-160-prism"], note="the three resistivity prisms",
  evidence="s10.p2; resistivity samples")
S("eq2-120", "model_run", "u", note="Eq. 2 estimate of the H2O purge time at T = 120 C (desorption energy given only in Note S1 of the SI)",
  evidence="eq2, s9.p9; purge time estimate at 120 C")
S("eq2-160", "model_run", "u", note="Eq. 2 estimate of the H2O purge time at T = 160 C", evidence="eq2, s9.p9; purge time estimate at 160 C")
S("eq2", "group", "u", members=["eq2-120", "eq2-160"], note="the two Eq. 2 purge-time estimates (shared inputs)", evidence="s9.p9, eq2; shared inputs of the estimate")

# ---------------------------------------------------------------- conditions
CC = ["condition_id", "sample_id", "kind", "quantity", "label_as_printed", "qualifiers", "value", "unit", "data_kind", "applies_when", "note", "evidence"]
def C(sid, kind, q, value, unit, ev, label="", qual="", dk="stated", when="", note=""):
    conds.append(dict(condition_id=f"{K}:c{len(conds) + 1:03d}", sample_id=sid if sid == "*" else f"{K}:{sid}", kind=kind, quantity=q,
                      label_as_printed=label, qualifiers=qual, value=value, unit=unit, data_kind=dk, applies_when=when, note=note, evidence=ev))

TNOTE = "T = boat inner-surface temperature at steady state under 20 sccm N2, rounded to 10 C; measured boat T varied about +/-5 C among calibration runs with the same jacket setting; chamber wall about equal to T"
C("R120", "process", "deposition_temperature", "120", "°C", "s9.p6, fig1, fig2a, s6.p8; run (1) at constant 120 C", qual="kind=set_point", note=TNOTE)
C("R160", "process", "deposition_temperature", "160", "°C", "s9.p6, fig1, fig2b, s6.p8; run (2) at constant 160 C", qual="kind=set_point", note=TNOTE)
C("R120-160", "process", "deposition_temperature", "120", "°C", "s9.p6, fig1, fig2c, s6.p8; run (3) base temperature 120 C", qual="kind=set_point",
  when="every step except the H2O purge", note=TNOTE)
C("R120-160", "process", "deposition_temperature", "160", "°C", "s9.p6, fig1, fig2c, s6.p8; run (3) H2O purge ramped to 160 C and back",
  qual="kind=set_point;step=purge_B", note="ramped from 120 up to 160 C and back to 120 C within each H2O purge, before the next DEZ pulse")
C("R120-160", "process", "other", "2010", "s", "s15.p4; heating ramp 120 to 160 C took 33.5 min", label="temperature ramp time, 120 to 160 C",
  note="printed 33.5 min; chamber heated by jacket")
C("Rtest", "process", "deposition_temperature", "120", "°C", "fig2d, fig2.cap; test run under the same conditions as the cycled run",
  qual="kind=set_point", when="every step except the H2O purge", note="same schedule as run 120/160 (stated)")
C("Rtest", "process", "deposition_temperature", "160", "°C", "fig2d, fig2.cap; test run, H2O purge at 160 C", qual="kind=set_point;step=purge_B",
  note="same schedule as run 120/160 (stated)")
C("runs", "process", "cycle_number", "20", "", "s9.p4, s9.p6, s6.p8, s15.p1; each run had 20 ALD cycles")
C("runs", "process", "other", "1", "", "s9.p6, fig2.cap; one H2O half-cycle before cycle 1 to hydroxylate the alumina", label="H2O half-cycle before the first cycle")
C("runs", "process", "other", "7200", "s", "s9.p6; NPCs degassed at least 2 h in the chamber at the initial T", label="degassing time before ALD",
  note="at least 2 h, at the initial T (120 or 160 C)")
C("runs", "process", "pulse_time", "10-14", "s", "s9.p4; DEZ pulse 10-14 s, adjusted by hand", qual="step=reactant_A",
  note="range; pulse length varied manually to keep the exposure pressure near 9 Torr")
C("runs", "process", "other", "1920", "s", "s9.p4, s6.p8, s12.p1, eq1, s9.p7, s9.p8; DEZ hold 32 min, hold time designed with Eq. 1", label="DEZ hold", qual="step=hold_A",
  note="hold_time; printed 32 min; chamber isolated, all valves closed; hold set from Eq. 1 (pore length squared over Knudsen diffusivity times reactant molecules per site)")
C("runs", "process", "purge_time", "2880", "s", "s9.p4, s14.p6; DEZ purge 48 min, not optimised, set equal to the H2O purge", qual="step=purge_A",
  note="printed 48 min; not optimised (copied from the H2O purge)")
C("runs", "process", "pulse_time", "8-11", "s", "s9.p4; H2O pulse 8-11 s", qual="step=reactant_B", note="range; varied manually")
C("runs", "process", "other", "1920", "s", "s9.p4, s6.p8, eq1, s9.p7; H2O hold 32 min", label="H2O hold", qual="step=hold_B",
  note="hold_time; printed 32 min; set from Eq. 1")
C("runs", "process", "purge_time", "2880", "s", "s9.p4, s9.p9, s12.p1, s15.p3; H2O purge 48 min, chosen with Eq. 2", qual="step=purge_B",
  note="printed 48 min; chosen so that residual H2O coverage below 5e-3 is reached in the 120/160 and 160 C processes (Eq. 2 estimates 360 min at 120 C, 11 min at 160 C)")
C("runs", "process", "cycle_time", "9600", "s", "s9.p4; one cycle about 160 min", note="printed ~160 min")
for st, sp, ev in (("reactant_A", "DEZ", "s9.p4, s6.p8, s12.p2, s12.p1; DEZ exposure pressure about 9 Torr"),
                   ("reactant_B", "H2O", "s9.p4, s6.p8, s12.p2; H2O exposure pressure about 9 Torr")):
    C("runs", "process", "partial_pressure", pa(9), "Pa", ev, qual=f"step={st};species={sp}",
      note="printed ~9 Torr; fluctuated between pulses (manual valves, unheated line sections); during pulse and hold the pump isolation valve was closed")
    C("runs", "process", "exposure", pa(17000), "Pa s", "s6.p8; exposure about 17 000 Torr s per reactant (9 Torr for 32 min)",
      qual=f"step={st};species={sp}", note="printed ~17 000 Torr s (pressure times hold time)")
    C("runs", "process", "source_temperature", "37", "°C", "s9.p4; stainless cylinders at 37 C, metering valves", qual=f"species={sp}")
C("runs", "process", "precursor_purity", "95", "%", "s9.p4; DEZ minimum 95% (Strem)", qual="species=DEZ", note="minimum purity; H2O de-ionized")
for st in ("purge_A", "purge_B"):
    C("runs", "process", "gas_flow_rate", "20", "sccm", "s9.p5, fig2.cap; N2 purge sequence, 10 sccm through each manifold half", qual=f"step={st};gas=N2",
      note="sequence: 30 s no flow, 30 s at 10 sccm through the half just used, 2790 s at 10 sccm through each half (20 sccm total), 30 s no flow; pump isolation valve open")
C("runs", "process", "other", "2.17", "L", "s9.p5; isolated deposition volume from pressure vs flow tests", label="isolated deposition volume",
  note="includes small tubing volumes besides the main cylinder")
C("runs", "process", "other", "20", "cm", "s9.p1; chamber length about 20 cm", label="chamber length")
C("runs", "process", "other", "10", "cm", "s9.p1; chamber inner diameter about 10 cm", label="chamber inner diameter")
C("runs", "process", "other", "1", "mm", "s9.p3, s9.p1, fig1; NPCs in rounded quartz boat, gap up to about 1 mm under the bottom face",
  label="gap under the NPC bottom face (maximum)", note="only the bottom circular edge touches the boat, so both faces see the gas")
C("runs", "process", "other", "100-130", "°C", "s9.p6; tubing outside the main chamber heated by tape", label="heating-tape external surface temperature of tubing")
C("runs", "process", "other", "90-120", "°C", "s9.p6, s12.p6; expected internal surface temperatures of the tubing", label="tubing internal surface temperature",
  dk="assumed", note="expected from the external values")
C("runs", "process", "other", "<90", "°C", "s9.p6, s12.p6; unheated windows possibly colder than 90 C", label="internal temperature of unheated surfaces (windows)",
  dk="assumed", note="quartz and sapphire windows not directly heated")
# measurement: pressure
C("runs", "measurement", "other", "100", "°C", "s9.p3; two heated capacitance manometers", label="manometer temperature", note="MKS Baratron 728A")
C("runs", "measurement", "other", "10", "Torr", "s9.p3, fig3.cap; low-range gauge full scale", label="full-scale range, gauge 1")
C("runs", "measurement", "other", "1000", "Torr", "s9.p3, fig3.cap; high-range gauge full scale (used for the noisy part of the 160 C trace)", label="full-scale range, gauge 2")
C("runs", "measurement", "other", "0.26", "Torr", "s9.p3; constant offset subtracted so base reads 0 at 120 C", label="pressure offset",
  note="base pressure unknown because of gauge drift; analysis uses pressure changes only")
C("runs", "measurement", "other", "10", "mTorr", "s12.x1, fig3a; recorded pressure resolution limits the slope analysis",
  label="recorded pressure resolution")
C("runs", "measurement", "other", "10", "min", "fig3.cap, fig3c, s12.p8; terminal slope averaged over the last 10 min of the DEZ hold", label="terminal-slope window")
# substrate prep
C("compacts", "substrate_prep", "substrate", "alpha-Al2O3 nanopowder compact (BMA15, Baikowski)", "", "s8.p1; deagglomerated alpha alumina nanopowder pressed into discs",
  note="pressed in ambient air; some mm-scale cracks (Fig. S1 of the SI)")
C("compacts", "substrate_prep", "other", "15", "m2/g", "s8.p1, s10.p1; BET specific surface area, manufacturer spec", label="powder specific surface area")
C("compacts", "substrate_prep", "other", "0.320", "g", "s8.p1; powder mass per compact", label="powder mass", note="+/- 0.005 g")
C("compacts", "substrate_prep", "other", "481", "MPa", "s8.p1; uniaxial pressing load", label="pressing pressure", note="12 ton manual hydraulic press (Carver)")
C("compacts", "substrate_prep", "other", "11.4", "mm", "s8.p1; tungsten carbide die diameter", label="die diameter")
C("compacts", "substrate_prep", "other", "<60", "s", "s8.p1; load held under 1 min", label="pressing hold time", note="printed < 1 min")
# eq2 model runs
C("eq2-120", "process", "deposition_temperature", "120", "°C", "s9.p9, eq2; purge temperature of the estimate", qual="kind=set_point")
C("eq2-160", "process", "deposition_temperature", "160", "°C", "s9.p9, eq2; purge temperature of the estimate", qual="kind=set_point")
# measurement: characterisation
C("runs", "measurement", "other", "Cu Ka1", "", "s10.p1; rotating-anode powder diffractometer (Rigaku)", label="XRD radiation", note="NPCs exposed to air before and during XRD and resistivity")
C("runs", "measurement", "other", "50", "kV", "s10.p1; XRD generator voltage", label="XRD tube voltage")
C("runs", "measurement", "other", "200", "mA", "s10.p1; XRD generator current", label="XRD tube current")
C("runs", "measurement", "other", "20-80", "deg", "s10.p1, fig5; 2-theta range", label="XRD 2theta range")
C("runs", "measurement", "other", "1", "deg/min", "s10.p1; scan speed", label="XRD scan rate")
C("runs", "measurement", "other", "0.02", "deg", "s10.p1; step", label="XRD step size",
  note="outer surface scanned, then fractured interior; no significant difference; Fig. 5 shows top surfaces (s13.p2)")
C("runs", "measurement", "other", "30", "kV", "s10.p3; EDS accelerating voltage", label="SEM-EDS accelerating voltage",
  note="Quattro S ESEM with EDAX detector; cross sections sectioned, epoxy-mounted, ground, polished and coated (Note S2)")
C("runs", "measurement", "other", "63", "nA", "s10.p3; probe current", label="SEM-EDS probe current")
C("runs", "measurement", "other", "50", "µm", "s10.p3; aperture", label="SEM-EDS aperture")
C("runs", "measurement", "other", "10", "mm", "s10.p3; working distance", label="SEM-EDS working distance")
C("runs", "measurement", "other", "0.96", "µs", "s10.p3; amplifier time", label="EDS amp time")
C("runs", "measurement", "other", "1.5 x 1", "mm", "s10.p4, fig6ac; mapped area through the thickness", label="EDS map area")
C("runs", "measurement", "other", "200", "µs", "s10.p4; map dwell per pixel", label="EDS map dwell time", note="32 frames")
C("runs", "measurement", "other", "100", "", "s10.p4, fig6d; line scan points through the thickness near the centre line", label="EDS line scan points")
C("runs", "measurement", "other", "100", "µm", "s10.p4; line scan width", label="EDS line scan width")
C("runs", "measurement", "other", "20", "ms", "s10.p4; dwell per line point, 512 frames", label="EDS line scan dwell time", note="512 frames")
C("runs", "measurement", "other", "1486.7", "eV", "s10.p5; monochromatic Al Ka XPS source (Nexsa)", label="XPS source energy", note="XPS spectra are in the SI only (Figs. S3, S4)")
C("runs", "measurement", "probe_resolution", "125", "µm", "s10.p5; XPS spot", label="XPS spot size")
C("runs", "measurement", "other", "1", "keV", "s10.p5; Ar ion etch energy", label="XPS Ar etch energy", note="spectra before and after 15 s and 30 s etch")
C("runs", "measurement", "other", "200", "eV", "s10.p5; survey pass energy, 1 eV step", label="XPS survey pass energy", note="1 eV step")
C("runs", "measurement", "other", "20", "eV", "s10.p5; high-resolution pass energy, 0.1 eV step, Al 2p, C 1s, O 1s, Zn 2p", label="XPS high-resolution pass energy", note="0.1 eV step")
C("runs", "measurement", "other", "284.8", "eV", "s10.p5; adventitious C 1s reference", label="XPS binding energy reference")
C("prisms", "measurement", "other", "20", "nm", "s10.p2, tabII.cap; e-beam Ti layer on top and bottom faces", label="Ti contact thickness (nominal)")
C("prisms", "measurement", "other", "200", "nm", "s10.p2, tabII.cap; e-beam Au layer", label="Au contact thickness (nominal)")
C("prisms", "measurement", "other", "1e-6", "Torr", "s10.p2; evaporation pressure", label="e-beam evaporation pressure")
C("prisms", "measurement", "other", "10", "V", "s10.p2, s13.p4; two-point measurement voltage through the thickness", label="measurement voltage",
  note="one probe on top pad, other via conductive stage; resistance converted with electrode area, reduced by flaking")

# ---------------------------------------------------------------- series
SR = ["series_id", "sample_id", "kind", "figure", "panel", "method", "x_id", "x_qualifiers", "x_label", "y_id", "y_qualifiers", "y_label",
      "z_id", "z_label", "data_kind", "link_status", "points_source", "points", "reused_from", "note", "evidence"]
def SE(sid, sample, kind, fig, panel, method, ev, x=("", "", ""), y=("", "", ""), z=("", ""), dk="measured", link="stated",
       psrc="", pts="", note=""):
    series.append(dict(series_id=f"{K}:{sid}", sample_id=f"{K}:{sample}" if sample else "", kind=kind, figure=fig, panel=panel, method=method,
                       x_id=x[0], x_qualifiers=x[1], x_label=x[2], y_id=y[0], y_qualifiers=y[1], y_label=y[2], z_id=z[0], z_label=z[1],
                       data_kind=dk, link_status=link, points_source=psrc, points=pts, reused_from="", note=note, evidence=ev))

SE("F1a", "compacts", "image", "1", "a", "schematic", "fig1, fig1.cap; sketch of an NPC in the quartz boat with labelled dimensions", dk="schematic",
   note="DEZ or H2O in, ethane out, both faces; T marked under the boat")
SE("F1b", "runs", "table", "1", "b", "schematic", "fig1, fig1.cap; which steps run at 120 C and which at 160 C for the three schedules", dk="schematic",
   note="a dose = pulse plus hold")
for rid, pan in (("R120", "a"), ("R160", "b"), ("R120-160", "c")):
    SE(f"F2{pan}", rid, "plot", "2", pan, "process_monitor", f"fig2{pan}, fig2.cap; chamber pressure trace, first five cycles plus the initial H2O half-cycle",
       x=("other", "", "Time (hr)"), y=("process_pressure", "", "p (Torr)"),
       note="pulse/hold/purge blocks; DEZ hold rises slightly, H2O hold falls; all 20 cycles in the SI")
SE("F2d", "Rtest", "plot", "2", "d", "process_monitor", "fig2d, fig2.cap; boat inner-surface temperature logged in the test run",
   x=("other", "", "Time (hr)"), y=("deposition_temperature", "kind=measured", "T (°C)"), note="thermocouple touching the boat; aligned with Fig. 2c time axis")
for rid in ("R160", "R120", "R120-160"):
    t = TAG[rid]
    SE(f"F3a-{t}", rid, "plot", "3", "a", "process_monitor", f"fig3a, fig3.cap; pressure change during the cycle-15 DEZ hold, legend {t}",
       x=("other", "", "Elapsed time, δt (min)"), y=("other", "", "Pressure change, δp (Torr)"),
       note="hold start pressure (~9 Torr) subtracted; arrows mark the net change Δp and the terminal slope")
    SE(f"F3b-{t}", rid, "plot", "3", "b", "process_monitor", f"fig3b, fig3.cap, s12.p8; net gain of gas moles per DEZ hold against cycle, legend {t}",
       x=("cycle_number", "", "Cycle number"), y=("other", "", "Net gain of gas moles, Δn_g (µmol)"), dk="calculated",
       note="from Δp with a correction for the leak across the stop valve and for reaction during the pulse (Note S3)")
    SE(f"F3c-{t}", rid, "plot", "3", "c", "process_monitor", f"fig3c, fig3.cap; terminal slope of the DEZ hold against cycle, legend {t}",
       x=("cycle_number", "", "Cycle number"), y=("other", "", "Terminal slope, TS (mTorr/min)"),
       note="mean pressure slope over the last 10 min of the hold")
for sid, pan, smp, nt in (("F4a", "a", "bare", "white, before ALD"), ("F4b", "b", "R120", "slight yellowing; interior similar"),
                          ("F4c", "c", "R160", "charcoal gray surface and interior"), ("F4d", "d", "R120-160", "light gray top surface only; interior like panel b")):
    SE(sid, smp, "image", "4", pan, "photograph", f"fig4, fig4.cap, s13.p1; photograph of the top face, panel {pan}", note=nt)
for rid, nt in (("R120", "blue, top pattern; corundum and broad zincite"), ("R160", "red, middle; also metallic Zn peaks"), ("R120-160", "green, bottom; corundum and broad zincite")):
    SE(f"F5-{TAG[rid]}", rid, "spectrum", "5", "", "xrd", f"fig5, fig5.cap, s13.p2; XRD pattern of the top surface, {TAG[rid]} run",
       x=("other", "", "2θ (deg.)"), y=("other", "", "Normalized counts"), note=nt)
for ph, card in (("Zn", "00-004-0831"), ("ZnO", "04-001-7297"), ("Al2O3", "04-002-5941")):
    SE(f"F5-ref-{ph}", "", "spectrum", "5", "", "cited", f"fig5, fig5.cap, s10.p1; reference stick pattern for {ph}", x=("other", "", "2θ (deg.)"),
       y=("other", "", "Normalized counts"), dk="cited", link="stated", note=f"ICDD PDF {card}")
for rid, pan in (("R120", "a"), ("R160", "b"), ("R120-160", "c")):
    extra = "; cross section incomplete (top ~0.4 mm lost in handling)" if rid == "R160" else ""
    SE(f"F6{pan}-SE", rid, "image", "6", pan, "sem", f"fig6ac, fig6.cap; SE image of the cross section, panel {pan}",
       x=("distance", "", "u"), y=("distance", "", "u"), note="scale bar 0.5 mm" + extra)
    for el in ("Al", "Zn"):
        SE(f"F6{pan}-{el}", rid, "map", "6", pan, "sem_eds", f"fig6ac, fig6.cap, s14.p1; {el} Ka map of the cross section, panel {pan}",
           x=("distance", "", "u"), y=("distance", "", "u"), z=("composition", f"{el} map"), note=f"element={el}; full thickness" + extra)
PTS = {}
for s in json.load(open(V2 / "cases/points.json"))["series"]:
    if s["paper"] == PID and s["series"].startswith("Zn"):
        PTS[s["panel"]] = s
for rid, pan in (("R120", "d"), ("R160", "e"), ("R120-160", "f")):
    for el in ("Al", "Zn", "O", "C"):
        p = PTS[pan] if el == "Zn" else None
        SE(f"F6{pan}-{el}", rid, "plot", "6", pan, "sem_eds", f"fig6{pan}, fig6.cap; {el} Ka line scan through the thickness, panel {pan}",
           x=("composition", f"element={el}", "Normalized X-ray counts"), y=("distance", "origin=top_face", "Postion (mm)"),
           psrc="cases/points.json" if p else "", pts=json.dumps(p["points"]) if p else "",
           note="axes swapped (position vertical, 0 at the top of the section); counts normalised to the total over all elements and positions; alignment with the maps approximate"
                + ("; points read by eye: " + p["quality"] if p else "") + ("; section starts at ~0.42 mm" if rid == "R160" else ""))

# ---------------------------------------------------------------- values
VC = ["value_id", "sample_id", "from_series", "quantity", "label_as_printed", "qualifiers", "value", "value_min", "value_max", "censor", "unit",
      "data_kind", "method", "relation", "regime", "cited_ref", "note", "evidence"]
def V(sid, q, value, unit, dk, method, ev, label="", qual="", vmin="", vmax="", censor="", fs="", rel="", regime="", ref="", note=""):
    values.append(dict(value_id=f"{K}:v{len(values) + 1:03d}", sample_id=f"{K}:{sid}" if sid else "", from_series=f"{K}:{fs}" if fs else "",
                       quantity=q, label_as_printed=label, qualifiers=qual, value=value, value_min=vmin, value_max=vmax, censor=censor, unit=unit,
                       data_kind=dk, method=method, relation=rel, regime=regime, cited_ref=ref, note=note, evidence=ev))

# compacts (structure)
V("compacts", "other", "1.55", "mm", "measured", "", "s8.p1; compact thickness by calipers", label="NPC thickness 2L", note="+/- 0.05 mm")
V("compacts", "other", "11.43", "mm", "measured", "", "s8.p1; compact diameter by calipers", label="NPC diameter", note="+/- 0.02 mm")
V("compacts", "other", "50.5", "%", "measured", "", "s8.p1, s6.p8, s15.p2, s12.p1, tabI.cap, s13.p5; initial porosity of the compacts", label="initial porosity φi",
  note="+/- 0.3%; how it was obtained is not stated; Table I caption and s12.p1 print it as φf / φ1 (typo)")
V("compacts", "other", "100", "nm", "calculated", "calculation", "s8.p1, s10.p1; NP diameter from the BET surface area spec", label="d_NP",
  rel="d_NP from specific surface area 15 m2/g")
V("compacts", "feature_width", "100", "nm", "assumed", "", "s8.p1, s6.p8, s14.p10; pore diameter taken equal to d_NP at 50% porosity", label="d_pore",
  note="approximate equality stated, not measured")
V("compacts", "feature_depth", "780000", "nm", "calculated", "calculation", "s6.p8, s15.p2, fig1; L = half the compact thickness (both faces open)", label="L",
  rel="L = thickness / 2", note="printed 0.78 +/- 0.02 mm")
V("compacts", "aspect_ratio", "7800", "", "calculated", "calculation", "s6.p8, s15.p2; AR from half-thickness over pore diameter", label="AR",
  qual="basis=AR", rel="AR = L / d_pore", note="+/- 200")
V("compacts", "other", "100", "", "calculated", "calculation", "s6.p8; AR about 100 times that of NP thin films coated with ZnO before",
  label="AR relative to typical ZnO-coated NP thin films", note="order of magnitude")
V("compacts", "other", "11.4", "mm", "measured", "", "fig1, fig1.cap; diameter label on the sketch", fs="F1a", label="~11.4 mm", note="rounded label")
V("compacts", "other", "1.6", "mm", "measured", "", "fig1, fig1.cap; thickness label on the sketch", fs="F1a", label="2L ≈ 1.6 mm", note="rounded label")
V("compacts", "other", "51", "%", "measured", "", "fig1, fig1.cap; porosity label on the sketch", fs="F1a", label="φi ≈ 51%", note="rounded label")
V("compacts", "other", "100", "nm", "calculated", "", "fig1, fig1.cap; NP diameter label on the sketch", fs="F1a", label="d_NP = 100 nm")
V("bare", "other", "11.4", "mm", "measured", "photograph", "fig4; diameter arrow on the uncoated compact photo", fs="F4a", label="~11.4 mm")
V("runs", "other", "", "nm", "fit", "xrd", "s10.p1; corundum grain size from Halder-Wagner, matches d_NP", label="corundum grain size", vmin="90", vmax="100",
  rel="Halder-Wagner crystallite size analysis (JADE 9)")
V("runs", "other", "15", "%", "fit", "xrd", "s10.p1; whole-pattern residual stabilised within one point of 15% for all three", label="Rietveld residual",
  vmin="14", vmax="16")
# Table I and text (pairs / runs)
TI = {"R120": 1, "R160": 2, "R120-160": 3}
DATA = {"R120": dict(mg="28.4", mge="0.1", por="36.7", pore="0.1", gpc="2.37", gpce="0.02", ns="150", ng="59.3", y="1.395"),
        "R160": dict(mg="36.4", mge="1.6", por="30.6", pore="1.4", gpc="3.48", gpce="0.26", ns="217", ng="191", y="1.880"),
        "R120-160": dict(mg="26.4", mge="0.1", por="38.0", pore="0.1", gpc="2.14", gpce="0.01", ns="139", ng="50.8", y="1.365")}
for rid, d in DATA.items():
    r = TI[rid]; t = TAG[rid]; pair = f"{rid}-pair"
    V(pair, "other", d["mg"], "%", "measured", "gravimetry", f"tabI.r{r}c1, tabI.r0c1, s12.p1, s13.p3, tabI.cap; mass gain of the pair, {t} run",
      label="Mass gain (%)", note=f"+/- {d['mge']} = spread within the pair; also called coating weight percentage")
    V(pair, "other", d["por"], "%", "calculated", "calculation", f"tabI.r{r}c2, tabI.r0c2, s12.p1; final porosity, {t} run", label="Final porosity, φf (%)",
      rel="porosity reduction from mass gain assuming uniform coating",
      note=f"+/- {d['pore']}; the text lists 36.7, 30.6, 38.0 for 120/160, 120, 160, an order that contradicts the table and the mass gains; table order kept")
    V(pair, "growth_per_cycle", d["gpc"], "Å", "calculated", "calculation",
      f"tabI.r{r}c3, tabI.r0c3, s12.p1, tabI.cap" + (", s15.p2" if rid == "R120-160" else ", s15.p3" if rid == "R120" else "") + f"; GPC from mass gain, {t} run",
      label="GPC (Å/cyc)", rel="porosity loss to coating thickness, mean of spherical-NP and spherical-pore models, over 20 cycles",
      note=f"+/- {d['gpce']} = spread in mass gain within the pair")
    V(pair, "other", d["ns"], "µmol/cyc", "calculated", "calculation", f"tabI.r{r}c4, tabI.r0c4, s12.p9, eq3, tabI.cap; moles of solid per cycle assuming ZnO, {t} run",
      label="Δn_s (µmol/cyc)", rel="eq3: GPC converted to moles of ZnO deposited on the pair per cycle", note="measurement uncertainty about +/- 0.1")
    V(rid, "other", d["ng"], "µmol/cyc", "calculated", "process_monitor", f"tabI.r{r}c5, tabI.r0c5, s12.p9, tabI.cap; cycle-averaged gas mole gain over the DEZ hold, {t} run",
      fs=f"F3b-{t}", label="Δn_g (µmol/cyc)", rel="mean over 20 cycles of Δn_g from Fig. 3b", note="measurement uncertainty about +/- 0.1")
    rel = "eq6: y = 1 + Δn_g/Δn_s; eq7: equals the mean reaction parameter x when only Eqs. 4-5 occur" if rid != "R160" else \
          "eq6: y = 1 + Δn_g/Δn_s; eq8: y = x + c, c from Zn metal deposition (2 ethane per DEZ, ZnO molar mass overestimates)"
    V(rid, "other", d["y"], "", "calculated", "calculation",
      f"tabI.r{r}c6, tabI.r0c6, s12.p14, s12.p15, eq6, eq7, eq8, s12.p10, s12.p11, s12.p13, s12.p17; gas-solid product ratio, {t} run",
      fs=f"F3b-{t}", label="ȳ = Δn_g/Δn_s + 1", rel=rel, note="measurement uncertainty about +/- 0.001; printed as ν̄ in the text layer")
V("R120-pair", "film_thickness", "4.73", "nm", "calculated", "calculation", "s13.p3; coating thickness inferred from mass gain, 120 run",
  rel="20 cycles x GPC from mass gain", note="+/- 0.03")
V("R120-160-pair", "film_thickness", "4.28", "nm", "calculated", "calculation", "s13.p3; coating thickness inferred from mass gain, 120/160 run",
  rel="20 cycles x GPC from mass gain", note="+/- 0.03")
V("R120", "other", "", "nm", "calculated", "calculation", "s14.p10; extra deposition of the 120 run over the cycled run", label="excess coating thickness vs 120/160",
  vmin="0.4", vmax="0.5", rel="4.73 - 4.28 nm", note="compared with ~100 nm pores")
V("R120", "other", "10", "%", "calculated", "calculation", "s14.p10; GPC of the 120 run about 10% above the cycled run", label="GPC difference vs 120/160")
V("R120", "other", "10", "%", "calculated", "gravimetry", "s14.p1; fractional mass gain 10% higher than the cycled run", label="fractional mass gain vs 120/160")
V("runs", "other", "1", "", "calculated", "process_monitor", "s12.p6, eq4, eq5, fig2a, fig2b, fig2c; pressure rises in DEZ hold and falls in H2O hold, so x above 1",
  label="reaction parameter x", censor=">", rel="eq4, eq5: net gas gain in the DEZ half-reaction when x > 1", note="inferred from the sign of the hold pressure change")
# Fig 2 / Fig 3a
V("runs", "other", "1", "Torr", "measured", "process_monitor", "fig2.cap, s12.p12; spikes and dips in purges from N2 line pressure drops", label="purge pressure spikes",
  note="artefact: glovebox drawing N2 from the shared feed line")
V("Rtest", "deposition_temperature", "157", "°C", "measured", "process_monitor", "fig2d; boat temperature peak during the H2O purge, read by eye",
  fs="F2d", qual="kind=measured;step=purge_B", note="read by eye; peak about 157 C")
V("Rtest", "deposition_temperature", "", "°C", "measured", "process_monitor", "fig2d; boat temperature during the other steps, read by eye",
  fs="F2d", qual="kind=measured", vmin="115", vmax="119", note="read by eye; dips to ~115 C right after the ramp down")
V("R120-160", "other", "450", "mTorr", "measured", "process_monitor", "s12.x1, fig3a; plateau of δp in the cycle-15 DEZ hold, 120/160 run", fs="F3a-cyc",
  label="δp maximum", regime="reaction then leak dominated", note="reached after ~10 min, then slowly falls (net leak across the pump valve)")
V("R120-160", "other", "10", "min", "measured", "process_monitor", "s12.x1, fig3a; time to the δp maximum, 120/160 run", fs="F3a-cyc", label="time to δp maximum",
  note="approximate")
V("R120-160", "other", "-2", "mTorr/min", "measured", "process_monitor", "s12.x1, fig3a, s12.p7; terminal slope, cycle 15, 120/160 run", fs="F3a-cyc", label="TS",
  regime="leak dominated", note="approximate")
V("R120", "other", "500", "mTorr", "measured", "process_monitor", "s12.x1, fig3a, s12.p7; δp maximum, cycle 15, 120 run", fs="F3a-120", label="δp maximum",
  note="approximate")
V("R120", "other", "15", "min", "measured", "process_monitor", "s12.x1, fig3a; time to the δp maximum, 120 run", fs="F3a-120", label="time to δp maximum",
  note="approximate")
V("R120", "other", "-1", "mTorr/min", "measured", "process_monitor", "s12.x1, fig3a, s12.p7; terminal slope, cycle 15, 120 run", fs="F3a-120", label="TS",
  note="approximate")
V("R160", "other", "80", "mTorr/min", "measured", "process_monitor", "s12.p7, fig3a; positive terminal slope, cycle 15, 160 run", fs="F3a-160", label="TS",
  regime="non-self-limiting gas generation", note="approximate")
V("R160", "other", "2.7", "Torr", "measured", "process_monitor", "s12.p7, fig3a; δp at the end of the cycle-15 DEZ hold, 160 run", fs="F3a-160", label="δp at end of hold",
  note="rises through the whole hold")
V("R160", "other", "260", "µmol", "measured", "process_monitor", "fig3b; maximum Δn_g near cycle 10, 160 run, read by eye", fs="F3b-160", label="Δn_g maximum",
  note="read by eye; cycles 6-20 rank 160 >> 120 > 120/160 (s12.p8)")
V("R160", "other", "88", "mTorr/min", "measured", "process_monitor", "fig3c; maximum terminal slope near cycle 10, 160 run, read by eye", fs="F3c-160", label="TS maximum",
  note="read by eye")
V("R160", "other", "-10", "%", "calculated", "calculation", "s14.p7; DEZ moles per pulse about 10% lower at 160 than 120 C at equal pressure",
  label="DEZ moles per pulse vs 120 run", rel="ideal gas at fixed pulse pressure")
# Table II
TII = {"R120": dict(zw="23.3", zwe="0.2", zs="6.0", zse="1.1", mw=None, ms=None, rho="1.3e7", rhoe="0.2e7"),
       "R160": dict(zw="17.1", zwe="0.2", zs="6.0", zse="1.5", mw="12.5", mwe="0.7", ms="57", mse="42", rho="8.3e3", rhoe="1.0e3"),
       "R120-160": dict(zw="17.7", zwe="0.1", zs="5.1", zse="1.1", mw=None, ms=None, rho="1.2e7", rhoe="0.1e7")}
for rid, d in TII.items():
    r = TI[rid]; t = TAG[rid]; tx = ", s13.p3" if rid != "R160" else ", s13.p3"
    V(rid, "composition", d["zw"], "wt%", "fit", "xrd", f"tabII.r{r}c1, tabII.r0c1, tabII.cap{tx}; zincite weight percent, {t} run", fs=f"F5-{t}",
      label="ZnO (zincite) Wt. %", qual="species=ZnO", rel="Rietveld refinement", note=f"+/- {d['zwe']} fitting error")
    V(rid, "other", d["zs"], "nm", "fit", "xrd", f"tabII.r{r}c2, tabII.r0c2, tabII.cap{tx}; zincite crystallite size, {t} run", fs=f"F5-{t}",
      label="ZnO crystallite size (nm)", qual="species=ZnO", rel="Halder-Wagner", note=f"+/- {d['zse']} fitting error")
    if d["mw"]:
        V(rid, "composition", d["mw"], "wt%", "fit", "xrd", f"tabII.r{r}c3, tabII.r0c3, s13.p2; metallic Zn weight percent, {t} run", fs=f"F5-{t}",
          label="Zn (metallic) Wt. %", qual="species=Zn", rel="Rietveld refinement", note=f"+/- {d['mwe']} fitting error")
        V(rid, "other", d["ms"], "nm", "fit", "xrd", f"tabII.r{r}c4, tabII.r0c4; metallic Zn crystallite size, {t} run", fs=f"F5-{t}",
          label="Zn crystallite size (nm)", qual="species=Zn", rel="Halder-Wagner", note=f"+/- {d['mse']} fitting error")
    else:
        V(rid, "composition", "", "wt%", "fit", "xrd", f"tabII.r{r}c3, tabII.r{r}c4, tabII.r0c3, tabII.r0c4, s13.p2; metallic Zn not detected, no size, {t} run",
          fs=f"F5-{t}", label="Zn (metallic) Wt. %", qual="species=Zn", censor="<dl", note="printed Not detected; crystallite size cell is a dash")
    V(f"{rid}-prism", "resistivity", d["rho"], "Ω cm", "measured", "electrical",
      f"tabII.r{r}c5, tabII.r0c5, tabII.cap, s13.p4; vertical two-point resistivity, {t} run",
      label="Electrical resistivity, ρ (Ω-cm)", note=f"+/- {d['rhoe']} from Ti/Au electrode area (flaking); text rounds to " + ("~8e3" if rid == "R160" else "~1e7"))
V("prisms", "other", "300", "nA", "measured", "electrical", "s13.p4; vertical current at 10 V, at least about 300 nA", label="vertical current at 10 V", censor=">",
  note="at least; percolating coating across the thickness")
V("prisms", "other", "1e6", "", "measured", "electrical", "s13.p4; current six orders above the noise floor", label="current over noise floor")
V("R160-prism", "other", "1e3", "", "calculated", "calculation", "s13.p4; resistivity of 120 and 120/160 more than three orders above 160", censor=">",
  label="resistivity ratio of 120 and 120/160 runs to 160 run")
# EDS
V("runs", "other", "", "mm", "measured", "sem_eds", "s14.p1, fig6ac; denser alumina band near the bottom of every section, from SE images and Al maps",
  label="width of higher-density band near bottom face", vmin="0.3", vmax="0.5", note="attributed to uneven powder packing before pressing")
V("lowT", "distance", "200", "µm", "measured", "sem_eds", "s14.p1, s14.p2, s14.p8, s15.p2, s15.p3, fig6d, fig6f; Zn signal lower within ~0.2 mm of each face, else flat",
  label="depth of near-surface ZnO depletion", qual="origin=nearer_face", note="XPS (SI) supports real thinning; possibly desorption during the long DEZ purge")
V("R120", "other", "12", "%", "measured", "sem_eds", "s14.p1; normalised Zn counts 12% above the cycled sample", fs="F6d-Zn", label="normalized Zn Kα counts vs 120/160")
for rid, pan, ref, rv, nt in (("R120", "d", "plateau", "3.75", "flat face to face"), ("R160", "e", "maximum", "5.7", "shallow mid-depth dip"),
                               ("R120-160", "f", "plateau", "3.3", "flat; roll-off within ~0.1 mm of the faces")):
    V(rid, "composition", rv, "", "measured", "sem_eds", f"fig6{pan}; Zn line scan reference level read by eye", fs=f"F6{pan}-Zn", label="Normalized X-ray counts",
      qual=f"element=Zn;reference={ref}", note=f"read by eye (cases/points.json reference value); {nt}")
V("R160", "composition", "5.1", "", "measured", "sem_eds", "fig6e, s14.p7; Zn counts minimum near the section centre, read by eye", fs="F6e-Zn",
  label="Normalized X-ray counts", qual="element=Zn", note="read by eye at ~0.9 mm; lower Zn far from the faces, consistent with non-self-limiting Zn deposition")
V("", "other", "1.2", "keV", "literature", "cited", "s14.p7; Zn L edge energy", label="Zn L edge", note="uncited physical constant; explains Al Ka enhancement")
V("", "other", "1.6", "keV", "literature", "cited", "s14.p7; Al K edge energy", label="Al K edge", note="uncited physical constant")
# Eq 2 estimate
V("eq2", "other", "1e13", "s-1", "chosen input", "calculation", "s9.p9, eq2; pre-exponential factor of H2O desorption", label="ν", ref="21",
  rel="eq2", note="taken from ref. 21")
V("eq2", "surface_coverage", "5e-3", "", "chosen input", "calculation", "s9.p9, eq2; target residual H2O coverage", label="θf", qual="species=H2O", ref="8",
  rel="eq2", note="value Cendejas et al. found necessary for uniform infiltration; E_des assumed coverage-independent (value in SI)")
V("eq2-120", "purge_time", "21600", "s", "calculated", "calculation", "s9.p9, eq2, s12.p1; purge needed at 120 C", qual="step=purge_B",
  rel="eq2: t_purge = ln(1/θf) / (ν exp(-E_des/RT))", note="printed 360 min")
V("eq2-160", "purge_time", "660", "s", "calculated", "calculation", "s9.p9, eq2; purge needed at 160 C", qual="step=purge_B",
  rel="eq2: t_purge = ln(1/θf) / (ν exp(-E_des/RT))", note="printed 11 min")
# context estimate
V("runs", "cycle_number", "100", "", "assumed", "", "s6.p7, s6.p6; about 100 cycles possibly needed for high-conductance coatings",
  note="authors' context estimate, not a process setting")
# literature
L = []
def LIT(q, value, unit, ref, ev, label="", qual="", vmin="", vmax="", censor="", note="", rel=""):
    V("", q, value, unit, "literature", "cited", ev, label=label, qual=qual, vmin=vmin, vmax=vmax, censor=censor, ref=ref, note=note, rel=rel)
LIT("other", "", "", "2-8", "s6.p2; porosity of NP thin films coated by ALD", label="porosity φ", vmin="0.3", vmax="0.5", note="approximate")
LIT("aspect_ratio", "100", "", "2-8", "s6.p2; AR of NP thin films", censor="<", qual="basis=AR", note="about 100 or less")
LIT("feature_depth", "", "nm", "2-8", "s6.p2; NP film thickness", label="L", vmin="100", vmax="1000", note="~100 nm to ~1 µm")
LIT("feature_width", "", "nm", "2-8", "s6.p2; pore diameter of NP films", label="d_pore", vmin="5", vmax="20")
LIT("partial_pressure", pa(1), "Pa", "2-8", "s6.p2; reactant pressure that suffices for NP films", censor="<", note="~1 Torr or less")
LIT("pulse_time", "1", "s", "2-8", "s6.p2; exposure duration that suffices for NP films", censor="<", note="~1 s or less")
LIT("other", "0.95", "", "9", "s6.p4; silica aerogel porosity (Gayle et al.)", label="φ")
LIT("aspect_ratio", "60000", "", "9", "s6.p4; aerogel AR, half thickness", censor=">", qual="basis=AR")
LIT("feature_width", "20", "nm", "9", "s6.p4; aerogel pore diameter", label="d_pore")
LIT("feature_depth", "1250000", "nm", "9", "s6.p4; aerogel half-thickness", label="L", note="printed ~1.25 mm")
LIT("other", "12", "", "9", "s6.p4; TMA doses for complete infiltration (one Al2O3 cycle)", label="number of TMA doses")
LIT("exposure", pa(1e4), "Pa s", "9", "s6.p4; total TMA exposure", censor=">", qual="species=TMA", note="printed > 1e4 Torr s; infiltration checked by SEM-EDS")
V("", "other", "95", "%", "literature", "cited", "s6.p8; porosity of ALD-coated aerogels", label="porosity", censor=">", ref="9;16", note="95+%")
LIT("deposition_temperature", "80", "°C", "10", "s6.p5; Ingale et al. ZnO on mesoporous SiO2 powder", qual="kind=set_point")
LIT("cycle_number", "3", "", "10", "s6.p5; up to three ZnO cycles", note="up to")
LIT("other", "2", "g", "10", "s6.p5; powder load", label="powder mass", note="~2 g")
LIT("other", "505", "m2/g", "10", "s6.p5; SiO2 powder specific surface area", label="s")
LIT("growth_per_cycle", "1", "Å", "10", "s6.p5; GPC through the powder bed", note="~1")
LIT("deposition_temperature", "177", "°C", "11", "s6.p5; Ferguson et al. ZnO on ZrO2 NP powder", qual="kind=set_point")
LIT("other", "20.2", "m2/g", "11", "s6.p5; ZrO2 powder specific surface area", label="s")
LIT("other", "50", "nm", "11", "s6.p5; ZrO2 NP diameter", label="d_NP")
LIT("growth_per_cycle", "2.2", "Å", "11", "s6.p5; GPC from TEM", note="~2.2")
LIT("exposure", pa(900), "Pa s", "11", "s6.p5; largest DEZ exposure, Zn deposition seen by FTIR", qual="species=DEZ", note="printed 900 Torr s (maximum)")
LIT("other", "1", "g", "12", "s6.p5; Libera et al. silica gel batch", label="batch mass")
LIT("other", "100", "m2/g", "12", "s6.p5; silica gel specific surface area", label="s")
LIT("cycle_number", "10", "", "12", "s6.p5; ZnO cycles")
LIT("exposure", pa(22.5), "Pa s", "12", "s6.p5; DEZ exposure kept constant", qual="species=DEZ", note="printed 22.5 Torr s")
LIT("deposition_temperature", "", "°C", "12", "s6.p5; temperature range studied", qual="kind=set_point", vmin="150", vmax="200", note="white at 150 C, black at 200 C")
LIT("deposition_temperature", "155", "°C", "12", "s6.p5; lowest temperature with detectable Zn metal by XRD", label="Zn onset temperature", qual="kind=set_point")
LIT("exposure", pa(10), "Pa s", "12", "s6.p5; DEZ exposure below which no Zn at 200 C", qual="species=DEZ", censor="<", note="printed < 10 Torr s at 200 C")
LIT("deposition_temperature", "180", "°C", "4;6-8", "s6.p5; NP thin-film ZnO infiltration studies without Zn metal", qual="kind=set_point")
LIT("exposure", pa(1), "Pa s", "4;6-8", "s6.p5; DEZ exposure of those studies", qual="species=DEZ", censor="<", note="printed < 1 Torr s")
LIT("deposition_temperature", "170", "°C", "13;14", "s6.p6; below about 170 C, ZnO resistivity rises with deposition temperature", label="threshold temperature", qual="kind=set_point")
LIT("other", "1", "", "10", "s12.p6, eq4, eq5; reaction parameter on silica powder at 80 C", label="x", note="~1", rel="eq4, eq5")
LIT("other", "1.37", "", "28", "s12.p6, eq4, eq5; reaction parameter on QCM at 177 C", label="x", rel="eq4, eq5")
LIT("other", "", "", "27", "s12.p6, eq4, eq5; reaction parameter on QCM, 80-250 C", label="x", vmin="1.4", vmax="1.6", rel="eq4, eq5")
LIT("film_thickness", "100", "nm", "13;14", "s13.p4; typical ALD ZnO films for electrical work", note="order of magnitude")
LIT("resistivity", "1e-2", "Ω cm", "13;14", "s13.p4; typical ALD ZnO film resistivity", note="order of magnitude")
LIT("other", "1e3", "s", "40", "s14.p10; time scale on which OH desorption is taken as self-limiting", label="OH desorption time scale", note="assumption of the OH-density argument")
LIT("other", "400", "°C", "42", "s15.p4; flash-lamp rise of Si substrate temperature", label="temperature rise", note="up to ~400 C within 5 s")
LIT("other", "5", "s", "42", "s15.p4; time of the flash-lamp rise", label="heating time")
LIT("other", "800", "°C", "43", "s15.p8; resistive heater rise of sapphire substrate temperature", label="temperature rise", note="up to ~800 C within 15 s")
LIT("other", "15", "s", "43", "s15.p8; time of the resistive-heater rise", label="heating time")
LIT("other", "2", "", "", "s12.p17, eq8; ethane per DEZ consumed when Zn metal forms", label="C2H6 per DEZ (Zn deposition)", note="stoichiometry, refs 25-26 for ethane byproduct", rel="eq8: raises c")

values = [v for v in values if v]

# ---------------------------------------------------------------- coverage
inv = list(csv.DictReader(open(OUT / "inventory.csv", encoding="utf-8")))
ids = [r["element_id"] for r in inv]
cites = {i: [] for i in ids}
bad = []
for tbl, key in ((samples, "sample_id"), (conds, "condition_id"), (series, "series_id"), (values, "value_id")):
    for r in tbl:
        head = r["evidence"].split(";")[0]
        for e in [x.strip() for x in head.split(",")]:
            if e in cites:
                cites[e].append(r[key])
            else:
                bad.append((r[key], e))
DUP = {"s5.p1": "abstract repeated in the body text; the abstract groups abs.g1-g5 are the check copy",
       "s9.p2": "duplicate of fig1.cap (rows cite fig1.cap)", "s12.p12": "duplicate of fig2.cap (rows cite fig2.cap)",
       "s12.p16": "duplicate of fig3.cap (rows cite fig3.cap)", "s13.p5": "duplicate of tabI.cap (rows cite tabI.cap)",
       "s14.p3": "duplicate of fig4.cap (rows cite fig4.cap)", "s14.p4": "duplicate of fig5.cap (rows cite fig5.cap)",
       "s14.p9": "duplicate of tabII.cap (rows cite tabII.cap)", "s15.p6": "duplicate of fig6.cap (rows cite fig6.cap)",
       "s15.p5": "page footer with a stray figure reference", "s14.p5": "page footer (download stamp)", "s15.p7": "page footer (download stamp)",
       "s5.p2": "page footer (download stamp)", "s5.p3": "DOI link", "s0.p1": "front matter (article type and date)",
       "s1.p1": "front matter (special collection)", "s1.p2": "author list", "s1.p3": "publisher widget", "s1.p4": "DOI link",
       "s2.p1": "publisher list of related articles", "s2.p2": "publisher list of related articles", "s2.p3": "publisher list of related articles",
       "s2.p4": "publisher list of related articles", "s2.p5": "publisher list of related articles", "s2.p6": "publisher list of related articles",
       "s3.p1": "citation line", "s3.p2": "submission dates", "s3.p3": "publication date", "s3.p4": "publisher widget", "s3.p5": "publisher widget",
       "s3.p6": "publisher widget", "s3.p7": "author list", "s4.p1": "affiliation", "s4.p2": "affiliation", "s4.p3": "affiliation",
       "s4.p4": "collection note", "s4.p5": "contact e-mail", "s6.p1": "background: definition of AR and porosity dependence, no numbers",
       "s6.p3": "background: motivation for mm-scale NP networks (continues in s6.p4)", "s12.p3": "sentence lead-in to Eq. 3, no knowledge beyond eq3",
       "s12.p4": "lead-in to Eqs. 4-5 (references only)", "s12.p5": "connective word between Eqs. 4 and 5",
       "s15.p9": "acknowledgement heading", "s15.p10": "acknowledgement", "s15.p11": "declarations heading", "s15.p12": "declarations heading",
       "s15.p13": "conflict of interest", "s15.p14": "author contributions heading", "s15.p15": "author contributions", "s15.p16": "author contributions",
       "s15.p17": "data availability heading", "s15.p18": "data availability statement",
       "abs.g1": "abstract (check only): background, no data of this work; nothing new",
       "abs.g2": "abstract (check only): summary of the literature in s6.p5; nothing new",
       "abs.g3": "abstract (check only): porosity, d_NP, thickness, AR, exposure and schedules all carried by body rows; nothing new",
       "abs.g4": "abstract (check only): GPC ~2.1, uniformity and depletion carried by body rows; nothing new",
       "abs.g5": "abstract (check only): list of methods; nothing new"}
cov = []
for r in inv:
    e = r["element_id"]
    if cites[e]:
        cov.append(dict(element_id=e, status="covered", rows=";".join(dict.fromkeys(cites[e])), reason=""))
    else:
        reason = DUP.get(e) or ("heading" if r["kind"] == "heading" else None)
        if reason is None:
            print("UNCOVERED", e, file=sys.stderr); reason = "??"
        cov.append(dict(element_id=e, status="no knowledge", rows="", reason=reason))

def W(name, cols, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
W("paper.csv", ["paper_id", "year", "topic"], [dict(paper_id=PID, year="2023",
  topic="static-dose ZnO ALD (DEZ/H2O) through mm-thick pressed Al2O3 nanoparticle compacts (AR 7800); constant 120 C, constant 160 C and a temperature-cycled purge; pressure-trace gas analysis, mass gain, XRD, resistivity, SEM-EDS profiles")])
W("sample.csv", SC, samples); W("condition.csv", CC, conds); W("series.csv", SR, series); W("value.csv", VC, values)
W("coverage.csv", ["element_id", "status", "rows", "reason"], cov)
print(len(samples), len(conds), len(series), len(values), len(cov), "bad evidence:", bad)
