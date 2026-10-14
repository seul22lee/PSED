# Schema pilot: sample / condition / series / value / link

Three papers filled by hand on 2026-10-14 (read from `ingest/final/`, no LLM API calls). Evidence fields are locators with a few
words of paraphrase, never copied text. Each folder holds the six CSVs as filled with the draft columns, `checklist.md`
(per key quantity: found / not stated / not read), `notes.md`, and `build.py` (plus `heat.py`/`cells.py` for the
colour-bar reads of mat22), which writes the CSVs.

| Paper | Why chosen | sample | condition | series | value | link |
|---|---|---|---|---|---|---|
| 10.1039_d0cp03358h (yim20) | 16 samples in Table 1, each with a profile, table values and fits; channels of one chip; model runs | 22 | 136 | 81 | 235 | 64 |
| 10.1021_acs.chemmater.2c01154 (mat22) | outside conformality (TMD films); a 32-cell temperature × H2-ratio grid seen by four figures, many methods | 57 | 281 | 67 | 264 | 170 |
| 10.1116_6.0003182 (gre23) | three runs, each followed by pressure traces, mass gain, porosity, XRD, EDS maps and scans; static dosing | 14 | 64 | 44 | 125 | 48 |

## Final columns (the draft, plus the changes the pilot needed)

- **paper**: paper_id, year, topic
- **sample**: sample_id, paper_id, **kind** (deposited | channel | piece | reference | model_run), label_as_printed (`u` if none),
  parent_sample, material, precursor, coreactant, process_mode, reactor, structure_class, structure_dims, width_kind (H | d | w | none),
  temperature_C, cycles, evidence
- **group** (new): group_id, paper_id, member_sample_ids, varied_quantities, rule, evidence
- **condition**: sample_id (`*`, a group_id, or a sample), **kind** (process | substrate_prep | measurement), quantity, **qualifiers**,
  step (reactant_A | purge_A | reactant_B | purge_B | plasma | none), value, unit, data_kind (stated | calculated | assumed),
  **applies_when** (a condition on other conditions, e.g. `deposition_temperature in 100-250`), evidence
- **series**: series_id, sample_ids (samples, a group_id, or `*`), figure, panel, method, x_id, x_by, **x_origin**, y_id, y_reference,
  **z_id** (colour axis of a map), data_kind (measured | fit | simulation | calculated | cited | **schematic**), points_status, points,
  reused_from (**a series_id first**, then the transform), evidence
- **value**: value_id, sample_id (sample, group_id or empty), from_series, quantity, qualifiers, value, **value_min, value_max, censor**
  (`<`, `>`, `dl`), unit, data_kind (measured | fit | chosen input | literature | assumed | calculated), method, relation, regime,
  **cited_ref**, evidence
- **link**: sample_id (sample or group_id), figure, panel, kind (plot | image | map | table | spectrum), stated_or_inferred, evidence

`x_by` is the width that divides x (H, 2H, d, w, none; Case 1 showed the convention moves comparisons by 2×); `x_origin` is where
x is measured from (entrance, top face, hole centre, nearer face).

## Decisions (step 3)

1. **Sweep plot, one run per point: one sample per point, tied by a group.** Each point is its own sample row; a group row names the
   members and the varied quantity; the series' sample_ids is the group; each point that is a result is a value with `from_series`.
   Example: the mat22 heat maps (Figs. 2, 4, 7b, 8) are 32 samples in one group, each map one series, each cell one value. yim20 Fig. 11a
   (TMA pulse 0.1, 0.2, 0.4 s) is three curves, one per Table 1 sample (12, 13, 14), named in the caption.
2. **One sample, several methods: one sample row, one series and one link per method.** Example: gre23's 120 °C run has a pressure trace
   (Fig. 2a), hold analysis (Fig. 3), mass gain and porosity (Table I), XRD (Fig. 5) and EDS map and scan (Fig. 6) on one sample; the
   pieces measured (two compacts, a resistivity prism) are children with `parent_sample` = the run, because which compact went where is
   not stated. yim20 sample 11: SEM-EDS map (Fig. 5a), EDS line scan (Fig. 5b) and reflectometer profile (Fig. 9d-f).
