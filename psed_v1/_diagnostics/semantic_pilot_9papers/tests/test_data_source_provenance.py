#!/usr/bin/env python3
"""Series-level `data_source` provenance.

`data_source` says where a curve's NUMBERS came from -- an instrument, or a model. The
extraction layer answers that at panel scope, which is the finest scope it has, and a
panel may hold a measured curve together with the model curve drawn over it. Broadcasting
the panel value to both made the model curve claim to be measured.

These tests fix the precedence: positive series evidence overrides the panel, `unknown`
preserves it, and neither scope knowing means the answer stays None. Producer class is
never consulted -- the tests below assert that explicitly, because "it is a SimulationRun,
so call it simulated" would state as provenance what was only ever a classification.

Run:  python3 tests/test_data_source_provenance.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
import pilot_semantics as PS          # noqa: E402

PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]
F = PS.effective_data_source
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def sem(pid, n):
    return json.loads((W / "papers" / pid / "semantic" / ("%s.json" % n)).read_text())


def ent(kind, **kw):
    e = {"entity_id": "E::x", "entity_class": "ExperimentSeries",
         "series_source_kind": kind}
    e.update(kw)
    return e


def main():
    print("=== A. positive calculated override ===")
    ok("A: a calculated series in a measured panel is not measured",
       F("measured", ent("calculated")) == "simulated", F("measured", ent("calculated")))

    print("=== B. positive fitted override ===")
    ok("B: a fit in a measured panel is not measured",
       F("measured", ent("fitted")) == "simulated", F("measured", ent("fitted")))

    print("=== C. positive measured override ===")
    ok("C: a measured series in a simulated panel is measured",
       F("simulated", ent("measured")) == "measured", F("simulated", ent("measured")))

    print("=== D. unknown preserves panel provenance ===")
    ok("D: unknown keeps the panel's measured evidence",
       F("measured", ent("unknown")) == "measured", F("measured", ent("unknown")))
    ok("D: unknown keeps the panel's simulated evidence",
       F("simulated", ent("unknown")) == "simulated", F("simulated", ent("unknown")))
    # `unknown` is the resolver saying the series carried no evidence of its own. That is
    # not a contradiction of the panel, so it may not weaken or strengthen it.
    ok("D: a missing series_source_kind key also preserves the panel",
       F("measured", {"entity_class": "ExperimentSeries"}) == "measured")
    ok("D: a None entity preserves the panel", F("measured", None) == "measured")

    print("=== E. unknown + no panel provenance ===")
    ok("E: unknown with no panel evidence stays None",
       F(None, ent("unknown")) is None, F(None, ent("unknown")))
    ok("E: an unrecognised series kind never invents provenance",
       F(None, ent("something_new")) is None, F(None, ent("something_new")))
    # positive series evidence is still usable when the panel knows nothing
    ok("E: positive series evidence resolves a panel that had none",
       F(None, ent("calculated")) == "simulated" and F(None, ent("measured")) == "measured")

    print("=== F. explicit series evidence beats the panel, both directions ===")
    ok("F: measured panel + calculated series -> simulated",
       F("measured", ent("calculated")) == "simulated")
    ok("F: simulated panel + measured series -> measured",
       F("simulated", ent("measured")) == "measured")
    ok("F: agreement is a no-op in both directions",
       F("measured", ent("measured")) == "measured"
       and F("simulated", ent("calculated")) == "simulated")

    print("=== G. producer class is never consulted ===")
    # This is the rule that keeps §E honest. A SimulationRun whose series said nothing
    # about itself must NOT be handed "simulated" for free: that would be a producer-aware
    # guess dressed up as provenance. It becomes an unresolved provenance case instead.
    for cls in ("SimulationRun", "ModelSweep", "Fit", "ImportedLiteratureObservation",
                "UnresolvedSourceEntity", "ExperimentSeries"):
        ok("G: %-28s does not change the answer" % cls,
           F("measured", ent("unknown", entity_class=cls)) == "measured"
           and F(None, ent("unknown", entity_class=cls)) is None)
    ok("G: entity_class cannot override positive series evidence either",
       F("measured", ent("measured", entity_class="SimulationRun")) == "measured")

    print("=== H. the coarse vocabulary is not expanded ===")
    vals = {F(b, ent(k)) for b in ("measured", "simulated", None)
            for k in ("measured", "calculated", "fitted", "unknown", None)}
    ok("H: only measured / simulated / None are ever produced",
       vals <= {"measured", "simulated", None}, vals)
    ok("H: 'calculated' and 'fitted' are never emitted as a data_source",
       not ({"calculated", "fitted"} & vals))
    # the finer distinction must stay recoverable from the entity, not from data_source
    ok("H: calculated and fitted project onto the same coarse value, "
       "distinguished only on the entity",
       F("measured", ent("calculated")) == F("measured", ent("fitted")) == "simulated")

    print("=== I. the projection is total and side-effect free ===")
    e = ent("calculated")
    snapshot = dict(e)
    F("measured", e)
    ok("I: the entity is not mutated", e == snapshot)
    ok("I: the base value is returned unchanged for every non-positive kind",
       all(F(b, ent(k)) == b for b in ("measured", "simulated", None, "both")
           for k in ("unknown", None, "", "weird")))

    print("=== J. persisted corpus: series evidence is honoured ===")
    ents, rows, bad_kind, changed = {}, [], [], []
    for pid in PAPERS:
        for e in json.loads((W.parent.parent / "papers" / pid / "resolved"
                             / "entities.json").read_text()):
            ents[e["entity_id"]] = e
        for r in sem(pid, "result_series"):
            e = ents.get(r.get("resolved_entity_id")) or {}
            k = e.get("series_source_kind")
            rows.append((pid, r, e, k))
            if k in PS._SERIES_KIND_SOURCE and r.get("data_source") != PS._SERIES_KIND_SOURCE[k]:
                bad_kind.append((r["result_series_id"], k, r.get("data_source")))
            if k in PS._SERIES_KIND_SOURCE:
                changed.append((r["result_series_id"], k, r.get("data_source")))
    ok("J: every persisted ResultSeries with positive series evidence matches its "
       "projection", not bad_kind, bad_kind[:4])
    ok("J: the corpus actually exercises positive series evidence", len(changed) > 0,
       len(changed))
    ok("J: no persisted ResultSeries carries a value outside the vocabulary",
       all(r.get("data_source") in ("measured", "simulated", None) for _, r, _, _ in rows))

    print("=== K. SimulationRun aggregates, it does not repair ===")
    ds_of = {}
    for pid in PAPERS:
        for r in sem(pid, "result_series"):
            ds_of[r["result_series_id"]] = r.get("data_source")
    drift = []
    for pid in PAPERS:
        for s in sem(pid, "simulation_runs"):
            want = sorted({ds_of.get(i) for i in s["result_series_ids"] if ds_of.get(i)})
            if sorted(s.get("data_source") or []) != want:
                drift.append((s["simulation_run_id"], s.get("data_source"), want))
    ok("K: every SimulationRun.data_source is exactly the set of its ResultSeries values",
       not drift, drift[:4])

    print("=== L. current-pilot consistency audit (corpus invariant, NOT a resolver "
          "rule) ===")
    # A model producer labelled `measured` means the panel claimed measurement and the
    # series never contradicted it. Today that set is empty. If a future paper lands in
    # it, the right response is to review that paper -- NOT to make the resolver guess
    # `simulated` from the producer class, which §G forbids.
    contra = []
    for pid in PAPERS:
        sims = {i for s in sem(pid, "simulation_runs") for i in s["result_series_ids"]}
        for r in sem(pid, "result_series"):
            if r["result_series_id"] in sims and r.get("data_source") == "measured":
                contra.append((pid, r["result_series_id"]))
    ok("L: no model-produced ResultSeries is labelled measured in the current corpus",
       not contra, contra[:4])
    simmeas = [s["simulation_run_id"] for pid in PAPERS for s in sem(pid, "simulation_runs")
               if "measured" in (s.get("data_source") or [])]
    ok("L: no SimulationRun carries 'measured' in the current corpus", not simmeas,
       simmeas[:4])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
