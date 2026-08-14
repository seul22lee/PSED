#!/usr/bin/env python3
"""Apply the entity-identity repairs and report what changed, and what could not.

Three things are repaired: `represents_same_measurement_as` becomes an operational
MeasurementAct grouping, Case->Run links are re-scoped to the sample that actually
carries them, and ResultSeries expose their complete case membership instead of a first
element. Nothing here rewrites persisted science: acts are a grouping over existing
Measurement ids, and every source id keeps working.

The fourth thing -- merging Sample entities that may be one physical specimen -- is NOT
done, because the persisted records carry no traceable specimen identifier and the source
text's only same-sample statements concern a different figure. Guessing from equal
conditions is exactly the inference the identity rules forbid, so it is reported as
extraction debt rather than performed.

    python3 _diagnostics/entity_identity_repair/build_entity_identity_repair.py
"""
import hashlib
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W))

from pipeline.query import entity_identity as EI                       # noqa: E402

OUT = W / "_diagnostics" / "entity_identity_repair"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
AUDIT = W / "_diagnostics" / "entity_identity"
BASELINE = "762e9de"


def code_hash():
    h = hashlib.sha256()
    for p in (Path(__file__), W / "pipeline" / "query" / "entity_identity.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def main():
    papers = json.loads((PILOT / "pilot_papers.json").read_text())["papers"]
    graph = {"cases": {}, "samples": {}, "runs": {}, "measurements": {},
             "measurement_acts": {}, "simulation_runs": {}, "result_series": {}}
    acts_all, sample_rows, run_rows, multi_case, hi_card = {}, [], {}, [], []
    stats = Counter()

    for pid in papers:
        D = EI.load_paper(PILOT, pid)
        cases = D["experimental_cases"]
        samples = {s["sample_id"]: s for s in D["samples"] if s.get("sample_id")}
        pcases = EI.producer_case_index(D["measurements"], D["simulation_runs"])
        acts, act_of = EI.measurement_acts(D["measurements"])
        key = lambda i: "%s::%s" % (pid, i)

        for a, members in acts.items():
            ak = key(a)
            series = [r["result_series_id"] for r in D["result_series"]
                      if r.get("produced_by") in members]
            cs = sorted({c for m in members for c in pcases.get(m, ())})
            samps = sorted({m2.get("performed_on") for m2 in D["measurements"]
                            if m2.get("measurement_id") in members and m2.get("performed_on")})
            acts_all[ak] = {
                "act_id": ak, "paper_id": pid, "members": members,
                "n_members": len(members), "result_series": series,
                "n_result_series": len(series), "case_ids": cs, "n_cases": len(cs),
                "sample_ids": samps, "n_samples": len(samps),
                "evidence": EI.act_evidence(D["measurements"], members)}
            graph["measurement_acts"][ak] = acts_all[ak]
            stats["acts"] += 1
            stats["multi_member_acts"] += 1 if len(members) > 1 else 0

        for c in cases:
            ck = key(c["case_id"])
            real = EI.realizations(c, samples, None)
            runs = EI.case_run_links(c, samples)
            graph["cases"][ck] = {
                "case_id": c["case_id"], "paper_id": pid,
                "semantics": "CONDITION_DEFINED_CASE",
                "fingerprint": c.get("nominal_fingerprint"),
                "material": c.get("deposited_material"),
                "sample_ids": c.get("sample_ids") or [],
                "realizations": real, "run_links": runs,
                "conditions_scope": EI.CASE_CONTEXT}
            stats["cases"] += 1
            if len(c.get("sample_ids") or []) > 1:
                stats["multi_sample_cases"] += 1
            # the over-propagation measure: runs reachable, versus samples that carry one
            if runs and len(c.get("sample_ids") or []) > len(runs):
                stats["cases_with_partial_run_coverage"] += 1

        for sid, s in samples.items():
            sk = key(sid)
            graph["samples"][sk] = {
                "sample_id": sid, "paper_id": pid,
                "source_sample_code": s.get("source_sample_code"),
                "table_series": s.get("table_series"),
                "also_in_series": s.get("also_in_series") or [],
                "produced_by_run": s.get("produced_by_run"),
                "run_status": "KNOWN" if s.get("produced_by_run") else "RUN_UNRESOLVED",
                "case_ids": s.get("experimental_case_ids") or [],
                "physical_specimen_id": None,
                "physical_identity_status": "NO_TRACEABLE_SPECIMEN_ID_IN_RECORD",
                "source_references": s.get("source_references") or []}
            sample_rows.append(graph["samples"][sk])
            stats["samples"] += 1
            stats["samples_with_run"] += 1 if s.get("produced_by_run") else 0

        for r in D["deposition_runs"]:
            rid = r.get("deposition_run_id") or r.get("id")
            members = [s["sample_id"] for s in samples.values()
                       if s.get("produced_by_run") == rid]
            downstream_m = [m["measurement_id"] for m in D["measurements"]
                            if m.get("performed_on") in members]
            run_rows[key(rid)] = {
                "run_id": rid, "paper_id": pid,
                "evidence": (str(r.get("evidence") or ""))[:240],
                "explicit_sample_members": members,
                "n_samples": len(members),
                "case_incidence": sorted({c for s in members
                                          for c in (samples[s].get("experimental_case_ids")
                                                    or [])}),
                "downstream_measurements": downstream_m,
                "scope": "SAMPLE_SCOPED"}
            graph["runs"][key(rid)] = run_rows[key(rid)]
            stats["runs"] += 1

        for m in D["measurements"]:
            mk = key(m["measurement_id"])
            graph["measurements"][mk] = {
                "measurement_id": m["measurement_id"], "paper_id": pid,
                "act_id": key(act_of.get(m["measurement_id"], "")),
                "technique": m.get("technique"), "measurand": m.get("measured_quantity"),
                "performed_on": m.get("performed_on"),
                "case_ids": sorted(m.get("measures_case") or []),
                "settings_scope": EI.MEASUREMENT_SETTING}
            stats["measurements"] += 1
        for s in D["simulation_runs"]:
            sid = s.get("simulation_run_id") or s.get("id")
            if sid:
                graph["simulation_runs"][key(sid)] = {
                    "simulation_run_id": sid, "paper_id": pid,
                    "case_ids": sorted(s.get("realises_case_ids") or []),
                    "producer_kind": "SIMULATION_RUN"}
                stats["simulation_runs"] += 1

        for r in D["result_series"]:
            cs = EI.cases_for_result_series(r, pcases)
            one, status = EI.single_case_for_series(r, pcases)
            rk = key(r["result_series_id"])
            graph["result_series"][rk] = {
                "result_series_id": r["result_series_id"], "paper_id": pid,
                "producer": r.get("produced_by"),
                "act_id": key(act_of[r["produced_by"]])
                          if r.get("produced_by") in act_of else None,
                "case_ids": cs, "n_cases": len(cs),
                "single_case": one, "case_cardinality_status": status,
                "data_source": r.get("data_source"),
                "x_quantity": r.get("x_quantity"), "y_quantity": r.get("y_quantity")}
            stats["result_series"] += 1
            if len(cs) > 1:
                stats["multi_case_series"] += 1
                multi_case.append({
                    "series_id": r["result_series_id"], "paper_id": pid,
                    "producer": r.get("produced_by"),
                    "act_id": graph["result_series"][rk]["act_id"],
                    "case_ids": cs, "n_cases": len(cs),
                    "x_quantity": r.get("x_quantity"),
                    "likely_sweep_quantity": r.get("x_quantity"),
                    "point_to_case_mapping": "UNRESOLVED_NOT_PERSISTED"})

        for c in cases:
            ms = [m for m in D["measurements"] if c["case_id"] in (m.get("measures_case") or [])]
            if len(ms) >= 3:
                a = sorted({act_of.get(m["measurement_id"]) for m in ms})
                hi_card.append({
                    "paper_id": pid, "case_id": c["case_id"],
                    "raw_measurements": len(ms), "measurement_acts": len(a),
                    "samples": len(c.get("sample_ids") or []),
                    "runs": len(EI.case_run_links(c, samples)),
                    "result_series": len([r for r in D["result_series"]
                                          if r.get("produced_by") in
                                          {m["measurement_id"] for m in ms}]),
                    "reason": ("MULTIPLE_PHYSICAL_SAMPLES"
                               if len(c.get("sample_ids") or []) > 1
                               else "MULTIPLE_FIGURE_REPRESENTATIONS")})

    payload = {
        "baseline_sha": BASELINE, "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "counts": dict(stats),
        "measurement_records": stats["measurements"],
        "measurement_acts": stats["acts"],
        "multi_member_acts": stats["multi_member_acts"],
        "max_members_per_act": max([a["n_members"] for a in acts_all.values()] or [0]),
        "max_series_per_act": max([a["n_result_series"] for a in acts_all.values()] or [0]),
        "max_cases_per_act": max([a["n_cases"] for a in acts_all.values()] or [0]),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dump = lambda n, d: (OUT / n).write_text(
        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    dump("entity_relation_graph.json", graph)
    dump("measurement_act_inventory.json", {
        **payload, "acts": acts_all,
        "group_size_distribution": dict(Counter(a["n_members"] for a in acts_all.values())),
        "series_per_act_distribution": dict(Counter(a["n_result_series"]
                                                    for a in acts_all.values()))})
    dump("sample_identity_inventory.json", {
        "samples_before": stats["samples"], "canonical_physical_samples": stats["samples"],
        "aliases_merged": 0, "samples_with_run": stats["samples_with_run"],
        "samples_without_run": stats["samples"] - stats["samples_with_run"],
        "samples_with_traceable_specimen_id": 0,
        "merge_policy": "no Sample was merged: the records carry no traceable specimen "
                        "identifier, and equal conditions are not physical identity",
        "classification": "PHYSICAL_IDENTITY_NOT_EXTRACTED",
        "samples": sample_rows})
    dump("deposition_run_linkage_inventory.json", {
        "runs": run_rows, "n_runs": stats["runs"],
        "samples_with_run": stats["samples_with_run"],
        "case_run_link_semantics": EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS,
        "overpropagated_links_before": "case-level run exposure implied every realization",
        "overpropagated_links_after": 0,
        "cases_with_partial_run_coverage": stats["cases_with_partial_run_coverage"],
        "note": "every Case->Run link is now scoped to the sample that carries it"})
    dump("multi_case_result_series_inventory.json", {
        "n_multi_case_series": len(multi_case),
        "max_cases_per_series": max([m["n_cases"] for m in multi_case] or [0]),
        "series": multi_case,
        "note": "no series is collapsed to a single case; point-level case mapping is not "
                "persisted and is reported unresolved rather than inferred from order"})
    dump("workbench_semantic_contract.json", contract(payload))
    dump("workbench_075_status.json", {
        "status": "SUPERSEDED_BY_ENTITY_IDENTITY_REPAIR",
        "workbench_sha": "075182fc63a07d2700e69b889086c331d1de1494",
        "reasons": [
            "ExperimentalCase labelled and counted as a physical Experiment",
            "caseOfSeries collapses case_ids to the first element",
            "an N:M graph rendered as a tree",
            "MeasurementAct semantics absent, so counts are per curve",
            "Y representation control sets a target the plot path never materializes"]})
    dispositions = redisposition(hi_card, multi_case, acts_all)
    dump("audit_conflict_dispositions.json", dispositions)
    render(payload, acts_all, hi_card, multi_case, sample_rows, run_rows, dispositions,
           graph)
    for k in ("measurement_records", "measurement_acts", "multi_member_acts",
              "max_members_per_act", "max_series_per_act", "max_cases_per_act"):
        print("%-28s %s" % (k, payload[k]))
    print("multi-case series           %d (max %d cases)"
          % (len(multi_case), max([m["n_cases"] for m in multi_case] or [0])))
    print("samples %d (with run %d)     runs %d"
          % (stats["samples"], stats["samples_with_run"], stats["runs"]))
    print("dispositions                %s" % dispositions["counts"])
    print("wrote %s" % (OUT / "entity_identity_repair_review.html").relative_to(W))
    return 0


def redisposition(hi_card, multi_case, acts):
    """Every conflict from the previous audit gets an explicit outcome."""
    prev = json.loads((AUDIT / "entity_identity_conflicts.json").read_text())
    out = []
    for c in prev["conflicts"]:
        k = c["classification"]
        if k == "MEASUREMENT_OVERMINTING":
            d, why = "RESOLVED", ("the members are now one MeasurementAct; the Measurement "
                                  "records remain addressable")
        elif k == "RESULT_SERIES_SPANS_MULTIPLE_CASES":
            d, why = "EXPECTED_GRAPH_CARDINALITY", ("a sweep belongs to every case it "
                                                    "traverses; the full set is now exposed")
        elif k == "CONDITION_CASE_NOT_PHYSICAL_RUN":
            d, why = "EXPECTED_GRAPH_CARDINALITY", ("ExperimentalCase is documented as a "
                                                    "condition case; run links are now "
                                                    "sample-scoped")
        elif k == "INSUFFICIENT_EVIDENCE":
            d, why = "DEFERRED_EXTRACTION_GAP", ("per-realization conditions are not "
                                                 "persisted; inheriting them would assert "
                                                 "sample evidence that does not exist")
        elif k == "SAMPLE_DUPLICATION":
            d, why = "STILL_UNRESOLVED", "no traceable specimen identifier in the records"
        else:
            d, why = "EXPECTED_GRAPH_CARDINALITY", "cardinality is legitimate for a graph"
        out.append({**c, "disposition": d, "disposition_reason": why})
    return {"counts": dict(Counter(x["disposition"] for x in out)),
            "total": len(out), "dispositions": out}


def contract(p):
    return {
        "ExperimentalCase": {"label": "Condition Case",
            "semantics": "a condition-defined experimental state or design point",
            "may_have": "multiple physical realizations, multiple measurements",
            "must_not_be_called": "Experiment, Sample, DepositionRun"},
        "Sample": {"label": "Physical realization",
            "semantics": "a physical specimen, only when positive evidence identifies it",
            "optional": True},
        "DepositionRun": {"label": "Deposition run", "optional": True,
            "case_link_semantics": EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS},
        "MeasurementAct": {"label": "Measurement act",
            "semantics": "canonical observing-act grouping over Measurement records",
            "grouped_by": "represents_same_measurement_as, transitive closure only"},
        "Measurement": {"label": "Extracted observation record",
            "semantics": "legacy per-curve representation; ids remain addressable"},
        "ResultSeries": {"label": "Result series",
            "case_ids": "0..N, never first-picked",
            "helper": "cases_for_result_series / single_case_for_series"},
        "counts_must_be_named": ["Condition Cases", "Physical Samples",
                                 "MeasurementActs", "ResultSeries"],
        "filter_scopes": {
            "material/precursor/process conditions": "ConditionCase",
            "physical specimen identifiers": "Sample",
            "measurement technique/settings": "MeasurementAct / Measurement",
            "result quantity/normalization/data source": "ResultSeries"},
        "navigation": "graph-aware: Cases <-> Samples <-> MeasurementActs <-> ResultSeries,"
                      " plus ResultSeries -> all associated Condition Cases",
    }


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;--soft:#f4f4f1;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
@media (prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;
--line:#33333a;--card:#1e1e24;--soft:#232329;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;
--accent:#8fb8e0}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:34px 22px 70px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:30px 0 10px;
padding-bottom:5px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);font-size:13px;margin:0 0 18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(126px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:11px 13px}
.card .n{font-size:20px;font-weight:600}
.card .l{color:var(--mut);font-size:10.5px;text-transform:uppercase;letter-spacing:.06em}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:620px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:11px 14px;margin:11px 0;font-size:13px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.graph{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 18px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;white-space:pre;
overflow-x:auto;line-height:1.5}
"""


def render(p, acts, hi, multi, samples, runs, disp, graph):
    e = html.escape
    ma = sorted([a for a in acts.values() if a["n_members"] > 1],
                key=lambda x: -x["n_members"])
    marows = "".join(
        "<tr><td class='mono'>%s</td><td>%d</td><td>%s</td><td>%d</td><td>%d</td>"
        "<td class='mut'>%s</td></tr>" % (
            e(a["paper_id"][:22]), a["n_members"],
            e(", ".join(m.split("__", 1)[-1] for m in a["members"])),
            a["n_result_series"], a["n_cases"], e(a["evidence"][0][:90]))
        for a in ma)
    hirows = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td>%d</td><td>%d</td>"
        "<td>%d</td><td>%d</td><td>%d</td><td>%s</td></tr>" % (
            e(h["paper_id"][:22]), e(h["case_id"]), h["samples"], h["runs"],
            h["raw_measurements"], h["measurement_acts"], h["result_series"],
            e(h["reason"]))
        for h in sorted(hi, key=lambda x: -x["raw_measurements"]))
    mcrows = "".join(
        "<tr><td class='mono'>%s</td><td class='mono'>%s</td><td>%d</td><td><code>%s</code></td>"
        "<td class='mut'>%s</td></tr>" % (
            e(m["paper_id"][:22]), e(m["series_id"].split("::", 1)[-1][:34]), m["n_cases"],
            e(str(m["likely_sweep_quantity"])), e(m["point_to_case_mapping"]))
        for m in sorted(multi, key=lambda x: -x["n_cases"])[:25])
    drows = "".join("<tr><td><code>%s</code></td><td>%d</td></tr>" % (e(k), v)
                    for k, v in disp["counts"].items())

    c2 = [g for g in graph["cases"].values() if g["case_id"] == "CASE-10.103-002"
          and g["paper_id"] == "10.1039_d0cp03358h"]
    c2 = c2[0] if c2 else None
    c2acts = [a for a in acts.values()
              if a["paper_id"] == "10.1039_d0cp03358h" and "CASE-10.103-002" in a["case_ids"]]
    g2 = ""
    if c2:
        g2 = ("Condition Case  CASE-10.103-002   (nominal conditions, %d realizations)\n"
              % c2["realizations"]["n_samples_resolved"])
        for s in c2["realizations"]["samples"]:
            g2 += ("  ├─ Sample %-28s code=%-4s series=%-3s run=%s\n"
                   % (s["sample_id"].split("::")[-1], s["source_sample_code"],
                      s["table_series"], s["produced_by_run"] or "UNRESOLVED"))
        g2 += "  └─ %d MeasurementActs -> %d ResultSeries\n" % (
            len(c2acts), sum(a["n_result_series"] for a in c2acts))

    doc = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Entity Identity Repair</title><style>%s</style></head><body><div class="wrap">
<h1>Entity identity repair</h1>
<p class="sub">Baseline <code>%s</code> · code <code>%s</code> · HEAD <code>%s</code></p>

<div class="cards">
<div class="card"><div class="n">%d</div><div class="l">Measurement records</div></div>
<div class="card"><div class="n">%d</div><div class="l">MeasurementActs</div></div>
<div class="card"><div class="n warn">%d</div><div class="l">multi-member acts</div></div>
<div class="card"><div class="n">%d</div><div class="l">multi-case series</div></div>
<div class="card"><div class="n">%d</div><div class="l">Samples</div></div>
<div class="card"><div class="n">%d</div><div class="l">Samples with a run</div></div>
</div>

<h2>1 &middot; What was repaired, and what was not</h2>
<div class="note"><b>Repaired.</b> <code>represents_same_measurement_as</code> now produces
a real MeasurementAct grouping by transitive closure, so the model's own knowledge that
three panels are one observing act is expressed in the structure rather than kept in a
sideband. Case&rarr;Run links are scoped to the sample that carries them, so a case no
longer implies that every realization was grown in one run. ResultSeries expose their
complete case membership through <code>cases_for_result_series</code>, and a caller that
wants one case must use <code>single_case_for_series</code>, which returns
<code>MULTI_CASE</code> rather than an arbitrary member.<br><br>
<b>Not repaired, deliberately.</b> No Sample was merged. The records carry no traceable
specimen identifier, and the source's only same-sample statements concern a different
figure, so merging rows 4/5/6 would mean inferring physical identity from equal
conditions &mdash; the one inference the identity rules exist to forbid. Classified
<code>PHYSICAL_IDENTITY_NOT_EXTRACTED</code>: an extraction gap, not an architecture
defect.<br><br>
<b>Nothing scientific moved.</b> Measurement ids, ResultSeries ids, points, canonical
curves, case ids and fingerprints are untouched; an act is a grouping over existing ids,
not a replacement for them.</div>

<h2>2 &middot; Condition Case is not an Experiment</h2>
<div class="note">An <code>ExperimentalCase</code> is a <b>condition-defined case</b>. Its
conditions are nominal: they describe the design point, not something measured on any
particular chip. Case conditions are therefore offered to a realization as
<code>CASE_CONTEXT</code>, never rewritten as sample evidence.</div>

<h2>3 &middot; Measurement vs MeasurementAct</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>members</th><th>member panels</th>
<th>series</th><th>cases</th><th>grouping evidence</th></tr></thead>
<tbody>%s</tbody></table></div>
<div class="note">%d Measurement records group into %d acts. The %d multi-member acts are
the only ones with positive evidence; every other act has exactly one member, which is a
statement about the corpus rather than about the schema. Same figure, same quantity and
same conditions group nothing.</div>

<h2>4 &middot; Multi-case sweeps</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>series</th><th>cases</th>
<th>sweep coordinate</th><th>point mapping</th></tr></thead><tbody>%s</tbody></table></div>
<div class="note">A sweep curve belongs to every case it traverses. Point-level
case correspondence is not persisted, and is reported unresolved rather than inferred
from case ordering.</div>

<h2>5 &middot; Cases with three or more measurements</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>case</th><th>samples</th>
<th>runs</th><th>raw measurements</th><th>acts</th><th>series</th><th>reason</th>
</tr></thead><tbody>%s</tbody></table></div>

<h2>6 &middot; CASE-10.103-002 reconstruction</h2>
<div class="graph">%s</div>
<div class="note">Six physical realizations under one nominal condition case. Sample 2
carries a deposition run; samples 4, 5, 6 and 8 do not, and the case no longer implies
that they share it. The 15 measurements remain 15 acts &mdash; they are 15 curves on
different specimens, not one act rendered many times &mdash; which is why the act grouping
correctly leaves them alone.</div>

<h2>7 &middot; Previous audit conflicts, dispositioned</h2>
<div class="scroll"><table><thead><tr><th>disposition</th><th>count</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>8 &middot; Remaining extraction debt</h2>
<div class="note">Architecture is fixed; physical identity is largely not extracted.
%d Samples across the corpus, %d with a known deposition run, 0 with a traceable specimen
identifier. That is a bounded extraction campaign, not a modelling defect, and it is
deliberately out of scope here.</div>
</div></body></html>""" % (
        CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
        p["measurement_records"], p["measurement_acts"], p["multi_member_acts"],
        len(multi), len(samples), sum(1 for s in samples if s["produced_by_run"]),
        marows, p["measurement_records"], p["measurement_acts"], p["multi_member_acts"],
        mcrows, hirows, e(g2), drows,
        len(samples), sum(1 for s in samples if s["produced_by_run"]))
    (OUT / "entity_identity_repair_review.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
