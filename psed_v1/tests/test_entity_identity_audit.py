#!/usr/bin/env python3
"""The entity audit must count entities and links as different things, and hide nothing.

Two numbers get confused whenever a knowledge graph is rendered as a tree: how many
Measurements exist, and how many times a Measurement appears under some Case. A
Measurement linked to ten cases is one Measurement and ten incidences, and summing the
second while calling it the first inflates every card in a UI.

The other thing these tests pin is that no multi-valued relation is silently reduced to
its first element. That is exactly the shortcut the workbench took, and the audit exists
to measure it rather than inherit it.

Run:  python3 tests/test_entity_identity_audit.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
EI = W / "_diagnostics" / "entity_identity"

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    mp = EI / "entity_cardinality_matrix.json"
    cp = EI / "entity_identity_conflicts.json"
    ip = EI / "workbench_hierarchy_implications.json"
    for p in (mp, cp, ip):
        ok("artifact %s exists" % p.name, p.exists(), str(p))
    if not (mp.exists() and cp.exists() and ip.exists()):
        print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
        return 1
    Mx = json.loads(mp.read_text())
    Cf = json.loads(cp.read_text())
    Im = json.loads(ip.read_text())
    matrix = {r["relation"]: r for r in Mx["matrix"]}

    print("=== A. entity counts and link incidences are separate numbers ===")
    ok("A: both are reported", "active8_unique_entities" in Mx
       and "active8_link_incidences" in Mx)
    cm = matrix["Case -> Measurement"]
    ok("A: Case->Measurement incidences exceed cases with a measurement",
       cm["links"] >= cm["1"] + cm["2+"], (cm["links"], cm["1"], cm["2+"]))
    ok("A: incidences are not equal to the unique entity count when 2+ exists",
       cm["2+"] == 0 or cm["links"] != Mx["active8_unique_entities"]["meas"],
       (cm["links"], Mx["active8_unique_entities"]["meas"]))
    ok("A: every relation row carries both sides' unique counts",
       all(r["unique_left"] and r["unique_right"] is not None for r in Mx["matrix"]))
    ok("A: every relation row reports 0/1/2+/max/links",
       all(set(("0", "1", "2+", "max", "links")) <= set(r) for r in Mx["matrix"]))

    print("=== B. many-to-many relations are surfaced, not collapsed ===")
    mc = matrix["Measurement -> Case"]
    ok("B: multi-case Measurements are counted", mc["2+"] == Mx["multi_case_measurements"],
       (mc["2+"], Mx["multi_case_measurements"]))
    ok("B: the maximum is reported, not just the existence",
       mc["max"] == Mx["max_cases_per_measurement"] and mc["max"] >= 2, mc["max"])
    sc = matrix["ResultSeries -> Case"]
    ok("B: ResultSeries reach cases through their producer", sc["links"] > 0, sc["links"])
    ok("B: and a series can reach more than one case",
       sc["2+"] > 0 or mc["2+"] == 0, (sc["2+"], mc["2+"]))
    ok("B: the audit never reports a relation as 1:1 when max exceeds 1",
       all(r["max"] <= 1 or r["2+"] > 0 for r in Mx["matrix"]))

    print("=== C. the measurement granularity finding is quantified ===")
    ok("C: entity and act counts are both reported",
       Mx["measurement_entities"] >= Mx["distinct_measurement_acts"],
       (Mx["measurement_entities"], Mx["distinct_measurement_acts"]))
    ok("C: the collapse is non-zero, so per-curve minting is demonstrated",
       Mx["measurement_entities"] > Mx["distinct_measurement_acts"],
       Mx["measurement_entities"] - Mx["distinct_measurement_acts"])
    ps = matrix["Producer -> ResultSeries"]
    ok("C: producer->series max is reported", ps["max"] >= 1, ps["max"])
    ok("C: and overminting is classified, not merely observed",
       Cf["by_classification"].get("MEASUREMENT_OVERMINTING", 0) > 0,
       Cf["by_classification"])

    print("=== D. the physical layer is measured honestly ===")
    ok("D: sample and run counts are reported",
       "sample" in Mx["active8_unique_entities"] and "run" in Mx["active8_unique_entities"],
       Mx["active8_unique_entities"])
    ok("D: multi-sample cases are counted", "multi_sample_cases" in Mx)
    ok("D: the largest case's sample count is reported",
       Mx["max_samples_per_case"] >= 1, Mx["max_samples_per_case"])
    ok("D: a case carrying several samples is classified as a condition case",
       Mx["max_samples_per_case"] < 2
       or Cf["by_classification"].get("CONDITION_CASE_NOT_PHYSICAL_RUN", 0) > 0,
       Cf["by_classification"])

    print("=== E. every classified conflict carries its evidence ===")
    ok("E: conflicts exist and are classified", Cf["count"] > 0, Cf["count"])
    for c in Cf["conflicts"]:
        pass
    ok("E: every conflict names a paper, type, ids and classification",
       all(c.get("paper") and c.get("entity_type") and c.get("entity_ids")
           and c.get("classification") for c in Cf["conflicts"]))
    ok("E: every conflict states a reason",
       all(c.get("reasons") for c in Cf["conflicts"]))
    ok("E: every conflict carries a confidence",
       all(c.get("confidence") for c in Cf["conflicts"]))
    vocab = {"EXPECTED_CARDINALITY", "CONDITION_CASE_NOT_PHYSICAL_RUN", "CASE_OVERGROUPING",
             "CASE_OVERSPLITTING", "SAMPLE_DUPLICATION", "SAMPLE_OVERMERGE",
             "RUN_OVERPROPAGATION", "RUN_IDENTITY_EXTRACTION_GAP", "RUN_OVERMERGE",
             "RUN_OVERSPLIT", "MEASUREMENT_OVERMINTING", "MEASUREMENT_OVERMERGE",
             "RESULT_SERIES_SPANS_MULTIPLE_CASES", "PLOT_REPRESENTATION_DUPLICATION",
             "LINKAGE_JOIN_ERROR", "INSUFFICIENT_EVIDENCE"}
    bad = {c["classification"] for c in Cf["conflicts"]} - vocab
    ok("E: classifications come from the controlled vocabulary", not bad, sorted(bad))
    ok("E: not every issue is reduced to one category",
       len(Cf["by_classification"]) >= 3, Cf["by_classification"])

    print("=== F. the workbench implications are stated with reasons ===")
    for k, v in Im.items():
        ok("F: %s answered" % k[:44], v.get("answer") in ("YES", "NO", "CONDITIONALLY")
           and v.get("reason"), v)
    ok("F: at least one current UI assumption is rejected",
       any(v["answer"] == "NO" for v in Im.values()), Im)

    print("=== G. the audit changed no science ===")
    src = (W / "_diagnostics" / "entity_identity"
           / "build_entity_identity_audit.py").read_text()
    ok("G: the generator never writes outside its own diagnostic directory",
       'OUT / ' in src and "write_text" in src
       and not any(t in src for t in ("semantic_pilot_9papers/papers", "ald_ontology")))
    ok("G: it declares itself read-only", "Read-only" in src)
    ok("G: scopes actually audited are recorded", Mx["scopes_included"], Mx["scopes_included"])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
