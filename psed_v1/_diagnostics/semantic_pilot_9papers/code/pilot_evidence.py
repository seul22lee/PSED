#!/usr/bin/env python3
"""
pilot_evidence.py — generic evidence extraction for the four-paper semantic pilot.

Everything here reads SOURCE TEXT (figure captions, body text near a figure, the
methods/experimental section) and returns structured evidence with the matched span
preserved. Nothing here knows a DOI, a paper id, or a figure number.

The contract that matters most: a function in this module never asserts identity. It
reports what the source SAYS. `case_identity.py` decides what that means.
"""
import re

# --------------------------------------------------------------- linkage phrases
#: Phrases by which a source explicitly claims that what it is describing is the SAME
#: physical thing as something described elsewhere. Each carries the strength the phrase
#: alone justifies. These are the only phrases that can license a cross-result merge.
EXPLICIT_SAME = [
    (re.compile(r"\bthe same (?:ALD |deposition |process )?run\b", re.I), "same_run"),
    (re.compile(r"\bgrown in (?:one|a|the) single (?:ALD )?run\b", re.I), "same_run"),
    (re.compile(r"\bthe same samples?\b", re.I), "same_sample"),
    (re.compile(r"\bthe same (?:film|films|specimen|specimens|chip|wafer)\b", re.I), "same_sample"),
    (re.compile(r"\bthese (?:same )?(?:film|films|samples?|specimens?)\b", re.I), "same_sample"),
    (re.compile(r"\bthe corresponding (?:film|sample|specimen)\b", re.I), "same_sample"),
    (re.compile(r"\bsamples? (?:described|discussed|reported|shown|presented) above\b", re.I),
     "same_sample"),
    (re.compile(r"\bthe (?:film|sample|specimen)s? (?:described|discussed|reported) "
                r"(?:above|previously|earlier)\b", re.I), "same_sample"),
    (re.compile(r"\bas (?:described|reported|discussed) (?:above|previously|earlier)\b", re.I),
     "same_context"),
]

#: Phrases asserting that two things are DIFFERENT physical realisations. These block a
#: merge of sample/run identity even when the nominal conditions agree.
EXPLICIT_DIFFERENT = [
    (re.compile(r"\breproducibilit\w+ of (?:the )?(?:ALD |deposition )?runs?\b", re.I),
     "different_run"),
    # "run-to-run" only asserts distinct runs when it is not being NEGATED: "grown in the
    # same ALD run to avoid run-to-run variations" says the opposite of what the bare
    # phrase suggests.
    (re.compile(r"(?<!avoid )(?<!without )(?<!free of )(?<!minimi[sz]e )"
                r"(?<!avoid the )\brun[- ]to[- ]run\b", re.I), "different_run"),
    (re.compile(r"\bdifferent (?:ALD |deposition )?runs?\b", re.I), "different_run"),
    (re.compile(r"\bseparate (?:ALD |deposition )?runs?\b", re.I), "different_run"),
    (re.compile(r"\bdifferent (?:chips?|wafers?|samples?|specimens?)\b", re.I),
     "different_sample"),
    (re.compile(r"\bvarious\s+\w*\s*(?:channels?|chips?|samples?|substrates?)\b", re.I),
     "different_sample"),
]

#: Repeat/replicate measurement on ONE specimen — measurement-level, never a new case.
REPEAT_MEASUREMENT = [
    (re.compile(r"\brepeatabilit\w+\b", re.I), "repeat_measurement"),
    (re.compile(r"\brepeated (?:measurement|measurements|scans?)\b", re.I), "repeat_measurement"),
    (re.compile(r"\bwithin[- ](?:chip|wafer|sample)\b", re.I), "repeat_measurement"),
    (re.compile(r"\bconsecutive (?:measurement|scans?)\b", re.I), "repeat_measurement"),
]

