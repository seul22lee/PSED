"""ADDED (A9): full recipe for reactor B from the calibrated twin (A6, c from KB): TMA pulse, TMA purge, H2O pulse, H2O purge.
Models: Larry's reactor model (one BDF call per window, C9; both reactants, walls via betas) and ChannelModel (irreversible, A7;
H2O resets the TMA coverage, C4). Criteria (stated, adjustable):
  TMA pulse  - TMA coverage front (theta = 0.5) at 100 um (from A6).
  purges     - partial pressure at the sample below 1e-3 of its pulse peak (reactor gas only; wall desorption is not modelled,
               so these are lower bounds). The channel empties in ~ms (Knudsen), checked.
  H2O pulse  - after H2O, remaining TMA coverage theta < 0.1 everywhere in 0-100 um (H2O must not limit the depth).
Assumptions: H2O delivered through the same source/valve model as TMA (eta_H2O = calibrated eta, source 20 sccm-equivalent);
wall reactivity for H2O = c_H2O from the KB (3e-4; walls are the same Al2O3 surface). Verification on reactor B truth (eta 0.6)."""
import os, json, time, warnings, numpy as np, torch
warnings.filterwarnings("ignore")
here = os.path.dirname(os.path.abspath(__file__)); import sys; sys.path.insert(0, os.path.join(here, ".."))
import reaction_model as M
T = 573.15; F_SRC = 20.0; C_TMA, C_H2O = 4e-3, 3e-4; THR = 1e-3; TARGET = 100.0
B = dict(L=0.30, R=0.04, p_torr=2.0, flow_sccm=300, n_z=301, zs=(0.20, 0.24))
A6 = json.load(open(os.path.join(here, "dt_qcm_doseseries.json"))); fit = [f for f in A6["fits"] if abs(f["c_assumed"] - C_TMA) < 1e-12][0]   # A11: twin from the QCM dose series
TWIN = dict(eta=fit["eta"], bw=[fit["beta_wall"], C_H2O]); TRUTH = dict(eta=0.6, bw=[2e-3, C_H2O]); TP_A = fit["tp"]
p_in = lambda eta: eta * M.torr_to_pa(B["p_torr"]) * F_SRC / (F_SRC + B["flow_sccm"])
def reactor(stages, eta, bw, tail):
    """stages: list of (duration, tma_on, h2o_on). Returns t, p_TMA(t), p_H2O(t) at the sample."""
    mc = M.ModelCoupling.__new__(M.ModelCoupling); mc.t_step = 0.005
    mc.model_init(t_step=0.005, T=T, z_max=B["L"], L=B["L"], R=B["R"], S=B["L"] * 2 * np.pi * B["R"], p_torr=B["p_torr"], flow_sccm=B["flow_sccm"], n_z=B["n_z"])
    mc.set_recipe([{'t': d, 'p': [p_in(eta) * a, p_in(eta) * b]} for d, a, b in stages] + [{'t': tail + 5.0, 'p': [0.0, 0.0]}])
    z = mc.model.setup.z; zpos = np.where((z >= B["zs"][0]) & (z <= B["zs"][1]))[0]
    win = sum(d for d, _, _ in stages) + tail
    mc.model.setup.construct_time_profile(tau_end=win, D=None, n_out=int(round(win / 0.005)) + 1); mc.model.reset_internal_state()
    _, _, (t, x, _) = mc.model.run_model(betas=bw, t_offset=0.0, outlet_type='noflux', method='BDF', return_profile=True)
    return t, x[:, 0, zpos].mean(axis=1), x[:, 1, zpos].mean(axis=1)
ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005; ref.model_init(t_step=0.005, T=T, n_z=51)
def channel(t, pA, pB, dt=1e-4):
    ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=dt, xpos=None, W=0.1e-3, H=500e-9, T=T, L=0.6e-3,
                        carrier_pressure=M.torr_to_pa(B["p_torr"]), points=240, K=None, logbetas=[np.log(C_TMA), np.log(C_H2O)])
    tt = np.arange(0, t[-1], dt); a = np.interp(tt, t, pA); b = np.interp(tt, t, pB); hist = {}
    with torch.no_grad():
        for k, (va, vb) in enumerate(zip(a, b)):
            ch.step(torch.tensor([va, vb], dtype=torch.float64))
    x = (np.arange(240) + 0.5) * 0.6e-3 / 240 * 1e6
    return x, ch.theta[0].numpy().copy(), ch.x.numpy().copy()
