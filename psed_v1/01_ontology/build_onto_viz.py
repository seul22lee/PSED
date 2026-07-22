#!/usr/bin/env python3
"""
build_onto_viz.py — a self-contained, theme-aware graph visualization of the COMPILED
ontology (ald_ontology.json): how classes, quantity kinds, categories/families and the
individual materials/precursors/coreactants/ligands relate.

Nodes:  Class · Category · Family · Quantity · Material · Precursor · Coreactant · Ligand
Edges:  subclass_of · instance_of · in_category · in_family · specializes · defined_by
        · deposits · has_ligand

Reads whichever ald_ontology.json is current (i.e. the most recently rebuilt version),
so run it AFTER build_ontology.py. Writes ontology_viewer.html next to it. No external
deps — inline SVG force graph, filter chips, search, click-for-detail. Same viewer
engine as 0706_pipeline/build_kg.py.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
ONTO = json.loads((ROOT / "ald_ontology.json").read_text())


def build():
    nodes, links = [], []
    seen = set()

    def add(nid, ntype, label, **extra):
        if nid in seen:
            return nid
        seen.add(nid)
        nodes.append({"id": nid, "type": ntype, "label": label, **extra})
        return nid

    def link(s, t, e):
        if s in seen and t in seen:
            links.append({"s": s, "t": t, "e": e})

    # ---- class taxonomy (Entity → Material → Oxide …) --------------------------
    for c in ONTO.get("classes", []):
        add("cls::" + c["id"], "Class", c["id"])
    for c in ONTO.get("classes", []):
        p = c.get("subclass_of")
        if p:
            link("cls::" + c["id"], "cls::" + p, "subclass_of")

    # ---- categories & families (quantity groupings) ----------------------------
    qr = ONTO.get("quantity_relations", {})
    for cat in (qr.get("categories") or {}):
        add("cat::" + cat, "Category", cat)
    for fam in (qr.get("families") or {}):
        add("fam::" + fam, "Family", fam)

    # ---- quantity kinds → category / family / specializes / defined_by ---------
    for q in ONTO.get("quantity_kinds", []):
        add("qk::" + q["id"], "Quantity", q["id"],
            unit=q.get("unit") or "", recipe_role=q.get("recipe_role") or "",
            category=q.get("category") or "", family=q.get("family") or "",
            source=q.get("source") or "core")
    for q in ONTO.get("quantity_kinds", []):
        qid = "qk::" + q["id"]
        if q.get("category"):
            link(qid, "cat::" + q["category"], "in_category")
        if q.get("family"):
            link(qid, "fam::" + q["family"], "in_family")
        if q.get("specializes"):
            link(qid, "qk::" + q["specializes"], "specializes")
        db = q.get("defined_by") or {}
        for other in (db.get("inputs") or db.get("from") or []):
            if isinstance(other, str):
                link(qid, "qk::" + other, "defined_by")

    # ---- geometry layer: geometry category → geometry_class → geometry quantities
    for gc, spec in (ONTO.get("geometry_classes", {}) or {}).items():
        add("gc::" + gc, "GeometryClass", gc, transport=spec.get("transport") or "",
            cremers=spec.get("cremers_class") or "")
        link("gc::" + gc, "cat::geometry", "in_category")     # under the geometry category
        for q in (spec.get("parameters") or []):
            link("gc::" + gc, "qk::" + q, "has_parameter")    # the quantities that describe it
    # models declare which geometry class they are valid for
    for m in ONTO.get("models", []):
        for gc in (m.get("applies_to_geometry") or []):
            add("mdl::" + m["id"], "Model", m["id"])
            link("mdl::" + m["id"], "gc::" + gc, "applies_to")

    # ---- individuals: materials / precursors / coreactants / ligands -----------
    ind = ONTO.get("individuals", {})
    for m in ind.get("materials", []):
        add("mat::" + m["id"], "Material", m["id"],
            formula=m.get("formula") or "", molar_mass=m.get("molar_mass"),
            cls=m.get("class") or "")
        if m.get("class"):
            link("mat::" + m["id"], "cls::" + m["class"], "instance_of")
    for lf in ind.get("ligand_families", []):
        add("lig::" + lf["id"], "Ligand", lf["id"])
    for p in ind.get("precursors", []):
        pid = add("prec::" + p["id"], "Precursor", p["id"],
                  full_name=p.get("full_name") or "", molar_mass=p.get("molar_mass"),
                  molecular_diameter=p.get("molecular_diameter"), cls=p.get("class") or "")
        if p.get("class"):
            link(pid, "cls::" + p["class"], "instance_of")
        if p.get("has_ligand"):
            link(pid, "lig::" + p["has_ligand"], "has_ligand")
        for dep in (p.get("deposits") or []):
            link(pid, "mat::" + dep, "deposits")
    for co in ind.get("coreactants", []):
        cid = add("core::" + co["id"], "Coreactant", co["id"],
                  full_name=co.get("full_name") or "", cls=co.get("class") or "")
        if co.get("class"):
            link(cid, "cls::" + co["class"], "instance_of")

    # degree (for node sizing)
    deg = Counter()
    for l in links:
        deg[l["s"]] += 1
        deg[l["t"]] += 1
    for n in nodes:
        n["deg"] = deg.get(n["id"], 0)

    counts = Counter(n["type"] for n in nodes)
    ecounts = Counter(l["e"] for l in links)
    return {"nodes": nodes, "links": links,
            "counts": dict(counts), "edgeCounts": dict(ecounts),
            "meta": {"quantity_kinds": counts.get("Quantity", 0),
                     "individuals": counts.get("Material", 0) + counts.get("Precursor", 0)
                     + counts.get("Coreactant", 0) + counts.get("Ligand", 0),
                     "auto": sum(1 for n in nodes if n.get("source") == "auto-proposed")}}


def main():
    data = build()
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    out = ROOT / "ontology_viewer.html"
    out.write_text(html)
    m = data["meta"]
    print(f"wrote {out.name}  ({len(html)//1024} KB)  {len(data['nodes'])} nodes, {len(data['links'])} edges")
    print(f"   node types: {data['counts']}")
    print(f"   edge types: {data['edgeCounts']}")
    print(f"   {m['auto']} auto-proposed quantities highlighted")


TEMPLATE = r"""<title>ALD Ontology graph</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --Class:#4a3aa7;--Category:#c65d3b;--Family:#7d5ba6;--Quantity:#2a78d6;--Material:#1baf7a;--Precursor:#e34948;--Coreactant:#e87ba4;--Ligand:#c98500;--GeometryClass:#0f9bd8;--Model:#d81b60;
 --e-subclass_of:#4a3aa7;--e-instance_of:#9aa0aa;--e-in_category:#c65d3b;--e-in_family:#7d5ba6;--e-specializes:#1baf7a;--e-defined_by:#2a78d6;--e-deposits:#1baf7a;--e-has_ligand:#c98500;--e-has_parameter:#0f9bd8;--e-applies_to:#d81b60;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --Class:#9085e9;--Category:#e07a54;--Family:#a98cd6;--Quantity:#3987e5;--Material:#199e70;--Precursor:#e66767;--Coreactant:#d55181;--Ligand:#c98500;--GeometryClass:#0f9bd8;--Model:#d81b60;
 --e-subclass_of:#9085e9;--e-instance_of:#6b7079;--e-in_category:#e07a54;--e-in_family:#a98cd6;--e-specializes:#199e70;--e-defined_by:#3987e5;--e-deposits:#199e70;--e-has_ligand:#c98500;--e-has_parameter:#0f9bd8;--e-applies_to:#d81b60;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --Class:#9085e9;--Category:#e07a54;--Family:#a98cd6;--Quantity:#3987e5;--Material:#199e70;--Precursor:#e66767;--Coreactant:#d55181;--Ligand:#c98500;--GeometryClass:#0f9bd8;--Model:#d81b60;
 --e-subclass_of:#9085e9;--e-instance_of:#6b7079;--e-in_category:#e07a54;--e-in_family:#a98cd6;--e-specializes:#199e70;--e-defined_by:#3987e5;--e-deposits:#199e70;--e-has_ligand:#c98500;--e-has_parameter:#0f9bd8;--e-applies_to:#d81b60;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --Class:#4a3aa7;--Category:#c65d3b;--Family:#7d5ba6;--Quantity:#2a78d6;--Material:#1baf7a;--Precursor:#e34948;--Coreactant:#e87ba4;--Ligand:#c98500;--GeometryClass:#0f9bd8;--Model:#d81b60;
 --e-subclass_of:#4a3aa7;--e-instance_of:#9aa0aa;--e-in_category:#c65d3b;--e-in_family:#7d5ba6;--e-specializes:#1baf7a;--e-defined_by:#2a78d6;--e-deposits:#1baf7a;--e-has_ligand:#c98500;--e-has_parameter:#0f9bd8;--e-applies_to:#d81b60;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1320px;margin:0 auto;padding:22px 20px 40px}
