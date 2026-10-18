#!/usr/bin/env python3
"""Stage 2 facts for zou23 (10.1116_6.0002804, van der Zouw, van der Wel, Aarnink, Wolters, Gravesteijn, Kovalgin 2023, JVST A: hot-wire-
assisted ALD of low-resistivity molybdenum from MoCl2O2 and atomic hydrogen; the ALD window 150-450 °C, saturation, growth against
temperature for ALD and pulsed CVD, nucleation, byproducts by mass spectrometry, composition by TOF-ERDA and SIMS, resistivity against
thickness and temperature, GIXRD, uniformity and conformality in SiO2-capped Si trenches by STEM and EDX).
Text and captions (no table); the Fig. 1-3, 5-7 curves and the Fig. 8 peaks are imported records (kb/figures_import.py, P88).

    python3 psed_v2/pilot/10.1116_6.0002804.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import facts as C  # noqa: E402
from facts import F, N, NK, write  # noqa: E402

K, PID = "zou23", "10.1116_6.0002804"
A = "s3.p1"                                                                      # the abstract printed again as a body paragraph


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


CLAIMS = {}


def claim(ev, s, stance, cause="", effect="", relation="", supports=(), **kw):
    h = f(ev, "claim", s, **kw)
    CLAIMS[h] = (stance, cause, effect, relation, list(supports))
    return h


# ---------------------------------------------------------------- elements without knowledge
NK("s1.h;s2.h;s3.h;s4.h;s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h;s12.h", "heading")
NK("s1.p1;s1.p2;s1.p3;s1.p4;s1.p5;s1.p6;s2.p1;s2.p2;s2.p3;s3.p2", "front matter, affiliation, note, contact, licence")
NK("s5.p10", "a download stamp of the PDF")
NK("s7.p2;s7.p6;s8.p2;s8.p4;s9.p3;s9.p4;s11.p2;s11.p3;s11.p7;s11.p8", "a caption printed again as a body paragraph; the knowledge is under the figure's caption element")
NK("s12.p3;s12.p4;s12.p5;s12.p6;s12.p7;s12.p8;s12.p9;s12.p10;s12.p11", "acknowledgements, declarations, author contributions, data availability")
NK(A, "the abstract printed again as a body paragraph (knowledge under abs.g1-g5)")

# ---------------------------------------------------------------- claims
c_new = claim("abs.g1;s4.p7;s12.p1", "a hot-wire-assisted ALD process deposits low-resistivity molybdenum from MoCl2O2 and atomic hydrogen, with self-limiting growth over a wide window of 150–450 °C", "asserted")
c_atH = claim("abs.g2;s7.p4;s12.p1", "molecular hydrogen deposits nothing; atomic hydrogen is needed to reduce MoCl2O2, and the growth per cycle decays quickly as the hot-wire temperature falls and stops with the wire off", "asserted",
              "surface_chemistry", "growth_per_cycle", "causes")
c_comp = claim("abs.g2;s9.p2;s12.p1", "at 350 °C and above the films are nearly pure molybdenum with a few atomic percent of oxygen and traces of carbon, chlorine, hydrogen and nitrogen", "asserted")
c_nosel = claim("abs.g3;s8.p1;s8.x1;s12.p2", "no substrate selectivity or pronounced nucleation delay appeared on Si, SiO2, Si3N4, SiC, Al2O3, HfO2 or low-k SiOC", "asserted", mentions="Fig. S4")
c_unif = claim("abs.g4;s11.p1;s11.p4;s12.p2", "thickness and sheet resistance vary little within a central circle of the wafer, the nonuniformity rising toward the edge where atomic hydrogen, admitted above the centre, arrives less", "asserted",
               "gas_diffusion", "thickness_nonuniformity", "causes", mentions="Figs. S5 and S6")
c_lowT = claim("abs.g4;abs.g5;s7.p8;s9.p2;s12.p1", "at 250 °C and below more oxygen and chlorine enter the film, the growth per cycle rises, the optical constants change, density and crystallinity fall and resistivity rises: atomic hydrogen no longer strips the ligands fully",
               "asserted", "deposition_temperature", "element_fraction", "decreases", mentions="Figs. S2 and S3")
c_window = claim("abs.g5;s12.p1", "self-limiting growth spans 150–450 °C, but low-resistivity Mo needs 250 °C or more", "asserted", "deposition_temperature", "resistivity", "decreases")
c_mo = claim("s4.p1;s4.p2;s4.p3", "below the electron mean free path of Cu and W interconnect resistivity rises; Mo, with a short mean free path, high conductivity and electromigration resistance, is a candidate to replace them", "asserted",
             mentions="ref 3;ref 4;ref 9;ref 25;ref 31;ref 32")
c_ald = claim("s4.p4;s4.p5", "ALD's self-limiting reactions give the thickness control, uniformity and conformality interconnects need, but a BEOL-compatible Mo ALD process was missing", "asserted", "self_limiting_growth", "step_coverage", "causes",
              mentions="ref 35;ref 36;ref 37;ref 38")
c_lit = claim("s4.p6", "earlier Mo CVD and ALD routes need high temperatures (MoCl5, Mo(CO)6), suffer corrosive byproducts or selectivity (MoF6), or ran far above the BEOL limit with H2", "asserted", mentions="ref 31;ref 39;ref 40;ref 41;ref 56;ref 61")
c_hw = claim("s4.p7", "hot-wire ALD makes atomic hydrogen on a heated tungsten filament, an alternative to plasma ALD without plasma damage", "asserted", mentions="ref 62;ref 63")
c_sat = claim("s7.p1;s7.p3;fig1.cap", "at 350 °C the growth per cycle saturates with the MoCl2O2 and the atomic-hydrogen pulse times, rises as the MoCl2O2 purge shortens (a CVD contribution) and ignores the atomic-hydrogen purge, since atomic hydrogen recombines fast",
              "asserted", "self_limiting_growth", "growth_per_cycle", "causes")
c_cycle = claim("s7.p3", "the standard cycle 1/15/29/15 s sits near saturation; the long atomic-hydrogen pulse ensures reduction, which the growth per cycle alone may not show", "asserted")
c_self = claim("s7.p5;s7.p7", "sequential MoCl2O2 pulses without atomic hydrogen saturate the thickness over the whole window: chemisorption is self-limiting", "asserted", "self_limiting_growth", "film_thickness", "causes", mentions="Fig. S1")
c_gpcT = claim("s7.p8;fig2.cap", "the growth per cycle is about constant over the upper window for ALD and for CVD, several times higher for CVD, and rises toward lower temperatures; SE and XRR agree", "asserted",
               "deposition_temperature", "growth_per_cycle", "causes")
c_cvd = claim("s7.p8", "the higher CVD growth per cycle points to gas-phase reactions or surface reactions enhanced by both reactants being present together", "hedged", "cvd_growth", "growth_per_cycle", "increases")
c_nuc = claim("s8.x1;fig3.cap", "on SiO2 the steady regime starts after the first few nanometres; the growth-per-cycle transient suggests inhibited nucleation, yet the extrapolated thickness intercept is positive, as for enhanced growth, so the nature of nucleation stays open",
              "hedged", "surface_chemistry", "film_thickness", "causes", mentions="ref 66")
c_ms = claim("s8.p3;s8.p5;fig4.cap", "mass spectrometry shows HCl leaving during the MoCl2O2 pulse and water during the atomic-hydrogen pulse: chemisorption goes through surface hydrogen and chloride ligands, and atomic hydrogen removes the oxygen and remaining chlorine",
             "asserted", "surface_chemistry", "element_fraction", "causes")
c_erda = claim("s9.p1;s9.p2;fig5.cap", "TOF-ERDA of a 20 nm film grown at 350 °C shows oxygen only at the surface oxide and the native SiO2 interface; the oxygen share climbs steeply toward lower temperatures, and chlorine appears at the lowest", "asserted",
               "deposition_temperature", "element_fraction", "decreases")
c_sims = claim("s9.p5;fig6.cap", "SIMS puts the O, Cl, C, N and Si contaminants of the 350 °C ALD film near 1e20 atoms per cm3; CVD films gain oxygen toward lower temperatures, above 1e22 at 250 °C, tens of atomic percent", "asserted",
               "deposition_temperature", "element_fraction", "decreases")
c_res = claim("s10.p1;s10.p2;fig7.cap", "the resistivity approaches a bulk-like value in the thickest film and rises sharply below the electron mean free path of Mo; against temperature it rises at the low end for ALD and earlier for CVD, with the oxygen uptake",
              "asserted", "film_thickness", "resistivity", "decreases", mentions="ref 4;ref 67")
c_reslit = claim("s10.p1", "other Mo ALD works reached lower resistivities only at far higher temperatures, and a much higher one at a low temperature, so the value here, at a moderate temperature, is low and in line with the temperature trend", "asserted", mentions="ref 31;ref 39;ref 40;ref 61")
c_xrd = claim("s10.p2;fig8.cap", "GIXRD of the 350 °C film shows the (110), (200) and (211) peaks of body-centred cubic Mo; the 150 °C film shows only the substrate peak and is amorphous, which also raises its resistivity", "asserted",
              "deposition_temperature", "crystallinity", "causes", mentions="ref 31;ref 61;ref 68;ref 69")
c_conf = claim("s11.p5;fig9.cap;s12.p2", "in SiO2-capped Si trenches of aspect ratio 2:1 to 10:1 the sidewall and bottom films keep most of the top thickness in the 3:1 trench, the bottom a little less; conformality falls with the aspect ratio, presumably through hydrogen recombination and hindered diffusion",
               "asserted", "surface_recombination", "step_coverage", "decreases", mentions="ref 70;ref 71;ref 72")
c_bcc = claim("s11.p6", "the FFT rings of the TEM image match the d spacings of body-centred cubic Mo", "asserted", mentions="ref 73")
c_edx = claim("s11.p6;s11.p9;fig10.cap", "EDX shows Mo reaching the bottom of a narrow trench with about twice the oxygen share there; atomic hydrogen likely recombines on the walls, so pure Mo deep in HAR structures may need longer atomic-hydrogen pulses",
              "hedged", "surface_recombination", "element_fraction", "increases")

# ---------------------------------------------------------------- cited
r_mfp = f("s10.p2", "cited", "the electron mean free path of molybdenum is 11.2 nm", quantity="other", label_as_printed="electron mean free path of Mo", value="11.2", unit="nm", data_kind="cited", method="cited", mentions="ref 4")
r_res = [f("s10.p1", "cited", "Mo ALD at 600–650 °C with H2 gave 13 µΩ cm", quantity="resistivity", value="13", unit="µΩ cm", data_kind="cited", method="cited", mentions="ref 61;600–650 °C"),
         f("s10.p1", "cited", "Mo ALD at 400–500 °C gave 15 µΩ cm", quantity="resistivity", value="15", unit="µΩ cm", data_kind="cited", method="cited", mentions="ref 39;400–500 °C"),
         f("s10.p1;s4.p6", "cited", "Mo ALD from an oxychloride and H2 at 450–590 °C gave 16 µΩ cm", quantity="resistivity", value="16", unit="µΩ cm", data_kind="cited", method="cited", mentions="ref 31;450–590 °C"),
         f("s10.p1", "cited", "Mo ALD at 120 °C gave 124 µΩ cm", quantity="resistivity", value="124", unit="µΩ cm", data_kind="cited", method="cited", mentions="ref 40;120 °C")]
r_h2 = f("s4.p6", "cited", "thermal ALD of Mo from MoCl2O2 and H2 was reported at 600–650 °C", quantity="deposition_temperature", value_min="600", value_max="650", unit="°C", data_kind="cited", method="cited", mentions="ref 61")

# ---------------------------------------------------------------- the recipe
reactor = f("s5.p1", "setting", "the reactor: home-built, hot-walled, high vacuum, with a low-volume chamber and a turbomolecular pump", quantity="reactor", value_text="home-built hot-wall HWALD reactor", data_kind="stated")
pbase = f("s5.p1", "setting", "base pressure about 1e-8 mbar", quantity="process_pressure", qualifiers="kind=default", label_as_printed="base pressure", value="1e-8", unit="hPa", data_kind="stated", mentions="~1 × 10^-8 mbar")
RA = f("s5.p1;abs.g1", "setting", "the precursor MoCl2O2 (Air Liquide), a solid", quantity="reactant_A", value_text="mocl2o2", data_kind="stated")
Tves = f("s5.p1", "setting", "the precursor vessel was heated to 75 °C, about 2 mbar of vapour", quantity="other", label_as_printed="precursor vessel temperature", value="75", unit="°C", data_kind="stated", mentions="~2 mbar")
pvap = f("s5.p1", "setting", "the MoCl2O2 vapour pressure at the vessel temperature is about 2 mbar, fed at 0.2 mbar overpressure", quantity="partial_pressure", qualifiers="species=mocl2o2;kind=default", label_as_printed="vapour pressure", value="2", unit="hPa",
         data_kind="stated", mentions="0.2 mbar overpressure")
Tin = f("s5.p1", "setting", "the gas inlet was held at 85 °C and the reactor outside at 100 °C against condensation", quantity="other", label_as_printed="inlet temperature", value="85", unit="°C", data_kind="stated", mentions="100 °C reactor outside")
Trange = f("s5.p1;abs.g1", "setting", "the chamber temperature ran from 150 to 450 °C", quantity="deposition_temperature", value_min="150", value_max="450", unit="°C", data_kind="stated")
RB = f("s5.p1;abs.g1", "setting", "the coreactant is atomic hydrogen from H2 dissociated on a heated tungsten filament behind a showerhead", quantity="reactant_B", value_text="h_atom", data_kind="stated", mentions="hot wire;showerhead")
fh2 = f("s5.p1", "setting", "20 sccm of H2 (Linde 5.0) fed the hot wire", quantity="gas_flow_rate", qualifiers="gas=h2;step=reactant_B", value="20", unit="sccm", data_kind="stated")
fn2 = f("s5.p1", "setting", "8 sccm of N2 (Linde 5.0) as carrier and purge gas", quantity="gas_flow_rate", qualifiers="gas=n2", value="8", unit="sccm", data_kind="stated")
carrier = f("s5.p1", "setting", "nitrogen is the carrier and purge gas", quantity="carrier_gas", value_text="n2", data_kind="stated")
pbg = f("s5.p1", "setting", "background pressure about 1e-3 mbar", quantity="process_pressure", value="1e-3", unit="hPa", data_kind="stated", mentions="~1 × 10^-3 mbar")
SUB = f("s5.p2;abs.g3", "setting", "substrates: Si(100), thermal SiO2 and Si3N4, SiC, sapphire, ALD HfO2 and low-k SiOC (k 3.0); the main results on Si with native oxide and on SiO2", quantity="substrate", value_text="si", data_kind="stated",
        mentions="Si3N4;SiC;sapphire;HfO2;SiOC")
clean = f("s5.p2;s5.p3", "setting", "substrates were precleaned with 99 % HNO3, 1 % HF or O3 steam; the cleaning did not visibly affect nucleation", data_kind="stated", mentions="99%;1%")
STRUCT = f("s5.p2", "setting", "the films of the growth studies grew on planar substrates", quantity="structure", value_text="planar", data_kind="stated")
tA = f("s5.p3;s7.p3", "setting", "standard cycle: 1 s MoCl2O2 pulse", quantity="pulse_time", qualifiers="step=reactant_A;species=mocl2o2", value="1", unit="s", data_kind="stated")
pA = f("s5.p3;s7.p3", "setting", "standard cycle: 15 s N2 purge after the precursor", quantity="purge_time", qualifiers="step=purge_A", value="15", unit="s", data_kind="stated")
tB = f("s5.p3;s7.p3", "setting", "standard cycle: 29 s atomic-hydrogen pulse", quantity="pulse_time", qualifiers="step=reactant_B;species=h_atom", value="29", unit="s", data_kind="stated")
pB = f("s5.p3;s7.p3", "setting", "standard cycle: 15 s N2 purge after the atomic hydrogen", quantity="purge_time", qualifiers="step=purge_B", value="15", unit="s", data_kind="stated")
se = f("s5.p4", "setting", "growth was monitored in situ with a J. A. Woollam M-2000 spectroscopic ellipsometer over 245–1690 nm; the growth per cycle is the thickness increase in the linear regime over the cycles", method="spectroscopic_ellipsometry",
       mentions="245–1690 nm;M-2000")
se2 = f("s5.p4", "setting", "ex situ SE on a Woollam M-2000UI; the Mo optics modelled as Drude plus two Lorentz oscillators in CompleteEASE 6.46; XRR and electron microscopy verified thicknesses above 5 nm, b-splines served below",
        method="spectroscopic_ellipsometry", mentions="ref 64;5 nm;M-2000UI")
xrr = f("s5.p5", "setting", "XRR and GIXRD on a Rigaku SmartLab; thickness and density from the SmartLab Studio II layer model; the XRR growth per cycle is the thickness over all cycles", method="xrr", mentions="Rigaku SmartLab")
ms = f("s5.p6", "setting", "mass spectrometry with a quadrupole residual gas analyser (MKS Spectra LM76 Microvision Plus)", method="process_monitor", mentions="MKS Spectra LM76")
erda = f("s5.p7", "setting", "TOF-ERDA at the Helsinki 5 MV tandem accelerator with a 30 MeV 127I beam, 40° recoil and 16° incidence, SRIM-2003 stopping powers", method="tof_erda", mentions="30 MeV;40°;16°;5 MV")
sims = f("s5.p8", "setting", "SIMS on an Atomika 4100 quadrupole tool, quantified with EAG software", method="sims", mentions="Atomika 4100")
sem = f("s5.p9", "setting", "HR-SEM on a Zeiss Merlin with in-lens (topography) and energy-selective backscatter (composition) detectors", method="sem", mentions="Zeiss Merlin")
tem = f("s5.p11", "setting", "STEM on a Helios 5 Dual Beam; TEM and EDX on an FEI Titan Cs-corrected 80–300 kV", method="tem", mentions="Helios 5;FEI Titan;80–300 kV")
fpp = f("s5.p12", "setting", "sheet resistance with a Polytec 280SI four-point probe, 69-point wafer maps at 1 cm intervals", method="four_point_probe", mentions="Polytec 280SI;69 points;1 cm")

# ---------------------------------------------------------------- the tree
PAPER = N(K, "paper", "van der Zouw et al. 2023: hot-wire-assisted ALD of low-resistivity Mo from MoCl2O2 and atomic hydrogen", "", evidence="s1.h")
RECIPE = N(f"{K}:recipe", "activity", "hot-wire ALD of Mo: MoCl2O2 and atomic hydrogen, cycle 1/15/29/15 s, 150–450 °C; pulsed CVD with constant atomic hydrogen for comparison", PAPER, evidence="s5.p1;s5.p3", kind="recipe", how="stated",
           label_as_printed="Mo HWALD recipe")
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


put(RECIPE, reactor, pbase, RA, Tves, pvap, Tin, Trange, RB, fh2, fn2, carrier, pbg, SUB, clean, STRUCT, tA, pA, tB, pB, se, se2, xrr, ms, erda, sims, sem, tem, fpp)
DEP_A = node(f"{K}:dep:ald", "activity", "the ALD process: MoCl2O2 and atomic hydrogen alternated with N2 purges", RECIPE, evidence="s5.p3", kind="deposition", how="stated", label_as_printed="Mo ALD")
put(DEP_A, f("s5.p3;abs.g1", "setting", "the ALD process deposits molybdenum", quantity="material", value_text="mo", data_kind="stated", mentions="ALD"))
DEP_C = node(f"{K}:dep:cvd", "activity", "pulsed CVD: 1 s MoCl2O2 pulses every 30 s under constant atomic hydrogen, no N2 purges", RECIPE, evidence="s5.p3", kind="deposition", how="stated", label_as_printed="Mo pulsed CVD")
put(DEP_C, f("s5.p3", "setting", "the pulsed CVD process deposits molybdenum", quantity="material", value_text="mo", data_kind="stated", mentions="CVD"),
    f("s5.p3", "setting", "pulsed CVD: a MoCl2O2 pulse every 30 s", quantity="cycle_time", value="30", unit="s", data_kind="stated", mentions="CVD"),
    f("s5.p3", "setting", "pulsed CVD: atomic hydrogen supplied continuously, no purges", quantity="purge_time", qualifiers="step=purge_A", value="0", unit="s", data_kind="stated", mentions="CVD;constant at-H"))
FILMS = {}


def film(tag, dep, T, label, ev, who, sub=None, extra=()):
    e = node(f"{K}:ent:{tag}", "entity", label, dep, evidence=ev, how="stated", label_as_printed=label)
    own = [f(ev, "setting", f"{who}: grown at {T} °C", quantity="deposition_temperature", value=T, unit="°C", data_kind="stated", mentions=label)]
    if sub:
        own.append(f(ev, "setting", f"{who}: on {sub[1]}", quantity="substrate", value_text=sub[0], data_kind="stated", mentions=label))
    put(e, *own, *extra)
    FILMS[tag] = e
    return e


# the ALD films by temperature and the CVD films
A350 = film("ald350", DEP_A, "350", "ALD Mo film, 350 °C", "s7.p1;fig1.cap;s9.p1", "the ALD film at the standard temperature")
A150 = film("ald150", DEP_A, "150", "ALD Mo film, 150 °C", "s9.p2;fig8.cap", "the ALD film at the lowest temperature")
A250 = film("ald250", DEP_A, "250", "ALD Mo film, 250 °C", "s9.p2;fig5.cap", "the ALD film at the lower window edge")
A450 = film("ald450", DEP_A, "450", "ALD Mo film, 450 °C", "s7.p8;fig2.cap", "the ALD film at the highest temperature")
C250 = film("cvd250", DEP_C, "250", "CVD Mo film, 250 °C", "s9.p5;fig6.cap", "the CVD film at the lowest temperature")
C350 = film("cvd350", DEP_C, "350", "CVD Mo film, 350 °C", "s7.p8;fig2.cap", "the CVD film at the standard temperature")
A350Q = film("ald350_sio2", DEP_A, "350", "ALD Mo film on SiO2, 350 °C", "s8.x1;fig3.cap;s10.p1;fig7.cap", "the ALD film on thermal oxide", sub=("sio2", "thermal SiO2"))
# Fig. 1: saturation at 350 °C
put(meas(A350, "spectroscopic_ellipsometry", mode="in_situ"),
    f("fig1a;fig1.cap;s7.p3", "observation", "Fig. 1(a): the growth per cycle against the MoCl2O2 pulse time at 350 °C saturates", quantity="growth_per_cycle", qualifiers="position=planar;over=run", method="spectroscopic_ellipsometry", mentions="Fig. 1(a)"),
    f("fig1b;fig1.cap;s7.p3", "observation", "Fig. 1(b): the growth per cycle against the atomic-hydrogen pulse time saturates", quantity="growth_per_cycle", qualifiers="position=planar;over=run", method="spectroscopic_ellipsometry", mentions="Fig. 1(b)"),
    f("fig1c;fig1.cap;s7.p3", "observation", "Fig. 1(c): the growth per cycle rises as the MoCl2O2 purge shortens", quantity="growth_per_cycle", qualifiers="position=planar;over=run", method="spectroscopic_ellipsometry", mentions="Fig. 1(c)"),
    f("fig1d;fig1.cap;s7.p3", "observation", "Fig. 1(d): the growth per cycle is about independent of the atomic-hydrogen purge time", quantity="growth_per_cycle", qualifiers="position=planar;over=run", method="spectroscopic_ellipsometry", mentions="Fig. 1(d)"),
    f("fig1e;fig1.cap;s7.p4", "observation", "Fig. 1(e): the growth per cycle decays as the hot-wire temperature falls and stops with the wire off; the wire temperature was estimated from the power through earlier work", quantity="growth_per_cycle",
      qualifiers="position=planar;over=run", method="spectroscopic_ellipsometry", mentions="Fig. 1(e);ref 65"),
    f("s7.p8;fig2.cap;fig2;abs.g3", "observation", "the ALD growth per cycle is about 0.022 nm per cycle between 250 and 450 °C", quantity="growth_per_cycle", qualifiers="position=planar;over=run", value="0.022", unit="nm/cycle", data_kind="measured",
      method="spectroscopic_ellipsometry", mentions="ALD SE;ALD XRR;250–450 °C"))
put(meas(C350, "spectroscopic_ellipsometry", mode="in_situ"), f("s7.p8;fig2.cap;fig2", "observation", "the CVD growth per cycle is about 0.080 nm per cycle between 350 and 450 °C", quantity="growth_per_cycle", qualifiers="position=planar;over=run", value="0.080",
                                                                 unit="nm/cycle", data_kind="measured", method="spectroscopic_ellipsometry", mentions="CVD SE;CVD XRR;350–450 °C"))
put(meas(A350, "xrr"), f("s7.p8;fig2.cap", "observation", "the XRR growth per cycle agrees closely with the SE value", quantity="growth_per_cycle", qualifiers="position=planar;over=run", method="xrr", mentions="ALD XRR"))
gpc_ald = next(x["fact_id"] for x in C.facts() if x["fact_id"].startswith(K) and x["value"] == "0.022")
C.spread(gpc_ald, [meas(A350, "spectroscopic_ellipsometry"), meas(A450, "spectroscopic_ellipsometry", mode="in_situ"), meas(A250, "spectroscopic_ellipsometry", mode="in_situ")], {meas(A450, "spectroscopic_ellipsometry"): "450 °C", meas(A250, "spectroscopic_ellipsometry"): "250 °C"})
# Fig. 3 and 4: nucleation on SiO2, byproducts
put(A350Q, f("s8.x1;fig3.cap", "setting", "the Fig. 3 run on SiO2 ran 400 cycles", quantity="cycle_number", value="400", data_kind="stated"))
put(meas(A350Q, "spectroscopic_ellipsometry", mode="in_situ"),
    f("fig3;fig3.cap;s8.x1", "observation", "Fig. 3: the thickness against cycles over the Fig. 3 run on SiO2, a nucleation stage then linear growth", quantity="film_thickness", qualifiers="position=planar", method="spectroscopic_ellipsometry", mentions="Fig. 3"),
    f("s8.x1", "observation", "the steady growth regime starts at about 3–3.5 nm of film", quantity="film_thickness", qualifiers="position=planar;stage=initial", label_as_printed="onset of steady growth", value_min="3", value_max="3.5", unit="nm", data_kind="stated",
      method="spectroscopic_ellipsometry"))
put(meas(A350, "process_monitor", mode="in_situ"), f("fig4;fig4.cap;s8.p3;s8.p5", "observation", "Fig. 4: a 1 s MoCl2O2 pulse on an atomic-hydrogen-exposed surface releases much HCl and little water; the following 1 s atomic-hydrogen pulse releases much water and little HCl",
                                                    method="process_monitor", mentions="HCl;H2O;Fig. 4"))
# Fig. 5 and 6: composition
put(meas(A350, "tof_erda"),
    f("fig5a;fig5.cap;s9.p1", "observation", "Fig. 5(a): TOF-ERDA depth profile, Mo, O and Si through the 20 nm film grown at 350 °C, oxygen only at the surface oxide and the native SiO2", quantity="element_fraction", qualifiers="element=O", method="tof_erda",
      mentions="Mo;Si;O;Fig. 5(a);20 nm"),
    f("fig5b;fig5.cap;s9.p2", "observation", "Fig. 5(b): the averaged composition against temperature", quantity="element_fraction", qualifiers="element=O", method="tof_erda", mentions="Fig. 5(b)"),
    f("s9.p2;abs.g2", "observation", "at 350 °C and above the film is about 95 at.% molybdenum", quantity="element_fraction", qualifiers="element=Mo", value="95", unit="at.%", data_kind="measured", method="tof_erda", mentions="Mo"),
    f("s9.p2;abs.g2", "observation", "at 350 °C and above the oxygen share is about 3.5 at.%", quantity="element_fraction", qualifiers="element=O", value="3.5", unit="at.%", data_kind="measured", method="tof_erda", mentions="O"),
    f("s9.p2", "observation", "hydrogen 0.7 at.%", quantity="element_fraction", qualifiers="element=H", value="0.7", unit="at.%", data_kind="measured", method="tof_erda", mentions="H"),
    f("s9.p2", "observation", "carbon 0.2 at.%", quantity="element_fraction", qualifiers="element=C", value="0.2", unit="at.%", data_kind="measured", method="tof_erda", mentions="C"),
    f("s9.p2", "observation", "nitrogen 0.3 at.%", quantity="element_fraction", qualifiers="element=N", value="0.3", unit="at.%", data_kind="measured", method="tof_erda", mentions="N"),
    f("s9.p2", "observation", "chlorine is below the detection limit at 350 °C and above", quantity="element_fraction", qualifiers="element=Cl", value_text="not_detected", data_kind="measured", method="tof_erda", mentions="Cl"),
    f("s9.p1", "observation", "the TOF-ERDA film at 350 °C is 20 nm thick", quantity="film_thickness", qualifiers="position=planar", value="20", unit="nm", data_kind="stated", method="tof_erda"))
put(meas(A250, "tof_erda"), f("s9.p2;fig5b", "observation", "at 250 °C the oxygen share is 6.6 at.%", quantity="element_fraction", qualifiers="element=O", value="6.6", unit="at.%", data_kind="measured", method="tof_erda", mentions="250 °C"))
put(meas(A150, "tof_erda"), f("s9.p2;fig5b;abs.g4", "observation", "at 150 °C the oxygen share is 33.3 at.%", quantity="element_fraction", qualifiers="element=O", value="33.3", unit="at.%", data_kind="measured", method="tof_erda", mentions="150 °C"),
    f("s9.p2;fig5b;abs.g4", "observation", "at 150 °C the chlorine share is 2.7 at.%", quantity="element_fraction", qualifiers="element=Cl", value="2.7", unit="at.%", data_kind="measured", method="tof_erda", mentions="150 °C"))
put(meas(A350, "sims"), f("fig6a;fig6.cap;s9.p5", "observation", "Fig. 6(a): SIMS depth profile of the 350 °C ALD film: O, Cl, C, N and Si contaminants near 1e20 atoms per cm3", quantity="other", label_as_printed="contaminant concentration", value="1e20",
                            unit="cm-3", data_kind="measured", method="sims", mentions="O;Cl;C;N;Si;Fig. 6(a)"))
put(meas(C250, "sims"), f("fig6b;fig6.cap;s9.p5", "observation", "Fig. 6(b): in the CVD film grown at 250 °C oxygen exceeds 1e22 atoms per cm3, tens of atomic percent, while chlorine only approaches 1e20", quantity="other", label_as_printed="oxygen concentration",
                            value="1e22", unit="cm-3", censor=">", data_kind="measured", method="sims", mentions="O;Cl;Fig. 6(b)"))
# Fig. 7 and 8: resistivity, crystallinity
put(meas(A350Q, "four_point_probe"),
    f("fig7a;fig7.cap;s10.p1", "observation", "Fig. 7(a): the resistivity against ALD film thickness at 350 °C on SiO2", quantity="resistivity", method="four_point_probe", mentions="Fig. 7(a)"),
    f("s10.p1;abs.g4;s12.p2", "observation", "the resistivity approaches 18.6 µΩ cm for the about 24 nm thick film", quantity="resistivity", value="18.6", unit="µΩ cm", data_kind="measured", method="four_point_probe", mentions="24 nm"),
    f("s10.p1", "observation", "the film of the bulk-like resistivity is about 24 nm thick", quantity="film_thickness", qualifiers="position=planar", value="24", unit="nm", data_kind="stated", method="spectroscopic_ellipsometry"))
put(meas(A350, "four_point_probe"), f("fig7b;fig7.cap;s10.p2", "observation", "Fig. 7(b): the resistivity of about 25 nm ALD films against temperature, corrected for the parallel path through the Si substrate; low above 250 °C, rising sharply below", quantity="resistivity",
                                      method="four_point_probe", mentions="ALD;Fig. 7(b);ref 67;25 nm"))
put(meas(C350, "four_point_probe"), f("fig7b;fig7.cap;s10.p2", "observation", "Fig. 7(b): the CVD films' resistivity rises sharply below 350 °C", quantity="resistivity", method="four_point_probe", mentions="CVD;Fig. 7(b)"))
th150 = f("s10.p2", "observation", "the 150 °C ALD film of Fig. 7(b) is about 50 nm thick, its lower density stretching the thickness", quantity="film_thickness", qualifiers="position=planar", value="50", unit="nm", data_kind="stated", method="spectroscopic_ellipsometry")
put(meas(A150, "spectroscopic_ellipsometry"), th150)
put(meas(A350, "xrd"), f("fig8;fig8.cap;s10.p2", "observation", "Fig. 8: GIXRD of the 350 °C film shows peaks at 41°, 59° and 74°, BCC Mo's (110), (200) and (211) planes", quantity="crystallinity", value_text="crystalline", data_kind="measured", method="xrd",
                          mentions="41°;59°;74°;Fig. 8"))
put(meas(A150, "xrd"), f("fig8;fig8.cap;s10.p2", "observation", "Fig. 8: the 150 °C film shows only the (311) peak of the p-Si(100) substrate, so it is amorphous", quantity="crystallinity", value_text="amorphous", data_kind="measured", method="xrd", mentions="Fig. 8"))
# uniformity on the wafer
unif = f("s11.p1;abs.g4", "observation", "thickness and sheet resistance vary ±5 % within a 7 cm circle centred on the 100 mm wafer, more toward the edge", quantity="thickness_nonuniformity", value="0.05", data_kind="measured", method="four_point_probe",
         mentions="±5%;7 cm;100 mm;Figs. S5 and S6")
put(meas(A350, "four_point_probe"), unif)
# the trench specimen
TR = node(f"{K}:ent:trench", "entity", "Mo in SiO2-capped Si trenches of aspect ratio 2:1 to 10:1, grown by ALD", DEP_A, evidence="s11.p5;fig9.cap;fig10.cap", how="stated", label_as_printed="Mo in Si trenches")
put(TR, f("s11.p5;fig9.cap", "setting", "the conformality specimen: Si trenches with an SiO2 capping on which the Mo grew", quantity="structure", value_text="si_trench_capped", data_kind="stated"),
    f("s11.p5", "setting", "the trenches span aspect ratios of 2–10 (2:1 to 10:1)", quantity="aspect_ratio", value_min="2", value_max="10", data_kind="stated"),
    f("s11.p5", "setting", "the trench surface is the SiO2 capping", quantity="substrate", value_text="sio2", data_kind="stated"))
put(meas(TR, "tem"),
    f("fig9a;fig9.cap;s11.p5", "observation", "Fig. 9(a): the STEM image of the layer stack with the conformality estimate", method="tem", mentions="Fig. 9(a)"),
    f("s11.p5;abs.g4", "observation", "in the 3:1 trench the sidewall film is 95 % of the top thickness", quantity="step_coverage", qualifiers="position=sidewall", value="0.95", data_kind="measured", method="tem", mentions="3:1;95%"),
    f("s11.p5;abs.g4", "observation", "in the 3:1 trench the bottom film is 90 % of the top thickness", quantity="step_coverage", qualifiers="position=bottom", value="0.90", data_kind="measured", method="tem", mentions="3:1;90%"),
    f("s11.p5", "setting", "the conformality figures refer to the trench of aspect ratio 3:1", quantity="aspect_ratio", value="3", data_kind="stated", mentions="3:1"),
    f("fig9b;fig9.cap;s11.p6", "observation", "Fig. 9(b): the FFT rings correspond to d spacings 2.22 Å, 1.57 Å and 1.26 Å, body-centred cubic Mo", quantity="phase", qualifiers="species=mo", value_text="detected", data_kind="measured", method="tem",
      mentions="2.22 Å;1.57 Å;1.26 Å;BCC;Fig. 9(b);ref 73"))
put(meas(TR, "tem_eds"),
    f("fig10a;fig10c;fig10e;fig10.cap;s11.p6", "observation", "Fig. 10(a),(c),(e): STEM image and Mo and O EDX maps near the top of a narrow trench, a uniform distribution", method="tem_eds", mentions="Fig. 10(a);Fig. 10(c);Fig. 10(e)"),
    f("fig10b;fig10d;fig10f;fig10.cap;s11.p6", "observation", "Fig. 10(b),(d),(f): Mo reaches the bottom of the narrow trench", method="tem_eds", mentions="Fig. 10(b);Fig. 10(d);Fig. 10(f)"),
    f("s11.p6", "derived", "the EDX line integral puts the oxygen share at the trench bottom at roughly twice that at the top", quantity="other", label_as_printed="oxygen share ratio, bottom over top", value="2", data_kind="computed_by_authors", method="tem_eds"),
    f("s11.p6;s11.p9", "observation", "the chlorine share is low and about uniform from top to bottom", quantity="element_fraction", qualifiers="element=Cl", method="tem_eds", mentions="low"))
# cited
REFS = {n: node(f"{K}:refs:{n}", "cited", f"cited work, reference {n} of the paper", PAPER, evidence=ev, label_as_printed=f"ref. {n}") for n, ev in (("4", "s10.p2"), ("31", "s10.p1"), ("39", "s10.p1"), ("40", "s10.p1"), ("61", "s10.p1"))}
put(REFS["4"], r_mfp)
put(REFS["61"], r_res[0], r_h2)
put(REFS["39"], r_res[1])
put(REFS["31"], r_res[2])
put(REFS["40"], r_res[3])
BY_TEXT = {"a hot-wire-assisted ALD process deposits": [RA, RB, Trange], "molecular hydrogen deposits nothing": [FILMS["ald350"]], "at 350 °C and above the films are nearly pure": [FILMS["ald350"]],
           "no substrate selectivity or pronounced nucleation delay": [SUB, FILMS["ald350_sio2"]], "thickness and sheet resistance vary": [unif], "at 250 °C and below more oxygen and chlorine": [FILMS["ald250"], FILMS["ald150"]],
           "self-limiting growth spans": [Trange, FILMS["ald250"]], "below the electron mean free path of Cu and W": [r_mfp], "ALD's self-limiting reactions give the thickness control": [TR], "earlier Mo CVD and ALD routes": [r_h2] + r_res,
           "hot-wire ALD makes atomic hydrogen": [RB, fh2], "at 350 °C the growth per cycle saturates": [FILMS["ald350"]], "the standard cycle 1/15/29/15 s": [tA, pA, tB, pB], "sequential MoCl2O2 pulses without atomic hydrogen": [tA],
           "the growth per cycle is about constant": [FILMS["ald350"], FILMS["cvd350"]], "the higher CVD growth per cycle": [FILMS["cvd350"]], "on SiO2 the steady regime starts": [FILMS["ald350_sio2"]],
           "mass spectrometry shows HCl": [FILMS["ald350"]], "TOF-ERDA of a 20 nm film": [FILMS["ald350"], FILMS["ald250"], FILMS["ald150"]], "SIMS puts the O, Cl, C, N and Si": [FILMS["ald350"], FILMS["cvd250"]],
           "the resistivity approaches a bulk-like": [FILMS["ald350_sio2"], r_mfp], "other Mo ALD works reached": r_res, "GIXRD of the 350 °C film": [FILMS["ald350"], FILMS["ald150"]], "in SiO2-capped Si trenches": [TR],
           "the FFT rings of the TEM image": [TR], "EDX shows Mo reaching the bottom": [TR]}
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
GROUPS = [(f"{K}:grp:ald_T", "series", "deposition_temperature", "the ALD temperature series: Figs. 2, 5(b), 7(b), 8, from 150 to 450 °C", "fig2.cap;fig5.cap;fig7.cap;fig8.cap", c_lowT, [A150, A250, A350, A450]),
          (f"{K}:grp:cvd_T", "series", "deposition_temperature", "the CVD temperature series: Figs. 2, 6(b), 7(b)", "fig2.cap;fig6.cap;fig7.cap", c_gpcT, [C250, C350]),
          (f"{K}:grp:mode", "series", "material", "ALD against pulsed CVD at the standard temperature: Figs. 2 and 7(b)", "fig2.cap;s5.p3", c_cvd, [A350, C350])]
for gid, kind, varied, st, ev, pur, members in GROUPS:
    N(gid, "group", st, PAPER, evidence=ev, label_as_printed=st.split(":")[0], qualifiers="how=stated", links=";".join([pur] + members))
C.comparisons(K, {gid: (kind, varied) for gid, kind, varied, *_ in GROUPS})
C.modes(K, MODES)
C.qualify(K, {})
CAV = [
    ("s8.x1", "Below 5 nm the SE thickness is not verified by XRR, SEM or TEM, and the optical constants were fitted along with the thickness; the nucleation stage is uncertain.", [FILMS["ald350_sio2"]], "film_thickness", ""),
    ("s7.p4", "The hot-wire temperature of Fig. 1(e) is estimated from the wire power through an earlier setup, not measured here.", [FILMS["ald350"]], "", ""),
    ("s10.p2", "The Fig. 7(b) resistivities are corrected for the parallel conduction through the Si substrate; the 150 °C ALD film is about 50 nm, the others about 25 nm.", [FILMS["ald350"], FILMS["ald150"], FILMS["cvd350"]], "resistivity", ""),
    ("s11.p5", "The conformality was read from STEM images of one 3:1 trench; the trench film's deposition temperature is not stated.", [TR], "", ""),
    ("s8.p3", "Mass spectrometry was run outside the standard ALD conditions to protect the sensor.", [FILMS["ald350"]], "", ""),
    ("s5.p2", "The substrates were cleaned in three different ways; no effect on nucleation was seen, but it was not studied systematically.", [clean], "", ""),
]
for ev_, st_, links_, q_, qq_ in CAV:
    C.caveat(K, ev_, st_, [x if x.startswith(K + ":") else f"{K}:{x}" for x in links_], q_, qq_)
C.specimen_classes(K, "film")
C.structure_classes(K)
C.rekey_structure_dimensions(K)
write(K, PID)
