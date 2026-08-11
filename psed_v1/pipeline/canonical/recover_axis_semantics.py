#!/usr/bin/env python3
"""
recover_axis_semantics.py — Stage D, part 1: recover axis semantics from the
LOCAL TEXT EVIDENCE that already exists, and decide which figures genuinely
still need to be looked at again.

Evidence priority (spec §2.2), all local, no network, no OCR:
    1 raw axis metadata      2 figure caption        3 panel caption clause
    4 figure discussion in document.md               5 equations in document.md

Writes, per paper:
    papers/{doi}/extracted/recovery/axis_semantics_v1.json

That file is an AUDIT + WORK LIST. It does not add raw evidence — text recovery
is re-derived deterministically by build_canonical.py from the same sources, so
there is one code path and no risk of the two drifting. New raw evidence only
comes from reextract_figures.py, which writes figure_semantics_v1.json.

Usage:
    python3 -m pipeline.canonical.recover_axis_semantics --all
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "canonical"

from . import sources as S                                     # noqa: E402
from . import axis_semantics as AX                             # noqa: E402
from . import units as U                                       # noqa: E402
from .schema import REPO, Status, code_version, build_timestamp  # noqa: E402

REPORTS = REPO / "reports" / "canonical"


def _axis_record(sem, raw, label):
    """The §2.1 axis shape: verbatim label + normalization semantics + provenance."""
    ndef = sem.get("normalization_definition")
    spec = AX.NORMALIZATION_DEFINITIONS.get(ndef) if ndef else None
    ev = (sem.get("evidence") or [{}])[0]
    unit_raw = raw.get("unit")
    unit_norm = None
    u = U.try_parse(unit_raw, allow_empty_as_dimensionless=bool(ndef))
    if u is not None:
        unit_norm = u.symbol
    return {
        "label_raw": label,
        "quantity": raw.get("quantity"),
        "quantity_canonical": sem.get("quantity"),
        "unit_raw": unit_raw,
        "unit_normalized": unit_norm,
        "is_normalized": bool(ndef) or None,
        "normalization_expression": (spec or {}).get("formula"),
        "normalization_denominator_symbol": (
            ((spec or {}).get("denominator_symbols") or [None])[0]),
        "normalization_definition": ndef,
        "normalization_denominator_role": (spec or {}).get("normalization_denominator_role"),
        "comparison_group": sem.get("comparison_group"),
        "axis_role": sem.get("axis_role"),
        "axis_kind": sem.get("axis_kind"),
        "status": sem.get("status"),
        "unresolved_reason": sem.get("unresolved_reason"),
        "recovery": None if not ev else {
            "method": ev.get("method"),
            "source": ev.get("source"),
            "source_file": ev.get("source_file"),
            "source_location": ev.get("source_location"),
            "evidence_span": ev.get("span"),
            "confidence": ev.get("confidence"),
            "automatic": ev.get("automatic"),
            "needs_manual_review": ev.get("needs_manual_review", False),
            "original_value": raw.get("quantity"),
            "recovered_value": ndef or sem.get("comparison_group"),
        },
    }


# --- §8.1 candidate criteria ---------------------------------------------
def reextraction_reasons(sem_x, sem_y, raw_x, raw_y, panel_axes_conflict):
    reasons = []
    if (sem_x.get("quantity") in ("spatial_coordinate", "dimensionless_distance")
            and not (raw_x.get("unit") or "").strip()
            and not sem_x.get("normalization_definition")):
        reasons.append("x_is_spatial_but_unit_empty_and_denominator_unresolved")
    if (sem_y.get("raw_quantity") in ("normalized_thickness", "step_coverage", "conformality")
            and not sem_y.get("normalization_definition")):
        reasons.append("normalized_y_without_normalization_definition")
    if sem_x.get("status") == Status.UNSUPPORTED:
        reasons.append("x_quantity_unknown")
    if sem_y.get("status") == Status.UNSUPPORTED:
        reasons.append("y_quantity_unknown")
    if sem_x.get("status") == Status.AMBIGUOUS:
        reasons.append("x_semantics_conflict")
    if sem_y.get("status") == Status.AMBIGUOUS:
        reasons.append("y_semantics_conflict")
    for name, raw, sem in (("x", raw_x, sem_x), ("y", raw_y, sem_y)):
        unit = raw.get("unit")
        if unit not in (None, "") and U.try_parse(unit) is None:
            reasons.append("%s_unit_unparseable:%s" % (name, unit))
        # A comparison-target quantity whose printed unit has the WRONG dimension
        # (growth_per_cycle labelled "nm" instead of "nm/cycle") or no unit at
        # all. This blocks a real comparison group, so the verbatim label is
        # worth re-reading. We never guess the missing "/cycle".
        grp = sem.get("comparison_group")
        if grp and sem.get("status") == "resolved":
            want = AX.COMPARISON_GROUPS[grp].get("canonical_unit")
            have = U.try_parse(unit, allow_empty_as_dimensionless=False)
            want_u = U.try_parse(want, allow_empty_as_dimensionless=True)
            if have is None and not sem.get("normalization_definition") \
                    and (AX.COMPARISON_GROUPS[grp].get("dimension") != "dimensionless"):
                reasons.append("%s_comparison_target_without_usable_unit" % name)
            elif have is not None and want_u is not None and have.dimension != want_u.dimension:
                reasons.append("%s_unit_dimension_conflicts_with_quantity:%s_vs_%s"
                               % (name, U.DIM_NAME.get(have.dimension),
                                  U.DIM_NAME.get(want_u.dimension)))
    if panel_axes_conflict:
        reasons.append("panel_curves_disagree_on_axes")
    return reasons


# Re-extraction is a paid vision call per figure, so it is spent where it can
# actually unlock a comparison group. HIGH = the axis is a conformality/growth
# comparison target whose semantics are blocked. LOW = spectra (XRD/XPS/FTIR)
# whose axes are not comparison targets at all; re-reading their labels would not
# make them comparable, so they stay flagged for the record but are not re-run.
_HIGH = {"normalized_y_without_normalization_definition",
         "x_is_spatial_but_unit_empty_and_denominator_unresolved",
         "x_semantics_conflict", "y_semantics_conflict"}
_HIGH_PREFIX = ("x_unit_dimension_conflicts_with_quantity",
                "y_unit_dimension_conflicts_with_quantity",
                "x_comparison_target_without_usable_unit",
                "y_comparison_target_without_usable_unit")
_MEDIUM_PREFIX = ("x_unit_unparseable", "y_unit_unparseable")


def _priority(reasons):
    rs = set(reasons)
    if rs & _HIGH or any(r.startswith(_HIGH_PREFIX) for r in rs):
        return "high"
    if any(r.startswith(_MEDIUM_PREFIX) for r in rs):
        return "medium"
    return "low"


def recover_paper(doi):
    paths = S.paper_paths(doi)
    fd = json.loads(paths["figure_data"].read_text())
    panels_out = []
    seen_panels = set()
    for c in S.iter_curves(doi):
        key = (c["figure"], c["panel"])
        if key in seen_panels:
            continue
        seen_panels.add(key)
        sem_x = AX.resolve_x_axis(c["x_raw"].get("quantity"), c["x_raw"].get("unit"),
                                  c["x_label"], c["texts_x"])
        sem_y = AX.resolve_y_axis(c["y_raw"].get("quantity"), c["y_raw"].get("unit"),
                                  c["y_label"], c["texts_y"])
        reasons = reextraction_reasons(sem_x, sem_y, c["x_raw"], c["y_raw"], False)
        panels_out.append({
            "figure": c["figure_number"],
            "figure_index": c["figure"],
            "panel": c["panel"],
            "image": _panel_image(fd, c["figure"]),
            "caption": c["caption"],
            "panel_caption": c["panel_caption"],
            "x": _axis_record(sem_x, c["x_raw"], c["x_label"]),
            "y": _axis_record(sem_y, c["y_raw"], c["y_label"]),
            "needs_image_reextraction": bool(reasons),
            "reextraction_reasons": reasons,
        })
    out = {
        "doi": doi,
        "schema_version": 1,
        "kind": "text_evidence_recovery_audit",
        "generator": "pipeline/canonical/recover_axis_semantics.py",
        "code_version": code_version(),
        "created_at": build_timestamp(),
        "note": ("Audit + work list. Text-evidence recovery is re-derived by "
                 "build_canonical.py from the same sources; new RAW evidence "
                 "(verbatim axis labels) is written by reextract_figures.py to "
                 "figure_semantics_v1.json."),
        "n_panels": len(panels_out),
        "panels": panels_out,
    }
    d = paths["recovery"].parent
    d.mkdir(parents=True, exist_ok=True)
    (d / "axis_semantics_v1.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def _panel_image(fd, figure_index):
    for f in fd.get("figures", []) or []:
        if str(f.get("figure")) == str(figure_index):
            return f.get("image")
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

    worklist, stats = [], Counter()
    for doi in ids:
        if not S.paper_paths(doi)["figure_data"].exists():
            stats["papers_without_figure_data"] += 1
            continue
        out = recover_paper(doi)
        stats["papers"] += 1
        for p in out["panels"]:
            stats["panels"] += 1
            for ax in ("x", "y"):
                if p[ax]["status"] == "resolved":
                    stats["%s_resolved" % ax] += 1
                if p[ax]["normalization_definition"]:
                    stats["%s_normalization_recovered" % ax] += 1
                    stats["nd:" + p[ax]["normalization_definition"]] += 1
                rec = p[ax].get("recovery") or {}
                if rec.get("source"):
                    stats["evidence_source:" + rec["source"]] += 1
                if rec.get("needs_manual_review"):
                    stats["low_confidence_needs_review"] += 1
            if p["needs_image_reextraction"]:
                stats["panels_needing_reextraction"] += 1
                for r in p["reextraction_reasons"]:
                    stats["reason:" + r.split(":")[0]] += 1
                worklist.append({
                    "doi": doi, "figure": p["figure"], "figure_index": p["figure_index"],
                    "panel": p["panel"], "image": p["image"],
                    "reasons": p["reextraction_reasons"],
                })
        print("  %-38s %3d panels, %3d need re-extraction"
              % (doi, out["n_panels"],
                 sum(1 for p in out["panels"] if p["needs_image_reextraction"])))

    REPORTS.mkdir(parents=True, exist_ok=True)
    # de-duplicate to FIGURE level: one vision call re-reads all panels at once
    figs = {}
    for w in worklist:
        k = (w["doi"], w["figure_index"])
        figs.setdefault(k, {"doi": w["doi"], "figure": w["figure"],
                            "figure_index": w["figure_index"], "image": w["image"],
                            "panels": [], "reasons": set()})
        figs[k]["panels"].append(w["panel"])
        figs[k]["reasons"].update(w["reasons"])
    figlist = [{**v, "reasons": sorted(v["reasons"]),
                "priority": _priority(v["reasons"])} for v in figs.values()]
    figlist.sort(key=lambda f: ({"high": 0, "medium": 1, "low": 2}[f["priority"]],
                                f["doi"], f["figure_index"]))
    (REPORTS / "reextraction_candidates.json").write_text(json.dumps(
        {"n_panels": len(worklist), "n_figures": len(figlist),
         "stats": dict(stats), "figures": figlist}, indent=1, ensure_ascii=False))

    print("\n%d panels across %d figures flagged for selective re-extraction"
          % (len(worklist), len(figlist)))
    for k, v in sorted(stats.items()):
        print("  %-46s %d" % (k, v))
    print("-> %s" % (REPORTS / "reextraction_candidates.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
