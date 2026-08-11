# PSED schema-level semantic gap audit

READ-ONLY. 0 API calls, 0 pipeline reruns, 0 existing files modified. Everything created
by this task lives under this directory.

## Question

Which parts of the current ontology / resolver / canonical / KG design already support
the intended scientific semantics? Which conflict? Which are at the wrong level? Which
are missing? Which exist but are unused or incorrectly instantiated?

## Answer

The ontology already declares nearly the whole target model — `ExperimentalCase`,
`DepositionRun`, `Sample`, `Measurement`, `PlotRepresentation`, `ModelPrediction` — with
correct definitions, correct linking relations, and **zero instances**. The resolver
builds a different model in which every identity key is a document coordinate
(paper / figure / panel) rather than a laboratory coordinate (run / sample / case).

So the dominant gap is **instantiation, not expressiveness**: 13 of 21 rows are type A
(schema can represent it, pipeline does not populate it), 3 are wrong-level, 1 is
duplicated, and only 3 are genuinely absent from the schema — all three small role
vocabularies rather than structure. **Zero new classes are required.**

The parts PSED gets right are exactly the parts where a dedicated class was actually
instantiated: simulated-vs-measured (`SimulationRun` 112, `ModelSweep` 95, `data_source`
never defaulted), imported-literature attribution (`ImportedLiteratureObservation` 10,
plus non-corpus Paper nodes), transformation provenance (2126 executions), and
`curve_id` (unique 1042/1042).

## Read in this order

1. `comparison/final_assessment.md` — the verdict, items 12/13/20/22/24
2. `comparison/semantic_gap_matrix.csv` / `.json` — 21 concepts x 14 columns
3. `comparison/current_vs_target_semantics.md` — the two models, identity keys (item 18),
   evidence already captured but unused (item 19)
4. `comparison/preserve_vs_conflict.md` — what must not be damaged; 7 named conflicts
5. `comparison/dependency_map.md` — origins, ordering, downstream breakage
6. `representative_cases/` — `am2016_182`, `2_067203jes`, `c7ta03257a`, `yim2020`
7. `concept_audits/` — 12 per-concept audits
8. `current_schema/` — ontology / resolver / canonical / KG / twin inventories

## Scope notes

- `am.2016.182` printed Figure 4 (caption grammar) and `c7ta03257a` Fig 8b (Docling
  PictureItem gap) are recorded as **KNOWN EXTRACTION ISSUE - OUTSIDE THIS AUDIT**.
- The core KG's 32 papers / 851 experiments is **staleness**, not a modelling
  disagreement — it predates the 12-paper expansion. Recorded so it is not misread.
- No repairs are proposed as actions here, and no implementation was begun.
