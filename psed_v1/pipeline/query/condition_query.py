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

from ontology import vocab as _vocab
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

#: why a pair fell short of the strong verdict, so "not proven" is never just a shrug
UNRESOLVED_REACTANT_QUALIFIER = "UNRESOLVED_REACTANT_QUALIFIER"
UNIT_NOT_COMPARABLE = "UNIT_NOT_COMPARABLE"
EXTRA_CONDITION = "EXTRA_CONDITION"
MISSING_CONDITION = "MISSING_CONDITION"
VALUE_DIFFERENCE_OUTSIDE_TARGET = "VALUE_DIFFERENCE_OUTSIDE_TARGET"


def requires_species(quantity):
    """Whether the ontology makes the reagent part of this quantity's identity."""
    return _vocab.quantity_requires_species(quantity)

_NUM = re.compile(r"^\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*$")


def species_of(cond):
    """The canonical species, or None. Empty string is absence, not a species."""
    s = cond.get("species")
    s = str(s).strip() if s is not None else ""
    return s or None


def _value_token(cond):
    """A hashable token that is equal exactly when two values are physically equal."""
    n = normalized_value(cond)
    return "%s|%s" % n if n else "raw:%s|%s" % (cond.get("value"), cond.get("unit") or "")


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


def units_compatible(ua, ub):
    """Whether two unit strings belong to the same convertible dimension.

    Differing spellings are not incompatibility and differing dimensions are not a
    conversion problem; only the unit system can tell them apart, so it is asked rather
    than guessed at from the strings.
    """
    if not ua or not ub:
        return ua == ub          # both absent is compatible; one absent is not
    if str(ua) == str(ub):
        return True
    try:
        return bool(U.same_dimension(ua, ub))
    except Exception:
        return False


def normalized_value(cond):
    """(dimension, magnitude) for a condition, or None when it has no physical value.

    The one place any part of this module decides whether two values are the same
    quantity of the same thing. 500 ms and 0.5 s are one physical value; 1 ms and 1 s are
    two, though both print as "1". Comparison, sweep detection and the inventory all read
    this, so they cannot drift into disagreeing about what "distinct" means.
    """
    v = _numeric(cond.get("value"))
    if v is None:
        return None
    u = cond.get("unit") or None
    if not u:
        return ("", v)           # a bare number is only ever equal to another bare number
    try:
        # reduce to the dimension's own SI reference, which is what `convert` does
        # internally -- comparing within each unit's own spelling would make 1 ms and
        # 1 s equal and 500 ms and 0.5 s different, the exact inversion of the physics
        fu = U.parse(u)
        return (U.DIM_NAME.get(fu.dimension, fu.dimension),
                float(v) * fu.factor + fu.offset)
    except Exception:
        return (str(u), v)       # unknown unit: comparable only to the same unit string


def _same_value(a, b):
    """(verdict, detail) for two condition values. None means 'cannot be decided'."""
    na, nb = normalized_value(a), normalized_value(b)
    ua, ub = (a.get("unit") or None), (b.get("unit") or None)
    if na is None or nb is None:
        # not numeric on at least one side: only an exact literal match is defensible
        if str(a.get("value")) == str(b.get("value")) and ua == ub:
            return True, {"basis": "identical literal value"}
        if units_compatible(ua, ub) and ua and ub:
            return None, {"basis": "values are not numeric, so unit-compatible "
                                   "conditions cannot be compared by magnitude",
                          "units_compatible": True}
        return None, {"basis": "units %r and %r are not of one dimension" % (ua, ub),
                      "units_compatible": False}
    if na[0] != nb[0]:
        # different dimensions, or a bare number against a dimensional one: equal
        # magnitudes here would be a coincidence of digits, not a physical equality
        return None, {"basis": "units %r and %r are not of one dimension" % (ua, ub),
                      "units_compatible": False}
    return na[1] == nb[1], {"basis": "compared as %s: %s vs %s" % (na[0] or "bare number",
                                                                  na[1], nb[1]),
                            "unit_converted": str(ua) != str(ub)}


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
    if ka[1] is not None and kb[1] is not None:
        if ka[1] != kb[1]:
            return DIFFERENT_SPECIES, {"a_species": ka[1], "b_species": kb[1]}
    elif ka[1] is not None or kb[1] is not None:
        # One side names its reagent and the other does not. MISSING is not SAME, whatever
        # the ontology says about this quantity: a stated difference must not be dropped
        # just because the quantity does not oblige anyone to state it.
        return SPECIES_UNRESOLVED, {
            "a_species": ka[1], "b_species": kb[1], "reason": UNRESOLVED_REACTANT_QUALIFIER,
            "basis": "one condition names its reagent and the other does not, so they "
                     "cannot be shown to control the same chemical"}
    elif requires_species(ka[0]):
        # Neither names a reagent, and for THIS quantity the ontology says the reagent is
        # part of what identifies the condition -- a pulse belongs to one reactant's
        # valve. Two unattributed pulses are not thereby the same pulse.
        return SPECIES_UNRESOLVED, {
            "a_species": None, "b_species": None, "reason": UNRESOLVED_REACTANT_QUALIFIER,
            "basis": "%r is qualified by reactant in the ontology and neither condition "
                     "names one" % ka[0]}
    # Either both name the same reagent, or the quantity does not need one: a deposition
    # temperature is complete without a chemical, so its absence is not missing evidence.
    same, detail = _same_value(a, b)
    if same is None:
        return (UNIT_CONVERTIBLE if detail.get("units_compatible")
                else NOT_COMPARABLE), detail
    return (EXACT_MATCH if same else SAME_CONDITION_DIFFERENT_VALUE), detail


