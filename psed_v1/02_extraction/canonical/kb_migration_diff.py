#!/usr/bin/env python3
"""
kb_migration_diff.py — structured before/after diff of the resolved experiments,
run after the live-pipeline fixes regenerate them (spec §9).

Reports, per paper and overall:
  * experiment-count change caused by corrected granularity
  * which experiment ids were preserved / split / replaced / added / removed
  * ExperimentSeries created
  * unit conversions that actually rescaled values
  * coordinate units recovered
  * context conflicts detected instead of broadcast

Usage:
    python3 02_extraction/canonical/kb_migration_diff.py \
        --before 02_extraction/output/_archive/resolved_pre_canonical \
        --out reports/canonical
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

from .schema import REPO, code_version                          # noqa: E402
from . import sources as S                                      # noqa: E402

OUTPUT = REPO / "02_extraction" / "output"


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return []


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default=str(REPO / "02_extraction" / "output" /
                                                 "_archive" / "resolved_pre_canonical"))
    ap.add_argument("--out", default=str(REPO / "reports" / "canonical"))
    a = ap.parse_args(argv)
    before_root = Path(a.before)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    papers, totals = [], Counter()
    for doi in S.papers():
        after_p = OUTPUT / doi / "resolved" / "experiments.json"
        if not after_p.exists():
            continue
        before = load(before_root / doi / "experiments.json")
        after = load(after_p)
        series = load(OUTPUT / doi / "resolved" / "series.json")

        b_ids = {e.get("exp_id") for e in before}
        a_ids = {e.get("exp_id") for e in after}
        replaced = {s.get("replaced_experiment_id") for s in series}
        split_children = {e.get("exp_id") for e in after if e.get("in_series")}

        preserved = sorted(b_ids & a_ids)
        removed = sorted(b_ids - a_ids)
        added = sorted(a_ids - b_ids)

        rescaled = sum(1 for e in after
                       if (e.get("measurand") or {}).get("unit_conversion", {}).get("values_rescaled"))
        coord_units = sum(1 for e in after if e.get("coordinate_unit_normalized"))
        coord_unresolved = sum(1 for e in after if not e.get("coordinate_unit_normalized"))
        conflicts = sum(len(e.get("context_conflicts") or []) for e in after)
        exps_with_conflicts = sum(1 for e in after if e.get("context_conflicts"))
        gran_after = Counter(e.get("granularity") for e in after)
        gran_before = Counter(e.get("granularity") for e in before)

        rec = {
            "doi": doi,
            "experiments_before": len(before),
            "experiments_after": len(after),
            "delta": len(after) - len(before),
            "series_created": len(series),
            "condition_curves_split": len(replaced - {None}),
            "experiments_from_splits": len(split_children),
            "preserved_ids": len(preserved),
            "removed_ids": len(removed),
            "added_ids": len(added),
            "replaced_by_series": sorted(x for x in replaced if x),
            "granularity_before": dict(gran_before),
            "granularity_after": dict(gran_after),
            "measurands_rescaled": rescaled,
            "coordinate_units_resolved": coord_units,
            "coordinate_units_unresolved": coord_unresolved,
            "context_conflicts_detected": conflicts,
            "experiments_with_context_conflicts": exps_with_conflicts,
        }
        papers.append(rec)
        for k in ("experiments_before", "experiments_after", "series_created",
                  "condition_curves_split", "experiments_from_splits",
                  "measurands_rescaled", "coordinate_units_resolved",
                  "coordinate_units_unresolved", "context_conflicts_detected",
                  "experiments_with_context_conflicts", "preserved_ids",
                  "removed_ids", "added_ids"):
            totals[k] += rec[k]

    summary = {
        "generator": "02_extraction/canonical/kb_migration_diff.py",
        "code_version": code_version(),
        "before_snapshot": str(before_root),
        "papers": len(papers),
        "totals": dict(totals),
        "note": ("Removed ids are condition-sweep curves that were replaced by an "
                 "ExperimentSeries plus one experiment per point; their ids appear "
                 "in replaced_by_series. No measured data was discarded."),
        "per_paper": papers,
    }
    (out / "kb_migration_summary.json").write_text(json.dumps(summary, indent=1))

    with open(out / "granularity_before_after.csv", "w") as fh:
        fh.write("doi,experiments_before,experiments_after,delta,series_created,"
                 "condition_curves_split,experiments_from_splits,preserved_ids,"
                 "removed_ids,added_ids,measurands_rescaled,"
                 "coordinate_units_resolved,coordinate_units_unresolved,"
                 "context_conflicts_detected\n")
        for r in papers:
            fh.write(",".join(str(r[k]) for k in (
                "doi", "experiments_before", "experiments_after", "delta",
                "series_created", "condition_curves_split", "experiments_from_splits",
                "preserved_ids", "removed_ids", "added_ids", "measurands_rescaled",
                "coordinate_units_resolved", "coordinate_units_unresolved",
                "context_conflicts_detected")) + "\n")

    gba = {"per_paper": [{k: r[k] for k in
                          ("doi", "granularity_before", "granularity_after",
                           "series_created", "replaced_by_series")} for r in papers],
           "totals": dict(totals)}
    (out / "granularity_before_after.json").write_text(json.dumps(gba, indent=1))

    print("KB migration: %d papers" % len(papers))
    for k in sorted(totals):
        print("  %-38s %d" % (k, totals[k]))
    print("-> %s" % (out / "kb_migration_summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
