#!/usr/bin/env python3
"""Docling parse: corpus/raw/<paper_id>.pdf -> ingest/docling/<paper_id>/. No LLM.

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py <paper_id> [...]
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --all
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --rebind <paper_id> [...] | --rebind --all
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --fetch-abstracts
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/parse_docling.py --check-abstracts

--rebind reruns caption binding and the text repairs from docling.json and the saved crops,
without Docling. Use it whenever only the binding rules change.

Writes, per paper:

    docling/<paper_id>/document.md      full markdown
    docling/<paper_id>/docling.json     Docling's document, images as placeholders
    docling/<paper_id>/figures/pic_K.png one crop per Docling picture (K = index in doc.pictures)
    docling/<paper_id>/figures/tab_K.png one crop per Docling table (K = index in doc.tables), cut
                                        from the PDF page with pypdfium2 at the picture scale
    docling/<paper_id>/structure.json   {n_pages, sections[headings], n_pictures, n_tables,
                                         captions[{kind, number, caption, images|table+image, page}],
                                         abstract, abstract_source}

Caption binding (replaces Docling's), in Docling's reading order:
- a caption is text starting with Fig./Figure/Scheme/Table (or 图/表) + number (not "Figs."; the
  number may carry a letter prefix: S1, A1), kept only if Docling labels it caption, or the number
  is followed by ".", ":" or "|", or it is text nested inside a picture that starts with
  Fig./Figure/Scheme + number, or it is a Table caption whose number is followed by a capitalised
  word ("Table 1 Summary ...", any label). A caption that
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
- a table whose Docling caption link (item.captions) points to a "Table N" caption takes that
  caption; else it goes to the nearest unused table caption on the same page, before or after it
  in reading order (tie: before), never across pages; else it stays unnumbered. Linked tables
  are bound first. Glyph repairs (below) are applied to the table markdown too. The markdown
  is built from Docling's cell grid: the column-header rows at the top become one header line,
  the texts per column joined with " / " (one header row: Docling's own export, unchanged).
Unnumbered items are listed with number null.

Abstract (structure.json "abstract", "abstract_source"), from Docling's text items, not reading order
alone, so an abstract placed inside the introduction is still found. "Page 1" is the first page with
running text (publisher cover pages are skipped). In order:
1. the text under a heading "Abstract", or a paragraph starting with "Abstract:" (ACS), with its
   continuation items -> "heading";
2. else, if OpenAlex has an abstract (corpus/openalex_abstracts.json, fetched once with
   --fetch-abstracts; --rebind never calls the network): the text item on pages 1-2 with the
   highest word overlap with it, joined with adjacent items that also overlap -> "openalex_match";
3. else the longest text item on page 1 that is wider than the body columns (1.4 x the median
   column width; full-width on a two-column page) -> "layout";
4. else the longest paragraph (40+ words) on page 1 after the author block and before the first
   body heading -> "order"; if nothing, empty and "none".
Fallback: if the abstract's Docling items have no PDF text layer under them (OCR; pdfplumber finds
no characters in their boxes) and the recall against the OpenAlex abstract is below 80%, the
OpenAlex abstract is used instead -> "openalex".
The glyph repairs are applied; document.md is unchanged. --check-abstracts prints, per paper,
recall (OpenAlex words in ours), precision (our words in OpenAlex) and length ratio (our words /
OpenAlex words); flags recall < 80%, precision < 80%, ratio > 1.5 or < 0.6. In the check only, an
OpenAlex abstract under 50 words (a cover blurb) counts as missing; a paper without a usable
OpenAlex abstract is flagged only if its abstract fails the form check: 80-400 words, ends with
".", and comes right after the title/author block. An empty abstract is always flagged. Manifest
column abstract_review records a review as "ok:<hash>" or "limit:<hash>" (first 8 hex of the
sha1 of the reviewed abstract); a paper is skipped only while its abstract still has that hash.
Writes ingest/review/abstract_check.html (gitignored) for the flagged papers.

Running heads, footers and download stamps: a text of 10 words or fewer that appears identically
(after the glyph repairs) on 3 or more pages and contains 4 or more letters (A-Z, a-z) is dropped
from document.md. The abstract items, captions and tables are not touched.

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
                        r"\s*([A-Z]?\d+|[IVXL]+)(?!\d)(\s*[.:|])?")
# a capitalised word after the number: "Table 1 Summary of ..." is a caption, "Table 1 shows" is not
CAPWORD_RE = re.compile(r"\s+[A-Z][A-Za-z]*(?![A-Za-z])")


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


OA_ABSTRACTS = CORPUS / "openalex_abstracts.json"
ABSTRACT_HEAD_RE = re.compile(r"\s*abstract\s*[:.]?\s*$", re.I)
ABSTRACT_INLINE_RE = re.compile(r"\s*abstract\s*[:.\-–—]\s*", re.I)
KEYWORDS_RE = re.compile(r"\s*(keywords?|key\s*words|■|graphical abstract|toc graphic)\b", re.I)
BODY_HEAD_RE = re.compile(r"\b(introduction|background|results|experimental|methods?|materials)\b", re.I)
WORD_RE = re.compile(r"[a-z0-9]{3,}")
BODY_LABELS = ("text", "paragraph")


def _words(text):
    return set(WORD_RE.findall((text or "").lower()))


def _load_oa_abstracts():
    """{paper_id: abstract text} from corpus/openalex_abstracts.json (written by --fetch-abstracts)."""
    try:
        data = json.loads(OA_ABSTRACTS.read_text())
    except (OSError, ValueError):
        return {}
    return {pid: (v or {}).get("abstract") for pid, v in data.get("papers", {}).items()}


def _running_lines(doc, fix):
    """Texts of 10 words or fewer with 4 or more letters that appear identically (after the glyph
    repairs) on 3 or more pages: running heads, footers, download stamps."""
    pages = {}
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        prov = (getattr(item, "prov", None) or [None])[0]
        if text is None or prov is None:
            continue
        t = re.sub(r"\s+", " ", fix(text)).strip()
        if t and len(t.split()) <= 10 and len(re.findall(r"[A-Za-z]", t)) >= 4:
            pages.setdefault(t, set()).add(prov.page_no)
    return {t for t, p in pages.items() if len(p) >= 3}


def _drop_running(md, running):
    """document.md without the running lines (markdown markers stripped for the comparison);
    runs of blank lines are collapsed. Returns (markdown, {line: count dropped})."""
    out, dropped = [], {}
    for line in md.split("\n"):
        core = re.sub(r"\s+", " ", re.sub(r"^(#{1,6}\s+|[-*]\s+|>\s+)", "", line.strip()))
        if core in running:
            dropped[core] = dropped.get(core, 0) + 1
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)), dropped


def _abstract(doc, oa_text):
    """(abstract, source) from Docling's text items; see the module docstring."""
    seq = []
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        prov = (getattr(item, "prov", None) or [None])[0]
        if text is None or prov is None:
            continue
        seq.append({"label": _label(item), "page": prov.page_no,
                    "width": abs(prov.bbox.r - prov.bbox.l), "text": text, "n": len(text.split())})
    is_body = lambda s: s["label"] in BODY_LABELS
    oa_words = _words(oa_text) if oa_text else set()
    def precision(s):
        w = _words(s["text"])
        return len(w & oa_words) / len(w) if w else 0.0

    def continuation(i, page):
        """Body items after seq[i] on the same page that continue a block: not a heading, not a
        keywords line; with OpenAlex they must overlap it, without it they follow while the text
        has not reached a sentence end (at most two)."""
        out, taken = [], 0
        for s in seq[i + 1:]:
            if s["page"] != page or s["label"] == "section_header" or KEYWORDS_RE.match(s["text"]):
                break
            if not is_body(s) or s["n"] < 8:      # pictures, widgets ("Supporting Information")
                continue
            if oa_words:
                if precision(s) < 0.6:
                    break
            else:
                prev = (out[-1] if out else seq[i])["text"].rstrip()
                if prev.endswith((".", "!", "?")) or taken >= 2:
                    break
            out.append(s); taken += 1
        return out

    # 1. heading "Abstract", or an inline "Abstract:" paragraph
    for i, s in enumerate(seq):
        if s["label"] == "section_header" and ABSTRACT_HEAD_RE.match(s["text"]):
            block, width0, words = [], None, 0
            for t in seq[i + 1:]:
                if t["label"] == "section_header" or KEYWORDS_RE.match(t["text"]) or t["page"] > s["page"] + 1:
                    break
                if not is_body(t) or t["n"] < 8:
                    continue
                # the body starts where the overlap with OpenAlex drops, else where the column
                # gets narrower (full-width abstract over a two-column body); 400 words at most
                if oa_words and precision(t) < 0.6:
                    break
                if not oa_words and width0 is not None and t["width"] < 0.7 * width0:
                    break
                if words >= 400:
                    break
                width0 = width0 or t["width"]
                block.append(t["text"]); words += t["n"]
            if words >= 20:
                return " ".join(block), "heading"
    for i, s in enumerate(seq):
        if is_body(s) and ABSTRACT_INLINE_RE.match(s["text"]) and s["n"] >= 20:
            first = ABSTRACT_INLINE_RE.sub("", s["text"], count=1)
            return " ".join([first] + [t["text"] for t in continuation(i, s["page"])]), "heading"

    # 2. best word overlap with the OpenAlex abstract on pages 1-2, extended to adjacent items
    if oa_words:
        cands = [i for i, s in enumerate(seq) if is_body(s) and s["page"] <= 2 and s["n"] >= 15]
        if cands:
            recall = lambda i: len(_words(seq[i]["text"]) & oa_words) / len(oa_words)
            best = max(cands, key=recall)
            if recall(best) >= 0.2:
                covered = _words(seq[best]["text"]) & oa_words
                def grow(step):
                    """Last index reached walking from best in one direction: past pictures and
                    short items, over body items that overlap OpenAlex and add to it; stops at a
                    heading, a page beyond 2, or a body item that does not fit."""
                    nonlocal covered
                    j, k = best, best + step
                    while 0 <= k < len(seq):
                        s = seq[k]
                        if s["label"] == "section_header" or s["page"] > 2:
                            break
                        if is_body(s) and s["n"] >= 8:
                            new = (_words(s["text"]) & oa_words) - covered
                            if precision(s) < 0.6 or len(new) < 3:
                                break
                            covered |= new
                            j = k
                        k += step
                    return j
                lo, hi = grow(-1), grow(1)
                return " ".join(s["text"] for s in seq[lo:hi + 1] if is_body(s) and s["n"] >= 8), "openalex_match"

    # "page 1": the first page with running text
    long_pages = [s["page"] for s in seq if is_body(s) and s["n"] >= 25]
    if not long_pages:
        return "", "none"
    page1 = min(long_pages)
    on_page1 = [i for i, s in enumerate(seq) if is_body(s) and s["page"] == page1 and s["n"] >= 25]

    # 3. the longest item on page 1 wider than the body columns
    widths = sorted(s["width"] for s in seq if is_body(s) and s["n"] >= 30 and s["page"] <= page1 + 2)
    if widths:
        column = widths[len(widths) // 2]
        wide = [i for i in on_page1 if seq[i]["width"] > 1.4 * column]
        if wide:
            return seq[max(wide, key=lambda i: seq[i]["n"])]["text"], "layout"

    # 4. the longest paragraph on page 1 after the author block and before the first body heading
    first_head = next((i for i, s in enumerate(seq) if s["label"] == "section_header"
                       and BODY_HEAD_RE.search(s["text"]) and s["page"] >= page1), len(seq))
    paras = [i for i in on_page1 if i < first_head and seq[i]["n"] >= 40]
    if paras:
        return seq[max(paras, key=lambda i: seq[i]["n"])]["text"], "order"
    return "", "none"


def _abstract_is_ocr(doc, pdf, abstract):
    """True if every Docling text item that makes up the abstract (8+ words, text found in it)
    has no PDF text layer under its box: pdfplumber finds no characters there."""
    try:
        import pdfplumber
    except ImportError:
        return False
    norm = lambda t: re.sub(r"\s+", " ", t).strip()
    target = norm(abstract)
    boxes = []
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        prov = (getattr(item, "prov", None) or [None])[0]
        if text is None or prov is None or _label(item) not in BODY_LABELS or len(text.split()) < 8:
            continue
        if norm(text)[:60] in target:
            boxes.append((prov.page_no, prov.bbox))
    if not boxes:
        return False
    try:
        with pdfplumber.open(str(pdf)) as pl:
            for page_no, bb in boxes:
                page = pl.pages[page_no - 1]
                H, x0 = page.height, page.bbox[0]
                top, bottom = H - max(bb.t, bb.b), H - min(bb.t, bb.b)
                l, r = min(bb.l, bb.r) + x0, max(bb.l, bb.r) + x0
                if any(l - 2 <= c["x0"] <= r + 2 and top - 2 <= c["top"] <= bottom + 2 for c in page.chars):
                    return False
    except Exception:
        return False
    return True


def _table_markdown(item, doc):
    """Markdown of a table from Docling's cell grid. Rows whose cells are column headers (Docling's
    column_header flag, the contiguous rows at the top) become one header line, the header texts
    per column joined with " / "; a cell spanning several columns applies to each, repeated
    identical parts are skipped. With 0 or 1 header rows the result is Docling's own export,
    byte for byte (Docling's caption text stays in front of the table either way)."""
    full = item.export_to_markdown(doc)
    grid = item.data.grid
    n_hdr = 0
    while n_hdr < len(grid) and any(getattr(c, "column_header", False) for c in grid[n_hdr]):
        n_hdr += 1
    if n_hdr <= 1 or not grid:
        return full
    try:
        from tabulate import tabulate
        cell = lambda c: c.text.replace("\n", " ").replace("|", "&#124;")
        rows = [[cell(c) for c in row] for row in grid]
        if any(not hasattr(c, "text") for row in grid for c in row):
            return full
        def table(body, header):
            try:
                return tabulate(body, headers=header, tablefmt="github")
            except ValueError:
                return tabulate(body, headers=header, tablefmt="github", disable_numparse=True)
        own = table(rows[1:], rows[0])                    # what Docling's export ends with
        if not full.endswith(own):
            return full
        header = []
        for j in range(len(rows[0])):
            parts = []
            for r in range(n_hdr):
                t = rows[r][j].strip()
                if t and t not in parts:
                    parts.append(t)
            header.append(" / ".join(parts))
        return full[:len(full) - len(own)] + table(rows[n_hdr:], header)
    except Exception:
        return full


def _table_crops(doc, pdf, figdir, scale=3):
    """One crop per Docling table, figures/tab_<k>.png (k = index in doc.tables), cut from the PDF
    page with pypdfium2 at the picture scale (no page images are kept, so --rebind can do this too).
    Docling's boxes are bottom-left, shifted so the MediaBox starts at 0. Returns {self_ref: path}."""
    out = {}
    try:
        import pypdfium2
        pdoc = pypdfium2.PdfDocument(str(pdf))
    except Exception as e:
        print(f"  table crops skipped ({e.__class__.__name__}: {e})", flush=True)
        return out
    figdir.mkdir(parents=True, exist_ok=True)
    for old in figdir.glob("tab_*.png"):
        old.unlink()
    pages = {}
    for k, item in enumerate(doc.tables):
        prov = (getattr(item, "prov", None) or [None])[0]
        bb = getattr(prov, "bbox", None)
        if bb is None:
            continue
        try:
            pno = prov.page_no
            if pno not in pages:
                page = pdoc[pno - 1]
                ml, mb, _, _ = page.get_mediabox()
                cl, _, _, ct = page.get_cropbox()
                pages[pno] = (page.render(scale=scale).to_pil(), ml, mb, cl, ct)
            im, ml, mb, cl, ct = pages[pno]
            x0 = (min(bb.l, bb.r) + ml - cl) * scale
            x1 = (max(bb.l, bb.r) + ml - cl) * scale
            y0 = (ct - (max(bb.t, bb.b) + mb)) * scale
            y1 = (ct - (min(bb.t, bb.b) + mb)) * scale
            box = (max(0, int(x0)), max(0, int(y0)), min(im.width, int(x1) + 1), min(im.height, int(y1) + 1))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            im.crop(box).save(figdir / f"tab_{k}.png")
            out[item.self_ref] = f"figures/tab_{k}.png"
        except Exception as e:
            print(f"  table {k} crop failed ({e.__class__.__name__}: {e})", flush=True)
    return out


def bind(doc, pdf, figdir):
    """Caption binding and text repairs on a Docling document. No Docling run: crops are read
    from figdir (figures/pic_<k>.png), the PDF only for page boxes and font evidence."""
    from PIL import Image
    evidence = _degree_evidence(pdf)
    fix = lambda text: _mark_degrees(_glyph_names(text), evidence)
    md, _dropped = _drop_running(fix(doc.export_to_markdown()), _running_lines(doc, fix))
    tab_images = _table_crops(doc, pdf, figdir)

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
                tmd = fix(_table_markdown(item, doc))
            except Exception:
                tmd = ""
            tabs.append({"markdown": tmd, "page": page, "image": tab_images.get(item.self_ref, ""),
                         "cap_refs": [getattr(r, "cref", None) for r in (getattr(item, "captions", None) or [])]})
            seq.append(("tab", len(tabs) - 1, page, ""))
        else:
            text = getattr(item, "text", "") or ""
            m = CAPTION_RE.match(text)
            is_cap_label = _label(item) == "caption"
            # a caption: Docling labels it caption, or the number is followed by . : |, or it is
            # text nested inside a picture that starts with Fig./Figure/Scheme + number
            nested_fig = nested and m is not None and m.group(1).lower().startswith(("fig", "scheme"))
            # a Table caption of any label when a capitalised word follows the number
            table_cap = (m is not None and _caption_kind(m.group(1)) == "table"
                         and CAPWORD_RE.match(text, m.end()) is not None)
            if m and (is_cap_label or m.group(3) or nested_fig or table_cap):
                cands.append({"kind": _caption_kind(m.group(1)), "number": m.group(2),
                              "caption": re.sub(r"\s+", " ", text).strip(), "page": page,
                              "span": _span(item), "labelled": is_cap_label,
                              "punct": bool(m.group(3)), "ref": item.self_ref})
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
                e["table"], e["image"] = "", ""
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

    # 5. tables: (1) a table whose Docling caption link points to a "Table N" caption takes that
    #    caption (the kept one for that number) and marks it used; (2) else the nearest unused
    #    table caption on the same page, before or after the table in reading order (tie: before),
    #    never across pages; (3) else unnumbered. Linked tables are bound first.
    cand_of_ref = {c["ref"]: i for i, c in enumerate(cands)}
    tab_pos = {st[1]: pos for pos, st in enumerate(seq) if st[0] == "tab"}
    cap_pos = {st[1]: pos for pos, st in enumerate(seq)
               if st[0] == "cap" and st[1] in kept and cands[st[1]]["kind"] == "table"}
    used, bound_tab = set(), {}
    for j, tab in enumerate(tabs):
        for ref in tab["cap_refs"]:
            ci = cand_of_ref.get(ref)
            if ci is None or cands[ci]["kind"] != "table":
                continue
            ki = kept_of[ci]
            if ki not in used:
                bound_tab[j], _ = ki, used.add(ki)
                break
    for j, tab in enumerate(tabs):
        if j in bound_tab or tab["page"] is None:
            continue
        free = [(abs(pos - tab_pos[j]), pos > tab_pos[j], ki) for ki, pos in cap_pos.items()
                if ki not in used and cands[ki]["page"] == tab["page"]]
        if free:
            ki = min(free)[2]
            bound_tab[j], _ = ki, used.add(ki)
    loose_tabs = []
    for j, tab in enumerate(tabs):
        if j in bound_tab:
            e = entry_of[bound_tab[j]]
            e["table"], e["image"] = tab["markdown"], tab["image"]
        else:
            loose_tabs.append(j)

    for j in loose_pics:
        entries.append({"kind": "figure", "number": None, "caption": "",
                        "images": [pics[j]["image"]] if pics[j]["image"] else [], "page": pics[j]["page"]})
    for j in loose_tabs:
        entries.append({"kind": "table", "number": None, "caption": "", "table": tabs[j]["markdown"],
                        "image": tabs[j]["image"], "page": tabs[j]["page"]})

    sections = [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", md, re.M)]
    oa_text = _load_oa_abstracts().get(Path(pdf).stem)
    abstract, source = _abstract(doc, oa_text)
    abstract = re.sub(r"\s+", " ", fix(abstract)).strip()
    if abstract and oa_text and _abstract_is_ocr(doc, pdf, abstract):
        ow = _words(oa_text)
        if ow and len(_words(abstract) & ow) / len(ow) < 0.8:
            abstract, source = re.sub(r"\s+", " ", oa_text).strip(), "openalex"
    return md, {"n_pages": getattr(doc, "num_pages", lambda: None)() if callable(getattr(doc, "num_pages", None)) else None,
                "sections": sections, "n_pictures": len(pics), "n_tables": len(tabs),
                "captions": entries, "abstract": abstract, "abstract_source": source}


def read_manifest():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    for col in ("docling", "abstract_review"):
        if col not in fields:
            fields.append(col)
    for r in rows:
        r.setdefault("docling", "")
        r.setdefault("abstract_review", "")
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
    if argv == ["--fetch-abstracts"]:
        return fetch_abstracts(rows)
    if argv == ["--check-abstracts"]:
        return check_abstracts(rows)
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


AUTHOR_BLOCK_RE = re.compile(r"universit|department|institute|laborator|faculty|school|cent(er|re)|@|"
                             r"received|accepted|corresponding|e-?mail|orcid", re.I)


def _abstract_hash(text):
    """First 8 hex of the sha1 of the abstract, as stored in manifest column abstract_review."""
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _abstract_form_problems(pid, ours):
    """Form check for a paper without a usable OpenAlex abstract: 80-400 words, ends with ".", and
    its first text item comes right after the title/author block (no body paragraph of 40+ words
    before it on its page, author and affiliation blocks excepted). Returns the failed points."""
    problems = []
    n = len(ours.split())
    if not 80 <= n <= 400:
        problems.append(f"length {n} words")
    if not ours.rstrip().endswith("."):
        problems.append("no final period")
    norm = lambda t: re.sub(r"\s+", " ", _glyph_names(t or "")).strip().lower()
    head = norm(ours)[:40]
    try:
        doc = load_docling(OUT / pid)
    except Exception:
        return problems + ["docling.json not readable"]
    items = []
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        prov = (getattr(item, "prov", None) or [None])[0]
        if text is not None and prov is not None:
            items.append((_label(item), prov.page_no, text))
    start = next((i for i, (lab, pg, tx) in enumerate(items) if head and lab in BODY_LABELS
                  and norm(tx)[:40] == head), None)
    if start is None:
        return problems + ["start item not found"]
    page = items[start][1]
    before = [tx for lab, pg, tx in items[:start] if lab in BODY_LABELS and pg == page
              and len(tx.split()) >= 40 and not AUTHOR_BLOCK_RE.search(tx)]
    if before:
        problems.append("body text before it")
    return problems


def check_abstracts(rows):
    """structure.json abstracts against OpenAlex: recall (OpenAlex words in ours), precision (our
    words in OpenAlex) and length ratio (our words / OpenAlex words). Flags recall < 80%,
    precision < 80%, length ratio > 1.5 or < 0.6; an OpenAlex abstract under 50 words counts as
    missing here; without a usable one, the form check applies; an empty abstract is always
    flagged; a paper whose abstract_review mark matches the abstract's hash is skipped.
    Writes ingest/review/abstract_check.html for the flagged papers."""
    import base64, html, io, statistics
    oa = _load_oa_abstracts()
    report, flagged = [], []
    for r in rows:
        pid = r["paper_id"]
        d = OUT / pid
        if r.get("in_scope") != "yes" or r.get("docling") != "ok" or not (d / "structure.json").exists():
            continue
        st = json.loads((d / "structure.json").read_text())
        ours, src = st.get("abstract", ""), st.get("abstract_source", "none")
        mark = (r.get("abstract_review") or "").strip()
        if ours.strip() and mark.split(":")[0] in ("ok", "limit") and mark.split(":", 1)[-1] == _abstract_hash(ours):
            continue
        oa_text = oa.get(pid)
        if oa_text and len(oa_text.split()) < 50:      # a cover blurb is not an abstract
            oa_text = None
        ow, uw = (_words(oa_text) if oa_text else set()), _words(ours)
        m = None
        if ow:
            m = {"recall": len(uw & ow) / len(ow), "precision": len(uw & ow) / len(uw) if uw else 0.0,
                 "ratio": len(ours.split()) / max(1, len(oa_text.split()))}
        reasons = []
        if not ours.strip():
            reasons.append("empty abstract")
        elif m is None:
            reasons += _abstract_form_problems(pid, ours)
        else:
            if m["recall"] < 0.8:
                reasons.append(f"recall {m['recall']:.0%}")
            if m["precision"] < 0.8:
                reasons.append(f"precision {m['precision']:.0%}")
            if m["ratio"] > 1.5 or m["ratio"] < 0.6:
                reasons.append(f"length ratio {m['ratio']:.2f}")
        report.append((pid, src, len(ours.split()), m, "; ".join(reasons)))
        if reasons:
            flagged.append((pid, src, ours, oa_text, m, "; ".join(reasons)))
    fmt = lambda m, k: "  n/a" if m is None else (f"{m[k]:5.0%}" if k != "ratio" else f"{m[k]:5.2f}")
    print(f"{'paper_id':34s} {'source':15s} words recall  prec  ratio  flag")
    for pid, src, n, m, flag in report:
        print(f"{pid:34s} {src:15s} {n:5d} {fmt(m, 'recall')} {fmt(m, 'precision')} {fmt(m, 'ratio')}  {flag}")
    from collections import Counter
    print("sources:", dict(Counter(x[1] for x in report)))
    ms = [x[3] for x in report if x[3] is not None]
    if ms:
        for k in ("recall", "precision", "ratio"):
            v = [m[k] for m in ms]
            f = (lambda x: f"{x:.2f}") if k == "ratio" else (lambda x: f"{x:.0%}")
            print(f"{k} ({len(v)} papers with an OpenAlex abstract): min {f(min(v))}, median {f(statistics.median(v))}, max {f(max(v))}")
    print(f"flagged: {len(flagged)}")
    try:
        import pypdfium2
    except ImportError:
        pypdfium2 = None
    parts = []
    for pid, src, ours, oa_text, m, flag in flagged:
        imgs = ""
        if pypdfium2 is not None:
            try:
                pdoc = pypdfium2.PdfDocument(str(RAW / f"{pid}.pdf"))
                for pno in range(min(2, len(pdoc))):
                    buf = io.BytesIO()
                    pdoc[pno].render(scale=90 / 72).to_pil().save(buf, format="PNG", optimize=True)
                    imgs += f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="page {pno + 1}">'
            except Exception as e:
                imgs = f"<p>page render failed: {html.escape(str(e))}</p>"
        parts.append(f"""<section><h2>{html.escape(pid)} <small>{html.escape(flag)}</small></h2>
<div class="cols"><div><h3>Ours ({html.escape(src)}, {len(ours.split())} words)</h3><p>{html.escape(ours) or '<i>empty</i>'}</p></div>
<div><h3>OpenAlex{'' if m is None else f" (recall {m['recall']:.0%}, precision {m['precision']:.0%}, length ratio {m['ratio']:.2f})"}</h3><p>{html.escape(oa_text) if oa_text else '<i>none</i>'}</p></div></div>
<div class="pages">{imgs}</div></section>""")
    out = HERE / "review" / "abstract_check.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Abstract check</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1400px;margin:0 auto;padding:16px;color:#222;background:#fff}}
.cols{{display:flex;gap:24px}} .cols>div{{flex:1}} p{{font-size:0.9em}} h2 small{{color:#a00;font-weight:normal;font-size:0.7em}}
.pages img{{max-width:48%;border:1px solid #ccc;margin:4px}} section{{border-top:1px solid #ccc;margin-top:2em;padding-top:1em}}</style></head>
<body><h1>Abstract check: {len(flagged)} flagged of {len(report)} papers</h1>
<p>Flag = recall (OpenAlex words in ours) below 80%, precision (our words in OpenAlex) below 80%, length ratio (our words / OpenAlex words) above 1.5 or below 0.6; without a usable OpenAlex abstract (none, or under 50 words): 80-400 words, final period, right after the title/author block. An empty abstract is always flagged. Papers whose manifest abstract_review mark (ok:hash / limit:hash) matches the current abstract are skipped. Pages 1-2 rendered at 90 dpi.</p>
{''.join(parts)}</body></html>""")
    print(f"-> {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main(sys.argv[1:])
