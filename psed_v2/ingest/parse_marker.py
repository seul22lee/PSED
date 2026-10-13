#!/usr/bin/env python3
"""Marker parse, parallel to the Docling stage: corpus/raw/<paper_id>.pdf -> ingest/marker/<paper_id>/.

    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py <paper_id> [...]
    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py --all
    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py --redo <paper_id> [...]
    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py --bands <paper_id> [...] | --bands --all

Marker 2.0.0 with force_ocr: full-page OCR by the surya-ocr-2 VLM, layout from the OCR pass. It is
used because it repairs what the PDF text layer breaks (private-use ligature characters, the °, −,
× and µ glyphs, super- and subscripts) and gives the print reading order (title, authors, abstract,
then the body; footnotes after the paragraph). Checked on 10.1039_c7ta03257a on 2026-10-12.
The VLM is served by llama.cpp (Docker is not permitted here); the env vars from CLAUDE.md are set
below when absent. One process converts all papers, so the server starts once.

Writes, per paper (one conversion, rendered twice):

    marker/<paper_id>/document.md          markdown (images referenced by file name)
    marker/<paper_id>/_page_P_<Type>_K.jpeg figure crops referenced by the markdown
    marker/<paper_id>/document_meta.json   Marker's metadata (table of contents, page stats)
    marker/<paper_id>/blocks.json          block tree: block_type, id, page (1-based), bbox
                                           [l, t, r, b] in PDF points from the top-left, polygon,
                                           html (text), children, section_hierarchy

Band-crop OCR (after each conversion, or alone with --bands on existing output): two layout
failures of Marker are repaired by OCR of a crop. T1: a Figure/Picture/Diagram block whose box holds
a text-layer line starting with a caption label (Figure/Fig./Scheme/Table + number) while the page
has no Caption block with that number (the caption bar was taken into the picture) -> the band
from that line down to the block's bottom is OCR'd and inserted after the block as a Caption block
(id "<block id>/cap"). T2: a Text block whose html holds no text but an image (a text block Marker
rendered as a picture, e.g. an abstract beside a TOC graphic) -> the block is OCR'd and its html
replaced; the image placeholder in the markdown is replaced by the text. Each repair is recorded in
bands.json; a block already repaired is skipped. Checked on the 13 papers, 2026-10-12: 2 captions
(10.1186_s11671-015-0872-9 Figures 1 and 3) and the abstract of 10.1021_acs.jpcc.9b08176 recovered;
7 other T2 hits were author lines and "Check for updates" badges (text added, nothing lost).

Progress lives in corpus/manifest.csv, column `marker`: ok | failed | blank (not run). The column
is written after each paper. Only in-scope rows with pdf_status ok are parsed; rows already ok are
skipped: Marker output is not deterministic across runs, so an ok paper is overwritten only with
--redo. Needs marker-pdf 2.0.0 (conda env psed_marker).
"""
import csv
import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"
MANIFEST = CORPUS / "manifest.csv"
RAW = CORPUS / "raw"
OUT = HERE / "marker"

LLAMA = Path.home() / "opt" / "llama.cpp"
LLAMA_DIRS = [LLAMA / "cudart-llama-b11574-bin-ubuntu-cuda-12.8-x64", LLAMA / "llama-b11574"]


def _env():
    """llama.cpp backend for surya (CLAUDE.md, Environments); only values not already set."""
    os.environ.setdefault("SURYA_INFERENCE_BACKEND", "llamacpp")
    os.environ.setdefault("LLAMA_CPP_BINARY", str(LLAMA / "llama-b11574" / "llama-server"))
    have = os.environ.get("LD_LIBRARY_PATH", "")
    missing = [str(d) for d in LLAMA_DIRS if str(d) not in have.split(":")]
    if missing:
        os.environ["LD_LIBRARY_PATH"] = ":".join(missing + ([have] if have else []))


_env()


def read_manifest():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    if "marker" not in fields:
        fields.append("marker")
    for r in rows:
        r.setdefault("marker", "")
    return rows, fields


def write_manifest(rows, fields):
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MANIFEST)


