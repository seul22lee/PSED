"""
run_all.py  (Phase C4)  — end-to-end pipeline orchestrator
----------------------------------------------------------
One command from PDF to conformance dashboard. Wires the reused parsing stages
(0604_kg: 01–05) and the ontology-grounded stages (0706_pipeline: s06–s09), then
rebuilds the dashboard.

  python3 run_all.py            # extraction + KG + dashboard (parsing already done)
  python3 run_all.py --parse    # also run 01–05 (docling…enrich) for NEW pdfs in 0604_kg/pdf
  python3 run_all.py --from s07 # resume from a given stage

s07 makes LLM calls (needs GOOGLE_API_KEY); it skips figures already extracted.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent          # 0706_pipeline
REPO = ROOT.parent
KG = REPO / "0604_kg"
STAGES = ROOT / "stages"

# (label, script, cwd)
PARSE = [("01 docling", "01_docling_extract.py", KG), ("02 figure-filter", "02_figure_filter.py", KG),
         ("03 plot-to-data", "03_plot_to_data.py", KG), ("04 formulas", "04_formula_to_data.py", KG),
         ("05 enrich-figures", "05_enrich_figures.py", KG)]
EXTRACT = [("s06 study-profile", "s06_study_profile.py", STAGES), ("s07 experiment (LLM)", "s07_experiment.py", STAGES),
           ("s08 resolve/granularity", "s08_resolve.py", STAGES), ("s09 knowledge-graph", "s09_kg.py", STAGES)]
DASH = [("dashboard", "build_dashboard.py", ROOT)]
ORDER = PARSE + EXTRACT + DASH
KEYS = [s[1].split(".")[0].split("_")[0] for s in ORDER]  # 01,02,...,s06,s07,...,build


def run(label, script, cwd):
    print(f"\n{'='*60}\n▶ {label}   ({cwd.name}/{script})\n{'='*60}")
    subprocess.run([sys.executable, script], cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parse", action="store_true", help="also run 01-05 (docling) for new PDFs")
    ap.add_argument("--from", dest="frm", default=None, help="resume from a stage key (e.g. s07)")
    a = ap.parse_args()
    stages = ORDER if a.parse else (EXTRACT + DASH)
    if a.frm:
        keys = [s[1].split(".")[0] for s in stages]
        idx = next((i for i, k in enumerate(keys) if k.startswith(a.frm)), 0)
        stages = stages[idx:]
    for label, script, cwd in stages:
        run(label, script, cwd)
    print("\n✓ pipeline complete → 0706_pipeline/experiment_dashboard.html + output/knowledge_graph_onto.json")


if __name__ == "__main__":
    main()
