#!/usr/bin/env python3
"""Docling parse: corpus/raw/<paper_id>.pdf -> corpus/docling/<paper_id>/. No LLM.

    ~/miniconda3/envs/psed310/bin/python psed_v2/corpus/parse_docling.py <paper_id> [...]
    ~/miniconda3/envs/psed310/bin/python psed_v2/corpus/parse_docling.py --all

Writes, per paper:

    docling/<paper_id>/document.md      full markdown
    docling/<paper_id>/structure.json   {n_pages, sections[headings], n_pictures, n_tables,
                                         captions[{kind, number, caption, images|table, page}]}

Caption binding (replaces Docling's), in Docling's reading order:
- a caption is text starting with Fig./Figure/Scheme/Table + number (not "Figs."), kept only
  if Docling labels it caption or the number is followed by ".", ":" or "|"; for a repeated
  kind+number the Docling-labelled one wins, else the first;
- pictures are held until the next figure/scheme caption, which takes them all; a section
  heading drops held pictures as unnumbered;
- a table goes to the latest earlier table caption without a table, else stays unnumbered.
Unnumbered items are listed with number null.
    docling/<paper_id>/figures/fig_N.png

Progress lives in manifest.csv, column `docling`: ok | failed | blank (not run).
The column is written after each paper; rows already ok are skipped.
--all parses every row with pdf_status ok. Needs docling (conda env psed310).
"""
import csv
import json
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
RAW = HERE / "raw"
OUT = HERE / "docling"


def _converter(force_ocr=False):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    opts = PdfPipelineOptions()
    opts.generate_picture_images = True      # keep figure crops so a vision LLM can read them
    opts.images_scale = 3
    if force_ocr:
        opts.do_ocr = True
        try:
            opts.ocr_options.force_full_page_ocr = True   # OCR the whole page (image-only PDFs)
        except Exception:
            pass
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})


CAPTION_RE = re.compile(r"\s*(Fig\.|FIG\.|Figure(?!s)|FIGURE(?!S)|Scheme(?!s)|SCHEME(?!S)|Table(?!s)|TABLE(?!S))"
                        r"\s*(S?\d+|[IVXL]+)\b(\s*[.:|])?")


def _caption_kind(word):
    w = word.lower()
    return "table" if w.startswith("table") else "scheme" if w.startswith("scheme") else "figure"


def _label(item):
    lab = getattr(item, "label", None)
    return getattr(lab, "value", lab)


def _page(item):
    prov = (getattr(item, "prov", None) or [None])[0]
    return getattr(prov, "page_no", None)