# ----------------------------------------------------------------- sample / run ids
#: An explicit specimen designator. Deliberately narrow: it requires the head noun, so a
#: bare number or a figure reference can never become a sample code.
_SAMPLE_HEAD = r"(?:samples?|specimens?|chips?|coupons?|wafers?|substrates?)"
SAMPLE_LIST = re.compile(
    _SAMPLE_HEAD + r"\s+((?:[A-Za-z]?\d{1,3}[A-Za-z]?)(?:\s*,\s*(?:and\s+)?"
    r"(?:[A-Za-z]?\d{1,3}[A-Za-z]?))*(?:\s*,?\s*and\s+(?:[A-Za-z]?\d{1,3}[A-Za-z]?))?)"
    r"(?=\b)", re.I)
SAMPLE_ONE = re.compile(_SAMPLE_HEAD + r"\s+([A-Za-z]?\d{1,3}[A-Za-z]?)(?=\b)", re.I)
#: an author-declared study series letter/number ("Series B", "series E")
SERIES_REF = re.compile(r"\bseries\s+([A-Z]|\d{1,2})\b", re.I)

#: measurement techniques, as the source names them. The value is the canonical label.
TECHNIQUES = [
    (r"\bcyclic voltammetr\w+|\bcyclic voltammogram\w*|\bCV\b", "cyclic_voltammetry"),
    (r"\bimpedance spectroscop\w+|\bimpedance spectra|\bEIS\b", "impedance_spectroscopy"),
    (r"\bX-?ray photoelectron spectroscop\w+|\bXPS\b", "XPS"),
    (r"\bX-?ray diffract\w+|\bXRD\b|\bGIXRD\b", "XRD"),
    (r"\bRutherford backscatter\w+|\bRBS\b", "RBS"),
    (r"\belastic recoil detect\w+|\bERDA?\b", "ERD"),
    (r"\bellipsometr\w+", "ellipsometry"),
    (r"\breflectomet\w+", "reflectometry"),
    (r"\bscanning electron micro\w+|\bSEM\b|\bFESEM\b", "SEM"),
    (r"\btransmission electron micro\w+|\bTEM\b|\bHRTEM\b", "TEM"),
    (r"\benergy[- ]dispersive X-?ray\w*|\bEDS\b|\bEDX\b|\bEDXS\b", "EDS"),
    (r"\bX-?ray (?:count )?map|\bK\s*[aα]\s*X-?ray\b|\belemental map\w*", "xray_map"),
    (r"\batomic force micro\w+|\bAFM\b", "AFM"),
    (r"\bfour[- ]point probe\b|\bsheet resistance\b|\bresistivit\w+", "resistivity"),
    (r"\bquartz crystal microbalance\b|\bQCM\b", "QCM"),
    (r"\bRaman\b", "Raman"),
    (r"\bFT-?IR\b|\binfrared spectroscop\w+", "FTIR"),
    (r"\bgrowth (?:rate )?per cycle\b|\bGPC\b|\bgrowth rate\b", "growth_per_cycle"),
    (r"\bfilm thickness\b|\bthickness\b", "thickness"),
    (r"\bcapacit\w+ (?:response|change)\b|\bcapacitance\b", "capacitance"),
    (r"\bsaturation profile\b", "saturation_profile"),
    (r"\bconformalit\w+|\bstep coverage\b", "conformality"),
    (r"\brefractive index\b", "refractive_index"),
    (r"\bnucleation\b", "nucleation"),
]
TECHNIQUES = [(re.compile(rx, re.I), lab) for rx, lab in TECHNIQUES]

#: An explicit attribution of a figure's data to ANOTHER work. A review article carries
#: one of these on nearly every caption, and the data behind such a figure is an
#: observation imported from the cited work — never a deposition the current paper made.
REPRODUCTION = re.compile(
    r"\b(?:Reproduced|Adapted|Reprinted|Modified|Taken|Redrawn)\b"
    r"(?:\s+and\s+\w+)?\s+(?:with\s+permission\s+)?from\s+"
    r"(?P<src>[^.]{0,160}?)(?:\.\s*Copyright|\.\s*©|\.\s*$|\.)", re.I)
