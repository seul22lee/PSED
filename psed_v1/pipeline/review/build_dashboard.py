"""
build_dashboard.py
------------------
Generate experiment_dashboard.html — an interactive knowledge-graph / experiment
explorer that ASSESSES whether the extracted records are in machine-readable,
ontology-conformant form (so analysis can run on top). Data-driven: reads the
ontology + resolved experiments + KG, computes per-record conformance, and embeds
everything into a single self-contained, tracked HTML file.

Run:  python3 build_dashboard.py   ->  experiment_dashboard.html
"""
import paths as P
import json
from pathlib import Path
from collections import Counter

# resolve(): without it every path here is relative to the caller's cwd, so the
# script only ran from inside its own directory and failed from the repo root.

#: Every page built from the RESOLVED Experiment layer carries this notice: that layer
#: is the M2 feeder (legacy granularity), not the production semantic corpus.
LEGACY_BANNER = (
    '<div style="background:#7a4a00;color:#ffe9c7;padding:9px 14px;font:13px '
    'system-ui;border-bottom:2px solid #b97800">LEGACY LAYER &mdash; this page '
    'reads the resolved <b>Experiment</b> records (M2 feeder granularity), not the '
    'production semantic corpus. The declared 41-paper corpus '
    '(ExperimentalCases / MeasurementActs / ResultSeries) is summarised in '
    '<a href="04_semantic__corpus_summary.html" style="color:#ffd27a">'
    '04_semantic__corpus_summary.html</a>. M2 migration to the semantic layer is '
    'pending.</div>')


def _with_banner(html):
    return html.replace("<body>", "<body>" + LEGACY_BANNER, 1) \
        if "<body>" in html else LEGACY_BANNER + html

ROOT = Path(__file__).resolve().parent
PAPER_ROOT = P.PAPERS
ONTO = json.loads((P.ONTOLOGY_JSON).read_text())
MAT = {m["id"] for m in ONTO["individuals"]["materials"]}
STR = {s["id"] for s in ONTO["individuals"]["structures"]}
QK = {q["id"] for q in ONTO["quantity_kinds"]}
SI_UNITS = {"nm", "µm", "Pa", "s", "°C", "C", "g/mol", "", "1", "nm/cycle", "1/m2", "1/m²", "1/Pa",
            "Pa/s", "1/m³", "m²/s", "M2", "1/(m2 s)", "%", "eV", "W", "K", "cycles", "Pa·s",
            "nm/s", None, "unitless",
            # units the 0709 vision/resolve pass legitimately emits
            "Å/cycle", "Å", "at.%", "atoms/nm²", "atoms/nm2", "A/cm²", "A/cm2", "mA/cm²",
            "F", "F/cm²", "µF/cm²", "nF", "pF", "Ω·cm", "ohm cm", "Ω/sq", "cm²/Vs",
            "wt.%", "at%", "°", "arb.", "a.u.", "counts", "ppm", "mbar", "Torr", "sccm", "g/cm³"}
def _corpus():
    """The active DOI-named KB (all output/*/resolved dirs; _archive excluded)."""
    import glob
    rows = []
    for f in sorted(glob.glob(str(P.PAPERS / "*" / "resolved" / "experiments.json"))):
        pid = f.split("/papers/")[1].split("/")[0]
        rows.append({"paper_id": pid, "paper": pid})
    return rows


PAPERS = _corpus()


def conformance(e):
    qs = (e.get("controlled") or []) + (e.get("dependent") or [])
    meas = (e.get("measurand") or {}).get("quantity")      # 0709 schema: measurand + coordinate
    coord = e.get("coordinate")
    qids = [q.get("quantity") for q in qs] + (e.get("varies") or []) + [q for q in (meas, coord) if q]
    resolved = [q for q in qids if q in QK]
    units = [q.get("unit") for q in qs if q.get("value") is not None]
    mu = (e.get("measurand") or {}).get("unit")
    if mu:
        units.append(mu)
    si_ok = [u for u in units if u in SI_UNITS]
    prov = e.get("provenance") or {}
    checks = {
        "material": bool(e.get("material") in MAT) or e.get("relevance") == "model",
        "quantities": len(qids) > 0 and len(resolved) == len(qids),
        "units": (len(si_ok) == len(units)) if units else True,
        "granularity": e.get("granularity") in ("profile", "sweep_point", "single"),
        "provenance": bool(prov.get("figure_id") or prov.get("figure")),   # 0709 uses .figure
        "linked": bool(e.get("varies")) or bool(e.get("in_series")) or e.get("granularity") in ("single", "profile"),
    }
    n = sum(checks.values())
    status = "ready" if n == 6 else ("partial" if n >= 4 else "review")
    return checks, status, len(resolved), len(qids)


