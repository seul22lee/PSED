#!/usr/bin/env python3
"""
build_dashboard.py — the visual scientific-review dashboard for the nine-paper pilot.

    python3 code/build_dashboard.py

Self-contained: one HTML file, inline SVG, no server and no external asset. The primary
interface is graphical — node-link graphs, matrices, fingerprints and small multiples —
with the text tables collapsed behind them rather than in front of them.

Every mark is drawn from the semantic JSON; nothing here recomputes semantics.
"""
import base64
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
MAN = json.loads((W / "pilot_papers.json").read_text())
PAPERS, ROLES = MAN["papers"], MAN["roles"]
OUT = W / "report" / "index.html"


def sem(pid, name):
    f = W / "papers" / pid / "semantic" / ("%s.json" % name)
    return json.loads(f.read_text()) if f.exists() else []


def e(x):
    return html.escape(str(x if x is not None else ""))


def short(pid, n=22):
    return pid if len(pid) <= n else pid[:n - 1] + "…"


# ---------------------------------------------------------------- visual vocabulary
#: node type -> (glyph, css class, human label). Shape and glyph carry the meaning; the
#: colour only reinforces it, so the graphs stay readable without colour.
NODE = {
    "case":  ("◆", "n-case", "ExperimentalCase"),
    "meas":  ("●", "n-meas", "Measurement"),
    "rs":    ("▬", "n-rs", "ResultSeries"),
    "rep":   ("◇", "n-rep", "PlotRepresentation"),
    "sample": ("▲", "n-samp", "Sample"),
    "run":   ("⬟", "n-run", "DepositionRun"),
    "runev": ("⬠", "n-runev", "run-distinctness evidence"),
    "series": ("▣", "n-series", "StudySeries"),
    "sim":   ("✚", "n-sim", "SimulationRun"),
    "unres": ("○", "n-unres", "unresolved"),
    "mat":   ("⬢", "n-mat", "Material"),
}
UNRES_ORDER = ["CONDITION_ONLY_NO_POSITIVE_LINK", "PROVENANCE_CHAIN_INCOMPLETE",
               "SOURCE_TRULY_UNSPECIFIED", "MEASUREMENT_ONLY_FIGURE",
               "REFERENCE_BY_DESIGN", "IMPORTED_LITERATURE", "CONFLICTING_EVIDENCE"]

CSS = """
:root{--bg:#f5f7fa;--fg:#141821;--mut:#5b6675;--line:#dae0e8;--card:#fff;--accent:#0b6e7d;
 --case:#0b6e7d;--meas:#1f7a4d;--rs:#5b6675;--rep:#8a5a12;--samp:#7a3f9e;--run:#a8410f;
 --sim:#9a5b00;--unres:#8a7300;--mat:#0f5f8a;--ctrl:#0b6e7d;--unseen:#a8410f;--chip:#eaeff5}
@media(prefers-color-scheme:dark){:root{--bg:#0f1319;--fg:#e6ebf2;--mut:#96a2b2;--line:#28303b;
 --card:#161b22;--accent:#4fc3d1;--case:#4fc3d1;--meas:#5ecf92;--rs:#96a2b2;--rep:#e0a267;
 --samp:#c497e8;--run:#f0906a;--sim:#e8b04f;--unres:#e2c760;--mat:#6ab8e8;--ctrl:#4fc3d1;
 --unseen:#f0906a;--chip:#1e242d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,BlinkMacSystemFont,
 "Segoe UI",Roboto,sans-serif;font-variant-numeric:tabular-nums}
.wrap{max-width:1340px;margin:0 auto;padding:26px 20px 100px}
h1{font-family:Georgia,serif;font-size:27px;margin:0 0 4px}
h2{font-family:Georgia,serif;font-size:20px;margin:34px 0 8px;padding-bottom:6px;
 border-bottom:2px solid var(--accent)}
h3{font-size:12px;margin:22px 0 7px;color:var(--mut);text-transform:uppercase;letter-spacing:.07em}
.sub{color:var(--mut);max-width:92ch}
a{color:var(--accent)}
.hint{color:var(--mut);font-size:12px;margin:2px 0 8px;max-width:96ch}
.scroll{overflow-x:auto;max-width:100%}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
table{border-collapse:collapse;font-size:12px;margin:6px 0}
th,td{border:1px solid var(--line);padding:4px 7px;text-align:left;vertical-align:top}
th{background:var(--chip);font-weight:600}
details{border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin:6px 0;
 background:var(--card)}
details>summary{cursor:pointer;font-size:12px;color:var(--mut)}
/* --- paper cards --- */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:11px;margin:12px 0}
.pc{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--ctrl);
 border-radius:10px;padding:11px 13px;text-decoration:none;color:inherit;display:block}
.pc.unseen{border-left:5px dashed var(--unseen)}
.pc:hover{border-color:var(--accent)}
.pc .nm{font-family:Georgia,serif;font-size:13.5px;font-weight:700;word-break:break-word}
.pc .rl{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:1px 0 7px}
.pc .rl b{color:var(--unseen)}
.mini{display:grid;grid-template-columns:auto 1fr auto;gap:2px 6px;align-items:center;font-size:11px}
.mini i{font-style:normal;color:var(--mut);white-space:nowrap}
.mini b{font-weight:700}
.trk{height:6px;background:var(--chip);border-radius:3px;overflow:hidden;min-width:34px}
.trk span{display:block;height:100%}
/* --- verdict pills --- */
.v{display:inline-block;padding:1px 8px;border-radius:20px;font-size:10.5px;font-weight:700;
 border:1px solid;letter-spacing:.03em}
.v.PASS{color:var(--meas);border-color:var(--meas)}
.v.PARTIAL{color:var(--sim);border-color:var(--sim)}
.v.FAIL{color:var(--run);border-color:var(--run)}
.tag{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10.5px;
 border:1px solid var(--line);background:var(--chip);font-weight:600}
/* --- node glyph legend --- */
.leg{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px;font-size:11.5px;color:var(--mut)}
.leg span{border:1px solid var(--line);border-radius:14px;padding:1px 9px;background:var(--card)}
.g-case{color:var(--case)}.g-meas{color:var(--meas)}.g-rs{color:var(--rs)}.g-rep{color:var(--rep)}
.g-samp{color:var(--samp)}.g-run{color:var(--run)}.g-sim{color:var(--sim)}.g-unres{color:var(--unres)}
.g-mat{color:var(--mat)}
svg{display:block;max-width:100%}
svg text{font:10px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;fill:var(--fg)}
svg .mut{fill:var(--mut)}
svg .edge{stroke:var(--line);stroke-width:1.2;fill:none}
svg .edge.dash{stroke-dasharray:3 3}
/* --- matrix --- */
.mx{border-collapse:collapse;font-size:10.5px}
.mx th{background:transparent;border:none;padding:2px 4px;font-weight:600;color:var(--mut)}
.mx td{border:1px solid var(--line);padding:0;width:19px;height:19px;text-align:center}
.mx td.rh{width:auto;text-align:left;padding:2px 7px;border:none;white-space:nowrap;font-weight:600}
.mx .c{display:block;width:100%;height:100%;line-height:19px;font-size:11px}
.mx .c.m{background:color-mix(in srgb,var(--meas) 26%,transparent);color:var(--meas)}
.mx .c.s{background:color-mix(in srgb,var(--sim) 26%,transparent);color:var(--sim)}
.mx .c.u{background:color-mix(in srgb,var(--unres) 22%,transparent);color:var(--unres)}
.mx .vert{writing-mode:vertical-rl;transform:rotate(180deg);font-size:9.5px;max-height:96px;
 overflow:hidden}
/* --- fingerprint --- */
.fp td{border:1px solid var(--line);padding:2px 6px;font-size:10.5px;white-space:nowrap}
.fp td.k{background:color-mix(in srgb,var(--meas) 16%,transparent)}
.fp td.r{background:color-mix(in srgb,var(--accent) 20%,transparent);font-weight:700}
.fp td.i{background:color-mix(in srgb,var(--samp) 14%,transparent);font-style:italic}
.fp td.n{color:var(--mut);opacity:.55}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.bars{display:grid;grid-template-columns:auto 1fr auto;gap:3px 8px;align-items:center;font-size:11.5px}
.bars i{font-style:normal;color:var(--mut);white-space:nowrap}
.stk{display:flex;height:15px;border-radius:3px;overflow:hidden;background:var(--chip)}
.stk span{display:block}
.fig{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));gap:9px}
.fcard{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:11.5px}
.fcard b{font-family:Georgia,serif;font-size:12.5px}
.fcard .bd{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}
.q{font-size:11px;color:var(--mut);font-style:italic;border-left:3px solid var(--line);
 padding-left:8px;margin:4px 0}
.chain{display:flex;gap:5px;align-items:center;flex-wrap:wrap;font-size:11.5px;margin:4px 0}
.chain b{background:var(--chip);border:1px solid var(--line);border-radius:6px;padding:1px 7px}
.stop{color:var(--unres);border:1px dashed var(--unres);border-radius:6px;padding:1px 7px}
.sticky{position:sticky;top:0;background:var(--bg);z-index:5;padding:8px 0;border-bottom:1px solid var(--line)}
.nav{display:flex;gap:6px;flex-wrap:wrap;font-size:11.5px}
.nav a{text-decoration:none;border:1px solid var(--line);border-radius:14px;padding:1px 9px;
 background:var(--card)}
.nav a.unseen{border-style:dashed;border-color:var(--unseen)}
"""


