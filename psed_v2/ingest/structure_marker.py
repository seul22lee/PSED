#!/usr/bin/env python3
"""Structure from Marker's output, in the schema of Docling's structure.json.

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/structure_marker.py <paper_id> [...] | --all

Reads ingest/marker/<paper_id>/ (blocks.json, the markdown, the images) and, for the abstract rules
only, corpus/openalex_abstracts.json and the PDF (pdfplumber, the OCR test of the fallback). No
Marker run, no Docling file. Writes, per paper:

    marker/<paper_id>/structure.json   {n_pages, sections[headings], n_pictures, n_tables,
                                        captions[{kind, number, caption, images|table+bbox, page}],
                                        equations[{page, bbox, number, latex}],
                                        abstract, abstract_source}
    marker/<paper_id>/document.md      Marker's markdown without running heads, footers and stamps
    marker/<paper_id>/marker.md        the markdown as Marker wrote it (renamed on the first run and
                                        read from then on, so the script can be rerun)

Captions, as in parse_docling.py: a block whose text starts with Fig./Figure/Scheme/Table + number
(letter prefix allowed) is a caption if Marker labels it Caption, or the number is followed by ".",
":" or "|", or it is a Table caption whose number is followed by a capitalised word; Text blocks
count too (Marker labels some captions Text). A caption continues with the Text block directly
below it in the same column (horizontal overlap, gap of at most 4 pt), stopping at a blank gap,
the next caption, a heading, a figure or a table. Binding: Marker's FigureGroup / PictureGroup
blocks bind a caption to its figure (a group that holds only captions binds nothing); tables ignore
Marker's TableGroup (it pairs neighbouring captions and tables wrongly) and use parse_docling.py's
table rule only. Pictures and captions outside a group follow parse_docling.py's position rules:
a picture goes to the next figure/scheme caption on its page whose horizontal span overlaps it,
else the previous figure caption on the page, else the next one, else it stays unnumbered; a table
goes to the nearest unused table caption on the same page; one caption per kind+number (a caption in a
group with content wins, then one with punctuation after the number, then the first). Tables are the Table block's HTML as a github-style markdown table (tabulate, as Docling); the <th>
rows at the top are merged into one header line per column, joined with " / " (parse_docling.py's
multi-row header rule); the markdown is built without tabulate's number parsing, so trailing zeros
stay (0.10, 8.0). Each table entry also gets a crop (table_<P-1>_<K>.png: the caption band above,
the table, 30 pt below, scale 3) and a rule check, "check": "ok" | "flag" with "check_reasons":
(a) the numeric tokens of the PDF text layer inside the table box (sign, decimals, exponents;
superscripts read by font size) against the delivered markdown (rowspan/colspan repeats counted
once), plus the count of ±; (b) letters of the layer that the table lacks (LaTeX, Greek, sub- and
superscripts normalised, Greek look-alike capitals mapped); (c) structure: header colspans against
the body's columns, an empty trailing header cell, an empty column, a short last row, numbers just
below the box on the table's number columns; (d) fewer than 5 text-layer words in the box (scanned
or image table). No exception excuses a mismatch: footnotes or a hidden duplicate text layer inside
the box also raise a flag. On the 16 numbered tables of the 13 papers (page judgements of
2026-10-12): 5 wrong tables flagged, 0 missed, 3 right tables flagged (footnotes inside the box, an
unmapped minus glyph, the MDPI hidden text layer). A flagged table is for the vision-model review at
extract time; nothing here reads the crop.
Equations are the Equation blocks' <math> content (LaTeX), with the number Marker kept in it, plus
short standalone blocks (ChemicalBlock, Text, TextInlineMath of 25 words or fewer) that hold a
reaction arrow (→ or \\rightarrow); such a ChemicalBlock is not counted as a picture.
Images: the Figure/Picture/Diagram crops Marker saved, _page_<P-1>_<Type>_<K>.jpeg; a Figure,
Picture, Diagram or ChemicalBlock without a file (Marker saves none for some types) is cropped from
the PDF page by its bbox with pypdfium2 at the picture scale (3), as parse_docling.py crops tables:
crop_page_<P-1>_<Type>_<K>.png.

The caption regex and the abstract rules are copied from parse_docling.py (2026-10-12 version), not
imported, so the two stages do not drift together by accident. Abstract: heading / inline
"Abstract:" paragraph, else the OpenAlex match on pages 1-2, else the widest item on page 1, else
the longest paragraph before the first body heading, else none; if the abstract's items have no
PDF text layer under them and recall against OpenAlex is below 80%, the OpenAlex text is used
("openalex"). Running lines (10 words or fewer, identical on 3+ pages, 4+ letters) are dropped
from document.md only.
"""
import csv
import html as html_mod
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"
MANIFEST = CORPUS / "manifest.csv"
RAW = CORPUS / "raw"
MARKER = HERE / "marker"
OA_ABSTRACTS = CORPUS / "openalex_abstracts.json"

