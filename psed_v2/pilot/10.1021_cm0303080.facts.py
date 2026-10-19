#!/usr/bin/env python3
"""Stage 2 facts for ela03 (10.1021_cm0303080, Elam et al. 2003, Chem. Mater.: Al2O3 and ZnO ALD in the nanopores of anodic alumina
membranes, EPMA infiltration profiles, a Monte Carlo pore model, FTIR of the diffusion- and reaction-limited regimes). One row per
piece of knowledge, each citing the elements that state it; handles (variables) instead of hard-coded fact numbers (P83).

    python3 psed_v2/pilot/10.1021_cm0303080.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write, purpose  # noqa: E402

K, PID = "ela03", "10.1021_cm0303080"
A = "s1.p4"                                                                     # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}                                                                     # handle -> (stance, cause, effect, relation, supports)


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h", "heading")
NK("s1.p1", "author list")
NK("s1.p2;s2.p3;s2.p4;s2.p5;s2.p6;s2.p7", "affiliations and contact")
NK("s1.p3", "received dates")
NK(";".join([f"s2.p{i}" for i in range(8, 21)] + [f"s3.p{i}" for i in range(3, 22)] + ["s4.p6", "s4.p7", "s5.p23"]), "reference list, printed as footnotes")
NK("s6.p3", "acknowledgement")
NK("s6.p4", "article code")
NK("fig2.cap;fig2a;fig2b", "a drawing of the polishing procedure, no value")

# ---------------------------------------------------------------- abstract and introduction
c_aa = claim(f"abs.g1;{A};s2.p2", "AA membranes hold highly uniform nanometre-scale pores in a hexagonal close-packed array", "asserted")
ar_abs = f(f"abs.g1;{A}", "setting", "the nanopores of the AA membranes have an ultrahigh aspect ratio of about 10^3, which makes conformal coating inside them very hard",
           quantity="aspect_ratio", label_as_printed="L/d", value="1000", data_kind="stated")
c_ald = claim(f"abs.g2;{A};s2.p22", "ALD grows very even films over high-aspect-ratio substrates and controls thickness one monolayer at a time", "asserted",
              "self_limiting_growth", "step_coverage", "increases")
c_sem = claim(f"abs.g3;{A};s6.p1;s4.p3", "SEM of single nanopores shows that AA membranes with d = 65 nm and L = 50 µm are coated conformally by Al2O3 ALD when the reactant exposure times are long enough",
              "asserted", "pulse_time", "step_coverage", "increases")
c_epma = claim(f"abs.g3;{A};s6.p1;s4.x1", "Zn profiles by EPMA after ZnO ALD show the ZnO reaching progressively deeper into the nanopores as the exposure time grows, up to aspect ratios of about 5000",
               "asserted", "pulse_time", "penetration_depth", "increases")
c_mc = claim(f"abs.g4;{A};s6.p1;s5.p27", "a Monte Carlo simulation assuming Knudsen diffusion reproduces the measured Zn profiles and predicts the minimum reactant exposures for a conformal film",
             "asserted", "gas_diffusion", "penetration_depth", "causes")
c_regime = claim(f"abs.g4;{A};s6.p1;s5.p22", "the simulation predicts that the diffusion-limited coating turns reaction-limited once the ALD reaction probability is low enough",
                 "asserted", "initial_sticking_coefficient", "gas_diffusion", "limits")
ftir_plan = f(f"abs.g5;{A};s2.p25", "setting", "FTIR absorption was measured during the coating of AA membranes by Al2O3 and by SiO2 ALD to test the two regimes", method="ftir")
s_al = f(f"abs.g5;{A};s4.p13;s5.p25", "cited", "Al2O3 ALD surface reactions proceed with a fairly high probability per collision, about 10^-3",
         quantity="initial_sticking_coefficient", qualifiers="species=tma", label_as_printed="S", value="1e-3", data_kind="cited", method="cited", mentions="ref 24")
s_si = f(f"abs.g6;{A};s4.p13;s5.p26", "cited", "SiO2 ALD surface reactions proceed with a tiny probability per collision, about 10^-8",
         quantity="initial_sticking_coefficient", qualifiers="species=sicl4", label_as_printed="S", value="1e-8", data_kind="cited", method="cited", mentions="ref 39")
c_half = claim(f"abs.g6;{A};s6.p2;s5.p25", "Al2O3 ALD on the membrane shows diffusion-limited behaviour, the hydroxyl loss growing with the square root of time", "asserted",
               "gas_diffusion", "surface_coverage", "limits")
c_lin = claim(f"abs.g7;{A};s6.p2;s5.p26", "SiO2 ALD on the membrane shows reaction-limited behaviour, the hydroxyl loss growing linearly with time", "asserted",
              "initial_sticking_coefficient", "surface_coverage", "limits")
f("s2.p1", "cited", "nanoporous AA membranes are made by the controlled electrochemical oxidation (anodization) of aluminium in certain electrolytes", mentions="refs 1-5")
f("s2.p1", "cited", "AA membranes serve as nanoscale templates, chemical filters, gas separation membranes, gas sensors and catalysts", mentions="refs 6-13")
pore_dens = f("s2.p2", "claim", "each square centimetre of an AA film holds 10^8 to 10^11 uniform, non-intersecting cylindrical nanopores",
              quantity="pore_density", label_as_printed="pores per cm2", value_min="1e8", value_max="1e11", unit="cm-2", data_kind="stated")
CLAIMS[pore_dens] = ("asserted", "", "", "", [])
c_perp = claim("s2.p2;s2.p1", "the nanopores run perpendicular to the membrane surface, roughly in a hexagonal close-packed array", "asserted")
d_range = claim("s2.p2", "by choice of the anodization conditions AA membranes can be made with pore diameters from 4 to 200 nm", "asserted",
                quantity="feature_width", label_as_printed="d", value_min="4", value_max="200", unit="nm", data_kind="stated")
L_range = claim("s2.p2", "AA membrane pore lengths range from 1 to 200 µm and beyond", "asserted",
                quantity="body_thickness", label_as_printed="L", value_min="1", value_max="200", unit="µm", data_kind="stated")
ar_max = claim("s2.p2", "so AA nanopores can reach aspect ratios as high as 2.5 × 10^4", "asserted",
               quantity="aspect_ratio", label_as_printed="L/d", value="2.5e4", data_kind="stated", supports=[d_range, L_range])
c_sensor = claim("s2.p2", "AA-based gas sensors depend on depositing uniform chemoresistive films inside the nanopores", "asserted")
c_pvd = claim("s2.p2;s2.p21", "the ultrahigh aspect ratios of AA nanopores seriously challenge physical and chemical vapour deposition", "asserted",
              "aspect_ratio", "step_coverage", "decreases")
f("s2.p22", "cited", "ALD uses a binary sequence of self-limiting reactions between gas-phase precursors and the surface; each AB cycle deposits about one monolayer", mentions="refs 14, 15")
claim("s2.p22", "the digital growth gives precise thickness control, and self-limiting reactions give excellent uniformity and conformality", "asserted",
      "self_limiting_growth", "step_coverage", "increases")
f("s2.p22", "cited", "ALD has coated porous media: powders, tubular gas-separation membranes, porous silicon and anodic alumina", mentions="refs 16-23")
scope_d = claim("s2.p23", "this study deposits Al2O3 and ZnO ALD films in AA membranes with pore diameters of 19 to 65 nm", "asserted",
                quantity="feature_width", label_as_printed="d", value_min="19", value_max="65", unit="nm", data_kind="stated")
scope_L = claim("s2.p23", "the membranes studied are 50 to 92 µm thick", "asserted",
                quantity="body_thickness", label_as_printed="L", value_min="50", value_max="92", unit="µm", data_kind="stated")
f("s2.p23", "cited", "Al2O3 ALD is among the best-studied ALD processes and serves as the model system for ALD in porous media", mentions="refs 24-28")
f("s2.p23", "cited", "ZnO is a semiconducting oxide with gas-sensing applications", mentions="refs 29, 30")
f("s2.p24", "cited", "ZnO ALD has received much attention", mentions="refs 31-36")
meth_plan = f("s2.p23;s2.p24", "setting", "SEM checks that Al2O3 ALD coats the membranes conformally at long enough exposures; EPMA quantifies how far ZnO ALD penetrates as a function of exposure time",
  method="epma")
ftir_plan2 = f("s2.p25", "setting", "in a second set of experiments Al2O3 and SiO2 ALD were grown on an AA membrane under high vacuum while in situ FTIR followed the surface chemistry", method="ftir")
claim("s2.p25", "because Al2O3 and SiO2 ALD have different reactive sticking coefficients, the two processes probe different rate-limiting regimes of the time dependence", "asserted",
      "initial_sticking_coefficient", "gas_diffusion", "limits")
mc_plan = f("s2.p25", "model", "a Monte Carlo model of reactant diffusion and growth in the nanopores reproduces the growth and predicts what conditions give conformal films across many aspect ratios")

# ---------------------------------------------------------------- II A. the membranes (an input entity with pieces per anodization recipe)
al_pur = f("s3.p1", "setting", "the membranes were made by anodizing 99.99 % pure aluminium in acidic electrolytes in a two-electrode cell",
           quantity="other", label_as_printed="Al purity", value="99.99", unit="%", data_kind="stated", mentions="ref 2")
anod_ctl = f("s3.p1;tab1.cap", "setting", "pore diameter and film thickness were set through the anodization voltage, current and temperature (Table 1)")
mem_dia = f("s3.p1", "setting", "the aluminium was masked lithographically to define circular membranes 1 cm across",
            quantity="body_diameter", label_as_printed="membrane diameter", value="1", unit="cm", data_kind="stated")
liftoff = f("s3.p1", "setting", "after anodization the porous alumina sat on a dense barrier layer, which was removed electrochemically to lift the membranes off the aluminium")
sides = f("s3.p1;s5.p3", "setting", "the membranes have uniform cylindrical pores open on both faces, so reactant enters from both ends",
          quantity="entry_sides", value_text="two", data_kind="stated")
fig1_d = f("fig1.cap;s3.p1;fig1a", "observation", "the uncoated membrane of Fig. 1 has 40 nm pores (SEM)",
           quantity="feature_width", label_as_printed="d", value="40", unit="nm", data_kind="measured", method="sem", mentions="Fig. 1")
fig1_L = f("s3.p1;fig1.cap;fig1a", "observation", "the uncoated membrane of Fig. 1 is about 120 µm thick (SEM side view)",
           quantity="body_thickness", label_as_printed="thickness", value="120", unit="µm", data_kind="measured", method="sem", mentions="Fig. 1")
f("fig1a;fig1.cap", "observation", "Fig. 1(a): a cross-sectional SEM view of the 40 nm pores, straight parallel channels", method="sem")
f("fig1b;fig1.cap", "observation", "Fig. 1(b): a top SEM view of the hexagonal pore array", method="sem")
# Table 1: three anodization recipes and the membranes they give
TAB = {}
for r, ely, V, T, Qc, d, L in (("1", "1.2 M H2SO4", "20", "2", "100, 200", "19", "50, 100"), ("2", "3% H2C2O4", "50", "12", "100", "46", "50"),
                                ("3", "3% H2C2O4", "70", "12", "100", "65", "50")):
    lab = f"d {d} nm"
    e = {}
    e["ely"] = f(f"tab1.r{r}c0;tab1.r0c0;tab1.cap", "setting", f"Table 1, {lab} membranes: anodized in {ely}", quantity="other", label_as_printed="electrolyte", value_text=ely, mentions=lab)
    e["V"] = f(f"tab1.r{r}c1;tab1.r0c1;tab1.cap", "setting", f"Table 1, {lab} membranes: anodization potential {V} V", quantity="other", label_as_printed="anodization potential", value=V, unit="V", data_kind="stated", mentions=lab)
    e["T"] = f(f"tab1.r{r}c2;tab1.r0c2;tab1.cap", "setting", f"Table 1, {lab} membranes: anodization temperature {T} °C", quantity="other", label_as_printed="anodization temperature", value=T, unit="°C", data_kind="stated", mentions=lab)
    if "," in Qc:
        e["Q"] = f(f"tab1.r{r}c3;tab1.r0c3;tab1.cap", "setting", f"Table 1, {lab} membranes: charge density 100 to 200 C/cm2 (100 for the thinner, 200 for the thicker membranes)", quantity="other", label_as_printed="charge density", value_min="100", value_max="200", unit="C/cm2", data_kind="stated", mentions=lab)
    else:
        e["Q"] = f(f"tab1.r{r}c3;tab1.r0c3;tab1.cap", "setting", f"Table 1, {lab} membranes: charge density {Qc} C/cm2", quantity="other", label_as_printed="charge density", value=Qc, unit="C/cm2", data_kind="stated", mentions=lab)
    e["d"] = f(f"tab1.r{r}c4;tab1.r0c4;tab1.cap", "setting", f"Table 1, {lab} membranes: pore diameter {d} nm", quantity="feature_width", label_as_printed="pore diameter (nm)", value=d, unit="nm", data_kind="stated", mentions=lab)
    if "," in L:
        e["L"] = f(f"tab1.r{r}c5;tab1.r0c5;tab1.cap", "setting", f"Table 1, {lab} membranes: film thickness 50 to 100 µm (50 at the lower, 100 at the higher charge density)", quantity="body_thickness", label_as_printed="film thickness (µm)", value_min="50", value_max="100", unit="µm", data_kind="stated", mentions=lab)
    else:
        e["L"] = f(f"tab1.r{r}c5;tab1.r0c5;tab1.cap", "setting", f"Table 1, {lab} membranes: film thickness {L} µm", quantity="body_thickness", label_as_printed="film thickness (µm)", value=L, unit="µm", data_kind="stated", mentions=lab)
    TAB[d] = e
NK("tab1.r0c6", "an empty header cell of the merged column group")

# ---------------------------------------------------------------- II B. the ALD recipe
reactor = f("s3.p2", "setting", "the membranes were coated in a viscous-flow ALD reactor", quantity="reactor", value_text="viscous-flow ALD reactor (home-built, ref. 37)", data_kind="stated", mentions="ref 37")
rtype = f("s3.p2;s2.p23", "setting", "the reactor works in viscous flow with a carrier gas: a flow-type reactor", quantity="reactor_type", value_text="flow_type", data_kind="stated")
T177 = f("s3.p2;s4.p1;s4.p4;s4.p10;s4.p12", "setting", "surface reactions at 177 °C", quantity="deposition_temperature", value="177", unit="°C", data_kind="stated")
carrier = f("s3.p2", "setting", "nitrogen carrier gas", quantity="carrier_gas", value_text="n2", data_kind="stated")
flow = f("s3.p2;s3.p27", "setting", "N2 carrier flow 200 sccm", quantity="gas_flow_rate", qualifiers="gas=n2", value="200", unit="sccm", data_kind="stated")
ptot = f("s3.p2;s3.p27", "setting", "reactor pressure 1 Torr", quantity="process_pressure", value="1", unit="Torr", data_kind="stated")
perp = f("s3.p2;s3.p22", "setting", "the membranes sat with the pore axes perpendicular to the carrier flow")
slow_p = f("s3.p22", "setting", "pressure was changed slowly when pumping down after loading and venting before unloading, since fast changes could sweep the fragile membranes out of the flow tube")
pur_tma = f("s3.p23", "setting", "Al2O3 ALD used Akzo Nobel semiconductor-grade TMA and Fisher Optima deionized water", quantity="precursor_purity", qualifiers="species=tma", value_text="semiconductor grade", mentions="refs 23-25")
eq1_m = f("eq1;s3.p23", "model", "Eq. (1), the A half-reaction of Al2O3 ALD: a surface hydroxyl takes up TMA, leaving AlOAl(CH3)2* and releasing methane")
eq2_m = f("eq2;s3.p23", "model", "Eq. (2), the B half-reaction of Al2O3 ALD: a surface methyl reacts with water to a hydroxyl and methane")
pur_dez = f("s3.p24", "setting", "ZnO ALD used Akzo Nobel semiconductor-grade diethylzinc and deionized water", quantity="precursor_purity", qualifiers="species=dez", value_text="semiconductor grade", mentions="refs 31, 33, 34")
eq3_m = f("eq3;s3.p24", "model", "Eq. (3), the A half-reaction of ZnO ALD: a surface hydroxyl takes up DEZ, leaving ZnOZn(C2H5)* and releasing ethane")
eq4_m = f("eq4;s3.p24", "model", "Eq. (4), the B half-reaction of ZnO ALD: the surface ethyl reacts with water to a hydroxyl and ethane")
def_t = f("s3.p25", "definition", "the timing sequence t1-t2-t3-t4 in seconds: t1 the A exposure, t2 the purge after it, t3 the B exposure, t4 the purge after it", quantity="pulse_time", term="t1|t3|exposure time|Exposure Time")
rng_t = f("s3.p25", "setting", "exposure steps of 1 to 30 s were used across the study; the shortest sequence was 1-3-1-3 and the longest 30-30-30-30", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value_min="1", value_max="30", unit="s", data_kind="stated")
rng_pg = f("s3.p25", "setting", "purge times across the study ranged from 3 to 30 s", quantity="purge_time", qualifiers="step=purge_A", value_min="3", value_max="30", unit="s", data_kind="stated")
p_tma = f("s3.p25;s5.p10;s5.p12", "setting", "TMA partial pressure 0.15 Torr in the Al2O3 exposures", quantity="partial_pressure", qualifiers="species=tma", value="0.15", unit="Torr", data_kind="stated")
p_dez = f("s3.p25;s5.p24", "setting", "DEZ partial pressure 0.068 Torr in the ZnO exposures", quantity="partial_pressure", qualifiers="species=dez", value="0.068", unit="Torr", data_kind="stated")
p_h2o = f("s3.p25;s5.p2", "setting", "the water partial pressure in the H2O exposures was two to three times the TMA or DEZ pressure, about 0.14 to 0.45 Torr",
          quantity="partial_pressure", qualifiers="species=h2o", value_min="0.14", value_max="0.45", unit="Torr", data_kind="computed_by_authors", inputs=[p_tma, p_dez])
claim("s3.p26", "the highest-aspect-ratio membranes need very large exposures, impractical under continuous flow because they drain the precursor reservoirs", "asserted",
      "aspect_ratio", "exposure", "increases")
qs_mode = f("s3.p26", "setting", "for those membranes the reactor ran quasi-statically, with a computer-controlled pneumatic exhaust valve between the flow tube and the mechanical pump")
qs_base = f("s3.p26;s3.p27", "setting", "quasi-static cycle: the tube is pumped below 0.035 Torr before each dose and after it", quantity="other", label_as_printed="base pressure", value="0.035", censor="<", unit="Torr", data_kind="stated")
qs_pdez = f("s3.p26;s4.p12", "setting", "quasi-static cycle: with the exhaust valve shut, 5 Torr of DEZ fills the reactor", quantity="partial_pressure", qualifiers="species=dez", value="5", unit="Torr", data_kind="stated")
qs_tdez = f("s3.p26;s4.p12", "setting", "quasi-static cycle: DEZ exposure 120 s", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value="120", unit="s", data_kind="stated")
qs_purge = f("s3.p27", "setting", "quasi-static cycle: after evacuation, a 200 sccm N2 purge at 1 Torr for 240 s", quantity="purge_time", qualifiers="step=purge_A", value="240", unit="s", data_kind="stated")
qs_ph2o = f("s3.p27", "setting", "quasi-static cycle: the H2O half-cycle repeats the sequence with 5 Torr of water", quantity="partial_pressure", qualifiers="species=h2o", value="5", unit="Torr", data_kind="stated")
qs_th2o = f("s3.p27", "setting", "quasi-static cycle: H2O exposure 120 s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="120", unit="s", data_kind="stated")
qs_purge2 = f("s3.p27", "setting", "quasi-static cycle: the purge after water is the same 240 s N2 purge", quantity="purge_time", qualifiers="step=purge_B", value="240", unit="s", data_kind="stated")

# ---------------------------------------------------------------- II C. ex situ analysis
sem_prep = f("s3.p28", "setting", "coated membranes were embedded in epoxy at a shallow angle (Fig. 2a), polished with ever finer sandpaper and then with a fine alumina paste to expose the pore cross sections (Fig. 2b)", method="sem", mentions="Fig. 2")
claim("s3.p28", "the shallow mounting angle brings pore cross sections from the whole membrane thickness into one polished plane, which eases SEM analysis", "asserted")
sem_etch = f("s3.p29", "setting", "before SEM the polished membranes were etched briefly in phosphoric acid, which sharpens the contrast between ALD alumina and anodic alumina and widens the pores where they are uncoated", method="sem")
etch_cit = f("s3.p29", "cited", "ALD-grown Al2O3 resists phosphoric acid better than anodic alumina does", mentions="ref 9")
sem_inst = f("s3.p29", "setting", "SEM in a JEOL JSM-5800", method="sem")
claim("s3.p30", "SEM shows the ALD film on the pore walls directly and so judges the coating's uniformity along the pores qualitatively", "asserted")
claim("s3.p30", "a quantified thickness profile is hard to get from SEM images, yet it is needed to compare with the simulations, so EPMA was used after ZnO ALD", "limitation")
epma_who = f("s3.p30", "setting", "EPMA gives the Zn concentration against distance into the pores; the measurements were made by J. Drexler (Geological Sciences, U. Colorado)", method="epma")
epma_prep = f("s3.p31;s3.p32", "setting", "for EPMA the ZnO-coated membranes were cleaved to expose the interior, mounted in epoxy with the pore axes parallel to the stub face, polished and carbon-coated against charging", method="epma")
epma_inst = f("s3.p32", "setting", "EPMA in a JEOL 8600 microprobe at a beam energy of 15 keV", quantity="other", label_as_printed="beam energy", value="15", unit="keV", data_kind="stated", method="epma")
epma_cur = f("s3.p32", "setting", "EPMA beam current 20 nA", quantity="other", label_as_printed="beam current", value="20", unit="nA", data_kind="stated", method="epma")
epma_res = f("s3.p32", "setting", "the EPMA spatial resolution is 3 to 5 µm, so each point averages several hundred nanopores",
             quantity="probe_resolution", value_min="3", value_max="5", unit="µm", data_kind="stated", method="epma")

# ---------------------------------------------------------------- II D. FTIR apparatus
ftir_inst = f("s3.p33", "setting", "transmission FTIR ran in a high-vacuum chamber (Nicolet Magna 560, MCT-B detector)", method="ftir", mentions="refs 16-18")
ftir_d = f("s3.p33;s4.p14;s5.p25", "setting", "the FTIR sample was an AA membrane with 47 nm pores", quantity="feature_width", label_as_printed="d", value="47", unit="nm", data_kind="stated")
ftir_L = f("s3.p33;s4.p14;s5.p25", "setting", "the FTIR membrane is 50 µm thick", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="stated")
claim("s3.p33", "AA membranes transmit infrared light, so transmission FTIR follows the surface species on the inner pore walls", "asserted")
ftir_mount = f("s3.p33", "setting", "the membrane edge was glued to a tungsten grid with Aremco Ceramabond 571; tantalum foils spot-welded to the grid sat in copper clamps", method="ftir")
ftir_heat = f("s3.p33", "setting", "the sample was heated resistively through the grid and foils; a chromel-alumel thermocouple glued to the bottom edge of the membrane read its temperature", method="ftir")
ftir_runs = f("s3.p34", "setting", "FTIR spectra were taken against time during sequential TMA and H2O exposures at 177 °C (Al2O3 ALD) and during sequential SiCl4 and H2O exposures at 427 °C (SiO2 ALD)", method="ftir")
eq5_m = f("eq5;s3.p34", "model", "Eq. (5), the A half-reaction of SiO2 ALD: a surface silanol takes up SiCl4, leaving SiOSiCl3* and releasing HCl", mentions="refs 38, 39")
eq6_m = f("eq6;s3.p34", "model", "Eq. (6), the B half-reaction of SiO2 ALD: a surface Si-Cl reacts with water to a silanol and HCl")
sicl4_pur = f("s3.p35", "setting", "SiCl4 of 99.999 % purity from Alfa Aesar", quantity="precursor_purity", qualifiers="species=sicl4", value="99.999", unit="%", data_kind="stated")

# ---------------------------------------------------------------- III A. SEM after Al2O3 ALD (four exposure times)
sem_dL = f("s4.p1;abs.g3;s6.p1", "setting", "the Al2O3 SEM series used membranes with d = 65 nm and L = 50 µm", quantity="feature_width", label_as_printed="d", value="65", unit="nm", data_kind="stated", mentions="Al2O3 series")
sem_L = f("s4.p1;abs.g3", "setting", "Al2O3 SEM series: membranes 50 µm thick", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="stated", mentions="Al2O3 series")
sem_N = f("s4.p1;fig3.cap", "setting", "100 AB cycles of Al2O3 ALD", quantity="cycle_number", value="100", data_kind="stated")
SEQ = (("1", "5"), ("3", "6"), ("10", "30"), ("30", "30"))
SEM = {}
for t, pg in SEQ:
    SEM[t] = dict(
        tA=f("s4.p1;fig3.cap", "setting", f"Al2O3 SEM series, sequence {t}-{pg}-{t}-{pg}: TMA exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value=t, unit="s", data_kind="stated", mentions=f"Al2O3;{t}-{pg}-{t}-{pg}"),
        pA=f("s4.p1", "setting", f"Al2O3 SEM series, sequence {t}-{pg}-{t}-{pg}: purge after TMA {pg} s", quantity="purge_time", qualifiers="step=purge_A", value=pg, unit="s", data_kind="stated", mentions=f"Al2O3;{t}-{pg}-{t}-{pg}"),
        tB=f("s4.p1", "setting", f"Al2O3 SEM series, sequence {t}-{pg}-{t}-{pg}: water exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value=t, unit="s", data_kind="stated", mentions=f"Al2O3;{t}-{pg}-{t}-{pg}"),
        pB=f("s4.p1", "setting", f"Al2O3 SEM series, sequence {t}-{pg}-{t}-{pg}: purge after water {pg} s", quantity="purge_time", qualifiers="step=purge_B", value=pg, unit="s", data_kind="stated", mentions=f"Al2O3;{t}-{pg}-{t}-{pg}"))
al_flat = f("s4.p1", "cited", "on a flat surface these 100 cycles would give 129 Å of Al2O3", quantity="film_thickness", qualifiers="position=planar", value="129", unit="Å", data_kind="cited", method="cited", mentions="ref 36;Al2O3", links=sem_N)
al_dfin = f("s4.p1", "derived", "at the same growth rate inside the pores, 100 Al2O3 cycles would narrow the 65 nm pores to 39 nm",
            quantity="feature_width", qualifiers="stage=final", label_as_printed="d", value="39", unit="nm", data_kind="computed_by_authors", method="calculation", inputs=[al_flat, sem_dL], mentions="Al2O3")
fig3_obs = f("s4.p1;fig3.cap;fig3", "observation", "Fig. 3 shows SEM images from the top, middle and bottom of the membranes for the four exposure times", method="sem")
o_ends = f("s4.p1;fig3", "observation", "the top and bottom images show a similar degree of coating for every exposure time", method="sem")
claim("s4.p1;s4.p2", "the top and bottom faces see the reactants directly in the flow tube, with no diffusion needed, so even 1 s exposures should coat them", "asserted",
      "pulse_time", "step_coverage", "no_effect", supports=[o_ends])
o_1s = f("s4.p3;fig3", "observation", "for the 1 s exposures the pores in the middle of the membrane were widened by the phosphoric acid etch: little or no Al2O3 there", method="sem", mentions="1 s")
c_1s = claim("s4.p3", "1 s exposures did not let the Al2O3 ALD precursors reach the middle of the 50 µm pores", "asserted", "pulse_time", "penetration_depth", "increases", supports=[o_1s])
o_3s = f("s4.p3;fig3", "observation", "exposure times of 3 s or more let the Al2O3 reactants reach the middle of the pores", quantity="other", label_as_printed="exposure time that coats the pore middle",
         value="3", censor=">", unit="s", data_kind="measured", method="sem")
o_wide = f("s4.p3;fig3", "observation", "for 3 and 10 s some middle pores are wider than average", method="sem", mentions="3 s;10 s")
claim("s4.p3", "the wider pores were etched more because they received less Al2O3, perhaps because their gas conductance was lower to begin with", "hedged",
      "gas_diffusion", "film_thickness", "causes", supports=[o_wide, SEM["3"]["tA"], SEM["10"]["tA"]])

# ---------------------------------------------------------------- III B. EPMA after ZnO ALD: exposure series, diameter series, the AR 5000 membrane
zno_dL = f("s4.p4", "setting", "the ZnO exposure series used membranes with d = 65 nm and L = 50 µm", quantity="feature_width", label_as_printed="d", value="65", unit="nm", data_kind="stated", mentions="ZnO series")
zno_L = f("s4.p4", "setting", "ZnO exposure series: membranes 50 µm thick", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="stated", mentions="ZnO series")
zno_N = f("s4.p4;fig4.cap;fig5.cap", "setting", "64 AB cycles of ZnO ALD", quantity="cycle_number", value="64", data_kind="stated")
ZNO = {}
for t, pg in SEQ:
    ZNO[t] = dict(
        tA=f("s4.p4;fig4.cap;fig5.cap", "setting", f"ZnO exposure series, sequence {t}-{pg}-{t}-{pg}: DEZ exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value=t, unit="s", data_kind="stated", mentions=f"{t}-{pg}-{t}-{pg}"),
        pA=f("s4.p4", "setting", f"ZnO exposure series, sequence {t}-{pg}-{t}-{pg}: purge after DEZ {pg} s", quantity="purge_time", qualifiers="step=purge_A", value=pg, unit="s", data_kind="stated", mentions=f"{t}-{pg}-{t}-{pg}"),
        tB=f("s4.p4", "setting", f"ZnO exposure series, sequence {t}-{pg}-{t}-{pg}: water exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value=t, unit="s", data_kind="stated", mentions=f"{t}-{pg}-{t}-{pg}"),
        pB=f("s4.p4", "setting", f"ZnO exposure series, sequence {t}-{pg}-{t}-{pg}: purge after water {pg} s", quantity="purge_time", qualifiers="step=purge_B", value=pg, unit="s", data_kind="stated", mentions=f"{t}-{pg}-{t}-{pg}"))
zn_flat = f("s4.p4", "cited", "64 ZnO cycles give 129 Å on a flat surface", quantity="film_thickness", qualifiers="position=planar", value="129", unit="Å", data_kind="cited", method="cited", mentions="ref 36;ZnO", links=zno_N)
zn_dfin = f("s4.p4", "derived", "such a ZnO film would narrow the 65 nm pores to 39 nm", quantity="feature_width", qualifiers="stage=final", label_as_printed="d", value="39", unit="nm",
            data_kind="computed_by_authors", method="calculation", inputs=[zn_flat, zno_dL], mentions="ZnO")
fig4_obs = f("s4.x1;fig4;fig4.cap", "observation", "Fig. 4: EPMA dot maps of the cross sections, the density of white dots giving the Zn concentration, one map per exposure time", method="epma")
o_map_ends = f("s4.x1;fig4", "observation", "every map shows a high Zn concentration at both faces of the membrane", method="epma")
o_map_prog = f("s4.x1;fig4", "observation", "the Zn reaches progressively further toward the middle as the exposure time grows", method="epma")
o_map30 = f("s4.x1;fig4", "observation", "with 30 s exposures the Zn concentration is nearly uniform through the membrane", method="epma", mentions="30 s")
claim("s4.x1", "a nearly uniform Zn map means a conformal ZnO film continuous along the whole pore", "asserted", "pulse_time", "step_coverage", "increases", supports=[o_map30])
scan_step = f("s4.p5", "setting", "EPMA line scans along the pore axis recorded the Zn concentration about every 1 µm", quantity="other", label_as_printed="scan step", value="1", unit="µm", data_kind="stated", method="epma")
def_norm = f("s4.p5;s4.p8;fig5.cap", "definition", "the Zn profiles of Fig. 5(a) are normalized to the highest Zn concentration measured", quantity="normalized_thickness", qualifiers="reference=maximum",
             term="Relative ZnO Coverage|Relative Al2O3 Coverage|relative coverage", definition_note="EPMA counts normalized to the highest concentration of the line scan, not to a planar reference")
o_prof = f("s4.p8;fig5a", "observation", "the ZnO film extends further into the membrane as the exposure time grows", method="epma")
unif30 = f("s4.p8;fig5a", "observation", "for 30 s exposures the Zn profile is nearly uniform through the membrane, within ±10 %",
           quantity="thickness_nonuniformity", value="10", unit="%", data_kind="measured", method="epma", mentions="30 s")
PTS = {}
for t in ("1", "3", "10", "30"):
    PTS[("5a", t)] = f("fig5a;fig5.cap;s4.p8", "observation", f"Fig. 5(a), {t} s exposures: relative ZnO coverage against distance into the membrane from one face (EPMA line scan)",
                       quantity="normalized_thickness", qualifiers="reference=maximum", data_kind="measured", method="epma", mentions=f"{t} s")
def_int = f("s4.p9;fig5.cap", "definition", "the normalized integrated coverage is the integral of a relative coverage profile over the membrane, normalized to its saturation value", quantity="surface_coverage",
            term="Normalized Integrated ZnO Coverage|Normalized Integrated Al2O3 Coverage|Normalized Integrated Coverage|integrated coverage",
            definition_note="integral of the relative EPMA coverage over the pore length, normalized to saturation, not a fraction of covered sites")
def_pd = f("s4.p10;fig6.cap", "definition", "the pore diameter d of a membrane is the width of its cylindrical pores", quantity="feature_width", term="Pore Diameter|d", definition_note="pore diameter of the membrane")
def_oh = f("fig8.cap", "definition", "the loss in hydroxyl feature is the drop of the FTIR hydroxyl absorbance after an exposure, in absorbance units", quantity="signal_intensity",
           term="Loss in Hydroxyl Feature", definition_note="FTIR hydroxyl absorbance lost after an exposure")
fig5b_obs = f("s4.x2;s4.p9;fig5b;fig5.cap", "observation", "Fig. 5(b): the normalized integrated ZnO coverage of each Fig. 5(a) profile against exposure time", quantity="surface_coverage", method="epma")
k_exp = f("s4.p9;s5.x1;fig5b", "derived", "a least-squares fit y = k t^1/2 to the integrated coverages between 0 and 10 s gives k = 0.23",
          quantity="other", label_as_printed="k", value="0.23", unit="s^-1/2", data_kind="computed_by_authors", method="calculation", mentions="Fig. 5b")
c_sqrt = claim("s4.p9", "the integrated ZnO coverage follows a square-root time law before it levels off at saturation beyond about 10 s", "asserted",
               "pulse_time", "surface_coverage", "increases", supports=[k_exp])
sat_t = f("s4.p9;fig5b", "observation", "the integrated coverage approaches its saturation value for exposure times above 10 s", quantity="other", label_as_printed="exposure time at saturation",
          value="10", censor=">", unit="s", data_kind="measured", method="epma")
# diameter series
dia_L = f("s4.p10;fig6.cap", "setting", "diameter series: membranes 50 µm thick", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="stated", mentions="diameter series")
DIA = {}
for d, n in (("19", "19"), ("46", "45"), ("65", "64")):
    DIA[d] = dict(d=f("s4.p10;fig6.cap", "setting", f"diameter series, d = {d} nm membrane", quantity="feature_width", label_as_printed="d", value=d, unit="nm", data_kind="stated", mentions=f"{d} nm"),
                  N=f("s4.p10;fig6.cap", "setting", f"diameter series, d = {d} nm membrane: {n} AB cycles of ZnO ALD", quantity="cycle_number", value=n, data_kind="stated", mentions=f"{d} nm"))
claim("s4.p10", "the cycle numbers 19, 45 and 64 were chosen to narrow each pore diameter by about 40 %", "asserted", "cycle_number", "feature_width", "decreases",
      supports=[DIA[d]["N"] for d in ("19", "46", "65")], quantity="other", label_as_printed="diameter reduction", value="40", unit="%", data_kind="stated")
dia_tA = f("s4.p10;fig6.cap", "setting", "diameter series: timing 5-10-5-10, DEZ exposure 5 s", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value="5", unit="s", data_kind="stated", mentions="5-10-5-10")
dia_pA = f("s4.p10", "setting", "diameter series: purge after DEZ 10 s", quantity="purge_time", qualifiers="step=purge_A", value="10", unit="s", data_kind="stated", mentions="5-10-5-10")
dia_tB = f("s4.p10", "setting", "diameter series: water exposure 5 s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="5", unit="s", data_kind="stated", mentions="5-10-5-10")
dia_pB = f("s4.p10", "setting", "diameter series: purge after water 10 s", quantity="purge_time", qualifiers="step=purge_B", value="10", unit="s", data_kind="stated", mentions="5-10-5-10")
o_dia = f("s4.p10;fig6a", "observation", "at a fixed 5 s exposure the ZnO profiles reach further into the pores the wider the pores are", method="epma")
for d, n in (("19", "19"), ("46", "45"), ("65", "64")):
    PTS[("6a", d)] = f("fig6a;fig6.cap;s4.p10", "observation", f"Fig. 6(a), d = {d} nm: relative ZnO coverage against distance into the membrane (EPMA line scan, 5 s exposures)",
                       quantity="normalized_thickness", qualifiers="reference=maximum", data_kind="measured", method="epma", mentions=f"{d} nm")
fig6b_obs = f("fig6b;fig6.cap;s4.p10", "observation", "Fig. 6(b): the normalized integrated ZnO coverage against pore diameter, with a linear least-squares fit", quantity="surface_coverage", method="epma")
slope_exp = f("s5.p17;s4.p10;fig6b", "derived", "the linear fit of integrated coverage against pore diameter in Fig. 6(b) has a slope of 0.25 per nm",
              quantity="other", label_as_printed="slope", value="0.25", unit="nm-1", data_kind="computed_by_authors", method="calculation", mentions="Fig. 6b")
# the AR 5000 membrane
ar_d = f("s4.p11;fig7.cap", "setting", "the ultrahigh-aspect-ratio membrane has 19 nm pores", quantity="feature_width", label_as_printed="d", value="19", unit="nm", data_kind="stated")
ar_L = f("s4.p11;fig7.cap", "setting", "the ultrahigh-aspect-ratio membrane is 92 µm thick", quantity="body_thickness", label_as_printed="L", value="92", unit="µm", data_kind="stated")
ar5000 = f("s4.p11;abs.g3;fig7.cap;s6.p1;s5.p34", "derived", "its aspect ratio L/d is about 5000", quantity="aspect_ratio", label_as_printed="L/d", value="5000", data_kind="computed_by_authors", method="calculation", inputs=[ar_L, ar_d])
f("s4.p11", "definition", "the paper's aspect ratio L/d divides the full membrane thickness L by the pore diameter d, although reactant enters from both faces", quantity="aspect_ratio",
  term="L/d|Aspect Ratio (L/D)", definition_note="full membrane thickness over pore diameter, both faces open")
ar_qs = f("s4.p11;s4.p12", "setting", "the AR 5000 membrane was coated in the quasi-static mode of Sec. II B", mentions="Sec. II B")
ar_N = f("s4.p12;fig7.cap", "setting", "the AR 5000 membrane got 19 ZnO ALD cycles", quantity="cycle_number", value="19", data_kind="stated")
fig7a_obs = f("s4.p12;fig7a;fig7.cap", "observation", "Fig. 7(a): the EPMA Zn map of the AR 5000 membrane", method="epma")
PTS[("7b", "")] = f("fig7b;fig7.cap;s4.p12", "observation", "Fig. 7(b): relative ZnO coverage across the 92 µm membrane (EPMA line scan)",
                    quantity="normalized_thickness", qualifiers="reference=maximum", data_kind="measured", method="epma")
o_nodip = f("s4.p12;fig7b", "observation", "the profile shows no dip at the middle of the 92 µm membrane", method="epma")
claim("s4.p12", "the missing mid-membrane dip means the ZnO coating runs continuously through the pores of the AR 5000 membrane", "asserted", "exposure", "step_coverage", "increases", supports=[o_nodip])
o_slope7 = f("s4.p12;fig7b", "observation", "the Zn profile slopes across the membrane", method="epma")
claim("s4.p12", "the slope may reflect how the sample was oriented in the microprobe, a small pore-diameter gradient along the membrane, or pores left partly closed by the lift-off", "hedged",
      "scan_angle", "signal_intensity", "causes", supports=[o_slope7])

# ---------------------------------------------------------------- III C. FTIR
sat_al = f("s4.p13", "cited", "the TMA and H2O half-reactions of Al2O3 ALD saturate at exposures of about 10^4 L", quantity="exposure", qualifiers="species=tma", value="1e4", unit="L", data_kind="cited", method="cited", mentions="ref 24")
f("s4.p13", "definition", "1 Langmuir (L) is 10^-6 Torr s", quantity="exposure", term="Langmuir")
sat_si = f("s4.p13", "cited", "the SiCl4 and H2O half-reactions of SiO2 ALD need about 10^9 L to saturate", quantity="exposure", qualifiers="species=sicl4", value="1e9", unit="L", data_kind="cited", method="cited", mentions="ref 39")
claim("s4.p13", "the saturation exposures imply far higher reactive sticking coefficients for TMA and H2O on Al2O3 than for SiCl4 and H2O on SiO2", "asserted",
      "exposure", "initial_sticking_coefficient", "decreases", supports=[sat_al, sat_si])
ini_N = f("s4.p14", "setting", "FTIR Al2O3 experiment: an initial Al2O3 layer from 4 TMA/H2O cycles", quantity="cycle_number", value="4", data_kind="stated")
ini_p = f("s4.p14", "setting", "FTIR Al2O3 experiment: initial-layer reactant pressures 2 to 5 Torr", quantity="partial_pressure", qualifiers="species=tma", value_min="2", value_max="5", unit="Torr", data_kind="stated")
ini_t = f("s4.p14", "setting", "FTIR Al2O3 experiment: initial-layer exposures of 15 to 30 min", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value_min="15", value_max="30", unit="min", data_kind="stated")
ini_T = f("s4.p14;s4.p15;s3.p34", "setting", "FTIR Al2O3 experiment at a substrate temperature of 177 °C", quantity="deposition_temperature", value="177", unit="°C", data_kind="stated", mentions="FTIR")
ftir_sat = f("s4.p14", "observation", "FTIR confirmed that those exposures saturated each half-reaction", method="ftir")
oh_al = f("s4.p14", "observation", "after the initial layer the spectrum shows a broad O-H stretch band between about 2700 and 3800 cm-1 from AlOH* surface hydroxyls",
          quantity="other", label_as_printed="O-H stretch band", value_min="2700", value_max="3800", unit="cm-1", data_kind="measured", method="ftir", mentions="ref 23")
up_p = f("s4.p15", "setting", "the hydroxylated Al2O3 surface then got successive small TMA exposures at about 10^-3 Torr", quantity="partial_pressure", qualifiers="species=tma", value="1e-3", unit="Torr", data_kind="stated")
spec_T = f("s4.p15;s4.p17", "setting", "each FTIR spectrum was recorded at 77 °C after an exposure", quantity="other", label_as_printed="spectrum temperature", value="77", unit="°C", data_kind="stated", method="ftir")
o_aloh = f("s4.p15", "observation", "the AlOH* band shrinks with growing TMA exposure, as Eq. (1) predicts", method="ftir")
fig8a_obs = f("s4.p15;fig8a;fig8.cap", "observation", "Fig. 8(a): the loss of integrated AlOH* absorbance against TMA exposure time, with a nonlinear least-squares fit y = k t^1/2", quantity="signal_intensity", method="ftir")
conv_N = f("s4.p16", "setting", "FTIR SiO2 experiment: the Al2O3 surface was turned into SiO2 by 2 SiCl4/H2O cycles", quantity="cycle_number", value="2", data_kind="stated")
conv_p = f("s4.p16", "setting", "FTIR SiO2 experiment: SiCl4 and H2O pressures of 10 Torr for the conversion", quantity="partial_pressure", qualifiers="species=sicl4", value="10", unit="Torr", data_kind="stated")
conv_t = f("s4.p16", "setting", "FTIR SiO2 experiment: conversion exposures of 5 min", quantity="pulse_time", qualifiers="step=reactant_A;species=sicl4", value="5", unit="min", data_kind="stated")
conv_T = f("s4.p16;s4.p17;s3.p34", "setting", "FTIR SiO2 experiment at 427 °C", quantity="deposition_temperature", value="427", unit="°C", data_kind="stated")
oh_si = f("s4.p16", "observation", "after the conversion a fairly sharp band near 3740 cm-1 appears, the O-H stretch of SiOH* silanols",
          quantity="other", label_as_printed="O-H stretch band", value="3740", unit="cm-1", data_kind="measured", method="ftir", mentions="ref 38")
up_psi = f("s4.p17", "setting", "the silanol surface got progressive SiCl4 exposures at about 1 Torr", quantity="partial_pressure", qualifiers="species=sicl4", value="1", unit="Torr", data_kind="stated")
o_sioh = f("s4.p17", "observation", "the SiOH* band shrinks with SiCl4 exposure, as Eq. (5) predicts", method="ftir")
fig8b_obs = f("s4.p17;fig8b;fig8.cap", "observation", "Fig. 8(b): the loss of integrated SiOH* absorbance against SiCl4 exposure time, with a linear least-squares fit", quantity="signal_intensity", method="ftir")

# ---------------------------------------------------------------- IV. discussion and the Monte Carlo model
c_diff = claim("s5.p1", "SEM and EPMA show that the coating of the membranes is governed by diffusion: the pore ends coat at once, the interior needs longer exposures", "asserted",
               "gas_diffusion", "penetration_depth", "limits")
c_both = claim("s5.p1", "the ZnO infiltration grows with both the exposure time and the pore diameter", "asserted", "pulse_time;feature_width", "penetration_depth", "increases")
mc = f("s5.p1;s2.p25", "model", "the Monte Carlo simulation assumes Knudsen diffusion in the pore, self-limiting adsorption, and a pore diameter that shrinks with the number of cycles")
mfp = f("s5.p2", "derived", "TMA in 1 Torr of N2 at the deposition temperature has a mean free path near 4e-5 m, hundreds of times the pore diameter, so transport is molecular flow",
        quantity="mean_free_path", qualifiers="species=tma", label_as_printed="λ", value="4e-5", unit="m", data_kind="computed_by_authors", method="calculation", inputs=[ptot, T177])
mc_half = f("s5.p2", "model", "the model follows the metal precursor (TMA or DEZ) only: heavier and slower than water, and dosed at a lower pressure than the water step")
claim("s5.p2", "with comparable sticking coefficients in the two half-reactions, the slower diffusion and lower pressure of TMA and DEZ make the A half-reaction rate-limiting", "asserted",
      "partial_pressure", "penetration_depth", "increases")
mc_array = f("s5.p3;s5.p4", "model", "all pores of a membrane are taken as identical cylinders entered from both ends at equal rates, so the membrane is a one-dimensional array of length L/2 whose elements record the local pore diameter")
half_L = f("s5.p4;s5.p3", "setting", "the simulated pore length is half the membrane thickness, 25 µm for a 50 µm membrane", quantity="feature_depth", label_as_printed="l/2", value="25", unit="µm", data_kind="computed_by_authors", mentions="Al2O3;Fig. 9", inputs=[sem_L, sides])   # P107: half the thickness, two entry faces
mc_elems = f("s5.p4;s5.p9", "model", "the array has 20 to 100 elements, each standing for a large number of reactive sites", quantity="other", label_as_printed="array elements", value_min="20", value_max="100", data_kind="model_input")
mc_step = f("s5.p5", "model", "each molecule starts at the pore entrance and moves in steps of ±d_i, the local diameter, the mean Knudsen step in a tube of that diameter (ref 40); exact positions are kept", mentions="ref 40")
mc_equiv = f("s5.p6", "model", "the ±d_i steps in one dimension are equivalent to three-dimensional trajectories with cosine desorption; the direction of each step is random; a molecule passing L/2 is reflected back, standing for molecules from the other end")
c_over = claim("s5.p6", "the model may overestimate the diffusion rate, since molecules leaving the wall at grazing angles can collide in the gas", "limitation", "gas_diffusion", "penetration_depth", "increases")
mc_react = f("s5.p7", "model", "after each step a random number R in (0, 1) is drawn; if R < S, the reactive sticking coefficient, and the element has not yet reacted in this cycle, its diameter shrinks by 2G, G the growth rate")
mc_once = f("s5.p7", "model", "each element reacts at most once per AB cycle, which models self-limiting growth; a trajectory ends when the molecule reacts or leaves the pore; the number of trajectories per cycle matches the exposure and the cycles match the experiment")
mc_time = f("s5.p8;s5.p9", "model", "the time one trajectory represents is t = N/(ΦA), N the molecules per trajectory and ΦA the molecules entering the pore per second")
mc_N = f("s5.p9", "model", "N = αγ/x: α the pore surface area, γ the areal density of reactive sites, x the number of elements; when a trajectory reacts, every site of its element is coated at once")
sim_al_d = f("s5.p12;fig9.cap", "setting", "simulated Al2O3 pore: d = 65 nm", quantity="feature_width", label_as_printed="d", value="65", unit="nm", data_kind="model_input", mentions="Al2O3;Fig. 9")
sim_al_L = f("s5.p12;fig9.cap", "setting", "simulated Al2O3 pore: L = 50 µm", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="model_input", mentions="Al2O3;Fig. 9")
rough = f("s5.p9", "model", "the pore area over L/2 is α = Rπd(L/2) with a roughness factor R = 1.5 measured for the AA membranes", quantity="other", label_as_printed="surface roughness factor R", value="1.5", data_kind="model_input")
mc_gamma = f("s5.p9", "model", "the site density γ follows from the film density and the ALD growth rate")
n_mol = f("s5.p9", "derived", "for Al2O3 ALD in a pore with d = 65 nm, L = 50 µm and 50 array elements, one trajectory stands for N = 7.0 × 10^5 molecules",
          quantity="other", label_as_printed="N", value="7.0e5", data_kind="computed_by_authors", method="calculation", inputs=[sim_al_d, sim_al_L, rough], mentions="x = 50")
mc_flux = f("s5.p10", "model", "the flux is Φ = p/(2πmkT)^1/2 and the pore cross section A = πd²/4")
phiA = f("s5.p10", "derived", "for TMA at 0.15 Torr and 177 °C entering a 65 nm pore, ΦA = 9.7 × 10^8 molecules per second",
         quantity="other", label_as_printed="ΦA", value="9.7e8", unit="s^-1", data_kind="computed_by_authors", method="calculation", inputs=[p_tma, T177, sim_al_d])
traj_t = f("s5.p10", "derived", "so one trajectory represents 0.00072 s, and a 1 s exposure at the TMA pressure of 0.15 Torr takes 1400 trajectories",
  quantity="other", label_as_printed="time per trajectory", value="7.2e-4", unit="s", data_kind="computed_by_authors", method="calculation", inputs=[n_mol, phiA, p_tma, SIMAL["1"]] if False else [n_mol, phiA, p_tma], mentions="1.4 × 10^3")
traj_n = f("s5.p10", "derived", "a 1 s exposure at 0.15 Torr TMA takes 1400 trajectories", quantity="other", label_as_printed="trajectories per second of exposure", value="1400", data_kind="computed_by_authors", method="calculation", inputs=[traj_t, p_tma])
# simulated Al2O3 (Fig. 9)
sim_al_S = f("s5.p12;fig9.cap", "setting", "the Al2O3 simulations (Fig. 9) use a reactive sticking coefficient S = 10^-3", quantity="initial_sticking_coefficient", qualifiers="species=tma", label_as_printed="S", value="1e-3", data_kind="model_input")
sim_al_N = f("s5.p12;fig9.cap", "setting", "the Al2O3 simulations run 100 cycles in a d = 65 nm, L = 50 µm pore with the TMA pressure and exposure times of Fig. 3", quantity="cycle_number", value="100", data_kind="model_input")
SIMAL = {}
for t in ("1", "3", "10"):
    SIMAL[t] = f("s5.p12;fig9.cap;fig9a", "setting", f"simulated Al2O3 coating, TMA exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value=t, unit="s", data_kind="model_input", mentions=f"{t} s")
fig9a_obs = f("fig9a;fig9.cap;s5.p12;s5.p11", "model", "Fig. 9(a): simulated relative Al2O3 coverage against distance into the pore for 1, 3 and 10 s exposures", quantity="normalized_thickness", qualifiers="reference=assumed_saturation", method="simulation")
sim1_flat = f("s5.p12;fig9a", "model", "1 s exposures give a uniform Al2O3 coverage over the first ~11 µm of the pore, then the relative thickness falls with depth",
              quantity="penetration_depth", qualifiers="level=front_start", value="11", unit="µm", data_kind="computed_by_authors", method="simulation", mentions="1 s")
sim1_25 = f("s5.p12;s5.p14;fig9a", "model", "1 s exposures: at 25 µm the relative Al2O3 coverage is only about 0.05 to 0.1",
            quantity="normalized_thickness", qualifiers="reference=assumed_saturation", value_min="0.05", value_max="0.1", data_kind="computed_by_authors", method="simulation", mentions="1 s;25 µm")
sim3_25 = f("s5.p13;fig9a", "model", "3 s exposures: the relative Al2O3 thickness is nearly uniform along the pore, falling only slightly to about 0.95 at 25 µm",
            quantity="normalized_thickness", qualifiers="reference=assumed_saturation", value="0.95", data_kind="computed_by_authors", method="simulation", mentions="3 s;25 µm")
sim10 = f("s5.p13;fig9a", "model", "exposures of 10 s or more give a completely uniform relative Al2O3 coverage", quantity="other", label_as_printed="exposure time for a uniform coverage", value="10", censor=">", unit="s", data_kind="computed_by_authors", method="simulation")
fig9b_obs = f("fig9b;fig9.cap;s5.p13", "model", "Fig. 9(b): simulated normalized integrated Al2O3 coverage against exposure time", quantity="surface_coverage", method="simulation")
sim_int = f("s5.p13;fig9b", "model", "the simulated normalized integrated coverage is about 1.0 for exposures of 3 s or more", quantity="surface_coverage", value="1.0", data_kind="computed_by_authors", method="simulation", mentions="3 s")
claim("s5.p14", "the Monte Carlo results of Fig. 9 match the SEM of Fig. 3: at 1 s the middle of the membrane is uncoated in both", "asserted", supports=[o_1s, sim1_25])
th_25 = f("s5.p14", "derived", "a relative coverage of 0.05 to 0.1 at 25 µm after 1 s exposures means an Al2O3 thickness of about 6 to 13 Å there",
          quantity="film_thickness", value_min="6", value_max="13", unit="Å", data_kind="computed_by_authors", method="calculation", inputs=[sim1_25, al_flat], mentions="25 µm;1 s")
claim("s5.p14", "6 to 13 Å of Al2O3 is probably too little to protect the pore walls during the phosphoric acid etch", "hedged", "film_thickness", "feature_width", "decreases", supports=[th_25])
# simulated ZnO (Fig. 10, 11, 12)
sim_zn_S = f("s5.p15;fig10.cap;s5.x2;fig12.cap", "setting", "the ZnO simulations use a reactive sticking coefficient S = 7 × 10^-3", quantity="initial_sticking_coefficient", qualifiers="species=dez", label_as_printed="S", value="7e-3", data_kind="model_input")
sim_zn_N = f("s5.p15;fig10.cap", "setting", "the ZnO exposure simulations run 64 cycles in a d = 65 nm, L = 50 µm pore, like the experiments of Figs. 4 and 5", quantity="cycle_number", value="64", data_kind="model_input")
sim_zn_d = f("s5.p15;fig10.cap", "setting", "simulated ZnO pore: d = 65 nm", quantity="feature_width", label_as_printed="d", value="65", unit="nm", data_kind="model_input", mentions="ZnO;Fig. 10")
sim_zn_L = f("s5.p15;fig10.cap", "setting", "simulated ZnO pore: L = 50 µm", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="model_input", mentions="ZnO;Fig. 10")
SIMZN = {}
for t in ("1", "3", "10", "30"):
    SIMZN[t] = f("s5.p15;fig10.cap;fig10a", "setting", f"simulated ZnO coating, DEZ exposure {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value=t, unit="s", data_kind="model_input", mentions=f"{t} s")
fig10a_obs = f("fig10a;fig10.cap;s5.p15", "model", "Fig. 10(a): simulated relative ZnO coverage against distance for 1, 3, 10 and 30 s exposures", quantity="normalized_thickness", qualifiers="reference=assumed_saturation", method="simulation")
o_match = f("s5.p15;fig10a;fig5a", "model", "the simulated ZnO profiles of Fig. 10(a) closely match the EPMA profiles of Fig. 5(a)", method="simulation")
sim30 = f("s5.p15;fig10a", "model", "the simulation predicts conformal coating of the pores at about 30 s exposures", quantity="other", label_as_printed="exposure time for a conformal coating", value="30", unit="s", data_kind="computed_by_authors", method="simulation")
o_even30 = f("s5.p15;fig5a", "observation", "the open diamonds of Fig. 5(a) show the pores coated very evenly with 30 s exposures", method="epma", mentions="30 s")
claim("s5.p15", "the slight drop of the measured coverage at 20 to 25 µm may come from non-ideal pores: narrower sections or blocked pores", "hedged", "feature_narrowing", "normalized_thickness", "decreases", supports=[PTS[("5a", "30")]])
fig10b_obs = f("fig10b;fig10.cap;s5.x1", "model", "Fig. 10(b): simulated normalized integrated ZnO coverage against exposure time, with a fit y = k t^1/2", quantity="surface_coverage", method="simulation")
k_sim = f("s5.x1;fig10b", "derived", "the fit to the simulated integrated coverages gives k = 0.28, against 0.23 for the measured ones", quantity="other", label_as_printed="k", value="0.28", unit="s^-1/2",
          data_kind="computed_by_authors", method="calculation", mentions="Fig. 10b")
claim("s5.x1", "the simulated integrated coverages agree very well with the EPMA data of Fig. 5(b)", "asserted", supports=[k_sim, k_exp])
sim_dia_t = f("s5.p16;fig11.cap", "setting", "the diameter simulations (Fig. 11) use 5 s exposures in 50 µm pores", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value="5", unit="s", data_kind="model_input")
sim_dia_L = f("s5.p16;fig11.cap", "setting", "simulated diameter series: L = 50 µm", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="model_input", mentions="Fig. 11")
SIMD = {}
for d in ("19", "47", "65"):
    SIMD[d] = f("s5.p16;fig11.cap;fig11a", "setting", f"simulated diameter series: d = {d} nm (the caption prints 46 nm for the middle diameter)", quantity="feature_width", label_as_printed="d", value=d, unit="nm", data_kind="model_input", mentions=f"{d} nm")
fig11a_obs = f("fig11a;fig11.cap;s5.p16", "model", "Fig. 11(a): simulated relative ZnO coverage against distance for the three pore diameters at 5 s", quantity="normalized_thickness", qualifiers="reference=assumed_saturation", method="simulation")
fig11b_obs = f("fig11b;fig11.cap;s5.p16", "model", "Fig. 11(b): simulated normalized integrated ZnO coverage against pore diameter with a linear fit", quantity="surface_coverage", method="simulation")
slope_sim = f("s5.p16;s5.p17;fig11b", "derived", "the linear fit of simulated integrated coverage against diameter has a slope of 0.25 per nm, the same as the measured one",
              quantity="other", label_as_printed="slope", value="0.25", unit="nm-1", data_kind="computed_by_authors", method="calculation", mentions="Fig. 11b")
claim("s5.p17", "the diameter simulations of Fig. 11 agree very well with the experiments of Fig. 6, both fits having the same slope", "asserted", supports=[slope_sim, slope_exp])
claim("s5.p18", "whether the coating is diffusion- or reaction-limited is set by the reactive sticking coefficient together with the pore aspect ratio, and each regime leaves a different profile", "asserted",
      "initial_sticking_coefficient;aspect_ratio", "gas_diffusion", "limits")
eq7_m = f("eq7;s5.p18;s5.p19", "model", "Eq. (7): a molecule A that entered the pore diffuses with probability H to an empty site (B) and reacts there with probability S (C)")
f("s5.p19", "definition", "S, the reactive sticking coefficient, is the probability that a surface collision ends in reaction; it follows from reactive uptake measurements", quantity="initial_sticking_coefficient", term="S")
f("s5.p20;s5.p21", "definition", "H, the hopping coefficient, is the probability that one hop reaches an empty site, from a one-dimensional random walk (ref 41): the most probable number of hops to a site j hops away is j², so H = 1/j²", mentions="ref 41")
mc_H = f("s5.p21", "model", "with L/4 (half the way to the array midpoint) as the typical distance to an empty site and d as the hop length, j = L/(4d) and H = 16 (d/L)²")
claim("s5.p22", "in the diffusion-limited regime, S much larger than H, sites fill in order from the entrance with a sharp boundary between coated and uncoated pore, and the result does not depend on S", "asserted",
      "gas_diffusion", "penetration_depth", "limits")
claim("s5.p22", "in the reaction-limited regime, S much smaller than H, sites fill at random, the profiles are flat and the molecules equilibrate through the membrane before reacting", "asserted",
      "initial_sticking_coefficient", "normalized_thickness", "causes")
H_a = f("s5.x2;fig12.cap", "derived", "Fig. 12(a), diffusion-limited: d = 65 nm, L = 50 µm, S = 7 × 10^-3 give H = 2.7 × 10^-5, so S is much larger than H",
        quantity="other", label_as_printed="hopping coefficient H", value="2.7e-5", data_kind="computed_by_authors", method="calculation", mentions="Fig. 12a")
H_b = f("s5.x2;fig12.cap;s5.p24", "derived", "Fig. 12(b), reaction-limited: d = 65 nm, L = 0.5 µm, S = 10^-4 give H = 0.27, so S is much smaller than H",
        quantity="other", label_as_printed="hopping coefficient H", value="0.27", data_kind="computed_by_authors", method="calculation", mentions="Fig. 12b")
sim12b_L = f("s5.x2;fig12.cap", "setting", "Fig. 12(b) uses a 0.5 µm thin membrane", quantity="body_thickness", label_as_printed="L", value="0.5", unit="µm", data_kind="model_input", mentions="Fig. 12b")
sim12b_S = f("s5.x2;fig12.cap", "setting", "Fig. 12(b) uses S = 10^-4", quantity="initial_sticking_coefficient", qualifiers="species=dez", label_as_printed="S", value="1e-4", data_kind="model_input", mentions="Fig. 12b")
sim12_d = f("s5.x2;fig12.cap", "setting", "both Fig. 12 simulations use d = 65 nm", quantity="feature_width", label_as_printed="d", value="65", unit="nm", data_kind="model_input", mentions="Fig. 12")
sim12a_L = f("s5.x2;fig12.cap", "setting", "Fig. 12(a) uses L = 50 µm", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="model_input", mentions="Fig. 12a")
mc_12 = f("s5.p24;fig12.cap", "model", "the two Fig. 12 cases are ZnO ALD at the experimental DEZ pressure in the low-coverage limit; at long exposures both reach an integrated coverage of 1", links=p_dez)
c_12a = claim("s5.x2;fig12a", "the diffusion-limited simulation (Fig. 12a) predicts a square-root time dependence of the integrated coverage", "asserted", "gas_diffusion", "surface_coverage", "limits", supports=[H_a])
c_12b = claim("s5.x2;fig12b", "the reaction-limited simulation (Fig. 12b) predicts a linear time dependence", "asserted", "initial_sticking_coefficient", "surface_coverage", "limits", supports=[H_b])
fig12a_obs = f("fig12a;fig12.cap", "model", "Fig. 12(a): simulated normalized integrated coverage against exposure time, diffusion-limited", quantity="surface_coverage", method="simulation")
fig12b_obs = f("fig12b;fig12.cap", "model", "Fig. 12(b): simulated normalized integrated coverage against exposure time, reaction-limited", quantity="surface_coverage", method="simulation")
H_ftir = f("s5.p25;s5.p26", "derived", "the FTIR membrane, d = 47 nm and L = 50 µm, has H = 1.4 × 10^-5", quantity="other", label_as_printed="hopping coefficient H", value="1.4e-5", data_kind="computed_by_authors", method="calculation", inputs=[ftir_d, ftir_L])
claim("s5.p25;fig8a", "with S about 10^-3 for Al2O3 ALD (ref 24) and H = 1.4 × 10^-5, S is much larger than H, and Fig. 8(a) indeed follows a square-root time law as Fig. 12(a) predicts", "asserted",
      "gas_diffusion", "surface_coverage", "limits", supports=[s_al, H_ftir, c_12a])
claim("s5.p26;fig8b", "with S about 10^-8 for SiO2 ALD (ref 39) and the same H, S is much smaller than H, and Fig. 8(b) follows a linear time law as Fig. 12(b) predicts (the parsed text prints t^4 for the exponent 1)", "asserted",
      "initial_sticking_coefficient", "surface_coverage", "limits", supports=[s_si, H_ftir, c_12b])
claim("s5.p27;s5.p28", "when S is much larger than H the simulation does not depend on S, and Figs. 9 to 11 agree with Figs. 3, 5 and 6 without any adjustable parameter", "asserted",
      "initial_sticking_coefficient", "penetration_depth", "no_effect")
# predicted minimum exposure times
mc_min = f("s5.p29", "model", "the simulations give the minimum exposure times for conformal deposition in high-aspect-ratio pores, valid when S is much larger than H, for any ALD chemistry; H depends only on the aspect ratio")
eq8_m = f("eq8;s5.p30;s5.p31", "model", "Eq. (8): in the diffusion-limited regime the integrated coverage Θ* grows as k t^1/2; k is set by the reactant pressure, its molecular mass and the site density")
eq9_m = f("eq9;s5.p32", "model", "Eq. (9): k equals 2.1e3 times P^1/2 m^-1/4 Γ^-1/2 over L/d (k in s^-1/2; P in Torr, m in amu, Γ in units of 1e15 cm-2)")
eq10_m = f("eq10;s5.p33", "model", "Eq. (10): setting Θ* = 1 gives the minimum exposure time for a conformal coating, t = 2.3 × 10^-7 P^-1 m^1/2 Γ (L/d)²")
gam = f("s5.p34", "setting", "Γ = 0.84 (in 10^15 cm-2, i.e. 8.4 nm-2) for ZnO ALD in the Eq. (10) example", quantity="saturation_density", label_as_printed="Γ", value="8.4", unit="nm-2", data_kind="model_input")
m_dez = f("s5.p34", "setting", "m = 123 amu for DEZ in the Eq. (10) example", quantity="other", label_as_printed="m", value="123", unit="amu", data_kind="model_input")
t_min = f("s5.p34", "derived", "with P 5 Torr, L/d 5000, m 123 and Γ 0.84, Eq. (10) gives 11 s as the shortest exposure that coats the pore conformally",
          quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value="11", unit="s", data_kind="computed_by_authors", method="calculation", inputs=[gam, m_dez, qs_pdez], mentions="L/d = 5000;P = 5")
f("s5.p34", "definition", "the minimum exposure time of Eq. (10) is the exposure step length at which the integrated coverage of the pore reaches 1", quantity="pulse_time",
  term="Minimum Exposure Time", definition_note="the exposure step length at which the integrated coverage reaches 1 (Eq. 10), a model estimate")
claim("s5.p34", "Eq. (10) gives a ready estimate of the exposure needed for conformal coating of porous samples of very high aspect ratio", "asserted", "aspect_ratio", "pulse_time", "increases")
p13 = f("s5.x3;fig13.cap", "setting", "the Fig. 13 curves take the DEZ pressure as 0.01, 0.1, 1 or 10 Torr, 0.01 to 10 Torr", quantity="partial_pressure", qualifiers="species=dez", value_min="0.01", value_max="10", unit="Torr", data_kind="model_input")
fig13_obs = f("s5.x3;fig13;fig13.cap", "model", "Fig. 13: the Eq. (10) minimum exposure time plotted over the aspect ratio for ZnO ALD, one curve per DEZ pressure", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", method="simulation", links=p13)
c_13 = claim("s5.x3;s5.p35", "pores of aspect ratio 10^3 to 10^4 reach conformal coverage within 1 to 10 s at 1 to 10 Torr of DEZ, conditions readily met in ZnO ALD", "asserted",
      "partial_pressure", "pulse_time", "decreases", quantity="pulse_time", qualifiers="step=reactant_A;species=dez", value_min="1", value_max="10", unit="s", data_kind="computed_by_authors", method="calculation")
claim("s5.p35", "the exposures that very high aspect ratios demand are therefore not excessive, and Fig. 13 carries over to other chemistries once m and Γ are replaced", "asserted")
claim("s6.p2", "the Monte Carlo predictions of the exposures needed for conformal coverage are general and should serve for porous substrates at large", "asserted")

# ================================================================== the tree: paper -> recipe -> depositions -> entities -> measurements
PAPER, RECIPE = K, f"{K}:recipe"
N(PAPER, "paper", "Elam, Routkevitch, Mardilovich and George 2003, Chem. Mater.: Al2O3 and ZnO ALD in the nanopores of anodic alumina membranes, "
  "EPMA infiltration profiles, a Monte Carlo pore model and FTIR of the diffusion- and reaction-limited regimes", "", evidence="abs.g1", label_as_printed="10.1021/cm0303080")
N(RECIPE, "activity", "shared recipe: a viscous-flow N2-carried ALD reactor at 1 Torr and 177 °C (Al2O3 from TMA/H2O, ZnO from DEZ/H2O) on free-standing anodic alumina membranes, "
  "SEM, EPMA and in situ FTIR", PAPER, evidence="s3.p2;s3.p1", kind="recipe", how="stated", label_as_printed="recipe")
MAT = {"al2o3": f("s2.p23;abs.g3", "setting", "film material of the Al2O3 runs", quantity="material", value_text="al2o3", data_kind="stated", mentions="Al2O3"),
       "zno": f("s2.p23;abs.g3", "setting", "film material of the ZnO runs", quantity="material", value_text="zno", data_kind="stated", mentions="ZnO"),
       "sio2": f("s2.p25;abs.g5", "setting", "film material of the FTIR SiO2 experiment", quantity="material", value_text="sio2", data_kind="stated", mentions="SiO2")}
RA = {"al2o3": f("s3.p23", "setting", "reactant A of Al2O3 ALD: trimethylaluminium", quantity="reactant_A", value_text="tma", data_kind="stated", mentions="TMA"),
      "zno": f("s3.p24", "setting", "reactant A of ZnO ALD: diethylzinc", quantity="reactant_A", value_text="dez", data_kind="stated", mentions="DEZ"),
      "sio2": f("s3.p34", "setting", "reactant A of SiO2 ALD: silicon tetrachloride", quantity="reactant_A", value_text="sicl4", data_kind="stated", mentions="SiCl4")}
RB = {"al2o3": f("s3.p23", "setting", "reactant B of Al2O3 ALD: water", quantity="reactant_B", value_text="h2o", data_kind="stated", mentions="H2O"),
      "zno": f("s3.p24", "setting", "reactant B of ZnO ALD: water", quantity="reactant_B", value_text="h2o", data_kind="stated", mentions="H2O;ZnO"),
      "sio2": f("s3.p34", "setting", "reactant B of SiO2 ALD: water", quantity="reactant_B", value_text="h2o", data_kind="stated", mentions="H2O;SiO2")}
STRUCT = f("abs.g1;s2.p2;s3.p1", "setting", "test structure: free-standing anodic alumina membranes with cylindrical nanopores", quantity="structure", value_text="anodic_alumina_membrane", data_kind="stated", mentions="AA")
SUBSTR = f("s3.p1;abs.g1", "setting", "the growth surface is the anodic alumina of the pore walls", quantity="substrate", value_text="al2o3", data_kind="stated")
FX = {r["fact_id"]: r for r in C.facts()}
PARENT = {}


def put(parent, *ids):
    for i in ids:
        if i not in FX:                                                         # a fact added after the snapshot
            FX[i] = next(x for x in C.facts() if x["fact_id"] == i)
        assert i not in PARENT, i
        PARENT[i] = parent


def meas(ent, method, label=None, mode=None, order=None):
    """A measurement activity of an entity (one per method), created on first use."""
    fid = f"{K}:meas:{ent.split(':', 1)[1]}:{method}"
    if fid not in FX:
        kw = dict(kind="measurement", how="stated", label_as_printed=label or method.replace("_", " "))
        if order is not None:
            kw["order"] = order
        N(fid, "activity", f"{method.replace('_', ' ')} on {FX[ent]['label_as_printed']}", ent, **kw)
        FX[fid] = C.facts()[-1]
        MODES[fid.split(":", 1)[1]] = mode or {"epma": "ex_situ", "ftir": "in_situ", "sem": "ex_situ"}.get(method, "ex_situ")
    return fid


MODES = {}
# the recipe's shared settings
put(RECIPE, reactor, rtype, T177, carrier, flow, ptot, STRUCT, SUBSTR, sides, mem_dia, perp, slow_p, pur_tma, pur_dez, def_t, rng_t, rng_pg, p_tma, p_dez, p_h2o,
    qs_mode, qs_base, qs_pdez, qs_tdez, qs_purge, qs_ph2o, qs_th2o, qs_purge2, sicl4_pur, anod_ctl, liftoff, al_pur, eq1_m, eq2_m, eq3_m, eq4_m, eq5_m, eq6_m)
# the membranes as made: an input entity with a piece per anodization recipe (Table 1) and per membrane used
N(f"{K}:ent:membranes", "entity", "the anodic alumina membranes as made: 1 cm discs with cylindrical pores open on both faces, pore diameter and thickness set by the anodization (Table 1)",
  RECIPE, evidence="s3.p1;tab1.cap", how="stated", label_as_printed="AA membranes as made")
FX[f"{K}:ent:membranes"] = C.facts()[-1]
MEM = {}
for d, lab, ev in (("19", "d 19 nm membranes (H2SO4, 20 V)", "tab1.r1c4"), ("46", "d 46 nm membranes (oxalic, 50 V)", "tab1.r2c4"), ("65", "d 65 nm membranes (oxalic, 70 V)", "tab1.r3c4")):
    MEM[d] = f"{K}:ent:mem_d{d}"
    N(MEM[d], "entity", f"the Table 1 membranes with {d} nm pores, as anodized", f"{K}:ent:membranes", evidence=ev, how="stated", label_as_printed=lab)
    FX[MEM[d]] = C.facts()[-1]
    put(MEM[d], *TAB[d].values())
N(f"{K}:ent:mem_fig1", "entity", "the uncoated membrane imaged in Fig. 1: 40 nm pores, about 120 µm thick", f"{K}:ent:membranes", evidence="fig1.cap", how="stated", label_as_printed="Fig. 1 membrane (d 40 nm)")
FX[f"{K}:ent:mem_fig1"] = C.facts()[-1]
put(meas(f"{K}:ent:mem_fig1", "sem", order="0"), fig1_d, fig1_L, f"{K}:fig1a#1", f"{K}:fig1b#1")
N(f"{K}:ent:mem_ftir", "entity", "the membrane of the FTIR experiments: 47 nm pores, 50 µm thick", f"{K}:ent:membranes", evidence="s3.p33", how="stated", label_as_printed="FTIR membrane (d 47 nm)")
FX[f"{K}:ent:mem_ftir"] = C.facts()[-1]
put(f"{K}:ent:mem_ftir", ftir_d, ftir_L)
N(f"{K}:ent:mem_ar5000", "entity", "the ultrahigh-aspect-ratio membrane: 19 nm pores, 92 µm thick, L/d about 5000", f"{K}:ent:membranes", evidence="s4.p11", how="stated", label_as_printed="AR 5000 membrane (d 19 nm, L 92 µm)")
FX[f"{K}:ent:mem_ar5000"] = C.facts()[-1]
put(f"{K}:ent:mem_ar5000", ar_d, ar_L, ar5000)
put(f"{K}:ent:membranes", ar_abs)
# depositions and specimens
SPEC = {}


def deposition(did, statement, label, ev, settings, mat, inputs=None):
    N(did, "activity", statement, RECIPE, evidence=ev, kind="deposition", how="stated", label_as_printed=label, inputs=";".join(filter(None, [inputs, f"{K}:ent:membranes"])))
    FX[did] = C.facts()[-1]
    put(did, *settings)
    ent = did.replace(":dep:", ":ent:")
    N(ent, "entity", f"the coated membrane of the {label} run", did, evidence=ev, how="stated", label_as_printed=label)
    FX[ent] = C.facts()[-1]
    return ent


# Al2O3 SEM series: one deposition per timing sequence; material and reactants per deposition (the recipe serves two chemistries)
for t, pg in SEQ:
    s = SEM[t]
    did = f"{K}:dep:al2o3_{t}s"
    sets = [s["tA"], s["pA"], s["tB"], s["pB"]]
    if t == "1":
        sets += [MAT["al2o3"], RA["al2o3"], RB["al2o3"], sem_N, sem_dL, sem_L]
    SPEC[("al", t)] = deposition(did, f"Al2O3 ALD, 100 cycles, sequence {t}-{pg}-{t}-{pg}, on a d 65 nm, L 50 µm membrane", f"Al2O3, {t} s exposures", "s4.p1", sets, "al2o3", inputs=MEM["65"])
for h in (MAT["al2o3"], RA["al2o3"], RB["al2o3"], sem_N, sem_dL, sem_L):          # the shared settings of the series, copied to the other depositions
    C.spread(h, [f"{K}:dep:al2o3_{t}s" for t, _ in SEQ], {f"{K}:dep:al2o3_{t}s": f"Al2O3, {t} s exposures" for t, _ in SEQ})
# ZnO exposure series
for t, pg in SEQ:
    s = ZNO[t]
    did = f"{K}:dep:zno_{t}s"
    SPEC[("zn", t)] = deposition(did, f"ZnO ALD, 64 cycles, sequence {t}-{pg}-{t}-{pg}, on a d 65 nm, L 50 µm membrane", f"ZnO, {t} s exposures", "s4.p4", [s["tA"], s["pA"], s["tB"], s["pB"]] + ([MAT["zno"], RA["zno"], RB["zno"], zno_N, zno_dL, zno_L] if t == "1" else []), "zno", inputs=MEM["65"])
for h in (MAT["zno"], RA["zno"], RB["zno"], zno_N, zno_dL, zno_L):
    C.spread(h, [f"{K}:dep:zno_{t}s" for t, _ in SEQ], {f"{K}:dep:zno_{t}s": f"ZnO, {t} s exposures" for t, _ in SEQ})
# ZnO diameter series
for d, n in (("19", "19"), ("46", "45"), ("65", "64")):
    did = f"{K}:dep:znod_{d}"
    SPEC[("zd", d)] = deposition(did, f"ZnO ALD, {n} cycles, 5-10-5-10, on a d {d} nm, L 50 µm membrane", f"ZnO, d {d} nm, {n} cycles", "s4.p10", [DIA[d]["d"], DIA[d]["N"]] + ([dia_tA, dia_pA, dia_tB, dia_pB, dia_L] if d == "19" else []), "zno", inputs=MEM[d])
for h in (dia_tA, dia_pA, dia_tB, dia_pB, dia_L):
    C.spread(h, [f"{K}:dep:znod_{d}" for d in ("19", "46", "65")], {f"{K}:dep:znod_{d}": f"ZnO, d {d} nm" for d in ("19", "46", "65")})
# the AR 5000 run (quasi-static)
ar_d2 = f("s4.p12;s4.p11", "setting", "AR 5000 run: the membrane's pore diameter, 19 nm", quantity="feature_width", label_as_printed="d", value="19", unit="nm", data_kind="stated", mentions="AR 5000 run")
ar_L2 = f("s4.p12;s4.p11", "setting", "AR 5000 run: the membrane's thickness, 92 µm", quantity="body_thickness", label_as_printed="L", value="92", unit="µm", data_kind="stated", mentions="AR 5000 run")
SPEC["ar"] = deposition(f"{K}:dep:zno_ar5000", "ZnO ALD, 19 cycles, quasi-static 120 s doses at 5 Torr, on the d 19 nm, L 92 µm membrane", "ZnO, AR 5000 membrane", "s4.p11;s4.p12",
                        [ar_N, ar_qs, ar_d2, ar_L2], "zno", inputs=f"{K}:ent:mem_ar5000")
# FTIR experiments: the Al2O3 layer on the FTIR membrane, then its SiO2 conversion (a later deposition on the same entity)
ftir_d2 = f("s4.p14;s3.p33", "setting", "FTIR runs: the membrane's pore diameter, 47 nm", quantity="feature_width", label_as_printed="d", value="47", unit="nm", data_kind="stated", mentions="FTIR run")
ftir_L2 = f("s4.p14;s3.p33", "setting", "FTIR runs: the membrane's thickness, 50 µm", quantity="body_thickness", label_as_printed="L", value="50", unit="µm", data_kind="stated", mentions="FTIR run")
SPEC["ftir_al"] = deposition(f"{K}:dep:ftir_al2o3", "Al2O3 ALD on the FTIR membrane in the high-vacuum chamber: 4 saturating TMA/H2O cycles, then small TMA uptake exposures followed by FTIR",
                             "FTIR Al2O3 layer", "s4.p14;s4.p15", [ini_N, ini_p, ini_t, ini_T, up_p, ftir_d2, ftir_L2], "al2o3", inputs=f"{K}:ent:mem_ftir")
SPEC["ftir_si"] = deposition(f"{K}:dep:ftir_sio2", "SiO2 ALD on the FTIR membrane: 2 SiCl4/H2O cycles at 427 °C converting the Al2O3 surface, then SiCl4 uptake exposures followed by FTIR",
                             "FTIR SiO2 layer", "s4.p16;s4.p17", [conv_N, conv_p, conv_t, conv_T, up_psi, MAT["sio2"], RA["sio2"], RB["sio2"]], "sio2", inputs=f"{K}:ent:mem_ftir")
C.spread(ftir_d2, [f"{K}:dep:ftir_al2o3", f"{K}:dep:ftir_sio2"], {f"{K}:dep:ftir_sio2": "FTIR SiO2 layer"})
C.spread(ftir_L2, [f"{K}:dep:ftir_al2o3", f"{K}:dep:ftir_sio2"], {f"{K}:dep:ftir_sio2": "FTIR SiO2 layer"})
# copies of the material and reactants for the runs that share the ZnO or Al2O3 chemistry outside their series
for h, deps in ((MAT["zno"], [f"{K}:dep:znod_19", f"{K}:dep:zno_ar5000"]), (RA["zno"], [f"{K}:dep:znod_19", f"{K}:dep:zno_ar5000"]), (RB["zno"], [f"{K}:dep:znod_19", f"{K}:dep:zno_ar5000"]),
                (MAT["al2o3"], [f"{K}:dep:ftir_al2o3"]), (RA["al2o3"], [f"{K}:dep:ftir_al2o3"]), (RB["al2o3"], [f"{K}:dep:ftir_al2o3"])):
    src = FX[h]
    for dep in deps:
        n_ = C._count[src["evidence"].split(";")[0]] = C._count.get(src["evidence"].split(";")[0], 0) + 1
        row = dict(src); row.update(fact_id=f"{K}:{src['evidence'].split(';')[0]}#{n_}", statement=f"{FX[dep]['label_as_printed']}: {src['statement']}", mentions=";".join(filter(None, [src["mentions"], FX[dep]["label_as_printed"]])))
        C.facts().append(row); FX[row["fact_id"]] = row; PARENT[row["fact_id"]] = dep
for d in ("46", "65"):                                                          # the diameter series' other two runs share the d 19 run's chemistry copies
    for h in (MAT["zno"], RA["zno"], RB["zno"]):
        src = FX[h]
        n_ = C._count[src["evidence"].split(";")[0]] = C._count.get(src["evidence"].split(";")[0], 0) + 1
        row = dict(src); row.update(fact_id=f"{K}:{src['evidence'].split(';')[0]}#{n_}", statement=f"ZnO, d {d} nm: {src['statement']}", mentions=";".join(filter(None, [src["mentions"], f"ZnO, d {d} nm"])))
        C.facts().append(row); FX[row["fact_id"]] = row; PARENT[row["fact_id"]] = f"{K}:dep:znod_{d}"
# observations under the specimens' measurement activities
put(meas(SPEC[("al", "1")], "sem"), o_1s)
put(meas(SPEC[("al", "3")], "sem"), o_3s)
meas(SPEC[("al", "30")], "sem")
for t, _ in SEQ:
    put(meas(SPEC[("zn", t)], "epma"), PTS[("5a", t)])
put(meas(SPEC[("zn", "1")], "epma"), scan_step)
put(meas(SPEC[("zn", "30")], "epma"), o_map30, unif30, o_even30, sat_t)
for d in ("19", "46", "65"):
    put(meas(SPEC[("zd", d)], "epma"), PTS[("6a", d)])
meas(SPEC[("zd", "19")], "epma")
put(meas(SPEC["ar"], "epma"), PTS[("7b", "")], fig7a_obs, o_nodip, o_slope7)
put(meas(SPEC["ftir_al"], "ftir"), ftir_sat, oh_al, o_aloh, fig8a_obs, spec_T)
put(meas(SPEC["ftir_si"], "ftir"), oh_si, o_sioh, fig8b_obs)
# derived values of the specimens
put(SPEC[("al", "1")], al_dfin)
put(SPEC[("zn", "1")], zn_dfin)
# the paper's method activities (settings and statements about the instruments, not about one sample)
N(f"{K}:method:sem", "activity", "SEM: the shared sample preparation and instrument", PAPER, kind="measurement", how="stated", label_as_printed="SEM (method)")
N(f"{K}:method:epma", "activity", "EPMA: the shared sample preparation and instrument", PAPER, kind="measurement", how="stated", label_as_printed="EPMA (method)")
N(f"{K}:method:ftir", "activity", "FTIR: the shared high-vacuum apparatus and mounting", PAPER, kind="measurement", how="stated", label_as_printed="FTIR (method)")
MODES.update({"method:sem": "ex_situ", "method:epma": "ex_situ", "method:ftir": "in_situ"})
put(f"{K}:method:sem", sem_prep, sem_etch, etch_cit, sem_inst)
put(f"{K}:method:epma", meth_plan, epma_who, epma_prep, epma_inst, epma_cur, epma_res)
put(f"{K}:method:ftir", ftir_plan, ftir_plan2, ftir_inst, ftir_mount, ftir_heat, ftir_runs)
FX[ftir_runs]["links"] = f"{ini_T};{conv_T}"
# the Monte Carlo model: a simulation activity with one run per simulated case
N(f"{K}:sim", "activity", "Monte Carlo simulation of ALD in a nanopore (elam_monte_carlo): one-dimensional Knudsen random walk, reaction probability S, pore narrowing by 2G",
  PAPER, evidence="s5.p1;s5.p2", kind="simulation", how="stated", label_as_printed="Monte Carlo model")
FX[f"{K}:sim"] = C.facts()[-1]
put(f"{K}:sim", mc, mfp, mc_half, mc_array, mc_elems, mc_step, mc_equiv, mc_react, mc_once, mc_time, mc_N, rough, mc_gamma, n_mol, mc_flux, phiA, traj_t, eq7_m, mc_H, mc_12,
    mc_min, eq8_m, eq9_m, eq10_m, mc_plan, traj_n)
RUNS = {}


def simrun(rid, statement, label, ev, settings, outputs, profile=""):
    """One simulated case: its own simulation activity under the model (the inputs as settings), its model-run entity under it (the outputs)."""
    act = rid.replace(":simrun:", ":simact:")
    N(act, "activity", statement, f"{K}:sim", evidence=ev, kind="simulation", how="stated", label_as_printed=label)
    FX[act] = C.facts()[-1]
    N(rid, "entity", f"model run of {label}", act, evidence=ev, how="inferred", label_as_printed=label)
    FX[rid] = C.facts()[-1]
    put(act, *settings)
    out = list(outputs)
    if profile:
        out.append(f(ev.split(";")[0] + ";" + ev.split(";")[1] if ";" in ev else ev, "model", profile, method="simulation", mentions=label))
    put(rid, *out)
    return rid


for t in ("1", "3", "10"):
    RUNS[("al", t)] = simrun(f"{K}:simrun:al2o3_{t}s", f"simulated Al2O3 ALD, 100 cycles, TMA {t} s at 0.15 Torr, d 65 nm, L 50 µm, S 1e-3", f"sim Al2O3, {t} s", "fig9a;s5.p12",
                             [SIMAL[t]] + ([sim_al_S, sim_al_N, sim_al_d, sim_al_L] if t == "1" else []), [], profile=f"Fig. 9(a), {t} s: the simulated relative Al2O3 coverage against distance into the pore for this exposure")
ACT = lambda r: r.replace(":simrun:", ":simact:")
for h in (sim_al_S, sim_al_N, sim_al_d, sim_al_L):
    C.spread(h, [ACT(f"{K}:simrun:al2o3_{t}s") for t in ("1", "3", "10")], {ACT(f"{K}:simrun:al2o3_{t}s"): f"sim Al2O3, {t} s" for t in ("1", "3", "10")})
L50 = [ACT(f"{K}:simrun:al2o3_{t}s") for t in ("1", "3", "10")] + [ACT(f"{K}:simrun:zno_{t}s") for t in ("1", "3", "10", "30")] + [ACT(f"{K}:simrun:znod_{d}") for d in ("19", "47", "65")] + [ACT(f"{K}:simrun:fig12a")]
PARENT[half_L] = L50[0]
put(RUNS[("al", "1")], sim1_flat, sim1_25, th_25)
put(RUNS[("al", "3")], sim3_25)
put(RUNS[("al", "10")], sim10)
for t in ("1", "3", "10", "30"):
    RUNS[("zn", t)] = simrun(f"{K}:simrun:zno_{t}s", f"simulated ZnO ALD, 64 cycles, DEZ {t} s at 0.068 Torr, d 65 nm, L 50 µm, S 7e-3", f"sim ZnO, {t} s", "fig10a;s5.p15",
                             [SIMZN[t]] + ([sim_zn_S, sim_zn_N, sim_zn_d, sim_zn_L] if t == "1" else []), [], profile=f"Fig. 10(a), {t} s: the simulated relative ZnO coverage against distance into the pore for this exposure")
for h in (sim_zn_N, sim_zn_d, sim_zn_L):
    C.spread(h, [ACT(f"{K}:simrun:zno_{t}s") for t in ("1", "3", "10", "30")], {ACT(f"{K}:simrun:zno_{t}s"): f"sim ZnO, {t} s" for t in ("1", "3", "10", "30")})
C.spread(sim_zn_S, [ACT(f"{K}:simrun:zno_{t}s") for t in ("1", "3", "10", "30")] + [ACT(f"{K}:simrun:fig12a")], {**{ACT(f"{K}:simrun:zno_{t}s"): f"sim ZnO, {t} s" for t in ("1", "3", "10", "30")}, ACT(f"{K}:simrun:fig12a"): "sim Fig. 12a"})

put(RUNS[("zn", "30")], sim30)
for d in ("19", "47", "65"):
    RUNS[("zd", d)] = simrun(f"{K}:simrun:znod_{d}", f"simulated ZnO ALD, DEZ 5 s, d {d} nm, L 50 µm", f"sim ZnO, d {d} nm", "fig11a;s5.p16", [SIMD[d]] + ([sim_dia_t, sim_dia_L] if d == "19" else []), [],
                             profile=f"Fig. 11(a), d = {d} nm: the simulated relative ZnO coverage against distance for this pore diameter at 5 s")
for h in (sim_dia_t, sim_dia_L):
    C.spread(h, [ACT(f"{K}:simrun:znod_{d}") for d in ("19", "47", "65")], {ACT(f"{K}:simrun:znod_{d}"): f"sim ZnO, d {d} nm" for d in ("19", "47", "65")})

RUNS["12a"] = simrun(f"{K}:simrun:fig12a", "simulated ZnO ALD in the diffusion-limited regime: d 65 nm, L 50 µm, S 7e-3, H 2.7e-5, DEZ 0.068 Torr", "sim Fig. 12a (diffusion-limited)", "s5.x2;fig12.cap",
                     [sim12_d, sim12a_L], [H_a, fig12a_obs])
RUNS["12b"] = simrun(f"{K}:simrun:fig12b", "simulated ZnO ALD in the reaction-limited regime: d 65 nm, L 0.5 µm, S 1e-4, H 0.27, DEZ 0.068 Torr", "sim Fig. 12b (reaction-limited)", "s5.x2;fig12.cap",
                     [sim12b_L, sim12b_S], [H_b, fig12b_obs])
C.spread(sim12_d, [ACT(f"{K}:simrun:fig12a"), ACT(f"{K}:simrun:fig12b")], {ACT(f"{K}:simrun:fig12b"): "sim Fig. 12b"})
C.spread(half_L, L50, {r: FX[r]["label_as_printed"] for r in L50})
C.spread(mc_12, [ACT(f"{K}:simrun:fig12a"), ACT(f"{K}:simrun:fig12b")], {ACT(f"{K}:simrun:fig12b"): "sim Fig. 12b"}) if False else None
RUNS["eq10"] = simrun(f"{K}:simrun:eq10", "the Eq. (10) estimate of the minimum exposure time: P 5 Torr, L/d 5000, m 123 amu, Γ 0.84 × 10^15 cm-2", "sim Eq. (10), L/d 5000", "s5.p34",
                      [gam, m_dez, p13], [t_min, fig13_obs])
put(f"{K}:ent:mem_ftir", H_ftir)
# the FTIR membrane and the AR 5000 membrane as inputs of their depositions are named in `inputs` (deposition()); the FTIR layer's conversion is a second deposition on the same membrane
# the set-level records: observations and fits that span a series sit under its comparison set
for fid_, gid in ((o_map_ends, f"{K}:grp:zno_t"), (o_map_prog, f"{K}:grp:zno_t"), (o_prof, f"{K}:grp:zno_t"), (k_exp, f"{K}:grp:zno_t"), (fig4_obs, f"{K}:grp:zno_t"), (fig5b_obs, f"{K}:grp:zno_t"),
                  (o_ends, f"{K}:grp:al2o3_t"), (fig3_obs, f"{K}:grp:al2o3_t"), (o_wide, f"{K}:grp:al2o3_t"), (o_dia, f"{K}:grp:zno_d"), (slope_exp, f"{K}:grp:zno_d"), (fig6b_obs, f"{K}:grp:zno_d"),
                  (o_match, f"{K}:grp:sim_zno_t"), (k_sim, f"{K}:grp:sim_zno_t"), (fig10a_obs, f"{K}:grp:sim_zno_t"), (fig10b_obs, f"{K}:grp:sim_zno_t"),
                  (fig9a_obs, f"{K}:grp:sim_al2o3"), (fig9b_obs, f"{K}:grp:sim_al2o3"), (sim_int, f"{K}:grp:sim_al2o3"),
                  (fig11a_obs, f"{K}:grp:sim_zno_d"), (fig11b_obs, f"{K}:grp:sim_zno_d"), (slope_sim, f"{K}:grp:sim_zno_d")):
    PARENT[fid_] = gid
# ---------------------------------------------------------------- stances, variables, relations (lists.STANCES, P54)
CLAIMS[c_sem][4].extend([sem_dL, sem_L])
CLAIMS[c_epma][4].extend([ar5000])
fig1a_obs = next(x["fact_id"] for x in C.facts() if x["fact_id"].startswith(f"{K}:fig1a#"))
fig1b_obs = next(x["fact_id"] for x in C.facts() if x["fact_id"].startswith(f"{K}:fig1b#"))
DEFAULT_SUPPORT = {c_aa: [STRUCT, fig1b_obs], c_ald: [eq1_m, eq2_m], c_mc: [o_match, k_sim], c_regime: [H_a, H_b], c_half: [fig8a_obs], c_lin: [fig8b_obs],
                   pore_dens: [STRUCT], c_perp: [fig1a_obs, fig1b_obs], d_range: [TAB["19"]["d"], TAB["65"]["d"]], L_range: [TAB["19"]["L"]], c_sensor: [STRUCT], c_pvd: [ar_max],
                   scope_d: [TAB["19"]["d"], TAB["65"]["d"]], scope_L: [TAB["19"]["L"], ar_L], c_diff: [o_1s, o_3s, o_map_prog], c_both: [o_prof, o_dia], c_over: [mc_equiv], c_13: [fig13_obs, p13]}
for h, sup in DEFAULT_SUPPORT.items():
    if not CLAIMS[h][4]:
        CLAIMS[h][4].extend(sup)
BY_TEXT = {"the digital growth gives precise thickness control": [eq1_m, eq2_m], "because Al2O3 and SiO2 ALD have different reactive sticking": [s_al, s_si],
           "the highest-aspect-ratio membranes need very large exposures": [qs_mode, qs_tdez], "the shallow mounting angle brings pore cross sections": [sem_prep],
           "SEM shows the ALD film on the pore walls directly": [sem_inst, fig3_obs], "a quantified thickness profile is hard to get from SEM": [sem_inst, epma_who],
           "AA membranes transmit infrared light": [ftir_inst], "with comparable sticking coefficients in the two half-reactions": [p_h2o],
           "whether the coating is diffusion- or reaction-limited": [H_a, H_b], "in the diffusion-limited regime, S much larger than H": [H_a], "in the reaction-limited regime, S much smaller than H": [H_b],
           "when S is much larger than H the simulation does not depend on S": [k_sim, k_exp, slope_sim, slope_exp], "Eq. (10) gives a ready estimate": [t_min, eq10_m],
           "the exposures that very high aspect ratios demand": [fig13_obs, c_13], "the Monte Carlo predictions of the exposures needed": [t_min, eq10_m],
           "the top and bottom faces see the reactants directly": [o_ends], "a nearly uniform Zn map means": [o_map30], "the missing mid-membrane dip": [o_nodip]}
for h, (stance, cause, effect, rel, sup) in CLAIMS.items():
    if not sup:
        st = FX_STATEMENT = next(x["statement"] for x in C.facts() if x["fact_id"] == h)
        for key, val in BY_TEXT.items():
            if st.startswith(key):
                sup.extend(val); break
for h, (stance, cause, effect, rel, sup) in CLAIMS.items():
    r = next(x for x in C.facts() if x["fact_id"] == h)
    r["stance"], r["cause"], r["effect"], r["relation"] = stance, cause, effect, rel

# claims under the paper, with their supports as links
for h, (stance, cause, effect, rel, sup) in CLAIMS.items():
    if h not in PARENT:
        PARENT[h] = PAPER
    FX[h]["links"] = ";".join(sup)
# definitions under the paper; cited facts under their references
for r in C.facts():
    if "#" in r["fact_id"] and r["fact_id"] not in PARENT:
        if r["type"] == "definition":
            PARENT[r["fact_id"]] = PAPER
        elif r["type"] == "cited":
            import re as _re
            m = _re.search(r"ref ?(\d+)", r["mentions"])
            PARENT[r["fact_id"]] = f"{K}:refs:{m.group(1)}" if m else PAPER
left = [r["fact_id"] for r in C.facts() if "#" in r["fact_id"] and r["fact_id"] not in PARENT and not r["parent"]]
assert not left, left
for r in sorted({p for p in PARENT.values() if ":refs:" in p}, key=lambda x: int(x.rsplit(":", 1)[1])):
    kids = [r_ for r_ in C.facts() if PARENT.get(r_["fact_id"]) == r]
    N(r, "cited", f"cited work, reference {r.rsplit(':', 1)[1]} of the paper", PAPER, evidence=";".join(dict.fromkeys(x["evidence"].split(";")[0] for x in kids)), label_as_printed=f"ref. {r.rsplit(':', 1)[1]}")
for r in C.facts():
    if r["fact_id"] in PARENT:
        r["parent"] = PARENT[r["fact_id"]]
# comparison sets (the authors' series): purpose fact first, then the members
GROUPS = [
    (f"{K}:grp:al2o3_t", "series", "pulse_time", "Al2O3 SEM series: four exposure times, 100 cycles, d 65 nm", "s4.p1", c_sem, [SPEC[("al", t)] for t, _ in SEQ]),
    (f"{K}:grp:zno_t", "series", "pulse_time", "ZnO EPMA series: four exposure times, 64 cycles, d 65 nm", "s4.p4", c_epma, [SPEC[("zn", t)] for t, _ in SEQ]),
    (f"{K}:grp:zno_d", "series", "feature_width;cycle_number", "ZnO diameter series: d 19, 46, 65 nm at 5 s exposures", "s4.p10", c_both, [SPEC[("zd", d)] for d in ("19", "46", "65")]),
    (f"{K}:grp:sim_al2o3", "series", "pulse_time", "simulated Al2O3 exposure series (Fig. 9)", "s5.p12", c_mc, [RUNS[("al", t)] for t in ("1", "3", "10")]),
    (f"{K}:grp:sim_zno_t", "series", "pulse_time", "simulated ZnO exposure series (Fig. 10)", "s5.p15", c_mc, [RUNS[("zn", t)] for t in ("1", "3", "10", "30")]),
    (f"{K}:grp:sim_zno_d", "series", "feature_width", "simulated ZnO diameter series (Fig. 11)", "s5.p16", c_mc, [RUNS[("zd", d)] for d in ("19", "47", "65")]),
    (f"{K}:grp:sim_regime", "series", "initial_sticking_coefficient;body_thickness", "the two kinetic regimes of Fig. 12", "s5.x2", c_regime, [RUNS["12a"], RUNS["12b"]]),
    (f"{K}:grp:ftir", "series", "initial_sticking_coefficient", "FTIR uptake on one membrane: Al2O3 (S ~1e-3) against SiO2 (S ~1e-8)", "s4.p13", c_half, [SPEC["ftir_al"], SPEC["ftir_si"]]),
]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0].split(" (")[0], qualifiers="how=stated", links=";".join([pur] + members))
    FX[gid] = C.facts()[-1]
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
# what each ± or range is: the paper states no uncertainty; the ±10 % uniformity is itself the nonuniformity value
# caveats (P45)
CAV = [
    ("s3.p32;s4.p5", "EPMA averages several hundred pores per point (3-5 µm resolution, ~1 µm steps), so a profile is an ensemble average, not one pore's coating.",
     [PTS[k] for k in PTS] + [unif30], "", ""),
    ("s4.p8;fig5.cap", "The Fig. 5(a) profiles are normalized to the single highest Zn concentration of the whole set, not profile by profile.", [PTS[("5a", t)] for t in ("1", "3", "10", "30")], "", ""),
    ("s4.p1;s4.p4", "The pore diameter shrinks during the run (65 to 39 nm after 100 Al2O3 or 64 ZnO cycles), so d is the starting diameter of each series.",
     [sem_dL, zno_dL], "", ""),
    ("s4.p9", "The square-root fit of the integrated coverage uses the 0-10 s points only; beyond 10 s the coverage saturates.", [k_exp, c_sqrt], "", ""),
    ("s4.p12", "The slope of the AR 5000 profile may be an artefact of the sample orientation in the microprobe, a pore-diameter gradient or incompletely opened pores.", [PTS[("7b", "")]], "", ""),
    ("s5.p2", "The simulations follow the metal precursor only (TMA or DEZ); water, lighter and at 2-3 times the pressure, is taken as never rate-limiting.", list(RUNS.values()), "", ""),
    ("s5.p6", "Reflection at the array midpoint stands in for molecules from the other face; the model may overestimate diffusion because grazing desorption can collide in the gas.", list(RUNS.values()), "", ""),
    ("s5.p15;s5.p12", "The sticking coefficients of the simulations (1e-3 for Al2O3, 7e-3 for ZnO) are inputs; in the diffusion-limited regime the results do not depend on them.", [sim_al_S, sim_zn_S], "", ""),
    ("s5.p16;fig11.cap", "The simulated middle diameter is 47 nm in the text and 46 nm in the caption and the experiment.", [SIMD["47"]], "", ""),
    ("s4.p11", "The paper's aspect ratio L/d uses the full membrane thickness although reactant enters from both faces; the diffusion length is L/2.", [ar5000, ar_abs, ar_max, half_L], "", ""),
    ("s5.p26", "The parsed text prints the SiO2 time exponent as t^4; the abstract and conclusions give t^1, a linear dependence.", [c_lin], "", ""),
    ("s4.p14;s4.p16", "The Al2O3 and SiO2 FTIR experiments were run one after the other on the same 47 nm membrane, the SiO2 surface made by converting the Al2O3 layer.", [SPEC["ftir_al"], SPEC["ftir_si"]], "", ""),
    ("s3.p29", "The phosphoric acid etch widens uncoated pores on purpose, so pore width in the SEM images marks the absence of ALD alumina rather than the as-made diameter.", [o_1s, o_3s, o_wide], "", ""),
    ("s5.p34", "The 11 s minimum exposure time is an Eq. (10) estimate for P = 5 Torr and L/d = 5000 with Γ = 0.84 and m = 123; it assumes the diffusion-limited regime.", [t_min], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_sem.split(":", 1)[1]: [o_3s.split(":", 1)[1], o_1s.split(":", 1)[1]], c_1s.split(":", 1)[1]: [o_1s.split(":", 1)[1], sim1_25.split(":", 1)[1]],
            c_half.split(":", 1)[1]: [s_al.split(":", 1)[1], H_ftir.split(":", 1)[1]], c_lin.split(":", 1)[1]: [s_si.split(":", 1)[1], H_ftir.split(":", 1)[1]],
            c_over.split(":", 1)[1]: [mfp.split(":", 1)[1]], c_regime.split(":", 1)[1]: [H_a.split(":", 1)[1], H_b.split(":", 1)[1]]})
C.specimen_classes(K, "porous_composite")                                      # P53: ZnO or Al2O3 inside a porous membrane
C.structure_classes(K)                                                         # P78
C.rekey_structure_dimensions(K)                                                # P78
# P131: a claim is a triple or it is not a claim; every claim without a full triple re-typed by the one rule (facts.retype)
BG = 'background, motivation, prior art or scope'
RETYPE = {
    'abs.g1#1': ('removed', BG),
    's2.p2#2': ('removed', BG),
    's2.p2#6': ('removed', BG),
    's2.p2#1': ('cited', 'ela03'),
    's2.p2#3': ('cited', 'ela03'),
    's2.p2#4': ('cited', 'ela03'),
    's2.p2#5': ('cited', 'ela03', {'censor': '<'}),
    's2.p23#1': ('setting', 'ela03:recipe'),
    's2.p23#2': ('setting', 'ela03:recipe'),
    's3.p28#2': ('setting', 'ela03:method:sem'),
    's3.p30#1': ('setting', 'ela03:method:sem'),
    's3.p33#4': ('setting', 'ela03:method:ftir'),
    's3.p30#2': ('caveat', ['s4.p1#22']),
    's5.p14#1': ('model', 'ela03:cmp:sim_al2o3'),
    's5.x1#2': ('model', 'ela03:cmp:sim_zno_t'),
    's5.p17#2': ('model', 'ela03:cmp:sim_zno_d'),
    's6.p2#1': ('model', 'ela03:sim'),
    's5.p35#1': ('triple', 'aspect_ratio', 'increases', 'exposure'),
}
C.retype(K, RETYPE)
write(K, PID)