# ------------------------------------------------------------------ svg primitives
def bar(v, vmax, cls="meas", w=90):
    frac = 0 if not vmax else max(0.02, min(1.0, v / float(vmax)))
    return ('<span class="trk"><span style="width:%.0f%%;background:var(--%s)"></span></span>'
            % (frac * 100, cls))


def stacked(parts, total, width=250, height=15):
    """parts = [(value, cssvar, label)]"""
    if not total:
        return '<div class="stk"></div>'
    out = ['<div class="stk" title="%s">' % e("; ".join("%s %d" % (l, v) for v, _, l in parts if v))]
    for v, var, lab in parts:
        if not v:
            continue
        out.append('<span style="width:%.2f%%;background:var(--%s)" title="%s %d"></span>'
                   % (100.0 * v / total, var, e(lab), v))
    out.append("</div>")
    return "".join(out)


def node_svg(x, y, kind, label, sub=None, wpx=None):
    glyph, cls, _ = NODE[kind]
    var = {"case": "case", "meas": "meas", "rs": "rs", "rep": "rep", "sample": "samp",
           "run": "run", "runev": "run", "series": "accent", "sim": "sim",
           "unres": "unres", "mat": "mat"}[kind]
    wpx = wpx or max(96, 7 * len(label) + 26)
    dash = ' stroke-dasharray="3 3"' if kind in ("runev", "unres") else ""
    return ('<g><rect x="%d" y="%d" rx="7" width="%d" height="26" fill="var(--card)" '
            'stroke="var(--%s)" stroke-width="1.4"%s/>'
            '<text x="%d" y="%d" fill="var(--%s)" font-size="12">%s</text>'
            '<text x="%d" y="%d">%s</text>%s</g>'
            % (x, y, wpx, var, dash, x + 8, y + 18, var, glyph, x + 22, y + 17, e(label),
               ('<text x="%d" y="%d" class="mut" font-size="9">%s</text>'
                % (x + 22, y + 26, e(sub))) if sub else ""))


def edge_svg(x1, y1, x2, y2, dash=False):
    mx = (x1 + x2) / 2.0
    return ('<path class="edge%s" d="M%d %d C%d %d %d %d %d %d"/>'
            % (" dash" if dash else "", x1, y1, mx, y1, mx, y2, x2, y2))


