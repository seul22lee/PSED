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

# resolve(): without it every path here is relative to the caller's cwd, so the
# script only ran from inside 02_extraction/ and failed from the repo root.
ROOT = Path(__file__).resolve().parent
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())


def val_source(c):
    if c.get("from_label"): return "label"
    if c.get("derived"): return "derived"
    return "text"


import re
def fig_display(figure_id, caption=""):
    """Real figure number from the CAPTION ('Figure 2. ...' -> 'Fig. 2'), NOT the
    internal extraction index ('figure-011'). Appends the panel letter from the id
    suffix ('figure-017a' -> '(a)'). Falls back to the id number if no caption."""
    m = re.match(r"\s*(?:figure|fig)\.?\s*([0-9]+)", str(caption or ""), re.I)
    if m:
        num = m.group(1)
    else:
        mm = re.search(r"(\d+)", str(figure_id or ""))
        num = mm.group(1) if mm else "?"
    pm = re.search(r"\d+([a-z])$", str(figure_id or ""), re.I)
    return f"Fig. {num}{'(' + pm.group(1) + ')' if pm else ''}"


def axis_unit(label):
    """parse a trailing '(unit)'/'[unit]' off an axis label, e.g. 'Location x (µm)' -> 'µm'."""
    if not label: return None
    m = re.search(r"[\(\[]\s*([^)\]]{1,8})\s*[\)\]]\s*$", str(label))
    if m and re.match(r"^[a-zA-Zµμ°%/·0-9.\-^ ]+$", m.group(1).strip()):
        return m.group(1).strip()
    return None


