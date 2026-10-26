"""ADDED (A11): twin calibration from a QCM dose series in mass units (replaces the in-pulse theta trace of A6 in the figure).
Measurement (synthetic, reactor B truth eta 0.6, beta_wall 2e-3): TMA half-cycle mass step dm_TMA [ng/cm2] after single TMA pulses of
different length at a reduced source flow (1 sccm), each from a fresh (H2O-reset) surface - what a QCM with ~1 s resolution gives.
Coverage -> mass: dm_TMA = theta * m_sat, m_sat = saturated TMA step measured on WALDO (7/02 run: 41-71 ng/cm2, mean of cycles 20-50
71 ng/cm2; Larry's suggestion in Sec. 3.2 / e-mail of 8/28). QCM noise sigma 2 ng/cm2 (step quantization seen in the WALDO data).
Twin fits eta and beta_wall with c from the KB (true 4e-3; also 2e-3 and 8e-3); m_sat taken as known. Then recipe and full-chain check
as in A6. Models: Larry's reactor model (one BDF call per window, C9) + FlatModel (irreversible) + ChannelModel (irreversible, A7)."""
import os, sys, json, time, warnings, numpy as np, torch
from scipy.optimize import least_squares
warnings.filterwarnings("ignore")
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, ".."))
import reaction_model as M
T = 573.15; F_RECIPE = 20.0; F_CAL = 1.0; C_TRUE = 4e-3; M_SAT = 71.0; SIG = 2.0; TAIL = 1.0
PULSES = [0.1, 0.2, 0.4, 0.8, 1.6, 3.2]
B = dict(L=0.30, R=0.04, p_torr=2.0, flow_sccm=300, n_z=151, zs=(0.20, 0.24)); TRUTH = dict(eta=0.6, beta_wall=2e-3)
A5 = json.load(open(os.path.join(here, "dt_recipe_correction.json")))
fE = np.array(A5["f_of_E"]); E_TGT = A5["E_target"]
front_of = lambda E: float(np.interp(np.log(max(E, 1e-6)), np.log(fE[:, 0]), fE[:, 1]))
def run(tp, F, eta, bw, c_flat):
    """one TMA pulse from a fresh surface: sample p(t) and FlatModel theta at the end of pulse + TAIL."""
    mc = M.ModelCoupling.__new__(M.ModelCoupling); mc.t_step = 0.005; mc.sample_betas = [c_flat, 3e-4]
    mc.model_init(t_step=0.005, T=T, z_max=B["L"], L=B["L"], R=B["R"], S=B["L"] * 2 * np.pi * B["R"], p_torr=B["p_torr"], flow_sccm=B["flow_sccm"], n_z=B["n_z"])
    mc.coupling_init(position_range=B["zs"])
    mc.set_recipe([{'t': tp, 'p': [eta * M.torr_to_pa(B["p_torr"]) * F / (F + B["flow_sccm"]), 0.0]}, {'t': 10.0, 'p': [0.0, 0.0]}])
    win = tp + TAIL; mc.model.setup.construct_time_profile(tau_end=win, D=None, n_out=int(round(win / 0.005)) + 1); mc.model.reset_internal_state()
    _, _, (tt, xx, _) = mc.model.run_model(betas=[bw, 0.0], t_offset=0.0, outlet_type='noflux', method='BDF', return_profile=True)
    p_s = xx[:, 0, mc.flat_model.xpos].mean(axis=1)
    # FlatModel (irreversible, TMA only): theta_{n+1} = theta_n + (1 - theta_n)(1 - exp(-coeff*beta*p_n)) multiplies out to
    # theta_end = 1 - exp(-coeff*beta/dt * int p dt); closed form (identical to stepping, much faster)
    k = float(mc.flat_model.coeff[0].item()) * c_flat / mc.t_step
    th = 1.0 - np.exp(-k * float(np.trapezoid(p_s, tt)))
    return tt, p_s, th
