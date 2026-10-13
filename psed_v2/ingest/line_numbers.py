#!/usr/bin/env python3
"""Margin line numbers of a line-numbered manuscript: found in the decoded text layer and removed from document.md.
Called by merge.py before body_check.py; writes nothing itself.

Detection, per page: every baseline of the page is read (all upright characters inside the page area). A candidate
is a bare integer of 1-4 digits that stands alone on its baseline, or starts or ends a text line (3+ words) set
apart from the text by a gap of 3 pt or more, not followed by "." or ")", and standing outside the text column (the
10th-90th percentile x-span of the first and last letters of the text lines, by 3 pt or more). A page has margin
line numbers when at least 8 candidates on one side stand at the same x (within one 4-pt bin), their values
increase down the page (at least 70 % of the steps are +1), and they are at least as many as 70 % of the page's text
lines (a manuscript numbers every line, a reference list does not). The paper is line-numbered when at least 3
pages have the pattern; only then is anything changed. Running lines (the same text on 3+ pages) are not text lines.

Removal (strip_margin_numbers): Marker writes the margin number of a line in front of that line's first words, so
over the whole document.md a bare integer of the sequence is removed when the two words before it end a text line k
and the two words after it start the next text line k+1 of some page with the pattern (a line break; the number
after it may itself open line k+1), unless the same bare number occurs in those two lines (a real number at the
break); a word hyphenated across the break is joined ("demon- 9 strate" -> "demonstrate"). A number alone on a
markdown line, and a run of three or more consecutive integers of the sequence separated by spaces or line breaks,
are margin numbers of empty lines and are removed too. Pages are not located in document.md: Marker's block order
may differ from the page order. Counts: pages, removed, kept_real (numbers kept because they occur at the break).
"""
import re
from collections import Counter

import structure_marker as SM

MIN_PER_PAGE = 8
MIN_PAGES = 3


def _baselines(chars):
    lines = []
    for c in sorted(chars, key=lambda c: (c["bottom"], c["x0"])):
        if lines and abs(lines[-1][0] - c["bottom"]) <= 2.5:
            lines[-1][1].append(c)
        else:
            lines.append([c["bottom"], [c]])
    return [sorted(cs, key=lambda c: c["x0"]) for _, cs in lines]


def _line_text(cs):
    txt, prev = "", None
    for c in cs:
        t, _ = SM._decode_char(c)
        if prev is not None and c["x0"] - prev["x1"] > max(0.6, 0.1 * c["size"]):
            txt += " "
        txt += t
        prev = c
    return SM._norm_cell_text(txt)


def _edge(cs, side):
    """(value, x0, rest chars) for a bare integer at the start ('left') or end ('right') of a text line."""
    seq = cs if side == "left" else cs[::-1]
    digits = []
    for c in seq:
        adjacent = not digits or (abs(c["x0"] - digits[-1]["x1"]) <= 1.5 if side == "left" else abs(digits[-1]["x0"] - c["x1"]) <= 1.5)
        if c["text"].isdigit() and adjacent:
            digits.append(c)
        else:
            break
    if not digits or len(digits) > 4 or len(digits) == len(cs):
        return None
    rest = seq[len(digits):]
    gap = rest[0]["x0"] - digits[-1]["x1"] if side == "left" else digits[-1]["x0"] - rest[0]["x1"]
    if gap < 3 or rest[0]["text"] in ".)":
        return None
    val = int("".join(c["text"] for c in (digits if side == "left" else digits[::-1])))
    return val, (digits[0]["x0"] if side == "left" else digits[-1]["x0"]), (rest if side == "left" else rest[::-1])


