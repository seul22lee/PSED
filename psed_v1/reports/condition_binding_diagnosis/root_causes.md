# Root causes

Frequencies are from the **seeded random sample only** (n = 120, seed 20260803).
Targeted-case findings are reported separately and are NOT mixed in.

| code | cause | n | share | 95 % CI | responsible code |
|---|---|--:|--:|---|---|
| **P** | Curve point incorrectly promoted to Experiment | 44 | 36.7 % | 28.6–45.6 % | `06_to_kb.py::split_condition_series` |
| — | no failure detected | 31 | 25.8 % | 18.8–34.3 % | — |
| **S** | Model / simulation data stored as Experiment | 17 | 14.2 % | 9.0–21.5 % | `06_to_kb.py::to_experiments` |
| **I** | Hidden / replaced by fallback or dedup | 9 | 7.5 % | 4.0–13.6 % | `06_to_kb.py::_dedup_pressures` |
| **C** | Wrong quantity classification / axis role unresolved | 8 | 6.7 % | 3.4–12.6 % | `canonical/axis_semantics.py::resolve_x_axis` |
| **J** | Incorrect paper-level broadcast | 5 | 4.2 % | 1.8–9.4 % | `10_pressure.py::pressure_facts` + `06_to_kb` `base_ctrl` |
| **A** | Mention not extracted | 4 | 3.3 % | 1.3–8.3 % | `05_figure_extract.py::VISION_SCHEMA` |
| **H** | Field dropped downstream | 2 | 1.7 % | 0.5–5.9 % | `06_to_kb.py::to_experiments` |

Categories **D, F, K, L, Q, R, T, U, V, W** were *looked for and not found* as a
first-failure cause in the random sample. **R** (literature attributed to the current
paper) and **F** (source identity lost) DO occur, but always downstream of **S**.

## P — point-level over-splitting (dominant, 36.7 %)

`06_to_kb.py::split_condition_series` turns every point of a condition-axis curve
into an `Experiment`. The rule is right in principle and wrong in practice because
**the point count reflects digitiser density, not the number of depositions**.

`05_figure_extract.py::VISION_SCHEMA` instructs:

> "For each series, read approximately **50 points** evenly spaced across the curve's
> full x-range … If the curve has fewer than ~50 visible markers, read every marker."

Worked example — `10.1002_pssa.201532305` Fig. 4:

* caption: *"Film growth (obtained by **in-situ SE**) versus different deposition parameters"*
* one continuous ellipsometry trace per curve; x = elapsed exposure (min)
* digitised at 19–25 points → **19–25 `Experiment` records per curve**; 10 curves → 232 records
* the paper actually ran **10 depositions** for that figure

The ontology already warns about exactly this (`01_ontology/core.yaml`, immediately
above `axis_role`):

> "NOTE ambiguous: cycle_number / time can be either (one monitored run vs separate
> depositions) → extractor should check whether other conditions also differ across
> points before splitting."

The warning was never implemented. **The discriminator is continuous-trace vs
discrete-runs, not the x-axis quantity.**

Splitting IS correct for genuine sweeps — verified: `10.1116_6.0002804` Fig. 1
("GPC … as a function of **independently varied** MoCl2O2 pulse time");
`10.1039_d3dt01824e` Fig. 4 (GPC vs deposition temperature, 6 points, 6 depositions).

## S — model/simulation records stored as Experiments (14.2 %)

335 / 2457 population records (13.6 %) carry `relevance="model"` /
`is_model_result=True` and are still written to `resolved/experiments.json` and
instantiated as `Experiment` nodes by `build_kg.py`.

`10.1016_j.sse.2022.108584` is **74/74 model** — including the `Arts 2019, 310 °C`
series, which is *imported literature experimental data*, not a model output. The
whole-figure `source` flag overrides per-series identity, so a measured-vs-simulated
comparison figure collapses to one class. Category **S**, with **R** downstream.

## I — dedup hides the narrower-scope value (7.5 %)

`06_to_kb.py::_dedup_pressures` keeps the `source=="pressure_extraction"` (paper
scope) value and drops any other pressure matching within 1 %:

```python
if (c.get("source") != "pressure_extraction" and q in _PRESSURE_Q
        and isinstance(v, (int, float)) and _matches_ext(v)):
    continue                      # ← the caption/panel-scope value is dropped
```

Verified on `10.1002_pssa.201532305` Fig. 4, caption *"Standard parameter values:
0.01 mbar of pressure, 325 °C …"*:

1. `records.json` → `controlled = {"pressure": "0.01 mbar", "temperature": "325 °C"}` ✓
2. `_num_cond("pressure","0.01 mbar")` → `generic_pressure = 1.0 Pa`, source `caption` ✓
3. `_dedup_pressures` drops it (paper-scope extraction also has `1.0 Pa`)
4. the surviving paper-scope `generic_pressure` has **3 distinct values** (1, 100, 1000 Pa)
   → `context_status = ambiguous`
5. **net: no usable pressure, although the caption states it unambiguously**

Temperature from the same caption survives (no dedup rule applies), which is exactly
why `temperature 325 °C scope=figure` is present and pressure is not. Category **I**,
compounded by **J**.

## J — paper-level broadcast (4.2 % first-cause; 32.5 % of records affected)

`geometry.json` and `pressure.json` attach to **every** experiment in a paper at
`scope="paper"`. In `10.1016_j.sse.2022.108584` the Fig. 2 geometry (`d = 1 µm`,
`L = 100 µm`) plus all Table-1 fitted parameters (4 evaporation fluxes, 7 sticking
coefficients) land on the Fig. 4 `Arts 2019` record, whose real geometry is
`d = 0.5 µm`, `L = 5000 µm` (stated in `document.md`).

The ambiguity flagging *detects* this (852 records carry `context_conflicts`) but
does not *prevent* attachment, and cannot pick the right value because no
figure-scoped alternative was ever extracted.

## B / N — schema cannot carry what the text already says

* `figure_data.panels[].conditions{}` is the **only** structured condition channel and
  is filled at the model's discretion. Captions carrying `s0`, `Γ0`, `pA0`, `pB`
  produced `conditions = {}` — 471 records affected (targeted set).
* One `y` per panel: SSE Fig. 5a gives `Gamma_ev` the measurand `ln(beta_0)`;
  Fig. 5b gives `theta_sat` and `SC_sat` the measurand `pulse_time [s]`. Three
  physically different outputs, one label. Category **N**.
* No slot for *estimated* / *assumed model input* / *literature-derived* values, so
  `pA = 325 mTorr (estimated)` has nowhere to go even if parsed.

## Hypotheses rejected

* **"Plot digitisation is broken."** Rejected. Every label, caption and axis needed
  for both case studies is present in `figure_data.json`. **0/120** sampled records
  need re-digitisation (95 % CI [0 %, 3.1 %]).
* **"Figure identifier mismatch (L) causes condition loss."** The dual identifier
  (`fig_docling_index` vs `figure_number`) is real and confusing, but every join in
  the live path uses `fig_docling_index` consistently. **0** first-failures in the
  sample. A latent hazard, not a current cause.
* **"Conditions are missing because captions were not captured."** Rejected. Captions
  are captured in full; they are simply never parsed for anything beyond the
  model-selected `conditions{}` dict.