def purge_time(t, p, t_end):
    """time after t_end until p stays below THR * peak."""
    pk = p.max(); after = t >= t_end; bad = np.where(after & (p > THR * pk))[0]
    return float(t[bad[-1]] - t_end) if len(bad) else 0.0
t0 = time.time(); res = dict(criteria=dict(purge_threshold=THR, h2o_theta_max=0.1, target_um=TARGET), twin=TWIN, truth=TRUTH)
print(f"twin of B (from A6): eta {TWIN['eta']:.3f}, beta_wall TMA {TWIN['bw'][0]:.2e}, H2O {TWIN['bw'][1]:.0e}; TMA pulse {TP_A:.3f} s")
# 1) TMA purge from the twin
t, pA, _ = reactor([(TP_A, 1, 0)], TWIN["eta"], TWIN["bw"], tail=20.0)
tP1 = purge_time(t, pA, TP_A); print(f"1) TMA purge: sample p_TMA < {THR:g} x peak ({pA.max():.2f} Pa) after {tP1:.2f} s  [{time.time()-t0:.0f}s]", flush=True)
tP1 = float(np.ceil(tP1 * 10) / 10)
# 2) H2O pulse: shortest pulse with theta < 0.1 in 0-100 um after H2O (twin)
def after_h2o(tB, P, tail=1.0):
    t, pA, pB = reactor([(TP_A, 1, 0), (tP1, 0, 0), (tB, 0, 1)], P["eta"], P["bw"], tail=tail)
    x, th, _ = channel(t, pA, pB); return x, th, t, pA, pB
def h2o_ok(tB):
    x, th, *_ = after_h2o(tB, TWIN); v = float(th[x <= TARGET].max()); print(f"   H2O {tB:.3f} s -> max theta(0-100 um) {v:.3f}  [{time.time()-t0:.0f}s]", flush=True); return v
lo, hi = 0.02, 0.02
while h2o_ok(hi) >= 0.1: lo, hi = hi, hi * 2
for _ in range(5):
    mid = np.sqrt(lo * hi)
    if h2o_ok(mid) < 0.1: hi = mid
    else: lo = mid
tB = float(np.ceil(hi * 100) / 100); print(f"2) H2O pulse {tB:.2f} s", flush=True)
# 3) H2O purge from the twin
t, pA, pB = reactor([(TP_A, 1, 0), (tP1, 0, 0), (tB, 0, 1)], TWIN["eta"], TWIN["bw"], tail=40.0)
tP2 = purge_time(t, pB, TP_A + tP1 + tB); tP2 = float(np.ceil(tP2 * 10) / 10); print(f"3) H2O purge {tP2:.1f} s", flush=True)
res["recipe"] = dict(tma_pulse=TP_A, tma_purge=tP1, h2o_pulse=tB, h2o_purge=tP2)
# 4) verify the whole cycle on reactor B truth
x, th1, _ = None, None, None
t, pA, pB = reactor([(TP_A, 1, 0), (tP1, 0, 0), (tB, 0, 1), (tP2, 0, 0)], TRUTH["eta"], TRUTH["bw"], tail=0.5)
t_end_A = TP_A; mA = t <= TP_A + 0.6
xA, thA, _ = channel(t[mA], pA[mA], pB[mA]); frontA = float(np.interp(0.5, thA[::-1], xA[::-1]))
x, th, gas = channel(t, pA, pB)
cvd = float(np.trapezoid(np.minimum(pA, pB) * 0 + pA * (pB > THR * pB.max()), t))   # TMA exposure while H2O is present at the sample
res["verify"] = dict(tma_front=frontA, theta_after_cycle_max_0_100=float(th[x <= TARGET].max()), tma_at_h2o_arrival_Pa=float(np.interp(TP_A + tP1, t, pA)),
                     tma_exposure_during_h2o_Pa_s=cvd, x=x.tolist(), theta_after_tma=thA.tolist(), theta_after_cycle=th.tolist(),
                     t=t.tolist(), pA=pA.tolist(), pB=pB.tolist())
print(f"4) truth check: TMA front {frontA:.1f} um; after full cycle max theta(0-100 um) {res['verify']['theta_after_cycle_max_0_100']:.3f}; "
      f"TMA at the sample when H2O starts {res['verify']['tma_at_h2o_arrival_Pa']:.4f} Pa; TMA exposure overlapping H2O {cvd:.4f} Pa s  [{time.time()-t0:.0f}s]")
print("RECIPE (reactor B):", {k: round(v, 3) for k, v in res["recipe"].items()})
json.dump(res, open(os.path.join(here, "dt_full_recipe.json"), "w"))
