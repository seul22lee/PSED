#!/usr/bin/env python3
"""ingest/NUMBERS.md: the numbers of the ingest output with the file each comes from, and the per-paper body table.
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/numbers_md.py

Everything is read from ingest/final/<paper_id>/structure.json, ingest/marker/<paper_id>/bands.json, ingest/answers/
and glyph_codes.json. The judged numbers (tables wrong on the page, the equation verdicts, body flags real or not,
the distinct real errors) come from the answer set and are marked as such. Two recorded numbers that no file holds
is kept in RECORDED with its origin: the breakdown of the unmatched output paragraphs by kind (a read-only recount of
the first 44 papers on 2026-10-13). The distinct real errors, their classes, causes and repair status are computed by
judged_counts() from the answer set, body_repairs and the current flags (also used by the ERRORS.md rows).

The table has two number columns: the in-scope papers (manifest in_scope = yes, covered by the answer set) and, on
its own and outside every total, Guyon 2004 (10.1016_j.cattod.2003.11.022: ingested, excluded from the scope, not
judged).
"""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL, MARKER, ANSWERS = HERE / "final", HERE / "marker", HERE / "answers"

RECORDED = {
    "unmatched_kinds": ("kinds from a read-only recount of the first 44 papers on 2026-10-13: 1,046 at or after the References heading; "
                        "before it 527: 294 equations, 127 author/affiliation/licence/furniture lines, 91 headings/labels/fragments, "
                        "9 captions, 4 author lists read as text, 2 reaction table rows"),
}

# error classes of ERRORS.md, by the first keyword found in the answer set's error_type (order matters)
CLASSES = [("margin line number", "margin numbers"), ("citation", "citations"), ("subscript digit", "subscripts"), ("exponent sign", "exponent sign"),
           ("prescript", "prescripts of J"), ("sentence, paragraph or caption dropped", "dropped text"), ("lookalike", "lookalike letters"),
           ("affiliation mark", "affiliation marks"), ("letter read as digit", "letter/digit"), ("letter/digit", "letter/digit"),
           ("digit changed", "digits"), ("text added", "text added"), ("decimal point", "decimal points"),
           ("text out of order", "caption label out of order"), ("caption label fused", "caption label fused"), ("letter case", "letter case")]


def error_class(t):
    t = (t or "").split("; the same key")[0].lower()        # a key shared by two flag kinds carries a note after the type
    for key, name in CLASSES:
        if key in t:
            return name
    return "other"


def judged_counts(pids):
    """From answers/body_flags.json, final/*/structure.json body_repairs and the current body_flags: the distinct real errors
    (grouped by distinct_error where the item has one, else by paper, page and class; the margin numbers of a paper as one
    error), their classes, their causes (the answer set's labels as they are), and how the repairs cover them: corrected =
    a repair covers a key of the error and none of its keys is still flagged; partly = a repair covers a key and another
    key is still flagged; flagged only = no repair covers it (regression.py's coverage rule: same page, the number in the
    repaired token, sentence or restored line; a dropped-line repair for a 'line not found' key)."""
    import re
    from collections import Counter, defaultdict
    items = [a for a in json.load(open(ANSWERS / "body_flags.json"))["items"] if a["paper_id"] in pids and a["verdict"] == "real error"]
    reps, flagged = defaultdict(list), set()
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        reps[pid] = st.get("body_repairs", [])
        flagged |= {f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}" for f in st["body_flags"] if f["kind"] != "not checkable"}
    plain = lambda s: re.sub(r"<[^>]+>|[_^{}$\\]", "", s or "")
    def covering(a):
        pid, page, _, num = a["flag_key"].split("|")
        for r in reps[pid]:
            if r["page"] != int(page):
                continue
            if num == "None":
                if r["kind"].startswith("dropped line"):
                    return r
            elif any(num in x or num.lstrip("-") in x for x in (plain(r["from"]), plain(r["to"]), r.get("sentence", ""))):
                return r
        return None
    groups = defaultdict(list)
    for a in items:
        c = error_class(a.get("error_type"))
        g = a.get("distinct_error") or (f"{a['paper_id']}|margin numbers" if c == "margin numbers" else f"{a['paper_id']}|{a['page']}|{c}")
        groups[g].append(a)
    out = {"n": len(groups), "classes": Counter(), "causes": Counter(), "corrected": [], "partly": [], "flagged_only": [], "groups": {}}
    for g, its in groups.items():
        cls = error_class(its[0].get("error_type")); out["classes"][cls] += 1; out["causes"][its[0].get("cause") or "none"] += 1
        pid = its[0]["paper_id"]; pages = {a["page"] for a in its}
        covered = []
        for r in [covering(a) for a in its]:
            if r is not None and r not in covered:
                covered.append(r)
        if covered and any(r["kind"].startswith("dropped line") for r in covered):   # a dropped passage: every R2 line of the page
            for r in reps[pid]:
                if r["kind"].startswith("dropped line") and r["page"] in pages and r not in covered:
                    covered.append(r)
        still = [a["flag_key"] for a in its if a["flag_key"] in flagged]
        status = "corrected" if covered and not still else "partly" if covered else "flagged only"
        label = f"{its[0]['paper_id']} p{its[0]['page']} {cls}"
        out[{"corrected": "corrected", "partly": "partly", "flagged only": "flagged_only"}[status]].append(label)
        out["groups"][g] = {"class": cls, "status": status, "keys": [a["flag_key"] for a in its], "pages": sorted({a["page"] for a in its}), "paper": its[0]["paper_id"],
                            "repairs": [(r["page"], r["kind"][:12], plain(r["from"]), plain(r["to"])[:60]) for r in covered], "still_flagged": still}
    return out


