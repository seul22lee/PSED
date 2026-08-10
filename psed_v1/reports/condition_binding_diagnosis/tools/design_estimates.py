#!/usr/bin/env python3
"""READ-ONLY. Correction #5 — replace binomial CIs with design-based estimates.

The sample is a THREE-STAGE, UNEQUAL-PROBABILITY design (2/paper quota +
proportional allocation + coverage top-ups). A simple binomial interval assumes
i.i.d. draws from the population and is therefore wrong here — it both mis-centres
the estimate (papers with few records are over-represented by the quota) and
mis-states the width.

Method:
  1. Monte-Carlo inclusion probabilities pi_i: re-run the EXACT sampler R times with
     different seeds and count how often each population record is drawn.
  2. Horvitz-Thompson point estimate  P_hat = sum(y_i/pi_i) / sum(1/pi_i)  over the
     realised sample, i.e. the population proportion, not the sample proportion.
  3. Uncertainty by a paper-level (cluster) bootstrap: papers are the primary
     sampling units, so resampling papers with replacement respects the clustering
     that records within a paper are not independent.
"""
import json, random, statistics
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
R_MC = 400          # Monte-Carlo replicates for inclusion probabilities
R_BOOT = 2000       # cluster-bootstrap replicates
TARGET = 120


def draw(pop, seed):
    """Faithful re-implementation of draw_sample.py stages 1+2 (the random part).
    Coverage top-ups are deterministic given stages 1-2 and add <=1 record per
    stratum, so they are excluded from the probability model and their records are
    reported separately."""
    rng = random.Random(seed)
    by_paper = defaultdict(list)
    for r in pop:
        by_paper[r["paper_id"]].append(r)
    for k in by_paper:
        by_paper[k].sort(key=lambda x: str(x["record_id"]))
    chosen = set()
    for doi in sorted(by_paper):
        pool = by_paper[doi]
        for p in rng.sample(pool, min(2, len(pool))):
            chosen.add(p["record_id"])
    remaining = TARGET - len(chosen)
    cap = int(0.15 * TARGET)
    total = len(pop)
    alloc = {d: min(cap - 2, int(round(remaining * len(by_paper[d]) / total))) for d in by_paper}
    order = sorted(alloc, key=lambda d: (-len(by_paper[d]), d))
    while sum(max(0, v) for v in alloc.values()) > remaining:
        for d in order:
            if alloc[d] > 0:
                alloc[d] -= 1
                if sum(max(0, v) for v in alloc.values()) <= remaining:
                    break
    while sum(max(0, v) for v in alloc.values()) < remaining:
        for d in order:
            avail = [x for x in by_paper[d] if x["record_id"] not in chosen]
            if alloc[d] < cap - 2 and len(avail) > alloc[d]:
                alloc[d] += 1
                if sum(max(0, v) for v in alloc.values()) >= remaining:
                    break
        else:
            break
    for doi in sorted(alloc):
        avail = [x for x in by_paper[doi] if x["record_id"] not in chosen]
        for p in rng.sample(avail, min(max(0, alloc[doi]), len(avail))):
            chosen.add(p["record_id"])
    return chosen


