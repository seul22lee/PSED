#!/usr/bin/env python3
"""reflatten_records.py — rebuild records.json from the CACHED figure_data.json.

No vision/LLM call: it imports flatten_records from 05_figure_extract and replays it
over the stored figure results. Use after changing flatten_records (e.g. the series
label vs material classifier) so existing papers pick up the fix for free.

  python3 scripts/reflatten_records.py <safe_doi> [<safe_doi> ...]
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"

# 05_figure_extract.py isn't a valid module name (leading digit) -> load by path.
_spec = importlib.util.spec_from_file_location(
    "figure_extract", Path(__file__).resolve().parent / "05_figure_extract.py")
_fe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fe)


def reflatten(sd):
    d = EXTRACTED / sd
    fd = d / "figure_data.json"
    if not fd.is_file():
        print(f"  [skip] {sd}: no figure_data.json cache")
        return None
    cached = json.loads(fd.read_text())
    scout = json.loads((d / "scout.json").read_text())
    figresults = cached.get("figures") or []

    before = []
    rj = d / "records.json"
    if rj.is_file():
        before = json.loads(rj.read_text())

    records = _fe.flatten_records(sd, scout, figresults)
    rj.write_text(json.dumps(records, indent=1))

    moved = sum(1 for r in records if r.get("series_label"))
    print(f"  {sd}: {len(before)} -> {len(records)} records | "
          f"{moved} series_label rescued | materials={sorted({r['material'] for r in records})}")
    return records


if __name__ == "__main__":
    for sd in sys.argv[1:]:
        reflatten(sd)
