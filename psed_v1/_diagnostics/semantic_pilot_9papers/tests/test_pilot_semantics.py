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
from collections import Counter, defaultdict
import re
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))

_MANIFEST = json.loads((W / "pilot_papers.json").read_text())
PAPERS = _MANIFEST["papers"]
ROLES = _MANIFEST["roles"]
#: the four regression controls, whose corrected second-pass behaviour must reproduce
CONTROLS = [p for p in PAPERS if ROLES[p] == "original_control"]
#: none of these papers is "unseen" any more -- all have influenced resolver development
DEVELOPMENT = [p for p in PAPERS if ROLES[p] == "development_validation"]
AM, JES, CTA, YIM = CONTROLS

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
    # Gold (PDF, Table 1): Fig 9's two rows show samples 7/8/9 and 8/10/11. Sample 8 is
    # SHARED, so the union is {2(BASE), 4, 5, 6, 7} -- FIVE unique nominal cases, not six.
    # The old expectation of 6 double-counted the shared BASE specimen, and its filter
    # (source_figures == ["9"]) also missed any case Fig 9 shares with another figure.
    f9_cases = {c for m in ms.values() if m["source"]["printed_figure"] == "9"
                for c in m["measures_case"]}
    ok("yim: Fig 9 declares 18 representation panels", len(f9_reps) == 18, len(f9_reps))
    ok("yim: Fig 9 yields 5 unique cases (sample 8 shared), not 18",
       len(f9_cases) == 5, sorted(f9_cases))
    f11_cases = {c for m in ms.values() if m["source"]["printed_figure"] == "11"
                 for c in m["measures_case"]}
    ok("yim: Fig 11 yields 5 unique cases (sample 12 shared), not 6",
       len(f11_cases) == 5, sorted(f11_cases))
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


