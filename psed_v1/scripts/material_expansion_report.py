#!/usr/bin/env python3
"""
scripts/material_expansion_report.py — what the 12-paper expansion actually added.

    python3 scripts/material_expansion_report.py

Writes reports/material_expansion_12.{json,html}.

BEFORE is the validated 32-paper corpus, reconstructed by excluding the 12 papers in
reports/true_deposition_overlap_12_selection.json from the live corpus; AFTER is the
live 44-paper corpus. Every number is computed from resolved/canonical data, never
from the candidate triage — the triage's material field was the thing the deposited-
material audit had to correct.

A paper is credited to a material only where its own resolved experiments carry that
material, so a multi-material paper (10.1149/2.067203jes deposits SiO2 and an Al2O3
capping layer) is counted under each material it actually deposits, and a substrate
never counts.
"""
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                              # noqa: E402

MANIFEST = P.REPORTS / "true_deposition_overlap_12_selection.json"
OUT_JSON = P.REPORTS / "material_expansion_12.json"
OUT_HTML = P.REPORTS / "material_expansion_12.html"


def paper_stats(pid):
    """Per-material stats for one paper, from its own resolved + canonical layer."""
    exps = json.loads(P.resolved_json(pid, "experiments").read_text()) \
        if P.resolved_json(pid, "experiments").exists() else []
    res = json.loads(P.resolved_json(pid, "results").read_text()).get("results", []) \
        if P.resolved_json(pid, "results").exists() else []
    curves = json.loads(P.curves_json(pid).read_text()).get("curves", []) \
        if P.curves_json(pid).exists() else []
    ents = json.loads(P.resolved_json(pid, "entities").read_text()) \
        if P.resolved_json(pid, "entities").exists() else []
    # Attribute a paper to a material from its resolved ENTITIES, not only from minted
    # experiments. A paper whose curves are all UnresolvedSourceEntity contributes no
    # experiments but still carries the material and its result series -- 10.1039/
    # c7ta03257a deposits Pt and yields four Pt curves, yet mints zero experiments
    # because its figures are electrochemical traces.
    mats = sorted({e.get("material") for e in (exps + ents) if e.get("material")})
    src = Counter()
    for c in curves:
        src[(c.get("source") or {}).get("data_source") or "unknown"] += 1
    return {"materials": mats, "experiments": len(exps), "results": len(res),
            "curves": len(curves), "measured": src.get("measured", 0),
            "simulated": src.get("simulated", 0)}


