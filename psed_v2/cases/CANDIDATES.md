# Candidate case studies

Built from `figures.csv` on 2026-10-13, first from the papers then parsed (parts A to C), then from all papers with a PDF (part D). Exploration only: nothing here is extracted data.
Figures are named `paper_id Fig. N panel`. Ontology ids are those of `ontology/ontology.yaml` v0.

How the list was made. Plot rows were grouped by the pair of axis ids with qualifiers removed, in either axis order (263 pairs, 31 shared by two or more papers), and by y quantity across different x forms. Each group was then judged. Candidate A9 comes from image rows, which the grouping cannot see. Part B is the second kind: one sample seen by several panels or methods inside one paper.

## A. Across papers (10)

### A1. Do TMA/water alumina profiles from different lateral-channel studies agree once channel height, cycles and dose are accounted for?
- **Figures.** 10.1063_1.5028178 Fig. 6; 10.1039_d0cp03358h Fig. 9a-f, Fig. 11a-b, Fig. 8b; 10.1016_j.sse.2022.108584 Fig. 6, Fig. 7.
- **Why a naive overlay is wrong.** The profiles differ in cycles (250 to 1000), pulse time, channel height and reflectometer spot size, so raw thickness against micrometres mixes four effects. Film growth narrows the channel, so profiles at different cycle numbers do not scale by a constant. The sse figures replot the same samples (data_kind cited), so counting them adds no experiment. Yim Fig. 8b shows run-to-run fronts tens of micrometres apart for nominally equal runs, which sets the floor for any agreement claim.
- **What makes them comparable.** `x_over_width` gives dimensionless_distance{by=H} and `thickness_to_gpc` gives growth_per_cycle{position=local}; Yim Fig. 9 already shows both forms. Missing in the ontology: nothing for the axes. Missing in the data: the reactant partial pressure is a model input in both papers, not a measured value, so `exposure` cannot be formed.
- **Conditions.** Temperature and pulse sequence of the Ylilammi sample are only in the body text; the Yim samples are defined only in its Table 1.
- **Papers still needed.** 10.1116/1.5093620 (the third data set plotted in sse Fig. 6) and 10.1116/1.4903941 (the test structure paper).

### A2. Which sticking coefficient does each study assign to TMA, and from which kind of evidence?
- **Figures.** 10.1063_1.5028178 Fig. 6 (fit); 10.1039_d0cp03358h Fig. 10 (simulation with chosen values) against Fig. 9; 10.1016_j.sse.2022.108584 Fig. 4, Fig. 6 (fit to cited data), Fig. 5a; 10.1039_d1cp04758b Fig. 6b-d (slope method on simulated profiles).
- **Why a naive table is wrong.** The values come from three different operations: a model adjusted to points (fit), a model run with given parameters (simulation), and a closed formula applied to a slope (calculated). The authors' own words do not separate them; two papers call a fitted curve "calculated". The models also differ (Knudsen only, with gas-phase diffusion, reversible adsorption), so one number is not the same parameter in each.
- **What makes them comparable.** initial_sticking_coefficient{species=tma} with data_kind and the model id (ylilammi_diffusion_reaction, arts_slope) attached to each value. Missing in the ontology: a model entry for the sse coverage model and a parameter for reversible desorption (evaporation flux).
- **Conditions.** The values themselves are only in tables (Ylilammi Table I, Yim Table 2, sse Tables 1 and 2).
- **Papers still needed.** 10.1116/1.5093620.

### A3. Does the recombination probability of oxygen radicals depend on material and on pressure regime?
- **Figures.** 10.1021_acs.jpcc.9b08176 Fig. 3; 10.1063_5.0168768 Fig. 3, Fig. 4; 10.1021_acs.jpcc.5c06502 Fig. 10b inset.
- **Why a naive overlay is wrong.** All three plot the same pair (half-thickness depth over cavity height against the logarithm of plasma time), which is what makes the overlay tempting. The slope means different things: at low pressure it follows the free-molecular relation, at atmospheric pressure a different prefactor applies, so equal slopes do not mean equal probabilities. Plasma time per cycle is a pulse length in one reactor and a transit time under a plasma head in the other two. The first TiO2 point at atmospheric pressure may not be recombination limited. The low-pressure lines in 10.1063_5.0168768 Fig. 4 are computed from the earlier paper's values, not new data.
- **What makes them comparable.** coated_aspect_ratio{basis=AR} on y in all three. Missing in the ontology: a transform for the logarithm of pulse_time{step=reactant_B}, and a way to carry the diffusion regime (process_pressure is there, a Knudsen number is not). The result, recombination_probability{species=o_atom, surface=...}, exists.
- **Conditions.** Cavity height, precursors and deposition temperature are only in the body text of all three papers.
- **Papers still needed.** 10.1149/1.3491381 for the low-pressure model behind the relation.

### A4. How does the shape of a plasma ALD thickness profile change with structure scale and pressure?
- **Figures.** 10.1021_acs.jpcc.9b08176 Fig. 2B; 10.1063_5.0168768 Fig. 2a-b; 10.1021_acs.jpcc.5c06502 Fig. 10b; 10.1116_6.0001094 Fig. 11, Fig. 12.
- **Why a naive overlay is wrong.** Four normalizations: thickness over its entrance value, raw nanometres, raw nanometres with no flat region at all, and thickness over an assumed saturated thickness of 22 nm, stated only in the body text (points exceed 1). Four x forms: distance over cavity height, micrometres, and metres. The structures span a gap of half a micrometre with aspect ratio above 1000 and a 1 mm gap with aspect ratio 20. In 10.1116_6.0001094 the two figures were made at different temperatures.
- **What makes them comparable.** normalized_thickness with the reference qualifier stated per row (entrance, assumed_saturation) and dimensionless_distance{by=H}. Missing: for the profiles that fall from the entrance on there is no plateau, so a reference has to be chosen and recorded; the ontology's reference list has no value for a chosen maximum.
- **Conditions.** Cavity heights for two papers and the thickness technique for three are only in the body text.
- **Papers still needed.** None for the comparison itself.

### A5. Can thickness-against-depth be compared between holes, nanotube arrays and porous bodies?
- **Figures.** 10.1038_s41467-022-35428-6 Fig. 4b; 10.3762_bjnano.5.25 Fig. 6b-c; 10.1116_1.4892385 Fig. 5; 10.1021_acs.chemmater.1c03164 Fig. 9; 10.1021_acs.langmuir.6b03119 Fig. 3a; 10.1116_6.0003182 Fig. 6d-f.
- **Why a naive overlay is wrong.** "Depth" is measured in six different geometries (a tapered hole, two nanotube arrays, a nanotube layer, a porous ceramic, a pressed powder compact), over ranges from 1 micrometre to 1.5 mm. One figure plots tube diameter, not film thickness; one plots thickness against local pore diameter with depth only on a second, non-linear axis; one plots an X-ray signal; one has thickness on the horizontal axis and depth on the vertical. In the inhibitor paper the film is intentionally thinnest at the top.
- **What makes them comparable.** distance and film_thickness map for four of the six. Missing in the ontology: a transform from coated diameter to thickness, and any equivalent aspect ratio for arrays and porous bodies (equivalent_aspect_ratio is recorded as reported only, and none of these papers reports one). Without it the x axes cannot be put on one scale. This is the geometry-class boundary of the conformality scope.
- **Conditions.** Cycle numbers and exposures are only in the body text for four of the six.
- **Papers still needed.** 10.1021/am505107s and 10.1021/cm0303080 would add the two classic array and pore cases.

### A6. Is "the dose at which growth saturates" comparable between processes?
- **Figures.** 10.1021_acs.chemmater.6c00816 Fig. 2a-b; 10.1021_acs.chemmater.9b05116 Fig. 2; 10.1021_acsnano.5b03429 Fig. 2a-b; 10.1021_acsami.0c22121 Fig. S1; 10.1116_6.0002804 Fig. 1a-b; 10.1116_6.0002993 Fig. 1c; 10.1149_2.067203jes Fig. 4; 10.1116_6.0001679 Fig. 3; 10.1021_acs.jpcc.5c06502 Fig. 2; 10.1002_adem.202201901 Fig. 1.
- **Why a naive table is wrong.** Nine papers plot growth per cycle against pulse time and one against a dose pressure. Pulse times run from milliseconds to minutes because the reactors differ, not the chemistry. One paper gives growth per precursor pulse, one derives growth from mass gain on a powder, one varies precursor and plasma time together. Saturation time is a reactor property unless the pressure during the pulse is known.
- **What makes them comparable.** Only `exposure` (partial_pressure times pulse_time) would do it. The partial pressure is on the figure in one paper out of ten. The ontology has the transform; the data do not have the input.
- **Conditions.** Reactor pressure during the pulse, where given at all, is in the body text.
- **Papers still needed.** None; the case is useful as a negative example.

