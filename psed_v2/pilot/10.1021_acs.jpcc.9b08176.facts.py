#!/usr/bin/env python3
"""Stage 2 facts for art19 (10.1021_acs.jpcc.9b08176, Arts, Utriainen, Puurunen, Kessels, Knoops 2019, J. Phys. Chem. C: the recombination
probability r of O radicals on SiO2, TiO2, Al2O3 and HfO2 read from how far plasma ALD films penetrate PillarHall LHAR trenches; the
recombination-limited regime of the Yanguas-Gil/Elam continuum model gives the aspect ratio at PD50% as a line in ln(plasma time) with
slope 1/sqrt(3r/4)). Text, Table 1, the six equations and the captions; the Fig. 2(B) profiles and the Fig. 3 points are imported
records (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1021_acs.jpcc.9b08176.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "art19", "10.1021_acs.jpcc.9b08176"
A = "s2.p1"                                                                      # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h;s12.h;s13.h;s14.h", "heading")
NK("s1.p1;s1.p2;s1.p3;s1.p4;s3.p5;s3.p6;s3.p7;s11.p1;s11.p2;s12.p1;s12.p2;s12.p3;s13.p3", "authors, affiliations, dates, e-mail, ORCID, address")
NK("s13.p1;s13.p2", "competing-interest statement")
NK("s14.p1", "acknowledgements")
NK("s9.p1;s9.p2", "the Supporting Information notice: the model derivation is in the SI, not in this text")
NK("fig1A", "a schematic side view of the PillarHall trench with an illustrative radical density and coverage, no value")
NK("fig2A", "optical top views of the eight coated chips; the aspect ratios printed in red are the Fig. 2(B) values stated in the text")
NK("tab1.r0c0;tab1.r0c1;tab1.r0c2;tab1.r1c0;tab1.r2c0;tab1.r3c0;tab1.r4c0", "Table 1 header and material cells (the rows' values are facts of the fits and the cited works)")

# ---------------------------------------------------------------- abstract, introduction, conclusions: claims
c_limit = claim(f"abs.g1;{A};s3.p1;s7.p1", "surface recombination of plasma radicals is generally held to limit film conformality in plasma ALD, and the penetration of a film into a high-AR trench is indeed set by it", "asserted",
                "surface_recombination", "penetration_depth", "limits")
c_method = claim(f"abs.g1;{A};s3.p4;s7.p1", "film penetration into high-aspect-ratio structures gives directly the probability r with which plasma radicals recombine on the growing film", "asserted",
                 "surface_recombination", "coated_aspect_ratio", "causes")
c_matdep = claim(f"abs.g2;{A};s3.p8;s6.p3;s7.p1", "the recombination of O atoms, and with it the film conformality of plasma ALD, depends strongly on the material: SiO2 and TiO2 recombine little, Al2O3 and HfO2 much more", "asserted",
                 "surface_recombination", "coated_aspect_ratio", "causes")
c_feasible = claim(f"abs.g3;{A};s6.p3;s7.p1", "for SiO2 and TiO2 r is low enough for very demanding conformality requirements; Al2O3 and HfO2 should coat aspect ratios between 10 and 30 in acceptable cycle times", "hedged")
c_pald = claim("s3.p1", "plasma ALD extends ALD to low temperatures and more materials; SiO2 in self-aligned multiple patterning brought it into high-volume manufacturing", "asserted", mentions="ref 3;ref 4;ref 6")
c_models = claim("s3.p2;s3.p3", "Monte Carlo and continuum models describe recombination through a probability r per collision, spanning 1e-5 to 1e-1, which sets the radical dose for saturation and the aspect ratio practically reachable",
                 "asserted", "surface_recombination", "coated_aspect_ratio", "limits", mentions="ref 9;ref 10;ref 11;ref 12")
r_range = f("s3.p3", "cited", "r spans several decades, 1e-5 to 1e-1", quantity="recombination_probability", value_min="1e-5", value_max="1e-1", data_kind="cited", method="cited", mentions="ref 9")
c_rare = claim("s3.p3", "quantitative r values are barely reported and come from complex, indirect measurements, yet they are vital for predicting plasma ALD conformality", "asserted")
c_exp = claim("s4.p4;fig1.cap;s7.p1", "in the recombination-limited regime the radical density falls exponentially into the trench, so the plasma time must grow exponentially for the penetration depth to grow linearly",
              "asserted", "surface_recombination", "penetration_depth", "causes")
c_rt = claim("s4.p4;fig1.cap", "a larger r shortens the film penetration and a longer exposure t lengthens it", "asserted", "surface_recombination", "penetration_depth", "decreases")

# ---------------------------------------------------------------- the model (Sec. Modeling)
m_src = f("s4.p1", "model", "the continuum reaction-diffusion model of Yanguas-Gil and Elam for ALD on a one-dimensional high-AR structure with a constant diffusion coefficient D, detailed in the SI", mentions="ref 11;ref 13")
m_eq12 = f("eq1;eq2;s4.p1", "model", "Eqs. (1)-(2): the dimensionless evolution of the normalized gas density ñ and the coverage θ, with a reaction loss η s0 (1 − θ) ñ and a recombination loss η r ñ")
d_xi = f("s4.p2", "definition", "ξ ≡ z/L: the distance z into the structure over its total length L", term="ξ|xi")
d_L = f("s4.p2", "definition", "L is the total length of the high-AR structure", quantity="feature_depth", term="L|total structure length|structure length")
d_tau = f("s4.p2", "definition", "τ ≡ tD/L²: the exposure time made dimensionless by the diffusion time over the structure", term="τ|tau")
d_n = f("s4.p2", "definition", "ñ ≡ n/n0: the gas-phase reactant density over its value n0 at the entrance z = 0", term="ñ|n/n0")
d_theta = f("s4.p1;s4.p2", "definition", "θ, the surface coverage, is the reacted fraction of the available reaction sites", quantity="surface_coverage", term="θ|theta|surface coverage")
d_eta = f("s4.p2", "definition", "η ≡ ¼ L² (S/V) v_th / D: the collision rate with the growth surface over the diffusion rate into the structure", term="η|eta")
d_gamma = f("s4.p2", "definition", "γ ≡ V n0 A0 / S: the reactant molecules present in the structure per adsorption site", term="γ|gamma")
d_A0 = f("s4.p2", "definition", "A0 is the average effective area of an adsorption site, calculable from the growth per cycle", term="A0|A_0", mentions="ref 11;ref 15")
d_s0 = f("s4.p2", "definition", "s0, the initial sticking probability (also initial reaction probability β0), is the reactant's probability of reacting on first collision with a bare site", quantity="initial_sticking_coefficient",
         term="s0|s_0|initial sticking probability|β0|initial reaction probability")
d_r = f("s4.p2;abs.g1;s3.p3", "definition", "r, the surface recombination probability, is the chance, per collision with the growth surface, that a radical recombines", quantity="recombination_probability",
        term="r|recombination probability|surface recombination probability", definition_note="per collision with the growth surface, first-order recombination kinetics")
m_lang = f("s4.p2", "model", "the surface chemistry is simplified to an irreversible Langmuir model with first-order recombination kinetics", mentions="ref 11;ref 13;ref 14;ref 16")
m_fig1 = f("s4.p3;fig1.cap;fig1B;fig1C", "model", "Fig. 1(B),(C): density profiles and coverage outlines computed with Eqs. (1)-(2) for molecular flow in trenches of AR 2000, γ ≪ 1 and s0 = 1e-4; (B) varies r at t = 1e4 (a.u.), (C) varies t at r = 5e-5",
             method="simulation", mentions="Fig. 1")
m_ar = f("s4.p3", "model", "the Fig. 1 trenches have aspect ratio 2000", quantity="aspect_ratio", value="2000", data_kind="model_input")
m_s0 = f("s4.p3", "model", "the Fig. 1 initial sticking probability is 1e-4", quantity="initial_sticking_coefficient", qualifiers="species=o_atom", value="1e-4", data_kind="model_input")
m_r1 = f("fig1.cap;fig1C", "model", "Fig. 1(C) is computed for one recombination probability, r = 5e-5, an illustration, not a fit", mentions="Fig. 1(C);5e-5")
m_mark = f("fig1.cap", "model", "the Fig. 1 markers sit where ñ = 1/e and θ = 1/2", mentions="Fig. 1")
m_lhar = f("s4.p3;s4.p4", "model", "the computed profiles represent plasma ALD on PillarHall LHAR generation 3 and 4 trenches: a polysilicon membrane on Si pillars above a c-Si substrate, horizontal, so nondirectional radicals enter and directional ions are excluded",
           mentions="ref 13;ref 15;ref 17;ref 18;ref 19;ref 20;ref 21")
m_red = f("s4.p5;s4.p6;eq3", "model", "Eq. (3): in the recombination-limited plasma half-cycle ∂ñ/∂τ ≈ 0 and r/(s0(1 − θ)) ≫ 1, so Eq. (1) reduces to ∂²ñ/∂ξ² ≈ η r ñ; the recombination loss dominates also near saturation, θ → 1")
c_s0 = claim("s4.p5", "s0 shapes the coverage profile but has a negligible effect on how far radicals penetrate during growth", "asserted", "initial_sticking_coefficient", "penetration_depth", "no_effect", mentions="ref 11;ref 13;ref 14")
m_eq4 = f("s4.p7;eq4", "model", "Eq. (4): with ñ(0) = 1 and ñ → 0 far in, the recombination-limited density is ñ(ξ) = exp(−√(ηr) ξ)")
c_mc = claim("s4.p8", "the exponential density decrease agrees with the Monte Carlo simulations of Knoops et al.", "asserted", mentions="ref 9")
d_pd = f("s4.p8", "definition", "PD50% is the depth where the film thickness is half the entrance value", quantity="penetration_depth", qualifiers="level=50%", term="PD50%|PD^{50%}|50% thickness penetration depth",
         mentions="ref 22")
d_xi50 = f("s4.p8", "definition", "ξ50% ≡ PD50%/L: the depth where the radical dose for 50 % saturation has been reached", term="ξ50%|xi50%")
d_t50 = f("s4.p8", "definition", "t50%: the time to half saturation at the structure's entrance, where n = n0", term="t50%|t_50%|50% saturation time")
m_eq5 = f("s4.p8;eq5;s4.p9", "model", "Eq. (5): since the dose is n(ξ) t, exp(−√(ηr) ξ50%) t = t50% gives ξ50%(t) = ln(t/t50%) / √(ηr): the penetration depth grows logarithmically with t, the magnitude set by η and r")
m_mol = f("s4.p10", "model", "at the process pressure the nominal gap is in molecular flow, the mean free path far above h, so D = ⅔ v_th h, η is independent of v_th, and with S/V = 2/h, η = ¾ (L/h)²", mentions="ref 13;ref 15;ref 22")
m_eq6 = f("s4.p10;eq6;s4.p11", "model", "Eq. (6): z̃50%(t) = ln(t/t50%) / √(¾ r); plotted against ln t the slope is 1/√(¾ r), so r follows without knowing t50%, which only shifts the line")
d_z50 = f("s4.p11;s6.p4", "definition", "z̃50% ≡ PD50%/h = ξ50% L/h is the aspect ratio at the 50 % thickness penetration depth", quantity="coated_aspect_ratio", qualifiers="level=50%",
          term="z̃50%|z50%|PD50%/h|PD50% / cavity height|PD^{50%} / cavity height|aspect ratio at 50% thickness penetration depth|film penetration")
d_h = f("s4.p10;fig2.cap", "definition", "h, the nominal gap height of the PillarHall trench (also cavity height), is its limiting dimension", quantity="feature_width", term="h|gap height|nominal gap height|cavity height|gap",
        definition_note="the lateral trench's height")
d_t = f("s4.p2;s5.p1;fig3.cap", "definition", "t, the plasma exposure time, is the plasma-on time of the plasma half-cycle", quantity="pulse_time", qualifiers="step=plasma", term="t|plasma time|plasma exposure time|plasma exposure times|Plasma time (s)")
m_two = f("s4.p11", "model", "two routes to r: the slope of z̃50% against ln t over several plasma times, or one z̃50% with t50% taken from how long the plasma half-cycle needs to saturate")
m_assume = f("s4.p11;s4.p12", "model", "the analysis assumes that growth by species other than the supplied O radicals is negligible for these processes")

# ---------------------------------------------------------------- experimental details
reactor = f("s5.p1", "setting", "the depositions ran in an Oxford Instruments FlexAL, a remote inductively coupled O2/Ar plasma at 13.56 MHz", quantity="reactor", value_text="Oxford Instruments FlexAL", data_kind="stated", mentions="ref 23;13.56 MHz")
RA = {"sio2": f("s5.p1", "setting", "SiO2 precursor: SiH2(N(C2H5)2)2, BDEAS", quantity="reactant_A", value_text="bdeas", data_kind="stated"),
      "tio2": f("s5.p1", "setting", "TiO2 precursor: Ti(N(CH3)2)4, TDMAT", quantity="reactant_A", value_text="tdmat", data_kind="stated"),
      "al2o3": f("s5.p1", "setting", "Al2O3 precursor: Al(CH3)3, TMA", quantity="reactant_A", value_text="tma", data_kind="stated"),
      "hfo2": f("s5.p1", "setting", "HfO2 precursor: HfCp(N(CH3)2)3, TDMACpH", quantity="reactant_A", value_text="tdmacph", data_kind="stated")}
RB = f("s5.p1", "setting", "the coreactant is an O2/Ar plasma", quantity="reactant_B", value_text="o_atom", data_kind="stated", mentions="O2/Ar plasma")
dose = f("s5.p1", "setting", "every recipe used a precursor dose high enough that the plasma half-cycle limited the film penetration", data_kind="stated", mentions="ref 13")
fo2 = f("s5.p1", "setting", "plasma feed: 100 sccm O2", quantity="gas_flow_rate", qualifiers="gas=o2;step=plasma", value="100", unit="sccm", data_kind="stated")
far = f("s5.p1", "setting", "plasma feed: 50 sccm Ar", quantity="gas_flow_rate", qualifiers="gas=ar;step=plasma", value="50", unit="sccm", data_kind="stated")
pp = f("s5.p1", "setting", "plasma pressure 50 mTorr", quantity="process_pressure", value="50", unit="mTorr", data_kind="stated")
pw = f("s5.p1", "setting", "ICP power 600 W", quantity="plasma_power", value="600", unit="W", data_kind="stated")
Tset = f("s5.p1", "setting", "table temperature set-point 200 °C for all depositions", quantity="deposition_temperature", qualifiers="kind=set_point", value="200", unit="°C", data_kind="stated")
trange = f("s5.p1", "setting", "plasma exposure times of 3.8–120 s", quantity="pulse_time", qualifiers="step=plasma", value_min="3.8", value_max="120", unit="s", data_kind="stated")
c_short = claim("s5.p1;fig3.cap", "the shorter plasmas carry a relatively larger uncertainty from striking time and other start-up effects; a one-second uncertainty in plasma time is included", "asserted")
unc_t = f("fig3.cap", "setting", "a one second uncertainty in plasma time is assumed", quantity="pulse_time", qualifiers="step=plasma;stat=tolerance;between=runs;n=not_stated", value="1", unit="s", data_kind="stated",
          basis="instrument")
peel = f("s5.p2", "setting", "after deposition the polysilicon membrane was removed with adhesive tape for top-view diagnostics", data_kind="stated", mentions="ref 13;ref 15;ref 17;ref 18;ref 19;ref 20;ref 21")
o_dark = f("s5.p2;fig2.cap;fig2A", "observation", "Fig. 2(A): by thin-film interference the coated areas are darker; they start at the entrance (top) and reach down to the penetration depth", method="optical_microscopy", mentions="Fig. 2(A)")
c_version = claim("s5.p2", "based on previous results the PillarHall version should not affect the thickness profile", "hedged", "pillar_effect", "normalized_thickness", "no_effect")
STRUCT = f("s4.p3;s5.p2", "setting", "the test structures are PillarHall LHAR generation 4 chips (LHAR4-ADVANCED trench W90 L1020, LHAR4 small chip vS1 and vS2)", quantity="structure", value_text="pillarhall_4", data_kind="stated")
H = f("s4.p10;fig2.cap", "setting", "the nominal gap height h is 500 nm", quantity="feature_width", label_as_printed="h", value="500", unit="nm", data_kind="stated")
mfp = f("s4.p10", "derived", "at 50 mTorr the mean free path is about 0.1 mm, far above h", quantity="mean_free_path", value="0.1", unit="mm", data_kind="computed_by_authors", method="calculation", inputs=[pp], mentions="ref 22")
SUBSTR = f("s4.p3", "setting", "the trench floor is the c-Si substrate, the roof a polysilicon membrane", quantity="substrate", value_text="si", data_kind="stated")
refl = f("s5.p3", "setting", "thickness profiles were measured with a Filmtech F40-UV reflectometer", method="reflectometry", mentions="Filmtech F40-UV")
spot = f("s5.p3", "setting", "the reflectometer spot is about 10 µm", quantity="probe_resolution", value="10", unit="µm", data_kind="stated", method="reflectometry")
stage = f("s5.p3", "setting", "a motorized Filmtech mapping stage, StageBase-XY10-Auto-100 mm, resolved the profiles at 5 µm spatial resolution", quantity="other", label_as_printed="spatial resolution", value="5", unit="µm",
          data_kind="stated", method="reflectometry")
normd = f("s5.p3;fig2.cap", "setting", "the profiles are normalized by the thickness just inside the cavity", data_kind="stated", method="reflectometry")
TH = {"sio2": ("60", "400"), "tio2": ("26", "400"), "al2o3": ("39", "300"), "hfo2": ("37", "300")}
LAB = {"sio2": "SiO2", "tio2": "TiO2", "al2o3": "Al2O3", "hfo2": "HfO2"}

# ---------------------------------------------------------------- results
o_deep = f("s6.p1;fig2.cap", "observation", "Fig. 2: SiO2 and TiO2 penetrate to extremely high aspect ratios, approaching 900 with 120 s plasma half-cycles", quantity="coated_aspect_ratio", qualifiers="level=50%", value="900",
           data_kind="stated", method="reflectometry", mentions="120 s")
c_plasma_lim = claim("s6.p1", "the increase of PD50% with plasma time confirms that the plasma half-cycle limited the film penetration, for all four processes", "asserted", "surface_recombination", "penetration_depth", "limits")
AR = {}
for mat, val in (("al2o3", "80"), ("hfo2", "40")):
    AR[mat] = f("s6.p1;abs.g3;fig2.cap", "observation", f"at t = 120 s the {LAB[mat]} film reached an aspect ratio of about {val}", quantity="coated_aspect_ratio", qualifiers="level=50%", value=val, data_kind="stated",
                method="reflectometry", mentions="120 s")
c_more = claim("s6.p1", "the far shorter penetration of Al2O3 and HfO2 suggests a significantly larger effect of surface recombination", "asserted", "surface_recombination", "coated_aspect_ratio", "decreases", supports=[AR["al2o3"], AR["hfo2"]])
c_lit = claim("s6.p1;s6.p2", "the lower conformality of Al2O3 and HfO2 against SiO2 and TiO2 agrees with the literature under similar plasma ALD conditions", "asserted", mentions="ref 24;ref 25;ref 26")
l_ding_si = f("s6.p2", "cited", "Dingemans et al.: more than 95 % conformality for plasma ALD SiO2 on a trench of aspect ratio about 30", quantity="normalized_thickness", qualifiers="reference=top;species=sio2", value="0.95",
              censor=">", data_kind="cited", method="cited", mentions="ref 24;AR 30")
l_ding_al = f("s6.p2", "cited", "Dingemans et al.: about 50 % conformality for Al2O3 on the same trench", quantity="normalized_thickness", qualifiers="reference=top;species=al2o3", value="0.5", data_kind="cited", method="cited",
              mentions="ref 24;AR 30")
l_schin = f("s6.p2", "cited", "Schindler et al.: a step coverage above 90 % for TiO2 on trench-like holes of aspect ratio 30", quantity="normalized_thickness", qualifiers="reference=top;species=tio2", value="0.9", censor=">",
            data_kind="cited", method="cited", mentions="ref 25;AR 30")
l_sharma = f("s6.p2", "cited", "Sharma et al.: HfO2 conformality limited to about 70 % on a trench of aspect ratio 7.3", quantity="normalized_thickness", qualifiers="reference=top;species=hfo2", value="0.7", data_kind="cited",
             method="cited", mentions="ref 26;AR 7.3")
l_karin = f("s6.p2", "cited", "Kariniemi et al.: conformal plasma ALD HfO2 on trenches of aspect ratio 60 with a different precursor", quantity="aspect_ratio", value="60", data_kind="cited", method="cited", mentions="ref 27")
c_karin = claim("s6.p2", "a higher HfO2 conformality may be reached under other experimental conditions", "hedged", supports=[l_karin, l_sharma])
o_lin = f("s6.p4;s6.p5;fig3.cap;fig3", "model", "Fig. 3: z̃50% of SiO2 and TiO2 against ln(plasma time) is linear, as Eq. (6) expects, with very similar slopes", quantity="coated_aspect_ratio", qualifiers="level=50%",
          method="reflectometry", mentions="Fig. 3")
R = {}
R["sio2"] = f("s6.p5;tab1.r1c1;fig3.cap;abs.g2", "derived", "the fitted surface recombination probability of O on SiO2 is (6 ± 2) × 10^-5", quantity="recombination_probability", qualifiers="species=o_atom;surface=sio2", value="6e-5",
              uncertainty="2e-5", uncertainty_kind="fit", data_kind="computed_by_authors", method="calculation", mentions="SiO2;Fig. 3")
R["tio2"] = f("s6.p5;tab1.r2c1;fig3.cap;abs.g2", "derived", "the fitted surface recombination probability of O on TiO2 is (7 ± 4) × 10^-5", quantity="recombination_probability", qualifiers="species=o_atom;surface=tio2", value="7e-5",
              uncertainty="4e-5", uncertainty_kind="fit", data_kind="computed_by_authors", method="calculation", mentions="TiO2;Fig. 3")
R["al2o3"] = f("s6.p5;tab1.r3c1;abs.g3", "derived", "r for Al2O3 is estimated with Eq. (6) in the range (1–10) × 10^-3", quantity="recombination_probability", qualifiers="species=o_atom;surface=al2o3", value_min="1e-3", value_max="1e-2",
               data_kind="computed_by_authors", method="calculation", mentions="Al2O3")
R["hfo2"] = f("s6.p5;tab1.r4c1;abs.g3", "derived", "r for HfO2 is estimated with Eq. (6) in the range (0.1–10) × 10^-2", quantity="recombination_probability", qualifiers="species=o_atom;surface=hfo2", value_min="1e-3", value_max="1e-1",
              data_kind="computed_by_authors", method="calculation", mentions="HfO2")
T50 = {}
T50["al2o3"] = f("s6.p5", "cited", "t50% for the Al2O3 process is estimated between 0.2 and 2 s from the saturation curves of Dingemans et al.", quantity="other", label_as_printed="t50%", value_min="0.2", value_max="2", unit="s",
                 data_kind="cited", method="cited", mentions="ref 24")
T50["hfo2"] = f("s6.p5", "cited", "t50% for the HfO2 process is estimated between 0.2 and 8 s from the saturation curves of Sharma et al.", quantity="other", label_as_printed="t50%", value_min="0.2", value_max="8", unit="s",
                data_kind="cited", method="cited", mentions="ref 26")
T50["sio2"] = f("s6.p5", "derived", "the linear fit gives t50% = 0.25 ± 0.07 s for SiO2", quantity="other", label_as_printed="t50%", value="0.25", uncertainty="0.07", uncertainty_kind="fit", unit="s", data_kind="computed_by_authors", method="calculation")
T50["tio2"] = f("s6.p5", "derived", "the linear fit gives t50% between 0.1 and 2 s for TiO2", quantity="other", label_as_printed="t50%", value_min="0.1", value_max="2", unit="s", data_kind="computed_by_authors", method="calculation",
                basis="fit")
c_tab = claim("s6.p6;tab1.cap", "Table 1: the determined r agree well with the literature where values exist; none were found for TiO2 and HfO2, and the SiO2-type values scatter widely", "asserted", mentions="Table 1")
LIT = [("tab1.r1c2;s6.p7", "Kim and Boudart: r = (2 ± 1) × 10^-4 for O on silica", "2e-4", "1e-4", "", "", "ref 28", "sio2", "silica"),
       ("tab1.r1c2;s6.p7", "Greaves and Linnett: r = 1.6 × 10^-4 for O on SiO2", "1.6e-4", "", "", "", "ref 32", "sio2", ""),
       ("tab1.r1c2;s6.p7", "Greaves and Linnett: r = (3–5) × 10^-5 for O on Pyrex (about 81 % SiO2)", "", "", "3e-5", "5e-5", "ref 32;ref 33", "sio2", "Pyrex, ~81% SiO2"),
       ("tab1.r1c2;s6.p7", "Macko et al.: r = (4–160) × 10^-4 for O on Pyrex", "", "", "4e-4", "1.6e-2", "ref 29", "sio2", "Pyrex"),
       ("tab1.r1c2;s6.p7", "Berkowitz-Mattuck: r = (0.8–3) × 10^-5 for O on Vycor (about 96 % SiO2)", "", "", "8e-6", "3e-5", "ref 34;ref 35", "sio2", "Vycor, ~96% SiO2"),
       ("tab1.r3c2;s6.p7", "Greaves and Linnett: r = 2.1 × 10^-3 for O on Al2O3", "2.1e-3", "", "", "", "ref 32", "al2o3", "")]
LITF = []
for ev, st, v, u, lo, hi, refs, surf, note in LIT:
    kw = dict(quantity="recombination_probability", qualifiers=f"species=o_atom;surface={surf}", data_kind="cited", method="cited", mentions=refs + (";" + note if note else ""))
    if v:
        kw["value"] = v
    if u:
        kw["uncertainty"] = u; kw["uncertainty_kind"] = "literature"
    if lo:
        kw["value_min"] = lo; kw["value_max"] = hi
    LITF.append(f(ev, "cited", st, **kw))
c_spread = claim("s6.p8", "beyond measurement accuracy, temperature, pressure, surface treatment and roughness spread the literature r for silica surfaces", "asserted", mentions="ref 28;ref 29;ref 30;ref 31;ref 32")
c_merit = claim("s6.p8;s6.p9", "the method's merit is that it yields r on the surface that is actually growing during the plasma step; residual hydrogen and carbon from the precursor could still influence r", "hedged")
c_open = claim("s6.p10", "why r depends on the material is open: recombination-site density, activation energies for recombination and surface diffusion, perhaps surface acidity", "hedged", mentions="ref 28;ref 29;ref 32")

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Arts et al. 2019: O-atom recombination probabilities on SiO2, TiO2, Al2O3 and HfO2 from plasma ALD film penetration into PillarHall trenches", "", evidence="s1.h")
RECIPE = N(f"{K}:recipe", "activity", "plasma ALD in an Oxford FlexAL on PillarHall LHAR chips: O2/Ar ICP plasma 100/50 sccm, 50 mTorr, 600 W, 200 °C table, plasma 3.8–120 s", PAPER, evidence="s5.p1", kind="recipe", how="stated",
           label_as_printed="plasma ALD recipe")
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


put(RECIPE, reactor, RB, dose, fo2, far, pp, pw, Tset, trange, unc_t, peel, STRUCT, H, mfp, SUBSTR, refl, spot, stage, normd, *RA.values())
DEPS, FILMS = {}, {}
CHIPS = {("sio2", "3.8"): ("pillarhall_4", "LHAR4-ADVANCED trench W90 L1020"), ("sio2", "12"): ("pillarhall_4", "LHAR4-ADVANCED trench W90 L1020"), ("sio2", "38"): ("pillarhall_4", "LHAR4-ADVANCED trench W90 L1020"),
         ("sio2", "120"): ("pillarhall_3", "LHAR3-v1a trench W100 L5mm"), ("tio2", "12"): ("pillarhall_4", "LHAR4 small chip vS2"), ("tio2", "120"): ("pillarhall_4", "LHAR4 small chip vS1"),
         ("al2o3", "120"): ("pillarhall_4", "LHAR4-ADVANCED trench W90 L1020"), ("hfo2", "120"): ("pillarhall_4", "LHAR4 small chip vS2")}
for mat in ("sio2", "tio2", "al2o3", "hfo2"):
    th, ncyc = TH[mat]
    d = node(f"{K}:dep:{mat}", "activity", f"plasma ALD of {LAB[mat]}: {ncyc} cycles, about {th} nm just inside the cavity", RECIPE, evidence="s5.p1;s5.p3", kind="deposition", how="stated", label_as_printed=f"{LAB[mat]} plasma ALD")
    DEPS[mat] = d
    put(d, f("s5.p1;s5.p3", "setting", f"the {LAB[mat]} process deposits {LAB[mat]}", quantity="material", value_text=mat, data_kind="stated", mentions=LAB[mat]),
        f("s5.p3", "setting", f"{LAB[mat]}: {ncyc} cycles", quantity="cycle_number", value=ncyc, data_kind="stated", mentions=LAB[mat]),
        )
    THF = f("s5.p3", "observation", f"{LAB[mat]}: about {th} nm just inside the cavity, the normalization thickness", quantity="film_thickness", qualifiers="position=entrance", value=th, unit="nm", data_kind="stated",
            method="reflectometry", mentions=LAB[mat])
    first = None
    for (m2, t), (sid, chip) in CHIPS.items():
        if m2 != mat:
            continue
        e = node(f"{K}:ent:{mat}_{t.replace('.', 'p')}s", "entity", f"the {LAB[mat]} film grown with {t} s plasma steps on a {chip} chip", d, evidence="s5.p2;fig2.cap", how="stated", label_as_printed=f"{LAB[mat]}, {t} s plasma")
        FILMS[(mat, t)] = e
        own = [f("s5.p1;fig2.cap;fig2B", "setting", f"{LAB[mat]}: plasma exposure {t} s per cycle", quantity="pulse_time", qualifiers="step=plasma", value=t, unit="s", data_kind="stated", mentions=f"{LAB[mat]}, {t} s"),
               f("s5.p2", "setting", f"{LAB[mat]} {t} s: grown on the {chip} chip", quantity="structure", value_text=sid, data_kind="stated", mentions=f"{LAB[mat]}, {t} s;{chip}")]
        put(e, *own)
        put(meas(e, "reflectometry"), f("fig2B;fig2.cap", "observation", f"Fig. 2(B): the normalized thickness profile of {LAB[mat]} at {t} s plasma against distance over cavity height", quantity="normalized_thickness",
                                       qualifiers="reference=entrance", method="reflectometry", mentions=f"{LAB[mat]}, {t} s;Fig. 2(B)"))
        put(meas(e, "optical_microscopy"), f("fig2A;fig2.cap", "observation", f"Fig. 2(A): top view of the {LAB[mat]} {t} s chip after membrane removal, the coated area dark", method="optical_microscopy",
                                            mentions=f"{LAB[mat]}, {t} s;Fig. 2(A)"))
        if first is None:
            first = e
            put(meas(e, "reflectometry"), THF)
        else:
            C.spread(THF, [meas(first, "reflectometry"), meas(e, "reflectometry")], {meas(e, "reflectometry"): f"{t} s film"})
put(meas(FILMS[("sio2", "120")], "reflectometry"), o_deep)
C.spread(o_deep, [meas(FILMS[("sio2", "120")], "reflectometry"), meas(FILMS[("tio2", "120")], "reflectometry")], {meas(FILMS[("tio2", "120")], "reflectometry"): "TiO2"})
put(meas(FILMS[("al2o3", "120")], "reflectometry"), AR["al2o3"])
put(meas(FILMS[("hfo2", "120")], "reflectometry"), AR["hfo2"])
put(meas(FILMS[("sio2", "3.8")], "optical_microscopy"), o_dark)
C.spread(o_dark, [meas(FILMS[("sio2", "3.8")], "optical_microscopy")] + [meas(FILMS[k], "optical_microscopy") for k in FILMS if k != ("sio2", "3.8")], {})
# the fits: a simulation activity with one run per material
SIM = node(f"{K}:sim", "activity", "the recombination-limited model, Eqs. (1)-(6), and its fits to the measured penetration", PAPER, evidence="s4.h;s4.p1", kind="simulation", how="stated", label_as_printed="recombination-limited model")
put(SIM, m_src, m_eq12, m_lang, m_fig1, m_ar, m_s0, m_r1, m_mark, m_lhar, m_red, m_eq4, m_eq5, m_mol, m_eq6, m_two, m_assume)
FIT = {}
for mat in ("sio2", "tio2", "al2o3", "hfo2"):
    FIT[mat] = node(f"{K}:fit:{mat}", "entity", f"the Eq. (6) {'fit' if mat in ('sio2', 'tio2') else 'estimate'} for the {LAB[mat]} process", SIM, evidence="s6.p5;tab1.cap", how="stated", label_as_printed=f"{LAB[mat]} fit")
    put(FIT[mat], f("s6.p5;tab1.cap", "setting", f"the {LAB[mat]} fit concerns the {LAB[mat]} process", quantity="material", value_text=mat, data_kind="stated", mentions=LAB[mat] + " fit"), R[mat], T50[mat])
put(FIT["sio2"], f("fig3;fig3.cap", "model", "Fig. 3: the SiO2 penetration z̃50% against ln(plasma time), four points and the linear fit", quantity="coated_aspect_ratio", qualifiers="level=50%", method="calculation", mentions="SiO_{2};Fig. 3"))
put(FIT["tio2"], f("fig3;fig3.cap", "model", "Fig. 3: the TiO2 penetration z̃50% against ln(plasma time), two points and the linear fit", quantity="coated_aspect_ratio", qualifiers="level=50%", method="calculation", mentions="TiO_{2};Fig. 3"))
put(FIT["sio2"], o_lin)
C.spread(o_lin, [FIT["sio2"], FIT["tio2"]], {FIT["tio2"]: "TiO2"})
# cited works
REFS = {n: node(f"{K}:refs:{n}", "cited", f"cited work, reference {n} of the paper", PAPER, evidence=ev, label_as_printed=f"ref. {n}")
        for n, ev in (("9", "s3.p3"), ("24", "s6.p2"), ("25", "s6.p2"), ("26", "s6.p2"), ("27", "s6.p2"), ("28", "s6.p7"), ("29", "s6.p7"), ("32", "s6.p7"), ("34", "s6.p7"))}
put(REFS["9"], r_range)
put(REFS["24"], l_ding_si, l_ding_al)
put(REFS["25"], l_schin)
put(REFS["26"], l_sharma)
put(REFS["27"], l_karin)
put(REFS["28"], LITF[0])
put(REFS["32"], LITF[1], LITF[2], LITF[5])
put(REFS["29"], LITF[3])
put(REFS["34"], LITF[4])
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
BY_TEXT = {"surface recombination of plasma radicals is generally held": [m_red, o_deep, AR["al2o3"]], "film penetration into high-aspect-ratio structures gives": [m_eq6, R["sio2"], R["tio2"]],
           "the recombination of O atoms, and with it": [R["sio2"], R["tio2"], R["al2o3"], R["hfo2"]], "for SiO2 and TiO2 r is low enough": [R["sio2"], R["tio2"], R["al2o3"], R["hfo2"]],
           "plasma ALD extends ALD": [m_src] if False else [reactor], "Monte Carlo and continuum models describe": [r_range, m_src], "quantitative r values are barely reported": [c_models] if False else [r_range],
           "in the recombination-limited regime the radical density": [m_eq4, m_eq5, m_fig1], "a larger r shortens the film penetration": [m_fig1], "s0 shapes the coverage profile": [m_red],
           "the exponential density decrease agrees": [m_eq4], "the shorter plasmas carry": [unc_t, trange], "based on previous results the PillarHall version": [STRUCT],
           "the increase of PD50% with plasma time confirms": [o_deep, o_lin], "the lower conformality of Al2O3 and HfO2 against": [l_ding_si, l_ding_al, l_schin, l_sharma],
           "Table 1: the determined r agree": [R["sio2"], R["al2o3"], LITF[0], LITF[5]], "beyond measurement accuracy, temperature": LITF[:5], "the method's merit": [R["sio2"]], "why r depends on the material": [R["sio2"], R["al2o3"]]}
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
GROUPS = [(f"{K}:grp:sio2_t", "series", "pulse_time", "SiO2 plasma-time series: 3.8, 12, 38 and 120 s", "fig2.cap;fig3.cap", c_exp, [FILMS[("sio2", t)] for t in ("3.8", "12", "38", "120")]),
          (f"{K}:grp:tio2_t", "series", "pulse_time", "TiO2 plasma-time series: 12 and 120 s", "fig2.cap;fig3.cap", c_exp, [FILMS[("tio2", t)] for t in ("12", "120")]),
          (f"{K}:grp:mat", "series", "material", "the four materials at 120 s plasma: SiO2, TiO2, Al2O3 and HfO2", "fig2.cap;s6.p1", c_matdep, [FILMS[(m, "120")] for m in ("sio2", "tio2", "al2o3", "hfo2")]),
          (f"{K}:grp:fits", "series", "material", "the four r determinations compared: Table 1", "tab1.cap", c_tab, [FIT[m] for m in ("sio2", "tio2", "al2o3", "hfo2")])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s4.p2;s4.p12", "The model is an irreversible Langmuir surface chemistry with first-order recombination, and growth by species other than the supplied O radicals is neglected.", [R[m] for m in R], "", ""),
    ("s6.p5", "The Al2O3 and HfO2 values of r are rough estimates from one penetration depth each with t50% taken from literature saturation curves, not fits.", [R["al2o3"], R["hfo2"]], "", ""),
    ("s5.p1;fig3.cap", "The shorter plasma exposures carry a relatively larger uncertainty from striking time and other start-up effects; one second of uncertainty in plasma time is assumed.", [R["sio2"], R["tio2"], T50["sio2"], T50["tio2"]], "", ""),
    ("s5.p2;fig2.cap", "Different PillarHall versions were used; the 120 s SiO2 film grew in a generation-3 chip with a smaller pillar spacing, taken not to affect the profile.", [FILMS[("sio2", "120")]], "", ""),
    ("s6.p9", "The saturated surface during plasma exposure, and so r, could depend on the precursor through residual hydrogen and carbon.", [R[m] for m in R], "", ""),
    ("s5.p1", "The 200 °C is a table set-point; the four processes were compared at fixed plasma conditions, not optimized individually.", [Tset], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_matdep.split(":", 1)[1]: [R[m].split(":", 1)[1] for m in ("sio2", "tio2", "al2o3", "hfo2")], c_more.split(":", 1)[1]: [AR["al2o3"].split(":", 1)[1], AR["hfo2"].split(":", 1)[1], o_deep.split(":", 1)[1]]})
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
# P131: a claim is a triple or it is not a claim; every claim without a full triple re-typed by the one rule (facts.retype)
BG = 'background, motivation, prior art or scope'
RETYPE = {
    's3.p1#1': ('removed', BG),
    's3.p3#2': ('removed', BG),
    'abs.g3#1': ('triple', 'surface_recombination', 'limits', 'coated_aspect_ratio'),
    's6.p1#6': ('triple', 'surface_recombination', 'decreases', 'step_coverage'),
    's6.p8#1': ('triple', 'deposition_temperature;process_pressure;surface_chemistry;roughness', 'causes', 'recombination_probability'),
    's4.p8#1': ('model', 'art19:sim'),
    's6.p6#1': ('model', 'art19:sim'),
    's5.p1#14': ('duplicate', 's5.p1#27'),
    's6.p8#2': ('duplicate', 's6.p9#1'),
    's6.p2#6': ('caveat', ['s6.p5#4']),
    's6.p10#1': ('caveat', ['s6.p5#1', 's6.p5#2', 's6.p5#3', 's6.p5#4']),
}
C.retype(K, RETYPE)
write(K, PID)
