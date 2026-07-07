"""
build_kg.py  (Phase E — KG viewer)
----------------------------------
Render the ontology-grounded knowledge graph (output/knowledge_graph_onto.json)
as a standalone, interactive node-link view: kg_viewer.html.

The 2187 QuantityValue nodes are aggregated into experiment->QuantityKind edges
so the backbone stays legible (Papers · Experiments · Materials · QuantityKinds ·
Precursors · Coreactants · Structures · Series). Typed colours, legend, per-type
toggles, click a node to highlight its neighbourhood + inspect it.
Self-contained (CSP-safe, theme-aware). Tracked in the repo.
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent


def main():
    kg = json.loads((ROOT / "output" / "knowledge_graph_onto.json").read_text())
    N = {n["id"]: n for n in kg["nodes"]}

    # QuantityValue -> its QuantityKind (via of_kind)  and  Experiment -> QV (reports)
    qv_kind = {l["source"]: l["target"] for l in kg["links"] if l["etype"] == "of_kind"}
    exp_qk = defaultdict(set)            # aggregate: experiment -> {quantitykind}
    keep_edges = []
    for l in kg["links"]:
        s, t, e = l["source"], l["target"], l["etype"]
        if e == "reports":               # exp -> QV : lift to exp -> QK
            qk = qv_kind.get(t)
            if qk: exp_qk[s].add(qk)
        elif e in ("of_kind",):          # QV -> QK : drop (aggregated)
            continue
        else:
            keep_edges.append({"s": s, "t": t, "e": e})
    for exp, qks in exp_qk.items():
        for qk in qks:
            keep_edges.append({"s": exp, "t": qk, "e": "measures"})

    # keep only non-QuantityValue nodes that are actually referenced
    used = {x for ed in keep_edges for x in (ed["s"], ed["t"])}
    nodes = []
    for nid, n in N.items():
        if n["ntype"] == "QuantityValue" or nid not in used:
            continue
        nodes.append({
            "id": nid, "type": n["ntype"],
            "label": n.get("name") or n.get("series_name") or nid.split("::")[-1],
            "sub": {"relevance": n.get("relevance"), "granularity": n.get("granularity"),
                    "is_model": n.get("is_model")} if n["ntype"] == "Experiment" else {},
        })
    deg = defaultdict(int)
    for ed in keep_edges: deg[ed["s"]] += 1; deg[ed["t"]] += 1
    for n in nodes: n["deg"] = deg[n["id"]]

    data = {"nodes": nodes, "links": keep_edges,
            "counts": {t: sum(1 for n in nodes if n["type"] == t)
                       for t in sorted({n["type"] for n in nodes})}}
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    (ROOT / "kg_viewer.html").write_text(html)
    print(f"wrote kg_viewer.html  ({len(html)//1024} KB)  "
          f"{len(nodes)} nodes, {len(keep_edges)} edges  (from {len(kg['nodes'])} raw, QVs aggregated)")
    print("  ", data["counts"])


TEMPLATE = r"""<title>ALD Knowledge Graph</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--QuantityKind:#eda100;--Precursor:#e34948;--Coreactant:#e87ba4;--Structure:#0f9bd8;--ExperimentSeries:#8b6f2b;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--QuantityKind:#c98500;--Precursor:#e66767;--Coreactant:#d55181;--Structure:#33a9dd;--ExperimentSeries:#b99653;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--QuantityKind:#c98500;--Precursor:#e66767;--Coreactant:#d55181;--Structure:#33a9dd;--ExperimentSeries:#b99653;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--QuantityKind:#eda100;--Precursor:#e34948;--Coreactant:#e87ba4;--Structure:#0f9bd8;--ExperimentSeries:#8b6f2b;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1320px;margin:0 auto;padding:24px 20px 40px}
h1{font-size:23px;margin:0 0 2px;font-weight:600;font-family:"Iowan Old Style",Georgia,serif}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);margin-bottom:14px}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.legend button{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:4px 11px 4px 8px;color:var(--ink2);font-size:12px;cursor:pointer}
.legend button.off{opacity:.34;text-decoration:line-through}
.dot{width:10px;height:10px;border-radius:3px;flex:none}
.stage{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
svg{display:block;width:100%;height:640px;cursor:grab}svg:active{cursor:grabbing}
.info{position:absolute;top:12px;right:12px;width:250px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 13px;font-size:12.5px;display:none}
.info h3{margin:0 0 6px;font-size:13.5px}.info .k{color:var(--ink3);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.info .row{margin:5px 0}.info .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.chip{font-size:11px;padding:1px 7px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.hint{font-size:12px;color:var(--ink3);margin-top:8px}
node,.n{cursor:pointer}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · ontology-grounded KG</div>
<h1>Knowledge graph</h1>
<div class="sub" id="sub"></div>
<div class="legend" id="legend"></div>
<div class="stage"><svg id="svg"></svg><div class="info" id="info"></div></div>
<div class="hint">drag the background to pan · scroll to zoom · click a node to highlight its neighbourhood &amp; inspect · toggle types in the legend. QuantityValues are aggregated into experiment→quantity edges.</div>
</div>
<script>
const D=/*DATA*/;
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const NS="http://www.w3.org/2000/svg",el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;};
const TYPES=Object.keys(D.counts);
const off=new Set();
document.getElementById("sub").textContent=`${D.nodes.length} nodes · ${D.links.length} edges · `+TYPES.map(t=>`${D.counts[t]} ${t}`).join(" · ");
document.getElementById("legend").innerHTML=TYPES.map(t=>`<button data-t="${t}" onclick="tog('${t}')"><span class="dot" style="background:var(--${t})"></span>${t} <span style="color:var(--ink3)">${D.counts[t]}</span></button>`).join("");

const W=1280,H=640,idx=Object.fromEntries(D.nodes.map(n=>[n.id,n]));
// seed positions by type ring so layout converges nicely
const ring={Paper:0,Material:90,QuantityKind:150,Structure:210,Precursor:260,Coreactant:300,ExperimentSeries:340,Experiment:420};
D.nodes.forEach((n,i)=>{const r=ring[n.type]??380,a=i*2.399;n.x=W/2+r*Math.cos(a);n.y=H/2+r*Math.sin(a);n.vx=0;n.vy=0;});
function layout(iters){
  for(let it=0;it<iters;it++){
    for(let i=0;i<D.nodes.length;i++)for(let j=i+1;j<D.nodes.length;j++){
      const a=D.nodes[i],b=D.nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1,d=Math.sqrt(d2),f=1400/d2;
      a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
    D.links.forEach(l=>{const a=idx[l.s],b=idx[l.t];if(!a||!b)return;let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-64)*0.02;
      a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;});
    D.nodes.forEach(n=>{n.vx+=(W/2-n.x)*0.003;n.vy+=(H/2-n.y)*0.003;n.x+=(n.vx*=0.82);n.y+=(n.vy*=0.82);});
  }
}
layout(260);
const nbr=Object.fromEntries(D.nodes.map(n=>[n.id,new Set()]));
D.links.forEach(l=>{if(nbr[l.s]&&nbr[l.t]){nbr[l.s].add(l.t);nbr[l.t].add(l.s);}});
let sel=null,view={x:0,y:0,k:1};
const svg=document.getElementById("svg");svg.setAttribute("viewBox",`0 0 ${W} ${H}`);

function vis(n){return !off.has(idx[n]?.type||n.type);}
function paint(){
  while(svg.firstChild)svg.remove(svg.firstChild);
  const g=el("g",{transform:`translate(${view.x} ${view.y}) scale(${view.k})`});
  D.links.forEach(l=>{const a=idx[l.s],b=idx[l.t];if(!a||!b||off.has(a.type)||off.has(b.type))return;
    const on=sel&&(l.s===sel||l.t===sel);const dim=sel&&!on;
    g.appendChild(el("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:CSS("--line"),"stroke-width":on?1.8:.7,opacity:dim?.08:.55}));});
  D.nodes.forEach(n=>{if(off.has(n.type))return;
    const r=n.type==="Experiment"?4.5:Math.min(7+n.deg*0.5,20);
    const on=!sel||n.id===sel||nbr[sel].has(n.id);
    const c=el("circle",{cx:n.x,cy:n.y,r,fill:CSS("--"+n.type),opacity:on?1:.16,stroke:CSS("--surface"),"stroke-width":1.2,class:"n"});
    c.onclick=ev=>{ev.stopPropagation();sel=sel===n.id?null:n.id;showInfo(n);paint();};
    g.appendChild(c);
    if((n.type!=="Experiment"&&n.deg>=2)||n.type==="Paper"){
      const t=el("text",{x:n.x+r+3,y:n.y+3.5,fill:CSS("--ink2"),"font-size":Math.min(12,9+n.deg*0.15),opacity:on?1:.16});
      t.textContent=n.label.length>22?n.label.slice(0,21)+"…":n.label;g.appendChild(t);}
  });
  svg.appendChild(g);
}
function showInfo(n){
  const box=document.getElementById("info");box.style.display="block";
  const links=D.links.filter(l=>l.s===n.id||l.t===n.id);
  const byType={};links.forEach(l=>{const o=idx[l.s===n.id?l.t:l.s];if(o){(byType[o.type]=byType[o.type]||new Set()).add(o.label);}});
  box.innerHTML=`<h3 style="color:var(--${n.type})">${n.label}</h3>
    <div class="k">${n.type}</div>
    ${Object.entries(n.sub||{}).filter(([,v])=>v!=null).map(([k,v])=>`<div class="row"><span class="k">${k}</span> ${v}</div>`).join("")}
    <div class="row"><span class="k">connections (${links.length})</span></div>
    ${Object.entries(byType).map(([t,s])=>`<div class="row"><span style="color:var(--${t})">${t}</span><div class="chips">${[...s].slice(0,8).map(x=>`<span class="chip">${x}</span>`).join("")}${s.size>8?`<span class="chip">+${s.size-8}</span>`:""}</div></div>`).join("")}`;
}
window.tog=t=>{off.has(t)?off.delete(t):off.add(t);document.querySelector(`[data-t="${t}"]`).classList.toggle("off");paint();};
svg.onclick=()=>{sel=null;document.getElementById("info").style.display="none";paint();};
// pan + zoom
let drag=null;
svg.addEventListener("mousedown",e=>{drag={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};});
window.addEventListener("mousemove",e=>{if(!drag)return;view.x=drag.vx+(e.clientX-drag.x);view.y=drag.vy+(e.clientY-drag.y);paint();});
window.addEventListener("mouseup",()=>drag=null);
svg.addEventListener("wheel",e=>{e.preventDefault();const s=e.deltaY<0?1.1:0.9;const r=svg.getBoundingClientRect();
  const mx=(e.clientX-r.left)/r.width*W,my=(e.clientY-r.top)/r.height*H;
  view.x=mx-(mx-view.x)*s;view.y=my-(my-view.y)*s;view.k*=s;paint();},{passive:false});
paint();
</script>
"""

if __name__ == "__main__":
    main()
