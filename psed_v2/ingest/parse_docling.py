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
- pictures whose box lies outside the page area (margin artifacts) are ignored;
- decoration pictures are ignored: the same image (16x16 grayscale thumbnail, exact match)
  on 2 or more pages;
- each picture goes to the first match: (1) the next figure/scheme caption on the same page
  whose horizontal span overlaps the picture's; (2) for a picture after the last text item
  on its page, the first text item of the next page if that is a figure/scheme caption;
  (3) the previous figure/scheme caption on the same page, else the next one on that page;
  (4) else it stays unnumbered. Captions nested inside pictures are included;
- a caption that is the last text item on its page and does not end with ".", ")" or "]"
  continues with the first text item of the next page;
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
import shutil
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


def _page_areas(pdf):
    """Per page (1-based): the page area in Docling's bottom-left coordinates, (l, b, r, t).

    Docling shifts coordinates so the PDF MediaBox starts at 0. A MediaBox that starts at a
    negative coordinate has a strip added outside the original page (download stamps, logos);
    the page area is the MediaBox part with non-negative PDF coordinates.
    """
    areas = {}
    try:
        import pypdfium2
        doc = pypdfium2.PdfDocument(str(pdf))
        for i in range(len(doc)):
            l, b, r, t = doc[i].get_mediabox()
            areas[i + 1] = (max(0.0, -l), max(0.0, -b), r - l, t - b)
    except Exception:
        pass
    return areas


def _outside(item, areas):
    """True if the item's box lies entirely outside its page area."""
    prov = (getattr(item, "prov", None) or [None])[0]
    bb = getattr(prov, "bbox", None)
    area = areas.get(getattr(prov, "page_no", None))
    if bb is None or area is None:
        return False
    lo_x, hi_x = min(bb.l, bb.r), max(bb.l, bb.r)
    lo_y, hi_y = min(bb.t, bb.b), max(bb.t, bb.b)
    return hi_x <= area[0] or lo_x >= area[2] or hi_y <= area[1] or lo_y >= area[3]


