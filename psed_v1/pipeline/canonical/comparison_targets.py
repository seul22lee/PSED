"""Ontology-resolved comparison targets: the ONE place representation identity lives.

A comparison target is what two curves must share before they may be drawn on one
axis. Its identity comes from the ontology and nowhere else:

    ComparisonGroup            the declared scientific target (canonical quantity,
                               normalization definition, canonical unit, axis role)
    QuantityKind               the fallback identity for a resolved quantity the
                               ontology has not (yet) grouped
    NormalizationDefinition    what a ratio is a ratio OF -- part of the identity,
                               so x/H and x/L can never meet
    canonical units            unit spelling is folded through the unit registry, so
                               µm/um/μm are one unit and "1"/"-"/"" are one
                               dimensionless marker, while nm vs µm remain a true
                               conversion that needs an explicit route

Source labels, source unit spellings and source quantity words NEVER participate in
target identity: a source representation is provenance and a route's starting point,
not a second scientific identity. An axis that cannot be resolved to an ontology
target stays source-native and unresolved -- it can be displayed, and it can never
be overlaid, because nothing established what it means.

Reachability between targets is the formal ontology TransformationRule registry
(`pipeline.canonical.rules`), which supersedes the informal `transforms` list; the
compatibility view at the bottom lets older comparability code read the same
authority in the shape it grew up with.
"""
import json
import re as _re
from pathlib import Path

from pipeline.canonical import axis_semantics as AX
from pipeline.canonical import rules as RULES
from pipeline.canonical import units as U

_ONTO = json.loads((Path(__file__).resolve().parents[2] / "ontology"
                    / "ald_ontology.json").read_text())
_QR = _ONTO["quantity_relations"]
GROUPS = _QR["comparison_groups"]
NORMALIZATIONS = {n["id"]: n for n in _QR["normalization_definitions"]}
QUANTITY_KINDS = {q["id"]: q for q in _ONTO["quantity_kinds"]}

#: quantities that are RATIOS BY DEFINITION: every comparison group they appear in
#: carries a normalization definition, so without a resolved basis they identify no
#: target at all. Derived from the ontology, never listed by hand.
_RATIO_ONLY_QUANTITIES = frozenset(
    q for q in {g["canonical_quantity"] for g in GROUPS.values()}
    if all(g.get("normalization_definition")
           for g in GROUPS.values() if g["canonical_quantity"] == q))

#: how a target was identified
TARGET_COMPARISON_GROUP = "COMPARISON_GROUP"
TARGET_QUANTITY_KIND = "QUANTITY_KIND"

#: QuantityKinds the ontology EXPLICITLY authorizes as direct comparison targets
#: when no ComparisonGroup covers them. The comparison_policy block names the
#: axis_role declaration as the authorization; nothing outside that declaration
#: ever becomes a target.
_QK_POLICY = (_QR.get("comparison_policy") or {}).get(
    "quantity_kind_direct_comparison")
_QK_AUTHORIZED = (frozenset((_QR.get("axis_role") or {}).get("coordinate") or [])
                  | frozenset((_QR.get("axis_role") or {}).get("output") or [])
                  if _QK_POLICY == "declared_axis_roles_only" else frozenset())


def _alias_root(gid, _seen=None):
    """Follow a group's DECLARED alias_of chain to its canonical group id.

    Aliasing between ComparisonGroups exists only where the ontology states it;
    two groups that merely share canonical quantity, unit and normalization are
    two distinct scientific identities until a declaration says otherwise."""
    seen = _seen or set()
    while gid in GROUPS and GROUPS[gid].get("alias_of") and gid not in seen:
        seen.add(gid)
        gid = GROUPS[gid]["alias_of"]
    return gid


def unit_identity(unit, allow_empty_as_dimensionless=False):
    """The registry identity of a unit spelling, or None when it does not parse.

    Two spellings are ONE unit exactly when the registry gives them the same
    dimension, factor and offset -- µm, um and μm collapse; nm stays a different
    unit of the same dimension (a conversion, not an alias).
    """
    u = U.try_parse(unit, allow_empty_as_dimensionless)
    if u is None:
        return None
    return (U.DIM_NAME.get(u.dimension, u.dimension), round(u.factor, 18), u.offset)