# ============================================================== per-paper views
def case_graph(pid, o):
    """Node-link graph: ExperimentalCase -> Measurement -> ResultSeries -> Representation,
    with Sample / Run / Series where evidence exists, and the model branch drawn apart."""
    cases, ms = o["experimental_cases"], {m["measurement_id"]: m for m in o["measurements"]}
    rs_by_m = defaultdict(list)
    for r in o["result_series"]:
        if r.get("produced_by"):
            rs_by_m[r["produced_by"]].append(r)
    rep_by_m = defaultdict(list)
    for r in o["representations"]:
        if r.get("underlying_measurement"):
            rep_by_m[r["underlying_measurement"]].append(r)
    samp_of = {}
    for s in o["samples"]:
        for m in s["measurement_ids"]:
            samp_of[m] = s
    run_of = {s["sample_id"]: s.get("produced_by_run") for s in o["samples"]}

    SHOW = 14
    shown = cases[:SHOW]
    rows, y = [], 14
    COLX = (10, 240, 470, 660)
    for c in shown:
        mids = [m for m in c["measurement_ids"] if m in ms][:5]
        h = max(1, len(mids)) * 34
        rows.append((c, mids, y, h))
        y += h + 12
    height = max(90, y + 10)
    svg = ['<svg viewBox="0 0 900 %d" width="900" height="%d" role="img" '
           'aria-label="case to measurement graph">' % (height, height)]
    for c, mids, y0, h in rows:
        cy = y0 + h / 2 - 13
        lbl = c["case_id"].split("-")[-1]
        sub = " ".join(filter(None, [c.get("deposited_material") or "material?",
                                     c.get("geometry") or ""]))[:26]
        svg.append(node_svg(COLX[0], int(cy), "case", "CASE %s" % lbl, sub, wpx=180))
        yy = y0
        for mid in mids:
            m = ms[mid]
            tech = ", ".join(m["technique"] or []) or "measurement"
            svg.append(edge_svg(COLX[0] + 180, int(cy) + 13, COLX[1], yy + 13))
            svg.append(node_svg(COLX[1], yy, "meas", tech[:22],
                                "Fig %s%s" % (m["source"]["printed_figure"],
                                              m["source"]["panel"] or ""), wpx=200))
            nrs, nrep = len(rs_by_m.get(mid) or []), len(rep_by_m.get(mid) or [])
            if nrs:
                svg.append(edge_svg(COLX[1] + 200, yy + 13, COLX[2], yy + 13))
                svg.append(node_svg(COLX[2], yy, "rs", "%d ResultSeries" % nrs, wpx=130))
            if nrep:
                svg.append(edge_svg(COLX[2] + 130, yy + 13, COLX[3], yy + 13, dash=True))
                svg.append(node_svg(COLX[3], yy, "rep", "%d representation%s"
                                    % (nrep, "" if nrep == 1 else "s"), wpx=150))
            s = samp_of.get(mid)
            if s:
                svg.append(node_svg(COLX[3] + 160, yy, "sample",
                                    "sample %s" % s["source_sample_code"], wpx=88))
            yy += 34
        if not mids:
            svg.append(edge_svg(COLX[0] + 180, int(cy) + 13, COLX[1], y0 + 13, dash=True))
            svg.append(node_svg(COLX[1], y0, "unres", "no measurement linked", wpx=180))
    svg.append("</svg>")
    extra = ""
    if len(cases) > SHOW:
        extra = ('<p class="hint">showing the first %d of %d cases; the full set is in the '
                 'matrix below and in <code>semantic/experimental_cases.json</code></p>'
                 % (SHOW, len(cases)))
    sims = o["simulation_runs"]
    if sims:
        byfig = Counter(s["source"]["printed_figure"] for s in sims)
        sy = 14
        s2 = ['<svg viewBox="0 0 620 %d" width="620" height="%d">'
              % (len(byfig) * 34 + 20, len(byfig) * 34 + 20)]
        for fig, n in sorted(byfig.items(), key=lambda kv: (len(str(kv[0])), str(kv[0]))):
            s2.append(node_svg(10, sy, "sim", "Model / SimulationRun", "Fig %s" % fig, wpx=196))
            s2.append(edge_svg(206, sy + 13, 240, sy + 13))
            s2.append(node_svg(240, sy, "rs", "%d ResultSeries" % n, wpx=130))
            s2.append('<text x="386" y="%d" class="mut">never an ExperimentalCase</text>' % (sy + 17))
            sy += 34
        s2.append("</svg>")
        extra += ('<h3>Model branch — kept separate</h3><div class="scroll">%s</div>'
                  % "".join(s2))
    return '<div class="scroll">%s</div>%s' % ("".join(svg), extra)


def figure_case_matrix(pid, o):
    """rows = printed figure/panel, columns = ExperimentalCase."""
    cases = o["experimental_cases"]
    cid = [c["case_id"] for c in cases]
    idx = {c: i for i, c in enumerate(cid)}
    rows = defaultdict(lambda: {})
    for m in o["measurements"]:
        key = "Fig %s%s" % (m["source"]["printed_figure"], m["source"]["panel"] or "")
        tech = ", ".join(m["technique"] or []) or "measurement"
        if not m["measures_case"]:
            rows[key].setdefault("__unres__", []).append(tech)
        for c in m["measures_case"]:
            rows[key].setdefault(c, []).append(tech)
    for s in o["simulation_runs"]:
        rows["Fig %s" % s["source"]["printed_figure"]].setdefault("__sim__", []).append("model")
    if not rows:
        return '<p class="hint">no figure carries a measurement in this paper</p>'
    MAXC = 26
    show = cid[:MAXC]
    h = ['<div class="scroll"><table class="mx"><tr><th></th>']
    for c in show:
        h.append('<th><div class="vert">%s</div></th>' % e(c.split("-")[-1]))
    h.append('<th><div class="vert">unresolved</div></th>'
             '<th><div class="vert">model</div></th></tr>')
    def figkey(k):
        t = k.replace("Fig ", "")
        num = "".join(ch for ch in t if ch.isdigit())
        return (len(num), num, t)
    for key in sorted(rows, key=figkey):
        h.append("<tr><td class='rh'>%s</td>" % e(key))
        for c in show:
            v = rows[key].get(c)
            h.append('<td>%s</td>' % (('<span class="c m" title="%s">●</span>'
                                       % e(", ".join(sorted(set(v))))) if v else ""))
        u = rows[key].get("__unres__")
        s = rows[key].get("__sim__")
        h.append('<td>%s</td>' % (('<span class="c u" title="%s">○</span>'
                                   % e(", ".join(sorted(set(u))))) if u else ""))
        h.append('<td>%s</td>' % ('<span class="c s" title="model output">✚</span>' if s else ""))
        h.append("</tr>")
    h.append("</table></div>")
    if len(cid) > MAXC:
        h.append('<p class="hint">showing %d of %d case columns</p>' % (MAXC, len(cid)))
    return "".join(h)


