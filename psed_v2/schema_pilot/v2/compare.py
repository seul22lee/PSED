#!/usr/bin/env python3
"""Compares the v2 tables with the first pilot (commit 840674c, schema_pilot/<paper_id>/*.csv) and writes v2/compare.md.

    python3 psed_v2/schema_pilot/v2/compare.py

Rows per table, and knowledge gained or lost: values matched by quantity (or printed label) and number, series by figure and panel.
"""
import csv, io, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inventory import PAPERS
REPO = HERE.parents[2]
FIRST = "840674c"
TABLES = ["sample", "condition", "series", "value"]


def first(pid, t):
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{FIRST}:psed_v2/schema_pilot/{pid}/{t}.csv"], capture_output=True, text=True)
    return list(csv.DictReader(io.StringIO(out.stdout))) if out.returncode == 0 else []


sys.path.insert(0, str(HERE.parent))
import lists as LS
SCALE = {"nm": ("len", 1e-9), "Å": ("len", 1e-10), "A": ("len", 1e-10), "µm": ("len", 1e-6), "um": ("len", 1e-6), "mm": ("len", 1e-3), "m": ("len", 1),
         "Pa": ("p", 1), "hPa": ("p", 100), "mbar": ("p", 100), "Torr": ("p", 133.322), "mTorr": ("p", 0.133322), "s": ("t", 1), "ms": ("t", 1e-3), "min": ("t", 60)}


def canon(q, x, unit):
    """a first-pilot number in the v2 canonical unit of its quantity, when the units convert."""
    to = LS.UNITS.get(q)
    u = (unit or "").replace("/cycle", "").replace(" per cycle", "").strip()
    if to is None or u == to.replace("/cycle", "") or u not in SCALE or to not in SCALE or SCALE[u][0] != SCALE[to][0]:
        return x
    return x * SCALE[u][1] / SCALE[to][1]


def vkey(v):
    q = v["quantity"] if v["quantity"] != "other" else "other:" + re.sub(r"[{(].*", "", v["label_as_printed"]).strip().lower()
    n = re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", (v["value"] or v["value_min"] or "").replace("−", "-"))
    try:
        return q, round(canon(v["quantity"], float(n[0]), v.get("unit", "")), 6) if n else (v["value"] or "").strip().lower()
    except ValueError:
        return q, n[0]


def main():
    lines = [f"# v2 against the first pilot ({FIRST})", "", "| Paper | " + " | ".join(f"{t} first → v2" for t in TABLES) + " |", "|---|" + "---|" * len(TABLES)]
    detail = []
    for pid, key in PAPERS.items():
        A = {t: first(pid, t) for t in TABLES}
        B = {t: list(csv.DictReader((HERE / pid / f"{t}.csv").open(encoding="utf-8"))) if (HERE / pid / f"{t}.csv").exists() else [] for t in TABLES}
        lines.append(f"| {key} | " + " | ".join(f"{len(A[t])} → {len(B[t])}" for t in TABLES) + " |")
        ka = {vkey(v): v for v in A["value"]}; kb = {vkey(v): v for v in B["value"]}
        lost = [ka[k] for k in ka if k not in kb]; gained = [kb[k] for k in kb if k not in ka]
        nb = {k[1] for k in kb}; na = {k[1] for k in ka}
        relab = [k for k in ka if k not in kb and k[1] in nb and isinstance(k[1], float)]
        fa = {(s["figure"], s["panel"]) for s in A["series"]}; fb = {(s["figure"], s["panel"]) for s in B["series"]}
        detail += [f"## {key}", "", f"Values: {len(ka)} distinct in the first pilot, {len(kb)} in v2; {len(set(ka) & set(kb))} shared, {len(gained)} only in v2, {len(lost)} only in the first pilot; of these, {len(relab)} of the first pilot's numbers are in v2 under another quantity (relabelled, e.g. {"; ".join(f"{k[0]} = {k[1]}" for k in relab[:4])}).",
                   f"Figure panels with a series: {len(fa)} first, {len(fb)} v2; only in v2: {', '.join(sorted(f'{a}{b}' for a, b in fb - fa)) or 'none'}; only in the first: {', '.join(sorted(f'{a}{b}' for a, b in fa - fb)) or 'none'}.",
                   "", "Only in v2, number not in the first pilot at all (first 15): " + "; ".join(f"{k[0]} = {k[1]}" for k in [k for k in kb if k not in ka and k[1] not in na][:15]),
                   "", "Only in the first pilot, number not in v2 at all (first 15): " + "; ".join(f"{k[0]} = {k[1]}" for k in [k for k in ka if k not in kb and k[1] not in nb][:15]), "",
                   f"Counts: numbers only in v2 {len([k for k in kb if k not in ka and k[1] not in na])}, numbers only in the first pilot {len([k for k in ka if k not in kb and k[1] not in nb])}.", ""]
    (HERE / "compare.md").write_text("\n".join(lines + [""] + detail) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
