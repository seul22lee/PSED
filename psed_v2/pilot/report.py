#!/usr/bin/env python3
"""Writes reports/pilot.html, the one report page of the pilot (untracked; self-contained, works offline), with three tabs:
- Facts, per paper: (a) the paper in reading order, each element coloured covered / no knowledge / missed, click for its
  facts; (b) the tree as find (default), as experiment cards or as text. Find is the workbench, laid out after the v1
  scientific comparison workbench: left, filters (material, structure type, method, result quantity, paper, from
  lists.py and the paper keys; min and max for deposition temperature, process pressure, cycle number and exposure,
  compared in lists.UNITS after a unit conversion of the value as printed); middle, the runs of the three papers that
  pass every filter by their inherited settings (the nearest scope wins, as in the cards), one line each: paper, run
  label, the setting the run varies with its value, an add button; right, a tray of at most eight runs or curves, and
  the compare panel for it: (a) an overlay plot of the tray's curves that share a quantity and an abscissa (the x=
  qualifier), with the y and x transforms of "Fig. 9 from tree" (S/N by the run's cycle number, S/S_plateau by its
  plateau thickness, x/H by its feature height, each value inherited from the tree; a curve without the value is
  listed, not drawn; curves on another axis are listed); (b) a condition table, one column per tray item, one row per
  inherited setting, the settings equal across the tray collapsed into one line of chips; "not stated" in grey, never a
  difference; (c) one verdict per pair: direct when the two share a result with the same quantity and qualifiers,
  transformable when a transform with the settings both have reaches a common quantity and abscissa, else not
  comparable, with the reason in one line (the first differing qualifier key, or the setting one item lacks), and the
  settings the pair differs in. Run and figure cards carry an add-to-tray button (a figure card adds its curves with
  points, else the runs it draws on) and a link to the tray; the run card's compare row (a run picker, siblings first,
  and a compare button) opens the tray with the two runs. Cards: on the left the tree collapsed to
  groups and runs (one line each); clicking a run, or any fact anywhere in the page, opens its card on the right. Clicking a
  figure panel anywhere (the paper view, the figures view, a crop in an evidence box) opens the figure card instead: the
  groups it compares (each group's label carries its varied setting and values), the runs it draws on (chips to their
  cards), other figures and tables on the same runs, the claims linked to its facts, runs or groups. Group labels
  everywhere read "<label> — <varied setting> <values>, <runs>". A run card has five rows:
  1 what was varied (the setting that differs among the run's siblings, this run's value beside theirs; when the run's
  siblings differ in nothing, the first level up the tree where they do), 2 other conditions (every setting inherited up
  the tree as chips, the process-defining ones first: reactor, temperature, pressure, precursor purity and source
  temperature, pulse and purge times, feature height, cycles, substrate; marked where that level's siblings differ; one
  value stated at two levels is one chip; two lines until "+N more" opens the rest), 3 measured (the run's observation, derived and model
  facts grouped by figure, table or paragraph, element id click = the element and its crop in the evidence box, curves
  as sparklines, inferred film membership marked), 4 why and what it showed (the group's purpose fact, then the claims
  linked to the run or its group), 5 compare (a run picker, siblings first, and a button that opens the tray with the two runs).
  Every screen names a quantity by its short label from lists.LABELS ("TMA pulse", "PD50"; a curve "S vs x"); simulation
  runs are labelled "sim · H 100 nm" in the tree. Claim scope (computed, next to every claim on cards and in the claims
  view): the claim's links lead to runs (a linked run, the runs of a linked group, the run above a linked fact), the runs'
  inherited settings give the ranges: "3 runs · T 300 °C · H 100–2000 nm · N 500"; "no run" when the links reach none.
  Claims view (toggle beside find, cards and text tree): one line per claim of each paper, with its scope and evidence.
  Group card (a group's label in the left tree): what the group varies, its runs, and effect ÷ sd per result quantity:
  the effect is max − min of the quantity over the group's runs; sd comes from the paper's reproducibility set, computed
  as the largest set of runs with the same conditions (the process-defining settings stated by both and equal, any other
  setting equal when both state it) that share numeric results
  (yim20: samples 2, 8 and 12); a ratio below 1 is flagged "within reproducibility"; no set, no sd. Natural series
  (computed): two runs of a paper that differ in exactly one inherited setting (stated by both, different; both stating the
  same process-defining settings) are joined; the
  runs so connected through one setting form a series, listed in the left tree beside the paper's groups (a line opens the
  tray with the series) and on the group card; a paper group whose runs differ in more than one setting is marked as
  confounded, with the run that deviates (Series E: sample 14 also differs in pillar layout). The tray is the one
  selection: its runs are highlighted in the left tree, the text tree, the figures view (panels with a fact on a tray run)
  and the forest scatter (points whose scope is a tray run). User facts (user.facts.csv, author user): a user claim is
  listed in the claims view under "user" with a scope computed across the papers its links reach; a user claim with a
  quantity and an x= qualifier is a forest preset button (its label_as_printed), replacing the hard-coded Case 9 and 10.
  Text tree: the paper as one collapsible tree (root -> process -> groups -> runs -> facts; claims and cited works as
  branches), one line per node with statement, value and element id (click = the element and its crop); among sibling
  runs only the settings that differ are bold; expanding a claim shows its linked facts; (c) figures: each panel's crop
  next to its facts. Tree rows (ids without "#") are not counted as facts anywhere. Above the trees, the forest: a quantity
  picker highlights every numeric leaf of that quantity in all three trees (cited works included) and draws one scatter of
  them (x = a chosen quantity taken from the leaf's nearest scope, forest.context; colour = paper; hollow = cited; a leaf
  whose qualifiers or unit differ from the majority is flagged with the differing key). In the tree, qualifiers are grey
  badges, red only on the picked quantity's leaves where the forest flags them; a curve the figure shows but that has no points (a fact citing a panel,
  with no points and no value, not the panel's first fact, whose statement names a curve, series, trace, spectrum or
  pattern in lowercase) is dimmed. Preset "Fig. 9 from tree" (yim20): the Fig. 9a/9d points of each curve with H, N, S_IIb,
  PD50 and x~50 inherited from the curve's run, replotted as S/N and S/S_IIb against x/H beside the paper's own 9b/9c and
  9e/9f crops, Table 1's x~50 (filled) and PD50/H (hollow) as markers (forest.fig9).
- Cases: the thirteen case studies (cases.py; Case 8 draws on cremers.py).
- Matrix: quantities per paper and papers x cases (matrix.py).

    python3 psed_v2/pilot/report.py

Embeds element texts and figure crops from ingest/final (and a page of the review PDF for the cases), so the page stays
out of git. Each tab is its own document in an iframe, so the three views keep their styles and scripts apart.
"""
import base64, csv, html, io, json, re, runpy, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import elements  # noqa: E402
import lists as L  # noqa: E402
from check import KEYS, summary  # noqa: E402
from forest import Forest, fig9  # noqa: E402


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


FOREST = Forest()
PAGE_FIELDS = FOREST.page_fields()


def paper(pid, key):
    els, rows = rd(HERE / f"{pid}.elements.csv"), rd(HERE / f"{pid}.facts.csv")
    facts = [r for r in rows if "#" in r["fact_id"]]
    tree = [r for r in rows if "#" not in r["fact_id"]]
    cov = {c["element_id"]: c for c in rd(HERE / f"{pid}.coverage.csv")}
    pts = json.loads((HERE / f"{pid}.points.json").read_text(encoding="utf-8")) if (HERE / f"{pid}.points.json").exists() else {}
    texts = elements.texts(pid)
    kinds = {e["element_id"]: e["kind"] for e in els}
    imgs = {}
    for e in els:
        if e["crop"] and e["crop"] not in imgs:
            p = V2 / "ingest/final" / pid / e["crop"]
            if p.exists():
                mime = "image/png" if p.suffix == ".png" else "image/jpeg"
                imgs[e["crop"]] = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    E = []
    for e in els:
        c = cov.get(e["element_id"], {})
        E.append(dict(id=e["element_id"], kind=e["kind"], sec=e["section"], loc=e["locator"], crop=e["crop"],
                      st=c.get("status", "missed"), why=c.get("reason", ""), nn=c.get("n_numbers", ""),
                      nr=c.get("n_numbers_reached", ""),
                      text=texts.get(e["element_id"], "") if e["kind"] != "panel" else ""))
    for f in facts:
        if f["points_ref"] in pts:
            f["points"] = pts[f["points_ref"]]["points"]
            f["xlab"], f["ylab"] = pts[f["points_ref"]]["x_label_as_printed"], pts[f["points_ref"]]["y_label_as_printed"]
        f.update(PAGE_FIELDS[key].get(f["fact_id"], {}))
        e0 = f["evidence"].split(";")[0]
        if (kinds.get(e0) == "panel" and not f["fact_id"].endswith("#1") and not f["points_ref"] and not (f["value"] or f["value_min"] or f["value_max"])
                and f["type"] in ("observation", "model") and re.search(r"\b(curve|series|traces?|spectrum|pattern)\b", f["statement"])):   # lowercase: "Series C" is a name
            f["nopts"] = True
    s = summary({e["element_id"]: e for e in els}, facts, list(cov.values())) if facts else {}
    out = dict(pid=pid, key=key, elements=E, facts=facts, tree=tree, imgs=imgs, summary=s, quantities=FOREST.quantities())
    if key == "yim20":
        out["demo"] = fig9(FOREST)
        out["demo"]["crops"] = fig9_crops(pid)
    return out


