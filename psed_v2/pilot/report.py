#!/usr/bin/env python3
"""Writes reports/pilot.html, the one report page of the pilot (untracked; self-contained, works offline), with three tabs:
- Facts, per paper: (a) the paper in reading order, each element coloured covered / no knowledge / missed, click for its
  facts; (b) the paper as one collapsible tree (root -> process -> groups -> runs -> facts; claims and cited works as
  branches), one line per node with statement, value and element id (click = the element and its crop); among sibling
  runs only the settings that differ are bold; expanding a claim shows its linked facts; (c) figures: each panel's crop
  next to its facts. Tree rows (ids without "#") are not counted as facts anywhere.
- Cases: the thirteen case studies (cases.py; Case 8 draws on cremers.py).
- Matrix: quantities per paper and papers x cases (matrix.py).

    python3 psed_v2/pilot/report.py

Embeds element texts and figure crops from ingest/final (and a page of the review PDF for the cases), so the page stays
out of git. Each tab is its own document in an iframe, so the three views keep their styles and scripts apart.
"""
import base64, csv, html, json, runpy, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import elements  # noqa: E402
from check import KEYS, summary  # noqa: E402


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def paper(pid, key):
    els, rows = rd(HERE / f"{pid}.elements.csv"), rd(HERE / f"{pid}.facts.csv")
    facts = [r for r in rows if "#" in r["fact_id"]]
    tree = [r for r in rows if "#" not in r["fact_id"]]
    cov = {c["element_id"]: c for c in rd(HERE / f"{pid}.coverage.csv")}
    pts = json.loads((HERE / f"{pid}.points.json").read_text(encoding="utf-8")) if (HERE / f"{pid}.points.json").exists() else {}
    texts = elements.texts(pid)
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
    s = summary({e["element_id"]: e for e in els}, facts, list(cov.values())) if facts else {}
    return dict(pid=pid, key=key, elements=E, facts=facts, tree=tree, imgs=imgs, summary=s)


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot Facts Layer</title><style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--card:#fff;--cov:#d8eedb;--covb:#2e7d3a;--nk:#ecebe7;--nkb:#9a978f;
--miss:#f7d6d2;--missb:#b3261e;--acc:#1f5fa8;--sel:#fff3c4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#e8e6e1;--mut:#a3a19b;--line:#33352f;--card:#1f2123;
--cov:#1f3a25;--covb:#6cc37a;--nk:#2a2b2d;--nkb:#77756f;--miss:#4a1f1c;--missb:#ff8a80;--acc:#7fb0ef;--sel:#4a4226}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#e8e6e1;--mut:#a3a19b;--line:#33352f;--card:#1f2123;--cov:#1f3a25;--covb:#6cc37a;--nk:#2a2b2d;
--nkb:#77756f;--miss:#4a1f1c;--missb:#ff8a80;--acc:#7fb0ef;--sel:#4a4226}
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
.flag{font:600 10px/1.4 ui-monospace,monospace;color:var(--missb);border:1px solid var(--missb);border-radius:3px;padding:0 3px;margin-left:4px}
h2{font-size:15px;margin:16px 0 6px}h3{font-size:14px;margin:10px 0 4px}.mut{color:var(--mut)}svg.pts{width:100%;height:150px;background:var(--card);border:1px solid var(--line);border-radius:4px}
</style></head><body>
<header><h1>Facts layer: pilot papers</h1><span id="papers"></span><span id="views"></span>
<span class="legend"><span style="background:var(--cov)">covered</span><span style="background:var(--nk)">no knowledge</span><span style="background:var(--miss)">missed</span></span></header>
<main><div class="sum" id="sum"></div><div id="view"></div></main>
<script>
const DATA=__DATA__;
let P=0,V="read",SP=0;
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const clean=s=>esc(String(s||"").replace(/\\text\{([^}]*)\}|\\mathrm\{([^}]*)\}/g,"$1$2").replace(/<\/?sup>/g,"").replace(/\$/g,""));
function factsOf(d,id){return d.facts.filter(f=>f.evidence.split(";").includes(id))}
function factHTML(f){const q=[f.quantity&&(f.quantity+(f.label_as_printed?` (${f.label_as_printed})`:"")),f.qualifiers].filter(Boolean).join(" · ");
 const v=[f.censor+f.value,f.value_min&&f.value_max?`${f.value_min}–${f.value_max}`:(f.value_min||f.value_max)].filter(Boolean).join(" ");
 return `<div class="fact"><div class="t">${esc(f.type)} <code class="mut">${esc(f.fact_id)}</code></div><div>${esc(f.statement)}</div>
 <div class="m">${q?esc(q):""}${v?` = <b>${esc(v)} ${esc(f.unit)}</b>`:""}${f.data_kind?` · ${esc(f.data_kind)}`:""}${f.method?` · ${esc(f.method)}`:""}${f.points_ref?` · ${f.points?f.points.length:"?"} points`:""}</div>
 ${f.mentions?`<div class="m">mentions: ${esc(f.mentions)}</div>`:""}${f.inputs?`<div class="m">inputs: ${esc(f.inputs)}</div>`:""}
 <div class="m">evidence: ${f.evidence.split(";").map(e=>`<span class="lnk" onclick="goto('${e}')">${e}</span>`).join(", ")}</div>${f.points?plot(f.points):""}</div>`}
