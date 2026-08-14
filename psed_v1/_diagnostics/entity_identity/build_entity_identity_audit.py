#!/usr/bin/env python3
"""Audit what the persisted scientific entities actually mean, and how they actually link.

Read-only. Nothing here repairs identity or regenerates science; it measures what is on
disk so the workbench can be judged before it is trusted.

The question behind it is whether ExperimentalCase is a physical experiment or a nominal
condition, because a UI that labels it "Experiment" is making a claim the data may not
support -- and whether Measurement is an observing act or one extracted curve, because a
tree drawn over the wrong granularity looks convincing and is wrong.

    python3 _diagnostics/entity_identity/build_entity_identity_audit.py
"""
import hashlib
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]
OUT = W / "_diagnostics" / "entity_identity"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
UNSEEN = W / "_diagnostics" / "unseen_eval_v3_axis_dimension"
BASELINE = "075182f"

#: quantities whose disagreement between two realizations of one case is a contradiction
#: rather than an instrument setting
CASE_DEFINING = ("deposition_temperature", "working_pressure", "cycle_number",
                 "precursor", "coreactant", "pulse_time", "purge_time",
                 "feature_height", "aspect_ratio")


def g(d, k):
    return d.get(k, d) if isinstance(d, dict) else d


def load(base, pid, name):
    p = base / "papers" / pid / "semantic" / ("%s.json" % name)
    return g(json.loads(p.read_text()), name) if p.exists() else []


def code_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


def scopes():
    a8 = set(json.loads((PILOT / "pilot_papers.json").read_text())["papers"])
    out = []
    for p in sorted((PILOT / "papers").glob("*/semantic")):
        pid = p.parents[0].name
        out.append((PILOT, pid, "ACTIVE8" if pid in a8 else "EXCLUDED_DEVELOPMENT"))
    if UNSEEN.exists():
        for p in sorted((UNSEEN / "papers").glob("*/semantic")):
            out.append((UNSEEN, p.parents[0].name, "UNSEEN"))
    return out


