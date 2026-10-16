#!/usr/bin/env python3
"""Writes reports/pilot.html (untracked; self-contained, works offline): one screen over the knowledge base of the three pilot papers.

    python3 psed_v2/pilot/report.py

Everything on the page comes from query.py at build time (find, detail, claims, source and the value records they return); the
page's JavaScript only filters, sorts and draws. The screen:
- top, one line of filters: material, structure, result, paper, and "more conditions" opening the ranges;
- left, a list with a toggle, experiments | claims. One line per experiment: paper · name · the 1-2 conditions that distinguish it ·
  the selected result's value. The authors' comparisons are group headers ("Series F — purge"); a click opens the comparison on the
  right. Each row has a checkbox; when the filters leave six rows or fewer, all are selected. With a paper filter, one line gives
  that paper's coverage;
- right, one panel in one of four states: selected (one plot, one table, the claims linked to two or more of the selected items),
  detail (what, what differs with the full recipe behind one line, results one line each with method and source, claims), a
  comparison (what it varies, its members, its main results with their effect and one sentence on noise), or a source (the passage
  coloured by coverage, or the figure crop with the figure's values).
Values: a measured or stated value carries no mark; anything else one plain word (read from figure, computed by the authors, computed here, assumed, model,
cited), written once in a column header when the whole column shares it; a definition only when it is not the default.
"""
import base64, collections, csv, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import elements  # noqa: E402
import lists as L  # noqa: E402
import query as Q  # noqa: E402

RANGES = [("deposition_temperature", "temperature", "°C"), ("plasma_gas_ratio", "H2 flow ratio", ""), ("cycle_number", "cycles", ""),
          ("feature_height", "channel height", "nm"), ("process_pressure", "pressure", "Pa"), ("exposure", "exposure", "Pa s")]


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def plain(t):
    """Element text as plain English for the screen: LaTeX and HTML markup removed."""
    t = re.sub(r"<su[bp]>(.*?)</su[bp]>", r"\1", t)
    t = re.sub(r"\\(?:text|mathrm|mathit|mathbf)\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\\(?:circ)", "°", t)
    t = t.replace("$", "").replace("\\%", "%").replace("\\,", " ").replace("\\ ", " ").replace("\\times", "×").replace("\\pm", "±")
    t = re.sub(r"\\([a-zA-Z]+)", r"\1", t)
    t = re.sub(r"[_^]\{([^}]*)\}", r"\1", t)
    t = re.sub(r"(?<=\w)[_^](?=\w)", "", t)
    return re.sub(r"\s+", " ", t).replace("{", "").replace("}", "").strip()


def lite(rec):
    """A value record trimmed to what the screen shows."""
    if not rec:
        return None
    u = rec.get("uncertainty")
    out = dict(text=rec["text"], kind=rec["kind"], fact=rec.get("fact", ""), statement=rec.get("statement", ""), definition=rec["definition"] if rec["kind"] != "computed here" else "", source=rec.get("source", ""),
               paper=rec.get("paper", ""), value=rec.get("value"), unit=rec.get("unit", ""), mode=rec.get("mode", ""), method=rec.get("method", ""),
               uncertainty=(f"± {u['value']}" + (f" ({u.get('stat') or 'spread'} between {u['kind'].replace('_', ' ')}{', ' + str(u['n']) if u.get('n') and u.get('n') != 'not_stated' else ''})"
                                                if u.get("kind") and u["kind"] not in ("not_stated",) else "")) if u else "",
               alternatives=[a["text"] + (f" ({a['kind']})" if a["kind"] in L.KIND_WORDS else "") for a in rec.get("alternatives", [])],
               formula=rec["definition"] if rec["kind"] == "computed here" else "", assumed=rec.get("assumed", []),
               inputs=[f"{i['name']} {i['value']} {i['unit']}".strip() for i in rec.get("inputs", [])], readings=rec.get("readings", []))
    if rec.get("curve") and rec["curve"].get("points"):
        out["curve"] = dict(x=rec["curve"]["x"], points=rec["curve"]["points"])
    if rec.get("settings"):
        out["settings"] = [f"{s['name']} {s['text']}" for s in rec["settings"]]
    return out


def paper_names():
    out = {}
    for k, T in Q.TREES.items():
        p = next(r for r in T.rows if r["type"] == "paper")
        m = re.match(r"([A-Z][a-z]+) et al\. (\d{4})", p["statement"])
        out[k] = f"{m.group(1)} {m.group(2)}" if m else k
    return out


