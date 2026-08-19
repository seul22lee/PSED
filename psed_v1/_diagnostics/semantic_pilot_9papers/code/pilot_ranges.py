#!/usr/bin/env python3
"""
pilot_ranges.py — numeric ranges, and a physical sign check.

A hyphen between two numbers is a range far more often than it is a minus sign, and an
upstream parser that guesses wrong turns "ultrashort doses (10-120 ms)" into a pulse time
of MINUS 120 milliseconds. That value then travels through the semantic layer as a
"directly stated" deposition condition.

Two defences, both generic:

  1. `parse_interval` reads a range written with a hyphen, en dash, em dash, "to" or
     "±", and returns an explicit interval rather than a scalar.
  2. `sign_is_physical` refuses a negative value for a quantity that cannot be negative.
     It is a whitelist of SIGNED quantities, not a blacklist of unsigned ones, so a new
     quantity is treated as unsigned until something says otherwise — the conservative
     direction.

Nothing here knows a paper, a DOI or a figure.
"""
import re

DASHES = "‐‑‒–—―−-"       # hyphen … en/em dash … minus
_D = "[" + re.escape(DASHES) + "]"
_NUM = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"

#: "10-120 ms", "10 – 120", "50 to 400 °C", "0.1–4.0 s"
_RANGE = re.compile(r"(?<![\w])(?<!\.\d)(?<!\d\.)(%s)\s*(?:%s|\bto\b)\s*(%s)(?![\w])(?!\.\d)" % (_NUM, _D, _NUM))
#: "~30", "≈ 30", "ca. 30", "about 30"
_APPROX = re.compile(r"(?:[~≈∼]|\bca\.?\b|\babout\b|\bapprox\w*\b)\s*(%s)" % _NUM, re.I)
#: a genuinely signed leading value: "-0.5 V", "− 1.2"
_SIGNED = re.compile(r"(?<![\w])(?<!\.\d)(?<!\d\.)(%s\s*%s)(?![\w])(?!\.\d)" % (_D, _NUM))

#: Quantities that CAN legitimately be negative. Everything else is treated as unsigned,
#: so an unknown quantity errs towards rejecting a negative rather than publishing one.
SIGNED_QUANTITIES = {
    "potential", "voltage", "bias", "bias_voltage", "flat_band_voltage",
    "threshold_voltage", "zeta_potential", "gibbs_energy", "enthalpy", "free_energy",
    "formation_energy", "binding_energy_shift", "slope", "gradient", "offset",
    "temperature_difference", "delta_temperature", "charge", "current",
}
#: Substrings that mark a quantity as signed even when its exact id is unknown.
_SIGNED_HINT = re.compile(r"(?:potential|voltage|bias|slope|gradient|offset|"
                          r"enthalp|free[_\s-]?energy|delta|difference|shift)", re.I)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def sign_is_physical(quantity, value):
    """(ok, reason). A negative value is only physical for a signed quantity."""
    v = _f(value)
    if v is None or v >= 0:
        return True, None
    q = str(quantity or "")
    if q in SIGNED_QUANTITIES or _SIGNED_HINT.search(q):
        return True, None
    return False, ("%s cannot be negative; %s is not a signed quantity" % (v, q or "this"))


def parse_interval(text, prefer_positive=True):
    """The first numeric interval in `text`, or None.

    `prefer_positive` exists because the same characters mean different things in
    "10-120 ms" (a range) and "-120 mV" (a signed value). A range is only recognised when
    a number precedes the dash, which is exactly what distinguishes the two.
    """
    if not text:
        return None
    m = _RANGE.search(text)
    if not m:
        return None
    lo, hi = _f(m.group(1)), _f(m.group(2))
    if lo is None or hi is None:
        return None
    if hi < lo:
        lo, hi = hi, lo
    return {"lower": lo, "upper": hi, "matched": m.group(0).strip(),
            "span": re.sub(r"\s+", " ", text[max(0, m.start() - 40):m.end() + 40]).strip()}


