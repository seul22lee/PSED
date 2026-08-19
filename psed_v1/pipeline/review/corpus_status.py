#!/usr/bin/env python3
"""status.py — corpus pipeline status + ontology coverage, at a glance.
  python3 scripts/status.py            # console table + writes corpus_status.html
Stages per paper: docling / scout / deep / KB / geometry. Also lists every
material / precursor / coreactant seen by the scout that is NOT in the ontology.
"""
import paths as P
import json, glob, html
from pathlib import Path

ROOT = P.REPO
PAPERS = P.PAPERS
ONTO = json.loads((P.ONTOLOGY_JSON).read_text())
O_MAT = {m["id"] for m in ONTO["individuals"]["materials"]}
O_PRE = {p["id"] for p in ONTO["individuals"]["precursors"]}
O_COR = {c["id"] for c in ONTO["individuals"]["coreactants"]}

rows, miss_m, miss_p, miss_c = [], {}, {}, {}
# The DECLARED corpus: papers/_corpus/corpus_manifest.json lists every paper --
# 41 included experimental/modeling papers plus the excluded reviews (which keep
# their extraction rows here, labelled, because their artifacts feed the KG).
# Membership never comes from directory globbing or the acquisition inbox.
_MF = json.loads(P.corpus_manifest_path().read_text())
_INCLUDED = [x["paper_id"] for x in _MF["included"]]
_EXCLUDED = {x["paper_id"]: x.get("reason", "excluded") for x in _MF["excluded"]}
_WB_MODEL = P.PAPERS / "_corpus" / "workbench" / "workbench_model.json"
_WB_PAPERS = set()
if _WB_MODEL.exists():
    _WB_PAPERS = {x.get("paper_id") for x in
                  json.loads(_WB_MODEL.read_text())["series"].values()}
for sd in _INCLUDED + sorted(_EXCLUDED):
    d = P.extracted_dir(sd)
    kbf = P.resolved_json(sd, "experiments")
    st = {
        "doc":  (d / "document.md").exists(),
        "scout":(d / "scout.json").exists(),
        "deep": (d / "records.json").exists(),
        "kb":   kbf.exists(),
        "geom": (d / "geometry.json").exists(),
        "sem":  (P.semantic_dir(sd) / "experimental_cases.json").exists()
                and sd not in _EXCLUDED,
        "wb":   sd in _WB_PAPERS,
        "member": ("review (excluded)" if sd in _EXCLUDED else "included"),
    }
    info = {"ald": "", "go": "", "mats": "", "nexp": "", "prof": "", "ser": "", "canon": ""}
    if st["scout"]:
        s = json.loads((d / "scout.json").read_text())
        # A FAILED scout must never look like a deliberate non-ALD rejection: a truncated
        # response leaves is_ald_process_paper=None, which used to render as "N" and hid
        # 10.1116_1.4938104 for weeks. "N" now means only a clean non-ALD verdict.
        if s.get("_parse_error") or s.get("_scout_failed") or s.get("is_ald_process_paper") is None:
            info["ald"] = "FAIL"
        else:
            info["ald"] = "Y" if s.get("is_ald_process_paper") else "N"
        info["go"] = "Y" if s.get("go_deeper") else ""
        info["mats"] = ",".join(s.get("materials") or [])
        for m in s.get("materials") or []:
            if m not in O_MAT: miss_m.setdefault(m, []).append(sd)
        for p in s.get("precursors") or []:
            if p not in O_PRE: miss_p.setdefault(p, []).append(sd)
        for c in s.get("coreactants") or []:
            if c not in O_COR: miss_c.setdefault(c, []).append(sd)
    if st["kb"]:
        exps = json.loads(kbf.read_text())
        info["nexp"] = str(len(exps))
        # A condition sweep is now one Experiment PER POINT plus an
        # ExperimentSeries, so the raw count alone would read as corpus growth.
        # Show the spatial-profile count and the series count next to it.
        info["prof"] = str(sum(1 for e in exps if e.get("granularity") == "profile"))
        sf = P.resolved_json(sd, "series")
        if sf.exists():
            info["ser"] = str(len(json.loads(sf.read_text())))
        cf = P.curves_json(sd)
        if cf.exists():
            cur = json.loads(cf.read_text()).get("curves", [])
            info["canon"] = str(sum(1 for c in cur
                                    if (c.get("canonical") or {}).get("x")
                                    or (c.get("canonical") or {}).get("y")))
    rows.append((sd, st, info))

