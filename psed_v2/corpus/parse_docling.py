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
- each picture goes to the first match: (1) the next figure/scheme caption on the same page
  whose horizontal span overlaps the picture's; (2) else the caption the next page starts
  with, if it is a figure/scheme caption; (3) else the previous figure/scheme caption on the
  same page; (4) else it stays unnumbered. Captions nested inside pictures are included;
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
                        r"\s*(S?\d+|[IVXL]+)(?!\d)(\s*[.:|])?")


def _caption_kind(word):
    w = word.lower()
    return "table" if w.startswith("table") else "scheme" if w.startswith("scheme") else "figure"


def _label(item):
    lab = getattr(item, "label", None)
    return getattr(lab, "value", lab)


def _page(item):
    prov = (getattr(item, "prov", None) or [None])[0]
    return getattr(prov, "page_no", None)


def _span(item):
    """Horizontal extent (l, r) of an item's first provenance box, or None."""
    prov = (getattr(item, "prov", None) or [None])[0]
    bb = getattr(prov, "bbox", None)
    return (min(bb.l, bb.r), max(bb.l, bb.r)) if bb is not None else None


def _overlap(a, b):
    return a is not None and b is not None and a[0] < b[1] and b[0] < a[1]


def run(pdf, force_ocr=False, figdir=None):
    res = _converter(force_ocr).convert(pdf)
    doc = res.document
    md = doc.export_to_markdown()

    # 1. reading-order sequence of every body item (captions nested in pictures included)
    seq = []            # ("pic", idx) | ("tab", idx) | ("cap", cand_idx) | ("other",), each with its page
    pics, tabs, cands = [], [], []
    for item, _level in doc.iterate_items(traverse_pictures=True):
        cls = type(item).__name__
        page = _page(item)
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
            pics.append({"image": imgpath, "page": page, "span": _span(item)})
            seq.append(("pic", idx, page))
        elif cls == "TableItem":
            try:
                tmd = item.export_to_markdown(doc)
            except Exception:
                tmd = ""
            tabs.append({"markdown": tmd, "page": page})
            seq.append(("tab", len(tabs) - 1, page))
        else:
            text = getattr(item, "text", "") or ""
            m = CAPTION_RE.match(text)
            is_cap_label = _label(item) == "caption"
            # a caption: Docling labels it caption, or the number is followed by . : |
            if m and (is_cap_label or m.group(3)):
                cands.append({"kind": _caption_kind(m.group(1)), "number": m.group(2),
                              "caption": re.sub(r"\s+", " ", text).strip(), "page": page,
                              "span": _span(item), "labelled": is_cap_label})
                seq.append(("cap", len(cands) - 1, page))
            else:
                seq.append(("other", None, page))

    # 2. one caption per kind+number: the Docling-labelled one, else the first
    keep = {}
    for i, c in enumerate(cands):
        k = (c["kind"], c["number"])
        if k not in keep or (c["labelled"] and not cands[keep[k]]["labelled"]):
            keep[k] = i
    kept = set(keep.values())

    # 3. entries for kept captions, in reading order
    entries, entry_of = [], {}
    for step in seq:
        if step[0] == "cap" and step[1] in kept:
            c = cands[step[1]]
            e = {"kind": c["kind"], "number": c["number"], "caption": c["caption"], "page": c["page"]}
            if c["kind"] == "table":
                e["table"] = ""
            else:
                e["images"] = []
            entry_of[step[1]] = e
            entries.append(e)
    is_fig_cap = lambda st: st[0] == "cap" and st[1] in kept and cands[st[1]]["kind"] != "table"

    # 4. pictures, first match wins:
    #    (1) next figure/scheme caption on the same page whose horizontal span overlaps;
    #    (2) else the caption the next page starts with, if it is a figure/scheme caption;
    #    (3) else the previous figure/scheme caption on the same page; (4) else unnumbered.
    first_on_page = {}
    for st in seq:
        first_on_page.setdefault(st[2], st)
    loose_pics = []
    for pos, st in enumerate(seq):
        if st[0] != "pic":
            continue
        pic = pics[st[1]]
        target = None
        for later in seq[pos + 1:]:
            if later[2] != pic["page"]:
                break
            if is_fig_cap(later) and _overlap(cands[later[1]]["span"], pic["span"]):
                target = later[1]
                break
        if target is None and pic["page"] is not None:
            nxt = first_on_page.get(pic["page"] + 1)
            if nxt is not None and is_fig_cap(nxt):
                target = nxt[1]
        if target is None:
            for earlier in reversed(seq[:pos]):
                if earlier[2] != pic["page"]:
                    break
                if is_fig_cap(earlier):
                    target = earlier[1]
                    break
        if target is None:
            loose_pics.append(st[1])
        elif pic["image"]:
            entry_of[target]["images"].append(pic["image"])

    # 5. tables: the latest earlier table caption that has no table yet, else unnumbered
    open_tab_caps, loose_tabs = [], []
    for st in seq:
        if st[0] == "cap" and st[1] in kept and cands[st[1]]["kind"] == "table":
            open_tab_caps.append(entry_of[st[1]])
        elif st[0] == "tab":
            if open_tab_caps:
                open_tab_caps.pop()["table"] = tabs[st[1]]["markdown"]
            else:
                loose_tabs.append(st[1])

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
