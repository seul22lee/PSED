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
def sweep_cases(entity):
    """One case candidate per distinct swept value, each carrying that value.

    HOW MANY settings a digitised curve really represents is an extraction-quality
    question the resolver already answers (`experimental_case_status` /
    `experimental_case_count`, guarded by MAX_UNENUMERATED_SETTINGS so a densely
    digitised line is not read as N films). That verdict is reused verbatim.

    WHICH setting each case carries is the question this function exists to answer, and
    the one the current pipeline never answers: `case00 / case01 / case02` becomes
    `deposition_temperature = 100 / 150 / 200 C`.

    Returns (candidates, role, basis, note).
    """
    q = entity.get("coordinate")
    role, basis = R.condition_role(q, (entity.get("x_semantics") or {}).get("raw_label"),
                                   None, entity.get("x_axis_role"))
    status = entity.get("experimental_case_status")
    n = entity.get("experimental_case_count") or 0
    if status != "independent_process_sweep" or n < 2:
        return [], role, basis, "not an independent process sweep (status %r)" % status
    if role != R.CASE_DEFINING:
        # the resolver called it a process sweep, but the axis is an instrument axis
        return [], role, ("%s; sweep NOT expanded because the axis is a measurement "
                          "setting" % basis), "axis role blocks case expansion"
    xs = []
    for o in entity.get("observations") or []:
        v = _num(o.get("x_canonical"))
        if v is None:
            v = _num(o.get("x_raw"))
        if v is not None:
            xs.append(v)
    seen, vals = set(), []
    for v in xs:
        k = round(v, 6)
        if k not in seen:
            seen.add(k)
            vals.append(v)
    vals.sort()
    if len(vals) != n:
        # the resolver's count and the distinct digitised x values disagree; assigning a
        # value per case would be a guess, so no value is attached and the mismatch is
        # reported instead of hidden
        return [], role, basis, ("resolver counted %d cases but %d distinct x values were "
                                 "digitised; per-case values not assigned" % (n, len(vals)))
    unit = entity.get("coordinate_unit")
    out = []
    for v in vals:
        out.append({"quantity": q, "value": v, "unit": unit,
                    "role": R.CASE_DEFINING, "role_basis": basis,
                    "provenance_type": "derived_from_sweep_axis",
                    "evidence": "x = %s %s is one of the %d separately prepared settings the "
                                "resolver resolved for this %s axis"
                                % (_fmt(v), unit or "", n, entity.get("x_axis_role")),
                    "source": "sweep_axis"})
    return out, role, basis, None


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
        role, basis = R.condition_role(q, None, b.get("evidence_kind"), None)
        rec = {"quantity": q, "value": b.get("value"), "unit": b.get("unit"),
               "role": role, "role_basis": basis,
               "provenance_type": ("methods_default" if b.get("source_kind") == "methods"
                                   else "directly_stated"),
               "source": b.get("source_kind"), "scope": b.get("bound_at_scope"),
               "assertion_status": b.get("assertion_status"),
               "species": b.get("species") or b.get("of_reactant"),
               "evidence": (b.get("raw_evidence") or "")[:220],
               "locator": b.get("evidence_locator")}
        (case_defining if role == R.CASE_DEFINING
         else measurement if role == R.MEASUREMENT_SETTING else other).append(rec)
    return case_defining, measurement, other


def _cond_key(conds):
    """Comparable fingerprint of a set of case-defining conditions.

    Species is part of the key: a 5 s TMA pulse and a 5 s water pulse are different
    settings of different reactants, not one condition."""
    d = {}
    for c in conds:
        if c.get("value") is None or not c.get("quantity"):
            continue
        d[(c["quantity"], c.get("species") or "")] = (_fmt(c["value"]), c.get("unit") or "")
    return d


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