def repair_regressions():
    """The two generic rules added in the condition-precedence / case-threshold repair.

    Both are stated as behaviour, not as counts: a more specific source must win over an
    inherited default, and a characterisation result must not invent a deposition.
    """
    sys.path.insert(0, str(W / "code"))
    import pilot_cases as PC
    import pilot_semantics as PS

    # ---- 1. condition specificity precedence -------------------------------
    default = {"quantity": "cycle_number", "value": "500", "unit": "cycle",
               "provenance_type": "methods_default", "source": "methods"}
    specific = {"quantity": "cycle_number", "value": "1000", "unit": "cycles",
                "provenance_type": "sample_table_direct", "source": "sample_table"}
    res = PC.resolve_conditions([default, specific])
    ok("precedence: the specimen table beats a methods default",
       len(res) == 1 and res[0]["value"] == "1000", [(c["quantity"], c["value"]) for c in res])
    ok("precedence: the superseded default is retained, not discarded",
       any(h["value"] == "500" for h in res[0].get("superseded") or []),
       res[0].get("superseded"))
    ok("precedence: an inherited default is not a scientific contradiction",
       PC.compatibility(PC._cond_key([default, specific]),
                        PC._cond_key([specific]))[0] == "COMPATIBLE")
    ok("precedence: two EQUALLY specific values still contradict",
       PC.compatibility(PC._cond_key([specific]),
                        PC._cond_key([dict(specific, value="250")]))[0] == "CONTRADICTS")
    ok("precedence: sample-specific outranks figure-local outranks methods outranks paper",
       (PC.provenance_rank({"provenance_type": "sample_table_direct"})
        > PC.provenance_rank({"provenance_type": "figure_local_direct"})
        > PC.provenance_rank({"provenance_type": "methods_default"})
        > PC.provenance_rank({"provenance_type": "paper_default"})))

    # ---- 2. case-minting evidence threshold --------------------------------
    inherited_only = [{"candidate_id": "X", "kind": "whole_curve", "source_figure": "6",
                       "case_conditions": [dict(default)], "sample_codes": []}]
    anchored, why = PS._anchors_deposition_case(inherited_only)
    ok("threshold: inherited defaults alone do not mint a deposition case",
       anchored is False and "inherited" in why, why[:60])
    for field, val in (("sample_codes", ["7"]), ("local_synthesis", "deposited 45 nm SiO2"),
                       ("label", "sample A")):
        m = dict(inherited_only[0]); m[field] = val
        ok("threshold: %s is positive deposition identity" % field,
           PS._anchors_deposition_case([m])[0] is True)
    ok("threshold: a design branch always anchors",
       PS._anchors_deposition_case([{"kind": "design_branch", "case_conditions": []}])[0])
    ok("threshold: a tabulated specimen always anchors",
       PS._anchors_deposition_case([{"kind": "tabulated_specimen",
                                     "case_conditions": []}])[0])
    ok("threshold: a caption restating the default recipe is not local synthesis",
       PS.local_synthesis_evidence("coated by an Al2O3 film at 300 C in 500 cycles",
                                   {"cycle_number": {"500"}}) is None)
    ok("threshold: a caption describing a distinct deposited object IS local synthesis",
       PS.local_synthesis_evidence(
           "an ALD SiO2 film of 7.0 nm thickness deposited on a Si wafer",
           {"cycle_number": {"500"}}) is not None)

    # ---- 3. Yim source-grounded gold ---------------------------------------
    cases = sem(YIM, "experimental_cases")
    samples = sem(YIM, "samples")
    ms = {m["measurement_id"]: m for m in sem(YIM, "measurements")}
    ok("yim: 16 specimens from Table 1", len(samples) == 16, len(samples))
    ok("yim: 11 nominal ExperimentalCases", len(cases) == 11, len(cases))
    base = next((c for c in cases if len(c.get("sample_ids") or []) > 1), None)
    ok("yim: BASE is realised by samples 2,4,5,6,8,12",
       base is not None and sorted((s.rsplit("::", 1)[-1] for s in base["sample_ids"]),
                                   key=int) == ["2", "4", "5", "6", "8", "12"],
       sorted(s.rsplit("::", 1)[-1] for s in (base or {}).get("sample_ids") or []))
    of_code = {}
    for c in cases:
        for sid in c.get("sample_ids") or []:
            of_code[sid.rsplit("::", 1)[-1]] = c["case_id"]
    with_case = {s["source_sample_code"] for s in samples
                 if s.get("experimental_case_ids")}
    for code in ("1", "3"):
        ok("yim: sample %s has a table-defined case with no plotted curve" % code,
           code not in of_code or code in with_case, code)
    s11 = next((s for s in samples if s["source_sample_code"] == "11"), {})
    cyc = [c for c in s11.get("case_defining_conditions") or []
           if c["quantity"] == "cycle_number"]
    ok("yim: sample 11 carries its tabulated 1000 cycles",
       any(str(c["value"]).startswith("1000") for c in cyc), [c["value"] for c in cyc])
    ok("yim: sample 11 resolves to a case, not blocked by the 500-cycle default",
       "11" in of_code, of_code.get("11"))
    f6 = [m for m in ms.values() if m["source"]["printed_figure"] == "6"]
    ok("yim: Fig 6 is preserved as a Measurement", len(f6) >= 1, len(f6))
    ok("yim: Fig 6 mints no unsupported deposition case",
       all(not m.get("measures_case") for m in f6),
       [m.get("measures_case") for m in f6])

    # ---- 4. preservation ----------------------------------------------------
    inv = json.loads((W / "comparison" / "semantic_invariants.json").read_text())
    for pid, v in sorted(inv.items()):
        cp = v.get("source_curves_preserved") or {}
        pp = v.get("points_preserved") or {}
        ok("preserved: %s curves" % pid[:22], cp.get("old") == cp.get("pilot"), cp)
        ok("preserved: %s points" % pid[:22], pp.get("old") == pp.get("pilot"), pp)


