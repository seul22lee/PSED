"""ADDED (A12): cycle boundaries and per-cycle QCM mass gain of the WALDO 7/02 run, from the raw logs.

The run is 50 cycles of TMA 0.1 s, purge 60 s, H2O 1 s, purge 60 s at 100 C (1.41 Torr, 120 sccm).
It is followed by 200 pump/hold/purge cycles.

Data (collaborator files, not in the repository), each tab-separated with time in s as the first column:
  WALDO_PRESSURE  time, exhaust pressure [Torr]
  WALDO_QCM       time, QCM areal mass [ng/cm2]
  WALDO_TEMP      time, setpoint, reading [C]       (only waldo_purge_decay.py uses it)
Optional:
  WALDO_PERCYCLE_REF  one value per line: per-cycle mass gains from another analysis, to compare against.

Method:
- The doses are the pressure spikes. A dose starts at the first sample more than THRESH above the baseline.
  Doses alternate TMA, H2O; TMA comes first.
- The QCM rises about 1.0 s before the exhaust-gauge onset (gauge downstream of the sample, plus any clock offset;
  printed as 'QCM rise - onset').
- A cycle runs from one TMA onset to the next. Its mass gain is the QCM value BOUNDARY_LEAD s before the next
  onset minus the value BOUNDARY_LEAD s before its own onset. These points lie on the flat end of the purge,
  before the QCM rise. The last cycle ends at the last H2O onset + 61 s.
"""
import os
import numpy as np

BOUNDARY_LEAD = 2.8  # s: a cycle boundary is the QCM value this long before the pressure onset
THRESH = 0.005       # Torr above the baseline: onset
PEAK = 0.04          # Torr above the baseline: a dose spike
MAX_HEIGHT = 1.0     # Torr: higher spikes are the pump/hold/purge refills, not doses
MIN_GAP = 30.0       # s
ALD_END = 6200.0     # s, pressure clock: the pump/hold/purge block starts after this


def load(name):
    path = os.environ.get(name)
    if not path:
        raise SystemExit(f"set {name} to the WALDO data file (not in the repository)")
    return np.loadtxt(path)


def find_doses(P):
    """Onset, peak time and peak height (above the local baseline) of each dose spike during the ALD block.
    A spike is a peak between PEAK and MAX_HEIGHT above the baseline (the pump/hold/purge refills are ~3 Torr).
    Its onset is the first sample above the local baseline (median of the 10 s before the spike), searched
    back from the peak. Spikes closer than MIN_GAP s are one spike. The gauge reads in 10 mTorr steps."""
    t, p = P[:, 0], P[:, 1]
    m = t < ALD_END
    t, p = t[m], p[m]
    base = np.median(p[(t > 5) & (t < 25)])          # before the first dose
    peaks = np.flatnonzero((p > base + PEAK) & (p < base + MAX_HEIGHT))
    out, last = [], -1e9
    for k in peaks:
        if t[k] - last < MIN_GAP:
            continue
        w = (t >= t[k]) & (t <= t[k] + 3.0)          # peak within 3 s of the first sample above PEAK
        kk = np.flatnonzero(w)[np.argmax(p[w])]
        loc = np.median(p[(t >= t[k] - 12.0) & (t < t[k] - 2.0)])
        if abs(loc - base) > 0.05:                   # not at the process baseline: pump/hold/purge block
            continue
        i = k
        while i > 0 and p[i - 1] > loc + THRESH:
            i -= 1
        out.append((t[i], t[kk], p[kk] - loc))
        last = t[k]
    return np.array(out), base


def per_cycle(Q, doses):
    tq, mq = Q[:, 0], Q[:, 1]
    tma, h2o = doses[0::2, 0], doses[1::2, 0]
    ends = np.r_[tma[1:], h2o[-1] + 61.0]
    before = lambda t: np.interp(t - BOUNDARY_LEAD - 0.1, tq, mq)
    return np.array([before(e) - before(s) for s, e in zip(tma, ends)]), tma, h2o


def qcm_rise(Q, onsets, jump=10.0):
    """Time of the first QCM sample more than `jump` ng/cm2 above the value 10 s before each onset."""
    tq, mq = Q[:, 0], Q[:, 1]
    out = []
    for t0 in onsets:
        m0 = np.interp(t0 - 10.0, tq, mq)
        k = np.flatnonzero((tq > t0 - 10.0) & (mq > m0 + jump))
        out.append(tq[k[0]])
    return np.array(out)


def main():
    P, Q = load("WALDO_PRESSURE"), load("WALDO_QCM")
    doses, base = find_doses(P)
    dm, tma, h2o = per_cycle(Q, doses)
    print(f"baseline {base:.3f} Torr; {len(tma)} TMA and {len(h2o)} H2O doses; first TMA onset {tma[0]:.1f} s; "
          f"period {np.median(np.diff(tma)):.1f} s (range {np.diff(tma).min():.1f}-{np.diff(tma).max():.1f})")
    lag = qcm_rise(Q, tma) - tma
    print(f"QCM rise - onset (TMA): median {np.median(lag):+.2f} s (IQR {np.percentile(lag, 25):+.2f} to {np.percentile(lag, 75):+.2f})")
    print(f"spike height: TMA {np.median(doses[0::2, 2]) * 1e3:.0f} mTorr, H2O {np.median(doses[1::2, 2]) * 1e3:.0f} mTorr")
    print("per-cycle mass gain [ng/cm2]:", " ".join(f"{v:.1f}" for v in dm))
    print(f"mean {dm.mean():.1f}; cycles 1-10 {dm[:10].mean():.1f}, 21-50 {dm[20:].mean():.1f}")
    ref = os.environ.get("WALDO_PERCYCLE_REF")
    if ref:
        r = np.loadtxt(ref)
        n = min(len(r), len(dm))
        d = dm[:n] - r[:n]
        print(f"vs reference ({n} cycles): mean {r[:n].mean():.1f} here {dm[:n].mean():.1f}; "
              f"mean |diff| cycles 1-{n - 1}: {np.abs(d[:-1]).mean():.2f}; max |diff| {np.abs(d[:-1]).max():.1f}; "
              f"last cycle diff {d[-1]:+.1f}")


if __name__ == "__main__":
    main()
