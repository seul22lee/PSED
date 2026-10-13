#!/usr/bin/env python3
"""Body-number check: numbers in the decoded PDF text layer of the body against numbers in final document.md,
matched by paragraph. Called by merge.py (after line_numbers.py, before and after body_repair.py); writes nothing.

Text layer: pdfplumber characters, decoded per embedded font with glyph_codes.json; a unit with a glyph that has no
decoding is not checkable and is counted with its reason. Characters outside the page area are dropped, a character
drawn twice at a slightly different size on one baseline is read once, a line printed twice on a page is read once
(the MDPI duplicate layer). Characters are read block by block inside Marker's text blocks (Text, SectionHeader,
Caption, ListItem, TextInlineMath, Footnote), lines by the baseline of the normal-size characters; small characters
(citation and affiliation numbers, exponents) join the line whose baseline and size span they overlap, superscripts
marked '^'; a few same-size characters without a word on their own baseline (LaTeX sub- and superscripts) join the
nearest line; stacked sub- and superscripts are read subscript first (O_2^+); a word space is a gap above 13 % of
the line's font size. The lines of an Equation box join the text unit before it as weak lines. Characters outside
every block are read as segments split at gaps of 20 pt or more. Excluded, with counts: PageHeader / PageFooter /
Figure / Picture / Diagram / Table / Form / Handwriting / Reference / Code boxes; everything from a References,
Acknowledgements, Funding, Author contributions, Conflicts, Associated content, Supporting information or Data
availability heading on (on the layer side, or when a unit matches an output paragraph after the first such heading
in the second half of document.md); author/affiliation blocks (keywords, addresses, dates), author lines (names with
affiliation markers, pages 1-2); furniture ("Published by", "Cite as", doi, URL, ORCID, licence, copyright, article
id: the line is cut there or dropped); running lines (10 words or fewer, identical on 3+ pages, page headers
counted); units of fewer than 4 words; segments outside the blocks that hold only a number; the page abstract when
the abstract comes from OpenAlex (its unmatched lines on pages 1-2). On the output side, URLs, DOIs, received /
accepted / published dates, ORCID ids, "Citation:" lines and markdown table rows are removed before the comparison.
Not checkable, with counts: rotated characters, undecoded glyphs (font and code listed in not_checkable_reasons),
units of fewer than 3 words, garbled lines (two lines drawn over each other: fewer than 30 % of their words occur in
the output, or two long unknown words), output sentences the layer does not cover (70 % of their words of 4+
letters), output paragraphs a not-checkable unit also matches, paragraphs whose equation lines hold an undecoded
glyph. A weak line (no word of 4+ letters, or a reaction line) is kept for the extra direction only.
What stays not checkable at the line level is also written as a flag of kind "not checkable" (reason, the line's text,
numbers, box and crop; for a unit with an undecoded glyph one flag with the glyph line and the unit's line count), so
that the flag review sees these lines as it sees a not-checkable table: one flag per unit with an undecoded glyph, per
garbled line, per unit too short to locate, and per equation or weak line with an undecoded glyph (it blocks the extra
direction of its paragraph). These flags are counted apart ("not-checkable flags"), not among "flags".

Tokens: both sides are normalised as the table check does (structure_marker._norm_cell_text); a subscript joins its
base (H2O), a superscript stands alone (10^12 -> 10, 12), a number with a unit or a lowercase word glued to it
counts as the number (514nm, 30μm, 4seconds), the diameter sign is dropped (Φ165), a comma run is split in the plain
variant (90,120 is a list) and joined in the thousands variant, Greek letters count as letters of a run. A pure
number (a run of digits with an optional decimal point, signed after a space or bracket, not after ° or %) is compared
as a multiset in both variants; a run that mixes letters and digits (H2S, MoS3.0, 40045TRS, kBN0) by occurrence in
the other side's text with spaces and markers removed. Display math and equation-like inline math ($...$ holding =,
\\frac, \\sqrt, \\sum, \\int, \\approx, \\equiv) are the equation check's domain: their numbers are not required
in the layer (a placeholder keeps the sentence intact).

Matching: a unit goes to the document.md paragraph sharing the most word 3-grams (sub/superscript markers removed
on both sides; at least a fifth of the unit's 3-grams, 2 at least, 1 for a unit under 6 tokens; ties go to the first
paragraph after the last match), together with the contiguous run of candidate paragraphs around it; overlapping
runs are compared as one group, a line printed twice counts once. A unit that matches nothing is "unmatched" and
its lines with a number are flagged "line not found in the output" (the flag carries the paragraph before it for
body_repair.py). Per group the numbers are compared both ways: a number of the text layer missing from the output
paragraphs is one flag, unless the group gathers several units or repeated text (a cover page, a duplicate layer)
and the number occurs in the paragraphs or within 3 paragraphs (a count mismatch), or the group's layer text is
repeated (presence only); a number of the output absent from the text layer is one flag only for output sentences
the layer lines cover, with the lines of the neighbouring units counting for the layer side (a paragraph that
crosses a column or page break). Each flag has page, kind, number, the text-layer line, the output sentence, the
numbers on each side, the line's box and crop, and the paragraph run (raw chunk indices) for body_repair.py.
"""
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import structure_marker as SM

