# gre23 (10.1116_6.0003182), v2 fresh extraction: notes

Built by a one-off script kept outside the repo (scratchpad `q8/build_gre23.py`). Rows: sample 24, condition 73, series 46, value 127, coverage 202.

## Decisions
- **Samples.** There are three 20-cycle runs (`R120`, `R160`, `R120-160`). Each run coated two NPCs (`-NPC1/2`, pieces), and their `-pair` group holds the Table I pair values: mass gain, final porosity, GPC, Δn_s and coating thickness. Δn_g and ȳ come from the chamber gas, so they sit on the run. Each run has one resistivity prism (`-prism`, piece), and the three prisms form the group `prisms`. The text does not say which NPC of a pair went to XRD, EDS and the photographs, so those series and values sit on the run.
- **Other samples.** The Fig. 2d temperature log comes from a separate test run (`Rtest`) under the cycled schedule. The uncoated compact in Fig. 4a is `bare` (reference). The other groups are `runs`, `lowT` (statements made jointly for 120 and 120/160) and `compacts` (pressing recipe and compact geometry). The Eq. 2 purge estimates are the model runs `eq2-120` and `eq2-160`, and their shared inputs ν and θf sit on the group `eq2`.
- **Temperature.** The cycled run has two set_point rows. One is 120 °C with applies_when "every step except the H2O purge". The other is 160 °C with step=purge_B. The 33.5 min ramp is its own row. The ±5 °C calibration scatter and the definition of T go in the note.
- **Hold times.** The DEZ and H2O holds are quantity `other`, label "DEZ hold"/"H2O hold", qualifiers step=hold_A/hold_B, 1920 s. The note says each hold was sized with Eq. 1. Eq. 1 gives no numbers.
- **Exposure.** ~9 Torr becomes 1200 Pa and ~17 000 Torr s becomes 2.27e6 Pa s, with the printed values in the notes. Pulse times are ranges ("10-14", "8-11" s) because a condition has a single value field.
- **Equations.** eq3 is used for Δn_s (solid taken as ZnO). eq4 and eq5 are used for x > 1, read from the sign of the hold pressure change, and for the literature x values. ȳ is linked through eq6 plus eq7 (120 and 120/160) or eq8 (160, c from Zn metal). eq2 gives the 360 min and 11 min purge estimates.
- **Points.** The three Zn line scans (Fig. 6d–f) come from cases/points.json. There are no v1 points for this paper. A few values were read by eye and are marked "read by eye" in the note: the Fig. 2d temperature peak and base, the Fig. 3b/3c maxima for 160 °C, and the Zn minimum in 6e.
- **Data kinds.** GPC, final porosity, Δn_s, Δn_g, ȳ and the coating thicknesses are `calculated`. Mass gain is `measured` by gravimetry. The XRD wt% and crystallite sizes are `fit` (Rietveld / Halder–Wagner). Resistivity is `measured`. The initial porosity is `measured` because the method is not stated.

## Source problems
1. **Fig. 3(a) paragraph.** This paragraph was missing from the first inventory and now has its own element, s12.x1. The rows taken from it (plateau, time to maximum and terminal slope for 120/160 and 120, and the 10 mTorr recording resolution) cite s12.x1 first.
2. **Porosity order.** The text (s12.p1) lists the final porosities 36.7, 30.6 and 38.0 % in the order 120/160, 120, 160. That contradicts Table I (120: 36.7, 160: 30.6, 120/160: 38.0) and the mass gains, since more gain must mean lower porosity. The table order is kept.
3. **Text-layer errors.** ȳ is printed as ν̄ in the text layer (s12.p14–17, Table I header). The Table I caption and s12.p1 call the initial porosity φf / φ1. s12.p17 says "c in Eq. (4)" where Eq. (8) is meant. s9.p7 cites "supplementary material 14" where 44 is meant. The Fig. 4 caption has "NS" for NPC.
4. **SI figure numbers.** The SI numbering is inconsistent. s12.p2 puts the remaining 15 cycles in Fig. S2, but the Fig. 2 caption says Fig. S1, and s8.p1 uses Fig. S1 for the cracks.
5. **Duplicate elements.** Caption copies in the body (s9.p2, s12.p12, s12.p16, s13.p5, s14.p3, s14.p4, s14.p9, s15.p6) are marked "no knowledge: duplicate" unless a row also cites them.

## Abstract check
Nothing new. The porosity, d_NP, thickness, AR, >1e4 Torr s exposure, the schedules, GPC ~2.1 Å and near-surface depletion all reach rows from the body.
