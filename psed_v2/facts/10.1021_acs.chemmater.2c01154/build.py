"""Stage 2 facts for mat22 (10.1021_acs.chemmater.2c01154), read by hand from the element texts, the figure crops and the
table crops. Heat-map cells: Fig. 2 classes (two-class legend) and Fig. 4 printed S/Mo values are typed in below; Fig. 7b
and Fig. 8 colours are not read as values (only the regions, the black >dl band of Fig. 8 and the values the text gives).
Points only from cases/points.json (Fig. 1c) and accepted v1 curves."""
import sys
sys.path.insert(0, "/home/ftk3187/github/PSED/psed_v2/facts")
from common import F, NK, P, write, v1_points, cases_points  # noqa: E402

K, PID = "mat22", "10.1021_acs.chemmater.2c01154"
R = "H2 flow ratio"


def hr(r):
    return f"{R} {r}"


def ratio(ev, r, what, mentions, dk="chosen input"):
    return F(K, ev, "setting", f"{what}: {R} set to {r}", quantity="other", label_as_printed=R, value=r,
             data_kind=dk, mentions=mentions)


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
  value="150", unit="°C", data_kind="literature", method="cited", mentions="ref. 53;TiS2")
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
F(K, "s3.p1", "observation", "Saturation curves show the process is self-limiting.", mentions="Figure S1")
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
  quantity="other", label_as_printed=R, value_min="0", value_max="0.50", data_kind="chosen input",
  method="raman", mentions="150 °C;a-MoS3;ref. 54;Figure 1a")
F(K, "s3.p4;fig1a", "observation",
  "At 150 °C polycrystalline MoS2 needs a ratio of at least 0.65, seen from the appearance of the MoS2 E1g (E2g1) and A1g "
  "Raman modes.", quantity="other", label_as_printed="minimum H2 flow ratio for c-MoS2", value="0.65", data_kind="measured",
  method="raman", mentions="150 °C;Figure 1a")
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
F(K, "s3.p5", "setting", "Most H2-flow-ratio comparisons use films 10-20 nm thick made with 100-140 cycles.",
  quantity="film_thickness", value_min="10", value_max="20", unit="nm", data_kind="measured", method="ellipsometry",
  mentions="100-140 ALD cycles")

# s3.p6 / Fig. 1c, 1d
F(K, "s3.p6;fig1c;fig1.cap;s5.p11", "observation", "Thickness standard deviation over a 4\" wafer is 3.3% (film mean 5.1 ± 0.2 nm "
  "printed on the map).", quantity="thickness_nonuniformity", value="3.3", unit="%", data_kind="measured",
  method="ellipsometry", mentions="4\";σ = 3.3%;Figure 1c")
F(K, "s3.p6", "observation", "MoS2 films about 1-5 nm thick are smooth and continuous with no visible holes by AFM.",
  method="afm", mentions="Figures S3;S4")
F(K, "s3.p6;fig1d;fig1.cap", "setting", "MoS2 is deposited on PET at the lowest temperature, 100 °C, with optimized ratio 0.80.",
  quantity="deposition_temperature", value="100", unit="°C", data_kind="chosen input", mentions="PET;0.80;Figure 1d")
F(K, "s3.p6", "observation", "About 5 nm MoS2 on PET has a resistivity of 0.3 Ω cm.", quantity="resistivity", value="0.3",
  unit="Ω cm", data_kind="measured", method="four_point_probe", mentions="PET;5 nm")
F(K, "s3.p6;fig1d", "observation", "The 5 nm MoS2 films on PET are highly transparent and their resistivity does not change after "
  "repeated bending by hand.", method="photograph", mentions="PET")

# s3.p7 / Fig. 2
F(K, "s3.p7;fig2;fig2.cap", "claim", "The lowest H2 flow ratio giving crystalline films rises as deposition temperature falls.",
  mentions="Figure 2;Figure S5")
F(K, "s3.p7;fig2", "observation", "At 300 °C and above even ratio 0.20 gives c-MoS2.", quantity="other",
  label_as_printed="minimum H2 flow ratio for c-MoS2", value="0.20", data_kind="measured", method="raman",
  mentions="≥300 °C;0.20")
F(K, "s3.p7;fig2", "observation", "At 100 °C ratio 0.80 is needed for c-MoS2.", quantity="other",
  label_as_printed="minimum H2 flow ratio for c-MoS2", value="0.80", data_kind="measured", method="raman",
  mentions="100 °C;0.80")
F(K, "s3.p7;s3.p13", "observation", "There is also an upper limit: XPS shows ratio 0.94 is too high, though Raman does not reveal it.",
  quantity="other", label_as_printed=R, value="0.94", data_kind="measured", method="xps", mentions="0.94")

# s3.p8 - s3.p10 / Fig. 3
F(K, "s3.p8;fig3a;fig3.cap;s5.p18", "setting", "TEM specimen: a sub-5 nm c-MoS2 film grown at 100 °C with ratio 0.80 and 50 cycles.",
  quantity="cycle_number", value="50", data_kind="chosen input", method="tem", mentions="100 °C;0.80;50 ALD cycles;Figure 3a")
F(K, "s3.p8;s3.p9;fig3a", "observation", "The 100 °C film looks fully crystallized and is built of nanocrystallites 4-5 "
  "monolayers thick.", quantity="other", label_as_printed="monolayer thick", value_min="4", value_max="5",
  data_kind="measured", method="tem", mentions="100 °C;Figure 3a")
F(K, "s3.p9;fig3a", "observation", "Nanocrystallites of the 100 °C film are about 5-10 nm wide.", quantity="other",
  label_as_printed="nanocrystallite width", value_min="5", value_max="10", unit="nm", data_kind="measured", method="tem",
  mentions="100 °C;Figure 3a")
F(K, "s3.p10", "observation", "Surface of the 100 °C TEM film is fairly smooth, RMS roughness 0.75 nm by AFM.", quantity="other",
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
  quantity="deposition_temperature", value_min="50", value_max="100", unit="°C", data_kind="chosen input", method="xps",
  mentions="50-100 °C")
