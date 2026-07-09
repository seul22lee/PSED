"""
channel_model.py  (M0)
----------------------
The ALD conformality digital twin (Ylilammi approximate model), extracted from the
Digital_Twin_mpc notebooks into an importable module so it can be *parameterised*
from the knowledge base (see kb_bridge.py) instead of hardcoding one process.

Physics is preserved verbatim from the notebook `channelModelMPC`:
  · Langmuir surface kinetics in a lateral high-aspect-ratio channel
  · effective diffusion (gas-phase + Knudsen), reactant partial-pressure profile
  · thickness = gpc · Σθ, penetration depth = where p_A(x) drops to 50% of inlet

All parameters keep the notebook's hardcoded defaults (Al2O3/TMA/H2O), so
`channelModel()` behaves exactly as before; `channelModel.from_kb(...)` swaps in
literature values.
"""
import copy
import numpy as np

# which ontology model this code implements (0706_ontology core.yaml `models:`)
MODEL_ID = "ylilammi_langmuir_channel"

# ---- physical constants (from notebook) ----
N0 = 6.22e23            # Avogadro (as used in the notebook)
kB = 1.38e-23           # Boltzmann constant  [J/K]
R = 8.314               # gas constant        [J/(K·mol)]

# the ~16 model parameters, grouped (used for provenance display)
PARAMS = ["gpc", "K", "c", "da", "db", "MA", "MB", "M", "rho", "b_film", "b_a",
          "H", "W", "T", "pA", "pB", "t_p"]


