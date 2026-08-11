# Decision inputs

One block per pending decision. Facts, mechanisms, available information, lost information,
dependencies. No ranking, no recommendation.

---

## DECISION 1 — where cross-result ExperimentalCase identity is resolved

**CURRENT IMPLEMENTATION FACTS.** Identity is minted at four sites in `to_kb.py`
(901-903, 1037-1101, 1127-1187, 793-828/1236). All inputs are document coordinates plus a
legend label. No condition, material or geometry value enters any identifier. The N cases of
a sweep are `json.loads(json.dumps(e))` deep copies differing only in `exp_id`/`case_index`;
408 of 561 carry no value of their own swept quantity. Two grouping passes exist
(`_events`, `_by_panel_label`), both keyed on `(fig_docling_index, panel_key, ...)`.

**AVAILABLE TECHNICAL MECHANISMS.** A1 in-loop; A2 split build/mint phases; A3 a new
cross-result pass between L1187 and L1236; A4 re-key the existing `_events` pass;
A5 a post-resolve rewrite in the style of `geometry.tag_experiments`. Details in
`implementation_surfaces/technical_alternatives.md`.

**INFORMATION AVAILABLE.** At L959: bound conditions (2601, with scope, source kind,
evidence kind, status, species, raw evidence, locator). At L898: classification, 8 signal
families, `signals` text, `supported_setting_count`. From L1766: material + scope level +
evidence + candidates. From L1188: every entity of the paper.

**INFORMATION ALREADY LOST.** After L1035: `cls["signals"]` (the matched sample/run text),
`cls["supported_setting_count"]`, `cls["votes"]`. After L1187: the per-case distinction of a
sweep (never created). After `geometry.tag_experiments`: local geometry.

**DOWNSTREAM DEPENDENCIES.** `canonical/curves.json` `linked_experiment_ids`;
`build_kg.py` Experiment nodes; `build_core_kg.py:112` (`split("__case")`);
`twin_validation._targets`; `fit_of_entity` (23); dashboards. Tests:
`test_stage0_regression.py:85,92,99,116,141`, `test_granularity_and_axes.py:255,266`,
`test_twin_validation.py` candidate count.

---

## DECISION 2 — Sample activation

**CURRENT IMPLEMENTATION FACTS.** No `Sample` object. `physical_case_id` is the nearest
proxy: 608 groups, all single-figure by construction (the `_events` key contains
`fig_docling_index`), 370 entities `None`, no code parses its string form, seven consumers
total. `SAMPLE_ID`/`SAMPLE_LIST` regexes exist (`entities.py:69-73`) and fire on 268
entities across 24 papers; the matched text is discarded at the entity dict.

**AVAILABLE TECHNICAL MECHANISMS.** E1 a new `entity_class` (needs `ENTITY_CLASS` +
`_ENTITY_NODE` entries); E2 a separate `resolved/samples.json` list, mirroring `series.json`;
E3 a `sample_id` attribute joined at projection; E4 a KG-only projection. The ontology
declares `Sample`, `produced_by_run`, `performed_on`; `build_kg.link()` emits any relation
string.

**INFORMATION AVAILABLE.** The `I` signal on 268 entities; captions such as `sample 11
surface`, `sample 8 in Table 1`, `sample 12, 13, and 14 in Table 1 Series E`; the existing
`_events` holder/member mechanism; `shares_physical_case_with`.

**INFORMATION ALREADY LOST.** The matched sample text (only the letter `I` survives);
table-row contents are not linked to captions anywhere.

**DOWNSTREAM DEPENDENCIES.** `build_core_kg.py:267`; `scripts/validate_granularity.py:72,130`;
`test_granularity_and_axes.py:266,355`; `test_stage0_regression.py:110,416`;
`to_kb.py` paper and figure summaries.

---

## DECISION 3 — DepositionRun activation

**CURRENT IMPLEMENTATION FACTS.** No object, no extraction, no relation emitted.
`DepositionRun` appears in a comment (`to_kb.py:1191`) and as a summary key
(`to_kb.py:1990` `deposition_runs`, computed from cases). Declared as a subclass of
`ExperimentalCase`; `produced_by_run: Sample -> DepositionRun` declared, 0 instances.

**AVAILABLE TECHNICAL MECHANISMS.** Same E1-E4 as Sample. `SAMPLE_ID` already matches
`runs?`.

**INFORMATION AVAILABLE.** Corpus text: `reproducibility` 12, `same sample` 5, `replicate`
4, `same ALD run` 2 — across 11 of 44 papers. Nothing in `scout.json`, `card.json` or
`records.json` carries run identity.

**INFORMATION ALREADY LOST.** Everything beyond the regex match; run structure is not a
scout or card field.

