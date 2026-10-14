# Notes: 10.1039_d0cp03358h (Yim 2020, key yim20)

**(a) Sweep plots.** Every point or curve in a sweep is its own sample, keyed by its Table 1 sample code. Fig. 9a-c (H 100/500/2000 nm) maps to samples 7, 8 and 9. Fig. 11a (TMA 0.1/0.2/0.4 s) maps to samples 12, 13 and 14. No group samples were made; the "series" (A-F) of Table 1 stays in the evidence text. Samples 8 and 12 appear in two Table 1 series each. They are recorded once, and the repeated row is noted. Fig. 8a has 9 legend entries, which are repeated scans on four channels (L 0.1-5 mm) of sample 8. These became four child samples (u2-u5, parent_sample yim20:8) with one series row per scan.

**(b) One sample, several methods.** Sample 11 has three measurements: an SEM image with an Al-Kα map (Fig. 5a, extent about 125 µm, v145), an EDS line scan (Fig. 5b, three series), and a reflectometer profile (Fig. 9d-f, plus the Table 1 row). Samples 4, 5 and 6 are one sample type measured at three spot sizes; the paper gives them separate codes, so they stay separate samples.

**(c) A value read from or fitted to a series.** The front slopes in Table 1 are the authors' linear fits to the scaled and normalized profiles (data_kind fit, e.g. v007). Values I read from points.json have from_series set, for example v211, x~ at θ = 0.5 for F9c-H500 = 213.1 against 214 in the Table. Table 1 values themselves have no from_series: footnote f says they come from averaged scans over several channels, which is not exactly the plotted curve. c_TMA 4e-3 (v177) is derived from fitted slopes of four samples (arts_slope).

**(d) A condition stated once for the whole paper.** 300 °C, about 3 hPa, N2 150 sccm and the Picosun R-150 reactor are written as `*` rows. Pulse and purge times appear in every Table 1 row, so they are stored per sample (4 rows × 16 samples).

**(e) What did not fit, and the smallest fix for each.**
1. Fig. 2 sketches have no data_kind; I used `schematic`. Fix: add `schematic` to the series data_kind values.
2. Maps (Fig. 5a, Fig. 6) need a third axis for the colour (counts, height). Fix: add a `z_id` column to series.csv.
3. Measurement settings (magnification, spot size, scan step, kV, AFM area) went into condition.csv with step `none`. Fix: add a `kind` column (process|measurement) to condition.csv.
4. Two purges per cycle cannot be told apart with step = `purge`. I used `purge_time{step=purge_A}` and `{step=purge_B}`. Fix: use the ontology step values (reactant_A, purge_A, reactant_B, purge_B) as the step enum.
5. Some values belong to a group of samples (the SDs over samples 2, 4, 8 and 12; the averaged c_TMA). I wrote a `;`-list in sample_id. Fix: allow `;`-lists or group ids in value.sample_id, as series.csv already does.
6. Simulated runs (Fig. 10) have no sample, so their varied H and N went into value.csv as chosen inputs keyed by from_series. Fix: allow a sample of kind `model_run` in sample.csv, or allow series_id as the key in condition.csv.
7. Literature context (other papers' T, H, AR, reactor) is packed into qualifiers. Fix: add a `cited_ref` column to value.csv.
8. Derived panels (9b and 9c from 9a; 10b and 10c from 10a) and identical curves reused across figures (8b S8 ≈ 9a H500, 8b S12 ≈ 11a 0.1 s ≈ 11b 4 s) are recorded only as free text in reused_from. Fix: put a series id first in reused_from, then the transform.
9. Source problems:
   - Table 1 header in document.md has one column fewer than the data, with x50% duplicated and S_I/S_IIb mis-labelled. I assigned the columns by checking x50 / H = x~50 for every row and against the page image.
   - Table 2 in document.md is misaligned: the Arts 2019 and this-work rows are swapped across cells (OpAL vs Picosun, 10^-4). I read it from the page image.
   - The first sentence of Results E is missing from document.md (body flag, p. 8). From the crop: Fig. 11a is Series E, and TMA dose rose with pulse time.
   - Table 1 footnote f prints "0.1 to 5 nm"; the paper's own text says mm.
10. ESI content (Tables S1-S5, Figs. S4-S17) is not available. Sample u1's recipe exists only in ESI Table S4.

**(f) Row counts.** paper 1, sample 22, condition 136, series 81 (9 with points), value 235, link 64.

**(g) Comparison with v1** (v1: 70 entities/series, 39 experiments, 70 results, 976 assertions, unique_samples 39; mine: 22 samples, 81 series, 136 conditions, 235 values, 64 links).
- v1 has no result scalars at all. All 976 assertions are conditions or model inputs, so it lacks every Table 1 output (PD50, x~50, S_I, S_IIb, GPC_I/IIb, both slopes, R²: 142 cells), c_TMA 4e-3 and c_H2O 3e-4, and all Table 2 literature values. Its sample_table.json holds the rows, but with the slope signs dropped and the "×" lost, and they never reach results.
- Sample identity is wrong. v1 counts 37 physical cases, one per panel curve, so Fig. 9a, 9b and 9c count the same three samples three times, and sample 8 recurs in Figs. 8a, 8b and 9a-f. Table 1 sample codes are never used; the paper has 16 samples plus one AFM sample.
- Fig. 8a: v1 collapses 9 scans into 4 series by L.
- Fig. 3a and 3b have no axis numbers, yet v1 gives them 26 and 38 numeric points: an invented scale.
- feature_height 500 nm is broadcast from methods text (317 assertions), including onto the 100 and 2000 nm samples. Pulse times have no species or step, and per-sample pillar layout and magnification are missing.
- Fig. 10 inputs: v1 has only p_A0, p_B and gpc_sat. It missed c_TMA 0.012, K, P_d, q, ρ, d_A, d_B, M_A, M_B, b and the solver tolerances. It also missed the text scalars: visual PD 140/100 µm, EDS 125 µm, front width 30 µm, filling 10/20/40%, tolerances, deflection, SDs, λ and Kn.
- v1 has, and I lack, digitized points for every plotted curve (1221 observations, including Figs. 5b, 7, 8, 11 and all of Fig. 10). I have points only for the 9 series in points.json.
