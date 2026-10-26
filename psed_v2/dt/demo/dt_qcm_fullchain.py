"""ADDED (A6b): full-chain check (reactor B truth -> Larry's ChannelModel) for every A6 recipe, so panel g of F2 uses the
same calculation as panel f (A6 reported the c = 2e-3 and 8e-3 cases only through the front-vs-exposure shortcut)."""
import os, json, numpy as np, torch
here = os.path.dirname(os.path.abspath(__file__)); g = {"__file__": os.path.join(here, "dt_qcm_calibration.py")}
exec(open(g["__file__"]).read().split("res = {}")[0], g)
M, T, B, TRUTH = g["M"], g["T"], g["B"], g["TRUTH"]
res = json.load(open(os.path.join(here, "dt_qcm_calibration.json")))
ref = M.ModelCoupling.__new__(M.ModelCoupling); ref.t_step = 0.005; ref.model_init(t_step=0.005, T=T, n_z=51)
for f in res["fits"]:
    t, p, _ = g["run"](f["tp"], g["F_RECIPE"], TRUTH["eta"], TRUTH["beta_wall"], g["C_TRUE"])
    ch = M.ChannelModel(s0=ref.model.s0s, vth=ref.model.vths, dt=1e-4, xpos=None, W=0.1e-3, H=500e-9, T=T, L=0.6e-3,
                        carrier_pressure=M.torr_to_pa(B["p_torr"]), points=240, K=g["K_TMA"], logbetas=[np.log(g["C_TRUE"]), np.log(3e-4)])
    with torch.no_grad():
        for v in np.interp(np.arange(0, t[-1], 1e-4), t, p): ch.step(torch.tensor([v, 0.0], dtype=torch.float64))
    th = ch.theta[0].numpy(); x = (np.arange(240) + 0.5) * 0.6e-3 / 240 * 1e6
    f["front_full"] = float(np.interp(0.5, th[::-1], x[::-1]))
    print(f"assumed c {f['c_assumed']:.0e}: t_p {f['tp']:.3f} s -> full chain {f['front_full']:.1f} um (shortcut {f['front_fE']:.1f})", flush=True)
json.dump(res, open(os.path.join(here, "dt_qcm_calibration.json"), "w"))
