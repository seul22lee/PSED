"""
inverse_solver.py — M2 target-dose solver by twin inversion.
------------------------------------------------------------
One-dimensional target matching under a FIXED pA/tp ratio. Given a target
penetration depth, solve directly for the dose the channel model needs:

    pA(D, r) = sqrt(D * r)          tp(D, r) = sqrt(D / r)
    F(D; r)  = PD50(pA(D,r), tp(D,r), … everything else fixed)
    solve    F(D; r) - target = 0

This is scalar ROOT FINDING on a physical forward model — not gradient descent,
not MPC, not general ALD recipe optimisation. Exactly one unknown (the dose)
moves; the ratio, temperature, geometry, species and model parameters are held.

Why a solver replaced the previous proportional controller: the controller
multiplied the dose by (1 + Kp·e) and clamped it, so an unreachable target was
indistinguishable from a slow one — both ran to the iteration cap and reported an
error, never "this target is outside the model's range". Feasibility here is
decided BEFORE any iteration, by evaluating the two bracket ends.

Analytic inverse: NOT available for the full model. PD50 is the 50 % crossing of
a piecewise profile (linear then exponential, joined at xt) located numerically on
a discrete grid, and the diffusion length
    xs = sqrt(t_p · pA·Deff·H / (q·kB·T·(1 - ln(K·pA+1)/(K·pA))))
depends on pA through BOTH a Bosanquet Deff(za(pA)) and a nonlinear Langmuir
factor. In the dilute limit (K·pA ≪ 1, Da ≫ Dkn) the model degenerates to
PD ∝ sqrt(D) — and empirically the current configuration sits close to that, with
a measured log-log slope of 0.4995. That limiting case is documented, not
substituted: the solver always calls the real model.
"""
from dataclasses import dataclass, field, asdict
import math

import numpy as np

# The channel model mutates itself on evaluation (pA, t_p and every prepare()-derived
# attribute), so every evaluation is sandwiched by save/restore. Without this a failed
# or exploratory evaluation would silently leave the twin at a bogus operating point.
_STATE_ATTRS = ("pA", "t_p", "q", "Q", "za", "h", "Deff")

STATUSES = ("solved", "infeasible_low", "infeasible_high", "saturated", "non_monotonic",
            "multiple_roots", "invalid_bounds", "model_error", "no_ratio", "max_evaluations")


@dataclass
class DoseSolution:
    """Structured solver result — never a bare tuple, so a caller cannot mistake an
    infeasible target for a converged one."""
    status: str
    feasible: bool
    target_pd: float = None                 # m
    achieved_pd: float = None               # m
    dose: float = None                      # Pa·s
    pA: float = None                        # Pa
    pulse_time: float = None                # s
    ratio: float = None                     # Pa/s
    residual: float = None                  # m  (achieved - target)
    effective_dose_bounds: tuple = None
    achievable_pd: tuple = None             # (PD at D_lo, PD at D_hi)
    model_evaluations: int = 0
    method: str = None
    tolerance_pd: float = None
    reference: dict = field(default_factory=dict)   # literature/KB warm start
    provenance: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    reason: str = None
    roots: list = field(default_factory=list)
    root_policy: str = None

    def to_dict(self):
        return asdict(self)


class _Evaluator:
    """Safe, counted forward evaluation of PD50 at a given dose."""

    def __init__(self, model, ratio):
        self.model, self.ratio, self.n = model, ratio, 0
        # snapshot the caller's state ONCE, so an aborted solve rewinds all the way back
        # rather than to whichever evaluation happened to succeed last
        self._entry = {a: getattr(model, a, None) for a in _STATE_ATTRS}

    def restore_entry(self):
        for a, v in self._entry.items():
            setattr(self.model, a, v)

    def __call__(self, dose):
        if not (isinstance(dose, (int, float)) and math.isfinite(dose)) or dose <= 0:
            raise ValueError(f"dose must be finite and positive, got {dose!r}")
        saved = {a: getattr(self.model, a, None) for a in _STATE_ATTRS}
        try:
            self.model.pA = float(np.sqrt(dose * self.ratio))
            self.model.t_p = float(np.sqrt(dose / self.ratio))
            self.model.prepare()
            pd = float(self.model.penetration_depth())
            self.n += 1
            if not math.isfinite(pd):
                raise ValueError(f"model returned non-finite PD ({pd}) at dose {dose:.6g}")
            return pd
        except Exception:
            for a, v in saved.items():                 # never leave the twin mid-flight
                if v is not None:
                    setattr(self.model, a, v)
            raise

    def restore_to(self, dose):
        """Leave the model AT the given operating point (the contract after a solve)."""
        self.model.pA = float(np.sqrt(dose * self.ratio))
        self.model.t_p = float(np.sqrt(dose / self.ratio))
        self.model.prepare()