class channelModel:
    """Ylilammi channel conformality model. SI units throughout
    (m, kg/mol, K, Pa, s)."""

    def __init__(self):
        # ---- film / material ----
        self.M = 101.96 / 1000      # kg/mol  (Al2O3 formula unit)
        self.rho = 3.99 * 1000      # kg/m^3  (film density)
        self.b_film = 2             # metal atoms per film formula unit
        self.b_a = 1                # metal atoms per precursor molecule (TMA)
        # ---- reaction ----
        self.c = 0.01               # sticking / reaction probability
        self.K = 100                # Langmuir equilibrium constant [1/Pa]
        self.gpc = 106e-12          # growth per cycle [m]
        # ---- collision species (Ylilammi §II) ----
        # A = the metal PRECURSOR (growth-limiting); B = the BACKGROUND/CARRIER gas
        # it collides with. In the paper this is NITROGEN (d_B=374 pm, M_B=0.028
        # kg/mol; Figs. 2–5 captions) — NOT the coreactant water, which diffuses too
        # fast to limit transport and is excluded from the model.
        self.da = 591e-12           # precursor A molecular diameter [m] (TMA)
        self.db = 374e-12           # background gas B molecular diameter [m] (N2)
        self.MA = 72.09e-3          # precursor A molar mass [kg/mol] (TMA)
        self.MB = 28.01e-3          # background gas B molar mass [kg/mol] (N2)
        # ---- geometry ----
        self.H = 0.2e-6             # feature height [m]
        self.W = 0.1e-3             # feature width [m]
        # ---- process ----
        self.T = 300 + 273          # temperature [K]
        self.t_p = 0.1              # pulse time [s]
        self.pA = 100               # precursor A partial pressure [Pa]
        self.pB = 300               # background gas B (N2) partial pressure [Pa]
        self.kb_provenance = {}     # filled by from_kb()

    # ---- derived quantities ----
    def calc_hydro_diameter(self):
        self.h = 2 / (1 / self.H + 1 / self.W)

    def calc_adsorption_density(self):
        self.q = (self.b_film / self.b_a) * (self.rho * self.gpc / self.M) * N0

    def collision_rate(self):
        self.Q = N0 / np.sqrt(2 * np.pi * self.M * R * self.T)

    def calc_za(self):
        self.za = (np.pi / 4 * ((self.da + self.db) ** 2)
                   * np.sqrt(8 * R * self.T / np.pi * (1 / self.MA + 1 / self.MB)) * self.pB
                   + np.pi * self.da ** 2 * np.sqrt(16 * R * self.T / (np.pi * self.MA)) * self.pA) / (R * self.T)

    def calc_Deff(self):
        va = np.sqrt(8 * R * self.T / (np.pi * self.MA))
        Da = 3 * np.pi / 16 * va ** 2 / self.za
        Dkn = self.h * np.sqrt(8 * R * self.T / (9 * np.pi * self.MA))
        self.Deff = 1 / (1 / Da + 1 / Dkn)

    def prepare(self):
        self.collision_rate()
        self.calc_adsorption_density()
        self.calc_za()
        self.calc_hydro_diameter()
        self.calc_Deff()

    # ---- forward model: reactant pressure profile + thickness ----
    def approx(self, x, last_theta):
        D = (self.pA * self.Deff * self.H /
             (self.q * kB * self.T *
              (1 - np.log(self.K * self.pA + 1) / (self.K * self.pA))))
        xs = np.sqrt(D * self.t_p)
        delim = np.sqrt((self.h * N0 * self.Deff) / (4 * R * self.T * self.c * self.Q))
        xt = max(xs - delim, 0.0)
        pt = self.pA * (1 - xt / xs) if xs > 0 else 0.0
        pA = self.pA * (1 - x / xs)
        if xs - xt > 0:
            pA[x > xt] = pt * np.exp(-(x[x > xt] - xt) / (xs - xt))
        else:
            pA[x > xt] = 0.0
        pA = np.clip(pA, 0, None)
        theta = (self.K * pA) / (1 + self.K * pA)
        next_theta = last_theta + theta
        thickness = self.gpc * next_theta
        return thickness, next_theta, {"pA": pA, "theta": theta, "xs": xs, "xt": xt}

    # ---- convenience: one-shot simulation over a grid ----
    def simulate(self, x=None, last_theta=None):
        """Return (x, thickness, info) for a single pulse. Builds a sensible x-grid
        (0 .. ~1.5·penetration) if none is given."""
        self.prepare()
        if x is None:
            probe = np.linspace(0, 5 * self.W if self.W else 1e-3, 4000)
            _, _, info0 = self.approx(probe, np.zeros_like(probe))
            xmax = max(info0["xs"] * 1.3, 1e-6)
            x = np.linspace(0, xmax, 400)
        if last_theta is None:
            last_theta = np.zeros_like(x)
        thickness, next_theta, info = self.approx(x, last_theta)
        return x, thickness, info

    def penetration_depth(self, x=None):
        """PD50: channel position where p_A drops to 50% of its inlet value."""
        x, _, info = self.simulate(x)
        pA = info["pA"]
        if pA[0] <= 0:
            return 0.0
        half = 0.5 * pA[0]
        idx = np.where(pA <= half)[0]
        if len(idx) == 0:
            return float(x[-1])
        i = idx[0]
        if i == 0:
            return float(x[0])
        slope = (pA[i] - pA[i - 1]) / (x[i] - x[i - 1])
        return float(x[i - 1] + (half - pA[i - 1]) / slope)

    def param_table(self):
        """Current parameter values + provenance (for inspection/visualisation)."""
        return {p: {"value": getattr(self, p, None),
                    **self.kb_provenance.get(p, {"source": "default"})} for p in PARAMS}

    # ---- M1: build from the knowledge base ----
    @classmethod
    def from_kb(cls, material, process=None, species=None, carrier=None, verbose=False):
        """Construct a twin whose parameters come from the KB (kb_bridge), falling
        back to the hardcoded defaults for anything the KB doesn't have.
        `species` = {"A":"TMA", ...} grounds A (the precursor). The B collision
        partner is the BACKGROUND/CARRIER gas (Ylilammi §II), so `carrier` (e.g.
        "N2") grounds db/MB — NOT the coreactant. da/MA/b_a come from A's ontology
        individual; db/MB from the carrier's."""
        from kb_bridge import params_for
        m = cls()                                   # hardcoded defaults = fallback
        sp = dict(species or {})
        if carrier:
            sp["B"] = carrier                       # collision partner B = background gas
        resolved, prov = params_for(material, process, sp or None)
        for attr, val in resolved.items():
            setattr(m, attr, val)
        m.kb_provenance = prov
        if verbose:
            for p in PARAMS:
                pr = prov.get(p, {"source": "default"})
                print(f"  {p:7} = {getattr(m, p):.4g}   [{pr['source']}]"
                      + (f"  ±{pr.get('sigma',0):.3g} (n={pr.get('n')}, {','.join(pr.get('refs',[]))})"
                         if pr['source'] == 'kb' else ""))
        return m


if __name__ == "__main__":
    m = channelModel()
    x, th, info = m.simulate()
    print(f"default twin: penetration PD50 = {m.penetration_depth()*1e6:.2f} µm, "
          f"xs = {info['xs']*1e6:.2f} µm, max thickness = {th.max()*1e9:.2f} nm")