def canonical_spelling(unit):
    """The registry's display symbol for a unit identity, or None.

    One identity, one spelling: 'deg' and '°' both come back as 'deg', every
    dimensionless marker as '1'. This is what a target may carry as its unit --
    a raw source spelling never is.
    """
    u = U.try_parse(unit, allow_empty_as_dimensionless=True)
    return u.symbol if u is not None else None


def same_unit(a, b, allow_empty_as_dimensionless=True):
    ia = unit_identity(a, allow_empty_as_dimensionless)
    ib = unit_identity(b, allow_empty_as_dimensionless)
    return ia is not None and ia == ib


def canonical_unit_for(quantity, group_id=None):
    """The ontology's canonical unit for a target, or None when it declares none."""
    if group_id and group_id in GROUPS:
        return GROUPS[group_id].get("canonical_unit")
    unit, _basis = AX.ontology_axis_unit(quantity)
    return unit


def _norm_id(normalization):
    n = str(normalization or "").strip()
    return n if n in NORMALIZATIONS else (n or None)


def group_for(quantity, normalization=None):
    """The ontology ComparisonGroup id for a resolved axis meaning, or None.

    Identity is (canonical quantity, normalization definition). Groups collapse
    ONLY through a declared `alias_of` relation; when several groups match one
    meaning without such a declaration, the meaning is ambiguous in the ontology
    itself and None is the honest answer -- no lexicographic or other guess.
    """
    norm = _norm_id(normalization)
    hits = sorted(gid for gid, g in GROUPS.items()
                  if g.get("canonical_quantity") == quantity
                  and (g.get("normalization_definition") or None) == norm)
    roots = {_alias_root(gid) for gid in hits}
    return roots.pop() if len(roots) == 1 else None


def resolve_target(quantity, normalization=None, axis=None, unit=None):
    """The ontology-resolved comparison target of an axis meaning, or None.

    None is a STATEMENT: the meaning is not established well enough to share an
    axis. That happens when the quantity is not an ontology QuantityKind, when a
    ratio-by-definition quantity has no resolved normalization basis, or when a
    declared normalization id is unknown to the ontology. No pseudo-target is ever
    invented from source strings.
    """
    q = str(quantity or "").strip()
    if not q or q not in QUANTITY_KINDS:
        return None
    norm = str(normalization or "").strip() or None
    if norm and norm not in NORMALIZATIONS:
        return None
    if norm is None and q in _RATIO_ONLY_QUANTITIES:
        return None                       # a ratio to an unknown reference
    gid = group_for(q, norm)
    if gid:
        g = GROUPS[gid]
        aliases = sorted(g2 for g2, d in GROUPS.items()
                         if g2 != gid and _alias_root(g2) == gid)
        cu = g.get("canonical_unit") or canonical_unit_for(q)
        tid = "%s|group:%s" % (axis or "?", gid)
        kind = TARGET_COMPARISON_GROUP
    else:
        if q not in _QK_AUTHORIZED:
            # no ComparisonGroup covers this meaning and the ontology's
            # comparison_policy does not authorize the QuantityKind directly:
            # the axis stays source-native until the ontology says otherwise
            return None
        aliases = []
        cu = canonical_unit_for(q)
        if cu is None:
            # no ontology canonical unit for this quantity's dimension: the unit
            # identity comes from the registry's reading of the axis' own unit --
            # alias-folded, never the raw spelling. No parseable unit, no target.
            ui = unit_identity(unit, allow_empty_as_dimensionless=True)
            if ui is None:
                return None
            cu = canonical_spelling(unit)
            tid = "%s|qk:%s|%s|%s:%s" % (axis or "?", q, norm or "",
                                         ui[0], ("%g" % ui[1]))
        else:
            tid = "%s|qk:%s|%s|%s" % (axis or "?", q, norm or "", cu)
        kind = TARGET_QUANTITY_KIND
    nd = NORMALIZATIONS.get(norm) if norm else None
    return {
        "target_id": tid,
        "target_kind": kind,
        "comparison_group": gid,
        "group_aliases": aliases,
        "quantity": q,
        "normalization": norm,
        "normalization_definition": ({"id": nd["id"], "formula": nd.get("formula"),
                                      "denominator": nd.get("denominator"),
                                      "reference_location": nd.get("reference_location")}
                                     if nd else None),
        "canonical_unit": cu,
        "dimension": (GROUPS[gid].get("dimension") if gid else
                      (unit_identity(cu, True) or (None,))[0]),
        "axis_role": GROUPS[gid].get("axis_role") if gid else None,
        "axis": axis,
        "display_label": display_label(q, norm, cu),
    }