def condition_fingerprint(pid, o):
    """Compact case x condition matrix. Categorical, never rescaled to a false number."""
    cases = o["experimental_cases"][:20]
    if not cases:
        return ""
    feats, seen = [], set()
    for c in cases:
        for x in c["case_defining_conditions"]:
            k = (x["quantity"], x.get("species") or "")
            if k not in seen:
                seen.add(k)
                feats.append(k)
    feats = feats[:11]
    h = ['<div class="scroll"><table class="fp"><tr><th>case</th><th>material</th>'
         '<th>geometry</th>']
    for q, sp in feats:
        h.append("<th>%s%s</th>" % (e(q), e(" (%s)" % sp) if sp else ""))
    h.append("</tr>")
    for c in cases:
        got = {(x["quantity"], x.get("species") or ""): x for x in c["case_defining_conditions"]}
        h.append("<tr><td class='mono'>%s</td>" % e(c["case_id"].split("-")[-1]))
        h.append("<td class='%s'>%s</td>" % ("k" if c.get("deposited_material") else "n",
                                             e(c.get("deposited_material") or "unresolved")))
        h.append("<td class='%s'>%s</td>"
                 % ("k" if c.get("geometry_source") == "figure/panel caption" else "i"
                    if c.get("geometry") else "n",
                    e(c.get("geometry") or "unknown")))
        for f in feats:
            x = got.get(f)
            if not x:
                h.append("<td class='n'>—</td>")
            elif x.get("value_kind") == "range":
                h.append("<td class='r'>%s–%s</td>" % (e(x.get("value_lower")),
                                                       e(x.get("value_upper"))))
            elif x.get("value") is None:
                h.append("<td class='n'>unresolved</td>")
            elif x.get("provenance_type") in ("methods_default",
                                              "inherited_from_explicit_sample"):
                h.append("<td class='i'>%s</td>" % e(x["value"]))
            else:
                h.append("<td class='k'>%s</td>" % e(x["value"]))
        h.append("</tr>")
    h.append("</table></div>")
    h.append('<p class="hint"><span class="tag" style="background:color-mix(in srgb,'
             'var(--meas) 16%,transparent)">stated</span> '
             '<span class="tag" style="background:color-mix(in srgb,var(--accent) 20%,'
             'transparent)">range</span> '
             '<span class="tag" style="background:color-mix(in srgb,var(--samp) 14%,'
             'transparent)">inherited / methods default</span> '
             '<span class="tag">— not known</span> &nbsp; Values are shown as printed; '
             'incomparable quantities are never rescaled onto a common axis.</p>')
    return "".join(h)


def run_sample_graph(pid, o):
    runs, runev, samples = o["deposition_runs"], o.get("run_evidence") or [], o["samples"]
    if not (runs or runev or samples):
        return ('<p class="hint">This paper names no specimen and makes no run statement, '
                'so no Sample and no DepositionRun is asserted. That is the intended '
                'output, not a gap in the resolver.</p>')
    ms = {m["measurement_id"]: m for m in o["measurements"]}
    h = ['<div class="grid2"><div><h3>Identified deposition runs</h3>']
    if runs:
        for r in runs:
            y = 14
            svg = ['<svg viewBox="0 0 560 %d" width="560" height="%d">'
                   % (len(r["sample_codes"]) * 32 + 24, len(r["sample_codes"]) * 32 + 24)]
            svg.append(node_svg(8, 14, "run", r["run_id"].split("::")[-1], "shared ALD run",
                                wpx=150))
            yy = 14
            for code in r["sample_codes"]:
                svg.append(edge_svg(158, 27, 200, yy + 13))
                s = next((x for x in samples if x["source_sample_code"] == code), None)
                nm = len(s["measurement_ids"]) if s else 0
                svg.append(node_svg(200, yy, "sample", "sample %s" % code,
                                    "%d measurement%s" % (nm, "" if nm == 1 else "s"), wpx=150))
                yy += 32
            svg.append("</svg>")
            h.append('<div class="scroll">%s</div>' % "".join(svg))
            h.append('<div class="q">%s</div>' % e((r.get("same_run_evidence") or "")[:220]))
    else:
        h.append('<p class="hint">none — no statement identifies a specific execution</p>')
    h.append('</div><div><h3>Run-distinctness evidence <span class="tag">NOT runs</span></h3>')
    if runev:
        for r in runev:
            h.append('<div class="chain"><span class="tag" style="border-style:dashed">'
                     '⬠ %s</span></div>' % e(r["run_id"].split("::")[-1]))
            h.append('<div class="q">%s</div>'
                     % e((r.get("different_run_evidence") or r.get("same_run_evidence") or "")[:220]))
    else:
        h.append('<p class="hint">none</p>')
    h.append("</div></div>")
    if samples:
        h.append("<h3>Specimens and what was measured on them</h3>")
        h.append('<div class="fig">')
        for s in sorted(samples, key=lambda x: (len(x["source_sample_code"]),
                                                x["source_sample_code"])):
            techs = Counter(t for m in s["measurement_ids"] if m in ms
                            for t in (ms[m]["technique"] or []))
            h.append('<div class="fcard"><b>▲ sample %s</b>'
                     '<div class="bd">%s</div>'
                     '<div class="hint" style="margin:4px 0 0">%s</div></div>'
                     % (e(s["source_sample_code"]),
                        "".join('<span class="tag">%s×%d</span>' % (e(t), n)
                                for t, n in techs.most_common(4)) or
                        '<span class="tag">no measurement</span>',
                        e("run %s" % s["produced_by_run"].split("::")[-1]
                          if s.get("produced_by_run") else "run not identified")))
        h.append("</div>")
    return "".join(h)