# ablation switch for the comparison rules (tests only): BODY_CHECK_DISABLE=stacked,equations,neighbours,dup_lines
DISABLED = set(filter(None, os.environ.get("BODY_CHECK_DISABLE", "").split(",")))

TEXT_BLOCKS = ("Text", "SectionHeader", "Caption", "ListItem", "TextInlineMath", "Footnote")
EXCL_BLOCKS = ("PageHeader", "PageFooter", "Figure", "Picture", "Diagram", "Table", "Form", "Handwriting", "Reference", "Code", "Equation")
WORD4_RE = re.compile(r"[a-zA-Z]{4,}")
STOP_HEAD_RE = re.compile(r"^\W*(references?|notes and references|bibliography|literature cited|references and notes|"
                          r"acknowledg\w*|funding(\s+sources?)?|author contributions?|conflicts? of interest|"
                          r"associated content|supporting information|data availability( statement)?)\W*$", re.I)
AFFIL_RE = re.compile(r"universit|department|institute|laborator|faculty|school|@|orcid|correspond|e-?mail|"
                      r"\b(received|accepted|published|revised)( on| online)?:? ?\d|^\s*\d{1,2} [A-Z][a-z]+ \d{4}[;.]?\s*$|authors? (contribut|declare)|"
                      r"supplementary (material|information)|p\.?o\.? box|\bbox \d|\bstreet\b|\bavenue\b|\broad\b|"
                      r"\b(the netherlands|germany|belgium|finland|france|japan|korea|china|usa|united states|united kingdom|"
                      r"switzerland|sweden|italy|spain|ireland|india)\b|^\s*citation:", re.I)
