#!/usr/bin/env python3
"""ingest/reports/review_body.html: every body flag of the final output with its crop, texts and verdict, the repairs,
the units recovered by the lookup near the previous match, and the under-4-word lines by block type.
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/report_body.py

Verdicts come from ingest/answers/body_flags.json (Claude Code on the crops): real = Marker's text differs from the
PDF text layer there; not = a measurement artefact (cause given); a flag whose key is not in the answer set is
"unjudged". "Not checkable" flags show their reason; output-side ones the numbers left unchecked.
"""
import base64
import datetime
import html
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL = HERE / "final"
OUT = HERE / "reports" / "review_body.html"


def key(pid, f):
    return f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}"


def img(pid, crop):
    if not crop:
        return ""
    try:
        b = (FINAL / pid / crop).read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return "(no crop)"
    return f'<img src="data:image/png;base64,{base64.b64encode(b).decode()}">'


def hasd(s):
    return bool(re.search(r"\d", s or ""))


def main():
    ans = {a["flag_key"]: a for a in json.load(open(HERE / "answers" / "body_flags.json"))["items"]}
    rows, newrows, reps, undone, recovered, short, summary = [], [], [], [], [], [], Counter()
    for d in sorted(p for p in FINAL.iterdir() if (p / "structure.json").exists()):
        pid = d.name
        st = json.load(open(d / "structure.json"))
        reps += [(pid, r) for r in st.get("body_repairs", [])]
        undone += [(pid, u) for u in st.get("body_repairs_undone", [])]
        recovered += [(pid, r) for r in st["body_check"].get("recovered", [])]
        for f in st.get("body_flags", []):
            if f["kind"] == "not checkable" and f.get("reason", "").startswith("unit under 4 words"):
                summary["not checkable: unit under 4 words"] += 1
                short.append((pid, f))
                continue
            if f["kind"] == "not checkable":
                v = "not checkable"
                typ = f.get("reason", "")
                cause = (f"output side; numbers not compared: {', '.join(f.get('output_numbers', [])[:12])}" if f.get("side") == "output"
                         else f"{f.get('lines', 1)} line(s), block {f.get('block')}")
            else:
                a = ans.get(key(pid, f))
                v = "unjudged" if a is None else ("real" if a["verdict"] == "real error" else "not")
                typ = (a or {}).get("error_type") or (a or {}).get("measurement_cause") or ""
                cause = (a or {}).get("cause", "") if a else ""
                if f["kind"].startswith("letters") and not typ:
                    typ = f"letters: {', '.join(f.get('layer_words', []))} -> {', '.join(f.get('output_words', []))} (similarity {f.get('similarity')})"
            summary[v] += 1
            row = (f"<tr class='{'nc' if v == 'not checkable' else v}'><td>{html.escape(pid)}<br>p {f['page']}</td><td>{img(pid, f.get('crop'))}</td>"
                   f"<td><b>{html.escape(f['kind'])}</b>{' <b>[output side]</b>' if f.get('side') == 'output' else ''}<br>number: {html.escape(str(f.get('number')))}"
                   f"<br><i>layer:</i> {html.escape(f.get('layer_line', '')[:300])}<br><i>output:</i> {html.escape((f.get('output_sentence') or '')[:300])}</td>"
                   f"<td class='v'>{v}</td><td>{html.escape(typ)}<br><small>{html.escape(cause)}</small></td></tr>")
            rows.append(row)
            if v == "unjudged":
                newrows.append(row)
    n = len(rows)
    import csv
    with (HERE.parent / "corpus" / "manifest.csv").open(newline="", encoding="utf-8") as fh:
        rows = {r["paper_id"]: r for r in csv.DictReader(fh)}
    have = [p.name for p in FINAL.iterdir() if (p / "structure.json").exists()]
    n_in = sum(1 for p in have if rows.get(p, {}).get("in_scope") == "yes")
    out_names = [f"{(rows[p].get('authors') or p).split(',')[0].split(';')[0].strip().split()[-1]} {rows[p].get('year', '')}".strip() for p in sorted(have) if rows.get(p, {}).get("in_scope") != "yes"]
    n_papers = f"{n_in} in-scope papers" + (" and " + ", ".join(out_names) if out_names else "")
    H = [f"""<!doctype html><html><head><meta charset="utf-8"><title>Body flags review</title><style>
body{{font-family:sans-serif;font-size:13px}} table{{border-collapse:collapse}} td{{border:1px solid #ccc;padding:4px;vertical-align:top;max-width:520px}}
img{{max-width:500px}} tr.real td.v{{background:#fdd}} tr.not td.v{{background:#dfd}} tr.unjudged td.v{{background:#fc9}} tr.nc td.v{{background:#eee}}</style></head><body>
<h1>Body flags of the final output ({n} flags in the main table, {len(short)} under-4-word lines, {n_papers})</h1>
<p>Built {datetime.date.today().isoformat()} by ingest/report_body.py from ingest/final/*/structure.json. Verdict per flag from ingest/answers/body_flags.json
(Claude Code on the crop): real = Marker's text differs from the PDF text layer at that number; not = the number is right, the flag is a
measurement artefact (cause given); not checkable = what the check cannot compare (reason given), reviewed like a not-checkable table;
unjudged = not in the answer set. Summary: {dict(summary)}. Repairs applied by body_repair.py: {len(reps)}, undone: {len(undone)}.</p>
<h2>Repairs (countermeasures applied to document.md)</h2><table><tr><th>paper</th><th>page</th><th>kind</th><th>from</th><th>to</th><th>sentence</th></tr>"""]
    H += [f"<tr><td>{html.escape(pid)}</td><td>{r['page']}</td><td>{html.escape(r['kind'])}</td><td>{html.escape(r['from'])}</td><td>{html.escape(r['to'][:200])}</td><td>{html.escape(r['sentence'][:160])}</td></tr>" for pid, r in reps]
    H.append("</table>")
    if undone:
        H.append("<h2>Repairs undone by the recheck (the flag stays)</h2><table><tr><th>paper</th><th>page</th><th>kind</th><th>from</th><th>to</th><th>remaining flag</th></tr>")
        H += [f"<tr><td>{html.escape(pid)}</td><td>{u['page']}</td><td>{html.escape(u['kind'])}</td><td>{html.escape(u['from'])}</td><td>{html.escape(u['to'][:200])}</td><td>{html.escape(u['remaining_flag']['kind'])} {html.escape(str(u['remaining_flag'].get('number')))}</td></tr>" for pid, u in undone]
        H.append("</table>")
    if newrows:
        H.append(f"<h2>Flags not in the answer set ({len(newrows)}; unjudged)</h2><table><tr><th>paper / page</th><th>crop</th><th>flag</th><th>verdict</th><th>type, cause</th></tr>" + "".join(newrows) + "</table>")
    H.append(f"<h2>Units found near the previous match and checked (A: short units, B: garbled lines; {len(recovered)})</h2><table><tr><th>paper / page</th><th>kind, how</th><th>text-layer text</th><th>matched output paragraph</th></tr>")
    H += [f"<tr><td>{html.escape(pid)}<br>p {r['page']}</td><td>{html.escape(r['kind'])}<br>{html.escape(r['how'])}<br>{html.escape(str(r.get('block')))}</td><td>{html.escape(r['layer_text'])}</td><td>{html.escape(r['output_text'])}</td></tr>" for pid, r in recovered]
    H.append("</table><h2>Flags</h2><table><tr><th>paper / page</th><th>crop</th><th>flag</th><th>verdict</th><th>type, cause</th></tr>" + "".join(rows) + "</table>")
    by_bt = Counter((f.get("block") or "?") for _, f in short)
    with_digit = sum(1 for _, f in short if hasd(f["layer_line"]))
    H.append(f"<h2>Not checkable: units under 4 words ({len(short)} lines; with a digit {with_digit}, without {len(short) - with_digit}; by block type: {dict(by_bt)})</h2>")
    for bt in sorted(by_bt, key=lambda b: -by_bt[b]):
        nd = sum(1 for _, f in short if (f.get("block") or "?") == bt and hasd(f["layer_line"]))
        H.append(f"<h3>{html.escape(bt)} ({by_bt[bt]} lines, {nd} with a digit)</h3><table><tr><th>paper / page</th><th>crop</th><th>text-layer line</th></tr>")
        H += [f"<tr><td>{html.escape(pid)}<br>p {f['page']}</td><td>{img(pid, f.get('crop'))}</td><td>{html.escape(f['layer_line'][:300])}{' <b>(digit)</b>' if hasd(f['layer_line']) else ''}</td></tr>"
              for pid, f in short if (f.get("block") or "?") == bt]
        H.append("</table>")
    H.append("</body></html>")
    OUT.write_text("".join(H))
    print(f"review_body.html: {n} flags in the main table, {len(short)} under-4-word lines, {len(reps)} repairs, {len(undone)} undone, {dict(summary)}")


if __name__ == "__main__":
    main()
