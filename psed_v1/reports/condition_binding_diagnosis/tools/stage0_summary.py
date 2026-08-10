#!/usr/bin/env python3
"""READ-ONLY. Stage 0 step 3 — per-paper node vs unique-case counts, corrected
case-count RANGES, pressure resolution at series/run scope, and completion status."""
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis" / "stage0"
DIAG = REPO / "reports" / "condition_binding_diagnosis"
KB = REPO / "02_extraction" / "output"


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


# how many EXPERIMENT/RUN cases each entity class contributes
#   lo/hi bracket the uncertainty that remains after Stage 0
CASE_YIELD = {
    "continuous_trace":            (1, 1),      # one run, however densely digitised
    "experimental_profile":        (1, 1),      # one coated specimen
    "multi_output_measurement":    (1, 1),      # one specimen scanned across a coordinate
    "discrete_experimental_sweep": (None, None),  # = number of genuinely distinct settings
    "simulation":                  (1, 1),      # one simulation run (not an experiment)
    "model_sweep":                 (1, 1),      # one parameter sweep (not an experiment)
    "imported_literature_data":    (1, 1),      # one cited profile (not this paper's experiment)
    "fit":                         (1, 1),
    "derived_representation":      (0, 0),      # a redraw of another entity
    "conceptual_figure":           (0, 0),
    "unknown":                     (1, None),   # at least one; upper bound unresolved
}
EXPERIMENTAL = {"continuous_trace", "experimental_profile",
                "multi_output_measurement", "discrete_experimental_sweep"}


def main():
    rows = J(OUT / "entity_audit.json")["rows"]
    src = J(OUT / "source_entities.json")
    trig = {t["paper_id"] for t in J(DIAG / "full_paper_audit_triggers.json")["triggers"]}
    by_paper = defaultdict(list)
    for r in rows:
        by_paper[r["paper_id"]].append(r)

    summaries, tot = [], Counter()
    for doi in sorted(trig):
        ents = by_paper[doi]
        nodes = src["node_counts_per_paper"].get(doi, 0)
        cls = Counter(e["classification"] for e in ents)
        lo, hi, unbounded = 0, 0, 0
        for e in ents:
            c = e["classification"]
            a, b = CASE_YIELD[c]
            if c == "discrete_experimental_sweep":
                # upper bound from STATED settings when the paper enumerates them;
                # otherwise the sweep size is UNRESOLVED (the digitised point count is
                # digitisation density, not a count of depositions)
                st = e.get("stated_setting_count")
                a, b = (1, st) if st else (1, None)
            if c == "unknown":
                a, b = (1, None)
            lo += a
            if b is None:
                unbounded += 1
                hi = None          # one open-ended entity opens the paper's bound
            elif hi is not None:
                hi += b
        exp_lo = exp_hi = 0
        for e in ents:
            if e["classification"] not in EXPERIMENTAL:
                continue
            c = e["classification"]
            if c == "discrete_experimental_sweep":
                exp_lo += 1
                st = e.get("stated_setting_count")
                exp_hi = (exp_hi + st) if (st and exp_hi is not None) else None
            else:
                exp_lo += 1
                if exp_hi is not None:
                    exp_hi += 1
        pres = Counter("%s/%s" % (e["pressure_applicable_scope"],
                                  e["pressure_applicable_status"]) for e in ents)
        resolved_p = sum(v for k, v in pres.items() if k.endswith("/resolved"))
        unresolved = sum(1 for e in ents
                         if e["classification_confidence"] in
                         ("conflicting_signals", "insufficient_corroboration"))
        summaries.append({
            "paper_id": doi,
            "audit_status": "complete",
            "record_nodes_now": nodes,
            "unique_source_entities": len(ents),
            "node_to_entity_ratio": round(nodes / len(ents), 1) if ents else None,
            "corrected_case_count_low": lo,
            "corrected_case_count_high": hi,
            "entities_with_unbounded_sweep_size": unbounded,
            "experimental_case_count_low": exp_lo,
            "experimental_case_count_high": exp_hi,
            "non_experimental_entities": sum(
                1 for e in ents if e["classification"] not in EXPERIMENTAL),
            "classification_breakdown": dict(cls),
            "entities_unresolved": unresolved,
            "pressure_scope_breakdown": dict(pres),
            "pressure_resolved_entities": resolved_p,
            "pressure_entities_with_no_applicable_assertion": pres.get("None/None", 0),
        })
        tot["nodes"] += nodes
        tot["entities"] += len(ents)
        tot["lo"] += lo
        tot["hi"] += (hi or 0)
        tot["unbounded"] += unbounded
        tot["exp_lo"] += exp_lo
        tot["exp_hi"] += (exp_hi or 0)
        tot["unresolved"] += unresolved

    (OUT / "paper_full_audits.json").write_text(json.dumps(
        {"triggered_papers": len(trig), "completed": len(summaries),
         "totals": dict(tot), "summaries": summaries}, indent=1))
    with open(OUT / "paper_full_audits.csv", "w", newline="") as fh:
        cols = ["paper_id", "audit_status", "record_nodes_now", "unique_source_entities",
                "node_to_entity_ratio", "corrected_case_count_low", "corrected_case_count_high",
                "entities_with_unbounded_sweep_size",
                "experimental_case_count_low", "experimental_case_count_high",
                "non_experimental_entities", "entities_unresolved",
                "pressure_resolved_entities", "pressure_entities_with_no_applicable_assertion"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for s in summaries:
            w.writerow(s)

    print("%-36s %6s %7s %6s  %-15s %-15s %5s" %
          ("paper", "nodes", "entities", "ratio", "cases(lo-hi)", "experimental", "unres"))
    for s in summaries:
        print("%-36s %6d %7d %5.1fx  %-15s %-15s %5d" % (
            s["paper_id"], s["record_nodes_now"], s["unique_source_entities"],
            s["node_to_entity_ratio"],
            "%d-%s" % (s["corrected_case_count_low"],
                       s["corrected_case_count_high"] if s["corrected_case_count_high"] is not None else "?"),
            "%d-%s" % (s["experimental_case_count_low"],
                       s["experimental_case_count_high"] if s["experimental_case_count_high"] is not None else "?"),
            s["entities_unresolved"]))
    print("\nTOTAL nodes=%d entities=%d  corrected cases >=%d  experimental >=%d"
          % (tot["nodes"], tot["entities"], tot["lo"], tot["exp_lo"]))
    print("  %d entities have an UNBOUNDED sweep size (paper does not enumerate its "
          "settings); their upper bound is deliberately left open rather than taken "
          "from the digitised point count." % tot["unbounded"])
    print("\nentity classification (all 24 papers):")
    for k, v in Counter(r["classification"] for r in rows).most_common():
        print("   %-30s %4d" % (k, v))


if __name__ == "__main__":
    main()
