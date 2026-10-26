"""A1: the paper's approximation with Table I reproduces the paper's fitted curves (KB yli18 Fig. 6, 7)."""
import os, sys, json, numpy as np, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from yli18_approx import thickness, q_from_film
FIG = os.environ.get("PSED_YLI18_FIGURES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb", "10.1063_1.5028178.figures.json"))
C = {c["id"]: np.array(c["points"]) for c in json.load(open(FIG))["curves"]}
CASES = {   # Table I + Sec. 8 (KB yli18:tabI.*, s8.p24#*); film density: Al2O3 3990 (gives q = 5 nm-2 as Fig. 2), TiO2 4230 assumed (rutile)
 "Al2O3": (dict(N=500, gpc_sat=0.1056e-9, H0=0.5e-6, W=0.1e-3, T=573.15, pA0=147.0, t_pulse=0.1, c=0.00572, K=219.0,
                MA=72.09, dA=591e-12, q=q_from_film(0.1056e-9, 3990.0, 101.96, 2)), "yli18:fig6#c1", 4.0),
 "TiO2":  (dict(N=1000, gpc_sat=0.0544e-9, H0=0.5e-6, W=0.1e-3, T=383.15, pA0=25.7, t_pulse=0.1, c=0.10, K=0.252,
                MA=189.68, dA=703.9e-12, q=q_from_film(0.0544e-9, 4230.0, 79.87, 1)), "yli18:fig7#c1", 1.5),
}
@pytest.mark.parametrize("name", list(CASES))
def test_plateau_and_profile(name):
    kw, fid, tol = CASES[name]
    x, s = thickness(**kw); P = C[fid]
    assert abs(s[0] / P[0, 1] - 1) < 0.01                                          # plateau within 1 %
    assert np.sqrt(np.mean((np.interp(P[:, 0], x * 1e6, s) - P[:, 1]) ** 2)) < tol   # RMSE vs paper fit
