"""ADDED (A4): group A campaign - lateral channel, thermal, KB papers yli18, yim20, gao15.
Per curve: (1) slope-method c, (2) c fixed at the dataset median slope c -> fit pA0, (3) joint fit (c, pA0).
gpc_sat is set so that the model entrance plateau equals the measured plateau: gpc_sat = gpc_obs * (1 + K pA0) / (K pA0)."""
import os, sys, json, time, numpy as np
from scipy.optimize import least_squares, minimize_scalar
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from yli18_approx import thickness, q_from_film
from slope_method import slope_c
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
DOI = {"yli18": "10.1063_1.5028178", "yim20": "10.1039_d0cp03358h", "gao15": "10.1116_1.4903941"}
CUR = {k: {c["id"]: c for c in json.load(open(f"{KB}/{d}.figures.json"))["curves"]} for k, d in DOI.items()}
SPECIES = {   # reactant that limits the profile; film terms for q (Eq. 9); K from yli18 Table I (TMA, TiCl4) or irreversible (H2O)
 "TMA":   dict(MA=72.09, dA=591e-12, K=1e8,   # A7: irreversible limit, as Larry (was yli18 K = 219)
             rho=3100.0, M_film=101.96, b_film=2),
 "TiCl4": dict(MA=189.68, dA=703.9e-12, K=0.252, rho=4230.0, M_film=79.87, b_film=1),
 "H2O":   dict(MA=18.02, dA=418e-12, K=1e6, rho=3100.0, M_film=101.96, b_film=3),
}
# (dataset, species, paper, curve id, H [m], N, T [K], pulse [s], pB [Pa], x is aspect ratio?, plateau override [nm] or None)
ROWS = [
 ("yli18 Al2O3", "TMA", "yli18", "yli18:fig6#c2", 500e-9, 500, 573.15, 0.1, 300.0, False, None),
 ("yli18 TiO2", "TiCl4", "yli18", "yli18:fig7#c2", 500e-9, 1000, 383.15, 0.1, 300.0, False, None),
 *[("yim20 Al2O3", "TMA", "yim20", f"yim20:fig8b#c{i}", 500e-9, 500, 573.15, 0.1, 300.0, False, None) for i in (1, 2, 3, 4)],
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig9a#c2", 500e-9, 500, 573.15, 0.1, 300.0, False, None),
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig9d#c1", 500e-9, 250, 573.15, 0.1, 300.0, False, None),
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig9d#c2", 500e-9, 500, 573.15, 0.1, 300.0, False, None),
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig9d#c3", 500e-9, 1000, 573.15, 0.1, 300.0, False, None),
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig11a#c1", 500e-9, 500, 573.15, 0.1, 300.0, False, 53.5),
 ("yim20 Al2O3", "TMA", "yim20", "yim20:fig11a#c2", 500e-9, 500, 573.15, 0.2, 300.0, False, 53.5),
 ("yim20 H2O-limited", "H2O", "yim20", "yim20:fig11a#c3", 500e-9, 500, 573.15, 0.1, 300.0, False, None),
 ("gao15 Al2O3", "TMA", "gao15", "gao15:fig5a#c1", 500e-9, 1109, 573.15, 0.1, 150.0, False, 108.0),
 *[("gao15 TiO2", "TiCl4", "gao15", f"gao15:fig5b#c{i}", H, 2000, 383.15, 0.1, 150.0, True, None) for i, H in ((1, 200e-9), (2, 500e-9), (3, 1000e-9))],
]
L = 1e-3; Wd = 0.1e-3
def prep(r):
    _, sp, paper, cid, H, N, T, tp, pB, is_ar, plat = r
    P = np.array(CUR[paper][cid]["points"], float)
    if is_ar: P[:, 0] = P[:, 0] * H * 1e6          # aspect ratio -> um
    P = P[P[:, 0] >= 0]
    pl = plat if plat else float(np.mean(P[P[:, 0] <= max(25.0, 0.08 * P[:, 0].max()), 1]))
    return P, pl
