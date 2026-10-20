#!/usr/bin/env python3
"""Stage 2 facts for yli18 (10.1063_1.5028178, Ylilammi, Ylivaara, Puurunen 2018, J. Appl. Phys.: a diffusion-reaction model of ALD
growth in lateral high-aspect-ratio channels with dynamic Langmuir adsorption and channel narrowing, its analytic approximation, the
comparison with the Gordon model, and the fit to Al2O3 (TMA/H2O) and TiO2 (TiCl4/H2O) profiles in PillarHall prototype 3 chips).
Text, the nomenclature, Table I, the equations and the captions; every curve is an imported record (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1063_1.5028178.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "yli18", "10.1063_1.5028178"
A = "s3.p5"                                                                     # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h", "heading")
NK("s0.p1;s1.p1;s1.p2;s1.p3;s3.p1;s3.p2;s3.p3;s3.p4;s3.p6;s4.p1;abs.g5", "front matter, authors, affiliations, dates, contact")
NK("s2.p1;s2.p2;s2.p3;s2.p4;s2.p5;s2.p6", "the publisher's related-article box")
NK("s5.p5;s8.p10;s8.p20", "a section heading set as a paragraph")
NK("s5.p7;s8.p3;s8.p4;s8.p22;s8.p23;s9.p2;s10.p2", "a caption printed again as a body paragraph; the knowledge is under the figure's or table's caption element")
NK("s5.p9;s5.p11;s5.p12;s6.p5;s6.p9;s7.p2;s7.p6;s7.p10;s7.p11;s7.p12;s7.p19;s8.p12;s8.p16;s8.p18", "a connective sentence introducing an equation")
NK("s11.p1", "acknowledgements")
NK(";".join(f"s11.p{i}" for i in range(2, 18)), "reference list")
NK("fig1.cap;fig1", "a schematic of the LHAR channel (x, W, L, x_p drawn), no value")
NK(";".join(f"tabu1.r{i}c{j}" for i in range(0, 30) for j in range(0, 4)), "nomenclature cells: the symbols are definition facts citing the rows that name a quantity")

# ---------------------------------------------------------------- the paper's claims (abstract, introduction, conclusions)
c_model = claim(f"abs.g1;abs.g2;{A};s6.p2", "a one-dimensional diffusion model with dynamic Langmuir adsorption and channel narrowing describes the propagation of ALD growth in a narrow channel", "asserted",
                "gas_diffusion", "penetration_depth", "causes")
c_fit = claim(f"abs.g3;{A};s10.p3", "an analytic approximation of the diffusion equation makes the model fast enough to fit measured thickness profiles, and the fit yields the adsorption equilibrium constant and the sticking coefficient",
              "asserted", "normalized_thickness", "initial_sticking_coefficient", "causes")
c_agree = claim(f"abs.g4;{A};s10.p1", "the simulations predict the measured profiles of the Al2O3 and TiO2 processes quite well", "asserted", "gas_diffusion", "film_thickness", "causes")
c_lhar = claim("s5.p3", "once a channel is long enough, its length has no effect on the penetration depth", "asserted", "feature_depth", "penetration_depth", "no_effect")
lhar_H = f("s5.p3", "setting", "the LHAR gap, typically 500 nm high, is a trench turned sideways inside a pillar-supported polysilicon membrane", quantity="feature_width", label_as_printed="H", value="500", unit="nm",
           data_kind="stated", mentions="Gao, 2015")
lhar_L = f("s5.p3", "setting", "the fabricated channel lengths spanned 1–5000 µm (1 µm to 5 mm)", quantity="feature_depth", label_as_printed="L", value_min="1", value_max="5000", unit="µm", data_kind="stated")
lhar_ar = f("s5.p3", "derived", "for the typical gap height the length over height gives aspect ratios from 2 to 10 000", quantity="aspect_ratio", value_min="2", value_max="10000", data_kind="computed_by_authors",
            method="calculation", inputs=[lhar_H, lhar_L])
f("s5.p1;s5.p2", "cited", "experimental conformality data are rare in the ALD literature; four groups are named as the exceptions", data_kind="cited", method="cited",
  mentions="Dendooven (2010);Rose and Bartha (2009);Schwille (2017);Yanguas-Gil (2017)")
f("s5.p3", "cited", "earlier LHAR prototypes served the conformality analysis of Al2O3, TiO2 and Ir-based films", data_kind="cited", method="cited", mentions="Gao, 2015;Mattinen, 2016;Puurunen and Gao, 2016")
c_goal = claim("s5.p4", "fitting the model to a measured thickness profile extracts kinetic growth information; the TMA/water and the chloride TiO2 processes verify it", "asserted")

# ---------------------------------------------------------------- Sec. II: gas diffusion in narrow channels (the model's transport part)
pB_def = f("s5.p6;eq1", "definition", "p_B is the partial pressure of the carrier gas B, nitrogen, in the collision rate of Eq. (1)", quantity="partial_pressure", qualifiers="gas=n2", term="pB|p_B")
hs = f("s5.p6;eq1;s5.p8", "model", "Eq. (1): the hard-sphere collision rate of A molecules in an A + B mixture from the diameters, molar masses and partial pressures", mentions="Levine, 1978;z_A")
vA = f("s5.p8;eq2", "model", "Eq. (2): the mean speed of A molecules, (8RT / π M_A)^1/2", mentions="v_A")
DA = f("s5.p9;eq3", "model", "Eq. (3): the gas-phase diffusion constant D_A = 3π v_A² / (16 z_A)", mentions="D_A")
dkn = f("s5.p10;eq4", "model", "Eq. (4): the Knudsen diffusion constant D_Kn = h (8RT / 9π M_A)^1/2", mentions="Poodt, 2017;D_Kn")
hyd = f("s5.p11;eq5;s5.p12", "model", "Eq. (5): the hydraulic diameter of a rectangular channel, h = 2 / (1/H + 1/W)", mentions="h")
bos = f("s5.p13;eq6", "model", "Eq. (6): the effective diffusion constant follows the Bosanquet relation, 1/D_eff = 1/D_A + 1/D_Kn, bulk diffusion and wall collisions in series", mentions="Poodt, 2017;D_eff")
dvis = f("s5.p14;eq7", "model", "Eq. (7): the molecular diameter from the gas viscosity, for common gases", mentions="Levine, 1978;η")
eta_w = f("s5.p15", "cited", "water vapor at 100 °C has a viscosity of 12.55 µPa s", quantity="other", label_as_printed="η", value="12.55", unit="µPa s", data_kind="cited", method="cited", mentions="Weast, 1977")
d_h2o = f("s5.p15", "derived", "the water molecule's diameter from its viscosity is 418 pm", quantity="molecule_diameter", qualifiers="species=h2o", label_as_printed="d_A", value="418", unit="pm", data_kind="computed_by_authors",
          method="calculation", inputs=[eta_w])
eta_n = f("s5.p15", "cited", "the viscosity of nitrogen at 11 °C is 17.07 µPa s", quantity="other", label_as_printed="η", value="17.07", unit="µPa s", data_kind="cited", method="cited", mentions="Weast, 1977")
d_n2 = f("s5.p15", "derived", "the nitrogen molecule's diameter is 374 pm", quantity="molecule_diameter", qualifiers="species=n2", label_as_printed="d_B", value="374", unit="pm", data_kind="computed_by_authors",
         method="calculation", inputs=[eta_n])
c_rough = claim("s5.p15", "a rough molecular diameter is enough, since Knudsen diffusion limits the transport in narrow channels", "asserted", "gas_diffusion", "penetration_depth", "limits")
dden = f("s5.p15;eq8", "model", "Eq. (8): for ALD reactants without a measured viscosity the diameter follows from the density of the condensed phase", mentions="ρ")
tma_mono = f("s5.p16", "cited", "TMA is dimeric at low temperature but above 215 °C more than 96 % is monomeric, so the monomer's diffusion constant is used", data_kind="cited", method="cited", mentions="Almenningen, 1971")
d_tma = f("s5.p16", "setting", "the molecular diameter of TMA used in the model is 591 pm", quantity="molecule_diameter", qualifiers="species=tma", label_as_printed="d_TMA", value="591", unit="pm", data_kind="stated")
d_ticl4 = f("s5.p16", "setting", "the molecular diameter of TiCl4 used in the model is 703.9 pm", quantity="molecule_diameter", qualifiers="species=ticl4", label_as_printed="d_TiCl4", value="703.9", unit="pm", data_kind="stated")
qdef = f("s5.p17;eq9;s5.p18", "model", "Eq. (9): the saturation adsorption density q follows from the film density, the molar mass of a formula unit, the saturation growth per cycle and the metal atoms per formula unit and per reactant molecule",
         mentions="q;b_film;b_A;M")
b_al = f("s5.p18", "setting", "for TMA and Al2O3, b_film = 2 metal atoms per formula unit and b_A = 1 per reactant molecule", quantity="other", label_as_printed="b_film", value="2", data_kind="stated", mentions="b_A = 1")
b_ti = f("s5.p18", "setting", "for TiCl4 and TiO2, b_film = 1 and b_A = 1", quantity="other", label_as_printed="b_film", value="1", data_kind="stated", mentions="b_A = 1")
c_water = claim("s5.p19", "water molecules, lighter and smaller than the metal reactants, diffuse much faster, so the metal precursor's diffusion is taken as the growth-limiting factor", "asserted",
                "gas_diffusion", "penetration_depth", "limits")

# ---------------------------------------------------------------- Sec. III: the growth model
coord = f("s6.p1;fig1.cap", "model", "the gas enters at x = 0 and propagates along the channel by diffusion; the channel is much wider than high, so the concentration is uniform across y and z", mentions="Fig. 1")
teq = f("s6.p1", "derived", "the time constant for diffusion across the channel height is about 10 ns for a 1 µm channel, far below the millisecond scale of ALD", quantity="other", label_as_printed="H²/D_eff",
        value="10", unit="ns", data_kind="computed_by_authors", method="calculation", mentions="1 µm;1 cm²/s")
deff_typ = f("s6.p1", "model", "the effective diffusion coefficient is typically about 1 cm²/s", quantity="other", label_as_printed="D_eff", value="1", unit="cm2/s", data_kind="stated")
eq10_m = f("s6.p2;eq10;s6.p3", "model", "Eq. (10): the one-dimensional diffusion equation for the partial pressure with a wall-adsorption sink term g 4RT / (h N_0); solvable numerically but impractically heavy over thousands of pulses")
lang = f("s6.p4;eq11;s6.p5;eq12;s6.p6", "model", "Eqs. (11)-(12): Langmuir chemisorption, adsorption rate (1 − θ) c N_0 p_A / (2π M_A RT)^1/2 with the lumped sticking coefficient c, desorption rate q θ P_d",
         mentions="Levine, 1978;P_d")
c_lump = claim("s6.p6", "c is a lumped sticking coefficient that combines every sequential and parallel surface process", "asserted", "initial_sticking_coefficient", "surface_chemistry", "causes")
eqK = f("s6.p7;eq13;eq14", "model", "Eqs. (13)-(14): the adsorption equilibrium constant K = cQ / (q P_d), with Q = N_0 / (2π M_A RT)^1/2 the collision rate at unit pressure", mentions="Levine, 1978;Q")
eqg = f("s6.p8;eq15;s6.p9;eq16", "model", "Eqs. (15)-(16): the net adsorption rate g = f_ads − f_des and dθ/dt = g/q")
c_rev = claim("s6.p10", "during a pulse the net adsorption rate is positive, so reversibility does not matter to the model; the TiO2 fit is better with a non-zero desorption probability", "hedged",
              "desorption", "normalized_thickness", "causes")
cav_lang = f("s6.p10", "model", "the Langmuir model stands in for a surface reaction mechanism that may be much more complicated")

# ---------------------------------------------------------------- Sec. IV: the approximate solution
appr0 = f("s7.p1;eq17;eq18;s7.p3", "model", "Eqs. (17)-(18): at the channel start the surfaces saturate at once and the flow is steady, so the pressure falls linearly from p_A0 to zero at x_s, the front position")
xs_def = f("s7.p3;s7.p4;eq19", "definition", "x_s is the zero crossing of the linear pressure part, how far the reactant front has come; it grows as the diffusion length, x_s = (Dt)^1/2",
           term="x_s|xs", mentions="Yanguas-Gil, 2017")
D_def = f("s7.p5;eq20", "definition", "D, the apparent longitudinal diffusion coefficient, sets the speed of the gas front; Eq. (20) gives the diffusive gas flow in the linear region", term="D")
eq21 = f("s7.p6;eq21;s7.p7;eq22", "model", "Eqs. (21)-(22): the molecules adsorbed up to x equal the integrated gas flow, neglecting the small unused amount in the gas phase", mentions="n_A")
eq23 = f("s7.p8;eq23", "model", "Eq. (23): the apparent longitudinal diffusion coefficient D from p_A0, H, D_eff, q, T and K")
tail = f("s7.p9;eq24;s7.p10;eq25;eq26;s7.p12;eq27;s7.p13;eq28", "model", "Eqs. (24)-(28): beyond x_t the pressure has an exponential tail; x_t is chosen so the diffusion equation holds there with θ about 0, and is never negative",
         mentions="x_t;p_t")
o_fig2 = f("s7.p14;fig2.cap;fig2", "model", "Fig. 2: the approximate pressure model against the numerical solution of the diffusion equation at four pulse lengths; the fit looks good", method="simulation", mentions="Fig. 2")
theq = f("s7.p15;eq29", "model", "Eq. (29): the equilibrium coverage θ_eq = K p_A / (1 + K p_A) when the pressure changes slowly")
tau_m = f("s7.p16;eq30;s7.p17", "model", "Eq. (30): the coverage relaxes exponentially with time constant τ = qK / (2cQ) at half coverage; the equilibrium model holds only when τ is much shorter than the pulse, which real ALD often violates",
          mentions="τ")
eq31 = f("s7.p18;eq31;s7.p19;eq32", "model", "Eqs. (31)-(32): the Langmuir coverage equation dθ/dt = cQp_A/q − (cQp_A/q + P_d) θ and its analytic solution")
rk4 = f("s7.p20", "setting", "a fourth-order Runge-Kutta scheme, self-starting and stable, solves Eq. (31); integrating Eq. (32) numerically would take too long", method="simulation", mentions="Arfken, 1970")
rk_n = f("s7.p20", "setting", "a fit solves Eq. (31) more than 10 000 times; usually 100 time points of about 1 ms suffice, more when convergence fails", quantity="other", label_as_printed="time points",
         value="100", data_kind="stated", mentions="10 000 times;1 ms")
o_fig3 = f("s7.p21;fig3.cap;fig3", "model", "Figs. 2 and 3: the approximate model and the numerical solution give practically identical pressures and coverages", method="simulation", mentions="Fig. 3")

# ---------------------------------------------------------------- Sec. V: thickness profile and penetration depth
pd_err = f("s8.p1;eq33;s8.p2", "model", "Eq. (33): the error of a penetration depth read from a thickness profile is the thickness error over the slope, smallest where the slope is largest, at half thickness")
pd_def = f("s8.p5;eq34;fig1.cap", "definition", "the half-thickness penetration depth x_p is where the film thickness is half its value at the channel start", quantity="penetration_depth", qualifiers="level=50%",
           term="x_p|xp|half-thickness penetration depth", definition_note="half the thickness at the channel start, the channel start as reference")
narrow = f("s8.p6;eq35;s8.p7", "model", "Eq. (35): after each pulse the model resets a single channel height to H(0) − 2N gpc, both walls growing; the tail therefore thins a little too steeply",
           mentions="H(N)")
sum_m = f("s8.p8;eq36;eq37", "model", "Eqs. (36)-(37): the coverages of all N cycles add up and the thickness is s(x) = θ(x) gpc_sat")
o_fig4 = f("fig4.cap;fig4;s8.p9", "model", "Fig. 4: thickness profiles after 1000 cycles for four original channel heights; the lowest channel plugs up at its entrance", method="simulation", mentions="Fig. 4")
plug = claim("fig4.cap", "a 0.2 µm channel is completely plugged at its entrance after 1000 cycles of the reference process", "asserted", "feature_width", "penetration_depth", "increases")

# ---------------------------------------------------------------- Sec. VI: the Gordon model
g_front = f("s8.p11;eq38", "model", "the Gordon model: the gas enters the wide channel as a front of constant concentration with no diffusion along x; Eq. (38) counts the molecules adsorbed per dx on both walls",
            mentions="Gordon, 2003")
g_v = f("s8.p12;eq39;s8.p13;eq40", "model", "Eqs. (39)-(40): the saturated front moves at v = F / (2qW)")
g_F = f("s8.p14;eq41;s8.p15", "model", "Eq. (41): Gordon's molecular-flow conductance of a channel of length x and cross-section WH", mentions="Gordon (2003)")
g_int = f("s8.p15;eq42;s8.p16;eq43", "model", "Eqs. (42)-(43): the front equation separates and integrates to x + 3x²(1/H + 1/W)/16 = C H t")
g_C = f("s8.p17;eq44;s8.p18;eq45", "model", "Eqs. (44)-(45): with C = p_A0 N_0 / (2q (2π M_A RT)^1/2) the Gordon penetration depth at pulse length t_p is H ((1 + 3Ct_p/4)^1/2 − 1) / 0.375 for W much larger than H",
           mentions="C;t_p")
c_gar = claim("s8.p17", "in the Gordon model the aspect ratio reached, x/H, does not depend on the channel height", "asserted", "feature_width", "coated_aspect_ratio", "no_effect")
o_fig5 = f("s8.p19;fig5.cap;fig5", "model", "Fig. 5: the penetration depth in one pulse by the numerical solution, the analytic approximation and the Gordon model against pulse length", method="simulation", mentions="Fig. 5")
c_gordon = claim("s8.p19;fig5.cap", "the Gordon model gives a good penetration depth here, slightly faster since it uses Knudsen diffusion alone, but no thickness profile and no growth kinetics", "asserted",
                 "gas_diffusion", "penetration_depth", "causes")

# ---------------------------------------------------------------- Sec. VII: experimental
MAT_AL = f("s8.p21;abs.g4", "setting", "the first film material is Al2O3", quantity="material", value_text="al2o3", data_kind="stated")
MAT_TI = f("s8.p21;abs.g4", "setting", "the second film material is TiO2", quantity="material", value_text="tio2", data_kind="stated")
reactor = f("s8.p21", "setting", "the reactor, a four-line Picosun R-150", quantity="reactor", value_text="Picosun R-150", data_kind="stated")
RA_AL = f("s8.p21;fig6.cap", "setting", "Al2O3 reactant A: trimethylaluminum", quantity="reactant_A", value_text="tma", data_kind="stated", mentions="Gao (2015)")
RB_AL = f("s8.p21;fig6.cap", "setting", "Al2O3 reactant B: water", quantity="reactant_B", value_text="h2o", data_kind="stated")
T_AL = f("s8.p21", "setting", "Al2O3 was grown at 300 °C", quantity="deposition_temperature", value="300", unit="°C", data_kind="stated")
RA_TI = f("s8.p21;fig7.cap", "setting", "TiO2 reactant A: titanium tetrachloride", quantity="reactant_A", value_text="ticl4", data_kind="stated")
RB_TI = f("s8.p21;fig7.cap", "setting", "TiO2 reactant B: water", quantity="reactant_B", value_text="h2o", data_kind="stated", mentions="TiO2")
T_TI = f("s8.p21", "setting", "TiO2 was grown at 110 °C", quantity="deposition_temperature", value="110", unit="°C", data_kind="stated")
carrier = f("s8.p21;s8.p24", "setting", "nitrogen served as purge and carrier gas", quantity="carrier_gas", value_text="n2", data_kind="stated")
STRUCT = f("s8.p24;s5.p3", "setting", "the chips were PillarHall third-generation prototypes by VTT", quantity="structure", value_text="pillarhall_3", data_kind="stated")
SUBSTR = f("s5.p3;s8.p24", "setting", "the growth surface is the silicon of the all-silicon LHAR chip", quantity="substrate", value_text="si", data_kind="stated")
therm = f("s8.p24", "setting", "the chips were held 10 min at the growth temperature in the chamber before the first pulse", quantity="other", label_as_printed="thermalization time", value="10", unit="min", data_kind="stated")
tA_al = f("s8.p24", "setting", "Al2O3: TMA pulse 0.1 s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value="0.1", unit="s", data_kind="stated")
pA_al = f("s8.p24", "setting", "Al2O3: purge after TMA 4.0 s", quantity="purge_time", qualifiers="step=purge_A", value="4.0", unit="s", data_kind="stated")
tB_al = f("s8.p24", "setting", "Al2O3: water pulse 0.1 s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="0.1", unit="s", data_kind="stated")
pB_al = f("s8.p24", "setting", "Al2O3: purge after water 4.0 s", quantity="purge_time", qualifiers="step=purge_B", value="4.0", unit="s", data_kind="stated")
N_al = f("s8.p24;fig6.cap;tabI.r1c1", "setting", "Al2O3: 500 cycles", quantity="cycle_number", value="500", data_kind="stated")
th_al = f("s8.p24", "observation", "the Al2O3 sequence gave approximately 50 nm of film", quantity="film_thickness", qualifiers="position=planar", value="50", unit="nm", data_kind="stated", method="reflectometry")
flow = f("s8.p24", "setting", "nitrogen flowed at 150 sccm through each reactant line", quantity="gas_flow_rate", qualifiers="gas=n2", value="150", unit="sccm", data_kind="stated")
tA_ti = f("s8.p24", "setting", "TiO2: reactant pulses 0.1 s", quantity="pulse_time", qualifiers="step=reactant_A;species=ticl4", value="0.1", unit="s", data_kind="stated", mentions="TiO2")
pA_ti = f("s8.p24", "setting", "TiO2: purges 4.0 s", quantity="purge_time", qualifiers="step=purge_A", value="4.0", unit="s", data_kind="stated", mentions="TiO2")
tB_ti = f("s8.p24", "setting", "TiO2: water pulse 0.1 s", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="0.1", unit="s", data_kind="stated", mentions="TiO2")
pB_ti = f("s8.p24", "setting", "TiO2: purge after water 4.0 s", quantity="purge_time", qualifiers="step=purge_B", value="4.0", unit="s", data_kind="stated", mentions="TiO2")
N_ti = f("s8.p24;fig7.cap;tabI.r2c1", "setting", "TiO2: 1000 pulse sequences", quantity="cycle_number", value="1000", data_kind="stated")
th_ti = f("s8.p24", "observation", "the TiO2 sequence gave approximately 50 nm of film", quantity="film_thickness", qualifiers="position=planar", value="50", unit="nm", data_kind="stated", method="reflectometry", mentions="TiO2")
ptot = f("s8.p24", "setting", "the chamber pressure during both runs was about 300 Pa", quantity="process_pressure", value="300", unit="Pa", data_kind="stated")
H_chip = f("fig6.cap;fig7.cap;tabI.r1c2;tabI.r2c2", "setting", "the channels' nominal gap is 0.5 µm high", quantity="feature_width", label_as_printed="H", value="500", unit="nm", data_kind="stated")
L_chip = f("fig6.cap;fig7.cap", "setting", "the channel length L was 1 mm", quantity="feature_depth", label_as_printed="L", value="1", unit="mm", data_kind="stated")
ar_chip = f("fig6.cap;fig7.cap", "derived", "the structural aspect ratio of the measured channels is 2000", quantity="aspect_ratio", value="2000", data_kind="computed_by_authors", method="calculation", inputs=[H_chip, L_chip])
opt = f("s8.p25", "setting", "the chips were inspected optically before and after removing the membrane", method="optical_microscopy")
refl = f("s8.p25", "setting", "the growth depth was measured by spectroscopic reflectometry with an SCI FilmTek 2000M", method="reflectometry", mentions="SCI FilmTek 2000M")
scan_n = f("s8.p25", "setting", "a 100-point line scan from the cavity entrance toward its end", quantity="other", label_as_printed="line scan points", value="100", data_kind="stated", method="reflectometry")
scan_step = f("s8.p25", "setting", "the line scan steps were 2 µm", quantity="other", label_as_printed="line scan step", value="2", unit="µm", data_kind="stated", method="reflectometry")
scan_L = f("s8.p25", "setting", "the total scan length was 200 µm", quantity="other", label_as_printed="scan length", value="200", unit="µm", data_kind="stated", method="reflectometry")
obj = f("s8.p25", "setting", "a 50× objective was used", quantity="objective_magnification", value="50", data_kind="stated", method="reflectometry")
spot = f("s8.p25", "setting", "the objective gives roughly a 5 µm spot", quantity="probe_resolution", value="5", unit="µm", data_kind="stated", method="reflectometry")
prec = f("s8.p25", "setting", "the thickness precision, set by how rough the channel surface is, is estimated at about 3 nm", quantity="other", label_as_printed="thickness precision",
         value="3", unit="nm", data_kind="stated", method="reflectometry")

# ---------------------------------------------------------------- Sec. VIII: results and Table I
o_res = f("s9.p1;fig6.cap;fig7.cap", "observation", "Figs. 6 and 7: the measured and fitted thickness profiles of the Al2O3 and TiO2 films", method="reflectometry", mentions="Figs. 6 and 7")
gpcsat_def = f("s9.p3;eq46;s9.p4", "definition", "the saturation growth per cycle gpc_sat is the equilibrium growth at saturating exposure, gpc (1 + K p_A) / (K p_A) from the observed gpc at reactant pressure p_A",
               quantity="saturation_growth_per_cycle", term="gpc_sat|gpcsat|saturation growth in cycle", definition_note="the Langmuir-extrapolated growth at saturating exposure")
rms_def = f("s9.p4;tabI.r0c7", "definition", "the rms thickness error is the root-mean-square difference between the measured and the calculated thickness, how well the model describes the measurement",
            term="rms thickness error")
TAB = {}
for row, mat, lab in (("1", "al", "Al2O3"), ("2", "ti", "TiO2")):
    sp = "tma" if mat == "al" else "ticl4"
    TAB[(mat, "p")] = f(f"tabI.r{row}c3;tabI.cap", "derived", f"Table I, {lab}: the fitted input partial pressure p_A0", quantity="partial_pressure", qualifiers=f"species={sp}", label_as_printed="p_A0",
                        value={"1": "147", "2": "25.7"}[row], unit="Pa", data_kind="computed_by_authors", method="calculation", mentions=lab)
    TAB[(mat, "c")] = f(f"tabI.r{row}c4;tabI.cap", "derived", f"Table I, {lab}: the fitted lumped sticking coefficient c", quantity="initial_sticking_coefficient", qualifiers=f"species={sp}", label_as_printed="c",
                        value={"1": "0.00572", "2": "0.10"}[row], data_kind="computed_by_authors", method="calculation", mentions=lab)
    TAB[(mat, "K")] = f(f"tabI.r{row}c5;tabI.cap", "derived", f"Table I, {lab}: the fitted adsorption equilibrium constant K", quantity="adsorption_equilibrium_constant", qualifiers=f"species={sp}", label_as_printed="K",
                        value={"1": "219", "2": "0.252"}[row], unit="1/Pa", data_kind="computed_by_authors", method="calculation", mentions=lab)
    TAB[(mat, "g")] = f(f"tabI.r{row}c6;tabI.cap", "derived", f"Table I, {lab}: the fitted saturation growth per cycle, printed in picometres", quantity="saturation_growth_per_cycle", qualifiers=f"species={sp}", label_as_printed="gpc_sat",
                        value={"1": "0.1056", "2": "0.0544"}[row], unit="nm/cycle", data_kind="computed_by_authors", method="calculation", mentions=lab + ";" + {"1": "105.6", "2": "54.4"}[row] + " pm")
    TAB[(mat, "e")] = f(f"tabI.r{row}c7;tabI.cap", "derived", f"Table I, {lab}: the rms thickness error of the fit", quantity="other", label_as_printed="rms thickness error",
                        value={"1": "0.974", "2": "1.525"}[row], unit="nm", data_kind="computed_by_authors", method="calculation", mentions=lab)
NK("tabI.r0c0;tabI.r0c1;tabI.r0c2;tabI.r0c3;tabI.r0c4;tabI.r0c5;tabI.r0c6;tabI.r1c0;tabI.r2c0", "Table I header and material cells (the rows' values are the derived facts)")
o_al = f("s9.p5;fig6", "observation", "the Al2O3 film keeps a constant thickness from the channel start almost to the penetration depth", quantity="normalized_thickness", qualifiers="reference=entrance", method="reflectometry")
o_ti = f("s9.p5;fig7", "observation", "the TiO2 thickness is nowhere constant; it falls gradually as the gas goes deeper", quantity="normalized_thickness", qualifiers="reference=entrance", method="reflectometry")
c_diff = claim("s9.p5", "the different profile shapes give quite different sticking coefficients and equilibrium constants in the Langmuir model", "asserted", "surface_chemistry", "initial_sticking_coefficient", "causes",
               supports=[TAB[("al", "c")], TAB[("ti", "c")], TAB[("al", "K")], TAB[("ti", "K")]])
c_hcl = claim("s9.p5", "the root cause is probably the by-product: TiO2 deposition releases very reactive HCl, Al2O3 deposition relatively passive methane", "hedged", "surface_chemistry", "normalized_thickness", "causes",
              mentions="Knapas and Ritala, 2013;Puurunen, 2005")
c_mech = claim("s9.p5;s10.p3", "a known reaction mechanism could replace the Langmuir equation (31) and the same fitting would then give that model's parameters; more parameters need more data", "hedged")

# ---------------------------------------------------------------- the nomenclature as definitions (P89 terms)
DEFS = [("tabu1.r0c0;tabu1.r0c1", "a", "aspect ratio", "aspect_ratio", "", ""), ("tabu1.r2c0;tabu1.r2c1;s6.p6", "c", "lumped sticking coefficient", "initial_sticking_coefficient", "", "a lumped coefficient of every sequential and parallel surface process"),
        ("tabu1.r5c0;tabu1.r5c1", "dA|d_A", "diameter of molecule A", "molecule_diameter", "", ""), ("tabu1.r13c0;tabu1.r13c1", "gpc", "film growth per cycle", "growth_per_cycle", "", ""),
        ("tabu1.r16c0;tabu1.r16c1", "H", "height of the channel", "feature_width", "", "the lateral channel's gap height"), ("tabu1.r17c0;tabu1.r17c1", "K", "adsorption equilibrium constant", "adsorption_equilibrium_constant", "", ""),
        ("tabu1.r18c0;tabu1.r18c1", "L|channel length", "length of the channel", "feature_depth", "", ""), ("tabu1.r19c0;tabu1.r19c1", "M", "molar mass of the deposited film", "molar_mass", "", "of the film's formula unit, not of a reactant"),
        ("tabu1.r20c0;tabu1.r20c1", "MA|M_A", "molar mass of reactant A", "molar_mass", "", ""), ("tabu1.r21c0;tabu1.r21c1", "N", "number of ALD cycles (also the total number of adsorbed molecules)", "cycle_number", "", ""),
        ("tabu1.r24c0;tabu1.r24c1", "pA|p_A", "partial pressure of reactant A", "partial_pressure", "", ""), ("tabu1.r25c0;tabu1.r25c1", "pA0|p_A0|p_{A0}", "input partial pressure of reactant A at the channel entrance", "partial_pressure", "", "the input value at the channel entrance"),
        ("tabu1.r27c0;tabu1.r27c1", "q", "adsorption density of molecules at saturation", "saturation_density", "", ""), ("tabu1.r0c2;tabu1.r0c3", "s", "film thickness", "film_thickness", "", ""),
        ("tabu1.r1c2;tabu1.r1c3", "t", "time", "time", "", ""), ("tabu1.r2c2;tabu1.r2c3", "T", "temperature", "deposition_temperature", "", ""), ("tabu1.r3c2;tabu1.r3c3", "tp|t_p|reactant pulse length|pulse length", "length of the reactant pulse", "pulse_time", "", ""),
        ("tabu1.r6c2;tabu1.r6c3", "W", "width of the channel", "feature_extent", "", ""), ("tabu1.r7c2;tabu1.r7c3", "x", "distance from the beginning of the channel", "distance", "", ""),
        ("tabu1.r14c2;tabu1.r14c3", "θ", "surface coverage", "surface_coverage", "", ""), ("tabu1.r16c2;tabu1.r16c3", "ρ", "density of the condensed phase", "film_density", "", ""),
        ("tabu1.r3c0;tabu1.r3c1", "C", "Gordon model's penetration-depth rate parameter (1/s)", "", "", ""), ("tabu1.r4c0;tabu1.r4c1", "D", "apparent longitudinal diffusion coefficient", "", "", ""),
        ("tabu1.r6c0;tabu1.r6c1", "DA", "gas-phase diffusion coefficient of molecules A", "", "", ""), ("tabu1.r7c0;tabu1.r7c1", "Deff", "effective diffusion coefficient", "", "", ""),
        ("tabu1.r8c0;tabu1.r8c1", "DKn", "Knudsen diffusion coefficient", "", "", ""), ("tabu1.r15c0;tabu1.r15c1", "h", "hydraulic diameter of the channel", "", "", ""),
        ("tabu1.r26c0;tabu1.r26c1", "Pd|P_d", "desorption probability per unit time", "", "", ""), ("tabu1.r8c2;tabu1.r8c3", "xp|x_p", "half-thickness penetration depth", "penetration_depth", "level=50%", "half the thickness at the channel start"),
        ("tabu1.r10c2;tabu1.r10c3", "xt|x_t", "linear region's length, how far the pressure falls linearly", "", "", ""), ("tabu1.r13c2;tabu1.r13c3", "η", "viscosity of gas", "", "", ""),
        ("tabu1.r17c2;tabu1.r17c3", "τ", "time constant of adsorption", "", "", "")]
for ev, term, text, q, quals, note in DEFS:
    kw = dict(term=term)
    if q:
        kw["quantity"] = q
    if quals:
        kw["qualifiers"] = quals
    if note:
        kw["definition_note"] = note
    f(ev, "definition", f"nomenclature: {term.split('|')[0]} is the {text}", **kw)

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Ylilammi et al. 2018: a diffusion-reaction model of ALD growth in lateral high-aspect-ratio channels, fitted to Al2O3 and TiO2 profiles", "", evidence="s3.h")
RECIPE = N(f"{K}:recipe", "activity", "ALD on PillarHall 3 chips in a Picosun R-150: Al2O3 from TMA and water at 300 °C, TiO2 from TiCl4 and water at 110 °C", PAPER, evidence="s8.p21;s8.p24", kind="recipe", how="stated",
           label_as_printed="LHAR recipe")
FX = {r["fact_id"]: r for r in C.facts()}
PARENT = {}


def put(parent, *ids):
    for i in ids:
        if i not in FX:
            FX[i] = next(x for x in C.facts() if x["fact_id"] == i)
        assert i not in PARENT, i
        PARENT[i] = parent


def node(fid, typ, st, parent, **kw):
    N(fid, typ, st, parent, **kw)
    FX[fid] = C.facts()[-1]
    return fid


MODES = {}


def meas(ent, method, label=None, mode="ex_situ", order=None):
    fid = f"{K}:meas:{ent.split(':', 1)[1]}:{method}"
    if fid not in FX:
        kw = dict(kind="measurement", how="stated", label_as_printed=label or method.replace("_", " "))
        if order is not None:
            kw["order"] = order
        node(fid, "activity", f"{method.replace('_', ' ')} on {FX[ent]['label_as_printed']}", ent, **kw)
        MODES[fid.split(":", 1)[1]] = mode
    return fid


put(RECIPE, reactor, carrier, STRUCT, SUBSTR, therm, flow, ptot, H_chip, L_chip, ar_chip, lhar_H, lhar_L, lhar_ar)
CHIP = node(f"{K}:ent:chip", "entity", "the PillarHall 3 chip: a 500 nm lateral gap in an all-silicon membrane on pillars, 1 mm long", RECIPE, evidence="s5.p3;s8.p24;fig6.cap", how="stated", label_as_printed="PillarHall 3 chip")
DEP_AL = node(f"{K}:dep:al2o3", "activity", "Al2O3 ALD, TMA/H2O, 300 °C, 0.1/4.0/0.1/4.0 s, 500 cycles", RECIPE, evidence="s8.p21;s8.p24", kind="deposition", how="stated", label_as_printed="Al2O3 run", inputs=CHIP)
put(DEP_AL, MAT_AL, RA_AL, RB_AL, T_AL, tA_al, pA_al, tB_al, pB_al, N_al)
AL = node(f"{K}:ent:al2o3", "entity", "the Al2O3 film in the LHAR channel, 500 cycles at 300 °C", DEP_AL, evidence="fig6.cap;s9.p1", how="stated", label_as_printed="Al2O3 film, 500 cycles")
DEP_TI = node(f"{K}:dep:tio2", "activity", "TiO2 ALD, TiCl4/H2O, 110 °C, 0.1/4.0/0.1/4.0 s, 1000 cycles", RECIPE, evidence="s8.p21;s8.p24", kind="deposition", how="stated", label_as_printed="TiO2 run", inputs=CHIP)
put(DEP_TI, MAT_TI, RA_TI, RB_TI, T_TI, tA_ti, pA_ti, tB_ti, pB_ti, N_ti)
TI = node(f"{K}:ent:tio2", "entity", "the TiO2 film in the LHAR channel, 1000 cycles at 110 °C", DEP_TI, evidence="fig7.cap;s9.p1", how="stated", label_as_printed="TiO2 film, 1000 cycles")
put(meas(AL, "reflectometry"), th_al, o_al, prec, refl, scan_n, scan_step, scan_L, obj, spot, o_res)
put(meas(TI, "reflectometry"), th_ti, o_ti)
for h in (refl, scan_n, scan_step, scan_L, obj, spot, prec):
    C.spread(h, [meas(AL, "reflectometry"), meas(TI, "reflectometry")], {meas(TI, "reflectometry"): "TiO2 scan"})
put(meas(AL, "optical_microscopy"), opt)
C.spread(opt, [meas(AL, "optical_microscopy"), meas(TI, "optical_microscopy")], {meas(TI, "optical_microscopy"): "TiO2 inspection"})
# the fits of the model to the measured profiles: a calculation activity per film
FIT_AL = node(f"{K}:fit:al2o3", "activity", "the model fitted to the Al2O3 profile (Fig. 6, Table I)", AL, evidence="tabI.cap;fig6.cap", kind="measurement", how="stated", label_as_printed="fit to the Al2O3 profile")
MODES["fit:al2o3"] = "ex_situ"
put(FIT_AL, *[TAB[("al", k)] for k in "pcKge"])
FIT_TI = node(f"{K}:fit:tio2", "activity", "the model fitted to the TiO2 profile (Fig. 7, Table I)", TI, evidence="tabI.cap;fig7.cap", kind="measurement", how="stated", label_as_printed="fit to the TiO2 profile")
MODES["fit:tio2"] = "ex_situ"
put(FIT_TI, *[TAB[("ti", k)] for k in "pcKge"])
# the model: a simulation activity, its reference parameter set as inputs, model runs for the figures
SIM = node(f"{K}:sim", "activity", "the diffusion-reaction model (Eqs. 1-37) and its analytic approximation", PAPER, evidence="s5.h;s6.h;s7.h;s8.h", kind="simulation", how="stated", label_as_printed="diffusion-reaction model")
put(SIM, hs, vA, DA, dkn, hyd, bos, dvis, dden, qdef, coord, teq, deff_typ, eq10_m, lang, eqK, eqg, cav_lang, appr0, eq21, eq23, tail, theq, tau_m, eq31, rk4, rk_n, pd_err, narrow, sum_m, d_tma, d_ticl4,
    b_al, b_ti, tma_mono, d_h2o, d_n2)
REF = [("H", "feature_width", "", "0.5", "µm", "H"), ("W", "feature_extent", "", "0.1", "mm", "W"), ("p_A0", "partial_pressure", "species=tma", "100", "Pa", "p_A0"), ("M_A", "molar_mass", "species=tma", "74.9", "g/mol", "M_A"),
       ("d_A", "molecule_diameter", "species=tma", "591", "pm", "d_A"), ("M_B", "molar_mass", "species=n2", "28", "g/mol", "M_B"), ("d_B", "molecule_diameter", "species=n2", "374", "pm", "d_B"),
       ("p_B", "partial_pressure", "gas=n2", "300", "Pa", "p_B"), ("q", "saturation_density", "", "5", "nm-2", "q"), ("T", "deposition_temperature", "", "500", "K", "T"), ("K", "adsorption_equilibrium_constant", "species=tma", "100", "1/Pa", "K"),
       ("c", "initial_sticking_coefficient", "species=tma", "0.01", "", "c"), ("gpc_sat", "saturation_growth_per_cycle", "species=tma", "0.106", "nm/cycle", "gpc_sat")]
REFS = []
for sym, q, quals, v, u, lab in REF:
    kw = dict(quantity=q, label_as_printed=lab, value=v, data_kind="model_input", mentions="reference parameter set")
    if quals:
        kw["qualifiers"] = quals
    if u:
        kw["unit"] = u
    REFS.append(f("fig2.cap;fig3.cap;fig5.cap", "model", f"the reference parameter set of Figs. 2-5: {sym} = {v} {u}".strip(), **kw))
tp_ref = f("fig4.cap;fig5.cap", "model", "the reference pulse length is 0.1 s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", label_as_printed="t_p", value="0.1", unit="s", data_kind="model_input")
put(SIM, *REFS, tp_ref)
RUNS = {}
for t in ("0.1", "0.05", "0.02", "0.01"):
    rid = node(f"{K}:simrun:tp{t}", "entity", f"model run of Figs. 2 and 3 at a {t} s pulse with the reference parameters", SIM, evidence="fig2.cap;fig3.cap", how="stated", label_as_printed=f"run, pulse {t} s")
    RUNS[("tp", t)] = rid
    put(rid, f("fig2.cap;fig3.cap;fig2;fig3", "setting", f"the pulse length of this run is {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", label_as_printed="Pulse time", value=t, unit="s", data_kind="model_input",
               mentions=f"Pulse time= {t} s;Pulse time= {t} s appr"),
        f("fig2;fig2.cap", "model", f"Fig. 2: the pressure distribution along the channel at the {t} s pulse, numerical and approximate", quantity="partial_pressure", qualifiers="species=tma", method="simulation", mentions=f"Pulse time= {t} s;Pulse time= {t} s appr;Fig. 2"),
        f("fig3;fig3.cap", "model", f"Fig. 3: the surface coverage along the channel at the {t} s pulse, numerical and approximate", quantity="surface_coverage", method="simulation", mentions=f"Pulse time= {t} s;Pulse time= {t} s appr;Fig. 3"))
for H in ("2", "1", "0.5", "0.2"):
    rid = node(f"{K}:simrun:H{H}", "entity", f"model run of Fig. 4: 1000 cycles in a {H} µm channel", SIM, evidence="fig4.cap", how="stated", label_as_printed=f"run, H {H} µm")
    RUNS[("H", H)] = rid
    put(rid, f("fig4.cap;fig4", "setting", f"the original channel height of this run is {H} µm", quantity="feature_width", label_as_printed="H", value=H, unit="µm", data_kind="model_input", mentions=f"H= {H} μm"),
        f("fig4.cap", "setting", f"the {H} µm run has 1000 cycles", quantity="cycle_number", value="1000", data_kind="model_input", mentions=f"H= {H} μm"),
        f("fig4;fig4.cap", "model", f"Fig. 4: the thickness profile after 1000 cycles for the {H} µm channel", quantity="film_thickness", method="simulation", mentions=f"H= {H} μm;Fig. 4"))
RUN5 = node(f"{K}:simrun:fig5", "entity", "the Fig. 5 comparison: the penetration depth in one pulse against pulse length, three models", SIM, evidence="fig5.cap", how="stated", label_as_printed="Fig. 5 models")
put(RUN5, o_fig5, f("fig5;fig5.cap", "model", "Fig. 5, numerical solution: the penetration depth against pulse length", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions="Numerical;Fig. 5"),
    f("fig5;fig5.cap", "model", "Fig. 5, analytic approximation: the penetration depth against pulse length", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions="Approximation;Fig. 5"),
    f("fig5;fig5.cap", "model", "Fig. 5, Gordon model: the penetration depth against pulse length", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions="Gordon model;Fig. 5"))
put(RUNS[("tp", "0.1")], o_fig2, o_fig3)
C.identity(K, "different", [RUNS[("tp", "0.1")], RUN5], "the Fig. 5 comparison scans the pulse length for three models; it is not the Fig. 2 run at a 0.1 s pulse", "fig5.cap;fig2.cap", parent=SIM)
put(RUNS[("H", "0.5")], o_fig4)
# the fitted curves of Figs. 6 and 7 belong to the films' fits
put(FIT_AL, f("fig6;fig6.cap", "model", "Fig. 6: the fitted thickness profile of the Al2O3 film", quantity="film_thickness", method="simulation", mentions="Fitting result;Fig. 6"))
put(meas(AL, "reflectometry"), f("fig6;fig6.cap", "observation", "Fig. 6: the measured thickness profile of the Al2O3 film", quantity="film_thickness", method="reflectometry", mentions="Measured;Fig. 6"))
put(FIT_TI, f("fig7;fig7.cap", "model", "Fig. 7: the fitted thickness profile of the TiO2 film", quantity="film_thickness", method="simulation", mentions="Fitting result;Fig. 7"))
put(meas(TI, "reflectometry"), f("fig7;fig7.cap", "observation", "Fig. 7: the measured thickness profile of the TiO2 film", quantity="film_thickness", method="reflectometry", mentions="Measured;Fig. 7"))
# the Gordon model as a second simulation activity
GSIM = node(f"{K}:sim:gordon", "activity", "the Gordon plug-flow model as rewritten here (Eqs. 38-45)", PAPER, evidence="s8.p10;s8.p11", kind="simulation", how="stated", label_as_printed="Gordon model")
put(GSIM, g_front, g_v, g_F, g_int, g_C)
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
BY_TEXT = {"a one-dimensional diffusion model": [eq10_m, lang, narrow], "an analytic approximation of the diffusion equation": [appr0, tail, eq31], "the simulations predict the measured profiles": [TAB[("al", "e")], TAB[("ti", "e")]],
           "once a channel is long enough": [lhar_L], "fitting the model to a measured thickness profile": [TAB[("al", "c")], TAB[("al", "K")]],
           "a rough molecular diameter is enough": [bos, dkn], "water molecules, lighter and smaller": [d_h2o, d_tma], "c is a lumped sticking coefficient": [lang], "during a pulse the net adsorption rate": [eqg, TAB[("ti", "K")]],
           "a 0.2 µm channel is completely plugged": [narrow], "in the Gordon model the aspect ratio reached": [g_C], "the Gordon model gives a good penetration depth": [o_fig5, bos],
           "the root cause is probably the by-product": [o_al, o_ti], "a known reaction mechanism could replace": [eq31]}
for h, (stance, cause, effect, rel, sup) in CLAIMS.items():
    st = FX[h]["statement"]
    if not sup:
        for key, val in BY_TEXT.items():
            if st.startswith(key):
                sup.extend(val); break
    FX[h].update(stance=stance, cause=cause, effect=effect, relation=rel, links=";".join(sup))
    PARENT.setdefault(h, PAPER)
import re as _re  # noqa: E402
for r in C.facts():
    if "#" in r["fact_id"] and r["type"] == "cited" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
left = [r["fact_id"] for r in C.facts() if "#" in r["fact_id"] and r["fact_id"] not in PARENT and not r["parent"]]
assert not left, left
for r in C.facts():
    if r["fact_id"] in PARENT:
        r["parent"] = PARENT[r["fact_id"]]
GROUPS = [(f"{K}:grp:films", "series", "material", "the two measured films: Al2O3 (TMA/H2O, 300 °C, 500 cycles) and TiO2 (TiCl4/H2O, 110 °C, 1000 cycles)", "s8.p21", c_diff, [AL, TI]),
          (f"{K}:grp:sim_tp", "series", "pulse_time", "the pulse-length series of the model in Figs. 2 and 3", "fig2.cap", o_fig3, [RUNS[("tp", t)] for t in ("0.1", "0.05", "0.02", "0.01")]),
          (f"{K}:grp:sim_H", "series", "feature_width", "the channel-height series of the model in Fig. 4", "fig4.cap", plug, [RUNS[("H", H)] for H in ("2", "1", "0.5", "0.2")])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0].split(" of ")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s6.p10", "The Langmuir adsorption model stands in for a surface mechanism that may be much more complicated; the fitted c and K are its lumped parameters.", [TAB[(m, k)] for m in ("al", "ti") for k in "cK"], "", ""),
    ("s8.p7", "The model updates one uniform channel height after each pulse, so the modelled tail is too narrow and the film thins slightly too steeply there; fine while the film is thin against H and grows little beyond x_p.",
     [narrow, TAB[("al", "e")], TAB[("ti", "e")]], "", ""),
    ("s5.p19", "Only the metal precursor's diffusion is modelled; water is taken as never rate-limiting.", [c_water], "", ""),
    ("s5.p15;s5.p16", "The molecular diameters of TMA and TiCl4 are rough estimates from the condensed-phase density; TMA is treated as its monomer.", [d_tma, d_ticl4], "", ""),
    ("s8.p25", "The thickness precision is about 3 nm, set by how rough the channel surface is.", [AL, TI], "film_thickness", ""),
    ("fig5.cap", "In the Fig. 5 comparison the Gordon model uses Knudsen diffusion alone, slightly faster than the Bosanquet effective diffusion of Eq. (6).", [o_fig5], "", ""),
    ("s8.p24", "The approximately 50 nm film thickness is the planar value the sequence leads to, stated without a measurement.", [th_al, th_ti], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_agree.split(":", 1)[1]: [TAB[("al", "e")].split(":", 1)[1], TAB[("ti", "e")].split(":", 1)[1]], c_diff.split(":", 1)[1]: [TAB[("al", "c")].split(":", 1)[1], TAB[("ti", "c")].split(":", 1)[1]]})
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
# P131: a claim is a triple or it is not a claim; every claim without a full triple re-typed by the one rule (facts.retype)
BG = 'background, motivation, prior art or scope'
RETYPE = {
    's5.p4#1': ('model', 'yli18:sim'),
    's9.p5#5': ('duplicate', 's6.p10#3'),
}
C.retype(K, RETYPE)
write(K, PID)
