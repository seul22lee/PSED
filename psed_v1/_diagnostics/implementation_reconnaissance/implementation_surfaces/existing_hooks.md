# Existing implementation affordances

Verified pieces of the current code that could carry additional semantics without new
architecture. Documented as affordances only.

## 1. Generic ontology IRI attachment (KG)

`build_kg.py:245` builds `ONTO_IRI = {class_id: iri}` for all 226 declared classes, and
`:583` attaches `onto_class = ONTO_IRI.get(n["type"])` at serialization. Any node typed with
a declared class id automatically receives the correct IRI. No per-class code.

## 2. Fully generic node/edge API

`build_kg.py:403-407`. `node(nid, ntype, label, **extra)` accepts any type string and any
attributes; `link(s, t, etype)` accepts any relation string. Neither validates. Edges may
also carry attributes via `links.append({..., "reactant": lab})` — already used by
`uses_precursor` and `with_coreactant`.

## 3. `record_kind` already says `ExperimentalCase`

`to_kb.py:1141-1142` writes `entity_class = "ExperimentalCase"` and
`record_kind = "ExperimentalCase"` on every case record; `build_kg.py:418` carries
`record_kind` onto all 1127 `Experiment` nodes. The string is present end-to-end; only the
node *type* is `Experiment`.

## 4. Sample/run identifier extraction that already fires

`entities.py:69-73`:
```python
SAMPLE_ID  = r"\b(?:samples?|runs?|specimens?)\s+(...)|\bSeries\s+([A-Z])\b"
SAMPLE_LIST= r"\b(?:samples?|runs?|specimens?)\s+((?:[A-Za-z0-9]+\s*(?:,|and)\s*){1,10}[A-Za-z0-9]+)"
```
Applied to caption and body at `entities.py:331`. **268 entities across 24 papers** produce
a match (signal family `I`). On Yim's captions it returns `sample 11 surface`,
`Samples 4, 5, and 6`, `sample 8 in Table 1`, `Sample 7, 8, and 9`,
`sample 12, 13, and 14 in Table 1 Series E`. The matched text is currently dropped:
`to_kb.py:976` persists only `signal_families` (the letters).

## 5. `supported_setting_count` — a paper-stated sample count, computed and discarded

`entities.py:279-295` returns `(count, evidence)` from an enumerated sample/run list, and
`_result` (L623-624) returns it as `supported_setting_count` / `supported_setting_evidence`.
Neither is written to any output; corpus check confirms 0 entities carry either key.

## 6. `representation` populated on every entity

`to_kb.py:985`, 1044/1044: `primary` 960, `scaled` 33, `normalized` 30, `as_measured` 20,
`inset` 1.

## 7. `experimental_case_status` populated on every entity

7 values, 1044/1044, read by no branch.

## 8. Material evidence ladder with scope level retained

`chemistry_scope.resolve_material` returns `scope_level` (7 rungs), `evidence` (the matched
text), `candidates` and `ambiguity_reason`; all four are persisted on entities and
experiments.

## 9. Assertion-level provenance fields, all open dicts

`conditions.assertion()` returns a plain dict with `evidence_kind`
(`experimental_condition`/`model_input`/`literature_condition`), `source_kind`, `scope`,
`assertion_status`, `species`, `raw_evidence`, `evidence_locator`. No schema, no enum, no
validator.

## 10. An existing cross-result grouping mechanism

`_events` (`to_kb.py:1210-1230`) is a real grouping pass over all entities of a paper. Its
key is `(fig_docling_index, panel_key, granularity_kind)` and its condition is
`granularity_kind == "multi_output_measurement"`. The **mechanism** is general — a
`defaultdict(list)` keyed by a tuple, with a holder/member split and a `_shares_with`
back-pointer resolved after ids exist. Its **key** is document-local.

Also present: `_by_panel_label` (`to_kb.py:1193-1203`), the fit-to-measurement linker, with
the same shape and the same locality.

## 11. Post-hoc id remapping already exists

`to_kb.py:1237-1259` builds `remap = {old_entity_id: experiment_id}` and rewrites entities,
cases, `fit_of_entity`, and condition `origin.experiment_id`. A working precedent for
changing an identifier after everything referencing it has been built.

## 12. `linked_experiment_ids` is a list

`build_canonical.py` `source.linked_experiment_ids` is a list field populated with 0 or 1
element. Cardinality > 1 requires no schema change.

## 13. Paper-level `_field_provenance` pattern

`to_kb._pprov` + `PAPER_ORIGINS`/`PAPER_STATUSES` (L139-153) is an existing pattern for
per-field origin records, asserted at construction time and never re-derived.

## 14. `axis_role` already separates measurement from process axes

`axis_roles.py` assigns roles including `measurement_coordinate` and `spatial_coordinate`;
`granularity.classify` already uses `x_role` to distinguish a measurement scan from an
independent process sweep. The measurement/deposition distinction exists at the **axis**
level today.

## 15. Ontology vocabularies are compiled, with a hard failure mode

`pipeline/canonical/schema.py:31-52` raises `RuntimeError` at import if the comparability
layer or any declared `Status` is missing from the compiled ontology — an existing pattern
for making a vocabulary addition fail loudly rather than silently.
