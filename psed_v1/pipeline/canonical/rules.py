"""
canonical/rules.py — the centralized transformation rule registry.

Rules are DECLARED in the ontology (quantity_relations.transformation_rules) and
BOUND to code here by `implementation_id`. There is no scattered if/elif
transformation logic anywhere else in the canonical layer.

validate_registry() fails when:
  * an ontology rule has no implementation,
  * an implementation has no ontology declaration,
  * a rule is missing input units / output unit / required context,
  * a rule claims invertibility but its implementation exposes no inverse.
"""
from __future__ import annotations

import math

from . import units as U
from .schema import (RULE_DECLS, NORMALIZATION_DEFINITIONS, COMPARISON_GROUPS,
                     Status, canonical_unit_for_group)

TOLERANCE = 1e-9


class TransformationError(Exception):
    """Rule applied but produced an invalid result (status -> invalid)."""


class MissingContext(Exception):
    def __init__(self, quantity):
        Exception.__init__(self, "missing required context: %s" % quantity)
        self.quantity = quantity


# =========================================================================
# implementations. Each is (forward, inverse|None, validate).
# `ctx` maps quantity id -> {"value": float, "unit": str, ...} (a ContextBinding).
# =========================================================================
class Implementation(object):
    def __init__(self, impl_id, forward, inverse=None, validate=None, doc=""):
        self.id = impl_id
        self.forward = forward
        self.inverse = inverse
        self.validate = validate or (lambda **kw: None)
        self.doc = doc

    @property
    def has_inverse(self):
        return self.inverse is not None


IMPLEMENTATIONS = {}


def _impl(impl_id, inverse=None, validate=None, doc=""):
    def deco(fn):
        IMPLEMENTATIONS[impl_id] = Implementation(impl_id, fn, inverse, validate, doc)
        return fn
    return deco


def _ctx_value(ctx, quantity):
    b = (ctx or {}).get(quantity)
    if b is None or b.get("value") is None:
        raise MissingContext(quantity)
    return float(b["value"]), b.get("unit")


# --- identity -------------------------------------------------------------
def _identity(values, **kw):
    return list(values)


IMPLEMENTATIONS["identity"] = Implementation(
    "identity", _identity, _identity, None,
    "source already IS the canonical quantity+unit; values copied unchanged")


# --- pure unit conversion -------------------------------------------------
def _unit_convert(values, from_unit=None, to_unit=None,
                  allow_empty_as_dimensionless=False, **kw):
    return U.convert_series(values, from_unit, to_unit, allow_empty_as_dimensionless)


def _unit_convert_inv(values, from_unit=None, to_unit=None,
                      allow_empty_as_dimensionless=False, **kw):
    return U.convert_series(values, to_unit, from_unit, allow_empty_as_dimensionless)


def _unit_validate(from_unit=None, to_unit=None, allow_empty_as_dimensionless=False, **kw):
    fu = U.parse(from_unit, allow_empty_as_dimensionless)
    tu = U.parse(to_unit, allow_empty_as_dimensionless)
    if fu.dimension != tu.dimension:
        raise TransformationError(
            "dimension mismatch %s -> %s" % (fu.symbol, tu.symbol))


IMPLEMENTATIONS["unit_convert"] = Implementation(
    "unit_convert", _unit_convert, _unit_convert_inv, _unit_validate,
    "dimension-checked scalar unit conversion (affine-aware)")


# --- denormalize: value * denominator ------------------------------------
def _denormalize(values, ctx=None, denominator_quantity=None, to_unit=None, **kw):
    dv, du = _ctx_value(ctx, denominator_quantity)
    if dv == 0:
        raise TransformationError("denominator is zero (%s)" % denominator_quantity)
    U.require_ratio_safe(du, "denominator")
    dv_target = U.convert(dv, du, to_unit)
    return [None if v is None else float(v) * dv_target for v in values]


def _denormalize_inv(values, ctx=None, denominator_quantity=None, to_unit=None, **kw):
    dv, du = _ctx_value(ctx, denominator_quantity)
    if dv == 0:
        raise TransformationError("denominator is zero (%s)" % denominator_quantity)
    dv_target = U.convert(dv, du, to_unit)
    return [None if v is None else float(v) / dv_target for v in values]


def _denormalize_validate(ctx=None, denominator_quantity=None, to_unit=None,
                          valid_domain=None, values=None, **kw):
    dv, du = _ctx_value(ctx, denominator_quantity)
    if dv == 0:
        raise TransformationError("denominator is zero (%s)" % denominator_quantity)
    if not U.is_ratio_safe(du):
        raise TransformationError("offset unit %r used as a denominator" % du)


