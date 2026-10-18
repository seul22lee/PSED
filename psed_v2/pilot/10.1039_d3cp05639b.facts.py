#!/usr/bin/env python3
"""Stage 2 facts for hei24 (10.1039_d3cp05639b, Heikkinen, Lehtonen, Puurunen 2024, PCCP: a diffusion-reaction model of ALD in a porous
particle with a shape factor for slab, cylinder and sphere geometries; the penetration depth r(θ=1/2) against particle radius, exposure,
porosity/tortuosity, reactant molar mass, areal site density, surface-to-pore-volume ratio, sticking probability, pore diameter, specific
surface area and temperature, with a baseline inspired by TMA/water on a mesoporous catalyst support).
Text, Tables 1-2, the symbol list, the 13 equations and the captions; every curve is an imported record (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1039_d3cp05639b.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "hei24", "10.1039_d3cp05639b"


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK(";".join(f"s{i}.h" for i in range(1, 17)), "heading")
NK("s0.p1;s1.p1;s1.p2;s1.p3;s1.p4;s2.p4;s2.p5;s2.p6", "front matter, authors, affiliations, dates, footnote mark")
NK("s14.p1;s15.p1;s16.p1", "author contributions, conflicts, acknowledgements")
NK("s4.p12;s4.p13;s4.p14", "the geometry label of the equation that follows")
NK("s5.p3", "a table footnote mark: the bold baseline is the 500 s exposure")
NK("fig1.cap;fig1a;fig1b;fig1c", "schematics of the slab, cylinder and sphere with their shape factors; the factors are definition facts")
NK("tab1.r0c0;tab1.r0c1;tab2.r0c0;tab2.r0c1", "table headers")
NK(";".join(f"tabu1.r{i}c{j}" for i in range(29) for j in range(2)) + ";" + ";".join(f"tabu2.r{i}c{j}" for i in range(3) for j in range(2)), "symbol-list cells: every symbol is a definition fact citing its row")

# ---------------------------------------------------------------- claims
c_model = claim("abs.g1;s2.p11;s12.p1", "a diffusion-reaction model of ALD adapted to radial transport and adsorption in a porous particle, with a shape factor for the slab, cylinder and sphere", "asserted")
c_dims = claim("abs.g2;s12.p1;s7.x1;s7.p2", "the reactant front is one-dimensional in a slab but closes in from two and three dimensions in a cylinder and a sphere, so these need less exposure for full penetration", "asserted",
               "gas_diffusion", "exposure", "decreases")
c_sens = claim("abs.g3;abs.g4;s12.p3", "a sensitivity analysis ranks porosity and tortuosity, pore diameter, specific surface area, pore volume, particle radius, reactant molar mass, GPC, sticking probability, exposure and temperature by their effect on the penetration depth", "asserted")
c_use = claim("abs.g4;s12.p5", "the model serves the design of ALD on porous media: catalyst particles as spheres, membranes as slabs, fibres and monoliths as cylinders", "asserted")
c_porous = claim("s2.p1;s2.p2", "ALD coats porous media conformally through self-limiting adsorption; in catalyst preparation it sets metal loading and penetration depth, which diffusion-reaction modelling can design", "asserted", mentions="ref 1;ref 5;ref 10")
c_lit = claim("s2.p3", "Gordon's analytic model has the exposure for conformal coating grow quadratically with the aspect ratio; computational models are ballistic, Monte Carlo or diffusion-reaction, the last suited to simplified particle geometries", "asserted",
              mentions="ref 18;ref 22;ref 31")
c_De = claim("s2.p7", "the effective diffusion coefficient of a porous catalyst particle is the Knudsen coefficient times porosity over tortuosity, so it depends on pore size, temperature, molar mass, porosity and tortuosity", "asserted",
             "gas_diffusion", "penetration_depth", "causes", mentions="ref 35;ref 36")
c_scm = claim("s2.p8", "catalyst regeneration is the classic diffusion-reaction case in a sphere: oxygen, like an ALD reactant, is consumed less toward the centre, described by a shrinking core model", "asserted", mentions="ref 35;ref 37")
c_shape = claim("s2.p9;s2.p10;s4.p4", "the shape factor s = a − 1, with a the outer surface over volume times R, is 0, 1 and 2 for slab, cylinder and sphere; r runs from the outer surface (0) to the centre or mid-plane (R)", "asserted",
                mentions="ref 35;ref 36;ref 37;ref 38")
c_prev = claim("s2.p10", "Lee et al. computed how the geometry of porous alumina monoliths (planar, cylindrical, spherical) changes the exposure time for complete ZnO coverage; Elam and Detavernier showed reactant consumption falling toward a sphere's centre", "asserted",
               mentions="ref 6;ref 39;ref 40")
c_beyond = claim("s2.p11", "the approach may carry over to sequential infiltration synthesis and vapour-phase infiltration", "hedged", mentions="ref 41;ref 42")
c_knud = claim("s4.p6", "transport is taken as pure Knudsen diffusion, the mean free path far above the pore size, so the molecular term of the Bosanquet relation is dropped", "asserted", "gas_diffusion", "penetration_depth", "causes")
c_lang = claim("s4.p15;s4.p16", "adsorption is irreversible single-site Langmuir; the site area s0 is the reciprocal of the areal site density σ, which the GPC fixes", "asserted", "surface_chemistry", "surface_coverage", "causes", mentions="ref 7;ref 22;ref 32;ref 46")
c_base = claim("s5.p1;s5.p4", "the baseline parameters represent no specific reactant or support; they are inspired by the TMA-water process and mesoporous silica or alumina supports", "asserted", mentions="ref 29;ref 49;ref 50")
c_order = claim("s7.p1;fig2.cap", "for the same exposure the coating penetrates deeper in the order sphere > cylinder > slab; the slab's reactant density falls linearly, the others' profiles curve", "asserted",
                "gas_diffusion", "penetration_depth", "causes", mentions="ref 18;ref 39")
c_cyl = claim("s7.p1", "the cylinder factor holds for long cylinders; a cylinder of height nR has s = 2(n+1)/n − 1, tending to 1 for large n and to the spherical equation for small n", "asserted", mentions="ref 36")
c_cov = claim("s7.p3", "although the shape factor is absent from the coverage equation, the coupling lets the cylinder and sphere penetrate deeper in coverage too; all three coverage profiles share their shape and front slope", "asserted",
              "gas_diffusion", "front_slope", "no_effect")
c_fig3 = claim("s8.x1;fig3.cap", "a larger exposure lets larger particles be fully penetrated; as the radius grows the three geometries converge, because the 1/R and 2/R terms vanish", "asserted", "exposure", "penetration_depth", "increases")
c_600 = claim("s8.p3", "in the example the shape factor matters for radii below 600 µm, but the relevant size range depends on the exposure, not on a fixed size", "asserted", "feature_depth", "penetration_depth", "causes")
c_xi = claim("s8.x2;s12.p2", "the slab and sphere estimates differ by under 5 % while ξ ≤ 0.15 and under 1 % while ξ ≤ 0.05; at full infiltration the difference reaches 40–45 %, so the shape factor matters more the deeper the coating", "asserted",
             "gas_diffusion", "penetration_depth", "causes", mentions="ref 6;ref 39;ref 40")
c_sqrt = claim("s12.p2", "for the slab the penetration depth grows with the square root of the exposure; for the sphere the shell volume shrinks as r³ toward the centre, so the relation differs", "asserted", "exposure", "penetration_depth", "increases")
c_tau = claim("s9.x1;s9.p2", "τ/ε from 1 to 5 is typical of catalyst supports; more tortuosity or less porosity restricts diffusion, and with restricted diffusion the slab and sphere depths converge, while at low τ/ε the shrinking-core effect sets them apart", "asserted",
              "gas_diffusion", "penetration_depth", "decreases", mentions="ref 35")
c_mass = claim("s9.p3", "a heavier reactant penetrates less, since its thermal velocity is lower, as Yim et al. also found", "asserted", "molar_mass", "penetration_depth", "decreases", mentions="ref 43")
c_sigma = claim("s9.p4", "a smaller areal site density, a smaller GPC, lengthens the penetration depth since fewer sites consume the reactant; at σ = 1 nm-2 the spheres are fully coated", "asserted", "saturation_density", "penetration_depth", "decreases",
                mentions="ref 43")
c_sbar = claim("s9.p5", "a larger surface-to-pore-volume ratio s̄ means more adsorption sites per volume and a shorter penetration depth", "asserted", "specific_surface_area", "penetration_depth", "decreases")
c_beta = claim("s9.p6", "the sticking probability leaves the reactant density profiles nearly unchanged, as Keuter and Arts found; only near depletion does a lower β0 let the reactant travel slightly deeper, unlike the slight increase Yim et al. saw with their analytic pressure",
               "asserted", "initial_sticking_coefficient", "penetration_depth", "no_effect", mentions="ref 34;ref 43;ref 51")
c_pore = claim("s9.p7;s9.p8", "the pore diameter enters only through the Knudsen coefficient: a narrower pore restricts diffusion; r(θ=1/2) grows linearly with pore diameter, faster for the sphere (×2.5 from 10 to 40 nm) than the slab (×2)", "asserted",
               "feature_width", "penetration_depth", "increases")
c_fig6 = claim("s9.x2;s9.p9", "the coverage profiles widen as β0 falls; sphere and slab share the coverage shape for a given β0 and differ only in depth, since only the propagation geometry differs", "asserted", "initial_sticking_coefficient", "front_slope", "decreases")
c_fig7 = claim("s10.p1;s10.p2;s10.p4;s12.p3", "with typical supports a higher specific surface area comes with more pore volume and smaller pores; at fixed exposure a higher surface area shortens the penetration depth and a larger pore diameter lengthens it through the Knudsen coefficient",
               "asserted", "specific_surface_area", "penetration_depth", "decreases")
c_T = claim("s11.p1;s11.p2;s11.p3;s12.p4", "with the reactant quantity fixed as a number density the penetration depth rises with temperature; with a fixed partial pressure the number density falls with temperature and so does the penetration depth, as Yim and Gayle reported",
            "asserted", "deposition_temperature", "penetration_depth", "causes", mentions="ref 1;ref 31;ref 32")

# ---------------------------------------------------------------- definitions (P89)
DEFS = [("tabu1.r1c0;tabu1.r1c1;s4.p4", "a", "the geometry factor a = s + 1: outer surface area over particle volume, times R", "", ""),
        ("tabu1.r2c0;tabu1.r2c1;s4.p3", "A_O|A_0|A_{O_0}|specific surface area|surface area", "specific surface area of the porous medium", "specific_surface_area", ""),
        ("tabu1.r3c0;tabu1.r3c1", "A_Par", "outer surface area of the particle as an ideal non-porous body", "", ""),
        ("tabu1.r4c0;tabu1.r4c1;s4.p3", "β0|β_0|beta_0|sticking probability|initial sticking probability", "initial sticking probability of the reactant on collision with the pore wall", "initial_sticking_coefficient", ""),
        ("tabu1.r5c0;tabu1.r5c1;s4.p5", "D_e|De|effective diffusion coefficient", "effective diffusion coefficient in the pores, ε/τ times the Knudsen coefficient", "effective_diffusion_coefficient", "in the pores: porosity over tortuosity times the Knudsen coefficient"),
        ("tabu1.r6c0;tabu1.r6c1", "D_i|Di", "gas-phase diffusion coefficient, the Bosanquet sum", "", ""),
        ("tabu1.r7c0;tabu1.r7c1", "D_Kn|DKn", "Knudsen diffusion coefficient", "knudsen_diffusion_coefficient", ""),
        ("tabu1.r8c0;tabu1.r8c1", "D_mi|Dmi", "molecular diffusion coefficient", "gas_phase_diffusion_coefficient", ""),
        ("tabu1.r9c0;tabu1.r9c1;s4.p10", "d_pore|dpore|d_{pore}|pore diameter|mean pore diameter", "mean pore diameter of the porous medium", "feature_width", "the pore, the smallest opening the reactant passes"),
        ("tabu1.r10c0;tabu1.r10c1", "v_th|vth", "mean thermal velocity of the reactant", "", ""),
        ("tabu1.r11c0;tabu1.r11c1", "ε|epsilon|porosity", "porosity, the void fraction of the particle", "porosity", ""),
        ("tabu1.r12c0;tabu1.r12c1", "GPC", "growth per cycle", "growth_per_cycle", ""),
        ("tabu1.r13c0;tabu1.r13c1", "h", "height of the cylinder", "", ""),
        ("tabu1.r14c0;tabu1.r14c1", "k_B", "Boltzmann constant", "", ""),
        ("tabu1.r15c0;tabu1.r15c1;tab2.r1c0", "m_r|m_R|mr|reactant molar mass", "mass of a single reactant molecule; Table 2 gives it as a molar mass", "molar_mass", "the reactant, generic"),
        ("tabu1.r16c0;tabu1.r16c1;s4.p3", "n_P0|n_p0|n_P|n_p|n_{P0}|volumetric reactant number density|reactant number density", "volumetric reactant number density of the gas in the pores (n_P0 at the surface)", "reactant_number_density", "n_P0: the value at the particle surface"),
        ("tabu1.r17c0;tabu1.r17c1", "p_A0|pA0|p_{A0}", "partial pressure of the reactant A", "partial_pressure", ""),
        ("tabu1.r18c0;tabu1.r18c1;s2.p9", "r|radial coordinate", "radial coordinate from the outer surface (0) to the centre (R)", "distance", "from the particle surface inward"),
        ("tabu1.r19c0;tabu1.r19c1;s8.p1", "r_θ=1/2|r_{θ=1/2}|r_{\\theta=1/2}|rθ=1/2|penetration depth|coating penetration depth", "the penetration depth: the radial position where the coverage is one half", "penetration_depth",
         "level 50 %, from the particle surface"),
        ("tabu1.r20c0;tabu1.r20c1;s2.p9", "R|particle radius", "particle radius (half-thickness for a slab), the diffusion path from the surface to the centre", "feature_depth", "the radius: the depth the reactant must travel to the centre"),
        ("tabu1.r21c0;tabu1.r21c1;s4.p4", "s|shape factor", "shape factor s = a − 1: 0 slab, 1 cylinder, 2 sphere", "", ""),
        ("tabu1.r22c0;tabu1.r22c1;s4.p3", "s̄|sbar|\\bar{s}|A_O/V_p", "the ratio of specific surface area to pore volume, s̄ = A_O/V_p, surface per pore volume", "", ""),
        ("tabu1.r23c0;tabu1.r23c1;s4.p16", "s_0|s0", "average area of one adsorption site, 1/σ", "", ""),
        ("tabu1.r24c0;tabu1.r24c1", "SCM", "shrinking core model", "", ""),
        ("tabu1.r25c0;tabu1.r25c1;s4.p16", "σ|σ_P|sigma|areal number density", "areal number density of metal atoms deposited per cycle at saturation, the GPC as a site density", "saturation_density", ""),
        ("tabu1.r26c0;tabu1.r26c1;s4.p3", "t|reactant exposure time|exposure time|reactant exposure duration|exposure duration", "reactant exposure time", "pulse_time", "the reactant step"),
        ("tabu1.r27c0;tabu1.r27c1", "τ|tau|tortuosity", "tortuosity of the pore network", "", ""),
        ("tabu1.r28c0;tabu1.r28c1", "T|temperature", "ALD process temperature", "deposition_temperature", ""),
        ("tabu2.r0c0;tabu2.r0c1", "θ|theta|surface coverage", "surface coverage, the fraction of occupied sites", "surface_coverage", ""),
        ("tabu2.r1c0;tabu2.r1c1", "V_P|V_p|Vp|pore volume", "pore volume per mass", "", ""),
        ("tabu2.r2c0;tabu2.r2c1", "V_Par", "particle volume", "", ""),
        ("s9.x1;fig5.cap", "τ/ε|tau/epsilon|\\tau/\\epsilon", "the combined factor tortuosity over porosity, the reciprocal of the ε/τ of the effective diffusion coefficient", "", ""),
        ("s8.p4;fig4.cap", "ξ|ξ_θ=1/2|ξ_{θ=1/2,sphere}|normalized penetration depth", "the normalized penetration depth ξ = r(θ=1/2)/R; one means a fully coated particle", "", ""),
        ("s4.p3;s8.p1", "exposure|reactant exposure", "the exposure, partial pressure times exposure time, in Pa s", "exposure", ""),
        ("tabu1.r0c0;tabu1.r0c1", "ALD", "atomic layer deposition", "", "")]
for ev, term, text, q, note in DEFS:
    kw = dict(term=term)
    if q:
        kw["quantity"] = q
        if q == "penetration_depth":
            kw["qualifiers"] = "level=50%"
        if q == "porosity":
            kw["qualifiers"] = "stage=initial;relative_to=total_volume"
    if note:
        kw["definition_note"] = note
    f(ev, "definition", f"symbol {term.split('|')[0]}: {text}", **kw)

# ---------------------------------------------------------------- the model
M = [f("s4.p1;s4.p2;eq1;s4.p3", "model", "Eq. (1): the diffusion-reaction equation for the reactant number density with the shape factor s in the radial Laplacian and the adsorption loss ¼ v_th β0 n_P (1 − θ), scaled by s̄ = A_O/V_p", mentions="ref 34;ref 37"),
     f("s4.p5;eq2;s4.p6;eq3", "model", "Eqs. (2)-(3): the Bosanquet relation 1/D_i = 1/D_mi + 1/D_Kn, reduced to D_i = D_Kn for Knudsen-dominated transport", mentions="ref 25"),
     f("s4.p7;s4.p8;eq4;s4.p9;eq5;s4.p10", "model", "Eqs. (4)-(5): D_e = (ε/τ) D_Kn with the kinetic-theory Knudsen coefficient from the pore diameter, temperature and molecular mass", mentions="ref 35;ref 36;ref 37;ref 44;ref 45"),
     f("s4.p11;eq6;eq7;eq8", "model", "Eqs. (6)-(8): the equations for slab, cylinder and sphere, the latter two with D_e (1/R) and D_e (2/R) times the first derivative"),
     f("s4.p15;eq9;s4.p16", "model", "Eq. (9): the coverage rate dθ/dt = −s0 ¼ v_th β0 n_P (1 − θ) with s0 = 1/σ; the ideal gas law converts the partial pressure to the number density", mentions="ref 22;ref 32"),
     f("s4.p17;eq10;s4.p18;eq11", "model", "Eqs. (10)-(11): θ and n_p are zero everywhere at t = 0"),
     f("s4.p19;eq12;s4.p20;eq13", "model", "Eqs. (12)-(13): Dirichlet n_p = n_p0 at the surface, Neumann zero gradient at the centre", mentions="ref 35;ref 47"),
     f("s4.p21", "model", "the PDEs were solved in MATLAB R2023a by the method of lines: dss004 (five-point) and dss044 (six-point) finite differences, typically 300 radial points, ode15s for the stiff ODE system", quantity="other",
       label_as_printed="radial discretisation points", value="300", data_kind="stated", mentions="ref 48;MATLAB 9.14.0 (R2023a);dss004;dss044;ode15s")]
pd_def = f("s8.p1", "model", "the penetration depth r(θ=1/2) is read where the coverage is 0.5", mentions="ref 32;ref 51")

# ---------------------------------------------------------------- the baseline (Tables 1 and 2)
BASE = {}
def bset(sym, ev, text, **kw):
    BASE[sym] = f(ev, "model", text, data_kind="model_input", **kw)


bset("eps", "tab1.r1c0;tab1.r1c1;tab1.cap", "Table 1 baseline: porosity 0.5, that is 50 %", quantity="porosity", qualifiers="stage=initial;relative_to=total_volume", label_as_printed="ε", value="50", unit="%", mentions="0.5")
bset("tau", "tab1.r2c0;tab1.r2c1;tab1.cap", "Table 1 baseline: tortuosity 1", quantity="other", label_as_printed="τ", value="1")
bset("dpore", "tab1.r3c0;tab1.r3c1;tab1.cap", "Table 1 baseline: mean pore diameter 2e-8 m, 20 nm", quantity="feature_width", label_as_printed="d_pore", value="20", unit="nm", mentions="2 × 10^-8 m")
bset("AO", "tab1.r4c0;tab1.r4c1;tab1.cap", "Table 1 baseline: specific surface area 200 m2/g", quantity="specific_surface_area", label_as_printed="A_O", value="200", unit="m2/g")
bset("Vp", "tab1.r5c0;tab1.r5c1;tab1.cap", "Table 1 baseline: pore volume 6e-7 m3/g", quantity="other", label_as_printed="V_p", value="6e-7", unit="m3/g")
bset("R", "tab1.r6c0;tab1.r6c1;tab1.cap", "Table 1 baseline: particle radius 3e-4 m, 300 µm", quantity="feature_depth", label_as_printed="R", value="300", unit="µm", mentions="3 × 10^-4 m")
bset("mR", "tab2.r1c0;tab2.r1c1;tab2.cap", "Table 2 baseline: reactant molar mass 100 g/mol", quantity="molar_mass", qualifiers="species=model_reactant", label_as_printed="m_R", value="100", unit="g/mol")
bset("beta", "tab2.r2c0;tab2.r2c1;tab2.cap", "Table 2 baseline: initial sticking probability 2e-2", quantity="initial_sticking_coefficient", qualifiers="kind=set_point;species=model_reactant", label_as_printed="β0", value="0.02", mentions="2 × 10^-2")
bset("sigma", "tab2.r3c0;tab2.r3c1;tab2.cap", "Table 2 baseline: areal number density of metal atoms per cycle at saturation 4e18 m-2, that is 4 nm-2", quantity="saturation_density", label_as_printed="σ_p", value="4", unit="nm-2", mentions="4 × 10^18 m^-2")
bset("np0", "tab2.r4c0;tab2.r4c1;tab2.cap;s5.p2", "Table 2 baseline: reactant number density outside the particle 1.71e22 m-3, estimated for 100 Pa of reactant vapour at the 423 K baseline", quantity="reactant_number_density", label_as_printed="n_p0", value="1.71e22", unit="m-3",
     mentions="100 Pa;423 K")
bset("pA0", "s5.p2;tab2.r4c1", "the baseline reactant partial pressure is 100 Pa, the vapour pressure the number density is estimated from", quantity="partial_pressure", qualifiers="species=model_reactant", label_as_printed="p_A0", value="100", unit="Pa")
bset("T", "tab2.r5c0;tab2.r5c1;tab2.cap", "Table 2 baseline: temperature 423 K", quantity="deposition_temperature", label_as_printed="T", value="423", unit="K")
bset("t", "tab2.r6c0;tab2.r6c1;tab2.cap;s5.p3", "Table 2 baseline: reactant exposure time 500 s (bold), with 100 and 1000 s as the other values", quantity="pulse_time", qualifiers="step=reactant_A", label_as_printed="t", value="500", unit="s",
     mentions="100 s;1000 s")
bset("E", "s8.p1;fig3.cap;tab2.r6c1", "the exposures used, 1e4, 5e4 and 1e5 Pa s, are the 100 Pa pressure times 100, 500 and 1000 s; the baseline exposure is 5e4 Pa s", quantity="exposure", qualifiers="species=model_reactant", label_as_printed="exposure", value="5e4", unit="Pa·s",
     mentions="1 × 10^4 Pa s;1 × 10^5 Pa s")
sbar_base = f("s4.p3;tab1.r4c1;tab1.r5c1", "derived", "the baseline surface-to-pore-volume ratio s̄ = A_O/V_p is 200 m2/g over 6e-7 m3/g, about 3.3e8 m-1", quantity="other", label_as_printed="s̄", value="3.3e8", unit="1/m", data_kind="computed_by_kb",
               method="calculation", inputs=[BASE["AO"], BASE["Vp"]])

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Heikkinen et al. 2024: a diffusion-reaction model of ALD in porous particles with slab, cylinder and sphere shape factors", "", evidence="s1.h")
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


SIM = node(f"{K}:sim", "activity", "the porous-particle diffusion-reaction model (Eqs. 1-13) solved in MATLAB at the Table 1-2 baseline, one parameter varied at a time", PAPER, evidence="s3.h;s4.h;tab1.cap;tab2.cap", kind="simulation", how="stated",
           label_as_printed="porous-particle model")
put(SIM, *M, pd_def, *BASE.values(), sbar_base)
RUNS = {}


def run(rid, st, ev, label, own):
    e = node(f"{K}:simrun:{rid}", "entity", st, SIM, evidence=ev, how="stated", label_as_printed=label)
    put(e, *own)
    RUNS[rid] = e
    return e


GEO = {"sphere": ("porous_sphere", "Sphere (s = 2)", "2"), "cylinder": ("porous_cylinder", "Cylinder (s = 1)", "1"), "slab": ("porous_slab", "Slab (s = 0)", "0")}


def geo_setting(g, ev, extra=""):
    sid, lab, s_ = GEO[g]
    return f(ev, "setting", f"{extra or 'the baseline run'}: the particle is a porous {g}, shape factor {s_}", quantity="structure", value_text=sid, data_kind="model_input", mentions=lab + (";" + extra if extra else ""))


# Fig. 2: the three geometries at the baseline (500 s)
PD2 = {"sphere": "177", "cylinder": "133", "slab": "114"}
for g in ("sphere", "cylinder", "slab"):
    e = run(f"fig2:{g}", f"the baseline run (500 s exposure) in a porous {g}", "fig2.cap;fig2a;fig2b;s7.p1", f"baseline run, {g}", [geo_setting(g, "fig2.cap;fig2a;fig2b", f"baseline run, {g}")])
    put(e, f("s7.p1;fig2.cap;fig2b", "derived", f"Fig. 2: the penetration depth r(θ=1/2) in the {g} is {PD2[g]} µm at the baseline exposure", quantity="penetration_depth", qualifiers="level=50%", value=PD2[g], unit="µm", data_kind="computed_by_authors",
               method="simulation", mentions=GEO[g][1]),
        f("fig2a;fig2.cap", "model", f"Fig. 2(a): the reactant number density against the radial coordinate in the {g}", method="simulation", mentions=GEO[g][1] + ";Fig. 2(a)"),
        f("fig2b;fig2.cap", "model", f"Fig. 2(b): the surface coverage against the radial coordinate in the {g}", quantity="surface_coverage", method="simulation", mentions=GEO[g][1] + ";Fig. 2(b)"))
# Fig. 3: geometry × exposure, the particle radius along x
EXP = {"1e5": ("1 × 10⁵ Pa·s", "1e5"), "5e4": ("5 × 10⁴ Pa·s", "5e4"), "1e4": ("1 × 10⁴ Pa·s", "1e4")}
EXPW = {"1e5": "the highest exposure", "5e4": "the middle exposure", "1e4": "the lowest exposure", "1e3": "the lowest exposure"}
FULL = {("sphere", "1e5"): "275", ("cylinder", "1e5"): "225", ("slab", "1e5"): "161"}
for g in ("sphere", "cylinder", "slab"):
    for ek, (elab, ev_) in EXP.items():
        lab = f"{GEO[g][1]}, Exposure: {elab}"
        if ek == "5e4":                                                         # the baseline exposure: the Fig. 2 run is this curve's run (same conditions, the radius swept in Fig. 3)
            e = RUNS[f"fig2:{g}"]
            FX[e]["mentions"] = (FX[e]["mentions"] + ";" if FX[e]["mentions"] else "") + lab
            FX[e]["evidence"] += ";fig3.cap;fig3"
            RUNS[f"fig3:{g}:{ek}"] = e
            put(e, f("fig3.cap;fig3;tab2.r6c1", "setting", f"the baseline run in the {g}: exposure 5e4 Pa s, 100 Pa for 500 s", quantity="exposure", qualifiers="species=model_reactant", value=ev_, unit="Pa·s", data_kind="model_input", mentions=lab))
        else:
            e = run(f"fig3:{g}:{ek}", f"Fig. 3 run: the porous {g} at an exposure of {ev_} Pa s, the particle radius swept", "fig3.cap;fig3", f"Fig. 3 run, {g}, {ev_} Pa s",
                    [geo_setting(g, "fig3.cap;fig3", f"Fig. 3 run, {g}, {ev_} Pa s"), f("fig3.cap;fig3", "setting", f"Fig. 3 run, {g}: exposure {ev_} Pa s", quantity="exposure", qualifiers="species=model_reactant", value=ev_, unit="Pa·s", data_kind="model_input", mentions=lab)])
        put(e, f("fig3;fig3.cap", "model", f"Fig. 3: the penetration depth against the particle radius for the {g} at {ev_} Pa s", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions=lab + ";Fig. 3"))
        if (g, ek) in FULL:
            put(e, f("s8.x1;fig3", "derived", f"Fig. 3: at 1e5 Pa s the {g} is fully penetrated up to a radius of {FULL[(g, ek)]} µm", quantity="feature_depth", qualifiers="stat=maximum", label_as_printed="R", value=FULL[(g, ek)], unit="µm",
                     data_kind="computed_by_authors", method="simulation", mentions=lab))
put(RUNS["fig3:sphere:1e5"], f("s8.p4;fig3", "derived", "Fig. 3 example: at R = 300 µm and 1e5 Pa s the sphere's penetration depth is 229 µm", quantity="penetration_depth", qualifiers="level=50%", value="229", unit="µm", data_kind="computed_by_authors",
                                method="simulation", mentions="R = 300 µm"))
put(RUNS["fig3:slab:1e5"], f("s8.p4;fig3", "derived", "Fig. 3 example: at R = 300 µm and 1e5 Pa s the slab's penetration depth is 161 µm", quantity="penetration_depth", qualifiers="level=50%", value="161", unit="µm", data_kind="computed_by_authors",
                              method="simulation", mentions="R = 300 µm"))
c_r50 = claim("s8.x1", "a 50 µm particle is penetrated to its centre at every exposure and geometry shown: the line from the origin is full penetration", "asserted", supports=[RUNS["fig3:sphere:1e4"]])
# Fig. 4: the slab/sphere difference against the normalized sphere depth, per exposure
diff30 = f("s8.p4", "derived", "the Fig. 4 example point: 30 % = 1 − 161/229 at ξ = 229/300 = 0.76", quantity="other", label_as_printed="slab–sphere difference", value="30", unit="%", data_kind="computed_by_authors", method="calculation",
           mentions="0.76;161 µm;229 µm")
for ek, (elab, ev_) in EXP.items():
    lab4 = elab.replace("⁵", "^5").replace("⁴", "^4")
    e = run(f"fig4:{ek}", f"Fig. 4 run pair: slab against sphere at {ev_} Pa s, 423 K, the radius from 50 to 3000 µm in 25 µm steps", "fig4.cap;fig4", f"Fig. 4 runs, {ev_} Pa s",
            [f("fig4.cap;fig4", "setting", f"Fig. 4: exposure {ev_} Pa s", quantity="exposure", qualifiers="species=model_reactant", value=ev_, unit="Pa·s", data_kind="model_input", mentions=lab4)])
    put(e, f("fig4;fig4.cap", "model", f"Fig. 4: the slab–sphere penetration-depth difference against ξ at {ev_} Pa s", method="simulation", mentions=lab4 + ";Fig. 4"))
put(RUNS["fig4:1e5"], diff30)
R_sweep = f("fig4.cap", "model", "Fig. 4 sweeps the particle radius from 50 to 3000 µm in 25 µm steps", quantity="feature_depth", label_as_printed="R", value_min="50", value_max="3000", unit="µm", data_kind="model_input", mentions="25 µm steps")
thr5 = f("s8.x2;s12.p2", "derived", "the slab and sphere depths differ by less than 5 % while ξ ≤ 0.15", quantity="other", label_as_printed="ξ for < 5 % difference", value="0.15", data_kind="computed_by_authors", method="simulation", mentions="5%")
thr1 = f("s8.x2;s12.p2", "derived", "the difference stays under 1 % while ξ ≤ 0.05", quantity="other", label_as_printed="ξ for < 1 % difference", value="0.05", data_kind="computed_by_authors", method="simulation", mentions="1%")
full_d = f("s8.x2", "derived", "at full infiltration the slab–sphere difference reaches about 40–45 %", quantity="other", label_as_printed="slab–sphere difference", value_min="40", value_max="45", unit="%", data_kind="computed_by_authors", method="simulation")
put(SIM, R_sweep, thr5, thr1, full_d)
# Figs. 5 and 6: the sensitivity runs, sphere and slab, 500 s
SENS = [("tau", "τ/ε", "", "", "", ["1", "2", "3", "4", "5"], "2", lambda v: [rf"\tau/\epsilon = {v}", f"τ/ε = {v}"], "ab"),
        ("mR", "reactant molar mass", "molar_mass", "species=model_reactant", "g/mol", ["50", "100", "150", "200", "250"], "100", lambda v: [f"{v} g mol^{{-1}}", f"{v} g mol-1"], "cd"),
        ("sigma", "σ", "saturation_density", "", "nm-2", ["1", "2", "4", "6", "8"], "4", lambda v: [rf"\sigma = {v} nm^{{-2}}", f"σ = {v} nm^-2"], "ef"),
        ("sbar", "s̄", "", "", "1/m", ["1e8", "2e8", "3e8", "4e8", "5e8"], None, lambda v: [rf"\bar{{s}} = {v[0]} \times 10^8 m^{{-1}}", f"s̄ = {v[0]} × 10^8 m^-1"], "gh"),
        ("beta", "sticking probability", "initial_sticking_coefficient", "kind=set_point;species=model_reactant", "", ["0.0001", "0.001", "0.01", "0.1", "1"], None, lambda v: [rf"\beta_0 = {v}", f"β0 = {v}"], "ij"),
        ("dpore", "d_pore", "feature_width", "", "nm", ["5", "10", "20", "30", "40"], "20", lambda v: [f"d_{{pore}} = {v} nm", f"d_pore = {v} nm"], "kl")]
GRP = {}
t500 = f("fig5.cap;fig6.cap", "model", "the Figs. 5 and 6 runs use a 500 s reactant exposure, the baseline, with one parameter changed at a time", quantity="pulse_time", qualifiers="step=reactant_A", value="500", unit="s", data_kind="model_input")
put(SIM, t500)
for sym, lab, q, quals, u, vals, bv, labs, pans in SENS:
    for gi, g in enumerate(("sphere", "slab")):
        p5, p6 = f"fig5{pans[gi]}", f"fig6{pans[gi]}"
        members = []
        for v in vals:
            ls = labs(v)
            if v == bv:
                e = RUNS[f"fig2:{g}"]
                FX[e]["mentions"] = (FX[e]["mentions"] + ";" if FX[e]["mentions"] else "") + ";".join(ls)
                FX[e]["evidence"] += f";{p5};{p6}"
                members.append(e); continue
            kw = dict(quantity=q or "other", label_as_printed=lab, value=v, data_kind="model_input", mentions=";".join(ls) + f";Fig. 5({pans[gi]})")
            if quals:
                kw["qualifiers"] = quals
            if u:
                kw["unit"] = u
            e = run(f"{p5}:{sym}:{v}", f"sensitivity run in the porous {g}: {lab} = {v} {u}, the other parameters at baseline, 500 s".strip(), f"fig5.cap;fig6.cap;{p5};{p6}", f"Fig. 5({pans[gi]}) run, {lab} {v}",
                    [geo_setting(g, f"fig5.cap;{p5}", f"Fig. 5({pans[gi]}) run, {lab} {v}"), f(f"fig5.cap;{p5};{p6}", "setting", f"{g}, Fig. 5({pans[gi]}): {lab} = {v} {u}".strip(), **kw)])
            put(e, f(f"{p5};fig5.cap", "model", f"Fig. 5({pans[gi]}): the reactant number density profile in the {g} at {lab} = {v} {u}".strip(), method="simulation", mentions=";".join(ls) + f";Fig. 5({pans[gi]})"),
                f(f"{p6};fig6.cap", "model", f"Fig. 6({pans[gi]}): the coverage profile in the {g} at {lab} = {v} {u}".strip(), quantity="surface_coverage", method="simulation", mentions=";".join(ls) + f";Fig. 6({pans[gi]})"))
            members.append(e)
        if q:
            GRP[f"{sym}:{g}"] = (q, members, f"{lab} series in the porous {g}: Fig. 5({pans[gi]}) and 6({pans[gi]}), {lab} over {', '.join(vals)} {u}".strip(), f"fig5.cap;fig6.cap;{p5};{p6}")
for g in ("sphere", "slab"):
    put(RUNS[f"fig2:{g}"], f("fig5.cap;s9.p1;fig5a;fig5b;fig5c;fig5d;fig5e;fig5f;fig5k;fig5l", "model", f"Figs. 5 and 6, the black baseline line in the {g}: the baseline reactant density profile", method="simulation", mentions=f"baseline;Fig. 5"),
        f("fig6.cap;fig6a;fig6b;fig6c;fig6d;fig6e;fig6f;fig6k;fig6l", "model", f"Figs. 6, the black baseline line in the {g}: the baseline coverage profile", quantity="surface_coverage", method="simulation", mentions=f"baseline;Fig. 6"))
pore2 = f("s9.p8", "derived", "raising the pore diameter from 10 to 40 nm doubles the slab's penetration depth and multiplies the sphere's by 2.5", quantity="other", label_as_printed="r(θ=1/2) ratio, 40 nm over 10 nm", value_min="2", value_max="2.5",
          data_kind="computed_by_authors", method="simulation", mentions="10 nm;40 nm;slab 2;sphere 2.5")
put(SIM, pore2)
# Fig. 7: specific surface area and pore diameter swept, sphere, three radii and three exposures
for Rv in ("300", "200", "100"):
    for ek, elab in (("1e5", "1 × 10⁵ Pa s"), ("1e4", "1 × 10⁴ Pa s"), ("1e3", "1 × 10³ Pa s")):
        lab = f"R = {Rv} µm, {elab}"
        e = run(f"fig7:R{Rv}:{ek}", f"Fig. 7 run: the porous sphere of radius {Rv} µm at {ek} Pa s and 423 K, the surface area and the pore diameter swept", "fig7.cap;fig7a;fig7b", f"Fig. 7 run, R {Rv} µm, {ek} Pa s",
                [geo_setting("sphere", "fig7.cap;fig7a;fig7b", f"Fig. 7 run, R {Rv} µm, {ek} Pa s"), f("fig7.cap;fig7a;fig7b", "setting", f"Fig. 7 run at {ek} Pa s: particle radius {Rv} µm", quantity="feature_depth", label_as_printed="R", value=Rv, unit="µm", data_kind="model_input", mentions=lab),
                 f("fig7.cap;fig7a;fig7b;s10.p3", "setting", f"Fig. 7 run with R {Rv} µm: exposure {ek} Pa s", quantity="exposure", qualifiers="species=model_reactant", value=ek, unit="Pa·s", data_kind="model_input", mentions=lab)])
        put(e, f("fig7a;fig7.cap", "model", f"Fig. 7(a): the penetration depth against specific surface area, R {Rv} µm, {ek} Pa s", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions=lab + ";Fig. 7(a)"),
            f("fig7b;fig7.cap", "model", f"Fig. 7(b): the penetration depth against pore diameter, R {Rv} µm, {ek} Pa s", quantity="penetration_depth", qualifiers="level=50%", method="simulation", mentions=lab + ";Fig. 7(b)"))
f7_AO = f("s10.p2;fig7.cap", "model", "Fig. 7 sweeps the specific surface area from 100 to 1000 m2/g", quantity="specific_surface_area", value_min="100", value_max="1000", unit="m2/g", data_kind="model_input")
f7_dp = f("s10.p2;fig7.cap", "model", "Fig. 7 sweeps the pore diameter from 3 to 50 nm", quantity="feature_width", label_as_printed="d_pore", value_min="3", value_max="50", unit="nm", data_kind="model_input")
f7_Vp = f("s10.p2", "model", "the Fig. 7 pore volumes run from 0.55 to 0.70 cm3/g", quantity="other", label_as_printed="V_p", value_min="0.55", value_max="0.70", unit="cm3/g", data_kind="model_input")
f7_sb = f("s10.p2", "model", "the Fig. 7 surface-to-pore-volume ratios run from 1.8e8 to 1.4e9 m-1", quantity="other", label_as_printed="s̄", value_min="1.8e8", value_max="1.4e9", unit="1/m", data_kind="model_input", mentions="Table S2")
f7_three = f("s10.p1;s10.p2", "model", "unlike the single-parameter analysis, Fig. 7 changes surface area, pore volume and pore diameter together, as real supports do", mentions="Table S2")
put(SIM, f7_AO, f7_dp, f7_Vp, f7_sb, f7_three)
# Fig. 8: temperature with the number density or the partial pressure fixed
NP = {"373": "1.94e22", "573": "1.26e22"}
for mode, pan, fixed in (("n", "a", "number density"), ("p", "b", "partial pressure")):
    for Tv in ("373", "423", "473", "523", "573"):
        own = [f(f"fig8.cap;fig8{pan}", "setting", f"Fig. 8({pan}) run: temperature {Tv} K", quantity="deposition_temperature", value=Tv, unit="K", data_kind="model_input", mentions=f"{Tv} K;Fig. 8({pan})")]
        if mode == "n":
            own.append(f("fig8.cap;fig8a;s11.p2", "setting", f"Fig. 8(a) run at {Tv} K: the reactant number density fixed at 1.94e22 m-3", quantity="other", label_as_printed="n_P0", value="1.94e22", unit="m-3", data_kind="model_input", mentions=f"{Tv} K"))
        else:
            own.append(f("fig8.cap;fig8b;s11.p3", "setting", f"Fig. 8(b) run at {Tv} K: the partial pressure fixed at 100 Pa", quantity="partial_pressure", qualifiers="species=model_reactant", value="100", unit="Pa", data_kind="model_input", mentions=f"{Tv} K"))
        e = run(f"fig8{pan}:T{Tv}", f"Fig. 8({pan}) run: {Tv} K with the reactant {fixed} fixed", f"fig8.cap;fig8{pan}", f"Fig. 8({pan}) run, {Tv} K", own)
        put(e, f(f"fig8{pan};fig8.cap", "model", f"Fig. 8({pan}): the reactant number density profile at {Tv} K with the {fixed} fixed", method="simulation", mentions=f"{Tv} K;Fig. 8({pan})"))
        if mode == "p" and Tv in NP:
            put(e, f("s11.p3", "derived", f"at {Tv} K a partial pressure of 100 Pa is a number density of {NP[Tv]} m-3", quantity="other", label_as_printed="n_P0", value=NP[Tv], unit="m-3", data_kind="computed_by_authors", method="calculation",
                     mentions=f"{Tv} K;100 Pa"))
C.identity(K, "different", [RUNS["fig4:5e4"], RUNS["fig8b:T423"]], "the Fig. 4 pair at 5e4 Pa s sweeps the radius for slab and sphere; the Fig. 8(b) run at 423 K is one sphere of baseline radius", "fig4.cap;fig8.cap", parent=SIM)
# definitions and cited under the paper
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
BY_TEXT = {"a diffusion-reaction model of ALD adapted to radial transport": [M[0], M[3]], "the reactant front is one-dimensional in a slab": [RUNS["fig2:sphere"], RUNS["fig2:slab"]],
           "a sensitivity analysis ranks porosity": [RUNS["fig5c:mR:50"], RUNS["fig5k:dpore:5"]], "the model serves the design of ALD": [M[3]], "ALD coats porous media conformally": [M[4]],
           "Gordon's analytic model has the exposure": [M[0]], "the effective diffusion coefficient of a porous catalyst": [M[2]], "catalyst regeneration is the classic": [M[3]], "the shape factor s = a − 1": [M[0], M[3]],
           "Lee et al. computed how the geometry": [M[3]], "the approach may carry over": [M[0]], "transport is taken as pure Knudsen": [M[1]], "adsorption is irreversible single-site Langmuir": [M[4]],
           "the baseline parameters represent no specific reactant": [BASE["mR"], BASE["beta"], BASE["sigma"]], "for the same exposure the coating penetrates deeper": [RUNS["fig2:sphere"], RUNS["fig2:cylinder"], RUNS["fig2:slab"]],
           "the cylinder factor holds for long cylinders": [RUNS["fig2:cylinder"]], "although the shape factor is absent": [RUNS["fig2:sphere"], RUNS["fig2:slab"]], "a larger exposure lets larger particles": [RUNS["fig3:sphere:1e5"], RUNS["fig3:slab:1e5"]],
           "in the example the shape factor matters for radii": [RUNS["fig3:sphere:1e4"]], "the slab and sphere estimates differ by under": [thr5, thr1, full_d], "for the slab the penetration depth grows with the square root": [RUNS["fig3:slab:1e5"]],
           "τ/ε from 1 to 5 is typical": [RUNS["fig5a:tau:1"], RUNS["fig5a:tau:5"]], "a heavier reactant penetrates less": [RUNS["fig5c:mR:50"], RUNS["fig5c:mR:250"]], "a smaller areal site density": [RUNS["fig5e:sigma:1"], RUNS["fig5e:sigma:8"]],
           "a larger surface-to-pore-volume ratio": [RUNS["fig5g:sbar:1e8"], RUNS["fig5g:sbar:5e8"]], "the sticking probability leaves the reactant density": [RUNS["fig5i:beta:0.0001"], RUNS["fig5i:beta:1"]],
           "the pore diameter enters only through": [pore2], "the coverage profiles widen as β0 falls": [RUNS["fig5i:beta:0.0001"], RUNS["fig5j:beta:0.0001"]], "with typical supports a higher specific surface area": [f7_AO, f7_dp, RUNS["fig7:R300:1e5"]],
           "with the reactant quantity fixed as a number density": [RUNS["fig8a:T373"], RUNS["fig8b:T373"], RUNS["fig8b:T573"]]}
for h, (stance, cause, effect, rel_, sup) in CLAIMS.items():
    if h not in FX:
        FX[h] = next(x for x in C.facts() if x["fact_id"] == h)
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
GROUPS = [(f"{K}:grp:fig2", "series", "structure", "the three geometries at the baseline: Fig. 2, sphere, cylinder and slab", "fig2.cap", c_order, [RUNS[f"fig2:{g}"] for g in ("sphere", "cylinder", "slab")])]
for ek, (elab, ev_) in EXP.items():
    GROUPS.append((f"{K}:grp:fig3_{ek}", "series", "structure", f"the three geometries at {EXPW[ek]}: Fig. 3, {ev_} Pa s, the radius swept", "fig3.cap", c_fig3, [RUNS[f"fig3:{g}:{ek}"] for g in ("sphere", "cylinder", "slab")]))
for g in ("sphere", "cylinder", "slab"):
    GROUPS.append((f"{K}:grp:fig3_{g}", "series", "exposure", f"the exposure series of the porous {g}: Fig. 3, 1e4, 5e4 and 1e5 Pa s", "fig3.cap", c_fig3, [RUNS[f"fig3:{g}:{ek}"] for ek in ("1e4", "5e4", "1e5")]))
GROUPS.append((f"{K}:grp:fig4", "series", "exposure", "the exposure series of the slab–sphere comparison: Fig. 4", "fig4.cap", c_xi, [RUNS[f"fig4:{ek}"] for ek in ("1e4", "5e4", "1e5")]))
PUR = {"mR": c_mass, "sigma": c_sigma, "beta": c_beta, "dpore": c_pore}
for gk, (q, members, st, ev) in GRP.items():
    GROUPS.append((f"{K}:grp:{gk.replace(':', '_')}", "series", q, st, ev, PUR[gk.split(":")[0]], members))
for Rv in ("300", "200", "100"):
    GROUPS.append((f"{K}:grp:fig7_R{Rv}", "series", "exposure", f"the exposure series at R {Rv} µm: Fig. 7", "fig7.cap", c_fig7, [RUNS[f"fig7:R{Rv}:{ek}"] for ek in ("1e3", "1e4", "1e5")]))
for ek in ("1e3", "1e4", "1e5"):
    GROUPS.append((f"{K}:grp:fig7_{ek}", "series", "feature_depth", f"the radius series at {EXPW[ek] if ek != '1e4' else 'the middle exposure'}: Fig. 7, {ek} Pa s, 100, 200 and 300 µm", "fig7.cap", c_fig7, [RUNS[f"fig7:R{Rv}:{ek}"] for Rv in ("100", "200", "300")]))
GROUPS.append((f"{K}:grp:fig8a", "series", "deposition_temperature", "the temperature series with the number density fixed: Fig. 8(a)", "fig8.cap", c_T, [RUNS[f"fig8a:T{T}"] for T in ("373", "423", "473", "523", "573")]))
GROUPS.append((f"{K}:grp:fig8b", "series", "deposition_temperature", "the temperature series with the partial pressure fixed: Fig. 8(b)", "fig8.cap", c_T, [RUNS[f"fig8b:T{T}"] for T in ("373", "423", "473", "523", "573")]))
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, {})
C.qualify(K, {})
CAV = [
    ("s5.p1;s5.p4", "The baseline is no real process: a generic reactant of 100 g/mol on a mesoporous support inspired by TMA/water and silica or alumina.", list(RUNS.values())[:3], "", ""),
    ("s4.p6", "Transport is pure Knudsen diffusion; molecular diffusion is dropped from the Bosanquet relation.", [M[1]], "", ""),
    ("s4.p15", "Adsorption is irreversible single-site Langmuir; the sticking probability is lumped.", [BASE["beta"]], "", ""),
    ("s7.p1;s4.p3", "The cylinder equation neglects the ends (a height above about a hundred radii); real cylinders with few radii of height approach the sphere.", [RUNS["fig2:cylinder"]], "", ""),
    ("s8.p2;tab1.r6c1", "The text places the Fig. 2 depths (177 and 114 µm) at R = 200 µm in Fig. 3 while Table 1 gives the baseline radius as 300 µm; the baseline here follows Table 1.", [RUNS["fig2:sphere"], RUNS["fig2:slab"]], "", ""),
    ("s4.p21", "The radial domain is discretised with typically 300 points; the method-of-lines finite differences are fourth order.", [M[7]], "", ""),
    ("s11.p2;s11.p3", "The temperature effect depends on whether the reactant quantity is held as a number density or a partial pressure; the model itself uses the number density.", [RUNS["fig8a:T573"], RUNS["fig8b:T573"]], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_xi.split(":", 1)[1]: [thr5.split(":", 1)[1], thr1.split(":", 1)[1], full_d.split(":", 1)[1]], c_pore.split(":", 1)[1]: [pore2.split(":", 1)[1]]})
C.specimen_classes(K, "porous_composite")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
write(K, PID)
