#!/usr/bin/env python3
"""R2: one self-contained HTML page per unit from (title, file) pairs: a .csv becomes a table, any other file a <pre>.

    python3 psed_v2/kb/report.py psed_v2/kb/reports/P135a.html "Mapping=psed_v2/kb/reports/P135a.mapping.csv" "Check diff=psed_v2/kb/reports/P135a.check.diff"
"""
import csv
import html
import sys
from pathlib import Path

STYLE = "body{font:13px monospace;margin:16px}table{border-collapse:collapse;margin-bottom:24px}td,th{border:1px solid #999;padding:2px 6px;vertical-align:top;text-align:left;max-width:40em;overflow-wrap:anywhere}pre{white-space:pre-wrap;border:1px solid #999;padding:8px}"


def section(title, path):
    p = Path(path)
    out = [f"<h2>{html.escape(title)}</h2><p>{html.escape(str(p))}</p>"]
    if p.suffix == ".csv":
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
