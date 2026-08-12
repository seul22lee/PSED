#!/usr/bin/env python3
"""
build_report.py — the human-review HTML for the four-paper semantic pilot.

    python3 code/build_report.py

Self-contained: one file, no server, no external asset. Page renders recovered from the
PDFs are inlined as data URIs so the report stays a single portable file.
"""
import base64
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]
OUT = W / "report" / "index.html"

TITLES = {}


def sem(pid, name):
    f = W / "papers" / pid / "semantic" / ("%s.json" % name)
    return json.loads(f.read_text()) if f.exists() else []


def e(x):
    return html.escape(str(x if x is not None else ""))


def data_uri(path):
    try:
        b = Path(path).read_bytes()
    except Exception:
        return None
    return "data:image/png;base64," + base64.b64encode(b).decode()


CSS = """
:root{--bg:#f6f7f9;--fg:#15181d;--mut:#5d6673;--line:#dde2e9;--card:#fff;--accent:#0f7c8a;
 --exp:#0f7c3f;--sim:#8a4b0f;--warn:#a8410f;--unres:#7a5c00;--chip:#eef2f6}
@media(prefers-color-scheme:dark){:root{--bg:#111419;--fg:#e7ebf1;--mut:#98a3b3;--line:#2a313b;
 --card:#181c23;--accent:#4fc3d1;--exp:#57c98b;--sim:#e0a267;--warn:#f0906a;--unres:#e2c760;--chip:#212831}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,BlinkMacSystemFont,
 "Segoe UI",Roboto,sans-serif;font-variant-numeric:tabular-nums}
.wrap{max-width:1220px;margin:0 auto;padding:28px 20px 90px}
h1{font-family:Georgia,serif;font-size:28px;margin:0 0 4px}
h2{font-family:Georgia,serif;font-size:21px;margin:38px 0 10px;border-bottom:2px solid var(--accent);padding-bottom:6px}
h3{font-size:15px;margin:24px 0 8px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.sub{color:var(--mut);max-width:88ch}
a{color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
th{background:var(--chip);font-weight:600}
td.num,th.num{text-align:right}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 15px;
 min-width:210px;flex:1 1 240px;text-decoration:none;color:inherit;display:block}
.card:hover{border-color:var(--accent)}
.card b{display:block;font-size:15px;font-family:Georgia,serif;margin-bottom:6px}
.card .doi{font-size:11.5px;color:var(--mut);word-break:break-all;margin-bottom:8px}
.kv{display:grid;grid-template-columns:1fr auto;gap:1px 8px;font-size:12px}
.kv span{color:var(--mut)}.kv b{font-weight:700;font-size:12px;display:inline}
.tag{display:inline-block;padding:1px 7px;border-radius:20px;font-size:11px;font-weight:600;
 border:1px solid var(--line);background:var(--chip)}
.EXPLICIT{color:var(--exp);border-color:var(--exp)}
.SUPPORTED{color:var(--accent);border-color:var(--accent)}
.UNRESOLVED{color:var(--unres);border-color:var(--unres)}
.sim{color:var(--sim);border-color:var(--sim)}
.exp{color:var(--exp);border-color:var(--exp)}
.warn{color:var(--warn);border-color:var(--warn)}
details{border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin:5px 0;background:var(--card)}
details>summary{cursor:pointer;font-size:12.5px;color:var(--mut)}
details[open]>summary{margin-bottom:6px}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px}
.scroll{overflow-x:auto;max-width:100%}
.q{font-size:12px;color:var(--mut);font-style:italic;border-left:3px solid var(--line);
 padding-left:9px;margin:4px 0}
.tree{list-style:none;padding-left:16px;margin:4px 0;border-left:1px dashed var(--line)}
.tree li{margin:2px 0;font-size:12.5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.hint{color:var(--mut);font-size:12.5px;margin:2px 0 8px}
img.page{max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:6px}
.bar{height:7px;border-radius:4px;background:var(--chip);overflow:hidden;margin-top:3px}
.bar i{display:block;height:100%;background:var(--accent)}
.kind-range{color:#0f7c8a;border-color:#0f7c8a;font-weight:700}
.kind-approx{color:var(--mut)}
.prov{opacity:.7;font-weight:400}
.cand{color:var(--unres);border-color:var(--unres)}
.ref{color:var(--sim);border-color:var(--sim)}
.chk .P{color:var(--exp);font-weight:700}.chk .F{color:var(--warn);font-weight:700}
.chain{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:12.5px;margin:5px 0}
.chain b{background:var(--chip);border:1px solid var(--line);border-radius:6px;padding:2px 8px;font-weight:600}
.chain i{color:var(--mut);font-style:normal}
.stop{color:var(--unres);border:1px dashed var(--unres);border-radius:6px;padding:2px 8px}
"""


