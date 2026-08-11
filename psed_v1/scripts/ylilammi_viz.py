#!/usr/bin/env python3
"""Extra visualizations for the Ylilammi channel model (ylilammi_twin.py).

Generates two more figures beyond ylilammi_samples.png:
  ylilammi_dynamics.png  — what happens INSIDE one pulse and OVER many cycles
  ylilammi_window.png    — process-window map: penetration depth vs (t_p, p_A0)
"""
import copy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twin import ylilammi_twin as yl
from twin.ylilammi_twin import AL2O3, thickness_profile, penetration_depth

UM, NM = 1e6, 1e9

# Fig-4 demonstration recipe (straight from the paper's Fig 2-5 captions):
# pA0=100 Pa, T=500 K, K=100, c=0.01, q=5e18, gpc_sat=106 pm, 1000 cycles.
DEMO = dict(name='demo', MA=0.0749, dA=591e-12, MB=0.028, dB=374e-12, pB=300.0,
            T=500.0, H0=500e-9, W=0.1e-3, cycles=1000, c=0.01, K=100.0,
            q=5e18, gpc_sat=106e-12, pA0_fit=100.0, tp=0.1, scan_length=700e-6)


# ======================================================================
# FIGURE 1 — dynamics inside a pulse and across cycles
# ======================================================================
fig, ax = plt.subplots(2, 2, figsize=(12, 9))
fig.suptitle("Ylilammi channel model — dynamics inside a pulse and across cycles", fontsize=13)

# (a) reactant-pressure front advancing during ONE pulse (reproduces Fig 2) ----
axa = ax[0, 0]
rec = DEMO
pA0 = rec['pA0_fit']
x = np.linspace(0, 200e-6, 400)
Deff, h = yl._D_eff(rec, rec['H0'], pA0)
D = yl._D_app(rec, rec['H0'], pA0, Deff)
for t, col in zip([0.01, 0.02, 0.05, 0.1], plt.cm.cool(np.linspace(0.1, 0.9, 4))):
    xs = np.sqrt(D * t)
    pA = np.clip(yl._pressure(x, xs, Deff, h, rec, pA0), 0, None)
    axa.plot(x * UM, pA, color=col, lw=1.9, label=f"t = {t:g} s")
axa.set_title("(a) reactant pressure front advancing during one pulse  (cf. Fig 2)")
axa.set_xlabel("distance x (µm)")
axa.set_ylabel("reactant pressure p$_A$ (Pa)")
axa.legend(fontsize=9); axa.grid(alpha=0.3)

# (b) surface-coverage front during the pulse (reproduces Fig 3) ---------------
axb = ax[0, 1]
for t, col in zip([0.01, 0.02, 0.05, 0.1], plt.cm.cool(np.linspace(0.1, 0.9, 4))):
    th, _ = yl._cycle_coverage(x, rec, rec['H0'], pA0, t)
    axb.plot(x * UM, th, color=col, lw=1.9, label=f"t = {t:g} s")
axb.set_title("(b) surface coverage θ(x) filling in during one pulse  (cf. Fig 3)")
axb.set_xlabel("distance x (µm)")
axb.set_ylabel("surface coverage θ")
axb.set_ylim(0, 1.05); axb.legend(fontsize=9); axb.grid(alpha=0.3)

# (c) thickness building up over cycles (Al2O3) -------------------------------
axc = ax[1, 0]
for N, col in zip([25, 50, 100, 250, 500], plt.cm.viridis(np.linspace(0.15, 0.9, 5))):
    r = copy.deepcopy(AL2O3); r['cycles'] = N
    xu, s = thickness_profile(AL2O3['tp'], AL2O3['pA0_fit'], r)
    axc.plot(xu * UM, s * NM, color=col, lw=1.8, label=f"N = {N} cycles")
axc.set_title("(c) film thickness building up over cycles  —  Al$_2$O$_3$")
axc.set_xlabel("distance x (µm)")
axc.set_ylabel("film thickness s (nm)")
axc.legend(fontsize=9); axc.grid(alpha=0.3)

# (d) channel-height sweep (reproduces Fig 4) --------------------------------
axd = ax[1, 1]
for H0, col in zip([2e-6, 1e-6, 0.5e-6, 0.2e-6], plt.cm.autumn(np.linspace(0.05, 0.7, 4))):
    r = copy.deepcopy(DEMO); r['H0'] = H0; r['scan_length'] = 700e-6
    xu, s = thickness_profile(r['tp'], r['pA0_fit'], r)
    axd.plot(xu * UM, s * NM, color=col, lw=1.8, label=f"H = {H0*UM:g} µm")
axd.set_title("(d) narrower channels fill less — the 0.2 µm gap plugs up  (cf. Fig 4)")
axd.set_xlabel("distance x (µm)")
axd.set_ylabel("film thickness s (nm)")
axd.legend(fontsize=9); axd.grid(alpha=0.3)

fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("ylilammi_dynamics.png", dpi=130)
print("wrote ylilammi_dynamics.png")


# ======================================================================
# FIGURE 2 — process-window map: penetration depth vs (t_p, p_A0)
# ======================================================================
tps = np.geomspace(0.01, 0.5, 22)
ps = np.geomspace(10, 400, 18)
Z = np.zeros((len(ps), len(tps)))
r = copy.deepcopy(AL2O3); r['scan_length'] = 400e-6      # widen so deep cases aren't clipped
for i, pA0 in enumerate(ps):
    for j, tp in enumerate(tps):
        xu, s = thickness_profile(tp, pA0, r)
        Z[i, j] = penetration_depth(xu, s) * UM

fig2, ax2 = plt.subplots(figsize=(8.5, 6.2))
pcm = ax2.pcolormesh(tps, ps, Z, shading="gouraud", cmap="magma")
cs = ax2.contour(tps, ps, Z, levels=[50, 100, 150, 200, 300], colors="white", linewidths=1.1)
ax2.clabel(cs, fmt="%d µm", fontsize=9)
ax2.set_xscale("log"); ax2.set_yscale("log")
ax2.set_xlabel("pulse time t$_p$ (s)")
ax2.set_ylabel("precursor pressure p$_{A0}$ (Pa)")
ax2.set_title("Process window — half-thickness penetration depth x$_p$ (µm)\n"
              "Al$_2$O$_3$; white contours are constant penetration (x$_p$ ∝ $\\sqrt{p_{A0} t_p}$)")
fig2.colorbar(pcm, ax=ax2, label="penetration depth x$_p$ (µm)")
fig2.tight_layout()
fig2.savefig("ylilammi_window.png", dpi=130)
print("wrote ylilammi_window.png")
