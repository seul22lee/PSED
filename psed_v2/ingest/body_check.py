#!/usr/bin/env python3
"""Body-number check: numbers in the decoded PDF text layer of the body against numbers in final document.md,
matched by paragraph. Called by merge.py; writes nothing itself.

Text layer: pdfplumber characters, decoded per embedded font with glyph_codes.json (the table check's decoding);
a unit with a glyph that has no decoding is not checkable and is counted with its reason. Characters outside the
page area (a hidden duplicate layer) are dropped, a character drawn twice at a slightly different size on one
baseline is read once. The characters are read block by block inside Marker's text blocks (Text, SectionHeader,
Caption, ListItem, TextInlineMath, Footnote), lines by the baseline of the normal-size characters; small characters
(citation and affiliation numbers, exponents) join the nearest line, superscripts marked with '^'; a few same-size
characters without a word on their own baseline (LaTeX sub- and superscripts) join the nearest line; a word space
is a gap above 10 % of the font size. Characters outside every block (a line Marker dropped) are read as segments
split at gaps of 20 pt or more. Excluded, with counts: Marker's PageHeader / PageFooter / Figure / Picture /
Diagram / Table / Form / Handwriting / Reference / Code / Equation boxes; everything from a References,
Acknowledgements, Funding, Author contributions, Conflicts, Associated content, Supporting information or Data
availability heading on (on the text-layer side, or when a unit matches an output paragraph after the first such
heading in the second half of document.md); author/affiliation blocks and author lines (names with affiliation
markers, pages 1-2; the authors come from the manifest); furniture ("Published by", "Cite as", doi, licence,
copyright: the line is cut there, or dropped when it is only furniture); running lines (10 words or fewer,
identical on 3+ pages, page headers counted); units of fewer than 4 words; segments outside the blocks that hold
only a number (page and margin line numbers). Not checkable, with counts: rotated characters, undecoded glyphs,
units of fewer than 3 words (not locatable by word 3-grams), garbled lines (two lines drawn over each other: fewer
than 30 % of their words occur in the output), and output sentences the layer does not cover (see below). A weak
line (no word of 4+ letters, or a reaction line) is kept for the extra direction only.

Tokens: both sides are normalised as the table check does (structure_marker._norm_cell_text: LaTeX, sub- and
superscripts, Greek, minus and decimal glyphs; thousands separators compared both ways); a subscript joins its
base (H2O), a superscript stands alone (10^12 -> 10, 12), a number with a short unit glued to it counts as the
number (514nm). A pure number (a run of digits with an optional decimal point, signed after a space or bracket) is
compared as a multiset; a run that mixes letters and digits (H2S, MoS3.0, 40045TRS, kBN0) is compared by
occurrence in the other side's text with spaces and markers removed, so a changed digit inside a formula or a
model name is caught while Marker's spacing (H_2 S) is not a difference.

Matching: a unit goes to the document.md paragraph that shares the most word 3-grams with it (at least 2, or 1
for a unit of fewer than 6 tokens), together with the contiguous run of candidate paragraphs around it (a block
Marker split, a line that straddles two paragraphs); overlapping runs are compared as one group, a line printed
twice (a cover-page title) counts once. Per group the numbers are compared both ways: a number of the text layer
missing from the output paragraph is one body_flag; a number of the output absent from the text layer is one
body_flag only for output sentences the layer lines cover (70 % of their words of 4+ letters), the others are
counted as not checkable. Each flag has page, the text-layer line, the output sentence, the numbers on each side
and a crop of the line. An unmatched unit that holds a number is flagged as "line not found in the output" (a
dropped or rewritten line).
"""
import re
from collections import Counter, defaultdict
from pathlib import Path

import structure_marker as SM

TEXT_BLOCKS = ("Text", "SectionHeader", "Caption", "ListItem", "TextInlineMath", "Footnote")
EXCL_BLOCKS = ("PageHeader", "PageFooter", "Figure", "Picture", "Diagram", "Table", "Form", "Handwriting", "Reference", "Code", "Equation")
WORD4_RE = re.compile(r"[a-zA-Z]{4,}")
STOP_HEAD_RE = re.compile(r"^\W*(references?|notes and references|bibliography|literature cited|references and notes|"
                          r"acknowledg\w*|funding(\s+sources?)?|author contributions?|conflicts? of interest|"
                          r"associated content|supporting information|data availability( statement)?)\W*$", re.I)
