#!/usr/bin/env bash
# Reproduce every result and the paper figure (F2). Can be run from any directory.
# Reads the PSED knowledge base from ../kb (psed_v2/kb) unless PSED_KB is set.
set -euo pipefail
cd "$(dirname "$0")"
export PSED_KB="${PSED_KB:-$(cd ../kb && pwd)}"
export PSED_YLI18_FIGURES="${PSED_YLI18_FIGURES:-$PSED_KB/10.1063_1.5028178.figures.json}"
step() { echo; echo "== $1"; }
step "tests (about 3 min)";                         python -m pytest -q tests
step "A4 literature fits, 17 curves (about 8 min)"; python fitting/campaign_groupA.py
step "A4 TiCl4 with K free (about 5 min)";           python fitting/campaign_ticl4_K.py
python fitting/plot_groupA.py
step "A5 two reactors + test chips (about 1 min)";  python demo/dt_recipe_correction.py
python demo/plot_dt_demo.py
step "A6 QCM calibration, 3 assumed c (about 2 min)"; python demo/dt_qcm_calibration.py
step "A6b full-chain check (about 1 min)";           python demo/dt_qcm_fullchain.py
python demo/plot_dt_qcm.py
step "A11 QCM dose series (about 3 min)";         python demo/dt_qcm_doseseries.py
step "A9 full recipe (about 4 min)";               python demo/dt_full_recipe.py
step "A14 QCM identifiability with desorption (about 2 min)"; python fitting/qcm_sticky_identifiability.py
step "F2 paper figure";                              python figures/fig_dt_kb_control.py
echo; echo "done: figures/fig_dt_kb_control.pdf"
