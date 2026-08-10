#!/usr/bin/env python3
"""
audit.py — corpus-level audit of the canonical layer (spec §11, §12).

Writes to psed_v1/reports/canonical/ :
    axis_semantics_audit.json / .csv     one row per curve, both axes, full provenance
    transformation_coverage.json / .csv  status/rule/group breakdown
    unresolved_transformations.json      everything with missing context / unsupported
    ambiguous_transformations.json       everything with conflicting candidates
    unit_conversion_audit.json           every unit conversion + every refusal
    context_binding_audit.json           scopes used, conflicts, paper-level reuse
    manual_review_queue.json             what a human must look at, ranked
    metrics.json                         the §12 metric block

Evidence counting rule: a paper-level assertion repeated across many experiments
counts ONCE per source assertion, never once per experiment.

Usage:
    python3 02_extraction/canonical/audit.py --all
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "canonical"

from . import sources as S                                       # noqa: E402
from . import units as U                                         # noqa: E402
from .axis_semantics import REVIEW_THRESHOLD, canon_quantity as _canon  # noqa: E402
from .schema import (REPO, Status, COMPARISON_GROUPS,             # noqa: E402
                     NORMALIZATION_DEFINITIONS, RULE_DECLS, code_version,
                     build_timestamp)

OUTPUT = REPO / "02_extraction" / "output"
REPORTS = REPO / "reports" / "canonical"

RESOLVED_STATUSES = {Status.CONVERTED, Status.ALREADY_CANONICAL}
UNRESOLVED_STATUSES = {Status.MISSING_CONTEXT, Status.UNSUPPORTED, Status.INVALID}


def load_curves(doi):
    p = OUTPUT / doi / "canonical" / "curves.json"
    if not p.exists():
        return []
    return json.loads(p.read_text()).get("curves", [])


def _axis_row(c, axis):
    sem = (c.get("semantics") or {}).get(axis) or {}
    raw = (c.get("raw") or {}).get(axis) or {}
    can = (c.get("canonical") or {}).get(axis)
    trs = [t for t in c.get("transformations") or [] if t.get("axis") == axis]
    ev = (sem.get("evidence") or [{}])[0]
    ctx_used, ctx_scopes = [], []
    for t in trs:
        for q, b in (t.get("context") or {}).items():
            ctx_used.append(q)
            if b.get("scope"):
                ctx_scopes.append("%s@%s" % (q, b["scope"]))
    status = _axis_status(trs)
    return {
        "raw_label": sem.get("raw_label"),
        "raw_quantity": raw.get("quantity"),
        "raw_unit": raw.get("unit"),
        "resolved_unit": sem.get("unit"),
        "unit_recovered": bool(sem.get("unit_recovered")),
        "resolved_meaning": sem.get("axis_kind"),
        "axis_role": sem.get("axis_role"),
        "normalization_definition": sem.get("normalization_definition"),
        "canonical_quantity": (can or {}).get("quantity"),
        "canonical_unit": (can or {}).get("unit"),
        "comparison_group": (can or {}).get("comparison_group"),
        "projections": ";".join(p.get("comparison_group") or ""
                                for p in ((c.get("projections") or {}).get(axis) or [])),
        "rules_applied": ";".join(t.get("rule_id") or "" for t in trs),
        "status": status,
        "unresolved_reason": next((t.get("unresolved_reason") for t in trs
                                   if t.get("unresolved_reason")), None),
        "context_required": ";".join(sorted(set(ctx_used))),
        "context_scope": ";".join(sorted(set(ctx_scopes))),
        "context_found": bool(ctx_scopes),
        "evidence_source": ev.get("source"),
        "evidence_span": (ev.get("span") or "")[:200] if ev else None,
        "evidence_method": ev.get("method"),
        "confidence": ev.get("confidence"),
        "needs_manual_review": bool(ev.get("needs_manual_review")),
    }


def _axis_status(trs):
    """One headline status per axis: the best outcome achieved."""
    sts = [t.get("status") for t in trs]
    for s in (Status.CONVERTED, Status.ALREADY_CANONICAL, Status.AMBIGUOUS,
              Status.MISSING_CONTEXT, Status.INVALID, Status.UNSUPPORTED,
              Status.NOT_APPLICABLE):
        if s in sts:
            return s
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--paper", action="append", default=[])
    a = ap.parse_args(argv)
    ids = a.paper or (S.papers() if a.all else [])
    if not ids:
        ap.error("pass --all or --paper <id>")
    REPORTS.mkdir(parents=True, exist_ok=True)

    rows, unresolved, ambiguous, unit_audit, review = [], [], [], [], []
    m = Counter()
    groups_hist = Counter()
    rule_hist = Counter()
    status_hist = {"x": Counter(), "y": Counter()}
    ndef_hist = Counter()
    reason_hist = Counter()
    figures, panels = set(), set()
    papers_with_fd = 0
    # paper-level assertions are counted ONCE per (paper, quantity, value, source)
    paper_scope_assertions = set()
    context_scope_hist = Counter()
    context_status_hist = Counter()

    for doi in ids:
        curves = load_curves(doi)
        if not curves:
            continue
        papers_with_fd += 1
        for c in curves:
            src = c.get("source") or {}
            figures.add((doi, src.get("figure")))
            panels.add((doi, src.get("figure"), src.get("panel")))
            m["curves"] += 1
            m["points"] += len(c.get("raw", {}).get("points") or [])
            gr = c.get("granularity") or {}
            m["granularity:" + str(gr.get("resolved_representation"))] += 1
            if gr.get("changed"):
                m["granularity_changed"] += 1

            row = {"paper": doi, "doi": doi, "figure": src.get("figure"),
                   "panel": src.get("panel"), "series": src.get("series"),
                   "curve_id": c["curve_id"],
                   "n_points": len(c.get("raw", {}).get("points") or []),
                   "source_file": src.get("source_file"),
                   "json_pointer": src.get("json_pointer"),
                   "source_checksum": src.get("source_checksum"),
                   "linked_experiments": ";".join(src.get("linked_experiment_ids") or []),
                   "previous_granularity": gr.get("previous_representation"),
                   "resolved_granularity": gr.get("resolved_representation"),
                   "granularity_changed": gr.get("changed"),
                   "reextraction_used": bool(c.get("recovery"))}
            for axis in ("x", "y"):
                ax = _axis_row(c, axis)
                status_hist[axis][ax["status"]] += 1
                if ax["raw_label"]:
                    m["%s_label_recovered" % axis] += 1
                if ax["raw_quantity"] and _canon(ax["raw_quantity"]):
                    m["%s_quantity_resolved" % axis] += 1
                if ax["comparison_group"]:
                    m["%s_semantics_resolved" % axis] += 1
                    groups_hist[ax["comparison_group"]] += 1
                if ax["normalization_definition"]:
                    ndef_hist[ax["normalization_definition"]] += 1
                if ax["unit_recovered"]:
                    m["units_recovered_from_label"] += 1
                if ax["needs_manual_review"]:
                    m["low_confidence_assignments"] += 1
                for k, v in ax.items():
                    row["%s_%s" % (axis, k)] = v
            rows.append(row)

            for t in c.get("transformations") or []:
                rule_hist[t.get("rule_id")] += 1
                st = t.get("status")
                m["tx:" + str(st)] += 1
                entry = {"curve_id": c["curve_id"], "doi": doi,
                         "figure": src.get("figure"), "panel": src.get("panel"),
                         "series": src.get("series"), "axis": t.get("axis"),
                         "rule_id": t.get("rule_id"), "rule_version": t.get("rule_version"),
                         "type": t.get("type"), "status": st,
                         "comparison_group": t.get("comparison_group"),
                         "normalization_definition": t.get("normalization_definition"),
                         "original_unit": t.get("original_unit"),
                         "canonical_unit": t.get("canonical_unit"),
                         "unresolved_reason": t.get("unresolved_reason"),
                         "context": t.get("context"),
                         "source_file": src.get("source_file"),
                         "json_pointer": src.get("json_pointer")}
                if st == Status.AMBIGUOUS:
                    ambiguous.append(entry)
                    reason_hist[_reason_key(t.get("unresolved_reason"))] += 1
                elif st in UNRESOLVED_STATUSES:
                    unresolved.append(entry)
                    reason_hist[_reason_key(t.get("unresolved_reason"))] += 1
                if t.get("type") in ("unit_conversion", "scale_conversion",
                                     "identity_canonical_mapping"):
                    unit_audit.append({
                        "curve_id": c["curve_id"], "axis": t.get("axis"),
                        "from_unit": t.get("original_unit"),
                        "to_unit": t.get("canonical_unit"),
                        "status": st, "rule_id": t.get("rule_id"),
                        "reason": t.get("unresolved_reason"),
                        "dimension": _dim(t.get("original_unit"))})
                for q, b in (t.get("context") or {}).items():
                    context_status_hist[b.get("status")] += 1
                    if b.get("scope"):
                        context_scope_hist[b["scope"]] += 1
                    if b.get("scope") == "paper":
                        paper_scope_assertions.add(
                            (doi, q, str(b.get("value")), str(b.get("source_location"))))

            # manual review queue
            for axis in ("x", "y"):
                sem = (c.get("semantics") or {}).get(axis) or {}
                ev = (sem.get("evidence") or [{}])[0]
                if ev and ev.get("needs_manual_review"):
                    review.append({
                        "priority": "confirm_low_confidence_assignment",
                        "curve_id": c["curve_id"], "doi": doi,
                        "figure": src.get("figure"), "panel": src.get("panel"),
                        "axis": axis,
                        "assigned": sem.get("normalization_definition"),
                        "confidence": ev.get("confidence"),
                        "evidence_source": ev.get("source"),
                        "evidence_span": (ev.get("span") or "")[:300],
                        "why": "assignment came from distant evidence; confirm against the figure"})
            for t in c.get("transformations") or []:
                if t.get("status") == Status.INVALID:
                    review.append({
                        "priority": "resolve_unit_quantity_conflict",
                        "curve_id": c["curve_id"], "doi": doi,
                        "figure": src.get("figure"), "panel": src.get("panel"),
                        "axis": t.get("axis"), "rule_id": t.get("rule_id"),
                        "why": t.get("unresolved_reason")})
                elif t.get("status") == Status.AMBIGUOUS:
                    review.append({
                        "priority": "disambiguate_context_or_semantics",
                        "curve_id": c["curve_id"], "doi": doi,
                        "figure": src.get("figure"), "panel": src.get("panel"),
                        "axis": t.get("axis"), "rule_id": t.get("rule_id"),
                        "why": t.get("unresolved_reason")})

    # ---------------- metrics (§12) ----------------
    n_curves = m["curves"] or 1
    axes = 2 * n_curves
    tx_total = sum(v for k, v in m.items() if k.startswith("tx:")) or 1
    metrics = {
        "papers_processed": len(ids),
        "papers_with_figure_data": papers_with_fd,
        "figures": len(figures),
        "panels": len(panels),
        "curves": m["curves"],
        "digitized_points": m["points"],
        "raw_x_label_recovery_rate": round(m["x_label_recovered"] / n_curves, 4),
        "raw_y_label_recovery_rate": round(m["y_label_recovered"] / n_curves, 4),
        # TWO distinct rates, reported separately so before/after is honest:
        #   quantity resolution = the axis maps to an ontology QuantityKind
        #                         (this is what the pre-work baseline measured)
        #   comparison-group    = the axis is additionally comparison-READY
        "x_quantity_resolution_rate": round(m["x_quantity_resolved"] / n_curves, 4),
        "y_quantity_resolution_rate": round(m["y_quantity_resolved"] / n_curves, 4),
        "x_quantity_resolved": m["x_quantity_resolved"],
        "y_quantity_resolved": m["y_quantity_resolved"],
        "x_semantic_resolution_rate": round(m["x_semantics_resolved"] / n_curves, 4),
        "y_semantic_resolution_rate": round(m["y_semantics_resolved"] / n_curves, 4),
        "x_comparison_ready": m["x_semantics_resolved"],
        "y_comparison_ready": m["y_semantics_resolved"],
        "axis_semantic_resolution_rate": round(
            (m["x_semantics_resolved"] + m["y_semantics_resolved"]) / axes, 4),
        "already_canonical_rate": round(m["tx:already_canonical"] / tx_total, 4),
        "direct_unit_conversion_rate": round(m["tx:converted"] / tx_total, 4),
        "successful_conversion_rate": round(
            (m["tx:converted"] + m["tx:already_canonical"]) / tx_total, 4),
        "missing_context_rate": round(m["tx:missing_context"] / tx_total, 4),
        "ambiguous_rate": round(m["tx:ambiguous"] / tx_total, 4),
        "unsupported_rate": round(m["tx:unsupported"] / tx_total, 4),
        "invalid_rate": round(m["tx:invalid"] / tx_total, 4),
        "not_applicable_rate": round(m["tx:not_applicable"] / tx_total, 4),
        "transformations_total": tx_total,
        "units_recovered_from_verbatim_label": m["units_recovered_from_label"],
        "low_confidence_assignments": m["low_confidence_assignments"],
        "granularity_changed_curves": m["granularity_changed"],
        "granularity_distribution": {k.split(":", 1)[1]: v for k, v in m.items()
                                     if k.startswith("granularity:")},
        "transformation_count_by_rule": dict(rule_hist),
        "quantity_count_by_comparison_group": dict(groups_hist),
        "normalization_definition_usage": dict(ndef_hist),
        "status_by_axis": {k: dict(v) for k, v in status_hist.items()},
        "context_scope_usage": dict(context_scope_hist),
        "context_status": dict(context_status_hist),
        "distinct_paper_level_assertions": len(paper_scope_assertions),
        "note_on_counting": ("paper-level context is counted once per distinct "
                             "(paper, quantity, value, source) assertion, not once "
                             "per experiment that could see it"),
        "most_common_unresolved_reasons": reason_hist.most_common(15),
        "code_version": code_version(),
        "created_at": build_timestamp(),
    }

    # ---------------- write ----------------
    _write_json("axis_semantics_audit.json",
                {"n_curves": len(rows), "curves": rows})
    _write_csv("axis_semantics_audit.csv", rows)
    _write_json("transformation_coverage.json",
                {"metrics": metrics,
                 "by_rule": dict(rule_hist),
                 "by_status_x": dict(status_hist["x"]),
                 "by_status_y": dict(status_hist["y"]),
                 "by_comparison_group": dict(groups_hist),
                 "by_normalization_definition": dict(ndef_hist)})
    _write_csv("transformation_coverage.csv",
               [{"rule_id": k, "applications": v,
                 "type": (RULE_DECLS.get(k) or {}).get("type"),
                 "version": (RULE_DECLS.get(k) or {}).get("version")}
                for k, v in rule_hist.most_common()])
    _write_json("unresolved_transformations.json",
                {"n": len(unresolved),
                 "reasons": reason_hist.most_common(),
                 "entries": unresolved})
    _write_json("ambiguous_transformations.json",
                {"n": len(ambiguous), "entries": ambiguous})
    _write_json("unit_conversion_audit.json",
                {"n": len(unit_audit),
                 "by_status": dict(Counter(u["status"] for u in unit_audit)),
                 "by_pair": dict(Counter("%s->%s" % (u["from_unit"], u["to_unit"])
                                         for u in unit_audit).most_common(40)),
                 "entries": unit_audit})
    _write_json("context_binding_audit.json",
                {"scope_usage": dict(context_scope_hist),
                 "status": dict(context_status_hist),
                 "distinct_paper_level_assertions": len(paper_scope_assertions),
                 "paper_level_assertions": [
                     {"doi": d, "quantity": q, "value": v, "source": src}
                     for d, q, v, src in sorted(paper_scope_assertions)][:200]})
    _write_json("manual_review_queue.json",
                {"n": len(review),
                 "by_priority": dict(Counter(r["priority"] for r in review)),
                 "entries": review})
    _write_json("metrics.json", metrics)

    print("audit: %d papers, %d curves, %d points" % (len(ids), m["curves"], m["points"]))
    for k in ("x_quantity_resolution_rate", "y_quantity_resolution_rate",
              "x_semantic_resolution_rate", "y_semantic_resolution_rate",
              "successful_conversion_rate", "missing_context_rate",
              "ambiguous_rate", "unsupported_rate", "invalid_rate"):
        print("  %-34s %.1f%%" % (k, 100 * metrics[k]))
    print("  %-34s %d" % ("manual review items", len(review)))
    print("-> %s" % REPORTS)
    return 0


def _reason_key(reason):
    if not reason:
        return "unspecified"
    r = str(reason)
    for key in ("does not resolve to any ontology QuantityKind",
                "not a comparison target",
                "no normalization expression found",
                "the printed unit and the quantity disagree",
                "distinct", "no value for", "not a recognised, convertible unit",
                "matches", "defined"):
        if key in r:
            return key
    return r[:80]


def _dim(unit):
    u = U.try_parse(unit, allow_empty_as_dimensionless=True)
    return U.DIM_NAME.get(u.dimension) if u else None


def _write_json(name, obj):
    (REPORTS / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def _write_csv(name, rows):
    if not rows:
        (REPORTS / name).write_text("")
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(REPORTS / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    raise SystemExit(main())
