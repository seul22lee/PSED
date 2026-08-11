#!/usr/bin/env python3
"""
pipeline/review/build_core_kg.py — two CORE scientific graphs, for comparison.

    python3 -m pipeline.review.build_core_kg

Writes:
    papers/_corpus/knowledge_graph_core_flat.json     Paper -> Experiment
    papers/_corpus/knowledge_graph_core_series.json   Paper -> ExperimentSeries -> Experiment
    reports/kg_core_flat.html
    reports/kg_core_series.html
    reports/kg_core_comparison.html

Read-only over the corpus. The existing full graph
(papers/_corpus/knowledge_graph_onto.json) is never touched: these are an
abstraction layer over the same validated resolved/canonical data.

The design question these answer: the full graph makes ConditionAssertion,
RawQuantityValue, CanonicalQuantityValue and TransformationExecution peer nodes,
which is right for audit and wrong for reading science. Here a VALUE
(temperature = 250 °C) is a property of the Experiment, while a CONCEPT
(QuantityKind:deposition_temperature) is a shared node — so "which experiments vary
temperature" is one hop, and "what was the temperature here" is a field.

Nothing is inferred. Series grouping uses experimental_series_id, which the resolve
layer mints only for a discrete_experimental_sweep; experiments without one are not
forced into a series.
"""
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import paths as P                                             # noqa: E402

FULL_KG = P.PAPERS / "_corpus" / "knowledge_graph_onto.json"
OUT_FLAT = P.PAPERS / "_corpus" / "knowledge_graph_core_flat.json"
OUT_SERIES = P.PAPERS / "_corpus" / "knowledge_graph_core_series.json"

CORE_TYPES = ["Paper", "ExperimentSeries", "Experiment", "Material", "Precursor",
              "Coreactant", "QuantityKind", "ResultSeries", "ProcessType",
              "GeometryClass", "Model", "ModelFamily"]


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def qname(q):
    """A QuantityKind's identity: the quantity concept, never its value."""
    if isinstance(q, dict):
        q = q.get("quantity")
    q = (q or "").strip()
    return q or None


def collect():
    """Everything the two variants share, read once from the resolved/canonical layer."""
    papers = sorted(P.papers())
    exps, series, results, curves = [], [], [], []
    for pid in papers:
        for row in load_json(P.resolved_json(pid, "experiments"), []) or []:
            exps.append(row)
        for row in load_json(P.resolved_json(pid, "series"), []) or []:
            series.append(row)
        r = load_json(P.resolved_json(pid, "results"), {}) or {}
        results.extend(r.get("results") or [])
        c = load_json(P.curves_json(pid), {}) or {}
        curves.extend(c.get("curves") or [])
    return papers, exps, series, results, curves


