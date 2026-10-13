#!/usr/bin/env python3
"""One output per paper from the two ingest tools: ingest/final/<paper_id>/.

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/merge.py <paper_id> [...] | --all

Marker supplies the body, the abstract, the figures, the captions and the tables (with their rule
check), Docling and Marker together the equations. No tool runs here; it reads
ingest/marker/<paper_id>/ (structure.json, document.md, images, table crops; written by
parse_marker.py and structure_marker.py) and ingest/docling/<paper_id>/equations.json (written by
parse_docling.py --formulas). Writes:

    final/<paper_id>/document.md       Marker's document.md (running lines removed)
    final/<paper_id>/structure.json    {abstract, abstract_source, sections, n_pictures, n_tables,
                                        captions[...] as Marker's structure.json (tables carry check,
                                        check_reasons, crop), equations[{page, bbox [l, t, r, b] from
                                        the top-left, number, docling, marker, status}], body_flags
                                        and body_check (body_check.py: numbers of the decoded text
                                        layer vs document.md, per paragraph, with line crops), sources}
    final/<paper_id>/figures/          the image files the captions and table crops refer to

Equations: Docling's formula items and Marker's equations are paired on the same page by their
boxes (IoU plus vertical overlap, at least 0.6), the rest by the printed number; each pair is
"agree" when the two LaTeX strings are equal after notation normalisation (\\text{}, \\left/\\right,
spacing, aligned environments, trailing number, \\cdot/\\times, braces), else "differ"; an equation
only one tool has is "docling only" / "marker only". A "differ" pair is for review at extract time.
On the 13 Marker papers (2026-10-12, judged on crops): 103 pairs, after the R1/R2 formula crops and
the Marker rules 74 agree and 29 differ (Marker right 14, Docling right 7, both wrong 3, formatting 3).
"""
import csv
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"
MANIFEST = CORPUS / "manifest.csv"
RAW = CORPUS / "raw"
DOCLING = HERE / "docling"
MARKER = HERE / "marker"
FINAL = HERE / "final"


def norm_latex(tex):
    """LaTeX in one notation for the agreement test (no change to the stored strings)."""
    t = tex or ""
    t = re.sub(r"\\tag\s*\{[^}]*\}", "", t)
    t = re.sub(r"(\\quad|\\qquad|\\,|\;|\\!|\\ )\s*\(\s*[A-Za-z]?\d(?:\s*\d)*[a-z]?\s*\)\s*(\\\\)?\s*$", "", t)
    t = re.sub(r"\(\s*[A-Za-z]?\d(?:\s*\d)*[a-z]?\s*\)\s*(\\\\)?\s*$", "", t)
    t = re.sub(r"\[\s*\d{1,2}\s*\]\s*$", "", t)
    t = re.sub(r"\\(left|right|displaystyle|quad|qquad|Bigg?[lrm]?|bigg?[lrm]?)(?![A-Za-z])", "", t)
    t = re.sub(r"\\[,;!:> ]", "", t)
    for _ in range(2):
        t = re.sub(r"\\(text|mathrm|mathit|mathbf|operatorname|textrm|mathsf)\s*\{([^{}]*)\}", r"\2", t)
    t = re.sub(r"\\(text|mathrm|mathit|mathbf|textrm|mathsf)\s+([A-Za-z])", r"\2", t)
    t = re.sub(r"\\(to|rightarrow|longrightarrow)(?![A-Za-z])", "→", t)
    t = re.sub(r"\\var(epsilon|phi|theta|rho|sigma|pi)", r"\\\1", t)
    t = t.replace("\\ldots", "\\dots").replace("\\cdot", "\\times").replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    t = re.sub(r"\\begin\{(aligned|align\*?|array|gathered|split)\}(\{[^}]*\})?|\\end\{(aligned|align\*?|array|gathered|split)\}", "", t)
    t = t.replace("&", "").replace("\\\\", "")
    t = re.sub(r"\\intertext\{[^}]*\}", "", t)
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"\s+", "", t)
    return re.sub(r"[.,;:]+$", "", t)