3. **A value read from or fitted to a series: a value row with `from_series`, data_kind and relation.** The authors' front slopes in
   yim20 Table 1 are `fit` with the relation (linear fit of θ against x̃ on 0.2 to 0.8); x̃ at one half read here from points.json is
   `measured` with `from_series`; c_TMA = 13.9·slope² is `calculated` with that relation.
4. **A condition stated once: `sample_id = *`.** yim20: 300 °C, about 3 hPa, N2 150 sccm, Picosun R-150. When the paper-wide rule
   depends on another condition (mat22: 100/120/140 cycles by temperature; gas flows by H2 ratio, Table 2), one row with
   `applies_when` instead of a copy per sample.
5. **Did not fit, and the change made** (each already in the columns above):
   - groups of samples carrying a value or a series (mat22 grid, yim20 SDs and averaged c_TMA) → `group` table, group ids allowed;
   - static dosing: a closed-chamber hold of 1920 s after each pulse carries the exposure (gre23, ~17,000 Torr s) → quantity
     `hold_time{step}`; exposure is pressure × hold, not × pulse;
   - two purges per cycle, with different temperatures in a cycled run → step values purge_A / purge_B;
   - measurement settings (spot size, magnification, EDS kV, Raman laser) → `condition.kind = measurement`;
   - maps → `z_id`; sketches → data_kind `schematic`; simulated runs → sample kind `model_run`;
   - ranges and detection limits (mat22 resistivity `>dl`, Hall ranges) → value_min / value_max / censor;
   - other papers' context in a literature value → `cited_ref`;
   - a curve repeated or derived in another panel → `reused_from` starts with a series_id.
   About 40 new quantity ids (e.g. h2_flow_ratio, atomic_ratio, eds_normalized_counts, hold_time) are listed in the notes; atomic_ratio
   is not the ontology's atomic fraction.

## Comparison with v1 (branch figure-provenance-repair, `resolved/`)

- **yim20**: v1 counts 39 "cases" and 70 entities for what are 16 samples plus one AFM sample (Fig. 9a, 9b, 9c counted three times);
  all 976 v1 assertions are conditions or model inputs, and none of the 142 Table 1 result cells, the sticking values (c_TMA 4e-3,
  c_H2O 3e-4) or the Table 2 literature values reach v1's results; v1 merges the nine scans of Fig. 8a into four series and puts made-up
  points on the Fig. 3 sketch. v1 has digitized points for every curve (1221), the pilot for 9 series.
- **mat22**: v1 51 entities, 34 experiments, 17 series, 51 results, 173 assertions against 57 samples, 67 series, 264 values. v1 reads
  the Fig. 4 x axis as a partial pressure (it is the H2 flow ratio), puts a 35 °C row in Fig. 8 (50 °C), stores "above the detection
  limit" as 5000, and has two Fig. 8 values that contradict the text (100 against 15 Ω cm; 800 against 220). v1 lacks Fig. 7b, the
  wafer map and its 3.3% spread, Tables 1 and 2, the cycle recipe, the H2S plasma co-reactant, and the text values (binding energies,
  Hall results, resistivities). v1 has full Raman spectra and Fig. 7a curves as points; the pilot left them "not read".
- **gre23**: no v1 output for this paper.

## Limits

Points are stored only where `cases/points.json` already had them (plus colour-bar reads for mat22 Figs. 7b and 8, checked against
values in the text); other series are listed with `points_status = not read`. The Supporting Information of all three papers is not in
the corpus, so values only there are marked "not stated in the paper as parsed". The CSVs use the draft columns; the added columns
above are the decided schema and are not yet back-filled.
