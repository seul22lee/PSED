# Resolver inventory (read-only trace of `pipeline/resolve/to_kb.py`)

| mechanism | input semantics | decision rule | output semantics | identity rule | known failure |
|---|---|---|---|---|---|
| entity classification | one flattened record (curve) + scout card | signal-family / granularity heuristics | one of 10 `entity_class` values | one record -> one entity | classes are *result shapes*, not scientific acts |
| Experiment minting | entity + its observations | a sweep yields one case per point; otherwise one case | rows in `experiments.json` | `exp_id = entity_id [+ __caseNN]` | cross-figure identity impossible |
| `entity_id` | figure slug + panel + running index | `<paper>__Fig<N><panel>__exp<NN>` | primary key of everything downstream | **figure/panel derived** | over-splits one case across figures |
| `physical_case_id` | `shares_physical_case_with or entity_id` | set only when `experimental_case_count` or a share exists | claims to be the physical case | inherits the figure-scoped entity_id | never spans figures (0/40 observed) |
| `shares_physical_case_with` | `_shares_with` holder within one channel group | set for non-first channels of a **single measurement event** | "one of N channels ... on the same sample" | within one figure/panel group only | cannot express same-sample across figures |
| sweep / case minting | `discrete_experimental_sweep` classification | mint `<paper>-S%03d`, one case per point | `experimental_series_id` | per entity | 387/851 experiments only |
| material assignment | scout `materials` + caption/legend | `material_scope_level` incl. `paper_single_material` | one material per experiment | paper-level default | stacks and secondary depositions collapse |
| geometry assignment | `classify_deterministic()` on title+abstract | one label per paper, then `tag_experiments()` stamps every row | `geometry_class` on every Experiment | **paper-level** | planar+HAR papers unrepresentable |
| controlled / varied | caption + card conditions | numeric-value guard | `controlled[]` list, `varies` | quantity + value | **no role field** distinguishing deposition vs measurement condition |
| measured / simulated | scout drill `source` per panel | `panel_source_for()` | `source` on records; SimulationRun/ModelSweep classes | explicit, never defaulted | correct |
| characterization fallback | entity with no process-condition/outcome relation | -> `UnresolvedSourceEntity` | stranded entity, `physical_case_id=None` | n/a | no link to producing deposition |

## Identity flow
`records.json` row -> `entity_id` (figure/panel) -> `experiment_id` -> `exp_id` ->
`physical_case_id` -> canonical `curve_id` -> KG `Experiment`/`PlotSeries` node.

Every downstream identity is therefore a function of **which figure panel the curve was
drawn in**, not of what was deposited or measured.
