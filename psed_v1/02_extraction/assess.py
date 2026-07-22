"""
assess.py — exercise the KB the way a researcher would: inspect extraction,
query by material+condition, compare experiments, and test cross-experiment
linking. Prints real results from the current resolved corpus + KG.
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent
def load():
    exps = []
    for d in sorted((ROOT / "output").glob("*/resolved/experiments.json")):
        pid = d.parent.parent.name
        for e in json.loads(d.read_text()):
            e["_pid"] = pid; exps.append(e)
    return exps
E = load()

def conds(e):
    return {c["quantity"]: c.get("value") for c in e.get("controlled", []) if c.get("quantity")}

print(f"corpus: {len(E)} experiments across {len({e['_pid'] for e in E})} papers\n")

# 1) EXTRACTION — one full record
print("="*70, "\n1) EXTRACTION — is a record complete & correct?")
e = next(x for x in E if x["_pid"] == "arts2019" and x["granularity"] == "profile")
print(f"  [{e['_pid']}] series='{e['series_name']}'  material={e['material']}  structure={e['structure']}")
print(f"  process={e['process_type']}  relevance={e['relevance']}  is_model={e['is_model_result']}")
print(f"  VARIES (x-axis): {e['varies']}   MEASURES (y): {[d['quantity'] for d in e['dependent']]}")
print(f"  CONDITIONS: {[(c['quantity'], c.get('value'), c.get('unit')) for c in e['controlled']]}")
print(f"  data points: {len(e.get('points') or [])}   source: {(e.get('provenance') or {}).get('figure_id')}")

# 2) QUERY — material X AND has pulse_time, sorted
print("="*70, "\n2) QUERY: experiments with material=Al2O3 AND a pulse_time, sorted by pulse_time")
hits = [(conds(x).get("pulse_time"), x) for x in E
        if x["material"] == "Al2O3" and "pulse_time" in conds(x) and conds(x)["pulse_time"] is not None]
for pt, x in sorted(hits, key=lambda h: h[0])[:8]:
    print(f"   pulse_time={pt:>5} s | {x['_pid']:12} '{x['series_name']}' | exposure={conds(x).get('exposure')} Pa·s")
print(f"   ({len(hits)} experiments match)")

# 3) COMPARE two experiments side by side
print("="*70, "\n3) COMPARE two experiments (shared quantities aligned)")
a, b = hits[0][1], hits[-1][1]
keys = sorted(set(conds(a)) | set(conds(b)))
print(f"   {'quantity':26}{'A: '+a['series_name'][:16]:>20}{'B: '+b['series_name'][:16]:>20}")
for k in keys:
    print(f"   {k:26}{str(conds(a).get(k,'—')):>20}{str(conds(b).get(k,'—')):>20}")

# 4) LINKING — cross-experiment via shared ontology nodes
print("="*70, "\n4) LINKING — shared nodes connect experiments across papers")
by_mat = defaultdict(set); by_q = defaultdict(set)
for x in E:
    if x["material"]: by_mat[x["material"]].add(x["_pid"])
    for c in x.get("controlled", []) + x.get("dependent", []):
        if c.get("quantity"): by_q[c["quantity"]].add(x["_pid"])
print("   materials shared across papers:", {m: len(p) for m, p in by_mat.items() if len(p) > 1})
print("   quantities in >1 paper (top):", dict(Counter({q: len(p) for q, p in by_q.items()}).most_common(6)))

# 5) UNCERTAINTY
print("="*70, "\n5) UNCERTAINTY — is it captured?")
has_unc = any("uncertainty" in c or "error" in c or "std" in c
              for x in E for c in x.get("controlled", []) + x.get("dependent", []))
print(f"   per-value uncertainty stored: {has_unc}")

print("\n" + "="*70)
print("SORT/FILTER works over these fields; COMPARE/DIFF-VIZ/KG-node-link = not built yet.")
