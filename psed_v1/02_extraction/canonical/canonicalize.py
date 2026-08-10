"""
canonical/canonicalize.py — turn one resolved axis into canonical values.

Contract:
  * RAW values are never modified. Canonical values are new arrays.
  * A canonical value ALWAYS comes with a TransformationRecord naming the rule,
    the context used (with scope + provenance) and the status.
  * Anything not transformable keeps a status and a structured reason and stays
    in the dataset.

Two kinds of canonical output:
  `canonical`   — the axis expressed in ITS OWN comparison group (an x/H curve
                  stays an x/H curve; it is comparison-ready against other x/H
                  curves and against nothing else).
  `projections` — additional comparison groups the axis can ALSO be expressed in
                  once context resolves (x/H + H -> spatial_position in µm).
                  A projection that lacks context is still emitted, with status
                  missing_context/ambiguous, so the gap is visible.
"""
from __future__ import annotations

from . import rules as R
from . import units as U
from .schema import (Status, TransformationRecord, COMPARISON_GROUPS,
                     NORMALIZATION_DEFINITIONS, canonical_unit_for_group,
                     canonical_quantity_for_group)

ROUNDTRIP_TOL = 1e-6


def _src(curve, axis):
    return {
        "paper_id": curve["doi"], "doi": curve["doi"],
        "figure": curve["figure_number"], "panel": curve["panel"],
        "series": curve.get("series_label"), "series_index": curve["series_index"],
        "axis": axis,
        "source_file": curve["source_file"],
        "json_pointer": curve["json_pointer"] + "/points",
        "source_checksum": curve["source_checksum"],
        "experiment_id": curve.get("experiment_id"),
    }


def _values(curve, axis):
    i = 0 if axis == "x" else 1
    return [p[i] for p in curve["points"]]


def canonicalize_axis(curve, axis, semantics, pool):
    """Returns (canonical|None, projections[], transformations[])."""
    values = _values(curve, axis)
    source = _src(curve, axis)
    # The unit used for conversion is the RECOVERED one when a verbatim axis
    # label supplied better evidence ("Thickness/cycles S/N (nm)" -> nm/cycle).
    # semantics["raw_unit"] is preserved untouched for the audit trail.
    raw_unit = semantics.get("unit", semantics.get("raw_unit"))
    status = semantics.get("status")
    transformations = []

    # --- semantics unresolved -> no canonical value, reason preserved -----
    if status != "resolved":
        transformations.append(TransformationRecord.make(
            axis=axis, rule_id="axis_semantic_resolution",
            rule_version=R.get("axis_semantic_resolution").version,
            ttype="axis_semantic_resolution",
            formula=None, status=status or Status.UNSUPPORTED,
            original_unit=raw_unit,
            unresolved_reason=semantics.get("unresolved_reason"),
            confidence=0.0, source=source,
            assumptions=[]))
        return None, [], transformations

    group = semantics.get("comparison_group")
    if not group:
        transformations.append(TransformationRecord.make(
            axis=axis, rule_id="axis_semantic_resolution",
            rule_version=R.get("axis_semantic_resolution").version,
            ttype="axis_semantic_resolution", formula=None,
            status=Status.NOT_APPLICABLE, original_unit=raw_unit,
            unresolved_reason=semantics.get("unresolved_reason")
            or "axis has no comparison group", source=source))
        return None, [], transformations

    gspec = COMPARISON_GROUPS[group]
    target_unit = canonical_unit_for_group(group)
    target_quantity = canonical_quantity_for_group(group)
    ndef_id = semantics.get("normalization_definition")
    # a resolved normalization definition IS the semantic evidence that an
    # empty unit means "dimensionless" (spec: never assume it otherwise)
    allow_empty = bool(ndef_id) or gspec.get("dimension") == "dimensionless"

    # --- 1. bring the axis into its own group's canonical unit ------------
    canonical, trec = _to_group_unit(values, raw_unit, target_unit, target_quantity,
                                     group, ndef_id, axis, source, allow_empty)
    transformations.append(trec)
    if canonical is None:
        return None, [], transformations

    # --- 2. projections into other comparison groups ----------------------
    projections = []
    if ndef_id:
        proj, ptrec = _project_denormalized(curve, axis, ndef_id, canonical["values"],
                                            pool, source)
        transformations.append(ptrec)
        if proj:
            projections.append(proj)
    return canonical, projections, transformations


