# Technical alternatives

Enumerated, not ranked. Every alternative listed is possible with the code and schemas that
exist today. No recommendation, no ordering, no preference is expressed or implied.

---

## A. Where cross-result ExperimentalCase identity could be resolved

### A1 — during entity construction, inside the per-record loop (`to_kb.py:847-1035`)
- **Required:** `resolve_source_entities` loop body.
- **Data available at that point:** `ctx` (caption, body, panel clause, panel labels,
  representation, source flags), the record's material + scope level + evidence, the
  classification and its signal families, `bound_conditions` (computed at L959, before the
  entity dict at L968), granularity, axis semantics.
- **Information already lost:** nothing — this is the earliest point at which conditions,
  material and classification coexist.
- **Constraint:** the loop processes one record at a time; no other entity of the paper
  exists yet, so a *cross-result* decision cannot be made here without buffering.
- **Backwards compatibility:** `entity_key` is built at L901 in this loop; changing it
  affects `results.json` `source_series_id` and therefore `build_core_kg.curves_for`.
- **Uses existing ontology declarations:** not by itself.

### A2 — after entity construction, before case minting
- **Required:** a restructure of `resolve_source_entities` — case minting (L1037-1101) and
  case records (L1127-1187) are currently inside the same loop as entity construction.
- **Data available:** everything in A1, for all entities of the paper, if the loop is split
  into a build phase and a mint phase.
- **Information already lost:** nothing.
- **Constraint:** `assign_experiment_ids` runs at L1236, after minting; a case identity
  decided before minting would have to be carried through the existing `remap` mechanism.
- **Backwards compatibility:** case `exp_id` shape is currently derived from `entity_id`
  plus `__case%02d`; `build_core_kg.py:112` parses that suffix.

### A3 — as a dedicated cross-result resolution pass after all entities exist
- **Required:** a new pass between L1187 (end of the record loop) and L1236
  (`assign_experiment_ids`); the `_events` block at L1210 is already such a pass.
- **Data available:** all entities of one paper with their bound conditions, materials,
  classifications, representations, granularity and case counts.
- **Information already lost:** `cls["signals"]` (the matched sample/run text),
  `cls["supported_setting_count"]`, `cls["votes"]` — discarded at entity-dict construction
  (L968-1035) unless also persisted.
- **Constraint:** case *records* are already built by this point (L1127-1187), so this pass
  would see cases that already exist.
- **Backwards compatibility:** the `remap` mechanism at L1237-1259 is an existing precedent
  for rewriting ids after everything is built.
- **Uses existing ontology declarations:** could emit `ExperimentalCase` / `case_in_series`.

### A4 — by reusing the existing `_events` grouping mechanism (`to_kb.py:1210-1230`)
- **Required:** the same block; its key tuple and its `shared` predicate.
- **Data available:** whatever is on the entity dicts at L1210.
- **Information already lost:** same as A3.
- **Constraint:** the current key is `(fig_docling_index, panel_key, granularity_kind)` and
  the predicate is `granularity_kind == "multi_output_measurement"`. Both are local decisions;
  the surrounding machinery (defaultdict, holder/member, `_shares_with`, post-id resolution)
  is key-agnostic.
- **Backwards compatibility:** `physical_case_id`, `shares_physical_case_with` and
  `measurement_event_id` are produced here; none is parsed anywhere; two tests assert
  cardinality per figure (`test_granularity_and_axes.py:266`) and per shared group
  (`test_stage0_regression.py:116`).

### A5 — as a post-resolve pass over `resolved/*.json`, like `geometry.tag_experiments`
- **Required:** a new module; `geometry.py:249-267` is the existing precedent for rewriting
  `resolved/experiments.json` in place after resolve.
- **Data available:** only what was persisted — entities, cases, series, assertions, results.
  That includes `bound_conditions`, `material` + scope, `representation`,
  `experimental_case_status`, `granularity_kind`, `classification_evidence`.
- **Information already lost:** `cls["signals"]`, `supported_setting_count`, `ctx` internals,
  the full caption (only a 200-char copy is on the record; `_figure_caption` re-reads
  `figure_data.json`).
- **Constraint:** runs after `assign_experiment_ids`, so ids already exist and are already
  referenced by canonical `linked_experiment_ids` if canonical was built first.
- **Backwards compatibility:** ordering-sensitive; `tag_experiments` today runs before
  canonical in the CLI sequence.

---

## B. Where a condition role could attach

### B1 — on the assertion (`conditions.assertion()`, `conditions.py:188-210`)
- Plain dict literal, no schema, no validator. Every downstream consumer reads by key.
- Data available: quantity, value, unit, raw evidence, locator, scope, source_kind,
  `evidence_kind`, species.
- Nothing lost — assertions are created at the point of text extraction.
- Would need `bind()` to carry it through (it already passes the assertion dict through).

### B2 — on the QuantityKind (`recipe_role`, `ontology/ald_ontology.yaml` -> `vocab.recipe_role`)
- Existing closed-ish vocabulary: `control_setting`, `observable`, `model_parameter`,
  `coordinate`, `structure`, `derived`, `species_property`.