def fig9_crops(pid):
    """The 9b, 9c, 9e and 9f panels cut from the Fig. 9 image (a 2 x 3 grid; the cuts are approximate)."""
    from PIL import Image
    src = next((c for c in json.loads((V2 / "ingest/final" / pid / "structure.json").read_text(encoding="utf-8"))["captions"]
                if c["kind"] == "figure" and str(c.get("number")) == "9"), None)
    if not src:
        return {}
    im = Image.open(V2 / "ingest/final" / pid / src["images"][0]).convert("RGB")
    W, H = im.size
    x1, x2, ym = int(W * 0.33), int(W * 0.674), H // 2
    out = {}
    for k, box in (("b", (x1, 0, x2, ym)), ("c", (x2, 0, W, ym)), ("e", (x1, ym, x2, H)), ("f", (x2, ym, W, H))):
        buf = io.BytesIO(); im.crop(box).save(buf, "JPEG", quality=85)
        out[k] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return out


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot Facts Layer</title><style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--card:#fff;--cov:#d8eedb;--covb:#2e7d3a;--nk:#ecebe7;--nkb:#9a978f;
--miss:#f7d6d2;--missb:#b3261e;--acc:#1f5fa8;--sel:#fff3c4;--c0:#1f5fa8;--c1:#c0392b;--c2:#2e7d3a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#e8e6e1;--mut:#a3a19b;--line:#33352f;--card:#1f2123;
--cov:#1f3a25;--covb:#6cc37a;--nk:#2a2b2d;--nkb:#77756f;--miss:#4a1f1c;--missb:#ff8a80;--acc:#7fb0ef;--sel:#4a4226;--c0:#7fb0ef;--c1:#ff8a80;--c2:#6cc37a}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#e8e6e1;--mut:#a3a19b;--line:#33352f;--card:#1f2123;--cov:#1f3a25;--covb:#6cc37a;--nk:#2a2b2d;
--nkb:#77756f;--miss:#4a1f1c;--missb:#ff8a80;--acc:#7fb0ef;--sel:#4a4226;--c0:#7fb0ef;--c1:#ff8a80;--c2:#6cc37a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:center}
h1{font-size:17px;margin:0 12px 0 0}button,select,input{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:4px 9px}
button.on{border-color:var(--acc);color:var(--acc);font-weight:600}main{padding:12px 16px;max-width:1500px;margin:0 auto}
.sum{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 12px}.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 11px;min-width:120px}
.tile b{display:block;font-size:18px}.tile span{color:var(--mut);font-size:12px}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:14px}@media(max-width:900px){.wrap{grid-template-columns:1fr}}
.side{position:sticky;top:8px;align-self:start;max-height:96vh;overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}
.el{border-left:4px solid var(--nkb);background:var(--nk);margin:5px 0;padding:5px 8px;border-radius:4px;cursor:pointer;white-space:pre-wrap;word-break:break-word}
.el.covered{background:var(--cov);border-color:var(--covb)}.el.missed{background:var(--miss);border-color:var(--missb)}.el.sel{outline:2px solid var(--acc)}
.el .id{font:11px ui-monospace,monospace;color:var(--mut);margin-right:6px}.el.heading{font-weight:600}
table.grid{border-collapse:collapse;margin:6px 0 14px;font-size:12px}table.grid td{border:1px solid var(--line);padding:3px 5px;cursor:pointer;vertical-align:top}
td.covered{background:var(--cov)}td.missed{background:var(--miss)}td.nk{background:var(--nk)}
.fact{border:1px solid var(--line);border-radius:6px;padding:6px 8px;margin:6px 0;background:var(--card)}
.fact .t{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;color:var(--acc)}.fact .m{color:var(--mut);font-size:12px}
.fact code{font-size:11px}.lnk{color:var(--acc);cursor:pointer;text-decoration:underline}
.fl{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}table.ft{border-collapse:collapse;width:100%;font-size:12.5px}
table.ft th,table.ft td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}table.ft th{position:sticky;top:0;background:var(--bg)}
.panel{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;border-top:1px solid var(--line);padding:12px 0}
@media(max-width:900px){.panel{grid-template-columns:1fr}}.panel img{max-width:100%;border:1px solid var(--line);border-radius:4px;background:#fff}
.legend span{display:inline-block;padding:1px 8px;border-radius:4px;margin-right:6px;font-size:12px}
.nd{margin-left:16px;padding:1px 0;line-height:1.35}.nd.leaf{padding-left:14px}summary{cursor:pointer;list-style-position:outside}
.nd .ty{display:inline-block;min-width:34px;font:600 10px/1.5 ui-monospace,monospace;text-transform:uppercase;color:var(--mut);text-align:center;border:1px solid var(--line);border-radius:3px;padding:0 3px;margin-right:4px}
.nd .ty.run,.nd .ty.paper,.nd .ty.process,.nd .ty.group{color:var(--acc);border-color:var(--acc)}.nd .ty.claim{color:var(--covb);border-color:var(--covb)}
.nd .v{color:var(--acc)}.nd.vary>summary,.nd.vary{font-weight:650}.nd.linked{opacity:.85;border-left:2px dashed var(--line);margin-left:30px;padding-left:6px}
.nd code.ev{font-size:11px;color:var(--mut);cursor:pointer;margin-left:4px}.nd code.ev:hover{color:var(--acc);text-decoration:underline}
.nd.hl>summary,.nd.hl{background:var(--sel);border-radius:3px}.tree{margin-bottom:10px}.tree>details>summary{font-size:15px;font-weight:600}
.q{font:10px/1.4 ui-monospace,monospace;color:var(--mut);border:1px solid var(--line);border-radius:3px;padding:0 3px;margin-left:4px}
.q.red{color:var(--missb);border-color:var(--missb);font-weight:600}.nd.dim{opacity:.5}
#forest{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:10px}
svg.sc{width:100%;max-width:820px;height:auto;display:block}svg.sc text{font-size:11px;fill:var(--fg)}svg.sc .tk{fill:var(--mut);font-size:10px}svg.sc .gr{stroke:var(--line)}
svg.sc .pt{cursor:pointer}.sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle}
.demo{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;align-items:start;margin:6px 0 10px}.demo svg,.demo img{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:4px;background:#fff}
.demo .cap{font-size:11px;color:var(--mut);text-align:center;margin-top:2px}@media(max-width:1100px){.demo{grid-template-columns:repeat(3,minmax(0,1fr))}}
.wrap2{display:grid;grid-template-columns:340px minmax(0,1fr);gap:14px}@media(max-width:900px){.wrap2{grid-template-columns:1fr}}
.lt{max-height:84vh;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:6px 8px;background:var(--card);font-size:12.5px}.lt details{margin-left:10px}.lt summary{cursor:pointer;padding:1px 0}
.rl{cursor:pointer;padding:1px 4px;margin-left:10px;border-radius:4px}.rl:hover{background:var(--nk)}.rl.on{background:var(--sel);font-weight:600}
.card{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:10px 14px;font-size:13px}.card h2{margin:0 0 6px;font-size:16px}.card h2 button{font-size:12px;font-weight:400;padding:1px 8px;margin-left:6px}.card h2 .lnk{font-size:12px;font-weight:400}
.card section{border-top:1px solid var(--line);padding:7px 0}.card h4{margin:0 0 5px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--acc)}
.card .mg{margin:3px 0 6px}.card .mg b{font-size:12px}.card .fl2{margin:2px 0 2px 10px;line-height:1.4}
.chip{display:inline-block;background:var(--nk);border:1px solid var(--line);border-radius:4px;padding:0 5px;margin:2px 3px 2px 0;line-height:18px;vertical-align:top;cursor:pointer;font-size:11.5px}.chip.diff{background:var(--sel);border-color:#d9b94a;font-weight:600}
.pchips{position:relative;overflow:hidden;max-height:48px;line-height:24px}.pchips.open{max-height:none}.num{display:inline-block;border-radius:3px;padding:0 4px;color:var(--acc);font-weight:600}
.spw{display:inline-block;vertical-align:middle;margin-right:4px}svg.sp{width:70px;height:20px;display:block}.evbox{margin-top:8px;padding:8px;border:1px dashed var(--line);border-radius:6px;max-height:50vh;overflow:auto}
.card code.ev{font-size:11px;color:var(--mut);cursor:pointer;margin-left:4px}.card code.ev:hover{color:var(--acc);text-decoration:underline}.sib{cursor:pointer;color:var(--acc);text-decoration:underline}
.card img.fig{max-width:100%;max-height:240px;cursor:pointer;border:1px solid var(--line);border-radius:4px;background:#fff;display:block;margin:4px 0}
.gd{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--nkb)}tr.rr{cursor:pointer}tr.rr:hover td{background:var(--nk)}.chip b{cursor:pointer;margin-left:3px}
.wb{display:grid;grid-template-columns:220px minmax(0,1fr) minmax(440px,1.25fr);gap:12px;align-items:start}@media(max-width:1100px){.wb{grid-template-columns:1fr}}
.wbf{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:8px 10px;font-size:12px}.wbf label{display:block;margin:4px 0}.wbf select{width:100%;margin-top:2px}.wbf input[type=number]{width:44%;margin-top:2px}
.wbm{max-height:84vh;overflow:auto;border:1px solid var(--line);border-radius:8px;background:var(--card);padding:6px 8px;font-size:12.5px}.wbr{display:flex;gap:6px;align-items:center;padding:2px 0;border-bottom:1px solid var(--line)}.wbr .mut{flex:1}.wbr button{padding:0 7px;font-size:11px}
.wbt{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:8px 10px;font-size:12.5px;margin-bottom:10px}
.rl.tray,.nd.tray{box-shadow:inset 3px 0 0 var(--acc)}.panel.tray{background:var(--sel);border-radius:6px}circle.pt.tray{stroke-width:4}
.ns .rl{cursor:pointer}.gl{cursor:pointer}.gl.on{background:var(--sel);border-radius:3px;padding:0 3px}.within{opacity:.75}
.cl{max-height:84vh;overflow:auto}.cl h3{margin:8px 0 4px}.clr{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap;padding:3px 0;border-bottom:1px solid var(--line);font-size:12.5px}.clr .st{flex:1;min-width:240px}.scope{font-size:11px;white-space:nowrap}
.wbt svg.ov{width:100%;max-width:560px;height:auto;display:block}table.cmp{font-size:12px}table.cmp th{font-weight:600}table.cmp td,table.cmp th{white-space:nowrap}.vd b.ok{color:var(--covb)}.vd b.tr{color:var(--acc)}.vd b.no{color:var(--missb)}
.inf{font:600 10px/1.4 ui-monospace,monospace;color:var(--missb);border:1px solid var(--missb);border-radius:3px;padding:0 3px;margin-left:4px}
h2{font-size:15px;margin:16px 0 6px}h3{font-size:14px;margin:10px 0 4px}.mut{color:var(--mut)}svg.pts{width:100%;height:150px;background:var(--card);border:1px solid var(--line);border-radius:4px}
</style></head><body>
<header><h1>Facts layer: pilot papers</h1><span id="papers"></span><span id="views"></span>
<span class="legend"><span style="background:var(--cov)">covered</span><span style="background:var(--nk)">no knowledge</span><span style="background:var(--miss)">missed</span></span></header>
<main><div class="sum" id="sum"></div><div id="view"></div></main>
<script>
const DATA=__DATA__;const LISTS=__LISTS__;const USER=__USER__;
let P=0,V="tree",SP=0;
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const clean=s=>esc(String(s||"").replace(/\\text\{([^}]*)\}|\\mathrm\{([^}]*)\}/g,"$1$2").replace(/<\/?sup>/g,"").replace(/\$/g,""));
function factsOf(d,id){return d.facts.filter(f=>f.evidence.split(";").includes(id))}
function factHTML(f,pi){pi=pi===undefined?SP:pi;const q=[f.quantity&&(f.quantity+(f.label_as_printed?` (${f.label_as_printed})`:"")),f.qualifiers].filter(Boolean).join(" · ");
 const v=[f.censor+f.value,f.value_min&&f.value_max?`${f.value_min}–${f.value_max}`:(f.value_min||f.value_max)].filter(Boolean).join(" ");
 return `<div class="fact" style="cursor:pointer" title="open the run's card" onclick="cardFor('${f.fact_id}',${pi})"><div class="t">${esc(f.type)} <code class="mut">${esc(f.fact_id)}</code></div><div>${esc(f.statement)}</div>
 <div class="m">${q?esc(q):""}${v?` = <b>${esc(v)} ${esc(f.unit)}</b>`:f.value_text?` = <b>${esc(f.value_text)}</b>`:""}${f.data_kind?` · ${esc(f.data_kind)}`:""}${f.method?` · ${esc(f.method)}`:""}${f.points_ref?` · ${f.points?f.points.length:"?"} points`:""}</div>
 ${f.mentions?`<div class="m">mentions: ${esc(f.mentions)}</div>`:""}${f.inputs?`<div class="m">inputs: ${esc(f.inputs)}</div>`:""}
 <div class="m">evidence: ${f.evidence.split(";").map(e=>`<span class="lnk" onclick="event.stopPropagation();goto('${e}')">${e}</span>`).join(", ")}</div>${f.points?plot(f.points):""}</div>`}
function plot(p){if(!p.length)return"";const xs=p.map(a=>a[0]),ys=p.map(a=>a[1]);const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
 const X=x=>8+284*(x-x0)/((x1-x0)||1),Y=y=>142-134*(y-y0)/((y1-y0)||1);
 return `<svg class="pts" viewBox="0 0 300 150"><polyline fill="none" stroke="var(--acc)" stroke-width="1.5" points="${p.map(a=>X(a[0])+","+Y(a[1])).join(" ")}"/>
 <text x="8" y="12" font-size="9" fill="var(--mut)">y ${y0}…${y1}; x ${x0}…${x1}</text></svg>`}
function side(id,pi){if(pi!==undefined)SP=pi;else SP=P;const d=DATA[SP],e=d.elements.find(x=>x.id===id);if(!e)return;document.querySelectorAll(".sel").forEach(x=>x.classList.remove("sel"));
 document.querySelectorAll(`[data-id="${id}"]`).forEach(x=>x.classList.add("sel"));const fs=factsOf(d,id);
 $("#side").innerHTML=`<h3>${esc(id)} <span class="mut">${esc(e.loc)}</span></h3><div class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""}${e.nn!==""?` · numbers ${e.nr}/${e.nn} reach a fact`:""}</div>
 ${e.crop&&d.imgs[e.crop]&&e.kind==="panel"?`<img src="${d.imgs[e.crop]}" style="max-width:100%;margin-top:6px;cursor:pointer" title="figure card" onclick="figCard('${id}',${SP})">`:""}${fs.map(factHTML).join("")||""}`}
function goto(id){P=SP;V="read";render();setTimeout(()=>{const n=document.querySelector(`[data-id="${id}"]`);if(n)n.scrollIntoView({block:"center"});side(id,P)},0)}
function readView(d){let h="",tabs={};const els=d.elements;
 for(const e of els){if(e.kind==="table_cell"){(tabs[e.sec]=tabs[e.sec]||[]).push(e);continue}
  const cls=e.st==="covered"?"covered":e.st==="missed"?"missed":"";
  if(e.kind==="panel"){h+=`<div class="el ${cls}" data-id="${e.id}" onclick="figCard('${e.id}',P)"><span class="id">${e.id}</span><i>panel ${esc(e.loc)}</i></div>`;continue}
  if(e.id.endsWith(".cap")&&e.id.startsWith("tab")){h+=`<div class="el ${cls}" data-id="${e.id}" onclick="side('${e.id}')"><span class="id">${e.id}</span>${clean(e.text)}</div>`+`@@${e.id.slice(0,-4)}@@`;continue}
  h+=`<div class="el ${cls} ${e.kind}" data-id="${e.id}" onclick="side('${e.id}')"><span class="id">${e.id}</span>${clean(e.text)}</div>`}
 const grid=t=>{const cs=tabs[t]||[];const R={};for(const c of cs){const m=c.id.match(/r(\d+)c(\d+)$/);(R[m[1]]=R[m[1]]||{})[m[2]]=c}
  const nc=Math.max(0,...cs.map(c=>+c.id.match(/c(\d+)$/)[1]))+1;
  return `<div style="overflow-x:auto"><table class="grid">${Object.keys(R).sort((a,b)=>a-b).map(r=>"<tr>"+Array.from({length:nc},(_,j)=>{const c=R[r][j];
   return c?`<td class="${c.st==="covered"?"covered":c.st==="missed"?"missed":"nk"}" data-id="${c.id}" onclick="side('${c.id}')">${clean(c.text)}</td>`:"<td></td>"}).join("")+"</tr>").join("")}</table></div>`};
 for(const t of Object.keys(tabs)){if(h.includes(`@@${t}@@`))h=h.replace(`@@${t}@@`,grid(t));else h+=`<h3>${t} (no caption)</h3>`+grid(t)}
 return `<div class="wrap"><div>${h.replace(/@@[^@]+@@/g,"")}</div><div class="side" id="side"><span class="mut">Click an element to see its facts.</span></div></div>`}
