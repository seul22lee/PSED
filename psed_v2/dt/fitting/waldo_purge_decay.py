"""ADDED (A13): what the WALDO 7/02 QCM does during the purges (evidence for desorption).

Uses the dose times from waldo_cycles.py. Needs WALDO_PRESSURE, WALDO_QCM and WALDO_TEMP (see there).
Writes waldo_purge_decay.json and waldo_purge_decay.png next to this file. Both hold collaborator data and
are git-ignored.

1. Cycle shape: each cycle aligned on the QCM rise of its TMA dose (t = 0), referenced to the QCM value 5 s
   before. Mean of cycles 21-49.
2. Two-exponential fit of each purge: m(t) = m_inf + A_fast exp(-t/tau_fast) + A_slow exp(-t/tau_slow),
   from the peak after the dose to 1 s before the next dose.
3. Per block of 10 cycles: mass lost in each purge (peak - end of purge), and the fast amplitude with
   tau_slow fixed at the value fitted on the mean cycle.
4. Checks on what else could move the QCM:
   - the QCM against pressure in the post-run pump/hold/purge cycles (0.07-3.8 Torr);
   - the logged reactor temperature over a mean cycle;
   - the QCM resolution step.
5. Exhaust pressure after the TMA dose: exponential fits of the late tail (mean of cycles 4-48).
"""
import json
import os
import numpy as np
from scipy.optimize import curve_fit
import waldo_cycles as wc

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCKS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 49)]


def e2(t, mi, a1, t1, a2, t2):
    return mi + a1 * np.exp(-t / t1) + a2 * np.exp(-t / t2)


def fit2(t, y):
    p, _ = curve_fit(e2, t, y, p0=[y[-1], 3, 1, y[0] - y[-1] - 3, 40], maxfev=50000)
    return dict(m_inf=p[0], A_fast=p[1], tau_fast=p[2], A_slow=p[3], tau_slow=p[4],
                rms=float(np.sqrt(np.mean((e2(t, *p) - y) ** 2))))


def main():
    P, Q, T = wc.load("WALDO_PRESSURE"), wc.load("WALDO_QCM"), wc.load("WALDO_TEMP")
    doses, base = wc.find_doses(P)
    tma, h2o = doses[0::2, 0], doses[1::2, 0]
    rise = wc.qcm_rise(Q, tma)                       # QCM clock
    lag = float(np.median(rise - tma))
    t_h2o = float(np.median(h2o - tma))              # H2O dose after the TMA dose
    period = float(np.median(np.diff(tma)))
    tq, mq = Q[:, 0], Q[:, 1]
    g = np.round(np.arange(-10.0, period, 0.1), 1)
    segs = np.array([np.interp(r + g, tq, mq) - np.interp(r - 5.0, tq, mq) for r in rise])
    out = dict(lag_qcm_minus_onset_s=lag, h2o_after_tma_s=t_h2o, period_s=period)

    # 1-2: mean cycle and fits
    avg = segs[20:49].mean(0)
    win = {"TMA": (0.0, t_h2o - 1.0), "H2O": (t_h2o, period - 1.5)}
    fits = {}
    for nm, (a, b) in win.items():
        m = (g >= a) & (g <= b)
        k0 = np.flatnonzero(m)[np.argmax(avg[m][:40])]      # peak within 4 s of the window start
        m2 = (g >= g[k0]) & (g <= b)
        fits[nm] = fit2(g[m2] - g[k0], avg[m2])
        fits[nm].update(peak=float(avg[k0]), end=float(avg[m2][-1]), t_peak=float(g[k0]))
    out["mean_cycle_21_49"] = fits

    # 3: per block
    blocks = []
    for i, j in BLOCKS:
        y = segs[i:j].mean(0)
        row = dict(cycles=f"{i + 1}-{j}")
        for nm, (a, b) in win.items():
            m = (g >= a) & (g <= b)
            k0 = np.flatnonzero(m)[np.argmax(y[m][:40])]
            m2 = (g >= g[k0]) & (g <= b)
            tt, yy = g[m2] - g[k0], y[m2]
            ts = fits[nm]["tau_slow"]
            f = lambda t, mi, a1, t1, a2: mi + a1 * np.exp(-t / t1) + a2 * np.exp(-t / ts)
            try:
                p, _ = curve_fit(f, tt, yy, p0=[yy[-1], 3, 1, 8], bounds=([-50, -20, 0.05, -50], [300, 50, 10, 100]))
                fa, ft = float(p[1]), float(p[2])
            except RuntimeError:
                fa = ft = float("nan")
            row[nm] = dict(peak=float(y[k0]), end=float(yy[-1]), lost=float(y[k0] - yy[-1]), A_fast=fa, tau_fast=ft)
        row["dm_cycle"] = float(y[np.argmin(abs(g - (period - 1.5)))])
        blocks.append(row)
    out["blocks"] = blocks

    # 4: checks
    late = (P[:, 0] > 12000) & (P[:, 0] < P[:, 0].max() - 200)
    tp, pp = P[late, 0], P[late, 1]
    mm = np.interp(tp + lag, tq, mq)
    slope = np.polyfit(pp, mm - mm.mean(), 1)[0]
    cyc = []                                          # QCM range within each 60 s pump/hold/purge cycle
    for t0 in np.arange(tp[0], tp[-1] - 60, 60.0):
        w = (tp >= t0) & (tp < t0 + 60)
        cyc.append(np.ptp(mm[w]))
    step = np.diff(mq[(tq > 1000) & (tq < 6000)])
    step = float(np.median(np.abs(step[step != 0])))
    Tok = T[T[:, 1] > 0]
    Tavg = np.array([np.interp(t + g[::10], Tok[:, 0], Tok[:, 2]) for t in tma[20:49]]).mean(0)
    out["checks"] = dict(
        pump_hold_purge_pressure_range_torr=[float(pp.min()), float(pp.max())],
        qcm_vs_pressure_slope_ng_cm2_per_torr=float(slope),
        qcm_range_within_pump_hold_purge_cycle_ng_cm2=dict(median=float(np.median(cyc)), max=float(np.max(cyc))),
        qcm_step_ng_cm2=step,
        reactor_temperature_range_over_mean_cycle_C=float(np.ptp(Tavg)))

    # 5: exhaust tail after the TMA dose
    gp = np.round(np.arange(-10.0, 58.0, 0.2), 1)
    pav = np.array([np.interp(t + gp, P[:, 0], P[:, 1]) for t in tma[3:48]]).mean(0)
    y = (pav - pav[gp < -2].mean()) * 1e3
    tail = dict(mTorr={str(t): float(y[np.argmin(abs(gp - t))]) for t in (0, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50)})
    for lo in (5, 10, 15):
        m = (gp >= lo) & (gp <= 55)
        f1 = lambda t, a, tau, c: a * np.exp(-(t - lo) / tau) + c
        f0 = lambda t, a, tau: a * np.exp(-(t - lo) / tau)
        p1, _ = curve_fit(f1, gp[m], y[m], p0=[20, 15, 0], maxfev=20000)
        p0, _ = curve_fit(f0, gp[m], y[m], p0=[20, 15], maxfev=20000)
        tail[f"tau_{lo}_55s"] = dict(with_offset=float(p1[1]), offset_mTorr=float(p1[2]), no_offset=float(p0[1]))
    out["exhaust_tail_TMA"] = tail

    json.dump(out, open(os.path.join(HERE, "waldo_purge_decay.json"), "w"), indent=1)
    print(f"QCM rise - onset {lag:+.2f} s; H2O dose {t_h2o:.1f} s after TMA; period {period:.1f} s")
    for nm, f in fits.items():
        print(f"{nm} purge (cycles 21-49): peak {f['peak']:.1f} end {f['end']:.1f}; fast {f['A_fast']:.1f} ng/cm2 "
              f"tau {f['tau_fast']:.2f} s; slow {f['A_slow']:.1f} ng/cm2 tau {f['tau_slow']:.0f} s; m_inf {f['m_inf']:.1f}; rms {f['rms']:.2f}")
    print("block   dm/cycle | TMA lost  fast A (tau) | H2O lost  fast A (tau)")
    for r in blocks:
        print(f"{r['cycles']:6s} {r['dm_cycle']:7.1f} | {r['TMA']['lost']:5.1f}  {r['TMA']['A_fast']:5.1f} ({r['TMA']['tau_fast']:.2f}) "
              f"| {r['H2O']['lost']:5.1f}  {r['H2O']['A_fast']:5.1f} ({r['H2O']['tau_fast']:.2f})")
    print("checks:", json.dumps(out["checks"]))
    print("exhaust tail:", json.dumps({k: v for k, v in tail.items() if k != 'mTorr'}))
    print("exhaust tail mTorr:", json.dumps(tail["mTorr"]))
    plot(g, avg, fits, win, blocks, gp, y)


