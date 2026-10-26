"""ADDED (A4): TiCl4 rows - K free. With yli18's K = 0.252 1/Pa the joint fit drives c to its bound (c unidentifiable)
and gao15 fronts are sharper than the model. Here fit (c, K, pA0) jointly; gao15 200 nm plateau taken from the entrance points."""
import os, sys, json, numpy as np
from scipy.optimize import least_squares
here = os.path.dirname(os.path.abspath(__file__)); g = {"__file__": os.path.join(here, "campaign_groupA.py")}
exec(open(g["__file__"]).read().split("out = []")[0], g)
rows = [r for r in g["ROWS"] if r[1] == "TiCl4"]
rows = [r if r[3] != "gao15:fig5b#c1" else (*r[:-1], 96.0) for r in rows]
res = []
for r in rows:
    P, pl = g["prep"](r)
    def m(z, x):
        g["SPECIES"]["TiCl4"]["K"] = float(np.exp(z[1])); return g["model"](r, np.exp(z[0]), np.exp(z[2]), x, pl)
    best = None
    for K0 in (0.252, 3.0, 30.0):
        f = least_squares(lambda z: m(z, P[:, 0]) - P[:, 1], np.log([3e-3, K0, 25.0]), bounds=(np.log([1e-6, 0.01, 0.5]), np.log([1.0, 1e4, 2000.0])), diff_step=0.02, max_nfev=60)
        if best is None or f.cost < best.cost: best = f
    J = best.jac; s2 = 2 * best.cost / max(len(best.fun) - 3, 1); sd = np.sqrt(np.clip(np.diag(np.linalg.pinv(J.T @ J) * s2), 0, None))
    c, K, p = np.exp(best.x); rm = float(np.sqrt(np.mean(best.fun ** 2)))
    print(f"{r[3]:16s} H{r[4]*1e9:5.0f} | c {c:.2e} (x/÷{np.exp(sd[0]):.1f}) K {K:.3g} 1/Pa (x/÷{np.exp(sd[1]):.1f}) pA0 {p:.1f} Pa  K*pA0 {K*p:.1f} | RMSE {rm:.2f} nm", flush=True)
    res.append(dict(curve=r[3], H_nm=r[4] * 1e9, plateau=pl, c=c, K=K, pA0=p, sd_log=sd.tolist(), rmse=rm))
g["SPECIES"]["TiCl4"]["K"] = 0.252
json.dump(res, open(os.path.join(here, "campaign_ticl4_K.json"), "w"), indent=1)
