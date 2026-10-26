"""ADDED (A1, not part of Larry's model): the analytic approximation of Ylilammi, Ylivaara, Puurunen,
J. Appl. Phys. 123, 205301 (2018), Eqs. 17-37. The paper fitted its Table I (c, K, p_A0) with this approximation,
so those parameters reproduce the paper profiles here, not necessarily in ChannelModel.
SI units. q (molecules per m2 per cycle) comes from Larry's adsorption_area(): q = N_A / adsorption_area(...)."""
import numpy as np
from scipy.constants import k as kB, N_A, R, pi
from reaction_model import adsorption_area

def q_from_film(gpc_sat, rho, M_film_gmol, b_film):
    """Eq. 9 via Larry's adsorption_area (m2 per mol of reactant): q = N_A / area."""
    return N_A / adsorption_area(b_film=b_film, rho=rho, gpc=gpc_sat, M=M_film_gmol * 1e-3)

def d_eff(H, W, T, pA0, MA, dA, MB, dB, pB):
    """Eqs. 1-6 (same physics as ChannelModel.calc_za / calc_Deff after C1-C2). M in g/mol, d in m."""
    MA, MB = MA * 1e-3, MB * 1e-3
    vA = np.sqrt(8 * R * T / (pi * MA))
    zA = N_A / (R * T) * (pi / 4 * (dA + dB) ** 2 * np.sqrt(8 * R * T / pi * (1 / MA + 1 / MB)) * pB
                          + pi * dA ** 2 * np.sqrt(16 * R * T / (pi * MA)) * pA0)
    D_A = 3 * pi * vA ** 2 / (16 * zA)
    h = 2 / (1 / H + 1 / W)
    D_Kn = h * np.sqrt(8 * R * T / (9 * pi * MA))
    return 1 / (1 / D_A + 1 / D_Kn)

def coverage(H, W, T, pA0, t_pulse, c, K, q, MA, dA, MB=28.0, dB=374e-12, pB=300.0, x=None, nt=400):
    """theta(x) after one pulse: linear pressure to x_s = sqrt(D t) (Eqs. 18-19, D Eq. 23), exponential tail
    beyond x_t = x_s - sqrt(h N0 D_eff / (4 R T c Q)) (Eqs. 24, 28), Langmuir along p(x, t) (Eqs. 31-32)."""
    x = np.linspace(0, 1e-3, 2001) if x is None else x
    De = d_eff(H, W, T, pA0, MA, dA, MB, dB, pB)
    Kp = K * pA0
    D = pA0 * H * De / (q * kB * T * (1 - np.log1p(Kp) / Kp))
    Q = 1 / np.sqrt(2 * pi * MA * 1e-3 / N_A * kB * T)
    ka = c * Q / q; Pd = ka / K
    h = 2 / (1 / H + 1 / W)
    ell = np.sqrt(h * De / (4 * kB * T * ka * q))
    th = np.zeros_like(x); dt = t_pulse / nt
    for i in range(nt):
        xs = np.sqrt(D * (i + 0.5) * dt); xt = max(xs - ell, 0.0); pt = pA0 * (1 - xt / xs)
        p = np.where(x < xt, pA0 * (1 - x / xs), pt * np.exp(-(x - xt) / max(xs - xt, 1e-30)))
        k = ka * p + Pd; th_inf = np.where(k > 0, ka * p / k, 0.0)
        th = th_inf + (th - th_inf) * np.exp(-k * dt)
    return x, th

def thickness(N, gpc_sat, H0, blocks=100, x=None, **kw):
    """Eqs. 35-37: thickness [nm] after N cycles; one channel height H(0) - 2 n gpc for the whole channel."""
    x = np.linspace(0, 1e-3, 2001) if x is None else x
    blocks = min(N, blocks); dn = N / blocks; s = np.zeros_like(x)
    for b in range(blocks):
        _, th = coverage(H=max(H0 - 2 * b * dn * gpc_sat, 2e-9), x=x, **kw); s += dn * gpc_sat * th
    return x, s * 1e9
