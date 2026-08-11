# Simulation / ModelRun - the part that is already right

1. **Is SimulationRun semantically distinct from Experiment?** Yes. Ontology: "One execution
   of a model with a stated input set. **Not a current-paper Experiment**". `ModelSweep`:
   "points are ModelPredictions, **not Experiments**".
2. **Preserved in resolver?** Yes - 112 SimulationRun and 95 ModelSweep entities, minted from
   scout `source=simulated` per panel, never defaulted (`panel_source_for()` returns
   `unresolved` rather than guessing measured).
3. **Preserved in canonical?** Yes - `source.data_source` = measured/simulated per curve.
4. **Preserved in KG?** Yes - SimulationRun/ModelSweep are separate node types from
   Experiment; Model (4) and ModelFamily (1) exist with `in_model_family` and
   `model_consumes -> QuantityKind`.
5. **Recoverable without a string flag?** Yes - entity_class is structural, and canonical
   carries `data_source` independently.
6. **ModelSweep vs SimulationRun distinct usefully?** Yes - one execution vs a family over a
   swept parameter, mirroring experimental case vs series.
7. **Can an experimental and a simulated ResultSeries be compared without collapsing
   provenance?** Yes - both are PlotSeries/Curve, provenance stays on the producing entity.
   Yim Fig 9 (measured) vs Fig 10 (Ylilammi model, MATLAB re-implementation) is exactly this,
   and PSED represents it correctly.
8. **Does the proposed ExperimentCase semantics threaten it?** No, provided ExperimentCase is
   defined as a *deposition* case. The risk would be defining Experiment as "anything that
   produces a comparable curve", which would swallow SimulationRun.

**Status: KEEP / CORRECT_AS_IS.** This is the one part of the architecture that already
implements the target semantics. Do not disturb it.
