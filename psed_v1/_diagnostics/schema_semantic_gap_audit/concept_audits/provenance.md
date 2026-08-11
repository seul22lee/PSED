# Provenance

**Scientifically important** (should reach a reader):
* `source` measured/simulated, and the entity class that produced it - **KEEP**
* source figure/panel and `json_pointer` + `source_checksum` - **KEEP**
* `linked_experiment_ids` on canonical curves - **KEEP**
* `material_evidence`, `material_scope_level`, condition `origin`/`evidence` - **KEEP**

**Audit/implementation provenance** (belongs in the full graph, not the reading graph):
* `ConditionAssertion` 3451, `TransformationExecution` 2126, `RawQuantityValue`,
  `CanonicalQuantityValue`, `ContextBinding` 42 - **KEEP as PROVENANCE_ONLY**

**Missing**: a link from a characterization result to the deposition that produced its
material. `c7ta03257a`'s CV/impedance curves are `UnresolvedSourceEntity` with
`physical_case_id=None`, although the PDF states the electrode was made from the Pt replica
of a fully specified 250-cycle ALD process. The ontology has `measures_case` and
`performed_on` for exactly this; both are unused.

**Status**: existing provenance KEEP; characterization linkage MISSING. Severity HIGH.
