#!/usr/bin/env python3
"""P150: one knowledge-graph page per paper, from facts.csv: the compiled tree (kb/compiled/<pid>.facts.csv) and the gold tree
(kb/pilot/<pid>.facts.csv) by the same code, one shown at a time. No model call.

    python3 psed_v2/kb/graph_page.py yli18 yim20 mat22     # kb/reports/graph_<pid>.html, graph_counts.csv, graph_index.html

Nodes: the tree rows (paper; activities by kind: recipe, deposition, measurement, simulation, other; entities: specimen, or model
run when a simulation is above it; comparisons; identity), the fact rows grouped by (parent, type) into one node each, and the
ontology ids the facts name (quantity, species, mechanism). A tree node's size is the number of fact rows below it.
Edges (from the P150 directive, counted between nodes): belongs_to (a row's parent), evidence (fact -> element; listed and shown
as the node's tooltip, never drawn), inputs (derived -> its input facts), links (claim or caveat -> facts; comparison -> its
purpose fact and members), cause / effect (claim -> quantity or mechanism id), qualified_by (fact -> the ontology id it names: its
quantity, the quantity of an x= qualifier, the species of a species= / gas= qualifier or of a species-valued value_text).
The page: a force layout drawn by the inline script below (tree edges stiff, the others loose), a side panel with the clicked
node's row (or its rows), toggles for the ontology layer and gold / compiled, a search by id or label; under it the node and edge
tables of both trees, so the picture can be checked against the rows. R2's no-script rule is waived for graph_*.html (user, P150).
"""
import collections
import csv
import html
import json
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "kb" / "extract"))
import common as C   # noqa: E402
import lists as L    # noqa: E402  (kb/pilot, on the path through common)
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("kb_report", V2 / "kb" / "report.py")   # kb/report.py (kb/pilot/report.py shadows the name)
REP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(REP)

R = V2 / "kb" / "reports"
SPECIES_VALUED = {"material", "substrate", "reactant_A", "reactant_B", "carrier_gas", "structure"}
COLOUR = {"paper": "#222222", "recipe": "#6a3d9a", "deposition": "#1f78b4", "measurement": "#a6cee3", "simulation": "#ff7f00",
          "activity": "#cab2d6", "specimen": "#33a02c", "model run": "#fdbf6f", "comparison": "#e31a1c", "identity": "#b15928",
          "setting": "#8dd3c7", "observation": "#80b1d3", "derived": "#bebada", "model": "#fb8072", "definition": "#fccde5",
          "claim": "#b3de69", "caveat": "#ffed6f", "cited": "#d9d9d9", "quantity": "#bc80bd", "species": "#ccebc5", "mechanism": "#ffffb3"}
TREE_EDGES = {"belongs_to", "inputs"}


def rows_of(path):
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []


def split(v):
    return [x for x in (v or "").split(";") if x]


