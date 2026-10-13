#!/usr/bin/env python3
"""Docling in the ingest stage: equations only, plus the one-off OpenAlex abstract fetch.

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --formulas <paper_id> [...]
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --fetch-abstracts

--formulas: Docling's layout gives the formula items of corpus/raw/<paper_id>.pdf; Docling's
CodeFormula model (CodeFormulaV2) reads our own crops: R1, the formula box without expansion at
216 dpi (Docling's enrichment crops the box expanded by 18 % at 120 dpi, which takes in neighbouring
text); R2, a box of at most 25 pt width holds only the printed equation number, so the band of its
text column between the text items above and below is read instead. Writes
docling/<paper_id>/equations.json: page, bbox (bottom-left origin), LaTeX, printed number (from the
LaTeX or the "(N)" word right of the formula), rule, crop box (top-left origin). Nothing else is
written. merge.py pairs these with Marker's equations. Needs a GPU (about 6 GB); set
CUDA_DEVICE_ORDER=PCI_BUS_ID so that CUDA_VISIBLE_DEVICES follows nvidia-smi's numbering.
On the 13 Marker papers (2026-10-12, 103 paired equations, judged on crops): R1 fixed 18 of
Docling's equations and broke 1, R2 fixed 12 of 19.

--fetch-abstracts: one network call per 50 DOIs, OpenAlex abstracts of the in-scope papers ->
corpus/openalex_abstracts.json (gitignored); structure_marker.py's abstract rules read it. The only
step in ingest that uses the network.

The full Docling parse of this stage (figures, captions, tables, abstract, body text; commits
cc5e59d to 0e2d59c) was removed on 2026-10-12: the final output takes those items from Marker
(INGEST.md). Needs docling (conda env psed310).
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"
MANIFEST = CORPUS / "manifest.csv"
RAW = CORPUS / "raw"
OUT = HERE / "docling"
OA_ABSTRACTS = CORPUS / "openalex_abstracts.json"


def read_manifest():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _converter():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    opts = PdfPipelineOptions()
    opts.generate_picture_images = True      # keep figure crops so a vision LLM can read them
    opts.images_scale = 3
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})


def _label(item):
    lab = getattr(item, "label", None)
    return getattr(lab, "value", lab)


EQ_NUMBER_RE = re.compile(r"\\tag\s*\{\s*([A-Za-z]?\d+[a-z]?)\s*\}\s*(?:\\\\)?\s*$"
                          r"|\(\s*((?:[A-Za-z]\s*)?\d(?:\s*\d){0,2}(?:\s*[a-z])?)\s*\)\s*(?:\\\\)?\s*$")


PRINTED_NUMBER_RE = re.compile(r"^\(?([A-Za-z]?\d{1,3}[a-z]?)\)$")


def _printed_number(latex, page, bbox):
    """The equation number: from the LaTeX ("(N)", "\\tag{N}", digits may be spaced) or, with a
    pdfplumber page, the "(N)" word in the formula's vertical band at its right."""
    m = EQ_NUMBER_RE.search(latex or "")
    if m:
        return re.sub(r"\s+", "", m.group(1) or m.group(2))
    if page is None or bbox is None:
        return None
    H, x0 = page.height, page.bbox[0]
    top, bottom = H - max(bbox.t, bbox.b), H - min(bbox.t, bbox.b)
    left, right = min(bbox.l, bbox.r) + x0, max(bbox.l, bbox.r) + x0
    right_part, limit = left + 0.5 * (right - left), right + 60      # the number sits at the right
    best = None                                                        # edge of the formula's column
    try:
        for w in page.extract_words():
            if w["top"] >= top - 3 and w["bottom"] <= bottom + 3 and right_part <= w["x0"] <= limit:
                pm = PRINTED_NUMBER_RE.match(w["text"])
                if pm and (best is None or w["x0"] > best[0]):
                    best = (w["x0"], pm.group(1))
    except Exception:
        return None
    return best[1] if best else None