F(K, "s3.p13", "claim", "Those low-temperature exceptions may come from too little thermal energy to crystallize and an S "
  "environment more like a-MoS2+x than MoS2.")
F(K, "s3.p13;fig4", "observation", "Ratio 0.94 gives a low S/Mo although Raman shows MoS2 peaks.", method="xps",
  mentions="0.94")
F(K, "s3.p13", "claim", "The 0.94 films hold both c-MoS2 and metallic Mo, so too high a ratio can starve the film of S and/or "
  "etch S away.", mentions="0.94")

# XPS chemistry (s3.p14 - s3.p20, Fig. 5)
F(K, "s3.p14;fig5a;fig5b;fig5.cap;s3.x3", "setting", "XPS core levels of 150 °C films grown with several ratios and 140 cycles are "
  "shown as examples; other temperatures are in Table S1.", quantity="deposition_temperature", value="150", unit="°C",
  data_kind="chosen input", method="xps", mentions="150 °C;140 ALD cycles;Table S1;Figure 5;H2 flow ratios")
F(K, "s3.p14;fig5a", "observation", "In the Mo 3d region most Mo is Mo4+, assigned to MoSx.", method="xps",
  mentions="Mo4+ (MoSx);Figure 5a")
F(K, "s3.p14;s3.p15;fig5a", "observation", "All samples show two weaker doublets at higher binding energy: the highest is Mo6+ "
  "(MoO3) from oxidation in air after deposition, the middle one Mo5+ (MoOySx), an intermediate oxidation product.",
  method="xps", mentions="Mo6+ (MoO3);Mo5+ (MoOxSy);ref. 57;ref. 58;ref. 59")
F(K, "s3.p15;fig5a", "observation", "c-MoS2 films need an extra weak doublet below Mo4+, labelled Mo(4-δ)+ and assigned to more "
  "metallic Mo at crystal edges, metastable 1T' MoS2 or MoS2-x subsulfide.", method="xps",
  mentions="Mo(4-δ)+;ref. 60;ref. 61;ref. 62")
for be, lab in (("228.9", "Mo(4-δ)+"), ("229.6", "Mo4+"), ("231.1", "Mo5+"), ("232.9", "Mo6+")):
    F(K, "s3.p16;fig5a", "observation", f"Mo 3d5/2 binding energy of the {lab} component of the ratio 0.80 c-MoS2 film is {be} eV.",
      quantity="other", label_as_printed="Mo 3d5/2 BE", value=be, unit="eV", data_kind="fit", method="xps",
      mentions=f"{lab};0.80")
F(K, "s3.p16", "cited", "Average literature Mo 3d5/2 binding energy of MoS2 is 229.3 ± 0.5 eV.", quantity="other",
  label_as_printed="Mo 3d5/2 BE", value="229.3", unit="eV", data_kind="literature", method="cited",
  mentions="MoS2;ref. 63")
F(K, "s3.p16", "cited", "Average literature Mo 3d5/2 binding energy of MoO3 is 232.7 ± 0.3 eV.", quantity="other",
  label_as_printed="Mo 3d5/2 BE", value="232.7", unit="eV", data_kind="literature", method="cited",
  mentions="MoO3;ref. 63")
F(K, "s3.p16", "observation", "Measured binding energies vary slightly with deposition conditions.", method="xps",
  mentions="Section S5")
F(K, "s3.p16;fig5a", "observation", "At ratio 0.94 an intense doublet below Mo4+ appears, assigned to metallic Mo.",
  method="xps", mentions="0.94;Mo")
F(K, "s3.p17;fig5a", "observation", "Two S 2s singlets overlapping Mo 3d are included in the fit.", method="xps",
  mentions="S 2s")
F(K, "s3.p17;fig5b", "observation", "S 2p of the ratio 0.80 crystalline film fits fairly well with one S2- doublet of MoS2 at "
  "S 2p3/2 162.4 eV.", quantity="other", label_as_printed="S 2p3/2 BE", value="162.4", unit="eV", data_kind="fit",
  method="xps", mentions="0.80;S2-;Figure 5b")
F(K, "s3.p17;fig5b", "observation", "A weak doublet about 0.9 eV below the main one improves the fit; it is assigned to "
  "electron-rich S2- on metallic edges, in 1T' MoS2 or in MoS2-x subsulfide.", quantity="other",
  label_as_printed="BE shift below S2-", value="0.9", unit="eV", data_kind="fit", method="xps",
  mentions="S2- (e- rich);ref. 61;ref. 62")
F(K, "s3.p18;fig5b", "observation", "A doublet above the S2- one is strongest for the low-ratio amorphous films.", method="xps",
  mentions="S2 2- (bridging) & S2- (apical)")
F(K, "s3.p18;fig5b", "observation", "In the a-MoS3.0 film (ratio 0.50) the two S 2p3/2 components sit at 161.9 eV, with roughly "
  "equal area to the other.", quantity="other", label_as_printed="S 2p3/2 BE", value="161.9", unit="eV", data_kind="fit",
  method="xps", mentions="a-MoS3,0;0.50;lower BE doublet")
F(K, "s3.p18;fig5b", "observation", "In the ratio 0.50 amorphous film the higher S 2p3/2 component is at 163.1 eV; no "
  "electron-rich S2- is seen in this or other amorphous samples.", quantity="other", label_as_printed="S 2p3/2 BE",
  value="163.1", unit="eV", data_kind="fit", method="xps", mentions="a-MoS3,0;0.50;higher BE doublet")
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
F(K, "s3.p19;tab1.cap;s3.p21", "setting", "Table 1 films are about 50 nm thick, grown at 150 °C on glassy carbon with ratios "
  "0.20 (amorphous), 0.65 and 0.80 (crystalline), analysed for H by ERD and for Mo, S, C, N, O by RBS.",
  quantity="film_thickness", value="50", unit="nm", data_kind="measured", method="rbs",
  mentions="~50 nm;150 °C;0.20;0.65;0.80;glassy carbon;Table 1")
