# Open questions

Architectural questions that cannot be answered from the repository. Listed, not answered.

## ExperimentalCase identity

1. Should exact nominal-condition equality imply the same `ExperimentalCase` when the paper
   does not state that the samples are the same? (`10.1039_d0ra09876k` has 27 entities
   across 8 figure slugs with identical bound conditions and material.)
2. Corpus-wide, **141 groups covering 686 entities** share identical bound conditions and
   material within a paper while carrying different `entity_key`s. Is that the candidate
   set for case merging, or is condition equality merely necessary and not sufficient?
3. Two entities may share conditions because the conditions are *incompletely extracted*
   (a figure-scope methods temperature bound to both) rather than because the cases are the
   same. What evidence level distinguishes those?
4. Is a case identified by its conditions, or by the paper's own sample enumeration when
   present, and which wins when they disagree?
5. Should a swept case carry its own x value as a condition? The N cases of a sweep are
   currently identical copies; 408 of 561 have no value distinguishing them.
6. When a sweep's setting count is `unresolved_settings` (27 entities), does a case exist
   with unknown multiplicity, or does no case exist?

## Sample activation

7. Should a `Sample` be mandatory when it is only indirectly inferable? 268 entities carry a
   sample/run identifier match; 776 do not.
8. When the paper labels samples only within a table ("sample 8 in Table 1"), is the table
   row the sample's identity, or is the identity the caption's textual reference?
9. Must every measurement have a sample, including for the 70 `UnresolvedSourceEntity`
   entities whose producing deposition is not represented?
10. Is `physical_case_id` to be reinterpreted, renamed, or left as a panel-local grouping id
    alongside a new sample concept?

## DepositionRun activation

11. Run identity is stated in 11 of 44 papers (`same ALD run` 2, `reproducibility` 12,
    `replicate` 4, `same sample` 5). Should `DepositionRun` be instantiated only where
    stated, or inferred by default (one run per case)?
12. When several samples come from one run, does the run own the conditions, or does the case?
13. Is a `DepositionRun` distinguishable at all without new extraction?

## Measurement activation

14. Are `ContinuousTrace` / `ExperimentalProfile` / `MultiOutputMeasurement` to *become*
    `Measurement` subclasses, or to remain result shapes with `Measurement` as a separate
    object above them?
15. Is a measurement identified by technique + sample, by panel, or by the paper's own
    statement?
16. Two panels showing the same technique on the same sample — one measurement or two?

## PlotRepresentation activation

17. Does a representation suppress case minting, or does it mint a case that is then merged?
18. When the same measurement appears in two panels with no caption keyword marking either
    as derived (`primary` on both), is that two representations or two measurements?
    960 of 1044 entities are `primary`.
19. Is `DerivedRepresentation` (2 instances, an entity class) the same concept as
    `PlotRepresentation` (0 instances, a `SourceEntity` subclass), or are they distinct?

## Study / ExperimentSeries semantics

20. Should `ExperimentSeries` keep its current meaning (a sweep within one figure, 327
    instances) with a separate concept for the author's study series, or change meaning?
21. If membership becomes many-to-many, is series membership evidence-bearing (the paper
    says so) or analytical (we grouped them)?
22. Yim's six author-declared Series produce zero current Series objects. Is that a defect
    to close, or a different concept that was never in scope?

## Condition role

23. Should the role live on the assertion (per occurrence) or on the QuantityKind (per
    quantity, corpus-wide)? The two answers are mutually exclusive for `temperature`.
24. How many roles are required? Is `evidence_kind`'s existing 3-value axis extended, or is
    a second axis added beside it?
25. Does an unroled condition default to deposition, to measurement, or to unresolved?
    2601 bound conditions currently have no role.
26. Are geometry-derived conditions (feature height/width/aspect ratio, `recipe_role ==
    "structure"`, 78 bound conditions) a third role or a sample property?

## Material role

27. Is the role a property of the material mention, of the `deposits` edge, or of a
    separate `on_substrate` relation (declared, 0 instances)?
28. For a stack, is there one entity with several roled materials, or several entities?
29. When the material is `unresolved` because the paper deposits two things (20 entities in
    `10.1149_2.067203jes`), does a role vocabulary resolve it or is the ambiguity genuine?

## Case-level geometry

30. Is geometry part of the `ExperimentalCase` identity key, or a linked context?
31. When a paper reports both planar and HAR results but geometry is classified once per
    document, is per-case geometry inferable from existing artifacts at all?
32. Should `tag_experiments` keep writing a paper default when no local evidence exists, and
    if so is `"planar"` the right literal default?

## Characterization linkage

33. Should a characterization curve with no representable producing deposition remain
    `UnresolvedSourceEntity`, or become a `Measurement` with a null case?
34. Is `10.1039_c7ta03257a` (0 experiments, 4 Pt curves with `cycle_number = 250`) correct
    as-is, under-resolved, or a case for a distinct result category?
35. Does linking characterization to synthesis require the deposition to be an object, or is
    an attribute-level link sufficient?

## KG projection

36. Should the full KG type case nodes `ExperimentalCase` (matching the `record_kind` string
    it already carries) or keep `Experiment`?
37. Should `PlotSeries` (1044) and `Curve` (1042) be joined by an edge, merged, or left as
    two independent projections? The core KG already merges them into `ResultSeries`.
38. Should `represents_same_as` be corrected to its declared endpoints, re-declared to match
    its 64 emitted instances, or removed?
39. Should an unknown `entity_class` reaching `_ENTITY_NODE` fail loudly instead of falling
    back to `UnresolvedSourceEntity`?

## Canonical responsibility

40. Should canonical stay one row per source curve, or gain a reference to a case/measurement?
41. Should `linked_experiment_ids` ever hold more than one id?
42. Should canonical carry material/geometry, which it currently has no field for?

## Simulation preservation

43. Simulation entities traverse the entire shared prefix and diverge only at two
    `is_experiment` gates. Is that acceptable, or should the model path be separated earlier?
44. Should `SimulationRun` gain `ModelPrediction` children (0 instances, declared), or stay
    a single object per model curve?
45. Yim Fig 10's 30 simulation entities carry `representation` labels
    (`as_measured`/`scaled`/`normalized`). Does representation apply to model output too?

## Cross-cutting

46. What is the intended reported unit of the corpus — is the headline "N experiments"
    replaced, and by what?
47. Do the existing per-entity assertions in `test_stage0_regression.py:141` and
    `test_granularity_and_axes.py:266` get rescoped, or kept alongside new ones?
48. Should `entity_key` become unique (it is not: 41 duplicates, 89 entities), and if so is
    that a semantic change or a defect fix?
