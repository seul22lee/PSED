#!/usr/bin/env python3
"""Can these two scientific results actually be compared?

A canonical quantity id is not enough to answer that. `t/t_entrance`, `t/t_max` and
`t/t_planar` all canonicalise to `normalized_thickness` with unit 1, and they are three
different physical statements: the first says how much thinner the film got relative to
the mouth of the feature, the second relative to wherever this particular profile peaked,
the third relative to a flat witness coupon. Overlaying them as if they were one curve
would be a quiet, confident error.

So the comparison identity here is (quantity, comparison group, normalization definition),
and a normalization nobody recorded is not a normalization that matches -- it is
`ambiguous`, which is a different answer from "no" and a very different answer from "yes".

This layer executes the contract the ontology already carries: comparison groups with
canonical units, normalization definitions naming their denominator, typed transformation
rules, and statuses that already separate a transform that ran from one whose context is
missing. It resolves transform parameters from the knowledge graph with provenance, and it
never invents one -- a transform that needs a feature height nobody extracted comes back
`missing_context` naming exactly what is absent, because a plausible literature value
would make the answer look better and be worth less.

Source series are immutable. Everything produced here is derived and carries its lineage.
"""
import json
import re
from pathlib import Path

from ontology import vocab as _vocab
from pipeline.canonical import units as U

_ONTO = json.loads((Path(__file__).resolve().parents[2] / "ontology"
                    / "ald_ontology.json").read_text())
QR = _ONTO["quantity_relations"]
GROUPS = QR["comparison_groups"]
NORMALIZATIONS = {n["id"]: n for n in QR["normalization_definitions"]}
TRANSFORMS = QR["transforms"]
TTYPES = {t["id"]: t for t in QR["transformation_types"]}

# --- axis / profile statuses. The ontology's own transformation_statuses vocabulary is
# reused wherever it already says the thing; the rest name outcomes it has no word for.
DIRECT = "DIRECT"
UNIT_CONVERTIBLE = "UNIT_CONVERTIBLE"
TRANSFORMABLE_EXACT = "TRANSFORMABLE_EXACT"
TRANSFORMABLE_WITH_CONTEXT = "TRANSFORMABLE_WITH_CONTEXT"
MISSING_CONTEXT = "missing_context"          # ontology status
AMBIGUOUS = "ambiguous"                      # ontology status
SHAPE_ONLY = "SHAPE_ONLY"
RELATED_NOT_COMPARABLE = "RELATED_NOT_COMPARABLE"
NOT_COMPARABLE = "NOT_COMPARABLE"

DIRECT_PROFILE = "DIRECT_PROFILE"
TRANSFORMABLE_PROFILE = "TRANSFORMABLE_PROFILE"
SHAPE_ONLY_PROFILE = "SHAPE_ONLY_PROFILE"

#: representation of a normalized axis whose basis nobody recorded
NORMALIZATION_UNKNOWN = "NORMALIZATION_UNKNOWN"
NORMALIZATION_EXPLICIT = "NORMALIZATION_EXPLICIT"
NORMALIZATION_INFERRED = "NORMALIZATION_INFERRED_WITH_PROVENANCE"

#: Wording that identifies WHICH normalization a printed axis used. These are read off the
#: paper's own axis label, so an inference is only ever made where the author said it.
#: `_` is a word character, so \b does not fire inside "t_max" -- the separator class is
#: spelled out instead, which is what the printed labels actually use.
_SEP = r"(?:^|[\s_/()\-,])"
_NORM_CLUES = (
    (re.compile(_SEP + r"(?:entrance|mouth|inlet)|\bt\(0\)", re.I), "t_over_t_entrance"),
    (re.compile(_SEP + r"max(?:imum)?\b", re.I), "t_over_t_max"),
    (re.compile(_SEP + r"(?:planar|blanket|flat|witness)", re.I), "t_over_t_planar"),
)

#: quantities whose value is dimensionless BECAUSE it was normalized
_NORMALIZED_QUANTITIES = {"normalized_thickness", "dimensionless_distance"}


