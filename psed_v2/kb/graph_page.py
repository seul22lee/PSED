#!/usr/bin/env python3
"""P150/P151: per paper, from facts.csv and experiments.csv of the compiled tree (kb/compiled/) and the gold tree (kb/pilot/), by the
same code: the experiment cards (P151, graph_<pid>.html) and the fact-level force graph (P150, graph_facts_<pid>.html). No model call.

    python3 psed_v2/kb/graph_page.py yli18 yim20 mat22     # kb/reports/graph_<pid>.html, graph_facts_<pid>.html, graph_counts.csv,
                                                           # graph_cards.csv, graph_index.html

P151 cards: one card per experiments.csv row (an entity with results; cited-work rows go to the paper-level list): its label and
kind (specimen, or model run when a simulation is above it); the deposition and simulation above it; its condition vector, every
setting on the entity and on the non-measurement activities above it as "quantity = value unit [qualifiers]", grouped by where it
sits; its results (observation, derived and model rows under it, not under another entity), the same way, a curve as its
points_ref; its data (figures.json ids with role and panel: compiled from the points_ref rows, gold from query's curve binding).
Blocks: a gold comparison (series / replicate / grid; the largest first) is a frame around its member cards titled with its kind
and varied quantity, the remaining cards are grouped in boxes by their deposition or simulation; each gold card has opposite it the
compiled card paired with it (render.pair_units on the pass-0 units compile.py reads; a gold specimen whose deposition pairs with a
pass-0 run that has a "film of <run>" card pairs with that film) or "no counterpart"; compiled cards with no gold card follow,
framed and boxed the same way. A condition or result cell of a paired card is marked when the other card has no value of that
quantity [qualifiers] (only) or another value (differs, compared in canonical units). Claims and caveats are boxes listing an arrow
to each card their links reach; definitions and cited facts one collapsed list; the experiments.csv rows of both trees as tables.
The inline script only toggles gold / compiled, searches, and collapses a block (R2's no-script rule is waived for graph_*.html).

P150 fact graph:
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
    (R / f"graph_facts_{pid}.html").write_text(doc, encoding="utf-8")
    return counts


# ---------------------------------------------------------------------------------------------------------------- P151 cards
import compile as K            # noqa: E402  (kb/extract)
import experiments as EXP      # noqa: E402  (kb/pilot: the value text of a fact)
import render                  # noqa: E402

RESULT_TYPES = ("observation", "derived", "model")
CARD_STYLE = (".blk{border:1px solid #888;margin:10px 0}.blk>h3{margin:0;padding:3px 6px;background:#eee;cursor:pointer;font-size:13px}"
              ".cmp>h3{background:#fde0dd}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:4px}"
              ".box{font-weight:bold;padding:2px 6px;color:#1f78b4}.card{border:1px solid #555;padding:4px;background:#fff}"
              ".card h4{margin:0 0 2px 0;font-size:13px}.none{border:1px dashed #c00;color:#c00;padding:4px}.lone{border-color:#c00;border-width:2px}"
              ".grp{color:#555;margin-top:2px}.card ul{margin:0;padding-left:16px}.diff{background:#f6c0c0}.only{background:#f8dfa0}"
              ".chip{display:inline-block;border:1px solid #999;padding:0 3px;margin:1px;font-size:11px}.tag{color:#6a3d9a;font-size:11px}"
              "body.gold-only .cside{display:none}body.comp-only .gside{display:none}.hide{display:none}.side-h{font-weight:bold}")
CARD_SCRIPT = r"""
function mode(m){document.body.className=m;}
document.querySelectorAll('.blk>h3').forEach(h=>h.addEventListener('click',()=>h.parentElement.querySelectorAll(':scope>.body').forEach(b=>b.classList.toggle('hide'))));
document.getElementById('q').addEventListener('input',e=>{const s=e.target.value.toLowerCase();
  document.querySelectorAll('.row').forEach(r=>r.classList.toggle('hide',!!s&&!r.textContent.toLowerCase().includes(s)));});
