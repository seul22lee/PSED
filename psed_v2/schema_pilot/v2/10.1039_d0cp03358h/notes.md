# yim20 (10.1039_d0cp03358h): notes on the fresh v2 extraction

`build.py` writes all tables. Rows: 53 samples, 173 conditions, 88 series, 212 values. Coverage: 518 elements.

## Decisions
- **Table 1 columns.** The parsed header has 17 cells and the data rows have 16. On the page image (table_3_3.png), x50% (PD50%, µm), then x~50% (-), slope d(S/N)/dx~ (nm), slope dθ/dx~ (-) and R². The values in c11-c15 belong under headers c11, c13, c14, c15 and c16. Header c12 is a duplicate from the parser. The check holds for every row: x50%/H = x~50% (140/0.5 = 280, 10/0.1 = 100, 375/2 ≈ 188), and dθ/dx~ ≈ d(S/N)/dx~ / GPC_IIb.
- **Samples.** Each Table 1 sample code is a `piece`. Samples 1-3 share one ALD run (`runA`, s6.p2). Samples 8 and 12 each appear twice in Table 1; they are one sample with both rows in evidence. Series A-F are groups. Other groups: `tab1` (reflectometer samples), `all_exp` (plus the AFM sample `SX` of Fig. 6, Table S4), `H100`/`H500`/`H2000` (design-height classes, for tolerances and membrane bending) and `repro` (samples 2, 4, 8, 12). The four channels of sample 8 in Fig. 8a are `channel` samples.
- **Model.** There are 9 model runs. The 500 nm / 500-cycle run is assumed to be one run serving both rows of Fig. 10, because its inputs are identical (stated as inferred). T, t_p, p_A0 and p_B are conditions. The other caption parameters are values with data_kind chosen input. The model's c_TMA (0.012) is three times the c_TMA extracted from the experiments (4e-3).
- **Literature.** Table 2 rows and the intro works are `reference` samples (refs 31, 33, 36, 40, 41, 60, plus the unnumbered Vandalon 2017 from footnote d). Their temperatures and cycles are conditions; their c values are literature values.
- **from_series.** Table 1 values point to the as-measured scan of each sample. x~50% and slopes point to the scaled or normalized series where one exists (Fig. 9). Samples 1-3 have their scans only in ESI Fig. S4, so placeholder series `FS4-S1..3` (no points) were made for them.
- **Units.** GPC values are converted from nm to Å (printed value kept in note). 3 hPa is stored as 300 Pa, 4.5 µm as 4500 nm, and 3100 kg m-3 as 3.1 g/cm3. Spot size is stored as the printed range "5-6" µm.
- **reused_from (inferred).** F9d-N500 ← F9a-H500 ← F8b-S8 (sample 8). F11b-4s ← F11a-0.1s ← F8b-S12 (sample 12). F10d-N500 ← F10a-H500.
- **Points.** 53 series use the accepted v1 points, keyed by the same series names. 6 series use cases/points.json (case 9: Fig. 9c H100/H500/H2000 and Fig. 9f N250/N500/N1000; v1 had rejected 9c-H100, 9f-N250 and 9f-N1000). The v1 points that were rejected (F7-x50, F8a 0.1 mm merged, F9d/e-N1000, F9e-N250, F10a-H1000, F10d/e/f-N2000) are left empty.

## Did not fit
- Qualitative findings have no column. Examples: spikes near pillar remnants, TMA-limited vs water-limited shape, purge-time trend, the wavy front for v2a. They are carried in series/group notes and in `regime` on S12-S14 values.
- Standard deviations (s16.p10) and the channel-height tolerances (±) are values with quantity `other`, because they are not central values of a listed quantity.
- Recommendations ("channel filling preferably <10%", "≤20% for fingerprint") are values: data_kind assumed and calculated, with censor `<`.

## Source problems
- Inventory: paragraphs starting with "Fig. n" were first dropped. They now exist as s10.x1-s14.x1 and are extracted.
- Text missing from document.md: section 14 starts mid-sentence ("with TMA pulse time ..."), so the opening of the Fig. 11a pulse-time paragraph is lost. s10.p2 also starts mid-sentence; its beginning is in s10.x2.
- Table 1 footnote f prints "0.1 to 5 nm" for the channel lengths; Methods gives 0.1 to 5 mm (misprint).
- Table 2 parse: the Arts row is split over two parsed rows. "OpAL reactor" (r6c5) and "10^-4" (r6c6) belong to Arts. r6c0-c4 belong to the this-work row (r7). r6c7 "—" does not exist on the page.
- Table 2 gives a 4.5 µm gap for Schwille, but footnote a describes a 5 µm cavity. Both are kept.
- The abstract says aspect ratios "beyond 10 000:1"; the body and Fig. 1 say "up to 10 000:1".
- Spelling of the model author varies (Ylilammi / Yilammi / Yillammi).
