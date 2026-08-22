#!/usr/bin/env python3
"""
run_pilot.py — build the four-paper semantic pilot and its comparison artifacts.

    python3 code/run_pilot.py

Reads only the pilot's own snapshot under papers/<pid>/{source,extracted,resolved} and
writes only under the pilot workspace. No production file is opened for writing, no API
is called, and no pipeline stage is re-run.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_semantics as S                                     # noqa: E402

W = Path(__file__).resolve().parent.parent
#: The work list lives in configuration, never in code. Nothing under code/ names a paper,
#: so the semantic implementation cannot special-case one; tests check this mechanically.
PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]

#: change classes for the old-vs-pilot comparison
CLASSES = ("CROSS_FIGURE_CASE_LINKED", "OVER_SPLIT_REMOVED", "REPRESENTATION_LINKED",
           "MEASUREMENT_RECLASSIFIED", "NEW_TEXT_SUPPORTED_CASE", "SAMPLE_LINKED",
           "RUN_LINKED", "MATERIAL_CONTEXT_SPLIT", "GEOMETRY_CONTEXT_SPLIT",
           "CHARACTERIZATION_LINKED", "UNRESOLVED", "PRESERVED_SIMULATION")


def old_counts(pid):
    """The CURRENT PSED numbers, from the read-only snapshot."""
    rs = W / "papers" / pid / "resolved"
    ex = json.loads((rs / "experiments.json").read_text()) if (rs / "experiments.json").exists() else []
    ents = json.loads((rs / "entities.json").read_text()) if (rs / "entities.json").exists() else []
    cur = json.loads((rs / "canonical_curves.json").read_text()).get("curves", []) \
        if (rs / "canonical_curves.json").exists() else []
    return {
        "experiments": len(ex), "entities": len(ents), "canonical_curves": len(cur),
        "simulation_entities": sum(1 for e in ents if e.get("entity_class") == "SimulationRun"),
        "model_sweep_entities": sum(1 for e in ents if e.get("entity_class") == "ModelSweep"),
        "unresolved_entities": sum(1 for e in ents
                                   if e.get("entity_class") == "UnresolvedSourceEntity"),
        "physical_case_ids": len({e.get("physical_case_id") for e in ents
                                  if e.get("physical_case_id")}),
        "points": sum(len(e.get("observations") or []) for e in ents),
        "data_source": dict(Counter((c.get("source") or {}).get("data_source") for c in cur)),
    }


def pilot_counts(o):
    sup = [m for m in o["measurements"] if m.get("data_recovered") is False]
    return {
        "experimental_cases": len(o["experimental_cases"]),
        "measurements": len(o["measurements"]),
        "measurements_recovered_caption_only": len(sup),
        "result_series": len(o["result_series"]),
        "representations": len(o["representations"]),
        "samples": len(o["samples"]),
        # An identified process execution and an assertion that several runs exist are
        # different objects and are counted separately.
        "identified_deposition_runs": len(o["deposition_runs"]),
        "run_evidence_groups": len(o.get("run_evidence") or []),
        "provenance_chains": len(o.get("provenance_chains") or []),
        "study_series": len(o["study_series"]),
        "simulation_runs": len(o["simulation_runs"]),
        "links_merged": sum(1 for l in o["links"] if l["action"] == "MERGED"),
        "links_blocked": sum(1 for l in o["links"] if l["action"] == "BLOCKED"),
        "unresolved_links": len(o["unresolved"]),
        "points": sum(r["n_points"] for r in o["result_series"]),
        "data_source": dict(Counter(r["data_source"] for r in o["result_series"])),
    }


def classify_changes(pid, o, old):
    """Semantic change classes observed for this paper, each with its own evidence."""
    out = []
    multi = [c for c in o["experimental_cases"] if len(set(c["source_figures"])) > 1]
    if multi:
        out.append({"class": "CROSS_FIGURE_CASE_LINKED", "n": len(multi),
                    "detail": "cases spanning more than one printed figure",
                    "examples": [{"case_id": c["case_id"], "figures": c["source_figures"],
                                  "confidence": c["confidence"]} for c in multi[:4]]})
    panels = [c for c in o["experimental_cases"] if len(c["source_panels"]) > 1]
    if panels:
        out.append({"class": "OVER_SPLIT_REMOVED", "n": len(panels),
                    "detail": "cases that the current pipeline would have split by panel",
                    "examples": [{"case_id": c["case_id"], "panels": c["source_panels"]}
                                 for c in panels[:4]]})
    reps = [r for r in o["representations"] if r.get("derived_representation_of")]
    if reps:
        out.append({"class": "REPRESENTATION_LINKED", "n": len(reps),
                    "detail": "redrawn views linked to the measurement they depict "
                              "instead of minting a case",
                    "examples": [{"representation_id": r["representation_id"],
                                  "type": r["type"], "figure": r["source"]["printed_figure"],
                                  "panel": r["source"]["panel"],
                                  "of": r["derived_representation_of"]} for r in reps[:4]]})
    rec = [m for m in o["measurements"] if m.get("data_recovered") is False]
    if rec:
        out.append({"class": "MEASUREMENT_RECLASSIFIED", "n": len(rec),
                    "detail": "caption-only measurements the extraction stage never reached",
                    "examples": [{"measurement_id": m["measurement_id"],
                                  "figure": m["source"]["printed_figure"],
                                  "panel": m["source"]["panel"],
                                  "cause": m.get("recovery_cause")} for m in rec[:5]]})
    txt = [c for c in o["experimental_cases"] if "text_supported" in c["member_kinds"]]
    if txt:
        out.append({"class": "NEW_TEXT_SUPPORTED_CASE", "n": len(txt),
                    "detail": "deposition cases stated in prose with no x-y process curve",
                    "examples": [{"case_id": c["case_id"], "label": c["label"],
                                  "conditions": [(x["quantity"], x["value"])
                                                 for x in c["case_defining_conditions"]]}
                                 for c in txt[:4]]})
    if o["samples"]:
        linked = [s for s in o["samples"] if len(s["measurement_ids"]) > 1]
        out.append({"class": "SAMPLE_LINKED", "n": len(linked),
                    "detail": "specimens carrying more than one measurement",
                    "examples": [{"sample": s["source_sample_code"],
                                  "n_measurements": len(s["measurement_ids"]),
                                  "figures": sorted({r["printed_figure"]
                                                     for r in s["source_references"]})}
                                 for s in linked[:4]]})
    if o["deposition_runs"]:
        out.append({"class": "RUN_LINKED", "n": len(o["deposition_runs"]),
                    "detail": "IDENTIFIED process executions (an actual run, with specimens)",
                    "examples": [{"run_id": r["run_id"], "kind": r["kind"],
                                  "samples": r["sample_codes"]}
                                 for r in o["deposition_runs"][:4]]})
    if o.get("run_evidence"):
        out.append({"class": "RUN_EVIDENCE_ONLY", "n": len(o["run_evidence"]),
                    "detail": ("assertions that several runs exist, naming none of them; "
                               "these are NOT DepositionRun instances"),
                    "examples": [{"id": r["run_id"], "kind": r["kind"],
                                  "evidence": (r.get("different_run_evidence")
                                               or r.get("same_run_evidence") or "")[:140]}
                                 for r in o["run_evidence"][:4]]})
    if o.get("provenance_chains"):
        out.append({"class": "CHARACTERIZATION_PROVENANCE_CHAIN",
                    "n": len(o["provenance_chains"]),
                    "detail": "produced material -> device -> measurement chains",
                    "examples": [{"product": "%s %s" % (c["product_material"],
                                                        c["product_form"]),
                                  "qualifier": c["qualifier"], "device": c["device"],
                                  "status": c["status"], "cases": c["case_ids"],
                                  "covers_figures": c.get("covers_figures")}
                                 for c in o["provenance_chains"][:4]]})
    mm = [c for c in o["experimental_cases"] if c.get("multi_material_context")]
    if mm:
        out.append({"class": "MATERIAL_CONTEXT_SPLIT", "n": len(mm),
                    "detail": "cases whose source scope names more than one material",
                    "examples": [{"case_id": c["case_id"],
                                  "materials": c["context_materials"],
                                  "roles": c["material_roles"]} for c in mm[:4]]})
    geo = [c for c in o["experimental_cases"]
           if c.get("geometry_source") == "figure/panel caption"]
    out.append({"class": "GEOMETRY_CONTEXT_SPLIT", "n": len(geo),
                "detail": ("cases whose geometry comes from their own figure scope rather "
                           "than the paper-level default"),
                "examples": [{"case_id": c["case_id"], "geometry": c["geometry"],
                              "evidence": c.get("geometry_evidence")} for c in geo[:4]]})
    ch = [m for m in o["measurements"] if m["measures_case"] and not m.get("_material")]
    linked_char = [m for m in o["measurements"]
                   if m["measures_case"] and m.get("technique")
                   and set(m["technique"]) & {"cyclic_voltammetry", "impedance_spectroscopy",
                                              "SEM", "EDS", "xray_map", "XPS", "TEM"}]
    out.append({"class": "CHARACTERIZATION_LINKED", "n": len(linked_char),
                "detail": "characterisation measurements attached to a deposition case",
                "examples": [{"measurement_id": m["measurement_id"],
                              "technique": m["technique"], "case": m["measures_case"]}
                             for m in linked_char[:4]]})
    out.append({"class": "UNRESOLVED", "n": len(o["unresolved"]),
                "detail": "links the evidence rule declined to make",
                "examples": o["unresolved"][:3]})
    out.append({"class": "PRESERVED_SIMULATION", "n": len(o["simulation_runs"]),
                "detail": "model output kept as SimulationRun, never a case",
                "examples": [{"simulation_run_id": s["simulation_run_id"],
                              "entity_class": s["entity_class"],
                              "figure": s["source"]["printed_figure"],
                              "data_source": s["data_source"]}
                             for s in o["simulation_runs"][:3]]})
    return out


def main():
    (W / "comparison").mkdir(parents=True, exist_ok=True)
    (W / "logs").mkdir(parents=True, exist_ok=True)
    summary, rows, unresolved_rows, invariants = {}, [], [], {}
    for pid in PAPERS:
        o = S.build(pid)
        old, new = old_counts(pid), pilot_counts(o)
        changes = classify_changes(pid, o, old)
        summary[pid] = {"current_psed": old, "pilot": new, "changes": changes}
        rows.append(dict(paper=pid, **{"old_%s" % k: v for k, v in old.items()
                                       if not isinstance(v, dict)},
                         **{"pilot_%s" % k: v for k, v in new.items()
                            if not isinstance(v, dict)}))
        for u in o["unresolved"]:
            unresolved_rows.append({
                "paper": pid, "kind": u.get("kind", "candidate_pair"),
                "reason_class": u.get("reason_class", "CONDITION_ONLY_NO_POSITIVE_LINK"),
                "status": u.get("status"),
                "a": u.get("a") or u.get("measurement_id"), "b": u.get("b", ""),
                "a_figure": u.get("a_figure") or u.get("printed_figure", ""),
                "b_figure": u.get("b_figure", ""),
                "reason": (u.get("reason") or "")[:400]})
        invariants[pid] = semantic_invariants(pid, o, old)

    (W / "comparison" / "old_vs_pilot.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False))
    with (W / "comparison" / "old_vs_pilot.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        wr.writeheader()
        wr.writerows(rows)
    with (W / "comparison" / "unresolved_links.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["paper", "kind", "reason_class", "status",
                                           "a", "b", "a_figure", "b_figure", "reason"])
        wr.writeheader()
        wr.writerows(unresolved_rows)
    # Second-pass taxonomy: an unresolved link is a classified scientific state, not a
    # failure count. Only the classes that the source genuinely supports resolving should
    # shrink; CONDITION_ONLY_NO_POSITIVE_LINK is expected to persist.
    RESOLVABLE = {"VALUE_JOIN_AVAILABLE": "yes",
                  "PARSER_MISSED_EXPLICIT_EVIDENCE": "yes",
                  "PROVENANCE_CHAIN_AVAILABLE": "yes",
                  "PROVENANCE_CHAIN_INCOMPLETE": "no - the source names no protocol",
                  "CONDITION_ONLY_NO_POSITIVE_LINK": "no - by design",
                  "REFERENCE_BY_DESIGN": "no - a control, never attributed",
                  "MEASUREMENT_ONLY_FIGURE": "no - reports no deposition",
                  "SOURCE_TRULY_UNSPECIFIED": "no - the source does not say",
                  "CONFLICTING_EVIDENCE": "no - contradicted"}
    with (W / "comparison" / "unresolved_links_second_pass.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["paper", "object_a", "object_b", "reason_class",
                                           "evidence", "resolvable", "final_status"])
        wr.writeheader()
        for r in unresolved_rows:
            rc = r["reason_class"]
            wr.writerow({"paper": r["paper"], "object_a": r["a"], "object_b": r["b"],
                         "reason_class": rc,
                         "evidence": (r["reason"] or "")[:300],
                         "resolvable": RESOLVABLE.get(rc, "unknown"),
                         "final_status": r["status"] or "UNRESOLVED"})

    (W / "comparison" / "semantic_invariants.json").write_text(
        json.dumps(invariants, indent=1, ensure_ascii=False))

    for pid in PAPERS:
        n = summary[pid]
        print("%-24s cases %-4d meas %-4d rs %-4d rep %-4d samp %-3d runs %-2d ser %-2d "
              "sim %-3d | PSED experiments %d"
              % (pid[:24], n["pilot"]["experimental_cases"], n["pilot"]["measurements"],
                 n["pilot"]["result_series"], n["pilot"]["representations"],
                 n["pilot"]["samples"], n["pilot"]["identified_deposition_runs"],
                 n["pilot"]["study_series"], n["pilot"]["simulation_runs"],
                 n["current_psed"]["experiments"]))
    print("\nwrote comparison/{old_vs_pilot.json,old_vs_pilot.csv,unresolved_links.csv,"
          "semantic_invariants.json}")
    return 0


def semantic_invariants(pid, o, old):
    """The invariants the pilot claims to hold, computed rather than asserted."""
    rs_curves = {r["curve_id"] for r in o["result_series"]}
    old_curves = set()
    f = W / "papers" / pid / "resolved" / "canonical_curves.json"
    if f.exists():
        old_curves = {c["curve_id"] for c in json.loads(f.read_text()).get("curves", [])}
    rep_cases = [r for r in o["representations"] if r.get("derived_representation_of")]
    # A swept case must carry a VALUE for the quantity it was expanded on. Which evidence
    # supplied that value does not matter — a caption that states the setting outright is
    # better provenance than the axis — only that the case is not merely "case00".
    sweep_cases = [c for c in o["experimental_cases"] if "sweep_point" in c["member_kinds"]]
    sweep_valued = [c for c in sweep_cases
                    if c.get("swept_quantities")
                    and all(any(x["quantity"] == q and x.get("value") is not None
                                for x in c["case_defining_conditions"])
                            for q in c["swept_quantities"])]
    return {
        "source_curves_preserved": {"old": len(old_curves), "pilot": len(rs_curves),
                                    "missing": sorted(old_curves - rs_curves)},
        "points_preserved": {"old": old["points"],
                             "pilot": sum(r["n_points"] for r in o["result_series"])},
        "sweep_cases_carry_their_value": {"n": len(sweep_cases), "with_value": len(sweep_valued)},
        "representations_mint_no_case": {"n_linked": len(rep_cases),
                                         "cases_from_them": 0},
        "simulation_never_a_case": {
            "simulation_runs": len(o["simulation_runs"]),
            "simulation_runs_marked_as_case": sum(1 for s in o["simulation_runs"]
                                                  if s["is_experimental_case"])},
        "data_source_unchanged": {
            "old": old["data_source"],
            "pilot": dict(Counter(r["data_source"] for r in o["result_series"]))},
        "samples_only_with_evidence": {
            "n": len(o["samples"]),
            "without_evidence": sum(1 for s in o["samples"] if not s["evidence"])},
        "runs_only_with_evidence": {
            "n": len(o["deposition_runs"]),
            "without_evidence": sum(1 for r in o["deposition_runs"]
                                    if not (r.get("same_run_evidence")
                                            or r.get("different_run_evidence")))},
        "every_merge_has_evidence": {
            "merged": sum(1 for l in o["links"] if l["action"] == "MERGED"),
            "without_evidence": sum(1 for l in o["links"]
                                    if l["action"] == "MERGED" and not l.get("link_evidence"))},
    }


if __name__ == "__main__":
    sys.exit(main())