def approx_value(text):
    """A value the source itself marks as approximate ("~30", "ca. 30")."""
    if not text:
        return None
    m = _APPROX.search(text)
    return None if not m else {"value": _f(m.group(1)), "matched": m.group(0).strip()}


def repair_condition(cond, context=None):
    """Repair one condition record; returns a NEW record.

    `context` is the paper text. It is consulted only when the condition's own evidence
    snippet was truncated at the dash — "-40 cycles" is what survives of "10-40 cycles" —
    in which case the fragment is relocated in the full text and re-parsed with a wider
    window.

    Three outcomes, all explicit:
      · `value_kind = "range"`  — the evidence holds an interval, so the scalar is replaced
        by `value_lower` / `value_upper` and the misread scalar is kept as
        `superseded_value` for audit;
      · unchanged — the value is physical and no interval was found;
      · `value = None`, `value_status = "REJECTED_UNPHYSICAL"` — the value is negative for
        an unsigned quantity and no interval explains it. The condition is kept with its
        evidence rather than deleted, so the gap is visible.
    """
    out = dict(cond)
    q, v = out.get("quantity"), out.get("value")
    raw = out.get("evidence") or out.get("raw_evidence") or ""
    fv = _f(v)
    ok, why = sign_is_physical(q, v)
    if ok and fv is not None:
        out.setdefault("value_kind", "scalar")
        return out
    iv = parse_interval(raw)
    if iv is None and context and raw:
        frag = re.sub(r"\s+", " ", raw).strip()
        j = context.find(frag)
        if j < 0 and len(frag) > 12:
            j = context.find(frag[:12])
        if j >= 0:
            iv = parse_interval(context[max(0, j - 40):j + len(frag) + 40])
    if iv is not None and (fv is None or abs(fv) in (iv["lower"], iv["upper"])):
        out["value_kind"] = "range"
        out["value_lower"], out["value_upper"] = iv["lower"], iv["upper"]
        out["value"] = None
        out["superseded_value"] = v
        out["value_repair"] = ("the source states an interval %s; the upstream parser read "
                               "its separator as a minus sign" % iv["matched"])
        out["provenance_type"] = "directly_stated_range"
        return out
    if not ok:
        out["value"] = None
        out["superseded_value"] = v
        out["value_status"] = "REJECTED_UNPHYSICAL"
        out["value_repair"] = why
        return out
    out.setdefault("value_kind", "scalar")
    return out


def repair_all(conds, context=None):
    return [repair_condition(c, context) for c in (conds or [])]