def block(pids, judged):
    """The table rows (item, number, source) and the per-paper rows for one set of papers. judged: whether the answer
    set covers the set (the in-scope papers) or not (Guyon 2004): judged numbers then say 'not judged'."""
    T, E, B, K, R, NC, SC = Counter(), Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    cov, rows, nopaper, rec, lnum, figs = [], [], 0, Counter(), Counter(), Counter()
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        for c in st["captions"]:
            if c["kind"] == "table":
                T["total"] += 1
                if "check" not in c:
                    raise SystemExit(f"table without a check: {pid} table {c.get('number')} p {c.get('page')} (every table must be ok, flag or not checkable)")
                T[c["check"]] += 1
            elif c["kind"] == "figure":
                figs["numbered" if c.get("number") else "unnumbered"] += 1
            else:
                figs[c["kind"]] += 1
        for e in st["equations"]:
            E["pairs"] += 1
            E[e["status"]] += 1
        c = st["body_check"]["counts"]
        B["lines"] += c["lines"]
        B["checked"] += c.get("checked", 0)
        B["rotated"] += c.get("not checkable: rotated text (characters)", 0)
        cov.append(100 * c.get("checked", 0) / c["lines"] if c["lines"] else 100)
        for k, v in c.items():
            if k.startswith("not checkable") and "rotated" not in k:
                NC[k.replace("not checkable: ", "")] += v
        B["unmatched"] += c.get("output paragraphs with numbers matched by no unit (not compared; references, tables, furniture)", 0)
        n = 0
        layer = out = eqglyph = 0
        for f in st["body_flags"]:
            if f["kind"] == "not checkable":
                if f.get("side") == "output":
                    out += 1
                else:
                    layer += 1
                    eqglyph += "equation or weak line" in (f.get("reason") or "")
            else:
                n += 1
                K[f["kind"]] += 1
                SC[f.get("crop_scope", "line")] += 1
        K["not checkable, layer side"] += layer
        K["not checkable, output side"] += out
        K["equation lines with an undecoded glyph"] += eqglyph
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
        rows.append((pid, c["lines"], c.get("checked", 0), und, c.get("not checkable: rotated text (characters)", 0), other, n, layer + out, len(st["body_repairs"])))
    bands = Counter()
    for pid in pids:
        for b in json.load(open(MARKER / pid / "bands.json")):
            bands["records"] += 1
            bands["applied"] += bool(b.get("applied"))
    ans_t = [a for a in json.load(open(ANSWERS / "tables.json"))["items"] if a["paper_id"] in pids]
    ans_e = [a for a in json.load(open(ANSWERS / "equations.json"))["items"] if a["paper_id"] in pids]
    ans_b = [a for a in json.load(open(ANSWERS / "body_flags.json"))["items"] if a["paper_id"] in pids]
    wrong = {(a["paper_id"], str(a["page"]), a["table"], a["ordinal"]) for a in ans_t if a["verdict"] == "real error"}
    wrong_flag = wrong_nc = wrong_ok = right_flag = 0
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
                wrong_ok += t["check"] == "ok"
            elif t["check"] == "flag":
                right_flag += 1
    judged_keys = {a["flag_key"]: a["verdict"] for a in ans_b}
    real = notc = unj = 0
    for pid in pids:
        st = json.load(open(FINAL / pid / "structure.json"))
        for f in st["body_flags"]:
            if f["kind"] == "not checkable":
                continue
            v = judged_keys.get(f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}")
            real += v == "real error"
            notc += v == "not an error"
            unj += v is None
    g = json.load(open(HERE / "glyph_codes.json"))
    n_entries = sum(len(v) for v in g["families"].values()) + sum(len(v) for v in g["instances"].values())
    sj = "structure.json"
    flags = sum(v for k, v in K.items() if not k.startswith("not checkable") and not k.startswith("equation lines"))
    ncl, nco = K["not checkable, layer side"], K["not checkable, output side"]
    ed = Counter(a["verdict"] for a in ans_e if a["status"] == "differ")
    es = Counter(a["verdict"] for a in ans_e if a["status"] not in ("differ", "agree"))
    n_ag = sum(1 for a in ans_e if a["status"] == "agree")
    L = []
    L.append(f"| Papers ingested | {len(pids)} | `ingest/final/` (manifest `marker` = ok) |")
    L.append(f"| **Tables** total | {T['total']} | {sj} `captions[kind=table]` |")
    L.append(f"| Tables `check` = flag | {T['flag']} | {sj} `captions[].check` |")
    L.append(f"| Tables `check` = ok | {T['ok']} | {sj} `captions[].check` |")
    L.append(f"| Tables `check` = not checkable | {T['not checkable']} | {sj} `captions[].check` |")
    L.append(f"| Tables wrong on the page (judged) | {len(wrong)} of {len(ans_t)} judged; reaching the review {wrong_flag + wrong_nc} ({wrong_flag} flagged, {wrong_nc} not checkable), missed with `check` = ok {wrong_ok}; {right_flag} right tables flagged | `answers/tables.json` against `check` |")
    L.append(f"| **Equations** pairs | {E['pairs']} | {sj} `equations` |")
    L.append(f"| Equations `agree` | {E['agree']} | {sj} `equations[].status` |")
    L.append(f"| Equations `differ` | {E['differ']} | {sj} `equations[].status` |")
    L.append(f"| Equations single tool | {E['docling only'] + E['marker only']} ({E['docling only']} docling only, {E['marker only']} marker only) | {sj} `equations[].status` |")
    L.append(f"| Equation pairs judged (answer set) | {len(ans_e)} items: {n_ag} agree accepted (not judged); {sum(ed.values())} differ pairs judged on the crop: "
             f"Marker right {ed.get('Marker right', 0)}, Docling right {ed.get('Docling right', 0)}, both wrong {ed.get('both wrong', 0)}, equivalent {ed.get('not an error', 0)}; "
             f"{sum(es.values())} single-tool items judged: Docling right {es.get('Docling right', 0)}, Docling wrong {es.get('Docling wrong', 0)}, Marker right {es.get('Marker right', 0)}, Marker wrong {es.get('Marker wrong', 0)} | `answers/equations.json` |")
    L.append(f"| **Body** lines read | {B['lines']:,} | {sj} `body_check.counts.lines` |")
    L.append(f"| Body lines checked | {B['checked']:,} ({100 * B['checked'] / B['lines']:.1f} %; median {statistics.median(cov):.0f} % per paper, min {min(cov):.0f} %) | {sj} `body_check.counts.checked` |")
    L.append(f"| Body lines not checkable, total | {B['lines'] - B['checked']} (every one covered by a layer-side \"not checkable\" flag) | {sj} `body_check.counts`, `body_flags` |")
    for k in ("unit under 4 words", "garbled text-layer line (overlapping duplicate layer)", "unit too short to locate in the output (fewer than 3 words)", "undecoded glyph"):
        L.append(f"| not checkable: {k} | {NC.get(k, 0)} | {sj} `body_check.counts` |")
    L.append(f"| Equation lines with an undecoded glyph (the extra direction of their paragraph blocked) | {K['equation lines with an undecoded glyph']}, each a layer-side flag | {sj} `body_flags[kind=not checkable]` |")
    L.append(f"| Output sentences not covered by the text layer (numbers not compared) | {NC.get('output sentence not covered by the text layer (its numbers not compared)', 0)}, each an output-side flag | {sj} `body_check.counts` |")
    L.append(f"| Output paragraphs blocked by an undecoded glyph in an equation or neighbour line | {NC.get('paragraph with an equation or neighbour line holding an undecoded glyph (extra numbers not compared)', 0)}, each an output-side flag | {sj} `body_check.counts` |")
    L.append(f"| Output paragraphs with numbers matched by no unit (counted, not flagged) | {B['unmatched']:,}{' (' + RECORDED['unmatched_kinds'] + ')' if judged else ''} | {sj} `body_check.counts`; kinds recorded |")
    L.append(f"| Units recovered by the lookup near the previous match | {sum(rec.values())} (short units {sum(v for (k, h), v in rec.items() if k != 'garbled line')}: "
             f"{rec.get(('short unit', 'exact'), 0) + rec.get(('unit too short to locate', 'exact'), 0)} exact, {rec.get(('short unit', 'without'), 0) + rec.get(('unit too short to locate', 'without'), 0)} without spaces; "
             f"garbled lines {sum(v for (k, h), v in rec.items() if k == 'garbled line')}: {rec.get(('garbled line', 'without'), 0)} without spaces, {rec.get(('garbled line', 'similarity'), 0)} by similarity) | {sj} `body_check.recovered` |")
    L.append(f"| Rotated characters (not read) | {B['rotated']:,} | {sj} `body_check.counts` |")
    L.append(f"| **Body flags** (number or letter kinds) | {flags} | {sj} `body_flags` |")
    for k in ("number of the text layer missing from the output paragraph", "number of the output paragraph absent from the text layer", "line not found in the output", "letters of the text layer differ from the output"):
        L.append(f"| flags: {k} | {K.get(k, 0)} | {sj} `body_flags[].kind` |")
    L.append(f"| flags cropping the paragraph block / the line | {SC['paragraph']} / {SC['line']} | {sj} `body_flags[].crop_scope` |")
    L.append(f"| Body flags judged (answer set) | {real + notc} of {flags}: {real} real, {notc} not errors (precision {100 * real / max(1, real + notc):.0f} %){', ' + str(unj) + ' unjudged' if unj else ''} | `answers/body_flags.json` against `body_flags` |")
    L.append(f"| Answer-set body flag keys (all passes) | {len(ans_b)}: {sum(1 for a in ans_b if a['verdict'] == 'real error')} real, {sum(1 for a in ans_b if a['verdict'] != 'real error')} not errors | `answers/body_flags.json` |")
    L.append(f"| Papers without a number flag | {nopaper} | {sj} `body_flags` |")
    L.append(f"| **Not-checkable flags** | {ncl + nco}: layer side {ncl}, output side {nco} | {sj} `body_flags[kind=not checkable]` |")
    L.append(f"| **Repairs** applied | {sum(v for k, v in R.items() if k != 'undone')} records ({R['number replaced from the text layer']} R1 numbers replaced, {R['dropped line restored from the text layer']} R2 lines restored), {R['undone']} undone | {sj} `body_repairs`, `body_repairs_undone` |")
    jc = judged_counts(pids) if judged else None
    if jc:
        classes = ", ".join(f"{v} {k}" for k, v in sorted(jc["classes"].items(), key=lambda x: (-x[1], x[0])))
        causes = ", ".join(f"{k} {v}" for k, v in sorted(jc["causes"].items(), key=lambda x: (-x[1], x[0])))
        L.append(f"| Distinct real body errors (judged, a lower bound) | {jc['n']}: {classes}; causes (answer-set labels): {causes} | `answers/body_flags.json` real keys grouped by distinct_error, else by paper, page and class (numbers_md.py CLASSES); margin numbers one error per paper |")
        L.append(f"| Distinct real errors corrected / partly / flagged only | {len(jc['corrected'])} corrected ({'; '.join(jc['corrected'])}), {len(jc['partly'])} partly ({'; '.join(jc['partly'])}), {len(jc['flagged_only'])} flagged only (the margin numbers among them, removed by line_numbers.py with the leftovers flagged) | `body_repairs` covering a key of the error (regression.py's rule), `body_flags` for a key still flagged |")
    else:
        L.append("| Distinct real body errors (judged, a lower bound) | not judged | `answers/body_flags.json` |")
        L.append("| Distinct real errors corrected / partly / flagged only | not judged | `body_repairs`, `body_flags` |")
    L.append(f"| Margin line numbers removed | {lnum['removed']:,} in {lnum['papers']} paper, {lnum['kept']} real numbers kept | {sj} `body_check.line_numbers` |")
    L.append(f"| Band repairs (parse_marker.py --bands) | {bands['applied']} applied of {bands['records']} records | `marker/<id>/bands.json` |")
    src = Counter(json.load(open(FINAL / pid / "structure.json")).get("abstract_source") for pid in pids)
    L.append(f"| Abstracts | {len(pids)}: {', '.join(f'{v} {k}' for k, v in sorted(src.items(), key=lambda x: -x[1]))} | {sj} `abstract_source` |")
    other = ", ".join(f"{v} {k}" for k, v in sorted(figs.items()) if k not in ("numbered", "unnumbered"))
    L.append(f"| Figure captions | {figs['numbered'] + figs['unnumbered']} ({figs['numbered']} numbered, {figs['unnumbered']} unnumbered pictures){'; other kinds: ' + other if other else ''} | {sj} `captions[kind=figure]`{' and the other non-table kinds' if other else ''} |")
    L.append(f"| Glyph table | {n_entries} entries ({len(g['families'])} families, {len(g['instances'])} subsets), {len(g.get('undecoded', {}))} groups left undecoded with the reason | `glyph_codes.json` |")
    J = ("Tables wrong on the page", "Equation pairs judged", "Body flags judged", "Answer-set body flag keys", "Distinct real")
    out = []
    for line in L:
        item, number, source = [c.strip() for c in line.strip().strip("|").split(" | ", 2)]
        source = source.rstrip(" |")
        if item.startswith(J) and not judged:
            number = "not judged (out of scope)"
        if item.startswith("Glyph table") and not judged:
            number = "one table for all papers"
        out.append((item, number, source))
    return out, rows