# ------------------------------------------------------------------ display labels
def _human(quantity):
    words = str(quantity or "").replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _ratio_text(nd):
    """The ratio notation of a normalization, from its own declared formula.

    Only the free variable the LHS itself declares is dropped from the RHS --
    "t_norm(x) = t(x) / t(0)" reads as t/t(0): the (x) is evaluation at the
    coordinate, the (0) is the reference point and stays.
    """
    f = str(nd.get("formula") or "")
    if "=" in f:
        lhs, rhs = f.split("=", 1)
        m = _re.search(r"\((\w{1,3})\)", lhs)
        if m:
            rhs = rhs.replace("(%s)" % m.group(1), "")
        return _re.sub(r"\s+", "", rhs)
    return str(nd.get("id") or "").replace("_over_", "/")


def unit_display(unit):
    """The display form of a canonical unit; dimensionless prints as an en dash."""
    if unit is None:
        return "?"
    if same_unit(unit, "1", allow_empty_as_dimensionless=True):
        return "–"
    return str(unit)


def display_label(quantity, normalization=None, unit=None):
    """Deterministic ontology-derived label. Never a source string, never
    dependent on which ResultSeries was seen first.

        plain target       "<Quantity kind> (<canonical unit>)"
        normalized target  "<Quantity kind> <ratio from the declared formula> (–)"
    """
    nd = NORMALIZATIONS.get(str(normalization or ""))
    if nd:
        return "%s %s (%s)" % (_human(quantity), _ratio_text(nd), unit_display(unit or "1"))
    return "%s (%s)" % (_human(quantity), unit_display(unit))


# ------------------------------------------------- formal-rule reachability graph
#: rule types that relate two QUANTITIES (identity/unit/axis bookkeeping rules do not)
_QUANTITY_RULE_TYPES = frozenset(
    r.type for r in RULES.REGISTRY.values()
    if r.source_quantity_kind and r.target_quantity_kind)


def quantity_rules():
    """Every formal rule that maps one quantity kind to another."""
    return [r for r in RULES.REGISTRY.values()
            if r.source_quantity_kind and r.target_quantity_kind]


def rules_from(quantity, normalization=None):
    """Formal rules applicable FORWARD from a resolved axis meaning.

    A rule that produces a normalized quantity always applies from the plain one;
    a rule CONSUMING a normalized quantity applies only when the axis' resolved
    basis IS the rule's declared normalization -- x/L is never fed to an x/H rule.
    """
    out = []
    for r in quantity_rules():
        if r.source_quantity_kind != quantity:
            continue
        if quantity in _RATIO_ONLY_QUANTITIES:
            if not r.normalization_definition or \
                    r.normalization_definition != (normalization or None):
                continue
        out.append(r)
    return sorted(out, key=lambda r: r.id)


def invertible_rules_to(quantity, normalization=None):
    """Formal invertible rules whose OUTPUT is this axis meaning (reverse routes)."""
    out = []
    for r in quantity_rules():
        if r.target_quantity_kind != quantity or not r.invertible:
            continue
        if quantity in _RATIO_ONLY_QUANTITIES:
            if not r.normalization_definition or \
                    r.normalization_definition != (normalization or None):
                continue
        out.append(r)
    return sorted(out, key=lambda r: r.id)