def _iou(a, b):
    l, t, r, bb = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if r <= l or bb <= t:
        return 0.0
    inter = (r - l) * (bb - t)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def pair_equations(docling_eqs, marker_eqs, page_height):
    """Equation entries with status agree | differ | docling only | marker only."""
    d_items = []
    for i, e in enumerate(docling_eqs):
        if not e.get("bbox") or not e.get("page"):
            continue
        H = page_height(e["page"])
        bb = e["bbox"]
        d_items.append({"i": i, "page": e["page"], "box": [bb[0], H - max(bb[1], bb[3]), bb[2], H - min(bb[1], bb[3])],
                        "latex": e.get("latex", ""), "number": e.get("number")})
    m_items = [{"i": i, "page": e["page"], "box": e["bbox"], "latex": e.get("latex", ""), "number": e.get("number")}
               for i, e in enumerate(marker_eqs) if e.get("bbox")]
    pairs, used = [], set()
    for d in d_items:
        best, score = None, 0.0
        for m in m_items:
            if m["i"] in used or m["page"] != d["page"]:
                continue
            vt = max(0, min(d["box"][3], m["box"][3]) - max(d["box"][1], m["box"][1]))
            vh = min(d["box"][3] - d["box"][1], m["box"][3] - m["box"][1])
            sc = _iou(d["box"], m["box"]) + (vt / vh if vh > 0 else 0)
            if sc > score:
                best, score = m, sc
        if best and score >= 0.6:
            pairs.append((d, best)); used.add(best["i"])
    paired_d = {id(p[0]) for p in pairs}
    for d in d_items:
        if id(d) in paired_d or not d["number"]:
            continue
        cand = [m for m in m_items if m["i"] not in used and m["number"] == d["number"] and m["page"] == d["page"]]
        if cand:
            pairs.append((d, cand[0])); used.add(cand[0]["i"]); paired_d.add(id(d))
    out = []
    for d, m in pairs:
        box = [min(d["box"][0], m["box"][0]), min(d["box"][1], m["box"][1]), max(d["box"][2], m["box"][2]), max(d["box"][3], m["box"][3])]
        out.append({"page": d["page"], "bbox": [round(x, 2) for x in box], "number": d["number"] or m["number"],
                    "docling": d["latex"], "marker": m["latex"],
                    "status": "agree" if norm_latex(d["latex"]) == norm_latex(m["latex"]) else "differ"})
    for d in d_items:
        if id(d) not in paired_d:
            out.append({"page": d["page"], "bbox": [round(x, 2) for x in d["box"]], "number": d["number"],
                        "docling": d["latex"], "marker": None, "status": "docling only"})
    for m in m_items:
        if m["i"] not in used:
            out.append({"page": m["page"], "bbox": [round(x, 2) for x in m["box"]], "number": m["number"],
                        "docling": None, "marker": m["latex"], "status": "marker only"})
    out.sort(key=lambda e: (e["page"], e["bbox"][1]))
    return out


