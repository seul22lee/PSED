#!/usr/bin/env python3
"""Docling parse: corpus/raw/<paper_id>.pdf -> corpus/docling/<paper_id>/. No LLM.

    ~/miniconda3/envs/psed310/bin/python psed_v2/corpus/parse_docling.py <paper_id> [...]
    ~/miniconda3/envs/psed310/bin/python psed_v2/corpus/parse_docling.py --all

Writes, per paper:

    docling/<paper_id>/document.md      full markdown
    docling/<paper_id>/structure.json   {n_pages, sections[headings],
                                         figures[{index,caption,image,page,bbox}],
                                         tables[{index,caption,markdown}]}
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


def run(pdf, force_ocr=False, figdir=None):
    res = _converter(force_ocr).convert(pdf)
    doc = res.document
    md = doc.export_to_markdown()
    # captions + saved image crops: docling PictureItem carries caption + .get_image(doc)
    figures, tables = [], []
    for item, _level in doc.iterate_items():
        cls = type(item).__name__
        if cls == "PictureItem":
            cap = ""
            try:
                cap = item.caption_text(doc) or ""
            except Exception:
                pass
            idx = len(figures)
            imgpath = ""
            if figdir is not None:
                try:
                    im = item.get_image(doc)
                    if im is not None:
                        figdir.mkdir(parents=True, exist_ok=True)
                        p = figdir / f"fig_{idx}.png"
                        im.save(p)
                        imgpath = f"figures/fig_{idx}.png"
                except Exception:
                    pass
            # Docling knows the page and bounding box of every crop; structure.json used
            # to discard both, which left the figure-provenance stage with nothing but
            # document order to work from. Captured here so future parses can bind
            # captions by geometry instead of adjacency alone. Absent on older parses.
            page, bbox = None, None
            try:
                prov = (getattr(item, "prov", None) or [None])[0]
                if prov is not None:
                    page = getattr(prov, "page_no", None)
                    bb = getattr(prov, "bbox", None)
                    if bb is not None:
                        bbox = [getattr(bb, k, None) for k in ("l", "t", "r", "b")]
            except Exception:
                pass
            figures.append({"index": idx, "caption": re.sub(r"\s+", " ", cap).strip(),
                            "image": imgpath, "page": page, "bbox": bbox})
        elif cls == "TableItem":
            cap = ""
            try:
                cap = item.caption_text(doc) or ""
            except Exception:
                pass
            try:
                tmd = item.export_to_markdown(doc)
            except Exception:
                tmd = ""
            tables.append({"index": len(tables), "caption": re.sub(r"\s+", " ", cap).strip(),
                           "markdown": tmd})
    # sections: markdown headings
    sections = [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", md, re.M)]
    return md, {"n_pages": getattr(doc, "num_pages", lambda: None)() if callable(getattr(doc, "num_pages", None)) else None,
                "sections": sections, "n_figures": len(figures), "n_tables": len(tables),
                "figures": figures, "tables": tables}


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
            print(f"  {len(md)} md chars, {struct['n_figures']} figures, {struct['n_tables']} tables, "
                  f"{len(struct['sections'])} headings{' (OCR)' if struct.get('ocr_forced') else ''}, "
                  f"{time.time() - t0:.0f}s -> docling/{pid}/", flush=True)
        except Exception:
            traceback.print_exc()
            r["docling"] = "failed"
        write_manifest(rows, fields)


if __name__ == "__main__":
    main(sys.argv[1:])
