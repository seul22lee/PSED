"""
yanguas_gil_reactor.py
----------------------
Direct implementation of

    A. Yanguas-Gil and J. W. Elam, "Simple model for atomic layer deposition
    precursor reaction and transport in a viscous-flow tubular reactor",
    J. Vac. Sci. Technol. A 30, 01A159 (2012).  doi:10.1116/1.3670396

Unlike the nanocrystal-infill paper, this PDF (psed_v1/01a159_1_online.pdf) is
intact, so the equations below are transcribed from the article rather than
reconstructed.

THE EQUATIONS (paper numbering)

  Dimensional, after radial averaging of the tube (Eqs. 7-8):

      dn/dt + u dn/dz - D d2n/dz2  =  -(1/2R) v_th b_0 theta n            (7)
      dtheta/dt                    =  -(1/4) s_0 v_th b_0 n theta         (8)

  with  theta = fraction of AVAILABLE sites (1 -> 0, the opposite convention
  to nc_infill_model.py), s_0 = mean area per adsorption site [m^2], b_0 = bare
  surface reaction probability, R = tube radius, v_th = mean thermal speed.

  Normalised with x = n/n_0, xi = z/L, tau = t D / L^2 (Eqs. 9-10):

      dx/dtau + Pe dx/dxi - d2x/dxi2 = -Da theta x                        (9)
      dtheta/dtau                    = -gamma Da theta x                 (10)

  The three groups that fully determine the problem (Eqs. 11-13):

      Pe    = u L / D                       Peclet   (convection/diffusion)
      Da    = (1/2R)(L^2/D) v_th b_0        Damkoehler (reaction/transport)
      gamma = s_0 n_0 R / 2                 excess number (molecules per site)

  Published boundary/initial conditions: a square pulse x(0,tau) = 1 for
  tau <= tau_0 and 0 after, x(xi_inf, tau) = 0 with xi_inf = 10, x(xi,0) = 0,
  theta(xi,0) = 1.  Reference case for TMA/H2O in their reactor (R = 2.5 cm,
  L = 45 cm): Pe = 65, Da = 1550, gamma = 2.5.

RELATION TO nc_infill_model.py
    Note 1/(2R) = S_v/4 for a cylinder, since a tube has S_v = 2/R of wall per
    unit volume.  Writing the sink with S_v makes Eq. (7) geometry-agnostic,
    and the nanocrystal-infill model is then the same equation at Pe = 0 with
    S_v = 3(1-eps)/r, a porosity holdup eps on the accumulation term, and a
    Knudsen rather than molecular diffusivity.  The groups map exactly:

        gamma  =  n_0 / (S_v / s_0)  =  C_0 / (S_v Gamma)  =  1 / alpha

    i.e. the excess number is the reciprocal of the infill model's capacity
    ratio.  See nc_infill_vs_yanguas.py for the numerical demonstration.

    `epsilon` below is 1 in the published model (an open tube is all void); it
    is exposed so the same solver can represent a porous medium and so the
    equivalence can be checked with and without that term.
"""
import numpy as np
from scipy.constants import Boltzmann as kB
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

# which ontology model this code implements (ontology/core.yaml `models:`)
MODEL_ID = "yanguas_gil_elam_tubular_reactor"

# Table caption / Sec. IV A: TMA/H2O in the Argonne viscous-flow reactor
PAPER_TMA = dict(Pe=65.0, Da=1550.0, gamma=2.5)


class ReactorProfile:
    """Result of :func:`solve`.

    xi    : (n_xi,)          normalised axial position z/L
    tau   : (n_t,)           normalised time t D / L^2
    x     : (n_t, n_xi)      normalised precursor density n/n_0
    theta : (n_t, n_xi)      fraction of AVAILABLE sites (paper convention)
    """

    def __init__(self, xi, tau, x, theta):
        self.xi = xi
        self.tau = tau
        self.x = x
        self.theta = theta

    @property
    def coverage(self):
        """Fraction of sites CONSUMED, i.e. the nc_infill_model convention and
        the quantity proportional to deposited thickness."""
        return 1.0 - self.theta

    def growth_profile(self, index=-1):
        """Relative film thickness along the reactor: 1 - theta."""
        return 1.0 - self.theta[index]


