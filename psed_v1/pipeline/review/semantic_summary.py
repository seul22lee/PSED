#!/usr/bin/env python3
"""
semantic_summary.py — the CURRENT production semantic corpus, humanly readable.

One page summarising exactly what the committed production artifacts say:

    papers/_corpus/corpus_manifest.json          declared membership
    papers/<id>/semantic/*.json                  the semantic layer
    papers/<id>/canonical/curves.json            canonical curves
    papers/_corpus/semantic_invariants.json      per-paper invariant status
    papers/_corpus/corpus_expansion_audit.json   declared gaps
    papers/_corpus/workbench/workbench_model.json / workbench_validation.json

Every number on the page is computed from those artifacts at generation time —
nothing is hard-coded. Writes reports/04_semantic__corpus_summary.html and
copies the production Workbench page to
reports/04_semantic__scientific_comparison_workbench.html so both are reachable
from the reports index. The Workbench under papers/_corpus/workbench/ stays the
single authority; the copy is refreshed on every run.

Run:  python3 -m pipeline.review.semantic_summary   (part of `cli.py review`)
"""
import html as _html
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import paths as P                                               # noqa: E402
from pipeline.query import entity_identity as EI                # noqa: E402

WB_DIR = P.PAPERS / "_corpus" / "workbench"
DOCUMENTED_GAP = ("documented gap: the persisted extraction holds no digitized "
                  "curves (see corpus_expansion_audit.json)")


