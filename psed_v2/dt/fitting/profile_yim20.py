"""Profile scan: for fixed c, best pA0 (1-D) on the six yim20 training curves; prints per-curve RMSE."""
import os, sys, json, numpy as np
from scipy.optimize import minimize_scalar
sys.path.insert(0, os.path.dirname(__file__))
from fit_lateral import load, plateau_gpc, model_curve
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
C = load(f"{KB}/10.1039_d0cp03358h.figures.json")
common = dict(L=1e-3, W=0.1e-3, T=573.15, K=219.0, rho=3100.0, M_film=101.96, b_film=2, MA=72.09, dA=591e-12, MB=28.0, dB=374e-12, pB=300.0)
cur = [("yim20:fig9a#c1", 100e-9, 500), ("yim20:fig9a#c2", 500e-9, 500), ("yim20:fig9a#c3", 2000e-9, 500),
       ("yim20:fig9d#c1", 500e-9, 250), ("yim20:fig9d#c2", 500e-9, 500), ("yim20:fig9d#c3", 500e-9, 1000)]
data = []
for cid, H, N in cur:
    P = np.array(C[cid]["points"]); P = P[P[:, 0] >= 0]; data.append((dict(id=cid, H=H, N=N, t_pulse=0.1, gpc=plateau_gpc(P, N)), P))
def per_curve(c, p): return [float(np.sqrt(np.mean((model_curve(s, c, p, common, P[:, 0]) - P[:, 1])**2))) for s, P in data]
rows = []
for c in [0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.03, 0.06]:
    r = minimize_scalar(lambda lp: sum(e**2 for e in per_curve(c, np.exp(lp))), bounds=(np.log(20), np.log(400)), method="bounded", options=dict(xatol=0.01))
    p = float(np.exp(r.x)); e = per_curve(c, p); rows.append(dict(c=c, pA0=p, rmse=e, sse=sum(x**2 for x in e)))
    print(f"c={c:<7} best pA0={p:6.1f} Pa | sum MSE {rows[-1]['sse']:6.1f} | per curve " + " ".join(f"{x:5.1f}" for x in e), flush=True)
json.dump(rows, open(os.path.join(os.path.dirname(__file__), "yim20_profile.json"), "w"), indent=1)
