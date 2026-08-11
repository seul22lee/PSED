# Condition representation

## Machinery inventory

| object | producer | shape | corpus |
|---|---|---|---|
| assertion | `conditions.assertion()` `conditions.py:188-210` | quantity, value, unit, raw_evidence, evidence_locator, assertion_status, **source_kind**, **evidence_kind**, species, species_basis, reactant_role, of_reactant, paper_id, figure_index, figure_number, panel, series_selector, reference_work, **scope**, confidence, ambiguity | 3451 `ConditionAssertion` KG nodes |
| bound condition | `conditions.bind()` `conditions.py:740-890` | assertion + `bound_at_scope` | 2601 on entities |
| `controlled` entry | `to_kb.py:1157-1178` | quantity, value, unit, of_reactant, source, assertion_source_kind, scope, context_status, assertion_status, species, origin{level,from,evidence,locator} | on every case record |
| `QuantityKind` | compiled ontology | 181 kinds, each with a `recipe_role` | 95 in core KG |
| `RawQuantityValue` / `CanonicalQuantityValue` | canonical layer | 2084 / 677 | full KG |
| `ContextBinding` | canonical context layer | 42 | full KG |
| `recipe_role` | `ontology/vocab.py:69`, per **QuantityKind** | `control_setting` 34, `observable` 37, `model_parameter` 22, `coordinate` 17, `structure` 11, `derived` 6, `species_property` 4, None 50 | — |

## Travel path

```
caption / series label / body / methods / tables / cited-work sentences
   -> ccond.from_caption / from_series_label / conditions_from_prose / pressures_from_text
      / reference_scoped_assertions                       (to_kb.py:911-956)
   -> assertion dicts, stamped a["source_entity"] = entity_key   (L957-958)
   -> ccond.bind(assertions, ctx, figure_varied)          (L959)
        narrowest SCOPE_ORDER wins: point < curve < series < panel < figure
                                    < experiment < method < paper
   -> ent["bound_conditions"] / ent["ambiguous_conditions"]
   -> case["controlled"]                                  (L1157-1178)
   -> KG ConditionAssertion nodes + asserts_condition / assertion_of_kind edges
                                                          (build_kg.py:336-361)
   -> twin: read from experiment["controlled"]
```

## What the code can and cannot distinguish today

| distinction | representable now? | mechanism |
|---|---|---|
| deposition/process condition | partially | `recipe_role == "control_setting"` on the QuantityKind |
| sample/geometry condition | partially | `recipe_role == "structure"` (11 kinds) |
| measurement condition | **no** | no field distinguishes it; a spot-size or objective setting has no quantity kind and no role |
| analysis/transformation condition | separately modelled | `TransformationExecution` is a distinct object, not a condition |
| model parameter | yes | `recipe_role == "model_parameter"` (22 kinds) **and** `evidence_kind == "model_input"` (184 bound conditions) |

The decisive constraint: `recipe_role` is a property of the **QuantityKind**, not of the
assertion. `temperature` has one role for the whole corpus. A deposition temperature and a
measurement-stage temperature are the same kind and therefore inseparable by this field.

## Existing role-like fields on the assertion itself

| field | values observed (2601 bound conditions) |
|---|---|
| `evidence_kind` | `experimental_condition` 2399, `model_input` 184, `literature_condition` 18 |
| `source_kind` | `methods` 1367, `caption` 493, `body` 462, `series_label` 279 |
| `bound_at_scope` | `method` 1367, `figure` 849, `series` 307, `panel` 78 |
| `assertion_status` | `direct` 2316, `approximate` 270, `estimated` 10, `fitted` 3, `derived` 2 |
| `recipe_role` (via quantity) | `control_setting` 2401, `observable` 83, `structure` 78, `derived` 39 |

`evidence_kind` is the closest existing axis. Its declared vocabulary
(`conditions.py:198-199`) is a comment, not an enum — no validator constrains it.

## Attachment points that exist today

| point | file | open or closed |
|---|---|---|
| assertion dict | `conditions.assertion()` `conditions.py:188-210` | **open** — a plain dict literal, no schema, no validator |
| bound condition | `conditions.bind()` output | **open** — passes the assertion through with `bound_at_scope` added |
| `controlled` entry | `to_kb.py:1159-1178` | **open** dict literal |
| QuantityKind `recipe_role` | `ontology/ald_ontology.yaml` -> compiled `ontology.json` | **closed-ish** — `vocab.recipe_role` is a lookup; adding a value requires the ontology rebuild, and `pipeline/canonical/schema.py` raises at import if the comparability layer is missing |
| `SCOPE_ORDER` | `pipeline/canonical/schema.py:53-54` | **closed list** — `["point","curve","series","panel","figure","experiment","method","paper"]`; `scope_rank` returns `len(SCOPE_ORDER)` for anything unknown, so an unrecognised scope sorts last rather than raising |
| KG `ConditionAssertion` node | `build_kg.py:352-359` | **open** — `node()` accepts `**extra` |
| `Status` / transformation vocab | `pipeline/canonical/schema.py:37-52` | **closed and validated** — raises `RuntimeError` at import if a status is not declared in the ontology |

## Downstream code that assumes all conditions are equivalent

- `pipeline/resolve/recipe.py` `from_experiment` — builds a Recipe from `controlled` without
  filtering by role, then scores `completeness()`.
- `twin/m2_design.py`, `twin/twin_validation.py` — read `controlled` by quantity id.
- `pipeline/canonical/similarity.py` — condition-vector similarity over all controlled entries.
- `build_kg.py:450-453` — emits a `controls` edge for every controlled entry whose quantity
  is not the swept coordinate (6042 edges).

## Yim Series B (spot size) as evidence

Yim's Fig 7a varies the microscope objective (10x vs 5x) — a measurement setting. It resolves
as `discrete_experimental_sweep` and mints 3 Experiments. The objective is not an ontology
QuantityKind, so it produces no assertion at all; the split comes from the x-axis being read
as an independent process sweep. Nothing in the condition layer is consulted.