F(K, "s3.p19", "observation", "Detection limit of C in these films is about 7 at.%.", quantity="other",
  label_as_printed="detection limit (dl.) for C", value="7", unit="at. %", data_kind="measured", method="rbs",
  mentions="dl.;glassy carbon")
F(K, "s3.p19;s5.p17;tab1.r0c3", "definition", "Film mass density is computed from RBS areal atom densities and SE thicknesses.",
  mentions="RBS;SE;density (g/cm^3)")
F(K, "s3.p19", "cited", "Bulk MoS2 density is 5.06 g/cm3.", quantity="film_density", value="5.06", unit="g/cm3",
  data_kind="literature", method="cited", mentions="ref. 66")
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
F(K, "s3.p22;fig6a;fig6.cap;s3.x5", "setting", "Morphology comparisons use relatively thick films, 8-20 nm, grown with 140 cycles.",
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
  "linearly with cycles.", method="in_situ_ellipsometry", mentions="H2 flow ratio 0;0.50;150 °C;Figure 7a;Figure S10")
F(K, "s3.p27;fig7a", "observation", "Crystalline films just past onset (0.65, 150 °C) also grow roughly linearly but with a "
  "higher GPC than amorphous ones.", method="in_situ_ellipsometry", mentions="0.65;150 °C")
F(K, "s3.p27;s3.p28;fig7a", "observation", "Ratio 0.80 gives clearly non-linear growth with GPC rising as cycles accumulate.",
  method="in_situ_ellipsometry", mentions="0.80")
F(K, "s3.p28;fig7a", "observation", "Ratio 0.94 lowers the GPC again.", method="in_situ_ellipsometry", mentions="0.94")
F(K, "s3.p28", "claim", "The lower GPC at 0.94 may reflect a mixed MoS2/Mo film whose phases differ in density, mechanism and "
  "morphology.", mentions="MoS2;Mo")
F(K, "s3.p29;fig7b;fig7.cap;s3.x6", "observation", "GPC averaged over the first 100 cycles increases from ratio 0 to 0.80 at every "
  "temperature.", quantity="growth_per_cycle", data_kind="measured", method="in_situ_ellipsometry",
  mentions="first 100 cycles;H2 flow ratio 0;0.80;Figure 7b;Figure S11")
F(K, "s3.p29;s3.p30;s3.p31", "claim", "Two factors explain the GPC trend: more adsorption sites for the Mo precursor at higher "
  "ratio, and more surface area and reactive fin edges at higher ratio and temperature.")
MO1 = F(K, "s3.p30", "observation", "By RBS, Mo atoms deposited per cycle are 0.6 at/nm2/cycle at ratio 0.20 and 150 °C.",
        quantity="other", label_as_printed="Mo atoms deposited per cycle", value="0.6", unit="at/nm2/cycle",
        data_kind="measured", method="rbs", mentions="0.20;150 °C")
MO2 = F(K, "s3.p30", "observation", "By RBS, Mo atoms deposited per cycle rise to 1.6 at/nm2/cycle at ratio 0.65 and 150 °C, more "
        "than double, with little change in morphology.", quantity="other", label_as_printed="Mo atoms deposited per cycle",
        value="1.6", unit="at/nm2/cycle", data_kind="measured", method="rbs", mentions="0.65;150 °C")
F(K, "s3.p30", "cited", "DFT for WS2 PEALD found that the metal precursor can adsorb on -SH sites.", method="cited",
  mentions="ref. 52;-SH;WS2")
F(K, "s3.p30;s3.p42", "claim", "The density of -SH (thiol) groups, and with it the GPC and doping, should increase with the H2 "
  "flow ratio, as observed.", mentions="-SH;H2")
F(K, "s3.p31", "claim", "Fin formation and growth make GPC increase with cycle number.")
F(K, "s3.p31", "cited", "GPC rising with thickness was seen for crystalline MoS2 at ≥300 °C with ratio 0.20 and in other "
  "crystalline TMDC ALD processes.", mentions="≥300 °C;0.20;ref. 36;ref. 52;ref. 53;ref. 68")
F(K, "s3.p32", "observation", "The most Mo per cycle, 2.2 at/nm2/cycle, is deposited at ratio 0.80.", quantity="other",
  label_as_printed="Mo atoms deposited per cycle", value="2.2", unit="at/nm2/cycle", data_kind="measured", method="rbs",
  mentions="0.80")
F(K, "s3.p32", "claim", "Optical GPC hides density and stoichiometry changes, but SE with RBS and XPS indicates that Mo precursor "
  "adsorption density dominates the GPC trends.", inputs=[MO1, MO2])
F(K, "s3.p32", "observation", "At 250 °C ratios 0.35 (amorphous) and 0.50 (crystalline) give almost equal GPC.",
  quantity="growth_per_cycle", data_kind="measured", method="in_situ_ellipsometry", mentions="0.35;0.50;250 °C;Figure S11")
F(K, "s3.p32", "claim", "Crystallization itself changes GPC at most moderately, less than ratio and morphology do.")

# ------------------------------------------------------------------ electrical
F(K, "s3.p33;fig8;fig8.cap", "claim", "The H2 flow ratio tunes resistivity over several orders of magnitude.", mentions="Figure 8")
F(K, "s3.p33;fig8", "observation", "At a given temperature and fixed cycle count, higher ratio gives lower resistivity.",
  quantity="resistivity", data_kind="measured", method="four_point_probe", mentions="Figure 8;Table S2")
F(K, "s3.p34", "observation", "For amorphous films resistivity follows stoichiometry.", method="four_point_probe")
F(K, "s3.p34;fig8", "observation", "The most S-rich films (S/Mo ≥ 3) exceed the four-point probe detection limit, of order 1000 Ω cm "
  "for 10 nm films.", quantity="resistivity", value="1000", censor=">dl", unit="Ω cm", data_kind="measured",
  method="four_point_probe", mentions="S/Mo ≥ 3;10 nm;>dl")
F(K, "s3.p34", "observation", "Lower S/Mo, from higher ratio and/or temperature, lowers resistivity.", method="four_point_probe")
F(K, "s3.p34;fig8", "observation", "Lowest amorphous-film resistivity is 2 Ω cm, for MoS2.2 grown at 100 °C with ratio 0.65.",
  quantity="resistivity", value="2", unit="Ω cm", data_kind="measured", method="four_point_probe",
  mentions="MoS2.2;100 °C;0.65")
