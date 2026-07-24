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

    @property
    def effective_dose(self):
        """Explicit alias for `dose` = pA · pulse_time [Pa·s].

        Named apart from the `D` inside channel_model.approx(), which is an internal
        transport coefficient in different units. The two must never be conflated in
        code, labels or report text, so the layer above always says effective_dose."""
        return self.dose

    def to_dict(self):
        d = asdict(self)
        d["effective_dose"] = self.dose
        return d


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


# =============================================================================
# feasible-region tracing and identifiability — derived from the ACTIVE model
# =============================================================================
# The functions below characterise the inverse problem WITHOUT assuming which
# operating combination is the invariant. `solve_pulse_for_pressure` inverts the
# real forward model one axis at a time; `trace_feasible_region` walks the true
# PD=target level set point by point and clips it to the operating bounds; and it
# reports, from the numbers it observed, whether the pressure/pulse split is
# structurally free (PD invariant along the locus) and how nearly the effective
# dose pA·t_p is conserved. Nothing here hardcodes pA·t_p = const — that claim, if
# it holds, is an OUTPUT (dose_spread), measured against the model.

_PA_ATTR, _TP_ATTR = "pA", "t_p"


def _pd_at(model, pA, tp):
    """PD50 at an explicit (pA, t_p), restoring the model's prior state afterwards."""
    saved = {a: getattr(model, a, None) for a in _STATE_ATTRS}
    try:
        model.pA, model.t_p = float(pA), float(tp)
        model.prepare()
        return float(model.penetration_depth())
    finally:
        for a, v in saved.items():
            if v is not None:
                setattr(model, a, v)


def solve_pulse_for_pressure(model, target_pd, pA, pulse_time_bounds,
                             tolerance_pd=1e-9, max_evaluations=200):
    """At a FIXED precursor pressure, solve for the pulse time that hits the target.

    This is the transpose of solve_target_dose: instead of moving both pA and t_p at
    a fixed ratio, it pins pA and moves t_p alone. It is what lets the region tracer
    walk the model's real level set (one point per pressure) rather than assume the
    level set is an iso-dose hyperbola. Returns (t_p, achieved_pd) or (None, reason)
    when the target is not reachable within the pulse-time bounds at this pressure —
    which is exactly how the locus gets clipped."""
    tlo, thi = pulse_time_bounds
    if not (tlo > 0 and thi > tlo):
        return None, f"invalid pulse-time bounds {pulse_time_bounds!r}"
    pd_lo, pd_hi = _pd_at(model, pA, tlo), _pd_at(model, pA, thi)
    # PD is monotone non-decreasing in pulse time (more exposure -> deeper); an
    # unreachable target at this pressure is reported, not forced.
    if target_pd < min(pd_lo, pd_hi) - tolerance_pd:
        return None, f"target below reach at pA={pA:g} (min {min(pd_lo, pd_hi):.3g} m at t_p={tlo:g})"
    if target_pd > max(pd_lo, pd_hi) + tolerance_pd:
        return None, f"target above reach at pA={pA:g} (max {max(pd_lo, pd_hi):.3g} m at t_p={thi:g})"
    try:
        from scipy.optimize import brentq
        tp = float(brentq(lambda t: _pd_at(model, pA, t) - target_pd, tlo, thi,
                          xtol=1e-14, rtol=1e-13, maxiter=max_evaluations))
    except ImportError:
        a, b = tlo, thi
        fa = _pd_at(model, pA, a) - target_pd
        tp = 0.5 * (a + b)
        for _ in range(max_evaluations):
            tp = 0.5 * (a + b)
            fr = _pd_at(model, pA, tp) - target_pd
            if abs(fr) <= tolerance_pd or (b - a) <= 1e-14 * max(1.0, tp):
                break
            if fa * fr < 0:
                b = tp
            else:
                a, fa = tp, fr
    return tp, _pd_at(model, pA, tp)