### A7. Do the lateral-channel models give the same answer for the same inputs, and the same link between front slope and sticking coefficient?
- **Figures.** 10.1063_1.5028178 Fig. 2, Fig. 3 against 10.1039_d1cp04758b Fig. 2a-b (same parameters, stated); 10.1039_d1cp04758b Fig. 6b-d, Fig. 7; 10.1039_d3cp01829f Fig. 4f, Fig. 6; 10.1039_d4cp00131a Fig. 11b, Fig. 12.
- **Why a naive overlay is wrong.** Most of these plot coverage after one exposure, not thickness after many cycles; the two coincide only without channel narrowing. Depth is in micrometres in one pair and in units of channel height elsewhere. The slope relation holds in the free-molecular limit only, and one paper shows it changing with Knudsen number. Fitted lines in 10.1039_d4cp00131a Fig. 12 are adjusted to simulated points, so data_kind fit there does not mean agreement with an experiment.
- **What makes them comparable.** surface_coverage against dimensionless_distance{by=H}; the half-coverage depth maps to coated_aspect_ratio{basis=AR}. Missing in the ontology: the slope at half coverage and the front broadness (three papers plot them), the Knudsen number, and model entries for the ballistic model and the porous-particle model.
- **Conditions.** Baseline parameter sets are only in tables in three of the four papers.
- **Papers still needed.** 10.1149/1.3072694 and 10.1002/cvde.200390005 for the two older models these are measured against.

### A8. Does penetration grow with the square root of exposure in experiment as it does in the models?
- **Figures.** Models: 10.1063_1.5028178 Fig. 5; 10.1021_acs.chemmater.1c03164 Fig. 4a; 10.3762_bjnano.5.25 Fig. 3c-d, Fig. 4; 10.1039_d3cp05639b Fig. 3; 10.1039_d3cp01829f Fig. 4e, 4h. Experiments: 10.1039_d0cp03358h Fig. 11a; 10.1021_acs.langmuir.6b03119 Fig. 3a; 10.3762_bjnano.5.25 Fig. 6c.
- **Why a naive overlay is wrong.** "Penetration depth" is the model's front position in three papers, the half-coverage depth in two, and has to be read off a thickness profile in the experiments. The x axis is pulse time, scaled time, exposure in pascal seconds, or particle radius. One model figure puts four different quantities on a single axis. The experiments give two to four exposure values each, with thickness-based depth.
- **What makes them comparable.** penetration_depth with the level qualifier (50%, or other: model front) and `exposure` on x. Missing: a value of the level qualifier for coverage-based depths, and partial pressure for the experiments.
- **Conditions.** Pressure during the pulse is only in the body text of the experimental papers.
- **Papers still needed.** 10.1002/cvde.200390005 (the plug-flow relation three of these compare with).

### A9. How does reported step coverage vary with aspect ratio across processes?
- **Figures (images with the numbers written on them or in words).** 10.1021_acs.jpclett.4c03545 Fig. 1, Fig. 2; 10.1021_acs.chemmater.6c00816 Fig. 4; 10.1116_6.0002804 Fig. 9; 10.1149_2.067203jes Fig. 8; 10.1016_j.mee.2018.01.027 Fig. 3; 10.1007_s12274-010-0066-9 Fig. 3.
- **Why a naive table is wrong.** The ratio is bottom over top in some, sidewall over top in others, and a set of percentages at three positions in one. Aspect ratios run from 1.5 to 90 and are for trenches, holes and pores, which need different doses at equal aspect ratio. Thermal, plasma and hot-wire processes are mixed. One value above 1 is deliberate. None of the values is on a plot axis.
- **What makes them comparable.** step_coverage{position=bottom | sidewall} and aspect_ratio; `step_coverage` from film_thickness{position=...} where thicknesses are given. Missing: equivalent_aspect_ratio is not reported by any of them, and no method field ties a number to the image it was read from.
- **Conditions.** Every value is in a caption or in the body text, none in a table.
- **Papers still needed.** This one matters: the bulk of such values are in the in-scope papers without a PDF (the papers behind the conformality tables of the 2019 review).

### A10. When do mesopores close during ALD, and how does growth inside pores compare with growth on a flat surface?
- **Figures.** 10.1039_c4nr05049e Fig. 6b, Fig. 7b, Fig. 8; 10.3390_separations11010024 Fig. 7, Fig. 9; 10.1116_6.0001679 Fig. 4; 10.1021_acs.langmuir.6b03119 Fig. 4c; 10.1039_c5ta00205b Fig. 1.
- **Why a naive overlay is wrong.** The signals are an X-ray critical angle, a scattering intensity, fluorescence counts, gas permeance, cations per area, and microbalance mass. All are plotted against cycle number, so they stack on one x axis while measuring different things. Two papers show a break near cycle 20 to 28 in titania films with pores of 4 and 5.5 nm, from different precursors; the agreement may be real or may be coincidence of pore size over growth per cycle.
- **What makes them comparable.** cycle_number on x; feature_width for the pore size; closure expected near pore width over twice the growth per cycle. Missing in the ontology: an amount-based growth per cycle (mass or atoms per area; the proposal was rejected for lack of gold evidence, and five papers here would use it) and a quantity for the cycle of pore closure.
- **Conditions.** The planar growth per cycle needed for the estimate is in the body text of both titania papers.
- **Papers still needed.** 10.1021/la300045z and 10.1021/jp111314b (same in-situ methods on other films).

## Rejected groups

- 2θ against intensity (13 papers): diffraction patterns of unrelated materials; no shared question.
- Binding energy against intensity (10 papers): XPS spectra of unrelated materials.
- Growth per cycle against deposition temperature (9 papers): nine different processes; no process occurs twice.
- Film thickness against cycle number (8 papers): linearity checks on different materials and substrates; nucleation delay is substrate specific.
- Absorbance against wavenumber (4 papers), Raman shift against intensity (3 papers): spectra of unrelated materials.
- Growth per cycle against purge time (3 papers): reactor-specific, same objection as A6 without a transform to rescue it.
- Current density against potential (3 papers), capacitance against voltage (2 papers), magnetization against field (2 papers): device and material tests outside the conformality scope.
- Composition against deposition temperature (2 papers), refractive index against temperature (2 papers), refractive index against pulse time (2 papers): different materials.
- Resistivity against temperature and against film thickness (2 papers each, WCx and Mo): a size-effect comparison is possible but lies outside the conformality scope.
- Growth per cycle against measurement position (2 papers): the x axis is a point label on a part or a strip, not a distance; the two reactors share nothing.
- Emission counts against wavelength (2 papers): oxygen plasma spectra taken for different purposes, without calibrated intensity.
- Diffusion coefficient against Knudsen number (2 papers): the same formula from the same group; folded into A7.
- Reactant partial pressure against distance (2 papers): a stated reproduction of one figure by another; folded into A7.
- Mass gain against time (2 papers): microbalance traces of unrelated processes; the useful part is in A10.
- X-ray line intensity against position (two groups, 2 papers each): signals without a thickness scale; the one useful case is in A5.
- Intensity against photon energy (2 papers), scattering maps (2 papers): raw detector output.
- Growth per cycle and normalized thickness against x/H (2 papers each): the Yim panels and their own simulations plus one more paper; folded into A1 and A4.
- Surface coverage against distance (5 papers, all simulation): folded into A7; the porous-body members belong to A5.

## B. Within one paper: one sample seen by several panels or methods

Link is **stated** when the caption or text names the same sample or run, or one panel is drawn on or derived from the other. It is **possibly** when only the conditions match.

### Stated (17 sample sets, 10 of them by two or more different techniques)

| Paper | Sample | Panels | Methods | What links them |
| --- | --- | --- | --- | --- |
| 10.1039_d0cp03358h | S11 | Fig. 5a, 5b, 9d-f | SEM with EDS map, EDS line scan, reflectometry | captions name sample 11 |
| 10.1039_d0cp03358h | S2 | Fig. 4b, 8b | optical top view, reflectometry | captions name sample 2 |
| 10.1039_d0cp03358h | S8, S12 | Fig. 8a-b, 9a-f; Fig. 8b, 11a-b | reflectometry in several series | captions name the samples |
| 10.1116_6.0001094 | L1-L6 | Fig. 11, 13 | thickness profile, fitted radical pressure | Fig. 13 is obtained from Fig. 11 |
| 10.1116_6.0001094 | L7-L11 | Fig. 12, 14 | thickness profile, fitted radical pressure | Fig. 14 is obtained from Fig. 12 |
| 10.1021_acs.jpcc.5c06502 | A-D | Fig. 10b and inset | optical grey scale scaled by ellipsometry, derived depth | same panel, samples lettered |
| 10.1021_acs.jpcc.9b08176 | LH1-LH8 | Fig. 2A, 2B, 3 | optical top view, thickness profile, derived depth | one figure; Fig. 3 refers to Fig. 2 |
| 10.1063_5.0168768 | Si1-Si3, Ti1-Ti3 | Fig. 2, 3, 4 | thickness profile, derived depth | Fig. 3 and 4 use the Fig. 2 profiles |
| 10.1021_acs.langmuir.6b03119 | NT0.5-NT10 | Fig. 3a, 3b-e | thickness at four depths, SEM of tube bottoms | one figure, same exposure times |
| 10.1021_acsami.0c06879 | c1, c5, c7, c10 | Fig. 4a-p | TEM, dark-field STEM, EDS map, EDS line scan | each column is one sample, stated |
| 10.1021_acsnano.5b03429 | MOF1 | Fig. 5b, 5c | SEM, EDS line scan | scan line drawn on the image |
| 10.1038_s41467-022-35428-6 | H0, H40, H60, H40w | Fig. 4a, 4b, 4c | TEM cross-section, thickness against depth, selectivity | panels b and c are read from panel a |
| 10.1116_6.0003182 | C120, C160, Ccyc | Fig. 2, 3, 4, 5, 6 | chamber pressure, photograph, XRD, SEM with EDS maps, EDS line scan | each run is named by its temperature schedule in every caption |
| 10.1149_2.067203jes | ST1 | Fig. 2b, 3 | ellipsometry, TEM | Fig. 2b takes its thicknesses from the Fig. 3 image |
| 10.3762_bjnano.5.25 | S400 | Fig. 6a, 6b | SEM at three depths, thickness against depth | caption ties the profile to the imaged array |
| 10.1186_s11671-015-0872-9 | F1 | Fig. 4a-c, 4c-1 to c-3 | ion-beam cross-section in SEM, EDS line scan | scan line drawn on the image |
| 10.1093_nsr_nwaf247 | R0, RB | Fig. 3a, 3c; 3d, 3f | ellipsometry at eleven points, plasma etch rate, interpolated map | one figure per run |