def _to_group_unit(values, raw_unit, target_unit, target_quantity, group,
                   ndef_id, axis, source, allow_empty):
    """Identity when already canonical, otherwise a declared unit-conversion rule."""
    src_u = U.try_parse(raw_unit, allow_empty)
    tgt_u = U.try_parse(target_unit, True)

    if src_u is None:
        rule = R.get("axis_semantic_resolution")
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=None, status=Status.UNSUPPORTED, original_unit=raw_unit,
            canonical_unit=target_unit, comparison_group=group,
            normalization_definition=ndef_id,
            unresolved_reason=("unit %r is not a recognised, convertible unit "
                               "(arbitrary/uncalibrated or unparseable)" % raw_unit),
            source=source, confidence=0.0)

    if src_u.dimension != tgt_u.dimension:
        rule = R.unit_conversion_rule_for(raw_unit, allow_empty) or R.get("axis_semantic_resolution")
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=None, status=Status.INVALID, original_unit=raw_unit,
            canonical_unit=target_unit, comparison_group=group,
            normalization_definition=ndef_id,
            unresolved_reason=(
                "declared unit %r has dimension %s but the quantity's comparison group "
                "%r is %s — the printed unit and the quantity disagree, so no conversion "
                "is safe (needs manual review)"
                % (raw_unit, U.DIM_NAME.get(src_u.dimension), group,
                   U.DIM_NAME.get(tgt_u.dimension))),
            source=source, confidence=0.0)

    if src_u.symbol == tgt_u.symbol:
        rule = R.get("identity_canonical_mapping")
        out = list(values)
        return ({"comparison_group": group, "quantity": target_quantity,
                 "unit": target_unit, "values": out,
                 "normalization_definition": ndef_id},
                TransformationRecord.make(
                    axis=axis, rule_id=rule.id, rule_version=rule.version,
                    ttype=rule.type, formula="identity", status=Status.ALREADY_CANONICAL,
                    original_unit=raw_unit, canonical_unit=target_unit,
                    comparison_group=group, normalization_definition=ndef_id,
                    invertible=True, confidence=1.0, source=source,
                    assumptions=rule.assumptions))

    rule = R.unit_conversion_rule_for(raw_unit, allow_empty)
    if rule is None:
        return None, TransformationRecord.make(
            axis=axis, rule_id="axis_semantic_resolution", rule_version="1.0.0",
            ttype="axis_semantic_resolution", formula=None, status=Status.UNSUPPORTED,
            original_unit=raw_unit, canonical_unit=target_unit, comparison_group=group,
            unresolved_reason="no declared unit-conversion rule for dimension %s"
                              % U.DIM_NAME.get(src_u.dimension),
            source=source, confidence=0.0)
    try:
        out = rule.apply(values, from_unit=raw_unit, to_unit=target_unit,
                         allow_empty_as_dimensionless=allow_empty)
        rt = rule.roundtrip_error(values, from_unit=raw_unit, to_unit=target_unit,
                                  allow_empty_as_dimensionless=allow_empty)
    except Exception as exc:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=None, status=Status.INVALID, original_unit=raw_unit,
            canonical_unit=target_unit, comparison_group=group,
            unresolved_reason="%s: %s" % (type(exc).__name__, exc),
            source=source, confidence=0.0)
    if rt is not None and rt > ROUNDTRIP_TOL:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=None, status=Status.INVALID, original_unit=raw_unit,
            canonical_unit=target_unit, comparison_group=group,
            unresolved_reason="round-trip error %.3g exceeds tolerance %g" % (rt, ROUNDTRIP_TOL),
            source=source, confidence=0.0)
    return ({"comparison_group": group, "quantity": target_quantity,
             "unit": target_unit, "values": out,
             "normalization_definition": ndef_id},
            TransformationRecord.make(
                axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
                formula="%s -> %s" % (src_u.symbol, tgt_u.symbol),
                status=Status.CONVERTED, original_unit=raw_unit,
                canonical_unit=target_unit, comparison_group=group,
                normalization_definition=ndef_id, invertible=rule.invertible,
                confidence=1.0, source=source, assumptions=rule.assumptions))


