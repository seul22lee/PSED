#!/usr/bin/env python3
"""Writes schema_pilot/reports/pilot.html (the v2 tables, with a coverage view per paper) and schema_pilot/reports/kg.html
(the knowledge graph of kg/graph.json), both self-contained with inlined JS; reports/ is gitignored.

    python3 psed_v2/schema_pilot/v2/inventory.py && python3 psed_v2/schema_pilot/v2/kg.py && python3 psed_v2/schema_pilot/v2/make_reports.py

The element texts shown in the coverage view come from ingest/final (local only; the tracked tables hold ids, not text).
"""
import collections, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
sys.path.insert(0, str(PILOT)); sys.path.insert(0, str(HERE))      # v2 modules first (validate, inventory), then lists and checklist
from inventory import PAPERS, build
import validate as V2V

TABLES = ["paper", "sample", "condition", "series", "value"]
old = (PILOT / "make_report.py").read_text(encoding="utf-8")
ns = {"__file__": str(PILOT / "make_report.py")}
exec(old[old.index("import base64"):old.index("DATA = {}")].replace("from convert import PAPERS, COLS", "COLS = None").replace("import validate, lists as L", "import lists as L"), ns)
crop, V1_FALLBACK, V1_MISSES = ns["crop"], ns["V1_FALLBACK"], ns["V1_MISSES"]
TEMPLATE = old[old.index('page = """') + len('page = """'):old.index('"""\npage = page.replace')]


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def chain(pid, T):
    """The worked chain of each paper, found in its own tables."""
    S, C, SE, VA = T["sample"], T["condition"], T["series"], T["value"]
    groups = {g["sample_id"]: g["members"].split(";") for g in S if g["kind"] == "group"}
    inside = lambda sid: [sid] + [g for g, m in groups.items() if sid in m]
    if pid.startswith("10.1039"):
        s = next((x for x in S if x["label_as_printed"] in ("8", "sample 8", "S8") and x["kind"] in ("run", "piece")), None)
        if not s: return []
        sid = s["sample_id"]
        ser = next((x for x in SE if x["figure"] == "9" and x["panel"].startswith("c") and x["sample_id"] in inside(sid)), None)
        read = [v for v in VA if ser and v["from_series"] == ser["series_id"] and v["sample_id"] in inside(sid)][:1]
        slope = [v for v in VA if v["sample_id"] == sid and v["quantity"] == "front_slope" and v["data_kind"] == "fit"][:1]
        c = [v for v in VA if v["quantity"] == "lumped_sticking_coefficient" and v["data_kind"] == "calculated" and v["sample_id"] in inside(sid)][:1]
        return [(sid, "sample 8 (Table 1)"), ("cond", "its conditions and the paper-wide ones")] + ([(ser["series_id"], "its Fig. 9c profile")] if ser else []) + \
               [(v["value_id"], "read from that profile") for v in read] + [(v["value_id"], "front slope fitted by the authors") for v in slope] + \
               [(v["value_id"], "lumped sticking coefficient, calculated") for v in c]
    if pid.startswith("10.1021"):
        s = next((x for x in S if re.search(r"150", x["sample_id"]) and re.search(r"0?\.?80|R080|r0\.80", x["sample_id"])), None)
        if not s: return []
        sid = s["sample_id"]
        vals = [v for v in VA if v["sample_id"] == sid and v["from_series"]][:5]
        return [(sid, "one grid run: 150 °C, H2 ratio 0.80"), ("cond", "its conditions")] + [(v["value_id"], f"{v['quantity'] if v['quantity'] != 'other' else v['label_as_printed']} from {v['from_series'].split(':', 1)[1]}") for v in vals]
    s = next((x for x in S if x["kind"] == "run" and re.search(r"120(?!/|-)", x["sample_id"]) and not re.search(r"160", x["sample_id"])), None)
    if not s: return []
    sid = s["sample_id"]
    kids = [x["sample_id"] for x in S if x["parent_sample"] == sid]
    ser = [x for x in SE if x["sample_id"] in [sid] + kids][:3]
    vals = [v for v in VA if v["sample_id"] in [sid] + kids][:4]
    return [(sid, "the 120 °C run"), ("cond", "its conditions")] + [(x["series_id"], f"Fig. {x['figure']}{x['panel']} {x['method']}") for x in ser] + [(v["value_id"], v["quantity"] if v["quantity"] != "other" else v["label_as_printed"]) for v in vals]


