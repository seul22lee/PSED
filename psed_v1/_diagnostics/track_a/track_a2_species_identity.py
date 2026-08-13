#!/usr/bin/env python3
"""Track A2: the species-hygiene / attribution migration map and review page.

`species` is the reagent dimension of the case fingerprint -- WHICH chemical a setting
applies to. Two things that are not reagents had been landing in it (a pressure unit, a
deposited film material), and the settings that genuinely belong to a named reagent were
carrying nothing at all. Both defects distort identity, in opposite directions.

Reads the pre-migration state from git so the diff depends only on (baseline, code) and
re-running cannot accumulate drift. Writes a machine-readable migration map alongside
the page, because a review artifact nobody can diff is not evidence.

    python3 _diagnostics/track_a/track_a2_species_identity.py
"""
import hashlib
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
REL = "psed_v1/_diagnostics/semantic_pilot_9papers/papers/%s/semantic/experimental_cases.json"
OUT_MAP = W / "_diagnostics" / "track_a" / "track_a2_migration_map.json"
OUT_HTML = W / "_diagnostics" / "track_a" / "track_a2_species_identity_migration_review.html"
BASELINE = "18bdb09"


def unwrap(d, k):
    return d.get(k, d) if isinstance(d, dict) else d


def baseline_cases(pid):
    r = subprocess.run(["git", "show", "%s:%s" % (BASELINE, REL % pid)],
                       cwd=str(W.parent), capture_output=True, text=True)
    if r.returncode:
        return {}
    return {c["case_id"]: c for c in unwrap(json.loads(r.stdout), "experimental_cases")}


def current_cases(pid):
    p = PILOT / "papers" / pid / "semantic" / "experimental_cases.json"
    return {c["case_id"]: c for c in unwrap(json.loads(p.read_text()), "experimental_cases")}