IMPLEMENTATIONS["denormalize_by_denominator"] = Implementation(
    "denormalize_by_denominator", _denormalize, _denormalize_inv, _denormalize_validate,
    "dimensional value = normalized value x explicitly resolved denominator")


# --- normalize: value / denominator --------------------------------------
def _normalize(values, ctx=None, denominator_quantity=None, from_unit=None, **kw):
    dv, du = _ctx_value(ctx, denominator_quantity)
    if dv == 0:
        raise TransformationError("denominator is zero (%s)" % denominator_quantity)
    U.require_ratio_safe(du, "denominator")
    U.require_ratio_safe(from_unit, "numerator")
    dv_src = U.convert(dv, du, from_unit)
    return [None if v is None else float(v) / dv_src for v in values]


def _normalize_inv(values, ctx=None, denominator_quantity=None, from_unit=None, **kw):
    dv, du = _ctx_value(ctx, denominator_quantity)
    dv_src = U.convert(dv, du, from_unit)
    return [None if v is None else float(v) * dv_src for v in values]


IMPLEMENTATIONS["normalize_by_denominator"] = Implementation(
    "normalize_by_denominator", _normalize, _normalize_inv, _denormalize_validate,
    "normalized value = dimensional value / explicitly resolved denominator")


# --- normalize by the curve's own maximum (self-contained) ----------------
def _normalize_by_max(values, **kw):
    nums = [float(v) for v in values if v is not None]
    if not nums:
        raise TransformationError("no numeric values to normalize")
    mx = max(nums)
    if mx == 0:
        raise TransformationError("profile maximum is zero")
    return [None if v is None else float(v) / mx for v in values]


IMPLEMENTATIONS["normalize_by_profile_max"] = Implementation(
    "normalize_by_profile_max", _normalize_by_max, None, None,
    "t(x)/t_max where t_max is the maximum of THIS curve; not invertible")


# --- ratio of two independently resolved values --------------------------
def _ratio(values, ctx=None, denominator_quantity=None, from_unit=None, **kw):
    return _normalize(values, ctx=ctx, denominator_quantity=denominator_quantity,
                      from_unit=from_unit, **kw)


def _ratio_inv(values, ctx=None, denominator_quantity=None, from_unit=None, **kw):
    return _normalize_inv(values, ctx=ctx, denominator_quantity=denominator_quantity,
                          from_unit=from_unit, **kw)


IMPLEMENTATIONS["ratio_of_two_values"] = Implementation(
    "ratio_of_two_values", _ratio, _ratio_inv, _denormalize_validate,
    "ratio of two separately measured values (step coverage, local/planar GPC)")


# --- cycle-based: thickness <-> GPC --------------------------------------
def _effective_cycles(ctx):
    """N_eff = N - N0 when nucleation_delay is available, else N. Raises when the
    effective count is not strictly positive."""
    n, nu = _ctx_value(ctx, "cycle_number")
    n = U.convert(n, nu or "cycle", "cycle") if nu else n
    n0 = 0.0
    used_delay = False
    b = (ctx or {}).get("nucleation_delay")
    if b is not None and b.get("value") is not None:
        n0 = float(b["value"])
        used_delay = True
    eff = n - n0
    if eff <= 0:
        raise TransformationError(
            "effective cycle count is not positive (N=%s, N0=%s)" % (n, n0))
    return eff, used_delay


def _thickness_from_gpc(values, ctx=None, **kw):
    eff, _ = _effective_cycles(ctx)
    return [None if v is None else float(v) * eff for v in values]


def _gpc_from_thickness(values, ctx=None, **kw):
    eff, _ = _effective_cycles(ctx)
    return [None if v is None else float(v) / eff for v in values]


def _cycle_validate(ctx=None, **kw):
    _effective_cycles(ctx)


IMPLEMENTATIONS["thickness_from_gpc"] = Implementation(
    "thickness_from_gpc", _thickness_from_gpc, _gpc_from_thickness, _cycle_validate,
    "d = GPC x (N - N0); steady linear growth assumed and recorded")

IMPLEMENTATIONS["gpc_from_thickness"] = Implementation(
    "gpc_from_thickness", _gpc_from_thickness, _thickness_from_gpc, _cycle_validate,
    "GPC = d / (N - N0); only under an explicit steady-growth assumption")


