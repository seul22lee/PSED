#!/usr/bin/env python3
"""Sample results for the Ylilammi channel model (ylilammi_twin.py).

Produces ylilammi_samples.png with four panels:
  (a) validation against the paper's own Al2O3 & TiO2 fits (Figs 6-7 / Table I),
  (b) pulse-time sweep      — thickness profile vs pulse length,
  (c) precursor-pressure sweep — thickness profile vs pA0,
  (d) half-thickness penetration xp vs pulse time, showing xp ~ sqrt(pA0 * tp).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ylilammi_twin import AL2O3, TIO2, thickness_profile, penetration_depth

UM, NM = 1e6, 1e9


def _profile(tp, pA0, rec):
    x, s = thickness_profile(tp, pA0, rec)
    return x * UM, s * NM, penetration_depth(x, s) * UM


fig, ax = plt.subplots(2, 2, figsize=(12, 9))
fig.suptitle("Virtual ALD-in-a-channel model  (Ylilammi et al., J. Appl. Phys. 123, 205301, 2018)\n"
             "inputs: pulse time t$_p$ and precursor pressure p$_{A0}$   →   output: thickness profile s(x)",
             fontsize=12)

# (a) validation vs the paper -------------------------------------------------
axa = ax[0, 0]
for rec, col in ((AL2O3, "tab:blue"), (TIO2, "tab:red")):
    xu, sn, xp = _profile(rec['tp'], rec['pA0_fit'], rec)
    axa.plot(xu, sn, color=col, lw=2,
             label=f"{rec['name']}  (t$_p$={rec['tp']} s, p$_{{A0}}$={rec['pA0_fit']} Pa)")
    axa.axvline(xp, color=col, ls=":", lw=1)
axa.set_title("(a) validation — reproduces the paper's Al$_2$O$_3$/TiO$_2$ fits")
axa.set_xlabel("distance into channel x (µm)")
axa.set_ylabel("film thickness s (nm)")
axa.legend(fontsize=9)
axa.grid(alpha=0.3)

# (b) pulse-time sweep (Al2O3, pA0 fixed) ------------------------------------
axb = ax[0, 1]
pA0 = AL2O3['pA0_fit']
for tp, col in zip([0.02, 0.05, 0.1, 0.2, 0.5],
                   plt.cm.viridis(np.linspace(0.15, 0.9, 5))):
    xu, sn, xp = _profile(tp, pA0, AL2O3)
    axb.plot(xu, sn, color=col, lw=1.8, label=f"t$_p$={tp:g} s  (x$_p$={xp:.0f} µm)")
axb.set_title(f"(b) pulse-time sweep — Al$_2$O$_3$, p$_{{A0}}$={pA0:.0f} Pa fixed")
axb.set_xlabel("distance into channel x (µm)")
axb.set_ylabel("film thickness s (nm)")
axb.legend(fontsize=8)
axb.grid(alpha=0.3)

# (c) precursor-pressure sweep (Al2O3, tp fixed) -----------------------------
axc = ax[1, 0]
tp = AL2O3['tp']
for pA0, col in zip([20, 50, 100, 200, 400],
                    plt.cm.plasma(np.linspace(0.1, 0.85, 5))):
    xu, sn, xp = _profile(tp, pA0, AL2O3)
    axc.plot(xu, sn, color=col, lw=1.8, label=f"p$_{{A0}}$={pA0} Pa  (x$_p$={xp:.0f} µm)")
axc.set_title(f"(c) precursor-pressure sweep — Al$_2$O$_3$, t$_p$={tp:g} s fixed")
axc.set_xlabel("distance into channel x (µm)")
axc.set_ylabel("film thickness s (nm)")
axc.legend(fontsize=8)
axc.grid(alpha=0.3)

# (d) penetration depth scaling ----------------------------------------------
axd = ax[1, 1]
tps = np.array([0.02, 0.03, 0.05, 0.08, 0.12, 0.2, 0.3, 0.5])
for pA0, col in zip([50, 100, 200, 400],
                    plt.cm.plasma(np.linspace(0.1, 0.85, 4))):
    xps = [penetration_depth(*thickness_profile(tp, pA0, AL2O3)) * UM for tp in tps]
    axd.plot(np.sqrt(pA0 * tps), xps, "o-", color=col, lw=1.6, ms=5,
             label=f"p$_{{A0}}$={pA0} Pa")
axd.set_title("(d) penetration collapses onto  x$_p$ $\\propto$ $\\sqrt{p_{A0}\\,t_p}$")
axd.set_xlabel(r"$\sqrt{p_{A0}\, t_p}$  (Pa$^{1/2}$ s$^{1/2}$)")
axd.set_ylabel("half-thickness penetration x$_p$ (µm)")
axd.legend(fontsize=9)
axd.grid(alpha=0.3)

fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig("ylilammi_samples.png", dpi=130)
print("wrote ylilammi_samples.png")

# --- numeric summary table --------------------------------------------------
print("\n=== penetration depth x_p (um), Al2O3 ===")
hdr = "pA0 \\ tp"
print(f"{hdr:>9} " + "".join(f"{t:>8g}" for t in [0.02, 0.05, 0.1, 0.2, 0.5]))
for pA0 in [20, 50, 100, 200, 400]:
    row = [penetration_depth(*thickness_profile(tp, pA0, AL2O3)) * UM for tp in [0.02, 0.05, 0.1, 0.2, 0.5]]
    print(f"{pA0:>7} Pa " + "".join(f"{v:>8.0f}" for v in row))
