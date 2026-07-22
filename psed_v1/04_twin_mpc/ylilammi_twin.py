#!/usr/bin/env python3
"""
ylilammi_twin.py — a virtual ALD-in-a-channel model built directly from
  M. Ylilammi, O. M. E. Ylivaara, R. L. Puurunen,
  "Modeling growth kinetics of thin films made by atomic layer deposition in
   lateral high-aspect-ratio structures", J. Appl. Phys. 123, 205301 (2018),
  doi:10.1063/1.5028178.

INPUTS  : precursor pulse time tp (s) and precursor partial pressure pA0 (Pa).
OUTPUT  : film thickness profile s(x) along a lateral high-aspect-ratio (LHAR)
          channel (the "half-thickness penetration" xp falls straight out of it).

Equation numbers below refer to the paper.

Physics chain
  gas transport   bulk hard-sphere diffusion DA (Eq 1-3) + Knudsen DKn (Eq 4-5),
                  combined by the Bosanquet relation Deff (Eq 6). Knudsen dominates.
  pressure front  apparent longitudinal diffusion D (Eq 23) sets the front
                  position xs = sqrt(D t) (Eq 19); the reactant pressure is linear
                  near the mouth and an exponential tail beyond xt (Eq 24 & 28).
  surface kinetics dynamic Langmuir adsorption (Eq 31), integrated across the pulse
                  to give the per-cycle coverage theta_i(x). (Solved here with an
                  exact linear/exponential step — the paper uses RK4; both are stable.)
  film build-up   thickness accumulates s(x) = sum_i theta_i(x) * gpc_sat (Eq 36-37);
                  the channel narrows each cycle H(N) = H0 - 2 N gpc (Eq 35).

Every numeric constant is taken from the paper (Table I, the Experimental section,
and the Fig 2-7 captions). The only quantity not in Table I is the saturation
adsorption density q; the paper's own figure captions state q = 5e18 /m^2, which is
used here. The desorption probability Pd is not tabulated but is DERIVED from the
tabulated c, K, q through the paper's Eq 13 (K = cQ / (q Pd)) — not guessed.
"""
import numpy as np

# --- universal constants -------------------------------------------------
R  = 8.314462          # gas constant           J/(K mol)
N0 = 6.02214076e23     # Avogadro               1/mol
kB = 1.380649e-23      # Boltzmann              J/K


# --- gas transport (Eq 1-6) ---------------------------------------------
def _mean_speed(M, T):                                   # Eq 2
    return np.sqrt(8.0 * R * T / (np.pi * M))


def _D_bulk(rec, pA0):                                   # Eq 1-3 : hard-sphere gas diffusion of A in A+B
    MA, dA, MB, dB, T, pB = rec['MA'], rec['dA'], rec['MB'], rec['dB'], rec['T'], rec['pB']
    vA = _mean_speed(MA, T)
    nA = pA0 * N0 / (R * T)                              # number densities (1/m^3)
    nB = pB * N0 / (R * T)
    zAB = (np.pi / 4.0) * (dA + dB) ** 2 * np.sqrt(8.0 * R * T / np.pi * (1.0 / MA + 1.0 / MB)) * nB
    zAA = np.pi * dA ** 2 * np.sqrt(16.0 * R * T / (np.pi * MA)) * nA
    zA = zAB + zAA                                       # Eq 1 (A-B + A-A collisions)
    return (3.0 * np.pi / 16.0) * vA ** 2 / zA           # Eq 3


def _D_knudsen(rec, H):                                  # Eq 4-5
    h = 2.0 / (1.0 / H + 1.0 / rec['W'])                 # hydraulic diameter (Eq 5)
    DKn = h * np.sqrt(8.0 * R * rec['T'] / (9.0 * np.pi * rec['MA']))
    return DKn, h


def _D_eff(rec, H, pA0):                                 # Eq 6 : Bosanquet
    DA = _D_bulk(rec, pA0)
    DKn, h = _D_knudsen(rec, H)
    return 1.0 / (1.0 / DA + 1.0 / DKn), h


# --- adsorption kinetics helpers ----------------------------------------
def _Q(rec):                                             # Eq 14 : collision rate at unit pressure
    return N0 / np.sqrt(2.0 * np.pi * rec['MA'] * R * rec['T'])


def _D_app(rec, H, pA0, Deff):                           # Eq 23 : apparent longitudinal diffusion
    Kp = rec['K'] * pA0
    corr = 1.0 - np.log(Kp + 1.0) / Kp                   # bracket term in Eq 23
    corr = max(corr, 1e-6)
    return pA0 * H * Deff / (rec['q'] * kB * rec['T'] * corr)


def _pressure(x, xs, Deff, h, rec, pA0):                 # Eq 24 + 28 : reactant pressure along channel
    Q = _Q(rec)
    Ltail = np.sqrt(h * N0 * Deff / (4.0 * R * rec['T'] * rec['c'] * Q))   # tail length from Eq 28
    xt = max(0.0, xs - Ltail)
    pt = pA0 * (1.0 - xt / xs)
    linear = pA0 * (1.0 - x / xs)                        # x <= xt   (Eq 24 upper branch)
    tail   = pt * np.exp(-(x - xt) / (xs - xt + 1e-30))  # x  > xt   (Eq 24 lower branch)
    return np.where(x <= xt, linear, tail)