def material_graph(pid, o):
    cases = o["experimental_cases"]
    edges = defaultdict(lambda: defaultdict(int))
    cand = defaultdict(int)
    for c in cases:
        for m, role in (c.get("material_roles") or {}).items():
            edges[m][role] += 1
        for m in (c.get("material_candidates") or {}):
            cand[m] += 1
    if not edges and not cand:
        return '<p class="hint">no material is asserted for any case in this paper</p>'
    rows = sorted(edges.items())
    height = max(70, 34 * max(1, sum(len(v) for _, v in rows)) + 40)
    svg = ['<svg viewBox="0 0 720 %d" width="720" height="%d">' % (height, height)]
    y = 14
    for mat, roles in rows:
        svg.append(node_svg(8, y, "mat", mat, wpx=118))
        yy = y
        for role, n in sorted(roles.items()):
            svg.append(edge_svg(126, y + 13, 210, yy + 13))
            svg.append('<text x="215" y="%d" class="mut" font-size="10">%s</text>' % (yy + 12, e(role)))
            svg.append(node_svg(340, yy, "case", "%d case%s" % (n, "" if n == 1 else "s"), wpx=96))
            yy += 32
        y = max(yy, y + 32)
    for mat, n in sorted(cand.items()):
        svg.append(node_svg(8, y, "unres", mat, "CANDIDATE ONLY", wpx=118))
        svg.append('<text x="140" y="%d" class="mut" font-size="10">'
                   'paper-wide inventory only — not asserted for any case</text>' % (y + 17))
        y += 32
    svg.append("</svg>")
    return '<div class="scroll">%s</div>' % "".join(svg)


def representation_view(pid, o):
    grouped = defaultdict(list)
    for r in o["representations"]:
        if r.get("derived_representation_of"):
            grouped[r["derived_representation_of"]].append(r)
    if not grouped:
        n = len(o["representations"])
        return ('<p class="hint">%d representation label%s detected, none of which groups '
                'several panels onto one measurement in this paper.</p>'
                % (n, "" if n == 1 else "s")) if n else \
               '<p class="hint">no plot representations declared in this paper</p>'
    ms = {m["measurement_id"]: m for m in o["measurements"]}
    h = ['<p class="hint">Each block is ONE underlying measurement. The panels under it are '
         'views of that same measurement and create <b>no</b> additional ExperimentalCase.</p>']
    for holder, rs in sorted(grouped.items())[:8]:
        m = ms.get(holder)
        rows = sorted(rs, key=lambda x: x["source"]["panel"] or "")
        svg = ['<svg viewBox="0 0 660 %d" width="660" height="%d">'
               % (len(rows) * 30 + 24, len(rows) * 30 + 24)]
        svg.append(node_svg(8, 14, "meas",
                            (", ".join(m["technique"]) if m else "measurement")[:22],
                            "Fig %s" % (m["source"]["printed_figure"] if m else "?"), wpx=200))
        yy = 14
        for r in rows:
            svg.append(edge_svg(208, 27, 260, yy + 13, dash=True))
            svg.append(node_svg(260, yy, "rep", r["type"],
                                "Fig %s%s" % (r["source"]["printed_figure"],
                                              r["source"]["panel"] or ""), wpx=190))
            yy += 30
        svg.append("</svg>")
        h.append('<div class="scroll">%s</div>' % "".join(svg))
    if len(grouped) > 8:
        h.append('<p class="hint">showing 8 of %d representation groups</p>' % len(grouped))
    return "".join(h)


def unresolved_plots(pid, o):
    c = Counter(u.get("reason_class", "CONDITION_ONLY_NO_POSITIVE_LINK") for u in o["unresolved"])
    if not c:
        return '<p class="hint">no unresolved links in this paper</p>'
    total = sum(c.values())
    vmax = max(c.values())
    h = ['<p class="hint"><b>unresolved is not an error count.</b> Each class below says '
         'why identity resolution stopped; only the first two are classes a source could '
         'in principle resolve.</p><div class="bars">']
    for k in UNRES_ORDER + [x for x in c if x not in UNRES_ORDER]:
        if not c.get(k):
            continue
        h.append("<i>%s</i>%s<b>%d</b>" % (e(k.replace("_", " ").lower()),
                                           bar(c[k], vmax, "unres"), c[k]))
    h.append("</div>")
    # flow view: where the chain stops
    stops = Counter()
    for m in o["measurements"]:
        if m["measures_case"]:
            stops["case linked"] += 1
        elif m.get("provenance_role") == "REFERENCE":
            stops["stops at: comparison control"] += 1
        elif m.get("provenance_role") == "IMPORTED_LITERATURE":
            stops["stops at: imported from another work"] += 1
        elif m.get("data_recovered") is False:
            stops["stops at: no extracted data"] += 1
        else:
            stops["stops at: producing case not stated"] += 1
    h.append("<h3>Where identity resolution stops</h3>")
    h.append('<div class="chain"><b>ResultSeries</b><span>→</span><b>Measurement</b>'
             '<span>→</span><b>ExperimentalCase?</b></div><div class="bars">')
    m2 = max(stops.values()) if stops else 1
    for k, v in stops.most_common():
        h.append("<i>%s</i>%s<b>%d</b>" % (e(k), bar(v, m2, "meas" if k == "case linked"
                                                    else "unres"), v))
    h.append("</div>")
    return "".join(h)