**DOWNSTREAM DEPENDENCIES.** None today (zero instances). Would newly couple to whatever
owns conditions.

---

## DECISION 4 — Measurement activation

**CURRENT IMPLEMENTATION FACTS.** `Measurement` is declared with `performed_on` and
`measures_case`, 0 instances. The string `"Measurement"` is the `measurement_class` value
for `discrete_experimental_sweep` (`entities.py:637`). Three result-shape classes occupy the
role: `MultiOutputMeasurement` 377, `ContinuousTrace` 118, `ExperimentalProfile` 71.
`measurement_event_id` exists on 1044/1044 entities, keyed on `(fig, panel, granularity)`.

**AVAILABLE TECHNICAL MECHANISMS.** E1-E4. `measurement_event_id` is an existing per-panel
measurement identity that no code parses.

**INFORMATION AVAILABLE.** `measurement_class`, `MODALITY` signal matches (`sig["M"]` 679
entities, `sig["Me"]` 715 from methods), axis semantics, `measurement_event_id`.

**INFORMATION ALREADY LOST.** The modality match text is in `classification_evidence`
(truncated to 4 strings) but not as a structured technique field.

**DOWNSTREAM DEPENDENCIES.** `build_core_kg.py:266` (`measurement_event_id` provenance);
`test_stage0_regression.py:110`; `test_granularity_and_axes.py:357`; `to_kb` summaries.

---

## DECISION 5 — PlotRepresentation activation

**CURRENT IMPLEMENTATION FACTS.** `representation` on 1044/1044 entities
(`primary` 960, `scaled` 33, `normalized` 30, `as_measured` 20, `inset` 1), derived at
`to_kb.py:764-774`. Read by no minting branch. In `entity_key` field 6 with **0** grouping
effect. `represents_same_as` is emitted 64 times with endpoints entity -> its own PlotSeries,
against a declared `PlotRepresentation -> Measurement`. `PlotRepresentation` 0 instances;
`DerivedRepresentation` 2.

**AVAILABLE TECHNICAL MECHANISMS.** E1-E4; F2 (remove from `entity_key`); a branch on
`representation` in the case-minting block; correcting or re-declaring `represents_same_as`.

**INFORMATION AVAILABLE.** The label on every entity; the full caption via
`_figure_caption`; `TransformationExecution` (2126) for numeric provenance of one curve.

**INFORMATION ALREADY LOST.** No source-curve -> target-curve relation exists in the
transformation layer; transformations are rule-declared, not recovered from paper equations.
Two `primary` panels showing the same measurement carry no marker at all.

**DOWNSTREAM DEPENDENCIES.** `build_kg.py:289,327-329`; `build_core_kg.py` `ResultSeries.representation`;
`test_stage0_regression.py:141` (per-entity `case_count <= 1`, which Yim Fig 9 satisfies
with 18 entities).

---

## DECISION 6 — Study / ExperimentSeries semantics

**CURRENT IMPLEMENTATION FACTS.** `ExperimentSeries` is minted only for
`discrete_experimental_sweep` (`to_kb.py:1104-1122`), 327 instances, id rewritten to
`{entity_id}__series` at L1277 — so it is figure-local by construction. Membership is a
parent pointer (`in_series` on the case, `contains` edges in the core KG series variant),
**not** a many-to-many relation. `case_in_series: ExperimentalCase -> ExperimentSeries` is
declared with 0 instances. Yim: 0 series objects despite 6 author-declared Series.

**AVAILABLE TECHNICAL MECHANISMS.** `SAMPLE_ID`'s `\bSeries\s+([A-Z])\b` alternative already
matches author series letters; `case_in_series` is declared and unused; the core KG already
builds a series variant with `contains` edges.

**INFORMATION AVAILABLE.** The `I` signal (268 entities); table captions
(`ctx["table_captions"]`); `between_curve_condition` / `between_curve_value`.

**INFORMATION ALREADY LOST.** Table row contents; the `Series X` match text.

**DOWNSTREAM DEPENDENCIES.** `build_kg.py` `es::` nodes, `series_varies` 161;
`build_core_kg.py` series variant (71 `ExperimentSeries`, 387 `contains`);
`test_granularity_and_axes.py:255`.

---

## DECISION 7 — condition role

**CURRENT IMPLEMENTATION FACTS.** `recipe_role` is per **QuantityKind** (34
`control_setting`, 37 `observable`, 22 `model_parameter`, 17 `coordinate`, 11 `structure`,
6 `derived`, 4 `species_property`, 50 null) — one role per quantity corpus-wide.
`evidence_kind` is per assertion (`experimental_condition` 2399, `model_input` 184,
`literature_condition` 18) with a comment, not an enum. `SCOPE_ORDER`
(`canonical/schema.py:53`) is a closed list; `scope_rank` returns `len(SCOPE_ORDER)` for
unknown values rather than raising. `Status` and the transformation vocabularies **are**
enforced — `schema.py` raises `RuntimeError` at import on a missing declaration.