"""


def fact_key(f):
    q = f"other:{f['label_as_printed']}" if f["quantity"] == "other" else f["quantity"] or f"(no quantity: {f['label_as_printed'] or f['statement'][:40]})"
    return q + (f" [{f['qualifiers']}]" if f["qualifiers"] else "")


def fact_text(f):
    return EXP.text(f) or (f"curve {f['points_ref']}" if f["points_ref"] else "(no value)")


def fact_canon(f):
    if f["value"]:
        return str(K.canon(f))
    return (EXP.text(f) or f["points_ref"]).lower()


class Tree:
    """One facts.csv tree with its experiment cards."""
    def __init__(self, pid, key, d, data_of):
        self.rows = rows_of(d / f"{pid}.facts.csv")
        self.R = {r["fact_id"]: r for r in self.rows}
        self.kids = collections.defaultdict(list)
        for r in self.rows:
            self.kids[r["parent"]].append(r)
        self.exp = rows_of(d / f"{pid}.experiments.csv")
        self.cards = [e["run"] for e in self.exp if e["kind"] != "cited" and e["run"] in self.R]
        self.data_of = data_of(self)

    def up(self, i):
        out, x = [], self.R.get(i, {}).get("parent", "")
        while x in self.R and x not in out:
            out.append(x); x = self.R[x]["parent"]
        return out

    def act(self, e, kind):
        return next((a for a in self.up(e) if self.R[a]["type"] == "activity" and self.R[a]["kind"] == kind), "")

    def kind(self, e):
        return "model run" if self.act(e, "simulation") else "specimen"

    def box(self, e):
        return self.act(e, "deposition") or self.act(e, "simulation") or ""

    def conditions(self, e):
        """[(where, [fact])]: the settings on the entity and on the non-measurement activities and entities above it."""
        out = []
        for h in [e] + self.up(e):
            r = self.R[h]
            if r["type"] == "paper" or (r["type"] == "activity" and r["kind"] == "measurement"):
                continue
            fs = [f for f in self.kids[h] if "#" in f["fact_id"] and f["type"] == "setting"]
            if fs:
                where = "entity's own" if h == e else (f"{r['kind']}: {r['label_as_printed'] or h}" if r["type"] == "activity" else f"{r['type']}: {r['label_as_printed'] or h}")
                out.append((where, fs))
        return out

    def results(self, e):
        out, stack = [], [e]
        while stack:
            for c in self.kids[stack.pop()]:
                if c["type"] == "entity":
                    continue
                if "#" in c["fact_id"] and c["type"] in RESULT_TYPES:
                    out.append(c)
                stack.append(c["fact_id"])
        return out

    def vec(self, e):
        cond, res = collections.defaultdict(set), collections.defaultdict(set)
        for _, fs in self.conditions(e):
            for f in fs:
                cond[fact_key(f)].add(fact_canon(f))
        for f in self.results(e):
            res[fact_key(f)].add(fact_canon(f))
        return cond, res

    def comparisons(self):
        out = []
        for r in self.rows:
            if r["type"] == "comparison":
                m = [x for x in split(r["links"]) if x in self.cards]
                if m:
                    out.append((r, m))
        return sorted(out, key=lambda x: -len(x[1]))

    def claims(self):
        """[(fact, [card])]: claims and caveats, each with the cards its links reach (a linked fact's entity, or the card itself)."""
        out = []
        for f in self.rows:
            if "#" in f["fact_id"] and f["type"] in ("claim", "caveat"):
                hit = []
                for x in split(f["links"]):
                    c = x if x in self.cards else next((a for a in self.up(x) if a in self.cards), "")
                    if c and c not in hit:
                        hit.append(c)
                out.append((f, hit))
        return out


def card_html(T, side, e, other=None, other_T=None, tags=()):
    """One card; with other (the paired card of the other tree) its differing cells are marked."""
    oc, orr = other_T.vec(other) if other else ({}, {})
    mc, mr = T.vec(e)
    r = T.R[e]

    def cell(f, mine, theirs):
        k = fact_key(f)
        cls = "" if not other else "only" if k not in theirs else "diff" if mine[k] != theirs[k] else ""
        tip = f" title='other side: {html.escape('; '.join(sorted(theirs[k])))}'" if cls == "diff" else ""
        return f"<li class='{cls}'{tip}>{html.escape(k)} = {html.escape(fact_text(f))}</li>"
    acts = " · ".join(f"{k}: {html.escape(T.R[a]['label_as_printed'] or a)}" for k in ("deposition", "simulation") for a in [T.act(e, k)] if a)
    h = [f"<div class='card{'' if other else ' lone'}' id='{side}:{html.escape(e)}'><h4>{html.escape(r['label_as_printed'] or e)} "
         f"<span class='tag'>({T.kind(e)}{'' if other else '; no counterpart'})</span></h4><div class='tag'>{html.escape(e)}</div>",
         f"<div>{acts or 'no deposition or simulation above'}</div><div class='grp'>conditions</div>"]
    for where, fs in T.conditions(e):
        h.append(f"<div class='grp'>{html.escape(where)}</div><ul>" + "".join(cell(f, mc, oc) for f in fs) + "</ul>")
    rs = T.results(e)
    h.append(f"<div class='grp'>results ({len(rs)})</div><ul>" + "".join(cell(f, mr, orr) for f in rs) + "</ul>")
    data = T.data_of.get(e, [])
    if data:
        h.append("<div class='grp'>data</div>" + "".join(f"<span class='chip'>{html.escape(i)} {role} ({html.escape(pn)})</span>" for i, role, pn in data))
    if tags:
        h.append("<div class='tag'>" + " · ".join(html.escape(t) for t in tags) + "</div>")
    return "".join(h) + "</div>"


def card_diffs(G, Cm, g, c):
    gc, gr = G.vec(g)
    cc, cr = Cm.vec(c)
    return (sum(1 for k in set(gc) | set(cc) if gc.get(k) != cc.get(k)), sum(1 for k in set(gr) | set(cr) if gr.get(k) != cr.get(k)))


def cards_page(pid, key):
    Fj = json.loads((V2 / "kb" / f"{pid}.figures.json").read_text(encoding="utf-8")) if (V2 / "kb" / f"{pid}.figures.json").exists() else {}
    fig = {x["id"]: x for sec in ("curves", "values") for x in Fj.get(sec) or []}
    panel = lambda i: f"fig{fig[i]['figure']}{fig[i].get('panel', '')}" if i in fig else "?"   # noqa: E731

    def comp_data(T):
        out = collections.defaultdict(list)
        for e in T.cards:
            for f in T.results(e):
                if f["points_ref"]:
                    role = "measured" if f["type"] == "observation" else "fitted" if f["data_kind"] == "computed_by_authors" else "simulated"
                    out[e].append((f["points_ref"], role, panel(f["points_ref"])))
        return out

    def gold_data_(T):
        out = collections.defaultdict(list)
        for cid, e in render.gold_curve_units(key).items():
            out[e].append((cid, fig.get(cid, {}).get("kind", "?"), panel(cid)))
        return out
    G = Tree(pid, key, V2 / "kb" / "pilot", gold_data_)
    Cm = Tree(pid, key, K.OUT, comp_data)
    run = K.Run(pid)
    run.read()
    run.tree()
    pu = render.pair_units(pid, key, [it for it in run.pass0 if isinstance(it, dict)])
    pair, used = {}, set()
    for want in ("matched", None):
        for g in G.cards:
            if g in pair or (want and pu["status_g"].get(g) != want):
                continue
            c = next((run.node[y][0] for y in pu["pair_of"].get(g, []) if y in run.node and run.node[y][0] in Cm.cards and run.node[y][0] not in used), None)
            if c is None:                                                       # a film of the run the gold deposition pairs with
                d = G.act(g, "deposition")
                c = next((run.node[y][0] + ":film" for y in pu["pair_of"].get(d, []) if y in run.node and run.node[y][0] + ":film" in Cm.cards
                          and run.node[y][0] + ":film" not in used), None)
            if c:
                pair[g] = c; used.add(c)
    inv = {c: g for g, c in pair.items()}
    ctags = collections.defaultdict(list)
    for T, tags in ((G, collections.defaultdict(list)), (Cm, ctags)):
        for r, m in T.comparisons():
            for e in m:
                tags[e].append(f"in {r['kind']} varying {r['quantity'] or '-'}" + (f" ({r['label_as_printed']})" if r["label_as_printed"] else ""))
        T.tags = tags
    blocks, placed = [], set()

    def block(title, cls, gold_cards, comp_cards, T_box):
        rows_ = []
        last = None
        for g in gold_cards:
            b = G.box(g)
            if b != last:
                rows_.append(f"<div class='box'>{html.escape(G.R[b]['kind'] + ': ' + (G.R[b]['label_as_printed'] or b)) if b else 'no deposition or simulation'}</div>")
                last = b
            c = pair.get(g)
            rows_.append("<div class='row'><div class='gside'>" + card_html(G, "g", g, c, Cm, G.tags[g]) + "</div><div class='cside'>"
                         + (card_html(Cm, "c", c, g, G, Cm.tags[c]) if c else "<div class='none'>no counterpart</div>") + "</div></div>")
        last = None
        for c in comp_cards:
            b = Cm.box(c)
            if b != last:
                rows_.append(f"<div class='box'>{html.escape(Cm.R[b]['kind'] + ': ' + (Cm.R[b]['label_as_printed'] or b)) if b else 'no deposition or simulation'}</div>")
                last = b
            rows_.append("<div class='row'><div class='gside'><div class='none'>no counterpart</div></div><div class='cside'>" + card_html(Cm, "c", c, None, None, Cm.tags[c]) + "</div></div>")
        blocks.append(f"<div class='blk {cls}'><h3>{html.escape(title)}</h3><div class='body'>{''.join(rows_)}</div></div>")
    for r, m in G.comparisons():
        m = [g for g in m if g not in placed]
        if m:
            m.sort(key=lambda g: (G.box(g), g))
            block(f"gold {r['kind']} · varied {r['quantity'] or '-'}" + (f" · {r['label_as_printed']}" if r["label_as_printed"] else "") + f" · {len(m)} cards", "cmp", m, [], G)
            placed |= set(m)
    rest = collections.defaultdict(list)
    for g in G.cards:
        if g not in placed:
            rest[G.box(g)].append(g)
    for b, gs in rest.items():
        block((f"gold {G.R[b]['kind']}: {G.R[b]['label_as_printed'] or b}" if b else "gold: no deposition or simulation") + f" · {len(gs)} cards", "", gs, [], G)
    lone, cplaced = [c for c in Cm.cards if c not in inv], set()
    for r, m in Cm.comparisons():
        m = [c for c in m if c in lone and c not in cplaced]
        if m:
            m.sort(key=lambda c: (Cm.box(c), c))
            block(f"compiled only: {r['kind']} · varied {r['quantity'] or '-'} · {len(m)} cards", "cmp", [], m, Cm)
            cplaced |= set(m)
    crest = collections.defaultdict(list)
    for c in lone:
        if c not in cplaced:
            crest[Cm.box(c)].append(c)
    for b, cs in crest.items():
        block((f"compiled only: {Cm.R[b]['kind']}: {Cm.R[b]['label_as_printed'] or b}" if b else "compiled only: no deposition or simulation") + f" · {len(cs)} cards", "", [], cs, Cm)

    def claims(T, side):
        out = []
        for f, hit in T.claims():
            arrows = " ".join(f"→ <a href='#{side}:{html.escape(c)}'>{html.escape(T.R[c]['label_as_printed'] or c)}</a>" for c in hit) or "(no card reached)"
            head = f"{f['type']} {f['stance']}".strip() + (f": {f['cause']} {f['relation']} {f['effect']}" if f["cause"] else "")
            out.append(f"<div class='card'><b>{html.escape(head)}</b> <span class='tag'>{html.escape(f['fact_id'])}</span><div>{html.escape(f['statement'][:300])}</div><div>{arrows}</div></div>")
        return "".join(out)

    def paper_list(T):
        fs = [f for f in T.rows if "#" in f["fact_id"] and f["type"] in ("definition", "cited")]
        return (f"<details><summary>{len(fs)} definitions and cited facts</summary><ul>" + "".join(
            f"<li>{f['type']}: {html.escape(fact_key(f) if f['quantity'] else f['term'] or '-')} {html.escape(fact_text(f) or f['term'])} "
            f"<span class='tag'>{html.escape(f['fact_id'])}</span></li>" for f in fs) + "</ul></details>")
    pairs = [(g, c) for g, c in pair.items()]
    dc = sum(card_diffs(G, Cm, g, c)[0] for g, c in pairs)
    dr = sum(card_diffs(G, Cm, g, c)[1] for g, c in pairs)
    stats = dict(paper=key, cards_gold=len(G.cards), cards_compiled=len(Cm.cards), paired=len(pairs), gold_without_counterpart=len(G.cards) - len(pairs),
                 compiled_without_counterpart=len(Cm.cards) - len(pairs), differing_condition_cells=dc, differing_result_cells=dr)
    tbl = lambda T, d: REP.section(f"experiments.csv ({d})", (V2 / "kb" / "pilot" if T is G else K.OUT) / f"{pid}.experiments.csv")   # noqa: E731
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>cards {key}</title><style>{REP.STYLE}{CARD_STYLE}</style></head><body>"
           f"<h1>Experiment cards: {key} ({pid})</h1><p>Left gold (kb/pilot), right compiled (kb/compiled). {stats['cards_gold']} gold cards, "
           f"{stats['cards_compiled']} compiled, {stats['paired']} paired (render.pair_units); differing cells: conditions {dc}, results {dr} "
           f"(<span class='diff'>differs</span>, <span class='only'>only on this side</span>; hover a red cell for the other side's value). "
           f"Click a block title to collapse it. <a href='graph_facts_{pid}.html'>fact graph</a></p>"
           f"<p><button onclick=\"mode('')\">both</button> <button onclick=\"mode('gold-only')\">gold</button> <button onclick=\"mode('comp-only')\">compiled</button> "
           f"<label>search <input id='q' placeholder='label, id, quantity'></label></p>"
           f"<div class='row'><div class='gside side-h'>gold</div><div class='cside side-h'>compiled</div></div>{''.join(blocks)}"
           f"<h2>Claims and caveats</h2><div class='row'><div class='gside'>{claims(G, 'g')}</div><div class='cside'>{claims(Cm, 'c')}</div></div>"
           f"<h2>Paper-level facts</h2><div class='row'><div class='gside'>{paper_list(G)}</div><div class='cside'>{paper_list(Cm)}</div></div>"
           f"<div class='row'><div class='gside'>{tbl(G, 'gold')}</div><div class='cside'>{tbl(Cm, 'compiled')}</div></div>"
           f"<script>{CARD_SCRIPT}</script></body></html>\n")
    (R / f"graph_{pid}.html").write_text(doc, encoding="utf-8")
    return stats


