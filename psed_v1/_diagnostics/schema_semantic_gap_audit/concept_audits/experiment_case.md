# ExperimentCase

**Required**: a scientifically distinguishable deposition case, keyed by deposited material,
chemistry, process settings, substrate and relevant sample geometry; may own many
Measurements.

**Ontology**: `ExperimentalCase` exists, defined exactly this way. **0 instances.**
`Experiment` also exists, defined "One run at a unique combination of controlled conditions"
- note this conflates *run* and *condition combination*, the very distinction Yim separates.

**Resolver**: mints `exp_id = <paper>__Fig<N><panel>__exp<NN>[__caseNN]`. Identity is
figure/panel-derived, so the same case appearing in three figures becomes three Experiments
(am.2016.182 T=100 C in Fig 2a/2b/2c).

**Status**: `Experiment` = OVERLOADED (result-locality + condition set);
`ExperimentalCase` = UNUSED_OR_UNINSTANTIATED. Gap type **A** (schema can, pipeline doesn't).