const ORDER={paper:-1,process:0,group:1,run:2,setting:3,observation:4,derived:5,model:6,definition:7,claim:8,cited:9};
const valStr=f=>{const v=[f.censor+f.value,f.value_min&&f.value_max?`${f.value_min}–${f.value_max}`:(f.value_min||f.value_max)].filter(Boolean).join(" ");return v?v+(f.unit?" "+f.unit:""):(f.value_text||"")};
const skey=f=>f.quantity+"|"+f.qualifiers+"|"+(f.quantity==="other"?f.label_as_printed:"");
function buildTree(d){if(d._T)return d._T;const byId={},kids={};[...d.tree,...d.facts].forEach(n=>{byId[n.fact_id]=n;if(n.parent)(kids[n.parent]=kids[n.parent]||[]).push(n)});
 for(const k in kids)kids[k].sort((a,b)=>(ORDER[a.type]??5)-(ORDER[b.type]??5));
 const vary=new Set();                                   // among sibling runs, the settings whose value differs or is missing in a sibling
 for(const k in kids){const runs=kids[k].filter(n=>n.type==="run");if(runs.length<2)continue;
  const per=runs.map(r=>{const m={};(kids[r.fact_id]||[]).filter(f=>f.type==="setting").forEach(f=>{m[skey(f)]=(m[skey(f)]?m[skey(f)]+"; ":"")+valStr(f)});return m});
  const keys=new Set(per.flatMap(m=>Object.keys(m)));
  for(const key of keys){if(new Set(per.map(m=>m[key]??"∅")).size>1)runs.forEach(r=>(kids[r.fact_id]||[]).forEach(f=>{if(f.type==="setting"&&skey(f)===key)vary.add(f.fact_id)}))}}
 const root=d.tree.find(n=>n.type==="paper");const up={};[...d.tree,...d.facts].forEach(n=>up[n.fact_id]=n.parent);
 const T=d._T={byId,kids,vary,root,up};
 d.tree.filter(n=>n.type==="group").forEach(g=>{let sib=(kids[g.fact_id]||[]).filter(k=>k.type==="run"||k.type==="group");   // "<label> — <varied setting> <values>, <runs>"
  if(sib.length===1&&sib[0].type==="run"){const ch=(kids[sib[0].fact_id]||[]).filter(k=>k.type==="run");if(ch.length)sib=ch}   // one deposition run with its specimens: the specimens
  const v=variedAmong(T,sib);
  const who=sib.length<=4?sib.map(k=>k.label_as_printed||k.fact_id.split(":").slice(1).join(":")).join(" · "):`${sib.length} ${sib.every(k=>k.type==="group")?"groups":"runs"}`;
  g.glab=`${g.label_as_printed||g.fact_id.split(":").slice(1).join(":")} — ${v.map(c=>qtext(c.f)+" "+[...new Set(Object.values(c.by))].join(" / ")).join("; ")}${v.length?", ":""}${who}`});
 return T}
function line(n,i,T){const node=!n.fact_id.includes("#");const v=node?"":valStr(n);const ev=(n.evidence||"").split(";")[0];const fl=n.flag||[];
 const q=(n.qualifiers||"").split(";").filter(Boolean).map(p=>`<span class="q" data-k="${esc(p.split("=")[0])}">${esc(p)}</span>`).join("")+(n.unit&&!node?`<span class="q" data-k="unit" hidden>unit</span>`:"");
 const lab=node&&n.label_as_printed?` <span class="mut">“${esc(n.label_as_printed)}”</span>`:"";
 return `<span class="ty ${n.type}">${node?n.type:n.type.slice(0,3)}</span><span ${node?"":`class="stm" onclick="event.preventDefault();event.stopPropagation();cardFor('${n.fact_id}',${i})"`}>${esc(n.statement)}</span>${v?` <span class="v">${esc(v)}</span>`:""}${lab}${q}${ev?`<code class="ev" title="${esc(n.fact_id)}" onclick="event.preventDefault();event.stopPropagation();side('${ev}',${i})">${ev}</code>`:""}`}
function node(n,i,T,open){const ch=T.kids[n.fact_id]||[];const linked=n.type==="claim"&&n.links?n.links.split(";").map(l=>T.byId[l]).filter(Boolean):[];
 const cls=`nd${T.vary.has(n.fact_id)?" vary":""}${n.nopts?" dim":""}${n.type==="run"&&trayHas(i,n.fact_id)?" tray":""}`;
 if(!ch.length&&!linked.length)return `<div class="${cls} leaf" data-f="${n.fact_id}">${line(n,i,T)}</div>`;
 const op=open||n.type==="group"||n.type==="process"||(n.type==="paper"&&i===P);
 return `<details class="${cls}" data-f="${n.fact_id}" ${op?"open":""}><summary>${line(n,i,T)} <span class="mut">(${ch.length}${linked.length?`, ${linked.length} linked`:""})</span></summary>${linked.map(l=>`<div class="nd leaf linked" data-f="${l.fact_id}">${line(l,i,T)}</div>`).join("")}${ch.map(c=>node(c,i,T,false)).join("")}</details>`}
let FQ="",FX="",DEMO=false;
const COL9={"100 nm":"#3b7fc4","500 nm":"#c0392b","2000 nm":"#2e7d3a","250 cycles":"#e67e22","500 cycles":"#c0392b","1000 cycles":"#3b5fc4"};
function lchart(ser,xl,yl){const W=300,H=230,L=46,R=10,T=10,B=36;const xs=ser.flatMap(s=>s.pts.map(p=>p[0]).concat(s.marks.map(m=>m.x))),ys=ser.flatMap(s=>s.pts.map(p=>p[1]).concat(s.marks.map(m=>m.y)));
 let x0=Math.min(0,...xs),x1=Math.max(...xs),y0=Math.min(0,...ys),y1=Math.max(...ys);x1+=(x1-x0)*.05;y1+=(y1-y0)*.08;if(x1===x0)x1=x0+1;if(y1===y0)y1=y0+1;
 const X=v=>L+(v-x0)/(x1-x0)*(W-L-R),Y=v=>H-B-(v-y0)/(y1-y0)*(H-T-B);
 const tk=(a,b)=>{const st=10**Math.floor(Math.log10((b-a)/4||1)),s2=(b-a)/st>8?5*st:(b-a)/st>4?2*st:st;const o=[];for(let v=Math.ceil(a/s2)*s2;v<=b+1e-9;v+=s2)o.push(+v.toPrecision(10));return o};
 let g=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(yl)} against ${esc(xl)}">`;
 tk(x0,x1).forEach(v=>g+=`<line class="gr" x1="${X(v).toFixed(1)}" x2="${X(v).toFixed(1)}" y1="${T}" y2="${H-B}" stroke="#e2dfd8"/><text x="${X(v).toFixed(1)}" y="${H-B+12}" text-anchor="middle" font-size="9" fill="#6b6a66">${v}</text>`);
 tk(y0,y1).forEach(v=>g+=`<line x1="${L}" x2="${W-R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#e2dfd8"/><text x="${L-4}" y="${(Y(v)+3).toFixed(1)}" text-anchor="end" font-size="9" fill="#6b6a66">${+v.toPrecision(3)}</text>`);
 g+=`<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle" font-size="10" fill="#1d1d1b">${esc(xl)}</text><text transform="translate(10 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle" font-size="10" fill="#1d1d1b">${esc(yl)}</text>`;
 ser.forEach((s,k)=>{if(s.pts.length)g+=`<polyline fill="none" stroke="${s.color}" stroke-width="1.6" points="${s.pts.map(p=>X(p[0]).toFixed(1)+","+Y(p[1]).toFixed(1)).join(" ")}"/>`+s.pts.map(p=>`<circle cx="${X(p[0]).toFixed(1)}" cy="${Y(p[1]).toFixed(1)}" r="2" fill="${s.color}"/>`).join("");
  s.marks.forEach(m=>g+=m.fill?`<path d="M${X(m.x).toFixed(1)} ${(Y(m.y)-6).toFixed(1)} l6 6 l-6 6 l-6 -6 Z" fill="${s.color}"><title>${esc(m.tip)}</title></path>`:`<circle cx="${X(m.x).toFixed(1)}" cy="${Y(m.y).toFixed(1)}" r="5" fill="none" stroke="${s.color}" stroke-width="1.8"><title>${esc(m.tip)}</title></circle>`);
  g+=`<text x="${W-R-2}" y="${T+12+12*k}" text-anchor="end" font-size="10" fill="${s.color}">${esc(s.label)}${s.pts.length?"":" (no points)"}</text>`});
 return g+"</svg>"}
function demoHTML(d){const D=d.demo;if(!D)return"";let h="";const used=[];
 for(const [ser,blk] of Object.entries(D).filter(([k])=>k!=="crops")){const cs=blk.curves;const col=c=>COL9[c.label]||"#888";
  const interp=(pts,x)=>{for(let i=0;i<pts.length-1;i++){const [a,b]=[pts[i],pts[i+1]];if(a[0]<=x&&x<=b[0])return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])}return null};
  const mk=(c,y,ysn)=>[{x:c.xt50_tab,y:y,fill:true,tip:`Table 1 x~50 = ${c.xt50_tab} (${c.run})`},{x:c.xt_pd50,y:y,fill:false,tip:`Table 1 PD50 ${c.PD50} µm / H = ${c.xt_pd50.toFixed(0)}`}];
  const sn=cs.map(c=>{const y=c.sn?interp(c.sn,c.xt50_tab):(c.SIIb/2)/c.N;return{pts:c.sn||[],color:col(c),label:c.label,marks:mk(c,y??(c.SIIb/2)/c.N)}});
  const nm=cs.map(c=>({pts:c.norm||[],color:col(c),label:c.label,marks:mk(c,0.5)}));
  const raw=cs.map(c=>({pts:c.raw||[],color:col(c),label:c.label,marks:[{x:c.PD50,y:c.raw?(interp(c.raw,c.PD50)??c.SIIb/2):c.SIIb/2,fill:true,tip:`Table 1 PD50 = ${c.PD50} µm`}]}));
  cs.forEach(c=>{used.push(c.fid);c.used.forEach(u=>used.push(u))});
  const p=blk.panel,p2=String.fromCharCode(p.charCodeAt(0)+1),p3=String.fromCharCode(p.charCodeAt(0)+2);
  h+=`<div class="demo"><div>${lchart(raw,"x (µm)","S (nm)")}<div class="cap">Series ${ser}: Fig. 9${p} points as digitized</div></div>
  <div>${lchart(sn,"x̃ = x/H","S/N (nm)")}<div class="cap">computed: S/N against x/H (H, N from the run)</div></div>
  <div>${lchart(nm,"x̃ = x/H","S/S_IIb")}<div class="cap">computed: S/S_IIb against x/H; ◆ Table 1 x̃50, ○ PD50/H</div></div>
  <div><img src="${D.crops[p2]}" alt="Fig. 9${p2} crop"><div class="cap">paper's Fig. 9${p2}</div></div><div><img src="${D.crops[p3]}" alt="Fig. 9${p3} crop"><div class="cap">paper's Fig. 9${p3}</div></div></div>`;
  h+=`<div class="mut" style="font-size:12px;margin:-4px 0 10px">${cs.map(c=>`${c.label}: x̃50 ${c.xt50?c.xt50.toFixed(0)+" computed vs "+c.xt50_tab+" Table 1 ("+((c.xt50-c.xt50_tab)/c.xt50_tab*100).toFixed(0).replace(/^(\d)/,"+$1")+"%)":"no points; Table 1 "+c.xt50_tab}`).join(" · ")}</div>`}
 return {html:h,used}}
const PAPERQ=()=>{const c={};DATA.forEach(d=>Object.entries(d.quantities).forEach(([q,n])=>c[q]=n));return c};
function fleaves(){const out=[];if(!FQ)return out;DATA.forEach((d,i)=>d.facts.forEach(f=>{if(f.quantity===FQ&&f.ctx)out.push({d,i,f})}));return out}
const fv=f=>{const v=parseFloat(String(f.value).replace("−","-").replace(/\s/g,""));if(!isNaN(v))return v;const lo=parseFloat(f.value_min),hi=parseFloat(f.value_max);
 if(!isNaN(lo)&&!isNaN(hi))return lo>0&&hi>0?Math.sqrt(lo*hi):(lo+hi)/2;return isNaN(lo)?hi:lo};
function forestBar(){const Q=PAPERQ();const ls=fleaves();const xs={};ls.forEach(l=>Object.entries(l.f.ctx).forEach(([q,c])=>{if(c!=="ambiguous"&&q!==FQ)xs[q]=(xs[q]||0)+1}));
 if(FQ&&!(FX in xs))FX=("deposition_temperature" in xs)?"deposition_temperature":Object.keys(xs)[0]||"";
 return `<div class="fl"><label>quantity <select onchange="DEMO=false;FQ=this.value;FX='';applyForest()"><option value="">none</option>${Object.keys(Q).sort().map(q=>`<option value="${q}" ${q===FQ?"selected":""}>${esc(LISTS.labels[q]||q)} (${Q[q]})</option>`).join("")}</select></label>
 <label>x = <select onchange="FX=this.value;applyForest()" ${FQ?"":"disabled"}>${Object.keys(xs).sort().map(q=>`<option value="${q}" ${q===FX?"selected":""}>${esc(LISTS.labels[q]||q)} (${xs[q]})</option>`).join("")||"<option>—</option>"}</select></label>
 ${USER.filter(u=>u.type==="claim"&&u.quantity&&/x=/.test(u.qualifiers)).map(u=>`<button class="${!DEMO&&FQ===u.quantity?"on":""}" title="${esc(u.statement)}" onclick="DEMO=false;FQ='${u.quantity}';FX='${quals(u.qualifiers).x}';applyForest()">${esc(u.label_as_printed||u.fact_id)}</button>`).join(" ")} <button class="${DEMO?"on":""}" onclick="DEMO=true;FQ='';applyForest()">Fig. 9 from tree</button>
 <span class="mut" id="fn"></span>${DATA.map((d,i)=>`<span class="sw" style="background:var(--c${i})"></span>${d.key}`).join("")} <span class="mut">· hollow = cited · red key = differs from the majority</span></div><div id="scat"></div>`}