# ---- console ----
def mark(b): return "O" if b else "."
print(f"{'paper':34} doc scout deep KB geom sem wb   ald go  exps prof ser canon  materials")
for sd, st, i in rows:
    print(f"{sd:34} {mark(st['doc']):3} {mark(st['scout']):5} {mark(st['deep']):4} "
          f"{mark(st['kb']):2} {mark(st['geom']):4} {mark(st['sem']):3} {mark(st['wb']):3} "
          f"{i['ald']:3} {i['go']:3} "
          f"{i['nexp']:4} {i['prof']:4} {i['ser']:3} {i['canon']:5}  {i['mats']}")
n = len(rows)
cnt = {k: sum(1 for _, st, _ in rows if st[k])
       for k in ("doc", "scout", "deep", "kb", "geom", "sem", "wb")}
print(f"\nTOTAL {n} declared papers ({len(_INCLUDED)} included + "
      f"{len(_EXCLUDED)} reviews excluded) | docling {cnt['doc']} | "
      f"scout {cnt['scout']} | deep {cnt['deep']} | KB {cnt['kb']} | "
      f"geometry {cnt['geom']} | semantic {cnt['sem']} | workbench {cnt['wb']}")
print(f"\n-- ontology gaps (scouted but not in ontology) --")
for label, dd in (("materials", miss_m), ("precursors", miss_p), ("coreactants", miss_c)):
    print(f"{label}: " + ("; ".join(f"{k} [{len(v)}]" for k, v in sorted(dd.items())) or "(none)"))

# ---- HTML ----
def cell(b): return f'<td class="{"y" if b else "n"}">{"✓" if b else ""}</td>'
h = ['<!doctype html><meta charset="utf-8"><title>corpus status</title><style>',
     'body{font-family:sans-serif;font-size:13px} table{border-collapse:collapse}',
     'td,th{border:1px solid #ccc;padding:2px 6px} .y{background:#c8e6c9;text-align:center}',
     '.n{background:#f5f5f5} .gap{background:#ffe0b2}</style>',
     f'<h2>Corpus status — {len(_INCLUDED)} papers in the production semantic '
     f'corpus ({len(_EXCLUDED)} reviews excluded, shown for their extractions)</h2>',
     f'<p>Membership is declared in papers/_corpus/corpus_manifest.json. '
     f'docling {cnt["doc"]} · scout {cnt["scout"]} · deep {cnt["deep"]} · '
     f'KB {cnt["kb"]} · geometry {cnt["geom"]} · '
     f'semantic {cnt["sem"]} · workbench {cnt["wb"]}</p>',
     '<p>exps = total Experiments (a condition sweep contributes one per point); '
     'prof = spatial-profile experiments; series = ExperimentSeries; '
     'canon = curves with at least one axis in a canonical comparison group. '
     'See docs/CANONICALIZATION.md.</p>',
     '<p>exps/prof/series describe the RESOLVED Experiment layer (M2 feeder '
     'granularity); the semantic corpus (ExperimentalCases / ResultSeries) is '
     'summarised in 04_semantic__corpus_summary.html.</p>',
     '<table><tr><th>paper</th><th>corpus</th><th>docling</th><th>scout</th>'
     '<th>deep</th><th>KB</th>'
     '<th>geom</th><th>semantic</th><th>workbench</th>'
     '<th>ALD?</th><th>deeper?</th><th>exps</th><th>prof</th>'
     '<th>series</th><th>canon</th><th>materials</th></tr>']
for sd, st, i in rows:
    h.append(f'<tr><td>{sd}</td><td>{st["member"]}</td>'
             f'{cell(st["doc"])}{cell(st["scout"])}{cell(st["deep"])}'
             f'{cell(st["kb"])}{cell(st["geom"])}{cell(st["sem"])}{cell(st["wb"])}'
             f'<td>{i["ald"]}</td><td>{i["go"]}</td>'
             f'<td>{i["nexp"]}</td><td>{i["prof"]}</td><td>{i["ser"]}</td>'
             f'<td>{i["canon"]}</td><td>{html.escape(i["mats"])}</td></tr>')
# candidate-expansion section, rendered from reports/candidate_corpus_expansion.json.
# Appended AFTER the live-corpus table so the existing status view is unchanged.
try:
    from pipeline.review.candidate_section import render as _render_candidates
except Exception:                                   # pragma: no cover - optional section
    _render_candidates = lambda: []

h.append('</table><h2>Ontology gaps</h2>')
for label, dd in (("materials", miss_m), ("precursors", miss_p), ("coreactants", miss_c)):
    h.append(f'<h3>{label} ({len(dd)})</h3><table><tr><th>term</th><th>papers</th></tr>')
    for k, v in sorted(dd.items()):
        h.append(f'<tr><td class="gap">{html.escape(k)}</td><td>{", ".join(v)}</td></tr>')
    h.append('</table>')
h += _render_candidates()

(P.REPORTS / "03_corpus__corpus_status.html").write_text("\n".join(h))
print(f"\nwrote {P.REPORTS / '03_corpus__corpus_status.html'}")