#: how a value was arrived at — never flattened into one visual kind
_KIND_TAG = {"range": ("range", "kind-range"), "approximate": ("approx", "kind-approx"),
             "scalar": ("", "")}
_PROV_TAG = {"directly_stated": "stated", "directly_stated_range": "stated range",
             "derived_from_sweep_axis": "from sweep axis",
             "methods_default": "methods default",
             "inherited_from_explicit_sample": "inherited from specimen"}


def fmt_value(c):
    if c.get("value_kind") == "range":
        return "%s&ndash;%s %s" % (e(c.get("value_lower")), e(c.get("value_upper")),
                                   e(c.get("unit") or ""))
    if c.get("value_status") == "REJECTED_UNPHYSICAL":
        return "unresolved"
    v = c.get("value")
    if v is None:
        return "unresolved"
    pre = "~" if c.get("value_kind") == "approximate" else ""
    return "%s%s %s" % (pre, e(v), e(c.get("unit") or ""))


def conds_cell(conds, limit=8):
    """One condition per line, with its VALUE KIND and its PROVENANCE both visible.

    A stated scalar, an inherited default, a value read off a sweep axis and a stated
    interval are four different epistemic states, and flattening them into one number is
    how "10-120 ms" became "-120 ms" without anyone noticing."""
    if not conds:
        return '<span class="tag UNRESOLVED">none known</span>'
    out = []
    for c in conds[:limit]:
        prov = c.get("provenance_type") or ""
        kind_lbl, kind_cls = _KIND_TAG.get(c.get("value_kind") or "scalar", ("", ""))
        bits = ['<code>%s = %s</code>' % (e(c.get("quantity")), fmt_value(c))]
        if kind_lbl:
            bits.append('<span class="tag %s">%s</span>' % (kind_cls, e(kind_lbl)))
        bits.append('<span class="tag prov">%s</span>'
                    % e(_PROV_TAG.get(prov, prov.replace("_", " "))))
        if c.get("value_status") == "REJECTED_UNPHYSICAL":
            bits.append('<span class="tag warn" title="%s">rejected %s</span>'
                        % (e(c.get("value_repair")), e(c.get("superseded_value"))))
        elif c.get("value_repair"):
            bits.append('<span class="tag warn" title="%s">repaired from %s</span>'
                        % (e(c.get("value_repair")), e(c.get("superseded_value"))))
        out.append("<div>%s</div>" % " ".join(bits))
    if len(conds) > limit:
        out.append('<div class="hint">+%d more</div>' % (len(conds) - limit))
    return "".join(out)


def evidence_block(o, ids, label="evidence"):
    ev = {x["evidence_id"]: x for x in o["evidence"]}
    rows = []
    for i in (ids or []):
        r = ev.get(i)
        if not r:
            continue
        extra = {k: v for k, v in r.items()
                 if k not in ("evidence_id", "kind", "subject", "detail")}
        rows.append("<tr><td class=mono>%s</td><td>%s</td><td>%s%s</td></tr>"
                    % (e(r["evidence_id"]), e(r["kind"].replace("_", " ")), e(r["detail"])[:600],
                       ('<div class="hint mono">%s</div>' % e(json.dumps(extra)[:300]))
                       if extra else ""))
    if not rows:
        return ""
    return ('<details><summary>%s (%d)</summary><div class="scroll"><table>'
            '<tr><th>id</th><th>kind</th><th>what the source says</th></tr>%s'
            '</table></div></details>' % (label, len(rows), "".join(rows)))


