#!/usr/bin/env python3
"""
cli.py — the supported entry point. Run everything from the psed_v1 root.

    python3 cli.py <stage> [args]

The repository previously had five competing ways in: `run_all.py`, numbered
scripts invoked by path, `python3 -m` on some modules, direct execution of
others, and a dead `pipeline.py` stage table pointing outside the project. This is the
one that is supported.

Stages, in pipeline order:

    parse       PDF            -> papers/<id>/extracted/{document.md,structure.json,figures/}
    inventory   docling output -> papers/<id>/extracted/figure_inventory.json  (no LLM)
    scout       document       -> papers/<id>/extracted/scout.json          (LLM)
    figures     figure crops   -> papers/<id>/extracted/{figure_data,records}.json (vision LLM)
    geometry    text + tables  -> papers/<id>/extracted/geometry.json       (LLM)
    pressure    text + tables  -> papers/<id>/extracted/pressure.json       (LLM)
    resolve     all the above  -> papers/<id>/{resolved/*,review.json}
    canonical   resolved       -> papers/<id>/canonical/curves.json
    semantic    resolved+canonical -> papers/<id>/semantic/*.json  (no LLM)
    workbench   semantic corpus -> papers/_corpus/workbench/       (no LLM)
    m2          semantic corpus -> twin/m2_report.html + reports/04_twin_mpc__m2_report.html
    m3          semantic corpus -> twin/m3_validation.html + reports/04_twin_mpc__m3_validation.html
                (m2/m3 run the twin against the production semantic corpus; `review`
                 never reruns them -- regenerate explicitly with these stages)
    kg          canonical      -> papers/_corpus/knowledge_graph_onto.json
    ontology    ontology src   -> ontology/ald_ontology.{json,yaml}
    review      everything     -> reports/*.html
    validate    structural + data checks

`resolve`, `canonical`, `kg` and `review` need no API key; the extraction stages
do (GOOGLE_API_KEY, read from the environment or a .env in this directory).
"""
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STAGES = {
    "parse":     "pipeline.parse.docling_parse",
    "inventory": "pipeline.figures.inventory",
    "scout":     "pipeline.scout.scout",
    "figures":   "pipeline.figures.figure_extract",
    "geometry":  "pipeline.text.geometry",
    "pressure":  "pipeline.text.pressure",
    "resolve":   "pipeline.resolve.to_kb",
    "canonical": "pipeline.canonical.build_canonical",
    "semantic":  "pipeline.semantic.build_semantic",
    "workbench": "pipeline.workbench.build_workbench_model",
    "kg":        "pipeline.review.build_kg",
    "ontology":  "ontology.build_ontology",
    "m2":        "twin.m2_design",
    "m3":        "twin.twin_validation",
}
#: stages that are several modules run in order
GROUPS = {
    "review": ["pipeline.review.build_dashboard", "pipeline.review.build_analysis",
               "pipeline.review.build_recipes", "pipeline.review.viz_recipes",
               "pipeline.review.corpus_status", "pipeline.review.corpus_dashboard",
               "pipeline.review.semantic_summary", "pipeline.review.build_index"],
}


def _run(mod, argv):
    sys.argv = [mod] + list(argv)
    runpy.run_module(mod, run_name="__main__", alter_sys=True)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        print("stages: %s" % ", ".join(list(STAGES) + list(GROUPS) + ["validate"]))
        return 0
    stage, rest = argv[0], argv[1:]
    if stage == "validate":
        rc = 0
        # `tests/integration/test_layout.py` never existed under that name, so `validate`
        # always exited non-zero regardless of the code under test. Its nearest relative,
        # validate_layout.py, imports a `paper_layout` module that no longer exists
        # anywhere in the tree — dead since an earlier refactor, and left alone here.
        for t in ("tests/integration/test_standalone.py",
                  "tests/regression/test_figure_provenance.py"):
            rc |= subprocess.call([sys.executable, str(ROOT / t)], cwd=str(ROOT))
        return rc
    if stage in GROUPS:
        for m in GROUPS[stage]:
            print("== %s" % m)
            _run(m, rest)
        return 0
    if stage not in STAGES:
        print("unknown stage %r; try --help" % stage, file=sys.stderr)
        return 2
    _run(STAGES[stage], rest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
