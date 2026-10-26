# Reproducing the results

Base: Larry's ReactionModel.ipynb (cells 71-86, `original/`), extracted to `reaction_model.py`; every change since is one row in `CHANGELOG.md` and one git commit.

## 1. Setup
This folder lives in the psed repository (`psed_v2/dt`); the scripts read the knowledge base from `psed_v2/kb` by default.
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: another KB checkout
# export PSED_KB=/path/to/psed_v2/kb
# export PSED_YLI18_FIGURES=$PSED_KB/10.1063_1.5028178.figures.json
```
KB files read: `kb/*.figures.json` (digitized curves). Reported c values used in figure panel c are from `kb/pilot/sticking_reported.csv` (yli18 5.72e-3, yim20 4e-3 and 3e-4), written into `figures/fig_dt_kb_control.py`.
The committed results were produced against the KB at commit ba77854; later KB updates changed some digitized curves slightly.
`fitting/waldo_pressure_fit.py` needs `WALDO_PRESSURE` (collaborator data, not in the repository); it is not part of `run_all.sh`.
The figure PDF is not tracked (the repository ignores `*.pdf`); `python figures/fig_dt_kb_control.py` writes it next to the PNG.

## 2. Run everything
```bash
./run_all.sh          # about 15 min on 2 CPU cores (after C9, C10, A8)
```
Committed `.json` outputs let you skip steps: e.g. only `python figures/fig_dt_kb_control.py` redraws the figure from them.

## 3. What each step produces
| step | script | output | model | data |
|---|---|---|---|---|
| tests | `tests/` | 12 pass, 1 strict xfail | ChannelModel, yli18_approx | KB yli18 curves |
| A4 | `fitting/campaign_groupA.py`, `campaign_ticl4_K.py` | `campaign_groupA.json`, `campaign_ticl4_K.json` | `yli18_approx.py` (yli18 analytic) + `slope_method.py` | KB curves of yli18, yim20, gao15 (real) |
| A5 | `demo/dt_recipe_correction.py` | `dt_recipe_correction.json` | Larry reactor model + ChannelModel | synthetic reactors A, B |
| A6 | `demo/dt_qcm_calibration.py` | `dt_qcm_calibration.json` | Larry reactor model (one BDF call per pulse, C9) + FlatModel; recipe via reactor model | synthetic QCM signal of reactor B |
| A6b | `demo/dt_qcm_fullchain.py` | adds `front_full` to the A6 json | reactor model + ChannelModel | synthetic |
| F2 | `figures/fig_dt_kb_control.py` | `fig_dt_kb_control.pdf/.png` | reads the json files above | — |

Figure panels: a concept; b illustration (no model-selection code yet); c, d real KB data; e-g synthetic reactor B (truth eta 0.6, beta_wall 2e-3 set by hand), QCM dose series in ng/cm2 scaled with the saturated TMA step of the WALDO 7/02 run.

## 4. Expected numbers (check against your run; TMA irreversible, A7)
- A4: yli18 Fig. 6 joint c 7.5e-3, pA0 111 Pa (TiCl4 rows keep K; out of scope).
- A5: reactor A tuned pulse 0.308 s -> 98.8 um; same pulse in B -> 63.3 um; chip-calibrated recipe 0.751 s -> 106.4 um.
- A6 (c = 4e-3): eta 0.535, beta_wall 1.75e-3, pulse 0.728 s -> 104.8 um (full chain).
- A6b: c 2e-3 -> 93.9 um; c 8e-3 -> 197.6 um (A6 is no longer in the figure).
- A11 (figure e-g): eta 0.584, beta_wall 2.13e-3, pulse 0.663 s -> 100.0 um; c 2e-3 -> 83.2 um; c 8e-3 -> 115.8 um.
- A9: TMA 0.663 s / purge 1.2 s / H2O 0.72 s / purge 1.3 s (purges = gas-transport lower bound).
Random noise is seeded (A5 seed 0, A6 seed 1).