AFFIL_RE = re.compile(r"universit|department|institute|laborator|faculty|school|@|orcid|correspond|e-?mail|"
                      r"\b(received|accepted|published)( on| online)?:? ?\d|authors? (contribut|declare)|"
                      r"supplementary (material|information)", re.I)
FURN_RE = re.compile(r"published by|copyright|©|licen[cs]e|creative commons|doi\.org|downloaded|cite (this|as)|this journal is|\bdoi:", re.I)
TOK_RE = re.compile(r"[a-z0-9]{2,}")
RUN_RE = re.compile(r"[A-Za-z0-9\u0370-\u03ff]+(?:(?<=\d)[.,](?=\d)[A-Za-z0-9\u0370-\u03ff]+)*")   # . or , joins digits only (3.0, 1,2, 10,000); Greek letters count as letters
AUTHOR_RE = re.compile(r"[A-Z][\w'’-]+,?\s*\^\d[\w,]*")        # "Lastname^1,2" or "Lastname,^1": a name with its affiliation marker
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
    t = t.replace("_", "").replace("^", " ")           # subscripts join their base (H2O), superscripts stand alone
    pure, mixed = [], []
    for m in RUN_RE.finditer(t):
        run = m.group(0)
        if not any(ch.isdigit() for ch in run):
            continue
        m_unit = re.fullmatch(r"(\d+(?:[.,]\d+)*)([A-Za-z]{1,3})", run)
        if m_unit:                                          # 514nm, 2s, 100mW, 1st: a number with a unit glued to it
            run = m_unit.group(1)
        if run.replace(".", "").replace(",", "").isdigit():
            if "," in run and "." not in run and not re.fullmatch(r"\d{1,3}(,\d{3})+", run):
                pure.extend(run.split(","))             # a citation list 14,15
                continue
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
    for para in re.split(r"\n\s*\n", md):
        p = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", para)
        p = re.sub(r"</?[A-Za-z][^<>]*>", lambda m: "^" if m.group(0) == "<sup>" else "_" if m.group(0) == "<sub>" else " ", p)   # tags only, not "< 10"
        p = re.sub(r"^\s{0,3}#{1,6}\s*", "", p, flags=re.M)
        p = re.sub(r"[*`]+", "", p)
        p = re.sub(r"\$\$?", " ", p)
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            out.append((SM._norm_cell_text(p), p))
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
                k = min(range(len(lines)), key=lambda i: abs(lines[i][0] - c["bottom"] - 2))
                if abs(lines[k][0] - c["bottom"]) <= 7:
                    lines[k][1].append(c)
                else:
                    lines.append([c["bottom"], [c]])
        lines.sort(key=lambda l: l[0])
    out = []
    for bottom, cs in lines:
        cs.sort(key=lambda c: c["x0"])
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
            if prev is not None and gap > max(0.6, 0.1 * c["size"]) and not (small and sup and gap <= 4):   # a word space is ~1.5 pt at 9 pt, in-word gaps ~0
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


