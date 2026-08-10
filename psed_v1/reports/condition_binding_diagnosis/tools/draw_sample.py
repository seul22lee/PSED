#!/usr/bin/env python3
"""READ-ONLY. §B — reproducible stratified random sample of >=100 records.

Design (documented, seeded, no post-hoc substitution):
  Stage 1  quota: 2 random records per paper (all papers with >=2 records; else all).
  Stage 2  proportional allocation of the remainder, capped at 15% of the RANDOM
           portion for any single paper.
  Stage 3  coverage top-ups: strata required by B.4-B.8 that stage 1+2 missed are
           filled by drawing additional records from the unsampled pool.
Selected IDs are frozen; nothing is swapped after inspection.
"""
import csv, json, random
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
SEED = 20260803          # fixed, documented
TARGET = 120             # >= 100 required

COND_KEYS = {
    "pressure": ("generic_pressure", "working_pressure", "base_pressure", "total_pressure",
                 "partial_pressure", "chamber_total_pressure", "bubbler_pressure",
                 "precursor_partial_pressure", "co_reactant_partial_pressure",
                 "reactant_A_partial_pressure", "reactant_B_partial_pressure"),
    "temperature": ("temperature", "deposition_temperature"),
    "pulse_time": ("pulse_time",),
    "purge_time": ("purge_time",),
    "cycle_count": ("cycle_number",),
    "geometry": ("feature_height", "feature_width", "feature_length", "aspect_ratio",
                 "pore_diameter", "hydraulic_diameter", "feature_depth"),
}


def strata(r):
    """Stratum label used for coverage checks and reporting."""
    axis = "condition_axis" if r["kind"] == "series_member_experiment" else (
        "coordinate_axis" if r["kind"] == "profile_experiment" else r["kind"])
    return "%s|%s" % (axis, "model" if r["is_model_result"] or r["relevance"] == "model"
                      else (r["relevance"] or "unknown"))


