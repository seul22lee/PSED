# Condition flow trace (live code path)

Every edge below was verified by running the live code, not by reading names.

```
document.md / caption / series label / table
   │
   │  03_corpus/scripts/05_figure_extract.py :: VISION_SCHEMA          [LLM, vision]
   │    OUT: figure_data.json
   │      figures[].caption                      ← full caption text PRESERVED
   │      figures[].panels[].x/y {quantity,unit} ← PANEL-level only (one y per panel)
   │      figures[].panels[].series_axis         ← name of the distinguishing variable
   │      figures[].panels[].series[].label      ← verbatim curve label PRESERVED
   │      figures[].panels[].conditions{}        ← "NUMERIC process conditions" — the
   │                                               ONLY structured condition channel
   ▼
figure_data.json
   │  05_figure_extract.py :: flatten → records.json
   │    controlled = panels[].conditions (copied verbatim, unchanged)
   │    series_axis / series_value / series_kind / series_value_num / series_unit
   ▼
records.json
   │  03_corpus/scripts/06_to_kb.py :: to_experiments()
   │    panel_ctrl  = [_num_cond(k,v) for k,v in r["controlled"].items()]      L636-638
   │    series_ctrl = ONLY when series_kind=="numeric_sweep"                   L640-650
   │    base_ctrl   = paper_conditions(card) + geometry_facts(sd)              L611-613
   │    press_ctrl  = pressure10.pressure_facts(sd, reactants)                 L621
   │    controlled  = _dedup_pressures(base+panel+series+press)                L659
   │    granularity = clive.axis_granularity(coordinate, len(points))          L655
   ▼
resolved/experiments.json  +  resolved/series.json
   │  06_to_kb.py :: split_condition_series()   ← condition axis ⇒ 1 exp / point
   ▼
02_extraction/recipe.py :: from_experiment()   → recipe{} on each experiment
02_extraction/build_kg.py                      → knowledge_graph_onto.json
02_extraction/canonical/build_canonical.py     → canonical/curves.json
```

## Fields copied / transformed / discarded at each edge

| edge | copied | transformed | **discarded** |
|---|---|---|---|
| caption → `figure_data.conditions{}` | numeric process conditions the model chose | — | **everything the model did not select**: `s0`, `Γ0`, `pA0`, `pB`, geometry stated in prose, "fictitious chemistry" |
| `figure_data` → `records.json` | `conditions` verbatim, series label + parsed numeric | — | nothing |
| `records.json` → `experiments.json` | `controlled` via `_num_cond` | value+unit normalised | **non-numeric conditions** (`_num_cond` returns None unless the value fully matches `^num unit$`); **categorical `series_kind`** never yields a condition |
| paper scope → every experiment | `card` + `geometry.json` + `pressure.json` | — | scope specificity: one figure's geometry reaches every figure |
| `_dedup_pressures` | paper-scope pressure | — | **the narrower caption/panel-scope pressure** (see `pressure_flow_trace.md`) |

## Verified: extraction is NOT the main failure

For `10.1016_j.sse.2022.108584` the vision stage preserved every label and caption
needed (`03_corpus/extracted/10.1016_j.sse.2022.108584/figure_data.json`):

* `Fig. 2` caption carries `d = 1μm`, `L = 100μm`, `s0 = 2 × 10-19 m2`, `Γ0 = 10^24 m-2 s-1`, "fictitious chemistry";
* `Fig. 4` labels carry `Arts 2019, 310 °C` … `Model, 150 °C`;
* `Fig. 6` labels carry `Yim and Ylivaara 2020, t_p = 0.2 s`;
* `Fig. 7` labels carry `d = 2.0 µm`, `d = 0.5 µm`, `d = 0.1 µm`.

Yet **`conditions` is `{}` for every one of those panels.** The information is
present as text and absent as structure. That is failure category **B**, not **A**.

## First-loss points (deep case studies)

| condition | present in | first absent in | code |
|---|---|---|---|
| SSE Fig.2 `s0`, `Γ0`, fictitious chemistry | caption | `figure_data.conditions{}` | `05_figure_extract.py::VISION_SCHEMA` |
| SSE Fig.4 legend temperatures | `series[].label`, `series_name` | `experiments.controlled` | `06_to_kb.py::to_experiments` — `series_ctrl` only fires for `series_kind=="numeric_sweep"`; a label like `Arts 2019, 310 °C` is `categorical`, so **no condition is emitted at all** |
| SSE Fig.4 `750 mTorr·s`, `400 cycles`, `1.12 Å/cycle` | `document.md` | never structured | no figure-linked-text parser exists |
| SSE Fig.5a/5b per-series y quantity | `series[].label` | `figure_data.panels[].y` | **schema**: one `y` per panel (category N) |
| SSE Fig.6 `pA = 325 mTorr` (estimated) | `document.md` | `pressure.json` (empty) | `10_pressure.py` |
| D0CP `3 hPa` process pressure | `document.md` methods | `pressure.json` (empty), `card.pressure_Pa = null` | `10_pressure.py`, `04_extract.py METHODS_SCHEMA` |
| D0CP Fig.10 `pA0 = 65 Pa`, `pB = 300 Pa (N2)` | caption | `figure_data.conditions{}` (kept only `cycle_number`,`temperature`,`pulse_time`) | `05_figure_extract.py::VISION_SCHEMA` |
| D0CP Fig.11 `of_reactant = A` on TMA pulse time | caption "different TMA pulse times" | `experiments.controlled[].of_reactant = None` | `06_to_kb.py::_ctrl` (no reactant inference from `series_axis`) |

## Confirmed working

* D0CP Fig. 11 `pulse_time` and `purge_time` **do** bind at experiment scope from the
  series label (`series_kind=="numeric_sweep"` path works when the label is a bare number).
* D0CP Fig. 10 caption `cycle_number=500`, `temperature=300 °C`, `pulse_time=0.10 s`
  **do** reach the record at figure scope.
