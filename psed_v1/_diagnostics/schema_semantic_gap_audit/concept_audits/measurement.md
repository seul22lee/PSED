# Measurement

**Required**: the act of observing a Sample or Case. One case/sample may have many.

**Ontology**: `Measurement` exists with `performed_on -> Sample` and
`measures_case -> ExperimentalCase`. **0 instances, both relations unused.**

**Resolver**: what exists instead are *result-shape* classes -
`MultiOutputMeasurement` (377), `ExperimentalProfile` (71), `ContinuousTrace` (118). These
describe the **shape of a curve set**, not a measurement act, and each is minted per
figure/panel. `MultiOutputMeasurement` is the closest genuine analogue (it does group
channels of one event) but it is scoped to one panel.

**Status**: `Measurement` UNUSED; the three shape classes are KEEP_BUT_CLARIFY - they are
ResultSeries groupings misread as measurements. Severity HIGH.