F(K, "s3.p35;fig8", "observation", "For crystalline films, raising the ratio at a given temperature lowers resistivity.",
  method="four_point_probe")
F(K, "s3.p35;s4.p1;fig8", "observation", "Lowest c-MoS2 resistivities, about 0.1-1 Ω cm, are reached at ratio 0.80.",
  quantity="resistivity", value_min="0.1", value_max="1", unit="Ω cm", data_kind="measured", method="four_point_probe",
  mentions="0.80;c-MoS2")
F(K, "s3.p35;fig8", "observation", "Crystalline film grown at 300 °C with ratio 0.20 has 15 Ω cm.", quantity="resistivity",
  value="15", unit="Ω cm", data_kind="measured", method="four_point_probe", mentions="300 °C;0.20")
F(K, "s3.p35;fig8", "observation", "Crystalline film grown at 450 °C with ratio 0.20 has 220 Ω cm.", quantity="resistivity",
  value="220", unit="Ω cm", data_kind="measured", method="four_point_probe", mentions="450 °C;0.20")
F(K, "s3.p35;fig8", "observation", "Ratio 0.94 gives resistivities down to 4 mΩ cm, likely owing to a highly conductive Mo phase.",
  quantity="resistivity", value="4", unit="mΩ cm", data_kind="measured", method="four_point_probe", mentions="0.94")
F(K, "s3.p35;fig8", "observation", "c-MoS2 resistivity is lowest at the lowest temperatures, 100-150 °C.", method="four_point_probe",
  mentions="100-150 °C")
HALL = F(K, "s3.p36;s3.p37;s4.p1;s4.p2", "observation", "c-MoS2 films grown with ratios 0.50-0.80 at 100-250 °C show p-type "
         "conduction with hole concentrations of order 10^21 cm^-3 by AC Hall.", quantity="other",
         label_as_printed="majority carrier (hole) concentration", value="1e21", unit="cm-3", data_kind="measured",
         method="electrical", mentions="0.50-0.80;100-250 °C;Section S10")
F(K, "s3.p36;s3.p37", "observation", "Hall mobilities of these low-temperature c-MoS2 films are modest, 0.001-0.01 (cm^2/Vs).",
  quantity="other", label_as_printed="Hall mobility", value_min="0.001", value_max="0.01", unit="cm2 V-1 s-1",
  data_kind="measured", method="electrical", mentions="0.50-0.80;100-250 °C")
F(K, "s3.p37", "observation", "Reference c-MoS2 films from 350-450 °C with ratio 0.20 have carrier densities of order 10^17 to "
  "10^18 cm^-3.", quantity="other", label_as_printed="carrier density", value_min="1e17", value_max="1e18", unit="cm-3",
  data_kind="measured", method="electrical", mentions="350-450 °C;0.20;ref. 69")
F(K, "s3.p37", "observation", "Those reference films have similar or slightly higher mobilities, of order 0.01 (cm^2/Vs), "
  "here and in Vandalon et al.", quantity="other", label_as_printed="mobility", value="0.01", unit="cm2 V-1 s-1",
  data_kind="measured", method="electrical", mentions="350-450 °C;0.20;ref. 69")
F(K, "s3.p37", "claim", "Similar mobilities at 150 and 450 °C indicate comparable electronic quality.", mentions="150 °C;450 °C")
F(K, "s3.p37", "cited", "MoS2 doped with 10 at.% Al at 450 °C has carrier concentrations and mobilities comparable to the "
  "low-temperature c-MoS2 here.", mentions="10 at. % Al;450 °C;ref. 69")
F(K, "s3.p37", "claim", "The process offers an easy way to make strongly p-doped MoS2 at low temperature.")
F(K, "s3.p38", "observation", "At 450 °C, raising the ratio from 0.20 to 0.80 lifts carrier concentration 3 orders of "
  "magnitude, from 10^17 to 10^20 cm^-3.", quantity="other", label_as_printed="carrier concentration", value_min="1e17",
  value_max="1e20", unit="cm-3", data_kind="measured", method="electrical", mentions="450 °C;0.20;0.80")
F(K, "s3.p38", "observation", "Ratio 0.94 gives extremely high carrier concentrations, of order 10^22 cm^-3, consistent with "
  "partial Mo content.", quantity="other", label_as_printed="carrier concentration", value="1e22", unit="cm-3",
  data_kind="measured", method="electrical", mentions="0.94")
F(K, "s3.p38", "cited", "Mo thin films have carrier concentrations of 5 × 10^22 to 1 × 10^23 cm^-3.", quantity="other",
  label_as_printed="carrier concentration", value_min="5e22", value_max="1e23", unit="cm-3", data_kind="literature",
  method="cited", mentions="Mo;ref. 70;ref. 71")
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
  quantity="other", label_as_printed="annealing temperature", value="300", unit="°C", data_kind="chosen input",
  method="electrical", mentions="Section S12")
F(K, "s3.p41", "observation", "Infrared and Raman measurements found no evidence of Mo-H or S-H bonds, which does not prove they "
  "are absent.", method="raman", mentions="Mo-H;S-H")
F(K, "s3.p41;s3.p42", "claim", "Given the process and the S deficiency of crystalline high-ratio films, H most likely sits at S "
  "vacancies or in thiol groups.")
F(K, "s3.p43", "setting", "FET channel: about 5 nm film grown at 100 °C with ratio 0.80.", quantity="film_thickness",
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
  "sample.", quantity="other", label_as_printed="interface layer thickness", value_min="2", value_max="3", unit="nm",
  data_kind="measured", method="tem", mentions="100 °C;Ni;Figure S14")
F(K, "s3.p44", "observation", "The 350 °C device has a thinner interface layer, about 1 nm.", quantity="other",
  label_as_printed="interface layer thickness", value="1", unit="nm", data_kind="measured", method="tem",
  mentions="350 °C;Figure S14")