def solve(Pe, Da, gamma, tau_end, tau_dose=None, xi_max=10.0, n_xi=None,
          epsilon=1.0, outlet="dirichlet", theta_init=1.0, x_init=0.0,
          n_out=120, rtol=1e-7, atol=1e-10):
    """Integrate Eqs. (9)-(10).

    Parameters
    ----------
    Pe, Da, gamma : float
        The three dimensionless groups, Eqs. (11)-(13).
    tau_end : float
        Normalised end time.
    tau_dose : float, optional
        Square-pulse length; the inlet drops to 0 afterwards.  None = dose for
        the whole run.
    xi_max : float
        Domain length in units of L.  The paper uses 10 to approximate the
        semi-infinite reactor.
    epsilon : float
        Coefficient on the accumulation term dx/dtau.  1.0 reproduces the
        published equation (an open tube); < 1 represents the void fraction of
        a porous medium.
    outlet : {"dirichlet", "noflux"}
        "dirichlet" is the paper's x(xi_max, tau) = 0 open outlet; "noflux"
        closes the far end, as for a blind feature or a film on a substrate.
    theta_init, x_init : scalar | array | callable
        Initial conditions; the paper uses theta = 1, x = 0.

    Returns
    -------
    ReactorProfile
    """
    # the paper's criterion for the central-difference scheme (Sec. III):
    # Pe*dxi < 0.1, which bounds the cell Peclet number and keeps the scheme
    # free of the oscillations central differencing shows on advection.
    if n_xi is None:
        n_xi = max(1000, int(np.ceil(Pe * xi_max / 0.09)))
    n = int(n_xi)
    xi = np.linspace(0.0, xi_max, n + 1)
    d = xi[1] - xi[0]
    if Pe * d > 0.1:
        raise ValueError("Pe*dxi = %.3g > 0.1; increase n_xi to at least %d"
                         % (Pe * d, int(np.ceil(Pe * xi_max / 0.1))))

    def prof(v, default):
        if v is None:
            return np.full(n + 1, float(default))
        if callable(v):
            return np.asarray(v(xi), dtype=float) * np.ones(n + 1)
        a = np.asarray(v, dtype=float)
        return np.full(n + 1, float(a)) if a.ndim == 0 else a.copy()

    if tau_dose is None:
        inlet = lambda t: 1.0
    else:
        inlet = lambda t: 1.0 if t <= tau_dose else 0.0

    # unknowns: x_1..x_{n-1} (interior), theta_0..theta_n
    nx = n - 1
    inv_d2 = 1.0 / d ** 2
    half_pe = Pe / (2.0 * d)

    def rhs(t, y):
        xi_x = y[:nx]
        th = y[nx:]
        x_full = np.empty(n + 1)
        x_full[0] = inlet(t)
        x_full[1:n] = xi_x
        x_full[n] = x_full[n - 1] if outlet == "noflux" else 0.0

        lap = (x_full[:-2] - 2.0 * x_full[1:-1] + x_full[2:]) * inv_d2
        adv = -half_pe * (x_full[2:] - x_full[:-2])
        dx = (lap + adv - Da * th[1:n] * x_full[1:n]) / epsilon
        dth = -gamma * Da * th * x_full
        return np.concatenate((dx, dth))

    jac = lil_matrix((nx + n + 1, nx + n + 1), dtype=int)
    r = np.arange(nx)
    jac[r, r] = 1
    jac[r[:-1], r[:-1] + 1] = 1
    jac[r[1:], r[1:] - 1] = 1
    jac[r, nx + 1 + r] = 1              # x_i  <- theta_i
    jac[nx + 1 + r, r] = 1              # theta_i <- x_i
    rt = np.arange(n + 1)
    jac[nx + rt, nx + rt] = 1
    if outlet == "noflux":
        jac[nx + n, nx - 1] = 1

    y0 = np.concatenate((prof(x_init, 0.0)[1:n], prof(theta_init, 1.0)))
    t_eval = np.linspace(0.0, tau_end, n_out)
    sol = solve_ivp(rhs, (0.0, tau_end), y0, method="BDF", t_eval=t_eval,
                    jac_sparsity=jac.tocsr(), rtol=rtol, atol=atol)
    if not sol.success:
        raise RuntimeError("integration failed: %s" % sol.message)

    x = np.empty((sol.t.size, n + 1))
    x[:, 0] = [inlet(t) for t in sol.t]
    x[:, 1:n] = sol.y[:nx].T
    x[:, n] = x[:, n - 1] if outlet == "noflux" else 0.0
    theta = np.clip(sol.y[nx:].T, 0.0, 1.0)
    return ReactorProfile(xi, sol.t, x, theta)