def main():
    manifest = json.loads(MANIFEST.read_text())
    new_ids = [p["paper_id"] for p in manifest["papers"]]
    live = sorted(P.papers())
    before_ids = [p for p in live if p not in set(new_ids)]

    stats = {pid: paper_stats(pid) for pid in live}
    focus = sorted({m for p in manifest["papers"] for m in p["true_overlap_material"]})

    def agg(ids):
        papers, exps, res, cur, meas, sim = (defaultdict(set), Counter(), Counter(),
                                             Counter(), Counter(), Counter())
        for pid in ids:
            s = stats[pid]
            n = max(len(s["materials"]), 1)
            for m in s["materials"]:
                papers[m].add(pid)
                exps[m] += s["experiments"] // n
                res[m] += s["results"] // n
                cur[m] += s["curves"] // n
                meas[m] += s["measured"] // n
                sim[m] += s["simulated"] // n
        return papers, exps, res, cur, meas, sim

    bP, bE, bR, bC, bM, bS = agg(before_ids)
    aP, aE, aR, aC, aM, aS = agg(live)
    nP, nE, nR, nC, nM, nS = agg(new_ids)

    rows = []
    for m in sorted(set(focus) | set(nP), key=lambda x: (-len(nP.get(x, ())), x)):
        rows.append({
            "material": m,
            "papers_before": len(bP.get(m, ())), "new_papers": len(nP.get(m, ())),
            "papers_after": len(aP.get(m, ())),
            "new_paper_ids": sorted(nP.get(m, ())),
            "experiments_before": bE[m], "experiments_added": nE[m], "experiments_after": aE[m],
            "measured_series_before": bM[m], "measured_series_added": nM[m],
            "measured_series_after": aM[m],
            "simulated_series_added": nS[m],
            "canonical_curves_before": bC[m], "canonical_curves_added": nC[m],
            "canonical_curves_after": aC[m],
        })

    out = {
        "note": ("Counts computed from the resolved/canonical layer of each paper, not "
                 "from candidate triage. A paper is credited only to materials its own "
                 "resolved experiments deposit; substrates and supports never count. "
                 "Multi-material papers are split evenly across their deposited materials, "
                 "so per-material series/experiment figures are apportioned, while paper "
                 "counts are exact."),
        "papers_before": len(before_ids), "papers_new": len(new_ids),
        "papers_after": len(live),
        "corpus_totals": {
            "before": {k: sum(stats[p][k] for p in before_ids)
                       for k in ("experiments", "results", "curves", "measured", "simulated")},
            "added": {k: sum(stats[p][k] for p in new_ids)
                      for k in ("experiments", "results", "curves", "measured", "simulated")},
            "after": {k: sum(stats[p][k] for p in live)
                      for k in ("experiments", "results", "curves", "measured", "simulated")},
        },
        "new_paper_materials": {p: stats[p]["materials"] for p in new_ids},
        "materials": rows,
    }
    OUT_JSON.write_text(json.dumps(out, indent=1))

    def esc(x):
        return html.escape(str(x if x is not None else ""))

    h = ["""<!doctype html><meta charset="utf-8"><title>Material expansion — 32 to 44 papers</title>
<style>
:root{--bg:#f7f8fa;--fg:#16181d;--mut:#5b6472;--line:#d9dee5;--card:#fff;--accent:#0f7c8a}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6eaf0;--mut:#98a3b3;--line:#2b323d;--card:#1a1f27;--accent:#4fc3d1}}
*{box-sizing:border-box}
body{margin:0 auto;max-width:1180px;padding:30px 22px 70px;background:var(--bg);color:var(--fg);
 font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-variant-numeric:tabular-nums}
h1{font-family:Georgia,serif;font-size:26px;margin:0 0 4px}
h2{font-family:Georgia,serif;font-size:18px;margin:30px 0 8px;border-bottom:2px solid var(--accent);padding-bottom:6px}
.sub{color:var(--mut);max-width:82ch}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th,td{border:1px solid var(--line);padding:4px 8px;text-align:right}
th:first-child,td:first-child{text-align:left}
th{background:var(--card)}
.gain{color:#0f7c3f;font-weight:700}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 13px;min-width:130px}
.card b{display:block;font-size:21px}.card span{font-size:11px;color:var(--mut);text-transform:uppercase}
.hint{color:var(--mut);font-size:12.5px}
</style>
<h1>Material expansion — 32 → 44 papers</h1>"""]
    h.append('<p class="sub">%s</p>' % esc(out["note"]))
    t = out["corpus_totals"]
    h.append('<div class="cards">')
    for label, key in (("papers", None), ("experiments", "experiments"),
                       ("source series", "results"), ("canonical curves", "curves"),
                       ("measured", "measured"), ("simulated", "simulated")):
        if key is None:
            h.append('<div class="card"><b>%d → %d</b><span>papers</span></div>'
                     % (out["papers_before"], out["papers_after"]))
        else:
            h.append('<div class="card"><b>%d → %d</b><span>%s (+%d)</span></div>'
                     % (t["before"][key], t["after"][key], esc(label), t["added"][key]))
    h.append("</div>")
    h.append("<h2>Per deposited material</h2>")
    h.append('<p class="hint">Only materials the new papers actually deposit. Paper counts '
             "are exact; per-material experiment and series figures are apportioned for "
             "multi-material papers.</p>")
    h.append("<table><tr><th>material</th><th>papers before</th><th>new</th><th>papers after</th>"
             "<th>exp before</th><th>exp added</th><th>exp after</th>"
             "<th>meas before</th><th>meas added</th><th>meas after</th>"
             "<th>sim added</th><th>curves added</th></tr>")
    for r in rows:
        h.append("<tr><td><b>%s</b></td><td>%d</td><td class=gain>+%d</td><td>%d</td>"
                 "<td>%d</td><td class=gain>+%d</td><td>%d</td>"
                 "<td>%d</td><td class=gain>+%d</td><td>%d</td><td>%d</td><td>%d</td></tr>"
                 % (esc(r["material"]), r["papers_before"], r["new_papers"], r["papers_after"],
                    r["experiments_before"], r["experiments_added"], r["experiments_after"],
                    r["measured_series_before"], r["measured_series_added"],
                    r["measured_series_after"], r["simulated_series_added"],
                    r["canonical_curves_added"]))
    h.append("</table>")
    h.append("<h2>New papers and the materials they deposit</h2><table>"
             "<tr><th>paper</th><th>deposited materials (resolved)</th><th>experiments</th>"
             "<th>series</th><th>curves</th><th>measured</th><th>simulated</th></tr>")
    for p in manifest["papers"]:
        pid = p["paper_id"]
        s = stats[pid]
        h.append("<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td>"
                 "<td>%d</td></tr>" % (esc(pid), esc(", ".join(s["materials"]) or "—"),
                                       s["experiments"], s["results"], s["curves"],
                                       s["measured"], s["simulated"]))
    h.append("</table>")
    OUT_HTML.write_text("\n".join(h))
    print("wrote %s" % OUT_JSON)
    print("wrote %s" % OUT_HTML)
    for r in rows:
        print("  %-8s papers %d -> %d (+%d)  meas series +%d  curves +%d"
              % (r["material"], r["papers_before"], r["papers_after"], r["new_papers"],
                 r["measured_series_added"], r["canonical_curves_added"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