def group_of(quantity):
    """The comparison group whose canonical quantity this is, or None."""
    for g, v in GROUPS.items():
        if v.get("canonical_quantity") == quantity:
            return g
    return None


def canonical_unit(quantity):
    g = group_of(quantity)
    return GROUPS[g].get("canonical_unit") if g else _vocab.quantity_unit(quantity)


def axis_representation(quantity, unit, raw_label=None):
    """What an axis actually represents, beyond its canonical quantity.

    Returns a dict carrying the normalization identity when the axis is a normalized one.
    A normalized axis whose basis is not stated is reported UNKNOWN rather than assumed --
    that distinction is the whole reason this function exists.
    """
    rep = {"quantity": quantity, "unit": unit, "raw_label": raw_label,
           "comparison_group": group_of(quantity),
           "normalized": quantity in _NORMALIZED_QUANTITIES,
           "normalization_definition": None,
           "normalization_status": None, "normalization_evidence": None}
    if not rep["normalized"]:
        return rep
    lab = str(raw_label or "")
    for pat, nid in _NORM_CLUES:
        if pat.search(lab):
            rep.update(normalization_definition=nid,
                       normalization_status=NORMALIZATION_INFERRED,
                       normalization_evidence="the printed axis label %r names the "
                                              "normalization basis" % lab)
            return rep
    rep.update(normalization_status=NORMALIZATION_UNKNOWN,
               normalization_evidence="the axis is dimensionless and normalized, but "
                                      "neither the label %r nor the record says relative "
                                      "to what" % lab)
    return rep


# --- context resolution ------------------------------------------------------------
def resolve_context(parameter, case=None, series=None, paper_records=None):
    """Find a transform parameter in the knowledge graph, with its provenance.

    Searches only places that carry evidence for THIS result: the case's own conditions
    and the series' own points. Paper-wide guessing is deliberately absent -- a feature
    height mentioned somewhere in a paper is not thereby the feature height of this
    profile, and a transform built on that would be untraceable.
    """
    if case:
        for c in (case.get("case_defining_conditions") or []):
            if c.get("quantity") == parameter and c.get("value") is not None:
                return {"parameter": parameter, "value": c.get("value"),
                        "unit": c.get("unit"), "found": True,
                        "source_object": "ExperimentalCase %s" % case.get("case_id"),
                        "source_evidence": c.get("evidence"),
                        "provenance_type": c.get("provenance_type"),
                        "confidence": "case_defining_condition"}
    # a normalization denominator taken from the profile's OWN points is self-evident:
    # t_max of this curve is in this curve, and nothing external is being assumed
    if series is not None and parameter in ("t_max", "self_maximum"):
        ys = [p[1] for p in (series.get("points") or []) if p and p[1] is not None]
        if ys:
            return {"parameter": parameter, "value": max(ys), "unit": series.get("y_unit"),
                    "found": True,
                    "source_object": "ResultSeries %s" % series.get("result_series_id"),
                    "source_evidence": "maximum of this series' own %d extracted points"
                                       % len(ys),
                    "provenance_type": "derived_from_series_points",
                    "confidence": "self_referential"}
    return {"parameter": parameter, "value": None, "unit": None, "found": False,
            "source_object": None,
            "source_evidence": "no evidence for %r on this result" % parameter,
            "confidence": None}


def transform_for(a_quantity, b_quantity):
    """The declared ontology transform between two quantities, either direction."""
    for t in TRANSFORMS:
        if t.get("from") == a_quantity and t.get("to") == b_quantity:
            return t, "forward"
        if t.get("to") == a_quantity and t.get("from") == b_quantity:
            return t, "reverse"
    return None, None