F(K, "s3.p44", "claim", "The thicker interface of the 100 °C sample may explain its non-linear I-V.", mentions="100 °C")
F(K, "s3.p44", "observation", "Films made at 100 °C start oxidizing when annealed in air at only 150 °C.", quantity="other",
  label_as_printed="annealing temperature in air", value="150", unit="°C", data_kind="chosen input",
  mentions="100 °C;Sections S11;S12")
F(K, "s3.p44", "claim", "Further work is needed on carrier density control, contact/MoS2 interfaces and MoS2 stability during "
  "processing for low-temperature PEALD MoS2.", mentions="MoS2")

# ------------------------------------------------------------------ other TMDCs
F(K, "s3.p45", "claim", "The H2 flow ratio is a key parameter for low-temperature PEALD of TMDCs generally, allowing crystalline "
  "films at lower temperatures than before.", mentions="H2")
F(K, "s3.p45;s5.p8", "cited", "The group's published WS2 and TiS2 PEALD processes use H2S/Ar plasma without H2 (ratio 0) and give "
  "highly S-rich films at low temperature.", quantity="other", label_as_printed=R, value="0", data_kind="literature",
  method="cited", mentions="ref. 52;ref. 53;H2S/Ar")
F(K, "s3.p46", "cited", "The tungsten sulfide process gives crystalline WS2 only from 300 °C.", quantity="deposition_temperature",
  value="300", unit="°C", data_kind="literature", method="cited", mentions="ref. 52;ref. 67;ref. 79;WS2")
F(K, "s3.p46;fig9a", "observation", "Without H2 at 150 °C the W sulfide films are highly S-rich (WS4.0 by XPS), amorphous and "
  "highly resistive, like the analogous MoS2 films.", quantity="composition", qualifiers="element=S",
  label_as_printed="S/W", value="4.0", data_kind="measured", method="xps", mentions="WS4.0;150 °C;0")
F(K, "s3.p46;fig9a;fig9.cap;s3.x7", "observation", "Ratio 0.80 at 150 °C yields crystalline WS2.1.", quantity="composition",
  qualifiers="element=S", label_as_printed="S/W", value="2.1", data_kind="measured", method="xps",
  mentions="WS2.1;0.80;150 °C;Figure 9a;Section S13")
F(K, "s3.p46", "observation", "The crystalline WS2.1 film has a resistivity of 4 Ω cm.", quantity="resistivity", value="4",
  unit="Ω cm", data_kind="measured", method="four_point_probe", mentions="WS2.1;0.80;150 °C")
F(K, "s3.p46;s3.p47", "claim", "MoS2 and WS2 behave alike since Mo and W share a group and both processes use analogous "
  "M(NtBu)2(NMe2)2 precursors.", mentions="M = Mo, W")
F(K, "s3.p48", "cited", "The only reported TiS2 PEALD process is crystalline from 150 °C, but gives amorphous TiS3 at 100 °C.",
  quantity="deposition_temperature", value="150", unit="°C", data_kind="literature", method="cited",
  mentions="ref. 53;TiS3;100 °C")
F(K, "s3.p48", "cited", "A thermal TiS2 ALD process with the same Ti(NMe2)4 precursor grows crystalline films down to 100 °C.",
  quantity="deposition_temperature", value="100", unit="°C", data_kind="literature", method="cited",
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
  "150 °C, conditions that otherwise give a-MoS3.4.", quantity="other", label_as_printed=R, value="0.20",
  data_kind="chosen input", mentions="0.20;150 °C;a-MoS3.4")
F(K, "s3.p52", "observation", "The H2 plasma step removes the extra S and yields c-MoS2, whereas H2 gas changes neither "
  "stoichiometry nor crystallinity.", mentions="Table S8")
F(K, "s3.p52", "claim", "H radicals can convert a-MoS2+x into c-MoS2 under these ALD conditions, though prevention of S uptake by "
  "a higher ratio is not excluded.", mentions="a-MoS2+x;c-MoS2")
F(K, "s3.p53", "observation", "Lowering the H2S flow reduces S incorporation like raising the ratio; crystalline films form at "
  "250 °C with no H2 added.", quantity="deposition_temperature", value="250", unit="°C", data_kind="chosen input",
  mentions="250 °C;Figure S22a")
F(K, "s3.p53", "observation", "At lower temperature such as 150 °C, H2 addition is still needed for c-MoS2.",
  quantity="deposition_temperature", value="150", unit="°C", data_kind="chosen input", mentions="150 °C;Figure S22b")
F(K, "s3.p53", "observation", "At fixed ratio, more H2S flow increases S incorporation.")
F(K, "s3.p53", "claim", "Ratio, absolute H2 and H2S flows and deposition temperature must all be considered to get the wanted "
  "film properties.")

# ------------------------------------------------------------------ conclusions
NK("s4.h", "heading")
F(K, "s4.p1", "observation", "Polycrystalline films reach compositions MoS2.2, TiS2.2 and WS2.2 (conclusions; the WS2 section "
  "gives WS2.1).", quantity="composition", qualifiers="element=S", label_as_printed="MoS2.2, TiS2.2, WS2.2", value="2.2",
  data_kind="measured", method="xps", mentions="MoS2.2;TiS2.2;WS2.2")
F(K, "s4.p1", "claim", "Quantifying temperature and ratio effects opens further development of low-temperature PEALD of "
  "crystalline chalcogenides with controlled stoichiometry.")

# ------------------------------------------------------------------ experimental
NK("s5.h", "heading")
F(K, "s5.p1", "setting", "Reactor: Oxford Instruments FlexAL PEALD with a remote inductively coupled plasma source at 13.56 MHz.",
  quantity="reactor_type", data_kind="chosen input", mentions="FlexAL;13.56 MHz;ICP")
F(K, "s5.p1", "setting", "A turbomolecular pump gives a base pressure of 10^-6 Torr.", quantity="other",
  label_as_printed="base pressure", value="1e-6", unit="Torr", data_kind="chosen input")
