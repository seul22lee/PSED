# Incidental findings — nine-paper pilot

Recorded, not fixed. None is in scope.

| # | where | observation | affected the pilot? |
|---|---|---|---|
| 1 | `cremers2019` resolved entities vs canonical curves | **9 of 86 model entities carry a curve `data_source` that is not `simulated`** — 3 empty and 6 `measured`, including one panel where the series labelled "Simulation" and the series labelled "Experiment" are BOTH marked `measured`. The resolver's entity class and the canonical layer's panel-source flag disagree. | Surfaced, not silenced. The pilot preserves `data_source` bit-identically (invariant 13 passes) and keeps the entity classes; the disagreement is visible in the model-branch view. |
| 2 | `cremers2019` `extracted/geometry.json` | The paper has **no `geometry_class` at all**. Production's `tag_experiments` would stamp the literal default `"planar"`; the pilot instead reads `porous_material` and `lateral_channel` from individual figure captions. | No — the pilot's figure-scope geometry covered it. |
| 3 | corpus-wide | **Only 10 of the 40 candidate papers have a local PDF.** The other 30 exist solely as Docling output and cannot be ground-truth reviewed. | Yes — it constrained the selection pool. See `scope_escalations.md` E1. |
| 4 | `selection/candidate_matrix.csv` | The `imported_literature` column sums entity counts AND text mentions, which made `10.1021_acs.langmuir.6b03119` look like it carried imported literature when it has none. | Yes — it misdirected one of five selection slots. Corrected in `selection/selected_5.md` rather than hidden. |
| 5 | production `pipeline/canonical/conditions.py` | Still reads a range separator as a minus sign (`"10-120 ms"` → −120 ms). The pilot repairs it downstream. | No — repaired by `pilot_ranges`. |
| 6 | production `pipeline/figures/inventory.py` | `_PANEL_HEAD` still rejects the spaced parenthetical `( a )`. | No — the pilot's own parser accepts it. |
| 7 | `10.1039_d0ra09876k` | Cases carry both `pulse_time = 10 s` (no species) and `pulse_time = 30 s (H2O)`. The species-less entry is ambiguous — it is probably the precursor pulse but the source does not say. | Minor. Both are kept with their species field; nothing is merged across them. |
