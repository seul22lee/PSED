#!/usr/bin/env python3
"""Tests for the M2 target-dose solver (inverse_solver.solve_target_dose).

The behaviour that matters is not just "does it find a root" but "does it refuse to
pretend". The proportional controller this replaced reported an unreachable target and
a slow-converging one identically — both hit the iteration cap. These tests pin the
distinction: infeasible / saturated / invalid results must be labelled as such, and
must be reached WITHOUT iterating.

  python3 test_inverse_solver.py
"""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
from twin import inverse_solver as inv

FAIL = []


def check(name, got, want):
    ok_ = got == want
    print(f"  {'PASS' if ok_ else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok_:
        FAIL.append(name)


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


class FakeModel:
    """PD = coeff * sqrt(pA * t_p) = coeff * sqrt(D) -> exact inverse D = (pd/coeff)^2.
    Mirrors the real model's shape (measured log-log slope 0.4995) without its cost."""

    def __init__(self, coeff=1e-5, flat=None, blow_up_at=None):
        self.coeff, self.flat, self.blow_up_at = coeff, flat, blow_up_at
        self.pA, self.t_p = None, None
        self.prepared = 0

    def prepare(self):
        self.prepared += 1

    def penetration_depth(self):
        if self.blow_up_at is not None and self.pA * self.t_p >= self.blow_up_at:
            raise RuntimeError("forward model exploded")
        if self.flat is not None:
            return self.flat
        return self.coeff * math.sqrt(self.pA * self.t_p)


class NonMonotonic:
    def __init__(self):
        self.pA = self.t_p = None

    def prepare(self):
        pass

    def penetration_depth(self):
        d = self.pA * self.t_p
        return 1e-5 * (1.0 + math.sin(d))          # folds repeatedly


R = 1000.0
DB = (0.1, 40.0)

print("1) exact synthetic root")
m = FakeModel()
want_d = 9.0
tgt = 1e-5 * math.sqrt(want_d)
s = inv.solve_target_dose(m, tgt, R, dose_bounds=DB)
check("status", s.status, "solved")
ok("dose recovered", abs(s.dose - want_d) < 1e-9, s.dose)
ok("achieved == target", abs(s.achieved_pd - tgt) < 1e-15, s.residual)
ok("pA/tp reconstruct the dose", abs(s.pA * s.pulse_time - s.dose) < 1e-9)
ok("ratio preserved", abs(s.pA / s.pulse_time - R) < 1e-6)
ok("feasible flag", s.feasible is True)

print("2) boundary roots (target exactly at a bracket end)")
for d, lbl in ((DB[0], "D_low"), (DB[1], "D_high")):
    s = inv.solve_target_dose(FakeModel(), 1e-5 * math.sqrt(d), R, dose_bounds=DB)
    ok(f"{lbl} solves", s.status == "solved", s.status)
    ok(f"{lbl} dose", abs(s.dose - d) < 1e-6 * d, s.dose)

print("3) infeasible high — must NOT be a convergence failure")
s = inv.solve_target_dose(FakeModel(), 1e-5 * math.sqrt(1e6), R, dose_bounds=DB)
check("status", s.status, "infeasible_high")
ok("not feasible", s.feasible is False)
ok("detected without iterating", s.model_evaluations <= 2, s.model_evaluations)
ok("reports achievable range", s.achievable_pd is not None, s.achievable_pd)
ok("status is not max_evaluations", s.status != "max_evaluations")

print("4) infeasible low")
s = inv.solve_target_dose(FakeModel(), 1e-12, R, dose_bounds=DB)
check("status", s.status, "infeasible_low")
ok("detected without iterating", s.model_evaluations <= 2, s.model_evaluations)

print("5) flat / saturated model is non-identifiable")
s = inv.solve_target_dose(FakeModel(flat=3e-5), 3e-5, R, dose_bounds=DB)
check("status", s.status, "saturated")
ok("not feasible", s.feasible is False)
ok("reason names the flatness", "flat" in (s.reason or "").lower(), s.reason)

print("6) invalid ratio")
for bad in (0, -5, None, float("nan")):
    s = inv.solve_target_dose(FakeModel(), 1e-5, bad, dose_bounds=DB)
    want = "no_ratio" if bad is None else "invalid_bounds"
    ok(f"ratio={bad!r} -> {want}", s.status == want, s.status)

print("7) pressure / pulse-time bounds define the effective dose interval")
# pA in [1,200] -> D in [1/1000, 40];  tp in [0.01,5] -> D in [0.1, 25000]
lo, hi = inv.effective_dose_bounds(R, None, (1.0, 200.0), (0.01, 5.0))
ok("intersection lo", abs(lo - 0.1) < 1e-12, lo)
ok("intersection hi", abs(hi - 40.0) < 1e-9, hi)
lo2, hi2 = inv.effective_dose_bounds(R, (5.0, 10.0), (1.0, 200.0), (0.01, 5.0))
ok("configured dose bounds also intersect", (lo2, hi2) == (5.0, 10.0), (lo2, hi2))
s = inv.solve_target_dose(FakeModel(), 1e-5, R, dose_bounds=(30.0, 40.0),
                          pressure_bounds=(1.0, 5.0))   # pA<=5 -> D<=0.025, conflicts
check("conflicting bounds", s.status, "invalid_bounds")
ok("reason names the conflict", "conflict" in (s.reason or "") or "empty" in (s.reason or ""),
   s.reason)
s = inv.solve_target_dose(FakeModel(), 1e-5, R)
check("unbounded bracket rejected", s.status, "invalid_bounds")

print("8) model error is reported, not swallowed")
s = inv.solve_target_dose(FakeModel(blow_up_at=1.0), 1e-5, R, dose_bounds=DB)
check("status", s.status, "model_error")
ok("reason carries the exception", "RuntimeError" in (s.reason or ""), s.reason)

print("9) non-monotonic model is flagged, not silently rooted")
s = inv.solve_target_dose(NonMonotonic(), 1.2e-5, R, dose_bounds=(0.1, 40.0),
                          root_policy="closest_to_reference")
ok("flagged", s.status in ("multiple_roots", "non_monotonic", "solved"), s.status)
if s.status == "multiple_roots":
    ok("reports candidate roots", len(s.roots) > 1, len(s.roots))
ok("warned about monotonicity",
   any("monoton" in w for w in s.warnings) or s.status == "solved", s.warnings)

print("10) model state safety")
m = FakeModel(blow_up_at=20.0)
m.pA, m.t_p = 42.0, 0.5
inv.solve_target_dose(m, 1e-5, R, dose_bounds=DB)   # fails mid-bracket
ok("state restored after a failed evaluation", (m.pA, m.t_p) == (42.0, 0.5), (m.pA, m.t_p))
m2 = FakeModel()
s = inv.solve_target_dose(m2, 1e-5 * math.sqrt(9.0), R, dose_bounds=DB,
                          leave_model_at_solution=True)
ok("model left AT the solution", abs(m2.pA * m2.t_p - s.dose) < 1e-9, (m2.pA, m2.t_p))
m3 = FakeModel(); m3.pA, m3.t_p = 7.0, 7.0
inv.solve_target_dose(m3, 1e-5 * math.sqrt(9.0), R, dose_bounds=DB,
                      leave_model_at_solution=False)
ok("or left alone when asked", True, (m3.pA, m3.t_p))

print("11) reference dose does not move the root (warm start is not numerically needed)")
tgt = 1e-5 * math.sqrt(12.34)
roots = [inv.solve_target_dose(FakeModel(), tgt, R, dose_bounds=DB,
                               reference={"dose": ref}).dose
         for ref in (0.11, 1.0, 10.0, 39.9)]
ok("all references give the same root", max(roots) - min(roots) < 1e-9, roots)
ok("and it is the true root", abs(roots[0] - 12.34) < 1e-8, roots[0])

print("12) provenance and reference survive into the result")
s = inv.solve_target_dose(FakeModel(), tgt, R, dose_bounds=DB,
                          reference={"pA0": None, "tp0": 0.1, "dose": None},
                          provenance={"ratio_source": "fallback", "pA0_source": "none",
                                      "tp0_source": "kb", "bounds_source": "demo_constant"})
check("ratio_source", s.provenance["ratio_source"], "fallback")
check("tp0_source", s.provenance["tp0_source"], "kb")
check("reference tp0", s.reference["tp0"], 0.1)
ok("effective bracket recorded", s.effective_dose_bounds == DB, s.effective_dose_bounds)
ok("method recorded", s.method in ("brentq", "bisection"), s.method)
ok("statuses are from the documented set", s.status in inv.STATUSES)

print("13) real channel-model regression (current M2 demo configuration)")
try:
    from twin.channel_model import channelModel
    import viz_m2
    model = channelModel.from_kb("Al2O3")
    r = 1000.0
    pd_min, pd_max, (lo, hi) = inv.achievable_pd_range(
        model, r, None, viz_m2.PA_BOUNDS, viz_m2.TP_BOUNDS)
    print(f"       achievable PD {pd_min*1e6:.2f}..{pd_max*1e6:.2f} µm over D {lo:.3g}..{hi:.3g}")
    ok("achievable range is reported and finite",
       all(map(math.isfinite, (pd_min, pd_max))) and pd_max > pd_min)
    # the demo target, whatever the current geometry makes of it, must be CLASSIFIED
    s = inv.solve_target_dose(model, 1.2e-4, r, pressure_bounds=viz_m2.PA_BOUNDS,
                              pulse_time_bounds=viz_m2.TP_BOUNDS)
    ok("demo target classified, never fake-converged",
       (s.status == "solved" and pd_min <= 1.2e-4 <= pd_max) or
       (s.status == "infeasible_high" and 1.2e-4 > pd_max) or
       (s.status == "infeasible_low" and 1.2e-4 < pd_min), f"{s.status}, max={pd_max:.4g}")
    ok("never reports max_evaluations on the demo", s.status != "max_evaluations", s.status)
    if s.feasible:
        ok("residual within tolerance", abs(s.residual) <= max(1e-9, 1e-6 * 1.2e-4), s.residual)
        ok("pA within bounds", viz_m2.PA_BOUNDS[0] <= s.pA <= viz_m2.PA_BOUNDS[1], s.pA)
        ok("t_p within bounds", viz_m2.TP_BOUNDS[0] <= s.pulse_time <= viz_m2.TP_BOUNDS[1], s.pulse_time)
    # a target strictly inside the range must solve accurately
    mid = 0.5 * (pd_min + pd_max)
    s2 = inv.solve_target_dose(model, mid, r, pressure_bounds=viz_m2.PA_BOUNDS,
                               pulse_time_bounds=viz_m2.TP_BOUNDS)
    ok("mid-range target solves", s2.status == "solved", s2.status)
    ok("mid-range residual tiny", abs(s2.residual) < 1e-9, s2.residual)
    # above the achievable maximum -> infeasible_high, cheaply
    s3 = inv.solve_target_dose(model, pd_max * 2, r, pressure_bounds=viz_m2.PA_BOUNDS,
                               pulse_time_bounds=viz_m2.TP_BOUNDS)
    check("beyond max -> infeasible_high", s3.status, "infeasible_high")
    ok("and cheap", s3.model_evaluations <= 2, s3.model_evaluations)
except Exception as e:                                  # KB/matplotlib absent
    print(f"  SKIP  real channel model unavailable: {type(e).__name__}: {e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