The two that fit the example in the brief (a profile and a picture of the same channel): Yim S11 and S2, and 10.1021_acs.jpcc.9b08176 LH1-LH8. The cross-section analogue is 10.1038_s41467-022-35428-6 and 10.3762_bjnano.5.25 S400.

### Possibly (18 links)

| Paper | Panels | Methods | Reason, and what is not stated |
| --- | --- | --- | --- |
| 10.1021_acs.chemmater.1c03164 | Fig. 8 with Fig. 9 | SEM at three depths; diameter against depth | both show the coated forest; same piece not stated |
| 10.1116_1.4892385 | Fig. 3, 4 with Fig. 5 | SEM of a fracture surface; thickness against depth | thickness is read on a fracture surface; same piece not stated |
| 10.1021_acs.jpclett.4c03545 | Fig. 1, 2 with Fig. 3 | trench cross-sections; top view of lateral chips | same two processes; same runs not stated |
| 10.1021_acs.jpclett.4c03545 | Fig. 3 with Fig. 4 | SEM top view; XPS at opening and inside | a lateral chip in both; which one not stated |
| 10.1021_acs.langmuir.6b03119 | Fig. 2 with Fig. 3 | SEM at four depths; thickness at four depths | same 5 s exposure |
| 10.1021_acs.langmuir.6b03119 | Fig. 4 with Fig. 3 | microbalance; SEM | same 10 s exposure, measured on a layer on a crystal |
| 10.1116_6.0002804 | Fig. 9 with Fig. 10 | STEM of trenches; element maps at top and bottom | a narrow trench in both |
| 10.1007_s12274-010-0066-9 | Fig. 1c with Fig. 1f | TEM; XRD | same cycle number |
| 10.1021_acs.chemmater.2c01154 | Fig. 1a with Fig. 5, Fig. 6 | Raman; XPS; SEM with AFM | same temperature, cycles and gas ratios |
| 10.1021_acsami.0c06879 | Fig. 2a-d with Fig. 2e-f, Fig. 5a | AFM; XRD; roughness | same cycle parameter values |
| 10.1021_acsnano.5b03429 | Fig. 2c with Fig. 3a | SEM cross-section; XRD | both a 1000-cycle film on silicon |
| 10.1039_c3ra42928h | Fig. 1 with Fig. 2c; Fig. 3 with Fig. 2b, 2d | microscopy; EDX; XRD | as-deposited and annealed states match |
| 10.1039_c4nr05049e | Fig. 5-7 with Fig. 8 | in-situ scattering; in-situ fluorescence | same film type and cycle range; same run not stated |
| 10.1093_nsr_nwaf247 | Fig. 3 with Fig. 4a-d | ellipsometry; AFM and SEM at one position | a good and a poor film; link to the two runs not stated |
| 10.1116_1.5116136 | Fig. 1, 2 with Fig. 3-5 | STEM with element maps; Raman in solution | same coating thickness; same batches not stated |
| 10.1016_j.mee.2018.01.027 | Fig. 3 with Fig. 4 | SEM cross-section; imaging test | gratings of the same kind |
| 10.1186_s11671-015-0872-9 | Fig. 4 with Fig. 3, Fig. 5 | cross-section with line scan; XRD; TEM | the filled template in all three |

## Limits of this pass

- 60 plot rows are marked "not viewed" in their note: panels whose layout repeats one I did read, or routine spectra, recorded from the caption. Their axis labels are not verbatim.
- Uncaptioned page-1 graphics and tables are not in the inventory.
- A panel holding both points and a curve is one row with two data kinds (for example "measured; fit").
- 334 measured rows carry a sample key of the form `u:<figure><panel>`: a sample is shown but nothing links it to another panel.

## C. Checked candidates N1 to N9

Each was checked against the named figures and, where needed, the body text and tables of `ingest/final/<id>/document.md`. Verdicts: 3 hold, 6 hold partly, none fails outright.

### N1. One experiment through the literature
- **Question.** How often does one measured profile reappear in later papers, and what does each paper conclude from it?
- **Figures.** 10.1063_1.5028178 Fig. 6 (the 500-cycle alumina profile) and 10.1039_d0cp03358h Fig. 11a (pulse 0.1 s and 0.2 s) reappear in 10.1016_j.sse.2022.108584 Fig. 6, together with a profile of Arts 2019 (10.1116/1.5093620, no PDF). 10.1039_d0cp03358h Fig. 9a (heights 100, 500, 2000 nm) reappears in sse Fig. 7. sse Fig. 4 uses three water-limited profiles of Arts 2019. 10.1039_d1cp04758b Fig. 2a-b repeats 10.1063_1.5028178 Fig. 2 and Fig. 3 with the same inputs (stated in its caption). 10.1063_5.0168768 Fig. 4 draws low-pressure lines from published values.
- **Sticking coefficient of TMA from the same alumina data.**

| Paper | Value | Model | data_kind | Where |
| --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 5.72e-3 | diffusion-reaction with reversible adsorption (ylilammi_diffusion_reaction) | fit | Table I |
| 10.1039_d0cp03358h | 4e-3 (average of several samples) | slope at half thickness (arts_slope) | calculated | Table 2 |
| Arts 2019, as quoted in the two papers above and in sse | (0.5 to 2)e-3 | slope at half thickness | cited | Yim Table 2, sse Table 2 |
| 10.1016_j.sse.2022.108584 | 7.5e-3, one set for all three sources | Knudsen or Bosanquet diffusion with an evaporation flux | fit, by hand and by eye (stated) | Table 2 |
| 10.1039_d0cp03358h Fig. 10 | 0.012 | ylilammi model, re-implemented | simulation input, not a result | figure caption |

- **What it shows about the pipeline.** Without the cited data kind and a pointer to the original figure, the same three samples would be counted three times, and five different numbers would look like five measurements of one quantity. The spread (0.5e-3 to 12e-3) comes from the model and the operation, not from new experiments.
- **Verdict: holds partly.** The re-use in sse and d1cp04758b is as described and stated by the authors. The third item is not: the low-pressure values in 10.1063_5.0168768 (Table I: 9e-5 for SiO2, 4e-5 for TiO2, at 100 °C) are taken from a 2021 paper by the same first author, then without a PDF, and they differ from those of 10.1021_acs.jpcc.9b08176 (6e-5 and 7e-5 at 200 °C).
- **Missing in the ontology.** A link from a cited series to the figure it was taken from; a model entry for the sse model; a parameter for the evaporation flux.
- **Only in text or tables.** Every value above. sse also states which inputs it had to estimate (partial pressures of 325 and 160 mTorr, a pulse time, a film density).

### N2. Calibration against prediction
- **Question.** Which model curves were adjusted to the data they are drawn with, and which were not?
- **Figures.** sse Fig. 6 against Fig. 7; 10.1039_d0cp03358h Fig. 9a-f against Fig. 10a-f.
- **What was found.** sse Fig. 7 uses the parameter set of its Table 2 without re-adjustment (stated in the text and the caption). Three caveats: for the 2 µm channel the diffusivity formula is switched to include gas-phase diffusion, which is a change of model form; the 0.5 µm profile is a nominal repeat of one used for calibration (another sample with the same recipe); and the 0.1 µm case does not match, which the authors attribute to the channel closing. In Yim, Fig. 10 is a simulation with chosen inputs and is laid out panel by panel like Fig. 9; it covers two heights and two cycle numbers that were not measured, reproduces the ordering and the collapse on x/H, and has none of the spikes and tails of the measured curves.
- **What it shows about the pipeline.** data_kind must separate fit from simulation by the operation, not by the wording: sse calls both figures "comparison of simulation", Yim calls Fig. 10 "simulated", Ylilammi calls a fit "calculated".
- **Verdict: holds partly.** The parameters are not re-adjusted, but only two of the three Fig. 7 profiles are new to the model and one of those needs a different diffusivity.
- **Missing in the ontology.** A way to say that a curve is a prediction with parameters taken from another fit (data_kind simulation plus the source of its parameters).
- **Only in text or tables.** The statement that parameters were kept; the sample definitions (Yim Table 1).

### N3. One symbol, several meanings
- **Question.** Which printed words for coverage, penetration and step coverage mean the same thing?