function plot(p){if(!p.length)return"";const xs=p.map(a=>a[0]),ys=p.map(a=>a[1]);const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
 const X=x=>8+284*(x-x0)/((x1-x0)||1),Y=y=>142-134*(y-y0)/((y1-y0)||1);
 return `<svg class="pts" viewBox="0 0 300 150"><polyline fill="none" stroke="var(--acc)" stroke-width="1.5" points="${p.map(a=>X(a[0])+","+Y(a[1])).join(" ")}"/>
 <text x="8" y="12" font-size="9" fill="var(--mut)">y ${y0}…${y1}; x ${x0}…${x1}</text></svg>`}
function side(id,pi){if(pi!==undefined)SP=pi;else SP=P;const d=DATA[SP],e=d.elements.find(x=>x.id===id);if(!e)return;document.querySelectorAll(".sel").forEach(x=>x.classList.remove("sel"));
 document.querySelectorAll(`[data-id="${id}"]`).forEach(x=>x.classList.add("sel"));const fs=factsOf(d,id);
 $("#side").innerHTML=`<h3>${esc(id)} <span class="mut">${esc(e.loc)}</span></h3><div class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""}${e.nn!==""?` · numbers ${e.nr}/${e.nn} reach a fact`:""}</div>
 ${e.crop&&d.imgs[e.crop]&&e.kind==="panel"?`<img src="${d.imgs[e.crop]}" style="max-width:100%;margin-top:6px">`:""}${fs.map(factHTML).join("")||""}`}
function goto(id){P=SP;V="read";render();setTimeout(()=>{const n=document.querySelector(`[data-id="${id}"]`);if(n)n.scrollIntoView({block:"center"});side(id,P)},0)}
function readView(d){let h="",tabs={};const els=d.elements;
 for(const e of els){if(e.kind==="table_cell"){(tabs[e.sec]=tabs[e.sec]||[]).push(e);continue}
  const cls=e.st==="covered"?"covered":e.st==="missed"?"missed":"";
  if(e.kind==="panel"){h+=`<div class="el ${cls}" data-id="${e.id}" onclick="side('${e.id}')"><span class="id">${e.id}</span><i>panel ${esc(e.loc)}</i></div>`;continue}
  if(e.id.endsWith(".cap")&&e.id.startsWith("tab")){h+=`<div class="el ${cls}" data-id="${e.id}" onclick="side('${e.id}')"><span class="id">${e.id}</span>${clean(e.text)}</div>`+`@@${e.id.slice(0,-4)}@@`;continue}
  h+=`<div class="el ${cls} ${e.kind}" data-id="${e.id}" onclick="side('${e.id}')"><span class="id">${e.id}</span>${clean(e.text)}</div>`}
 const grid=t=>{const cs=tabs[t]||[];const R={};for(const c of cs){const m=c.id.match(/r(\d+)c(\d+)$/);(R[m[1]]=R[m[1]]||{})[m[2]]=c}
  const nc=Math.max(0,...cs.map(c=>+c.id.match(/c(\d+)$/)[1]))+1;
  return `<div style="overflow-x:auto"><table class="grid">${Object.keys(R).sort((a,b)=>a-b).map(r=>"<tr>"+Array.from({length:nc},(_,j)=>{const c=R[r][j];
   return c?`<td class="${c.st==="covered"?"covered":c.st==="missed"?"missed":"nk"}" data-id="${c.id}" onclick="side('${c.id}')">${clean(c.text)}</td>`:"<td></td>"}).join("")+"</tr>").join("")}</table></div>`};
 for(const t of Object.keys(tabs)){if(h.includes(`@@${t}@@`))h=h.replace(`@@${t}@@`,grid(t));else h+=`<h3>${t} (no caption)</h3>`+grid(t)}
 return `<div class="wrap"><div>${h.replace(/@@[^@]+@@/g,"")}</div><div class="side" id="side"><span class="mut">Click an element to see its facts.</span></div></div>`}