def ground_truth_checks(checks, pid):
    """The PDF-ground-truth anchors for one paper, as the test run reported them."""
    rows = [c for c in checks if c["paper"] == pid]
    if not rows:
        return ""
    npass = sum(1 for r in rows if r["pass"])
    h = ['<h3>PDF-ground-truth checks &mdash; %d / %d pass</h3>' % (npass, len(rows))]
    h.append('<p class="hint">Read from the original PDF, not from the pilot output. A '
             'failure here means the pilot disagrees with the paper.</p>')
    h.append('<div class="scroll"><table class="chk"><tr><th>check</th><th>result</th>'
             '<th>detail</th></tr>')
    for r in rows:
        h.append("<tr><td>%s</td><td class='%s'>%s</td><td class='hint mono'>%s</td></tr>"
                 % (e(r["name"]), "P" if r["pass"] else "F",
                    "PASS" if r["pass"] else "FAIL", e(r["detail"])[:200]))
    h.append("</table></div>")
    return "\n".join(h)


def material_cell(c):
    """Local materials, their roles, and WHERE the assignment came from.

    A material proposed only by the paper-wide inventory is shown as a candidate, so
    leakage is visible at a glance instead of reading as an assertion."""
    bits = []
    for m, role in sorted((c.get("material_roles") or {}).items()):
        bits.append('<span class="tag exp">%s: %s</span>' % (e(m), e(role)))
    for m, role in sorted((c.get("material_candidates") or {}).items()):
        bits.append('<span class="tag cand" title="paper-wide inventory only; '
                    'not asserted for this result">%s: %s (candidate)</span>'
                    % (e(m), e(role)))
    if not bits:
        bits.append('<span class="tag UNRESOLVED">unresolved</span>')
    src = c.get("material_evidence_scope") or "none"
    bits.append('<div class="hint">source: %s</div>' % e(src))
    if c.get("material_status") and c["material_status"] != "ASSERTED":
        bits.append('<div class="hint">%s</div>' % e(c.get("material_status_reason")))
    return " ".join(bits)


