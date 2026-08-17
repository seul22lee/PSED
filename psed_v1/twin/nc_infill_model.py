"""
nc_infill_model.py
------------------
Transient diffusion--reaction model for ALD infiltration of a randomly packed
nanocrystal (NC) network, i.e. the process modelled in

    A. Cendejas, D. Moher, E. Thimsen, "Modeling atomic layer deposition
    process parameters to achieve dense nanocrystal-based nanocomposites",
    J. Vac. Sci. Technol. A 39, 012406 (2021).  doi:10.1116/6.0000588

which sets criteria for the three process parameters needed to fully infill a
3D NC network: *cycle number*, *precursor pulse time*, and *purge time*.

PROVENANCE WARNING
    The local copy of the PDF (psed_v1/012406_1_online.pdf) is corrupted -- its
    binary streams were destroyed by a UTF-8 round-trip, so only the XMP
    metadata is readable and the article itself is paywalled.  The equations
    below are therefore the *standard* Knudsen-diffusion + Langmuir-chemisorption
    formulation for ALD in a porous medium, not a transcription of the paper's
    equations.  Symbols, closures and defaults are all exposed as parameters, so
    re-fitting to the published formulation is a matter of changing arguments,
    not rewriting the solver.

COMPANION FILES
    twin/nc_infill_demo.py     worked example + figure (nc_infill_profiles.png)
    twin/nc_infill_report.py   generates the technical report nc_infill_report.html
    tests/test_nc_infill_model.py   49 checks: analytic limits, conservation,
                                    grid convergence, quasi-steady vs transient

MODEL
    One spatial dimension z, from the exposed film surface (z = 0) to the
    impermeable substrate (z = L).  Two coupled fields:

        C(z, t)      precursor number density in the pore gas   [m^-3]
        theta(z, t)  fraction of surface sites consumed         [-]

    Gas-phase balance, per unit *total* film volume:

        eps dC/dt = d/dz ( D_e dC/dz ) - S_v * Gamma * dtheta/dt        (1)

    Surface balance (Langmuir, irreversible by default):

        dtheta/dt = s(theta) * (v_th / 4) * C / Gamma  -  k_des theta   (2)
        s(theta)  = s_0 (1 - theta)^n

    with
        eps      porosity (void fraction)                       [-]
        S_v      internal surface area per unit film volume     [m^2/m^3]
        Gamma    saturation areal density of chemisorbed        [m^-2]
                 precursor  =  (b_film/b_a)(rho * GPC / M) N_A
        v_th     mean thermal speed  sqrt(8 R T / (pi M_A))     [m/s]
        D_e      effective (Knudsen) diffusivity                [m^2/s]

    Boundary conditions
        z = 0   Robin/Dirichlet against the reactor gas: the flux into the top
                cell is (C_gas - C_0) / (1/k_m + dz/(2 D_e)).  k_m = inf (the
                default) reduces this to a Dirichlet condition C(0,t) = C_gas.
                C_gas(t) is the dose/purge waveform.
        z = L   zero flux (impermeable substrate).

    Initial conditions are user-supplied: scalar, array over the grid, or a
    callable f(z) -- for both C and theta.

GEOMETRY / PORE EVOLUTION
    Randomly packed spheres of radius r, solid fraction phi = 1 - eps:

        S_v   = 3 phi / r
        r_p   = 2 eps / S_v            (hydraulic pore radius)
        D_K   = (2/3) r_p v_th         (Knudsen diffusion)
        D_e   = (eps / tau) D_K,  tau = eps^-0.5 (Bruggeman) by default

    Each completed ALD cycle grows a shell of thickness GPC * theta_lim on the
    internal surface, where theta_lim = min(theta_A, theta_B) is the coverage
    reached by the limiting half-reaction.  Porosity is updated by the exact
    volume balance d(eps) = -S_v * d(t_film), which is self-consistent with
    S_v = 3 phi / r in the non-overlapping limit.  Once eps falls to
    `pore_closure_porosity` the pore network is treated as closed: D_e and S_v
    are set to zero there, so a prematurely sealed surface layer starves the
    interior -- the failure mode that makes saturating doses necessary.

UNITS
    SI throughout (m, s, K, Pa, kg/mol), matching channel_model.py.
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import solve_banded
from scipy.sparse import lil_matrix

# which ontology model this code implements (ontology/core.yaml `models:`)
MODEL_ID = "nc_network_infill_diffusion_reaction"

# ---- physical constants (CODATA) ----
kB = 1.380649e-23        # Boltzmann constant   [J/K]
NA = 6.02214076e23       # Avogadro constant    [1/mol]
R = 8.314462618          # gas constant         [J/(mol K)]


# --------------------------------------------------------------------------
# configuration objects
# --------------------------------------------------------------------------
class Precursor:
    """One half-reaction: the gas species and the surface reaction it drives.

    Parameters
    ----------
    name : str
    M : float
        Molar mass [kg/mol].
    sticking : float
        Bare-surface reaction probability s_0 [-].
    pressure : float
        Partial pressure during the dose [Pa].
    gamma : float, optional
        Saturation areal density of chemisorbed precursor [m^-2].  If None it
        is derived from the film properties via `NCInfillModel.site_density()`.
    sticking_exponent : float
        Exponent n in s(theta) = s_0 (1-theta)^n.  n = 1 is Langmuir; n > 1
        reproduces the "soft saturation" seen for sterically hindered ligands.
    k_des : float
        First-order desorption rate constant [1/s].  0 = irreversible
        chemisorption (the usual ALD assumption).
    """

    def __init__(self, name, M, sticking=0.01, pressure=100.0, gamma=None,
                 sticking_exponent=1.0, k_des=0.0):
        self.name = name
        self.M = M
        self.sticking = sticking
        self.pressure = pressure
        self.gamma = gamma
        self.sticking_exponent = sticking_exponent
        self.k_des = k_des

    def thermal_speed(self, T):
        """Mean thermal speed [m/s]."""
        return np.sqrt(8 * R * T / (np.pi * self.M))


class NCFilm:
    """The porous nanocrystal network being infilled.

    Parameters
    ----------
    thickness : float
        Film thickness L [m].
    nc_radius : float
        Nanocrystal radius [m].
    porosity : float
        Initial void fraction [-].  Random close packing of monodisperse
        spheres gives ~0.36; plasma-synthesised NC films are typically looser.
    tortuosity : float, optional
        Pore tortuosity tau [-].  None => Bruggeman, tau = eps^-0.5.
    pore_closure_porosity : float
        Porosity below which the pore network is treated as closed [-].
    """

    def __init__(self, thickness=1.0e-6, nc_radius=5.0e-9, porosity=0.5,
                 tortuosity=None, pore_closure_porosity=0.02):
        self.thickness = thickness
        self.nc_radius = nc_radius
        self.porosity = porosity
        self.tortuosity = tortuosity
        self.pore_closure_porosity = pore_closure_porosity


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------
class HalfCycleResult:
    """Profiles returned by :meth:`NCInfillModel.simulate_half_cycle`.

    Attributes
    ----------
    t : (n_t,) array          times [s]
    z : (n_z,) array          cell-centre depths [m]
    C : (n_t, n_z) array      pore-gas number density [m^-3]
    theta : (n_t, n_z) array  fractional coverage [-]
    pressure : (n_t, n_z)     pore-gas partial pressure [Pa]
    """

    def __init__(self, t, z, C, theta, T, precursor, saturated_at=None):
        self.t = t
        self.z = z
        self.C = C
        self.theta = theta
        self.T = T
        self.precursor = precursor
        self.saturated_at = saturated_at   # [s] or None

    @property
    def pressure(self):
        return self.C * kB * self.T

    @property
    def theta_final(self):
        return self.theta[-1]

    @property
    def theta_bottom(self):
        """Coverage at the deepest cell vs time."""
        return self.theta[:, -1]

    def penetration_depth(self, fraction=0.5, index=-1):
        """Depth at which coverage has dropped to `fraction` of its surface
        value, linearly interpolated [m].  Returns L if the whole film is above
        the threshold."""
        th = self.theta[index]
        target = fraction * th[0]
        below = np.nonzero(th < target)[0]
        if below.size == 0:
            return float(self.z[-1])
        i = below[0]
        if i == 0:
            return float(self.z[0])
        z0, z1 = self.z[i - 1], self.z[i]
        t0, t1 = th[i - 1], th[i]
        return float(z0 + (target - t0) * (z1 - z0) / (t1 - t0))

    def residual_fraction(self, index=-1):
        """Peak pore-gas concentration remaining, normalised by the dose
        concentration -- the quantity a purge has to drive to zero."""
        c_dose = self.precursor.pressure / (kB * self.T)
        return float(np.max(self.C[index]) / c_dose)


class CycleResult:
    """Per-cycle summary returned by :meth:`NCInfillModel.run_cycles`."""

    def __init__(self, z):
        self.z = z
        self.cycle = []            # cycle index (1-based)
        self.theta_limiting = []   # (n_z,) coverage that set the growth
        self.film_thickness = []   # (n_z,) deposited shell thickness [m]
        self.porosity = []         # (n_z,) porosity after the cycle
        self.dose_saturation = []  # min coverage over depth, per cycle
        self.purge_residual = []   # residual gas fraction after each purge
        self.dose_time = []        # dose time actually used, per cycle [s]

    def _append(self, cycle, theta_lim, t_film, eps, purge_residual, dose_time,
                accessible):
        self.cycle.append(cycle)
        self.theta_limiting.append(theta_lim.copy())
        self.film_thickness.append(t_film.copy())
        self.porosity.append(eps.copy())
        # saturation is only meaningful on surface the precursor can still
        # reach; sealed-off cells sit at theta = 0 forever
        self.dose_saturation.append(float(theta_lim[accessible].min())
                                    if accessible.any() else float("nan"))
        self.purge_residual.append(purge_residual)
        self.dose_time.append(dose_time)

    def finalize(self):
        self.cycle = np.asarray(self.cycle)
        self.theta_limiting = np.asarray(self.theta_limiting)
        self.film_thickness = np.asarray(self.film_thickness)
        self.porosity = np.asarray(self.porosity)
        self.dose_saturation = np.asarray(self.dose_saturation)
        self.purge_residual = np.asarray(self.purge_residual)
        self.dose_time = np.asarray(self.dose_time)
        return self

    @property
    def cycles_to_infill(self):
        """First cycle at which every depth has reached pore closure, or None."""
        return self._first_infilled

    def _set_infill(self, cycle):
        self._first_infilled = cycle

    _first_infilled = None


# --------------------------------------------------------------------------
# the model
# --------------------------------------------------------------------------
class NCInfillModel:
    """Diffusion--reaction model for ALD infill of a nanocrystal network.

    Parameters
    ----------
    film : NCFilm
    precursor : Precursor
        The metal precursor (half-reaction A).
    coreactant : Precursor, optional
        Half-reaction B.  If None, B is assumed to saturate instantly, so
        growth is set by theta_A alone.
    T : float
        Substrate/gas temperature [K].
    gpc : float
        Growth per cycle at full saturation [m].
    film_density, film_molar_mass : float
        Deposited-film density [kg/m^3] and molar mass [kg/mol], used with
        `metal_per_formula` / `metal_per_molecule` to derive Gamma.
    n_cells : int
        Number of finite-volume cells across the film thickness.
    mass_transfer : float, optional
        External mass-transfer coefficient k_m [m/s] at the film surface.
        None => Dirichlet (perfectly stirred gas above the film).
    """

    def __init__(self, film=None, precursor=None, coreactant=None, T=473.0,
                 gpc=1.1e-10, film_density=3990.0, film_molar_mass=0.101961,
                 metal_per_formula=2, metal_per_molecule=1, n_cells=120,
                 mass_transfer=None):
        self.film = film if film is not None else NCFilm()
        self.precursor = precursor if precursor is not None else Precursor(
            "TMA", M=72.09e-3, sticking=0.01, pressure=100.0)
        self.coreactant = coreactant
        self.T = T
        self.gpc = gpc
        self.film_density = film_density
        self.film_molar_mass = film_molar_mass
        self.metal_per_formula = metal_per_formula
        self.metal_per_molecule = metal_per_molecule
        self.n_cells = n_cells
        self.mass_transfer = mass_transfer
        self.reset_geometry()

    # ---- derived scalars -------------------------------------------------
    def site_density(self):
        """Saturation areal density of chemisorbed precursor Gamma [m^-2].

        Same GPC-based relation as channel_model.calc_adsorption_density():
        one cycle of saturated coverage must deposit exactly `gpc` of film.
        """
        return (self.metal_per_formula / self.metal_per_molecule
                * (self.film_density * self.gpc / self.film_molar_mass) * NA)

    def gamma_for(self, precursor):
        return precursor.gamma if precursor.gamma is not None else self.site_density()

    def gas_density(self, pressure):
        """Ideal-gas number density [m^-3] at the model temperature."""
        return pressure / (kB * self.T)

    # ---- geometry --------------------------------------------------------
    def reset_geometry(self):
        """(Re)initialise the depth-resolved pore geometry."""
        n = self.n_cells
        self.dz = self.film.thickness / n
        self.z = (np.arange(n) + 0.5) * self.dz
        self.eps = np.full(n, float(self.film.porosity))
        self.r_eff = np.full(n, float(self.film.nc_radius))
        self.t_film = np.zeros(n)
        return self

    def specific_area(self, eps=None, r_eff=None):
        """Internal surface area per unit film volume S_v [m^2/m^3]."""
        eps = self.eps if eps is None else eps
        r_eff = self.r_eff if r_eff is None else r_eff
        sv = 3.0 * (1.0 - eps) / r_eff
        return np.where(eps <= self.film.pore_closure_porosity, 0.0, sv)

    def pore_radius(self, eps=None, r_eff=None):
        """Hydraulic pore radius r_p = 2 eps / S_v [m]."""
        eps = self.eps if eps is None else eps
        sv = self.specific_area(eps, r_eff)
        return np.where(sv > 0.0, 2.0 * eps / np.where(sv > 0.0, sv, 1.0), 0.0)

    def effective_diffusivity(self, precursor, eps=None, r_eff=None):
        """Effective Knudsen diffusivity D_e [m^2/s]."""
        eps = self.eps if eps is None else eps
        v_th = precursor.thermal_speed(self.T)
        d_kn = (2.0 / 3.0) * self.pore_radius(eps, r_eff) * v_th
        if self.film.tortuosity is None:
            # Bruggeman: tau = eps^-0.5  =>  eps/tau = eps^1.5
            factor = np.power(np.clip(eps, 0.0, 1.0), 1.5)
        else:
            factor = eps / self.film.tortuosity
        d_e = factor * d_kn
        return np.where(eps <= self.film.pore_closure_porosity, 0.0, d_e)

    def diffusion_time(self, precursor=None):
        """Bare pore-diffusion time L^2 / D_e [s] (no adsorption)."""
        precursor = precursor or self.precursor
        d_e = self.effective_diffusivity(precursor)
        return self.film.thickness ** 2 / np.mean(d_e[d_e > 0])

    def capacity_ratio(self, precursor=None):
        """alpha = S_v Gamma / C_gas: adsorption capacity per unit film volume
        divided by the pore-gas inventory.  alpha >> 1 (typically 1e4-1e6) is
        why infill proceeds as a sharp saturation front rather than by simple
        diffusive filling."""
        precursor = precursor or self.precursor
        gamma = self.gamma_for(precursor)
        c_gas = self.gas_density(precursor.pressure)
        return np.mean(self.specific_area()) * gamma / c_gas

    def saturation_time_estimate(self, precursor=None):
        """Order-of-magnitude dose time to drive the front to z = L [s].

        Sharp-front (shrinking-core) balance: the front at depth zf advances at
        the rate the diffusive flux can feed it,
            S_v Gamma dzf/dt = D_e C_gas / zf   =>   t = alpha L^2 / (2 D_e).
        """
        precursor = precursor or self.precursor
        d_e = self.effective_diffusivity(precursor)
        d_e = np.mean(d_e[d_e > 0]) if np.any(d_e > 0) else np.nan
        return self.capacity_ratio(precursor) * self.film.thickness ** 2 / (2.0 * d_e)

    # ---- initial conditions ---------------------------------------------
    def _as_profile(self, value, default=0.0):
        """Coerce scalar / array / callable f(z) into a (n_cells,) array."""
        if value is None:
            return np.full(self.n_cells, float(default))
        if callable(value):
            return np.asarray(value(self.z), dtype=float) * np.ones(self.n_cells)
        arr = np.asarray(value, dtype=float)
        if arr.ndim == 0:
            return np.full(self.n_cells, float(arr))
        if arr.shape != (self.n_cells,):
            raise ValueError("initial profile has shape %s, expected (%d,)"
                             % (arr.shape, self.n_cells))
        return arr.copy()

    # ---- core solver -----------------------------------------------------
    def simulate_half_cycle(self, duration, precursor=None, c_init=0.0,
                            theta_init=0.0, inlet=None, n_out=200,
                            saturation_target=None, rtol=1e-6, atol=1e-10,
                            method="BDF", quasi_steady=False):
        """Integrate (1)-(2) over one dose or purge.

        Parameters
        ----------
        duration : float
            Length of the step [s].
        precursor : Precursor, optional
            Defaults to `self.precursor`.
        c_init : scalar | array | callable
            Initial pore-gas number density [m^-3].  **User-defined IC.**
        theta_init : scalar | array | callable
            Initial fractional coverage [-].  **User-defined IC.**
        inlet : None | float | callable
            Reactor-side partial pressure above the film [Pa].  None => dose at
            `precursor.pressure`; 0.0 => purge; a callable t -> Pa gives an
            arbitrary waveform.
        saturation_target : float, optional
            If given, integration stops early once the *minimum* coverage over
            the accessible depth reaches this value, and the time is recorded
            in `result.saturated_at`.
        quasi_steady : bool
            Drop the eps dC/dt term, i.e. assume the pore gas equilibrates
            instantly with the current coverage.  The capacity ratio alpha
            (:meth:`capacity_ratio`) is the ratio of the two timescales and is
            typically 1e4-1e6, so the approximation is excellent -- and it
            removes exactly the stiffness that makes the transient form hard to
            integrate once the pores tighten.  With irreversible chemisorption
            the quasi-steady gas balance is *linear* in C, so each step costs
            one tridiagonal solve and `c_init` is ignored (C is slaved to
            theta).  Recommended for multi-cycle runs.

            Not valid for purge steps: the residual pore gas is zero by
            construction, and that residual is exactly what a purge calculation
            measures.  :meth:`purge` and :meth:`purge_time` therefore always
            use the transient form.

        Returns
        -------
        HalfCycleResult
        """
        precursor = precursor or self.precursor
        n = self.n_cells
        dz = self.dz
        gamma = self.gamma_for(precursor)
        v_th = precursor.thermal_speed(self.T)

        # scale the gas field by the dose density so the state is O(1)
        c_ref = self.gas_density(precursor.pressure)
        if c_ref <= 0:
            raise ValueError("precursor pressure must be > 0")

        # frozen-geometry coefficients for this half-cycle
        eps = np.maximum(self.eps, 1e-8)
        s_v = self.specific_area()
        d_e = self.effective_diffusivity(precursor)
        open_cell = self.eps > self.film.pore_closure_porosity

        # face diffusivities: harmonic mean (series resistance)
        d_l, d_r = d_e[:-1], d_e[1:]
        denom = d_l + d_r
        d_face = np.where(denom > 0, 2.0 * d_l * d_r / np.where(denom > 0, denom, 1.0), 0.0)

        k_ads = np.where(open_cell,
                         precursor.sticking * (v_th / 4.0) * c_ref / gamma, 0.0)
        alpha = s_v * gamma / c_ref          # surface capacity / gas inventory
        n_exp = precursor.sticking_exponent
        k_des = precursor.k_des

        # inlet waveform, in scaled units
        if inlet is None:
            inlet_u = lambda t: 1.0
        elif callable(inlet):
            inlet_u = lambda t: inlet(t) / (kB * self.T) / c_ref
        else:
            u_const = float(inlet) / (kB * self.T) / c_ref
            inlet_u = lambda t: u_const

        # top-face conductance: external mass transfer in series with half a cell
        if d_e[0] <= 0 or self.mass_transfer == 0:
            # closed top cell, or a deliberately sealed surface
            top_cond = 0.0
        else:
            half_cell = dz / (2.0 * d_e[0])
            if self.mass_transfer is None:
                top_cond = 1.0 / half_cell          # Dirichlet at z = 0
            else:
                top_cond = 1.0 / (1.0 / self.mass_transfer + half_cell)

        flux = np.zeros(n + 1)

        # ---- quasi-steady gas field: solve  d/dz(D dC/dz) = S_v Gamma dtheta/dt
        # for u given theta.  Linear in u, tridiagonal, one solve per step.
        inv_dz2 = 1.0 / dz ** 2
        lower = np.zeros(n)          # coefficient on u_{i-1}
        upper = np.zeros(n)          # coefficient on u_{i+1}
        lower[1:] = d_face * inv_dz2
        upper[:-1] = d_face * inv_dz2

        def gas_quasi_steady(t, th):
            avail = np.clip(1.0 - th, 0.0, None)
            sink = alpha * k_ads * np.power(avail, n_exp)     # a_i
            diag = -(lower + upper) - sink
            rhs_vec = -alpha * k_des * th
            u_in = inlet_u(t)
            diag[0] -= top_cond / dz
            rhs_vec[0] -= top_cond * u_in / dz
            # cells with no transport and no reaction (sealed pores) drop out
            isolated = diag == 0.0
            if isolated.any():
                diag = np.where(isolated, 1.0, diag)
                rhs_vec = np.where(isolated, 0.0, rhs_vec)
            ab = np.zeros((3, n))
            ab[0, 1:] = upper[:-1]
            ab[1] = diag
            ab[2, :-1] = lower[1:]
            return np.clip(solve_banded((1, 1), ab, rhs_vec), 0.0, None)

        def rhs_qs(t, th):
            u = gas_quasi_steady(t, th)
            avail = np.clip(1.0 - th, 0.0, None)
            return k_ads * np.power(avail, n_exp) * u - k_des * th

        def rhs(t, y):
            u = y[:n]
            th = y[n:]
            avail = np.clip(1.0 - th, 0.0, None)
            dth = k_ads * np.power(avail, n_exp) * np.clip(u, 0.0, None) - k_des * th
            flux[1:n] = -d_face * (u[1:] - u[:-1]) / dz
            flux[0] = top_cond * (inlet_u(t) - u[0])
            flux[n] = 0.0
            du = (-(flux[1:] - flux[:n]) / dz - alpha * dth) / eps
            return np.concatenate((du, dth))

        # Jacobian sparsity: u_i <- u_{i-1}, u_i, u_{i+1}, th_i ; th_i <- u_i, th_i
        jac = lil_matrix((2 * n, 2 * n), dtype=int)
        rows = np.arange(n)
        jac[rows, rows] = 1
        jac[rows[:-1], rows[:-1] + 1] = 1
        jac[rows[1:], rows[1:] - 1] = 1
        jac[rows, rows + n] = 1
        jac[rows + n, rows] = 1
        jac[rows + n, rows + n] = 1

        theta0 = self._as_profile(theta_init)
        t_eval = np.linspace(0.0, duration, n_out)

        # coverage lives in the tail of the state vector in transient mode and
        # is the whole state in quasi-steady mode
        theta_offset = 0 if quasi_steady else n

        events = None
        if saturation_target is not None:
            # Judge saturation on the *accessible* surface only: cells whose
            # pores have closed can never be dosed, so including them would
            # make the target unreachable once infill starts sealing pores.
            open_idx = np.nonzero(open_cell)[0]

            def hit_saturation(t, y):
                if open_idx.size == 0:
                    return 1.0
                return float(np.min(y[theta_offset:][open_idx])
                             - saturation_target)
            hit_saturation.terminal = True
            hit_saturation.direction = 1.0
            events = [hit_saturation]

        if quasi_steady:
            y0 = theta0
            # theta_i couples to theta_j through the gas field, so the Jacobian
            # is dense in principle; n is small enough for the default.
            kwargs = dict(method="LSODA")
        else:
            y0 = np.concatenate((self._as_profile(c_init) / c_ref, theta0))
            # Jacobian sparsity: u_i <- u_{i-1}, u_i, u_{i+1}, th_i;
            #                    th_i <- u_i, th_i
            jac = lil_matrix((2 * n, 2 * n), dtype=int)
            rows = np.arange(n)
            jac[rows, rows] = 1
            jac[rows[:-1], rows[:-1] + 1] = 1
            jac[rows[1:], rows[1:] - 1] = 1
            jac[rows, rows + n] = 1
            jac[rows + n, rows] = 1
            jac[rows + n, rows + n] = 1
            kwargs = dict(method=method, jac_sparsity=jac.tocsr())

        sol = solve_ivp(rhs_qs if quasi_steady else rhs, (0.0, duration), y0,
                        t_eval=t_eval, rtol=rtol, atol=atol, events=events,
                        dense_output=events is not None, **kwargs)
        if not sol.success:
            raise RuntimeError(
                "integration failed: %s%s" % (sol.message, "" if quasi_steady
                                              else "  (try quasi_steady=True: "
                                              "capacity ratio %.2e makes the "
                                              "transient form very stiff)"
                                              % self.capacity_ratio(precursor)))

        t = sol.t
        y = sol.y
        saturated_at = None
        if events is not None and sol.t_events[0].size:
            # t_eval is truncated at the event; append the event state.  Taken
            # from the dense output rather than sol.y_events, which needs
            # scipy >= 1.4.
            saturated_at = float(sol.t_events[0][0])
            t = np.append(t, saturated_at)
            y = np.column_stack((y, sol.sol(saturated_at)))

        theta = np.clip(y[theta_offset:].T, 0.0, 1.0)
        if quasi_steady:
            # reconstruct the slaved gas field at each output time
            C = np.array([gas_quasi_steady(ti, thi)
                          for ti, thi in zip(t, theta)]) * c_ref
        else:
            C = (y[:n].T) * c_ref
        return HalfCycleResult(t, self.z.copy(), C, theta, self.T, precursor,
                               saturated_at)

    # ---- convenience wrappers -------------------------------------------
    def dose(self, duration, precursor=None, **kw):
        """Precursor exposure at `precursor.pressure`."""
        return self.simulate_half_cycle(duration, precursor=precursor, **kw)

    def purge(self, duration, precursor=None, c_init=None, theta_init=None, **kw):
        """Inert purge: inlet pressure held at zero.

        Always transient -- the quantity of interest is the decaying residual,
        which the quasi-steady approximation sets to zero by construction.
        """
        kw.pop("quasi_steady", None)
        return self.simulate_half_cycle(duration, precursor=precursor,
                                        c_init=c_init, theta_init=theta_init,
                                        inlet=0.0, **kw)

    def saturation_dose_time(self, target=0.99, t_max=None, precursor=None,
                             **kw):
        """Dose time needed for coverage to reach `target` at *every* depth [s].

        Returns (time, HalfCycleResult).  time is None if saturation was not
        reached within t_max (default: 20x the sharp-front estimate).
        """
        precursor = precursor or self.precursor
        if t_max is None:
            t_max = 20.0 * self.saturation_time_estimate(precursor)
        res = self.simulate_half_cycle(t_max, precursor=precursor,
                                       saturation_target=target, **kw)
        return res.saturated_at, res

    def purge_time(self, residual=1e-3, t_max=None, precursor=None,
                   c_init=None, theta_init=1.0, **kw):
        """Purge time for the peak pore-gas density to fall to `residual` x the
        dose density [s].  Returns (time, HalfCycleResult)."""
        precursor = precursor or self.precursor
        c_dose = self.gas_density(precursor.pressure)
        if c_init is None:
            c_init = c_dose
        if t_max is None:
            t_max = 100.0 * self.diffusion_time(precursor)
        res = self.purge(t_max, precursor=precursor, c_init=c_init,
                         theta_init=theta_init, **kw)
        peak = np.max(res.C, axis=1) / c_dose
        below = np.nonzero(peak <= residual)[0]
        t_purge = float(res.t[below[0]]) if below.size else None
        return t_purge, res

    # ---- multi-cycle infill ---------------------------------------------
    def grow(self, theta_limiting):
        """Advance the geometry by one ALD cycle given the limiting coverage.

        Deposits a shell of thickness gpc * theta_limiting on the internal
        surface and updates porosity by the volume balance d(eps) = -S_v dt.
        """
        s_v = self.specific_area()
        dt_film = self.gpc * np.clip(theta_limiting, 0.0, 1.0)
        # never deposit more than the remaining void can hold
        headroom = np.where(s_v > 0, self.eps / np.where(s_v > 0, s_v, 1.0),
                            0.0)
        dt_film = np.minimum(dt_film, headroom)
        self.eps = np.clip(self.eps - s_v * dt_film, 0.0, 1.0)
        self.r_eff = self.r_eff + dt_film
        self.t_film = self.t_film + dt_film
        return dt_film

    def run_cycles(self, n_cycles, t_dose, t_purge, t_dose_b=None,
                   t_purge_b=None, dose_target=None, reset=True, n_out=40,
                   quasi_steady=True, verbose=False):
        """Run `n_cycles` full ALD cycles and track the infill.

        Each cycle is dose A -> purge -> dose B -> purge.  Coverage is reset
        between half-reactions (chemisorbed A is consumed by B); the growth
        increment is gpc * min(theta_A, theta_B).  Geometry (porosity, pore
        radius, surface area, diffusivity) is updated after every cycle, so
        transport slows down as the network fills and stops entirely where the
        pores close.

        Parameters
        ----------
        t_dose, t_purge : float
            Half-cycle A timings [s]; `t_dose_b`/`t_purge_b` default to them.
        dose_target : float, optional
            If given, the dose is re-sized every cycle: each exposure runs only
            until the least-covered *accessible* cell reaches this coverage,
            with `t_dose` as the cap.  This matters because the dose time needed
            grows by orders of magnitude as the pores close -- a dose fixed at
            the first-cycle requirement becomes starved late in the run, seals
            the top of the film, and strands the interior porous.
        quasi_steady : bool
            Use the quasi-steady gas field for the *doses* (default True).  The
            transient form becomes extremely stiff in the last cycles before
            pore closure, where alpha/eps exceeds 1e6.  Purges are always
            transient.

        Returns
        -------
        CycleResult
        """
        if reset:
            self.reset_geometry()
        t_dose_b = t_dose if t_dose_b is None else t_dose_b
        t_purge_b = t_purge if t_purge_b is None else t_purge_b
        out = CycleResult(self.z.copy())

        for cycle in range(1, n_cycles + 1):
            accessible = self.eps > self.film.pore_closure_porosity
            if not np.any(accessible):
                if verbose:
                    print("cycle %d: pore network fully closed" % cycle)
                break

            res_a = self.simulate_half_cycle(t_dose, precursor=self.precursor,
                                             saturation_target=dose_target,
                                             quasi_steady=quasi_steady,
                                             n_out=n_out)
            dose_time = res_a.saturated_at if res_a.saturated_at is not None \
                else t_dose
            theta_a = res_a.theta_final
            purge_a = self.purge(t_purge, precursor=self.precursor,
                                 c_init=res_a.C[-1], theta_init=theta_a,
                                 n_out=n_out)

            if self.coreactant is not None:
                res_b = self.simulate_half_cycle(t_dose_b,
                                                 precursor=self.coreactant,
                                                 saturation_target=dose_target,
                                                 quasi_steady=quasi_steady,
                                                 n_out=n_out)
                theta_b = res_b.theta_final
                purge_b = self.purge(t_purge_b, precursor=self.coreactant,
                                     c_init=res_b.C[-1], theta_init=theta_b,
                                     n_out=n_out)
                residual = max(purge_a.residual_fraction(),
                               purge_b.residual_fraction())
                dose_time = max(dose_time, res_b.saturated_at
                                if res_b.saturated_at is not None else t_dose_b)
            else:
                theta_b = np.ones_like(theta_a)
                residual = purge_a.residual_fraction()

            theta_lim = np.minimum(theta_a, theta_b)
            self.grow(theta_lim)
            out._append(cycle, theta_lim, self.t_film, self.eps, residual,
                        dose_time, accessible)

            closed = self.eps <= self.film.pore_closure_porosity
            if closed.all() and out.cycles_to_infill is None:
                out._set_infill(cycle)
            if verbose:
                print("cycle %3d  theta_min=%.3f  eps: top=%.3f bottom=%.3f "
                      "  closed=%d/%d"
                      % (cycle, theta_lim.min(), self.eps[0], self.eps[-1],
                         closed.sum(), self.n_cells))
            if closed.all():
                break

        return out.finalize()


# --------------------------------------------------------------------------
# a worked default: Al2O3 (TMA/H2O) infilling a ZnO nanocrystal film
# --------------------------------------------------------------------------
def default_model(**overrides):
    """TMA/H2O -> Al2O3 infill of a 1 um, 50%-porous, 5 nm-radius NC network."""
    kw = dict(
        film=NCFilm(thickness=1.0e-6, nc_radius=5.0e-9, porosity=0.5),
        precursor=Precursor("TMA", M=72.09e-3, sticking=0.01, pressure=100.0),
        coreactant=Precursor("H2O", M=18.02e-3, sticking=0.005, pressure=100.0),
        T=473.0, gpc=1.1e-10,
        film_density=3990.0, film_molar_mass=0.101961,
        metal_per_formula=2, metal_per_molecule=1,
        n_cells=120,
    )
    kw.update(overrides)
    return NCInfillModel(**kw)


if __name__ == "__main__":
    m = default_model()
    print("Gamma            = %.3e m^-2" % m.site_density())
    print("S_v              = %.3e m^2/m^3" % m.specific_area()[0])
    print("pore radius      = %.3e m" % m.pore_radius()[0])
    print("D_eff (TMA)      = %.3e m^2/s" % m.effective_diffusivity(m.precursor)[0])
    print("capacity ratio   = %.3e" % m.capacity_ratio())
    print("dose estimate    = %.3e s" % m.saturation_time_estimate())

    t_sat, res = m.saturation_dose_time(target=0.99)
    print("dose to 99%% at L = %s s" % t_sat)
    print("penetration (50%%) = %.3e m" % res.penetration_depth(0.5))

    t_pg, _ = m.purge_time(residual=1e-3)
    print("purge to 1e-3     = %s s" % t_pg)