# ---- copied from parse_docling.py -----------------------------------------------------------------
CAPTION_RE = re.compile(r"\s*(Fig\.|FIG\.|Figure(?!s)|FIGURE(?!S)|Scheme(?!s)|SCHEME(?!S)|Table(?!s)|TABLE(?!S)|图|表)"
                        r"\s*([A-Z]?\d+|[IVXL]+)(?!\d)(\s*[.:|])?")
CAPWORD_RE = re.compile(r"\s+[A-Z][A-Za-z]*(?![A-Za-z])")
ABSTRACT_HEAD_RE = re.compile(r"\s*abstract\s*[:.]?\s*$", re.I)
ABSTRACT_INLINE_RE = re.compile(r"\s*abstract\s*[:.\-–—]\s*", re.I)
KEYWORDS_RE = re.compile(r"\s*(keywords?|key\s*words|■|graphical abstract|toc graphic)\b", re.I)
BODY_HEAD_RE = re.compile(r"\b(introduction|background|results|experimental|methods?|materials)\b", re.I)
WORD_RE = re.compile(r"[a-z0-9]{3,}")
BODY_LABELS = ("text", "paragraph")


def _caption_kind(word):
    w = word.lower()
    return "table" if w.startswith(("table", "表")) else "scheme" if w.startswith("scheme") else "figure"


def _words(text):
    return set(WORD_RE.findall((text or "").lower()))


def _load_oa_abstracts():
    """{paper_id: abstract text} from corpus/openalex_abstracts.json (written by --fetch-abstracts)."""
    try:
        data = json.loads(OA_ABSTRACTS.read_text())
    except (OSError, ValueError):
        return {}
    return {pid: (v or {}).get("abstract") for pid, v in data.get("papers", {}).items()}


def _abstract(seq, oa_text):
    """(abstract, source) from the text items; the rules of parse_docling.py, applied to Marker's
    items (label, page, width, text, n)."""
    is_body = lambda s: s["label"] in BODY_LABELS
    oa_words = _words(oa_text) if oa_text else set()
    def precision(s):
        w = _words(s["text"])
        return len(w & oa_words) / len(w) if w else 0.0

    def continuation(i, page):
        out, taken = [], 0
        for s in seq[i + 1:]:
            if s["page"] != page or s["label"] == "section_header" or KEYWORDS_RE.match(s["text"]):
                break
            if not is_body(s) or s["n"] < 8:
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


def _abstract_is_ocr(items, pdf, abstract):
    """True if every text item that makes up the abstract (8+ words, text found in it) has no PDF
    text layer under its box (Marker boxes are top-left PDF points, as pdfplumber's)."""
    try:
        import pdfplumber
    except ImportError:
        return False
    norm = lambda t: re.sub(r"\s+", " ", t).strip()
    target = norm(abstract)
    boxes = [(s["page"], s["bbox"]) for s in items
             if s["label"] in BODY_LABELS and s["n"] >= 8 and norm(s["text"])[:60] in target]
    if not boxes:
        return False
    try:
        with pdfplumber.open(str(pdf)) as pl:
            for page_no, (l, t, r, b) in boxes:
                page = pl.pages[page_no - 1]
                x0 = page.bbox[0]
                if any(l + x0 - 2 <= c["x0"] <= r + x0 + 2 and t - 2 <= c["top"] <= b + 2 for c in page.chars):
                    return False
    except Exception:
        return False
    return True
# ---- end of the copied rules ----------------------------------------------------------------------

LABELS = {"Text": "text", "SectionHeader": "section_header", "Caption": "caption", "Footnote": "footnote",
          "PageHeader": "page_header", "PageFooter": "page_footer", "Equation": "formula", "Table": "table",
          "Figure": "picture", "Picture": "picture", "Diagram": "picture", "ChemicalBlock": "picture",
          "ListGroup": "list", "Bibliography": "bibliography", "TextInlineMath": "text"}
