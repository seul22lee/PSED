"""ADDED (A5): digital-twin demo - same recipe in two reactors, calibration of reactor B from test chips, corrected recipe.
Uses Larry's ALD_Reactor_Model (through ModelCoupling.model_init / set_recipe) and ChannelModel; no change to reaction_model.py.

Recipe (what an operator sets): TMA source flow F_A [sccm] during the pulse, pulse time t_p, carrier flow Q, pressure p, T.
Inlet TMA partial pressure = eta * p * F_A / (F_A + Q)   (eta: source delivery efficiency - unknown, bottle/valve dependent).
Reactor walls: beta_wall passed to Larry's run_model (reactive walls consume TMA before the sample; 0 = Larry's default D1).
Channel: PillarHall-type lateral gap H = 500 nm, TMA c = 4e-3 (KB campaign / yim20), K = 219 1/Pa (yli18), single TMA pulse.
Target: coverage front (theta = 0.5) at 100 um.

Shortcut (checked at the end): the single-pulse front depends on the TMA exposure at the sample E = int p_s dt,
so the channel model builds front = f(E) once; the reactor model maps recipe -> E. Final recipes are re-checked with the full chain."""
import os, sys, json, time, warnings, numpy as np, torch
warnings.filterwarnings("ignore")
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, ".."))
import reaction_model as M
T = 573.15; F_A = 20.0; TARGET = 100.0; C_TMA, K_TMA = 4e-3, None   # A7: irreversible, as Larry (was K = 219 1/Pa)
REACTORS = {   # geometry and flow known to the twin; eta and beta_wall are the truth the twin does not know
 "A": dict(L=0.64, R=0.0175, p_torr=1.0, flow_sccm=120, n_z=501, zs=(0.31, 0.35), eta=1.0, beta_wall=0.0),
 "B": dict(L=0.30, R=0.04,   p_torr=2.0, flow_sccm=300, n_z=301, zs=(0.20, 0.24), eta=0.6, beta_wall=2e-3),
}
LOG = []
def p_inlet(r, eta):
    g = REACTORS[r]; return eta * M.torr_to_pa(g["p_torr"]) * F_A / (F_A + g["flow_sccm"])
_cache = {}
def sample_trace(r, tp, eta, beta_wall):
    """Larry's reactor model: TMA partial pressure at the sample position vs time for one pulse."""
    key = (r, round(tp, 4), round(eta, 4), beta_wall)
    if key in _cache: return _cache[key]
    g = REACTORS[r]; t0 = time.time()
    mc = M.ModelCoupling.__new__(M.ModelCoupling); mc.t_step = 0.005
    mc.model_init(t_step=0.005, T=T, z_max=g["L"], L=g["L"], R=g["R"], S=g["L"] * 2 * np.pi * g["R"],
                  p_torr=g["p_torr"], flow_sccm=g["flow_sccm"], n_z=g["n_z"])
    mc.set_recipe([{'t': tp, 'p': [p_inlet(r, eta), 0.0]}, {'t': 5.0, 'p': [0.0, 0.0]}])
    z = mc.model.setup.z; zpos = np.where((z >= g["zs"][0]) & (z <= g["zs"][1]))[0]
    win = tp + 0.6   # A8: whole window in one call with Larry's default BDF (C9) instead of RK45 restarts every 5 ms
    mc.model.setup.construct_time_profile(tau_end=win, D=None, n_out=int(round(win / mc.t_step)) + 1); mc.model.reset_internal_state()
    _, _, (tt, xx, _) = mc.model.run_model(betas=[beta_wall, 0.0], t_offset=0.0, outlet_type='noflux', method='BDF', return_profile=True)
    ts, ps = list(tt), list(xx[:, 0, zpos].mean(axis=1))
    out = (np.array(ts), np.array(ps)); _cache[key] = out
    print(f"  reactor {r} tp {tp:.3f} eta {eta:.2f} beta_wall {beta_wall:.0e}: E = {np.trapezoid(out[1], out[0]):.2f} Pa s, peak {out[1].max():.1f} Pa  [{time.time()-t0:.0f}s]", flush=True)
    return out
def exposure(*a): t, p = sample_trace(*a); return float(np.trapezoid(p, t))
def channel_front(t, p, r, H=500e-9, L=0.6e-3, pts=240, dt=1e-4):
    """Larry's ChannelModel driven by the sample trace; returns the theta = 0.5 front [um] and the profile."""
    g = REACTORS[r]; ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005
    ref.model_init(t_step=0.005, T=T, n_z=51)   # only for s0, vth (same species and T in both reactors)
    ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=dt, xpos=None, W=0.1e-3, H=H, T=T, L=L,
                        carrier_pressure=M.torr_to_pa(g["p_torr"]), points=pts, K=K_TMA, logbetas=[np.log(C_TMA), np.log(3e-4)])
    tt = np.arange(0, t[-1], dt); pp = np.interp(tt, t, p)
    with torch.no_grad():
        for v in pp: ch.step(torch.tensor([v, 0.0], dtype=torch.float64))
    th = ch.theta[0].numpy().copy(); x = (np.arange(pts) + 0.5) * L / pts * 1e6
    return float(np.interp(0.5, th[::-1], x[::-1])), x, th
