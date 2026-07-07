"""
build_analysis.py  (Phase E)
----------------------------
Generate analysis_dashboard.html — an interactive experiment-analysis tool over
the ontology-grounded KB: filter/sort, compare 2+ experiments, overlay their
profile curves (+ difference), a filtered node-link KG view, and a data-driven
uncertainty (source-tier confidence + cross-experiment spread).

Data-driven & tracked. Run:  python3 build_analysis.py -> analysis_dashboard.html
"""
import json
from pathlib import Path
from collections import defaultdict
from statistics import mean, pstdev

ROOT = Path(__file__).parent


def val_source(c):
    if c.get("from_label"): return "label"
    if c.get("derived"): return "derived"
    return "text"


def main():
    exps = []
    for d in sorted((ROOT / "output").glob("*/resolved/experiments.json")):
        pid = d.parent.parent.name
        for i, e in enumerate(json.loads(d.read_text())):
            conds = [{"q": c["quantity"], "v": c.get("value"), "u": c.get("unit"), "src": val_source(c)}
                     for c in (e.get("controlled") or []) if c.get("quantity")]
            measures = [dd["quantity"] for dd in (e.get("dependent") or []) if dd.get("quantity")]
            pts = e.get("points") or None
            exps.append({
                "id": f"{pid}:{i}", "pid": pid, "series": e.get("series_name") or "—",
                "material": e.get("material") or "—", "structure": e.get("structure") or "—",
                "process": e.get("process_type") or "—", "gran": e.get("granularity"),
                "rel": e.get("relevance"), "model": bool(e.get("is_model_result")),
                "varies": e.get("varies") or [], "measures": measures, "conds": conds,
                "points": pts if e.get("granularity") == "profile" else None,
                "xax": e.get("x_label"), "yax": e.get("y_label"),
                "fig": (e.get("provenance") or {}).get("figure_id"),
            })

    materials = sorted({e["material"] for e in exps if e["material"] != "—"})
    quantities = sorted({q for e in exps for q in
                         [c["q"] for c in e["conds"]] + e["measures"] + e["varies"]})
    # numeric ranges per condition quantity (for range filters)
    vals = defaultdict(list)
    for e in exps:
        for c in e["conds"]:
            if isinstance(c["v"], (int, float)):
                vals[c["q"]].append(c["v"])
    ranges = {q: [min(v), max(v)] for q, v in vals.items() if len(v) > 1}
    # cross-experiment spread (uncertainty) per (material, quantity)
    grp = defaultdict(list)
    for e in exps:
        for c in e["conds"]:
            if isinstance(c["v"], (int, float)):
                grp[(e["material"], c["q"])].append(c["v"])
    spread = [{"material": m, "q": q, "n": len(v), "mean": round(mean(v), 4),
               "std": round(pstdev(v), 4) if len(v) > 1 else 0.0,
               "min": round(min(v), 4), "max": round(max(v), 4)}
              for (m, q), v in grp.items() if len(v) >= 3]
    spread.sort(key=lambda s: -s["n"])

    data = {"exps": exps, "materials": materials, "quantities": quantities,
            "ranges": ranges, "spread": spread[:60],
            "papers": sorted({e["pid"] for e in exps})}
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    (ROOT / "analysis_dashboard.html").write_text(html)
    print(f"wrote analysis_dashboard.html  ({len(html)//1024} KB)  "
          f"{len(exps)} experiments, {len(materials)} materials, {len(quantities)} quantities")


