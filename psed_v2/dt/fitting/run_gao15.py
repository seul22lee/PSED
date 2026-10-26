"""gao15 (Gao et al. 2015, PillarHall-1, Al2O3 TMA/H2O 300 C): no sticking coefficient reported.
Fit Fig. 5a (500 nm gap, 1109 cycles); then predict the film ends reported in the text for 200/500/1000 nm gaps
(Fig. 3, ~50 nm films: 25 / 90 / 155 um; KB gao15:s6.p13#2-4), which are not used in the fit."""
import os, sys, json, numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(__file__))
from fit_lateral import load, plateau_gpc, model_curve
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
C = load(f"{KB}/10.1116_1.4903941.figures.json")
P = np.array(C["gao15:fig5a#c1"]["points"])
common = dict(L=1e-3, W=0.1e-3, T=573.15, K=219.0, rho=3100.0, M_film=101.96, b_film=2, MA=72.09, dA=591e-12, MB=28.0, dB=374e-12, pB=150.0)
# sources: T gao15:fig5.cap#4; H gao15:fig5.cap#6; N gao15:fig5.cap#1; pulse gao15:s6.p5#6; pB = 1-2 mbar (gao15:s6.p5#3) -> 150 Pa assumed;
# rho 3100, W, K, dA, d_B: assumed (not in gao15)
spec = dict(id="gao15:fig5a#c1", H=500e-9, N=1109, t_pulse=0.1, gpc=plateau_gpc(P, 1109, x_max_um=45))
yim = json.load(open(os.path.join(os.path.dirname(__file__), "yim20_fit.json")))
def run(mask, label, fix_p=None):
    Q = P[mask]
    if fix_p is None:
        f = lambda z: model_curve(spec, np.exp(z[0]), np.exp(z[1]), common, Q[:, 0]) - Q[:, 1]
        r = least_squares(f, np.log([0.005, 80.0]), diff_step=0.02); c, p = np.exp(r.x)
        J = r.jac; s2 = 2 * r.cost / max(len(r.fun) - 2, 1); cov = np.linalg.pinv(J.T @ J) * s2; sd = np.sqrt(np.diag(cov))
        extra = f"(1 sigma c {c*np.exp(-sd[0]):.2g}-{c*np.exp(sd[0]):.2g}, pA0 {p*np.exp(-sd[1]):.3g}-{p*np.exp(sd[1]):.3g}; corr {cov[0,1]/sd[0]/sd[1]:.2f})"
    else:
        p = fix_p
        f = lambda z: model_curve(spec, np.exp(z[0]), p, common, Q[:, 0]) - Q[:, 1]
        r = least_squares(f, np.log([0.005]), diff_step=0.02); c = float(np.exp(r.x[0]))
        J = r.jac; s2 = 2 * r.cost / max(len(r.fun) - 1, 1); sd = float(np.sqrt(np.linalg.pinv(J.T @ J)[0, 0] * s2))
        extra = f"(1 sigma c {c*np.exp(-sd):.2g}-{c*np.exp(sd):.2g}; pA0 fixed)"
    rms = np.sqrt(np.mean((model_curve(spec, c, p, common, P[:, 0]) - P[:, 1]) ** 2))
    print(f"[{label}] c = {c:.3g}, pA0 = {p:.3g} Pa {extra}; RMSE all points {rms:.2f} nm")
    return c, p
res = {}
res["a_all"] = run(P[:, 0] >= 0, "a: c and pA0, all points")
res["a_cut"] = run(P[:, 0] <= 85, "a: c and pA0, x <= 85 um (tail treated as reflectometer floor)")
res["b_cut"] = run(P[:, 0] <= 85, "b: pA0 fixed = yim20 fit", fix_p=yim["pA0"])
# out-of-sample: film end (thickness falls below a threshold) for ~50 nm films, 200/500/1000 nm gaps
obs = {200e-9: 25.0, 500e-9: 90.0, 1000e-9: 155.0}
N50 = int(round(50e-9 / spec["gpc"]))
print(f"held-out: Fig. 3 film ends, ~50 nm films -> N = {N50} cycles; end = first x where thickness < threshold")
xx = np.linspace(0, 400, 1601)
for key, (c, p) in res.items():
    line = []
    for H, o in obs.items():
        s = dict(id="pred", H=H, N=N50, t_pulse=0.1, gpc=spec["gpc"]); m = model_curve(s, c, p, common, xx)
        ends = [float(xx[np.argmax(m < th)]) for th in (5.0, 10.0)]
        line.append(f"H {H*1e9:.0f} nm: obs {o:.0f} / model {ends[0]:.0f}-{ends[1]:.0f} um")
    print(f"   [{key}] " + " | ".join(line))
json.dump({k: [float(v[0]), float(v[1])] for k, v in res.items()}, open(os.path.join(os.path.dirname(__file__), "gao15_fit.json"), "w"), indent=1)