def _j(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def load():
    mf = json.loads(P.corpus_manifest_path().read_text())
    inv = _j(P.PAPERS / "_corpus" / "semantic_invariants.json", {})
    audit = _j(P.PAPERS / "_corpus" / "corpus_expansion_audit.json", {})
    wbm = _j(WB_DIR / "workbench_model.json", {})
    wbv = _j(WB_DIR / "workbench_validation.json", {})
    wb_series = {}
    for s in (wbm.get("series") or {}).values():
        wb_series.setdefault(s.get("paper_id"), []).append(s)
    rows = []
    for entry in mf["included"]:
        pid = entry["paper_id"]
        sd = P.semantic_dir(pid)
        cases = _j(sd / "experimental_cases.json", [])
        meas = _j(sd / "measurements.json", [])
        rs = _j(sd / "result_series.json", [])
        reps = _j(sd / "representations.json", [])
        unres = _j(sd / "unresolved.json", [])
        acts, _ = EI.measurement_acts(meas)
        cur = (_j(P.canonical_dir(pid) / "curves.json", {}) or {}).get("curves", [])

        def npts(c):
            return len(((c.get("canonical") or {}).get("x") or {}).get("values") or [])
        pinv = inv.get(pid) or {}
        wbs = wb_series.get(pid) or []
        flags = []
        if not cases:
            flags.append("zero ExperimentalCases")
        if not rs:
            flags.append("zero ResultSeries")
        if pid == "10.1016_j.mee.2018.01.033":
            flags.append(DOCUMENTED_GAP)
        n_empty = sum(1 for c in cur if not npts(c))
        if n_empty:
            flags.append("%d canonical curve(s) with unresolved axes "
                         "(display-only)" % n_empty)
        rows.append({
            "paper": pid, "study": entry.get("study_type"),
            "cases": len(cases), "measurements": len(meas), "acts": len(acts),
            "series": len(rs), "reps": len(reps),
            "points": sum(r.get("n_points") or 0 for r in rs),
            "curves": len(cur), "curves_empty": n_empty,
            "wb_series": len(wbs),
            "profile": sum(1 for s in wbs if s.get("is_profile")),
            "unresolved": len(unres),
            "inv_ok": (not pinv.get("source_curves_preserved", {}).get("missing")
                       and bool(pinv)),
            "flags": flags,
        })
    return mf, rows, audit, wbv, wbm


TPL = """<!doctype html><meta charset="utf-8">
<title>Production semantic corpus</title><style>
body{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:26px 22px}h1{font-size:22px;margin:0 0 2px}
.sub{color:#565c66;margin-bottom:14px}.card{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}
h2{font-size:14px;margin:0 0 10px}table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec;cursor:pointer;user-select:none}
td{padding:5px 8px;border-bottom:1px solid #eef0f3;vertical-align:top}
.m{font-family:ui-monospace,Menlo,monospace}.sm{font-size:11px;color:#565c66}
.kpi{display:inline-block;background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:10px 16px;margin:0 8px 8px 0}
.kpi b{display:block;font-size:20px}.flag{color:#b23a00;font-size:11px}
.warn{background:#fff4e5}.rev{color:#8b919b}
input{padding:6px 10px;border:1px solid #d5d9e0;border-radius:8px;width:280px;margin-bottom:8px}
</style><div class="wrap">
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600">PSED &middot; production semantic corpus</div>
<h1>Semantic corpus summary</h1>
<div class="sub">Computed from the committed production artifacts
(corpus_manifest, papers/&lt;id&gt;/semantic, canonical curves,
semantic_invariants, workbench model/validation). /*STAMP*/</div>
/*KPIS*/
<div class="card"><h2>Excluded reviews (never counted in semantic totals)</h2>/*REVIEWS*/</div>
<div class="card"><h2>Per paper</h2>
<input id="q" placeholder="filter papers / study type / flags&hellip;" oninput="flt()">
<table id="t"><thead><tr>/*HEAD*/</tr></thead><tbody>/*ROWS*/</tbody>
<tfoot>/*TOTALS*/</tfoot></table>
<div class="sm">Click a column header to sort. "wb series" = ResultSeries carried into the
production Workbench; "profile" = conformality-profile series there. "canonical (empty)" =
curves whose axis semantics never resolved at the canonical layer &mdash; their raw
digitized points still flow into ResultSeries but stay display-only.</div></div>
<div class="card"><h2>Declared gaps (corpus_expansion_audit.json)</h2><ul>/*GAPS*/</ul></div>
<div class="card"><h2>Workbench</h2>/*WB*/
<div class="sm">The authoritative Workbench lives at papers/_corpus/workbench/; a current copy is
<a href="04_semantic__scientific_comparison_workbench.html">04_semantic__scientific_comparison_workbench.html</a>.</div></div>
</div><script>
function flt(){var q=document.getElementById('q').value.toLowerCase();
 document.querySelectorAll('#t tbody tr').forEach(function(r){
  r.style.display=r.textContent.toLowerCase().indexOf(q)>=0?'':'none';});}
var dir={};
document.querySelectorAll('#t th').forEach(function(th,i){th.onclick=function(){
 var tb=document.querySelector('#t tbody');var rows=[].slice.call(tb.rows);
 dir[i]=!dir[i];
 rows.sort(function(a,b){var x=a.cells[i].textContent,y=b.cells[i].textContent;
  var nx=parseFloat(x),ny=parseFloat(y);
  var c=(!isNaN(nx)&&!isNaN(ny))?nx-ny:x.localeCompare(y);
  return dir[i]?c:-c;});
 rows.forEach(function(r){tb.appendChild(r);});};});
</script>"""


def main():
    mf, rows, audit, wbv, wbm = load()
    tot = {k: sum(r[k] for r in rows)
           for k in ("cases", "measurements", "acts", "series", "reps", "points",
                     "curves", "curves_empty", "wb_series", "profile", "unresolved")}
    inv_ok = sum(1 for r in rows if r["inv_ok"])
    wb_papers = len({s.get("paper_id") for s in (wbm.get("series") or {}).values()})
    c = wbv.get("counts", {})
    kpis = "".join(
        '<div class="kpi"><b>%s</b>%s</div>' % (v, k) for k, v in [
            ("paper folders declared", len(mf["included"]) + len(mf["excluded"])),
            ("included papers", len(mf["included"])),
            ("reviews excluded", len(mf["excluded"])),
            ("ExperimentalCases", tot["cases"]),
            ("Measurements", tot["measurements"]),
            ("MeasurementActs", tot["acts"]),
            ("ResultSeries", tot["series"]),
            ("representations", tot["reps"]),
            ("points", tot["points"]),
            ("canonical curves", tot["curves"]),
            ("profile series (Workbench)", tot["profile"]),
            ("invariants passing", "%d / %d" % (inv_ok, len(rows))),
        ])
    reviews = "<ul>" + "".join(
        "<li class=rev><b>%s</b> — %s<br><span class=sm>%s</span></li>"
        % (_html.escape(x["paper_id"]), _html.escape(x.get("reason", "")),
           _html.escape(x.get("evidence", ""))) for x in mf["excluded"]) + "</ul>"
    head = "".join("<th>%s</th>" % h for h in
                   ("paper", "study", "cases", "meas", "acts", "series", "reps",
                    "points", "canonical (empty)", "wb series", "profile",
                    "unresolved", "invariants", "flags"))
    body = []
    for r in sorted(rows, key=lambda r: r["paper"]):
        cls = ' class="warn"' if r["flags"] else ""
        body.append(
            "<tr%s><td class=m>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td>"
            "<td>%d</td><td>%d</td><td>%d</td><td>%d (%d)</td><td>%d</td><td>%d</td>"
            "<td>%d</td><td>%s</td><td class=flag>%s</td></tr>"
            % (cls, _html.escape(r["paper"]), _html.escape(str(r["study"])),
               r["cases"], r["measurements"], r["acts"], r["series"], r["reps"],
               r["points"], r["curves"], r["curves_empty"], r["wb_series"],
               r["profile"], r["unresolved"],
               "ok" if r["inv_ok"] else "FAILED",
               "; ".join(_html.escape(f) for f in r["flags"])))
    totals = ("<tr><td><b>TOTAL (%d included)</b></td><td></td>"
              "<td><b>%d</b></td><td><b>%d</b></td><td><b>%d</b></td><td><b>%d</b></td>"
              "<td><b>%d</b></td><td><b>%d</b></td><td><b>%d (%d)</b></td>"
              "<td><b>%d</b></td><td><b>%d</b></td><td><b>%d</b></td>"
              "<td><b>%d/%d ok</b></td><td></td></tr>"
              % (len(rows), tot["cases"], tot["measurements"], tot["acts"],
                 tot["series"], tot["reps"], tot["points"], tot["curves"],
                 tot["curves_empty"], tot["wb_series"], tot["profile"],
                 tot["unresolved"], inv_ok, len(rows)))
    gaps = "".join("<li class=sm>%s</li>" % _html.escape(g)
                   for g in audit.get("gaps", [])) or "<li class=sm>(none declared)</li>"
    pair = (audit.get("totals", {}).get("workbench", {}) or {}).get("pair_statuses", {})
    wb = ("<p>%d papers contribute ResultSeries (of %d included; see flags for the "
          "papers that do not) &middot; %s series &middot; %s MeasurementActs &middot; "
          "%s profile series &middot; %s indexed pairs %s &middot; invariants %s</p>"
          % (wb_papers, len(rows), c.get("result_series_persisted", "?"),
             c.get("measurement_acts", "?"), c.get("profile_series", "?"),
             c.get("indexed_pairs", "?"),
             _html.escape(json.dumps(pair)) if pair else "",
             "ok" if all((wbv.get("invariants") or {}).values()) else "FAILED"))
    meta = wbm.get("meta") or {}
    stamp = ("Workbench model built at repo %s (code %s)."
             % (meta.get("head_sha", "?"),
                (meta.get("generating_code_sha256") or "?")[:12]))
    page = (TPL.replace("/*KPIS*/", kpis).replace("/*REVIEWS*/", reviews)
            .replace("/*HEAD*/", head).replace("/*ROWS*/", "".join(body))
            .replace("/*TOTALS*/", totals).replace("/*GAPS*/", gaps)
            .replace("/*WB*/", wb).replace("/*STAMP*/", stamp))
    out = P.REPORTS / "04_semantic__corpus_summary.html"
    out.write_text(page)
    print("wrote %s  (%d included papers, %d cases, %d series, %d points)"
          % (out, len(rows), tot["cases"], tot["series"], tot["points"]))
    src = WB_DIR / "psed_scientific_comparison_workbench.html"
    if src.exists():
        dst = P.REPORTS / "04_semantic__scientific_comparison_workbench.html"
        shutil.copyfile(src, dst)
        print("copied production workbench -> %s" % dst)
    else:
        print("NOTE: %s missing; run `python3 cli.py workbench` first" % src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
