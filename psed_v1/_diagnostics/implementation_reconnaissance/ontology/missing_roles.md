# Role vocabularies — what exists, what does not

## Condition role

| existing field | level | values | can it separate deposition from measurement conditions? |
|---|---|---|---|
| `recipe_role` | **QuantityKind** (ontology) | `control_setting` 34, `observable` 37, `model_parameter` 22, `coordinate` 17, `structure` 11, `derived` 6, `species_property` 4, null 50 | **no** — one role per quantity kind for the whole corpus; a deposition temperature and a stage temperature are the same kind |
| `evidence_kind` | assertion | `experimental_condition` 2399, `model_input` 184, `literature_condition` 18 | partially — it separates model inputs and cited-work values, not measurement settings |
| `source_kind` | assertion | `methods` 1367, `caption` 493, `body` 462, `series_label` 279 | no — provenance of the text, not the physics |
| `bound_at_scope` / `scope` | assertion | `method` 1367, `figure` 849, `series` 307, `panel` 78 | no — document scope |
| `assertion_status` | assertion | `direct`/`approximate`/`estimated`/`fitted`/`derived` | no — confidence |
| `axis_role` (`x_axis_role`, `y_axis_role`) | entity | incl. `measurement_coordinate`, `spatial_coordinate`, process-setting roles | partially — it types the **axis**, and `granularity.classify` already uses it to separate a measurement scan from a process sweep |

**Absent:** any per-assertion field stating whether the value describes the deposition or the
observation.

## Material role

| existing field | what it holds |
|---|---|
| `material` | one string or `None` |
| `material_raw` | the unnormalised source string |
| `material_scope_level` | which rung of the evidence ladder |
| `material_evidence` | the matched text |
| `material_candidates` | competing names when unresolved |
| `multi_material_paper` | boolean |

**Absent:** deposited vs substrate / support / template / electrode / capping / comparison.
The ontology declares `on_substrate: Experiment -> Substrate` and a `Substrate` class — **0
instances, no producer**. `scripts/audit_exact_overlap.py` reconstructed the distinction by
hand for 21 candidate papers, storing `deposited_material` and `substrate_support_material`
in `reports/exact_overlap_audit.json`; that file is an audit artifact, not a pipeline input.

## Stack / multi-material

No representation. `material` is a single string per entity. Two materials in one sample
(`10.1149_2.067203jes` SiO2 + Al2O3 capping) can only be expressed by leaving `material`
unresolved, which is what the resolver does (20 of 38 entities, 11 of 32 experiments).

## Where a role could technically attach (implementation fact, not a proposal)

| attachment point | file:line | schema constraint |
|---|---|---|
| assertion dict | `conditions.py:188-210` | none — a dict literal |
| bound condition | `conditions.bind()` output | none — the assertion passes through |
| `controlled` entry | `to_kb.py:1159-1178` | none — a dict literal |
| entity dict | `to_kb.py:968-1035` | none |
| KG `ConditionAssertion` node | `build_kg.py:352-359` `**extra` | none |
| KG edge | `links.append({...})` accepts extra keys (`uses_precursor` already carries `reactant=lab`) | none |
| `QuantityKind.recipe_role` | `ontology/ald_ontology.yaml` -> compiled JSON | requires an ontology rebuild; `vocab.RECIPE_ROLE` is a plain dict lookup |
| `SCOPE_ORDER` | `pipeline/canonical/schema.py:53` | **closed list**; `scope_rank` returns `len(SCOPE_ORDER)` for unknown values (sorts last, does not raise) |
| transformation statuses / types / comparison groups | `pipeline/canonical/schema.py:31-52` | **closed and enforced** — `RuntimeError` at import if a `Status` value is not declared in the ontology |

Only the last two rows are closed vocabularies. Every per-record dict in the resolver is open.
