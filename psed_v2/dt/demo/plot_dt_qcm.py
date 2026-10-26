"""ADDED (A6): figure for demo/dt_qcm_calibration.py."""
import os, json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__)); r = json.load(open(os.path.join(here, "dt_qcm_calibration.json")))
m = r["meas"]; fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
ax[0].plot(m["t_model"], m["theta_true"], "k-", lw=1, label="truth (η 0.6, β_wall 2e-3)"); ax[0].plot(m["t"], m["theta"], "ko", ms=4, label="QCM-like data (20 Hz, σ 0.01)")
for f, col in zip(r["fits"], ("C0", "C3", "C2")):
    ax[0].plot(f["t_fit"], f["theta_fit"], "--", color=col, label=f"fit, assumed c {f['c_assumed']:.0e}: η {f['eta']:.2f}, β {f['beta_wall']:.1e}")
ax[0].set(xlabel="time (s)", ylabel="sample coverage θ (FlatModel)", title="low-dose calibration pulse in reactor B"); ax[0].legend(fontsize=7)
cs = [f["c_assumed"] for f in r["fits"]]; o = np.argsort(cs)
ax[1].plot(np.array(cs)[o], np.array([f["eta"] for f in r["fits"]])[o], "o-", label="fitted η"); ax[1].axhline(0.6, color="gray", ls=":", label="true η")
ax[1].plot(np.array(cs)[o], np.array([f["beta_wall"] for f in r["fits"]])[o] / 2e-3 * 0.6, "s--", label="fitted β_wall (scaled, true at 0.6)")
ax[1].axvline(4e-3, color="k", ls=":", lw=.8); ax[1].set(xscale="log", xlabel="sample sticking c assumed in the twin", ylabel="η", title="flat data fix c·η, not c and η"); ax[1].legend(fontsize=7)
ax[2].bar([f"{c:.0e}" for c in np.array(cs)[o]], np.array([f["front_fE"] for f in r["fits"]])[o], color=["C3", "C0", "C2"])
ax[2].axhline(100, color="k", ls=":"); ax[2].set(xlabel="assumed c (true 4e-3)", ylabel="front in reactor B truth (µm)", title=f"corrected recipe outcome (target 100 µm)\nfull-chain check at true c: {r['check']['front']:.0f} µm")
for i, f in enumerate(np.array(r["fits"])[o]): ax[2].text(i, f["front_fE"] + 2, f"t_p {f['tp']:.2f} s", ha="center", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(here, "dt_qcm_calibration.png"), dpi=100)
