"""ADDED (A5): figure for demo/dt_recipe_correction.py."""
import os, json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__)); r = json.load(open(os.path.join(here, "dt_recipe_correction.json")))
A, S, C = r["check_A"], r["check_same recipe"], r["check_corrected"]
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
for d, lab, st in ((A, f"reactor A, t_p {A['tp']:.2f} s", "k-"), (S, f"reactor B, same recipe ({S['tp']:.2f} s)", "C3--"), (C, f"reactor B, corrected ({C['tp']:.2f} s)", "C0-")):
    ax[0].plot(d["t"], d["p"], st, label=lab); ax[1].plot(d["x"], d["theta"], st, label=f"{lab}: front {d['front']:.0f} µm")
ax[0].set(xlabel="time (s)", ylabel="TMA partial pressure at sample (Pa)", title="Larry reactor model: sample-position pulse"); ax[0].legend(fontsize=8)
ax[1].axvline(100, color="gray", ls=":"); ax[1].set(xlabel="depth in 500 nm gap (µm)", ylabel="coverage θ after one pulse", title="ChannelModel: target front 100 µm", xlim=(0, 250)); ax[1].legend(fontsize=8)
G = np.array(r["calib_grid"]); bws = np.unique(G[:, 0]); etas = np.unique(G[:, 1])
Z = np.array([[G[(G[:, 0] == b) & (G[:, 1] == e), 4][0] for e in etas] for b in bws])
im = ax[2].imshow(np.log10(Z + 1), origin="lower", aspect="auto", cmap="viridis")
ax[2].set_xticks(range(len(etas)), [f"{e:.1f}" for e in etas]); ax[2].set_yticks(range(len(bws)), [f"{b:.0e}" for b in bws])
cal = r["calibrated"]; ax[2].set(xlabel="delivery efficiency η", ylabel="wall reactivity β_wall",
    title=f"calibration misfit (2 chips)\nfit η {cal['eta']:.2f}, β {cal['beta_wall']:.0e}  |  truth η {cal['truth']['eta']}, β {cal['truth']['beta_wall']:.0e}")
plt.colorbar(im, ax=ax[2], label="log10(SSE + 1), µm²"); fig.tight_layout(); fig.savefig(os.path.join(here, "dt_recipe_correction.png"), dpi=100)
