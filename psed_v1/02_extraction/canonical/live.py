"""
canonical/live.py — the canonical layer's interface for the LIVE extraction-to-KB
path (03_corpus/scripts/06_to_kb.py).

Everything the live pipeline needs, in one place, so the fixes are shared with the
post-processor instead of reimplemented:

  normalize_measurand()   converts VALUE AND UNIT together (the historical bug was
                          calling the converter with value=None, so nothing was
                          rescaled); preserves the /cycle dimension.
  coordinate_unit()       resolves and canonicalises the x unit so coordinate
                          numbers are never stored bare.
  axis_granularity()      ontology axis_role -> profile | series | single |
                          correlation, replacing `len(points) > 1`.
  split_series()          turns a condition-axis curve into one experiment per
                          point plus the ExperimentSeries that owns them, with
                          deterministic ids.
  scope_of()              declares the applicability scope of a controlled value.
  mark_ambiguous_context() flags conflicting same-scope candidates instead of
                          broadcasting one of them.

Python 3.8 compatible.
"""
from __future__ import annotations

from . import units as U
from .axis_semantics import (canon_quantity, axis_role_of, recover_unit,
                             resolve_granularity)
from .schema import COMPARISON_GROUPS, QK_META, SCOPE_ORDER, Status

# Canonical storage unit per quantity dimension for the KB. These are the units
# the resolved experiments store in; display units may differ.
KB_UNIT_BY_DIMENSION = {
    "length": "nm",              # the KB's historical convention for lengths
    "length_per_cycle": "nm/cycle",
    "pressure": "Pa",
    "time": "s",
    "temperature": "°C",         # the KB stores °C; canonical comparison uses K
    "cycle": "cycle",
    "dimensionless": "1",
    "exposure": "Pa.s",
    "angle": "deg",
}


def kb_unit_for(quantity, unit):
    """Target KB unit for a quantity given its printed unit. None when the unit
    cannot be parsed (in which case the caller must leave the value alone)."""
    u = U.try_parse(unit)
    if u is None:
        return None
    return KB_UNIT_BY_DIMENSION.get(U.DIM_NAME.get(u.dimension))


def normalize_measurand(quantity, unit, values, label=None):
    """Convert a measurand's UNIT AND VALUES together.

    Returns (values, unit, record) where `record` documents what happened.
    `values` is returned unchanged whenever conversion is not provably safe:
      * unit unparseable / arbitrary  -> unchanged, status unsupported
      * unit dimension conflicts with the quantity's ontology dimension
        (growth_per_cycle printed as "nm") -> unchanged, status invalid.
        The missing "/cycle" is NEVER assumed; only a verbatim label that shows
        the per-cycle division can recover it (see recover_unit)."""
    qid = canon_quantity(quantity) or quantity
    unit_in = unit
    unit, unit_ev = recover_unit(unit, label, qid)

    u = U.try_parse(unit)
    if u is None:
        return values, unit_in, {
            "status": Status.UNSUPPORTED, "from_unit": unit_in, "to_unit": None,
            "reason": "unit %r is not a recognised convertible unit" % unit_in,
            "unit_recovered": None, "values_rescaled": False}

    # cross-check the printed unit against the ontology's dimension for the quantity
    expected = _ontology_unit(qid)
    if expected is not None:
        eu = U.try_parse(expected, allow_empty_as_dimensionless=True)
        if eu is not None and eu.dimension != u.dimension:
            return values, unit_in, {
                "status": Status.INVALID, "from_unit": unit_in,
                "to_unit": None,
                "reason": ("printed unit %r is %s but ontology quantity %r is %s; "
                           "the label and the quantity disagree — not converted, "
                           "needs manual review"
                           % (unit_in, U.DIM_NAME.get(u.dimension), qid,
                              U.DIM_NAME.get(eu.dimension))),
                "unit_recovered": unit if unit != unit_in else None,
                "values_rescaled": False}

    target = kb_unit_for(qid, unit)
    if target is None or U.try_parse(target) is None:
        return values, U.canonical_symbol(unit), {
            "status": Status.ALREADY_CANONICAL, "from_unit": unit_in,
            "to_unit": U.canonical_symbol(unit), "reason": None,
            "unit_recovered": unit if unit != unit_in else None,
            "values_rescaled": False}
    if U.parse(target) is u:
        return values, target, {
            "status": Status.ALREADY_CANONICAL, "from_unit": unit_in,
            "to_unit": target, "reason": None,
            "unit_recovered": unit if unit != unit_in else None,
            "values_rescaled": False}
    out = U.convert_series(values, unit, target) if values else values
    return out, target, {
        "status": Status.CONVERTED, "from_unit": unit_in, "to_unit": target,
        "reason": None, "unit_recovered": unit if unit != unit_in else None,
        "values_rescaled": True,
        "factor": U.convert(1.0, unit, target)}


