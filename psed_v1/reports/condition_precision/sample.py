#!/usr/bin/env python3
"""READ-ONLY. Reproducible stratified sample of the BOUND condition assertions.

Strata required by the request: evidence source (methods/caption/body/series_label),
bound scope (method/figure/panel/series), entity class (case/trace/profile/simulation/
imported literature/unresolved), and quantity family (pressure, exposure, temperature,
flow, pulse, purge, cycle, geometry, GPC, model parameter).
"""
import csv, json, random, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KB = REPO / "papers"              # papers/<doi>/resolved/
OUT = REPO / "reports" / "condition_precision"
SEED = 20260804
# A held-out draw under a different seed checks that precision did not simply
# follow the rows the first draw happened to expose: `sample.py <seed> <suffix>`.
if len(sys.argv) > 1:
    SEED = int(sys.argv[1])
SUFFIX = sys.argv[2] if len(sys.argv) > 2 else ""
TARGET = 150

FAMILY = {
    "pressure": ("working_pressure", "base_pressure", "generic_pressure",
                 "precursor_partial_pressure", "co_reactant_partial_pressure",
                 "carrier_gas_partial_pressure", "bubbler_pressure"),
    "exposure": ("exposure",),
    "temperature": ("deposition_temperature", "temperature", "hot_wire_temperature"),
    "flow": ("flow_rate",),
    "pulse": ("pulse_time",),
    "purge": ("purge_time",),
    "cycle": ("cycle_number",),
    "geometry": ("feature_height", "feature_width", "feature_length", "aspect_ratio",
                 "pore_diameter", "hydraulic_diameter"),
    "gpc": ("growth_per_cycle", "film_thickness"),
}


def family(q):
    for f, qs in FAMILY.items():
        if q in qs:
            return f
    return "model_parameter"


def main():
    pool = []
    for ef in sorted(KB.glob("*/resolved/entities.json")):
        doi = ef.parent.parent.name
        for e in json.loads(ef.read_text()):
            for i, b in enumerate(e.get("bound_conditions") or []):
                pool.append({
                    "assertion_uid": "%s::%s::%d" % (doi, e["entity_id"], i),
                    "paper_id": doi, "entity_id": e["entity_id"],
                    "entity_class": e["entity_class"],
                    "classification": e["classification"],
                    "fig_docling_index": e["fig_docling_index"],
                    "printed_figure_number": e["printed_figure_number"],
                    "panel": e["panel"], "source_series": e["source_series"],
                    "quantity": b["quantity"], "value": b["value"], "unit": b["unit"],
                    "species": b.get("species"), "of_reactant": b.get("of_reactant"),
                    "species_basis": b.get("species_basis"),
                    "assertion_status": b.get("assertion_status"),
                    "evidence_kind": b.get("evidence_kind"),
                    "source_kind": b.get("source_kind"),
                    "bound_at_scope": b.get("bound_at_scope"),
                    "declared_scope": b.get("scope"),
                    "raw_evidence": b.get("raw_evidence"),
                    "evidence_locator": b.get("evidence_locator"),
                    "reference_work": b.get("reference_work"),
                    "figure_common": b.get("figure_common"),
                    "family": family(b["quantity"]),
                })
    for p in pool:
        p["_stratum"] = "%s|%s|%s" % (p["source_kind"], p["bound_at_scope"], p["family"])

    rng = random.Random(SEED)
    pool.sort(key=lambda p: p["assertion_uid"])
    strata = defaultdict(list)
    for p in pool:
        strata[p["_stratum"]].append(p)

    selected, chosen = [], set()
    # stage 1: >=1 from every stratum that exists
    for k in sorted(strata):
        p = rng.choice(strata[k])
        selected.append(p); chosen.add(p["assertion_uid"])
    # stage 2: coverage of every required dimension value
    dims = [("source_kind", lambda p, v: p["source_kind"] == v,
             ["methods", "caption", "body", "series_label"]),
            ("bound_at_scope", lambda p, v: p["bound_at_scope"] == v,
             ["method", "figure", "panel", "series"]),
            ("classification", lambda p, v: p["classification"] == v,
             ["continuous_trace", "experimental_profile", "discrete_experimental_sweep",
              "multi_output_measurement", "simulation", "model_sweep",
              "imported_literature_data", "fit", "unknown"]),
            ("family", lambda p, v: p["family"] == v, list(FAMILY) + ["model_parameter"])]
    for name, pred, vals in dims:
        for v in vals:
            have = sum(1 for s in selected if pred(s, v))
            need = max(0, 3 - have)
            avail = [p for p in pool if pred(p, v) and p["assertion_uid"] not in chosen]
            for p in rng.sample(avail, min(need, len(avail))):
                selected.append(p); chosen.add(p["assertion_uid"])
    # stage 3: proportional fill to TARGET
    rest = [p for p in pool if p["assertion_uid"] not in chosen]
    n = max(0, TARGET - len(selected))
    for p in rng.sample(rest, min(n, len(rest))):
        selected.append(p); chosen.add(p["assertion_uid"])

    selected.sort(key=lambda p: p["assertion_uid"])
    for i, p in enumerate(selected):
        p["sample_index"] = i + 1

    man = {
        "random_seed": SEED, "population_bound_assertions": len(pool),
        "sample_n": len(selected),
        "algorithm": ("stage1 one per observed stratum (source_kind|scope|family); "
                      "stage2 top-up to >=3 per required dimension value; "
                      "stage3 proportional random fill to the target"),
        "strata_observed": len(strata),
        # per-stratum POPULATION sizes: stage 1 forces one row from every stratum,
        # so rare strata are over-sampled and any population-level rate must be
        # reweighted by N_h. Without these the audit can only describe the sample.
        "population_stratum_counts": dict(Counter(p["_stratum"] for p in pool)),
        "sample_stratum_counts": dict(Counter(p["_stratum"] for p in selected)),
        "coverage": {
            "source_kind": dict(Counter(p["source_kind"] for p in selected)),
            "bound_at_scope": dict(Counter(p["bound_at_scope"] for p in selected)),
            "classification": dict(Counter(p["classification"] for p in selected)),
            "family": dict(Counter(p["family"] for p in selected)),
        },
        "population_coverage": {
            "source_kind": dict(Counter(p["source_kind"] for p in pool)),
            "bound_at_scope": dict(Counter(p["bound_at_scope"] for p in pool)),
            "classification": dict(Counter(p["classification"] for p in pool)),
            "family": dict(Counter(p["family"] for p in pool)),
        },
        "selected_uids": [p["assertion_uid"] for p in selected],
        "records": selected,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("precision_sample_manifest%s.json" % SUFFIX)).write_text(json.dumps(man, indent=1, ensure_ascii=False))
    print("population %d bound assertions, %d strata" % (len(pool), len(strata)))
    print("sample n=%d (seed %d)" % (len(selected), SEED))
    for k, v in man["coverage"].items():
        print("  %-16s %s" % (k, v))


if __name__ == "__main__":
    main()