FIG_COLS = ["captioned figures", "panels: plot", "spectrum", "micrograph", "photo", "schematic", "map", "table_image", "other", "points", "peaks", "cells", "tokens in", "tokens out",
            "flags F1", "F2", "F3", "F4", "F5", "F6", "verdicts ok", "wrong_axis", "wrong_points", "missed_series", "wrong_type", "unreadable", "repeat: series agreeing"]
PANEL_TYPES = ["plot", "spectrum", "micrograph", "photo", "schematic", "map", "table_image", "other"]
VERDICTS = ["ok", "wrong_axis", "wrong_points", "missed_series", "wrong_type", "unreadable"]


def figures_rows():
    """Per paper with a figures.json: the figure-stage numbers (captioned figures, panels by type, points, tokens, flags by kind,
    verdicts by kind from answers/figures.json, repeat agreement from figures_repeat.json); the papers in manifest order of the
    stage (sorted by id here) and a total row. [] when no paper has a figures.json."""
    ans = json.load(open(ANSWERS / "figures.json"))["items"] if (ANSWERS / "figures.json").exists() else []
    V = Counter()
    for v in ans:
        V[(v["paper_id"], v["verdict"])] += 1
    rows = []
    for d in sorted(FINAL.iterdir()):
        f = d / "figures.json"
        if not f.exists():
            continue
        fj = json.load(open(f)); pid = fj["paper_id"]
        P, F, pts, pks, cls, ti, to = Counter(), Counter(), 0, 0, 0, 0, 0
        for fig in fj["figures"]:
            ti += fig["tokens"]["in"]; to += fig["tokens"]["out"]
            for fl in fig["flags"]:
                F[fl["flag"]] += 1
            for pn in fig["panels"]:
                P[pn["panel_type"]] += 1
                pts += sum(len(s["points"]) for s in pn.get("series") or [])
                pks += len(pn.get("peaks") or [])
                cls += len(pn.get("cells") or [])
        rep = ""
        r = d / "figures_repeat.json"
        if r.exists():
            rj = json.load(open(r)); a = sum(c["agreeing"] for c in rj.get("comparison", [])); t = sum(c["series"] for c in rj.get("comparison", []))
            rep = f"{a} of {t}"
        rows.append([pid, len(fj["figures"])] + [P[t] for t in PANEL_TYPES] + [pts, pks, cls, ti, to] + [F[f"F{i}"] for i in range(1, 7)] + [V[(pid, v)] for v in VERDICTS] + [rep])
    if rows:
        tot = ["**total**"] + [sum(r[i] for r in rows) for i in range(1, len(FIG_COLS))]
        a = sum(int(r[-1].split(" of ")[0]) for r in rows if r[-1]); t = sum(int(r[-1].split(" of ")[1]) for r in rows if r[-1])
        tot.append(f"{a} of {t}" if t else "")
        rows.append(tot)
    return rows


