#!/usr/bin/env python3
"""Countermeasures applied to document.md from the body check (body_check.py), on born-digital pages only.
Called by merge.py after the first body check; the check is run again on the repaired text. Each change is
recorded in structure.json under body_repairs (page, kind, from, to, the sentence or line).

R1  number replaced from the text layer: in one output paragraph the numbers of the text layer that are missing and
    the numbers of the output that are absent from the layer are paired one to one, closest pairs first (a pair
    differs by at most two characters and at most one in length: a-MoS3,0 / a-MoS3.0; 3d_3/2 / 3d5/2; ^33 / ^53;
    g/cm^3 / g/cm^-3); a layer token glued to a minus sign is left alone (an exponent next to a citation, Å^-1 55
    read as 155); the output token is replaced by the layer token inside the markdown (markup between its
    characters kept).
R2  dropped line restored: a text-layer line of a Text, Caption or TextInlineMath block that no output paragraph contains (body flag "line not
    found in the output"), with at least 8 words, no undecoded glyph, at least 70 % of its words of 4+ letters in
    the document's vocabulary and no reaction arrow, is inserted as a paragraph after the paragraph the previous
    unit matched, marked "[restored from the text layer]".
A page is born-digital when its text layer comes from embedded fonts (no OCR font such as GlyphLessFont) and no
image covers the whole page (a scanned page carries an OCR text layer, which is not trusted).
"""
import re
from collections import defaultdict

WORD4_RE = re.compile(r"[a-zA-Z]{4,}")