def checklist_rows(pid, key):
    import checklist as CL
    CL.HERE = HERE
    if not (HERE / pid / "sample.csv").exists():
        return []
    CL.make(pid, key)
    rows = []
    for line in (HERE / pid / "checklist.md").read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 6 and p[1] and p[1] != "Core item" and not p[1].startswith("---"):
            rows.append(p[1:5])
    return rows


DATA, SHARES = {}, {}
for pid, key in PAPERS.items():
    T = {t: rd(HERE / pid / f"{t}.csv") for t in TABLES}
    if not T["sample"]:
        continue
    n, err, share = V2V.check(pid)
    SHARES[key] = share
    inv = rd(HERE / pid / "inventory.csv")
    cov = {c["element_id"]: c for c in rd(HERE / pid / "coverage.csv")}
    texts = build(pid)[1]
    allids = {r[k] for t, k in (("sample", "sample_id"), ("condition", "condition_id"), ("series", "series_id"), ("value", "value_id")) for r in T[t]}
    els = []
    for e in inv:
        c = cov.get(e["element_id"])
        st = "missed" if not c or (c["status"] == "covered" and not all(x in allids for x in re.split(r"[;,\s]+", c["rows"]) if x)) else ("covered" if c["status"] == "covered" else "no knowledge")
        els.append(dict(id=e["element_id"], kind=e["kind"], loc=e["locator"], n=e["n_numbers"], status=st, rows=[x for x in re.split(r"[;,\s]+", (c or {}).get("rows", "")) if x],
                        reason=(c or {}).get("reason", ""), text=re.sub(r"\s+", " ", texts.get(e["element_id"], ""))[:260]))
    figs = sorted({r["figure"] for r in T["series"] if r["figure"] and not r["figure"].startswith("Table")}, key=lambda f: (len(f), f))
    DATA[pid] = dict(key=key, title=T["paper"][0].get("topic", ""), year=T["paper"][0].get("year", ""), tables=T, counts=n, errors=err,
                     figs={f: crop(pid, f) for f in figs}, checklist=checklist_rows(pid, key), v1=V1_FALLBACK.get(pid, {}), v1misses=V1_MISSES[pid],
                     chain=chain(pid, T), npoints=sum(1 for r in T["series"] if r["points"]), nv1=sum(1 for r in T["series"] if r["points_source"].startswith("v1")),
                     elements=els, share={k: list(v) for k, v in share.items()})

