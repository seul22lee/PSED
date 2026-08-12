#!/usr/bin/env python3
"""
Pilot invariants and four-paper acceptance anchors.

    python3 tests/test_pilot_semantics.py

The sixteen INVARIANTS are generic: they must hold for any paper. The ACCEPTANCE ANCHORS
name the four pilot papers on purpose — they are regression expectations, and they exist
only in this file. No paper, DOI or figure number appears in any module under code/,
which invariant 16 checks mechanically.
"""
import json
import re
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))

PAPERS = ["10.1038_am.2016.182", "10.1149_2.067203jes",
          "10.1039_c7ta03257a", "10.1039_d0cp03358h"]
AM, JES, CTA, YIM = PAPERS

_fail, _pass = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %-4s %-62s %s" % ("PASS" if cond else "FAIL", name, detail if not cond else ""))


def _strip_prose(src):
    """Source with docstrings and comments removed, so invariant 16 tests code, not prose.

    A comment may legitimately cite the paper a past defect was found on; what must not
    exist is a DOI reaching a decision."""
    src = re.sub(r'"{3}(?:.|\n)*?"{3}', '""', src)
    src = re.sub(r"'{3}(?:.|\n)*?'{3}", "''", src)
    return re.sub(r"(?m)#.*$", "", src)


def sem(pid, name):
    return json.loads((W / "papers" / pid / "semantic" / ("%s.json" % name)).read_text())


def resolved(pid, name):
    f = W / "papers" / pid / "resolved" / ("%s.json" % name)
    return json.loads(f.read_text()) if f.exists() else []


def curves(pid):
    f = W / "papers" / pid / "resolved" / "canonical_curves.json"
    return json.loads(f.read_text()).get("curves", []) if f.exists() else []