GROUPS = ("FigureGroup", "PictureGroup", "TableGroup")
IMAGE_TYPES = ("Figure", "Picture", "Diagram", "ChemicalBlock")
TAG_RE = re.compile(r"<[^>]+>")
INLINE_TAG_RE = re.compile(r"</?(sup|sub|i|b|em|strong|math[^>]*|p|span[^>]*|br\s*/?)>")
MATH_RE = re.compile(r"<math[^>]*>(.*?)</math>", re.S)


def _text(html):
    """Text of a block's html: inline tags removed without a space, other tags as a space."""
    t = INLINE_TAG_RE.sub("", html or "")
    t = TAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", html_mod.unescape(t)).strip()


def _flatten(tree):
    """Items in document order: type, id, page, bbox [l, t, r, b], html, text, n, label, group
    (the id of the enclosing Figure/Picture/Table group, or None)."""
    items = []
    def walk(block, group):
        bt = block["block_type"]
        if bt in GROUPS:
            for c in block.get("children") or []:
                walk(c, block["id"])
            return
        if bt == "Page":
            for c in block.get("children") or []:
                walk(c, None)
            return
        text = _text(block.get("html", ""))
        items.append({"type": bt, "id": block["id"], "page": block.get("page"), "bbox": block.get("bbox"),
                      "html": block.get("html", ""), "text": text, "n": len(text.split()),
                      "label": LABELS.get(bt, bt.lower()), "group": group,
                      "width": abs(block["bbox"][2] - block["bbox"][0]) if block.get("bbox") else 0.0})
        for c in block.get("children") or []:     # ListGroup etc.: children are part of the block
            if c.get("block_type") in GROUPS or c.get("block_type") in IMAGE_TYPES or c.get("block_type") == "Caption":
                walk(c, group)
    for page in tree.get("children") or []:
        walk(page, None)
    return items


_PAGE_CACHE = {}


def _image_file(d, item, pdf=None):
    """Marker's crop for the block, else a crop from the PDF page by the block's bbox (scale 3)."""
    k = item['id'].rsplit('/', 1)[1]
    name = f"_page_{item['page'] - 1}_{item['type']}_{k}.jpeg"
    if (d / name).exists():
        return name
    crop = f"crop_page_{item['page'] - 1}_{item['type']}_{k}.png"
    if (d / crop).exists():
        return crop
    if pdf is None or not item.get("bbox"):
        return ""
    try:
        import pypdfium2
        key = (str(pdf), item["page"])
        if key not in _PAGE_CACHE:
            _PAGE_CACHE[key] = pypdfium2.PdfDocument(str(pdf))[item["page"] - 1].render(scale=3).to_pil()
        im = _PAGE_CACHE[key]
        l, t, r, b = item["bbox"]
        box = (max(0, int(l * 3)), max(0, int(t * 3)), min(im.width, int(r * 3) + 1), min(im.height, int(b * 3) + 1))
        if box[2] <= box[0] or box[3] <= box[1]:
            return ""
        im.crop(box).save(d / crop)
        return crop
    except Exception as e:
        print(f"  crop failed for {item['id']} ({e.__class__.__name__}: {e})", flush=True)
        return ""