const ORDER={paper:-1,process:0,group:1,run:2,setting:3,observation:4,derived:5,model:6,definition:7,claim:8,cited:9};
const valStr=f=>[f.censor+f.value,f.value_min&&f.value_max?`${f.value_min}–${f.value_max}`:(f.value_min||f.value_max)].filter(Boolean).join(" ")+(f.unit?" "+f.unit:"");
const skey=f=>f.quantity+"|"+f.qualifiers+"|"+(f.quantity==="other"?f.label_as_printed:"");
function buildTree(d){if(d._T)return d._T;const byId={},kids={};[...d.tree,...d.facts].forEach(n=>{byId[n.fact_id]=n;if(n.parent)(kids[n.parent]=kids[n.parent]||[]).push(n)});
 for(const k in kids)kids[k].sort((a,b)=>(ORDER[a.type]??5)-(ORDER[b.type]??5));
 const vary=new Set();                                   // among sibling runs, the settings whose value differs or is missing in a sibling
 for(const k in kids){const runs=kids[k].filter(n=>n.type==="run");if(runs.length<2)continue;
  const per=runs.map(r=>{const m={};(kids[r.fact_id]||[]).filter(f=>f.type==="setting").forEach(f=>{m[skey(f)]=(m[skey(f)]?m[skey(f)]+"; ":"")+valStr(f)});return m});
  const keys=new Set(per.flatMap(m=>Object.keys(m)));
  for(const key of keys){if(new Set(per.map(m=>m[key]??"∅")).size>1)runs.forEach(r=>(kids[r.fact_id]||[]).forEach(f=>{if(f.type==="setting"&&skey(f)===key)vary.add(f.fact_id)}))}}
 const root=d.tree.find(n=>n.type==="paper");const up={};[...d.tree,...d.facts].forEach(n=>up[n.fact_id]=n.parent);
 return d._T={byId,kids,vary,root,up}}
function line(n,i,T){const node=!n.fact_id.includes("#");const v=node?"":valStr(n);const ev=(n.evidence||"").split(";")[0];
 const q=node&&n.qualifiers?` <span class="mut">${esc(n.qualifiers)}</span>`:"";const lab=node&&n.label_as_printed?` <span class="mut">“${esc(n.label_as_printed)}”</span>`:"";
 const fl=(n.flag||[]).map(k=>`<span class="flag">${esc(k)}</span>`).join("");
 return `<span class="ty ${n.type}">${node?n.type:n.type.slice(0,3)}</span>${esc(n.statement)}${v?` <span class="v">${esc(v)}</span>`:""}${lab}${q}${fl}${ev?`<code class="ev" title="${esc(n.fact_id)}" onclick="event.preventDefault();event.stopPropagation();side('${ev}',${i})">${ev}</code>`:""}`}