# ============================================================ 16 generic invariants
def invariants():
    print("\n=== GENERIC INVARIANTS ===")
    inv = json.loads((W / "comparison" / "semantic_invariants.json").read_text())

    # 1. all original source curve provenance remains traceable
    bad = []
    for pid in PAPERS:
        rs = sem(pid, "result_series")
        have = {r["curve_id"] for r in rs}
        want = {c["curve_id"] for c in curves(pid)}
        missing = want - have
        noptr = [r["result_series_id"] for r in rs if not r["source"].get("json_pointer")]
        if missing or noptr:
            bad.append((pid, sorted(missing)[:3], noptr[:3]))
    ok("1. every source curve is traceable (curve_id + json_pointer)", not bad, bad)

    # 2. all extracted points preserved; increases only from recovered evidence
    bad = [(p, v["points_preserved"]) for p, v in inv.items()
           if v["points_preserved"]["pilot"] < v["points_preserved"]["old"]]
    ok("2. no extracted point was lost", not bad, bad)

    # 3. a swept case carries its own varied value
    bad = [(p, v["sweep_cases_carry_their_value"]) for p, v in inv.items()
           if v["sweep_cases_carry_their_value"]["n"]
           != v["sweep_cases_carry_their_value"]["with_value"]]
    ok("3. every swept case carries its own varied value", not bad, bad)

    # 4. a pure measurement setting never creates a case
    bad = []
    for pid in PAPERS:
        for c in sem(pid, "experimental_cases"):
            ms = [x for x in c["case_defining_conditions"]
                  if x.get("role") == "MEASUREMENT_SETTING"]
            if ms:
                bad.append((pid, c["case_id"], [x["quantity"] for x in ms]))
    ok("4. no MEASUREMENT_SETTING appears among case-defining conditions", not bad, bad[:3])

    # 5. representations create no case
    bad = []
    for pid in PAPERS:
        cases = sem(pid, "experimental_cases")
        for r in sem(pid, "representations"):
            if not r.get("derived_representation_of"):
                continue
            ent = r["source"]["resolved_entity_id"]
            for c in cases:
                if ent and ent in json.dumps(c.get("candidate_ids", [])):
                    bad.append((pid, r["representation_id"]))
    ok("5. a linked representation mints no ExperimentalCase", not bad, bad[:3])

    # 6. several measurements may share one case
    shared = 0
    for pid in PAPERS:
        shared += sum(1 for c in sem(pid, "experimental_cases")
                      if len(c["measurement_ids"]) > 1)
    ok("6. one ExperimentalCase can carry several Measurements", shared > 0,
       "no case has more than one measurement")

    # 7. a missing condition value never implies equality
    bad = []
    for pid in PAPERS:
        for l in sem(pid, "links"):
            if l["action"] != "MERGED":
                continue
            d = l.get("detail") or {}
            if not d.get("agree") and d.get("unknown_on_one_side") \
                    and l.get("strength") != "EXPLICIT":
                bad.append((pid, l["a"], l["b"], l.get("strength")))
    ok("7. no merge rests on unknown-on-one-side alone (non-EXPLICIT)", not bad, bad[:3])

    # 8. contradictory case-defining conditions never merge
    bad = []
    for pid in PAPERS:
        for l in sem(pid, "links"):
            if l["action"] == "MERGED" and (l.get("detail") or {}).get("clash"):
                bad.append((pid, l["a"], l["b"]))
    ok("8. a contradiction always blocks the merge", not bad, bad[:3])

    # 9/10. sample and run identity require evidence
    bad = [(p, v["samples_only_with_evidence"]) for p, v in inv.items()
           if v["samples_only_with_evidence"]["without_evidence"]]
    ok("9. no Sample without source evidence", not bad, bad)
    bad = [(p, v["runs_only_with_evidence"]) for p, v in inv.items()
           if v["runs_only_with_evidence"]["without_evidence"]]
    ok("10. no DepositionRun without source evidence", not bad, bad)

    # 11. figure/panel provenance preserved
    bad = []
    for pid in PAPERS:
        for m in sem(pid, "measurements"):
            if m["source"].get("printed_figure") in (None, ""):
                bad.append((pid, m["measurement_id"]))
    ok("11. every Measurement keeps its figure/panel provenance", not bad, bad[:3])

    # 12. SimulationRun is never an ExperimentalCase
    bad = [(p, v["simulation_never_a_case"]) for p, v in inv.items()
           if v["simulation_never_a_case"]["simulation_runs_marked_as_case"]]
    ok("12. SimulationRun is never an ExperimentalCase", not bad, bad)

    # 13. measured/simulated provenance unchanged
    bad = [(p, v["data_source_unchanged"]) for p, v in inv.items()
           if v["data_source_unchanged"]["old"] != v["data_source_unchanged"]["pilot"]]
    ok("13. measured/simulated provenance is bit-identical to PSED", not bad, bad)

    # 14. imported-literature provenance preserved
    bad = []
    for pid in PAPERS:
        lit = [e for e in resolved(pid, "entities")
               if e.get("entity_class") == "ImportedLiteratureObservation"]
        ids = {m["source"]["resolved_entity_id"] for m in sem(pid, "measurements")}
        for e in lit:
            if e["entity_id"] not in ids:
                bad.append((pid, e["entity_id"]))
    ok("14. imported-literature entities are preserved", not bad, bad[:3])

    # 15. transformation provenance preserved
    bad = []
    for pid in PAPERS:
        by_id = {c["curve_id"]: c for c in curves(pid)}
        for r in sem(pid, "result_series"):
            src = by_id.get(r["curve_id"])
            if src and len(src.get("transformations") or []) != r["n_transformations"]:
                bad.append((pid, r["curve_id"]))
    ok("15. transformation counts match the canonical layer", not bad, bad[:3])

    # 16. no DOI-specific logic in the pilot implementation
    offenders = []
    for f in sorted((W / "code").glob("*.py")):
        src = _strip_prose(f.read_text())
        for m in re.finditer(r"10\.\d{4,5}[_/][^\s\"']+", src):
            offenders.append("%s: %s" % (f.name, m.group(0)))
        for m in re.finditer(r"(?:paper_id|pid|doi)\s*==\s*[\"']", src):
            offenders.append("%s: %s" % (f.name, m.group(0)))
    ok("16. no DOI / paper-id equality test in executable pilot code", not offenders,
       offenders[:4])