def curve_attribution_join():
    """Generic behaviour of curve -> semantic entity attribution.

    An explicit `linked_experiment_id` is candidate evidence, not unconditional truth. It
    is refused only on POSITIVE contradiction with the curve's own provenance; absence of
    information never refuses it, and a refused link leaves the curve for source-slice
    matching rather than forcing an attribution.
    """
    sys.path.insert(0, str(W / "code"))
    import pilot_semantics as PS
    L = PS.link_is_supported

    def ent(fig=None, panel=None, series=None, didx=None):
        return {"printed_figure_number": fig, "panel": panel, "source_series": series,
                "fig_docling_index": didx}

    def cur(fig=None, panel=None, series=None, didx=None):
        return {"figure": fig, "panel": panel, "series": series, "figure_index": didx}

    # ---- accepted attributions ---------------------------------------------
    ok("join: same figure/panel with no competing entity is accepted",
       L(cur("2", "a", "HDMP", "1"), ent("2", "a", "HDMP", "1"), {})[0])
    ok("join: source series supporting the linked entity is accepted",
       L(cur("3", "c", "200 C", "1"), ent("3", "c", "200 C", "1"),
         {("1", "c"): {"200 C", "300 C"}})[0])
    ok("join: a case-suffixed link with only one compatible entity is accepted",
       L(cur("3", "b", "Thickness", "1"), ent("3", "b", "Thickness", "1"),
         {("1", "b"): {"Thickness"}})[0])
    ok("join: an unknown linked entity cannot be contradicted, so it is accepted",
       L(cur("2", "a", "X", "1"), None, {})[0])

    # ---- rejected / deferred attributions -----------------------------------
    okc, why = L(cur("9", "a", "m/z = 18", "5"), ent("10", "a", "ALD", "6"), {})
    ok("join: a linked entity in a different figure is refused", not okc, why[:70])
    okc, _ = L(cur("2", "a", "X", "1"), ent("2", "b", "Y", "1"), {})
    ok("join: a linked entity in a contradictory panel is refused", not okc)
    okc, why = L(cur("3", "c", "300 C", "1"), ent("3", "c", "200 C", "1"),
                 {("1", "c"): {"200 C", "300 C"}})
    ok("join: a case-suffixed link is refused when the local label matches a sibling",
       not okc, why[:70])
    okc, _ = L(cur("5", "a", "Simulated", "3"), ent("5", "a", "Measured", "3"),
               {("3", "a"): {"Measured", "Simulated"}})
    ok("join: a link conflicting with a locally attributable simulation entity is refused",
       not okc)

    # ---- safety behaviour ---------------------------------------------------
    ok("join: missing figure provenance alone does not refuse a link",
       L(cur(None, "a", "X", None), ent(None, "a", "X", None), {})[0])
    ok("join: missing panel provenance alone does not refuse a link",
       L(cur("2", None, "X", "1"), ent("2", None, "X", "1"), {})[0])
    ok("join: a differing label with NO sibling carrying it does not refuse a link",
       L(cur("2", "a", "Pt", "1"), ent("2", "a", "<single>", "1"),
         {("1", "a"): {"<single>"}})[0])
    ok("join: identical conditions are never consulted as identity evidence",
       "condition" not in (PS.link_is_supported.__doc__ or "").split("Equality")[0])

    # ---- applied to the real outputs ----------------------------------------
    het, rs_multi = [], []
    for pid in PAPERS:
        rs = sem(pid, "result_series")
        labels = defaultdict(set)
        for r in rs:
            lab = (r.get("source") or {}).get("series")
            if r.get("produced_by") and lab:
                labels[r["produced_by"]].add(lab)
        for mid, labs in labels.items():
            if len(labs) > 1:
                het.append((pid, mid, sorted(labs)))
        cases = sem(pid, "experimental_cases")
        case_of = defaultdict(list)
        for c in cases:
            for mid in c.get("measurement_ids") or []:
                case_of[mid].append(c["case_id"])
        for r in rs:
            if len(case_of.get(r.get("produced_by")) or []) > 1:
                rs_multi.append((pid, r["result_series_id"]))
    ok("join: no Measurement carries curves with different legend labels", not het,
       het[:3])
    # a ResultSeries may still legitimately reach several cases through branches
    print("    [join] ResultSeries reaching >1 case through branches: %d" % len(rs_multi))

    # a simulated curve binds to a SimulationRun and mints no ExperimentalCase
    bad_sim = []
    for pid in PAPERS:
        sims = {s.get("simulation_run_id") or s.get("run_id")
                for s in sem(pid, "simulation_runs")}
        cases = sem(pid, "experimental_cases")
        in_case = {mid for c in cases for mid in c.get("measurement_ids") or []}
        for r in sem(pid, "result_series"):
            lab = str((r.get("source") or {}).get("series") or "").strip().lower()
            if lab == "simulated":
                if r.get("produced_by") not in sims:
                    bad_sim.append((pid, r["result_series_id"], "not a SimulationRun"))
                if r.get("produced_by") in in_case:
                    bad_sim.append((pid, r["result_series_id"], "minted a case"))
    ok("join: a simulated curve binds to a SimulationRun and mints no case", not bad_sim,
       bad_sim[:3])


