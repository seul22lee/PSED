# PSED v2 Plan

Sep 30, 2026 · @Seul

## Purpose and scope

PSED v2 is a rebuild of the literature-to-knowledge pipeline for ALD papers, starting from the ontology, with a gold set built first. The pipeline output uses the same table format as the gold set, so verification is one automatic score and nothing else.

v1 (`psed_v1`, tag `v1-final`, commit `a06a714`) works but is too complex: 13 stages, about 200 ontology classes, and two separate places that decide what counts as an experiment. It has no ground truth for whether its output is correct.

**Repository:** [github.com/seul22lee/PSED](https://github.com/seul22lee/PSED)

- v1 code: `psed_v1/`, frozen at tag `v1-final` (`a06a714`).
- v2 code: `psed_v2/` on branch `v2`.

**In scope:** corpus definition and PDF acquisition, gold set, minimal ontology, four-stage pipeline, corpus growth from 5 to about 1,100 ALD papers, one comparison view, connection to the HAR channel twin.

**Out of scope for now:** control, agentic orchestration, flat-surface and reactor-scale models, automatic intake of newly published papers. These come after Phase 7.

The schedule is not a constraint. The work is done properly, in order.

## Principles

1. **The competency questions cap the scope.** A feature that answers none of them is not built. A new need means adding a question first.
2. **One data format.** Six tables, identical for the gold set and the pipeline output.
3. **One place decides experiment identity.** A paper is not one experiment and a figure is not one experiment. The `resolve` stage is the only place this is judged.
4. **LLM calls are made once per paper and cached.** Everything after extraction is deterministic code.
5. **An unknown quantity is not an error.** It keeps its original label and unit and is listed for later.
6. **Verification is the gold score only.** No count-pinning tests, no re-audits, no manual inspection of every output.
7. **Simple is best.** The simplest thing that answers the competency questions wins.

## Competency questions

These 11 questions are the upper bound of what v2 must answer.

**Experiment identity**

1. How many independent experiments (samples or deposition runs) does this paper contain, and what are the conditions of each?
2. Which experiment does this curve come from? Is each point a separate experiment, or is the curve one experiment along a time or space axis?
3. Which experiment, and which location on the sample, does this SEM/TEM image show?
4. Is this curve a measurement, a fit, a simulation, or data cited from another paper?

**Cross-paper comparison**

5. Can GPC versus deposition temperature be overlaid across papers for the same chemistry (for example TMA/H₂O)?
6. Can saturation curves (GPC versus pulse time, GPC versus purge time) be compared across papers?
7. Can HAR penetration profiles be overlaid after normalizing the depth axis to x/H?
8. What are the condition differences between two experiments, and where does each value come from?

**Twin**

9. For a given material and geometry, which twin inputs are available from the literature and which are not?
10. What effective sticking coefficient does a fit to a measured profile give, and does it agree with the value the paper reports?
11. How well does a coefficient fitted on one paper predict a profile from another paper?

## Data model

Six tables hold everything. The gold set and the pipeline both write these tables, so scoring is a comparison of two tables of the same shape.

| Table | One row is | Main columns |
| --- | --- | --- |
| papers | a paper | DOI, title, corpus tier, status, reason |
| panels | one panel of a figure | figure number, panel, type (plot, image, schematic, table) |
| experiments | one experiment | experiment ID, kind (sample, in-situ run, simulation, cited), evidence sentence |
| series | one series in a panel | x and y quantity and unit, data kind, structure, linked experiment IDs |
| conditions | one condition of an experiment | quantity, value, unit, source location, evidence sentence, status |
| points | one data point | series, x, y |

**Series structure** takes one of four values: spatial profile of one experiment, time trace of one experiment, one experiment per point, image of part of one experiment. For "one experiment per point" the row maps each x value to an experiment ID. For an image it records the location on the sample.

**Data kind** takes one of four values: measured, fit, simulation, cited.

**Condition source** is caption, methods section, table, or body text. **Condition status** is stated, approximated, or inferred.

**The number of experiments** is the row count of the `experiments` table. This replaces the three different counts v1 produced (1,127 in the knowledge graph, 1,044 resolved entities, 1,231 semantic cases).

In the gold set, every row carries two extra columns: the LLM draft value and the expert verdict (accept, edit, reject, add).

## Pipeline

A corpus stage plus four processing stages replace the 13 in v1.

| Stage | What it does | How |
| --- | --- | --- |
| 0. corpus | Decide which papers are in, get their PDFs | Manifest CSV + OpenAlex lookup + downloads; see Corpus management |
| ingest | PDF to body text, captions, tables, panel crops | Docling; v1 results reused |
| extract | Per panel: series, points, candidate conditions with evidence sentences | LLM, cached |
| resolve | Reads the whole paper, builds the experiment list, links series and conditions to experiments | One LLM call per paper plus deterministic rules; the only judgment point |
| normalize | Maps labels to the ontology, converts units, applies normalizing transforms | Deterministic |

The comparison view and the twin read the tables that `normalize` writes. They add no new data layer.

Two lessons from v1 are fixed in the design. Image panels are extracted as panels in their own right, so a figure that mixes a plot and a TEM image no longer loses the image. Points interpolated along a drawn line are never turned into separate experiments.

## Ontology

The ontology is one flat file, written new for v2.

- **Quantities:** one row each with id, name, aliases, dimension, canonical unit, role (coordinate, condition, output).
- **Chemical species and materials:** id, aliases, formula.
- **Transforms:** unit conversion, depth to x/H, thickness to normalized thickness. Each names the context it needs (for example feature height H).
- **Fixed vocabularies:** panel type, data kind, series structure, condition source, condition status.

**v0 source.** v0 contains the quantities that the competency questions need and that appear in the five gold papers. The expected size is 20 to 30 quantities.

**Growth rule.** Every corpus run lists unknown labels ranked by how many papers use them. A label is added when it appears in two or more papers or a competency question needs it. An alias is added directly. A new quantity or a new transform needs expert approval.

**Generality across ALD.** Papers outside HAR conformality (process development, characterization-heavy work) are handled by the growth rule and by principle 5. Spectra such as XPS and XRD stay in their native form unless a competency question asks for them.

**External review.** The Parsons group reviews the ontology twice: when v0 is fixed, and after the corpus expansion in Phase 7.

**Naming.** Where the TIB/TU Eindhoven ALD schema or QUDT already has a field name or unit, v2 uses the same one.

## Gold set

The gold set is built before the pipeline. An LLM drafts it from the PDF and the domain expert checks every row against the paper.

**Procedure**

1. Pilot on one paper (Ylilammi 2018). Fill the six tables, find missing columns and unclear categories, and fix the format once.
2. Draft the other four papers with an LLM. The draft model and prompt differ from the ones the pipeline uses (v1 used Gemini), so the gold set does not inherit the pipeline's errors.
3. The expert marks each row accept, edit, reject, or add. The edit rate is recorded and is a reportable number.
4. Data points are not drafted by an LLM. Two or three curves per paper are digitized by hand with a tool such as WebPlotDigitizer.
5. The expert's checking time per paper is recorded, to estimate the cost of later gold papers.

**First five papers (development set)**

| Paper | Why it is included |
| --- | --- |
| Ylilammi 2018 (`10.1063_1.5028178`) | Measured profile and fit in one panel |
| Yim 2020 (`10.1039_d0cp03358h`) | Many profiles plus a sample table |
| `10.1002_pssa.201532305` | In-situ continuous trace; v1 split one figure into 212 cases |
| `10.1149_2.067203jes` | GPC saturation sweeps; v1 classified them as continuous traces |
| `10.1039_c5tc03561a` | TEM close-ups and an XPS depth profile in the same figures |

**External material that can be reused.** The TIB/TU Eindhoven expert spreadsheet (one row per sample with conditions, results, and evidence sentence) is the model for the format. The ALD-E-ImageMiner benchmark has 1,411 panel data tables that can serve as digitization ground truth.

## Corpus management

**Criterion.** A paper is in the corpus if it comes from one of three sources:

- Popov et al., *J. Vac. Sci. Technol. A* 43, 030801 (2025): a first reference in Table I (new thermal ALD processes published 2010–2023, from the AtomicLimits ALD database).
- Cremers et al., *Appl. Phys. Rev.* 6, 021302 (2019): any reference (table footnotes excluded).
- Papers citing Cremers 2019 (OpenAlex, forward citation) whose title or abstract mentions conformality keywords (conformal, conformality, aspect ratio, high-aspect-ratio, step coverage, trench, LHAR, PillarHall, penetration depth, saturation profile) and ALD ("atomic layer" or "ALD"). This covers conformality work published after 2019.

Papers added by hand are marked `extra`.

**Two axes.** The corpus is built on two axes. Popov 2025 covers the process-chemistry axis: which precursors and reactants deposit which material, for thermal ALD. Cremers 2019 and the papers citing it add the geometry axis: conformality in high-aspect-ratio structures (trenches, holes, AAO, LHAR). Plasma ALD papers entered through the geometry axis and are accepted as they are. Plasma coverage is therefore partial (conformality-related only) and is not claimed as general plasma ALD coverage. The ontology must include geometry concepts (structure type, aspect ratio, feature dimensions, penetration depth, thickness profile) and a minimal process-mode set (thermal, ozone, plasma; plasma configuration; radical recombination).

**Size.** 1,124 rows, of which 22 are excluded (not ALD), leaving 1,102 papers. By source (a paper can have several): Popov 699, Cremers 292, Cremers-citing 143, extra 1. 54 papers have no DOI and are resolved by hand. The list is `psed_v2/corpus/manifest.csv`; `psed_v2/corpus/report.csv` is generated from it.

**PDF acquisition.**

1. Look up every DOI in OpenAlex: OA status, license, PDF URL.
2. Download open PDFs directly.
3. Get the rest through Northwestern access (publisher TDM API where available, otherwise Zotero "Find Available PDF").

OA status is a column, not a filter. All included papers are read and extracted. Only extracted data (conditions, digitized points, provenance) is published; PDFs, full text, and figure crops are redistributed only for CC-licensed papers. PDFs (`psed_v2/corpus/raw/`), `document.md`, and figure crops are never committed to git.

**Tiers.**

| Tier | Papers | Gold | Purpose |
| --- | --- | --- | --- |
| Dev | 5 | Full | Pipeline development |
| Held-out | 3 | Full | Scored only at milestones |
| Sample | 80, the Table I papers whose PDFs were collected first | None | Generality check; ontology growth |
| Full | about 1,100 | None | Final corpus |

Dev and Held-out papers may come from outside the two reviews; such papers are added as `extra`. The Sample is not random: it leans toward open-access papers.

**Held-out selection.** Different in type from the Dev set: two Popov process-development papers of different material classes, and one paper from the TIB/TU Eindhoven expert spreadsheet.

**Expansion condition.** Move to the next tier when the Dev score passes its target and the Held-out score does not drop sharply below it.

**Gold growth.** Each expansion adds two or three gold papers, chosen from a new paper type or from papers that look wrong in the corpus report. The final gold set is 12 to 15 papers.

**Papers without gold are not checked one by one.** They are judged by the corpus report statistics and a skim of 10 randomly chosen series.

**Manifest.** One CSV lists every paper with its origin and the evidence for it (`source`; `popov_ref`; `cremers_ref` and `cremers_context`; `cites_cremers_keywords`; `extra_reason`), PDF status and source, OA status, license, and its inclusion decision (`status`, `reason`, `decision` auto or manual, `decided_on`). Excluded papers keep their rows. A paper that fails is quarantined with its outputs kept, not deleted.

## Work order

Nine phases (0 to 8) run in sequence; each ends when its done criterion is met.

| Phase | Work | Done when |
| --- | --- | --- |
| 0 | Tag v1; create the v2 skeleton and `CLAUDE.md`; build the manifest from the three sources and acquire PDFs | Manifest lists every paper with source, decision, and PDF status; an empty pipeline runs end to end on one paper |
| 1 | Gold set: Ylilammi pilot, then the five Dev papers | Format fixed; all five papers checked by the expert |
| 2 | Ontology v0 | Every quantity in the gold set is mapped or declared native |
| 3 | Convert v1 output to the six tables and score it | Baseline score exists; list of reusable v1 extraction results exists |
| 4 | Build the v2 pipeline on the Dev set | Dev score beats the baseline and reaches the target |
| 5 | Score Held-out; run the Sample tier; first ontology growth round | Corpus report exists; first external ontology review done |
| 6 | Comparison view; twin connection (questions 5 to 11) | Cross-paper case studies run on real data |
| 7 | Run all included papers; second ontology growth round; more gold papers | Full corpus processed; second external review done |
| 8 | New-paper intake, control, agentic layer | Decided later |

The Phase 4 target score is set after the Phase 3 baseline is known.

Phase 0 and the Phase 1 pilot can run in parallel.

## HTML reports

Six reports cover the whole project. Each is a single self-contained HTML file generated from the tables by one command.

| Report | First built in | Contents |
| --- | --- | --- |
| Paper card | Phase 1 | Original panel crops beside the extracted series drawn over them; experiment list with conditions and evidence sentences; unknown labels. Used for the expert's gold check and for debugging |
| Ontology page | Phase 2 | Quantity table, usage counts, example figures, change log. Used for expert and external review |
| Score report | Phase 3 | Experiment count match, series structure accuracy, condition precision and recall, point error. Each wrong item links to its paper card. Shows the change from the previous run |
| Corpus report | Phase 5 | Per-paper status and counts, data coverage per competency question, unknown labels ranked by paper count, quarantine reasons |
| Comparison view | Phase 6 | Pick a quantity pair to overlay curves across papers; filters for material, precursor, temperature; clicking a curve opens its paper card. This one screen is the dashboard |
| Twin report | Phase 6 | Per experiment: prediction versus measurement, source of every input, fitted coefficient, prediction on other papers |

The paper card is built first because it is the screen the expert uses to check the gold set.

## Working rules for Claude Code

These rules go into `CLAUDE.md` so that every session starts from them.

- Simplest solution first.
- PDFs, full text, and figure crops live outside git.
- One unit of work has one goal and one commit. The done criterion is written in one line before starting.
- Tests are the gold score plus about 10 invariants taken from v1 failure cases. No tests that pin counts.
- Before any LLM call, state the expected number of calls. Results are cached.
- The corpus is re-run once, at the end of a phase. Generated outputs are committed separately from code.
- Earlier commits, old reports, and v1 diagnostics are not re-audited.
- An investigation that reaches no conclusion in 20 minutes ends with two options and a question.
- A report back is 15 lines or fewer: what changed, how the score moved, what is left.
- Each unit starts a new session; `CLAUDE.md` supplies the context.

## What carries over from v1

v1 is frozen with a tag and kept for reference. v2 starts in a new directory.

| v1 part | In v2 |
| --- | --- |
| Docling parsing and figure crops (44 papers) | Reused as is |
| LLM extraction results (`figure_data.json`, `records.json`, 41 papers) | Reused as the starting input; figures with image panels or interpolated line curves are re-extracted |
| Unit parser and dimension check (`units.py`) | Kept |
| Condition scope and evidence (ConditionAssertion) | Idea kept, implementation simplified into the `conditions` table |
| HAR channel model and calibration (`channel_model.py`, M3) | Kept; input interface changed to the six tables |
| Experiment identity logic (two layers that disagree) | Dropped; redesigned as the single `resolve` stage |
| Ontology (about 200 classes) | Dropped; rewritten as the flat file |
| resolve, canonical, semantic, workbench stages | Dropped |
| 52 test files, `DEFERRED.md` | Code dropped; 10 to 20 failure cases kept as invariants |
| Control notebook, keyword-router orchestrator | Outside this plan |

**Known v1 rule to keep in mind while reusing its outputs:** never re-ingest a paper whose stored results are richer than what re-extraction would produce.

## Open decisions

- [ ] Confirm the five Dev papers.
- [ ] Choose the three Held-out papers.
- [ ] Choose the LLM for gold drafts and the LLM for the pipeline (they must differ).
- [ ] Confirm the competency question list, or add to it.
- [ ] Set the Phase 4 target score after the Phase 3 baseline.