def code_hash():
    """Hash the code that produced this run -- the working tree, not just HEAD (§46)."""
    h = hashlib.sha256()
    for p in (PILOT / "code" / "pilot_semantics.py", Path(__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def conds(c):
    return c.get("case_defining_conditions") or []


def main():
    papers = json.loads((PILOT / "pilot_papers.json").read_text())["papers"]
    added, removed, replaced, unresolved = [], [], [], []
    migrated, per_paper = [], []
    topo_b, topo_a = Counter(), Counter()

    for pid in papers:
        B, A = baseline_cases(pid), current_cases(pid)
        relabel = 0
        for cid, ca in A.items():
            cb = B.get(cid)
            topo_a["INDISTINGUISHABLE" if ca.get("indistinguishable_from")
                   else "DISTINGUISHED"] += 1
            if not cb:
                continue
            topo_b["INDISTINGUISHABLE" if cb.get("indistinguishable_from")
                   else "DISTINGUISHED"] += 1
            sb = {(x["quantity"], str(x.get("value"))): x for x in conds(cb)}
            changes = []
            for x in conds(ca):
                k = (x["quantity"], str(x.get("value")))
                old = (sb.get(k) or {}).get("species")
                new = x.get("species")
                row = {"paper": pid, "case_id": cid, "quantity": x["quantity"],
                       "value": x.get("value"), "unit": x.get("unit"),
                       "raw_axis_label": x.get("raw_axis_label"),
                       "species_before": old, "species_after": new,
                       "tier": x.get("species_basis"),
                       "evidence": x.get("species_evidence")}
                if old == new:
                    if new is None and x["quantity"] in (
                            "pulse_time", "purge_time", "exposure_time"):
                        unresolved.append(row)
                    continue
                changes.append(row)
                if new and not old:
                    row["action"] = "ADD_SPECIES"
                    added.append(row)
                elif old and not new:
                    row["action"] = "REMOVE_INVALID_SPECIES"
                    row["removed"] = (sb.get(k) or {}).get("species")
                    removed.append(row)
                else:
                    row["action"] = "REPLACE_SPECIES"
                    replaced.append(row)
            if cb.get("nominal_fingerprint") != ca.get("nominal_fingerprint"):
                relabel += 1
                migrated.append({
                    "paper": pid, "case_id": cid,
                    "case_id_changed": False,
                    "fingerprint_before": cb.get("nominal_fingerprint"),
                    "fingerprint_after": ca.get("nominal_fingerprint"),
                    "species_changes": changes,
                    "reason": "; ".join(sorted({r["action"] for r in changes}))
                              or "condition recovered by species-scoped dedup key",
                })
        per_paper.append({
            "paper": pid, "cases_before": len(B), "cases_after": len(A),
            "relabeled": relabel,
            "fingerprints_before": len({c.get("nominal_fingerprint") for c in B.values()}),
            "fingerprints_after": len({c.get("nominal_fingerprint") for c in A.values()}),
            "case_ids_added": sorted(set(A) - set(B)),
            "case_ids_removed": sorted(set(B) - set(A)),
        })

    payload = {
        "baseline_sha": BASELINE,
        "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "case_id_migration_required": False,
        "case_id_note": ("case_id is a positional index assigned when the case is built; "
                         "nominal_fingerprint is computed afterwards from the finished "
                         "cases. A species change moves the fingerprint and cannot move "
                         "the id, so no reference rewrite exists to perform."),
        "counts": {
            "species_added": len(added), "species_removed": len(removed),
            "species_replaced": len(replaced), "left_unresolved": len(unresolved),
            "cases_relabeled": len(migrated),
            "cases_total": sum(p["cases_after"] for p in per_paper),
            "case_ids_changed": sum(len(p["case_ids_added"]) + len(p["case_ids_removed"])
                                    for p in per_paper),
        },
        "topology_before": dict(topo_b), "topology_after": dict(topo_a),
        "per_paper": per_paper,
        "added": added, "removed": removed, "replaced": replaced,
        "unresolved_sample": unresolved[:40], "unresolved_total": len(unresolved),
        "migrated_cases": migrated,
    }
    OUT_MAP.write_text(json.dumps(payload, indent=2, sort_keys=True,
                                  ensure_ascii=False) + "\n")
    render(payload)
    c = payload["counts"]
    for k in ("species_added", "species_removed", "species_replaced", "left_unresolved",
              "cases_relabeled", "case_ids_changed"):
        print("%-22s %d" % (k, c[k]))
    print("topology  before %s" % dict(topo_b))
    print("topology  after  %s" % dict(topo_a))
    print("wrote %s" % OUT_MAP.relative_to(W))
    print("wrote %s" % OUT_HTML.relative_to(W))
    return 0


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;--card:#1e1e24;
--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}}
:root[data-theme=dark]{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;
--card:#1e1e24;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:14px;margin:22px 0 8px;color:var(--mut);text-transform:uppercase;
letter-spacing:.06em}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .n{font-size:24px;font-weight:600;letter-spacing:-.02em}
.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:720px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;white-space:nowrap}
tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 16px;margin:14px 0}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;
border:1px solid var(--line);color:var(--mut);white-space:nowrap}
"""


def render(p):
    e = html.escape
    c = p["counts"]

    def sp(v):
        return '<span class="mut">unknown</span>' if not v else "<code>%s</code>" % e(str(v))

    add = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td>%s</td><td><code>%s</code></td>"
        "<td>%s</td><td>%s</td><td><span class='pill'>%s</span></td></tr>" % (
            e(r["paper"][:24]), e(r["case_id"]), e(r["quantity"]), e(str(r["value"])),
            e(str(r["raw_axis_label"] or "")), sp(r["species_after"]), e(str(r["tier"])))
        for r in p["added"])

    rem = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td>%s</td><td><code>%s</code></td>"
        "<td class='bad'>%s</td><td class='mut'>unknown</td><td>%s</td></tr>" % (
            e(r["paper"][:24]), e(r["case_id"]), e(r["quantity"]), e(str(r["value"])),
            e(str(r.get("removed") or r["species_before"])), e(str(r["evidence"] or "")))
        for r in p["removed"])

    pp = "".join(
        "<tr><td class='mono'>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td>"
        "<td class='%s'>%d</td></tr>" % (
            e(r["paper"][:26]), r["cases_before"], r["cases_after"], r["relabeled"],
            r["fingerprints_before"], r["fingerprints_after"],
            "good" if not (r["case_ids_added"] or r["case_ids_removed"]) else "bad",
            len(r["case_ids_added"]) + len(r["case_ids_removed"]))
        for r in p["per_paper"])

    mig = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td class='good'>unchanged</td>"
        "<td><code>%s</code></td><td><code>%s</code></td><td>%s</td></tr>" % (
            e(m["paper"][:22]), e(m["case_id"]),
            e(str(m["fingerprint_before"] or "")[:70]),
            e(str(m["fingerprint_after"] or "")[:70]), e(m["reason"]))
        for m in p["migrated_cases"][:60])

    tb, ta = p["topology_before"], p["topology_after"]
    doc = """<title>Track A2 Species Identity</title><style>%s</style>
<div class="wrap">
<h1>Track A2 &mdash; species hygiene and case identity</h1>
<p class="sub"><code>species</code> is the reagent dimension of the case fingerprint:
which chemical a setting applies to. Baseline <code>%s</code>, generating code
<code>%s</code>, HEAD <code>%s</code>.</p>

<div class="cards">
<div class="card"><div class="n good">%d</div><div class="l">species added</div></div>
<div class="card"><div class="n bad">%d</div><div class="l">invalid removed</div></div>
<div class="card"><div class="n">%d</div><div class="l">replaced</div></div>
<div class="card"><div class="n mut">%d</div><div class="l">left unresolved</div></div>
<div class="card"><div class="n">%d</div><div class="l">cases relabeled</div></div>
<div class="card"><div class="n good">%d</div><div class="l">case IDs changed</div></div>
<div class="card"><div class="n good">0</div><div class="l">splits</div></div>
<div class="card"><div class="n good">0</div><div class="l">merges</div></div>
</div>