h1{font-size:23px;margin:0 0 2px;font-weight:600;font-family:"Iowan Old Style",Georgia,serif}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);margin-bottom:12px}
.bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
.grp{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);margin:0 2px}
.chip{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:4px 11px 4px 8px;color:var(--ink2);font-size:12px;cursor:pointer;user-select:none}
.chip.off{opacity:.32;text-decoration:line-through}
.dot{width:10px;height:10px;border-radius:3px;flex:none}.edg{width:16px;border-top:3px solid;flex:none}
input[type=search]{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:5px 9px;color:var(--ink);font-size:12px;min-width:150px}
button.mini{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:5px 10px;color:var(--accent);font-size:12px;cursor:pointer}
.stage{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:6px}
svg{display:block;width:100%;height:680px;touch-action:none;cursor:grab}
svg.drag{cursor:grabbing}
.info{position:absolute;top:12px;right:12px;width:270px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 13px;font-size:12.5px;display:none;max-height:90%;overflow:auto}
.info h3{margin:0 0 6px;font-size:14px}.info .k{color:var(--ink3);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.info .row{margin:5px 0}.info .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.ichip{font-size:11px;padding:1px 7px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.hint{font-size:12px;color:var(--ink3);margin-top:8px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--ink2);margin-top:8px}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · compiled ontology</div>
<h1>Ontology graph</h1>
<div class="sub" id="sub"></div>
<div class="bar"><span class="grp">nodes</span><span id="legNodes"></span></div>
<div class="bar"><span class="grp">edges</span><span id="legEdges"></span></div>
<div class="bar"><input type="search" id="search" placeholder="search a class / quantity / species…">
  <button class="mini" onclick="relayout()">relayout</button>
  <button class="mini" onclick="resetAll()">reset</button></div>
<div class="stage"><svg id="svg"></svg><div class="info" id="info"></div></div>
<div class="hint">Drag a node to pin · scroll to zoom · drag background to pan · click a node for its relations. Auto-proposed quantities have a ✦.</div>
</div>
<script>
const D=/*DATA*/;
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const NS="http://www.w3.org/2000/svg",el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a||{})e.setAttribute(k,a[k]);return e;};
const VBW=1280,VBH=680;
const NT=["Category","GeometryClass","Model","Family","Quantity","Class","Material","Precursor","Coreactant","Ligand"].filter(t=>D.counts[t]);
const ET=["in_category","has_parameter","applies_to","in_family","subclass_of","instance_of","specializes","defined_by","deposits","has_ligand"].filter(t=>D.edgeCounts[t]);
const offN=new Set(["Class"]), offE=new Set(["instance_of"]);   // taxonomy hidden by default (toggle on); keeps the quantity/species relations legible on load
document.getElementById("sub").textContent=`${D.nodes.length} nodes · ${D.links.length} edges · `+NT.map(t=>`${D.counts[t]} ${t}`).join(" · ");