def quantities_from_text(text, hints):
    """[{quantity, value…}] for each `hints` keyword that is followed by a number.

    `hints` is [(regex, quantity, unit)]. Two constructions are handled explicitly because
    scientific captions use both:

      · direct        "an aspect ratio of ~30"        -> the value FOLLOWS the keyword
      · respectively  "the depth and average width … were 18.5 and 0.6 µm, respectively"
                      -> two keywords, then their two values in the same order

    The tail is preferred over the head: a caption states a quantity and then its value, and
    scanning backwards is how "coated by 830 cycles … aspect ratio" gave the aspect ratio a
    cycle count.
    """
    t = re.sub(r"\s+", " ", text or "")
    out, claimed = [], set()

    def add(quantity, unit, value=None, interval=None, approx=False, span=""):
        if quantity in claimed:
            return
        rec = {"quantity": quantity, "unit": unit, "span": span[:260]}
        if interval:
            rec.update({"value": None, "value_kind": "range",
                        "value_lower": interval["lower"], "value_upper": interval["upper"]})
        else:
            ok, _ = sign_is_physical(quantity, value)
            if value is None or not ok:
                return
            rec.update({"value": value,
                        "value_kind": "approximate" if approx else "scalar"})
        claimed.add(quantity)
        out.append(rec)

    # ---- the "A and B … were x and y, respectively" pairing ------------------------
    for sent in re.split(r"(?<=[.]) ", t):
        if "respectively" not in sent.lower():
            continue
        order = []
        for rx, quantity, unit in hints:
            m = rx.search(sent)
            if m:
                order.append((m.start(), quantity, unit))
        order.sort()
        vals = re.findall(r"(?<![\w])(?<!\.\d)(?<!\d\.)(%s)(?![\w])(?!\.\d)" % _NUM, sent)
        if len(order) >= 2 and len(vals) >= len(order):
            tail_vals = vals[-len(order):]
            for (_, quantity, unit), v in zip(order, tail_vals):
                add(quantity, unit, value=_f(v), span=sent)

    # ---- the direct "keyword … value" form ----------------------------------------
    # Value resolution is QUANTITY-LOCAL, in a strict order of proximity:
    #   1. inside the matched phrase itself — a hint like "10-40 cycles" carries its own
    #      number (scalar or range), and that number IS the value. Scanning past it is
    #      how "deposited using 10-40 cycles each. The substrate temperature was 200 °C"
    #      once produced cycle_number = 200: the parser skipped the range it had already
    #      matched and consumed the next sentence's unrelated number.
    #   2. the tail after the keyword, WITHIN the same sentence — "an aspect ratio
    #      of ~30" states the keyword first and its value after, but a sentence boundary
    #      ends the statement, and a number beyond it belongs to a different assertion.
    #   3. the head immediately before the keyword ("830 cycles"), same sentence.
    _numrx = r"(?<![\w])(?<!\.\d)(?<!\d\.)(%s)(?![\w])(?!\.\d)" % _NUM

    def _sentence_bounded(seg, from_end=False):
        """Trim a segment at the nearest sentence boundary."""
        parts = re.split(r"(?<=[.;])\s+", seg)
        return parts[-1] if from_end else parts[0]

    for rx, quantity, unit in hints:
        if quantity in claimed:
            continue
        for m in rx.finditer(t):
            span = t[max(0, m.start() - 60):m.end() + 90]
            matched = m.group(0)
            # 1. the value the matched phrase itself carries
            iv = parse_interval(matched)
            ap = approx_value(matched)
            num = re.search(_numrx, matched)
            if iv:
                add(quantity, unit, interval=iv, span=span)
            elif ap and ap["value"] is not None:
                add(quantity, unit, value=ap["value"], approx=True, span=span)
            elif num:
                add(quantity, unit, value=_f(num.group(1)), span=span)
            else:
                # 2. the tail, never across a sentence boundary
                tail = _sentence_bounded(t[m.end():m.end() + 60])
                lead = re.match(r"[^0-9]{0,25}", tail)
                near = tail[:(lead.end() if lead else 0) + 40]
                iv = parse_interval(near)
                ap = approx_value(near)
                num = re.search(_numrx, near)
                if iv:
                    add(quantity, unit, interval=iv, span=span)
                elif ap and ap["value"] is not None:
                    add(quantity, unit, value=ap["value"], approx=True, span=span)
                elif num:
                    add(quantity, unit, value=_f(num.group(1)), span=span)
                else:
                    # 3. the value may sit immediately BEFORE the keyword ("830 cycles")
                    head = _sentence_bounded(t[max(0, m.start() - 40):m.end()],
                                             from_end=True)
                    hm = re.search(_numrx + r"\s*\S{0,12}$", head)
                    if hm:
                        add(quantity, unit, value=_f(hm.group(1)), span=span)
            if quantity in claimed:
                break
    return out


def fmt(cond):
    """One human-readable value string for a repaired condition."""
    if cond.get("value_kind") == "range":
        return "%g–%g %s" % (cond["value_lower"], cond["value_upper"], cond.get("unit") or "")
    if cond.get("value_status") == "REJECTED_UNPHYSICAL":
        return "unresolved (rejected: %s)" % cond.get("superseded_value")
    v = cond.get("value")
    if v is None:
        return "unresolved"
    fv = _f(v)
    s = ("%g" % fv) if fv is not None else str(v)
    if cond.get("value_kind") == "approximate":
        s = "~" + s
    return "%s %s" % (s, cond.get("unit") or "")