def _project_denormalized(curve, axis, ndef_id, norm_values, pool, source):
    """Recover the DIMENSIONAL axis from a normalized one, when (and only when)
    the denominator resolves at a single applicable scope."""
    rule = R.denormalization_rule_for(ndef_id)
    ndef = NORMALIZATION_DEFINITIONS[ndef_id]
    if rule is None:
        return None, TransformationRecord.make(
            axis=axis, rule_id="axis_semantic_resolution", rule_version="1.0.0",
            ttype="axis_semantic_resolution", formula=ndef.get("formula"),
            status=Status.UNSUPPORTED, normalization_definition=ndef_id,
            unresolved_reason="no denormalization rule declared for %s" % ndef_id,
            source=source)

    ctx, res, cstatus, creason = pool.resolve_all(
        rule.required_context, target_units={q: rule.output_unit for q in rule.required_context})
    target_group = _dimensional_group_for(rule.target_quantity_kind)

    if cstatus is not None:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=ndef.get("formula"), status=cstatus,
            normalization_definition=ndef_id, comparison_group=target_group,
            canonical_unit=rule.output_unit, context=res,
            unresolved_reason=creason, confidence=0.0, source=source,
            assumptions=rule.assumptions)
    try:
        out = rule.apply(norm_values, ctx=ctx, from_unit="1", to_unit=rule.output_unit,
                         allow_empty_as_dimensionless=True)
        rt = rule.roundtrip_error(norm_values, ctx=ctx, from_unit="1",
                                  to_unit=rule.output_unit, allow_empty_as_dimensionless=True)
    except R.MissingContext as exc:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=ndef.get("formula"), status=Status.MISSING_CONTEXT,
            normalization_definition=ndef_id, comparison_group=target_group,
            context=res, unresolved_reason=str(exc), source=source,
            assumptions=rule.assumptions)
    except Exception as exc:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=ndef.get("formula"), status=Status.INVALID,
            normalization_definition=ndef_id, comparison_group=target_group,
            context=res, unresolved_reason="%s: %s" % (type(exc).__name__, exc),
            source=source, assumptions=rule.assumptions)

    domain_violations = rule.check_domain(norm_values)
    if rt is not None and rt > ROUNDTRIP_TOL:
        return None, TransformationRecord.make(
            axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
            formula=ndef.get("formula"), status=Status.INVALID,
            normalization_definition=ndef_id, comparison_group=target_group,
            context=res, unresolved_reason="round-trip error %.3g" % rt, source=source)

    proj = {"comparison_group": target_group,
            "quantity": rule.target_quantity_kind,
            "unit": rule.output_unit, "values": out,
            "from_normalization": ndef_id}
    trec = TransformationRecord.make(
        axis=axis, rule_id=rule.id, rule_version=rule.version, ttype=rule.type,
        formula=ndef.get("formula"), status=Status.CONVERTED,
        normalization_definition=ndef_id, comparison_group=target_group,
        original_unit="1", canonical_unit=rule.output_unit, context=res,
        invertible=rule.invertible, confidence=0.9, source=source,
        assumptions=rule.assumptions + (
            ["%d value(s) outside the declared valid domain (flagged, not clamped)"
             % len(domain_violations)] if domain_violations else []))
    if domain_violations:
        trec["domain_violations"] = domain_violations
    return proj, trec


_DIM_GROUP = {}
for _gid, _g in COMPARISON_GROUPS.items():
    if not _g.get("normalization_definition"):
        _DIM_GROUP.setdefault(_g["canonical_quantity"], _gid)


def _dimensional_group_for(quantity):
    return _DIM_GROUP.get(quantity)