def tp_for_exposure(r, E_target, eta, bw, lo=0.02, hi=3.0):
    """pulse time giving exposure E_target (E increases with tp); bisection on log tp."""
    for _ in range(9):
        mid = np.sqrt(lo * hi)
        if exposure(r, mid, eta, bw) < E_target: lo = mid
        else: hi = mid
    return float(np.sqrt(lo * hi))
res = {}
print("1) channel model: front vs exposure (reactor A pulses)")
fE = []
for tp in (0.05, 0.1, 0.2, 0.4, 0.8):
    t, p = sample_trace("A", tp, 1.0, 0.0); f, x, th = channel_front(t, p, "A")
    fE.append((float(np.trapezoid(p, t)), f)); print(f"   E {fE[-1][0]:6.2f} Pa s -> front {f:6.1f} um", flush=True)
fE = np.array(fE); front_of = lambda E: float(np.interp(np.log(E), np.log(fE[:, 0]), fE[:, 1]))
E_of_front = lambda f: float(np.exp(np.interp(f, fE[:, 1], np.log(fE[:, 0]))))
E_tgt = E_of_front(TARGET); res["f_of_E"] = fE.tolist(); res["E_target"] = E_tgt
print(f"   exposure for a {TARGET:.0f} um front: {E_tgt:.2f} Pa s")
print("2) recipe tuned on reactor A")
tpA = tp_for_exposure("A", E_tgt, 1.0, 0.0); res["tp_A"] = tpA; print(f"   reactor A: t_p = {tpA:.3f} s")
print("3) same recipe in reactor B (truth)")
gB = REACTORS["B"]; EB = exposure("B", tpA, gB["eta"], gB["beta_wall"]); res["B_same_recipe_front"] = front_of(EB)
print(f"   reactor B, same t_p: E = {EB:.2f} Pa s -> front {front_of(EB):.0f} um (target {TARGET:.0f})")
print("4) twin of B before calibration (eta = 1, inert walls)")
E_naive = exposure("B", tpA, 1.0, 0.0); res["B_naive_pred_front"] = front_of(E_naive)
print(f"   predicted front {front_of(E_naive):.0f} um vs measured {front_of(EB):.0f} um")
print("5) calibration: two test chips in B (t_p 0.1 s and 0.4 s), measured fronts with 2 um noise")
rng = np.random.default_rng(0); chips = (0.1, 0.4)
meas = [front_of(exposure("B", tp, gB["eta"], gB["beta_wall"])) + rng.normal(0, 2.0) for tp in chips]
print("   measured fronts:", [round(m, 1) for m in meas])
grid = []
for bw in (0.0, 5e-4, 2e-3, 5e-3):
    for eta in (0.3, 0.6, 1.0):
        pred = [front_of(exposure("B", tp, eta, bw)) for tp in chips]
        grid.append((bw, eta, *pred, float(np.sum((np.array(pred) - meas) ** 2))))
grid = np.array(grid); res["calib_grid"] = grid.tolist()
best = []   # eta refined per beta_wall: fronts are smooth in eta -> quadratic interpolation of SSE over the 3 eta values
for bw in np.unique(grid[:, 0]):
    G = grid[grid[:, 0] == bw]; a, b, c = np.polyfit(np.log(G[:, 1]), G[:, 4], 2)
    le = np.clip(-b / (2 * a), np.log(0.3), np.log(1.0)) if a > 0 else np.log(G[np.argmin(G[:, 4]), 1])
    eta = float(np.exp(le)); pred = [front_of(exposure("B", tp, eta, bw)) for tp in chips]
    best.append((bw, eta, float(np.sum((np.array(pred) - meas) ** 2)))); print(f"   beta_wall {bw:.0e}: eta {eta:.2f}, SSE {best[-1][2]:.1f} um^2")
bw_fit, eta_fit, _ = min(best, key=lambda b: b[2]); res["calibrated"] = dict(beta_wall=bw_fit, eta=eta_fit, truth=dict(beta_wall=gB["beta_wall"], eta=gB["eta"]))
print(f"   calibrated twin: eta {eta_fit:.2f} (truth {gB['eta']}), beta_wall {bw_fit:.0e} (truth {gB['beta_wall']:.0e})")
print("6) corrected recipe for B from the calibrated twin")
tpB = tp_for_exposure("B", E_tgt, eta_fit, bw_fit); res["tp_B_corrected"] = tpB; print(f"   reactor B: t_p = {tpB:.3f} s (was {tpA:.3f} s)")
print("7) check with the full chain (reactor B truth -> ChannelModel)")
for name, tp in (("same recipe", tpA), ("corrected", tpB)):
    t, p = sample_trace("B", tp, gB["eta"], gB["beta_wall"]); f, x, th = channel_front(t, p, "B")
    res[f"check_{name}"] = dict(tp=tp, front=f, x=x.tolist(), theta=th.tolist(), t=t.tolist(), p=p.tolist()); print(f"   {name}: t_p {tp:.3f} s -> front {f:.1f} um")
tA, pA = sample_trace("A", tpA, 1.0, 0.0); fA, xA, thA = channel_front(tA, pA, "A")
res["check_A"] = dict(tp=tpA, front=fA, x=xA.tolist(), theta=thA.tolist(), t=tA.tolist(), p=pA.tolist()); print(f"   reactor A: t_p {tpA:.3f} s -> front {fA:.1f} um")
json.dump(res, open(os.path.join(here, "dt_recipe_correction.json"), "w"))