**AVAILABLE TECHNICAL MECHANISMS.** B1 assertion dict; B2 QuantityKind `recipe_role`;
B3 `controlled` entry; B4 KG node/edge attributes; B5 extend `evidence_kind`; B6 reuse
`axis_role`. Details in `technical_alternatives.md`.

**INFORMATION AVAILABLE.** Per assertion: quantity, value, unit, scope, source kind,
evidence kind, status, species, raw evidence text, evidence locator. Per axis: `axis_role`,
already used by `granularity.classify` to separate a measurement scan from a process sweep.

**INFORMATION ALREADY LOST.** Nothing at assertion creation — that is the extraction point.

**DOWNSTREAM DEPENDENCIES.** `recipe.from_experiment` (+ `completeness()`);
`similarity.py`; `twin/m2_design.py`, `twin_validation.py`; `build_kg.py:450-453`
(`controls`, 6042 edges); `build_core_kg.py` `fixed_conditions`.

---

## DECISION 8 — material role

**CURRENT IMPLEMENTATION FACTS.** One `material` string per entity, plus `material_raw`,
`material_scope_level` (7 rungs), `material_evidence`, `material_candidates`,
`material_ambiguity_reason`, `multi_material_paper`. No role vocabulary. `Substrate` class
and `on_substrate: Experiment -> Substrate` declared, 0 instances, no producer. No validator
requires exactly one material. Canonical has no material field.

**AVAILABLE TECHNICAL MECHANISMS.** C1 in `resolve_material`; C2 on the scout list (an API
stage); C3 on the KG `deposits` edge (edges already carry attributes); C4 a second field on
the entity dict.

**INFORMATION AVAILABLE.** The scout material list; the evidence text at every rung;
`material_candidates` for unresolved cases; `scripts/audit_exact_overlap.py` +
`reports/exact_overlap_audit.json`, which already store hand-audited
`deposited_material` / `substrate_support_material` for 21 candidate papers.

**INFORMATION ALREADY LOST.** Nothing at the ladder — it sees series label, panel clause,
caption, scout note and body.

**DOWNSTREAM DEPENDENCIES.** `build_kg.py:432` `deposits` (1072 edges);
`build_core_kg.py` `Material` nodes (25); `twin/m2_design.py:697`; `similarity.py`;
`material_expansion_report.py`; every dashboard.

---

## DECISION 9 — case-level geometry

**CURRENT IMPLEMENTATION FACTS.** `geometry.tag_experiments` (`geometry.py:249-267`)
writes one paper value onto every experiment, with the literal default `"planar"`. It is a
post-resolve rewrite of `resolved/experiments.json`. `to_kb._geom_for` already resolves
geometry per record and writes it to the entity (L1021-1022). Canonical has no geometry field.

**AVAILABLE TECHNICAL MECHANISMS.** D1 `_geom_for`; D2 `tag_experiments`; D3 per-figure
classification (new extraction).

**INFORMATION AVAILABLE.** `geometry.json` per paper with a one-line evidence string;
`geometry_classes.yaml`; geometry-derived conditions (feature height/width/aspect ratio,
78 bound conditions with `recipe_role == "structure"`).

**INFORMATION ALREADY LOST.** Per-figure geometry evidence is never extracted;
`classify_deterministic` runs once per document.

**DOWNSTREAM DEPENDENCIES.** `twin_validation._coverage` and `_commensurability`
(`geometry_out_of_domain`); `m2_design.py:690-741,798,1257-1308`;
`build_core_kg.py:211-213` (`GeometryClass` node, `geometry` edge);
`kb_service.py:64`. Canonical is unaffected.

---

## DECISION 10 — characterization linkage

**CURRENT IMPLEMENTATION FACTS.** `10.1039_c7ta03257a`: 4 entities, all
`UnresolvedSourceEntity`, **all carrying `material = "Pt"` and `cycle_number = 250`**, 0
experiments. The filter is by class (`CLASS_MODEL["unknown"]["is_experiment"] is False`), not
by any characterization rule. The entities are present in `entities.json`, `results.json`,
canonical and the full KG; absent from `experiments.json`, the core KG and the twin.

**AVAILABLE TECHNICAL MECHANISMS.** `measures_case` and `performed_on` declared with correct
endpoints; `link()` emits any relation between two existing nodes but **silently drops** an
edge with a missing endpoint; a new `entity_class` would need `_ENTITY_NODE` awareness or it
becomes `UnresolvedSourceEntity` silently.

