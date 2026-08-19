#!/usr/bin/env python3
"""
build_corpus_dashboard.py — a self-contained dashboard for the paper-collection
pipeline: how the corpus narrows from review-paper references → resolved DOIs →
open-access PDFs collected → docling-parsed → scouted → figure-extracted → in the KB.

Reads live from the repo (refsets, pdf inbox, papers/*/extracted, papers/*/resolvut/),
so the numbers are always current. Writes reports/corpus_dashboard.html.
No external deps (inline CSS/SVG, theme-aware).
"""
import paths as P
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = P.REPO
REF = ROOT / "corpus" / "references" / "refsets"
PDFS = P.PDF_INBOX
EXTRACTED = P.PAPERS                 # papers/<id>/extracted/
KB = P.PAPERS          # papers/<doi>/{resolved,canonical}/


def load():
    merged = list(csv.DictReader(open(REF / "merged_refs.csv"))) if (REF / "merged_refs.csv").exists() else []
    dl = list(csv.DictReader(open(REF / "download_log.csv"))) if (REF / "download_log.csv").exists() else []
    triage = list(csv.DictReader(open(REF / "triage.csv"))) if (REF / "triage.csv").exists() else []

    cited = Counter(r.get("cited_by", "") for r in merged)
    cremers = sum(v for k, v in cited.items() if "cremers" in k)
    popov = sum(v for k, v in cited.items() if "popov" in k)
    shared = sum(v for k, v in cited.items() if "|" in k)
    status = Counter(r.get("status", "") for r in dl)
    oa = Counter(r.get("oa_status", "") or "—" for r in dl)
    tier = Counter(r.get("tier", "") for r in triage)

    pdfs = sorted(p.stem for p in PDFS.glob("*.pdf"))
    # the DECLARED corpus (papers/_corpus/corpus_manifest.json), never a glob
    mf = json.loads(P.corpus_manifest_path().read_text())
    included = [x["paper_id"] for x in mf["included"]]
    excluded = {x["paper_id"]: x.get("reason", "excluded") for x in mf["excluded"]}
    papers = []
    for d in sorted(P.extracted_dir(x) for x in included + sorted(excluded)):
        sd = d.parent.name
        sc = {}
        if (d / "scout.json").exists():
            try:
                sc = json.loads((d / "scout.json").read_text())
            except Exception:
                sc = {}
        nrec = 0
        if (d / "records.json").exists():
            try:
                nrec = len(json.loads((d / "records.json").read_text()))
            except Exception:
                nrec = 0
        kbf = P.resolved_json(sd, "experiments")
        nexp = 0
        exps = []
        if kbf.exists():
            try:
                exps = json.loads(kbf.read_text())
                nexp = len(exps)
            except Exception:
                exps, nexp = [], 0
        # Since condition sweeps became ExperimentSeries, a bare experiment count
        # is no longer comparable with the old one: each point of a sweep is now its
        # own Experiment. Report the breakdown so a granularity correction cannot be
        # mistaken for corpus growth.
        nseries = 0
        sf = P.resolved_json(sd, "series")
        if sf.exists():
            try:
                nseries = len(json.loads(sf.read_text()))
            except Exception:
                nseries = 0
        n_profile = sum(1 for e in exps if e.get("granularity") == "profile")
        n_in_series = sum(1 for e in exps if e.get("in_series"))
        # everything that is neither a spatial profile nor a member of a sweep
        # series: single-point records, output-vs-output correlations, and curves
        # whose axis role could not be resolved from the available evidence
        n_other = nexp - n_profile - n_in_series
        # curves carrying at least one comparison-ready canonical axis
        ncanon = 0
        cf = P.curves_json(sd)
        if cf.exists():
            try:
                cur = json.loads(cf.read_text()).get("curves", [])
                ncanon = sum(1 for c in cur
                             if (c.get("canonical") or {}).get("x")
                             or (c.get("canonical") or {}).get("y"))
            except Exception:
                ncanon = 0
        papers.append({
            "doi": sd,
            "corpus": ("review (excluded)" if sd in excluded else "included"),
            "docling": (d / "document.md").exists(),
            "scouted": bool(sc) and "_parse_error" not in sc,
            "study": (sc.get("study_type") if sc else None),
            "material": ((sc.get("materials") or [None])[0] if sc else None),
            "drill": len(sc.get("drill") or []) if sc else 0,
            "records": nrec, "experiments": nexp,
            "profiles": n_profile, "series": nseries, "in_series": n_in_series,
            "other": n_other,
            "canonical": ncanon,
            "in_kb": nexp > 0,
        })

    n_extracted = sum(1 for p in papers if p["docling"])
    n_scouted = sum(1 for p in papers if p["scouted"])
    n_records = sum(1 for p in papers if p["records"] > 0)
    n_kb = sum(1 for p in papers if p["in_kb"])
    total_exp = sum(p["experiments"] for p in papers)
    total_profiles = sum(p["profiles"] for p in papers)
    total_series = sum(p["series"] for p in papers)
    total_in_series = sum(p["in_series"] for p in papers)
    total_canonical = sum(p["canonical"] for p in papers)
    total_other = sum(p["other"] for p in papers)

    funnel = [
        {"label": "Review papers", "n": 2, "note": "Cremers 2019 · Popov 2025"},
        {"label": "Cited references (rows)", "n": cremers + popov - shared + shared, "note": f"Cremers {cremers} · Popov {popov} · {shared} shared"},
        {"label": "Unique DOIs resolved", "n": len(merged), "note": "Crossref deposited + bibliographic"},
        {"label": "Triaged: relevant", "n": tier.get("high", 0) + tier.get("med", 0) + tier.get("low", 0), "note": f"high {tier.get('high',0)} · med {tier.get('med',0)} · low {tier.get('low',0)} · reject {tier.get('reject',0)}"},
        {"label": "Open-access PDF fetchable", "n": status.get("downloaded", 0) + status.get("already_have", 0), "note": f"{status.get('not_oa',0)} closed · {status.get('oa_no_pdf_url',0)} OA-no-url · {status.get('http_error',0)} http-err"},
        {"label": "PDFs collected", "n": len(pdfs), "note": "auto-fetched + manually added"},
        {"label": "Docling-parsed", "n": n_extracted, "note": "document.md + structure.json"},
        {"label": "Scouted (abstract/figs)", "n": n_scouted, "note": "role-separated process card"},
        {"label": "Figure-extracted", "n": n_records, "note": "vision digitized data points"},
        {"label": "In knowledge base (resolved Experiment layer)", "n": n_kb,
         "note": (f"{total_exp} experiments = {total_profiles} spatial profiles "
                  f"+ {total_in_series} sweep points in {total_series} series "
                  f"+ {total_other} single/correlation/unresolved -- M2 feeder "
                  "granularity, NOT the semantic corpus")},
        {"label": "Comparison-ready curves", "n": total_canonical,
         "note": "at least one axis in a canonical comparison group"},
    ]
    # ---- the PRODUCTION SEMANTIC CORPUS: a different population from the
    # acquisition funnel above, declared in the manifest and summarised from the
    # committed production artifacts, never recomputed here
    sem = {"cases": 0, "meas": 0, "series": 0, "points": 0}
    for pid in included:
        sd2 = P.semantic_dir(pid)
        if not (sd2 / "result_series.json").exists():
            continue
        sem["cases"] += len(json.loads((sd2 / "experimental_cases.json").read_text()))
        sem["meas"] += len(json.loads((sd2 / "measurements.json").read_text()))
        rs = json.loads((sd2 / "result_series.json").read_text())
        sem["series"] += len(rs)
        sem["points"] += sum(r.get("n_points") or 0 for r in rs)
    wbv = P.PAPERS / "_corpus" / "workbench" / "workbench_validation.json"
    wb = json.loads(wbv.read_text())["counts"] if wbv.exists() else {}
    wbm = P.PAPERS / "_corpus" / "workbench" / "workbench_model.json"
    wb_papers = (len({x.get("paper_id")
                      for x in json.loads(wbm.read_text())["series"].values()})
                 if wbm.exists() else 0)
    funnel += [
        {"label": "Declared corpus (manifest)", "n": len(included) + len(excluded),
         "note": f"{len(included)} included · {len(excluded)} reviews excluded: "
                 + ", ".join(sorted(excluded))},
        {"label": "Production semantic corpus", "n": len(included),
         "note": (f"{sem['cases']} ExperimentalCases · {sem['meas']} Measurements · "
                  f"{sem['series']} ResultSeries · {sem['points']} points")},
        {"label": "Workbench", "n": wb.get("result_series_persisted", 0),
         "note": (f"ResultSeries across {wb_papers} papers · "
                  f"{wb.get('indexed_pairs', 0)} indexed pairs · "
                  f"{wb.get('profile_series', 0)} profile series")},
    ]
    return {
        "funnel": funnel,
        "reviews": {"cremers": cremers, "popov": popov, "shared": shared, "total": len(merged)},
        "status": dict(status), "oa": dict(oa), "tier": dict(tier),
        "pdfs": len(pdfs), "papers": papers,
        "totals": {"extracted": n_extracted, "kb": n_kb, "experiments": total_exp,
                   "profiles": total_profiles, "series": total_series,
                   "in_series": total_in_series, "canonical": total_canonical,
                   "other": total_other},
    }