function applyForest(){const bar=$("#forest");if(!bar)return;bar.innerHTML=forestBar();document.querySelectorAll(".hl").forEach(n=>n.classList.remove("hl"));
 document.querySelectorAll(".q.red").forEach(n=>{n.classList.remove("red");if(n.dataset.k==="unit")n.hidden=true});
 if(DEMO){const dm=demoHTML(DATA[0]);$("#fn").textContent=`Fig. 9 of yim20 rebuilt from the tree: ${dm.used.length} leaves used`;$("#scat").innerHTML=dm.html;
  dm.used.forEach(id=>{const el=document.querySelector(`[data-f="${CSS.escape(id)}"]:not(.linked)`);if(el){el.classList.add("hl");let p=el.parentElement;while(p){if(p.tagName==="DETAILS")p.open=true;p=p.parentElement}}});return}
 const ls=fleaves();let shown=0;const pts=[];
 ls.forEach(l=>{const el=document.querySelector(`[data-f="${CSS.escape(l.f.fact_id)}"]:not(.linked)`);if(el){el.classList.add("hl");let p=el.parentElement;while(p){if(p.tagName==="DETAILS")p.open=true;p=p.parentElement}
   (l.f.flag||[]).forEach(k=>el.querySelectorAll(`.q[data-k="${k}"]`).forEach(b=>{b.classList.add("red");b.hidden=false}))}
  const c=l.f.ctx[FX];if(c&&c!=="ambiguous"&&c[1]!=null){pts.push({l,x:c[1],xs:c[0],y:fv(l.f)});shown++}});
 const amb=ls.filter(l=>l.f.ctx[FX]==="ambiguous").length,nox=ls.length-shown-amb;
 $("#fn").textContent=FQ?`${ls.length} leaves highlighted; ${shown} in the scatter${amb?`, ${amb} with an ambiguous ${FX}`:""}${nox?`, ${nox} with no ${FX} in scope`:""}`:"";
 $("#scat").innerHTML=pts.length?scatter(pts):""}
function scatter(pts){const W=820,H=360,L=64,R=16,T=18,B=44;
 const xs=pts.flatMap(p=>[p.x,p.l.f.ctx[FX][3],p.l.f.ctx[FX][4]]).filter(v=>v!=null&&!isNaN(v)),ys=pts.flatMap(p=>[p.y,parseFloat(p.l.f.value_min),parseFloat(p.l.f.value_max)]).filter(v=>!isNaN(v));
 const pos=a=>a.every(v=>v>0),span=a=>Math.log10(Math.max(...a)/Math.min(...a));const lx=pos(xs)&&span(xs)>2,ly=pos(ys)&&span(ys)>2;
 const tx=v=>lx?Math.log10(v):v,ty=v=>ly?Math.log10(v):v;let x0=Math.min(...xs.map(tx)),x1=Math.max(...xs.map(tx)),y0=Math.min(...ys.map(ty)),y1=Math.max(...ys.map(ty));
 if(x1===x0){x0-=1;x1+=1}if(y1===y0){y0-=1;y1+=1}const px=(x1-x0)*0.06,py=(y1-y0)*0.08;x0-=px;x1+=px;y0-=py;y1+=py;
 const X=v=>L+(tx(v)-x0)/(x1-x0)*(W-L-R),Y=v=>H-B-(ty(v)-y0)/(y1-y0)*(H-T-B);
 const ticks=(a,b,log)=>{if(log){const o=[];for(let k=Math.ceil(a);k<=Math.floor(b);k++)o.push(10**k);return o}const st=10**Math.floor(Math.log10((b-a)/4||1)),s2=(b-a)/st>8?5*st:(b-a)/st>4?2*st:st;const o=[];for(let v=Math.ceil(a/s2)*s2;v<=b+1e-9;v+=s2)o.push(+v.toPrecision(10));return o};
 const fmt=v=>v===0?"0":Math.abs(v)>=1e6||Math.abs(v)<1e-2?v.toExponential(2).replace(/\.?0+e/,"e").replace("e+","e"):String(+v.toPrecision(5));
 const units=[...new Set(pts.map(p=>p.l.f.unit))].join(", "),xunits=[...new Set(pts.map(p=>p.xs.replace(/^[^\s]+\s?/,"")))].filter(Boolean).join(", ");
 let g=`<svg class="sc" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(FQ)} against ${esc(FX)}">`;
 ticks(x0,x1,lx).forEach(v=>{const vv=lx?v:v;const x=L+(( lx?Math.log10(v):v)-x0)/(x1-x0)*(W-L-R);g+=`<line class="gr" x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${T}" y2="${H-B}"/><text class="tk" x="${x.toFixed(1)}" y="${H-B+14}" text-anchor="middle">${fmt(vv)}</text>`});
 ticks(y0,y1,ly).forEach(v=>{const y=H-B-((ly?Math.log10(v):v)-y0)/(y1-y0)*(H-T-B);g+=`<line class="gr" x1="${L}" x2="${W-R}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"/><text class="tk" x="${L-6}" y="${(y+3).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`});
 g+=`<text x="${(L+W-R)/2}" y="${H-6}" text-anchor="middle">${esc(LISTS.labels[FX]||FX)}${xunits?` (${esc(xunits)})`:""}${lx?", log":""}</text><text transform="translate(12 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle">${esc(LISTS.labels[FQ]||FQ)}${units?` (${esc(units)})`:""}${ly?", log":""}</text>`;
 pts.forEach(p=>{const f=p.l.f,c=`var(--c${p.l.i})`,x=X(p.x),y=Y(p.y);const lo=parseFloat(f.value_min),hi=parseFloat(f.value_max);
  if(!isNaN(lo)&&!isNaN(hi)&&(!ly||(lo>0&&hi>0)))g+=`<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${Y(lo).toFixed(1)}" y2="${Y(hi).toFixed(1)}" stroke="${c}" stroke-width="1.5"/>`;
  const cx=f.ctx[FX];if(cx[3]!=null&&cx[4]!=null&&(!lx||(cx[3]>0&&cx[4]>0)))g+=`<line x1="${X(cx[3]).toFixed(1)}" x2="${X(cx[4]).toFixed(1)}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${c}" stroke-width="1.5"/>`;
  const tip=`${p.l.d.key} ${f.fact_id.split(":")[1]}: ${esc(f.statement)}\n${esc(FQ)} = ${esc(valStr(f))}${f.qualifiers?" ["+esc(f.qualifiers)+"]":""} · ${esc(f.data_kind)}${f.cited?" · cited":""}\n${esc(FX)} = ${esc(p.xs)} (${esc(f.ctx[FX][2].split(":")[1])})${(f.flag||[]).length?"\nflag: "+f.flag.join(", "):""}`;
  const tr=f.scope&&trayHas(p.l.i,f.scope);g+=`<circle class="pt ${tr?"tray":""}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${tr?8:5.5}" fill="${f.cited?"var(--card)":c}" stroke="${c}" stroke-width="2" onclick="jump('${f.fact_id}')"><title>${tip}</title></circle>`;
  if(f.censor)g+=`<text x="${(x+7).toFixed(1)}" y="${(y+4).toFixed(1)}" class="tk">${esc(f.censor)}</text>`;
  if((f.flag||[]).length)g+=`<text x="${(x+7).toFixed(1)}" y="${(y-5).toFixed(1)}" fill="var(--missb)" font-size="10">${esc(f.flag.join(","))}</text>`});
 return g+"</svg>"}
function jump(fid){if(V==="tree"&&TM!=="text"){const pi=DATA.findIndex(d=>d.facts.some(f=>f.fact_id===fid));if(pi>=0){cardFor(fid,pi);return}}const el=document.querySelector(`[data-f="${CSS.escape(fid)}"]:not(.linked)`);if(!el)return;let p=el.parentElement;while(p){if(p.tagName==="DETAILS")p.open=true;p=p.parentElement}el.scrollIntoView({block:"center"});el.classList.add("sel");setTimeout(()=>el.classList.remove("sel"),1500)}
let TM="find";let CARD=null;let FIGC=null;let GCARD=null;
const ckey=f=>`${f.quantity||"—"}|${f.qualifiers}|${f.quantity==="other"?f.label_as_printed:""}`;
const PRIM=["reactor_type","deposition_temperature","process_pressure","precursor_purity","source_temperature","pulse_time","purge_time","feature_height","cycle_number","substrate"];   // row 2 and find: the process-defining settings, in this order, before the rest
const rank=f=>{const r=PRIM.indexOf(f.quantity);return r<0?PRIM.length:r};
function fitChips(){const box=document.getElementById("pchips"),t=document.getElementById("pmore");if(!box||!t)return;
 if(box.classList.contains("open")){t.textContent="show fewer";return}
 const n=[...box.querySelectorAll(".chip")].filter(c=>c.offsetTop+c.offsetHeight>box.clientHeight).length;t.textContent=n?`+${n} more`:"";t.style.display=n?"":"none"}
function toggleChips(){const box=document.getElementById("pchips");if(!box)return;box.classList.toggle("open");fitChips()}
const ctext=f=>valStr(f)||f.statement.replace(/^[^:]*:\s*/,"").slice(0,40);
const qlab=f=>esc(qtext(f));   // the short label (lists.LABELS), as every screen shows it
function subtree(T,id){const out=[];(function w(x){for(const c of T.kids[x]||[]){if(c.type==="run"||c.type==="group")continue;if(c.fact_id.includes("#"))out.push(c);w(c.fact_id)}})(id);return out}
const settingsOf=(T,id)=>subtree(T,id).filter(f=>f.type==="setting"&&f.quantity);
function variedAmong(T,nodes){const per={};nodes.forEach(n=>settingsOf(T,n.fact_id).forEach(f=>{const k=ckey(f),v=ctext(f);(per[k]=per[k]||{f,by:{}});const cur=per[k].by[n.fact_id];if(!cur)per[k].by[n.fact_id]=v;else if(!cur.split("; ").includes(v))per[k].by[n.fact_id]=cur+"; "+v}));
 return Object.values(per).filter(c=>new Set(Object.values(c.by)).size>1)}
const rowOf=(T,id)=>{let x=id;while(x&&T.byId[x]&&!(T.byId[x].type==="run"||T.byId[x].type==="group"))x=T.up[x];return x};
const nlab=n=>n.glab||n.label_as_printed||n.fact_id.split(":").slice(1).join(":");
const spark=p=>{const xs=p.map(a=>a[0]),ys=p.map(a=>a[1]);const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);return `<svg class="sp" viewBox="0 0 70 20"><polyline fill="none" stroke="var(--acc)" stroke-width="1.2" points="${p.map(a=>(2+66*(a[0]-x0)/((x1-x0)||1)).toFixed(1)+","+(18-16*(a[1]-y0)/((y1-y0)||1)).toFixed(1)).join(" ")}"/></svg>`};
const elab=e=>{let m;if(m=e.match(/^fig(\d+)([a-z]*)(\.cap)?$/))return `Fig. ${m[1]}${m[2]}${m[3]?" caption":""}`;if(m=e.match(/^tab(u?)(\w+)\./))return m[1]?"nomenclature":`Table ${m[2]}`;if(m=e.match(/^s(\d+)\./))return `text §${m[1]}`;if(e.startsWith("abs"))return "abstract";if(e.startsWith("eq"))return `Eq. ${e.slice(2)}`;return e};
function cardFor(fid,pi){const d=DATA[pi],T=buildTree(d);const run=(function(){let x=T.up[fid];while(x&&T.byId[x]&&T.byId[x].type!=="run")x=T.up[x];return x})();
 P=pi;V="tree";TM="cards";CARD=run||null;FIGC=null;GCARD=null;render();if(!run){$("#cardpane").innerHTML=`<div class="card"><h2>no run</h2><div class="mut">${esc(fid)} is not under a run (a paper-, process- or group-level fact).</div><div id="side" class="evbox"></div></div>`}}
function openCard(pi,id){P=pi;CARD=id;FIGC=null;GCARD=null;document.querySelectorAll(".rl.on").forEach(n=>n.classList.remove("on"));document.querySelectorAll(`.rl[data-r="${CSS.escape(id)}"]`).forEach(n=>n.classList.add("on"));$("#cardpane").innerHTML=card(DATA[pi],pi,id);fitChips()}
const trayHas=(i,id)=>WB.tray.some(t=>t.i===i&&t.id===id);
function leftTree(d,i){const T=buildTree(d);const line=n=>`<div class="rl ${CARD===n.fact_id?"on":""} ${trayHas(i,n.fact_id)?"tray":""}" data-r="${n.fact_id}" title="${esc(n.statement)}" onclick="openCard(${i},'${n.fact_id}')"><span class="ty ${n.type}">${n.type}</span>${esc(nlab(n))}</div>`;
 const walk=x=>(T.kids[x]||[]).map(c=>{if(c.type==="process")return `<div class="mut" style="margin-left:10px">process (conditions in each card, row 2)</div>`+walk(c.fact_id);
  if(c.type==="group"){const cf=confound(T,c.fact_id);return `<details open><summary><span class="ty group">group</span><span class="gl ${GCARD===c.fact_id?"on":""}" data-g="${c.fact_id}" onclick="event.preventDefault();event.stopPropagation();openGroup(${i},'${c.fact_id}')">${esc(nlab(c))}</span>${cf?` <span class="inf" title="runs differ in ${cf.length} settings">${cf.length} settings</span>`:""}</summary>${walk(c.fact_id)}</details>`}
  if(c.type==="run"){const ch=(T.kids[c.fact_id]||[]).some(k=>k.type==="run");return ch?`<details open><summary>${line(c)}</summary>${walk(c.fact_id)}</details>`:line(c)}return""}).join("");
 const ns=naturalSeries(i);return `<div class="lt"><b>${d.key}</b> <span class="mut">${d.tree.filter(n=>n.type==="run").length} runs</span>${walk(T.root.fact_id)}<details open class="ns"><summary><span class="ty group">series</span>natural series, computed <span class="mut">(${ns.length})</span></summary>${ns.map((sr,j)=>seriesLine(i,sr,j)).join("")||'<div class="mut" style="margin-left:10px">none</div>'}</details></div>`}
