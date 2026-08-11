# Stage x information matrix

Where information actually exists, and where it is lost. Values: PRESENT / PARTIAL /
ABSENT / DISCARDED BEFORE THIS STAGE / OVERWRITTEN / N/A.

| stage | material | material role | geometry | deposition conditions | measurement conditions | representation | experiment-status | sample evidence | run evidence | measurement technique | source figure/panel | measured/simulated | transformation links |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Docling/inventory | ABSENT | ABSENT | ABSENT | PRESENT (in text) | PRESENT (in text) | PRESENT (in caption text) | N/A | PRESENT (in caption/body text) | PRESENT (in body text) | PRESENT (in text) | PRESENT | ABSENT | N/A |
| Scout | PRESENT (paper-level list) | ABSENT | ABSENT | PARTIAL (window, process type, precursors) | ABSENT | ABSENT | N/A | ABSENT | ABSENT | PARTIAL (per-figure why note) | PRESENT (crop tag) | PARTIAL (drill note) | N/A |
| figure extraction | PARTIAL (per figure/panel/legend) | ABSENT | ABSENT | PARTIAL (panel conditions) | ABSENT | PRESENT (caption text retained) | N/A | PRESENT (caption text retained) | PARTIAL (caption/body text) | PARTIAL (caption text) | PRESENT | PRESENT (panel_source, never defaulted) | N/A |
| records | PARTIAL (raw material string) | ABSENT | ABSENT | PARTIAL (controlled dict, series value) | ABSENT | ABSENT (caption truncated to 200 chars) | N/A | ABSENT | ABSENT | ABSENT | PRESENT (provenance figure/panel) | PRESENT | N/A |
| resolver pre-classification (ctx) | PRESENT (ladder resolved) | ABSENT | PRESENT (paper value via _geom_for) | PRESENT (assertions bound) | ABSENT (no role axis) | PRESENT (_representation) | N/A | PRESENT (SAMPLE_ID sig I, 268 entities) | PARTIAL (SAMPLE_ID matches runs/specimens) | PARTIAL (MODALITY signals) | PRESENT | PRESENT (panel/figure source flag) | N/A |
| resolver entity | PRESENT + scope_level + evidence + candidates | ABSENT | PRESENT (paper value) | PRESENT (bound_conditions, 2601) | ABSENT | PRESENT (1044/1044) | PRESENT (experimental_case_status, 1044/1044) | DISCARDED BEFORE THIS STAGE (only the letter I survives; signals text dropped) | DISCARDED BEFORE THIS STAGE | PARTIAL (measurement_class string) | PRESENT | PRESENT (entity_class) | ABSENT |
| Experiment minting | PRESENT (copied) | ABSENT | PRESENT (copied) | PRESENT (controlled, same list on every case of a sweep) | ABSENT | PRESENT on the entity; NOT READ by any branch | PRESENT (co-determined with the count) | ABSENT | ABSENT | PARTIAL (measurement_class) | PRESENT | PRESENT (gates minting) | ABSENT |
| resolved output | PRESENT | ABSENT | OVERWRITTEN (tag_experiments stamps the paper value on every experiment) | PRESENT | ABSENT | PRESENT | PRESENT | ABSENT | ABSENT | PARTIAL | PRESENT | PRESENT | ABSENT |
| canonical | ABSENT (no material field) | ABSENT | ABSENT (no geometry field) | PARTIAL (context_available quantities) | ABSENT | PARTIAL (granularity.resolved_representation, a different notion) | ABSENT | ABSENT | ABSENT | ABSENT | PRESENT (figure/panel/series/json_pointer) | PRESENT (source.data_source) | PRESENT (transformations, projections, derived_from_value) |
| KG (full) | PRESENT (Material node + deposits) | ABSENT | ABSENT (full KG has no geometry node) | PRESENT (ConditionAssertion 3451) | ABSENT | PRESENT (PlotSeries attribute; represents_same_as 64 with entity->own-PlotSeries endpoints) | PRESENT (case_status node attribute) | ABSENT | ABSENT | PARTIAL (measurement_class attribute) | PRESENT (Figure nodes, shown_in) | PRESENT (SimulationRun/ModelSweep nodes) | PRESENT (TransformationExecution 2126) |
| KG (core) | PRESENT | ABSENT | PRESENT (GeometryClass node + geometry edge) | PRESENT (fixed_conditions attribute) | ABSENT | PRESENT (ResultSeries.representation) | ABSENT | ABSENT | ABSENT | PRESENT (ResultSeries.measurement_class) | PRESENT (source_figure, panel) | PRESENT (ResultSeries.source, falls back to 'unknown') | PARTIAL (canonical_curve_ids) |


## The four loss points this matrix exposes

1. **Sample and run evidence** — PRESENT at resolver pre-classification (`SAMPLE_ID` fires
   on 268 entities across 24 papers), **DISCARDED** at the entity dict. `to_kb.py:968-1035`
   copies `cls["signal_families"]` (letters) and `cls["classification_evidence"]` (4 strings)
   but not `cls["signals"]`, `cls["supported_setting_count"]` or
   `cls["supported_setting_evidence"]`. Corpus check: none of those three keys appears on
   any of the 1044 entities.

2. **Geometry** — PRESENT per entity from `_geom_for`, then **OVERWRITTEN** at the resolved
   output by `geometry.tag_experiments` (`geometry.py:263`), which writes one paper value
   onto every experiment record with `"planar"` as the literal default.

3. **Measurement conditions** — **ABSENT at every stage.** No field distinguishes an
   instrument setting from a deposition setting. `recipe_role` is per QuantityKind
   (corpus-wide, one role per quantity); `evidence_kind` separates model inputs and
   cited-work values, not measurement settings; `axis_role` types the axis, not scalars.

4. **Material role** — **ABSENT at every stage.** `material` is a single string.
   `scripts/audit_exact_overlap.py` reconstructed deposited-vs-substrate by hand for 21
   candidate papers into `reports/exact_overlap_audit.json`; that is an audit artifact, not
   a pipeline input.

## Two additional observations from the matrix

- **Representation** is PRESENT from figure extraction through the KG and is read by no
  minting branch. The canonical layer's `granularity.resolved_representation` is a
  *different* notion (profile / single / series / correlation), not the
  as-measured/scaled/normalized axis.
- **Material and geometry are both ABSENT from canonical.** Any change to how they attach
  cannot break the canonical layer, because canonical never reads them.
