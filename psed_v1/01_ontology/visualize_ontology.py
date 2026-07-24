"""
visualize_ontology.py
----------------------
Render the compiled ontology (ald_ontology.json) as a single self-contained,
offline HTML file: collapsible class taxonomy + quantity kinds by domain +
relation vocabulary. No external dependencies (works with file:// offline).
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
ONTO = ROOT / "ald_ontology.json"
OUT = ROOT / "ontology.html"

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ALD Ontology __VERSION__</title>
<style>
:root{
  --bg:#fbfbfd; --panel:#fff; --ink:#1a1a2e; --muted:#6b7280; --line:#e5e7eb;
  --accent:#4b2e83;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#15151d; --panel:#1e1e29; --ink:#e8e8ef; --muted:#9aa0aa; --line:#2c2c3a; --accent:#b79cff;}}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--ink)}
header{padding:22px 28px;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:20px;letter-spacing:-.01em}
.sub{color:var(--muted);margin-top:4px;font-size:13px}
.counts{display:flex;gap:18px;margin-top:12px;flex-wrap:wrap}
.counts b{font-size:19px;color:var(--accent)} .counts span{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.wrap{display:grid;grid-template-columns:1.3fr 1fr;gap:0}
@media(max-width:900px){.wrap{grid-template-columns:1fr}}
section{padding:20px 28px;border-right:1px solid var(--line);min-width:0}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 14px}
/* tree */
ul.tree{list-style:none;margin:0;padding:0} ul.tree ul{list-style:none;margin:0;padding:0 0 0 18px;
  border-left:1px dashed var(--line)}
.node{display:inline-flex;align-items:center;gap:7px;padding:3px 9px;margin:2px 0;border-radius:7px;
  cursor:default;font-weight:500}
.node.has-children{cursor:pointer}
.node .tw{width:11px;display:inline-block;color:var(--muted);font-size:10px}
.node .lbl{white-space:nowrap}
.node .def{color:var(--muted);font-weight:400;font-size:12px}
.badge{font-size:10px;padding:1px 6px;border-radius:20px;background:var(--line);color:var(--muted)}
.collapsed>ul{display:none}
/* quantity groups */
.qgroup{margin-bottom:16px}
.qgroup h3{font-size:12px;margin:0 0 7px;display:flex;align-items:center;gap:8px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--line);border-radius:7px;padding:4px 8px;font-size:12px;background:var(--panel)}
.chip .sym{color:var(--accent);font-style:italic;margin-left:4px}
.chip .u{color:var(--muted);font-size:11px;margin-left:5px}
.chip .q{font-size:9px;background:#10b98122;color:#0f9d6f;border-radius:4px;padding:0 4px;margin-left:5px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
td,th{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase}
code{background:var(--line);padding:1px 5px;border-radius:4px;font-size:11.5px}
.rel-verb{color:var(--accent);font-weight:600}
</style></head><body>
<header>
  <h1>ALD Ontology <span class="badge">v__VERSION__</span></h1>
  <div class="sub">__SCOPE__</div>
  <div class="counts">
    <div><b>__NC__</b><span>classes</span></div>
    <div><b>__NR__</b><span>relation types</span></div>
    <div><b>__NE__</b><span>quantity edges</span></div>
    <div><b>__NQ__</b><span>quantity kinds</span></div>
    <div><b>__NQE__</b><span>QUDT-enriched</span></div>
    <div><b>__NI__</b><span>individuals</span></div>
  </div>
</header>
<div class="wrap">
  <section style="border-right:1px solid var(--line)">
    <h2>Class taxonomy &nbsp;·&nbsp; click to collapse</h2>
    <ul class="tree" id="tree"></ul>
  </section>
  <div>
    <section style="border-right:none;border-bottom:1px solid var(--line)">
      <h2>Quantity kinds by domain</h2>
      <div id="quant"></div>
    </section>
    <section style="border-right:none">
      <h2>Relations (typed edges)</h2>
      <table id="rels"><thead><tr><th>domain</th><th>relation</th><th>range</th></tr></thead><tbody></tbody></table>
      <h2 style="margin-top:20px">Quantity relationships <span class="badge" id="edgeN"></span>
        &nbsp;·&nbsp;<select id="edgeFilter" style="font:inherit"></select></h2>
      <div id="edgeWarn" class="def" style="color:#c2410c"></div>
      <table id="edges"><thead><tr><th>source</th><th>relationship</th><th>target</th></tr></thead><tbody></tbody></table>
      <h2 style="margin-top:20px">Seed individuals</h2>
      <div id="inds" class="chips"></div>
    </section>
  </div>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ["#4b2e83","#0f9d6f","#c2410c","#1d4ed8","#9d174d","#b45309","#0e7490","#6d28d9","#65a30d"];
// top-level branch (child of Entity) -> color
const byId = Object.fromEntries(DATA.classes.map(c=>[c.id,c]));
function topBranch(id){let c=byId[id];while(c&&c.parent&&c.parent!=="Entity")c=byId[c.parent];return c?c.id:id;}
const branches=[...new Set(DATA.classes.filter(c=>c.parent==="Entity").map(c=>c.id))];
const color=id=>PALETTE[branches.indexOf(topBranch(id))%PALETTE.length]||"#888";
// build children map
const kids={};DATA.classes.forEach(c=>{(kids[c.parent]=kids[c.parent]||[]).push(c);});
function render(node,parent){
  const li=document.createElement("li");
  const children=kids[node.id]||[];
  const div=document.createElement("div");
  div.className="node"+(children.length?" has-children":"");
  div.style.color=color(node.id);
  div.innerHTML=(children.length?'<span class="tw">▶</span>':'<span class="tw"></span>')+
    '<span class="lbl">'+node.id+'</span>'+
    (children.length?'<span class="badge">'+countDesc(node.id)+'</span>':'')+
    (node.definition?'<span class="def">— '+node.definition+'</span>':'');
  li.appendChild(div);
  if(children.length){
    const ul=document.createElement("ul");
    children.forEach(ch=>render(ch,ul));
    li.appendChild(ul);
    div.querySelector(".tw").textContent="▼";
    div.onclick=e=>{e.stopPropagation();li.classList.toggle("collapsed");
      div.querySelector(".tw").textContent=li.classList.contains("collapsed")?"▶":"▼";};
  }
  parent.appendChild(li);
}
function countDesc(id){let n=0;(kids[id]||[]).forEach(c=>n+=1+countDesc(c.id));return n;}
const root=DATA.classes.find(c=>c.parent===null);
render(root,document.getElementById("tree"));
// quantities by domain
const doms={};DATA.quantity_kinds.forEach(q=>{(doms[q.domain||"other"]=doms[q.domain||"other"]||[]).push(q);});
const qc=document.getElementById("quant");let di=0;
for(const[dom,qs]of Object.entries(doms)){
  const col=PALETTE[di++%PALETTE.length];
  const g=document.createElement("div");g.className="qgroup";
  g.innerHTML='<h3><span class="dot" style="background:'+col+'"></span>'+dom+' <span class="badge">'+qs.length+'</span></h3>';
  const chips=document.createElement("div");chips.className="chips";
  qs.forEach(q=>{const c=document.createElement("div");c.className="chip";
    c.innerHTML=q.id+(q.symbols&&q.symbols.length?'<span class="sym">'+q.symbols[0]+'</span>':'')+
      (q.unit?'<span class="u">'+q.unit.split("/").pop()+'</span>':'')+
      (q.qudt_quantitykind?'<span class="q">QUDT</span>':'');
    chips.appendChild(c);});
  g.appendChild(chips);qc.appendChild(g);
}
// relations
const rb=document.querySelector("#rels tbody");
DATA.relations.forEach(r=>{const tr=document.createElement("tr");
  tr.innerHTML='<td><code>'+(r.domain||"")+'</code></td><td class="rel-verb">'+r.id+
    '</td><td><code>'+(r.range||"")+'</code></td>';rb.appendChild(tr);});
// quantity relationships — directed edges the ontology defines
const EDGES=DATA._edges||[], EWARN=DATA._edge_warnings||[];
const qById=Object.fromEntries(DATA.quantity_kinds.map(q=>[q.id,q]));
const outN={},inN={};
EDGES.forEach(e=>{outN[e.source]=(outN[e.source]||0)+1;inN[e.target]=(inN[e.target]||0)+1;});
document.getElementById("edgeN").textContent=EDGES.length;
if(EWARN.length)document.getElementById("edgeWarn").textContent=
  "⚠ "+EWARN.length+" edge(s) reference an unknown node (shown, not dropped)";
const eb=document.querySelector("#edges tbody");
const ARROW={specializes:"↑ specializes",same_as:"= same as",related:"~ related",
  transforms_to:"→ transforms to",in_family:"∈ in family",defines:"→ defines"};
function drawEdges(kind){
  eb.innerHTML="";
  EDGES.filter(e=>!kind||e.kind===kind).forEach(e=>{
    const tr=document.createElement("tr");tr.dataset.s=e.source;tr.dataset.t=e.target;
    tr.innerHTML='<td><code class="qn" data-q="'+e.source+'">'+e.source+'</code></td>'+
      '<td class="rel-verb">'+(ARROW[e.predicate]||e.predicate)+'</td>'+
      '<td><code class="qn" data-q="'+e.target+'">'+e.target+'</code></td>';
    eb.appendChild(tr);});
  // click a quantity id to highlight every edge it participates in
  eb.querySelectorAll(".qn").forEach(el=>el.onclick=()=>{
    const q=el.dataset.q;
    eb.querySelectorAll("tr").forEach(tr=>
      tr.style.background=(tr.dataset.s===q||tr.dataset.t===q)?"rgba(75,46,131,.12)":"");
  });
}
const ef=document.getElementById("edgeFilter");
[["","all types ("+EDGES.length+")"]].concat(
  [...new Set(EDGES.map(e=>e.kind))].sort().map(k=>[k,k+" ("+EDGES.filter(e=>e.kind===k).length+")"]))
  .forEach(([v,t])=>{const o=document.createElement("option");o.value=v;o.textContent=t;ef.appendChild(o);});
ef.onchange=()=>drawEdges(ef.value);
drawEdges("");
// individuals
const ib=document.getElementById("inds");
for(const[grp,items]of Object.entries(DATA.individuals)){
  items.forEach(it=>{const c=document.createElement("div");c.className="chip";
    c.style.borderColor=color(it.class);
    c.innerHTML=it.id+'<span class="u">'+it.class+'</span>';ib.appendChild(c);});
}
</script></body></html>"""