function card(d,i,id){const T=buildTree(d),n=T.byId[id];if(!n)return"";const ev=f=>`<code class="ev" title="${esc(f.fact_id)}" onclick="side('${f.evidence.split(";")[0]}',${i})">${f.evidence.split(";")[0]}</code>`;
 const levels=levelsOf(T,id);
 const own=levels[0];const shown=levels.find(l=>l.varied.length)||own;
 // 1 what was varied
 let r1="";const sibLab=s=>`<span class="sib" onclick="openCard(${i},'${s.fact_id}')">${esc(nlab(s))}</span>`;
 if(own.sibs.length<2)r1=`<div class="mut">no sibling runs under ${esc(nlab(T.byId[own.par]))}.</div>`;
 else if(!own.varied.length)r1=`<div class="mut">the ${own.sibs.length} siblings under ${esc(nlab(T.byId[own.par]))} differ in no recorded setting (${own.sibs.filter(s=>s.fact_id!==id).map(sibLab).join(", ")}).</div>`;
 if(shown.varied.length){r1+=(shown!==own?`<div class="mut">one level up, ${esc(nlab(T.byId[shown.node]))} against its siblings:</div>`:"")+shown.varied.map(c=>`<div><b>${qlab(c.f)}</b>: <span class="num">${esc(c.by[shown.node]||"not stated")}</span> <span class="mut">· siblings: ${shown.sibs.filter(s=>s.fact_id!==shown.node).map(s=>`${esc(c.by[s.fact_id]||"—")} (${sibLab(s)})`).join(", ")}</span></div>`).join("")}
 else if(shown===own&&own.sibs.length>=2)r1+="";
 if(!shown.varied.length&&own.sibs.length>=2)r1+=`<div class="mut">nor does any level above.</div>`;
 // 2 other conditions: the process-defining settings first (PRIM), then the rest; the same value stated at two levels is one chip
 // (marked if either is); the box shows two lines until "+N more" opens it (fitChips counts the chips the two lines cut off)
 const varKeys=new Set(shown.varied.map(c=>ckey(c.f)));const chips=[];
 const addChip=(f,diff,lv)=>{const k=ckey(f)+"|"+ctext(f);const c=chips.find(x=>x.k===k);if(c){c.diff=c.diff||diff;return}chips.push({f,diff,lv,k})};
 settingsOf(T,id).filter(f=>!(shown===own&&varKeys.has(ckey(f)))).forEach(f=>addChip(f,false,"this run"));
 levels.forEach((l,k)=>{if(k===0)return;const lvVar=new Set(l.varied.map(c=>ckey(c.f)));settingsOf(T,l.node).forEach(f=>addChip(f,lvVar.has(ckey(f)),nlab(T.byId[l.node])))});
 let a=T.up[levels[levels.length-1].node];while(a&&T.byId[a]){settingsOf(T,a).forEach(f=>addChip(f,false,T.byId[a].type));a=T.up[a]}
 chips.sort((x,y)=>rank(x.f)-rank(y.f));
 const r2=chips.length?`<div class="pchips" id="pchips">${chips.map(c=>`<span class="chip ${c.diff?"diff":""}" data-f="${c.f.fact_id}" title="${esc(c.lv)}: ${esc(c.f.statement)}" onclick="side('${c.f.evidence.split(";")[0]}',${i})">${esc(qtext(c.f))} ${esc(ctext(c.f))}</span>`).join(" ")}</div><div class="mut" style="font-size:11px"><span class="lnk" id="pmore" onclick="toggleChips()"></span> ${chips.filter(c=>c.diff).length} marked: differ from a sibling at their level</div>`:`<div class="mut">none recorded</div>`;
 // 3 measured
 const meas=subtree(T,id).filter(f=>["observation","derived","model"].includes(f.type));const groups={};meas.forEach(f=>{const e=f.evidence.split(";")[0];const g=elab(e);(groups[g]=groups[g]||[]).push(f)});
 const inf=n.qualifiers.includes("how=inferred");
 const fline=f=>`<div class="fl2"><span class="cv" data-f="${f.fact_id}">${f.points?`<span class="spw">${spark(f.points)}</span>`:""}<span class="ty ${f.type}">${f.type.slice(0,3)}</span>${esc(f.statement)}${valStr(f)?` <span class="num">${esc(valStr(f))}</span>`:""}${f.nopts?' <span class="mut">(no points)</span>':""}${ev(f)}</span></div>`;
 const childRuns=(T.kids[id]||[]).filter(k=>k.type==="run");
 const r3=(inf?`<div><span class="inf">membership inferred</span> <span class="mut">${esc(n.statement)}</span></div>`:"")+(childRuns.length?`<div class="mut">measured on its specimens: ${childRuns.map(sibLab).join(", ")}</div>`:"")+(meas.length?Object.entries(groups).map(([g,fs])=>`<div class="mg"><b>${esc(g)}</b> <span class="mut">(${fs.length})</span>${fs.map(fline).join("")}</div>`).join(""):`<div class="mut">no measured facts on this run</div>`);
 // 4 why and what it showed
 const grpId=levels.map(l=>l.par).find(p=>T.byId[p].type==="group"||(T.byId[p].type==="run"&&T.byId[p].links));const grp=grpId?T.byId[grpId]:null;const pur=grp&&grp.links?T.byId[grp.links.split(";")[0]]:null;
 const inRun=new Set(subtree(T,id).map(f=>f.fact_id).concat([id]));const inGrp=grpId?new Set(subtree(T,grpId).map(f=>f.fact_id).concat([grpId])):new Set();
 const claims=d.facts.filter(c=>c.type==="claim"&&c.links&&c.links.split(";").some(l=>inRun.has(l)||inGrp.has(l)||rowOf(T,l)===id||rowOf(T,l)===grpId)&&(!pur||c.fact_id!==pur.fact_id));
 const r4=(pur?`<div><b>purpose of ${esc(nlab(grp))}</b> <span class="mut">(${esc(pur.type)})</span>: ${esc(pur.statement)}${pur.type==="claim"?` <span class="chip scope">${esc(claimScope(d,i,pur).text)}</span>`:""}${ev(pur)}</div>`:`<div class="mut">no group with a purpose above this run</div>`)+(claims.length?claims.map(c=>claimLine(d,i,c)).join(""):`<div class="mut fl2">no claim links to this run or its group</div>`);
 // 5 compare: a run picker (siblings first, then every run of the three papers) and a button that opens find with the two runs
 const sibs=own.sibs.filter(s=>s.fact_id!==id);const opt=(j,n,sel)=>`<option value="${j}|${n.fact_id}" ${sel?"selected":""}>${esc(nlab(n))}</option>`;
 const r5=`<select id="cmp">${sibs.length?`<optgroup label="siblings">${sibs.map((s,k)=>opt(i,s,k===0)).join("")}</optgroup>`:""}${DATA.map((o,j)=>`<optgroup label="${o.key}">${o.tree.filter(n=>n.type==="run"&&n.fact_id!==id).map(n=>opt(j,n,false)).join("")}</optgroup>`).join("")}</select> <button onclick="compareWith(${i},'${id}')">compare</button>`;
 return `<div class="card"><h2>${esc(nlab(n))} <span class="mut" style="font-size:12px;font-weight:400">${esc(n.fact_id)} · ${esc(n.qualifiers)}</span> ${trayBtn(i,id)}</h2><div class="mut">${esc(n.statement)}</div>
 <section><h4>1 · what was varied</h4>${r1}</section><section><h4>2 · other conditions</h4>${r2}</section><section><h4>3 · measured</h4>${r3}</section>
 <section><h4>4 · why and what it showed</h4>${r4}</section><section><h4>5 · compare</h4>${r5}</section>
 <div id="side" class="evbox"><span class="mut">Click an element id for the element, its crop and its facts.</span></div></div>`}
// workbench (the find view): left filters, middle the matching runs, right the tray and the compare panel
function inherited(T,id){const m={};let x=id;while(x&&T.byId[x]){const lv={};settingsOf(T,x).forEach(f=>{const k=ckey(f);(lv[k]=lv[k]||{f,fs:[],t:[]});lv[k].fs.push(f);const t=valStr(f);if(t&&!lv[k].t.includes(t))lv[k].t.push(t)});for(const k in lv)if(!(k in m))m[k]={f:lv[k].f,fs:lv[k].fs,text:lv[k].t.join("; ")};x=T.up[x]}return m}
function results(T,id){const m={};subtree(T,id).filter(f=>["observation","derived","model"].includes(f.type)&&f.quantity&&(valStr(f)||f.points_ref)).forEach(f=>{const k=ckey(f);(m[k]=m[k]||{f,fs:[]}).fs.push(f)});return m}
const grpOf=(T,id)=>{let x=T.up[id];while(x&&T.byId[x]&&T.byId[x].type!=="group")x=T.up[x];return x&&T.byId[x]?x:null};
let _RUNS=null;const RUNS=()=>_RUNS||(_RUNS=DATA.flatMap((d,i)=>{const T=buildTree(d);return d.tree.filter(n=>n.type==="run").map(n=>({d,i,T,n,id:n.fact_id,inh:inherited(T,n.fact_id),res:results(T,n.fact_id)}))}));
const qshort=(q,qs)=>{const k=q+"{"+qs+"}";if(LISTS.labels[k])return LISTS.labels[k];const base=LISTS.labels[q]||(q||"").replace(/_/g," ");const vals=qs.split(";").filter(Boolean).map(p=>p.split("=")[1]);return vals.length?base+" "+vals.join(" "):base};
const qtext=f=>{const qs=(f.qualifiers||"").split(";").filter(Boolean);const x=qs.find(p=>p.startsWith("x="));const rest=qs.filter(p=>!p.startsWith("x=")).join(";");const base=f.quantity==="other"?(f.label_as_printed||"other")+(rest?" "+rest.split(";").map(p=>p.split("=")[1]).join(" "):""):qshort(f.quantity||"",rest);return x?`${base} vs ${qshort(x.slice(2),"")}`:base};
const shadeOf=fs=>{const nums=fs.map(fv).filter(v=>v!=null&&!isNaN(v));const min=Math.min(...nums),max=Math.max(...nums),log=nums.length>1&&nums.every(v=>v>0)&&Math.log10(max/min)>2;return v=>{if(v==null||isNaN(v)||!(max>min))return"";const t=log?(Math.log10(v)-Math.log10(min))/(Math.log10(max)-Math.log10(min)):(v-min)/(max-min);return `background:color-mix(in srgb,var(--acc) ${Math.round(8+42*t)}%,transparent)`}};
const evc=(f,i)=>`onclick="event.stopPropagation();side('${f.evidence.split(";")[0]}',${i})"`;
function levelsOf(T,id){const levels=[];let x=id;while(T.up[x]&&T.byId[T.up[x]]){const par=T.up[x];const sibs=(T.kids[par]||[]).filter(k=>(k.type==="run"||k.type==="group"));levels.push({node:x,par,sibs,varied:variedAmong(T,sibs)});if(["process","paper"].includes(T.byId[par].type))break;x=par}return levels}
const variedText=(T,id)=>{const s=levelsOf(T,id).find(l=>l.varied.length);return s?s.varied.filter(c=>c.by[s.node]).sort((a,b)=>rank(a.f)-rank(b.f)).map(c=>`${qtext(c.f)} ${c.by[s.node]}`).join("; "):""};
const EMPTY_RANGE=()=>({deposition_temperature:["",""],process_pressure:["",""],cycle_number:["",""],exposure:["",""]});
let WB={material:"",structure:"",method:"",quantity:"",paper:"",range:EMPTY_RANGE(),tray:[]};
const RANGE={deposition_temperature:"°C",process_pressure:"Pa",cycle_number:"",exposure:"Pa s"};   // the filter's units (lists.UNITS)
const CONV={"°C":[1,0],"K":[1,-273.15],"Pa":[1,0],"hPa":[100,0],"kPa":[1000,0],"mbar":[100,0],"bar":[1e5,0],"Torr":[133.322,0],"mTorr":[0.133322,0],"Pa s":[1,0],"Torr s":[133.322,0],"Torr-s":[133.322,0],"mbar s":[100,0],"":[1,0]};   // value as printed -> the filter's unit
function nums(r,q){let es=Object.values(r.inh).filter(v=>v.f.quantity===q);const plain=es.filter(v=>!v.f.qualifiers);if(plain.length)es=plain;const out=[];
 es.forEach(v=>v.fs.forEach(f=>{const c=CONV[f.unit||""];if(!c)return;const lo=parseFloat(f.value_min),hi=parseFloat(f.value_max),a=fv(f);if(!isNaN(lo)&&!isNaN(hi))out.push([lo*c[0]+c[1],hi*c[0]+c[1]]);else if(a!=null&&!isNaN(a))out.push([a*c[0]+c[1],a*c[0]+c[1]])}));return out}