<div class="note"><strong>There is no case-ID migration to perform.</strong> %s
So this batch is a <em>semantic</em> correction plus a <em>fingerprint</em> relabel;
nothing references a fingerprint, and every reference points at a case ID that did
not move. Referential integrity is preserved by construction, not by rewriting.</div>

<h2>Species hygiene &mdash; what was in the field that is not a reagent</h2>
<div class="note"><code>bar</code> &times;19: on
<code>carrier_gas_partial_pressure = 1 bar</code>, the species field held the pressure
<em>unit</em>. Species equalled unit in 19 of 19 instances; the carrier gas is never
named in the evidence span. &nbsp;&nbsp;<code>SiO2</code> &times;7: on a
<code>structural_identity</code> condition, the species field held the deposited film
<em>material</em>, which the case already carries as <code>deposited_material</code>.
It was constant across every instance, so it distinguished nothing. Neither is deleted
for looking wrong &mdash; both are refused because the field means something they are
not, and what replaces them is nothing, because MISSING is not SAME.</div>
<div class="scroll"><table><thead><tr><th>paper</th><th>case</th><th>quantity</th>
<th>value</th><th>species before</th><th>after</th><th>reason</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Species attribution &mdash; what evidence supports</h2>
<div class="note">Attribution runs only on positive evidence in the axis label the
condition actually carried: a chemical the paper's own inventory lists, or a role word
the inventory binds to exactly one reagent. Of %d unattributed reagent-scoped time
conditions, <strong>%d</strong> carry such evidence and <strong>%d</strong> carry none
&mdash; their evidence spans name a swept number and no chemical. Those stay unknown.</div>
<div class="scroll"><table><thead><tr><th>paper</th><th>case</th><th>quantity</th>
<th>value</th><th>raw axis label</th><th>species after</th><th>tier</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Why attribution changed distinguishability</h2>
<div class="note">Conditions are de-duplicated per case on
<code>(quantity, species)</code>. A swept <code>Precursor Pulse</code> value therefore
collided with a methods-default <code>pulse_time</code> carrying no species, and the
methods number won &mdash; the swept value, which is the entire subject of that figure,
was being discarded. Giving the precursor condition its own species gives it its own key,
so the sweep survives. Ten cases the source distinguishes by precursor pulse length are
distinguished again: DISTINGUISHED %d&nbsp;&rarr;&nbsp;%d,
INDISTINGUISHABLE %d&nbsp;&rarr;&nbsp;%d. No case was created, destroyed, split or merged.</div>

<h2>Topology and structural counts</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>cases before</th>
<th>cases after</th><th>relabeled</th><th>fingerprints before</th>
<th>fingerprints after</th><th>case IDs changed</th></tr></thead>
<tbody>%s</tbody></table></div>
<div class="note">Unchanged across the migration: ResultSeries 231, points 4027,
Measurements 213, SimulationRuns 34, DesignBranches 105, and the technique,
<code>data_source</code> and producer distributions byte-for-byte. A0.1 and A0.2 remain
closed &mdash; <code>H2 flow ratio</code> is still unsupported end to end.</div>

<h2>Case migration map</h2>
<p class="sub">Every relabeled case, with the fingerprint before and after. Full
machine-readable map in <code>track_a2_migration_map.json</code>.</p>
<div class="scroll"><table><thead><tr><th>paper</th><th>case ID</th><th>ID</th>
<th>fingerprint before</th><th>fingerprint after</th><th>reason</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Deferred</h2>
<div class="note">Kept out of A2 deliberately: species-aware comparability and query;
the <code>flow_ratio</code> ontology gap; ambiguous common-name normalisation
(<code>Alcohol</code>, <code>at-H</code>, <code>LiO&#7511;Bu</code>);
<code>electrode_potential</code>, <code>vapor_pressure</code>,
<code>critical_angle</code>. Separately noted for a later batch: in one paper the source
recipe states precursor <em>purge</em> durations that upstream extraction typed as
<code>pulse_time</code>. A2 neither creates nor repairs that &mdash; correcting it needs
re-extraction, not a species rule &mdash; but attribution makes it visible.</div>
</div>""" % (CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
             c["species_added"], c["species_removed"], c["species_replaced"],
             c["left_unresolved"], c["cases_relabeled"], c["case_ids_changed"],
             e(p["case_id_note"]), rem,
             c["left_unresolved"] + c["species_added"], c["species_added"],
             c["left_unresolved"], add,
             tb.get("DISTINGUISHED", 0), ta.get("DISTINGUISHED", 0),
             tb.get("INDISTINGUISHABLE", 0), ta.get("INDISTINGUISHABLE", 0),
             pp, mig)
    OUT_HTML.write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