def main():
    pop = json.loads((OUT / "corpus_population_manifest.json").read_text())["records"]
    audit = json.loads((OUT / "random_sample_audit.json").read_text())["rows"]
    man = json.loads((OUT / "random_sample_manifest.json").read_text())
    topups = {e["record_id"] for e in man["replacement_or_exclusion_events"]
              if e.get("event") == "coverage_topup"}

    # ---- 1. Monte-Carlo inclusion probabilities ----
    cnt = Counter()
    for i in range(R_MC):
        cnt.update(draw(pop, 900000 + i))
    N = len(pop)
    pi = {r["record_id"]: max(cnt[r["record_id"]], 1) / R_MC for r in pop}
    npap = defaultdict(int)
    for r in pop:
        npap[r["paper_id"]] += 1

    rows = [a for a in audit if a["record_id"] not in topups]
    dropped = len(audit) - len(rows)

    def ht(pred):
        """Horvitz-Thompson ratio estimator of a population proportion."""
        num = sum(1.0 / pi[a["record_id"]] for a in rows if pred(a))
        den = sum(1.0 / pi[a["record_id"]] for a in rows)
        return num / den if den else 0.0

    def boot(pred):
        by_paper = defaultdict(list)
        for a in rows:
            by_paper[a["paper_id"]].append(a)
        papers = sorted(by_paper)
        rng = random.Random(4242)
        vals = []
        for _ in range(R_BOOT):
            pick = [rng.choice(papers) for _ in papers]
            num = den = 0.0
            for p in pick:
                for a in by_paper[p]:
                    w = 1.0 / pi[a["record_id"]]
                    den += w
                    if pred(a):
                        num += w
            if den:
                vals.append(num / den)
        vals.sort()
        lo = vals[int(0.025 * len(vals))]
        hi = vals[int(0.975 * len(vals)) - 1]
        return lo, hi

    METRICS = [
        ("record_supported_as_physical_experiment",
         lambda a: a["supported_as_physical_experiment"] == "yes"),
        ("record_not_a_physical_experiment",
         lambda a: a["supported_as_physical_experiment"] == "no"),
        ("record_uncertain", lambda a: a["supported_as_physical_experiment"] == "uncertain"),
        ("record_is_model_or_simulation",
         lambda a: a.get("paper_ground_truth_entity_kind") == "simulation_run_or_profile"),
        ("record_is_one_point_of_a_continuous_run",
         lambda a: a.get("run_structure") == "one_continuous_run"
         and a["current_record_kind"] == "series_member_experiment"),
        ("verdict_backed_by_an_exact_span",
         lambda a: a.get("classification_method") in ("paper_verified", "caption_inferred")),
        ("verdict_heuristic_only",
         lambda a: a.get("classification_method") == "heuristic"),
        ("has_missing_source_supported_condition", lambda a: bool(a["missing_conditions"])),
        ("has_over_broadcast_condition", lambda a: bool(a["over_broadcast_conditions"])),
        ("pressure_applicable_and_lost", lambda a: a.get("pressure_applicable_and_lost") is True),
    ]
    ests = []
    for name, pred in METRICS:
        p = ht(pred)
        lo, hi = boot(pred)
        raw = sum(1 for a in rows if pred(a))
        ests.append({"metric": name, "sample_count": raw, "sample_n": len(rows),
                     "sample_share": round(raw / len(rows), 4),
                     "ht_population_estimate": round(p, 4),
                     "cluster_bootstrap_95": [round(lo, 4), round(hi, 4)]})
    out = {
        "design": ("3-stage unequal-probability: 2/paper quota + proportional "
                   "allocation (15% cap) + deterministic coverage top-ups"),
        "estimator": "Horvitz-Thompson ratio estimator with Monte-Carlo inclusion probabilities",
        "uncertainty": "paper-level (cluster) bootstrap, %d replicates" % R_BOOT,
        "mc_replicates_for_inclusion_probabilities": R_MC,
        "coverage_topup_records_excluded_from_estimation": dropped,
        "note": ("Binomial/Wilson intervals were REMOVED: they assume i.i.d. draws, "
                 "which this design violates. The quota over-samples small papers, so "
                 "the sample share and the population estimate differ systematically."),
        "population_n": N,
        "estimates": ests,
    }
    (OUT / "design_based_estimates.json").write_text(json.dumps(out, indent=1))
    print("design-based estimates (n=%d used, %d top-ups excluded, N=%d)"
          % (len(rows), dropped, N))
    for e in ests:
        print("  %-46s sample %5.1f%%   population %5.1f%%  boot95 [%.1f%%, %.1f%%]"
              % (e["metric"], 100 * e["sample_share"], 100 * e["ht_population_estimate"],
                 100 * e["cluster_bootstrap_95"][0], 100 * e["cluster_bootstrap_95"][1]))


if __name__ == "__main__":
    main()
