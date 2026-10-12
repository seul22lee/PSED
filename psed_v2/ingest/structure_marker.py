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

Caption binding: Marker's FigureGroup / PictureGroup / TableGroup blocks bind a caption to its
figure or table (a group that holds only captions binds nothing; Marker sometimes leaves the Table
block as a sibling). Pictures and captions outside a group follow parse_docling.py's position rules:
a picture goes to the next figure/scheme caption on its page whose horizontal span overlaps it,
else the previous figure caption on the page, else the next one, else it stays unnumbered; a table
goes to the nearest unused table caption on the same page; one caption per kind+number (a caption in a
group with content wins, then one with punctuation after the number, then the first). Tables are the Table block's HTML as a github-style markdown table (tabulate, as Docling).
Equations are the Equation blocks' <math> content (LaTeX), with the number Marker kept in it.
Images: the Figure/Picture/Diagram crops Marker saved, _page_<P-1>_<Type>_<K>.jpeg.

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


def _image_file(d, item):
    name = f"_page_{item['page'] - 1}_{item['type']}_{item['id'].rsplit('/', 1)[1]}.jpeg"
    return name if (d / name).exists() else ""


def _table_markdown(html):
    """Marker's <table> html as a github-style markdown table (first row as header, as Docling)."""
    from html.parser import HTMLParser
    from tabulate import tabulate
    rows, row, cell, span = [], None, None, 1
    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            nonlocal row, cell, span
            if tag == "tr":
                row = []
            elif tag in ("td", "th"):
                cell = []; span = int(dict(attrs).get("colspan") or 1)
        def handle_endtag(self, tag):
            nonlocal row, cell
            if tag in ("td", "th") and cell is not None and row is not None:
                t = re.sub(r"\s+", " ", html_mod.unescape("".join(cell))).strip().replace("|", "&#124;")
                row.extend([t] * span); cell = None
            elif tag == "tr" and row is not None:
                rows.append(row); row = None
        def handle_data(self, data):
            if cell is not None:
                cell.append(data)
    P().feed(INLINE_TAG_RE.sub("", html or ""))
    rows = [r for r in rows if r]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    try:
        return tabulate(rows[1:], headers=rows[0], tablefmt="github")
    except ValueError:
        return tabulate(rows[1:], headers=rows[0], tablefmt="github", disable_numparse=True)


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


def structure(paper_id):
    d = MARKER / paper_id
    tree = json.loads((d / "blocks.json").read_text())
    items = _flatten(tree)
    pos = {it["id"]: k for k, it in enumerate(items)}

    # captions: candidates with kind and number; one kept per kind+number (the first)
    cands = []
    for it in items:
        if it["type"] != "Caption":
            continue
        m = CAPTION_RE.match(it["text"])
        kind = _caption_kind(m.group(1)) if m else None
        cands.append({"item": it, "kind": kind, "number": m.group(2) if m else None})
    # groups: the caption(s) and the picture/table children of each Figure/Picture/Table group
    groups = {}
    for it in items:
        if it["group"]:
            groups.setdefault(it["group"], []).append(it)
    has_content = {gid: any(m["type"] in IMAGE_TYPES or m["type"] == "Table" for m in members)
                   for gid, members in groups.items()}
    # one caption per kind+number: in a group with a picture or table first, then the number
    # followed by ".", ":" or "|" (as parse_docling.py), then the first in document order
    keep = {}
    rank = lambda c: (bool(c["item"]["group"] and has_content.get(c["item"]["group"])),
                      bool(CAPTION_RE.match(c["item"]["text"]).group(3)))
    for i, c in enumerate(cands):
        if c["number"] is None:
            continue
        k = (c["kind"], c["number"])
        if k not in keep or rank(c) > rank(cands[keep[k]]):
            keep[k] = i
    kept = set(keep.values())
    entries, used_caps, used_items = [], set(), set()
    def entry_for(c, kind):
        e = {"kind": kind, "number": c["number"], "caption": c["item"]["text"], "page": c["item"]["page"]}
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
        if cap is None or (not pics and not tabs):      # a group of captions only: position rules
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
            img = _image_file(d, p)
            if img and kind != "table":
                e["images"].append(img)
            used_items.add(p["id"])
        if kind == "table" and pics and not tabs:          # a table drawn as an image
            e["images"] = [_image_file(d, p) for p in pics if _image_file(d, p)]
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
        img = _image_file(d, it)
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

    equations = [_equation(it) for it in items if it["type"] == "Equation"]

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

    # document.md without running lines; Marker's own markdown kept as marker.md
    raw = d / "marker.md"
    if not raw.exists():
        (d / "document.md").rename(raw)
    md, dropped = _drop_running(raw.read_text(), _running_lines(items))
    (d / "document.md").write_text(md)

    struct = {"n_pages": len(tree.get("children") or []),
              "sections": [h.strip() for h in re.findall(r"^#{1,4}\s+(.+)$", md, re.M)],
              "n_pictures": sum(1 for it in items if it["type"] in IMAGE_TYPES),
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
        print(f"[structure_marker] {pid}: {st['n_pictures']} pictures, {st['n_tables']} tables, "
              f"{n_num} numbered captions, {len(st['equations'])} equations, abstract {st['abstract_source']} "
              f"({len(st['abstract'].split())} w), {sum(dropped.values())} running lines dropped")


if __name__ == "__main__":
    main(sys.argv[1:])