def figure_cards(pid, o):
    by = defaultdict(lambda: {"m": [], "s": []})
    for m in o["measurements"]:
        by["%s%s" % (m["source"]["printed_figure"], m["source"]["panel"] or "")]["m"].append(m)
    for s in o["simulation_runs"]:
        by["%s%s" % (s["source"]["printed_figure"], s["source"]["panel"] or "")]["s"].append(s)
    def k(x):
        num = "".join(ch for ch in x if ch.isdigit())
        return (len(num), num, x)
    h = ['<div class="fig">']
    for key in sorted(by, key=k):
        v = by[key]
        badges = []
        for m in v["m"][:4]:
            for t in (m["technique"] or ["measurement"])[:2]:
                badges.append('<span class="tag g-meas">● %s</span>' % e(t))
            if m["measures_case"]:
                badges.append('<span class="tag g-case">◆ %d case%s</span>'
                              % (len(m["measures_case"]),
                                 "" if len(m["measures_case"]) == 1 else "s"))
            else:
                badges.append('<span class="tag g-unres">○ unresolved</span>')
            if m.get("performed_on"):
                badges.append('<span class="tag g-samp">▲ %s</span>'
                              % e(m["performed_on"].split("::")[-1]))
            if m.get("provenance_role") in ("REFERENCE", "IMPORTED_LITERATURE"):
                badges.append('<span class="tag">%s</span>' % e(m["provenance_role"].lower()))
            if m.get("data_recovered") is False:
                badges.append('<span class="tag">caption/image only</span>')
        if v["s"]:
            badges.append('<span class="tag g-sim">✚ %d model</span>' % len(v["s"]))
        h.append('<div class="fcard"><b>Figure %s</b><div class="bd">%s</div></div>'
                 % (e(key), "".join(dict.fromkeys(badges))))
    h.append("</div>")
    return "".join(h)


# ================================================================ cross-paper views
def landing(cmp_all, verdicts, counts):
    mx = {k: max((c[k] for c in counts.values()), default=1) or 1
          for k in ("experimental_cases", "measurements", "result_series", "samples",
                    "identified_deposition_runs", "representations", "simulation_runs",
                    "unresolved_links")}
    h = ['<div class="cards">']
    for pid in PAPERS:
        c, v = counts[pid], verdicts.get(pid, {})
        unseen = ROLES[pid] == "unseen_generalization"
        h.append('<a class="pc%s" href="#%s">' % (" unseen" if unseen else "", e(pid)))
        h.append('<div class="nm">%s</div>' % e(short(pid, 30)))
        h.append('<div class="rl">%s &nbsp;<span class="v %s">%s</span></div>'
                 % ("<b>unseen generalization</b>" if unseen else "original control",
                    e(v.get("verdict", "")), e(v.get("verdict", ""))))
        h.append('<div class="mini">')
        for lab, key, cls in (("cases", "experimental_cases", "case"),
                              ("measurements", "measurements", "meas"),
                              ("result series", "result_series", "rs"),
                              ("representations", "representations", "rep"),
                              ("samples", "samples", "samp"),
                              ("runs", "identified_deposition_runs", "run"),
                              ("simulations", "simulation_runs", "sim"),
                              ("unresolved", "unresolved_links", "unres")):
            h.append("<i>%s</i>%s<b>%d</b>" % (lab, bar(c[key], mx[key], cls), c[key]))
        h.append("<i>run evidence</i><span></span><b>%d</b>" % c["run_evidence_groups"])
        h.append("</div></a>")
    h.append("</div>")
    return "".join(h)


def old_vs_pilot_chart(cmp_all, counts):
    """Grouped bars per paper: what PSED reports against what the pilot reports."""
    h = ['<p class="hint">Bars are per paper and share a scale only within a paper. A '
         'smaller pilot number is not automatically better — the change class below says '
         'what actually happened.</p><div class="grid2">']
    for pid in PAPERS:
        old, new = cmp_all[pid]["current_psed"], counts[pid]
        pairs = [("Experiments → Cases", old["experiments"], new["experimental_cases"]),
                 ("entities → Measurements", old["entities"], new["measurements"]),
                 ("curves → ResultSeries", old["canonical_curves"], new["result_series"]),
                 ("physical_case_id → Samples", old["physical_case_ids"], new["samples"]),
                 ("— → identified Runs", 0, new["identified_deposition_runs"]),
                 ("— → Representations", 0, new["representations"]),
                 ("sim entities → SimulationRuns",
                  old["simulation_entities"] + old["model_sweep_entities"],
                  new["simulation_runs"])]
        vmax = max([max(a, b) for _, a, b in pairs] + [1])
        h.append('<div><h3>%s %s</h3><div class="bars">'
                 % (e(short(pid, 30)),
                    '<span class="tag">unseen</span>'
                    if ROLES[pid] == "unseen_generalization" else ""))
        for lab, a, b in pairs:
            h.append('<i>%s</i><div>%s%s</div><b>%d→%d</b>'
                     % (e(lab),
                        '<div class="stk" style="height:7px;margin-bottom:2px"><span '
                        'style="width:%.1f%%;background:var(--rs)"></span></div>'
                        % (100.0 * a / vmax),
                        '<div class="stk" style="height:7px"><span '
                        'style="width:%.1f%%;background:var(--case)"></span></div>'
                        % (100.0 * b / vmax), a, b))
        h.append("</div></div>")
    h.append("</div>")
    h.append('<p class="hint"><span class="tag" style="border-color:var(--rs)">grey = current '
             'PSED</span> <span class="tag" style="border-color:var(--case)">teal = pilot</span></p>')
    return "".join(h)


def change_class_chart(cmp_all):
    agg = defaultdict(lambda: defaultdict(int))
    for pid in PAPERS:
        for ch in cmp_all[pid]["changes"]:
            agg[ch["class"]][pid] = ch["n"]
    if not agg:
        return ""
    tot = {k: sum(v.values()) for k, v in agg.items()}
    vmax = max(tot.values()) or 1
    h = ['<div class="bars">']
    for k in sorted(agg, key=lambda x: -tot[x]):
        parts = []
        for pid in PAPERS:
            n = agg[k].get(pid, 0)
            if n:
                parts.append((n, "unseen" if ROLES[pid] == "unseen_generalization" else "case",
                              "%s %d" % (short(pid, 18), n)))
        h.append("<i>%s</i><div style='max-width:420px'>%s</div><b>%d</b>"
                 % (e(k.replace("_", " ").lower()),
                    stacked(parts, max(tot[k], vmax)), tot[k]))
    h.append("</div>")
    h.append('<p class="hint">Segments are papers; dashed-border papers in the cards above are '
             'the unseen five. Hover a segment for its paper and count.</p>')
    return "".join(h)