COV_JS = r"""
function conditionView(id){const c=T.condition.find(x=>x.condition_id===id);if(!c)return;$("det").innerHTML=`<h3>${esc(id)} <span class="k">${esc(c.kind)}</span></h3><table><tr><th>sample</th><td>${c.sample_id==='*'?'* (whole paper)':lk('s',c.sample_id)}</td></tr><tr><th>quantity</th><td>${qv(c)}</td></tr><tr><th>value</th><td>${val(c)}</td></tr><tr><th>data</th><td>${esc(c.data_kind)}</td></tr><tr><th>applies when</th><td>${esc(c.applies_when)}</td></tr><tr><th>evidence</th><td>${esc(c.evidence)}</td></tr><tr><th>note</th><td>${esc(c.note)}</td></tr></table>`;}
function kindOf(id){if(T.sample.find(s=>s.sample_id===id))return 's';if(T.series.find(s=>s.series_id===id))return 'se';if(T.value.find(s=>s.value_id===id))return 'v';return 'c';}
const _open=open;open=function(k,id){if(k==='c')return conditionView(id);_open(k,id)};
function coverage(){const d=D[P];const sh=Object.entries(d.share).map(([k,[a,b]])=>`<span class="c"><b>${b?Math.round(100*a/b):0}%</b>${esc(k)} ${a}/${b}</span>`).join("");
 return `<h3>Coverage: the paper in reading order</h3><div class="cnt">${sh}</div><p class="pid">green: covered (click for its rows) · grey: no knowledge (reason) · red: missed</p><div class="covl">`+
 d.elements.map(e=>`<div class="el el-${e.status.replace(' ','-')}" data-e="${esc(e.id)}"><b>${esc(e.id)}</b> <span class="pid">${esc(e.kind)} · ${esc(e.loc)}${e.n?' · '+e.n+' numbers':''}</span><div class="tx">${esc(e.text)}</div>${e.status==='no knowledge'?'<div class="pid">'+esc(e.reason)+'</div>':''}</div>`).join("")+'</div>';}
document.addEventListener("click",e=>{const el=e.target.closest(".el");if(!el)return;const x=D[P].elements.find(z=>z.id===el.dataset.e);
 $("det").innerHTML=`<h3>${esc(x.id)} <span class="k">${esc(x.status)}</span></h3><p class="pid">${esc(x.loc)}</p><p>${esc(x.text)}</p>`+(x.rows.length?'<h4>Rows it produced</h4><ul>'+x.rows.map(r=>'<li>'+lk(kindOf(r),r)+'</li>').join("")+'</ul>':'<p class="pid">'+esc(x.reason)+'</p>');$("det").scrollIntoView({block:"nearest"});});
"""
COV_CSS = ".covl{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:6px}.el{border-left:5px solid var(--line);padding:3px 8px;margin:3px 0;cursor:pointer;font-size:12.5px}.el .tx{color:var(--text2);font-size:11.5px}.el-covered{border-color:var(--okb);background:var(--ok)}.el-no-knowledge{border-color:var(--line);background:var(--no)}.el-missed{border-color:#c0392b;background:var(--bad)}.c{display:inline-block;margin:0 8px 8px 0}"
page = TEMPLATE.replace("</style>", COV_CSS + "</style>").replace("<title>Schema pilot</title>", "<title>Schema pilot v2</title>")
page = page.replace("Schema pilot: five tables on three papers", "Schema pilot v2: five tables on three papers, grounded in the paper's elements")
page = page.replace("summary();tabs();show(Object.keys(D)[0]);", COV_JS + "summary();tabs();show(Object.keys(D)[0]);")
page = page.replace(" <h3>Checklist</h3>${cl}", " ${coverage()}\n <h3>Checklist</h3>${cl}")
page = page.replace("lk(id.includes(':v')?'v':(SE(id)?'se':'s'),id)", "lk(kindOf(id),id)")
page = page.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__LISTS__", "{}")
(PILOT / "reports").mkdir(exist_ok=True)
(PILOT / "reports" / "pilot.html").write_text(page, encoding="utf-8")
print("pilot.html", f"{len(page) / 1e6:.2f} MB")

# ----------------------------------------------------------------------------- kg.html
G = json.loads((HERE / "kg" / "graph.json").read_text(encoding="utf-8"))
nodes, edges = G["nodes"], G["edges"]
NID = {n["id"]: n for n in nodes}
adj = collections.defaultdict(set)
for e in edges:
    adj[e["source"]].add(e["target"]); adj[e["target"]].add(e["source"])


def of_type(nid, *types):
    return NID[nid]["type"] in types


def q_tma():
    out = {"chemical:TMA"}
    for e in edges:
        if e["type"] == "uses_chemical" and e["target"] == "chemical:TMA":
            s = e["source"]; out.add(s)
            paper = next(x["target"] for x in edges if x["source"] == s and x["type"] == "in_paper")
            grp = {x["target"] for x in edges if x["source"] == s and x["type"] == "member_of"}
            for x in edges:
                if x["type"] in ("of_sample", "of_paper") and of_type(x["source"], "condition") and (x["target"] == s or x["target"] in grp or (x["type"] == "of_paper" and x["target"] == paper)):
                    out.add(x["source"]); out.add(x["target"])
    return sorted(out)


def q_gpc():
    out = {"quantity:growth_per_cycle"}
    for e in edges:
        if e["type"] == "has_quantity" and e["target"] == "quantity:growth_per_cycle" and of_type(e["source"], "value"):
            out.add(e["source"])
            for x in edges:
                if x["source"] == e["source"] and x["type"] == "from_series":
                    out.add(x["target"])
    return sorted(out)


def q_run():
    run = next((n["id"] for n in nodes if n["type"] == "sample" and n["paper"] == "gre23" and n.get("kind") == "run" and re.search(r"120.?160", n["id"])), None)
    if not run:
        return []
    out = {run}
    kids = {e["source"] for e in edges if e["type"] == "child_of" and e["target"] == run}
    grp = {e["target"] for e in edges if e["type"] == "member_of" and e["source"] in kids | {run}}
    for e in edges:
        if e["type"] == "of_sample" and e["target"] in kids | {run} | grp and of_type(e["source"], "series", "value"):
            out.add(e["source"]); out.add(e["target"])
    return sorted(out)


