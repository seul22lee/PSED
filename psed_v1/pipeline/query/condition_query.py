#!/usr/bin/env python3
"""Species-aware condition comparison and case querying.

A condition is not identified by its quantity. `pulse_time` is a valve duration for ONE
named chemical -- the ontology says so, qualifying it by reactant -- so a 2 s SnI4 pulse
and a 2 s H2O pulse are different controls that happen to share a number and a unit.
Comparing them on quantity alone answers the wrong question, and answering it confidently
is worse than abstaining.

So the comparison key is (quantity, species, process_step), and the rule for an unknown
species is the identity rule this repository already runs on: MISSING is not SAME. A
condition whose reagent was never attributed is not thereby the same control as one that
was; it is a condition whose comparability is unresolved, and it is reported as such
rather than quietly matched or quietly dropped.

This layer reads case identity; it does not create it. Fingerprints and case IDs come
from the semantic pipeline, and nothing here writes them.

Authoritative input: semantic/experimental_cases.json.
"""
import json
import re
from pathlib import Path

from pipeline.canonical import units as U

# --- comparison outcomes ----------------------------------------------------------
EXACT_MATCH = "EXACT_MATCH"
SAME_CONDITION_DIFFERENT_VALUE = "SAME_CONDITION_DIFFERENT_VALUE"
DIFFERENT_SPECIES = "DIFFERENT_SPECIES"
DIFFERENT_QUANTITY = "DIFFERENT_QUANTITY"
DIFFERENT_STEP = "DIFFERENT_STEP"
SPECIES_UNRESOLVED = "SPECIES_UNRESOLVED"
UNIT_CONVERTIBLE = "UNIT_CONVERTIBLE"
NOT_COMPARABLE = "NOT_COMPARABLE"

#: how a whole case pair relates, which is a weaker claim than any single condition's
MATCH_ON_SHARED_CONDITIONS = "MATCH_ON_SHARED_CONDITIONS"
PROVEN_DIFFER_ONLY_IN = "PROVEN_DIFFER_ONLY_IN"

_NUM = re.compile(r"^\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*$")


def species_of(cond):
    """The canonical species, or None. Empty string is absence, not a species."""
    s = cond.get("species")
    s = str(s).strip() if s is not None else ""
    return s or None


def condition_key(cond):
    """What identifies a condition for comparison: not the quantity alone."""
    return (cond.get("quantity"), species_of(cond),
            str(cond.get("process_step") or "") or None)