def merge_one(paper_id):
    md_dir, dd = MARKER / paper_id, DOCLING / paper_id
    st = json.loads((md_dir / "structure.json").read_text())
    out = FINAL / paper_id
    shutil.rmtree(out, ignore_errors=True)
    (out / "figures").mkdir(parents=True)
    shutil.copy(md_dir / "document.md", out / "document.md")
    captions = []
    for c in st["captions"]:
        c = dict(c)
        files = list(c.get("images") or []) + ([c["crop"]] if c.get("crop") else [])
        for f in files:
            if (md_dir / f).exists():
                shutil.copy(md_dir / f, out / "figures" / f)
        if c.get("images") is not None:
            c["images"] = [f"figures/{f}" for f in c["images"]]
        if c.get("crop"):
            c["crop"] = f"figures/{c['crop']}"
        captions.append(c)
    docling_eqs = json.loads((dd / "equations.json").read_text()) if (dd / "equations.json").exists() else []
    import pypdfium2
    pdf = pypdfium2.PdfDocument(str(RAW / f"{paper_id}.pdf"))
    heights = {}
    def page_height(p):
        if p not in heights:
            heights[p] = pdf[p - 1].get_size()[1]
        return heights[p]
    equations = pair_equations(docling_eqs, st.get("equations", []), page_height)
    import body_check
    import line_numbers
    md_text, ln = line_numbers.process(RAW / f"{paper_id}.pdf", (out / "document.md").read_text())
    if ln["pages"]:
        (out / "document.md").write_text(md_text)
    tree = json.loads((md_dir / "blocks.json").read_text())
    import body_repair
    oa = st.get("abstract") if st.get("abstract_source") == "openalex" else None
    body = body_check.check_body(RAW / f"{paper_id}.pdf", (out / "document.md").read_text(), tree, out / "figures", openalex_abstract=oa)
    md0 = (out / "document.md").read_text()
    md_text, repairs = body_repair.repair(md0, body, RAW / f"{paper_id}.pdf")
    undone = []
    if repairs:                                   # countermeasures applied: check the repaired text again
        body2 = body_check.check_body(RAW / f"{paper_id}.pdf", md_text, tree, None, openalex_abstract=oa)
        failed = body_repair.recheck(repairs, body2["body_flags"])
        if failed:                                # a repair whose sentence still carries a flag is undone, its flag stays
            undone = [dict(r, remaining_flag=fl) for r, fl in failed]
            md_text, repairs = body_repair.repair(md0, body, RAW / f"{paper_id}.pdf", skip={body_repair._sig(r) for r, _ in failed})
    if repairs or undone:
        (out / "document.md").write_text(md_text)
        for f in out.glob("figures/body_p*.png"):
            f.unlink()
        body = body_check.check_body(RAW / f"{paper_id}.pdf", md_text, tree, out / "figures", openalex_abstract=oa)
    body["body_check"]["line_numbers"] = ln
    body["body_check"]["repairs"] = len(repairs)
    body["body_check"]["repairs_undone"] = len(undone)
    for f in body["body_flags"]:
        f["crop"] = f"figures/{f['crop']}"
    final = {"paper_id": paper_id, "body_flags": body["body_flags"], "body_check": body["body_check"], "body_repairs": repairs,
             "body_repairs_undone": undone,
             "abstract": st.get("abstract", ""), "abstract_source": st.get("abstract_source"),
             "sections": st.get("sections", []), "n_pictures": st.get("n_pictures"), "n_tables": st.get("n_tables"),
             "captions": captions, "equations": equations,
             "sources": {"body": "marker", "abstract": "marker", "figures": "marker", "captions": "marker",
                         "tables": "marker (rule check)", "equations": "docling + marker, paired"}}
    (out / "structure.json").write_text(json.dumps(final, indent=1, ensure_ascii=False))
    return final


def main(argv):
    rows = list(csv.DictReader(MANIFEST.open(newline="", encoding="utf-8")))
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    if argv == ["--all"]:
        todo = [r["paper_id"] for r in rows if r.get("marker") == "ok"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: merge.py <paper_id> [...] | --all  (unknown: {missing})")
        todo = argv
    for pid in todo:
        if not (MARKER / pid / "structure.json").exists():
            print(f"[merge] {pid}: no marker/structure.json, skipped")
            continue
        f = merge_one(pid)
        eq = f["equations"]
        n_flag = sum(1 for c in f["captions"] if c["kind"] == "table" and c.get("check") == "flag")
        bc = f["body_check"]["counts"]
        print(f"[merge] {pid}: body {bc.get('checked', 0)} lines checked, {bc.get('flags', 0)} flags, {bc.get('not checkable: undecoded glyph', 0)} lines not checkable ({bc.get('not-checkable flags', 0)} not-checkable flags, {f['body_check'].get('repairs', 0)} repairs, {f['body_check'].get('repairs_undone', 0)} undone); "
              f"{sum(1 for c in f['captions'] if c['kind'] != 'table')} figure captions, "
              f"{sum(1 for c in f['captions'] if c['kind'] == 'table')} tables ({n_flag} flagged), "
              f"{len(eq)} equations ({sum(1 for e in eq if e['status'] == 'agree')} agree, "
              f"{sum(1 for e in eq if e['status'] == 'differ')} differ, "
              f"{sum(1 for e in eq if e['status'].endswith('only'))} one tool only) -> final/{pid}/", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