function node(n,i,T,open){const ch=T.kids[n.fact_id]||[];const linked=n.type==="claim"&&n.links?n.links.split(";").map(l=>T.byId[l]).filter(Boolean):[];
 const cls=`nd${T.vary.has(n.fact_id)?" vary":""}`;
 if(!ch.length&&!linked.length)return `<div class="${cls} leaf" data-f="${n.fact_id}">${line(n,i,T)}</div>`;
 const op=open||n.type==="group"||n.type==="process"||(n.type==="paper"&&i===P);
 return `<details class="${cls}" data-f="${n.fact_id}" ${op?"open":""}><summary>${line(n,i,T)} <span class="mut">(${ch.length}${linked.length?`, ${linked.length} linked`:""})</span></summary>${linked.map(l=>`<div class="nd leaf linked" data-f="${l.fact_id}">${line(l,i,T)}</div>`).join("")}${ch.map(c=>node(c,i,T,false)).join("")}</details>`}
function treeView(){const trees=DATA.map((d,i)=>{const T=buildTree(d);if(!T.root)return `<div class="tree"><b>${d.key}</b> <span class="mut">no tree yet</span></div>`;
  return `<div class="tree" id="tree${i}">${node(T.root,i,T,i===P)}</div>`}).join("");
 return `<div id="forest"></div><div class="wrap"><div>${trees}</div><div class="side" id="side"><span class="mut">Click an element id to see the element, its crop and its facts.</span></div></div>`}
function figView(d){const ps=d.elements.filter(e=>e.kind==="panel");return ps.map(e=>{const fs=factsOf(d,e.id);
 return `<div class="panel"><div><h3>${e.id} <span class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""} · ${fs.length} facts</span></h3>${d.imgs[e.crop]?`<img loading="lazy" src="${d.imgs[e.crop]}">`:"<i>no crop</i>"}</div>
 <div>${fs.map(factHTML).join("")||"<i class='mut'>no facts</i>"}</div></div>`}).join("")}
function render(){const d=DATA[P];
 $("#papers").innerHTML=DATA.map((x,i)=>`<button class="${i===P?"on":""}" onclick="P=${i};render();if(V==='tree'){const t=document.getElementById('tree'+${i});if(t)t.scrollIntoView()}">${x.key}</button>`).join(" ");
 $("#views").innerHTML=[["read","(a) paper"],["tree","(b) tree"],["figs","(c) figures"]].map(([k,l])=>`<button class="${V===k?"on":""}" onclick="V='${k}';render()">${l}</button>`).join(" ");
 const s=d.summary||{};const st={};d.elements.forEach(e=>st[e.st]=(st[e.st]||0)+1);
 const tn=s.text_numbers||[0,0];
 $("#sum").innerHTML=`<div class="tile"><b>${d.elements.length}</b><span>${esc(d.pid)}<br>elements</span></div>
 <div class="tile"><b>${st.covered||0} / ${st["no knowledge"]||0} / ${st.missed||0}</b><span>covered / no knowledge / missed</span></div>
 <div class="tile"><b>${d.facts.length}</b><span>facts</span></div>
 <div class="tile"><b>${d.tree.filter(n=>n.type==="run").length} / ${d.tree.filter(n=>n.type==="group").length} / ${d.tree.filter(n=>n.type==="cited").length}</b><span>tree: runs / groups / cited works (not facts)</span></div>
 <div class="tile"><b>${tn[1]?Math.round(100*tn[0]/tn[1]):0}%</b><span>numbers in text reaching a fact (${tn[0]}/${tn[1]})</span></div>
 <div class="tile"><b>${Object.entries(s.panels||{}).map(([k,v])=>v).join(" / ")}</b><span>panels: ${Object.keys(s.panels||{}).join(" / ")}</span></div>`;
 $("#view").innerHTML=V==="read"?readView(d):V==="tree"?treeView():figView(d)}
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
    facts_page = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    cases_page = runpy.run_path(str(HERE / "cases.py"))["main"]()
    matrix_page = runpy.run_path(str(HERE / "matrix.py"))["page"]
    tabs = [("facts", "Facts", facts_page), ("cases", "Cases", cases_page), ("matrix", "Matrix", matrix_page)]
    out = HERE / "reports/pilot.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(OUTER.replace("__BUTTONS__", "".join(f'<button data-k="{k}" onclick="tab(\'{k}\')">{t}</button>' for k, t, _ in tabs))
                   .replace("__FRAMES__", "".join(f'<iframe data-k="{k}" title="{t}" srcdoc="{html.escape(p, quote=True)}"></iframe>' for k, t, p in tabs)),
                   encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")