F(K, "s5.p1", "setting", "Reactor walls heat to at most 150 °C; for 50-150 °C depositions wall and substrate are set equal.",
  quantity="other", label_as_printed="wall temperature", value="150", unit="°C", data_kind="chosen input",
  mentions="50-150 °C")
F(K, "s5.p1", "setting", "For 200-450 °C the substrate table is heated to the set value with walls kept at 150 °C.",
  quantity="deposition_temperature", value_min="200", value_max="450", unit="°C", qualifiers="kind=set_point",
  data_kind="chosen input", mentions="200-450 °C;150 °C")
F(K, "s5.p1", "definition", "Temperatures quoted are table set points; actual substrate temperature is lower at high set points "
  "because of poor thermal contact at low pressure, negligibly so at 150 °C and below.", mentions="ref. 86;150 °C")
F(K, "s5.p2", "setting", "Most depositions use Si(100) with 450 nm thermal SiO2 (Siegert Wafer) for optical contrast.",
  quantity="substrate", data_kind="chosen input", mentions="Si (100);450 nm SiO2")
F(K, "s5.p2;s5.p13", "setting", "Some Hall samples are on fused SiO2, which needs no cutting since leakage to Si via side "
  "deposits is impossible; others on SiO2/Si.", quantity="substrate", data_kind="chosen input", mentions="fused SiO2")
F(K, "s5.p2", "setting", "Transistors use Si substrates with 90 nm thermal SiO2.", quantity="substrate", data_kind="chosen input",
  mentions="90 nm SiO2")
F(K, "s5.p2", "setting", "Plastic substrate: Melinex ST504 PET foil (DuPont Teijin Films), 125 µm thick.", quantity="substrate",
  data_kind="chosen input", mentions="PET;125 μm")
F(K, "s5.p2", "observation", "Uncoated and ALD Al2O3-coated PET (50 cycles of AlMe3/H2O) give similar results.",
  mentions="Al2O3;50 ALD cycles;AlMe3;H2O")
F(K, "s5.p3", "setting", "Substrates of 1 × 1 to 3 × 3 cm2 are used as received (cut, blown with N2) on an 8\" carrier wafer.",
  quantity="substrate", data_kind="chosen input", mentions="8\" carrier wafer")
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
  "ratio 0.20.", quantity="other", label_as_printed=R, value="0.20", data_kind="literature", method="cited",
  mentions="ref. 36;8 sccm;2 sccm")
# Table 2
T2 = [("0", "10", "0", "40"), ("0.20", "8", "2", "40"), ("0.35", "6.5", "3.5", "40"), ("0.50", "5", "5", "40"),
      ("0.65", "3.5", "6.5", "40"), ("0.80", "2", "8", "40"), ("0.94", "2", "30", "18")]
for i, (r, h2s, h2, ar) in enumerate(T2, start=1):
    for j, (g, v) in enumerate((("H2S", h2s), ("H2", h2), ("Ar", ar)), start=1):
        F(K, f"tab2.r{i}c{j};tab2.r{i}c0;tab2.r0c{j};tab2.cap", "setting", f"At {R} {r} the {g} flow through the ICP tube is "
          f"{v} sccm.", quantity="gas_flow_rate", qualifiers=f"step=plasma;gas={g}", value=v, unit="sccm",
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
  quantity="other", label_as_printed="stabilization step", value_min="4", value_max="5", unit="s", data_kind="chosen input")
F(K, "s5.p6", "setting", "One full ALD cycle takes 51 s.", quantity="cycle_time", value="51", unit="s", data_kind="chosen input")
F(K, "s5.p6", "setting", "Chamber pressure is controlled at 200 mTorr during the precursor pulse.", quantity="process_pressure",
  qualifiers="step=reactant_A;kind=set_point", value="200", unit="mTorr", data_kind="chosen input")
for n, t in (("100", "450 °C"), ("120", "50 °C, 300 °C and 350 °C"), ("140", "100-250 °C")):
    F(K, "s5.p7", "setting", f"Unless noted, depositions at {t} use {n} ALD cycles.", quantity="cycle_number", value=n,
      data_kind="chosen input", mentions=t)
F(K, "s5.p7", "setting", "Cycle numbers were chosen to give about 10 nm at ratio 0.20 at each temperature (no such data for "
  "50-100 °C).", quantity="film_thickness", value="10", unit="nm", data_kind="chosen input", mentions="0.20;50-100 °C")
F(K, "s5.p7", "observation", "SE showed the H2S/H2/Ar plasma alone deposits no S, and the Mo precursor does not condense, so the "
  "lowest temperatures stay in the ALD regime.", method="ellipsometry", mentions="ref. 87")
F(K, "s5.p8", "setting", "WS2 and TiS2 follow the literature recipes, with the plasma feed gas (ratio) as the only change; a "
  "thermal TiSx recipe serves for comparison.", mentions="ref. 52;ref. 53;ref. 80")
F(K, "s5.p8;fig9a", "setting", "WS2 is grown at 150 °C with ratio 0.80.", quantity="deposition_temperature", value="150",
  unit="°C", data_kind="chosen input", mentions="WS2;0.80")
F(K, "s5.p8;fig9b", "setting", "TiS2 is grown at 100 °C with ratio 0.50.", quantity="deposition_temperature", value="100",
  unit="°C", data_kind="chosen input", mentions="TiS2;0.50")
F(K, "s5.p9", "setting", "Thickness is followed in situ by SE with a J.A. Woollam M-2000FI (0.8-5.0 eV; fits over 0.8-4.0 eV)" \
  " or M-2000F (1.2-5.0 eV).", quantity="other", label_as_printed="spectral range", value_min="0.8", value_max="5.0",
  unit="eV", data_kind="chosen input", method="in_situ_ellipsometry", mentions="M-2000FI;M-2000F")
F(K, "s5.p9", "setting", "An in situ SE measurement is usually taken every 10 cycles.", quantity="cycle_number", value="10",
  data_kind="chosen input", method="in_situ_ellipsometry")
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
  "SP4-4004STRS head).", method="four_point_probe", mentions="Keithley 2400;SP4-4004STRS")
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
  label_as_printed="pass energy", value_min="20", value_max="50", unit="eV", data_kind="chosen input", method="xps")
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
  "made with 140 cycles at six ratios, peaks labelled E2g1, A1g, a-MoS3 and Si.", quantity="other",
  label_as_printed="Intensity (Arb. units)", data_kind="measured", method="raman",
  mentions="150 °C;140 ALD cycles;Raman shift (cm-1)")