def paper_section(pid, o, cmp_, checks=None):
    ms = {m["measurement_id"]: m for m in o["measurements"]}
    cases = o["experimental_cases"]
    samples = {s["sample_id"]: s for s in o["samples"]}
    h = ['<h2 id="%s">%s</h2>' % (e(pid), e(pid))]
    old, new = cmp_["current_psed"], cmp_["pilot"]
    h.append('<div class="cards">')
    for lab, a, b in (("Experiments &rarr; ExperimentalCases", old["experiments"],
                       new["experimental_cases"]),
                      ("Measurements", "&mdash;", new["measurements"]),
                      ("ResultSeries", old["canonical_curves"], new["result_series"]),
                      ("Representations", "&mdash;", new["representations"]),
                      ("Samples", old["physical_case_ids"], new["samples"]),
                      ("identified DepositionRuns", 0, new["identified_deposition_runs"]),
                      ("run-evidence groups", 0, new["run_evidence_groups"]),
                      ("SimulationRuns", old["simulation_entities"] + old["model_sweep_entities"],
                       new["simulation_runs"]),
                      ("Unresolved links", "&mdash;", new["unresolved_links"])):
        h.append('<div class="card"><b>%s &rarr; %s</b><span class="doi">%s</span></div>'
                 % (a, b, lab))
    h.append("</div>")
    h.append(ground_truth_checks(checks or [], pid))

    # ---- case-centric ----
    h.append("<h3>ExperimentalCase view &mdash; one row per scientifically distinct case</h3>")
    h.append('<div class="scroll"><table><tr><th>Case</th><th>Deposited material</th>'
             '<th>Geometry</th><th>Case-defining conditions</th><th>Run</th><th>Sample</th>'
             '<th>Measurements</th><th>Source figures</th><th>Link confidence</th>'
             '<th>Warnings</th></tr>')
    for c in cases:
        mrows = []
        for mid in c["measurement_ids"]:
            m = ms.get(mid)
            if not m:
                continue
            mrows.append("<div>%s <span class='tag'>Fig %s%s</span></div>"
                         % (e(", ".join(m["technique"]) or "—"),
                            e(m["source"]["printed_figure"]), e(m["source"]["panel"])))
        roles = material_cell(c)
        h.append("<tr id='%s'><td class=mono>%s%s</td><td>%s</td><td>%s<div class='hint'>%s</div></td>"
                 "<td>%s</td><td class=mono>%s</td><td class=mono>%s</td><td>%s</td>"
                 "<td class=mono>%s</td><td><span class='tag %s'>%s</span></td><td>%s</td></tr>"
                 % (e(c["case_id"]), e(c["case_id"]),
                    ("<div class='hint'>%s</div>" % e(c["label"])) if c.get("label") else "",
                    roles,
                    e(c["geometry"] or "—"), e(c.get("geometry_source") or ""),
                    conds_cell(c["case_defining_conditions"]),
                    e(", ".join(c["deposition_run_ids"]) or "—"),
                    e(", ".join(x.split("::")[-1] for x in c["sample_ids"]) or "—"),
                    "".join(mrows) or "—",
                    e(", ".join(c["source_panels"]) or "—"),
                    e(c["confidence"]), e(c["confidence"]),
                    "".join("<div class='tag warn'>%s</div>" % e(x) for x in c["warnings"]) or ""))
        h.append("<tr><td colspan=10>%s</td></tr>"
                 % evidence_block(o, c["identity_evidence"], "identity evidence"))
    h.append("</table></div>")

    # ---- figure/panel-centric ----
    h.append("<h3>Figure &rarr; panel view &mdash; what each printed panel became</h3>")
    by_fig = defaultdict(list)
    for m in o["measurements"]:
        by_fig[str(m["source"]["printed_figure"] or "?")].append(("MEAS", m))
    for s in o["simulation_runs"]:
        by_fig[str(s["source"]["printed_figure"] or "?")].append(("SIM", s))
    reps = defaultdict(list)
    for r in o["representations"]:
        reps[(str(r["source"]["printed_figure"]), r["source"]["panel"])].append(r)
    case_of_meas = defaultdict(list)
    for c in cases:
        for mid in c["measurement_ids"]:
            case_of_meas[mid].append(c["case_id"])
    for fig in sorted(by_fig, key=lambda x: (len(x), x)):
        items = sorted(by_fig[fig], key=lambda t: (t[1]["source"]["panel"] or ""))
        h.append("<h3 style='color:var(--fg);text-transform:none;font-family:Georgia,serif;"
                 "font-size:16px;letter-spacing:0'>Figure %s</h3>" % e(fig))
        h.append('<div class="scroll"><table><tr><th>Panel</th><th>Kind</th><th>What it is</th>'
                 '<th>Measurement / SimulationRun</th><th>ResultSeries</th>'
                 '<th>ExperimentalCase(s)</th><th>Sample(s)</th><th>Representation</th>'
                 '<th>Source</th></tr>')
        for kind, it in items:
            pan = it["source"]["panel"] or "—"
            rr = reps.get((fig, it["source"]["panel"]), [])
            if kind == "SIM":
                h.append("<tr><td class=mono>%s</td><td><span class='tag sim'>SIMULATION</span></td>"
                         "<td>%s</td><td class=mono>%s</td><td class=mono>%d series</td>"
                         "<td><span class='tag sim'>never a case</span></td><td>—</td>"
                         "<td>%s</td><td><span class='tag sim'>%s</span></td></tr>"
                         % (e(pan), e((it.get("model_statement") or "model output")[:150]),
                            e(it["simulation_run_id"]), len(it["result_series_ids"]),
                            " ".join('<span class="tag">%s</span>' % e(r["type"]) for r in rr),
                            e(", ".join(it["data_source"]) or "simulated")))
                continue
            samp = set()
            if it.get("performed_on"):
                samp.add(it["performed_on"].split("::")[-1])
            h.append("<tr><td class=mono>%s</td><td><span class='tag exp'>%s</span></td>"
                     "<td>%s%s</td><td class=mono>%s</td><td class=mono>%s</td>"
                     "<td class=mono>%s</td><td class=mono>%s</td><td>%s</td>"
                     "<td>%s</td></tr>"
                     % (e(pan),
                        "CAPTION ONLY" if it.get("data_recovered") is False else "MEASUREMENT",
                        e(", ".join(it["technique"]) or "—"),
                        "<div class='q'>%s</div>" % e(it["caption_reference"][:220])
                        if it.get("caption_reference") else "",
                        e(it["measurement_id"]),
                        ("%d" % len(it["result_series_ids"])) if it["result_series_ids"]
                        else "<span class='tag UNRESOLVED'>no data</span>",
                        e(", ".join(case_of_meas.get(it["measurement_id"], []))
                          or "UNRESOLVED"),
                        e(", ".join(sorted(samp)) or "—"),
                        " ".join('<span class="tag">%s</span>' % e(r["type"]) for r in rr),
                        e("measured" if it["result_series_ids"] else
                          (it.get("recovery_cause") or "—"))))
        h.append("</table></div>")

    # ---- representation view ----
    grouped = defaultdict(list)
    for r in o["representations"]:
        if r.get("derived_representation_of"):
            grouped[r["derived_representation_of"]].append(r)
    if grouped:
        h.append("<h3>Representation view &mdash; redrawn views of one measurement</h3>")
        h.append('<p class="hint">Each block is ONE underlying measurement. The panels below '
                 'it are views of that measurement; none of them creates an ExperimentalCase.</p>')
        for holder, rs in sorted(grouped.items()):
            m = ms.get(holder)
            h.append('<details open><summary><code>%s</code> &mdash; %s &nbsp; '
                     '<span class="tag exp">%d representations, 0 extra cases</span></summary>'
                     % (e(holder), e(", ".join(m["technique"]) if m else ""), len(rs)))
            h.append("<ul class=tree>")
            for r in sorted(rs, key=lambda x: x["source"]["panel"] or ""):
                h.append("<li>Fig %s(%s) &nbsp;<span class='tag'>%s</span> &nbsp;"
                         "<span class=mono>%s</span></li>"
                         % (e(r["source"]["printed_figure"]), e(r["source"]["panel"]),
                            e(r["type"]), e(r["representation_id"])))
            h.append("</ul></details>")

    # ---- sample / run view ----
    if o["samples"] or o["deposition_runs"]:
        h.append("<h3>Sample and DepositionRun view</h3>")
        h.append('<p class="hint"><b>%d identified deposition run(s)</b> &mdash; an actual '
                 'process execution with named specimens. Separately, <b>%d '
                 'run-distinctness assertion(s)</b>: the source says several runs exist '
                 'but names none of them, so they are NOT DepositionRun instances and are '
                 'not counted as runs.</p>'
                 % (len(o["deposition_runs"]), len(o.get("run_evidence") or [])))
        h.append('<div class="grid2"><div>')
        h.append("<h3 style='margin-top:4px'>Identified deposition runs</h3>")
        for r in o["deposition_runs"]:
            h.append('<details open><summary><code>%s</code> <span class="tag %s">%s</span>'
                     '</summary>' % (e(r["run_id"]), e(r["confidence"]), e(r["kind"])))
            h.append('<div class="q">%s</div>'
                     % e(r.get("same_run_evidence") or r.get("different_run_evidence") or ""))
            if r["sample_codes"]:
                h.append("<ul class=tree>")
                for c in r["sample_codes"]:
                    h.append("<li>Sample %s</li>" % e(c))
                h.append("</ul>")
            elif r.get("note"):
                h.append('<div class="hint">%s</div>' % e(r["note"]))
            h.append("</details>")
        if not o["deposition_runs"]:
            h.append('<p class="hint">none &mdash; no statement in this paper identifies a '
                     'specific process execution.</p>')
        for r in (o.get("run_evidence") or []):
            h.append('<details><summary><span class="tag UNRESOLVED">RUN-DISTINCTNESS '
                     'EVIDENCE</span> &nbsp;<code>%s</code></summary>' % e(r["run_id"]))
            h.append('<div class="q">%s</div>'
                     % e(r.get("different_run_evidence") or r.get("same_run_evidence") or ""))
            h.append('<div class="hint">%s</div>'
                     % e(r.get("note") or "an assertion about runs, not a run instance"))
            h.append("</details>")
        h.append("</div><div>")
        for s in sorted(o["samples"], key=lambda x: (len(x["source_sample_code"]),
                                                     x["source_sample_code"])):
            if not s["measurement_ids"]:
                continue
            h.append('<details><summary>Sample <b>%s</b> &nbsp;<span class="tag %s">%s</span>'
                     '&nbsp;<span class="tag">%d measurements</span></summary>'
                     % (e(s["source_sample_code"]), e(s["confidence"]), e(s["confidence"]),
                        len(s["measurement_ids"])))
            h.append("<ul class=tree>")
            for mid in s["measurement_ids"]:
                m = ms.get(mid)
                if m:
                    h.append("<li>%s &nbsp;<span class='tag'>Fig %s%s</span></li>"
                             % (e(", ".join(m["technique"]) or "—"),
                                e(m["source"]["printed_figure"]), e(m["source"]["panel"])))
            h.append("</ul>")
            if s.get("case_defining_conditions"):
                h.append("<div class='hint'>%s</div>"
                         % " &nbsp; ".join("<code>%s = %s %s</code>"
                                           % (e(c["quantity"]), e(c["value"]), e(c["unit"] or ""))
                                           for c in s["case_defining_conditions"]))
            h.append(evidence_block(o, [x for x in s["evidence"]], "specimen evidence"))
            h.append("</details>")
        h.append("</div></div>")

    # ---- series view ----
    if o["study_series"]:
        h.append("<h3>Study series view &mdash; author-declared groupings (many-to-many)</h3>")
        h.append('<div class="scroll"><table><tr><th>Series</th><th>Varied variable</th>'
                 '<th>Role</th><th>Where the variable comes from</th>'
                 '<th>Co-varying context</th><th>Member samples</th><th>Member cases</th>'
                 '</tr>')
        multi = Counter()
        for s in o["study_series"]:
            for c in s["member_sample_codes"]:
                multi[c] += 1
        for s in o["study_series"]:
            mem = " ".join('<span class="tag%s">%s</span>'
                           % (" SUPPORTED" if multi[c] > 1 else "", e(c))
                           for c in s["member_sample_codes"])
            cov = " ".join('<span class="tag cand">%s: %s</span>'
                           % (e(c["quantity"]), e(", ".join(c["values"])[:40]))
                           for c in (s.get("co_varying_context") or [])) or "—"
            h.append("<tr><td><b>%s</b></td><td class=mono>%s</td>"
                     "<td><span class='tag %s'>%s</span></td>"
                     "<td><span class='tag %s'>%s</span><div class='hint'>%s</div></td>"
                     "<td>%s</td><td>%s</td><td class=mono>%s</td></tr>"
                     % (e(s["author_series_name"]), e(s["varied_variable"] or "—"),
                        "UNRESOLVED" if s["varied_variable_role"] == "UNRESOLVED" else "",
                        e(s["varied_variable_role"]),
                        "exp" if s.get("varied_variable_source") == "author_declaration" else "",
                        e((s.get("varied_variable_source") or "").replace("_", " ")),
                        e((s["purpose"] or "")[:160]), cov, mem,
                        e(", ".join(s["member_case_ids"]) or "—")))
        h.append("</table></div>")
        if any(v > 1 for v in multi.values()):
            h.append('<p class="hint">Highlighted specimens belong to more than one series &mdash; '
                     'membership is many-to-many: %s</p>'
                     % e(", ".join("sample %s (%d series)" % (k, v)
                                   for k, v in sorted(multi.items()) if v > 1)))

    # ---- provenance chains ----
    if o.get("provenance_chains"):
        h.append("<h3>Characterisation provenance chain</h3>")
        h.append('<p class="hint">A measured result is attributed to a deposition case only '
                 'when the source states that the material that case PRODUCED was placed on '
                 'the thing that was measured. Where the chain stops, it is shown stopping.</p>')
        for ch in o["provenance_chains"]:
            h.append('<div class="chain"><b>%s</b><i>&rarr;</i><b>%s %s</b><i>&rarr;</i>'
                     '<b>%s</b><i>&rarr;</i>%s</div>'
                     % (e(", ".join(ch["case_ids"]) or "?"),
                        e(ch.get("qualifier") or ""), e("%s %s" % (ch["product_material"],
                                                                  ch["product_form"])),
                        e(ch["device"]),
                        ('<b>measurements of figure %s</b>' % e(", ".join(ch.get("covers_figures") or []))
                         if ch["status"] == "RESOLVED" else
                         '<span class="stop">chain stops: %s</span>' % e(ch.get("reason")))))
            h.append('<div class="q">%s</div>' % e(ch["statement"]))
        refs = [m for m in o["measurements"] if m.get("provenance_role") == "REFERENCE"]
        if refs:
            h.append('<p class="hint">Comparison controls, never attributed to a deposition '
                     'case:</p>')
            for m in refs:
                h.append('<div class="chain"><span class="tag ref">REFERENCE</span>'
                         '<b>Fig %s%s &mdash; %s</b><i>%s</i></div>'
                         % (e(m["source"]["printed_figure"]), e(m["source"]["panel"]),
                            e(m["source"].get("source_series") or ", ".join(m["technique"])),
                            e(m.get("provenance_note") or "")))
        stops = [m for m in o["measurements"] if m.get("provenance_role") == "CASE_UNRESOLVED"]
        if stops:
            h.append('<p class="hint">Measured, but the producing case is not identified by '
                     'the source:</p>')
            for m in stops:
                h.append('<div class="chain"><b>Fig %s%s</b><i>&rarr;</i>'
                         '<span class="stop">%s</span></div>'
                         % (e(m["source"]["printed_figure"]), e(m["source"]["panel"]),
                            e(m.get("provenance_note"))))

    # ---- unresolved ----
    if o["unresolved"]:
        h.append("<h3>Unresolved links &mdash; merges the evidence did not support</h3>")
        h.append('<p class="hint">An unresolved link is the intended outcome when the source '
                 'does not state identity. Missing information is never treated as sameness.</p>')
        h.append('<div class="scroll"><table><tr><th>Reason class</th><th>What</th>'
                 '<th>Why it is unresolved</th></tr>')
        for u in o["unresolved"][:40]:
            what = (u.get("measurement_id") or "%s &harr; %s (Fig %s vs %s)"
                    % (u.get("a"), u.get("b"), u.get("a_figure"), u.get("b_figure")))
            h.append("<tr><td><span class='tag UNRESOLVED'>%s</span></td><td class=mono>%s</td>"
                     "<td>%s</td></tr>"
                     % (e(u.get("reason_class", "CONDITION_ONLY_NO_POSITIVE_LINK")),
                        what, e(u.get("reason"))))
        h.append("</table></div>")
        if len(o["unresolved"]) > 40:
            h.append('<p class="hint">showing 40 of %d</p>' % len(o["unresolved"]))

    # ---- recovered evidence ----
    sup = [m for m in o["measurements"] if m.get("data_recovered") is False]
    if sup:
        h.append("<h3>Recovered source evidence &mdash; panels the extraction stage never reached</h3>")
        for m in sup:
            h.append('<details><summary>Fig %s(%s) &mdash; <span class="tag warn">%s</span> '
                     '%s</summary>'
                     % (e(m["source"]["printed_figure"]), e(m["source"]["panel"]),
                        e(m.get("recovery_cause")), e(", ".join(m["technique"]))))
            h.append('<div class="q">%s</div>' % e(m["caption_reference"]))
            h.append('<div class="hint">%s</div>' % e(m.get("recovery_detail")))
            if m.get("page_render"):
                uri = data_uri(W / "papers" / m["paper_id"] / "diagnostics" / "assets"
                               / m["page_render"])
                if uri:
                    h.append('<img class="page" src="%s" alt="PDF page carrying figure %s">'
                             % (uri, e(m["source"]["printed_figure"])))
            h.append("</details>")

    # ---- old vs pilot ----
    h.append("<h3>Current PSED vs pilot &mdash; semantic changes</h3>")
    h.append('<p class="hint">Counts are diagnostic only. A smaller number is not automatically '
             'better semantics; what matters is which change class it belongs to.</p>')
    h.append('<div class="scroll"><table><tr><th>Change class</th><th class=num>n</th>'
             '<th>What it means here</th><th>Examples</th></tr>')
    for ch in cmp_["changes"]:
        h.append("<tr><td><span class='tag'>%s</span></td><td class=num>%d</td><td>%s</td>"
                 "<td class='mono hint'>%s</td></tr>"
                 % (e(ch["class"]), ch["n"], e(ch["detail"]),
                    e(json.dumps(ch["examples"])[:420])))
    h.append("</table></div>")
    return "\n".join(h)