def compare_axis(a, b, a_case=None, b_case=None, a_series=None, b_series=None):
    """How two axes relate. `a`/`b` are axis_representation dicts."""
    out = {"a": a, "b": b, "status": None, "reason": None,
           "semantically_transformable": False,
           "operationally_transformable_now": False,
           "required_context": [], "available_context": [], "missing_context": [],
           "transform": None}

    if a["quantity"] == b["quantity"]:
        # same quantity -- but a normalized one is only the same axis if the BASIS matches
        if a["normalized"] or b["normalized"]:
            na, nb = a["normalization_definition"], b["normalization_definition"]
            if na and nb and na == nb:
                out.update(status=DIRECT, reason="same quantity and the same declared "
                                                 "normalization %r" % na,
                           semantically_transformable=True,
                           operationally_transformable_now=True)
                return out
            if na and nb and na != nb:
                out.update(status=RELATED_NOT_COMPARABLE,
                           reason="both are %s, but normalized against different "
                                  "references (%s vs %s), which are different physical "
                                  "statements" % (a["quantity"], na, nb))
                return out
            out.update(status=AMBIGUOUS,
                       reason="both are %s, but at least one does not say what it was "
                              "normalized against (%s / %s)"
                              % (a["quantity"], na or "unknown", nb or "unknown"),
                       semantically_transformable=True)
            return out
        ua, ub = a.get("unit"), b.get("unit")
        if str(ua or "") == str(ub or ""):
            out.update(status=DIRECT, reason="same quantity and unit",
                       semantically_transformable=True,
                       operationally_transformable_now=True)
            return out
        try:
            same = U.same_dimension(ua, ub)
        except Exception:
            same = False
        if same:
            out.update(status=UNIT_CONVERTIBLE,
                       reason="same quantity; %r and %r are the same dimension" % (ua, ub),
                       semantically_transformable=True,
                       operationally_transformable_now=True)
            return out
        out.update(status=NOT_COMPARABLE,
                   reason="same quantity but units %r and %r are not convertible"
                          % (ua, ub))
        return out

    t, direction = transform_for(a["quantity"], b["quantity"])
    if not t:
        out.update(status=NOT_COMPARABLE,
                   reason="no declared ontology relation between %s and %s"
                          % (a["quantity"], b["quantity"]))
        return out
    bridge = t.get("bridge")
    out["transform"] = {"from": t.get("from"), "to": t.get("to"), "op": t.get("op"),
                        "bridge": bridge, "validity": t.get("validity"),
                        "direction": direction}
    out["semantically_transformable"] = True
    if not bridge:
        out.update(status=TRANSFORMABLE_EXACT,
                   reason="declared transform needs no external parameter",
                   operationally_transformable_now=True)
        return out
    out["required_context"] = [bridge]
    ctx = resolve_context(bridge, case=a_case or b_case, series=a_series or b_series)
    if ctx["found"]:
        out["available_context"] = [ctx]
        out.update(status=TRANSFORMABLE_WITH_CONTEXT,
                   reason="declared transform via %s, and %s is available" % (t.get("op"),
                                                                              bridge),
                   operationally_transformable_now=True)
    else:
        out["missing_context"] = [bridge]
        out.update(status=MISSING_CONTEXT,
                   reason="the ontology declares this transform, but %r is not extracted "
                          "for this result" % bridge)
    return out


def compare_result_series(a, b, a_case=None, b_case=None):
    """Whole-profile comparability: both axes, then the profile-level verdict."""
    ax = compare_axis(axis_representation(a.get("x_quantity"), a.get("x_unit"),
                                          a.get("x_label")),
                      axis_representation(b.get("x_quantity"), b.get("x_unit"),
                                          b.get("x_label")),
                      a_case, b_case, a, b)
    ay = compare_axis(axis_representation(a.get("y_quantity"), a.get("y_unit"),
                                          a.get("y_label")),
                      axis_representation(b.get("y_quantity"), b.get("y_unit"),
                                          b.get("y_label")),
                      a_case, b_case, a, b)
    ok = {DIRECT, UNIT_CONVERTIBLE, TRANSFORMABLE_EXACT, TRANSFORMABLE_WITH_CONTEXT}
    if ax["status"] in ok and ay["status"] in ok:
        verdict = (DIRECT_PROFILE if ax["status"] == DIRECT and ay["status"] == DIRECT
                   else TRANSFORMABLE_PROFILE)
    elif MISSING_CONTEXT in (ax["status"], ay["status"]):
        verdict = MISSING_CONTEXT
    elif AMBIGUOUS in (ax["status"], ay["status"]):
        # dimensionless on both sides with an unrecorded basis: the shape is still a
        # legitimate object of comparison, the absolute values are not
        verdict = (SHAPE_ONLY_PROFILE
                   if ax["status"] in ok | {AMBIGUOUS} and ay["status"] == AMBIGUOUS
                   else AMBIGUOUS)
    elif RELATED_NOT_COMPARABLE in (ax["status"], ay["status"]):
        verdict = RELATED_NOT_COMPARABLE
    else:
        verdict = NOT_COMPARABLE
    return {
        "a": {"paper_id": a.get("paper_id"), "series": a.get("result_series_id"),
              "data_source": a.get("data_source")},
        "b": {"paper_id": b.get("paper_id"), "series": b.get("result_series_id"),
              "data_source": b.get("data_source")},
        "profile_status": verdict, "x": ax, "y": ay,
        "cross_paper": a.get("paper_id") != b.get("paper_id"),
        "provenance_note": ("comparability of REPRESENTATION only; it does not assert the "
                            "two experiments were run under equivalent conditions"),
    }


