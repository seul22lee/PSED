#!/usr/bin/env python3
"""Docling parse: corpus/raw/<paper_id>.pdf -> ingest/docling/<paper_id>/. No LLM.

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py <paper_id> [...]
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --all
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --rebind <paper_id> [...] | --rebind --all

--rebind reruns caption binding and the text repairs from docling.json and the saved crops,
without Docling. Use it whenever only the binding rules change.

Writes, per paper:

    docling/<paper_id>/document.md      full markdown
    docling/<paper_id>/docling.json     Docling's document, images as placeholders
    docling/<paper_id>/figures/pic_K.png one crop per Docling picture (K = index in doc.pictures)
    docling/<paper_id>/structure.json   {n_pages, sections[headings], n_pictures, n_tables,
                                         captions[{kind, number, caption, images|table, page}]}

Caption binding (replaces Docling's), in Docling's reading order:
- a caption is text starting with Fig./Figure/Scheme/Table (or 图/表) + number (not "Figs."), kept only
  if Docling labels it caption, or the number is followed by ".", ":" or "|", or it is text
  nested inside a picture that starts with Fig./Figure/Scheme + number. A caption that
  qualifies through that last rule alone (no caption label, no punctuation after the number)
  continues with the text items nested under the same picture after it that have at least 4
  words, up to the next caption or the end of the picture; for a repeated
  kind+number the one with that punctuation wins, then the Docling-labelled one, else the first;
- pictures whose box lies outside the page area (margin artifacts) are ignored;
- decoration pictures are ignored: the same image (16x16 grayscale thumbnail, exact match)
  on 2 or more pages;
- each picture goes to the first match: (1) the next figure/scheme caption on the same page
  whose horizontal span overlaps the picture's; (2) for a picture after the last text item
  on its page, the first text item of the next page if that is a figure/scheme caption;
  (3) the previous figure/scheme caption on the same page, else the next one on that page;
  (4) else it stays unnumbered. In (1) a dropped duplicate caption counts for its number when
  that number's kept caption also comes after the picture.
  Captions nested inside pictures are included;
- manuscripts with all captions together and the figures at the end: if two or more figure
  captions got no image and the unnumbered pictures after the last caption page sit on exactly
  that many pages, those pages are bound to the captions in number order;
- a caption that is the last text item on its page and does not end with ".", ")" or "]"
  continues with the first text item of the next page;
- a table goes to the latest earlier table caption without a table, else stays unnumbered.
Unnumbered items are listed with number null.

Glyph repairs, applied to document.md and caption text after Docling runs:
- glyph names that carry a code point, "/uniXXXX" and "/uXXXXX", become that character
  (ligatures U+FB00..FB06 become plain letters); the one space after it is dropped when a
  letter follows;
- a single digit between a number and C or K ("300 1 C") is marked "[?]" ("300 [?] C") only
  where the PDF shows that digit in a different font from the number (read with pdfplumber).
  What the symbol is, is not guessed. Other glyph problems are left unchanged.

Progress lives in corpus/manifest.csv, column `docling`: ok | failed | blank (not run).
The column is written after each paper; rows already ok are skipped.
Only in-scope papers are parsed (manifest column in_scope, set by corpus/make_report.py).
--all parses every in-scope row with pdf_status ok. Needs docling (conda env psed310).
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
CORPUS = HERE.parent / "corpus"
MANIFEST = CORPUS / "manifest.csv"
RAW = CORPUS / "raw"
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


CAPTION_RE = re.compile(r"\s*(Fig\.|FIG\.|Figure(?!s)|FIGURE(?!S)|Scheme(?!s)|SCHEME(?!S)|Table(?!s)|TABLE(?!S)|图|表)"
                        r"\s*(S?\d+|[IVXL]+)(?!\d)(\s*[.:|])?")


def _caption_kind(word):
    w = word.lower()
    return "table" if w.startswith(("table", "表")) else "scheme" if w.startswith("scheme") else "figure"


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


# Glyph names that carry a code point: "/uniXXXX" (4 hex) and "/uXXXXX" (5 hex). Docling
# leaves one space after the name; it is dropped when a letter follows.
GLYPH_NAME_RE = re.compile(r"/(?:uni([0-9A-Fa-f]{4})|u([0-9A-Fa-f]{5}))(?![0-9A-Fa-f])( (?=[A-Za-z]))?")
LIGATURES = {0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl",
             0xFB05: "st", 0xFB06: "st"}
# A number, a single digit, then C or K: "300 1 C", "325 8C".
DEGREE_RE = re.compile(r"(?<![\d.])(\d{1,4}) (\d) ?([CK])\b")


def _glyph_names(text):
    """Replace /uniXXXX and /uXXXXX glyph names with their character (ligatures as letters)."""
    def sub(m):
        cp = int(m.group(1) or m.group(2), 16)
        return LIGATURES.get(cp) or chr(cp)
    return GLYPH_NAME_RE.sub(sub, text)


def _degree_evidence(pdf):
    """{(number, digit, unit)} seen in the PDF where a single digit sits between a number and
    C or K and is set in a different font from the number: a symbol whose glyph maps to a digit."""
    found = set()
    try:
        import pdfplumber
    except ImportError:
        print("  pdfplumber not installed: digit-like degree signs are not marked", flush=True)
        return found
    try:
        with pdfplumber.open(str(pdf)) as doc:
            for page in doc.pages:
                ch = [c for c in page.chars if c["text"].strip()]
                for i in range(1, len(ch) - 1):
                    c, prev = ch[i], ch[i - 1]
                    if not (c["text"].isdigit() and ch[i + 1]["text"] in ("C", "K")
                            and prev["text"].isdigit() and prev["fontname"] != c["fontname"]):
                        continue
                    j = i - 1
                    while j > 0 and ch[j - 1]["text"].isdigit() and ch[j - 1]["fontname"] == prev["fontname"]:
                        j -= 1
                    found.add(("".join(x["text"] for x in ch[j:i]), c["text"], ch[i + 1]["text"]))
    except Exception as e:
        print(f"  pdfplumber failed ({e.__class__.__name__}): digit-like degree signs are not marked", flush=True)
    return found


def _mark_degrees(text, evidence):
    """Mark "300 1 C" as "300 [?] C" where the PDF shows the digit is in another font."""
    if not evidence:
        return text
    return DEGREE_RE.sub(
        lambda m: f"{m.group(1)} [?] {m.group(3)}" if m.groups() in evidence else m.group(0), text)


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


def convert(pdf, force_ocr=False):
    """Run Docling on the PDF (the only step that needs Docling and its models)."""
    return _converter(force_ocr).convert(pdf).document


def _pic_index(item):
    return int(item.self_ref.rsplit("/", 1)[1])


def save_docling(doc, d):
    """Save Docling's output so binding can rerun without Docling: docling.json (no embedded
    images) and one crop per picture, figures/pic_<k>.png, k = index in doc.pictures."""
    from docling_core.types.doc import ImageRefMode
    figdir = d / "figures"
    shutil.rmtree(figdir, ignore_errors=True)        # old crops never linger
    figdir.mkdir(parents=True, exist_ok=True)
    for item in doc.pictures:
        try:
            im = item.get_image(doc)
            if im is not None:
                im.save(figdir / f"pic_{_pic_index(item)}.png")
        except Exception:
            pass
    for item in doc.pictures:                        # crops are saved above; keep the JSON small
        item.image = None
    for page in doc.pages.values():
        page.image = None
    doc.save_as_json(d / "docling.json", image_mode=ImageRefMode.PLACEHOLDER)


def load_docling(d):
    from docling_core.types.doc import DoclingDocument
    return DoclingDocument.load_from_json(d / "docling.json")


def bind(doc, pdf, figdir):
    """Caption binding and text repairs on a Docling document. No Docling run: crops are read
    from figdir (figures/pic_<k>.png), the PDF only for page boxes and font evidence."""
    from PIL import Image
    evidence = _degree_evidence(pdf)
    fix = lambda text: _mark_degrees(_glyph_names(text), evidence)
    md = fix(doc.export_to_markdown())

    # 1. reading-order sequence. Text nested inside a picture (axis labels, scale bars) is not
    #    a text item of the page, except captions, which Docling may nest there.
    areas = _page_areas(pdf)
    # decoration: the same image (16x16 grayscale thumbnail, exact match) on 2 or more pages
    images, thumb_pages = {}, {}
    for item, _level in doc.iterate_items(traverse_pictures=True):
        if type(item).__name__ != "PictureItem":
            continue
        path = figdir / f"pic_{_pic_index(item)}.png"
        try:
            im = Image.open(path) if path.exists() else None
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
    open_cap = None     # a caption nested inside the current picture, collecting the text after it
    for item, level in doc.iterate_items(traverse_pictures=True):
        cls = type(item).__name__
        page = _page(item)
        if pic_level is not None and level <= pic_level:
            pic_level = None
            open_cap = None                 # end of that picture
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
            imgpath = f"figures/pic_{_pic_index(item)}.png" if im is not None else ""
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
            # a caption: Docling labels it caption, or the number is followed by . : |, or it is
            # text nested inside a picture that starts with Fig./Figure/Scheme + number
            nested_fig = nested and m is not None and m.group(1).lower().startswith(("fig", "scheme"))
            if m and (is_cap_label or m.group(3) or nested_fig):
                cands.append({"kind": _caption_kind(m.group(1)), "number": m.group(2),
                              "caption": re.sub(r"\s+", " ", text).strip(), "page": page,
                              "span": _span(item), "labelled": is_cap_label,
                              "punct": bool(m.group(3))})
                seq.append(("cap", len(cands) - 1, page, text))
                # only a caption that qualifies through the nested-text rule alone collects text
                open_cap = len(cands) - 1 if (nested_fig and not is_cap_label and not m.group(3)) else None
            elif nested and open_cap is not None:
                # text nested under the same picture after that caption continues it, if it has
                # at least 4 words (shorter items are panel or axis labels and are skipped)
                if len(text.split()) >= 4:
                    cands[open_cap]["caption"] += " " + re.sub(r"\s+", " ", text).strip()
            elif not nested and text.strip():
                seq.append(("text", None, page, text))

    # 2. one caption per kind+number. Preference: the number is followed by . : | (a body
    #    sentence like "Figure 10 shows" is not), then Docling-labelled, then the first.
    keep = {}
    rank = lambda c: (c["punct"], c["labelled"])
    for i, c in enumerate(cands):
        k = (c["kind"], c["number"])
        if k not in keep or rank(c) > rank(cands[keep[k]]):
            keep[k] = i
    kept = set(keep.values())
    # every candidate stands for its kind+number's kept caption (used for the overlap test)
    kept_of = {i: keep[(c["kind"], c["number"])] for i, c in enumerate(cands)}

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
            e = {"kind": c["kind"], "number": c["number"], "caption": fix(caption), "page": c["page"]}
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
        # (1) a later caption candidate on the page counts for its number, a dropped duplicate
        #     included, but only if that number's kept caption also comes after the picture
        later_kept = {x[1] for x in same_after}
        for later in seq[pos + 1:]:
            if later[2] != page or later[0] != "cap" or cands[later[1]]["kind"] == "table":
                continue
            if kept_of[later[1]] in later_kept and _overlap(cands[later[1]]["span"], pic["span"]):
                target = kept_of[later[1]]
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

    # 4b. manuscripts that list the captions together and put the figures at the end: if two
    #     or more figure captions got no image and the unnumbered pictures after the last
    #     caption page sit on exactly that many pages, bind them page by page in number order.
    fig_entries = [e for e in entries if e["kind"] != "table" and e["number"] is not None]
    empty = sorted((e for e in fig_entries if not e["images"] and e["number"].isdigit()),
                   key=lambda e: int(e["number"]))
    if len(empty) >= 2:
        last_cap_page = max(e["page"] for e in fig_entries if e["page"] is not None)
        late = [j for j in loose_pics if (pics[j]["page"] or 0) > last_cap_page]
        late_pages = sorted({pics[j]["page"] for j in late})
        if len(late_pages) == len(empty):
            for e, pg in zip(empty, late_pages):
                e["images"] = [pics[j]["image"] for j in late if pics[j]["page"] == pg and pics[j]["image"]]
            loose_pics = [j for j in loose_pics if j not in late]

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


def _write(d, md, struct, ocr_forced):
    if ocr_forced:
        struct["ocr_forced"] = True
    (d / "document.md").write_text(md)
    (d / "structure.json").write_text(json.dumps(struct, indent=1))


def parse_one(paper_id):
    """Docling run + binding: writes docling.json, figures/, document.md, structure.json."""
    pdf = RAW / f"{paper_id}.pdf"
    d = OUT / paper_id
    d.mkdir(parents=True, exist_ok=True)
    doc = convert(pdf)
    ocr = False
    n = len(doc.export_to_markdown())
    if n < 500:                                     # image-only PDF -> force full-page OCR
        print(f"  only {n} chars; retrying with full-page OCR", flush=True)
        doc, ocr = convert(pdf, force_ocr=True), True
    save_docling(doc, d)
    md, struct = bind(doc, pdf, d / "figures")
    _write(d, md, struct, ocr)
    return md, struct


def rebind_one(paper_id):
    """Binding only, from the saved docling.json and crops; no Docling run."""
    d = OUT / paper_id
    old = json.loads((d / "structure.json").read_text()) if (d / "structure.json").exists() else {}
    md, struct = bind(load_docling(d), RAW / f"{paper_id}.pdf", d / "figures")
    _write(d, md, struct, old.get("ocr_forced", False))
    return md, struct


def main(argv):
    rows, fields = read_manifest()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    if argv[:1] == ["--rebind"]:
        return rebind(rows, by_id, argv[1:])
    if argv == ["--all"]:
        todo = [r for r in rows if r["pdf_status"] == "ok" and r.get("in_scope") == "yes"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: parse_docling.py <paper_id> [...] | --all  (unknown: {missing})")
        todo = [by_id[a] for a in argv]
    for r in todo:
        pid = r["paper_id"]
        if r.get("in_scope") != "yes":
            print(f"[docling] {pid}: not in scope, skipped")
            continue
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


def rebind(rows, by_id, argv):
    """Rerun caption binding for parsed papers from docling.json; the docling column is unchanged."""
    if argv == ["--all"]:
        todo = [r for r in rows if r.get("in_scope") == "yes" and r["docling"] == "ok"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: parse_docling.py --rebind <paper_id> [...] | --rebind --all  (unknown: {missing})")
        todo = [by_id[a] for a in argv]
    for r in todo:
        pid = r["paper_id"]
        if not (OUT / pid / "docling.json").exists():
            print(f"[rebind] {pid}: no docling.json, run a full parse first")
            continue
        md, struct = rebind_one(pid)
        print(f"[rebind] {pid}: {len(md)} md chars, {struct['n_pictures']} pictures, "
              f"{sum(1 for c in struct['captions'] if c['number'] is not None)} captions", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