#: A weaker, narrative form: "as reported by Elam et al." The attributed source must look
#: like a WORK, not an instrument — "as measured by in situ spectroscopic ellipsometry" is
#: a method statement, and reading it as an attribution moved a paper's own figure into
#: imported literature. An author surname plus "et al." or a year is the discriminator, and
#: this pattern is deliberately case-SENSITIVE on the surname.
ATTRIBUTION = re.compile(
    r"\bas\s+(?:reported|measured|published|shown|obtained|presented)\s+by\s+"
    r"(?P<src>[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+)?"
    r"(?:\s+et\s+al\.?|\s*\(?(?:19|20)\d{2}\)?))")


def imported_from(text):
    """(source_reference, matched_statement) when the text attributes its data to another
    work, else (None, None).

    The strong form is the copyright line a journal requires on a reproduced figure; the
    weak form is a narrative attribution. Either is the paper telling you the data is not
    its own."""
    for rx in (REPRODUCTION, ATTRIBUTION):
        m = rx.search(text or "")
        if m:
            src = re.sub(r"\s+", " ", m.group("src") or "").strip(" ,;")
            return src[:180], re.sub(r"\s+", " ", m.group(0)).strip()[:240]
    return None, None


#: representation of an underlying measurement, from the panel's own caption clause
REPRESENTATION = [
    (re.compile(r"\bas[-\s]?measured\b", re.I), "as_measured"),
    (re.compile(r"\bnormali[sz]ed\b", re.I), "normalized"),
    (re.compile(r"\bscaled\b", re.I), "scaled"),
    (re.compile(r"\binset\b", re.I), "inset"),
]


def _span(text, m, pad=70):
    a = max(0, m.start() - pad)
    b = min(len(text), m.end() + pad)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def _hits(patterns, text, kind):
    out = []
    for rx, label in patterns:
        for m in rx.finditer(text or ""):
            out.append({"kind": kind, "label": label,
                        "matched": re.sub(r"\s+", " ", m.group(0)).strip(),
                        "span": _span(text, m), "offset": m.start()})
    return out


def linkage_evidence(text):
    """Explicit same/different/repeat statements in one block of source text."""
    return (_hits(EXPLICIT_SAME, text, "explicit_same")
            + _hits(EXPLICIT_DIFFERENT, text, "explicit_different")
            + _hits(REPEAT_MEASUREMENT, text, "repeat_measurement"))


def sample_codes(text):
    """Explicit specimen designators, with the sentence they were read from.

    A list ("samples 4, 5, and 6") yields one record per code, all sharing the span, so
    a caption naming three specimens produces three sample references rather than one
    opaque string."""
    out, seen = [], set()
    for m in SAMPLE_LIST.finditer(text or ""):
        codes = [c.strip() for c in re.split(r"\s*(?:,|and)\s*", m.group(1)) if c.strip()]
        for c in codes:
            key = (c.lower(), m.start())
            if key in seen:
                continue
            seen.add(key)
            out.append({"code": c, "matched": re.sub(r"\s+", " ", m.group(0)).strip(),
                        "span": _span(text, m), "offset": m.start(),
                        "n_in_mention": len(codes)})
    for m in SAMPLE_ONE.finditer(text or ""):
        c = m.group(1).strip()
        if any(o["code"].lower() == c.lower() and abs(o["offset"] - m.start()) < 40 for o in out):
            continue
        out.append({"code": c, "matched": re.sub(r"\s+", " ", m.group(0)).strip(),
                    "span": _span(text, m), "offset": m.start(), "n_in_mention": 1})
    return out


def series_refs(text):
    out, seen = [], set()
    for m in SERIES_REF.finditer(text or ""):
        s = m.group(1).upper()
        if (s, m.start()) in seen:
            continue
        seen.add((s, m.start()))
        out.append({"series": s, "matched": re.sub(r"\s+", " ", m.group(0)).strip(),
                    "span": _span(text, m), "offset": m.start()})
    return out


