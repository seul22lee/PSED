# StudySeries vs ExperimentSeries

**Required**: an author-defined analytical grouping. Yim samples 8 and 12 each belong to two
Series, so membership is **many-to-many**, and the grouped variable may be a deposition
condition (D, E, F), a sample geometry (A, C) or a *measurement* condition (B).

**Ontology**: `ExperimentSeries` = "A group of experiments **from one figure/table** that
sweep a single condition (the per-point case)"; relation `case_in_series` exists but is
**unused**.

**Resolver**: mints `experimental_series_id` only for `discrete_experimental_sweep`
(387/851 experiments, 71 groups). Scoped to one entity/figure.

**Observed**: Yim declares 6 Series; PSED mints **0** for that paper.

**Status**: MISNAMED_OR_MISLEADING + KEEP_BUT_CLARIFY. Current `ExperimentSeries` is a
*curve/sweep abstraction*, not a study grouping. The schema does not forbid overlapping
membership (a multigraph), but the current construction is one-parent-per-entity.
Severity HIGH.