**INFORMATION AVAILABLE.** Material, ALD cycle count, scout drill notes naming the Pt
replica/electrode, series labels `uncoated`/`coated`.

**INFORMATION ALREADY LOST.** The link between the electrode preparation described in the
methods and the curves — no code attempts it.

**DOWNSTREAM DEPENDENCIES.** `test_stage0_regression.py:131` asserts unknown entities keep
`case_count == 0`, an `unresolved_reason`, and class `UnresolvedSourceEntity`. Any
reclassification changes that test.

---

## DECISION 11 — KG projection

**CURRENT IMPLEMENTATION FACTS.** Full KG 13323/38055; core KG 1877/7243 flat, 1948/7385
series — and **the core KG is stale** (32 papers / 851 Experiments vs 44 / 1127; mtime 12:32
vs 14:01). `onto_class` assignment is fully generic (`ONTO_IRI.get(node.type)`);
node typing is hard-coded per call site; `_ENTITY_NODE` is a closed 10-entry map with a
silent `UnresolvedSourceEntity` fallback. `link()` accepts any `etype` and drops edges with
missing endpoints without a message. `PlotSeries` 1044 and `Curve` 1042 have no edge
between them; the core KG merges them into `ResultSeries` 835.

**AVAILABLE TECHNICAL MECHANISMS.** New explicit `node()`/`link()` calls (immediate);
`_ENTITY_NODE` entries; a generic relation walker over `ONTO["relations"]` (does not exist).

**INFORMATION AVAILABLE.** The full compiled ontology is already loaded (`build_kg.py:24`),
including all 226 classes and 75 relations.

**INFORMATION ALREADY LOST.** Whatever the resolver did not persist.

**DOWNSTREAM DEPENDENCIES.** `kg_viewer.html`, `kg_core_*.html`, `reports/index.md`,
`test_report_freshness.py`, `check_ontology_graph_browser.py`.

---

## DECISION 12 — canonical responsibility

**CURRENT IMPLEMENTATION FACTS.** One row per **source curve** (1042).
`curve_id = doi::F{fig}::{panel}::{i}::f{fi}p{pi}` identifies a source slice and reads no
resolved identity. `linked_experiment_ids` is a list, populated with 0 or 1 element. No
material field, no geometry field, no case-count awareness. `validate_raw_unchanged` asserts
`raw.points` byte-identical to `figure_data.json`.

**AVAILABLE TECHNICAL MECHANISMS.** Extra keys in the `source` block (a dict literal, and
`validate_curve` does not check its key set); more entries in `linked_experiment_ids`.

**INFORMATION AVAILABLE.** The full figure_data slice, the resolved experiment via
`build_context_pool`, the axis semantics and the transformation chain.

**INFORMATION ALREADY LOST.** Nothing canonical needs — it re-reads `figure_data.json`.

**DOWNSTREAM DEPENDENCIES.** `build_kg.py` `Curve` nodes; `build_core_kg.curves_for`
(which parses `entity_key` positionally at L123-129 and the case suffix at L112);
`canonical/validate.py`; the release audit; `similarity.py`.

---

## DECISION 13 — simulation preservation

**CURRENT IMPLEMENTATION FACTS.** Simulation entities traverse the **entire** shared
prefix — `_entity_context`, `entity_key`, axis/granularity resolution, condition binding,
`assign_experiment_ids`, `_events` — and diverge only at `to_kb.py:1039` and `:1127`, both
driven by the static `CLASS_MODEL[...]["is_experiment"]`. `panel_source_for` never defaults
to `"measured"`; `build_canonical` copies `data_source` rather than inferring it.
`SimulationRun` 112, `ModelSweep` 95, `ModelPrediction` 0.

**AVAILABLE TECHNICAL MECHANISMS.** The two `is_experiment` gates are the only
simulation-safe boundaries in the resolver. `ModelPrediction` + `predicted_by:
ModelPrediction -> ModelSweep` are declared and unused.

**INFORMATION AVAILABLE.** Panel/figure source flags, `SIM_LABEL` matches,
`is_model_result`/`relevance`, body text, `Model`/`ModelFamily` individuals,
`model_consumes` 23, `in_family` 20.

**INFORMATION ALREADY LOST.** Nothing specific to simulation.

**DOWNSTREAM DEPENDENCIES.** `test_figure_provenance.py` (panel-source resolution + the
corpus DRILL anchor); `data_source` counts in every report; `material_expansion_report.py`
measured/simulated split; the twin (which never sees simulation entities because they are
absent from `experiments.json`).

Note for any decision touching the shared prefix: a change to `entity_key`,
`assign_experiment_ids`, `_events` or condition binding reaches simulation entities too,
because they are ordinary entities up to those two gates.