def build(variant, papers, exps, series, results, curves, full_kg):
    nodes, links = {}, []
    seen_edge = set()

    def node(nid, ntype, name, **props):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "ntype": ntype, "name": name, **props}
        return nid

    def link(s, t, etype):
        k = (s, t, etype)
        if s in nodes and t in nodes and k not in seen_edge:
            seen_edge.add(k)
            links.append({"source": s, "target": t, "etype": etype})

    # ---- canonical curve provenance -------------------------------------------
    # Join on the SOURCE SLICE (paper, docling figure index, panel, series label),
    # which is what result.source_series_id encodes. linked_experiment_ids looks like
    # the natural key but is empty for most curves, and using it alone left 354 of 835
    # result series with source "unknown" and lost every simulated label.
    def _lab(x):
        """An unlabelled single curve is written '<single>' in a result id and '' in a
        canonical curve; without normalising them the two never join."""
        x = str(x if x is not None else "").strip()
        return "" if x in ("<single>", "None", "primary") else x

    curve_by_slice, curve_by_panel, curve_by_entity = {}, defaultdict(list), defaultdict(list)
    for c in curves:
        src = c.get("source") or {}
        k = (src.get("paper_id"), str(src.get("figure_index")), str(src.get("panel")))
        curve_by_slice[k + (_lab(src.get("series")),)] = c
        curve_by_panel[k].append(c)
        for eid in (src.get("linked_experiment_ids") or []):
            curve_by_entity[eid.split("__case")[0]].append(c)

    def curves_for(entity_id, source_series_id=None):
        """Canonical curves behind a resolved entity.

        Three keys in order of strength: the exact source slice, the same slice with an
        unlabelled-series placeholder normalised, and — only when a panel holds exactly
        one curve — the panel itself. Anything else stays unjoined and the ResultSeries
        reports source "unknown" rather than guessing measured.
        """
        if source_series_id:
            parts = str(source_series_id).split("|")
            if len(parts) >= 5:
                k = (parts[0], parts[1], parts[3])
                c = curve_by_slice.get(k + (_lab(parts[4]),))
                if c:
                    return [c]
                same = curve_by_panel.get(k) or []
                if len(same) == 1:
                    return same
        return curve_by_entity.get(entity_id) or []

    ssid_by_entity = {}
    for r in results:
        if r.get("result_series_id") and r.get("source_series_id"):
            ssid_by_entity.setdefault(r["result_series_id"], r["source_series_id"])

    # ---- shared concept nodes -------------------------------------------------
    for pid in papers:
        node("paper::%s" % pid, "Paper", pid, paper_id=pid)

    # ---- experiments ----------------------------------------------------------
    ser_by_entity = {s.get("entity_id"): s for s in series}
    res_by_entity = defaultdict(list)
    for r in results:
        res_by_entity[r.get("result_series_id")].append(r)

    exp_of_series = defaultdict(list)
    for e in exps:
        eid = e.get("exp_id")
        ent = e.get("entity_id")
        pid = e.get("paper_id") or e.get("doi")
        if not eid or not pid:
            continue
        conds = {}
        for c in (e.get("controlled") or []):
            q = qname(c.get("quantity"))
            if q and c.get("value") is not None and q not in conds:
                conds[q] = {"value": c.get("value"), "unit": c.get("unit"),
                            "source": (c.get("origin") or {}).get("from") or c.get("source"),
                            "recipe_role": c.get("recipe_role")}
        meas = qname(e.get("measurand"))
        varied = [q for q in {qname(e.get("series_varies")), qname(e.get("coordinate"))} if q]
        rs = res_by_entity.get(ent) or []
        crv = curves_for(ent, ssid_by_entity.get(ent))
        dsrc = sorted({(c.get("source") or {}).get("data_source") for c in crv if
                       (c.get("source") or {}).get("data_source")})
        nid = node(
            "exp::%s" % eid, "Experiment", eid,
            paper_id=pid, experiment_id=eid, entity_id=ent,
            material=[e["material"]] if e.get("material") else [],
            precursor=e.get("precursors") or [], coreactant=e.get("coreactants") or [],
            process_type=e.get("process_type"), geometry=e.get("geometry_class"),
            fixed_conditions=conds, varied_quantities=varied,
            measured_quantities=[meas] if meas else [],
            granularity=e.get("granularity"), classification=e.get("classification"),
            record_kind=e.get("record_kind"), relevance=e.get("relevance"),
            data_source=dsrc,
            source_figures=[x for x in [e.get("printed_figure_number")] if x],
            panel=e.get("panel"), n_points=len(e.get("points") or []),
            result_series_ids=[r.get("result_series_id") for r in rs],
            provenance={"resolved_entity_ids": [ent] if ent else [],
                        "source_record_ids": [eid],
                        "canonical_curve_ids": [c.get("curve_id") for c in crv],
                        "full_kg_ids": ["exp::%s" % eid]},
        )
        link("paper::%s" % pid, nid, "reports") if variant == "flat" or not e.get("in_series") \
            else None
        if e.get("in_series"):
            exp_of_series[(pid, e["in_series"])].append((nid, ent))

        if e.get("material"):
            node("mat::%s" % e["material"], "Material", e["material"])
            link(nid, "mat::%s" % e["material"], "deposits")
        for pre in (e.get("precursors") or []):
            node("pre::%s" % pre, "Precursor", pre)
            link(nid, "pre::%s" % pre, "uses_precursor")
        for co in (e.get("coreactants") or []):
            node("cor::%s" % co, "Coreactant", co)
            link(nid, "cor::%s" % co, "uses_coreactant")
        for q in varied:
            node("qk::%s" % q, "QuantityKind", q)
            link(nid, "qk::%s" % q, "varies")
        if meas:
            node("qk::%s" % meas, "QuantityKind", meas)
            link(nid, "qk::%s" % meas, "measures")
        if e.get("process_type"):
            node("proc::%s" % e["process_type"], "ProcessType", e["process_type"])
            link(nid, "proc::%s" % e["process_type"], "process_type")
        if e.get("geometry_class"):
            node("geo::%s" % e["geometry_class"], "GeometryClass", e["geometry_class"])
            link(nid, "geo::%s" % e["geometry_class"], "geometry")

    # ---- experiment series (variant B only) -----------------------------------
    if variant == "series":
        for (pid, sid), pairs in sorted(exp_of_series.items()):
            members = [m for m, _ in pairs]
            ents = [en for _, en in pairs]
            ent = ents[0]
            s = ser_by_entity.get(ent) or {}
            varq = qname(s.get("series_varies")) or qname(
                (exps[0] if False else {}).get("coordinate"))
            snid = node(
                "es::%s" % sid, "ExperimentSeries", s.get("series_name") or sid,
                paper_id=pid, series_id=sid, entity_id=ent,
                series_type=s.get("between_curve_condition") or "sweep",
                varied_quantity=varq, member_count=len(members),
                n_observations=s.get("n_observations"),
                supported_case_count=s.get("supported_case_count"),
                material=s.get("material"),
                measured_quantity=qname(s.get("measurand")),
                provenance={"resolved_series_ids": [s.get("series_id")] if s.get("series_id") else [],
                            "resolved_entity_ids": sorted(set(ents))},
            )
            link("paper::%s" % pid, snid, "reports")
            for m in members:
                link(snid, m, "contains")
            if varq:
                node("qk::%s" % varq, "QuantityKind", varq)
                link(snid, "qk::%s" % varq, "varies")

    # ---- result series ---------------------------------------------------------
    for r in results:
        rid = r.get("result_series_id")
        if not rid:
            continue
        ent = rid
        crv = curves_for(ent, r.get("source_series_id"))
        ds = sorted({(c.get("source") or {}).get("data_source") for c in crv
                     if (c.get("source") or {}).get("data_source")})
        nid = node(
            "rs::%s" % rid, "ResultSeries", rid,
            result_series_id=rid, paper_id=r.get("paper_id"),
            source_figure=r.get("printed_figure_number"), panel=r.get("panel"),
            figure_slug=r.get("figure_slug"),
            x_quantity=r.get("coordinate"), x_unit=r.get("coordinate_unit"),
            y_quantity=r.get("measurand"), y_unit=r.get("measurand_unit"),
            n_points=r.get("n_points"),
            source=(ds[0] if len(ds) == 1 else (ds or ["unknown"])[0] if ds else "unknown"),
            source_kind=r.get("source_kind"),
            representation=r.get("representation"),
            measurement_class=r.get("measurement_class"),
            canonical_curve_ids=[c.get("curve_id") for c in crv],
            provenance={"source_series_id": r.get("source_series_id"),
                        "measurement_event_id": r.get("measurement_event_id"),
                        "physical_case_id": r.get("physical_case_id"),
                        "full_kg_ids": ["ps::%s" % rid]},
        )
        for m in [n for n in nodes.values()
                  if n["ntype"] == "Experiment" and n.get("entity_id") == ent]:
            link(m["id"], nid, "has_result")
        if r.get("measurand"):
            node("qk::%s" % r["measurand"], "QuantityKind", r["measurand"])

    # ---- models: only relations that ALREADY exist -----------------------------
    fnodes = {n["id"]: n for n in (full_kg.get("nodes") or [])}
    for n in fnodes.values():
        if n.get("ntype") == "Model":
            node("model::%s" % n["id"], "Model", n.get("name"),
                 provenance={"full_kg_ids": [n["id"]]})
        elif n.get("ntype") == "ModelFamily":
            node("mf::%s" % n["id"], "ModelFamily", n.get("name"),
                 provenance={"full_kg_ids": [n["id"]]})
    for l in (full_kg.get("links") or []):
        s, t, et = l.get("source"), l.get("target"), l.get("etype")
        if et == "in_model_family":
            link("model::%s" % s, "mf::%s" % t, "in_model_family")
        elif et == "model_consumes":
            q = qname((fnodes.get(t) or {}).get("name"))
            if q and "qk::%s" % q in nodes:
                link("model::%s" % s, "qk::%s" % q, "consumes_quantity")

    counts = Counter(n["ntype"] for n in nodes.values())
    ecounts = Counter(l["etype"] for l in links)
    return {"variant": variant,
            "built_from": "resolved + canonical layers; full KG untouched",
            "note": ("Values are Experiment properties; only quantity CONCEPTS are nodes. "
                     "Provenance ids link back to knowledge_graph_onto.json, resolved "
                     "entities and canonical curves."),
            "counts": dict(counts), "edgeCounts": dict(ecounts),
            "n_nodes": len(nodes), "n_links": len(links),
            "nodes": list(nodes.values()), "links": links}