def series(eta, bw, c): return np.array([run(tp, F_CAL, eta, bw, c)[2] for tp in PULSES]) * M_SAT
def exposure(tp, eta, bw): t, p, _ = run(tp, F_RECIPE, eta, bw, C_TRUE); return float(np.trapezoid(p, t))
def tp_for(E, eta, bw, lo=0.05, hi=6.0):
    for _ in range(9):
        mid = np.sqrt(lo * hi); lo, hi = (mid, hi) if exposure(mid, eta, bw) < E else (lo, mid)
    return float(np.sqrt(lo * hi))
ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005; ref.model_init(t_step=0.005, T=T, n_z=51)
def full_chain(tp):
    t, p, _ = run(tp, F_RECIPE, TRUTH["eta"], TRUTH["beta_wall"], C_TRUE)
    ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=1e-4, xpos=None, W=0.1e-3, H=500e-9, T=T, L=0.6e-3,
                        carrier_pressure=M.torr_to_pa(B["p_torr"]), points=240, K=None, logbetas=[np.log(C_TRUE), np.log(3e-4)])
    with torch.no_grad():
        for v in np.interp(np.arange(0, t[-1], 1e-4), t, p): ch.step(torch.tensor([v, 0.0], dtype=torch.float64))
    th = ch.theta[0].numpy().copy(); x = (np.arange(240) + 0.5) * 0.6e-3 / 240 * 1e6
    return float(np.interp(0.5, th[::-1], x[::-1])), x, th
t0 = time.time(); rng = np.random.default_rng(2)
true = series(TRUTH["eta"], TRUTH["beta_wall"], C_TRUE); meas = true + rng.normal(0, SIG, len(PULSES))
print("dose series (truth, ng/cm2):", np.round(true, 1), "\n measured:", np.round(meas, 1), f" [{time.time()-t0:.0f}s]", flush=True)
res = dict(pulses=PULSES, m_sat=M_SAT, sigma=SIG, F_cal=F_CAL, meas=meas.tolist(), true=true.tolist(), fits=[])
for c in (C_TRUE, 2e-3, 8e-3):
    best = None
    for z0 in (np.log([0.5, 1e-3]),):
        f = least_squares(lambda z: (series(np.exp(z[0]), np.exp(z[1]), c) - meas) / SIG, z0, bounds=(np.log([0.02, 1e-6]), np.log([5.0, 0.05])), diff_step=0.05, max_nfev=25)
        if best is None or f.cost < best.cost: best = f
    J = best.jac; cov = np.linalg.pinv(J.T @ J) * (2 * best.cost / max(len(PULSES) - 2, 1)); sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    eta, bw = map(float, np.exp(best.x)); corr = float(cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])) if cov[0, 0] > 0 and cov[1, 1] > 0 else float("nan")
    tp = tp_for(E_TGT, eta, bw); fr, x, th = full_chain(tp)
    tg = np.geomspace(0.05, 6, 16); curve = series_curve = [run(t_, F_CAL, eta, bw, c)[2] * M_SAT for t_ in tg]
    res["fits"].append(dict(c_assumed=c, eta=eta, beta_wall=bw, sd_log=sd.tolist(), corr=corr, chi2=float(2 * best.cost), tp=tp, front_full=fr,
                            curve_t=tg.tolist(), curve_m=list(map(float, curve))))
    if c == C_TRUE: res["check"] = dict(tp=tp, front=fr, x=x.tolist(), theta=th.tolist())
    print(f"assumed c {c:.0e}: eta {eta:.3f} (x/÷{np.exp(sd[0]):.2f}), beta_wall {bw:.2e} (x/÷{np.exp(sd[1]):.2f}), corr {corr:+.2f}, chi2 {2*best.cost:.1f} | recipe {tp:.3f} s -> {fr:.1f} um  [{time.time()-t0:.0f}s]", flush=True)
json.dump(res, open(os.path.join(here, "dt_qcm_doseseries.json"), "w"))