def _converter():
    """Marker's PDF converter with force_ocr; the models are loaded once per process."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    return PdfConverter(artifact_dict=create_model_dict(), config={"force_ocr": True})


def _add_pages(block):
    """Add "page" (1-based) to every block from its id ("/page/3/Text/12" -> 4)."""
    try:
        block["page"] = int(block["id"].split("/")[2]) + 1
    except (KeyError, IndexError, ValueError):
        pass
    for child in block.get("children") or []:
        _add_pages(child)


def parse_one(converter, paper_id):
    """One conversion; markdown (with images) and the block tree from the same document."""
    from marker.output import save_output
    from marker.renderers.json import JSONRenderer
    from marker.renderers.markdown import MarkdownRenderer
    pdf = RAW / f"{paper_id}.pdf"
    d = OUT / paper_id
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    document = converter.build_document(str(pdf))
    md = converter.resolve_dependencies(MarkdownRenderer)(document)
    save_output(md, str(d), "document")                       # document.md, document_meta.json, images
    blocks = JSONRenderer(dict(converter.config, extract_images=False))(document)
    tree = json.loads(blocks.model_dump_json())
    for page in tree.get("children") or []:
        _add_pages(page)
    (d / "blocks.json").write_text(json.dumps(tree, indent=1, ensure_ascii=False))
    n_blocks = sum(1 for _ in _walk(tree))
    images = [p.name for p in d.iterdir() if p.suffix.lower() in (".jpeg", ".jpg", ".png")]
    bands = band_ocr(converter, paper_id)
    return {"pages": len(document.pages), "blocks": n_blocks, "md_chars": len(md.markdown), "images": len(images), "bands": bands}


def _walk(block):
    yield block
    for child in block.get("children") or []:
        yield from _walk(child)


CAPTION_LINE_RE = re.compile(r"^\s*(Figure|FIGURE|Fig\.|FIG\.|Scheme|SCHEME|Table|TABLE)\s*([A-Z]?\d+|[IVX]+)(?=[^0-9]|$)")
IMAGE_TYPES = ("Figure", "Picture", "Diagram")


def _md_to_html(md):
    """OCR markdown of a crop as one html paragraph (images dropped, bold kept, links unwrapped)."""
    t = re.sub(r"!\[\]\([^)]*\)", "", md)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"\[([^\]]*)\]\(#\)", r"\1", t)
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    return f"<p>{t}</p>" if t else ""


def _band_triggers(tree, pdf):
    """[(trigger, block, parent, band [l, t, r, b], label)] for T1 and T2 (see the module docstring)."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(str(pdf))
    hits = []
    for page in tree.get("children") or []:
        pno = page.get("page")
        if not pno:
            continue
        cap_numbers = set()
        for b in _walk(page):
            if b.get("block_type") == "Caption":
                m = CAPTION_LINE_RE.match(re.sub(r"<[^>]+>", "", b.get("html", "")).strip())
                if m:
                    cap_numbers.add(m.group(2))
        pdf_page = doc[pno - 1]
        H = pdf_page.get_size()[1]
        textpage = pdf_page.get_textpage()
        rects = [textpage.get_rect(i) for i in range(textpage.count_rects())]   # (left, bottom, right, top), bottom-left origin
        def walk(b, parent):
            if "band_ocr" in b:
                pass
            elif b.get("block_type") in IMAGE_TYPES and b.get("bbox"):
                l, t, r, bt = b["bbox"]
                segs = []                                   # text rectangles inside the block, one per font run
                for (rl, rb, rr, rt) in rects:
                    if rl >= l - 2 and rr <= r + 2 and (H - rt) >= t - 2 and (H - rb) <= bt + 2:
                        segs.append((H - rt, rl, textpage.get_text_bounded(left=rl, bottom=rb, right=rr, top=rt).strip()))
                lines = []                                  # runs on one line (tops within 3 pt) joined in x order
                for top, left, text in sorted(segs):
                    if lines and abs(lines[-1][0] - top) <= 3:
                        lines[-1][1].append((left, text))
                    else:
                        lines.append([top, [(left, text)]])
                lines = [(top, " ".join(s for _, s in sorted(runs))) for top, runs in lines]
                for top, text in sorted(lines):
                    m = CAPTION_LINE_RE.match(text)
                    if m and m.group(2) not in cap_numbers and len(text) >= 20:
                        hits.append(("T1", b, parent, [l - 2, top - 3, r + 2, bt + 2], f"{m.group(1)} {m.group(2)}"))
                        break
            elif b.get("block_type") == "Text" and b.get("bbox"):
                h = b.get("html", "")
                if "<img" in h and not re.sub(r"<[^>]+>", "", h).strip():
                    l, t, r, bt = b["bbox"]
                    hits.append(("T2", b, parent, [l - 2, t - 2, r + 2, bt + 2], ""))
            for c in b.get("children") or []:
                walk(c, b)
        walk(page, None)
    return hits