def graph(rows):
    """(nodes {id: node}, edges Counter{(from, to, kind): count}) of one tree; see the module docstring."""
    Rw = {r["fact_id"]: r for r in rows}
    tree = [r for r in rows if "#" not in r["fact_id"]]
    facts = [r for r in rows if "#" in r["fact_id"]]

    def above(i):
        out, x = [], Rw.get(i, {}).get("parent", "")
        while x in Rw and x not in out:
            out.append(x); x = Rw[x]["parent"]
        return out

    def kind(r):
        if r["type"] == "activity":
            return r["kind"] if r["kind"] in ("recipe", "deposition", "measurement", "simulation") else "activity"
        if r["type"] == "entity":
            return "model run" if any(Rw[a]["type"] == "activity" and Rw[a]["kind"] == "simulation" for a in above(r["fact_id"])) else "specimen"
        return r["type"]
    nodes, edges, group_of = {}, collections.Counter(), {}
    for r in tree:
        nodes[r["fact_id"]] = dict(id=r["fact_id"], k=kind(r), l=r["label_as_printed"] or r["kind"] or r["type"], layer="tree", n=0,
                                   ev=r["evidence"], f={k: v for k, v in r.items() if v})
    for f in facts:
        g = f"{f['parent']}::{f['type']}"
        group_of[f["fact_id"]] = g
        nd = nodes.setdefault(g, dict(id=g, k=f["type"], l="", layer="fact", n=0, ev="", f=[]))
        nd["n"] += 1
        nd["f"].append({k: v for k, v in f.items() if v})
        for a in [f["parent"]] + above(f["fact_id"]):
            if a in nodes and nodes[a]["layer"] == "tree":
                nodes[a]["n"] += 1
    for g, nd in nodes.items():
        if nd["layer"] == "fact":
            nd["l"] = f"{nd['n']} {nd['k']}"
            nd["ev"] = ";".join(dict.fromkeys(e for x in nd["f"] for e in split(x.get("evidence"))))

    def onto(kind_, i):
        key = {"quantity": "q", "species": "s", "mechanism": "m"}[kind_] + ":" + i
        nodes.setdefault(key, dict(id=key, k=kind_, l=i, layer="onto", n=0, ev="", f={"id": i, "kind": kind_}))["n"] += 1
        return key

    def target(i):
        return group_of.get(i) or (i if i in nodes else None)
    for r in tree:
        if r["parent"] in nodes:
            edges[(r["fact_id"], r["parent"], "belongs_to")] += 1
        for e in split(r["evidence"]):
            edges[(r["fact_id"], e, "evidence")] += 1
        if r["type"] == "comparison":
            for x in split(r["links"]):
                if target(x):
                    edges[(r["fact_id"], target(x), "links")] += 1
    for f in facts:
        g = group_of[f["fact_id"]]
        if f["parent"] in nodes:
            edges[(g, f["parent"], "belongs_to")] += 1
        for e in split(f["evidence"]):
            edges[(g, e, "evidence")] += 1
        for x in split(f["inputs"]):
            if target(x):
                edges[(g, target(x), "inputs")] += 1
        if f["type"] in ("claim", "caveat"):
            for x in split(f["links"]):
                if target(x):
                    edges[(g, target(x), "links")] += 1
        for side in ("cause", "effect"):
            for x in split(f[side]):
                x = x.removeprefix("mechanism:")
                edges[(g, onto("mechanism" if x in L.MECHANISMS or f[side].startswith("mechanism:") else "quantity", x), side)] += 1
        for q in split(f["quantity"]):
            edges[(g, onto("quantity", q), "qualified_by")] += 1
        for part in split(f["qualifiers"]):
            k, _, v = part.partition("=")
            if k == "x" and v:
                edges[(g, onto("quantity", v), "qualified_by")] += 1
            elif k in ("species", "gas") and v:
                edges[(g, onto("species", v), "qualified_by")] += 1
        if f["quantity"] in SPECIES_VALUED and f["value_text"]:
            edges[(g, onto("species", f["value_text"].lower()), "qualified_by")] += 1
    return nodes, edges


