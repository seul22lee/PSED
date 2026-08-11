# PSED implementation reconnaissance

READ-ONLY. 0 API calls, 0 pipeline reruns, 0 existing files modified, 0 architectural
decisions, no repair plan. Everything created by this task is under this directory.

Successor to `_diagnostics/schema_semantic_gap_audit/` (which established the semantics).
This task establishes the **implementation reality** those decisions need.

## Layout

```
identity/     entity_identity.md      every id generator, inputs, consumers, uniqueness
              experiment_identity.md  the case-minting branch table
              physical_case_identity.md
              representation_identity.md
resolver/     dataflow.md             end-to-end transition table, from code
              semantic_fields.md      what is available at identity time
              classification_gates.md experimental_case_status: assignment vs use
              material_flow.md  geometry_flow.md  condition_flow.md
              characterization_flow.md  simulation_flow.md
ontology/     existing_classes.md  existing_relations.md
              serialization_support.md  missing_roles.md
canonical/    canonical_contract.md  identity_dependencies.md  provenance_preservation.md
kg/           kg_builder_contract.md  scientific_vs_provenance_nodes.md
              existing_entity_support.md
tests/        test_dependency_inventory.md  count_sensitive_tests.md
              semantic_invariants_available.md
implementation_surfaces/
              affected_files.csv (26)  affected_functions.csv (34)
              existing_hooks.md  technical_alternatives.md
              backward_compatibility.md  artifact_dependencies.md (stage x info matrix)
representative_traces/  am2016_182.md  2_067203jes.md  c7ta03257a.md  yim2020.md
final/        implementation_facts.md  open_questions.md  decision_inputs.md
```

## Load-bearing implementation facts

**Identity is minted in one file.** All four sites are in `pipeline/resolve/to_kb.py`
(L901-903, L1037-1101, L1127-1187, L793-828 called at L1236), plus three grouping ids at
L1263-1273. `pipeline/text/geometry.py:263` is the only other site that overwrites a
semantic field after resolve.

**No condition, material or geometry value enters any identifier at any layer.**

**A sweep's cases are indistinguishable.** `to_kb.py:1129` deep-copies the record per case;
**561 swept cases, 408 without their own swept quantity in `controlled`** (top absent:
`deposition_temperature` 109, `exposure_time` 52, `pulse_time` 46).

**`entity_key` is not unique** — 996 unique for 1044 entities, 41 duplicate values over 89
entities. `build_core_kg.py:123-129` parses it positionally (`split("|")`, fields 1/2/4/5),
and `:112` parses the `__case` suffix. These are the only two format parsers of a resolved id.

**Representation is captured and ignored.** Populated 1044/1044; **0 identity groups differ
only by representation**, so its presence in `entity_key` changes nothing today. Yim Fig 9's
18 panels are labelled `as_measured`/`scaled`/`normalized` correctly and still mint 18 cases,
because `CLASS_MODEL["experimental_profile"]["case"] == 1` is unconditional.

**Sample/run evidence is extracted and discarded.** `SAMPLE_ID`/`SAMPLE_LIST`
(`entities.py:69-73`) fire on **268 entities across 24 papers** — on Yim's captions they
return `sample 11 surface`, `sample 8 in Table 1`, `sample 12, 13, and 14 in Table 1 Series
E`. `to_kb.py:976` keeps only the letter `I`; `cls["signals"]`,
`cls["supported_setting_count"]` and `cls["supported_setting_evidence"]` reach no output.

**Material is *not* broadcast from the paper.** `resolve_material`'s rung 6 fires only when
the paper has one material. `10.1149_2.067203jes` refuses on 20 of 38 entities rather than
choosing between SiO2 and Al2O3. **Geometry *is* broadcast** — `geometry.tag_experiments`
writes one paper value onto every experiment with the literal default `"planar"`.

**Characterization context is not lost.** `10.1039_c7ta03257a`'s four entities all carry
`material = "Pt"` and `cycle_number = 250`; they mint no experiment only because
`classify` returns `"unknown"`.

**Serialization is already generic; typing is not.** `build_kg.py:583` assigns `onto_class`
from `ONTO_IRI.get(node.type)` for all 226 declared classes, and `link()` accepts any
relation string. But `_ENTITY_NODE` (`build_kg.py:262-273`) is a closed 10-entry map and an
unknown `entity_class` becomes `UnresolvedSourceEntity` **silently**.

**Two cross-result grouping mechanisms already exist** — `_events` (L1210-1230) and
`_by_panel_label` (L1193-1203) — both key-agnostic in structure, both keyed on document
coordinates. `remap` (L1237-1259) is a working precedent for rewriting an id after every
reference to it has been built.

**Canonical is decoupled.** `curve_id` reads the source pointer, not resolved identity;
canonical has no material and no geometry field.

## Incidental observations (not acted on)

- `figure_slug` is `None` on all 1127 case records; `to_kb.py:1140` says
  "filled by assign_experiment_ids", which iterates entities, not cases.
- `canonical/live.py:155,160` (`series_id`, `point_experiment_id`) have no caller in `pipeline/`.
- The core KG is stale: 32 papers / 851 Experiments vs the full graph's 44 / 1127.
- `build_kg.py:328` re-`node()`s an existing id to retype it; `node()` is first-write-wins,
  so it is a no-op.
- `represents_same_as` (64 instances) runs entity -> its own PlotSeries, against a declared
  `PlotRepresentation -> Measurement`.

## Out of scope

`am.2016.182` printed Figure 4 (caption grammar) and `c7ta03257a` Fig 8b (Docling
PictureItem gap): KNOWN EXTRACTION ISSUES, recorded only.
