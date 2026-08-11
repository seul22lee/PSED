# Simulation path — why it works (preservation target)

## Chain

```
figure_extract.panel_source_for(fr, panel_label)          figure_extract.py:367-387
    -> figure_data.json  figures[].panel_source{<panel>: measured|simulated, _fig: ...}
    -> to_kb._entity_context  ctx["panel_source_flag"], ctx["figure_source_flag"]   L576-577
    -> csid.resolve_panel(labels, caption, figure_source_flag)                      L856
    -> entities.classify -> "simulation" | "model_sweep"                            L375-425
    -> ENTITY_CLASS -> "SimulationRun" | "ModelSweep";  CLASS_MODEL case=0, is_experiment=False
    -> entity written; NO case minted (L1039 gate)
    -> build_canonical: source.data_source = panel_source or source
    -> build_kg: _ENTITY_NODE -> SimulationRun / ModelSweep nodes
    -> twin: absent (twin reads experiments.json, which never contains them)
```

## The mechanisms that prevent silent default-to-measured

1. **`panel_source_for` never defaults** (`figure_extract.py:367-387`):
   panel evidence -> `_fig` -> unanimous drilled panels -> figure `source` -> `"unresolved"`.
   `"both"` is deliberately not a valid stand-in. This is the B2 fix.
2. **`data_source` is copied, not inferred**: `build_canonical.py` sets
   `source.data_source = c.get("panel_source") or c.get("source")` — no fallback literal.
3. **Class-level exclusion**: `CLASS_MODEL["simulation"]` and `["model_sweep"]` have
   `case: 0, is_experiment: False`, so the L1039 branch is never entered.
4. **`entities.py:424-425`**: a `simulation` whose coordinate is not a spatial/time axis is
   demoted to `model_sweep`, keeping profile-shaped and sweep-shaped model output apart.
5. **Voting**: simulation votes come from the series label (`SIM_LABEL`), the panel/figure
   source flag, `is_model_result`/`relevance == "model"`, and body text — four independent
   families (`entities.py:375-397`).

## Does `SimulationRun` share code with `Experiment`?

Yes, up to the point of minting. Both run through the same `resolve_source_entities` loop,
the same `_entity_context`, the same axis/granularity resolution, the same
`assign_experiment_ids` (so a simulation entity also gets a `pid__Fig10a` id), the same
condition binding, and the same `entity_key`.

They diverge at exactly two places:

| divergence | line |
|---|---|
| `if model["is_experiment"]` — case counting | `to_kb.py:1039` |
| `if model["is_experiment"] and n_cases >= 1` — case records | `to_kb.py:1127` |

Both are driven by `CLASS_MODEL[classification]["is_experiment"]`, a static table
(`entities.py:629-655`).

**Implication for reconnaissance:** any change to the shared prefix — `entity_key`,
`assign_experiment_ids`, `_events` grouping, condition binding — reaches simulation entities
too, because they are ordinary entities. Only the two `is_experiment` gates are
simulation-safe boundaries.

## Yim Fig 10 (`10.1039_d0cp03358h`)

31 of 70 entities are `SimulationRun`. Corpus totals: `SimulationRun` 112, `ModelSweep` 95.
The paper's MATLAB re-implementation of the Ylilammi model is classified `simulation`, mints
no case, and appears in canonical with `data_source = "simulated"`.

## Tests protecting this

| test | protects |
|---|---|
| `tests/regression/test_figure_provenance.py` | the panel-source provenance resolution and the corpus DRILL anchor |
| `tests/regression/test_provenance.py` | paper-card field provenance, window-not-endpoint |
| `tests/canonical_layer/test_provenance.py` | canonical transformation/provenance chain |
| `tests/regression/test_twin_validation.py` | `STATUS` closed set, 6 explanatory loci |
