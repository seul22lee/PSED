#!/usr/bin/env python3
"""READ-ONLY. §H/I/J — root-cause frequency, corpus estimates with CIs, paper summaries."""
import paths as P
import csv, json, math
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = P.PAPERS
BASE = KB / "_archive" / "resolved_pre_canonical"

CAUSE = {
    "A": "Mention not extracted",
    "B": "Mention preserved as text but not parsed",
    "C": "Wrong quantity classification / axis role unresolved",
    "D": "Wrong unit or dimension",
    "E": "Applicability scope lost",
    "F": "Reference or source identity lost",
    "G": "Reactant or species binding lost",
    "H": "Field dropped downstream",
    "I": "Hidden or replaced by fallback / dedup",
    "J": "Incorrect paper-level broadcast",
    "L": "Figure identifier mismatch",
    "M": "Relevant extractor not executed",
    "N": "Schema cannot represent the condition",
    "P": "Curve point incorrectly promoted to Experiment",
    "S": "Model or simulation data stored as Experiment",
    "": "no failure detected",
}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    audit = json.loads((OUT / "random_sample_audit.json").read_text())
    rows = audit["rows"]
    pop = json.loads((OUT / "corpus_population_manifest.json").read_text())
    n = len(rows)

    # ---------- §H root-cause frequency (random sample only) ----------
    rc = Counter(r["root_cause_category"] for r in rows)
    freq = []
    for code, cnt in rc.most_common():
        lo, hi = wilson(cnt, n)
        freq.append({"code": code, "label": CAUSE.get(code, code), "count": cnt,
                     "share": round(cnt / n, 4), "ci95": [round(lo, 4), round(hi, 4)],
                     "responsible_code_path": next(
                         (r["responsible_code_path"] for r in rows
                          if r["root_cause_category"] == code), "")})
    (OUT / "root_cause_frequency.json").write_text(json.dumps(
        {"sample_n": n, "note": "random sample only; targeted cases excluded",
         "frequencies": freq}, indent=1))
    with open(OUT / "root_cause_frequency.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["code", "label", "count", "share", "ci95",
                                           "responsible_code_path"])
        w.writeheader()
        for f in freq:
            w.writerow(f)

    # ---------- §I corpus estimates ----------
    def est(name, pred):
        k = sum(1 for r in rows if pred(r))
        lo, hi = wilson(k, n)
        return {"metric": name, "count": k, "n": n, "share": round(k / n, 4),
                "ci95": [round(lo, 4), round(hi, 4)]}

    ests = [
        est("supported_as_physical_experiment_yes", lambda r: r["supported_as_physical_experiment"] == "yes"),
        est("supported_as_physical_experiment_no", lambda r: r["supported_as_physical_experiment"] == "no"),
        est("supported_uncertain", lambda r: r["supported_as_physical_experiment"] == "uncertain"),
        est("model_or_simulation", lambda r: r["paper_ground_truth_entity_kind"] in
            ("simulation_run", "simulation_profile", "model_prediction", "model_parameter_sweep")),
        est("derived_or_duplicate", lambda r: r["paper_ground_truth_entity_kind"] == "derived_representation"),
        est("digitised_point_of_one_curve", lambda r: r["paper_ground_truth_entity_kind"] == "measurement"),
        est("has_missing_source_supported_condition", lambda r: bool(r["missing_conditions"])),
        est("has_over_broadcast_condition", lambda r: bool(r["over_broadcast_conditions"])),
        est("affected_by_point_level_splitting", lambda r: r["created_by_granularity_migration"]
            if "created_by_granularity_migration" in r else bool(r.get("current_series_id"))),
        est("pressure_lost", lambda r: (r.get("pressure_in_caption") or r.get("pressure_in_pressure_json"))
            and not r.get("pressure_on_record_usable")),
        est("deterministically_recoverable", lambda r: r["root_cause_category"] in
            ("B", "E", "H", "I", "J", "P", "S", "G", "N")),
        est("requires_image_or_pdf_review", lambda r: r["root_cause_category"] in ("A", "C")),
        est("requires_re_digitisation", lambda r: False),
    ]
    (OUT / "corpus_estimates.json").write_text(json.dumps(
        {"sample_n": n, "population_n": pop["n_experiment_like_records"],
         "method": "Wilson score 95% interval on the seeded stratified random sample",
         "estimates": ests}, indent=1))

    # ---------- §J paper-level summaries ----------
    by_paper = defaultdict(list)
    for r in rows:
        by_paper[r["paper_id"]].append(r)
    summaries = []
    for doi in sorted(pop["per_paper"]):
        s = by_paper.get(doi, [])
        before = len(json.loads((BASE / doi / "experiments.json").read_text())) \
            if (BASE / doi / "experiments.json").exists() else None
        summaries.append({
            "paper_id": doi,
            "current_record_count": pop["per_paper"][doi]["experiments"],
            "previous_record_count": before,
            "sampled": len(s),
            "verified_physical_experiment": sum(1 for r in s if r["supported_as_physical_experiment"] == "yes"),
            "verified_model_or_simulation": sum(1 for r in s if r["paper_ground_truth_entity_kind"]
                                                in ("simulation_run", "simulation_profile")),
            "verified_duplicate_or_derived": sum(1 for r in s if r["paper_ground_truth_entity_kind"]
                                                 == "derived_representation"),
            "digitised_points_of_a_curve": sum(1 for r in s if r["paper_ground_truth_entity_kind"] == "measurement"),
            "records_with_missing_conditions": sum(1 for r in s if r["missing_conditions"]),
            "records_with_broadcast_context": sum(1 for r in s if r["over_broadcast_conditions"]),
            "pressure_findings": ("usable pressure on some record"
                                  if any(r.get("pressure_on_record_usable") for r in s)
                                  else "no usable pressure on any sampled record"),
            "dominant_root_causes": [c for c, _ in Counter(
                r["root_cause_category"] for r in s).most_common(3) if c],
            "confidence": "medium" if len(s) >= 4 else "low",
            "needs_full_paper_audit": None,
        })
    trig = {t["paper_id"] for t in json.loads(
        (OUT / "full_paper_audit_triggers.json").read_text())["triggers"]}
    for s in summaries:
        s["needs_full_paper_audit"] = s["paper_id"] in trig
    (OUT / "paper_level_summaries.json").write_text(json.dumps(
        {"papers": len(summaries), "summaries": summaries}, indent=1))

    md = ["# Paper-level audit summaries", "",
          "Random-sample findings only. Targeted-case findings are reported separately.", "",
          "| paper | now | before | sampled | phys | model | derived | digitised pts | miss cond | broadcast | pressure | causes | full audit |",
          "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|---|"]
    for s in summaries:
        md.append("| %s | %d | %s | %d | %d | %d | %d | %d | %d | %d | %s | %s | %s |" % (
            s["paper_id"], s["current_record_count"], s["previous_record_count"],
            s["sampled"], s["verified_physical_experiment"], s["verified_model_or_simulation"],
            s["verified_duplicate_or_derived"], s["digitised_points_of_a_curve"],
            s["records_with_missing_conditions"], s["records_with_broadcast_context"],
            "yes" if "usable" in s["pressure_findings"] and "no usable" not in s["pressure_findings"] else "none",
            ",".join(s["dominant_root_causes"]) or "-",
            "YES" if s["needs_full_paper_audit"] else ""))
    (OUT / "paper_level_summaries.md").write_text("\n".join(md) + "\n")

    print("root causes (random sample, n=%d):" % n)
    for f in freq:
        print("  %-3s %-52s %3d  %.1f%%  CI[%.1f%%,%.1f%%]" %
              (f["code"] or "-", f["label"], f["count"], 100 * f["share"],
               100 * f["ci95"][0], 100 * f["ci95"][1]))
    print("\nestimates:")
    for e in ests:
        print("  %-46s %3d/%d = %.1f%%  CI[%.1f%%,%.1f%%]" %
              (e["metric"], e["count"], e["n"], 100 * e["share"],
               100 * e["ci95"][0], 100 * e["ci95"][1]))


if __name__ == "__main__":
    main()
