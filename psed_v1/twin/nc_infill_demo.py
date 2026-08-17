#!/usr/bin/env python3
"""
nc_infill_demo.py
-----------------
Worked example + figure generator for twin/nc_infill_model.py: solves the
diffusion-reaction equations for ALD infill of a nanocrystal network and plots
the precursor concentration and coverage-fraction depth profiles.

The initial conditions are user-defined -- pass `--theta-init` / `--c-init` as a
constant or as any expression in `z` (metres), e.g.

    python3 twin/nc_infill_demo.py --theta-init "0.4*exp(-z/2e-7)"
    python3 twin/nc_infill_demo.py --thickness 3e-6 --pressure 30 --cycles 40

Writes twin/nc_infill_profiles.png (regenerate rather than edit by hand).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twin.nc_infill_model import (                               # noqa: E402
    NCFilm, Precursor, NCInfillModel, default_model)

# dataviz palette: single-hue ordinal ramp for the time series (magnitude), two
# categorical slots for the two dosing strategies (identity).  Both validated
# with scripts/validate_palette.js --mode light.
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
CAT_1, CAT_2 = "#2a78d6", "#eb6834"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#8a8a85"
GRID = "#e6e5e1"


def _profile_arg(text, z):
    """A constant or any numpy expression in `z` -> array over the grid."""
    try:
        return float(text)
    except ValueError:
        env = {k: getattr(np, k) for k in
               ("exp", "log", "sqrt", "sin", "cos", "tanh", "where", "clip",
                "minimum", "maximum", "pi")}
        env["z"] = z
        return np.asarray(eval(text, {"__builtins__": {}}, env), dtype=float)


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8, length=3, color=GRID)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--thickness", type=float, default=1.0e-6, help="film thickness L [m]")
    p.add_argument("--nc-radius", type=float, default=5.0e-9, help="nanocrystal radius [m]")
    p.add_argument("--porosity", type=float, default=0.5, help="initial void fraction [-]")
    p.add_argument("--pressure", type=float, default=100.0, help="precursor partial pressure [Pa]")
    p.add_argument("--sticking", type=float, default=0.01, help="bare-surface reaction probability [-]")
    p.add_argument("--temperature", type=float, default=473.0, help="temperature [K]")
    p.add_argument("--gpc", type=float, default=1.1e-10, help="growth per cycle [m]")
    p.add_argument("--cells", type=int, default=120, help="finite-volume cells")
    p.add_argument("--theta-init", default="0.0", help="initial coverage: constant or expression in z")
    p.add_argument("--c-init", default="0.0", help="initial pore-gas density [m^-3]: constant or expression in z")
    p.add_argument("--cycles", type=int, default=40, help="max cycles for the infill panels")
    p.add_argument("--infill-thickness", type=float, default=2.0e-7,
                   help="film thickness used for the multi-cycle panels [m]")
    p.add_argument("--out", default=str(Path(__file__).with_name("nc_infill_profiles.png")))
    a = p.parse_args(argv)

    film = NCFilm(thickness=a.thickness, nc_radius=a.nc_radius, porosity=a.porosity)
    prec = Precursor("TMA", M=72.09e-3, sticking=a.sticking, pressure=a.pressure)
    m = NCInfillModel(film=film, precursor=prec, T=a.temperature, gpc=a.gpc,
                      n_cells=a.cells)

    print("--- derived quantities " + "-" * 40)
    print("saturation site density Gamma  %.3e m^-2" % m.site_density())
    print("specific surface area   S_v    %.3e m^2/m^3" % m.specific_area()[0])
    print("hydraulic pore radius   r_p    %.3e m" % m.pore_radius()[0])
    print("effective diffusivity   D_e    %.3e m^2/s" % m.effective_diffusivity(prec)[0])
    print("pore diffusion time     L^2/D  %.3e s" % m.diffusion_time(prec))
    print("capacity ratio          alpha  %.3e" % m.capacity_ratio(prec))

    t_est = m.saturation_time_estimate(prec)
    print("sharp-front dose estimate      %.3e s" % t_est)

    # ---- (a),(b) depth profiles during one dose, from user-defined ICs ----
    theta0 = _profile_arg(a.theta_init, m.z)
    c0 = _profile_arg(a.c_init, m.z)
    run = m.simulate_half_cycle(1.3 * t_est, theta_init=theta0, c_init=c0,
                                n_out=261)
    picks = [0.05, 0.15, 0.35, 0.70, 1.25]
    idx = [int(np.argmin(np.abs(run.t - f * t_est))) for f in picks]

    t_sat, _ = m.saturation_dose_time(target=0.99)
    print("dose to 99%% at every depth     %s s" % t_sat)
    t_pg, _ = m.purge_time(residual=1e-3)
    print("purge to 1e-3 of dose density  %s s" % t_pg)

    # ---- (c),(d) multi-cycle infill, two dosing strategies ----
    geom = dict(film=NCFilm(thickness=a.infill_thickness, nc_radius=a.nc_radius,
                            porosity=a.porosity),
                precursor=prec, T=a.temperature, gpc=a.gpc, n_cells=60)
    adaptive = NCInfillModel(**geom)
    ad = adaptive.run_cycles(a.cycles, t_dose=1e3, t_purge=1e-4,
                             dose_target=0.99)
    fixed = NCInfillModel(**geom)
    fx = fixed.run_cycles(a.cycles,
                          t_dose=5.0 * fixed.saturation_time_estimate(prec),
                          t_purge=1e-4)
    print("adaptive dosing: %d cycles to closure, final dose %.3g s"
          % (len(ad.cycle), ad.dose_time[-1]))
    print("fixed dosing:    porosity top %.3f, bottom %.3f after %d cycles"
          % (fx.porosity[-1][0], fx.porosity[-1][-1], len(fx.cycle)))

    # ---- figure ----------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.6))
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axes.ravel():
        ax.set_facecolor("#fcfcfb")
        style(ax)
    zn = run.z * 1e9
    c_dose = m.gas_density(prec.pressure)

    ax = axes[0, 0]
    for k, i in enumerate(idx):
        ax.plot(zn, run.C[i] / c_dose, color=RAMP[k], linewidth=2,
                label="%.2f $t_{sat}$" % picks[k])
    ax.set_xlabel("depth  z  [nm]")
    ax.set_ylabel("$C/C_0$   pore-gas density")
    ax.set_title("(a)  precursor concentration profile", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    # opaque surface-coloured box: the fully saturated curve runs flat at C/C0=1
    # straight through the upper-right corner
    leg = ax.legend(fontsize=8, title="dose time", loc="upper right",
                    facecolor="#fcfcfb", edgecolor="none", framealpha=1.0)
    leg.get_title().set_fontsize(8)
    leg.get_title().set_color(MUTED)
    for txt in leg.get_texts():
        txt.set_color(INK_2)

    ax = axes[0, 1]
    for k, i in enumerate(idx):
        ax.plot(zn, run.theta[i], color=RAMP[k], linewidth=2)
    ax.set_xlabel("depth  z  [nm]")
    ax.set_ylabel(r"$\theta$   coverage fraction")
    ax.set_title("(b)  coverage profile — the saturation front", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    # direct labels instead of a second legend box
    for k, i in enumerate(idx):
        th = run.theta[i]
        j = int(np.argmin(np.abs(th - 0.5)))
        if 0 < j < len(zn) - 1:
            ax.annotate("%.2f $t_{sat}$" % picks[k], xy=(zn[j], 0.5),
                        xytext=(4, 8), textcoords="offset points",
                        fontsize=7.5, color=INK_2)

    ax = axes[1, 0]
    zi = ad.z * 1e9
    ax.plot(zi, ad.porosity[-1], color=CAT_1, linewidth=2,
            label="dose re-sized each cycle")
    ax.plot(zi, fx.porosity[-1], color=CAT_2, linewidth=2,
            label="dose fixed at cycle-1 requirement")
    ax.axhline(adaptive.film.pore_closure_porosity, color=MUTED,
               linewidth=1, linestyle=":")
    ax.annotate("pore closure", xy=(zi[-1], adaptive.film.pore_closure_porosity),
                xytext=(-4, 6), textcoords="offset points", ha="right",
                fontsize=7.5, color=MUTED)
    ax.set_xlabel("depth  z  [nm]")
    ax.set_ylabel(r"porosity  $\varepsilon$  [-]")
    ax.set_title("(c)  porosity left after infill", loc="left", fontsize=10,
                 color=INK, pad=8)
    ax.set_ylim(bottom=-0.02)
    leg = ax.legend(frameon=False, fontsize=8, loc="upper left")
    for txt in leg.get_texts():
        txt.set_color(INK_2)

    ax = axes[1, 1]
    ax.plot(ad.cycle, ad.dose_time, color=CAT_1, linewidth=2,
            marker="o", markersize=4)
    ax.set_yscale("log")
    ax.set_xlabel("ALD cycle")
    ax.set_ylabel("dose time for 99% coverage  [s]")
    ax.set_title("(d)  dose requirement escalates as pores close", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.annotate("%.3g s" % ad.dose_time[-1],
                xy=(ad.cycle[-1], ad.dose_time[-1]), xytext=(-6, 8),
                textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    ax.annotate("%.3g s" % ad.dose_time[0],
                xy=(ad.cycle[0], ad.dose_time[0]), xytext=(6, -12),
                textcoords="offset points", fontsize=8, color=INK_2)

    fig.suptitle("ALD infill of a nanocrystal network — "
                 "%.0f nm film, %.0f%% porous, %.0f nm NCs, %.0f Pa, %.0f K"
                 % (a.thickness * 1e9, a.porosity * 100, a.nc_radius * 2e9,
                    a.pressure, a.temperature),
                 fontsize=11, color=INK, x=0.008, ha="left", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(a.out, dpi=160, facecolor=fig.get_facecolor())
    print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