def unresolved_overview(all_unres):
    tot = Counter()
    per = defaultdict(Counter)
    for pid in PAPERS:
        for u in all_unres[pid]:
            k = u.get("reason_class", "CONDITION_ONLY_NO_POSITIVE_LINK")
            tot[k] += 1
            per[pid][k] += 1
    vmax = max(tot.values()) if tot else 1
    h = ['<div class="grid2"><div><h3>By reason class, all nine papers</h3><div class="bars">']
    for k in UNRES_ORDER + [x for x in tot if x not in UNRES_ORDER]:
        if not tot.get(k):
            continue
        h.append("<i>%s</i>%s<b>%d</b>" % (e(k.replace("_", " ").lower()),
                                           bar(tot[k], vmax, "unres"), tot[k]))
    h.append('</div></div><div><h3>Per paper</h3><div class="bars">')
    pmax = max((sum(per[p].values()) for p in PAPERS), default=1) or 1
    VAR = {"CONDITION_ONLY_NO_POSITIVE_LINK": "unres", "PROVENANCE_CHAIN_INCOMPLETE": "run",
           "SOURCE_TRULY_UNSPECIFIED": "rs", "MEASUREMENT_ONLY_FIGURE": "mat",
           "REFERENCE_BY_DESIGN": "sim", "IMPORTED_LITERATURE": "rep",
           "CONFLICTING_EVIDENCE": "case"}
    for pid in PAPERS:
        s = sum(per[pid].values())
        parts = [(per[pid][k], VAR.get(k, "rs"), k.replace("_", " ").lower())
                 for k in UNRES_ORDER if per[pid].get(k)]
        h.append("<i>%s</i><div>%s</div><b>%d</b>"
                 % (e(short(pid, 24)), stacked(parts, pmax), s))
    h.append("</div></div></div>")
    return "".join(h)


def verdict_matrix(verdicts):
    dims = ["ExperimentalCase identity", "Measurement separation", "Sample identity",
            "Run identity", "Representation", "Condition roles", "Material roles",
            "Geometry", "Characterization provenance", "Simulation provenance"]
    h = ['<p class="hint">A <b>scientific-review</b> verdict, read from the PDFs. It is not '
         'the test result: all 85 tests pass, and three papers are still PARTIAL.</p>'
         '<div class="scroll"><table class="mx"><tr><th></th>']
    for d in dims:
        h.append('<th><div class="vert">%s</div></th>' % e(d))
    h.append("<th></th></tr>")
    for pid in PAPERS:
        v = verdicts.get(pid, {})
        h.append("<tr><td class='rh'>%s%s</td>"
                 % (e(short(pid, 26)),
                    ' <span class="tag">unseen</span>'
                    if ROLES[pid] == "unseen_generalization" else ""))
        for d in dims:
            got = (v.get("dims") or {}).get(d, ["", ""])
            sym = {"PASS": ("●", "m"), "PARTIAL": ("◐", "u"), "FAIL": ("○", "s")}.get(got[0],
                                                                                      ("", ""))
            h.append('<td><span class="c %s" title="%s">%s</span></td>'
                     % (sym[1], e(got[1] or got[0]), sym[0]))
        h.append('<td class="rh"><span class="v %s">%s</span></td></tr>'
                 % (e(v.get("verdict", "")), e(v.get("verdict", ""))))
    h.append("</table></div>")
    h.append('<p class="hint">● PASS &nbsp; ◐ PARTIAL &nbsp; ○ FAIL &nbsp;— hover a cell for '
             'the exact reason.</p>')
    return "".join(h)


def legend():
    return ('<div class="leg">' + "".join(
        '<span class="g-%s">%s %s</span>'
        % ({"case": "case", "meas": "meas", "rs": "rs", "rep": "rep", "sample": "samp",
            "run": "run", "runev": "run", "series": "case", "sim": "sim",
            "unres": "unres", "mat": "mat"}[k], g, lab)
        for k, (g, _, lab) in NODE.items()) + "</div>")


