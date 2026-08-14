#!/usr/bin/env python3
"""Condition cases, physical realizations and observing acts must stay distinct.

Three claims are easy to make and wrong. That a condition case is a physical experiment --
it can hold six specimens. That one sample's deposition run is the case's run -- the other
five realizations may have none. That a sweep curve belongs to a case -- it belongs to
every case it traverses, and returning the first is a smaller, different answer.

The grouping rule is the mirror image: Measurement records become one act only where the
records themselves say so. Same figure, same conditions and same quantity group nothing,
because none of them is evidence about an observing act.

Run:  python3 tests/test_entity_identity_repair.py
"""
import io
import json
import sys
import tokenize
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.query import entity_identity as EI                       # noqa: E402

R = W / "_diagnostics" / "entity_identity_repair"
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def M(mid, same=None, **kw):
    d = {"measurement_id": mid}
    if same:
        d["represents_same_measurement_as"] = same
    d.update(kw)
    return d


def main():
    print("=== A. MeasurementAct groups only on explicit evidence ===")
    acts, of = EI.measurement_acts([M("A"), M("B", same="A"), M("C", same="B")])
    ok("A: a same-as chain closes transitively", len(acts) == 1, acts)
    ok("A: all members are retained",
       sorted(list(acts.values())[0]) == ["A", "B", "C"], acts)
    ok("A: every member maps to the act", {of["A"], of["B"], of["C"]} == set(acts))
    # order independence
    a2, _ = EI.measurement_acts([M("C", same="B"), M("A"), M("B", same="A")])
    ok("A: grouping is order-independent", a2 == acts, (a2, acts))
    ok("A: the act id is the smallest member", list(acts) == ["ACT::A"], list(acts))

    print("=== B. what must NOT group ===")
    same_fig = [M("X", figure="3", panel="a"), M("Y", figure="3", panel="a")]
    ok("B: same figure/panel alone groups nothing",
       len(EI.measurement_acts(same_fig)[0]) == 2)
    same_cond = [M("X", measured_quantity="film_thickness"),
                 M("Y", measured_quantity="film_thickness")]
    ok("B: same measurand alone groups nothing",
       len(EI.measurement_acts(same_cond)[0]) == 2)
    diff_spec = [M("X", performed_on="S1"), M("Y", performed_on="S2")]
    ok("B: different specimens group nothing",
       len(EI.measurement_acts(diff_spec)[0]) == 2)
    ok("B: an isolated record is its own act",
       len(EI.measurement_acts([M("Z")])[0]) == 1)

    print("=== C. existing Measurement ids stay addressable ===")
    ms = [M("A"), M("B", same="A")]
    acts, of = EI.measurement_acts(ms)
    ok("C: every input id appears in the mapping", set(of) == {"A", "B"})
    ok("C: an act is a grouping, not a replacement",
       all(m in sum(acts.values(), []) for m in ("A", "B")))

    print("=== D. a ResultSeries keeps its full case membership ===")
    pc = EI.producer_case_index(
        [M("M1", measures_case=["C1", "C2", "C3"]), M("M2", measures_case=["C1"]),
         M("M3", measures_case=[])], [])
    s_multi = {"result_series_id": "R1", "produced_by": "M1"}
    s_one = {"result_series_id": "R2", "produced_by": "M2"}
    s_none = {"result_series_id": "R3", "produced_by": "M3"}
    ok("D: a sweep series returns every case",
       EI.cases_for_result_series(s_multi, pc) == ["C1", "C2", "C3"])
    ok("D: the set is sorted and de-duplicated",
       EI.cases_for_result_series(s_multi, pc) ==
       sorted(set(EI.cases_for_result_series(s_multi, pc))))
    ok("D: a single-case series returns one",
       EI.cases_for_result_series(s_one, pc) == ["C1"])
    ok("D: a producer with no case returns none",
       EI.cases_for_result_series(s_none, pc) == [])

    print("=== E. no helper silently picks a first case ===")
    ok("E: single_case refuses to choose for a multi-case series",
       EI.single_case_for_series(s_multi, pc) == (None, EI.MULTI_CASE))
    ok("E: it answers only when there is exactly one",
       EI.single_case_for_series(s_one, pc) == ("C1", "SINGLE_CASE"))
    ok("E: and reports absence distinctly from multiplicity",
       EI.single_case_for_series(s_none, pc) == (None, EI.NO_CASE))
    # EXECUTABLE code only: the docstring deliberately quotes the defect it replaces,
    # which is documentation rather than a first-element pick.
    src = (W / "pipeline" / "query" / "entity_identity.py").read_text()
    code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                   for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("E: no case_ids first-element pick in executable code",
       "case_ids[0]" not in code)
    # the one indexing that exists is guarded: cs[0] is returned ONLY when len(cs) == 1,
    # which is reading the sole element rather than choosing among several
    body = src.split("def single_case_for_series")[1]
    ok("E: the only [0] is guarded by a length-one check",
       "len(cs) == 1" in body and body.index("len(cs) == 1") < body.index("cs[0]"), body[:0])
    ok("E: the docstring may still name the defect", "case_ids[0]" in src)

    print("=== F. run links are sample-scoped ===")
    samples = {"S1": {"sample_id": "S1", "produced_by_run": "RUN1"},
               "S2": {"sample_id": "S2", "produced_by_run": None},
               "S3": {"sample_id": "S3", "produced_by_run": None}}
    case = {"case_id": "C1", "sample_ids": ["S1", "S2", "S3"]}
    links = EI.case_run_links(case, samples)
    ok("F: only the sample that carries a run produces a link", len(links) == 1, links)
    ok("F: the link names the sample it came from", links[0]["via_sample"] == "S1")
    ok("F: and is typed as observed-among-realizations",
       links[0]["semantics"] == EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS)
    # the mandatory regression: no sibling inherits it
    real = EI.realizations(case, samples, None)
    ok("F: a sibling sample does not inherit the run",
       [s["run_status"] for s in real["samples"] if s["sample_id"] == "S2"]
       == ["RUN_UNRESOLVED"], real["samples"])
    ok("F: the case reports runs observed, not a run identity",
       real["run_link_semantics"] == EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS)

    print("=== G. a case may hold several realizations, or none ===")
    ok("G: several samples are all reported", real["n_samples_resolved"] == 3)
    empty = EI.realizations({"case_id": "C9", "sample_ids": []}, samples, None)
    ok("G: a case with no sample is unresolved, not broken",
       empty["physical_identity_status"] == "UNRESOLVED", empty)
    ok("G: and is not given a fabricated sample", empty["samples"] == [])

    print("=== H. case conditions are context, never sample evidence ===")
    conds = EI.inherited_conditions({"case_defining_conditions": [
        {"quantity": "deposition_temperature", "value": 300}]})
    ok("H: an inherited condition is scoped to the case",
       conds[0]["condition_scope"] == EI.CASE_CONTEXT, conds)
    ok("H: and says it was not measured on a realization",
       "not measured" in conds[0]["provenance_note"])
    ok("H: the four scopes are distinct constants",
       len({EI.DIRECT_SAMPLE_EVIDENCE, EI.CASE_CONTEXT, EI.RUN_CONTEXT,
            EI.MEASUREMENT_SETTING}) == 4)

    print("=== I. the repaired corpus artifacts agree with the model ===")
    for n in ("entity_relation_graph.json", "measurement_act_inventory.json",
              "sample_identity_inventory.json", "deposition_run_linkage_inventory.json",
              "multi_case_result_series_inventory.json", "workbench_semantic_contract.json",
              "audit_conflict_dispositions.json"):
        ok("I: %s exists" % n, (R / n).exists(), n)
    if not (R / "measurement_act_inventory.json").exists():
        print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
        return 1
    inv = json.loads((R / "measurement_act_inventory.json").read_text())
    ok("I: acts never exceed measurement records",
       inv["measurement_acts"] <= inv["measurement_records"],
       (inv["measurement_acts"], inv["measurement_records"]))
    ok("I: the corpus really contains multi-member acts",
       inv["multi_member_acts"] > 0, inv["multi_member_acts"])
    ok("I: every act cites its grouping evidence",
       all(a["evidence"] for a in inv["acts"].values()))
    ok("I: multi-member acts cite the same-as relation",
       all(any("represents_same_measurement_as" in e for e in a["evidence"])
           for a in inv["acts"].values() if a["n_members"] > 1))

    sam = json.loads((R / "sample_identity_inventory.json").read_text())
    ok("I: no Sample was merged without a specimen id",
       sam["aliases_merged"] == 0 and sam["samples_with_traceable_specimen_id"] == 0, sam)
    ok("I: the gap is classified as extraction debt",
       sam["classification"] == "PHYSICAL_IDENTITY_NOT_EXTRACTED")

    run = json.loads((R / "deposition_run_linkage_inventory.json").read_text())
    ok("I: no whole-case run propagation remains",
       run["overpropagated_links_after"] == 0, run["overpropagated_links_after"])
    ok("I: every run lists its explicit sample members",
       all("explicit_sample_members" in r for r in run["runs"].values()))

    mc = json.loads((R / "multi_case_result_series_inventory.json").read_text())
    ok("I: multi-case series are enumerated", mc["n_multi_case_series"] > 0,
       mc["n_multi_case_series"])
    ok("I: none is collapsed to one case",
       all(s["n_cases"] >= 2 for s in mc["series"]))
    ok("I: point-level mapping is reported unresolved, not invented",
       all(s["point_to_case_mapping"] == "UNRESOLVED_NOT_PERSISTED" for s in mc["series"]))

    disp = json.loads((R / "audit_conflict_dispositions.json").read_text())
    prev = json.loads((W / "_diagnostics" / "entity_identity"
                       / "entity_identity_conflicts.json").read_text())
    ok("I: every previous conflict is dispositioned",
       disp["total"] == prev["count"], (disp["total"], prev["count"]))
    ok("I: every disposition is from the controlled set",
       set(disp["counts"]) <= {"RESOLVED", "EXPECTED_GRAPH_CARDINALITY",
                               "STILL_UNRESOLVED", "DEFERRED_EXTRACTION_GAP"},
       disp["counts"])
    ok("I: every disposition carries a reason",
       all(d.get("disposition_reason") for d in disp["dispositions"]))

    con = json.loads((R / "workbench_semantic_contract.json").read_text())
    ok("I: the contract forbids calling a case an Experiment",
       "Experiment" in con["ExperimentalCase"]["must_not_be_called"])
    ok("I: and requires 0..N never-first-picked case ids",
       "never first-picked" in con["ResultSeries"]["case_ids"])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