def check_body(pdf_path, md_text, tree, crop_dir, crop_prefix="body"):
    """-> {"body_flags": [...], "body_check": {...}}. Crops go to crop_dir/<crop_prefix>_p<P>_<k>.png."""
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
    paras = _md_paragraphs(md_text)
    vocab = set(TOK_RE.findall(md_text.lower()))
    grams = defaultdict(set)
    for i, (pn, _) in enumerate(paras):
        toks = TOK_RE.findall(pn.lower())
        for k in range(len(toks) - 2):
            grams[(toks[k], toks[k + 1], toks[k + 2])].add(i)
    counts, not_checkable, flags = Counter(), Counter(), []
    pl = pdfplumber.open(str(pdf_path))
    pdoc = pypdfium2.PdfDocument(str(pdf_path))
    # units: (page, block type, bbox, lines) in reading order; segments outside the blocks as units of their own
    units = []
    header_lines = []
    for pno, page in enumerate(pl.pages, 1):
        chars = [c for c in page.chars if c["text"].strip() and c.get("upright", True)]
        n0 = len(chars)                            # characters drawn outside the page area are not visible (MDPI's
        chars = [c for c in chars if c["top"] >= 0 and c["bottom"] <= page.height and c["x1"] >= 0 and c["x0"] <= page.width]
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
        blocks = blocks_by_page.get(pno, [])
        excl = [bb for bt, bb in blocks if bt in EXCL_BLOCKS]
        for bt, bb in blocks:
            if bt in ("PageHeader", "PageFooter"):
                for l in _lines_of([c for c in chars if _inside(c, bb)]):
                    header_lines.append((pno, l[0]))
        text = [bb for bt, bb in blocks if bt in TEXT_BLOCKS]
        used = [False] * len(chars)
        for bt, bb in blocks:
            if bt not in TEXT_BLOCKS:
                continue
            inside = [k for k, c in enumerate(chars) if not used[k] and _inside(c, bb)]
            for k in inside:
                used[k] = True
            if inside:
                units.append((pno, bt, bb, _lines_of([chars[k] for k in inside])))
        rest = [c for k, c in enumerate(chars) if not used[k] and not any(_inside(c, bb) for bb in excl)]
        for seg in _segments(rest):
            units.append((pno, "outside", [seg[3], seg[1], seg[4], seg[2]], [seg]))
    # units stay in Marker's reading order (the block tree); the segments outside the blocks follow their page
    line_pages = defaultdict(set)
    for pno, bt, bb, lines in units:
        for l in lines:
            line_pages[re.sub(r"\d+", "#", l[0].strip())].add(pno)
    for pno, txt in header_lines:
        line_pages[re.sub(r"\d+", "#", txt.strip())].add(pno)
    running = {k for k, ps in line_pages.items() if len(ps) >= 3 and len(k.split()) <= 10}
    rendered = {}
    def crop(pno, line, k):
        if pno not in rendered:
            rendered[pno] = pdoc[pno - 1].render(scale=2).to_pil()
        im = rendered[pno]
        box = (max(0, int((line[3] - 30) * 2)), max(0, int((line[1] - 14) * 2)), min(im.width, int((line[4] + 30) * 2)), min(im.height, int((line[2] + 14) * 2)))
        if box[2] <= box[0] or box[3] <= box[1]:                  # a line outside the page area: no crop
            return ""
        name = f"{crop_prefix}_p{pno}_{k}.png"
        im.crop(box).save(Path(crop_dir) / name)
        return name
    stop_heads = [i for i, (pn, po) in enumerate(paras) if STOP_HEAD_RE.match(po.strip()) and len(po.split()) <= 4]
    ref_idx = next((i for i in stop_heads if i >= len(paras) * 0.5), None)   # the first stop heading in the second half
    blocked = set()                    # output paragraphs a not-checkable unit matches: no extra direction for them
    assigned = defaultdict(list)       # paragraph index -> [(line, pno)]
    assigned_weak = defaultdict(list)  # paragraph index -> [(weak line, pno)]
    stopped = False
    for pno, bt, bb, lines in units:
        n0 = len(lines)
        lines = [l for l in lines if re.sub(r"\d+", "#", l[0].strip()) not in running]
        counts["excluded: running line"] += n0 - len(lines)
        n_aff = sum(1 for l in lines if AFFIL_RE.search(l[0]))
        if n_aff and (len(lines) <= 3 or n_aff >= len(lines) / 2):     # an author/affiliation block
            counts["excluded: author/affiliation/furniture line"] += len(lines)
            continue
        if pno <= 2 and sum(1 for l in lines if len(AUTHOR_RE.findall(l[0])) >= 2) >= max(1, len(lines) / 2):
            counts["excluded: author line (names with affiliation markers)"] += len(lines)   # the authors come from the manifest
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
        if not lines:
            counts["excluded: unit without a word of 4+ letters (formula, labels, numbers alone)"] += len(weak)
            continue
        # a weak line (no word of 4+ letters: a formula, a short last line "al.^36 ).") stays with its unit for the
        # extra direction only: its numbers count as present in the layer, but are not required in the output
        counts["weak lines (no word of 4+ letters or a reaction line): extra direction only"] += len(weak)
        text = " ".join(l[0] for l in lines)
        if STOP_HEAD_RE.match(text.strip()) and len(text.split()) <= 4:
            stopped = True
        if stopped:
            counts["excluded: after the references/acknowledgements heading"] += len(lines)
            continue
        counts["lines"] += len(lines)
        if len(text.split()) < 4:
            counts["excluded: fewer than 4 words"] += len(lines)
            continue
        garbled = [l for l in lines if len(WORD4_RE.findall(l[0])) >= 3
                   and sum(1 for w in WORD4_RE.findall(l[0]) if w.lower() in vocab) < 0.3 * len(WORD4_RE.findall(l[0]))]
        if garbled:                                   # two lines drawn over each other (MDPI's misplaced duplicate layer)
            counts["not checkable: garbled text-layer line (overlapping duplicate layer; fewer than 30 % of its words occur in the output)"] += len(garbled)
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
        best, n = (cand.most_common(1)[0] if cand else (None, 0))
        need = 1 if len(toks) < 6 else 2
        if unk:
            not_checkable[", ".join(f"{fam} {code}" for (fam, code) in sorted(unk))] += len(lines)
            counts["not checkable: undecoded glyph"] += len(lines)
            if best is not None and n >= need:
                blocked.add(best)                 # its output paragraph is not checked in the extra direction either
            continue
        counts["checked"] += len(lines)
        if len(toks) < 3:
            counts["not checkable: unit too short to locate in the output (fewer than 3 words)"] += len(lines)
            continue
        if best is None or n < need:
            counts["unmatched"] += len(lines)
            for l in lines:
                nums = _nums(l[0])
                if nums:
                    k = len(flags)
                    flags.append({"page": pno, "kind": "line not found in the output", "layer_line": l[0], "output_sentence": "",
                                  "layer_numbers": nums, "output_numbers": [], "crop": crop(pno, l, k)})
            continue
        if ref_idx is not None and best >= ref_idx:         # the unit matches a paragraph after the References heading
            stopped = True
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
        for l in lines:
            assigned[key].append((l, pno))
        for l in weak:
            assigned_weak[key].append((l, pno))
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
    groups, groups_weak = defaultdict(list), defaultdict(list)
    for key, ls in assigned.items():
        groups[find(key[0])].extend(ls)
    for key, ls in assigned_weak.items():
        groups_weak[find(key[0])].extend(ls)
    members = defaultdict(set)
    for key in list(assigned) + list(assigned_weak):
        members[find(key[0])].update(key)
    for root, lines in groups.items():
        key = tuple(sorted(members[root]))
        assigned_weak_i = groups_weak.get(root, [])
        seen_text, uniq = set(), []
        for l, p_ in lines:                   # the same line printed twice (a title on a cover page) counts once
            if l[0] not in seen_text:
                seen_text.add(l[0]); uniq.append((l, p_))
        lines = uniq
        ptext = " ".join(paras[j][0] for j in key)
        porig = " ".join(paras[j][1] for j in key)
        ltext = " ".join(l[0] for l, _ in lines)
        ltext_all = " ".join(l[0] for l, _ in lines + assigned_weak_i)
        la, lb = tokens(ltext)
        la_all, lb_all = tokens(ltext_all)
        pa, pb = tokens(ptext)
        miss = (la - pa) & (lb - pb)
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
        ctext = " ".join(covered)
        ca, cb = tokens(ctext)
        extra = (ca - la_all) & (cb - lb_all)
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
                          "output_numbers": _nums(SM._norm_cell_text(s))[:30], "crop": crop(pno, line, k)})
        for tok in sorted(extra.elements()):
            s = next((s for s in sentences if tok in sent_nums(s)), sentences[0])
            line, pno = max(lines, key=lambda lp: len(set(TOK_RE.findall(lp[0][0].lower())) & set(TOK_RE.findall(s.lower()))))
            k = len(flags)
            flags.append({"page": pno, "kind": "number of the output paragraph absent from the text layer", "number": tok,
                          "layer_line": line[0], "output_sentence": s[:400], "layer_numbers": _nums(line[0]),
                          "output_numbers": _nums(SM._norm_cell_text(s))[:30], "crop": crop(pno, line, k)})
    pl.close()
    counts["flags"] = len(flags)
    return {"body_flags": flags,
            "body_check": {"counts": dict(counts), "not_checkable_reasons": dict(not_checkable),
                           "method": "decoded text layer (glyph_codes.json) read inside Marker's text blocks vs document.md paragraphs matched by word 3-grams; numbers compared both ways"}}
