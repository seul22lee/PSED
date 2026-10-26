"""ADDED (A6): digital-twin demo, calibration from a flat in-situ measurement (QCM-like coverage trace) instead of test chips.
Same reactors, recipe convention and channel target as A5 (demo/dt_recipe_correction.py; f(E) taken from its json).
Measurement: Larry's FlatModel at the sample position (coverage theta(t) during one low-dose TMA pulse) in reactor B (truth),
sampled at 20 Hz with noise sigma 0.01. Twin of B fits eta and beta_wall with an assumed sample sticking c (KB value).
Flat uptake measures c * exposure, so the assumed c is varied (true 4e-3; assumed 2e-3, 4e-3, 8e-3) to show its effect on the recipe.
No change to reaction_model.py; beta_wall > 0 only here (Larry's default D1 unchanged)."""
import os, sys, json, time, warnings, numpy as np, torch
from scipy.optimize import least_squares
warnings.filterwarnings("ignore")
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, ".."))
import reaction_model as M
T = 573.15; F_RECIPE = 20.0; F_CAL = 1.0; TP_CAL = 0.5; C_TRUE = 4e-3; K_TMA = None;   # A7: irreversible, as Larry (was 219)
TARGET = 100.0
B = dict(L=0.30, R=0.04, p_torr=2.0, flow_sccm=300, n_z=301, zs=(0.20, 0.24))
TRUTH = dict(eta=0.6, beta_wall=2e-3)
A5 = json.load(open(os.path.join(here, "dt_recipe_correction.json")))
fE = np.array(A5["f_of_E"]); E_TGT = A5["E_target"]; TP_A = A5["tp_A"]
front_of = lambda E: float(np.interp(np.log(max(E, 1e-6)), np.log(fE[:, 0]), fE[:, 1]))
def run(tp, F, eta, bw, c_flat):
    """Larry's reactor model + FlatModel at the sample: returns t, p_sample(t), theta_sample(t)."""
    mc = M.ModelCoupling.__new__(M.ModelCoupling); mc.t_step = 0.005; mc.sample_betas = [c_flat, 3e-4]
    mc.model_init(t_step=0.005, T=T, z_max=B["L"], L=B["L"], R=B["R"], S=B["L"] * 2 * np.pi * B["R"],
                  p_torr=B["p_torr"], flow_sccm=B["flow_sccm"], n_z=B["n_z"])
    mc.coupling_init(position_range=B["zs"])   # Larry's FlatModel (and ChannelModel) at the sample position
    p_in = eta * M.torr_to_pa(B["p_torr"]) * F / (F + B["flow_sccm"])
    mc.set_recipe([{'t': tp, 'p': [p_in, 0.0]}, {'t': 5.0, 'p': [0.0, 0.0]}])
    win = tp + 0.6   # A8: whole window in one BDF call (C9); FlatModel then stepped every t_step on the stored gas state, as in ModelCoupling
    mc.model.setup.construct_time_profile(tau_end=win, D=None, n_out=int(round(win / mc.t_step)) + 1); mc.model.reset_internal_state()
    _, _, (tt, xx, _) = mc.model.run_model(betas=[bw, 0.0], t_offset=0.0, outlet_type='noflux', method='BDF', return_profile=True)
    ts, ps, ths = [0.0], [0.0], [0.0]
    for k in range(1, len(tt)):
        ths.append(mc.flat_model.eval_step(xx[k])); ps.append(float(xx[k, 0, mc.flat_model.xpos].mean())); ts.append(tt[k])
    return np.array(ts), np.array(ps), np.array(ths)
_E = {}
def exposure(tp, eta, bw):
    k = (round(tp, 4), round(eta, 4), bw)
    if k not in _E: t, p, _ = run(tp, F_RECIPE, eta, bw, C_TRUE); _E[k] = float(np.trapezoid(p, t))
    return _E[k]
def tp_for(E_target, eta, bw, lo=0.05, hi=3.0):
    for _ in range(8):
        mid = np.sqrt(lo * hi); lo, hi = (mid, hi) if exposure(mid, eta, bw) < E_target else (lo, mid)
    return float(np.sqrt(lo * hi))
