#!/usr/bin/env python3
"""Population precision from the stratified audit, with an honest interval.

The sample is NOT a simple random draw -- stage 1 forces one row from every
observed (source_kind | scope | family) stratum, so rare strata are massively
over-represented and a raw pass-count over the sample would not estimate the
corpus. Two corrections are applied:

  * Horvitz-Thompson ratio estimator. Each sampled row carries weight
    N_h / n_h for its stratum h, so an over-sampled stratum contributes in
    proportion to its true population share, not its sample share.
  * Paper-level cluster bootstrap for the interval. Assertions from one paper
    share a parser path, a docling conversion and an author's phrasing, so they
    are not independent; a binomial interval over 150 rows would be far too
    narrow. Resampling PAPERS with replacement propagates that correlation.

Usage: estimate.py [suffix]   (matches the sample/verify suffix, e.g. _holdout)
"""
import json
import random
import sys
import collections
from pathlib import Path

OUT = Path(__file__).resolve().parent
SUFFIX = sys.argv[1] if len(sys.argv) > 1 else ""
B = 10000
SEED = 20260805


def main():
    man = json.loads((OUT / ("precision_sample_manifest%s.json" % SUFFIX)).read_text())
    aud = json.loads((OUT / ("precision_audit%s.json" % SUFFIX)).read_text())
    rows = aud["rows"]
    by_uid = {r["assertion_uid"]: r for r in rows}

    # population size per stratum, from the manifest's own stratum bookkeeping
    N_h = man.get("stratum_population") or {}
    if not N_h:
        # recompute from the population the sampler saw
        N_h = collections.Counter()
        for rec in man.get("records", []):
            N_h[rec.get("_stratum") or rec.get("stratum")] += 0
    n_h = collections.Counter()
    strat = {}
    for rec in man.get("records", []):
        uid = rec.get("assertion_uid") or rec.get("uid")
        h = rec.get("_stratum") or rec.get("stratum") or "%s|%s|%s" % (
            rec.get("source_kind"), rec.get("bound_at_scope"), rec.get("family"))
        strat[uid] = h
        if uid in by_uid:
            n_h[h] += 1
    pop_h = man.get("population_stratum_counts")
    if not pop_h:
        raise SystemExit("manifest lacks population stratum counts; rerun sample.py")

    def ht(sel):
        num = den = 0.0
        for uid in sel:
            r = by_uid.get(uid)
            if r is None:
                continue
            h = strat[uid]
            w = pop_h[h] / float(n_h[h])
            den += w
            num += w * (1.0 if r["verdict"] == "correct" else 0.0)
        return num / den if den else float("nan")

    sel_all = [uid for uid in strat if uid in by_uid]
    point = ht(sel_all)

    by_paper = collections.defaultdict(list)
    for uid in sel_all:
        by_paper[by_uid[uid]["paper_id"]].append(uid)
    papers = sorted(by_paper)
    rng = random.Random(SEED)
    reps = []
    for _ in range(B):
        draw = [papers[rng.randrange(len(papers))] for _ in papers]
        sel = [uid for p in draw for uid in by_paper[p]]
        v = ht(sel)
        if v == v:
            reps.append(v)
    reps.sort()
    lo = reps[int(0.025 * len(reps))]
    hi = reps[int(0.975 * len(reps)) - 1]

    # A bootstrap cannot bound a rate it never observed: with zero failures every
    # resample is also all-correct and the interval collapses to [1,1], which
    # would assert perfection rather than measure it. Report the zero-failure
    # bound instead, at both ends of the clustering assumption -- rows treated as
    # independent (n=150) and the worst case where a paper's rows are perfectly
    # correlated so only the 21 papers count as independent evidence.
    n_err = sum(1 for u in sel_all if by_uid[u]["verdict"] != "correct")
    zero_failure = None
    if n_err == 0:
        zero_failure = {
            "rule_of_three_rows": round(3.0 / len(sel_all), 5),
            "rule_of_three_paper_clusters": round(3.0 / len(papers), 5),
            "reading": ("0 errors in %d rows across %d papers bounds the corpus "
                        "error rate at <=%.1f%% if rows are independent and "
                        "<=%.1f%% under complete within-paper correlation; the "
                        "bootstrap interval is degenerate and is not the bound"
                        % (len(sel_all), len(papers), 300.0 / len(sel_all),
                           300.0 / len(papers))),
        }

    res = {
        "suffix": SUFFIX or "primary",
        "observed_errors": n_err,
        "zero_failure_bound_on_error_rate": zero_failure,
        "sampled_rows": len(sel_all),
        "papers_in_sample": len(papers),
        "unweighted_correct": sum(1 for u in sel_all if by_uid[u]["verdict"] == "correct"),
        "ht_precision_point": round(point, 5),
        "ht_precision_ci95_cluster_bootstrap":
            None if n_err == 0 else [round(lo, 5), round(hi, 5)],
        "ht_precision_ci95_degenerate": n_err == 0,
        "bootstrap_replicates": B,
        "note": ("HT weights by stratum population share; interval resamples PAPERS "
                 "with replacement, so within-paper correlation is not treated as "
                 "independent evidence"),
    }
    (OUT / ("precision_estimate%s.json" % SUFFIX)).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