document.getElementById("legNodes").insertAdjacentHTML("beforeend",NT.map(t=>`<span class="chip ${offN.has(t)?"off":""}" data-t="${t}" onclick="togN('${t}')"><span class="dot" style="background:var(--${t})"></span>${t} <span style="color:var(--ink3)">${D.counts[t]}</span></span>`).join(""));
document.getElementById("legEdges").insertAdjacentHTML("beforeend",ET.map(t=>`<span class="chip ${offE.has(t)?"off":""}" data-e="${t}" onclick="togE('${t}')"><span class="edg" style="border-color:var(--e-${t})"></span>${t} <span style="color:var(--ink3)">${D.edgeCounts[t]}</span></span>`).join(""));
window.togN=t=>{offN.has(t)?offN.delete(t):offN.add(t);document.querySelector(`[data-t="${t}"]`).classList.toggle("off");
  layout(200);fit();frame();};   // re-distribute the now-visible set to fill the window
window.togE=t=>{offE.has(t)?offE.delete(t):offE.add(t);document.querySelector(`[data-e="${t}"]`).classList.toggle("off");frame();};

const idx=Object.fromEntries(D.nodes.map(n=>[n.id,n]));
const nbr=Object.fromEntries(D.nodes.map(n=>[n.id,new Set()]));
D.links.forEach(l=>{if(nbr[l.s]&&nbr[l.t]){nbr[l.s].add(l.t);nbr[l.t].add(l.s);}});
const ring={Category:60,GeometryClass:110,Model:150,Family:95,Class:200,Quantity:300,Material:420,Ligand:470,Precursor:520,Coreactant:560};
const visN=()=>D.nodes.filter(n=>!offN.has(n.type));   // only the currently-shown node types
function seed(){D.nodes.forEach((n,i)=>{const r=ring[n.type]??380,a=i*2.399;n.x=VBW/2+r*Math.cos(a);n.y=VBH/2+r*Math.sin(a);n.vx=0;n.vy=0;});}
// layout distributes only the VISIBLE nodes, so hidden layers (e.g. the taxonomy) don't
// consume space or push the shown nodes into a corner.
function layout(iters){const V=visN(),S=new Set(V.map(n=>n.id));if(V.length<2)return;
  for(let it=0;it<iters;it++){
    for(let i=0;i<V.length;i++)for(let j=i+1;j<V.length;j++){const a=V[i],b=V[j];
      let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1,d=Math.sqrt(d2),f=3000/d2;a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
    D.links.forEach(l=>{if(!S.has(l.s)||!S.has(l.t))return;const a=idx[l.s],b=idx[l.t];
      let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-70)*0.016;a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;});
    V.forEach(n=>{if(n.fx==null){n.vx+=(VBW/2-n.x)*0.002;n.vy+=(VBH/2-n.y)*0.002;n.x+=(n.vx*=0.82);n.y+=(n.vy*=0.82);}});}}