def _page_pattern(chars):
    """{"side", "values", "text_lines": [(y, text)]} when the page carries margin line numbers, else None."""
    lines = _baselines(chars)
    text, cands = [], []          # text lines (y, x0, x1, chars without an edge number); candidates (value, x, y, side)
    tlines = [cs for cs in lines if len(re.findall(r"[A-Za-z]{2,}", _line_text(cs))) >= 3]   # at least 3 words
    if len(tlines) < 5:
        return None
    x0s = sorted(next((c["x0"] for c in cs if c["text"].isalpha()), cs[0]["x0"]) for cs in tlines)   # first letter
    x1s = sorted(max((c["x1"] for c in cs if c["text"].isalpha()), default=cs[-1]["x1"]) for cs in tlines)
    left, right = x0s[len(x0s) // 10], x1s[-1 - len(x1s) // 10]       # the text column (10th-90th percentile)
    for cs in lines:
        s = "".join(c["text"] for c in cs)
        if s.isdigit() and len(s) <= 4:
            cands.append((int(s), cs[0]["x0"], cs[-1]["x1"], cs[0]["bottom"], None))
            continue
        if cs not in tlines:
            continue
        body = cs
        for side in ("left", "right"):
            e = _edge(cs, side)
            if e and ((side == "left" and e[1] + 5 < left - 3) or (side == "right" and e[1] > right + 3)):
                cands.append((e[0], e[1], e[1] + 5, cs[0]["bottom"], side))   # a number outside the text column
                body = e[2]
        text.append((cs[0]["bottom"], body[0]["x0"], body[-1]["x1"], body))
    if len(cands) < MIN_PER_PAGE:
        return None
    for side in ("left", "right"):
        col = [c for c in cands if (c[2] < left - 3) if side == "left"] if side == "left" else [c for c in cands if c[1] > right + 3]
        if len(col) < MIN_PER_PAGE:
            continue
        x_mode = Counter(round(c[1] / 4) for c in col).most_common(1)[0][0]
        col = sorted([c for c in col if abs(round(c[1] / 4) - x_mode) <= 1], key=lambda c: c[3])
        if len(col) < MIN_PER_PAGE or len(col) < 0.7 * len(text):
            continue
        steps = [col[i + 1][0] - col[i][0] for i in range(len(col) - 1)]
        if sum(1 for s in steps if s == 1) < 0.7 * len(steps):
            continue
        return {"side": side, "values": [c[0] for c in col], "text_lines": [(y, _line_text(body)) for y, _, _, body in text]}
    return None


def find_margin_numbers(pl):
    found = {}
    for pno, page in enumerate(pl.pages, 1):
        chars = [c for c in page.chars if c["text"].strip() and c.get("upright", True) and c["top"] >= 0 and c["bottom"] <= page.height]
        r = _page_pattern(chars)
        if r:
            found[pno] = r
    seen = Counter()                            # running lines (the same text, digits masked, on 3+ pages) are not
    for r in found.values():                    # text lines: they do not take part in the line breaks
        seen.update({re.sub(r"\d+", "#", lt)[:30] for _, lt in r["text_lines"]})
    for r in found.values():
        r["text_lines"] = [(y, lt) for y, lt in r["text_lines"] if seen[re.sub(r"\d+", "#", lt)[:30]] < 3]
    return found


def _tolerant(word):
    return r"[*_`\\${}^]*".join(re.escape(ch) for ch in word)


def _words(s, n=2):
    return [w.lower() for w in re.findall(r"[A-Za-z]+", s) if len(w) >= 2][:n]


def strip_margin_numbers(md_text, found):
    """(new document.md text, counts). Marker writes the margin number of a line in front of that line's first words,
    so a bare integer of the sequence is removed when the two words before it end a text line k and the two words
    after it start the next text line k+1 of some page with the pattern (a line break), unless the same bare number
    occurs in those two lines (a real number at the break); a number alone on a markdown line, or a run of three or
    more consecutive integers of the sequence separated by spaces or line breaks, is removed too. Pages are not
    located in document.md: Marker's block order may differ from the page order."""
    values = set()
    breaks = {}                           # (last two words of line k, first two words of line k+1) -> (line k, line k+1)
    firsts = {}                           # first two words of a page's first body line -> that line
    for pno in sorted(found):
        v = found[pno]["values"]
        values.update(range(min(v), max(v) + 1))
        tls = [lt for _, lt in sorted(found[pno]["text_lines"])]
        for k, lt in enumerate(tls):
            w = _words(lt)
            if len(w) < 2 and len(re.findall(r"[A-Za-z]+", lt)) > 2:
                continue                                      # a one-word key only for a short last line ("porous.")
            if not w:
                continue
            if k == 0:
                firsts[tuple(w)] = lt
            else:
                e = [x.lower() for x in re.findall(r"[A-Za-z]+", tls[k - 1]) if len(x) >= 2][-2:]
                if len(e) == 2:
                    breaks[(tuple(e), tuple(w))] = (tls[k - 1], lt)
    removed = kept_real = 0
    # runs of consecutive integers of the sequence ("T the 21 22 23 24")
    runs = []
    for m in re.finditer(r"(?<![\w.,])\d{1,4}(?:[ \t]*\n?[ \t]*\d{1,4}){2,}(?![\w.,])", md_text):
        nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
        if all(n in values for n in nums) and all(nums[i + 1] - nums[i] == 1 for i in range(len(nums) - 1)):
            runs.append((m.start(), m.end(), len(nums)))
    for s, e, n in reversed(runs):
        head = md_text[:s].rstrip(" \t")
        md_text = head + (" " if head and not head.endswith("\n") else "") + md_text[e:].lstrip(" \t")
        removed += n
    out = []
    for m in re.finditer(r"(?<![^\s>])(\d{1,4})(?![^\s<])", md_text):     # a bare token between spaces ("1:1" is not)
        v = int(m.group(1))
        if v not in values:
            continue
        alone = re.search(r"(^|\n)[ \t]*$", md_text[:m.start(1)]) and re.match(r"[ \t]*(\n|$)", md_text[m.end(1):])
        if alone:                             # a number alone on a markdown line: a margin number of an empty line
            out.append((m.start(1), m.end(1)))
            continue
        after_txt = re.sub(r"<[^>]+>|\\[a-z]+|[*_`$\\{}^<>/]", " ", md_text[m.end():m.end() + 160])
        nxt = re.findall(r"[A-Za-z0-9.:]+", after_txt)
        if not nxt:
            continue
        lead_num = nxt[0] if nxt[0][0].isdigit() else None   # "14 46 at%": the next line may itself start with a number
        key = tuple(_words(" ".join(nxt)))
        if not key:
            continue
        before = [x.lower() for x in re.findall(r"[A-Za-z]+", re.sub(r"<[^>]+>|\\[a-z]+|[*_`$\\{}^<>/]", " ", md_text[max(0, m.start(1) - 160):m.start(1)])) if len(x) >= 2][-2:]
        at_line_start = re.search(r"(^|\n)[ \t]*$", md_text[:m.start(1)]) is not None
        pair = (tuple(before), key) if len(before) == 2 else None
        if pair in breaks:
            both = " ".join(breaks[pair])
            nxt_line = breaks[pair][1]
        elif key in firsts and at_line_start:
            both = nxt_line = firsts[key]
        else:
            continue
        if lead_num and not nxt_line.lstrip().startswith(lead_num.rstrip(".:")):
            continue                          # the number after it does not open that text line
        if re.search(r"(?<![^\s])" + str(v) + r"(?![^\s])", both):     # the same bare number in the text at the break
            kept_real += 1
            continue
        out.append((m.start(1), m.end(1)))
    for s, e in reversed(out):
        seg = md_text[:s].rstrip(" \t")
        if re.search(r"\w-$", seg) and md_text[e:e + 1] in " \t":        # "demon- 9 strate" -> "demonstrate"
            md_text = seg + md_text[e:].lstrip(" \t")
        elif re.search(r"\w-[ \t]*\n$", seg + "\n") and md_text[e:e + 1] in " \t":   # "demon-  \n9 strate"
            md_text = re.sub(r"-[ \t]*\n$", "", seg) + md_text[e:].lstrip(" \t")
        elif re.match(r"[ \t]*\n", md_text[e:]) and re.search(r"\n[ \t]*$", md_text[:s]):   # alone on its line
            md_text = md_text[:s].rstrip(" \t") + md_text[e:].lstrip(" \t")
        else:
            md_text = md_text[:s] + md_text[e:].lstrip(" \t") if md_text[s - 1:s] in " \t\n" or s == 0 else md_text[:s] + md_text[e:]
        removed += 1
    md_text = re.sub(r"(?<=\S) {2,}(?=\S)", " ", md_text)
    return md_text, {"pages": len(found), "removed": removed, "kept_real": kept_real}


def process(pdf_path, md_text):
    """-> (document.md text, info). info["pages"] == 0 when the paper has no margin line numbers (text unchanged)."""
    import pdfplumber
    pl = pdfplumber.open(str(pdf_path))
    found = find_margin_numbers(pl)
    pl.close()
    if len(found) < MIN_PAGES:
        return md_text, {"pages": 0, "removed": 0, "kept_real": 0, "candidate_pages": sorted(found)}
    new, info = strip_margin_numbers(md_text, found)
    info["page_list"] = sorted(found)
    return new, info