| Paper | Figure | Printed | What it means | Ontology id with qualifier |
| --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 3 | Surface coverage (θ) | covered site fraction after one pulse | surface_coverage |
| 10.1039_d3cp01829f | 2, 3 | Surface coverage θ | covered fraction after one exposure; called a saturation profile | surface_coverage |
| 10.1039_d4cp00131a | 1a | s/N over gpc_sat, θ on one axis | thickness per cycle over its saturation value, set equal to coverage | normalized_thickness{reference=assumed_saturation}, equal to surface_coverage only without channel narrowing |
| 10.1116_6.0001094 | 11, 12 | Coverage | thickness after 200 cycles over an assumed 22 nm | normalized_thickness{reference=assumed_saturation} |
| 10.1116_1.4892385 | 2 | Degree of surface coverage 1-Θ | Θ is the free fraction, so the plotted quantity is the covered one | surface_coverage = 1 - Θ |
| 10.1093_nsr_nwaf247 | 1b, 1d, 1f | -OH surface coverage | hydroxyl groups left unreacted after the TMA step | 1 - surface_coverage (of the TMA step) |
| 10.1093_nsr_nwaf247 | 3a, 3d | DMA(ads)+MMA(ads) surface coverage | adsorbed aluminium species, the product side | surface_coverage |
| 10.1038_s41467-022-35428-6 | 2e | Areal coverage (%) | area fraction taken by inhibitor molecules, saturating near 50% | surface_coverage on an area basis; no qualifier for the basis |
| 10.1016_j.sse.2022.108584 | 5b | θ_sat | coverage at saturation, below 1 because adsorption is reversible | surface_coverage at long exposure; no entry |
| 10.1063_1.5028178 | 5 | Penetration depth x_p | front position of the model after one pulse | penetration_depth{level=other:model front} |
| 10.1039_d0cp03358h | Table 1 | x50%, PD50% | depth of half the thickness | penetration_depth{level=50%} |
| 10.1039_d3cp01829f, 10.1039_d4cp00131a | 4; 5, 8, 10, 11 | x̃ at θ = 0.5 | depth of half coverage, in channel heights | coated_aspect_ratio{basis=AR}, on coverage; no qualifier for coverage against thickness |
| 10.1039_d3cp05639b | 2 to 8 | r at θ = 1/2 | used both as the depth coordinate of a profile and as the half-coverage depth | distance in one use, penetration_depth{level=50%} in the other |
| 10.1016_j.sse.2022.108584 | 5b | SC_sat | coverage at the bottom over coverage at the top, at saturation | not step_coverage (which is a thickness ratio) |
| 10.1021_acs.jpclett.4c03545 | 1, 2 | SC | bottom thickness over top thickness, 1 and 1.6 | step_coverage{position=bottom} |
| 10.1021_acsami.0c06879 | S2 | SC | shell thickness at two points 900 nm apart along a wire | step_coverage, no matching position value |

- **What it shows about the pipeline.** Label matching alone would merge six different quantities under "coverage". Two of the ambiguous aliases already in the ontology (coverage, depth) are confirmed, and two more are needed (penetration depth, step coverage).
- **Verdict: holds.** Every row was read on the figure; the free-fraction reading of Θ rests on the axis label itself.
- **Missing in the ontology.** A basis for coverage (sites or area); a level qualifier that says coverage or thickness; saturation coverage; a complement transform.
- **Only in text or tables.** The 22 nm of 10.1116_6.0001094; the meaning of -OH coverage in 10.1093_nsr_nwaf247; the Yim depths.

### N4. Where a thickness number comes from

| Paper, figure | Method | How thickness is derived | Stated uncertainty |
| --- | --- | --- | --- |
| 10.1039_d0cp03358h Fig. 7, 8 | reflectometry line scan, spot 5, 25 or 50 µm | optical model of a smooth alumina film on silicon | positioning about 2 µm; repeat scans overlap (no number); the 50 µm spot leaves a false tail; four nominally equal runs differ by tens of µm in front position |
| 10.1063_1.5028178 Fig. 6, 7 | reflectometry, 100-point line scan | same kind of optical model | about 3 nm, limited by surface roughness (body text) |
| 10.1021_acs.jpcc.9b08176 Fig. 2B | reflectometry, spot about 10 µm, mapping stage | optical model, then normalized | none found |
| 10.1021_acs.jpcc.5c06502 Fig. 10b | optical microscope image | grey level along the channel, scaled with ellipsometry on a planar film | none found; profiles have no flat region |
| 10.1063_5.0168768 Fig. 2 | small-spot ellipsometry, 25 by 40 µm | optical model per material | systematic error about 1 nm per point (caption) |
| 10.1116_6.0001094 Fig. 11, 12 | mapping ellipsometry, one point per mm | optical model, then divided by an assumed 22 nm | fitting error below 1% for the derived pressure; none for thickness |
| 10.3762_bjnano.5.25 Fig. 6b | SEM | distribution of coated tube diameters at each depth | error bars the size of the symbols (caption) |
| 10.1021_acs.chemmater.1c03164 Fig. 9 | SEM | coated tube diameter plotted directly; thickness would be half the gain over the bare tube | error bars on each point; 95% band on the expected curve |
| 10.3390_separations11010024 Fig. 7 | permporometry before and after | half the loss of pore width, about 0.33 nm after 12 cycles | none shown |
| 10.1149_2.067203jes Fig. 2b | TEM and in-situ ellipsometry on one stack | layer thickness read on the image; optical model | the two agree within the symbol except at 10 cycles (about 0.9 against 1.3 nm) |
| 10.1038_s41467-022-35428-6 Fig. 4b | TEM | thickness read along the hole wall | none shown |

- **What it shows about the pipeline.** "Film thickness (nm)" hides five derivations with resolutions from 5 µm to 1 mm along the profile. A profile cannot be compared without the method and the spot size.
- **Verdict: holds.**
- **Missing in the ontology.** Lateral resolution of a measurement (spot size was sent to unmapped in v0); "derived" as a method; a pore-width-loss transform; a diameter-to-thickness transform.
- **Only in text or tables.** Spot size and technique for five of the eleven.

### N5. Reactor-scale uniformity
- **Question.** How even is growth across a part, a tube or a batch, and can the three be compared?
- **Figures.** 10.1093_nsr_nwaf247 Fig. 3a, 3d (eleven numbered points on a 3D part, without and with baffles; growth per cycle measured, coverage simulated); 10.3390_separations11010024 Fig. 3 (five numbered spots along a 100 mm strip in a tube, three carrier flows); 10.1002_adem.202201901 Fig. 3a-b (within-wafer value against dose and temperature), Fig. 4a (wafer slot 1 to 25 of a batch, loads of 5 and 25).
- **How position is given.** As a point number on a drawing in the first (coordinates only in a supplement figure), as a spot number in the second (first spot at the inlet; spacing not on the figure), as a slot number in the third. The within-wafer value of the third is one percentage with no positions at all; the paper defines it from the maximum, minimum and mean.
- **What it shows about the pipeline.** Position labels are not coordinates. The only common currency is a spread, and the first paper prints one (35% to 6% measured, 12% to 2% simulated) with an unstated definition.
- **Verdict: holds partly.** The three figures are as described, but nothing puts their positions on one scale, and only one definition of non-uniformity is printed.
- **Missing in the ontology.** thickness_nonuniformity has no qualifier for its scope (within wafer, across a batch, over a part) or its formula; no entry for a position label; the simulated counterpart is a coverage, not a thickness.
- **Only in text or tables.** The definition of the spread (adem equation); point coordinates (nsr supplement).

### N6. Recipe card

| Material | Precursor / co-reactant | Reactor (as far as read) | Temperature range shown | Saturation pulse, precursor / co-reactant | Purge | Growth per cycle | Partial pressure known |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Al2O3 | TMA / water | pump-type batch | 35 to 150 °C, nearly flat | dose 1.3 Torr / 1.0 Torr, no times | not varied | about 1.0 Å | yes, the dose is a pressure |
| SiO2 | aminosilane / O2 plasma | plasma reactor | 50 to 400 °C, falling 1.7 to 0.8 Å | about 50 ms / about 1 s | 2 s / 2 s | 1.1 Å at 250 °C | no |
| Al2O3 (reference in the same reactor) | TMA / O2 plasma | same | 250 °C only | about 20 ms / 2 s | 2.5 s / 1 s | 1.1 Å | no |
| WCx | carbonyl precursor / H2 plasma | plasma reactor | 150 to 300 °C, rising, no flat window | 18 s / 3 to 10 s | not varied | 1.0 Å at 250 °C | no |
| Mo | MoCl2O2 / atomic H | hot-wire reactor | 150 to 450 °C, flat from 250 °C | about 1 s, still rising / about 10 s | 6 s / any | 0.022 nm | no |
| Ga2S3 | gallium amide / H2S plasma | plasma reactor | 125 to 225 °C, not flat | 10 s / 5 s | not varied | 1.1 to 1.7 Å | no |
| Co9S8 | amidinate / H2S | not on the figures | 130 °C only | about 1 s / about 0.03 s | not varied | 0.4 Å | no |
| TiO2 on polymer | TiCl4 / water | not on the figures | not varied | 0.1 s / 3 s | not varied | 0.65 Å | no |
| TiO2 | TiCl4 / water | atmospheric, tubular | 75 to 135 °C, falling | 1 s, not varied | 120 s or more | 0.5 to 1.1 Å | no |
| hybrid Mg film | Mg(MeCp)2 / diol | pump-type, static | 100 to 250 °C, falling | 10 s / 5 to 10 s | 60 s pumping | 0.25 to 0.35 nm | no |
| IrOx | Ir precursor / O2-N2 plasma | atmospheric, spatial | 80 to 200 °C, falling | about 0.3 s for both, varied together | not applicable | 0.66 Å at 150 °C | estimated, from an assumed vapour pressure |
| La2O3, Fe2O3 on powder | diketonate, ferrocene / air in a hot zone | rotating evacuated tube | not varied | 9 min | evacuation | 0.017 and 0.030 nm, from mass gain | no |

