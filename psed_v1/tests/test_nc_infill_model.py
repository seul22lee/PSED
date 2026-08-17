#!/usr/bin/env python3
"""Validation for twin/nc_infill_model.py -- the diffusion-reaction model for ALD
infill of a nanocrystal network.

The solver is checked against the limits where the answer is known analytically
(pure Langmuir kinetics, sharp-front shrinking-core scaling), against exact
conservation laws (precursor inventory, deposited volume), and for grid
independence.

Run:  python3 tests/test_nc_infill_model.py
"""
import sys
from pathlib import Path

import numpy as np

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
from twin.nc_infill_model import (                            # noqa: E402
    NCInfillModel, NCFilm, Precursor, default_model, kB, NA)

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def close(a, b, rtol):
    return abs(a - b) <= rtol * abs(b)


def main():
    print("=== A. derived quantities ===")
    m = default_model()
    # Gamma is defined so that one fully saturated cycle deposits exactly gpc.
    gamma = m.site_density()
    gpc_back = (gamma * m.metal_per_molecule / m.metal_per_formula
                * m.film_molar_mass / (m.film_density * NA))
    ok("Gamma round-trips to GPC", close(gpc_back, m.gpc, 1e-12),
       (gpc_back, m.gpc))

    # spheres: S_v = 3(1-eps)/r, r_p = 2 eps / S_v
    ok("S_v = 3(1-eps)/r", close(m.specific_area()[0],
                                 3 * (1 - 0.5) / 5e-9, 1e-12))
    ok("pore radius = 2 eps / S_v",
       close(m.pore_radius()[0], 2 * 0.5 / m.specific_area()[0], 1e-12))
    # thermal speed of TMA at 473 K
    v_th = m.precursor.thermal_speed(m.T)
    ok("v_th in range for TMA @473K", 350.0 < v_th < 400.0, v_th)
    ok("capacity ratio >> 1 (front regime)", m.capacity_ratio() > 1e3,
       m.capacity_ratio())

    print("\n=== B. kinetic limit: no transport resistance -> Langmuir ===")
    # When consumption is slow enough that the pore gas is never depleted, the
    # solution must collapse to the well-mixed Langmuir result
    # theta(t) = 1 - exp(-k_ads t).  The depletion at the bottom scales as
    # S_v Gamma k_ads L^2 / (2 D_e C_ref), so a thin film *and* a small
    # sticking coefficient are both needed: at s_0 = 0.01 and L = 10 nm the
    # depletion is still ~5%, which is real physics, not solver error.
    thin = default_model(film=NCFilm(thickness=1.0e-8, nc_radius=5.0e-9,
                                     porosity=0.5),
                         precursor=Precursor("TMA", M=72.09e-3, sticking=1e-4,
                                             pressure=100.0),
                         n_cells=20)
    c_ref = thin.gas_density(thin.precursor.pressure)
    k_ads = (thin.precursor.sticking * thin.precursor.thermal_speed(thin.T)
             / 4.0 * c_ref / thin.site_density())
    t_end = 1.0 / k_ads
    res = thin.simulate_half_cycle(t_end, n_out=40)
    analytic = 1.0 - np.exp(-k_ads * res.t)
    err = np.max(np.abs(res.theta.mean(axis=1) - analytic))
    ok("theta(t) matches 1-exp(-k t)", err < 1e-3, err)
    spread = float(np.ptp(res.theta_final))
    ok("profile is flat (no depth gradient)", spread < 1e-3, spread)

    print("\n=== C. transport limit: sharp-front scaling ===")
    # alpha >> 1 means infill advances as a front; dose time ~ alpha L^2/(2 D_e).
    t_num, res = m.saturation_dose_time(target=0.99)
    t_est = m.saturation_time_estimate()
    ok("saturation reached", t_num is not None, t_num)
    ok("numeric dose time within 20% of front estimate",
       t_num is not None and close(t_num, t_est, 0.20), (t_num, t_est))
    ok("front estimate scales as L^2",
       close(default_model(film=NCFilm(thickness=2.0e-6, nc_radius=5.0e-9,
                                       porosity=0.5)).saturation_time_estimate(),
             4.0 * t_est, 1e-9))
    # a dose cut well short must leave the bottom starved
    short = m.simulate_half_cycle(0.2 * t_est, n_out=40)
    ok("short dose starves the bottom", short.theta_final[-1] < 0.5,
       short.theta_final[-1])
    ok("short dose saturates the top", short.theta_final[0] > 0.99,
       short.theta_final[0])
    ok("coverage decreases with depth",
       np.all(np.diff(short.theta_final) <= 1e-9))
    ok("penetration depth inside film",
       0.0 < short.penetration_depth(0.5) < m.film.thickness,
       short.penetration_depth(0.5))

    print("\n=== D. conservation ===")
    # Seal the surface (mass_transfer=0) and start with a charged pore volume:
    # gas + adsorbed precursor must be conserved exactly.
    sealed = default_model(mass_transfer=0.0, n_cells=60)
    c0 = sealed.gas_density(sealed.precursor.pressure)
    r = sealed.simulate_half_cycle(1e-3, c_init=c0, theta_init=0.0, n_out=30)
    s_v = sealed.specific_area()
    gam = sealed.site_density()
    inv = (sealed.eps * r.C + s_v * gam * r.theta).sum(axis=1) * sealed.dz
    drift = float(np.max(np.abs(inv - inv[0])) / inv[0])
    ok("sealed inventory conserved", drift < 1e-3, drift)
    ok("sealed system adsorbs something", r.theta_final.max() > 0.0,
       r.theta_final.max())
    ok("coverage never exceeds 1", r.theta.max() <= 1.0 + 1e-9, r.theta.max())
    ok("concentration stays non-negative", r.C.min() > -1e-6 * c0, r.C.min())

    # growth: the porosity drop must equal the deposited shell volume
    g = default_model()
    s_v0 = g.specific_area().copy()
    eps0 = g.eps.copy()
    dt_film = g.grow(np.ones(g.n_cells))
    ok("growth deposits gpc at full coverage",
       close(float(dt_film[0]), g.gpc, 1e-12), (dt_film[0], g.gpc))
    ok("d(eps) = -S_v dt_film",
       np.allclose(eps0 - g.eps, s_v0 * dt_film, rtol=1e-12))
    ok("half coverage deposits half as much",
       close(float(default_model().grow(0.5 * np.ones(120))[0]),
             0.5 * g.gpc, 1e-12))

    print("\n=== E. numerics ===")
    times = {}
    for n in (60, 120, 240):
        mm = default_model(n_cells=n)
        times[n], _ = mm.saturation_dose_time(target=0.99)
    rel = abs(times[240] - times[120]) / times[240]
    ok("grid converged (120 vs 240 cells)", rel < 0.03, (times, rel))
    ok("grid refinement is monotone-ish",
       abs(times[240] - times[60]) / times[240] < 0.10, times)

    # The quasi-steady gas field is an approximation only in that it drops
    # eps dC/dt; at alpha ~ 1e5 it must reproduce the transient solution.
    qs = default_model()
    t_qs, res_qs = qs.saturation_dose_time(target=0.99, quasi_steady=True)
    ok("quasi-steady matches transient dose time",
       close(t_qs, t_num, 0.02), (t_qs, t_num))
    tr = m.simulate_half_cycle(0.5 * t_est, n_out=20)
    qq = qs.simulate_half_cycle(0.5 * t_est, n_out=20, quasi_steady=True)
    dth = float(np.max(np.abs(tr.theta_final - qq.theta_final)))
    ok("quasi-steady matches transient profile", dth < 0.02, dth)
    dc = float(np.max(np.abs(tr.C[-1] - qq.C[-1])) / np.max(tr.C[-1]))
    ok("quasi-steady matches transient gas field", dc < 0.02, dc)

    print("\n=== F. purge ===")
    t_pg, pg = m.purge_time(residual=1e-3)
    ok("purge completes", t_pg is not None, t_pg)
    peak = np.max(pg.C, axis=1)
    ok("purge decays monotonically", np.all(np.diff(peak) <= 1e-9 * peak[0]))
    ok("purge time near the diffusion time",
       t_pg is not None and 0.1 * m.diffusion_time() < t_pg
       < 100 * m.diffusion_time(), (t_pg, m.diffusion_time()))
    ok("purge leaves chemisorbed layer intact",
       close(float(pg.theta_final.min()), 1.0, 1e-9), pg.theta_final.min())

    print("\n=== G. user-defined initial conditions ===")
    z = m.z
    for label, ic in (("scalar", 0.3),
                      ("array", np.linspace(0.2, 0.8, m.n_cells)),
                      ("callable", lambda zz: 0.5 * np.exp(-zz / 3e-7))):
        r = m.simulate_half_cycle(1e-9, theta_init=ic, n_out=3)
        want = m._as_profile(ic)
        ok("theta IC honoured (%s)" % label,
           np.allclose(r.theta[0], want, atol=1e-9), label)
    r = m.simulate_half_cycle(1e-9, c_init=lambda zz: 1e21 * np.ones_like(zz),
                              n_out=3)
    ok("C IC honoured (callable)", close(float(r.C[0].mean()), 1e21, 1e-6),
       r.C[0].mean())
    try:
        m.simulate_half_cycle(1e-9, theta_init=np.zeros(7))
        ok("wrong-length IC rejected", False)
    except ValueError:
        ok("wrong-length IC rejected", True)

    print("\n=== H. multi-cycle infill ===")
    # Doses re-sized every cycle keep every accessible cell saturated, so the
    # shell grows by gpc everywhere and the film densifies uniformly.
    geom = dict(film=NCFilm(thickness=2.0e-7, nc_radius=5.0e-9, porosity=0.4),
                n_cells=40)
    mc = default_model(**geom)
    out = mc.run_cycles(60, t_dose=100.0, t_purge=1e-4, dose_target=0.99)
    ok("cycles ran", len(out.cycle) > 0, len(out.cycle))
    ok("porosity decreases monotonically",
       np.all(np.diff(out.porosity[:, 0]) <= 1e-12))
    ok("saturating dose fills uniformly",
       float(np.ptp(out.porosity[-1])) < 0.02, np.ptp(out.porosity[-1]))
    ok("porosity never negative", out.porosity.min() >= 0.0,
       out.porosity.min())
    ok("infill reaches closure",
       out.porosity[-1].max() <= mc.film.pore_closure_porosity + 1e-9,
       out.porosity[-1].max())
    ok("film thickness accumulates", out.film_thickness[-1][0] > mc.gpc,
       out.film_thickness[-1][0])
    ok("every dose stayed saturated", out.dose_saturation.min() >= 0.98,
       out.dose_saturation.min())
    # closing pores throttle transport, so the dose requirement escalates
    ok("dose time escalates as pores close",
       out.dose_time[-1] > 10.0 * out.dose_time[0],
       (out.dose_time[0], out.dose_time[-1]))

    # The failure mode: a dose sized for the *initial* geometry is starved once
    # the pores tighten, so the top seals and strands the interior porous.
    fx = default_model(**geom)
    fixed = fx.run_cycles(60, t_dose=5.0 * fx.saturation_time_estimate(),
                          t_purge=1e-4)
    ok("fixed dose seals the top", fixed.porosity[-1][0]
       <= fx.film.pore_closure_porosity + 1e-9, fixed.porosity[-1][0])
    ok("fixed dose strands the interior porous",
       fixed.porosity[-1][-1] > 0.1, fixed.porosity[-1][-1])
    ok("fixed dose infills top faster than bottom",
       fixed.porosity[-1][0] < fixed.porosity[-1][-1] - 0.05,
       (fixed.porosity[-1][0], fixed.porosity[-1][-1]))
    ok("fixed dose loses saturation over the run",
       fixed.dose_saturation[-1] < 0.9, fixed.dose_saturation[-1])

    # Severely starved doses are top-heavy from the very first cycle.
    st = default_model(**geom)
    starved = st.run_cycles(60, t_dose=0.02 * st.saturation_time_estimate(),
                            t_purge=1e-4)
    ok("starved dose leaves the interior porous",
       starved.porosity[-1][-1] > st.film.pore_closure_porosity,
       starved.porosity[-1][-1])
    ok("starved coverage below saturating coverage",
       starved.dose_saturation[0] < out.dose_saturation[0],
       (starved.dose_saturation[0], out.dose_saturation[0]))

    print("\n=== I. equivalence with Yanguas-Gil & Elam (JVST A 30, 01A159) ===")
    # Their Eqs. (9)-(10) and this model are the same system: theta_YG = 1-theta,
    # s_0 = 1/Gamma, and their 1/(2R) is S_v/4 for a tube.  Check the group
    # mapping algebraically, then the solutions numerically.
    import twin.yanguas_gil_reactor as yg                        # noqa: E402
    from twin.nc_infill_vs_yanguas import groups                 # noqa: E402

    e = default_model()
    gp = groups(e)
    ok("gamma is exactly 1/alpha", close(gp["gamma"], 1.0 / e.capacity_ratio(),
                                         1e-12), (gp["gamma"], e.capacity_ratio()))
    # Da built from S_v must equal their Eq. (12) written with 1/(2R)
    R_equiv = 2.0 / e.specific_area()[0]
    ok("Da matches Eq. (12) with S_v = 2/R",
       close(gp["Da"], yg.damkoehler(R_equiv, e.film.thickness,
                                     e.effective_diffusivity(e.precursor)[0],
                                     e.precursor.thermal_speed(e.T),
                                     e.precursor.sticking), 1e-12))
    ok("gamma matches Eq. (13) with s_0 = 1/Gamma",
       close(gp["gamma"], yg.excess_number(1.0 / e.site_density(),
                                           e.gas_density(e.precursor.pressure),
                                           R_equiv), 1e-12))

    t_phys = 0.35 * e.saturation_time_estimate()
    th_e = e.simulate_half_cycle(t_phys, n_out=3).theta_final
    xi_e = e.z / e.film.thickness
    for label, epsv in (("published eps=1", 1.0), ("matched eps", e.film.porosity)):
        r = yg.solve(Pe=0.0, Da=gp["Da"], gamma=gp["gamma"],
                     tau_end=t_phys * gp["tau_per_second"], xi_max=1.0,
                     n_xi=1200, epsilon=epsv, outlet="noflux")
        err = float(np.max(np.abs(th_e - np.interp(xi_e, r.xi,
                                                   r.growth_profile()))))
        ok("solutions agree (%s)" % label, err < 2e-3, err)

    # sanity on the reference implementation itself
    # tau is scaled by L^2/D, so filling a closed domain by diffusion alone
    # takes tau of order 1 -- run well past that before expecting x -> 1
    r0 = yg.solve(Pe=0.0, Da=1e-9, gamma=1e-9, tau_end=3.0, xi_max=1.0,
                  n_xi=400, outlet="noflux")
    ok("no reaction at Da->0 leaves theta untouched",
       float(np.max(r0.growth_profile())) < 1e-6, np.max(r0.growth_profile()))
    ok("no reaction at Da->0 fills the domain with precursor",
       float(np.min(r0.x[-1])) > 0.99, np.min(r0.x[-1]))

    def exit_coverage(res):
        """Coverage at the reactor exit, xi = 1 (each run has its own grid)."""
        return float(np.interp(1.0, res.xi, res.growth_profile()))

    rp = yg.solve(tau_end=0.02, **yg.PAPER_TMA)
    ok("paper reference case gives a downstream-decaying profile",
       rp.growth_profile()[0] > exit_coverage(rp),
       (rp.growth_profile()[0], exit_coverage(rp)))
    adv = yg.solve(Pe=50.0, Da=1550.0, gamma=2.5, tau_end=0.02, xi_max=2.0)
    dif = yg.solve(Pe=0.0, Da=1550.0, gamma=2.5, tau_end=0.02, xi_max=2.0)
    ok("advection pushes the front downstream",
       exit_coverage(adv) > exit_coverage(dif),
       (exit_coverage(adv), exit_coverage(dif)))
    # the paper's own discretisation criterion must be enforced, not assumed
    try:
        yg.solve(Pe=65.0, Da=1550.0, gamma=2.5, tau_end=1e-4, n_xi=100)
        ok("rejects a grid that violates Pe*dxi < 0.1", False)
    except ValueError:
        ok("rejects a grid that violates Pe*dxi < 0.1", True)

    print("\n=== J. 1-D reduction of the CFD paper (arXiv:2106.07132) ===")
    # Yanguas-Gil, Libera & Elam benchmark their reactor-scale CFD against an
    # analytic 1-D plug-flow solution, Eq. (24).  Check that expression solves
    # the quasi-steady plug-flow system, that it is the Pe -> inf limit of the
    # 1-D advection-diffusion model, and that it degenerates to 0-D Langmuir.
    Pe_, Da_, gm_ = 100.0, 300.0, 0.05
    xi_, tau_, h_ = 0.37, 0.004, 1e-6
    th = lambda s, t: yg.plug_flow_coverage(s, t, Pe_, Da_, gm_)
    A_ = np.exp(gm_ * Da_ * tau_) - 1.0
    xg = lambda s: (A_ + 1.0) / (np.exp(s * Da_ / Pe_) + A_)
    res_s = abs((th(xi_, tau_ + h_) - th(xi_, tau_ - h_)) / (2 * h_)
                - gm_ * Da_ * (1 - th(xi_, tau_)) * xg(xi_))
    res_g = abs(Pe_ * (xg(xi_ + h_) - xg(xi_ - h_)) / (2 * h_)
                + Da_ * (1 - th(xi_, tau_)) * xg(xi_))
    ok("Eq. (24) satisfies the surface equation", res_s < 1e-7, res_s)
    ok("Eq. (24) satisfies the plug-flow gas equation", res_g < 1e-7, res_g)
    ok("Eq. (24) at the inlet is 1 - exp(-t/t_bar)",
       close(float(th(0.0, tau_)), 1 - np.exp(-gm_ * Da_ * tau_), 1e-12))

    # the 1-D model must reproduce plug flow once axial diffusion is negligible
    # and the propagation delay (their Eq. 28) is small
    errs = []
    for gam in (0.02, 0.005):
        Pe2, Da2 = 400.0, 1200.0
        tau2 = 1.6 / (gam * Da2)
        r = yg.solve(Pe=Pe2, Da=Da2, gamma=gam, tau_end=tau2, xi_max=1.0,
                     outlet="noflux")
        errs.append(float(np.max(np.abs(
            r.growth_profile()
            - yg.plug_flow_coverage(r.xi, tau2, Pe2, Da2, gam)))))
    ok("1-D solver reproduces plug flow at high Pe", errs[0] < 0.02, errs)
    ok("residual shrinks with the propagation delay", errs[1] < 0.4 * errs[0],
       errs)

    # axial diffusion softens the profile -- the paper's stated CFD/plug-flow gap
    lo = yg.solve(Pe=25.0, Da=75.0, gamma=0.02, tau_end=1.6 / (0.02 * 75.0),
                  xi_max=1.0, outlet="noflux")
    soft = float(np.max(np.abs(lo.growth_profile()
                               - yg.plug_flow_coverage(lo.xi, 1.6 / (0.02 * 75.0),
                                                       25.0, 75.0, 0.02))))
    ok("axial diffusion softens the profile vs plug flow", soft > 2 * errs[0],
       (soft, errs[0]))

    # front kinematics: linear in time under advection, sqrt(t) under diffusion
    grid = np.linspace(0.0, 1.0, 4001)
    fronts = [float(np.interp(0.5, yg.plug_flow_coverage(
        grid, k * 1.6 / (0.02 * 300.0), 100.0, 300.0, 0.02)[::-1], grid[::-1]))
        for k in (1, 2)]
    ok("plug-flow front advances faster than sqrt(t)",
       fronts[1] / fronts[0] > 1.6, fronts)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % ", ".join(_fail))
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