def run(pdf, force_ocr=False, figdir=None):
    res = _converter(force_ocr).convert(pdf)
    doc = res.document
    md = doc.export_to_markdown()

    # 1. reading-order sequence: pictures (crops saved in order), tables, headings, captions
    seq = []            # ("pic", idx) | ("tab", idx) | ("head",) | ("cap", cand_idx)
    pics, tabs, cands = [], [], []
    for item, _level in doc.iterate_items():
        cls = type(item).__name__
        if cls == "PictureItem":
            idx = len(pics)
            imgpath = ""
            if figdir is not None:
                try:
                    im = item.get_image(doc)
                    if im is not None:
                        figdir.mkdir(parents=True, exist_ok=True)
                        im.save(figdir / f"fig_{idx}.png")
                        imgpath = f"figures/fig_{idx}.png"
                except Exception:
                    pass
            pics.append({"image": imgpath, "page": _page(item)})
            seq.append(("pic", idx))
        elif cls == "TableItem":
            try:
                tmd = item.export_to_markdown(doc)
            except Exception:
                tmd = ""
            tabs.append({"markdown": tmd, "page": _page(item)})
            seq.append(("tab", len(tabs) - 1))
        elif _label(item) in ("section_header", "title"):
            seq.append(("head",))
        else:
            text = getattr(item, "text", "") or ""
            m = CAPTION_RE.match(text)
            is_cap_label = _label(item) == "caption"
            # a caption: Docling labels it caption, or the number is followed by . : |
            if m and (is_cap_label or m.group(3)):
                cands.append({"kind": _caption_kind(m.group(1)), "number": m.group(2),
                              "caption": re.sub(r"\s+", " ", text).strip(), "page": _page(item),
                              "labelled": is_cap_label})
                seq.append(("cap", len(cands) - 1))

    # 2. one caption per kind+number: the Docling-labelled one, else the first
    keep = {}
    for i, c in enumerate(cands):
        k = (c["kind"], c["number"])
        if k not in keep or (c["labelled"] and not cands[keep[k]]["labelled"]):
            keep[k] = i
    kept = set(keep.values())

    # 3. walk: pictures wait for the next figure/scheme caption; a heading drops them;
    #    a table goes to the latest earlier table caption that has no table yet
    entries, by_cand = [], {}
    held, open_tab_caps, loose_pics, loose_tabs = [], [], [], []
    for step in seq:
        if step[0] == "pic":
            held.append(step[1])
        elif step[0] == "head":
            loose_pics += held
            held = []
        elif step[0] == "cap" and step[1] in kept:
            c = cands[step[1]]
            e = {"kind": c["kind"], "number": c["number"], "caption": c["caption"], "page": c["page"]}
            if c["kind"] == "table":
                e["table"] = ""
                open_tab_caps.append(e)
            else:
                e["images"] = [pics[j]["image"] for j in held if pics[j]["image"]]
                held = []
            entries.append(e)
        elif step[0] == "tab":
            if open_tab_caps:
                open_tab_caps.pop()["table"] = tabs[step[1]]["markdown"]
            else:
                loose_tabs.append(step[1])
    loose_pics += held
    for j in loose_pics:
        entries.append({"kind": "figure", "number": None, "caption": "",
                        "images": [pics[j]["image"]] if pics[j]["image"] else [], "page": pics[j]["page"]})
    for j in loose_tabs:
        entries.append({"kind": "table", "number": None, "caption": "", "table": tabs[j]["markdown"],
                        "page": tabs[j]["page"]})

    sections = [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", md, re.M)]
    return md, {"n_pages": getattr(doc, "num_pages", lambda: None)() if callable(getattr(doc, "num_pages", None)) else None,
                "sections": sections, "n_pictures": len(pics), "n_tables": len(tabs),
                "captions": entries}


def read_manifest():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    if "docling" not in fields:
        fields.append("docling")
    for r in rows:
        r.setdefault("docling", "")
    return rows, fields


def write_manifest(rows, fields):
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MANIFEST)


def parse_one(paper_id):
    pdf = RAW / f"{paper_id}.pdf"
    d = OUT / paper_id
    d.mkdir(parents=True, exist_ok=True)
    md, struct = run(pdf, figdir=d / "figures")
    if len(md) < 500:                               # image-only PDF -> force full-page OCR
        print(f"  only {len(md)} chars; retrying with full-page OCR", flush=True)
        md, struct = run(pdf, force_ocr=True, figdir=d / "figures")
        struct["ocr_forced"] = True
    (d / "document.md").write_text(md)
    (d / "structure.json").write_text(json.dumps(struct, indent=1))
    return md, struct


def main(argv):
    rows, fields = read_manifest()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    if argv == ["--all"]:
        todo = [r for r in rows if r["pdf_status"] == "ok"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: parse_docling.py <paper_id> [...] | --all  (unknown: {missing})")
        todo = [by_id[a] for a in argv]
    for r in todo:
        pid = r["paper_id"]
        if r["docling"] == "ok":
            print(f"[docling] {pid}: already ok, skipped")
            continue
        print(f"[docling] {pid} ...", flush=True)
        t0 = time.time()
        try:
            md, struct = parse_one(pid)
            r["docling"] = "ok"
            print(f"  {len(md)} md chars, {struct['n_pictures']} pictures, {struct['n_tables']} tables, "
                  f"{len(struct['sections'])} headings{' (OCR)' if struct.get('ocr_forced') else ''}, "
                  f"{time.time() - t0:.0f}s -> docling/{pid}/", flush=True)
        except Exception:
            traceback.print_exc()
            r["docling"] = "failed"
        write_manifest(rows, fields)


if __name__ == "__main__":
    main(sys.argv[1:])