# --- exposure = P * t -----------------------------------------------------
def _exposure(values, ctx=None, from_unit=None, **kw):
    t, tu = _ctx_value(ctx, "pulse_time")
    t_s = U.convert(t, tu or "s", "s")
    if t_s <= 0:
        raise TransformationError("pulse_time must be positive")
    return [None if v is None else U.convert(float(v), from_unit, "Pa") * t_s
            for v in values]


IMPLEMENTATIONS["exposure_from_pressure_time"] = Implementation(
    "exposure_from_pressure_time", _exposure, None, None,
    "E = P_partial x t_pulse; NOT independent evidence of either operand")


# --- axis semantic resolution (bookkeeping only, no numeric change) -------
IMPLEMENTATIONS["axis_semantics"] = Implementation(
    "axis_semantics", _identity, None, None,
    "records the evidence-backed assignment of an axis to a comparison group")


# =========================================================================
# Rule objects
# =========================================================================
class Rule(object):
    def __init__(self, decl):
        self.decl = decl
        self.id = decl["id"]
        self.version = decl["version"]
        self.type = decl["type"]
        self.implementation_id = decl["implementation_id"]
        self.impl = IMPLEMENTATIONS[decl["implementation_id"]]
        self.source_quantity_kind = decl.get("source_quantity_kind")
        self.target_quantity_kind = decl.get("target_quantity_kind")
        self.input_units = decl.get("input_units")
        self.output_unit = decl.get("output_unit")
        self.required_context = list(decl.get("required_context") or [])
        self.optional_context = list(decl.get("optional_context") or [])
        self.invertible = bool(decl.get("invertible"))
        self.self_contained = bool(decl.get("self_contained"))
        self.valid_domain = decl.get("valid_domain")
        self.assumptions = list(decl.get("assumptions") or [])
        self.confidence_policy = decl.get("confidence_policy")
        self.applicability = decl.get("applicability") or {}
        self.dimension = decl.get("dimension")
        self.normalization_definition = decl.get("normalization_definition")

    @property
    def normalization(self):
        return NORMALIZATION_DEFINITIONS.get(self.normalization_definition)

    @property
    def comparison_group(self):
        nd = self.normalization
        return nd.get("comparison_group") if nd else None

    @property
    def denominator_quantity(self):
        """The key the CONTEXT RESOLVER must look up for the denominator.

        This is not always the denominator's quantity kind. For a reference-value
        normalization the denominator kind is `film_thickness` (a thickness at a
        reference location), but what the resolver has to find is the declared
        context quantity `reference_thickness`. `required_context` is the
        authority; the normalization's `denominator` is the fallback."""
        if self.required_context:
            return self.required_context[0]
        nd = self.normalization
        return nd.get("denominator") if nd else None

    def missing_context(self, ctx):
        return [q for q in self.required_context
                if not ((ctx or {}).get(q) or {}).get("value") is not None]

    def apply(self, values, ctx=None, from_unit=None, to_unit=None,
              allow_empty_as_dimensionless=False):
        """Run the forward transformation. Raises MissingContext /
        TransformationError / units errors; never returns a partial result."""
        kw = dict(values=values, ctx=ctx, from_unit=from_unit,
                  to_unit=to_unit or self.output_unit,
                  denominator_quantity=self.denominator_quantity,
                  valid_domain=self.valid_domain,
                  allow_empty_as_dimensionless=allow_empty_as_dimensionless)
        if self.impl.validate:
            self.impl.validate(**kw)
        return self.impl.forward(values, **{k: v for k, v in kw.items() if k != "values"})

    def invert(self, values, ctx=None, from_unit=None, to_unit=None,
               allow_empty_as_dimensionless=False):
        if not self.impl.has_inverse:
            raise TransformationError("rule %s has no inverse" % self.id)
        kw = dict(ctx=ctx, from_unit=from_unit, to_unit=to_unit or self.output_unit,
                  denominator_quantity=self.denominator_quantity,
                  valid_domain=self.valid_domain,
                  allow_empty_as_dimensionless=allow_empty_as_dimensionless)
        return self.impl.inverse(values, **kw)

    def check_domain(self, values):
        """Return a list of domain violations. Values are FLAGGED, never clamped."""
        vd = self.valid_domain or {}
        lo, hi = vd.get("min"), vd.get("max")
        bad = []
        for i, v in enumerate(values):
            if v is None:
                continue
            if lo is not None and v < lo - 1e-9:
                bad.append({"index": i, "value": v, "bound": "min", "limit": lo})
            if hi is not None and v > hi + 1e-9:
                bad.append({"index": i, "value": v, "bound": "max", "limit": hi})
        return bad

    def roundtrip_error(self, values, ctx=None, from_unit=None, to_unit=None,
                        allow_empty_as_dimensionless=False):
        """Max relative error of inverse(forward(x)) vs x. None when not invertible."""
        if not (self.invertible and self.impl.has_inverse):
            return None
        fwd = self.apply(values, ctx=ctx, from_unit=from_unit, to_unit=to_unit,
                         allow_empty_as_dimensionless=allow_empty_as_dimensionless)
        back = self.invert(fwd, ctx=ctx, from_unit=from_unit, to_unit=to_unit,
                           allow_empty_as_dimensionless=allow_empty_as_dimensionless)
        err = 0.0
        for a, b in zip(values, back):
            if a is None or b is None:
                continue
            denom = max(abs(float(a)), 1e-12)
            err = max(err, abs(float(a) - float(b)) / denom)
        return err

    def __repr__(self):
        return "Rule(%s v%s, %s)" % (self.id, self.version, self.type)


