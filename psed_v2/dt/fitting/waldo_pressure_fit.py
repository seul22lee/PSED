"""ADDED (A10): fit Larry's reactor model (WALDO geometry) to the measured exhaust-pressure spikes of the 7/02 WALDO run
(TMA 0.1 s, H2O 1 s, 100 C, 120 sccm, 1.41 Torr baseline). Model output = gas at the reactor outlet (z = L), passed through a
first-order gauge/line lag tau_g. Fitted per reactant: tau_g, time shift, and optionally the reversible wall reservoir (C11)
k_ads, k_des; amplitude by linear least squares (the Convectron is N2-calibrated, so absolute TMA/H2O pressure is not used).
Then the purge time at the sample (QCM, 31-35 cm) to 1e-3 of the pulse peak, with and without the reservoir.
Data: env WALDO_PRESSURE (two columns: time s, pressure Torr)."""
import os, sys, json, time, warnings, numpy as np
from scipy.optimize import least_squares
warnings.filterwarnings("ignore")
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, ".."))
import reaction_model as M
P = np.loadtxt(os.environ["WALDO_PRESSURE"])
T, L, R, P_TORR, Q = 373.15, 0.64, 0.0175, 1.41, 120.0; ZS = (0.31, 0.35); THR = 1e-3; DT = 0.02
def average_spike(first, period, rel, win, cycles):
    out = []
    for k in cycles:
        a = first + k * period + rel; m = (P[:, 0] > a - 6) & (P[:, 0] < a + 6)
        tt, pp = P[m, 0], P[m, 1]; base = np.median(pp[tt < a - 2]) if np.any(tt < a - 2) else np.median(pp)
        on = np.where((tt > a - 3) & (pp > base + 0.02))[0]
        if not len(on): continue
        t0 = tt[on[0]]; mm = (P[:, 0] >= t0 - 2) & (P[:, 0] <= t0 + win)
        out.append(np.interp(np.arange(-2, win, 0.2), P[mm, 0] - t0, P[mm, 1] - base))
    return np.arange(-2, win, 0.2), np.mean(out, axis=0), len(out)
def model_trace(pulse, which, res, win):
    mc = M.ModelCoupling.__new__(M.ModelCoupling); mc.t_step = 0.005
    mc.model_init(t_step=0.005, T=T, z_max=L, L=L, R=R, S=L * 2 * np.pi * R, p_torr=P_TORR, flow_sccm=Q, n_z=201)
    on = [1.0, 0.0] if which == 0 else [0.0, 1.0]
    mc.set_recipe([{'t': pulse, 'p': on}, {'t': win + 5, 'p': [0.0, 0.0]}])
    mc.model.setup.construct_time_profile(tau_end=win, D=None, n_out=int(round(win / DT)) + 1); mc.model.reset_internal_state()
    _, _, (t, x, _) = mc.model.run_model(betas=[0.0, 0.0], outlet_type='noflux', method='BDF', return_profile=True,
                                         wall_reservoir=None if res is None else {'k_ads': [res[0]] * 2, 'k_des': [res[1]] * 2})
    z = mc.model.setup.z; zs = np.where((z >= ZS[0]) & (z <= ZS[1]))[0]
    return t, x[:, which, -2], x[:, which, zs].mean(axis=1)
def lag(t, p, tau):
    y = np.zeros_like(p); a = 1 - np.exp(-(t[1] - t[0]) / tau)
    for i in range(1, len(p)): y[i] = y[i - 1] + a * (p[i] - y[i - 1])
    return y
def fit(td, pd, pulse, which, with_res, win):
    def pred(z):
        tau, shift = np.exp(z[0]), z[1]; res = (np.exp(z[2]), np.exp(z[3])) if with_res else None
        t, pout, _ = model_trace(pulse, which, res, win)
        g = np.interp(td - shift, t, lag(t, pout, tau), left=0.0); A = float(g @ pd / (g @ g)) if g @ g > 0 else 0.0
        return A * g
    z0 = [np.log(0.5), 0.0] + ([np.log(1.0), np.log(0.3)] if with_res else [])
    lb = [np.log(0.02), -3.0] + ([np.log(1e-3), np.log(1e-3)] if with_res else []); ub = [np.log(10.0), 3.0] + ([np.log(100.0), np.log(10.0)] if with_res else [])
    f = least_squares(lambda z: pred(z) - pd, z0, bounds=(lb, ub), diff_step=0.05, max_nfev=80)
    return f, pred(f.x)
