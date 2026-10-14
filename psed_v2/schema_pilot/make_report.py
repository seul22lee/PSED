#!/usr/bin/env python3
"""Writes schema_pilot/reports/pilot.html (gitignored with reports/): the five tables of the three pilot papers, browsable.

    python3 psed_v2/schema_pilot/make_report.py

Self-contained (data as JSON, figure crops as JPEG data URLs); opens offline.
"""
import base64, csv, html, io, json, re, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
from convert import PAPERS, COLS
import validate, lists as L

E = html.escape
V1 = Path("/tmp/claude-1040/-home-ftk3187-github-PSED/87cc3933-a487-425d-a5ee-9c146d97c52c/scratchpad/q7/v1")
V1_FALLBACK = {"10.1039_d0cp03358h": {"source_entities": 70, "experimental_cases": 39, "plot_series": 70, "results": 0, "assertions": 976, "points": 1221},
               "10.1021_acs.chemmater.2c01154": {"source_entities": 51, "experimental_cases": 34, "plot_series": 51, "results": 51, "assertions": 173, "points": 538}}
V1_MISSES = {
    "10.1039_d0cp03358h": [
        ("missed", "all 142 result cells of Table 1 (thicknesses, both growths per cycle, PD50, x̃ at one half, both front slopes, R²): v1 keeps the rows in a diagnostic file, with the slope signs lost, but no result reaches its tables"),
        ("missed", "the sticking values the paper derives (c of TMA 0.004 over samples 2, 4, 8, 12; c of water 0.0003 from sample 14) and the Table 2 literature values"),
        ("missed", "most model inputs of Fig. 10 (sticking 0.012, adsorption constant, desorption, site density); v1 has only the pressures and the saturation growth"),
        ("wrong", "sample identity: 39 'cases', one per curve, so the same three samples of Fig. 9a, 9b and 9c count three times; the paper has 16 samples plus one AFM sample"),
        ("wrong", "the nine scans of Fig. 8a merged into four series; made-up numeric points on the unscaled sketch of Fig. 3"),
        ("v1 has more", "digitized points for every curve (1221); the pilot imports them only where a check against the figure accepts them"),
    ],
    "10.1021_acs.chemmater.2c01154": [
        ("wrong", "the x axis of Fig. 4 read as a partial pressure; it is the H2 flow ratio"),
        ("wrong", "Fig. 8: a '35 °C' row (it is 50 °C), 'above the detection limit' stored as the number 5000, and two cells that contradict the text (100 against 15 Ω cm; 800 against 220)"),
        ("missed", "Fig. 7b (all 32 growth-per-cycle cells), the wafer map of Fig. 1c with its 3.3% spread, Tables 1 and 2, the cycle recipe"),
        ("missed", "the H2S plasma as co-reactant (v1 lists H2 only), the precursor, binding energies, Hall results and the resistivities stated in the text"),
        ("missed", "that the 32 runs are one temperature × H2-ratio grid seen by four figures; v1 has one 'experiment' per curve and no named samples"),
        ("v1 has more", "full Raman spectra and the Fig. 7a curves as points"),
    ],
    "10.1116_6.0003182": [("none", "v1 has no output for this paper")],
}
CHAINS = {
    "10.1039_d0cp03358h": [("yim20:8", "sample 8: 500 cycles in a 500 nm channel (Table 1, Series B)"), ("cond", "its conditions: pulse and purge times, cycles, 300 °C (paper-wide)"),
                           ("yim20:F9c-H500", "Fig. 9c: its normalized profile (points from cases/points.json)"), ("yim20:v211", "x̃ at one half read from that profile"),
                           ("yim20:v069", "the front slope dθ/dx̃ fitted by the authors (Table 1)"), ("yim20:v177", "c of TMA = 13.9·slope², averaged over samples 2, 4, 8, 12 (a group)")],
    "10.1021_acs.chemmater.2c01154": [("mat22:uT150R080", "one grid cell: 150 °C, H2 flow ratio 0.80"), ("cond", "its conditions: temperature, cycles, flows (paper-wide recipe greyed)"),
                                      ("mat22:s2_map", "Fig. 2: the crystallinity map of the grid"), ("mat22:v026", "this cell: crystalline"), ("mat22:v058", "Fig. 4: S/Mo 1.9"),
                                      ("mat22:v090", "Fig. 7b: growth per cycle 1.30 Å (read against the colour bar)"), ("mat22:v122", "Fig. 8: resistivity 0.4 Ω cm")],
    "10.1116_6.0003182": [("gre23:120", "the 120 °C run (two compacts and a resistivity prism as pieces)"), ("cond", "its conditions: holds of 1920 s at about 9 Torr per reactant, 20 cycles"),
                          ("gre23:s2a", "Fig. 2a: chamber pressure trace of the run"), ("gre23:v069", "pressure rise during a hold, read from Fig. 3a"),
                          ("gre23:v018", "mass gain (Table I)"), ("gre23:v020", "growth per cycle inside the compact, calculated from the mass gain"),
                          ("gre23:s6d_Zn", "Fig. 6d: Zn EDS line scan through the thickness"), ("gre23:v083", "coated aspect ratio = the full 7800 (no front)")],
}


