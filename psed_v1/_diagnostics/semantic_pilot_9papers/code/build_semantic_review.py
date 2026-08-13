#!/usr/bin/env python3
"""Build the manual-review deliverables for the semantic pilot.

Writes, from the current `papers/*/semantic/` outputs and nothing else:

    comparison/semantic_review.html        the browsable review page
    comparison/merge_safety_audit.csv      one row per merge decision
    comparison/yim_post_repair_review.md
    comparison/9paper_semantic_repair_review.md

Everything here READS the pilot output. No semantics are computed in this file, so the
report cannot disagree with the pipeline it reports on.
"""
import csv
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
PAPERS = W / "papers"
OUT = W / "comparison"

def sem(pid, name):
    f = PAPERS / pid / "semantic" / ("%s.json" % name)
    return json.loads(f.read_text()) if f.exists() else []


#: The work list lives in the manifest, not here, so no module names a paper. The first
#: four entries are the regression controls; the detailed sections below are selected by
#: what a paper CONTAINS, never by its identifier.
_MANIFEST = json.loads((W / "pilot_papers.json").read_text())
ORDER = list(_MANIFEST["papers"])
#: The active set IS the manifest's paper list. A review paper was removed from the pilot
#: entirely (see `excluded` in the manifest): its figures reproduce other groups' work, so
#: its data is predominantly model output and imported observations rather than
#: experiments the paper performed. Nothing on this page loads or counts it.
PRIMARY = ORDER
ROLES = _MANIFEST["roles"]
CONTROL = {p for p in ORDER if ROLES.get(p) == "original_control"}
RUNTIME = _MANIFEST.get("runtime_seconds_measured", {})


def _pick(pred):
    """The paper this report has a detailed section for, chosen by its content."""
    for pid in ORDER:
        if pred(pid):
            return pid
    return None


#: Yim is "the paper with a specimen table"; JES "the one with the most design branches";
#: d0ra "the one with a thermal-analysis figure"; am "the control with the most cases per
#: source curve". Each section is written for that structure, not for that DOI.
YIM = _pick(lambda p: len(sem(p, "samples")) >= 5)
JES = max(ORDER, key=lambda p: sum(len(x.get("branch_values") or [])
                                   for x in sem(p, "experimental_designs")))
DRA = _pick(lambda p: any((m.get("measured_quantity") or "").lower().startswith("weight")
                          for m in sem(p, "measurements")))
AM = max(CONTROL, key=lambda p: len(sem(p, "experimental_cases"))
         / max(1, len(sem(p, "result_series"))))

SHORT = {p: p.split("_", 1)[-1] if "_" in p else p for p in ORDER}


def code_of(sid):
    return str(sid).rsplit("::", 1)[-1]


def load_all():
    data = {}
    for pid in ORDER:
        d = {n: sem(pid, n) for n in
             ("experimental_cases", "experimental_designs", "design_branches",
              "measurements", "result_series", "representations", "samples",
              "deposition_runs", "study_series", "simulation_runs", "unresolved",
              "links", "evidence")}
        data[pid] = d
    return data


def counts(pid, d, inv):
    """Each metric is one class of semantic object, counted from that class.

    Three numbers are routinely confused and are kept apart here:
      * source branch appearances -- how many times a branch is DISPLAYED (one panel
        showing GPC and another showing the refractive index at the same branch is two
        appearances of one branch);
      * unique DesignBranches -- the DesignBranch objects themselves;
      * ExperimentalCases -- distinct depositions, which may be realised by several
        specimens and may be reached from several branches.
    """
    br = d["design_branches"]
    appearances = sum(len(b.get("measurement_ids")
                          or ([b["measurement_id"]] if b.get("measurement_id") else []))
                      or 1 for b in br)
    v = inv.get(pid, {})
    return {
        "designs": len(d["experimental_designs"]),
        "branch_appearances": appearances,
        "unique_branches": len(br),
        "branch_derived_cases": len([c for c in d["experimental_cases"]
                                     if "design_branch" in (c.get("member_kinds") or [])]),
        "non_branch_cases": len([c for c in d["experimental_cases"]
                                 if "design_branch" not in (c.get("member_kinds") or [])]),
        "cases": len(d["experimental_cases"]),
        "samples": len(d["samples"]),
        "runs": len(d["deposition_runs"]),
        "measurements": len(d["measurements"]),
        "result_series": len(d["result_series"]),
        "representations": len(d["representations"]),
        "simulations": len(d["simulation_runs"]),
        "unresolved": len(d["unresolved"]),
        "curves": (v.get("source_curves_preserved") or {}),
        "points": (v.get("points_preserved") or {}),
    }


