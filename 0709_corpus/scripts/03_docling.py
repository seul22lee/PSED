#!/usr/bin/env python3
"""
03_docling.py — Stage 1: PDF → structure (markdown + sections + tables + figure captions).
Run with the psed310 env python (has docling 2.75). NO LLM.

  <psed310>/bin/python scripts/03_docling.py <pdf> [<pdf> ...]

Writes 0709_corpus/extracted/{safe_doi}/{document.md, structure.json}.
structure.json = {n_pages, sections[], tables[md], figures[{index,caption}]}.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "extracted"
OUT.mkdir(exist_ok=True)


def safe_doi(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).stem.lower())


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
            figures.append({"index": idx, "caption": re.sub(r"\s+", " ", cap).strip(), "image": imgpath})
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


def main(pdfs):
    for pdf in pdfs:
        sd = safe_doi(pdf)
        d = OUT / sd
        d.mkdir(exist_ok=True)
        print(f"[docling] {sd} …", flush=True)
        md, struct = run(pdf, figdir=d / "figures")
        if len(md) < 500:                               # image-only PDF → force full-page OCR
            print(f"  only {len(md)} chars — retrying with full-page OCR …", flush=True)
            md, struct = run(pdf, force_ocr=True, figdir=d / "figures")
            struct["ocr_forced"] = True
        (d / "document.md").write_text(md)
        (d / "structure.json").write_text(json.dumps(struct, indent=1))
        print(f"  {len(md)} md chars · {struct['n_figures']} figures · {struct['n_tables']} tables "
              f"· {len(struct['sections'])} headings"
              f"{' (OCR)' if struct.get('ocr_forced') else ''} → extracted/{sd}/")


if __name__ == "__main__":
    main(sys.argv[1:])