def _table_markdown(html):
    """Marker's <table> html as a github-style markdown table (first row as header, as Docling)."""
    from html.parser import HTMLParser
    from tabulate import tabulate
    rows, row, cell, span, rspan, th_rows, row_th = [], None, None, 1, 1, [], False
    pending = {}                       # column -> (rows left, text) for cells spanning several rows
    def place(r, text, cspan, rsp):
        """Put a cell into row r at the first free column (columns held by a rowspan are filled)."""
        j = len(r)
        while j in pending:
            n, t = pending[j]; r.append(t); pending[j] = (n - 1, t) if n > 1 else None
            if pending[j] is None: del pending[j]
            j += 1
        for k in range(cspan):
            r.append(text)
            if rsp > 1: pending[j + k] = (rsp - 1, text)
    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            nonlocal row, cell, span, rspan, row_th
            if tag == "tr":
                row = []; row_th = False
            elif tag in ("td", "th"):
                a = dict(attrs); cell = []; span = int(a.get("colspan") or 1); rspan = int(a.get("rowspan") or 1); row_th = row_th or tag == "th"
        def handle_endtag(self, tag):
            nonlocal row, cell
            if tag in ("td", "th") and cell is not None and row is not None:
                t = re.sub(r"\s+", " ", html_mod.unescape("".join(cell))).strip().replace("|", "&#124;")
                place(row, t, span, rspan); cell = None
            elif tag == "tr" and row is not None:
                j = len(row)
                while j in pending:                          # trailing columns held by a rowspan
                    n, t = pending[j]; row.append(t); pending[j] = (n - 1, t) if n > 1 else None
                    if pending[j] is None: del pending[j]
                    j += 1
                rows.append(row); th_rows.append(row_th); row = None
        def handle_data(self, data):
            if cell is not None:
                cell.append(data)
    P().feed(INLINE_TAG_RE.sub("", re.sub(r"<sup>", "^", html or "")))   # superscripts kept as ^, e.g. 10^14
    th_rows = [t for r, t in zip(rows, th_rows) if r]
    rows = [r for r in rows if r]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    # header rows (the <th> rows at the top) merged into one line per column, joined with " / ",
    # repeated identical parts skipped (parse_docling.py's multi-row header rule)
    n_hdr = 0
    while n_hdr < len(th_rows) and th_rows[n_hdr]:
        n_hdr += 1
    n_hdr = max(1, min(n_hdr, len(rows) - 1))
    header = []
    for j in range(width):
        parts = []
        for r in range(n_hdr):
            t = rows[r][j].strip()
            if t and t not in parts:
                parts.append(t)
        header.append(" / ".join(parts))
    return tabulate(rows[n_hdr:], headers=header, tablefmt="github", disable_numparse=True)   # keeps 0.10, 8.0


def _equation(item):
    m = MATH_RE.search(item["html"] or "")
    latex = html_mod.unescape(m.group(1)).strip() if m else _text(item["html"])
    num = re.search(r"\\tag\{\s*([A-Za-z]?\d+[a-z]?)\s*\}\s*$|\(\s*([A-Za-z]?\d+[a-z]?)\s*\)\s*$", latex)
    return {"page": item["page"], "bbox": item["bbox"], "number": (num.group(1) or num.group(2)) if num else None,
            "latex": latex}


def _running_lines(items):
    pages = {}
    for s in items:
        t = s["text"]
        if t and len(t.split()) <= 10 and len(re.findall(r"[A-Za-z]", t)) >= 4:
            pages.setdefault(t, set()).add(s["page"])
    return {t for t, p in pages.items() if len(p) >= 3}


def _drop_running(md, running):
    out, dropped = [], {}
    for line in md.split("\n"):
        core = re.sub(r"\s+", " ", html_mod.unescape(INLINE_TAG_RE.sub("", re.sub(r"^(#{1,6}\s+|[-*]\s+|>\s+)", "", line.strip()))))
        if core in running:
            dropped[core] = dropped.get(core, 0) + 1
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)), dropped


def _span(item):
    return (item["bbox"][0], item["bbox"][2]) if item.get("bbox") else None


def _overlap(a, b):
    return a is not None and b is not None and a[0] < b[1] and b[0] < a[1]


# ---- table checks ------------------------------------------------------------------------------
GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
         "theta": "θ", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ",
         "tau": "τ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ",
         "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω"}
NUM_TOKEN_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
LOOKALIKE = str.maketrans("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ", "ABEZHIKMNOPTYX")


def _norm_cell_text(t):
    """Cell or layer text in one form: Greek commands as letters, \\text{} unwrapped, ^{} and _{} as ^ and _,
    other LaTeX commands removed, minus signs and µ unified, NFKC."""
    import unicodedata
    t = t.replace("&#124;", "|")
    t = re.sub(r"\\(" + "|".join(GREEK) + r")(?![a-zA-Z])", lambda m: GREEK[m.group(1)], t)
    t = re.sub(r"\\(text|mathrm|mathit|mathbf|textbf)\{([^}]*)\}", r"\2", t)
    t = t.replace("\\times", "×").replace("\\pm", "±").replace("\\cdot", "·")
    t = re.sub(r"\^\{([^}]*)\}", r"^\1", t)
    t = re.sub(r"_\{([^}]*)\}", r"_\1", t)
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    return unicodedata.normalize("NFKC", t.replace("−", "-").replace("–", "-").replace("µ", "μ"))


def _num_tokens(t):
    return NUM_TOKEN_RE.findall(re.sub(r"[\^_]", " ", t))


def _letter_counts(t):
    from collections import Counter
    return Counter(ch for ch in re.sub(r"[\^_]", "", t).translate(LOOKALIKE) if ch.isalpha())