- Constraint: **one role per quantity kind, corpus-wide.** `temperature` cannot be a
  deposition condition in one place and a measurement setting in another.
- Requires an ontology rebuild; `pipeline/canonical/schema.py` already fails loudly on a
  missing vocabulary.

### B3 — on the `controlled` entry (`to_kb.py:1159-1178`)
- Plain dict literal; already carries `source`, `assertion_source_kind`, `scope`,
  `context_status`, `assertion_status`, `species`, `origin{}`.
- By this point the assertion has been bound, so `bound_at_scope` and `source_kind` exist.
- Consumers that read `controlled` undifferentiated: `recipe.from_experiment`,
  `similarity.py`, `twin/m2_design.py`, `build_kg.py:450-453`.

### B4 — on the KG `ConditionAssertion` node / the `controls` edge
- `node(..., **extra)` and `links.append({...})` both accept arbitrary keys.
- Data available: whatever is on the bound condition.
- Purely a projection; the resolved layer would still not carry the distinction.

### B5 — via the existing `evidence_kind` field
- Already three values (`experimental_condition` 2399, `model_input` 184,
  `literature_condition` 18), already persisted, already flows to the KG node.
- Its declared vocabulary is a source comment, not an enum — nothing validates it.

### B6 — via `axis_role` (`axis_roles.py`)
- Already distinguishes `measurement_coordinate` from process-setting roles, and
  `granularity.classify` already consumes that distinction.
- Applies to the **axis** of a curve, not to a scalar condition.

---

## C. Where material role could attach

### C1 — in `chemistry_scope.resolve_material` (`chemistry_scope.py:171-245`)
- Returns a dict; adding a key requires no schema change.
- Data available: series label, panel clause, caption, scout note, body, the paper's
  material list.
- Constraint: it currently answers "which one material", returning `None` on ambiguity.
- `material_candidates` already survives on the record.

### C2 — on the scout material list (`scout.json` `materials`)
- Would require re-running Scout (an API stage).
- Data available: the full document.

### C3 — on the KG `deposits` edge
- `links.append({"s":..., "t":..., "e":"deposits", "role": ...})` — the pattern already
  exists (`uses_precursor` carries `reactant=lab`).
- The ontology declares `on_substrate: Experiment -> Substrate` with a `Substrate` class,
  0 instances, no producer.

### C4 — as a second field beside `material` on the entity/experiment dict
- Open dicts; no validator requires exactly one material.
- Canonical has no material field at all, so canonical is unaffected either way.

---

## D. Where case-level geometry could be decided

### D1 — in `to_kb._geom_for` (L398-435), already called per record
- Already material-parameterised; already returns `(structure, geometry_class, conditions)`;
  its output already lands on the entity (L1021-1022).
- Constraint: it reads the paper-level `extracted/geometry.json`.

### D2 — by changing `geometry.tag_experiments` (L249-267)
- The single site that overwrites every experiment with the paper value.
- Data available at that point: only the persisted experiment records plus `geometry.json`.

### D3 — as a per-figure geometry classification
- Would require new extraction; `classify_deterministic` operates on the whole document.

Canonical retains no geometry, so none of D1-D3 touches the canonical layer.

---

## E. How `Sample` / `DepositionRun` / `Measurement` / `PlotRepresentation` could be emitted

### E1 — as new `entity_class` values
- Requires an entry in `entities.ENTITY_CLASS` **and** in `build_kg._ENTITY_NODE`, otherwise
  the KG silently types them `UnresolvedSourceEntity` (`build_kg.py:304`).
- `onto_class` would resolve automatically via `ONTO_IRI`.

### E2 — as a separate object list in `resolved/`
- e.g. `resolved/samples.json`, mirroring `series.json`, which is already a separate list
  written by the same function and consumed by `build_kg.py:384`.
- KG emission would need explicit `node()`/`link()` calls; both accept arbitrary types.

### E3 — as attributes on existing objects rather than nodes
- e.g. a `sample_id` field on the entity, joined at projection time.
- No schema obstacle; the core KG already synthesises `ResultSeries` from result rows.

### E4 — as a KG-only projection
- Both builders already synthesise nodes that do not exist in resolved JSON
  (`Figure`, `ResultSeries`, `GeometryClass`, `ComparisonGroup`).

---

## F. What `entity_key` could become

### F1 — left as-is
- 41 duplicate values over 89 entities today; not unique, not validated.
- `build_core_kg.py:123-129` parses fields 1, 2, 4, 5 positionally.

### F2 — fields removed (e.g. `representation`)
- Measured: 0 identity groups differ only by representation, so removing field 6 changes no
  grouping in this corpus.
- `build_core_kg.py` reads `parts[0], parts[1], parts[3], parts[4]` — it does not read
  field 6, but it does index positionally, so field order matters.

### F3 — semantic fields added
- Every field is currently a document coordinate plus a legend label. Conditions, material
  and geometry are all available at L901.

### F4 — split into two keys (a source key and a semantic key)
- No schema obstacle; `provisional_entity_id` is an existing precedent for carrying two ids.
