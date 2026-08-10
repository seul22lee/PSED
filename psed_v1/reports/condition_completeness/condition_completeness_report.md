# Condition-completeness repair

> **Recomputed after the experiment-extraction repair.** Bindings were
> re-derived against the corrected entities, so the targets differ from the
> first run: more conditions now reach an experimental case because measured
> discrete sweeps mint per-setting cases, and 14 conditions sit on fits, which
> are preserved but are not experiments. See
> [experiment_extraction_regression/REPAIR_REPORT.md](../experiment_extraction_regression/REPAIR_REPORT.md).

Success is measured as: **every condition the source states reaches the correct
entity with provenance and stays visible downstream** — not as a count of
ConditionAssertion objects.

## Coverage

| | count |
|---|--:|
| distinct conditions placed on an entity (matrix rows) | 2517 |
| **assertions successfully bound** | **1964** |
| ambiguous — candidates preserved, deliberately unbound | 553 |
| bound conditions on entities that have experimental cases | 1142 |
| **… inherited by the case / run** | **1142/1142** |
| bound on entities with no case (simulation / literature / unresolved) | 822 |
| **visible in the KG** | **1964/1964** |
| entities carrying ≥1 bound condition | 606/663 |
| conditions attached to a mis-materialised entity | **0** |
| **unresolved entities that KEPT their conditions** | **46/72** |
| first missing stage (bound rows) | {'none': 1915} |

## By quantity type

| quantity | bound | ambiguous |
|---|--:|--:|
| deposition_temperature | 352 | 104 |
| flow_rate | 320 | 110 |
| cycle_number | 285 | 70 |
| working_pressure | 208 | 35 |
| pulse_time | 176 | 80 |
| temperature | 104 | 6 |
| purge_time | 89 | 58 |
| feature_height | 72 | 24 |
| base_pressure | 62 | 0 |
| growth_per_cycle | 50 | 56 |
| carrier_gas_partial_pressure | 47 | 0 |
| precursor_partial_pressure | 36 | 0 |
| bubbler_pressure | 31 | 0 |
| hot_wire_temperature | 26 | 1 |
| generic_pressure | 25 | 27 |
| exposure | 22 | 0 |
| feature_length | 10 | 0 |

## By source type

| source | bound |
|---|--:|
| methods | 962 |
| caption | 423 |
| body | 309 |
| series_label | 221 |

## By bound scope

| scope | bound |
|---|--:|
| method | 962 |
| figure | 627 |
| series | 249 |
| panel | 77 |

## Ambiguous (withheld, candidates preserved)

571 conditions have several candidates at their narrowest applicable scope and
are **not** applied. Their candidates and the reason are kept on the entity.

| quantity | withheld |
|---|--:|
| flow_rate | 110 |
| deposition_temperature | 104 |
| pulse_time | 80 |
| cycle_number | 70 |
| purge_time | 58 |
| growth_per_cycle | 56 |
| working_pressure | 35 |
| generic_pressure | 27 |
| feature_height | 24 |
| temperature | 6 |

## Evidence separation

| evidence kind | assertions |
|---|--:|
| experimental_condition | 5135 |
| model_input | 583 |
| literature_condition | 130 |

| assertion status | assertions |
|---|--:|
| direct | 5181 |
| approximate | 571 |
| estimated | 78 |
| assumed | 8 |
| fitted | 6 |
| derived | 4 |

Imported-literature conditions carry `reference_work` and bind only to the series
naming that work; current-paper simulation inputs carry `evidence_kind=model_input`
and are never presented as measured conditions.

## What was repaired

| defect | fix |
|---|---|
| methods section never parsed — a bare "method" match hit the INTRODUCTION | heading-based section extraction, all methods-like sections |
| only pressures were extracted from prose | `conditions_from_prose`: governing-phrase typing for pressure, temperature, cycles, flow, pulse, purge, geometry, GPC |
| docling glyph damage: `300 1 C` (degree→digit), `10 /C0 7` (minus), `0 . 5` (split decimal), `Cof` (glued) | `normalize_docling` before parsing |
| reference-anchored statements invisible (no nearby "Fig. N") | nearest-preceding-citation binding; d/L/cycles/GPC attributed to the cited work |
| `TMA pulse time` axis lost its reactant | series axis naming a reactant binds species + `of_reactant` |
| panel (a)'s value leaked to panel (b) | caption split into panel clauses; a quantity a panel varies blocks broader values — except caption-preamble standards |
| H2/WF6/Ar flows collapsed into one ambiguous `flow_rate` | bindings keyed by (quantity, species) |
| one value typed as three pressure kinds | tight typing window + strongest-evidence dedup |
| generic `length`/`time`/`temperature` duplicated typed values | self-typing units only; specialisation wins over generic |
| range endpoints and capability claims asserted as settings | range/capability guard |
| KG dropped assertions whose quantity had no pre-existing node | quantity nodes minted; per-species node ids |
| `knowledge_graph_onto.json` was frozen since July (written by dead `s09_kg.py`) | `build_kg.py` now writes it |
| KB only saw experimental cases | `kb_service._load` folds in typed entities with `record_nature` |

## Known gap

`hot_wire_temperature` is asserted and bound (27 KG nodes) but is **not** an ontology
QuantityKind. It flows through as a `Condition` node. Adding the term is an ontology
change and was out of scope here; it is recorded rather than silently mapped onto
`deposition_temperature`, which would be wrong.