- **What it shows about the pipeline.** A card per process can be filled from the saturation figures alone, and it shows at once that pulse times span four orders of magnitude for reactor reasons.
- **Verdict: holds partly.** The card works, but the brief's reference process in 10.1149_2.067203jes Fig. 4e-h is TMA with oxygen plasma, not TMA with water (its axes are plasma time and plasma purge). Reactor type is on no figure and was filled only where the text read so far states it. Partial pressure is known for one process and estimated for one.
- **Missing in the ontology.** A third or combined cycle step (two rows vary both steps together); a saturation-point quantity; reactor_type has no value for spatial.
- **Only in text or tables.** Reactor type and pressure for every row.

### N7. Parameter sensitivity across models

| Parameter raised | 10.1039_d1cp04758b Fig. 4 (thickness, lateral channel) | 10.1039_d3cp01829f Fig. 3-5 (coverage; model A diffusion, model B ballistic) | 10.1039_d3cp05639b Fig. 5-6 (coverage, porous sphere) | 10.3762_bjnano.5.25 Fig. 3, 4 (nanotube array) |
| --- | --- | --- | --- | --- |
| reactant pressure, 16 to 20 times | depth about 4 times (square root) | A 60 to 360, B 80 to 550 channel heights | (exposure in Fig. 3: square-root-like) | square root of concentration |
| pulse or exposure time | square root | A 250 to 830 for 10 times | same | square root |
| pressure times time held constant | not shown | profile unchanged in both models | not shown | not shown |
| molar mass | depth falls, about a factor 2 for 16 times | falls, A 300 to 190 for 5 times | falls, 170 to 105 for 5 times | not shown |
| site density (or 1 / site area) | depth falls, 270 to 60 µm for 10 times | falls (rises with site area) | falls, full to 90 µm for 8 times | falls as inverse square root, 95 to 21 µm for 20 times |
| sticking coefficient | depth nearly unchanged, front steepens | depth unchanged; slope rises 10 times in A, less in B | depth unchanged, only the tail | depth unchanged above about 0.01; broad at 1e-4 |
| temperature | slight fall | slight fall in both | rises at fixed number density, falls at fixed pressure (Fig. 8) | not shown |
| channel or pore width | deeper in µm, same in channel heights until narrowing matters | no effect in channel heights (aspect ratio series) | rises, 60 to 225 µm for 8 times the pore diameter | falls with tube radius |
| film density, inert gas pressure, desorption | change the thickness level, hardly the depth | not shown | tortuosity over porosity: falls, 225 to 80 µm | diffusivity: square root |

- **Where the models disagree.** The ballistic model gives about 1.5 times the depth and half the slope of the diffusion model for the same inputs, and twice the front width; its slope also depends on pressure and site area, which it does not in the diffusion model. The sign of the temperature effect depends on whether pressure or number density is held fixed, which only one paper states.
- **What it shows about the pipeline.** The trends agree across four independent models, so they can serve as a consistency rule for extracted experiments (for example: sticking moves the slope, not the depth).
- **Verdict: holds.**
- **Missing in the ontology.** Molar mass, site density, tortuosity, the slope and width of the front; a Knudsen number.
- **Only in text or tables.** The baseline values of every sweep.

### N8. Consistency check on pore closure
- **Question.** Does pore width over twice the planar growth per cycle predict the cycle at which pores close?
- **10.1039_c4nr05049e.** Stated: neck about 3 nm, small pore axis 3.8 nm, planar growth 0.55 Å per cycle, precursor size about 0.7 nm, break observed at cycle 23 to 24 (Fig. 6b, 7b, 8). Prediction from the neck: 27 cycles to zero width, 21 cycles to the precursor size. Observed 23 to 24 lies between. From the small axis the prediction is 35, which is wrong; the neck is what closes.
- **10.3390_separations11010024.** Stated: pore width about 5.5 nm (Fig. 6b, 7); permeance drops to its floor between cycle 21 and 28 for six membranes (Fig. 9). Planar growth at the same nominal conditions is read as about 0.48 Å in Fig. 4 and about 0.77 Å in Fig. 5, two figures of the paper that do not agree. Prediction: 57 or 36 cycles. The in-pore growth of Fig. 7 (0.33 nm in 12 cycles) predicts about 100. Observed closure is earlier than all three.
- **What it shows about the pipeline.** A cross-figure check can confirm a paper's own reasoning (first paper) and can expose an internal mismatch (second paper: two planar values, and permeance that ends long before the mean pore would be full).
- **Verdict: holds partly.** It holds for the first paper when the neck is used; it does not hold for the second, where Fig. 7 was made in a different reactor from Fig. 9 and permeance may be set by the narrowest pores.
- **Missing in the ontology.** A neck width as distinct from the pore width; a closure-cycle quantity; an amount-based growth per cycle.
- **Only in text or tables.** The planar growth and precursor size of the first paper. No value is missing in either paper; the second has two.

### N9. Structure equivalence and unusual profiles
- **Figures and findings.** 10.1021_acs.jpclett.4c03545: the same process gives step coverage 1 and 1.6 in an 18:1 vertical trench (Fig. 1, 2), while in lateral channels the film reaches 42 µm, an aspect ratio of 84, with and without krypton (Fig. 3, value in the body text). The lateral structure shows the limit the trench cannot show, and does not show the top-to-bottom effect the trench shows. 10.1116_6.0001094 states both an aspect ratio of 20 and an equivalent aspect ratio of 10 for one trench; 10.1021_acs.jpcc.5c06502 Table 1 does the same for its four samples. 10.1038_s41467-022-35428-6 Fig. 4b has the film thinnest at the top, by design; 10.1021_acs.jpclett.4c03545 reports step coverage above 1.
- **What it shows about the pipeline.** Two structures answer different questions about one process, so a "conformality" value needs its structure class. Profiles that rise with depth break any normalization to the top or the entrance and any reading of a half-thickness depth.
- **Verdict: holds.**
- **Missing in the ontology.** Nothing for AR and EAR (both entries exist and both are stated here). A reference value for profiles thickest at the bottom; a flag that step coverage may exceed 1; a link between two structures coated in one process.
- **Only in text or tables.** The 42 µm depth; the AR and EAR pairs.

## D. Update after 15 more papers (2026-10-13)

Fifteen PDFs were obtained by hand and parsed: Cremers refs 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228, 251 and 10.1021/acs.jpcc.1c01505. `figures.csv` now covers every paper with a PDF: the in-scope papers and 10.1016_j.cattod.2003.11.022 (Guyon 2004), which is out of scope as not an ALD paper and kept only as a cited source of recombination values; it counts in no number of corpus papers below. Parts A to C above are as written before that day; this part says what changes.

### Existing candidates whose evidence or verdict changes

