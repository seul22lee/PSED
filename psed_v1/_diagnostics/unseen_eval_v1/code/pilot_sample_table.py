#!/usr/bin/env python3
"""
pilot_sample_table.py — recover a paper's SAMPLE TABLE from the original PDF.

Why this exists: a per-sample parameter table is the richest source of specimen identity
in an ALD paper, and Docling's markdown export of a wide numeric table in this corpus is
transposed and column-merged beyond use.

The table is rebuilt from the PDF's own READING ORDER, which preserves the logical row
sequence even when the table is typeset rotated on the page (as it is here — grouping by
y coordinate recovers the printed columns, not the rows).

Entirely local and deterministic: PyMuPDF text extraction, no API, no vision model.

Generic by construction. A table qualifies only if
  · its header names a specimen-code column, and
  · its specimen codes form a run of consecutive integers 1..N, and
  · every row has the same number of value columns.
Failing any of these returns {} — the honest answer for a paper that does not tabulate
its samples. No paper, DOI, table number or column name is hard-coded.
"""
import re
import sys
from collections import Counter

_CODE_HEAD = re.compile(r"\b(?:sample|specimen|chip|wafer|coupon)s?\s*"
                        r"(?:code|codes|id|no|number|nr)[a-z]?\b", re.I)
_SERIES_HEAD = re.compile(r"\bseries\b", re.I)
_SERIES_VAL = re.compile(r"^[A-Z]$")
_INT = re.compile(r"^\d{1,3}$")


def _norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def _ctrl(t):
    """Strip the C0 control bytes PDF text extraction leaves inside numeric cells
    (\x03 before a value), which would otherwise make a plain number unparseable."""
    return re.sub(r"[\x00-\x1f\x7f]", "", t or "")


def find_sample_table(pdf_path, max_pages=None):
    """({sample_code: {series, columns, page}}, header_text_or_reason)."""
    try:
        import fitz
    except ImportError:
        return {}, "PyMuPDF unavailable"
    doc = fitz.open(str(pdf_path))
    n = doc.page_count if max_pages is None else min(max_pages, doc.page_count)
    for pno in range(n):
        text = doc[pno].get_text()
        m = _CODE_HEAD.search(text.replace("\n", " "))
        if not m:
            continue
        toks = [t for t in (_ctrl(x) for x in text.split()) if t]
        parsed, header = _parse_tokens(toks)
        if parsed:
            for v in parsed.values():
                v["page"] = pno + 1
            return parsed, header
    return {}, "no table with a specimen-code column and a consecutive specimen-code run"


def _parse_tokens(toks):
    """Segment the reading-order token stream into one row per specimen.

    The specimen codes are located as a run of consecutive integers 1, 2, 3 … The stride
    between them must be constant — that constant IS the column count, and requiring it
    is what stops a numeric cell that happens to equal the next code from splitting a row.
    """
    pos = {}
    for i, t in enumerate(toks):
        if _INT.match(t):
            pos.setdefault(int(t), []).append(i)
    if 1 not in pos or 2 not in pos:
        return {}, "no specimen-code run"
    best = None
    for start in pos[1]:
        chain, cur = [start], start
        code = 2
        while code in pos:
            nxt = next((p for p in pos[code] if p > cur), None)
            if nxt is None:
                break
            chain.append(nxt)
            cur = nxt
            code += 1
        if len(chain) >= 3:
            gaps = [chain[i + 1] - chain[i] for i in range(len(chain) - 1)]
            k, count = Counter(gaps).most_common(1)[0]
            # Keep the leading prefix whose stride is the modal stride, tolerating one
            # extra token where a series letter opens a new block: the letter sits
            # between two specimen rows and lengthens that one gap by exactly 1.
            trimmed = [chain[0]]
            for i in range(1, len(chain)):
                d = chain[i] - trimmed[-1]
                if d == k or (d == k + 1 and _SERIES_VAL.match(toks[chain[i] - 1])):
                    trimmed.append(chain[i])
                else:
                    break
            if len(trimmed) >= 3 and (best is None or len(trimmed) > len(best[0])):
                best = (trimmed, k)
    if not best:
        return {}, "no constant-stride specimen-code run"
    chain, stride = best
    ncols = stride - 1
    if ncols < 2:
        return {}, "specimen rows carry no value columns"

    # The consecutive run only had to establish the STRIDE. Rows are then walked by that
    # stride, taking whatever specimen code sits at each row start — a table may reuse a
    # specimen in a later block (one chip belonging to two study series), and requiring
    # codes to keep incrementing would stop the parse at the first such reuse.
    starts, p = list(chain), chain[-1]
    while True:
        nxt = None
        for d in (stride, stride + 1):
            q = p + d
            if q < len(toks) and _INT.match(toks[q]):
                nxt = q
                break
        if nxt is None:
            break
        starts.append(nxt)
        p = nxt

    out, series, order = {}, None, []
    for p in starts:
        code = toks[p]
        if p > 0 and _SERIES_VAL.match(toks[p - 1]):
            series = toks[p - 1]
        rec = {"series": series, "columns": toks[p + 1: p + 1 + ncols],
               "source": "pdf_reading_order", "n_columns": ncols}
        if code in out:
            # a reused specimen: keep the first row's values, record every series it is in
            prev = out[code]
            prev.setdefault("also_in_series", [])
            if series and series != prev["series"] and series not in prev["also_in_series"]:
                prev["also_in_series"].append(series)
            continue
        out[code] = rec
        order.append(code)
    head_start = max(0, chain[0] - 90)
    return out, _norm(" ".join(toks[head_start:chain[0]]))[:700]


#: header keyword -> (quantity id, unit, role hint). Matched in header order, so the
#: recognised keywords are assigned to value columns left to right.
_COL_HINTS = [
    (re.compile(r"pulse[-\s]?purge", re.I), "pulse_purge_sequence", None, "CASE"),
    (re.compile(r"channel\s*height", re.I), "feature_height", "nm", "CASE"),
    (re.compile(r"pillar\s*(?:layout|design)", re.I), "pillar_layout", None, "CASE"),
    (re.compile(r"\bcycles?\b", re.I), "cycle_number", "cycle", "CASE"),
    (re.compile(r"magnificat|objective|spot\s*size", re.I),
     "reflectometer_magnification", None, "MEAS"),
    (re.compile(r"\btemperature\b", re.I), "deposition_temperature", "°C", "CASE"),
    (re.compile(r"\bpressure\b", re.I), "working_pressure", "Pa", "CASE"),
]


def column_map(header_text, ncols):
    """[(quantity, unit, role_hint)] for the leading value columns, from the header.

    Only recognised keywords are mapped, in the order they appear in the header; the
    remaining columns stay unnamed and their values are carried opaquely, so nothing is
    invented for a column whose meaning is not established.
    """
    hits = []
    for rx, q, unit, role in _COL_HINTS:
        m = rx.search(header_text or "")
        if m:
            hits.append((m.start(), q, unit, role))
    hits.sort()
    seen, out = set(), []
    for _, q, unit, role in hits:
        if q in seen:
            continue
        seen.add(q)
        out.append((q, unit, role))
    return out[:ncols]


if __name__ == "__main__":
    t, h = find_sample_table(sys.argv[1])
    print("header:", h[:300])
    print("columns mapped:", column_map(h, 14))
    for k in sorted(t, key=lambda x: int(x)):
        print("  sample %-4s series=%-4s %s" % (k, t[k]["series"], t[k]["columns"][:7]))