def run_checks():
    """The PDF-ground-truth anchors, taken from an actual run of the test suite.

    Reporting a stored verdict would let the page claim a pass the tests no longer give,
    so the suite is executed and its machine-readable ANCHOR lines are parsed. Those lines
    carry the paper id, which is why no module here needs to name a paper."""
    try:
        out = subprocess.run([sys.executable, str(W / "tests" / "test_pilot_semantics.py")],
                             capture_output=True, text=True, timeout=600).stdout
    except Exception as exc:
        return [], "the test suite could not be run: %s" % exc
    rows = []
    for line in out.splitlines():
        if not line.startswith("ANCHOR\t"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        _, pid, verdict, name = parts[:4]
        rows.append({"paper": pid, "name": name,
                     "detail": parts[4] if len(parts) > 4 else "",
                     "pass": verdict == "PASS"})
    return rows, None


def main():
    checks, check_err = run_checks()
    cmp_all = json.loads((W / "comparison" / "old_vs_pilot.json").read_text())
    inv = json.loads((W / "comparison" / "semantic_invariants.json").read_text())
    h = ['<title>Four-Paper Semantic Pilot</title><style>%s</style><div class="wrap">' % CSS]
    h.append("<h1>Four-Paper Semantic Pilot</h1>")
    h.append('<p class="sub">A sandboxed test of the revised PSED experimental semantics on '
             'four papers. Production is untouched: everything here was built from a read-only '
             'snapshot, with no API calls and no pipeline stage re-run. '
             '<b>ExperimentalCase</b> is a scientifically distinguishable deposition case; '
             'figures, panels, curves, plot representations and measurement settings never '
             'define one.</p>')

    h.append('<div class="cards">')
    for pid in PAPERS:
        c = cmp_all[pid]
        o = {k: sem(pid, k) for k in ("experimental_cases", "measurements", "samples",
                                      "deposition_runs", "representations",
                                      "simulation_runs", "unresolved")}
        h.append('<a class="card" href="#%s"><b>%s</b><span class="doi">%s</span>'
                 '<div class="kv">' % (e(pid), e(pid.split("_", 1)[-1][:26]), e(pid)))
        for lab, v in (("current PSED Experiments", c["current_psed"]["experiments"]),
                       ("pilot ExperimentalCases", len(o["experimental_cases"])),
                       ("Measurements", len(o["measurements"])),
                       ("Samples", len(o["samples"])),
                       ("identified DepositionRuns", len(o["deposition_runs"])),
                       ("run-evidence groups", len(sem(pid, "run_evidence"))),
                       ("Representations", len(o["representations"])),
                       ("SimulationRuns", len(o["simulation_runs"])),
                       ("unresolved links", len(o["unresolved"]))):
            h.append("<span>%s</span><b>%d</b>" % (e(lab), v))
        h.append("</div></a>")
    h.append("</div>")

    # invariant strip
    if checks:
        npass = sum(1 for c in checks if c["pass"])
        h.append('<p class="sub"><b>PDF-ground-truth checks: %d / %d pass.</b> Each paper\'s '
                 'own checks are shown in its section below.</p>' % (npass, len(checks)))
    elif check_err:
        h.append('<p class="sub warn">%s</p>' % e(check_err))
    h.append("<h2>Invariants</h2>")
    h.append('<div class="scroll"><table><tr><th>Paper</th><th>source curves</th>'
             '<th>points</th><th>measured/simulated</th><th>swept cases carrying their value</th>'
             '<th>samples w/o evidence</th><th>runs w/o evidence</th>'
             '<th>merges w/o evidence</th><th>simulation as case</th></tr>')
    for pid in PAPERS:
        v = inv[pid]
        sc, pt = v["source_curves_preserved"], v["points_preserved"]
        sw = v["sweep_cases_carry_their_value"]
        h.append("<tr><td class=mono>%s</td><td>%d &rarr; %d %s</td><td>%d &rarr; %d %s</td>"
                 "<td>%s</td><td>%d / %d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>"
                 % (e(pid), sc["old"], sc["pilot"],
                    "&#10003;" if not sc["missing"] else "&#10007;",
                    pt["old"], pt["pilot"], "&#10003;" if pt["pilot"] >= pt["old"] else "&#10007;",
                    "&#10003; identical" if v["data_source_unchanged"]["old"]
                    == v["data_source_unchanged"]["pilot"] else "&#10007;",
                    sw["with_value"], sw["n"],
                    v["samples_only_with_evidence"]["without_evidence"],
                    v["runs_only_with_evidence"]["without_evidence"],
                    v["every_merge_has_evidence"]["without_evidence"],
                    v["simulation_never_a_case"]["simulation_runs_marked_as_case"]))
    h.append("</table></div>")

    for pid in PAPERS:
        o = {k: sem(pid, k) for k in ("experimental_cases", "measurements", "result_series",
                                      "representations", "samples", "deposition_runs",
                                      "study_series", "simulation_runs", "links",
                                      "evidence", "unresolved", "run_evidence",
                                      "provenance_chains")}
        h.append(paper_section(pid, o, cmp_all[pid], checks))

    h.append('<p class="hint" style="margin-top:40px">Generated by '
             '<code>code/build_report.py</code> from the pilot workspace. '
             'No production file was read for writing and no API was called.</p>')
    h.append("</div>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(h), encoding="utf-8")
    print("wrote %s (%.0f KB)" % (OUT, OUT.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