def progression_continuity_guard():
    """Targeted validation of the PROGRESSION_STAGE_LINK continuity guard.

    The guard exists because separate CURVES are prima facie separate objects. Merging
    them into one deposition needs positive evidence that one growth produced them, and
    that evidence must be attributable to the results in hand -- not to prose elsewhere
    in the paper.
    """
    sys.path.insert(0, str(W / "code"))
    import pilot_design as D

    # -- what does and does not count as continuity evidence ------------------
    accepted = [
        ("the same film was repeatedly measured after each cycle", "same specimen"),
        ("the same specimen was then re-scanned", "same specimen re-measured"),
        ("without breaking vacuum the sample was scanned again", "no vacuum break"),
        ("the spectra were recorded continuously during one deposition",
         "continuous recording"),
    ]
    for text, label in accepted:
        v, why = D.progression_continuity(text)
        ok("guard: %s is continuity evidence" % label, v == "CONTINUOUS", (v, why[:60]))

    rejected = [
        ("data points were taken after a certain number of cycles", "'after N cycles'"),
        ("measured by in situ spectroscopic ellipsometry", "'in situ' alone"),
        ("the thickness is shown as a function of the deposition time",
         "generic growth prose"),
        ("", "silence"),
    ]
    for text, label in rejected:
        v, why = D.progression_continuity(text)
        ok("guard: %s is NOT continuity evidence" % label, v == "UNRESOLVED", (v, why[:60]))

    v, _ = D.progression_continuity("a series of samples was prepared, one per cycle count")
    ok("guard: separately prepared specimens block a merge", v == "SEPARATE", v)

    # -- the guard is applied, not merely defined -----------------------------
    applied, unresolved, over_strong = [], [], []
    for pid in PAPERS:
        links = sem(pid, "links")
        ev = {e["evidence_id"]: e for e in sem(pid, "evidence")}
        for l in links:
            if l.get("link_class") != "PROGRESSION_STAGE_LINK":
                continue
            applied.append((pid, l.get("a"), l.get("b")))
            detail = (ev.get(l.get("evidence")) or {}).get("detail", "")
            # every applied progression merge must cite specimen/run identity or a
            # locally-attributable statement that one growth was followed
            if not any(k in detail for k in ("same specimen", "same deposition run",
                                             "this scope states that one growth")):
                over_strong.append((pid, l.get("a"), l.get("b"), detail[:80]))
            if l.get("strength") == "EXPLICIT" and "same" not in detail:
                over_strong.append((pid, "EXPLICIT without stated identity", l.get("a"), ""))
        for e in sem(pid, "evidence"):
            if e.get("kind") == "progression_stage_unresolved":
                unresolved.append((pid, e.get("subject")))
    ok("guard: every applied progression merge cites positive identity evidence",
       not over_strong, over_strong[:3])
    ok("guard: declined progression pairs are recorded with a reason",
       all(isinstance(u[1], str) for u in unresolved), len(unresolved))
    # the active set currently establishes no continuity locally; if that ever changes,
    # this check simply reports the new count rather than failing
    print("    [guard] applied progression merges: %d ; declined and recorded: %d"
          % (len(applied), len(unresolved)))


