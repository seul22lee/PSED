#!/usr/bin/env python3
"""
pilot_cases.py — case candidate construction, sweep normalisation, and evidence-gated
cross-result identity resolution.

Three rules govern everything here, and they are the reason the module exists:

  1. A case candidate produced from a sweep carries ITS OWN value of the swept quantity.
     `case00 / case01 / case02` is not an identity; `deposition_temperature = 100 C` is.

  2. Two candidates may only be merged when the source gives POSITIVE LINKAGE EVIDENCE,
     the case-defining conditions are COMPATIBLE, and nothing CONTRADICTS. Missing is
     never the same as equal.

  3. A measurement setting never defines a case, and a plot representation never creates
     one.

No DOI, paper id or figure number appears in any decision.
"""
import re
from collections import defaultdict

import pilot_design as D
from pipeline.canonical import conditions as CC
import pilot_roles as R

EXPLICIT = "EXPLICIT"
SUPPORTED = "SUPPORTED"
UNRESOLVED = "UNRESOLVED"


def _num(v):
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def _fmt(v):
    f = _num(v)
    if f is None:
        return str(v)
    return ("%g" % f)


# ------------------------------------------------------------------ sweep expansion
def sweep_cases(entity, scope_text="", methods_text="", material=None, step=None):
    """One case candidate per DESIGN BRANCH of a plotted sweep.

    The resolver used to gate this on `experimental_case_status == independent_process_sweep`
    and on the resolver's own case count. That gate is what produced the JES under-split: a
    saturation panel plotting GPC against six dose values was typed `supported` with a count
    of 1, so the six depositions the author performed became one case.

    The gate is now the AXIS ROLE. A case-defining process setting yields one branch per
    distinct plotted value; a progression axis (thickness vs cycle number) yields none,
    because those points track one growth; a measurement coordinate yields none.

    Returns (candidates, role, basis, note, design).
    """
    design, branches, role, basis = D.design_from_sweep(entity, scope_text, methods_text,
                                                        material=material, step=step)
    if design is None:
        return [], role, basis, ("axis role %s: no design branches" % role), None
    n = entity.get("experimental_case_count") or 0
    if n and n != len(branches):
        design["resolver_count_disagrees"] = n
    return branches, role, basis, None, design


# ------------------------------------------------------------------ chemistry identity
def chemistry_conditions(paper_chem, series_label, panel_clause, preamble):
    """Case-defining CHEMISTRY read from the source scope.

    A series legend that is simply the precursor name ("HDMP" / "MeCpPtMe3") is the
    paper telling you which chemistry that curve used, and two curves using different
    precursors are different deposition cases however well their other conditions agree.
    The resolver leaves `precursors` empty for these entities, so without this the two
    precursor series of one panel are indistinguishable.

    Only species the PAPER ITSELF names (`paper_chem`) can be matched, so no chemistry is
    ever invented from an arbitrary legend string.
    """
    out = []
    for role, names in sorted(paper_chem.items()):
        for name in sorted(names or [], key=len, reverse=True):
            if not name:
                continue
            rx = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(name), re.I)
            for scope, text, prov in (("series_legend", series_label, "directly_stated"),
                                      ("panel_caption_clause", panel_clause, "directly_stated"),
                                      ("figure_caption", preamble, "directly_stated")):
                if text and rx.search(text):
                    out.append({"quantity": role, "value": name, "unit": None,
                                "role": R.CASE_DEFINING,
                                "role_basis": "process chemistry named by the source scope",
                                "provenance_type": prov, "source": scope,
                                "evidence": "%r names %r, one of the paper's %s"
                                            % (str(text)[:120], name, role)})
                    break
            else:
                continue
            break
    return out