function wbMatch(r){if(WB.paper&&r.d.key!==WB.paper)return false;if(WB.material&&(r.inh["material||"]||{}).text!==WB.material)return false;if(WB.structure&&(r.inh["structure_type||"]||{}).text!==WB.structure)return false;
 if(WB.quantity&&!Object.values(r.res).some(o=>o.f.quantity===WB.quantity))return false;if(WB.method&&!subtree(r.T,r.id).some(f=>f.method===WB.method))return false;
 for(const q in WB.range){const [a,b]=WB.range[q];if(a===""&&b==="")continue;const lo=a===""?-Infinity:+a,hi=b===""?Infinity:+b;if(!nums(r,q).some(([x,y])=>y>=lo&&x<=hi))return false}return true}
function wbView(){const rs=RUNS();const m=rs.filter(wbMatch);const sel=(k,opts,cur)=>`<select onchange="wbSet('${k}',this.value)"><option value="">any</option>${opts.map(o=>`<option value="${esc(o)}" ${o===cur?"selected":""}>${esc(k==="quantity"?LISTS.labels[o]||o:o.replace(/_/g," "))}</option>`).join("")}</select>`;
 const left=`<div class="wbf"><label>material${sel("material",LISTS.materials,WB.material)}</label><label>structure type${sel("structure",LISTS.structures,WB.structure)}</label><label>method${sel("method",LISTS.methods,WB.method)}</label><label>result quantity${sel("quantity",LISTS.quantities.filter(q=>q!=="other"),WB.quantity)}</label><label>paper${sel("paper",DATA.map(d=>d.key),WB.paper)}</label>
 ${Object.entries(RANGE).map(([q,u])=>`<label>${q.replace(/_/g," ")}${u?` (${u})`:""}<div><input type="number" placeholder="min" value="${WB.range[q][0]}" onchange="wbRange('${q}',0,this.value)"> – <input type="number" placeholder="max" value="${WB.range[q][1]}" onchange="wbRange('${q}',1,this.value)"></div></label>`).join("")}<button onclick="wbClear()">clear filters</button></div>`;
 const inTray=new Set(WB.tray.filter(t=>!t.fid).map(t=>t.id));
 const mid=`<div class="wbm"><div class="mut">${m.length} runs</div>${m.map(r=>`<div class="wbr" data-r="${r.id}"><span class="sw" style="background:var(--c${r.i})"></span>${r.d.key} · <span class="lnk" onclick="showCard(${r.i},'${r.id}')">${esc(nlab(r.n))}</span> · <span class="mut">${esc(variedText(r.T,r.id))}</span><button ${inTray.has(r.id)||WB.tray.length>=8?"disabled":""} onclick="trayAdd(${r.i},'${r.id}')">add</button></div>`).join("")}</div>`;
 const right=`<div class="wbt"><b>tray</b> <span class="mut">${WB.tray.length}/8</span> <button onclick="trayClear()">clear</button>${WB.tray.map((t,j)=>{const r=rs.find(x=>x.id===t.id);return `<div class="wbr"><span class="sw" style="background:var(--c${t.i})"></span>${DATA[t.i].key} · <span class="lnk" onclick="showCard(${t.i},'${t.id}')">${esc(r?nlab(r.n):t.id)}</span>${t.fid?` · <span class="mut">${esc(t.label||t.fid)}</span>`:'<span class="mut"></span>'}<b class="lnk" onclick="trayDrop(${j})">×</b></div>`}).join("")||'<div class="mut">empty</div>'}</div><div id="cmppane">${cmpPanel()}</div><div id="side" class="evbox"></div>`;
 return `<div class="wb">${left}<div>${mid}</div><div>${right}</div></div>`}
// compare panel for the tray: (a) overlay plot with Fig. 9's transforms, (b) condition table, (c) pair verdicts
const NORM={y:{film_thickness:[["growth_per_cycle","cycle_number","S / N"],["normalized_thickness","plateau","S / S_plateau"]]},x:{distance:[["dimensionless_distance","feature_height","x / H"]]}};   // target, the setting it needs, label
const quals=s=>Object.fromEntries((s||"").split(";").filter(p=>p.includes("=")).map(p=>p.split("=")));
const LEN={nm:1e-9,"µm":1e-6,um:1e-6,mm:1e-3,m:1};const PAL=["#1f5fa8","#c0392b","#2e7d3a","#e67e22","#8e44ad","#16a085","#7f8c8d","#d35400"];
const unitOf=lab=>{const m=(lab||"").match(/\(([^)]*)\)|\[([^\]]*)\]/g);return m?m[m.length-1].replace(/[()\[\]]/g,"").trim():""};
let WBT={y:"raw",x:"raw"};
function trayItems(){const rs=RUNS();return WB.tray.map((t,j)=>{const r=rs.find(x=>x.id===t.id);if(!r)return null;const cf=t.fid?r.d.facts.find(f=>f.fact_id===t.fid):null;
 const curves=(cf?[cf]:Object.values(r.res).flatMap(o=>o.fs)).filter(f=>f&&f.points);const keys=cf?{[ckey(cf)]:cf}:Object.fromEntries(Object.entries(r.res).map(([k,o])=>[k,o.f]));
 return {t,j,r,curves,keys,label:`${r.d.key} · ${nlab(r.n)}${cf?" · "+(t.label||cf.mentions.split(";")[0]||t.fid):""}`}}).filter(Boolean)}
function need(it,what,xunit){const r=it.r;if(what==="cycle_number"){const v=r.inh["cycle_number||"];return v?fv(v.f):null}
 if(what==="feature_height"){const v=r.inh["feature_height||"];if(!v)return null;const h=fv(v.f),k=LEN[v.f.unit],u=LEN[xunit];return h==null?null:(k&&u?h*k/u:h)}
 if(what==="plateau"){const o=r.res["film_thickness|position=plateau|"];return o?fv(o.fs[0]):null}return null}
function reach(it){const out={};const put=(q,x,via,missing)=>{const k=q+"|"+x;if(!(k in out)||(out[k].missing&&!missing))out[k]={via,missing}};
 Object.values(it.keys).forEach(f=>{const qs=quals(f.qualifiers);if(!qs.x)return;const q=f.quantity,x=qs.x,xu=unitOf(f.xlab);put(q,x,[],null);
  const ys=[[q,null,null]].concat((NORM.y[q]||[]).map(([q2,s])=>[q2,s,need(it,s,xu)==null?s:null])),xs=[[x,null,null]].concat((NORM.x[x]||[]).map(([x2,s])=>[x2,s,need(it,s,xu)==null?s:null]));
  ys.forEach(([q2,sy,my])=>xs.forEach(([x2,sx,mx])=>{if(sy||sx)put(q2,x2,[sy,sx].filter(Boolean),my||mx)}))});return out}
function diffs(a,b){const ks=[...new Set([...Object.keys(a.r.inh),...Object.keys(b.r.inh)])];return ks.filter(k=>a.r.inh[k]&&b.r.inh[k]&&a.r.inh[k].text!==b.r.inh[k].text).map(k=>({f:a.r.inh[k].f,k,va:a.r.inh[k].text,vb:b.r.inh[k].text})).sort((x,y)=>rank(x.f)-rank(y.f))}
function verdict(a,b){const direct=Object.keys(a.keys).filter(k=>k in b.keys);const d=diffs(a,b).map(x=>`${qtext(x.f)} ${x.va||"—"} vs ${x.vb||"—"}`);const tail=d.length?` · differs: ${d.slice(0,4).join("; ")}${d.length>4?` +${d.length-4}`:""}`:" · no differing setting";
 if(direct.length)return {v:"direct",c:"ok",why:direct.slice(0,5).map(k=>qtext(a.keys[k])).join(", ")+(direct.length>5?` +${direct.length-5}`:"")+tail};
 const A=reach(a),B=reach(b),common=Object.keys(A).filter(k=>k in B);const ok=common.find(k=>!A[k].missing&&!B[k].missing);
 if(ok)return {v:"transformable",c:"tr",why:`${ok.split("|")[0].replace(/_/g," ")} against ${ok.split("|")[1].replace(/_/g," ")} via ${[...new Set([...A[ok].via,...B[ok].via])].join(", ").replace(/_/g," ")}`+tail};
 const bl=common.find(k=>A[k].missing||B[k].missing);if(bl){const m=A[bl].missing?[A[bl].missing,a.label]:[B[bl].missing,b.label];return {v:"not comparable",c:"no",why:`${m[0].replace(/_/g," ")} not stated for ${m[1]}`}}
 const pairs=[];for(const fa of Object.values(a.keys))for(const fb of Object.values(b.keys))if(fa.quantity===fb.quantity)pairs.push([fa,fb]);   // same quantity: curve against curve first, the abscissa first
 const isc=p=>quals(p[0].qualifiers).x&&quals(p[1].qualifiers).x?1:0;pairs.sort((p,q)=>isc(q)-isc(p));
 if(pairs.length){const [fa,fb]=pairs[0];const qa=quals(fa.qualifiers),qb=quals(fb.qualifiers);const ks=[...new Set([...Object.keys(qa),...Object.keys(qb)])].filter(k=>qa[k]!==qb[k]);const key=ks.includes("x")?"x":ks[0];
  return {v:"not comparable",c:"no",why:`${fa.quantity.replace(/_/g," ")}: ${key} ${(qa[key]||"—").replace(/_/g," ")} vs ${(qb[key]||"—").replace(/_/g," ")}`}}
 return {v:"not comparable",c:"no",why:"no shared quantity"}}
function overlay(items){const cs=items.flatMap(it=>it.curves.map(f=>({it,f,q:f.quantity,x:quals(f.qualifiers).x||"",xu:unitOf(f.xlab)})));if(!cs.length)return '<div class="mut">no curves</div>';
 const groups={};cs.forEach(c=>{const k=c.q+"|"+c.x;(groups[k]=groups[k]||[]).push(c)});const best=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length)[0];const [bk,on]=best;const [q,x]=bk.split("|");const off=cs.filter(c=>!on.includes(c));
 const yopts=[["raw","raw",null]].concat((NORM.y[q]||[]).map(([q2,s,l])=>[q2,l,s])),xopts=[["raw","raw",null]].concat((NORM.x[x]||[]).map(([x2,s,l])=>[x2,l,s]));
 if(!yopts.some(o=>o[0]===WBT.y))WBT.y="raw";if(!xopts.some(o=>o[0]===WBT.x))WBT.x="raw";const ys=yopts.find(o=>o[0]===WBT.y),xs=xopts.find(o=>o[0]===WBT.x);
 const ser=[],skipped=[];on.forEach(c=>{const ny=ys[2]?need(c.it,ys[2],c.xu):1,nx=xs[2]?need(c.it,xs[2],c.xu):1;if(ny==null||nx==null){skipped.push(`${c.it.label}: ${(ny==null?ys[2]:xs[2]).replace(/_/g," ")} not stated`);return}
  ser.push({pts:c.f.points.map(p=>[p[0]/nx,p[1]/ny]),color:PAL[c.it.j%PAL.length],label:`${c.it.r.d.key} ${nlab(c.it.r.n)}${c.f.mentions?" "+c.f.mentions.split(";")[0]:""}`.slice(0,34),marks:[]})});
 const yl=ys[2]?ys[1]+(ys[0]==="growth_per_cycle"&&on[0].f.unit?" ("+on[0].f.unit+")":""):(on[0].f.ylab||q),xl=xs[2]?xs[1]:(on[0].f.xlab||x);
 const sel=(k,opts)=>`<select onchange="wbT('${k}',this.value)">${opts.map(o=>`<option value="${o[0]}" ${WBT[k]===o[0]?"selected":""}>${esc(o[1])}</option>`).join("")}</select>`;
 return `<div class="fl"><label>y ${sel("y",yopts)}</label><label>x ${sel("x",xopts)}</label><span class="mut">${on.length} curves: ${esc(q.replace(/_/g," "))} against ${esc(x.replace(/_/g," "))}</span></div>${ser.length?lchart(ser,xl,yl).replace('<svg ','<svg class="ov" '):'<div class="mut">no curve has the setting</div>'}
 ${skipped.map(t=>`<div class="mut">not drawn · ${esc(t)}</div>`).join("")}${off.map(c=>`<div class="mut">other axis · ${esc(c.it.label)}: ${esc(c.q.replace(/_/g," "))} against ${esc(c.x.replace(/_/g," "))}</div>`).join("")}`}
