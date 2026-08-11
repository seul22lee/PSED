"""
bench_process_id.py — paper-aligned process-IDENTIFICATION benchmark
(reproduces the RSI 2026 Table VI task with our KB-grounded identifier).

Task (per Paper 2, Sec. IV.B): given a target material + the installed reactor
channels, return an Argonne-style JSON process {possible, precursor, coreactant,
ncycles} with **0-indexed channel numbers**, and score it 0–1 against a known
correct answer with their rubric:
  · not valid JSON                      -> 0
  · wrong channel (precursor/coreactant)-> 0
  · channels right, ncycles wrong       -> relative-error score
  · sequence correct                    -> 1
  · (impossible task) predict possible=0 -> 1 if truly impossible, else 0

We report our KB-grounded process_id.py with CITATIONS, and compare ONLY to the
LLM scores **reported in Paper 2 Table VII** (not rerun here). Ground-truth answers
are assigned from standard ALD chemistry; the channel configs follow Table VI's
common set. This is a faithful reconstruction — the paper's exact 30-challenge list
+ answers live in its supplementary material (transcribe from SI to grade all 30).

Run:  python3 eval/bench_process_id.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# psed_v1 is self-contained: ordinary package imports below.
from pipeline.resolve import process_id

# The common Table VI reactor configuration (0-indexed channels):
CFG = ["TMA", "water", "DEZ", "TDMAHf", "Si2H6", "WF6", "TTIP", "MgCp2"]
#        0       1       2      3         4        5      6       7

# challenges: (material, ncycles, config, ground-truth {possible, precursor_ch, coreactant_ch})
# ground truth from standard ALD chemistry (oxides via H2O; W via WF6/Si2H6 reduction).
CHALLENGES = [
    ("Al2O3", 200, CFG, {"possible": 1, "precursor": 0, "coreactant": 1}),   # TMA + water
    ("ZnO",   200, CFG, {"possible": 1, "precursor": 2, "coreactant": 1}),   # DEZ + water
    ("HfO2",  300, CFG, {"possible": 1, "precursor": 3, "coreactant": 1}),   # TDMAHf + water
    ("TiO2",  250, CFG, {"possible": 1, "precursor": 6, "coreactant": 1}),   # TTIP + water
    ("W",     300, CFG, {"possible": 1, "precursor": 5, "coreactant": 4}),   # WF6 + Si2H6 (reducer)
    ("MgO",   350, CFG, {"possible": 1, "precursor": 7, "coreactant": 1}),   # MgCp2 + water
    # infeasible on this reactor (no compatible precursor installed):
    ("Fe2O3", 200, CFG, {"possible": 0}),                                    # no Fe precursor
    ("Ru",    200, CFG, {"possible": 0}),                                    # no Ru precursor
    ("Er2O3", 350, CFG, {"possible": 0}),                                    # no Er precursor
    ("SrTiO3",300, CFG, {"possible": 0}),                                    # no Sr precursor
    # variant config that DOES install the right precursor:
    ("TiO2",  250, ["TiCl4", "water", "TMA", "O3"], {"possible": 1, "precursor": 0, "coreactant": 1}),
    ("Al2O3", 200, ["DEZ", "TMA", "water", "WF6"], {"possible": 1, "precursor": 1, "coreactant": 2}),
]

# LLM scores REPORTED in Paper 2, Table VII (process identification, no background).
# NOT rerun here — shown for reference only.
PAPER_TABLE_VII = {"GPT-3.5": 0.39, "GPT-4o": 0.72, "o1": 0.94, "o3": 0.96, "GPT-5": 0.93,
                   "Claude Sonnet 4": 0.85, "Claude Opus 4": 0.93, "Claude Sonnet 4.5": 0.78,
                   "Gemini 2.5 Flash": 0.84, "average(reported)": 0.82}


def predict(material, ncycles, config):
    """Run our KB-grounded identifier; return 0-indexed Argonne JSON + provenance."""
    cands = process_id.identify(material, config)
    top = cands[0] if cands else None
    if not top:
        return {"possible": 0, "precursor": None, "coreactant": None, "ncycles": ncycles,
                "source": "none", "citations": []}
    arg = top["argonne"]                      # 1-indexed from resolve_channels
    out = {"possible": arg.get("possible", 0), "ncycles": ncycles,
           "precursor": (arg["precursor"] - 1) if arg.get("precursor") else None,
           "coreactant": (arg["coreactant"] - 1) if arg.get("coreactant") else None,
           "source": top["source"], "citations": top["papers"],
           "precursor_species": top["precursor"], "coreactant_species": top["coreactant"]}
    return out


def score(pred, truth):
    """Paper 2 0–1 rubric."""
    if not isinstance(pred, dict):
        return 0.0                                     # not valid JSON
    if truth["possible"] == 0:
        return 1.0 if pred.get("possible") == 0 else 0.0
    if pred.get("possible") == 0:
        return 0.0                                     # said impossible when it's possible
    if pred.get("precursor") != truth["precursor"] or pred.get("coreactant") != truth["coreactant"]:
        return 0.0                                     # wrong channel
    return 1.0                                         # channels (and echoed ncycles) correct


def run():
    rows = []
    for material, ncy, cfg, truth in CHALLENGES:
        pred = predict(material, ncy, cfg)
        rows.append({"material": material, "ncycles": ncy, "config": cfg, "truth": truth,
                     "pred": pred, "score": score(pred, truth)})
    total = sum(r["score"] for r in rows) / len(rows)
    result = {"benchmark": "RSI-2026 Table VI (reconstructed subset)",
              "n_challenges": len(rows), "our_score": round(total, 3),
              "rows": rows, "reported_llm_table_vii": PAPER_TABLE_VII}
    (ROOT / "eval" / "process_id_results.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def report(r):
    print("=" * 78)
    print("PROCESS-IDENTIFICATION BENCHMARK  (RSI 2026 Table VI, reconstructed subset)")
    print("=" * 78)
    print(f"{'material':8} {'truth':>14} | {'our prediction':>26} | score | source/cite")
    print("-" * 92)
    for row in r["rows"]:
        t = row["truth"]; p = row["pred"]
        tstr = "impossible" if t["possible"] == 0 else f'ch {t["precursor"]}+{t["coreactant"]}'
        if p.get("possible") == 0:
            pstr = "impossible"
        else:
            pstr = f'{p.get("precursor_species")}({p.get("precursor")})+{p.get("coreactant_species")}({p.get("coreactant")})'
        cite = ",".join(p["citations"]) if p["citations"] else p["source"]
        print(f"{row['material']:8} {tstr:>14} | {pstr:>26} | {row['score']:.1f}   | {cite}")
    print("-" * 92)
    print(f"\nOUR KB-grounded process_id:  {r['our_score']:.2f}  (0–1, {r['n_challenges']} challenges)")
    print("Reported LLM scores (Paper 2 Table VII, process-ID, NOT rerun here):")
    for m, s in r["reported_llm_table_vii"].items():
        print(f"    {m:20} {s:.2f}")
    print("\nnote: same 0–1 rubric; our score is on a reconstructed subset, so it is")
    print("      indicative — not a like-for-like number vs their full 30-challenge set.")
    print("saved → eval/process_id_results.json")


if __name__ == "__main__":
    report(run())