def _codeformula():
    """Docling's CodeFormula model (CodeFormulaV2), called on our own crops."""
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.pipeline_options import CodeFormulaVlmOptions
    from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
    model = CodeFormulaVlmModel(enabled=True, enable_remote_services=False, artifacts_path=None,
                                options=CodeFormulaVlmOptions.from_preset("codeformulav2"),
                                accelerator_options=AcceleratorOptions(device="cuda"))
    return model


def _codeformula_run(model, images):
    from docling.models.inference_engines.vlm.base import VlmEngineInput
    prompt = model._get_prompt("formula")
    outs = []
    for i in range(0, len(images), 5):
        batch = [VlmEngineInput(image=im, prompt=prompt, temperature=0.0, max_new_tokens=2048,
                                extra_generation_config={"skip_special_tokens": False}) for im in images[i:i + 5]]
        outs += [o.text for o in model.engine.predict_batch(batch)]
    return model._post_process(outs)


def _band_box(doc, page_no, box, W):
    """R2: for a formula box of at most 25 pt width (it holds only the printed number), the text
    column's band between the nearest text items above and below the number, from the column's
    left edge to 2 pt left of the number. box and the result are [l, t, r, b] from the top-left."""
    l, t, r, b = box
    if r - l > 25:
        return None
    H = doc.pages[page_no].size.height
    items = []
    for item, _level in doc.iterate_items():
        if _label(item) == "formula" or not getattr(item, "prov", None):
            continue
        for pv in item.prov:
            if pv.page_no == page_no:
                bb = pv.bbox
                items.append((bb.l, H - max(bb.t, bb.b), bb.r, H - min(bb.t, bb.b)))
                break
    cx = (l + r) / 2
    col = [it for it in items if ((it[0] + it[2]) / 2 < W / 2) == (cx < W / 2) and (it[2] - it[0]) < 0.7 * W]
    if not col:
        return None
    col_left = min(it[0] for it in col)
    above = [it for it in col if it[3] <= t + 2]
    below = [it for it in col if it[1] >= b - 2]
    top = max(it[3] for it in above) if above else t - 20
    bot = min(it[1] for it in below) if below else b + 20
    if bot - top > 150:
        top, bot = max(top, t - 60), min(bot, b + 60)
    return [col_left, top, l - 2, bot]