def run(pdf, force_ocr=False, figdir=None):
    res = _converter(force_ocr).convert(pdf)
    doc = res.document
    md = doc.export_to_markdown()

    # 1. reading-order sequence. Text nested inside a picture (axis labels, scale bars) is not
    #    a text item of the page, except captions, which Docling may nest there.
    areas = _page_areas(pdf)
    # decoration: the same image (16x16 grayscale thumbnail, exact match) on 2 or more pages
    images, thumb_pages = {}, {}
    for item, _level in doc.iterate_items(traverse_pictures=True):
        if type(item).__name__ != "PictureItem":
            continue
        try:
            im = item.get_image(doc)
        except Exception:
            im = None
        key = im.convert("L").resize((16, 16)).tobytes() if im is not None else None
        images[item.self_ref] = (im, key)
        if key is not None:
            thumb_pages.setdefault(key, set()).add(_page(item))
    decoration = {k for k, pages in thumb_pages.items() if len(pages) >= 2}
    seq = []            # (type, idx, page, text): type is "pic" | "tab" | "cap" | "text"
    pics, tabs, cands = [], [], []
    pic_level = None
    for item, level in doc.iterate_items(traverse_pictures=True):
        cls = type(item).__name__
        page = _page(item)
        if pic_level is not None and level <= pic_level:
            pic_level = None
        nested = pic_level is not None
        if cls == "PictureItem":
            if pic_level is None:
                pic_level = level
            if _outside(item, areas):       # margin artifact: not bound, not listed
                continue
            im, key = images.get(item.self_ref, (None, None))
            if key in decoration:           # repeated on 2+ pages: not bound, not listed
                continue
            idx = len(pics)
            imgpath = ""
            if figdir is not None and im is not None:
                try:
                    figdir.mkdir(parents=True, exist_ok=True)
                    im.save(figdir / f"fig_{idx}.png")
                    imgpath = f"figures/fig_{idx}.png"
                except Exception:
                    pass
            pics.append({"image": imgpath, "page": page, "span": _span(item)})
            seq.append(("pic", idx, page, ""))
        elif cls == "TableItem":
            try:
                tmd = item.export_to_markdown(doc)
            except Exception:
                tmd = ""
            tabs.append({"markdown": tmd, "page": page})
            seq.append(("tab", len(tabs) - 1, page, ""))
        else:
            text = getattr(item, "text", "") or ""
            m = CAPTION_RE.match(text)
            is_cap_label = _label(item) == "caption"
            # a caption: Docling labels it caption, or the number is followed by . : |
            if m and (is_cap_label or m.group(3)):
                cands.append({"kind": _caption_kind(m.group(1)), "number": m.group(2),
                              "caption": re.sub(r"\s+", " ", text).strip(), "page": page,
                              "span": _span(item), "labelled": is_cap_label})
                seq.append(("cap", len(cands) - 1, page, text))
            elif not nested and text.strip():
                seq.append(("text", None, page, text))

    # 2. one caption per kind+number: the Docling-labelled one, else the first
    keep = {}
    for i, c in enumerate(cands):
        k = (c["kind"], c["number"])
        if k not in keep or (c["labelled"] and not cands[keep[k]]["labelled"]):
            keep[k] = i
    kept = set(keep.values())

    # text items per page: first and last position in reading order
    is_text = lambda st: st[0] in ("cap", "text")
    first_text, last_text = {}, {}
    for pos, st in enumerate(seq):
        if is_text(st):
            first_text.setdefault(st[2], pos)
            last_text[st[2]] = pos

    # 3. entries for kept captions, in reading order. A caption that is the last text item on
    #    its page and does not end with . ) ] continues with the next page's first text item.
    entries, entry_of = [], {}
    for pos, st in enumerate(seq):
        if st[0] == "cap" and st[1] in kept:
            c = cands[st[1]]
            caption = c["caption"]
            if (c["page"] is not None and last_text.get(c["page"]) == pos
                    and not caption.endswith((".", ")", "]"))):
                nxt = first_text.get(c["page"] + 1)
                if nxt is not None:
                    caption = caption + " " + re.sub(r"\s+", " ", seq[nxt][3]).strip()
            e = {"kind": c["kind"], "number": c["number"], "caption": caption, "page": c["page"]}
            if c["kind"] == "table":
                e["table"] = ""
            else:
                e["images"] = []
            entry_of[st[1]] = e
            entries.append(e)
    is_fig_cap = lambda st: st[0] == "cap" and st[1] in kept and cands[st[1]]["kind"] != "table"

    # 4. pictures, first match wins:
    #    (1) next figure/scheme caption on the same page whose horizontal span overlaps;
    #    (2) only for a picture after the last text item on its page: the first text item on
    #        the next page, if it is a figure/scheme caption;
    #    (3) the previous figure/scheme caption on the same page, else the next one on the page;
    #    (4) else unnumbered.
    loose_pics = []
    for pos, st in enumerate(seq):
        if st[0] != "pic":
            continue
        pic = pics[st[1]]
        page = pic["page"]
        same_after = [x for x in seq[pos + 1:] if x[2] == page and is_fig_cap(x)]
        same_before = [x for x in seq[:pos] if x[2] == page and is_fig_cap(x)]
        target = None
        for later in same_after:
            if _overlap(cands[later[1]]["span"], pic["span"]):
                target = later[1]
                break
        if target is None and page is not None and pos > last_text.get(page, -1):
            nxt = first_text.get(page + 1)
            if nxt is not None and is_fig_cap(seq[nxt]):
                target = seq[nxt][1]
        if target is None and same_before:
            target = same_before[-1][1]
        if target is None and same_after:
            target = same_after[0][1]
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
    shutil.rmtree(d / "figures", ignore_errors=True)    # old crops never linger
    md, struct = run(pdf, figdir=d / "figures")
    if len(md) < 500:                               # image-only PDF -> force full-page OCR
        print(f"  only {len(md)} chars; retrying with full-page OCR", flush=True)
        shutil.rmtree(d / "figures", ignore_errors=True)
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