- **A1.** Two more thermal alumina profiles: 10.1116_1.4903941 Fig. 5a (same channel type, 300 °C) and 10.1149_1.3072694 Fig. 5 (a 0.1 mm high hole). On x/H the half-thickness depths of six profiles from four papers lie between 104 and 269. Of the papers still needed, 10.1116/1.4903941 is now parsed; 10.1116/1.5093620 is still missing.
- **A2.** Two more fitted TMA values, from other structures: 0.009 to 0.02 in a cavity (10.1116_1.4971196) and 0.026 for the plasma process in holes (10.1063_1.2714685). Two values the review lists as results are not: 0.001 is quoted in 10.1021_cm0303080 from an earlier paper, and 0.1 is a chosen input in 10.1149_1.3072694.
- **A3.** 10.1021_acs.jpcc.1c01505 gives the slope plot for twelve conditions in one reactor: r of SiO2 falls from about 1e-4 to 3e-5 between 100 and 240 °C and from 2e-4 to 2e-5 between 12 and 130 mTorr. So "material and regime" is not enough: temperature and pressure inside one regime move r by a factor of ten. The model paper named as still needed (10.1149/1.3491381) is parsed; it is the origin of the three-regime scheme.
- **A4.** One more macroscopic plasma hole (10.1149_1.3301664 Fig. 2b) and one more low-pressure SiO2 series. The two macroscopic holes both reach half thickness at their end, so the "different structure scale" reading is confirmed for both.
- **A5.** Three more geometries with thickness or a thickness signal against depth: pores open at both ends (10.1021_cm0303080 Fig. 5a, an X-ray signal), a fibre-filled hole (10.1016_j.surfcoat.2012.02.038 Fig. 5), and a cavity entered through a central hole, where depth is radial (10.1116_1.4971196 Fig. 8). The case for a geometry class on every profile gets stronger; 10.1021/cm0303080 is no longer missing.
- **A7.** The two older models named as still needed are parsed (10.1149_1.3072694, 10.1002_cvde.200390005), with the Monte Carlo model of 10.1149_1.3491381. The claim that sticking moves the slope and not the depth is stated in all three.
- **A8.** Verdict moves from open to **holds partly**. Two sources test the square law of 10.1002_cvde.200390005 for TMA and water. For 10.1149_1.3072694 it predicts a coated aspect ratio of 49 at 9 × 10^3 L, against 47 and 53 read by eye and one fully coated structure of 33, so it matches. For 10.1021_cm0303080 it asks for 530 × 10^3 L, while the centre of the membrane was already coated between 150 and 450 × 10^3 L, so the model overestimates the need by about 1.2 to 3.5 times (membrane counted at half its length, as the source supports). See CREMERS.md 3a.
- **A9.** New values with a number: bottom over top of 52% to 100% at aspect ratio 8.7 against pulse time and cycles (10.1149_1.2789802 Fig. 3, 5), and 92% to 104% for Pt in trenches of aspect ratio 3 to 34 defined as mean trench thickness over planar thickness (10.1063_1.4972120 Table II). Two more definitions of the same word.
- **N1.** The third item is now traced: the low-pressure values in 10.1063_5.0168768 come from 10.1021_acs.jpcc.1c01505, which is in the corpus, and its Fig. 5A agrees with them. A second lineage appears: Tables V and VII of the review are updates of the tables of 10.1149_1.3491381, and one TMA value there goes back through 10.1021_cm0303080 to a still earlier paper, changing its method label on the way. Verdict stays "holds partly"; the part that did not hold is now explained.
- **N2.** More cases of both kinds. 10.1149_1.3072694 Fig. 6 is a simulation with a chosen sticking value that the review's Table V lists as a derived one. 10.1149_1.2789802 Fig. 6a and 7a and 10.1063_1.2714685 Fig. 9 are real predictions: bottom-of-hole curves computed from parameters fitted elsewhere.
- **N3.** Five more labels: "relative ZnO coverage" (an X-ray signal over its maximum, 10.1021_cm0303080), "precursor coverage" (thickness over cycles and a chosen saturation level, 10.1116_1.4971196), "thickness (%)" (simulated, over saturation, 10.1149_1.3491381), "normalized Al concentration" called relative thickness in a caption (10.1016_j.surfcoat.2012.02.038), and "conformality (%)" as mean trench thickness over planar thickness (10.1063_1.4972120).
- **N4.** Five more derivations, three with a stated uncertainty: microprobe line scan with 3 to 5 µm resolution; X-ray signal on fibres with error bars; micro-spot ellipsometry with a 10 µm spot and 3% error; plan-view TEM cuts with depth known to 10 nm; and, in one paper, SEM (4 nm, about 12%) against TEM (160 values, spread 3 nm) on the same trench type.
- **N6.** Five more processes, and the reactant partial pressure is stated in four of them (0.3 Pa, 0.08 Pa, 0.15 Torr and 0.01 Torr of TMA). The count of processes with a known partial pressure goes from 1 of 12 to 5 of 17.
- **N7.** Four more models agree on the two main trends (depth with the square root of exposure, slope with sticking). 10.1149_1.3491381 adds the recombination probability: it sets the dose and bends the profile near the bottom.
- **N9.** Two papers state the equivalence of a trench of aspect ratio 20 and a pore of 10 (10.1063_1.4972120, 10.1149_1.3491381). 10.1016_j.surfcoat.2012.02.038 and 10.1149_1.3301664 give thermal and plasma profiles in one structure at the same exposure.

### New candidates

### N10. The square law across papers
- **Question.** Does the exposure needed for full coverage grow with the square of the aspect ratio in measured data from different groups?
- **Figures.** 10.1002_cvde.200390005 Fig. 2, Fig. 3 (model and hafnia holes); 10.1149_1.3072694 Fig. 5; 10.1021_cm0303080 Fig. 3, Fig. 5, Fig. 13.
- **What it shows about the pipeline.** The comparison needs three things the review's rows do not carry: an exposure in pressure times time, an aspect ratio on one definition, and whether a pore is entered from one end or two.
- **Verdict: holds partly** for TMA and water, with a saturation density assumed from a third paper: the prediction matches 10.1149_1.3072694 (49 against 47 to 53) and overestimates the need for 10.1021_cm0303080 by about 1.2 to 3.5 times. For hafnia the source's own test holds (coated to a quarter, three quarters, fully at 2, 4, 30 × 10^3 L).
- **Missing in the ontology.** An entry or qualifier for one-sided against two-sided entry; a transform from depth, width and structure class to the equivalent aspect ratio; the saturation density as a quantity.
- **Only in text or tables.** Pressures and pulse times, in all three papers.

### N11. A recombination probability belongs to a surface state, not to a material
- **Question.** Can a literature value of r for "titania" or "alumina" be used for the film during growth?
- **Figures.** 10.1016_j.cattod.2003.11.022 (out of scope, cited source) Table 1, Fig. 5; 10.1021_acs.jpcc.1c01505 Fig. 5; 10.1063_5.0168768 Fig. 3; 10.1021_acs.jpcc.9b08176 Fig. 3; the review's Table VII.
- **What it shows about the pipeline.** A value without temperature, pressure, method and kind of surface cannot be joined to a process. The same material name carries values 350 times apart with opposite temperature trends.
- **Verdict: holds.** Sintered ceramic in a 110 Pa air plasma: 0.014 at 300 K, rising. ALD film in a lateral channel: about 4e-5 at 100 to 180 °C, falling.
- **Missing in the ontology.** Conditions on a recombination probability (temperature, pressure, method); a way to say what the surface is (bulk ceramic, growing film, film covered with ligands).
- **Only in text or tables.** The ceramic values (a table); the conditions of both.

### N12. Thermal and plasma in one structure at one exposure
- **Question.** How much less deep does the plasma process coat when everything else is equal?
- **Figures.** 10.1016_j.surfcoat.2012.02.038 Fig. 10; 10.1149_1.3301664 Fig. 2a-b, Fig. 9, Fig. 10.
- **What it shows about the pipeline.** The review lists these papers as unmatched rows (different exposure, different structure). The matched pair exists only inside each paper and has to be read from the figures.
- **Verdict: holds.** About six times less deep in a fibre plug at 75 °C; in an empty hole of aspect ratio 22 the thermal film is complete and the plasma film reaches half thickness near 14. In the second paper a thermal side reaction with water formed in the plasma step makes the plasma profile look better than recombination alone would give; a cobalt oxide profile without that side reaction is much sharper.
- **Missing in the ontology.** A link between two series that differ in one condition only; a note that a profile is the sum of two reactions.
- **Only in text or tables.** The statement that conditions are equal; pressures.

### N13. How many points does a sticking coefficient rest on?
- **Question.** Which published sticking values come from profiles dense enough to fix them?
- **Figures.** 10.1016_j.apsusc.2009.02.055 Fig. 3 (4 points); 10.1016_j.apsusc.2010.01.025 Fig. 1 (4 to 5 points each); 10.1116_1.4971196 Fig. 8, 9 (about 100 points); 10.1063_1.5028178 Fig. 6 (about 85 points); 10.1149_1.3072694 Fig. 5 (about 20 points, no fit made).
- **What it shows about the pipeline.** The number of points in the slope region is a property the knowledge base can hold for every fitted value; the review itself asks for it (its Sec. VI B 3).
- **Verdict: holds partly.** The counts are as given (profiles.csv); whether few points make a value wrong cannot be said here. The two hole-based papers give error ranges from shifting their points by 10 nm, and one paper with 20 points declines to fit because the pressure is not known well enough.
- **Missing in the ontology.** Fit quality and the number of points behind a fitted value (v0 sent fit quality to unmapped).
- **Only in text or tables.** The stated uncertainties.

## E. Cross-paper synthesis (third search, 2026-10-13)

Each candidate below needs data from three or more papers put on one axis or through one method, and its answer is stated by none of them. Inputs come from `quantity_matrix.csv` (58 in-scope papers with a PDF, 14 quantities; cells give where a value is, read by hand for the 24 conformality papers and found by keyword for the rest). Nothing is computed here except the by-eye pilots at the end, which are marked.

### S1. One method for every sticking coefficient
- **Question.** If the same method is applied to every digitizable measured profile, do the sticking values of TMA (and other precursors) agree better than the values the papers report?
- **Papers and figures.** 10.1063_1.5028178 Fig. 6, 7; 10.1039_d0cp03358h Fig. 9, 11 and Table 1 (slopes); 10.1116_1.4903941 Fig. 5; 10.1149_1.3072694 Fig. 5; 10.1149_1.3301664 Fig. 2a, 6a (thermal); 10.1016_j.surfcoat.2012.02.038 Fig. 5; 10.1021_cm0303080 Fig. 5a, 6a; 10.1116_1.4971196 Fig. 8; 10.1016_j.apsusc.2009.02.055 Fig. 3; 10.1016_j.apsusc.2010.01.025 Fig. 1, 3.
- **What to compute.** Digitize each profile, normalize it to its plateau, put depth in units of the limiting width, and apply one relation between the slope at half thickness and the sticking coefficient (the free-molecular slope relation used by 10.1039_d0cp03358h), or one model fit; compare with each paper's own value and method.
- **Inputs.** Profile and width: present in all eleven. Plateau: absent in the TiO2 profiles of 10.1063_1.5028178 and 10.1116_1.4903941. Exposure: needed only for a full fit; stated in 10.1149_1.3072694, 10.1149_1.3301664, 10.1016_j.surfcoat.2012.02.038, 10.1021_cm0303080. Geometry outside the slope relation's validity: fibre plug (10.1016_j.surfcoat.2012.02.038), radial cavity (10.1116_1.4971196), two-sided pores (10.1021_cm0303080).
- **Usable now.** About 6 lateral-channel and macro-hole profiles for the slope method; 3 more with a geometry-specific model. Missing PDFs that add most: 10.1116/1.5093620 (Arts 2019, the slope method and its water and TMA profiles), ref. 87 (Mattinen 2016, four Ir profiles in channels).
- **Possible finding (hypothesis).** The reported TMA values span 0.0005 to 0.026; one method may narrow this to a factor of a few, with the remainder tied to temperature and to the probe's lateral resolution.
- **Ontology.** `initial_sticking_coefficient` exists; v0 lacks the method and model as attributes of a value, and the probe resolution.
- **Feasibility: feasible partly** (digitizing needed; three profiles have too few points, see profiles.csv).

