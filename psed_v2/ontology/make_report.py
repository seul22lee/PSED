#!/usr/bin/env python3
"""ontology.yaml + unmapped.csv -> report.html (self-contained), after running the checks.

    python3 psed_v2/ontology/make_report.py

Needs PyYAML. Exits non-zero when a check fails; report.html is still written and shows which.
"""
import csv
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "sources" / "experimental-ideal-schema.json"
EXTENSION_CAP = 15
ROLES = ["condition", "coordinate", "output", "model_parameter"]
# Base quantity ids the criteria expect (Sec. 10). Categorical entries are checked separately
# against vocabularies.categorical_conditions plus crystallinity (an output, Sec. 2).
EXPECTED_BASE = {
    "deposition_temperature", "process_pressure", "pulse_time", "purge_time", "growth_per_cycle",
    "aspect_ratio", "coated_aspect_ratio", "nucleation_period", "refractive_index",
    "absorption_coefficient", "resistivity", "carrier_density", "mobility", "thickness_nonuniformity",
    "composition", "film_density", "film_thickness", "penetration_depth", "equivalent_aspect_ratio",
    "initial_sticking_coefficient", "recombination_probability", "partial_pressure", "surface_coverage",
    "gap", "feature_depth", "feature_extent", "exposure", "step_coverage", "source_temperature"}


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def leaf_paths(node: dict, prefix: str = "") -> list[str]:
    props = node.get("properties")
    if not props:
        return [prefix]
    return [p for k, v in props.items() for p in leaf_paths(v, f"{prefix}/{k}" if prefix else k)]


def base_paths(entry: dict) -> list[str]:
    path = (entry.get("base") or {}).get("path", [])
    return [path] if isinstance(path, str) else list(path)


def bare(ref: str) -> str:
    return re.sub(r"\{.*\}", "", ref)


def run_checks(onto: dict) -> list[tuple[str, bool, str]]:
    entries = onto["entries"]
    ids = [e["id"] for e in entries]
    quantities = [e for e in entries if e["type"] == "quantity"]
    voc = onto["vocabularies"]
    out = []

    leaves = onto["base_sources"]["schema_miner"]["leaf_paths"]
    note = ""
    if SCHEMA.exists():
        if sorted(leaf_paths(json.loads(SCHEMA.read_text()))) != sorted(leaves):
            note = "leaf_paths differ from sources/experimental-ideal-schema.json; "
    else:
        note = "(sources JSON absent; used leaf_paths in ontology.yaml) "
    used = Counter(p for e in entries for p in base_paths(e))
    used.update(x["path"] for x in onto["excluded_base"])
    bad = [p for p in leaves if used[p] != 1] + [p for p in used if p not in leaves]
    out.append(("1. every schema-miner leaf path appears exactly once", not bad and "differ" not in note,
                note + (f"problems: {bad}" if bad else f"{len(leaves)} paths")))

    bad = [e["id"] for e in entries if not (e.get("definition") or "").strip()]
    bad += [e["id"] for e in entries
            if (e.get("base") or {}).get("source") in ("cremers_2019", "popov_2025")
            and not re.search(r"Cremers|Popov", e["definition"])]
    out.append(("2. every entry has a definition; review-defined terms cite the review", not bad, f"problems: {bad}" if bad else ""))

    bad = [e["id"] for e in entries if e["origin"] == "extension" and not e.get("evidence")]
    out.append(("3. every extension entry has gold evidence", not bad, f"problems: {bad}" if bad else ""))

    seen = Counter(a.lower() for e in entries for a in e.get("aliases", []))
    ambiguous = {a.lower() for a in voc["ambiguous_aliases"]}
    bad = [a for a, n in seen.items() if n > 1] + [a for a in seen if a in ambiguous]
    out.append(("4. no alias in two entries; ambiguous words only in ambiguous_aliases", not bad, f"problems: {bad}" if bad else ""))

    ext = [e["id"] for e in quantities if e["origin"] == "extension"]
    base = {e["id"] for e in quantities if e["origin"] == "base"}
    diff = sorted(base ^ EXPECTED_BASE)
    cats = {e["id"] for e in entries if e["type"] == "categorical"}
    cat_diff = sorted(cats ^ (set(voc["categorical_conditions"]) | {"crystallinity"}))
    out.append((f"5. extension quantities <= {EXTENSION_CAP}; base quantities = Sec. 10 list; categoricals = Sec. 12 keys + crystallinity",
                len(ext) <= EXTENSION_CAP and not diff and not cat_diff,
                f"{len(ext)} extension quantities" + (f"; base differs: {diff}" if diff else "")
                + (f"; categoricals differ: {cat_diff}" if cat_diff else "")))

    refs = [bare(r) for t in onto["transforms"] for r in t["inputs"] + [t["output"]] if r not in ("any", "same")]
    refs += [p for e in entries if e["type"] == "model" for p in e.get("parameters", [])]
    bad = sorted({r for r in refs if r not in ids})
    dup = [i for i, n in Counter(ids).items() if n > 1]
    out.append(("6. transform inputs/outputs and model parameters are existing ids; ids unique", not bad and not dup,
                f"problems: {bad + dup}" if bad or dup else ""))

    bad = [e["id"] for e in entries if e["type"] in ("species", "structure") and not e.get("evidence")]
    out.append(("7. no species, structure or process taken from a review table (each has gold evidence)", not bad,
                f"problems: {bad}" if bad else ""))
    return out


