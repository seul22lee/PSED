#!/usr/bin/env python3
"""Marker parse, parallel to the Docling stage: corpus/raw/<paper_id>.pdf -> ingest/marker/<paper_id>/.

    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py <paper_id> [...]
    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py --all
    ~/miniconda3/envs/psed_marker/bin/python psed_v2/ingest/parse_marker.py --redo <paper_id> [...]

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

Progress lives in corpus/manifest.csv, column `marker`: ok | failed | blank (not run). The column
is written after each paper. Only in-scope rows with pdf_status ok are parsed; rows already ok are
skipped: Marker output is not deterministic across runs, so an ok paper is overwritten only with
--redo. Needs marker-pdf 2.0.0 (conda env psed_marker).
"""
import csv
import json
import os
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
    return {"pages": len(document.pages), "blocks": n_blocks, "md_chars": len(md.markdown), "images": len(images)}


def _walk(block):
    yield block
    for child in block.get("children") or []:
        yield from _walk(child)


def main(argv):
    rows, fields = read_manifest()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    redo = argv[:1] == ["--redo"]
    if redo:
        argv = argv[1:]
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
                  f"{info['images']} images, {time.time() - t0:.0f}s -> marker/{pid}/", flush=True)
        except Exception:
            traceback.print_exc()
            r["marker"] = "failed"
        write_manifest(rows, fields)


if __name__ == "__main__":
    main(sys.argv[1:])
