#!/usr/bin/env python3
"""Corpus-wide acceptance check for the experiment-extraction repair.

Checks the §7 criteria, and the §8 requirement that a condition is correct only
when its TARGET ENTITY is correctly typed and materialised -- a perfectly parsed
pressure attached to a fit that should never have been an experiment, or to a
curve labelled Al2O3 that the caption calls TiO2, is not a correct binding.

Read-only. Writes reports/experiment_extraction_regression/acceptance.json.
"""
import json
import glob
import sys
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
KB = ROOT / "02_extraction" / "output"
EXTRACTED = ROOT / "03_corpus" / "extracted"
sys.path.insert(0, str(ROOT / "02_extraction"))
from canonical import chemistry_scope as cschem      # noqa: E402
from canonical import entities as cent               # noqa: E402


def jload(p, d=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else d


def raw_series_count(paper):
    fd = jload(EXTRACTED / paper / "figure_data.json", {})
    return sum(len(pan.get("series") or [])
               for f in (fd.get("figures") or []) for pan in (f.get("panels") or []))


def main():
    papers = sorted(p.name for p in KB.iterdir()
                    if (p / "resolved" / "results.json").exists())
    fail = collections.defaultdict(list)
    tot = collections.Counter()
    per_paper = {}

    for p in papers:
        res = jload(KB / p / "resolved" / "results.json")
        rows = res["results"]
        ents = {e["entity_id"]: e for e in jload(KB / p / "resolved" / "entities.json", [])}
        raw = raw_series_count(p)
        s = res["summary"]
        for k, v in s.items():
            tot[k] += v
        tot["raw_series"] += raw
        tot["result_records"] += len(rows)

        # --- §7 acceptance ------------------------------------------------
        if raw and raw != len(rows):
            fail["orphaned_or_duplicated_series"].append((p, raw, len(rows)))
        raw_pts = sum(len(sx.get("points") or [])
                      for f in (jload(EXTRACTED / p / "figure_data.json", {})
                                .get("figures") or [])
                      for pan in (f.get("panels") or [])
                      for sx in (pan.get("series") or []))
        got_pts = sum(r["n_points"] or 0 for r in rows)
        if raw_pts and raw_pts != got_pts:
            fail["points_lost"].append((p, raw_pts, got_pts))

        for r in rows:
            rid = "%s/%s" % (p, r["result_id"])
            if r["result_kind"] == "fit_or_calculated_representation":
                if r["experimental_case_count"]:
                    fail["fit_minted_a_physical_experiment"].append(rid)
                if r["is_current_paper_experiment"]:
                    fail["fit_flagged_as_experiment"].append(rid)
            if r["result_kind"] in ("simulation", "model_curve"):
                if r["experimental_case_count"]:
                    fail["model_curve_minted_experiment"].append(rid)
                if not r["points"]:
                    fail["model_curve_lost_its_points"].append(rid)
            axis = cent.setting_axis_kind(r["coordinate"])
            if axis in ("within_run", "measurement_coordinate") \
                    and (r["experimental_case_count"] or 0) > 1:
                fail["density_became_experiments"].append((rid, r["coordinate"]))
            if r["multi_material_paper"] and r["material"] and \
                    r["material_scope_level"] in (None, "unresolved",
                                                  "paper_single_material"):
                fail["first_item_chemistry_fallback"].append(rid)
            if r["chemistry_consistent"] is False:
                fail["chemistry_inconsistent"].append(
                    (rid, r["chemistry_inconsistency"]))
            if r["material"] is None and r["multi_material_paper"] \
                    and not (r["material_candidates"] or r["material_ambiguity_reason"]):
                fail["material_dropped_without_explanation"].append(rid)
            if r["experimental_case_status"] == "unresolved_settings" \
                    and not r["experimental_case_reason"]:
                fail["unresolved_without_reason"].append(rid)

            # --- §8 target-entity correctness -----------------------------
            ent = ents.get(r["result_id"])
            nb = len(ent.get("bound_conditions") or []) if ent else 0
            if nb:
                tot["conditions_bound"] += nb
                if r["result_kind"] == "fit_or_calculated_representation":
                    tot["conditions_on_fits"] += nb
                if r["is_current_paper_experiment"]:
                    tot["conditions_on_experiments"] += nb
                # a condition on a MEASURED entity whose material came from a
                # non-evidence rung is attached to a mis-materialised target
                if r["is_current_paper_experiment"] and r["material"] \
                        and r["material_scope_level"] == "unresolved":
                    fail["condition_on_mismaterialised_entity"].append(rid)

        # --- the caption must not contradict the assigned material --------
        fd = jload(EXTRACTED / p / "figure_data.json", {})
        scout = jload(EXTRACTED / p / "scout.json", {})
        mats = scout.get("materials") or []
        bykey = collections.defaultdict(set)
        for r in rows:
            bykey[str(r["fig_docling_index"])].add(r["material"])
        for f in (fd.get("figures") or []):
            named = cschem._named(f.get("caption"), mats)
            assigned = {m for m in bykey.get(str(f.get("figure")), set()) if m}
            if len(named) == 1 and assigned and named[0] not in assigned:
                fail["caption_material_conflict"].append(
                    (p, f.get("figure"), named[0], sorted(assigned)))

        per_paper[p] = {"raw_series": raw, "result_records": len(rows),
                        "summary": s}

    report = {
        "papers": len(papers),
        "totals": dict(tot),
        "acceptance": {k: len(v) for k, v in sorted(fail.items())},
        "failures": {k: v[:12] for k, v in sorted(fail.items())},
        "per_paper": per_paper,
    }
    (OUT / "acceptance.json").write_text(json.dumps(report, indent=1))

    print("papers: %d   raw series: %d   result records: %d"
          % (len(papers), tot["raw_series"], tot["result_records"]))
    print("\n-- §7 acceptance criteria --")
    CRIT = ["orphaned_or_duplicated_series", "points_lost",
            "fit_minted_a_physical_experiment", "fit_flagged_as_experiment",
            "model_curve_minted_experiment", "model_curve_lost_its_points",
            "density_became_experiments", "first_item_chemistry_fallback",
            "chemistry_inconsistent", "caption_material_conflict",
            "material_dropped_without_explanation", "unresolved_without_reason",
            "condition_on_mismaterialised_entity"]
    for k in CRIT:
        n = len(fail.get(k, []))
        print("  %-42s %s" % (k, "PASS" if n == 0 else "FAIL (%d)" % n))
        for x in fail.get(k, [])[:3]:
            print("        %s" % (x,))
    return 0 if not any(fail.get(k) for k in CRIT) else 1


if __name__ == "__main__":
    sys.exit(main())