def plot(g, avg, fits, win, blocks, gp, y):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6), gridspec_kw=dict(width_ratios=[2.2, 1, 1]))
    a = ax[0]
    a.plot(g, avg, "k", lw=1.2, label="QCM, mean of cycles 21-49")
    for (nm, f), c in zip(fits.items(), ("C3", "C0")):
        m = (g >= f["t_peak"]) & (g <= win[nm][1])
        t = g[m] - f["t_peak"]
        a.plot(g[m], e2(t, f["m_inf"], f["A_fast"], f["tau_fast"], f["A_slow"], f["tau_slow"]), "--", color=c, lw=1.5,
               label=f"{nm} purge fit: fast {f['A_fast']:.0f} ng/cm² ({f['tau_fast']:.1f} s) + slow {f['A_slow']:.0f} ng/cm² ({f['tau_slow']:.0f} s)")
    a.set(xlabel="time from the QCM rise of the TMA dose (s)", ylabel="Δm (ng/cm²)")
    a.legend(fontsize=7, loc="lower right")
    x = np.arange(len(blocks))
    b = ax[1]
    b.bar(x - 0.2, [r["TMA"]["lost"] for r in blocks], 0.4, color="C3", label="lost in TMA purge")
    b.bar(x + 0.2, [r["H2O"]["lost"] for r in blocks], 0.4, color="C0", label="lost in H2O purge")
    b.plot(x, [r["dm_cycle"] / 5 for r in blocks], "ko-", ms=3, label="Δm per cycle / 5")
    b.set_xticks(x, [r["cycles"] for r in blocks], fontsize=8)
    b.set(xlabel="cycles", ylabel="ng/cm²")
    b.legend(fontsize=7)
    c = ax[2]
    c.semilogy(gp[gp > 0], np.clip(y[gp > 0], 1, None), "k.", ms=2)
    c.set(xlabel="time from the TMA onset (s)", ylabel="exhaust Δp (mTorr)", title="TMA exhaust tail, mean of 45 cycles")
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "waldo_purge_decay.png"), dpi=160)


if __name__ == "__main__":
    main()