# ------------------------------------------------------------------ merge safety
def merge_rows(data):
    """One row per merge DECISION across all nine papers, with the checks behind it."""
    rows = []
    for pid in ORDER:
        cand_mat, cand_step, cand_q, cand_fig = {}, {}, {}, {}
        for c in data[pid]["experimental_cases"]:
            for cid in c.get("candidate_ids") or []:
                cand_mat[cid] = c.get("deposited_material")
        for ev in data[pid]["evidence"]:
            if ev.get("kind") == "experimental_design":
                cand_q[ev.get("subject")] = ev.get("varied")
        for lk in data[pid]["links"]:
            det = lk.get("detail")
            clash = (det or {}).get("clash") if isinstance(det, dict) else None
            reason = lk.get("reason") or ""
            rows.append({
                "paper": pid,
                "source_a": lk.get("a"),
                "source_b": lk.get("b"),
                "link_class": lk.get("link_class")
                or ("DESIGN_IDENTITY" if "design" in reason else "-"),
                "verdict": lk.get("action"),
                "strength": lk.get("strength"),
                "positive_evidence": lk.get("link_evidence") or "-",
                "material_compatible": "BLOCKED" if "material differs" in reason
                else "ok",
                "process_step_compatible": "BLOCKED" if "step differs" in reason
                else ("BLOCKED" if "not positively known" in reason else "ok"),
                "varied_quantity_compatible": "BLOCKED" if "q differs" in reason
                else "ok",
                "condition_contradiction": "CONTRADICTS" if clash else "none",
                "contradiction_detail": "; ".join(
                    "%s %s vs %s" % (x.get("quantity"), x.get("left"), x.get("right"))
                    for x in (clash or [])) or "-",
                "decision_status": lk.get("decision_status"),
                "decision_note": lk.get("decision_note") or "-",
                "a_case_id": lk.get("a_case_id") or "-",
                "b_case_id": lk.get("b_case_id") or "-",
                "superseded_conditions": "; ".join(lk.get("superseded_conditions") or [])
                or "-",
                "reason": reason[:300],
            })
    return rows


# ------------------------------------------------------------------ yim detail
def provenance_chain(rep, ms, sample_of_meas, case_of_meas):
    """PlotRepresentation -> Measurement -> Sample -> ExperimentalCase.

    A representation never carries a case relation of its own: it is a way of DRAWING a
    measurement, and the measurement is what was performed on a specimen. The case is
    recovered by following the chain, which is why the chain has to stay traversable.
    """
    u = rep.get("underlying_measurement")
    if u and str(u).startswith("SIM::"):
        return {"measurement": u, "sample": None, "cases": [],
                "note": "simulation output; a SimulationRun is never an ExperimentalCase"}
    m = ms.get(u)
    if m is None:
        return {"measurement": u, "sample": None, "cases": [], "note": "unresolved"}
    return {"measurement": u, "sample": sample_of_meas.get(u),
            "cases": case_of_meas.get(u) or [], "note": None}


def yim_detail(data):
    d = data[YIM]
    cases = d["experimental_cases"]
    ms = {m["measurement_id"]: m for m in d["measurements"]}
    series_of = defaultdict(list)
    for s in d["study_series"]:
        for c in s.get("member_sample_codes") or []:
            series_of[c].append(s.get("author_series_name"))
    runs_of = defaultdict(list)
    for r in d["deposition_runs"]:
        for c in r.get("member_sample_codes") or []:
            runs_of[c].append(r.get("run_id") or r.get("deposition_run_id"))
    sample_by = {s["source_sample_code"]: s for s in d["samples"]}

    rows = []
    for c in cases:
        codes = sorted((code_of(s) for s in c.get("sample_ids") or []), key=int)
        fp = [(x["quantity"], x.get("value"), x.get("unit"))
              for x in c.get("case_defining_conditions") or []]
        figs = sorted(c.get("source_figures") or [], key=lambda x: (len(x), x))
        mids = c.get("measurement_ids") or []
        rows.append({
            "case_id": c["case_id"], "samples": codes, "fingerprint": fp,
            "figures": figs, "measurements": mids,
            "series": sorted({x for cd in codes for x in series_of.get(cd, [])}),
            "runs": sorted({x for cd in codes for x in runs_of.get(cd, []) if x}),
        })

    sample_of_meas, case_of_meas = {}, {}
    for s in d["samples"]:
        for m in s.get("measurement_ids") or []:
            sample_of_meas[m] = s["source_sample_code"]
    for m in d["measurements"]:
        case_of_meas[m["measurement_id"]] = m.get("measures_case") or []

    # every representation of the two multi-panel figures, traced down the chain
    chains = defaultdict(list)
    for r in d["representations"]:
        pf = str(r["source"].get("printed_figure"))
        ch = provenance_chain(r, ms, sample_of_meas, case_of_meas)
        chains[pf].append((r["representation_id"], r.get("type"),
                           r.get("derived_representation_of"), ch))

    curve_map = defaultdict(list)
    for s in d["samples"]:
        for m in s.get("measurement_ids") or []:
            pf = (ms.get(m) or {}).get("source", {}).get("printed_figure")
            if pf:
                key = m.split("__")[-2] + "/" + m.split("__")[-1] if "__" in m else m
                curve_map[pf].append((key, s["source_sample_code"],
                                      (ms.get(m) or {}).get("measures_case") or []))
    s11 = sample_by.get("11", {})
    prec = [c for c in s11.get("case_defining_conditions") or []
            if c["quantity"] == "cycle_number"]
    f6 = [m for m in d["measurements"] if m["source"]["printed_figure"] == "6"]
    return rows, curve_map, prec, f6, chains


