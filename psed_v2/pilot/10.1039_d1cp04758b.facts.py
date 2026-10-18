#!/usr/bin/env python3
"""Stage 2 facts for yim22 (10.1039_d1cp04758b, Yim, Verkama, Velasco, Arts, Puurunen 2022, PCCP: the Ylilammi diffusion-reaction model
re-implemented in MATLAB (Model A) and used to simulate ALD thickness profiles in wide microchannels against every process parameter, the
channel-filling effect, the free-molecular against the transition flow regime (Table 2), and the slope method's back-extracted sticking
coefficients against the set values (Table 3, Fig. 6), with the Yanguas-Gil/Elam model (Model B) for comparison (Fig. 7)).
Text, Tables 1-3, the symbol list, the 31 equations and the captions; every curve is an imported record (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1039_d1cp04758b.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "yim22", "10.1039_d1cp04758b"


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK(";".join(f"s{i}.h" for i in range(1, 22)), "heading")
NK("s0.p1;s1.p1;s1.p2;s1.p3;s1.p4;s2.p4;s2.p5;s2.p6;s2.p7", "front matter, authors, affiliations, dates, footnote marks")
NK("s17.p1;s18.p1;s20.p1;s21.p1", "author contributions, funding, conflicts, acknowledgements")
NK("s21.p2;s21.p3;s21.p4", "reference list")
NK("s3.p1;s4.p1", "pointers to the Ylilammi 2018 derivation, no value")
NK(";".join(f"tab1.r{i}c0" for i in range(1, 12)), "Table 1 parameter symbols (the symbol definitions cover them)")
NK("s5.p5;s9.p4", "a connective fragment of the previous paragraph")
NK("fig1.cap;fig1a;fig1b", "a schematic of the microchannel and the four regions of a thickness profile, no value")
NK("fig3.cap;fig3", "the algorithm flowchart, no value")
NK(";".join(f"tab1.r0c{j}" for j in range(3)) + ";" + ";".join(f"tab2.r0c{j}" for j in range(7)) + ";" + ";".join(f"tab3.r0c{j}" for j in range(8)), "table headers")
NK(";".join(f"tab3.r{i}c0" for i in range(1, 16)), "Table 3 series labels (the runs carry the series as groups)")
NK(";".join(f"tabu1.r{i}c{j}" for i in range(34) for j in range(2)) + ";" + ";".join(f"tabu2.r{i}c{j}" for i in range(23) for j in range(2)),
   "list-of-symbols cells: every symbol is a definition fact citing its row")

# ---------------------------------------------------------------- the paper's claims
c_reimpl = claim("abs.g1;s2.p13;s16.p1;s16.p2", "the Ylilammi diffusion-reaction model was re-implemented to simulate how ALD growth propagates in wide microchannels, and used to map the thickness profile against process parameters and flow regimes", "asserted")
c_approx = claim("abs.g2;s5.p10", "in the model the reactant partial pressure is an analytic approximation, linear then exponential along the channel", "asserted")
c_mass = claim("abs.g3;s12.p3;s16.p3", "a larger molar mass of the reactant and a larger GPC both shorten the penetration depth", "asserted", "molar_mass", "penetration_depth", "decreases")
c_inert = claim("abs.g3;s14.p5;s14.p7", "the inert gas's molecular mass and diameter matter only in transition flow, never in free molecular flow", "asserted", "gas_diffusion", "penetration_depth", "causes")
c_slope = claim("abs.g4;s15.x1;s16.p5", "the slope method returns sticking coefficients systematically about 25 % above the set values; a correction factor would make it usable on Model A profiles", "asserted",
                "initial_sticking_coefficient", "front_slope", "causes")
c_why = claim("s15.p3;s15.p5;s16.p5", "the overshoot most likely comes from the analytic pressure approximation of Model A, whose pressure drops faster at the adsorption front than Model B's and steepens the half-thickness slope", "hedged",
              "gas_diffusion", "front_slope", "causes")
c_fp = claim("s16.p3;s16.p4;s13.p7", "a fingerprint thickness profile needs free molecular flow, channel filling below 5 %, and the scaled profile (thickness over cycles against dimensionless distance), from which the GPC and the kinetics follow",
             "asserted", "feature_narrowing", "front_slope", "causes")
c_press = claim("s16.p6", "to extract kinetic parameters from measured profiles the pressure must be known, since most models assume free molecular flow; different models give different parameters from the same data", "asserted")
c_open = claim("s16.p7", "the community should share measured profiles openly as data and the models as code", "asserted")
c_intro = claim("s2.p1", "ALD coats almost any inorganic substrate, high-aspect-ratio structures included, yet conformality there often needs tuned process parameters", "asserted", mentions="ref 1;ref 2;ref 3")
c_mc = claim("s2.p9", "Monte Carlo methods reach beyond free molecular flow through the mean free path as a statistical parameter; every model reproduces the ideal profile, constant thickness then an abrupt fall", "asserted", mentions="ref 11;ref 12;ref 13;ref 29")
c_43 = claim("s14.p1;s14.p2;s14.p3", "the regime comparison varied one parameter at a time in free molecular and in transition flow over a single cycle, reading x̃50% and the slope from both the scaled and the Type 1 profile (Figs. S6-S15)", "asserted", mentions="ref 25;ref 27;ref 28;ref 31")
c_models = claim("s2.p2;s2.p3", "feature-scale ALD models are ballistic, Monte Carlo or diffusion-reaction; the last, on Fick's law, serve free molecular, transition and continuum flow alike through the effective diffusion coefficient", "asserted",
                 mentions="ref 4;ref 5;ref 6;ref 9;ref 10;ref 17;ref 18;ref 20;ref 23;ref 25;ref 27;ref 28")
c_regime = claim("s2.p10", "the Thiele modulus, reaction rate over diffusion rate, tells a reaction-limited from a diffusion-limited regime; it is far above one in the latter", "asserted", mentions="ref 27;ref 37")
c_kin = claim("s2.p10;s2.p11", "ALD kinetics are usually described by irreversible single-site Langmuir adsorption with a lumped sticking coefficient, read from the steepness of the termination profile", "asserted",
              "surface_chemistry", "front_slope", "causes", mentions="ref 11;ref 12;ref 30;ref 31")
c_wide = claim("s4.p2;s4.p3", "the model's microchannel is wide and infinitely long, the height the limiting dimension; it describes vertical trenches as well", "asserted")
c_step = claim("s4.p4", "the reactant enters as a step: p_A0 at the entrance during the pulse, zero otherwise; the inert gas pressure is the same inside and outside; only the reactant-A step is simulated", "asserted", mentions="ref 3;ref 42")
c_err1 = claim("s5.p12", "Eq. (1) of Ylilammi 2018 for the collision frequency lacks Avogadro's number in both terms; Eq. (6) here corrects it", "asserted", mentions="ref 18;ref 40")
c_err2 = claim("s10.p7", "Eq. (4) of Cremers 2019 for the collision cross section takes the sum of squared radii instead of the squared sum; Eq. (27) here corrects it", "asserted", mentions="ref 4;ref 54")
c_lump = claim("s6.p1;s6.p2", "the Langmuir step A + * ⇌ A* is a lumped, not an elementary, reaction; the real surface chemistry is more complex", "asserted", "surface_chemistry", "initial_sticking_coefficient", "causes", mentions="ref 3;ref 18")
c_narrow = claim("s7.p3;s7.p4", "the constant free-height simplification speeds up the computation but thins each cycle's coverage somewhat too steeply in Region III; it holds while the film is thin against H and grows little beyond x50%", "asserted",
                 "feature_narrowing", "normalized_thickness", "causes", mentions="ref 18")
c_ok2 = claim("s5.p19;s6.p10;s7.p4", "Fig. 2 and Fig. S2 reproduce Figs. 2-4 of Ylilammi 2018, so the model was re-implemented correctly", "asserted", mentions="ref 18")
c_dose = claim("s12.p3", "a higher reactant partial pressure and a longer pulse both lengthen the penetration depth; their product, the dose, sets it in free molecular flow, PD50% scaling as the square root of p_A t1", "asserted",
               "partial_pressure", "penetration_depth", "increases", mentions="ref 20;ref 26;ref 31")
c_light = claim("s12.p3", "lighter reactant molecules penetrate deeper, since they diffuse faster", "asserted", "molar_mass", "penetration_depth", "decreases")
c_rho = claim("s12.p3", "a lower film density raises the thickness at constant adsorption density but leaves the penetration depth unchanged", "asserted", "film_density", "film_thickness", "decreases")
c_q = claim("s12.p3", "a higher adsorption density (GPC as areal number density) raises the saturated thickness and shortens the penetration depth, as seen experimentally", "asserted", "saturation_density", "penetration_depth", "decreases",
            mentions="ref 40;ref 45;ref 51")
c_pd = claim("s12.p3", "a high desorption probability reshapes Region II of the profile, before the fast decrease", "asserted", "desorption", "normalized_thickness", "causes")
c_c = claim("s12.p3", "the sticking coefficient strongly shapes the thickness profile, as earlier diffusion-limited simulations showed", "asserted", "initial_sticking_coefficient", "front_slope", "increases", mentions="ref 12;ref 30;ref 31")
c_Tp = claim("s12.p3", "the temperature and the inert gas pressure have only a minor effect on the penetration depth", "asserted", "deposition_temperature", "penetration_depth", "no_effect")
c_sum = claim("s12.p4", "besides the sticking coefficient and the dose, the reactant molar mass, the adsorption density and the film density shape the detailed thickness profile", "asserted")
c_fill = claim("s13.p1;s13.p2", "the film narrows the channel by twice the GPC per cycle, so the profile's shape depends on the cycle number; a fingerprint profile needs little filling (earlier under 10 %)", "asserted",
               "feature_narrowing", "normalized_thickness", "causes", mentions="ref 40")
c_5ab = claim("s13.p3;fig5.cap", "Fig. 5(a),(b): a higher channel increases the penetration depth and more cycles increase the thickness, as expected", "asserted", "feature_width", "penetration_depth", "increases")
c_5c = claim("s13.p3;s13.p4;fig5.cap", "at constant cycles the scaled half-thickness penetration depth x̃50% first rises then falls with the channel height", "asserted", "feature_width", "coated_aspect_ratio", "causes")
c_5d = claim("s13.p4", "at constant height the scaled profiles for 5 to 20 cycles about overlap; from a few percent filling the penetration depth falls with filling", "asserted", "feature_narrowing", "coated_aspect_ratio", "decreases")
c_knee = claim("s13.p5", "the slope at x̃50% settles to about −0.0029 for little filling in the cycle series; in the height series it rises again after a knee at Kn = 8, because wider channels move toward transition flow where gas-phase collisions lower the diffusion coefficient",
               "asserted", "gas_diffusion", "front_slope", "causes")
c_concl2 = claim("s13.p6;s13.p7", "to keep the profile independent of cycle number the filling must stay under a few percent, and the flow must be free molecular, checked by the mean free path against the limiting dimension", "asserted")
c_tab2 = claim("s14.p4;s14.p5;s14.p7;tab2.cap", "Table 2: the trends differ between regimes; in transition flow a higher channel height, total pressure or reactant molar mass shortens the penetration depth and steepens the slope, and the inert gas matters", "asserted",
               "gas_diffusion", "coated_aspect_ratio", "causes")
c_scaled = claim("s14.p8", "the scaled profile and the Type 1 normalized profile show the same trends except for q and ρ, which change the scaled slope but not the normalized one", "asserted", "saturation_density", "front_slope", "increases")
c_kn100 = claim("s15.p1;s15.p2;fig6.cap", "at Kn ≥ 100 the effective diffusion coefficient equals the Knudsen one; the comparison used one cycle so that filling does not bias the extracted sticking coefficient", "asserted",
                "gas_diffusion", "initial_sticking_coefficient", "causes")
c_A_B = claim("s9.p5", "Model B differs from Model A in two ways: irreversible adsorption without desorption, and the pressure solved numerically from Eq. (1) instead of the analytic approximation", "asserted", mentions="ref 18;ref 20")

# ---------------------------------------------------------------- cited
r_p = f("s2.p3", "cited", "ALD processes often run in a low vacuum of roughly 1e2 Pa", quantity="process_pressure", value="100", unit="Pa", data_kind="cited", method="cited", mentions="ref 3")
r_kn = f("s2.p8;s2.p3;s12.p2", "cited", "flow regimes by Knudsen number: free molecular Kn ≫ 1, transition 0.1–10, continuum Kn ≤ 1e-3", quantity="knudsen_number", value_min="0.1", value_max="10", data_kind="cited", method="cited",
         mentions="ref 25;transition flow 0.1–10")
r_fill = f("s13.p2", "cited", "an earlier work proposed a channel filling below 10 %", quantity="other", label_as_printed="channel filling", value="0.1", data_kind="cited", method="cited", mentions="ref 40;10%")
r_q = f("s12.p1", "cited", "an adsorption density of 4 nm-2 is in the range of the TMA-water process and typical for ALD", quantity="saturation_density", value="4", unit="nm-2", data_kind="cited", method="cited", mentions="ref 32;ref 42;ref 49;ref 50")

# ---------------------------------------------------------------- definitions (P89): the symbol list and the text
DEFS = [
    ("tabu1.r0c0;tabu1.r0c1;s5.p16", "b|b_film|b_A", "metal atoms per reactant molecule (b_A) or per film formula unit (b_film)", "", ""),
    ("tabu1.r1c0;tabu1.r1c1;s5.p17", "c", "sticking coefficient, the sticking probability of Reactant A on collision with the wall, 0 to 1", "initial_sticking_coefficient", "a lumped coefficient"),
    ("tabu1.r2c0;tabu1.r2c1;s10.p11", "c_ext|cext|c_{ext}", "the sticking coefficient the slope method gives back", "initial_sticking_coefficient", "back-extracted by the slope method of Arts 2019, Eq. (30)"),
    ("tabu1.r3c0;tabu1.r3c1;s5.p14", "D", "apparent longitudinal diffusion coefficient of the Ylilammi model", "", ""),
    ("tabu1.r4c0;tabu1.r4c1;s5.p2", "D_A|DA|gas-phase diffusion coefficient", "gas-phase diffusion coefficient of Reactant A", "", ""),
    ("tabu1.r5c0;tabu1.r5c1;s5.p2", "D_eff|Deff|effective diffusion coefficient|diffusion coefficient", "effective diffusion coefficient, Bosanquet of D_A and D_Kn", "", ""),
    ("tabu1.r6c0;tabu1.r6c1;s5.p9", "D_Kn|DKn|Dkn|Knudsen diffusion coefficient", "Knudsen diffusion coefficient", "", ""),
    ("tabu1.r7c0;tabu1.r7c1;s5.p8", "d_A|dA", "hard-sphere diameter of molecule A", "molecule_diameter", ""),
    ("tabu1.r8c0;tabu1.r8c1;s5.p8", "d_I|dI|d_i|d_t", "the inert gas molecule's hard-sphere diameter", "molecule_diameter", "of the inert carrier gas I"),
    ("tabu1.r9c0;tabu1.r9c1", "f_ads", "adsorption rate per unit area", "", ""),
    ("tabu1.r10c0;tabu1.r10c1", "f_des", "desorption rate per unit area", "", ""),
    ("tabu1.r11c0;tabu1.r11c1;s5.p3", "g", "the net rate of molecules adsorbing, gas to surface", "", ""),
    ("tabu1.r12c0;tabu1.r12c1;s5.p16", "gpc_sat|gpcsat|GPC", "saturation growth per cycle, thickness-based", "saturation_growth_per_cycle", ""),
    ("tabu1.r13c0;tabu1.r13c1;s5.p3", "h", "hydraulic diameter of the channel", "", ""),
    ("tabu1.r14c0;tabu1.r14c1;s4.p2", "H|channel height|microchannel height", "height of the channel, the limiting dimension", "feature_width", ""),
    ("tabu1.r15c0;tabu1.r15c1;s2.p10", "h_T|hT|h_r|Thiele modulus", "Thiele modulus, reaction rate over diffusion rate", "", ""),
    ("tabu1.r16c0;tabu1.r16c1;s6.p7", "K", "adsorption equilibrium constant of the Ylilammi model", "adsorption_equilibrium_constant", ""),
    ("tabu1.r17c0;tabu1.r17c1;s2.p3", "Kn|K_n|K_N", "Knudsen number, mean free path over the hydraulic diameter", "knudsen_number", ""),
    ("tabu1.r18c0;tabu1.r18c1", "k_B", "Boltzmann constant", "", ""),
    ("tabu1.r19c0;tabu1.r19c1;s4.p2", "L", "length of the channel", "feature_depth", ""),
    ("tabu1.r20c0;tabu1.r20c1;s5.p16", "M", "molar mass of the deposited film material, one formula unit", "molar_mass", "of the film's formula unit"),
    ("tabu1.r21c0;tabu1.r21c1", "M_A|MA", "molar mass of Reactant A", "molar_mass", ""),
    ("tabu1.r22c0;tabu1.r22c1;s4.p4", "M_I|MI|M_i|M_t|M_l", "molar mass of the inert gas I (M_B in Ylilammi 2018)", "molar_mass", "of the inert carrier gas I"),
    ("tabu1.r23c0;tabu1.r23c1", "N", "number of ALD cycles", "cycle_number", ""),
    ("tabu1.r24c0;tabu1.r24c1;s10.p10", "n_A", "particle concentration of Reactant A at the entrance", "", ""),
    ("tabu1.r25c0;tabu1.r25c1", "N_0", "Avogadro's constant", "", ""),
    ("tabu1.r26c0;tabu1.r26c1", "p|total pressure", "total pressure, p_A0 + p_I", "process_pressure", "the sum of the reactant and inert partial pressures"),
    ("tabu1.r27c0;tabu1.r27c1;s4.p4", "p_A|pA", "partial pressure of Reactant A", "partial_pressure", ""),
    ("tabu1.r28c0;tabu1.r28c1;s4.p4", "p_A0|pA0|p_{A0}|rho_{A0}|initial partial pressure of Reactant A", "initial partial pressure of Reactant A at the entrance", "partial_pressure", "the entrance value"),
    ("tabu1.r29c0;tabu1.r29c1;s4.p4", "p_I|pI|p_i|p_t|rho_1|inert gas pressure", "partial pressure of the inert gas I", "partial_pressure", "of the inert carrier gas I"),
    ("tabu1.r30c0;tabu1.r30c1", "p_At", "the Reactant A pressure at the transition point x_t", "", ""),
    ("tabu1.r31c0;tabu1.r31c1;s6.p5", "P_d|Pd|p_d|desorption probability", "desorption probability in unit time", "", ""),
    ("tabu1.r32c0;tabu1.r32c1;s5.p15", "q|adsorption density", "adsorption density of metal atoms, the GPC as an areal number density", "saturation_density", ""),
    ("tabu1.r33c0;tabu1.r33c1;s5.p17", "Q", "collision rate with the surface at unit pressure", "", ""),
    ("tabu2.r0c0;tabu2.r0c1", "r_i", "hard-sphere radius of molecule i", "", ""),
    ("tabu2.r1c0;tabu2.r1c1", "R", "gas constant", "", ""),
    ("tabu2.r2c0;tabu2.r2c1", "s|film thickness", "film thickness in the Ylilammi model", "film_thickness", ""),
    ("tabu2.r3c0;tabu2.r3c1", "S", "surface area of the microchannel", "", ""),
    ("tabu2.r4c0;tabu2.r4c1", "t|time", "time", "time", ""),
    ("tabu2.r5c0;tabu2.r5c1;s4.p4", "t_1|t1|pulse length of Reactant A|reactant pulse time", "length of the Reactant A pulse, Step 1 of the cycle", "pulse_time", "the reactant-A step"),
    ("tabu2.r6c0;tabu2.r6c1", "T", "temperature", "deposition_temperature", ""),
    ("tabu2.r7c0;tabu2.r7c1", "ν|nu", "velocity of the gas front in the Ylilammi model", "", ""),
    ("tabu2.r8c0;tabu2.r8c1", "V", "volume of the microchannel", "", ""),
    ("tabu2.r9c0;tabu2.r9c1;s5.p6", "v̄_A|v_A|vA", "average speed of molecules A, the thermal velocity", "", ""),
    ("tabu2.r10c0;tabu2.r10c1;s4.p2", "W", "width of the channel", "feature_extent", ""),
    ("tabu2.r11c0;tabu2.r11c1", "x", "distance from the channel entrance", "distance", ""),
    ("tabu2.r12c0;tabu2.r12c1;s7.p4", "x_50%|x50%|half-thickness penetration depth", "half-thickness penetration depth (x_p in Ylilammi 2018)", "penetration_depth", "level 50 %, the entrance thickness as reference"),
    ("tabu2.r13c0;tabu2.r13c1;s2.p12", "x̃|x~|dimensionless distance", "dimensionless distance into the channel, x/H", "dimensionless_distance", ""),
    ("tabu2.r14c0;tabu2.r14c1;s13.p4", "x̃_50%|x̃50%|x̃₅₀%|x~50%", "scaled half-thickness penetration depth, x50%/H", "coated_aspect_ratio", "PD50% over the channel height"),
    ("tabu2.r15c0;tabu2.r15c1;s5.p13", "x_s|xs", "distance where the extrapolated linear pressure is zero", "", ""),
    ("tabu2.r16c0;tabu2.r16c1;s5.p10", "x_t|xt", "distance of the linear part of the pressure distribution", "", ""),
    ("tabu2.r17c0;tabu2.r17c1;s5.p7", "z_A|zA", "how often a Reactant A molecule collides with other gas molecules", "", ""),
    ("tabu2.r18c0;tabu2.r18c1;s6.p3", "θ|theta|surface coverage", "surface coverage, the fraction of occupied sites, 0 to 1", "surface_coverage", ""),
    ("tabu2.r19c0;tabu2.r19c1;s5.p16", "ρ|rho|film density|density", "mass density of the deposited film", "film_density", ""),
    ("tabu2.r20c0;tabu2.r20c1;s10.p3", "λ|lambda|mean free path", "mean free path", "mean_free_path", ""),
    ("tabu2.r21c0;tabu2.r21c1;s10.p5", "σ_ij|sigma", "the cross section for a collision of molecules i and j", "", ""),
    ("tabu2.r22c0;tabu2.r22c1;s10.p9", "γ|gamma|excess number", "excess number of the Yanguas-Gil/Elam model: Reactant A molecules per adsorption site in the structure", "", ""),
    ("s13.p3;fig5.cap", "1-2s/H|1 - 2s/H|channel filling fraction|channel filling", "the channel filling fraction 1 − 2s/H: how much of the channel height the film on both walls has taken", "", ""),
    ("s13.p5;fig5.cap;tab2.r0c2", "d(s/N)/dx̃ at x̃₅₀%|d(s/N)/dx̃|scaled slope at half-thickness penetration depth|slope at half-thickness penetration depth", "the slope of the scaled profile s/N against x̃ at the half-thickness penetration depth, in nm", "", ""),
    ("s2.p11;s2.p12;s10.p12", "Type 1 normalized thickness profile|normalized thickness", "the Type 1 normalized profile: the normalized growth (one at saturation, θ = 1) against the dimensionless distance", "normalized_thickness",
     "reference assumed saturation, s/(N gpc_sat)"),
    ("s14.p2;s16.p3", "scaled thickness profile|s/N", "the scaled profile: thickness over cycles s/N against the dimensionless distance", "growth_per_cycle", "s/N, the per-cycle thickness along the channel"),
    ("tab3.r0c5;s10.p12", "dθ/dx̃|dθ/dx̃ at θ=1/2|slope", "the slope of the Type 1 normalized profile at half coverage, the input of the slope method", "front_slope", "dθ/dx̃ at θ = 1/2"),
]
for ev, term, text, q, note in DEFS:
    kw = dict(term=term)
    if q:
        kw["quantity"] = q
        if q in ("penetration_depth", "coated_aspect_ratio"):
            kw["qualifiers"] = "level=50%"
        if q == "normalized_thickness":
            kw["qualifiers"] = "reference=assumed_saturation"
        if q == "front_slope":
            kw["qualifiers"] = "by=H;reference=assumed_saturation"
    if note:
        kw["definition_note"] = note
    f(ev, "definition", f"symbol {term.split('|')[0]}: {text}", **kw)

# ---------------------------------------------------------------- the model as model facts
M = []
M.append(f("s5.p1;eq1;s5.p2", "model", "Eq. (1): the one-dimensional diffusion equation for p_A with the adsorption loss term 4gRT/(hN0)", mentions="ref 18"))
M.append(f("eq2;s5.p2", "model", "Eq. (2): the Bosanquet effective diffusion coefficient from the gas-phase and the Knudsen coefficients"))
M.append(f("eq3;s5.p3", "model", "Eq. (3): the hydraulic diameter h = 2/(1/H + 1/W)"))
M.append(f("s5.p4;eq4;s5.p6;eq5", "model", "Eqs. (4)-(5): D_A = 3π v̄_A²/(16 z_A) with the thermal speed (8RT/πM_A)^1/2"))
M.append(f("s5.p7;eq6;s5.p8", "model", "Eq. (6): the collision frequency of A in the A + I mixture from hard-sphere diameters, molar masses and partial pressures, with Avogadro's number in both terms"))
M.append(f("s5.p9;eq7", "model", "Eq. (7): the Knudsen diffusion coefficient h (8RT/9πM_A)^1/2"))
M.append(f("s5.p10;eq8;s5.p11;eq9;eq10", "model", "Eqs. (8)-(9): the analytic pressure, linear p_A0 (1 − x/x_s) up to x_t, then exponential with the scale x_s − x_t"))
M.append(f("s5.p13;eq11;s5.p14;eq12", "model", "Eqs. (10)-(11): x_s = (Dt)^1/2 and the apparent longitudinal diffusion coefficient D from p_A0, H, D_eff, q, T and K"))
M.append(f("s5.p15;eq13;s5.p16", "model", "Eq. (12): the adsorption density q from the film density, the saturation GPC, the formula-unit molar mass and the metal atoms per formula unit and per reactant molecule"))
M.append(f("eq14;s5.p17;eq15", "model", "Eqs. (13)-(14): the transition point x_t from x_s and h N0 D_eff/(4RTcQ), never negative; Q = N0/(2πM_A RT)^1/2"))
M.append(f("s5.p18", "model", "D_A, D and D_eff are updated at every position and time in each cycle, since D_A depends on p_A(x,t)"))
M.append(f("s6.p1;eq16;s6.p2", "model", "Eq. (15): reversible single-site Langmuir adsorption A + * ⇌ A* on a checkerboard of equal, non-interacting sites"))
M.append(f("s6.p3;eq17;s6.p4;eq18", "model", "Eqs. (16)-(17): the adsorption rate (1 − θ) c Q p_A"))
M.append(f("s6.p5;eq19;s6.p6;eq20", "model", "Eqs. (18)-(19): the desorption rate θ q P_d and the net rate g = f_ads − f_des"))
M.append(f("s6.p7;eq21", "model", "Eq. (20): the equilibrium constant K = θ_eq/(p_A (1 − θ_eq)) = cQ/(q P_d)"))
M.append(f("s6.p8;eq22;s6.p9", "model", "Eq. (21): the coverage rate equation dθ/dt = cQp_A/q − (cQp_A/q + P_d) θ, solved numerically with the analytic p_A"))
M.append(f("s7.p1;eq23;s7.p2;eq24", "model", "Eqs. (22)-(23): the thickness s = θ gpc_sat per cycle, summed over the N cycles"))
M.append(f("s7.p3;eq25;s7.p4", "model", "Eq. (24): the free height H(N) = H(0) − 2N gpc_sat, and D_Kn updated with it each cycle"))
M.append(f("s9.p1;s9.p2", "model", "Model A was solved in MATLAB on an equidistant x array with the ODE23 solver (relative tolerance 1e-3, absolute 1e-5), p_A zero everywhere at t = 0, the transport properties from the previous time step",
           mentions="MATLAB;ODE23;1e-3;1e-5"))
M.append(f("s9.p3", "model", "each cycle: solve Eq. (21) to the pulse time, the thickness from Eq. (22), the increment and the new height from Eqs. (23)-(24), repeated to N cycles"))
MB = []
MB.append(f("s9.p5;s9.p6;s9.p7", "model", "Model B (Yanguas-Gil and Elam): irreversible adsorption, p_A and θ solved together from Eq. (1) and Eq. (21) with MATLAB's pdepe in slab geometry, free molecular flow (D_eff = D_Kn), tolerances 1e-3 and 1e-6, p_A = θ = 0 at t = 0, p_A(0,t) = p_A0 and a reactive end boundary",
             mentions="ref 20;ref 43;pdepe;1e-3;1e-6"))
A_ext = []
A_ext.append(f("s10.p1", "model", "the half-thickness penetration depth and its slope are interpolated linearly between the two discretisation points around half thickness; the points are spaced so that their y difference is at most 3 % of the range",
               quantity="other", label_as_printed="discretisation criterion", value="3", unit="%", data_kind="stated"))
A_ext.append(f("s10.p2;eq26;s10.p3", "model", "Eq. (25): Kn = λ/h with the hydraulic diameter; the model comparison used Kn ≥ 100 and Thiele modulus above one", mentions="ref 4;ref 9;ref 25;ref 27;ref 37"))
A_ext.append(f("s10.p4;eq27;s10.p5;eq28;s10.p6", "model", "Eqs. (26)-(27): the mean free path from k_B T over the collision cross sections with A and with I, σ_ij = π (d_i/2 + d_j/2)²", mentions="ref 4;ref 44"))
A_ext.append(f("s10.p8;eq29", "model", "Eq. (28): the Thiele modulus h_T = L (c v̄_A/(2 H D_eff))^1/2 for a first-order reaction in the channel", mentions="ref 27;ref 37"))
A_ext.append(f("s10.p9;eq30;s10.p10", "model", "Eq. (29): the excess number γ = V n_A/(q S); the slope method needs γ ≪ 1", mentions="ref 20;ref 31"))
gam = f("s10.p10", "derived", "the excess number at the baseline condition is about 4.5e-4", quantity="other", label_as_printed="γ", value="4.5e-4", data_kind="computed_by_authors", method="calculation")
A_ext.append(f("s10.p11;eq31;s10.p12", "model", "Eq. (30): the slope method, c = 13.9 (dθ/dx̃ at θ = 1/2)², θ read from the Type 1 normalized profile s/(N gpc_sat); for the back-extraction the y step of the discretisation was below 1 % of the range",
               quantity="other", label_as_printed="discretisation criterion (back-extraction)", value="1", unit="%", data_kind="stated", mentions="ref 31;13.9"))

# ---------------------------------------------------------------- the parameter sets (model inputs)
def pset(ev, rows):
    out = {}
    for sym, q, quals, v, u, lab, note in rows:
        kw = dict(quantity=q, label_as_printed=lab, value=v, data_kind="model_input", mentions=note) if q else dict(label_as_printed=lab, value=v, mentions=note)
        if quals:
            kw["qualifiers"] = quals
        if u:
            kw["unit"] = u
        if not q:
            kw["quantity"] = "other"; kw["data_kind"] = "model_input"
        out[sym] = f(ev, "model", f"{note.split(';')[0]}: {sym} = {v} {u}".strip(), **kw)
    return out


BASE = pset("tab1.cap;tab1.r1c1;tab1.r2c1;tab1.r3c1;tab1.r4c1;tab1.r5c1;tab1.r6c1;tab1.r7c1;tab1.r8c1;tab1.r9c1;tab1.r10c1;tab1.r11c1;s12.p1;s12.p2;s12.p5", [
    ("H", "feature_width", "", "0.5", "µm", "H", "Table 1 baseline (bold);500 nm"), ("W", "feature_extent", "", "10", "mm", "W", "Table 1 baseline footnote"),
    ("T", "deposition_temperature", "", "250", "°C", "T", "Table 1 baseline (bold)"), ("p_A0", "partial_pressure", "species=tma", "100", "Pa", "p_A0", "Table 1 baseline (bold);Reactant A, TMA-like"),
    ("p_i", "partial_pressure", "gas=n2", "500", "Pa", "p_i", "Table 1 baseline (bold);inert gas, nitrogen-like"), ("t_1", "pulse_time", "step=reactant_A;species=tma", "0.1", "s", "t_1", "Table 1 baseline (bold)"),
    ("q", "saturation_density", "", "4", "nm-2", "q", "Table 1 baseline (bold)"), ("M_A", "molar_mass", "species=tma", "100", "g/mol", "M_A", "Table 1 baseline (bold);an arbitrary value"),
    ("M_I", "molar_mass", "gas=n2", "28", "g/mol", "M_I", "Table 1 baseline footnote;typical for nitrogen"), ("rho", "film_density", "", "3.5", "g/cm3", "ρ", "Table 1 baseline (bold);3500 kg m-3"),
    ("P_d", "", "", "0.01", "1/s", "P_d", "Table 1 baseline (bold);desorption probability"), ("c", "initial_sticking_coefficient", "species=tma;kind=set_point", "0.01", "", "c", "Table 1 baseline (bold)"),
    ("N", "cycle_number", "", "250", "", "N", "Table 1 baseline (bold)"), ("d_A", "molecule_diameter", "species=tma", "600", "pm", "d_A", "Table 1 baseline footnote;6e-10 m"),
    ("d_I", "molecule_diameter", "gas=n2", "374", "pm", "d_I", "Table 1 baseline footnote;3.74e-10 m"), ("M", "molar_mass", "species=al2o3", "50", "g/mol", "M", "Table 1 baseline footnote;0.050 kg/mol, the film's formula unit"),
    ("b_film", "", "", "1", "", "b_film", "Table 1 baseline footnote"), ("b_A", "", "", "1", "", "b_A", "Table 1 baseline footnote")])
kn_base = f("s12.p2;tab1.r1c2;tab1.r2c2;tab1.r4c2;tab1.r5c2;tab1.r6c2;tab1.r7c2;tab1.r11c2", "derived", "the baseline Knudsen number is 7.6, in the transition flow regime", quantity="knudsen_number", value="7.6", data_kind="computed_by_authors", method="calculation", mentions="ref 25")
c_base = claim("s12.p1;s12.p2", "the baseline is inspired by the TMA-water process in a 500 nm PillarHall channel; with the pressures used it sits in transition flow, Kn 7.6", "asserted", supports=[kn_base], mentions="ref 18;ref 31;ref 39;ref 40;ref 45;ref 46;ref 47;ref 48")
YLI = pset("fig2.cap", [
    ("c", "initial_sticking_coefficient", "species=tma;kind=set_point", "0.01", "", "c", "Fig. 2 parameters, as Ylilammi 2018"), ("T", "deposition_temperature", "", "500", "K", "T", "Fig. 2 parameters"),
    ("p_A0", "partial_pressure", "species=tma", "100", "Pa", "p_A0", "Fig. 2 parameters"), ("M_A", "molar_mass", "species=tma", "74.9", "g/mol", "M_A", "Fig. 2 parameters;0.0749 kg/mol"),
    ("d_A", "molecule_diameter", "species=tma", "591", "pm", "d_A", "Fig. 2 parameters;5.91e-10 m"), ("p_I", "partial_pressure", "gas=n2", "300", "Pa", "p_I", "Fig. 2 parameters;printed ρ1"),
    ("M_I", "molar_mass", "gas=n2", "28", "g/mol", "M_I", "Fig. 2 parameters;0.028 kg/mol"), ("d_I", "molecule_diameter", "gas=n2", "374", "pm", "d_I", "Fig. 2 parameters;3.74e-10 m"),
    ("rho", "film_density", "", "4", "g/cm3", "ρ", "Fig. 2 parameters;4000 kg m-3"), ("gpc_sat", "saturation_growth_per_cycle", "species=tma", "0.106", "nm/cycle", "gpc_sat", "Fig. 2 parameters;1.06e-10 m"),
    ("K", "adsorption_equilibrium_constant", "species=tma", "100", "1/Pa", "K", "Fig. 2 parameters"), ("q", "saturation_density", "", "5", "nm-2", "q", "Fig. 2 parameters"),
    ("H", "feature_width", "", "0.5", "µm", "H", "Fig. 2 parameters"), ("W", "feature_extent", "", "0.1", "mm", "W", "Fig. 2 parameters")])
FMF = pset("fig6.cap;s15.p4;fig7.cap", [
    ("W", "feature_extent", "", "10", "mm", "W", "Fig. 6 and Table 3 parameters"), ("H", "feature_width", "", "0.1", "µm", "H", "Fig. 6 and Table 3 parameters"),
    ("N", "cycle_number", "", "1", "", "N", "Fig. 6 and Table 3 parameters;one cycle"), ("T", "deposition_temperature", "", "523.15", "K", "T", "Fig. 6 and Table 3 parameters"),
    ("t_1", "pulse_time", "step=reactant_A;species=tma", "2", "s", "t_1", "Fig. 6 and Table 3 parameters"), ("p_A0", "partial_pressure", "species=tma", "10", "Pa", "p_A0", "Fig. 6 and Table 3 parameters"),
    ("M_A", "molar_mass", "species=tma", "100", "g/mol", "M_A", "Fig. 6 and Table 3 parameters;0.1 kg/mol"), ("d_A", "molecule_diameter", "species=tma", "600", "pm", "d_A", "Fig. 6 and Table 3 parameters;6.0e-10 m"),
    ("M_I", "molar_mass", "gas=n2", "28", "g/mol", "M_I", "Fig. 6 and Table 3 parameters;0.028 kg/mol"), ("d_I", "molecule_diameter", "gas=n2", "374", "pm", "d_I", "Fig. 6 and Table 3 parameters;3.74e-10 m"),
    ("p_I", "partial_pressure", "gas=n2", "50", "Pa", "p_I", "Fig. 6 and Table 3 parameters"), ("q", "saturation_density", "", "4", "nm-2", "q", "Fig. 6 and Table 3 parameters"),
    ("rho", "film_density", "", "3.5", "g/cm3", "ρ", "Fig. 6 and Table 3 parameters;3500 kg m-3"), ("M", "molar_mass", "species=al2o3", "50", "g/mol", "M", "Fig. 6 and Table 3 parameters;0.050 kg/mol"),
    ("P_d", "", "", "1e-5", "1/s", "P_d", "Fig. 6 and Table 3 parameters;desorption probability"), ("c", "initial_sticking_coefficient", "species=tma;kind=set_point", "0.01", "", "c", "Fig. 6 and Table 3 parameters")])
disc = f("s15.p4", "model", "5000 discretisation points served the molar-mass and temperature series, 30 000 the sticking-coefficient series, to meet the back-extraction criterion on the y step", quantity="other", label_as_printed="discretisation points",
         value_min="5000", value_max="30000", data_kind="stated", mentions="5000–30 000 points, two series")
TAB2 = {}
for reg, H_, pA0, pi_, lab in (("fmf", "0.05", "50", "250", "Table 2 centre point, free molecular flow"), ("tf", "0.5", "500", "2500", "Table 2 centre point, transition flow")):
    TAB2[reg] = pset("s14.p6;tab2.cap", [
        ("W", "feature_extent", "", "10", "mm", "W", lab), ("H", "feature_width", "", H_, "µm", "H", lab), ("N", "cycle_number", "", "1", "", "N", lab), ("T", "deposition_temperature", "", "573.15", "K", "T", lab),
        ("t_1", "pulse_time", "step=reactant_A;species=tma", "0.1", "s", "t_1", lab), ("p_A0", "partial_pressure", "species=tma", pA0, "Pa", "p_A0", lab), ("M_A", "molar_mass", "species=tma", "100", "g/mol", "M_A", lab + ";0.1 kg/mol"),
        ("d_A", "molecule_diameter", "species=tma", "600", "pm", "d_A", lab + ";6.0e-10 m"), ("M_i", "molar_mass", "gas=n2", "28", "g/mol", "M_i", lab + ";0.028 kg/mol"), ("d_i", "molecule_diameter", "gas=n2", "400", "pm", "d_i", lab + ";4.0e-10 m"),
        ("p_i", "partial_pressure", "gas=n2", pi_, "Pa", "p_i", lab), ("q", "saturation_density", "", "4", "nm-2", "q", lab), ("rho", "film_density", "", "3.5", "g/cm3", "ρ", lab + ";3500 kg m-3"),
        ("M", "molar_mass", "species=al2o3", "50", "g/mol", "M", lab + ";0.050 kg/mol"), ("P_d", "", "", "0.01", "1/s", "P_d", lab + ";desorption probability"), ("c", "initial_sticking_coefficient", "species=tma;kind=set_point", "0.01", "", "c", lab)])
t2_p_f = f("s14.p6", "model", "Table 2, total pressure row in free molecular flow: p_i raised from 0.5 to 250 Pa at the centre-point reactant pressure", quantity="partial_pressure", qualifiers="gas=n2", value_min="0.5", value_max="250", unit="Pa", data_kind="model_input")
t2_p_t = f("s14.p6", "model", "Table 2, total pressure row in transition flow: p_i raised from 625 to 10 000 Pa at the centre-point reactant pressure", quantity="partial_pressure", qualifiers="gas=n2", value_min="625", value_max="10000", unit="Pa", data_kind="model_input")
t2_frac_f = f("s14.p6", "model", "Table 2, reactant fraction row in free molecular flow: p_A0 varied from 1 to 100 Pa at the centre-point inert pressure", quantity="partial_pressure", qualifiers="species=tma", value_min="1", value_max="100", unit="Pa", data_kind="model_input")
t2_frac_t = f("s14.p6", "model", "Table 2, reactant fraction row in transition flow: p_A0 varied from 100 to 1000 Pa at the centre-point inert pressure", quantity="partial_pressure", qualifiers="species=tma", value_min="100", value_max="1000", unit="Pa", data_kind="model_input")

# ---------------------------------------------------------------- Table 2 as claims (P54): one per parameter, regime and characteristic
T2 = [("tab2.r1", "channel height H", "feature_width", (("no_effect", "no_effect"), ("decreases", "increases"))),
      ("tab2.r2", "the initial reactant partial pressure p_A0", "partial_pressure", (("increases", "no_effect"), ("increases", "no_effect"))),
      ("tab2.r3", "the reactant pulse time t_1", "pulse_time", (("increases", "no_effect"), ("increases", "no_effect"))),
      ("tab2.r4", "the sticking coefficient c", "initial_sticking_coefficient", (("increases", "increases"), ("increases", "increases"))),
      ("tab2.r5", "the desorption probability P_d", "desorption", (("no_effect", "no_effect"), ("no_effect", "no_effect"))),
      ("tab2.r6", "the adsorption density q", "saturation_density", (("decreases", "increases"), ("decreases", "increases"))),
      ("tab2.r7", "the temperature T", "deposition_temperature", (("decreases", "no_effect"), ("decreases", "no_effect"))),
      ("tab2.r8", "the total pressure p (through the inert gas)", "process_pressure", (("no_effect", "no_effect"), ("decreases", "increases"))),
      ("tab2.r9", "the reactant fraction of the total pressure p_A0/p", "partial_pressure", (("increases", "no_effect"), ("increases", "no_effect"))),
      ("tab2.r10", "the reactant molar mass M_A", "molar_mass", (("decreases", "no_effect"), ("decreases", "increases"))),
      ("tab2.r11", "the carrier gas molar mass M_i", "molar_mass", (("no_effect", "no_effect"), ("increases", "decreases"))),
      ("tab2.r12", "the reactant molecule size d_A", "molecule_diameter", (("no_effect", "no_effect"), ("no_effect", "increases"))),
      ("tab2.r13", "the film density ρ", "film_density", (("no_effect", "decreases"), ("no_effect", "decreases")))]
WORD = {"increases": "raises", "decreases": "lowers", "no_effect": "leaves unchanged"}
T2C = []
for row, name, cause, ((xf, sf), (xt, st)) in T2:
    ev_f = f"{row}c0;{row}c1;{row}c2;{row}c3;tab2.cap"; ev_t = f"{row}c0;{row}c4;{row}c5;{row}c6;tab2.cap"
    T2C.append(claim(ev_f, f"Table 2, free molecular flow: raising {name} {WORD[xf]} the scaled half-thickness penetration depth x̃50%", "asserted", cause, "coated_aspect_ratio", xf, supports=[TAB2["fmf"].get("H")], mentions="Kn ≫ 1"))
    T2C.append(claim(ev_f, f"Table 2, free molecular flow: raising {name} {WORD[sf]} the absolute slope at x̃50%, of the scaled and of the Type 1 profile alike" if row not in ("tab2.r6", "tab2.r13") else
                     f"Table 2, free molecular flow: raising {name} {WORD[sf]} the absolute slope of the scaled profile at x̃50% but not that of the Type 1 profile", "asserted", cause, "front_slope", sf,
                     supports=[TAB2["fmf"].get("c")], mentions="Kn ≫ 1"))
    T2C.append(claim(ev_t, f"Table 2, transition flow: raising {name} {WORD[xt]} the scaled half-thickness penetration depth x̃50%", "asserted", cause, "coated_aspect_ratio", xt, supports=[TAB2["tf"].get("H")], mentions="Kn ≈ 1"))
    T2C.append(claim(ev_t, f"Table 2, transition flow: raising {name} {WORD[st]} the absolute slope at x̃50%" + (" of the scaled profile only" if row in ("tab2.r6", "tab2.r13") else ""), "asserted", cause, "front_slope", st,
                     supports=[TAB2["tf"].get("c")], mentions="Kn ≈ 1"))

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Yim et al. 2022: the Ylilammi diffusion-reaction model re-implemented; thickness-profile trends against every parameter, channel filling, flow regime, and the slope method", "", evidence="s1.h")
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


SIM_A = node(f"{K}:sim", "activity", "Model A: the Ylilammi diffusion-reaction model re-implemented in MATLAB (Eqs. 1-24) and the analysis equations (25-30)", PAPER, evidence="s3.h;s8.h;s9.p1", kind="simulation", how="stated", label_as_printed="Model A")
put(SIM_A, *M, *A_ext, gam, disc)
SIM_B = node(f"{K}:sim:modelB", "activity", "Model B: the Yanguas-Gil and Elam diffusion-reaction model solved with pdepe, the basis of the slope method", PAPER, evidence="s9.p5;s9.p6", kind="simulation", how="stated", label_as_printed="Model B")
put(SIM_B, *MB)
SET = {}
SET["base"] = node(f"{K}:sim:base", "activity", "Model A at the Table 1 baseline (a TMA-water-like process in a 500 nm channel), one parameter varied at a time: Figs. 4 and 5", SIM_A, evidence="tab1.cap;s12.p1", kind="simulation", how="stated",
                   label_as_printed="baseline set")
put(SET["base"], *BASE.values(), kn_base)
SET["yli"] = node(f"{K}:sim:yli", "activity", "Model A with the Ylilammi 2018 parameters: Fig. 2", SIM_A, evidence="fig2.cap;s5.p19", kind="simulation", how="stated", label_as_printed="Ylilammi set")
put(SET["yli"], *YLI.values())
SET["fmf"] = node(f"{K}:sim:fmf", "activity", "Model A in free molecular flow (Kn ≥ 100), one cycle: Fig. 6, Table 3 and the Fig. 7 comparison", SIM_A, evidence="fig6.cap;s15.p4;s15.p1", kind="simulation", how="stated", label_as_printed="free-molecular set")
put(SET["fmf"], *FMF.values())
SET["t2f"] = node(f"{K}:sim:tab2_fmf", "activity", "Model A at the Table 2 centre point of free molecular flow, one parameter varied at a time (Figs. S6-S15)", SIM_A, evidence="s14.p6;s14.p2", kind="simulation", how="stated",
                  label_as_printed="Table 2 free-molecular set")
put(SET["t2f"], *TAB2["fmf"].values(), t2_p_f, t2_frac_f)
SET["t2t"] = node(f"{K}:sim:tab2_tf", "activity", "Model A at the Table 2 centre point of transition flow, one parameter varied at a time (Figs. S6-S15)", SIM_A, evidence="s14.p6;s14.p2", kind="simulation", how="stated",
                  label_as_printed="Table 2 transition set")
put(SET["t2t"], *TAB2["tf"].values(), t2_p_t, t2_frac_t)
RUNS = {}


def run(rid, parent, st, ev, label, own):
    e = node(f"{K}:simrun:{rid}", "entity", st, parent, evidence=ev, how="stated", label_as_printed=label)
    put(e, *own)
    RUNS[rid] = e
    return e


# Fig. 2: the Ylilammi set at four times
for t in ("0.01", "0.02", "0.05", "0.1"):
    e = run(f"fig2:t{t}", SET["yli"], f"Model A run of Fig. 2 at t_1 = {t} s with the Ylilammi parameters", "fig2.cap;fig2a;fig2b", f"Fig. 2 run, t_1 {t} s",
            [f("fig2.cap;fig2a;fig2b", "setting", f"the Fig. 2 run's exposure time is {t} s", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value=t, unit="s", data_kind="model_input", mentions=f"t_1 = {t} s")])
    put(e, f("fig2a;fig2.cap", "model", f"Fig. 2(a): the reactant partial pressure along the channel at t_1 = {t} s", quantity="partial_pressure", qualifiers="species=tma", method="simulation", mentions=f"t_1 = {t} s;Fig. 2(a)"),
        f("fig2b;fig2.cap", "model", f"Fig. 2(b): the surface coverage along the channel at t_1 = {t} s", quantity="surface_coverage", method="simulation", mentions=f"t_1 = {t} s;Fig. 2(b)"))
# Figs. 4 and 5: the baseline run and one run per varied value
F4 = [("a", "p_A0", "partial_pressure", "species=tma", "Pa", ["50", "100", "200", "400", "800"], "100", "p_{{A0}} = {v} Pa", "tab1.r1", ["8.2", "7.6", "6.5", "5.0", "3.5"]),
      ("b", "t_1", "pulse_time", "step=reactant_A;species=tma", "s", ["0.05", "0.1", "0.2", "0.4", "0.8"], "0.1", "t_1 = {v} s", "tab1.r2", None),
      ("c", "M_A", "molar_mass", "species=tma", "g/mol", ["25", "50", "100", "200", "400"], "100", "M_A = {v} g mol^{{-1}}", "tab1.r3", ["10.7", "9.2", "7.6", "5.9", "4.5"]),
      ("d", "rho", "film_density", "", "g/cm3", ["2.5", "3", "3.5", "4", "4.5"], "3.5", "ρ = {kg} kg m^{{-3}}", "tab1.r4", None),
      ("e", "q", "saturation_density", "", "nm-2", ["1", "2", "4", "8", "10"], "4", "q = {v} nm^{{-2}}", "tab1.r5", None),
      ("f", "P_d", "", "", "1/s", ["0.01", "0.1", "1", "10", "100"], "0.01", "P_d = {v} s^{{-1}}", "tab1.r6", None),
      ("g", "c", "initial_sticking_coefficient", "species=tma;kind=set_point", "", ["0.0001", "0.001", "0.01", "0.1", "1"], "0.01", "c = {v}", "tab1.r7", None),
      ("h", "T", "deposition_temperature", "", "°C", ["100", "150", "200", "250", "300"], "250", "T = {K} K", "tab1.r8", ["5.4", "6.1", "6.8", "7.6", "8.3"]),
      ("i", "p_i", "partial_pressure", "gas=n2", "Pa", ["0.1", "250", "500", "750", "1000"], "500", "p_i = {v} Pa", "tab1.r9", ["45.2", "12.9", "7.6", "5.3", "4.1"])]
HT = {"1": "898", "0.1": "284", "0.01": "90", "0.001": "28", "0.0001": "9"}
NAME = {"p_A0": "reactant pressure", "t_1": "pulse time", "M_A": "reactant molar mass", "rho": "film density", "q": "adsorption density", "c": "sticking coefficient", "T": "temperature", "p_i": "inert gas pressure", "H": "channel height", "N": "cycle number", "P_d": "desorption probability"}


def lab(fmt, v):
    kg = str(int(float(v) * 1000)); Kk = f"{float(v) + 273.15:.2f}"
    return fmt.format(v=v, kg=kg, K=Kk)


base_labels = [lab(fmt, bv) for _, _, _, _, _, _, bv, fmt, _, _ in F4] + ["0.5", "250"]
BASE_RUN = run("base", SET["base"], "the baseline run of Model A (Table 1 bold values), the blue line of every Fig. 4 and Fig. 5 panel", "tab1.cap;" + ";".join(f"fig4{p}" for p in "abcdefghi") + ";fig5a;fig5b;fig5c;fig5d;fig4.cap;fig5.cap",
               "baseline run", [f("tab1.cap;s12.p1", "setting", "the baseline run keeps every Table 1 parameter at its bold value", data_kind="model_input", mentions=";".join(base_labels))])
put(BASE_RUN, f("fig4.cap;fig4a;fig4b;fig4c;fig4d;fig4e;fig4f;fig4g;fig4h;fig4i", "model", "Fig. 4, the solid blue line in every panel: the baseline thickness profile", quantity="film_thickness", method="simulation",
                mentions=";".join(base_labels[:9]) + ";Fig. 4"),
    f("fig5.cap;fig5a;fig5b", "model", "Fig. 5(a),(b): the baseline thickness profile (H 0.5 µm, 250 cycles), marked blue", quantity="film_thickness", method="simulation", mentions="0.5;250;Fig. 5(a);Fig. 5(b)"),
    f("fig5.cap;fig5c;fig5d", "model", "Fig. 5(c),(d): the baseline scaled profile s/N against x̃", quantity="growth_per_cycle", qualifiers="position=local", method="simulation", mentions="0.5;250;Fig. 5(c);Fig. 5(d)"),
    f("s12.p5", "derived", "the Thiele modulus of the baseline (c = 0.01) is 90", quantity="other", label_as_printed="h_T", value="90", data_kind="computed_by_authors", method="calculation"))
GRP = {}
for pan, sym, q, quals, u, vals, bv, fmt, trow, kns in F4:
    members = []
    for n, v in enumerate(vals):
        if v == bv:
            members.append(BASE_RUN); continue
        kw = dict(quantity=q or "other", label_as_printed=sym, value=v, data_kind="model_input", mentions=lab(fmt, v))
        if quals:
            kw["qualifiers"] = quals
        if u:
            kw["unit"] = u
        own = [f(f"{trow}c1;fig4.cap;fig4{pan}", "setting", f"Fig. 4({pan}) run: {sym} = {v} {u}".strip(), **kw)]
        e = run(f"fig4{pan}:{v}", SET["base"], f"Model A run of Fig. 4({pan}) with {sym} = {v} {u} and the other parameters at baseline".strip(), f"fig4.cap;fig4{pan};{trow}c1", f"Fig. 4({pan}) run, {sym} {v}", own)
        put(e, f(f"fig4{pan};fig4.cap", "model", f"Fig. 4({pan}): the thickness profile at {sym} = {v} {u}".strip(), quantity="film_thickness", method="simulation", mentions=f"{lab(fmt, v)};Fig. 4({pan})"))
        if kns:
            put(e, f(f"{trow}c2;tab1.cap", "derived", f"Table 1: the effective Knudsen number at {sym} = {v} {u} is {kns[n]}".strip(), quantity="knudsen_number", value=kns[n], data_kind="computed_by_authors", method="calculation", mentions=lab(fmt, v)))
        if pan == "g":
            put(e, f("s12.p5", "derived", f"the Thiele modulus at c = {v} is {HT[v]}", quantity="other", label_as_printed="h_T", value=HT[v], data_kind="computed_by_authors", method="calculation", mentions=f"c = {v}"))
        members.append(e)
    GRP[f"fig4{pan}"] = (q or "other", members, f"{NAME[sym]} series: Fig. 4({pan}), {sym} varied over {', '.join(vals)} {u}".strip(), f"fig4.cap;fig4{pan};{trow}c1")
for pan, sym, q, u, vals, bv, trow, kns, pfx in (("a", "H", "feature_width", "µm", ["0.1", "0.2", "0.5", "1", "2", "2.5", "4"], "0.5", "tab1.r10", ["37.8", "18.9", "7.6", "3.8", "1.9", "1.5", "0.9"], "c"),
                                                   ("b", "N", "cycle_number", "", ["5", "10", "20", "50", "100", "250", "500"], "250", "tab1.r11", None, "d")):
    members = []
    for n, v in enumerate(vals):
        if v == bv:
            members.append(BASE_RUN); continue
        kw = dict(quantity=q, label_as_printed=sym, value=v, data_kind="model_input", mentions=v)
        if u:
            kw["unit"] = u
        e = run(f"fig5{pan}:{v}", SET["base"], f"Model A run of Fig. 5({pan}) with {sym} = {v} {u} and the other parameters at baseline".strip(), f"fig5.cap;fig5{pan};fig5{pfx};{trow}c1", f"Fig. 5({pan}) run, {sym} {v}",
                [f(f"{trow}c1;fig5.cap;fig5{pan};fig5{pfx}", "setting", f"Fig. 5({pan}) run: {sym} = {v} {u}".strip(), **kw)])
        put(e, f(f"fig5{pan};fig5.cap", "model", f"Fig. 5({pan}): the thickness profile at {sym} = {v} {u}".strip(), quantity="film_thickness", method="simulation", mentions=f"{v};Fig. 5({pan})"),
            f(f"fig5{pfx};fig5.cap", "model", f"Fig. 5({pfx}): the scaled profile s/N against x̃ at {sym} = {v} {u}".strip(), quantity="growth_per_cycle", qualifiers="position=local", method="simulation", mentions=f"{v};Fig. 5({pfx})"))
        if kns:
            put(e, f(f"{trow}c2;tab1.cap", "derived", f"Table 1: the effective Knudsen number at H = {v} µm is {kns[n]}", quantity="knudsen_number", value=kns[n], data_kind="computed_by_authors", method="calculation", mentions=f"H = {v}"))
        members.append(e)
    GRP[f"fig5{pan}"] = (q, members, f"{NAME[sym]} series: Fig. 5({pan}), {sym} varied over {', '.join(vals)} {u}".strip(), f"fig5.cap;fig5{pan};fig5{pfx};{trow}c1")
o_5e = f("fig5e;fig5.cap;s13.p4", "model", "Fig. 5(e): x̃50% of the scaled profile against the channel filling fraction for the height series and the cycle series", quantity="coated_aspect_ratio", qualifiers="level=50%", method="simulation",
         mentions="Fig. 5(e)")
o_5f = f("fig5f;fig5.cap;s13.p5", "model", "Fig. 5(f): the slope at x̃50% against the channel filling fraction for both series", method="simulation", mentions="Fig. 5(f)")
slope_c = f("s13.p5", "derived", "for little filling the cycle series' slope at x̃50% settles near −0.0029 nm per unit x̃", quantity="other", label_as_printed="d(s/N)/dx̃ at x̃50%", value="-0.0029", unit="nm", data_kind="computed_by_authors", method="calculation")
kn_knee = f("s13.p5", "derived", "the knee of the height series lies at Kn = 8", quantity="knudsen_number", value="8", data_kind="computed_by_authors", method="calculation")
put(SET["base"], o_5e, o_5f, slope_c, kn_knee)
# Fig. 6 and Table 3: the free-molecular set
o_6a = f("fig6a;fig6.cap;s15.p2", "model", "Fig. 6(a): D_Kn, D_eff and D_A against the Knudsen number, varied through p_A0 from 1 to 20 480 Pa at p_A0:p_I = 1:5; above Kn 100 D_eff equals D_Kn", quantity="knudsen_number",
         value_min="1", value_max="20480", unit="", data_kind="model_input", method="simulation", mentions="Fig. 6(a);1 to 20 480 Pa, the p_A0 range")
put(SET["fmf"], o_6a)
T3 = [("T", "323.15", "0.1", "0.01", "233", "0.0300", "0.0125", "1.25", "tab3.r1"), ("T", "423.15", "0.1", "0.01", "305", "0.0301", "0.0126", "1.26", "tab3.r2"),
      ("T", "523.15", "0.1", "0.01", "378", "0.0300", "0.0125", "1.25", "tab3.r3;tab3.r8;tab3.r13"), ("T", "623.15", "0.1", "0.01", "450", "0.0300", "0.0125", "1.25", "tab3.r4"), ("T", "723.15", "0.1", "0.01", "522", "0.0300", "0.0125", "1.25", "tab3.r5"),
      ("M", "523.15", "0.025", "0.01", "537", "0.0301", "0.0126", "1.26", "tab3.r6"), ("M", "523.15", "0.05", "0.01", "462", "0.0300", "0.0125", "1.25", "tab3.r7"), ("M", "523.15", "0.2", "0.01", "295", "0.0300", "0.0125", "1.25", "tab3.r9"),
      ("M", "523.15", "0.4", "0.01", "223", "0.0300", "0.0125", "1.25", "tab3.r10"), ("c", "523.15", "0.1", "0.0001", "378", "0.0030", "0.000126", "1.26", "tab3.r11"), ("c", "523.15", "0.1", "0.001", "378", "0.0095", "0.00125", "1.25", "tab3.r12"),
      ("c", "523.15", "0.1", "0.1", "378", "0.0951", "0.126", "1.26", "tab3.r14"), ("c", "523.15", "0.1", "1", "378", "0.3004", "1.25", "1.25", "tab3.r15")]
T3RUN = {}
for ser, T_, MA, c_, kn, sl, cext, ratio, rows in T3:
    rr = rows.split(";")
    evc = lambda col: ";".join(f"{r}c{col}" for r in rr)
    rid = f"tab3:T{T_}:M{MA}:c{c_}"
    own = []
    if T_ != "523.15":
        own.append(f(evc(1) + ";fig6b", "setting", f"Table 3 run: T = {T_} K", quantity="deposition_temperature", value=T_, unit="K", data_kind="model_input", mentions=f"T = {T_} K"))
    if MA != "0.1":
        own.append(f(evc(2) + ";fig6c", "setting", f"Table 3 run: M_A = {MA} kg/mol", quantity="molar_mass", qualifiers="species=tma", value=str(float(MA) * 1000), unit="g/mol", data_kind="model_input", mentions=f"M_A = {MA} kg mol-1"))
    if c_ != "0.01":
        own.append(f(evc(3) + ";fig6d", "setting", f"Table 3 run: c = {c_}", quantity="initial_sticking_coefficient", qualifiers="species=tma;kind=set_point", value=c_, data_kind="model_input", mentions=f"c = {c_}"))
    lbl = f"Table 3 run, T {T_} K, M_A {MA} kg/mol, c {c_}"
    e = run(rid, SET["fmf"], f"Model A run of Table 3 at T = {T_} K, M_A = {MA} kg/mol, c = {c_}, one cycle in free molecular flow", "tab3.cap;" + evc(6) + ";fig6b;fig6c;fig6d", lbl, own)
    for col, sym_, val_ in ((1, "T", "523.15"), (2, "M_A", "0.1"), (3, "c", "0.01")):
        if (T_, MA, c_)[col - 1] == val_:
            FX[FMF[sym_]]["evidence"] += ";" + evc(col)
    T3RUN[rid] = (ser, e)
    put(e, f(evc(4) + ";tab3.cap", "derived", f"Table 3: Knudsen number {kn} for the run at T {T_} K, M_A {MA}, c {c_}", quantity="knudsen_number", value=kn, data_kind="computed_by_authors", method="calculation", mentions=lbl),
        f(evc(5) + ";tab3.cap", "derived", f"Table 3: slope dθ/dx̃ at θ = 1/2 of {sl} for the run at T {T_} K, M_A {MA}, c {c_}", quantity="front_slope", qualifiers="by=H;reference=assumed_saturation", value=sl, data_kind="computed_by_authors",
          method="calculation", mentions=lbl),
        f(evc(6) + ";tab3.cap", "derived", f"Table 3: the back-extracted sticking coefficient c_ext = {cext} for the run at T {T_} K, M_A {MA}, c {c_}", quantity="initial_sticking_coefficient", qualifiers="species=tma", label_as_printed="c_ext",
          value=cext, data_kind="computed_by_authors", method="calculation", mentions=lbl + ";slope method"),
        f(evc(7) + ";tab3.cap", "derived", f"Table 3: c_ext/c = {ratio} for the run at T {T_} K, M_A {MA}, c {c_}", quantity="other", label_as_printed="c_ext/c", value=ratio, data_kind="computed_by_authors", method="calculation", mentions=lbl))
BASE3 = T3RUN["tab3:T523.15:M0.1:c0.01"][1]
# Fig. 7: Model A against Model B at H = 0.5 µm
for mdl, parent in (("A", SET["fmf"]), ("B", SIM_B)):
    e = run(f"fig7:model{mdl}", parent, f"Model {mdl} run of Fig. 7: the Table 3 parameters with H = 0.5 µm, one cycle", "fig7.cap;fig7a;fig7b", f"Fig. 7 run, Model {mdl}",
            [f("fig7.cap", "setting", f"the Fig. 7 Model {mdl} run has a 0.5 µm channel", quantity="feature_width", value="0.5", unit="µm", data_kind="model_input", mentions=f"Model {mdl}")])
    put(e, f("fig7a;fig7b;fig7.cap", "model", f"Fig. 7: the surface coverage and the reactant partial pressure against x̃ from Model {mdl}", quantity="surface_coverage", method="simulation", mentions=f"Model {mdl};Fig. 7"))
for h in FMF.values():
    C.spread(h, [SET["fmf"], SIM_B], {SIM_B: "Model B"})
o_7 = f("s15.p3;s15.p5;fig7.cap;fig7b", "model", "Fig. 7(b): Model A's pressure and coverage differ visibly from Model B's in Region III, the adsorption front, where Model A's pressure drops faster", method="simulation", mentions="Fig. 7(b)")
put(SIM_A, o_7)
# claims on the Fig. 6 comparison
o_6b = f("fig6b;fig6c;fig6d;fig6.cap;s15.x1", "model", "Fig. 6(b)-(d): the back-extracted sticking coefficients (triangles) lie above the set values (circles) at every temperature, molar mass and set value", method="simulation",
         mentions="Fig. 6(b);Fig. 6(c);Fig. 6(d)")
put(SET["fmf"], o_6b)
ratio_all = f("s15.x1;tab3.cap", "derived", "the back-extracted sticking coefficients exceed the set values systematically, c_ext/c about 1.25", quantity="other", label_as_printed="c_ext/c", value="1.25", data_kind="computed_by_authors",
              method="calculation", mentions="ca. 25% higher")
put(SET["fmf"], ratio_all)
# cited and definitions
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
put(PAPER, r_p, r_kn, r_fill, r_q)
NAME_ = None
BY_TEXT = {"ALD coats almost any inorganic substrate": [r_p], "Monte Carlo methods reach beyond free molecular flow": [M[1]], "the regime comparison varied one parameter": [TAB2["fmf"]["H"], TAB2["tf"]["H"]],
           "the Ylilammi diffusion-reaction model was re-implemented": [M[0], M[18]], "in the model the reactant partial pressure is an analytic": [M[6]], "a larger molar mass of the reactant and a larger GPC": [GRP["fig4c"][1][0], GRP["fig4e"][1][0]],
           "the inert gas's molecular mass": [TAB2["tf"]["M_i"], TAB2["tf"]["d_i"]], "the slope method returns sticking coefficients": [ratio_all], "the overshoot most likely comes": [o_7, M[6]],
           "a fingerprint thickness profile needs free molecular flow": [kn_knee, slope_c], "to extract kinetic parameters from measured profiles": [ratio_all, kn_base], "the community should share": [M[18]],
           "feature-scale ALD models are ballistic": [M[1]], "the Thiele modulus, reaction rate over diffusion": [A_ext[3]], "ALD kinetics are usually described": [M[11]], "the model's microchannel is wide": [BASE["W"], BASE["H"]],
           "the reactant enters as a step": [M[6]], "Eq. (1) of Ylilammi 2018 for the collision frequency": [M[4]], "Eq. (4) of Cremers 2019 for the collision cross section": [A_ext[2]], "the Langmuir step A + * ⇌ A*": [M[11]],
           "the constant free-height simplification": [M[17]], "Fig. 2 and Fig. S2 reproduce": [RUNS["fig2:t0.1"]], "a higher reactant partial pressure and a longer pulse": [GRP["fig4a"][1][-1], GRP["fig4b"][1][-1]],
           "lighter reactant molecules penetrate deeper": [GRP["fig4c"][1][0]], "a lower film density raises the thickness": [GRP["fig4d"][1][0]], "a higher adsorption density": [GRP["fig4e"][1][-1]],
           "a high desorption probability reshapes": [GRP["fig4f"][1][-1]], "the sticking coefficient strongly shapes": [GRP["fig4g"][1][-1]], "the temperature and the inert gas pressure": [GRP["fig4h"][1][0], GRP["fig4i"][1][0]],
           "besides the sticking coefficient and the dose": [GRP["fig4c"][1][0], GRP["fig4d"][1][0], GRP["fig4e"][1][0]], "the film narrows the channel by twice the GPC": [M[17], r_fill],
           "Fig. 5(a),(b): a higher channel increases": [GRP["fig5a"][1][-1], GRP["fig5b"][1][-1]], "at constant cycles the scaled half-thickness": [o_5e], "at constant height the scaled profiles": [o_5e],
           "the slope at x̃50% settles": [slope_c, kn_knee], "to keep the profile independent of cycle number": [o_5e, kn_knee], "Table 2: the trends differ between regimes": [TAB2["fmf"]["H"], TAB2["tf"]["H"]],
           "the scaled profile and the Type 1 normalized profile show": [TAB2["fmf"]["q"], TAB2["fmf"]["rho"]], "at Kn ≥ 100 the effective diffusion coefficient": [o_6a, FMF["N"]], "Model B differs from Model A": [MB[0], M[6]],
           "the baseline is inspired by the TMA-water": [kn_base]}
for h, (stance, cause, effect, rel_, sup) in CLAIMS.items():
    st = FX[h]["statement"]
    if not sup:
        for key, val in BY_TEXT.items():
            if st.startswith(key):
                sup.extend(val); break
    FX[h].update(stance=stance, cause=cause, effect=effect, relation=rel_, links=";".join(sup))
    PARENT.setdefault(h, PAPER)
left = [r["fact_id"] for r in C.facts() if "#" in r["fact_id"] and r["fact_id"] not in PARENT and not r["parent"]]
assert not left, left
for r in C.facts():
    if r["fact_id"] in PARENT:
        r["parent"] = PARENT[r["fact_id"]]
GROUPS = [(f"{K}:grp:fig2", "series", "pulse_time", "time series of the Ylilammi set: Fig. 2, 0.01, 0.02, 0.05 and 0.1 s", "fig2.cap", c_ok2, [RUNS[f"fig2:t{t}"] for t in ("0.01", "0.02", "0.05", "0.1")])]
PUR = {"fig4a": c_dose, "fig4b": c_dose, "fig4c": c_light, "fig4d": c_rho, "fig4e": c_q, "fig4f": c_pd, "fig4g": c_c, "fig4h": c_Tp, "fig4i": c_Tp, "fig5a": c_5c, "fig5b": c_5d}
for gk, (q, members, st, ev) in GRP.items():
    if q == "other":                                                            # P_d has no quantity id: no comparison set (the runs stay)
        continue
    GROUPS.append((f"{K}:grp:{gk}", "series", q if q != "other" else "", st, ev, PUR[gk], members))
for ser, name, q in (("T", "temperature series of the slope-method comparison: Table 3, 323.15 to 723.15 K", "deposition_temperature"), ("M", "molar-mass series of the slope-method comparison: Table 3, 0.025 to 0.4 kg/mol", "molar_mass"), ("c", "sticking-coefficient series of the slope-method comparison: Table 3, 0.0001 to 1", "initial_sticking_coefficient")):
    mem = [e for rid, (s_, e) in T3RUN.items() if s_ == ser]
    mem.insert(2, BASE3) if ser != "T" else None
    GROUPS.append((f"{K}:grp:tab3_{ser}", "series", q, name, "tab3.cap;fig6.cap", c_slope, mem))
GROUPS.append((f"{K}:grp:fig7", "series", "", "Fig. 7: Model A against Model B at the same parameters", "fig7.cap", c_why, [RUNS["fig7:modelA"], RUNS["fig7:modelB"]]))
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind if varied else "replicate", varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, {})
C.qualify(K, {})
CAV = [
    ("s7.p3;s7.p4", "Model A keeps one free channel height per cycle, so each cycle's coverage thins somewhat too steeply in Region III; valid for thin films that grow little beyond x50%.", [BASE_RUN] + [RUNS[f"fig5b:{v}"] for v in ("5", "10", "20", "50", "100", "500")], "", ""),
    ("s5.p10;s15.p5", "Model A's partial pressure is an analytic approximation (Eqs. 8-9) that drops faster at the adsorption front than the numerical Model B solution; the slope method's 25 % overshoot is attributed to it.", [ratio_all] + [T3RUN[r][1] for r in T3RUN], "", ""),
    ("s12.p1", "The baseline is a TMA-water-like process with an arbitrary molar mass of 100 g/mol, not a fitted real process.", [BASE_RUN], "", ""),
    ("s6.p2", "The Langmuir step is a lumped reaction, not an elementary one.", [BASE["c"], FMF["c"], YLI["c"]], "", ""),
    ("s15.p2", "The Table 3 comparison uses one cycle; with more cycles the channel filling would lower the slope and the penetration depth and change the extracted sticking coefficient.", [ratio_all], "", ""),
    ("fig4.cap", "Fig. 4(b) is drawn over a longer distance axis than the other panels.", [GRP["fig4b"][1][-1]], "", ""),
    ("s10.p1;s15.p4", "The half-thickness point and its slope are linear interpolations between discretisation points; the point spacing was set so the y step stays under 3 % (profiles) or 1 % (back-extraction) of the range.", [slope_c, BASE3], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_slope.split(":", 1)[1]: [ratio_all.split(":", 1)[1]], c_knee.split(":", 1)[1]: [slope_c.split(":", 1)[1], kn_knee.split(":", 1)[1]]})
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
write(K, PID)