REGISTRY = {rid: Rule(decl) for rid, decl in RULE_DECLS.items()}


def get(rule_id):
    return REGISTRY[rule_id]


def rules_of_type(ttype):
    return [r for r in REGISTRY.values() if r.type == ttype]


def unit_conversion_rule_for(unit_symbol, allow_empty_as_dimensionless=False):
    """Pick the declared unit-conversion rule whose `dimension` matches the unit."""
    u = U.try_parse(unit_symbol, allow_empty_as_dimensionless)
    if u is None:
        return None
    dname = U.DIM_NAME.get(u.dimension)
    for r in REGISTRY.values():
        if r.type in ("unit_conversion", "scale_conversion") and r.dimension == dname:
            return r
    return None


def denormalization_rule_for(normalization_definition_id):
    for r in REGISTRY.values():
        if (r.normalization_definition == normalization_definition_id
                and r.type in ("geometry_based_conversion", "denormalization",
                               "reference_value_normalization")
                and r.implementation_id == "denormalize_by_denominator"):
            return r
    return None


# =========================================================================
# registry validation (build gate)
# =========================================================================
def validate_registry():
    """Returns a list of error strings; empty means the registry is consistent."""
    errors = []
    declared_impls = set()
    for rid, decl in RULE_DECLS.items():
        impl_id = decl.get("implementation_id")
        declared_impls.add(impl_id)
        if impl_id not in IMPLEMENTATIONS:
            errors.append("rule %s declares implementation_id %r with no implementation"
                          % (rid, impl_id))
            continue
        if not decl.get("input_units"):
            errors.append("rule %s: missing input_units" % rid)
        if not decl.get("output_unit"):
            errors.append("rule %s: missing output_unit" % rid)
        if not decl.get("version"):
            errors.append("rule %s: missing version" % rid)
        impl = IMPLEMENTATIONS[impl_id]
        if decl.get("invertible") and not impl.has_inverse:
            errors.append("rule %s claims invertible but implementation %r has no inverse"
                          % (rid, impl_id))
        nd = decl.get("normalization_definition")
        if nd and nd not in NORMALIZATION_DEFINITIONS:
            errors.append("rule %s: unknown normalization_definition %r" % (rid, nd))
        if nd:
            grp = NORMALIZATION_DEFINITIONS[nd].get("comparison_group")
            if grp and grp not in COMPARISON_GROUPS:
                errors.append("rule %s -> normalization %s: unknown comparison_group %r"
                              % (rid, nd, grp))
        # every rule needing context must name it (unless self-contained)
        tspec_needs = decl.get("type") in ("normalization", "denormalization",
                                           "geometry_based_conversion",
                                           "cycle_based_conversion",
                                           "reference_value_normalization",
                                           "algebraic_derivation")
        if tspec_needs and not decl.get("required_context") and not decl.get("self_contained"):
            errors.append("rule %s: type %s requires context but declares none"
                          % (rid, decl.get("type")))
    for impl_id in IMPLEMENTATIONS:
        if impl_id not in declared_impls:
            errors.append("implementation %r has no ontology rule declaration" % impl_id)
    # comparison groups must have a resolvable canonical unit
    for gid in COMPARISON_GROUPS:
        cu = canonical_unit_for_group(gid)
        if U.try_parse(cu, allow_empty_as_dimensionless=True) is None:
            errors.append("comparison_group %s: canonical_unit %r is not a known unit"
                          % (gid, cu))
    return errors