res = {}; t0 = time.time()
print("1) QCM measurement in reactor B (truth): low-dose pulse, source %.1f sccm, %.2f s" % (F_CAL, TP_CAL), flush=True)
t, p, th = run(TP_CAL, F_CAL, TRUTH["eta"], TRUTH["beta_wall"], C_TRUE)
tq = np.arange(0.05, t[-1], 0.05); rng = np.random.default_rng(1)
thq = np.interp(tq, t, th) + rng.normal(0, 0.01, tq.size)
res["meas"] = dict(t=tq.tolist(), theta=thq.tolist(), t_model=t.tolist(), theta_true=th.tolist(), p_true=p.tolist())
print(f"   exposure {np.trapezoid(p, t):.3f} Pa s, final theta {th[-1]:.2f}  [{time.time()-t0:.0f}s]", flush=True)
res["fits"] = []
for c_assumed in (C_TRUE, 2e-3, 8e-3):
    ts = time.time()
    def resid(z):
        tt, pp, hh = run(TP_CAL, F_CAL, np.exp(z[0]), np.exp(z[1]), c_assumed); return np.interp(tq, tt, hh) - thq
    best = None
    for z0 in (np.log([0.5, 1e-3]), np.log([1.0, 1e-4])):
        f = least_squares(resid, z0, bounds=(np.log([0.05, 1e-6]), np.log([5.0, 0.05])), diff_step=0.05, max_nfev=25)
        if best is None or f.cost < best.cost: best = f
    J = best.jac; s2 = 2 * best.cost / max(tq.size - 2, 1); cov = np.linalg.pinv(J.T @ J) * s2; sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    eta, bw = map(float, np.exp(best.x)); corr = float(cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1]))
    tt, pp, hh = run(TP_CAL, F_CAL, eta, bw, c_assumed)
    print(f"2) assumed c {c_assumed:.0e}: eta {eta:.3f} (x/÷{np.exp(sd[0]):.2f}), beta_wall {bw:.2e} (x/÷{np.exp(sd[1]):.2f}), corr {corr:+.2f}, "
          f"RMSE {np.sqrt(2*best.cost/tq.size):.4f}  [{time.time()-ts:.0f}s]", flush=True)
    tpB = tp_for(E_TGT, eta, bw); Etrue = exposure(tpB, TRUTH["eta"], TRUTH["beta_wall"])
    print(f"   corrected recipe t_p {tpB:.3f} s -> truth exposure {Etrue:.2f} Pa s -> front {front_of(Etrue):.0f} um (target {TARGET:.0f})", flush=True)
    res["fits"].append(dict(c_assumed=c_assumed, eta=eta, beta_wall=bw, sd_log=sd.tolist(), corr=corr, rmse=float(np.sqrt(2 * best.cost / tq.size)),
                            t_fit=tt.tolist(), theta_fit=hh.tolist(), tp=tpB, E_truth=Etrue, front_fE=front_of(Etrue)))
print("3) full-chain check of the c = true recipe (reactor B truth -> ChannelModel)", flush=True)
tpB = res["fits"][0]["tp"]; t, p, _ = run(tpB, F_RECIPE, TRUTH["eta"], TRUTH["beta_wall"], C_TRUE)
ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005; ref.model_init(t_step=0.005, T=T, n_z=51)
ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=1e-4, xpos=None, W=0.1e-3, H=500e-9, T=T, L=0.6e-3,
                    carrier_pressure=M.torr_to_pa(B["p_torr"]), points=240, K=K_TMA, logbetas=[np.log(C_TRUE), np.log(3e-4)])
with torch.no_grad():
    for v in np.interp(np.arange(0, t[-1], 1e-4), t, p): ch.step(torch.tensor([v, 0.0], dtype=torch.float64))
thc = ch.theta[0].numpy(); x = (np.arange(240) + 0.5) * 0.6e-3 / 240 * 1e6; fr = float(np.interp(0.5, thc[::-1], x[::-1]))
res["check"] = dict(tp=tpB, front=fr, x=x.tolist(), theta=thc.tolist()); print(f"   t_p {tpB:.3f} s -> front {fr:.1f} um", flush=True)
json.dump(res, open(os.path.join(here, "dt_qcm_calibration.json"), "w")); print(f"done [{time.time()-t0:.0f}s]")
