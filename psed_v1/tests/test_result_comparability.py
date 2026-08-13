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
    # shape-only used to be granted automatically here; it is now opt-in, because
    # "we cannot establish the scale" must not silently become a weaker claim the caller
    # never asked for
    ok("F: two unknown-basis normalized profiles are ambiguous by default",
       RC.compare_result_series(n4, b4)["profile_status"] == RC.AMBIGUOUS,
       RC.compare_result_series(n4, b4)["profile_status"])
    ok("F: and shape-only only when explicitly requested",
       RC.compare_result_series(n4, b4, allow_shape_only=True)["profile_status"]
       == RC.SHAPE_ONLY_PROFILE)

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

    print("=== K. the canonical record is authoritative, not the printed label ===")
    # the regression this task exists to close: a fully resolved axis whose label says
    # only "Dimensionless distance x̃" must not be downgraded to UNKNOWN
    rep = RC.axis_representation(
        "dimensionless_distance", "1", "Dimensionless distance x\u0303",
        normalization_definition="x_over_feature_height",
        comparison_group="normalized_spatial_position_by_feature_height")
    ok("K: a canonical normalization is used verbatim",
       rep["normalization_definition"] == "x_over_feature_height", rep)
    ok("K: and marked EXPLICIT, not inferred from the label",
       rep["normalization_status"] == RC.NORMALIZATION_EXPLICIT, rep["normalization_status"])
    ok("K: the canonical comparison group wins over the ontology lookup",
       rep["comparison_group"] == "normalized_spatial_position_by_feature_height")
    # label inference survives only where the canonical record said nothing
    bare = RC.axis_representation("normalized_thickness", "1", "t / t_max")
    ok("K: label inference still works as a fallback",
       bare["normalization_definition"] == "t_over_t_max"
       and bare["normalization_status"] == RC.NORMALIZATION_INFERRED, bare)
    ok("K: and a silent label is still UNKNOWN",
       RC.axis_representation("normalized_thickness", "1", "Normalized thickness")
       ["normalization_status"] == RC.NORMALIZATION_UNKNOWN)
    mism = RC.axis_representation("film_thickness", "nm", "t",
                                  comparison_group="spatial_position")
    ok("K: a canonical/ontology group disagreement is surfaced, not overwritten",
       mism.get("canonical_ontology_mismatch"), mism)

    print("=== L. resolved canonical context is reused, never re-derived ===")
    tr = [{"axis": "x", "rule_id": "denormalize_x_by_feature_height",
           "status": "converted", "type": "geometry_based_conversion",
           "context": {"feature_height": {"value": 0.1, "unit": "um",
                                          "status": "resolved", "confidence": 0.9,
                                          "evidence": "100 nm",
                                          "source_location": "series label"}}}]
    got = RC.resolve_context("feature_height", transformations=tr)
    ok("L: the parameter the canonical layer actually used is found",
       got["found"] and got["value"] == 0.1, got)
    ok("L: provenance points at the canonical record, not a weaker copy",
       got["provenance_type"] == "canonical_transform_context"
       and got["source_field"].startswith("transformations"), got)
    ok("L: and it carries the canonical status", got["canonical_status"] == "converted")
    # a context entry the canonical layer could NOT resolve must not be used
    unres = [{"axis": "x", "rule_id": "r", "status": "ambiguous",
              "context": {"feature_height": {"value": 3, "status": "ambiguous"}}}]
    ok("L: an unresolved canonical context is not consumed",
       not RC.resolve_context("feature_height", transformations=unres)["found"])
    # §43: converted upstream may not read as missing downstream
    x = RC.axis_representation("dimensionless_distance", "1", "x/H",
                               normalization_definition="x_over_feature_height",
                               transformations=tr)
    xa = RC.axis_representation("spatial_coordinate", "um", "x")
    d = RC.compare_axis(x, xa)
    ok("L: a converted canonical transform is not reported missing_context",
       d["status"] != RC.MISSING_CONTEXT, d["status"])
    ok("L: and the execution source names the canonical context",
       d.get("execution_source") in ("CANONICAL_CONTEXT", "CANONICAL_PROJECTION"),
       d.get("execution_source"))

    print("=== M. persisted projections are reused ahead of recomputation ===")
    proj = [{"quantity": "spatial_coordinate", "unit": "µm",
             "comparison_group": "spatial_position",
             "from_normalization": "x_over_feature_height",
             "values": [-2.0, 0.0, 4.0]}]
    xp = RC.axis_representation("dimensionless_distance", "1", "x/H",
                                normalization_definition="x_over_feature_height",
                                projections=proj)
    d = RC.compare_axis(xp, xa)
    ok("M: a persisted projection makes the pair transformable",
       d["status"] == RC.TRANSFORMABLE_EXACT, d["status"])
    ok("M: and is marked as reused rather than recomputed",
       d["execution_source"] == "CANONICAL_PROJECTION", d.get("execution_source"))
    ok("M: the common representation is stated explicitly",
       d["common_representation"]["quantity"] == "spatial_coordinate"
       and d["common_representation"]["unit"] == "µm", d.get("common_representation"))

    print("=== N. normalization applicability is validated ===")
    gpc = S("p", "spatial_coordinate", "um", "growth_per_cycle", "nm/cycle",
            pts=[[0, 1.0], [1, 2.0]])
    r = RC.transform_series(gpc, normalization="t_over_t_max",
                            context=RC.resolve_context("t_max", series=gpc))
    ok("N: t/t_max is refused on a growth-per-cycle curve",
       r["status"] == "not_applicable", r["status"])
    ok("N: and says which numerator it expected",
       "film_thickness" in r["reason"], r["reason"])
    th = S("p", "spatial_coordinate", "um", "film_thickness", "nm",
           pts=[[0, 10.0], [1, 20.0]])
    ok("N: and accepted on a thickness curve",
       RC.transform_series(th, normalization="t_over_t_max",
                           context=RC.resolve_context("t_max", series=th))["status"]
       == "converted")
    ok("N: a normalization with no denominator is missing_context, not a division by None",
       RC.transform_series(th, normalization="t_over_t_max",
                           context={"found": False})["status"] == "missing_context")

    print("=== O. a partially resolved series stays in the universe ===")
    # canonical.y is null because canonicalization could not pin the BASIS, not because
    # the science is absent -- the measurand is known and the curve must remain comparable
    partial = S("P", "spatial_coordinate", "um", "normalized_thickness", "1",
                yl="Normalized thickness (-)", sid="P1")
    known = S("K", "spatial_coordinate", "um", "normalized_thickness", "1",
              yl="t / t_max", sid="K1")
    known["y_normalization"] = "t_over_t_max"
    ok("O: a known basis against an unknown one is ambiguous, not direct",
       RC.compare_result_series(known, partial)["profile_status"] == RC.AMBIGUOUS,
       RC.compare_result_series(known, partial)["profile_status"])
    ok("O: and never DIRECT",
       RC.compare_result_series(known, partial)["profile_status"] != RC.DIRECT_PROFILE)
    ok("O: two unknown bases are ambiguous by default, not shape-only",
       RC.compare_result_series(partial, dict(partial, paper_id="Q", result_series_id="Q1"))
       ["profile_status"] == RC.AMBIGUOUS)
    # the partial series must actually appear in a search, not vanish
    hits = RC.find_comparable_series(known, [partial])
    ok("O: the partial series is found, not absent", len(hits) == 1, len(hits))
    ok("O: with an explicit ambiguity verdict",
       hits[0]["profile_status"] == RC.AMBIGUOUS, hits[0]["profile_status"])
    # unknown REPRESENTATION is not unknown QUANTITY
    rep = RC.axis_representation("normalized_thickness", "1", "Normalized thickness")
    ok("O: the measurand is still known", rep["quantity"] == "normalized_thickness")
    ok("O: only the basis is unknown",
       rep["normalization_status"] == RC.NORMALIZATION_UNKNOWN
       and rep["normalization_definition"] is None, rep)

    print("=== P. shape-only is opt-in and deterministic ===")
    r = RC.compare_result_series(partial,
                                 dict(partial, paper_id="Q", result_series_id="Q1"),
                                 allow_shape_only=True)
    ok("P: requested shape-only on two normalized profiles is granted",
       r["profile_status"] == RC.SHAPE_ONLY_PROFILE, r["profile_status"])
    ok("P: and the request is recorded", r["shape_only_requested"] is True)
    ok("P: not requested means ambiguous",
       RC.compare_result_series(partial,
                                dict(partial, paper_id="Q", result_series_id="Q1"))
       ["profile_status"] == RC.AMBIGUOUS)
    # eligibility is gated on the measurand, not merely on ambiguity existing
    other = S("Q", "spatial_coordinate", "um", "surface_coverage", "1",
              yl="Coverage", sid="Q2")
    ok("P: a different measurand is not shape-only eligible",
       RC.compare_result_series(partial, other, allow_shape_only=True)["profile_status"]
       != RC.SHAPE_ONLY_PROFILE)
    # an unresolved x axis blocks it too: shapes plotted against incomparable abscissae
    # are not comparable shapes
    badx = S("Q", "dimensionless_distance", "1", "normalized_thickness", "1",
             xl="x/H", yl="Normalized thickness", sid="Q3")
    ok("P: an unresolved x axis blocks shape-only",
       RC.compare_result_series(partial, badx, allow_shape_only=True)["profile_status"]
       != RC.SHAPE_ONLY_PROFILE)

    print("=== Q. ambiguity and missing context stay distinct ===")
    xh = S("A", "dimensionless_distance", "1", "film_thickness", "nm", xl="x/H", sid="A9")
    xa = S("B", "spatial_coordinate", "um", "film_thickness", "nm", sid="B9")
    ok("Q: a known transform with no parameter is missing_context",
       RC.compare_result_series(xh, xa)["profile_status"] == RC.MISSING_CONTEXT)
    ok("Q: an unknown representation basis is ambiguous, not missing_context",
       RC.compare_result_series(known, partial)["profile_status"] == RC.AMBIGUOUS)
    ok("Q: the two are different statuses", RC.MISSING_CONTEXT != RC.AMBIGUOUS)

    print("=== R. the false-ambiguity fix from a7ae72b still holds ===")
    # a canonical normalization must survive a generic printed label
    both = S("A", "spatial_coordinate", "um", "normalized_thickness", "1",
             yl="Normalized thickness", sid="A8")
    both["y_normalization"] = "t_over_t_max"
    other2 = dict(both, paper_id="B", result_series_id="B8")
    ok("R: two canonically t_over_t_max curves are direct despite a vague label",
       RC.compare_result_series(both, other2)["profile_status"] == RC.DIRECT_PROFILE,
       RC.compare_result_series(both, other2)["profile_status"])

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
