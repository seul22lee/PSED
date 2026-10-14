# Notes: 10.1116_6.0003182 (gre23)

Tables built by a script kept in the session scratchpad (not in the repo). Quantity ids are from ontology.yaml where one exists; every other id is marked "(new)" in the quantity column (37 condition ids, about 25 value/series ids, e.g. hold_time, porosity, mass_gain, gas_moles_gain, terminal_slope, eds_normalized_counts, crystallite_size).

**(a) Sweep plots where each point is a different run.** There are none in the usual sense. The paper has three runs (120, 160, cycled 120/160) and each panel draws one curve per run (Fig. 3a-c, Fig. 5), so each curve is one series on one run sample. In Fig. 3b/3c, each point is one *cycle* of a single run, not a separate run, so the x axis is cycle_number inside one sample. The run is the unit the paper calls a "sample" (Table I/II rows), and each run coated **two** NPCs. I modelled the run as the sample (gre23:120, :160, :120/160) and gave each run two child NPCs (u1-u6). Table I values are pair means or pair totals, so they sit on the run sample.

**(b) One sample measured by several methods.** gre23:160 has weighing (v024), pressure traces (s2b, s3a-c_160), photo (s4c), XRD (s5_160 → v047-v050), SEM-EDS maps and line scans (s6b_*, s6e_*) and resistivity. Resistivity was measured on a prism cut from one NPC (gre23:u8, parent gre23:160). The paper does not say which NPC of the pair, so the prism's parent is the run and not u3/u4.

**(c) A value read from or fitted to a series.** v087 (Zn plateau 5.7) and v089 (centre minimum/maximum 0.89) come from the points.json Zn series of Fig. 6e (from_series gre23:s6e_Zn). Check: the points.json plateaus 3.75 (120 C) and 3.3 (cycled) give 3.75/3.3 = 1.14, which agrees with the 12 % higher Zn signal stated in the text (v081). The XRD wt% values (v043-v054) are fits to s5_* and carry from_series.

**(d) A condition stated once for the whole paper.** These use sample_id "*": partial pressure ~9 Torr, hold 1920 s, purge 2880 s, 20 cycles, sources at 37 C. "*" then also covers the bare NPC (u10) and the test run (u11), which is not quite right for u10.

**(e) What did not fit, and the smallest fix for each.**
1. Cycled temperature per step: the condition step vocabulary has only one "purge", so the DEZ purge (120 C) and the H2O purge (160 C) can be told apart only by evidence text. Fix: step values purge_A / purge_B.
2. Static dosing has three phases per reactant: pulse (10-14 s), hold (1920 s) and purge. The ontology has only pulse_time, and its exposure definition is pulse pressure × pulse time, which is wrong here: the exposure comes from the hold. Fix: add hold_time (step-qualified), and define exposure as partial pressure × (pulse + hold) for static dose.
3. Characterization settings (XRD, EDS, XPS, electrodes) and substrate preparation (pressing) were put in condition.csv as "(new)" quantities. Fix: add a `context` column (deposition | substrate_prep | characterization).
4. Fig. 6d-f has its axes swapped (position on y, counts on x). The x_id/y_id follow the printed axes, and `distance` is measured from the top of the section with entry from both faces. Fix: an `axes_swapped` flag and an `origin` qualifier on distance (top face, two-sided).
5. An EDS signal is not a film thickness: there is no quantity for an element-signal profile, so I used eds_normalized_counts / zn_profile_shape (new). Images and photos have no x/y quantity (x_id "none").
6. `x_by` was read as "what x is measured from / its origin". The column needs a definition.
7. Group sample "*" cannot express "all coated runs". Fix: allow a group id such as gre23:runs.
8. Inconsistencies in the paper, recorded and not resolved: (i) Sec. III A lists final porosities in the order 120/160, 120, 160 as 36.7, 30.6, 38.0, but Table I gives 120 = 36.7, 160 = 30.6, 120/160 = 38.0. The table is physically consistent (largest mass gain, lowest porosity), so I used it. (ii) The Fig. 2 caption sends readers to Fig. S1 for all 20 cycles, while the text says Fig. S2. (iii) "high c in Eq. (4)" should read Eq. (8). (iv) The parsed document.md renders ȳ as ν̄ (Table I and text). The table crop shows ȳ.
9. Literature values (41 rows) have no sample. They are kept as value rows with sample empty. A `cited_ref` column would help.

**(f) Row counts.** paper 1, sample 14, condition 64, series 44 (3 with points from points.json), value 125 (41 literature), link 48.

**(g) V1 comparison.** Skipped: there is no v1 folder for this paper.