# --------------------------------------------------------------------------- viewer
VIEWER = r"""<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{--bg:#f7f8fa;--fg:#16181d;--mut:#5b6472;--line:#d9dee5;--card:#fff;--accent:#0f7c8a}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6eaf0;--mut:#98a3b3;--line:#2b323d;--card:#1a1f27;--accent:#4fc3d1}}
*{box-sizing:border-box}
body{margin:0;font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 background:var(--bg);color:var(--fg);display:grid;grid-template-columns:210px 1fr 340px;height:100vh}
h1{font-size:15px;margin:0 0 8px}
aside,#side{padding:12px;overflow:auto;border-right:1px solid var(--line);background:var(--card)}
#side{border-right:0;border-left:1px solid var(--line)}
main{position:relative;overflow:hidden}
svg{width:100%;height:100%;display:block}
.t{display:block;font-size:12px;margin:2px 0}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
input[type=search]{width:100%;padding:5px;border:1px solid var(--line);border-radius:5px;
 background:var(--bg);color:var(--fg)}
#crumb{position:absolute;top:8px;left:10px;font-size:12px;color:var(--mut);z-index:2}
#crumb b{color:var(--fg)}
button{font:inherit;padding:3px 8px;border:1px solid var(--line);border-radius:5px;
 background:var(--bg);color:var(--fg);cursor:pointer}
button:hover{border-color:var(--accent)}
.kv{margin:6px 0}.kv b{display:block;font-size:11px;color:var(--mut);text-transform:uppercase;
 letter-spacing:.04em}
.pill{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:1px 7px;
 margin:2px 3px 0 0;font-size:11.5px;background:var(--bg)}
.hint{color:var(--mut);font-size:11.5px}
table{border-collapse:collapse;width:100%;font-size:11.5px}td{padding:1px 4px;border-bottom:1px solid var(--line)}
code{font-size:11px;word-break:break-all}
circle{cursor:pointer}text{pointer-events:none;font-size:11px;fill:var(--fg)}
</style>
<aside>
 <h1>__TITLE__</h1>
 <input type="search" id="q" placeholder="search nodes…">
 <div id="results" class="hint"></div>
 <p class="hint" style="margin-top:10px">Click a node to focus it and expand its
 neighbours. Use the type filters to hide categories.</p>
 <div id="filters" class="legend"></div>
 <p><button id="whole">show whole graph</button></p>
 <p class="hint" id="stat"></p>
</aside>
<main><div id="crumb"></div><svg id="cv"></svg></main>
<div id="side"><p class="hint">Select a node.</p></div>
<script>
const DATA = __DATA__;
const COLORS = {Paper:'#1565c0',ExperimentSeries:'#6a1b9a',Experiment:'#0f7c8a',
 Material:'#2e7d32',Precursor:'#ad6800',Coreactant:'#b8860b',QuantityKind:'#c2185b',
 ResultSeries:'#546e7a',ProcessType:'#00838f',GeometryClass:'#5d4037',
 Model:'#d84315',ModelFamily:'#8d6e63'};
const byId={}; DATA.nodes.forEach(n=>byId[n.id]=n);
const adj={}; DATA.nodes.forEach(n=>adj[n.id]=[]);
DATA.links.forEach(l=>{adj[l.source].push([l.target,l.etype,'out']);
                       adj[l.target].push([l.source,l.etype,'in']);});
const types=[...new Set(DATA.nodes.map(n=>n.ntype))];
const off=new Set();
const fdiv=document.getElementById('filters');
types.forEach(t=>{const c=DATA.nodes.filter(n=>n.ntype===t).length;
 const l=document.createElement('label'); l.className='t';
 l.innerHTML='<input type=checkbox checked data-t="'+t+'"> <i style="background:'+(COLORS[t]||'#888')+'"></i>'+t+' <span class=hint>('+c+')</span>';
 l.querySelector('input').onchange=e=>{e.target.checked?off.delete(t):off.add(t);draw();};
 fdiv.appendChild(l);});
document.getElementById('stat').textContent=DATA.n_nodes+' nodes · '+DATA.n_links+' edges';

let focus=null, whole=false;
const svg=document.getElementById('cv');
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function neighbours(id){
 const seen=new Set(); const out=[];
 (adj[id]||[]).forEach(([t,et,dir])=>{ if(off.has(byId[t].ntype))return;
  if(seen.has(t))return; seen.add(t); out.push([t,et,dir]);});
 return out;
}
function draw(){
 const W=svg.clientWidth,H=svg.clientHeight; svg.innerHTML='';
 if(whole){drawWhole(W,H);return;}
 if(!focus){ // entry view: papers + materials
  const seeds=DATA.nodes.filter(n=>(n.ntype==='Paper'||n.ntype==='Material')&&!off.has(n.ntype));
  place(seeds.map(n=>n.id),W,H,null); return;
 }
 const ns=neighbours(focus);
 place(ns.map(x=>x[0]),W,H,focus,ns);
}
function node_el(n,x,y,r,label){
 const g=document.createElementNS('http://www.w3.org/2000/svg','g');
 const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
 c.setAttribute('cx',x);c.setAttribute('cy',y);c.setAttribute('r',r);
 c.setAttribute('fill',COLORS[n.ntype]||'#888');c.setAttribute('opacity',.9);
 c.onclick=()=>{focus=n.id;whole=false;select(n.id);draw();};
 const t=document.createElementNS('http://www.w3.org/2000/svg','text');
 t.setAttribute('x',x);t.setAttribute('y',y+r+12);t.setAttribute('text-anchor','middle');
 t.textContent=(label||n.name||n.id).slice(0,26);
 g.appendChild(c);g.appendChild(t);svg.appendChild(g);
}
function place(ids,W,H,center,meta){
 const cx=W/2, cy=H/2;
 if(center){
  const cn=byId[center];
  ids.forEach((id,i)=>{const a=2*Math.PI*i/ids.length, R=Math.min(W,H)*0.34;
   const x=cx+R*Math.cos(a), y=cy+R*Math.sin(a);
   const ln=document.createElementNS('http://www.w3.org/2000/svg','line');
   ln.setAttribute('x1',cx);ln.setAttribute('y1',cy);ln.setAttribute('x2',x);ln.setAttribute('y2',y);
   ln.setAttribute('stroke','var(--line)');svg.appendChild(ln);
   const lt=document.createElementNS('http://www.w3.org/2000/svg','text');
   lt.setAttribute('x',(cx+x)/2);lt.setAttribute('y',(cy+y)/2);lt.setAttribute('text-anchor','middle');
   lt.setAttribute('opacity','.6');lt.textContent=(meta&&meta[i])?meta[i][1]:'';
   svg.appendChild(lt);
   node_el(byId[id],x,y,9);});
  node_el(cn,cx,cy,15);
  document.getElementById('crumb').innerHTML='focus: <b>'+esc(cn.name)+'</b> ('+cn.ntype+
    ') · '+ids.length+' neighbours <button onclick="reset()">reset</button>';
 } else {
  const per=Math.ceil(Math.sqrt(ids.length))||1;
  ids.forEach((id,i)=>{const x=60+(i%per)*(W-120)/Math.max(per-1,1),
   y=50+Math.floor(i/per)*(H-100)/Math.max(Math.ceil(ids.length/per)-1,1);
   node_el(byId[id],x,y,8);});
  document.getElementById('crumb').innerHTML='corpus entry view — Papers and Materials ('+
   ids.length+'). Click one to expand.';
 }
}
function drawWhole(W,H){
 const vis=DATA.nodes.filter(n=>!off.has(n.ntype));
 if(vis.length>700){svg.innerHTML='';
  document.getElementById('crumb').innerHTML='<b>'+vis.length+
   ' nodes</b> — too many to lay out legibly. Filter types first, or explore by clicking. '+
   '<button onclick="whole=false;draw()">back</button>';return;}
 const cx=W/2,cy=H/2,R=Math.min(W,H)*0.42;
 const pos={}; vis.forEach((n,i)=>{const a=2*Math.PI*i/vis.length;
  pos[n.id]=[cx+R*Math.cos(a),cy+R*Math.sin(a)];});
 DATA.links.forEach(l=>{if(!pos[l.source]||!pos[l.target])return;
  const ln=document.createElementNS('http://www.w3.org/2000/svg','line');
  ln.setAttribute('x1',pos[l.source][0]);ln.setAttribute('y1',pos[l.source][1]);
  ln.setAttribute('x2',pos[l.target][0]);ln.setAttribute('y2',pos[l.target][1]);
  ln.setAttribute('stroke','var(--line)');ln.setAttribute('opacity','.45');svg.appendChild(ln);});
 vis.forEach(n=>node_el(n,pos[n.id][0],pos[n.id][1],6,' '));
 document.getElementById('crumb').innerHTML='whole graph ('+vis.length+' nodes) '+
  '<button onclick="whole=false;draw()">back to explorer</button>';
}
function reset(){focus=null;whole=false;draw();}
window.reset=reset;
document.getElementById('whole').onclick=()=>{whole=!whole;draw();};

function row(k,v){return v==null||v===''||(Array.isArray(v)&&!v.length)?'':
 '<div class=kv><b>'+esc(k)+'</b>'+v+'</div>';}
function pills(a){return (a||[]).map(x=>'<span class=pill>'+esc(x)+'</span>').join('');}
function select(id){
 const n=byId[id]; const s=document.getElementById('side'); let h='<h1>'+esc(n.ntype)+'</h1>';
 h+='<div class=kv><b>name</b>'+esc(n.name)+'</div>';
 if(n.ntype==='Experiment'){
  h+=row('paper',esc(n.paper_id))+row('material',pills(n.material))
   +row('process',esc(n.process_type))+row('geometry',esc(n.geometry))
   +row('chemistry','<div class=hint>precursor</div>'+pills(n.precursor)+
        '<div class=hint>coreactant</div>'+pills(n.coreactant));
  const fc=n.fixed_conditions||{}; const ks=Object.keys(fc);
  h+=row('fixed conditions', ks.length?'<table>'+ks.map(k=>'<tr><td>'+esc(k)+
    '</td><td>'+esc(fc[k].value)+' '+esc(fc[k].unit||'')+'</td><td class=hint>'+
    esc(fc[k].source||'')+'</td></tr>').join('')+'</table>':'<span class=hint>none recorded</span>');
  h+=row('varied',pills(n.varied_quantities))+row('measured',pills(n.measured_quantities))
   +row('data source',pills(n.data_source))
   +row('source figure',esc('Fig '+(n.source_figures||[]).join(', ')+(n.panel?(' panel '+n.panel):'')))
   +row('points',esc(n.n_points))
   +row('result series',pills(n.result_series_ids));
  const p=n.provenance||{};
  h+=row('provenance','<div class=hint>resolved entity</div><code>'+esc((p.resolved_entity_ids||[]).join(', '))+
    '</code><div class=hint>source record</div><code>'+esc((p.source_record_ids||[]).join(', '))+
    '</code><div class=hint>canonical curves</div><code>'+esc((p.canonical_curve_ids||[]).join(', '))+'</code>');
 } else if(n.ntype==='ExperimentSeries'){
  h+=row('paper',esc(n.paper_id))+row('series type',esc(n.series_type))
   +row('varied quantity',esc(n.varied_quantity))+row('member experiments',esc(n.member_count))
   +row('observations',esc(n.n_observations))+row('supported cases',esc(n.supported_case_count))
   +row('material',esc(n.material))+row('measured',esc(n.measured_quantity));
  const mem=(adj[n.id]||[]).filter(x=>x[1]==='contains').map(x=>byId[x[0]]);
  const conds={}; mem.forEach(m=>Object.keys(m.fixed_conditions||{}).forEach(k=>{
   (conds[k]=conds[k]||[]).push(m.fixed_conditions[k].value+' '+(m.fixed_conditions[k].unit||''));}));
  h+=row('member conditions',Object.keys(conds).length?'<table>'+Object.keys(conds).map(k=>
   '<tr><td>'+esc(k)+'</td><td class=hint>'+esc([...new Set(conds[k])].join(' · '))+'</td></tr>').join('')+'</table>':'');
  h+=row('result series',esc(mem.reduce((a,m)=>a+(m.result_series_ids||[]).length,0)));
 } else if(n.ntype==='ResultSeries'){
  h+=row('paper',esc(n.paper_id))+row('figure',esc('Fig '+n.source_figure+(n.panel?(' panel '+n.panel):'')))
   +row('x',esc(n.x_quantity)+' '+esc(n.x_unit||''))+row('y',esc(n.y_quantity)+' '+esc(n.y_unit||''))
   +row('points',esc(n.n_points))+row('source',esc(n.source))
   +row('representation',esc(n.representation))
   +row('canonical curves','<code>'+esc((n.canonical_curve_ids||[]).join(', '))+'</code>')
   +row('provenance','<code>'+esc(JSON.stringify(n.provenance))+'</code>');
 } else {
  const nb=(adj[n.id]||[]);
  const c={}; nb.forEach(([t,et])=>{c[et]=(c[et]||0)+1;});
  h+=row('connections','<table>'+Object.keys(c).map(k=>'<tr><td>'+esc(k)+'</td><td>'+c[k]+'</td></tr>').join('')+'</table>');
  h+='<p class=hint>Click the node in the canvas to expand these.</p>';
 }
 s.innerHTML=h;
}
document.getElementById('q').addEventListener('input',e=>{
 const v=e.target.value.toLowerCase(); const r=document.getElementById('results');
 if(v.length<2){r.textContent='';return;}
 const hits=DATA.nodes.filter(n=>(n.name||'').toLowerCase().includes(v)).slice(0,25);
 r.innerHTML=hits.map(n=>'<div class=t><a href="#" data-id="'+n.id+'">'+esc(n.ntype)+': '+
   esc(n.name).slice(0,40)+'</a></div>').join('')||'<span class=hint>no match</span>';
 r.querySelectorAll('a').forEach(a=>a.onclick=ev=>{ev.preventDefault();
  focus=a.dataset.id;whole=false;select(focus);draw();});});
window.addEventListener('resize',draw); draw();
</script>
"""