# ------------------------------------------------------------ candidate construction
def entity_conditions(entity):
    """The entity's bound conditions, split by role. Every record keeps its provenance."""
    case_defining, measurement, other = [], [], []
    for b in entity.get("bound_conditions") or []:
        q = b.get("quantity")
        # Impossible magnitudes are refused at the FIRST deterministic read of the
        # persisted conditions, so no case-minting path can carry one: a written range
        # whose hyphen was read as a minus sign is restored to the range its own evidence
        # still shows, and a negative duration with no such evidence is dropped rather
        # than propagated. Quantities whose semantics permit a negative value are untouched.
        _v, _rng, _why = CC.sanitize_magnitude(q, b.get("value"), b.get("raw_evidence"))
        if _why:
            b = dict(b, value=_v, sanitized_reason=_why)
            if _rng:
                b.update(value_kind="range", value_lower=_rng[0], value_upper=_rng[1])
            # a refused magnitude is never a deleted ASSERTION: the record stays, carrying
            # its evidence and the reason its value was withheld, so the loss is visible
            # rather than silent
        # A magnitude qualified by a comparator in its own evidence is a BOUND, not a
        # setting: "<2 Torr" states a limit the process stayed under, and recording it as
        # an equality asserts a value the source never gave.
        _bound = CC.bound_in_evidence(b.get("value"), b.get("raw_evidence"))
        if _bound:
            b = dict(b, value_kind="bound", bound_comparator=_bound,
                     bound_value=b.get("value"), value=None,
                     bound_reason="the source states this magnitude as a bound (%r), not "
                                  "as a fixed value" % _bound)
            continue
        # A role-qualified quantity whose role its own evidence never mentions is a number
        # that landed on the wrong physical quantity.
        if CC.role_unsupported_by_evidence(q, b.get("raw_evidence")):
            continue
        # ... and a numeric condition whose own evidence does not contain its number was
        # not read from that sentence, so the pairing cannot be checked and is refused.
        if not CC.value_supported_by_evidence(b.get("value"), b.get("raw_evidence")):
            continue
        # a unit token captured as a chemical is not a species qualification
        if CC.species_is_a_unit(b.get("species") or b.get("of_reactant")):
            b = dict(b, species=None, of_reactant=None)
        role, basis = R.condition_role(q, None, b.get("evidence_kind"), None)
        rec = {"quantity": q, "value": b.get("value"), "unit": b.get("unit"),
               "role": role, "role_basis": basis,
               "provenance_type": ("methods_default" if b.get("source_kind") == "methods"
                                   else "paper_default"
                                   if b.get("bound_at_scope") == "paper"
                                   else "directly_stated"),
               "source": b.get("source_kind"), "scope": b.get("bound_at_scope"),
               "assertion_status": b.get("assertion_status"),
               "species": b.get("species") or b.get("of_reactant"),
               "evidence": (b.get("raw_evidence") or "")[:220],
               "locator": b.get("evidence_locator")}
        (case_defining if role == R.CASE_DEFINING
         else measurement if role == R.MEASUREMENT_SETTING else other).append(rec)
    return case_defining, measurement, other


# ------------------------------------------------------- condition specificity ladder
#: How SPECIFIC a condition record is to the thing it describes. A value stated for one
#: specimen outranks one stated for a figure, which outranks a methods default, which
#: outranks a paper-wide default. Specificity is not confidence: a paper default may be
#: perfectly true and still lose to a row of the specimen table that speaks about exactly
#: this specimen.
PROVENANCE_RANK = {
    "sample_table_direct": 60,
    "derived_from_table_recipe": 58,
    "inherited_from_sample": 55,
    "directly_stated": 50,
    #: a panel's own caption clause speaks about exactly that panel's results --
    #: more specific than a figure-wide statement, less than a specimen-table row
    "panel_caption_direct": 52,
    "figure_local_direct": 50,
    "directly_stated_range": 50,
    "derived_from_design_branch": 48,
    "derived_from_sweep_axis": 46,
    "inherited_from_explicit_sample": 55,
    "methods_default": 20,
    "paper_default": 10,
}
#: An unrecognised provenance sits between a default and a direct statement, so a new
#: source can never silently outrank the specimen table nor be discarded as a default.
UNRANKED_PROVENANCE = 30


def provenance_rank(cond):
    return PROVENANCE_RANK.get(cond.get("provenance_type"), UNRANKED_PROVENANCE)


def resolve_conditions(conds):
    """One record per (quantity, species), keeping the most specific evidence.

    Two sources disagreeing about the same quantity is only a scientific contradiction
    when they are equally specific. A methods default of 500 cycles and a specimen table
    row of 1000 cycles for the SAME specimen are not a conflict in the world -- the
    default simply does not apply to this specimen. Treating it as one blocked every
    merge between a figure result and the specimen it was measured on.

    The losing record is kept on the winner as `superseded`, so nothing is discarded.
    """
    best, order = {}, []
    for c in conds:
        q = c.get("quantity")
        if not q:
            continue
        k = (q, c.get("species") or "")
        if k not in best:
            best[k] = dict(c)
            order.append(k)
            continue
        cur = best[k]
        if provenance_rank(c) > provenance_rank(cur):
            win, lose = dict(c), cur
        else:
            win, lose = cur, c
        same = (value_token(win) == value_token(lose)
                and _unit_key(win.get("unit")) == _unit_key(lose.get("unit")))
        if not same and provenance_rank(win) > provenance_rank(lose):
            hist = list(win.get("superseded") or [])
            hist.append({"value": lose.get("value"), "unit": lose.get("unit"),
                         "provenance_type": lose.get("provenance_type"),
                         "source": lose.get("source"),
                         "evidence": lose.get("evidence"),
                         "reason": "superseded by more specific %s evidence"
                                   % win.get("provenance_type")})
            win["superseded"] = hist
        elif not same:
            # equally specific and disagreeing: a real conflict, kept visible
            win = dict(win)
            win["conflicting_values"] = sorted(
                {_fmt(win.get("value")), _fmt(lose.get("value"))})
        best[k] = win
    return [best[k] for k in order]