function fit(pad){pad=pad||58;   // fit the VISIBLE dense core to the viewBox, clamp outliers to the edge
  const V=visN();if(!V.length)return;
  const xs=V.map(n=>n.x).sort((a,b)=>a-b),ys=V.map(n=>n.y).sort((a,b)=>a-b);
  const q=(v,p)=>{const k=(v.length-1)*p,f=Math.floor(k);return v[f]+(v[Math.min(f+1,v.length-1)]-v[f])*(k-f);};
  const x0=q(xs,0.05),x1=q(xs,0.95),y0=q(ys,0.05),y1=q(ys,0.95);
  const w=x1-x0||1,h=y1-y0||1,s=Math.min((VBW-2*pad)/w,(VBH-2*pad)/h);
  const ox=(VBW-2*pad-w*s)/2,oy=(VBH-2*pad-h*s)/2;
  D.nodes.forEach(n=>{const x=pad+(n.x-x0)*s+ox,y=pad+(n.y-y0)*s+oy;
    n.x=Math.min(Math.max(x,pad),VBW-pad);n.y=Math.min(Math.max(y,pad),VBH-pad);});}
seed();layout(300);fit();

const svg=el("svg",{viewBox:`0 0 ${VBW} ${VBH}`});svg.id="svg";
document.getElementById("svg").replaceWith(svg);
const view=el("g");svg.appendChild(view);
const gL=el("g");const gN=el("g");view.appendChild(gL);view.appendChild(gN);
D.links.forEach(l=>{l._el=el("line",{"stroke-linecap":"round"});gL.appendChild(l._el);});
D.nodes.forEach(n=>{n._g=el("g");n._c=el("circle",{stroke:CSS("--surface"),"stroke-width":1.3});
  n._t=el("text",{"font-size":11,"pointer-events":"none"});const lab=(n.source==="auto-proposed"?"✦":"")+n.label;
  n._t.textContent=lab.length>24?lab.slice(0,23)+"…":lab;
  n._g.appendChild(n._c);n._g.appendChild(n._t);gN.appendChild(n._g);
  n._c.addEventListener("pointerdown",ev=>startDrag(ev,n));});

