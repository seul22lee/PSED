"""Blind fit on yim20 (Yim et al. 2020, PillarHall-3, TMA/H2O 300 C). c and pA0 are NOT taken from the paper;
the paper's own simulation inputs (Fig. 10 caption: c_TMA 0.012, p_A0 65 Pa) are only printed at the end."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from fit_lateral import load, plateau_gpc, fit, model_curve
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
C = load(f"{KB}/10.1039_d0cp03358h.figures.json")
common = dict(L=1e-3, W=0.1e-3, T=573.15, K=219.0, rho=3100.0, M_film=101.96, b_film=2, MA=72.09, dA=591e-12,
              MB=28.0, dB=374e-12, pB=300.0)
# sources: T yim20:s6.p1#1; pB 3 hPa yim20:s6.p1#5; rho 3100 yim20:fig10.cap#16 (film property, ref. 51); b_film yim20:fig10.cap#9;
# K: yli18 Table I TMA (assumed; K*pA0 >> 1 so insensitive); W, dA, MB, dB: yli18 / PillarHall (assumed)
train = [("yim20:fig9a#c1", 100e-9, 500), ("yim20:fig9a#c2", 500e-9, 500), ("yim20:fig9a#c3", 2000e-9, 500),
         ("yim20:fig9d#c1", 500e-9, 250), ("yim20:fig9d#c2", 500e-9, 500), ("yim20:fig9d#c3", 500e-9, 1000)]
specs = []
for cid, H, N in train:
    P = np.array(C[cid]["points"]); specs.append(dict(id=cid, H=H, N=N, t_pulse=0.1, gpc=plateau_gpc(P, N)))
t = time.time(); res = fit(specs, C, common)
print(f"fit ({time.time()-t:.0f} s, {res['nfev']} evals): c = {res['c']:.4g} (1 sigma {res['c_1sigma'][0]:.3g}-{res['c_1sigma'][1]:.3g}), "
      f"pA0 = {res['pA0']:.3g} Pa (1 sigma {res['pA0_1sigma'][0]:.3g}-{res['pA0_1sigma'][1]:.3g}), corr(log c, log pA0) = {res['corr_log']:.2f}")
for k, v in res["rms"].items(): print(f"   train {k}: RMSE {v:.2f} nm")
# held-out: pulse 0.2 s and 0.4 s (Fig. 11a), H 500 nm, 500 cycles
for cid, tp in [("yim20:fig11a#c1", 0.1), ("yim20:fig11a#c2", 0.2), ("yim20:fig11a#c3", 0.4)]:
    P = np.array(C[cid]["points"]); P = P[P[:, 0] >= 0]
    gpc = 0.107e-9 if P[:, 0].min() > 25 else plateau_gpc(P, 500)       # 0.1/0.2 s curves start inside the channel: use Table 1 GPC_IIb
    s = dict(id=cid, H=500e-9, N=500, t_pulse=tp, gpc=gpc)
    m = model_curve(s, res["c"], res["pA0"], common, P[:, 0])
    half = lambda x, y: float(np.interp(y.max() / 2, y[::-1], x[::-1]))
    xx = np.linspace(0, 400, 801); mm = model_curve(s, res["c"], res["pA0"], common, xx)
    print(f"   held-out {cid} (pulse {tp} s): RMSE {np.sqrt(np.mean((m - P[:, 1])**2)):.2f} nm; half-thickness depth model {half(xx, mm):.0f} µm")
json.dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in res.items()}, open(os.path.join(os.path.dirname(__file__), "yim20_fit.json"), "w"), indent=1)
print("paper's own simulation inputs (revealed after the fit): c_TMA = 0.012, p_A0 = 65 Pa (yim20:fig10.cap#14, #3)")
