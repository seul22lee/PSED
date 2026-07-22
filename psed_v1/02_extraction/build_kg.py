"""
build_kg.py  (Phase E — KG viewer, v2 role-aware)
-------------------------------------------------
Render the ontology-grounded knowledge graph as a standalone, interactive
node-link view: kg_viewer.html — built from the resolved experiments so it
carries the full role model.

Meaningful structure:
  · every Experiment links to its PAPER node (from_paper) and its MATERIAL.
  · quantity nodes are DIFFERENTIATED by role — Independent (x / varies),
    Dependent (y / property of interest), Condition (held fixed) — coloured by
    the quantity's dominant role across the corpus.
  · edges are typed by the ACTUAL per-experiment role: varies · measures · controls.

QuantityValues are aggregated into experiment→quantity edges so the backbone
stays legible. Self-contained (CSP-safe, theme-aware). Tracked in the repo.
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).parent
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
# species -> intrinsic properties (molar_mass, molecular_diameter, central_atoms)
SPECIES_PROPS = {}
for _g in ("precursors", "coreactants"):
    for _it in ONTO["individuals"].get(_g, []):
        _p = {k: _it[k] for k in ("molar_mass", "molecular_diameter", "central_atoms") if k in _it}
        for _k in (_it["id"], _it.get("formula"), _it.get("full_name")):
            if _k:
                SPECIES_PROPS[str(_k)] = _p


def main():
    exps = []
    for d in sorted((ROOT / "output").glob("*/resolved/experiments.json")):
        pid = d.parent.parent.name
        for i, e in enumerate(json.loads(d.read_text())):
            e["_pid"], e["_id"] = pid, f"{pid}:{i}"
            exps.append(e)

    # dominant role per quantity (across the corpus) -> node type
    role = defaultdict(Counter)
    for e in exps:
        iv = e.get("coordinate")
        if iv: role[iv]["Independent"] += 1
        poi = (e.get("measurand") or {}).get("quantity")
        if poi: role[poi]["Dependent"] += 1
        for c in e.get("controlled") or []:
            q = c.get("quantity")
            if q and q != iv: role[q]["Condition"] += 1
    qtype = {q: cc.most_common(1)[0][0] for q, cc in role.items()}

    nodes, links = {}, []
    def node(nid, ntype, label, **extra):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, **extra}
        return nodes[nid]
    def link(s, t, etype):
        if s in nodes and t in nodes: links.append({"s": s, "t": t, "e": etype})

    for e in exps:
        eid = "e::" + e["_id"]
        reacts = e.get("reactants") or []
        cyc = " · ".join(f"{r['label']}={r.get('species') or r.get('role')}" for r in reacts) or None
        cg = e.get("carrier_gas") or {}
        carrier_str = (cg["species"] + (f" ({cg['flow_sccm']} sccm)" if cg.get("flow_sccm") else "")) if cg.get("species") else None
        node(eid, "Experiment", e.get("exp_id") or e["_id"],
             series=e.get("series_name"),
             relevance=e.get("relevance"), granularity=e.get("granularity"),
             poi=(e.get("measurand") or {}).get("quantity"), paper=e["_pid"],
             material=e.get("material"), cycle=e.get("cycle_sequence"), reactants=cyc,
             carrier=carrier_str, ready=bool(e.get("analysis_ready")))
        if cg.get("species"):                   # carrier/background gas (its own node type)
            node("ca::" + cg["species"], "Carrier", cg["species"], **SPECIES_PROPS.get(cg["species"], {}))
            links.append({"s": eid, "t": "ca::" + cg["species"], "e": "carrier_gas"})
        node("p::" + e["_pid"], "Paper", e["_pid"])
        link(eid, "p::" + e["_pid"], "from_paper")
        if e.get("material"):
            node("m::" + e["material"], "Material", e["material"]); link(eid, "m::" + e["material"], "deposits")
        for r in reacts:                        # precursor / coreactant / carrier from species
            sp, role, lab = r.get("species"), r.get("role"), r.get("label")
            if not sp:
                continue
            if role == "coreactant":
                node("co::" + sp, "Coreactant", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "co::" + sp, "e": "with_coreactant", "reactant": lab})
            elif role == "carrier":
                node("ca::" + sp, "Carrier", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "ca::" + sp, "e": "carrier_gas", "reactant": lab})
            else:
                node("pre::" + sp, "Precursor", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "pre::" + sp, "e": "uses_precursor", "reactant": lab})
        # role-typed quantity edges
        iv = e.get("coordinate")
        if iv:
            node("q::" + iv, qtype.get(iv, "Condition"), iv); link(eid, "q::" + iv, "varies")
        poi = (e.get("measurand") or {}).get("quantity")
        if poi:
            node("q::" + poi, qtype.get(poi, "Dependent"), poi); link(eid, "q::" + poi, "measures")
        for c in e.get("controlled") or []:
            q = c.get("quantity")
            if q and q != iv:
                node("q::" + q, qtype.get(q, "Condition"), q); link(eid, "q::" + q, "controls")

    # ---- ONTOLOGY LAYER: quantity↔quantity relations from the ontology ----
    # (shows that e.g. normalized_thickness & film_thickness are related, via a
    #  shared Family node + a transform edge, plus specializes / same_as)
    present_q = {nid[3:] for nid in nodes if nid.startswith("q::")}
    QK = {q["id"]: q for q in ONTO["quantity_kinds"]}
    qr = ONTO.get("quantity_relations", {})
    for fam, spec in (qr.get("families") or {}).items():
        members = [m for m in spec.get("members", []) if m in present_q]
        if len(members) >= 1:
            fn = "fam::" + fam
            node(fn, "Family", fam, canonical=spec.get("canonical"))
            for m in members:
                link("q::" + m, fn, "in_family")
    for cat, members in (qr.get("categories") or {}).items():        # semantic categories
        ms = [m for m in members if m in present_q]
        if ms:
            cn = "cat::" + cat
            node(cn, "Category", cat)
            for m in ms:
                link("q::" + m, cn, "in_category")
    for t in qr.get("transforms", []) or []:
        if t.get("from") in present_q and t.get("to") in present_q:
            links.append({"s": "q::" + t["from"], "t": "q::" + t["to"], "e": "transforms_to",
                          "bridge": t.get("bridge")})
    for qid in present_q:
        q = QK.get(qid, {})
        if q.get("specializes") in present_q:
            links.append({"s": "q::" + qid, "t": "q::" + q["specializes"], "e": "specializes"})
        if q.get("same_as") in present_q:
            links.append({"s": "q::" + qid, "t": "q::" + q["same_as"], "e": "same_as"})

    # ---- MODEL LAYER: kinetic/transport MODELS as ontology objects ----
    # each Model links to its family, the quantities it consumes (shared with the
    # experiments that measure them), the paper it comes from, and related models.
    fams = ONTO.get("model_families", {}) or {}
    models = ONTO.get("models", []) or []
    model_ids = {m["id"] for m in models}
    for fid, spec in fams.items():
        node("mfam::" + fid, "ModelFamily", spec.get("name", fid), base=spec.get("base"))
    for m in models:
        mid = "mdl::" + m["id"]
        node(mid, "Model", m.get("name", m["id"]),
             branch=m.get("branch"), predicts=", ".join(m.get("predicts", []) or [])[:120],
             paper=(m.get("reference") or {}).get("ref_tag"),
             equations=len(m.get("equations", []) or []),
             implemented_by=m.get("implemented_by"))
        if m.get("family"):
            link(mid, "mfam::" + m["family"], "in_model_family")
        for inp in m.get("inputs", []) or []:                 # model consumes a quantity
            q = inp.get("quantity")
            if q in present_q:
                link(mid, "q::" + q, "model_consumes")
        ref = (m.get("reference") or {}).get("ref_tag")
        if ref and ("p::" + ref) in nodes:                    # model ← its paper
            link(mid, "p::" + ref, "model_from_paper")
        for rel in ([m.get("related_to")] if isinstance(m.get("related_to"), str) else (m.get("related_to") or [])) \
                + (m.get("shares_base_kinetics_with") or []):
            if rel in model_ids:
                links.append({"s": mid, "t": "mdl::" + rel, "e": "model_related"})

    # dedup identical edges, compute degree
    seen, uniq = set(), []
    for l in links:
        k = (l["s"], l["t"], l["e"])
        if k not in seen: seen.add(k); uniq.append(l)
    links = uniq
    deg = defaultdict(int)
    for l in links: deg[l["s"]] += 1; deg[l["t"]] += 1
    for n in nodes.values(): n["deg"] = deg[n["id"]]

    counts = Counter(n["type"] for n in nodes.values())
    data = {"nodes": list(nodes.values()), "links": links, "counts": dict(counts),
            "edgeCounts": dict(Counter(l["e"] for l in links)),
            "papers": sorted({e["_pid"] for e in exps}),
            "materials": sorted({e["material"] for e in exps if e.get("material")}),
            "relevances": sorted({e.get("relevance") for e in exps if e.get("relevance")})}
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    (ROOT / "kg_viewer.html").write_text(html)
    print(f"wrote kg_viewer.html  ({len(html)//1024} KB)  {len(nodes)} nodes, {len(links)} edges")
    print("   node types:", dict(counts))
    print("   edge types:", data["edgeCounts"])


TEMPLATE = r"""<title>ALD Knowledge Graph</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--Independent:#0f9bd8;--Dependent:#eda100;--Condition:#9aa0aa;--Precursor:#e34948;--Coreactant:#e87ba4;--Carrier:#7a8b99;--e-carrier_gas:#7a8b99;--Family:#7d5ba6;--Model:#d81b60;--ModelFamily:#8e24aa;--Category:#c65d3b;--e-in_family:#7d5ba6;--e-in_category:#c65d3b;--e-transforms_to:#0f9bd8;--e-specializes:#1baf7a;--e-same_as:#9aa0aa;
 --e-varies:#0f9bd8;--e-measures:#eda100;--e-controls:#c3c7cd;--e-from_paper:#4a3aa7;--e-deposits:#1baf7a;--e-uses_precursor:#e34948;--e-with_coreactant:#e87ba4;--e-in_model_family:#8e24aa;--e-model_consumes:#d81b60;--e-model_from_paper:#7d5ba6;--e-model_related:#d81b60;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--Independent:#33a9dd;--Dependent:#c98500;--Condition:#6b7079;--Precursor:#e66767;--Coreactant:#d55181;--Carrier:#8b9aa8;--e-carrier_gas:#8b9aa8;--Family:#a98cd6;--Model:#ec407a;--ModelFamily:#ab47bc;--Category:#e07a54;--e-in_family:#a98cd6;--e-in_category:#e07a54;--e-transforms_to:#33a9dd;--e-specializes:#199e70;--e-same_as:#767c86;
 --e-varies:#33a9dd;--e-measures:#c98500;--e-controls:#3a3d44;--e-from_paper:#9085e9;--e-deposits:#199e70;--e-uses_precursor:#e66767;--e-with_coreactant:#d55181;--e-in_model_family:#ab47bc;--e-model_consumes:#ec407a;--e-model_from_paper:#a98cd6;--e-model_related:#ec407a;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--Independent:#33a9dd;--Dependent:#c98500;--Condition:#6b7079;--Precursor:#e66767;--Coreactant:#d55181;--Carrier:#8b9aa8;--e-carrier_gas:#8b9aa8;--Family:#a98cd6;--Model:#ec407a;--ModelFamily:#ab47bc;--Category:#e07a54;--e-in_family:#a98cd6;--e-in_category:#e07a54;--e-transforms_to:#33a9dd;--e-specializes:#199e70;--e-same_as:#767c86;
 --e-varies:#33a9dd;--e-measures:#c98500;--e-controls:#3a3d44;--e-from_paper:#9085e9;--e-deposits:#199e70;--e-uses_precursor:#e66767;--e-with_coreactant:#d55181;--e-in_model_family:#ab47bc;--e-model_consumes:#ec407a;--e-model_from_paper:#a98cd6;--e-model_related:#ec407a;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--Independent:#0f9bd8;--Dependent:#eda100;--Condition:#9aa0aa;--Precursor:#e34948;--Coreactant:#e87ba4;--Carrier:#7a8b99;--e-carrier_gas:#7a8b99;--Family:#7d5ba6;--Model:#d81b60;--ModelFamily:#8e24aa;--Category:#c65d3b;--e-in_family:#7d5ba6;--e-in_category:#c65d3b;--e-transforms_to:#0f9bd8;--e-specializes:#1baf7a;--e-same_as:#9aa0aa;
 --e-varies:#0f9bd8;--e-measures:#eda100;--e-controls:#c3c7cd;--e-from_paper:#4a3aa7;--e-deposits:#1baf7a;--e-uses_precursor:#e34948;--e-with_coreactant:#e87ba4;--e-in_model_family:#8e24aa;--e-model_consumes:#d81b60;--e-model_from_paper:#7d5ba6;--e-model_related:#d81b60;}
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
details.ms{position:relative}
details.ms>summary{list-style:none;cursor:pointer;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:5px 10px;font-size:12px;color:var(--ink2)}
details.ms>summary::-webkit-details-marker{display:none}
details.ms[open]>summary{border-color:var(--accent,#2a78d6)}
.mspanel{position:absolute;z-index:20;top:110%;left:0;min-width:150px;max-height:260px;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:6px;box-shadow:0 8px 24px rgba(0,0,0,.14)}
.mspanel label{display:flex;align-items:center;gap:7px;padding:4px 6px;font-size:12px;border-radius:6px;cursor:pointer}
.mspanel label:hover{background:var(--line2)}
input[type=search]{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:5px 9px;color:var(--ink);font-size:12px;min-width:150px}
button.mini{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:5px 10px;color:var(--accent,#2a78d6);font-size:12px;cursor:pointer}
.stage{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:6px}
svg{display:block;width:100%;height:660px;touch-action:none;cursor:grab}
svg.drag{cursor:grabbing}
.info{position:absolute;top:12px;right:12px;width:262px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 13px;font-size:12.5px;display:none;max-height:88%;overflow:auto}
.info h3{margin:0 0 6px;font-size:13.5px}.info .k{color:var(--ink3);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.info .row{margin:5px 0}.info .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.ichip{font-size:11px;padding:1px 7px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.hint{font-size:12px;color:var(--ink3);margin-top:8px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--ink2);margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:5px}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · ontology-grounded KG</div>
<h1>Knowledge graph</h1>
<div class="sub" id="sub"></div>
<div class="bar">
  <span class="grp">filter</span>
  <details class="ms" id="msPaper"><summary>paper: all</summary><div class="mspanel"></div></details>
  <details class="ms" id="msMat"><summary>material: all</summary><div class="mspanel"></div></details>
  <details class="ms" id="msRel"><summary>relevance: all</summary><div class="mspanel"></div></details>
  <input type="search" id="search" placeholder="search label…">
  <button class="mini" onclick="relayout()">re-layout</button>
  <button class="mini" onclick="resetAll()">reset</button>
</div>
<div class="bar" id="legNodes"><span class="grp">node types</span></div>
<div class="bar" id="legEdges"><span class="grp">edge types</span></div>
<div class="stage"><svg id="svg"></svg><div class="info" id="info"></div></div>
<div class="hint"><b>drag a node</b> to move it · <b>drag the background</b> to pan · <b>scroll</b> to zoom · <b>click a node</b> to inspect &amp; highlight its neighbourhood · filters are multi-select (tick several).</div>
</div>
<script>
const D=/*DATA*/;
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const NS="http://www.w3.org/2000/svg",el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a||{})e.setAttribute(k,a[k]);return e;};
const VBW=1280,VBH=660;
const NT=["Paper","Experiment","Material","Independent","Dependent","Condition","Category","Family","Model","ModelFamily","Precursor","Coreactant","Carrier"].filter(t=>D.counts[t]);
const ET=["from_paper","deposits","varies","measures","controls","in_category","in_family","transforms_to","specializes","same_as","in_model_family","model_consumes","model_from_paper","model_related","uses_precursor","with_coreactant","carrier_gas"].filter(t=>D.edgeCounts[t]);
const offN=new Set(["Family","Precursor","Coreactant"].filter(t=>D.counts[t]));
const offE=new Set(["controls","in_family","uses_precursor","with_coreactant"].filter(t=>D.edgeCounts[t]));
const selPaper=new Set(), selMat=new Set(), selRel=new Set();   // empty = all
document.getElementById("sub").textContent=`${D.nodes.length} nodes · ${D.links.length} edges · `+NT.map(t=>`${D.counts[t]} ${t}`).join(" · ");

// ---- multi-select dropdowns ----
function fillMS(id,opts,set,label){
  const d=document.getElementById(id),panel=d.querySelector(".mspanel"),sum=d.querySelector("summary");
  panel.innerHTML=opts.map(o=>`<label><input type="checkbox" value="${o}">${o}</label>`).join("");
  panel.querySelectorAll("input").forEach(cb=>cb.onchange=()=>{cb.checked?set.add(cb.value):set.delete(cb.value);
    sum.textContent=`${label}: ${set.size?[...set].join(", ").slice(0,22)+(set.size>1?` (${set.size})`:""):"all"}`;frame();});
}
fillMS("msPaper",D.papers,selPaper,"paper");
fillMS("msMat",D.materials,selMat,"material");
fillMS("msRel",D.relevances,selRel,"relevance");
// close dropdowns on outside click
document.addEventListener("click",e=>{document.querySelectorAll("details.ms[open]").forEach(d=>{if(!d.contains(e.target))d.open=false;});});

// ---- node-type + edge-type chips ----
document.getElementById("legNodes").insertAdjacentHTML("beforeend",NT.map(t=>`<span class="chip ${offN.has(t)?"off":""}" data-t="${t}" onclick="togN('${t}')"><span class="dot" style="background:var(--${t})"></span>${t} <span style="color:var(--ink3)">${D.counts[t]}</span></span>`).join(""));
document.getElementById("legEdges").insertAdjacentHTML("beforeend",ET.map(t=>`<span class="chip ${offE.has(t)?"off":""}" data-e="${t}" onclick="togE('${t}')"><span class="edg" style="border-color:var(--e-${t})"></span>${t} <span style="color:var(--ink3)">${D.edgeCounts[t]}</span></span>`).join(""));
window.togN=t=>{offN.has(t)?offN.delete(t):offN.add(t);document.querySelector(`[data-t="${t}"]`).classList.toggle("off");frame();};
window.togE=t=>{offE.has(t)?offE.delete(t):offE.add(t);document.querySelector(`[data-e="${t}"]`).classList.toggle("off");frame();};

// ---- graph state ----
const idx=Object.fromEntries(D.nodes.map(n=>[n.id,n]));
const nbr=Object.fromEntries(D.nodes.map(n=>[n.id,new Set()]));
D.links.forEach(l=>{if(nbr[l.s]&&nbr[l.t]){nbr[l.s].add(l.t);nbr[l.t].add(l.s);}});
const ring={Paper:0,Category:55,Family:90,ModelFamily:70,Model:100,Material:120,Dependent:180,Independent:180,Condition:250,Precursor:300,Coreactant:330,Carrier:345,Experiment:440};
function seed(){D.nodes.forEach((n,i)=>{const r=ring[n.type]??380,a=i*2.399;n.x=VBW/2+r*Math.cos(a);n.y=VBH/2+r*Math.sin(a);n.vx=0;n.vy=0;});}
function layout(iters){for(let it=0;it<iters;it++){
  for(let i=0;i<D.nodes.length;i++)for(let j=i+1;j<D.nodes.length;j++){const a=D.nodes[i],b=D.nodes[j];
    let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1,d=Math.sqrt(d2),f=3000/d2;a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
  D.links.forEach(l=>{const a=idx[l.s],b=idx[l.t];if(!a||!b)return;let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-70)*0.016;
    a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;});
  D.nodes.forEach(n=>{if(n.fx==null){n.vx+=(VBW/2-n.x)*0.002;n.vy+=(VBH/2-n.y)*0.002;n.x+=(n.vx*=0.82);n.y+=(n.vy*=0.82);}});}}
function fit(pad){pad=pad||58;   // fit the DENSE CORE to the viewBox, clamp outliers to the edge,
  // so the readable bulk fills the window instead of being crushed by a few far-flung nodes.
  const xs=D.nodes.map(n=>n.x).sort((a,b)=>a-b),ys=D.nodes.map(n=>n.y).sort((a,b)=>a-b);
  const q=(v,p)=>{const k=(v.length-1)*p,f=Math.floor(k);return v[f]+(v[Math.min(f+1,v.length-1)]-v[f])*(k-f);};
  const x0=q(xs,0.05),x1=q(xs,0.95),y0=q(ys,0.05),y1=q(ys,0.95);
  const w=x1-x0||1,h=y1-y0||1,s=Math.min((VBW-2*pad)/w,(VBH-2*pad)/h);
  const ox=(VBW-2*pad-w*s)/2,oy=(VBH-2*pad-h*s)/2;
  D.nodes.forEach(n=>{const x=pad+(n.x-x0)*s+ox,y=pad+(n.y-y0)*s+oy;
    n.x=Math.min(Math.max(x,pad),VBW-pad);n.y=Math.min(Math.max(y,pad),VBH-pad);});}
seed();layout(280);fit();

// ---- persistent DOM ----
const svg=el("svg",{viewBox:`0 0 ${VBW} ${VBH}`});svg.id="svg";
document.getElementById("svg").replaceWith(svg);
const view=el("g");svg.appendChild(view);
const gL=el("g");const gN=el("g");view.appendChild(gL);view.appendChild(gN);
D.links.forEach(l=>{l._el=el("line",{"stroke-linecap":"round"});gL.appendChild(l._el);});
D.nodes.forEach(n=>{n._g=el("g");n._c=el("circle",{stroke:CSS("--surface"),"stroke-width":1.3});
  n._t=el("text",{"font-size":11,"pointer-events":"none"});n._t.textContent=n.label.length>22?n.label.slice(0,21)+"…":n.label;
  n._g.appendChild(n._c);n._g.appendChild(n._t);gN.appendChild(n._g);
  n._c.addEventListener("pointerdown",ev=>startDrag(ev,n));});

let tx=0,ty=0,scale=1,sel=null,q="";
function updateView(){view.setAttribute("transform",`translate(${tx} ${ty}) scale(${scale})`);}
function visibleNodes(){
  const vis=new Set();
  D.nodes.forEach(n=>{if(n.type!=="Experiment")return;if(offN.has("Experiment"))return;
    if(selPaper.size&&!selPaper.has(n.paper))return;
    if(selRel.size&&!selRel.has(n.relevance))return;
    if(selMat.size&&!selMat.has(n.material))return;
    vis.add(n.id);});
  // entity nodes visible if linked to a visible experiment (and type on)
  D.nodes.forEach(n=>{if(n.type==="Experiment"||offN.has(n.type))return;
    for(const m of nbr[n.id])if(vis.has(m)){vis.add(n.id);break;}});
  return vis;
}
function frame(){
  const vis=visibleNodes();
  const hi=sel, ql=q.toLowerCase();
  D.links.forEach(l=>{const a=idx[l.s],b=idx[l.t],on=vis.has(l.s)&&vis.has(l.t)&&!offE.has(l.e);
    l._el.style.display=on?"":"none";if(!on)return;
    const near=hi&&(l.s===hi||l.t===hi),dim=hi&&!near;
    l._el.setAttribute("x1",a.x);l._el.setAttribute("y1",a.y);l._el.setAttribute("x2",b.x);l._el.setAttribute("y2",b.y);
    l._el.setAttribute("stroke",CSS("--e-"+l.e)||CSS("--line"));
    l._el.setAttribute("stroke-width",near?2:(l.e==="from_paper"||l.e==="deposits"?1.1:.7));
    l._el.setAttribute("opacity",dim?.05:(l.e==="controls"?.28:.6));});
  D.nodes.forEach(n=>{const on=vis.has(n.id);n._g.style.display=on?"":"none";if(!on)return;
    const r=n.type==="Experiment"?4.4:n.type==="Paper"?Math.min(11+n.deg*0.25,22):Math.min(7+n.deg*0.5,19);
    const near=!hi||n.id===hi||nbr[hi].has(n.id);
    const match=!ql||n.label.toLowerCase().includes(ql);
    n._c.setAttribute("cx",n.x);n._c.setAttribute("cy",n.y);n._c.setAttribute("r",r);
    n._c.setAttribute("fill",CSS("--"+n.type));
    n._c.setAttribute("opacity",(near&&match)?1:.13);
    n._c.setAttribute("stroke-width",n.id===hi?2.4:1.3);
    n._c.setAttribute("stroke",n.id===hi?CSS("--ink"):CSS("--surface"));
    n._c.style.cursor="grab";
    const showT=(n.type==="Paper"||(n.type!=="Experiment"&&n.deg>=2)||(ql&&match));
    n._t.style.display=showT?"":"none";
    if(showT){n._t.setAttribute("x",n.x+r+3);n._t.setAttribute("y",n.y+3.5);
      n._t.setAttribute("fill",CSS("--ink2"));n._t.setAttribute("font-weight",n.type==="Paper"?600:400);
      n._t.setAttribute("opacity",(near&&match)?1:.13);}});
}
updateView();frame();

// ---- interaction ----
function toVB(ev){const r=svg.getBoundingClientRect();return {x:(ev.clientX-r.left)/r.width*VBW,y:(ev.clientY-r.top)/r.height*VBH};}
function toWorld(vb){return {x:(vb.x-tx)/scale,y:(vb.y-ty)/scale};}
let drag=null,pan=null,moved=0;
function startDrag(ev,n){ev.stopPropagation();ev.preventDefault();
  const w=toWorld(toVB(ev));drag={n,ox:w.x-n.x,oy:w.y-n.y};moved=0;svg.classList.add("drag");
  n.fx=n.x;n.fy=n.y;}     // pin during drag
svg.addEventListener("pointerdown",ev=>{if(drag)return;pan={vb:toVB(ev)};moved=0;svg.classList.add("drag");});
svg.addEventListener("pointermove",ev=>{
  if(drag){const w=toWorld(toVB(ev));drag.n.x=w.x-drag.ox;drag.n.y=w.y-drag.oy;drag.n.fx=drag.n.x;drag.n.fy=drag.n.y;moved++;frame();}
  else if(pan){const vb=toVB(ev);tx+=vb.x-pan.vb.x;ty+=vb.y-pan.vb.y;pan.vb=vb;moved++;updateView();}});
function endDrag(ev){
  if(drag){if(moved<3){sel=(sel===drag.n.id?null:drag.n.id);showInfo(sel?drag.n:null);frame();}
    drag.n.fx=null;drag.n.fy=null;drag=null;}
  pan=null;svg.classList.remove("drag");}
svg.addEventListener("pointerup",endDrag);svg.addEventListener("pointerleave",endDrag);
svg.addEventListener("click",ev=>{if(ev.target===svg||ev.target===view){sel=null;showInfo(null);frame();}});
svg.addEventListener("wheel",ev=>{ev.preventDefault();const vb=toVB(ev),w=toWorld(vb),f=ev.deltaY<0?1.12:0.89;
  scale=Math.max(.2,Math.min(6,scale*f));tx=vb.x-w.x*scale;ty=vb.y-w.y*scale;updateView();},{passive:false});
document.getElementById("search").addEventListener("input",e=>{q=e.target.value;frame();});

function showInfo(n){const box=document.getElementById("info");
  if(!n){box.style.display="none";return;}box.style.display="block";
  const ls=D.links.filter(l=>l.s===n.id||l.t===n.id);const byRel={};
  ls.forEach(l=>{const o=idx[l.s===n.id?l.t:l.s];if(!o)return;
    let lab=o.label;
    if(l.e==="transforms_to"&&l.bridge)lab=`${o.label} (via ${l.bridge})`;
    else if(l.reactant)lab=`${l.reactant}: ${o.label}`;
    (byRel[l.e]=byRel[l.e]||new Set()).add(lab);});
  box.innerHTML=`<h3 style="color:var(--${n.type})">${n.label}</h3><div class="k">${n.type}</div>
    ${n.reactants?`<div class="row"><span class="k">reactants (cycle ${n.cycle||""})</span> ${n.reactants}</div>`:""}
    ${n.carrier?`<div class="row"><span class="k">carrier gas</span> ${n.carrier}</div>`:""}
    ${n.series?`<div class="row"><span class="k">series</span> ${n.series}</div>`:""}
    ${n.canonical?`<div class="row"><span class="k">canonical basis</span> ${n.canonical}</div>`:""}
    ${n.molar_mass?`<div class="row"><span class="k">molar mass</span> ${n.molar_mass} g/mol</div>`:""}
    ${n.molecular_diameter?`<div class="row"><span class="k">molecular diameter</span> ${n.molecular_diameter} pm</div>`:""}
    ${n.central_atoms?`<div class="row"><span class="k">metal atoms / molecule</span> ${n.central_atoms}</div>`:""}
    ${n.material?`<div class="row"><span class="k">material</span> ${n.material}</div>`:""}
    ${n.relevance?`<div class="row"><span class="k">relevance</span> ${n.relevance}${n.ready===false?" · ⚠ quarantined":""}</div>`:""}
    ${n.poi?`<div class="row"><span class="k">measurand</span> ${n.poi}</div>`:""}
    ${n.branch?`<div class="row"><span class="k">family branch</span> ${n.branch}</div>`:""}
    ${n.predicts?`<div class="row"><span class="k">predicts</span> ${n.predicts}</div>`:""}
    ${n.equations?`<div class="row"><span class="k">equations</span> ${n.equations}</div>`:""}
    ${n.paper?`<div class="row"><span class="k">from paper</span> ${n.paper}</div>`:""}
    ${n.implemented_by?`<div class="row"><span class="k">implemented by</span> ${n.implemented_by}</div>`:""}
    ${n.base?`<div class="row"><span class="k">base</span> ${n.base}</div>`:""}
    <div class="row"><span class="k">links (${ls.length})</span></div>
    ${Object.entries(byRel).map(([e,s])=>`<div class="row"><span style="color:var(--e-${e},var(--ink2))">${e}</span> <span style="color:var(--ink3)">(${s.size})</span><div class="chips">${[...s].slice(0,10).map(x=>`<span class="ichip">${x}</span>`).join("")}${s.size>10?`<span class="ichip">+${s.size-10}</span>`:""}</div></div>`).join("")}`;
}
window.relayout=()=>{seed();layout(280);fit();tx=0;ty=0;scale=1;updateView();frame();};
window.resetAll=()=>{selPaper.clear();selMat.clear();selRel.clear();q="";document.getElementById("search").value="";
  document.querySelectorAll(".mspanel input").forEach(cb=>cb.checked=false);
  document.querySelectorAll("details.ms summary").forEach(su=>su.textContent=su.textContent.split(":")[0]+": all");
  frame();};
</script>
"""

if __name__ == "__main__":
    main()