def techniques(text):
    out, seen = [], set()
    for rx, lab in TECHNIQUES:
        m = rx.search(text or "")
        if m and lab not in seen:
            seen.add(lab)
            out.append({"technique": lab, "matched": re.sub(r"\s+", " ", m.group(0)).strip(),
                        "span": _span(text, m), "offset": m.start()})
    return out


# ------------------------------------------------------------ panel caption clauses
#: One panel marker. Three shapes, all seen in this corpus:
#:   (a)            plain
#:   ( a )          spaced — the shape that loses a whole printed figure downstream
#:   ( a -b ) (a-c) (a and b) (a, b)   a RANGE or LIST covering several panels at once
#: A BARE "c)" marker must not be preceded by a capitalised noun: "Series C)",
#: "Table 1 Series E)" and "Type 1)" are enumerations of that noun, not panel markers,
#: and reading them as panels stole the caption text of the real panels.
_PANEL_MARK = re.compile(
    r"\(\s*(?:panels?\s+)?([a-hA-H])\s*(?:(?:[-–—]|,|and)\s*([a-hA-H])\s*)?\)"
    r"|(?<![A-Za-z0-9])(?<!\bSeries )(?<!\bType )(?<!\bTable )(?<!\bRegion )"
    r"(?<!\bPart )(?<!\bStep )([a-hA-H])\)")
_CAP_NOUN_BEFORE = re.compile(r"\b[A-Z][a-z]{2,}\s+$")


def _letters(a, b):
    if not b:
        return [a.lower()]
    lo, hi = sorted((a.lower(), b.lower()))
    return [chr(c) for c in range(ord(lo), ord(hi) + 1)]


def panel_clauses(caption):
    """{panel_letter: the caption text belonging to that panel}.

    A marker covering several panels ("( a -b ) GPCs (a) and electrical resistivity (b)")
    gives its clause to EVERY panel it names, because the sentence describes all of them.
    The preamble before the first marker is returned under the key '' — it holds the
    conditions the whole figure shares, which must not be attributed to one panel.
    """
    cap = re.sub(r"\s+", " ", caption or "")
    marks = []
    for m in _PANEL_MARK.finditer(cap):
        if m.group(3):
            if _CAP_NOUN_BEFORE.search(cap[:m.start()]):
                continue                      # "Series C)" — an enumeration, not a panel
            marks.append((m.start(), m.end(), [m.group(3).lower()]))
        else:
            marks.append((m.start(), m.end(), _letters(m.group(1), m.group(2))))
    # "(a)-(d)" is ONE range written as two markers joined by a dash. Read as two separate
    # markers it gives panel a the text "-" and panels b and c no text at all, so they
    # silently inherit whatever the whole figure says. Any caption using the
    # "(a)-(c) SEM images ... (d)-(f) TEM images" convention hits this.
    joined, i = [], 0
    while i < len(marks):
        s0, e0, la = marks[i]
        while (i + 1 < len(marks) and len(la) == 1
               and len(marks[i + 1][2]) == 1
               and re.match(r"^\s*[-–—]\s*$", cap[e0:marks[i + 1][0]])):
            la = _letters(la[0], marks[i + 1][2][0])
            e0 = marks[i + 1][1]
            i += 1
        joined.append((s0, e0, la))
        i += 1
    marks = joined
    if not marks:
        return {"": cap}
    out = {"": cap[:marks[0][0]].strip()}
    for i, (s, e, letters) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(cap)
        text = cap[e:end].strip()
        for letter in letters:
            out.setdefault(letter, "")
            out[letter] = (out[letter] + " " + text).strip()
    return out


def representation_of(clause):
    """The representation this panel clause declares, or None.

    `as_measured` is tested first because "as-measured saturation profile" also contains
    no other marker; `normalized` before `scaled` because a normalisation clause often
    also says "scaled" when it names the axis it normalised."""
    for rx, label in REPRESENTATION:
        if rx.search(clause or ""):
            return label, re.sub(r"\s+", " ", rx.search(clause).group(0))
    return None, None
