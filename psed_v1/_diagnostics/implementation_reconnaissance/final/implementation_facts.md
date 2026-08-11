# Implementation facts

Factual answers only. No recommendations.

### 1. Exactly where is scientific identity currently minted?

Four sites, all in `pipeline/resolve/to_kb.py`:

| site | line | mints |
|---|---|---|
| `entity_key` | 901-903 | `pid\|fig_docling_index\|printed_figure_number\|panel_key\|source_series\|representation` |
| case-count block | 1037-1101 | `experimental_case_count` / `_status` / `_reason` / `_lower_bound` |
| case-record block | 1127-1187 | one case dict per case, `record_kind = "ExperimentalCase"` |
| `assign_experiment_ids` | 793-828, called at 1236 | `experiment_id = pid__Fig7a[__expNN]`, which **overwrites** `entity_id` at 1242 |

Plus three grouping ids at 1263-1273: `physical_case_id`, `shares_physical_case_with`,
`measurement_event_id`.

### 2. At that point, which semantic fields are available?

At `entity_key` (L901): full caption, body mentions near the figure, panel caption clause,
all panel series labels, panel conditions, panel/figure source flags, resolved x/y axis
semantics and roles, granularity kind + evidence, the 11-way classification with 8 signal
families, material + `scope_level` + `evidence` + `candidates` + `ambiguity_reason` +
`multi_material_paper`, precursors/coreactants/reactants/carrier/process type/cycle sequence
+ `chemistry_provenance`, geometry class + structure, and the raw + canonical point arrays.

By L1037, additionally: `bound_conditions` (2601 corpus-wide, each with quantity, value,
unit, `bound_at_scope`, `source_kind`, `evidence_kind`, `assertion_status`, species,
`raw_evidence`, `evidence_locator`) and `ambiguous_conditions`.

### 3. Which available fields are currently ignored for identity?

All conditions; material and its scope level; geometry; classification; granularity;
`representation` (in the key but with no discriminating effect — 0 groups differ only by it);
`experimental_case_status`; `series_source_kind`; `signal_families`; every evidence string.

### 4. Which fields used for identity are document provenance rather than laboratory semantics?

Four of the six `entity_key` fields (`fig_docling_index`, `printed_figure_number`,
`panel_key`, and `pid`), and both fields consumed by `assign_experiment_ids`
(`printed_figure_number`, `panel`). `source_series` is a legend label — document text that
sometimes names a laboratory quantity. The only laboratory-semantic field in any identifier
is `representation`, and it changes no grouping.

### 5. Where does representation enter identity?

`to_kb.py:903`, field 6 of `entity_key`. It is derived at `to_kb.py:764-774` by keyword
match inside the panel's own caption clause. Measured: **0 identity groups differ only by
representation**, because it is constant within a `(figure, panel, series)` triple. It
reaches no other identifier.

### 6. Where do measurement settings enter or influence case minting?

Indirectly, through the x axis. `granularity.classify` uses `x_axis_role` to decide
`independent_process_sweep` vs a measurement scan; when it returns the former,
`to_kb.py:1057-1058` mints one case per distinct x value. Yim Fig 7a (objective lens
10x/5x) takes this path and mints 3 Experiments. No condition-level mechanism exists,
because no field marks a condition as a measurement setting.

### 7. Where are material and geometry attached?

Material: `chemistry_scope.resolve_material` (`chemistry_scope.py:171-245`), called per
record; written at `to_kb.py:1766-1771` (record), `1001-1006` (entity), `1394-1395` (result).
Geometry: `to_kb._geom_for` (L398-435) per record -> entity at L1021-1022; then
`geometry.tag_experiments` (`geometry.py:249-267`) rewrites `resolved/experiments.json`.

### 8. Where does local material/geometry information get overridden?

**Geometry: `geometry.py:263`** — `e["geometry_class"] = gc` for every experiment, with
`gc = g.get("geometry_class", "planar")`.

**Material: nowhere.** The ladder's rung 6 (`paper_single_material`) fires only when
`len(set(materials)) == 1`, i.e. when there is no competing local value. A multi-material
paper with no local evidence lands on rung 7 and gets `material = None` with candidates
retained. `10.1149_2.067203jes`: 20 of 38 entities and 11 of 32 experiments are `unresolved`,
not broadcast.

### 9. Which existing ontology classes can already be serialized/linked today?