def main():
    pids = sorted(p.name for p in FINAL.iterdir() if (p / "structure.json").exists())
    with (HERE.parent / "corpus" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        scope = {r["paper_id"]: r["in_scope"] for r in csv.DictReader(f)}
    inscope = [p for p in pids if scope.get(p) == "yes"]
    outscope = [p for p in pids if scope.get(p) != "yes"]
    (a_in, rows_in), (a_out, rows_out) = block(inscope, True), block(outscope, False)
    L = [f"# Ingest numbers ({len(inscope)} in-scope papers with a PDF; written by ingest/numbers_md.py from the final output)\n"]
    L.append("One table; every number in INGEST, ERRORS and the plan must match it. \"structure.json\" means the sum over\n"
             f"`ingest/final/<paper_id>/structure.json`. The first number column is the {len(inscope)} in-scope papers (manifest `in_scope` = yes),\n"
             "which the answer set `ingest/answers/` (Claude Code's page judgements) covers in full: every judged number (tables wrong\n"
             "on the page, equation verdicts, body flags real or not, distinct real errors) holds for them. The second column is\n"
             f"{', '.join(outscope)} (Guyon 2004: ingested, excluded from the scope as not an ALD paper, not judged); it stands on its own and is\n"
             "in no total. One recorded number names its origin (the kinds of the unmatched paragraphs, recounted for the first 44 papers).\n")
    L.append(f"| Item | {len(inscope)} in scope | Guyon 2004 (out of scope) | Source |\n|---|---|---|---|")
    for (item, n_in, src), (_, n_out, _) in zip(a_in, a_out):
        L.append(f"| {item} | {n_in} | {n_out} | {src} |")
    L.append("\n## Per paper (body check)\n")
    L.append("| paper | body lines read | checked | share | not checkable: undecoded glyph (lines) | rotated (characters) | other not checkable (lines/sentences) | number or letter flags | not-checkable flags | repairs |\n|---|---|---|---|---|---|---|---|---|---|")
    for r in rows_in:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {round(100 * r[2] / r[1]) if r[1] else 0} % | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} |")
    tot = [sum(r[i] for r in rows_in) for i in range(1, 9)]
    L.append(f"| **total, {len(inscope)} in scope** | {tot[0]:,} | {tot[1]:,} | {round(100 * tot[1] / tot[0])} % | {tot[2]} | {tot[3]:,} | {tot[4]} | {tot[5]} | {tot[6]} | {tot[7]} |")
    for r in rows_out:
        L.append(f"| {r[0]} (out of scope, in no total) | {r[1]} | {r[2]} | {round(100 * r[2] / r[1]) if r[1] else 0} % | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} |")
    fr = figures_rows()
    if fr:
        L.append(f"\n## Figure stage (VLM; ingest/figures.py, {len(fr) - 1} papers with a figures.json)\n")
        L.append("Per paper: the captioned figures sent (structure.json captions of kind figure with caption text and images), the panels returned by type, the points read,\n"
                 "the tokens (in: images and prompt; out: the response with the model's reasoning tokens), the rule flags F1-F6 (figures.json `flags`, counted per\n"
                 "figure and kind), the verdicts of `answers/figures.json` on every plot/spectrum panel, and the repeat agreement (series agreeing of series compared,\n"
                 "figures_repeat.json). Captioned figures and unnumbered pictures are not the same count as the Figure captions row above: pictures without caption text are never sent.\n")
        L.append("| paper | " + " | ".join(FIG_COLS) + " |\n|---|" + "---|" * len(FIG_COLS))
        for r in fr:
            L.append("| " + " | ".join(str(x) for x in r) + " |")
    (HERE / "NUMBERS.md").write_text("\n".join(L) + "\n")
    print(f"NUMBERS.md written: {len(inscope)} in scope + {len(outscope)} out of scope")
    for it in a_in: print("  ", it[0], "|", it[1][:160])


if __name__ == "__main__":
    main()