def _cond_key(conds):
    """Comparable fingerprint of a set of case-defining conditions.

    Species is part of the key: a 5 s TMA pulse and a 5 s water pulse are different
    settings of different reactants, not one condition."""
    d = {}
    for c in resolve_conditions(conds):
        tok = value_token(c)
        if tok is None or not c.get("quantity"):
            continue
        d[(c["quantity"], c.get("species") or "")] = (tok, _unit_key(c.get("unit")))
    return d


def value_token(cond):
    """The comparable token of a condition's VALUE, whatever its structure.

    A condition is not always a scalar: sources state ranges ("10-40 cycles"),
    bounds ("<2 Torr"), lists and categorical settings. Each structure gets a
    deterministic token so identity, dedup and fingerprints can carry it -- a range
    must never fingerprint as nothing merely because the scalar slot is null.

        scalar        "0.4"
        range         "10..40"
        bound         "<2"
        list/set      "a|b|c"   (order-independent)
        categorical   the text itself
    """
    vk = cond.get("value_kind")
    lo, hi = cond.get("value_lower"), cond.get("value_upper")
    if vk == "range" or (lo is not None and hi is not None
                         and cond.get("value") is None):
        return "%s..%s" % (_fmt(lo), _fmt(hi))
    if vk == "bound" and cond.get("bound_value") is not None:
        return "%s%s" % (cond.get("bound_comparator") or "<",
                         _fmt(cond.get("bound_value")))
    v = cond.get("value")
    if isinstance(v, (list, tuple, set, frozenset)):
        return "|".join(sorted(_fmt(x) for x in v))
    return _fmt(v) if v is not None else None


def _material_key(m):
    """A material token reduced to its chemical identity for comparison.

    Canonical identity where the chemistry layer resolves it, a normalised spelling
    otherwise -- so "SiO2" and "SiO 2" are one material and a resolver upgrade
    tightens rather than changes this comparison.
    """
    try:
        from pipeline.canonical import chemical_identity as _CI
        k = _CI.identity_key(str(m), None)
        if k:
            return k
    except Exception:
        pass
    return re.sub(r"[\s_\-]+", "", str(m or "")).lower()


def _unit_key(u):
    """A unit reduced to what it MEANS, so spelling cannot fake a contradiction.

    A legend printing "500 cycles" and a table column parsed as "cycle" are the same
    condition. Comparing the raw strings reported them as a clash and blocked every
    otherwise-supported merge between a figure result and its tabulated specimen.
    """
    u = re.sub(r"[\s.]+", "", str(u or "")).lower()
    return u[:-1] if len(u) > 2 and u.endswith("s") else u


def compatibility(a, b):
    """(verdict, reasons) for two condition fingerprints.

    COMPATIBLE  — every shared quantity agrees.
    CONTRADICTS — at least one shared quantity disagrees.
    Quantities present on only one side are reported as `unknown_on_one_side` and are
    explicitly NOT treated as agreement.
    """
    shared = set(a) & set(b)
    agree, clash, unknown = [], [], sorted(set(a) ^ set(b))
    for k in sorted(shared):
        if a[k][0] == b[k][0] and (a[k][1] or "") == (b[k][1] or ""):
            agree.append({"quantity": k[0], "species": k[1], "value": a[k][0], "unit": a[k][1]})
        else:
            clash.append({"quantity": k[0], "species": k[1],
                          "left": "%s %s" % a[k], "right": "%s %s" % b[k]})
    verdict = "CONTRADICTS" if clash else "COMPATIBLE"
    return verdict, {"agree": agree, "clash": clash,
                     "unknown_on_one_side": [{"quantity": q, "species": s}
                                             for q, s in unknown]}


