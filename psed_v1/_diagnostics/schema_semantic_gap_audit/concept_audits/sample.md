# Sample / specimen

**Required**: a physical specimen carried between measurements. Yim sample 11 receives SEM,
Al-Ka map, EDS line scan and reflectometry; Yim Fig 8a repeats one measurement on sample 8.

**Ontology**: `Sample` exists - "A physical specimen produced by one or more deposition runs
and **carried between measurements**" - with `performed_on: Measurement -> Sample`.
**0 instances, relation unused.**

**Resolver**: the nearest thing is `physical_case_id`, which is
`shares_physical_case_with or entity_id`. Because `entity_id` is figure-derived and
`_shares_with` is only set between channels of a single measurement event, a physical case
**cannot span two figures**: 0 of 40 do in the audited papers, 66/1044 entities corpus-wide
carry a share and all are intra-event.

Schema note: `shares_physical_case_with` is a bare id string, so the *schema* permits
cross-figure identity; the *implementation* never produces it. Gap type **A**, not **B**.

**Status**: UNUSED_OR_UNINSTANTIATED (ontology) + MISNAMED_OR_MISLEADING
(`physical_case_id` promises a physical case and delivers a figure-scoped curve group).
Severity CRITICAL.