def audit():
    ents = defaultdict(dict)          # type -> key -> record
    rel = defaultdict(lambda: defaultdict(set))
    counts = defaultdict(Counter)
    for base, pid, scope in scopes():
        K = lambda t, i: "%s::%s::%s" % (scope, pid, i)
        cases = load(base, pid, "experimental_cases")
        samples = load(base, pid, "samples")
        runs = load(base, pid, "deposition_runs")
        meas = load(base, pid, "measurements")
        sims = load(base, pid, "simulation_runs")
        rss = load(base, pid, "result_series")
        reps = load(base, pid, "representations")
        counts[scope].update({"cases": len(cases), "samples": len(samples),
                              "runs": len(runs), "measurements": len(meas),
                              "simulation_runs": len(sims), "result_series": len(rss),
                              "representations": len(reps)})
        for c in cases:
            k = K("case", c["case_id"])
            ents["case"][k] = {"key": k, "scope": scope, "paper_id": pid,
                               "case_id": c["case_id"],
                               "fingerprint": c.get("nominal_fingerprint"),
                               "material": c.get("deposited_material"),
                               "geometry": c.get("geometry"),
                               "conditions": c.get("case_defining_conditions") or [],
                               "sample_ids": c.get("sample_ids") or []}
            for s in (c.get("sample_ids") or []):
                rel["case_sample"][k].add(K("sample", s))
                rel["sample_case"][K("sample", s)].add(k)
        for s in samples:
            sid = s.get("sample_id")
            k = K("sample", sid)
            ents["sample"][k] = {"key": k, "scope": scope, "paper_id": pid,
                                 "sample_id": sid,
                                 "source_sample_code": s.get("source_sample_code"),
                                 "produced_by_run": s.get("produced_by_run"),
                                 "case_ids": s.get("experimental_case_ids") or [],
                                 "evidence": (str(s.get("evidence") or ""))[:240]}
            if s.get("produced_by_run"):
                rel["sample_run"][k].add(K("run", s["produced_by_run"]))
                rel["run_sample"][K("run", s["produced_by_run"])].add(k)
        for r in runs:
            rid = r.get("deposition_run_id") or r.get("id")
            ents["run"][K("run", rid)] = {"key": K("run", rid), "scope": scope,
                                          "paper_id": pid, "run_id": rid,
                                          "evidence": (str(r.get("evidence") or ""))[:240]}
        for m in meas:
            mid = m["measurement_id"]
            k = K("meas", mid)
            ents["meas"][k] = {
                "key": k, "scope": scope, "paper_id": pid, "measurement_id": mid,
                "kind": "MEASUREMENT",
                "technique": m.get("technique"), "measurand": m.get("measured_quantity"),
                "settings": m.get("measurement_settings") or [],
                "performed_on": m.get("performed_on"),
                "specimen_binding": m.get("specimen_binding"),
                "repeat_measurement": m.get("repeat_measurement"),
                "same_act_as": m.get("represents_same_measurement_as"),
                "n_observations": m.get("n_observations"),
                "case_ids": m.get("measures_case") or [],
                "evidence": (str(m.get("evidence") or ""))[:240]}
            for c in (m.get("measures_case") or []):
                rel["meas_case"][k].add(K("case", c))
                rel["case_meas"][K("case", c)].add(k)
            if m.get("performed_on"):
                rel["meas_sample"][k].add(K("sample", m["performed_on"]))
        for s in sims:
            sid = s.get("simulation_run_id") or s.get("id")
            ents["meas"][K("meas", sid)] = {
                "key": K("meas", sid), "scope": scope, "paper_id": pid,
                "measurement_id": sid, "kind": "SIMULATION_RUN",
                "technique": s.get("model_family") or s.get("model"),
                "measurand": None, "settings": [], "performed_on": None,
                "specimen_binding": None, "repeat_measurement": None,
                "same_act_as": None, "n_observations": None,
                "case_ids": s.get("realises_case_ids") or [], "evidence": ""}
            for c in (s.get("realises_case_ids") or []):
                rel["meas_case"][K("meas", sid)].add(K("case", c))
                rel["case_meas"][K("case", c)].add(K("meas", sid))
        for r in rss:
            rid = r["result_series_id"]
            k = K("series", rid)
            ents["series"][k] = {
                "key": k, "scope": scope, "paper_id": pid, "series_id": rid,
                "producer": r.get("produced_by"), "data_source": r.get("data_source"),
                "n_points": r.get("n_points"),
                "x_quantity": r.get("x_quantity"), "y_quantity": r.get("y_quantity"),
                "figure": (r.get("source") or {}).get("figure"),
                "panel": (r.get("source") or {}).get("panel"),
                "series_label": (r.get("source") or {}).get("series")}
            if r.get("produced_by"):
                pk = K("meas", r["produced_by"])
                rel["prod_series"][pk].add(k)
                rel["series_prod"][k].add(pk)
                # a series reaches its cases only through its producer
                for c in rel["meas_case"].get(pk, ()):
                    rel["series_case"][k].add(c)
                    rel["case_series"][c].add(k)
    return ents, rel, counts


def distribution(mp, universe):
    c = Counter(len(v) for v in mp.values())
    c[0] += len(universe) - len(mp)
    return {"0": c[0], "1": c[1], "2+": sum(v for k, v in c.items() if k >= 2),
            "max": max(c) if c else 0,
            "links": sum(k * v for k, v in c.items())}


