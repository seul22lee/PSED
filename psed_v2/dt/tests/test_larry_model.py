"""Tests for Larry's model after the logged changes (CHANGELOG.md). Data: yli18 curves in the KB.
KB path: env PSED_YLI18_FIGURES."""
import os, sys, json, warnings, numpy as np, pytest, torch
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import reaction_model as M
from scipy.constants import N_A

FIG = os.environ.get("PSED_YLI18_FIGURES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb", "10.1063_1.5028178.figures.json"))
C = {c["id"]: np.array(c["points"]) for c in json.load(open(FIG))["curves"]}
front = lambda x, y: float(np.interp(0.5, y[::-1], x[::-1]))

def channel_fig2(dt=1e-4, K=100.0):
    """yli18 Fig. 2 caption inputs (KB yli18:fig2.cap#1-13) in Larry's ChannelModel."""
    q = 5e18
    s0 = np.array([[N_A / q], [N_A / q]])                                    # site area per mol (= adsorption_area)
    vth = np.array([[M.particle_velocity(74.9e-3 / N_A, 500.0)], [M.particle_velocity(18.02e-3 / N_A, 500.0)]])
    return M.ChannelModel(s0=s0, vth=vth, dt=dt, xpos=None, W=0.1e-3, H=0.5e-6, T=500.0, L=1e-3,
                          carrier_pressure=300.0, points=400, K=K, logbetas=[np.log(0.01), np.log(0.01)],
                          reactants={"TMA": {"M": 74.9, "d_r": 591e-12}, "H2O": {"M": 18.02, "d_r": 418e-12}},
                          carrier={"M": 28.0, "d_r": 374e-12})

def run_pulse(ch, tp, pA0=100.0):
    with torch.no_grad():
        for _ in range(round(tp / ch.dt)):
            ch.step(torch.tensor([pA0, 0.0], dtype=torch.float64))
    return np.arange(ch.theta.shape[1]) * ch.dz * 1e6, ch.theta[0].numpy()

def test_C1_za_differs_by_reactant():
    ch = channel_fig2()
    za = [float(f(torch.tensor(100.0))) for f in ch.za_funcs]
    assert za[0] != za[1]

def test_C2_deff_matches_paper_order():          # yli18 Sec. III: D_eff "typically about 1 cm2/s"
    ch = channel_fig2()
    D = float(ch.calc_Deff(float(ch.vths[0, 0]), ch.za_funcs[0](torch.tensor(100.0))))
    assert 0.8e-4 < D < 1.5e-4

OPEN = pytest.mark.xfail(strict=True, reason="0.01 s: 14-17 % short in every solver (also the BDF reference) -> input/digitization, open")
@pytest.mark.parametrize("tp,cid", [pytest.param(0.01, "yli18:fig3#c7", marks=OPEN), (0.02, "yli18:fig3#c5"),
                                    (0.05, "yli18:fig3#c3"), (0.1, "yli18:fig3#c1")])
def test_fig3_front_vs_paper_numerical(tp, cid):  # front within 10 % of the paper's numerical solution
    x, th = run_pulse(channel_fig2(), tp)
    P = C[cid]
    assert abs(front(x, th) / front(P[:, 0], P[:, 1]) - 1) < 0.10

def test_C5_stable_at_coupling_step():           # dt = t_step of ModelCoupling (0.005 s): finite, theta in [0, 1]
    x, th = run_pulse(channel_fig2(dt=0.005), 0.1)
    assert np.isfinite(th).all() and th.min() >= 0 and th.max() <= 1

def test_C6_K_none_is_irreversible():            # K=None keeps Larry's model: theta -> 1 behind the front
    x, th = run_pulse(channel_fig2(K=None), 0.05)
    assert th[1] > 0.999

def test_R_reactor_tma_reaches_sample_in_time():  # R1-R3: 33 cm at u = 2.16 m/s ~ 0.15 s; theta = 0.5 well before 1 s
    m = M.ModelCoupling()
    assert abs(m.model.reactor.u - 2.157) < 0.01
    x, th, thick, sth, tau = m.run_model(1.0, log_freq=1)
    assert tau[np.argmax(sth > 0.5)] < 0.5

def test_G1_one_gpc_per_cycle():                 # G1: a full cycle (fill + reset) adds 1 x gpc, not 2
    recipe = [{'t': 0.1, 'p': [M.tma_n0, 0]}, {'t': 1.0, 'p': [0, 0]}, {'t': 0.5, 'p': [0, M.h2o_n0]}, {'t': 1.0, 'p': [0, 0]}]
    m = M.ModelCoupling(recipe=recipe)
    x, th, thick, sth, tau = m.run_model(2 * m.cycle_time, log_freq=1, gpc=1)
    assert sth.max() > 0.99 and sth[-1] < 0.01        # sample saturates and is reset each cycle
    assert abs(thick[-1] - 2.0) < 0.05                 # two cycles -> 2 x gpc

def test_P1_sample_betas_per_reactant():          # P1: ModelCoupling passes [beta_A, beta_B] to both sample models
    m = M.ModelCoupling(sample_betas=[4e-3, 3e-4])
    assert np.allclose(m.flat_model.get_betas(), [4e-3, 3e-4]) and np.allclose(m.har_model.get_betas(), [4e-3, 3e-4])
    d = M.ModelCoupling()                         # default unchanged: Larry's 0.001 for both
    assert np.allclose(d.flat_model.get_betas(), [1e-3, 1e-3]) and np.allclose(d.har_model.get_betas(), [1e-3, 1e-3])