# --- loading ----------------------------------------------------------------------
ACTIVE8 = "ACTIVE8"
EXCLUDED_DEVELOPMENT = "EXCLUDED_DEVELOPMENT"


def load_cases(corpus_dir, scope=ACTIVE8, roster=None):
    """ExperimentalCases under `corpus_dir`, restricted to one corpus scope.

    A development paper sitting in the same directory is not part of the corpus any
    headline number describes, and silently folding it in makes every count a little bit
    about something the corpus excluded. The roster file is the authority on membership;
    `scope=None` returns everything, each case tagged so a caller can still separate them.
    """
    roster = Path(roster) if roster else Path(corpus_dir).parent / "pilot_papers.json"
    members = set(json.loads(roster.read_text())["papers"]) if roster.exists() else None
    out = []
    for p in sorted(Path(corpus_dir).glob("*/semantic/experimental_cases.json")):
        pid = p.parents[1].name
        sc = ACTIVE8 if (members is None or pid in members) else EXCLUDED_DEVELOPMENT
        if scope is not None and sc != scope:
            continue
        d = json.loads(p.read_text())
        for c in (d.get("experimental_cases", d) if isinstance(d, dict) else d):
            c = dict(c)
            c.setdefault("paper_id", pid)
            c["corpus_scope"] = sc
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
            e["values"].add(_value_token(cond))
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
        vals = {_value_token(cond) for _, cond in members}
        if len(vals) < min_values:
            continue
        out.append({"paper_id": k[0], "quantity": k[1], "species": k[2],
                    "process_step": k[3], "n_values": len(vals),
                    "values": sorted(vals, key=lambda v: (_numeric(v) is None,
                                                          _numeric(v) or 0, v)),
                    "raw_values": sorted({str(cond.get("value")) for _, cond in members}),
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
    verdict, blockers = MATCH_ON_SHARED_CONDITIONS, []
    if focus is not None:
        want = [k for k in differing if (k[0], k[1]) == tuple(focus)]
        # every way the strong claim can fail, named rather than collapsed into "no"
        if any(results[k][0] == SPECIES_UNRESOLVED for k in unresolved):
            blockers.append(UNRESOLVED_REACTANT_QUALIFIER)
        if any(results[k][0] in (UNIT_CONVERTIBLE, NOT_COMPARABLE) for k in unresolved):
            blockers.append(UNIT_NOT_COMPARABLE)
        if only_b:
            blockers.append(EXTRA_CONDITION)
        if only_a:
            blockers.append(MISSING_CONDITION)
        if len(differing) != len(want):
            blockers.append(VALUE_DIFFERENCE_OUTSIDE_TARGET)
        if want and not blockers:
            verdict = PROVEN_DIFFER_ONLY_IN
    return {"a": {"paper_id": a.get("paper_id"), "case_id": a.get("case_id")},
            "b": {"paper_id": b.get("paper_id"), "case_id": b.get("case_id")},
            "verdict": verdict, "blockers": sorted(set(blockers)),
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
