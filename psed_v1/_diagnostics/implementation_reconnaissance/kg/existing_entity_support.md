# Existing entity support in the KG

## What is already generic

| mechanism | file:line | consequence |
|---|---|---|
| `ONTO_IRI = {c["id"]: c.get("iri") for c in ONTO["classes"]}` | `build_kg.py:245` | a table of all 226 declared classes |
| `"onto_class": ONTO_IRI.get(n.get("type"))` | `build_kg.py:583` | **any** node typed with a declared class id gets its IRI automatically |
| `node(nid, ntype, label, **extra)` | `build_kg.py:403` | arbitrary node type + arbitrary attributes |
| `link(s, t, etype)` | `build_kg.py:407` | arbitrary edge type |
| `links.append({...})` with extra keys | e.g. `build_kg.py:443` `reactant=lab` | edges can carry attributes |
| `ONTO` loaded whole | `build_kg.py:24` | classes, relations, quantity kinds, individuals, models all available |
| `_emit_tbox` | `build_kg.py:45` | already emits ontology-declared vocabulary nodes (rules, groups, normalization definitions) |

## What is hard-coded

| mechanism | file:line | consequence |
|---|---|---|
| `_ENTITY_NODE` 10-entry map | `build_kg.py:262-273` | resolved entity classes outside it fall to `UnresolvedSourceEntity`, silently (L304) |
| every `node(...)` call site | throughout | node classes are enumerated by hand |
| every `link(...)` call site | throughout | relations are enumerated by hand; no relation-declaration walker |
| core KG node types | `build_core_kg.py` | 11 types, hand-written |

## Support matrix for the six zero-instance classes

| class | would get correct IRI if a node existed | reachable through the entity path | reachable through a new explicit call |
|---|---|---|---|
| `ExperimentalCase` | yes | no (`_ENTITY_NODE`) | yes |
| `DepositionRun` | yes | no | yes |
| `Sample` | yes | no | yes |
| `Measurement` | yes | no | yes |
| `PlotRepresentation` | yes | no | yes |
| `ModelPrediction` | yes | no | yes |

## Relation support matrix

All eight zero-instance relations (`case_in_series`, `performed_on`, `measures_case`,
`produced_by_run`, `has_observation`, `predicted_by`, `derived_representation_of`,
`on_substrate`) would be emitted by a plain `link(src, dst, "<relation_id>")` call, with no
validation obstacle — the only requirement is that both endpoint nodes already exist in
`nodes`, otherwise the edge is dropped without a message.