def formulas(by_id, argv):
    """Docling's layout for the formula items, CodeFormula on our own crops: R1, the formula box
    without expansion at 216 dpi (Docling's enrichment crops the box expanded by 18 % at 120 dpi,
    which takes in neighbouring text); R2, a box of at most 25 pt width holds only the printed
    equation number, so the band of its text column between the text items above and below is
    read instead. Writes docling/<paper_id>/equations.json (page, bbox from the bottom-left, LaTeX,
    printed number, rule, crop box from the top-left) and nothing else. On the 13 Marker papers
    (2026-10-12, 103 paired equations, judged on crops): R1 fixed 18 and broke 1, R2 fixed 12 of 19."""
    missing = [a for a in argv if a not in by_id]
    if missing or not argv:
        sys.exit(f"usage: parse_docling.py --formulas <paper_id> [...]  (unknown: {missing})")
    import pypdfium2
    conv = _converter()
    model = _codeformula()
    try:
        import pdfplumber
    except ImportError:
        pdfplumber = None
    for pid in argv:
        pdf = RAW / f"{pid}.pdf"
        if not pdf.exists():
            print(f"[formulas] {pid}: no PDF, skipped")
            continue
        t0 = time.time()
        doc = conv.convert(pdf).document
        pl = pdfplumber.open(str(pdf)) if pdfplumber else None
        pdfium_doc = pypdfium2.PdfDocument(str(pdf))
        rendered = {}
        eqs, crops = [], []
        for item, _level in doc.iterate_items():
            if _label(item) != "formula":
                continue
            prov = (getattr(item, "prov", None) or [None])[0]
            bb = getattr(prov, "bbox", None)
            page_no = getattr(prov, "page_no", None)
            if bb is None or not page_no:
                continue
            size = doc.pages[page_no].size
            tl = [min(bb.l, bb.r), size.height - max(bb.t, bb.b), max(bb.l, bb.r), size.height - min(bb.t, bb.b)]
            band = _band_box(doc, page_no, tl, size.width)
            crop_box, rule = (band, "R2") if band else (tl, "R1")
            if page_no not in rendered:
                rendered[page_no] = pdfium_doc[page_no - 1].render(scale=3).to_pil()
            im = rendered[page_no]
            l, t, r, b = crop_box
            crops.append(im.crop((max(0, int(l * 3)), max(0, int(t * 3)), min(im.width, int(r * 3)), min(im.height, int(b * 3)))))
            eqs.append({"page": page_no, "bbox": [bb.l, bb.t, bb.r, bb.b], "coord_origin": "BOTTOMLEFT",
                        "latex": "", "number": None, "rule": rule, "crop_box": [round(x, 2) for x in crop_box]})
        latexes = _codeformula_run(model, crops) if crops else []
        for e, latex in zip(eqs, latexes):
            e["latex"] = (latex or "").strip()
            page = pl.pages[e["page"] - 1] if pl is not None else None
            bb = type("B", (), {})()
            if e["rule"] == "R2":                  # the number sits right of the band, not of the number-only box
                H = doc.pages[e["page"]].size.height
                l, t, r, b = e["crop_box"]
                bb.l, bb.t, bb.r, bb.b = l, H - t, r, H - b
            else:
                bb.l, bb.t, bb.r, bb.b = e["bbox"]
            e["number"] = _printed_number(e["latex"], page, bb)
        if pl is not None:
            pl.close()
        d = OUT / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "equations.json").write_text(json.dumps(eqs, indent=1, ensure_ascii=False))
        print(f"[formulas] {pid}: {len(eqs)} formula items, {sum(1 for e in eqs if e['latex'])} with LaTeX, "
              f"{sum(1 for e in eqs if e['number'])} numbered, {sum(1 for e in eqs if e['rule'] == 'R2')} band boxes, "
              f"{time.time() - t0:.0f}s -> docling/{pid}/equations.json", flush=True)


def fetch_abstracts(rows):
    """One network call per 50 DOIs: OpenAlex abstracts (abstract_inverted_index) of the in-scope
    papers -> corpus/openalex_abstracts.json (gitignored). The only step here that uses the network."""
    import datetime
    sys.path.insert(0, str(CORPUS))
    from fetch_pdfs import make_session, openalex_works, normalise_doi
    todo = [r for r in rows if r.get("in_scope") == "yes" and r.get("doi")]
    works = openalex_works(make_session(), todo, select="doi,abstract_inverted_index")
    papers, n_abs = {}, 0
    for r in todo:
        work = works.get(normalise_doi(r["doi"]), {})
        inv = work.get("abstract_inverted_index")
        text = None
        if inv:
            pos = sorted((p, w) for w, ps in inv.items() for p in ps)
            text = " ".join(w for _, w in pos)
            n_abs += 1
        papers[r["paper_id"]] = {"doi": r["doi"], "abstract": text}
    OA_ABSTRACTS.write_text(json.dumps({"fetched_on": datetime.date.today().isoformat(),
                                        "source": "OpenAlex works.abstract_inverted_index",
                                        "papers": papers}, indent=1, ensure_ascii=False))
    print(f"{len(todo)} in-scope papers queried, {n_abs} with an OpenAlex abstract -> {OA_ABSTRACTS}")


def main(argv):
    rows = read_manifest()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    if argv[:1] == ["--formulas"]:
        return formulas(by_id, argv[1:])
    if argv == ["--fetch-abstracts"]:
        return fetch_abstracts(rows)
    sys.exit("usage: parse_docling.py --formulas <paper_id> [...] | --fetch-abstracts")


if __name__ == "__main__":
    main(sys.argv[1:])
