import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from fit_lateral import load, plateau_gpc, model_curve
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
C = load(f"{KB}/10.1039_d0cp03358h.figures.json")
common = dict(L=1e-3, W=0.1e-3, T=573.15, K=219.0, rho=3100.0, M_film=101.96, b_film=2, MA=72.09, dA=591e-12, MB=28.0, dB=374e-12, pB=300.0)
fitres = json.load(open(os.path.join(os.path.dirname(__file__), "yim20_fit.json")))
sets = {"fit (this work)": (fitres["c"], fitres["pA0"]), "yim20 sim inputs": (0.012, 65.0), "yli18 Table I (TMA)": (0.00572, 147.0)}
cur = [("yim20:fig9a#c1", 100e-9, 500, 0.1), ("yim20:fig9a#c2", 500e-9, 500, 0.1), ("yim20:fig9a#c3", 2000e-9, 500, 0.1),
       ("yim20:fig9d#c1", 500e-9, 250, 0.1), ("yim20:fig9d#c2", 500e-9, 500, 0.1), ("yim20:fig9d#c3", 500e-9, 1000, 0.1),
       ("yim20:fig11a#c2", 500e-9, 500, 0.2), ("yim20:fig11a#c3", 500e-9, 500, 0.4)]
out = {}
for name, (c, p) in sets.items():
    row = []
    for cid, H, N, tp in cur:
        P = np.array(C[cid]["points"]); P = P[P[:, 0] >= 0]
        gpc = 0.107e-9 if P[:, 0].min() > 25 else plateau_gpc(P, N)
        s = dict(id=cid, H=H, N=N, t_pulse=tp, gpc=gpc)
        m = model_curve(s, c, p, common, P[:, 0]); row.append(np.sqrt(np.mean((m - P[:, 1])**2)))
        xx = np.linspace(0, 400, 801); out[(name, cid)] = (xx, model_curve(s, c, p, common, xx))
    print(f"{name:22s} c={c:.4g} pA0={p:.3g}: RMSE per curve " + " ".join(f"{r:5.1f}" for r in row) + f" | mean train {np.mean(row[:6]):.2f}, held-out {np.mean(row[6:]):.2f} nm")
np.save(os.path.join(os.path.dirname(__file__), "yim20_curves.npy"), {f"{k[0]}|{k[1]}": np.c_[v] for k, v in out.items()}, allow_pickle=True)