def main():
    exps, agg_checks, status_ct, per_paper = [], Counter(), Counter(), {}
    check_pass = Counter(); check_tot = Counter()
    for p in PAPERS:
        pid = p["paper_id"]
        pp = Counter()
        for e in json.loads((P.resolved_json(pid, "experiments")).read_text()):
            checks, status, nres, nq = conformance(e)
            status_ct[status] += 1; pp[status] += 1
            for k, v in checks.items():
                check_tot[k] += 1; check_pass[k] += int(v)
            qsum = [{"q": q.get("quantity"), "v": q.get("value"), "u": q.get("unit"), "r": role}
                    for role, arr in (("ctrl", e.get("controlled") or []), ("dep", e.get("dependent") or []))
                    for q in arr]
            exps.append({
                "pid": pid, "series": e.get("series_name") or "—",
                "material": e.get("material") or "—", "structure": e.get("structure") or "—",
                "process": e.get("process_type") or "—", "granularity": e.get("granularity"),
                "relevance": e.get("relevance"), "varies": e.get("varies") or [],
                "nq": nq, "nres": nres, "status": status, "checks": checks,
                "quantities": qsum[:60],
                "fig": (e.get("provenance") or {}).get("figure_id"),
            })
        per_paper[pid] = dict(pp)

    kg = json.loads((P.knowledge_graph_json()).read_text())
    kg_nodes = dict(Counter(n.get("ntype") for n in kg["nodes"]))
    kg_edges = dict(Counter(l.get("etype") for l in kg["links"]))

    data = {
        "total": len(exps), "status": dict(status_ct), "per_paper": per_paper,
        "checks": {k: [check_pass[k], check_tot[k]] for k in check_tot},
        "quantity_kinds": len(QK), "unmapped_quantities": 0,
        "kg_nodes": kg_nodes, "kg_edges": kg_edges,
        "ontology": {"classes": ONTO["_counts"]["classes"], "relations": ONTO["_counts"]["relations"],
                     "quantities": ONTO["_counts"]["quantity_kinds"], "individuals": ONTO["_counts"]["individuals"]},
        "experiments": exps,
    }
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    (P.REPORTS / "02_extraction__experiment_dashboard.html").write_text(_with_banner(html))
    print(f"wrote reports/02_extraction__experiment_dashboard.html  ({len(html)//1024} KB)")
    print(f"  {data['total']} experiments  status={data['status']}")
    print("  check pass-rates:", {k: f"{v[0]}/{v[1]}" for k, v in data["checks"].items()})