let tx=0,ty=0,scale=1,sel=null,q="";
function updateView(){view.setAttribute("transform",`translate(${tx} ${ty}) scale(${scale})`);}
function visibleNodes(){
  const vis=new Set();
  D.nodes.forEach(n=>{if(!offN.has(n.type))vis.add(n.id);});
  return vis;
}
function frame(){
  const vis=visibleNodes(),hi=sel,ql=q.toLowerCase();
  D.links.forEach(l=>{const a=idx[l.s],b=idx[l.t],on=vis.has(l.s)&&vis.has(l.t)&&!offE.has(l.e);
    l._el.style.display=on?"":"none";if(!on)return;
    const near=hi&&(l.s===hi||l.t===hi),dim=hi&&!near;
    l._el.setAttribute("x1",a.x);l._el.setAttribute("y1",a.y);l._el.setAttribute("x2",b.x);l._el.setAttribute("y2",b.y);
    l._el.setAttribute("stroke",CSS("--e-"+l.e)||CSS("--line"));
    l._el.setAttribute("stroke-width",near?2.2:.8);
    l._el.setAttribute("opacity",dim?.05:.55);});
  D.nodes.forEach(n=>{const on=vis.has(n.id);n._g.style.display=on?"":"none";if(!on)return;
    const r=Math.min(6+n.deg*0.5,20);
    const near=!hi||n.id===hi||nbr[hi].has(n.id);
    const match=!ql||n.label.toLowerCase().includes(ql);
    n._c.setAttribute("cx",n.x);n._c.setAttribute("cy",n.y);n._c.setAttribute("r",r);
    n._c.setAttribute("fill",CSS("--"+n.type));
    n._c.setAttribute("opacity",(near&&match)?1:.12);
    n._c.setAttribute("stroke-width",n.id===hi?2.4:1.3);
    n._c.setAttribute("stroke",n.id===hi?CSS("--ink"):CSS("--surface"));
    n._c.style.cursor="grab";
    const showT=(n.type==="Category"||n.type==="Family"||n.type==="Class"||n.deg>=3||(ql&&match));
    n._t.style.display=showT?"":"none";
    if(showT){n._t.setAttribute("x",n.x+r+3);n._t.setAttribute("y",n.y+3.5);
      n._t.setAttribute("fill",CSS("--ink2"));n._t.setAttribute("font-weight",(n.type==="Category"||n.type==="Class")?600:400);
      n._t.setAttribute("opacity",(near&&match)?1:.12);}});
}
updateView();frame();

function toVB(ev){const r=svg.getBoundingClientRect();return {x:(ev.clientX-r.left)/r.width*VBW,y:(ev.clientY-r.top)/r.height*VBH};}
function toWorld(vb){return {x:(vb.x-tx)/scale,y:(vb.y-ty)/scale};}
let drag=null,pan=null,moved=0;
function startDrag(ev,n){ev.stopPropagation();ev.preventDefault();
  const w=toWorld(toVB(ev));drag={n,ox:w.x-n.x,oy:w.y-n.y};moved=0;svg.classList.add("drag");n.fx=n.x;n.fy=n.y;}