def _layer_lines(page, box):
    """Lines of the PDF text layer inside box (pdfplumber page), '^' before a superscript run (a char
    smaller than the line's font and raised); unmapped glyphs as '?'. Returns (lines, word count)."""
    l, t, r, b = box
    chars = [c for c in page.chars if c["x0"] >= l - 3 and c["x1"] <= r + 3 and c["top"] >= t - 3
             and c["bottom"] <= b + 6 and c["text"].strip()]
    if not chars:
        return [], 0
    for c in chars:
        if c["text"].startswith("(cid:"):
            c["text"] = "?"
    size0 = sorted(c["size"] for c in chars)[len(chars) // 2]
    lines = []
    for c in sorted([c for c in chars if c["size"] >= 0.85 * size0], key=lambda c: c["bottom"]):
        if lines and abs(lines[-1][0] - c["bottom"]) <= 2.5:
            lines[-1][1].append(c)
        else:
            lines.append([c["bottom"], [c]])
    for c in chars:
        if c["size"] < 0.85 * size0 and lines:
            k = min(range(len(lines)), key=lambda i: abs(lines[i][0] - c["bottom"] - 2))
            if abs(lines[k][0] - c["bottom"]) <= 7:
                lines[k][1].append(c)
    out, nwords = [], 0
    for base_bottom, cs in lines:
        cs.sort(key=lambda c: c["x0"])
        txt, prev, sup = "", None, False
        for c in cs:
            small = c["size"] < 0.85 * size0 and c["bottom"] < base_bottom - 1
            if prev is not None and c["x0"] - prev["x1"] > 1.5:
                txt += " "; sup = False; nwords += 1
            if small and not sup:
                txt += "^"; sup = True
            elif not small and sup:
                txt += " "; sup = False
            txt += c["text"]; prev = c
        out.append(txt); nwords += 1
    return [_norm_cell_text(x) for x in out], nwords


def _md_cells(md):
    return [[c.strip() for c in l.strip("|").split("|")] for l in md.split("\n")
            if l.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", l)]


def _html_cells(html):
    """[(tag, colspan, rowspan, text)] per row of a Marker table html, sup/sub as ^ and _."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html or "", re.S):
        row = []
        for tag, attrs, inner in re.findall(r"<(t[dh])([^>]*)>(.*?)</t[dh]>", tr, re.S):
            cs = int((re.search(r'colspan="(\d+)"', attrs) or [0, "1"])[1])
            rs = int((re.search(r'rowspan="(\d+)"', attrs) or [0, "1"])[1])
            text = re.sub(r"<[^>]+>", "", re.sub(r"<sup>", "^", re.sub(r"<sub>", "_", inner))).strip()
            row.append((tag, cs, rs, html_mod.unescape(text)))
        rows.append(row)
    return rows


def _table_check(entry, html, page):
    """Rule check of one table entry against the PDF text layer (pdfplumber page); returns (status, reasons)."""
    from collections import Counter
    reasons = []
    box = entry["bbox"]
    lines, nwords = _layer_lines(page, box)
    cells = _md_cells(entry["table"])
    if nwords < 5:
        reasons.append("no text layer in the table box (scanned or image table)")
    else:
        ltext = " ".join(lines)
        ttext = _norm_cell_text(" ".join(c for r in cells for c in r))
        repeats = Counter()
        for row in _html_cells(html):
            for tag, cs, rs, text in row:
                k = (cs - 1) if tag == "th" else (rs * cs - 1)       # the header merge collapses a header rowspan
                if k > 0 and text:
                    repeats[_norm_cell_text(text)] += k
        ln, tn = Counter(_num_tokens(ltext)), Counter(_num_tokens(ttext))
        ll, tl = _letter_counts(ltext), _letter_counts(ttext)
        for text, k in repeats.items():
            for tok in _num_tokens(text):
                tn[tok] -= min(k, tn[tok])
            for ch, n in _letter_counts(text).items():
                tl[ch] -= min(k * n, tl[ch])
        miss, extra = sorted((ln - tn).elements()), sorted((tn - ln).elements())
        if miss or extra:
            reasons.append(f"numbers: in the text layer only {miss[:12]}, in the table only {extra[:12]}")
        if ltext.count("±") != ttext.count("±"):
            reasons.append(f"± count: text layer {ltext.count('±')}, table {ttext.count('±')}")
        dl = "".join(sorted((ll - tl).elements()))
        if dl:
            reasons.append(f"letters in the text layer missing from the table: {dl[:40]}")
    if cells:
        width = max(len(r) for r in cells)
        body = cells[1:]
        empty = [j for j in range(width) if all(j >= len(r) or not r[j] for r in cells)]
        if empty:
            reasons.append(f"empty column(s) {empty}")
        if cells[0] and not cells[0][-1].strip():
            reasons.append("empty trailing header cell")
        if len(body) >= 3:
            ne = [sum(1 for c in r if c) for r in body]
            if ne[-1] < max(ne) - 1 and ne[-1] < ne[-2]:
                reasons.append(f"short last row ({ne[-1]} filled cells)")
    hrows = _html_cells(html)
    head = [r for r in hrows if r and all(tag == "th" for tag, _, _, _ in r)]
    bodyr = [r for r in hrows if r and not all(tag == "th" for tag, _, _, _ in r)]
    if head and bodyr:
        hspan = max(sum(cs for _, cs, _, _ in r) for r in head)
        bspan = max(sum(cs for _, cs, _, _ in r) for r in bodyr)
        if hspan != bspan:
            reasons.append(f"header colspans sum to {hspan}, body rows have {bspan} columns")
    if nwords >= 5:
        l, t, r, b = box
        words = page.extract_words()
        isnum = lambda w: NUM_TOKEN_RE.fullmatch(w["text"].replace("−", "-")) is not None
        inside = [w for w in words if w["x0"] >= l - 3 and w["x1"] <= r + 3 and w["top"] >= t - 3 and w["bottom"] <= b + 3 and isnum(w)]
        below = [w for w in words if w["x0"] >= l - 3 and w["x1"] <= r + 3 and b + 1 < w["top"] <= b + 16 and isnum(w)]
        cols = [(w["x0"] + w["x1"]) / 2 for w in inside]
        hits = [w["text"] for w in below if any(abs((w["x0"] + w["x1"]) / 2 - x) < 8 for x in cols)]
        if len(hits) >= 2:
            reasons.append(f"numbers just below the box on the table's columns: {hits[:6]}")
    return ("flag" if reasons else "ok"), reasons


def _table_crop(d, pdf, entry, k):
    """Crop of the table with the caption band above it: table_<P-1>_<K>.png (scale 3)."""
    import pypdfium2
    name = f"table_{entry['page'] - 1}_{k}.png"
    try:
        key = (str(pdf), entry["page"])
        if key not in _PAGE_CACHE:
            _PAGE_CACHE[key] = pypdfium2.PdfDocument(str(pdf))[entry["page"] - 1].render(scale=3).to_pil()
        im = _PAGE_CACHE[key]
        l, t, r, b = entry["bbox"]
        im.crop((max(0, int((l - 8) * 3)), max(0, int((t - 55) * 3)), min(im.width, int((r + 8) * 3)), min(im.height, int((b + 30) * 3)))).save(d / name)
        return name
    except Exception as e:
        print(f"  table crop failed ({e.__class__.__name__}: {e})", flush=True)
        return ""


def structure(paper_id):
    d = MARKER / paper_id
    tree = json.loads((d / "blocks.json").read_text())
    items = _flatten(tree)
    pdf = RAW / f"{paper_id}.pdf"
    pos = {it["id"]: k for k, it in enumerate(items)}

    # captions: candidates with kind and number; one kept per kind+number (the first)
    cands = []
    for it in items:
        if it["type"] in IMAGE_TYPES or it["type"] == "Table":
            continue
        m = CAPTION_RE.match(it["text"])
        labelled = it["type"] == "Caption"
        if m is None:
            if labelled:
                cands.append({"item": it, "kind": None, "number": None, "labelled": True, "punct": False})
            continue
        kind = _caption_kind(m.group(1))
        table_cap = kind == "table" and CAPWORD_RE.match(it["text"], m.end()) is not None
        if labelled or m.group(3) or table_cap:
            cands.append({"item": it, "kind": kind, "number": m.group(2), "labelled": labelled, "punct": bool(m.group(3))})
    # caption continuation: the Text block directly below, same column, gap <= 14 pt; stops at a
    # blank gap, the next caption, a heading, a figure or a table
    cand_ids = {c["item"]["id"] for c in cands}
    for c in cands:
        it = c["item"]
        if not it.get("bbox"):
            continue
        k = pos[it["id"]]; last = it
        while k + 1 < len(items):
            nxt = items[k + 1]
            if (nxt["type"] != "Text" or nxt["id"] in cand_ids or nxt["page"] != it["page"] or not nxt.get("bbox")
                    or CAPTION_RE.match(nxt["text"]) or nxt["label"] == "section_header"):
                break
            l1, t1, r1, b1 = last["bbox"]; l2, t2, r2, b2 = nxt["bbox"]
            overlap = min(r1, r2) - max(l1, l2)
            if overlap < 0.5 * min(r1 - l1, r2 - l2) or t2 - b1 > 4:
                break
            c["text"] = (c.get("text") or it["text"]) + " " + nxt["text"]
            last = nxt; k += 1
    for c in cands:
        c["text"] = c.get("text") or c["item"]["text"]

    # groups: the caption(s) and the picture/table children of each Figure/Picture/Table group
    groups = {}
    for it in items:
        if it["group"]:
            groups.setdefault(it["group"], []).append(it)
    has_content = {gid: any(m["type"] in IMAGE_TYPES or m["type"] == "Table" for m in members)
                   for gid, members in groups.items()}
    # one caption per kind+number: in a group with a picture or table first, then the number
    # followed by ".", ":" or "|", then Marker's Caption label (as parse_docling.py), then the first
    keep = {}
    rank = lambda c: (bool(c["item"]["group"] and has_content.get(c["item"]["group"])), c["punct"], c["labelled"])
    for i, c in enumerate(cands):
        if c["number"] is None:
            continue
        k = (c["kind"], c["number"])
        if k not in keep or rank(c) > rank(cands[keep[k]]):
            keep[k] = i
    kept = set(keep.values())
    entries, used_caps, used_items = [], set(), set()
    def entry_for(c, kind):
        e = {"kind": kind, "number": c["number"], "caption": c["text"], "page": c["item"]["page"]}
        if kind == "table":
            e["table"], e["bbox"] = "", None
        else:
            e["images"] = []
        return e
    for gid, members in groups.items():
        caps = [i for i, c in enumerate(cands) if c["item"]["group"] == gid]
        pics = [m for m in members if m["type"] in IMAGE_TYPES]
        tabs = [m for m in members if m["type"] == "Table"]
        kind = "table" if tabs and not pics else None
        cap = next((i for i in caps if i in kept), caps[0] if caps else None)
        if cap is None or (not pics and not tabs) or tabs:   # captions-only or table groups: position rules
            continue
        c = cands[cap]
        if c["number"] is None:
            kind = kind or (c["kind"] or "figure")
        else:
            kind = c["kind"]
        e = entry_for(c, kind)
        if kind == "table" and tabs:
            e["table"], e["bbox"] = _table_markdown(tabs[0]["html"]), tabs[0]["bbox"]
            used_items.update(m["id"] for m in tabs)
        for p in pics:
            img = _image_file(d, p, pdf)
            if img and kind != "table":
                e["images"].append(img)
            used_items.add(p["id"])
        if kind == "table" and pics and not tabs:          # a table drawn as an image
            e["images"] = [_image_file(d, p, pdf) for p in pics if _image_file(d, p, pdf)]
        if c["number"] is not None and cap not in kept:     # a repeated number: the first one holds it
            e["number"] = None
        entries.append(e); used_caps.update(caps)

    # loose captions, pictures and tables: parse_docling.py's position rules
    loose_caps = [i for i in kept if i not in used_caps]
    cap_entries = {}
    for i in sorted(loose_caps, key=lambda i: pos[cands[i]["item"]["id"]]):
        c = cands[i]; cap_entries[i] = entry_for(c, c["kind"]); entries.append(cap_entries[i])
    fig_caps = [i for i in loose_caps if cands[i]["kind"] != "table"]
    for it in items:
        if it["type"] not in IMAGE_TYPES or it["id"] in used_items:
            continue
        same = [i for i in fig_caps if cands[i]["item"]["page"] == it["page"]]
        after = [i for i in same if pos[cands[i]["item"]["id"]] > pos[it["id"]]]
        before = [i for i in same if pos[cands[i]["item"]["id"]] < pos[it["id"]]]
        target = next((i for i in after if _overlap(_span(cands[i]["item"]), _span(it))), None)
        if target is None and before:
            target = before[-1]
        if target is None and after:
            target = after[0]
        img = _image_file(d, it, pdf)
        if target is not None:
            if img:
                cap_entries[target]["images"].append(img)
        else:
            entries.append({"kind": "figure", "number": None, "caption": "", "images": [img] if img else [], "page": it["page"]})
    tab_caps = [i for i in loose_caps if cands[i]["kind"] == "table"]
    used_tc = set()
    for it in items:
        if it["type"] != "Table" or it["id"] in used_items:
            continue
        free = [(abs(pos[cands[i]["item"]["id"]] - pos[it["id"]]), pos[cands[i]["item"]["id"]] > pos[it["id"]], i)
                for i in tab_caps if i not in used_tc and cands[i]["item"]["page"] == it["page"]]
        if free:
            i = min(free)[2]; used_tc.add(i)
            cap_entries[i]["table"], cap_entries[i]["bbox"] = _table_markdown(it["html"]), it["bbox"]
        else:
            entries.append({"kind": "table", "number": None, "caption": "", "table": _table_markdown(it["html"]),
                            "bbox": it["bbox"], "page": it["page"]})

    def is_arrow_eq(it):
        return (it["type"] in ("ChemicalBlock", "Text", "TextInlineMath") and it["n"] <= 25
                and ("→" in it["text"] or "\\rightarrow" in (it["html"] or "")))
    equations = [_equation(it) for it in items if it["type"] == "Equation" or is_arrow_eq(it)]
    arrow_ids = {it["id"] for it in items if is_arrow_eq(it)}

    # abstract
    seq = [{"label": s["label"], "page": s["page"], "width": s["width"], "text": s["text"], "n": s["n"], "bbox": s["bbox"]}
           for s in items if s["type"] not in IMAGE_TYPES]
    oa_text = _load_oa_abstracts().get(paper_id)
    abstract, source = _abstract(seq, oa_text)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    if abstract and oa_text and _abstract_is_ocr(seq, RAW / f"{paper_id}.pdf", abstract):
        ow = _words(oa_text)
        if ow and len(_words(abstract) & ow) / len(ow) < 0.8:
            abstract, source = re.sub(r"\s+", " ", oa_text).strip(), "openalex"

    # tables: crop and rule check (see the module docstring)
    html_by_bbox = {tuple(it["bbox"]): (it["html"], it["id"]) for it in items if it["type"] == "Table" and it.get("bbox")}
    tabs = [e for e in entries if e["kind"] == "table" and e.get("bbox")]
    if tabs:
        import pdfplumber
        with pdfplumber.open(str(pdf)) as pl:
            for e in tabs:
                html, tid = html_by_bbox.get(tuple(e["bbox"]), ("", ""))
                e["check"], e["check_reasons"] = _table_check(e, html, pl.pages[e["page"] - 1])
                e["crop"] = _table_crop(d, pdf, e, tid.rsplit("/", 1)[-1] if tid else "x")

    # document.md without running lines; Marker's own markdown kept as marker.md
    raw = d / "marker.md"
    if not raw.exists():
        (d / "document.md").rename(raw)
    md, dropped = _drop_running(raw.read_text(), _running_lines(items))
    (d / "document.md").write_text(md)

    struct = {"n_pages": len(tree.get("children") or []),
              "sections": [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", md, re.M)],
              "n_pictures": sum(1 for it in items if it["type"] in IMAGE_TYPES and it["id"] not in arrow_ids),
              "n_tables": sum(1 for it in items if it["type"] == "Table"),
              "captions": entries, "equations": equations,
              "abstract": abstract, "abstract_source": source}
    (d / "structure.json").write_text(json.dumps(struct, indent=1, ensure_ascii=False))
    return struct, dropped


def main(argv):
    rows = list(csv.DictReader(MANIFEST.open(newline="", encoding="utf-8")))
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    if argv == ["--all"]:
        todo = [r["paper_id"] for r in rows if r.get("marker") == "ok"]
    else:
        missing = [a for a in argv if a not in by_id]
        if missing or not argv:
            sys.exit(f"usage: structure_marker.py <paper_id> [...] | --all  (unknown: {missing})")
        todo = argv
    for pid in todo:
        if not (MARKER / pid / "blocks.json").exists():
            print(f"[structure_marker] {pid}: no blocks.json, skipped")
            continue
        st, dropped = structure(pid)
        n_num = sum(1 for e in st["captions"] if e["number"] is not None)
        n_flag = sum(1 for e in st["captions"] if e["kind"] == "table" and e.get("check") == "flag")
        print(f"[structure_marker] {pid}: {st['n_pictures']} pictures, {st['n_tables']} tables ({n_flag} flagged), "
              f"{n_num} numbered captions, {len(st['equations'])} equations, abstract {st['abstract_source']} "
              f"({len(st['abstract'].split())} w), {sum(dropped.values())} running lines dropped")


if __name__ == "__main__":
    main(sys.argv[1:])
