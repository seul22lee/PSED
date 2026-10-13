#!/usr/bin/env python3
"""ingest/NUMBERS.md: the numbers of the ingest output with the file each comes from, and the per-paper body table.
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/numbers_md.py

Everything is read from ingest/final/<paper_id>/structure.json, ingest/marker/<paper_id>/bands.json, ingest/answers/
and glyph_codes.json. The judged numbers (the distinct real errors per class, which repairs correct them, the equation
verdicts) come from the answer set and are marked as such. Two recorded numbers that no file holds are kept in RECORDED
with their origin: the breakdown of the unmatched output paragraphs by kind (a read-only recount of 2026-10-13) and
the class list of the 44 distinct errors (ingest/ERRORS.md).
"""
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL, MARKER, ANSWERS = HERE / "final", HERE / "marker", HERE / "answers"

RECORDED = {
    "unmatched_kinds": ("read-only recount 2026-10-13: 1,046 at or after the References heading; before it 527: 294 equations, "
                        "127 author/affiliation/licence/furniture lines, 91 headings/labels/fragments, 9 captions, "
                        "4 author lists read as text, 2 reaction table rows"),
    "distinct_errors": ("44: 10 dropped text, 8 citations, 6 letter/digit, 5 lookalike letters, 4 digits, 3 subscripts, "
                        "3 text added, 2 decimal points, 1 exponent sign, 1 caption label out of order, 1 margin numbers "
                        "(ingest/ERRORS.md, judged on crops)"),
    "corrected": "8 corrected (each viewed on its crop), 1 partly (10.1186_s11671-015-0872-9 Figure 1 caption: 2 of 3 lines restored), "
                 "35 flagged only (one of them, the margin numbers, removed by line_numbers.py with 5 leftovers flagged)",
}


