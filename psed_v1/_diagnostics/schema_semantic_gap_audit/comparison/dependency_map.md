# Dependency map

What each gap depends on, and what would break if it were ever addressed. Ordering, not
a plan.

## Layer where each gap originates

```
Docling / figure provenance      [no gaps found in this audit]
        |
Scout                            material candidates, figure relevance
        |
RESOLVER  <=== every semantic gap in this audit originates here
        |      entity_id / entity_key construction
        |      Experiment minting
        |      physical_case_id scoping
        |      paper-level material application
        |
Canonical                        inherits identity; adds honest curve_id
        |
Geometry tagging                 stamps geometry_class paper-wide  [second origin]
        |
KG (onto / core)                 faithful projection of resolved; adds Curve duplication
        |
Twin / reports / dashboards      consume Experiment counts as if they were case counts
```

Two origins only: **the resolver's identity construction**, and **`tag_experiments`**.
Nothing in the ontology, canonical layer, or KG builder needs to change first — they
propagate whatever identity the resolver mints.

## Ordering constraints

1. `Representation` must be resolved **before** case identity. If representations still
   mint separate entities, any case-grouping rule inherits the 3x inflation (Yim Fig 9).
2. `Sample` / `DepositionRun` must exist **before** `StudySeries` can be many-to-many.
   A series is a set of runs; without run identity there is nothing to put in the set.
3. `MeasurementCondition` vs `DepositionCondition` must be separated **before** case
   identity is keyed on conditions, or instrument settings will mint cases (Yim Fig 7a).
4. Material and geometry level-moves are **independent** of the above and of each other.
   They are the two cheapest items and they do not block anything.
5. The `Curve`/`PlotSeries` duplication is KG-local and blocks nothing.

## What breaks downstream if identity changes

| consumer | current assumption | breakage |
|---|---|---|
| `evaluate_kb.py` 5-axis rubric | Experiment count is the evidence count | scores shift; the rubric compares against itself, so thresholds need restating |
| `similarity.py` condition/curve/derived | pairwise over Experiments | pair counts change; the composite metric is coverage-aware so it degrades gracefully |
| twin validation | fixed expected counts | already brittle (the 26/27 issue, deliberately not repaired) |
| corpus dashboard, corpus_status | "N experiments" headline | needs relabelling to whatever the new unit is |
| `curve_id` | derived from source pointer, not from Experiment | **unaffected** — this is why the curve-identity fix was worth doing separately |
| canonical points, series/record/point conservation (I1-I8) | source-slice identity | **unaffected** |

The release invariants and the canonical numeric layer survive an identity change
untouched. Everything that breaks is a *count*, and every count that breaks is currently
reporting the wrong quantity anyway.

## Cost shape

- Level-moves (material, geometry): resolver-local, no ontology change.
- Instantiation of `Sample` / `DepositionRun` / `Measurement` / `PlotRepresentation`:
  resolver-local, no ontology change — the classes and the relations
  (`performed_on`, `measures_case`, `produced_by_run`, `case_in_series`,
  `derived_representation_of`) already exist and are declared with the right endpoints.
- New vocabulary genuinely required: a **condition-role axis** (deposition vs measurement)
  and a **material-role axis** (deposited vs substrate/support/electrode/comparison).
  These two are the only additions this audit finds necessary.
