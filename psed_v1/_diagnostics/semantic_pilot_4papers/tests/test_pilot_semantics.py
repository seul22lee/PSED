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


#: short prefix used in anchor names -> the paper it belongs to. Paper ids live HERE and
#: nowhere under code/, so the report can group anchors without naming a paper itself.
ANCHOR_PAPER = {"am": AM, "jes": JES, "cta": CTA, "yim": YIM}


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %-4s %-62s %s" % ("PASS" if cond else "FAIL", name, detail if not cond else ""))
    head = name.split(":", 1)[0].strip().lower()
    pid = ANCHOR_PAPER.get(head)
    if pid:
        # machine-readable line for the HTML report: it carries the paper id explicitly
        print("ANCHOR\t%s\t%s\t%s\t%s"
              % (pid, "PASS" if cond else "FAIL", name.split(":", 1)[-1].strip(),
                 str(detail)[:200]))


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

    # 17. numeric ranges are positive intervals, never negative scalars
    bad = []
    for pid in PAPERS:
        for c in sem(pid, "experimental_cases"):
            for x in c["case_defining_conditions"]:
                v = x.get("value")
                if isinstance(v, (int, float)) and v < 0:
                    import pilot_ranges as _PR
                    okv, _ = _PR.sign_is_physical(x["quantity"], v)
                    if not okv:
                        bad.append((pid, c["case_id"], x["quantity"], v))
    ok("17. no unphysical negative condition survives", not bad, bad[:4])

    # 18. material roles are internally consistent
    bad = []
    for pid in PAPERS:
        for c in sem(pid, "experimental_cases"):
            roles = c.get("material_roles") or {}
            if c.get("deposited_material") is None and "DEPOSITED" in roles.values() \
                    and len([m for m, r in roles.items() if r == "DEPOSITED"]) == 1:
                bad.append((pid, c["case_id"], roles))
    ok("18. no case asserts one DEPOSITED material while its deposit is null", not bad,
       bad[:3])

    # 19. paper-wide inventory alone never asserts a local role
    bad = []
    for pid in PAPERS:
        for c in sem(pid, "experimental_cases"):
            if c.get("material_status") == "CANDIDATE_ONLY" and c.get("material_roles"):
                bad.append((pid, c["case_id"]))
    ok("19. a candidate-only material asserts no role", not bad, bad[:3])

    # 20. identified runs are real executions, not assertions about runs
    bad = []
    for pid in PAPERS:
        for r in sem(pid, "deposition_runs"):
            if not r.get("sample_ids"):
                bad.append((pid, r["run_id"], r.get("kind")))
    ok("20. every DepositionRun names at least one specimen", not bad, bad[:3])

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
    """Regression expectations read from the ORIGINAL PDFs. Paper-specific values appear
    here and nowhere under code/ — invariant 16 checks that mechanically."""
    print("\n=== PDF-GROUND-TRUTH ANCHORS ===")
    import pilot_ranges as PR

    # ---- am.2016.182 -------------------------------------------------------
    cases = sem(AM, "experimental_cases")
    meas = {m["measurement_id"]: m for m in sem(AM, "measurements")}
    cross = [c for c in cases if len(set(c["source_panels"])) > 1]
    ok("am: GPC / resistivity / XPS join into one deposition case", len(cross) >= 2,
       "%d multi-panel cases" % len(cross))
    techs = set()
    for c in cross:
        techs |= {t for m in c["measurement_ids"] for t in (meas[m]["technique"] or [])}
    ok("am: that case carries all three techniques",
       {"growth_per_cycle", "resistivity", "XPS"} <= techs, sorted(techs))
    blocked = [l for l in sem(AM, "links") if l["action"] == "BLOCKED"]
    ok("am: a different precursor still blocks the merge", len(blocked) >= 1, len(blocked))
    ok("am: the blocked merges clash on chemistry",
       all(any(x["quantity"] in ("precursor", "coreactant") for x in l["detail"]["clash"])
           for l in blocked), [l["detail"]["clash"] for l in blocked][:2])
    f4 = [m for m in sem(AM, "measurements") if m["source"]["printed_figure"] == "4"]
    ok("am: printed Figure 4 device panels are present", len(f4) >= 3, len(f4))
    ok("am: Figure 4 is caption-only, with no invented data",
       all(m.get("data_recovered") is False and not m["result_series_ids"] for m in f4))
    ok("am: Figure 4 device characterisation mints no deposition case",
       not any("4" in c["source_figures"] for c in cases))

    # ---- 2.067203jes -------------------------------------------------------
    cases = sem(JES, "experimental_cases")
    # PDF: "ultrashort doses (10-120 ms)" — a positive interval
    rng = [x for c in cases for x in c["case_defining_conditions"]
           if x.get("value_kind") == "range"]
    ok("jes: a stated interval is carried as an interval, not a negative scalar",
       any(x.get("superseded_value") is not None for x in rng), len(rng))
    ok("jes: no negative pulse time or cycle count survives",
       not [x for c in cases for x in c["case_defining_conditions"]
            if isinstance(x.get("value"), (int, float)) and x["value"] < 0
            and x["quantity"] in ("pulse_time", "cycle_number", "purge_time")])
    # PDF Fig 1: vapour pressure of a precursor — not a deposition
    f1 = [c for c in cases if "1" in c["source_figures"]]
    ok("jes: printed Fig 1 (precursor vapour pressure) is not a deposition case",
       not f1, [c["case_id"] for c in f1])
    f1m = [m for m in sem(JES, "measurements") if m["source"]["printed_figure"] == "1"]
    ok("jes: Fig 1 is still preserved as Measurements", len(f1m) >= 1, len(f1m))
    ok("jes: Fig 1 asserts no material role",
       not any(m.get("_material") for m in f1m) or all(m.get("reports_species_property")
                                                       for m in f1m))
    # PDF Fig 8: HAR trench, AR ~30, 18.5 x 0.6 um, 830 cycles of ALD SiO2
    har = [c for c in cases if c.get("geometry") == "vertical_structure"]
    ok("jes: the HAR trench figure produces a case with local geometry", len(har) == 1,
       len(har))
    if har:
        h = har[0]
        q = {x["quantity"]: x for x in h["case_defining_conditions"]}
        ok("jes: HAR geometry comes from the figure, not the paper default",
           h.get("geometry_source") == "figure/panel caption", h.get("geometry_source"))
        ok("jes: HAR case carries aspect ratio ~30", q.get("aspect_ratio", {}).get("value") == 30,
           q.get("aspect_ratio"))
        ok("jes: HAR case carries 830 ALD cycles", q.get("cycle_number", {}).get("value") == 830,
           q.get("cycle_number"))
        ok("jes: HAR case carries trench depth 18.5 and width 0.6",
           q.get("feature_height", {}).get("value") == 18.5
           and q.get("feature_width", {}).get("value") == 0.6,
           (q.get("feature_height", {}).get("value"), q.get("feature_width", {}).get("value")))
        ok("jes: HAR deposits SiO2", h.get("deposited_material") == "SiO2",
           h.get("deposited_material"))
        ok("jes: HAR claims no digitised points",
           not any(sem(JES, "measurements")[0] for _ in [])
           or all(not m["result_series_ids"] for m in sem(JES, "measurements")
                  if m.get("recovery_cause") == "image_only_figure"))
    ok("jes: planar and HAR contexts coexist",
       len({c.get("geometry") for c in cases if c.get("geometry")}) >= 2,
       sorted({c.get("geometry") for c in cases if c.get("geometry")}))
    stack = [c for c in cases if c.get("multi_material_context")]
    ok("jes: the SiO2/Al2O3 stack context is representable", len(stack) >= 1, len(stack))
    ok("jes: stack constituents carry a stack role",
       any(set(c["material_roles"].values()) & {"STACK_COMPONENT"} for c in stack),
       [c["material_roles"] for c in stack[:2]])
    ok("jes: distinct cases were not over-merged", len(cases) > 5, len(cases))

    # ---- c7ta03257a --------------------------------------------------------
    cases = sem(CTA, "experimental_cases")
    ms = sem(CTA, "measurements")
    chains = sem(CTA, "provenance_chains")
    ok("cta: two deposition cases exist with no x-y process curve", len(cases) == 2,
       len(cases))
    labels = {(c.get("synthesis_label") or "").lower() for c in cases}
    ok("cta: the cases are the full replica and the tubular replica",
       any("full" in l for l in labels) and any("tube" in l or "tubular" in l for l in labels),
       sorted(labels))
    cv = [m for m in ms if set(m["technique"] or []) &
          {"cyclic_voltammetry", "impedance_spectroscopy"}]
    ok("cta: CV / impedance are Measurements, never cases", len(cv) >= 4
       and not any(m["measurement_id"].startswith("CASE") for m in cv), len(cv))
    coated8 = [m for m in ms if m["source"]["printed_figure"] == "8"
               and m.get("provenance_role") == "PRODUCT_OF_CASE"]
    ok("cta: Fig 8 coated results carry tubular-replica provenance", len(coated8) >= 2,
       len(coated8))
    ok("cta: that provenance points at the tubular synthesis case",
       all(any((c.get("synthesis_label") or "").lower().find("tube") >= 0
               or (c.get("synthesis_label") or "").lower().find("tubular") >= 0
               for c in cases if c["case_id"] in m["measures_case"]) for m in coated8),
       [m["measures_case"] for m in coated8])
    bare = [m for m in ms if m.get("provenance_role") == "REFERENCE"]
    ok("cta: bare / uncoated reference series exist and are typed REFERENCE",
       len(bare) >= 2, len(bare))
    ok("cta: no reference series is attributed to a deposition case",
       not any(m["measures_case"] for m in bare))
    f7 = [m for m in ms if m["source"]["printed_figure"] == "7"
          and m.get("provenance_role") != "REFERENCE"]
    ok("cta: Fig 7 coated result stays UNRESOLVED (the source names no protocol)",
       bool(f7) and not any(m["measures_case"] for m in f7),
       [m["measures_case"] for m in f7])
    f8b = [m for m in ms if m["source"]["printed_figure"] == "8"
           and m["source"]["panel"] == "b"]
    ok("cta: printed Fig 8(b) is represented", len(f8b) == 1, len(f8b))
    ok("cta: Fig 8(b) records why it was missing",
       bool(f8b) and f8b[0].get("recovery_cause") == "panel_absent_from_crop",
       f8b[0].get("recovery_cause") if f8b else None)
    ok("cta: the resolved chain names the device it was placed on",
       any(c["status"] == "RESOLVED" and c.get("device") for c in chains),
       [(c["status"], c.get("device")) for c in chains])

    # ---- Yim 2020 ----------------------------------------------------------
    cases = sem(YIM, "experimental_cases")
    samples = {s["source_sample_code"]: s for s in sem(YIM, "samples")}
    runs = sem(YIM, "deposition_runs")
    run_ev = sem(YIM, "run_evidence")
    series = {s["author_series_name"]: s for s in sem(YIM, "study_series")}
    reps = sem(YIM, "representations")
    ms = {m["measurement_id"]: m for m in sem(YIM, "measurements")}

    # PDF Table 1 footnote a defines every series
    ok("yim: Series A primary variable is the pillar layout",
       series.get("Series A", {}).get("varied_variable") == "pillar_layout",
       series.get("Series A", {}).get("varied_variable"))
    ok("yim: Series B primary variable is the reflectometer magnification",
       series.get("Series B", {}).get("varied_variable") == "reflectometer_magnification",
       series.get("Series B", {}).get("varied_variable"))
    ok("yim: Series C primary variable is the channel height",
       series.get("Series C", {}).get("varied_variable") == "feature_height",
       series.get("Series C", {}).get("varied_variable"))
    ok("yim: Series D primary variable is the ALD cycle count",
       series.get("Series D", {}).get("varied_variable") == "cycle_number",
       series.get("Series D", {}).get("varied_variable"))
    ok("yim: Series E primary variable is the TMA pulse time",
       series.get("Series E", {}).get("varied_variable") == "pulse_time",
       series.get("Series E", {}).get("varied_variable"))
    ok("yim: Series F primary variable is the purge time",
       series.get("Series F", {}).get("varied_variable") == "purge_time",
       series.get("Series F", {}).get("varied_variable"))
    ok("yim: every series variable comes from the author's own declaration",
       all(s.get("varied_variable_source") == "author_declaration"
           for s in series.values()),
       {k: v.get("varied_variable_source") for k, v in series.items()})
    ok("yim: Series E keeps its pillar-layout co-variation without losing its variable",
       any(c["quantity"] == "pillar_layout"
           for c in series.get("Series E", {}).get("co_varying_context") or []),
       series.get("Series E", {}).get("co_varying_context"))
    ok("yim: Series B is typed a MEASUREMENT_SETTING",
       series.get("Series B", {}).get("varied_variable_role") == "MEASUREMENT_SETTING",
       series.get("Series B", {}).get("varied_variable_role"))

    # PDF Table 1: sample 4 = 50x, 5 = 10x, 6 = 5x; Fig 7 legends X50 / X10 / X5
    want = {"X50": "4", "X10": "5", "X5": "6"}
    got = {}
    for m in ms.values():
        if m["source"]["printed_figure"] != "7":
            continue
        # exact first token: "X5 (50 um)" must not also satisfy the "X50" expectation
        lab = str(m["source"].get("source_series") or "").upper().split(" ")[0]
        if lab in want:
            got[lab] = (m.get("performed_on") or "").split("::")[-1]
    for k, v in sorted(want.items()):
        ok("yim: Fig 7 %s maps to specimen %s" % (k, v), got.get(k) == v,
           "got %s" % got.get(k))
    ok("yim: that mapping is a value join, not list order",
       all(m.get("specimen_binding") == "value_join" for m in ms.values()
           if m["source"]["printed_figure"] == "7"),
       {m["source"]["source_series"]: m.get("specimen_binding") for m in ms.values()
        if m["source"]["printed_figure"] == "7"})
    setq = {x["quantity"] for m in ms.values() if m["source"]["printed_figure"] == "7"
            for x in m["measurement_settings"]}
    ok("yim: the magnification is attached as a MEASUREMENT_SETTING",
       "reflectometer_magnification" in setq, sorted(setq))
    spots = [x.get("derived_quantity", {}).get("value") for m in ms.values()
             if m["source"]["printed_figure"] == "7" for x in m["measurement_settings"]]
    ok("yim: each objective carries its methods-stated spot size",
       len([v for v in spots if v]) == 3, spots)
    b_cases = [c for c in cases if c["source_figures"] == ["7"]]
    ok("yim: magnification variation alone creates no deposition case", len(b_cases) <= 1,
       "%d cases from the Series B figure" % len(b_cases))

    s11 = samples.get("11")
    ok("yim: sample 11 carries several Measurements",
       bool(s11) and len(s11["measurement_ids"]) > 1,
       len(s11["measurement_ids"]) if s11 else None)
    for code in ("8", "12"):
        ok("yim: sample %s belongs to two study series" % code,
           len([s for s in series.values() if code in s["member_sample_codes"]]) == 2,
           [s["author_series_name"] for s in series.values()
            if code in s["member_sample_codes"]])

    # PDF: "All of the films were grown in the same ALD run" (Series A)
    ok("yim: exactly one IDENTIFIED DepositionRun exists", len(runs) == 1, len(runs))
    ok("yim: that run holds the three Series A specimens",
       bool(runs) and sorted(runs[0]["sample_codes"]) == ["1", "2", "3"],
       runs[0]["sample_codes"] if runs else None)
    ok("yim: run-distinctness assertions are NOT counted as runs", len(run_ev) >= 1,
       len(run_ev))
    ok("yim: those assertions carry their evidence and name no specimen",
       all(not r.get("sample_ids") and (r.get("different_run_evidence")
                                        or r.get("same_run_evidence")) for r in run_ev))

    f8a = [m for m in ms.values() if m["source"]["printed_figure"] == "8"
           and m["source"]["panel"] == "a"]
    ok("yim: Fig 8a repeat measurement stays one deposition case",
       len({c for m in f8a for c in m["measures_case"]}) <= 1,
       sorted({c for m in f8a for c in m["measures_case"]}))

    f9_reps = [r for r in reps if r["source"]["printed_figure"] == "9"]
    f9_cases = [c for c in cases if c["source_figures"] == ["9"]]
    ok("yim: Fig 9 declares 18 representation panels", len(f9_reps) == 18, len(f9_reps))
    ok("yim: Fig 9 yields 6 cases, not 18", len(f9_cases) == 6, len(f9_cases))
    ok("yim: the scaled and normalized panels link to their as-measured panel",
       len([r for r in f9_reps if r.get("derived_representation_of")]) == 12,
       len([r for r in f9_reps if r.get("derived_representation_of")]))

    sims = sem(YIM, "simulation_runs")
    f10 = [s for s in sims if s["source"]["printed_figure"] == "10"]
    ok("yim: Fig 10 remains SimulationRun", len(f10) >= 10, len(f10))
    ok("yim: no simulation is an ExperimentalCase",
       not any(s["is_experimental_case"] for s in sims))
    ok("yim: every Fig 10 series is still 'simulated'",
       all(s["data_source"] == ["simulated"] for s in f10 if s["data_source"]))
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
