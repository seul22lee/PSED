# Handoff (2026-10-16; the state at commit 7d9470b, the tree foundation change)

For a new session on branch `v2`. Read `psed_v2/CLAUDE.md` first; this page adds what the last sessions built and learned. It is
also the one text file of the pilot: the facts plan, the pipeline decisions, the case candidates and the Cremers notes are
sections below.

## What matters now
- **`psed_v2/ingest/final/<paper_id>/`** (untracked, absolute path `/home/ftk3187/github/PSED/psed_v2/ingest/final/`, 59 folders):
  document.md, structure.json, figures/. Every pilot script reads it, so it must exist. It is produced by the ingest
  pipeline (see ingest/INGEST.md) and is not rebuilt casually.
- **`psed_v2/pilot/`**: all pre-pipeline exploration in one flat folder (it replaces gold/, cases/, facts/ and schema_pilot/).
  Per-paper files carry the paper id in their name. One set of controlled lists (`lists.py`), one check (`check.py`), one
  report page (`report.py` → `reports/pilot.html`, untracked, tabs Facts / Cases / Matrix). The Facts tab shows each paper as
  (a) the paper in reading order, (b) experiment cards (default) or the text tree, (c) figures; above the trees the forest
  (`forest.py`: the three trees read together, a quantity picker, one scatter, and the Case 9, Case 10 and Fig. 9 presets).
  - Facts layer (three pilot papers): `elements.py` (stage 1 → `<paper_id>.elements.csv`), `facts.py` (stage 2 helpers and the
    column spec), `<paper_id>.facts.py` (the facts of one paper, read by hand) → `<paper_id>.facts.csv`,
    `<paper_id>.coverage.csv`, `<paper_id>.points.json`.
  - Case studies on the 58 in-scope papers with a PDF: `figures.csv` (figure inventory), `papers.csv` (one line per paper),
    `points.json` (points read by eye, illustrative), `quantity_matrix.py` → `.csv` (41 papers read by hand),
    `paper_case.py` → `paper_case.csv` (paper × case, exclusions with reasons in `case_decisions.csv`), the CSVs behind Cases
    9–13 (`sticking_reported`, `exposure_ear`, `recombination`, `narrowing`, `gpc_temperature`), `recheck.json` (reading check),
    `cases.py` (the Cases tab) and `matrix.py` (the Matrix tab).
  - Cremers 2019 typed in: `cremers.py` (part 1 transcribes Tables II–VII, part 2 checks and plots) → `cremers_*.csv`.
  - v1 points: `v1_points_check.csv` records which v1 curves were checked against their figure and accepted; `v1_points.json`
    holds those points.
- The five-table schema pilot (first pass at 840674c, the element-grounded v2 at c796617) is superseded by the facts layer and
  was removed on 2026-10-14; read it from git history if needed. Its lessons are below.

## Standing rules
- No LLM API calls; read papers yourself (subagents are fine).
- Own words only. Tracked files hold no copied text; evidence is an element id (abs.gN, sN.pM, sN.xK, figN.cap, figN<panel>,
  tabN.rIcJ, tabuK.rIcJ, eqN) plus a short locator. `check.py` rejects a statement that repeats eight words of its element.
- No changes to `corpus/` or `ingest/` unless asked. Never edit `PSED_v2_Plan.md`. Touch nothing outside `psed_v2/`.
- `corpus/raw/`, `ingest/final/` (and marker/, docling/) and every `reports/` folder stay untracked.
- Simple is best; one goal per commit; report briefly; commit lines end with the Co-Authored-By line given in the session.

## Design principles
- One tree per paper inside `<paper_id>.facts.csv`; the atom is a fact with a parent. Every screen (entity card, figure card,
  comparison card, find workbench, forest, claims view, `experiments.csv`) is a projection computed from that file. Screens never
  link to each other; they read the same facts.
- Two kinds of things. What a person must write down is a fact: what a paper measured, set, claimed or cited; what the user claims
  across papers; how the user bridges two definitions. What can be derived is never stored: which entities form a series, what
  range a claim covers, whether an effect exceeds reproducibility, which entities are selected. If it can be computed, compute it;
  if a person must judge it, store it as a fact with an author.
- The old tree mixed three things in one parent chain: physical containment, the authors' comparison intent and measurement
  settings. The symptoms: one mat22 experiment as three "films", sample 4 out of the reproducibility set because a scan position
  counted as a condition, 79 claims without a range, every grid cell with the same purpose sentence, replicates in natural series.
- Tree nodes are of two kinds: an activity (something done, with settings: kind recipe, deposition, anneal, plasma_treatment,
  measurement or simulation; order when several apply to one entity; stated or inferred) and an entity (a physical thing or its
  state: a specimen, a piece cut from it, a position, a model run; stated or inferred). The tree is physical provenance only:
  paper -> recipe -> deposition -> entity -> later activities (measurement, anneal) -> facts; pieces are entities under entities.
- Observations sit under the measurement activity of an entity. Settings sit on the activity they belong to, or on the entity as
  its own properties; measurement settings never enter a condition vector. The condition vector of any node is the union of the
  settings of the non-measurement activities above it and the entity's own, computed for every node, so every claim gets a scope.
- An experiment is any entity with observations (the find rows). When one deposition made one entity they coincide.
- The authors' comparison intent is a fact, not a parent: type comparison, kind series, grid or replicate, the varied quantity,
  links = purpose fact + members. Natural series and replicates are computed from condition vectors and shown beside the stated
  comparisons; disagreement is a confounder (Series E: sample 14 also differs in pillar layout).
- Where a paper names no deposition or specimen, one inferred deposition per condition set and one inferred entity per deposition
  cover the measurements sharing cycle count and substrate; a different count or substrate is a separate, stated deposition.
- Claims carry stance (asserted, hedged, open, limitation) and variables (cause, effect: `lists.py` ids or `mechanism:<token>`);
  a user claim is a claim with author user and links into several papers; a bridge is a user fact with the transform.
- One selection: whatever is in the tray is highlighted everywhere.

## v1
v1 lives on branch `figure-provenance-repair` under `psed_v1/papers/<paper_id>/` (read with `git show figure-provenance-repair:<path>`;
do not check it out over v2). Useful for its digitized points (`extracted/figure_data.json`, mapped by `canonical/curves.json`): they
were checked against the figures for two papers (75 of 121 curves accepted, `pilot/v1_points_check.csv`). Its resolved results
are not reliable: whole tables missing, axes misread, sentinel numbers stored as values.

## What the schema pilot taught
1. Sample or experiment as the one container loses knowledge: values about groups, structures, model runs and literature have no single
   sample, and v1 dropped such results wholesale (all 142 Table 1 cells of one paper).
2. Counts mixed kinds: groups, pieces, references and model runs inflate "samples"; count by sample kind.
3. Linking a figure to its specimen needs the whole paper (methods define runs, captions name them, tables carry their results).
4. Citing element ids with a coverage table makes gaps visible (it exposed an inventory bug); colour-bar reads do not reproduce.
Hence the facts layer: facts first, stated locally per element; linking to depositions and specimens is a later, paper-wide step.

## How to run
```
python3 psed_v2/pilot/elements.py [--text DIR]        # stage 1; --text writes element texts (for reading) outside the repo
python3 psed_v2/pilot/10.1039_d0cp03358h.facts.py     # stage 2, one per paper (also 10.1021_acs.chemmater.2c01154, 10.1116_6.0003182)
python3 psed_v2/pilot/quantity_matrix.py && python3 psed_v2/pilot/paper_case.py   # matrix, then the paper × case table
python3 psed_v2/pilot/cremers.py                      # Cremers tables and checks
python3 psed_v2/pilot/forest.py                       # Cases 9 and 10 and Fig. 9 rebuilt from the three trees alone, against the hand-made CSVs
python3 psed_v2/pilot/user_facts.py && python3 psed_v2/pilot/experiments.py   # the user's facts; one row per experiment (entity with observations) and per cited work
python3 psed_v2/pilot/check.py                        # the one check: facts of the three papers, no unresolved case candidate
python3 psed_v2/pilot/report.py                       # reports/pilot.html (needs corpus/raw review PDF and pdftoppm for Case 8)
python3 psed_v2/ingest/regression.py                  # ingest output against the answer set
```

## Facts layer: plan
Goal: a knowledge layer built from facts, each tied to the paper elements that state it, shown on three pilot papers (yim20 =
10.1039_d0cp03358h, mat22 = 10.1021_acs.chemmater.2c01154, gre23 = 10.1116_6.0003182). Papers are read by hand, every row cites
element ids, statements are in our own words.

Stages:
1. **Elements** (`elements.py` → `<paper_id>.elements.csv`): every abstract sentence group, body paragraph, heading, caption, figure
   panel (plots, images, maps, spectra, schematics; split as seen on the crop), table cell and equation, with a stable id and locator.
