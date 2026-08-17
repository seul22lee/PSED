#!/usr/bin/env python3
"""
nc_infill_vs_yanguas.py
-----------------------
Do the nanocrystal-infill model (twin/nc_infill_model.py) and the Yanguas-Gil &
Elam tubular-reactor model (twin/yanguas_gil_reactor.py, JVST A 30, 01A159
(2012)) boil down to the same thing?

THE ALGEBRA

  Yanguas-Gil & Elam, Eqs. (7)-(8), theta = fraction of AVAILABLE sites:

      dn/dt + u dn/dz - D d2n/dz2 = -(1/2R) v_th b_0 theta n
      dtheta/dt                   = -(1/4) s_0 v_th b_0 n theta

  nc_infill_model, theta = fraction of CONSUMED sites, so theta_YG = 1 - theta:

      eps dC/dt - d/dz(D_e dC/dz)  = -S_v Gamma dtheta/dt
      dtheta/dt                    =  b_0 (1-theta) (v_th/4) C / Gamma

  Substituting theta_YG = 1 - theta and s_0 = 1/Gamma (s_0 is the area per
  site, Gamma the sites per area) makes the surface equations *identical*.
  For the gas equation, note that a tube of radius R has S_v = 2/R of wall per
  unit volume, so their 1/(2R) is exactly S_v/4 and the sink terms are the same
  expression written for two geometries.

  What is genuinely different, and only this:

      term            reactor (01A159)        nanocrystal film
      advection       u dn/dz, Pe = uL/D      none; Pe = 0
      accumulation    dn/dt                   eps dC/dt  (void fraction)
      diffusivity     molecular, Eq. (15)     Knudsen, (2/3) r_p v_th eps/tau
      S_v             2/R, fixed              3(1-eps)/r, shrinks each cycle
      sticking        b_0 theta (first order) b_0 (1-theta)^n, n adjustable

  Normalising the infill model the same way (x = C/C_0, xi = z/L,
  tau = t D_e/L^2) gives their Eqs. (9)-(10) with Pe = 0:

      eps dx/dtau - d2x/dxi2 = -Da theta x
      dtheta/dtau            = -gamma Da theta x

      Da    = (S_v/4)(L^2/D_e) v_th b_0      <-> their Eq. (12) with S_v = 2/R
      gamma = C_0 / (S_v Gamma) = 1 / alpha  <-> their Eq. (13), s_0 n_0 R / 2

  So the "excess number" of the reactor paper is the reciprocal of the infill
  model's capacity ratio.  Same equation, different regime.

Writes twin/nc_infill_vs_yanguas.png.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twin.nc_infill_model import default_model                   # noqa: E402
import twin.yanguas_gil_reactor as yg                            # noqa: E402

RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
CAT_1, CAT_2 = "#2a78d6", "#eb6834"
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a85", "#e6e5e1"


def groups(model):
    """Map an NCInfillModel onto (Pe, Da, gamma)."""
    p = model.precursor
    s_v = model.specific_area()[0]
    gamma_site = model.site_density()
    c0 = model.gas_density(p.pressure)
    d_e = model.effective_diffusivity(p)[0]
    v_th = p.thermal_speed(model.T)
    L = model.film.thickness
    return dict(
        Pe=0.0,
        Da=(s_v * v_th * p.sticking / 4.0) * (L ** 2 / d_e),
        gamma=c0 / (s_v * gamma_site),
        tau_per_second=d_e / L ** 2,
    )


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8, length=3, color=GRID)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def legend(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=8, **kw)
    for t in leg.get_texts():
        t.set_color(INK_2)
    return leg


def main():
    m = default_model()
    g = groups(m)
    print("=" * 68)
    print("nanocrystal film  ->  Pe = %.0f   Da = %.4g   gamma = %.4g"
          % (g["Pe"], g["Da"], g["gamma"]))
    print("reactor (01A159)  ->  Pe = %(Pe).0f   Da = %(Da).4g   gamma = %(gamma).4g"
          % yg.PAPER_TMA)
    print("gamma == 1/alpha  ->  %.6g vs %.6g"
          % (g["gamma"], 1.0 / m.capacity_ratio()))
    print("=" * 68)

    # ---- equivalence test: same equations, matched groups -----------------
    t_phys = 0.35 * m.saturation_time_estimate()
    tau = t_phys * g["tau_per_second"]
    mine = m.simulate_half_cycle(t_phys, n_out=3)
    th_mine = mine.theta_final
    xi_mine = m.z / m.film.thickness

    runs = {}
    for key, eps in (("matched", m.film.porosity), ("published", 1.0)):
        r = yg.solve(Pe=0.0, Da=g["Da"], gamma=g["gamma"], tau_end=tau,
                     xi_max=1.0, n_xi=1200, epsilon=eps, outlet="noflux")
        runs[key] = r
        err = np.max(np.abs(th_mine - np.interp(xi_mine, r.xi,
                                                r.growth_profile())))
        print("equivalence, epsilon=%-9s  max|d(theta)| = %.3e" % (eps, err))
    err_pub = np.max(np.abs(th_mine - np.interp(xi_mine, runs["published"].xi,
                                                runs["published"].growth_profile())))

    # ---- what gamma does: timescale, not shape ---------------------------
    gam_runs = []
    for gv in (1e-5, 1e-3, 1e-1, 2.5):
        # dose each to the same coverage state: tau scales as 1/gamma
        r = yg.solve(Pe=0.0, Da=g["Da"], gamma=gv, tau_end=0.18 / gv,
                     xi_max=1.0, n_xi=800, outlet="noflux")
        gam_runs.append((gv, r))
        print("gamma=%-8g tau to reach the same front = %.4g" % (gv, 0.18 / gv))

    # ---- what Pe does: sweeps the front downstream -----------------------
    pe_runs = []
    for pv in (0.0, 10.0, 65.0):
        r = yg.solve(Pe=pv, Da=yg.PAPER_TMA["Da"], gamma=yg.PAPER_TMA["gamma"],
                     tau_end=0.02, xi_max=2.0)
        pe_runs.append((pv, r))

    # ---- what Da does: front sharpness -----------------------------------
    da_runs = []
    for dv in (10.0, 100.0, 1550.0):
        r = yg.solve(Pe=0.0, Da=dv, gamma=yg.PAPER_TMA["gamma"],
                     tau_end=0.06, xi_max=1.0, n_xi=800, outlet="noflux")
        da_runs.append((dv, r))

    # ---- figure ----------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.6))
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axes.ravel():
        ax.set_facecolor("#fcfcfb")
        style(ax)

    ax = axes[0, 0]
    r = runs["published"]
    ax.plot(r.xi, r.growth_profile(), color=CAT_2, linewidth=4.5, alpha=.5,
            label="Yanguas-Gil Eqs. (9)-(10), Pe=0")
    ax.plot(xi_mine, th_mine, color=CAT_1, linewidth=1.8,
            label="nc_infill_model solver")
    ax.set_xlabel(r"$\xi = z/L$")
    ax.set_ylabel(r"$\theta$   consumed fraction")
    ax.set_title("(a)  same equations, same answer", loc="left", fontsize=10,
                 color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    ax.annotate("max |$\\Delta\\theta$| = %.1e" % err_pub, xy=(0.04, 0.12),
                fontsize=8.5, color=MUTED)
    leg = legend(ax, loc="upper right")
    leg.set_frame_on(True)
    leg.get_frame().set_facecolor("#fcfcfb")
    leg.get_frame().set_edgecolor("none")

    ax = axes[0, 1]
    for k, (gv, r) in enumerate(gam_runs):
        ax.plot(r.xi, r.growth_profile(), color=RAMP[k + 1], linewidth=2,
                label=r"$\gamma$ = %g" % gv)
    ax.set_xlabel(r"$\xi = z/L$")
    ax.set_ylabel(r"$\theta$   consumed fraction")
    ax.set_title(r"(b)  $\gamma$ rescales time — until it nears 1", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    ax.annotate(r"each curve at $\tau = 0.18/\gamma$." "\n"
                r"$\gamma \lesssim 0.1$ collapses; at $\gamma$ = 2.5 the" "\n"
                "dose is so short that gas-phase\ntransients still matter",
                xy=(0.03, 0.14), fontsize=8, color=MUTED)
    legend(ax, loc="upper right")

    ax = axes[1, 0]
    for k, (pv, r) in enumerate(pe_runs):
        ax.plot(r.xi, r.growth_profile(), color=RAMP[k + 1], linewidth=2,
                label="Pe = %g" % pv)
    ax.axvline(1.0, color=MUTED, linewidth=1, linestyle=":")
    ax.annotate("reactor exit", xy=(1.0, 0.92), xytext=(5, 0),
                textcoords="offset points", fontsize=7.5, color=MUTED)
    ax.set_xlabel(r"$\xi = z/L$")
    ax.set_ylabel(r"$\theta$   consumed fraction")
    ax.set_title("(c)  advection is the real difference", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    legend(ax, loc="upper right")

    ax = axes[1, 1]
    for k, (dv, r) in enumerate(da_runs):
        ax.plot(r.xi, r.growth_profile(), color=RAMP[k + 1], linewidth=2,
                label="Da = %g" % dv)
    ax.set_xlabel(r"$\xi = z/L$")
    ax.set_ylabel(r"$\theta$   consumed fraction")
    ax.set_title("(d)  Da sets how sharp the front is", loc="left",
                 fontsize=10, color=INK, pad=8)
    ax.set_ylim(-0.03, 1.05)
    legend(ax, loc="upper right")

    fig.suptitle("One equation, two regimes — nanocrystal infill "
                 "(Pe 0, Da %.0f, $\\gamma$ %.0e) vs viscous-flow reactor "
                 "(Pe 65, Da 1550, $\\gamma$ 2.5)" % (g["Da"], g["gamma"]),
                 fontsize=11, color=INK, x=0.008, ha="left", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    out = Path(__file__).with_name("nc_infill_vs_yanguas.png")
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