def effective_dose_bounds(ratio, dose_bounds=None, pressure_bounds=None, pulse_time_bounds=None):
    """Intersect the configured dose window with the windows implied by the pA and tp
    limits, since both are reconstructed from the dose at fixed ratio:
        pA_min <= sqrt(D·r) <= pA_max   ->   D in [pA_min^2/r, pA_max^2/r]
        tp_min <= sqrt(D/r) <= tp_max   ->   D in [tp_min^2·r, tp_max^2·r]
    Returns (lo, hi); lo > hi means the constraints conflict."""
    lo, hi = (dose_bounds or (0.0, math.inf))
    lo = max(lo or 0.0, 0.0)
    hi = hi if hi is not None else math.inf
    if pressure_bounds:
        plo, phi = pressure_bounds
        lo = max(lo, (plo ** 2) / ratio)
        hi = min(hi, (phi ** 2) / ratio)
    if pulse_time_bounds:
        tlo, thi = pulse_time_bounds
        lo = max(lo, (tlo ** 2) * ratio)
        hi = min(hi, (thi ** 2) * ratio)
    return lo, hi


def solve_target_dose(model, target_pd, ratio, dose_bounds=None, pressure_bounds=None,
                      pulse_time_bounds=None, tolerance_pd=1e-9, max_evaluations=200,
                      monotonicity_samples=25, root_policy="min_dose", reference=None,
                      provenance=None, leave_model_at_solution=True):
    """Solve F(D; ratio) = target_pd for the dose, by bracketed root finding.

    target_pd / tolerance_pd are in METRES (SI throughout; callers convert for display).
    `reference` carries the literature/KB warm start — it is recorded for comparison and
    is NOT numerically required: with a valid bracket the root is independent of it.
    Returns a DoseSolution; an unreachable target is reported as infeasible_*, never as
    a convergence failure."""
    warns, prov = [], dict(provenance or {})
    ref = dict(reference or {})

    holder = {}                       # set once the evaluator exists

    def out(status, **kw):
        # any outcome other than a solve rewinds the twin to the caller's entry state,
        # so a rejected target never leaves the model at a probe point
        ev = holder.get("f")
        if ev is not None and status != "solved":
            ev.restore_entry()
        return DoseSolution(status=status, feasible=(status == "solved"), target_pd=target_pd,
                            ratio=ratio, tolerance_pd=tolerance_pd, reference=ref,
                            provenance=prov, warnings=warns, root_policy=root_policy, **kw)

    if ratio is None:
        return out("no_ratio", reason="no pA/tp ratio available (needs pA0 and tp0, or an explicit ratio)")
    if not (isinstance(ratio, (int, float)) and math.isfinite(ratio)) or ratio <= 0:
        return out("invalid_bounds", reason=f"ratio must be finite and > 0, got {ratio!r}")
    if not (isinstance(target_pd, (int, float)) and math.isfinite(target_pd)) or target_pd <= 0:
        return out("invalid_bounds", reason=f"target_pd must be finite and > 0, got {target_pd!r}")

    lo, hi = effective_dose_bounds(ratio, dose_bounds, pressure_bounds, pulse_time_bounds)
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return out("invalid_bounds", effective_dose_bounds=(lo, hi),
                   reason="dose bracket is unbounded — supply dose, pressure or pulse-time bounds")
    if lo <= 0 or hi <= 0 or lo >= hi:
        return out("invalid_bounds", effective_dose_bounds=(lo, hi),
                   reason=f"empty or non-positive dose interval [{lo:.6g}, {hi:.6g}] "
                          "(dose, pressure and pulse-time bounds conflict)")

    f = _Evaluator(model, ratio)
    holder["f"] = f
    try:
        pd_lo, pd_hi = f(lo), f(hi)
    except Exception as e:
        return out("model_error", effective_dose_bounds=(lo, hi), model_evaluations=f.n,
                   reason=f"model evaluation failed at a bracket end: {type(e).__name__}: {e}")

    common = dict(effective_dose_bounds=(lo, hi), achievable_pd=(pd_lo, pd_hi))

    span = abs(pd_hi - pd_lo)
    if span <= tolerance_pd:
        return out("saturated", model_evaluations=f.n, **common,
                   reason=f"PD is flat across the dose bracket ({pd_lo:.6g} .. {pd_hi:.6g} m); "
                          "the dose is not identifiable from this target")
    if target_pd < min(pd_lo, pd_hi) - tolerance_pd:
        return out("infeasible_low", model_evaluations=f.n, **common,
                   reason=f"target {target_pd:.6g} m is below the minimum achievable "
                          f"{min(pd_lo, pd_hi):.6g} m at dose {lo:.6g}")
    if target_pd > max(pd_lo, pd_hi) + tolerance_pd:
        return out("infeasible_high", model_evaluations=f.n, **common,
                   reason=f"target {target_pd:.6g} m exceeds the maximum achievable "
                          f"{max(pd_lo, pd_hi):.6g} m at dose {hi:.6g}")

    # Monotonicity is CHECKED, never assumed: a hidden fold would let a bracketed solver
    # return an arbitrary one of several roots without saying so.
    grid = np.geomspace(lo, hi, max(3, monotonicity_samples))
    try:
        vals = [pd_lo] + [f(d) for d in grid[1:-1]] + [pd_hi]
    except Exception as e:
        return out("model_error", model_evaluations=f.n, **common,
                   reason=f"model evaluation failed while sampling: {type(e).__name__}: {e}")
    res = [v - target_pd for v in vals]
    brackets = [(grid[i], grid[i + 1]) for i in range(len(res) - 1)
                if res[i] == 0 or res[i] * res[i + 1] < 0]
    dv = np.diff(vals)
    if not (np.all(dv >= -tolerance_pd) or np.all(dv <= tolerance_pd)):
        warns.append("PD is not monotonic in dose over the effective bracket")
        if len(brackets) > 1:
            if root_policy != "min_dose":
                return out("multiple_roots", model_evaluations=f.n, **common,
                           roots=[b[0] for b in brackets],
                           reason=f"{len(brackets)} sign-changing sub-brackets and no policy "
                                  f"for choosing among them (root_policy={root_policy!r})")
            brackets = brackets[:1]                       # documented policy: smallest dose
        elif not brackets:
            return out("non_monotonic", model_evaluations=f.n, **common,
                       reason="PD is non-monotonic and no sign change was found on the sample grid")
    if not brackets:
        brackets = [(lo, hi)]

    a, b = brackets[0]
    try:
        from scipy.optimize import brentq                 # already a repo dependency
        root, rr = brentq(lambda d: f(d) - target_pd, a, b, xtol=1e-12, rtol=1e-12,
                          maxiter=max_evaluations, full_output=True, disp=False)
        method, converged = "brentq", rr.converged
    except ImportError:                                   # bisection fallback, no new dependency
        method, converged = "bisection", False
        fa = f(a) - target_pd
        for _ in range(max_evaluations):
            root = 0.5 * (a + b)
            fr = f(root) - target_pd
            if abs(fr) <= tolerance_pd or (b - a) <= 1e-12 * max(1.0, root):
                converged = True
                break
            if fa * fr < 0:
                b = root
            else:
                a, fa = root, fr
    if not converged:
        return out("max_evaluations", model_evaluations=f.n, **common, dose=root,
                   reason=f"root solver did not converge in {max_evaluations} evaluations")

    achieved = f(root)
    if leave_model_at_solution:
        f.restore_to(root)          # contract: the twin is LEFT at the solved operating point
    else:
        f.restore_entry()
    residual = achieved - target_pd
    if abs(residual) > max(tolerance_pd, 1e-6 * target_pd):
        warns.append(f"residual {residual:.3g} m exceeds the PD tolerance")
    return out("solved", model_evaluations=f.n, **common, dose=root, achieved_pd=achieved,
               pA=float(np.sqrt(root * ratio)), pulse_time=float(np.sqrt(root / ratio)),
               residual=residual, method=method)


def achievable_pd_range(model, ratio, dose_bounds=None, pressure_bounds=None,
                        pulse_time_bounds=None):
    """(PD_min, PD_max, (D_lo, D_hi)) over the effective bracket — what the twin can
    actually reach at this ratio. Used to show a target against the model's range."""
    lo, hi = effective_dose_bounds(ratio, dose_bounds, pressure_bounds, pulse_time_bounds)
    f = _Evaluator(model, ratio)
    a, b = f(lo), f(hi)
    return min(a, b), max(a, b), (lo, hi)