OUT_FURN_RE = re.compile(r"https?://\S+|\b10\.\d{4,}/\S+|\b(received|accepted|published(\s+online)?):?\s*\d{1,2}\s+\w+\s+\d{4}|"
                         r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b|^\s*citation:[^\n]*", re.I | re.M)
FURN_RE = re.compile(r"published by|copyright|©|licen[cs]e|creative commons|doi\.org|downloaded|cite (this|as)|this journal is|\bdoi:|^\s*[a-z]+\d{8,}\s*$|"
                     r"https?://|\d{4}-\d{4}-\d{4}-\d{3}[\dX]|contact information|^\s*10\.\d{4,}/\S+\s*$", re.I)
TOK_RE = re.compile(r"[a-z0-9]{2,}")
RUN_RE = re.compile(r"[A-Za-z0-9\u0370-\u03ff]+(?:(?<=\d)[.,](?=\d)[A-Za-z0-9\u0370-\u03ff]+)*")   # . or , joins digits only (3.0, 1,2, 10,000); Greek letters count as letters
AUTHOR_RE = re.compile(r"[A-Z][a-z'’-]+,?\s*\^?\d[\d,]*(?![\d,]*\s*[a-z%°])")   # "Lastname^1,2", "Lastname,^1", "Pei1,2,4": a name with its affiliation marker
FORMULA_LINE_RE = re.compile(r"[→⇌⇄↔]|\\(rightarrow|leftrightarrow|rightleftharpoons)")


def _tokens(t):
    """(pure numbers, mixed runs) of a normalised text. A pure number is a run of digits with an optional decimal
    point that stands on its own, signed when the sign follows a space or a bracket; a mixed run is an alphanumeric
    run that contains both letters and digits (H2S, MoS3.0, 40045TRS, kBN0). Subscript markers are dropped first
    (H2 and H_2 give the same run) and superscripts become tokens of their own (10^12 -> 10, 12; cm^2 -> cm, 2);
    pure numbers are compared as multisets, mixed runs by occurrence in the other side's text with spaces removed
    (Marker writes H_2 S for H2S)."""
    t = re.sub(r"([_^]) +", r"\1", t)                 # a marker followed by a space (nested braces) : _ 2.2 -> _2.2
    t = re.sub(r"(?<![\w.^])([-+]) +(?=\d)", r"\1", t)   # a sign followed by a space: + 0.23 -> +0.23
    t = re.sub(r"\^([-+]?\d+)(?=[A-Za-z\u0370-\u03ff])", r"^\1 ", t)   # a superscript number before a letter: ^1Δg -> 1, Δg
    t = re.sub(r"(?<![\w])[Φ⌀](?=\d)", "", t)          # a diameter sign before a number: Φ165 -> 165
    t = re.sub(r"(?<=\d)x(?=10(?:\^|\s|$))", " × ", t)   # a multiplication sign typed as the letter x: 1x10^-3
    t = t.replace("_", "").replace("^", " ")           # subscripts join their base (H2O), superscripts stand alone
    pure, mixed = [], []
    for m in RUN_RE.finditer(t):
        run = m.group(0)
        if not any(ch.isdigit() for ch in run):
            continue
        m_unit = re.fullmatch(r"(\d+(?:[.,]\d+)*)([A-Za-z\u0370-\u03ff]{1,3}|[a-z]{4,})", run)
        if m_unit:                                          # 514nm, 30μm, 2s, 100mW, 1st, 4seconds: a number with a
            run = m_unit.group(1)                           # unit or a word glued to it
        if run.replace(".", "").replace(",", "").isdigit():
            if "," in run and "." not in run:
                pure.extend(run.split(","))             # a citation list 14,15 or a list "90,120"; the thousands
                continue                                # reading comes from the _join_thousands variant
            run = run.replace(",", "")
            sign = t[m.start() - 1] if m.start() > 0 else ""
            prev2 = t[m.start() - 2] if m.start() > 1 else " "
            if sign in "-+" and (prev2 in " ([" or m.start() == 1):
                run = sign + run
            pure.append(run)
        else:
            mixed.append(run)
    return pure, mixed


def _nums(t):
    pure, mixed = _tokens(t)
    return pure + mixed


def _nospace(t):
    return re.sub(r"[\s^_]", "", t)


def _md_paragraphs(md):
    """Paragraphs of document.md as (normalised text, original text), markdown markers and images removed."""
    out = []
    for raw_i, para in enumerate(re.split(r"\n\s*\n", md)):
        p = "\n".join(ln for ln in para.split("\n") if not ln.lstrip().startswith("|"))   # table rows: the table check
        p = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", p)
        p = re.sub(r"</?[A-Za-z][^<>]*>", lambda m: "^" if m.group(0) == "<sup>" else "_" if m.group(0) == "<sub>" else " ", p)   # tags only, not "< 10"
        p = re.sub(r"^\s{0,3}#{1,6}\s*", "", p, flags=re.M)
        p = re.sub(r"[*`]+", "", p)
        def _math(m):                                              # display math and equation-like inline math are the
            s = m.group(0)                                         # equation check's domain: their numbers are not
            if s.startswith("$$") or re.search(r"=|\\frac|\\sqrt|\\sum|\\int|\\approx|\\equiv", s):   # required in the layer
                return " ∎ "
            return s
        nomath = re.sub(r"\$\$[^$]*\$\$|\$[^$\n]*\$", _math, p)
        nomath = re.sub(r"\$\$?", " ", nomath)
        nomath = re.sub(r"\s+", " ", nomath).strip()
        p = re.sub(r"\$\$?", " ", p)
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            out.append((SM._norm_cell_text(p), p, nomath, raw_i))
    return out


def _lines_of(chars):
    """[(text, top, bottom, x0, x1, unknown)] from characters: lines by the baseline of the normal-size characters,
    small characters (super- and subscripts, citation numbers) attached to the nearest line, decoded, superscripts
    marked with '^'."""
    if not chars:
        return []
    size0 = sorted(c["size"] for c in chars)[len(chars) // 2]
    lines = []
    for c in sorted([c for c in chars if c["size"] >= 0.85 * size0], key=lambda c: (c["bottom"], c["x0"])):
        if lines and abs(lines[-1][0] - c["bottom"]) <= 2.5:
            lines[-1][1].append(c)
        else:
            lines.append([c["bottom"], [c]])
    def fragment(l):        # a few characters without a word on their own baseline: same-size sub- or superscripts
        return len(l[1]) <= 12 and not re.search(r"[A-Za-z]{3}", "".join(c["text"] for c in l[1]))   # (LaTeX manuscripts)
    main = [l for l in lines if not fragment(l)]
    if main:
        for l in [l for l in lines if fragment(l)]:
            k = min(range(len(main)), key=lambda i: abs(main[i][0] - l[0]))
            if abs(main[k][0] - l[0]) <= 7:
                main[k][1].extend(l[1])
            else:
                main.append(l)
        lines = sorted(main, key=lambda l: l[0])
    if not lines:
        lines = [[max(c["bottom"] for c in chars), list(chars)]]
    else:
        for c in chars:
            if c["size"] < 0.85 * size0:
                cands_ = [i for i in range(len(lines)) if c["top"] < lines[i][0] + 0.35 * size0 and c["bottom"] > lines[i][0] - 1.3 * size0]
                k = min(cands_ or range(len(lines)), key=lambda i: abs(lines[i][0] - c["bottom"] - 2))
                if cands_ and abs(lines[k][0] - c["bottom"]) <= 7:
                    lines[k][1].append(c)
                else:
                    lines.append([c["bottom"], [c]])
        lines.sort(key=lambda l: l[0])
    out = []
    for bottom, cs in lines:
        cs.sort(key=lambda c: c["x0"] if "stacked" in DISABLED else (round(c["x0"] * 2) / 2, -c["bottom"]))   # stacked sub/superscript: subscript first
        sizes = sorted(c["size"] for c in cs)
        base = sizes[len(sizes) // 2]
        unknown = Counter()
        txt, prev, sup = "", None, False
        for c in cs:
            t, unk = SM._decode_char(c)
            if unk:
                unknown[unk] += 1
            if t == "":
                continue
            small = c["size"] < 0.85 * base and c["bottom"] < bottom - 1
            gap = c["x0"] - prev["x1"] if prev is not None else 0.0
            if prev is not None and gap > max(0.6, 0.13 * base) and not (small and sup and gap <= 4):   # a word space is ~1.5 pt at 9 pt, in-word gaps ~0
                txt += " "
                sup = False
            if small and not sup:
                txt += "^"
                sup = True
            elif not small and sup:
                txt += " "
                sup = False
            txt += t
            prev = c
        out.append((SM._norm_cell_text(txt), min(c["top"] for c in cs), bottom, cs[0]["x0"], cs[-1]["x1"], unknown))
    return out


def _segments(chars):
    """Characters outside every block: lines by baseline, split at horizontal gaps of 20 pt or more."""
    segs = []
    for line in _lines_of_raw(chars):
        cur = []
        for c in sorted(line, key=lambda c: c["x0"]):
            if cur and c["x0"] - cur[-1]["x1"] >= 20:
                segs.append(cur)
                cur = []
            cur.append(c)
        if cur:
            segs.append(cur)
    return [l for s in segs if s for l in _lines_of(s)]


def _lines_of_raw(chars):
    """Baseline groups; a group of a few characters without a word (same-size sub- or superscripts) joins the
    nearest group within 7 pt, as in _lines_of."""
    lines = []
    for c in sorted(chars, key=lambda c: (c["bottom"], c["x0"])):
        if lines and abs(lines[-1][0] - c["bottom"]) <= 2.5:
            lines[-1][1].append(c)
        else:
            lines.append([c["bottom"], [c]])
    def fragment(l):
        return len(l[1]) <= 12 and not re.search(r"[A-Za-z]{3}", "".join(c["text"] for c in l[1]))
    main = [l for l in lines if not fragment(l)]
    if main:
        for l in [l for l in lines if fragment(l)]:
            k = min(range(len(main)), key=lambda i: abs(main[i][0] - l[0]))
            if abs(main[k][0] - l[0]) <= 7:
                main[k][1].extend(l[1])
            else:
                main.append(l)
        lines = sorted(main, key=lambda l: l[0])
    return [cs for _, cs in lines]


def _inside(c, b):
    cx, cy = (c["x0"] + c["x1"]) / 2, (c["top"] + c["bottom"]) / 2
    return b[0] - 2 <= cx <= b[2] + 2 and b[1] - 2 <= cy <= b[3] + 2


def check_body(pdf_path, md_text, tree, crop_dir, crop_prefix="body", openalex_abstract=None):
    """-> {"body_flags": [...], "body_check": {...}}. Crops go to crop_dir/<crop_prefix>_p<P>_<k>.png (none when
    crop_dir is None)."""
    import pdfplumber
    import pypdfium2
    blocks_by_page = defaultdict(list)
    def walk(b, pno):
        pno = b.get("page", pno)
        if b.get("bbox") and b.get("block_type") and b["block_type"] not in ("Page", "Document"):
            blocks_by_page[pno].append((b["block_type"], b["bbox"]))
        for c in b.get("children") or []:
            walk(c, pno)
    walk(tree, None)
    md_text = OUT_FURN_RE.sub(" ", md_text)
    paras = _md_paragraphs(md_text)
    vocab = set(TOK_RE.findall(md_text.lower()))
    oa_words = {w.lower() for w in WORD4_RE.findall(openalex_abstract or "")}
    grams = defaultdict(set)
    for i, (pn, _, _, _) in enumerate(paras):
        toks = TOK_RE.findall(re.sub(r"[_^]", "", pn).lower())
        for k in range(len(toks) - 2):
            grams[(toks[k], toks[k + 1], toks[k + 2])].add(i)
    counts, not_checkable, flags = Counter(), Counter(), []
    pl = pdfplumber.open(str(pdf_path))
    pdoc = pypdfium2.PdfDocument(str(pdf_path))
    # units: (page, block type, bbox, lines) in reading order; segments outside the blocks as units of their own
    units = []
    header_lines = []
    n_pages = len(pl.pages)
    for pno, page in enumerate(pl.pages, 1):
        chars = [c for c in page.chars if c["text"].strip() and c.get("upright", True)]
        n0 = len(chars)                            # characters drawn outside the page area are not visible (MDPI's
        bx0, btop, bx1, bbot = page.bbox           # hidden copy at the top edge); the page box may not start at (0, 0)
        chars = [c for c in chars if c["top"] >= btop and c["bottom"] <= bbot and c["x1"] >= bx0 and c["x0"] <= bx1]
        counts["characters outside the page area dropped (a hidden duplicate layer)"] += n0 - len(chars)   # hidden copy at the top edge)
        kept, seen = [], defaultdict(list)         # the same character drawn twice at a slightly different size within
        for c in sorted(chars, key=lambda c: c["x0"]):       # 6 pt on one baseline (MDPI's second copy) is read once
            b = round(c["bottom"])
            if any(abs(x - c["x0"]) <= 6 and abs(y - c["bottom"]) <= 1.0 and abs(s - c["size"]) >= 0.1
                   for bb in (b - 1, b, b + 1) for x, y, s in seen[(c["text"], bb)]):
                counts["duplicated text-layer characters read once"] += 1
                continue
            seen[(c["text"], b)].append((c["x0"], c["bottom"], c["size"]))
            kept.append(c)
        chars = kept
        rotated = sum(1 for c in page.chars if c["text"].strip() and not c.get("upright", True))
        if rotated:
            counts["not checkable: rotated text (characters)"] += rotated
        # Marker's boxes start at (0, 0); pdfplumber keeps the PDF's page box origin (a media box may start at -92)
        blocks = [(bt, [bb[0] + bx0, bb[1] + btop, bb[2] + bx0, bb[3] + btop]) for bt, bb in blocks_by_page.get(pno, [])]
        excl = [bb for bt, bb in blocks if bt in EXCL_BLOCKS]
        for bt, bb in blocks:
            if bt in ("PageHeader", "PageFooter"):
                for l in _lines_of([c for c in chars if _inside(c, bb)]):
                    header_lines.append((pno, l[0]))
        used = [False] * len(chars)
        page_seen = set()
        def once(lines):                           # a line printed twice on the page (a hidden duplicate layer) once
            out = []
            for l in lines:
                key = l[0].strip()[:40]
                if len(key) >= 20 and key in page_seen and "dup_lines" not in DISABLED:
                    counts["duplicated text-layer lines read once"] += 1
                    continue
                page_seen.add(key)
                out.append(l)
            return out
        last_text_unit = None
        for bt, bb in blocks:
            if bt not in TEXT_BLOCKS and (bt != "Equation" or "equations" in DISABLED):
                continue
            inside = [k for k, c in enumerate(chars) if not used[k] and _inside(c, bb)]
            for k in inside:
                used[k] = True
            if not inside:
                continue
            if bt == "Equation":                   # an equation Marker may keep inline: its numbers count as present
                if last_text_unit is not None:     # in the layer of the paragraph before it (extra direction only)
                    units[last_text_unit][4].extend(_lines_of([chars[k] for k in inside]))
                    counts["equation lines joined to the paragraph before them (extra direction only)"] += 1
                continue
            units.append([pno, bt, bb, once(_lines_of([chars[k] for k in inside])), []])
            last_text_unit = len(units) - 1
        rest = [c for k, c in enumerate(chars) if not used[k] and not any(_inside(c, bb) for bb in excl)]
        for seg in _segments(rest):
            units.append([pno, "outside", [seg[3], seg[1], seg[4], seg[2]], once([seg]), []])
    # units stay in Marker's reading order (the block tree); the segments outside the blocks follow their page
    line_pages = defaultdict(set)
    def rkey(s):
        return re.sub(r"\d+", "#", s.strip())[:30]
    for pno, bt, bb, lines, _ in units:
        for l in lines:
            line_pages[rkey(l[0])].add(pno)
    for pno, txt in header_lines:
        line_pages[rkey(txt)].add(pno)
    running = {k for k, ps in line_pages.items() if len(ps) >= 3 and len(k.split()) <= 10}
    rendered = {}
    def crop(pno, line, k):
        if crop_dir is None:
            return ""
        if pno not in rendered:
            rendered[pno] = pdoc[pno - 1].render(scale=2).to_pil()
        im = rendered[pno]
        box = (max(0, int((line[3] - 30) * 2)), max(0, int((line[1] - 14) * 2)), min(im.width, int((line[4] + 30) * 2)), min(im.height, int((line[2] + 14) * 2)))
        if box[2] <= box[0] or box[3] <= box[1]:                  # a line outside the page area: no crop
            return ""
        name = f"{crop_prefix}_p{pno}_{k}.png"
        im.crop(box).save(Path(crop_dir) / name)
        return name
    nc_seen = set()
    def nc_flag(pno, l, reason, bt, n_lines):
        """A flag of kind "not checkable" for a layer line (once per line)."""
        key = (pno, round(l[1]), round(l[3]), l[0][:40])
        if key in nc_seen:
            return
        nc_seen.add(key)
        k = len(flags)
        flags.append({"page": pno, "kind": "not checkable", "reason": reason, "layer_line": l[0], "output_sentence": "",
                      "layer_numbers": _nums(l[0]), "output_numbers": [], "crop": crop(pno, l, k), "bbox": [l[3], l[1], l[4], l[2]],
                      "lines": n_lines, "block": bt})
    stop_heads = [i for i, (pn, po, _, _) in enumerate(paras) if STOP_HEAD_RE.match(po.strip()) and len(po.split()) <= 4]
    ref_idx = next((i for i in stop_heads if i >= len(paras) * 0.5), None)   # the first stop heading in the second half
    last_best = 0                      # reading-order cursor for ties
    blocked = set()                    # output paragraphs a not-checkable unit matches: no extra direction for them
    assigned = defaultdict(list)       # paragraph index -> [(line, pno)]
    assigned_units = defaultdict(set)  # paragraph run -> unit indices
    assigned_weak = defaultdict(list)  # paragraph index -> [(weak line, pno)]
    stopped = False
    for u, (pno, bt, bb, lines, eq_lines) in enumerate(units):
        n0 = len(lines)
        lines = [l for l in lines if rkey(l[0]) not in running]
        counts["excluded: running line"] += n0 - len(lines)
        n_aff = sum(1 for l in lines if AFFIL_RE.search(l[0]))
        if n_aff and (len(lines) <= 3 or n_aff >= len(lines) / (3 if pno <= 2 else 2)):     # an author/affiliation block
            counts["excluded: author/affiliation/furniture line"] += len(lines)
            continue
        if pno <= 2:
            n0 = len(lines)
            lines = [l for l in lines if len(AUTHOR_RE.findall(l[0])) < 2]       # the authors come from the manifest
            counts["excluded: author line (names with affiliation markers)"] += n0 - len(lines)
            if not lines:
                continue
        kept = []
        for l in lines:
            m = FURN_RE.search(l[0])
            if m and m.start() >= 20:                                   # body text followed by furniture: keep the text
                kept.append((l[0][:m.start()],) + tuple(l[1:]))
            elif m:
                counts["excluded: author/affiliation/furniture line"] += 1
            else:
                kept.append(l)
        lines = kept
        weak = [l for l in lines if not WORD4_RE.search(l[0]) or (FORMULA_LINE_RE.search(l[0]) and len(WORD4_RE.findall(l[0])) < 6)]
        lines = [l for l in lines if l not in weak]
        weak = weak + eq_lines
        if not lines:
            counts["excluded: unit without a word of 4+ letters (formula, labels, numbers alone)"] += len(weak)
            continue
        # a weak line (no word of 4+ letters: a formula, a short last line "al.^36 ).") stays with its unit for the
        # extra direction only: its numbers count as present in the layer, but are not required in the output
        counts["weak lines (no word of 4+ letters or a reaction line): extra direction only"] += len(weak)
        text = " ".join(l[0] for l in lines)
        if STOP_HEAD_RE.match(text.strip()) and len(text.split()) <= 4 and pno >= n_pages / 2:   # not a cover page's "Reference"
            stopped = True
        if stopped:
            counts["excluded: after the references/acknowledgements heading"] += len(lines)
            continue
        counts["lines"] += len(lines)
        if len(text.split()) < 4:
            counts["excluded: fewer than 4 words"] += len(lines)
            continue
        garbled = [l for l in lines if (len(WORD4_RE.findall(l[0])) >= 3
                   and sum(1 for w in WORD4_RE.findall(l[0]) if w.lower() in vocab) < 0.3 * len(WORD4_RE.findall(l[0])))
                   or sum(1 for w in re.findall(r"[A-Za-z]{8,}", l[0]) if w.lower() not in vocab) >= 2]
        if garbled:                                   # two lines drawn over each other (MDPI's misplaced duplicate layer)
            counts["not checkable: garbled text-layer line (overlapping duplicate layer; fewer than 30 % of its words occur in the output)"] += len(garbled)
            for l in garbled:
                nc_flag(pno, l, "garbled text-layer line (overlapping duplicate layer; fewer than 30 % of its words occur in the output)", bt, 1)
            lines = [l for l in lines if l not in garbled]
            if not lines:
                continue
        unk = Counter()
        for l in lines:
            unk.update(l[5])
        toks = TOK_RE.findall(text.lower())
        cand = Counter()
        for k in range(len(toks) - 2):
            for i in grams.get((toks[k], toks[k + 1], toks[k + 2]), ()):
                cand[i] += 1
        if cand:                                       # the best paragraph; ties go to the first one after the last match
            n = max(cand.values())
            tied = sorted(i for i, c in cand.items() if c == n)
            best = next((i for i in tied if i >= last_best), tied[0])
        else:
            best, n = None, 0
        need = 1 if len(toks) < 6 else max(2, -(-(len(toks) - 2) // 5))   # a fifth of the unit's 3-grams (2 at least)
        if unk:
            glyphs = ", ".join(f"{fam} {code}" for (fam, code) in sorted(unk))
            not_checkable[glyphs] += len(lines)
            counts["not checkable: undecoded glyph"] += len(lines)
            if best is not None and n >= need:
                blocked.add(best)                 # its output paragraph is not checked in the extra direction either
            nc_flag(pno, next(l for l in lines if l[5]), f"undecoded glyph {glyphs}: the unit's {len(lines)} line(s) not checked", bt, len(lines))
            continue
        counts["checked"] += len(lines)
        if len(toks) < 3:
            counts["not checkable: unit too short to locate in the output (fewer than 3 words)"] += len(lines)
            nc_flag(pno, lines[0], f"unit too short to locate in the output (fewer than 3 words; {len(lines)} line(s))", bt, len(lines))
            continue
        if (best is None or n < need) and openalex_abstract and pno <= 2:
            w4 = {w.lower() for w in WORD4_RE.findall(text)}
            if w4 and len(w4 & oa_words) >= 0.6 * len(w4):        # the page abstract, replaced by the OpenAlex text
                counts["excluded: page abstract replaced by the OpenAlex abstract (abstract_source openalex)"] += len(lines)
                continue
        if best is None or n < need:
            counts["unmatched"] += len(lines)
            for l in lines:
                nums = _nums(l[0])
                if nums:
                    k = len(flags)
                    flags.append({"page": pno, "kind": "line not found in the output", "layer_line": l[0], "output_sentence": "",
                                  "layer_numbers": nums, "output_numbers": [], "crop": crop(pno, l, k), "bbox": [l[3], l[1], l[4], l[2]],
                                  "after_paragraph": paras[last_best][3] if paras else 0, "words": len(l[0].split()),
                                  "block": bt, "undecoded": bool(l[5])})
            continue
        if ref_idx is not None and best >= ref_idx and pno >= n_pages / 2:   # the unit matches a paragraph after the
            stopped = True                                   # References heading (and lies in the second half of the paper)
            counts["excluded: after the references/acknowledgements heading"] += len(lines)
            continue
        # a unit that spans several output paragraphs (Marker split the block, or a line straddles two paragraphs) is
        # compared with the contiguous run of candidate paragraphs around the best one
        strong_cands = {i for i, c in cand.items() if c >= need}
        lo = hi = best
        while lo - 1 in strong_cands:
            lo -= 1
        while hi + 1 in strong_cands:
            hi += 1
        key = tuple(range(lo, hi + 1))
        last_best = max(last_best, best)
        for l in lines:
            assigned[key].append((l, pno))
        for l in weak:
            assigned_weak[key].append((l, pno))
        assigned_units[key].add(u)
    def tokens(t):
        return Counter(_tokens(t)[0]), Counter(_tokens(SM._join_thousands(t))[0])
    parent = {}
    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for key in list(assigned) + list(assigned_weak):
        for j in key[1:]:
            parent[find(j)] = find(key[0])
    groups, groups_weak, groups_units = defaultdict(list), defaultdict(list), defaultdict(set)
    for key, ls in assigned.items():
        groups[find(key[0])].extend(ls)
    for key, ls in assigned_weak.items():
        groups_weak[find(key[0])].extend(ls)
    for key, us in assigned_units.items():
        groups_units[find(key[0])].update(us)
    members = defaultdict(set)
    for key in list(assigned) + list(assigned_weak):
        members[find(key[0])].update(key)
    for root, lines in groups.items():
        key = tuple(sorted(members[root]))
        assigned_weak_i = list(groups_weak.get(root, []))
        us = groups_units.get(root, set())             # a paragraph that crosses a column or page break, or that
        for v in sorted({v for u in us for v in (u - 1, u + 1)} - us):   # Marker split: the neighbouring units'
            if 0 <= v < len(units) and "neighbours" not in DISABLED:    # lines count for the extra direction
                assigned_weak_i.extend((l, units[v][0]) for l in units[v][3] + units[v][4])
        seen_text, uniq = set(), []
        for l, p_ in lines:                   # the same line printed twice (a title on a cover page) counts once
            if l[0] not in seen_text:
                seen_text.add(l[0]); uniq.append((l, p_))
        lines = uniq
        ptext = " ".join(paras[j][0] for j in key)
        porig = " ".join(paras[j][2] for j in key)       # without math spans: for the extra direction
        ltext = " ".join(l[0] for l, _ in lines)
        ltext_all = " ".join(l[0] for l, _ in lines + assigned_weak_i)
        la, lb = tokens(ltext)
        la_all, lb_all = tokens(ltext_all)
        pa, pb = tokens(ptext)
        miss = (la - pa) & (lb - pb)
        chunks = [l[0].strip()[:30] for l, _ in lines if len(l[0].strip()) >= 30]
        repeated = len(chunks) != len(set(chunks)) or any(c in l2[0] for c in chunks for l2, _ in lines if l2[0].strip()[:30] != c)
        near = " ".join(paras[j][0] for j in range(max(0, key[0] - 3), min(len(paras), key[-1] + 4)) if j not in key)
        na, nb = tokens(near)                                  # a number the paragraph has (fewer times than the layer)
        forgiven = Counter({k: v for k, v in miss.items() if (pa[k] + pb[k]) > 0 and (na[k] + nb[k]) > 0})
        if forgiven and (len(us) > 1 or repeated):             # and a paragraph within 3 also has, is a count mismatch
            miss = miss - forgiven                             # when the group gathers several units or repeated text
        if repeated:                                           # the same text twice in the layer (a cover page, a
            miss = Counter({k: 1 for k, v in miss.items() if (pa[k] + pb[k]) == 0})   # duplicate layer): presence only
        lns_all, pns = _nospace(ltext_all), _nospace(ptext)
        for tok in set(_tokens(ltext)[1]):
            if tok not in pns:
                miss[tok] += 1
        # the extra direction (numbers of the output absent from the layer) is checked per output sentence, and only
        # for sentences covered by the layer lines: a paragraph that spans a column or page break, or an excluded
        # block, is only partly covered, and the numbers of its uncovered sentences are not checkable here
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", porig) or [porig]
        lt = set(TOK_RE.findall(ltext_all.lower()))
        covered = []
        for s in sentences:
            sn = SM._norm_cell_text(s)
            st = [w for w in TOK_RE.findall(sn.lower()) if len(w) >= 4] or TOK_RE.findall(sn.lower())
            if not st or sum(1 for w in st if w in lt) / len(st) >= 0.7:
                covered.append(sn)
            elif _tokens(sn)[0] or _tokens(sn)[1]:
                counts["not checkable: output sentence not covered by the text layer (its numbers not compared)"] += 1
        if any(j in blocked for j in key):
            counts["not checkable: output paragraph also matched by a not-checkable unit (extra numbers not compared)"] += 1
            covered = []
        elif any(l[5] for l, _ in assigned_weak_i):
            counts["not checkable: paragraph with an equation or neighbour line holding an undecoded glyph (extra numbers not compared)"] += 1
            for l, p_ in assigned_weak_i:
                if l[5]:
                    nc_flag(p_, l, "undecoded glyph " + ", ".join(f"{fam} {code}" for (fam, code) in sorted(l[5])) + " in an equation or weak line: the output numbers of its paragraph are not compared with the layer", "Equation", 1)
            covered = []
        ctext = " ".join(covered)
        ca, cb = tokens(ctext)
        extra = (ca - la_all) & (cb - lb_all)
        if repeated:
            extra = Counter({k: 1 for k, v in extra.items() if (la_all[k] + lb_all[k]) == 0})
        for tok in set(_tokens(ctext)[1]):
            if tok not in lns_all:
                extra[tok] += 1
        def sent_nums(s):
            n = SM._norm_cell_text(s)
            return set(_nums(n)) | set(_nums(SM._join_thousands(n)))
        def sentence_like(line_text):
            lw = set(TOK_RE.findall(line_text.lower()))
            return max(sentences, key=lambda s: len(lw & set(TOK_RE.findall(s.lower()))))
        for tok in sorted(miss.elements()):
            line, pno = next(((l, p) for l, p in lines if tok in _nums(l[0]) or tok in _nums(SM._join_thousands(l[0]))), lines[0])
            s = sentence_like(line[0])
            k = len(flags)
            flags.append({"page": pno, "kind": "number of the text layer missing from the output paragraph", "number": tok,
                          "layer_line": line[0], "output_sentence": s[:400], "layer_numbers": _nums(line[0]),
                          "output_numbers": _nums(SM._norm_cell_text(s))[:30], "crop": crop(pno, line, k), "bbox": [line[3], line[1], line[4], line[2]],
                          "paragraph": paras[key[0]][3], "paragraphs": [paras[j][3] for j in key], "layer_context": line[0]})
        for tok in sorted(extra.elements()):
            s = next((s for s in sentences if tok in sent_nums(s)), sentences[0])
            line, pno = max(lines, key=lambda lp: len(set(TOK_RE.findall(lp[0][0].lower())) & set(TOK_RE.findall(s.lower()))))
            k = len(flags)
            flags.append({"page": pno, "kind": "number of the output paragraph absent from the text layer", "number": tok,
                          "layer_line": line[0], "output_sentence": s[:400], "layer_numbers": _nums(line[0]),
                          "output_numbers": _nums(SM._norm_cell_text(s))[:30], "crop": crop(pno, line, k), "bbox": [line[3], line[1], line[4], line[2]],
                          "paragraph": paras[key[0]][3], "paragraphs": [paras[j][3] for j in key]})
    pl.close()
    counts["flags"] = sum(1 for f in flags if f["kind"] != "not checkable")
    counts["not-checkable flags"] = sum(1 for f in flags if f["kind"] == "not checkable")
    return {"body_flags": flags,
            "body_check": {"counts": dict(counts), "not_checkable_reasons": dict(not_checkable),
                           "method": "decoded text layer (glyph_codes.json) read inside Marker's text blocks vs document.md paragraphs matched by word 3-grams; numbers compared both ways"}}