def band_ocr(converter, paper_id):
    """T1 / T2 repairs on marker/<paper_id>/: blocks.json patched, the markdown placeholder of a T2
    block replaced by its text, bands.json written. Returns the number of repairs."""
    import pypdfium2
    from marker.output import text_from_rendered
    d = OUT / paper_id
    pdf = RAW / f"{paper_id}.pdf"
    tree = json.loads((d / "blocks.json").read_text())
    hits = _band_triggers(tree, pdf)
    done = json.loads((d / "bands.json").read_text()) if (d / "bands.json").exists() else []   # earlier repairs kept
    if not hits:
        (d / "bands.json").write_text(json.dumps(done, indent=1, ensure_ascii=False))
        return 0
    doc = pypdfium2.PdfDocument(str(pdf))
    for trigger, b, parent, band, label in hits:
        pno = b.get("page")
        l, t, r, bt = band
        im = doc[pno - 1].render(scale=3).to_pil()
        crop = im.crop((max(0, int(l * 3)), max(0, int(t * 3)), min(im.width, int(r * 3)), min(im.height, int(bt * 3))))
        png = d / f"band_{trigger}_{b['id'].strip('/').replace('/', '_')}.png"
        crop.save(png)
        try:
            text, _, _ = text_from_rendered(converter(str(png)))
        except Exception as e:
            print(f"  band OCR failed for {b['id']} ({e.__class__.__name__}: {e})", flush=True)
            continue
        html = _md_to_html(text)
        plain = re.sub(r"<[^>]+>", "", html).strip()
        rec = {"trigger": trigger, "block": b["id"], "page": pno, "band": band, "label": label, "png": png.name, "text": plain}
        if not plain:
            rec["applied"] = False
            b["band_ocr"] = "empty"                       # not retried
            done.append(rec)
            continue
        if trigger == "T1":
            cap = {"id": b["id"] + "/cap", "block_type": "Caption", "bbox": band,
                   "polygon": [[l, t], [r, t], [r, bt], [l, bt]], "html": html, "children": None,
                   "section_hierarchy": b.get("section_hierarchy"), "page": pno, "band_ocr": "T1"}
            kids = parent["children"]
            kids.insert(kids.index(b) + 1, cap)
            b["band_ocr"] = "T1-source"
        else:
            src = re.search(r'<img[^>]*src="([^"]+)"', b.get("html", ""))
            b["html"] = html
            b["band_ocr"] = "T2"
            if src:
                for name in ("marker.md", "document.md"):
                    md_path = d / name
                    if md_path.exists():
                        md = md_path.read_text()
                        new = re.sub(r"!\[[^\]]*\]\(" + re.escape(src.group(1)) + r"\)", plain.replace("\\", "\\\\"), md)
                        if new != md:
                            md_path.write_text(new)
                        break
        rec["applied"] = True
        done.append(rec)
    (d / "blocks.json").write_text(json.dumps(tree, indent=1, ensure_ascii=False))
    (d / "bands.json").write_text(json.dumps(done, indent=1, ensure_ascii=False))
    return sum(1 for x in done if x["applied"] and x["block"] in {h[1]["id"] for h in hits})


def main(argv):
    rows, fields = read_manifest()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    redo = argv[:1] == ["--redo"]
    if redo:
        argv = argv[1:]
    if argv[:1] == ["--bands"]:
        return bands_only(rows, by_id, argv[1:])
    if argv == ["--all"]:
        todo = [r for r in rows if r["pdf_status"] == "ok" and r.get("in_scope") == "yes"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: parse_marker.py <paper_id> [...] | --all | --redo <paper_id> [...]  (unknown: {missing})")
        todo = [by_id[a] for a in argv]
    converter = None
    for r in todo:
        pid = r["paper_id"]
        if r.get("in_scope") != "yes":
            print(f"[marker] {pid}: not in scope, skipped")
            continue
        if r["marker"] == "ok" and not redo:
            print(f"[marker] {pid}: already ok, skipped (use --redo to overwrite)")
            continue
        if not (RAW / f"{pid}.pdf").exists():
            print(f"[marker] {pid}: no PDF, skipped")
            continue
        print(f"[marker] {pid} ...", flush=True)
        t0 = time.time()
        try:
            if converter is None:
                converter = _converter()
            info = parse_one(converter, pid)
            r["marker"] = "ok"
            print(f"  {info['pages']} pages, {info['blocks']} blocks, {info['md_chars']} md chars, "
                  f"{info['images']} images, {info['bands']} band repairs, {time.time() - t0:.0f}s -> marker/{pid}/", flush=True)
        except Exception:
            traceback.print_exc()
            r["marker"] = "failed"
        write_manifest(rows, fields)


def bands_only(rows, by_id, argv):
    """Band-crop OCR on existing marker/<paper_id>/ output (no conversion); the manifest is unchanged."""
    if argv == ["--all"]:
        todo = [r["paper_id"] for r in rows if r.get("marker") == "ok"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: parse_marker.py --bands <paper_id> [...] | --bands --all  (unknown: {missing})")
        todo = argv
    converter = None
    for pid in todo:
        if not (OUT / pid / "blocks.json").exists():
            print(f"[bands] {pid}: no blocks.json, skipped")
            continue
        tree = json.loads((OUT / pid / "blocks.json").read_text())
        hits = _band_triggers(tree, RAW / f"{pid}.pdf")
        if not hits:
            if not (OUT / pid / "bands.json").exists():
                (OUT / pid / "bands.json").write_text("[]\n")
            print(f"[bands] {pid}: no trigger", flush=True)
            continue
        if converter is None:
            converter = _converter()
        t0 = time.time()
        n = band_ocr(converter, pid)
        print(f"[bands] {pid}: {len(hits)} triggers, {n} applied, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
