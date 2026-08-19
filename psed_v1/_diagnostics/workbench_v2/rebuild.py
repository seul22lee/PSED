#!/usr/bin/env python3
"""Regenerate the frozen PILOT workbench (the regression fixture).

Runs the PRODUCTION workbench build (pipeline.workbench.build_workbench_model)
against the semantic pilot snapshot and writes the artifacts here, so
tests/test_workbench_v2.py keeps pinning the reference behaviour on the frozen
8-paper corpus. The production corpus build is `python3 cli.py workbench`.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.workbench import build_workbench_model as WBM     # noqa: E402

PILOT = ROOT / "_diagnostics" / "semantic_pilot_9papers"

if __name__ == "__main__":
    sys.exit(WBM.main(["--corpus-root", str(PILOT / "papers"),
                       "--papers-file", str(PILOT / "pilot_papers.json"),
                       "--out", str(HERE)]))