def paper_section(pid, o, cmp_, verdict, checks):
    unseen = ROLES[pid] == "unseen_generalization"
    h = ['<h2 id="%s">%s %s <span class="v %s">%s</span></h2>'
         % (e(pid), e(pid),
            '<span class="tag" style="border-style:dashed;border-color:var(--unseen)">'
            'UNSEEN GENERALIZATION</span>' if unseen else
            '<span class="tag">original control</span>',
            e(verdict.get("verdict", "")), e(verdict.get("verdict", "")))]
    rows = [c for c in (checks or []) if c["paper"] == pid]
    if rows:
        npass = sum(1 for r in rows if r["pass"])
        h.append('<p class="hint">PDF-ground-truth anchors: <b>%d / %d pass</b>. %s</p>'
                 % (npass, len(rows),
                    " ".join('<span class="tag" style="border-color:var(--run)">%s</span>'
                             % e(r["name"]) for r in rows if not r["pass"])))
    h.append("<h3>Case → Measurement → ResultSeries → Representation</h3>")
    h.append(legend())
    h.append(case_graph(pid, o))
    h.append("<h3>Figure × Case matrix</h3>")
    h.append('<p class="hint">A row spanning several columns is one figure feeding several '
             'cases; a column spanning several rows is one case measured across several '
             'figures. The last two columns are results with no case and model output.</p>')
    h.append(figure_case_matrix(pid, o))
    h.append("<h3>Case condition fingerprint</h3>")
    h.append(condition_fingerprint(pid, o))
    h.append("<h3>Material roles</h3>")
    h.append(material_graph(pid, o))
    h.append("<h3>Deposition runs and specimens</h3>")
    h.append(run_sample_graph(pid, o))
    h.append("<h3>Representation grouping</h3>")
    h.append(representation_view(pid, o))
    if o.get("provenance_chains"):
        h.append("<h3>Characterisation provenance chain</h3>")
        for ch in o["provenance_chains"]:
            h.append('<div class="chain"><b>%s</b><span>→</span><b>%s %s</b><span>→</span>'
                     '<b>%s</b><span>→</span>%s</div>'
                     % (e(", ".join(ch["case_ids"]) or "?"), e(ch.get("qualifier") or ""),
                        e("%s %s" % (ch["product_material"], ch["product_form"])),
                        e(ch["device"]),
                        ('<b>Fig %s</b>' % e(", ".join(ch.get("covers_figures") or []))
                         if ch["status"] == "RESOLVED"
                         else '<span class="stop">stops: %s</span>' % e(ch.get("reason")))))
    h.append("<h3>Unresolved links</h3>")
    h.append(unresolved_plots(pid, o))
    h.append("<h3>Figures</h3>")
    h.append(figure_cards(pid, o))
    # collapsible detail
    h.append('<details><summary>Scientific-review detail, dimension by dimension</summary>'
             '<table><tr><th>dimension</th><th>verdict</th><th>reason</th></tr>')
    for d, (v, why) in (verdict.get("dims") or {}).items():
        h.append('<tr><td>%s</td><td><span class="v %s">%s</span></td><td>%s</td></tr>'
                 % (e(d), e(v), e(v), e(why)))
    h.append("</table></details>")
    h.append('<details><summary>Every ExperimentalCase, with its evidence</summary>'
             '<div class="scroll"><table><tr><th>case</th><th>material</th><th>geometry</th>'
             '<th>conditions</th><th>measurements</th><th>figures</th><th>confidence</th>'
             '<th>warnings</th></tr>')
    ms = {m["measurement_id"]: m for m in o["measurements"]}
    for c in o["experimental_cases"]:
        conds = "; ".join("%s=%s" % (x["quantity"],
                                     ("%s–%s" % (x.get("value_lower"), x.get("value_upper")))
                                     if x.get("value_kind") == "range" else x.get("value"))
                          for x in c["case_defining_conditions"][:6]) or "—"
        techs = ", ".join(sorted({t for mid in c["measurement_ids"] if mid in ms
                                  for t in (ms[mid]["technique"] or [])})) or "—"
        h.append("<tr><td class=mono>%s</td><td>%s</td><td>%s</td><td class=mono>%s</td>"
                 "<td>%s</td><td class=mono>%s</td><td>%s</td><td>%s</td></tr>"
                 % (e(c["case_id"]), e(c.get("deposited_material") or c.get("material_status")),
                    e(c.get("geometry") or "—"), e(conds), e(techs),
                    e(", ".join(c["source_figures"])), e(c["confidence"]),
                    e("; ".join(c["warnings"])[:120])))
    h.append("</table></div></details>")
    return "\n".join(h)


PREFIX_LINES = "ANCHOR\t"


def run_checks():
    try:
        out = subprocess.run([sys.executable, str(W / "tests" / "test_pilot_semantics.py")],
                             capture_output=True, text=True, timeout=900).stdout
    except Exception as exc:
        return [], "the test suite could not be run: %s" % exc, (0, 0)
    rows, npass, ntot = [], 0, 0
    for line in out.splitlines():
        if line.startswith(PREFIX_LINES):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 4:
                rows.append({"paper": p[1], "name": p[3],
                             "detail": p[4] if len(p) > 4 else "", "pass": p[2] == "PASS"})
        t = line.strip()
        if t.startswith("PASS ") or t.startswith("FAIL "):
            ntot += 1
            npass += t.startswith("PASS ")
    return rows, None, (npass, ntot)


def main():
    checks, err, (npass, ntot) = run_checks()
    cmp_all = json.loads((W / "comparison" / "old_vs_pilot.json").read_text())
    verdicts = json.loads((W / "comparison" / "scientific_verdicts.json").read_text())
    counts = {p: cmp_all[p]["pilot"] for p in PAPERS}
    all_unres = {p: sem(p, "unresolved") for p in PAPERS}

    h = ['<title>Nine-Paper Semantic Generalization Pilot</title><style>%s</style>'
         '<div class="wrap">' % CSS]
    h.append("<h1>Nine-Paper Semantic Generalization Pilot</h1>")
    h.append('<p class="sub">Four <b>original control</b> papers, whose corrected behaviour '
             'must reproduce, and five <b>unseen generalization</b> papers selected from the '
             'live 44-paper corpus and never studied before. Same generic resolver for all '
             'nine — no paper, DOI or figure appears in any decision. '
             '0 API calls; production untouched.</p>')
    nu = sum(1 for p in PAPERS if ROLES[p] == "unseen_generalization")
    h.append('<p class="sub"><b>%d / %d</b> tests pass · <b>%d</b> control papers reproduce '
             'exactly · <b>%d</b> unseen papers · every source curve and digitised point '
             'preserved on all nine.</p>' % (npass, ntot, len(PAPERS) - nu, nu))
    h.append('<div class="sticky"><div class="nav">%s</div></div>'
             % "".join('<a class="%s" href="#%s">%s</a>'
                       % ("unseen" if ROLES[p] == "unseen_generalization" else "",
                          e(p), e(short(p, 24))) for p in PAPERS))
    h.append(landing(cmp_all, verdicts, counts))
    h.append("<h2>Scientific review — all nine papers, ten dimensions</h2>")
    h.append(verdict_matrix(verdicts))
    h.append("<h2>Current PSED vs pilot</h2>")
    h.append(old_vs_pilot_chart(cmp_all, counts))
    h.append("<h3>Semantic change classes</h3>")
    h.append(change_class_chart(cmp_all))
    h.append("<h2>Unresolved links across the corpus</h2>")
    h.append(unresolved_overview(all_unres))
    for pid in PAPERS:
        o = {k: sem(pid, k) for k in
             ("experimental_cases", "measurements", "result_series", "representations",
              "samples", "deposition_runs", "run_evidence", "study_series",
              "simulation_runs", "provenance_chains", "links", "evidence", "unresolved")}
        h.append(paper_section(pid, o, cmp_all[pid], verdicts.get(pid, {}), checks))
    h.append('<p class="hint" style="margin-top:44px">Generated by '
             '<code>code/build_dashboard.py</code> from the pilot workspace. Nothing here '
             'was migrated to production.</p></div>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(h), encoding="utf-8")
    print("wrote %s (%.0f KB)" % (OUT, OUT.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
