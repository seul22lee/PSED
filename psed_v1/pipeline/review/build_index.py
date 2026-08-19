#!/usr/bin/env python3
"""
build_index.py — reports/index.html, the landing page for the CURRENT reports.

A curated map, not a directory listing: every entry says which population it
describes (production semantic corpus, resolved Experiment layer, historical
acquisition funnel, milestone deliverable), and genuinely historical pages are
labelled as such instead of being presented as current corpus truth.

Run:  python3 -m pipeline.review.build_index   (part of `cli.py review`)
"""
import html as _html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import paths as P                                               # noqa: E402

#: (section, [(file, title, note, tag)]) — tag: current | legacy | historical
SECTIONS = [
    ("Production semantic corpus (current)", [
        ("04_semantic__corpus_summary.html", "Semantic corpus summary",
         "41 included papers · ExperimentalCases / MeasurementActs / ResultSeries / "
         "points · invariants · declared gaps", "current"),
        ("04_semantic__scientific_comparison_workbench.html",
         "Scientific comparison Workbench",
         "the production Workbench (copy of papers/_corpus/workbench/, refreshed by "
         "`cli.py review`)", "current"),
    ]),
    ("Corpus & pipeline status (current)", [
        ("03_corpus__corpus_status.html", "Corpus status",
         "per-paper pipeline stages over the declared 44 (41 included + 3 reviews), "
         "plus ontology coverage gaps", "current"),
        ("03_corpus__corpus_dashboard.html", "Corpus dashboard",
         "historical acquisition funnel (labelled) + current extraction state + "
         "production-corpus rows", "current"),
    ]),
    ("Ontology (current)", [
        ("01_ontology__ontology_viewer.html", "Ontology viewer",
         "interactive class/quantity/relations browser", "current"),
        ("01_ontology__ontology.html", "Ontology page",
         "compiled ontology rendering", "current"),
    ]),
    ("Resolved Experiment layer (legacy granularity — M2 feeder)", [
        ("02_extraction__experiment_dashboard.html", "Experiment dashboard",
         "ontology-conformance of the resolved Experiment records; NOT the semantic "
         "corpus (banner on page)", "legacy"),
        ("02_extraction__analysis_dashboard.html", "Analysis dashboard",
         "recipe-oriented analysis over the resolved layer", "legacy"),
        ("02_extraction__recipes.html", "Recipes",
         "per-experiment recipes with probabilistic gap-filling", "legacy"),
        ("02_extraction__m2_recipes.html", "M2 recipes",
         "recipe completeness + Argonne-JSON emission; M2 migration to the semantic "
         "layer pending", "legacy"),
    ]),
    ("Twin — production semantic corpus (current)", [
        ("04_twin_mpc__m2_report.html", "M2 inverse-design certificate",
         "literature evidence from the production semantic corpus (41-paper "
         "manifest, canonical chemistry); regenerate with `cli.py m2`", "current"),
        ("04_twin_mpc__m3_validation.html", "M3 validation brief",
         "candidates from semantic ResultSeries via Workbench reachability, with "
         "the full candidate funnel; regenerate with `cli.py m3`", "current"),
    ]),
    ("Milestone deliverables (twin / MPC / orchestration)", [
        ("04_twin_mpc__m1_report.html", "M1 report", "", "milestone"),
        ("04_twin_mpc__m4_benchmark.html", "M4 benchmark", "", "milestone"),
        ("04_twin_mpc__ylilammi_gallery.html", "Ylilammi gallery", "", "milestone"),
        ("05_orchestration__m5_orchestration.html", "M5 orchestration", "", "milestone"),
        ("05_orchestration__eval__m5_design.html", "M5 design eval", "", "milestone"),
    ]),
    ("Historical snapshots (kept for provenance, not current truth)", [
        ("02_extraction__phase_ab_summary.html", "Phase A+B summary",
         "July extraction-phase snapshot; no maintained generator", "historical"),
        ("02_extraction__kg_viewer.html", "KG viewer (snapshot)",
         "knowledge-graph view of an earlier resolved layer; regenerate via "
         "`cli.py kg`", "historical"),
        ("FIGURE_PROVENANCE_REPAIR_REPORT.md", "Figure-provenance repair report",
         "the repair campaign record", "historical"),
    ]),
]

TAG = {"current": ("#0a7a3d", "CURRENT"), "legacy": ("#b97800", "LEGACY LAYER"),
       "milestone": ("#2a5fd6", "MILESTONE"), "historical": ("#8b919b", "HISTORICAL")}


def main():
    rows = []
    for section, items in SECTIONS:
        rows.append("<h2>%s</h2><ul>" % _html.escape(section))
        for fn, title, note, tag in items:
            color, label = TAG[tag]
            exists = (P.REPORTS / fn).exists()
            miss = "" if exists else " <span style='color:#b23a00'>(missing — regenerate)</span>"
            rows.append(
                "<li><span style='color:%s;font-size:10px;font-weight:700'>%s</span> "
                "<a href='%s'>%s</a>%s<br><span class=sm>%s</span></li>"
                % (color, label, _html.escape(fn), _html.escape(title), miss,
                   _html.escape(note)))
        rows.append("</ul>")
    page = """<!doctype html><meta charset="utf-8"><title>PSED reports</title><style>
body{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:26px 22px}h1{font-size:22px;margin:0 0 4px}
h2{font-size:14px;margin:20px 0 6px}ul{margin:4px 0;padding-left:18px}li{margin:6px 0}
.sm{font-size:11.5px;color:#565c66}a{color:#2a5fd6}</style><div class=wrap>
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600">PSED</div>
<h1>Reports</h1>
<div class=sm>Regenerate the current set with <code>python3 cli.py review</code>.
Production data authority: papers/_corpus/ (corpus_manifest, semantic_invariants,
workbench). Pages labelled LEGACY read the resolved Experiment layer; HISTORICAL
pages are provenance snapshots.</div>
%s</div>""" % "\n".join(rows)
    out = P.REPORTS / "index.html"
    out.write_text(page)
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