def main():
    data = load()
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    out = P.REPORTS / "03_corpus__corpus_dashboard.html"
    out.write_text(html)
    f = data["funnel"]
    print(f"wrote {out.relative_to(ROOT.parent)}  ({len(html)//1024} KB)")
    for s in f:
        print(f"   {s['n']:>5}  {s['label']}")


TEMPLATE = r"""<title>ALD corpus pipeline</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fafbfc;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --a1:#4a3aa7;--a2:#2a78d6;--a3:#0f9bd8;--a4:#1baf7a;--a5:#7d5ba6;--a6:#c65d3b;--a7:#eda100;--a8:#e34948;--ok:#1baf7a;--no:#c65d3b;--warn:#eda100;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#191b1f;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --a1:#9085e9;--a2:#3987e5;--a3:#33a9dd;--a4:#199e70;--a5:#a98cd6;--a6:#e07a54;--a7:#c98500;--a8:#e66767;--ok:#199e70;--no:#e07a54;--warn:#c98500;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#191b1f;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --a1:#9085e9;--a2:#3987e5;--a3:#33a9dd;--a4:#199e70;--a5:#a98cd6;--a6:#e07a54;--a7:#c98500;--a8:#e66767;--ok:#199e70;--no:#e07a54;--warn:#c98500;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fafbfc;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --a1:#4a3aa7;--a2:#2a78d6;--a3:#0f9bd8;--a4:#1baf7a;--a5:#7d5ba6;--a6:#c65d3b;--a7:#eda100;--a8:#e34948;--ok:#1baf7a;--no:#c65d3b;--warn:#eda100;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:26px 20px 60px}
h1{font-size:25px;margin:0 0 2px;font-weight:600;font-family:"Iowan Old Style",Georgia,serif}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:26px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .n{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums}
.card .l{font-size:12px;color:var(--ink3);text-transform:uppercase;letter-spacing:.04em}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--ink3);margin:30px 0 12px;font-weight:600}
.funnel{display:flex;flex-direction:column;gap:3px}
.frow{display:grid;grid-template-columns:190px 1fr 60px;align-items:center;gap:12px}
.frow .name{font-size:13px;color:var(--ink2);text-align:right}
.bar{height:34px;border-radius:7px;display:flex;align-items:center;padding:0 11px;color:#fff;font-weight:600;font-size:13px;min-width:36px;white-space:nowrap;overflow:hidden}
.frow .note{font-size:11px;color:var(--ink3)}
.pct{font-size:12px;color:var(--ink3);text-align:right;font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line2)}
th{color:var(--ink3);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.05em}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:1px 8px;border-radius:11px;font-size:11px;font-weight:600}
.pill.ok{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.pill.no{background:color-mix(in srgb,var(--no) 16%,transparent);color:var(--no)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:26px}
@media(max-width:820px){.two{grid-template-columns:1fr}.frow{grid-template-columns:120px 1fr 46px}}
.seg{display:flex;height:26px;border-radius:7px;overflow:hidden;border:1px solid var(--line)}
.seg div{display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:600}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:5px}.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
.muted{color:var(--ink3);font-size:12px}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · corpus collection</div>
<h1>Paper pipeline</h1>
<div class="sub" id="sub"></div>
<div class="grid" id="cards"></div>

<h2>Collection funnel</h2>
<div class="funnel" id="funnel"></div>

<div class="two">
<div>
<h2>References by review</h2>
<div class="seg" id="revseg"></div>
<div class="legend" id="revleg"></div>
<table id="revtab" style="margin-top:14px"></table>
</div>
<div>
<h2>Open-access reachability</h2>
<div class="seg" id="oaseg"></div>
<div class="legend" id="oaleg"></div>
<table id="statustab" style="margin-top:14px"></table>
</div>
</div>

<h2>Extracted papers (in the knowledge base)</h2>
<table id="papertab"></table>
</div>
<script>
const D=/*DATA*/;
const $=id=>document.getElementById(id);
const COL=["--a1","--a2","--a3","--a4","--a5","--a6","--a7","--a8"];
const CSS=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
$("sub").textContent=`${D.reviews.total} unique DOIs from 2 reviews · ${D.pdfs} PDFs collected · ${D.totals.extracted} extracted · ${D.totals.kb} in KB (${D.totals.profiles} profiles + ${D.totals.in_series} sweep points in ${D.totals.series} series)`;

// summary cards
const cards=[["Unique DOIs",D.reviews.total],["PDFs collected",D.pdfs],["Extracted",D.totals.extracted],["In knowledge base",D.totals.kb],["Experiments",D.totals.experiments],["ExperimentSeries",D.totals.series],["Comparison-ready curves",D.totals.canonical]];
$("cards").innerHTML=cards.map((c,i)=>`<div class="card"><div class="n" style="color:var(${COL[i%COL.length]})">${c[1]}</div><div class="l">${c[0]}</div></div>`).join("");

// funnel — bar width relative to the max (DOIs)
const fmax=Math.max(...D.funnel.map(f=>f.n))||1;
$("funnel").innerHTML=D.funnel.map((f,i)=>{
  const w=Math.max(3,f.n/fmax*100), prev=i>0?D.funnel[i-1].n:f.n, pct=prev?Math.round(f.n/prev*100):100;
  return `<div class="frow"><div class="name">${f.label}</div>
    <div style="display:flex;align-items:center;gap:9px">
      <div class="bar" style="width:${w}%;background:var(${COL[i%COL.length]})">${f.n}</div>
      <div class="note">${f.note}</div></div>
    <div class="pct">${i>0?pct+"%":""}</div></div>`;
}).join("");

// references by review — stacked segment
function seg(el,parts){const tot=parts.reduce((a,p)=>a+p.n,0)||1;
  el.innerHTML=parts.map((p,i)=>`<div style="width:${p.n/tot*100}%;background:var(${p.c})">${p.n/tot>0.06?p.n:""}</div>`).join("");}
function leg(el,parts){el.innerHTML=parts.map(p=>`<span><i style="background:var(${p.c})"></i>${p.label} ${p.n}</span>`).join("");}
const rev=[{label:"Cremers only",n:D.reviews.cremers-D.reviews.shared,c:"--a1"},
           {label:"Shared",n:D.reviews.shared,c:"--a5"},
           {label:"Popov only",n:D.reviews.popov-D.reviews.shared,c:"--a2"}];
seg($("revseg"),rev);leg($("revleg"),rev);
$("revtab").innerHTML=`<tr><th>Review</th><th class="n">cited refs</th></tr>`+
  [["Cremers 2019",D.reviews.cremers],["Popov 2025",D.reviews.popov],["Shared by both",D.reviews.shared],["Union (unique)",D.reviews.total]]
  .map(r=>`<tr><td>${r[0]}</td><td class="n">${r[1]}</td></tr>`).join("");

// OA reachability
const oaParts=[{label:"downloaded",n:(D.status.downloaded||0)+(D.status.already_have||0),c:"--a4"},
  {label:"OA no url",n:D.status.oa_no_pdf_url||0,c:"--a7"},
  {label:"http error",n:D.status.http_error||0,c:"--a6"},
  {label:"closed",n:D.status.not_oa||0,c:"--a8"}];
seg($("oaseg"),oaParts);leg($("oaleg"),oaParts);
$("statustab").innerHTML=`<tr><th>fetch status</th><th class="n">count</th></tr>`+
  Object.entries(D.status).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<tr><td>${k}</td><td class="n">${v}</td></tr>`).join("");

// extracted papers table
const P=D.papers.filter(p=>p.docling).sort((a,b)=>b.experiments-a.experiments);
$("papertab").innerHTML=`<tr><th>DOI</th><th>study</th><th>material</th><th class="n">drill</th><th class="n">records</th><th class="n">experiments</th><th class="n">profiles</th><th class="n">series</th><th class="n">canon</th><th>KB</th></tr>`+
  P.map(p=>`<tr><td>${p.doi}</td><td>${p.study||'—'}</td><td>${p.material||'—'}</td>
    <td class="n">${p.drill}</td><td class="n">${p.records}</td><td class="n">${p.experiments}</td>
    <td class="n">${p.profiles}</td><td class="n">${p.series}</td><td class="n">${p.canonical}</td>
    <td><span class="pill ${p.in_kb?'ok':'no'}">${p.in_kb?'in KB':'—'}</span></td></tr>`).join("");
</script>
"""

if __name__ == "__main__":
    main()