`build_kg.py:583` sets `onto_class = ONTO_IRI.get(n["type"])` — **all 226 declared classes**
would receive the correct IRI the moment a node of that type existed. `link(s, t, etype)`
accepts any relation string with no validation. The obstacle is node *typing*, not
serialization: `_ENTITY_NODE` (`build_kg.py:262-273`) is a closed 10-entry map and unknown
entity classes fall through to `UnresolvedSourceEntity` at L304 **without warning**.

### 10. Which ontology classes exist only declaratively?

`PlotRepresentation` and `ModelPrediction` (ontology only). `ExperimentalCase` exists as a
**string** in `to_kb.py:1141-1142` and reaches all 1127 KG `Experiment` nodes as
`record_kind`, but is never a node type. `Sample` exists only as regexes
(`entities.py:69-73`) and the `samples_are` field. `Measurement` exists as the
`measurement_class` string value for `discrete_experimental_sweep` (`entities.py:637`).
`DepositionRun` exists only in a comment (`to_kb.py:1191`) and a summary key
(`to_kb.py:1990` `deposition_runs`).

### 11. Why are those six classes zero-instance?

| class | reason |
|---|---|
| `ExperimentalCase` | the string is written to `record_kind`; the KG types the node `Experiment`; no `ExperimentalCase` node is created |
| `DepositionRun` | no resolver instantiation; no run-identity extraction |
| `Sample` | no resolver instantiation; the extraction signal exists (268 entities carry family `I`) and its matched text is discarded |
| `Measurement` | no resolver instantiation; the three result-shape classes occupy the role |
| `PlotRepresentation` | no resolver instantiation; the `representation` field exists on 1044/1044 |
| `ModelPrediction` | no resolver instantiation; `samples_are: "model_predictions"` marks 95 entities |

None is blocked by a missing serializer (there is no serializer — resolved JSON is
`json.dumps` of free-form dicts) or by validation (there is no schema for resolved JSON).

### 12. Where can same-case information potentially be known before it is lost?

- `bound_conditions` are computed at `to_kb.py:959`, **before** the entity dict (L968) and
  before case minting (L1037).
- `cls["signals"]` (the matched sample/run/`Series X` text) and
  `cls["supported_setting_count"]` exist at L898 and are dropped at L968-1035.
- Material + `scope_level` + `evidence` exist from the record loop (L1766).
- All entities of a paper coexist from L1188 onward, before `assign_experiment_ids` (L1236).

### 13. Does any existing cross-result grouping mechanism exist?

**Yes, two**, both in `to_kb.py`:

- `_events` (L1210-1230): `defaultdict(list)` keyed `(fig_docling_index, panel_key,
  granularity_kind)`, with a holder/member split, a `_shares_with` back-pointer, and
  resolution after ids exist (L1260-1273). Produces `physical_case_id`,
  `shares_physical_case_with`, `measurement_event_id`.
- `_by_panel_label` (L1193-1203): keyed `(fig_docling_index, panel_key, series_label)`,
  links a fit to the measured curve it describes -> `fit_of_entity` (23 instances).

Both mechanisms are key-agnostic; both keys are document-local.

Also: `remap` (L1237-1259) is a working precedent for rewriting an identifier after every
reference to it has been built.

### 14. Which identifiers are safe source identifiers vs overloaded scientific identifiers?

**Source identifiers** (they name a place in a document and are honest about it):
`curve_id` (its docstring says so), `json_pointer`, `fig_docling_index`,
`printed_figure_number`, `panel`, `figure_slug`.

**Overloaded** (a document coordinate standing in for a laboratory object):
`entity_id`/`experiment_id`, case `exp_id`, `physical_case_id` (named for a specimen,
computed as the panel-local case-owning entity), `measurement_event_id`,
`result_series_id` (aliased to `entity_id`), `experimental_series_id`.

**Purely internal:** the provisional `eid` (L904) and `exp_id` (L1737), and `entity_key` —
except that `entity_key` is exported as `results.json` `source_series_id` and parsed
positionally by `build_core_kg.py:123-129`.

### 15. Which downstream systems depend on current Experiment ids?

