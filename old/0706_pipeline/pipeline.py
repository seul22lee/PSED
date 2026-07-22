"""
0706_pipeline/pipeline.py  —  orchestrator
Lists stages + their input scope + status, and dispatches the stages that are
already implemented. Ported stages raise NotImplementedError with the source
script to port from, so nothing silently no-ops.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from config import STAGES, INPUT_SCOPE, PORT_FROM, ONTOLOGY_DIR, ROOT

# stage_key -> (scope_key or "-", status, runner)
#   runner: ("py", path) runs a script; None means not yet ported.
DONE = {
    "s00": ("-",                 "done", ("py", ONTOLOGY_DIR / "build_ontology.py")),
    "s09": ("-",                 "done", ("py", ROOT.parent / "0604_kg" / "09_kg_onto.py")),
}
SCOPE_OF = {
    "s01": "-", "s02": "-", "s03": "figure_data", "s04": "equations",
    "s05": "-", "s06": "experiment_schema", "s07": "-", "s08": "-", "s10": "-",
}


def status(key):
    if key in DONE:
        return DONE[key]
    scope = SCOPE_OF.get(key, "-")
    return (scope, "port", None)


def cmd_list():
    print(f"{'stage':<6}{'name':<20}{'scope':<22}{'status':<8}port-from")
    print("-" * 92)
    for key, name in STAGES.items():
        scope_key, st, _ = status(key)
        scope = INPUT_SCOPE.get(scope_key, scope_key if scope_key != "-" else "")
        mark = "✅" if st == "done" else "· "
        print(f"{key:<6}{name:<20}{scope:<22}{mark}{st:<6}{PORT_FROM.get(key,'')}")


def cmd_stage(key):
    scope_key, st, runner = status(key)
    if runner is None:
        src = PORT_FROM.get(key, "(unknown)")
        raise NotImplementedError(
            f"stage {key} ({STAGES.get(key)}) not ported yet — port from {src}")
    kind, path = runner
    print(f"running {key} -> {path}")
    subprocess.run([sys.executable, str(path)], check=True)


def cmd_benchmark_scope():
    raise NotImplementedError(
        "benchmark-scope not implemented yet. Plan: run s06 schema extraction under "
        "INPUT_SCOPE in {abstract, abstract+conclusion, full} on the 3-paper set, "
        "then report per-scope schema-field coverage and hallucinated-field rate. "
        "Say the word and I'll build it.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--stage")
    ap.add_argument("--benchmark-scope", action="store_true")
    a = ap.parse_args()
    if a.list or (not a.stage and not a.benchmark_scope):
        cmd_list()
    elif a.stage:
        cmd_stage(a.stage)
    elif a.benchmark_scope:
        cmd_benchmark_scope()


if __name__ == "__main__":
    main()
