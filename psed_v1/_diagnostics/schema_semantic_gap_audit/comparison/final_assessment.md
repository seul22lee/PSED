# Final assessment

## 12. Can the current ontology support the intended semantics without a major redesign?

**Yes.** This is the audit's headline finding, and it was not the expected answer.

The ontology already declares nearly the entire target model. These classes exist, are
documented with exactly the meaning the science requires, and have **zero instances**:

| class | ontology definition | instances |
|---|---|---|
| `ExperimentalCase` | "A physically distinct experimental case performed under one supported condition set" | 0 |
| `DepositionRun` | "An ExperimentalCase that is a film-growth run" | 0 |
| `Sample` | "A physical specimen produced by one or more deposition runs and carried between measurements" | 0 |
| `Measurement` | "One measurement performed on a Sample or ExperimentalCase" | 0 |
| `PlotRepresentation` | "One depiction (as-measured / scaled / normalized / inset) of an underlying measurement" | 0 |
| `ModelPrediction` | — | 0 |
| `DerivedRepresentation` | — | 2 corpus-wide |

The linking relations exist too, declared with the correct endpoints and unused:
`performed_on` (Measurement -> Sample), `measures_case` (Measurement -> ExperimentalCase),
`produced_by_run` (Sample -> DepositionRun), `case_in_series` (ExperimentalCase ->
ExperimentSeries), `derived_representation_of`, `observation_of_kind`, `measured_by`.

So the dominant gap type across the matrix is **A — the schema can represent it, the
pipeline does not populate it** (13 of 21 rows), not **B — the schema cannot represent
it**. Only two rows are genuine schema absences, and both are small vocabulary additions
rather than structural change (see item 13).

The corollary matters as much as the finding: **the ontology is not the thing to fix.**
Someone reading the class list would conclude PSED models runs, samples, measurements and
representations. It does not. The classes are declarations of intent that the resolver
never honoured, and adding more classes now would enlarge that gap rather than close it.

## 13. Minimum scientific distinctions any eventual extension must support

Reduced to the smallest set that discharges every CRITICAL and HIGH row in the gap matrix.
Deliberately minimal — this audit is not a licence to build maximal ontology complexity.

1. **A case is defined by its conditions, not by where it was printed.** Two panels
   reporting the same condition set are one case. One panel reporting eight settings is
   eight cases. (Discharges: `am.2016.182` Fig 2a/b/c; `2.067203jes` Fig 4.)

2. **A representation is not a case.** As-measured, scaled, normalized and inset views of
   one measurement are one measurement. The evidence for this is *already extracted* —
   `entity.representation` is populated on 1044/1044 entities — it just needs to stop
   being part of the identity string and start being a reason not to mint. (Yim Fig 9:
   6 measurements currently yield 18 Experiments.)

3. **A sample persists across measurements.** One specimen measured by three techniques
   is one sample. `physical_case_id` currently never crosses a figure — 608 groups, 608
   confined to a single printed figure. (Yim sample 11, Yim Fig 8a.)

4. **A run is distinct from a case and from a sample.** Three samples from one ALD run
   share the run; two runs under one recipe share the case but not the run. Without this
   no reproducibility claim in the corpus is representable. (Yim Series A; Yim Fig 8b.)

5. **Measurement conditions are not deposition conditions.** An objective-lens change is
   not a new deposition case. This needs a **role axis on conditions** — one of the two
   genuine schema additions. (Yim Fig 7a.)

6. **Material and geometry attach to the run/case, not to the paper.** A paper may deposit
   more than one material and use more than one geometry. `material_scope_level` already
   records which scope the evidence came from; the paper-level value overrides it anyway.
   (`2.067203jes`: SiO2 + Al2O3, planar + AR~30.)

7. **Deposited material is distinct from substrate, support, electrode and comparison
   material.** The second genuine schema addition — a **role axis on materials**. The
   candidate-expansion audit had to reconstruct this by hand for 21 papers precisely
   because the schema cannot express it. (`c3ta01665j` deposits Pt on TiO2 particles.)

8. **A characterization result links to the deposition that produced its sample.** The
   relations exist (`measures_case`, `performed_on`); nothing uses them, so electrochemical
   and imaging results become `UnresolvedSourceEntity` with no path back to the process.
   (`c7ta03257a`: 4 entities, all unresolved, `physical_case_id = None`.)

9. **Study-series membership is many-to-many and crosses figures.** One sample can belong
   to two author series. PSED has 327 `ExperimentSeries`, all figure-scoped, and zero
   cross-figure series. (Yim samples 8 and 12.)

Items 5 and 7 are the only two requiring new ontology vocabulary. Items 1-4, 6, 8 and 9
are resolver instantiation of classes and relations that already exist.

## 20. Full KG vs core KG

| | full onto KG | core flat KG | core series KG |
|---|---|---|---|
| nodes / edges | 13323 / 38055 | 1877 / 7243 | 1948 / 7385 |
| Paper | 47 (44 corpus + Arts 2019, Ylilammi 2018, Ylivaara 2020) | 32 | 32 |
| Experiment | 1127 | 851 | 851 |
| result nodes | `PlotSeries` 1044 **and** `Curve` 1042 | `ResultSeries` 835 | `ResultSeries` 835 |
| series | `ExperimentSeries` 327 | — | `ExperimentSeries` 71 |
| conditions | `ConditionAssertion` 3451 | folded into `varies` edges | same |

