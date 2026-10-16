#!/usr/bin/env python3
"""Stage 2 facts for gre23 (10.1116_6.0003182): one row per piece of knowledge, each citing the elements that state it.

    python3 psed_v2/pilot/10.1116_6.0003182.facts.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import re  # noqa: E402
import facts as C  # noqa: E402
from facts import F, N, NK, P, write, cases_points  # noqa: E402

K, PID = "gre23", "10.1116_6.0003182"


def f(ev, t, s, **kw):
    return F(K, ev, t, s, **kw)


A = "s5.p1"  # the abstract printed again as a body paragraph

# ---------------------------------------------------------------- front matter
NK("s0.p1;s1.p1;s1.p3;s1.p4;s3.p1;s3.p2;s3.p3;s3.p4;s3.p5;s3.p6;s4.p4;s5.p3", "front matter")
NK("s1.h;s3.h", "title")
NK("s1.p2;s3.p7", "author list")
NK("s2.h;s2.p1;s2.p2;s2.p3;s2.p4;s2.p5;s2.p6", "publisher list of related articles")
NK("s4.h;s4.p1;s4.p2;s4.p3", "affiliations")
NK("s4.p5", "contact e-mail")
NK("s5.p2;s14.p5;s15.p5;s15.p7", "download stamp")
NK("s5.h;s6.h;s7.h;s8.h;s9.h;s10.h;s11.h;s12.h;s13.h;s14.h;s15.h", "heading")

# ---------------------------------------------------------------- abstract-only statements
f(f"abs.g1;{A}", "claim", "conformal ALD in macroscopic nanoporous solids with AR above 10^3 may need reactant exposures of about 10^3 Torr-s or more")
f(f"abs.g1;{A}", "claim", "with some ALD chemistries, exposures that large make non-self-limiting growth a concern")
f(f"abs.g2;{A}", "cited", "DEZ/H2O ZnO ALD with exposures between 10 and 10^3 Torr-s has given metallic Zn at temperatures usual for wafers, e.g. ~180 °C",
  quantity="exposure", value_min="10", value_max="1e3", unit="Torr-s", data_kind="literature", method="cited", mentions="~180 °C")
f(f"abs.g2;{A};s6.p6", "claim", "a lower deposition temperature suppresses the Zn deposition but slows H2O desorption, which can force impractically long purges")
f(f"abs.g3;{A}", "setting", "the static-dose DEZ and H2O exposures used here exceed 10^4 Torr-s",
  quantity="exposure", value="1e4", censor=">", unit="Torr-s", data_kind="chosen input")
f(f"abs.g4;{A};s15.p2;s15.p3;s14.p8;s14.p10", "claim", "the temperature-cycled process gives apparently self-limiting ZnO growth with a conductive ZnO network uniform through the NPC thickness, apart from some ZnO depletion near the faces")
f(f"abs.g4;{A};s15.p3", "claim", "the T = 120 °C process gives results like the cycled one but with a slightly higher GPC, pointing to less H2O and/or OH removed during purges",
  mentions="T = 120 °C")
f(f"abs.g5;{A}", "setting", "the three processes are compared with SEM-EDS, XRD, electrical resistivity and analysis of the ALD chamber pressure")

# ---------------------------------------------------------------- I. introduction
f("s6.p1", "claim", "ALD can coat the inner surfaces of porous nanoparticle networks and so change their optical, electronic or structural properties")
f("s6.p1", "claim", "self-limiting half-reactions can in principle coat the whole inner surface of an NP network uniformly if the pores are open and the whole surface sees enough reactant")
f("s6.p1", "definition", "aspect ratio AR of an NP network: its thickness L divided by the mean pore diameter d_pore", mentions="ref. 1")
f("s6.p1", "cited", "the minimum exposure needed depends on the network porosity φ and on the AR", mentions="ref. 1")
f("s6.p2", "cited", "for NP thin films with porosity ~0.3 to ~0.5 and AR ~100 or less (L ~100 nm to ~1 µm, d_pore ~5 to ~20 nm) about 1 Torr or less of reactant suffices",
  quantity="partial_pressure", value="1", unit="Torr", data_kind="literature", method="cited")
f("s6.p2", "cited", "for such NP thin films an exposure time of about 1 s or less is usually enough",
  quantity="pulse_time", value="1", unit="s", data_kind="literature", method="cited")
f("s6.p2", "cited", "NP thin films have been ALD-coated with Al2O3, HfO2 and ZnO", mentions="ref. 2-8;ref. 5;ref. 4;ref. 6-8")
f("s6.p2", "cited", "a ZnO coating is attractive for its semiconducting behaviour and because it enables bandlike transport in NP networks", mentions="ref. 6;ref. 7")
f("s6.p3;s6.p4", "claim", "scaling the substrate up from NP thin films to mm-scale NP networks with L of order 1 mm and AR of order 10^4 could widen applications but needs much larger exposures")
f("s6.p4", "cited", "Gayle et al. ran one TMA/H2O Al2O3 cycle through a silica aerogel monolith with AR above 60 000",
  quantity="aspect_ratio", value="60000", censor=">", data_kind="literature", method="cited", mentions="ref. 9;Gayle et al.")
f("s6.p4", "cited", "porosity of that silica aerogel monolith: φ = 0.95",
  quantity="porosity", label_as_printed="φ", value="0.95", data_kind="literature", method="cited", mentions="ref. 9")
f("s6.p4", "cited", "pore diameter of that aerogel monolith ≈ 20 nm",
  quantity="feature_width", label_as_printed="d_pore", value="20", unit="nm", data_kind="literature", method="cited", mentions="ref. 9")
f("s6.p4", "cited", "L of the aerogel monolith ≈ 1.25 mm, taken as half its thickness since reactants diffused in from top and bottom",
  quantity="feature_depth", label_as_printed="L", value="1.25", unit="mm", data_kind="literature", method="cited", mentions="ref. 9")
f("s6.p4", "cited", "full infiltration, checked by SEM-EDS, took a series of 12 TMA doses with total exposure above 10^4 Torr-s",
  quantity="exposure", value="1e4", censor=">", unit="Torr-s", data_kind="literature", method="cited", mentions="ref. 9")
# Ingale (ref. 10)
f("s6.p5", "cited", "Ingale et al. deposited up to three ZnO cycles at 80 °C onto ~2 g of mesoporous SiO2 powder",
  quantity="deposition_temperature", value="80", unit="°C", data_kind="literature", method="cited", mentions="ref. 10;Ingale et al.")
f("s6.p5", "cited", "specific surface area of the mesoporous SiO2 powder of Ingale et al.: 505 m2/g",
  quantity="other", label_as_printed="s", value="505", unit="m2/g", data_kind="literature", method="cited", mentions="ref. 10")
f("s6.p5", "cited", "XRD, TEM, x-ray fluorescence and mass-gain data of Ingale et al. fit ZnO through the whole powder bed at a GPC of ~1 Å/cyc",
  quantity="growth_per_cycle", value="1", unit="Å/cyc", data_kind="literature", method="cited", mentions="ref. 10")
# Ferguson (ref. 11)
f("s6.p5", "cited", "Ferguson et al. coated ZrO2 NP powder with ZnO at 177 °C",
  quantity="deposition_temperature", value="177", unit="°C", data_kind="literature", method="cited", mentions="ref. 11;Ferguson et al.")
f("s6.p5", "cited", "the ZrO2 powder of Ferguson et al. had s = 20.2 m2/g",
  quantity="other", label_as_printed="s", value="20.2", unit="m2/g", data_kind="literature", method="cited", mentions="ref. 11")
f("s6.p5", "cited", "the ZrO2 particles of Ferguson et al. had d_NP = 50 nm",
  quantity="other", label_as_printed="d_NP", value="50", unit="nm", data_kind="literature", method="cited", mentions="ref. 11")
f("s6.p5", "cited", "TEM coating thicknesses of Ferguson et al. gave a GPC of ~2.2 Å/cyc",
  quantity="growth_per_cycle", value="2.2", unit="Å/cyc", data_kind="literature", method="cited", mentions="ref. 11")
f("s6.p5", "cited", "Ferguson et al. saw signs of non-self-limiting growth during the DEZ exposure", mentions="ref. 11")
f("s6.p5", "cited", "raising the exposure up to 900 Torr-s, Ferguson et al. found by in situ FTIR that background absorbance grew with exposure, which they assigned to conductive Zn from DEZ decomposition",
  quantity="exposure", value_max="900", unit="Torr-s", data_kind="literature", method="cited", mentions="ref. 11")
# Libera (ref. 12)
f("s6.p5", "cited", "Libera et al. found Zn metal by XRD in ZnO ALD coatings in mesoporous silica gel (1 g batches, s = 100 m2/g)",
  quantity="other", label_as_printed="s", value="100", unit="m2/g", data_kind="literature", method="cited", mentions="ref. 12;Libera et al.")
f("s6.p5", "cited", "Libera et al. deposited ten ZnO cycles with the DEZ exposure kept at 22.5 Torr-s",
  quantity="exposure", value="22.5", unit="Torr-s", data_kind="literature", method="cited", mentions="ref. 12")
f("s6.p5", "cited", "Libera et al. ran depositions between 150 and 200 °C",
  quantity="deposition_temperature", value_min="150", value_max="200", unit="°C", data_kind="literature", method="cited", mentions="ref. 12")
f("s6.p5", "cited", "Zn metal XRD peaks appeared at 155 °C and grew steadily stronger with temperature",
  quantity="deposition_temperature", value="155", unit="°C", data_kind="literature", method="cited", mentions="ref. 12")
f("s6.p5", "cited", "the coated silica turned gradually from white at 150 °C to black at 200 °C along with the Zn peak growth", mentions="ref. 12")
f("s6.p5", "cited", "at a fixed 200 °C, DEZ exposures below 10 Torr-s gave no Zn metal in XRD and no colour change",
  quantity="exposure", value="10", censor="<", unit="Torr-s", data_kind="literature", method="cited", mentions="ref. 12;200 °C")
f("s6.p5", "cited", "ZnO infiltration of NP thin films at 180 °C with DEZ exposure below 1 Torr-s showed no Zn metal",
  quantity="exposure", value="1", censor="<", unit="Torr-s", data_kind="literature", method="cited", mentions="ref. 4;ref. 6-8;180 °C")
f("s6.p6", "claim", "using a lower temperature to avoid Zn is hard to apply to conductive ZnO coatings on macroscopic NP networks for two reasons")
f("s6.p6", "cited", "below ~170 °C the resistivity of ALD ZnO often rises with deposition temperature, through the temperature dependence of stoichiometry, grain size and orientation",
  quantity="deposition_temperature", value="170", censor="<", unit="°C", data_kind="literature", method="cited", mentions="ref. 13;ref. 14")
f("s6.p6", "cited", "H2O desorbs from ZnO more slowly at lower temperature, with the usual exponential dependence", mentions="ref. 15")
f("s6.p6;s6.p7", "claim", "so the needed H2O purge time depends exponentially on temperature, which matters for long infiltration runs (possibly ~100 cycles) aimed at high-conductance coatings")
f("s6.p8", "claim", "the NP networks studied here have AR ~100 times that of the NP thin films coated with ZnO in earlier work", mentions="ref. 6-8")
f("s6.p8", "claim", "the case is useful both for the difficulty of avoiding Zn deposition and because the conductive ZnO lets infiltration be checked electrically")
cyc20 = f("s6.p8;s9.p4;s9.p6;s15.p1", "setting", "each ZnO ALD run on the NPCs has 20 cycles",
          quantity="cycle_number", value="20", data_kind="chosen input")
L_ = f("s6.p8;s15.p2", "setting", "NPC half-thickness L = 0.78 ± 0.02 mm",
       quantity="feature_depth", label_as_printed="L", value="0.78", unit="mm", data_kind="calculated")
f("s6.p8;fig1.cap;s9.p2", "definition", "L is taken as half the NPC thickness since precursors get in through both the top face and the bottom face")
dpore = f("s6.p8;s8.p1", "claim", "pore diameter roughly equals the NP diameter, 100 nm, given the initial porosity",
          quantity="feature_width", label_as_printed="d_pore", value="100", unit="nm", data_kind="assumed")
f(f"s6.p8;abs.g3;{A};s15.p2", "derived", "NPC aspect ratio 7800 ± 200, from the half-thickness L and d_pore",
  quantity="aspect_ratio", value="7800", data_kind="calculated", method="calculation", inputs=[L_, dpore])
f("s6.p8", "cited", "some aerogel monoliths coated with Al2O3 or ZnO by ALD have higher AR than these NPCs", mentions="ref. 9;ref. 16")
f("s6.p8", "claim", "the NPC porosity (50.5 ± 0.3%) is far below the 95+% of aerogel monoliths, which lowers reactant diffusivity")
f("s6.p8;s9.p4;s12.p1", "setting", "reactant partial pressure in each exposure is ~9 Torr for both DEZ and H2O",
  quantity="partial_pressure", value="9", unit="Torr", data_kind="chosen input", mentions="DEZ;H2O")
f("s6.p8", "setting", "exposure of ~17 000 Torr-s per reactant, from ~9 Torr held for 1920 s (32 min)",
  quantity="exposure", value="17000", unit="Torr-s", data_kind="calculated", mentions="DEZ;H2O")
f("s6.p8", "claim", "the temperature schedule is explored to see whether Zn metal can be avoided while the total run time stays reasonable")

# ---------------------------------------------------------------- II A. compacts
f("s8.p1", "setting", "the porous Al2O3 NPCs were pressed in air in an 11.4 mm tungsten carbide die (REFLEX) using a manual 12 ton hydraulic press (Carver)",
  quantity="other", label_as_printed="die diameter", value="11.4", unit="mm", data_kind="chosen input")
s_ = f("s8.p1", "setting", "the starting powder is BMA15 deagglomerated alpha alumina (Baikowski) with s = 15 m2/g, the maker's BET specification",
       quantity="other", label_as_printed="s", value="15", unit="m2/g", data_kind="literature")
f(f"s8.p1;abs.g3;{A};s10.p1;fig1a;fig1.cap;s9.p2", "derived", "NP diameter d_NP = 100 nm, obtained from s = 15 m2/g",
  quantity="other", label_as_printed="d_NP", value="100", unit="nm", data_kind="calculated", method="calculation", inputs=[s_])
f("s8.p1", "setting", "powder mass per compact 0.320 ± 0.005 g",
  quantity="other", label_as_printed="powder mass", value="0.320", unit="g", data_kind="chosen input")
f("s8.p1", "setting", "pressing pressure 481 MPa",
  quantity="other", label_as_printed="pressing pressure", value="481", unit="MPa", data_kind="chosen input")
f("s8.p1", "setting", "the load was held under 1 min, then released and the compact ejected",
  quantity="other", label_as_printed="load hold", value="1", censor="<", unit="min", data_kind="chosen input")
f(f"s8.p1;abs.g3;{A}", "observation", "final NPC thickness 1.55 ± 0.05 mm by electronic calipers",
  quantity="other", label_as_printed="thickness", value="1.55", unit="mm", data_kind="measured")
f("s8.p1", "observation", "final NPC diameter 11.43 ± 0.02 mm by electronic calipers",
  quantity="other", label_as_printed="diameter", value="11.43", unit="mm", data_kind="measured")
phi_i = f(f"s8.p1;abs.g3;{A};s6.p8;s15.p2;s12.p1;tabI.cap;s13.p5", "observation", "initial NPC porosity φ_i = 50.5 ± 0.3% (printed φ_1 in the text and φ_f in the Table I caption)",
          quantity="porosity", qualifiers="stage=initial", label_as_printed="φ_i", value="50.5", unit="%", data_kind="measured", mentions="φ_1;φ_f")
f("s8.p1", "observation", "the pressing recipe was tuned for intact compacts, yet some mm-scale cracks appeared", mentions="Fig. S1")

# ---------------------------------------------------------------- II B. ZnO ALD
f("s9.p1", "setting", "reactor, with a near-horizontal cylindrical chamber and an MKS LoPro isolation valve to the pump",
  quantity="reactor_type", value_text="ALD NanoSolutions (Forge Nano) custom RX-series")
f("s9.p1", "setting", "deposition chamber about 20 cm long and 10 cm inner diameter",
  quantity="other", label_as_printed="chamber length", value="20", unit="cm", data_kind="chosen input", mentions="10 cm ID")
f("s9.p1;s9.p3;fig1a", "setting", "the NPCs sit in a round-bottomed rectangular quartz boat touching only at their lower circular edge, leaving at most ~1 mm under the bottom face",
  quantity="other", label_as_printed="gap height", value_max="1", unit="mm", data_kind="chosen input", mentions="Fig. 1")
f("s9.p3;s12.p1", "setting", "every NPC was weighed before and after ALD to get the deposited ZnO mass", method="gravimetry")
f("s9.p3", "setting", "chamber pressure read by two Baratron 728A manometers (MKS) heated to 100 °C, with 10 and 1000 Torr full scale",
  quantity="other", label_as_printed="gauge temperature", value="100", unit="°C", data_kind="chosen input", method="process_monitor")
f("s9.p3", "setting", "base pressure set to 0 Torr at 120 °C because of gauge drift, i.e. a 0.26 Torr offset subtracted from all pressure data",
  quantity="other", label_as_printed="pressure offset", value="0.26", unit="Torr", data_kind="chosen input", method="process_monitor")
f("s9.p3", "claim", "the offset does not matter for the trace analysis, which uses pressure changes only")
f("s9.p4", "setting", "precursors: diethylzinc (min. 95%, Strem Chemicals) and de-ionized H2O",
  quantity="precursor_purity", value="95", unit="%", data_kind="chosen input", qualifiers="species=DEZ")
f("s9.p4", "setting", "both precursors held at 37 °C in heated stainless steel cylinders, with metering valves for the vapor flow",
  quantity="source_temperature", value="37", unit="°C", data_kind="chosen input", mentions="DEZ;H2O")
f("s9.p4", "definition", "static dosing: vapor kept in the chamber without flow for a long time so it can diffuse into the NPC")
f("s9.p4", "setting", "one cycle lasts ~160 min",
  quantity="cycle_time", value="160", unit="min", data_kind="chosen input")
f("s9.p4", "setting", "DEZ pulse 10-14 s",
  quantity="pulse_time", qualifiers="step=reactant_A;species=DEZ", value_min="10", value_max="14", unit="s", data_kind="chosen input")
f(f"s9.p4;s6.p8;s12.p1;fig1b", "setting", "DEZ hold 1920 s (32 min); a dose is the pulse plus the hold",
  quantity="other", label_as_printed="DEZ hold", qualifiers="step=hold_A;species=DEZ", value="1920", unit="s", data_kind="chosen input")
f("s9.p4;s14.p6;s9.p9", "setting", "purge after DEZ 2880 s (48 min), not optimized and set equal to the H2O purge",
  quantity="purge_time", qualifiers="step=purge_A", value="2880", unit="s", data_kind="chosen input")
f("s9.p4", "setting", "H2O pulse 8-11 s",
  quantity="pulse_time", qualifiers="step=reactant_B;species=H2O", value_min="8", value_max="11", unit="s", data_kind="chosen input")
f("s9.p4;s6.p8", "setting", "H2O hold 1920 s (32 min)",
  quantity="other", label_as_printed="H2O hold", qualifiers="step=hold_B;species=H2O", value="1920", unit="s", data_kind="chosen input")
f("s9.p4;s9.p9;s12.p1;s15.p3", "setting", "purge after H2O 2880 s (48 min)",
  quantity="purge_time", qualifiers="step=purge_B", value="2880", unit="s", data_kind="chosen input")
f("s9.p4", "observation", "pulse times were adjusted by hand to keep exposure pressures near ~9 Torr, which still fluctuated, perhaps from valve control or unheated line sections",
  mentions="Fig. S2")
f("s9.p4;s9.p5;s12.p2", "setting", "during pulses and holds the pump isolation valve is shut; during holds the ALD valves are shut too, isolating the chamber")
f("s9.p5", "observation", "the isolated deposition volume is 2.17 l from pressure-versus-flow tests, including small extras such as 1/4 in. and KF25 tubing",
  quantity="other", label_as_printed="isolated deposition volume", value="2.17", unit="l", data_kind="measured")
f("s9.p5", "setting", "purges open the isolation valve and feed N2: 30 s without flow, 30 s at 10 SCCM through the half of the manifold just used, 2790 s at 10 SCCM through each half, 30 s without flow",
  quantity="carrier_gas", qualifiers="gas=N2")
f("s9.p5;s9.p6;fig2.cap;s12.p12", "setting", "main purge N2 flow 20 SCCM in total",
  quantity="gas_flow_rate", qualifiers="gas=N2", value="20", unit="SCCM", data_kind="chosen input")
f("s9.p6", "setting", "chamber heated by an insulating heater jacket controlled by a thermocouple on the chamber outside", method="process_monitor")
f("s9.p6;fig2.cap;s12.p12;fig1a", "definition", "T: approximate steady-state temperature (to the nearest 10 °C) of the inner quartz-boat surface under 20 SCCM N2, found in calibration with a thermocouple touching the boat")
f("s9.p6", "observation", "calibration runs at the same outside temperature gave deposition temperatures differing by about ±5 °C, from thermocouple placement and pressure",
  quantity="deposition_temperature", qualifiers="stat=half_range;between=runs;n=not_stated", label_as_printed="calibration spread", value="5", unit="°C",
  data_kind="measured", method="process_monitor")
f(f"s9.p6;abs.g3;{A};s6.p8;fig1b;fig2.cap;s12.p12;fig3.cap;s12.p16", "setting", "run (1): T held at 120 °C",
  quantity="deposition_temperature", value="120", unit="°C", data_kind="chosen input", mentions="T held constant at 120 °C;120 °C")
f(f"s9.p6;abs.g3;{A};s6.p8;fig1b;fig2.cap;s12.p12;fig3.cap;s12.p16", "setting", "run (2): T held at 160 °C",
  quantity="deposition_temperature", value="160", unit="°C", data_kind="chosen input", mentions="T held constant at 160 °C;160 °C")
f(f"s9.p6;abs.g3;{A};s6.p8;s15.p2;fig1b;fig2.cap;s12.p12", "setting", "run (3), cycled: T is 120 °C for every step but the H2O purge",
  quantity="deposition_temperature", qualifiers="step=reactant_A", value="120", unit="°C", data_kind="chosen input", mentions="T cycled between 120 and 160 °C;120/160 °C")
f(f"s9.p6;abs.g3;{A};s6.p8;s15.p2;fig1b", "setting", "run (3), cycled: during each H2O purge T is raised to 160 °C and brought back to 120 °C before the next DEZ pulse",
  quantity="deposition_temperature", qualifiers="step=purge_B", value="160", unit="°C", data_kind="chosen input", mentions="T cycled between 120 and 160 °C;120/160 °C")
f("s9.p6;fig2.cap;s12.p12", "setting", "an H2O half-cycle hydroxylates the Al2O3 before each run's ZnO ALD")
f("s9.p6", "setting", "before that half-cycle the NPCs degas at least 2 h in the chamber at the starting T (120 or 160 °C)",
  quantity="other", label_as_printed="degassing time", value="2", censor=">", unit="h", data_kind="chosen input")
f("s9.p6", "observation", "in all three runs the inner wall of the main chamber is about at the boat temperature T")
f("s9.p6", "setting", "small parts of the deposition volume outside the main chamber (1/4 in. and KF25 tubing) are tape-heated to 100-130 °C outside",
  quantity="other", label_as_printed="external surface temperature", value_min="100", value_max="130", unit="°C", data_kind="chosen input")
f("s9.p6;s12.p6", "claim", "those tubing parts are expected to be ~90 to ~120 °C inside",
  quantity="other", label_as_printed="internal surface temperature", value_min="90", value_max="120", unit="°C", data_kind="assumed")
f("s9.p6", "claim", "surfaces not heated directly, such as the quartz and sapphire windows, may be below 90 °C inside",
  quantity="other", label_as_printed="window temperature", value="90", censor="<", unit="°C", data_kind="assumed")
f("s9.p7", "claim", "the process designs follow theory by Yanguas-Gil and Elam and the study of Cendejas et al. on exposure and purge times for uniform coating of nanostructures",
  mentions="ref. 17;ref. 18;ref. 8;Note S1")
f("eq1;s9.p7", "model", "Eq. (1): hold time t_hold = L_pore^2 / (D γ); used to set the hold times")
f("s9.p8;eq1", "definition", "L_pore: mean pore length including tortuosity")
f("s9.p8;eq1", "definition", "D: the diffusion coefficient, here the Knudsen coefficient")
f("s9.p8;eq1", "definition", "γ: number of reactant molecules in the nanostructure for each reaction site")
f("eq2;s9.p8", "model", "Eq. (2): purge time t_purge equals ln(1/θ_f) over ν exp(-E_des/RT); used to set the purge times")
f("s9.p9;eq2", "definition", "θ_f: the fractional coverage of adsorbed H2O left after the purge")
nu = f("s9.p9;eq2", "model", "pre-exponential factor ν = 10^13 s^-1 in Eq. (2)",
       quantity="other", label_as_printed="ν", value="1e13", unit="s^-1", data_kind="literature", mentions="ref. 21")
f("s9.p9;eq2", "model", "E_des, the H2O desorption energy, is taken as independent of coverage")
th = f("s9.p9", "model", "target θ_f = 5 × 10^-3, which Cendejas et al. found necessary for uniform infiltration",
       quantity="other", label_as_printed="θ_f", value="5e-3", data_kind="literature", mentions="ref. 8")
f("s9.p9", "derived", "Eq. (2) gives a needed purge of 360 min at T = 120 °C",
  quantity="purge_time", qualifiers="step=purge_B", value="360", unit="min", data_kind="calculated", method="calculation", mentions="T = 120 °C", inputs=[nu, th])
f("s9.p9", "derived", "Eq. (2) gives a needed purge of 11 min at T = 160 °C",
  quantity="purge_time", qualifiers="step=purge_B", value="11", unit="min", data_kind="calculated", method="calculation", mentions="T = 160 °C", inputs=[nu, th])
f("s9.p9", "claim", "48 min was chosen so that θ_f below 5 × 10^-3 is reachable in the 120/160 and 160 °C processes", mentions="120/160 °C;160 °C")

# ---------------------------------------------------------------- II C. characterization
f("s10.p1", "setting", "all coated NPCs saw ambient air before characterization, and during XRD and resistivity measurement")
f("s10.p1", "setting", "XRD with Cu Kα1 from a rotating anode on a Rigaku high-resolution powder diffractometer at 50 kV and 200 mA", method="xrd")
f("s10.p1", "setting", "2θ range 20° to 80°, scanned at 1°/min in 0.02° steps", method="xrd")
f("s10.p1", "setting", "NPCs taped to low-background quartz holders; one outer face scanned, then the compact was broken and the exposed inner faces scanned", method="xrd")
f("s10.p1", "observation", "XRD patterns of inner and outer surfaces did not differ significantly", method="xrd")
f("s10.p1;fig5;fig5.cap;s14.p4", "setting", "reference patterns: ICDD PDF cards #04-002-5941 (Al2O3, corundum), #04-001-7297 (ZnO, zincite) and #00-004-0831 (Zn), drawn as sticks under the measured patterns",
  method="xrd", mentions="ICDD PDF #04-002-5941;#04-001-7297;#00-004-0831")
f("s10.p1;tabII.cap;s14.p9", "setting", "phase fractions and grain sizes by Rietveld refinement plus Halder-Wagner analysis of crystallite size, in JADE 9 (MDI)", method="xrd")
f("s10.p1", "setting", "whole-pattern fits were repeated until the residual became stable at 15% (within one percentage point) for all three samples",
  quantity="other", label_as_printed="residual", value="15", unit="%", data_kind="fit", method="xrd")
f("s10.p1", "observation", "corundum grain size 90-100 nm, agreeing with the BET-based d_NP = 100 nm",
  quantity="crystallite_size", qualifiers="species=Al2O3", label_as_printed="corundum grain size", value_min="90", value_max="100", unit="nm", data_kind="fit", method="xrd")
f("s10.p2;tabII.cap;s14.p9", "setting", "for resistivity, top and bottom faces got blanket e-beam evaporated films at 10^-6 Torr, nominally 20 nm Ti and 200 nm Au", method="electrical")
f("s10.p2", "setting", "prisms of about 6 × 3 × 1.6 mm were cut from the NPCs after metallization to avoid edge effects", method="electrical")
f("s10.p2;s13.p4;tabII.cap;s14.p9", "setting", "two-point resistivity through the sample thickness on a probe station, one probe on top and the other via the conductive stage", method="electrical")
f("s10.p2;tabII.cap;s14.p9", "setting", "resistance taken at 10 V and turned into volume resistivity with the metal film areas, which flaking during cutting reduced somewhat", method="electrical")
f("s10.p3", "setting", "SEM samples were sectioned, epoxy-mounted, ground, polished and given a conductive coating", method="sem", mentions="Note S2")
f("s10.p3", "setting", "SEM in a Quattro S ESEM (ThermoFisher) with an EDAX detector for EDS; collection and analysis in APEX software", method="sem_eds")
f("s10.p3", "setting", "EDS maps and line scans of the cross sections at 30 kV, 63 nA probe current, 50 µm aperture, working distance 10 mm, amp time 0.96 µS", method="sem_eds")
f("s10.p3;s10.p4", "setting", "EDS maps span the cross-section thickness, about 1.5 × 1 mm, with 200 µS dwell over 32 frames", method="sem_eds")
f("s10.p4", "setting", "EDS line scans with 100 points across the thickness near the centre line, 100 µm wide, 20 ms per point over 512 frames", method="sem_eds")
f("s10.p4", "setting", "backscattered-electron imaging was also done", method="sem")
f("s10.p5", "setting", "XPS on a Thermo Scientific Nexsa with monochromatic Al Kα (1486.7 eV), 125 µm spot and a flood gun for charge compensation",
  quantity="probe_resolution", value="125", unit="µm", data_kind="chosen input", method="xps")
f("s10.p5", "setting", "XPS spectra taken before etching with 1 keV monatomic Ar ions, then after 15 s and after 30 s of etch to strip adventitious carbon", method="xps")
f("s10.p5", "setting", "survey spectra: 1 eV step, 200 eV pass energy; high-resolution scans (Zn 2p, Al 2p, O 1s, C 1s): 0.1 eV step, 20 eV pass energy", method="xps")
f("s10.p5", "setting", "peak fits in Thermo Avantage with Gaussian-Lorentzian convolutions on Shirley backgrounds", method="xps")
f("s10.p5", "setting", "binding energies referenced to adventitious C 1s at 284.8 eV", method="xps")

# ---------------------------------------------------------------- III A. mass gain and pressure
f("s12.p1", "claim", "from earlier studies, the 32 min DEZ exposure at ~9 Torr should deposit Zn metal at T = 160 °C", mentions="ref. 11;ref. 12;T = 160 °C")
f("s12.p1", "claim", "at T = 120 °C the 48 min H2O purge should leave residual H2O that reacts with the next DEZ dose and adds ZnO", mentions="ref. 8;T = 120 °C")
f("s12.p1", "claim", "the cycled 120/160 °C process, built to avoid both side reactions, should give the smallest deposited mass, and the weighings confirm it", mentions="120/160 °C")
f("s12.p1", "setting", "two Al2O3 NPCs were coated in each run", method="gravimetry")
mg = {}
for r, lab, v, pm, extra in (("1", "120", "28.4", "0.1", ";s13.p3"), ("2", "160", "36.4", "1.6", ";s13.p3"), ("3", "120/160", "26.4", "0.1", ";s13.p3")):
    mg[lab] = f(f"s12.p1;tabI.r{r}c1;tabI.r{r}c0;tabI.r0c1;tabI.r0c0;tabI.cap;s13.p5{extra}", "observation",
                f"NPC mass gain {v} ± {pm}% for the {lab} °C run (± is sample-to-sample spread)",
                quantity="mass_gain", label_as_printed="Mass gain (%)", value=v, unit="%", data_kind="measured", method="gravimetry",
                mentions=f"{lab};{lab} °C")
f("s12.p1", "observation", "the text lists final porosities 36.7 ± 0.1%, 30.6 ± 1.4% and 38.0 ± 0.1% in the order 120/160, 120 and 160 °C, an order that differs from Table I",
  mentions="φ_f;120/160;120;160")
por = {}
for r, lab, v, pm in (("1", "120", "36.7", "0.1"), ("2", "160", "30.6", "1.4"), ("3", "120/160", "38.0", "0.1")):
    por[lab] = f(f"tabI.r{r}c2;tabI.r0c2;tabI.cap;s13.p5", "derived",
                 f"final porosity φ_f {v} ± {pm}% for the {lab} °C run, from the mass gain assuming uniform coating",
                 quantity="porosity", qualifiers="stage=final", label_as_printed="Final porosity, φ_f (%)", value=v, unit="%", data_kind="calculated",
                 method="calculation", mentions=lab, inputs=[mg[lab], phi_i])
f("s12.p1", "model", "porosity loss is turned into ZnO thickness as the mean of two geometries, spherical NPs and spherical pores, provisionally assuming uniform coating", mentions="ref. 4;Sec. III C")
gpc = {}
for r, lab, v, pm, ev in (("1", "120", "2.37", "0.02", ";s15.p3"), ("2", "160", "3.48", "0.26", ""),
                          ("3", "120/160", "2.14", "0.01", f";s15.p2;abs.g4;{A}")):
    gpc[lab] = f(f"s12.p1;tabI.r{r}c3;tabI.r0c3;tabI.cap;s13.p5{ev}", "derived",
                 f"average GPC {v} ± {pm} Å/cyc for the {lab} °C run, from the porosity drop" + (" (abstract: ~2.1 Å/cyc)" if lab == "120/160" else ""),
                 quantity="growth_per_cycle", value=v, unit="Å/cyc", data_kind="calculated", method="calculation",
                 mentions=f"{lab};{lab} °C" + (";T = 120 °C" if lab == "120" else ";T = 160 °C" if lab == "160" else ""), inputs=[por[lab]])
f("s12.p1", "claim", "2.14 Å/cyc is at the top of the range usually seen for conventional ZnO ALD on flat substrates", mentions="ref. 14;ref. 25")
f("s12.p2;fig2a;fig2b;fig2c;fig2.cap;s12.p12", "observation", "Fig. 2 plots p(t) for the first five cycles of each run; the other 15 cycles are in the supplement",
  mentions="Fig. 2;Fig. S2;Fig. S1;ref. 44")
f("s12.p2;fig2a;fig2b;fig2c", "observation", "p jumps sharply to ~9 Torr when a DEZ or H2O pulse admits reactant", method="process_monitor")
f("s12.p2;s12.p3;fig2a;fig2b;fig2c;s12.p6", "observation", "with the chamber isolated, p shows a net rise over a DEZ hold and a net fall over an H2O hold, partly from the half-reactions", method="process_monitor")
f("eq3;s12.p3", "model", "Eq. (3): overall reaction Zn(C2H5)2 + H2O gives ZnO + 2 C2H6")
f("eq4;s12.p4", "model", "Eq. (4): DEZ half-reaction, surface (OH)x plus Zn(C2H5)2 gives surface Ox-Zn(C2H5)2-x and x C2H6", mentions="ref. 10;ref. 27")
NK("s12.p5", "connective word between equations")
f("eq5;s12.p4", "model", "Eq. (5): H2O half-reaction, surface Ox-Zn(C2H5)2-x plus H2O gives surface OZn-(OH)x and (2-x) C2H6", mentions="ref. 10;ref. 27")
f("s12.p6;eq4;eq5", "definition", "|- marks a surface species; x may range from 0 to 2")
f("s12.p6", "cited", "x ~1 for ZnO ALD on silica powder at 80 °C",
  quantity="reaction_stoichiometry", label_as_printed="x", value="1", data_kind="literature", method="cited", mentions="ref. 10;80 °C")
f("s12.p6", "cited", "x = 1.37 for ZnO ALD on a QCM at 177 °C",
  quantity="reaction_stoichiometry", label_as_printed="x", value="1.37", data_kind="literature", method="cited", mentions="ref. 28;177 °C")
f("s12.p6", "cited", "x ~1.4-1.6 for ZnO ALD on a QCM between 80 and 250 °C",
  quantity="reaction_stoichiometry", label_as_printed="x", value_min="1.4", value_max="1.6", data_kind="literature", method="cited", mentions="ref. 27;80-250 °C")
f("s12.p6;fig2a;fig2b;fig2c", "claim", "the pressure traces imply x > 1 here: p rises in the DEZ half-reaction (more C2H6 out than reactant used) and falls in the H2O half-reaction",
  quantity="reaction_stoichiometry", label_as_printed="x", value="1", censor=">", data_kind="calculated", method="process_monitor", mentions="Fig. 2;Eq. (4);Eq. (5)")
f("s12.p6", "claim", "the analysis uses the DEZ step because H2O likely adsorbs in multilayers, especially on non-sample surfaces at ~90 °C or colder, blurring the pressure change", mentions="Sec. II B")
f("s12.x1;fig3a;fig3.cap;s12.p16", "observation", "Fig. 3(a): δp, the pressure minus its value at the start of the hold (~9 Torr), versus elapsed time δt (min) in the cycle 15 DEZ hold, one curve per run",
  method="process_monitor", mentions="cycle 15;Fig. 3(a);Note S3;ref. 44")
f("s12.x1", "model", "the δp change in a DEZ hold is taken to come from the Eq. (4) half-reaction plus a net leak out of the chamber")
f("s12.x1", "observation", "leak tests showed the main leak usually runs across the pump valve that isolates the chamber in holds")
f("s12.x1;fig3a", "observation", "120/160 °C, cycle 15: δp climbs for the first ~10 min of the DEZ hold",
  quantity="time_to_maximum", label_as_printed="time to δp maximum", value="10", unit="min", data_kind="measured", method="process_monitor", mentions="120/160 °C;cycle 15")
f("s12.x1;fig3a", "observation", "120/160 °C, cycle 15: δp levels off at ~450 mTorr",
  quantity="pressure_rise", qualifiers="level=maximum", label_as_printed="δp maximum", value="450", unit="mTorr", data_kind="measured", method="process_monitor", mentions="120/160 °C;cycle 15")
f("s12.x1;fig3a", "observation", "120/160 °C, cycle 15: δp then falls slowly, at ~2 mTorr/min on average over the last ~10 min (terminal slope ~-2)",
  quantity="pressure_rate", label_as_printed="TS", value="-2", unit="mTorr/min", data_kind="measured", method="process_monitor", mentions="120/160 °C;cycle 15")
f("s12.x1;fig3a", "claim", "the slope turning from positive to negative is read as a change from reaction-dominated to leak-dominated pressure")
f("s12.x1", "setting", "recorded pressure data have 10 mTorr resolution, which limits the slope analysis",
  quantity="other", label_as_printed="pressure resolution", value="10", unit="mTorr", data_kind="measured", method="process_monitor", mentions="Note S3")
f("s12.x1;fig3a", "claim", "whether diffusion-reaction saturated cannot be told from δp(δt), given unequal DEZ and C2H6 leak rates and varying valve seating, but gas generation clearly slows")
f("s12.x1;fig3a", "observation", "T = 120 °C, cycle 15: δp peaks later, after ~15 min versus 10 min for 120/160",
  quantity="time_to_maximum", label_as_printed="time to δp maximum", value="15", unit="min", data_kind="measured", method="process_monitor", mentions="T = 120 °C;cycle 15")
f("s12.x1;fig3a", "observation", "T = 120 °C, cycle 15: δp maximum ~500 mTorr versus 450 mTorr for 120/160",
  quantity="pressure_rise", qualifiers="level=maximum", label_as_printed="δp maximum", value="500", unit="mTorr", data_kind="measured", method="process_monitor", mentions="T = 120 °C;cycle 15")
f("s12.x1;fig3a", "observation", "T = 120 °C, cycle 15: terminal slope (mean over the last 10 min) about -1 versus -2 mTorr/min for 120/160",
  quantity="pressure_rate", label_as_printed="TS", value="-1", unit="mTorr/min", data_kind="measured", method="process_monitor", mentions="T = 120 °C;cycle 15")
f("s12.x1;s12.p7;fig3a", "observation", "T = 160 °C, cycle 15: δp keeps rising for the whole hold, with terminal slope ~80 mTorr/min",
  quantity="pressure_rate", label_as_printed="TS", value="80", unit="mTorr/min", data_kind="measured", method="process_monitor", mentions="T = 160 °C;cycle 15")
f("s12.p7;fig3a", "observation", "T = 160 °C, cycle 15: δp reaches ~2.7 Torr before the pump step",
  quantity="pressure_rise", label_as_printed="δp", value="2.7", unit="Torr", data_kind="measured", method="process_monitor", mentions="T = 160 °C;cycle 15")
f("fig3a;fig3.cap;s12.p16", "setting", "pressure gauges behind the 160 °C δp curve", quantity="other", label_as_printed="gauge",
  value_text="1000 Torr gauge for the noisier part, 10 Torr gauge for the rest", method="process_monitor", mentions="T = 160 °C")
f("fig3a", "observation", "Fig. 3(a) marks Δp as the net rise at the end of each hold, labels the terminal slope, and shades the early 120/160 curve as 'Reaction' leading to 'Saturation?'")
f("s12.p7", "claim", "higher δp maxima at 120 and 160 °C fit more deposition than in the 120/160 °C process")
f("s12.p7", "claim", "the higher terminal slopes suggest gas-producing processes still running at the end of the DEZ hold, slight at 120 °C and strong at 160 °C, and absent or weaker for 120/160 °C")
f("s12.p8;fig3b;fig3c;fig3.cap;s12.p16", "observation", "Fig. 3(b) and 3(c) compare gas generation of the three runs over all 20 cycles", mentions="Fig. 3(b);Fig. 3(c)")
f("s12.p8;fig3b;fig3.cap;s12.p16;tabI.cap;s13.p5", "model", "Δn_g, the net gas mole change from the DEZ half-reaction, comes from Δp after correcting for the stop-valve leak and for reaction during the pulse",
  method="process_monitor", mentions="Note S3")
f("s12.p8", "model", "the first five cycles are set aside as complicated by ZnO nucleation and the switch from Al2O3 to ZnO growth surfaces")
f("s12.p8;fig3b;fig3c", "observation", "over cycles 6 to 20, Δn_g and TS rank 120/160 °C lowest, T = 120 °C a little above it, and T = 160 °C far above both",
  method="process_monitor", mentions="cycles 6 through 20;120/160 °C;T = 120 °C;T = 160 °C")
f("s12.p8;fig3b", "claim", "the early rise of Δn_g is tentatively put down to thicker effective growth per cycle in early cycles, and the later fall to shrinking NPC surface area", mentions="ref. 27")
f("s12.p8;fig3c", "claim", "TS follows Δn_g because the gas generation rate in the last 10 min tracks the total gas generated")
f("fig3b;fig3.cap;s12.p16", "observation", "Fig. 3(b): net gain of gas moles Δn_g (µmol) per DEZ hold versus cycle number 1-20, one marker series per run", method="process_monitor")
f("fig3b", "observation", "160 °C series (red up-triangles) in Fig. 3(b): rises steeply from cycle 4, peaks near cycle 10 well above the others, then declines", mentions="160 °C")
f("fig3b", "observation", "120 °C series (blue down-triangles) in Fig. 3(b): stays low, a little above the 120/160 series in most cycles", mentions="120 °C")
f("fig3b", "observation", "120/160 °C series (green diamonds) in Fig. 3(b): the lowest series, slowly falling after cycle 6", mentions="120/160 °C")
f("fig3c;fig3.cap;s12.p16", "observation", "Fig. 3(c): terminal slope TS (mTorr/min), average slope of pressure in the final 10 min of the DEZ hold, versus cycle number", method="process_monitor")
f("fig3c", "observation", "160 °C series in Fig. 3(c): TS climbs from near zero to a maximum around cycle 10 and then decreases", mentions="160 °C")
f("fig3c", "observation", "120 °C and 120/160 °C series in Fig. 3(c): TS stays close to zero or slightly negative through all cycles", mentions="120 °C;120/160 °C")
f("s12.p9;tabI.r0c5", "definition", "Δn_g with an overbar: Δn_g averaged over cycles, in µmol/cyc", mentions="Table I")
f("s12.p9;tabI.r0c4;tabI.cap;s13.p5", "model", "assuming only ZnO is deposited, the GPC is converted into the cycle-averaged moles of solid Δn_s (µmol/cyc)")
f("s12.p9;eq6", "definition", "ȳ: moles of gas gained per mole of solid gained, introduced to compare the runs")
f("eq6;s12.p9;tabI.r0c6", "model", "Eq. (6): ȳ = 1 + Δn_g/Δn_s (cycle averages)")
f("eq7;s12.p10", "model", "Eq. (7): if Eqs. (4) and (5) alone govern growth, ȳ = 1 + (x̄ - 1) Δn_DEZ / Δn_DEZ = x̄, the mean of x over the 20 cycles")
f("eq8;s12.p11;s12.p13", "model", "Eq. (8): if other reactions also deposit material, ȳ = x̄ + c with c a correction from those reactions")
dns, dng = {}, {}
for r, lab, s, g in (("1", "120", "150", "59.3"), ("2", "160", "217", "191"), ("3", "120/160", "139", "50.8")):
    dns[lab] = f(f"tabI.r{r}c4;tabI.r0c4", "derived", f"Δn_s = {s} µmol/cyc for the {lab} °C run, from the GPC with the solid taken as ZnO",
                 quantity="deposited_moles_per_cycle", label_as_printed="Δn_s", value=s, unit="µmol/cyc", data_kind="calculated", method="calculation", mentions=lab, inputs=[gpc[lab]])
    dng[lab] = f(f"tabI.r{r}c5;tabI.r0c5", "derived", f"Δn_g = {g} µmol/cyc for the {lab} °C run, averaged over cycles from the DEZ-hold pressure data",
                 quantity="gas_moles_per_cycle", label_as_printed="Δn_g", value=g, unit="µmol/cyc", data_kind="calculated", method="process_monitor", mentions=lab)
f("tabI.cap;s13.p5", "definition", "Table I: GPC ± is the spread within each run's NPC pair; Δn_s and Δn_g are totals for the pair, with ~±0.1 measurement uncertainty, giving ~±0.001 on ȳ", mentions="Note S3;ref. 44")
for r, lab, v, tlab in (("1", "120", "1.395", "T = 120 °C"), ("2", "160", "1.880", "T = 160 °C"), ("3", "120/160", "1.365", "T cycled between 120 and 160 °C")):
    f(f"s12.p14;tabI.r{r}c6;tabI.r0c6;s12.p15;tabI.cap;s13.p5", "derived", f"ȳ = {v} (±0.001) for the {lab} °C run, from Eq. (6)",
      quantity="reaction_stoichiometry", label_as_printed="ȳ (printed ν̄ in the text layer)", value=v, data_kind="calculated", method="calculation",
      mentions=f"{lab};{tlab}", inputs=[dng[lab], dns[lab]])
f("s12.p15;s12.p17", "claim", "for 120 and 120/160 °C, where pure ZnO is not in doubt, ȳ measures ethane produced in the DEZ exposure by hydrogenation of the ethyl ligands", mentions="120;120/160 °C")
f("s12.p17", "claim", "the slightly higher ȳ at T = 120 °C fits more residual H2O, which could raise c (reacting with DEZ or MEZ) and/or x̄ (helping DEZ adsorb and react with OH)", mentions="ref. 25;ref. 26;T = 120 °C")
f("s12.p17", "claim", "a higher density of chemisorbed OH, a plausible result of a cooler purge, could also explain the higher ȳ", mentions="ref. 29")
f("s12.p17", "claim", "the 120 versus 120/160 °C difference in ȳ is small and cannot separate H2O from OH effects, so it needs caution")
f("s12.p17", "claim", "the much larger ȳ at T = 160 °C fits a coating that holds metallic Zn rather than pure ZnO", mentions="T = 160 °C")
f("s12.p17", "claim", "if Zn deposition also yields C2H6 (2 mol per mol of DEZ), it raises c, and the pure-ZnO molar mass leads to underestimating Δn_s", mentions="ref. 25;ref. 26;Eq. (4)")

# ---------------------------------------------------------------- Fig. 1 and Fig. 2 panels
f("fig1a;fig1.cap;s9.p2", "definition", "Fig. 1(a) sketches an Al2O3 NP compact in the quartz boat: Zn(C2H5)2 or H2O diffuse in, C2H6 leaves, and T is marked at the boat bottom", method="schematic")
f("fig1a;fig4a", "observation", "NPC diameter drawn and photographed as ~11.4 mm",
  quantity="other", label_as_printed="diameter", value="11.4", unit="mm", data_kind="measured", method="schematic", mentions="~11.4 mm")
f("fig1a", "observation", "the schematic labels the compact thickness 2L ≈ 1.6 mm",
  quantity="other", label_as_printed="2L", value="1.6", unit="mm", data_kind="measured", method="schematic")
f("fig1a;fig1.cap;s9.p2", "observation", "the schematic labels the initial porosity φ_i ≈ 51%",
  quantity="porosity", qualifiers="stage=initial", label_as_printed="φ_i", value="51", unit="%", data_kind="measured", method="schematic")
f("fig1b;fig1.cap;s9.p2", "definition", "Fig. 1(b) tabulates which steps run at 120 °C and which at 160 °C in the three schedules; a 'dose' means the pulse step plus the hold step", method="schematic",
  mentions='"120 °C";"160 °C";"120/160 °C"')
f("fig1b", "setting", 'the "120/160 °C" schedule as drawn in Fig. 1(b)', quantity="deposition_temperature",
  value_text="120 °C for the DEZ dose, DEZ purge and H2O dose, 160 °C for the H2O purge", method="schematic", mentions='"120/160 °C"')
# the per-step temperature schedule of Fig. 1(b) (the text: s9.p6, and s6.p8 for the cycled run), one fact per run and step; a dose is
# the pulse plus the hold, so step=reactant_A / reactant_B. The cycled run's DEZ dose is s9.p6#6 (step=reactant_A) and its H2O purge
# s9.p6#7 (step=purge_B); SCHED keeps the ids for the stage-3 parents
STEPS = (("reactant_A", "DEZ dose", "the DEZ dose (pulse and hold)"), ("purge_A", "DEZ purge", "the DEZ purge"),
         ("reactant_B", "H2O dose", "the H2O dose (pulse and hold)"), ("purge_B", "H2O purge", "the H2O purge"))
SCHED = {"120": [], "160": [], "120/160": []}
for lab in ("120", "160"):
    for step, printed, what in STEPS:
        SCHED[lab].append(f("fig1b;s9.p6", "setting", f'Fig. 1(b), "{lab} °C" schedule: {what} runs at T = {lab} °C',
                            quantity="deposition_temperature", qualifiers=f"step={step}", value=lab, unit="°C", data_kind="chosen input",
                            method="schematic", mentions=f'"{lab} °C";{printed}'))
for step, printed, what in STEPS[1:3]:
    SCHED["120/160"].append(f("fig1b;s9.p6;s6.p8", "setting", f'Fig. 1(b), "120/160 °C" schedule: {what} runs at T = 120 °C, like every step but the H2O purge',
                              quantity="deposition_temperature", qualifiers=f"step={step}", value="120", unit="°C", data_kind="chosen input",
                              method="schematic", mentions=f'"120/160 °C";{printed}'))
f("fig2a;fig2b;fig2c;fig2.cap;s12.p12", "observation", "the ~1 Torr spikes and dips in purges come from periodic pressure drops in the N2 feed line when the attached glovebox draws N2",
  method="process_monitor")
f("fig2a;fig2.cap;s12.p12", "observation", "Fig. 2(a), T held at 120 °C: p (Torr) versus time (hr) for the initial H2O half-cycle and cycles 1-5, with pulse and hold steps marked",
  method="process_monitor", mentions="120 °C;Cyc 1-5")
f("fig2a", "observation", "in Fig. 2(a) the DEZ holds stay nearly flat at the top of the scale while the H2O holds drop after the pulse", mentions="120 °C")
f("fig2b;fig2.cap;s12.p12", "observation", "Fig. 2(b), T held at 160 °C: p versus time for the first five cycles", method="process_monitor", mentions="160 °C")
f("fig2b", "observation", "in Fig. 2(b) the DEZ-hold pressure climbs during the hold, more steeply in later cycles, and runs off the top of the axis in cycle 5", mentions="160 °C;Cyc 5")
f("fig2c;fig2.cap;s12.p12", "observation", "Fig. 2(c), T cycled between 120 and 160 °C: p versus time for the first five cycles, each pulse labelled DEZ or H2O", method="process_monitor", mentions="120/160 °C")
f("fig2d;fig2.cap;s12.p12", "observation", "Fig. 2(d): inner quartz-boat surface temperature T (°C) over time in a test run with the same conditions as (c)", method="process_monitor", mentions="120/160 °C")
f("fig2d;s15.p4", "observation", "in Fig. 2(d) the boat sits just below 120 °C for most steps and climbs to just below 160 °C during each H2O purge before falling back", method="process_monitor")

# ---------------------------------------------------------------- III B. colour, XRD, resistivity
f("s13.p1;fig4a;fig4b;fig4c;fig4d;fig4.cap;s14.p3", "observation", "Fig. 4 shows photographs of Al2O3 NPC top faces before and after ZnO ALD", method="photograph")
f("fig4a;fig4.cap;s14.p3", "observation", "Fig. 4(a): uncoated NPC before ALD, white", method="photograph", mentions="Before ALD")
f("s13.p1;fig4b;fig4.cap;s14.p3", "observation", "T = 120 °C: ZnO ALD turns both the surface and the interior of the white NPC slightly yellow; cracks are visible on the photographed face",
  method="photograph", mentions="T = 120 °C;120 °C")
f("s13.p1", "cited", "yellowing is expected for oxygen-deficient ZnO1−x, and oxygen vacancies have been linked to n-type conduction in ALD ZnO", mentions="ref. 30;ref. 31;ref. 32-35")
f("s13.p1;fig4c;fig4.cap;s14.p3", "observation", "T = 160 °C: surface and interior of the NPC turn charcoal gray", method="photograph", mentions="T = 160 °C;160 °C")
f("s13.p1;fig4d;fig4.cap;s14.p3", "observation", "T cycled 120/160 °C: the top surface is light gray while the interior has about the colour of the 120 °C sample", method="photograph",
  mentions="T cycled between 120 and 160 °C;120/160 °C")
f("s13.p2;fig5;fig5.cap;s14.p4", "observation", "XRD of the NPC top surfaces confirms the phases expected from each run", method="xrd", qualifiers="position=top", mentions="Fig. 5")
f("fig5;fig5.cap;s14.p4", "observation", "Fig. 5: normalized counts versus 2θ (deg.) from 20 to 80 for the coated NPCs, patterns stacked with reference sticks below", method="xrd")
f("fig5;fig5.cap;s14.p4", "observation", "Fig. 5 top (blue) pattern: T held at 120 °C", method="xrd", mentions="120 °C")
f("fig5;fig5.cap;s14.p4", "observation", "Fig. 5 middle (red) pattern: T held at 160 °C, showing extra peaks at Zn positions", method="xrd", mentions="160 °C")
f("fig5;fig5.cap;s14.p4", "observation", "Fig. 5 bottom (green) pattern: T cycled between 120 and 160 °C", method="xrd", mentions="120/160 °C")
f("s13.p2;fig5", "observation", "all three samples show narrow corundum peaks and broad zincite peaks, as large Al2O3 NPs under thin ZnO coatings should", method="xrd")
f("s13.p2;fig5;s13.p3", "observation", "the T = 160 °C sample shows clear metallic Zn peaks", quantity="phase", qualifiers="species=Zn", value_text="detected",
  data_kind="measured", method="xrd", mentions="T = 160 °C")
for r, lab, v, pm, ev in (("1", "120", "23.3", "0.2", ";s13.p3;s13.p2"), ("2", "160", "17.1", "0.2", ""), ("3", "120/160", "17.7", "0.1", ";s13.p3;s13.p2")):
    f(f"tabII.r{r}c1;tabII.r0c1;tabII.r{r}c0;tabII.r0c0;tabII.cap;s14.p9{ev}", "derived", f"zincite (ZnO) weight percent {v} ± {pm} for the {lab} °C sample, from Rietveld refinement",
      quantity="composition", qualifiers="species=ZnO", label_as_printed="ZnO (zincite) Wt. %", value=v, unit="wt%", data_kind="fit", method="xrd", mentions=lab)
for r, lab, v, pm, ev in (("1", "120", "6.0", "1.1", ";s13.p3"), ("2", "160", "6.0", "1.5", ""), ("3", "120/160", "5.1", "1.1", ";s13.p3")):
    f(f"tabII.r{r}c2;tabII.r0c2;tabII.cap;s14.p9{ev}", "derived", f"zincite crystallite size {v} ± {pm} nm for the {lab} °C sample, Halder-Wagner analysis",
      quantity="crystallite_size", qualifiers="species=ZnO", label_as_printed="ZnO (zincite) Crystallite size (nm)", value=v, unit="nm", data_kind="fit", method="xrd", mentions=lab)
for r, lab in (("1", "120"), ("3", "120/160")):
    f(f"tabII.r{r}c3;tabII.r{r}c4;tabII.r0c3;tabII.r0c4;tabII.cap", "observation", f"no metallic Zn detected by XRD in the {lab} °C sample, so no Zn crystallite size is given",
      quantity="phase", qualifiers="species=Zn", label_as_printed="Zn (metallic) Wt. %", value_text="not detected", data_kind="measured", method="xrd", mentions=f"{lab};Not detected")
f("tabII.r2c3;tabII.r0c3;tabII.cap", "derived", "metallic Zn weight percent 12.5 ± 0.7 in the 160 °C sample",
  quantity="composition", qualifiers="species=Zn", label_as_printed="Zn (metallic) Wt. %", value="12.5", unit="wt%", data_kind="fit", method="xrd", mentions="160")
f("tabII.r2c4;tabII.r0c4;tabII.cap", "derived", "metallic Zn crystallite size 57 ± 42 nm in the 160 °C sample",
  quantity="crystallite_size", qualifiers="species=Zn", label_as_printed="Zn (metallic) Crystallite size (nm)", value="57", unit="nm", data_kind="fit", method="xrd", mentions="160")
f("tabII.cap;s14.p9", "definition", "Table II: ± on wt.% and crystallite size are pattern-fit errors; ± on ρ comes from the uncertain Ti-Au electrode areas after flaking")
th120 = f("s13.p3", "derived", "coating thickness 4.73 ± 0.03 nm for T = 120 °C, inferred from the mass gain",
          quantity="film_thickness", value="4.73", unit="nm", data_kind="calculated", method="calculation", mentions="T = 120 °C", inputs=[mg["120"]])
th12 = f("s13.p3", "derived", "coating thickness 4.28 ± 0.03 nm for T cycled 120/160 °C, inferred from the mass gain",
         quantity="film_thickness", value="4.28", unit="nm", data_kind="calculated", method="calculation", mentions="T cycled between 120 and 160 °C", inputs=[mg["120/160"]])
f("s13.p3", "claim", "for 120 and 120/160 °C the zincite weight and crystallite size track the coating weight and thickness from mass gain")
f("s13.p3", "claim", "zincite weight below coating weight implies a large amorphous share of the coating, not surprising for a very thin film unmatched to the substrate lattice")
f("s13.p3", "claim", "at T = 160 °C zincite weight and size are not larger despite 36.4 ± 1.6% coating weight, so the extra mass is mostly metallic Zn, matching the dark colour", mentions="T = 160 °C")
f("s13.p3", "claim", "the light gray top face of the 120/160 °C sample is still unexplained, although XPS was run on all three samples", mentions="Fig. S3;Fig. S4;120/160 °C")
for r, lab, v, txt, ev in (("1", "120", "1.3e7", "1.3 ± 0.2 × 10^7 (text: ~1 × 10^7)", ""), ("2", "160", "8.3e3", "8.3 ± 1.0 × 10^3 (text: ~8 × 10^3)", ""),
                           ("3", "120/160", "1.2e7", "1.2 ± 0.1 × 10^7 (text: ~1 × 10^7)", "")):
    f(f"s13.p4;tabII.r{r}c5;tabII.r0c5;tabII.r{r}c0;tabII.cap;s14.p9", "observation", f"through-thickness resistivity ρ = {txt} Ω-cm for the {lab} °C NPC",
      quantity="resistivity", value=v, unit="Ω-cm", data_kind="measured", method="electrical", mentions=f"{lab};{lab} °C")
f("s13.p4", "claim", "the low resistivity of the 160 °C sample fits metallic Zn in it; the gap of more than three orders of magnitude to the other two is significant", mentions="160 °C")
f("s13.p4", "setting", "only one NPC per ALD condition was measured for resistivity", method="electrical")
f("s13.p4", "claim", "the near-identical 120 and 120/160 °C resistivities need caution, as resistivity likely varies with cracking, adventitious carbon and other sample details", mentions="120;120/160 °C")
f("s13.p4", "cited", "ALD ZnO films used for electrical measurements are typically of order 100 nm thick",
  quantity="film_thickness", value="100", unit="nm", data_kind="literature", method="cited", mentions="ref. 13;ref. 14")
f("s13.p4", "cited", "such ALD ZnO films typically have resistivity of order 10^-2 Ω-cm",
  quantity="resistivity", value="1e-2", unit="Ω-cm", data_kind="literature", method="cited", mentions="ref. 13;ref. 14")
f("s13.p4;s15.p2", "claim", "the NPC resistivity is high because the ZnO is very thin with crystallites smaller than the electron mean free path, likely largely amorphous, tortuous and of low volume fraction",
  mentions="ref. 36;ref. 37;ref. 38")
f("s13.p4", "observation", "vertical current of ~300 nA or more at 10 V, about six orders of magnitude above the noise floor",
  quantity="other", label_as_printed="vertical current", value="300", censor=">", unit="nA", data_kind="measured", method="electrical")
f("s13.p4;s15.p2", "claim", "the measurable vertical current shows the ALD coatings form percolating networks across the NPC thickness, allowing conduction from top to bottom face")

# ---------------------------------------------------------------- III C. EDS
f("s14.p1;fig6a;fig6b;fig6c;fig6d;fig6e;fig6f;fig6.cap;s15.p6", "observation", "cross-sectional SEM-EDS maps and line scans show the ALD coatings reach through the full NPC thickness", method="sem_eds")
f("s14.p1;fig6d;fig6e;fig6f", "definition", "in Figs. 6(d)-6(f) each Kα count is normalized to the counts summed over all elements and positions", method="sem_eds")
f("s14.p1;fig6a;fig6b;fig6c;fig6d;fig6e;fig6f", "observation", "the Al2O3 density varies a little, with a denser ~0.3-0.5 mm band near the bottom of each cross section, likely from uneven powder packing before pressing",
  quantity="other", label_as_printed="denser band width", value_min="0.3", value_max="0.5", unit="mm", data_kind="measured", method="sem_eds", mentions="Fig. S5")
f(f"s14.p1;fig6d;fig6f;s14.p2;s15.p2;abs.g4;{A}", "observation", "for T = 120 °C and 120/160 °C the normalized Zn Kα signal is about constant through the thickness apart from the outer ~0.2 mm at each face",
  quantity="other", label_as_printed="near-surface depletion depth", value="0.2", unit="mm", data_kind="measured", method="sem_eds", mentions="T = 120 °C;T cycled between 120 and 160 °C")
f("s14.p1", "observation", "the 120 °C sample has 12% more normalized Zn Kα counts than the 120/160 °C sample, in line with its 10% higher fractional mass gain",
  quantity="other", label_as_printed="Zn Kα counts relative to the 120/160 °C section", value="12", unit="%", data_kind="measured", method="sem_eds",
  mentions="120 °C;120/160 °C")
f("s14.p2", "observation", "XPS of top and interior surfaces shows the weaker Zn Kα signal within ~0.2 mm of the faces reflects real thinning of the ZnO", method="xps", mentions="Fig. S3;Fig. S4")
f(f"s14.p2;s14.p6;abs.g4;{A};s15.p2", "claim", "the near-face ZnO depletion may come from Zn-containing species desorbing during the long DEZ purges, as Ti species desorb in TiO2 ALD from TiCl4/H2O at high temperature",
  mentions="ref. 39")
f("s14.p6", "claim", "marked desorption is not usually seen in ZnO ALD at moderate temperatures, but the 48 min DEZ purge used here is unusually long")
f("s14.p6", "claim", "the strong curvature of a ZnO coating inside 100 nm pores might promote desorption, e.g. by raising the DEZ-OH reaction barrier so that some Zn stays as weakly bound unreacted DEZ instead of MEZ",
  mentions="ref. 25")
f(f"s14.p7;fig6e;abs.g4;{A}", "observation", "for T = 160 °C the Zn concentration drops noticeably toward the middle of the sample, as expected for non-self-limiting Zn growth where the time-averaged DEZ pressure is lower",
  method="sem_eds", mentions="T = 160 °C")
f("s14.p7", "claim", "a slightly slower reaction-diffusion with ~10% fewer DEZ moles at 160 °C (same pulse pressure, hotter gas) could add to the Zn gradient", mentions="T = 160 °C;T = 120 °C")
f("s14.p7;fig6e", "claim", "the outsized Al Kα rise where Zn Kα falls likely comes from normalization and reabsorption, since the Zn L edge (~1.2 keV) sits just under the Al K edge (~1.6 keV)")
f("s14.p8;s14.p10", "claim", "apart from near-face depletion, the even ZnO in both the 120 °C and 120/160 °C samples is consistent with a saturated self-limiting reaction-diffusion process", mentions="120;120/160 °C")
f("s14.p10", "claim", "this is expected for the cycled process but not obviously for T = 120 °C, given its higher GPC, Δn_g, terminal slope and ȳ", mentions="Sec. III A;T = 120 °C")
f("s14.p10", "claim", "with incomplete H2O removal, H2O likely still desorbs when DEZ arrives, so part of the extra growth may be gas-phase, CVD-like")
f("s14.p10", "cited", "in attempts to fully infill NP thin films, CVD from residual H2O caused pore clogging and left porosity", mentions="ref. 8")
f("s14.p10", "derived", "the excess deposition at T = 120 °C is 0.4-0.5 nm, small next to the ~100 nm pores, so uniform infiltration may survive far from complete infilling",
  quantity="other", label_as_printed="excess deposition", value_min="0.4", value_max="0.5", unit="nm", data_kind="calculated", method="calculation", mentions="T = 120 °C", inputs=[th120, th12])
f("s14.p10", "claim", "if the excess comes from higher OH density instead, uniformity may simply reflect no CVD, the extra growth being surface reactions")
f("s14.p10", "model", "assumption: on a 10^3 s scale OH desorption self-limits at a final OH density that falls with temperature, so a cooler purge mainly leaves more surface OH rather than more H2O vapour", mentions="ref. 40")
f("s14.p10", "cited", "the change of ZnO OH coverage between 120 and 160 °C may often be too small to account for a 10% GPC difference", mentions="ref. 23;ref. 41")
f("s14.p10", "claim", "desorption from strongly curved surfaces in very long purges may be atypical, and OH coverage differences between runs cannot be excluded without more in situ or ex situ work")

# ---------------------------------------------------------------- Fig. 6 panels
for p, lab, extra in (("a", "120 °C", ""), ("b", "160 °C", "; the top of this cross section is missing (damage in transport and handling)"),
                      ("c", "120/160 °C", "")):
    f(f"fig6{p};fig6.cap;s15.p6", "observation", f"Fig. 6({p}), {lab}: SE image, Al map and Zn map of the NPC cross section side by side, 0.5 mm scale bar{extra}",
      method="sem_eds", mentions=lab)
f("fig6a;fig6c", "observation", "for 120 and 120/160 °C the Al and Zn maps look even over the whole section height", method="sem_eds", mentions="120 °C;120/160 °C")
f("fig6d;fig6e;fig6f;fig6.cap;s15.p6", "observation", "Figs. 6(d)-(f): Al, Zn, O and C Kα line scans, normalized X-ray counts (0-10) against position (mm, 0-1.5), roughly aligned with the images in (a)-(c)",
  method="sem_eds")
SER = {"d": "Zn K-alpha, T held at 120 C", "e": "Zn K-alpha, T held at 160 C (section incomplete above 0.42 mm)", "f": "Zn K-alpha, T cycled 120/160 C"}
LAB = {"d": "120 °C", "e": "160 °C", "f": "120/160 °C"}
for p in "def":
    s = cases_points(PID, "6", p, SER[p])
    ref = P(PID, f"fig6{p}_zn", s["points"], source=f"points.json: figure 6 panel {p}, series '{SER[p]}' ({s['source']})",
            x_label=s["x_label_as_printed"], y_label=s["y_label_as_printed"], note="points are [x, y] = [normalized counts, position mm] (axes swapped); " + s["quality"])
    f(f"fig6{p};fig6.cap;s15.p6", "observation", f"Fig. 6({p}) Zn Kα line scan of the {LAB[p]} sample: normalized counts against position through the thickness",
      quantity="signal_intensity", qualifiers="element=Zn", label_as_printed="Normalized X-ray counts (Zn)", points_ref=ref, data_kind="measured", method="sem_eds", mentions=LAB[p])
for p in "def":
    f(f"fig6{p}", "observation", f"Fig. 6({p}), {LAB[p]}: the Al Kα trace is the highest-count curve and the noisiest, roughly flat across the section",
      quantity="signal_intensity", qualifiers="element=Al", method="sem_eds", mentions=LAB[p])
    f(f"fig6{p}", "observation", f"Fig. 6({p}), {LAB[p]}: the O and C Kα traces lie low and flat, C below O",
      quantity="signal_intensity", method="sem_eds", mentions=LAB[p])
f("fig6e", "observation", "Fig. 6(e): the scan starts near 0.4 mm because the upper part of the 160 °C section is missing; the Zn trace bulges outward near the faces and dips at mid-depth", method="sem_eds", mentions="160 °C")

# ---------------------------------------------------------------- IV. conclusions
f("s15.p1;s15.p2", "claim", "a 20-cycle static-dose DEZ/H2O process designed with a simplified 1D reaction-diffusion model coats the pores of macroscopic Al2O3 NPCs conformally with ZnO")
f("s15.p2", "claim", "the resistivity is well above that of typical ALD ZnO films")
f("s15.p2", "claim", "resistivity could likely be cut a lot by thicker ZnO, or better crystallinity from post-ALD annealing or a hotter H2O purge", mentions="ref. 4")
f("s15.p3;abs.g4;s5.p1;s13.p2", "claim", "holding T at 160 °C throughout gives metallic Zn along with the ZnO", mentions="T = 160 °C")
f("s15.p3", "claim", "holding T at 120 °C gives a pure, uniform ZnO coating (same near-face exception) with resistivity like the cycled process", mentions="T = 120 °C")
f("s15.p3", "claim", "at 120 °C the chamber pressure suggests the DEZ half-reaction saturates more slowly and makes slightly more ethane per Zn deposited", mentions="120 °C")
f("s15.p3", "claim", "these 120 °C results fit the expectation that a 48 min H2O purge at only 120 °C leaves residual H2O that reacts with the next DEZ dose")
f("s15.p3", "claim", "more experiments are needed to tell gas-phase DEZ-H2O (CVD) reactions from surface DEZ-OH reactions as the cause of the high GPC at 120 °C", mentions="T = 120 °C")
f("s15.p4", "claim", "whether it lowers OH or H2O coverage, temperature cycling can control the ZnO ALD purge without causing metallic Zn")
f("s15.p4", "claim", "temperature cycling may shorten purges where residual H2O threatens uniform infiltration, e.g. for complete infilling or very low deposition temperature")
f("s15.p4", "claim", "other heating methods should be tried to reach practical purge times")
f("s15.p4;fig2d", "setting", "chamber heating raised T from 120 to 160 °C over a 33.5 min ramp",
  quantity="other", label_as_printed="temperature ramp time", value="33.5", unit="min", data_kind="measured", method="process_monitor")
f("s15.p4", "cited", "an ALD reactor with a flash lamp raised Si substrate temperature as much as ~400 °C in 5 s",
  quantity="other", label_as_printed="temperature rise", value="400", unit="°C", data_kind="literature", method="cited", mentions="ref. 42")
f("s15.p4;s15.p8", "cited", "a high-power resistive heater raised sapphire substrate temperature by up to ~800 °C within 15 s to crystallize films during ZnO ALD",
  quantity="other", label_as_printed="temperature rise", value_max="800", unit="°C", data_kind="literature", method="cited", mentions="ref. 43")
f("s15.p8", "claim", "uniform infiltration plus higher GPC at 120 °C suggest that a lower purge temperature can sometimes reduce the cycles, and so the time, needed for a target thickness", mentions="120 °C")
f("s15.p8", "claim", "the 120 °C results justify further study of how H2O purge time and temperature relate to coating thickness and infiltration uniformity", mentions="120 °C")

NK("s15.p9;s15.p10", "acknowledgement")
NK("s15.p11;s15.p12;s15.p14;s15.p17", "heading")
NK("s15.p13", "conflict statement")
NK("s15.p15;s15.p16", "author contributions")
NK("s15.p18", "data availability statement")

# ---------------------------------------------------------------- the film material and the test structure type (lists.MATERIALS, lists.STRUCTURES)
MAT = f("abs.g1;s9.p1", "setting", "film material", quantity="material", value_text="ZnO", data_kind="chosen input", mentions="ZnO")
STRUCT = f("abs.g1;s8.p1", "setting", "test structure type: pressed Al2O3 nanoparticle compacts", quantity="structure_type", value_text="porous",
           data_kind="chosen input", mentions="NPC")

# ---------------------------------------------------------------- the abscissa of the Fig. 6 line scans: the position through the compact (x= qualifier).
# The paper draws the position vertically and the points are kept as printed (counts, position); the scan's independent variable is the position.
for cf in C.facts():
    if cf["points_ref"] and "x=" not in cf["qualifiers"]:
        cf["qualifiers"] = ";".join(filter(None, [cf["qualifiers"], "x=distance"]))


# ---------------------------------------------------------------- the stance of every claim, from the paper's wording (lists.STANCES)
STANCE = {"abs.g1#1": "hedged", "abs.g1#2": "asserted", "abs.g2#2": "asserted", "abs.g4#1": "asserted", "abs.g4#2": "hedged", "s6.p1#1": "asserted",
          "s6.p1#2": "asserted", "s6.p3#1": "hedged", "s6.p6#1": "asserted", "s6.p6#4": "asserted", "s6.p8#1": "asserted", "s6.p8#2": "asserted",
          "s6.p8#6": "hedged", "s6.p8#9": "asserted", "s6.p8#12": "asserted", "s9.p3#4": "asserted", "s9.p6#12": "hedged", "s9.p6#13": "hedged",
          "s9.p7#1": "asserted", "s9.p9#7": "asserted", "s12.p1#1": "hedged", "s12.p1#2": "hedged", "s12.p1#3": "asserted", "s12.p1#13": "asserted",
          "s12.p6#5": "asserted", "s12.p6#6": "hedged", "s12.x1#7": "asserted", "s12.x1#9": "open", "s12.p7#2": "asserted", "s12.p7#3": "hedged",
          "s12.p8#5": "hedged", "s12.p8#6": "asserted", "s12.p15#1": "asserted", "s12.p17#1": "hedged", "s12.p17#2": "hedged", "s12.p17#3": "open",
          "s12.p17#4": "asserted", "s12.p17#5": "hedged", "s13.p3#3": "asserted", "s13.p3#4": "hedged", "s13.p3#5": "asserted", "s13.p3#6": "open",
          "s13.p4#4": "asserted", "s13.p4#6": "limitation", "s13.p4#9": "hedged", "s13.p4#11": "asserted", "s14.p2#2": "hedged", "s14.p6#1": "asserted",
          "s14.p6#2": "hedged", "s14.p7#2": "hedged", "s14.p7#3": "hedged", "s14.p8#1": "asserted", "s14.p10#1": "asserted", "s14.p10#2": "hedged",
          "s14.p10#5": "hedged", "s14.p10#8": "open", "s15.p1#1": "asserted", "s15.p2#1": "asserted", "s15.p2#2": "hedged", "s15.p3#1": "asserted",
          "s15.p3#2": "asserted", "s15.p3#3": "hedged", "s15.p3#4": "asserted", "s15.p3#5": "open", "s15.p4#1": "asserted", "s15.p4#2": "hedged",
          "s15.p4#3": "open", "s15.p8#1": "hedged", "s15.p8#2": "open"}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["stance"] = STANCE[cf["fact_id"].split(":", 1)[1]]          # KeyError = a claim without a stance
VARS = {   # claim id -> (cause, effect): quantity ids or mechanism:<token> (lists.MECHANISMS), blank when the claim has none
    'abs.g1#1': ('aspect_ratio', 'exposure'),
    'abs.g1#2': ('exposure', 'mechanism:side_reaction'),
    'abs.g2#2': ('deposition_temperature', 'mechanism:Zn_metal;purge_time'),
    'abs.g4#1': ('deposition_temperature', 'mechanism:self_limiting;resistivity'),
    'abs.g4#2': ('deposition_temperature;mechanism:residual_H2O', 'growth_per_cycle'),
    's6.p1#1': ('', ''),
    's6.p1#2': ('mechanism:self_limiting', 'film_thickness'),
    's6.p3#1': ('aspect_ratio', 'exposure'),
    's6.p6#1': ('deposition_temperature', 'mechanism:Zn_metal'),
    's6.p6#4': ('deposition_temperature', 'purge_time'),
    's6.p8#1': ('', 'aspect_ratio'),
    's6.p8#2': ('', ''),
    's6.p8#6': ('porosity', 'feature_width'),
    's6.p8#9': ('porosity', 'mechanism:gas_diffusion'),
    's6.p8#12': ('deposition_temperature', 'mechanism:Zn_metal'),
    's9.p3#4': ('', ''),
    's9.p6#12': ('', 'deposition_temperature'),
    's9.p6#13': ('', 'deposition_temperature'),
    's9.p7#1': ('', ''),
    's9.p9#7': ('purge_time', 'surface_coverage'),
    's12.p1#1': ('exposure;deposition_temperature', 'mechanism:Zn_metal'),
    's12.p1#2': ('deposition_temperature;purge_time', 'mechanism:residual_H2O;growth_per_cycle'),
    's12.p1#3': ('deposition_temperature', 'mass_gain'),
    's12.p1#13': ('', 'growth_per_cycle'),
    's12.p6#5': ('mechanism:gas_generation', 'pressure_rise'),
    's12.p6#6': ('mechanism:residual_H2O', 'pressure_rise'),
    's12.x1#7': ('mechanism:leak', 'pressure_rate'),
    's12.x1#9': ('mechanism:leak', 'pressure_rise'),
    's12.p7#2': ('deposition_temperature', 'pressure_rise;mass_gain'),
    's12.p7#3': ('deposition_temperature;mechanism:gas_generation', 'pressure_rate'),
    's12.p8#5': ('cycle_number', 'gas_moles_per_cycle'),
    's12.p8#6': ('gas_moles_per_cycle', 'pressure_rate'),
    's12.p15#1': ('', 'reaction_stoichiometry'),
    's12.p17#1': ('mechanism:residual_H2O', 'reaction_stoichiometry'),
    's12.p17#2': ('mechanism:surface_OH', 'reaction_stoichiometry'),
    's12.p17#3': ('mechanism:residual_H2O;mechanism:surface_OH', 'reaction_stoichiometry'),
    's12.p17#4': ('mechanism:Zn_metal', 'reaction_stoichiometry'),
    's12.p17#5': ('mechanism:Zn_metal', 'deposited_moles_per_cycle'),
    's13.p3#3': ('mass_gain', 'crystallite_size'),
    's13.p3#4': ('film_thickness', 'crystallinity'),
    's13.p3#5': ('deposition_temperature', 'mechanism:Zn_metal'),
    's13.p3#6': ('', ''),
    's13.p4#4': ('mechanism:Zn_metal', 'resistivity'),
    's13.p4#6': ('mechanism:cracks', 'resistivity'),
    's13.p4#9': ('film_thickness;crystallite_size', 'resistivity'),
    's13.p4#11': ('mechanism:percolation', 'resistivity'),
    's14.p2#2': ('mechanism:desorption;purge_time', 'composition'),
    's14.p6#1': ('purge_time', 'mechanism:desorption'),
    's14.p6#2': ('feature_width', 'mechanism:desorption'),
    's14.p7#2': ('deposition_temperature;mechanism:reaction_diffusion', 'composition'),
    's14.p7#3': ('mechanism:reabsorption', 'signal_intensity'),
    's14.p8#1': ('mechanism:self_limiting;mechanism:reaction_diffusion', 'composition'),
    's14.p10#1': ('deposition_temperature', 'growth_per_cycle'),
    's14.p10#2': ('mechanism:residual_H2O', 'mechanism:CVD_growth'),
    's14.p10#5': ('mechanism:surface_OH', 'growth_per_cycle'),
    's14.p10#8': ('purge_time;mechanism:desorption', 'mechanism:surface_OH'),
    's15.p1#1': ('exposure;purge_time', 'step_coverage'),
    's15.p2#1': ('', 'resistivity'),
    's15.p2#2': ('film_thickness;crystallinity;annealing_temperature', 'resistivity'),
    's15.p3#1': ('deposition_temperature', 'mechanism:Zn_metal'),
    's15.p3#2': ('deposition_temperature', 'composition;resistivity'),
    's15.p3#3': ('deposition_temperature', 'reaction_stoichiometry'),
    's15.p3#4': ('deposition_temperature;purge_time', 'mechanism:residual_H2O'),
    's15.p3#5': ('mechanism:CVD_growth;mechanism:surface_OH', 'growth_per_cycle'),
    's15.p4#1': ('deposition_temperature', 'mechanism:surface_OH;mechanism:residual_H2O'),
    's15.p4#2': ('deposition_temperature', 'purge_time'),
    's15.p4#3': ('', ''),
    's15.p8#1': ('deposition_temperature', 'growth_per_cycle;cycle_number'),
    's15.p8#2': ('purge_time;deposition_temperature', 'film_thickness'),
}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["cause"], cf["effect"] = VARS[cf["fact_id"].split(":", 1)[1]]  # KeyError = a claim without variables

# ================================================================== stage 3: one tree (parent, links)
# Runs: the three stated depositions of Sec. II B (T held at 120 °C, held at 160 °C, cycled 120/160 °C), each coating an NPC pair;
# under each, one specimen run per physical object the paper's facts are about (the weighed pair, the SEM-EDS section, the XRD
# NPC, the photographed NPC, the resistivity prism); the thermocouple test run of Fig. 2(d) (same conditions as the cycled run, so
# a deposition of its own, linked to it); the uncoated compact of Fig. 4(a); and the Eq. (1)-(2) estimate of hold and purge times,
# a simulation under the process because it exists only to set the shared hold and purge times. Parent rule: the row without which
# the fact would not exist; links: a second home (a claim's support, the same data shown twice, the runs a comparison covers).
PAPER, PROC = K, f"{K}:process"
R120, R160, RCYC = f"{K}:run120", f"{K}:run160", f"{K}:run120_160"
RUN = {"120": R120, "160": R160, "120/160": RCYC}
TEST, BARE, SIM = f"{K}:run_tc", f"{K}:run_bare", f"{K}:sim:eq1_2"
RUNS = f"{R120};{R160};{RCYC}"
N(PAPER, "paper", "Greenberg et al. 2023, JVST A: static-dose DEZ/H2O ZnO ALD infiltration of mm-thick Al2O3 nanoparticle compacts "
  "at 120 °C, 160 °C and with the temperature cycled 120/160 °C", "", evidence="abs.g1", label_as_printed="10.1116/6.0003182")
N(PROC, "process", "shared process: 20 static-dose DEZ/H2O cycles (~9 Torr, 1920 s holds, 2880 s purges) in an ALD NanoSolutions "
  "RX-series reactor on pressed Al2O3 NPCs (L = 0.78 mm, φ_i = 50.5%), with gravimetry, pressure logging, XRD, resistivity, SEM-EDS and XPS",
  PAPER, evidence="s9.p4;s8.p1;s9.p1;abs.g5")
for r, lab, ev in ((R120, "120 °C", "s9.p6;fig1b"), (R160, "160 °C", "s9.p6;fig1b"), (RCYC, "120/160 °C", "s9.p6;fig1b")):
    what = {"120 °C": "T held at 120 °C", "160 °C": "T held at 160 °C",
            "120/160 °C": "T cycled: 120 °C for every step but the H2O purge, 160 °C during it"}[lab]
    N(r, "run", f"ALD run, {what}, two NPCs coated together", PROC, evidence=ev, label_as_printed=lab,
      qualifiers=f"run=deposition;how=stated;sample={r.rsplit(':run', 1)[1]}")
# specimens: one row per physical object the facts are about, under the run that coated it. Two NPCs were coated in each run and
# all were weighed (s12.p1, s9.p3, Table I caption: the pair, stated); a prism was cut from one NPC after Ti/Au metallization for
# resistivity (s10.p2; s13.p4: one NPC per condition), stated as a prism, though not which NPC. Which NPC of the pair went to XRD
# (s10.p1: one face scanned, then fractured and rescanned), to SEM-EDS (s10.p3: sectioned and epoxy-mounted) or to the photograph
# (Fig. 4, s13.p1) is not stated, and nothing in Secs. II C, III B, III C or the captions ties two of these to one NPC: inferred,
# one specimen each. Table II: columns 1-4 are XRD (Rietveld, Halder-Wagner), under the XRD specimen; column 5 is ρ, under the prism.
SPEC = {}
for lab in ("120", "160", "120/160"):
    r, s = RUN[lab], RUN[lab].rsplit(":run", 1)[1]
    SPEC[lab] = {}
    for kind, how, printed, what, ev in (
            ("pair", "stated", "NPC pair", f"the two NPCs of the {lab} °C run, weighed before and after ALD: the mass gain and what is "
             "derived from it (porosity, GPC, Δn_s, coating thickness)", "s12.p1;s9.p3;tabI.cap"),
            ("section", "inferred", "SEM-EDS section", f"the NPC of the {lab} °C run sectioned for cross-sectional SEM-EDS (Fig. 6); "
             "which NPC of the pair is not stated", "fig6.cap;s10.p3"),
            ("xrd", "inferred", "XRD", f"the NPC of the {lab} °C run measured by XRD, one face then the fracture surfaces (Fig. 5; Table II "
             "phase fractions and crystallite sizes); which NPC of the pair is not stated", "fig5.cap;s10.p1;tabII.cap"),
            ("photo", "inferred", "photograph", f"the NPC of the {lab} °C run photographed after ALD (Fig. 4); which NPC of the pair is not stated",
             "fig4.cap;s13.p1"),
            ("prism", "stated", "ρ prism", f"the prism cut from one NPC of the {lab} °C run after Ti/Au metallization, for through-thickness "
             "resistivity (Table II); which NPC of the pair it was cut from is not stated", "s10.p2;s13.p4;tabII.cap")):
        SPEC[lab][kind] = N(f"{r}:{kind}", "run", what, r, evidence=ev, label_as_printed=f"{lab} °C {printed}",
                            qualifiers=f"run=specimen;how={how};sample={s}_{kind}")
N(TEST, "run", "thermocouple test run of Fig. 2(d): same conditions as the cycled run, boat temperature logged", PROC,
  evidence="fig2d;fig2.cap", label_as_printed="test run", qualifiers="run=deposition;how=stated;sample=fig2d_test", links=RCYC)
N(BARE, "run", "uncoated Al2O3 NPC photographed before ALD (Fig. 4a)", PROC, evidence="fig4a;fig4.cap", label_as_printed="Before ALD",
  qualifiers="run=specimen;how=stated;sample=before_ALD")
N(SIM, "run", "Eq. (1)-(2) estimate of the hold time and of the H2O purge time needed at 120 and 160 °C", PROC,
  evidence="eq1;eq2;s9.p9", label_as_printed="sim · Eq. (2)", qualifiers="run=simulation;how=stated;sim=eq1_2")

PARENT, LINKS = {}, {}
FX = {f["fact_id"]: f for f in C.facts()}
fid = lambda s_: f"{K}:{s_}"


def put(parent, *ids, links=""):
    for i in ids:
        assert fid(i) in FX, i
        assert fid(i) not in PARENT, i
        PARENT[fid(i)] = parent
        if links:
            LINKS[fid(i)] = links


def ln(i, *targets):
    LINKS[fid(i)] = ";".join(t if t.startswith(K + ":") else fid(t) for t in targets)


# shared process: reactor, precursors, dosing, NPC preparation, characterization
put(PROC, "abs.g3#1", "abs.g5#1", "s6.p8#3", "s6.p8#4", "s6.p8#10", "s6.p8#11",
    *[f"s8.p1#{i}" for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)], "s9.p1#1", "s9.p1#2", "s9.p1#3", "s9.p3#1", "s9.p3#2", "s9.p3#3",
    *[f"s9.p4#{i}" for i in range(1, 13) if i != 3], "s9.p5#1", "s9.p5#2", "s9.p5#3", "s9.p6#1", "s9.p6#3", "s9.p6#8", "s9.p6#9",
    "s9.p6#11", *[f"s10.p1#{i}" for i in range(1, 10)], *[f"s10.p2#{i}" for i in range(1, 5)], *[f"s10.p3#{i}" for i in range(1, 5)],
    "s10.p4#1", "s10.p4#2", *[f"s10.p5#{i}" for i in range(1, 6)], "s12.p1#4", "s12.p1#9", "s12.p2#2", "s12.p2#3",
    "eq3#1", "eq4#1", "eq5#1", "s12.x1#2", "s12.x1#3", "s12.x1#8", "fig3a#2", "s12.p8#2", "s12.p8#3", "fig3b#1", "fig3c#1",
    "s12.p9#2", "eq6#1", "eq7#1", "eq8#1", "fig2a#1", "s13.p1#1", "fig5#1", "s13.p2#2", "s13.p4#5", "s13.p4#10",
    "s14.p1#3", "s14.p2#1", "fig6d#1")
put(PROC, "fig1a#2", links=fid("s8.p1#8"))                                     # the schematic repeats the measured compact size
put(PROC, "fig1a#3", links=fid("s8.p1#7"))
put(PROC, "fig1a#4", links=fid("s8.p1#9"))
# facts that compare or cover the runs: under the process, linked to the runs
for i in ("s9.p6#10", "s12.p2#1", "s12.x1#1", "s12.p8#1", "s12.p8#4", "s13.p2#1", "s14.p1#1"):
    put(PROC, i, links=RUNS)
put(PROC, "fig3c#3", "fig6a#2", links=f"{R120};{RCYC}")
put(PROC, "s14.p1#4", links=f"{R120};{RCYC};{fid('fig6d#2')};{fid('fig6f#1')}")
put(PROC, "s14.p1#5", links=f"{R120};{RCYC};{fid('s12.p1#5')};{fid('s12.p1#7')}")
put(PROC, "s12.p1#8", links=";".join(fid(f"tabI.r{r}c2#1") for r in (1, 2, 3)))   # the text's porosities, printed in another order
# the Eq. (1)-(2) estimate: its model, parameters and outputs (definitions of its symbols stay with the paper's terms)
put(SIM, "eq1#1", "eq2#1", "s9.p9#2", "s9.p9#3", "s9.p9#4", "s9.p9#5", "s9.p9#6")
# deposition runs: the chamber during the run (its T and schedule, the Fig. 2 trace, the cycle-15 δp, TS and Δn_g of Fig. 3 and Table I;
# ȳ, derived from Δn_g and Δn_s, sits under Δn_g by the first-input rule below)
put(R120, "s9.p6#4", "s12.x1#10", "s12.x1#11", "s12.x1#12", "fig2a#2", "fig2a#3")
put(R160, "s9.p6#5", "s12.x1#13", "s12.p7#1", "fig3a#1", "fig2b#1", "fig2b#2", "fig3c#2")
put(RCYC, "s9.p6#6", "s9.p6#7", "s12.x1#4", "s12.x1#5", "s12.x1#6", "fig2c#1")
put(RCYC, "fig1b#2", links=fid("s9.p6#7"))                                     # the cycled schedule, in the text and in Fig. 1(b)
for lab, ids in SCHED.items():                                                 # the per-step temperatures of Fig. 1(b), under their run
    put(RUN[lab], *[i.split(":", 1)[1] for i in ids])
for lab, r in (("120", "1"), ("160", "2"), ("120/160", "3")):
    put(RUN[lab], f"tabI.r{r}c5#1")                                            # Δn_g, Table I
put(TEST, "fig2d#1", "fig2d#2")
put(TEST, "s15.p4#4", links=fid("fig2d#2"))                                    # the 33.5 min ramp read from the test-run trace
put(BARE, "fig4a#1")
# specimens: measured or fitted values under the specimen they were measured on; calculated values under their first input
# (porosity <- mass gain, GPC <- porosity, Δn_s <- GPC, thickness <- mass gain, excess thickness <- thickness), so the mass gain
# carries its chain into the pair
for lab, r, mass, photo, pat in (("120", "1", "s12.p1#5", "s13.p1#2", "fig5#2"), ("160", "2", "s12.p1#6", "s13.p1#4", "fig5#3"),
                                 ("120/160", "3", "s12.p1#7", "s13.p1#5", "fig5#4")):
    put(SPEC[lab]["pair"], mass)                                               # mass gain (Table I c1 and the text)
    put(SPEC[lab]["photo"], photo)                                             # Fig. 4(b)-(d) and the text's colours
    put(SPEC[lab]["xrd"], pat, f"tabII.r{r}c1#1", f"tabII.r{r}c2#1", f"tabII.r{r}c3#1")   # Fig. 5 pattern, Table II c1-c3
    put(SPEC[lab]["prism"], f"s13.p4#{r}")                                     # ρ, Table II c5 and the text
put(SPEC["160"]["xrd"], "tabII.r2c4#1")                                        # Zn crystallite size, only detected at 160 °C
put(SPEC["160"]["xrd"], "s13.p2#3", links=fid("fig5#3"))                      # the Zn peaks, in the text and in Fig. 5
put(SPEC["120"]["section"], "fig6a#1", "fig6d#2", "fig6d#3", "fig6d#4")       # Fig. 6 images, maps and line scans
put(SPEC["160"]["section"], "fig6b#1", "fig6e#1", "fig6e#2", "fig6e#3", "fig6e#4")
put(SPEC["160"]["section"], "s14.p7#1", links=fid("fig6e#1"))                 # the Zn dip, in the text and in Fig. 6(e)
put(SPEC["120/160"]["section"], "fig6c#1", "fig6f#1", "fig6f#2", "fig6f#3")
# Fig. 3(b) plots per cycle the Δn_g that Table I averages: each series under its Table I value
put(fid("tabI.r1c5#1"), "fig3b#3")
put(fid("tabI.r2c5#1"), "fig3b#2")
put(fid("tabI.r3c5#1"), "fig3b#4")
# cited facts: under the first reference they name
for f in C.facts():
    if f["type"] == "cited" and f["fact_id"] not in PARENT:
        m = re.search(r"ref\. (\d+)", f["mentions"])
        if m:
            PARENT[f["fact_id"]] = f"{K}:refs:{m.group(1)}"
# what the rules above do not place: cited statements with no reference number, an interpretive model assumption
put(PAPER, "abs.g2#1", "s6.p2#1", "s6.p2#2", "s14.p10#6")
# claims: under the paper, linked to what supports them
CLAIM = {"abs.g1#1": ("s6.p4#5", "s6.p8#11"), "abs.g1#2": ("s6.p5#9",), "abs.g2#2": ("s6.p6#3", "s6.p5#13"),
         "abs.g4#1": ("s14.p1#4", "s12.p1#12", "s13.p4#11"), "abs.g4#2": ("s12.p1#10", "s12.p1#12"), "s6.p1#1": ("s6.p2#3",),
         "s6.p1#2": ("s6.p1#4",), "s6.p3#1": ("s6.p4#5",), "s6.p6#1": ("s6.p6#2", "s6.p6#3"), "s6.p6#4": ("s6.p6#3",),
         "s6.p8#1": ("s6.p8#7", "s6.p2#1"), "s6.p8#2": ("s6.p5#9",), "s6.p8#6": ("s8.p1#3", "s8.p1#9"), "s6.p8#9": ("s8.p1#9", "s6.p4#2"),
         "s6.p8#12": (R120, R160, RCYC), "s9.p3#4": ("s9.p3#3",), "s9.p6#12": ("s9.p6#11",), "s9.p6#13": ("s9.p6#1", "s9.p6#11"),
         "s9.p7#1": ("eq1#1", "eq2#1"), "s9.p9#7": ("s9.p9#5", "s9.p9#6", "s9.p4#10"),
         "s12.p1#1": ("s6.p5#9", "s6.p5#13"), "s12.p1#2": ("s9.p9#5",), "s12.p1#3": ("s12.p1#5", "s12.p1#6", "s12.p1#7"),
         "s12.p1#13": ("s12.p1#12",), "s12.p6#5": ("s12.p2#3", "eq4#1", "eq5#1"), "s12.p6#6": ("s9.p6#12",),
         "s12.x1#7": ("s12.x1#4", "s12.x1#6"), "s12.x1#9": ("s12.x1#3", "s12.x1#5"), "s12.p7#2": ("s12.x1#5", "s12.x1#11", "s12.p7#1"),
         "s12.p7#3": ("s12.x1#6", "s12.x1#12", "s12.x1#13"), "s12.p8#5": ("fig3b#2",), "s12.p8#6": ("fig3c#2", "fig3b#2"),
         "s12.p15#1": ("s12.p14#1", "s12.p14#3"), "s12.p17#1": ("s12.p14#1", "s12.p14#3"), "s12.p17#2": ("s12.p14#1",),
         "s12.p17#3": ("s12.p14#1", "s12.p14#3"), "s12.p17#4": ("s12.p14#2",), "s12.p17#5": ("eq8#1", "tabI.r2c4#1"),
         "s13.p3#3": ("tabII.r1c1#1", "tabII.r1c2#1", "tabII.r3c1#1", "tabII.r3c2#1", "s13.p3#1", "s13.p3#2"),
         "s13.p3#4": ("tabII.r1c1#1", "s12.p1#5"), "s13.p3#5": ("tabII.r2c1#1", "tabII.r2c2#1", "s12.p1#6", "tabII.r2c3#1", "s13.p1#4"),
         "s13.p3#6": ("s13.p1#5",), "s13.p4#4": ("s13.p4#2", "tabII.r2c3#1"), "s13.p4#6": ("s13.p4#1", "s13.p4#3"),
         "s13.p4#9": ("s13.p4#7", "s13.p4#8", "tabII.r1c2#1", "s13.p3#1"), "s13.p4#11": ("s13.p4#10",),
         "s14.p2#2": ("s14.p1#4", "s14.p2#1"), "s14.p6#1": ("s9.p4#7",), "s14.p6#2": ("s14.p1#4",), "s14.p7#2": ("s14.p7#1",),
         "s14.p7#3": ("s14.p7#1", "fig6e#2"), "s14.p8#1": ("s14.p1#4",), "s14.p10#1": ("s12.p1#10", "s12.p14#1", "s12.x1#12"),
         "s14.p10#2": ("s9.p9#5",), "s14.p10#5": ("s14.p10#4", "s14.p1#4"), "s14.p10#8": ("s14.p10#7", "s14.p6#2"),
         "s15.p1#1": ("s14.p1#1", "eq1#1"), "s15.p2#1": ("s13.p4#1", "s13.p4#3", "s13.p4#8"), "s15.p2#2": ("s13.p4#9",),
         "s15.p3#1": ("tabII.r2c3#1", "s13.p2#3"), "s15.p3#2": ("tabII.r1c3#1", "s14.p1#4", "s13.p4#1"),
         "s15.p3#3": ("s12.x1#10", "s12.p14#1"), "s15.p3#4": ("s9.p9#5", "s12.p1#10"), "s15.p3#5": ("s14.p10#8", "s12.p1#10"),
         "s15.p4#1": ("tabII.r3c3#1", "s12.p14#3"), "s15.p4#2": ("s9.p9#5", "s9.p9#6"), "s15.p4#3": ("s15.p4#4",),
         "s15.p8#1": ("s12.p1#10", "s14.p1#4"), "s15.p8#2": ("s15.p8#1",)}
for c, sup in CLAIM.items():
    put(PAPER, c)
    ln(c, *sup)
for f in C.facts():                                                            # definitions: terms and symbols of the paper
    if f["type"] == "definition" and f["fact_id"] not in PARENT:
        PARENT[f["fact_id"]] = PAPER
for f in C.facts():                                                            # a value computed from others: under its first input
    if f["type"] == "derived" and f["inputs"] and f["fact_id"] not in PARENT:
        PARENT[f["fact_id"]] = f["inputs"].split(";")[0]
PARENT[MAT] = PARENT[STRUCT] = PROC                                            # material and structure type: shared by every run
left = [f["fact_id"] for f in C.facts() if "#" in f["fact_id"] and f["fact_id"] not in PARENT]
assert not left, left
assert not [c for c in C.facts() if c["type"] == "claim" and c["fact_id"] not in LINKS], "claim without links"
for r in sorted({p for p in PARENT.values() if ":refs:" in p}, key=lambda x: int(x.rsplit(":", 1)[1])):
    kids = [f for f in C.facts() if PARENT.get(f["fact_id"]) == r]
    ev = list(dict.fromkeys(f["evidence"].split(";")[0] for f in kids))
    N(r, "cited", f"cited work, reference {r.rsplit(':', 1)[1]} of the paper", PAPER, evidence=";".join(ev),
      label_as_printed=f"ref. {r.rsplit(':', 1)[1]}")
for f in C.facts():
    if f["fact_id"] in PARENT:
        f["parent"] = PARENT[f["fact_id"]]
        f["links"] = LINKS.get(f["fact_id"], "")
# the set the paper names: the three temperature schedules, explored to see whether Zn metal can be avoided (s6.p8)
from facts import purpose, facts as _facts  # noqa: E402
N(f"{K}:grp:schedules", "group", "the three temperature schedules of the 20-cycle ZnO runs: T held at 120, held at 160, cycled 120/160 °C",
  PROC, evidence="s6.p8;fig1b;s9.p6", label_as_printed="120, 160, 120/160 °C", qualifiers="how=stated")
for r in _facts():
    if r["fact_id"] in (f"{K}:run120", f"{K}:run160", f"{K}:run120_160"):
        r["parent"] = f"{K}:grp:schedules"
purpose(f"{K}:grp:schedules", f"{K}:s6.p8#12")

# ================================================================== stage 3b: the activity/entity tree (facts.retree)
# recipe = the old process; the three stated depositions and the thermocouple test run become deposition activities (converted in
# place, their chamber observations under a process-monitor measurement); under each deposition the weighed NPC pair is an entity,
# and the sectioned, XRD, photographed and resistivity specimens are pieces (entities under the pair); a weighing before ALD is a
# measurement activity of order 0 on the pair; the uncoated NPC of Fig. 4(a) is an entity under the recipe, photographed before any
# deposition; the Eq. (1)-(2) estimate is a simulation activity with a model-run entity.
RUNROW = {r["fact_id"]: r for r in C.facts() if r["type"] == "run"}
DEPS = {d: dict(statement=RUNROW[d]["statement"], label=RUNROW[d]["label_as_printed"], how="stated", evidence=RUNROW[d]["evidence"]) for d in (R120, R160, RCYC, TEST)}
ENTS = {d: dict(dep=d, ent=None, parent=None, statement="", label=RUNROW[d]["label_as_printed"], how="stated") for d in (R120, R160, RCYC, TEST)}
EXTRA = []
for lab, s_ in (("120", "120"), ("160", "160"), ("120/160", "120_160")):
    pair_ = f"{K}:ent:{s_}:pair"
    pr = RUNROW[SPEC[lab]["pair"]]
    ENTS[SPEC[lab]["pair"]] = dict(dep=RUN[lab], ent=pair_, parent=RUN[lab], statement=pr["statement"], label=f"{lab} °C NPC pair", how="stated", evidence=pr["evidence"])
    for kind in ("section", "xrd", "photo", "prism"):
        sr = RUNROW[SPEC[lab][kind]]
        ENTS[SPEC[lab][kind]] = dict(dep=RUN[lab], ent=f"{K}:ent:{s_}:{kind}", parent=pair_, statement=sr["statement"], label=sr["label_as_printed"],
                                     how=re.search(r"how=(\w+)", sr["qualifiers"]).group(1), evidence=sr["evidence"])
    EXTRA.append((f"{K}:meas:ent:{s_}:pair:weighing_before", "activity", "the two NPCs weighed before ALD", pair_,
                  dict(kind="measurement", how="stated", order="0", evidence="s9.p3", label_as_printed="weighing before ALD")))
ENTS[BARE] = dict(dep=f"{K}:recipe", ent=f"{K}:ent:bare", parent=f"{K}:ent:compacts", statement=RUNROW[BARE]["statement"], label="uncoated NPC", how="stated",
                  evidence=RUNROW[BARE]["evidence"])
SIMRUNS = {SIM: dict(act=f"{K}:simact:eq1_2", ent=f"{K}:simact:eq1_2:run", parent=PAPER, statement=RUNROW[SIM]["statement"], label=RUNROW[SIM]["label_as_printed"],
                     evidence=RUNROW[SIM]["evidence"])}
C.retree(K, PROC, DEPS, ENTS, SIMRUNS, extra=EXTRA)
for r in C.facts():                                                             # the schedules group's members: the three depositions
    if r["fact_id"] == f"{K}:grp:schedules":
        r["links"] = ";".join([r["links"].split(";")[0], R120, R160, RCYC])
for r in C.facts():
    if r["fact_id"] == f"{K}:meas:ent:bare:photograph":
        r["order"] = "0"                                                        # photographed before any deposition
# the compacts as pressed are an input entity (calipers, porosity, cracks under an order-0 measurement; d_NP and the aspect ratio
# derived from them), named in the inputs of the three runs; the uncoated NPC of Fig. 4(a) is a piece of it. What the text says of
# the process monitor itself (hand-adjusted pulses, the chamber volume, the calibration spread, leaks, the figure's markings) stays
# on that method activity; what it observes over all three coated samples (XRD faces and phases, the vertical current, the Al and
# Zn maps, the pressure traces' common shape, the ranking of Δn_g and TS) spans the schedules comparison; the Zn Kα excess of the
# 120 °C sample is that section's observation, relative to the 120/160 °C section
C.input_entity(K, f"{K}:ent:compacts", "the pressed Al2O3 NPCs as made, the input of every ALD run: thickness and diameter by calipers, initial porosity, cracks; "
               "d_NP from the powder's BET area and the aspect ratio from L and d_pore", "NPCs as pressed", "s8.p1;s6.p8",
               measured=[("measurement", [f"{K}:s8.p1#7", f"{K}:s8.p1#8", f"{K}:s8.p1#9", f"{K}:s8.p1#10", f"{K}:fig1a#2", f"{K}:fig1a#3", f"{K}:fig1a#4"])],
               inputs_of=[R120, R160, RCYC])   # the schematic's printed labels (fig1a) repeat the compacts' measured size and porosity: read from figure (P9)
# the temperature calibration runs (s9.p6) measured the reactor, not a sample: a measurement activity of the recipe
N(f"{K}:meas:recipe:calibration", "activity", "temperature calibration runs with an extra thermocouple on the boat, at the same outside temperature",
  f"{K}:recipe", evidence="s9.p6", kind="measurement", how="stated", label_as_printed="temperature calibration")
for fid_, par in ((f"{K}:s9.p6#3", f"{K}:meas:recipe:calibration"),
                  (f"{K}:s8.p1#3", f"{K}:ent:compacts"), (f"{K}:s6.p8#7", f"{K}:ent:compacts"), (f"{K}:s9.p4#11", f"{K}:method:process_monitor"),
                  (f"{K}:s9.p5#1", f"{K}:method:process_monitor"), (f"{K}:s12.x1#3", f"{K}:method:process_monitor"), (f"{K}:fig3a#2", f"{K}:method:process_monitor"),
                  (f"{K}:s14.p1#5", f"{K}:meas:ent:120:section:sem_eds")):
    next(r for r in C.facts() if r["fact_id"] == fid_)["parent"] = par
C.comparisons(K, {f"{K}:grp:schedules": ("series", "deposition_temperature")})
for fid_ in ("s12.p1#8", "s10.p1#5", "s10.p1#9", "s13.p2#1", "s13.p2#2", "fig5#1", "s13.p4#10", "s14.p1#1", "s14.p1#3", "s14.p1#4", "s14.p2#1", "fig6d#1",
             "fig6a#2", "s13.p1#1", "s12.p8#4", "fig3b#1", "fig3c#1", "s12.p2#2", "s12.p2#3", "s12.x1#1"):
    next(r for r in C.facts() if r["fact_id"] == f"{K}:{fid_}")["parent"] = f"{K}:cmp:schedules"
# what each ± is (P2): the paper says mass gain and GPC ± are the spread within each run's NPC pair, Table II's are
# pattern-fit errors, ρ's the electrode-area uncertainty, ȳ's a measurement uncertainty; AR's is propagated from L; the rest is not stated
# what each fraction is a fraction of (P4): porosity of the compact volume (its definition); the paper does not say whether the mass
# in situ or ex situ (P6): the runs' generic measurements are the chamber pressure traces (in situ); the compacts were measured by calipers
C.modes(K, {"meas:run120:measurement": "in_situ", "meas:run160:measurement": "in_situ", "meas:ent:compacts:measurement": "ex_situ"})
# what each GPC is averaged over (P5): the run's porosity drop over its 20 cycles; the cited GPCs are coating thickness or mass over cycles
C.qualify(K, {s: "over=run" for s in ("s12.p1#10", "s12.p1#11", "s12.p1#12", "s6.p5#3", "s6.p5#7")})
# gain is relative to the initial or the final mass, nor whether the Rietveld wt% are of all phases or of the crystalline ones
C.relative_to(K, {**{s: "total_volume" for s in ("s8.p1#9", "fig1a#4", "tabI.r1c2#1", "tabI.r2c2#1", "tabI.r3c2#1")},
                  **{f"s12.p1#{i}": "not_stated" for i in (5, 6, 7)}, **{s: "not_stated" for s in ("tabII.r1c1#1", "tabII.r2c1#1", "tabII.r3c1#1", "tabII.r2c3#1")}})
C.uncertainty_kinds(K, {'s6.p8#4': ('not_stated', ''), 's6.p8#7': ('propagated', ''), 's8.p1#4': ('not_stated', ''), 's8.p1#7': ('not_stated', ''), 's8.p1#8': ('not_stated', ''), 's8.p1#9': ('not_stated', ''), 's12.p1#5': ('pieces', '2'), 's12.p1#6': ('pieces', '2'), 's12.p1#7': ('pieces', '2'), 's12.p1#10': ('pieces', '2'), 's12.p1#11': ('pieces', '2'), 's12.p1#12': ('pieces', '2'), 'tabI.r1c2#1': ('not_stated', ''), 'tabI.r2c2#1': ('not_stated', ''), 'tabI.r3c2#1': ('not_stated', ''), 's12.p14#1': ('measurement', ''), 's12.p14#2': ('measurement', ''), 's12.p14#3': ('measurement', ''), 'tabII.r1c1#1': ('fit', ''), 'tabII.r1c2#1': ('fit', ''), 'tabII.r2c1#1': ('fit', ''), 'tabII.r2c2#1': ('fit', ''), 'tabII.r3c1#1': ('fit', ''), 'tabII.r3c2#1': ('fit', ''), 'tabII.r2c3#1': ('fit', ''), 'tabII.r2c4#1': ('fit', ''), 's13.p3#1': ('not_stated', ''), 's13.p3#2': ('not_stated', ''), 's13.p4#1': ('measurement', ''), 's13.p4#2': ('measurement', ''), 's13.p4#3': ('measurement', '')})
# identity of entities with equal conditions (P23): each run's pieces (section, XRD specimen, photographed face, resistivity prism) come
# from its pair of NPCs; which NPC each comes from is not stated
for lab, s_ in (("120", "120"), ("160", "160"), ("120/160", "120_160")):
    C.identity(K, "not_stated", [f"{K}:ent:{s_}:{p}" for p in ("section", "xrd", "photo", "prism")], f"the pieces of the {lab} °C pair come from its two NPCs; which NPC each comes from is not stated", "s9.p3;s10.p1;s10.p2;s10.p3")
write(K, PID)