def main():
    T, E, B, K, R, NC, SC, A = Counter(), Counter(), Counter(), Counter(), Counter(), Counter(), Counter(), {}
    cov, rows, nopaper, rec, lnum, figs = [], [], 0, Counter(), Counter(), Counter()
    pids = sorted(p.name for p in FINAL.iterdir() if (p / "structure.json").exists())
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        for c in st["captions"]:
            if c["kind"] == "table":
                T["total"] += 1
                T[c["check"]] += 1
            else:
                figs["numbered" if c.get("number") else "unnumbered"] += 1
        for e in st["equations"]:
            E["pairs"] += 1
            E[e["status"]] += 1
        c = st["body_check"]["counts"]
        B["lines"] += c["lines"]
        B["checked"] += c["checked"]
        B["rotated"] += c.get("not checkable: rotated text (characters)", 0)
        cov.append(100 * c["checked"] / c["lines"] if c["lines"] else 100)
        for k, v in c.items():
            if k.startswith("not checkable") and "rotated" not in k:
                NC[k.replace("not checkable: ", "")] += v
        B["unmatched"] += c.get("output paragraphs with numbers matched by no unit (not compared; references, tables, furniture)", 0)
        n = 0
        layer = out = 0
        for f in st["body_flags"]:
            if f["kind"] == "not checkable":
                if f.get("side") == "output":
                    out += 1
                else:
                    layer += 1
            else:
                n += 1
                K[f["kind"]] += 1
                SC[f.get("crop_scope", "line")] += 1
        K["not checkable, layer side"] += layer
        K["not checkable, output side"] += out
        if n == 0:
            nopaper += 1
        for r in st["body_repairs"]:
            R[r["kind"]] += 1
        R["undone"] += len(st.get("body_repairs_undone", []))
        for r in st["body_check"].get("recovered", []):
            rec[(r["kind"], r["how"].split(" ")[0])] += 1
        ln = st["body_check"].get("line_numbers") or {}
        if ln.get("removed"):
            lnum["papers"] += 1
            lnum["removed"] += ln["removed"]
            lnum["kept"] += ln.get("kept_real", 0)
        und = c.get("not checkable: undecoded glyph", 0)
        other = sum(v for k, v in c.items() if k.startswith("not checkable") and "undecoded" not in k and "rotated" not in k)
        rows.append((pid, c["lines"], c["checked"], und, c.get("not checkable: rotated text (characters)", 0), other, n, layer + out, len(st["body_repairs"])))
    bands = Counter()
    for pid in pids:
        for b in json.load(open(MARKER / pid / "bands.json")):
            bands["records"] += 1
            bands["applied"] += bool(b.get("applied"))
    ans_t = json.load(open(ANSWERS / "tables.json"))["items"]
    ans_e = json.load(open(ANSWERS / "equations.json"))["items"]
    ans_b = json.load(open(ANSWERS / "body_flags.json"))["items"]
    wrong = {(a["paper_id"], str(a["page"]), a["table"], a["ordinal"]) for a in ans_t if a["verdict"] == "real error"}
    wrong_flag = wrong_nc = right_flag = 0
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        seen = Counter()
        for t in [c for c in st["captions"] if c["kind"] == "table"]:
            k = (str(t["page"]), t["number"])
            key = (pid, str(t["page"]), t["number"], seen[k])
            seen[k] += 1
            if key in wrong:
                wrong_flag += t["check"] == "flag"
                wrong_nc += t["check"] == "not checkable"
            elif t["check"] == "flag":
                right_flag += 1
    ev = Counter(a["verdict"] for a in ans_e)
    judged = {a["flag_key"]: a["verdict"] for a in ans_b}
    real = notc = unj = 0
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        for f in st["body_flags"]:
            if f["kind"] == "not checkable":
                continue
            v = judged.get(f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}")
            real += v == "real error"
            notc += v == "not an error"
            unj += v is None
    g = json.load(open(HERE / "glyph_codes.json"))
    n_entries = sum(len(v) for v in g["families"].values()) + sum(len(v) for v in g["instances"].values())
    sj = "structure.json"
    flags = sum(v for k, v in K.items() if not k.startswith("not checkable"))
    ncl, nco = K["not checkable, layer side"], K["not checkable, output side"]
    L = []
    L.append(f"# Ingest numbers ({len(pids)} in-scope papers with a PDF; written by ingest/numbers_md.py from the final output)\n")
    L.append("One table; every number in INGEST, ERRORS and the plan must match it. \"structure.json\" means the sum over\n"
             "`ingest/final/<paper_id>/structure.json`. Judged numbers come from the answer set `ingest/answers/` (Claude Code's\n"
             "page judgements) and are marked as such; two recorded numbers name their origin.\n")
    L.append("| Item | Number | Source |\n|---|---|---|")
    L.append(f"| Papers ingested | {len(pids)} | `ingest/final/` (manifest `marker` = ok) |")
    L.append(f"| **Tables** total | {T['total']} | {sj} `captions[kind=table]` |")
    L.append(f"| Tables `check` = flag | {T['flag']} | {sj} `captions[].check` |")
    L.append(f"| Tables `check` = ok | {T['ok']} | {sj} `captions[].check` |")
    L.append(f"| Tables `check` = not checkable | {T['not checkable']} | {sj} `captions[].check` |")
    L.append(f"| Tables wrong on the page (judged) | {len(wrong)} of {T['total']}; {wrong_flag} of them flagged, {wrong_nc} not checkable; {right_flag} right tables flagged | `answers/tables.json` against `check` |")
    L.append(f"| **Equations** pairs | {E['pairs']} | {sj} `equations` |")
    L.append(f"| Equations `agree` | {E['agree']} | {sj} `equations[].status` |")
    L.append(f"| Equations `differ` | {E['differ']} | {sj} `equations[].status` |")
    L.append(f"| Equations single tool | {E['docling only'] + E['marker only']} ({E['docling only']} docling only, {E['marker only']} marker only) | {sj} `equations[].status` |")
    ed = Counter(a["verdict"] for a in ans_e if a["status"] == "differ")
    es = Counter(a["verdict"] for a in ans_e if a["status"] not in ("differ", "agree"))
    n_ag = sum(1 for a in ans_e if a["status"] == "agree")
    L.append(f"| Equation pairs judged (answer set, 44 papers) | {len(ans_e)} items: {n_ag} agree accepted (not judged); {sum(ed.values())} differ pairs judged on the crop: "
             f"Marker right {ed.get('Marker right', 0)}, Docling right {ed.get('Docling right', 0)}, both wrong {ed.get('both wrong', 0)}, equivalent {ed.get('not an error', 0)}; "
             f"{sum(es.values())} single-tool items judged: Docling right {es.get('Docling right', 0)}, Docling wrong {es.get('Docling wrong', 0)}, Marker right {es.get('Marker right', 0)}, Marker wrong {es.get('Marker wrong', 0)} | `answers/equations.json` |")
    L.append(f"| **Body** lines read | {B['lines']:,} | {sj} `body_check.counts.lines` |")
    L.append(f"| Body lines checked | {B['checked']:,} ({100 * B['checked'] / B['lines']:.1f} %; median {statistics.median(cov):.0f} % per paper, min {min(cov):.0f} %) | {sj} `body_check.counts.checked` |")
    L.append(f"| Body lines not checkable, total | {B['lines'] - B['checked']} (every one covered by a layer-side \"not checkable\" flag) | {sj} `body_check.counts`, `body_flags` |")
    for k in ("unit under 4 words", "garbled text-layer line (overlapping duplicate layer)", "unit too short to locate in the output (fewer than 3 words)", "undecoded glyph"):
        L.append(f"| not checkable: {k} | {NC.get(k, 0)} | {sj} `body_check.counts` |")
    L.append(f"| Output sentences not covered by the text layer (numbers not compared) | {NC.get('output sentence not covered by the text layer (its numbers not compared)', 0)}, each an output-side flag | {sj} `body_check.counts` |")
    L.append(f"| Output paragraphs blocked by an undecoded glyph in an equation or neighbour line | {NC.get('paragraph with an equation or neighbour line holding an undecoded glyph (extra numbers not compared)', 0)}, each an output-side flag | {sj} `body_check.counts` |")
    L.append(f"| Output paragraphs with numbers matched by no unit (counted, not flagged) | {B['unmatched']:,} ({RECORDED['unmatched_kinds']}) | {sj} `body_check.counts`; kinds recorded |")
    L.append(f"| Units recovered by the lookup near the previous match | {sum(rec.values())} (short units {sum(v for (k, h), v in rec.items() if k != 'garbled line')}: "
             f"{rec.get(('short unit', 'exact'), 0) + rec.get(('unit too short to locate', 'exact'), 0)} exact, {rec.get(('short unit', 'without'), 0) + rec.get(('unit too short to locate', 'without'), 0)} without spaces; "
             f"garbled lines {sum(v for (k, h), v in rec.items() if k == 'garbled line')}: {rec.get(('garbled line', 'without'), 0)} without spaces, {rec.get(('garbled line', 'similarity'), 0)} by similarity) | {sj} `body_check.recovered` |")
    L.append(f"| Rotated characters (not read) | {B['rotated']:,} | {sj} `body_check.counts` |")
    L.append(f"| **Body flags** (number or letter kinds) | {flags} | {sj} `body_flags` |")
    for k in ("number of the text layer missing from the output paragraph", "number of the output paragraph absent from the text layer", "line not found in the output", "letters of the text layer differ from the output"):
        L.append(f"| flags: {k} | {K.get(k, 0)}{' (not yet judged)' if k.startswith('letters') and unj else ''} | {sj} `body_flags[].kind` |")
    L.append(f"| flags cropping the paragraph block / the line | {SC['paragraph']} / {SC['line']} | {sj} `body_flags[].crop_scope` |")
    L.append(f"| Body flags judged (answer set) | {real + notc} of {flags}: {real} real, {notc} not errors (precision {100 * real / max(1, real + notc):.0f} %){', ' + str(unj) + ' unjudged' if unj else ''} | `answers/body_flags.json` against `body_flags` |")
    L.append(f"| Answer-set body flag keys (all passes) | {len(ans_b)}: {sum(1 for a in ans_b if a['verdict'] == 'real error')} real, {sum(1 for a in ans_b if a['verdict'] != 'real error')} not errors | `answers/body_flags.json` |")
    L.append(f"| Papers without a number flag | {nopaper} | {sj} `body_flags` |")
    L.append(f"| **Not-checkable flags** | {ncl + nco}: layer side {ncl}, output side {nco} | {sj} `body_flags[kind=not checkable]` |")
    L.append(f"| **Repairs** applied | {sum(v for k, v in R.items() if k != 'undone')} records ({R['number replaced from the text layer']} R1 numbers replaced, {R['dropped line restored from the text layer']} R2 lines restored), {R['undone']} undone | {sj} `body_repairs`, `body_repairs_undone` |")
    L.append(f"| Distinct real body errors (judged) | {RECORDED['distinct_errors']} | `answers/body_flags.json` verdicts grouped by error, classes recorded from ERRORS.md |")
    L.append(f"| Distinct real errors corrected / partly / flagged only | {RECORDED['corrected']} | `body_repairs`, `body_flags`, recorded |")
    L.append(f"| Margin line numbers removed | {lnum['removed']:,} in {lnum['papers']} paper, {lnum['kept']} real numbers kept | {sj} `body_check.line_numbers` |")
    L.append(f"| Band repairs (parse_marker.py --bands) | {bands['applied']} applied of {bands['records']} records | `marker/<id>/bands.json` |")
    src = Counter(json.load(open(FINAL / pid / "structure.json")).get("abstract_source") for pid in pids)
    L.append(f"| Abstracts | {len(pids)}: {', '.join(f'{v} {k}' for k, v in sorted(src.items(), key=lambda x: -x[1]))} | {sj} `abstract_source` |")
    L.append(f"| Figure captions | {figs['numbered'] + figs['unnumbered']} ({figs['numbered']} numbered, {figs['unnumbered']} unnumbered pictures) | {sj} `captions[kind=figure]` |")
    L.append(f"| Glyph table | {n_entries} entries ({len(g['families'])} families, {len(g['instances'])} subsets), {len(g.get('undecoded', {}))} groups left undecoded with the reason | `glyph_codes.json` |")
    L.append("\n## Per paper (body check)\n")
    L.append("| paper | body lines read | checked | share | not checkable: undecoded glyph (lines) | rotated (characters) | other not checkable (lines/sentences) | number or letter flags | not-checkable flags | repairs |\n|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {round(100 * r[2] / r[1]) if r[1] else 0} % | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} |")
    (HERE / "NUMBERS.md").write_text("\n".join(L) + "\n")
    print(f"NUMBERS.md written: tables {T['total']}, equations {E['pairs']}, lines {B['lines']:,} checked {B['checked']:,}, flags {flags}, not-checkable {ncl + nco}, repairs {sum(v for k, v in R.items() if k != 'undone')}")


if __name__ == "__main__":
    main()