TEMPLATE = r"""<title>ALD Experiment Analysis</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;
 --line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --c1:#2a78d6;--c2:#1baf7a;--c3:#eda100;--c4:#4a3aa7;--c5:#e34948;--c6:#e87ba4;--grey:#9aa0aa;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;
 --ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --c1:#3987e5;--c2:#199e70;--c3:#c98500;--c4:#9085e9;--c5:#e66767;--c6:#d55181;--grey:#828892;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;
 --ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;--c1:#3987e5;--c2:#199e70;--c3:#c98500;--c4:#9085e9;--c5:#e66767;--c6:#d55181;--grey:#828892;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;
 --line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;--c1:#2a78d6;--c2:#1baf7a;--c3:#eda100;--c4:#4a3aa7;--c5:#e34948;--c6:#e87ba4;--grey:#9aa0aa;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:26px 22px 60px}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.serif{font-family:"Iowan Old Style","Charter",Georgia,serif}
h1{font-size:24px;margin:0 0 3px;font-weight:600}.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);font-size:13px;margin-bottom:16px}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:16px}
.tabs button{background:none;border:0;border-bottom:2px solid transparent;color:var(--ink2);padding:9px 14px;font-size:13.5px;cursor:pointer;font-weight:500}
.tabs button.on{color:var(--ink);border-color:var(--accent)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
select,input{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 9px;color:var(--ink);font-size:12.5px}
input[type=text]{min-width:180px}
label.f{font-size:11.5px;color:var(--ink3);display:flex;flex-direction:column;gap:3px}
.count{margin-left:auto;font-size:12px;color:var(--ink3)}
.tablewrap{border:1px solid var(--line);border-radius:10px;overflow:auto;max-height:520px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{position:sticky;top:0;background:var(--panel);text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);
 color:var(--ink3);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;cursor:pointer;white-space:nowrap}
td{padding:7px 9px;border-bottom:1px solid var(--line2);white-space:nowrap}
tr:hover{background:var(--line2)}
.tag{font-size:10px;padding:1px 6px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.pill{font-size:10px;padding:1px 7px;border-radius:20px}
.pill.experimental{background:color-mix(in srgb,var(--c2) 16%,var(--panel));color:var(--c2)}
.pill.model{background:color-mix(in srgb,var(--c4) 18%,var(--panel));color:var(--c4)}
.pill.background{background:color-mix(in srgb,var(--c5) 16%,var(--panel));color:var(--c5)}
svg{display:block}.svgwrap{overflow:auto}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--ink2);margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:5px}.dot{width:9px;height:9px;border-radius:3px}
.cmpgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.cmpgrid{grid-template-columns:1fr}}
.src-label{color:var(--c2)}.src-text{color:var(--ink2)}.src-chart{color:var(--c1)}.src-derived{color:var(--c3)}
.hint{font-size:12px;color:var(--ink3);margin:2px 0 10px}
.chk{width:14px;height:14px}
.selbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;font-size:12px;color:var(--ink2)}
.gnode{cursor:pointer}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base</div>
<h1 class="serif">Experiment analysis</h1>
<div class="sub" id="sub"></div>
<div class="tabs">
  <button class="on" onclick="tab('explore',this)">Explore &amp; filter</button>
  <button onclick="tab('compare',this)">Compare &amp; overlay</button>
  <button onclick="tab('graph',this)">Knowledge graph</button>
  <button onclick="tab('uncert',this)">Uncertainty</button>
</div>

<div id="explore" class="pane">
  <div class="toolbar">
    <label class="f">material<select id="fmat"></select></label>
    <label class="f">has quantity<select id="fq"></select></label>
    <label class="f" id="rangewrap" style="display:none">range<span style="display:flex;gap:4px">
      <input id="rmin" type="text" style="width:64px" placeholder="min" oninput="render()">
      <input id="rmax" type="text" style="width:64px" placeholder="max" oninput="render()"></span></label>
    <label class="f">granularity<select id="fgran"><option value="">any</option><option>profile</option><option>sweep_point</option><option>single</option></select></label>
    <label class="f">relevance<select id="frel"><option value="">any</option><option>experimental</option><option>model</option><option>background</option></select></label>
    <label class="f">search<input id="fsearch" type="text" placeholder="series / material…" oninput="render()"></label>
    <span class="count" id="count"></span>
  </div>
  <div class="hint">click column headers to sort · tick rows to add to Compare (max 6)</div>
  <div class="tablewrap"><table id="tbl"><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
</div>

<div id="compare" class="pane" style="display:none">
  <div class="selbar" id="selbar"></div>
  <div class="cmpgrid">
    <div class="card"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">aligned conditions (colour = source)</div>
      <div class="svgwrap"><table id="cmptbl" class="mono" style="font-size:11.5px"></table></div>
      <div class="legend"><span><i class="dot" style="background:var(--c2)"></i>label</span>
        <span><i class="dot" style="background:var(--ink2)"></i>text</span>
        <span><i class="dot" style="background:var(--c1)"></i>chart</span>
        <span><i class="dot" style="background:var(--c3)"></i>derived</span></div></div>
    <div class="card"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">overlay of profile curves</div>
      <div class="svgwrap"><div id="overlay"></div></div>
      <div class="legend" id="ovlegend"></div></div>
  </div>
</div>

<div id="graph" class="pane" style="display:none">
  <div class="hint">nodes = the currently-filtered experiments (small) + their shared materials / quantities / series (large). Click an entity to highlight everything linked to it.</div>
  <div class="card svgwrap"><div id="kg"></div></div>
  <div class="legend"><span><i class="dot" style="background:var(--c1)"></i>experiment</span>
    <span><i class="dot" style="background:var(--c2)"></i>material</span>
    <span><i class="dot" style="background:var(--c3)"></i>quantity</span>
    <span><i class="dot" style="background:var(--c4)"></i>series</span></div>
</div>

<div id="uncert" class="pane" style="display:none">
  <div class="hint">Empirical uncertainty: spread of each quantity across comparable experiments (same material, n≥3). Source-tier confidence is shown per value in Compare.</div>
  <div class="tablewrap"><table id="unctbl" class="mono" style="font-size:12px"></table></div>
</div>
</div>
<script>
const D=/*DATA*/, E=D.exps;
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const SVGNS="http://www.w3.org/2000/svg";
const el=(t,a)=>{const e=document.createElementNS(SVGNS,t);for(const k in a)e.setAttribute(k,a[k]);return e;};
const tx=(x,y,s,o={})=>{const t=el("text",{x,y,...o});t.textContent=s;return t;};
const cget=(e,q)=>{const c=e.conds.find(c=>c.q===q);return c?c.v:undefined;};
document.getElementById("sub").textContent=`${E.length} experiments · ${D.materials.length} materials · ${D.quantities.length} quantities · ${D.papers.length} papers`;
let sort={k:"pid",dir:1}, sel=new Set();

// filters
const fmat=document.getElementById("fmat"), fq=document.getElementById("fq");
fmat.innerHTML='<option value="">any material</option>'+D.materials.map(m=>`<option>${m}</option>`).join("");
fq.innerHTML='<option value="">any quantity</option>'+D.quantities.map(q=>`<option>${q}</option>`).join("");
[fmat,fq,"fgran","frel"].forEach(x=>(typeof x==="string"?document.getElementById(x):x).addEventListener("change",()=>{
  document.getElementById("rangewrap").style.display=(fq.value in D.ranges)?"":"none";render();}));

const COLS=[["pid","paper"],["series","series"],["material","material"],["gran","granularity"],["rel","relevance"],["nq","#cond"]];
function rows(){
  const mat=fmat.value,q=fq.value,g=document.getElementById("fgran").value,r=document.getElementById("frel").value,
    s=document.getElementById("fsearch").value.toLowerCase(),
    rmin=parseFloat(document.getElementById("rmin").value),rmax=parseFloat(document.getElementById("rmax").value);
  let out=E.filter(e=>(!mat||e.material===mat)&&(!g||e.gran===g)&&(!r||e.rel===r)&&
    (!q||e.conds.some(c=>c.q===q)||e.measures.includes(q)||e.varies.includes(q))&&
    (!s||[e.series,e.material,e.pid].join(" ").toLowerCase().includes(s)));
  if(q&&(!isNaN(rmin)||!isNaN(rmax)))out=out.filter(e=>{const v=cget(e,q);return v!=null&&(isNaN(rmin)||v>=rmin)&&(isNaN(rmax)||v<=rmax);});
  const kf=e=>sort.k==="nq"?e.conds.length:e[sort.k];
  out.sort((a,b)=>(kf(a)>kf(b)?1:kf(a)<kf(b)?-1:0)*sort.dir);
  return out;
}
function render(){
  const rs=rows();document.getElementById("count").textContent=rs.length+" / "+E.length;
  document.getElementById("thead").innerHTML="<tr><th></th>"+COLS.map(([k,l])=>`<th onclick="setSort('${k}')">${l}${sort.k===k?(sort.dir>0?" ▲":" ▼"):""}</th>`).join("")+"</tr>";
  document.getElementById("tbody").innerHTML=rs.slice(0,500).map(e=>`<tr>
    <td><input class="chk" type="checkbox" ${sel.has(e.id)?"checked":""} onchange="togSel('${e.id}',this.checked)"></td>
    <td class="mono">${e.pid}</td><td>${e.series}</td><td class="mono">${e.material}</td>
    <td><span class="tag">${e.gran}</span></td><td><span class="pill ${e.rel}">${e.rel}</span></td>
    <td class="mono">${e.conds.length}</td></tr>`).join("");
  drawGraph(rs);
}
window.setSort=k=>{sort.dir=(sort.k===k?-sort.dir:1);sort.k=k;render();};
window.togSel=(id,on)=>{on?(sel.size<6&&sel.add(id)):sel.delete(id);drawCompare();};
window.render=render;

// ---- compare + overlay ----
function drawCompare(){
  const items=[...sel].map(id=>E.find(e=>e.id===id));
  document.getElementById("selbar").innerHTML=items.length?("comparing: "+items.map(e=>`<span class="tag">${e.material} ${e.series}</span>`).join(" ")):"tick rows in Explore to compare (max 6).";
  const cols=["c1","c2","c3","c4","c5","c6"].map(c=>CSS("--"+c));
  const keys=[...new Set(items.flatMap(e=>e.conds.map(c=>c.q)))].sort();
  const src2col={label:"var(--c2)",text:"var(--ink2)",chart:"var(--c1)",derived:"var(--c3)"};
  let h="<tr><td></td>"+items.map((e,i)=>`<td style="color:${cols[i]};font-weight:600">${e.series}</td>`).join("")+"</tr>";
  for(const k of keys){h+=`<tr><td style="color:var(--ink3)">${k}</td>`+items.map(e=>{
    const c=e.conds.find(c=>c.q===k);return `<td style="color:${c?src2col[c.src]:'var(--line)'}">${c?(c.v??"·")+" "+(c.u||""):"—"}</td>`;}).join("")+"</tr>";}
  document.getElementById("cmptbl").innerHTML=h;
  // overlay profiles
  const profs=items.map((e,i)=>({e,i})).filter(o=>o.e.points&&o.e.points.length);
  const box={w:560,h:320,l:52,b:38,t:12,r:12};
  const s=el("svg",{width:"100%",viewBox:`0 0 ${box.w} ${box.h}`,height:box.h});
  if(!profs.length){s.appendChild(tx(box.w/2,box.h/2,"select profile experiments to overlay curves",{fill:CSS("--ink3"),"font-size":12,"text-anchor":"middle"}));}
  else{
    const all=profs.flatMap(o=>o.e.points);
    const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);
    const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
    const X=v=>box.l+(v-xmin)/((xmax-xmin)||1)*(box.w-box.l-box.r);
    const Y=v=>box.h-box.b-(v-ymin)/((ymax-ymin)||1)*(box.h-box.b-box.t);
    [0,.25,.5,.75,1].forEach(f=>{const y=box.t+f*(box.h-box.b-box.t);s.appendChild(el("line",{x1:box.l,y1:y,x2:box.w-box.r,y2:y,stroke:CSS("--line2")}));});
    s.appendChild(tx(box.l,box.h-8,(profs[0].e.xax||"x").slice(0,40),{fill:CSS("--ink3"),"font-size":10}));
    s.appendChild(tx(6,box.t+8,(profs[0].e.yax||"y").slice(0,26),{fill:CSS("--ink3"),"font-size":10}));
    profs.forEach(o=>{const pts=o.e.points.slice().sort((a,b)=>a[0]-b[0]);
      const d=pts.map((p,k)=>(k?"L":"M")+X(p[0]).toFixed(1)+" "+Y(p[1]).toFixed(1)).join(" ");
      s.appendChild(el("path",{d,fill:"none",stroke:cols[o.i],"stroke-width":2}));
      pts.forEach(p=>s.appendChild(el("circle",{cx:X(p[0]),cy:Y(p[1]),r:2.4,fill:cols[o.i]})));});
  }
  document.getElementById("overlay").innerHTML="";document.getElementById("overlay").appendChild(s);
  document.getElementById("ovlegend").innerHTML=profs.map(o=>`<span><i class="dot" style="background:${cols[o.i]}"></i>${o.e.series}</span>`).join("");
}

// ---- knowledge graph (filtered, aggregated, force layout) ----
let gnodes=[],glinks=[];
function drawGraph(rs){
  const set=rs.slice(0,80);            // keep legible
  const nodes={},links=[];
  const add=(id,type,label)=>{if(!nodes[id])nodes[id]={id,type,label,deg:0};return nodes[id];};
  set.forEach(e=>{add(e.id,"exp",e.series);
    const link=(t)=>{if(nodes[t]||true){links.push({s:e.id,t});}};
    const m=add("m:"+e.material,"mat",e.material);link("m:"+e.material);
    [...new Set(e.conds.map(c=>c.q).concat(e.measures))].slice(0,6).forEach(q=>{add("q:"+q,"q",q);link("q:"+q);});
  });
  Object.values(nodes).forEach(n=>n.deg=0);links.forEach(l=>{if(nodes[l.t])nodes[l.t].deg++;});
  gnodes=Object.values(nodes);glinks=links.filter(l=>nodes[l.s]&&nodes[l.t]);
  layout(gnodes,glinks);
  if(document.getElementById("graph").style.display!=="none")paintGraph();
}
function layout(nodes,links,W=1120,H=560){
  nodes.forEach(n=>{if(n.x==null){n.x=W/2+(Math.random()-.5)*W*0.7;n.y=H/2+(Math.random()-.5)*H*0.7;}n.vx=0;n.vy=0;});
  const idx=Object.fromEntries(nodes.map(n=>[n.id,n]));
  for(let it=0;it<180;it++){
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
      const a=nodes[i],b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1,d=Math.sqrt(d2),f=900/d2;
      a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
    links.forEach(l=>{const a=idx[l.s],b=idx[l.t];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-70)*0.02;
      a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;});
    nodes.forEach(n=>{n.vx+=(W/2-n.x)*0.002;n.vy+=(H/2-n.y)*0.002;n.x+=(n.vx*=0.8);n.y+=(n.vy*=0.8);});
  }
}
let hi=null;
function paintGraph(){
  const W=1120,H=560,col={exp:"--c1",mat:"--c2",q:"--c3",series:"--c4"};
  const s=el("svg",{width:"100%",viewBox:`0 0 ${W} ${H}`,height:H});
  const idx=Object.fromEntries(gnodes.map(n=>[n.id,n]));
  glinks.forEach(l=>{const a=idx[l.s],b=idx[l.t];const on=hi&&(l.s===hi||l.t===hi);
    s.appendChild(el("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:CSS("--line"),"stroke-width":on?1.6:.6,opacity:hi&&!on?.15:.7}));});
  gnodes.forEach(n=>{const r=n.type==="exp"?4:Math.min(6+n.deg,16);const on=!hi||n.id===hi||glinks.some(l=>(l.s===hi&&l.t===n.id)||(l.t===hi&&l.s===n.id));
    const g=el("g",{class:"gnode"});g.appendChild(el("circle",{cx:n.x,cy:n.y,r,fill:CSS(col[n.type]),opacity:on?1:.2,stroke:CSS("--surface"),"stroke-width":1}));
    if(n.type!=="exp"&&n.deg>1)g.appendChild(tx(n.x+r+3,n.y+3,n.label,{fill:CSS("--ink2"),"font-size":10,opacity:on?1:.2}));
    g.onclick=()=>{hi=hi===n.id?null:n.id;paintGraph();};s.appendChild(g);});
  const c=document.getElementById("kg");c.innerHTML="";c.appendChild(s);
}

// ---- uncertainty ----
document.getElementById("unctbl").innerHTML="<tr><th>material</th><th>quantity</th><th>n</th><th>mean</th><th>± std</th><th>min</th><th>max</th></tr>"+
 D.spread.map(s=>`<tr><td>${s.material}</td><td>${s.q}</td><td>${s.n}</td><td>${s.mean}</td><td>±${s.std}</td><td>${s.min}</td><td>${s.max}</td></tr>`).join("");

// ---- tabs ----
window.tab=(id,btn)=>{document.querySelectorAll(".pane").forEach(p=>p.style.display="none");
  document.getElementById(id).style.display="";document.querySelectorAll(".tabs button").forEach(b=>b.classList.remove("on"));btn.classList.add("on");
  if(id==="graph")paintGraph();if(id==="compare")drawCompare();};
render();drawCompare();
</script>
"""

if __name__ == "__main__":
    main()