def write_viewer(path, title, data):
    slim = {"n_nodes": data["n_nodes"], "n_links": data["n_links"],
            "nodes": data["nodes"], "links": data["links"]}
    path.write_text(VIEWER.replace("__TITLE__", title)
                    .replace("__DATA__", json.dumps(slim)))




# ------------------------------------------------------------------ comparison
#: three papers with genuinely rich experimental structure (most series, then most
#: experiments) -- not trivial single-figure cases
COMPARE_PAPERS = ["10.1021_acs.chemmater.2c01154", "10.1116_6.0002436",
                  "10.1002_pssa.201532305"]
COMPARE_MATERIAL = "Al2O3"

FULL_INTERNAL = ["ConditionAssertion", "RawQuantityValue", "CanonicalQuantityValue",
                 "TransformationExecution", "ContextBinding", "Curve", "PlotSeries",
                 "Figure", "Condition", "Dependent", "Independent"]


def _esc(x):
    return html.escape(str(x if x is not None else ""))


def _traverse(g, paper):
    """What a reader actually walks: paper -> (series ->) experiments -> results."""
    N = {n["id"]: n for n in g["nodes"]}
    out = defaultdict(list)
    for l in g["links"]:
        out[l["source"]].append((l["target"], l["etype"]))
    pid = "paper::%s" % paper
    lines, first = [], out.get(pid, [])
    for tid, et in sorted(first)[:6]:
        n = N[tid]
        lines.append((1, et, n["ntype"], n.get("name"), n))
        for t2, e2 in sorted(out.get(tid, []))[:6]:
            n2 = N[t2]
            if n2["ntype"] in ("Experiment", "ResultSeries", "QuantityKind"):
                lines.append((2, e2, n2["ntype"], n2.get("name"), n2))
                if n2["ntype"] == "Experiment":
                    for t3, e3 in sorted(out.get(t2, []))[:4]:
                        n3 = N[t3]
                        lines.append((3, e3, n3["ntype"], n3.get("name"), n3))
    return lines, len(first)


