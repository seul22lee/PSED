#!/usr/bin/env python3
"""Can these two results be compared -- and what would it cost to say yes?

`t/t_entrance`, `t/t_max` and `t/t_planar` all canonicalise to `normalized_thickness`
with unit 1, and they are three different physical statements. Overlaying them because
their quantity ids match would be a quiet, confident error, so the comparison identity
here is (quantity, comparison group, normalization definition) and a normalization nobody
recorded is `ambiguous` -- which is a different answer from "no" and a very different
answer from "yes".

The other thing these tests pin is that a missing transform parameter stays missing. A
feature height nobody extracted must not be filled in from a typical value: the transform
would run, the picture would look better, and the result would be untraceable.

Run:  python3 tests/test_result_comparability.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.query import result_comparability as RC                  # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def S(pid, xq, xu, yq, yu, xl=None, yl=None, pts=None, sid="S", ds="measured"):
    return {"paper_id": pid, "result_series_id": sid, "data_source": ds,
            "x_quantity": xq, "x_unit": xu, "x_label": xl,
            "y_quantity": yq, "y_unit": yu, "y_label": yl,
            "points": pts or [[0, 1.0], [1, 2.0], [2, 3.0]]}


def main():
    print("=== A. representation identity is more than the quantity id ===")
    r = RC.axis_representation("normalized_thickness", "1", "t / t_max")
    ok("A: a stated basis is read off the printed label",
       r["normalization_definition"] == "t_over_t_max", r)
    ok("A: and marked as inferred with evidence",
       r["normalization_status"] == RC.NORMALIZATION_INFERRED and r["normalization_evidence"])
    r2 = RC.axis_representation("normalized_thickness", "1", "Normalized thickness (-)")
    ok("A: an unstated basis is UNKNOWN, not assumed",
       r2["normalization_definition"] is None
       and r2["normalization_status"] == RC.NORMALIZATION_UNKNOWN, r2)
    ok("A: a non-normalized axis carries no normalization",
       not RC.axis_representation("film_thickness", "nm", "Film thickness")["normalized"])
    ok("A: comparison groups resolve from the ontology",
       RC.group_of("film_thickness") == "film_thickness"
       and RC.group_of("spatial_coordinate") == "spatial_position")

    print("=== B. normalization identity is a hard contract ===")
    ent = RC.axis_representation("normalized_thickness", "1", "t / t_entrance")
    mx = RC.axis_representation("normalized_thickness", "1", "t / t_max")
    d = RC.compare_axis(ent, mx)
    ok("B: t/t_entrance and t/t_max are NOT directly comparable",
       d["status"] == RC.RELATED_NOT_COMPARABLE, d["status"])
    ok("B: and the reason names both bases",
       "t_over_t_entrance" in d["reason"] and "t_over_t_max" in d["reason"], d["reason"])
    ok("B: the same basis on both sides IS direct",
       RC.compare_axis(mx, RC.axis_representation("normalized_thickness", "1",
                                                  "t/t_max"))["status"] == RC.DIRECT)
    unk = RC.axis_representation("normalized_thickness", "1", "Normalized thickness")
    ok("B: a known basis against an unknown one is ambiguous, not equal",
       RC.compare_axis(ent, unk)["status"] == RC.AMBIGUOUS,
       RC.compare_axis(ent, unk)["status"])
    ok("B: two unknown bases are also ambiguous",
       RC.compare_axis(unk, unk)["status"] == RC.AMBIGUOUS)

    print("=== C. same quantity: direct, convertible, or not ===")
    A = RC.axis_representation("film_thickness", "nm", "thickness")
    ok("C: same quantity and unit is DIRECT",
       RC.compare_axis(A, A)["status"] == RC.DIRECT)
    ang = RC.axis_representation("film_thickness", "angstrom", "thickness")
    ok("C: nm against angstrom is unit-convertible",
       RC.compare_axis(A, ang)["status"] == RC.UNIT_CONVERTIBLE,
       RC.compare_axis(A, ang)["status"])
    bad = RC.axis_representation("film_thickness", "s", "thickness")
    ok("C: incompatible dimensions are not comparable",
       RC.compare_axis(A, bad)["status"] == RC.NOT_COMPARABLE)
    # different quantity that happens to share a unit is not thereby comparable
    fh = RC.axis_representation("feature_height", "nm", "H")
    ok("C: a different quantity in the same unit is not comparable",
       RC.compare_axis(A, fh)["status"] == RC.NOT_COMPARABLE,
       RC.compare_axis(A, fh)["status"])

    print("=== D. semantic vs operational transformability ===")
    x = RC.axis_representation("spatial_coordinate", "um", "x")
    xn = RC.axis_representation("dimensionless_distance", "1", "x/H")
    d = RC.compare_axis(x, xn)
    ok("D: the ontology declares x <-> x/H", d["semantically_transformable"], d)
    ok("D: without H it is missing_context, not a guess",
       d["status"] == RC.MISSING_CONTEXT and not d["operationally_transformable_now"], d)
    ok("D: and it names exactly what is missing",
       d["missing_context"] == ["feature_height"], d["missing_context"])
    case = {"case_id": "C1", "case_defining_conditions": [
        {"quantity": "feature_height", "value": 50, "unit": "um",
         "evidence": "stated in the methods", "provenance_type": "methods_default"}]}
    d2 = RC.compare_axis(x, xn, a_case=case)
    ok("D: with H resolved it becomes operationally transformable",
       d2["status"] == RC.TRANSFORMABLE_WITH_CONTEXT
       and d2["operationally_transformable_now"], d2["status"])
    ok("D: the resolved parameter carries its provenance",
       d2["available_context"][0]["source_object"].startswith("ExperimentalCase")
       and d2["available_context"][0]["source_evidence"], d2["available_context"])

    print("=== E. context is never invented ===")
    miss = RC.resolve_context("feature_height")
    ok("E: an unresolvable parameter reports not-found",
       miss["found"] is False and miss["value"] is None, miss)
    ok("E: and says so rather than offering a default",
       "no evidence" in miss["source_evidence"], miss["source_evidence"])
    # a self-referential parameter IS resolvable, because it is in the data itself
    ser = S("p", "spatial_coordinate", "um", "film_thickness", "nm",
            pts=[[0, 10.0], [1, 25.0], [2, 5.0]])
    got = RC.resolve_context("t_max", series=ser)
    ok("E: t_max comes from the profile's own points", got["found"] and got["value"] == 25.0,
       got)
    ok("E: and is labelled self-referential",
       got["confidence"] == "self_referential" and "own" in got["source_evidence"], got)

    print("=== F. whole-profile verdicts combine both axes ===")
    a = S("A", "spatial_coordinate", "um", "film_thickness", "nm", sid="A1")
    b = S("B", "spatial_coordinate", "um", "film_thickness", "nm", sid="B1")
    r = RC.compare_result_series(a, b)
    ok("F: both axes direct gives a direct profile",
       r["profile_status"] == RC.DIRECT_PROFILE, r["profile_status"])
    ok("F: cross-paper is reported", r["cross_paper"] is True)
    ok("F: and the verdict is about representation, not equivalence",
       "does not assert" in r["provenance_note"])
    b2 = S("B", "spatial_coordinate", "mm", "film_thickness", "nm", sid="B2")
    r2 = RC.compare_result_series(a, b2)
    ok("F: a unit difference still yields a transformable profile",
       r2["profile_status"] == RC.TRANSFORMABLE_PROFILE
       and r2["x"]["status"] == RC.UNIT_CONVERTIBLE, r2["profile_status"])
    b3 = S("B", "dimensionless_distance", "1", "film_thickness", "nm", xl="x/H",
           sid="B3")
    ok("F: an axis needing an unavailable parameter blocks the profile",
       RC.compare_result_series(a, b3)["profile_status"] == RC.MISSING_CONTEXT)
    b4 = S("B", "spatial_coordinate", "um", "normalized_thickness", "1",
           yl="Normalized thickness")
    n4 = S("A", "spatial_coordinate", "um", "normalized_thickness", "1",
           yl="Normalized thickness")
    ok("F: two unknown-basis normalized profiles are shape-only",
       RC.compare_result_series(n4, b4)["profile_status"] == RC.SHAPE_ONLY_PROFILE,
       RC.compare_result_series(n4, b4)["profile_status"])

    print("=== G. provenance difference alone is not incomparability ===")
    sim = S("B", "spatial_coordinate", "um", "film_thickness", "nm", ds="simulated",
            sid="B4")
    r = RC.compare_result_series(a, sim)
    ok("G: experiment against simulation still compares",
       r["profile_status"] == RC.DIRECT_PROFILE, r["profile_status"])
    ok("G: and provenance is reported, not used as a verdict",
       r["a"]["data_source"] == "measured" and r["b"]["data_source"] == "simulated")

    print("=== H. transformation preserves the source and its lineage ===")
    src = S("A", "spatial_coordinate", "mm", "film_thickness", "nm",
            pts=[[0, 10.0], [1, 20.0], [2, 5.0]])
    before = json.dumps(src, sort_keys=True)
    t = RC.transform_series(src, target_unit="um")
    ok("H: the source series is untouched", json.dumps(src, sort_keys=True) == before)
    ok("H: mm became um", [p[0] for p in t["points"]] == [0.0, 1000.0, 2000.0],
       t["points"])
    ok("H: y is unchanged by an x-only transform",
       [p[1] for p in t["points"]] == [10.0, 20.0, 5.0])
    ok("H: the step is recorded with its rule",
       t["transformations"][0]["type"] == "unit_conversion"
       and t["transformations"][0]["rule_id"] == "length_unit_conversion", t)
    ok("H: lineage names the source series and its points",
       t["source_series_id"] == "S" and t["source_points"] == src["points"])
    ctx = RC.resolve_context("t_max", series=src)
    n = RC.transform_series(src, target_unit="um", normalization="t_over_t_max",
                            context=ctx)
    ok("H: normalization divides by the declared denominator",
       [round(p[1], 4) for p in n["points"]] == [0.5, 1.0, 0.25], n["points"])
    ok("H: the target quantity changes to the normalized one",
       n["target_y_quantity"] == "normalized_thickness" and n["target_y_unit"] == "1")
    ok("H: the normalization definition is named",
       n["normalization_definition"] == "t_over_t_max")
    ok("H: and its parameter carries provenance",
       n["transformations"][-1]["parameter_provenance"]["source_object"], n)
    ok("H: a transform with no steps is already_canonical",
       RC.transform_series(src)["status"] == "already_canonical")

    print("=== I. search returns reasons, not just hits ===")
    universe = [a, b, b2, b3, sim]
    hits = RC.find_comparable_series(a, universe)
    ok("I: comparable series are found", hits, len(hits))
    ok("I: every hit carries a profile status and both axis reasons",
       all(h["profile_status"] and h["x"]["reason"] and h["y"]["reason"] for h in hits))
    ok("I: the target is never compared with itself",
       all(h["b"]["series"] != h["a"]["series"] or h["a"]["paper_id"] != h["b"]["paper_id"]
           for h in hits))
    cross = RC.find_comparable_series(a, universe, cross_paper_only=True)
    ok("I: cross-paper filtering works",
       all(h["a"]["paper_id"] != h["b"]["paper_id"] for h in cross), len(cross))
    only = RC.find_comparable_series(a, universe, statuses={RC.DIRECT_PROFILE})
    ok("I: status filtering works",
       all(h["profile_status"] == RC.DIRECT_PROFILE for h in only), len(only))
    ok("I: an unrelated quantity is indexed out, not compared",
       not RC.find_comparable_series(
           a, [S("Z", "cycle_number", "cycle", "atomic_concentration", "%")]))

    print("=== J. the published artifacts are consistent ===")
    d = W / "_diagnostics" / "comparability"
    for n in ("result_series_inventory.json", "real_pair_inventory.json",
              "runtime_comparability_results.json", "cross_paper_overlay_data.json"):
        ok("J: %s exists" % n, (d / n).exists())
    ovp = d / "cross_paper_overlay_data.json"
    if ovp.exists():
        ov = json.loads(ovp.read_text())
        ok("J: the overlay is cross-paper",
           len({s["source"]["paper_id"] for s in ov["series"]}) == 2,
           [s["source"]["paper_id"] for s in ov["series"]])
        ok("J: every overlay series keeps its source points",
           all(s["transformed"]["source_points"] for s in ov["series"]))
        ok("J: every normalization parameter has a source object",
           all(s["normalization_context"]["source_object"] for s in ov["series"]))
        ok("J: the overlay states it is not an equivalence claim",
           "does not assert" in ov["caveat"])
        # the silent-rescale trap: canonical values must be paired with canonical units
        for s in ov["series"]:
            src = s["source"]
            if str(src.get("raw_x_unit")) == "mm":
                ok("J: a mm-printed profile is carried in canonical um",
                   max(p[0] for p in s["transformed"]["points"]) > 1000,
                   max(p[0] for p in s["transformed"]["points"]))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
