"""ADDED (A7): redo only the recipe step and the full-chain check of A6 from its saved fits (eta, beta_wall).
Used after switching the channel model to irreversible (K = None, as Larry): the QCM fits (FlatModel, irreversible) do not change,
the target exposure (from A5 f(E)) and the channel response do."""
import os, json, numpy as np, torch
here = os.path.dirname(os.path.abspath(__file__)); g = {"__file__": os.path.join(here, "dt_qcm_calibration.py")}
exec(open(g["__file__"]).read().split("res = {}")[0], g)
M, T, B, TRUTH = g["M"], g["T"], g["B"], g["TRUTH"]
res = json.load(open(os.path.join(here, "dt_qcm_calibration.json")))
ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005; ref.model_init(t_step=0.005, T=T, n_z=51)
def full_chain(tp):
    t, p, _ = g["run"](tp, g["F_RECIPE"], TRUTH["eta"], TRUTH["beta_wall"], g["C_TRUE"])
    ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=1e-4, xpos=None, W=0.1e-3, H=500e-9, T=T, L=0.6e-3,
                        carrier_pressure=M.torr_to_pa(B["p_torr"]), points=240, K=g["K_TMA"], logbetas=[np.log(g["C_TRUE"]), np.log(3e-4)])
    with torch.no_grad():
        for v in np.interp(np.arange(0, t[-1], 1e-4), t, p): ch.step(torch.tensor([v, 0.0], dtype=torch.float64))
    th = ch.theta[0].numpy().copy(); x = (np.arange(240) + 0.5) * 0.6e-3 / 240 * 1e6
    return float(np.interp(0.5, th[::-1], x[::-1])), x, th, float(np.trapezoid(p, t))
print("target exposure (A5):", round(g["E_TGT"], 3), "Pa s")
for f in res["fits"]:
    f["tp"] = g["tp_for"](g["E_TGT"], f["eta"], f["beta_wall"])
    f["front_full"], x, th, f["E_truth"] = full_chain(f["tp"]); f["front_fE"] = g["front_of"](f["E_truth"])
    print(f"assumed c {f['c_assumed']:.0e}: t_p {f['tp']:.3f} s -> full chain {f['front_full']:.1f} um (shortcut {f['front_fE']:.1f})", flush=True)
    if abs(f["c_assumed"] - g["C_TRUE"]) < 1e-12: res["check"] = dict(tp=f["tp"], front=f["front_full"], x=x.tolist(), theta=th.tolist())
json.dump(res, open(os.path.join(here, "dt_qcm_calibration.json"), "w"))