svg.addEventListener("pointerdown",ev=>{if(drag)return;pan={vb:toVB(ev)};moved=0;svg.classList.add("drag");});
svg.addEventListener("pointermove",ev=>{
  if(drag){const w=toWorld(toVB(ev));drag.n.x=w.x-drag.ox;drag.n.y=w.y-drag.oy;drag.n.fx=drag.n.x;drag.n.fy=drag.n.y;moved++;frame();}
  else if(pan){const vb=toVB(ev);tx+=vb.x-pan.vb.x;ty+=vb.y-pan.vb.y;pan.vb=vb;moved++;updateView();}});
function endDrag(){if(drag){if(moved<3){sel=(sel===drag.n.id?null:drag.n.id);showInfo(sel?drag.n:null);frame();}
    drag.n.fx=null;drag.n.fy=null;drag=null;}pan=null;svg.classList.remove("drag");}
svg.addEventListener("pointerup",endDrag);svg.addEventListener("pointerleave",endDrag);
svg.addEventListener("click",ev=>{if(ev.target===svg||ev.target===view){sel=null;showInfo(null);frame();}});
svg.addEventListener("wheel",ev=>{ev.preventDefault();const vb=toVB(ev),w=toWorld(vb),f=ev.deltaY<0?1.12:0.89;
  scale=Math.max(.2,Math.min(6,scale*f));tx=vb.x-w.x*scale;ty=vb.y-w.y*scale;updateView();},{passive:false});
document.getElementById("search").addEventListener("input",e=>{q=e.target.value;frame();});

function showInfo(n){const box=document.getElementById("info");
  if(!n){box.style.display="none";return;}box.style.display="block";
  const ls=D.links.filter(l=>l.s===n.id||l.t===n.id);const byRel={};
  ls.forEach(l=>{const o=idx[l.s===n.id?l.t:l.s];if(!o)return;(byRel[l.e]=byRel[l.e]||new Set()).add(o.label);});
  box.innerHTML=`<h3 style="color:var(--${n.type})">${(n.source==="auto-proposed"?"✦ ":"")}${n.label}</h3><div class="k">${n.type}</div>
    ${n.unit?`<div class="row"><span class="k">unit</span> ${n.unit}</div>`:""}
    ${n.recipe_role?`<div class="row"><span class="k">recipe role</span> ${n.recipe_role}</div>`:""}
    ${n.category?`<div class="row"><span class="k">category</span> ${n.category}</div>`:""}
    ${n.family?`<div class="row"><span class="k">family</span> ${n.family}</div>`:""}
    ${n.formula?`<div class="row"><span class="k">formula</span> ${n.formula}</div>`:""}
    ${n.full_name?`<div class="row"><span class="k">name</span> ${n.full_name}</div>`:""}
    ${n.cls?`<div class="row"><span class="k">class</span> ${n.cls}</div>`:""}
    ${n.molar_mass?`<div class="row"><span class="k">molar mass</span> ${n.molar_mass} g/mol</div>`:""}
    ${n.molecular_diameter?`<div class="row"><span class="k">molecular diameter</span> ${n.molecular_diameter} pm</div>`:""}
    ${n.source==="auto-proposed"?`<div class="row"><span class="k">provenance</span> auto-proposed from corpus</div>`:""}
    <div class="row"><span class="k">relations (${ls.length})</span></div>
    ${Object.entries(byRel).map(([e,s])=>`<div class="row"><span style="color:var(--e-${e})">${e}</span> <span style="color:var(--ink3)">(${s.size})</span><div class="chips">${[...s].slice(0,12).map(x=>`<span class="ichip">${x}</span>`).join("")}${s.size>12?`<span class="ichip">+${s.size-12}</span>`:""}</div></div>`).join("")}`;
}
window.relayout=()=>{seed();layout(300);fit();tx=0;ty=0;scale=1;updateView();frame();};
window.resetAll=()=>{offN.clear();offE.clear();q="";document.getElementById("search").value="";
  document.querySelectorAll(".chip").forEach(c=>c.classList.remove("off"));frame();};
</script>
"""

if __name__ == "__main__":
    main()