def _ontology_unit(qid):
    meta = QK_META.get(qid)
    if not meta:
        return None
    return U.from_qudt(meta.get("unit")) or meta.get("unit")


def coordinate_unit(quantity, unit, label=None):
    """Resolve the x-axis unit. Returns (raw_unit, normalized_unit, dimensionless).

    `normalized_unit` is None when the unit cannot be parsed — the caller must
    then record the coordinate as unit-less-with-reason rather than as a bare
    number (spec §2.3)."""
    qid = canon_quantity(quantity) or quantity
    recovered, _ = recover_unit(unit, label, qid)
    u = U.try_parse(recovered)
    if u is not None:
        return unit, u.symbol, U.DIM_NAME.get(u.dimension) == "dimensionless"
    # An unresolved quantity gets NO unit. Falling through to "1" here would treat
    # every unrecognised axis (binding energy, Raman shift, ...) as dimensionless,
    # which is precisely the "empty unit means dimensionless" assumption the spec
    # forbids without semantic evidence.
    if qid not in QK_META:
        return unit, None, False
    onto_unit = _ontology_unit(qid)
    if not onto_unit:
        return unit, None, False
    onto = U.try_parse(onto_unit)
    if onto is not None and U.DIM_NAME.get(onto.dimension) == "dimensionless":
        return unit, "1", True          # the ONTOLOGY declares it dimensionless
    if onto is not None and U.DIM_NAME.get(onto.dimension) == "cycle":
        return unit, "cycle", False     # a cycle count is not a bare number
    return unit, None, False


def axis_granularity(coordinate_quantity, n_points):
    """Ontology-backed representation for a curve. Never uses the point count to
    decide between profile and series."""
    qid = canon_quantity(coordinate_quantity) or coordinate_quantity
    return resolve_granularity({"quantity": qid, "axis_role": axis_role_of(qid)}, n_points)


def series_id(pid, fig, panel, index):
    """Deterministic ExperimentSeries id (stable across rebuilds)."""
    return "%s-%s%s-S%d" % (pid, fig, panel or "", index)


def point_experiment_id(base_series_id, point_index):
    """Deterministic id for one point of a condition sweep."""
    return "%s-P%03d" % (base_series_id, point_index)


def scope_of(origin, source):
    """Applicability scope of a controlled value, from its origin record.
    Narrowest wins during resolution, so scope must be honest."""
    lvl = (origin or {}).get("level")
    frm = (origin or {}).get("from")
    if frm == "series_label":
        return "curve"
    if frm in ("panel_conditions",):
        return "panel"
    if frm in ("caption", "figure_caption"):
        return "figure"
    if lvl == "experiment":
        return "experiment"
    if source in ("methods", "card") or frm in ("card", "methods"):
        return "method"
    return "paper"


def mark_ambiguous_context(controlled):
    """Flag every controlled quantity that has SEVERAL DISTINCT values at the
    same scope. Such a value must not be treated as applying to the experiment.

    Returns (controlled, conflicts) where each entry gains
    `context_status` = resolved | ambiguous and `scope`."""
    by_key = {}
    for c in controlled:
        c["scope"] = scope_of(c.get("origin"), c.get("source"))
        by_key.setdefault((c.get("quantity"), c["scope"]), []).append(c)
    conflicts = []
    for (q, scope), group in by_key.items():
        vals = []
        for c in group:
            v, unit = c.get("value"), c.get("unit")
            try:
                vals.append(U.convert(float(v), unit, group[0].get("unit"))
                            if (unit and group[0].get("unit")) else float(v))
            except Exception:
                vals.append(None)
        clean = [v for v in vals if v is not None]
        distinct = {round(v, 12) for v in clean}
        if len(distinct) > 1:
            reason = ("%d distinct %s values at %s scope (%s); not applied to this "
                      "experiment without narrower evidence"
                      % (len(distinct), q, scope,
                         ", ".join("%g" % d for d in sorted(distinct))))
            for c in group:
                c["context_status"] = Status.AMBIGUOUS
                c["context_conflict_reason"] = reason
            conflicts.append({"quantity": q, "scope": scope,
                              "values": sorted(distinct), "reason": reason})
        else:
            for c in group:
                c["context_status"] = "resolved"
    return controlled, conflicts


def narrowest_scope_value(controlled, quantity):
    """The value for `quantity` from the narrowest scope that is not ambiguous.
    Returns (value, unit, scope) or (None, None, None)."""
    cands = [c for c in controlled if c.get("quantity") == quantity
             and c.get("value") is not None
             and c.get("context_status") != Status.AMBIGUOUS]
    if not cands:
        return None, None, None
    cands.sort(key=lambda c: SCOPE_ORDER.index(c.get("scope"))
               if c.get("scope") in SCOPE_ORDER else len(SCOPE_ORDER))
    best = cands[0]
    return best.get("value"), best.get("unit"), best.get("scope")