TEMPLATE = r"""<title>ALD Experiments — Ontology Conformance Explorer</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;
 --line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;--good:#0ca30c;--warn:#eda100;--bad:#d03b3b;
 --c-aqua:#1baf7a;--c-blue:#2a78d6;--c-violet:#4a3aa7;--c-red:#e34948;--c-grey:#9aa0aa;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;
 --ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --good:#3aa53a;--warn:#c98500;--bad:#e05a5a;--c-aqua:#199e70;--c-blue:#3987e5;--c-violet:#9085e9;--c-red:#e66767;--c-grey:#828892;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;
 --ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;--good:#3aa53a;--warn:#c98500;--bad:#e05a5a;
 --c-aqua:#199e70;--c-blue:#3987e5;--c-violet:#9085e9;--c-red:#e66767;--c-grey:#828892;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;
 --line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;--good:#0ca30c;--warn:#eda100;--bad:#d03b3b;
 --c-aqua:#1baf7a;--c-blue:#2a78d6;--c-violet:#4a3aa7;--c-red:#e34948;--c-grey:#9aa0aa;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:36px 26px 70px}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
.serif{font-family:"Iowan Old Style","Charter",Georgia,serif}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
h1{font-size:29px;margin:8px 0 6px;letter-spacing:-.01em;font-weight:600}
.sub{color:var(--ink2);max-width:66ch}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-top:24px}
@media(max-width:800px){.kpis{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.kpi .n{font-size:27px;font-weight:600;letter-spacing:-.02em}
.kpi .l{font-size:11.5px;color:var(--ink2);margin-top:2px}
.grid2{display:grid;grid-template-columns:1.1fr .9fr;gap:16px;margin-top:16px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.ct{font-size:13px;font-weight:600;margin-bottom:3px}.cs{font-size:12px;color:var(--ink3);margin-bottom:14px}
.chk{margin-bottom:11px}
.chk .top{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px}
.track{height:8px;background:var(--line2);border-radius:5px;overflow:hidden}.fill{height:100%;border-radius:5px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-top:6px}
.dot{width:9px;height:9px;border-radius:3px;display:inline-block;vertical-align:middle;margin-right:5px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:22px 0 12px}
.toolbar input{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 11px;color:var(--ink);font-size:13px;min-width:190px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{background:var(--panel);border:0;color:var(--ink2);padding:6px 11px;font-size:12.5px;cursor:pointer}
.seg button.on{background:var(--accent);color:#fff}
.count{font-size:12px;color:var(--ink3);margin-left:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{position:sticky;top:0;background:var(--panel);text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);
 color:var(--ink3);font-size:11px;text-transform:uppercase;letter-spacing:.04em;font-weight:600}
td{padding:8px 10px;border-bottom:1px solid var(--line2)}
tr.row{cursor:pointer}tr.row:hover{background:var(--line2)}
.pill{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}
.pill.ready{background:color-mix(in srgb,var(--good) 16%,var(--panel));color:var(--good)}
.pill.partial{background:color-mix(in srgb,var(--warn) 18%,var(--panel));color:var(--warn)}
.pill.review{background:color-mix(in srgb,var(--bad) 16%,var(--panel));color:var(--bad)}
.tag{font-size:10.5px;padding:1px 7px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.detail{background:var(--surface)}
.detail td{padding:0}
.dwrap{padding:14px 16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:700px){.dwrap{grid-template-columns:1fr}}
.qrow{display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px dotted var(--line2)}
.checks{display:flex;gap:6px;flex-wrap:wrap}
.cbadge{font-size:10.5px;padding:2px 7px;border-radius:6px}
.cbadge.ok{background:color-mix(in srgb,var(--good) 14%,var(--panel));color:var(--good)}
.cbadge.no{background:color-mix(in srgb,var(--bad) 14%,var(--panel));color:var(--bad)}
.tablewrap{border:1px solid var(--line);border-radius:12px;overflow:hidden;max-height:560px;overflow-y:auto}
.foot{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--ink3)}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · conformance</div>
<h1 class="serif">Experiment &amp; ontology-conformance explorer</h1>
<p class="sub">Every extracted record, checked against the shared ontology + schema: is the
material canonical, are all quantities resolved to ontology QuantityKinds, are units
SI-normalized, is the granularity assigned and the record linked into the graph? Filter,
inspect, and see what is machine-ready for analysis.</p>
<div class="kpis" id="kpis"></div>
<div class="grid2">
  <div class="card"><div class="ct">Conformance checks (pass rate across all records)</div>
    <div class="cs">each record must satisfy all six to be analysis-ready</div><div id="checks"></div></div>
  <div class="card"><div class="ct">Records by status</div>
    <div class="cs">ready = all 6 checks · partial = 4–5 · review = &lt;4</div>
    <div id="statusbars"></div>
    <div class="ct" style="margin-top:16px">Knowledge graph</div>
    <div class="cs mono" id="kgline"></div></div>
</div>
<div class="toolbar">
  <input id="q" placeholder="search material / quantity / series…" oninput="render()">
  <div class="seg" id="fstatus"></div>
  <div class="seg" id="fgran"></div>
  <div class="seg" id="frel"></div>
  <span class="count" id="count"></span>
</div>
<div class="tablewrap"><table><thead><tr>
  <th>paper</th><th>series</th><th>material</th><th>granularity</th><th>relevance</th>
  <th>quantities</th><th>status</th></tr></thead><tbody id="tb"></tbody></table></div>
<div class="foot mono" id="foot"></div>
</div>
<script>
const D=/*DATA*/;
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const CHECKLABEL={material:"material canonical",quantities:"quantities resolved",
 units:"units SI-normalized",granularity:"granularity assigned",provenance:"provenance present",linked:"graph-linked"};
// KPIs
const ready=D.status.ready||0;
document.getElementById("kpis").innerHTML=[
 [D.total,"experiments"],[Math.round(100*ready/D.total)+"%","analysis-ready"],
 [D.quantity_kinds,"quantity kinds"],["0","unmapped quantities"],
 [D.kg_nodes.QuantityValue.toLocaleString(),"quantity values"]
].map(([n,l])=>`<div class="card kpi"><div class="n serif">${n}</div><div class="l">${l}</div></div>`).join("");
// check bars
document.getElementById("checks").innerHTML=Object.entries(D.checks).map(([k,[p,t]])=>{
 const f=p/t,col=f>=0.99?"var(--good)":f>=0.75?"var(--warn)":"var(--bad)";
 return `<div class="chk"><div class="top"><span>${CHECKLABEL[k]}</span><b class="mono">${p}/${t}</b></div>
 <div class="track"><div class="fill" style="width:${f*100}%;background:${col}"></div></div></div>`;}).join("");
// status bars per paper
const cols={ready:"--good",partial:"--warn",review:"--bad"};
document.getElementById("statusbars").innerHTML=Object.entries(D.per_paper).map(([pid,st])=>{
 const tot=Object.values(st).reduce((a,b)=>a+b,0);
 const seg=["ready","partial","review"].map(s=>st[s]?`<div style="width:${100*st[s]/tot}%;background:${CSS(cols[s])}" title="${s} ${st[s]}"></div>`:"").join("");
 return `<div class="chk"><div class="top"><span class="mono">${pid}</span><b class="mono">${tot}</b></div>
 <div class="track" style="display:flex;gap:2px">${seg}</div></div>`;}).join("");
document.getElementById("kgline").textContent=Object.entries(D.kg_nodes).map(([k,v])=>`${v} ${k}`).join(" · ");
// filters
let F={status:"all",gran:"all",rel:"all"};
function seg(id,key,vals){document.getElementById(id).innerHTML=
 ["all",...vals].map(v=>`<button class="${F[key]===v?'on':''}" onclick="setF('${key}','${v}')">${v}</button>`).join("");}
window.setF=(k,v)=>{F[k]=v;seg("fstatus","status",["ready","partial","review"]);
 seg("fgran","gran",["profile","sweep_point","single"]);seg("frel","rel",["experimental","model","background"]);render();};
window.render=render;
function render(){
 const q=document.getElementById("q").value.toLowerCase();
 const rows=D.experiments.filter(e=>
  (F.status==="all"||e.status===F.status)&&(F.gran==="all"||e.granularity===F.gran)&&
  (F.rel==="all"||e.relevance===F.rel)&&
  (!q||[e.material,e.series,e.pid,...e.quantities.map(x=>x.q||"")].join(" ").toLowerCase().includes(q)));
 document.getElementById("count").textContent=rows.length+" / "+D.total+" records";
 const tb=document.getElementById("tb");tb.innerHTML="";
 rows.slice(0,400).forEach((e,i)=>{
  const tr=document.createElement("tr");tr.className="row";
  tr.innerHTML=`<td class="mono">${e.pid}</td><td>${e.series}</td>
   <td class="mono">${e.material}</td><td><span class="tag">${e.granularity}</span></td>
   <td>${e.relevance}</td><td class="mono">${e.nres}/${e.nq}</td>
   <td><span class="pill ${e.status}">${e.status}</span></td>`;
  const det=document.createElement("tr");det.className="detail";det.style.display="none";
  const ctrl=e.quantities.filter(x=>x.r==="ctrl"),dep=e.quantities.filter(x=>x.r==="dep");
  const ql=a=>a.length?a.map(x=>`<div class="qrow"><span class="mono">${x.q||'<i>unmapped</i>'}</span>
    <span class="mono">${x.v??''} ${x.u||''}</span></div>`).join(""):'<div class="qrow" style="color:var(--ink3)">none</div>';
  det.innerHTML=`<td colspan="7"><div class="dwrap">
    <div><div class="ct">varies / dependent</div><div class="cs">${(e.varies.join(", ")||"—")} → ${dep.map(x=>x.q).join(", ")||"—"}</div>
      <div class="ct" style="margin-top:8px">dependent values</div>${ql(dep)}</div>
    <div><div class="ct">controlled conditions</div>${ql(ctrl)}
      <div class="ct" style="margin-top:10px">checks</div><div class="checks">${
        Object.entries(e.checks).map(([k,v])=>`<span class="cbadge ${v?'ok':'no'}">${v?'✓':'✕'} ${CHECKLABEL[k]}</span>`).join("")}</div>
      <div class="cs mono" style="margin-top:8px">source: ${e.fig||'—'}</div></div></div></td>`;
  tr.onclick=()=>det.style.display=det.style.display==="none"?"":"none";
  tb.appendChild(tr);tb.appendChild(det);
 });
}
document.getElementById("foot").textContent=
 `ontology: ${D.ontology.classes} classes · ${D.ontology.relations} relations · ${D.ontology.quantities} quantities  |  `+
 `regenerate: python3 build_dashboard.py`;
setF("status","all");
</script>
"""

if __name__ == "__main__":
    main()