function condTable(items){const ks=[...new Set(items.flatMap(it=>Object.keys(it.r.inh)))];const rows=[],common=[];
 ks.forEach(k=>{const vals=items.map(it=>it.r.inh[k]?it.r.inh[k].text:null);const stated=[...new Set(vals.filter(v=>v!==null))];const f=items.find(it=>it.r.inh[k]).r.inh[k].f;if(stated.length===1&&vals.every(v=>v!==null))common.push({f,k,text:stated[0]});else rows.push({f,k,vals})});   // common only when every item states the same value
 const byRank=(a,b)=>rank(a.f)-rank(b.f)||a.k.localeCompare(b.k);common.sort(byRank);rows.sort(byRank);
 return `<div class="pchips open">${common.map(c=>`<span class="chip" title="${esc(c.k)}">${esc(qtext(c.f))} ${esc(c.text)}</span>`).join(" ")||'<span class="mut">none</span>'}</div><div style="overflow-x:auto"><table class="ft cmp"><thead><tr><th>${rows.length} differ</th>${items.map(it=>`<th>${esc(it.label)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr><th>${qlab(r.f)}</th>${r.vals.map((v,j)=>`<td>${v===null?'<span class="mut">not stated</span>':`<span class="chip diff" ${evc(items[j].r.inh[r.k].f,items[j].r.i)}>${esc(v)}</span>`}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`}
function cmpPanel(){const items=trayItems();if(items.length<1)return"";const vs=[];items.forEach((a,i)=>items.slice(i+1).forEach(b=>{const v=verdict(a,b);vs.push(`<div class="fl2 vd"><b class="${v.c}">${v.v}</b> · ${esc(a.label)} vs ${esc(b.label)} · ${esc(v.why)}</div>`)}));
 return `<div class="wbt"><b>plot</b>${overlay(items)}</div><div class="wbt"><b>conditions</b>${condTable(items)}</div><div class="wbt"><b>verdicts</b>${vs.join("")||'<div class="mut">one item</div>'}</div>`}
function wbT(k,v){WBT[k]=v;render()}
function wbSet(k,v){WB[k]=v;render()}
function wbRange(q,j,v){WB.range[q][j]=v;render()}
function wbClear(){WB={...WB,material:"",structure:"",method:"",quantity:"",paper:"",range:EMPTY_RANGE()};render()}
function trayAdd(i,id,fid,label){if(WB.tray.length>=8||WB.tray.some(t=>t.id===id&&t.fid===fid))return;WB.tray.push({i,id,fid,label});render()}
function trayDrop(j){WB.tray.splice(j,1);render()}
const runOfF=(T,id)=>{let x=T.up[id];while(x&&T.byId[x]&&T.byId[x].type!=="run")x=T.up[x];return x&&T.byId[x]?x:null};
const trayLink=()=>`<span class="lnk" onclick="TM='find';render()">tray (${WB.tray.length})</span>`;
const trayBtn=(i,id)=>{const inT=WB.tray.some(t=>t.id===id&&!t.fid);return `<button ${inT||WB.tray.length>=8?"disabled":""} onclick="trayAdd(${i},'${id}')">${inT?"in tray":"add to tray"}</button> ${trayLink()}`};
function figCurves(i,eid){const d=DATA[i],T=buildTree(d);return d.facts.filter(f=>f.evidence.split(";").includes(eid)&&f.points).map(f=>({f,run:runOfF(T,f.fact_id)})).filter(c=>c.run)}
function trayAddFig(i,eid){const cs=figCurves(i,eid);if(cs.length)cs.forEach(c=>{if(WB.tray.length<8&&!WB.tray.some(t=>t.fid===c.f.fact_id))WB.tray.push({i,id:c.run,fid:c.f.fact_id,label:`${elab(eid)} ${(c.f.mentions||"").split(";")[0]}`.trim()})});
 else{const d=DATA[i],T=buildTree(d);[...new Set(d.facts.filter(f=>f.evidence.split(";").includes(eid)).map(f=>runOfF(T,f.fact_id)).filter(Boolean))].forEach(r=>{if(WB.tray.length<8&&!WB.tray.some(t=>t.id===r&&!t.fid))WB.tray.push({i,id:r})})}render()}
const figTrayBtn=(i,eid)=>{const cs=figCurves(i,eid);const inT=cs.length?cs.every(c=>WB.tray.some(t=>t.fid===c.f.fact_id)):false;return `<button ${inT||WB.tray.length>=8?"disabled":""} onclick="trayAddFig(${i},'${eid}')">${inT?"in tray":`add to tray${cs.length?` (${cs.length} curves)`:""}`}</button> ${trayLink()}`};
function trayClear(){WB.tray=[];render()}
function showCard(i,id){P=i;CARD=id;FIGC=null;GCARD=null;V="tree";TM="cards";render()}
function figCard(eid,pi){if(pi!==undefined)P=pi;V="tree";TM="cards";FIGC=eid;GCARD=null;render()}
function openGroup(i,gid){P=i;GCARD=gid;FIGC=null;V="tree";TM="cards";render()}
// reproducibility (computed): the largest set of a paper's runs with the same conditions (every setting stated by both equal) that
// share numeric results; sd (n-1) per result key over that set
const core=k=>PRIM.includes(k.split("|")[0]);   // the process-defining settings: both runs must state them, equal; any other setting counts only when both state it
const stated=(r,k)=>(k in r.inh)&&r.inh[k].text!==""&&!r.inh[k].text.includes("; ");   // one value; several values at a level (the process's three heights) are not a run's stated value
const sameCond=(a,b)=>[...new Set([...Object.keys(a.inh),...Object.keys(b.inh)])].every(k=>core(k)?stated(a,k)===stated(b,k)&&(!stated(a,k)||a.inh[k].text===b.inh[k].text):!stated(a,k)||!stated(b,k)||a.inh[k].text===b.inh[k].text);
const firstNum=o=>{const f=o.fs[0];const a=fv(f);return a!=null&&!isNaN(a)?a:null};
function reproOf(i){const d=DATA[i];if(d._REP!==undefined)return d._REP;const rs=RUNS().filter(r=>r.i===i&&Object.values(r.res).some(o=>firstNum(o)!=null));let best=null;
 rs.forEach(seed=>{const set=[seed];rs.forEach(r=>{if(r!==seed&&set.every(s=>sameCond(s,r)&&sameCond(r,s)))set.push(r)});if(set.length<2)return;
  const sd={};[...new Set(set.flatMap(r=>Object.keys(r.res)))].forEach(k=>{const vals=set.filter(r=>r.res[k]).map(r=>firstNum(r.res[k])).filter(v=>v!=null);if(vals.length>=2){const m=vals.reduce((a,b)=>a+b,0)/vals.length;sd[k]={sd:Math.sqrt(vals.reduce((a,v)=>a+(v-m)**2,0)/(vals.length-1)),n:vals.length,f:set.find(r=>r.res[k]).res[k].f}}});
  const nk=Object.keys(sd).length;if(nk&&(!best||set.length>best.set.length||(set.length===best.set.length&&nk>Object.keys(best.sd).length)))best={set,sd}});
 return d._REP=best?{runs:best.set,sd:best.sd}:null}
// natural series (computed): runs that differ in exactly one inherited setting, joined through that setting
const diffKeys=(a,b)=>[...new Set([...Object.keys(a.inh),...Object.keys(b.inh)])].filter(k=>stated(a,k)&&stated(b,k)&&a.inh[k].text!==b.inh[k].text);
function naturalSeries(i){const d=DATA[i];if(d._NS)return d._NS;const rs=RUNS().filter(r=>r.i===i);const byKey={};
 const coreMatch=(a,b)=>[...new Set([...Object.keys(a.inh),...Object.keys(b.inh)])].every(k=>!core(k)||stated(a,k)===stated(b,k));   // both state the same core settings
 for(let a=0;a<rs.length;a++)for(let b=a+1;b<rs.length;b++){const dk=diffKeys(rs[a],rs[b]);if(dk.length===1&&coreMatch(rs[a],rs[b]))(byKey[dk[0]]=byKey[dk[0]]||[]).push([rs[a].id,rs[b].id])}
 const out=[];Object.entries(byKey).forEach(([k,edges])=>{const par={};const find=x=>par[x]===undefined?x:(par[x]=find(par[x]));edges.forEach(([a,b])=>{const ra=find(a),rb=find(b);if(ra!==rb)par[ra]=rb});const comp={};edges.flat().forEach(x=>(comp[find(x)]=comp[find(x)]||new Set()).add(x));
  Object.values(comp).forEach(set=>{const runs=rs.filter(r=>set.has(r.id));out.push({k,f:runs[0].inh[k].f,runs,vals:[...new Set(runs.map(r=>r.inh[k].text))]})})});
 out.sort((a,b)=>rank(a.f)-rank(b.f)||b.runs.length-a.runs.length);return d._NS=out}
const seriesLine=(i,sr,j)=>`<div class="rl" onclick="seriesTray(${i},${j})" title="open the tray with this series"><span class="ty group">series</span>${esc(qtext(sr.f))} ${esc(sr.vals.slice(0,6).join(" / "))}${sr.vals.length>6?" …":""} · <span class="mut">${sr.runs.slice(0,8).map(r=>esc(nlab(r.n))).join(" · ")}${sr.runs.length>8?` +${sr.runs.length-8}`:""}</span></div>`;
function seriesTray(i,j){const sr=naturalSeries(i)[j];WB.tray=sr.runs.slice(0,8).map(r=>({i,id:r.id}));TM="find";render()}
function confound(T,gid){const sib=(T.kids[gid]||[]).filter(k=>k.type==="run"||k.type==="group");const v=variedAmong(T,sib);if(v.length<2)return null;
 return v.map(c=>{const cnt={};Object.values(c.by).forEach(t=>cnt[t]=(cnt[t]||0)+1);const mode=Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0][0];const odd=sib.filter(n=>c.by[n.fact_id]&&c.by[n.fact_id]!==mode);return {f:c.f,mode,odd:odd.map(n=>({n,v:c.by[n.fact_id]}))}})}
function groupRuns(T,gid){const out=[];(function w(x){(T.kids[x]||[]).forEach(k=>{if(k.type==="run")out.push(k.fact_id);if(k.type==="run"||k.type==="group")w(k.fact_id)})})(gid);return out}
function groupCard(d,i,gid){const T=buildTree(d),g=T.byId[gid];const ids=groupRuns(T,gid);const rs=RUNS().filter(r=>r.i===i&&ids.includes(r.id));const sib=(T.kids[gid]||[]).filter(k=>k.type==="run"||k.type==="group");const v=variedAmong(T,sib);
 const r1=v.map(c=>`<span class="chip diff">${qlab(c.f)}: ${[...new Set(Object.values(c.by))].map(esc).join(" / ")}</span>`).join(" ")||'<span class="mut">none</span>';
 const r2=rs.map(r=>`<span class="chip" onclick="openCard(${i},'${r.id}')">${esc(nlab(r.n))}</span>`).join(" ")||'<span class="mut">none</span>';
 const rep=reproOf(i);const keys={};rs.forEach(r=>Object.entries(r.res).forEach(([k,o])=>{const a=firstNum(o);if(a!=null){(keys[k]=keys[k]||{f:o.f,vals:[]});keys[k].vals.push(a)}}));
 const lines=Object.entries(keys).filter(([k,o])=>o.vals.length>=2).map(([k,o])=>{const eff=Math.max(...o.vals)-Math.min(...o.vals);const u=o.f.unit?" "+o.f.unit:"";const sd=rep&&rep.sd[k]?rep.sd[k].sd:null;const ratio=sd?eff/sd:null;
  return `<div class="fl2 ${ratio!=null&&ratio<1?"within":""}">${qlab(o.f)}: <span class="num">${fmtv(eff)}${esc(u)}</span> <span class="mut">(${o.vals.length} runs)</span>${sd!=null?` = <b>${ratio.toFixed(1)} × sd</b>${ratio<1?' <span class="inf">within reproducibility</span>':""}`:' <span class="mut">no sd</span>'}</div>`}).join("");
 const r3=(rep?`<div class="mut">sd from ${rep.runs.map(r=>esc(nlab(r.n))).join(" · ")}, ${Object.keys(rep.sd).length} quantities</div>`:'<div class="mut">no reproducibility set in this paper</div>')+(lines||'<div class="mut">no result on two or more runs</div>');
 const cf=confound(T,gid);const ns=naturalSeries(i).map((sr,j)=>[sr,j]).filter(([sr])=>sr.runs.some(r=>ids.includes(r.id)));
 const r4=(cf?`<div class="fl2"><span class="inf">confounded</span> ${cf.length} settings differ: ${cf.map(c=>`<span class="chip diff">${qlab(c.f)}: ${c.odd.map(o=>`${esc(nlab(o.n))} ${esc(o.v)}`).join(", ")} <span class="mut">(others ${esc(c.mode)})</span></span>`).join(" ")}</div>`:'<div class="fl2 mut">one setting varies, as the group states</div>')+(ns.map(([sr,j])=>seriesLine(i,sr,j)).join("")||'<div class="fl2 mut">no natural series through these runs</div>');
 return `<div class="card"><h2>${esc(nlab(g))} <span class="mut" style="font-size:12px;font-weight:400">${esc(gid)}</span></h2><div class="mut">${esc(g.statement)}</div><section><h4>varied</h4>${r1}</section><section><h4>runs</h4>${r2}</section><section><h4>effect ÷ sd</h4>${r3}</section><section><h4>natural series</h4>${r4}</section><div id="side" class="evbox"></div></div>`}
function compareWith(i,id){const v=document.getElementById("cmp").value;if(!v)return;const [j,rid]=v.split("|");WB.tray=[{i,id},{i:+j,id:rid}];TM="find";render()}
function figureCard(d,i,eid){const T=buildTree(d);const e=d.elements.find(x=>x.id===eid);const fs=d.facts.filter(f=>f.evidence.split(";").includes(eid));
 const runOf=id=>{let x=T.up[id];while(x&&T.byId[x]&&T.byId[x].type!=="run")x=T.up[x];return x&&T.byId[x]?x:null};
 const runs=[...new Set(fs.map(f=>runOf(f.fact_id)).filter(Boolean))];const groups=[...new Set(runs.map(r=>grpOf(T,r)).concat(fs.map(f=>grpOf(T,f.fact_id))).filter(Boolean))];
 const r1=groups.map(g=>`<span class="chip">${esc(nlab(T.byId[g]))}</span>`).join(" ")||'<span class="mut">—</span>';
 const r2=runs.map(r=>`<span class="chip" onclick="openCard(${i},'${r}')">${esc(nlab(T.byId[r]))}</span>`).join(" ")||'<span class="mut">—</span>';
 const other={};runs.forEach(r=>subtree(T,r).forEach(f=>f.evidence.split(";").forEach(x=>{if(x===eid||x.endsWith(".cap")||!/^(fig|tab)/.test(x))return;const k=elab(x);(other[k]=other[k]||{x,panel:d.elements.some(z=>z.id===x&&z.kind==="panel"),n:new Set()}).n.add(f.fact_id)})));
 const r3=Object.entries(other).sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true})).map(([k,o])=>`<span class="chip" onclick="${o.panel?`figCard('${o.x}',${i})`:`side('${o.x}',${i})`}">${esc(k)} <span class="mut">${o.n.size}</span></span>`).join(" ")||'<span class="mut">—</span>';
 const ids=new Set(fs.map(f=>f.fact_id).concat(runs,groups));const claims=d.facts.filter(c=>c.type==="claim"&&c.links&&c.links.split(";").some(l=>ids.has(l)||runs.includes(runOf(l))||groups.includes(grpOf(T,l))));
 const r4=claims.map(c=>claimLine(d,i,c)).join("")||'<div class="mut">—</div>';
 return `<div class="card"><h2>${esc(elab(eid))} <span class="mut" style="font-size:12px;font-weight:400">${esc(eid)}${e?" · "+esc(e.loc):""} · ${fs.length} facts</span> ${figTrayBtn(i,eid)}</h2>${e&&e.crop&&d.imgs[e.crop]?`<img class="fig" src="${d.imgs[e.crop]}" onclick="side('${eid}',${i})">`:""}
 <section><h4>compares</h4>${r1}</section><section><h4>runs</h4>${r2}</section><section><h4>also on these runs</h4>${r3}</section><section><h4>claims</h4>${r4}</section>
 <div id="side" class="evbox"></div></div>`}