def main(argv):
    counts, links, cards = [], [], []
    for arg in argv:
        pid, key = C.resolve(arg)
        counts += page(pid, key)
        cards.append(cards_page(pid, key))
        links.append(f"<li><a href='graph_{pid}.html'>graph_{pid}.html</a> (experiment cards) · <a href='graph_facts_{pid}.html'>graph_facts_{pid}.html</a> "
                     f"(fact graph) · {key}</li>")
    with (R / "graph_cards.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cards[0])); w.writeheader(); w.writerows(cards)
    with (R / "graph_counts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "element", "kind", "gold", "compiled"]); w.writeheader()
        by = collections.defaultdict(dict)
        for c in counts:
            by[(c["paper"], c["element"], c["kind"])][c["source"]] = c["count"]
        for (p, e, k), v in by.items():
            w.writerow(dict(paper=p, element=e, kind=k, gold=v.get("gold", 0), compiled=v.get("compiled", 0)))
    body = ("<ul>" + "".join(links) + "</ul>" + REP.section("Experiment cards per paper: gold, compiled, paired; differing cells", R / "graph_cards.csv")
            + REP.section("Fact graph: node and edge counts by kind, gold vs compiled (edge = node pairs; edge (rows) = rows)", R / "graph_counts.csv"))
    (R / "graph_index.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>graph index</title><style>{REP.STYLE}</style></head>"
                                        f"<body><h1>Knowledge graph pages</h1>\n{body}\n</body></html>\n", encoding="utf-8")
    print(f"{len(links)} papers: graph_<pid>.html (cards), graph_facts_<pid>.html; kb/reports/graph_cards.csv, graph_counts.csv, graph_index.html")
    for c in cards:
        print(c)


if __name__ == "__main__":
    main(sys.argv[1:])
