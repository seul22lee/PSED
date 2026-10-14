#!/usr/bin/env python3
"""Exploration: the matrix view of reports/pilot.html (report.py runs this file and takes `page`), two views of the 58 in-scope papers with a PDF:
"Quantities" (quantity_matrix.csv, one row per paper) and "Papers × cases" (paper_case.csv, one column per case).

    (no command of its own: python3 psed_v2/pilot/report.py)

Self-contained (data embedded as JSON, no external resources).
Quantity cells: hand-read value; not read by hand (keyword hit or figure-inventory rule); "no". Case cells: used; candidate,
not used; empty. The S1/S2/S6 counts come from the usable_for column; the case counts from paper_case.csv.
openCase(k) and show(paper_id) open a case's list or a paper (used by the cases view).
"""
import csv, html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = list(csv.DictReader((HERE / "quantity_matrix.csv").open(encoding="utf-8")))
cols = [c for c in rows[0] if c not in ("paper_id", "year")]
pc = {r["paper_id"]: r for r in csv.DictReader((HERE / "paper_case.csv").open(encoding="utf-8"))}
src = (HERE / "paper_case.py").read_text(encoding="utf-8")
CASES = eval(src[src.index("COLS = [") + len("COLS = "):src.index("]\n\n\ndef figlab") + 1])     # the column list only, no run
man = {r["paper_id"]: r for r in csv.DictReader((HERE.parent / "corpus/manifest.csv").open(encoding="utf-8"))}
for r in rows:
    m = man.get(r["paper_id"], {})
    r["_title"] = m.get("title", "")
    a = (m.get("authors") or "").split(";")[0].strip()
    r["_who"] = f"{a.split(' ')[-1] if a else r['paper_id']} {r['year']}"
    r["_cases"] = {k: pc.get(r["paper_id"], {}).get(k, "") for k, _ in CASES}
    r["_none"] = pc.get(r["paper_id"], {}).get("in_no_case", "")