def transform_series(series, target_unit=None, normalization=None, context=None):
    """Derive a transformed copy. The source series is never modified.

    Returns a TransformedSeries carrying its own lineage: which series it came from, which
    rule was applied, with what parameter, and where that parameter came from.
    """
    pts = [list(p) for p in (series.get("points") or [])]
    steps = []
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if target_unit and series.get("x_unit") and str(target_unit) != str(series["x_unit"]):
        xs = [U.convert(v, series["x_unit"], target_unit) if v is not None else None
              for v in xs]
        steps.append({"axis": "x", "type": "unit_conversion",
                      "rule_id": "length_unit_conversion",
                      "from_unit": series["x_unit"], "to_unit": target_unit,
                      "invertible": True, "parameters": None})
    if normalization:
        nd = NORMALIZATIONS[normalization]
        ref = context["value"]
        ys = [(v / ref) if v is not None else None for v in ys]
        steps.append({"axis": "y", "type": "reference_value_normalization",
                      "rule_id": normalization,
                      "definition": nd.get("semantic_label"),
                      "numerator": nd.get("numerator"), "denominator": nd.get("denominator"),
                      "parameters": {"reference": ref, "unit": context.get("unit")},
                      "parameter_provenance": context,
                      "invertible": True})
    return {
        "source_series_id": series.get("result_series_id"),
        "source_paper_id": series.get("paper_id"),
        "source_points": series.get("points"),
        "source_x_quantity": series.get("x_quantity"), "source_x_unit": series.get("x_unit"),
        "source_y_quantity": series.get("y_quantity"), "source_y_unit": series.get("y_unit"),
        "target_x_unit": target_unit or series.get("x_unit"),
        "target_y_quantity": ("normalized_thickness" if normalization
                              else series.get("y_quantity")),
        "target_y_unit": "1" if normalization else series.get("y_unit"),
        "normalization_definition": normalization,
        "transformations": steps,
        "points": [[x, y] for x, y in zip(xs, ys)],
        "status": "converted" if steps else "already_canonical",
    }


def find_comparable_series(target, universe, cross_paper_only=False,
                           statuses=None, cases=None):
    """Every series in `universe` comparable to `target`, with the reason attached.

    Pre-indexed on comparison group so unrelated series are never pairwise compared.
    """
    cases = cases or {}
    tg = (group_of(target.get("x_quantity")), group_of(target.get("y_quantity")))
    out = []
    for s in universe:
        if s.get("result_series_id") == target.get("result_series_id"):
            continue
        if cross_paper_only and s.get("paper_id") == target.get("paper_id"):
            continue
        sg = (group_of(s.get("x_quantity")), group_of(s.get("y_quantity")))
        # index: at least one axis must share a comparison group, or a declared transform
        # must exist between the y quantities
        if tg[1] != sg[1] and not transform_for(target.get("y_quantity"),
                                                s.get("y_quantity"))[0]:
            continue
        r = compare_result_series(target, s, cases.get(target.get("paper_id")),
                                  cases.get(s.get("paper_id")))
        if statuses and r["profile_status"] not in statuses:
            continue
        out.append(r)
    return out