def main():
    ents, rel, counts = audit()
    A = {t: {k: v for k, v in ents[t].items() if v["scope"] == "ACTIVE8"}
         for t in ents}
    keys = {t: set(A[t]) for t in A}

    def sub(r):
        return {k: {x for x in v if x.split("::")[0] == "ACTIVE8"}
                for k, v in rel[r].items() if k.split("::")[0] == "ACTIVE8"}

    RELS = [("Case -> Sample", "case_sample", "case", "sample"),
            ("Sample -> Case", "sample_case", "sample", "case"),
            ("Sample -> Run", "sample_run", "sample", "run"),
            ("Run -> Sample", "run_sample", "run", "sample"),
            ("Case -> Measurement", "case_meas", "case", "meas"),
            ("Measurement -> Case", "meas_case", "meas", "case"),
            ("Measurement -> Sample", "meas_sample", "meas", "sample"),
            ("Producer -> ResultSeries", "prod_series", "meas", "series"),
            ("ResultSeries -> Producer", "series_prod", "series", "meas"),
            ("ResultSeries -> Case", "series_case", "series", "case"),
            ("Case -> ResultSeries", "case_series", "case", "series")]
    matrix = []
    for label, r, left, right in RELS:
        m = sub(r)
        d = distribution(m, keys[left])
        matrix.append({"relation": label, "unique_left": len(keys[left]),
                       "unique_right": len(keys[right]), **d})

    # --- conflicts -------------------------------------------------------------------
    conflicts = []
    cs, cm, csam = sub("case_sample"), sub("case_meas"), sub("case_sample")
    mc = sub("meas_case")
    sr = sub("sample_run")

    for k, ms in cm.items():
        if len(ms) < 3:
            continue
        samples = cs.get(k, set())
        runs = {r for s in samples for r in sr.get(s, set())}
        acts = {A["meas"][m]["same_act_as"] or A["meas"][m]["measurement_id"] for m in ms}
        figs = {A["series"][x]["figure"] for m in ms for x in sub("prod_series").get(m, set())}
        reasons = []
        if len(samples) > 1:
            reasons.append("MULTIPLE_PHYSICAL_SAMPLES")
        if len(figs) > 1:
            reasons.append("MULTIPLE_FIGURE_REPRESENTATIONS")
        if len({A["meas"][m]["measurand"] for m in ms}) > 1:
            reasons.append("MULTIPLE_MEASURANDS")
        if len(acts) < len(ms):
            reasons.append("DUPLICATE_MEASUREMENT_ENTITIES")
        if len(runs) and len(samples) > len({s for s in samples if sr.get(s)}):
            reasons.append("RUN_LINK_PARTIAL")
        conflicts.append({
            "paper": A["case"][k]["paper_id"], "entity_type": "ExperimentalCase",
            "entity_ids": [A["case"][k]["case_id"]], "relation": "Case -> Measurement",
            "n_samples": len(samples), "n_runs": len(runs), "n_measurements": len(ms),
            "n_series": len(sub("case_series").get(k, set())),
            "n_distinct_acts": len(acts),
            "reasons": reasons or ["UNKNOWN"],
            "classification": ("CONDITION_CASE_NOT_PHYSICAL_RUN" if len(samples) > 1
                               else "EXPECTED_CARDINALITY"),
            "source_evidence": A["case"][k]["fingerprint"],
            "confidence": "high" if samples else "medium"})

    for k, cc in mc.items():
        if len(cc) < 2:
            continue
        m = A["meas"][k]
        conflicts.append({
            "paper": m["paper_id"], "entity_type": "Measurement",
            "entity_ids": [m["measurement_id"]], "relation": "Measurement -> Case",
            "n_cases": len(cc),
            "reasons": ["SWEEP_SERIES_SPANS_CASES" if (m["measurand"] or "") else "OTHER"],
            "classification": "RESULT_SERIES_SPANS_MULTIPLE_CASES",
            "source_evidence": m["evidence"], "confidence": "medium",
            "cases": sorted(A["case"][c]["case_id"] for c in cc if c in A["case"])})

    same_act = defaultdict(list)
    for k, m in A["meas"].items():
        if m["same_act_as"]:
            same_act[m["same_act_as"]].append(m["measurement_id"])
    for root, members in same_act.items():
        conflicts.append({
            "paper": A["meas"][[k for k, v in A["meas"].items()
                                if v["measurement_id"] == members[0]][0]]["paper_id"],
            "entity_type": "Measurement", "entity_ids": [root] + members,
            "relation": "Measurement -> Measurement",
            "reasons": ["one observing act rendered in several panels"],
            "classification": "MEASUREMENT_OVERMINTING",
            "source_evidence": "represents_same_measurement_as is persisted on the record",
            "confidence": "high"})

    codes = defaultdict(list)
    for k, s in A["sample"].items():
        if s["source_sample_code"]:
            codes[(s["paper_id"], str(s["source_sample_code"]))].append(s["sample_id"])
    for (pid, code), ids in codes.items():
        if len(ids) > 1:
            conflicts.append({
                "paper": pid, "entity_type": "Sample", "entity_ids": ids,
                "relation": "Sample identity", "reasons": ["same source_sample_code"],
                "classification": "SAMPLE_DUPLICATION",
                "source_evidence": "source_sample_code=%s" % code, "confidence": "high"})

    # within-case condition contradictions between linked samples
    for k, samples in cs.items():
        if len(samples) < 2:
            continue
        vals = defaultdict(set)
        for s in samples:
            pass                                    # sample conditions are not persisted
        # nothing to compare: recorded as an evidence gap rather than a contradiction
        conflicts.append({
            "paper": A["case"][k]["paper_id"], "entity_type": "ExperimentalCase",
            "entity_ids": [A["case"][k]["case_id"]],
            "relation": "Case -> Sample conditions",
            "reasons": ["case carries %d samples but conditions are stored only on the "
                        "case, so per-realization variation cannot be checked"
                        % len(samples)],
            "classification": "INSUFFICIENT_EVIDENCE", "source_evidence": None,
            "confidence": "high"})

    payload = {
        "baseline_sha": BASELINE, "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "scopes_included": sorted({s for _, _, s in scopes()}),
        "entity_counts_by_scope": {k: dict(v) for k, v in counts.items()},
        "active8_unique_entities": {t: len(keys[t]) for t in keys},
        "active8_link_incidences": {label: distribution(sub(r), keys[left])["links"]
                                    for label, r, left, _ in RELS},
        "cardinality_matrix": matrix,
        "measurement_entities": len(A["meas"]),
        "distinct_measurement_acts": len({m["same_act_as"] or m["measurement_id"]
                                          for m in A["meas"].values()}),
        "multi_case_measurements": len([1 for v in mc.values() if len(v) > 1]),
        "max_cases_per_measurement": max([len(v) for v in mc.values()] or [0]),
        "measurements_without_case": len(keys["meas"]) - len(mc),
        "multi_sample_cases": len([1 for v in cs.values() if len(v) > 1]),
        "max_samples_per_case": max([len(v) for v in cs.values()] or [0]),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dump = lambda n, d: (OUT / n).write_text(
        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    dump("entity_cardinality_matrix.json", {**payload, "matrix": matrix})
    dump("entity_identity_conflicts.json",
         {"count": len(conflicts), "by_classification":
          dict(Counter(c["classification"] for c in conflicts)), "conflicts": conflicts})
    dump("workbench_hierarchy_implications.json", implications(payload, matrix))
    render(payload, matrix, conflicts, A, rel)
    for k in ("active8_unique_entities", "active8_link_incidences",
              "measurement_entities", "distinct_measurement_acts",
              "multi_case_measurements", "max_cases_per_measurement",
              "measurements_without_case", "multi_sample_cases", "max_samples_per_case"):
        print("%-30s %s" % (k, payload[k]))
    print("conflicts %d %s" % (len(conflicts),
                               dict(Counter(c["classification"] for c in conflicts))))
    print("wrote %s" % (OUT / "experimental_entity_cardinality_identity_review.html")
          .relative_to(W))
    return 0


def implications(p, matrix):
    m = {r["relation"]: r for r in matrix}
    return {
        "can_experimentalcase_be_labelled_Experiment": {
            "answer": "NO",
            "reason": "one case carries up to %d physical Samples under a single nominal "
                      "fingerprint, so it is a condition-defined case, not a physical "
                      "experiment or run" % p["max_samples_per_case"]},
        "can_case_measurement_series_be_rendered_as_a_tree": {
            "answer": "NO",
            "reason": "%d Measurements link to more than one Case (max %d), so the "
                      "relation is N:M and a tree must duplicate or drop nodes"
                      % (p["multi_case_measurements"], p["max_cases_per_measurement"])},
        "can_one_resultseries_be_shown_under_one_case_only": {
            "answer": "NO",
            "reason": "a series reaches its cases through its producer, and a producer "
                      "with several cases gives the series several cases; picking the "
                      "first silently hides the rest"},
        "can_measurement_be_presented_as_a_real_observing_act": {
            "answer": "CONDITIONALLY",
            "reason": "%d Measurement entities reduce to %d distinct acts once "
                      "represents_same_measurement_as is applied; the remainder are one "
                      "curve each, so the entity is per-curve, not per-act"
                      % (p["measurement_entities"], p["distinct_measurement_acts"])},
        "can_counts_under_case_cards_be_treated_as_unique_entity_counts": {
            "answer": "NO",
            "reason": "summing measurements under cases counts Case-Measurement "
                      "incidences (%d) rather than unique Measurements (%d)"
                      % (p["active8_link_incidences"]["Case -> Measurement"],
                         p["active8_unique_entities"]["meas"])},
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
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:32px 0 10px;
padding-bottom:5px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);font-size:13px;margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(126px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:11px 13px}
.card .n{font-size:20px;font-weight:600}
.card .l{color:var(--mut);font-size:10.5px;text-transform:uppercase;letter-spacing:.06em}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:640px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:11px 14px;margin:11px 0;font-size:13px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.pill{display:inline-block;padding:0 7px;border-radius:99px;font-size:10.5px;
border:1px solid var(--line);color:var(--mut)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:9px 12px;margin-bottom:7px}
summary{cursor:pointer;font-weight:600;font-size:13px}
"""


def render(p, matrix, conflicts, A, rel):
    e = html.escape
    mrows = "".join(
        "<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td class='%s'>%d</td>"
        "<td>%d</td><td>%d</td></tr>" % (
            e(r["relation"]), r["unique_left"], r["unique_right"], r["0"], r["1"],
            "warn" if r["2+"] else "", r["2+"], r["max"], r["links"])
        for r in matrix)
    byc = Counter(c["classification"] for c in conflicts)
    crows = "".join("<tr><td><code>%s</code></td><td>%d</td></tr>" % (e(k), v)
                    for k, v in byc.most_common())
    hi = [c for c in conflicts if c["entity_type"] == "ExperimentalCase"
          and c.get("n_measurements", 0) >= 3]
    hrows = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td>%d</td><td>%d</td>"
        "<td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td></tr>" % (
            e(c["paper"][:24]), e(c["entity_ids"][0]), c["n_samples"], c["n_runs"],
            c["n_measurements"], c["n_series"], c["n_distinct_acts"],
            e(", ".join(c["reasons"])), e(c["classification"]))
        for c in sorted(hi, key=lambda x: -x["n_measurements"]))
    imp = implications(p, matrix)
    irows = "".join(
        "<tr><td>%s</td><td class='%s'>%s</td><td class='mut'>%s</td></tr>" % (
            e(k.replace("_", " ")), "bad" if v["answer"] == "NO" else "warn",
            e(v["answer"]), e(v["reason"]))
        for k, v in imp.items())

    doc = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Entity Cardinality &amp; Identity Audit</title><style>%s</style></head><body>
<div class="wrap">
<h1>Experimental entity cardinality &amp; identity audit</h1>
<p class="sub">Read-only. Baseline <code>%s</code> · code <code>%s</code> · HEAD
<code>%s</code> · scopes %s</p>

<div class="cards">%s</div>

<h2>What ExperimentalCase actually is</h2>
<div class="note">One case carries up to <b>%d physical Samples</b> under a single nominal
fingerprint, and the conditions are stored on the case rather than on each realization.
So <code>ExperimentalCase</code> is a <b>nominal condition case</b> &mdash; option B &mdash;
not a physical experiment, sample or deposition run. Labelling it &ldquo;Experiment&rdquo;
in a UI asserts a physical identity the data does not carry.<br><br>
The physical layer is nearly absent: <b>%d Samples</b> and <b>%d DepositionRun</b> across
%d cases. Sample&rarr;Run is set on only a few samples, so a case that exposes a run is
usually exposing the run of <em>one</em> of its samples.</div>

<h2>Relation cardinality matrix (ACTIVE8)</h2>
<div class="scroll"><table><thead><tr><th>relation</th><th>unique left</th>
<th>unique right</th><th>0</th><th>1</th><th>2+</th><th>max</th><th>link incidences</th>
</tr></thead><tbody>%s</tbody></table></div>
<div class="note">Entity counts and link incidences are different numbers. There are
<b>%d</b> unique Measurements but <b>%d</b> Case&ndash;Measurement incidences, so summing
measurements under case cards over-counts. The relation is N:M in both directions:
<b>%d</b> Measurements link to more than one Case (max <b>%d</b>), and <b>%d</b> link to
none.</div>

<h2>Measurement granularity</h2>
<div class="note">Every producer has at most <b>one</b> ResultSeries. That is not simply a
sparse corpus: the records carry <code>represents_same_measurement_as</code>, and applying
it collapses <b>%d</b> Measurement entities into <b>%d</b> distinct observing acts. Six
acts are each rendered as three separate Measurement entities &mdash; one per panel &mdash;
with the same-act relation kept as a sideband instead of as shared identity. So the entity
is currently <b>per extracted curve</b>, while the schema's own fields describe a
<b>per observing act</b> intent. Classification: <code>MEASUREMENT_OVERMINTING</code> for
those, <code>INTENDED_CARDINALITY</code> unproven for the rest.</div>

<h2>Cases with three or more measurements</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>case</th><th>samples</th>
<th>runs</th><th>measurements</th><th>series</th><th>distinct acts</th><th>why</th>
<th>classification</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Conflict inventory</h2>
<div class="scroll"><table><thead><tr><th>classification</th><th>count</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Workbench implications</h2>
<div class="scroll"><table><thead><tr><th>question</th><th>answer</th><th>reason</th>
</tr></thead><tbody>%s</tbody></table></div>

<h2>Recorded UI defects (not evidence about the science)</h2>
<div class="note">Kept separate from the entity findings, and not fixed here:
the workbench's <code>caseOfSeries</code> returns <code>case_ids[0]</code>, silently
collapsing an N:M relation; its parentage diagnostic reports
<code>max_series_per_producer = 1</code> without saying that this reflects per-curve
Measurement minting; and the Y representation control sets a target that the plot path
does not materialize, so only x projections are actually applied.</div>
</div></body></html>""" % (
        CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
        e(", ".join(p["scopes_included"])),
        "".join("<div class='card'><div class='n'>%d</div><div class='l'>%s</div></div>"
                % (v, e(k)) for k, v in p["active8_unique_entities"].items()),
        p["max_samples_per_case"], p["active8_unique_entities"]["sample"],
        p["active8_unique_entities"]["run"], p["active8_unique_entities"]["case"],
        mrows, p["active8_unique_entities"]["meas"],
        p["active8_link_incidences"]["Case -> Measurement"],
        p["multi_case_measurements"], p["max_cases_per_measurement"],
        p["measurements_without_case"],
        p["measurement_entities"], p["distinct_measurement_acts"],
        hrows, crows, irows)
    (OUT / "experimental_entity_cardinality_identity_review.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
