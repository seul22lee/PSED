"""ADDED (A4): overlay of group A fits (c fixed at slope value vs joint fit) on the KB curves."""
import os, sys, json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ["x"]
src = open(os.path.join(here, "campaign_groupA.py")).read().split("out = []")[0]
g = {"__file__": os.path.join(here, "campaign_groupA.py")}; exec(src, g)
res = {o["curve"]: o for o in json.load(open(os.path.join(here, "campaign_groupA.json")))}
fig, ax = plt.subplots(4, 5, figsize=(20, 14)); ax = ax.ravel()
for i, r in enumerate(g["ROWS"]):
    P, pl = g["prep"](r); o = res[r[3]]; x = np.linspace(0, P[:, 0].max() * 1.05, 200); a = ax[i]
    a.plot(P[:, 0], P[:, 1], "ko", ms=3, label="KB data")
    a.plot(x, g["model"](r, o["fixed_c"], o["pA0_fixed_c"], x, pl), "C0-", label=f"c={o['fixed_c']:.1e} fixed, pA0={o['pA0_fixed_c']:.0f}")
    a.plot(x, g["model"](r, o["c_joint"], o["pA0_joint"], x, pl), "C3--", label=f"joint c={o['c_joint']:.1e}, pA0={o['pA0_joint']:.0f}")
    a.set_title(f"{r[3]}  ({r[1]}, H {r[4]*1e9:.0f} nm, N {r[5]})", fontsize=9); a.legend(fontsize=7); a.set_xlabel("x (µm)"); a.set_ylabel("nm")
for a in ax[len(g["ROWS"]):]: a.axis("off")
fig.tight_layout(); fig.savefig(os.path.join(here, "campaign_groupA.png"), dpi=90)