for r, key in (("0.94", "s1a_R094"), ("0.80", "s1a_R080"), ("0.65", "s1a_R065")):
    s = v1_points(f"{K}:{key}")
    pts = [p for p in s["points"] if p[0] != 518.0]
    ref = P(PID, f"fig1a_{r}", pts, "v1 points, accepted in schema_pilot/v1_points_check.csv", "Raman shift (cm-1)",
            "Intensity (Arb. units)", note="offset curve, y in v1's own scale (axis unnumbered); clipped Si point at 518 cm-1 "
            "dropped")
    F(K, "fig1a;fig1.cap", "observation", f"Raman spectrum of the {r} film: MoS2 E2g1 and A1g peaks present.", quantity="other",
      label_as_printed="Intensity (Arb. units)", points_ref=ref, data_kind="measured", method="raman", mentions=f"{R}: {r}")
for r, what in (("0.50", "with only weak broad features"),
                ("0.20", "with the broad a-MoS3 bands marked by arrows"),
                ("0", "with broad weak bands")):
    F(K, "fig1a;fig1.cap", "observation", f"Raman spectrum of the {r} film, {what}, no MoS2 peaks (not digitized).",
      method="raman", mentions=f"{R}: {r}")
F(K, "fig1b;fig1.cap", "observation", "Panel b plots Raman intensity normalized to Si against Raman shift 350-430 cm-1 for 150 °C "
  "films of 10-50 cycles, with dashed lines tracking the E2g1 and A1g peaks.", quantity="other",
  label_as_printed="Intensity (Normalized to Si)", data_kind="measured", method="raman", mentions="150 °C;Raman shift (cm-1)")
for c, th in (("50", "4.8"), ("30", "2.6"), ("20", "1.6"), ("10", "0.9")):
    extra = " (text: about 1 nm; MoS2 modes already visible)" if c == "10" else ""
    F(K, "fig1b;fig1.cap" + (";s3.p5" if c == "10" else ""), "observation",
      f"Raman spectrum of the {c}-cycle film, whose ex situ SE thickness is {th} nm{extra}.", quantity="film_thickness",
      value=th, unit="nm", data_kind="measured", method="ellipsometry", mentions=f"{c} cyc ({th} nm)")
s = v1_points(f"{K}:s1b_sub")
ref = P(PID, "fig1b_substrate", s["points"], "v1 points, accepted in schema_pilot/v1_points_check.csv", "Raman shift (cm-1)",
        "Intensity (Normalized to Si)", note="flat substrate line; y in v1's own scale (axis unnumbered)")
F(K, "fig1b;fig1.cap", "observation", "Bare SiO2/Si substrate gives a flat line in the 350-430 cm-1 window.", quantity="other",
  label_as_printed="Intensity (Normalized to Si)", points_ref=ref, data_kind="measured", method="raman", mentions="SiO2/Si")
temp("fig1c;fig1.cap", "150", "Fig. 1c wafer film", "Figure 1c")
ratio("fig1c;fig1.cap", "0.80", "Fig. 1c wafer film", "Figure 1c")
cyc("fig1c;fig1.cap", "50", "Fig. 1c wafer film", "Figure 1c")
F(K, "fig1c;fig1.cap", "observation", "Mean SE thickness over the 4\" SiO2/Si wafer is 5.1 ± 0.2 nm; colour scale runs 4.7-5.3 nm "
  "and dots mark the measured points.", quantity="film_thickness", value="5.1", unit="nm", data_kind="measured",
  method="ellipsometry", mentions="5.1±0.2 nm;4\" SiO2/Si wafer")
s = cases_points(PID, "1", "c", "thickness along the vertical diameter of the map")
ref = P(PID, "fig1c_diameter", s["points"], "cases/points.json (read by eye from the figure image)",
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
    F(K, "fig2", "observation", f"Fig. 2 cell at {t} °C and ratio {r} is coloured {'crystalline' if cl == 'c' else 'amorphous'}.",
      quantity="crystallinity", method="raman", mentions=f"{r};{t} °C")

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
  "238-224 eV, data with fit envelope, background and components, one per ratio at 150 °C.", quantity="other",
  label_as_printed="Intensity (arb. units)", data_kind="measured", method="xps", mentions="Mo 3d / S 2s;150 °C")
for r, smo in (("0.94", "1.3"), ("0.80", "1.9"), ("0.65", "2.1"), ("0.50", "3.0"), ("0.20", "3.5")):
    s = v1_points(f"{K}:s5a_R{r.replace('.', '')}_data")
    ref = P(PID, f"fig5a_{r}", s["points"], "v1 points, accepted in schema_pilot/v1_points_check.csv", "Binding energy (eV)",
            "Intensity (arb. units)", note="data markers; stacked curves, y in v1's own scale (axis unnumbered)")
    F(K, "fig5a;fig5.cap", "observation", f"Mo 3d/S 2s spectrum (data) of the ratio {r} film.", quantity="other",
      label_as_printed="Intensity (arb. units)", points_ref=ref, data_kind="measured", method="xps", mentions=f"{r};MoS{smo}")
    F(K, "fig5a;fig5b;fig5.cap;s3.x3", "observation", f"Spectra of the ratio {r} film are labelled with composition MoS{smo}.",
      quantity="composition", qualifiers="element=S", label_as_printed="S/Mo", value=smo, data_kind="measured", method="xps",
      mentions=f"{r};MoS{smo};Figure 5")
F(K, "fig5b;fig5.cap;s3.x3", "observation", "Panel b: XPS S 2p spectra, binding energy 168-159 eV, with fitted S components; the "
  "high-BE component grows towards low ratios (not digitized).", quantity="other", label_as_printed="Intensity (arb. units)",
  data_kind="measured", method="xps", mentions="S 2p;150 °C;0.94;0.80;0.65;0.50;0.20")

