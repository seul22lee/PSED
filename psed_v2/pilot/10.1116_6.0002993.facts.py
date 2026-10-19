#!/usr/bin/env python3
"""Stage 2 facts for mat23 (10.1116_6.0002993, Mathew, Poonkottil, Solano, Poelman, Hens, Detavernier, Dendooven 2023, JVST A letter: a
plasma-enhanced ALD process for crystalline Ga2S3 from hexakis(dimethylamido)digallium and H2S plasma against the thermal process with
H2S: growth per cycle against temperature, in situ thickness against cycles, saturation, GIWAXS/XRD phase and texture, SEM and AFM
morphology, XPS composition and impurities, transmittance and band gap).
Text and captions (no table); the Fig. 1(b) thickness curves and the Fig. 4(b) Tauc plot are imported records (kb/figures_import.py,
P88); the Fig. 2(d) peaks are imported peak records.

    python3 psed_v2/pilot/10.1116_6.0002993.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "mat23", "10.1116_6.0002993"
A = "s5.p1"                                                                      # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h;s12.h", "heading")
NK("s0.p1;s1.p1;s1.p2;s1.p3;s1.p4;s3.p1;s3.p2;s3.p3;s3.p4;s3.p5;s3.p6;s3.p7;s4.p1;s4.p2;s4.p3;s4.p4;s4.p5;s4.p6;s5.p2", "front matter, authors, affiliations, dates, note, licence")
NK("s2.p1;s2.p2;s2.p3;s2.p4;s2.p5;s2.p6", "the publisher's related-article box")
NK("s9.p2;s10.p2;s10.p9;s11.p2", "download stamps of the PDF")
NK("s9.p3;s10.p3;s10.p8;s10.p14", "a caption printed again as a body paragraph; the knowledge is under the figure's caption element")
NK("s12.p1;s12.p2;s12.p3;s12.p4;s12.p5;s12.p6;s12.p7;s12.p8;s12.p9", "acknowledgements, declarations, author contributions, data availability")
NK(A, "the abstract printed again as a body paragraph (knowledge under abs.g1-g5)")

# ---------------------------------------------------------------- claims
c_new = claim("abs.g2;abs.g3;s6.p5;s11.p1", "a new PE-ALD process, hexakis(dimethylamido)digallium with H2S plasma, deposits high-quality Ga2S3 and outperforms the thermal process with the same reactants", "asserted")
c_state = claim("abs.g2;s6.p5", "the existing ALD routes to Ga2S3 give amorphous, nonstoichiometric films with carbon and oxygen contamination", "asserted", mentions="ref 7;ref 21")
c_cryst = claim("abs.g3;abs.g4;s11.p1", "the PE-ALD process deposits crystalline, smooth, stoichiometric Ga2S3 already at its lowest temperature, at the highest growth per cycle, without detectable carbon or oxygen", "asserted", "plasma_chemistry", "crystallinity", "causes")
c_cubic = claim("abs.g4;s10.p4;s10.p6;s11.p1", "GIWAXS shows the as-deposited Ga2S3 is cubic with a preferred [111] orientation, the (111) planes parallel to the substrate", "asserted", "plasma_chemistry", "phase", "causes")
c_opt = claim("abs.g5;s10.p15;s11.p1", "the crystalline Ga2S3 film is less transparent than the amorphous thermal film and has a direct, narrower band gap; the wider gap of the amorphous film is attributed to oxygen", "asserted", mentions="ref 34;ref 35;ref 36")
c_app = claim("abs.g1;s6.p1;s6.p2;s6.p3", "Ga2S3 is a wide-gap III-VI semiconductor of interest for photocatalysis, photodetection, nonlinear optics, battery anodes, luminescent glasses and GaAs passivation; it is polymorphic (monoclinic, hexagonal, cubic) and hard to grow pure and stoichiometric", "asserted",
              mentions="ref 1;ref 2;ref 3;ref 4;ref 5;ref 6;ref 7;ref 8;ref 9;ref 10;ref 11")
c_ald = claim("s6.p3", "ALD's self-limiting reactions give angstrom-scale thickness control and conformal coating of complex three-dimensional substrates, but gallium sulfide by ALD has few reports", "asserted", "self_limiting_growth", "normalized_thickness", "causes",
              mentions="ref 15;ref 16;ref 17;ref 18;ref 19")
c_pe = claim("s6.p5", "recent PE-ALD work tailors material properties and processing conditions, which motivated the plasma route with the same gallium source", "asserted", mentions="ref 22;ref 23;ref 24")
c_first = claim("s6.p5", "to the authors' knowledge crystalline Ga2S3 had not been deposited by ALD before", "asserted")
c_sat = claim("s7.p2", "the 25 s pulses are well above saturation; the reactant pulse time can affect morphology but was not studied here", "asserted", mentions="ref 26")
c_se = claim("s7.p3", "the ellipsometric thicknesses (Cauchy model) agree well with the XRR thicknesses", "asserted")
c_gpcT = claim("s9.p1;fig1.cap", "across the temperature window the PE-ALD growth per cycle first falls, stays flat, then rises again at the top; the thermal process follows the same trend at lower values", "asserted",
               "deposition_temperature", "growth_per_cycle", "causes")
c_plasma = claim("s9.p1;s9.p4", "the higher growth per cycle of PE-ALD comes from the higher reactivity of the plasma species; the thermal values agree with Meng et al. except a lower 0.28 against 0.49 Å at 200 °C", "asserted",
                 "plasma_chemistry", "growth_per_cycle", "increases", mentions="ref 7")
c_nucl = claim("s9.p5;s9.p6;fig1.cap", "PE-ALD shows substrate-enhanced growth at both 125 and 225 °C: about three cycles at 125 °C, and at 225 °C an S-shaped start (enhanced, then a dip, then steady), the island growth the SEM grains support", "asserted",
               "surface_chemistry", "film_thickness", "causes", mentions="ref 27;ref 28")
c_tnucl = claim("s9.p6", "the thermal process grows linearly at 125 °C without nucleation effects, unlike the 50-cycle enhancement reported before; at 225 °C it is linear at 0.5 Å per cycle after a 20-cycle enhanced start", "asserted",
                "surface_chemistry", "growth_per_cycle", "causes", mentions="ref 7")
c_satc = claim("s9.p7;fig1.cap", "at 125 °C the growth per cycle saturates after a 10 s precursor dose and a 5 s H2S plasma pulse", "asserted", "self_limiting_growth", "growth_per_cycle", "causes")
c_amorph = claim("s10.p1;fig2.cap", "the thermal GaSx film shows no gallium sulfide Bragg peaks in GIWAXS, only the silicon substrate, so it is amorphous, as Meng et al. found", "asserted", "surface_chemistry", "crystallinity", "causes", mentions="ref 7")
c_texture = claim("s10.p1;s10.p4;s10.p5;s10.p6", "the PE-ALD film's arc-shaped GIWAXS intensity on the Debye-Scherrer rings means preferred orientation; the integrated profile matches cubic Ga2S3 (JCPDS 43-0916), and the χ positions of (111), (220) and (311) fit (111) planes parallel to the substrate",
                  "asserted", mentions="ref 10;ref 29;ref 30;ref 31")
c_broad = claim("s10.p4", "the broad GIWAXS peak comes from the grazing geometry and from small crystallites", "hedged", mentions="ref 30")
c_smooth = claim("s10.p7;s10.p10;fig2.cap", "both 150 °C films are smooth and continuous in SEM and AFM, with comparable rms roughness although the PE-ALD film is about three times thicker; at 225 °C the PE-ALD film shows islands and the thermal film none", "asserted",
                 "deposition_temperature", "roughness", "increases")
c_xps = claim("s10.p11", "the PE-ALD film's Ga 2p3/2 and S 2s binding energies match Ga2S3 and its S/Ga ratio means stoichiometric Ga2S3; the thermal film's far lower S/Ga is nonstoichiometric, as before", "asserted",
              "plasma_chemistry", "element_ratio", "increases", mentions="ref 7;ref 32;ref 33")
c_imp = claim("s10.p12;s10.p13", "after the argon sputtering no carbon or oxygen remains in the PE-ALD film, so its surface contamination is adventitious; the thermal film keeps carbon and oxygen in its bulk, most likely from the precursor and air ageing",
              "asserted", "surface_oxidation", "element_fraction", "causes", mentions="ref 7;ref 20")
c_H = claim("s10.p12", "XPS cannot assess hydrogen (ERD would), and the N 1s region overlaps the Ga Auger peaks", "asserted")
c_outlook = claim("s11.p1", "the superiority of PE-ALD over thermal ALD here could inspire similar routes for other sulfides", "hedged")

# ---------------------------------------------------------------- cited
r_meng = f("s6.p4", "cited", "Meng et al.: thermal ALD from Ga2(NMe2)6 and H2S gives amorphous GaSx at 1 to 0.5 Å per cycle over 125–225 °C", quantity="growth_per_cycle", value_min="0.05", value_max="0.1", unit="nm/cycle", data_kind="cited", method="cited",
           mentions="ref 7;1–0.5 Å;125–225 °C")
r_mengS = f("s6.p5", "cited", "Meng et al.: S/Ga between 1.0 and 1.2 over 125–200 °C, with carbon and oxygen in the bulk", quantity="element_ratio", qualifiers="element=S;reference_element=Ga", value_min="1.0", value_max="1.2", data_kind="cited", method="cited",
            mentions="ref 7;125–200 °C")
r_dft = f("s6.p4", "cited", "Schneider et al.: DFT confirms a ligand-exchange mechanism with low barriers, aided by cooperative and crawling effects", data_kind="cited", method="cited", mentions="ref 20")
r_kuhs = f("s6.p4", "cited", "Kuhs et al.: PE-ALD from trimethylgallium and H2S plasma gives amorphous GaSx, at most 0.65 Å per cycle at 100 °C over a 70–350 °C window", quantity="growth_per_cycle", qualifiers="stat=maximum", value="0.065", unit="nm/cycle",
             data_kind="cited", method="cited", mentions="ref 21;100 °C;70–350 °C")
r_meng200 = f("s9.p4", "cited", "Meng et al. report 0.49 Å per cycle for the thermal process at 200 °C", quantity="growth_per_cycle", value="0.049", unit="nm/cycle", data_kind="cited", method="cited", mentions="ref 7;200 °C")
r_meng50 = f("s9.p6", "cited", "the earlier thermal-ALD report saw substrate-enhanced growth over 50 cycles", quantity="cycle_number", value="50", data_kind="cited", method="cited", mentions="ref 7")

# ---------------------------------------------------------------- the recipe
reactor = f("s7.p1", "setting", "the reactor is a home-built pump type suited to H2S", quantity="reactor", value_text="home-built pump-type reactor", data_kind="stated", mentions="ref 25")
pbase = f("s7.p1", "setting", "base pressure 7e-6 mbar", quantity="process_pressure", qualifiers="kind=default", label_as_printed="base pressure", value="7e-6", unit="hPa", data_kind="stated", mentions="7 × 10^-6 mbar")
walls = f("s7.p1", "setting", "the chamber walls were held at 120 °C", quantity="other", label_as_printed="wall temperature", value="120", unit="°C", data_kind="stated")
SUB_SI = f("s7.p1", "setting", "the substrates were silicon (100) with native oxide", quantity="substrate", value_text="si", data_kind="stated", mentions="Si(100), native oxide")
STRUCT = f("s7.p1", "setting", "the films grew on planar substrates", quantity="structure", value_text="planar", data_kind="stated")
RA = f("s7.p1;abs.g2", "setting", "the gallium precursor Ga2(NMe2)6 (98 %, Strem Chemicals)", quantity="reactant_A", value_text="ga2_nme2_6", data_kind="stated")
bub = f("s7.p1", "setting", "the precursor bubbler was heated to 100 °C", quantity="other", label_as_printed="precursor temperature", value="100", unit="°C", data_kind="stated")
line = f("s7.p1", "setting", "the precursor line was held at 110 °C against condensation", quantity="other", label_as_printed="line temperature", value="110", unit="°C", data_kind="stated")
carrier = f("s7.p1", "setting", "argon carried the precursor", quantity="carrier_gas", value_text="ar", data_kind="stated")
pprec = f("s7.p1", "setting", "the precursor pressure was 6e-3 mbar in every process", quantity="partial_pressure", qualifiers="species=ga2_nme2_6", value="6e-3", unit="hPa", data_kind="stated", mentions="6 × 10^-3 mbar")
tA = f("s7.p2", "setting", "precursor pulse 25 s unless stated otherwise", quantity="pulse_time", qualifiers="step=reactant_A;species=ga2_nme2_6", value="25", unit="s", data_kind="stated")
tB = f("s7.p2", "setting", "reactant pulse 25 s unless stated otherwise", quantity="pulse_time", qualifiers="step=reactant_B;species=h2s", value="25", unit="s", data_kind="stated")
pumpA = f("s7.p2", "setting", "pumping to base pressure after the precursor pulse took 50 s", quantity="purge_time", qualifiers="step=purge_A", value="50", unit="s", data_kind="stated")
pumpB = f("s7.p2", "setting", "pumping after the reactant pulse took 90 s", quantity="purge_time", qualifiers="step=purge_B", value="90", unit="s", data_kind="stated")
se = f("s7.p3", "setting", "growth was followed in situ by spectroscopic ellipsometry, fitted with a Cauchy model", method="spectroscopic_ellipsometry")
xrr = f("s7.p3", "setting", "ex situ thicknesses by X-ray reflectivity on a Bruker D8 Discover with Cu Kα", method="xrr", mentions="Bruker D8 Discover")
xrd = f("s7.p3", "setting", "XRD scans on the same Bruker D8 Discover", method="xrd")
giw = f("s7.p3", "setting", "GIWAXS at the NCD-SWEET beamline of ALBA with a Rayonix LX-255HS detector: 12.4 keV, 151.1 mm, 0.19° for the PE-ALD film; 12.95 keV, 129 mm, 0.2° for the thermal film", method="giwaxs",
        mentions="12.4 keV;12.95 keV;151.1 mm;129 mm;0.19°;0.2°;Si (111) monochromator")
sem = f("s7.p4", "setting", "SEM on an FEI Quanta", method="sem", mentions="FEI Quanta")
afm = f("s7.p4", "setting", "AFM in tapping mode on a Bruker Dimension Edge", method="afm", mentions="Bruker Dimension Edge")
xps = f("s7.p4", "setting", "XPS on a Thermo-Scientific Sigma Probe with Al Kα at 50 eV pass energy; depth profiling with an EX05 Ar+ gun at 3 kV and 2 µA; binding energies referenced to adventitious C 1s at 284.6 eV", method="xps",
        mentions="50 eV;3 kV;2 µA;284.6 eV")
uvv = f("s7.p4", "setting", "transmission in the UV-visible on a Perkin Elmer Lambda 1050 for films on quartz", method="uv_vis_spectroscopy", mentions="Perkin Elmer Lambda 1050")

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Mathew et al. 2023: PE-ALD of crystalline Ga2S3 from Ga2(NMe2)6 and H2S plasma against the thermal H2S process", "", evidence="s3.h")
RECIPE = N(f"{K}:recipe", "activity", "gallium sulfide ALD in a home-built pump-type reactor: Ga2(NMe2)6 with H2S (thermal) or H2S/Ar plasma (PE-ALD), 25 s pulses, 125–225 °C", PAPER, evidence="s7.p1;s7.p2", kind="recipe", how="stated",
           label_as_printed="gallium sulfide recipe")
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


put(RECIPE, reactor, pbase, walls, SUB_SI, STRUCT, RA, bub, line, carrier, pprec, tA, tB, pumpA, pumpB, se, xrr, xrd, giw, sem, afm, xps, uvv)
DEP = {}
DEP["t"] = node(f"{K}:dep:thermal", "activity", "thermal ALD: Ga2(NMe2)6 and H2S, 6e-3 mbar during the H2S pulse", RECIPE, evidence="s7.p1", kind="deposition", how="stated", label_as_printed="thermal ALD")
put(DEP["t"], f("s7.p1;abs.g2", "setting", "thermal ALD: the coreactant is H2S gas", quantity="reactant_B", value_text="h2s", data_kind="stated", mentions="thermal"),
    f("s7.p1", "setting", "thermal ALD: process pressure 6e-3 mbar during the H2S pulse", quantity="process_pressure", value="6e-3", unit="hPa", data_kind="stated", mentions="6 × 10^-3 mbar;H2S"),
    f("s6.p4;s10.p1", "setting", "the thermal process deposits amorphous GaSx", quantity="material", value_text="gasx", data_kind="stated", mentions="thermal"))
DEP["p"] = node(f"{K}:dep:pe", "activity", "PE-ALD: Ga2(NMe2)6 and a remote H2S/Ar (1:3) ICP plasma at 200 W, 3e-2 mbar", RECIPE, evidence="s7.p1", kind="deposition", how="stated", label_as_printed="PE-ALD")
put(DEP["p"], f("s7.p1;abs.g2", "setting", "PE-ALD: the coreactant is an H2S/Ar plasma, 1:3, generated remotely by an inductively coupled source", quantity="reactant_B", value_text="h2s", data_kind="stated", mentions="plasma;1:3;Ar"),
    f("s7.p1", "setting", "PE-ALD: ICP power 200 W", quantity="plasma_power", value="200", unit="W", data_kind="stated"),
    f("s7.p1", "setting", "PE-ALD: H2S to Ar ratio 1:3 in the plasma feed", quantity="other", label_as_printed="H2S:Ar ratio", value_text="1:3", data_kind="stated"),
    f("s7.p1", "setting", "PE-ALD: process pressure 3e-2 mbar during the plasma", quantity="process_pressure", value="3e-2", unit="hPa", data_kind="stated", mentions="3 × 10^-2 mbar"),
    f("abs.g3;s10.p4", "setting", "the PE-ALD process deposits Ga2S3", quantity="material", value_text="ga2s3", data_kind="stated", mentions="PE-ALD"))
FILMS = {}


def film(tag, dep, T, label, ev, th=None, quartz=False, extra=(), desc=""):
    e = node(f"{K}:ent:{tag}", "entity", f"{label}", DEP[dep], evidence=ev, how="stated", label_as_printed=label)
    who = desc or label
    own = [f(ev, "setting", f"{who}: deposited at {T} °C", quantity="deposition_temperature", value=T, unit="°C", data_kind="stated", mentions=label)]
    if quartz:
        own.append(f(ev, "setting", f"{who}: on a quartz substrate, fused silica", quantity="substrate", value_text="sio2", data_kind="stated", mentions=label + ";quartz"))
    put(e, *own, *extra)
    if th:
        put(meas(e, "spectroscopic_ellipsometry" if not quartz else "xrr"), f(ev, "observation", f"{who}: about {th} nm thick", quantity="film_thickness", qualifiers="position=planar", value=th, unit="nm", data_kind="stated",
                                                                                    method="spectroscopic_ellipsometry" if not quartz else "xrr", mentions=label))
    FILMS[tag] = e
    return e


# growth per cycle against temperature (Fig. 1(a)): one film per process and temperature
GPC = {("p", "125"): "0.171", ("p", "175"): "0.108", ("p", "200"): "0.108", ("p", "225"): "0.152", ("t", "125"): "0.098", ("t", "200"): "0.028"}
LAB = {"p": "PE-ALD", "t": "thermal ALD"}
for (dep, T), g in GPC.items():
    e = film(f"{dep}{T}", dep, T, f"{LAB[dep]} film, {T} °C", "s9.p1;fig1.cap;fig1a")
    put(meas(e, "spectroscopic_ellipsometry", mode="in_situ"), f("s9.p1;fig1a;fig1.cap", "observation", f"Fig. 1(a): the {LAB[dep]} growth per cycle at {T} °C is {float(g) * 10:g} Å", quantity="growth_per_cycle", qualifiers="position=planar;over=run",
                                                                 value=g, unit="nm/cycle", data_kind="stated", method="spectroscopic_ellipsometry", mentions=f"{LAB[dep]};{T} °C;{float(g) * 10:g} Å"))
e = film("p150", "p", "150", "PE-ALD film, 150 °C", "fig2.cap;fig2b;s10.p1", th="21", extra=[f("fig2.cap;fig2b;fig2f", "setting", "PE-ALD 150 °C: the 21 nm film", quantity="film_thickness", qualifiers="kind=target", value="21", unit="nm", data_kind="stated", mentions="GIWAXS, SEM")])
e = film("t150", "t", "150", "thermal ALD film, 150 °C", "fig2.cap;fig2a;s10.p1", th="10", extra=[f("fig2.cap;fig2a;fig2e;fig2g", "setting", "thermal 150 °C: the 10 nm film", quantity="film_thickness", qualifiers="kind=target", value="10", unit="nm", data_kind="stated", mentions="GIWAXS, SEM, AFM")])
film("p150_42", "p", "150", "PE-ALD film, 150 °C, 42 nm", "fig2.cap;fig2h", th="42", desc="the thicker PE-ALD film of the AFM scan")
film("p150_q", "p", "150", "PE-ALD film on quartz, 150 °C, 48 nm", "fig4.cap;fig4a;s10.p15", th="48", quartz=True, desc="the PE-ALD film on quartz")
film("t150_q", "t", "150", "thermal ALD film on quartz, 150 °C, 51 nm", "fig4.cap;fig4a;s10.p15", th="51", quartz=True, desc="the thermal film on quartz")
film("p225_20", "p", "225", "PE-ALD film, 225 °C, 20 nm", "fig2.cap;fig2i", th="20", desc="the PE-ALD film of the SEM image at the highest temperature")
film("t225_10", "t", "225", "thermal ALD film, 225 °C, 10 nm", "fig2.cap;fig2j", th="10", desc="the thermal film of the SEM image at the highest temperature")
e225 = film("t225", "t", "225", "thermal ALD film, 225 °C", "s9.p6;fig1b;fig1.cap")
# Fig. 1(b): thickness against cycles, in situ, four films
for dep, T, lab in (("p", "125", "PE ALD@125°C"), ("p", "225", "PE ALD@225°C"), ("t", "125", "T-ALD@125°C"), ("t", "225", "T-ALD@225°C")):
    e = FILMS[f"{dep}{T}"]
    FX[e]["evidence"] += ";fig1b"
    put(meas(e, "spectroscopic_ellipsometry", mode="in_situ"), f("fig1b;fig1.cap;s9.p5", "observation", f"Fig. 1(b): the thickness of the {LAB[dep]} film at {T} °C against the cycle number, in situ", quantity="film_thickness", qualifiers="position=planar",
                                                                 method="spectroscopic_ellipsometry", mentions=f"{lab};Fig. 1(b)"))
nuc_p125 = f("s9.p6", "observation", "PE-ALD at 125 °C: the substrate-enhanced regime spans about three cycles", quantity="other", label_as_printed="enhanced-growth cycles", value="3", data_kind="stated",
             method="spectroscopic_ellipsometry")
nuc_t225 = f("s9.p6", "observation", "thermal ALD at 225 °C: a substrate-enhanced start over 20 cycles, then linear growth", quantity="other", label_as_printed="enhanced-growth cycles", value="20", data_kind="stated",
             method="spectroscopic_ellipsometry")
gpc_t225 = f("s9.p6", "observation", "thermal ALD at 225 °C: 0.5 Å per cycle in the linear regime", quantity="growth_per_cycle", qualifiers="position=planar;over=run", value="0.05", unit="nm/cycle", data_kind="stated", method="spectroscopic_ellipsometry",
             mentions="0.5 Å")
put(meas(FILMS["p125"], "spectroscopic_ellipsometry"), nuc_p125)
put(meas(e225, "spectroscopic_ellipsometry", mode="in_situ"), nuc_t225, gpc_t225)
# Fig. 1(c): saturation at 125 °C
sat_A = f("s9.p7;fig1c;fig1.cap", "observation", "Fig. 1(c): at 125 °C the growth per cycle rises slowly with the Ga2(NMe2)6 pulse and is constant from a 10 s dose, the plasma fixed at 25 s", quantity="other",
            label_as_printed="saturating precursor pulse", value="10", unit="s", data_kind="stated", method="spectroscopic_ellipsometry", mentions="Ga₂(NMe₂)₆;Fig. 1(c)")
sat_B = f("s9.p7;fig1c;fig1.cap", "observation", "Fig. 1(c): the H2S plasma saturates at a 5 s pulse with the precursor fixed at 25 s", quantity="other", label_as_printed="saturating plasma pulse",
            value="5", unit="s", data_kind="stated", method="spectroscopic_ellipsometry", mentions="H₂S plasma;Fig. 1(c)")
put(meas(FILMS["p125"], "spectroscopic_ellipsometry"), sat_A, sat_B)
# Fig. 2: GIWAXS, XRD, SEM, AFM at 150 °C and SEM at 225 °C
P150, T150 = FILMS["p150"], FILMS["t150"]
put(meas(T150, "giwaxs"), f("fig2a;fig2.cap;s10.p1", "observation", "Fig. 2(a): the thermal GaSx film's GIWAXS at 0.2° shows no gallium sulfide Bragg peak, only the silicon substrate", quantity="crystallinity", value_text="amorphous", data_kind="measured",
                             method="giwaxs", mentions="Fig. 2(a);0.2°"))
put(meas(P150, "giwaxs"), f("fig2b;fig2.cap;s10.p1", "observation", "Fig. 2(b): the PE-ALD film's GIWAXS at 0.19° shows arcs on the Debye-Scherrer rings, a textured crystalline film", quantity="crystallinity", value_text="crystalline", data_kind="measured",
                             method="giwaxs", mentions="Fig. 2(b);0.19°"),
    f("fig2d;fig2.cap;s10.p4", "observation", "Fig. 2(d): the azimuthally integrated profile matches cubic Ga2S3 (JCPDS 43-0916)", quantity="phase", qualifiers="species=ga2s3", value_text="detected", data_kind="measured", method="giwaxs",
      mentions="JCPDS 43-0916;cubic;Fig. 2(d)"),
    f("s10.p6;s11.p1", "observation", "the film is preferentially oriented with [111] out of plane, the (111) planes parallel to the substrate", quantity="other", label_as_printed="preferred orientation", value_text="[111] out of plane", data_kind="measured", method="giwaxs"),
    f("fig2c;fig2.cap;s10.p5", "observation", "Fig. 2(c): in the (q, χ) plot the (111) plane lies at q = 20.7 nm-1", quantity="other", label_as_printed="q(111)", value="20.7", unit="1/nm", data_kind="measured", method="giwaxs", mentions="Fig. 2(c)"),
    f("fig2c;s10.p5", "observation", "the (220) plane lies at q = 34.2 nm-1", quantity="other", label_as_printed="q(220)", value="34.2", unit="1/nm", data_kind="measured", method="giwaxs"),
    f("fig2c;s10.p5", "observation", "the (311) plane lies at q = 39.4 nm-1", quantity="other", label_as_printed="q(311)", value="39.4", unit="1/nm", data_kind="measured", method="giwaxs"),
    f("s10.p5", "observation", "the (111) diffraction appears at χ = 0.2° and 70.2°: out of plane, and the equivalent (11-1) planes 70.5° away", quantity="other", label_as_printed="χ of (111)", value="0.2", unit="°", data_kind="measured", method="giwaxs",
      mentions="70.2°;70.5°"),
    f("s10.p6", "observation", "the (220) spots sit 35.2° from (111), as (111)-parallel crystallites require", quantity="other", label_as_printed="χ of (220)", value="35.2", unit="°", data_kind="measured", method="giwaxs"),
    f("s10.p6", "observation", "the (311) spots sit 29.4° from (111)", quantity="other", label_as_printed="χ of (311)", value="29.4", unit="°", data_kind="measured", method="giwaxs"))
put(meas(T150, "xrd"), f("fig2d;fig2.cap", "observation", "Fig. 2(d): the thermal GaSx profile has no Ga2S3 peaks", quantity="phase", qualifiers="species=ga2s3", value_text="not detected", data_kind="measured", method="xrd", mentions="Fig. 2(d);GaSx"))
put(meas(T150, "sem"), f("fig2e;fig2.cap;s10.p7", "observation", "Fig. 2(e): the 10 nm thermal film is smooth and continuous in SEM", method="sem", mentions="Fig. 2(e)"))
put(meas(P150, "sem"), f("fig2f;fig2.cap;s10.p7", "observation", "Fig. 2(f): the 21 nm PE-ALD film shows no SEM contrast, a smooth film", method="sem", mentions="Fig. 2(f)"))
afm_area = f("s10.p7;fig2.cap", "setting", "the AFM scans cover 5 × 5 µm²", quantity="other", label_as_printed="AFM scan size", value="5", unit="µm", data_kind="stated", method="afm", mentions="5 × 5 µm2")
put(meas(T150, "afm"), afm_area, f("fig2g;fig2.cap;s10.p7;s10.p10", "observation", "Fig. 2(g): rms roughness 0.5 nm for the 10 nm thermal film", quantity="roughness", label_as_printed="rms roughness", value="0.5", unit="nm", data_kind="measured",
                          method="afm", mentions="Fig. 2(g);5 × 5 µm2"))
put(meas(FILMS["p150_42"], "afm"), f("fig2h;fig2.cap;s10.p10", "observation", "Fig. 2(h): rms roughness 0.8 nm for the thicker PE-ALD film", quantity="roughness", label_as_printed="rms roughness", value="0.8", unit="nm", data_kind="measured", method="afm",
                                     mentions="Fig. 2(h)"))
put(meas(FILMS["p225_20"], "sem"), f("fig2i;fig2.cap;s10.p10;s9.p6", "observation", "Fig. 2(i): the PE-ALD film grown at 225 °C shows island-like crystalline grains", method="sem", mentions="Fig. 2(i)"))
put(meas(FILMS["t225_10"], "sem"), f("fig2j;fig2.cap;s10.p10", "observation", "Fig. 2(j): the thermal film grown at 225 °C shows no SEM contrast", method="sem", mentions="Fig. 2(j)"))
# Fig. 3: XPS at 150 °C
put(meas(P150, "xps"), f("fig3a;fig3.cap;s10.p11", "observation", "Fig. 3(a): the PE-ALD film's Ga 2p3/2 lies at about 1118 eV", quantity="binding_energy", qualifiers="element=Ga", label_as_printed="Ga 2p3/2", value="1118", unit="eV", data_kind="measured", method="xps",
                         mentions="Fig. 3(a);ref 32;ref 33"),
    f("fig3b;fig3.cap;s10.p11", "observation", "Fig. 3(b): the PE-ALD film's S 2s lies at 225.9 eV", quantity="binding_energy", qualifiers="element=S", label_as_printed="S 2s", value="225.9", unit="eV", data_kind="measured", method="xps", mentions="Fig. 3(b)"),
    f("s10.p11;abs.g4", "derived", "the PE-ALD film's S/Ga ratio is 1.56 from the Ga 2p3/2 and S 2s areas after a Tougaard U2 background (1,0,0), stoichiometric Ga2S3", quantity="element_ratio", qualifiers="element=S;reference_element=Ga", value="1.56",
      data_kind="computed_by_authors", method="xps", mentions="Tougaard"),
    f("fig3c;fig3d;fig3.cap;s10.p12", "observation", "Fig. 3(c),(d): the PE-ALD film carries much carbon and oxygen at the surface; after 100 s of Ar sputtering neither is detected", quantity="element_fraction", qualifiers="element=C", label_as_printed="C after sputtering",
      value_text="not_detected", data_kind="measured", method="xps", mentions="Fig. 3(c);Fig. 3(d);100 s"),
    f("fig3d;fig3.cap;s10.p12", "observation", "Fig. 3(d): no oxygen in the bulk of the PE-ALD film after sputtering", quantity="element_fraction", qualifiers="element=O", label_as_printed="O after sputtering", value_text="not_detected", data_kind="measured", method="xps", mentions="Fig. 3(d)"))
put(meas(T150, "xps"), f("fig3a;fig3.cap;s10.p11", "observation", "Fig. 3(a): the thermal film's Ga 2p3/2 lies at 1117.9 eV, trivalent gallium", quantity="binding_energy", qualifiers="element=Ga", label_as_printed="Ga 2p3/2", value="1117.9", unit="eV",
                         data_kind="measured", method="xps", mentions="Fig. 3(a);thermal"),
    f("fig3b;fig3.cap;s10.p11", "observation", "Fig. 3(b): the thermal film's S 2s lies at 225.6 eV", quantity="binding_energy", qualifiers="element=S", label_as_printed="S 2s", value="225.6", unit="eV", data_kind="measured", method="xps", mentions="Fig. 3(b);thermal"),
    f("s10.p11;s6.p5", "derived", "the thermal film's S/Ga ratio is 0.5, nonstoichiometric", quantity="element_ratio", qualifiers="element=S;reference_element=Ga", value="0.5", data_kind="computed_by_authors", method="xps", mentions="thermal"),
    f("fig3e;fig3f;fig3.cap;s10.p12", "observation", "Fig. 3(e),(f): the thermal film keeps about 8 % carbon and oxygen after 100 s of sputtering", quantity="element_fraction", qualifiers="element=C", label_as_printed="C after sputtering", value="8", unit="%", data_kind="measured",
      method="xps", mentions="Fig. 3(e);Fig. 3(f);100 s;oxygen too"),
    f("fig3f;fig3.cap;s10.p12", "observation", "Fig. 3(f): about 8 % oxygen remains in the thermal film's bulk", quantity="element_fraction", qualifiers="element=O", label_as_printed="O after sputtering", value="8", unit="%", data_kind="measured", method="xps", mentions="Fig. 3(f)"))
sput = f("s7.p4;s10.p12", "setting", "surface contamination was removed by 100 s of argon sputtering before the bulk XPS", quantity="other", label_as_printed="sputter time", value="100", unit="s", data_kind="stated", method="xps")
put(meas(P150, "xps"), sput)
C.spread(sput, [meas(P150, "xps"), meas(T150, "xps")], {meas(T150, "xps"): "thermal film"})
# Fig. 4: optics on quartz
PQ, TQ = FILMS["p150_q"], FILMS["t150_q"]
wl = f("s10.p15;fig4.cap", "setting", "transmittance was recorded over 250–1100 nm", quantity="other", label_as_printed="wavelength range", value_min="250", value_max="1100", unit="nm", data_kind="stated", method="uv_vis_spectroscopy")
put(meas(PQ, "uv_vis_spectroscopy"), wl, f("fig4a;fig4.cap;s10.p15;abs.g5", "observation", "Fig. 4(a): the crystalline PE-ALD film transmits 70 % in the near-infrared and visible", quantity="other", label_as_printed="transmittance", value="70", unit="%",
                                        data_kind="measured", method="uv_vis_spectroscopy", mentions="Fig. 4(a)"),
    f("fig4b;fig4.cap;s10.p15;abs.g5", "derived", "Fig. 4(b): the Tauc plot, (αhν)² against hν, gives a direct band gap of 3.2 eV for the crystalline Ga2S3", quantity="other", label_as_printed="band gap", value="3.2", unit="eV", data_kind="computed_by_authors",
      method="calculation", mentions="PE-ALD @150°C;Fig. 4(b);ref 34;ref 35"))
put(meas(TQ, "uv_vis_spectroscopy"), f("fig4a;fig4.cap;s10.p15", "observation", "Fig. 4(a): the amorphous thermal film transmits 90 %", quantity="other", label_as_printed="transmittance", value="90", unit="%", data_kind="measured", method="uv_vis_spectroscopy",
                                        mentions="Fig. 4(a);thermal"),
    f("fig4b;fig4.cap;s10.p15", "derived", "Fig. 4(b): the amorphous GaSx film's Tauc gap is 3.6 eV, above the Ga2S3 literature, attributed to oxygen", quantity="other", label_as_printed="band gap", value="3.6", unit="eV", data_kind="computed_by_authors",
      method="calculation", mentions="Thermal ALD@150°C;Fig. 4(b);ref 36"))
C.spread(wl, [meas(PQ, "uv_vis_spectroscopy"), meas(TQ, "uv_vis_spectroscopy")], {meas(TQ, "uv_vis_spectroscopy"): "thermal film"})
C.spread(afm_area, [meas(T150, "afm"), meas(FILMS["p150_42"], "afm")], {meas(FILMS["p150_42"], "afm"): "PE-ALD film"})
C.identity(K, "not_stated", [FILMS["p225"], FILMS["p225_20"]], "whether the PE-ALD film imaged by SEM at the highest temperature is the film of the growth curve there is not stated", "fig2.cap;s9.p6", parent=DEP["p"])
C.identity(K, "not_stated", [e225, FILMS["t225_10"]], "whether the thermal film imaged by SEM at the highest temperature is the film of the growth curve there is not stated", "fig2.cap;s9.p6", parent=DEP["t"])
# cited under reference nodes
REFS = {n: node(f"{K}:refs:{n}", "cited", f"cited work, reference {n} of the paper", PAPER, evidence=ev, label_as_printed=f"ref. {n}") for n, ev in (("7", "s6.p4"), ("20", "s6.p4"), ("21", "s6.p4"))}
put(REFS["7"], r_meng, r_mengS, r_meng200, r_meng50)
put(REFS["20"], r_dft)
put(REFS["21"], r_kuhs)
BY_TEXT = {"a new PE-ALD process, hexakis": [FILMS["p150"], FILMS["t150"]], "the existing ALD routes to Ga2S3": [r_meng, r_mengS, r_kuhs], "the PE-ALD process deposits crystalline, smooth": [FILMS["p150"], FILMS["p125"]],
           "GIWAXS shows the as-deposited Ga2S3 is cubic": [FILMS["p150"]], "the crystalline Ga2S3 film is less transparent": [PQ, TQ], "Ga2S3 is a wide-gap III-VI semiconductor": [c_cubic] if False else [FILMS["p150"]],
           "ALD's self-limiting reactions give": [sat_A, sat_B], "recent PE-ALD work tailors": [FILMS["p150"]], "to the authors' knowledge crystalline Ga2S3": [FILMS["p150"]], "the 25 s pulses are well above saturation": [tA, tB, sat_A, sat_B],
           "the ellipsometric thicknesses": [se, xrr], "across the temperature window the PE-ALD growth per cycle": [FILMS["p125"], FILMS["p175"], FILMS["p225"], FILMS["t125"], FILMS["t200"]], "the higher growth per cycle of PE-ALD": [FILMS["p200"], FILMS["t200"], r_meng200],
           "PE-ALD shows substrate-enhanced growth": [nuc_p125, FILMS["p225"]], "the thermal process grows linearly at 125 °C": [FILMS["t125"], nuc_t225, gpc_t225, r_meng50], "at 125 °C the growth per cycle saturates": [sat_A, sat_B],
           "the thermal GaSx film shows no gallium sulfide": [T150], "the PE-ALD film's arc-shaped GIWAXS": [P150], "the broad GIWAXS peak": [P150], "both 150 °C films are smooth": [T150, FILMS["p150_42"], FILMS["p225_20"], FILMS["t225_10"]],
           "the PE-ALD film's Ga 2p3/2 and S 2s": [P150, T150], "after the argon sputtering": [P150, T150], "XPS cannot assess hydrogen": [P150], "the superiority of PE-ALD": [FILMS["p150"]]}
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
GROUPS = [(f"{K}:grp:gpc_pe", "series", "deposition_temperature", "the PE-ALD temperature series of Fig. 1(a): 125 to 225 °C", "fig1.cap", c_gpcT, [FILMS[f"p{T}"] for T in ("125", "175", "200", "225")]),
          (f"{K}:grp:gpc_t", "series", "deposition_temperature", "the thermal temperature series of Fig. 1(a): 125 and 200 °C", "fig1.cap", c_gpcT, [FILMS["t125"], FILMS["t200"]]),
          (f"{K}:grp:growth", "series", "material", "the four in situ growth curves of Fig. 1(b): PE-ALD and thermal at 125 and 225 °C", "fig1.cap", c_nucl, [FILMS["p125"], FILMS["p225"], FILMS["t125"], e225]),
          (f"{K}:grp:films150", "series", "material", "the two 150 °C films compared by GIWAXS, SEM, XPS: Ga2S3 against GaSx", "fig2.cap;fig3.cap", c_xps, [P150, T150]),
          (f"{K}:grp:optics", "series", "material", "the two films on quartz compared optically: Fig. 4", "fig4.cap", c_opt, [PQ, TQ]),
          (f"{K}:grp:afm", "series", "material", "the two films compared by AFM: 42 nm Ga2S3 against 10 nm GaSx", "fig2.cap", c_smooth, [FILMS["p150_42"], T150]),
          (f"{K}:grp:sem225", "series", "material", "the two 225 °C films compared by SEM", "fig2.cap", c_smooth, [FILMS["p225_20"], FILMS["t225_10"]])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s10.p12", "XPS cannot see hydrogen, and the N 1s region is hidden by the Ga Auger peaks; the impurity statements cover carbon and oxygen only.", [P150, T150], "", ""),
    ("s7.p2", "The reactant pulse time, known to affect morphology, was not studied; all films used 25 s pulses well above saturation.", [tA, tB], "", ""),
    ("s10.p4", "The GIWAXS peaks are broadened by the grazing geometry and by small crystallites.", [P150], "", ""),
    ("fig2.cap;s10.p11", "The XPS films at 150 °C have no stated thickness; the facts attach them to the 21 nm (PE-ALD) and 10 nm (thermal) films of Fig. 2.", [P150, T150], "", ""),
    ("s10.p15", "The 3.6 eV gap of the amorphous film is above the Ga2S3 literature and is attributed to oxygen impurities.", [TQ], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
# P131: a claim is a triple or it is not a claim; every claim without a full triple re-typed by the one rule (facts.retype)
BG = 'background, motivation, prior art or scope'
RETYPE = {
    'abs.g2#2': ('removed', BG),
    'abs.g1#1': ('removed', BG),
    's6.p5#1': ('removed', BG),
    's6.p5#2': ('removed', BG),
    's11.p1#1': ('removed', BG),
    's7.p2#1': ('duplicate', 's7.p2#6'),
    's10.p4#1': ('duplicate', 's10.p4#2'),
    's10.p12#2': ('duplicate', 's10.p12#3'),
    's7.p3#1': ('model', 'mat23:recipe'),
    'abs.g5#1': ('observation', 'mat23:cmp:optics'),
    's10.p1#2': ('observation', 'mat23:meas:ent:p150:giwaxs', {'links': 'mat23:fig2d#1;mat23:s10.p6#1;mat23:ent:p150'}),
    'abs.g2#1': ('triple', 'plasma_chemistry', 'causes', 'crystallinity'),
}
C.retype(K, RETYPE)
write(K, PID)
