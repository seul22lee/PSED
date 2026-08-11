#!/usr/bin/env python3
"""Corpus validation for the granularity / axis-semantics / identity repair.

Reports, per paper, exactly the columns the review asked for, and asserts the
two directional guarantees:

  * every minted independent case carries source evidence saying WHY the setting
    was a separate execution;
  * continuous traces, spectra, profiles and multi-output measurements are never
    exploded into point-level experiments.

Also checks id integrity: printed-figure anchoring, collisions, orphans.
"""
import paths as P
import json
import re
import sys
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPERS = P.PAPERS

NEVER_SPLIT = {"continuous_or_longitudinal_run", "measurement_scan",
               "spatial_profile", "multi_output_measurement",
               "model_or_simulation"}


def main():
    fail = collections.defaultdict(list)
    rows, totals = [], collections.Counter()
    all_ids = collections.Counter()
    review = []

    for d in sorted(p for p in PAPERS.iterdir() if p.is_dir()):
        rf = P.resolved_json(d.name, "results")
        if not rf.exists():
            continue
        res = json.loads(rf.read_text())
        R, S = res["results"], res["summary"]
        paper = d.name
        kinds = collections.Counter(r["result_kind"] for r in R)

        for r in R:
            all_ids[r["result_id"]] += 1
            g = r.get("granularity_kind")
            n = r.get("experimental_case_count") or 0

            # (1) a minted independent case must say why it is a separate run
            if g == "independent_process_sweep" and n > 0:
                if not (r.get("granularity_evidence") or
                        r.get("experimental_case_reason")):
                    fail["sweep_case_without_evidence"].append(
                        (paper, r["result_id"]))
            # (2) nothing that is one run/specimen may become point-level
            if g in NEVER_SPLIT and n > 1:
                fail["non_sweep_exploded_into_points"].append(
                    (paper, r["result_id"], g, n))
            if g == "model_or_simulation" and n:
                fail["model_counted_as_physical"].append((paper, r["result_id"]))
            # (3) the id must be anchored on the PRINTED figure number
            fn = str(r.get("printed_figure_number") or "").strip()
            slug = r.get("figure_slug") or ""
            if fn and slug and not slug.startswith("Fig%s" % re.sub(
                    r"[^A-Za-z0-9.]", "", fn)):
                fail["id_uses_wrong_figure_number"].append(
                    (paper, r["result_id"], "printed=%s" % fn))
            di = str(r.get("fig_docling_index") or "").strip()
            if fn and di and fn != di and slug == "Fig%s" % di:
                fail["id_uses_docling_index"].append((paper, r["result_id"]))
            # (4) links must resolve
            for k in ("shares_physical_case_with", "physical_case_id"):
                v = r.get(k)
                if v and v not in {x["result_id"] for x in R}:
                    fail["orphaned_%s" % k].append((paper, r["result_id"], v))
            if r.get("granularity_review_reason"):
                review.append((paper, r["result_id"], g,
                               r["granularity_review_reason"]))

        row = {
            "paper": paper,
            "source_figure_series": len(R),
            "physical_process_runs": S.get("physical_process_runs", 0),
            "measurement_events": S.get("measurement_events", 0),
            "result_series": len(R),
            "independent_sweep_cases": S.get("independent_sweep_cases_minted", 0),
            "continuous_runs": kinds.get("continuous_or_longitudinal_run", 0),
            "spatial_profiles": kinds.get("spatial_profile", 0),
            "measurement_scans": kinds.get("measurement_scan", 0),
            "multi_output": kinds.get("multi_output_measurement", 0),
            "models_sims": (kinds.get("model_or_simulation", 0)
                            + kinds.get("simulation", 0)
                            + kinds.get("model_curve", 0)
                            + kinds.get("fit_or_calculated_representation", 0)),
            "unresolved": S.get("unresolved_granularity", 0),
            "physical_cases_total": sum(r["experimental_case_count"] or 0
                                        for r in R),
        }
        rows.append(row)
        for k, v in row.items():
            if isinstance(v, int):
                totals[k] += v

    dup = [k for k, v in all_ids.items() if v > 1]
    if dup:
        fail["id_collisions"] = dup[:20]

    hdr = ("paper", "series", "runs", "meas", "sweepC", "cont", "spat", "scan",
           "multi", "model", "unres", "cases")
    print("%-34s %6s %5s %5s %6s %5s %5s %5s %5s %5s %5s %5s" % hdr)
    for r in rows:
        print("%-34s %6d %5d %5d %6d %5d %5d %5d %5d %5d %5d %5d" % (
            r["paper"][:34], r["source_figure_series"], r["physical_process_runs"],
            r["measurement_events"], r["independent_sweep_cases"],
            r["continuous_runs"], r["spatial_profiles"], r["measurement_scans"],
            r["multi_output"], r["models_sims"], r["unresolved"],
            r["physical_cases_total"]))
    print("%-34s %6d %5d %5d %6d %5d %5d %5d %5d %5d %5d %5d" % (
        "TOTAL", totals["source_figure_series"], totals["physical_process_runs"],
        totals["measurement_events"], totals["independent_sweep_cases"],
        totals["continuous_runs"], totals["spatial_profiles"],
        totals["measurement_scans"], totals["multi_output"],
        totals["models_sims"], totals["unresolved"],
        totals["physical_cases_total"]))

    print("\n-- assertions --")
    CHECKS = ["sweep_case_without_evidence", "non_sweep_exploded_into_points",
              "model_counted_as_physical", "id_uses_wrong_figure_number",
              "id_uses_docling_index", "id_collisions",
              "orphaned_shares_physical_case_with", "orphaned_physical_case_id"]
    for k in CHECKS:
        n = len(fail.get(k, []))
        print("  %-38s %s" % (k, "PASS" if n == 0 else "FAIL (%d)" % n))
        for x in fail.get(k, [])[:4]:
            print("        %s" % (x,))

    print("\n-- left for review: %d --" % len(review))
    for x in review[:15]:
        print("  %-30s %-34s %-30s %s" % x)

    (REPO / "tools" / "granularity_validation.json").write_text(json.dumps(
        {"per_paper": rows, "totals": dict(totals),
         "failures": {k: v[:20] for k, v in fail.items()},
         "review_queue": review}, indent=1))
    return 1 if any(fail.get(k) for k in CHECKS) else 0


if __name__ == "__main__":
    sys.exit(main())
