"""ADDED (A2): fit the lateral-channel model to measured thickness profiles stored in the KB.
Shared parameters across curves (e.g. c, pA0); per-curve conditions (H, N, t_pulse, gpc from the entrance plateau).
Solver: yli18_approx (A1). Reports fitted values, a Jacobian-based 1-sigma, and the c-pA0 correlation."""
import json, sys, os, numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from yli18_approx import thickness, q_from_film

def load(path):
    return {c["id"]: c for c in json.load(open(path))["curves"]}

def plateau_gpc(P, N, x_max_um=25.0):
    """gpc from the measured entrance plateau: mean thickness for 0 <= x <= x_max_um, divided by N."""
    m = (P[:, 0] >= 0) & (P[:, 0] <= x_max_um)
    return float(np.mean(P[m, 1])) / N * 1e-9

def model_curve(spec, c, pA0, common, x_um):
    x = np.linspace(0, common["L"], 2001)
    _, s = thickness(N=spec["N"], gpc_sat=spec["gpc"], H0=spec["H"], blocks=min(spec["N"], 50), x=x,
                     W=common["W"], T=common["T"], pA0=pA0, t_pulse=spec["t_pulse"], c=c, K=common["K"],
                     q=q_from_film(spec["gpc"], common["rho"], common["M_film"], common["b_film"]),
                     MA=common["MA"], dA=common["dA"], MB=common["MB"], dB=common["dB"], pB=common["pB"])
    return np.interp(x_um * 1e-6, x, s)

def fit(specs, curves, common, x0=(0.01, 100.0)):
    data = []
    for s in specs:
        P = np.array(curves[s["id"]]["points"]); P = P[P[:, 0] >= 0]
        data.append((s, P))
    def resid(z):
        c, p = np.exp(z)
        return np.concatenate([(model_curve(s, c, p, common, P[:, 0]) - P[:, 1]) / np.sqrt(len(P)) for s, P in data])
    r = least_squares(resid, np.log(x0), diff_step=0.02, x_scale=1.0, max_nfev=80)
    c, p = np.exp(r.x)
    J = r.jac; dof = max(len(r.fun) - 2, 1); s2 = 2 * r.cost / dof
    cov = np.linalg.pinv(J.T @ J) * s2                     # covariance of log-parameters
    sd = np.sqrt(np.diag(cov)); corr = cov[0, 1] / (sd[0] * sd[1])
    rms = {s["id"]: float(np.sqrt(np.mean((model_curve(s, c, p, common, P[:, 0]) - P[:, 1]) ** 2))) for s, P in data}
    return dict(c=c, pA0=p, c_1sigma=(c * np.exp(-sd[0]), c * np.exp(sd[0])), pA0_1sigma=(p * np.exp(-sd[1]), p * np.exp(sd[1])),
                corr_log=corr, rms=rms, nfev=r.nfev)
