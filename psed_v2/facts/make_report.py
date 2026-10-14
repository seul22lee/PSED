#!/usr/bin/env python3
"""Writes facts/reports/facts.html (untracked; self-contained, works offline): per paper
(a) the paper in reading order, each element coloured covered / no knowledge / missed, click for its facts;
(b) facts by type with counts, filterable; (c) figures: each panel's crop next to its facts.

    python3 psed_v2/facts/make_report.py

Embeds element texts and figure crops from ingest/final, so the page must stay out of git.
"""
import base64, csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
from check import KEYS, summary  # noqa: E402


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def paper(pid, key):
    d = HERE / pid
    els, facts, cov = rd(d / "elements.csv"), rd(d / "facts.csv"), {c["element_id"]: c for c in rd(d / "coverage.csv")}
    texts = C.element_texts(pid)
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
        if f["points_ref"] and (d / f["points_ref"]).exists():
            f["points"] = json.loads((d / f["points_ref"]).read_text(encoding="utf-8")).get("points", [])
    s = summary({e["element_id"]: e for e in els}, facts, list(cov.values())) if facts else {}
    return dict(pid=pid, key=key, elements=E, facts=facts, imgs=imgs, summary=s)


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
h2{font-size:15px;margin:16px 0 6px}h3{font-size:14px;margin:10px 0 4px}.mut{color:var(--mut)}svg.pts{width:100%;height:150px;background:var(--card);border:1px solid var(--line);border-radius:4px}
</style></head><body>
<header><h1>Facts layer: pilot papers</h1><span id="papers"></span><span id="views"></span>
<span class="legend"><span style="background:var(--cov)">covered</span><span style="background:var(--nk)">no knowledge</span><span style="background:var(--miss)">missed</span></span></header>
<main><div class="sum" id="sum"></div><div id="view"></div></main>
<script>
const DATA=__DATA__;
let P=0,V="read";
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
function side(id){const d=DATA[P],e=d.elements.find(x=>x.id===id);document.querySelectorAll(".sel").forEach(x=>x.classList.remove("sel"));
 document.querySelectorAll(`[data-id="${id}"]`).forEach(x=>x.classList.add("sel"));const fs=factsOf(d,id);
 $("#side").innerHTML=`<h3>${esc(id)} <span class="mut">${esc(e.loc)}</span></h3><div class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""}${e.nn!==""?` · numbers ${e.nr}/${e.nn} reach a fact`:""}</div>
 ${e.crop&&d.imgs[e.crop]&&e.kind==="panel"?`<img src="${d.imgs[e.crop]}" style="max-width:100%;margin-top:6px">`:""}${fs.map(factHTML).join("")||""}`}
function goto(id){V="read";render();setTimeout(()=>{const n=document.querySelector(`[data-id="${id}"]`);if(n)n.scrollIntoView({block:"center"});side(id)},0)}
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
let FT="",FQ="",FS="";
function factsView(d){const types=["setting","observation","derived","model","definition","claim","cited"];const cnt={};d.facts.forEach(f=>cnt[f.type]=(cnt[f.type]||0)+1);
 const qs=[...new Set(d.facts.map(f=>f.quantity).filter(Boolean))].sort();
 const rows=d.facts.filter(f=>(!FT||f.type===FT)&&(!FQ||f.quantity===FQ)&&(!FS||JSON.stringify(f).toLowerCase().includes(FS.toLowerCase())));
 return `<div class="fl">${["",...types].map(t=>`<button class="${FT===t?"on":""}" onclick="FT='${t}';render()">${t||"all"} (${t?cnt[t]||0:d.facts.length})</button>`).join("")}
 <select onchange="FQ=this.value;render()"><option value="">any quantity</option>${qs.map(q=>`<option ${q===FQ?"selected":""}>${q}</option>`).join("")}</select>
 <input placeholder="search" value="${esc(FS)}" onchange="FS=this.value;render()"> <span class="mut">${rows.length} shown</span></div>
 <div style="overflow-x:auto"><table class="ft"><tr><th>id</th><th>type</th><th>statement</th><th>quantity</th><th>value</th><th>kind / method</th><th>mentions</th><th>evidence</th></tr>
 ${rows.map(f=>`<tr><td><code>${esc(f.fact_id.split(":")[1])}</code></td><td>${f.type}</td><td>${esc(f.statement)}</td><td>${esc(f.quantity)}${f.label_as_printed?` <span class="mut">${esc(f.label_as_printed)}</span>`:""}${f.qualifiers?`<br><span class="mut">${esc(f.qualifiers)}</span>`:""}</td>
 <td>${esc(f.censor+f.value)}${f.value_min||f.value_max?` ${esc(f.value_min)}–${esc(f.value_max)}`:""} ${esc(f.unit)}${f.points_ref?`<br><span class="mut">${f.points?f.points.length:""} pts</span>`:""}</td>
 <td>${esc(f.data_kind)}<br><span class="mut">${esc(f.method)}</span></td><td>${esc(f.mentions)}</td><td>${f.evidence.split(";").map(e=>`<span class="lnk" onclick="goto('${e}')">${e}</span>`).join(" ")}</td></tr>`).join("")}</table></div>`}
function figView(d){const ps=d.elements.filter(e=>e.kind==="panel");return ps.map(e=>{const fs=factsOf(d,e.id);
 return `<div class="panel"><div><h3>${e.id} <span class="mut">${esc(e.st)}${e.why?": "+esc(e.why):""} · ${fs.length} facts</span></h3>${d.imgs[e.crop]?`<img loading="lazy" src="${d.imgs[e.crop]}">`:"<i>no crop</i>"}</div>
 <div>${fs.map(factHTML).join("")||"<i class='mut'>no facts</i>"}</div></div>`}).join("")}
function render(){const d=DATA[P];
 $("#papers").innerHTML=DATA.map((x,i)=>`<button class="${i===P?"on":""}" onclick="P=${i};FT=FQ=FS='';render()">${x.key}</button>`).join(" ");
 $("#views").innerHTML=[["read","(a) paper"],["facts","(b) facts"],["figs","(c) figures"]].map(([k,l])=>`<button class="${V===k?"on":""}" onclick="V='${k}';render()">${l}</button>`).join(" ");
 const s=d.summary||{};const st={};d.elements.forEach(e=>st[e.st]=(st[e.st]||0)+1);
 const tn=s.text_numbers||[0,0];
 $("#sum").innerHTML=`<div class="tile"><b>${d.elements.length}</b><span>${esc(d.pid)}<br>elements</span></div>
 <div class="tile"><b>${st.covered||0} / ${st["no knowledge"]||0} / ${st.missed||0}</b><span>covered / no knowledge / missed</span></div>
 <div class="tile"><b>${d.facts.length}</b><span>facts</span></div>
 <div class="tile"><b>${tn[1]?Math.round(100*tn[0]/tn[1]):0}%</b><span>numbers in text reaching a fact (${tn[0]}/${tn[1]})</span></div>
 <div class="tile"><b>${Object.entries(s.panels||{}).map(([k,v])=>v).join(" / ")}</b><span>panels: ${Object.keys(s.panels||{}).join(" / ")}</span></div>`;
 $("#view").innerHTML=V==="read"?readView(d):V==="facts"?factsView(d):figView(d)}
render();
</script></body></html>"""

if __name__ == "__main__":
    data = [paper(pid, k) for pid, k in KEYS.items()]
    out = HERE / "reports/facts.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")