# --- per-cycle surface coverage (Eq 31) ---------------------------------
def _cycle_coverage(x, rec, H, pA0, tp, nt=100):
    """Fractional coverage theta(x) reached in ONE pulse of length tp.

    Integrates the dynamic Langmuir ODE (Eq 31)
        dtheta/dt = (cQ/q) pA (1 - theta) - Pd theta
    with pA = pA(x, t) from the advancing front xs = sqrt(D t). Uses the exact
    solution of the linear ODE over each (constant-pA) sub-step for stability.
    """
    Deff, h = _D_eff(rec, H, pA0)
    D = _D_app(rec, H, pA0, Deff)
    Q = _Q(rec)
    a  = rec['c'] * Q / rec['q']                         # cQ/q prefactor
    Pd = rec['c'] * Q / (rec['q'] * rec['K'])            # Eq 13 : Pd from c, K, q
    dt = tp / nt
    th = np.zeros_like(x)
    t = 0.0
    for _ in range(nt):
        tm = t + 0.5 * dt                                # midpoint pA for the step
        xs = np.sqrt(max(D * tm, 1e-30))
        pA = np.clip(_pressure(x, xs, Deff, h, rec, pA0), 0.0, None)
        beta = a * pA + Pd
        ss = np.where(beta > 0, a * pA / beta, 0.0)      # instantaneous steady-state coverage
        th = ss + (th - ss) * np.exp(-beta * dt)         # exact linear step
        t += dt
    return np.clip(th, 0.0, 1.0), D


# --- public API ----------------------------------------------------------
def thickness_profile(tp, pA0, rec, x=None):
    """Thickness profile s(x) for pulse time tp (s) and precursor pressure pA0 (Pa).

    Returns (x_m, s_m) in metres. rec is a recipe dict (see AL2O3 / TIO2 below).
    """
    if x is None:
        x = np.linspace(0.0, rec['scan_length'], 201)
    N, gpc = rec['cycles'], rec['gpc_sat']
    step = max(1, N // 150)                              # chunk cycles: H changes negligibly within a chunk
    s = np.zeros_like(x)
    H = rec['H0']
    done = 0
    while done < N:
        k = min(step, N - done)
        th, _ = _cycle_coverage(x, rec, H, pA0, tp)
        s += th * gpc * k                               # Eq 36-37 (per-cycle coverage summed)
        done += k
        H = max(rec['H0'] - 2.0 * done * gpc, 0.05 * rec['H0'])   # Eq 35 : channel narrows
    return x, s


def penetration_depth(x, s):
    """Half-thickness penetration xp (Eq 34): where s falls to s(0)/2."""
    if s[0] <= 0:
        return 0.0
    half = s[0] / 2.0
    below = np.where(s <= half)[0]
    if len(below) == 0:
        return x[-1]
    i = below[0]
    if i == 0:
        return 0.0
    x0, x1, y0, y1 = x[i - 1], x[i], s[i - 1], s[i]
    return x0 + (half - y0) * (x1 - x0) / (y1 - y0)


# --- recipes straight from the paper ------------------------------------
# Al2O3 : Table I + Experimental (300 C, TMA/H2O, 500 cyc, 0.1 s pulses, 300 Pa).
AL2O3 = dict(name='Al2O3',
             MA=0.0749, dA=591e-12,          # TMA molar mass / diameter (Sec II, Fig captions)
             MB=0.028,  dB=374e-12, pB=300.0,# N2 carrier; chamber ~300 Pa (Experimental)
             T=573.15, H0=500e-9, W=0.1e-3,  # 300 C; 0.5 um gap; 0.1 mm width (Fig captions)
             cycles=500, c=0.00572, K=219.0, # Table I
             q=5e18, gpc_sat=105.6e-12,      # q from Fig 2-5 captions; gpc_sat from Table I
             pA0_fit=147.0, tp=0.1,          # Table I input pressure; 0.1 s pulse (Experimental)
             scan_length=200e-6)             # 200 um line scan (Experimental)

# TiO2 : Table I + Experimental (110 C, TiCl4/H2O, 1000 cyc, 0.1 s pulses).
TIO2 = dict(name='TiO2',
            MA=0.18968, dA=703.9e-12,        # TiCl4 molar mass / diameter (Sec II)
            MB=0.028, dB=374e-12, pB=300.0,
            T=383.15, H0=500e-9, W=0.1e-3,   # 110 C
            cycles=1000, c=0.10, K=0.252,    # Table I
            q=5e18, gpc_sat=54.4e-12,
            pA0_fit=25.7, tp=0.1,            # Table I
            scan_length=120e-6)


if __name__ == "__main__":
    # tiny self-check: reproduce the paper's Al2O3 case and print key numbers
    x, s = thickness_profile(AL2O3['tp'], AL2O3['pA0_fit'], AL2O3)
    print(f"Al2O3  plateau s(0) = {s[0]*1e9:5.1f} nm   "
          f"xp = {penetration_depth(x, s)*1e6:5.1f} um   "
          f"(paper: ~53 nm, drop near ~130-160 um)")
    x, s = thickness_profile(TIO2['tp'], TIO2['pA0_fit'], TIO2)
    print(f"TiO2   mouth   s(0) = {s[0]*1e9:5.1f} nm   "
          f"xp = {penetration_depth(x, s)*1e6:5.1f} um   "
          f"(paper: ~47 nm, gradual decline to ~100 um)")