start = [x for x, _ in DATA.get("10.1039_d0cp03358h", {}).get("chain", []) if x != "cond"]
start_nodes = set()
for x in start:
    for pre in ("sample:", "series:", "value:"):
        if pre + x in NID:
            start_nodes.add(pre + x)
for s in list(start_nodes):
    if s.startswith("sample:"):
        start_nodes |= {e["source"] for e in edges if e["target"] == s and e["type"] == "of_sample" and of_type(e["source"], "condition")}
Q = {"tma": q_tma(), "gpc": q_gpc(), "run": q_run(), "start": sorted(start_nodes)}
cnt_n = collections.Counter((n["type"], n["paper"] or "shared") for n in nodes)
cnt_e = collections.Counter(e["type"] for e in edges)
KGPAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pilot knowledge graph</title><style>
:root{--surface:#fcfcfb;--panel:#f3f2ee;--text:#1f1f1c;--text2:#55544e;--line:#d9d7cf;--accent:#184f95}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1600px;margin:0 auto;padding:16px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--text2);max-width:110ch;margin:0 0 10px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}button,select{font:inherit;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);cursor:pointer}
label{font-size:12.5px;color:var(--text2)}.wrap{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:12px}@media (max-width:900px){.wrap{grid-template-columns:1fr}}
svg#g{width:100%;height:640px;border:1px solid var(--line);border-radius:8px;background:var(--surface);touch-action:none}#side{border:1px solid var(--line);border-radius:8px;padding:10px;max-height:640px;overflow:auto;font-size:12.5px}
#side table{border-collapse:collapse;width:100%}#side td{border-bottom:1px solid var(--line);padding:2px 4px;vertical-align:top;overflow-wrap:anywhere}.nb{color:var(--accent);cursor:pointer}.lg{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;margin:6px 0}.lg i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:4px;vertical-align:-1px}
table.cnt{border-collapse:collapse;font-size:12px;margin-top:10px}table.cnt td,table.cnt th{border-bottom:1px solid var(--line);padding:2px 8px;text-align:right}table.cnt th:first-child,table.cnt td:first-child{text-align:left}
text.lb{font-size:10px;fill:var(--text);pointer-events:none}
</style></head><body><main>
<h1>Knowledge graph of the schema pilot</h1>
<p class="sub">Built by kg.py from the five tables of three papers (the tables stay the source). Click a node for its attributes and neighbours; double-click to expand it; drag the background to pan, wheel to zoom.</p>
<div class="bar"><button id="b0">Start: yim20 sample 8 chain</button><button id="b1">(a) samples that used TMA, with conditions</button><button id="b2">(b) every growth_per_cycle value</button><button id="b3">(c) gre23 120/160 run</button>
<label>Paper <select id="fp"><option value="">all</option></select></label><span id="ft"></span><span id="info" class="sub"></span></div>
<div class="lg" id="lg"></div>
<div class="wrap"><svg id="g"></svg><div id="side"><i>Click a node.</i></div></div>
<div id="counts"></div>
</main><script>
const G=__G__;const Q=__Q__;const CN=__CN__;const CE=__CE__;
const COL={paper:"#5a5a5a",sample:"#2a78d6",group:"#7a5195",condition:"#1baf7a",series:"#eb6834",value:"#eda100",quantity:"#e87ba4",material:"#8c6d31",chemical:"#008300",method:"#4e79a7",structure_class:"#a0a0a0",process_mode:"#b07aa1"};
const N={};G.nodes.forEach(n=>N[n.id]=n);const ADJ={};G.edges.forEach(e=>{(ADJ[e.source]=ADJ[e.source]||[]).push([e.target,e]);(ADJ[e.target]=ADJ[e.target]||[]).push([e.source,e]);});
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let vis=new Set(),pos={},hidden=new Set(),sel=null,view={x:0,y:0,k:1};const svg=document.getElementById("g");
const types=Object.keys(COL);document.getElementById("ft").innerHTML=types.map(t=>`<label><input type="checkbox" data-t="${t}" checked> ${t}</label>`).join(" ");
document.getElementById("lg").innerHTML=types.map(t=>`<span><i style="background:${COL[t]}"></i>${t}</span>`).join("");
[...new Set(G.nodes.map(n=>n.paper).filter(Boolean))].forEach(p=>document.getElementById("fp").innerHTML+=`<option>${p}</option>`);
function shown(id){const n=N[id];if(!n||hidden.has(n.type))return false;const fp=document.getElementById("fp").value;return !fp||!n.paper||n.paper===fp;}
function setView(ids,msg){vis=new Set(ids.filter(i=>N[i]));pos={};layout();draw();document.getElementById("info").textContent=msg+": "+vis.size+" nodes";}
function layout(){const ids=[...vis].filter(shown);const W=1000,H=640;ids.forEach((id,i)=>{if(!pos[id])pos[id]={x:W/2+300*Math.cos(i*2.4)*Math.sqrt(i/ids.length),y:H/2+250*Math.sin(i*2.4)*Math.sqrt(i/ids.length)}});
 const E=G.edges.filter(e=>vis.has(e.source)&&vis.has(e.target)&&shown(e.source)&&shown(e.target));
 for(let it=0;it<250;it++){const f={};ids.forEach(i=>f[i]={x:0,y:0});
  for(let a=0;a<ids.length;a++)for(let b=a+1;b<ids.length;b++){const p=pos[ids[a]],q=pos[ids[b]];let dx=p.x-q.x,dy=p.y-q.y,d2=dx*dx+dy*dy+0.01;const r=1800/d2;f[ids[a]].x+=dx*r;f[ids[a]].y+=dy*r;f[ids[b]].x-=dx*r;f[ids[b]].y-=dy*r;}
  E.forEach(e=>{const p=pos[e.source],q=pos[e.target];const dx=q.x-p.x,dy=q.y-p.y,d=Math.sqrt(dx*dx+dy*dy)+0.01,k=(d-70)*0.02;f[e.source].x+=dx/d*k*d/10;f[e.source].y+=dy/d*k*d/10;f[e.target].x-=dx/d*k*d/10;f[e.target].y-=dy/d*k*d/10;});
  ids.forEach(i=>{f[i].x+=(W/2-pos[i].x)*0.005;f[i].y+=(H/2-pos[i].y)*0.005;const m=Math.min(1,10/(Math.hypot(f[i].x,f[i].y)+0.01));pos[i].x+=f[i].x*m;pos[i].y+=f[i].y*m;});}}
function draw(){const ids=[...vis].filter(shown);const E=G.edges.filter(e=>vis.has(e.source)&&vis.has(e.target)&&shown(e.source)&&shown(e.target));
 let s=`<g transform="translate(${view.x} ${view.y}) scale(${view.k})">`;E.forEach(e=>{const p=pos[e.source],q=pos[e.target];s+=`<line x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}" stroke="currentColor" opacity=".25"><title>${esc(e.type)}</title></line>`});
 ids.forEach(id=>{const n=N[id],p=pos[id];s+=`<g data-id="${esc(id)}" style="cursor:pointer"><circle cx="${p.x}" cy="${p.y}" r="${id===sel?9:6}" fill="${COL[n.type]||'#999'}" stroke="${id===sel?'currentColor':'none'}" stroke-width="2"><title>${esc(n.type)}: ${esc(n.label||id)}</title></circle><text class="lb" x="${p.x+8}" y="${p.y+3}">${esc((n.label||id).slice(0,28))}</text></g>`});
 svg.innerHTML=s+"</g>";svg.style.color=getComputedStyle(document.body).color;}
function side(id){const n=N[id];sel=id;const nb=(ADJ[id]||[]);
 document.getElementById("side").innerHTML=`<b style="color:${COL[n.type]}">${esc(n.type)}</b> <b>${esc(n.label||id)}</b><div style="font:11px monospace;color:var(--text2)">${esc(id)}</div><table>`+Object.entries(n).filter(([k])=>!["id","label"].includes(k)).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")+`</table><h4>Neighbours (${nb.length})</h4>`+nb.slice(0,200).map(([m,e])=>`<div><span class="nb" data-id="${esc(m)}">${esc((N[m]||{}).label||m)}</span> <span style="color:var(--text2)">${esc(e.type)}${e.qualifiers?' {'+esc(e.qualifiers)+'}':''}${e.role?' '+esc(e.role):''}</span></div>`).join("");draw();}
svg.addEventListener("click",e=>{const g=e.target.closest("g[data-id]");if(g)side(g.dataset.id)});
svg.addEventListener("dblclick",e=>{const g=e.target.closest("g[data-id]");if(!g)return;const c=pos[g.dataset.id];(ADJ[g.dataset.id]||[]).forEach(([m])=>{if(!vis.has(m)){vis.add(m);pos[m]={x:c.x+Math.random()*60-30,y:c.y+Math.random()*60-30}}});layout();draw();});
document.getElementById("side").addEventListener("click",e=>{const x=e.target.closest(".nb");if(!x)return;const id=x.dataset.id;if(!vis.has(id)){vis.add(id);const c=pos[sel]||{x:500,y:320};pos[id]={x:c.x+40,y:c.y+40};layout();}side(id);});
let drag=null;svg.addEventListener("pointerdown",e=>{if(!e.target.closest("g[data-id]"))drag={x:e.clientX-view.x,y:e.clientY-view.y}});svg.addEventListener("pointermove",e=>{if(drag){view.x=e.clientX-drag.x;view.y=e.clientY-drag.y;draw()}});addEventListener("pointerup",()=>drag=null);
svg.addEventListener("wheel",e=>{e.preventDefault();view.k*=e.deltaY<0?1.1:0.9;draw()},{passive:false});
document.querySelectorAll("#ft input").forEach(c=>c.onchange=()=>{c.checked?hidden.delete(c.dataset.t):hidden.add(c.dataset.t);layout();draw()});document.getElementById("fp").onchange=()=>{layout();draw()};
document.getElementById("b0").onclick=()=>setView(Q.start,"yim20 sample 8 chain");document.getElementById("b1").onclick=()=>setView(Q.tma,"(a) samples that used TMA with their conditions");
document.getElementById("b2").onclick=()=>setView(Q.gpc,"(b) growth_per_cycle values with their source series");document.getElementById("b3").onclick=()=>setView(Q.run,"(c) gre23 120/160 run, its series and values");
const papers=[...new Set(CN.map(r=>r[1]))];document.getElementById("counts").innerHTML=`<table class="cnt"><tr><th>node type</th>${papers.map(p=>`<th>${p}</th>`).join("")}<th>all</th></tr>`+[...new Set(CN.map(r=>r[0]))].map(t=>`<tr><td>${t}</td>${papers.map(p=>`<td>${(CN.find(r=>r[0]===t&&r[1]===p)||[0,0,""])[2]}</td>`).join("")}<td>${CN.filter(r=>r[0]===t).reduce((a,r)=>a+r[2],0)}</td></tr>`).join("")+
 `<tr><th>nodes</th>${papers.map(p=>`<th>${CN.filter(r=>r[1]===p).reduce((a,r)=>a+r[2],0)}</th>`).join("")}<th>${G.nodes.length}</th></tr><tr><th>edges</th><td colspan="${papers.length}"></td><th>${G.edges.length}</th></tr></table>`+
 `<table class="cnt"><tr><th>edge type</th><th>count</th></tr>${CE.map(([t,c])=>`<tr><td>${t}</td><td>${c}</td></tr>`).join("")}</table><p class="sub">v1 for comparison: 13,323 nodes and 38,055 edges for 47 papers (about ${Math.round(13323/47)} nodes and ${Math.round(38055/47)} edges per paper); this pilot: ${G.nodes.length} nodes and ${G.edges.length} edges for 3 papers (${Math.round(G.nodes.length/3)} and ${Math.round(G.edges.length/3)} per paper, shared nodes counted once).</p>`;
setView(Q.start,"yim20 sample 8 chain");
</script></body></html>"""
kgp = KGPAGE.replace("__G__", json.dumps(G, ensure_ascii=False)).replace("__Q__", json.dumps(Q)).replace("__CN__", json.dumps([[t, p, c] for (t, p), c in sorted(cnt_n.items())])).replace("__CE__", json.dumps(sorted(cnt_e.items())))
(PILOT / "reports" / "kg.html").write_text(kgp, encoding="utf-8")
print("kg.html", f"{len(kgp) / 1e6:.2f} MB", {k: len(v) for k, v in Q.items()})
