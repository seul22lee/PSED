#!/usr/bin/env python3
"""Stage 2 facts for gao15 (10.1116_1.4903941, Gao, Arpiainen, Puurunen 2015, J. Vac. Sci. Technol. A letter: the first microscopic
silicon lateral high-aspect-ratio (LHAR) test structures, their fabrication, and three ways of reading ALD Al2O3 and TiO2 conformality in
them: infrared and visible microscopy through the membrane, reflectometer line scans after peeling the membrane, SEM cross sections).
Text and captions; the paper has no numbered table (the Fig. 1 dimension table is an image the figure stage did not read as cells); the
two Fig. 5 line scans are imported records (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1116_1.4903941.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "gao15", "10.1116_1.4903941"


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h", "heading")
NK("s0.p1;s1.p1;s1.p2;s1.p3;s4.p1;s4.p2;s6.p2", "front matter, authors, affiliation, dates, footnote")
NK("s2.p1;s2.p2;s2.p3;s2.p4;s2.p5;s2.p6", "the publisher's related-article box")
NK("s4.p3", "the abstract printed again as a body paragraph (knowledge under abs.g1-g3)")
NK("s6.p9;s6.p10;s6.p14", "a section heading set as a paragraph")
NK("s6.p7;s6.p17;s7.p3;s7.p4", "a caption printed again as a body paragraph; the knowledge is under the figure's caption element")
NK("s9.p1;s9.p2", "acknowledgements")
NK("s9.p6;s9.p7;s9.p10", "reference list entries not cited for a value")
NK("fig1.cap;fig1", "the chip layout as a schematic and a dimension table drawn as an image: the dimensions the text states are facts of the chip entity; the table's cells were not read")

# ---------------------------------------------------------------- claims of abstract, introduction and conclusions
c_new = claim("abs.g1;s5.p5;s8.p1", "silicon-based microscopic LHAR test structures, a lateral cavity under a pillar-supported roof, serve the conformality analysis of ALD and other CVD films", "asserted")
c_space = claim("abs.g3;s8.p2", "the microscopic LHAR structures open a parameter space of aspect ratios beyond earlier conformality studies", "asserted", "aspect_ratio", "penetration_depth", "causes")
c_conf = claim("s5.p1;s5.p2;s9.p3;s9.p4;s9.p8;s9.p9;s9.p11;s9.p12", "conformality follows from self-terminating ALD chemistry, yet even ideal processes need longer pulsing in demanding 3D features, and secondary reactions reduce it", "asserted",
               "self_limiting_growth", "normalized_thickness", "causes", mentions="ref 1;ref 2;ref 3;ref 6;ref 7;ref 9;ref 10")
c_lack = claim("s5.p3;s5.p4", "most ALD studies skip conformality for lack of easy, simple and available test structures", "hedged")
c_mol = claim("s5.p5", "with a limiting dimension of hundreds of nanometres the microscopic LHAR is in molecular flow at typical ALD pressures of one to tens of millibars, where the mean free path is micrometres to tens of micrometres",
              "asserted", "gas_diffusion", "penetration_depth", "causes")
mfp = f("s5.p5", "cited", "at one to tens of millibars the mean free path is of the order of micrometres to tens of micrometres", quantity="mean_free_path", value_min="1", value_max="100", unit="µm", data_kind="stated",
        method="cited", mentions="1 µm to 100 µm, read as 'micrometers to tens of micrometers'")
p_ald = f("s5.p5", "cited", "typical ALD pressures run from one to tens of millibars", quantity="process_pressure", value_min="1", value_max="100", unit="hPa", data_kind="stated", method="cited",
          mentions="1 mbar to tens of mbar")
c_uses = claim("s8.p2", "the structures could tune processes for a target aspect ratio, screen up-scalability through thickness gradients from decomposition or by-product readsorption, and feed kinetic models under molecular flow", "hedged")
c_agree = claim("s8.p1", "nondestructive microscopy, reflectometry after membrane removal and SEM of cross sections gave the same qualitative penetration depth", "asserted")
c_shape = claim("s8.p1;s6.p22", "Al2O3 is uniform along the cavity until its termination starts, while the TiO2 thickness decreases slowly but continuously", "asserted", "surface_chemistry", "normalized_thickness", "causes")
# cited state of the art
r_tr5 = f("s5.p4;s9.p5", "cited", "vertical trenches of modest depth-to-width aspect ratio, about 5:1", quantity="aspect_ratio", value="5", data_kind="cited", method="cited", mentions="ref 3")
r_tr40 = f("s5.p4;s9.p13;s9.p14", "cited", "more demanding vertical trenches of aspect ratio about 40:1", quantity="aspect_ratio", value="40", data_kind="cited", method="cited", mentions="ref 11;ref 12")
r_mac = f("s5.p4;s9.p15;s9.p16", "cited", "macroscopic LHAR structures gave thickness profiles along the gap up to aspect ratio 200:1", quantity="coated_aspect_ratio", qualifiers="level=front_end", value="200", data_kind="cited", method="cited",
          mentions="ref 13;ref 14")
r_gap = f("s5.p4", "cited", "the macroscopic LHAR gap is of the order of 100 µm", quantity="feature_width", value="100", unit="µm", data_kind="cited", method="cited", mentions="ref 13;ref 14")
r_vac = f("s5.p4", "cited", "molecular flow in the macroscopic LHAR needs high vacuum, about 1e-4 Torr", quantity="process_pressure", value="1e-4", unit="Torr", data_kind="cited", method="cited", mentions="ref 13;ref 14")
c_mac = claim("s5.p4", "because of its 100 µm gap the macroscopic LHAR reaches molecular flow only in high vacuum", "asserted", "gas_diffusion", "penetration_depth", "limits", supports=[r_gap, r_vac])
r_plug = f("s6.p3;s9.p17;s9.p18", "cited", "the patented plug-up sequence: release holes etched, covered with porous polysilicon with nanometre pinholes, vapour-HF etch of the sacrificial oxide through the pinholes, then sealing by a second polysilicon layer",
           data_kind="cited", method="cited", mentions="ref 15;ref 16")

# ---------------------------------------------------------------- definitions (P89)
d_ar = f("s5.p4;fig1.cap", "definition", "AR, the aspect ratio, is the depth-to-width ratio of a feature; for the LHAR the cavity length over its height, written n:1", quantity="aspect_ratio", term="AR|aspect ratio",
         definition_note="cavity length over cavity height, written n:1")
d_gap = f("abs.g2;s6.p1;fig3.cap;fig5.cap", "definition", "the gap height (also cavity height, gap size) is the height of the lateral cavity, set by the thermal oxide thickness", quantity="feature_width",
          term="gap height|gap size|cavity height|LHAR gap size|LHAR gap height", definition_note="the lateral cavity's height, the limiting dimension")
d_len = f("abs.g2;fig1.cap", "definition", "the cavity length is the lateral extent of the cavity from the central opening", quantity="feature_depth", term="cavity length|lateral length")
d_pd = f("s6.p12;s6.p13", "definition", "the penetration depth is how far the film extends into the cavity from the central opening", quantity="penetration_depth", term="penetration depth|film penetration depth",
         definition_note="the visible film extent from the opening, unless a thickness level is named")
d_lhar = f("abs.g1;abs.g2", "definition", "a microscopic LHAR structure is a lateral high-aspect-ratio cavity in silicon, its roof carried by pillars, with a central opening", term="LHAR|microscopic LHAR")

# ---------------------------------------------------------------- the chip: fabrication and dimensions
wafer = f("s6.p1", "setting", "the structures were made on 150 mm silicon wafers by standard surface micromachining", quantity="other", label_as_printed="wafer diameter", value="150", unit="mm", data_kind="stated")
oxide = f("s6.p1;abs.g2", "setting", "a thermal oxide defines the gap height: 200, 500 and 1000 nm, a 200–1000 nm range", quantity="feature_width", label_as_printed="gap height", value_min="200", value_max="1000", unit="nm",
          data_kind="stated", mentions="200 nm;500 nm;1000 nm")
poly1 = f("s6.p3", "setting", "a polycrystalline silicon layer of about 1.4 µm was deposited on the oxide by LPCVD", quantity="other", label_as_printed="polysilicon membrane", value="1.4", unit="µm", data_kind="stated")
seal = f("s6.p3", "setting", "a second polysilicon layer of about 400 nm closes the pinholes", quantity="other", label_as_printed="sealing polysilicon", value="400", unit="nm", data_kind="stated")
port = f("s6.p3", "setting", "a port opening was dry-etched through the membrane with fluorine chemistry", data_kind="stated")
pil_d = f("s6.x1;s6.p4", "setting", "a timed vapour-HF etch leaves unetched oxide pillars that keep the membrane off the substrate; the pillars are 10 µm apart", quantity="other", label_as_printed="pillar spacing", value="10", unit="µm",
          data_kind="stated")
chip = f("s6.p5", "setting", "the wafers were diced into chips of 20 × 25 mm² for the coating experiments", quantity="other", label_as_printed="chip size", value_text="20 × 25 mm2", data_kind="stated", mentions="20 mm;25 mm")
L_r = f("abs.g2", "setting", "the cavity length ranges, for example, from 20 to 5000 µm", quantity="feature_depth", label_as_printed="cavity length", value_min="20", value_max="5000", unit="µm", data_kind="stated")
ar_r = f("abs.g2;s8.p1", "derived", "the aspect ratios run from 20:1 to 25 000:1", quantity="aspect_ratio", value_min="20", value_max="25000", data_kind="computed_by_authors", method="calculation", inputs=[L_r, oxide])
o_sem2 = f("fig2.cap;fig2;s6.x1", "observation", "Fig. 2: SEM cross sections of uncoated 500 nm cavities of aspect ratio 40:1 and 1000:1 show the membrane held off the substrate by the oxide pillars", method="sem",
           quantity="feature_width", value="500", unit="nm", data_kind="stated", mentions="AR 40:1;AR 1000:1;Fig. 2")
ar_sem = f("fig2.cap", "setting", "the upper Fig. 2 structure has aspect ratio 40:1", quantity="aspect_ratio", value="40", data_kind="stated", mentions="top")
ar_sem2 = f("fig2.cap", "setting", "the lower Fig. 2 structure has aspect ratio 1000:1", quantity="aspect_ratio", value="1000", data_kind="stated", mentions="bottom")
c_open = claim("s6.p11;s6.p15", "the film under the membrane can be inspected through it by visible or infrared microscopy, or after peeling the membrane off with adhesive tape", "asserted")

# ---------------------------------------------------------------- the ALD recipe
reactor = f("s6.p5", "setting", "the films were grown in a Picosun R-150 reactor", quantity="reactor", value_text="Picosun R-150", data_kind="stated")
ptot = f("s6.p5", "setting", "the reactor pressure was typically 1–2 mbar", quantity="process_pressure", value_min="1", value_max="2", unit="hPa", data_kind="stated")
carrier = f("s6.p5", "setting", "nitrogen was the carrier gas", quantity="carrier_gas", value_text="n2", data_kind="stated")
T_r = f("s6.p5", "setting", "the ALD temperature was varied between 110 and 300 °C", quantity="deposition_temperature", value_min="110", value_max="300", unit="°C", data_kind="stated")
tA = f("s6.p5", "setting", "a typical cycle: 100 ms Me3Al exposure", quantity="pulse_time", qualifiers="step=reactant_A;species=tma", value="0.1", unit="s", data_kind="stated", mentions="100 ms")
tA2 = f("s6.p5", "setting", "or a 100 ms TiCl4 exposure", quantity="pulse_time", qualifiers="step=reactant_A;species=ticl4", value="0.1", unit="s", data_kind="stated", mentions="100 ms")
pA = f("s6.p5", "setting", "then a 4 s purge", quantity="purge_time", qualifiers="step=purge_A", value="4", unit="s", data_kind="stated")
tB = f("s6.p5", "setting", "a 100 ms water exposure", quantity="pulse_time", qualifiers="step=reactant_B;species=h2o", value="0.1", unit="s", data_kind="stated", mentions="100 ms")
pB = f("s6.p5", "setting", "and again a 4 s purge", quantity="purge_time", qualifiers="step=purge_B", value="4", unit="s", data_kind="stated")
rep = f("s6.p5", "setting", "the cycle was repeated until the desired thickness", data_kind="stated")
RB = f("s6.p5;abs.g3", "setting", "deionized water was the second reactant", quantity="reactant_B", value_text="h2o", data_kind="stated")
RA_al = f("s6.p5;abs.g3", "setting", "trimethylaluminium (SAFC Hitech, electronic grade) for Al2O3", quantity="reactant_A", value_text="tma", data_kind="stated")
RA_ti = f("s6.p5;abs.g3", "setting", "titanium tetrachloride (SAFC Hitech, electronic grade) for TiO2", quantity="reactant_A", value_text="ticl4", data_kind="stated")
STRUCT = f("abs.g1;s6.p1", "setting", "the test structure is the microscopic LHAR chip of this work", quantity="structure", value_text="pillarhall_1", data_kind="stated")
SUBSTR = f("s6.p1;s6.p16", "setting", "the film grows on the silicon of the cavity floor and on the polysilicon roof", quantity="substrate", value_text="si", data_kind="stated")
instr = f("s6.p6;s6.p8", "setting", "Nikon visible and infrared microscopes, a FilmTek 2000M reflectometer and a Zeiss LEO1560 SEM analysed the coated and uncoated chips", method="reflectometry",
          mentions="Nikon;FilmTek 2000M;Zeiss LEO1560")
spot = f("s6.p8", "setting", "the reflectometer spot is about 5 × 5 µm² at 50× magnification", quantity="probe_resolution", value="5", unit="µm", data_kind="stated", method="reflectometry", mentions="5 × 5 µm2")
mag = f("s6.p8", "setting", "the reflectometer objective magnification is 50×", quantity="objective_magnification", value="50", data_kind="stated", method="reflectometry")

# ---------------------------------------------------------------- Fig. 3: infrared top views, nine films
o_sym = f("s6.p12;fig3.cap", "observation", "Fig. 3: each film reaches equally far on both sides of the central opening", method="infrared_microscopy", mentions="Fig. 3")
o_100 = f("s6.p12", "observation", "in 500 nm gaps the films extend of the order of 100 µm from the opening", quantity="penetration_depth", qualifiers="level=front_end", value="100", unit="µm", data_kind="stated",
          method="infrared_microscopy")
c_alT = claim("s6.p12", "for Al2O3 the penetration depth increases as the ALD temperature decreases", "asserted", "deposition_temperature", "penetration_depth", "decreases")
c_tiT = claim("s6.p12", "for TiO2 a falling temperature first lengthens, then shortens the penetration depth", "asserted", "deposition_temperature", "penetration_depth", "causes")
c_why = claim("s6.p12", "the temperature trends come from changes in the ALD reaction mechanisms and in reaction and diffusion kinetics; a dedicated study would be needed", "hedged", "surface_chemistry", "penetration_depth", "causes")
c_gap = claim("s6.p13;fig3.cap", "the penetration depth grows with the gap height: about 25, 90 and 155 µm for gaps of 200, 500 and 1000 nm", "asserted", "feature_width", "penetration_depth", "increases")
PD3 = {}
for gap, pd in (("200", "25"), ("500", "90"), ("1000", "155")):
    PD3[gap] = f("s6.p13;fig3.cap", "observation", f"Fig. 3, Al2O3 at 300 °C in the {gap} nm gap: the film extends to about {pd} µm", quantity="penetration_depth", qualifiers="level=front_end", value=pd, unit="µm",
                 data_kind="stated", method="infrared_microscopy", mentions=f"{gap} nm gap;Fig. 3")

# ---------------------------------------------------------------- Fig. 4: visible top view after peeling, 100 nm Al2O3 at 300 °C, 500 nm gap
o_peel = f("s6.p16;s6.p18;fig4.cap", "observation", "Fig. 4: the membrane was peeled off on the left of the opening and the chip cleaved for cross-section work; the film in the cavity is seen by visible-light microscopy",
           method="optical_microscopy", mentions="Fig. 4")
pd4_blue = f("s6.p18;fig4", "observation", "Fig. 4: the film keeps the blue interference colour of a 100 nm Al2O3 film on Si to about 65 µm into the cavity", quantity="penetration_depth", qualifiers="level=front_start", value="65",
             unit="µm", data_kind="stated", method="optical_microscopy", mentions="100 nm;AR 130:1")
ar4_blue = f("s6.p18", "derived", "65 µm into a 500 nm gap is an aspect ratio of 130:1", quantity="coated_aspect_ratio", qualifiers="level=front_start", value="130", data_kind="computed_by_authors", method="calculation", inputs=[pd4_blue])
pd4_brown = f("s6.p18;fig4", "observation", "Fig. 4: the interference colour turns brown at 80 µm, about 50 nm of film", quantity="penetration_depth", qualifiers="level=50%", value="80", unit="µm", data_kind="stated",
              method="optical_microscopy", mentions="50 nm")
th4_brown = f("s6.p18", "observation", "the brown interference colour at 80 µm corresponds to about 50 nm of Al2O3", quantity="film_thickness", qualifiers="position=local", value="50", unit="nm", data_kind="stated",
              method="optical_microscopy", mentions="80 µm")
pd4_end = f("s6.p18;fig4", "observation", "Fig. 4: the film is colourless, bare silicon, at 90 µm", quantity="penetration_depth", qualifiers="level=front_end", value="90", unit="µm", data_kind="stated", method="optical_microscopy")
c_soft = claim("s6.p18", "the ending profile is soft: the thickness takes tens of micrometres to fall below the detection level", "asserted", supports=[pd4_blue, pd4_end])
c_scan = claim("s6.p19", "thickness line scans after peeling the membrane are the most powerful use of the structure, given a spot small enough for lateral resolution", "asserted")

# ---------------------------------------------------------------- Fig. 5: reflectometer line scans
o_5a = f("s6.p20;s6.p21;fig5.cap;fig5a", "observation", "Fig. 5(a): the Al2O3 thickness along a 500 nm cavity, 1109 cycles at 300 °C, is about constant to 52 µm, then falls rather linearly", quantity="film_thickness",
         method="reflectometry", mentions="500 nm;Fig. 5(a)")
pd5a = f("s6.p21;fig5a", "observation", "Fig. 5(a): the Al2O3 thickness stays constant out to about 52 µm", quantity="penetration_depth", qualifiers="level=front_start", value="52", unit="µm", data_kind="stated", method="reflectometry",
         mentions="AR 104:1")
ar5a = f("s6.p21", "derived", "52 µm in the 500 nm gap is an aspect ratio of 104:1", quantity="coated_aspect_ratio", qualifiers="level=front_start", value="104", data_kind="computed_by_authors", method="calculation", inputs=[pd5a])
wav = f("s6.p21;fig5a", "observation", "Fig. 5(a): the profile is wavy with a 10 µm period, most likely from the oxide pillars", quantity="other", label_as_printed="waviness period", value="10", unit="µm", data_kind="stated",
        method="reflectometry")
c_wav = claim("s6.p21", "the 10 µm waviness most likely comes from the oxide pillars, which are 10 µm apart", "hedged", supports=[wav, pil_d])
rel = f("s6.p21", "setting", "the reflectometer becomes unreliable for thicknesses of the order of 10 nm, so the film's ending profile cannot be measured accurately", quantity="other", label_as_printed="reflectometer reliability limit",
        value="10", unit="nm", data_kind="stated", method="reflectometry")
o_5b = f("s6.p22;fig5.cap;fig5b", "observation", "Fig. 5(b): reflectometer scans of TiO2 grown at 110 °C in 200, 500 and 1000 nm cavities, 2000 cycles; the thickness falls slowly with a slope that differs between regimes",
         quantity="film_thickness", method="reflectometry", mentions="Fig. 5(b)")
o_90 = f("s6.p22;fig5b", "observation", "Fig. 5(b), 500 nm gap: the TiO2 thickness has fallen to 90 % of its entrance value by aspect ratio 40:1", quantity="normalized_thickness", qualifiers="reference=entrance", value="0.9",
         data_kind="stated", method="reflectometry", mentions="90%;AR 40:1")
ar_90 = f("s6.p22", "observation", "Fig. 5(b), 500 nm gap: the aspect ratio where the thickness has fallen to 90 % is 40:1", quantity="coated_aspect_ratio", qualifiers="level=front_start", value="40", data_kind="stated",
          method="reflectometry", mentions="90%")
ar_50 = f("s6.p22;fig5b", "observation", "Fig. 5(b), 500 nm gap: around aspect ratio 130:1 the thickness falls rapidly to 50 % of the entrance value", quantity="coated_aspect_ratio", qualifiers="level=50%", value="130",
          data_kind="stated", method="reflectometry")
ar_end = f("s6.p22;fig5b", "observation", "Fig. 5(b), 500 nm gap: beyond aspect ratio 150:1 the film is too thin for the reflectometer", quantity="coated_aspect_ratio", qualifiers="level=front_end", value="150", data_kind="stated",
           method="reflectometry")
tgt5b = f("s6.p23;fig5.cap", "setting", "the entrance target thickness was about 100 nm", quantity="film_thickness", qualifiers="kind=target", value="100", unit="nm", data_kind="stated")
REM = {}
for gap, remn in (("200", "0"), ("500", "300"), ("1000", "800")):
    REM[gap] = f("s6.p23", "derived", f"after a 100 nm film the {gap} nm gap should be {remn} nm high", quantity="other", label_as_printed="remaining gap height", value=remn, unit="nm", data_kind="computed_by_authors",
                 method="calculation", inputs=[tgt5b], mentions=f"{gap} nm")
c_exp = claim("s6.p23", "if the aspect ratio alone set the film extent, the film would reach furthest in the 1000 nm cavity relative to its original aspect ratio", "asserted", "aspect_ratio", "penetration_depth", "causes")
c_dim = claim("s6.p23;fig5b", "against that expectation the TiO2 film reached slightly further, per unit of original aspect ratio, with a 500 nm gap than with 1000 nm; physical dimensions and not aspect ratio alone set the penetration depth",
              "hedged", "feature_width", "coated_aspect_ratio", "causes")
c_close = claim("s6.p23;fig5b", "in the 200 nm gap the narrow opening nearly closed, and the thickness fell fastest with aspect ratio", "asserted", "feature_narrowing", "coated_aspect_ratio", "decreases", supports=[REM["200"]])

# ---------------------------------------------------------------- Fig. 6: SEM cross section
c_sem = claim("s7.p1", "cross-sectioning with electron microscopy, often with EDS, is the traditional analysis of microscopic HAR structures; the long opening makes the chips easy to cleave", "asserted")
o_6 = f("s7.p2;fig6.cap;fig6", "observation", "Fig. 6: SEM cross section of a 500 nm cavity of aspect ratio 400:1 with Al2O3 grown at 300 °C, the entrance on the right; insets zoom in along the cavity", method="sem",
        mentions="Fig. 6;500 nm;AR 400:1")
ar6 = f("fig6.cap", "setting", "the Fig. 6 structure has aspect ratio 400:1", quantity="aspect_ratio", value="400", data_kind="stated")
pd6_full = f("s7.p2;fig6", "observation", "Fig. 6: the film keeps its expected thickness of about 100 nm out to an aspect ratio of about 120:1", quantity="coated_aspect_ratio", qualifiers="level=front_start", value="120",
             data_kind="stated", method="sem", mentions="100 nm")
th6 = f("s7.p2", "observation", "the Fig. 6 film is about 100 nm thick near the entrance, as expected", quantity="film_thickness", qualifiers="position=plateau", value="100", unit="nm", data_kind="stated", method="sem")
pd6_end = f("s7.p2;fig6", "observation", "Fig. 6: at a cavity length of about 200:1 no film is detected", quantity="coated_aspect_ratio", qualifiers="level=front_end", value="200", data_kind="stated", method="sem")

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "Gao et al. 2015: microscopic silicon LHAR test structures and three ways to read ALD Al2O3 and TiO2 conformality in them", "", evidence="s4.h")
RECIPE = N(f"{K}:recipe", "activity", "ALD in a Picosun R-150 on microscopic LHAR chips: TMA or TiCl4 and water, 0.1/4/0.1/4 s, 110–300 °C, 1–2 mbar", PAPER, evidence="s6.p5", kind="recipe", how="stated", label_as_printed="LHAR recipe")
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


put(RECIPE, reactor, ptot, carrier, T_r, tA, tA2, pA, tB, pB, rep, RB, RA_al, RA_ti, STRUCT, SUBSTR, instr, spot, mag, wafer, oxide, poly1, seal, port, pil_d, chip, L_r, ar_r)
CHIP = node(f"{K}:ent:chip", "entity", "the microscopic LHAR chip: a lateral cavity 200–1000 nm high and 20–5000 µm long under a polysilicon roof on oxide pillars, with a central port", RECIPE, evidence="abs.g2;s6.p1;fig1.cap",
            how="stated", label_as_printed="microscopic LHAR chip")
put(meas(CHIP, "sem", order="0"), o_sem2, ar_sem, ar_sem2)
# depositions and films
DEPS, ENTS = {}, {}


def dep(tag, mat, ra, T, tgt, ev, label, extra=()):
    d = node(f"{K}:dep:{tag}", "activity", f"{label}: {mat} ALD at {T} °C to a {tgt} nm target", RECIPE, evidence=ev, kind="deposition", how="stated", label_as_printed=label, inputs=CHIP)
    put(d, f(ev, "setting", f"{label}: the film material is {mat}", quantity="material", value_text=mat.lower(), data_kind="stated", mentions=label),
        f(ev, "setting", f"{label}: reactant A", quantity="reactant_A", value_text=ra, data_kind="stated", mentions=label),
        f(ev, "setting", f"{label}: grown at {T} °C", quantity="deposition_temperature", value=T, unit="°C", data_kind="stated", mentions=label),
        f(ev, "setting", f"{label}: target thickness {tgt} nm", quantity="film_thickness", qualifiers="kind=target", value=tgt, unit="nm", data_kind="stated", mentions=label), *extra)
    DEPS[tag] = d
    return d


def film(tag, dep_id, gap, ev, label):
    e = node(f"{K}:ent:{tag}", "entity", f"{label} in the {gap} nm gap", dep_id, evidence=ev, how="stated", label_as_printed=f"{label}, {gap} nm gap")
    put(e, f(ev, "setting", f"{label}: the gap height of this chip is {gap} nm", quantity="feature_width", label_as_printed="gap height", value=gap, unit="nm", data_kind="stated", mentions=label))
    ENTS[tag] = e
    return e


# Fig. 3 films, target 50 nm
for T, pan_al, pan_ti in (("110", "a", "b"), ("200", "d", "e"), ("300", "f", "h")):
    dep(f"al_{T}_50", "Al2O3", "tma", T, "50", f"fig3.cap;fig3{pan_al}", f"Al2O3 {T} °C, 50 nm")
    e = film(f"al_{T}_50_500", DEPS[f"al_{T}_50"], "500", f"fig3.cap;fig3{pan_al}", f"Al2O3 {T} °C")
    put(meas(e, "infrared_microscopy"), f(f"fig3{pan_al};fig3.cap", "observation", f"Fig. 3({pan_al}): infrared top view of Al2O3 grown at {T} °C in a 500 nm gap", method="infrared_microscopy", mentions=f"Fig. 3({pan_al})"))
    if T == "300":
        put(meas(e, "infrared_microscopy"), f("fig3g;fig3.cap", "observation", "Fig. 3(g): a second infrared top view of Al2O3 grown at 300 °C in a 500 nm gap", method="infrared_microscopy", mentions="Fig. 3(g)"))
    dep(f"ti_{T}_50", "TiO2", "ticl4", T, "50", f"fig3.cap;fig3{pan_ti}", f"TiO2 {T} °C, 50 nm")
    e = film(f"ti_{T}_50_500", DEPS[f"ti_{T}_50"], "500", f"fig3.cap;fig3{pan_ti}", f"TiO2 {T} °C")
    put(meas(e, "infrared_microscopy"), f(f"fig3{pan_ti};fig3.cap", "observation", f"Fig. 3({pan_ti}): infrared top view of TiO2 grown at {T} °C in a 500 nm gap", method="infrared_microscopy", mentions=f"Fig. 3({pan_ti})"))
for gap, pan in (("200", "c"), ("1000", "i")):
    e = film(f"al_300_50_{gap}", DEPS["al_300_50"], gap, f"fig3.cap;fig3{pan}", "Al2O3 300 °C")
    put(meas(e, "infrared_microscopy"), f(f"fig3{pan};fig3.cap", "observation", f"Fig. 3({pan}): infrared top view of Al2O3 grown at 300 °C in a {gap} nm gap", method="infrared_microscopy", mentions=f"Fig. 3({pan})"))
put(meas(ENTS["al_300_50_200"], "infrared_microscopy"), PD3["200"])
put(meas(ENTS["al_300_50_500"], "infrared_microscopy"), PD3["500"], o_sym, o_100)
put(meas(ENTS["al_300_50_1000"], "infrared_microscopy"), PD3["1000"])
C.spread(o_sym, [meas(ENTS["al_300_50_500"], "infrared_microscopy")] + [meas(ENTS[t], "infrared_microscopy") for t in ENTS if t != "al_300_50_500"], {})
# Figs. 4 and 6: Al2O3 at 300 °C, 100 nm target, 500 nm gap; Fig. 5(a): 1109 cycles
dep("al_300_100", "Al2O3", "tma", "300", "100", "fig4.cap;fig6.cap;s6.p18", "Al2O3 300 °C, 100 nm")
F4 = film("al_300_100_fig4", DEPS["al_300_100"], "500", "fig4.cap", "Al2O3 300 °C, 100 nm, Fig. 4 chip")
put(meas(F4, "optical_microscopy"), o_peel, pd4_blue, ar4_blue, pd4_brown, th4_brown, pd4_end)
F6 = film("al_300_100_fig6", DEPS["al_300_100"], "500", "fig6.cap", "Al2O3 300 °C, 100 nm, Fig. 6 chip")
put(F6, ar6)
put(meas(F6, "sem"), o_6, pd6_full, th6, pd6_end)
dep("al_300_1109", "Al2O3", "tma", "300", "100", "fig5.cap;s6.p21", "Al2O3 300 °C, 1109 cycles",
    extra=[f("fig5.cap", "setting", "Fig. 5(a): 1109 ALD cycles", quantity="cycle_number", value="1109", data_kind="stated")])
F5A = film("al_300_1109_500", DEPS["al_300_1109"], "500", "fig5.cap;fig5a", "Al2O3 300 °C, 1109 cycles")
put(meas(F5A, "reflectometry"), o_5a, pd5a, ar5a, wav, rel)
# Fig. 5(b): TiO2 at 110 °C, 2000 cycles, three gaps
dep("ti_110_2000", "TiO2", "ticl4", "110", "100", "fig5.cap;s6.p22;s6.p23", "TiO2 110 °C, 2000 cycles",
    extra=[f("fig5.cap", "setting", "Fig. 5(b): 2000 ALD cycles", quantity="cycle_number", value="2000", data_kind="stated"), tgt5b])
for gap in ("200", "500", "1000"):
    e = film(f"ti_110_2000_{gap}", DEPS["ti_110_2000"], gap, "fig5.cap;fig5b", "TiO2 110 °C, 2000 cycles")
    put(e, REM[gap])
    put(meas(e, "reflectometry"), f("fig5b;fig5.cap", "observation", f"Fig. 5(b): the TiO2 thickness against aspect ratio in the {gap} nm gap", quantity="film_thickness", method="reflectometry", mentions=f"{gap} nm;Fig. 5(b)"))
put(meas(ENTS["ti_110_2000_500"], "reflectometry"), o_5b, o_90, ar_90, ar_50, ar_end)
for h in (spot, mag):
    C.spread(h, [RECIPE] + [meas(ENTS[t], "reflectometry") for t in ("al_300_1109_500", "ti_110_2000_200", "ti_110_2000_500", "ti_110_2000_1000")], {})
# cited facts under reference nodes
REFS = {n: node(f"{K}:refs:{n}", "cited", f"cited work{'s' if ',' in n else ''}, reference{'s' if ',' in n else ''} {n} of the paper", PAPER, evidence=ev, label_as_printed=f"ref. {n}")
        for n, ev in (("3", "s9.p5"), ("11, 12", "s9.p13;s9.p14"), ("13, 14", "s9.p15;s9.p16"), ("15, 16", "s9.p17;s9.p18"))}
put(REFS["3"], r_tr5)
put(REFS["11, 12"], r_tr40)
put(REFS["13, 14"], r_mac, r_gap, r_vac)
put(REFS["15, 16"], r_plug)
put(PAPER, mfp, p_ald)
for r in C.facts():
    if r["type"] == "definition" and r["fact_id"] not in PARENT:
        PARENT[r["fact_id"]] = PAPER
BY_TEXT = {"the microscopic LHAR structures open a parameter space": [ar_r], "with a limiting dimension of hundreds of nanometres": [oxide, mfp, p_ald],
           "silicon-based microscopic LHAR test structures, a lateral cavity": [oxide, L_r], "conformality follows from self-terminating ALD chemistry": [c_shape] if False else [o_5b],
           "most ALD studies skip conformality": [r_tr5, r_tr40], "the structures could tune processes": [ar_r], "nondestructive microscopy, reflectometry after membrane removal": [PD3["500"], pd4_end, pd6_end],
           "Al2O3 is uniform along the cavity": [o_5a, o_5b], "the film under the membrane can be inspected": [o_peel], "for Al2O3 the penetration depth increases": [PD3["500"]],
           "for TiO2 a falling temperature": [o_100], "the temperature trends come from": [c_alT] if False else [o_100], "the penetration depth grows with the gap height": [PD3["200"], PD3["500"], PD3["1000"]],
           "thickness line scans after peeling the membrane": [o_5a], "if the aspect ratio alone set the film extent": [REM["1000"], REM["500"]], "against that expectation the TiO2 film": [o_5b, REM["500"], REM["1000"]],
           "cross-sectioning with electron microscopy": [o_6]}
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
GROUPS = [(f"{K}:grp:al_T", "series", "deposition_temperature", "Al2O3 temperature series: Fig. 3, 110, 200 and 300 °C in 500 nm gaps", "fig3.cap", c_alT, [ENTS[f"al_{T}_50_500"] for T in ("110", "200", "300")]),
          (f"{K}:grp:ti_T", "series", "deposition_temperature", "TiO2 temperature series: Fig. 3, 110, 200 and 300 °C in 500 nm gaps", "fig3.cap", c_tiT, [ENTS[f"ti_{T}_50_500"] for T in ("110", "200", "300")]),
          (f"{K}:grp:al_gap", "series", "feature_width", "Al2O3 gap series: Fig. 3, 200, 500 and 1000 nm gaps at 300 °C", "fig3.cap", c_gap, [ENTS[f"al_300_50_{g}"] for g in ("200", "500", "1000")]),
          (f"{K}:grp:ti_gap", "series", "feature_width", "TiO2 gap series: Fig. 5(b), 200, 500 and 1000 nm gaps at 110 °C, 2000 cycles", "fig5.cap", c_dim, [ENTS[f"ti_110_2000_{g}"] for g in ("200", "500", "1000")]),
          (f"{K}:grp:shape", "series", "material", "the Al2O3 and TiO2 line scans compared: Fig. 5(a) against Fig. 5(b), 500 nm gaps", "s6.p22", c_shape, [F5A, ENTS["ti_110_2000_500"]])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s6.p21", "The reflectometer is unreliable for thicknesses of the order of 10 nm, so the ending profiles of the line scans are not accurate.", [o_5a, o_5b, ar_end], "", ""),
    ("s6.p12", "The temperature trends of the penetration depth are reported without a mechanism; the authors call for a dedicated study.", [c_alT, c_tiT], "", ""),
    ("s6.p18", "The Fig. 4 depths come from interference colours read by eye (blue for 100 nm, brown for 50 nm), not from a thickness measurement.", [pd4_blue, pd4_brown, pd4_end], "", ""),
    ("s6.p23", "The gap-height comparison of Fig. 5(b) is an initial result from three chips; the remaining gap heights 0, 300 and 800 nm are the target thickness subtracted twice from the original height.",
     [c_dim, REM["200"], REM["500"], REM["1000"]], "", ""),
    ("fig3.cap", "The nine Fig. 3 films share the recipe's typical pulsing and a 50 nm target; their cycle numbers are not stated.", [ENTS[t] for t in ENTS if t.endswith("_50_500") or t.startswith("al_300_50_")], "", ""),
    ("fig1.cap", "The Fig. 1 dimension table (lateral lengths, opening widths, maximum aspect ratios per cavity height) is an image whose cells were not read; the stated ranges stand in for it.", [CHIP], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.sized(K, {c_gap.split(":", 1)[1]: [PD3[g].split(":", 1)[1] for g in ("200", "500", "1000")], c_dim.split(":", 1)[1]: [ar_50.split(":", 1)[1], ar_end.split(":", 1)[1]]})
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
# P131: a claim is a triple or it is not a claim; every claim without a full triple re-typed by the one rule (facts.retype)
BG = 'background, motivation, prior art or scope'
RETYPE = {
    'abs.g1#1': ('removed', BG),
    's5.p3#1': ('removed', BG),
    's8.p2#1': ('removed', BG),
    's7.p1#1': ('removed', BG),
    's8.p1#1': ('observation', '^s6.p13#3'),
    's6.p18#6': ('observation', '^s6.p18#1'),
    's6.p11#1': ('setting', '^s6.p16#1'),
    's6.p19#1': ('caveat', ['s6.p20#1']),
    's6.p21#4': ('triple', 'pillar_effect', 'causes', 'film_thickness'),
}
C.retype(K, RETYPE)
write(K, PID)
