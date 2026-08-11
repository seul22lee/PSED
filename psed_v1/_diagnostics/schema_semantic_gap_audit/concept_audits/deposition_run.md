# DepositionRun

**Required**: an actual process execution. Yim Series A proves one run -> three samples;
Yim Fig 8b proves several runs -> one nominal case.

**Ontology**: `DepositionRun` exists ("An ExperimentalCase that is a film-growth run"), with
relation `produced_by_run: Sample -> DepositionRun`. **0 instances, relation unused.**

**Resolver**: no concept of a process execution. Nothing reads "same ALD run" style evidence.

**Evidence dependence**: rarely stated. Yim states it explicitly; the three audited papers do
not. Therefore MANDATORY SEMANTIC LEVEL but **not** a mandatory instance.

**Status**: UNUSED_OR_UNINSTANTIATED. Gap type **A**. Severity HIGH (it is the control
variable in Series A).