def graph_svg(onto: dict) -> str:
    entries = onto["entries"]
    cols = {r: [e for e in entries if e.get("role") == r] for r in ROLES}
    cols["model"] = [e for e in entries if e["type"] == "model"]
    w, h, gapx, gapy, top = 215, 18, 40, 5, 30
    pos, parts = {}, []
    for ci, (name, col) in enumerate(cols.items()):
        x = 10 + ci * (w + gapx)
        parts.append(f'<text x="{x}" y="18" font-weight="bold">{esc(name)}</text>')
        for ri, e in enumerate(col):
            pos[e["id"]] = (x, top + ri * (h + gapy))
    edges = []
    for t in onto["transforms"]:
        edges += [(bare(i), bare(t["output"]), "derives", t["id"]) for i in t["inputs"] if i != "any"]
    for e in cols["model"]:
        edges += [(p, e["id"], "parameter_of", "") for p in e.get("parameters", [])]
    for a, b, kind, label in edges:
        if a not in pos or b not in pos or a == b:
            continue
        (x1, y1), (x2, y2) = pos[a], pos[b]
        x1, x2 = (x1 + w, x2) if x2 >= x1 else (x1, x2 + w)
        if pos[a][0] == pos[b][0]:   # same column: bow out on the right
            x1 = x2 = pos[a][0] + w
            d = f"M{x1},{y1 + h / 2} C{x1 + 30},{y1 + h / 2} {x2 + 30},{y2 + h / 2} {x2},{y2 + h / 2}"
        else:
            mid = (x1 + x2) / 2
            d = f"M{x1},{y1 + h / 2} C{mid},{y1 + h / 2} {mid},{y2 + h / 2} {x2},{y2 + h / 2}"
        parts.append(f'<path d="{d}" class="{kind}"><title>{esc(kind)} {esc(label)}: {esc(a)} -> {esc(b)}</title></path>')
    for e in entries:
        if e["id"] not in pos:
            continue
        x, y = pos[e["id"]]
        cls = e["origin"] + ("" if e.get("evidence") else " faded")
        parts.append(f'<g class="{cls}"><title>{esc(e["definition"])}</title>'
                     f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>'
                     f'<text x="{x + 5}" y="{y + 13}">{esc(e["id"])}</text></g>')
    height = top + max(len(c) for c in cols.values()) * (h + gapy) + 10
    width = 10 + len(cols) * (w + gapx)
    return f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-size="11">{"".join(parts)}</svg>'