def write_comparison(full, flat, ser):
    fc, lc, sc = full.get("counts", {}), flat["counts"], ser["counts"]
    types = sorted(set(fc) | set(lc) | set(sc),
                   key=lambda t: (t not in CORE_TYPES, t))
    h = ["""<!doctype html><meta charset="utf-8"><title>Core KG — design comparison</title>
<style>
:root{--bg:#f7f8fa;--fg:#16181d;--mut:#5b6472;--line:#d9dee5;--card:#fff;--accent:#0f7c8a}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6eaf0;--mut:#98a3b3;--line:#2b323d;--card:#1a1f27;--accent:#4fc3d1}}
*{box-sizing:border-box}
body{margin:0 auto;max-width:1220px;padding:30px 22px 70px;background:var(--bg);color:var(--fg);
 font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-variant-numeric:tabular-nums}
h1{font-family:Georgia,serif;font-size:27px;margin:0 0 4px}
h2{font-family:Georgia,serif;font-size:19px;margin:34px 0 8px;border-bottom:2px solid var(--accent);padding-bottom:6px}
h3{font-size:14px;margin:18px 0 6px}
.sub{color:var(--mut);max-width:80ch}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th,td{border:1px solid var(--line);padding:4px 9px;text-align:left}
th{background:var(--card)}
tr.core td{background:rgba(15,124,138,.07)}
tr.internal td{color:var(--mut)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;
 overflow-x:auto;font-size:12px;line-height:1.45}
.hint{color:var(--mut);font-size:12.5px}
.big{font-size:22px;font-weight:700}
a{color:var(--accent)}
iframe{width:100%;height:460px;border:1px solid var(--line);border-radius:8px;background:var(--card)}
</style>
<h1>Core scientific KG — two designs, same corpus</h1>
<p class="sub">Both graphs are abstractions over the identical validated corpus
(32 papers, 833 canonical curves, 851 experiments). The existing full graph
<code>knowledge_graph_onto.json</code> is unchanged and remains the audit/provenance
graph. Nothing here decides which design wins.</p>"""]

    h.append("<h2>Node counts by type</h2>")
    h.append('<p class="hint">Highlighted rows are the core scientific types. The greyed '
             "rows are the internal/provenance types the core graphs deliberately do not "
             "expose as peer nodes — they remain in the full graph.</p>")
    h.append("<table><tr><th>type</th><th>full</th><th>flat-core</th><th>series-core</th></tr>")
    for t in types:
        cls = "core" if t in CORE_TYPES else ("internal" if t in FULL_INTERNAL else "")
        h.append("<tr class='%s'><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (cls, _esc(t), fc.get(t, "—"), lc.get(t, "—"), sc.get(t, "—")))
    h.append("<tr><th>TOTAL NODES</th><th>%d</th><th>%d</th><th>%d</th></tr>"
             % (len(full.get("nodes") or []), flat["n_nodes"], ser["n_nodes"]))
    h.append("<tr><th>TOTAL EDGES</th><th>%d</th><th>%d</th><th>%d</th></tr>"
             % (len(full.get("links") or []), flat["n_links"], ser["n_links"]))
    h.append("</table>")

    h.append("<h2>Edge counts</h2><table><tr><th>relation</th><th>flat-core</th>"
             "<th>series-core</th></tr>")
    for k in sorted(set(flat["edgeCounts"]) | set(ser["edgeCounts"])):
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (_esc(k), flat["edgeCounts"].get(k, "—"), ser["edgeCounts"].get(k, "—")))
    h.append("</table>")

    h.append("<h2>Same three papers, both models</h2>")
    h.append('<p class="hint">Chosen for experimental richness (most resolved sweeps, then '
             "most experiments), not for being easy.</p>")
    for paper in COMPARE_PAPERS:
        h.append("<h3>%s</h3><div class=two>" % _esc(paper))
        for g, label in ((flat, "A · flat"), (ser, "B · series")):
            lines, n_first = _traverse(g, paper)
            txt = "\n".join("%s%s %s: %s" % ("  " * (d - 1), "--%s-->" % et, nt,
                                              (nm or "")[:52]) for d, et, nt, nm, _ in lines)
            h.append("<div class=card><b>%s</b> <span class=hint>— %d direct children of "
                     "Paper</span><pre>%s</pre></div>" % (label, n_first, _esc(txt) or "—"))
        h.append("</div>")

    h.append("<h2>Material traversal — %s</h2>" % _esc(COMPARE_MATERIAL))
    for g, label in ((flat, "A · flat"), (ser, "B · series")):
        N = {n["id"]: n for n in g["nodes"]}
        mid = "mat::%s" % COMPARE_MATERIAL
        exps = [N[l["source"]] for l in g["links"]
                if l["target"] == mid and l["etype"] == "deposits"]
        papers_ = sorted({e["paper_id"] for e in exps})
        h.append("<p><b>%s</b>: %d experiments deposit %s, across %d papers "
                 "(%s).</p>" % (label, len(exps), _esc(COMPARE_MATERIAL), len(papers_),
                                _esc(", ".join(papers_))))
    h.append('<p class="hint">Identical in both variants: Material is a shared node and '
             "ExperimentSeries sits above Experiment, so it does not change how a material "
             "reaches its experiments.</p>")

    h.append("""<h2>What ExperimentSeries changes</h2>
<p>Variant B adds one node type between Paper and Experiment, built only from
<code>experimental_series_id</code> — which the resolve layer mints solely for a
<code>discrete_experimental_sweep</code>. It is not derived from figure number.</p>
<ul>
<li><b>Grouping is partial by construction.</b> %d of %d experiments belong to a sweep;
the other %d are not forced into singleton series and attach directly to their Paper.</li>
<li><b>Papers get far fewer direct children.</b> A temperature sweep with 8 cases becomes
one child of the Paper instead of eight, which is what makes a paper readable at a glance.</li>
<li><b>The sweep variable becomes explicit.</b> Each series carries
<code>series_type</code>, <code>varied_quantity</code> and <code>member_count</code>, so
"this paper contains a deposition-temperature sweep" is a node property rather than
something inferred by comparing sibling experiments.</li>
<li><b>Cost:</b> +%d nodes and +%d edges over the flat model, and a second hop between
Paper and Experiment.</li>
</ul>""" % (sum(1 for l in ser["links"] if l["etype"] == "contains"),
            sc.get("Experiment", 0),
            sc.get("Experiment", 0) - sum(1 for l in ser["links"] if l["etype"] == "contains"),
            ser["n_nodes"] - flat["n_nodes"], ser["n_links"] - flat["n_links"]))

    h.append("<h2>Live viewers</h2><div class=two>"
             '<div class=card><b>A · flat</b><br><a href="kg_core_flat.html">open '
             "kg_core_flat.html</a><iframe src='kg_core_flat.html'></iframe></div>"
             '<div class=card><b>B · series</b><br><a href="kg_core_series.html">open '
             "kg_core_series.html</a><iframe src='kg_core_series.html'></iframe></div></div>")
    h.append('<p class="hint">Both viewers open on a Paper/Material entry view and expand '
             "on click rather than rendering every node at once.</p>")
    (P.REPORTS / "kg_core_comparison.html").write_text("\n".join(h))
    print("wrote reports/kg_core_comparison.html")


def main():
    full = load_json(FULL_KG, {}) or {}
    papers, exps, series, results, curves = collect()
    flat = build("flat", papers, exps, series, results, curves, full)
    ser = build("series", papers, exps, series, results, curves, full)
    OUT_FLAT.write_text(json.dumps(flat, indent=1))
    OUT_SERIES.write_text(json.dumps(ser, indent=1))
    write_viewer(P.REPORTS / "kg_core_flat.html", "Core KG — flat experiment model", flat)
    write_viewer(P.REPORTS / "kg_core_series.html", "Core KG — experiment-series model", ser)
    write_comparison(full, flat, ser)
    print("full   : %d nodes / %d links" % (len(full.get("nodes") or []), len(full.get("links") or [])))
    print("flat   : %d nodes / %d links" % (flat["n_nodes"], flat["n_links"]))
    print("series : %d nodes / %d links" % (ser["n_nodes"], ser["n_links"]))
    return flat, ser, full


if __name__ == "__main__":
    main()