def rule_target(rule, direction="forward"):
    """The comparison target a rule lands on, in the given direction."""
    if direction == "forward":
        q = rule.target_quantity_kind
        norm = rule.normalization_definition if rule.type in (
            "normalization", "reference_value_normalization") and \
            q in _RATIO_ONLY_QUANTITIES else None
        # a normalization rule's declared definition IS the produced basis
        if rule.normalization_definition and q in _RATIO_ONLY_QUANTITIES:
            norm = rule.normalization_definition
        return q, norm
    q = rule.source_quantity_kind
    norm = rule.normalization_definition if q in _RATIO_ONLY_QUANTITIES else None
    return q, norm


def rule_between(qa, qb):
    """Any formal rule relating two quantities, either direction, else None."""
    for r in quantity_rules():
        if r.source_quantity_kind == qa and r.target_quantity_kind == qb:
            return r, "forward"
        if r.source_quantity_kind == qb and r.target_quantity_kind == qa \
                and r.invertible:
            return r, "reverse"
    return None, None


# ------------------------------------------- profile-derivable reference contexts
def profile_reference(reference_location, xs, ys):
    """(value, evidence) for a normalization reference the PROFILE ITSELF defines.

    Driven by the ontology's `reference_location` field, for any quantity:

        entrance          the observation at coordinate 0 -- sampled exactly or
                          interpolated between the bracketing observations; a
                          profile that never reaches the entrance is NOT
                          extrapolated to it
        profile_maximum   the maximum of the profile's own values

    Locations naming ANOTHER specimen or position (planar_reference, top) are not
    derivable from one profile and return None.
    """
    if reference_location == "profile_maximum":
        vals = [v for v in (ys or []) if v is not None]
        if not vals:
            return None, None
        return max(vals), "maximum of this profile's own %d values" % len(vals)
    if reference_location != "entrance":
        return None, None
    pairs = sorted(((x, y) for x, y in zip(xs or [], ys or [])
                    if x is not None and y is not None), key=lambda p: p[0])
    if len(pairs) < 2:
        return None, None
    for x, y in pairs:
        if x == 0.0:
            return y, "the profile samples the entrance (coordinate 0) directly"
    lo = [p for p in pairs if p[0] < 0.0]
    hi = [p for p in pairs if p[0] > 0.0]
    if not lo or not hi or hi[0][0] == lo[-1][0]:
        return None, None
    (x0, y0), (x1, y1) = lo[-1], hi[0]
    y = y0 + (y1 - y0) * (0.0 - x0) / (x1 - x0)
    return y, ("the entrance is bracketed by observations at %g and %g; the "
               "reference is interpolated between them" % (x0, x1))


# --------------------------------------------- compatibility view for older code
#: op each implementation applies, for consumers that still think in divide/multiply
_IMPL_OP = {"normalize_by_denominator": "divide",
            "denormalize_by_denominator": "multiply",
            "normalize_by_profile_max": "divide",
            "gpc_from_thickness": "divide",
            "thickness_from_gpc": "multiply",
            "ratio_of_two_values": "divide",
            "exposure_from_pressure_time": "multiply"}


def informal_transform_view():
    """The formal registry rendered in the legacy `transforms` shape.

    One authority: consumers that used the ontology's informal `transforms` list
    read this instead, so nothing can become transformable merely because a legacy
    list mentioned it. A legacy transform with no formal declaration is an ontology
    gap, not a capability.
    """
    out, seen = [], set()
    for r in sorted(quantity_rules(), key=lambda r: r.id):
        key = (r.source_quantity_kind, r.target_quantity_kind,
               r.normalization_definition)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "from": r.source_quantity_kind, "to": r.target_quantity_kind,
            "op": _IMPL_OP.get(r.implementation_id),
            "bridge": (r.required_context[0] if r.required_context else None),
            "normalization": r.normalization_definition,
            "rule_id": r.id, "self_contained": r.self_contained,
            "invertible": r.invertible,
            "validity": "; ".join(r.assumptions) or None,
            "family": None,
        })
    return out