# ------------------------------------------------------------------ Fig. 6
F(K, "fig6a;fig6.cap;s3.x5", "observation", "SEM top views of 150 °C films (200 nm scale bar): ratios 0, 0.20 and 0.50 form the "
  "amorphous row, 0.65, 0.80 and 0.94 the crystalline row; fins are dense at 0.80 and sparse at 0.94.", method="sem",
  mentions="150 °C;Amorphous;Crystalline;200 nm")
for r, rq in (("0", "0.4"), ("0.20", "0.7"), ("0.50", "0.4"), ("0.65", "0.9"), ("0.80", "3.1"), ("0.94", "4.0")):
    F(K, "fig6a;fig6.cap", "observation", f"AFM roughness printed for the ratio {r} film is Rq = {rq} nm.", quantity="other",
      label_as_printed="Rq", value=rq, unit="nm", data_kind="measured", method="afm", mentions=f"{r};Rq = {rq} nm")
F(K, "fig6b;fig6.cap;s3.x5", "observation", "Cross-sectional TEM (smoothed; unfiltered in Figure S9) of the 150 °C, 0.65 H2 film "
  "with a magnified inset of randomly oriented 2D layers (20 nm and 5 nm scale bars).", method="tem",
  mentions="150 °C, 0.65 H2;Figure S9;20 nm;5 nm")

# ------------------------------------------------------------------ Fig. 7
F(K, "fig7a;fig7.cap;s3.x6", "observation", "Panel a: in situ SE thickness (nm, 0-22) against number of ALD cycles (0-140) at "
  "150 °C for six ratios.", quantity="film_thickness", unit="nm", data_kind="measured", method="in_situ_ellipsometry",
  mentions="Thickness (nm);Number of ALD cycles;150 °C")
for r in ("0", "0.20", "0.50", "0.65", "0.80", "0.94"):
    s = v1_points(f"{K}:s7a_R{r.replace('.', '').ljust(3, '0')}")
    ref = P(PID, f"fig7a_{r}", s["points"], "v1 points, accepted in schema_pilot/v1_points_check.csv",
            "Number of ALD cycles", "Thickness (nm)", note=s.get("note", ""))
    F(K, "fig7a", "observation", f"Thickness against cycles for the ratio {r} film.", quantity="film_thickness", unit="nm",
      points_ref=ref, data_kind="measured", method="in_situ_ellipsometry", mentions=f"{R}: {r}")
F(K, "fig7b;fig7.cap;s3.x6", "observation", "Panel b: heat map of GPC averaged over the first 100 cycles (colour bar 0.50-1.75 "
  "Å/cycle) against deposition temperature and ratio; cell colours are not read as values.", quantity="growth_per_cycle",
  unit="Å/cycle", method="in_situ_ellipsometry", mentions="GPCaverage (Å/cycle);100 cycles")

# ------------------------------------------------------------------ Fig. 8
F(K, "fig8;fig8.cap", "observation", "Fig. 8 maps four-point probe resistivity (log colour bar 10^-3 to 10^3 Ω cm, top band >dl) "
  "over deposition temperature and ratio; cell colours are not read as values.", quantity="resistivity", unit="Ω cm",
  method="four_point_probe", mentions="Resistivity (Ωcm);>dl")
F(K, "fig8", "observation", "Cells drawn in the black >dl band: 200 and 150 °C at ratio 0; 200, 150, 100 and 50 °C at 0.20; 100 °C "
  "at 0.50.", quantity="resistivity", censor=">dl", unit="Ω cm", method="four_point_probe",
  mentions=">dl;0;0.20;0.50")

# ------------------------------------------------------------------ Fig. 9
F(K, "fig9a;fig9.cap;s3.x7", "observation", "Panel a: Raman spectra (100-550 cm-1) of WSx grown at 150 °C, peaks labelled from "
  "refs 82-84: ZA(M), LA(M), 2LA(M), E2g1(Γ), A1g(Γ) and Si.", method="raman",
  mentions="WS2 @ 150 °C;ref. 82;ref. 84")
for r, key, what in (("0.80", "s9a_R080", "WS2 phonon peaks"), ("0", "s9a_R000", "a flat line without WS2 peaks")):
    s = v1_points(f"{K}:{key}")
    ref = P(PID, f"fig9a_{r}", s["points"], "v1 points, accepted in schema_pilot/v1_points_check.csv", "Raman shift (cm-1)",
            "Intensity (Arb. units)", note=s.get("note", ""))
    F(K, "fig9a", "observation", f"WSx spectrum at ratio {r}: {what}.", quantity="other",
      label_as_printed="Intensity (Arb. units)", points_ref=ref, data_kind="measured", method="raman", mentions=f"{R}: {r}")
F(K, "fig9b;fig9.cap;s3.x7", "observation", "Panel b: Raman spectra of TiSx grown at 100 °C, peaks Eg, A1g, Sh and Si.",
  method="raman", mentions="TiS2 @ 100 °C")
F(K, "fig9b;fig9.cap;s3.x7", "definition", "Sh means shoulder, a TiS2 mode often seen but not conclusively identified.",
  mentions="Sh")
for r, key, what in (("0.50", "s9b_R050", "strong Eg, A1g and Sh features"),
                     ("Thermal ALD", "s9b_thermal", "weak Eg and A1g bumps")):
    s = v1_points(f"{K}:{key}")
    ref = P(PID, f"fig9b_{r.replace(' ', '_')}", s["points"], "v1 points, accepted in schema_pilot/v1_points_check.csv",
            "Raman shift (cm-1)", "Intensity (Arb. units)", note=s.get("note", ""))
    F(K, "fig9b", "observation", f"TiSx spectrum, {r}: {what}.", quantity="other", label_as_printed="Intensity (Arb. units)",
      points_ref=ref, data_kind="measured", method="raman", mentions=r)
F(K, "fig9b", "observation", "TiSx spectrum at ratio 0: nearly flat apart from the Si line (not digitized).", method="raman",
  mentions=f"{R}: 0")

write(K, PID)
