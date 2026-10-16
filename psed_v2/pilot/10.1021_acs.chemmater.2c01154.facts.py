"""Stage 2 facts for mat22 (10.1021_acs.chemmater.2c01154), read by hand from the element texts, the figure crops and the
table crops. Heat-map cells: Fig. 2 classes (two-class legend) and Fig. 4 printed S/Mo values are typed in below; Fig. 7b
and Fig. 8 colours are read cell by cell against the bars (one fact each, "read from colour"; the black >dl band of Fig. 8 and the values the text gives).
Points only from points.json (Fig. 1c) and accepted v1 curves."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from facts import F, NK, P, write, v1_points, cases_points  # noqa: E402

K, PID = "mat22", "10.1021_acs.chemmater.2c01154"
R = "H2 flow ratio"


def hr(r):
    return f"{R} {r}"


def ratio(ev, r, what, mentions, dk="chosen input"):
    return F(K, ev, "setting", f"{what}: {R} set to {r}", quantity="plasma_gas_ratio", qualifiers="gas=H2",
             label_as_printed=R, value=r, data_kind=dk, mentions=mentions)


def temp(ev, t, what, mentions):
    return F(K, ev, "setting", f"{what}: deposition temperature {t} °C", quantity="deposition_temperature", value=t,
             unit="°C", data_kind="chosen input", mentions=mentions)


def cyc(ev, n, what, mentions):
    return F(K, ev, "setting", f"{what}: {n} ALD cycles", quantity="cycle_number", value=n, data_kind="chosen input",
             mentions=mentions)


# ------------------------------------------------------------------ front matter
NK("s1.h", "title")
NK("s1.p1", "author list")
NK("s1.p2", "citation line")
NK("s1.p3;s1.p4;s1.p5;s1.p6;s1.p7", "front matter")

# ------------------------------------------------------------------ abstract (s1.p8 is the same abstract as one block)
F(K, "abs.g1;s1.p8", "claim", "Two-dimensional TMDCs such as MoS2 attract intense study for electronic applications.")
F(K, "abs.g1;s1.p8", "claim", "Depositing large-area TMDC films of adequate quality under conditions that applications allow is "
  "still a major unsolved challenge.")
C_MAIN = F(K, "abs.g2;s1.p8;s2.p10;s4.p1;s1.h", "claim",
           "Plasma-enhanced ALD gives polycrystalline, wafer-scale MoS2, TiS2 and WS2 films with controlled thickness at "
           "temperatures as low as 100 °C, a record low.", mentions="100 °C")
C_KEY = F(K, "abs.g2;s1.p8;s2.p11;s4.p1", "claim",
          "Keeping excess sulfur from the H2S-based plasma out of the film is what allows crystalline growth; adding H2 to the "
          "plasma feed gas achieves this (two key factors: remote H2S plasma with reactive radicals and low-energy ions, and "
          "enough H2 next to H2S, since excess S blocks crystallization).", mentions="H2S;H2")
F(K, "abs.g3;s1.p8;s4.p1", "claim",
  "MoSx films were characterized systematically (composition, crystallinity, growth, morphology, electrical behaviour) over "
  "a wide window of deposition conditions, showing the interplay of temperature and H2 flow ratio.")
F(K, "abs.g3;s1.p8", "claim", "Film properties were related to the behaviour of field-effect transistors made from MoS2 deposited "
  "at 100 °C.", mentions="100 °C;FET")
F(K, "abs.g4;s1.p8;s4.p2", "claim",
  "Deposition of MoS2 on PET substrates (and the 100 °C FET channel) points to use of the process in flexible electronics and "
  "other fields needing low deposition temperatures.", mentions="PET;100 °C")
F(K, "abs.g4;s1.p8;s3.p45", "claim",
  "Composition control by tailoring the plasma chemistry is expected to hold for low-temperature plasma deposition of metal "
  "chalcogenides in general, including other PEALD sulfides and phase control of sulfides with several stoichiometries.")

# ------------------------------------------------------------------ introduction
NK("s2.h", "heading")
F(K, "s2.p1", "cited", "TMDCs have unusual electronic, optical and mechanical properties owing to their layered crystal "
  "structure, and are stable as single monolayers.", mentions="2D;ref. 1;ref. 2;ref. 3")
F(K, "s2.p1", "cited", "TMDCs are of interest for electronics, catalysis, energy storage and medicine.",
  mentions="ref. 1;ref. 3;ref. 4;ref. 5;ref. 6;ref. 7")
F(K, "s2.p1", "cited", "The TMDC family has over 30 layered MX2 materials (M a transition metal or Sn, X being S, Se or Te), from "
  "semiconductors to (semi)metals and superconductors.", mentions="ref. 1;ref. 2;ref. 8;ref. 9")
F(K, "s2.p1", "cited", "TMDC devices shown so far include FETs, photodetectors, tunneling FETs, memristors and memtransistors; "
  "semiconducting MoS2 and WS2 are studied as silicon alternatives.", mentions="refs. 10-17")
F(K, "s2.p2", "cited", "Mechanically exfoliated flakes, used in early and many current TMDC studies, cannot be scaled up.",
  mentions="ref. 3;ref. 17;ref. 18")
F(K, "s2.p2;s2.p3", "cited", "High-temperature CVD from oxide powder precursors gives high-quality TMDCs, but often struggles with "
  "large-area uniformity and thickness control, for which some fixes exist.", mentions="ref. 9;refs. 19-22;refs. 23-27")
F(K, "s2.p3", "cited", "CVD of MoS2 typically needs 600-800 °C.", quantity="deposition_temperature", value_min="600",
  value_max="800", unit="°C", data_kind="literature", method="cited", mentions="CVD;MoS2")
F(K, "s2.p4", "cited", "Back-end-of-line processing allows at most 400-500 °C.", quantity="other",
  label_as_printed="maximum allowed processing temperature", value_min="400", value_max="500", unit="°C",
  data_kind="literature", method="cited", mentions="ref. 28")
F(K, "s2.p4", "cited", "Metal-organic and halide CVD and ALD processes give polycrystalline MoS2 at 200-500 °C.",
  quantity="deposition_temperature", value_min="200", value_max="500", unit="°C", data_kind="literature", method="cited",
  mentions="refs. 32-34;refs. 35-38")
F(K, "s2.p4;s2.p8", "cited", "TMDCs are promising for flexible electronics and displays, e.g. as thin-film transistors and as "
  "gas, light, biomolecule and pressure sensors; BEOL integration aims at memory and photodetectors on Si chips.",
  mentions="refs. 29-31;refs. 39-41")
NK("s2.p5;s2.p6;s2.p7", "received/revised/published dates")
F(K, "s2.p8", "cited", "Typical polymer flexible substrates tolerate maximum temperatures of 100 to 400 °C.", quantity="other",
  label_as_printed="highest temperature substrates withstand", value_min="100", value_max="400", unit="°C",
  data_kind="literature", method="cited", mentions="refs. 41-43")
F(K, "s2.p8", "cited", "PET should stay below 100-150 °C to avoid deforming.", quantity="other",
  label_as_printed="temperature limit of PET", value_min="100", value_max="150", unit="°C", data_kind="literature",
  method="cited", mentions="PET;ref. 42")
F(K, "s2.p8", "cited", "The few known TMDC ALD processes at or below 150 °C give amorphous films with too little conductivity "
  "and mobility for electronics.", mentions="150 °C;ref. 36;refs. 44-46")
F(K, "s2.p8", "cited", "For plastic substrates only film transfer or assembly from flake dispersions (printing, spin coating) is "
  "available now.", mentions="ref. 47;ref. 48")
F(K, "s2.p8", "claim", "Direct deposition is preferable for simplicity, cost, film quality and uniformity, and coverage of 3D "
  "structures.", mentions="3D")
F(K, "s2.p9", "cited", "PEALD reaches high film quality at low temperature through reactive radicals and low-energy ions that "
  "add energy without heating the substrate much; being self-limiting it offers uniformity, thickness control, "
  "reproducibility and scalability.", mentions="ref. 49;ref. 50;ref. 51")
F(K, "s2.p9", "cited", "The group's earlier PEALD processes for MoS2 and WS2 work well at 300 °C and above, but below 300 °C give "
  "amorphous, S-rich, highly resistive films.", quantity="deposition_temperature", value="300", censor="", unit="°C",
  data_kind="literature", method="cited", mentions="ref. 36;ref. 52;MoS2;WS2")
F(K, "s2.p9", "cited", "Highly conductive TiS2 has been grown by PEALD down to 150 °C.", quantity="deposition_temperature",
  value_min="150", unit="°C", data_kind="literature", method="cited", mentions="ref. 53;TiS2")
F(K, "s2.p10;s2.p11", "claim", "As far as the authors know, 100 °C is the lowest temperature reported for MoS2 from any chemical "
  "vapour-phase method.", mentions="100 °C;MoS2")
C_H = F(K, "s2.p11;s3.p49;s4.p1", "claim",
        "Besides stoichiometry and crystallinity, hydrogen in the feed gas also changes growth, morphology and electrical "
        "properties, together with deposition temperature (studied in detail for MoSx).", mentions="H2;MoSx;Figure S19;Section S14")
F(K, "s2.p11", "claim", "The key process parameters discussed apply to other plasma-made chalcogenides too, not only MoS2.")

# ------------------------------------------------------------------ results: concept and crystallinity
NK("s3.h", "heading")
F(K, "s3.p1;fig1a;fig1.cap", "definition",
  "One ALD cycle: Mo(NtBu)2(NMe2)2 vapour pulse that reacts until surface sites are used up, purge, H2S/H2/Ar remote plasma "
  "exposure, second purge; cycles are repeated to the target thickness.", mentions="Figure 1a;Mo(NtBu)2(NMe2)2;H2S/H2/Ar plasma")
F(K, "s3.p1", "claim", "The plasma strips the ligands of the adsorbed Mo precursor and delivers S to the film.")
F(K, "s3.p1", "claim", "Saturation curves show the process is self-limiting.", mentions="Figure S1")
F(K, "s3.p2", "claim", "Plasma feed gas composition and deposition temperature together decide whether amorphous S-rich or "
  "polycrystalline MoS2 grows.")
F(K, "s3.p2", "definition", "a-MoS2+x denotes amorphous S-rich films and c-MoS2 polycrystalline MoS2 films.",
  mentions="a-MoS2+x;c-MoS2")
F(K, "eq1;s3.p2;s3.p3;tab2.r0c0", "definition", "The H2 flow ratio is the H2 fraction of the H2 plus H2S flow in the plasma "
  "feed gas.", mentions="eq 1;H2 flow ratio")
F(K, "eq1;s3.p3", "model", "Eq. 1 relates the H2 flow ratio to the H2 and H2S flow rates in sccm: ratio = H2/(H2 + H2S).",
  mentions="eq 1")
F(K, "s3.p3", "claim", "Absolute flows and other process parameters are given in the Experimental Section.")

# s3.p4 / Fig. 1a
F(K, "s3.p4;fig1a;fig1.cap", "observation",
  "At 150 °C, ratios of 0 to 0.50 give a-MoS2+x with weak, broad Raman bands resembling amorphous MoS3.",
  method="raman", mentions="150 °C;a-MoS3;ref. 54;Figure 1a")
F(K, "s3.p4;fig1a", "observation",
  "At 150 °C polycrystalline MoS2 needs a ratio of at least 0.65, seen from the appearance of the MoS2 E1g (E2g1) and A1g "
  "Raman modes.", quantity="other", qualifiers="gas=H2", label_as_printed="H2 flow ratio at the crystallinity onset",
  value="0.65", data_kind="measured", method="raman", mentions="150 °C;Figure 1a")
F(K, "s3.p4;fig1a", "claim", "Raman peak intensity rises from ratio 0.65 to 0.80, suggesting better crystallinity.",
  mentions="0.65;0.80")
F(K, "s3.p4", "observation", "XRD confirms crystalline films for ratios of 0.65 and above.", method="xrd",
  mentions="0.65;Figure S2")

# s3.p5 / Fig. 1b
F(K, "s3.p5;fig1b;fig1.cap", "claim", "With the optimized ratio 0.80, crystalline MoS2 grows at 150 °C with sub-monolayer "
  "thickness control.", mentions="0.80;150 °C;Figure 1b")
F(K, "s3.p5;fig1b", "observation", "With more cycles the E2g1 peak moves to lower and A1g to higher wavenumber (dashed lines in "
  "the panel), confirming thickness control.", method="raman", mentions="E1g;A1g;ref. 55;ref. 56")
F(K, "s3.p5", "claim", "Thickness can be set by cycle number from about one monolayer to tens of nm.")
F(K, "s3.p5", "observation", "Most H2-flow-ratio comparisons use films 10-20 nm thick made with 100-140 cycles.",
  quantity="film_thickness", value_min="10", value_max="20", unit="nm", data_kind="measured", method="ellipsometry",
  mentions="100-140 ALD cycles")

# s3.p6 / Fig. 1c, 1d
F(K, "s3.p6;fig1c;fig1.cap;s5.p11", "observation", "Thickness standard deviation over a 4\" wafer is 3.3% (film mean 5.1 ± 0.2 nm "
  "printed on the map).", quantity="film_thickness", qualifiers="stat=relative_sd;between=position;n=not_stated", value="3.3", unit="%", data_kind="measured",
  method="ellipsometry", mentions="4\";σ = 3.3%;Figure 1c")
F(K, "s3.p6", "observation", "MoS2 films about 1-5 nm thick are smooth and continuous with no visible holes by AFM.",
  method="afm", mentions="Figures S3;S4")
F(K, "s3.p6;fig1d;fig1.cap", "setting", "MoS2 is deposited on PET at the lowest temperature, 100 °C, with optimized ratio 0.80.",
  quantity="deposition_temperature", value="100", unit="°C", data_kind="chosen input", mentions="PET;0.80;Figure 1d")
F(K, "s3.p6", "observation", "About 5 nm MoS2 on PET has a resistivity of 0.3 Ω cm.", quantity="resistivity", value="0.3",
  unit="Ω cm", data_kind="measured", method="electrical", mentions="PET;5 nm")
F(K, "s3.p6;fig1d", "observation", "The 5 nm MoS2 films on PET are highly transparent and their resistivity does not change after "
  "repeated bending by hand.", method="photograph", mentions="PET")

# s3.p7 / Fig. 2
F(K, "s3.p7;fig2;fig2.cap", "claim", "The lowest H2 flow ratio giving crystalline films rises as deposition temperature falls.",
  mentions="Figure 2;Figure S5")
F(K, "s3.p7;fig2", "observation", "At 300 °C and above even ratio 0.20 gives c-MoS2.", quantity="other",
  qualifiers="gas=H2", label_as_printed="H2 flow ratio at the crystallinity onset", value_max="0.20", data_kind="measured", method="raman",
  mentions="≥300 °C;0.20")
F(K, "s3.p7;fig2", "observation", "At 100 °C ratio 0.80 is needed for c-MoS2.", quantity="other",
  qualifiers="gas=H2", label_as_printed="H2 flow ratio at the crystallinity onset", value="0.80", data_kind="measured", method="raman",
  mentions="100 °C;0.80")
F(K, "s3.p7;s3.p13", "observation", "There is also an upper limit: XPS shows ratio 0.94 is too high, though Raman does not reveal it.",
  method="xps", mentions="0.94")

# s3.p8 - s3.p10 / Fig. 3
F(K, "s3.p8;fig3a;fig3.cap;s5.p18", "setting", "TEM specimen: a sub-5 nm c-MoS2 film grown at 100 °C with ratio 0.80 and 50 cycles.",
  quantity="cycle_number", value="50", data_kind="chosen input", method="tem", mentions="100 °C;0.80;50 ALD cycles;Figure 3a")
F(K, "s3.p8;s3.p9;fig3a", "observation", "The 100 °C film looks fully crystallized and is built of nanocrystallites 4-5 "
  "monolayers thick.", quantity="other", label_as_printed="monolayer thick", value_min="4", value_max="5",
  data_kind="measured", method="tem", mentions="100 °C;Figure 3a")
F(K, "s3.p9;fig3a", "observation", "Nanocrystallites of the 100 °C film are about 5-10 nm wide.", quantity="crystallite_size",
  label_as_printed="nanocrystallite width", value_min="5", value_max="10", unit="nm", data_kind="measured", method="tem",
  mentions="100 °C;Figure 3a")
F(K, "s3.p10", "observation", "Surface of the 100 °C TEM film is fairly smooth, RMS roughness 0.75 nm by AFM.", quantity="roughness",
  label_as_printed="root-mean-square roughness", value="0.75", unit="nm", data_kind="measured", method="afm",
  mentions="100 °C")
F(K, "s3.p10;fig3b;fig3.cap", "setting", "Reference TEM film grown at 350 °C with ratio 0.20 (60 cycles, reference condition after "
  "Sharma et al.).", quantity="deposition_temperature", value="350", unit="°C", data_kind="chosen input",
  mentions="350 °C;H2 flow ratio 0.20;60 ALD cycles;ref. 36;Figure 3b")
F(K, "s3.p10;fig3b", "observation", "The 5-6 monolayer film made at 350 °C has a microstructure and crystallinity much like the "
  "100 °C film.", quantity="other", label_as_printed="monolayer film", value_min="5", value_max="6", data_kind="measured",
  method="tem", mentions="350 °C;100 °C;Figure 3b")

# ------------------------------------------------------------------ composition
F(K, "s3.p11;fig4;fig4.cap;s3.x2", "claim", "S/Mo atomic ratio and crystallinity are strongly correlated.", mentions="Figure 4")
F(K, "s3.p11;fig4", "observation", "Most crystalline films have XPS compositions between MoS1.8 and MoS2.3, close to MoS2.",
  quantity="composition", qualifiers="element=S", label_as_printed="S/Mo", value_min="1.8", value_max="2.3",
  data_kind="measured", method="xps", mentions="c-MoS2")
F(K, "s3.p11", "claim", "Right stoichiometry and chemical environment from plasma chemistry control let MoS2 crystallize at "
  "temperatures down to 100 °C.", mentions="100 °C")
F(K, "s3.p11;fig4", "observation", "Amorphous films grown at 150 °C or more hold excess S, MoS2.5 to MoS3.6.",
  quantity="composition", qualifiers="element=S", label_as_printed="S/Mo", value_min="2.5", value_max="3.6",
  data_kind="measured", method="xps", mentions="≥150 °C;a-MoS2+x")
F(K, "s3.p11;fig4", "observation", "Within the amorphous region, raising temperature at fixed ratio lowers S/Mo.",
  method="xps")
F(K, "s3.p11", "claim", "The lower S/Mo at higher temperature is likely due to changed reaction mechanisms and lower stability of "
  "S-rich compositions and their S2- and S2 2- species at higher temperature.", mentions="Section S14")
F(K, "s3.p11;s3.p12", "claim", "Stoichiometry and crystallinity come from the interplay of plasma chemistry (set by the H2 flow ratio) and "
  "surface chemistry (set by ratio, deposition temperature and film crystallinity).")
F(K, "s3.p13;fig4", "observation", "At 50-100 °C some films made with high ratios are near MoS2 composition yet amorphous.",
  method="xps", mentions="50-100 °C")
F(K, "s3.p13", "claim", "Those low-temperature exceptions may come from too little thermal energy to crystallize and an S "
  "environment more like a-MoS2+x than MoS2.")
F(K, "s3.p13;fig4", "observation", "Ratio 0.94 gives a low S/Mo although Raman shows MoS2 peaks.", method="xps",
  mentions="0.94")
F(K, "s3.p13", "claim", "The 0.94 films hold both c-MoS2 and metallic Mo, so too high a ratio can starve the film of S and/or "
  "etch S away.", mentions="0.94")

# XPS chemistry (s3.p14 - s3.p20, Fig. 5)
F(K, "s3.p14;fig5a;fig5b;fig5.cap;s3.x3", "observation", "XPS core levels of 150 °C films grown with several ratios and 140 cycles are "
  "shown as examples; other temperatures are in Table S1.", method="xps", mentions="150 °C;140 ALD cycles;Table S1;Figure 5;H2 flow ratios")
F(K, "s3.p14;fig5a", "observation", "In the Mo 3d region most Mo is Mo4+, assigned to MoSx.", method="xps",
  mentions="Mo4+ (MoSx);Figure 5a")
F(K, "s3.p14;s3.p15;fig5a", "observation", "All samples show two weaker doublets at higher binding energy: the highest is Mo6+ "
  "(MoO3) from oxidation in air after deposition, the middle one Mo5+ (MoOySx), an intermediate oxidation product.",
  quantity="phase", qualifiers="species=MoO3", value_text="detected", data_kind="measured", method="xps", mentions="Mo6+ (MoO3);Mo5+ (MoOxSy);ref. 57;ref. 58;ref. 59")
F(K, "s3.p15;fig5a", "observation", "c-MoS2 films need an extra weak doublet below Mo4+, labelled Mo(4-δ)+ and assigned to more "
  "metallic Mo at crystal edges, metastable 1T' MoS2 or MoS2-x subsulfide.", method="xps",
  mentions="Mo(4-δ)+;ref. 60;ref. 61;ref. 62")
for be, lab in (("228.9", "Mo(4-δ)+"), ("229.6", "Mo4+"), ("231.1", "Mo5+"), ("232.9", "Mo6+")):
    F(K, "s3.p16;fig5a", "observation", f"Mo 3d5/2 binding energy of the {lab} component of the ratio 0.80 c-MoS2 film is {be} eV.",
      quantity="binding_energy", qualifiers="element=Mo", label_as_printed="Mo 3d5/2 BE", value=be, unit="eV", data_kind="fit",
      method="xps", mentions=f"{lab};0.80")
F(K, "s3.p16", "cited", "Average literature Mo 3d5/2 binding energy of MoS2 is 229.3 ± 0.5 eV.", quantity="binding_energy",
  qualifiers="element=Mo", label_as_printed="Mo 3d5/2 BE", value="229.3", unit="eV", data_kind="literature", method="cited",
  mentions="MoS2;ref. 63")
F(K, "s3.p16", "cited", "Average literature Mo 3d5/2 binding energy of MoO3 is 232.7 ± 0.3 eV.", quantity="binding_energy",
  qualifiers="element=Mo", label_as_printed="Mo 3d5/2 BE", value="232.7", unit="eV", data_kind="literature", method="cited",
  mentions="MoO3;ref. 63")
F(K, "s3.p16", "observation", "Measured binding energies vary slightly with deposition conditions.", method="xps",
  mentions="Section S5")
F(K, "s3.p16;fig5a", "observation", "At ratio 0.94 an intense doublet below Mo4+ appears, assigned to metallic Mo.",
  quantity="phase", qualifiers="species=Mo", value_text="detected", data_kind="measured", method="xps", mentions="0.94;Mo")
F(K, "s3.p17;fig5a", "observation", "Two S 2s singlets overlapping Mo 3d are included in the fit.", method="xps",
  mentions="S 2s")
F(K, "s3.p17;fig5b", "observation", "S 2p of the ratio 0.80 crystalline film fits fairly well with one S2- doublet of MoS2 at "
  "S 2p3/2 162.4 eV.", quantity="binding_energy", qualifiers="element=S", label_as_printed="S 2p3/2 BE", value="162.4",
  unit="eV", data_kind="fit", method="xps", mentions="0.80;S2-;Figure 5b")
F(K, "s3.p17;fig5b", "observation", "A weak doublet about 0.9 eV below the main one improves the fit; it is assigned to "
  "electron-rich S2- on metallic edges, in 1T' MoS2 or in MoS2-x subsulfide.", quantity="binding_energy",
  qualifiers="element=S", label_as_printed="BE shift below S2-", value="0.9", unit="eV", data_kind="fit", method="xps",
  mentions="S2- (e- rich);ref. 61;ref. 62")
F(K, "s3.p18;fig5b", "observation", "A doublet above the S2- one is strongest for the low-ratio amorphous films.", method="xps",
  mentions="S2 2- (bridging) & S2- (apical)")
F(K, "s3.p18;fig5b", "observation", "In the a-MoS3.0 film (ratio 0.50) the two S 2p3/2 components sit at 161.9 eV, with roughly "
  "equal area to the other.", quantity="binding_energy", qualifiers="element=S", label_as_printed="S 2p3/2 BE", value="161.9",
  unit="eV", data_kind="fit", method="xps", mentions="a-MoS3,0;0.50;lower BE doublet")
F(K, "s3.p18;fig5b", "observation", "In the ratio 0.50 amorphous film the higher S 2p3/2 component is at 163.1 eV; no "
  "electron-rich S2- is seen in this or other amorphous samples.", quantity="binding_energy", qualifiers="element=S",
  label_as_printed="S 2p3/2 BE", value="163.1", unit="eV", data_kind="fit", method="xps",
  mentions="a-MoS3,0;0.50;higher BE doublet")
F(K, "s3.p18", "cited", "Amorphous MoS3 contains sulfur in at least four chemical environments.", mentions="a-MoS3;ref. 64;ref. 65")
F(K, "s3.p18;fig5a;fig5b", "definition", "Lower-BE S doublet = MoS2-like S2- plus terminal S2 2-; higher-BE doublet = bridging "
  "S2 2- plus apical S2-.", mentions="S2- & S2 2- (terminal);S2 2- (bridging) & S2- (apical)")
F(K, "s3.p18;s3.p20", "claim", "The varied S species and their overlapping binding energies prevent an exact determination of S "
  "species or S oxidation states.")
F(K, "s3.p20", "observation", "The area ratio of the higher-BE to the lower-BE doublet grows for more S-rich material.",
  method="xps")
F(K, "s3.p20", "model", "With Mo as Mo4+ in both MoS2 and MoS3, charge neutrality requires more S2 2- in place of S2- the more "
  "S-rich MoS2+x is, so the lower- and higher-BE doublets mainly reflect S2- and S2 2-.", mentions="Mo4+;MoS2+x;MoS3")

# Table 1 (and s3.p19, s3.p21)
T1EV = "tab1.cap;s3.x4"
F(K, "s3.p19;tab1.cap;s3.p21", "observation", "Table 1 films are about 50 nm thick, grown at 150 °C on glassy carbon with ratios "
  "0.20 (amorphous), 0.65 and 0.80 (crystalline), analysed for H by ERD and for Mo, S, C, N, O by RBS.",
  quantity="film_thickness", value="50", unit="nm", data_kind="measured", method="rbs",
  mentions="~50 nm;150 °C;0.20;0.65;0.80;glassy carbon;Table 1")
F(K, "s3.p19", "observation", "Detection limit of C in these films is about 7 at.%.", quantity="other",
  label_as_printed="detection limit (dl.) for C", value="7", unit="at. %", data_kind="measured", method="rbs",
  mentions="dl.;glassy carbon")
F(K, "s3.p19;s5.p17;tab1.r0c3", "definition", "Film mass density is computed from RBS areal atom densities and SE thicknesses.",
  mentions="RBS;SE;density (g/cm^3)")
F(K, "s3.p19", "cited", "Bulk MoS2 density is 5.06 g/cm3.", quantity="film_density", qualifiers="reference=bulk;species=MoS2", value="5.06", unit="g/cm3",
  data_kind="literature", method="cited", mentions="ref. 66")
F(K, "s3.p19;tab1.cap", "setting", "The Table 1 films (RBS, ERD) are grown on a glassy carbon substrate.", quantity="substrate", value_text="glassy carbon",
  data_kind="chosen input", mentions="glassy carbon;Table 1")
T1 = {"0.20": [("3.7", "0.1"), ("3.4", "0.2"), "3.2", ("6.4", "0.5"), ("0.5", "0.2"), ("0.8", "0.2")],
      "0.65": [("2.1", "0.1"), ("2.1", "0.1"), "4.0", ("11.7", "0.9"), ("1.5", "0.4"), ("0.5", "0.1")],
      "0.80": [("1.8", "0.1"), ("1.9", "0.1"), "3.1", ("22", "2"), ("1.0", "0.3"), ("5", "2")]}
H_TXT = {"0.20": "6", "0.65": "12", "0.80": "22"}
TAB1 = {}
for i, (r, row) in enumerate(T1.items(), start=1):
    rc = f"tab1.r{i}c0"
    (a, ua), (b, ub), dens, (h, uh), (n, un), (o, uo) = row
    ev0 = ";".join(x for x in [T1EV] if x)
    F(K, f"tab1.r{i}c1;{rc};tab1.r0c1;tab1.r0c0;{ev0};s3.p21", "observation",
      f"RBS S/Mo ratio of the ratio {r} film is {a} ± {ua}.", quantity="composition", qualifiers="element=S",
      label_as_printed="S/Mo ratio (RBS)", value=a, data_kind="measured", method="rbs", mentions=f"{hr(r)};S/Mo ratio (RBS)")
    F(K, f"tab1.r{i}c2;{rc};tab1.r0c2;{ev0}", "observation", f"XPS S/Mo ratio of the ratio {r} Table 1 film is {b} ± {ub}.",
      quantity="composition", qualifiers="element=S", label_as_printed="S/Mo ratio (XPS)", value=b, data_kind="measured",
      method="xps", mentions=f"{hr(r)};S/Mo ratio (XPS)")
    TAB1[(r, "dens")] = F(K, f"tab1.r{i}c3;{rc};tab1.r0c3;{ev0}", "derived", f"Mass density of the ratio {r} film is {dens} g/cm^3.",
                          quantity="film_density", value=dens, unit="g/cm^3", data_kind="calculated", method="calculation",
                          mentions=f"{hr(r)};density (g/cm^3)")
    hev = f"tab1.r{i}c4;{rc};tab1.r0c4;{ev0};s3.p21"
    TAB1[(r, "H")] = F(K, hev, "observation",
                       f"H content of the ratio {r} film is {h} ± {uh} at.% by ERD (text: {H_TXT[r]} at.%).",
                       quantity="composition", qualifiers="element=H", label_as_printed="H (at. %)", value=h, unit="at. %",
                       data_kind="measured", method="rbs", mentions=f"{hr(r)};H (at. %);ERD")
    F(K, f"tab1.r{i}c5;{rc};tab1.r0c5;{ev0};s3.p19", "observation", f"C content of the ratio {r} film is below the detection limit.",
      quantity="composition", qualifiers="element=C", label_as_printed="C (at. %)", censor="<dl", unit="at. %",
      data_kind="measured", method="rbs", mentions=f"{hr(r)};C (at. %);<dl.")
    F(K, f"tab1.r{i}c6;{rc};tab1.r0c6;{ev0}", "observation", f"N content of the ratio {r} film is {n} ± {un} at.%.",
      quantity="composition", qualifiers="element=N", label_as_printed="N (at. %)", value=n, unit="at. %",
      data_kind="measured", method="rbs", mentions=f"{hr(r)};N (at. %)")
    F(K, f"tab1.r{i}c7;{rc};tab1.r0c7;{ev0}" + (";s3.p21" if r == "0.80" else ""), "observation",
      f"O content of the ratio {r} film is {o} ± {uo} at.%.", quantity="composition", qualifiers="element=O",
      label_as_printed="O (at. %)", value=o, unit="at. %", data_kind="measured", method="rbs",
      mentions=f"{hr(r)};O (at. %)")
F(K, "s3.p21", "observation", "RBS S/Mo ratios agree closely with XPS for the three 150 °C films.", method="rbs",
  mentions="150 °C;0.20;0.65;0.80;Table 1")
F(K, "s3.p21", "observation", "Nitrogen left from precursor ligands is low, 0.5-1.5 at.%.", quantity="composition",
  qualifiers="element=N", label_as_printed="N content", value_min="0.5", value_max="1.5", unit="at. %",
  data_kind="measured", method="rbs")
F(K, "s3.p21", "observation", "Oxygen is under 1 at.% in the ratio 0.20 and 0.65 films.", quantity="composition",
  qualifiers="element=O", label_as_printed="O content", value="1", censor="<", unit="at. %", data_kind="measured",
  method="rbs", mentions="0.20;0.65")
F(K, "s3.p21", "claim", "Higher O at ratio 0.80 is likely surface oxidation helped by a rough morphology with many easily "
  "oxidized edge sites, also hinted by the low mass density.", mentions="0.80")
F(K, "s3.p21", "claim", "Hydrogen is the main impurity and clearly increases with the ratio, even if roughness and surface "
  "oxidation may inflate the last value.", mentions="0.20;0.65;0.80")

# ------------------------------------------------------------------ morphology
F(K, "s3.p22", "claim", "Morphology matters: roughness can raise resistivity by carrier scattering, hinder integration in "
  "nanoscale devices, and tells about growth mechanisms.")
F(K, "s3.p22;fig6a;fig6.cap;s3.x5", "observation", "Morphology comparisons use relatively thick films, 8-20 nm, grown with 140 cycles.",
  quantity="film_thickness", value_min="8", value_max="20", unit="nm", data_kind="measured", method="ellipsometry",
  mentions="140 ALD cycles;Figure 6a")
F(K, "s3.p22", "observation", "Thinner films are smoother and differ less between conditions.", method="sem")
F(K, "s3.p22;fig6a", "observation", "At 150 °C, amorphous films from ratios 0-0.50 are very smooth by SEM and AFM.", method="sem",
  mentions="150 °C;0;0.50;Figure 6a")
F(K, "s3.p22;fig6a", "observation", "Raising the ratio to 0.65 gives crystalline but still smooth films.", method="sem",
  mentions="0.65")
F(K, "s3.p22;fig6a", "observation", "At ratio 0.80 films are rough, made of out-of-plane oriented MoS2 crystallites ('fins').",
  method="sem", mentions="0.80;fins")
F(K, "s3.p22;fig6a", "observation", "At the highest ratio 0.94 the areal fin density drops, possibly because part of the film is "
  "metallic Mo.", method="sem", mentions="0.94")
F(K, "s3.p22", "observation", "Other temperatures behave alike: amorphous films are smooth at every temperature, crystalline films "
  "just past the onset are fairly smooth, and roughness grows with ratio up to the roughest at 0.80.", method="sem",
  mentions="Figure S8;0.80")
F(K, "s3.p22", "claim", "The minimum ratio for crystalline (rougher) films falls as deposition temperature rises.")
F(K, "s3.p22", "claim", "A higher ratio appears to promote fin formation and/or growth.")
F(K, "s3.p23", "cited", "Out-of-plane fins are common in (PE)ALD and CVD multilayer TMDC films.", mentions="ref. 35;ref. 67")
F(K, "s3.p23;s3.p24", "cited", "In PEALD MoS2 and WS2 the fins sit (almost only) at grain boundaries, so grain size and boundary "
  "density control fin density.", mentions="ref. 36;ref. 52;ref. 67;MoS2;WS2")
F(K, "s3.p24", "model", "Possible fin mechanism 1: two crystallites grow sideways until they meet, then the top layer(s) of one or "
  "both bend upward into a fin.")
F(K, "s3.p24", "model", "Possible fin mechanism 2: metal precursor adsorbs at a reactive grain-boundary or defect site and nucleates "
  "a new, randomly oriented grain.")
F(K, "s3.p25", "model", "Fin edges carry more reactive sites than basal planes, so fins grow vertically faster than new basal "
  "layers form, giving the usual change from smooth to fin-dominated films with thickness.")
F(K, "s3.p25", "claim", "In this process the ratio may tune edge reactivity by changing S and S-H coverage on the edges.",
  mentions="S-H;H2")
F(K, "s3.p25", "cited", "DFT for WS2 showed that lower S coverage and higher S-H coverage of edges favour W precursor "
  "adsorption.", method="cited", mentions="ref. 52;DFT;WS2")
F(K, "s3.p25", "claim", "A similar effect is expected here because Mo(NtBu)2(NMe2)2 has the same ligands as the W precursor and "
  "Mo and W are chemically alike.", mentions="Mo(NtBu)2(NMe2)2")
F(K, "s3.p26", "claim", "Thick ratio-0.80 films are very rough, so fins form and grow easily under those conditions.",
  mentions="0.80")
F(K, "s3.p26;fig6b;fig6.cap;s3.x5", "observation", "With ratio 0.65 at 150 °C crystalline films stay smooth even at about 50 nm "
  "(500 cycles).", quantity="film_thickness", value="50", unit="nm", data_kind="measured", method="tem",
  mentions="0.65;150 °C;~50 nm;500 ALD cycles;Figure 6b")
F(K, "s3.p26;fig6b", "observation", "By TEM, in the first ~5 nm next to the SiO2 the MoS2 grains lie about parallel to the substrate; "
  "above that crystallites are randomly oriented, yet the film is smooth and dense.", quantity="other",
  label_as_printed="parallel-oriented layer thickness", value="5", unit="nm", data_kind="measured", method="tem",
  mentions="Parallel to substrate;Randomly oriented;SiO2")
F(K, "s3.p26", "claim", "S-rich (H-poor) plasma may hinder fin growth compared with S-poor (H-rich) plasma.")
F(K, "s3.p26", "claim", "The ratio at which fin growth sets in depends on temperature: at higher temperature a lower ratio "
  "suffices to activate edges, perhaps through precursor adsorption kinetics or easier excess S at low temperature.")
F(K, "s3.p26", "claim", "Excess surface S at low temperature fits the need for a higher ratio to reach MoS2 stoichiometry and "
  "crystallinity at lower temperatures.", mentions="MoS2")

# ------------------------------------------------------------------ growth
F(K, "s3.p27;fig7a;fig7.cap;s3.x6", "observation", "At 150 °C, in situ SE shows amorphous films from ratios 0 to 0.50 thickening "
  "linearly with cycles.", method="ellipsometry", mentions="H2 flow ratio 0;0.50;150 °C;Figure 7a;Figure S10")
F(K, "s3.p27;fig7a", "observation", "Crystalline films just past onset (0.65, 150 °C) also grow roughly linearly but with a "
  "higher GPC than amorphous ones.", method="ellipsometry", mentions="0.65;150 °C")
F(K, "s3.p27;s3.p28;fig7a", "observation", "Ratio 0.80 gives clearly non-linear growth with GPC rising as cycles accumulate.",
  method="ellipsometry", mentions="0.80")
F(K, "s3.p28;fig7a", "observation", "Ratio 0.94 lowers the GPC again.", method="ellipsometry", mentions="0.94")
F(K, "s3.p28", "claim", "The lower GPC at 0.94 may reflect a mixed MoS2/Mo film whose phases differ in density, mechanism and "
  "morphology.", mentions="MoS2;Mo")
F(K, "s3.p29;fig7b;fig7.cap;s3.x6", "observation", "GPC averaged over the first 100 cycles increases from ratio 0 to 0.80 at every "
  "temperature.", quantity="growth_per_cycle", data_kind="measured", method="ellipsometry",
  mentions="first 100 cycles;H2 flow ratio 0;0.80;Figure 7b;Figure S11")
F(K, "s3.p29;s3.p30;s3.p31", "claim", "Two factors explain the GPC trend: more adsorption sites for the Mo precursor at higher "
  "ratio, and more surface area and reactive fin edges at higher ratio and temperature.")
MO1 = F(K, "s3.p30", "observation", "By RBS, Mo atoms deposited per cycle are 0.6 at/nm2/cycle at ratio 0.20 and 150 °C.",
        quantity="atoms_per_cycle", qualifiers="element=Mo", label_as_printed="Mo atoms deposited per cycle", value="0.6",
        unit="at/nm2/cycle", data_kind="measured", method="rbs", mentions="0.20;150 °C")
MO2 = F(K, "s3.p30", "observation", "By RBS, Mo atoms deposited per cycle rise to 1.6 at/nm2/cycle at ratio 0.65 and 150 °C, more "
        "than double, with little change in morphology.", quantity="atoms_per_cycle", qualifiers="element=Mo",
        label_as_printed="Mo atoms deposited per cycle", value="1.6", unit="at/nm2/cycle", data_kind="measured", method="rbs",
        mentions="0.65;150 °C")
F(K, "s3.p30", "cited", "DFT for WS2 PEALD found that the metal precursor can adsorb on -SH sites.", method="cited",
  mentions="ref. 52;-SH;WS2")
F(K, "s3.p30;s3.p42", "claim", "The density of -SH (thiol) groups, and with it the GPC and doping, should increase with the H2 "
  "flow ratio, as observed.", mentions="-SH;H2")
F(K, "s3.p31", "claim", "Fin formation and growth make GPC increase with cycle number.")
F(K, "s3.p31", "cited", "GPC rising with thickness was seen for crystalline MoS2 at ≥300 °C with ratio 0.20 and in other "
  "crystalline TMDC ALD processes.", mentions="≥300 °C;0.20;ref. 36;ref. 52;ref. 53;ref. 68")
F(K, "s3.p32", "observation", "The most Mo per cycle, 2.2 at/nm2/cycle, is deposited at ratio 0.80.", quantity="atoms_per_cycle",
  qualifiers="element=Mo", label_as_printed="Mo atoms deposited per cycle", value="2.2", unit="at/nm2/cycle",
  data_kind="measured", method="rbs", mentions="0.80")
F(K, "s3.p32", "claim", "Optical GPC hides density and stoichiometry changes, but SE with RBS and XPS indicates that Mo precursor "
  "adsorption density dominates the GPC trends.", inputs=[MO1, MO2])
F(K, "s3.p32", "observation", "At 250 °C ratios 0.35 (amorphous) and 0.50 (crystalline) give almost equal GPC.",
  quantity="growth_per_cycle", data_kind="measured", method="ellipsometry", mentions="0.35;0.50;250 °C;Figure S11")
F(K, "s3.p32", "claim", "Crystallization itself changes GPC at most moderately, less than ratio and morphology do.")

# ------------------------------------------------------------------ electrical
F(K, "s3.p33;fig8;fig8.cap", "claim", "The H2 flow ratio tunes resistivity over several orders of magnitude.", mentions="Figure 8")
F(K, "s3.p33;fig8", "observation", "At a given temperature and fixed cycle count, higher ratio gives lower resistivity.",
  quantity="resistivity", data_kind="measured", method="electrical", mentions="Figure 8;Table S2")
F(K, "s3.p34", "observation", "For amorphous films resistivity follows stoichiometry.", method="electrical")
F(K, "s3.p34;fig8", "observation", "The most S-rich films (S/Mo ≥ 3) exceed the four-point probe detection limit, of order 1000 Ω cm "
  "for 10 nm films.", quantity="resistivity", value="1000", censor=">", unit="Ω cm", data_kind="measured",
  method="electrical", mentions="S/Mo ≥ 3;10 nm;>dl")
F(K, "s3.p34", "observation", "Lower S/Mo, from higher ratio and/or temperature, lowers resistivity.", method="electrical")
F(K, "s3.p34;fig8", "observation", "Lowest amorphous-film resistivity is 2 Ω cm, for MoS2.2 grown at 100 °C with ratio 0.65.",
  quantity="resistivity", value="2", unit="Ω cm", data_kind="measured", method="electrical",
  mentions="MoS2.2;100 °C;0.65")
F(K, "s3.p35;fig8", "observation", "For crystalline films, raising the ratio at a given temperature lowers resistivity.",
  method="electrical")
F(K, "s3.p35;s4.p1;fig8", "observation", "Lowest c-MoS2 resistivities, about 0.1-1 Ω cm, are reached at ratio 0.80.",
  quantity="resistivity", qualifiers="stat=minimum;between=runs;n=not_stated", value_min="0.1", value_max="1", unit="Ω cm", data_kind="measured", method="electrical",
  mentions="0.80;c-MoS2")
F(K, "s3.p35;fig8", "observation", "Crystalline film grown at 300 °C with ratio 0.20 has 15 Ω cm.", quantity="resistivity",
  value="15", unit="Ω cm", data_kind="measured", method="electrical", mentions="300 °C;0.20")
F(K, "s3.p35;fig8", "observation", "Crystalline film grown at 450 °C with ratio 0.20 has 220 Ω cm.", quantity="resistivity",
  value="220", unit="Ω cm", data_kind="measured", method="electrical", mentions="450 °C;0.20")
F(K, "s3.p35;fig8", "observation", "Ratio 0.94 gives resistivities down to 4 mΩ cm, likely owing to a highly conductive Mo phase.",
  quantity="resistivity", qualifiers="stat=minimum;between=runs;n=not_stated", value="4", unit="mΩ cm", data_kind="measured", method="electrical", mentions="0.94")
F(K, "s3.p35;fig8", "observation", "c-MoS2 resistivity is lowest at the lowest temperatures, 100-150 °C.", method="electrical",
  mentions="100-150 °C")
HALL = F(K, "s3.p36;s3.p37;s4.p1;s4.p2", "observation", "c-MoS2 films grown with ratios 0.50-0.80 at 100-250 °C show p-type "
         "conduction with hole concentrations of order 10^21 cm^-3 by AC Hall.", quantity="carrier_concentration",
         label_as_printed="majority carrier (hole) concentration", value="1e21", unit="cm-3", data_kind="measured",
         method="electrical", mentions="0.50-0.80;100-250 °C;Section S10")
F(K, "s3.p36;s3.p37", "observation", "Hall mobilities of these low-temperature c-MoS2 films are modest, 0.001-0.01 (cm^2/Vs).",
  quantity="carrier_mobility", label_as_printed="Hall mobility", value_min="0.001", value_max="0.01", unit="cm2 V-1 s-1",
  data_kind="measured", method="electrical", mentions="0.50-0.80;100-250 °C")
F(K, "s3.p37", "observation", "Reference c-MoS2 films from 350-450 °C with ratio 0.20 have carrier densities of order 10^17 to "
  "10^18 cm^-3.", quantity="carrier_concentration", label_as_printed="carrier density", value_min="1e17", value_max="1e18",
  unit="cm-3", data_kind="measured", method="electrical", mentions="350-450 °C;0.20;ref. 69")
F(K, "s3.p37", "observation", "Those reference films have similar or slightly higher mobilities, of order 0.01 (cm^2/Vs), "
  "here and in Vandalon et al.", quantity="carrier_mobility", label_as_printed="mobility", value="0.01", unit="cm2 V-1 s-1",
  data_kind="measured", method="electrical", mentions="350-450 °C;0.20;ref. 69")
F(K, "s3.p37", "claim", "Similar mobilities at 150 and 450 °C indicate comparable electronic quality.", mentions="150 °C;450 °C")
F(K, "s3.p37", "cited", "MoS2 doped with 10 at.% Al at 450 °C has carrier concentrations and mobilities comparable to the "
  "low-temperature c-MoS2 here.", mentions="10 at. % Al;450 °C;ref. 69")
F(K, "s3.p37", "claim", "The process offers an easy way to make strongly p-doped MoS2 at low temperature.")
F(K, "s3.p38", "observation", "At 450 °C, raising the ratio from 0.20 to 0.80 lifts carrier concentration 3 orders of "
  "magnitude, from 10^17 to 10^20 cm^-3.", quantity="carrier_concentration", label_as_printed="carrier concentration",
  method="electrical", mentions="450 °C;0.20;0.80")
F(K, "s3.p38", "observation", "Ratio 0.94 gives extremely high carrier concentrations, of order 10^22 cm^-3, consistent with "
  "partial Mo content.", quantity="carrier_concentration", label_as_printed="carrier concentration", value="1e22", unit="cm-3",
  data_kind="measured", method="electrical", mentions="0.94")
F(K, "s3.p38", "cited", "Mo thin films have carrier concentrations of 5 × 10^22 to 1 × 10^23 cm^-3.", quantity="carrier_concentration",
  label_as_printed="carrier concentration", value_min="5e22", value_max="1e23", unit="cm-3", data_kind="literature",
  method="cited", mentions="Mo;ref. 70;ref. 71")
for r_, v_ in (("0.20", "1e17"), ("0.80", "1e20")):                      # the two ends of s3.p38's change are two films' values (P14)
    F(K, "s3.p38", "observation", f"At 450 °C and ratio {r_} the carrier concentration is of order {v_.replace('1e', '10^')} cm^-3.",
      quantity="carrier_concentration", label_as_printed="carrier concentration", value=v_, unit="cm-3", data_kind="measured", method="electrical",
      mentions=f"450 °C;{r_}")
F(K, "s3.p39", "observation", "c-MoS2 films are near stoichiometric, MoS1.8 to MoS2.2 by XPS.", quantity="composition",
  qualifiers="element=S", label_as_printed="S/Mo", value_min="1.8", value_max="2.2", data_kind="measured", method="xps",
  mentions="c-MoS2")
F(K, "s3.p39;s4.p2", "claim", "The high hole concentrations are attributed mainly to H incorporated from the plasma, H being the "
  "main impurity by RBS.", inputs=[HALL])
F(K, "s3.p39", "derived", "12 at.% H in the 150 °C, ratio 0.65 film corresponds to 6 × 10^21 H atoms/cm3, three times its measured "
  "carrier concentration.", quantity="other", label_as_printed="H atoms/cm^3", value="6e21", unit="cm-3",
  data_kind="calculated", method="calculation", mentions="12 at. %;150 °C;0.65", inputs=[TAB1[("0.65", "H")]])
F(K, "s3.p39", "claim", "N and O are far less abundant than the carriers; grain boundaries and S or Mo vacancies may also add "
  "carriers.")
F(K, "s3.p40", "cited", "Literature (mostly DFT) places H in MoS2 at S vacancies (n- or p-type), on S as thiol groups (n-type), "
  "interstitially within the Mo plane (n-type), as neutral intercalated H2, or replacing S to form n-type MoSH.",
  mentions="ref. 72;ref. 73;ref. 74;ref. 75;ref. 76;ref. 77")
F(K, "s3.p40", "observation", "Annealing up to 300 °C causes no major change in electrical properties.",
  method="electrical", mentions="Section S12")
F(K, "s3.p40", "setting", "Annealing at temperatures up to 300 °C (Section S12).", quantity="annealing_temperature",
  label_as_printed="annealing temperature", value_max="300", unit="°C", data_kind="chosen input", mentions="Section S12")
F(K, "s3.p41", "observation", "Infrared and Raman measurements found no evidence of Mo-H or S-H bonds, which does not prove they "
  "are absent.", method="raman", mentions="Mo-H;S-H")
F(K, "s3.p41;s3.p42", "claim", "Given the process and the S deficiency of crystalline high-ratio films, H most likely sits at S "
  "vacancies or in thiol groups.")
F(K, "s3.p43", "observation", "FET channel: about 5 nm film grown at 100 °C with ratio 0.80.", quantity="film_thickness",
  value="5", unit="nm", data_kind="measured", mentions="100 °C;0.80;FET")
F(K, "s3.p43", "setting", "Reference FET film of similar thickness grown at 350 °C with ratio 0.20.",
  quantity="deposition_temperature", value="350", unit="°C", data_kind="chosen input", mentions="350 °C;0.20;FET")
F(K, "s3.p43", "observation", "Both FETs conduct p-type with on/off current ratios of about 3-4.", quantity="other",
  label_as_printed="current on/off ratio", value_min="3", value_max="4", data_kind="measured", method="electrical",
  mentions="100 °C;350 °C;Figure S13")
F(K, "s3.p43", "cited", "Few p-type 2D semiconductors are known, unlike n-type ones.", mentions="ref. 78")
F(K, "s3.p43", "observation", "Output current of the 100 °C FET is over ten times that of the 350 °C reference, matching its lower "
  "resistivity and higher carrier concentration.", method="electrical", mentions="100 °C;350 °C")
F(K, "s3.p43", "observation", "The 100 °C FET contacts show non-linear I-V (a Schottky barrier); the 350 °C contacts are near "
  "Ohmic.", method="electrical", mentions="100 °C;350 °C")
F(K, "s3.p44", "observation", "Device cross-sections show an amorphous MoS2/Ni interface layer about 2-3 nm thick for the 100 °C "
  "sample.", quantity="film_thickness", qualifiers="position=interface", label_as_printed="interface layer thickness",
  value_min="2", value_max="3", unit="nm", data_kind="measured", method="tem", mentions="100 °C;Ni;Figure S14")
F(K, "s3.p44", "observation", "The 350 °C device has a thinner interface layer, about 1 nm.", quantity="film_thickness",
  qualifiers="position=interface", label_as_printed="interface layer thickness", value="1", unit="nm", data_kind="measured",
  method="tem", mentions="350 °C;Figure S14")
F(K, "s3.p44", "claim", "The thicker interface of the 100 °C sample may explain its non-linear I-V.", mentions="100 °C")
F(K, "s3.p44", "observation", "Films made at 100 °C start oxidizing when annealed in air at only 150 °C.",
  mentions="100 °C;Sections S11;S12")
F(K, "s3.p44", "claim", "Further work is needed on carrier density control, contact/MoS2 interfaces and MoS2 stability during "
  "processing for low-temperature PEALD MoS2.", mentions="MoS2")
F(K, "s3.p44", "setting", "Annealing in air at 150 °C, the lowest temperature at which the 100 °C films oxidized (Sections S11, S12).",
  quantity="annealing_temperature", qualifiers="gas=air", label_as_printed="annealing temperature in air", value="150", unit="°C",
  data_kind="chosen input", mentions="100 °C;Sections S11;S12")

# ------------------------------------------------------------------ other TMDCs
F(K, "s3.p45", "claim", "The H2 flow ratio is a key parameter for low-temperature PEALD of TMDCs generally, allowing crystalline "
  "films at lower temperatures than before.", mentions="H2")
F(K, "s3.p45;s5.p8", "cited", "The group's published WS2 and TiS2 PEALD processes use H2S/Ar plasma without H2 (ratio 0) and give "
  "highly S-rich films at low temperature.", quantity="plasma_gas_ratio", qualifiers="gas=H2", label_as_printed=R, value="0",
  data_kind="literature", method="cited", mentions="ref. 52;ref. 53;H2S/Ar")
F(K, "s3.p46", "cited", "The tungsten sulfide process gives crystalline WS2 only from 300 °C.", quantity="deposition_temperature",
  value="300", unit="°C", data_kind="literature", method="cited", mentions="ref. 52;ref. 67;ref. 79;WS2")
F(K, "s3.p46;fig9a", "observation", "Without H2 at 150 °C the W sulfide films are highly S-rich (WS4.0 by XPS), amorphous and "
  "highly resistive, like the analogous MoS2 films.", quantity="composition", qualifiers="element=S",
  label_as_printed="S/W", value="4.0", data_kind="measured", method="xps", mentions="WS4.0;150 °C;0")
F(K, "s3.p46;fig9a;fig9.cap;s3.x7", "observation", "Ratio 0.80 at 150 °C yields crystalline WS2.1.", quantity="composition",
  qualifiers="element=S", label_as_printed="S/W", value="2.1", data_kind="measured", method="xps",
  mentions="WS2.1;0.80;150 °C;Figure 9a;Section S13")
F(K, "s3.p46", "observation", "The crystalline WS2.1 film has a resistivity of 4 Ω cm.", quantity="resistivity", value="4",
  unit="Ω cm", data_kind="measured", method="electrical", mentions="WS2.1;0.80;150 °C")
F(K, "s3.p46;s3.p47", "claim", "MoS2 and WS2 behave alike since Mo and W share a group and both processes use analogous "
  "M(NtBu)2(NMe2)2 precursors.", mentions="M = Mo, W")
F(K, "s3.p48", "cited", "The only reported TiS2 PEALD process is crystalline from 150 °C, but gives amorphous TiS3 at 100 °C.",
  quantity="deposition_temperature", value="150", unit="°C", data_kind="literature", method="cited",
  mentions="ref. 53;TiS3;100 °C")
F(K, "s3.p48", "cited", "A thermal TiS2 ALD process with the same Ti(NMe2)4 precursor grows crystalline films down to 100 °C.",
  quantity="deposition_temperature", value_min="100", unit="°C", data_kind="literature", method="cited",
  mentions="ref. 80;ref. 81;Ti(NMe2)4")
F(K, "s3.p48", "claim", "So the PEALD failure at 100 °C stems from excess S rather than lack of energy for crystallization.")
F(K, "s3.p48;fig9b;fig9.cap;s3.x7", "observation", "With ratio 0.50 at 100 °C, TiS2 has better crystallinity and stoichiometry than "
  "the reported thermal process.", method="raman", mentions="0.50;100 °C;Figure 9b;Table S7")
F(K, "s3.p48", "observation", "For TiS2 the ratio 0.80 used for MoS2 and WS2 is too high and gives S-poor films (not shown).",
  method="xps", mentions="0.80")

# ------------------------------------------------------------------ role of hydrogen
F(K, "s3.p50;s3.p51", "observation", "OES of the H2S/H2/Ar plasma suggests S-containing species S, S+, S2, SH+ and H2S+; atomic H "
  "(H radicals) is the main reactive hydrogen species.", mentions="ref. 85;Figure S20")
F(K, "s3.p51", "claim", "OES can hardly tell sulfur species apart, so changes in plasma species with ratio are hard to infer.")
F(K, "s3.p51;s5.p4", "setting", "Combined H2S plus H2 flow is held at 10 sccm (except at ratio 0.94).", quantity="gas_flow_rate",
  value="10", unit="sccm", data_kind="chosen input", mentions="H2S;H2;0.94")
F(K, "s3.p51", "observation", "With rising ratio, atomic H emission grows while reactive S species emission falls, consistent with "
  "the flow changes.", mentions="Figure S21")
F(K, "s3.p51", "claim", "H2S itself contains H, so some atomic H forms even with no added H2.")
F(K, "s3.p52", "claim", "A higher atomic H to reactive S ratio may either keep excess S out or add a reaction that removes S.")
F(K, "s3.p52", "setting", "Extra step test: a separate H2 gas or H2 plasma step follows the H2S/H2/Ar plasma (ratio 0.20) at "
  "150 °C, conditions that otherwise give a-MoS3.4.", quantity="plasma_gas_ratio", qualifiers="gas=H2", label_as_printed=R,
  value="0.20", data_kind="chosen input", mentions="0.20;150 °C;a-MoS3.4")
F(K, "s3.p52", "observation", "The H2 plasma step removes the extra S and yields c-MoS2, whereas H2 gas changes neither "
  "stoichiometry nor crystallinity.", mentions="Table S8")
F(K, "s3.p52", "claim", "H radicals can convert a-MoS2+x into c-MoS2 under these ALD conditions, though prevention of S uptake by "
  "a higher ratio is not excluded.", mentions="a-MoS2+x;c-MoS2")
F(K, "s3.p53", "observation", "Lowering the H2S flow reduces S incorporation like raising the ratio; crystalline films form at "
  "250 °C with no H2 added.", quantity="crystallinity", value_text="crystalline", data_kind="measured",
  mentions="250 °C;Figure S22a")
F(K, "s3.p53", "observation", "At lower temperature such as 150 °C, H2 addition is still needed for c-MoS2.",
  mentions="150 °C;Figure S22b")
F(K, "s3.p53", "observation", "At fixed ratio, more H2S flow increases S incorporation.")
F(K, "s3.p53", "claim", "Ratio, absolute H2 and H2S flows and deposition temperature must all be considered to get the wanted "
  "film properties.")

# ------------------------------------------------------------------ conclusions
NK("s4.h", "heading")
F(K, "s4.p1", "claim", "Polycrystalline films reach compositions MoS2.2, TiS2.2 and WS2.2 (conclusions; the WS2 section "
  "gives WS2.1).", mentions="MoS2.2;TiS2.2;WS2.2")
F(K, "s4.p1", "claim", "Quantifying temperature and ratio effects opens further development of low-temperature PEALD of "
  "crystalline chalcogenides with controlled stoichiometry.")

# ------------------------------------------------------------------ experimental
NK("s5.h", "heading")
F(K, "s5.p1", "setting", "Reactor, with a remote inductively coupled plasma source at 13.56 MHz.", quantity="reactor_type",
  value_text="Oxford Instruments FlexAL PEALD", data_kind="chosen input", mentions="FlexAL;13.56 MHz;ICP")
F(K, "s5.p1", "setting", "A turbomolecular pump gives a base pressure of 10^-6 Torr.", quantity="other",
  label_as_printed="base pressure", value="1e-6", unit="Torr", data_kind="chosen input")
F(K, "s5.p1", "setting", "Reactor walls heat to at most 150 °C; for 50-150 °C depositions wall and substrate are set equal.",
  quantity="other", label_as_printed="wall temperature", value_max="150", unit="°C", data_kind="chosen input",
  mentions="50-150 °C")
F(K, "s5.p1", "setting", "For 200-450 °C the substrate table is heated to the set value with walls kept at 150 °C.",
  quantity="deposition_temperature", value_min="200", value_max="450", unit="°C", qualifiers="kind=set_point",
  data_kind="chosen input", mentions="200-450 °C;150 °C")
F(K, "s5.p1", "definition", "Temperatures quoted are table set points; actual substrate temperature is lower at high set points "
  "because of poor thermal contact at low pressure, negligibly so at 150 °C and below.", mentions="ref. 86;150 °C")
F(K, "s5.p2", "setting", "Substrate of most depositions (Siegert Wafer), chosen for optical contrast.", quantity="substrate",
  qualifiers="kind=default", value_text="Si(100) with 450 nm thermal SiO2", data_kind="chosen input", mentions="Si (100);450 nm SiO2")
F(K, "s5.p2;s5.p13", "setting", "Substrate of some Hall samples, which needs no cutting since leakage to Si via side deposits "
  "is impossible; others on SiO2/Si.", quantity="substrate", qualifiers="kind=option", value_text="fused SiO2", data_kind="chosen input", mentions="fused SiO2")
F(K, "s5.p2", "setting", "Substrate of the transistors.", quantity="substrate", value_text="Si with 90 nm thermal SiO2",
  data_kind="chosen input", mentions="90 nm SiO2")
F(K, "s5.p2", "setting", "Plastic substrate (DuPont Teijin Films), 125 µm thick.", quantity="substrate",
  value_text="Melinex ST504 PET foil", data_kind="chosen input", mentions="PET;125 μm")
F(K, "s5.p2", "observation", "Uncoated and ALD Al2O3-coated PET (50 cycles of AlMe3/H2O) give similar results.",
  mentions="Al2O3;50 ALD cycles;AlMe3;H2O")
F(K, "s5.p3", "setting", "Substrates of 1 × 1 to 3 × 3 cm2 are used as received (cut, blown with N2) on an 8\" carrier wafer.",
  quantity="other", label_as_printed="substrate size", value_text="1 × 1 to 3 × 3 cm2", data_kind="chosen input", mentions="8\" carrier wafer")
F(K, "s5.p3", "setting", "The load lock is pumped below 10^-2 Torr before transfer.", quantity="other",
  label_as_printed="load lock pressure", value="1e-2", censor="<", unit="Torr", data_kind="chosen input")
F(K, "s5.p3", "setting", "Before deposition substrates equilibrate for 10 min at 200 mTorr with Ar flowing.", quantity="other",
  label_as_printed="equilibration time", value="10", unit="min", data_kind="chosen input", mentions="Ar;200 mTorr")
F(K, "s5.p4", "setting", "The MoS2 process follows Sharma et al., changing mainly the plasma feed gas composition.",
  mentions="ref. 36")
F(K, "s5.p4;s5.p5;tab2.cap", "setting", "Total H2S + H2 + Ar flow through the ICP tube during the plasma is 50 sccm in every case.",
  quantity="gas_flow_rate", value="50", unit="sccm", qualifiers="step=plasma", data_kind="chosen input",
  mentions="ICP tube;Table 2")
F(K, "s5.p4;s5.p6", "setting", "Chamber pressure during the plasma is about 6 mTorr, with the pressure valve open.",
  quantity="process_pressure", qualifiers="step=plasma", value="6", unit="mTorr", data_kind="measured", method="process_monitor")
for g, p in (("H2S", "99.5"), ("H2", "99.999"), ("Ar", "99.999")):
    F(K, "s5.p4", "setting", f"{g} gas purity is {p}% (Linde Gas).", quantity="precursor_purity", qualifiers=f"species={g}",
      value=p, unit="%", data_kind="chosen input", mentions=g)
F(K, "s5.p4", "cited", "In Sharma et al. the H2S and H2 flows were really 8 and 2 sccm (the article had them swapped), i.e. "
  "ratio 0.20.", quantity="plasma_gas_ratio", qualifiers="gas=H2", label_as_printed=R, value="0.20", data_kind="literature",
  method="cited", mentions="ref. 36;8 sccm;2 sccm")
# Table 2
T2 = [("0", "10", "0", "40"), ("0.20", "8", "2", "40"), ("0.35", "6.5", "3.5", "40"), ("0.50", "5", "5", "40"),
      ("0.65", "3.5", "6.5", "40"), ("0.80", "2", "8", "40"), ("0.94", "2", "30", "18")]
for i, (r, h2s, h2, ar) in enumerate(T2, start=1):
    for j, (g, v) in enumerate((("H2S", h2s), ("H2", h2), ("Ar", ar)), start=1):
        F(K, f"tab2.r{i}c{j};tab2.r{i}c0;tab2.r0c{j};tab2.cap", "setting", f"At {R} {r} the {g} flow through the ICP tube is "
          f"{v} sccm.", quantity="gas_flow_rate", qualifiers=f"step=plasma;gas={g};ratio={r}", value=v, unit="sccm",
          data_kind="chosen input", mentions=f"{hr(r)};{g} flow rate (sccm)")
F(K, "s5.p6", "definition", "Cycle steps: (1) Mo precursor dose, (2) purge, (3) H2S/H2/Ar plasma, (4) purge, i.e. four main steps.")
F(K, "s5.p6", "setting", "Mo(NtBu)2(NMe2)2 dose lasts 6 s.", quantity="pulse_time", qualifiers="step=reactant_A", value="6",
  unit="s", data_kind="chosen input")
F(K, "s5.p6", "setting", "First purge is 10 s: 6 s with 300 sccm Ar into the chamber and 4 s of pumping with no flow.",
  quantity="purge_time", qualifiers="step=purge_A", value="10", unit="s", data_kind="chosen input", mentions="6 s;4 s")
F(K, "s5.p6", "setting", "Purge Ar flow is 300 sccm.", quantity="gas_flow_rate", qualifiers="gas=Ar", value="300", unit="sccm",
  data_kind="chosen input", mentions="purge")
F(K, "s5.p6", "setting", "Plasma step lasts 20 s.", quantity="pulse_time", qualifiers="step=plasma", value="20", unit="s",
  data_kind="chosen input")
F(K, "s5.p6", "setting", "ICP plasma power is 100 W.", quantity="other", label_as_printed="ICP power", value="100", unit="W",
  data_kind="chosen input")
F(K, "s5.p6", "setting", "Second purge is 6 s with 300 sccm Ar.", quantity="purge_time", qualifiers="step=purge_B", value="6",
  unit="s", data_kind="chosen input", mentions="300 sccm Ar")
F(K, "s5.p6", "setting", "Mo precursor purity is 98% (Strem Chemicals).", quantity="precursor_purity",
  value="98", unit="%", data_kind="chosen input",
  mentions="Mo(NtBu)2(NMe2)2")
F(K, "s5.p6", "setting", "Precursor canister is heated to 50 °C.", quantity="source_temperature", value="50", unit="°C",
  data_kind="chosen input", mentions="Mo(NtBu)2(NMe2)2")
F(K, "s5.p6", "setting", "Precursor vapour is carried by 50 sccm Ar.", quantity="gas_flow_rate", qualifiers="gas=Ar;step=reactant_A",
  value="50", unit="sccm", data_kind="chosen input", mentions="carrier")
F(K, "s5.p6", "setting", "Delivery lines are held at 70 °C against condensation.", quantity="other",
  label_as_printed="delivery line temperature", value="70", unit="°C", data_kind="chosen input")
F(K, "s5.p6", "setting", "Pressure and gas-flow stabilization steps of 4 s and 5 s precede the precursor and plasma pulses.",
  quantity="other", label_as_printed="stabilization steps", value_text="4 s and 5 s", unit="s", data_kind="chosen input")
F(K, "s5.p6", "setting", "One full ALD cycle takes 51 s.", quantity="cycle_time", value="51", unit="s", data_kind="chosen input")
F(K, "s5.p6", "setting", "Chamber pressure is controlled at 200 mTorr during the precursor pulse.", quantity="process_pressure",
  qualifiers="step=reactant_A;kind=set_point", value="200", unit="mTorr", data_kind="chosen input")
for n, t in (("100", "450 °C"), ("120", "50 °C, 300 °C and 350 °C"), ("140", "100-250 °C")):
    F(K, "s5.p7", "setting", f"Unless noted, depositions at {t} use {n} ALD cycles.", quantity="cycle_number", value=n,
      data_kind="chosen input", mentions=t)
F(K, "s5.p7", "setting", "Cycle numbers were chosen to give about 10 nm at ratio 0.20 at each temperature (no such data for "
  "50-100 °C).", quantity="film_thickness", qualifiers="kind=target", value="10", unit="nm", data_kind="chosen input", mentions="0.20;50-100 °C")
F(K, "s5.p7", "observation", "SE showed the H2S/H2/Ar plasma alone deposits no S, and the Mo precursor does not condense, so the "
  "lowest temperatures stay in the ALD regime.", method="ellipsometry", mentions="ref. 87")
F(K, "s5.p8", "setting", "WS2 and TiS2 deposition procedures, with the plasma feed gas (ratio) as the only change; a thermal TiSx "
  "recipe serves for comparison.", quantity="other", label_as_printed="literature procedures",
  value_text="refs. 52 (WS2) and 53 (TiS2), H2 flow ratio changed; thermal TiSx ref. 80", mentions="ref. 52;ref. 53;ref. 80")
F(K, "s5.p8;fig9a", "setting", "WS2 is grown at 150 °C with ratio 0.80.", quantity="deposition_temperature", value="150",
  unit="°C", data_kind="chosen input", mentions="WS2;0.80")
F(K, "s5.p8;fig9b", "setting", "TiS2 is grown at 100 °C with ratio 0.50.", quantity="deposition_temperature", value="100",
  unit="°C", data_kind="chosen input", mentions="TiS2;0.50")
F(K, "s5.p9", "setting", "Thickness is followed in situ by SE with a J.A. Woollam M-2000FI (0.8-5.0 eV; fits over 0.8-4.0 eV)" \
  " or M-2000F (1.2-5.0 eV).", quantity="other", label_as_printed="spectral range", value_min="0.8", value_max="5.0",
  unit="eV", data_kind="chosen input", method="ellipsometry", mentions="M-2000FI;M-2000F")
F(K, "s5.p9", "setting", "An in situ SE measurement is usually taken every 10 cycles.", quantity="other", label_as_printed="measurement interval", value="10",
  data_kind="chosen input", method="ellipsometry")
F(K, "s5.p9", "model", "SE optical model: MoSx (B-spline)/SiO2/interlayer/Si in CompleteEASE 5.1, with software optical constants "
  "for the other layers; roughness of crystalline MoS2 as an effective medium layer with 50% void.",
  quantity="other", label_as_printed="void content", value="50", unit="%", data_kind="assumed", method="ellipsometry",
  mentions="CompleteEASE 5.1")
F(K, "s5.p9", "definition", "Reported SE thickness = dense MoSx layer plus half the roughness layer, approximating the deposited "
  "amount.")
F(K, "s5.p10", "model", "Fitting: SiO2 thickness and substrate temperature from the spectrum before cycle 1; MoSx thickness and "
  "optical constants from the last spectrum; only MoSx thickness (and roughness) for spectra in between.",
  method="ellipsometry")
F(K, "s5.p10", "definition", "Reported thicknesses average many grains of slightly different thickness and optics over a few "
  "mm2.", mentions="mm2")
F(K, "s5.p11", "setting", "Ex situ SE uses a J.A. Woollam M-2000U at 65, 75 and 85° incidence over 1.2-6.5 eV, fitting MoS2 and "
  "SiO2 thickness with fixed optical constants from in situ data.", quantity="other", label_as_printed="spectral range",
  value_min="1.2", value_max="6.5", unit="eV", data_kind="chosen input", method="ellipsometry",
  mentions="M-2000U;65;75;85°")
F(K, "s5.p11;fig1c", "setting", "Uniformity maps use a J.A. Woollam M-2000 (1.2-3.3 eV) with a mapping stage, circular pattern "
  "avoiding wafer edges; a 5 nm MoS2 film on a 4\" 450 nm SiO2/Si wafer and a bare substrate were measured.",
  quantity="other", label_as_printed="spectral range", value_min="1.2", value_max="3.3", unit="eV",
  data_kind="chosen input", method="ellipsometry", mentions="M-2000;5 nm;450 nm SiO2/Si;4\"")
F(K, "s5.p12", "setting", "Sheet resistance is measured with a four-point probe (Keithley 2400 SourceMeter, Signatone "
  "SP4-4004STRS head).", method="electrical", mentions="Keithley 2400;SP4-4004STRS")
F(K, "s5.p12", "definition", "Resistivity = sheet resistance × film thickness from in situ SE.", method="calculation")
F(K, "s5.p13", "setting", "Hall measurements: van der Pauw geometry on about 1 × 1 cm2 samples (Lakeshore 8404 HMS), AC Hall for "
  "low Hall voltages, repeated without removing the sample to estimate uncertainty.", method="electrical",
  mentions="Lakeshore 8404;1 × 1 cm2")
F(K, "s5.p14", "setting", "SEM: Zeiss Sigma at 3 kV with InLens detector.", quantity="other",
  label_as_printed="acceleration voltage", value="3", unit="kV", data_kind="chosen input", method="sem")
F(K, "s5.p14", "setting", "AFM: Bruker Dimension Icon, PeakForce Tapping ScanAsyst mode in air, probes of 0.4 N/m nominal spring "
  "constant and 2 nm tip radius.", quantity="probe_resolution", value="2", unit="nm", data_kind="chosen input", method="afm",
  mentions="ScanAsyst-air;0.4 N/m")
F(K, "s5.p14;fig6a", "definition", "Rq is the root-mean-square roughness of a 500 × 500 nm2 image after first-order flattening in "
  "Nanoscope 2.0.", method="afm", mentions="Rq;500 × 500 nm2;1st order;Nanoscope 2.0")
F(K, "s5.p15", "setting", "Raman: Renishaw inVia confocal microscope, 514 nm laser, NA 0.75 50× objective, 1800 lines/mm "
  "grating; six 10 s spectra accumulated.", quantity="other", label_as_printed="laser wavelength", value="514", unit="nm",
  data_kind="chosen input", method="raman", mentions="50×;NA 0.75;1800 lines/mm;10 s")
F(K, "s5.p15", "setting", "Laser power on the sample is about 0.6 mW (100 mW laser through a 1% ND filter).", quantity="other",
  label_as_printed="laser power", value="0.6", unit="mW", data_kind="chosen input", method="raman", mentions="100 mW;1%")
F(K, "s5.p16", "setting", "XPS: Thermo Scientific K-Alpha with monochromatic Al Kα (1486.6 eV) in a 400 µm spot, flood gun "
  "against charging.", quantity="probe_resolution", value="400", unit="µm", data_kind="chosen input", method="xps",
  mentions="Al Kα;1486.6 eV")
F(K, "s5.p16", "setting", "Spectra are referenced to adventitious C 1s at 284.8 eV.", quantity="other",
  label_as_printed="C 1s reference BE", value="284.8", unit="eV", data_kind="chosen input", method="xps", mentions="C 1s")
F(K, "s5.p16", "setting", "Pass energies: 50 eV for survey and 20 eV for high-resolution spectra.", quantity="other",
  label_as_printed="pass energy", value_text="50 eV survey, 20 eV high resolution", unit="eV", data_kind="chosen input", method="xps")
F(K, "s5.p16", "model", "Peaks are fitted in Avantage with Gaussian-Lorentzian sum components and a Shirley background.",
  method="xps")
F(K, "s5.p16", "observation", "XPS depth profiles (Ar+ at 500 eV, spectrum every 30 s) on selected samples showed no major carbon "
  "contamination.", method="xps", mentions="Ar+;500 eV;30 s")
F(K, "s5.p17", "setting", "RBS and ERD are done by Detect 99 B.V. with a 2 MeV He+ beam; RBS gives atom density, stoichiometry and "
  "non-H impurities, ERD gives hydrogen.", quantity="other", label_as_printed="He+ beam energy", value="2", unit="MeV",
  data_kind="chosen input", method="rbs", mentions="Detect 99 B.V.")
F(K, "s5.p17", "definition", "Reported RBS/ERD uncertainties include known systematic and statistical parts.", method="rbs")
F(K, "s5.p18", "setting", "TEM lamellae are prepared by FIB lift-out (FEI Helios Nanolab 600/600i) with C/Pt or SiO2 masks and "
  "imaged on a probe-corrected JEOL ARM 200F at 200 kV.", quantity="other", label_as_printed="operating voltage",
  value="200", unit="kV", data_kind="chosen input", method="tem", mentions="Helios Nanolab 600;600i;ARM 200F")
F(K, "s5.p18", "setting", "The ~50 nm 150 °C TEM sample is used as deposited; the ~5 nm 100 and 350 °C samples first get "
  "transistor channel patterning and Au/Ni metallization.", method="tem", mentions="~50 nm;150 °C;~5 nm;100 °C;350 °C")
NK("s6.h;s7.h", "heading")
NK("s7.p1;s7.p10", "front matter")
NK("s7.p2;s7.p3;s7.p4;s7.p5;s7.p6;s7.p7;s7.p8;s7.p9", "author information")
NK("s7.p11", "conflict statement")
NK("s7.p12", "acknowledgement")

# ------------------------------------------------------------------ Fig. 1
F(K, "fig1a;fig1.cap", "definition", "Schematic: high H2 flow ratio plasma holds mostly H species with few S-bearing molecules; "
  "low ratio plasma holds many S-bearing species (Mo, N, C, S, H, Ar atom legend).", method="schematic",
  mentions="High H2 flow ratio;Low H2 flow ratio")
F(K, "fig1a;fig1.cap", "observation", "Panel a plots Raman intensity (arb. units) against Raman shift 300-550 cm-1 for 150 °C films "
  "made with 140 cycles at six ratios, peaks labelled E2g1, A1g, a-MoS3 and Si.", quantity="signal_intensity",
  label_as_printed="Intensity (Arb. units)", data_kind="measured", method="raman",
  mentions="150 °C;140 ALD cycles;Raman shift (cm-1)")
for r, key in (("0.94", "s1a_R094"), ("0.80", "s1a_R080"), ("0.65", "s1a_R065")):
    s = v1_points(f"{K}:{key}")
    pts = [p for p in s["points"] if p[0] != 518.0]
    ref = P(PID, f"fig1a_{r}", pts, "v1 points, accepted in v1_points_check.csv", "Raman shift (cm-1)",
            "Intensity (Arb. units)", note="offset curve, y in v1's own scale (axis unnumbered); clipped Si point at 518 cm-1 "
            "dropped")
    F(K, "fig1a;fig1.cap", "observation", f"Raman spectrum of the {r} film: MoS2 E2g1 and A1g peaks present.",
      quantity="signal_intensity", label_as_printed="Intensity (Arb. units)", points_ref=ref, data_kind="measured", method="raman",
      mentions=f"{R}: {r}")
for r, what in (("0.50", "with only weak broad features"),
                ("0.20", "with the broad a-MoS3 bands marked by arrows"),
                ("0", "with broad weak bands")):
    F(K, "fig1a;fig1.cap", "observation", f"Raman spectrum of the {r} film, {what}, no MoS2 peaks (not digitized).",
      method="raman", mentions=f"{R}: {r}")
F(K, "fig1b;fig1.cap", "observation", "Panel b plots Raman intensity normalized to Si against Raman shift 350-430 cm-1 for 150 °C "
  "films of 10-50 cycles, with dashed lines tracking the E2g1 and A1g peaks.", quantity="signal_intensity",
  label_as_printed="Intensity (Normalized to Si)", data_kind="measured", method="raman", mentions="150 °C;Raman shift (cm-1)")
for c, th in (("50", "4.8"), ("30", "2.6"), ("20", "1.6"), ("10", "0.9")):
    extra = " (text: about 1 nm; MoS2 modes already visible)" if c == "10" else ""
    F(K, "fig1b;fig1.cap" + (";s3.p5" if c == "10" else ""), "observation",
      f"Raman spectrum of the {c}-cycle film, whose ex situ SE thickness is {th} nm{extra}.", quantity="film_thickness",
      value=th, unit="nm", data_kind="measured", method="ellipsometry", mentions=f"{c} cyc ({th} nm)")
s = v1_points(f"{K}:s1b_sub")
ref = P(PID, "fig1b_substrate", s["points"], "v1 points, accepted in v1_points_check.csv", "Raman shift (cm-1)",
        "Intensity (Normalized to Si)", note="flat substrate line; y in v1's own scale (axis unnumbered)")
F(K, "fig1b;fig1.cap", "observation", "Bare SiO2/Si substrate gives a flat line in the 350-430 cm-1 window.",
  quantity="signal_intensity", label_as_printed="Intensity (Normalized to Si)", points_ref=ref, data_kind="measured",
  method="raman", mentions="SiO2/Si")
temp("fig1c;fig1.cap", "150", "Fig. 1c wafer film", "Figure 1c")
ratio("fig1c;fig1.cap", "0.80", "Fig. 1c wafer film", "Figure 1c")
cyc("fig1c;fig1.cap", "50", "Fig. 1c wafer film", "Figure 1c")
F(K, "fig1c;fig1.cap", "observation", "Mean SE thickness over the 4\" SiO2/Si wafer is 5.1 ± 0.2 nm; colour scale runs 4.7-5.3 nm "
  "and dots mark the measured points.", quantity="film_thickness", value="5.1", unit="nm", data_kind="measured",
  method="ellipsometry", mentions="5.1±0.2 nm;4\" SiO2/Si wafer")
s = cases_points(PID, "1", "c", "thickness along the vertical diameter of the map")
ref = P(PID, "fig1c_diameter", s["points"], "points.json (read by eye from the figure image)",
        s["x_label_as_printed"], s["y_label_as_printed"], note=s["quality"])
F(K, "fig1c", "observation", "Along the vertical diameter the film is thickest (~5.3 nm) in the upper half and thinnest (~4.7-4.8 "
  "nm) at the bottom edge.", quantity="film_thickness", unit="nm", points_ref=ref, data_kind="measured",
  method="ellipsometry", mentions="Thickness (nm)")
temp("fig1d;fig1.cap", "100", "Fig. 1d PET film", "Figure 1d")
cyc("fig1d;fig1.cap", "50", "Fig. 1d PET film", "Figure 1d")
F(K, "fig1d;fig1.cap", "observation", "Photograph: an about 5 nm MoS2 film on a 15 × 15 cm transparent PET foil, bent by a gloved "
  "hand.", quantity="film_thickness", value="5", unit="nm", data_kind="measured", method="photograph",
  mentions="MoS2 @ 100 °C;15 x 15 cm PET foil;0.80")

# ------------------------------------------------------------------ Fig. 2 (two-class colour per cell)
TEMPS = [450, 350, 300, 250, 200, 150, 100, 50]
CELLS = {  # (T, ratio): (Fig. 2 class, Fig. 4 printed S/Mo)
    (450, "0.20"): ("c", "2.0"), (450, "0.80"): ("c", "1.9"),
    (350, "0.20"): ("c", "2.1"), (350, "0.50"): ("c", "2.2"), (350, "0.80"): ("c", "1.9"),
    (300, "0.20"): ("c", "2.3"),
    (250, "0"): ("a", "2.8"), (250, "0.20"): ("a", "2.7"), (250, "0.35"): ("a", "2.5"), (250, "0.50"): ("c", "2.2"),
    (250, "0.65"): ("c", "2.1"), (250, "0.80"): ("c", "1.9"), (250, "0.94"): ("c", "1.3"),
    (200, "0"): ("a", "3.1"), (200, "0.20"): ("a", "3.0"), (200, "0.50"): ("a", "2.5"), (200, "0.65"): ("c", "2.2"),
    (200, "0.80"): ("c", "1.9"), (200, "0.94"): ("c", "1.3"),
    (150, "0"): ("a", "3.6"), (150, "0.20"): ("a", "3.5"), (150, "0.50"): ("a", "3.0"), (150, "0.65"): ("c", "2.1"),
    (150, "0.80"): ("c", "1.9"), (150, "0.94"): ("c", "1.3"),
    (100, "0.20"): ("a", "4.6"), (100, "0.50"): ("a", "3.6"), (100, "0.65"): ("a", "2.2"), (100, "0.80"): ("c", "1.8"),
    (100, "0.94"): ("c", "1.4"),
    (50, "0.20"): ("a", "7.3"), (50, "0.80"): ("a", "2.0"),
}
assert len(CELLS) == 32
F(K, "fig2;fig2.cap;s3.x1", "observation", "Fig. 2 is a grid of deposition temperature (°C) against H2 flow ratio (0-0.94), each "
  "tested cell coloured by Raman crystallinity class: crystalline or amorphous.", quantity="crystallinity",
  method="raman", mentions="Tdeposition (°C);H2 flow ratio;Crystallinity")
F(K, "fig2.cap;s3.x1;fig4.cap;s3.x2;fig8.cap", "setting", "The heat-map films were deposited with 100-140 ALD cycles.",
  quantity="cycle_number", value_min="100", value_max="140", data_kind="chosen input", mentions="Figure 2;Figure 4;Figure 8")
for (t, r), (cl, _) in CELLS.items():
    F(K, "fig2", "observation", f"Fig. 2 cell at {t} °C and ratio {r}, Raman crystallinity class.", quantity="crystallinity",
      value_text="crystalline" if cl == "c" else "amorphous", method="raman", mentions=f"{r};{t} °C")

# ------------------------------------------------------------------ Fig. 3
F(K, "fig3a;fig3.cap", "observation", "Cross-sectional TEM of the film labelled 100 °C, 0.80 H2: a few-layer MoS2 band between "
  "the mask and SiO2, layers mostly parallel to the substrate.", method="tem", mentions="100 °C, 0.80 H2;Mask;MoS2;SiO2")
F(K, "fig3b;fig3.cap", "observation", "Cross-sectional TEM of the film labelled 350 °C, 0.20 H2: a similar few-layer MoS2 band "
  "(10 nm scale bar).", method="tem", mentions="350 °C, 0.20 H2;10 nm")
cyc("fig3b;fig3.cap", "60", "Fig. 3b reference film", "Figure 3b;350 °C")

# ------------------------------------------------------------------ Fig. 4 (printed S/Mo per cell)
F(K, "fig4;fig4.cap;s3.x2", "observation", "Fig. 4 maps the XPS S/Mo ratio (colour bar 0-4.0, value printed in each cell) over "
  "deposition temperature and H2 flow ratio.", quantity="composition", qualifiers="element=S",
  label_as_printed="XPS S/Mo ratio", data_kind="measured", method="xps", mentions="Tdeposition (°C);H2 flow ratio")
F(K, "fig4;fig4.cap;fig7b;fig8;s3.x2", "observation", "Dotted lines split the maps into three regions: a-MoS2+x at low ratio and "
  "temperature, c-MoS2 above/right of a stepped boundary, and Mo/c-MoS2 at ratio 0.94 right of a vertical line.",
  mentions="a-MoS2+x;c-MoS2;Mo/c-MoS2;0.94")
for (t, r), (_, smo) in CELLS.items():
    F(K, "fig4", "observation", f"Fig. 4 cell at {t} °C and ratio {r} prints S/Mo = {smo}.", quantity="composition",
      qualifiers="element=S", label_as_printed="XPS S/Mo ratio", value=smo, data_kind="measured", method="xps",
      mentions=f"{r};{t} °C")

# ------------------------------------------------------------------ Fig. 5
F(K, "fig5a;fig5.cap;s3.x3", "observation", "Panel a: XPS Mo 3d/S 2s spectra, intensity (arb. units) against binding energy "
  "238-224 eV, data with fit envelope, background and components, one per ratio at 150 °C.", quantity="signal_intensity",
  qualifiers="element=Mo", label_as_printed="Intensity (arb. units)", data_kind="measured", method="xps",
  mentions="Mo 3d / S 2s;150 °C")
for r, smo in (("0.94", "1.3"), ("0.80", "1.9"), ("0.65", "2.1"), ("0.50", "3.0"), ("0.20", "3.5")):
    s = v1_points(f"{K}:s5a_R{r.replace('.', '')}_data")
    ref = P(PID, f"fig5a_{r}", s["points"], "v1 points, accepted in v1_points_check.csv", "Binding energy (eV)",
            "Intensity (arb. units)", note="data markers; stacked curves, y in v1's own scale (axis unnumbered)")
    F(K, "fig5a;fig5.cap", "observation", f"Mo 3d/S 2s spectrum (data) of the ratio {r} film.", quantity="signal_intensity",
      qualifiers="element=Mo", label_as_printed="Intensity (arb. units)", points_ref=ref, data_kind="measured", method="xps",
      mentions=f"{r};MoS{smo}")
    F(K, "fig5a;fig5b;fig5.cap;s3.x3", "observation", f"Spectra of the ratio {r} film are labelled with composition MoS{smo}.",
      quantity="composition", qualifiers="element=S", label_as_printed="S/Mo", value=smo, data_kind="measured", method="xps",
      mentions=f"{r};MoS{smo};Figure 5")
F(K, "fig5b;fig5.cap;s3.x3", "observation", "Panel b: XPS S 2p spectra, binding energy 168-159 eV, with fitted S components; the "
  "high-BE component grows towards low ratios (not digitized).", quantity="signal_intensity", qualifiers="element=S",
  label_as_printed="Intensity (arb. units)", data_kind="measured", method="xps", mentions="S 2p;150 °C;0.94;0.80;0.65;0.50;0.20")

# ------------------------------------------------------------------ Fig. 6
F(K, "fig6a;fig6.cap;s3.x5", "observation", "SEM top views of 150 °C films (200 nm scale bar): ratios 0, 0.20 and 0.50 form the "
  "amorphous row, 0.65, 0.80 and 0.94 the crystalline row; fins are dense at 0.80 and sparse at 0.94.", method="sem",
  mentions="150 °C;Amorphous;Crystalline;200 nm")
for r, rq in (("0", "0.4"), ("0.20", "0.7"), ("0.50", "0.4"), ("0.65", "0.9"), ("0.80", "3.1"), ("0.94", "4.0")):
    F(K, "fig6a;fig6.cap", "observation", f"AFM roughness printed for the ratio {r} film is Rq = {rq} nm.", quantity="roughness",
      label_as_printed="Rq", value=rq, unit="nm", data_kind="measured", method="afm", mentions=f"{r};Rq = {rq} nm")
F(K, "fig6b;fig6.cap;s3.x5", "observation", "Cross-sectional TEM (smoothed; unfiltered in Figure S9) of the 150 °C, 0.65 H2 film "
  "with a magnified inset of randomly oriented 2D layers (20 nm and 5 nm scale bars).", method="tem",
  mentions="150 °C, 0.65 H2;Figure S9;20 nm;5 nm")

# ------------------------------------------------------------------ Fig. 7
F(K, "fig7a;fig7.cap;s3.x6", "observation", "Panel a: in situ SE thickness (nm, 0-22) against number of ALD cycles (0-140) at "
  "150 °C for six ratios.", quantity="film_thickness", unit="nm", data_kind="measured", method="ellipsometry",
  mentions="Thickness (nm);Number of ALD cycles;150 °C")
for r in ("0", "0.20", "0.50", "0.65", "0.80", "0.94"):
    s = v1_points(f"{K}:s7a_R{r.replace('.', '').ljust(3, '0')}")
    ref = P(PID, f"fig7a_{r}", s["points"], "v1 points, accepted in v1_points_check.csv",
            "Number of ALD cycles", "Thickness (nm)", note=s.get("note", ""))
    F(K, "fig7a", "observation", f"Thickness against cycles for the ratio {r} film.", quantity="film_thickness", unit="nm",
      points_ref=ref, data_kind="measured", method="ellipsometry", mentions=f"{R}: {r}")
F(K, "fig7b;fig7.cap;s3.x6", "observation", "Panel b: heat map of GPC averaged over the first 100 cycles (colour bar 0.50-1.75 "
  "Å/cycle) against deposition temperature and ratio; the cells are read against the bar, one fact each.", quantity="growth_per_cycle",
  unit="Å/cycle", method="ellipsometry", mentions="GPCaverage (Å/cycle);100 cycles")

# ------------------------------------------------------------------ Fig. 8
F(K, "fig8;fig8.cap", "observation", "Fig. 8 maps four-point probe resistivity (log colour bar 10^-3 to 10^3 Ω cm, top band >dl) "
  "over deposition temperature and ratio; the cells are read against the bar, one fact each.", quantity="resistivity", unit="Ω cm",
  method="electrical", mentions="Resistivity (Ωcm);>dl")
F(K, "fig8", "observation", "Cells drawn in the black band, above the four-point-probe limit of order 1000 Ω cm (s3.p34): 200 and 150 °C at "
  "ratio 0; 200, 150, 100 and 50 °C at 0.20; 100 °C at 0.50 (7 cells, read from colour).", quantity="resistivity", censor=">", value="1000", unit="Ω cm",
  data_kind="measured", method="electrical",
  mentions=">dl;0;0.20;0.50")

# ------------------------------------------------------------------ Fig. 9
F(K, "fig9a;fig9.cap;s3.x7", "observation", "Panel a: Raman spectra (100-550 cm-1) of WSx grown at 150 °C, peaks labelled from "
  "refs 82-84: ZA(M), LA(M), 2LA(M), E2g1(Γ), A1g(Γ) and Si.", method="raman",
  mentions="WS2 @ 150 °C;ref. 82;ref. 84")
for r, key, what in (("0.80", "s9a_R080", "WS2 phonon peaks"), ("0", "s9a_R000", "a flat line without WS2 peaks")):
    s = v1_points(f"{K}:{key}")
    ref = P(PID, f"fig9a_{r}", s["points"], "v1 points, accepted in v1_points_check.csv", "Raman shift (cm-1)",
            "Intensity (Arb. units)", note=s.get("note", ""))
    F(K, "fig9a", "observation", f"WSx spectrum at ratio {r}: {what}.", quantity="signal_intensity",
      label_as_printed="Intensity (Arb. units)", points_ref=ref, data_kind="measured", method="raman", mentions=f"{R}: {r}")
F(K, "fig9b;fig9.cap;s3.x7", "observation", "Panel b: Raman spectra of TiSx grown at 100 °C, peaks Eg, A1g, Sh and Si.",
  method="raman", mentions="TiS2 @ 100 °C")
F(K, "fig9b;fig9.cap;s3.x7", "definition", "Sh means shoulder, a TiS2 mode often seen but not conclusively identified.",
  mentions="Sh")
for r, key, what in (("0.50", "s9b_R050", "strong Eg, A1g and Sh features"),
                     ("Thermal ALD", "s9b_thermal", "weak Eg and A1g bumps")):
    s = v1_points(f"{K}:{key}")
    ref = P(PID, f"fig9b_{r.replace(' ', '_')}", s["points"], "v1 points, accepted in v1_points_check.csv",
            "Raman shift (cm-1)", "Intensity (Arb. units)", note=s.get("note", ""))
    F(K, "fig9b", "observation", f"TiSx spectrum, {r}: {what}.", quantity="signal_intensity",
      label_as_printed="Intensity (Arb. units)", points_ref=ref, data_kind="measured", method="raman", mentions=r)
F(K, "fig9b", "observation", "TiSx spectrum at ratio 0: nearly flat apart from the Si line (not digitized).", method="raman",
  mentions=f"{R}: 0")

# ------------------------------------------------------------------ the H2 flow ratio of every run as an explicit setting
# One fact per run whose ratio the paper states, cited from the elements that name the (temperature, ratio) pair: the Fig. 2
# and Fig. 4 cells plus the text, table-row and panel labels that name the pair. The 150 °C / 0.80 wafer film keeps fig1c#2
# above; the extra-H2-step run keeps s3.p52#2. Placed under their run in stage 3 (RATIO_RUN: run suffix -> fact id).
RATIO_EV = {(450, "0.20"): "s3.p35;s3.p37;s3.p38", (450, "0.80"): "s3.p38", (300, "0.20"): "s3.p35;s3.p7",
            (350, "0.20"): "s3.p10;fig3b;fig3.cap;s3.p43;s3.p37", (250, "0.35"): "s3.p32", (250, "0.50"): "s3.p32",
            (150, "0"): "s3.p4;fig1a", (150, "0.20"): "s3.p4;fig1a;tab1.r1c0;s3.p19;s3.p30;s3.p52", (150, "0.50"): "s3.p4;fig1a",
            (150, "0.65"): "s3.p4;fig1a;tab1.r2c0;s3.p19;s3.p26;s3.p30;fig6b", (150, "0.94"): "fig1a", (100, "0.65"): "s3.p34",
            (100, "0.80"): "s3.p8;fig3a;fig3.cap;fig1.cap;s3.p43;s3.p7"}
RATIO_RUN = {}
for (t, r) in CELLS:
    if (t, r) == (150, "0.80"):
        continue
    RATIO_RUN[f"T{t}_R{r}"] = F(K, "fig2;fig4" + (";" + RATIO_EV[(t, r)] if (t, r) in RATIO_EV else ""), "setting",
                                f"{t} °C, {R} {r}: H2 share of the plasma feed set to {r}", quantity="plasma_gas_ratio",
                                qualifiers="gas=H2", value=r, data_kind="chosen input", mentions=f"{r};{t} °C")
for n in ("10", "20", "30", "50"):
    RATIO_RUN[f"T150_R0.80_N{n}"] = F(K, "fig1b;s3.p5", "setting", f"150 °C, {R} 0.80, {n}-cycle film of Fig. 1b: H2 share of the "
                                      f"plasma feed set to 0.80", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0.80",
                                      data_kind="chosen input", mentions=f"0.80;150 °C;{n} cyc")
RATIO_RUN["T250_R0_lowH2S"] = F(K, "s3.p53", "setting", f"250 °C, {R} 0 with a lowered H2S flow (no H2 added, Fig. S22a): H2 share "
                                "of the plasma feed set to 0", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0",
                                data_kind="chosen input", mentions="0;250 °C;Figure S22a")
RATIO_RUN["WS2_T150_R0.80"] = F(K, "s5.p8;s3.p46;fig9a;fig9.cap", "setting", f"WS2 at 150 °C, {R} 0.80: H2 share of the plasma "
                                "feed set to 0.80", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0.80",
                                data_kind="chosen input", mentions="0.80;150 °C;WS2")
RATIO_RUN["WS2_T150_R0"] = F(K, "s3.p46;fig9a;fig9.cap", "setting", f"WSx at 150 °C, {R} 0 (no H2 in the plasma feed): H2 share of "
                             "the plasma feed set to 0", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0",
                             data_kind="chosen input", mentions="0;150 °C;WS2")
RATIO_RUN["TiS2_T100_R0.50"] = F(K, "s5.p8;s3.p48;fig9b;fig9.cap", "setting", f"TiS2 at 100 °C, {R} 0.50: H2 share of the plasma "
                                 "feed set to 0.50", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0.50",
                                 data_kind="chosen input", mentions="0.50;100 °C;TiS2")
RATIO_RUN["TiS2_T100_R0"] = F(K, "fig9b;fig9.cap", "setting", f"TiSx at 100 °C, {R} 0 (the Fig. 9b curve labelled 0): H2 share of "
                              "the plasma feed set to 0", quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0",
                              data_kind="chosen input", mentions="0;100 °C;TiS2")
RATIO_RUN["TiS2_T100_R0.80"] = F(K, "s3.p48", "setting", f"TiSx, {R} 0.80 at a temperature the paper does not state (100 °C "
                                 "inferred from the TiS2 recipe): H2 share of the plasma feed set to 0.80",
                                 quantity="plasma_gas_ratio", qualifiers="gas=H2", value="0.80", data_kind="chosen input",
                                 mentions="0.80;TiS2")

# ------------------------------------------------------------------ the deposition temperature of every heat-map row and the cycles of every Fig. 1b film
# One deposition_temperature fact per temperature group (the setting the group holds, which its label states), cited from the heat
# maps and the elements that name a pair at that temperature (RATIO_EV); one cycle_number fact per Fig. 1b film (what grp:cyc varies,
# so far stated only in the curve labels). Placed under the group or run in stage 3 (TEMP_GRP: t -> fact id; CYC_RUN: n -> fact id).
CYC_RUN = {n: cyc("fig1b;s3.p5", n, f"150 °C, {R} 0.80, {n}-cycle film of Fig. 1b", f"{n} cyc;150 °C;0.80") for n in ("10", "20", "30", "50")}
CYC_TEM = cyc("s3.p26;fig6b", "500", f"150 °C, {R} 0.65, the about 50 nm film of Fig. 6b", "500 cycles;0.65;150 °C;Figure 6b")   # the 500-cycle TEM film
# the film material (lists.MATERIALS) of the process and of the WS2 and TiS2 groups, and the structure type (planar substrates)
MAT = F(K, "abs.g1;s5.p1", "setting", "film material of the main process", quantity="material", value_text="MoS2", data_kind="chosen input",
        mentions="MoS2")
STRUCT = F(K, "s5.p2;s5.p3", "setting", "substrate form: planar pieces of wafer or foil", quantity="structure_type", value_text="planar",
           data_kind="chosen input")
MAT_W = F(K, "s5.p8;fig9a", "setting", "film material of the WS2 depositions", quantity="material", value_text="WS2", data_kind="chosen input",
          mentions="WS2")
MAT_T = F(K, "s5.p8;fig9b", "setting", "film material of the TiS2 depositions", quantity="material", value_text="TiS2", data_kind="chosen input",
          mentions="TiS2")
# the abscissa of every curve with points (x= qualifier, from the printed x label)
XQ = {"Raman shift (cm-1)": "raman_shift", "Binding energy (eV)": "binding_energy", "Number of ALD cycles": "cycle_number",
      "(wafer position, read off the map, mm)": "distance"}
import facts as C  # noqa: E402
for cf in C.facts():
    if cf["points_ref"] and "x=" not in cf["qualifiers"]:
        cf["qualifiers"] = ";".join(filter(None, [cf["qualifiers"], "x=" + XQ[C.points()[cf["points_ref"]]["x_label_as_printed"]]]))


# ------------------------------------------------------------------ the stance of every claim, from the paper's wording (lists.STANCES)
STANCE = {"abs.g1#1": "asserted", "abs.g1#2": "asserted", "abs.g2#1": "asserted", "abs.g2#2": "asserted", "abs.g3#1": "asserted",
          "abs.g3#2": "asserted", "abs.g4#1": "hedged", "abs.g4#2": "hedged", "s2.p8#5": "asserted", "s2.p10#1": "hedged", "s2.p11#1": "asserted",
          "s2.p11#2": "asserted", "s3.p1#2": "asserted", "s3.p2#1": "asserted", "s3.p3#1": "asserted", "s3.p4#3": "hedged", "s3.p5#1": "asserted",
          "s3.p5#3": "asserted", "s3.p7#1": "asserted", "s3.p11#1": "asserted", "s3.p11#3": "asserted", "s3.p11#6": "hedged", "s3.p11#7": "asserted",
          "s3.p13#2": "hedged", "s3.p13#4": "hedged", "s3.p18#6": "limitation", "s3.p21#4": "hedged", "s3.p21#5": "asserted", "s3.p22#1": "asserted",
          "s3.p22#9": "asserted", "s3.p22#10": "hedged", "s3.p25#2": "hedged", "s3.p25#4": "hedged", "s3.p26#1": "asserted", "s3.p26#4": "hedged",
          "s3.p26#5": "hedged", "s3.p26#6": "hedged", "s3.p28#2": "hedged", "s3.p29#2": "asserted", "s3.p30#4": "hedged", "s3.p31#1": "asserted",
          "s3.p32#2": "asserted", "s3.p32#4": "asserted", "s3.p33#1": "asserted", "s3.p37#3": "asserted", "s3.p37#5": "asserted",
          "s3.p39#2": "hedged", "s3.p39#4": "hedged", "s3.p41#2": "hedged", "s3.p44#3": "hedged", "s3.p44#5": "open", "s3.p45#1": "asserted",
          "s3.p46#5": "asserted", "s3.p48#3": "asserted", "s3.p51#1": "limitation", "s3.p51#4": "asserted", "s3.p52#1": "hedged",
          "s3.p52#4": "open", "s3.p53#4": "asserted", "s4.p1#2": "asserted", "s3.p1#3": "asserted", "s4.p1#1": "asserted"}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["stance"] = STANCE[cf["fact_id"].split(":", 1)[1]]          # KeyError = a claim without a stance
VARS = {   # claim id -> (cause, effect): quantity ids or mechanism:<token> (lists.MECHANISMS), blank when the claim has none
    'abs.g1#1': ('', ''),
    'abs.g1#2': ('', ''),
    'abs.g2#1': ('deposition_temperature', 'crystallinity'),
    'abs.g2#2': ('plasma_gas_ratio;mechanism:excess_S', 'crystallinity'),
    'abs.g3#1': ('deposition_temperature;plasma_gas_ratio', 'composition;crystallinity'),
    'abs.g3#2': ('', 'carrier_concentration'),
    'abs.g4#1': ('', ''),
    'abs.g4#2': ('mechanism:plasma_chemistry', 'composition'),
    's2.p8#5': ('', ''),
    's2.p10#1': ('deposition_temperature', 'crystallinity'),
    's2.p11#1': ('plasma_gas_ratio', 'growth_per_cycle;roughness;resistivity'),
    's2.p11#2': ('', ''),
    's3.p1#2': ('mechanism:plasma_chemistry', 'composition'),
    's3.p2#1': ('plasma_gas_ratio;deposition_temperature', 'crystallinity'),
    's3.p3#1': ('', ''),
    's3.p4#3': ('plasma_gas_ratio', 'crystallinity'),
    's3.p5#1': ('plasma_gas_ratio', 'crystallinity;film_thickness'),
    's3.p5#3': ('cycle_number', 'film_thickness'),
    's3.p7#1': ('deposition_temperature', 'plasma_gas_ratio'),
    's3.p11#1': ('composition', 'crystallinity'),
    's3.p11#3': ('composition;mechanism:plasma_chemistry', 'crystallinity'),
    's3.p11#6': ('deposition_temperature', 'composition'),
    's3.p11#7': ('plasma_gas_ratio;deposition_temperature;mechanism:surface_chemistry', 'composition;crystallinity'),
    's3.p13#2': ('deposition_temperature;mechanism:excess_S', 'crystallinity'),
    's3.p13#4': ('plasma_gas_ratio', 'composition'),
    's3.p18#6': ('', ''),
    's3.p21#4': ('roughness;mechanism:surface_oxidation', 'composition'),
    's3.p21#5': ('plasma_gas_ratio', 'composition'),
    's3.p22#1': ('roughness', 'resistivity'),
    's3.p22#9': ('deposition_temperature', 'plasma_gas_ratio'),
    's3.p22#10': ('plasma_gas_ratio', 'mechanism:fin_growth'),
    's3.p25#2': ('plasma_gas_ratio', 'mechanism:edge_reactivity'),
    's3.p25#4': ('', 'mechanism:fin_growth'),
    's3.p26#1': ('plasma_gas_ratio;film_thickness', 'mechanism:fin_growth;roughness'),
    's3.p26#4': ('plasma_gas_ratio', 'mechanism:fin_growth'),
    's3.p26#5': ('deposition_temperature;plasma_gas_ratio', 'mechanism:fin_growth'),
    's3.p26#6': ('deposition_temperature;mechanism:excess_S', 'composition'),
    's3.p28#2': ('plasma_gas_ratio', 'growth_per_cycle'),
    's3.p29#2': ('plasma_gas_ratio;mechanism:precursor_adsorption;mechanism:fin_growth', 'growth_per_cycle'),
    's3.p30#4': ('plasma_gas_ratio;mechanism:thiol_groups', 'growth_per_cycle;carrier_concentration'),
    's3.p31#1': ('mechanism:fin_growth;cycle_number', 'growth_per_cycle'),
    's3.p32#2': ('mechanism:precursor_adsorption', 'growth_per_cycle'),
    's3.p32#4': ('crystallinity', 'growth_per_cycle'),
    's3.p33#1': ('plasma_gas_ratio', 'resistivity'),
    's3.p37#3': ('deposition_temperature', 'carrier_mobility'),
    's3.p37#5': ('', 'carrier_concentration'),
    's3.p39#2': ('mechanism:H_incorporation', 'carrier_concentration'),
    's3.p39#4': ('mechanism:S_vacancy', 'carrier_concentration'),
    's3.p41#2': ('', 'mechanism:H_incorporation'),
    's3.p44#3': ('film_thickness', 'resistivity'),
    's3.p44#5': ('', ''),
    's3.p45#1': ('plasma_gas_ratio', 'crystallinity'),
    's3.p46#5': ('', ''),
    's3.p48#3': ('mechanism:excess_S', 'crystallinity'),
    's3.p51#1': ('', ''),
    's3.p51#4': ('', 'mechanism:plasma_chemistry'),
    's3.p52#1': ('plasma_gas_ratio;mechanism:plasma_chemistry', 'mechanism:excess_S'),
    's3.p52#4': ('mechanism:plasma_chemistry', 'crystallinity'),
    's3.p53#4': ('plasma_gas_ratio;gas_flow_rate;deposition_temperature', 'composition;crystallinity'),
    's4.p1#2': ('', ''),
    's3.p1#3': ('', ''), 's4.p1#1': ('plasma_gas_ratio', 'composition'),
}
for cf in C.facts():
    if cf["type"] == "claim":
        cf["cause"], cf["effect"] = VARS[cf["fact_id"].split(":", 1)[1]]  # KeyError = a claim without variables

# ------------------------------------------------------------------ the colour cells of Fig. 7b (GPC) and Fig. 8 (resistivity), read against their bars
# One fact per tested cell, read by eye from the colour against the bar (Fig. 7b linear 0.50-1.75 Å/cycle; Fig. 8 log 1e-3-1e3 Ω cm,
# black = above the detection limit): the statement says "read from colour" (lists.COLOUR_PANELS, check.py). Placed under the cell
# film's in situ SE and four-point-probe measurement activities in stage 3b (GPC7B, RHO8: (t, r) -> fact id).
GPC7B_VALUES = {(450, "0.20"): 1.2, (450, "0.80"): 1.65, (350, "0.20"): 0.85, (350, "0.50"): 1.25, (350, "0.80"): 1.45, (300, "0.20"): 0.85,
                (250, "0"): 0.6, (250, "0.20"): 0.65, (250, "0.35"): 0.8, (250, "0.50"): 0.95, (250, "0.65"): 1.1, (250, "0.80"): 1.3, (250, "0.94"): 0.65,
                (200, "0"): 0.6, (200, "0.20"): 0.6, (200, "0.50"): 0.85, (200, "0.65"): 1.1, (200, "0.80"): 1.3, (200, "0.94"): 0.7,
                (150, "0"): 0.7, (150, "0.20"): 0.75, (150, "0.50"): 0.9, (150, "0.65"): 1.1, (150, "0.80"): 1.3, (150, "0.94"): 0.7,
                (100, "0.20"): 1.15, (100, "0.50"): 1.15, (100, "0.65"): 1.15, (100, "0.80"): 1.4, (100, "0.94"): 0.7, (50, "0.20"): 1.7, (50, "0.80"): 1.45}
RHO8_VALUES = {(450, "0.20"): 100, (450, "0.80"): 1, (350, "0.20"): 30, (350, "0.50"): 100, (350, "0.80"): 1, (300, "0.20"): 10,
               (250, "0"): 1000, (250, "0.20"): 500, (250, "0.35"): 30, (250, "0.50"): 5, (250, "0.65"): 1, (250, "0.80"): 0.5, (250, "0.94"): 0.02,
               (200, "0"): None, (200, "0.20"): None, (200, "0.50"): 10, (200, "0.65"): 1, (200, "0.80"): 0.5, (200, "0.94"): 0.02,
               (150, "0"): None, (150, "0.20"): None, (150, "0.50"): 100, (150, "0.65"): 3, (150, "0.80"): 0.5, (150, "0.94"): 0.02,
               (100, "0.20"): None, (100, "0.50"): None, (100, "0.65"): 3, (100, "0.80"): 0.5, (100, "0.94"): 0.02, (50, "0.20"): None, (50, "0.80"): 3}
assert set(GPC7B_VALUES) == set(RHO8_VALUES) == set(CELLS)
GPC7B, RHO8 = {}, {}
for (t, r) in CELLS:
    GPC7B[(t, r)] = F(K, "fig7b", "observation", f"Fig. 7b cell at {t} °C and ratio {r}: GPC over the first 100 cycles, read from colour against the bar (about)",
                      quantity="growth_per_cycle", value=f"{GPC7B_VALUES[(t, r)]:g}", unit="Å", data_kind="measured", method="ellipsometry", mentions=f"{r};{t} °C")
    v = RHO8_VALUES[(t, r)]
    if v is None:
        RHO8[(t, r)] = F(K, "fig8", "observation", f"Fig. 8 cell at {t} °C and ratio {r}: resistivity above the four-point-probe limit of order 1000 Ω cm (black), read from colour",
                         quantity="resistivity", censor=">", value="1000", unit="Ω cm", data_kind="measured", method="electrical", mentions=f"{r};{t} °C")
    else:
        RHO8[(t, r)] = F(K, "fig8", "observation", f"Fig. 8 cell at {t} °C and ratio {r}: resistivity read from colour against the log bar (about)",
                         quantity="resistivity", value=f"{v:g}", unit="Ω cm", data_kind="measured", method="electrical", mentions=f"{r};{t} °C")

# ================================================================== stage 3: one tree (parent, links)
# A MoS2 (deposition temperature, H2 flow ratio) pair is a GROUP; a RUN under it is one physical film the paper's facts are about.
# The heat-map film of a pair was measured by Raman (Fig. 2), XPS (Fig. 4), SEM/AFM (Fig. 6a), in situ SE (Fig. 7a) and four-point
# probe (Fig. 8) without the paper saying one film served all, so each technique's facts are a film of their own; the Table 1
# glassy-carbon film, the 4" wafer, the PET foil and the TEM specimens are films the paper names. how=stated when the paper ties a
# film's facts to one film (one measurement; Rq printed on the SEM image; the TEM lamellae cut from the transistor samples, s5.p18),
# how=inferred when facts of two measurements are put on one film without the paper saying so (the statement says which). Pairs are
# grouped by temperature; the heat-map window (Figs. 2, 4, 7b, 8) is a group of its own for facts that span several temperatures.
# Other samples (Fig. 1b cycle series, extra H2 step, H2S-flow tests, annealed films, WS2 and TiS2 of Fig. 9, thermal TiS2
# reference) keep their own run rows. Parent rule: the row without which the fact would not exist; links: a claim's support, the
# same data shown twice, the pairs a fact spans.
import re  # noqa: E402
import facts as C  # noqa: E402
from facts import N  # noqa: E402

PAPER, PROC = K, f"{K}:process"
grp = lambda g: f"{K}:grp:{g}"
pair = lambda t, r: f"{K}:grp:T{t}_R{r}"                   # the group of one (temperature, ratio) pair
film = lambda t, r, kind: f"{K}:run:T{t}_R{r}:{kind}"      # one physical film of that pair
xrun = lambda s_: f"{K}:run:{s_}"
FX = {f["fact_id"]: f for f in C.facts()}
fid = lambda s_: s_ if s_.startswith(K + ":") else f"{K}:{s_}"
PARENT, LINKS = {}, {}
PAIRS = {}                      # pair group id -> (t, r, statement, label)
FILMS = {}                      # film run id -> (t, r, kind, statement, label, how)
RUNS = {}                       # other run id -> (parent, statement, label, qualifiers)

# the films of a pair: token -> (label, what the paper's facts about it are), in the order they are listed under their pair
FILM = {
    "se": ("in situ SE film", "the film followed by in situ SE (its Fig. 7a thickness curve and its growth in the text)"),
    "raman": ("Raman film", "the film classified by Raman (its Fig. 2 cell)"),
    "xps": ("XPS film", "the film measured by XPS (its Fig. 4 S/Mo cell)"),
    "afm": ("SEM/AFM film", "the film imaged by SEM with its AFM roughness Rq printed on the image (Fig. 6a) and described in the text"),
    "fpp": ("4PP film", "the film whose four-point-probe resistivity the text gives (a cell of Fig. 8)"),
    "gc": ("glassy-carbon film", "the ~50 nm film on glassy carbon of its Table 1 row, measured by RBS, ERD and XPS; the RBS Mo atoms "
           "deposited per cycle of the text (same technique, temperature and ratio) are put on this film without the paper saying "
           "they are its values"),
    "tem": ("TEM film", "the film cut into a TEM lamella"),
    "wafer": ("wafer film", "the 5 nm film on a 4\" SiO2/Si wafer mapped by ex situ SE (Fig. 1c)"),
    "pet": ("PET film", "the ~5 nm film on PET foil of Fig. 1d, photographed, bent by hand and measured by four-point probe"),
}
TEM_FILM = {  # the three TEM specimens (s5.p18): label, statement
    (150, "0.65"): ("TEM film", "the ~50 nm, 500-cycle film of Fig. 6b, cut into a TEM lamella as deposited (s5.p18)"),
    (100, "0.80"): ("TEM/FET film", "the sub-5 nm, 50-cycle film of Fig. 3a; the 100 °C TEM sample went through transistor channel "
                    "patterning and Au/Ni contacts before FIB (s5.p18), so the FET channel, its AFM roughness and the device "
                    "cross-section of Fig. S14 are this film"),
    (350, "0.20"): ("TEM/FET film", "the ~5 nm, 60-cycle reference film of Fig. 3b, patterned into the reference FET before FIB "
                    "(s5.p18), so the reference FET and its device cross-section are this film"),
}


def put(parent, *ids, links=""):
    for i in ids:
        assert fid(i) in FX, i
        assert fid(i) not in PARENT, i
        PARENT[fid(i)] = parent
        if links:
            LINKS[fid(i)] = links


def ln(i, *targets):
    LINKS[fid(i)] = ";".join(fid(t) for t in targets)


def mpair(t, r):
    """The group of one MoS2 (temperature, ratio) pair, created on first use."""
    i = pair(t, r)
    if i not in PAIRS:
        PAIRS[i] = (t, r, f"MoSx depositions at {t} °C with H2 flow ratio {r}: the films the paper made at this pair", f"{t} °C, {r} H2")
    return i


def mfilm(t, r, kind):
    """One physical film of a pair, created on first use; statement, label and how=stated|inferred follow from kind and pair."""
    i = film(t, r, kind)
    if i not in FILMS:
        mpair(t, r)
        lab, what = FILM[kind]
        how = "stated"
        if kind == "raman" and t == 150:
            what, how = ("the film measured by Raman: its Fig. 1a spectrum and its Fig. 2 cell, put on one film although the paper "
                         "cites Figure S5, not Fig. 1a, for the spectra behind the heat map"), "inferred"
        elif kind == "xps" and t == 150 and r != "0":
            what = ("the film measured by XPS: its Fig. 4 S/Mo cell, printed again as the composition of its Fig. 5 spectra, and the "
                    "binding energies the text reads from those spectra")
        elif kind == "gc":
            how = "inferred"
        elif kind == "tem":
            lab, what = TEM_FILM[(t, r)]
        FILMS[i] = (t, r, kind, f"{t} °C, H2 flow ratio {r}: {what}", f"{t} °C, {r} H2, {lab}", how)
    return i


def lk(*ids):
    return ";".join(fid(i) for i in ids)


# heat-map cells: the Fig. 2 class is the pair's Raman film, the Fig. 4 S/Mo its XPS film
CELL2, CELL4 = {}, {}
for f in C.facts():
    m = re.match(r"Fig\. ([24]) cell at (\d+) °C and ratio ([\d.]+)[ ,]", f["statement"])
    if m:
        t, r = int(m.group(2)), m.group(3)
        cells, kind = (CELL2, "raman") if m.group(1) == "2" else (CELL4, "xps")
        cells[(t, r)] = f["fact_id"]
        put(mfilm(t, r, kind), f["fact_id"])
assert len(CELL2) == len(CELL4) == 32
TEMPS = sorted({t for t, _ in CELL2}, reverse=True)
# Fig. 1a Raman curves (150 °C, 140 cycles): the Raman film of their pair; the Fig. 2 cell at that pair repeats the class they show
for i, r in (("fig1a#3", "0.94"), ("fig1a#4", "0.80"), ("fig1a#5", "0.65"), ("fig1a#6", "0.50"), ("fig1a#7", "0.20"),
             ("fig1a#8", "0")):
    put(mfilm(150, r, "raman"), i)
    ln(CELL2[(150, r)], i)
# Fig. 5 (150 °C, 140 cycles): spectra and composition labels on the XPS film; a label repeats the Fig. 4 cell of that pair
for j, r in enumerate(("0.94", "0.80", "0.65", "0.50", "0.20")):
    put(mfilm(150, r, "xps"), f"fig5a#{2 + 2 * j}")
    put(mfilm(150, r, "xps"), f"fig5a#{3 + 2 * j}", links=CELL4[(150, r)])
# Fig. 6a Rq on the SEM/AFM film and Fig. 7a growth curves on the in situ SE film (150 °C)
for j, r in enumerate(("0", "0.20", "0.50", "0.65", "0.80", "0.94")):
    put(mfilm(150, r, "afm"), f"fig6a#{2 + j}")
    put(mfilm(150, r, "se"), f"fig7a#{2 + j}")
# Table 1 (150 °C films on glassy carbon, ~50 nm): every cell on the glassy-carbon film of its row. Fig. 4 cells are a different
# film (140 cycles on SiO2/Si; 0.20 prints 3.5 against Table 1 XPS 3.4), so they are not placed under the Table 1 values.
for f in C.facts():
    m = re.match(rf"{K}:tab1\.r(\d)c\d#", f["fact_id"])
    if m:
        put(mfilm(150, {"1": "0.20", "2": "0.65", "3": "0.80"}[m.group(1)], "gc"), f["fact_id"])
# Table 2 (flows per ratio, used at every temperature) and the shared recipe, reactor, substrates and methods: the process
put(PROC, *[f for f in FX if f.startswith(f"{K}:tab2.")])
put(PROC, "eq1#2", "s3.p50#1", "s3.p51#2", "s3.p51#3",
    *[f"s5.p1#{i}" for i in (1, 2, 3, 4)], "s5.p2#1", "s5.p2#2", "s5.p2#3", "s5.p3#1", "s5.p3#2", "s5.p3#3",
    *[f"s5.p4#{i}" for i in range(1, 7)], *[f"s5.p6#{i}" for i in range(2, 15)],
    "s5.p9#1", "s5.p9#2", "s5.p9#3", "s5.p10#1", "s5.p11#1", "s5.p12#1", "s5.p13#1", "s5.p14#1", "s5.p14#2", "s5.p15#1",
    "s5.p15#2", "s5.p16#1", "s5.p16#2", "s5.p16#3", "s5.p16#4", "s5.p17#1", "s5.p18#1")
put(PROC, "s3.p1#3", links=PROC)                                            # a claim about the process (the saturation curves of Fig. S1)
put(PROC, "s4.p1#1", links=lk(grp("map"), grp("WS2"), grp("TiS2")))          # the conclusions' compositions, over the three materials
put(grp("cyc"), "s3.p6#2")                                                  # the 1-5 nm films of the cycle series are smooth and continuous (Figs. S3, S4)
put(grp("map"), "s5.p16#5")                                                 # XPS depth profiles on selected grid films
put(PROC, "s5.p18#2", links=lk(pair(150, "0.65"), pair(100, "0.80"), pair(350, "0.20")))
# the heat-map window: facts over several temperatures
put(grp("map"), "fig2#1", "fig2.cap#1", "fig4#1", "fig4#2", "fig7b#1", "fig8#1", "s3.p5#4", "s3.p7#4", "s3.p11#2", "s3.p11#4",
    "s3.p11#5", "s3.p13#3", "s3.p22#3", "s3.p22#8", "s3.p24#1", "s3.p24#2", "s3.p25#1", "s3.p29#1", "s3.p33#2", "s3.p34#1",
    "s3.p34#2", "s3.p34#3", "s3.p35#1", "s3.p35#2", "s3.p35#5", "s3.p35#6", "s3.p36#1", "s3.p36#2", "s3.p38#2", "s3.p39#1",
    "s3.p41#1", "s5.p7#4")
put(grp("map"), "fig8#2", links=lk(*[pair(t, r) for t, r in ((200, "0"), (150, "0"), (200, "0.20"), (150, "0.20"),
                                                               (100, "0.20"), (50, "0.20"), (100, "0.50"))]))
put(grp("map"), "s3.p7#2", links=lk(CELL2[(300, "0.20")], CELL2[(350, "0.20")], CELL2[(450, "0.20")]))
put(grp("map"), "s3.p13#1", links=lk(pair(50, "0.80"), pair(100, "0.65")))
put(grp("map"), "s3.p37#1", "s3.p37#2", links=lk(pair(350, "0.20"), pair(450, "0.20")))
put(grp("map"), "s5.p7#1", links=grp("T450"))
put(grp("map"), "s5.p7#2", links=lk(grp("T50"), grp("T300"), grp("T350")))
put(grp("map"), "s5.p7#3", links=lk(grp("T100"), grp("T150"), grp("T200"), grp("T250")))
# 450 °C
put(mfilm(450, "0.20", "fpp"), "s3.p35#4", "s3.p38#4")
put(mfilm(450, "0.80", "fpp"), "s3.p38#5")
put(grp("T450"), "s3.p38#1", links=lk(pair(450, "0.20"), pair(450, "0.80")))
# 350 °C: the Fig. 3b TEM reference film, patterned into the reference FET (s5.p18), at 0.20
put(mfilm(350, "0.20", "tem"), "s3.p10#3", "fig3b#1", "fig3b#2", "s3.p43#2", "s3.p44#2")
put(mfilm(350, "0.20", "tem"), "s3.p10#2", links=fid("fig3b#2"))
# 300 °C
put(mfilm(300, "0.20", "fpp"), "s3.p35#3")
# 250 °C
put(grp("T250"), "s3.p32#3", links=lk(pair(250, "0.35"), pair(250, "0.50")))
# 150 °C: the ratio series of Figs. 1a, 5, 6a, 7a and Table 1
put(grp("T150"), "fig1a#2", links=lk(*[pair(150, r) for r in ("0.94", "0.80", "0.65", "0.50", "0.20", "0")]))
put(grp("T150"), "fig5a#1", "fig5b#1", "s3.p14#1", "s3.p14#2", "s3.p14#3", "s3.p15#1", "s3.p16#7", "s3.p17#1", "s3.p18#1",
    "s3.p20#1", "s3.p20#2", "s3.p4#4", "s3.p19#2", "s3.p21#2", "fig6a#1", "s3.p22#2", "fig7a#1")
put(grp("T150"), "s3.p4#1", "s3.p22#4", "s3.p27#1", links=lk(pair(150, "0"), pair(150, "0.20"), pair(150, "0.50")))
put(grp("T150"), "s3.p4#2", links=lk(CELL2[(150, "0.65")], "fig1a#5"))
put(grp("T150"), "s3.p19#1", "s3.p19#5", "s3.p21#1", links=lk(pair(150, "0.20"), pair(150, "0.65"), pair(150, "0.80")))
put(grp("T150"), "s3.p21#3", links=lk(pair(150, "0.20"), pair(150, "0.65")))
put(mfilm(150, "0.20", "gc"), "s3.p30#1")
put(mfilm(150, "0.50", "xps"), "s3.p18#2", "s3.p18#3")
put(mfilm(150, "0.65", "afm"), "s3.p22#5")
put(mfilm(150, "0.65", "se"), "s3.p27#2")
put(mfilm(150, "0.65", "gc"), "s3.p30#2")
put(mfilm(150, "0.65", "tem"), "s3.p26#3", "fig6b#1")
put(mfilm(150, "0.65", "tem"), "s3.p26#2", links=fid("fig6b#1"))
put(mfilm(150, "0.80", "xps"), "s3.p16#1", "s3.p16#2", "s3.p16#3", "s3.p16#4", "s3.p17#2", "s3.p17#3")
put(mfilm(150, "0.80", "afm"), "s3.p22#6")
put(mfilm(150, "0.80", "se"), "s3.p27#3")
put(mfilm(150, "0.80", "gc"), "s3.p32#1")
put(mfilm(150, "0.80", "wafer"), "fig1c#1", "fig1c#3", "fig1c#4", "fig1c#5", "s5.p11#2")
put(mfilm(150, "0.80", "wafer"), "s3.p6#1", links=fid("fig1c#4"))
put(mpair(150, "0.80"), "fig1c#2")                 # the pair's H2 flow ratio: stage 2 reuses the wafer film's ratio fact for it
put(mfilm(150, "0.94", "xps"), "s3.p16#8")
put(mfilm(150, "0.94", "afm"), "s3.p22#7")
put(mfilm(150, "0.94", "se"), "s3.p28#1")
# Fig. 1b: cycle-number series at 150 °C and ratio 0.80 (ratio from s3.p5)
put(grp("cyc"), "fig1b#1", "fig1b#6", "s3.p5#2")
CYC = {"10": "fig1b#5", "20": "fig1b#4", "30": "fig1b#3", "50": "fig1b#2"}
for n, i in CYC.items():
    RUNS[xrun(f"T150_R0.80_N{n}")] = (grp("cyc"), f"MoS2 film of {n} cycles at 150 °C and ratio 0.80 (Fig. 1b)",
                                      f"{n} cyc", f"run=deposition;how=stated;sample=T150_R0.80_N{n}")
    put(xrun(f"T150_R0.80_N{n}"), i)
# extra H2 gas / H2 plasma step after a ratio-0.20 plasma at 150 °C (Table S8)
RUNS[xrun("T150_R0.20_H2step")] = (grp("T150"), "150 °C, ratio 0.20 films with an extra H2 gas or H2 plasma step (Table S8)",
                                   "H2 gas or H2 plasma step", "run=deposition;how=stated;sample=T150_R0.20+H2step")
put(xrun("T150_R0.20_H2step"), "s3.p52#2", "s3.p52#3")
# 100 °C: the TEM film patterned into the FET (Fig. 3a, Figs. S13 and S14) and the PET foil (Fig. 1d), both at 0.80
put(grp("T100"), "s3.p7#3", links=lk(CELL2[(100, "0.80")], CELL2[(100, "0.65")]))
put(mfilm(100, "0.65", "fpp"), "s3.p34#4", links=CELL4[(100, "0.65")])
put(mfilm(100, "0.80", "tem"), "s3.p8#1", "s3.p8#2", "s3.p9#1", "s3.p10#1", "fig3a#1", "s3.p43#1", "s3.p44#1")
put(mfilm(100, "0.80", "tem"), "s3.p43#3", "s3.p43#5", "s3.p43#6", links=pair(350, "0.20"))
put(mfilm(100, "0.80", "pet"), "fig1d#1", "fig1d#2", "fig1d#3", "s3.p6#4", "s3.p6#5", "s5.p2#4", "s5.p2#5")
put(mfilm(100, "0.80", "pet"), "s3.p6#3", links=fid("fig1d#1"))
# annealed films (Sections S11, S12): the anneal is an activity of the 100 °C device film (stage 3b); its settings and what it
# showed go to that film here
put(mfilm(100, "0.80", "tem"), "s3.p40#2", "s3.p40#3", "s3.p44#6")
put(mfilm(100, "0.80", "tem"), "s3.p44#4", links=grp("T100"))
# H2S flow tests (Fig. S22)
put(grp("h2s"), "s3.p53#3")
RUNS[xrun("T250_R0_lowH2S")] = (grp("h2s"), "250 °C film with lowered H2S flow and no H2 (Fig. S22a)", "Figure S22a",
                                "run=deposition;how=stated;sample=T250_R0_lowH2S")
RUNS[xrun("T150_lowH2S")] = (grp("h2s"), "150 °C films with lowered H2S flow (Fig. S22b)", "Figure S22b",
                             "run=deposition;how=stated;sample=T150_lowH2S")
put(xrun("T250_R0_lowH2S"), "s3.p53#1")
put(xrun("T150_lowH2S"), "s3.p53#2")
# the control exposures (s5.p7): the plasma alone and the Mo precursor alone, followed by in situ SE; the paper names no run
RUNS[xrun("control")] = (PROC, "control exposures at the lowest temperatures: the H2S/H2/Ar plasma alone and the Mo precursor alone, followed by in situ SE; "
                               "the paper names no run", "control exposures", "run=deposition;how=inferred;sample=control")
put(xrun("control"), "s5.p7#5")
# WS2 and TiS2 (Fig. 9)
put(grp("WS2"), "fig9a#1")
put(grp("WS2"), "s5.p8#1", links=grp("TiS2"))
put(grp("TiS2"), "fig9b#1")
for s_, g, st, lab, how in (("WS2_T150_R0.80", "WS2", "WS2 deposition at 150 °C with ratio 0.80", "WS2 @ 150 °C, 0.80", "stated"),
                            ("WS2_T150_R0", "WS2", "WSx deposition at 150 °C without H2 (ratio 0)", "WS2 @ 150 °C, 0", "stated"),
                            ("TiS2_T100_R0.50", "TiS2", "TiS2 deposition at 100 °C with ratio 0.50", "TiS2 @ 100 °C, 0.50", "stated"),
                            ("TiS2_T100_R0", "TiS2", "TiSx deposition at 100 °C without H2 (ratio 0)", "TiS2 @ 100 °C, 0", "stated"),
                            ("TiS2_T100_R0.80", "TiS2", "TiSx deposition with ratio 0.80 (not shown; 100 °C assumed from the "
                             "TiS2 recipe)", "0.80", "inferred"),
                            ("TiS2_thermal", "TiS2", "thermal ALD TiS2 reference (Fig. 9b)", "Thermal ALD", "stated")):
    RUNS[xrun(s_)] = (grp(g), st, lab, f"run=deposition;how={how};sample={s_}")
put(xrun("WS2_T150_R0.80"), "s5.p8#2", "s3.p46#4")
put(xrun("WS2_T150_R0.80"), "fig9a#2")
put(xrun("WS2_T150_R0.80"), "s3.p46#3", links=fid("fig9a#2"))
put(xrun("WS2_T150_R0"), "fig9a#3")
put(xrun("WS2_T150_R0"), "s3.p46#2", links=fid("fig9a#3"))
put(xrun("TiS2_T100_R0.50"), "s5.p8#3", "fig9b#3")
put(xrun("TiS2_T100_R0.50"), "s3.p48#4", links=lk("fig9b#3", "fig9b#4"))
put(xrun("TiS2_T100_R0"), "fig9b#5")
put(xrun("TiS2_T100_R0.80"), "s3.p48#5")
put(xrun("TiS2_thermal"), "fig9b#4")
# the explicit H2 flow ratio of each pair or run (RATIO_RUN, stage 2): under the pair's group, or under that run
for s_, i in RATIO_RUN.items():
    m = re.fullmatch(r"T(\d+)_R([\d.]+)", s_)
    put(mpair(int(m.group(1)), m.group(2)) if m else xrun(s_), i)
# the cycle number of each Fig. 1b film (CYC_RUN, stage 2); each deposition's temperature is set in stage 3b
for n, i in CYC_RUN.items():
    put(xrun(f"T150_R0.80_N{n}"), i)
put(mfilm(150, "0.65", "tem"), CYC_TEM)
put(PROC, MAT, STRUCT)
put(grp("WS2"), MAT_W)
put(grp("TiS2"), MAT_T)
# a value computed from others: under its first input
for f in C.facts():
    if f["type"] == "derived" and f["inputs"] and f["fact_id"] not in PARENT:
        _ins = {x["fact_id"]: x["type"] for x in C.facts()}
        _res = [i for i in f["inputs"].split(";") if i and _ins.get(i) != "setting"]   # its first input that is a result (a setting is no home, P25)
        if _res:
            PARENT[f["fact_id"]] = _res[0]
        elif PARENT.get(f["inputs"].split(";")[0]):
            PARENT[f["fact_id"]] = PARENT[f["inputs"].split(";")[0]]                  # computed from settings only: beside them
# cited facts: under the first reference they name (a range "refs. a-b" counts as its first number)
for f in C.facts():
    if f["type"] == "cited" and f["fact_id"] not in PARENT:
        m = re.search(r"refs?\. (\d+)", f["mentions"])
        if m:
            PARENT[f["fact_id"]] = f"{K}:refs:{m.group(1)}"
put(PAPER, "s2.p3#1")                                                          # CVD temperature: cited with no number
# claims: under the paper, linked to what supports them
CLAIM = {
    "abs.g1#1": ("s2.p1#1", "s2.p1#4"), "abs.g1#2": ("s2.p2#2", "s2.p3#1", "s2.p4#1"),
    "abs.g2#1": ("fig2#30", "fig3a#1", "s3.p6#1", "s3.p46#3", "s3.p48#4"), "abs.g2#2": ("s3.p52#3", "s3.p11#4", "s3.p11#2"),
    "abs.g3#1": (grp("map"),), "abs.g3#2": ("s3.p43#3", "s3.p43#5"), "abs.g4#1": ("s3.p6#3", "s3.p6#4", "s3.p6#5"),
    "abs.g4#2": ("s3.p46#3", "s3.p48#4"), "s2.p8#5": ("s2.p8#4",), "s2.p10#1": ("s2.p4#2", "s2.p8#3", "fig2#30"),
    "s2.p11#1": ("s3.p29#1", "s3.p22#6", "s3.p33#2"), "s2.p11#2": ("s3.p46#3", "s3.p48#4"), "s3.p1#2": ("s3.p1#1",),
    "s3.p2#1": ("fig2#1", "s3.p7#2", "s3.p7#3"), "s3.p3#1": ("s5.p4#2", "tab2.r6c2#1"), "s3.p4#3": ("fig1a#5", "fig1a#4"),
    "s3.p5#1": ("fig1b#5", "fig1b#2", "s3.p5#2"), "s3.p5#3": ("fig1b#5", "fig1b#4", "fig1b#3", "fig1b#2"),
    "s3.p7#1": ("s3.p7#2", "s3.p4#2", "s3.p7#3"), "s3.p11#1": ("s3.p11#2", "s3.p11#4", "fig4#2"),
    "s3.p11#3": (CELL4[(100, "0.80")], CELL2[(100, "0.80")]), "s3.p11#6": ("s3.p11#5",),
    "s3.p11#7": ("s3.p11#5", "s3.p11#4", "s3.p11#2"), "s3.p13#2": ("s3.p13#1",), "s3.p13#4": ("s3.p13#3", "s3.p16#8"),
    "s3.p18#6": ("s3.p18#4", "s3.p18#5"), "s3.p21#4": ("tab1.r3c7#1", "tab1.r3c3#1", "s3.p22#6"),
    "s3.p21#5": ("tab1.r1c4#1", "tab1.r2c4#1", "tab1.r3c4#1"), "s3.p22#1": ("s3.p22#6", "s3.p22#3"),
    "s3.p22#9": ("s3.p22#8", "s3.p7#2"), "s3.p22#10": ("s3.p22#6", "fig6a#6"), "s3.p25#2": ("s3.p25#3", "s3.p25#1"),
    "s3.p25#4": ("s3.p25#3",), "s3.p26#1": ("fig6a#6", "s3.p22#6"), "s3.p26#4": ("s3.p26#2", "s3.p22#6"),
    "s3.p26#5": ("s3.p22#8",), "s3.p26#6": ("s3.p7#3", "s3.p11#5"), "s3.p28#2": ("s3.p28#1", "s3.p16#8"),
    "s3.p29#2": ("s3.p30#1", "s3.p30#2", "s3.p27#3"), "s3.p30#4": ("s3.p30#3", "s3.p29#1"), "s3.p31#1": ("s3.p27#3", "s3.p31#2"),
    "s3.p32#2": ("s3.p30#1", "s3.p30#2", "s3.p32#1"), "s3.p32#4": ("s3.p32#3",),
    "s3.p33#1": ("s3.p33#2", "fig8#1", "s3.p35#5"), "s3.p37#3": ("s3.p36#2", "s3.p37#2"), "s3.p37#5": ("s3.p36#1", "s3.p37#4"),
    "s3.p39#2": ("s3.p39#3", "tab1.r2c4#1", "s3.p36#1"), "s3.p39#4": ("tab1.r2c6#1", "tab1.r2c7#1", "s3.p21#2"),
    "s3.p41#2": ("s3.p39#1", "s3.p41#1", "s3.p40#1"), "s3.p44#3": ("s3.p44#1", "s3.p44#2", "s3.p43#6"),
    "s3.p44#5": ("s3.p44#4", "s3.p44#1"), "s3.p45#1": ("s3.p46#3", "s3.p48#4", "s3.p7#3"), "s3.p46#5": ("s3.p46#2", "s3.p46#3"),
    "s3.p48#3": ("s3.p48#2", "s3.p48#1", "s3.p48#4"), "s3.p51#1": ("s3.p50#1",), "s3.p51#4": ("s3.p50#1",),
    "s3.p52#1": ("s3.p51#3",), "s3.p52#4": ("s3.p52#3",), "s3.p53#4": ("s3.p53#1", "s3.p53#3"),
    "s4.p1#2": (grp("map"), "s4.p1#1")}
for c, sup in CLAIM.items():
    put(PAPER, c)
    ln(c, *sup)
for f in C.facts():                                                            # definitions: terms and symbols of the paper
    if f["type"] == "definition" and f["fact_id"] not in PARENT:
        PARENT[f["fact_id"]] = PAPER
for f_ in list(GPC7B.values()) + list(RHO8.values()):                           # the colour cells: placed under their cell films in stage 3b
    PARENT[f_] = PROC
left = [f["fact_id"] for f in C.facts() if f["fact_id"] not in PARENT]
assert not left, left

# tree rows: paper, process, groups (pairs: evidence = the cells that name them), runs (films: evidence = every element their
# facts cite; other runs: first elements of their children), cited works
first_ev = lambda i: list(dict.fromkeys(f["evidence"].split(";")[0] for f in C.facts() if PARENT.get(f["fact_id"]) == i))
all_ev = lambda i: list(dict.fromkeys(e for f in C.facts() if PARENT.get(f["fact_id"]) == i for e in f["evidence"].split(";")))
N(PAPER, "paper", "Mattinen et al. 2022, Chem. Mater.: crystalline MoS2 (and WS2, TiS2) by PEALD down to 100 °C, steered by the "
  "H2 flow ratio of the H2S/H2/Ar plasma", "", evidence="abs.g1;abs.g2", label_as_printed="10.1021/acs.chemmater.2c01154")
N(PROC, "process", "shared process: MoSx PEALD from Mo(NtBu)2(NMe2)2 and H2S/H2/Ar remote ICP plasma in an Oxford FlexAL, Table 2 "
  "flows per H2 flow ratio, SiO2/Si substrates, and the shared characterization methods", PAPER,
  evidence="s5.p1;s5.p2;s5.p4;s5.p6;tab2.cap")
N(grp("map"), "group", "deposition window of the heat maps (Figs. 2, 4, 7b, 8): MoSx films over 50-450 °C and H2 flow ratios "
  "0-0.94 with 100-140 cycles", PROC, evidence="fig2;fig4;fig7b;fig8;fig2.cap", label_as_printed="Tdeposition (°C); H2 flow ratio",
  qualifiers="how=stated", links=lk(*[grp(f"T{t}") for t in TEMPS]))
for t in TEMPS:
    N(grp(f"T{t}"), "group", f"MoSx depositions at {t} °C (one row of Figs. 2 and 4)", PROC, evidence="fig2;fig4",
      label_as_printed=f"{t} °C", qualifiers="how=stated")
N(grp("cyc"), "group", "cycle-number series at 150 °C and ratio 0.80: 10, 20, 30 and 50 cycles (Fig. 1b)", grp("T150"),
  evidence="fig1b;s3.p5", label_as_printed="10-50 cyc", qualifiers="how=stated")
N(grp("h2s"), "group", "H2S flow tests: H2S flow varied besides the H2 flow ratio (Fig. S22)", PROC, evidence="s3.p53",
  label_as_printed="H2S flow rate", qualifiers="how=stated")
N(grp("WS2"), "group", "WS2 by PEALD from the W analogue of the Mo precursor with H2S/H2/Ar plasma (Fig. 9a)", PROC,
  evidence="fig9a;s5.p8;s3.p46", label_as_printed="WS2", qualifiers="how=stated")
N(grp("TiS2"), "group", "TiS2 by PEALD with H2S/H2/Ar plasma, and a thermal ALD reference (Fig. 9b)", PROC,
  evidence="fig9b;s5.p8;s3.p48", label_as_printed="TiS2", qualifiers="how=stated")
KINDS = list(FILM)
for i in sorted(PAIRS, key=lambda i: (TEMPS.index(PAIRS[i][0]), float(PAIRS[i][1]))):
    t, r, st, lab = PAIRS[i]
    N(i, "group", st, grp(f"T{t}"), evidence="fig2;fig4", label_as_printed=lab, qualifiers="how=stated")
for i in sorted(FILMS, key=lambda i: (TEMPS.index(FILMS[i][0]), float(FILMS[i][1]), KINDS.index(FILMS[i][2]))):
    t, r, kind, st, lab, how = FILMS[i]
    N(i, "run", st, pair(t, r), evidence=";".join(all_ev(i)), label_as_printed=lab,
      qualifiers=f"run=deposition;how={how};sample=T{t}_R{r}_{kind}")
for i in sorted(RUNS):
    p, st, lab, q = RUNS[i]
    N(i, "run", st, p, evidence=";".join(first_ev(i)[:8]), label_as_printed=lab, qualifiers=q)
for r in sorted({p for p in PARENT.values() if ":refs:" in p}, key=lambda x: int(x.rsplit(":", 1)[1])):
    N(r, "cited", f"cited work, reference {r.rsplit(':', 1)[1]} of the paper", PAPER, evidence=";".join(first_ev(r)),
      label_as_printed=f"ref. {r.rsplit(':', 1)[1]}")
for f in C.facts():
    if f["fact_id"] in PARENT:
        f["parent"] = PARENT[f["fact_id"]]
        f["links"] = LINKS.get(f["fact_id"], "")
# the purpose of each group: the paper's own sentence on what it was made to test. The map, the temperature groups and the
# (T, ratio) pairs share the one sentence (abs.g3#1): the paper has no per-temperature or per-pair sentence.
from facts import purpose  # noqa: E402
PUR = {f"{K}:grp:cyc": f"{K}:s3.p5#1", f"{K}:grp:h2s": f"{K}:s3.p53#4", f"{K}:grp:WS2": f"{K}:s3.p45#1", f"{K}:grp:TiS2": f"{K}:s3.p45#1"}
for g in [r["fact_id"] for r in C.facts() if r["type"] == "group"]:
    purpose(g, PUR.get(g, f"{K}:abs.g3#1"))

# ================================================================== stage 3b: the activity/entity tree (facts.retree)
# recipe = the old process. One inferred deposition per (T, ratio) cell of the heat maps and one inferred film entity per cell, on
# which Raman, XPS, in situ SE, SEM/AFM and four-point probe are measurement activities (the paper does not say whether one film
# served all; the measurements share cycle count and substrate). Films whose cycles or substrate differ get their own stated
# depositions: the 4" wafer (50 cycles), the glassy-carbon films of Table 1, the TEM films, the PET film, the cycle series, the
# extra-H2-step run, the H2S tests, WS2 and TiS2, the control exposures; the anneal is an activity under the 100 °C device film. Every
# deposition carries its temperature and H2 flow ratio as settings (generated below where stage 2 has none). The (T, ratio) pair
# groups are dropped (one entity each); the other groups survive with their members (step 3 turns them into comparisons).
RUNROW = {r["fact_id"]: r for r in C.facts() if r["type"] == "run"}
DEPS, ENTS, DROP = {}, {}, []
FX2 = {f["fact_id"]: f for f in C.facts()}
FX2[f"{K}:fig1c#2"]["parent"] = film(150, "0.80", "wafer")           # the wafer film's ratio belongs to the wafer deposition
for rid, r in RUNROW.items():
    s_ = rid.split(":", 2)[2]
    how_ = re.search(r"how=(\w+)", r["qualifiers"]).group(1)
    m = re.fullmatch(r"T(\d+)_R([\d.]+):(\w+)", s_)
    if m:
        t, rt, kind = m.groups()
        if kind in ("raman", "xps", "se", "afm", "fpp"):
            dep, ent = f"{K}:dep:T{t}_R{rt}", f"{K}:ent:T{t}_R{rt}"
            DEPS[dep] = dict(statement=f"MoSx deposition at {t} °C with {R} {rt}, 100-140 cycles on SiO2/Si; the paper names no run, one per cell is inferred",
                             label=f"{t} °C, {rt} H2", how="inferred", evidence="fig2;fig4" + (";" + RATIO_EV[(int(t), rt)] if (int(t), rt) in RATIO_EV else ""))
            ENTS[rid] = dict(dep=dep, ent=ent, parent=dep, how="inferred", label=f"{t} °C, {rt} H2 film", evidence="fig2;fig4",
                             statement=f"the film of the {t} °C, ratio {rt} cell, measured by Raman, XPS, in situ SE, SEM/AFM and four-point probe; "
                                       "whether one film served all is not stated, one is inferred (same cycle count and substrate)")
            DROP.append(pair(int(t), rt))
        else:
            dep, ent = f"{K}:dep:{kind}_T{t}_R{rt}", f"{K}:ent:{kind}_T{t}_R{rt}"
            DEPS[dep] = dict(statement=f"deposition of the {FILM[kind][0]} at {t} °C, {R} {rt} (its own cycles or substrate)", label=f"{t} °C, {rt} H2, {FILM[kind][0]}",
                             how="stated", evidence=r["evidence"].split(";")[0])
            ENTS[rid] = dict(dep=dep, ent=ent, parent=dep, statement=r["statement"], label=r["label_as_printed"], how=how_, evidence=r["evidence"])
    else:
        dep, ent = f"{K}:dep:{s_}", f"{K}:ent:{s_}"
        DEPS[dep] = dict(statement=r["statement"], label=r["label_as_printed"], how=how_, evidence=r["evidence"].split(";")[0])
        ENTS[rid] = dict(dep=dep, ent=ent, parent=dep, statement=r["statement"], label=r["label_as_printed"], how=how_, evidence=r["evidence"])
DROP.append(grp("T300"))                                                   # one cell at 300 °C: no series to compare
C.retree(K, PROC, DEPS, ENTS, group_facts_to={g: f"{K}:dep:{g.split(':')[-1]}" for g in DROP}, drop_groups=DROP)
# OES of the H2S/H2/Ar plasma measured the process, not a thing that ends up in the film (P19): a measurement activity of the recipe
N(f"{K}:meas:recipe:oes", "activity", "optical emission spectroscopy of the H2S/H2/Ar plasma (Section S9)", f"{K}:recipe", evidence="s3.p50;s3.p51",
  kind="measurement", how="stated", label_as_printed="OES")
for fid_ in (f"{K}:s3.p50#1", f"{K}:s3.p51#3"):
    next(x for x in C.facts() if x["fact_id"] == fid_)["parent"] = f"{K}:meas:recipe:oes"
# the anneal (Sections S11, S12) is an activity of the 100 °C device film: the paper does not name the annealed films, the device
# film (patterned and contacted) is inferred; its settings under the activity, what it showed under measurements after it
ANN, DEV = f"{K}:act:anneal", f"{K}:ent:tem_T100_R0.80"
N(ANN, "activity", "annealing of the 100 °C film up to 300 °C and in air at 150 °C (Sections S11, S12); which film was annealed is not stated, the device film is inferred",
  DEV, evidence="s3.p40;s3.p44", kind="anneal", how="inferred", label_as_printed="anneal")
for m_ in ("electrical", "measurement"):
    N(f"{K}:meas:ent:tem_T100_R0.80:anneal:{m_}", "activity", f"{m_} after the anneal", ANN, evidence="s3.p40;s3.p44", kind="measurement", how="stated",
      label_as_printed=m_)
for fid_, par in ((f"{K}:s3.p40#3", ANN), (f"{K}:s3.p44#6", ANN), (f"{K}:s3.p40#2", f"{K}:meas:ent:tem_T100_R0.80:anneal:electrical"),
                  (f"{K}:s3.p44#4", f"{K}:meas:ent:tem_T100_R0.80:anneal:measurement")):
    next(r for r in C.facts() if r["fact_id"] == fid_)["parent"] = par
# every deposition carries its temperature and H2 flow ratio
import collections  # noqa: E402
KIDS = collections.defaultdict(list)
for r in C.facts():
    KIDS[r["parent"]].append(r)
for d, spec in DEPS.items():
    mt, mr = re.search(r"T(\d+)_", d), re.search(r"_R([\d.]+)", d)       # the temperature and ratio the deposition's name states
    have = {f["quantity"] for f in KIDS[d] if f["type"] == "setting"}
    if mt and "deposition_temperature" not in have:
        temp(spec["evidence"], mt.group(1), spec["label"], f"{mt.group(1)} °C;{spec['label']}"); C.facts()[-1]["parent"] = d
    if mr and "plasma_gas_ratio" not in have:
        ratio(spec["evidence"], mr.group(1), spec["label"], f"{mr.group(1)};{spec['label']}"); C.facts()[-1]["parent"] = d
# the colour cells of Fig. 7b and Fig. 8: under the cell film's in situ SE and four-point-probe measurement activities (made here if the
# cell had none)
for (t, r), fid7 in GPC7B.items():
    for fid_, meth, lab in ((fid7, "ellipsometry", "in situ SE"), (RHO8[(t, r)], "electrical", "four-point probe")):
        act = f"{K}:meas:ent:T{t}_R{r}:{meth}"
        if not any(x["fact_id"] == act for x in C.facts()):
            N(act, "activity", f"{meth} on the {t} °C, {r} H2 film", f"{K}:ent:T{t}_R{r}", evidence="fig7b" if meth == "ellipsometry" else "fig8",
              kind="measurement", how="stated", label_as_printed=meth)
        next(x for x in C.facts() if x["fact_id"] == fid_)["parent"] = act
# the Fig. 4 region right of the vertical line at ratio 0.94 is Mo/c-MoS2 (fig4#2): a metallic Mo phase in each 0.94 cell, read from the
# figure's region (P15)
for (t, r) in sorted(c for c in CELLS if c[1] == "0.94"):
    fid_ = F(K, "fig4", "observation", f"Fig. 4 cell at {t} °C and ratio {r} lies in the Mo/c-MoS2 region of the map", quantity="phase",
             qualifiers="species=Mo", value_text="detected", data_kind="measured", method="xps", mentions=f"{r};{t} °C;Mo/c-MoS2")
    next(x for x in C.facts() if x["fact_id"] == fid_)["parent"] = f"{K}:meas:ent:T{t}_R{r}:xps"
# a comparison holds no setting: the cycle counts of s5.p7 go on every cell deposition of their temperatures (the first gets the
# fact, the others a copy citing s5.p7), the 10 nm target on every ratio-0.20 cell, the Table 1 thickness on the glassy-carbon
# depositions, the morphology films' thickness on the 150 °C cells, the WS2/TiS2 procedure and materials on their depositions;
# the grid-wide ranges (100-140 cycles, 10-20 nm films) are recipe settings
LAB = {d: spec["label"] for d, spec in DEPS.items()}
cells_at = lambda ts: [f"{K}:dep:T{t}_R{r}" for (t, r) in sorted(CELLS, key=lambda c: (-c[0], float(c[1]))) if t in ts]
C.spread(f"{K}:s5.p7#1", cells_at({450}), LAB)
C.spread(f"{K}:s5.p7#2", cells_at({50, 300, 350}), LAB)
C.spread(f"{K}:s5.p7#3", cells_at({100, 150, 200, 250}), LAB)
C.spread(f"{K}:s5.p7#4", [f"{K}:dep:T{t}_R0.20" for (t, r) in sorted(CELLS, key=lambda c: -c[0]) if r == "0.20"], LAB)
C.spread(f"{K}:s3.p19#5", [d for d in DEPS if ":dep:gc_" in d], LAB)
C.spread(f"{K}:s5.p2#3", [f"{K}:dep:tem_T100_R0.80", f"{K}:dep:tem_T350_R0.20"], LAB)    # the transistor substrate: the two FET films (P16)                 # their substrate: glassy carbon, not the SiO2/Si of the recipe
C.spread(f"{K}:s5.p8#1", [d for d in DEPS if ":dep:WS2" in d or ":dep:TiS2" in d], LAB)
C.spread(f"{K}:s5.p8#6", [d for d in DEPS if ":dep:WS2" in d], LAB)
C.spread(f"{K}:s5.p8#7", [d for d in DEPS if ":dep:TiS2" in d], LAB)
for fid_ in (f"{K}:fig2.cap#1",):
    next(x for x in C.facts() if x["fact_id"] == fid_)["parent"] = f"{K}:recipe"
# the authors' comparisons: the T x ratio grid (its members the 32 cell films), one ratio series per temperature row, the cycle
# series, the H2S tests, the WS2 and TiS2 series
CELLS_ = [f"{K}:ent:T{t}_R{r}" for (t, r) in CELLS]
C.comparisons(K, {grp("map"): ("grid", "deposition_temperature;plasma_gas_ratio"), **{grp(f"T{t}"): ("series", "plasma_gas_ratio") for t in TEMPS if t != 300},
                  grp("cyc"): ("series", "cycle_number"), grp("h2s"): ("series", "gas_flow_rate"), grp("WS2"): ("series", "plasma_gas_ratio"),
                  grp("TiS2"): ("series", "plasma_gas_ratio")}, members={grp("map"): CELLS_})
# in situ or ex situ (P6): film thickness was followed by in situ SE during the depositions (s5.p9; Figs. 7a, 7b); Fig. 1b and the
# Fig. 1c wafer map are ex situ SE (fig1.cap, s5.p11); the Table 1 density's SE thickness and the control check (s5.p7) do not say;
# the shared SE settings: s5.p9 and s5.p10 describe the in situ instrument, s5.p11 the ex situ one
C.modes(K, {**{f["fact_id"].split(":", 1)[1]: "in_situ" for f in C.facts() if re.fullmatch(rf"{K}:meas:ent:T\d+_R[\d.]+:ellipsometry", f["fact_id"])},
            **{f"meas:ent:T150_R0.80_N{n}:ellipsometry": "ex_situ" for n in (10, 20, 30, 50)}, "meas:ent:wafer_T150_R0.80:ellipsometry": "ex_situ",
            "meas:ent:control:ellipsometry": "not_stated", "method:ellipsometry": "not_stated",
            **{f["fact_id"].split(":", 1)[1]: ("not_stated" if ":gc_" in f["fact_id"] else "ex_situ") for f in C.facts() if f["type"] == "activity" and f["fact_id"].endswith(":measurement")}})
C.qualify(K, {f["fact_id"].split(":", 1)[1]: ("mode=ex_situ" if f["evidence"].startswith("s5.p11") else "mode=in_situ") for f in C.facts()
              if f["parent"] == f"{K}:method:ellipsometry" and "#" in f["fact_id"]})
# what each GPC is averaged over (P5): Fig. 7b and the text on it average the first 100 cycles; s3.p32 points at Fig. S11 without saying;
# the RBS Mo atoms per cycle are the run's areal density over its cycles
C.qualify(K, {**{f["fact_id"].split(":", 1)[1]: "over=first_100_cycles" for f in C.facts() if f["fact_id"].startswith(f"{K}:fig7b#")},
              "s3.p29#1": "over=first_100_cycles", "s3.p32#3": "over=not_stated",
              **{f["fact_id"].split(":", 1)[1]: "over=run" for f in C.facts() if "#" in f["fact_id"] and f["quantity"] == "atoms_per_cycle"}})
# what each fraction is a fraction of (P4): at.% of all atoms, an S/Mo (S/W) value per metal atom, by their definitions
AT_PCT = lambda u: u.replace(" ", "") == "at.%"
C.relative_to(K, {f["fact_id"].split(":", 1)[1]: ("all_atoms" if AT_PCT(f["unit"]) else "metal_atoms") for f in C.facts()
                  if "#" in f["fact_id"] and f["type"] != "cited" and (f["quantity"] == "composition" or AT_PCT(f["unit"]))})
# what each ± is (P2): literature averages, the wafer map's spread over positions; Table 1 does not say
C.uncertainty_kinds(K, {'s3.p16#5': ('literature', ''), 's3.p16#6': ('literature', ''), 'fig1c#4': ('position', 'not_stated'), 'tab1.r1c1#1': ('not_stated', ''), 'tab1.r1c2#1': ('not_stated', ''), 'tab1.r1c4#1': ('not_stated', ''), 'tab1.r1c6#1': ('not_stated', ''), 'tab1.r1c7#1': ('not_stated', ''), 'tab1.r2c1#1': ('not_stated', ''), 'tab1.r2c2#1': ('not_stated', ''), 'tab1.r2c4#1': ('not_stated', ''), 'tab1.r2c6#1': ('not_stated', ''), 'tab1.r2c7#1': ('not_stated', ''), 'tab1.r3c1#1': ('not_stated', ''), 'tab1.r3c2#1': ('not_stated', ''), 'tab1.r3c4#1': ('not_stated', ''), 'tab1.r3c6#1': ('not_stated', ''), 'tab1.r3c7#1': ('not_stated', '')})
# the WS2, TiS2 and thermal TiS2 films come from other processes (refs. 52, 53, 80; s5.p8, s3.p45-48): they share the reactor, the
# substrates and the gas supply with the MoS2 process, not its Mo precursor, cycle or flows (P28). A reactor activity holds what all
# share; the MoS2 recipe and three recipes for the other processes sit under it
REACTOR = f"{K}:reactor"
N(REACTOR, "activity", "the Oxford Instruments FlexAL reactor with its substrates and gas supply, shared by every deposition of the paper", PAPER,
  evidence="s5.p1;s5.p2;s5.p3;s5.p4", kind="recipe", how="stated", label_as_printed="reactor and substrates")
FXR = {x["fact_id"]: x for x in C.facts()}
FXR[f"{K}:recipe"]["parent"] = REACTOR
FXR[f"{K}:recipe"]["label_as_printed"] = "MoS2 PEALD"
for sfx in ("s5.p1#1", "s5.p1#2", "s5.p1#3", "s5.p1#4", "s5.p2#1", "s5.p2#2", "s5.p2#6", "s5.p3#1", "s5.p3#2", "s5.p3#3", "s5.p4#4", "s5.p4#5", "s5.p4#6"):
    FXR[f"{K}:{sfx}"]["parent"] = REACTOR
for rid, lab, st in (("WS2", "WS2 PEALD", "WS2 by PEALD from the W analogue of the Mo precursor with H2S/H2/Ar plasma, after the group's earlier process (ref. 52)"),
                     ("TiS2", "TiS2 PEALD", "TiS2 by PEALD from Ti(NMe2)4 with H2S/H2/Ar plasma, after the group's earlier process (ref. 53)"),
                     ("TiS2_thermal", "TiS2 thermal ALD", "thermal TiS2 ALD from Ti(NMe2)4 and H2S, after the literature process (refs. 80, 81)")):
    N(f"{K}:recipe:{rid}", "activity", st, REACTOR, evidence="s5.p8;s3.p45", kind="recipe", how="stated", label_as_printed=lab)
    for d in [d for d in DEPS if d.split(":dep:")[1].startswith(rid + "_") and (rid != "TiS2" or "thermal" not in d)] + ([f"{K}:dep:TiS2_thermal"] if rid == "TiS2_thermal" else []):
        FXR[d]["parent"] = f"{K}:recipe:{rid}"
# a thickness stated for a set of films is an observation on their comparison that names the films (P18): the ratio comparisons (s3.p5#4,
# on the grid), the Table 1 films (s3.p19#1), the 150 °C morphology films (s3.p22#2)
for fid_, ents_ in ((f"{K}:s3.p19#1", [f"{K}:ent:gc_T150_R{r}" for r in ("0.20", "0.65", "0.80")]),
                    (f"{K}:s3.p22#2", [f"{K}:ent:T150_R{r}" for (t, r) in sorted(CELLS) if t == 150])):
    next(x for x in C.facts() if x["fact_id"] == fid_)["links"] = ";".join(ents_)
# a minimum over a set of films names the films (P12): the ratio-0.94 cells (s3.p35#5) and the crystalline ratio-0.80 cells (s3.p35#2)
for fid_, cells_ in ((f"{K}:s3.p35#5", [c for c in CELLS if c[1] == "0.94"]), (f"{K}:s3.p35#2", [c for c in CELLS if c[1] == "0.80" and CELLS[c][0] == "c"])):
    next(x for x in C.facts() if x["fact_id"] == fid_)["links"] = ";".join(f"{K}:ent:T{t}_R{r}" for t, r in sorted(cells_))
# identity of entities with equal conditions (P23): the 50-cycle film of Fig. 1b and the wafer film of Fig. 1c share every stated
# condition; the paper does not say whether they are one film (if two, they would be mat22's only run-to-run pair)
C.identity(K, "not_stated", [f"{K}:ent:T150_R0.80_N50", f"{K}:ent:wafer_T150_R0.80"], "the 50-cycle film of Fig. 1b and the wafer-mapped film of Fig. 1c share every stated condition (150 °C, ratio 0.80, 50 cycles); whether they are one film is not stated", "fig1b;fig1c;fig1.cap")
# a claim rests on the results it compares (P26): s3.p39 sets the N and O contents against the carrier concentration of s3.p36
next(x for x in C.facts() if x["fact_id"] == f"{K}:s3.p39#4")["links"] += f";{K}:s3.p36#1"
# plain names for the screen (entity and comparison labels): what the film is, not the panel it is drawn in
NAMES_ = {"ent:T150_R0.20_H2step": "150 °C, 0.20 H2 film with an extra H2 step", **{f"ent:T150_R0.80_N{n}": f"150 °C, 0.80 H2 film, {n} cycles" for n in (10, 20, 30, 50)},
          "ent:T150_lowH2S": "150 °C film with lowered H2S flow", "ent:T250_R0_lowH2S": "250 °C, 0 H2 film with lowered H2S flow",
          "ent:TiS2_T100_R0": "TiS2 film, 100 °C, 0 H2", "ent:TiS2_T100_R0.50": "TiS2 film, 100 °C, 0.50 H2", "ent:TiS2_T100_R0.80": "TiS2 film, 0.80 H2",
          "ent:TiS2_thermal": "TiS2 film, thermal ALD", "ent:WS2_T150_R0": "WS2 film, 150 °C, 0 H2", "ent:WS2_T150_R0.80": "WS2 film, 150 °C, 0.80 H2",
          "ent:control": "control exposures (plasma alone, precursor alone)", "cmp:map": "temperature and H2 flow ratio grid", "cmp:cyc": "cycle series at 150 °C, 0.80 H2",
          "cmp:h2s": "H2S flow tests", "cmp:WS2": "WS2 films", "cmp:TiS2": "TiS2 films"}
for x in C.facts():
    if ":" in x["fact_id"] and x["fact_id"].split(":", 1)[1] in NAMES_ and "#" not in x["fact_id"]:
        x["label_as_printed"] = NAMES_[x["fact_id"].split(":", 1)[1]]
write(K, PID)
