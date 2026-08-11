# Serialization capability per zero-instance class

For each class: is there a Python representation, a JSON path, validation, KG emission,
canonical awareness, resolver awareness — and **why** it has zero instances.

| | `ExperimentalCase` | `DepositionRun` | `Sample` | `Measurement` | `PlotRepresentation` | `ModelPrediction` |
|---|---|---|---|---|---|---|
| 1. Python/dataclass/schema representation | **no** — no dataclass anywhere; resolved JSON is free-form dicts | no | no | no | no | no |
| 2. JSON serialization path | **yes, in effect** — `entity_class`/`record_kind` are already the literal string `"ExperimentalCase"` on all 1127 case records | no producer | no producer | partially — `measurement_class` carries the literal `"Measurement"` for sweeps | no producer | no producer |
| 3. validation path | **none** — no schema, no enum, no validator for resolved JSON | none | none | none | none | none |
| 4. can the KG builder emit it today | only via the generic `node(id, "ExperimentalCase", ...)` call; **not reachable through `_ENTITY_NODE`** | same | same | same | same | same |
| 5. relations serialized generically or hard-coded | **hard-coded per call site**; `etype` is an arbitrary string with no validation | " | " | " | " | " |
| 6. canonical layer knows it | no — canonical has no entity-class concept; it links by `linked_experiment_ids` only | no | no | no | no | no |
| 7. resolver knows it | **yes as a string**, `to_kb.py:1141-1142` | only in a comment (`to_kb.py:1191`) and a summary key `deposition_runs` (`to_kb.py:1990`) | only via `SAMPLE_ID`/`SAMPLE_LIST` regexes and `samples_are` | as a `measurement_class` string value | no | no |
| 8. **reason for zero instances** | **class only exists in YAML/ontology as a node type.** The string is written to `record_kind`, but `build_kg.py` types the node `Experiment`; no `ExperimentalCase` node is ever created | **no resolver instantiation** and no extraction of run identity | **no resolver instantiation**; extraction evidence partially exists (268 entities carry the `I` signal) but is discarded | **no resolver instantiation**; the three result-shape classes occupy this role | **no resolver instantiation**; the `representation` field exists on 1044/1044 entities | **no resolver instantiation**; `samples_are: "model_predictions"` marks 95 entities |

## Which are blocked by which layer

| blocker | classes |
|---|---|
| missing serializer | none — `json.dumps` of a dict is the only serializer |
| missing schema/validation | all six, equally (there is no schema for anything) |
| missing KG builder awareness | all six — `_ENTITY_NODE` (`build_kg.py:262-273`) is a closed 10-entry dict and unknown classes fall back to `UnresolvedSourceEntity` at L304 **without warning** |
| missing resolver instantiation | all six |
| missing extraction evidence | `DepositionRun` primarily; corpus text carries `same ALD run` 2, `reproducibility` 12, `replicate` 4, `same sample` 5 across 11 of 44 papers |
| class exists only in ontology YAML | `PlotRepresentation`, `ModelPrediction` |

## The generic affordance

`build_kg.py:583` computes `onto_class` as `ONTO_IRI.get(n.get("type"))`. Any node created
with `type == "<a declared class id>"` is automatically given the correct IRI with no code
change. The **typing** of entities is what is hard-coded, not the IRI mapping.