# --- relationship edges -------------------------------------------------------
# The document viewer already renders the class taxonomy (parent edges as a nested
# tree) and the relation vocabulary (typed predicate table). This builds the
# quantity-to-quantity edges the ontology defines but the viewer never drew:
# specializes, same_as, transforms, in_family, related, defined_by. Every edge comes
# straight from the ontology — none is inferred, aliases are NOT turned into edges,
# and endpoints are validated against real node ids.
def build_relationship_edges(o):
    node_ids = ({c["id"] for c in o.get("classes", [])}
                | {q["id"] for q in o.get("quantity_kinds", [])})
    edges, warnings, seen = [], [], set()

    def add(source, predicate, target, kind, directed=True):
        if not source or not target or source == target:
            return
        key = (source, predicate, target)
        if key in seen:                      # dedup identical edges
            return
        seen.add(key)
        e = {"source": source, "predicate": predicate, "target": target,
             "kind": kind, "directed": directed}
        miss = [end for end, v in (("source", source), ("target", target)) if v not in node_ids]
        if miss:
            warnings.append({**e, "missing": miss})   # reported, never dropped silently
        edges.append(e)

    qr = o.get("quantity_relations", {}) or {}
    # per-quantity specializes / same_as (authoritative on the quantity record)
    for q in o.get("quantity_kinds", []):
        if q.get("specializes"):
            add(q["id"], "specializes", q["specializes"], "specializes")
        if q.get("same_as"):
            add(q["id"], "same_as", q["same_as"], "same_as", directed=False)
    # quantity_relations block
    for child, parent in (qr.get("specializes") or {}).items():
        add(child, "specializes", parent, "specializes")
    for a, b in (qr.get("same_as") or {}).items():
        add(a, "same_as", b, "same_as", directed=False)
    for a, b in (qr.get("related") or {}).items():
        add(a, "related", b, "related", directed=False)
    for t in qr.get("transforms", []) or []:
        add(t.get("from"), "transforms_to", t.get("to"), "transforms")
    for fam, spec in (qr.get("families") or {}).items():
        canon = (spec or {}).get("canonical")
        for m in (spec or {}).get("members", []) or []:
            add(m, "in_family", canon, "in_family")
    for d in qr.get("defined_by", []) or []:
        for inp in d.get("inputs", []) or []:
            add(inp, "defines", d.get("quantity"), "defines")
    return edges, warnings


def main():
    o = json.loads(ONTO.read_text())
    edges, warnings = build_relationship_edges(o)
    o["_edges"] = edges
    o["_edge_warnings"] = warnings
    counts = o["_counts"]
    html = (HTML
            .replace("__DATA__", json.dumps(o))
            .replace("__VERSION__", str(o["meta"]["version"]))
            .replace("__SCOPE__", o["meta"].get("scope", ""))
            .replace("__NC__", str(counts["classes"]))
            .replace("__NR__", str(counts["relations"]))
            .replace("__NE__", str(len(edges)))
            .replace("__NQ__", str(counts["quantity_kinds"]))
            .replace("__NQE__", str(counts["quantity_kinds_enriched"]))
            .replace("__NI__", str(counts["individuals"])))
    OUT.write_text(html)
    print(f"wrote {OUT}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