def table(header: list[str], rows: list[list]) -> str:
    head = "".join(f"<th>{esc(c)}</th>" for c in header)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def main() -> int:
    onto = yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))
    with (HERE / "unmapped.csv").open(newline="", encoding="utf-8") as f:
        unmapped = list(csv.DictReader(f))
    entries = onto["entries"]
    checks = run_checks(onto)
    ok = all(c[1] for c in checks)

    counts = Counter((e["type"], e["origin"], "with evidence" if e.get("evidence") else "no evidence") for e in entries)
    n_ext = sum(e["type"] == "quantity" and e["origin"] == "extension" for e in entries)
    summary = table(["type", "origin", "evidence", "entries"], [[*k, n] for k, n in sorted(counts.items())])
    summary += f"<p>{len(entries)} entries. Extension quantities: {n_ext} of at most {EXTENSION_CAP}.</p>"
    summary += table(["check", "result", "detail"], [[c, "pass" if good else "FAIL", d] for c, good, d in checks])

    def dev(e):
        d = e.get("deviation")
        return f'{d["type"]}: {d["reason"]}' if d else ""

    entry_rows = [[e["id"], e["type"], e.get("role", ""), e.get("unit", ""), e["origin"],
                   ", ".join(e.get("qualifiers", [])), "; ".join(e.get("evidence", [])), dev(e)] for e in entries]
    by_path = {p: e for e in entries for p in base_paths(e)}
    excluded = {x["path"]: x for x in onto["excluded_base"]}
    diff_rows = []
    for p in onto["base_sources"]["schema_miner"]["leaf_paths"]:
        if p in by_path:
            d = by_path[p].get("deviation") or {}
            diff_rows.append([p, by_path[p]["id"], d.get("type", "—"), d.get("reason", "")])
        elif p in excluded:
            diff_rows.append([p, "excluded_base", excluded[p]["deviation"], excluded[p]["reason"]])
        else:
            diff_rows.append([p, "MISSING", "", ""])
    diff_rows += [["(all fields)", "—", n["type"], f'{n["what"]}: {n["reason"]}'] for n in onto["base_notes"]]
    unit_rows = [[d, u["canonical"], ", ".join(u["accepted"])] for d, u in onto["units"].items()]
    reasons = Counter(r["reason"] for r in unmapped)
    unmapped_html = table(["reason", "labels"], reasons.most_common())
    unmapped_html += table(["reason", "paper", "location", "label", "unit"],
                           [[r["reason"], r["paper"], r["location"], r["label"], r["unit"]]
                            for r in sorted(unmapped, key=lambda r: (r["reason"], r["paper"]))])

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>PSED v2 ontology v0</title>
<style>
body {{ font-family: sans-serif; font-size: 14px; margin: 16px; color: #222; background: #fff; }}
table {{ border-collapse: collapse; margin: 8px 0 16px; }}
th, td {{ border: 1px solid #bbb; padding: 3px 6px; text-align: left; vertical-align: top; }}
th {{ background: #eee; }}
.wide {{ overflow-x: auto; }}
svg rect {{ stroke: #444; }}
svg .base rect {{ fill: #cfe2f3; }}
svg .extension rect {{ fill: #fde3b4; }}
svg .faded {{ opacity: 0.35; }}
svg path {{ fill: none; stroke-width: 1.2; }}
svg path.derives {{ stroke: #2a7; }}
svg path.parameter_of {{ stroke: #b36; stroke-dasharray: 4 3; }}
</style></head><body>
<h1>PSED v2 ontology v0: completion report</h1>
<p>Checks: <b>{"all passed" if ok else "FAILED"}</b>.</p>
<h2>1. Summary</h2>{summary}
<h2>2. Graph</h2>
<p>Blue = base, orange = extension, faded = no gold evidence. Green line = derives (transform),
dashed red line = parameter_of. Hover a node for its definition.</p>
<div class="wide">{graph_svg(onto)}</div>
<h2>3. Entries</h2><div class="wide">{table(["id", "type", "role", "unit", "origin", "qualifiers", "evidence", "deviation"], entry_rows)}</div>
<h2>4. schema-miner diff</h2>{table(["schema-miner path", "entry", "deviation", "reason"], diff_rows)}
<h2>5. Units</h2>{table(["dimension", "canonical", "accepted"], unit_rows)}
<h2>6. Unmapped</h2>{unmapped_html}
</body></html>
"""
    (HERE / "report.html").write_text(page, encoding="utf-8")
    for c, good, d in checks:
        print("pass" if good else "FAIL", c, d)
    print(f"{HERE / 'report.html'}: {len(entries)} entries, {len(unmapped)} unmapped labels")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