COUNTS = {
    "S1": ("one method for sticking", lambda r: "S1" in r.get("usable_for", "")),
    "S1 slope": ("rectangular channel, slope method valid", lambda r: "S1 slope" in r.get("usable_for", "")),
    "S1 model": ("needs a geometry model", lambda r: "S1 model" in r.get("usable_for", "")),
    "S2": ("exposure of the limiting step against EAR", lambda r: "S2" in r.get("usable_for", "")),
    "S6": ("depth over channel height across scales", lambda r: "S6" in r.get("usable_for", "")),
}
counts = [(k, d, sum(1 for r in rows if f(r))) for k, (d, f) in COUNTS.items()]
ccounts = [(k, t, sum(r["_cases"][k].startswith("used") for r in rows), sum(r["_cases"][k].startswith(("candidate", "excluded")) for r in rows)) for k, t in CASES]
hand = sum(1 for r in rows if r["read_by_hand"] == "yes")
ppt = sum(1 for r in rows if r["read_by_hand"] == "yes" and r["exposure_or_pp_and_pulse"].startswith("pp × time"))
lim = sum(1 for r in rows if r.get("limiting_step_exposure") == "yes")
none = sum(1 for r in rows if r["_none"] == "yes")
E = html.escape

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quantity matrix</title><style>
:root{{--surface:#fcfcfb;--panel:#f3f2ee;--text:#1f1f1c;--text2:#55544e;--line:#d9d7cf;--accent:#184f95;--hand:#dcefe3;--handb:#1b8a55;--kw:#fbeccb;--kwb:#b07a00;--no:#eeedea;--used:#cfe0f5;--cand:#fbeccb}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4;--hand:#183526;--handb:#5fd39a;--kw:#3a2f14;--kwb:#e5b54a;--no:#262624;--used:#1c3150;--cand:#3a2f14}}}}
:root[data-theme="dark"]{{--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--accent:#9ec5f4;--hand:#183526;--handb:#5fd39a;--kw:#3a2f14;--kwb:#e5b54a;--no:#262624;--used:#1c3150;--cand:#3a2f14}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--text);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1800px;margin:0 auto;padding:20px 16px 48px}}h1{{font-size:24px;margin:0 0 4px}}.sub{{color:var(--text2);max-width:110ch;margin:0 0 14px}}
.tabs{{display:flex;gap:6px;margin:0 0 14px}}.tabs button{{font-weight:600}}.tabs button.on{{background:var(--accent);color:var(--surface);border-color:var(--accent)}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}}.cnt{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 14px;min-width:150px}}
.cnt b{{display:block;font-size:22px}}.cnt span{{color:var(--text2);font-size:12px}}.cc{{min-width:110px;cursor:pointer}}.cc b{{font-size:18px}}
.bar{{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin:0 0 10px}}label{{font-size:12px;color:var(--text2);display:grid;gap:2px}}
select,input{{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--text)}}
button{{font:inherit;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--text);cursor:pointer}}
.legend{{display:flex;gap:14px;font-size:12px;color:var(--text2);margin:0 0 8px;flex-wrap:wrap}}.sw{{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:4px}}
.tw{{overflow:auto;max-height:70vh;border:1px solid var(--line);border-radius:8px}}table{{border-collapse:collapse;font-size:12px}}
th,td{{padding:4px 6px;border-bottom:1px solid var(--line);border-right:1px solid var(--line);text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:var(--panel);color:var(--text2);font-weight:600;z-index:1;writing-mode:vertical-rl;transform:rotate(180deg);height:150px;white-space:nowrap}}#clist{{margin:0 0 12px}}
th.ch{{cursor:pointer}}th.ch:hover,th.ch.on{{color:var(--accent)}}
th.p{{writing-mode:horizontal-tb;transform:none;height:auto;left:0;z-index:2}}td.p{{position:sticky;left:0;background:var(--surface);white-space:nowrap;font-weight:600}}
td.c{{max-width:120px;min-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}td.h{{background:var(--hand)}}td.k{{background:var(--kw)}}td.n{{background:var(--no);color:var(--text2)}}
td.u{{background:var(--used)}}td.a{{background:var(--cand)}}td.e{{background:var(--surface)}}td.x{{text-align:center;font-weight:600}}
tr{{cursor:pointer}}tr.on td{{outline:2px solid var(--accent);outline-offset:-2px}}.pid{{display:block;font:11px ui-monospace,monospace;color:var(--text2);font-weight:400}}
.det{{margin:14px 0 0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 16px}}.det dl{{display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:4px 14px;margin:8px 0 0}}
.det dt{{color:var(--text2);font-size:12px}}.det dd{{margin:0}}.det h4{{margin:12px 0 0}}.tag{{font-size:11px;border-radius:8px;padding:0 6px;margin-left:6px;border:1px solid}}
.th{{color:var(--handb);border-color:var(--handb)}}.tk{{color:var(--kwb);border-color:var(--kwb)}}.det table{{margin-top:6px}}.det td{{border-right:0}}
.view{{display:none}}.view.on{{display:block}}
@media (max-width:700px){{th{{height:110px}}}}
</style></head><body><main>
<h1>Quantity matrix</h1>
<p class="sub">{len(rows)} in-scope papers with a PDF, one row each. <b>Quantities</b>: a cell says where a quantity is (figure, table, text), not the value; {hand} papers were read by hand, every cell; the rest are keyword hits. Of the hand-read papers, {ppt} state an exposure as partial pressure and time (or the exposure itself), and {lim} state it for the step that limits conformality. <b>Papers × cases</b>: which paper each case of cases.html uses, which it could use by its own rule, and which papers no case uses ({none}).</p>
<div class="tabs"><button id="t1" class="on">Quantities</button><button id="t2">Papers × cases</button></div>
<section id="v1" class="view on">
<div class="counts">{"".join(f'<div class="cnt"><b>{n}</b>{E(k)}<br><span>{E(d)}</span></div>' for k, d, n in counts)}</div>
<div class="bar">
<label>Read by hand<select id="fh"><option value="">all</option><option value="yes">yes</option><option value="no">no</option></select></label>
<label>Column<select id="fc"><option value="">(none)</option>{"".join(f'<option>{E(c)}</option>' for c in cols)}</select></label>
<label>Condition<select id="fm"><option value="has">has a value (not “no”)</option><option value="no">is “no”</option><option value="kw">not read by hand</option><option value="txt">contains text</option></select></label>
<label>Text<input id="ft" placeholder="e.g. pp × time" size="16"></label>
<label>Search all cells<input id="fs" placeholder="paper, figure, word" size="18"></label>
<button id="ppt">Only pp × time</button><button id="lim">Only limiting step exposure</button><button id="rst">Reset</button>
</div>
<div class="legend"><span><i class="sw" style="background:var(--hand)"></i>read by hand</span><span><i class="sw" style="background:var(--kw)"></i>not read by hand: a keyword hit or a figure-inventory rule (not checked)</span><span><i class="sw" style="background:var(--no)"></i>no</span><span id="shown"></span><span>Click a row for its full cells.</span></div>
<div class="tw"><table><thead><tr><th class="p">Paper</th>{"".join(f'<th>{E(c)}</th>' for c in cols)}</tr></thead><tbody id="tb"></tbody></table></div>
</section>
<section id="v2" class="view">
<div class="counts">{"".join(f'<div class="cnt cc" data-k="{k}"><b>{u} · {c}</b>{E(k)}<br><span>{E(t)}</span></div>' for k, t, u, c in ccounts)}<div class="cnt"><b>{none}</b>no case<br><span>papers used by no case 1 to 11</span></div></div>
<div class="bar"><label>Show<select id="fv"><option value="">all papers</option><option value="none">papers in no case</option><option value="hand">read by hand</option></select></label>
<label>Search<input id="fs2" placeholder="paper, figure, word" size="18"></label></div>
<div class="legend"><span><i class="sw" style="background:var(--used)"></i>used: the case draws on the paper</span><span><i class="sw" style="background:var(--no)"></i>excluded: selected by the rule, judged not to belong (reason given)</span><span><i class="sw" style="background:var(--cand)"></i>candidate, not decided (part E columns)</span><span><i class="sw" style="background:var(--surface);border:1px solid var(--line)"></i>empty</span><span>Counts are used · excluded or candidate. Click a case header for its papers, a row for the paper in both views. S4 to S11 are part E candidates not built yet.</span></div>
<div id="clist" class="det"><i>Click a case header or count for its papers.</i></div>
<div class="tw"><table><thead><tr><th class="p">Paper</th>{"".join(f'<th class="ch" data-k="{k}" title="{E(t)}">{E(k)} {E(" ".join((t.split(" ", 2)[-1] if k.startswith("c") else t.split(" ", 1)[1]).split(" ")[:3]))}</th>' for k, t in CASES)}<th>in no case</th></tr></thead><tbody id="tb2"></tbody></table></div>
</section>
<div id="det" class="det"><i>Click a row to show the paper's cells in both views.</i></div>
</main>
<script>
const R={json.dumps(rows, ensure_ascii=False)};const C={json.dumps(cols)};const K={json.dumps(CASES, ensure_ascii=False)};
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
const kind=(r,c,v)=>v==="no"||v.startsWith("no ")||v.startsWith("no (")||v==="not read"?"n":(r.read_by_hand==="yes"?"h":"k");
const ck=v=>v.startsWith("used")?"u":v.startsWith("candidate")?"a":v.startsWith("excluded")?"n":"e";
let sel=null,cas=null;
function ok(r){{
  const h=$("fh").value; if(h&&r.read_by_hand!==h) return false;
  const c=$("fc").value, m=$("fm").value, t=$("ft").value.trim().toLowerCase();
  if(c){{const v=r[c]||"";const k=kind(r,c,v);
    if(m==="has"&&k==="n") return false; if(m==="no"&&k!=="n") return false; if(m==="kw"&&k!=="k") return false;
    if(m==="txt"&&t&&!v.toLowerCase().includes(t)) return false;}}
  const s=$("fs").value.trim().toLowerCase();
  if(s&&!(r.paper_id+" "+r._who+" "+C.map(c=>r[c]).join(" ")).toLowerCase().includes(s)) return false;
  return true;}}
function ok2(r){{
  const v=$("fv").value; if(v==="none"&&r._none!=="yes") return false; if(v==="hand"&&r.read_by_hand!=="yes") return false;
  const s=$("fs2").value.trim().toLowerCase();
  if(s&&!(r.paper_id+" "+r._who+" "+K.map(k=>r._cases[k[0]]).join(" ")).toLowerCase().includes(s)) return false;
  return true;}}
const pcell=r=>`<td class="p">${{esc(r._who)}}<span class="pid">${{esc(r.paper_id)}}</span></td>`;
function draw(){{
  const rows=R.filter(ok);$("shown").textContent=rows.length+" of "+R.length+" papers shown";
  $("tb").innerHTML=rows.map(r=>`<tr data-p="${{esc(r.paper_id)}}" class="${{r.paper_id===sel?"on":""}}">${{pcell(r)}}`+C.map(c=>{{const v=r[c]||"";return `<td class="c ${{kind(r,c,v)}}" title="${{esc(v)}}">${{esc(v)}}</td>`}}).join("")+"</tr>").join("");
  $("tb2").innerHTML=R.filter(ok2).map(r=>`<tr data-p="${{esc(r.paper_id)}}" class="${{r.paper_id===sel?"on":""}}">${{pcell(r)}}`+K.map(k=>{{const v=r._cases[k[0]];return `<td class="c ${{ck(v)}}" title="${{esc(v)}}">${{esc(v.replace("candidate, not used: ","candidate: "))}}</td>`}}).join("")+`<td class="c x">${{r._none==="yes"?"yes":""}}</td></tr>`).join("");
  document.querySelectorAll("th.ch").forEach(t=>t.classList.toggle("on",t.dataset.k===cas));}}
function show(p){{sel=p;const r=R.find(x=>x.paper_id===p);if(!r) return;
  $("det").innerHTML=`<b>${{esc(r._who)}}</b> · ${{esc(r._title)}}<span class="pid">${{esc(r.paper_id)}}</span>`+
  (r.read_by_hand==="yes"?'<span class="tag th">read by hand</span>':'<span class="tag tk">keyword only</span>')+(r._none==="yes"?'<span class="tag tk">in no case</span>':"")+
  "<h4>Cases</h4><dl>"+K.map(k=>`<dt>${{esc(k[1])}}</dt><dd>${{esc(r._cases[k[0]]||"—")}}</dd>`).join("")+"</dl>"+
  "<h4>Quantities</h4><dl>"+C.map(c=>`<dt>${{esc(c)}}</dt><dd>${{esc(r[c]||"")}}</dd>`).join("")+"</dl>";draw();}}
function showCase(k){{cas=k;const t=K.find(x=>x[0]===k);if(!t) return;
  const u=R.filter(r=>r._cases[k].startsWith("used")),c=R.filter(r=>r._cases[k].startsWith("candidate"));
  const tab=(rs,h)=>rs.length?`<h4>${{h}} (${{rs.length}})</h4><table><tbody>`+rs.map(r=>`<tr data-p="${{esc(r.paper_id)}}"><td class="p">${{esc(r._who)}}<span class="pid">${{esc(r.paper_id)}}</span></td><td>${{esc(r._cases[k].replace(/^(used|excluded|candidate, not used): /,""))}}</td></tr>`).join("")+"</tbody></table>":`<h4>${{h}} (0)</h4>`;
  $("clist").innerHTML=`<b>${{esc(t[1])}}</b>`+tab(u,"Used: figure or table")+tab(R.filter(r=>r._cases[k].startswith("excluded")),"Excluded: reason")+tab(c,"Candidate, not decided: reason");draw();}}
function view(n){{$("v1").classList.toggle("on",n===1);$("v2").classList.toggle("on",n===2);$("t1").classList.toggle("on",n===1);$("t2").classList.toggle("on",n===2);}}
for(const id of ["tb","tb2","clist"]) $(id).addEventListener("click",e=>{{const tr=e.target.closest("tr[data-p]");if(tr) show(tr.dataset.p);}});
document.querySelector("#v2 thead").addEventListener("click",e=>{{const th=e.target.closest("th.ch");if(th) showCase(th.dataset.k);}});
document.querySelectorAll(".cc").forEach(d=>d.addEventListener("click",()=>showCase(d.dataset.k)));
for(const id of ["fh","fc","fm","ft","fs","fv","fs2"]) $(id).addEventListener("input",draw);
$("t1").onclick=()=>view(1);$("t2").onclick=()=>view(2);
$("ppt").onclick=()=>{{$("fc").value="exposure_or_pp_and_pulse";$("fm").value="txt";$("ft").value="pp × time";$("fh").value="yes";draw();}};
$("lim").onclick=()=>{{$("fc").value="limiting_step_exposure";$("fm").value="txt";$("ft").value="yes";$("fh").value="";draw();}};
$("rst").onclick=()=>{{for(const id of ["fh","fc","ft","fs"]) $(id).value="";$("fm").value="has";draw();}};
function openCase(k){{view(2);showCase(k);$("clist").scrollIntoView();}}
function fromHash(){{const h=new URLSearchParams(location.hash.slice(1));
  if(h.get("case")){{view(2);showCase(h.get("case"));$("clist").scrollIntoView();}}
  if(h.get("paper")) show(h.get("paper"));}}
window.addEventListener("hashchange",fromHash);
draw();fromHash();
</script></body></html>"""
print(f"matrix: {len(rows)} rows, {hand} read by hand; counts", {k: n for k, _, n in counts}, "; no case", none)