2. **Facts per element** (`<paper_id>.facts.py` → `.facts.csv`, `.coverage.csv`, `.points.json`): what each element itself states,
   one row per piece of knowledge, typed setting / observation / derived / model / definition / claim / cited. Local only:
   mentions are copied as printed ("sample 8", "H 500 nm"), with no decision on what they refer to. Values and units as printed.
   Every element is covered or marked "no knowledge" with a reason. Done 2026-10-14; now yim20 700 facts, mat22 620, gre23 336
   (the tree passes added explicit settings, purpose claims, each deposition's temperature and ratio, the colour cells of Figs. 7b and 8).
3. **One tree per paper** (replaces the earlier separate anchors and relations steps): inside `<paper_id>.facts.csv`, the columns
   `parent` (one id: the row without which the fact would not exist), `links` (a second home: a claim's supporting facts, a
   comparison's members, the same data in another panel), `kind`, `order`, `how`, `stance`, `cause`, `effect`, `author`, and tree
   rows (ids without "#"): the paper (root), activities (`<key>:recipe`, `<key>:dep:<name>`, `<key>:meas:<entity>:<method>`,
   `<key>:method:<method>` for shared measurement settings, `<key>:simrun:<k>`), entities (`<key>:ent:<name>`), comparisons
   (`<key>:cmp:<name>`, a fact with members) and cited works (`<key>:refs:N`). Each script's stage 3 still places facts under
   the old process, runs and groups; `facts.retree()` and `facts.comparisons()` then build the activity/entity tree from that
   placement (stage 3b; the per-paper tables say which runs are depositions, entities, pieces, simulations, which groups are
   dropped). Rules checked by `check.py`: an entity has a deposition (a model run its simulation) above it or sits under the recipe
   before any deposition; every observation under a measurement activity or the comparison it spans; every setting under an
   activity, an entity or a comparison; a comparison has a purpose fact first, two or more members and a varied quantity id (none
   for a replicate set), varies nothing of quantity other, and its label's values are in a member's condition vector; a value read
   off a colour-bar panel says so. Done 2026-10-16 (commit 7d9470b): yim20 27 entities (17 stated, 10 model runs), 15 depositions,
   42 measurement activities, 8 comparisons; mat22 54 entities (36 inferred), 54 depositions, 128 measurement activities, 12
   comparisons, 620 facts (64 colour cells); gre23 17 entities, 4 depositions, 34 measurement activities, 1 comparison; 98
   experiments in `experiments.csv`; 50 of 187 claims reach no condition (links to definitions, cited works or claims only).
4. **Standardization**: units converted to `lists.UNITS` and quantity ids standardized, in the facts file.
5. **Views and demo**, seven views: coverage (nothing lost); facts by type; experiment view (per deposition: conditions,
   measurements, results, link status coloured); figure view (crop next to its facts); evidence trace (a claim → derived →
   observation → crop or table cell); cross-paper comparison (same quantity, comparable only with matching qualifiers and
   data_kind); v1 comparison by fact type. The KG is these files as a graph and serves the trace and cross-paper views.
   Built at 85fdb15: coverage (a), facts by type (the text tree), the figure view (c) and the experiment view as cards (b): the
   left pane is the tree collapsed to groups and runs; clicking a run, a fact line in the text tree, a fact in the figures view
   or a scatter point opens the run's card. A card has five rows: 1 what was varied (the setting differing among the run's
   siblings, this run's value beside theirs; when siblings differ in nothing, the first level up where they do); 2 other
   conditions (every setting inherited up the tree as chips, the process-defining ones first, two lines until "+N more" opens
   the rest, marked where that level's siblings differ; one value stated at two levels is one chip); 3 measured (observation,
   derived and model facts grouped by figure, table or paragraph; an element id opens the evidence box with the crop; curves as
   sparklines; inferred film membership marked; child specimen runs listed); 4 why and what it showed (the group's purpose fact,
   then the claims linked to the run or its group); 5 compare (siblings with their varied values; the same varied quantity in
   the other two papers). The trace (view 5) is row 3 → evidence box; the cross-paper view (6) is the forest scatter and row 5.

Files per paper: `.elements.csv`, `.facts.csv` (facts and the tree), `.coverage.csv`, `.points.json`; no separate anchor or link
files. They are the source; the KG and the pages are rebuilt from them. Order: stages 1–2 → 3 → 4 → 5, with a
short report after each. Views 1, 2 and 4 are the Facts tab of `reports/pilot.html`.

## Pipeline decisions to make (what did not fit the fact columns, stage 2)
The columns were kept as they are; these are open decisions for the pipeline schema.
1. **Uncertainty column.** "±" values have no column and sit in the statement only (about 70 facts: gre23 ~45, mat22 ~20, yim20 6;
   e.g. Table I porosities, Fig. 1c mean thickness, tolerances).
2. **Non-numeric value column.** Categorical or named results carry their value in the statement only (about 110 facts: mat22 Fig. 2
   crystalline/amorphous per cell (32) and map regions, yim20 pillar layout "v1a", reactor names, LHAR type).
3. **Promote "other" ids used in two or more papers.** Done 2026-10-14 for 21 ids (`lists.py`); 108 facts still use other (yim20 44,
   mat22 27, gre23 37) and no label is left that two papers share. Before that pass, 260 facts used other. Labels then seen in
   two or more papers: signal intensity (EDS, Raman, XPS, X-ray counts; all three), accelerating voltage (yim20, mat22),
   crystallite size (mat22, gre23), sample or channel length L (yim20, gre23), reactor part temperatures (wall, window, delivery
   line; mat22, gre23). Frequent single-paper labels to weigh: porosity, mass gain, hold time, binding energy, roughness Rq, carrier
   concentration, mobility, plasma power, base pressure, R² of a fit.
4. **Methods** missing from `lists.METHODS`: ERD (stored as rbs), OES (blank), Hall (stored as electrical), IR spectroscopy, calipers
   (blank).
5. **"≤" censor.** "20% or less" was stored as value_max; CENSOR has no "≤" / "≥".
6. **Species tokens with parentheses.** A precursor such as Mo(NtBu)2(NMe2)2 is not a valid `species=` token, so that fact has no
   qualifier.
7. **In situ vs ex situ is a qualifier, not a method.** The facts use ellipsometry for both (mat22 in situ SE); the
   distinction needs a qualifier key, as do map vs line scan (sem_eds) and gauge vs thermocouple (process_monitor).
8. **Node attributes.** Activities and entities carry `kind`, `order` and `how` as columns (2026-10-16); the old run=, how=, sample= and
   sim= qualifiers are gone.
9. **What a run is.** Decided 2026-10-14: one physical film, specimen or simulation per run (stage 3 above); a condition set is a
   group. The pipeline needs the `how=inferred` mark for facts of two measurements put on one film without the paper saying so.
Also seen: multi-number table cells (yim20 pulse-purge sequences "0.1-4.0-0.1-4.0") split into one fact per step; text that rounds a
table value kept as one fact with the table value; conflicts between text and table kept as printed. Channel height H of lateral
channels is `feature_height` (added to the lists). Twelve yim20 curves have facts but no points (rejected in v1, absent from
points.json) and stay so.

## Case candidates (the cases behind the Cases tab)

Built from `figures.csv` on 2026-10-13, first from the papers then parsed (parts A to C), then from all papers with a PDF (part D). Exploration only: nothing here is extracted data.
Figures are named `paper_id Fig. N panel`. Ontology ids are those of `ontology/ontology.yaml` v0.

How the list was made. Plot rows were grouped by the pair of axis ids with qualifiers removed, in either axis order (263 pairs, 31 shared by two or more papers), and by y quantity across different x forms. Each group was then judged. Candidate A9 comes from image rows, which the grouping cannot see. Part B is the second kind: one sample seen by several panels or methods inside one paper.

### A. Across papers (10)

#### A1. Do TMA/water alumina profiles from different lateral-channel studies agree once channel height, cycles and dose are accounted for?
- **Figures.** 10.1063_1.5028178 Fig. 6; 10.1039_d0cp03358h Fig. 9a-f, Fig. 11a-b, Fig. 8b; 10.1016_j.sse.2022.108584 Fig. 6, Fig. 7.
- **Why a naive overlay is wrong.** The profiles differ in cycles (250 to 1000), pulse time, channel height and reflectometer spot size, so raw thickness against micrometres mixes four effects. Film growth narrows the channel, so profiles at different cycle numbers do not scale by a constant. The sse figures replot the same samples (data_kind cited), so counting them adds no experiment. Yim Fig. 8b shows run-to-run fronts tens of micrometres apart for nominally equal runs, which sets the floor for any agreement claim.
- **What makes them comparable.** `x_over_width` gives dimensionless_distance{by=H} and `thickness_to_gpc` gives growth_per_cycle{position=local}; Yim Fig. 9 already shows both forms. Missing in the ontology: nothing for the axes. Missing in the data: the reactant partial pressure is a model input in both papers, not a measured value, so `exposure` cannot be formed.
- **Conditions.** Temperature and pulse sequence of the Ylilammi sample are only in the body text; the Yim samples are defined only in its Table 1.
- **Papers still needed.** 10.1116/1.5093620 (the third data set plotted in sse Fig. 6) and 10.1116/1.4903941 (the test structure paper).

#### A2. Which sticking coefficient does each study assign to TMA, and from which kind of evidence?
- **Figures.** 10.1063_1.5028178 Fig. 6 (fit); 10.1039_d0cp03358h Fig. 10 (simulation with chosen values) against Fig. 9; 10.1016_j.sse.2022.108584 Fig. 4, Fig. 6 (fit to cited data), Fig. 5a; 10.1039_d1cp04758b Fig. 6b-d (slope method on simulated profiles).
- **Why a naive table is wrong.** The values come from three different operations: a model adjusted to points (fit), a model run with given parameters (simulation), and a closed formula applied to a slope (calculated). The authors' own words do not separate them; two papers call a fitted curve "calculated". The models also differ (Knudsen only, with gas-phase diffusion, reversible adsorption), so one number is not the same parameter in each.
- **What makes them comparable.** initial_sticking_coefficient{species=tma} with data_kind and the model id (ylilammi_diffusion_reaction, arts_slope) attached to each value. Missing in the ontology: a model entry for the sse coverage model and a parameter for reversible desorption (evaporation flux).
- **Conditions.** The values themselves are only in tables (Ylilammi Table I, Yim Table 2, sse Tables 1 and 2).
- **Papers still needed.** 10.1116/1.5093620.

#### A3. Does the recombination probability of oxygen radicals depend on material and on pressure regime?
- **Figures.** 10.1021_acs.jpcc.9b08176 Fig. 3; 10.1063_5.0168768 Fig. 3, Fig. 4; 10.1021_acs.jpcc.5c06502 Fig. 10b inset.
- **Why a naive overlay is wrong.** All three plot the same pair (half-thickness depth over cavity height against the logarithm of plasma time), which is what makes the overlay tempting. The slope means different things: at low pressure it follows the free-molecular relation, at atmospheric pressure a different prefactor applies, so equal slopes do not mean equal probabilities. Plasma time per cycle is a pulse length in one reactor and a transit time under a plasma head in the other two. The first TiO2 point at atmospheric pressure may not be recombination limited. The low-pressure lines in 10.1063_5.0168768 Fig. 4 are computed from the earlier paper's values, not new data.
- **What makes them comparable.** coated_aspect_ratio{basis=AR} on y in all three. Missing in the ontology: a transform for the logarithm of pulse_time{step=reactant_B}, and a way to carry the diffusion regime (process_pressure is there, a Knudsen number is not). The result, recombination_probability{species=o_atom, surface=...}, exists.
- **Conditions.** Cavity height, precursors and deposition temperature are only in the body text of all three papers.
- **Papers still needed.** 10.1149/1.3491381 for the low-pressure model behind the relation.

#### A4. How does the shape of a plasma ALD thickness profile change with structure scale and pressure?
- **Figures.** 10.1021_acs.jpcc.9b08176 Fig. 2B; 10.1063_5.0168768 Fig. 2a-b; 10.1021_acs.jpcc.5c06502 Fig. 10b; 10.1116_6.0001094 Fig. 11, Fig. 12.
- **Why a naive overlay is wrong.** Four normalizations: thickness over its entrance value, raw nanometres, raw nanometres with no flat region at all, and thickness over an assumed saturated thickness of 22 nm, stated only in the body text (points exceed 1). Four x forms: distance over cavity height, micrometres, and metres. The structures span a gap of half a micrometre with aspect ratio above 1000 and a 1 mm gap with aspect ratio 20. In 10.1116_6.0001094 the two figures were made at different temperatures.
- **What makes them comparable.** normalized_thickness with the reference qualifier stated per row (entrance, assumed_saturation) and dimensionless_distance{by=H}. Missing: for the profiles that fall from the entrance on there is no plateau, so a reference has to be chosen and recorded; the ontology's reference list has no value for a chosen maximum.
- **Conditions.** Cavity heights for two papers and the thickness technique for three are only in the body text.
- **Papers still needed.** None for the comparison itself.

#### A5. Can thickness-against-depth be compared between holes, nanotube arrays and porous bodies?
- **Figures.** 10.1038_s41467-022-35428-6 Fig. 4b; 10.3762_bjnano.5.25 Fig. 6b-c; 10.1116_1.4892385 Fig. 5; 10.1021_acs.chemmater.1c03164 Fig. 9; 10.1021_acs.langmuir.6b03119 Fig. 3a; 10.1116_6.0003182 Fig. 6d-f.
- **Why a naive overlay is wrong.** "Depth" is measured in six different geometries (a tapered hole, two nanotube arrays, a nanotube layer, a porous ceramic, a pressed powder compact), over ranges from 1 micrometre to 1.5 mm. One figure plots tube diameter, not film thickness; one plots thickness against local pore diameter with depth only on a second, non-linear axis; one plots an X-ray signal; one has thickness on the horizontal axis and depth on the vertical. In the inhibitor paper the film is intentionally thinnest at the top.
- **What makes them comparable.** distance and film_thickness map for four of the six. Missing in the ontology: a transform from coated diameter to thickness, and any equivalent aspect ratio for arrays and porous bodies (equivalent_aspect_ratio is recorded as reported only, and none of these papers reports one). Without it the x axes cannot be put on one scale. This is the geometry-class boundary of the conformality scope.
- **Conditions.** Cycle numbers and exposures are only in the body text for four of the six.
- **Papers still needed.** 10.1021/am505107s and 10.1021/cm0303080 would add the two classic array and pore cases.

#### A6. Is "the dose at which growth saturates" comparable between processes?
- **Figures.** 10.1021_acs.chemmater.6c00816 Fig. 2a-b; 10.1021_acs.chemmater.9b05116 Fig. 2; 10.1021_acsnano.5b03429 Fig. 2a-b; 10.1021_acsami.0c22121 Fig. S1; 10.1116_6.0002804 Fig. 1a-b; 10.1116_6.0002993 Fig. 1c; 10.1149_2.067203jes Fig. 4; 10.1116_6.0001679 Fig. 3; 10.1021_acs.jpcc.5c06502 Fig. 2; 10.1002_adem.202201901 Fig. 1.
- **Why a naive table is wrong.** Nine papers plot growth per cycle against pulse time and one against a dose pressure. Pulse times run from milliseconds to minutes because the reactors differ, not the chemistry. One paper gives growth per precursor pulse, one derives growth from mass gain on a powder, one varies precursor and plasma time together. Saturation time is a reactor property unless the pressure during the pulse is known.
- **What makes them comparable.** Only `exposure` (partial_pressure times pulse_time) would do it. The partial pressure is on the figure in one paper out of ten. The ontology has the transform; the data do not have the input.
- **Conditions.** Reactor pressure during the pulse, where given at all, is in the body text.
- **Papers still needed.** None; the case is useful as a negative example.

#### A7. Do the lateral-channel models give the same answer for the same inputs, and the same link between front slope and sticking coefficient?
- **Figures.** 10.1063_1.5028178 Fig. 2, Fig. 3 against 10.1039_d1cp04758b Fig. 2a-b (same parameters, stated); 10.1039_d1cp04758b Fig. 6b-d, Fig. 7; 10.1039_d3cp01829f Fig. 4f, Fig. 6; 10.1039_d4cp00131a Fig. 11b, Fig. 12.
- **Why a naive overlay is wrong.** Most of these plot coverage after one exposure, not thickness after many cycles; the two coincide only without channel narrowing. Depth is in micrometres in one pair and in units of channel height elsewhere. The slope relation holds in the free-molecular limit only, and one paper shows it changing with Knudsen number. Fitted lines in 10.1039_d4cp00131a Fig. 12 are adjusted to simulated points, so data_kind fit there does not mean agreement with an experiment.
- **What makes them comparable.** surface_coverage against dimensionless_distance{by=H}; the half-coverage depth maps to coated_aspect_ratio{basis=AR}. Missing in the ontology: the slope at half coverage and the front broadness (three papers plot them), the Knudsen number, and model entries for the ballistic model and the porous-particle model.
- **Conditions.** Baseline parameter sets are only in tables in three of the four papers.
- **Papers still needed.** 10.1149/1.3072694 and 10.1002/cvde.200390005 for the two older models these are measured against.

#### A8. Does penetration grow with the square root of exposure in experiment as it does in the models?
- **Figures.** Models: 10.1063_1.5028178 Fig. 5; 10.1021_acs.chemmater.1c03164 Fig. 4a; 10.3762_bjnano.5.25 Fig. 3c-d, Fig. 4; 10.1039_d3cp05639b Fig. 3; 10.1039_d3cp01829f Fig. 4e, 4h. Experiments: 10.1039_d0cp03358h Fig. 11a; 10.1021_acs.langmuir.6b03119 Fig. 3a; 10.3762_bjnano.5.25 Fig. 6c.
- **Why a naive overlay is wrong.** "Penetration depth" is the model's front position in three papers, the half-coverage depth in two, and has to be read off a thickness profile in the experiments. The x axis is pulse time, scaled time, exposure in pascal seconds, or particle radius. One model figure puts four different quantities on a single axis. The experiments give two to four exposure values each, with thickness-based depth.
- **What makes them comparable.** penetration_depth with the level qualifier (50%, or other: model front) and `exposure` on x. Missing: a value of the level qualifier for coverage-based depths, and partial pressure for the experiments.
- **Conditions.** Pressure during the pulse is only in the body text of the experimental papers.
- **Papers still needed.** 10.1002/cvde.200390005 (the plug-flow relation three of these compare with).

#### A9. How does reported step coverage vary with aspect ratio across processes?
- **Figures (images with the numbers written on them or in words).** 10.1021_acs.jpclett.4c03545 Fig. 1, Fig. 2; 10.1021_acs.chemmater.6c00816 Fig. 4; 10.1116_6.0002804 Fig. 9; 10.1149_2.067203jes Fig. 8; 10.1016_j.mee.2018.01.027 Fig. 3; 10.1007_s12274-010-0066-9 Fig. 3.
- **Why a naive table is wrong.** The ratio is bottom over top in some, sidewall over top in others, and a set of percentages at three positions in one. Aspect ratios run from 1.5 to 90 and are for trenches, holes and pores, which need different doses at equal aspect ratio. Thermal, plasma and hot-wire processes are mixed. One value above 1 is deliberate. None of the values is on a plot axis.
- **What makes them comparable.** step_coverage{position=bottom | sidewall} and aspect_ratio; `step_coverage` from film_thickness{position=...} where thicknesses are given. Missing: equivalent_aspect_ratio is not reported by any of them, and no method field ties a number to the image it was read from.
- **Conditions.** Every value is in a caption or in the body text, none in a table.
- **Papers still needed.** This one matters: the bulk of such values are in the in-scope papers without a PDF (the papers behind the conformality tables of the 2019 review).

#### A10. When do mesopores close during ALD, and how does growth inside pores compare with growth on a flat surface?
- **Figures.** 10.1039_c4nr05049e Fig. 6b, Fig. 7b, Fig. 8; 10.3390_separations11010024 Fig. 7, Fig. 9; 10.1116_6.0001679 Fig. 4; 10.1021_acs.langmuir.6b03119 Fig. 4c; 10.1039_c5ta00205b Fig. 1.
- **Why a naive overlay is wrong.** The signals are an X-ray critical angle, a scattering intensity, fluorescence counts, gas permeance, cations per area, and microbalance mass. All are plotted against cycle number, so they stack on one x axis while measuring different things. Two papers show a break near cycle 20 to 28 in titania films with pores of 4 and 5.5 nm, from different precursors; the agreement may be real or may be coincidence of pore size over growth per cycle.
- **What makes them comparable.** cycle_number on x; feature_width for the pore size; closure expected near pore width over twice the growth per cycle. Missing in the ontology: an amount-based growth per cycle (mass or atoms per area; the proposal was rejected for lack of gold evidence, and five papers here would use it) and a quantity for the cycle of pore closure.
- **Conditions.** The planar growth per cycle needed for the estimate is in the body text of both titania papers.
- **Papers still needed.** 10.1021/la300045z and 10.1021/jp111314b (same in-situ methods on other films).

### Rejected groups

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

### B. Within one paper: one sample seen by several panels or methods

Link is **stated** when the caption or text names the same sample or run, or one panel is drawn on or derived from the other. It is **possibly** when only the conditions match.

#### Stated (17 sample sets, 10 of them by two or more different techniques)

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

#### Possibly (18 links)

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

### Limits of this pass

- 60 plot rows are marked "not viewed" in their note: panels whose layout repeats one I did read, or routine spectra, recorded from the caption. Their axis labels are not verbatim.
- Uncaptioned page-1 graphics and tables are not in the inventory.
- A panel holding both points and a curve is one row with two data kinds (for example "measured; fit").
- 334 measured rows carry a sample key of the form `u:<figure><panel>`: a sample is shown but nothing links it to another panel.

### C. Checked candidates N1 to N9

Each was checked against the named figures and, where needed, the body text and tables of `ingest/final/<id>/document.md`. Verdicts: 3 hold, 6 hold partly, none fails outright.

#### N1. One experiment through the literature
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

#### N2. Calibration against prediction
- **Question.** Which model curves were adjusted to the data they are drawn with, and which were not?
- **Figures.** sse Fig. 6 against Fig. 7; 10.1039_d0cp03358h Fig. 9a-f against Fig. 10a-f.
- **What was found.** sse Fig. 7 uses the parameter set of its Table 2 without re-adjustment (stated in the text and the caption). Three caveats: for the 2 µm channel the diffusivity formula is switched to include gas-phase diffusion, which is a change of model form; the 0.5 µm profile is a nominal repeat of one used for calibration (another sample with the same recipe); and the 0.1 µm case does not match, which the authors attribute to the channel closing. In Yim, Fig. 10 is a simulation with chosen inputs and is laid out panel by panel like Fig. 9; it covers two heights and two cycle numbers that were not measured, reproduces the ordering and the collapse on x/H, and has none of the spikes and tails of the measured curves.
- **What it shows about the pipeline.** data_kind must separate fit from simulation by the operation, not by the wording: sse calls both figures "comparison of simulation", Yim calls Fig. 10 "simulated", Ylilammi calls a fit "calculated".
- **Verdict: holds partly.** The parameters are not re-adjusted, but only two of the three Fig. 7 profiles are new to the model and one of those needs a different diffusivity.
- **Missing in the ontology.** A way to say that a curve is a prediction with parameters taken from another fit (data_kind simulation plus the source of its parameters).
- **Only in text or tables.** The statement that parameters were kept; the sample definitions (Yim Table 1).

#### N3. One symbol, several meanings
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

#### N4. Where a thickness number comes from

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

#### N5. Reactor-scale uniformity
- **Question.** How even is growth across a part, a tube or a batch, and can the three be compared?
- **Figures.** 10.1093_nsr_nwaf247 Fig. 3a, 3d (eleven numbered points on a 3D part, without and with baffles; growth per cycle measured, coverage simulated); 10.3390_separations11010024 Fig. 3 (five numbered spots along a 100 mm strip in a tube, three carrier flows); 10.1002_adem.202201901 Fig. 3a-b (within-wafer value against dose and temperature), Fig. 4a (wafer slot 1 to 25 of a batch, loads of 5 and 25).
- **How position is given.** As a point number on a drawing in the first (coordinates only in a supplement figure), as a spot number in the second (first spot at the inlet; spacing not on the figure), as a slot number in the third. The within-wafer value of the third is one percentage with no positions at all; the paper defines it from the maximum, minimum and mean.
- **What it shows about the pipeline.** Position labels are not coordinates. The only common currency is a spread, and the first paper prints one (35% to 6% measured, 12% to 2% simulated) with an unstated definition.
- **Verdict: holds partly.** The three figures are as described, but nothing puts their positions on one scale, and only one definition of non-uniformity is printed.
- **Missing in the ontology.** thickness_nonuniformity has no qualifier for its scope (within wafer, across a batch, over a part) or its formula; no entry for a position label; the simulated counterpart is a coverage, not a thickness.
- **Only in text or tables.** The definition of the spread (adem equation); point coordinates (nsr supplement).

#### N6. Recipe card

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

#### N7. Parameter sensitivity across models

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

#### N8. Consistency check on pore closure
- **Question.** Does pore width over twice the planar growth per cycle predict the cycle at which pores close?
- **10.1039_c4nr05049e.** Stated: neck about 3 nm, small pore axis 3.8 nm, planar growth 0.55 Å per cycle, precursor size about 0.7 nm, break observed at cycle 23 to 24 (Fig. 6b, 7b, 8). Prediction from the neck: 27 cycles to zero width, 21 cycles to the precursor size. Observed 23 to 24 lies between. From the small axis the prediction is 35, which is wrong; the neck is what closes.
- **10.3390_separations11010024.** Stated: pore width about 5.5 nm (Fig. 6b, 7); permeance drops to its floor between cycle 21 and 28 for six membranes (Fig. 9). Planar growth at the same nominal conditions is read as about 0.48 Å in Fig. 4 and about 0.77 Å in Fig. 5, two figures of the paper that do not agree. Prediction: 57 or 36 cycles. The in-pore growth of Fig. 7 (0.33 nm in 12 cycles) predicts about 100. Observed closure is earlier than all three.
- **What it shows about the pipeline.** A cross-figure check can confirm a paper's own reasoning (first paper) and can expose an internal mismatch (second paper: two planar values, and permeance that ends long before the mean pore would be full).
- **Verdict: holds partly.** It holds for the first paper when the neck is used; it does not hold for the second, where Fig. 7 was made in a different reactor from Fig. 9 and permeance may be set by the narrowest pores.
- **Missing in the ontology.** A neck width as distinct from the pore width; a closure-cycle quantity; an amount-based growth per cycle.
- **Only in text or tables.** The planar growth and precursor size of the first paper. No value is missing in either paper; the second has two.

#### N9. Structure equivalence and unusual profiles
- **Figures and findings.** 10.1021_acs.jpclett.4c03545: the same process gives step coverage 1 and 1.6 in an 18:1 vertical trench (Fig. 1, 2), while in lateral channels the film reaches 42 µm, an aspect ratio of 84, with and without krypton (Fig. 3, value in the body text). The lateral structure shows the limit the trench cannot show, and does not show the top-to-bottom effect the trench shows. 10.1116_6.0001094 states both an aspect ratio of 20 and an equivalent aspect ratio of 10 for one trench; 10.1021_acs.jpcc.5c06502 Table 1 does the same for its four samples. 10.1038_s41467-022-35428-6 Fig. 4b has the film thinnest at the top, by design; 10.1021_acs.jpclett.4c03545 reports step coverage above 1.
- **What it shows about the pipeline.** Two structures answer different questions about one process, so a "conformality" value needs its structure class. Profiles that rise with depth break any normalization to the top or the entrance and any reading of a half-thickness depth.
- **Verdict: holds.**
- **Missing in the ontology.** Nothing for AR and EAR (both entries exist and both are stated here). A reference value for profiles thickest at the bottom; a flag that step coverage may exceed 1; a link between two structures coated in one process.
- **Only in text or tables.** The 42 µm depth; the AR and EAR pairs.

### D. Update after 15 more papers (2026-10-13)

Fifteen PDFs were obtained by hand and parsed: Cremers refs 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228, 251 and 10.1021/acs.jpcc.1c01505. `figures.csv` now covers every paper with a PDF: the in-scope papers and 10.1016_j.cattod.2003.11.022 (Guyon 2004), which is out of scope as not an ALD paper and kept only as a cited source of recombination values; it counts in no number of corpus papers below. Parts A to C above are as written before that day; this part says what changes.

#### Existing candidates whose evidence or verdict changes

- **A1.** Two more thermal alumina profiles: 10.1116_1.4903941 Fig. 5a (same channel type, 300 °C) and 10.1149_1.3072694 Fig. 5 (a 0.1 mm high hole). On x/H the half-thickness depths of six profiles from four papers lie between 104 and 269. Of the papers still needed, 10.1116/1.4903941 is now parsed; 10.1116/1.5093620 is still missing.
- **A2.** Two more fitted TMA values, from other structures: 0.009 to 0.02 in a cavity (10.1116_1.4971196) and 0.026 for the plasma process in holes (10.1063_1.2714685). Two values the review lists as results are not: 0.001 is quoted in 10.1021_cm0303080 from an earlier paper, and 0.1 is a chosen input in 10.1149_1.3072694.
- **A3.** 10.1021_acs.jpcc.1c01505 gives the slope plot for twelve conditions in one reactor: r of SiO2 falls from about 1e-4 to 3e-5 between 100 and 240 °C and from 2e-4 to 2e-5 between 12 and 130 mTorr. So "material and regime" is not enough: temperature and pressure inside one regime move r by a factor of ten. The model paper named as still needed (10.1149/1.3491381) is parsed; it is the origin of the three-regime scheme.
- **A4.** One more macroscopic plasma hole (10.1149_1.3301664 Fig. 2b) and one more low-pressure SiO2 series. The two macroscopic holes both reach half thickness at their end, so the "different structure scale" reading is confirmed for both.
- **A5.** Three more geometries with thickness or a thickness signal against depth: pores open at both ends (10.1021_cm0303080 Fig. 5a, an X-ray signal), a fibre-filled hole (10.1016_j.surfcoat.2012.02.038 Fig. 5), and a cavity entered through a central hole, where depth is radial (10.1116_1.4971196 Fig. 8). The case for a geometry class on every profile gets stronger; 10.1021/cm0303080 is no longer missing.
- **A7.** The two older models named as still needed are parsed (10.1149_1.3072694, 10.1002_cvde.200390005), with the Monte Carlo model of 10.1149_1.3491381. The claim that sticking moves the slope and not the depth is stated in all three.
- **A8.** Verdict moves from open to **holds partly**. Two sources test the square law of 10.1002_cvde.200390005 for TMA and water. For 10.1149_1.3072694 it predicts a coated aspect ratio of 49 at 9 × 10^3 L, against 47 and 53 read by eye and one fully coated structure of 33, so it matches. For 10.1021_cm0303080 it asks for 530 × 10^3 L, while the centre of the membrane was already coated between 150 and 450 × 10^3 L, so the model overestimates the need by about 1.2 to 3.5 times (membrane counted at half its length, as the source supports). See the Cremers section of HANDOFF.md 3a.
- **A9.** New values with a number: bottom over top of 52% to 100% at aspect ratio 8.7 against pulse time and cycles (10.1149_1.2789802 Fig. 3, 5), and 92% to 104% for Pt in trenches of aspect ratio 3 to 34 defined as mean trench thickness over planar thickness (10.1063_1.4972120 Table II). Two more definitions of the same word.
- **N1.** The third item is now traced: the low-pressure values in 10.1063_5.0168768 come from 10.1021_acs.jpcc.1c01505, which is in the corpus, and its Fig. 5A agrees with them. A second lineage appears: Tables V and VII of the review are updates of the tables of 10.1149_1.3491381, and one TMA value there goes back through 10.1021_cm0303080 to a still earlier paper, changing its method label on the way. Verdict stays "holds partly"; the part that did not hold is now explained.
- **N2.** More cases of both kinds. 10.1149_1.3072694 Fig. 6 is a simulation with a chosen sticking value that the review's Table V lists as a derived one. 10.1149_1.2789802 Fig. 6a and 7a and 10.1063_1.2714685 Fig. 9 are real predictions: bottom-of-hole curves computed from parameters fitted elsewhere.
- **N3.** Five more labels: "relative ZnO coverage" (an X-ray signal over its maximum, 10.1021_cm0303080), "precursor coverage" (thickness over cycles and a chosen saturation level, 10.1116_1.4971196), "thickness (%)" (simulated, over saturation, 10.1149_1.3491381), "normalized Al concentration" called relative thickness in a caption (10.1016_j.surfcoat.2012.02.038), and "conformality (%)" as mean trench thickness over planar thickness (10.1063_1.4972120).
- **N4.** Five more derivations, three with a stated uncertainty: microprobe line scan with 3 to 5 µm resolution; X-ray signal on fibres with error bars; micro-spot ellipsometry with a 10 µm spot and 3% error; plan-view TEM cuts with depth known to 10 nm; and, in one paper, SEM (4 nm, about 12%) against TEM (160 values, spread 3 nm) on the same trench type.
- **N6.** Five more processes, and the reactant partial pressure is stated in four of them (0.3 Pa, 0.08 Pa, 0.15 Torr and 0.01 Torr of TMA). The count of processes with a known partial pressure goes from 1 of 12 to 5 of 17.
- **N7.** Four more models agree on the two main trends (depth with the square root of exposure, slope with sticking). 10.1149_1.3491381 adds the recombination probability: it sets the dose and bends the profile near the bottom.
- **N9.** Two papers state the equivalence of a trench of aspect ratio 20 and a pore of 10 (10.1063_1.4972120, 10.1149_1.3491381). 10.1016_j.surfcoat.2012.02.038 and 10.1149_1.3301664 give thermal and plasma profiles in one structure at the same exposure.

#### New candidates

#### N10. The square law across papers
- **Question.** Does the exposure needed for full coverage grow with the square of the aspect ratio in measured data from different groups?
- **Figures.** 10.1002_cvde.200390005 Fig. 2, Fig. 3 (model and hafnia holes); 10.1149_1.3072694 Fig. 5; 10.1021_cm0303080 Fig. 3, Fig. 5, Fig. 13.
- **What it shows about the pipeline.** The comparison needs three things the review's rows do not carry: an exposure in pressure times time, an aspect ratio on one definition, and whether a pore is entered from one end or two.
- **Verdict: holds partly** for TMA and water, with a saturation density assumed from a third paper: the prediction matches 10.1149_1.3072694 (49 against 47 to 53) and overestimates the need for 10.1021_cm0303080 by about 1.2 to 3.5 times. For hafnia the source's own test holds (coated to a quarter, three quarters, fully at 2, 4, 30 × 10^3 L).
- **Missing in the ontology.** An entry or qualifier for one-sided against two-sided entry; a transform from depth, width and structure class to the equivalent aspect ratio; the saturation density as a quantity.
- **Only in text or tables.** Pressures and pulse times, in all three papers.

#### N11. A recombination probability belongs to a surface state, not to a material
- **Question.** Can a literature value of r for "titania" or "alumina" be used for the film during growth?
- **Figures.** 10.1016_j.cattod.2003.11.022 (out of scope, cited source) Table 1, Fig. 5; 10.1021_acs.jpcc.1c01505 Fig. 5; 10.1063_5.0168768 Fig. 3; 10.1021_acs.jpcc.9b08176 Fig. 3; the review's Table VII.
- **What it shows about the pipeline.** A value without temperature, pressure, method and kind of surface cannot be joined to a process. The same material name carries values 350 times apart with opposite temperature trends.
- **Verdict: holds.** Sintered ceramic in a 110 Pa air plasma: 0.014 at 300 K, rising. ALD film in a lateral channel: about 4e-5 at 100 to 180 °C, falling.
- **Missing in the ontology.** Conditions on a recombination probability (temperature, pressure, method); a way to say what the surface is (bulk ceramic, growing film, film covered with ligands).
- **Only in text or tables.** The ceramic values (a table); the conditions of both.

#### N12. Thermal and plasma in one structure at one exposure
- **Question.** How much less deep does the plasma process coat when everything else is equal?
- **Figures.** 10.1016_j.surfcoat.2012.02.038 Fig. 10; 10.1149_1.3301664 Fig. 2a-b, Fig. 9, Fig. 10.
- **What it shows about the pipeline.** The review lists these papers as unmatched rows (different exposure, different structure). The matched pair exists only inside each paper and has to be read from the figures.
- **Verdict: holds.** About six times less deep in a fibre plug at 75 °C; in an empty hole of aspect ratio 22 the thermal film is complete and the plasma film reaches half thickness near 14. In the second paper a thermal side reaction with water formed in the plasma step makes the plasma profile look better than recombination alone would give; a cobalt oxide profile without that side reaction is much sharper.
- **Missing in the ontology.** A link between two series that differ in one condition only; a note that a profile is the sum of two reactions.
- **Only in text or tables.** The statement that conditions are equal; pressures.

#### N13. How many points does a sticking coefficient rest on?
- **Question.** Which published sticking values come from profiles dense enough to fix them?
- **Figures.** 10.1016_j.apsusc.2009.02.055 Fig. 3 (4 points); 10.1016_j.apsusc.2010.01.025 Fig. 1 (4 to 5 points each); 10.1116_1.4971196 Fig. 8, 9 (about 100 points); 10.1063_1.5028178 Fig. 6 (about 85 points); 10.1149_1.3072694 Fig. 5 (about 20 points, no fit made).
- **What it shows about the pipeline.** The number of points in the slope region is a property the knowledge base can hold for every fitted value; the review itself asks for it (its Sec. VI B 3).
- **Verdict: holds partly.** The counts are as given (profiles.csv); whether few points make a value wrong cannot be said here. The two hole-based papers give error ranges from shifting their points by 10 nm, and one paper with 20 points declines to fit because the pressure is not known well enough.
- **Missing in the ontology.** Fit quality and the number of points behind a fitted value (v0 sent fit quality to unmapped).
- **Only in text or tables.** The stated uncertainties.

### E. Cross-paper synthesis (third search, 2026-10-13)

Each candidate below needs data from three or more papers put on one axis or through one method, and its answer is stated by none of them. Inputs come from `quantity_matrix.csv` (58 in-scope papers with a PDF, 14 quantities; cells give where a value is, every cell read by hand for 41 conformality papers and found by keyword for the other 17; the exposure cell of a hand-read paper starts with a tag, names the step each value belongs to and marks it measured, calculated, assumed or fitted; 13 of the 41 state an exposure as partial pressure and time, or as the exposure itself, and 8 state it for the step that limits conformality (column `limiting_step_exposure`); column `usable_for` holds the S1, S2 and S6 judgements). Nothing is computed here except the by-eye pilots at the end, which are marked.

#### S1. One method for every sticking coefficient
- **Question.** If the same method is applied to every digitizable measured profile, do the sticking values of TMA (and other precursors) agree better than the values the papers report?
- **Papers and figures.** 10.1063_1.5028178 Fig. 6, 7; 10.1039_d0cp03358h Fig. 9, 11 and Table 1 (slopes); 10.1116_1.4903941 Fig. 5; 10.1149_1.3072694 Fig. 5; 10.1149_1.3301664 Fig. 2a, 6a (thermal); 10.1016_j.surfcoat.2012.02.038 Fig. 5; 10.1021_cm0303080 Fig. 5a, 6a; 10.1116_1.4971196 Fig. 8; 10.1016_j.apsusc.2009.02.055 Fig. 3; 10.1016_j.apsusc.2010.01.025 Fig. 1, 3. Added by the second hand pass, for a geometry-specific model only: 10.1021_acs.chemmater.1c03164 Fig. 9 (CNT forest), 10.3762_bjnano.5.25 Fig. 6b, c (CNT forest), 10.1116_1.4892385 Fig. 5 (porous layer, fitted 2e-4), 10.1021_acs.langmuir.6b03119 Fig. 3a (nanotube layer).
- **What to compute.** Digitize each profile, normalize it to its plateau, put depth in units of the limiting width, and apply one relation between the slope at half thickness and the sticking coefficient (the free-molecular slope relation used by 10.1039_d0cp03358h), or one model fit; compare with each paper's own value and method.
- **Inputs.** Profile and width: present in the ten listed first and the four added. Plateau: absent in the TiO2 profiles of 10.1063_1.5028178 and 10.1116_1.4903941. Exposure: needed only for a full fit; stated in 10.1149_1.3072694, 10.1149_1.3301664, 10.1016_j.surfcoat.2012.02.038, 10.1021_cm0303080. Geometry outside the slope relation's validity: fibre plug (10.1016_j.surfcoat.2012.02.038), radial cavity (10.1116_1.4971196), two-sided pores (10.1021_cm0303080).
- **Usable now.** 5 papers with rectangular-channel profiles for the slope method; 10 more need a geometry-specific model (15 in all). Done as Case 9.
- **Possible finding (hypothesis).** The reported TMA values span 0.0005 to 0.026; one method may narrow this to a factor of a few, with the remainder tied to temperature and to the probe's lateral resolution.
- **Ontology.** `initial_sticking_coefficient` exists; v0 lacks the method and model as attributes of a value, and the probe resolution.
- **Result (Case 9).** Like with like, the two fitted TMA values in 0.5 µm channels (0.004, 0.0057) re-derive to 6.3e-3 and 3.9e-3: one method adds nothing there. By limiting species, TMA spans 3.9e-3 to 1.3e-2 over three papers (a factor of 3.4; the reported 0.1 of the third is a chosen input); with Gao 2015's Al2O3 (limiting species not stated) a factor of 14; water 9.1e-3 against a fitted 3e-4 (30×); TiO2 about 50× below the one TiCl4 fit. Resolution-limited fronts (width under three probe spots): three EPMA scans of 10.1021_cm0303080; Yim 2020's fronts are 3.3 to 6.6 spots wide, so resolution does not explain their constant 20 to 33 µm width.
- **Feasibility: done as a by-eye case; the verdict stays feasible partly** (one method narrows TMA only by removing a chosen value).

#### S2. Exposure needed against equivalent aspect ratio across structures
- **Question.** Plotted as exposure against EAR on one scale, do holes, pores, macroscopic holes, fibre plugs and lateral channels lie on one curve near Gordon's square law?
- **Papers and figures.** 10.1002_cvde.200390005 Fig. 2, 3 and text; 10.1021_cm0303080 Fig. 3, 5, 13; 10.1149_1.3072694 Fig. 5; 10.1149_1.3301664 Fig. 2a; 10.1016_j.surfcoat.2012.02.038 Fig. 5; 10.1063_1.2714685 Fig. 7; 10.1149_1.2789802 Fig. 3; the review's Table II rows with an exposure.
- **What to compute.** Exposure in Pa·s from partial pressure and time; EAR from each structure's dimensions with the review's formulas (and half length for two-sided pores); a mark for fully coated (lower bound) or half-thickness depth (measured); Gordon's curve per precursor with its saturation density.
- **Inputs.** Partial pressure and time stated in 6 of the listed papers (10.1149_1.2789802 gives only the bubbler vapour pressure and a fitted flux); two more papers state an exposure with a coated depth: 10.1021_acs.chemmater.1c03164 (wall exposure from a measured TMA pressure trace, CNT forest, Fig. 7, 9) and 10.1116_6.0003182 (about 17,000 Torr·s of DEZ, nanoparticle compact coated through, a lower bound). Exposure absent in the lateral-channel papers (10.1039_d0cp03358h gives it only as a model input) and in 10.1116_1.4971196 and the two Rose papers. Saturation density per precursor: estimated from planar growth.
- **Usable now.** 8 papers whose stated exposure is that of the limiting step (TMA, DEZ, Hf amide, and water for the thermal 10.1149_1.3301664); 10.1149_1.2789802 drops out. Done as Case 10. The other two papers with a stated exposure (10.1021_acs.jpcc.5c06502, 10.1021_acs.jpcc.1c01505) are limited by the plasma step, not the precursor.
- **Possible finding.** Gordon's curve matches one source and overestimates the need for another by 1.2 to 3.5 times (Case 8); across eight sources the scatter around the curve may group by structure class.
- **Ontology.** `exposure` exists with a species qualifier; v0 lacks the one-sided or two-sided entry and an EAR transform per structure class.
- **Feasibility: feasible partly.**
- **Result (Case 10).** Of 16 measured depths, 62% lie within a factor of 1.5 of the square law and 81% within a factor of 3. Per paper: alumina pores 0.54 to 1.2, macroscopic slots (TMA) 0.85 to 1.1, Hf amide 0.86 to 3.1, fibre plug 0.19 to 0.89 (the 0.19 is the 2 s run its authors explain by a pressure build-up), CNT forest 2.5, water-limited slot 7.4 (on an assumed saturation density). Two bounds disagree (Elam 2003 TMA at 0.87, Kim 2007 at 4.2 with an unsaturated flat surface).

#### S3. O-radical recombination on SiO2 and TiO2 against temperature and pressure
- **Question.** Do the recombination probabilities from different reactors and pressures fall on one trend with substrate temperature and pressure?
- **Papers and figures.** 10.1021_acs.jpcc.1c01505 Fig. 5; 10.1021_acs.jpcc.9b08176 Fig. 3 and text; 10.1063_5.0168768 Fig. 3, Table I; 10.1021_acs.jpcc.5c06502 text (IrOx); 10.1149_1.3491381 Table II (literature); the review's Table VII; 10.1016_j.cattod.2003.11.022 Table 1 (out of scope, cited source).
- **What to compute.** r against substrate temperature with pressure as a second variable, one symbol per reactor and surface kind (growing film, bulk or ceramic).
- **Inputs.** Temperature and pressure present in all four ALD papers; the surface kind is implicit in the literature tables.
- **Usable now.** 4 ALD papers, 2 literature tables, 1 cited source.
- **Possible finding.** On growing SiO2 r falls with temperature and pressure within one reactor and is higher at atmospheric pressure; the bulk-surface values sit two orders above and rise with temperature.
- **Ontology.** `recombination_probability{species, surface}` exists; v0 lacks temperature, pressure and the surface kind as conditions of the value.
- **Feasibility: feasible now.**
- **Result (Case 11).** On growing SiO2 in one reactor r falls 3.4× from 100 to 240 °C, and with pressure 12× from 1.6 to 17 Pa, or 3.2× without the uncertain 1.6 Pa point. Atmospheric values are 23× (SiO2) and 9× (TiO2) the 50 mTorr values when read with the low-pressure relation, 4.3× and 1.6× with their own; the data cannot separate r from regime.

#### S4. Thermal against plasma depth at equal structure and exposure
- **Question.** Across papers, how much shallower is plasma ALD than thermal ALD at equal structure and exposure, and does the ratio follow the regime diagram of 10.1149_1.3491381?
- **Papers and figures.** 10.1016_j.surfcoat.2012.02.038 Fig. 10; 10.1149_1.3301664 Fig. 2; 10.1149_1.3491381 Fig. 9; 10.1063_1.2714685 and 10.1149_1.2789802 (plasma only; partial pressure stated in the first, a fitted flux in the second); 10.1063_1.4972120 (plasma Pt, full coverage).
- **What to compute.** Depth ratio at equal exposure; position of each case on the r-against-aspect-ratio diagram.
- **Inputs.** Matched pairs exist in 2 papers; r for the matched surfaces is only in literature tables.
- **Usable now.** 2 matched pairs and 3 plasma-only papers.
- **Possible finding.** Thermal side reactions make the measured ratio smaller than recombination alone predicts.
- **Ontology.** v0 lacks a link between two series differing in one condition.
- **Feasibility: not yet** (two pairs).

#### S5. Channel narrowing
- **Question.** Does the loss of step coverage or of half-thickness depth with film thickness follow one curve in film thickness over channel height?
- **Papers and figures.** 10.1149_1.2789802 Fig. 5; 10.1039_d0cp03358h Fig. 9d-f, Table 1; 10.1116_1.4903941 Fig. 5b; 10.1039_d1cp04758b Fig. 5e (model).
- **What to compute.** 1 − 2s/H on x for each sample (s from the plateau or the top thickness), coated depth over H or step coverage on y, against the model curve.
- **Inputs.** Thickness and H present in all four; for 10.1116_1.4903941 only the 200 nm gap closes.
- **Usable now.** 3 experiments plus the model.
- **Possible finding.** The experiments fall below the model once 2s/H exceeds about 0.3.
- **Ontology.** v0 lacks the open fraction of a channel as a derived quantity.
- **Feasibility: feasible partly.**

- **Result (Case 12, for S5).** With the mean narrowed width (W − s), thermal-channel median depth moves 141 → 184 H and pores 215 → 269 d; Yim 2020's 100 nm channel is closed by its film, and the spread of c across H grows 143 → 545, so narrowing does not explain it; Case 10's alumina pores drop from 5 to 1 of 6 within a factor of 1.5 of the square law.

#### S6. Where depth in units of channel height stops scaling
- **Question.** Does half-thickness depth over H stay constant from 0.1 µm channels to 1 mm holes, and where does it break as the Knudsen number falls?
- **Papers and figures.** 10.1039_d0cp03358h Fig. 9 (0.1 to 2 µm); 10.1116_1.4903941 Fig. 5b (0.2 to 1 µm); 10.1149_1.3072694 Fig. 5 (0.1 mm); 10.1149_1.3301664 Fig. 2a (thermal, 0.5 mm); 10.1039_d4cp00131a Fig. 5, 8 (model).
- **What to compute.** Knudsen number from the reactor pressure and H; depth over H at comparable exposure.
- **Inputs.** Reactor pressure in text for all; partial pressure and time stated only for the two macroscopic holes (10.1149_1.3072694, 10.1149_1.3301664); the lateral-channel papers give times and total pressure only.
- **Usable now.** 5 papers (10.1063_1.5028178 added), exposure stated in 2; no pair at matched exposure across scales. Checked in Case 11 with the plasma papers and the Case 10 points.
- **Possible finding.** The microscopic channels sit in the free-molecular plateau of the model; the macroscopic holes do not.
- **Ontology.** v0 lacks a Knudsen number.
- **Result (Case 11).** No thermal profile in the corpus is outside the Knudsen regime; the only data below Kn 1 are the two atmospheric plasma papers, which cannot separate a change of r from a change of regime. Thermal depths from 65 nm pores to 0.3 mm slots (Case 10) lie mostly within a factor of 3 of the square law.
- **Feasibility: not yet for thermal ALD** (no thermal data below Kn 1; the plasma data cannot separate r from regime).

#### S7. Planar saturation exposure of TMA across reactors
- **Question.** In one unit, how much TMA exposure saturates a flat surface in each reactor?
- **Papers and figures.** 10.1002_adem.202201901 Fig. 1b (dose in Torr); 10.1063_1.2714685 Fig. 7a (flat surface, injection time at 0.01 Torr); 10.1021_cm0303080 text (about 10^4 L, quoted); 10.1021_acsami.0c22121 Fig. S1 (TiCl4, no pressure); 10.1149_2.067203jes Fig. 4e (TMA with plasma, time only).
- **What to compute.** Exposure at 90% of saturated growth in Pa·s.
- **Inputs.** Pressure stated in 2 of 5.
- **Usable now.** 2 to 3.
- **Possible finding.** The quoted saturation exposures differ by more than the sticking values imply.
- **Ontology.** v0 lacks a saturation-point quantity.
- **Feasibility: not yet.**

#### S8. Planar growth per cycle of TMA/water and TMA/O2 plasma against temperature across reactors
- **Question.** On one plot, how far do reactors disagree on the growth per cycle at the same temperature?
- **Papers and figures.** 10.1002_adem.202201901 Fig. 2a; 10.1016_j.surfcoat.2012.02.038 Fig. 9; 10.1039_d0cp03358h Table 1; 10.1149_1.3072694 text; 10.1021_cm0303080 text; 10.1116_1.4971196 text; 10.1063_1.2714685 Fig. 7 (plasma); 10.1116_6.0001094 text (plasma); 10.1149_2.067203jes Fig. 4e-h (plasma reference); 10.1063_1.5028178 Table I (model value, kept apart).
- **What to compute.** Growth per cycle against temperature, measured values only, one symbol per reactor; thermal and plasma apart.
- **Inputs.** Temperature and growth per cycle stated in all; whether doses were saturating is stated in about half.
- **Usable now.** 6 thermal, 3 plasma.
- **Possible finding.** Reactors agree near 200 to 300 °C and disagree by up to 1.5 times below 150 °C.
- **Ontology.** `growth_per_cycle{position=planar}` exists; v0 lacks a flag for saturated dosing.
- **Feasibility: feasible now.**

- **Result (Case 13, for S8).** TMA/water planar growth: a batch chamber stays at 0.93–0.96 Å from 35 to 100 °C while a high-vacuum chamber falls to 0.65–0.67 Å (1.4×); at 200 °C four papers span 0.88–1.29 Å, the top from a cross-flow reactor with pulse-dependent growth; at 300 °C two papers agree within 0.90–1.03 Å; 3 of 10 papers state that saturation was checked.

#### S9. Pore-closure cycle against pore width over growth per cycle
- **Question.** Does the cycle at which pores close follow pore width over twice the planar growth per cycle across papers?
- **Papers and figures.** 10.1039_c4nr05049e Fig. 6b, 7b, 8; 10.3390_separations11010024 Fig. 7, 9; 10.1021_cm0303080 text (65 to 39 nm after 100 cycles); 10.1116_6.0003182 (porosity loss, mass gain).
- **What to compute.** Predicted against observed closure cycle.
- **Inputs.** Pore width and planar growth stated in 3; closure observed in 2.
- **Usable now.** 2 (N8 showed one agreement and one mismatch).
- **Possible finding.** The neck, not the mean pore, sets closure.
- **Ontology.** v0 lacks a neck width and a closure cycle.
- **Feasibility: not yet.**

#### S10. Temperature dependence of sticking and recombination across precursors (new)
- **Question.** Put on one Arrhenius plot, do the fitted sticking coefficients of different precursors and the recombination of O radicals share a sign and size of activation?
- **Papers and figures.** 10.1016_j.apsusc.2010.01.025 Fig. 4, Table 4 (Hf and Ti amides); 10.1149_1.2789802 Fig. 7b (TTIP); 10.1016_j.sse.2022.108584 Table 1, Fig. 5a (water); 10.1021_acs.jpcc.1c01505 Fig. 5A (O on SiO2, TiO2); 10.1116_1.4903941 Fig. 3 and text (penetration against temperature, qualitative).
- **What to compute.** ln of each value against 1/T; slopes per series.
- **Inputs.** Values with temperatures present in 4 papers.
- **Usable now.** 4.
- **Possible finding.** Precursor sticking rises with temperature in all three amide and alkoxide series, while O recombination on growing films falls.
- **Ontology.** v0 lacks temperature as a condition on model parameters.
- **Feasibility: feasible now.**

#### S11. Growth above the planar value near the entrance (new)
- **Question.** How common is a thickness or growth per cycle above the planar or plateau value near the entrance of a structure, and does it scale with dose?
- **Papers and figures.** 10.1116_1.4971196 Fig. 8 (above the test-wafer value near small holes); 10.1116_6.0001094 Fig. 11, 12 (points above 1); 10.1039_d0cp03358h Fig. 3b, Table 1 (initial thickness above the outside value); 10.1149_1.3301664 Fig. 6a (slow early decline); 10.1021_acs.jpcc.1c01505 Fig. 3A (TiO2 jump at the entrance).
- **What to compute.** Excess over the planar value against dose and structure.
- **Inputs.** Planar reference present in 4 of 5.
- **Usable now.** 4.
- **Possible finding.** The excess appears when water purge is short or the opening small, a CVD-like contribution the self-limiting models leave out.
- **Ontology.** v0 lacks a reference value for an entrance excess.
- **Feasibility: feasible partly.**

#### Ranking and pilots

| Rank | Candidate | Papers usable now | Inputs | New | Link |
| --- | --- | --- | --- | --- | --- |
| 1 | S8 planar growth against temperature | 9 | complete | yes, no paper compares reactors | twin prior for saturated growth; agent recipe questions |
| 2 | S3 recombination against temperature and pressure | 4 plus 2 tables | complete | yes | twin prior for r |
| 3 | S1 one method for sticking | 5 now, 15 with models | partial (digitizing) | yes | twin calibration and priors |
| 4 | S10 Arrhenius across precursors | 4 | complete | yes | twin priors with temperature |
| 5 | S2 exposure against EAR | 8 | partial (limiting-step exposure in 8 of 41 hand-read papers) | partly (Case 8 began it) | agent: how much dose for a structure |
| 6 | S11 entrance excess | 4 | partial | yes | twin model limits |
| 7 | S5 channel narrowing | 3 | partial | yes | twin model check |
| 8 | S6 Knudsen break | 5 | exposure stated in 2; no thermal data below Kn 1 | partly | twin validity range |
| 9 | S4, S7, S9 | 2 to 3 | too few | — | — |

**Pilot S8 (by eye, pilot).** Growth per cycle in Å, TMA and water: 10.1016_j.surfcoat.2012.02.038 Fig. 9 reads 0.66 at 50 °C, 0.67 at 100, 0.85 at 150, 1.0 at 200, 0.96 at 250, 0.94 at 300; 10.1002_adem.202201901 Fig. 2a reads 0.96 at 35, 0.93 at 60, 0.94 at 80, 0.96 at 100, 1.02 at 125 and 150; text values add 1.0 at 200 (10.1149_1.3072694), 1.29 at 177 (10.1021_cm0303080), 1.19 and 1.29 at 200 (10.1116_1.4971196), and 0.93 to 1.03 at 300 (10.1039_d0cp03358h Table 1). Impression: informative. The two reactors that both span low temperature differ by about 1.4 times at 50 to 100 °C and agree within 0.05 Å at 150 °C and above; the 177 to 200 °C text values spread from 1.0 to 1.3.

**Pilot S3 (by eye, pilot).** r of O on SiO2: about 1e-4 at 100 °C, 6.5e-5 at 180, 3e-5 at 240 (50 mTorr), and 2.5e-4 at 12 mTorr down to 2e-5 at 130 mTorr (10.1021_acs.jpcc.1c01505 Fig. 5); 6e-5 at 200 °C (10.1021_acs.jpcc.9b08176); 4e-4 at 100 °C, atmospheric (10.1063_5.0168768); literature 2e-4 and 4e-4; cited ceramic values 4e-3 to 9e-3 (out of scope, cited source). TiO2: 4e-5 at 100 and 180 °C, below 1e-5 at 240; 7e-5 at 200 °C; 6e-5 atmospheric; literature 1.4e-2. Impression: informative for SiO2 (a clear trend within one reactor and an order of magnitude between regimes); for TiO2 the ALD values cluster within a factor of two and the outlier is the bulk value.

**Pilot S1 (by eye, pilot).** Front width from 80% to 20% of the plateau, in channel heights: about 36 for 10.1063_1.5028178 Fig. 6 (Al2O3, 0.5 µm gap), about 30 for 10.1039_d0cp03358h Fig. 9 (H 500 nm), about 20 for 10.1149_1.3072694 Fig. 5 (aspect ratio 100, 0.1 mm hole); 10.1116_1.4903941 Fig. 5a never reaches 20% (a floor near 22 nm). The papers' own TMA values for the first three are 0.0057 (fit), 0.004 (slope) and 0.1 (chosen). Impression: informative but confounded: the widths differ by less than a factor of two while the reported values differ by 25 times, and probe resolution and channel narrowing both widen fronts.

### F. Within-paper candidates (third search)

Brief; each with the field that matters most. "Cross-paper" marks those that grow by adding other papers.

- **E1. Saturation is local.** 10.1063_1.2714685 Fig. 7a, 10.1149_1.2789802 Fig. 3a, 6a, 7a, 10.1002_cvde.200390005 Fig. 2: growth per cycle on the flat surface saturates within seconds while the hole bottom needs ten to a hundred times longer. Verdict: feasible now. Cross-paper: yes, joins S2 (the ratio of bottom to flat saturation time against aspect ratio).
- **E2. Calibrate once, predict elsewhere.** 10.1063_1.2714685 Fig. 7a (fit) against Fig. 9 (second pressure); 10.1149_1.2789802 Fig. 3a (fit) against Fig. 6a and 7a. Each paper states that the prediction agrees; nobody quantifies by how much. Verdict: feasible now (two predictions per paper). Cross-paper: yes, with 10.1016_j.sse.2022.108584 Fig. 7 (N2).
- **E3. Parameters as functions of temperature.** 10.1016_j.apsusc.2010.01.025 Fig. 4, 10.1149_1.2789802 Fig. 7b. Verdict: feasible now; it is S10 within each paper.
- **E4. How well a fitted value is determined.** Misfit curves: 10.1116_1.4971196 Fig. 10, 13 (flat over a factor of 30 for TMA, narrow for BDEAS); 10.1016_j.apsusc.2009.02.055 Fig. 4; 10.1016_j.apsusc.2010.01.025 Fig. 2, 3 (shifted-profile ranges). Verdict: feasible now. Cross-paper: yes, joins N13 (points behind a value).
- **E5. Properties along the depth.** 10.1149_1.3301664 Fig. 5d (AlN refractive index falls with depth), Fig. 8 to 10 (water from the plasma step); 10.1021_acs.jpclett.4c03545 Fig. 4 (XPS at the opening and inside); 10.1116_6.0002804 Fig. 10 (oxygen share doubled at the trench bottom, text). Verdict: feasible partly (qualitative in two of three). Cross-paper: yes, a composition-against-depth case across these three.
- **E6. Conformality depends on how much was deposited.** 10.1149_1.2789802 Fig. 5 (step coverage 73% to 52% from 200 to 500 cycles); 10.1116_1.4903941 Fig. 5b (the 200 nm gap closes). Verdict: feasible now. Cross-paper: it is S5.
- **E7. A worked example end to end.** 10.1149_1.3301664 (structure, conditions, profiles at four settings, emission spectrum, Monte Carlo with two side reactions) or 10.1039_d0cp03358h (16 samples, Table 1 with every derived number, simulation). Verdict: feasible now; 10.1039_d0cp03358h is the better choice because Table 1 lets every derived number be checked against its profile.

## Cremers 2019 read as data (cremers.py)

Exploration, 2026-10-13. The review is Cremers, Puurunen and Dendooven, Appl. Phys. Rev. 6, 021302 (2019). Its Tables II to VII were typed in by hand (`cremers.py`) and every row was compared with the page image. All values are data_kind cited; blank cells stay blank; footnote markers are in `note`.

Files: `cremers_conformality.csv` (140 rows), `cremers_parameters.csv` (68 rows), `cremers_source_checks.csv`, `cremers_new_rows.csv`, `cremers_profiles.csv`, `cremers.py`. Plots: Case 8 of the Cases tab of `reports/pilot.html` (not tracked).

Updated the same day after 15 PDFs were obtained by hand (refs 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228, 251 and 10.1021/acs.jpcc.1c01505). `in_corpus` (was `in_44`) marks rows whose source is in scope and has a PDF; `source_scope` says "out of scope, cited source" for rows whose source is excluded (the Table VII sources, refs 250 to 263, and ref. 134), whose values are kept only as cited data; `value_from_source` holds what the source gives for cells the review leaves blank, and never replaces a transcribed value. What the new sources changed is said under each result.

### Step 1. Transcription

| Table | Content | Rows | Rows whose source is in scope with a PDF |
| --- | --- | --- | --- |
| II | thermal ALD | 71 | 16 |
| III | ozone-based ALD | 24 | 5 |
| IV | plasma ALD | 45 | 10 |
| V | sticking probabilities | 27 | 13 |
| VI | ozone recombination | 6 | 0 |
| VII | atom recombination | 35 | 0 |

Things seen while typing that a reader of the tables should know:
- The PD50% mark is an asterisk. It is lost in the PDF text layer, so it was read from the page images.
- Five reference numbers, in seven rows, have no DOI in the manifest (150, 168, 176, 201, 213).
- Table IV uses a plasma configuration "HW" that its caption does not define.
- Table V lists the ref. 77 value for TiCl4 on a line whose material cell is empty under "TiN"; the source deposits TiO2.
- The running text and the tables disagree in three places: ozone Al2O3 (text 20:1, table "Ref. 175"), the reference for ozone V2O5 (text 78, table 150), and O on Pyrex (text 0.000094, table 0.000045).

### Step 2. Source checks

48 rows point to a paper with a PDF (four of them to ref. 251, out of scope and kept as a cited source): 35 agree, 10 differ, 3 not found. Of these, 16 were checked against papers parsed before 2026-10-13 and 32 against the papers whose PDFs were obtained by hand that day (25 agree, 6 differ, 1 not found). `value_from_source` is filled in 11 rows: 5 give a value the review lacks, 6 record that the source does not state the exposure either.

| Table | Row in the review | Ref. | Paper | Verdict | Where | Remark |
| --- | --- | --- | --- | --- | --- | --- |
| II | Al2O3 TMA/H2O, LHAR, 300 °C, coated 130* (D) | 77 | 10.1063_1.5028178 | agree | Fig. 6, Table I | half thickness at about 133 µm (by eye) in a 0.5 µm gap gives 133 with the trench formula; the 300 °C is not in the parsed text; the printed EAR 10-12500 is the chip family, the sample has L 1 mm (AR 2000) |
| II | TiO2 TiCl4/H2O, LHAR, 110 °C, coated 90* (D) | 77 | 10.1063_1.5028178 | agree | Fig. 7 | half of the entrance thickness at about 90 µm (by eye); the profile has no plateau; the 110 °C is not in the parsed text |
| III | TiO2 TDMAT/O3, CNT, 100 °C, exposure 4500 | 98 | 10.1039_c3ra42928h | agree | experimental section | 0.3 mbar for 20 s is 4.5 Torr s, i.e. 4500 × 10^3 L; the review computed the exposure, the source does not print it |
| II | TiO2 TTIP/H2O, VACNT, 225 °C, (D) | 100 | 10.3762_bjnano.5.25 | agree | methods, Fig. 6b | 225 °C, TTIP and water, thickness against depth; no aspect ratio in the source either |
| II | TiO2 TiCl4/H2O, AAO, EAR 7.5, 200 °C, coated 7.5 | 140 | 10.1186_s11671-015-0872-9 | agree | abstract, methods | 500 nm deep, 67 nm pores, 7.5:1, filled |
| II | Fe3O4 Fe(Cp)2/O2, AAO, 400 °C | 144 | 10.1038_srep18401 | agree | methods | ferrocene and oxygen at 400 °C; no pore dimensions found, as in the review |
| II | Ir Ir(acac)3/O2, trench, 370 °C (thermal table) | 169 | 10.1016_j.mee.2018.01.027 | not found | process section | precursors agree; 370 °C is not in the parsed text; the source says oxygen can be supplied thermally or through the plasma and does not say which was used, and gives a 30 µm depth the review leaves out |
| IV | Ir Ir(acac)3/O2*, trench, 370 °C (plasma table) | 169 | 10.1016_j.mee.2018.01.027 | not found | process section | same paper listed in both tables; mode not stated in the source |
| II | Pt MeCpPtMe3/O2, AAO, EAR 200, coated 50 | 173 | 10.1007_s12274-010-0066-9 | differ | text on AAO templates, Fig. 2 | 60 µm thick with 250 to 300 nm pores gives 200 to 240; the source gives a penetration that saturates near 20 µm (about 70 to 80) and tubes 15 µm long (about 50 to 60): the review took the tube length |
| II | Pt MeCpPtMe3/O2, hole, EAR 90, coated 30 | 173 | 10.1007_s12274-010-0066-9 | agree | Fig. 3e-f | 30 µm of a 90 µm pore of 1 µm; the same figure shows 90 µm reached with added exposure time, which the review does not list |
| III | Pt Pt(acac)2/O3, AAO, EAR 120, 150 °C, coated 50 | 196 | 10.1039_c5ta00205b | differ | abstract, text at Fig. 6 | coated 50 agrees; the structure value 120 was not found (the abstract says 70); both 130 and 150 °C were used |
| IV | Al2O3 TMA/O2*, trench, EAR 15, coated 15* | 202 | 10.1149_2.067203jes | differ | conformality paragraph, Fig. 8 | the source tests SiO2 only; the alumina in that trench is an underlayer for contrast, and no half-thickness depth is given |
| IV | SiO2 H2Si[N(C2H5)2]2/O2*, trench, EAR 15, coated 15 | 202 | 10.1149_2.067203jes | agree | conformality paragraph, Fig. 8 | aspect ratio about 30 for a trench is 15; 95 to 100% bottom to top |
| IV | Ir Ir(acac)3/O2*, hole (elongated), 370 °C, I | 226 | 10.1016_j.mee.2018.01.033 | agree | methods | 370 °C, oxygen plasma, inductively coupled |
| V | Al(CH3)3 on Al2O3, continuum model, 300 °C, 0.00572 | 77 | 10.1063_1.5028178 | agree | Table I, Eq. for the adsorption rate | c = 0.00572; c multiplies (1 − θ), so it is an initial (bare-surface) value, called a lumped sticking coefficient |
| V | TiCl4 on TiN, continuum model, 110 °C, 0.1 | 77 | 10.1063_1.5028178 | differ | Table I | value agrees (0.10) but the source deposits TiO2; TiN is carried over from the line above in the table |
| II | Al2O3 TMA/H2O, macro lateral, EAR 100, 200 °C, exposure 9, coated 50* (D) | 67 | 10.1149_1.3072694 | agree | experimental section, Fig. 5 | 0.3 Pa for 4 s is 1.2 Pa s, i.e. 9.0 × 10^3 L; aspect ratio 100 by the source's perimeter definition; half thickness at about 10.7 of 20 mm (by eye) gives 53 |
| II | Al2O3 TMA/H2O, AAO, EAR 770, 177 °C, exposure 4500, coated 770 | 65 | 10.1021_cm0303080 | agree | Sec. III A, Fig. 3 | 65 nm x 50 um gives 769; 0.15 Torr for 30 s is 4500 × 10^3 L. The source coats the membrane already at 3 s (450) and the pores are open at both ends: the review lists the largest exposure used and the full length |
| II | ZnO DEZ/H2O, AAO, EAR 700, 177 °C, exposure 2000, coated 700 (D) | 65 | 10.1021_cm0303080 | differ | Sec. III B, Fig. 5 | exposure agrees (0.068 Torr for 30 s); the membrane is the same 65 nm x 50 um one that the Al2O3 row lists as 770 |
| II | ZnO DEZ/H2O, AAO, EAR 5000, 177 °C, exposure 600000, coated 5000 (D) | 65 | 10.1021_cm0303080 | agree | Sec. III B, Fig. 7 | 19 nm x 92 um; 5 Torr for 120 s |
| II | Al2O3 TMA/H2O, LHAR, 300 °C, coated 75* (D) | 86 | 10.1116_1.4903941 | agree | Fig. 4, Fig. 5a | film to 65 um in a 500 nm gap (AR 130, stated), half thickness near 70 um by eye: 65 to 70 with the trench formula; EAR range 10 to 12500 matches half of the Fig. 1 table |
| II | TiO2 TiCl4/H2O, LHAR, 110 °C, coated 65* (D) | 86 | 10.1116_1.4903941 | agree | text to Fig. 5b | 50% of the entrance value at AR 130, stated; the profile has no plateau |
| II | Al2O3 TMA/H2O, macro lateral, EAR 5, 75 °C, exposure 18, coated 2.5* (D) | 69 | 10.1016_j.surfcoat.2012.02.038 | agree | Sec. 2, Fig. 5 | 0.08 Pa for 30 s is 18 × 10^3 L; half value at 27 mm of a 1 cm wide hole. The hole is filled with a fibre non-woven, which the row does not say: its EAR is not that of an empty hole |
| II | HfO2 Hf(NMe2)4/H2O, holes, EAR 36, 150 °C, exposure 9, coated 36 | 62 | 10.1002_cvde.200390005 | agree | Sec. 4, Sec. 6 | elliptical holes 0.17 x 0.30 x 7.3 um, aspect ratio 36 by the source; 9 × 10^3 L is the calculated minimum, the fully coated sample had 30 |
| III | TiO2 TDMAT/O3, hole, EAR 20, 180 °C, coated 20* (D) | 178 | 10.1016_j.apsusc.2009.02.055 | differ | Sec. 2, Fig. 3 | the source writes AR = 20 for holes of 130 nm x 2 um, which is 15.4 (the review uses 15.3 for the same holes in the ref. 180 rows); the profile falls only to 70% of its top value, so no half-thickness depth exists |
| III | TiO2 Cp*Ti(OMe)3/O3, hole, EAR 15.3, 270 °C, (D) | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Sec. 3, Fig. 3 |  |
| III | HfO2 TEMAHf/O3, hole, EAR 15.3, 180 °C, coated 9.6* (D) | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 1a | half of 18.8 nm near 1250 nm, over 130 nm; the 230 and 270 °C profiles of the same figure are not listed |
| IV | Al2O3 TMA/O2*, macro lateral, EAR 10, 200 °C, RI, exposure 27, coated 10 (D) | 70 | 10.1149_1.3301664 | differ | experimental section, Fig. 2b | structure, temperature and coating agree (thickness falls to about 75% at the end, above one half); the exposure does not reproduce: 0.3 Pa for 9 s is 20, for 18 s it is 40 |
| IV | Al2O3 TMA/O2*, macro lateral, EAR 5, 75 °C, RI, exposure 5, coated 0.75* (D) | 69 | 10.1016_j.surfcoat.2012.02.038 | differ | Fig. 10 | exposure agrees as the TMA exposure (0.08 Pa for 8 s); the plasma profile is at half its entrance value near 3 mm, i.e. about 0.3, not 0.75 |
| IV | Al2O3 TMA/O2*, hole, EAR 10, 225 °C, exposure 30, coated 10 | 200 | 10.1063_1.2714685 | agree | Sec. IV, Fig. 7 | 0.3 um holes of aspect ratio 10; 0.01 Torr for 3 s is 30 × 10^3 L, a TMA exposure |
| IV | TiO2 TTIP/O2*, hole, EAR 8.7, 225 °C, coated 8.7 (D) | 204 | 10.1149_1.2789802 | agree | experimental conditions, Fig. 2b, Fig. 4 | full coverage needs a long TTIP pulse; at 5 s the bottom has 52% (Fig. 4, 5) |
| IV | AlN TMA/NH3*, macro lateral, EAR 10, 200 °C, RI, exposure 40, coated 2.5* (D) | 70 | 10.1149_1.3301664 | agree | Fig. 5b | 0.3 Pa for 18 s is 40 × 10^3 L; half thickness at 4 to 5 of 20 mm |
| IV | Pt MeCpPtMe3/O2*, trench, EAR 17, 300 °C, I, coated 17 (D) | 228 | 10.1063_1.4972120 | agree | Table II, Fig. 5 | trench aspect ratio 34, conformality 92 ± 8% |
| V | Al(CH3)3, Monte Carlo model, 177 °C, 0.001 | 65 | 10.1021_cm0303080 | differ | Sec. IV D | the value is quoted there from an earlier paper and used as an input; it is not derived with the Monte Carlo model |
| V | Al(CH3)3, ballistic model, 225 °C, 0.026 | 200 | 10.1063_1.2714685 | agree | Sec. IV, Fig. 8 | an initial sticking probability, fitted, for TMA in the TMA/O2 plasma process |
| V | Al(CH3)3, semi-analytical model, 200 °C, 0.1 | 67 | 10.1149_1.3072694 | differ | text to Fig. 6 | 0.1 is a value chosen for the simulation; the source says a fit would need the pressure to 0.01 Pa and does not make one |
| V | Al(CH3)3, Monte Carlo model, 200 °C, 0.02 | 128 | 10.1116_1.4971196 | agree | Sec. IV A 3 | fitted; range 0.009 to 0.02 |
| V | Hf(NEtMe)4, Monte Carlo model, 180-270 °C, 0.03-0.6 | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 1 | 0.031, 0.15, 0.56 at 180, 230, 270 °C |
| V | Ti(NMe2)4, Monte Carlo model, 180 °C, 0.02 ± 0.005 | 178 | 10.1016_j.apsusc.2009.02.055 | agree | Fig. 4 | from four thickness points |
| V | Ti(OiPr)4, ballistic model, 125-225 °C, 0.04-0.1 | 204 | 10.1149_1.2789802 | agree | Fig. 7b, Table II | initial sticking probability with an adsorption order |
| V | Cp*Ti(OMe)3, Monte Carlo model, 270 °C, 0.01 | 180 | 10.1016_j.apsusc.2010.01.025 | agree | Fig. 3 | range 0.006 to 0.018 |
| V | ZnEt2, Monte Carlo model, 177 °C, 0.007 | 65 | 10.1021_cm0303080 | not found | Sec. IV C | 0.007 is the value used in the simulations; how it was obtained was not found |
| V | SiCl4, Monte Carlo model, 10^-8 | 65 and 239 | 10.1021_cm0303080 | agree | Sec. III C, IV D | quoted there from the second reference |
| V | H2Si[N(C2H5)2]2, Monte Carlo model, 300 °C, 3 × 10^-5 | 128 | 10.1116_1.4971196 | agree | Sec. IV B 3 | fitted; range 3 to 5 × 10^-5 |
| VII | O on alumina, 0.0097 ± 0.0019 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K, ± 20%, on a sintered ceramic in an air plasma at 110 Pa; 0.061 at 773 K |
| VII | O on titania, 0.014 ± 0.003 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K; 0.031 at 773 K |
| VII | O on iron(II, III) oxide, 0.015 ± 0.003 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | at 300 K |
| VII | O on cobalt oxide, 0.029 ± 0.006 (out of scope, cited source) | 251 | 10.1016_j.cattod.2003.11.022 | agree | Table 1 | CoO at 300 K |

### Step 3. Computed

#### a. Exposure coverage

| Table | Rows | Rows with an exposure |
| --- | --- | --- |
| II | 71 | 20 |
| III | 24 | 1 |
| IV | 45 | 6 |

TMA/H2O, coated EAR against exposure (10^3 L):

| Structure | EAR | T (°C) | Exposure | Coated EAR as printed | Reading | Ref. |
| --- | --- | --- | --- | --- | --- | --- |
| Macro lateral | 100 | 200 | 9 | 50* (D) | measured (PD50%) | 67 |
| Trench | 5 | 300 | — | 5 | lower bound | 134 |
| AAO | 8.5 | 200 | 300 | 8.5 | lower bound | 135 |
| Nanorods (ZnO) |  | 300 | 560 | Conformal | no number | 99 |
| Pillars (Si) |  | 125 | — | Conformal | no number | 93 |
| AAO | 1750 | 177 | — | 1750 | lower bound | 96 |
| AAO | 770 | 177 | 4500 | 770 | lower bound | 65 |
| LHAR | 10-12500 | 300 | — | 75* (D) | measured (PD50%) | 86 |
| LHAR | 10-12500 | 300 | — | 130* (D) | measured (PD50%) | 77 |
| Trench | 11 |  | — | 11 | lower bound | 138 |
| Macro lateral | 5 | 75 | 18 | 2.5* (D) | measured (PD50%) | 69 |
| Hole | 17 | 200 | 370 | 17 | lower bound | 139 |

Of the six rows with an exposure, two are measured depths, three are lower bounds and one has no number. The two measured ones do not order by exposure (50 at 9, 2.5 at 18): the second is a hole filled with fibres at 75 °C (ref. 69, now read).

What the new sources add. From the sources, at the same exposures:

| Exposure (10^3 L) | Coated EAR | Reading | Structure | Where |
| --- | --- | --- | --- | --- |
| 9 | 33 | lower bound | macro hole, aspect ratio 33, fully coated | 10.1149_1.3072694 Fig. 5 |
| 9 | 47 | measured, by eye | macro hole, aspect ratio 50, half thickness at about 19 of 20 mm (by eye) | 10.1149_1.3072694 Fig. 5 |
| 9 | 53 | measured, by eye | macro hole, aspect ratio 100, half thickness at about 10.7 mm (by eye) | 10.1149_1.3072694 Fig. 5 |
| 450 | 385 | lower bound | AAO 65 nm x 50 um, coated from both ends at 3 s | 10.1021_cm0303080 Fig. 3 |
| 150 | 385 | upper bound | the same membrane at 1 s: centre not coated | 10.1021_cm0303080 Fig. 3 |

The kinetic model of ref. 62 gives the exposure for full coverage as a flat-surface exposure times (1 + 19a/4 + 3a²/2). For TMA at 200 °C with 4.5e+18 molecules per m² per cycle (the saturation value of 10.1063_1.2714685, an assumption here) the flat-surface exposure is 2.4 L, and 9 × 10^3 L should coat an aspect ratio of 49. Ref. 67 measures 47 to 53 at that exposure. For the 65 nm by 50 µm membrane of ref. 65 the model asks for 530 × 10^3 L when the pores are entered from both ends (aspect ratio 385) and 2106 × 10^3 L if they were entered from one; the source finds the centre uncoated at 150 and coated at 450. Two sources test the square law of ref. 62 for TMA and water. For ref. 67 it predicts a coated aspect ratio of 49 at 9 × 10³ L, against 47 and 53 read by eye and one fully coated structure of 33 (a lower bound), so it matches. For ref. 65 it asks for 530 × 10³ L, while the centre of the membrane was already coated by an exposure between 150 and 450 × 10³ L, so there the model overestimates the need by about 1.2 to 3.5 times. The ref. 65 comparison counts the membrane at half its length, which the source supports: it states that the top and bottom of the membrane are both directly exposed to the precursors in the flow tube (Sec. III A), and its model has the pores entered from both ends at equal rates, over half their length (Sec. IV A). The review's 770 at 4500 is a fully coated structure at about eight times the predicted need. The blanks of refs 86 and 77 cannot be filled from their sources.

#### b. EAR check and the unit conversion

| Source | Dimensions | Formula | Computed | Printed | Result |
| --- | --- | --- | --- | --- | --- |
| 10.1186_s11671-015-0872-9 (ref. 140) | hole, 500 nm deep, 67 nm wide | L/w | 7.5 | 7.5 | agree |
| 10.1007_s12274-010-0066-9 (ref. 173) | hole, 90 µm deep, 1 µm wide | L/w | 90 | 90 | agree |
| 10.1007_s12274-010-0066-9 (ref. 173) | AAO, 60 µm thick, 250 to 300 nm pores | L/w | 200 to 240 | 200 | agree |
| 10.1149_2.067203jes (ref. 202) | trench, 18.5 µm deep, 0.6 µm wide | L/(2w) | 15 | 15 | agree |
| 10.1063_1.5028178 (ref. 77) | lateral channel, half thickness at about 133 µm, gap 0.5 µm | L/(2w) | about 133 | 130 (coated) | agree |
| 10.1039_c5ta00205b (ref. 196) | AAO; dimensions of the coated membrane not found | L/w | — | 120 | cannot check |
| 10.1116_6.0001094 (not a review row) | trench, 20 mm deep, 1 mm opening | L/(2w) | 10 | 10 (stated by the source) | agree |
| 10.1021_acs.jpcc.5c06502 (not a review row) | lateral channel, PD50% 4.4 µm, gap 0.5 µm | L/(2w) | 4.4 | 4.4 (stated by the source) | agree |
| 10.1002_cvde.200390005 (ref. 62) | elliptical holes 0.17 x 0.30 um, 7.3 um deep | L(w+z)/(2wz) | 34 | 36 | agree (the source computes 36 from the true perimeter) |
| 10.1149_1.3072694 (ref. 67) | rectangular hole 5 x 20 mm, 0.1 mm high (height from the review's Fig. 22) | L(w+z)/(2wz) | 102 | 100 | agree |
| 10.1149_1.3301664 (ref. 70) | rectangular hole 5 x 20 mm, spacer 3.9, 1.3, 0.5 mm | L(w+z)/(2wz) | 4.6; 9.7; 22 | 10 (the row used) | agree |
| 10.1021_cm0303080 (ref. 65) | pores 65 nm x 50 um; 19 nm x 92 um | L/w | 769; 4840 | 770 and 700 for the first; 5000 | agree, but one membrane has two values; pores open at both ends, so the diffusion length is half |
| 10.1016_j.apsusc.2009.02.055 and 2010.01.025 (refs 178, 180) | holes 130 nm x 2 um, the same in both papers | L/w | 15.4 | 20 (ref. 178 row); 15.3 (ref. 180 rows) | differ for ref. 178: 20 is the number the source writes, not what its dimensions give |
| 10.1063_1.2714685 (ref. 200) | holes 0.3 um, aspect ratio 10 stated | L/w | 10 | 10 | agree |
| 10.1149_1.2789802 (ref. 204) | holes 0.15 um, aspect ratio 8.7 stated | L/w | 8.7 | 8.7 | agree |
| 10.1063_1.4972120 (ref. 228) | trenches, aspect ratio up to 34 | L/(2w) | 17 | 17 | agree |
| 10.1116_1.4903941 (ref. 86) | lateral channels, aspect ratio 20 to 25000 (Fig. 1 table) | L/(2w) | 10 to 12500 | 10-12500 | agree |
| 10.1016_j.surfcoat.2012.02.038 (ref. 69) | hole 1 x 1 x 5 cm filled with fibres | L/w | 5 for the empty hole | 5 | agree as a hole; the fibre filling is not in the number |

The conversion in Sec. II D is printed as "1 L = 10^6 Torr s = 7500 Pa s". Both parts are wrong as printed: 1 L is 10^-6 Torr s, which is 1.33 × 10^-4 Pa s, and it is 1 Pa s that equals 7500 L. The tables use the correct relation: the review's own Fig. 22 gives 0.27 Pa for 4 s, which is 8100 L against the 9 × 10^3 L of the first row of Table II, and the ref. 98 row reproduces from the source's pressure and pulse time.

#### c. Recombination probability against coated EAR (Table IV with Table VII)

Mappings used: Al2O3 → O on alumina (O2 plasma; the growing surface is alumina); SiO2 → O on silica (O2 plasma; silica); TiO2 → O on titania (O2 plasma; titania); Ni → H on nickel (H2 plasma on a nickel film); Cu → H on copper (H2 plasma on a copper film).
Left out: HfO2, Ta2O5 (no hafnia or tantala surface in Table VII); Ti (TiCl4/O2*) (film printed as Ti; unclear whether metal or oxide); AlN, SiNx, TiN, Mo2N, TaN (Table VII has N and H on metals, silicon, silica and steel, but on no nitride); Co, Ru (NH3*) (no cobalt or ruthenium surface for H or N); Ag, Ta (H2*) (no silver or tantalum surface); Ir, Pt (O2*) (no noble-metal surface for O atoms in Table VII (Table VI has ozone on Pt only)).

| Film | Process | Structure | EAR | Coated EAR | Reading | r from Table VII | Ref. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Al2O3 | TMA/O2* | Macro lateral | 10 | 10 | lower bound | 0.0021 to 0.0097 | 70 |
| Al2O3 | TMA/O2* | Hole | 8 | 8 | lower bound | 0.0021 to 0.0097 | 197 |
| Al2O3 | TMA/O2* | Trench | 13.5 | 13.5 | lower bound | 0.0021 to 0.0097 | 198 |
| Al2O3 | TMA/O2* | Macro lateral | 5 | 0.75 | measured (PD50%) | 0.0021 to 0.0097 | 69 |
| Al2O3 | TMA/O2* | Hole | 10 | 10 | lower bound | 0.0021 to 0.0097 | 200 |
| Al2O3 | TMA/O2* | Trench | 2 | 2 | lower bound | 0.0021 to 0.0097 | 201 |
| Al2O3 | TMA/O2* | Trench | 15 | 15 | measured (PD50%) | 0.0021 to 0.0097 | 202 |
| SiO2 | 3DMAS/O2* | Trench | 30 | 30 | lower bound | 0.0004 | 198 |
| SiO2 | H2Si[N(C2H5)2]2/O2* | Trench | 15 | 15 | lower bound | 0.0004 | 202 |
| TiO2 | TTIP/O2* | Trench | 13.5 | 13.5 | lower bound | 0.014 | 198 |
| TiO2 | TTIP/O2* | Hole | 8.7 | 8.7 | lower bound | 0.014 | 204 |
| Ni | Ni(Cp)2/H2O/H2* | Hole (TaN) | 3.3 | 3.3 | lower bound | 0.18 to 0.25 | 221 |
| Cu | Cu(acac)2/H2* | Trench (SiO2) | 1.75 | 1.75 | lower bound | 0.14 | 222 |
| Cu | Cu(acac)2/H2* | (trench) | 2.5 | 2.5 | lower bound | 0.14 | 222 |
| Cu | Cu(acac)2/H2* | (trench) | 4.5 | 4.5 | lower bound | 0.14 | 222 |

r of O atoms in the parsed papers, beside Table VII:

| Surface | Table VII | From the parsed papers | Conditions | Paper | Where |
| --- | --- | --- | --- | --- | --- |
| Silica | 0.0004 | 6e-05 | 50 mTorr, 200 °C | 10.1021_acs.jpcc.9b08176 | Fig. 3 |
| Titania | 0.014 ± 0.003 | 7e-05 | 50 mTorr, 200 °C | 10.1021_acs.jpcc.9b08176 | Fig. 3 |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.001 to 0.01 | 50 mTorr, 200 °C; a range | 10.1021_acs.jpcc.9b08176 | text, Table 1 |
| Hafnia | — | 0.001 to 0.1 | 50 mTorr, 200 °C; a range | 10.1021_acs.jpcc.9b08176 | text, Table 1 |
| Silica | 0.0004 | 0.0004 | atmospheric, 100 °C | 10.1063_5.0168768 | Fig. 3, Table I |
| Titania | 0.014 ± 0.003 | 6e-05 | atmospheric, 100 °C | 10.1063_5.0168768 | Fig. 3, Table I |
| Iridium oxide | — | 0.003 | atmospheric | 10.1021_acs.jpcc.5c06502 | body text |
| Silica | 0.0004 | 3e-05 to 0.0001 | 50 mTorr, 100 to 240 °C; falls with temperature | 10.1021_acs.jpcc.1c01505 | Fig. 5A |
| Silica | 0.0004 | 2e-05 to 0.00025 | 180 °C, 12 to 130 mTorr; falls with pressure | 10.1021_acs.jpcc.1c01505 | Fig. 5B |
| Titania | 0.014 ± 0.003 | 1e-05 to 4e-05 | 50 mTorr, 100 to 240 °C; upper limit at 240 °C | 10.1021_acs.jpcc.1c01505 | Fig. 5A |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.0097 to 0.061 | out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Titania | 0.014 ± 0.003 | 0.014 to 0.031 | out of scope, cited source: sintered ceramic, 110 Pa air plasma, 300 to 773 K; rises with temperature | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Silica | 0.0004 | 0.004 to 0.0093 | out of scope, cited source: oxidized SiC, 110 Pa air plasma, 300 to 773 K | 10.1016_j.cattod.2003.11.022 | Table 1 |
| Silica | 0.0004 | 0.0002 | literature value, cited | 10.1149_1.3491381 | Table II |
| Alumina | 0.0021; 0.0097 ± 0.0019 | 0.0021 | literature value, cited (the same as Table VII) | 10.1149_1.3491381 | Table II |
| Silica | 0.0004 | 9e-05 | low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 1e-4) | 10.1063_5.0168768 | Table I |
| Titania | 0.014 ± 0.003 | 4e-05 | low pressure, 100 °C, cited there from 10.1021_acs.jpcc.1c01505 (its Fig. 5A reads about 4e-5) | 10.1063_5.0168768 | Table I |

What the new sources changed. The Table VII values of ref. 251 (out of scope as not an ALD paper, kept as a cited source) are confirmed, and their conditions are now known: sintered oxide discs at 300 K in an air plasma at 110 Pa, measured by emission actinometry, with r rising with temperature (alumina 0.0097 to 0.061, titania 0.014 to 0.031 between 300 and 773 K). The lateral-channel values of 10.1021_acs.jpcc.1c01505 are for the growing ALD film at 50 mTorr: titania about 4e-5 at 100 to 180 °C and below 1e-5 at 240 °C, falling with temperature. The titania gap is therefore a factor of about 350 at the low end and above 3000 near 500 K, with opposite temperature trends. Ref. 66 is the table that Table VII was updated from; it is a literature table itself. Ref. 228 quotes 0.01 for O on platinum, a surface Table VII lacks. Two of the fifteen matched rows change on the source check: ref. 69 (0.3 instead of 0.75) and ref. 70 (exposure).

#### d. Same film, different oxidant

| Film | Structure matched on | Thermal | Ozone | Plasma | Remark |
| --- | --- | --- | --- | --- | --- |
| Al2O3 | macro lateral, EAR 5, 75 °C, one paper (ref. 69) | 2.5 PD50 at 18 | — | 0.75 PD50 at 5 | best match in the tables: same structure, temperature and paper; exposures differ by 3.6 |
| Al2O3 | macro lateral, 200 °C (refs 67, 70) | 50 PD50 at 9 (EAR 100) | — | 10 complete at 27 (EAR 10) | plasma value is a lower bound capped by the structure |
| Al2O3 | maximum per table | 1750 complete | none in the table (text: 20) | 15 PD50; 13.5 complete | the 30 often quoted for plasma is SiO2 and HfO2 |
| TiO2 | hole | — | 20 PD50 (EAR 20) | 8.7 complete (EAR 8.7) | no exposure in either |
| HfO2 | hole | 36 complete at 6 to 9 | 9.6 PD50 (EAR 15.3) | — (trench: 30 complete) | ozone row has no exposure |
| Pt | AAO, EAR 150 | 110 PD50, 250 °C | 35 PD50, 150 °C | — | same structure value; temperatures differ; no exposure |
| Ir / IrO2 | LHAR, one paper (ref. 87) | 15 and 20 PD50, 250 °C | 15 and 45 PD50, 185 °C | — | same structure and paper; no exposure |
| V2O5 | AAO | 7000 complete | 100 complete; 44 of 185 | — | no exposure |
| ZnO | AAO | 700 and 5000 complete at 2000 and 600000 | 250 complete | — | ozone row has no exposure |
| Ru | hole | 4.6 to 32 complete; 20 PD50 | 16 complete | — (trench: 2 complete) | all but one are lower bounds |
| Al2O3 | fibre-filled macro hole, 75 °C, same TMA exposure of 4.8, one paper (10.1016_j.surfcoat.2012.02.038 Fig. 10; from the source, by eye) | about 1.8 PD50 | — | about 0.3 PD50 | the matched pair the review rows miss: its thermal row is the 30 s run (18), its plasma row the 8 s run (5) |
| Al2O3 | empty macro hole, aspect ratio 22, 200 °C, same exposures, one paper (10.1149_1.3301664 Fig. 2; from the source, by eye) | 22 complete | — | about 14 PD50 | stated by the source to differ only in the pump time; the review pairs a ref. 67 row with a ref. 70 row of another structure |

What the new sources changed: the last two rows. They are the only pairs with the same structure, temperature and exposure, and both come from reading the source, not from the review's rows.

#### e. Sticking values

| Species | Value | Method or model | data_kind | s or s0 | Source | In Table V |
| --- | --- | --- | --- | --- | --- | --- |
| TMA | 0.001 | Monte Carlo model (value quoted from an earlier paper and used as input) | cited | s (reactive sticking coefficient) | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| TMA | 0.026 | ballistic model with re-emission, adsorption order 1.9; TMA/O2 plasma process | fit | s0 (checked in the source) | review Table V, ref. 200 = 10.1063_1.2714685 | yes |
| TMA | 0.1 | conductance model; value chosen, no fit made | simulation input | s0 (checked in the source) | review Table V, ref. 67 = 10.1149_1.3072694 | yes |
| TMA | 0.1 to 0.9 | DFT | calculated | not checked | review Table V, ref. 176 | yes |
| TMA | 0.00572 | continuum (diffusion-reaction) model | fit | s0 (checked in the source) | review Table V, ref. 77 = 10.1063_1.5028178 | yes |
| TMA | 0.009 to 0.02 | Monte Carlo model of a cavity, best value 0.02 | fit | s0 (checked in the source) | review Table V, ref. 128 = 10.1116_1.4971196 | yes |
| TMA | 0.002 to 0.005 | sum-frequency generation | measured | not checked | review Table V, ref. 237 | yes |
| TMA | 0.01 | Auger electron spectroscopy | measured | not checked | review Table V, ref. 235 | yes |
| TMA | 0.004 | slope at half thickness | calculated | s0 | 10.1039_d0cp03358h Table 2 | no |
| TMA | 0.0005 to 0.002 | slope at half thickness (Arts 2019) | cited | s0 | quoted in 10.1039_d0cp03358h Table 2 and 10.1016_j.sse.2022.108584 Table 2 | no |
| TMA | 0.0075 | diffusion with evaporation flux, fitted by hand | fit | s0 | 10.1016_j.sse.2022.108584 Table 2 | no |
| TMA | 0.012 | diffusion-reaction model | simulation input | s0 | 10.1039_d0cp03358h Fig. 10 | no |
| TMA | 0.01 | diffusion-reaction model, baseline | simulation input | s0 | 10.1039_d1cp04758b Table 1 | no |
| TMA | 0.0008 to 0.002 | literature range | cited | not stated | quoted in 10.1116_6.0001094 | no |
| H2O | 0.0003 | slope at half thickness, one sample | calculated | s0 | 10.1039_d0cp03358h Table 2 | no |
| H2O | 5e-05 to 0.00019 | diffusion with evaporation flux, 150 to 310 °C | fit | s0 | 10.1016_j.sse.2022.108584 Table 1 | no |
| O radical (TMA/O2* process) | 0.172 to 0.316 | Markov chain model, recombination held fixed | fit | s0 | 10.1116_6.0001094 Sec. III D | no |
| TEMAZ | 0.0002 | diffusion model in a porous body | fit | s0 | 10.1116_1.4892385 Fig. 5 | no |
| TMA | 0.01 | one-dimensional Monte Carlo in a fibre plug, 75 °C; picked by comparing simulations | fit | s0 | 10.1016_j.surfcoat.2012.02.038 Sec. 4.2 | no |
| TMA | 0.1 | Monte Carlo of a macro hole | simulation input | s0 | 10.1149_1.3301664 Fig. 6b | no |
| H2O | 0.05 | Monte Carlo of a macro hole | simulation input | s0 | 10.1149_1.3301664 Fig. 9 | no |
| TDMAT (with O3) | 0.015 to 0.025 | Monte Carlo of a hole, four thickness points, 180 °C | fit | s0 | review Table V, ref. 178 = 10.1016_j.apsusc.2009.02.055 | yes |
| TEMAHf (with O3) | 0.031 to 0.56 | Monte Carlo of a hole, 180 to 270 °C; activation energy 0.62 eV | fit | s0 | review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025 | yes |
| Cp*Ti(OMe)3 (with O3) | 0.006 to 0.018 | Monte Carlo of a hole, 270 °C, best value 0.01 | fit | s0 | review Table V, ref. 180 = 10.1016_j.apsusc.2010.01.025 | yes |
| TTIP (O2 plasma process) | 0.04 to 0.1 | ballistic model with re-emission, 125 to 225 °C | fit | s0 | review Table V, ref. 204 = 10.1149_1.2789802 | yes |
| BDEAS (with O3) | 3e-05 to 5e-05 | Monte Carlo model of a cavity, 300 °C | fit | s0 | review Table V, ref. 128 = 10.1116_1.4971196 | yes |
| DEZ | 0.007 | Monte Carlo of a pore; origin of the value not found | simulation input | s | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| SiCl4 | 1e-08 | quoted from another paper | cited | s | review Table V, ref. 65 = 10.1021_cm0303080 | yes |
| Hf(NMe2)4 | 0.07 to 1 | microbalance, a lower limit of 0.07 | cited | s | 10.1002_cvde.200390005 Sec. 3.1 | no |

What the new sources changed. Seven Table V sources are now read (refs 65, 67, 128, 178, 180, 200, 204; 11 rows). For TMA, the two ends of the non-DFT range are not results: 0.001 (ref. 65) is quoted from an earlier paper and 0.1 (ref. 67) is a chosen input. The fitted TMA values are 0.0005 to 0.0075 from lateral channels (after 2019), 0.009 to 0.02 from a cavity (ref. 128), 0.026 for the plasma process in holes (ref. 200) and 0.01 in a fibre plug at 75 °C. The hole-based fits of refs 178 and 180 rest on four or five thickness points each.

#### f. Censoring

| Table | complete (lower bound) | PD50% (measured) | conformal (no number) | blank or other |
| --- | --- | --- | --- | --- |
| II | 40 | 12 | 7 | 12 |
| III | 12 | 5 | 1 | 6 |
| IV | 35 | 3 | 0 | 7 |

In the blank column, 9 rows have a coated value below the structure value without the mark: BN 20 of 10000 (ref. 149); WN 210 of 1000 (ref. 85); Ru 100 of 166 (ref. 159); Pt 94 of 200 (ref. 172); Pt 50 of 200 (ref. 173); Pt 30 of 90 (ref. 173); V2O5 44 of 185 (ref. 159); Pt 50 of 120 (ref. 196); Ag 5 of 30 (ref. 198). 3 rows carry the mark with equal values: Ru 20 (ref. 160); TiO2 20 (ref. 178); Al2O3 15 (ref. 202).

#### g. Profiles: the references marked D

| Ref. | DOI | Films (table) | Year | PDF | Open access |
| --- | --- | --- | --- | --- | --- |
| 65 | 10.1021/cm0303080 | ZnO (II) | 2003 | have it | closed |
| 67 | 10.1149/1.3072694 | Al2O3 (II) | 2009 | have it | bronze |
| 69 | 10.1016/j.surfcoat.2012.02.038 | Al2O3 (II); Al2O3 (IV) | 2012 | have it | closed |
| 70 | 10.1149/1.3301664 | Al2O3 (IV); AlN (IV) | 2010 | have it | bronze |
| 77 | 10.1063/1.5028178 | Al2O3 (II); TiO2 (II) | 2018 | have it | green |
| 86 | 10.1116/1.4903941 | Al2O3 (II); TiO2 (II) | 2015 | have it | closed |
| 87 | 10.1021/acs.langmuir.6b03007 | Ir (II); Ir (III); IrO2 (III) | 2016 | to collect | closed |
| 94 | 10.1039/C4TC01961J | Ru (II) | 2015 | to collect | closed |
| 100 | 10.3762/bjnano.5.25 | TiO2 (II) | 2014 | have it | diamond |
| 107 | 10.1149/1.1836500 | SnOx (II) | 1996 | to collect | closed |
| 166 | 10.1063/1.2245216 | W (II) | 2006 | to collect | closed |
| 171 | 10.1116/1.4904398 | Pt (II) | 2015 | to collect | closed |
| 178 | 10.1016/j.apsusc.2009.02.055 | TiO2 (III) | 2009 | have it | closed |
| 180 | 10.1016/j.apsusc.2010.01.025 | HfO2 (III); TiO2 (III) | 2010 | have it | closed |
| 181 | 10.1021/jp110203x | Fe2O3 (III) | 2011 | to collect | closed |
| 184 | 10.1002/cvde.201006891 | Co3O4 (III) | 2011 | to collect | closed |
| 187 | 10.1116/1.4937728 | ZnO (III) | 2016 | to collect | closed |
| 195 | 10.1021/jp403455a | Pt (III) | 2013 | to collect | closed |
| 203 | 10.7567/JJAP.57.06JB03 | SiO2 (IV) | 2018 | to collect | bronze |
| 204 | 10.1149/1.2789802 | TiO2 (IV) | 2007 | have it | bronze |
| 228 | 10.1063/1.4972120 | Pt (IV) | 2017 | have it | green |

### Values read from the papers obtained by hand on 2026-10-13

Every value used above from those papers, with where it was read, whether the ingest checks now cover that unit, and whether it was compared with the page image (`cremers_values_hand_obtained.csv`). 19 are covered by the body or table check without a flag, 13 are figure values or values in a flagged table that were compared with the page image, 0 are neither. Two readings changed on that comparison (last column).

| Paper | Value as used | Where read | Check now | Compared with page image | Correction |
| --- | --- | --- | --- | --- | --- |
| 10.1002_cvde.200390005 | holes 0.17 x 0.30 um, 7.3 um deep, aspect ratio 36 (43 after coating) | body | body check: covered, no flag | no |  |
| 10.1002_cvde.200390005 | 150 °C; minimum exposure 9 × 10^3 L; 30 × 10^3 L for full coverage | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | pores 65 nm x 50 um and 19 nm x 92 um; 177 °C | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | TMA at 0.15 Torr; exposure times 1, 3, 10, 30 s | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | DEZ at 0.068 Torr; 5 Torr for 120 s in the quasi-static run | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | both faces directly exposed; pores entered from both ends | body | body check: covered, no flag | no |  |
| 10.1021_cm0303080 | middle of the membrane uncoated at 1 s, coated at 3 s | figure 3 | not checked (figure) | yes |  |
| 10.1021_cm0303080 | sticking 1e-3 for TMA (quoted) and 7e-3 for DEZ | body | body check: covered, no flag | no |  |
| 10.1149_1.3072694 | TMA about 0.3 Pa, 4 s, 200 °C, 150 cycles; s0 = 0.1 chosen | body | body check: covered, no flag | no |  |
| 10.1149_1.3072694 | half thickness: aspect ratio 50 at about 19 mm, 100 at about 10.7 mm | figure 5 | not checked (figure) | yes | corrected from 49 and 55 to 47 and 53 |
| 10.1016_j.surfcoat.2012.02.038 | TMA 0.08 Pa, 75 °C, 500 cycles; S0 = 0.01 | body | body check: covered, no flag | no |  |
| 10.1016_j.surfcoat.2012.02.038 | Table 2 parameters (0.08 Pa, 8 s, S0 0.01) | table | table check: ok | no |  |
| 10.1016_j.surfcoat.2012.02.038 | half values: thermal 2, 8, 30 s at about 15, 18, 27.5 mm; plasma at about 2.8 mm | figures 5, 10 | not checked (figure) | yes |  |
| 10.1149_1.3301664 | spacers 3.9, 1.3, 0.5 mm; TMA about 0.2 Pa, reactant 0.3 Pa; 9 s; 200 °C | body | body check: covered, no flag | no |  |
| 10.1149_1.3301664 | sticking inputs 0.1 (TMA, at 0.12 Pa) and 5% (water) | body | body check: covered, no flag | no |  |
| 10.1149_1.3301664 | aspect ratio 22: thermal complete, plasma half at about 12.5 mm (about 14) | figure 2 | not checked (figure) | yes |  |
| 10.1116_1.4903941 | gap 500 nm; film to 65 um; aspect ratio 130 at half the entrance value (TiO2) | body | body check: covered, no flag | no |  |
| 10.1116_1.4903941 | Al2O3 half thickness near 70 um | figure 5a | not checked (figure) | yes |  |
| 10.1116_1.4971196 | TMA 0.02 (0.009 to 0.02); BDEAS 3e-5 (3 to 5e-5); 200 and 300 °C | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2009.02.055 | holes 130 nm x 2 um, written as AR = 20; SC 0.02 ± 0.005; 180 °C | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2009.02.055 | profile never below 70% of its top value | figure 3 | not checked (figure) | yes |  |
| 10.1016_j.apsusc.2010.01.025 | SC 0.032, 0.15, 0.56 at 180, 230, 270 °C; Cp*Ti(OMe)3 0.006 to 0.018 | body | body check: covered, no flag | no |  |
| 10.1016_j.apsusc.2010.01.025 | HfO2 half thickness near 1250 nm at 180 °C | figure 1a | not checked (figure) | yes |  |
| 10.1063_1.2714685 | holes 0.3 um, aspect ratio 10; TMA 0.01 Torr; 225 °C; S(0) = 0.026 | body | body check: covered, no flag | no |  |
| 10.1149_1.2789802 | holes 0.15 um, aspect ratio 8.7; step coverage 52% at 500 cycles | body | body check: flagged (not checkable) | yes | none: compared with the page image (p. H1010 and the conclusion on p. H1013); the same values stand in the abstract and conclusion |
| 10.1149_1.2789802 | S(0) 0.1 and 0.052; flux 3.282e20 m-2 s-1 | table | table check: flag | yes |  |
| 10.1063_1.4972120 | trench aspect ratio up to 34; conformality 92 ± 8% | table | table check: ok | no |  |
| 10.1063_1.4972120 | O2 plasma 7.5 mTorr; r of O on Pt 0.01 (quoted) | body | body check: covered, no flag | no |  |
| 10.1149_1.3491381 | r of O on silica 0.0002, alumina 0.0021 (a literature table) | table | table check: flag | yes |  |
| 10.1021_acs.jpcc.1c01505 | r of SiO2 about 1e-4 to 3e-5 (temperature) and 2.5e-4 to 2e-5 (pressure); TiO2 about 4e-5, below 1e-5 at 240 °C | figure 5 | not checked (figure) | yes | corrected: upper pressure value from 2e-4 to 2.5e-4 |
| 10.1021_acs.jpcc.1c01505 | half-thickness depths over cavity height | figures 2-4 | not checked (figure) | yes |  |
| 10.1016_j.cattod.2003.11.022 | out of scope, cited source: γ of O on Al2O3 9.7e-3 (300 K) to 61e-3 (773 K), TiO2 14e-3 to 31e-3, SiC/SiO2 4e-3 to 9.3e-3 | table | table check: flag | yes |  |

### Ideas

#### 1. One process across several test structures
- **Verdict: doable partly.**
- Claim: Sec. VII says a benchmark across test structures would be useful. **true** (outlook, p. 021302-30).
- Claim: Sec. IV A: TMA/H2O coated EAR from 5 to 1750. **true** (p. 021302-15).
- Claim: Table II has 12 TMA/H2O rows, 6 with an exposure. **true** (Table II).
- Claim: the record row (AAO, 1750) has no exposure. **true** (Table II, ref. 96).
- Claim: 1 Pa·s is about 7500 L. **true** (but the review prints it the wrong way round, see 3b).
- Claim: Fig. 17 shows Monte Carlo curves for the exposure needed. **true** (caption of Fig. 17; the a² scaling itself was not checked).
- Needs exposure for each row. Have: 6 of 12 in the review; three of those sources are now read (refs 65, 67, 69) and confirm the printed exposures. With them the square law of ref. 62 can be tested for TMA on two sources: it matches ref. 67 and overestimates the need for ref. 65 by about 1.2 to 3.5 times (3a). The ref. 86 source is read too and gives no partial pressure, so its blank cannot be filled; ref. 77 gives a fitted, not measured, pressure. Missing: refs 134, 93, 96, 138 (no PDF). Joins Case 1, Case 8 and candidate A1.

#### 2. Automatic EAR conversion
- **Verdict: doable partly.**
- Claim: formulas for hole, trench, elongated hole; pillars from Monte Carlo. **true** (Sec. II G).
- Claim: Werbrouck 2021 states AR 20 and EAR 10. **true** (its Sec. II D).
- Needs L, w and the structure type from each source. Have: 18 checks; 16 agree. Three things a transform would have caught: one membrane listed as 770 and as 700, one hole type listed as 20 and as 15.3, and pores open at both ends counted at full length. Missing: the sources of the other rows. Joins N9 and Case 8.

#### 3. Continuing the tables after 2019
- **Verdict: doable now.**
- Claim: Mo trench 100/95/90%. **true** (10.1116_6.0002804 Fig. 9a).
- Claim: WCx step coverage about 80%. **true** (10.1021_acs.chemmater.6c00816 Fig. 4).
- Claim: AlN with Kr, step coverage 1.6. **true** (10.1021_acs.jpclett.4c03545 Fig. 2).
- Claim: PD50% in three plasma LHAR papers. **true** (Fig. 2A; body text; Table 1).
- new_rows.csv holds 21 draft rows from 16 papers, each with its source (two added from 10.1021_acs.jpcc.1c01505). Exposure is blank in all but one. Three things do not fit the review's columns: a step coverage above 1, a profile thicker at the bottom, and atmospheric plasma. Adds a new case (a living table); uses Case 7 for the values written on images.

#### 4. Recombination probability against coated EAR
- **Verdict: doable partly.**
- Claim: the review explains the lower EAR of metals only in words; largest 30 for oxides, 17 for metals. **true** (p. 021302-19).
- Claim: O on alumina: 0.0021 and 0.0097. **true** (Table VII, refs 250 and 251).
- Have: 15 Table IV rows with a fair surface match, 13 of them lower bounds. The order of the largest values follows r (silica, then alumina and titania, then copper and nickel), but lower bounds capped by the structure cannot test it. Missing: profiles for these rows. Two matched rows fail the source check (ref. 69: about 0.3, not 0.75; ref. 70: exposure). The Table VII values for alumina and titania are now traced to their source (ref. 251): sintered ceramics at 300 K in a 110 Pa air plasma, where r rises with temperature; on ALD films in lateral channels r is 200 to 1000 times lower for titania and falls with temperature and pressure. So Table VII values cannot stand in for the growth surface. Joins Case 2 and Case 8.

#### 5. Same film, different oxidant
- **Verdict: doable partly.**
- Claim: Al2O3 largest coated EAR about 1750, 20, 30 for thermal, ozone, plasma. **wrong in part** (1750 is right; 20 is in the running text only, the table cell says 'Ref. 175'; 30 is SiO2 and HfO2, the largest plasma Al2O3 value is 15 (PD50%) or 13.5).
- Claim: TiO2, HfO2, Ru, Pt, ZnO also have pairs. **true** (plus V2O5, Fe2O3, Ir, SiO2, AlN, TiN, TaN).
- Claim: the review compares maxima without matching. **true** (Sec. IV B).
- Have: 10 pairs from the tables with the same structure type, none matched in exposure, and now two matched pairs taken from the sources (refs 69 and 70): at equal exposure, structure and temperature the plasma process coats about 6 times and about 1.6 times less deep than the thermal one. Missing: exposure in every ozone row but one. Joins Case 8.

#### 6. Why sticking probabilities scatter
- **Verdict: doable now.**
- Claim: TMA has 8 values from 0.001 to 0.1, DFT 0.1 to 0.9. **true** (Table V).
- Claim: the review only suggests the methods differ. **true** (p. 021302-16).
- Claim: Ylilammi's 0.00572 is an initial sticking coefficient. **true** (source: c multiplies (1 − θ); the review's Sec. VI B 3 calls it initial, its Table V header says sticking probability).
- Have: the 27 Table V rows and 14 values outside the table, each with model and data kind. Of the 16 Table V rows now checked in a source, 2 are not results of the method named: the TMA value of ref. 65 is quoted from an earlier paper and that of ref. 67 is a chosen input. With those two removed and DFT set aside, the fitted TMA values run from 0.0005 to 0.026. Every checked value is an initial (bare-surface) one. Joins Case 4, Case 8 and N1.

#### 7. Many coated EAR values are lower bounds
- **Verdict: doable now.**
- Claim: coated EAR equals the structure EAR when fully coated, PD50% otherwise. **true** (captions of Tables II to IV).
- Claim: '75 (D)' is a measured value. **true** (printed as 75* (D)).
- Counts are in 3f. The rule is not applied evenly: 9 rows have a coated value below the structure value without the PD50% mark, and 3 carry the mark although the two values are equal. One marked row is contradicted by its source (ref. 178: the profile never falls to one half). Supports a basis qualifier on coated_aspect_ratio; joins N3 and Case 8.

#### 8. The (D) mark as a collection list
- **Verdict: doable partly.**
- Claim: (D) means a thickness profile was reported. **true** (captions).
- Claim: Sec. VI B 3: dense points in the slope region are needed (Fig. 22). **true** (p. 021302-31).
- Have: 21 references marked D, 11 with a PDF. The point count now covers 43 measured profile groups (21 new, profiles.csv). The rest of the list is in wanted_pdfs.csv.

#### 9. Growth type classification
- **Verdict: doable partly.**
- Claim: three growth types told apart by profile shape. **true** (Sec. II F, Fig. 4).
- Shape separates diffusion-limited profiles (plateau and front) well. It cannot separate reaction- from recombination-limited growth, or either from channel closing or reversible adsorption; those need a time or dose series. The new papers add three more cases where shape misleads: a plasma profile with a sharp front (CoOx), plasma profiles shaped by a thermal side reaction (Al2O3), and a precursor-limited plasma profile (TiO2 at the highest temperature). Ref. 66, now read, is where the third type was introduced; its regime diagram needs r and the aspect ratio, not the shape. Joins N7.

#### Idea 8, tried: calibration fitness of the measured profiles

Threshold used: at least 5 points between 80% and 20% of the reference level, a plateau or a stated reference to normalize by, and a probe smaller than the front. Reason: a front is described by two numbers, its position and its slope; with fewer than five points there are fewer than three left to judge the fit, and the review's Fig. 22 shows that sparse points in the slope region cannot tell sticking values apart. Counts are by eye.

Of 43 series groups: 11 fit, 10 marginal, 22 not fit.

| Paper | Fig. | Series | Points | Points 80 to 20% | Plateau | Fit for a sticking value | Remark |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 6 | Al2O3, 500 cycles | about 85 | about 8 | yes | yes |  |
| 10.1063_1.5028178 | 7 | TiO2, 1000 cycles | about 70 | about 35 | no | no: no plateau | looks reaction-limited, but the authors' fit gives a high sticking coefficient (0.1) with weak reversible adsorption |
| 10.1039_d0cp03358h | 7 | spot 5 µm | about 90 | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 7 | spot 25 and 50 µm | about 90 each | 15 to 25 | yes | no: spot wider than the front | more points, but the slope is the instrument's |
| 10.1039_d0cp03358h | 8a, 8b | repeats and four runs | about 90 each | 10 to 15 | yes | yes | fronts of nominally equal runs differ by tens of µm |
| 10.1039_d0cp03358h | 9a-c | H 500 nm | about 90 | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 9a-c | H 100 nm | about 30 in the channel | about 8 | no | no: no plateau, channel closing | the shape of a reaction-limited profile, caused here by film growth narrowing a 100 nm channel |
| 10.1039_d0cp03358h | 9a-c | H 2000 nm | about 90 | about 10, curve cut at one third | yes | marginal | gas-phase collisions matter at this height |
| 10.1039_d0cp03358h | 9d-f | 250, 500, 1000 cycles | about 90 each | 10 to 15 | yes | yes |  |
| 10.1039_d0cp03358h | 11a-b | pulse and purge series | about 90 each | 10 to 25 | yes | yes |  |
| 10.1116_6.0001094 | 11 | six power and pulse pairs | 10 each | 3 to 6; most never reach 20% | partly | no | the authors state diffusion-limited conditions; in a structure of aspect ratio 20 the three types look alike |
| 10.1116_6.0001094 | 12 | five pressures | 10 each | 2 to 5; none reaches 20% | partly | no | same |
| 10.1021_acs.jpcc.9b08176 | 2B | SiO2, four plasma times | 40 to 90 each | about 10 | yes | yes, for a recombination probability | the time series, not one profile, is what identifies the type |
| 10.1021_acs.jpcc.9b08176 | 2B | TiO2, Al2O3, HfO2 | 10 to 80 each | 5 to 8 | no | marginal | from one profile alone this cannot be told from reaction-limited growth |
| 10.1063_5.0168768 | 2a | SiO2, three plasma times | about 35 each | 3 to 4 | yes, short | no | type stated by the authors |
| 10.1063_5.0168768 | 2b | TiO2, three plasma times | about 35 each | 6 to 8 | no | marginal |  |
| 10.1021_acs.jpcc.5c06502 | 10b | samples A to D | continuous traces | many, from image grey levels | no | no: thickness scale is indirect | type stated by the authors from the comparison of four samples |
| 10.1038_s41467-022-35428-6 | 4b | four inhibitor treatments | about 12 each | 0: no front | not applicable | no | inhibitor-controlled growth is outside the scheme |
| 10.1116_1.4892385 | 5 | ZrO2, 1135 cycles | 17 | about 9, scattered | no | marginal |  |
| 10.3762_bjnano.5.25 | 6b | 400 cycles | 13 | about 6 | yes | marginal | the slope reflects exposure not scaled as tubes thicken |
| 10.3762_bjnano.5.25 | 6b | 200 cycles | 12 | 2 to 3 | yes | no |  |
| 10.3762_bjnano.5.25 | 6c | three series | 8 to 10 each | 3 to 5 | yes | no |  |
| 10.1149_1.3072694 | 5 | aspect ratio 100 | about 20 | 3 to 4 | yes | marginal | the authors decline to fit: the result depends on the pressure to 0.01 Pa |
| 10.1149_1.3072694 | 5 | aspect ratio 33 and 50 | about 20 each | 0 to 2 | yes | no: coated to the end |  |
| 10.1149_1.3301664 | 2a, 6a | thermal, aspect ratio 50 | about 30 | about 8 | yes, with a slow early decline | marginal | the authors suspect a CVD-like part in the early decline |
| 10.1149_1.3301664 | 2b, 3, 4b, 5a, 9a | plasma Al2O3, about 20 profiles | about 30 each | 5 to 15 | partly | no: two reactions overlap | the authors attribute the tail to water formed in the plasma step: recombination-limited growth with a thermal side reaction |
| 10.1149_1.3301664 | 5b | plasma AlN, three plasma times | about 30 each | 5 to 8 | no | no | the film composition changes with depth |
| 10.1149_1.3301664 | 10 | plasma CoOx | about 30 | about 4 | yes, short | marginal | a plasma process with the shape of a diffusion-limited profile |
| 10.1016_j.surfcoat.2012.02.038 | 5, 7 | thermal, three pulse times, two densities | 5 to 8 each | 2 to 4 | partly | no | an X-ray signal with wide error bars; type stated by the authors |
| 10.1016_j.surfcoat.2012.02.038 | 10 | plasma | 9 | 3 | no | no | type from the comparison with the thermal run, not from the shape |
| 10.1116_1.4903941 | 5a | Al2O3, 300 °C | about 50 | about 10 | yes | yes | the tail below 30 nm is not reliable (stated) |
| 10.1116_1.4903941 | 5b | TiO2, 110 °C, three gaps | 30 to 45 each | 10 to 20 | no | no: no plateau | same behaviour as the TiO2 profile of 10.1063_1.5028178 |
| 10.1116_1.4971196 | 8, 9 | Al2O3, four access holes | about 100 each | 8 to 10 per edge | yes, with growth above the planar level near the hole | yes | the authors fit 0.02 (0.009 to 0.02); the reference level is chosen |
| 10.1116_1.4971196 | 11, 12 | SiO2, four access holes | about 100 each | the whole scan | no | yes, for a low value | the authors fit 3e-5; a low value is fixed by the overall shape |
| 10.1016_j.apsusc.2009.02.055 | 3 | TiO2, one sample | 4 | 0: never below 70% | one point | no: four points | the authors fit 0.02 ± 0.005 from these four points |
| 10.1016_j.apsusc.2010.01.025 | 1 | HfO2 at 180, 230, 270 °C | 4 to 5 each | 2 to 3 | one point | no: too few points | the authors fit 0.031, 0.15, 0.56; shape goes from reaction- to diffusion-limited |
| 10.1016_j.apsusc.2010.01.025 | 3 | TiO2, 270 °C | 5 | 0 | no | no | only a range, 0.006 to 0.018 |
| 10.1149_1.2789802 | 4 | TiO2, one hole | 7 values at three heights | about 3 | no | no | the model is fitted to top and bottom values against pulse time, not to this profile |
| 10.1063_1.4972120 | 5, 7 | Pt, four trenches; one trench by TEM | 6 each; 160 | 0: no front | yes, all of it | no: saturated | a fully coated structure carries no kinetic information |
| 10.1021_cm0303080 | 5a, 6a | ZnO, four exposure times, three pore sizes | about 25 each | 5 to 10 | yes, short | marginal | probe of 3 to 5 um against fronts of 5 to 10 um; type stated by the authors |
| 10.1021_cm0303080 | 7b | ZnO, aspect ratio 5000 | about 100 | 0: no front | yes | no: saturated |  |
| 10.1021_acs.jpcc.1c01505 | 2A, 4A | SiO2, four temperatures, five pressures | 50 to 100 each | about 10 | a slow decline, then a front | yes, for a recombination probability | type from the time series |
| 10.1021_acs.jpcc.1c01505 | 3A | TiO2, three temperatures | 50 to 100 each | 10 to 20 | no | marginal | at the highest temperature the precursor step limits the depth (stated), which the shape does not show |

#### Idea 9, tried: growth type by shape

Counts: diffusion-limited 18, cannot decide 10, recombination-limited 9, none of the three 3, reaction-limited 3.

| Paper | Fig. | Series | Type by shape | Feature used | Where shape alone cannot decide |
| --- | --- | --- | --- | --- | --- |
| 10.1063_1.5028178 | 6 | Al2O3, 500 cycles | diffusion-limited | flat, then a front of about 20 µm |  |
| 10.1063_1.5028178 | 7 | TiO2, 1000 cycles | cannot decide | falls from the entrance on | looks reaction-limited, but the authors' fit gives a high sticking coefficient (0.1) with weak reversible adsorption |
| 10.1039_d0cp03358h | 7 | spot 5 µm | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 7 | spot 25 and 50 µm | diffusion-limited | front smeared by the instrument | more points, but the slope is the instrument's |
| 10.1039_d0cp03358h | 8a, 8b | repeats and four runs | diffusion-limited | flat, then a sharp front | fronts of nominally equal runs differ by tens of µm |
| 10.1039_d0cp03358h | 9a-c | H 500 nm | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 9a-c | H 100 nm | cannot decide | falls from the entrance on | the shape of a reaction-limited profile, caused here by film growth narrowing a 100 nm channel |
| 10.1039_d0cp03358h | 9a-c | H 2000 nm | diffusion-limited | flat, then a front | gas-phase collisions matter at this height |
| 10.1039_d0cp03358h | 9d-f | 250, 500, 1000 cycles | diffusion-limited | flat, then a sharp front |  |
| 10.1039_d0cp03358h | 11a-b | pulse and purge series | diffusion-limited | flat, then a front; broader at 0.4 s |  |
| 10.1116_6.0001094 | 11 | six power and pulse pairs | cannot decide | gradual decline over the whole 20 mm | the authors state diffusion-limited conditions; in a structure of aspect ratio 20 the three types look alike |
| 10.1116_6.0001094 | 12 | five pressures | cannot decide | gradual decline | same |
| 10.1021_acs.jpcc.9b08176 | 2B | SiO2, four plasma times | recombination-limited | long shallow decline, then a front; depth grows with the logarithm of time | the time series, not one profile, is what identifies the type |
| 10.1021_acs.jpcc.9b08176 | 2B | TiO2, Al2O3, HfO2 | recombination-limited | decline from the entrance on | from one profile alone this cannot be told from reaction-limited growth |
| 10.1063_5.0168768 | 2a | SiO2, three plasma times | recombination-limited | front moves with the logarithm of time | type stated by the authors |
| 10.1063_5.0168768 | 2b | TiO2, three plasma times | recombination-limited | decline from the entrance, then a front |  |
| 10.1021_acs.jpcc.5c06502 | 10b | samples A to D | recombination-limited | depth set by plasma time, not precursor dose | type stated by the authors from the comparison of four samples |
| 10.1038_s41467-022-35428-6 | 4b | four inhibitor treatments | none of the three | thinner at the top than at the bottom | inhibitor-controlled growth is outside the scheme |
| 10.1116_1.4892385 | 5 | ZrO2, 1135 cycles | reaction-limited | decline from the surface on; fitted probability 2e-4 |  |
| 10.3762_bjnano.5.25 | 6b | 400 cycles | diffusion-limited | flat to 12 µm, then a slope | the slope reflects exposure not scaled as tubes thicken |
| 10.3762_bjnano.5.25 | 6b | 200 cycles | diffusion-limited | flat to 30 µm, then a drop |  |
| 10.3762_bjnano.5.25 | 6c | three series | diffusion-limited | flat, then a slope |  |
| 10.1149_1.3072694 | 5 | aspect ratio 100 | diffusion-limited | flat, then a front 2 mm wide | the authors decline to fit: the result depends on the pressure to 0.01 Pa |
| 10.1149_1.3072694 | 5 | aspect ratio 33 and 50 | diffusion-limited | no front inside the structure |  |
| 10.1149_1.3301664 | 2a, 6a | thermal, aspect ratio 50 | diffusion-limited | decline, then a front | the authors suspect a CVD-like part in the early decline |
| 10.1149_1.3301664 | 2b, 3, 4b, 5a, 9a | plasma Al2O3, about 20 profiles | cannot decide | gradual decline with a kink and a tail | the authors attribute the tail to water formed in the plasma step: recombination-limited growth with a thermal side reaction |
| 10.1149_1.3301664 | 5b | plasma AlN, three plasma times | recombination-limited | falls from the entrance on within 5 mm | the film composition changes with depth |
| 10.1149_1.3301664 | 10 | plasma CoOx | cannot decide | flat to 3 mm, then a sharp front | a plasma process with the shape of a diffusion-limited profile |
| 10.1016_j.surfcoat.2012.02.038 | 5, 7 | thermal, three pulse times, two densities | diffusion-limited | front moves in with pulse time | an X-ray signal with wide error bars; type stated by the authors |
| 10.1016_j.surfcoat.2012.02.038 | 10 | plasma | recombination-limited | falls from the entrance on, depth six times less than thermal | type from the comparison with the thermal run, not from the shape |
| 10.1116_1.4903941 | 5a | Al2O3, 300 °C | diffusion-limited | flat to 52 um, then a front | the tail below 30 nm is not reliable (stated) |
| 10.1116_1.4903941 | 5b | TiO2, 110 °C, three gaps | cannot decide | falls from the entrance on, in two slopes | same behaviour as the TiO2 profile of 10.1063_1.5028178 |
| 10.1116_1.4971196 | 8, 9 | Al2O3, four access holes | diffusion-limited | flat, then an edge about 100 um wide | the authors fit 0.02 (0.009 to 0.02); the reference level is chosen |
| 10.1116_1.4971196 | 11, 12 | SiO2, four access holes | reaction-limited | smooth decline over the whole cavity | the authors fit 3e-5; a low value is fixed by the overall shape |
| 10.1016_j.apsusc.2009.02.055 | 3 | TiO2, one sample | cannot decide | gentle decline | the authors fit 0.02 ± 0.005 from these four points |
| 10.1016_j.apsusc.2010.01.025 | 1 | HfO2 at 180, 230, 270 °C | cannot decide | front steepens with temperature | the authors fit 0.031, 0.15, 0.56; shape goes from reaction- to diffusion-limited |
| 10.1016_j.apsusc.2010.01.025 | 3 | TiO2, 270 °C | reaction-limited | nearly flat decline | only a range, 0.006 to 0.018 |
| 10.1149_1.2789802 | 4 | TiO2, one hole | cannot decide | thinner toward the bottom | the model is fitted to top and bottom values against pulse time, not to this profile |
| 10.1063_1.4972120 | 5, 7 | Pt, four trenches; one trench by TEM | none of the three | flat to the bottom | a fully coated structure carries no kinetic information |
| 10.1021_cm0303080 | 5a, 6a | ZnO, four exposure times, three pore sizes | diffusion-limited | front moves in with the square root of time | probe of 3 to 5 um against fronts of 5 to 10 um; type stated by the authors |
| 10.1021_cm0303080 | 7b | ZnO, aspect ratio 5000 | none of the three | coated through, with a slope across the membrane |  |
| 10.1021_acs.jpcc.1c01505 | 2A, 4A | SiO2, four temperatures, five pressures | recombination-limited | depth grows with the logarithm of plasma time | type from the time series |
| 10.1021_acs.jpcc.1c01505 | 3A | TiO2, three temperatures | recombination-limited | declines from the entrance on | at the highest temperature the precursor step limits the depth (stated), which the shape does not show |

## Cremers ideas: cross-paper comparisons the review suggests

Notes from reading Cremers et al., Appl. Phys. Rev. 6, 021302 (2019). The factual claims below (marked "Claim:") are not yet verified; check each against the review and the source papers.

### A. What Cremers wanted but could not do

#### 1. One process across several test structures (benchmark)
- In the outlook (Sec. VII) the authors say it would be useful to measure one process on different test structures and cross-compare. In Sec. IV A they note that the coated EAR of TMA/H2O ranges from 5 to 1750 depending on structure and conditions.
- Claim: of the 12 TMA/H2O rows in Table II, only 6 give an exposure. The record row (AAO, 1750:1) has none. The variable this comparison needs most is already missing at the review stage.
- What we can do: go back to the sources and fill the blanks, or confirm that the source does not state them; then put coated EAR against exposure and compare with Gordon's a² scaling (the Monte Carlo curves of Fig. 17).
- Units: the tables give exposure in 10³ L (1 Pa·s ≈ 7500 L). The conversion printed in Sec. II D looks garbled in the extracted text; check it on the page.

#### 2. Automatic EAR conversion and a check of the tables
- Cremers gives EAR formulas per structure (Sec. II G): circular or square hole L/w, trench L/(2w), elongated hole L(w+z)/(2wz), pillar arrays from Monte Carlo.
- The EAR values in Tables II–IV were converted by the authors. If the KB computes EAR from the source's L, w and structure type with a transform, it can reproduce and check the review's tables.
- Example: Werbrouck 2021 (10.1116/6.0001094) states AR 20 and EAR 10 for a trench, consistent with the trench formula.

#### 3. Continuing the tables after 2019 (living table)
- The review's tables end in early 2019. The 44 papers already hold candidate new rows:
  - Mo in a trench, top/side/bottom 100/95/90% (10.1116/6.0002804)
  - WCx in a trench, step coverage about 80% (10.1021/acs.chemmater.6c00816)
  - AlN with Kr co-flow, step coverage 1.6 (10.1021/acs.jpclett.4c03545)
  - PD50% of three plasma LHAR papers (10.1021/acs.jpcc.9b08176, 10.1063/5.0168768, 10.1021/acs.jpcc.5c06502)
- "The review's tables, updated automatically" is a candidate headline result for the perspective paper.

### B. What only shows when tables are joined

#### 4. Recombination probability against coated EAR (Table IV × Table VII)
- Claim: Cremers states only qualitatively that metal surfaces have a high r, so plasma ALD of metals reaches a lower coated EAR (largest 30 for oxides, 17 for metals).
- Attaching the r of the deposited material's surface (Table VII) to each process's coated EAR (Table IV) would test this quantitatively.
- Putting the r values the 44 papers obtain from LHAR slopes (case C2) beside the older Table VII values also compares measurement methods. Example: O on alumina is 0.0021 in one source and 0.0097 in another.

#### 5. Same film, different oxidant (Table II × III × IV)
- Some films appear with thermal, ozone and plasma processes. Claim: for Al2O3 the largest coated EAR is about 1750, 20 and 30 respectively. TiO2, HfO2, Ru, Pt and ZnO also have pairs.
- Only pairs with matching structure and exposure can show the effect of the process mode. The review compares maxima without matching.

#### 6. Why sticking probabilities scatter (Table V)
- Claim: TMA alone has 8 values from 0.001 to 0.1 (DFT 0.1–0.9), and Cremers only suggests the methods may differ.
- A definition issue is mixed in. Table V says "sticking probability", but, claim: Ylilammi's 0.00572 is an initial sticking coefficient s0. The review itself defines s and s0 separately.
- Tagging each value with method, model, data_kind and s/s0 may explain part of the spread. Adding post-2019 values (Yim 2020, sse.2022, the slope method of d1cp04758b) gives a literature prior for the warm start of the twin's parameter estimation (Case 2-2).

### C. About the nature of the data itself

#### 7. Many coated EAR values are lower bounds
- By the table headers' definition, coated EAR equals the structure's EAR when the structure was fully coated (including "Conformal"), and is PD50% only when coverage was incomplete. So "1750" means "at least 1750", while "75 (D)" is a measured value.
- Mixing the two on one plot is wrong. This supports a qualifier on coated_aspect_ratio such as {basis=complete (lower bound) | PD50%}. Another case of "comparable is not identical".

#### 8. The "(D)" mark is a collection priority list
- (D) means the paper reported a thickness profile. These are the papers we can digitize and use for model calibration.
- Cremers Sec. VI B 3: fixing s0 needs dense points in the slope region (Fig. 22). Counting the points in the slope region of each profile gives a score for whether it is fit for calibration, a direct input to the twin.
- This list decides which of the 283 papers to request through the library first.

#### 9. Growth type classification (Fig. 4)
- The concept of telling diffusion-, reaction- and recombination-limited growth apart by profile shape (Sec. II F). Together with case N7 (parameter sensitivity), it gives a case that classifies "which type is this process" across the literature.