def build():
    names = paper_names()
    found = Q.find()
    rows, groups, details = [], [], {}
    for k, T in Q.TREES.items():
        for e in Q.experiments(T) + [r["fact_id"] for r in T.rows if r["type"] == "entity" and Q.role(T, r["fact_id"]) == "input"]:
            d = Q.detail(e)
            details[e] = dict(d, recipe=[dict(key=c["key"], name=c["name"], record=lite(c["record"])) for c in d["recipe"]],
                              results=[dict(key=r["key"], name=r["name"], record=lite(r["record"])) for r in d["results"]],
                              claims=[c["id"] for c in d["claims"]])
        for c in T.comps:
            d = Q.detail(c["fact_id"])
            details[c["fact_id"]] = dict(d, claims=[x["id"] for x in d["claims"]], values=[lite(v) for v in d["values"]])
    for i, r in found["rows"].items():
        T = Q.tree_of(i)
        d = details.get(i) or Q.detail(i)
        if i not in details:                                                    # a cited work
            details[i] = dict(d, recipe=[dict(key=c["key"], name=c["name"], record=lite(c["record"])) for c in d["recipe"]],
                              results=[dict(key=x["key"], name=x["name"], record=lite(x["record"])) for x in d["results"]], claims=[c["id"] for c in d["claims"]])
        res = collections.defaultdict(list)                                    # the values of a result are filled from find(result=) below
        conds = {}
        if r["role"] != "cited":
            for q, _, unit in RANGES:
                for kk, fs in T.vector(i).items():
                    if kk.split("{")[0] == q and Q.val(fs[0]) is not None:
                        try:
                            conds[q] = L.convert(Q.val(fs[0]), fs[0]["unit"], unit)
                        except (ValueError, KeyError):
                            pass
                        break
        rec = {c["key"].split("{")[0]: c["record"]["text"] for c in details[i]["recipe"] if c.get("record")}
        rows.append(dict(id=i, paper=r["paper"], name=r["name"], inferred=r["inferred"], role=r["role"], distinguish=r["distinguish"], home=r["home"],
                         groups=r["groups"], material=rec.get("material", ""), structure=rec.get("structure_type", ""), conds=conds, results=res))
    by_id = {r["id"]: r for r in rows}
    for q in sorted({x["key"].split("{")[0].split("[")[0] for d in details.values() for x in d.get("results", []) if x.get("record")}):
        for i, r in Q.find(result=q)["rows"].items():                           # the query layer selects the values of each result
            if i in by_id:
                by_id[i]["results"][q] = [dict(key=x["key"], name=x["name"], **lite(x["record"])) for x in r["result"]]
    for gr in found["groups"]:
        own = sorted({v["fact"].split(":")[0] and Q.TREES[gr["paper"]].byid[v["fact"]]["quantity"] for v in details.get(gr["id"], {}).get("values", []) if v.get("fact")})
        groups.append(dict(id=gr["id"], paper=gr["paper"], label=gr["label"], kind=gr["kind"], members=gr["members"], all=gr["all_members"], own=own))
    cl = Q.claims()
    claims_ = [dict(c, rests_on=[lite(x) for x in c["rests_on"]], user=c["author"] == "user") for c in cl]
    # sources: every element with a fact, the figure's values for a panel
    sources, imgs = {}, {}
    for k, T in Q.TREES.items():
        pid = Q.KEY[k]
        els = rd(HERE / f"{pid}.elements.csv"); cov = {c["element_id"]: c["status"] for c in rd(HERE / f"{pid}.coverage.csv")}
        texts = elements.texts(pid)
        by_el = collections.defaultdict(list)
        for f in T.rows:
            if "#" in f["fact_id"]:
                for e in f["evidence"].split(";"):
                    by_el[e].append(f)
        for e in els:
            eid = e["element_id"]
            fig = re.match(r"(fig\d+)", eid)
            pool = [f for e2, fs in by_el.items() if fig and re.match(rf"{fig.group(1)}(?![0-9])", e2) for f in fs] if e["kind"] in ("panel", "caption") else by_el.get(eid, [])
            seen, vals = set(), []
            for f in pool:
                if f["fact_id"] not in seen and Q.text_of(f) and f["type"] in ("observation", "derived", "model", "setting"):
                    seen.add(f["fact_id"]); e_ = T.ent_of(f["fact_id"])
                    vals.append(dict(lite(Q.record(T, f)), name=Q.name_of(Q.ckey(f), f), of=T.label(e_) if e_ else ""))
            if e["crop"] and e["crop"] not in imgs:
                p = V2 / "ingest/final" / pid / e["crop"]
                if p.exists():
                    imgs[e["crop"]] = ("data:image/png;base64," if p.suffix == ".png" else "data:image/jpeg;base64,") + base64.b64encode(p.read_bytes()).decode()
            sources[f"{k}:{eid}"] = dict(paper=k, element=eid, kind=e["kind"], locator=e["locator"], coverage=cov.get(eid, ""),
                                          text=plain(texts.get(eid, "")) if e["kind"] != "panel" else "", crop=e["crop"] if e["kind"] in ("panel", "caption") else "",
                                          values=vals, statements=[f["statement"] for f in by_el.get(eid, []) if not Q.text_of(f) and f["type"] in ("observation",)][:6])
    coverage = {}
    for k in Q.TREES:
        c = collections.Counter(r["status"] for r in rd(HERE / f"{Q.KEY[k]}.coverage.csv"))
        coverage[k] = dict(covered=c.get("covered", 0), none=c.get("no knowledge", 0), missed=c.get("missed", 0), total=sum(c.values()))
    results = sorted({q for r in rows for q in r["results"]}, key=lambda q: L.NAMES.get(q, q))
    filters = dict(materials=sorted({r["material"] for r in rows if r["material"]}), structures=sorted({r["structure"] for r in rows if r["structure"]}),
                   results=[dict(q=q, name=L.NAMES.get(q, q.replace("_", " "))) for q in results if q != "other"],
                   ranges=[dict(q=q, name=n, unit=u) for q, n, u in RANGES])
    return dict(papers=names, rows=rows, groups=groups, details=details, claims=claims_, sources=sources, coverage=coverage, filters=filters,
                kinds=L.KIND_WORDS, primary=L.PRIMARY), imgs


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PSED pilot</title>
<style>
:root{--fg:#1d2330;--mut:#5d6675;--line:#d9dee6;--bg:#fff;--acc:#1f5fa8;--hi:#f2f6fc;--ok:#e3f2e6;--none:#f1f1f1;--miss:#fbe3e1;--c0:#1f5fa8;--c1:#c0392b;--c2:#2e7d3a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--fg:#e6e9ef;--mut:#a8b0bd;--line:#3a4150;--bg:#151821;--acc:#7fb0ef;--hi:#1e2431;--ok:#1f3326;--none:#262a33;--miss:#3b2423;--c0:#7fb0ef;--c1:#ef8a7f;--c2:#7fcf8a}}
:root[data-theme="dark"]{--fg:#e6e9ef;--mut:#a8b0bd;--line:#3a4150;--bg:#151821;--acc:#7fb0ef;--hi:#1e2431;--ok:#1f3326;--none:#262a33;--miss:#3b2423;--c0:#7fb0ef;--c1:#ef8a7f;--c2:#7fcf8a}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--fg);background:var(--bg)}
#bar{display:flex;flex-wrap:nowrap;gap:10px;align-items:center;padding:8px 16px;border-bottom:1px solid var(--line);overflow-x:auto;white-space:nowrap}
#bar label{font-size:14px;color:var(--mut)}select,input,button{font:inherit;font-size:14px;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:3px 6px}
button{cursor:pointer}#more{display:none;gap:10px;padding:6px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}#more.on{display:flex}#more input{width:76px}
main{display:grid;grid-template-columns:minmax(300px,40%) 1fr;height:calc(100vh - 48px)}#left{border-right:1px solid var(--line);overflow:auto;padding:8px 12px}#right{overflow:auto;padding:12px 18px}
.tog button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.gh{margin:12px 0 4px;font-weight:600;color:var(--acc)}.gh span{cursor:pointer}.gh span:hover{text-decoration:underline}.gh input{margin:0 4px 0 0;vertical-align:middle}.gp{margin:16px 0 4px;font-size:14px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.row{padding:2px 0 2px 24px;text-indent:-24px}.row input{margin:0 6px 0 0;vertical-align:middle}.row .nm{cursor:pointer}.row .nm:hover{text-decoration:underline}.mut{color:var(--mut)}
.mark{font-size:14px;color:var(--mut);border-bottom:1px dotted var(--mut);cursor:help}.val{font-variant-numeric:tabular-nums}
.chip{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:0 7px;margin:1px 2px;font-size:14px}
h2{font-size:18px;margin:4px 0 8px}h3{font-size:15px;margin:14px 0 4px}.part{margin-bottom:10px}.line{padding:2px 0}.more{color:var(--acc);cursor:pointer;font-size:14px}
.src{color:var(--acc);cursor:pointer;font-size:14px}.src:hover{text-decoration:underline}
table{border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:3px 8px;text-align:left;vertical-align:top}th{font-weight:600}
.cov-covered{background:var(--ok)}.cov-no\ knowledge{background:var(--none)}.cov-missed{background:var(--miss)}.passage{padding:8px 10px;border-radius:4px}
.claim{padding:4px 0;border-bottom:1px solid var(--line)}.st{font-size:14px;color:var(--mut)}img.crop{max-width:100%;border:1px solid var(--line)}
svg text{font-size:14px;fill:var(--fg)}svg .ax{stroke:var(--mut)}.lg{display:flex;gap:14px;flex-wrap:wrap;font-size:14px;color:var(--mut)}
@media (max-width:760px){main{grid-template-columns:1fr;height:auto}#left{border-right:0}}
</style></head><body>
<div id="bar"></div><div id="more"></div><main><div id="left"></div><div id="right"></div></main>
<script>
const D=__DATA__, IM=__IMGS__;
const S={paper:"",material:"",structure:"",result:"",ranges:{},list:"experiments",checked:new Set(),panel:{type:"none"},x:"",open:new Set()};
const $=s=>document.querySelector(s), esc=t=>String(t??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ROW=Object.fromEntries(D.rows.map(r=>[r.id,r])), GRP=Object.fromEntries(D.groups.map(g=>[g.id,g])), CL=Object.fromEntries(D.claims.map(c=>[c.id,c]));
const PN=k=>D.papers[k]||k, col=k=>`var(--c${Object.keys(D.papers).indexOf(k)})`;
const word=r=>r&&D.kinds[r.kind]?D.kinds[r.kind]:"";
const vtext=(r,skipKind)=>!r?"":`${r.text}${r.definition?` <span class="mut">${esc(r.definition)}</span>`:""}${!skipKind&&word(r)?` <span class="mut">${word(r)}</span>`:""}`;
const srcLink=r=>r&&r.source?`<span class="src" onclick="openSource('${r.paper}:${r.source}','${r.fact||""}')">${esc(D.sources[r.paper+":"+r.source]?.locator||"source")}</span>`:"";
const inferredMark=x=>x?` <span class="mark" title="not stated by the paper; inferred">i</span>`:"";
function bar(){const sel=(k,opts,cur,lab)=>`<label>${lab} <select onchange="setF('${k}',this.value)"><option value="">any</option>${opts.map(o=>`<option value="${esc(o.v)}" ${o.v===cur?"selected":""}>${esc(o.t)}</option>`).join("")}</select></label>`;
 $("#bar").innerHTML=sel("material",D.filters.materials.map(m=>({v:m,t:m})),S.material,"material")+sel("structure",D.filters.structures.map(m=>({v:m,t:m.replace(/_/g," ")})),S.structure,"structure")
  +sel("result",D.filters.results.map(r=>({v:r.q,t:r.name})),S.result,"result")+sel("paper",Object.entries(D.papers).map(([k,n])=>({v:k,t:n})),S.paper,"paper")
  +`<button onclick="$('#more').classList.toggle('on')">more conditions</button>`;
 $("#more").innerHTML=D.filters.ranges.map(r=>`<label>${r.name}${r.unit?` (${r.unit})`:""} <input type="number" placeholder="min" value="${S.ranges[r.q]?.[0]??""}" onchange="setR('${r.q}',0,this.value)"> – <input type="number" placeholder="max" value="${S.ranges[r.q]?.[1]??""}" onchange="setR('${r.q}',1,this.value)"></label>`).join("")}
function pass(r){if(S.paper&&r.paper!==S.paper)return false;if(S.material&&r.material!==S.material)return false;if(S.structure&&r.structure!==S.structure)return false;
 if(S.result&&!(r.results[S.result]||[]).length)return false;for(const q in S.ranges){const [a,b]=S.ranges[q];if(a===""&&b==="")continue;const v=r.conds[q];if(v==null)return false;if(a!==""&&v<+a)return false;if(b!==""&&v>+b)return false}return true}
function visible(){return D.rows.filter(pass)}
function setF(k,v){S[k]=v;autoSelect();render()}
function setR(q,i,v){S.ranges[q]=S.ranges[q]||["",""];S.ranges[q][i]=v;autoSelect();render()}
function autoSelect(){const v=visible();if(v.length&&v.length<=6){S.checked=new Set(v.map(r=>r.id));S.panel={type:"selected"}}else if(S.panel.type==="selected"){S.checked=new Set([...S.checked].filter(i=>v.some(r=>r.id===i)));if(!S.checked.size)S.panel={type:"none"}}}
function rowLine(r){const res=S.result?(r.results[S.result]||[]).map(x=>`<span class="val">${vtext(x)}</span>`).join("; "):"";
 const dis=r.distinguish.filter(d=>!r.name.includes(d.text.split(" ")[0])).map(d=>`${esc(d.name)} ${esc(d.text)}`).join(", ");
 return `<div class="row"><input type="checkbox" ${S.checked.has(r.id)?"checked":""} onchange="tick('${r.id}',this.checked)"><span class="mut">${esc(PN(r.paper))}</span> · <span class="nm" onclick="openDetail('${r.id}')">${esc(r.name)}</span>${inferredMark(r.inferred)}${dis?` · <span class="mut">${dis}</span>`:""}${res?` · ${res}`:""}</div>`}
function left(){const tog=`<div class="tog"><button class="${S.list==="experiments"?"on":""}" onclick="S.list='experiments';render()">experiments</button> <button class="${S.list==="claims"?"on":""}" onclick="S.list='claims';render()">claims</button></div>`;
 if(S.list==="claims"){const cs=D.claims.filter(c=>(!S.paper||c.paper===S.paper)&&(!S.result||c.effect.includes((D.filters.results.find(r=>r.q===S.result)||{}).name)));
  return tog+`<div class="mut" style="margin:6px 0">${cs.length} claims</div>`+cs.map(c=>`<div class="claim"><span class="mut">${c.user?"by user":esc(PN(c.paper))} · ${esc(c.stance)}</span> ${esc(c.statement)}${c.cause.length||c.effect.length?` <span class="mut">${esc(c.cause.join(", "))} → ${esc(c.effect.join(", "))}</span>`:""} <span class="chip">${esc(c.scope)}</span></div>`).join("")}
 const v=visible(), ids=new Set(v.map(r=>r.id));let h=tog+`<div class="mut" style="margin:6px 0">${v.length} experiments${S.checked.size?` · ${S.checked.size} selected <span class="more" onclick="S.checked=new Set();S.panel={type:'none'};render()">clear</span>`:""}</div>`;
 if(S.paper){const c=D.coverage[S.paper];h+=`<div class="mut">coverage of ${esc(PN(S.paper))}: ${c.covered} of ${c.total} elements covered, ${c.missed} missed</div>`}
 for(const k of Object.keys(D.papers)){if(S.paper&&k!==S.paper)continue;const gs=D.groups.filter(g=>g.paper===k&&g.kind!=="cited").concat(D.groups.filter(g=>g.paper===k&&g.kind==="cited"));const rs=v.filter(r=>r.paper===k);if(!rs.length)continue;
  const other=rs.filter(r=>!r.home);if(other.length)h+=`<div class="gh mut" style="cursor:default">${esc(PN(k))} · other experiments</div>`+other.map(rowLine).join("");
  for(const g of gs){const ms=g.members.filter(i=>ids.has(i));const any=g.all.some(i=>ids.has(i))||(S.result&&(g.own||[]).includes(S.result)&&(!S.paper||g.paper===S.paper));if(!any)continue;const vis=g.all.filter(i=>ids.has(i)),allOn=vis.length&&vis.every(i=>S.checked.has(i));
   h+=`<div class="gh"><input type="checkbox" title="select all its experiments" ${allOn?"checked":""} onchange="tickGroup('${g.id}',this.checked)"> <span ${g.kind==="cited"?'style="cursor:default"':`onclick="openComp('${g.id}')"`}>${esc(PN(k))} · ${esc(g.label)}</span></div>`+ms.map(i=>rowLine(ROW[i])).join("")}}
 return h}
function tickGroup(g,on){const ids=new Set(visible().map(r=>r.id));GRP[g].all.filter(i=>ids.has(i)).forEach(i=>on?S.checked.add(i):S.checked.delete(i));S.panel=S.checked.size?{type:"selected"}:{type:"none"};render()}
function tick(i,on){on?S.checked.add(i):S.checked.delete(i);S.panel=S.checked.size?{type:"selected"}:{type:"none"};render()}
function openDetail(i){S.panel={type:"detail",id:i};renderRight()}function openComp(i){S.panel={type:"comparison",id:i};renderRight()}function openSource(i,f){S.panel={type:"source",id:i,fact:f||""};renderRight()}
function lim(items,key,n=6){const all=S.open.has(key);const sh=all?items:items.slice(0,n);return sh.join("")+(items.length>n?`<div class="more" onclick="S.open.${all?"delete":"add"}('${key}');renderRight()">${all?"show fewer":`+${items.length-n} more`}</div>`:"")}
function claimLine(id){const c=CL[id];if(!c)return"";return `<div class="claim"><span class="mut">${c.user?"by user":esc(PN(c.paper))} · ${esc(c.stance)}</span> ${esc(c.statement)} <span class="chip">${esc(c.scope)}</span></div>`}
function detailPanel(id){const d=D.details[id];if(!d)return"";const what=d.what||{};
 const link=i=>`<span class="src" onclick="openDetail('${i}')">${esc((D.details[i]||{name:i}).name)}</span>`;
 const sub=[what.substrate?`substrate: ${esc(what.substrate)}`:"",(what.input_ids||[]).length?`made from: ${what.input_ids.map(link).join(", ")}`:"",what.parent?`part of: ${link(what.parent)}`:"",d.type==="cited"?"a work the paper cites":""].filter(Boolean).join(" · ");
 const rr=(d.recipe||[]);const unc=k=>{const c=rr.find(c=>c.key===k);return c&&c.record&&c.record.uncertainty?` <span class="mut">${esc(c.record.uncertainty)}</span>`:""};
 const diffs=(d.differs||[]).map(x=>`<div class="line">${esc(x.name)} <span class="val">${esc(x.text)}</span>${unc(x.key)}</div>`);
 const full=S.open.has("recipe:"+id)?rr.map(c=>`<div class="line mut">${esc(c.name)} <span class="val">${vtext(c.record)}</span>${c.record.uncertainty?` ${esc(c.record.uncertainty)}`:""} ${srcLink(c.record)}</div>`).join(""):"";
 const ORD=["penetration_depth","film_thickness","growth_per_cycle","resistivity","composition","h_per_metal","film_density","density_relative_to_bulk","mass_gain","phase","crystallinity","shell_volume_fraction","coating_mass_fraction","moles_deposited","moles_from_mass_gain"];
 const ordk=k=>{const i=ORD.indexOf(k.split("{")[0]);return i<0?ORD.length:i};
 const res=(d.results||[]).filter(x=>x.record&&(x.record.text||x.record.curve)).sort((a,b)=>ordk(a.key)-ordk(b.key)).map(x=>{const r=x.record,k="res:"+id+":"+x.key,o=S.open.has(k);
  return `<div class="line"><span class="more" style="color:inherit" onclick="S.open.${o?"delete":"add"}('${k}');renderRight()">${esc(x.name)}</span> <span class="val">${r.curve&&!r.text?"curve of "+r.curve.points.length+" points":vtext(r)}</span>${r.uncertainty?` <span class="mut">${esc(r.uncertainty)}</span>`:""}${r.method&&r.method!=="calculation"?` <span class="mut">${esc(r.method.replace(/_/g," "))}${r.mode&&r.mode!=="not_stated"?", "+r.mode.replace("_"," "):""}</span>`:""} ${srcLink(r)}`
   +(o?`<div class="mut" style="margin-left:14px">${(r.settings||[]).map(esc).join(" · ")||""}${r.alternatives.length?` chosen over ${esc(r.alternatives.join(", "))}`:""}${r.formula?` ${esc(r.formula)}`:""}${r.inputs.length?` from ${esc(r.inputs.join(", "))}`:""}${r.assumed.length?` · assumed: ${esc(r.assumed.map(a=>a.replace("user:assume_","").replace(/_/g," ")).join(", "))}`:""}</div>`:"")+`</div>`});
 const cls=(d.claims||[]).map(claimLine);
 return `<h2>${esc(d.name)}${inferredMark(d.inferred)} <span class="mut" style="font-size:14px;font-weight:400">${esc(PN(d.paper))}</span></h2>
 <div class="part"><h3>What</h3><div class="line">${esc(d.role==="model run"?"a model run":d.role==="input"?"measured before any deposition":d.type==="cited"?"cited work":"a deposited specimen")}${(d.comparisons||[]).length?` in ${d.comparisons.map(c=>`<span class="src" onclick="openComp('${c.id}')">${esc(c.label)}</span>`).join(", ")}`:""}</div>${sub?`<div class="line mut">${sub}</div>`:""}</div>
 <div class="part"><h3>What differs</h3>${diffs.slice(0,6).join("")||'<div class="mut">nothing beyond its group</div>'}<div class="more" onclick="S.open.${S.open.has("recipe:"+id)?"delete":"add"}('recipe:${id}');renderRight()">${S.open.has("recipe:"+id)?"hide the full recipe":"full recipe"}</div>${full}</div>
 <div class="part"><h3>Results</h3>${lim(res,"r:"+id)||'<div class="mut">none</div>'}</div>
 <div class="part"><h3>Claims</h3>${lim(cls,"c:"+id,3)||'<div class="mut">none</div>'}</div>`}
function compPanel(id){const d=D.details[id];if(!d)return"";const ms=d.members.map(m=>`<span class="chip src" onclick="openDetail('${m}')">${esc((ROW[m]||D.details[m]||{name:m}).name)}</span>`);
 const eff=(d.effects||[]).filter(e=>e.main);const cant=eff.length&&eff.every(e=>/cannot be judged/.test(e.sentence));
 const fitOf=k=>(d.fits||[]).find(f=>f.key===k);
 const lines=eff.map(e=>{const f=fitOf(e.key);return `<div class="line">${esc(e.name)}: range <span class="val">${esc(e.effect)}${e.unit?" "+esc(e.unit):""}</span> over ${e.n}${f?` <span class="mut">· power-law exponent ${esc(f.exponent)} against ${esc(f.x)}${f.corrected.map(c=>`, ${esc(c.exponent)} with ${esc(c.condition)} set to ${esc(c.to)}`).join("")}</span>`:""}${cant?"":` <span class="mut">${esc(e.sentence)}</span>`}</div>`});
 const own=(d.values||[]).map(v=>`<div class="line">${esc(v.text&&v.statement?v.statement:"")}</div>`);
 return `<h2>${esc(d.label)} <span class="mut" style="font-size:14px;font-weight:400">${esc(PN(d.paper))}</span></h2>${d.purpose?`<div class="line mut">${esc(d.purpose)}</div>`:""}
 <div class="part"><h3>Varies</h3><div class="line">${esc(d.varies.join(", ")||"nothing stated")}${d.confounders?` <span class="mut">· also differs: ${esc(d.confounders)}</span>`:""}</div></div>
 <div class="part"><h3>Members</h3>${lim(ms,"m:"+id)}</div><div class="part"><h3>Main results</h3>${lim(lines,"e:"+id,3)||'<div class="mut">no result on two or more members</div>'}${cant?`<div class="line mut">no repeated runs; the size of the differences cannot be judged</div>`:""}</div>
 ${own.length?`<div class="part"><h3>Stated for the set</h3>${lim(own,"o:"+id,6)}</div>`:""}`}
function sourcePanel(id){const s=D.sources[id];if(!s)return"";const f=S.panel.fact;const vs=[...s.values].sort((a,b)=>(b.fact===f)-(a.fact===f));
 const vals=vs.map(v=>`<div class="line"${v.fact===f&&f?' style="font-weight:600"':""}>${v.of?esc(v.of)+": ":""}${esc(v.name)} <span class="val">${vtext(v)}</span></div>`);
 return `<h2>${esc(s.locator)} <span class="mut" style="font-size:14px;font-weight:400">${esc(PN(s.paper))}</span></h2>${s.crop&&IM[s.crop]?`<img class="crop" src="${IM[s.crop]}" alt="${esc(s.locator)}">`:""}
 ${s.text?`<div class="passage cov-${esc(s.coverage)}">${esc(s.text)}</div><div class="mut" style="font-size:14px">${s.coverage==="covered"?"covered by the knowledge base":s.coverage==="missed"?"not covered":"no knowledge to extract"}</div>`:""}
 <div class="part"><h3>${s.crop?"Values in this figure":"Values from this passage"}</h3>${lim(vals,"s:"+id)||'<div class="mut">none</div>'}</div>`}
// selected: one plot, one table, the claims linked to two or more of them
function numOf(t){const m=String(t||"").match(/^[≤≥<>]?\s*(-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)/i);return m?+m[1]:null}
function selPanel(){const ids=[...S.checked].filter(i=>D.details[i]);if(!ids.length)return"";const ds=ids.map(i=>D.details[i]);
 const ck={};ds.forEach((d,j)=>(d.recipe||[]).forEach(c=>{(ck[c.key]=ck[c.key]||{name:c.name,v:{}}).v[ids[j]]=c.record}));
 const shared=[],diff=[];Object.entries(ck).forEach(([k,o])=>{const t=ids.map(i=>o.v[i]?o.v[i].text:null);(new Set(t).size===1&&t[0]!==null?shared:diff).push([k,o])});
 const rank=k=>{const r=D.primary.indexOf(k.split("{")[0]);return r<0?99:r};diff.sort((a,b)=>rank(a[0])-rank(b[0]));
 const baseKey=k=>k.replace(/(over|relative_to|kind)=[^;}]*;?/g,"").replace(/;}/,"}").replace(/{}/,"");
 const rk={};ds.forEach((d,j)=>(d.results||[]).forEach(x=>{if(!x.record||(!x.record.text&&!x.record.curve))return;if(S.result&&x.key.split("{")[0].split("[")[0]!==S.result)return;const bk=baseKey(x.key);
  const o=(rk[bk]=rk[bk]||{name:x.name,v:{}});if(!o.v[ids[j]]||(x.record.kind!=="computed here"&&o.v[ids[j]].kind==="computed here"))o.v[ids[j]]=x.record;if(x.name.length<o.name.length)o.name=x.name}));
 const PR=["penetration_depth","film_thickness","growth_per_cycle","resistivity","composition","mass_gain","crystallinity","phase"],pr=k=>{const i=PR.indexOf(k.split("{")[0]);return i<0?50:i};
 let rcols=Object.entries(rk).filter(([k,o])=>S.result||Object.keys(o.v).length===ids.length).sort((a,b)=>pr(a[0])-pr(b[0])||a[1].name.localeCompare(b[1].name));
 const rmore=rcols.length>6&&!S.open.has("rcols");if(rmore)rcols=rcols.slice(0,6);const nAll=Object.entries(rk).filter(([k,o])=>S.result||Object.keys(o.v).length===ids.length).length;
 const xs=diff.filter(([k,o])=>ids.every(i=>o.v[i]&&o.v[i].value!=null)).map(([k,o])=>({k,name:o.name}));
 const curveX=[...new Set(rcols.flatMap(([k,o])=>Object.values(o.v).filter(r=>r.curve).map(r=>r.curve.x)))];
 curveX.forEach(q=>{if(!xs.some(x=>x.k.split("{")[0]===q))xs.push({k:q,name:q.replace(/_/g," ")})});
 if(!xs.some(x=>x.k===S.x))S.x=xs.length?xs[0].k:"";
 const qOfX=S.x.split("{")[0];
 const pts=[],curves=[];rcols.forEach(([k,o])=>ids.forEach(i=>{const r=o.v[i];if(!r)return;if(r.curve&&r.curve.x===qOfX)curves.push({i,name:ROW[i]?ROW[i].name:D.details[i].name,r,col:o.name});else{const xr=ck[S.x]&&ck[S.x].v[i];if(xr&&xr.value!=null&&r.value!=null)pts.push({i,x:xr.value,y:r.value,r,col:o.name})}}));
 const xu=(ids.map(i=>ck[S.x]&&ck[S.x].v[i]).find(Boolean)||{}).unit||"",yu=(pts[0]?.r.unit)||(curves[0]?.r.unit)||"";
 const plot=plotSvg(pts,curves,(xs.find(x=>x.k===S.x)?.name||"")+(xu?` (${xu})`:""),(rcols.length===1?rcols[0][1].name:(S.result?(D.filters.results.find(r=>r.q===S.result)||{}).name:"value"))+(yu?` (${yu})`:""));
 const colHead=([k,o])=>{const ws=[...new Set(Object.values(o.v).map(word))];const defs=[...new Set(Object.values(o.v).map(r=>r.definition||r.formula||""))].filter(x=>!Object.values(o.v).some(r=>r.formula===x));return `${esc(o.name)}${ws.length===1&&ws[0]?` <span class="mut">${ws[0]}</span>`:""}${defs.length===1&&defs[0]?` <span class="mut">${esc(defs[0])}</span>`:""}`};
 const sameDef=([k,o])=>new Set(Object.values(o.v).map(r=>r.definition||r.formula||"")).size<=1;
 const byQ={};rcols.forEach(([k])=>{const q=k.split("{")[0];byQ[q]=(byQ[q]||0)+1});
 const cell=(o,i,col)=>{const r=o.v[i];if(!r)return"";const ws=new Set(Object.values(o.v).map(word));const ok=sameDef(col);
  return `${r.curve&&!r.text?"curve":esc(r.text)}${ws.size>1&&word(r)?` <span class="mut">${word(r)}</span>`:""}${!ok?` <span class="mut">different definition: ${esc(r.definition||r.formula||"the default")}</span>`:""}`};
 const table=`<div class="line mut">${shared.length?"shared: "+lim(shared.map(([k,o])=>`<span class="chip">${esc(o.name)} ${esc(o.v[ids[0]].text)}</span>`),"sh",6):""}</div>
 <div style="overflow-x:auto"><table><thead><tr><th></th>${diff.map(([k,o])=>`<th>${esc(o.name)}</th>`).join("")}${rcols.map(c=>`<th>${colHead(c)}</th>`).join("")}</tr></thead><tbody>${ids.map(i=>`<tr><th><span class="src" onclick="openDetail('${i}')">${esc(ROW[i]?ROW[i].name:D.details[i].name)}</span> <span class="mut">${esc(PN(D.details[i].paper))}</span></th>${diff.map(([k,o])=>`<td>${esc(o.v[i]?o.v[i].text:"")}</td>`).join("")}${rcols.map(c=>`<td>${cell(c[1],i,c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
 const cnt={};ids.forEach(i=>[...(D.details[i].claims||[])].forEach(c=>cnt[c]=(cnt[c]||0)+1));const linked=Object.entries(cnt).filter(([c,n])=>n>=2).map(([c])=>claimLine(c));
 const xsel=xs.length>1?`<label class="mut">x <select onchange="S.x=this.value;renderRight()">${xs.map(x=>`<option value="${esc(x.k)}" ${x.k===S.x?"selected":""}>${esc(x.name)}</option>`).join("")}</select></label>`:"";
 const colsMore=nAll>6?`<div class="more" onclick="S.open.${S.open.has("rcols")?"delete":"add"}('rcols');renderRight()">${S.open.has("rcols")?"fewer results":`+${nAll-6} more results`}</div>`:"";
 return `<h2>${ids.length} selected</h2>${xsel}${plot}${table}${colsMore}<div class="part"><h3>Claims on two or more of them</h3>${lim(linked,"sel-c",3)||'<div class="mut">none</div>'}</div>`}
function plotSvg(pts,curves,xn,yn){if(!pts.length&&!curves.length)return '<div class="mut">nothing to plot: no shared condition with numbers, or no numeric result</div>';
 const W=620,H=300,ml=64,mb=44,mt=12,mr=16;const all=[...pts.map(p=>[p.x,p.y]),...curves.flatMap(c=>c.r.curve.points)];const X=all.map(a=>a[0]),Y=all.map(a=>a[1]);
 const lx=X.every(v=>v>0)&&Math.max(...X)/Math.min(...X)>50,ly=Y.every(v=>v>0)&&Math.max(...Y)/Math.min(...Y)>50;const tx=v=>lx?Math.log10(v):v,ty=v=>ly?Math.log10(v):v;
 let x0=Math.min(...X.map(tx)),x1=Math.max(...X.map(tx)),y0=Math.min(...Y.map(ty)),y1=Math.max(...Y.map(ty));if(x0===x1){x0-=1;x1+=1}if(y0===y1){y0-=Math.abs(y0)*.1||1;y1+=Math.abs(y1)*.1||1}
 if(!ly&&y0>0&&y0<(y1-y0))y0=0;const sx=v=>ml+(W-ml-mr)*(tx(v)-x0)/(x1-x0),sy=v=>H-mb-(H-mb-mt)*(ty(v)-y0)/(y1-y0);
 const tk=(a,b,lg)=>{const n=5;return [...Array(n+1)].map((_,i)=>a+(b-a)*i/n).map(v=>lg?10**v:v)};const fm=v=>Math.abs(v)>=1e4||(Math.abs(v)<1e-2&&v!==0)?v.toExponential(1):+v.toPrecision(3);
 const papers=[...new Set([...pts.map(p=>D.details[p.i].paper),...curves.map(c=>D.details[c.i].paper)])];const modes=[...new Set([...pts.map(p=>p.r.mode),...curves.map(c=>c.r.mode)].filter(m=>m==="in_situ"||m==="ex_situ"))];
 const mk=(p,x,y)=>p.r.mode==="in_situ"?`<circle cx="${x}" cy="${y}" r="5" fill="none" stroke="${col(D.details[p.i].paper)}" stroke-width="2"><title>${esc(p.name||ROW[p.i]?.name||"")}</title></circle>`:`<circle cx="${x}" cy="${y}" r="5" fill="${col(D.details[p.i].paper)}"><title>${esc(ROW[p.i]?ROW[p.i].name:"")}: ${fm(p.x)}, ${fm(p.y)}</title></circle>`;
 const svg=`<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px" role="img" aria-label="${esc(yn)} against ${esc(xn)}"><line class="ax" x1="${ml}" y1="${H-mb}" x2="${W-mr}" y2="${H-mb}"/><line class="ax" x1="${ml}" y1="${mt}" x2="${ml}" y2="${H-mb}"/>
 ${tk(x0,x1,lx).map(v=>`<text x="${sx(v)}" y="${H-mb+18}" text-anchor="middle">${fm(v)}</text>`).join("")}${tk(y0,y1,ly).map(v=>`<text x="${ml-6}" y="${sy(v)+4}" text-anchor="end">${fm(v)}</text>`).join("")}
 <text x="${(W+ml)/2}" y="${H-6}" text-anchor="middle">${esc(xn)}${lx?" (log)":""}</text><text x="14" y="${(H-mb)/2}" text-anchor="middle" transform="rotate(-90 14 ${(H-mb)/2})">${esc(yn)}${ly?" (log)":""}</text>
 ${curves.map(c=>`<polyline fill="none" stroke="${col(D.details[c.i].paper)}" stroke-width="2" ${c.r.mode==="in_situ"?'stroke-dasharray="5 3"':""} points="${c.r.curve.points.map(a=>sx(a[0]).toFixed(1)+","+sy(a[1]).toFixed(1)).join(" ")}"><title>${esc(c.name)}</title></polyline>`).join("")}
 ${pts.map(p=>mk(p,sx(p.x),sy(p.y))).join("")}</svg>`;
 const lg=`<div class="lg">${papers.map(k=>`<span><span style="color:${col(k)}">●</span> ${esc(PN(k))}</span>`).join("")}${modes.includes("ex_situ")?"<span>● filled, solid line: ex situ</span>":""}${modes.includes("in_situ")?"<span>○ open, dashed line: in situ</span>":""}</div>`;
 return svg+lg}
function renderRight(){const p=S.panel;$("#right").innerHTML=p.type==="detail"?detailPanel(p.id):p.type==="comparison"?compPanel(p.id):p.type==="source"?sourcePanel(p.id):p.type==="selected"?selPanel():
 `<h2>PSED pilot</h2><div class="line mut">Three papers on conformal ALD read into one knowledge base. Filter at the top, tick experiments to set them side by side, click a name for its detail, a group header for the authors' comparison, a source for the passage or figure.</div>`}
function render(){bar();$("#left").innerHTML=left();renderRight()}
render();
</script></body></html>"""


if __name__ == "__main__":
    data, imgs = build()
    out = HERE / "reports/pilot.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")).replace("__IMGS__", json.dumps(imgs)), encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB; {len(data['rows'])} rows, {len(data['groups'])} groups, {len(data['claims'])} claims, {len(data['sources'])} sources")