### S2. Exposure needed against equivalent aspect ratio across structures
- **Question.** Plotted as exposure against EAR on one scale, do holes, pores, macroscopic holes, fibre plugs and lateral channels lie on one curve near Gordon's square law?
- **Papers and figures.** 10.1002_cvde.200390005 Fig. 2, 3 and text; 10.1021_cm0303080 Fig. 3, 5, 13; 10.1149_1.3072694 Fig. 5; 10.1149_1.3301664 Fig. 2a; 10.1016_j.surfcoat.2012.02.038 Fig. 5; 10.1063_1.2714685 Fig. 7; 10.1149_1.2789802 Fig. 3; the review's Table II rows with an exposure.
- **What to compute.** Exposure in Pa·s from partial pressure and time; EAR from each structure's dimensions with the review's formulas (and half length for two-sided pores); a mark for fully coated (lower bound) or half-thickness depth (measured); Gordon's curve per precursor with its saturation density.
- **Inputs.** Partial pressure stated in 7 of these papers; absent in the lateral-channel papers (10.1039_d0cp03358h gives it only as a model input) and in 10.1116_1.4971196 and the two Rose papers. Saturation density per precursor: estimated from planar growth.
- **Usable now.** 7 papers, with TMA, DEZ and Hf amide. Missing PDFs: ref. 96 (Elam 2006, the AAO record rows), ref. 135, ref. 139 (rows with an exposure), ref. 166 (W at the largest exposure).
- **Possible finding.** Gordon's curve matches one source and overestimates the need for another by 1.2 to 3.5 times (Case 8); across seven sources the scatter around the curve may group by structure class.
- **Ontology.** `exposure` exists with a species qualifier; v0 lacks the one-sided or two-sided entry and an EAR transform per structure class.
- **Feasibility: feasible partly.**

### S3. O-radical recombination on SiO2 and TiO2 against temperature and pressure
- **Question.** Do the recombination probabilities from different reactors and pressures fall on one trend with substrate temperature and pressure?
- **Papers and figures.** 10.1021_acs.jpcc.1c01505 Fig. 5; 10.1021_acs.jpcc.9b08176 Fig. 3 and text; 10.1063_5.0168768 Fig. 3, Table I; 10.1021_acs.jpcc.5c06502 text (IrOx); 10.1149_1.3491381 Table II (literature); the review's Table VII; 10.1016_j.cattod.2003.11.022 Table 1 (out of scope, cited source).
- **What to compute.** r against substrate temperature with pressure as a second variable, one symbol per reactor and surface kind (growing film, bulk or ceramic).
- **Inputs.** Temperature and pressure present in all four ALD papers; the surface kind is implicit in the literature tables.
- **Usable now.** 4 ALD papers, 2 literature tables, 1 cited source. Missing PDFs: ref. 252 and ref. 250 are excluded (not ALD), so the literature values stay cited; in scope, refs 198 and 203 would add plasma SiO2 conformality without r.
- **Possible finding.** On growing SiO2 r falls with temperature and pressure within one reactor and is higher at atmospheric pressure; the bulk-surface values sit two orders above and rise with temperature.
- **Ontology.** `recombination_probability{species, surface}` exists; v0 lacks temperature, pressure and the surface kind as conditions of the value.
- **Feasibility: feasible now.**

### S4. Thermal against plasma depth at equal structure and exposure
- **Question.** Across papers, how much shallower is plasma ALD than thermal ALD at equal structure and exposure, and does the ratio follow the regime diagram of 10.1149_1.3491381?
- **Papers and figures.** 10.1016_j.surfcoat.2012.02.038 Fig. 10; 10.1149_1.3301664 Fig. 2; 10.1149_1.3491381 Fig. 9; 10.1063_1.2714685 and 10.1149_1.2789802 (plasma only, with exposure); 10.1063_1.4972120 (plasma Pt, full coverage).
- **What to compute.** Depth ratio at equal exposure; position of each case on the r-against-aspect-ratio diagram.
- **Inputs.** Matched pairs exist in 2 papers; r for the matched surfaces is only in literature tables.
- **Usable now.** 2 matched pairs and 3 plasma-only papers. Missing PDFs: ref. 198 (five plasma rows), ref. 69's companion work.
- **Possible finding.** Thermal side reactions make the measured ratio smaller than recombination alone predicts.
- **Ontology.** v0 lacks a link between two series differing in one condition.
- **Feasibility: not yet** (two pairs).

### S5. Channel narrowing
- **Question.** Does the loss of step coverage or of half-thickness depth with film thickness follow one curve in film thickness over channel height?
- **Papers and figures.** 10.1149_1.2789802 Fig. 5; 10.1039_d0cp03358h Fig. 9d-f, Table 1; 10.1116_1.4903941 Fig. 5b; 10.1039_d1cp04758b Fig. 5e (model).
- **What to compute.** 1 − 2s/H on x for each sample (s from the plateau or the top thickness), coated depth over H or step coverage on y, against the model curve.
- **Inputs.** Thickness and H present in all four; for 10.1116_1.4903941 only the 200 nm gap closes.
- **Usable now.** 3 experiments plus the model. Missing PDFs: ref. 89 (trench rows with thickness and depth).
- **Possible finding.** The experiments fall below the model once 2s/H exceeds about 0.3.
- **Ontology.** v0 lacks the open fraction of a channel as a derived quantity.
- **Feasibility: feasible partly.**

### S6. Where depth in units of channel height stops scaling
- **Question.** Does half-thickness depth over H stay constant from 0.1 µm channels to 1 mm holes, and where does it break as the Knudsen number falls?
- **Papers and figures.** 10.1039_d0cp03358h Fig. 9 (0.1 to 2 µm); 10.1116_1.4903941 Fig. 5b (0.2 to 1 µm); 10.1149_1.3072694 Fig. 5 (0.1 mm); 10.1149_1.3301664 Fig. 2a (thermal, 0.5 mm); 10.1039_d4cp00131a Fig. 5, 8 (model).
- **What to compute.** Knudsen number from the reactor pressure and H; depth over H at comparable exposure.
- **Inputs.** Reactor pressure in text for all; exposure not comparable across them (missing in the lateral-channel papers).
- **Usable now.** 4 experiments, but at unmatched exposures. Missing PDFs: 10.1116/1.5093620.
- **Possible finding.** The microscopic channels sit in the free-molecular plateau of the model; the macroscopic holes do not.
- **Ontology.** v0 lacks a Knudsen number.
- **Feasibility: feasible partly.**

### S7. Planar saturation exposure of TMA across reactors
- **Question.** In one unit, how much TMA exposure saturates a flat surface in each reactor?
- **Papers and figures.** 10.1002_adem.202201901 Fig. 1b (dose in Torr); 10.1063_1.2714685 Fig. 7a (flat surface, injection time at 0.01 Torr); 10.1021_cm0303080 text (about 10^4 L, quoted); 10.1021_acsami.0c22121 Fig. S1 (TiCl4, no pressure); 10.1149_2.067203jes Fig. 4e (TMA with plasma, time only).
- **What to compute.** Exposure at 90% of saturated growth in Pa·s.
- **Inputs.** Pressure stated in 2 of 5.
- **Usable now.** 2 to 3. Missing PDFs: refs 236, 235 (sticking by QCM and Auger), ref. 237.
- **Possible finding.** The quoted saturation exposures differ by more than the sticking values imply.
- **Ontology.** v0 lacks a saturation-point quantity.
- **Feasibility: not yet.**

### S8. Planar growth per cycle of TMA/water and TMA/O2 plasma against temperature across reactors
- **Question.** On one plot, how far do reactors disagree on the growth per cycle at the same temperature?
- **Papers and figures.** 10.1002_adem.202201901 Fig. 2a; 10.1016_j.surfcoat.2012.02.038 Fig. 9; 10.1039_d0cp03358h Table 1; 10.1149_1.3072694 text; 10.1021_cm0303080 text; 10.1116_1.4971196 text; 10.1063_1.2714685 Fig. 7 (plasma); 10.1116_6.0001094 text (plasma); 10.1149_2.067203jes Fig. 4e-h (plasma reference); 10.1063_1.5028178 Table I (model value, kept apart).
- **What to compute.** Growth per cycle against temperature, measured values only, one symbol per reactor; thermal and plasma apart.
- **Inputs.** Temperature and growth per cycle stated in all; whether doses were saturating is stated in about half.
- **Usable now.** 6 thermal, 3 plasma. Missing PDFs: none essential; many planar papers outside the conformality scope (Popov rows) would add the most.
- **Possible finding.** Reactors agree near 200 to 300 °C and disagree by up to 1.5 times below 150 °C.
- **Ontology.** `growth_per_cycle{position=planar}` exists; v0 lacks a flag for saturated dosing.
- **Feasibility: feasible now.**