# ------------------------------------------------------------------ identity resolver
def resolve_cases(candidates, links):
    """Group case candidates into ExperimentalCases.

    `links` is a list of positive-linkage records:
        {"a": cand_id, "b": cand_id, "strength": EXPLICIT|SUPPORTED, "evidence": ...}

    A pair is merged only when a link exists AND the conditions do not contradict. Two
    candidates that merely happen to share conditions are NEVER merged: without a link
    record they stay separate and the pair is reported as an unresolved link instead.

    Returns (groups, decisions). `groups` is a list of lists of candidate ids.
    """
    by_id = {c["candidate_id"]: c for c in candidates}
    parent = {cid: cid for cid in by_id}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    decisions = []
    for lk in sorted(links, key=lambda l: (l["strength"] != EXPLICIT, l["a"], l["b"])):
        a, b = lk["a"], lk["b"]
        if a not in by_id or b not in by_id:
            continue
        # The deposition TARGET material is case-defining. Two candidates whose own
        # resolved single target materials positively differ are two different
        # deposition contexts however strong the specimen link between them: a physical
        # specimen can realise several depositions (a multilayer, a stack, sequential
        # stages), so "same sample" is specimen identity and never case identity. A
        # candidate with no target of its own, or with multi-material scope evidence
        # only, blocks nothing -- missing is not different.
        ma = by_id[a].get("deposited_material")
        mb = by_id[b].get("deposited_material")
        if ma and mb and _material_key(ma) != _material_key(mb):
            decisions.append({"a": a, "b": b, "action": "BLOCKED",
                              "strength": lk["strength"],
                              "reason": "different deposition target materials",
                              "detail": {"a_material": ma, "b_material": mb,
                                         "note": ("specimen identity does not imply "
                                                  "case identity; the two results "
                                                  "target different deposited "
                                                  "materials")},
                              "link_evidence": lk.get("evidence")})
            continue
        ka = _cond_key(by_id[a]["case_conditions"])
        kb = _cond_key(by_id[b]["case_conditions"])
        verdict, detail = compatibility(ka, kb)
        if verdict == "CONTRADICTS":
            decisions.append({"a": a, "b": b, "action": "BLOCKED",
                              "strength": lk["strength"], "reason": "contradictory "
                              "case-defining conditions", "detail": detail,
                              "link_evidence": lk.get("evidence")})
            continue
        if find(a) == find(b):
            decisions.append({"a": a, "b": b, "action": "ALREADY_LINKED",
                              "strength": lk["strength"], "detail": detail,
                              "link_evidence": lk.get("evidence")})
            continue
        union(a, b)
        decisions.append({"a": a, "b": b, "action": "MERGED", "strength": lk["strength"],
                          "reason": lk.get("reason"), "detail": detail,
                          "link_evidence": lk.get("evidence")})

    groups = defaultdict(list)
    for cid in by_id:
        groups[find(cid)].append(cid)
    return [sorted(v) for v in groups.values()], decisions


def unresolved_pairs(candidates, merged_groups, max_report=400):
    """Pairs that share every known case-defining condition but were never linked.

    These are exactly the merges the evidence rule declines to make. Reporting them is
    the point: an unresolved link is the honest answer, and the reviewer can see what
    evidence would have been needed.
    """
    member_of = {}
    for i, g in enumerate(merged_groups):
        for cid in g:
            member_of[cid] = i
    keyed = defaultdict(list)
    for c in candidates:
        k = _cond_key(c["case_conditions"])
        if not k:
            continue
        keyed[tuple(sorted((q, s, v, u) for (q, s), (v, u) in k.items()))].append(c)
    out = []
    for _, group in keyed.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if member_of.get(a["candidate_id"]) == member_of.get(b["candidate_id"]):
                    continue
                if (a.get("source_figure"), a.get("source_panel")) == \
                        (b.get("source_figure"), b.get("source_panel")):
                    continue
                out.append({
                    "a": a["candidate_id"], "b": b["candidate_id"],
                    "a_figure": a.get("source_figure"), "b_figure": b.get("source_figure"),
                    "shared_conditions": [{"quantity": q, "species": s, "value": v, "unit": u}
                                          for (q, s), (v, u) in _cond_key(a["case_conditions"]).items()],
                    "status": UNRESOLVED,
                    "reason": "case-defining conditions agree, but the source states no "
                              "positive linkage (same sample / same run / shared sample "
                              "code) between these results; missing is not the same as same",
                })
                if len(out) >= max_report:
                    return out
    return out