def model(r, c, pA0, x_um, pl):
    _, sp, paper, cid, H, N, T, tp, pB, is_ar, _ = r; s = SPECIES[sp]
    gpc_obs = pl / N * 1e-9; Kp = s["K"] * pA0; gpc_sat = gpc_obs * (1 + Kp) / Kp
    x = np.linspace(0, L, 2001)
    _, th = thickness(N=N, gpc_sat=gpc_sat, H0=H, blocks=min(N, 40), x=x, W=Wd, T=T, pA0=pA0, t_pulse=tp, c=c, K=s["K"],
                      q=q_from_film(gpc_sat, s["rho"], s["M_film"], s["b_film"]), MA=s["MA"], dA=s["dA"], MB=28.0, dB=374e-12, pB=pB)
    return np.interp(x_um * 1e-6, x, th)
out = []
for r in ROWS:
    P, pl = prep(r)
    c_sl, n_sl = slope_c(P.copy(), r[4], pl)
    out.append(dict(dataset=r[0], species=r[1], curve=r[3], H_nm=r[4] * 1e9, N=r[5], c_slope=c_sl, n_front=n_sl, P=P, pl=pl, row=r))
datasets = sorted({o["dataset"] for o in out})
c_med = {d: float(np.nanmedian([o["c_slope"] for o in out if o["dataset"] == d and 1e-5 < o["c_slope"] < 1])) for d in datasets}
for o in out:
    r, P, pl = o["row"], o["P"], o["pl"]; t0 = time.time()
    cf = c_med[o["dataset"]]
    f1 = minimize_scalar(lambda lp: np.mean((model(r, cf, np.exp(lp), P[:, 0], pl) - P[:, 1]) ** 2), bounds=(np.log(1.0), np.log(1000.0)), method="bounded", options=dict(xatol=0.01))
    o["fixed_c"] = cf; o["pA0_fixed_c"] = float(np.exp(f1.x)); o["rmse_fixed_c"] = float(np.sqrt(f1.fun))
    g = least_squares(lambda z: model(r, np.exp(z[0]), np.exp(z[1]), P[:, 0], pl) - P[:, 1], np.log([cf, o["pA0_fixed_c"]]),
                      bounds=(np.log([1e-6, 0.5]), np.log([1.0, 2000.0])), diff_step=0.02, max_nfev=40)
    J = g.jac; s2 = 2 * g.cost / max(len(g.fun) - 2, 1); cov = np.linalg.pinv(J.T @ J) * s2; sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    o["c_joint"], o["pA0_joint"] = map(float, np.exp(g.x)); o["c_joint_1s"] = [float(o["c_joint"] * np.exp(-sd[0])), float(o["c_joint"] * np.exp(sd[0]))]
    o["rmse_joint"] = float(np.sqrt(np.mean(g.fun ** 2)))
    print(f"{o['dataset']:18s} {o['curve']:17s} H{o['H_nm']:5.0f} N{o['N']:5d} | slope c {o['c_slope']:.2e} (n={o['n_front']}) | "
          f"c fixed {cf:.1e}: pA0 {o['pA0_fixed_c']:6.1f} Pa, RMSE {o['rmse_fixed_c']:5.2f} | joint: c {o['c_joint']:.2e} (1s {o['c_joint_1s'][0]:.1e}-{o['c_joint_1s'][1]:.1e}), "
          f"pA0 {o['pA0_joint']:6.1f}, RMSE {o['rmse_joint']:5.2f} nm  [{time.time()-t0:.0f}s]", flush=True)
json.dump([{k: v for k, v in o.items() if k not in ("P", "row")} for o in out], open(os.path.join(os.path.dirname(__file__), "campaign_groupA.json"), "w"), indent=1)
print("dataset median slope c:", {k: f"{v:.2e}" for k, v in c_med.items()})