# ==================================================== four-paper acceptance anchors
def anchors():
    print("\n=== ACCEPTANCE ANCHORS (regression expectations, not resolver logic) ===")

    # ---- am.2016.182 -------------------------------------------------------
    cases = sem(AM, "experimental_cases")
    meas = {m["measurement_id"]: m for m in sem(AM, "measurements")}
    cross = [c for c in cases if len(set(c["source_panels"])) > 1]
    ok("am: GPC / resistivity / XPS linked into one deposition case", len(cross) >= 2,
       "%d multi-panel cases" % len(cross))
    techs = set()
    for c in cross:
        techs |= {t for m in c["measurement_ids"] for t in (meas[m]["technique"] or [])}
    ok("am: that case carries three different techniques",
       {"growth_per_cycle", "resistivity", "XPS"} <= techs, sorted(techs))
    blocked = [l for l in sem(AM, "links") if l["action"] == "BLOCKED"]
    ok("am: a different precursor blocks the merge", len(blocked) >= 1,
       "%d blocked" % len(blocked))
    ok("am: the blocked merges clash on chemistry",
       all(any(x["quantity"] in ("precursor", "coreactant") for x in l["detail"]["clash"])
           for l in blocked), [l["detail"]["clash"] for l in blocked][:2])
    f4 = [m for m in sem(AM, "measurements") if m["source"]["printed_figure"] == "4"]
    ok("am: printed Figure 4 evidence is present", len(f4) >= 3, "%d panels" % len(f4))
    ok("am: Figure 4 is recovered as caption-only, not invented data",
       all(m.get("data_recovered") is False and not m["result_series_ids"] for m in f4))
    ok("am: Figure 4 mints no deposition case",
       not any("4" in c["source_figures"] for c in cases))

    # ---- 2.067203jes -------------------------------------------------------
    cases = sem(JES, "experimental_cases")
    mm = [c for c in cases if c.get("multi_material_context")]
    ok("jes: multi-material (stack) context is representable", len(mm) >= 1,
       "%d multi-material cases" % len(mm))
    ok("jes: the stack case names both constituents with a role",
       any(set(c["context_materials"]) >= {"SiO2", "Al2O3"}
           and set(c["material_roles"].values()) & {"STACK_COMPONENT", "DEPOSITED"}
           for c in mm), [c["material_roles"] for c in mm[:2]])
    ok("jes: distinct cases were not over-merged into one", len(cases) > 5, len(cases))
    ok("jes: no merge happened without evidence",
       not [l for l in sem(JES, "links") if l["action"] == "MERGED"
            and not l.get("link_evidence")])

    # ---- c7ta03257a --------------------------------------------------------
    cases = sem(CTA, "experimental_cases")
    ok("cta: deposition cases exist with no x-y process curve", len(cases) >= 2, len(cases))
    ok("cta: they are text-supported and distinguished by a per-cycle process quantity",
       all("text_supported" in c["member_kinds"] for c in cases)
       and len({tuple((x["quantity"], x["value"]) for x in c["case_defining_conditions"])
                for c in cases}) == len(cases))
    ms = sem(CTA, "measurements")
    cv = [m for m in ms if set(m["technique"] or []) &
          {"cyclic_voltammetry", "impedance_spectroscopy"}]
    ok("cta: CV / impedance are Measurements", len(cv) >= 2, len(cv))
    ok("cta: CV / impedance are NOT deposition cases",
       not any(m["measures_case"] for m in cv))
    unres = sem(CTA, "unresolved")
    ok("cta: the unestablished case link is recorded as UNRESOLVED",
       any(u.get("kind") == "measurement_without_case" for u in unres), len(unres))
    f8b = [m for m in ms if m["source"]["printed_figure"] == "8"
           and m["source"]["panel"] == "b"]
    ok("cta: printed Fig 8(b) is represented", len(f8b) == 1, len(f8b))
    ok("cta: Fig 8(b) records the missing-crop cause",
       bool(f8b) and f8b[0].get("recovery_cause") == "panel_absent_from_crop",
       f8b[0].get("recovery_cause") if f8b else None)

    # ---- Yim 2020 ----------------------------------------------------------
    cases = sem(YIM, "experimental_cases")
    samples = {s["source_sample_code"]: s for s in sem(YIM, "samples")}
    runs = sem(YIM, "deposition_runs")
    series = {s["author_series_name"]: s for s in sem(YIM, "study_series")}
    reps = sem(YIM, "representations")
    ms = {m["measurement_id"]: m for m in sem(YIM, "measurements")}

    shared = [r for r in runs if r["kind"] == "SHARED_RUN" and len(r["sample_codes"]) > 1]
    ok("yim: Series A — one DepositionRun produces several Samples", len(shared) >= 1,
       [r["sample_codes"] for r in runs])
    ok("yim: that run holds exactly the three Series A specimens",
       bool(shared) and sorted(shared[0]["sample_codes"]) == ["1", "2", "3"],
       shared[0]["sample_codes"] if shared else None)

    ok("yim: Series B varies a MEASUREMENT_SETTING",
       series.get("Series B", {}).get("varied_variable_role") == "MEASUREMENT_SETTING",
       series.get("Series B", {}).get("varied_variable_role"))
    b_cases = [c for c in cases if c["source_figures"] == ["7"]]
    ok("yim: Series B's three curves do not become three deposition cases",
       len(b_cases) == 1, "%d cases from the Series B figure" % len(b_cases))
    ok("yim: that single case carries all three Series B measurements",
       bool(b_cases) and len(b_cases[0]["measurement_ids"]) == 3,
       len(b_cases[0]["measurement_ids"]) if b_cases else None)

    s11 = samples.get("11")
    ok("yim: sample 11 — one Sample carries several Measurements",
       bool(s11) and len(s11["measurement_ids"]) > 1,
       len(s11["measurement_ids"]) if s11 else None)

    ok("yim: sample 8 belongs to two study series",
       bool(samples.get("8")) and len([s for s in series.values()
                                       if "8" in s["member_sample_codes"]]) == 2,
       [s["author_series_name"] for s in series.values()
        if "8" in s["member_sample_codes"]])
    ok("yim: sample 12 belongs to two study series",
       bool(samples.get("12")) and len([s for s in series.values()
                                        if "12" in s["member_sample_codes"]]) == 2,
       [s["author_series_name"] for s in series.values()
        if "12" in s["member_sample_codes"]])

    f8a = [m for m in ms.values() if m["source"]["printed_figure"] == "8"
           and m["source"]["panel"] == "a"]
    cases8a = {c for m in f8a for c in m["measures_case"]}
    ok("yim: Fig 8a repeat measurement stays one deposition case", len(cases8a) <= 1,
       sorted(cases8a))

    f8b_runs = [r for r in runs if r["kind"] == "DISTINCT_RUNS"]
    ok("yim: Fig 8b's distinct runs are recorded as such", len(f8b_runs) >= 1,
       len(f8b_runs))

    f9_reps = [r for r in reps if r["source"]["printed_figure"] == "9"]
    f9_cases = [c for c in cases if c["source_figures"] == ["9"]]
    ok("yim: Fig 9 declares 18 representation panels", len(f9_reps) == 18, len(f9_reps))
    ok("yim: Fig 9 yields 6 cases, not 18", len(f9_cases) == 6, len(f9_cases))
    ok("yim: Fig 9's scaled/normalized panels link to their as-measured panel",
       len([r for r in f9_reps if r.get("derived_representation_of")]) == 12,
       len([r for r in f9_reps if r.get("derived_representation_of")]))

    sims = sem(YIM, "simulation_runs")
    f10 = [s for s in sims if s["source"]["printed_figure"] == "10"]
    ok("yim: Fig 10 remains SimulationRun", len(f10) >= 10, len(f10))
    ok("yim: no simulation is an ExperimentalCase",
       not any(s["is_experimental_case"] for s in sims))
    ok("yim: every Fig 10 series is still 'simulated'",
       all(s["data_source"] == ["simulated"] for s in f10 if s["data_source"]),
       [s["data_source"] for s in f10[:3]])

    f11 = [c for c in cases if c["source_figures"] == ["11"]]
    ok("yim: Fig 11's deposition-condition variations are distinct cases", len(f11) >= 4,
       len(f11))


if __name__ == "__main__":
    invariants()
    anchors()
    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    sys.exit(1 if _fail else 0)