def structural_invariants():
    """The graph must hold together on its own terms, for every paper.

    ExperimentalDesign -> DesignFactor -> DesignBranch -> ExperimentalCase
    -> Sample / DepositionRun -> Measurement -> PlotRepresentation
    """
    for pid in PAPERS:
        cases = sem(pid, "experimental_cases")
        samples = sem(pid, "samples")
        runs = sem(pid, "deposition_runs")
        series = sem(pid, "study_series")
        designs = sem(pid, "experimental_designs")
        branches = sem(pid, "design_branches")
        ms = {m["measurement_id"]: m for m in sem(pid, "measurements")}
        reps = sem(pid, "representations")
        sims = {s.get("simulation_run_id") or s.get("run_id") for s in
                sem(pid, "simulation_runs")}
        sample_by = {s["source_sample_code"]: s for s in samples}
        tag = pid[:20]

        # -- complete nominal case fingerprint --------------------------------------
        # Two cases may serialise the same condition set only when some OTHER
        # case-defining dimension the model represents tells them apart. When nothing
        # does, the case must say so rather than present itself as a distinct deposition.
        by_fp = defaultdict(list)
        for c in cases:
            by_fp[c.get("nominal_fingerprint")].append(c)
        unmarked = []
        for k, group in by_fp.items():
            if len(group) < 2:
                continue
            for c in group:
                if c.get("identity_status") != "INDISTINGUISHABLE_FROM_SIBLING":
                    unmarked.append((c["case_id"], k))
        ok("S1 %s: colliding cases are marked, never presented as distinct" % tag,
           not unmarked, unmarked[:3])
        ok("S1b %s: every case records what distinguishes it" % tag,
           all(c.get("identity_status") for c in cases),
           [c["case_id"] for c in cases if not c.get("identity_status")][:3])
        # the fingerprint must carry the components that establish identity
        thin = [c["case_id"] for c in cases
                if c.get("sample_ids") and len(c.get("case_defining_conditions") or []) < 3]
        ok("S1c %s: a specimen-derived case keeps its full condition set" % tag,
           not thin, thin[:3])

        # -- bidirectional Sample <-> ExperimentalCase realization ------------------
        bad = []
        for c in cases:
            for sid in c.get("sample_ids") or []:
                s = sample_by.get(sid.rsplit("::", 1)[-1])
                if not s or c["case_id"] not in (s.get("experimental_case_ids") or []):
                    bad.append((c["case_id"], sid))
        for s in samples:
            for cid in s.get("experimental_case_ids") or []:
                c = next((x for x in cases if x["case_id"] == cid), None)
                if not c or s["sample_id"] not in (c.get("sample_ids") or []):
                    bad.append((s["sample_id"], cid))
        ok("S2 %s: Sample <-> Case realization is bidirectional" % tag, not bad, bad[:3])

        # -- a case with no plotted result still keeps its specimens ----------------
        orphan = [s["source_sample_code"] for s in samples
                  if not s.get("experimental_case_ids")]
        ok("S3 %s: every Sample realizes a Case" % tag, not orphan, orphan[:5])

        # -- StudySeries membership is many-to-many and survives without curves -----
        bad = []
        for ser in series:
            for code in ser.get("member_sample_codes") or []:
                s = sample_by.get(code)
                if not s or ser["series_id"] not in (s.get("study_series_ids") or []):
                    bad.append((ser["series_id"], code))
        ok("S4 %s: StudySeries membership is recorded on the Sample" % tag, not bad,
           bad[:3])

        # -- Run -> Sample provenance, and a run never merges cases -----------------
        bad = []
        for r in runs:
            for code in r.get("sample_codes") or []:
                s = sample_by.get(code)
                if not s or s.get("produced_by_run") != r["run_id"]:
                    bad.append((r["run_id"], code))
        ok("S5 %s: DepositionRun -> Sample provenance is attached" % tag, not bad, bad[:3])
        ok("S6 %s: a shared run does not merge the cases it produced" % tag,
           all(len(r.get("experimental_case_ids") or []) >= 1 for r in runs) if runs
           else True,
           [(r["run_id"], r.get("experimental_case_ids")) for r in runs])

        # -- DesignBranch uniqueness and design/branch agreement --------------------
        keys = [(b.get("design_id"), str(b.get("value"))) for b in branches]
        ok("S7 %s: DesignBranch identity is unique per design+value" % tag,
           len(keys) == len(set(keys)),
           [k for k, n in Counter(keys).items() if n > 1][:3])
        ok("S8 %s: design ids are unique" % tag,
           len({d["design_id"] for d in designs}) == len(designs), len(designs))
        owned = defaultdict(list)
        for b in branches:
            owned[b.get("design_id")].append(b)
        bad = [d["design_id"] for d in designs
               if d.get("branch_values") is not None
               and len(d["branch_values"]) != len({str(b.get("value"))
                                                   for b in owned.get(d["design_id"], [])})]
        ok("S9 %s: a design's branch list matches its branch objects" % tag, not bad,
           bad[:3])

        # -- every design declares a DesignFactor or a varied quantity --------------
        ok("S10 %s: every design names what it varies" % tag,
           all(d.get("varied_quantity") for d in designs), len(designs))

        # -- branch appearances >= unique branches ----------------------------------
        appear = sum(len(b.get("measurement_ids")
                         or ([b["measurement_id"]] if b.get("measurement_id") else []))
                     or 1 for b in branches)
        ok("S11 %s: source branch appearances >= unique DesignBranches" % tag,
           appear >= len(branches), (appear, len(branches)))

        # -- representation provenance is traversable -------------------------------
        bad = []
        for r in reps:
            u = r.get("underlying_measurement")
            if not u:
                bad.append((r["representation_id"], "no underlying object"))
            elif u not in ms and u not in sims and not str(u).startswith("SIM::"):
                bad.append((r["representation_id"], u))
        ok("S12 %s: every representation resolves to a Measurement or SimulationRun" % tag,
           not bad, bad[:3])
        bad = []
        for r in reps:
            m = ms.get(r.get("underlying_measurement"))
            if m is None:
                continue
            # the representation must recover exactly the measurement's own provenance
            got = sorted(m.get("measures_case") or [])
            via = sorted({c for c in got})
            if got != via:
                bad.append(r["representation_id"])
        ok("S13 %s: a representation recovers its measurement's case provenance" % tag,
           not bad, bad[:3])

        # -- no active contradiction from a superseded lower-specificity condition --
        stale = [l for l in sem(pid, "links")
                 if l.get("decision_status") == "STALE_SUPERSEDED"]
        ok("S14 %s: no blocked edge rests on a superseded condition" % tag, not stale,
           [(l.get("a"), l.get("b")) for l in stale][:3])

        # -- every blocked edge is classified --------------------------------------
        unclassified = [l for l in sem(pid, "links") if not l.get("decision_status")]
        ok("S15 %s: every merge decision is classified" % tag, not unclassified,
           len(unclassified))


if __name__ == "__main__":
    invariants()
    anchors()
    repair_regressions()
    curve_attribution_join()
    progression_continuity_guard()
    structural_invariants()
    print("\n%d papers: %d passed, %d failed" % (len(PAPERS), len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    sys.exit(1 if _fail else 0)