def _numeric(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and _NUM.match(v):
        return float(v)
    return None


def _same_value(a, b):
    """(verdict, detail) for two condition values, converting units where possible."""
    va, vb = _numeric(a.get("value")), _numeric(b.get("value"))
    ua, ub = (a.get("unit") or None), (b.get("unit") or None)
    if va is None or vb is None:
        # not numeric on at least one side: only an exact literal match is defensible
        if str(a.get("value")) == str(b.get("value")) and ua == ub:
            return True, {"basis": "identical literal value"}
        if ua and ub and ua != ub:
            return None, {"basis": "values are not numeric, so unit-compatible "
                                   "conditions cannot be compared by magnitude"}
        return False, {"basis": "differing non-numeric values"}
    if ua == ub:
        return va == vb, {"basis": "same unit"}
    if not ua or not ub:
        return None, {"basis": "one side carries no unit, so magnitudes are not "
                               "comparable"}
    try:
        conv = U.convert(va, ua, ub)
    except Exception:
        conv = None
    if conv is None:
        return None, {"basis": "units %r and %r are not convertible" % (ua, ub)}
    return conv == vb, {"basis": "converted %s %s -> %s %s" % (va, ua, conv, ub),
                        "unit_converted": True}


def compare_conditions(a, b):
    """How two conditions relate. Returns (outcome, detail).

    Precision first at every branch: a difference is only reported when it is known, and
    an unknown is reported as unknown rather than resolved in whichever direction would
    produce an answer.
    """
    ka, kb = condition_key(a), condition_key(b)
    if ka[0] != kb[0]:
        return DIFFERENT_QUANTITY, {"a": ka, "b": kb}
    if ka[2] != kb[2]:
        return DIFFERENT_STEP, {"a": ka, "b": kb}
    if ka[1] is None or kb[1] is None:
        # MISSING is not SAME. One side names its reagent and the other does not, or
        # neither does; either way there is no evidence these are the same control.
        return SPECIES_UNRESOLVED, {
            "a_species": ka[1], "b_species": kb[1],
            "basis": "at least one condition has no attributed species, so the two "
                     "cannot be shown to control the same reagent"}
    if ka[1] != kb[1]:
        return DIFFERENT_SPECIES, {"a_species": ka[1], "b_species": kb[1]}
    same, detail = _same_value(a, b)
    if same is None:
        return (UNIT_CONVERTIBLE if detail.get("basis", "").startswith("values are not")
                else NOT_COMPARABLE), detail
    return (EXACT_MATCH if same else SAME_CONDITION_DIFFERENT_VALUE), detail


# --- loading ----------------------------------------------------------------------
def load_cases(corpus_dir):
    """Every ExperimentalCase under `corpus_dir`, each tagged with its paper."""
    out = []
    for p in sorted(Path(corpus_dir).glob("*/semantic/experimental_cases.json")):
        d = json.loads(p.read_text())
        for c in (d.get("experimental_cases", d) if isinstance(d, dict) else d):
            c = dict(c)
            c.setdefault("paper_id", p.parents[1].name)
            out.append(c)
    return out


def conditions_of(case):
    return case.get("case_defining_conditions") or []


def _provenance(case, cond):
    """Enough to answer: which paper, which case, which condition, on what evidence."""
    return {"paper_id": case.get("paper_id"), "case_id": case.get("case_id"),
            "quantity": cond.get("quantity"), "species": species_of(cond),
            "process_step": cond.get("process_step"),
            "value": cond.get("value"), "unit": cond.get("unit"),
            "raw_axis_label": cond.get("raw_axis_label"),
            "species_basis": cond.get("species_basis"),
            "species_evidence": cond.get("species_evidence"),
            "condition_evidence": cond.get("evidence"),
            "source": cond.get("source"), "provenance_type": cond.get("provenance_type"),
            "nominal_fingerprint": case.get("nominal_fingerprint")}


# --- query primitives -------------------------------------------------------------
def cases_with_condition(cases, quantity, species=None, value=None, unit=None,
                         require_species=True):
    """Cases carrying `quantity` for `species`, optionally at a value.

    `require_species` is the precision switch: by default a requested species must be
    ATTRIBUTED on the condition, so unattributed conditions are not swept into an answer
    about a named reagent. Setting it False widens the question to "this quantity,
    species unknown or matching", and the caller is told which it got.
    """
    hits = []
    for c in cases:
        for cond in conditions_of(c):
            if cond.get("quantity") != quantity:
                continue
            sp = species_of(cond)
            if species is not None:
                if sp is None and require_species:
                    continue
                if sp is not None and sp != species:
                    continue
            if value is not None:
                same, det = _same_value(cond, {"value": value, "unit": unit or cond.get("unit")})
                if same is not True:
                    continue
            p = _provenance(c, cond)
            p["species_resolved"] = sp is not None
            hits.append(p)
    return hits


def condition_inventory(cases):
    """Every distinct (quantity, species, step) with where it occurs."""
    inv = {}
    for c in cases:
        for cond in conditions_of(c):
            k = condition_key(cond)
            e = inv.setdefault(k, {"quantity": k[0], "species": k[1], "process_step": k[2],
                                   "cases": set(), "papers": set(), "units": set(),
                                   "values": set()})
            e["cases"].add((c.get("paper_id"), c.get("case_id")))
            e["papers"].add(c.get("paper_id"))
            if cond.get("unit"):
                e["units"].add(cond["unit"])
            e["values"].add(str(cond.get("value")))
    return [{"quantity": v["quantity"], "species": v["species"],
             "process_step": v["process_step"], "n_cases": len(v["cases"]),
             "n_papers": len(v["papers"]), "units": sorted(v["units"]),
             "n_distinct_values": len(v["values"]),
             "papers": sorted(v["papers"])}
            for v in inv.values()]


def cases_varying_condition(cases, quantity=None, species=None, min_values=2,
                            require_species=True):
    """Sweeps: one condition identity taking several values across cases of a paper.

    Identity, not label similarity -- a sweep of the SnI4 pulse is not the same sweep as
    the H2O pulse even though both are drawn as "pulse time".
    """
    groups = {}
    for c in cases:
        for cond in conditions_of(c):
            k = condition_key(cond)
            if quantity and k[0] != quantity:
                continue
            if species is not None and k[1] != species:
                continue
            if require_species and k[1] is None:
                continue
            groups.setdefault((c.get("paper_id"),) + k, []).append((c, cond))
    out = []
    for k, members in groups.items():
        vals = {str(cond.get("value")) for _, cond in members}
        if len(vals) < min_values:
            continue
        out.append({"paper_id": k[0], "quantity": k[1], "species": k[2],
                    "process_step": k[3], "n_values": len(vals),
                    "values": sorted(vals, key=lambda v: (_numeric(v) is None,
                                                          _numeric(v) or 0, v)),
                    "n_cases": len(members),
                    "cases": [_provenance(c, cond) for c, cond in members]})
    return sorted(out, key=lambda x: (-x["n_values"], x["paper_id"]))


def compare_cases(a, b, focus=None):
    """How two cases relate condition by condition.

    `focus` is an optional (quantity, species) the caller expects to differ. The verdict
    separates what was PROVEN from what merely was not contradicted: a case carrying an
    unresolved or unshared condition cannot support "these differ only in X", however
    well the shared conditions line up.
    """
    ka = {condition_key(x): x for x in conditions_of(a)}
    kb = {condition_key(x): x for x in conditions_of(b)}
    shared, only_a, only_b = [], [], []
    for k in ka:
        (shared if k in kb else only_a).append(k)
    only_b = [k for k in kb if k not in ka]
    results = {}
    for k in shared:
        results[k] = compare_conditions(ka[k], kb[k])
    differing = [k for k, (o, _) in results.items() if o == SAME_CONDITION_DIFFERENT_VALUE]
    unresolved = [k for k, (o, _) in results.items()
                  if o in (SPECIES_UNRESOLVED, UNIT_CONVERTIBLE, NOT_COMPARABLE)]
    verdict = MATCH_ON_SHARED_CONDITIONS
    if focus is not None:
        want = [k for k in differing if (k[0], k[1]) == tuple(focus)]
        if (want and len(differing) == len(want) and not unresolved
                and not only_a and not only_b):
            verdict = PROVEN_DIFFER_ONLY_IN
    return {"a": {"paper_id": a.get("paper_id"), "case_id": a.get("case_id")},
            "b": {"paper_id": b.get("paper_id"), "case_id": b.get("case_id")},
            "verdict": verdict,
            "differing": [list(k) for k in differing],
            "unresolved": [list(k) for k in unresolved],
            "only_in_a": [list(k) for k in only_a],
            "only_in_b": [list(k) for k in only_b],
            "outcomes": {"|".join(str(x) for x in k): o for k, (o, _) in results.items()}}


def cases_differing_only_in(cases, quantity, species=None, same_paper=True):
    """Case pairs whose shared conditions agree except the requested one.

    Reported with the verdict attached rather than filtered to the strong answer, because
    the weaker one -- shared conditions agree, something else is unknown -- is a real and
    useful result that must not be dressed up as the strong one.
    """
    out = []
    for i, a in enumerate(cases):
        for b in cases[i + 1:]:
            if same_paper and a.get("paper_id") != b.get("paper_id"):
                continue
            r = compare_cases(a, b, focus=(quantity, species))
            if not r["differing"]:
                continue
            if not any(k[0] == quantity and (species is None or k[1] == species)
                       for k in [tuple(x) for x in r["differing"]]):
                continue
            out.append(r)
    return out