### S9. Pore-closure cycle against pore width over growth per cycle
- **Question.** Does the cycle at which pores close follow pore width over twice the planar growth per cycle across papers?
- **Papers and figures.** 10.1039_c4nr05049e Fig. 6b, 7b, 8; 10.3390_separations11010024 Fig. 7, 9; 10.1021_cm0303080 text (65 to 39 nm after 100 cycles); 10.1116_6.0003182 (porosity loss, mass gain).
- **What to compute.** Predicted against observed closure cycle.
- **Inputs.** Pore width and planar growth stated in 3; closure observed in 2.
- **Usable now.** 2 (N8 showed one agreement and one mismatch). Missing PDFs: 10.1021/la300045z, 10.1021/jp111314b.
- **Possible finding.** The neck, not the mean pore, sets closure.
- **Ontology.** v0 lacks a neck width and a closure cycle.
- **Feasibility: not yet.**

### S10. Temperature dependence of sticking and recombination across precursors (new)
- **Question.** Put on one Arrhenius plot, do the fitted sticking coefficients of different precursors and the recombination of O radicals share a sign and size of activation?
- **Papers and figures.** 10.1016_j.apsusc.2010.01.025 Fig. 4, Table 4 (Hf and Ti amides); 10.1149_1.2789802 Fig. 7b (TTIP); 10.1016_j.sse.2022.108584 Table 1, Fig. 5a (water); 10.1021_acs.jpcc.1c01505 Fig. 5A (O on SiO2, TiO2); 10.1116_1.4903941 Fig. 3 and text (penetration against temperature, qualitative).
- **What to compute.** ln of each value against 1/T; slopes per series.
- **Inputs.** Values with temperatures present in 4 papers.
- **Usable now.** 4. Missing PDFs: ref. 237, 238 (sum-frequency sticking at several temperatures).
- **Possible finding.** Precursor sticking rises with temperature in all three amide and alkoxide series, while O recombination on growing films falls.
- **Ontology.** v0 lacks temperature as a condition on model parameters.
- **Feasibility: feasible now.**

### S11. Growth above the planar value near the entrance (new)
- **Question.** How common is a thickness or growth per cycle above the planar or plateau value near the entrance of a structure, and does it scale with dose?
- **Papers and figures.** 10.1116_1.4971196 Fig. 8 (above the test-wafer value near small holes); 10.1116_6.0001094 Fig. 11, 12 (points above 1); 10.1039_d0cp03358h Fig. 3b, Table 1 (initial thickness above the outside value); 10.1149_1.3301664 Fig. 6a (slow early decline); 10.1021_acs.jpcc.1c01505 Fig. 3A (TiO2 jump at the entrance).
- **What to compute.** Excess over the planar value against dose and structure.
- **Inputs.** Planar reference present in 4 of 5.
- **Usable now.** 4.
- **Possible finding.** The excess appears when water purge is short or the opening small, a CVD-like contribution the self-limiting models leave out.
- **Ontology.** v0 lacks a reference value for an entrance excess.
- **Feasibility: feasible partly.**

### Ranking and pilots

| Rank | Candidate | Papers usable now | Inputs | New | Link |
| --- | --- | --- | --- | --- | --- |
| 1 | S8 planar growth against temperature | 9 | complete | yes, no paper compares reactors | twin prior for saturated growth; agent recipe questions |
| 2 | S3 recombination against temperature and pressure | 4 plus 2 tables | complete | yes | twin prior for r |
| 3 | S1 one method for sticking | 6 now, 9 with models | partial (digitizing) | yes | twin calibration and priors |
| 4 | S10 Arrhenius across precursors | 4 | complete | yes | twin priors with temperature |
| 5 | S2 exposure against EAR | 7 | partial (partial pressure in 7 only) | partly (Case 8 began it) | agent: how much dose for a structure |
| 6 | S11 entrance excess | 4 | partial | yes | twin model limits |
| 7 | S5 channel narrowing | 3 | partial | yes | twin model check |
| 8 | S6 Knudsen break | 4 | exposures unmatched | partly | twin validity range |
| 9 | S4, S7, S9 | 2 to 3 | too few | — | — |

**Pilot S8 (by eye, pilot).** Growth per cycle in Å, TMA and water: 10.1016_j.surfcoat.2012.02.038 Fig. 9 reads 0.66 at 50 °C, 0.67 at 100, 0.85 at 150, 1.0 at 200, 0.96 at 250, 0.94 at 300; 10.1002_adem.202201901 Fig. 2a reads 0.96 at 35, 0.93 at 60, 0.94 at 80, 0.96 at 100, 1.02 at 125 and 150; text values add 1.0 at 200 (10.1149_1.3072694), 1.29 at 177 (10.1021_cm0303080), 1.19 and 1.29 at 200 (10.1116_1.4971196), and 0.93 to 1.03 at 300 (10.1039_d0cp03358h Table 1). Impression: informative. The two reactors that both span low temperature differ by about 1.4 times at 50 to 100 °C and agree within 0.05 Å at 150 °C and above; the 177 to 200 °C text values spread from 1.0 to 1.3.

**Pilot S3 (by eye, pilot).** r of O on SiO2: about 1e-4 at 100 °C, 6.5e-5 at 180, 3e-5 at 240 (50 mTorr), and 2.5e-4 at 12 mTorr down to 2e-5 at 130 mTorr (10.1021_acs.jpcc.1c01505 Fig. 5); 6e-5 at 200 °C (10.1021_acs.jpcc.9b08176); 4e-4 at 100 °C, atmospheric (10.1063_5.0168768); literature 2e-4 and 4e-4; cited ceramic values 4e-3 to 9e-3 (out of scope, cited source). TiO2: 4e-5 at 100 and 180 °C, below 1e-5 at 240; 7e-5 at 200 °C; 6e-5 atmospheric; literature 1.4e-2. Impression: informative for SiO2 (a clear trend within one reactor and an order of magnitude between regimes); for TiO2 the ALD values cluster within a factor of two and the outlier is the bulk value.

**Pilot S1 (by eye, pilot).** Front width from 80% to 20% of the plateau, in channel heights: about 36 for 10.1063_1.5028178 Fig. 6 (Al2O3, 0.5 µm gap), about 30 for 10.1039_d0cp03358h Fig. 9 (H 500 nm), about 20 for 10.1149_1.3072694 Fig. 5 (aspect ratio 100, 0.1 mm hole); 10.1116_1.4903941 Fig. 5a never reaches 20% (a floor near 22 nm). The papers' own TMA values for the first three are 0.0057 (fit), 0.004 (slope) and 0.1 (chosen). Impression: informative but confounded: the widths differ by less than a factor of two while the reported values differ by 25 times, and probe resolution and channel narrowing both widen fronts.

## F. Within-paper candidates (third search)

Brief; each with the field that matters most. "Cross-paper" marks those that grow by adding other papers.

- **E1. Saturation is local.** 10.1063_1.2714685 Fig. 7a, 10.1149_1.2789802 Fig. 3a, 6a, 7a, 10.1002_cvde.200390005 Fig. 2: growth per cycle on the flat surface saturates within seconds while the hole bottom needs ten to a hundred times longer. Verdict: feasible now. Cross-paper: yes, joins S2 (the ratio of bottom to flat saturation time against aspect ratio).
- **E2. Calibrate once, predict elsewhere.** 10.1063_1.2714685 Fig. 7a (fit) against Fig. 9 (second pressure); 10.1149_1.2789802 Fig. 3a (fit) against Fig. 6a and 7a. Each paper states that the prediction agrees; nobody quantifies by how much. Verdict: feasible now (two predictions per paper). Cross-paper: yes, with 10.1016_j.sse.2022.108584 Fig. 7 (N2).
- **E3. Parameters as functions of temperature.** 10.1016_j.apsusc.2010.01.025 Fig. 4, 10.1149_1.2789802 Fig. 7b. Verdict: feasible now; it is S10 within each paper.
- **E4. How well a fitted value is determined.** Misfit curves: 10.1116_1.4971196 Fig. 10, 13 (flat over a factor of 30 for TMA, narrow for BDEAS); 10.1016_j.apsusc.2009.02.055 Fig. 4; 10.1016_j.apsusc.2010.01.025 Fig. 2, 3 (shifted-profile ranges). Verdict: feasible now. Cross-paper: yes, joins N13 (points behind a value).
- **E5. Properties along the depth.** 10.1149_1.3301664 Fig. 5d (AlN refractive index falls with depth), Fig. 8 to 10 (water from the plasma step); 10.1021_acs.jpclett.4c03545 Fig. 4 (XPS at the opening and inside); 10.1116_6.0002804 Fig. 10 (oxygen share doubled at the trench bottom, text). Verdict: feasible partly (qualitative in two of three). Cross-paper: yes, a composition-against-depth case across these three.
- **E6. Conformality depends on how much was deposited.** 10.1149_1.2789802 Fig. 5 (step coverage 73% to 52% from 200 to 500 cycles); 10.1116_1.4903941 Fig. 5b (the 200 nm gap closes). Verdict: feasible now. Cross-paper: it is S5.
- **E7. A worked example end to end.** 10.1149_1.3301664 (structure, conditions, profiles at four settings, emission spectrum, Monte Carlo with two side reactions) or 10.1039_d0cp03358h (16 samples, Table 1 with every derived number, simulation). Verdict: feasible now; 10.1039_d0cp03358h is the better choice because Table 1 lets every derived number be checked against its profile.
