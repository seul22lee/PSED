#!/usr/bin/env python3
"""Stage 2 facts for gor03 (10.1002_cvde.200390005, Gordon, Hausmann, Kim, Shepard 2003, Chem. Vap. Deposition: a kinetic model for
step coverage by ALD in narrow holes (molecular flow, the Clausing factor, Eq. 15), tested on HfO2 from Hf(NMe2)4 and water in
elliptical holes of aspect ratio 43). Text, equations and captions only; the Fig. 3 curve is an imported record (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1002_cvde.200390005.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "gor03", "10.1002_cvde.200390005"
A = "s2.p2"                                                                     # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h", "heading")
NK("s2.p1", "author list")
NK("s2.p3", "keywords")
NK("s3.p6;s3.p7", "affiliations")
NK("s3.p8", "funding and precursor supplier")
NK("s3.p10", "outline of the paper")
NK("s10.p8", "received dates")
NK("s10.p9;s10.p10", "reference list")
NK("fig1.cap;fig1", "a drawing of the hole geometry (λ, L, p, A), no value")
NK("fig4.cap;fig4", "a schematic of the deposition system, no value")

# ---------------------------------------------------------------- abstract and introduction: the claims of the paper
c_conf = claim(f"abs.g1;{A}", "complementary self-limiting surface reactions of two vapors let ALD coat the inside of narrow features such as holes with high conformality", "asserted",
               "self_limiting_growth", "step_coverage", "causes")
c_two = claim(f"abs.g2;{A};s3.p4", "two conditions are necessary for a uniform coating in a hole: a minimum amount of each vapor (stoichiometry) and a minimum product of vapor pressure and exposure time at the hole entrance (kinetics)",
              "asserted", "exposure", "step_coverage", "requires")
c_agree = claim(f"abs.g2;{A};s9.p1", "the theory agrees with the HfO2 data: holes of the final aspect ratio are coated completely once the exposure exceeds the Eq. (15) minimum",
                "asserted", "exposure", "step_coverage", "requires")
c_scale = claim(f"abs.g3;{A};s8.p6", "the theory gives scaling laws for other aspect ratios: the required amount of precursor grows linearly with the aspect ratio, the required exposure as its square",
                "asserted", "aspect_ratio", "exposure", "increases")
ar_def = f("s3.p1;s4.p8;eq4", "definition", "the aspect ratio a of a hole is its depth times its perimeter over four times its cross-sectional area (Eq. 4); for a circular hole the length over the diameter",
           quantity="aspect_ratio", term="a|aspect ratio", definition_note="depth × perimeter / (4 × cross-sectional area), Eq. (4); length over diameter for a circular hole")
f("s3.p1", "cited", "aspect ratios of five to ten are in use in microelectronics, an order of magnitude more is expected for trench capacitors", quantity="aspect_ratio", value_min="5", value_max="10",
  data_kind="cited", method="cited", mentions="ref 1")
claim("s3.p2;s3.p3", "conformal CVD needs its rate-limiting step on the surface; ALD forces the two reactions onto the surface by supplying the reactants in alternating pulses, so it can coat particularly high aspect ratios",
      "asserted", "self_limiting_growth", "step_coverage", "causes", mentions="ref 4")
c_chem = claim("s3.p5", "the chemistry condition: each reactant must react self-limitingly, fast, completely and irreversibly on the surface left by the other, with no physisorption, no etching and no reaction with its own products; hafnium dialkylamides with water meet it",
               "asserted", "surface_chemistry", "step_coverage", "requires")
c_stoi = claim("s3.p5", "the stoichiometry condition: the dose of each reactant must cover the whole exposed area, flat surface, hole interiors and reactor walls; bulky ligands keep the saturation dose below the number of reactive sites",
               "asserted", "exposure", "step_coverage", "requires")
c_kin = claim("s3.p9", "the kinetics condition: each dose must stay at the hole entrances long enough to react with the whole interior, the rate being set by diffusive molecular flow down the hole, not by the fast surface reactions",
              "asserted", "gas_diffusion", "step_coverage", "limits")
mfp_c = f("s3.p9;s7.p2", "model", "the model treats molecular flow: the mean free path is much larger than the hole diameter", mentions="Knudsen")

# ---------------------------------------------------------------- Sec. 2: stoichiometry, saturation doses
S_hf = f("s4.p1;eq1;s6.p7", "observation", "the saturation dose of Hf(NMe2)4 in the first half-cycle is 2.5 molecules per nm² (the paper writes it per square metre)",
         quantity="saturation_density", qualifiers="species=hf_nme2_4", label_as_printed="S_Hf", value="2.5", unit="nm-2", data_kind="measured", method="rbs", mentions="S_Hf = 2.5 × 10^18")
S_def = f("s4.p5;s6.p7", "definition", "S is the saturated surface density of reactant molecules per cycle, the amount a self-limiting half-reaction can chemisorb per unit area",
          quantity="saturation_density", term="S|saturation dose|saturated surface density", definition_note="molecules chemisorbed per unit area per cycle at saturation")
eq1_m = f("eq1;s4.p1;s4.p2", "model", "Eq. (1): surface hydroxyls react with HfL4 vapor to a surface O2HfL2 species and two HL molecules, L an alkylamide ligand such as dimethylamide",
          mentions="HfL4;HL")
S_h2o = f("s4.p2;eq2", "observation", "the saturation dose of water in the second half-cycle is 5 molecules per nm²", quantity="saturation_density", qualifiers="species=h2o", label_as_printed="S_O",
          value="5", unit="nm-2", data_kind="measured", method="rbs", mentions="S_O = 5 × 10^18")
eq2_m = f("eq2;s4.p2", "model", "Eq. (2): two water molecules convert the surface O2HfL2 species to O2Hf(OH)2, releasing two HL", mentions="HL")
no_xs = f("s4.p2", "observation", "excess molecules beyond the saturation dose do not chemisorb; unreacted or physisorbed molecules are pumped away", method="rbs")
apc = f("s4.p3", "observation", "each cycle deposits 2.5 Hf atoms per nm² of HfO2, measured by RBS on the film", quantity="atoms_per_cycle", qualifiers="over=run", value="2.5", unit="nm-2", data_kind="measured", method="rbs",
        mentions="2.5 × 10^18 molecules of solid HfO2")
gpc = f("s4.p3", "derived", "the saturation dose corresponds to a thickness of 0.1 nm per cycle", quantity="growth_per_cycle", qualifiers="over=run", value="0.1", unit="nm/cycle", data_kind="computed_by_authors", method="calculation",
        inputs=[apc])
yld = f("s4.p3;s4.p4", "observation", "within the experimental accuracy the yield is 100 %: every Hf or O atom of a saturation dose ends up in the film, and RBS found no carbon or nitrogen",
        quantity="other", label_as_printed="yield", value="100", unit="%", data_kind="measured", method="rbs")
excess = f("s4.p4", "setting", "the reactant doses are set about 10 % above saturation so that the whole surface saturates",
           quantity="other", label_as_printed="excess over the saturation dose", value="10", unit="%", data_kind="stated")
area_rule = f("s4.p5;s4.p6", "model", "the amount of each reactant needed is S times the whole area to be coated: the substrate's flat surface and hole interiors, the reactor interior, and part of the substrate's back by diffusion under it; at full step coverage the hole bottoms count as flat area")
eq3_m = f("s4.p7;eq3", "model", "Eq. (3): the vertical walls of a hole take S × (depth × perimeter) = 4 × S × A_hole × a molecules per cycle", mentions="N_walls")
c_lin = claim("s4.p9;s8.p6", "the stoichiometric amount of reactant for conformal coating inside holes rises linearly with their aspect ratio", "asserted", "aspect_ratio", "exposure", "increases", supports=[eq3_m])

# ---------------------------------------------------------------- Sec. 3.1: the flat-surface kinetics
c_time = claim("s6.p1", "even a stoichiometrically sufficient amount of precursor needs a minimum time to be deposited over a patterned substrate; that time is estimated from first principles", "asserted",
               "gas_diffusion", "exposure", "requires")
c_ideal = claim("s6.p2;s6.p3", "an ideal ALD reactant has a sticking coefficient of 1 on a surface saturated with the other reactant until it reaches its own saturation coverage, then zero", "asserted",
                "initial_sticking_coefficient", "surface_coverage", "causes")
eq5_m = f("s6.p4;eq5;s6.p5", "model", "Eq. (5): the impingement flux J is P over the square root of 2π m k T, with P the precursor partial pressure, m the molecular mass, k Boltzmann's constant and T the temperature",
          mentions="ref 5;J;P;m;k;T")
f("s6.p5", "definition", "P: the precursor's partial pressure close to the surface, in pascal", quantity="partial_pressure", term="P")
f("s6.p5", "definition", "m is the molecular mass of the precursor, in kilograms", quantity="molar_mass", term="m|molecular mass", definition_note="the mass of one molecule, converted to a molar mass here")
eq6_m = f("s6.p5;eq6", "model", "Eq. (6): the time to supply a saturation dose is t = S / J", mentions="t;S;J")
def_Pt = f("s6.p6;eq7", "definition", "the exposure Pt, the product of precursor partial pressure and time, measures how much vapor a surface has seen; Eq. (7) gives the exposure that saturates a flat surface",
           quantity="exposure", term="Pt|exposure")
eq7_m = f("s6.p6;eq7", "model", "Eq. (7): the saturation exposure of a flat surface is S times the square root of 2π m k T")
m_hf = f("s6.p7", "setting", "the molecular mass of Hf(NMe2)4, taken as monomeric vapor, corresponds to a molar mass of 354 g/mol", quantity="molar_mass", qualifiers="species=hf_nme2_4", value="354", unit="g/mol",
         data_kind="stated", mentions="5.88 × 10^-25 kg")
T_calc = f("s6.p7", "setting", "the flat-surface calculation takes a substrate temperature of 200 °C", quantity="deposition_temperature", qualifiers="kind=option", value="200", unit="°C", data_kind="stated", mentions="473 K")
Pt_hf = f("s6.p7", "derived", "Eq. (7) gives a saturation exposure of 3.9 × 10^-4 Pa s for Hf(NMe2)4, about 3 Langmuir", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="Pt", value="3.9e-4", unit="Pa s",
          data_kind="computed_by_authors", method="calculation", inputs=[S_hf, m_hf, T_calc], mentions="3 × 10^-6 torr s;3 Langmuir")
Pt_hf_L = f("s6.p7", "derived", "the same saturation exposure of Hf(NMe2)4 in Langmuir", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="Pt", value="3", unit="L",
            data_kind="computed_by_authors", method="calculation", inputs=[Pt_hf])
def_L = f("s6.p7", "definition", "a Langmuir equals 10^-6 torr s; the unit is handy because fast surface reactions saturate within a few of them", quantity="exposure", term="Langmuir|L")
eqv = f("s6.p7", "model", "the Hf(NMe2)4 reaction could be completed at 1 torr in three microseconds, at 1 mtorr in three milliseconds, or at 6 mtorr in half a millisecond", method="calculation",
        mentions="1 torr;three microseconds;1 mtorr;three milliseconds;6 mtorr;0.5 ms")
Pt_h2o = f("s6.p7", "observation", "the saturation exposure of water on a surface saturated with hafnium dimethylamide was found to be 1.3 Langmuir", quantity="exposure", qualifiers="species=h2o", label_as_printed="Pt",
           value="1.3", unit="L", data_kind="measured", method="rbs")
c_lower = claim("s6.p8", "the calculated exposures assume a reaction probability of 1; a real reaction needs more, so they are lower limits", "asserted", "initial_sticking_coefficient", "exposure", "decreases")
s_hf = f("s6.p9", "cited", "hafnium dimethylamide reacts on a water-saturated surface with a probability of at least 7 %, a quartz-crystal-microbalance estimate (unpublished)", quantity="initial_sticking_coefficient",
         qualifiers="species=hf_nme2_4", label_as_printed="reaction probability", value="0.07", censor=">", data_kind="cited", method="cited", mentions="ref 6")
Pt_max = f("s6.p9;s6.p10", "derived", "so at most about 43 Langmuir (3 divided by 0.07) saturate the reaction on a flat surface; the true value lies between 3 and 43 Langmuir", quantity="exposure",
           qualifiers="species=hf_nme2_4", label_as_printed="Pt", value="43", censor="<", unit="L", data_kind="computed_by_authors", method="calculation", inputs=[Pt_hf_L, s_hf])
c_fast = claim("s6.p10", "wherever the saturation exposure lies in that range, the Hf(NMe2)4 reaction is extremely fast", "asserted", "initial_sticking_coefficient", "exposure", "decreases", supports=[Pt_max])
c_reactor = claim("s6.p11", "diffusion and convection within the reactor volume lengthen the exposure time needed on a flat surface; reactor-scale modelling is needed for those delays", "hedged",
                  "gas_diffusion", "exposure", "increases")

# ---------------------------------------------------------------- Sec. 3.2: the hole model
a_nodep = f("s7.p1", "model", "assumption: no depletion of either precursor just outside the hole (high concentration, fast gas-phase diffusion in the reactor, rapid flow over the surface); the samples sat near the vapor entrance")
a_dep2 = f("s7.p1", "model", "where depletion matters, a conservative estimate uses the vapor concentration left after the reaction on all surfaces is complete")
a_molflow = f("s7.p2", "model", "assumption: molecular flow in the hole (no gas-phase collisions), realistic for sub-micrometre holes at about 1 torr; molecules hitting a saturated surface do not physisorb and re-emit by the cosine law; by-products neither re-adsorb nor etch",
              mentions="1 torr;cosine law")
front = f("s7.p3", "model", "the flat surface saturates first, then the hole coats from the top down: molecules diffuse along the saturated upper part and react on their first collision with the unsaturated lower part")
eq8_m = f("s7.p4;s7.p5;eq8;s7.p6;s7.p7", "model", "Eq. (8): the coated upper part of depth λ acts as a pipe to the reactive lower part; the flux is reduced by the Clausing factor CF = 1 / (1 + 3λp / 16A), which for a circular hole of diameter d is 1 / (1 + 3λ/4d)",
          mentions="ref 7;Clausing factor;CF;λ;p;A;d")
def_lam = f("s7.p6", "definition", "λ: how far down from the entrance the hole is already saturated with the reactant", quantity="penetration_depth", term="λ", definition_note="the saturated (coated) length from the entrance at a moment of the exposure")
eq9_m = f("s7.p7;eq9", "model", "Eq. (9): the flux at depth λ is the flat-surface flux divided by (1 + 3λp / 16A)")
eq10_m = f("s7.p8;eq10", "model", "Eq. (10): coating a further length dλ takes a time dt = S p dλ / (J A_hole), the flux falling as the coated length grows")
eq12_m = f("s7.p9;eq11;eq12", "model", "Eqs. (11)-(12): integrating to the time the front reaches the bottom (λ = L) gives t = S √(2πmkT) (p/A_hole) (L + 3pL² / 32A_hole)")
eq13_m = f("s7.p10;eq13", "model", "Eq. (13): the exposure to coat the side walls is the flat-surface exposure times (4a + 3a²/2)")
eq14_m = f("s7.p11;eq14", "model", "Eq. (14): the bottom is coated after the walls, with the flux of Eq. (9) at λ = L; its exposure is the flat-surface exposure times (1 + 3a/4)")
eq15_m = f("s7.p12;eq15;s7.p13", "model", "Eq. (15): the total exposure for a complete coating is the flat-surface exposure times (1 + 19a/4 + 3a²/2)")
fac43 = f("s7.p13", "derived", "a hole of aspect ratio 43 needs an exposure 3000 times that of a flat surface", quantity="other", label_as_printed="exposure factor 1 + 19a/4 + 3a²/2", value="3000",
          data_kind="computed_by_authors", method="calculation", inputs=[eq15_m], mentions="aspect ratio 43")
Pt_43 = f("s7.p13;s8.p1", "derived", "with 3 Langmuir for the flat surface, a hole of aspect ratio 43 needs 9 × 10^3 Langmuir", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="Pt", value="9000", unit="L",
          data_kind="computed_by_authors", method="calculation", inputs=[fac43, Pt_hf_L], mentions="9 × 10^3 Langmuir")
c_final = claim("s7.p14", "the aspect ratio grows as the film narrows the hole, so the exposure criterion has to hold for the coated hole's final aspect ratio", "asserted", "film_thickness", "aspect_ratio", "increases")
c_sq = claim("s8.p6", "for large aspect ratios the required exposure grows with the square of the aspect ratio while the required amount of precursor grows linearly", "asserted", "aspect_ratio", "exposure", "increases",
             supports=[eq15_m, eq3_m])
fig3_m = f("fig3.cap;s8.p6;fig3", "model", "Fig. 3 plots the exposure of Eq. (15) needed for holes over the plotted range of aspect ratios", quantity="exposure", method="calculation", mentions="Fig. 3;Equation 15;aspect ratios 1 to 2000")

# ---------------------------------------------------------------- Sec. 4 and 6: the experiments
MAT = f("s8.p1;abs.g2;s2.p3", "setting", "the film material is hafnium dioxide", quantity="material", value_text="hfo2", data_kind="stated")
RA = f("s8.p1;s10.p4;abs.g2", "setting", "reactant A is tetrakis(dimethylamido)hafnium vapor", quantity="reactant_A", value_text="hf_nme2_4", data_kind="stated", mentions="Hf(NMe2)4;hafnium dimethylamide")
RB = f("s8.p1;s10.p3;abs.g2", "setting", "reactant B is water vapor", quantity="reactant_B", value_text="h2o", data_kind="stated")
STRUCT = f("s8.p1;s10.p7", "setting", "the test structure: elliptical holes etched in silicon", quantity="structure", value_text="etched_hole_array", data_kind="stated")
SUBSTR = f("s10.p7", "setting", "the holes are etched in silicon", quantity="substrate", value_text="si", data_kind="stated")
hole_L = f("s8.p1;s10.p7", "setting", "the holes are 7.3 µm deep", quantity="feature_depth", label_as_printed="L", value="7.3", unit="µm", data_kind="stated")
hole_w1 = f("s8.p1;s10.p7", "setting", "the elliptical cross section has a major axis of about 0.30 µm", quantity="feature_extent", label_as_printed="major axis", value="0.30", unit="µm", data_kind="stated")
hole_w2 = f("s8.p1;s10.p7", "setting", "the minor axis of the elliptical cross section is about 0.17 µm", quantity="feature_width", label_as_printed="minor axis", value="0.17", unit="µm", data_kind="stated")
ar_i = f("s8.p1", "derived", "the as-etched geometry gives an aspect ratio of 36", quantity="aspect_ratio", qualifiers="stage=initial", label_as_printed="a", value="36", data_kind="computed_by_authors", method="calculation",
         inputs=[hole_L, hole_w1, hole_w2])
th25 = f("s8.p1", "setting", "the films of the step-coverage test are 25 nm thick", quantity="film_thickness", qualifiers="kind=target", value="25", unit="nm", data_kind="stated")
w_f1 = f("s8.p1", "derived", "after 25 nm of HfO2 the inside major axis is about 0.25 µm", quantity="feature_extent", qualifiers="stage=final", value="0.25", unit="µm", data_kind="computed_by_authors", method="calculation", inputs=[hole_w1, th25])
w_f2 = f("s8.p1", "derived", "after 25 nm of HfO2 the inside minor axis is about 0.12 µm", quantity="feature_width", qualifiers="stage=final", value="0.12", unit="µm", data_kind="computed_by_authors", method="calculation", inputs=[hole_w2, th25])
ar_f = f("s8.p1;abs.g2;s9.p1", "derived", "once coated, the holes have an aspect ratio of 43, the value that sets the exposure criterion", quantity="aspect_ratio", qualifiers="stage=final", label_as_printed="a", value="43", data_kind="computed_by_authors",
         method="calculation", inputs=[hole_L, w_f1, w_f2], mentions="9 × 10^3 Langmuir")
c_above = claim("s8.p2;s9.p1", "HfO2 coatings made with exposures above the Eq. (15) minimum for the final aspect ratio had 100 % step coverage, in agreement with the calculation", "asserted",
                "exposure", "step_coverage", "increases", supports=[Pt_43, ar_f])
c_below = claim("s8.p4", "exposures below the minimum gave incomplete step coverage", "asserted", "exposure", "step_coverage", "increases", supports=[Pt_43])
# the three coated runs of Fig. 2 and the uncoated hole
E30 = f("s8.p3;fig2.cap", "setting", "the fully coated hole: 30 × 10^3 Langmuir of Hf precursor exposure in each cycle", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="exposure", value="30000", unit="L",
        data_kind="stated", mentions="30 × 10^3 Langmuir")
N30 = f("s8.p3;fig2.cap", "setting", "the fully coated hole: 250 cycles", quantity="cycle_number", value="250", data_kind="stated", mentions="30 × 10^3 Langmuir run")
sc30 = f("s8.p3;fig2;fig2.cap", "observation", "Fig. 2: two complete holes with 100 % step coverage, the film a light band of uniform thickness in the top and bottom close-ups", quantity="step_coverage", value="100", unit="%",
         data_kind="measured", method="sem", mentions="Fig. 2")
th30 = f("s8.p3;fig2", "observation", "the film in the fully coated holes is 26 nm thick, uniform from top to bottom", quantity="film_thickness", qualifiers="position=sidewall", value="26", unit="nm", data_kind="measured", method="sem")
E4 = f("s8.p5;fig2.cap", "setting", "the three-quarter-coated holes: 4 × 10^3 Langmuir per cycle", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="exposure", value="4000", unit="L", data_kind="stated",
       mentions="4 × 10^3 Langmuir")
N4 = f("s8.p5;fig2.cap", "setting", "the three-quarter-coated holes: 250 cycles", quantity="cycle_number", value="250", data_kind="stated", mentions="4 × 10^3 Langmuir run")
sc4 = f("s8.p5;fig2", "observation", "with 4 × 10^3 Langmuir per cycle the film covers roughly the upper three quarters of each hole", quantity="fill_fraction", label_as_printed="coated length fraction", value="75", unit="%",
        data_kind="measured", method="sem", mentions="4 × 10^3 Langmuir")
E2 = f("s8.p5;fig2.cap", "setting", "the top-quarter-coated holes: 2 × 10^3 Langmuir per cycle", quantity="exposure", qualifiers="species=hf_nme2_4", label_as_printed="exposure", value="2000", unit="L", data_kind="stated",
       mentions="2 × 10^3 Langmuir")
N2 = f("s8.p5;fig2.cap", "setting", "the top-quarter-coated holes: 350 cycles", quantity="cycle_number", value="350", data_kind="stated")
sc2 = f("s8.p5;fig2", "observation", "with 2 × 10^3 Langmuir per cycle only the upper quarter of each hole carries film", quantity="fill_fraction", label_as_printed="coated length fraction", value="25", unit="%",
        data_kind="measured", method="sem", mentions="2 × 10^3 Langmuir")
unc_hole = f("s8.p4;s8.p5;fig2", "observation", "an uncoated hole is shown for comparison; the thin light line along its edges is an imaging artefact of the electron microscope", method="sem")
# the reactor and the recipe (Sec. 6)
reactor = f("s10.p1;fig4.cap", "setting", "a flow reactor: a stainless steel tube in a tube furnace, precursors and nitrogen in through a bored flange at one end, pumped at the other by a rotary vane pump",
            quantity="reactor", value_text="Harvard flow tube reactor", data_kind="stated", mentions="Fig. 4")
rtype = f("s10.p1;s10.p5", "setting", "the reactor runs as a flow-type reactor with the pump maintaining 0.2 torr", quantity="reactor_type", value_text="flow_type", data_kind="stated")
tube_L = f("s10.p1", "setting", "the reactor tube is 76 cm long", quantity="other", label_as_printed="reactor tube length", value="76", unit="cm", data_kind="stated")
tube_d = f("s10.p1", "setting", "the reactor tube is 3.7 cm in diameter", quantity="other", label_as_printed="reactor tube diameter", value="3.7", unit="cm", data_kind="stated")
zone = f("s10.p2", "setting", "the reaction zone, the heated zone of the furnace, is 46 cm long; both precursors enter at its start and pass a static mixer before the substrate holder",
         quantity="other", label_as_printed="reaction zone length", value="46", unit="cm", data_kind="stated")
area = f("s10.p2", "setting", "the exposed area in the reaction zone (reactor interior, static mixer, the half-round aluminium substrate holder and the substrates) is 944 cm²",
         quantity="other", label_as_printed="exposed reactor area", value="944", unit="cm2", data_kind="stated")
h2o_src = f("s10.p3", "setting", "water vapor enters through a three-way GC valve and a 0.04 mm bore feed-through; the valve switches between a nitrogen purge state and a water dose state",
            quantity="other", label_as_printed="feed-through bore", value="0.04", unit="mm", data_kind="stated")
h2o_T = f("s10.p3", "setting", "the water was kept at room temperature", quantity="source_temperature", qualifiers="species=h2o", value_text="room temperature", data_kind="stated")
h2o_p = f("s10.p3", "setting", "the water vapor pressure was about 24 torr", quantity="partial_pressure", qualifiers="species=h2o", value="24", unit="Torr", data_kind="stated")
h2o_t = f("s10.p3", "setting", "a 0.5 s dose state supplies at least one micromole of water", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="0.5", unit="s", data_kind="stated", mentions="1 µmol")
h2o_mol = f("s10.p3", "setting", "the water dose, set by its time, is twice the metal precursor dose in moles", quantity="other", label_as_printed="water dose over metal dose", value="2", data_kind="stated")
dose_V = f("s10.p4", "setting", "a 10 mL volume of metal amide vapor is charged from the reservoir through a fill valve and emptied into the reactor through an empty valve",
           quantity="other", label_as_printed="precursor dose volume", value="10", unit="mL", data_kind="stated", mentions="V")
src_p = f("s10.p4", "setting", "the precursor assembly is heated so that the precursor vapor pressure is at least 1.0 torr", quantity="partial_pressure", qualifiers="species=hf_nme2_4", value="1.0", censor=">", unit="Torr",
          data_kind="stated")
src_T = f("s10.p4", "setting", "the vaporization temperature of tetrakis(dimethylamido)hafnium was 60 °C", quantity="source_temperature", qualifiers="species=hf_nme2_4", value="60", unit="°C", data_kind="stated")
fill_t = f("s10.p4", "setting", "the fill valve opens for one second, then the empty valve for one second, which lets most of the dose into the reactor", quantity="pulse_time", qualifiers="step=reactant_A;species=hf_nme2_4",
           value="1", unit="s", data_kind="stated")
dose_mol = f("s10.p4", "setting", "the metal precursor dose was set between 1 and 10 µmol through the oven temperature", quantity="other", label_as_printed="metal precursor dose", value_min="1", value_max="10",
             unit="µmol", data_kind="stated")
n2 = f("s10.p4;s10.p5;s10.p6", "setting", "nitrogen flows constantly, directed at the outlet of the empty valve", quantity="carrier_gas", value_text="n2", data_kind="stated")
flow = f("s10.p5", "setting", "the total nitrogen flow was 20 sccm", quantity="gas_flow_rate", qualifiers="gas=n2", value="20", unit="sccm", data_kind="stated")
ptot = f("s10.p5", "setting", "the reactor pressure was 0.2 torr", quantity="process_pressure", value="0.2", unit="Torr", data_kind="stated")
Tdep = f("s10.p5", "setting", "the deposition temperature was 150 °C", quantity="deposition_temperature", value="150", unit="°C", data_kind="stated")
purgeA = f("s10.p5", "setting", "at least five seconds of purging after the metal precursor dose", quantity="purge_time", qualifiers="step=purge_A", value="5", censor=">", unit="s", data_kind="stated")
purgeB = f("s10.p5", "setting", "at least five seconds of purging after the water dose", quantity="purge_time", qualifiers="step=purge_B", value="5", censor=">", unit="s", data_kind="stated")
cyc_def = f("s10.p5;s10.p6", "definition", "one ALD cycle is one metal precursor dose, a purge, one water dose and a purge, the nitrogen flow constant throughout and no precursor entering during a purge",
            term="ALD reaction cycle")
sem_i = f("s10.p7", "setting", "cross sections were imaged by SEM in an FEI Strata DB235 dual-beam focused-ion-beam system, a field-emission SEM with a focused ion beam", method="sem", mentions="FEI Strata DB235")
sem_c = f("s10.p7", "setting", "samples were cleaved just before loading to keep the cross section fresh; images were taken in charge-reduction mode with the grounded through-lens detector", method="sem",
          mentions="TLD-C")
sem_e = f("s10.p7", "setting", "the electron beam energy was 3 to 5 keV for most specimens", quantity="other", label_as_printed="SEM beam energy", value_min="3", value_max="5", unit="keV", data_kind="stated", method="sem")
# the cited reviews and uses
f("s3.p1", "cited", "conformal coatings reduce pore sizes in filtration and gas-separation systems in a controlled way", data_kind="cited", method="cited", mentions="ref 2")
f("s3.p1", "cited", "conformal coating spreads catalysts over high-surface-area supports", data_kind="cited", method="cited", mentions="ref 3")
f("s6.p4", "cited", "the impingement flux of kinetic theory, Eq. (5), is textbook physical chemistry", data_kind="cited", method="cited", mentions="ref 5")
f("s7.p5", "cited", "the Clausing factor of Eq. (8) comes from the vacuum-science literature on molecular flow in pipes", data_kind="cited", method="cited", mentions="ref 7")

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Gordon et al. 2003: a kinetic model for step coverage by ALD in narrow holes, tested on HfO2 in holes of aspect ratio 43", "", evidence="s2.h")
RECIPE = N(f"{K}:recipe", "activity", "HfO2 ALD from Hf(NMe2)4 and water in the flow-tube reactor at 150 °C", PAPER, evidence="s10.p1;s10.p5", kind="recipe", how="stated", label_as_printed="HfO2 recipe")
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


put(RECIPE, MAT, RA, RB, STRUCT, SUBSTR, reactor, rtype, tube_L, tube_d, zone, area, h2o_src, h2o_T, h2o_p, h2o_t, h2o_mol, dose_V, src_p, src_T, fill_t, dose_mol, n2, flow, ptot, Tdep, purgeA, purgeB,
    cyc_def, excess, eq1_m, eq2_m, mfp_c)
# the input entity: the patterned substrate with its holes (a via_hole structure)
HOLES = node(f"{K}:ent:holes", "entity", "the patterned silicon substrate with elliptical holes 0.17 by 0.30 µm, 7.3 µm deep", RECIPE, evidence="s8.p1;s10.p7", how="stated", label_as_printed="etched holes in Si")
put(HOLES, hole_L, hole_w1, hole_w2, ar_i, w_f1, w_f2, ar_f)
# the three coated runs of Fig. 2 (the exposure series)
SPEC = {}
for tag, lab, ev, sets in (("30k", "30 × 10^3 Langmuir, 250 cycles", "s8.p3;fig2.cap", [E30, N30]), ("4k", "4 × 10^3 Langmuir, 250 cycles", "s8.p5;fig2.cap", [E4, N4]),
                           ("2k", "2 × 10^3 Langmuir, 350 cycles", "s8.p5;fig2.cap", [E2, N2])):
    did = node(f"{K}:dep:{tag}", "activity", f"HfO2 ALD run at {lab}", RECIPE, evidence=ev, kind="deposition", how="stated", label_as_printed=f"run {lab}", inputs=HOLES)
    put(did, *sets)
    SPEC[tag] = node(f"{K}:ent:{tag}", "entity", f"the coated holes of the {lab} run", did, evidence=ev, how="stated", label_as_printed=f"holes, {lab}")
put(meas(SPEC["30k"], "sem"), sc30, th30, sem_i, sem_c, sem_e)
put(meas(SPEC["4k"], "sem"), sc4)
put(meas(SPEC["2k"], "sem"), sc2)
put(meas(HOLES, "sem", order="0"), unc_hole)
for h in (sem_i, sem_c, sem_e):                                                 # the SEM settings hold for every cross section imaged
    C.spread(h, [meas(SPEC["30k"], "sem"), meas(SPEC["4k"], "sem"), meas(SPEC["2k"], "sem"), meas(HOLES, "sem")], {meas(SPEC["4k"], "sem"): "SEM, 4k run", meas(SPEC["2k"], "sem"): "SEM, 2k run", meas(HOLES, "sem"): "SEM, uncoated"})
# the flat-surface measurements (RBS, water saturation): a planar deposition of the same recipe
FLAT_DEP = node(f"{K}:dep:flat", "activity", "HfO2 ALD on flat substrates, the saturation doses measured by RBS", RECIPE, evidence="s4.p1;s4.p3", kind="deposition", how="inferred", label_as_printed="flat-surface runs")
FLAT = node(f"{K}:ent:flat", "entity", "HfO2 films on flat surfaces used for the saturation-dose and yield measurements", FLAT_DEP, evidence="s4.p3", how="inferred", label_as_printed="flat HfO2 film")
put(meas(FLAT, "rbs"), S_hf, S_h2o, apc, gpc, yld, Pt_h2o, no_xs)
put(FLAT_DEP, th25)
# the model: a simulation activity with one model-run entity (the Fig. 3 prediction) and the flat-surface calculation as its inputs
SIM = node(f"{K}:sim", "activity", "the kinetic model of Secs. 2-3: stoichiometry and molecular-flow exposure (Eqs. 3-15)", PAPER, evidence="s5.h;s7.h", kind="simulation", how="stated", label_as_printed="kinetic model")
put(SIM, eq3_m, area_rule, eq5_m, eq6_m, eq7_m, eq8_m, eq9_m, eq10_m, eq12_m, eq13_m, eq14_m, eq15_m, a_nodep, a_dep2, a_molflow, front, m_hf, T_calc, Pt_hf, Pt_hf_L, Pt_max, s_hf, eqv)
RUN3 = node(f"{K}:simrun:fig3", "entity", "the Eq. (15) prediction plotted in Fig. 3: exposure against aspect ratio 1 to 2000", SIM, evidence="fig3.cap;s8.p6", how="stated", label_as_printed="Fig. 3 prediction")
put(RUN3, fig3_m, fac43, Pt_43)
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
# claims under the paper, their supports as links
BY_TEXT = {"two conditions are necessary": [eq15_m, eq3_m], "the theory agrees with the HfO2 data": [sc30, sc4, sc2, Pt_43], "the theory gives scaling laws": [eq15_m, eq3_m], "complementary self-limiting surface reactions": [sc30], "even a stoichiometrically sufficient amount": [eq6_m, eq7_m],
           "conformal CVD needs its rate-limiting step": [mfp_c], "the chemistry condition": [eq1_m, eq2_m], "the stoichiometry condition": [area_rule, S_def], "the kinetics condition": [front, eq8_m],
           "an ideal ALD reactant has a sticking coefficient": [eq7_m], "the calculated exposures assume a reaction probability": [Pt_hf_L, s_hf],
           "diffusion and convection within the reactor volume": [eq7_m], "the aspect ratio grows as the film narrows": [ar_i, ar_f]}
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
        m = _re.search(r"ref ?(\d+)", r["mentions"])
        PARENT[r["fact_id"]] = f"{K}:refs:{m.group(1)}" if m else PAPER
left = [r["fact_id"] for r in C.facts() if "#" in r["fact_id"] and r["fact_id"] not in PARENT and not r["parent"]]
assert not left, left
for ref in sorted({p for p in PARENT.values() if ":refs:" in p}, key=lambda x: int(x.rsplit(":", 1)[1])):
    kids = [x for x in C.facts() if PARENT.get(x["fact_id"]) == ref]
    N(ref, "cited", f"cited work, reference {ref.rsplit(':', 1)[1]} of the paper", PAPER, evidence=";".join(dict.fromkeys(x["evidence"].split(";")[0] for x in kids)), label_as_printed=f"ref. {ref.rsplit(':', 1)[1]}")
for r in C.facts():
    if r["fact_id"] in PARENT:
        r["parent"] = PARENT[r["fact_id"]]
GROUPS = [(f"{K}:grp:exposure", "series", "exposure;cycle_number", "the Fig. 2 exposure series: three Hf precursor exposures per cycle in the same holes", "s8.p2;fig2.cap", c_above, [SPEC["30k"], SPEC["4k"], SPEC["2k"]])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed="Fig. 2 exposure series", qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s7.p1", "The model neglects precursor depletion outside the hole; the samples sat near the vapor entrance, and where depletion matters the post-reaction concentration is the conservative estimate.", [eq15_m, fig3_m], "", ""),
    ("s6.p8", "The calculated saturation exposures assume a reaction probability of 1 and are lower limits; the real exposure is higher by the inverse of the reaction probability.", [Pt_hf], "", ""),
    ("s6.p9;s6.p10", "The 7 % reaction probability is a lower bound set by the size of the microbalance sensor; the true saturation exposure lies anywhere between 3 and 43 Langmuir.", [s_hf], "", ""),
    ("s7.p14", "The minimum exposure is calculated for the final aspect ratio of the narrowed, coated hole, not the as-etched one.", [Pt_43, ar_f], "", ""),
    ("s8.p5", "The thin light line along the edges of the uncoated holes is an imaging artefact of the electron microscope, not a film.", [unc_hole], "", ""),
    ("s6.p7", "The molecular mass of Hf(NMe2)4 assumes a monomeric vapor.", [m_hf], "", ""),
    ("s6.p7;s10.p5", "The flat-surface exposure is evaluated at 200 °C while the depositions ran at 150 °C.", [T_calc], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_above.split(":", 1)[1]: [Pt_43.split(":", 1)[1], E30.split(":", 1)[1]], c_below.split(":", 1)[1]: [E4.split(":", 1)[1], E2.split(":", 1)[1]],
            c_lower.split(":", 1)[1]: [s_hf.split(":", 1)[1]], c_fast.split(":", 1)[1]: [Pt_max.split(":", 1)[1]]})
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
C.retype(K, {})                                                         # P131: every claim already carries a full triple
write(K, PID)