def main():
    man = json.loads((OUT / "corpus_population_manifest.json").read_text())
    pop = man["records"]
    for r in pop:
        r["_stratum"] = strata(r)
        cq = set(r["ctrl_quantities"])
        for name, keys in COND_KEYS.items():
            r["has_" + name] = bool(cq & set(keys))
        r["has_series_membership"] = bool(r["in_series"])
        # granularity migration marker: split point ids carry the -S<n>-P<nnn> suffix
        r["created_by_granularity_migration"] = "-P" in str(r["record_id"] or "")

    rng = random.Random(SEED)
    by_paper = defaultdict(list)
    for r in pop:
        by_paper[r["paper_id"]].append(r)
    for k in by_paper:
        by_paper[k].sort(key=lambda x: str(x["record_id"]))

    selected, events = [], []
    chosen_ids = set()

    # --- stage 1: >=2 per paper -----------------------------------------
    for doi in sorted(by_paper):
        pool = by_paper[doi]
        take = min(2, len(pool))
        picks = rng.sample(pool, take)
        if len(pool) < 2:
            events.append({"event": "paper_has_fewer_than_2_records", "paper": doi,
                           "n": len(pool)})
        for p in picks:
            p["_stage"] = "quota_per_paper"
            selected.append(p); chosen_ids.add(p["record_id"])

    # --- stage 2: proportional, capped at 15% of the random portion ------
    remaining = TARGET - len(selected)
    cap = int(0.15 * TARGET)
    total = len(pop)
    alloc = {}
    for doi, pool in by_paper.items():
        alloc[doi] = min(cap - 2, int(round(remaining * len(pool) / total)))
    # trim/expand to hit `remaining` deterministically
    order = sorted(alloc, key=lambda d: (-len(by_paper[d]), d))
    while sum(max(0, v) for v in alloc.values()) > remaining:
        for d in order:
            if alloc[d] > 0:
                alloc[d] -= 1
                if sum(max(0, v) for v in alloc.values()) <= remaining:
                    break
    while sum(max(0, v) for v in alloc.values()) < remaining:
        for d in order:
            avail = [x for x in by_paper[d] if x["record_id"] not in chosen_ids]
            if alloc[d] < cap - 2 and len(avail) > alloc[d]:
                alloc[d] += 1
                if sum(max(0, v) for v in alloc.values()) >= remaining:
                    break
        else:
            break
    for doi in sorted(alloc):
        n = max(0, alloc[doi])
        avail = [x for x in by_paper[doi] if x["record_id"] not in chosen_ids]
        n = min(n, len(avail))
        for p in rng.sample(avail, n):
            p["_stage"] = "proportional"
            selected.append(p); chosen_ids.add(p["record_id"])

    # --- stage 3: required-coverage top-ups (B.4-B.8) --------------------
    def covered(pred):
        return any(pred(x) for x in selected)

    reqs = [
        ("profile_experiment_present", lambda x: x["kind"] == "profile_experiment"),
        ("point_level_present", lambda x: x["created_by_granularity_migration"]),
        ("model_present", lambda x: x["is_model_result"] or x["relevance"] == "model"),
        ("experimental_present", lambda x: x["relevance"] == "experimental"),
        ("unresolved_present", lambda x: x["kind"] == "unresolved_experiment_record"),
        ("correlation_present", lambda x: x["kind"] == "correlation_record"),
        ("paper_level_present", lambda x: x["kind"] == "paper_level_record"),
        ("context_conflict_present", lambda x: x["has_context_conflicts"]),
        ("no_context_conflict_present", lambda x: not x["has_context_conflicts"]),
        ("series_member_present", lambda x: x["has_series_membership"]),
        ("non_series_present", lambda x: not x["has_series_membership"]),
    ]
    for name in COND_KEYS:
        reqs.append(("with_" + name, (lambda n: (lambda x: x["has_" + n]))(name)))
        reqs.append(("without_" + name, (lambda n: (lambda x: not x["has_" + n]))(name)))
    for name, pred in reqs:
        if covered(pred):
            continue
        avail = [x for x in pop if x["record_id"] not in chosen_ids and pred(x)]
        if not avail:
            events.append({"event": "stratum_empty_in_population", "stratum": name})
            continue
        p = rng.choice(avail)
        p["_stage"] = "coverage_topup:" + name
        selected.append(p); chosen_ids.add(p["record_id"])
        events.append({"event": "coverage_topup", "stratum": name, "record_id": p["record_id"]})

    selected.sort(key=lambda x: (x["paper_id"], str(x["record_id"])))
    for i, r in enumerate(selected):
        r["sample_index"] = i + 1

    manifest = {
        "random_seed": SEED,
        "sampling_algorithm": ("stage1 quota 2/paper (uniform w/o replacement); "
                               "stage2 proportional-to-record-count, capped at 15% of target; "
                               "stage3 coverage top-ups for required strata. "
                               "python random.Random(seed).sample, records sorted by id "
                               "before sampling for determinism."),
        "target_n": TARGET,
        "actual_n": len(selected),
        "population_n": len(pop),
        "papers_in_population": len(by_paper),
        "papers_represented": len({r["paper_id"] for r in selected}),
        "per_paper_cap": cap,
        "stage_counts": dict(Counter(r["_stage"].split(":")[0] for r in selected)),
        "stratum_counts": dict(Counter(r["_stratum"] for r in selected)),
        "coverage": {name: sum(1 for x in selected if pred(x)) for name, pred in reqs},
        "replacement_or_exclusion_events": events,
        "selected_record_ids": [r["record_id"] for r in selected],
        "records": selected,
    }
    (OUT / "random_sample_manifest.json").write_text(json.dumps(manifest, indent=1))
    cols = ["sample_index", "paper_id", "record_id", "_stage", "_stratum", "kind",
            "relevance", "granularity", "is_model_result", "in_series",
            "figure_number", "fig_docling_index", "panel", "series_name",
            "coordinate", "measurand", "n_points", "has_context_conflicts",
            "created_by_granularity_migration"] + ["has_" + k for k in COND_KEYS]
    with open(OUT / "random_sample_manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in selected:
            w.writerow(r)
    print("seed=%d  n=%d  papers=%d/%d  cap=%d" %
          (SEED, len(selected), manifest["papers_represented"], len(by_paper), cap))
    print("stages:", manifest["stage_counts"])
    print("strata:", manifest["stratum_counts"])
    miss = [k for k, v in manifest["coverage"].items() if v == 0]
    print("uncovered strata:", miss or "none")


if __name__ == "__main__":
    main()