def trace_feasible_region(model_factory, target_pd, pressure_bounds, pulse_time_bounds,
                          n_samples=25, tolerance_pd=1e-9):
    """Walk the model's real PD=target level set across the pressure bounds, clipped
    by the pulse-time bounds. Returns a dict describing the FEASIBLE SOLUTION SPACE:

        points                (pA, t_p, achieved_pd, residual) on the locus, in bounds
        n_points, empty
        pressure_range/pulse_range   spans actually attained on the locus
        dose_values, dose_range, dose_spread_frac   pA·t_p along the locus and how
              nearly it is conserved — the *measured* degeneracy, never assumed
        free_coordinate_count       1 when the locus is a curve (a span of pressures
              all satisfy the target), 0 when it collapses to a point / is empty
        pd_max_abs_residual         worst |PD-target| over the accepted points
        split_structural            True when PD is invariant (residual ≤ tol) along
              a genuine span of pressures — i.e. the pressure/pulse split is
              structurally undetermined FOR THIS model, shown from the trace
        tolerance_pd

    model_factory() must return a FRESH forward model each call (the tracer mutates
    pA / t_p)."""
    plo, phi = pressure_bounds
    grid = np.geomspace(max(plo, 1e-12), phi, max(3, n_samples))
    model = model_factory()
    pts = []
    for pA in grid:
        tp, info = solve_pulse_for_pressure(model, target_pd, float(pA), pulse_time_bounds,
                                            tolerance_pd=tolerance_pd)
        if tp is None:
            continue                                   # clipped: target unreachable here
        pd = info
        if not math.isfinite(pd):
            continue
        pts.append({"pA": float(pA), "t_p": float(tp), "achieved_pd": float(pd),
                    "residual": float(pd - target_pd), "effective_dose": float(pA) * float(tp)})
    if not pts:
        return {"points": [], "n_points": 0, "empty": True,
                "pressure_range": None, "pulse_range": None,
                "dose_values": [], "dose_range": None, "dose_spread_frac": None,
                "free_coordinate_count": 0, "pd_max_abs_residual": None,
                "split_structural": False, "tolerance_pd": tolerance_pd,
                "reason": "no operating point in the given bounds satisfies the target"}
    pAs = [p["pA"] for p in pts]
    tps = [p["t_p"] for p in pts]
    doses = [p["effective_dose"] for p in pts]
    max_resid = max(abs(p["residual"]) for p in pts)
    d_lo, d_hi = min(doses), max(doses)
    dose_spread = (d_hi - d_lo) / (sum(doses) / len(doses)) if doses else None
    pressure_span = (max(pAs) > min(pAs) * (1 + 1e-6))
    free_dims = 1 if (len(pts) >= 2 and pressure_span) else 0
    # the split is structurally undetermined when the target is met (residual within
    # tolerance) across a real span of pressures — the model itself leaves it free
    split_structural = bool(free_dims == 1 and max_resid <= max(tolerance_pd, 1e-6 * target_pd))
    return {"points": pts, "n_points": len(pts), "empty": False,
            "pressure_range": (min(pAs), max(pAs)), "pulse_range": (min(tps), max(tps)),
            "dose_values": doses, "dose_range": (d_lo, d_hi), "dose_spread_frac": dose_spread,
            "free_coordinate_count": free_dims, "pd_max_abs_residual": max_resid,
            "split_structural": split_structural, "tolerance_pd": tolerance_pd}


# kinetic parameters of the channel twin: their scatter, if known, is the physically
# meaningful uncertainty on the required dose. Geometry/temperature also carry σ but
# describe the FEATURE and the process condition, not the chemistry.
_KINETIC_PARAMS = ("c", "K", "gpc")


def propagate_dose_uncertainty(model_factory, target_pd, ratio, provenance,
                               dose_bounds=None, pressure_bounds=None, pulse_time_bounds=None):
    """Propagate the KB parameter scatter that actually exists (provenance σ) into a
    band on the identified effective dose, by re-solving under one-at-a-time ±σ
    perturbations and combining in quadrature.

    HONEST WITHHOLDING is the point: if no consumed parameter carries a σ, the band is
    None and `withheld` is True. Separately, if the KINETIC parameters (c, K, gpc) —
    the ones that dominate PD — are model defaults without σ, `kinetic_uncertainty` is
    False and the caller must NOT claim a quantitative credibility, however tight the
    geometry/temperature band looks. This is evidence-based; it is not a ±x% sensitivity
    scenario (that lives in analyse_robustness and is labelled as such).

    Returns a dict: {effective_dose, dose_band, sigma_dose, contributions, dominant,
    kinetic_uncertainty, withheld, note}."""
    def solve(model):
        return solve_target_dose(model, target_pd, ratio, dose_bounds=dose_bounds,
                                 pressure_bounds=pressure_bounds,
                                 pulse_time_bounds=pulse_time_bounds,
                                 leave_model_at_solution=False)
    base = solve(model_factory())
    if not base.feasible:
        return {"effective_dose": None, "dose_band": None, "sigma_dose": None,
                "contributions": {}, "dominant": None, "kinetic_uncertainty": False,
                "withheld": True, "note": f"base solve not feasible ({base.status})"}
    d0 = base.effective_dose
    contribs = {}
    prov = provenance or {}
    for p, meta in prov.items():
        if (meta or {}).get("source") != "kb":
            continue
        sigma = (meta or {}).get("sigma")
        if not (isinstance(sigma, (int, float)) and sigma > 0):
            continue
        deltas = []
        for sign in (+1.0, -1.0):
            m = model_factory()
            if not hasattr(m, p):
                continue
            base_v = getattr(m, p)
            new_v = base_v + sign * sigma
            if new_v <= 0:                     # keep every perturbed parameter physical
                continue
            setattr(m, p, new_v)
            s = solve(m)
            if s.feasible:
                deltas.append(abs(s.effective_dose - d0))
        if deltas:
            contribs[p] = sum(deltas) / len(deltas)
    if not contribs:
        return {"effective_dose": d0, "dose_band": None, "sigma_dose": None,
                "contributions": {}, "dominant": None, "kinetic_uncertainty": False,
                "withheld": True,
                "note": "no consumed parameter carries a KB uncertainty (σ); "
                        "confidence on the required dose is withheld"}
    sigma_dose = math.sqrt(sum(v * v for v in contribs.values()))
    dominant = max(contribs, key=contribs.get)
    kinetic = any(p in contribs for p in _KINETIC_PARAMS)
    note = ("evidence band from KB parameter scatter"
            if kinetic else
            "band reflects geometry/temperature scatter only; the kinetic parameters "
            f"{[p for p in _KINETIC_PARAMS]} are model defaults without σ, so absolute "
            "target-hit credibility is withheld")
    return {"effective_dose": d0, "dose_band": (d0 - sigma_dose, d0 + sigma_dose),
            "sigma_dose": sigma_dose, "contributions": contribs, "dominant": dominant,
            "kinetic_uncertainty": kinetic, "withheld": not kinetic, "note": note}