out = {}; t0 = time.time()
for name, which, pulse, rel, win in (("TMA", 0, 0.1, 0.0, 40.0), ("H2O", 1, 1.0, 60.0, 45.0)):
    td, pd, n = average_spike(30.0, 121.1, rel, win, range(5, 50))
    r = dict(n_cycles=n, t=td.tolist(), p=pd.tolist())
    for with_res in (False, True):
        f, pr = fit(td, pd, pulse, which, with_res, win + 5)
        z = f.x; tau, shift = float(np.exp(z[0])), float(z[1]); res = (float(np.exp(z[2])), float(np.exp(z[3]))) if with_res else None
        t, _, ps = model_trace(pulse, which, res, 60.0); pk = ps.max(); bad = np.where((t > pulse) & (ps > THR * pk))[0]
        purge = float(t[bad[-1]] - pulse) if len(bad) else 0.0
        key = "reservoir" if with_res else "no_reservoir"
        r[key] = dict(tau_g=tau, shift=shift, k_ads=None if res is None else res[0], k_des=None if res is None else res[1],
                      rmse_torr=float(np.sqrt(np.mean((pr - pd) ** 2))), pred=pr.tolist(), purge_at_sample_s=purge, sample_t=t.tolist(), sample_p=ps.tolist())
        print(f"{name} ({n} cycles) {key:12s}: tau_g {tau:.2f} s, shift {shift:+.2f} s" + (f", k_ads {res[0]:.2f} 1/s, k_des {res[1]:.3f} 1/s (1/k_des {1/res[1]:.1f} s)" if res else "")
              + f" | RMSE {r[key]['rmse_torr']*1e3:.1f} mTorr | purge at sample (1e-3 of peak) {purge:.1f} s  [{time.time()-t0:.0f}s]", flush=True)
    out[name] = r
json.dump(out, open(os.path.join(here, "waldo_pressure_fit.json"), "w"))

# A10b: the gauge is shared, so its lag cannot be 3.5 s for TMA and 0.33 s for H2O. Fix tau_g at the H2O value (H2O needs no reservoir)
# and refit TMA with the reservoir: the extra TMA broadening must then come from the reactor/delivery side.
tau_fix = out["H2O"]["no_reservoir"]["tau_g"]; td = np.array(out["TMA"]["t"]); pd = np.array(out["TMA"]["p"])
def pred_fixed(z, res_on=True):
    shift = z[0]; res = (np.exp(z[1]), np.exp(z[2])) if res_on else None
    t, pout, _ = model_trace(0.1, 0, res, 45.0); g = np.interp(td - shift, t, lag(t, pout, tau_fix), left=0.0)
    return (g @ pd / (g @ g)) * g
f = least_squares(lambda z: pred_fixed(z) - pd, [-0.4, np.log(1.0), np.log(0.1)], bounds=([-3, np.log(1e-3), np.log(1e-3)], [3, np.log(100), np.log(10)]), diff_step=0.05, max_nfev=80)
res = (float(np.exp(f.x[1])), float(np.exp(f.x[2]))); pr = pred_fixed(f.x)
t, _, ps = model_trace(0.1, 0, res, 120.0); pk = ps.max(); bad = np.where((t > 0.1) & (ps > THR * pk))[0]; purge = float(t[bad[-1]] - 0.1)
bad2 = np.where((t > 0.1) & (ps > 1e-2 * pk))[0]; purge2 = float(t[bad2[-1]] - 0.1)
out["TMA"]["reservoir_shared_gauge"] = dict(tau_g=tau_fix, shift=float(f.x[0]), k_ads=res[0], k_des=res[1], rmse_torr=float(np.sqrt(np.mean((pr - pd) ** 2))),
                                           pred=pr.tolist(), purge_at_sample_s=purge, purge_1e2_s=purge2, sample_t=t.tolist(), sample_p=ps.tolist())
print(f"TMA reservoir, shared gauge tau {tau_fix:.2f} s: k_ads {res[0]:.2f} 1/s, k_des {res[1]:.3f} 1/s (1/k_des {1/res[1]:.1f} s) | RMSE {out['TMA']['reservoir_shared_gauge']['rmse_torr']*1e3:.1f} mTorr | purge at sample: 1e-3 of peak {purge:.1f} s, 1e-2 {purge2:.1f} s")
json.dump(out, open(os.path.join(here, "waldo_pressure_fit.json"), "w"))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
for a, nm in zip(ax[:2], ("TMA", "H2O")):
    r = out[nm]; a.plot(r["t"], np.array(r["p"]) * 1e3, "k.", ms=3, label=f"WALDO 7/02, mean of {r['n_cycles']} cycles")
    for key, st in (("no_reservoir", "C0--"), ("reservoir", "C1-"), ("reservoir_shared_gauge", "C2-")):
        if key in r: a.plot(r["t"], np.array(r[key]["pred"]) * 1e3, st, label=f"{key}: RMSE {r[key]['rmse_torr']*1e3:.1f} mTorr")
    a.set(title=f"{nm} spike at the exhaust gauge", xlabel="time after onset (s)", ylabel="Δp (mTorr)"); a.legend(fontsize=7)
for key, st in (("no_reservoir", "C0--"), ("reservoir_shared_gauge", "C2-")):
    r = out["TMA"][key]; tt = np.array(r["sample_t"]); pp = np.array(r["sample_p"]); ax[2].semilogy(tt, pp / pp.max() + 1e-12, st, label=f"{key}: purge {r['purge_at_sample_s']:.1f} s")
ax[2].axhline(THR, color="k", ls=":"); ax[2].set(ylim=(1e-5, 2), xlim=(0, 60), xlabel="time (s)", ylabel="TMA at sample / peak", title="TMA at the sample (model)"); ax[2].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(here, "waldo_pressure_fit.png"), dpi=90)
