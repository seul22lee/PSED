#!/usr/bin/env python3
"""Stage 2 facts for yim20 (10.1039_d0cp03358h): what each element states, read by hand from the element texts, the
figure crops and the table crops (table_3_3.png for Table 1, table_10_3.png for Table 2).

    python3 psed_v2/pilot/10.1039_d0cp03358h.facts.py

Reading notes:
- Table 1: the parsed header has 17 cells, the data rows 16. On the crop the columns after x50% are x~50%, the two slopes
  and R^2, so data column c11 sits under headers c11+c12 (one header split in two by the parser) and c12..c15 under
  c13..c16. Samples 8 and 12 are printed twice (rows 8/11 and 13/17); each cell pair is one fact.
- Table 2: the Arts et al. row is split over two parsed rows (r6c5 "OpAL reactor", r6c6 the 10^-4 of its c_H2O), and
  r6c0..c4 belong to the this-work row r7. r6c7 is not on the page.
- Points: accepted v1 curves (v1_points_check.csv) first, else points.json; curves with neither have
  facts without points.
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, P, write  # noqa: E402
import re  # noqa: E402

K, PID = "yim20", "10.1039_d0cp03358h"


def v1(sid, name, xl, yl):
    s = C.v1_points(sid)
    return P(PID, name, s["points"], f"v1_points.json {sid} (accepted in v1_points_check.csv)", xl, yl,
             s.get("note", ""))


def cp(fig, panel, series, name):
    s = C.cases_points(PID, fig, panel, series)
    return P(PID, name, s["points"], f"points.json Fig. {fig}{panel} '{series}'", s["x_label_as_printed"],
             s["y_label_as_printed"], s.get("quality", ""))


# ------------------------------------------------------------------ front matter and headings
NK("s0.p1;s1.p2;s1.p3;s1.p4", "front matter")
NK("s1.p1", "author list")
NK("s2.p5;s2.p6", "affiliations")
NK("s2.p7", "front matter (ESI note)")
NK("s2.p8", "author contribution note")
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h;s12.h;s13.h;s14.h;s15.h;s16.h;s17.h;s18.h;s19.h;s20.h;"
   "s21.h;s22.h;s23.h;s24.h", "heading")

# ------------------------------------------------------------------ abstract
F(K, "abs.g1;s2.p10", "claim", "the paper introduces and describes new microscopic LHAR test structures for analysing ALD conformality",
  mentions="LHAR")
F(K, "abs.g1;s2.p1", "cited", "ALD draws wide interest for its unmatched conformality, which results from self-terminating gas-solid reactions",
  method="cited", mentions="ref. 1;ref. 25-27")
F(K, "abs.g2;s5.p1", "setting", "the LHAR structures are all-silicon rectangular channels whose roof is held up by pillars",
  mentions="LHAR")
F(K, "abs.g2;s2.p9", "claim", "aspect ratios beyond 10 000:1 keep the adsorption front from reaching the channel end, so the saturation profile is exposed for analysis",
  quantity="aspect_ratio", value="10000", censor=">", data_kind="chosen input", mentions="10 000:1")
F(K, "abs.g3;s2.p13;s20.p1", "claim", "TMA-water alumina ALD is used as a test vehicle to show that saturation profile measurement is applicable, repeatable and reproducible, and as a benchmark for later studies",
  mentions="TMA;water")
F(K, "abs.g3;s2.p13", "claim", "longer or shorter TMA pulses and purges revealed new details of how TMA-water ALD chemisorbs and of its surface chemistry",
  mentions="TMA")
F(K, "abs.g4;s2.p13;s20.p1", "claim", "new classifications and terms for saturation profiles are proposed, meant for other LHAR studies and partly also for CVD and ALE",
  mentions="CVD;ALE")

# ------------------------------------------------------------------ introduction
F(K, "s2.p1", "definition", "conformality: the ability to cover a 3D object with a homogeneous coating of even thickness", mentions="ref. 1;ref. 2")
F(K, "s2.p1", "cited", "conformal coatings are needed in electronics, heterogeneous catalysis, biosensors and energy applications",
  method="cited", mentions="ref. 2-11")
F(K, "s2.p1", "cited", "ALD, a CVD variant, was invented independently more than forty years ago as atomic layer epitaxy and molecular layering; Tuomo Suntola received the Millennium Technology Prize in 2018",
  method="cited", mentions="ref. 16-23")
F(K, "s2.p1", "cited", "ALD offers film thickness control below one nanometre through self-terminating reactions that stop by themselves",
  method="cited", mentions="ref. 13;ref. 14;ref. 24")
F(K, "s2.p2", "cited", "even ALD does not guarantee conformal coating at a given aspect ratio, so process parameters must be tuned for HAR structures",
  method="cited", mentions="ref. 1;ref. 8;ref. 28-31")
F(K, "s2.p2", "cited", "in ideal ALD, how deep the coating reaches grows as the square root of reactant dose",
  method="cited", mentions="ref. 29;ref. 32-34")
F(K, "s2.p2;s14.p1", "definition", "dose = reactant partial pressure times exposure time; in this work the partial pressure is not strictly constant, so dose need not grow linearly with pulse time",
  mentions="dose")
F(K, "s2.p2", "cited", "reactivity, often given as a lumped sticking coefficient c_A, sets how fast uniform thickness is reached; CVD from decomposition or pulse mixing, or unsaturated reactions, harm conformality",
  method="cited", mentions="c_A;ref. 1;ref. 31;ref. 35-37")
F(K, "s2.p3", "cited", "vertical HAR structures etched in silicon, analysed by SEM or TEM after careful preparation, have been the practical industry standard for conformality",
  method="cited", mentions="VHAR;ref. 1;ref. 2;ref. 29;ref. 34;ref. 35;ref. 38")
F(K, "s2.p3", "definition", "step coverage: ratio of bottom film thickness to top film thickness of a feature", mentions="step coverage")
F(K, "s2.p3", "cited", "lumped sticking coefficients have sometimes been extracted from the often sparse VHAR data", method="cited", mentions="ref. 35")
F(K, "s2.p4;s2.p9;fig1c;fig1.cap", "definition", "in LHAR analysis the channel roof is taken off after ALD so the film can be examined from the top with methods for planar surfaces",
  method="schematic", mentions="Fig. 1;Fig. 1c")
F(K, "s2.p9", "definition", "LHAR features are usually made so deep that the film does not reach their end, which allows analysis of the saturation profile",
  mentions="saturation profile")
F(K, "s2.p10", "cited", "Dendooven et al. assembled macroscopic rectangular LHAR channels with heights in the hundreds of micrometres",
  method="cited", mentions="ref. 31;ref. 39")
F(K, "s2.p10", "cited", "Gao et al. microfabricated LHAR cavities (Si bottom, polysilicon roof, SiO2 pillars) with design heights of 200, 500 or 1000 nm and ARs above 10 000:1; called PillarHall-1 here",
  quantity="feature_height", label_as_printed="design cavity height", value_min="200", value_max="1000", unit="nm",
  data_kind="literature", method="cited", mentions="ref. 40;PillarHall-1")
F(K, "s2.p10;tab2.r2c2;tab2.r0c2", "cited", "Schwille et al. built centrosymmetric MEMS-like LHAR cavities with a limiting gap height of 4.5 µm",
  quantity="feature_height", label_as_printed="LHAR H", value="4.5", unit="µm", data_kind="literature", method="cited",
  mentions="ref. 30;ref. 41;Schwille et al. (2016)")
F(K, "s2.p10", "cited", "improved microscopic rectangular LHAR channels derived from the Gao process were used before but not described in detail",
  method="cited", mentions="ref. 33;ref. 36;ref. 42-44")
F(K, "s2.p10", "cited", "only a small minority of over 700 published ALD processes have had their conformality studied in LHAR structures",
  quantity="other", label_as_printed="published ALD processes", value="700", censor=">", data_kind="literature",
  method="cited", mentions="ref. 45")
F(K, "s2.p10", "cited", "processes studied in LHAR so far: Al2O3 from TMA/H2O, TiO2 from TiCl4/H2O, Ir and IrOx from Ir(acac)3, HfSiOx, SiO2 with O3, and PEALD of Al2O3, AlN, SiO2, TiO2 and HfO2",
  method="cited", mentions="ref. 30;ref. 31;ref. 33;ref. 36;ref. 39-42;ref. 44;ref. 46-48")
F(K, "s2.p11", "cited", "LHAR studies usually fit a reversible or irreversible single-site Langmuir adsorption model to the saturation profile to get a lumped sticking coefficient",
  method="cited", mentions="ref. 1;ref. 30;ref. 31;ref. 33;ref. 36")
F(K, "s2.p11;s2.p12", "cited", "Dendooven et al. extracted the TMA sticking coefficient on Al2O3 and its effect on step coverage, and used Monte Carlo with LHAR for PEALD Al2O3 and AlN",
  method="cited", mentions="ref. 31;ref. 39")
F(K, "s2.p12", "cited", "Schwille et al. obtained sticking coefficients of TMA and BDEAS from Monte Carlo simulation combined with LHAR data",
  method="cited", mentions="ref. 30;ref. 41")
F(K, "s2.p12", "cited", "Ylilammi et al. obtained lumped sticking coefficients of TMA on Al2O3 and TiCl4 on TiO2 with a diffusion-reaction model of LHAR profiles",
  method="cited", mentions="ref. 33")
F(K, "s2.p12", "cited", "Arts et al. took the lumped sticking coefficient from the profile slope, and O2 plasma radical recombination probabilities from PEALD penetration depth",
  method="cited", mentions="ref. 36;ref. 44")
F(K, "s2.p13", "claim", "TMA-water was chosen because it is near-ideal, already studied in LHAR, and its surface chemistry and kinetics are still debated",
  mentions="ref. 13-15;ref. 30;ref. 31;ref. 33;ref. 36;ref. 40;ref. 46;ref. 50-57")
F(K, "s2.p13", "claim", "the authors hope that CVD, ALE and other ALD processes can later be compared against this TMA-water benchmark")
T300 = F(K, "s6.p1;s2.p13;s20.p1;tab1.cap;tab2.r6c0;tab2.r0c0;fig4.cap;fig6.cap;fig9.cap;fig11.cap", "setting",
         "the ALD Al2O3 films of this work were grown at 300 °C, the temperature most used for TMA-water",
         quantity="deposition_temperature", value="300", unit="°C", data_kind="chosen input", mentions="This work")

# ------------------------------------------------------------------ B. terminology
NK("s3.p1", "section overview")
F(K, "s3.p2;fig2.cap", "claim", "four saturation profile classes are proposed (as-measured, scaled, Type 1 and Type 2 normalized); each has been used in the literature, also in combination",
  mentions="Fig. 2")
F(K, "s3.p2;fig2a;fig2.cap", "definition", "as-measured saturation profile: total growth (nm, ng, nm-2, ...) against distance x (µm), straight from the measurement",
  method="schematic", mentions="Fig. 2a")
F(K, "s3.p2", "cited", "Dendooven et al. and Ylilammi et al. showed process-parameter effects on PEALD and ALD conformality with as-measured profiles",
  method="cited", mentions="ref. 39;ref. 33")
F(K, "s3.p3;fig2b;fig2.cap", "definition", "scaled saturation profile: growth per cycle (nm, ng, nm-2, ...) against the dimensionless distance",
  method="schematic", mentions="Fig. 2b")
F(K, "s3.p3;fig2.cap;tabu2.r25c0;tabu2.r25c1", "definition", "dimensionless distance x~ = x/H, measurement distance over channel height (unitless)", quantity="dimensionless_distance", qualifiers="by=H",
  label_as_printed="x̃", mentions="Fig. 2")
F(K, "s3.p3;s3.p4", "cited", "earlier works often used the aspect ratio as horizontal axis where this work uses the dimensionless distance",
  method="cited", mentions="AR;ref. 1;ref. 2;ref. 40;ref. 47")
F(K, "s3.p4", "claim", "x~ stays fixed however much film grows, while the aspect ratio felt by the process rises as the film narrows the channel")
F(K, "s3.p5;fig2c;fig2.cap", "definition", "Type 1 normalized profile: growth with its channel-entrance value set to 1 against x~",
  method="schematic", mentions="Fig. 2c")
F(K, "s3.p5;tabu2.r28c0;tabu2.r28c1", "definition", "the normalized growth may be read as surface coverage θ, with 0 ≤ θ ≤ 1",
  label_as_printed="θ", mentions="ref. 32;ref. 36")
F(K, "s3.p5", "cited", "Arts et al. get a lumped sticking coefficient from the slope of the Type 1 profile when the mean free path greatly exceeds the limiting channel size and the excess number is below 0.1",
  quantity="other", label_as_printed="excess number", value="0.1", censor="<", data_kind="literature", method="cited",
  mentions="ref. 36;ref. 32;λ")
F(K, "s3.p5;fig2d;fig2.cap", "definition", "Type 2 normalized profile: normalized growth against the normalized distance",
  method="schematic", mentions="Fig. 2d")
F(K, "s3.p5;fig2.cap;tabu2.r29c0;tabu2.r29c1", "definition", "normalized distance ξ = x/L, distance over the channel lateral length (unitless)",
  label_as_printed="ξ", mentions="ref. 32")
F(K, "s3.p5", "cited", "Yanguas-Gil et al. used the Type 2 profile to set criteria telling diffusion-limited from reaction-limited ALD",
  method="cited", mentions="ref. 32;ref. 58")
F(K, "s3.p6;fig3.cap;fig3a;fig3b", "definition", "the profile is split into four regions; Region I lies outside, in front of the channel, i.e. on the planar substrate",
  mentions="Region I;Fig. 3a")
F(K, "s3.p6;fig3.cap", "definition", "Region II starts at the channel entry (distance zero) and has roughly constant thickness from saturated reactions up to a knee",
  mentions="Region II;knee;Fig. 3b (1)")
F(K, "s3.p6;s3.p7", "claim", "ideally thickness divided by cycles in Regions I and II gives the characteristic GPC", mentions="Region I;Region II")
F(K, "s3.p7;fig3.cap", "definition", "Region III, after the knee, is where thickness falls because reactions are unsaturated; it is also called the adsorption front",
  mentions="Region III;knee (1)")
F(K, "s3.p7;fig3.cap", "definition", "Region IV follows the adsorption front; thickness there should ideally be zero", mentions="Region IV")
F(K, "s3.p8;fig3.cap;fig3b", "definition", "Region II has subregions a, b, c; a nanostep with slightly higher thickness is sometimes seen between IIa and IIb",
  mentions="Region IIa;Region IIb;nanostep (5);Fig. 3b")
F(K, "s3.p8;fig3.cap", "definition", "Region IIb is the early part after the nanostep where growth per cycle is at its saturated maximum (useful for modelling); IIc is the rest before the knee, and the IIb/IIc border may be arbitrary",
  mentions="Region IIb;Region IIc")
F(K, "fig3.cap;fig3a;fig3b;tabu2.r13c0;tabu2.r13c1;tabu2.r24c0;tabu2.r24c1", "definition",
  "PD50% (x50%): the penetration depth at which thickness is 50% (µm)", label_as_printed="PD^50% (x_50%)", mentions="(2)")
F(K, "fig3.cap;fig3a;fig3b", "definition", "also marked on the profiles: the front slope at PD50% (3) and the leading edge of the front (4)",
  mentions="(3);(4)")
F(K, "fig3a;fig3.cap", "model", "Fig. 3a: ideal simulated scaled profile, growth/cycles against x~ with no axis numbers, annotated with Regions I-IV and marks 1-4",
  method="simulation", mentions="Fig. 3a")
F(K, "fig3b;fig3.cap", "observation", "Fig. 3b: experimental Al2O3 scaled profile without axis numbers, annotated with Regions I, IIa, IIb, IIc, III, IV and marks 1-6",
  mentions="Fig. 3b")
F(K, "fig3.cap;fig3b;s17.p1", "observation", "spikes (6) were occasionally observed in experimental profiles ahead of the leading edge, in Region IV where thickness should be zero",
  mentions="(6);Region IV;Fig. 3")
# Table 1 footnotes (s3.p9)
F(K, "s3.p9;tab1.r0c0", "definition", "each Table 1 series varies one parameter: A pillar layout, B reflectometer magnification, C design channel height, D ALD cycles, E TMA pulse time, F purge time",
  mentions="Series A;Series B;Series C;Series D;Series E;Series F")
F(K, "s3.p9;tab1.r0c1", "definition", "original traceable sample codes are listed in ESI Table S3", mentions="Table S3")
F(K, "s3.p9;tab1.r0c8", "definition", "initial thickness S_IIb is the mean of the first five points of the constant Region IIb; for H 100 nm it is the first point of the constant region",
  method="calculation", mentions="S_IIb;Region IIb;Fig. 3;100 nm")
F(K, "s3.p9;s16.p7;s16.p8", "claim", "the optically measured thickness includes native silicon oxide, which may have raised the measured values somewhat",
  method="reflectometry")
F(K, "s3.p9;tab1.r0c14", "definition", "Region III front slope = slope of the best-fitting straight line through the scaled profile",
  method="calculation", mentions="Region III;Fig. 3")

# ------------------------------------------------------------------ C. experimental
F(K, "s5.p1", "setting", "the test chips (PillarHall-3, third generation) were made by MEMS processing with a process modified from PillarHall-1 of Gao et al.",
  mentions="PillarHall-3;PillarHall-1;ref. 40;Fig. S1")
F(K, "s5.p1", "setting", "starting substrates", quantity="substrate", value_text="low-doped 150 mm Si(100) wafers", mentions="Si (100)")
for h in ("100", "500", "2000"):
    F(K, "s5.p1", "setting", f"one of the targeted channel heights, set by thermal oxide growth, is {h} nm",
      quantity="feature_height", label_as_printed="targeted channel height H", value=h, unit="nm", data_kind="chosen input",
      mentions=f"H {h} nm")
F(K, "s5.p1", "setting", "fabrication steps: multi-step polysilicon membrane from SiH4, several photolithography steps, a plug-up step, and HF vapour etching last",
  mentions="ref. 40")
F(K, "s5.p1", "setting", "wafers could optionally be diced into 15 × 20 mm chips", quantity="other", label_as_printed="chip size", unit="mm")
F(K, "s5.p1", "setting", "an optional distance scale processed on top of the membrane helps optical analysis", mentions="Fig. S2")
F(K, "s5.p1", "setting", "tools: Centrotherm E1200 HT 260-4 furnaces, Primaxx MEMS-CET HF vapour etcher, SUSS MA150 contact aligner, Canon FPA3000-i4 stepper")
F(K, "s5.p2;fig1.cap;fig1a;tab2.r6c3;tab2.r0c3;s3.p9", "setting", "channel aspect ratios in this work go up to 10 000:1 (L 5000 µm with target H 500 nm); per-channel design AR in ESI Table S1",
  quantity="aspect_ratio", value_max="10000", data_kind="chosen input", mentions="L 5000 µm;H 500 nm;Table S1;This work")
F(K, "s5.p2", "definition", "chip layout and pillar layout designs are given in the ESI", mentions="ESI")
F(K, "s6.p1;tab2.r7c5;tab2.r0c5", "setting", "ALD reactor", quantity="reactor_type", value_text="Picosun R-150", mentions="This work")
F(K, "s6.p1", "setting", "the usual target thickness was about 50 nm", quantity="film_thickness", qualifiers="kind=target", value="50", unit="nm",
  data_kind="chosen input")
F(K, "s6.p1;tab2.r6c4;tab2.r0c4", "setting", "the usual number of ALD cycles was 500", quantity="cycle_number", value="500",
  data_kind="chosen input", mentions="This work")
F(K, "s6.p1", "setting", "process pressure about 3 hPa", quantity="process_pressure", value="3", unit="hPa", data_kind="chosen input")
F(K, "s6.p1", "setting", "nitrogen of purity 6.0 served as carrier and purge gas", quantity="carrier_gas", qualifiers="gas=N2")
F(K, "s6.p1", "setting", "constant nitrogen flow of 150 sccm through four reactant lines", quantity="gas_flow_rate", qualifiers="gas=N2",
  value="150", unit="sccm", data_kind="chosen input")
for q, st, val, txt in (("pulse_time", "step=reactant_A;species=TMA", "0.1", "TMA pulse"), ("purge_time", "step=purge_A", "4.0", "purge after TMA"),
                        ("pulse_time", "step=reactant_B;species=H2O", "0.1", "water pulse"), ("purge_time", "step=purge_B", "4.0", "purge after water")):
    F(K, "s6.p1", "setting", f"typical {txt} {val} s in the usual TMA-purge-water-purge sequence", quantity=q, qualifiers=st, value=val, unit="s",
      data_kind="chosen input", mentions="typical;ref. 33;ref. 40;ref. 51")
F(K, "s6.p1", "setting", "TMA, being pyrophoric, was handled under inert conditions", mentions="TMA")
F(K, "tab1.cap;s6.p1", "definition", "Table 1 lists the samples, the parameters used (varied ones in bold) and profile features measured by reflectometer",
  method="tabulated", mentions="Table 1")
F(K, "s6.p2", "setting", "Series A: films with pillar layouts v1a, v1b and v2a in 500 nm design channels, grown together to avoid run-to-run variation",
  quantity="other", label_as_printed="ALD run", value_text="one run and one wafer for samples 1, 2 and 3", mentions="Series A;v1a;v1b;v2a;Table S2;Fig. S3;Table 1")
F(K, "s7.p1;fig1c;fig6.cap", "setting", "unless noted otherwise the film was characterized after the top membrane was peeled off with adhesive tape",
  mentions="Fig. 1c")
F(K, "s7.p1", "setting", "coated channels were routinely imaged by optical microscopy before and after membrane removal", method="optical_microscopy")
F(K, "s7.p2", "setting", "SEM-EDS was done on a Tescan Mira3 SEM with a Thermo Scientific EDS", method="sem_eds")
F(K, "s7.p2;s10.x2", "setting", "the SEM-EDS line scans used 5 keV accelerating voltage (written 5 kV in the results)",
  quantity="other", label_as_printed="accelerating voltage", value="5", unit="keV", data_kind="chosen input", method="sem_eds")
F(K, "s7.p2;s7.p3", "setting", "SEM-EDS sample preparation of the 500 nm design-height sample, which had been stored in ambient air",
  quantity="other", label_as_printed="sample preparation", value_text="none, no step against charging", method="sem_eds", mentions="500 nm")
F(K, "s7.p3", "setting", "an elemental X-ray map was taken first, then elemental line scans", method="sem_eds")
F(K, "s7.p3", "setting", "SEM-EDS line length 500 µm", quantity="other", label_as_printed="length of the line", value="500", unit="µm",
  data_kind="chosen input", method="sem_eds")
F(K, "s7.p3", "setting", "SEM-EDS points spaced 1 µm along the line", quantity="other", label_as_printed="measurement point interval",
  value="1", unit="µm", data_kind="chosen input", method="sem_eds")
F(K, "s7.p3", "setting", "outliers from pillars and channel edges were removed and each line scan is the average of five measurements",
  quantity="other", label_as_printed="measurements averaged", value="5", data_kind="chosen input", method="sem_eds")
F(K, "s7.p4", "setting", "AFM topography on a PSIA XE-100 in non-contact mode with standard tips", method="afm")
F(K, "s7.p4", "setting", "AFM areas from 10 µm × 10 µm to 90 µm × 90 µm at 1024 × 256 pixels", method="afm")
F(K, "s7.p4", "setting", "AFM tilt and slow-axis drift corrected by line-wise first-order polynomial fits", method="afm")
F(K, "s7.p5", "setting", "saturation profiles were measured as line scans with a FilmTek 2000M spectroscopic reflectometer covering 380 to 800 nm",
  quantity="other", label_as_printed="wavelength range", value_min="380", value_max="800", unit="nm", data_kind="chosen input",
  method="reflectometry")
F(K, "s7.p5", "setting", "reflectometer scans started in Region I, about 13 µm before the channel entry", quantity="distance",
  value="13", unit="µm", data_kind="chosen input", method="reflectometry", mentions="Region I;Fig. 3")
F(K, "s7.p5", "setting", "reflectometer scans were 198 or 398 µm long, giving 100 to 200 points", method="reflectometry")
F(K, "s7.p5", "setting", "reflectometer scan step 2 µm", quantity="other", label_as_printed="step", value="2", unit="µm",
  data_kind="chosen input", method="reflectometry")
F(K, "s7.p5;s11.x1;fig7;fig7.cap", "setting", "the default ×50 objective has an estimated spot of 5-6 µm (5 µm in the spot-size results)",
  quantity="probe_resolution", value_min="5", value_max="6", unit="µm", data_kind="assumed", method="reflectometry",
  mentions="×50;X50 (5 µm)")
F(K, "s7.p5;fig7;fig7.cap", "setting", "the ×10 objective has an estimated spot of 25 µm", quantity="probe_resolution", value="25", unit="µm",
  data_kind="assumed", method="reflectometry", mentions="×10;X10 (25 µm)")
F(K, "s7.p5;fig7;fig7.cap", "setting", "the ×5 objective has an estimated spot of 50 µm", quantity="probe_resolution", value="50", unit="µm",
  data_kind="assumed", method="reflectometry", mentions="×5;X5 (50 µm)")
F(K, "s7.p5", "setting", "for repeatability at one spot and within-chip reproducibility, scans were repeated several times on each lateral length (layout v1b)",
  method="reflectometry", mentions="v1b")
F(K, "s7.p5;s3.p9;tab1.r0c3", "setting", "channels with lateral lengths 0.1 to 5 mm were each scanned several times, outliers dropped and the rest averaged (footnote f prints nm)",
  quantity="other", label_as_printed="lateral length L", value_min="0.1", value_max="5", unit="mm", data_kind="chosen input",
  method="reflectometry")
F(K, "s7.p5;s3.p9", "setting", "Series B values come from the L 5 mm channel alone", quantity="other", label_as_printed="lateral length L",
  value="5", unit="mm", data_kind="chosen input", method="reflectometry", mentions="Series B;Table 1")
F(K, "s7.p5", "claim", "averaging repeated scans gave more representative results than single scans", method="reflectometry")
F(K, "s8.p1;fig10.cap", "model", "simulations used a MATLAB implementation of the Ylilammi et al. 2018 diffusion-reaction model",
  method="simulation", mentions="ref. 33")
F(K, "s8.p1", "model", "the partial pressure of Reactant A came from the discretized approximate solution of the 1D diffusion equation, eqns 17-28 of ref. 33",
  method="simulation", mentions="ref. 33;eqn (17)–(28)")
F(K, "s8.p1", "model", "simplification: in the gas diffusion constant of A (eqn 3 of ref. 33) the collision rate at x was taken from the previous time step t_-1",
  method="simulation", mentions="ref. 33;eqn (3)")
F(K, "s8.p1", "model", "the discretized surface-coverage equation (eqn 31 of ref. 33) was solved with the MATLAB ODE23 solver",
  method="simulation", mentions="ref. 33;eqn (31)")
F(K, "s8.p1", "model", "ODE23 relative tolerance 10^-3", quantity="other", label_as_printed="relative tolerance", value="1e-3",
  data_kind="chosen input", method="simulation")
F(K, "s8.p1", "model", "ODE23 absolute tolerance 10^-5", quantity="other", label_as_printed="absolute tolerance", value="1e-5",
  data_kind="chosen input", method="simulation")
F(K, "s8.p1", "claim", "eqn (1) of ref. 33 has an error: both right-hand terms should be multiplied by Avogadro's number",
  mentions="ref. 33;eqn (1)")

# ------------------------------------------------------------------ Fig. 1
F(K, "fig1.cap;fig1a;tabu2.r2c0;tabu2.r2c1", "definition", "H: height of the LHAR channel (nm)", label_as_printed="H", unit="nm",
  mentions="Fig. 1a")
F(K, "fig1.cap;fig1a;tabu2.r6c0;tabu2.r6c1", "definition", "L: lateral length of the LHAR channel (µm)", label_as_printed="L", unit="µm",
  mentions="Fig. 1a")
F(K, "fig1a;fig1.cap", "definition", "Fig. 1a: side and top views of an uncoated channel with L and H marked", method="schematic", mentions="Fig. 1a")
F(K, "fig1b;fig1.cap", "definition", "Fig. 1b: the channel after ALD, coating (blue) on the roof and partway into the channel", method="schematic",
  mentions="Fig. 1b")
F(K, "fig1.cap", "claim", "Fig. 1 is deliberately not to scale; typical LHAR ratios L:H are at least 200:1", mentions="L : H")

# ------------------------------------------------------------------ Table 1 (per sample)
TAB1 = {  # sample: (rows, series, sequence, H nm, layout, N, magnification, c7..c15)
    1: ([1], "A", "0.1-4.0-0.1-4.0", "500", "v1a", "500", "50", ["49.8", "53.3", "0.100", "0.107", "140", "280", "-0.0013", "-0.013", "0.983"]),
    2: ([2], "A", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "50", ["49.6", "54.5", "0.0993", "0.109", "140", "280", "-0.0013", "-0.011", "0.991"]),
    3: ([3], "A", "0.1-4.0-0.1-4.0", "500", "v2a", "500", "50", ["50.5", "53.4", "0.101", "0.107", "110", "220", "-0.0018", "-0.018", "0.997"]),
    4: ([4], "B", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "50", ["47.4", "47.8", "0.0949", "0.0956", "105", "208", "-0.0018", "-0.019", "0.993"]),
    5: ([5], "B", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "10", ["49.1", "50.0", "0.0983", "0.100", "103", "208", "-0.0015", "-0.015", "0.998"]),
    6: ([6], "B", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "5", ["51.4", "52.9", "0.103", "0.106", "109", "214", "-0.00087", "-0.0083", "0.998"]),
    7: ([7], "C", "0.1-4.0-0.1-4.0", "100", "v1b", "500", "50", [None, "47.8", None, "0.0955", "10", "100", "-0.00048", "-0.0050", "0.995"]),
    8: ([8, 11], "CD", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "50", ["46.7", "51.1", "0.0934", "0.102", "106", "214", "-0.0020", "-0.019", "0.993"]),
    9: ([9], "C", "0.1-4.0-0.1-4.0", "2000", "v1b", "500", "50", ["45.3", "48.8", "0.0906", "0.0976", "375", "188", "-0.0046", "-0.047", "0.995"]),
    10: ([10], "D", "0.1-4.0-0.1-4.0", "500", "v1b", "250", "50", ["24.3", "26.0", "0.0970", "0.104", "115", "230", "-0.0022", "-0.021", "0.982"]),
    11: ([12], "D", "0.1-4.0-0.1-4.0", "500", "v1b", "1000", "50", ["94.7", "99.3", "0.0947", "0.0993", "95", "190", "-0.00099", "-0.010", "0.996"]),
    12: ([13, 17], "EF", "0.1-4.0-0.1-4.0", "500", "v1b", "500", "50", ["47.5", "50.2", "0.0951", "0.100", "96", "192", "-0.0021", "-0.021", "0.971"]),
    13: ([14], "E", "0.2-4.0-0.1-4.0", "500", "v1b", "500", "50", ["48.2", "49.8", "0.0962", "0.100", "133", "266", "-0.0014", "-0.014", "0.996"]),
    14: ([15], "E", "0.4-4.0-0.1-4.0", "500", "v2a", "500", "50", ["48.6", "51.0", "0.0972", "0.102", "197", "386", "-0.00045", "-0.0044", "0.996"]),
    15: ([16], "F", "0.1-1.0-0.1-1.0", "500", "v1b", "500", "50", ["50.4", "51.9", "0.101", "0.104", "99", "198", "-0.0017", "-0.016", "0.983"]),
    16: ([18], "F", "0.1-10.0-0.1-10.0", "500", "v1b", "500", "50", ["44.8", "48.9", "0.0897", "0.0978", "109", "218", "-0.0017", "-0.018", "0.999"]),
}
HDR = {c: [c] for c in range(11)}
HDR.update({11: [11, 12], 12: [13], 13: [14], 14: [15], 15: [16]})
# the same value stated by a caption or by the text (local statements of a sample's cycles, height or layout)
EXTRA = {(1, 4): "fig4.cap;fig4a", (2, 4): "fig4.cap;fig4b", (3, 4): "fig4.cap;fig4c", (1, 5): "fig4.cap", (2, 5): "fig4.cap;fig8.cap",
         (3, 5): "fig4.cap", (11, 5): "fig5.cap", (11, 3): "fig5.cap;fig9.cap", (7, 5): "fig9.cap", (8, 5): "fig9.cap;fig8.cap",
         (9, 5): "fig9.cap", (10, 3): "fig9.cap", (8, 3): "fig9.cap;fig8.cap", (2, 3): "fig8.cap", (4, 3): "fig8.cap",
         (4, 5): "fig8.cap", (12, 5): "fig8.cap", (2, 6): "", (4, 6): "fig7.cap", (5, 6): "fig7.cap", (6, 6): "fig7.cap",
         (12, 3): "fig8.cap;fig11.cap", (13, 3): "fig11.cap", (14, 3): "fig11.cap", (15, 3): "fig11.cap", (16, 3): "fig11.cap",
         (2, 4): "fig4.cap;fig4b;fig8.cap", (4, 4): "fig8.cap", (8, 4): "fig8.cap", (12, 4): "fig8.cap"}
ID = {}


def tab1_facts():
    for n, (rows, ser, seq, H, lay, N, mag, v) in TAB1.items():
        sers = ";".join(f"Series {s}" for s in ser)
        men = f"sample {n};{sers}"

        def ev(c):
            e = [f"tab1.r{r}c{c}" for r in rows] + [f"tab1.r0c{h}" for h in HDR[c]]
            e += [f"tab1.r{r}c{k}" for r in rows for k in (0, 1)]
            if EXTRA.get((n, c)):
                e += EXTRA[(n, c)].split(";")
            return ";".join(e)

        a, pa, b, pb = seq.split("-")
        for q, st, val, txt in (("pulse_time", "step=reactant_A;species=TMA", a, "TMA pulse"), ("purge_time", "step=purge_A", pa, "purge after TMA"),
                                ("pulse_time", "step=reactant_B;species=H2O", b, "water pulse"), ("purge_time", "step=purge_B", pb, "purge after water")):
            F(K, ev(2), "setting", f"sample {n}: {txt} {val} s (pulse-purge column)", quantity=q, qualifiers=st, value=val, unit="s",
              data_kind="chosen input", mentions=men)
        ID[n, 3] = F(K, ev(3), "setting", f"sample {n}: design channel height H {H} nm", quantity="feature_height",
                     label_as_printed="Design channel height H", value=H, unit="nm", data_kind="chosen input", mentions=men)
        F(K, ev(4), "setting", f"sample {n}: pillar layout", quantity="pillar_layout", label_as_printed="Pillar layout", value_text=lay,
          mentions=f"{men};{lay}")
        ID[n, 5] = F(K, ev(5), "setting", f"sample {n}: {N} ALD cycles", quantity="cycle_number", value=N, data_kind="chosen input",
                     mentions=men)
        F(K, ev(6), "setting", f"sample {n}: reflectometer magnification ×{mag}", quantity="objective_magnification",
          label_as_printed="Reflectometer magnification", value=mag, unit="×", data_kind="chosen input", method="reflectometry",
          mentions=men)
        if v[0] is None:
            F(K, ";".join(f"tab1.r{r}c{c}" for r in rows for c in (7, 9)) + ";tab1.r0c7;tab1.r0c9;s3.p9;tab1.r7c0;tab1.r7c1",
              "observation", f"sample {n} (H {H} nm): thickness outside the channel (Region I) and S_I/N were not measured (dash, footnote e)",
              method="reflectometry", mentions=f"{men};Region I")
        else:
            ID[n, 7] = F(K, ev(7), "observation", f"sample {n}: thickness outside the channel S_I {v[0]} nm", quantity="film_thickness",
                         qualifiers="position=outside", value=v[0], unit="nm", data_kind="measured", method="reflectometry", mentions=men)
        ID[n, 8] = F(K, ev(8), "observation", f"sample {n}: initial thickness S_IIb {v[1]} nm", quantity="film_thickness",
                     qualifiers="position=plateau", value=v[1], unit="nm", data_kind="measured", method="reflectometry", mentions=men)
        if v[2] is not None:
            F(K, ev(9), "derived", f"sample {n}: S_I/N (GPC_I) {v[2]} nm", quantity="growth_per_cycle", qualifiers="position=outside",
              label_as_printed="S_I/N (GPC_I)", value=v[2], unit="nm", data_kind="calculated", method="calculation", mentions=men,
              inputs=[ID[n, 7], ID[n, 5]])
        F(K, ev(10), "derived", f"sample {n}: S_IIb/N (GPC_IIb) {v[3]} nm", quantity="growth_per_cycle", qualifiers="position=plateau",
          label_as_printed="S_IIb/N (GPC_IIb)", value=v[3], unit="nm", data_kind="calculated", method="calculation", mentions=men,
          inputs=[ID[n, 8], ID[n, 5]])
        ID[n, 11] = F(K, ev(11), "observation", f"sample {n}: x50% (PD50%) {v[4]} µm", quantity="penetration_depth",
                      qualifiers="level=50%;origin=entrance", label_as_printed="x_50% (PD^50%)", value=v[4], unit="µm",
                      data_kind="measured", method="reflectometry", mentions=men)
        F(K, ev(12), "derived", f"sample {n}: dimensionless x~50% {v[5]}", quantity="dimensionless_distance",
          qualifiers="level=50%;by=H", label_as_printed="x̃_50%", value=v[5], data_kind="calculated", method="calculation",
          mentions=men, inputs=[ID[n, 11], ID[n, 3]])
        ID[n, 13] = F(K, ev(13), "derived", f"sample {n}: front slope d(S/N)/dx~ {v[6]} nm", quantity="front_slope", qualifiers="by=H",
                      label_as_printed="Slope d(S/N)/dx̃", value=v[6], unit="nm", data_kind="fit", method="calculation", mentions=men,
                      inputs=[ID[n, 5], ID[n, 3]])                     # a slope of S/N against x/H: defined with N and H (P25)
        ID[n, 14] = F(K, ev(14), "derived", f"sample {n}: front slope dθ/dx~ {v[7]}", quantity="front_slope",
                      qualifiers="by=H;reference=entrance", label_as_printed="Slope dθ/dx̃", value=v[7], data_kind="fit",
                      method="calculation", mentions=men, inputs=[ID[n, 3]])   # against x/H (P25)
        F(K, ev(15), "derived", f"sample {n}: R^2 of the linear front fit {v[8]}", quantity="fit_r2",
          label_as_printed="Linear fitting residual R^2", value=v[8], data_kind="fit", method="calculation", mentions=men)


# ------------------------------------------------------------------ D. results: microscopy (Figs. 4-6)
F(K, "s10.x1;fig4.cap;fig4a;fig4b;fig4c", "observation", "Fig. 4: top-view optical micrographs of Al2O3-coated LHAR channels after removal of the top membrane; the coating looks brown",
  method="optical_microscopy", mentions="Fig. 4")
F(K, "fig4.cap", "setting", "the channels in Fig. 4 have length L of 1 mm", quantity="other", label_as_printed="channel length L", value="1",
  unit="mm", data_kind="chosen input", mentions="Fig. 4")
F(K, "s10.p1;fig4a;fig4b;fig4c", "observation", "the coated area shows up as a colour difference", method="optical_microscopy")
F(K, "s10.p1;fig4a;fig4b;fig4.cap", "observation", "layouts v1a and v1b: penetration depth about 140 µm from the entry, judged by eye, with a straight front parallel to the entry",
  quantity="penetration_depth", qualifiers="origin=entrance", value="140", unit="µm", data_kind="measured", method="optical_microscopy",
  mentions="v1a;v1b;Fig. 4a;Fig. 4b")
F(K, "s10.p1;fig4c;fig4.cap", "observation", "v2a layout: the front is wavy and penetration is shallower, about 100 µm",
  quantity="penetration_depth", qualifiers="origin=entrance", value="100", unit="µm", data_kind="measured", method="optical_microscopy",
  mentions="v2a;Fig. 4c")
F(K, "s10.p1", "claim", "the smaller v2a penetration most likely comes from the membrane sagging between pillars, giving a channel narrower than the target",
  mentions="v2a")
F(K, "s10.p1", "observation", "ESI Fig. S4 profiles: v1a and v1b overlap and v2a penetrates less, as in the micrographs",
  method="reflectometry", mentions="Fig. S4;v1a;v1b;v2a")
F(K, "fig4a", "observation", "Fig. 4a (sample 1, v1a): densely spaced pillars; Regions I-IV bracketed above; scale bar 100 µm",
  method="optical_microscopy", mentions="Fig. 4a;sample 1;v1a")
F(K, "fig4b", "observation", "Fig. 4b (sample 2, v1b): pillars in sparser rows than v1a; straight coated band; scale bar 100 µm",
  method="optical_microscopy", mentions="Fig. 4b;sample 2;v1b")
F(K, "fig4c", "observation", "Fig. 4c (sample 3, v2a): sparse pillars and a wavy edge of the brown coated band; scale bar 100 µm",
  method="optical_microscopy", mentions="Fig. 4c;sample 3;v2a")
F(K, "s10.x2;fig5a;fig5.cap", "observation", "Fig. 5a: SEM top view of sample 11 with the Al-Kα X-ray count map in red showing where Al lies; Regions I-IV marked; scale bar 100 µm",
  method="sem_eds", mentions="sample 11;Fig. 5a;Table 1")
F(K, "s10.x2;fig5a", "observation", "the X-ray map shows the Al2O3 film reaching about 125 µm under the top membrane",
  quantity="penetration_depth", value="125", unit="µm", data_kind="measured", method="sem_eds", mentions="sample 11;Fig. S5")
F(K, "s10.x2;fig5b;fig5.cap", "observation", "Fig. 5b: SEM-EDS line scans, intensity (a.u.) of O, Al and Si against distance (µm), same sample 11",
  method="sem_eds", mentions="Fig. 5b;sample 11")
F(K, "s10.x2", "claim", "at 5 kV the X-ray interaction volume is deeper than the alumina film, so Si from the substrate shows along the whole scan",
  method="sem_eds", mentions="5 kV")
F(K, "s10.x2;s10.p2;fig5b", "observation", "the Al, O and Si intensities change with distance and so trace the film thickness profile", method="sem_eds")
F(K, "s10.p2;fig5b", "observation", "in front of the channel (Region I), between about -40 and 40 µm, the film thickness is constant",
  quantity="distance", value_min="-40", value_max="40", unit="µm", data_kind="measured", method="sem_eds",
  mentions="Region I;Fig. 3b;Fig. 5b")
F(K, "s10.p2;fig5b", "observation", "next comes a plateau of slightly larger thickness (Regions IIb, IIc), then after a knee the thickness drops sharply to zero",
  method="sem_eds", mentions="Region II b;Region II c;Fig. 3b")
for el, nm in (("O", "O"), ("Al", "Al"), ("Si", "Si")):
    F(K, "fig5b", "observation", f"Fig. 5b curve {el}: EDS intensity across the coated channels",
      quantity="signal_intensity", label_as_printed="Intensity [a.u.]", qualifiers=f"element={el}",
      points_ref=v1(f"yim20:F5b-{nm}", f"fig5b_{el}", "Distance [µm]", "Intensity [a.u.]"), data_kind="measured", method="sem_eds",
      mentions=f"{el};Fig. 5b")
F(K, "s10.x3;fig6;fig6.cap", "observation", "Fig. 6: AFM image of a coated channel (500 nm design, 500 cycles at 300 °C, Table S4); white are membrane remnants and black are holes from torn-off pillars",
  method="afm", mentions="Fig. 6;Table S4")
F(K, "fig6", "observation", "Fig. 6 AFM scan covers 90 µm × 90 µm with a Z range of 3.081 µm; Regions I, IIa and IIb are marked",
  quantity="other", label_as_printed="Z Range", value="3.081", unit="µm", data_kind="measured", method="afm", mentions="Fig. 6")
F(K, "s10.x3;fig6", "observation", "a nanostep can be seen close to the entry, marking where the surface turns rough (Region IIa); curtain-like waviness extends from IIa toward IIb",
  method="afm", mentions="Region IIa;Region IIb;Fig. 3b")
F(K, "s10.x3", "observation", "the nanostep also appears in the AFM line scan of ESI Fig. S6", method="afm", mentions="Fig. S6")

# ------------------------------------------------------------------ spot size (Fig. 7)
F(K, "fig7;fig7.cap;s11.x1", "observation", "Fig. 7: as-measured profiles, film thickness S (nm) against distance x (µm), for three reflectometer spot sizes; samples 4, 5, 6 of Series B",
  method="reflectometry", mentions="Fig. 7;Samples 4, 5, and 6;Series B")
F(K, "fig7", "observation", "Fig. 7 curve X5 (50 µm spot)", quantity="film_thickness",
  points_ref=v1("yim20:F7-x5", "fig7_X5", "Distance x (µm)", "Film thickness S (nm)"), data_kind="measured", method="reflectometry",
  mentions="X5 (50 µm);Fig. 7")
F(K, "fig7", "observation", "Fig. 7 curve X10 (25 µm spot)", quantity="film_thickness",
  points_ref=v1("yim20:F7-x10", "fig7_X10", "Distance x (µm)", "Film thickness S (nm)"), data_kind="measured", method="reflectometry",
  mentions="X10 (25 µm);Fig. 7")
F(K, "fig7", "observation", "Fig. 7 curve X50 (5 µm spot); no accepted points", quantity="film_thickness", method="reflectometry",
  mentions="X50 (5 µm);Fig. 7")
F(K, "s11.x1;fig7", "observation", "larger spots broadened the entrance bump caused by membrane remnants and widened the adsorption front",
  method="reflectometry")
F(K, "s11.x1", "claim", "the measured profile shape depends on spot size whenever the spot is wider than the adsorption front",
  method="reflectometry")
F(K, "s11.x1;fig7", "observation", "the adsorption front is about 30 µm wide", quantity="other", label_as_printed="width of the adsorption front",
  value="30", unit="µm", data_kind="measured", method="reflectometry")
F(K, "s11.x1", "setting", "the smallest spot (×50), well below the front width, was used for all later profile measurements",
  method="reflectometry", mentions="×50")

# ------------------------------------------------------------------ repeatability (Fig. 8)
F(K, "s12.x1;fig8a;fig8.cap", "observation", "Fig. 8a: repeated reflectometer scans of sample 8 on 500 nm design channels of several lateral lengths; film thickness S (nm) against distance inside the channel x (µm)",
  method="reflectometry", mentions="sample 8;Fig. 8a")
F8A = [("0.1", 1, None), ("0.1", 2, None), ("0.1", 3, None), ("0.5", 1, None), ("0.5", 2, None), ("0.5", 3, "yim20:F8a-L0.5-scan3"),
       ("1", 1, "yim20:F8a-L1-scan1"), ("1", 2, None), ("5", 1, "yim20:F8a-L5-scan1")]
for L, k, sid in F8A:
    kw = dict(points_ref=v1(sid, f"fig8a_L{L}mm_scan{k}", "Distance inside the channel x (µm)", "Film thickness S (nm)"),
              data_kind="measured") if sid else {}
    F(K, "fig8a", "observation", f"Fig. 8a curve L {L} mm, legend entry {k} of that length" + ("" if sid else "; no accepted points"),
      quantity="film_thickness", method="reflectometry", mentions=f"L (mm): {L};Fig. 8a", **kw)
F(K, "s12.x1;fig8a", "claim", "the overlapping repeated profiles show good measurement repeatability", method="reflectometry")
F(K, "s12.x1;fig8a;s20.p3", "claim", "profiles from lateral lengths of 100 µm to 5 mm overlap, so L has no significant effect on the measured profile, at least for Al2O3 ALD",
  method="reflectometry", mentions="L")
F(K, "s12.x1", "observation", "matching results for design heights 100 and 2000 nm are in ESI Fig. S7", method="reflectometry",
  mentions="Fig. S7;100 nm;2000 nm")
F(K, "s12.x2;fig8b;fig8.cap;s16.p10", "observation", "Fig. 8b: profiles of different chips, ALD runs and times at fixed ALD parameters (500 cycles, H 500 nm, layout v1b)",
  method="reflectometry", mentions="Fig. 8b")
for smp in ("2", "4", "8", "12"):
    F(K, "fig8b", "observation", f"Fig. 8b curve Sample {smp}", quantity="film_thickness",
      points_ref=v1(f"yim20:F8b-S{smp}", f"fig8b_sample{smp}", "Distance inside the channel x (µm)", "Film thickness S (nm)"),
      data_kind="measured", method="reflectometry", mentions=f"Sample {smp};Fig. 8b")
F(K, "s12.x2;fig8b", "observation", "different chips gave somewhat different thickness and penetration depth with the same ALD sequence",
  method="reflectometry")
F(K, "s12.p1", "claim", "uncertainty sources include small pressure differences between runs, the reflectometer measurement and the real channel height differing from design",
  mentions="Section E")

# ------------------------------------------------------------------ channel height and cycles (Fig. 9)
LAB = {"a": ("Distance inside the channel x (µm)", "Film thickness S (nm)", "film_thickness", ""),
       "b": ("Dimensionless distance x̃", "Thickness/cycles S/N (nm)", "growth_per_cycle", ""),
       "c": ("Dimensionless distance x̃", "Normalized thickness (-)", "normalized_thickness", "reference=entrance")}
LAB.update({"d": LAB["a"], "e": LAB["b"], "f": LAB["c"]})
KIND = {"a": "as-measured", "b": "scaled", "c": "Type 1 normalized", "d": "as-measured", "e": "scaled", "f": "Type 1 normalized"}
for p in "abcdef":
    top = p in "abc"
    F(K, f"fig9{p};fig9.cap", "observation",
      f"Fig. 9{p}: {KIND[p]} profile of Al2O3 at 300 °C, {LAB[p][1]} against {LAB[p][0]}; "
      + ("H varied (100, 500, 2000 nm) at N 500, samples 7, 8, 9 (Series C)" if top else "N varied (250, 500, 1000 cycles) at H 500 nm, samples 8, 10, 11 (Series D)"),
      method="reflectometry", mentions=f"Fig. 9{p};" + ("Sample 7, 8, and 9;Series C" if top else "Sample 8, 10 and 11;Series D"))
F9 = {"a": [("100 nm", ("v1", "yim20:F9a-H100")), ("500 nm", ("v1", "yim20:F9a-H500")), ("2000 nm", ("v1", "yim20:F9a-H2000"))],
      "b": [("100 nm", ("v1", "yim20:F9b-H100")), ("500 nm", ("v1", "yim20:F9b-H500")), ("2000 nm", ("v1", "yim20:F9b-H2000"))],
      "c": [("100 nm", ("cp", "H 100 nm, 500 cycles (sample 7)")), ("500 nm", ("v1", "yim20:F9c-H500")), ("2000 nm", ("v1", "yim20:F9c-H2000"))],
      "d": [("250 cycles", ("v1", "yim20:F9d-N250")), ("500 cycles", ("v1", "yim20:F9d-N500")), ("1000 cycles", None)],
      "e": [("250 cycles", None), ("500 cycles", ("v1", "yim20:F9e-N500")), ("1000 cycles", None)],
      "f": [("250 cycles", ("cp", "H 500 nm, 250 cycles (sample 10)")), ("500 cycles", ("v1", "yim20:F9f-N500")),
            ("1000 cycles", ("cp", "H 500 nm, 1000 cycles (sample 11)"))]}


XQ = {"Distance inside the channel x (µm)": "distance", "Distance x (µm)": "distance", "Distance [µm]": "distance",
      "Dimensionless distance x̃": "dimensionless_distance"}            # the abscissa of a curve (x= qualifier) from its printed x label


def curves(fig, F_, typ, dk, method):
    for p, lst in F_.items():
        xl, yl, q, qual = LAB[p]
        qual = ";".join(filter(None, [qual, "x=" + XQ[xl]]))
        for lab, src in lst:
            name = f"fig{fig}{p}_{lab.replace(' ', '')}"
            kw = {}
            if src:
                ref = v1(src[1], name, xl, yl) if src[0] == "v1" else cp(fig, p, src[1], name)
                kw = dict(points_ref=ref, data_kind=dk)
            F(K, f"fig{fig}{p}", typ, f"Fig. {fig}{p} curve {lab}" + ("" if src else "; no accepted points"), quantity=q,
              qualifiers=qual, method=method, mentions=f"{lab};Fig. {fig}{p}", **kw)


curves(9, F9, "observation", "measured", "reflectometry")
F(K, "s13.x1;fig9a", "observation", "a constant-thickness Region II appears for design heights 500 and 2000 nm",
  method="reflectometry", mentions="500 nm;2000 nm;Region II;Series C")
F(K, "s13.x1;fig9a", "observation", "the taller the channel, the deeper the film penetrated", method="reflectometry", mentions="Fig. 9a")
F(K, "s13.x1;fig9b;fig9c", "observation", "scaled and normalized profiles of the 500 and 2000 nm channels nearly coincide",
  method="reflectometry", mentions="500 nm;2000 nm")
F(K, "s13.x1;fig9a;fig9b;fig9c", "observation", "in the 100 nm channel the front begins right at the entry without a constant-thickness region",
  method="reflectometry", mentions="100 nm")
F(K, "s13.x1", "claim", "the 100 nm profile departs from the series because a film about 50 nm thick plugged the entry as growth went on",
  quantity="film_thickness", value="50", unit="nm", data_kind="measured", mentions="100 nm")
F(K, "s13.x2;fig9d;fig9e;fig9f", "observation", "with cycles varied at H 500 nm the leading edges of the fronts coincide",
  method="reflectometry", mentions="Series D;500 nm")
F(K, "s13.x2;fig9e;fig9f", "observation", "PD50% appears to fall as the cycle number rises", method="reflectometry", mentions="PD^50%")
F(K, "s13.x2;s13.p1", "claim", "PD50% falls because the film fills more of the channel, so the process sees a higher AR that limits propagation",
  mentions="PD^50%")
for fill, n, smp in (("10", "250", 10), ("20", "500", 8), ("40", "1000", 11)):      # the estimate names its cycle count; the formula is not stated (P25)
    F(K, "s13.p1", "derived", f"about {fill}% of the channel is filled after {n} cycles", quantity="fill_fraction",
      label_as_printed="channel filled", value=fill, unit="%", data_kind="calculated", method="calculation", mentions=f"{n} ALD cycles")
F(K, "s13.p1;fig9e;fig9f", "observation", "the front slope gets less steep as cycles increase", method="reflectometry")
F(K, "s13.p1", "observation", "thickness outside and inside the channel (Regions I and IIb) rises linearly with cycle number (Table 1, ESI Fig. S9)",
  method="reflectometry", mentions="Region I;Region IIb;Table 1;Fig. S9")
F(K, "s13.p1", "observation", "SEM-EDS Al line scans (ESI Fig. S8) roughly show X-ray intensity linear in cycle number, consistent with reflectometry",
  method="sem_eds", mentions="Fig. S8")

# ------------------------------------------------------------------ simulations (Fig. 10)
F(K, "s13.p2;fig10.cap", "model", "the effects of channel height and cycle number were simulated with the diffusion-reaction model and set against the experimental profiles",
  method="simulation", mentions="ref. 33;Fig. 10")
for p in "abcdef":
    top = p in "abc"
    F(K, f"fig10{p};fig10.cap", "model",
      f"Fig. 10{p}: simulated {KIND[p]} profile, {LAB[p][1]} against {LAB[p][0]}; "
      + ("H 100, 200, 500, 1000, 2000 nm at N 500" if top else "N 100, 250, 500, 1000, 2000 cycles at H 500 nm"),
      method="simulation", mentions=f"Fig. 10{p}")
F10 = {}
for p in "abc":
    F10[p] = [(f"{h} nm", ("v1", f"yim20:F10{p}-H{h}") if not (p == "a" and h == "1000") else None) for h in ("100", "200", "500", "1000", "2000")]
for p in "def":
    F10[p] = [(f"{n} cycles", ("v1", f"yim20:F10{p}-N{n}") if n != "2000" else None) for n in ("100", "250", "500", "1000", "2000")]
curves(10, F10, "model", "calculated", "simulation")
PAR = [("T", "deposition_temperature", "", "300", "°C", "temperature"),
       ("t_p", "pulse_time", "step=reactant_A;species=TMA", "0.10", "s", "TMA pulse length"),
       ("ρ_A0", "partial_pressure", "species=TMA", "65", "Pa", "input partial pressure of TMA"),
       ("ρ_B", "partial_pressure", "species=N2", "300", "Pa", "partial pressure of the N2 carrier"),
       ("M_A", "other", "", "0.075", "kg mol-1", "molar mass of TMA"),
       ("M_B", "other", "", "0.028", "kg mol-1", "molar mass of N2"),
       ("d_A", "other", "", "591", "pm", "molecular diameter of TMA (from ref. 33)"),
       ("d_B", "other", "", "374", "pm", "molecular diameter of N2"),
       ("b_film", "other", "", "2", "", "metal atoms per film formula unit"),
       ("b_TMA", "other", "", "1", "", "metal atoms per TMA molecule"),
       ("gpc_sat", "growth_per_cycle", "", "0.098", "nm", "saturation growth per cycle"),
       ("q", "saturation_density", "", "3.6", "nm-2", "adsorption density at saturation"),
       ("K", "other", "", "1000.0", "Pa-1", "adsorption equilibrium constant"),
       ("c_TMA", "lumped_sticking_coefficient", "species=TMA", "0.012", "", "lumped sticking coefficient of TMA"),
       ("P_d", "other", "", "0.043", "1 s-1", "desorption probability per unit time")]
for sym, q, qual, val, unit, what in PAR:
    F(K, "fig10.cap", "model", f"simulation input {sym} = {val} {unit}: {what}".strip(), quantity=q, qualifiers=qual,
      label_as_printed=sym, value=val, unit=unit, data_kind="chosen input", method="simulation",
      mentions="Fig. 10;ref. 33" if sym == "d_A" else "Fig. 10")
F(K, "fig10.cap;s18.p3", "model", "simulation input film density ρ = 3100 kg m-3 (from ref. 51), lower than the 4000 kg m-3 used by Ylilammi et al.",
  quantity="film_density", label_as_printed="ρ", value="3100", unit="kg m-3", data_kind="chosen input", method="simulation",
  mentions="Fig. 10;ref. 51")
F(K, "s18.p3;tab2.r4c6", "cited", "Ylilammi et al. used an alumina density of 4000 kg m-3, not reported in their paper (Table 2 footnote e)",
  quantity="film_density", value="4000", unit="kg m-3", data_kind="literature", method="cited", mentions="ref. 33;e")
F(K, "s13.p2;fig10b", "model", "simulated scaled profiles for different heights approach a process-specific fingerprint when the film fills 20% or less of the channel height",
  quantity="fill_fraction", label_as_printed="film filling of the channel height", value_max="20", unit="%", data_kind="calculated",
  method="simulation", mentions="fingerprint")
F(K, "s13.p2;fig10e;fig10f", "model", "in the simulations the leading edges coincide and PD50% drops with more cycles", method="simulation")
F(K, "s13.p2", "claim", "the simulated trends closely resemble the experimental profiles", mentions="Fig. 10;Fig. 9")

# ------------------------------------------------------------------ TMA pulse and purge (Fig. 11)
F(K, "fig11a;fig11.cap", "observation", "Fig. 11a: film thickness S (nm) against distance inside the channel x (µm) for TMA pulses 0.1, 0.2 and 0.4 s (samples 12, 13, 14, Series E); x axis to 400 µm",
  method="reflectometry", mentions="Fig. 11a;sample 12, 13, and 14;Series E")
for t, sid in (("0.1 s", "0.1s"), ("0.2 s", "0.2s"), ("0.4 s", "0.4s")):
    F(K, "fig11a", "observation", f"Fig. 11a curve TMA pulse {t}", quantity="film_thickness",
      points_ref=v1(f"yim20:F11a-{sid}", f"fig11a_TMA{sid}", "Distance inside the channel x (µm)", "Film thickness S (nm)"),
      data_kind="measured", method="reflectometry", mentions=f"TMA pulse: {t};Fig. 11a")
F(K, "s14.p1;fig11a", "observation", "penetration depth grew with TMA pulse time, i.e. it depends on the precursor dose", method="reflectometry")
F(K, "s14.p1;fig11a", "observation", "with a 0.4 s TMA pulse the front was much broader than with 0.1 or 0.2 s pulses while GPC stayed alike",
  method="reflectometry", mentions="0.4 s;0.1 s;0.2 s")
F(K, "s14.p1;s20.p3", "claim", "as the TMA dose increases, growth changes from being limited by TMA dose to being limited by water dose, which then defines the profile; the governing regime depends on exposure")
F(K, "s14.p1;s18.p1", "claim", "TMA-limited and water-limited growth give profiles of different characteristic shape at 300 °C, in line with Arts et al.",
  mentions="ref. 36;Fig. 11a")
F(K, "fig11b;fig11.cap;s14.x1", "observation", "Fig. 11b: film thickness S (nm) against x (µm) for purge times 1, 4 and 10 s (samples 12, 15, 16, Series F) in 500 nm design channels; purges after TMA and water lengthened equally; x axis to 200 µm",
  method="reflectometry", mentions="Fig. 11b;sample 12, 15, and 16;Series F")
for t in ("1", "4", "10"):
    F(K, "fig11b", "observation", f"Fig. 11b curve purge {t} s", quantity="film_thickness",
      points_ref=v1(f"yim20:F11b-{t}s", f"fig11b_purge{t}s", "Distance inside the channel x (µm)", "Film thickness S (nm)"),
      data_kind="measured", method="reflectometry", mentions=f"Purge: {t} s;Fig. 11b")
F(K, "s14.x1;fig11b", "observation", "for every purge time the as-measured profile has a constant region and then a sharp fall", method="reflectometry")
F(K, "s14.x1;s18.p2;s18.p4;fig11b", "observation", "going from 1 to 10 s purge, GPC dropped slightly and PD50% rose slightly (inverse GPC-purge dependence)",
  method="reflectometry", mentions="Series F;Table 1;Fig. S14")
F(K, "s14.x1;s18.p5", "observation", "the purge-time decrease of GPC was a little larger outside the channel (Region I, GPC_I) than inside (Region II, GPC_IIb)",
  method="reflectometry", mentions="Region I;Region II;GPC_I;GPC_IIb;Fig. S14")

# ------------------------------------------------------------------ E. discussion: uncertainty
F(K, "s16.p1;s16.p2", "claim", "profile uncertainty has three sources: channel fabrication, the profile measurement, and the ALD process parameters",
  mentions="(a);(b);(c)")
F(K, "s16.p3", "claim", "fabrication components versus an ideal channel: real height differs from design, pillars affect growth, the membrane may bend in between pillars, an entrance nanostep, and roughness at the bottom (likely also the top)",
  mentions="(i)-(v);PillarHall-3")
F(K, "s16.p3", "observation", "the PillarHall-3 channel entrance has a nanostep about 2 to 5 nm high", quantity="other",
  label_as_printed="nanostep height", value_min="2", value_max="5", unit="nm", data_kind="measured", mentions="PillarHall-3")
for tol, h in (("10", "100"), ("20", "500"), ("30", "2000")):
    F(K, "s16.p4", "observation", f"tolerance of the oxide thickness defining the channel height: ± {tol} nm for the {h} nm design (from oxide measured in fabrication, ESI Table S5)",
      quantity="feature_height", qualifiers="stat=tolerance;between=items;n=not_stated", label_as_printed="tolerance for the oxide thickness", value=tol, unit="nm", data_kind="measured",
      mentions=f"{h} nm;Table S5")
F(K, "s16.p4", "claim", "the smaller the design height the larger the relative height uncertainty; unknown factors may add deviation, so measuring the real height is advised")
F(K, "s16.p4;s16.p5", "model", "for a 500 nm channel a 1% height error causes roughly a 1.5% error in penetration depth (ESI Fig. S10)",
  quantity="other", label_as_printed="error in the penetration depth per 1% error in channel height", value="1.5", unit="%",
  data_kind="calculated", method="calculation", mentions="500 nm;Fig. S10")
F(K, "s16.p5", "model", "for a 500 nm channel, pillars change the penetration depth by less than 1% (ESI section 3.2, Figs. S11, S12)",
  quantity="other", label_as_printed="effect of pillars on the penetration depth", value="1", censor="<", unit="%",
  data_kind="calculated", method="calculation", mentions="500 nm;Fig. S11;Fig. S12")
F(K, "s16.p5", "setting", "typical pillar diameter 4 µm", quantity="other", label_as_printed="pillar diameter", value="4", unit="µm",
  data_kind="chosen input")
F(K, "s16.p5", "setting", "typical pillar interdistance 49 µm in triangular symmetry", quantity="other", label_as_printed="interdistance",
  value="49", unit="µm", data_kind="chosen input")
F(K, "s16.p5", "observation", "AFM: in 500 nm channels the membrane bent down by about 25 nm (ESI Fig. S13a)", quantity="other",
  label_as_printed="membrane bending displacement", value="25", unit="nm", data_kind="measured", method="afm",
  mentions="500 nm;Fig. S13a")
F(K, "s16.p5", "observation", "the 2000 nm design bent about as much as the 500 nm design", method="afm", mentions="2000 nm;500 nm")
F(K, "s16.p5", "observation", "the 100 nm design channel bent about 40 nm (ESI Fig. S13b)", quantity="other",
  label_as_printed="membrane bending displacement", value="40", unit="nm", data_kind="measured", method="afm",
  mentions="100 nm;Fig. S13b")
F(K, "s16.p5", "claim", "the nanostep lowers the channel height and roughness adds surface beyond the flat surface assumed, raising the apparent GPC",
  mentions="(iv);(v)")
F(K, "s16.p5", "claim", "roughness should make PD50% a bit smaller and its slope somewhat steeper compared with a flat surface")
F(K, "s16.p6", "claim", "channels of 500 nm design height with pillar layout v1b came closest to the design and should give the most reliable profiles",
  mentions="500 nm;v1b")
F(K, "s16.p7", "claim", "reflectometry uncertainty comes from manual sample placement, the optical model, the referencing procedure (lamp ageing included) and motorized stage accuracy",
  method="reflectometry")
F(K, "s16.p7", "observation", "samples were positioned by hand to start at the same point relative to the entry seen under the microscope; positioning uncertainty about 2 µm",
  quantity="other", label_as_printed="positioning uncertainty", value="2", unit="µm", data_kind="assumed", method="reflectometry",
  mentions="Region II;Fig. 3")
F(K, "s16.p7", "claim", "the scan should run at exactly 90° to the entry; a deviation causes a cosine error that broadens the profile and raises PD50%, judged insignificant here",
  method="reflectometry", mentions="90°")
F(K, "s16.p7", "model", "the thickness model assumes a roughness-free uniform dielectric with the properties of ALD Al2O3 grown at 300 °C on silicon",
  method="reflectometry")
F(K, "s16.p8", "claim", "a mismatch between optical model and reality gives a systematic thickness error", method="reflectometry")
F(K, "s16.p8", "observation", "the reflectometer reference was hard to repeat at high magnification (50× preferred) and sometimes needed manual focusing",
  method="reflectometry", mentions="50×")
F(K, "s16.p8", "observation", "a change of reference could shift the measured thickness by a few nm for a film of about 50 nm",
  method="reflectometry", mentions="50 nm")
F(K, "s16.p9", "claim", "the ALD process fluctuates within and between runs (flow, pressure, temperature tolerances), and the dose can deviate when a fresh precursor bottle starts, vapour pressure drops, or vaporization is slow")
F(K, "s16.p10;fig8b", "claim", "fully independent TMA-water measurements at 300 °C vary in plateau thickness and penetration depth, but the overall profile and slope at PD50% look alike",
  mentions="Fig. 8b")


def std_facts():
    S = ("2", "4", "8", "12")
    men = "samples 2, 4, 8, and 12;Table 1"
    F(K, "s16.p10", "derived", "standard deviation of PD50% over samples 2, 4, 8 and 12 is 19.4 µm", quantity="penetration_depth",
      qualifiers="level=50%;origin=entrance;stat=sd;between=runs;n=4", label_as_printed="standard deviation of PD50%", value="19.4", unit="µm", data_kind="calculated", method="calculation",
      mentions=men, inputs=[ID[int(s), 11] for s in S])
    F(K, "s16.p10", "derived", "standard deviation of the slope at PD50% over those samples is 0.0003 nm", quantity="front_slope",
      qualifiers="by=H;stat=sd;between=runs;n=4", label_as_printed="standard deviation of the slope at PD50%", value="0.0003", unit="nm", data_kind="calculated",
      method="calculation", mentions=men, inputs=[ID[int(s), 13] for s in S])
    F(K, "s16.p10", "derived", "standard deviation of the initial Region IIb thickness over those samples is 2.8 nm", quantity="film_thickness",
      qualifiers="position=plateau;stat=sd;between=runs;n=4", label_as_printed="standard deviation of the initial film thickness in Region IIb", value="2.8", unit="nm",
      data_kind="calculated", method="calculation", mentions=men + ";Region IIb", inputs=[ID[int(s), 8] for s in S])


# ------------------------------------------------------------------ spikes, TMA-water chemistry
F(K, "s17.p1", "cited", "Schwille et al. saw spikes in TMA-water profiles measured by ellipsometry on their MEMS structures and suggested a CVD-related cause",
  method="cited", mentions="ref. 41")
F(K, "s17.p1;fig5b", "observation", "here spikes appeared in reflectometer profiles but not in SEM-EDS", mentions="Fig. 5")
F(K, "s17.p2", "observation", "spikes occurred where the measurement spot was near pillar remnants (ESI Fig. S16)", method="reflectometry",
  mentions="Fig. S16")
F(K, "s17.p2", "observation", "repeated scans on layout v1a, with smaller pillar spacing than v1b, gave more spikes (ESI Fig. S17)",
  method="reflectometry", mentions="v1a;v1b;Fig. S17")
F(K, "s17.p2", "claim", "testing TMA-water on channels with a sparser pillar network could avoid remnant spikes, but lies outside this work")
F(K, "s18.p4;s20.p3", "claim", "during long purges reversibly adsorbed water likely desorbs, lowering surface OH and hence TMA uptake; this points to a reversible part of the water reaction, against the ideal of fully irreversible ALD",
  mentions="ref. 13;ref. 50")
F(K, "s18.p4", "cited", "Ylivaara et al. found GPC decreasing as purge time rose from 1 s to 4 s", method="cited", mentions="ref. 51")
F(K, "s18.p4", "cited", "Matero et al. reported higher TMA-water GPC at higher water partial pressure", method="cited", mentions="ref. 59")
F(K, "s18.p4", "cited", "Gakis et al. assumed a reversible water reaction", method="cited", mentions="ref. 56")
F(K, "s18.p4", "cited", "Sønsteby et al. noted that long purges can change GPC through surface dehydration", method="cited", mentions="ref. 26")
F(K, "s18.p5", "claim", "re-adsorption of desorbed water on channel walls likely slows the GPC decrease inside the channel versus a planar surface, consistent with Abelson and Girolami on CVD desorption",
  mentions="ref. 2")
F(K, "s18.p6;fig11b", "claim", "lower surface binding capacity for TMA let molecules travel deeper before reacting, increasing penetration depth",
  mentions="Fig. 11b")
F(K, "s18.p6", "cited", "deeper penetration with lower GPC in PillarHall-1 was seen before for iridium ALD and for Al2O3 ALD at different temperatures",
  method="cited", mentions="ref. 47;ref. 46;PillarHall-1")

# ------------------------------------------------------------------ sticking coefficients
F(K, "s19.p1", "model", "Arts et al. eqn (3): |dθ/dx~| ≈ sqrt(c_A/13.9) gives the lumped sticking coefficient from the Type 1 normalized profile",
  method="calculation", mentions="ref. 36;eqn (3)")
F(K, "s19.p1;s19.p2", "model", "the Arts method requires the Knudsen flow regime, i.e. mean free path much larger than the characteristic size h",
  mentions="ref. 36")
F(K, "s19.p2;tabu2.r5c0;tabu2.r5c1", "definition", "Knudsen number K_n = λ/h (unitless); Knudsen regime means K_n ≫ 1",
  label_as_printed="K_n", mentions="K_n")
F(K, "s19.p3;s8.p1", "derived", "TMA mean free path at 300 °C in the process conditions is about 40 µm (eqn (3) of ref. 1); the simulated conditions give the same",
  quantity="mean_free_path", qualifiers="species=TMA", value="40", unit="µm", data_kind="calculated", method="calculation",
  mentions="λ_TMA;ref. 1")
F(K, "s19.p3", "derived", "water mean free path at 300 °C in the process conditions is 100 µm", quantity="mean_free_path",
  qualifiers="species=H2O", value="100", unit="µm", data_kind="calculated", method="calculation", mentions="ref. 1")
F(K, "s19.p3;tabu2.r3c0;tabu2.r3c1", "model", "the characteristic size is the hydraulic diameter h = 2/(1/H + 1/W) (µm)",
  label_as_printed="h", unit="µm")
F(K, "s19.p3", "derived", "hydraulic diameter of a 500 nm channel: 1.0 µm", quantity="other", label_as_printed="hydraulic diameter h",
  value="1.0", unit="µm", data_kind="calculated", method="calculation", mentions="500 nm")
F(K, "s19.p3", "derived", "Knudsen number for TMA in a 500 nm channel is 40", quantity="knudsen_number", qualifiers="species=TMA",
  value="40", data_kind="calculated", method="calculation", mentions="500 nm")
F(K, "s19.p3", "derived", "Knudsen number for water in a 500 nm channel is 100", quantity="knudsen_number", qualifiers="species=H2O",
  value="100", data_kind="calculated", method="calculation", mentions="500 nm")
F(K, "s19.p3", "claim", "the Arts et al. method should therefore be valid here", mentions="ref. 36")
F(K, "s19.p4", "definition", "c_TMA was computed for several samples and averaged; c_H2O came from one sample (Table 2)", mentions="Table 2")
F(K, "s19.p4;s20.p3", "claim", "the extracted c_TMA of 4 × 10^-3 agrees with the literature, lying between Arts et al. and Ylilammi et al.; lumped coefficients from the slope match earlier values",
  mentions="ref. 36;ref. 33;ref. 54;ref. 60")
F(K, "s19.p4", "claim", "the extracted c_H2O of 3 × 10^-4 is in line with earlier reports", mentions="ref. 36;ref. 60")

# ------------------------------------------------------------------ conclusions
F(K, "s20.p1", "claim", "LHAR prototype dimensions, effect of pillars, process reproducibility and thickness measurement uncertainty were discussed")
F(K, "s20.p2;fig9a;fig9d", "claim", "as-measured profiles differed with cycle number (250-1000) and design height (100, 500, 2000 nm)",
  mentions="250–1000;100, 500, 2000 nm")
F(K, "s20.p2", "claim", "scaled by cycle number and channel height the profiles converge; the scaled profile is proposed as an informative measure that can become a fingerprint of an ALD process")
F(K, "s20.p2", "claim", "favourable conditions for the fingerprint: Knudsen diffusion and an open channel, filling preferably below 10%",
  quantity="fill_fraction", label_as_printed="channel filling", value="10", censor="<", unit="%", data_kind="assumed")
F(K, "s20.p3", "claim", "the Al2O3 profiles had the near-ideal ALD shape: constant thickness, then a steep fall to zero")

# ------------------------------------------------------------------ back matter
NK("s21.p1", "funding")
F(K, "s22.p1", "definition", "notation largely follows Ylilammi et al. 2018, with influence from Arts et al.", mentions="ref. 33;ref. 36")
NK("s23.p1", "conflict statement")
NK("s24.p1;s24.p2", "acknowledgement")

# ------------------------------------------------------------------ Table 1 cells
tab1_facts()
for sfx_, smp_ in (("s13.p1#1", 10), ("s13.p1#2", 8), ("s13.p1#3", 11)):        # the fill estimates' inputs: the sample's cycle count and height (P25)
    next(x for x in C.facts() if x["fact_id"] == f"{K}:{sfx_}")["inputs"] = f"{ID[smp_, 5]};{ID[smp_, 3]}"
std_facts()

# ------------------------------------------------------------------ Table 2
F(K, "tab2.cap;tab2.r0c8", "definition", "Table 2 compares lumped sticking coefficients of TMA and water on ALD Al2O3 in various LHAR features",
  method="tabulated", mentions="Table 2")
LIT = {1: "ref. 31;Dendooven et al. (2009)", 2: "ref. 41;Schwille et al. (2016)", 3: "ref. 60;Vandalon et al. (2016)",
       4: "ref. 33;Ylilammi et al. (2018)", 5: "ref. 36;Arts et al. (2019)"}


def t2(r, c, extra=""):
    e = [f"tab2.r{r}c{c}", f"tab2.r0c{c}", f"tab2.r{r}c8"]
    return ";".join(e + ([x for x in extra.split(";") if x] if extra else []))


def lit(r, c, stmt, extra="", **kw):
    kw.setdefault("method", "cited")
    if kw.get("value") or kw.get("value_min") or kw.get("value_max"):
        kw.setdefault("data_kind", "literature")
    return F(K, t2(r, c, extra), "cited", stmt, mentions=LIT[r], **kw)


lit(1, 0, "Dendooven et al. (2009): deposition at 200 °C", quantity="deposition_temperature", value="200", unit="°C")
lit(1, 1, "Dendooven et al. (2009): LHAR type", quantity="other", label_as_printed="LHAR type", value_text="macroscopic rectangular")
lit(1, 2, "Dendooven et al. (2009): LHAR H 100 µm", quantity="feature_height", label_as_printed="LHAR H", value="100", unit="µm")
lit(1, 3, "Dendooven et al. (2009): max. AR 200:1", quantity="aspect_ratio", label_as_printed="Max. AR", value="200")
lit(1, 4, "Dendooven et al. (2009): 150 cycles", quantity="cycle_number", value="150")
lit(1, 5, "Dendooven et al. (2009): reactor", quantity="reactor_type", value_text="home-built")
lit(1, 6, "Dendooven et al. (2009): c_TMA 0.1", quantity="lumped_sticking_coefficient", qualifiers="species=TMA", value="0.1")
lit(2, 0, "Schwille et al. (2016): deposition at 200 °C", quantity="deposition_temperature", value="200", unit="°C")
lit(2, 1, "Schwille et al. (2016): LHAR type", quantity="other", label_as_printed="LHAR type", value_text="microscopic centrosymmetric")
lit(2, 3, "Schwille et al. (2016): max. AR about 100:1, an order-of-magnitude estimate (footnote a)", extra="s18.p3",
    quantity="aspect_ratio", label_as_printed="Max. AR", value="100")
F(K, "s18.p3;tab2.r2c3", "cited", "the Schwille structure is a microscopic cavity 5 µm high and 2000 µm long with one access hole of 4 to 100 µm diameter",
  method="cited", mentions="ref. 41;a")
lit(2, 5, "Schwille et al. (2016): reactor", quantity="reactor_type", value_text="single-wafer cross-flow hot-wall")
lit(2, 6, "Schwille et al. (2016): c_TMA 2 × 10^-2", quantity="lumped_sticking_coefficient", qualifiers="species=TMA", value="2e-2")
F(K, "s18.p3;tab2.r2c4;tab2.r3c4;tab2.r0c4", "cited", "the number of ALD cycles is not reported for the Schwille and Vandalon works (dash, footnote b)",
  method="cited", mentions="ref. 41;ref. 60;b")
lit(3, 0, "Vandalon et al. (2016): temperatures 100–300 °C", quantity="deposition_temperature", value_min="100", value_max="300", unit="°C")
F(K, "s18.p3;tab2.r3c1;tab2.r3c2;tab2.r3c3;tab2.r0c1", "cited", "Vandalon et al. coated a planar Si(100) wafer, not an LHAR feature; their coefficients are listed for reference (footnote c)",
  method="cited", mentions="ref. 60;c")
lit(3, 5, "Vandalon et al. (2016): reactor", quantity="reactor_type", value_text="home-built")
lit(3, 6, "Vandalon et al. (2016): c_TMA of order 10^-3 (footnote d)", extra="s18.p3", quantity="lumped_sticking_coefficient",
    qualifiers="species=TMA", value="1e-3")
lit(3, 7, "Vandalon et al. (2016): c_H2O of order 10^-4 (footnote d)", extra="s18.p3;tab2.r0c7", quantity="lumped_sticking_coefficient",
    qualifiers="species=H2O", value="1e-4")
for v, t, extra in (("1e-4", "300", ""), ("1e-6", "100", "")):
    F(K, "s18.p3", "cited", f"follow-up Vandalon et al. (2017): c_H2O {v.replace('1e-', '1 × 10^-')} at {t} °C", quantity="lumped_sticking_coefficient",
      qualifiers="species=H2O", value=v, data_kind="literature", method="cited", mentions=f"Vandalon et al. (2017);{t} °C")
F(K, "s18.p3", "cited", "follow-up Vandalon et al. (2017): c_TMA 2 × 10^-3, independent of temperature", quantity="lumped_sticking_coefficient",
  qualifiers="species=TMA", value="2e-3", data_kind="literature", method="cited", mentions="Vandalon et al. (2017)")
lit(4, 0, "Ylilammi et al. (2018): deposition at 300 °C", quantity="deposition_temperature", value="300", unit="°C")
lit(4, 1, "Ylilammi et al. (2018): LHAR type", quantity="other", label_as_printed="LHAR type", value_text="microscopic rectangular PillarHall-3")
lit(4, 2, "Ylilammi et al. (2018): LHAR H 0.50 µm", quantity="feature_height", label_as_printed="LHAR H", value="0.50", unit="µm")
lit(4, 3, "Ylilammi et al. (2018): max. AR 2000:1", quantity="aspect_ratio", label_as_printed="Max. AR", value="2000")
lit(4, 4, "Ylilammi et al. (2018): 500 cycles", quantity="cycle_number", value="500")
lit(4, 5, "Ylilammi et al. (2018): reactor", quantity="reactor_type", value_text="Picosun R-150")
lit(4, 6, "Ylilammi et al. (2018): c_TMA 5.72 × 10^-3", quantity="lumped_sticking_coefficient", qualifiers="species=TMA", value="5.72e-3")
F(K, "tab2.r1c7;tab2.r2c7;tab2.r4c7;tab2.r0c7", "cited", "Table 2 gives no c_H2O (dash) for Dendooven, Schwille and Ylilammi",
  method="cited", mentions="ref. 31;ref. 41;ref. 33")
lit(5, 0, "Arts et al. (2019): deposition at 275 °C", quantity="deposition_temperature", value="275", unit="°C")
lit(5, 1, "Arts et al. (2019): LHAR type", quantity="other", label_as_printed="LHAR type", value_text="microscopic rectangular PillarHall-3")
lit(5, 2, "Arts et al. (2019): LHAR H 0.50 µm", quantity="feature_height", label_as_printed="LHAR H", value="0.50", unit="µm")
lit(5, 3, "Arts et al. (2019): max. AR 10 000:1", quantity="aspect_ratio", label_as_printed="Max. AR", value="10000")
lit(5, 4, "Arts et al. (2019): 400 cycles", quantity="cycle_number", value="400")
lit(5, 5, "Arts et al. (2019): reactor (name split over two parsed rows)", extra="tab2.r6c5", quantity="reactor_type", value_text="Oxford Instruments OpAL")
lit(5, 6, "Arts et al. (2019): c_TMA (0.5-2) × 10^-3", quantity="lumped_sticking_coefficient", qualifiers="species=TMA",
    value_min="0.5e-3", value_max="2e-3")
lit(5, 7, "Arts et al. (2019): c_H2O (0.8-2) × 10^-4 (exponent on the next parsed row)", extra="tab2.r6c6", quantity="lumped_sticking_coefficient",
    qualifiers="species=H2O", value_min="0.8e-4", value_max="2e-4")
F(K, "tab2.r6c1;tab2.r0c1;tab2.r7c8", "setting", "this work: LHAR type", quantity="other", label_as_printed="LHAR type",
  value_text="microscopic rectangular PillarHall-3", mentions="This work;PillarHall-3")
F(K, "tab2.r6c2;tab2.r0c2;tab2.r7c8", "setting", "this work (Table 2 row): LHAR H 0.50 µm", quantity="feature_height", label_as_printed="LHAR H",
  value="0.50", unit="µm", data_kind="chosen input", mentions="This work")
S = (2, 4, 8, 12)
F(K, "tab2.r7c6;tab2.r0c6;tab2.r7c8;s19.p4;s18.p3", "derived", "this work: c_TMA 4 × 10^-3, from the Arts et al. method on samples 2, 4, 8 and 12, averaged (footnote f)",
  quantity="lumped_sticking_coefficient", qualifiers="species=TMA", value="4e-3", data_kind="calculated", method="calculation",
  mentions="This work;sample 2, 4, 8, and 12;ref. 36;f", inputs=[ID[s, 14] for s in S])
F(K, "tab2.r7c7;tab2.r0c7;tab2.r7c8;s19.p4;s18.p3", "derived", "this work: c_H2O 3 × 10^-4, from the Arts et al. method on sample 14 (footnote g)",
  quantity="lumped_sticking_coefficient", qualifiers="species=H2O", value="3e-4", data_kind="calculated", method="calculation",
  mentions="This work;sample 14;ref. 36;g", inputs=[ID[14, 14]])
NK("tab2.r6c7", "parser artefact: no such cell on the page")

# ------------------------------------------------------------------ nomenclature (tabu1, tabu2)
SYM = {("tabu1", 0): ("a", "distance between pillars", "m"), ("tabu1", 1): ("A", "surface area", "m2"),
       ("tabu1", 2): ("c_TMA", "lumped sticking coefficient of TMA", ""), ("tabu1", 3): ("c_H2O", "lumped sticking coefficient of water", ""),
       ("tabu1", 4): ("b", "number of metal atoms in a molecule", ""), ("tabu1", 5): ("d", "pillar diameter", "µm"),
       ("tabu1", 6): ("d_A", "molecular diameter of Reactant A", "pm"), ("tabu1", 7): ("d_B", "molecular diameter of carrier gas B", "pm"),
       ("tabu1", 8): ("D", "apparent diffusion coefficient", "m2 s-1"), ("tabu1", 9): ("D_0", "diffusion coefficient without pillars", "m2 s-1"),
       ("tabu1", 10): ("F", "material flux along x", "mol m-2 s-1"),
       ("tabu2", 0): ("GPC", "growth per cycle", "m"), ("tabu2", 1): ("gpc_sat", "saturation growth in a cycle", "nm"),
       ("tabu2", 4): ("K", "adsorption equilibrium constant", "1 Pa-1"), ("tabu2", 7): ("l", "distance between pillar rows", "µm"),
       ("tabu2", 8): ("M_B", "molar mass of carrier gas B", "kg mol-1"), ("tabu2", 9): ("M_A", "molar mass of reactant A", "kg mol-1"),
       ("tabu2", 10): ("N", "number of cycles", ""), ("tabu2", 11): ("p_A0", "input partial pressure of Reactant A", "Pa"),
       ("tabu2", 12): ("p_B", "partial pressure of carrier gas B", "Pa"), ("tabu2", 14): ("P_d", "desorption probability per unit time", "1 s-1"),
       ("tabu2", 15): ("Q", "collision rate at unit pressure", "m-2 s-1 Pa-1"),
       ("tabu2", 16): ("q", "adsorption density of reactant A at saturation", "1 m-2"),
       ("tabu2", 17): ("R", "diffusion resistance of a rectangular channel", "s m-3"),
       ("tabu2", 18): ("R_row", "diffusion resistance of one pillar row", "s m-3"),
       ("tabu2", 19): ("S_I", "film thickness outside the channel", "m"), ("tabu2", 20): ("S_II", "film thickness inside the channel", "m"),
       ("tabu2", 21): ("t_p", "pulse length", "s"), ("tabu2", 22): ("W", "opening width of the channel", "m"),
       ("tabu2", 23): ("x", "distance from the channel opening", "m"), ("tabu2", 26): ("λ_TMA", "mean free path of TMA", "µm"),
       ("tabu2", 27): ("ρ", "film density", "kg m-3")}
for (t, r), (sym, what, unit) in SYM.items():
    F(K, f"{t}.r{r}c0;{t}.r{r}c1", "definition", f"symbol {sym}: {what}" + (f"; unit {unit}" if unit else ""),
      label_as_printed=sym, unit=unit, mentions="Symbols and abbreviations")

# ------------------------------------------------------------------ purpose sentences of the series (stage 3 group rows)
PUR_A = F(K, "s6.p2", "claim", "Series A exists to test how pillar density affects the saturation profile", mentions="Series A")
PUR_B = F(K, "s7.p5", "claim", "the ×10 and ×5 objectives were used to test how the spot size affects the saturation profile",
          mentions="×10;×5;Series B")
PUR_C = F(K, "s13.x1", "claim", "Series C was made to show the effect of channel height on the saturation profile", mentions="Series C;Fig. 9")
PUR_D = F(K, "s13.x2", "claim", "Series D was made to show how the cycle count changes the saturation profile at H 500 nm",
          mentions="Series D;Fig. 9;500 nm")
PUR_F = F(K, "s18.p2", "claim", "the purge-time series was made to look further into how purge time changes the saturation profile",
          mentions="purge time")
PUR_R = F(K, "s16.p10;fig8.cap", "claim", "fully independent measurements of one process are compared to show the reproducibility of the saturation profile",
          mentions="Fig. 8b")

# ------------------------------------------------------------------ the film material and the test structure type (lists.MATERIALS, lists.STRUCTURES)
MAT = F(K, "s6.p1;abs.g1", "setting", "film material of this work", quantity="material", value_text="Al2O3", data_kind="chosen input",
        mentions="Al2O3")
STRUCT = F(K, "s5.p1;abs.g1", "setting", "test structure type of this work: PillarHall-3 LHAR chips", quantity="structure_type",
           value_text="lateral_channel", data_kind="chosen input", mentions="PillarHall-3;LHAR")

# ------------------------------------------------------------------ the abscissa of every curve with points (x= qualifier, from the printed x label)
for cf in C.facts():
    if cf["points_ref"] and "x=" not in cf["qualifiers"]:
        cf["qualifiers"] = ";".join(filter(None, [cf["qualifiers"], "x=" + XQ[C.points()[cf["points_ref"]]["x_label_as_printed"]]]))


# ------------------------------------------------------------------ the stance of every claim, from the paper's wording (lists.STANCES)
STANCE = {"abs.g1#1": "asserted", "abs.g2#2": "asserted", "abs.g3#1": "asserted", "abs.g3#2": "asserted", "abs.g4#1": "asserted",
          "s2.p13#1": "asserted", "s2.p13#2": "open", "s3.p2#1": "asserted", "s3.p4#1": "asserted", "s3.p6#3": "hedged", "s3.p9#4": "limitation",
          "s7.p5#11": "asserted", "s8.p1#7": "asserted", "fig1.cap#3": "asserted", "s10.p1#4": "hedged", "s10.x2#4": "asserted",
          "s11.x1#2": "asserted", "s12.x1#2": "asserted", "s12.x1#3": "asserted", "s12.p1#1": "limitation", "s13.x1#5": "asserted",
          "s13.x2#3": "asserted", "s13.p2#4": "asserted", "s14.p1#3": "asserted", "s14.p1#4": "asserted", "s16.p1#1": "limitation",
          "s16.p3#1": "limitation", "s16.p4#4": "limitation", "s16.p5#7": "hedged", "s16.p5#8": "hedged", "s16.p6#1": "hedged",
          "s16.p7#1": "limitation", "s16.p7#3": "limitation", "s16.p8#1": "limitation", "s16.p9#1": "limitation", "s16.p10#1": "asserted",
          "s17.p2#3": "open", "s18.p4#1": "hedged", "s18.p5#1": "hedged", "s18.p6#1": "hedged", "s19.p3#7": "hedged", "s19.p4#2": "asserted",
          "s19.p4#3": "asserted", "s20.p1#1": "asserted", "s20.p2#1": "asserted", "s20.p2#2": "asserted", "s20.p2#3": "asserted",
          "s20.p3#1": "asserted", "s6.p2#2": "asserted", "s7.p5#12": "asserted", "s13.x1#6": "asserted", "s13.x2#4": "asserted",
          "s18.p2#1": "asserted", "s16.p10#5": "asserted"}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["stance"] = STANCE[cf["fact_id"].split(":", 1)[1]]          # KeyError = a claim without a stance
VARS = {   # claim id -> (cause, effect): quantity ids or mechanism:<token> (lists.MECHANISMS), blank when the claim has none
    'abs.g1#1': ('', ''),
    'abs.g2#2': ('aspect_ratio', 'penetration_depth'),
    'abs.g3#1': ('', ''),
    'abs.g3#2': ('pulse_time;purge_time', 'mechanism:surface_chemistry'),
    'abs.g4#1': ('', ''),
    's2.p13#1': ('', ''),
    's2.p13#2': ('', ''),
    's3.p2#1': ('', ''),
    's3.p4#1': ('film_thickness', 'aspect_ratio'),
    's3.p6#3': ('cycle_number', 'growth_per_cycle'),
    's3.p9#4': ('mechanism:native_oxide', 'film_thickness'),
    's7.p5#11': ('mechanism:averaging', 'film_thickness'),
    's8.p1#7': ('', ''),
    'fig1.cap#3': ('', ''),
    's10.p1#4': ('mechanism:membrane_sagging', 'penetration_depth'),
    's10.x2#4': ('mechanism:interaction_volume', 'signal_intensity'),
    's11.x1#2': ('probe_resolution', 'front_slope'),
    's12.x1#2': ('', 'film_thickness'),
    's12.x1#3': ('mechanism:channel_length', 'penetration_depth'),
    's12.p1#1': ('process_pressure;probe_resolution;feature_height', 'film_thickness'),
    's13.x1#5': ('mechanism:channel_plugging', 'penetration_depth'),
    's13.x2#3': ('cycle_number;mechanism:channel_narrowing', 'penetration_depth'),
    's13.p2#4': ('', ''),
    's14.p1#3': ('pulse_time', 'front_slope'),
    's14.p1#4': ('pulse_time', 'front_slope'),
    's16.p1#1': ('feature_height;probe_resolution;process_pressure', 'film_thickness'),
    's16.p3#1': ('mechanism:membrane_sagging;mechanism:pillar_effect', 'feature_height'),
    's16.p4#4': ('feature_height', 'feature_height'),
    's16.p5#7': ('roughness;mechanism:nanostep', 'growth_per_cycle'),
    's16.p5#8': ('roughness', 'penetration_depth;front_slope'),
    's16.p6#1': ('pillar_layout;feature_height', 'film_thickness'),
    's16.p7#1': ('mechanism:optical_model;probe_resolution', 'film_thickness'),
    's16.p7#3': ('mechanism:scan_angle', 'penetration_depth'),
    's16.p8#1': ('mechanism:optical_model', 'film_thickness'),
    's16.p9#1': ('gas_flow_rate;process_pressure;deposition_temperature', 'film_thickness'),
    's16.p10#1': ('mechanism:run_variation', 'film_thickness;penetration_depth'),
    's17.p2#3': ('pillar_layout', 'film_thickness'),
    's18.p4#1': ('purge_time', 'mechanism:surface_OH'),
    's18.p5#1': ('mechanism:water_readsorption', 'growth_per_cycle'),
    's18.p6#1': ('mechanism:surface_OH', 'penetration_depth'),
    's19.p3#7': ('', 'lumped_sticking_coefficient'),
    's19.p4#2': ('', 'lumped_sticking_coefficient'),
    's19.p4#3': ('', 'lumped_sticking_coefficient'),
    's20.p1#1': ('', ''),
    's20.p2#1': ('cycle_number;feature_height', 'film_thickness'),
    's20.p2#2': ('cycle_number;feature_height', 'growth_per_cycle'),
    's20.p2#3': ('knudsen_number;fill_fraction', 'growth_per_cycle'),
    's20.p3#1': ('', 'front_slope'),
    's6.p2#2': ('pillar_layout', 'penetration_depth'),
    's7.p5#12': ('objective_magnification', 'penetration_depth'),
    's13.x1#6': ('feature_height', 'penetration_depth'),
    's13.x2#4': ('cycle_number', 'penetration_depth'),
    's18.p2#1': ('purge_time', 'penetration_depth'),
    's16.p10#5': ('mechanism:run_variation', 'penetration_depth'),
}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["cause"], cf["effect"] = VARS[cf["fact_id"].split(":", 1)[1]]  # KeyError = a claim without variables

# ================================================================== stage 3: one tree (parent, links)
# Runs come from Table 1 (one specimen per sample code; Series A is also one stated ALD run, s6.p2), the AFM specimen of Fig. 6
# (Table S4) and the simulations (Fig. 10 curves, ESI sensitivity runs). Parent rule: the row without which the fact would not
# exist; links: a second home (series membership, a claim's support, the same data in another panel).
ROWS = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 7: [7], 8: [8, 11], 9: [9], 10: [10], 11: [12], 12: [13, 17], 13: [14],
        14: [15], 15: [16], 16: [18]}                                         # sample code -> Table 1 rows (8 and 12 printed twice)
SERIES = {"A": (1, 2, 3), "B": (4, 5, 6), "C": (7, 8, 9), "D": (8, 10, 11), "E": (12, 13, 14), "F": (12, 15, 16)}
VARIED = {"A": "pillar layout", "B": "reflectometer magnification", "C": "design channel height", "D": "number of ALD cycles",
          "E": "TMA pulse time", "F": "purge time"}
PAPER, PROC = K, f"{K}:process"
run = lambda n: f"{K}:run{n}"
grp = lambda g: f"{K}:grp:{g}"
SIMS = {"H100": ("100", "500"), "H200": ("200", "500"), "H500": ("500", "500"), "H1000": ("1000", "500"), "H2000": ("2000", "500"),
        "N100": ("500", "100"), "N250": ("500", "250"), "N1000": ("500", "1000"), "N2000": ("500", "2000")}
sim = lambda k: f"{K}:sim:{k}"
N(PAPER, "paper", "Yim et al. 2020, PCCP: PillarHall-3 LHAR test chips and saturation-profile analysis of TMA-water Al2O3 ALD", "",
  evidence="abs.g1", label_as_printed="10.1039/d0cp03358h")
N(PROC, "process", "shared process: thermal Al2O3 ALD from TMA and water at 300 °C in a Picosun R-150 on PillarHall-3 LHAR chips, "
  "with the shared characterization methods", PAPER, evidence="s6.p1;s5.p1;s7.p1")
for g, smp in SERIES.items():
    N(grp(g), "group", f"Series {g} of Table 1: {VARIED[g]} varied over samples {', '.join(map(str, smp))}", PROC,
      evidence=f"s3.p9;tab1.r{ROWS[smp[0]][0]}c0", label_as_printed=f"Series {g}", qualifiers="how=stated")
N(f"{K}:dep:A", "run", "one ALD run that coated samples 1, 2 and 3 (Series A) together, all on one wafer", grp("A"),
  evidence="s6.p2", label_as_printed="Series A", qualifiers="run=deposition;how=stated")
SER_OF = {}
for g, smp in SERIES.items():
    for n in smp:
        SER_OF.setdefault(n, []).append(g)
for n, rows in ROWS.items():
    gs = SER_OF[n]
    N(run(n), "run", f"specimen sample {n} of Table 1 (Series {' and '.join(gs)})", f"{K}:dep:A" if gs == ["A"] else grp(gs[0]),
      evidence=";".join(f"tab1.r{r}c0;tab1.r{r}c1" for r in rows), label_as_printed=f"sample {n}",
      qualifiers=f"run=specimen;how=stated;sample={n}", links=";".join(grp(g) for g in gs[1:]))
N(f"{K}:runS4", "run", "AFM specimen of Fig. 6: 500 nm design channel, 500 cycles at 300 °C, listed in ESI Table S4", PROC,
  evidence="fig6.cap;s10.x3", label_as_printed="Table S4", qualifiers="run=specimen;how=stated;sample=TableS4")
N(grp("repro"), "group", "reproducibility set: samples 2, 4, 8 and 12, alike ALD parameters on different chips, runs and times",
  PROC, evidence="fig8.cap;s12.x2;s16.p10;tab2.r7c6", label_as_printed="sample 2, 4, 8, and 12", qualifiers="how=stated",
  links=";".join(run(n) for n in (2, 4, 8, 12)))
N(grp("sims"), "group", "simulations with the MATLAB diffusion-reaction model (Ylilammi et al. 2018) and their shared inputs",
  PAPER, evidence="s8.p1;s13.p2;fig10.cap", qualifiers="how=stated")
for k, (h, n) in SIMS.items():
    N(sim(k), "run", f"simulated profile for channel height {h} nm and {n} cycles (Fig. 10)", grp("sims"), evidence="fig10.cap",
      label_as_printed=f"sim · H {h} nm" if k.startswith("H") else f"sim · N {n}", qualifiers=f"run=simulation;how=stated;sim=H{h}_N{n}")
N(sim("esi"), "run", "sensitivity simulations of the ESI: channel-height error and pillar effect on penetration depth", grp("sims"),
  evidence="s16.p4;s16.p5", label_as_printed="sim · ESI Fig. S10-S12", qualifiers="run=simulation;how=stated;sim=ESI")

PARENT, LINKS = {}, {}
FX = {f["fact_id"]: f for f in C.facts()}
fid = lambda s_: f"{K}:{s_}"


def put(parent, *ids, links=""):
    for i in ids:
        assert fid(i) in FX, i
        PARENT[fid(i)] = parent
        if links:
            LINKS[fid(i)] = links


def ln(i, *targets):
    LINKS[fid(i)] = ";".join(t if t.startswith(K + ":") else fid(t) for t in targets)


# Table 1 cells: under the sample's run; a value computed from others goes under its first input
FXTYPE = {x["fact_id"]: x["type"] for x in C.facts()}
for f in C.facts():
    m = re.match(rf"{K}:tab1\.r(\d+)c\d+#", f["fact_id"])
    if m and int(m.group(1)) > 0:
        n = int(re.search(r"sample (\d+)", f["mentions"]).group(1))
        res_in = [i for i in f["inputs"].split(";") if i and FXTYPE.get(i) != "setting"]   # under its first input that is a result, else its run
        PARENT[f["fact_id"]] = res_in[0] if f["type"] == "derived" and res_in else run(n)
# figure curves of measured runs
CURVE = {"fig4a#1": 1, "fig4b#1": 2, "fig4c#1": 3, "fig5b#1": 11, "fig5b#2": 11, "fig5b#3": 11,
         "fig7#2": 6, "fig7#3": 5, "fig7#4": 4, "fig8b#1": 2, "fig8b#2": 4, "fig8b#3": 8, "fig8b#4": 12,
         "fig11a#2": 12, "fig11a#3": 13, "fig11a#4": 14, "fig11b#2": 15, "fig11b#3": 12, "fig11b#4": 16}
CURVE.update({f"fig8a#{i}": 8 for i in range(1, 10)})
for p in "abc":
    CURVE.update({f"fig9{p}#2": 7, f"fig9{p}#3": 8, f"fig9{p}#4": 9})
for p in "def":
    CURVE.update({f"fig9{p}#2": 10, f"fig9{p}#3": 8, f"fig9{p}#4": 11})
for i, n in CURVE.items():
    put(run(n), i)
for p, ks in (("abc", ("H100", "H200", "H500", "H1000", "H2000")), ("def", ("N100", "N250", "H500", "N1000", "N2000"))):
    for q in p:
        for j, k in enumerate(ks):
            put(sim(k), f"fig10{q}#{j + 2}")
# the same profile shown again: later panels link to the first panel showing it
first = {}
for i in sorted(list(CURVE) + [f"fig10{q}#{j}" for q in "abcdef" for j in range(2, 7)], key=lambda x: list(FX).index(fid(x))):
    if i.startswith(("fig8a", "fig8b", "fig4", "fig5b")):                     # separate scans or figures, not the same data
        continue
    who = PARENT[fid(i)]
    if who in first:
        ln(i, first[who])
    else:
        first[who] = i
# cited facts: under the first reference they name
REFS = {}
for f in C.facts():
    if f["type"] == "cited" and f["fact_id"] not in PARENT:
        m = re.search(r"ref\. (\d+)", f["mentions"])
        if m:
            PARENT[f["fact_id"]] = f"{K}:refs:{m.group(1)}"
put(f"{K}:refs:54", "s18.p3#5", "s18.p3#6", "s18.p3#7")                        # Vandalon et al. (2017) is ref. 54 in the reference list

# settings, observations and models that the rules above do not place
put(PROC, "abs.g2#1", *[f"s6.p1#{i}" for i in range(1, 13)], *[f"s5.p1#{i}" for i in range(1, 10)], "s5.p2#1", "s7.p1#1", "s7.p1#2",
    "s7.p2#1", "s7.p2#2", *[f"s7.p3#{i}" for i in range(1, 5)], *[f"s7.p4#{i}" for i in range(1, 4)],
    *[f"s7.p5#{i}" for i in range(1, 10)], "s11.x1#4", "fig3.cap#3", "s12.x1#4", "s16.p3#2", "s16.p4#1", "s16.p4#2", "s16.p4#3",
    "s16.p5#2", "s16.p5#3", "s16.p5#4", "s16.p5#5", "s16.p5#6", "s16.p7#2", "s16.p7#4", "s16.p8#2", "s16.p8#3", "s17.p1#2",
    "s17.p2#1", "s17.p2#2", "s19.p3#1", "s19.p3#2", "s19.p3#3", "s19.p3#4", "s19.p3#5", "s19.p3#6", "tab2.r6c1#1", "tab2.r6c2#1")
put(f"{K}:dep:A", "s6.p2#1")
put(grp("A"), "s10.x1#1", "fig4.cap#1", "s10.p1#1", "s10.p1#5")
put(grp("A"), "s10.p1#2", links=f"{run(1)};{run(2)}")
put(run(3), "s10.p1#3")
put(run(11), "s7.p2#3", "s10.x2#1", "s10.x2#2", "s10.x2#3", "s10.x2#5", "s10.p2#1", "s10.p2#2", "s13.p1#3")
put(f"{K}:runS4", "s10.x3#1", "fig6#1", "s10.x3#2", "s10.x3#3")
put(grp("B"), "s7.p5#10", "fig7#1", "s11.x1#1", "s11.x1#3")
put(run(8), "s12.x1#1", "s13.p1#2")
put(grp("repro"), "s12.x2#1", "s12.x2#2", "s16.p10#2", "s16.p10#3", "s16.p10#4", "tab2.r7c6#1")
put(grp("C"), "fig9a#1", "fig9b#1", "fig9c#1", "s13.x1#2", "s13.x1#3")
put(grp("C"), "s13.x1#1", links=f"{run(8)};{run(9)}")
put(run(7), "s13.x1#4")
put(grp("D"), "fig9d#1", "fig9e#1", "fig9f#1", "s13.x2#1", "s13.x2#2", "s13.p1#4", "s13.p1#5", "s13.p1#6")
put(run(10), "s13.p1#1")
put(grp("sims"), *[f"s8.p1#{i}" for i in range(1, 7)], "s13.p2#1", "s13.p2#2", "s13.p2#3",
    *[f"fig10{q}#1" for q in "abcdef"], *[f"fig10.cap#{i}" for i in range(1, 17)])
put(sim("esi"), "s16.p4#5", "s16.p5#1")
put(grp("E"), "fig11a#1", "s14.p1#1")
put(grp("E"), "s14.p1#2", links=run(14))
put(grp("F"), "fig11b#1", "s14.x1#1", "s14.x1#2", "s14.x1#3")
put(f"{K}:refs:36", "s19.p1#1", "s19.p1#2")                                    # the Arts et al. slope method
put(PAPER, "fig3a#1", "fig3b#1")                                               # illustrations with no axis numbers and no stated sample
# claims: under the paper, linked to what supports them
CLAIM = {"abs.g1#1": (PROC, "s5.p1#1"), "abs.g2#2": ("s5.p2#1",), "abs.g3#1": (grp("repro"), "s12.x1#2", "s16.p10#1"),
         "abs.g3#2": (grp("E"), grp("F")), "abs.g4#1": ("s3.p2#1",), "s2.p13#1": (PROC, "s2.p11#1"), "s2.p13#2": ("abs.g3#1",),
         "s3.p2#1": ("s3.p2#2", "s3.p3#1", "s3.p5#1", "s3.p5#4"), "s3.p4#1": ("s3.p3#2",), "s3.p6#3": ("s3.p6#1", "s3.p6#2"),
         "s3.p9#4": ("s3.p9#3",), "s7.p5#11": ("s7.p5#9",), "s8.p1#7": ("s8.p1#1",), "fig1.cap#3": ("fig1a#1",),
         "s10.p1#4": ("s10.p1#3",), "s10.x2#4": ("s7.p2#2", "fig5b#3"), "s11.x1#2": ("s11.x1#1", "fig7#1"), "s12.x1#2": ("s12.x1#1",),
         "s12.x1#3": ("s12.x1#1", "fig8a#9"), "s12.p1#1": ("s12.x2#2",), "s13.x1#5": ("s13.x1#4",), "s13.x2#3": ("s13.x2#2", "s13.p1#1"),
         "s13.p2#4": (grp("sims"), grp("C"), grp("D")), "s14.p1#3": ("s14.p1#1", "s14.p1#2"), "s14.p1#4": ("s14.p1#2", f"{K}:refs:36"),
         "s16.p1#1": ("s16.p3#1", "s16.p7#1", "s16.p9#1"), "s16.p3#1": ("s16.p3#2", "s16.p5#4"), "s16.p4#4": ("s16.p4#1", "s16.p4#3"),
         "s16.p5#7": ("s16.p3#2",), "s16.p5#8": ("s16.p5#7",), "s16.p6#1": ("s10.p1#2", "s16.p5#4"), "s16.p7#1": ("s16.p7#2", "s16.p8#2"),
         "s16.p7#3": ("s16.p7#2",), "s16.p8#1": ("s16.p7#4",), "s16.p9#1": ("s12.x2#2",), "s16.p10#1": (grp("repro"), "s16.p10#2"),
         "s17.p2#3": ("s17.p2#2",), "s18.p4#1": ("s14.x1#2",), "s18.p5#1": ("s14.x1#3",), "s18.p6#1": ("s14.x1#2", "fig11b#1"),
         "s19.p3#7": ("s19.p3#5", "s19.p3#6", "s19.p1#2"), "s19.p4#2": ("tab2.r7c6#1", "tab2.r5c6#1", "tab2.r4c6#1"),
         "s19.p4#3": ("tab2.r7c7#1", "tab2.r5c7#1"), "s20.p1#1": ("s16.p1#1",), "s20.p2#1": (grp("C"), grp("D")),
         "s20.p2#2": ("s13.x1#3", "fig9b#1", "fig9e#1"), "s20.p2#3": ("s19.p3#5", "s13.p1#1"), "s20.p3#1": ("s10.p2#2", "s14.x1#1")}
short = lambda f: f.split(":", 1)[1]
CLAIM.update({short(PUR_A): ("s10.p1#2", "s10.p1#3"), short(PUR_B): ("s11.x1#2",), short(PUR_C): ("s13.x1#2", "s13.x1#3"),
              short(PUR_D): ("s13.x2#1", "s13.x2#2"), short(PUR_F): ("s14.x1#2",), short(PUR_R): ("s16.p10#1",)})
for c, sup in CLAIM.items():
    put(PAPER, c)
    ln(c, *sup)
for f in C.facts():                                                            # definitions: terms and symbols of the paper
    if f["type"] == "definition" and f["fact_id"] not in PARENT:
        PARENT[f["fact_id"]] = PAPER
for f in C.facts():                                                            # a value computed from others: under its first input
    if f["type"] == "derived" and f["inputs"] and f["fact_id"] not in PARENT:
        _ins = {x["fact_id"]: x["type"] for x in C.facts()}
        _res = [i for i in f["inputs"].split(";") if i and _ins.get(i) != "setting"]   # its first input that is a result (a setting is no home, P25)
        if _res:
            PARENT[f["fact_id"]] = _res[0]
        elif PARENT.get(f["inputs"].split(";")[0]):
            PARENT[f["fact_id"]] = PARENT[f["inputs"].split(";")[0]]                  # computed from settings only: beside them
PARENT[MAT] = PARENT[STRUCT] = PROC                                            # material and structure type: shared by every run
left = [f["fact_id"] for f in C.facts() if "#" in f["fact_id"] and f["fact_id"] not in PARENT]
assert not left, left
for r in sorted({p for p in PARENT.values() if ":refs:" in p}, key=lambda x: int(x.rsplit(":", 1)[1])):
    kids = [f for f in C.facts() if PARENT.get(f["fact_id"]) == r]
    ev = list(dict.fromkeys(f["evidence"].split(";")[0] for f in kids))
    N(r, "cited", f"cited work, reference {r.rsplit(':', 1)[1]} of the paper", PAPER, evidence=";".join(ev),
      label_as_printed=f"ref. {r.rsplit(':', 1)[1]}")
for f in C.facts():
    if f["fact_id"] in PARENT:
        f["parent"] = PARENT[f["fact_id"]]
        f["links"] = LINKS.get(f["fact_id"], "")
# the purpose of each series: the paper's own sentence on what it was made to test (Series E has none; the abstract's
# sentence on what varying the TMA pulse revealed stands in)
from facts import purpose  # noqa: E402
for g, p in {grp("A"): PUR_A, f"{K}:dep:A": PUR_A, grp("B"): PUR_B, grp("C"): PUR_C, grp("D"): PUR_D, grp("E"): fid("abs.g3#2"),
             grp("F"): PUR_F, grp("repro"): PUR_R, grp("sims"): fid("s13.p2#1")}.items():
    purpose(g, p)

# ================================================================== stage 3b: the activity/entity tree (facts.retree)
# recipe = the old process; one deposition per sample (Series A: one stated run that coated samples 1-3; the others inferred, the
# paper names no run), the sample as an entity under it; measurement activities by method hold the Table 1 values and curves, the
# reflectometer magnification and the SEM-EDS preparation; the simulations are activities under the shared model activity, each with
# a model-run entity. The series groups survive as rows under the paper with their members (step 3 turns them into comparisons).
RUNROW = {r["fact_id"]: r for r in C.facts() if r["type"] == "run"}
DEPS = {f"{K}:dep:A": dict(statement=RUNROW[f"{K}:dep:A"]["statement"], label="run of samples 1-3", how="stated", evidence="s6.p2")}
ENTS = {f"{K}:dep:A": dict(dep=f"{K}:dep:A", ent=None, parent=None, statement="", label="run of samples 1-3", how="stated")}
for n in ROWS:
    r = RUNROW[run(n)]
    dep = f"{K}:dep:A" if n <= 3 else f"{K}:dep:{n}"
    if n > 3:
        DEPS[dep] = dict(statement=f"the ALD run that coated sample {n}; the paper names no run, one per sample is inferred", label=f"run of sample {n}",
                         how="inferred", evidence=r["evidence"].split(";")[0])
    ENTS[run(n)] = dict(dep=dep, ent=f"{K}:ent:{n}", parent=dep, statement=r["statement"], label=r["label_as_printed"], how="stated", evidence=r["evidence"])
DEPS[f"{K}:dep:S4"] = dict(statement="the ALD run that coated the AFM specimen of Table S4; inferred", label="run of the AFM specimen", how="inferred", evidence="fig6.cap")
ENTS[f"{K}:runS4"] = dict(dep=f"{K}:dep:S4", ent=f"{K}:ent:S4", parent=f"{K}:dep:S4", statement=RUNROW[f"{K}:runS4"]["statement"], label="Table S4 specimen",
                          how="stated", evidence=RUNROW[f"{K}:runS4"]["evidence"])
SIMACT = f"{K}:sim"
N(SIMACT, "activity", "the MATLAB diffusion-reaction model (Ylilammi et al. 2018) and its shared inputs", PAPER, evidence="s8.p1;fig10.cap",
  kind="simulation", how="stated", label_as_printed="model")
SIMRUNS = {}
for k in list(SIMS) + ["esi"]:
    SIMRUNS[sim(k)] = dict(act=f"{K}:simrun:{k}", ent=f"{K}:simrun:{k}:run", parent=SIMACT, statement=RUNROW[sim(k)]["statement"],
                        label=RUNROW[sim(k)]["label_as_printed"], evidence=RUNROW[sim(k)]["evidence"])
C.retree(K, PROC, DEPS, ENTS, SIMRUNS, group_facts_to={grp("sims"): SIMACT})
# each model run's own inputs (P29): the channel height and cycle number the Fig. 10 caption gives each simulated profile
for k_, (h_, n_) in SIMS.items():
    for q_, v_, u_ in (("feature_height", h_, "nm"), ("cycle_number", n_, "")):
        fid_ = F(K, "fig10.cap", "setting", f"simulation run {k_}: {'channel height' if q_ == 'feature_height' else 'cycle number'} {v_}{' ' + u_ if u_ else ''}",
                 quantity=q_, value=v_, unit=u_, data_kind="chosen input", mentions=f"{v_}{' ' + u_ if u_ else ''};sim {k_}")
        next(x for x in C.facts() if x["fact_id"] == fid_)["parent"] = f"{K}:simrun:{k_}"
# observations about the reflectometry method itself (the regions it shows, the spikes) stay on the paper's method activity; the
# ESI comparison of Series C with the model spans that series
for fid_, par in ((f"{K}:fig3b#1", f"{K}:method:reflectometry"), (f"{K}:fig3.cap#3", f"{K}:method:reflectometry"), (f"{K}:s17.p1#2", f"{K}:method:reflectometry"),
                  (f"{K}:s12.x1#4", grp("C"))):
    next(r for r in C.facts() if r["fact_id"] == fid_)["parent"] = par
# the chips as fabricated are an input entity (the PillarHall-3 chip, whose entrance nanostep is common to the designs), with one
# piece per design height: the design height is the piece's own setting (s5.p1), the oxide tolerance (s16.p4) and the membrane
# bending (s16.p5) its order-0 measurements; every deposition names the chip it coated in `inputs` (the AFM specimen's height is
# not stated: the chip type)
CHIPS = f"{K}:ent:chips"
C.input_entity(K, CHIPS, "PillarHall-3 LHAR chips as fabricated, the input of every ALD run; the entrance nanostep is common to the design heights",
               "PillarHall-3 chips", "s5.p1;s16.p3", measured=[("metrology", [f"{K}:s16.p3#2"])], inputs_of=[f"{K}:dep:S4"])
H_DEP = {}
for f_ in C.facts():
    if f_["type"] == "setting" and f_["quantity"] == "feature_height" and f_["parent"].startswith((f"{K}:ent:", f"{K}:dep:")):
        dep_ = f_["parent"] if ":dep:" in f_["parent"] else next(r["parent"] for r in C.facts() if r["fact_id"] == f_["parent"])
        H_DEP.setdefault(int(float(f_["value"])), set()).add(dep_)
HFACT = {100: f"{K}:s5.p1#3", 500: f"{K}:s5.p1#4", 2000: f"{K}:s5.p1#5"}
TOL = {100: f"{K}:s16.p4#1", 500: f"{K}:s16.p4#2", 2000: f"{K}:s16.p4#3"}
BEND = {100: [f"{K}:s16.p5#6"], 500: [f"{K}:s16.p5#4"], 2000: [f"{K}:s16.p5#5"]}
for h in (100, 500, 2000):
    piece = f"{K}:ent:chip_H{h}"
    C.input_entity(K, piece, f"the {h} nm design of the PillarHall-3 chip: its oxide-defined channel height with its tolerance, its membrane bending",
                   f"{h} nm design chip", "s5.p1;s16.p4;s16.p5", parent=CHIPS, measured=[("metrology", [TOL[h]]), ("afm", BEND[h])], inputs_of=sorted(H_DEP[h]))
    next(r for r in C.facts() if r["fact_id"] == HFACT[h])["parent"] = piece      # the design height is the chip's own setting
# a comparison holds no setting: the channel lengths scanned for Series A (1 mm, Fig. 4) and Series B (5 mm) are measurement settings
# of those samples' reflectometry
C.spread(f"{K}:fig4.cap#1", [f"{K}:meas:ent:{n}:reflectometry" for n in (1, 2, 3)], {f"{K}:meas:ent:{n}:reflectometry": f"sample {n}" for n in (1, 2, 3)})
C.spread(f"{K}:s7.p5#10", [f"{K}:meas:ent:{n}:reflectometry" for n in (4, 5, 6)], {f"{K}:meas:ent:{n}:reflectometry": f"sample {n}" for n in (4, 5, 6)})
# the authors' comparisons: the Table 1 series (what each varies), the reproducibility set (a replicate set), the simulations
C.comparisons(K, {grp("A"): ("series", "pillar_layout"), grp("B"): ("series", "objective_magnification"), grp("C"): ("series", "feature_height"),
                  grp("D"): ("series", "cycle_number"), grp("E"): ("series", "pulse_time"), grp("F"): ("series", "purge_time"),
                  grp("repro"): ("replicate", ""), grp("sims"): ("series", "feature_height;cycle_number")})
# in situ or ex situ (P6): the generic measurement activities hold calculations from the ex situ reflectometer profiles
C.modes(K, {f["fact_id"].split(":", 1)[1]: "ex_situ" for f in C.facts() if f["type"] == "activity" and f["fact_id"].endswith(":measurement")})
# what each GPC is averaged over (P5): Table 1's S/N and the S/N profiles are thickness over the run's cycles; gpc_sat is the model's
# saturation value
C.qualify(K, {f["fact_id"].split(":", 1)[1]: ("over=saturation" if f["fact_id"] == f"{K}:fig10.cap#11" else "over=run") for f in C.facts()
              if "#" in f["fact_id"] and (f["quantity"] == "growth_per_cycle" or "x=growth_per_cycle" in f["qualifiers"])})
# identity of entities with equal conditions (P23): Table 1 lists samples 4, 5, 6, 8 and 12 as separate samples
C.identity(K, "different", [f"{K}:ent:{n}" for n in (4, 5, 6, 8, 12)], "samples 4, 5, 6, 8 and 12 share every stated condition and are separate samples, each a row of Table 1 with its own results", "tab1.r4c0;tab1.r5c0;tab1.r6c0;tab1.r8c0;tab1.r13c0")
write(K, PID)
