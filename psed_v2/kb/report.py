#!/usr/bin/env python3
"""R2: one self-contained HTML page per unit from (title, file) pairs: a .csv becomes a table, a .graph.json an inline SVG of two trees
(P145), any other file a <pre>.

    python3 psed_v2/kb/report.py psed_v2/kb/reports/P135a.html "Mapping=psed_v2/kb/reports/P135a.mapping.csv" "Check diff=psed_v2/kb/reports/P135a.check.diff"
"""
import csv
import html
import sys
from pathlib import Path

STYLE = "body{font:13px monospace;margin:16px}table{border-collapse:collapse;margin-bottom:24px}td,th{border:1px solid #999;padding:2px 6px;vertical-align:top;text-align:left;max-width:40em;overflow-wrap:anywhere}pre{white-space:pre-wrap;border:1px solid #999;padding:8px}"


GRAPH_FILL = {"matched": "#c8f0c8", "agrees": "#c8f0c8", "merged": "#f8dfa0", "split": "#f8dfa0", "merged+split": "#f8dfa0", "differs": "#f8dfa0",
              "double-assigned": "#f8dfa0", "missing": "#f6c0c0", "extra": "#f6c0c0", "unassigned": "#f6c0c0", "esi_only": "#dddddd"}
ROW, INDENT, BOX, LEAF, WRAP, HALF, GAP = 18, 22, 330, 170, 20, 780, 60


def graph(path):
    """P145: a .graph.json {left: [nodes], right: [nodes], links: [[right id, left id]]} (node: id, parent, label, status) as one static
    inline SVG: two trees side by side (gold left, pass 0 right), one indentation column per depth; a node with more than WRAP leaf
    children places them in columns; fill by status (GRAPH_FILL); a dashed line per link."""
    import json
    G = json.loads(Path(path).read_text(encoding="utf-8"))
    pos, parts = {}, []

    def tree(nodes, x0, side):
        kids, ids = {}, {n["id"] for n in nodes}
        for n in nodes:
            kids.setdefault(n["parent"] if n["parent"] in ids else None, []).append(n)
        y = [0]

        def place(n, depth):
            x = x0 + depth * INDENT
            pos[(side, n["id"])] = (x, y[0] * ROW, BOX - depth * INDENT, n)
            y[0] += 1
            ch = kids.get(n["id"], [])
            leaves = [c for c in ch if c["id"] not in kids]
            inner = [c for c in ch if c["id"] in kids]
            if len(leaves) > WRAP:
                cols = max(1, min((HALF - (depth + 1) * INDENT) // LEAF, -(-len(leaves) // WRAP)))
                rows = -(-len(leaves) // cols)
                for k, c in enumerate(leaves):
                    pos[(side, c["id"])] = (x0 + (depth + 1) * INDENT + (k // rows) * LEAF, (y[0] + k % rows) * ROW, LEAF - 6, c)
                y[0] += rows
            else:
                for c in leaves:
                    place(c, depth + 1)
            for c in inner:
                place(c, depth + 1)
        for r in kids.get(None, []):
            place(r, 0)
        return y[0]
    h = max(tree(G["left"], 0, "L"), tree(G["right"], HALF + GAP, "R")) * ROW + ROW
    for (side, i), (x, y, w, n) in pos.items():                                 # parent-child elbows
        p = pos.get((side, n["parent"]))
        if p:
            parts.append(f'<path d="M{p[0] + 6},{p[1] + ROW - 4} V{y + ROW / 2} H{x}" fill="none" stroke="#999" stroke-width="1"/>')
    for (side, i), (x, y, w, n) in pos.items():
        fill = GRAPH_FILL.get(n.get("status", ""), "#ffffff")
        chars = max(4, int((w - 6) / 6.7))
        lab = n["label"] if len(n["label"]) <= chars else n["label"][:chars - 1] + "…"
        parts.append(f'<rect x="{x}" y="{y + 1}" width="{w}" height="{ROW - 3}" fill="{fill}" stroke="#777" stroke-width="0.5"/>'
                     f'<text x="{x + 3}" y="{y + ROW - 5}" font-size="11" font-family="monospace"><title>{html.escape(n["label"])}</title>{html.escape(lab)}</text>')
    for r, l in G.get("links", []):                                             # pass-0 node -> the gold node it is paired with
        a, b = pos.get(("R", r)), pos.get(("L", l))
        if a and b:
            parts.append(f'<line x1="{a[0]}" y1="{a[1] + ROW / 2}" x2="{b[0] + b[2]}" y2="{b[1] + ROW / 2}" stroke="#36c" stroke-width="0.6" stroke-dasharray="3,3"/>')
    head = (f'<text x="0" y="12" font-size="12" font-family="monospace" font-weight="bold">gold</text>'
            f'<text x="{HALF + GAP}" y="12" font-size="12" font-family="monospace" font-weight="bold">pass 0</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -4 {2 * HALF + GAP} {h + 20}" width="100%">'
            f'<g transform="translate(0,18)">{"".join(parts)}</g>{head}</svg>')


def section(title, path):
    p = Path(path)
    out = [f"<h2>{html.escape(title)}</h2><p>{html.escape(str(p))}</p>"]
    if p.name.endswith(".graph.json"):                                          # P145: the experiment graph
        out.append(graph(p))
    elif p.suffix == ".csv":
        rows = list(csv.reader(p.open(newline="", encoding="utf-8")))
        if rows:
            out.append("<table><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in rows[0]) + "</tr>")
            out += ["<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:]]
            out.append("</table>")
    else:
        out.append(f"<pre>{html.escape(p.read_text(encoding='utf-8'))}</pre>")
    return "\n".join(out)


def main(argv):
    out, pairs = Path(argv[0]), [a.split("=", 1) for a in argv[1:]]
    body = "\n".join(section(t, p) for t, p in pairs)
    out.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(out.stem)}</title><style>{STYLE}</style></head>"
                   f"<body><h1>{html.escape(out.stem)}</h1>\n{body}\n</body></html>\n", encoding="utf-8")
    print(f"{out}: {len(pairs)} sections")


if __name__ == "__main__":
    main(sys.argv[1:])