// claim scope (computed): links -> runs (a linked run, the runs of a linked group, the run above a linked fact) -> inherited settings -> ranges
function claimRuns(T,c){const runs=new Set();(c.links||"").split(";").filter(Boolean).forEach(l=>{let x=l;while(x&&T.byId[x]&&!["run","group"].includes(T.byId[x].type))x=T.up[x];if(!x||!T.byId[x])return;
 if(T.byId[x].type==="run")runs.add(x);else (function w(g){(T.kids[g]||[]).forEach(k=>{if(k.type==="run")runs.add(k.fact_id);if(k.type==="run"||k.type==="group")w(k.fact_id)})})(x)});return [...runs]}
const SCOPEQ=["deposition_temperature","feature_height","cycle_number","process_pressure","plasma_gas_ratio","exposure"];const fmtv=v=>String(+v.toPrecision(4));
function claimScope(d,i,c){const T=buildTree(d);const runs=claimRuns(T,c);if(!runs.length)return {n:0,runs,text:"no run"};const rs=RUNS().filter(r=>r.i===i&&runs.includes(r.id));const parts=[];
 SCOPEQ.forEach(q=>{const vals=[],units=new Set();rs.forEach(r=>{const es=Object.values(r.inh).filter(e=>e.f.quantity===q);const plain=es.filter(e=>!e.f.qualifiers);(plain.length?plain:es).forEach(e=>e.fs.forEach(f=>{const a=fv(f);if(a!=null&&!isNaN(a)){vals.push(a);units.add(f.unit||"")}}))});
  if(vals.length&&units.size===1){const lo=Math.min(...vals),hi=Math.max(...vals),u=[...units][0];parts.push(`${LISTS.labels[q]||q} ${lo===hi?fmtv(lo):fmtv(lo)+"–"+fmtv(hi)}${u?" "+u:""}`)}});
 return {n:runs.length,runs,text:`${runs.length} run${runs.length>1?"s":""}${parts.length?" · "+parts.slice(0,3).join(" · "):""}`}}
function claimLine(d,i,c){const sc=claimScope(d,i,c);const e=c.evidence.split(";")[0];return `<div class="clr" data-f="${c.fact_id}"><span class="ty claim">claim</span><span class="st">${esc(c.statement)}</span><span class="chip scope ${sc.n?"":"mut"}" title="runs behind the claim">${esc(sc.text)}</span><code class="ev" onclick="side('${e}',${i})">${e}</code></div>`}
function userScope(u){const runs=[];DATA.forEach((d,i)=>{const T=buildTree(d);claimRuns(T,{links:(u.links||"").split(";").filter(l=>l.startsWith(d.key+":")).join(";")}).forEach(r=>runs.push({i,id:r}))});
 if(!runs.length)return "no run";const rs=RUNS().filter(r=>runs.some(x=>x.i===r.i&&x.id===r.id));const parts=[];
 SCOPEQ.forEach(q=>{const vals=[],units=new Set();rs.forEach(r=>{const es=Object.values(r.inh).filter(e=>e.f.quantity===q);const plain=es.filter(e=>!e.f.qualifiers);(plain.length?plain:es).forEach(e=>e.fs.forEach(f=>{const a=fv(f);if(a!=null&&!isNaN(a)){vals.push(a);units.add(f.unit||"")}}))});
  if(vals.length&&units.size===1){const lo=Math.min(...vals),hi=Math.max(...vals),u=[...units][0];parts.push(`${LISTS.labels[q]||q} ${lo===hi?fmtv(lo):fmtv(lo)+"–"+fmtv(hi)}${u?" "+u:""}`)}});
 const papers=[...new Set(runs.map(x=>DATA[x.i].key))];return `${runs.length} run${runs.length>1?"s":""} in ${papers.join(", ")}${parts.length?" · "+parts.slice(0,3).join(" · "):""}`}
function userLine(u){const n=(u.links||"").split(";").filter(Boolean).length;return `<div class="clr user" data-f="${u.fact_id}"><span class="ty claim">${esc(u.type)}</span><span class="st">${esc(u.statement)}</span><span class="chip scope">${esc(userScope(u))}</span><span class="mut">${n} links</span>${u.label_as_printed?`<span class="chip">${esc(u.label_as_printed)}</span>`:""}</div>`}
function claimsView(){return `<div class="wrap"><div class="cl"><h3>user <span class="mut">${USER.length} facts</span></h3>${USER.map(userLine).join("")}${DATA.map((d,i)=>`<h3><span class="sw" style="background:var(--c${i})"></span>${d.key} <span class="mut">${d.facts.filter(f=>f.type==="claim").length} claims</span></h3>`+d.facts.filter(f=>f.type==="claim").map(c=>claimLine(d,i,c)).join("")).join("")}</div><div class="side" id="side"><span class="mut">Click an element id for the element and its facts.</span></div></div>`}
function treeView(){const tog=`<div class="fl">${[["find","find"],["cards","cards"],["text","text tree"],["claims","claims"]].map(([k,l])=>`<button class="${TM===k?"on":""}" onclick="TM='${k}';render()">${l}</button>`).join("")}</div>`;
 if(TM==="find")return `<div id="forest"></div>${tog}${wbView()}`;if(TM==="claims")return `<div id="forest"></div>${tog}${claimsView()}`;
 if(TM==="cards"){const d=DATA[P];if(CARD&&!buildTree(d).byId[CARD])CARD=null;if(!CARD){const first=d.tree.find(n=>n.type==="run");CARD=first?first.fact_id:null}if(FIGC&&!d.elements.some(x=>x.id===FIGC))FIGC=null;if(GCARD&&!buildTree(d).byId[GCARD])GCARD=null;
  return `<div id="forest"></div>${tog}<div class="wrap2"><div>${leftTree(d,P)}</div><div id="cardpane">${FIGC?figureCard(d,P,FIGC):GCARD?groupCard(d,P,GCARD):CARD?card(d,P,CARD):'<div class="card mut">no runs</div>'}</div></div>`}
 const body=DATA.map((d,i)=>{const T=buildTree(d);if(!T.root)return `<div class="tree"><b>${d.key}</b> <span class="mut">no tree yet</span></div>`;return `<div class="tree" id="tree${i}">${node(T.root,i,T,i===P)}</div>`}).join("");
 return `<div id="forest"></div>${tog}<div class="wrap"><div>${body}</div><div class="side" id="side"><span class="mut">Click an element id to see the element, its crop and its facts.</span></div></div>`}
function figView(d){const ps=d.elements.filter(e=>e.kind==="panel");const T=buildTree(d);return ps.map(e=>{const fs=factsOf(d,e.id);const tr=fs.some(f=>{const r=runOfF(T,f.fact_id);return r&&trayHas(P,r)});
 return `<div class="panel ${tr?"tray":""}"><div><h3><span class="lnk" onclick="figCard('${e.id}',P)">${e.id}</span> <span class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""} · ${fs.length} facts</span></h3>${d.imgs[e.crop]?`<img loading="lazy" src="${d.imgs[e.crop]}" style="cursor:pointer" onclick="figCard('${e.id}',P)">`:"<i>no crop</i>"}</div>
 <div>${fs.map(f=>factHTML(f,P)).join("")||"<i class='mut'>no facts</i>"}</div></div>`}).join("")}
function render(){const d=DATA[P];
 $("#papers").innerHTML=DATA.map((x,i)=>`<button class="${i===P?"on":""}" onclick="P=${i};render();if(V==='tree'){const t=document.getElementById('tree'+${i});if(t)t.scrollIntoView()}">${x.key}</button>`).join(" ");
 $("#views").innerHTML=[["read","(a) paper"],["tree","(b) cards / tree"],["figs","(c) figures"]].map(([k,l])=>`<button class="${V===k?"on":""}" onclick="V='${k}';render()">${l}</button>`).join(" ");
 const s=d.summary||{};const st={};d.elements.forEach(e=>st[e.st]=(st[e.st]||0)+1);
 const tn=s.text_numbers||[0,0];
 $("#sum").innerHTML=`<div class="tile"><b>${d.elements.length}</b><span>${esc(d.pid)}<br>elements</span></div>
 <div class="tile"><b>${st.covered||0} / ${st["no knowledge"]||0} / ${st.missed||0}</b><span>covered / no knowledge / missed</span></div>
 <div class="tile"><b>${d.facts.length}</b><span>facts</span></div>
 <div class="tile"><b>${d.tree.filter(n=>n.type==="run").length} / ${d.tree.filter(n=>n.type==="group").length} / ${d.tree.filter(n=>n.type==="cited").length}</b><span>tree: runs / groups / cited works (not facts)</span></div>
 <div class="tile"><b>${tn[1]?Math.round(100*tn[0]/tn[1]):0}%</b><span>numbers in text reaching a fact (${tn[0]}/${tn[1]})</span></div>
 <div class="tile"><b>${Object.entries(s.panels||{}).map(([k,v])=>v).join(" / ")}</b><span>panels: ${Object.keys(s.panels||{}).join(" / ")}</span></div>`;
 $("#view").innerHTML=V==="read"?readView(d):V==="tree"?treeView():figView(d);if(V==="tree"){applyForest();fitChips()}}
window.openCard=openCard;window.cardFor=cardFor;window.toggleChips=toggleChips;window.showCard=showCard;window.compareWith=compareWith;window.figCard=figCard;window.openGroup=openGroup;window.seriesTray=seriesTray;window.wbSet=wbSet;window.wbT=wbT;window.wbRange=wbRange;window.wbClear=wbClear;window.trayAdd=trayAdd;window.trayAddFig=trayAddFig;window.trayDrop=trayDrop;window.trayClear=trayClear;
render();
</script></body></html>"""

OUTER = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot Report</title><style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--line:#e2dfd8;--acc:#1f5fa8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#e8e6e1;--line:#33352f;--acc:#7fb0ef}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#e8e6e1;--line:#33352f;--acc:#7fb0ef}
html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font:14px system-ui,-apple-system,Segoe UI,sans-serif}
nav{display:flex;gap:6px;padding:8px 16px;border-bottom:1px solid var(--line);height:44px;box-sizing:border-box;align-items:center}
nav b{margin-right:10px}button{font:inherit;color:inherit;background:transparent;border:1px solid var(--line);border-radius:6px;padding:4px 12px;cursor:pointer}
button.on{border-color:var(--acc);color:var(--acc);font-weight:600}iframe{display:none;border:0;width:100%;height:calc(100% - 44px);background:#fff}iframe.on{display:block}
</style></head><body><nav><b>PSED pilot</b>__BUTTONS__</nav>__FRAMES__
<script>
function tab(k){document.querySelectorAll("nav button,iframe").forEach(n=>n.classList.toggle("on",n.dataset.k===k))}
function openCase(k){tab("matrix");const w=document.querySelector('iframe[data-k="matrix"]').contentWindow;if(w.openCase)w.openCase(k)}
tab("facts");
</script></body></html>"""


if __name__ == "__main__":
    data = [paper(pid, k) for pid, k in KEYS.items()]
    lists = dict(materials=L.MATERIALS, structures=L.STRUCTURES, methods=L.METHODS, quantities=L.QUANTITIES, labels=L.LABELS)
    user = rd(HERE / "user.facts.csv")
    facts_page = (PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")).replace("__LISTS__", json.dumps(lists))
                  .replace("__USER__", json.dumps(user, ensure_ascii=False).replace("</", "<\\/")))
    cases_page = runpy.run_path(str(HERE / "cases.py"))["main"]()
    matrix_page = runpy.run_path(str(HERE / "matrix.py"))["page"]
    tabs = [("facts", "Facts", facts_page), ("cases", "Cases", cases_page), ("matrix", "Matrix", matrix_page)]
    out = HERE / "reports/pilot.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(OUTER.replace("__BUTTONS__", "".join(f'<button data-k="{k}" onclick="tab(\'{k}\')">{t}</button>' for k, t, _ in tabs))
                   .replace("__FRAMES__", "".join(f'<iframe data-k="{k}" title="{t}" srcdoc="{html.escape(p, quote=True)}"></iframe>' for k, t, p in tabs)),
                   encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")