SCRIPT = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const cv=document.getElementById('cv'),cx=cv.getContext('2d'),side=document.getElementById('side');
const TREE=new Set(D.tree);
let src='compiled',showOnto=true,G=null,sel=null,view={x:0,y:0,s:1},tick=0,raf=null,auto=true;
const LEN={belongs_to:28,inputs:40,links:140,cause:160,effect:160,qualified_by:150},K={belongs_to:.12,inputs:.06,links:.008,cause:.006,effect:.006,qualified_by:.004};
function rnd(i){const x=Math.sin(i*9301+49297)*233280;return x-Math.floor(x);}
function build(){
  const d=D[src];const idx={};
  const ns=d.nodes.filter(n=>showOnto||n.layer!=='onto').map((n,i)=>{const o=Object.assign({},n,{x:(rnd(i)-.5)*800,y:(rnd(i+7)-.5)*800,vx:0,vy:0});idx[n.id]=o;return o;});
  const es=d.edges.filter(e=>e.k!=='evidence'&&idx[e.s]&&idx[e.t]).map(e=>({a:idx[e.s],b:idx[e.t],k:e.k,c:e.c}));
  G={ns,es,idx};tick=0;sel=null;auto=true;side.innerHTML='Click a node.';
  document.querySelectorAll('.tbl').forEach(t=>t.style.display=t.dataset.src===src?'':'none');
  document.getElementById('srcname').textContent=src;
  if(!raf)raf=requestAnimationFrame(step);
}
function step(){
  const ns=G.ns,n=ns.length;
  for(let it=0;it<3&&tick<450;it++,tick++){
    const cool=Math.max(.05,1-tick/450);
    for(let i=0;i<n;i++){const a=ns[i];for(let j=i+1;j<n;j++){const b=ns[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01;
      if(d2>90000)continue;const f=600/d2;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}}
    for(const e of G.es){const dx=e.b.x-e.a.x,dy=e.b.y-e.a.y,d=Math.sqrt(dx*dx+dy*dy)+.01,f=K[e.k]*(d-LEN[e.k])/d;
      e.a.vx+=dx*f;e.a.vy+=dy*f;e.b.vx-=dx*f;e.b.vy-=dy*f;}
    for(const a of ns){a.vx-=a.x*.002;a.vy-=a.y*.002;a.vx*=.6;a.vy*=.6;a.x+=a.vx*cool;a.y+=a.vy*cool;}
  }
  if(auto)fit();draw();raf=tick<450?requestAnimationFrame(step):null;
}
function fit(){let a=1e9,b=1e9,c=-1e9,d=-1e9;for(const n of G.ns){a=Math.min(a,n.x);b=Math.min(b,n.y);c=Math.max(c,n.x);d=Math.max(d,n.y);}
  view.x=(a+c)/2;view.y=(b+d)/2;view.s=Math.min(cv.width/(c-a+60),cv.height/(d-b+60),3);}
function rad(n){return n.layer==='fact'?3+Math.min(9,Math.sqrt(n.n)*1.5):n.layer==='onto'?3+Math.min(6,Math.sqrt(n.n)):4+Math.min(14,Math.sqrt(n.n)*1.2);}
function scr(n){return[(n.x-view.x)*view.s+cv.width/2,(n.y-view.y)*view.s+cv.height/2];}
function draw(){
  cx.clearRect(0,0,cv.width,cv.height);
  const near=new Set();if(sel){near.add(sel);for(const e of G.es){if(e.a===sel)near.add(e.b);if(e.b===sel)near.add(e.a);}}
  for(const e of G.es){const[p,q]=[scr(e.a),scr(e.b)];cx.strokeStyle=sel&&(e.a===sel||e.b===sel)?'#000':(D.ecol[e.k]||'#bbb');
    cx.globalAlpha=sel&&!(e.a===sel||e.b===sel)?.15:TREE.has(e.k)?.7:.35;cx.setLineDash(TREE.has(e.k)?[]:[3,3]);
    cx.lineWidth=TREE.has(e.k)?1.2:.8;cx.beginPath();cx.moveTo(p[0],p[1]);cx.lineTo(q[0],q[1]);cx.stroke();}
  cx.setLineDash([]);
  for(const n of G.ns){const[p,q]=scr(n),r=rad(n)*Math.sqrt(view.s);cx.globalAlpha=sel&&!near.has(n)?.25:1;
    cx.fillStyle=D.col[n.k]||'#999';cx.beginPath();cx.arc(p,q,r,0,6.3);cx.fill();cx.strokeStyle=n===sel?'#000':'#555';cx.lineWidth=n===sel?2.5:.5;cx.stroke();
    if(n.layer==='tree'&&(r>9||view.s>1.6)||n===sel||near.has(n)&&sel){cx.fillStyle='#000';cx.font='11px monospace';cx.fillText(n.l.slice(0,40),p+r+2,q+3);}}
  cx.globalAlpha=1;
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function table(o){return'<table>'+Object.entries(o).map(([k,v])=>'<tr><th>'+esc(k)+'</th><td>'+esc(v)+'</td></tr>').join('')+'</table>';}
function show(n){sel=n;if(!n){side.innerHTML='Click a node.';draw();return;}
  let h='<b>'+esc(n.id)+'</b><br>'+esc(n.k)+' · '+esc(n.layer)+' · '+n.n+(n.layer==='tree'?' fact rows below':' rows')+'<br>';
  if(n.ev)h+='<div title="'+esc(n.ev)+'">evidence: '+esc(n.ev.split(';').slice(0,12).join(', '))+(n.ev.split(';').length>12?' …':'')+'</div>';
  const ins=G.es.filter(e=>e.b===n),outs=G.es.filter(e=>e.a===n);
  h+='<div>edges out: '+outs.map(e=>esc(e.k)+'→'+esc(e.b.id)+' ×'+e.c).slice(0,30).join('; ')+'</div><div>edges in: '+ins.length+'</div>';
  h+=Array.isArray(n.f)?n.f.map(table).join(''):table(n.f);side.innerHTML=h;draw();}
function pick(ev){const b=cv.getBoundingClientRect(),mx=ev.clientX-b.left,my=ev.clientY-b.top;let best=null,bd=1e9;
  for(const n of G.ns){const[p,q]=scr(n),d=(p-mx)**2+(q-my)**2;if(d<bd&&d<(rad(n)*Math.sqrt(view.s)+4)**2){bd=d;best=n;}}return best;}
let drag=null;
cv.addEventListener('mousedown',e=>{auto=false;drag={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y,moved:false};});
window.addEventListener('mousemove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>3)drag.moved=true;
  view.x=drag.vx-dx/view.s;view.y=drag.vy-dy/view.s;draw();});
window.addEventListener('mouseup',e=>{if(drag&&!drag.moved)show(pick(e));drag=null;});
cv.addEventListener('mousemove',e=>{if(drag)return;const n=pick(e);cv.title=n?n.id+' | '+n.l+(n.ev?' | evidence '+n.ev:''):'';});
cv.addEventListener('wheel',e=>{e.preventDefault();auto=false;view.s*=e.deltaY<0?1.15:1/1.15;view.s=Math.max(.1,Math.min(8,view.s));draw();},{passive:false});
document.getElementById('onto').addEventListener('change',e=>{showOnto=e.target.checked;build();});
document.getElementById('src').addEventListener('change',e=>{src=e.target.checked?'gold':'compiled';build();});
document.getElementById('q').addEventListener('keydown',e=>{if(e.key!=='Enter')return;const s=e.target.value.toLowerCase();
  const n=G.ns.find(n=>n.id.toLowerCase().includes(s)||n.l.toLowerCase().includes(s));if(n){auto=false;view.x=n.x;view.y=n.y;view.s=Math.max(view.s,1.5);show(n);}});
function size(){cv.width=cv.parentElement.clientWidth;cv.height=Math.max(480,window.innerHeight*.7);if(auto)fit();draw();}
window.addEventListener('resize',size);
build();size();
"""

PAGE_STYLE = REP.STYLE + ("#wrap{display:flex;gap:8px}#canvas{flex:1;border:1px solid #999;min-width:0}#side{width:34em;max-height:72vh;overflow:auto;"
                          "border:1px solid #999;padding:6px}#side table{margin:4px 0}label{margin-right:16px}.legend span{display:inline-block;"
                          "padding:0 6px;margin:2px;border:1px solid #777}")
ECOL = {"belongs_to": "#888888", "inputs": "#6a3d9a", "links": "#1f78b4", "cause": "#e31a1c", "effect": "#33a02c", "qualified_by": "#bc80bd"}


def tables(src, nodes, edges):
    nrow = "".join(f"<tr><td>{html.escape(n['id'])}</td><td>{html.escape(n['k'])}</td><td>{html.escape(n['layer'])}</td><td>{html.escape(n['l'])}</td>"
                   f"<td>{n['n']}</td><td>{html.escape(n['ev'])}</td></tr>" for n in nodes.values())
    erow = "".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{k}</td><td>{c}</td></tr>" for (a, b, k), c in sorted(edges.items(), key=lambda x: (x[0][2], x[0][0], x[0][1])))
    return (f"<div class='tbl' data-src='{src}'><h2>{src}: edges ({len(edges)}; evidence edges listed, not drawn)</h2><table><tr><th>from</th><th>to</th>"
            f"<th>edge kind</th><th>count</th></tr>{erow}</table><h2>{src}: nodes ({len(nodes)})</h2><table><tr><th>id</th><th>kind</th><th>layer</th>"
            f"<th>label</th><th>facts</th><th>evidence</th></tr>{nrow}</table></div>")


def page(pid, key):
    out, counts = {}, []
    for src, path in (("compiled", V2 / "kb" / "compiled" / f"{pid}.facts.csv"), ("gold", V2 / "kb" / "pilot" / f"{pid}.facts.csv")):
        nodes, edges = graph(rows_of(path))
        out[src] = (nodes, edges)
        counts += [dict(paper=key, source=src, element="node", kind=k, count=n) for k, n in collections.Counter(x["k"] for x in nodes.values()).items()]
        counts += [dict(paper=key, source=src, element="edge", kind=k, count=n) for k, n in collections.Counter(k for (_, _, k) in edges).items()]
        counts += [dict(paper=key, source=src, element="edge (rows)", kind=k, count=sum(c for (_, _, kk), c in edges.items() if kk == k))
                   for k in sorted({k for (_, _, k) in edges})]
    data = {src: dict(nodes=list(n.values()), edges=[dict(s=a, t=b, k=k, c=c) for (a, b, k), c in e.items()]) for src, (n, e) in out.items()}
    data.update(col=COLOUR, ecol=ECOL, tree=sorted(TREE_EDGES))
    legend = "".join(f"<span style='background:{c}'>{html.escape(k)}</span>" for k, c in COLOUR.items())
    elegend = " ".join(f"<span style='border-color:{c};color:{c}'>{k}{' (stiff)' if k in TREE_EDGES else ' (loose, dashed)'}</span>" for k, c in ECOL.items())
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>graph {key}</title><style>{PAGE_STYLE}</style></head><body>"
           f"<h1>Knowledge graph: {key} ({pid})</h1><p>Showing <b id='srcname'>compiled</b> (kb/compiled/{pid}.facts.csv; gold: kb/pilot/{pid}.facts.csv). "
           f"Drag to pan, wheel to zoom, click a node for its row(s); hover for id, label and evidence.</p>"
           f"<p><label><input type='checkbox' id='onto' checked> ontology ids</label><label><input type='checkbox' id='src'> show gold</label>"
           f"<label>search <input id='q' placeholder='id or label, Enter'></label></p><p class='legend'>{legend}</p><p class='legend'>{elegend}</p>"
           f"<div id='wrap'><div id='canvas'><canvas id='cv'></canvas></div><div id='side'>Click a node.</div></div>"
           + tables("compiled", *out["compiled"]) + tables("gold", *out["gold"]).replace("class='tbl'", "class='tbl' style='display:none'")
           + "<script type='application/json' id='data'>" + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"
           + f"<script>{SCRIPT}</script></body></html>\n")
    (R / f"graph_{pid}.html").write_text(doc, encoding="utf-8")
    return counts


def main(argv):
    counts, links = [], []
    for arg in argv:
        pid, key = C.resolve(arg)
        counts += page(pid, key)
        links.append(f"<li><a href='graph_{pid}.html'>graph_{pid}.html</a> ({key})</li>")
    with (R / "graph_counts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "element", "kind", "gold", "compiled"]); w.writeheader()
        by = collections.defaultdict(dict)
        for c in counts:
            by[(c["paper"], c["element"], c["kind"])][c["source"]] = c["count"]
        for (p, e, k), v in by.items():
            w.writerow(dict(paper=p, element=e, kind=k, gold=v.get("gold", 0), compiled=v.get("compiled", 0)))
    body = "<ul>" + "".join(links) + "</ul>" + REP.section("Node and edge counts by kind, gold vs compiled (edge = node pairs; edge (rows) = rows)", R / "graph_counts.csv")
    (R / "graph_index.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>graph index</title><style>{REP.STYLE}</style></head>"
                                        f"<body><h1>Knowledge graph pages</h1>\n{body}\n</body></html>\n", encoding="utf-8")
    print(f"{len(links)} graph pages; kb/reports/graph_counts.csv, graph_index.html")


if __name__ == "__main__":
    main(sys.argv[1:])