`canonical/curves.json` `source.linked_experiment_ids`; `build_kg.py` (`Experiment` node
labels, `depicted_by` joins); `build_core_kg.py` (`exp::` ids, and the
`eid.split("__case")[0]` parse at L112); `twin/twin_validation.py` `_targets`;
`twin/kb_bridge.py:174`; all report/dashboard generators; `fit_of_entity` (23 instances
storing a resolved `entity_id`); `scripts/validate_granularity.py` orphan checks.

No file path or external URL is derived from any of them.

### 16. Which tests freeze current incorrect semantics?

- `test_stage0_regression.py:141` — "representations do not duplicate the underlying case"
  asserts `experimental_case_count <= 1` **per entity**. Yim Fig 9's 18 entities each have
  exactly 1 case, so the test passes while 6 measurements are counted 18 times. The scope
  is the entity; the claim it names is about the measurement.
- `test_granularity_and_axes.py:266` — asserts `len({physical_case_id}) == 1` **per printed
  figure**, which `_events` guarantees by construction.
- `test_granularity_and_axes.py` "ids use the printed figure number" — pins the `Fig<n>`
  id shape.
- `test_twin_validation.py` candidate count — a known-brittle snapshot.
- `test_m2_design.py:336` `len(family_ranges) == 3`, `test_chemistry_params.py:70`
  `len(byk) == 4`, `test_m2_chemistry.py:78` `== 2` — corpus snapshots.

### 17. Which tests protect behaviour that must be preserved?

No experiment count from point count (`:61`); a PlotSeries is never an Experiment (`:72`);
observations are not experiments (`:78`); multi-output channels do not each mint a case
(`:99`, `:116`); imported literature keeps both papers (`:123`); unknown entities preserved
unsplit and unpromoted (`:131`); no observation lost (`:148`); series/record/point
conservation (`test_extraction_coverage.py`); raw points byte-identical
(`canonical/validate.py:241`); window endpoint never a scalar
(`test_card_temperature.py:42-43`); the ~20 sections of `test_figure_provenance.py`;
`test_ontology_relationships.py`; the canonical rules/units/context/semantics suite.

### 18. Which implementation surfaces affect simulation provenance?

`figure_extract.panel_source_for` (L367-387, never defaults to measured);
`canonical/series_identity.resolve_panel`; `entities.classify` simulation votes
(L375-397) and the `simulation -> model_sweep` demotion (L424-425);
`CLASS_MODEL["simulation"]` / `["model_sweep"]` (`entities.py:638-641`);
`ENTITY_CLASS` (`:659-660`); `build_canonical` `source.data_source`;
`build_kg._ENTITY_NODE`.

Simulation entities pass through **the entire shared prefix** — `_entity_context`,
`entity_key`, axis/granularity resolution, condition binding, `assign_experiment_ids`,
`_events` — and diverge only at the two `model["is_experiment"]` gates
(`to_kb.py:1039` and `:1127`).

### 19. Which surfaces affect imported literature / transformations?

Imported literature: `entities.LIT_LABEL`, `CLASS_MODEL["imported_literature_data"]`,
`originally_reported_in` (`_result`), `to_kb.py:1000` `reported_in`,
`build_kg.py:319-324` (the `cite::` Paper node with `cited_work=True` — `Arts 2019`,
`Ylilammi 2018`, `Ylivaara 2020`), `test_stage0_regression.py:123`.

Transformations: `canonical/canonicalize.py`, `rules.py`, `units.py`, `context.py`,
`schema.py` (which raises at import on a missing vocabulary), `validate.py`
(`validate_raw_unchanged`), and the KG comparability layer (`TransformationExecution` 2126,
`TransformationRule` 8, `RawQuantityValue` 2084, `derived_from_value` 2803).

Neither depends on Experiment ids, except `fit_of_entity` (23 instances).

### 20. What existing code hooks could support activation of the declared ontology?

Fifteen, detailed in `implementation_surfaces/existing_hooks.md`. The load-bearing ones:
the generic `ONTO_IRI` -> `onto_class` attachment (`build_kg.py:245,583`); the untyped
`node`/`link` API (`build_kg.py:403-407`); `record_kind = "ExperimentalCase"` already
present end-to-end; `SAMPLE_ID`/`SAMPLE_LIST` already firing on 268 entities;
`supported_setting_count` already computed; `representation` and
`experimental_case_status` already on 1044/1044 entities; the `_events` grouping
mechanism; the `remap` post-hoc id rewrite; `linked_experiment_ids` already a list; and the
`_field_provenance` per-field origin pattern.