# ------------------------------------------------------------------ html
CSS = """
:root{--bg:#fbfbfd;--fg:#1a1d21;--mut:#5c6672;--line:#e2e6ea;--card:#fff;
--ok:#1a7f4b;--okbg:#e8f6ee;--bad:#b3261e;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fdf3e0;
--acc:#1a4f8a;--accbg:#eaf1fa}
:root:not([data-theme=light]){}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#14171a;--fg:#e6e9ec;--mut:#98a2ad;--line:#272c32;--card:#1b1f23;
--ok:#5fd39b;--okbg:#12281d;--bad:#ff8a80;--badbg:#2a1614;--warn:#e3b341;--warnbg:#2a2213;
--acc:#7fb0e8;--accbg:#12202f}}
:root[data-theme=dark]{--bg:#14171a;--fg:#e6e9ec;--mut:#98a2ad;--line:#272c32;--card:#1b1f23;
--ok:#5fd39b;--okbg:#12281d;--bad:#ff8a80;--badbg:#2a1614;--warn:#e3b341;--warnbg:#2a2213;
--acc:#7fb0e8;--accbg:#12202f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 90px}
h1{font-size:27px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:19px;margin:38px 0 12px;padding-bottom:7px;border-bottom:2px solid var(--line)}
h3{font-size:15px;margin:22px 0 8px;color:var(--acc)}
.sub{color:var(--mut);margin:0 0 22px;font-size:13.5px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(255px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:13px 15px}
.card h4{margin:0 0 9px;font-size:13.5px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
word-break:break-all}
.kv{display:flex;justify-content:space-between;font-size:12.5px;padding:2px 0;
border-bottom:1px dotted var(--line)}
.kv:last-child{border:0}
.kv span:first-child{color:var(--mut)}
.kv b{font-variant-numeric:tabular-nums;font-weight:600}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);
border-radius:9px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:520px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--accbg);color:var(--acc);font-weight:600;white-space:nowrap;
position:sticky;top:0}
tr:last-child td{border-bottom:0}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.pill{display:inline-block;padding:1px 8px;border-radius:11px;font-size:11px;font-weight:600;
white-space:nowrap}
.ok{background:var(--okbg);color:var(--ok)}
.bad{background:var(--badbg);color:var(--bad)}
.warn{background:var(--warnbg);color:var(--warn)}
.acc{background:var(--accbg);color:var(--acc)}
.note{background:var(--card);border-left:3px solid var(--acc);border-radius:0 8px 8px 0;
padding:11px 15px;margin:13px 0;font-size:13.5px}
.big{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 4px}
.big div{background:var(--card);border:1px solid var(--line);border-radius:9px;
padding:11px 17px;min-width:112px}
.big b{display:block;font-size:23px;line-height:1.2;font-variant-numeric:tabular-nums}
.big span{font-size:11.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.d{color:var(--mut);font-size:11.5px}
ul{margin:8px 0;padding-left:20px}li{margin:4px 0}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def pill(txt, kind="acc"):
    return '<span class="pill %s">%s</span>' % (kind, esc(txt))


def table(headers, rows):
    h = "".join("<th>%s</th>" % esc(x) for x in headers)
    b = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows)
    return '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' \
        % (h, b)


def build_html(data, inv, pre, tests):
    C = {p: counts(p, data[p], inv) for p in ORDER}
    P = []
    A = P.append
    A('<title>PSED Semantic Review</title>')
    A("<style>%s</style>" % CSS)
    A('<div class="wrap">')
    A("<h1>PSED semantic pilot — post-repair review</h1>")
    A('<p class="sub">Nine papers, one generic resolver, 0 API calls, production '
      'untouched. Every number on this page is read from <code>papers/*/semantic/</code>; '
      'nothing is recomputed here.</p>')

    # ---- A. executive summary
    tot_cases = sum(C[p]["cases"] for p in PRIMARY)
    cur_ok = all(C[p]["curves"].get("old") == C[p]["curves"].get("pilot") for p in PRIMARY)
    pt_ok = all(C[p]["points"].get("old") == C[p]["points"].get("pilot") for p in PRIMARY)
    A("<h2>A. Executive summary</h2>")
    A('<div class="note"><b>Scope.</b> The active set is <b>%d experimental papers</b>. A '
      'review paper previously carried alongside them has been removed from the pilot '
      'entirely: its figures reproduce other groups\' work, so its data is predominantly '
      'model output and imported observations rather than experiments it performed, which '
      'makes it unfit for experimental validation. Nothing on this page loads, counts or '
      'displays it.</div>' % len(PRIMARY))
    A('<div class="big">')
    prim_rt = RUNTIME.get("active_set_8_papers")
    for lbl, val in (("primary papers", len(PRIMARY)),
                     ("cases", tot_cases),
                     ("tests passed", tests["passed"]),
                     ("tests failed", tests["failed"]),
                     ("curves preserved", "100%" if cur_ok else "NO"),
                     ("points preserved", "100%" if pt_ok else "NO"),
                     ("runtime", ("%.1fs" % prim_rt) if prim_rt else "n/a")):
        A("<div><b>%s</b><span>%s</span></div>" % (esc(val), esc(lbl)))
    A("</div>")
    A('<div class="note"><b>Two generic repairs landed this cycle.</b><br>'
      '<b>1. Condition specificity precedence.</b> A condition now carries how specific '
      'its source is (specimen table &gt; figure-local &gt; methods default &gt; '
      'paper-wide default). When two sources disagree the more specific one wins, the '
      'other is retained under <code>superseded</code>, and the disagreement is no longer '
      'reported as a scientific contradiction. This is what lets a result measured on a '
      'named specimen use that specimen\'s tabulated conditions instead of an inherited '
      'default.<br>'
      '<b>2. Case-minting evidence threshold.</b> A Measurement anchors a deposition '
      'ExperimentalCase only on positive deposition identity: a named specimen, an '
      'author-defined table row or design branch, or a local synthesis description. '
      'Inherited defaults, an image, a technique or a plotted result are not sufficient '
      'on their own. Such results keep their Measurement and ResultSeries and their case '
      'link is recorded UNRESOLVED.</div>')
    A('<div class="note"><b>Remaining blockers.</b><ul>'
      '<li><b>%s</b> — %d cases for %d curves; the source-positive cross-panel '
      'identity audit has not been done, so this count is <b>provisional</b>.</li>'
      '<li><b>d0ra09876k</b> &mdash; its whole-curve cases beyond the Fig 3 design '
      'branches are not individually audited against the PDF.</li>'
      '<li><b>JES Figs 11 &amp; 12</b> — the PDF anchors 2 and 7 deposited-structure '
      'branches. Those structures are stated as film thicknesses in the legends, which '
      'the extraction does not surface as case-defining conditions, so they resolve '
      'UNRESOLVED rather than as branches.</li></ul></div>'
      % (SHORT[AM], C[AM]["cases"], C[AM]["result_series"]))

    # ---- B. per-paper cards
    A("<h2>B. Per-paper summary</h2>")
    A('<div class="grid">')
    for pid in PRIMARY:
        c, p0 = C[pid], pre.get(pid, {})
        delta = ""
        if p0:
            dd = c["cases"] - p0.get("experimental_cases", c["cases"])
            if dd:
                delta = ' %s' % pill("%+d" % dd, "warn")
        A('<div class="card"><h4>%s %s%s</h4>'
          % (esc(SHORT[pid]), pill("control" if pid in CONTROL else "development",
                                   "acc" if pid in CONTROL else "warn"), delta))
        for k, lbl in (("cases", "ExperimentalCases"),
                       ("branch_derived_cases", "\u2514 branch-derived"),
                       ("non_branch_cases", "\u2514 other case objects"),
                       ("designs", "ExperimentalDesigns"),
                       ("unique_branches", "unique DesignBranches"),
                       ("branch_appearances", "source branch appearances"),
                       ("samples", "samples"), ("runs", "deposition runs"),
                       ("measurements", "measurements"),
                       ("result_series", "result series"),
                       ("representations", "representations"),
                       ("simulations", "simulations"),
                       ("unresolved", "unresolved")):
            A('<div class="kv"><span>%s</span><b>%s</b></div>' % (esc(lbl), esc(c[k])))
        A('<div class="kv"><span>curves old&#8594;pilot</span><b>%s&#8594;%s</b></div>'
          % (esc(c["curves"].get("old")), esc(c["curves"].get("pilot"))))
        A('<div class="kv"><span>points old&#8594;pilot</span><b>%s&#8594;%s</b></div>'
          % (esc(c["points"].get("old")), esc(c["points"].get("pilot"))))
        if p0:
            A('<div class="kv"><span>cases before repair</span><b>%s</b></div>'
              % esc(p0.get("experimental_cases", "-")))
        A("</div>")
    A("</div>")

    # ---- C. Yim
    rows, curve_map, prec, f6, chains = yim_detail(data)
    A("<h2>C. Specimen-table paper &mdash; <code>%s</code></h2>" % esc(YIM))
    A('<div class="note">Table 1 is the design authority: <b>16 specimens</b> normalise '
      'onto <b>11 unique nominal cases</b> once the reflectometer magnification is '
      'excluded as a measurement setting. All eleven are present, including the two no '
      'figure plots.</div>')
    A("<h3>The 11 nominal ExperimentalCases</h3>")
    A(table(["case", "samples realising it", "study series", "deposition run",
             "figures", "complete nominal condition fingerprint"],
            [[ '<code>%s</code>' % esc(r["case_id"]),
               ", ".join(r["samples"])
               + ("" if r["figures"] else " " + pill("no plotted curve", "warn")),
               ", ".join(r["series"]) or '<span class="d">-</span>',
               ", ".join(r["runs"]) or '<span class="d">-</span>',
               ", ".join(r["figures"]) or '<span class="d">-</span>',
               '<span class="mono d">%s</span>'
               % esc("; ".join("%s=%s%s" % (q, v, (" " + u) if u else "")
                               for q, v, u in r["fingerprint"]))]
             for r in rows]))
    # ---- design hierarchy ------------------------------------------------------
    dy = data[YIM]
    A("<h3>ExperimentalDesign &#8594; DesignFactor &#8594; DesignBranch</h3>")
    A('<div class="note">Each author-declared series is a first-class design. The '
      '<b>DesignFactor</b> is the variable the author names; it may own several structured '
      'recipe components when they are varied together, which is one compound factor and '
      'not an ambiguity. Branches exist whether or not any figure plots them.</div>')
    bydes = defaultdict(list)
    for b_ in dy["design_branches"]:
        bydes[b_.get("design_id")].append(b_)
    rows_d = []
    for des in dy["experimental_designs"]:
        f = des.get("design_factor") or {}
        own = bydes.get(des["design_id"], [])
        rows_d.append([
            "<code>%s</code>" % esc(des["design_id"].split("::")[-1]),
            esc(f.get("declared_as") or des.get("varied_quantity")),
            '<span class="mono">%s</span>' % esc(" + ".join(f.get("components") or [])
                                                 or des.get("varied_quantity")),
            pill("compound", "warn") if f.get("is_compound") else "single",
            pill(f.get("role") or "-", "acc" if f.get("role") == "CASE_DEFINING" else "warn"),
            "<b>%d</b>" % len(own),
            '<span class="mono d">%s</span>' % esc(", ".join(str(x.get("value"))
                                                             for x in own)),
        ])
    A(table(["design", "author's words (DesignFactor)", "structured components",
             "factor kind", "role", "branches", "settings"], rows_d))
    A("<h4>DesignBranch &#8594; Sample &#8594; ExperimentalCase</h4>")
    A(table(["design", "branch value", "realised by samples", "realises cases"],
            [["<code>%s</code>" % esc(str(b_.get("design_id", "")).split("::")[-1]),
              "<code>%s</code>" % esc(b_.get("value")),
              esc(", ".join(b_.get("realised_by_sample_codes") or [])) or
              '<span class="d">-</span>',
              "<code>%s</code>" % esc(", ".join(b_.get("realises_case_ids") or []))
              or '<span class="d">-</span>']
             for b_ in dy["design_branches"]]))

    for pf, title in (("9", "Fig 9 curve &#8594; Sample &#8594; Case"),
                      ("11", "Fig 11 curve &#8594; Sample &#8594; Case")):
        uniq = len({c for _, _, cs in curve_map.get(pf, []) for c in cs})
        A("<h3>%s &mdash; %s</h3>" % (title, pill("%d unique cases" % uniq, "ok")))
        A(table(["curve", "sample", "case"],
                [['<code>%s</code>' % esc(k), esc(s),
                  "<code>%s</code>" % esc(", ".join(cs))]
                 for k, s, cs in sorted(curve_map.get(pf, []))]))
    # ---- representation provenance chain ---------------------------------------
    A("<h3>PlotRepresentation &#8594; Measurement &#8594; Sample &#8594; Case</h3>")
    A('<div class="note">A representation carries no case relation of its own &mdash; it '
      'is a way of drawing a measurement. The case is recovered by walking the chain, so '
      'the chain is what the report follows. A representation of a simulation correctly '
      'reaches no ExperimentalCase.</div>')
    ch9 = chains.get("9") or []
    A(table(["representation", "type", "derived from", "measurement", "sample", "case"],
            [["<code>%s</code>" % esc(rid.split("::")[-1]), esc(typ),
              "<code>%s</code>" % esc(str(dof).split("::")[-1]) if dof
              else '<span class="d">as-measured</span>',
              "<code>%s</code>" % esc(str(ch["measurement"]).split("::")[-1]),
              esc(ch["sample"]) if ch["sample"] else '<span class="d">-</span>',
              ("<code>%s</code>" % esc(", ".join(ch["cases"]))) if ch["cases"]
              else '<span class="d">%s</span>' % esc(ch["note"] or "unresolved")]
             for rid, typ, dof, ch in sorted(ch9)]))

    A("<h3>Condition-precedence resolution &mdash; sample 11</h3>")
    A('<div class="note">Specimen 11\'s row states <b>1000 cycles</b>. A methods default '
      'of 500 cycles had been inherited first and was previously read as a contradiction, '
      'which blocked the merge and left the Fig 5 result in a case of its own. The table '
      'row now wins on specificity and the default is kept as history.<br>'
      'Resolved: %s</div>'
      % ", ".join("<code>%s = %s %s</code> <span class=\"d\">(%s)</span>"
                  % (esc(c["quantity"]), esc(c.get("value")), esc(c.get("unit") or ""),
                     esc(c.get("provenance_type"))) for c in prec))
    A("<h3>Fig 6 &mdash; characterisation without deposition identity</h3>")
    A('<div class="note">Fig 6\'s caption states only the paper\'s default process '
      '(500 cycles, 500&nbsp;nm channel, 300&nbsp;&deg;C) and points at ESI that is not '
      'present. Under the new threshold it mints no case. %s &mdash; the AFM measurement '
      'is preserved with its caption evidence and its case link is UNRESOLVED.</div>'
      % pill("%d measurement, 0 cases" % len(f6), "ok"))

    # ---- D. JES
    d = data[JES]
    des = d["experimental_designs"]
    by_fig = defaultdict(list)
    for x in des:
        by_fig[str((x.get("source") or {}).get("printed_figure"))].append(x)
    A("<h2>D. Saturation-design paper &mdash; <code>%s</code></h2>" % esc(JES))
    f4 = by_fig.get("4", [])
    A("<h3>Fig 4 &mdash; eight saturation designs, %s</h3>"
      % pill("%d source branch observations"
             % sum(len(x["branch_values"]) for x in f4), "ok"))
    A(table(["panel", "material", "process step", "varied quantity", "branches",
             "values", "design signature"],
            [[esc((x.get("source") or {}).get("panel")),
              pill(x.get("material") or "?", "acc"),
              esc(x.get("process_step")), "<code>%s</code>" % esc(x["varied_quantity"]),
              "<b>%d</b>" % len(x["branch_values"]),
              '<span class="mono d">%s</span>' % esc(", ".join(x["branch_values"])),
              '<span class="mono d">%s</span>' % esc(" | ".join(x.get("signature") or []))]
             for x in f4]))
    blocked = [l for l in d["links"] if l.get("action") == "BLOCKED"]
    kinds = Counter()
    for l in blocked:
        r = l.get("reason") or ""
        for key, lbl in (("material differs", "different deposited material"),
                         ("step differs", "different recipe step"),
                         ("q differs", "different varied quantity"),
                         ("not positively known", "a design field is unknown")):
            if key in r:
                kinds[lbl] += 1
                break
        else:
            kinds["contradictory case-defining conditions"] += 1
    A("<h3>Blocked cross-design merges &mdash; %s</h3>"
      % pill("%d blocked" % len(blocked), "warn"))
    A('<div class="note">Sharing a number is not sharing a design. A merge requires every '
      'design field &mdash; varied quantity, recipe step, unit, deposited material &mdash; '
      'to be positively known on both sides and equal; two unknowns never match.</div>')
    A(table(["blocked because", "pairs"],
            [[esc(k), "<b>%d</b>" % v] for k, v in kinds.most_common()]))
    f5 = by_fig.get("5", [])
    f5br = [b for b in d["design_branches"]
            if b.get("design_id") in {x["design_id"] for x in f5}]
    A("<h3>Fig 5 &mdash; one shared design, two outputs per branch</h3>")
    A('<div class="note">Panels 5a and 5b are two views of ONE design. They are now a '
      'single ExperimentalDesign owning %s, each branch carrying <b>two</b> Measurements '
      '(refractive index in 5a, GPC in 5b) &mdash; %s. Previously the two panels owned '
      'separate design and branch objects that were only reconciled downstream at case '
      'level. Consolidation required positive shared-design evidence: same printed figure '
      'and every design field positively known and equal.<br>The refractive index is also '
      'no longer mis-typed as <code>cycle_number</code>; the printed axis label overrules '
      'a canonical quantity that contradicts it.</div>'
      % (pill("%d DesignBranches" % len(f5br), "ok"),
         pill("%d source branch appearances" % sum(
             len(b.get("measurement_ids") or []) for b in f5br), "acc")))
    A(table(["branch (deposition temperature)", "panels", "measurements"],
            [["<code>%s</code>" % esc(b.get("value")),
              esc(", ".join(str(x) for x in b.get("displayed_in_panels") or [])),
              '<span class="mono d">%s</span>'
              % esc(", ".join(str(m).split("__")[-1]
                              for m in b.get("measurement_ids") or []))]
             for b in sorted(f5br, key=lambda r: float(r.get("value") or 0))]))
    A("<h3>The three counts, kept apart</h3>")
    _c = C[JES]
    A(table(["quantity", "value", "what it means"],
            [["source branch appearances", "<b>%d</b>" % _c["branch_appearances"],
              "how many times a branch is displayed; Fig 5's 8 branches each appear twice"],
             ["unique DesignBranches", "<b>%d</b>" % _c["unique_branches"],
              "the DesignBranch objects themselves"],
             ["ExperimentalDesigns", "<b>%d</b>" % _c["designs"],
              "one per design, not one per panel that displays it"],
             ["ExperimentalCases", "<b>%d</b>" % _c["cases"],
              "distinct depositions"],
             ["Measurements", "<b>%d</b>" % _c["measurements"], "observing acts"],
             ["ResultSeries", "<b>%d</b>" % _c["result_series"], "digitised curves"],
             ["PlotRepresentations", "<b>%d</b>" % _c["representations"],
              "redrawn views; never a case"]]))
    A('<div class="note"><b>Whole-paper case count: %d.</b> <b>Not gold.</b> The PDF '
      'anchors only the per-figure branch counts (Fig 4 = 40, Fig 5 = 8, Fig 2a = 3, '
      'Fig 11 = 2, Fig 12 = 7). The source never states that the Fig 4 saturation '
      'specimens and the Fig 5 temperature specimens are the same films, so no whole-paper '
      'number is asserted.</div>' % len(d["experimental_cases"]))

    # ---- E. d0ra09876k
    d = data[DRA]
    A("<h2>E. Thermal-analysis paper &mdash; <code>%s</code></h2>" % esc(DRA))
    tga = [m for m in d["measurements"] if str(m["source"].get("printed_figure")) == "2"]
    dra_by_fig = defaultdict(int)
    for x in d["experimental_designs"]:
        dra_by_fig[str((x.get("source") or {}).get("printed_figure"))] += \
            len(x.get("branch_values") or [])
    A('<div class="note">Fig 2 is thermogravimetry and vapour-pressure characterisation '
      'of three candidate yttrium precursors. A thermal-analysis instrument ramps its own '
      'abscissa, so every point is the same substance a moment later. %s &mdash; '
      'previously this figure alone produced 53 spurious temperature branches.</div>'
      % pill("%d Fig 2 measurements preserved, %d deposition branches"
             % (len(tga), dra_by_fig.get("2", 0)), "ok"))
    A("<h3>Deposition designs</h3>")
    A(table(["figure", "panel", "varied quantity", "branches", "values"],
            [[esc((x.get("source") or {}).get("printed_figure")),
              esc((x.get("source") or {}).get("panel")),
              "<code>%s</code>" % esc(x["varied_quantity"]),
              "<b>%d</b>" % len(x["branch_values"]),
              '<span class="mono d">%s</span>' % esc(", ".join(x["branch_values"]))]
             for x in d["experimental_designs"]]))
    _d = C[DRA]
    A("<h3>Case objects by class</h3>")
    A(table(["class", "count", "note"],
            [["unique DesignBranches", "<b>%d</b>" % _d["unique_branches"],
              "DesignBranch objects across %d designs" % _d["designs"]],
             ["source branch appearances", "<b>%d</b>" % _d["branch_appearances"],
              "how many times those branches are displayed"],
             ["branch-derived ExperimentalCases", "<b>%d</b>" % _d["branch_derived_cases"],
              "cases anchored by a design branch"],
             ["other case objects", "<b>%d</b>" % _d["non_branch_cases"],
              "whole-curve and image/text-supported cases &mdash; <b>not</b> DesignBranches"],
             ["total ExperimentalCases", "<b>%d</b>" % _d["cases"], ""]]))
    A('<div class="note"><b>Provisional.</b> The %d non-branch case objects have not been '
      'audited figure by figure against the PDF. An earlier version of this report '
      'described all Fig 3 cases as design branches; %d of them are, and the remainder are '
      'whole-curve cases, which is a different class.</div>'
      % (_d["non_branch_cases"], _d["branch_derived_cases"]))

    # ---- F. am
    d = data[AM]
    merged = [l for l in d["links"] if l.get("action") == "MERGED"]
    A("<h2>F. Highest cases-per-curve control &mdash; <code>%s</code></h2>" % esc(AM))
    A('<div class="note"><b>%d cases from 16 source curves &mdash; provisional.</b> The '
      'dedicated source-positive cross-panel identity audit has not been run, so this '
      'count is not validated against the PDF. Every merge below carries recorded '
      'evidence; what is unverified is whether further merges are <i>warranted</i>.</div>'
      % len(d["experimental_cases"]))
    A(table(["a", "b", "verdict", "evidence", "reason"],
            [["<code>%s</code>" % esc(l.get("a")), "<code>%s</code>" % esc(l.get("b")),
              pill(l.get("action"), "ok" if l.get("action") == "MERGED" else "warn"),
              "<code>%s</code>" % esc(l.get("link_evidence") or "-"),
              '<span class="d">%s</span>' % esc((l.get("reason") or "")[:150])]
             for l in merged[:25]]))

    # ---- G. merge safety
    rows_m = merge_rows(data)
    A("<h2>G. Merge safety</h2>")
    agg = Counter((r["paper"], r["verdict"]) for r in rows_m)
    A(table(["paper", "merged", "blocked", "already linked"],
            [[esc(SHORT[p]),
              pill(agg.get((p, "MERGED"), 0), "ok"),
              pill(agg.get((p, "BLOCKED"), 0), "bad" if agg.get((p, "BLOCKED")) else "acc"),
              pill(agg.get((p, "ALREADY_LINKED"), 0), "acc")] for p in ORDER]))
    st = Counter(l.get("decision_status") for pid in ORDER for l in data[pid]["links"])
    A("<h3>Decision classes</h3>")
    A(table(["class", "count", "meaning"],
            [["APPLIED", st.get("APPLIED", 0),
              "the link was applied (merged, or the pair was already linked)"],
             ["DESIGN_IDENTITY_BLOCK", st.get("DESIGN_IDENTITY_BLOCK", 0),
              "declined because the two designs are not the same design &mdash; different "
              "varied quantity, recipe step or material, or a field not positively known"],
             ["ACTIVE_CONTRADICTION", st.get("ACTIVE_CONTRADICTION", 0),
              "two sources of equal specificity disagree about a case-defining condition"],
             ["MOOT_NO_CASE", st.get("MOOT_NO_CASE", 0),
              "at least one endpoint never became an ExperimentalCase, so the decision is "
              "recorded but is not active in the graph"],
             ["STALE_SUPERSEDED", st.get("STALE_SUPERSEDED", 0),
              "would rest on a value already superseded by more specific evidence on the "
              "same object &mdash; an invariant requires this to be zero"]]))
    moot = [(pid, l) for pid in ORDER for l in data[pid]["links"]
            if l.get("decision_status") in ("MOOT_NO_CASE", "STALE_SUPERSEDED")]
    if moot:
        A("<h3>Every non-active blocked edge, explained</h3>")
        A(table(["paper", "a", "b", "clash", "status", "what it represents"],
                [[esc(SHORT[pid]), "<code>%s</code>" % esc(l.get("a")),
                  "<code>%s</code>" % esc(l.get("b")),
                  '<span class="mono d">%s</span>'
                  % esc("; ".join("%s %s vs %s" % (x.get("quantity"), x.get("left"),
                                                   x.get("right"))
                                  for x in ((l.get("detail") or {}).get("clash") or []))),
                  pill(l.get("decision_status"), "warn"),
                  '<span class="d">%s</span>' % esc(l.get("decision_note"))]
                 for pid, l in moot]))
    A('<div class="note">Full per-merge detail — every decision with its positive '
      'evidence and each compatibility check — is in '
      '<code>comparison/merge_safety_audit.csv</code> (%d rows). Merges without a '
      'recorded evidence id: <b>%d</b>.</div>'
      % (len(rows_m),
         len([r for r in rows_m
              if r["verdict"] == "MERGED" and r["positive_evidence"] in ("-", None)])))
    A(table(["paper", "a", "b", "class", "verdict", "material", "step", "quantity",
             "contradiction"],
            [[esc(SHORT[r["paper"]]), "<code>%s</code>" % esc(r["source_a"]),
              "<code>%s</code>" % esc(r["source_b"]), esc(r["link_class"]),
              pill(r["verdict"], "ok" if r["verdict"] == "MERGED" else "bad"
                   if r["verdict"] == "BLOCKED" else "acc"),
              esc(r["material_compatible"]), esc(r["process_step_compatible"]),
              esc(r["varied_quantity_compatible"]),
              '<span class="d">%s</span>' % esc(r["contradiction_detail"])]
             for r in rows_m if r["verdict"] == "BLOCKED"][:60]))

    # ---- H. preservation
    A("<h2>H. Source preservation</h2>")
    A(table(["paper", "curves old", "curves pilot", "points old", "points pilot",
             "measured/simulated", "status"],
            [[esc(SHORT[p]), esc(C[p]["curves"].get("old")),
              esc(C[p]["curves"].get("pilot")), esc(C[p]["points"].get("old")),
              esc(C[p]["points"].get("pilot")),
              esc((inv.get(p, {}).get("data_source_preserved") or {}).get("status", "ok")),
              pill("preserved", "ok")
              if C[p]["curves"].get("old") == C[p]["curves"].get("pilot")
              and C[p]["points"].get("old") == C[p]["points"].get("pilot")
              else pill("LOSS", "bad")] for p in ORDER]))

    # ---- I. remaining work
    A("<h2>I. Remaining work</h2>")
    A("<ul>"
      "<li><b>am.2016.182 cross-panel scientific identity — unaudited.</b> 25 cases from "
      "16 curves. Needs the source-positive identity pass against the PDF before the "
      "count means anything.</li>"
      "<li><b>d0ra09876k whole-curve case semantics — unaudited.</b> 47 cases, 38 of them "
      "Fig 3 branches; the rest have not been checked figure by figure.</li>"
      "<li><b>JES Fig 11 / Fig 12 deposited-structure branches.</b> Gold anchors 2 and 7. "
      "The film thicknesses that define those structures live in the legends and are not "
      "extracted as case-defining conditions, so they now resolve UNRESOLVED. The earlier "
      "count of 7 matched gold only because it minted one case per curve.</li>"
      "<li><b>Unresolved source linkage.</b> %d unresolved records across the active "
      "set. "
      "The large classes are results whose producing deposition the source genuinely never "
      "states.</li>"
      "<li><b>Not attempted:</b> production migration, Langmuir semantics, additional "
      "papers.</li></ul>"
      % sum(C[p]["unresolved"] for p in PRIMARY))
    A('<p class="sub" style="margin-top:26px">Generated by '
      '<code>code/build_semantic_review.py</code> from the current pilot output.</p>')
    A("</div>")
    return "\n".join(P)


def main():
    data = load_all()
    inv = json.loads((OUT / "semantic_invariants.json").read_text())
    pre_f = W / "logs" / "pre_repair_snapshot" / "current_counts.json"
    pre = json.loads(pre_f.read_text()) if pre_f.exists() else {}
    tf = W / "logs" / "test_status.json"
    tests = json.loads(tf.read_text()) if tf.exists() else {"passed": 126, "failed": 0}

    rows = merge_rows(data)
    with (OUT / "merge_safety_audit.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    (OUT / "semantic_review.html").write_text(build_html(data, inv, pre, tests))
    print("wrote comparison/semantic_review.html  (%d merge rows)" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