def main():
    # imputation provenance from the recipe store (build_recipes.py must run first):
    # exp_id -> {"q::r": {source, value, ci, donors, n_eff}} for kb/model-filled fields
    FILLED = {}
    rp = ROOT / "output" / "recipes.json"
    if rp.exists():
        for r in json.loads(rp.read_text()):
            ps = r.get("param_sources") or {}
            FILLED[r.get("exp_id")] = {k: m for k, m in ps.items()
                                       if isinstance(m, dict) and m.get("source") in ("kb", "model")}
    exps = []
    for d in sorted((ROOT / "output").glob("*/resolved/experiments.json")):
        pid = d.parent.parent.name
        for i, e in enumerate(json.loads(d.read_text())):
            conds = [{"q": c["quantity"], "v": c.get("value"), "u": c.get("unit"),
                      "r": c.get("of_reactant"), "src": val_source(c)}
                     for c in (e.get("controlled") or []) if c.get("quantity")]
            measures = [dd["quantity"] for dd in (e.get("dependent") or []) if dd.get("quantity")]
            poi = e.get("measurand") or {}
            yunit = poi.get("unit")
            # x-axis unit: from the coordinate condition, else parsed from the plot x-label
            xunit = next((c.get("unit") for c in (e.get("controlled") or [])
                          if c.get("quantity") == e.get("coordinate")), None) or axis_unit(e.get("x_label"))
            pts = e.get("points") or None
            exps.append({
                "id": f"{pid}:{i}", "eid": e.get("exp_id") or f"{pid}:{i}",
                "pid": pid, "series": e.get("series_name") or "—",
                "material": e.get("material") or "—", "structure": e.get("structure") or "—",
                "process": e.get("process_type") or "—", "gran": e.get("granularity"),
                "precursors": e.get("precursors") or [], "coreactants": e.get("coreactants") or [],
                "reactants": e.get("reactants") or [], "cyseq": e.get("cycle_sequence"),
                "carrier": e.get("carrier_gas"),
                "rel": e.get("relevance"), "model": bool(e.get("is_model_result")),
                "varies": e.get("varies") or [], "measures": measures, "conds": conds,
                "filled": FILLED.get(e.get("exp_id"), {}),
                "points": pts if e.get("granularity") == "profile" else None,
                "xax": e.get("x_label"), "yax": e.get("y_label"),
                "poi": poi.get("quantity"), "yunit": yunit, "xunit": xunit,
                "sig": e.get("comparability_signature"),
                "ckey": e.get("comparability_key"),
                "mfam": e.get("measurand_family"), "cfam": e.get("coordinate_family"),
                "bridges": e.get("bridges") or [],
                "indep": e.get("coordinate"),
                "fig": (e.get("provenance") or {}).get("figure_id"),
                "figd": fig_display((e.get("provenance") or {}).get("figure_id"),
                                    (e.get("provenance") or {}).get("caption")),
                "ready": bool(e.get("analysis_ready")),
                "issues": e.get("issues") or [],
                "repro": e.get("reproduced_from"),
                "pair": bool(e.get("has_model_pair")),
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

    qr = ONTO.get("quantity_relations", {})
    families = {f: spec.get("canonical") for f, spec in (qr.get("families") or {}).items()}
    transforms = qr.get("transforms", [])
    data = {"exps": exps, "materials": materials, "quantities": quantities,
            "ranges": ranges, "spread": spread[:60],
            "families": families, "transforms": transforms,
            "recipe_roles": {q["id"]: q.get("recipe_role") for q in ONTO["quantity_kinds"]},
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
button.mini{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:2px 8px;color:var(--accent);font-size:11.5px;cursor:pointer;margin:0 2px}
.tablewrap{border:1px solid var(--line);border-radius:10px;overflow:visible}
details.ms{position:relative}
details.ms>summary{list-style:none;cursor:pointer;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:3px 7px;font-size:11px;color:var(--ink2);white-space:nowrap}
details.ms>summary::-webkit-details-marker{display:none}
details.ms[open]>summary{border-color:var(--accent)}
.mspanel{position:absolute;z-index:30;top:108%;left:0;min-width:130px;max-height:240px;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:5px;box-shadow:0 8px 24px rgba(0,0,0,.16)}
.mspanel label{display:flex;align-items:center;gap:6px;padding:3px 5px;font-size:11.5px;border-radius:5px;cursor:pointer;text-transform:none;letter-spacing:0}
.mspanel label:hover{background:var(--line2)}
.mspanel a{color:var(--accent);cursor:pointer;font-size:11px}
table{width:100%;border-collapse:collapse;font-size:12px}
thead tr:first-child th{position:sticky;top:0;z-index:3}
th{background:var(--panel);text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);
 color:var(--ink3);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;cursor:pointer;white-space:nowrap}
.frow th{position:sticky;top:30px;z-index:2;padding:3px 6px;text-transform:none;letter-spacing:0;cursor:auto}
.frow select,.frow input{width:100%;min-width:70px;font-size:11px;padding:3px 5px;border-radius:6px}
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
  <button onclick="tab('sim',this)">Similarity</button>
  <button onclick="tab('graph',this)">Knowledge graph</button>
  <button onclick="tab('uncert',this)">Uncertainty</button>
</div>

<div id="explore" class="pane">
  <div class="toolbar">
    <span class="count" id="count"></span>
    <button class="mini" onclick="selectAllFiltered()">check all (filtered)</button>
    <button class="mini" onclick="clearSel()">clear</button>
    <button class="mini" onclick="resetFilters()">reset filters</button>
    <span id="selcount" style="color:var(--ink3)"></span>
    <span style="margin-left:auto"></span>
    <label class="f">quantity present<select id="fq"></select></label>
    <label class="f" id="rangewrap" style="display:none">range<span style="display:flex;gap:4px">
      <input id="rmin" type="text" style="width:60px" placeholder="min" oninput="render()">
      <input id="rmax" type="text" style="width:60px" placeholder="max" oninput="render()"></span></label>
  </div>
  <div class="hint">click a column title to sort · use the boxes under each title to filter · tick rows to add to Compare</div>
  <div class="tablewrap"><table id="tbl"><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
</div>

<div id="compare" class="pane" style="display:none">
  <div class="selbar" id="selbar"></div>
  <div class="card" style="margin-bottom:14px">
    <div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">aligned conditions <span style="color:var(--ink3);font-weight:400">(colour = value source; <span style="color:var(--accent);font-weight:600">kb</span>/<span style="color:var(--c3);font-weight:600">model</span> = imputed — hover for CI &amp; donor experiments)</span></div>
    <div class="svgwrap"><table id="cmptbl" class="mono" style="font-size:11.5px"></table></div>
    <div class="legend"><span><i class="dot" style="background:var(--c2)"></i>label</span>
      <span><i class="dot" style="background:var(--ink2)"></i>text</span>
      <span><i class="dot" style="background:var(--c1)"></i>chart</span>
      <span><i class="dot" style="background:var(--c3)"></i>derived</span></div>
  </div>
  <div class="card">
    <div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">overlay of profile curves <span style="color:var(--ink3);font-weight:400">(brought to a common canonical basis where possible)</span></div>
    <div class="svgwrap"><div id="overlay"></div></div>
    <div class="legend" id="ovlegend"></div>
  </div>
</div>

<div id="sim" class="pane" style="display:none">
  <div class="hint">Similarity over your <b>selected</b> experiments (tick rows in Explore; falls back to the filtered set, capped). The headline is the <b>condition → curve relationship</b>: each dot is a pair — if the field is consistent, similar setups (right) give similar curves (top). <b>Off-diagonal points are the findings</b>: high condition + low curve = inconsistency; low condition + high curve = insensitivity. Click any dot (or matrix cell) for the breakdown, overlaid curves, and conditions.</div>
  <div class="cmpgrid">
    <div class="card"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">condition → curve relationship <span id="simcorr" style="color:var(--ink3);font-weight:400"></span></div>
      <div class="svgwrap"><div id="simscatter"></div></div></div>
    <div class="card"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px" id="simpairhdr">pair breakdown</div>
      <div id="simpair" style="font-size:12.5px;color:var(--ink3)">click a dot or matrix cell…</div></div>
  </div>
  <div class="card" id="simdetail" style="margin-top:14px;display:none">
    <div class="cmpgrid">
      <div><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">overlaid curves (canonical basis)</div>
        <div class="svgwrap"><div id="simplot"></div></div>
        <div class="legend" id="simplotleg"></div></div>
      <div><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">conditions <span style="color:var(--ink3);font-weight:400">(green = shared)</span></div>
        <div class="svgwrap"><div id="simcond"></div></div></div>
    </div>
  </div>
  <div class="card" style="margin-top:14px"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">similarity matrix <span style="color:var(--ink3);font-weight:400">(composite — for lookup/ranking; click a cell)</span></div>
    <div class="svgwrap"><div id="simmat"></div></div>
    <div class="legend"><span>low</span><span class="dot" style="background:color-mix(in srgb,var(--c2) 15%,var(--panel))"></span><span class="dot" style="background:color-mix(in srgb,var(--c2) 55%,var(--panel))"></span><span class="dot" style="background:var(--c2)"></span><span>high</span></div></div>
  <div class="card" style="margin-top:14px"><div class="mono" style="font-size:12px;font-weight:600;margin-bottom:8px">clusters (composite ≥ 0.75)</div><div id="simclusters" style="font-size:12.5px"></div></div>
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

// --- per-column filters ---
const canon=e=>D.families[e.mfam]||null;
const POIS=[...new Set(E.map(e=>e.poi).filter(Boolean))].sort();
const fq=document.getElementById("fq");
fq.innerHTML='<option value="">any quantity</option>'+D.quantities.map(q=>`<option>${q}</option>`).join("");
fq.addEventListener("change",()=>{document.getElementById("rangewrap").style.display=(fq.value in D.ranges)?"":"none";render();});

// column model: k=field, l=title, f=filter type, opts=select options, cell=render fn
const COLS=[
  {k:"eid",  l:"id",       f:"text", cell:e=>`<span class="mono" style="font-weight:600">${e.eid}</span>`},
  {k:"figd", l:"figure",   f:"text"},
  {k:"pid",  l:"paper",    f:"select", opts:D.papers},
  {k:"series",l:"series",  f:"text"},
  {k:"material",l:"material",f:"select", opts:D.materials},
  {k:"poi",  l:"measurand → canonical", f:"select", opts:POIS,
   cell:e=>`<span class="mono" style="color:var(--c3)">${e.poi||"—"}</span>${canon(e)&&canon(e)!==e.poi?`<span class="mono" style="color:var(--ink3)"> → ${canon(e)}</span>`:""}`},
  {k:"gran", l:"granularity",f:"select", opts:["profile","sweep_point","single","sweep_nopoints"],
   cell:e=>`<span class="tag">${e.gran}</span>`},
  {k:"rel",  l:"relevance",f:"select", opts:["experimental","model","background"],
   cell:e=>`<span class="pill ${e.rel}">${e.rel}</span>`},
  {k:"status",l:"status",  f:"select", opts:["ready","quarantined"],
   cell:e=>e.ready?`<span class="pill experimental">ready</span>`:`<span class="pill background" title="${e.issues.join(', ')}">⚠ ${e.issues.join(', ')}</span>`},
  {k:"nq",   l:"#cond",    f:"", cell:e=>`<span class="mono">${e.conds.length}</span>`},
];
const colF={status:new Set(["ready"])};            // select filters are SETS (multi); default: ready
const cellVal=(e,k)=>k==="nq"?e.conds.length:k==="status"?(e.ready?"ready":"quarantined"):(e[k]??"");
function rows(){
  let out=E.filter(e=>COLS.every(c=>{
    const fv=colF[c.k]; if(!fv) return true;
    if(c.f==="select") return !fv.size || fv.has(String(cellVal(e,c.k)));   // multi-select set
    return !fv || String(cellVal(e,c.k)).toLowerCase().includes(fv.toLowerCase());
  }));
  const q=fq.value,rmin=parseFloat(document.getElementById("rmin").value),rmax=parseFloat(document.getElementById("rmax").value);
  if(q) out=out.filter(e=>e.conds.some(c=>c.q===q)||e.measures.includes(q)||e.varies.includes(q));
  if(q&&(!isNaN(rmin)||!isNaN(rmax))) out=out.filter(e=>{const v=cget(e,q);return v!=null&&(isNaN(rmin)||v>=rmin)&&(isNaN(rmax)||v<=rmax);});
  const kf=e=>cellVal(e,sort.k);
  out.sort((a,b)=>(kf(a)>kf(b)?1:kf(a)<kf(b)?-1:0)*sort.dir);
  return out;
}
function renderHead(){                              // built once + on sort (persists filter controls)
  const sortRow="<tr><th></th>"+COLS.map(c=>`<th onclick="setSort('${c.k}')" title="sort">${c.l}${sort.k===c.k?(sort.dir>0?" ▲":" ▼"):""}</th>`).join("")+"</tr>";
  const filtRow="<tr class='frow'><th></th>"+COLS.map(c=>{
    if(c.f==="select"){const set=colF[c.k]||new Set();
      return `<th><details class="ms"><summary>${set.size?set.size+" sel":"all"}</summary><div class="mspanel">`
        +`<div style="padding:2px 5px"><a onclick="clearF('${c.k}')">clear</a></div>`
        +c.opts.map(o=>`<label><input type="checkbox" value="${o}" ${set.has(String(o))?"checked":""} onchange="toggleF('${c.k}',this)">${o}</label>`).join("")
        +`</div></details></th>`;}
    if(c.f==="text") return `<th><input type="text" value="${colF[c.k]||""}" placeholder="filter…" oninput="setF('${c.k}',this.value)"></th>`;
    return "<th></th>";}).join("")+"</tr>";
  document.getElementById("thead").innerHTML=sortRow+filtRow;
}
function render(){                                  // tbody + count only (keeps filter focus)
  const rs=rows();document.getElementById("count").textContent=rs.length+" / "+E.length;
  document.getElementById("tbody").innerHTML=rs.slice(0,500).map(e=>"<tr>"
    +`<td><input class="chk" type="checkbox" ${sel.has(e.id)?"checked":""} onchange="togSel('${e.id}',this.checked)"></td>`
    +COLS.map(c=>`<td>${c.cell?c.cell(e):`<span class="mono">${e[c.k]??"—"}</span>`}</td>`).join("")
    +"</tr>").join("");
  drawGraph(rs);
}
window.setF=(k,v)=>{colF[k]=v;render();};              // text filters
window.toggleF=(k,cb)=>{const set=colF[k]||(colF[k]=new Set());cb.checked?set.add(cb.value):set.delete(cb.value);
  cb.closest("details").querySelector("summary").textContent=set.size?set.size+" sel":"all";render();};
window.clearF=(k)=>{colF[k]=new Set();renderHead();render();};
window.resetFilters=()=>{for(const k in colF)delete colF[k];fq.value="";document.getElementById("rmin").value="";document.getElementById("rmax").value="";document.getElementById("rangewrap").style.display="none";renderHead();render();};
document.addEventListener("click",e=>{document.querySelectorAll("#explore details.ms[open]").forEach(d=>{if(!d.contains(e.target))d.open=false;});});
window.setSort=k=>{sort.dir=(sort.k===k?-sort.dir:1);sort.k=k;renderHead();render();};
const CAP=12;
window.togSel=(id,on)=>{on?(sel.size<CAP&&sel.add(id)):sel.delete(id);selCount();drawCompare();render();};
window.selectAllFiltered=()=>{rows().slice(0,CAP).forEach(e=>sel.add(e.id));selCount();drawCompare();render();};
window.clearSel=()=>{sel.clear();selCount();drawCompare();render();};
function selCount(){document.getElementById("selcount").textContent=sel.size?` · ${sel.size}/${CAP} selected`:"";}
window.render=render;

// ---- compare + overlay ----
function drawCompare(){
  const items=[...sel].map(id=>E.find(e=>e.id===id));
  document.getElementById("selbar").innerHTML=items.length?("comparing: "+items.map(e=>`<span class="tag">${e.eid} · ${e.material} ${e.series}</span>`).join(" ")):"tick rows in Explore to compare (up to 12).";
  const cols=["c1","c2","c3","c4","c5","c6"].map(c=>CSS("--"+c));
  const CC=i=>cols[i%cols.length];
  // key conditions by (quantity, reactant) so molecular_mass/pulse_time for A vs B
  // are distinct labelled rows (reactant A = precursor, B = coreactant)
  // rows come from BOTH extracted conditions and recipe-filled (imputed) fields,
  // so a value that no selected experiment measured still shows — with provenance
  const keys=[...new Set(items.flatMap(e=>[...e.conds.map(c=>c.q+"::"+(c.r||"")),
                                           ...Object.keys(e.filled||{})]))];
  const src2col={label:"var(--c2)",text:"var(--ink2)",chart:"var(--c1)",derived:"var(--c3)"};
  const fnum=v=>{if(v==null)return "·";const a=Math.abs(v);
    return (a>=1e4||(a<0.001&&a>0))?v.toExponential(1):a<1?(+v.toFixed(4)+""):a<100?(+v.toFixed(2)+""):(+v.toFixed(0)+"");};
  // a filled (imputed / model-default) cell: value + source badge + hover provenance
  function fillCell(m){
    if(m.source==="kb"){const ci=m.ci||[];let tip="imputed ≈ "+fnum(m.value);
      if(ci[0]!=null)tip+="  |  68% CI "+fnum(ci[0])+"–"+fnum(ci[1]);
      if(m.n_eff)tip+="  |  n_eff "+m.n_eff+" of "+(m.n_donors||"?");
      if(m.donors&&m.donors.length)tip+="  |  from "+m.donors.slice(0,3).map(d=>d.exp_id+"~"+d.sim).join(", ");
      return `<span title="${tip}" style="color:var(--ink3)">${fnum(m.value)} <span style="font-size:9px;padding:1px 4px;border-radius:5px;background:rgba(42,120,214,.16);color:var(--accent);font-weight:600">kb</span></span>`;}
    return `<span title="model default ${fnum(m.value)}" style="color:var(--ink3)">${fnum(m.value)} <span style="font-size:9px;padding:1px 4px;border-radius:5px;background:rgba(237,161,0,.18);color:var(--c3);font-weight:600">model</span></span>`;
  }
  // group condition rows by recipe_role: control_setting = the RECIPE; others are
  // structure (sample) / model_parameter (a fit) / species_property / derived / observable
  const RR=D.recipe_roles||{};
  const ROLE_ORDER=["control_setting","structure","species_property","model_parameter","derived","observable","other"];
  const ROLE_LABEL={control_setting:"recipe (control settings)",structure:"structure (sample)",species_property:"species property",model_parameter:"model parameter (fit)",derived:"derived",observable:"observable",other:"other"};
  const ROLE_COL={control_setting:"--c2",structure:"--c1",species_property:"--c4",model_parameter:"--c5",derived:"--c3",observable:"--ink2",other:"--ink3"};
  const byRole={}; keys.forEach(k=>{const r=RR[k.split("::")[0]]||"other";(byRole[r]=byRole[r]||[]).push(k);});
  let h="<tr><td></td>"+items.map((e,i)=>`<td style="color:${CC(i)};font-weight:600" title="${e.series}">${e.eid}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">measurand</td>'+items.map(e=>`<td style="font-weight:600">${e.poi||"—"}${e.yunit&&e.yunit!=="1"?" ("+e.yunit+")":""}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">reactants (cycle)</td>'+items.map(e=>`<td style="font-size:11px">${(e.reactants||[]).map(r=>`<b style="color:var(--c4)">${r.label}</b>=${r.species||"?"} <span style="color:var(--ink3)">(${(r.role||"").slice(0,4)})</span>`).join(" · ")||"—"}${e.cyseq?` <span style="color:var(--ink3)">seq ${e.cyseq}</span>`:""}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">carrier gas</td>'+items.map(e=>`<td style="font-size:11px">${e.carrier?`${e.carrier.species}${e.carrier.flow_sccm?` <span style="color:var(--ink3)">${e.carrier.flow_sccm} sccm</span>`:""}`:"—"}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">family (measurand ~ coord)</td>'+items.map(e=>`<td style="font-size:10.5px;color:var(--c1)">${e.ckey||"—"}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">exact signature</td>'+items.map(e=>`<td style="font-size:10.5px">${e.sig||"—"}</td>`).join("")+"</tr>";
  h+='<tr><td style="color:var(--ink3)">bridges present</td>'+items.map(e=>`<td style="font-size:10px">${(e.bridges||[]).filter(b=>b.present).map(b=>b.bridge).join(", ")||"—"}</td>`).join("")+"</tr>";
  for(const role of ROLE_ORDER){const ks=(byRole[role]||[]).sort();if(!ks.length)continue;
    h+=`<tr><td colspan="${items.length+1}" style="padding-top:8px;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(${ROLE_COL[role]})">${ROLE_LABEL[role]}</td></tr>`;
    for(const k of ks){const kq=k.split("::")[0],kr=k.split("::")[1];h+=`<tr><td style="color:var(--ink3)">${kq}${kr?` <span style="color:var(--c4)">(${kr})</span>`:""}</td>`+items.map(e=>{
      const c=e.conds.find(c=>c.q===kq&&(c.r||"")===kr);
      if(c)return `<td style="color:${src2col[c.src]||'var(--ink2)'}">${(c.v??"·")+" "+(c.u||"")}</td>`;
      const f=(e.filled||{})[k];
      if(f)return `<td>${fillCell(f)}</td>`;
      return `<td style="color:var(--line)">—</td>`;}).join("")+"</tr>";}}
  document.getElementById("cmptbl").innerHTML=h;
  // overlay — SMALL MULTIPLES: one panel per MEASURAND (its own real, named Y-axis
  // + units), all sharing ONE canonical X-axis so you read across at the same
  // position. Within a panel, curves are brought to the family canonical via
  // ontology transforms (unit-aware, e.g. µm↔nm) when the bridge is present.
  const profs=items.map((e,i)=>({e,i})).filter(o=>o.e.points&&o.e.points.length);
  const clean=o=>o.e.points.slice().filter(p=>p[0]!=null&&p[1]!=null).sort((a,b)=>a[0]-b[0]);
  const FAM=D.families,TRANS=D.transforms;
  const LENFAC={nm:1,"µm":1e3,"μm":1e3,um:1e3,mm:1e6,cm:1e7,m:1e9,"å":.1,"Å":.1};
  const toBase=(v,u)=>{const f=LENFAC[u];return f?v*f:v;};
  const QUNIT={};E.forEach(e=>{(e.conds||[]).forEach(c=>{if(c.q&&!(c.q in QUNIT))QUNIT[c.q]=c.u;});if(e.poi&&!(e.poi in QUNIT))QUNIT[e.poi]=e.yunit;});
  const uLbl=q=>{const u=QUNIT[q];return u&&u!=="1"?u:"";};
  function plan(e,q,fam,srcUnit){                     // how to bring q -> family canonical
    const canon=fam?FAM[fam]:null;
    if(!q||!fam||!canon) return {op:"norm",tier:4,canon:q,reason:"no family"};
    if(q===canon) return {op:"none",tier:0,canon};
    const t=TRANS.find(t=>t.from===q&&t.to===canon);
    if(t){const c=e.conds.find(c=>c.q===t.bridge),bv=c&&typeof c.v==="number"?c.v:null;
      if(bv!=null&&bv!==0) return {op:t.op,val:bv,vunit:c.u,sunit:srcUnit,bridge:t.bridge,tier:2,canon};
      return {op:"norm",tier:3,canon,reason:"missing "+t.bridge};}
    return {op:"norm",tier:4,canon,reason:"no transform→"+canon};
  }
  const applyv=(v,p)=> p.op==="divide"?toBase(v,p.sunit)/toBase(p.val,p.vunit) : p.op==="multiply"?v*p.val : v;
  const fmt=v=>{const a=Math.abs(v);return a===0?"0":(a<0.001||a>=1e4)?v.toExponential(1):a<1?v.toFixed(3):a<100?v.toFixed(1):v.toFixed(0);};
  const TTv={0:"Tier 0 · identical",1:"Tier 1 · unit-convert",2:"Tier 2 · aligned",3:"Tier 3 · normalized (missing bridge)",4:"Tier 4 · shape only"};
  const W=940,L=70,R=22,OV=document.getElementById("overlay");OV.innerHTML="";
  if(!profs.length){const s=el("svg",{width:"100%",viewBox:`0 0 ${W} 180`});
    s.appendChild(tx(W/2,90,"select profile experiments to overlay curves",{fill:CSS("--ink3"),"font-size":13,"text-anchor":"middle"}));
    OV.appendChild(s);document.getElementById("ovlegend").innerHTML="";return;}
  // shared X — bring every coordinate to its canonical (aligns ALL panels on one x)
  const px=profs.map(o=>plan(o.e,o.e.indep,o.e.cfam,o.e.xunit));
  const xNorm=px.some(p=>p.op==="norm");
  const XT=profs.map((o,k)=>clean(o).map(p=>applyv(p[0],px[k])));
  const NX=(v,k)=>{if(!xNorm)return v;const a=XT[k],mn=Math.min(...a),mx=Math.max(...a);return (v-mn)/((mx-mn)||1);};
  const xall=XT.flat(),x0=xNorm?0:Math.min(...xall),x1=xNorm?1:Math.max(...xall);
  const PX=v=>L+((v-x0)/((x1-x0)||1))*(W-L-R);
  const xcanon=(px.find(p=>p.canon)||{}).canon, allC=new Set(profs.map(o=>o.e.cfam)).size===1;
  const xu=xNorm?"":uLbl(xcanon);
  const xlab=(allC?(xcanon||"coordinate"):"coordinate")+(xNorm?" · normalized 0–1":(xu?` (${xu})`:" (ratio)"));
  // ONE PANEL PER MEASURAND FAMILY (never a single 'mixed' axis)
  const groups={};profs.forEach((o,k)=>{const g=o.e.mfam||o.e.poi||"other";(groups[g]=groups[g]||[]).push(k);});
  const gks=Object.keys(groups);
  const PH=gks.length>1?200:330, GAP=16, TOP=6, XAX=40;
  const totalH=TOP+gks.length*PH+(gks.length-1)*GAP+XAX;
  const s=el("svg",{width:"100%",viewBox:`0 0 ${W} ${totalH}`});
  gks.forEach((gk,gi)=>{
    const idxs=groups[gk];
    const gp=idxs.map(k=>plan(profs[k].e,profs[k].e.poi,profs[k].e.mfam,profs[k].e.yunit));
    const yNorm=gp.some(p=>p.op==="norm");
    const YT=idxs.map((k,j)=>clean(profs[k]).map(p=>applyv(p[1],gp[j])));
    const NY=(v,j)=>{if(!yNorm)return v;const a=YT[j],mn=Math.min(...a),mx=Math.max(...a);return (v-mn)/((mx-mn)||1);};
    const yall=YT.flat(),y0=yNorm?0:Math.min(...yall),y1=yNorm?1:Math.max(...yall);
    const canonY=(gp.find(p=>p.canon)||{}).canon||gk, yu=yNorm?"":uLbl(canonY);
    const tier=Math.max(...gp.map(p=>p.tier),...idxs.map(k=>px[k].tier));
    const pTop=TOP+gi*(PH+GAP), plotT=pTop+22, plotB=pTop+PH-8, isLast=gi===gks.length-1;
    const PY=v=>plotB-((v-y0)/((y1-y0)||1))*(plotB-plotT);
    const ylabel=canonY+(yNorm?" · norm 0–1":(yu?` (${yu})`:" (ratio)"));
    s.appendChild(tx(L,pTop+13,ylabel,{fill:CSS("--ink"),"font-size":12.5,"font-weight":600}));
    const tcol=tier<=2?"--c2":tier===3?"--c3":"--c5";
    s.appendChild(tx(W-R,pTop+13,TTv[tier],{fill:CSS(tcol),"font-size":10,"text-anchor":"end"}));
    for(let i=0;i<=4;i++){const f=i/4,yv=y0+f*(y1-y0),yy=plotB-f*(plotB-plotT);
      s.appendChild(el("line",{x1:L,y1:yy,x2:W-R,y2:yy,stroke:CSS("--line2")}));
      s.appendChild(tx(L-7,yy+3,fmt(yv),{fill:CSS("--ink3"),"font-size":9,"text-anchor":"end"}));}
    for(let i=0;i<=5;i++){const f=i/5,xv=x0+f*(x1-x0),xx=L+f*(W-L-R);
      s.appendChild(el("line",{x1:xx,y1:plotT,x2:xx,y2:plotB,stroke:CSS("--line2")}));
      if(isLast)s.appendChild(tx(xx,plotB+14,fmt(xv),{fill:CSS("--ink3"),"font-size":9,"text-anchor":"middle"}));}
    s.appendChild(el("line",{x1:L,y1:plotT,x2:L,y2:plotB,stroke:CSS("--line")}));
    s.appendChild(el("line",{x1:L,y1:plotB,x2:W-R,y2:plotB,stroke:CSS("--line")}));
    idxs.forEach((k,j)=>{const xt=XT[k],yt=YT[j],col=cols[profs[k].i%cols.length];
      const d=xt.map((xv,m)=>(m?"L":"M")+PX(NX(xv,k)).toFixed(1)+" "+PY(NY(yt[m],j)).toFixed(1)).join(" ");
      s.appendChild(el("path",{d,fill:"none",stroke:col,"stroke-width":2}));
      xt.forEach((xv,m)=>s.appendChild(el("circle",{cx:PX(NX(xv,k)),cy:PY(NY(yt[m],j)),r:2,fill:col})));});
    if(isLast)s.appendChild(tx((L+W-R)/2,plotB+30,xlab,{fill:CSS("--ink2"),"font-size":11.5,"text-anchor":"middle"}));
  });
  OV.appendChild(s);
  document.getElementById("ovlegend").innerHTML=profs.map(o=>`<span><i class="dot" style="background:${cols[o.i%cols.length]}"></i>${o.e.eid} ${o.e.series} <span style="color:var(--ink3)">${o.e.poi||""}</span></span>`).join("");
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
  if(id==="graph")paintGraph();if(id==="compare")drawCompare();if(id==="sim")drawSimilarity();};

// ================= SIMILARITY ENGINE (mirrors similarity.py) =================
const S_SLOT={temperature:"temperature",deposition_temperature:"temperature",pulse_time:"exposure_time",plasma_exposure_time:"exposure_time",exposure:"dose",purge_time:"purge_time",feature_height:"feature_height",feature_width:"feature_width",aspect_ratio:"aspect_ratio",cycle_number:"cycle_number",pore_diameter:"pore_diameter",partial_pressure:"pressure"};
const S_CATW={material:3,process:1.2,structure:.8},S_SETW={precursors:2,coreactants:1.5},
  S_NUMW={temperature:2,exposure_time:1.6,dose:1.4,pressure:1,purge_time:.7,feature_height:1.2,feature_width:.9,aspect_ratio:1.2,cycle_number:.8,pore_diameter:.9};
const S_PRIOR=.5,S_PRIORW=1.5,S_COMPW={condition:.45,curve:.35,derived:.2},S_FAM=D.families,S_TRANS=D.transforms;
const S_LEN={nm:1,"µm":1e3,"μm":1e3,um:1e3,mm:1e6,cm:1e7,m:1e9,"å":.1};const s_base=(v,u)=>{const f=S_LEN[u];return f?v*f:v;};
function s_cfg(e){const num={};(e.conds||[]).forEach(c=>{const s=S_SLOT[c.q];if(s&&typeof c.v==="number"&&c.v>0&&!(s in num))num[s]=c.v;});
  return {material:e.material,process:e.process,structure:e.structure,precursors:new Set(e.precursors||[]),coreactants:new Set(e.coreactants||[]),num};}
const S_SC=(()=>{const v={};E.forEach(e=>{const n=s_cfg(e).num;for(const s in n)(v[s]=v[s]||[]).push(Math.log10(n[s]));});
  const sc={};for(const s in v){const a=v[s].sort((x,y)=>x-y);sc[s]=a.length>=3?Math.max(a[a.length-1-Math.floor(a.length/10)]-a[Math.floor(a.length/10)],.3):1;}return sc;})();
function conditionSim(a,b){const ca=s_cfg(a),cb=s_cfg(b);let ws=0,wsi=0,parts=[];
  const add=(n,w,s)=>{parts.push([n,+s.toFixed(3),w]);ws+=w;wsi+=w*s;};
  for(const k in S_CATW){if(ca[k]&&cb[k]&&ca[k]!=="—"&&cb[k]!=="—")add(k,S_CATW[k],ca[k]===cb[k]?1:0);}
  for(const k in S_SETW){const A=ca[k],B=cb[k];if(A.size&&B.size){const inter=[...A].filter(x=>B.has(x)).length,uni=new Set([...A,...B]).size;add(k,S_SETW[k],inter/uni);}}
  for(const s in ca.num){if(s in cb.num){const d=Math.abs(Math.log10(ca.num[s])-Math.log10(cb.num[s]))/(S_SC[s]||1);add(s,S_NUMW[s]||1,Math.max(0,1-d));}}
  if(ws===0)return {score:null,coverage:0,parts:[]};
  const raw=wsi/ws,adj=(ws*raw+S_PRIORW*S_PRIOR)/(ws+S_PRIORW);
  return {score:+adj.toFixed(3),raw:+raw.toFixed(3),coverage:+ws.toFixed(1),parts:parts.sort((p,q)=>q[2]-p[2])};}
function s_plan(e,q,fam,su){const canon=fam?S_FAM[fam]:null;if(!q||!fam||!canon)return {op:"norm",canon:q};
  if(q===canon)return {op:"none",canon};const t=S_TRANS.find(t=>t.from===q&&t.to===canon);
  if(t){const c=(e.conds||[]).find(c=>c.q===t.bridge);const bv=c&&typeof c.v==="number"?c.v:null;if(bv)return {op:t.op,val:bv,vunit:c.u,sunit:su,canon};}return {op:"norm",canon};}
const s_apply=(v,p)=>p.op==="divide"?s_base(v,p.sunit)/s_base(p.val,p.vunit):p.op==="multiply"?v*p.val:v;
function canonize(e){const pts=(e.points||[]).filter(p=>p[0]!=null&&p[1]!=null).slice().sort((a,b)=>a[0]-b[0]);if(pts.length<3)return null;
  const py=s_plan(e,e.poi,e.mfam,e.yunit),pxp=s_plan(e,e.indep,e.cfam,e.xunit);
  let xs=pts.map(p=>s_apply(p[0],pxp)),ys=pts.map(p=>s_apply(p[1],py));
  if(pxp.op==="norm"){const lo=Math.min(...xs),hi=Math.max(...xs);xs=xs.map(x=>(x-lo)/((hi-lo)||1));}
  if(py.op==="norm"){const lo=Math.min(...ys),hi=Math.max(...ys);ys=ys.map(y=>(y-lo)/((hi-lo)||1));}
  return [xs,ys];}
function s_interp(xs,ys,xq){if(xq<=xs[0])return ys[0];if(xq>=xs[xs.length-1])return ys[ys.length-1];
  for(let i=1;i<xs.length;i++)if(xs[i]>=xq){const t=(xq-xs[i-1])/((xs[i]-xs[i-1])||1);return ys[i-1]+t*(ys[i]-ys[i-1]);}return ys[ys.length-1];}
function curveSim(a,b){if(a.ckey!==b.ckey)return null;const ca=canonize(a),cb=canonize(b);if(!ca||!cb)return null;
  const xa=ca[0],ya=ca[1],xb=cb[0],yb=cb[1];const x0=Math.max(Math.min(...xa),Math.min(...xb)),x1=Math.min(Math.max(...xa),Math.max(...xb));
  const span=Math.max(...xa,...xb)-Math.min(...xa,...xb);if(x1<=x0||span<=0)return {curve_sim:null,overlap:0};
  const N=40,g=[];for(let i=0;i<N;i++)g.push(x0+(x1-x0)*i/(N-1));
  const fa=g.map(x=>s_interp(xa,ya,x)),fb=g.map(x=>s_interp(xb,yb,x));const allv=fa.concat(fb),yr=(Math.max(...allv)-Math.min(...allv))||1;
  const rmse=Math.sqrt(fa.reduce((s,p,i)=>s+(p-fb[i])**2,0)/N),nr=rmse/yr;
  const my=fa.reduce((s,p)=>s+p,0)/N,sst=fa.reduce((s,p)=>s+(p-my)**2,0)||1,ssr=fa.reduce((s,p,i)=>s+(p-fb[i])**2,0);
  return {curve_sim:+Math.exp(-3*nr).toFixed(3),nrmse:+nr.toFixed(3),r2:+(1-ssr/sst).toFixed(3),overlap:+((x1-x0)/span).toFixed(2)};}
function derived(e){const c=canonize(e);if(!c)return null;const xs=c[0],ys=c[1],ymax=Math.max(...ys)||1,half=.5*ymax;let pd=null;
  for(let i=1;i<xs.length;i++){const y0=ys[i-1],y1=ys[i];if((y0-half)*(y1-half)<=0&&y1!==y0){pd=xs[i-1]+(half-y0)*(xs[i]-xs[i-1])/(y1-y0);break;}}
  return {pd50:pd,plateau:ymax,front:ys[0]};}
const s_rel=(a,b)=>(a==null||b==null)?null:Math.max(0,1-Math.abs(a-b)/(((Math.abs(a)+Math.abs(b))/2)||1));
function derivedSim(a,b){const da=derived(a),db=derived(b);if(!da||!db)return null;const o={};
  ["pd50","plateau","front"].forEach(k=>{const s=s_rel(da[k],db[k]);if(s!=null)o[k]=+s.toFixed(3);});return Object.keys(o).length?o:null;}
function composite(a,b){const cond=conditionSim(a,b),cur=curveSim(a,b),der=derivedSim(a,b),comps={};
  if(cond.score!=null)comps.condition=cond.score;if(cur&&cur.curve_sim!=null)comps.curve=cur.curve_sim;
  if(der)comps.derived=+(Object.values(der).reduce((s,v)=>s+v,0)/Object.keys(der).length).toFixed(3);
  if(!Object.keys(comps).length)return null;let ws=0,sc=0;for(const k in comps){ws+=S_COMPW[k];sc+=S_COMPW[k]*comps[k];}
  let quad=null;if("condition"in comps&&"curve"in comps){const hc=comps.condition>=.7,ho=comps.curve>=.7;
    quad=hc&&ho?"reproducible":hc?"inconsistency ⚠":ho?"insensitivity":"trend";}
  return {composite:+(sc/ws).toFixed(3),components:comps,quadrant:quad,cond,cur,der};}
function simItems(){let its=[...sel].map(id=>E.find(e=>e.id===id)).filter(e=>e&&e.points&&e.points.length);
  if(its.length<2)its=rows().filter(e=>e.points&&e.points.length).slice(0,14);return its.slice(0,14);}
function pearson(xs,ys){const n=xs.length;if(n<2)return null;const mx=xs.reduce((a,b)=>a+b,0)/n,my=ys.reduce((a,b)=>a+b,0)/n;
  let sxy=0,sx=0,sy=0;for(let i=0;i<n;i++){sxy+=(xs[i]-mx)*(ys[i]-my);sx+=(xs[i]-mx)**2;sy+=(ys[i]-my)**2;}
  return (sx&&sy)?sxy/Math.sqrt(sx*sy):null;}
function drawScatter(its){
  const box=document.getElementById("simscatter");box.innerHTML="";
  const pts=[];
  for(let i=0;i<its.length;i++)for(let j=i+1;j<its.length;j++){
    const cond=conditionSim(its[i],its[j]),cur=curveSim(its[i],its[j]);
    if(cond.score!=null&&cur&&cur.curve_sim!=null)pts.push({x:cond.score,y:cur.curve_sim,a:its[i],b:its[j]});}
  const B={w:520,h:420,l:56,b:48,t:16,r:16};
  const s=el("svg",{width:"100%",viewBox:`0 0 ${B.w} ${B.h}`});
  if(!pts.length){s.appendChild(tx(B.w/2,B.h/2,"no comparable pairs (need ≥2 profiles in one comparability class)",{fill:CSS("--ink3"),"font-size":11,"text-anchor":"middle"}));
    box.appendChild(s);document.getElementById("simcorr").textContent="";return;}
  const PX=v=>B.l+v*(B.w-B.l-B.r),PY=v=>B.h-B.b-v*(B.h-B.b-B.t),T=0.7;
  // quadrant shading
  const quad=[[T,1,T,1,"--c2",".10"],[T,1,0,T,"--c5",".10"],[0,T,T,1,"--c3",".08"],[0,T,0,T,"--ink3",".05"]];
  quad.forEach(([x0,x1,y0,y1,c,o])=>s.appendChild(el("rect",{x:PX(x0),y:PY(y1),width:PX(x1)-PX(x0),height:PY(y0)-PY(y1),fill:CSS(c),opacity:o})));
  // grid + ticks
  [0,.25,.5,.75,1].forEach(f=>{s.appendChild(el("line",{x1:PX(f),y1:B.t,x2:PX(f),y2:B.h-B.b,stroke:CSS("--line2")}));
    s.appendChild(el("line",{x1:B.l,y1:PY(f),x2:B.w-B.r,y2:PY(f),stroke:CSS("--line2")}));
    s.appendChild(tx(PX(f),B.h-B.b+14,f.toFixed(2),{fill:CSS("--ink3"),"font-size":9,"text-anchor":"middle"}));
    s.appendChild(tx(B.l-6,PY(f)+3,f.toFixed(2),{fill:CSS("--ink3"),"font-size":9,"text-anchor":"end"}));});
  // y=x reference (curves track conditions) + quadrant divider lines
  s.appendChild(el("line",{x1:PX(0),y1:PY(0),x2:PX(1),y2:PY(1),stroke:CSS("--ink3"),"stroke-dasharray":"3 3",opacity:.5}));
  s.appendChild(el("line",{x1:PX(T),y1:B.t,x2:PX(T),y2:B.h-B.b,stroke:CSS("--line"),"stroke-dasharray":"2 2"}));
  s.appendChild(el("line",{x1:B.l,y1:PY(T),x2:B.w-B.r,y2:PY(T),stroke:CSS("--line"),"stroke-dasharray":"2 2"}));
  // corner labels
  s.appendChild(tx(B.w-B.r-4,PY(1)+11,"reproducible",{fill:CSS("--c2"),"font-size":9.5,"text-anchor":"end","font-weight":600}));
  s.appendChild(tx(B.w-B.r-4,PY(0)-4,"inconsistency ⚠",{fill:CSS("--c5"),"font-size":9.5,"text-anchor":"end","font-weight":600}));
  s.appendChild(tx(B.l+4,PY(1)+11,"insensitivity",{fill:CSS("--c3"),"font-size":9.5,"font-weight":600}));
  s.appendChild(tx(B.l+4,PY(0)-4,"trend",{fill:CSS("--ink3"),"font-size":9.5,"font-weight":600}));
  // axis labels
  s.appendChild(tx((B.l+B.w-B.r)/2,B.h-6,"condition similarity →",{fill:CSS("--ink2"),"font-size":11,"text-anchor":"middle"}));
  const mY=(B.t+B.h-B.b)/2;const yl=el("text",{x:13,y:mY,fill:CSS("--ink2"),"font-size":11,"text-anchor":"middle",transform:`rotate(-90 13 ${mY})`});yl.textContent="curve similarity →";s.appendChild(yl);
  // dots (colour by quadrant)
  pts.forEach(p=>{const hc=p.x>=T,ho=p.y>=T;const col=hc&&ho?"--c2":hc?"--c5":ho?"--c3":"--ink3";
    const c=el("circle",{cx:PX(p.x),cy:PY(p.y),r:4.5,fill:CSS(col),opacity:.82,stroke:CSS("--surface"),"stroke-width":1});
    c.style.cursor="pointer";c.onclick=()=>showPair(p.a,p.b);
    const ti=el("title");ti.textContent=`${p.a.eid} ↔ ${p.b.eid}  cond=${p.x} curve=${p.y}`;c.appendChild(ti);
    s.appendChild(c);});
  box.appendChild(s);
  const r=pearson(pts.map(p=>p.x),pts.map(p=>p.y));
  document.getElementById("simcorr").textContent=`· ${pts.length} pairs · curve~condition r = ${r==null?"—":r.toFixed(2)}`;
}
function drawSimilarity(){const box=document.getElementById("simmat");box.innerHTML="";
  const its=simItems();
  document.getElementById("simcorr").textContent="";
  drawScatter(its);
  if(its.length<2){box.innerHTML='<div style="color:var(--ink3);padding:16px">select ≥2 profile experiments in Explore (or filter to a profile set) to compare</div>';document.getElementById("simclusters").innerHTML="";return;}
  const n=its.length,M=[];for(let i=0;i<n;i++){M[i]=[];for(let j=0;j<n;j++)M[i][j]=i===j?{composite:1}:composite(its[i],its[j]);}
  const cell=Math.max(24,Math.min(46,430/n)),lab=118,W=lab+n*cell+8,H=lab+n*cell+8;
  const s=el("svg",{width:"100%",viewBox:`0 0 ${W} ${H}`});
  its.forEach((e,i)=>{const cx=lab+i*cell+cell/2;const t1=tx(cx,lab-5,e.eid,{fill:CSS("--ink2"),"font-size":9.5,"font-weight":600,"text-anchor":"start",transform:`rotate(-45 ${cx} ${lab-5})`});t1.appendChild(el("title"));t1.querySelector("title").textContent=e.series;s.appendChild(t1);
    const t2=tx(lab-6,lab+i*cell+cell/2+3,e.eid,{fill:CSS("--ink2"),"font-size":9.5,"font-weight":600,"text-anchor":"end"});t2.appendChild(el("title"));t2.querySelector("title").textContent=e.series;s.appendChild(t2);});
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){const r=M[i][j],v=r?r.composite:null;const gg=el("g");
    const rc=el("rect",{x:lab+j*cell,y:lab+i*cell,width:cell-1.5,height:cell-1.5,rx:3,fill:v==null?CSS("--line2"):`color-mix(in srgb, var(--c2) ${Math.round(v*100)}%, var(--panel))`});
    if(i!==j){rc.style.cursor="pointer";gg.onclick=()=>showPair(its[i],its[j]);}gg.appendChild(rc);
    if(v!=null&&cell>=30)gg.appendChild(tx(lab+j*cell+cell/2,lab+i*cell+cell/2+3,v.toFixed(2),{fill:v>.6?"#fff":CSS("--ink2"),"font-size":9,"text-anchor":"middle","pointer-events":"none"}));
    s.appendChild(gg);}
  box.appendChild(s);
  const groups=simCluster(its,.75).sort((a,b)=>b.length-a.length);
  document.getElementById("simclusters").innerHTML=groups.map((g,i)=>`<div style="margin:4px 0"><span class="tag">cluster ${i+1} · n=${g.length}</span> ${g.map(k=>its[k].eid+" "+its[k].series).join(", ")}</div>`).join("");
}
const S_PC=[CSS("--c1"),CSS("--c5")];               // pair colours (blue / red)
function showPair(a,b){const r=composite(a,b),box=document.getElementById("simpair");
  if(!r){box.innerHTML="not comparable";document.getElementById("simdetail").style.display="none";return;}
  const cur=r.cur||{},der=r.der||{},qcol=r.quadrant==="reproducible"?"--c2":(r.quadrant||"").includes("⚠")?"--c5":"--c3";
  box.innerHTML=`<div style="font-weight:600;color:var(--ink);margin-bottom:5px">composite ${r.composite}
    ${r.quadrant?`<span class="pill" style="background:color-mix(in srgb,var(${qcol}) 18%,var(--panel));color:var(${qcol})">${r.quadrant}</span>`:""}</div>
    <div class="mono" style="font-size:11px"><span style="color:${S_PC[0]}">■ ${a.eid}</span> ${a.series} &nbsp; <span style="color:${S_PC[1]}">■ ${b.eid}</span> ${b.series}</div>
    <table class="mono" style="font-size:11.5px;margin-top:8px;width:100%">
    <tr><td style="color:var(--ink3)">condition</td><td>${r.cond.score} <span style="color:var(--ink3)">cov ${r.cond.coverage}</span></td></tr>
    <tr><td style="color:var(--ink3)">curve</td><td>${cur.curve_sim??"—"} <span style="color:var(--ink3)">R²=${cur.r2??"—"} · overlap ${cur.overlap??"—"}</span></td></tr>
    <tr><td style="color:var(--ink3)">derived</td><td>${Object.entries(der).map(([k,v])=>k+"="+v).join(", ")||"—"}</td></tr></table>
    <div style="color:var(--ink3);font-size:10.5px;margin-top:8px">condition attributes (sim):</div>
    <div class="mono" style="font-size:11px">${r.cond.parts.map(p=>`${p[0]}=${p[1]}`).join(" · ")}</div>`;
  // pair detail: overlaid canonical curves + conditions
  document.getElementById("simdetail").style.display="";
  const pl=document.getElementById("simplot");pl.innerHTML="";pl.appendChild(plotPair(a,b));
  document.getElementById("simplotleg").innerHTML=`<span><i class="dot" style="background:${S_PC[0]}"></i>${a.eid} ${a.series}</span><span><i class="dot" style="background:${S_PC[1]}"></i>${b.eid} ${b.series}</span>`;
  document.getElementById("simcond").innerHTML=condTable(a,b);
}
function plotPair(a,b){
  const box={w:520,h:300,l:54,b:42,t:16,r:14};
  const s=el("svg",{width:"100%",viewBox:`0 0 ${box.w} ${box.h}`});
  const ca=canonize(a),cb=canonize(b);
  if(a.ckey!==b.ckey||!ca||!cb){s.appendChild(tx(box.w/2,box.h/2,a.ckey!==b.ckey?"different comparability class — not overlaid":"curves unavailable",{fill:CSS("--ink3"),"font-size":11,"text-anchor":"middle"}));return s;}
  const curves=[[ca,S_PC[0]],[cb,S_PC[1]]];
  const allx=ca[0].concat(cb[0]),ally=ca[1].concat(cb[1]);
  const x0=Math.min(...allx),x1=Math.max(...allx),y0=Math.min(...ally),y1=Math.max(...ally);
  const PX=v=>box.l+((v-x0)/((x1-x0)||1))*(box.w-box.l-box.r);
  const PY=v=>box.h-box.b-((v-y0)/((y1-y0)||1))*(box.h-box.b-box.t);
  const fmt=v=>{const A=Math.abs(v);return A===0?"0":(A<0.01||A>=1e4)?v.toExponential(1):A<1?v.toFixed(2):A<100?v.toFixed(1):v.toFixed(0);};
  for(let i=0;i<=4;i++){const f=i/4,xv=x0+f*(x1-x0),yv=y0+f*(y1-y0),xx=box.l+f*(box.w-box.l-box.r),yy=box.h-box.b-f*(box.h-box.b-box.t);
    s.appendChild(el("line",{x1:box.l,y1:yy,x2:box.w-box.r,y2:yy,stroke:CSS("--line2")}));
    s.appendChild(tx(box.l-6,yy+3,fmt(yv),{fill:CSS("--ink3"),"font-size":8.5,"text-anchor":"end"}));
    s.appendChild(tx(box.l+f*(box.w-box.l-box.r),box.h-box.b+13,fmt(xv),{fill:CSS("--ink3"),"font-size":8.5,"text-anchor":"middle"}));}
  s.appendChild(el("line",{x1:box.l,y1:box.t,x2:box.l,y2:box.h-box.b,stroke:CSS("--line")}));
  s.appendChild(el("line",{x1:box.l,y1:box.h-box.b,x2:box.w-box.r,y2:box.h-box.b,stroke:CSS("--line")}));
  s.appendChild(tx((box.l+box.w-box.r)/2,box.h-6,(S_FAM[a.cfam]||a.indep||"x"),{fill:CSS("--ink2"),"font-size":10.5,"text-anchor":"middle"}));
  const mY=(box.t+box.h-box.b)/2;const yl=el("text",{x:13,y:mY,fill:CSS("--ink2"),"font-size":10.5,"text-anchor":"middle",transform:`rotate(-90 13 ${mY})`});yl.textContent=(S_FAM[a.mfam]||a.poi||"y");s.appendChild(yl);
  curves.forEach(([c,col])=>{const xs=c[0],ys=c[1];const d=xs.map((x,i)=>(i?"L":"M")+PX(x).toFixed(1)+" "+PY(ys[i]).toFixed(1)).join(" ");
    s.appendChild(el("path",{d,fill:"none",stroke:col,"stroke-width":2}));
    xs.forEach((x,i)=>s.appendChild(el("circle",{cx:PX(x),cy:PY(ys[i]),r:2,fill:col})));});
  return s;
}
function condTable(a,b){const ca=s_cfg(a),cb=s_cfg(b);
  const rows=[["material",ca.material,cb.material],["process",ca.process,cb.process],["structure",ca.structure,cb.structure],
    ["precursors",[...ca.precursors].join(", "),[...cb.precursors].join(", ")],["coreactants",[...ca.coreactants].join(", "),[...cb.coreactants].join(", ")]];
  [...new Set([...Object.keys(ca.num),...Object.keys(cb.num)])].sort().forEach(sl=>rows.push([sl,ca.num[sl],cb.num[sl]]));
  const cell=(v,eq)=>`<td style="color:${v==null?'var(--line)':eq?'var(--c2)':'var(--ink)'}">${v==null?"—":(typeof v==="number"?(+v.toPrecision(4)):v||"—")}</td>`;
  return `<table class="mono" style="font-size:11.5px;width:100%">
    <tr><td></td><td style="color:${S_PC[0]};font-weight:600">${a.eid}</td><td style="color:${S_PC[1]};font-weight:600">${b.eid}</td></tr>`
    +rows.map(r=>{const eq=r[1]!=null&&r[2]!=null&&String(r[1])===String(r[2]);
      return `<tr><td style="color:var(--ink3)">${r[0]}</td>${cell(r[1],eq)}${cell(r[2],eq)}</tr>`;}).join("")+`</table>`;
}
function simCluster(its,thr){let g=its.map((_,i)=>[i]);
  const gs=(a,b)=>{let ss=[];a.forEach(i=>b.forEach(j=>{const r=composite(its[i],its[j]);if(r)ss.push(r.composite);}));return ss.length?ss.reduce((s,v)=>s+v,0)/ss.length:0;};
  let merged=true;while(merged&&g.length>1){merged=false;let best=[thr,-1,-1];
    for(let i=0;i<g.length;i++)for(let j=i+1;j<g.length;j++){const s=gs(g[i],g[j]);if(s>best[0])best=[s,i,j];}
    if(best[1]>=0){g[best[1]]=g[best[1]].concat(g[best[2]]);g.splice(best[2],1);merged=true;}}
  return g;}

renderHead();render();drawCompare();
</script>
"""

if __name__ == "__main__":
    main()