# --------------------------------------------------------------------------
# dimensional helpers (Eqs. 11-15)
# --------------------------------------------------------------------------
def peclet(u, L, D):
    """Eq. (11)."""
    return u * L / D


def damkoehler(R, L, D, v_th, beta0):
    """Eq. (12).  1/(2R) is S_v/4 for a tube."""
    return (1.0 / (2.0 * R)) * (L ** 2 / D) * v_th * beta0


def excess_number(s0, n0, R):
    """Eq. (13).  s0 is the area per site, i.e. 1/Gamma."""
    return s0 * n0 * R / 2.0


def plug_flow_coverage(xi, tau, Pe, Da, gamma):
    """Analytic plug-flow coverage, Eq. (24) of Yanguas-Gil, Libera & Elam,
    JVST A 39, 062404 (2021) / arXiv:2106.07132, in dimensionless form.

    The published form is

        Theta(z; t_d) = (exp(t_d/t_bar) - 1) / (exp(z/z_bar) + exp(t_d/t_bar) - 1)
        t_bar = 4 k_B T / (s_0 v_th b_0 p_0)                            (25)
        z_bar = (V/S) 4u / (v_th b_0)                                   (26)

    Substituting the groups of the 2012 paper (V/S = 1/S_v for any geometry):

        t/t_bar = gamma * Da * tau        z/z_bar = xi * Da / Pe

    so the plug-flow solution is the Pe -> infinity limit of Eqs. (9)-(10)
    at fixed Da/Pe, i.e. the same 1-D system with axial diffusion switched off.

    Two limits worth noting:
      * at xi = 0 this reduces to Theta = 1 - exp(-tau gamma Da), the
        well-mixed Langmuir result;
      * the half-coverage front sits at xi = (Pe/Da) ln(exp(gamma Da tau) - 1),
        i.e. it advances *linearly* in time, whereas the diffusion-limited
        (Pe = 0) front advances as sqrt(tau).

    Returns the CONSUMED fraction, matching ReactorProfile.growth_profile().
    """
    xi = np.asarray(xi, dtype=float)
    e_t = np.exp(gamma * Da * tau)
    return (e_t - 1.0) / (np.exp(xi * Da / Pe) + e_t - 1.0)


def plug_flow_scales(T, s0, v_th, beta0, p0, u, S_v):
    """The dimensional scales of Eqs. (25)-(26): (t_bar [s], z_bar [m])."""
    t_bar = 4.0 * kB * T / (s0 * v_th * beta0 * p0)
    z_bar = (1.0 / S_v) * 4.0 * u / (v_th * beta0)
    return t_bar, z_bar


def axial_velocity(flow_sccm, p_torr, T, R):
    """Eq. (14): u = (p0 T phi) / (p T0 pi R^2), phi in sccm."""
    p0, T0 = 101325.0, 273.15          # standard conditions for sccm
    phi = flow_sccm * 1e-6 / 60.0      # sccm -> m^3/s at STP
    p = p_torr * 133.322
    return p0 * T * phi / (p * T0 * np.pi * R ** 2)


if __name__ == "__main__":
    # the paper's TMA/H2O reference case
    res = solve(tau_end=0.02, **PAPER_TMA)
    g = res.growth_profile()
    inside = res.xi <= 1.0
    print("Yanguas-Gil & Elam 2012, TMA/H2O reference case")
    print("  Pe=%(Pe)g  Da=%(Da)g  gamma=%(gamma)g" % PAPER_TMA)
    print("  coverage at reactor inlet  %.3f" % g[0])
    print("  coverage at reactor outlet %.3f" % g[inside][-1])
    for tau0 in (0.0005, 0.002, 0.01):
        r = solve(tau_end=tau0, **PAPER_TMA)
        gg = r.growth_profile()[r.xi <= 1.0]
        print("  tau=%-7g inlet %.3f -> outlet %.3f" % (tau0, gg[0], gg[-1]))