Three observations.

- **The core KG is stale, not different.** It is missing all 12 expansion papers
  (`knowledge_graph_core_flat.json` mtime 12:32 vs `knowledge_graph_onto.json` 14:01).
  This is a build-currency defect, not a modelling disagreement, and it is recorded so
  that a reader comparing 851 against 1127 does not diagnose a schema conflict.
- **The core KG's simplification is sound.** Collapsing `ConditionAssertion` into `varies`
  edges and `PlotSeries`+`Curve` into one `ResultSeries` loses provenance depth but no
  scientific distinction. `ResultSeries` is in fact the *better* name: the full KG's
  `PlotSeries` (1044) and `Curve` (1042) are two node types for one object.
- **Neither KG introduces a gap of its own.** Both faithfully project whatever the
  resolver mints. Every semantic defect visible in either is inherited.

## 22. Does closing these gaps require new node classes?

Mostly **no**, and that is the useful answer.

| need | new class? | why |
|---|---|---|
| ExperimentalCase, DepositionRun, Sample, Measurement, PlotRepresentation, ModelPrediction | **No** | all declared, all at 0 instances |
| Sample -> run, Measurement -> sample/case, case -> series, representation -> measurement | **No** | `produced_by_run`, `performed_on`, `measures_case`, `case_in_series`, `derived_representation_of` all declared with correct endpoints |
| condition role (deposition vs measurement) | **No new class** — a property/vocabulary on the existing `Condition`/`ConditionAssertion` | `recipe_role` exists but does not encode this axis |
| material role (deposited vs substrate/support/electrode/comparison) | **No new class** — a role property on the `deposits`/`Material` link | currently a bare `deposits` edge with no role |
| study series distinct from figure sweep | **No** | `ExperimentSeries` + the unused `case_in_series` already give the two levels |
| `Curve` / `PlotSeries` duplication | **No** — a removal, not an addition | KG-local |

**Zero new classes. Two new role vocabularies.** Everything else is instantiation.

## 24. Final classification

| # | concept | status | gap type | severity | layer |
|---|---|---|---|---|---|
| 1 | ExperimentCase | OVERLOADED / UNINSTANTIATED | A | CRITICAL | resolver |
| 2 | Sample | UNINSTANTIATED + MISNAMED | A | CRITICAL | resolver |
| 3 | DepositionRun | UNINSTANTIATED | A | HIGH | resolver + extraction |
| 4 | Measurement | KEEP_BUT_CLARIFY / UNUSED | A | HIGH | resolver |
| 5 | Representation | UNINSTANTIATED | A | HIGH | resolver |
| 6 | MeasurementCondition | MISSING | B | HIGH | ontology role + resolver |
| 7 | Material level | KEEP_BUT_MOVE_LEVEL | C | HIGH | resolver |
| 8 | Geometry level | KEEP_BUT_MOVE_LEVEL | C | HIGH | resolver |
| 9 | StudySeries | MISNAMED_OR_MISLEADING | A | HIGH | ontology clarify + resolver |
| 10 | characterization linkage | MISSING (relations exist) | A | HIGH | resolver |
| 11 | Substrate/support role | MISSING | B | MEDIUM | ontology role |
| 12 | Stack / multi-material sample | MISSING | B | MEDIUM | ontology + resolver |
| 13 | DepositionCondition | KEEP_BUT_CLARIFY | C | MEDIUM | ontology role |
| 14 | ResultSeries | KEEP + DUPLICATED | D | MEDIUM | KG |
| 15 | Transformation | KEEP (PROVENANCE_ONLY) | — | NONE | none |
| 16 | Model / ModelFamily | KEEP | — | NONE | none |
| 17 | SimulationRun | CORRECT_AS_IS | — | NONE | none |
| 18 | ModelSweep | CORRECT_AS_IS | — | NONE | none |
| 19 | experimental provenance | KEEP | — | NONE | none |
| 20 | simulated provenance | KEEP / CORRECT_AS_IS | — | NONE | none |
| 21 | imported-literature provenance | KEEP | — | NONE | none |

Gap types: **A** schema can represent it, pipeline does not populate it (13) — **B** schema
cannot represent it (3) — **C** represented at the wrong level (3) — **D** represented
twice (1) — no gap (7, counted in the KEEP rows above; rows 15-21).

Severity: CRITICAL 2, HIGH 8, MEDIUM 4, NONE 7.

## Summary in one paragraph

PSED's ontology already describes the intended science almost completely; its resolver
builds a different model. Every identity key in the pipeline is a document coordinate —
paper, figure, panel — where the science needs a laboratory coordinate — run, sample,
case. Seven classes that encode the laboratory view exist at zero instances, their linking
relations are declared and unused, and the resolver already extracts most of the evidence
those classes need (`representation` on 1044/1044 entities, `experimental_case_status` on
1044/1044, `material_scope_level` on 1127/1127) while declining to let any of it
participate in identity. The parts PSED gets right — simulated/measured separation,
imported-literature attribution, transformation provenance, canonical curve identity —
are exactly the parts where a dedicated class was actually instantiated. No structural
redesign is indicated. What is indicated is resolver instantiation of the existing model,
two role vocabularies (condition role, material role), and moving material and geometry
off the paper.