def crop(pid, fig):
    try:
        st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
        cap = next(c for c in st["captions"] if c["kind"] == "figure" and str(c["number"]) == str(fig))
    except (StopIteration, FileNotFoundError):
        return ""
    out = []
    for rel in cap["images"][:2]:
        im = Image.open(V2 / f"ingest/final/{pid}/{rel}").convert("RGB")
        if im.width > 700:
            im = im.resize((700, round(im.height * 700 / im.width)), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, "JPEG", quality=72, optimize=True)
        out.append("data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode())
    return out


def checklist(pid):
    rows = []
    for line in (HERE / pid / "checklist.md").read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 6 and p[1] and p[1] not in ("Core item",) and not p[1].startswith("---"):
            rows.append(p[1:5])
    return rows


DATA = {}
for pid, key in PAPERS.items():
    T = {t: list(csv.DictReader((HERE / pid / f"{t}.csv").open(encoding="utf-8"))) for t in COLS}
    n, err = validate.check(pid)
    figs = sorted({r["figure"] for r in T["series"] if r["figure"] and not r["figure"].startswith("Table")}, key=lambda f: (len(f), f))
    v1c = dict(V1_FALLBACK.get(pid, {}))
    cj = V1 / pid / "counts.json"
    if cj.exists():
        c = json.loads(cj.read_text()); v1c.update({k: c[k] for k in ("source_entities", "experimental_cases", "plot_series") if k in c})
    DATA[pid] = dict(key=key, title=T["paper"][0].get("topic", ""), year=T["paper"][0].get("year", ""), tables=T, counts=n, errors=err,
                     figs={f: crop(pid, f) for f in figs}, checklist=checklist(pid), v1=v1c, v1misses=V1_MISSES[pid], chain=CHAINS[pid],
                     npoints=sum(1 for r in T["series"] if r["points"]), nv1=sum(1 for r in T["series"] if r["points_source"].startswith("v1")))

page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Schema pilot</title><style>
:root{--surface:#fcfcfb;--panel:#f3f2ee;--text:#1f1f1c;--text2:#55544e;--line:#d9d7cf;--accent:#184f95;--ok:#dcefe3;--okb:#1b8a55;--warn:#fbeccb;--no:#eeedea;--bad:#f8d9d4;--sel:#e3ecf8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4;--ok:#183526;--okb:#5fd39a;--warn:#3a2f14;--no:#262624;--bad:#4a1f1a;--sel:#1f2d42}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4;--ok:#183526;--okb:#5fd39a;--warn:#3a2f14;--no:#262624;--bad:#4a1f1a;--sel:#1f2d42}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1500px;margin:0 auto;padding:20px 16px 48px}h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:30px 0 8px;padding-top:14px;border-top:2px solid var(--line)}h3{font-size:15px;margin:18px 0 6px}
.sub{color:var(--text2);max-width:100ch}.diagram svg{width:100%;max-width:820px;height:auto}.box{fill:var(--panel);stroke:var(--line)}.bt{fill:var(--text);font-size:13px;font-weight:600}.bs{fill:var(--text2);font-size:11px}.ar{stroke:var(--text2);stroke-width:1.5;fill:none;marker-end:url(#a)}
table{border-collapse:collapse;font-size:12.5px;width:100%}th,td{text-align:left;vertical-align:top;padding:4px 8px;border-bottom:1px solid var(--line)}th{color:var(--text2);font-weight:600}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.tabs button{font:inherit;padding:5px 12px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);cursor:pointer;font-weight:600}.tabs button.on{background:var(--accent);color:var(--surface)}
.grid{display:grid;grid-template-columns:minmax(260px,340px) minmax(0,1fr);gap:16px}@media (max-width:900px){.grid{grid-template-columns:1fr}}
.tree{max-height:640px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:8px;background:var(--panel)}.tree ul{list-style:none;margin:0;padding-left:16px}.tree>ul{padding-left:0}
.tree li{margin:1px 0}.node{cursor:pointer;border-radius:4px;padding:1px 4px}.node:hover,.node.on{background:var(--sel)}.k{font-size:10.5px;color:var(--text2);border:1px solid var(--line);border-radius:6px;padding:0 4px;margin-left:4px}
.det{border:1px solid var(--line);border-radius:8px;padding:12px 14px;min-height:300px}.det h4{margin:12px 0 4px}.grey td{color:var(--text2);opacity:.7}
.lk{color:var(--accent);cursor:pointer;text-decoration:underline}.pid{font:11px ui-monospace,monospace;color:var(--text2)}code{font:12px ui-monospace,monospace;background:var(--panel);padding:1px 4px;border-radius:3px}
.figs{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}@media (max-width:900px){.figs{grid-template-columns:1fr}}.figs img{max-width:100%;background:#fff;border-radius:4px}
svg.pl{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:var(--surface)}.st-found{background:var(--ok)}.st-not-stated{background:var(--no)}.st-not-in-document-SI{background:var(--warn)}.st-not-read{background:var(--bad)}
.cnt{display:flex;gap:10px;flex-wrap:wrap}.c{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 12px}.c b{font-size:18px;display:block}.okv{color:var(--okb);font-weight:700}.badv{color:#c0392b;font-weight:700}
.chain{display:flex;flex-wrap:wrap;gap:6px;align-items:stretch}.step{border:1px solid var(--line);border-radius:8px;padding:6px 10px;background:var(--panel);max-width:250px;font-size:12.5px}.step .lk{font-weight:600}.arrow{align-self:center;color:var(--text2)}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:900px){.cmp{grid-template-columns:1fr}}.tag{font-size:11px;border-radius:6px;padding:0 6px;border:1px solid var(--line)}
</style></head><body><main>
<h1>Schema pilot: five tables on three papers</h1>
<p class="sub">Each paper read by hand into five tables. Points are only those read by eye in cases/points.json or v1 points accepted after a check against the figure; evidence is a locator, not copied text. Click a sample, a series or a value.</p>
<div class="diagram"><svg viewBox="0 0 820 230"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="currentColor"/></marker></defs>
<rect class="box" x="10" y="85" width="150" height="60" rx="8"/><text class="bt" x="85" y="110" text-anchor="middle">paper</text><text class="bs" x="85" y="128" text-anchor="middle">id, year, topic</text>
<rect class="box" x="230" y="70" width="190" height="90" rx="8"/><text class="bt" x="325" y="95" text-anchor="middle">sample</text><text class="bs" x="325" y="113" text-anchor="middle">run, piece, channel, reference,</text><text class="bs" x="325" y="128" text-anchor="middle">group (members), model_run;</text><text class="bs" x="325" y="143" text-anchor="middle">parent; chemistry; structure</text>
<rect class="box" x="500" y="10" width="300" height="55" rx="8"/><text class="bt" x="650" y="32" text-anchor="middle">condition</text><text class="bs" x="650" y="50" text-anchor="middle">sample or * · kind · quantity{qualifiers} · value</text>
<rect class="box" x="500" y="88" width="300" height="55" rx="8"/><text class="bt" x="650" y="110" text-anchor="middle">series</text><text class="bs" x="650" y="128" text-anchor="middle">sample · kind · figure, panel · method · x, y (z) · points</text>
<rect class="box" x="500" y="166" width="300" height="55" rx="8"/><text class="bt" x="650" y="188" text-anchor="middle">value</text><text class="bs" x="650" y="206" text-anchor="middle">sample · from_series · quantity · data_kind · relation</text>
<path class="ar" d="M230 115 L160 115"/><path class="ar" d="M500 37 L420 95"/><path class="ar" d="M500 115 L420 115"/><path class="ar" d="M500 190 L420 135"/><path class="ar" d="M650 166 L650 143"/>
<path class="ar" d="M420 80 C 460 40, 380 30, 360 70"/><text class="bs" x="430" y="36">parent / members</text></svg></div>
<div id="summary"></div>
<div class="tabs" id="tabs"></div><div id="paper"></div>
</main><script>
const D=__DATA__;const LISTS=__LISTS__;
const $=id=>document.getElementById(id);const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let P=null,T=null;
function summary(){let h='<table><tr><th>Paper</th><th>sample</th><th>condition</th><th>series</th><th>value</th><th>series with points</th><th>validator</th></tr>';
 for(const [pid,d] of Object.entries(D)){h+=`<tr><td>${esc(d.key)} <span class="pid">${pid}</span></td><td>${d.counts.sample}</td><td>${d.counts.condition}</td><td>${d.counts.series}</td><td>${d.counts.value}</td><td>${d.npoints} (${d.nv1} from v1)</td><td>${d.errors.length?'<span class="badv">'+d.errors.length+' problems</span>':'<span class="okv">pass</span>'}</td></tr>`}
 $("summary").innerHTML=h+'</table>';}
function tabs(){$("tabs").innerHTML=Object.entries(D).map(([pid,d])=>`<button data-p="${pid}">${esc(d.key)} · ${esc(d.year)}</button>`).join("");
 $("tabs").onclick=e=>{const b=e.target.closest("button");if(b) show(b.dataset.p)};}
const S=id=>T.sample.find(s=>s.sample_id===id),SE=id=>T.series.find(s=>s.series_id===id),V=id=>T.value.find(v=>v.value_id===id);
function lk(kind,id,txt){return `<span class="lk" data-k="${kind}" data-id="${esc(id)}">${esc(txt??id)}</span>`}
function tree(){const kids={},inGroup=new Set();for(const s of T.sample){if(s.parent_sample)(kids[s.parent_sample]=kids[s.parent_sample]||[]).push(s);}
 const groups=T.sample.filter(s=>s.kind==="group");for(const g of groups)for(const m of g.members.split(";"))inGroup.add(m);
 const li=s=>`<li><span class="node" data-id="${esc(s.sample_id)}">${esc(s.sample_id.split(":")[1])}<span class="k">${esc(s.kind)}</span></span>${kids[s.sample_id]?'<ul>'+kids[s.sample_id].map(li).join("")+'</ul>':''}</li>`;
 const roots=T.sample.filter(s=>!s.parent_sample&&s.kind!=="group");
 let h='<ul>'+roots.filter(s=>s.kind!=="model_run").map(li).join("")+'</ul>';
 h+='<h4>Groups</h4><ul>'+groups.map(g=>`<li><span class="node" data-id="${esc(g.sample_id)}">${esc(g.sample_id.split(":")[1])}<span class="k">${g.members.split(";").length} members</span></span><div class="pid">${esc(g.note)}</div></li>`).join("")+'</ul>';
 h+='<h4>Model runs</h4><ul>'+roots.filter(s=>s.kind==="model_run").map(li).join("")+'</ul>';return h;}
function rowsTable(rows,cols,grey){return rows.length?'<table><tr>'+cols.map(c=>`<th>${c[0]}</th>`).join("")+'</tr>'+rows.map(r=>`<tr class="${grey&&grey(r)?'grey':''}">`+cols.map(c=>`<td>${c[1](r)}</td>`).join("")+'</tr>').join("")+'</table>':'<p class="pid">none</p>'}
const qv=r=>(r.quantity==="other"?'other: '+esc(r.label_as_printed):esc(r.quantity))+(r.qualifiers?' <code>{'+esc(r.qualifiers)+'}</code>':'');
const val=r=>esc(r.value||((r.value_min||r.value_max)?r.value_min+' to '+r.value_max:''))+(r.censor?' '+esc(r.censor):'')+' '+esc(r.unit);
function groupsOf(id){return T.sample.filter(g=>g.kind==="group"&&g.members.split(";").includes(id)).map(g=>g.sample_id)}
function sampleView(id){const s=S(id);if(!s)return;const ids=[id,...groupsOf(id)];
 const cond=T.condition.filter(c=>ids.includes(c.sample_id)||c.sample_id==="*");
 let h=`<h3>${esc(id)} <span class="k">${esc(s.kind)}</span></h3><p>${esc([s.material,s.precursor&&('from '+s.precursor),s.coreactant&&('and '+s.coreactant),s.process_mode,s.reactor].filter(Boolean).join(' · '))}</p><p class="pid">${esc([s.structure_class,s.structure_dims,s.width_kind&&('width '+s.width_kind)].filter(Boolean).join(' · '))}${s.parent_sample?' · parent '+lk('s',s.parent_sample):''}${s.members?' · members: '+s.members.split(";").map(m=>lk('s',m,m.split(':')[1])).join(', '):''}${groupsOf(id).length?' · in groups: '+groupsOf(id).map(g=>lk('s',g,g.split(':')[1])).join(', '):''}</p><p class="pid">${esc(s.note)} ${esc(s.evidence)}</p>`;
 h+='<h4>Conditions (paper-wide * rows greyed; group rows marked)</h4>'+rowsTable(cond,[["kind",r=>esc(r.kind)],["quantity",qv],["value",val],["data",r=>esc(r.data_kind)],["of",r=>r.sample_id==="*"?'*':r.sample_id===id?'this':lk('s',r.sample_id,r.sample_id.split(':')[1])],["evidence",r=>esc(r.evidence)]],r=>r.sample_id==="*");
 h+='<h4>Series</h4>'+rowsTable(T.series.filter(r=>ids.includes(r.sample_id)),[["series",r=>lk('se',r.series_id)],["kind",r=>esc(r.kind)],["figure",r=>esc(r.figure+r.panel)],["method",r=>esc(r.method)],["x → y",r=>esc((r.x_id==='other'?r.x_label:r.x_id)+' → '+(r.y_id==='other'?r.y_label:r.y_id))],["points",r=>r.points?'yes':'']]);
 h+='<h4>Values</h4>'+rowsTable(T.value.filter(r=>ids.includes(r.sample_id)),[["value",r=>lk('v',r.value_id)],["quantity",qv],["value",val],["data",r=>esc(r.data_kind)],["from series",r=>r.from_series?lk('se',r.from_series):''],["of",r=>r.sample_id===id?'this':lk('s',r.sample_id,r.sample_id.split(':')[1])]]);
 $("det").innerHTML=h;}
function plot(pts,xl,yl){if(!pts||!pts.length)return '';const w=520,h=300,L=56,R=12,Tp=12,B=40;const xs=pts.map(p=>+p[0]),ys=pts.map(p=>+p[1]);let x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(0,...ys),y1=Math.max(...ys);if(x1===x0)x1=x0+1;if(y1===y0)y1=y0+1;
 const X=v=>L+(v-x0)/(x1-x0)*(w-L-R),Y=v=>h-B-(v-y0)/(y1-y0)*(h-Tp-B);let s=`<svg class="pl" viewBox="0 0 ${w} ${h}"><line x1="${L}" x2="${w-R}" y1="${h-B}" y2="${h-B}" stroke="currentColor" opacity=".4"/><line x1="${L}" x2="${L}" y1="${Tp}" y2="${h-B}" stroke="currentColor" opacity=".4"/>`;
 for(const v of [x0,(x0+x1)/2,x1])s+=`<text x="${X(v)}" y="${h-B+14}" font-size="10" text-anchor="middle" fill="currentColor">${+v.toPrecision(3)}</text>`;for(const v of [y0,(y0+y1)/2,y1])s+=`<text x="${L-4}" y="${Y(v)+3}" font-size="10" text-anchor="end" fill="currentColor">${+v.toPrecision(3)}</text>`;
 s+=`<polyline fill="none" stroke="#2a78d6" stroke-width="1.5" points="${pts.map(p=>X(+p[0])+','+Y(+p[1])).join(' ')}"/>`+pts.map(p=>`<circle cx="${X(+p[0])}" cy="${Y(+p[1])}" r="2.6" fill="#2a78d6"/>`).join("");
 s+=`<text x="${(L+w)/2}" y="${h-6}" font-size="11" text-anchor="middle" fill="currentColor">${esc(xl)}</text><text transform="translate(12 ${(Tp+h-B)/2}) rotate(-90)" font-size="11" text-anchor="middle" fill="currentColor">${esc(yl)}</text></svg>`;return s;}
function seriesView(id){const r=SE(id);if(!r)return;const imgs=(D[P].figs[r.figure]||[]);const pts=r.points?JSON.parse(r.points):null;
 let h=`<h3>${esc(id)} <span class="k">${esc(r.kind)}</span> <span class="k">${esc(r.data_kind)}</span></h3><p>Fig. ${esc(r.figure)}${esc(r.panel)} · method <code>${esc(r.method)}</code> · sample ${r.sample_id?lk('s',r.sample_id):'none (cited)'} ${r.link_status?'· link '+esc(r.link_status):''}</p>`;
 h+=`<p>x: <code>${esc(r.x_id)}</code>${r.x_qualifiers?' <code>{'+esc(r.x_qualifiers)+'}</code>':''} ${esc(r.x_label)} · y: <code>${esc(r.y_id)}</code>${r.y_qualifiers?' <code>{'+esc(r.y_qualifiers)+'}</code>':''} ${esc(r.y_label)}${r.z_id?' · z: <code>'+esc(r.z_id)+'</code> '+esc(r.z_label):''}</p>`;
 h+=`<div class="figs"><div>${imgs.map(u=>`<img src="${u}" alt="Fig. ${esc(r.figure)} crop">`).join("")||'<p class="pid">no crop (table or not found)</p>'}</div><div>${pts?plot(pts,r.x_label||r.x_id,r.y_label||r.y_id)+`<p class="pid">${pts.length} points · source: ${esc(r.points_source)}</p>`:'<p class="pid">points not read</p>'}</div></div>`;
 h+=`<p class="pid">${esc(r.note)} · ${esc(r.evidence)}${r.reused_from?' · reused from '+esc(r.reused_from):''}</p>`;
 h+='<h4>Values from this series</h4>'+rowsTable(T.value.filter(v=>v.from_series===id),[["value",v=>lk('v',v.value_id)],["quantity",qv],["value",val],["data",v=>esc(v.data_kind)],["relation",v=>esc(v.relation)]]);$("det").innerHTML=h;}
function valueView(id){const v=V(id);if(!v)return;$("det").innerHTML=`<h3>${esc(id)} <span class="k">${esc(v.data_kind)}</span></h3><table>
 <tr><th>quantity</th><td>${qv(v)}</td></tr><tr><th>value</th><td>${val(v)}</td></tr><tr><th>sample</th><td>${v.sample_id?lk('s',v.sample_id):'none (literature)'}</td></tr>
 <tr><th>from series</th><td>${v.from_series?lk('se',v.from_series):'—'}</td></tr><tr><th>method</th><td>${esc(v.method)}</td></tr><tr><th>relation</th><td>${esc(v.relation)}</td></tr><tr><th>regime</th><td>${esc(v.regime)}</td></tr>
 <tr><th>cited</th><td>${esc(v.cited_ref)}</td></tr><tr><th>evidence (locator)</th><td>${esc(v.evidence)}</td></tr><tr><th>note</th><td>${esc(v.note)}</td></tr></table>`;}
function open(kind,id){document.querySelectorAll(".node").forEach(n=>n.classList.toggle("on",n.dataset.id===id));if(kind==='s')sampleView(id);else if(kind==='se')seriesView(id);else valueView(id);}
function show(pid){P=pid;const d=D[pid];T=d.tables;document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.p===pid));
 const chain=d.chain.map(([id,txt])=>`<div class="step">${id==='cond'?'<b>conditions</b>':lk(id.includes(':v')?'v':(SE(id)?'se':'s'),id)}<br>${esc(txt)}</div>`).join('<span class="arrow">→</span>');
 const cl='<table><tr><th>Core item</th><th>Status</th><th>Ids</th><th>Note</th></tr>'+d.checklist.map(r=>`<tr><td>${esc(r[0])}</td><td class="st-${r[1].replace(/[() ]+/g,'-').replace(/-$/,'')}">${esc(r[1])}</td><td class="pid">${esc(r[2])}</td><td>${esc(r[3])}</td></tr>`).join("")+'</table>';
 const v1=Object.keys(d.v1).length?'<table>'+Object.entries(d.v1).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join("")+'</table>':'<p>no v1 output</p>';
 const pc=`<table><tr><td>samples (incl. groups, model runs)</td><td>${d.counts.sample}</td></tr><tr><td>conditions</td><td>${d.counts.condition}</td></tr><tr><td>series</td><td>${d.counts.series}</td></tr><tr><td>values</td><td>${d.counts.value}</td></tr><tr><td>series with points</td><td>${d.npoints}</td></tr></table>`;
 $("paper").innerHTML=`<h2>${esc(d.key)} <span class="pid">${pid}</span></h2><p class="sub">${esc(d.title)}</p>
 <h3>Worked chain</h3><div class="chain">${chain}</div>
 <h3>Samples and details</h3><div class="grid"><div class="tree" id="tree">${tree()}</div><div class="det" id="det"><i>Click a sample, a series or a value.</i></div></div>
 <h3>Checklist</h3>${cl}
 <h3>v1 against the pilot</h3><div class="cmp"><div><h4>v1 counts</h4>${v1}</div><div><h4>pilot counts</h4>${pc}</div></div>
 <table><tr><th></th><th>What v1 missed or got wrong</th></tr>${d.v1misses.map(([k,t])=>`<tr><td><span class="tag">${esc(k)}</span></td><td>${esc(t)}</td></tr>`).join("")}</table>
 ${d.errors.length?'<h3>Validator problems</h3><ul>'+d.errors.map(e=>'<li>'+esc(e)+'</li>').join('')+'</ul>':''}`;
 $("tree").onclick=e=>{const n=e.target.closest(".node");if(n)open('s',n.dataset.id)};}
document.addEventListener("click",e=>{const l=e.target.closest(".lk");if(l)open(l.dataset.k,l.dataset.id)});
summary();tabs();show(Object.keys(D)[0]);
</script></body></html>"""
page = page.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__LISTS__", json.dumps({"methods": L.METHODS, "quantities": L.QUANTITIES}))
(HERE / "reports").mkdir(exist_ok=True)
(HERE / "reports" / "pilot.html").write_text(page, encoding="utf-8")
print(HERE / "reports" / "pilot.html", f"{len(page) / 1e6:.2f} MB")