def _same_shape(a, b):
    """The two tokens differ only in digits or punctuation (a decimal point, a comma, a sign), never in letters: the
    common prefix and suffix are stripped and what remains on either side holds digits and punctuation only."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    ma, mb = a[i:len(a) - j], b[i:len(b) - j]
    return all(re.fullmatch(r"[\d.,\-]*", m) for m in (ma, mb)) and any(ch.isdigit() for ch in ma + mb + "0")


def _edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


MARKUP = r"(?:\s|[_^{}\\$*]|<[^<>]{1,12}>)*"           # markup that may sit between a token's characters


def _tolerant(tok):
    """Regex for a token as it may appear in the markdown: markup (LaTeX, html tags) allowed between its characters."""
    return MARKUP.join(re.escape(ch) for ch in tok)


def _born_digital(pl, pno):
    """A page whose text layer comes from embedded fonts, not from OCR (Tesseract's GlyphLessFont, "OCR" fonts) and
    that is not one full-page image with text on top."""
    page = pl.pages[pno - 1]
    fonts = {c["fontname"] for c in page.chars}
    if not fonts or any("glyphless" in f.lower() or "ocr" in f.lower() for f in fonts):
        return False
    area = page.width * page.height
    return not any((im["x1"] - im["x0"]) * (im["bottom"] - im["top"]) >= 0.95 * area for im in page.images)


def repair(md_text, body, pdf_path):
    import pdfplumber
    pl = pdfplumber.open(str(pdf_path))
    vocab = {w.lower() for w in WORD4_RE.findall(md_text)}
    repairs = []
    chunks = re.split(r"(\n\s*\n)", md_text)                 # text chunks and the blank-line separators between them
    texts = chunks[0::2]
    # R1: one missing + one extra number in the same output sentence
    groups = defaultdict(lambda: {"miss": [], "extra": []})
    for f in body["body_flags"]:
        if "paragraph" not in f:
            continue
        if f["kind"].startswith("number of the text layer missing"):
            groups[(f["page"], f["paragraph"])]["miss"].append(f)
        elif f["kind"].startswith("number of the output paragraph absent"):
            groups[(f["page"], f["paragraph"])]["extra"].append(f)
    born = {}
    for (pno, hit), g in groups.items():
        if not g["miss"] or not g["extra"] or hit >= len(texts):
            continue
        cands = defaultdict(set)                              # missing token -> extra tokens it could stand for
        for fm in g["miss"]:
            a = fm["number"]
            if re.search(r"-" + re.escape(a) + r"(?!\d)", fm.get("layer_context", "")) and not a.startswith("-"):
                continue                                      # the layer token hangs on a minus sign (155 for -1 55)
            for fe in g["extra"]:
                b = fe["number"]
                if (a != b and any(ch.isdigit() for ch in a) and any(ch.isdigit() for ch in b) and _edit_distance(a, b) <= 2
                        and abs(len(a) - len(b)) <= 1 and _same_shape(a, b)):
                    cands[a].add(b)
        # unambiguous pairs only: a missing token with one candidate that no other missing token claims
        claims = defaultdict(set)
        for a, bs in cands.items():
            for b in bs:
                claims[b].add(a)
        unique = [(a, next(iter(bs))) for a, bs in cands.items() if len(bs) == 1 and len(claims[next(iter(bs))]) == 1]
        pairs = []
        for a, b in unique:                                   # the same pair repeated (two -3 written 3) is applied as often
            n = min(sum(1 for fm in g["miss"] if fm["number"] == a), sum(1 for fe in g["extra"] if fe["number"] == b))
            pairs += [(a, b)] * max(1, n)
        if not pairs:
            continue
        if pno not in born:
            born[pno] = _born_digital(pl, pno)
        if not born[pno]:
            continue
        for a, b in pairs:
            pat = re.compile(r"(?<![\w.])" + _tolerant(b) + r"(?![\w.])")
            where = [(j, list(pat.finditer(texts[j]))) for j in g["miss"][0].get("paragraphs", [hit]) if j < len(texts)]
            where = [(j, ms) for j, ms in where if ms]
            if len(where) != 1:                               # the token must sit in exactly one paragraph of the run
                continue
            hit, ms = where[0]
            m = ms[0]                                         # the first occurrence not yet replaced
            raw = m.group(0)
            pieces = re.split(r"(" + MARKUP[:-1] + "+)", raw)    # characters of the token and the markup between them
            plain = "".join(x for x in pieces if not re.fullmatch(MARKUP, x) or x == "")
            plain = re.sub(MARKUP, "", raw)
            if len(plain) == len(a):                          # same length: keep the markup, swap the characters
                out, k, i = [], 0, 0
                while i < len(raw):
                    mm = re.match(MARKUP[:-1] + "+", raw[i:])
                    if mm and mm.group(0):
                        out.append(mm.group(0)); i += len(mm.group(0))
                    else:
                        out.append(a[k]); k += 1; i += 1
                new = "".join(out)
            else:
                new = a
            texts[hit] = texts[hit][:m.start()] + new + texts[hit][m.end():]
            repairs.append({"page": pno, "kind": "number replaced from the text layer", "from": raw, "to": new, "sentence": g["miss"][0]["output_sentence"][:200]})
    # R2: dropped lines restored
    inserts = defaultdict(list)
    for f in body["body_flags"]:
        if f["kind"] != "line not found in the output" or f.get("block") not in ("Text", "Caption", "TextInlineMath") or f.get("undecoded"):
            continue
        line = f["layer_line"]
        w4 = WORD4_RE.findall(line)
        if f.get("words", 0) < 8 or not w4 or sum(1 for w in w4 if w.lower() in vocab) < 0.7 * len(w4) or "→" in line:
            continue
        pno = f["page"]
        if pno not in born:
            born[pno] = _born_digital(pl, pno)
        if not born[pno]:
            continue
        inserts[f.get("after_paragraph", 0)].append((pno, line))
    for idx in sorted(inserts, reverse=True):
        block = " ".join(l for _, l in inserts[idx])
        texts[idx] = texts[idx].rstrip() + "\n\n" + block + " [restored from the text layer]"
        for pno, l in inserts[idx]:
            repairs.append({"page": pno, "kind": "dropped line restored from the text layer", "from": "", "to": l, "sentence": ""})
    pl.close()
    chunks[0::2] = texts
    return "".join(chunks), repairs
