"""
canonical/conditions.py — ConditionAssertion recovery and scoped binding.

An ASSERTION is "the paper says X somewhere, with this status, over this scope".
A BINDING is "this entity is covered by that scope". They are separate acts: an
assertion is never attached to an entity its own scope does not cover, and a
paper-scope value with several candidates is never broadcast.

Everything here is deterministic and reads only text already in the repository.

Pressure contract (spec):
  * working/process, precursor partial, co-reactant partial, carrier/background,
    apparatus/base, model-input pressures are DIFFERENT quantities;
  * an exposure/dose product (mTorr*s, Pa*s) is NOT a pressure;
  * direct / approximate / estimated / assumed / fitted status is preserved;
  * Mathematical-Italic Unicode is folded before parsing (docling writes p_A as
    U+1D45D U+1D434, which is invisible to an ASCII pattern);
  * species come from the symbol definition or the sentence, never from the
    nearest numeric token.
"""
from __future__ import annotations

import re
from pipeline.canonical import process_steps as PS
from collections import defaultdict

from .schema import SCOPE_ORDER, Status

# --------------------------------------------------------------- unicode folding
#: Degree-sign shapes a PDF extractor emits instead of U+00B0. "250 \u25e6 C" is what a
#: caption reading "250 °C" becomes, and every temperature in a paper typeset that way was
#: invisible to the unit patterns -- a whole figure's process context lost to one glyph.
_DEGREE_LIKE = ("\u25e6", "\u00ba", "\u02da", "\u2218", "\u00b0")


def normalise_degrees(t):
    """Fold degree-sign variants, and close the gap a PDF leaves before the scale letter."""
    if not t:
        return t
    for ch in _DEGREE_LIKE:
        if ch != "\u00b0":
            t = t.replace(ch, "\u00b0")
    # "250 ° C" and "250 °  C" are one token; the space is a typesetting artefact
    return re.sub(r"\u00b0\s+([CFK])\b", "\u00b0\\1", t)


def fold_math(t):
    """Mathematical Alphanumeric Symbols -> ASCII. Without this, `p_A = 325 mTorr`
    is literally `\U0001D45D \U0001D434 = 325 mTorr` and no ASCII pattern matches.

    Degree shapes are folded here too, so every caller of fold_math gets them.
    """
    if not t:
        return t
    t = normalise_degrees(t)
    out = []
    for ch in t:
        c = ord(ch)
        if 0x1D400 <= c <= 0x1D7FF:
            for base, start in ((0x41, 0x1D434), (0x61, 0x1D44E), (0x41, 0x1D400),
                                (0x61, 0x1D41A), (0x41, 0x1D468), (0x61, 0x1D482)):
                if start <= c < start + 26:
                    out.append(chr(base + c - start))
                    break
            else:
                out.append(ch)
        else:
            out.append(ch)
    t = "".join(out)
    return normalize_docling(t)


# docling mangles two glyphs systematically, and both corrupt VALUES:
#   the degree sign becomes a stray digit  -> "300 1 C" / "325 8 C" mean 300/325 °C
#   the minus sign becomes "/C0"           -> "10 /C0 7 mbar" means 1e-7 mbar
# Left unhandled, the first yields the unit "1 C" and the second reads 1e-7 as 7.
_DEG_ARTIFACT = re.compile(r"(?<=\d)\s*[18]\s*C(?=\b|of|at|,|\.)")
# docling also splits decimals across spaces ("0 . 5", "1 . 12") and glues the next
# word to the unit ("325 °Cof substrate temperature"). Both break number parsing.
_SPLIT_DECIMAL = re.compile(r"(\d)\s+\.\s+(\d)")
# ... and renders the micro sign as a bare 'l' ("0.5 l m" is 0.5 µm). Anchored to a
# preceding number so prose letters can never be rewritten.
_MU_ARTIFACT = re.compile(r"(?<=\d)\s*l\s?(m|s|g|L|mol|bar)\b")
# ... and the degree glyph as the ligature "/C14" ("300 /C14 C" is 300 °C)
_DEG_LIGATURE = re.compile(r"(?<=\d)\s*/C14\s*C\b")
_GLUED_WORD = re.compile(r"\b(C|s|nm|mbar|Torr|sccm)(of|at|in|and|with|for)\b")
# "10 /C0 7" is the superscript form of 10^-7. Rewriting it as "10e-7" parses as
# 1e-6 -- a factor of ten too high, which corrupted 62 base-pressure assertions.
# The mantissa form "5 x 10 /C0 3" (5x10^-3) is handled first.
_EXP_MANTISSA = re.compile(r"(\d+(?:\.\d+)?)\s*[x×]\s*10\s*/C0\s*(\d+)")
_EXP_POWER10 = re.compile(r"(?<![\d.])10\s*/C0\s*(\d+)")
_EXP_ARTIFACT = re.compile(r"(\d)\s*/C0\s*(\d+)")
_MINUS_ARTIFACT = re.compile(r"/C0\s*")


def normalize_docling(t):
    if not t:
        return t
    t = _SPLIT_DECIMAL.sub(lambda m: "%s.%s" % (m.group(1), m.group(2)), t)
    t = _EXP_MANTISSA.sub(lambda m: "%se-%s" % (m.group(1), m.group(2)), t)
    t = _EXP_POWER10.sub(lambda m: "1e-%s" % m.group(1), t)
    t = _DEG_ARTIFACT.sub(" °C", t)
    t = _MU_ARTIFACT.sub(lambda m: " µ%s" % m.group(1), t)
    t = _DEG_LIGATURE.sub(" °C", t)
    t = _GLUED_WORD.sub(lambda m: "%s %s" % (m.group(1), m.group(2)), t)
    t = _MINUS_ARTIFACT.sub("-", t)
    return t


NUM = r"[-+]?\d*\.?\d+(?:\s*[x×]\s*10\s*[-–−]?\s*\d+)?(?:[eE][-+]?\d+)?"
PUNIT = r"(?:mTorr|Torr|mbar|hPa|kPa|MPa|Pa|atm|bar)"
TUNIT = r"(?:ms|s|sec|min|h)"

EXPOSURE_RX = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\s*[·⋅*.\s]?\s*(?:s|sec)\b", re.I)
PSYM_RX = re.compile(r"\bp\s*[_ ]?\s*(A0|B0|A|B)\b\s*[=≈]\s*(" + NUM + r")\s*(" + PUNIT + r")", re.I)
PPLAIN_RX = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\b")
SPECIES_DEF = re.compile(r"\(\s*([AB])\s*0?\s*=\s*([A-Za-z0-9][A-Za-z0-9()\-]*)\s*\)")
SPECIES_SENT = re.compile(r"\b([A-Z][A-Za-z0-9]{1,7})\s+(?:partial\s+)?pressure", re.I)

STATUS_RX = [
    (re.compile(r"\b(?:we\s+)?estimat\w+", re.I), "estimated"),
    (re.compile(r"\bassum\w+", re.I), "assumed"),
    (re.compile(r"\bfitt?ed\b|\bfitting\b|\bfit\s+to\b", re.I), "fitted"),
    (re.compile(r"\bderiv\w+|\bcalculated from\b", re.I), "derived"),
    (re.compile(r"\bca\.|\babout\b|approximately|typical\w*|nominal\w*|~", re.I), "approximate"),
]

PRESSURE_KIND = [
    (re.compile(r"base pressure|residual pressure", re.I), "base_pressure", "apparatus"),
    (re.compile(r"process pressure|working pressure|deposition pressure|"
                r"chamber pressure|total pressure|reactor pressure", re.I),
     "working_pressure", "process"),
    (re.compile(r"precursor partial|partial pressure of the precursor", re.I),
     "precursor_partial_pressure", "process"),
    (re.compile(r"co[- ]?reactant partial|oxidant partial", re.I),
     "co_reactant_partial_pressure", "process"),
    (re.compile(r"carrier gas|purge gas|background gas|carrier partial", re.I),
     "carrier_gas_partial_pressure", "process"),
    (re.compile(r"bubbler|delivery line|vapor pressure", re.I), "bubbler_pressure", "apparatus"),
]
MODEL_CONTEXT = re.compile(r"simulat\w+|model(?:l)?ed|model input|parameter values|"
                           r"we estimate|assum\w+", re.I)


def _status(win):
    for rx, s in STATUS_RX:
        if rx.search(win):
            return s
    return "direct"


def _pressure_kind(win, symbol, near=None):
    """`near` is a TIGHT window around the number. A phrase far away in the same
    caption does not type this pressure: a caption naming a carrier gas in one
    clause was re-typing an unrelated process pressure in another."""
    if symbol in ("A", "A0"):
        return "precursor_partial_pressure", "process"
    if symbol in ("B", "B0"):
        return "carrier_gas_partial_pressure", "process"
    for scope_text in (near, win):
        if not scope_text:
            continue
        for rx, kind, ctx in PRESSURE_KIND:
            if rx.search(scope_text):
                return kind, ctx
        if scope_text is near:
            break            # a tight window that says nothing stays generic
    return "generic_pressure", "process"


_NOT_A_SPECIES = {"of", "at", "in", "the", "a", "and", "with", "for", "was", "is"}


def _species(win, symbol):
    """Species from the SYMBOL DEFINITION first, then the sentence. Never the
    nearest numeric token."""
    if symbol:
        for m in SPECIES_DEF.finditer(win):
            if m.group(1).upper() == symbol[0].upper():
                return m.group(2).rstrip(")"), "symbol_definition"
    m = SPECIES_SENT.search(win)
    if m and m.group(1).lower() not in _NOT_A_SPECIES | {"partial", "total", "base",
                                                         "process", "working", "chamber"}:
        return m.group(1), "sentence"
    return None, None


def _reactant_role(kind, symbol):
    if symbol in ("A", "A0") or kind == "precursor_partial_pressure":
        return "precursor", "A"
    if kind == "co_reactant_partial_pressure":
        return "coreactant", "B"
    if symbol in ("B", "B0") or kind == "carrier_gas_partial_pressure":
        return "carrier", "B"
    return None, None


# ============================================================================
def _norm_unit(unit):
    """One spelling per unit, so identity comparisons downstream actually match.

    docling leaves the degree sign detached ("150 ° C") in some captions and
    attached ("150 °C") in others; the same assertion then reaches `bind()` as
    two distinct (value, unit) pairs and escapes specialisation dedup. Only
    whitespace is touched -- no unit is renamed, and raw_evidence keeps the
    original spelling.
    """
    if not isinstance(unit, str):
        return unit
    u = re.sub(r"\s+", " ", unit).strip()
    u = re.sub(r"°\s+(?=[CFK]\b)", "°", u)
    u = re.sub(r"\s*/\s*", "/", u)
    u = re.sub(r"(?<=\S)\s+per\s+(?=\S)", "/", u)   # "Å per cycle" == "Å/cycle"
    return u or None


def assertion(quantity, value, unit, raw, locator, scope, status="direct",
              source_kind="text", evidence_kind="experimental_condition",
              species=None, species_basis=None, reactant_role=None, of_reactant=None,
              step_context=None, activation=None, plasma_type=None, follows=None,
              preceding_species=None, preceding_activation=None, step_evidence=None,
              paper_id=None, figure_index=None, figure_number=None, panel=None,
              series_selector=None, reference_work=None, confidence=0.8,
              ambiguity=None, source_quantity=None):
    return {
        "quantity": quantity, "value": value, "unit": _norm_unit(unit),
        # the source's own word for the quantity, kept when a resolved ALD step
        # specialised the recorded name (pulse_time -> precursor_pulse_time)
        "source_quantity": source_quantity,
        "raw_evidence": raw, "evidence_locator": locator,
        "assertion_status": status,            # direct|approximate|estimated|assumed|fitted|derived
        "source_kind": source_kind,            # caption|legend|body|methods|table|series_label|model
        "evidence_kind": evidence_kind,        # experimental_condition|model_input|literature_condition
        "species": species, "species_basis": species_basis,
        "reactant_role": reactant_role, "of_reactant": of_reactant,
        # WHERE in the ALD cycle this timing belongs. `pulse_time = 2 s` is not an
        # experimental condition until the half-cycle is named, and the two purges of one
        # cycle are only distinguishable through this field.
        "step_context": step_context,
        "activation": activation,               # a property of an EXPOSURE, never a species
        "plasma_type": plasma_type,
        "follows": follows,                     # for a purge: the step it comes after
        "preceding_species": preceding_species,
        "preceding_activation": preceding_activation,
        "step_evidence": step_evidence,
        "paper_id": paper_id,
        "figure_index": figure_index, "figure_number": figure_number,
        "panel": panel, "series_selector": series_selector,
        "reference_work": reference_work,
        "scope": scope,                        # series|panel|figure|method|paper
        "confidence": confidence,
        "ambiguity": ambiguity,
    }


def pressures_from_text(text, scope, source_kind, locator, paper_id=None,
                        figure_index=None, figure_number=None, panel=None,
                        series_selector=None):
    """All pressure and exposure assertions in `text`. Exposure products are typed
    as `exposure`, never as a pressure."""
    text = fold_math(text or "")
    out = []
    exp_spans = []
    for m in EXPOSURE_RX.finditer(text):
        exp_spans.append((m.start(), m.end()))
        win = text[max(0, m.start() - 220): m.end() + 220]
        out.append(assertion(
            "exposure", m.group(1), m.group(2) + "*s",
            " ".join(m.group(0).split()), locator, scope, _status(win), source_kind,
            evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                           else "experimental_condition"),
            paper_id=paper_id, figure_index=figure_index, figure_number=figure_number,
            panel=panel, series_selector=series_selector, confidence=0.85))
    for m in PSYM_RX.finditer(text):
        win = text[max(0, m.start() - 300): m.end() + 300]
        sym = m.group(1).upper()
        kind, ctx = _pressure_kind(win, sym)
        sp, basis = _species(win, sym)
        role, react = _reactant_role(kind, sym)
        out.append(assertion(
            kind, m.group(2), m.group(3), " ".join(m.group(0).split()), locator, scope,
            _status(win), source_kind,
            evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                           else "experimental_condition"),
            species=sp, species_basis=basis, reactant_role=role, of_reactant=react,
            paper_id=paper_id, figure_index=figure_index, figure_number=figure_number,
            panel=panel, series_selector=series_selector, confidence=0.9))
    for m in PPLAIN_RX.finditer(text):
        if any(a <= m.start() < b for a, b in exp_spans):
            continue                                  # part of an exposure product
        win = text[max(0, m.start() - 240): m.end() + 240]
        if not re.search(r"pressure|vacuum|\bp\s*[_ ]?[AB]\b", win, re.I):
            continue
        if PSYM_RX.search(win):
            continue                                  # already captured symbolically
        kind, ctx = _pressure_kind(win, None)
        sp, basis = _species(win, None)
        role, react = _reactant_role(kind, None)
        out.append(assertion(
            kind, m.group(1), m.group(2),
            " ".join(win[200:].split())[:160], locator, scope, _status(win), source_kind,
            evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                           else "experimental_condition"),
            species=sp, species_basis=basis, reactant_role=role, of_reactant=react,
            paper_id=paper_id, figure_index=figure_index, figure_number=figure_number,
            panel=panel, series_selector=series_selector, confidence=0.7))
    return out


# --------------------------------------------------------------- legend/caption
LEGEND_VALUE = re.compile(
    r"(?:^|[\s,(])(?:(?P<sym>[A-Za-z][A-Za-z_0-9]{0,12})\s*[=:]\s*)?"
    r"(?P<num>" + NUM + r")\s*"
    r"(?P<unit>°\s*C|K|" + PUNIT + r"|sccm|cycles?|" + TUNIT + r"|nm|µm|um|μm|mm|%)\b")
UNIT_QUANTITY = [
    (re.compile(r"^°\s*C$|^K$"), "temperature"),
    (re.compile(r"^(?:mTorr|Torr|mbar|hPa|kPa|MPa|Pa|atm|bar)$", re.I), "generic_pressure"),
    (re.compile(r"^sccm$", re.I), "flow_rate"),
    (re.compile(r"^cycles?$", re.I), "cycle_number"),
    (re.compile(r"^(?:ms|s|sec|min|h)$", re.I), "time"),
    (re.compile(r"^(?:nm|µm|um|μm|mm)$", re.I), "length"),
    (re.compile(r"^%$"), "fraction"),
]
# a series axis NAMES the quantity; the label carries its value
AXIS_QUANTITY = [
    (re.compile(r"hot[- ]?wire", re.I), "hot_wire_temperature"),
    (re.compile(r"substrate\s+temperatur", re.I), "deposition_temperature"),
    (re.compile(r"pulse", re.I), "pulse_time"),
    (re.compile(r"purge", re.I), "purge_time"),
    # "dose" resolves to NEITHER the pulse nor the exposure family: the literature uses
    # it for both physical durations, so a dose-worded axis keeps the unresolved dose
    # kind. Folding it into "exposure" (the old behaviour) or into "pulse" would both
    # invent an equivalence the source never stated.
    (re.compile(r"dos(?:e|ing)", re.I), "dose_time"),
    (re.compile(r"plasma", re.I), "exposure"),
    (re.compile(r"temperatur", re.I), "deposition_temperature"),
    (re.compile(r"pressure", re.I), "generic_pressure"),
    (re.compile(r"cycle", re.I), "cycle_number"),
    (re.compile(r"exposure|soak|dwell", re.I), "exposure"),
    (re.compile(r"flow", re.I), "flow_rate"),
    (re.compile(r"height|opening", re.I), "feature_height"),
    (re.compile(r"width", re.I), "feature_width"),
    (re.compile(r"length", re.I), "feature_length"),
    (re.compile(r"aspect", re.I), "aspect_ratio"),
    (re.compile(r"thickness", re.I), "film_thickness"),
]


# units whose quantity is unambiguous even without a naming phrase
_SELF_TYPING_UNITS = re.compile(r"^(?:°\s*C|K|sccm|cycles?)$", re.I)


def quantity_for(series_axis, unit, symbol=None):
    """Quantity of a legend value.

    The SERIES AXIS names the quantity. A bare unit types the value only when the
    unit itself is unambiguous (°C, K, sccm, cycles). A bare 'nm' or 's' does NOT:
    emitting a generic `length`/`time` for it duplicated properly-typed assertions
    and crowded the binding, so it is refused."""
    if series_axis:
        for rx, q in AXIS_QUANTITY:
            if rx.search(series_axis):
                return q, "series_axis"
    u = (unit or "").strip()
    if _SELF_TYPING_UNITS.match(u):
        for rx, q in UNIT_QUANTITY:
            if rx.match(u):
                return q, "unit"
    return None, None


def from_series_label(label, series_axis, **prov):
    """Conditions stated in a curve's own label — the narrowest possible scope.

    A series axis that NAMES A REACTANT binds it: an axis called "TMA pulse time"
    makes its values pulse times OF TMA, which is what the caption asserts and what
    a recipe needs."""
    out = []
    axis_species = _species_in(series_axis or "")
    for m in LEGEND_VALUE.finditer(fold_math(label or "")):
        q, basis = quantity_for(series_axis, m.group("unit"), m.group("sym"))
        if not q:
            continue
        sp = axis_species if q in ("pulse_time", "dose_time", "purge_time",
                                   "flow_rate", "exposure",
                                   "partial_pressure") else None
        # the half-cycle this timing belongs to, from the axis wording and any species the
        # axis already names. A species never decides the position on its own.
        step = PS.describe_step(series_axis or label, species=sp) \
            if q in ("pulse_time", "dose_time", "purge_time", "exposure") else {}
        role, react = (("precursor", "A")
                       if sp and q in ("pulse_time", "dose_time", "exposure")
                       else (None, None))
        if step.get("step_context") in PS.EXPOSURE_STEPS:
            role = ("precursor" if step["step_context"] == PS.PRECURSOR_EXPOSURE
                    else "coreactant")
            react = "A" if role == "precursor" else "B"
        # The resolved step SPECIALISES the quantity without changing its family: a
        # pulse time whose step is the precursor exposure is a precursor_pulse_time.
        # It is never renamed into an exposure time -- delivery duration and contact
        # duration are different measurements, and the axis said which one it plots.
        q_out = q
        if (step.get("step_context") and PS.timing_side(q)
                and PS.timing_side(q) == PS.step_side(step["step_context"])):
            q_out = PS.specialize_timing_quantity(q, step["step_context"])
        out.append(assertion(q_out, m.group("num"), m.group("unit").replace(" ", ""),
                             " ".join(m.group(0).split()),
                             "series label %r (axis %r)" % (label, series_axis),
                             "series", "direct", "series_label",
                             source_quantity=(q if q_out != q else None),
                             step_context=step.get("step_context"),
                             activation=step.get("activation"),
                             plasma_type=step.get("plasma_type"),
                             follows=step.get("follows"),
                             preceding_species=step.get("preceding_species"),
                             preceding_activation=step.get("preceding_activation"),
                             step_evidence=step.get("evidence"),
                             species=sp, species_basis=("series_axis" if sp else None),
                             reactant_role=role, of_reactant=react,
                             series_selector=label, confidence=0.9, **prov))
    return out


_PANEL_CLAUSE = re.compile(r"\(\s*([a-h])\s*\)", re.I)


def caption_panel_clauses(caption):
    """Split a multi-panel caption into {panel_letter: clause}.

    A caption that says "(a) different TMA pulse times ... (b) purge times" states
    DIFFERENT conditions for different panels. Treating the whole caption as one
    figure-scope blob leaked panel (a)'s pulse times onto panel (b)."""
    cap = fold_math(caption or "")
    marks = list(_PANEL_CLAUSE.finditer(cap))
    if len(marks) < 2:
        return {}, cap
    out, first = {}, cap[:marks[0].start()]
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(cap)
        out[m.group(1).lower()] = cap[m.start():end]
    return out, first


def from_caption(caption, series_axis=None, **prov):
    """Numeric conditions stated in a caption — figure scope."""
    out = []
    cap = fold_math(caption or "")
    for m in LEGEND_VALUE.finditer(cap):
        sym, unit = m.group("sym"), m.group("unit")
        q, basis = quantity_for(None, unit, sym)
        if sym:
            for rx, qq in AXIS_QUANTITY:
                if rx.search(sym):
                    q = qq
                    break
        if not q:
            continue
        win = cap[max(0, m.start() - 160): m.end() + 160]
        out.append(assertion(q, m.group("num"), unit.replace(" ", ""),
                             " ".join(m.group(0).split()), "figure caption", "figure",
                             _status(win), "caption",
                             evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                                            else "experimental_condition"),
                             confidence=0.8, **prov))
    return out


# ------------------------------------------------------------ prose conditions
# A GOVERNING PHRASE types a number; a bare "<num> <unit>" does not. This is what
# separates "the process pressure was ca. 3 hPa" (working_pressure) from any other
# pressure-united number, and "100 sccm of H2" (flow of H2) from "50 sccm WF6-carrier".
PROSE_RULES = [
    # (phrase regex, quantity, unit group kind, species group index or None)
    (r"(?:process|working|deposition|chamber|reactor|total)\s+pressure[^.;,]{0,40}?"
     r"(?:was|of|at|=|~|ca\.?)?\s*(NUM)\s*(PUNIT)", "working_pressure", None),
    (r"base\s+pressure[^.;,]{0,30}?(NUM)\s*(PUNIT)", "base_pressure", None),
    (r"(?:substrate|deposition|growth|sample)\s+temperature[^.;,]{0,40}?"
     r"(?:was|of|at|=|~|ca\.?)?\s*(NUM)\s*(TUNIT_T)", "deposition_temperature", None),
    # A process statement often names its chemistry between the verb and the value --
    # "carried out using HDMP and O2 ... , respectively, at 300 C". Requiring the value to
    # follow the verb immediately lost every such sentence. A bounded clause is allowed in
    # between; it may not cross a sentence boundary, and the quantifier is lazy so the
    # FIRST stated temperature wins and the pattern can never reach past one value to a
    # later, different one.
    (r"(?:grown|deposited|performed|carried out)\s+(?:(?:(?!\bat\b)[^.;]){0,120}?\s)?at\s*"
     r"(?:ca\.?|about|~)?\s*(NUM)\s*(TUNIT_T)", "deposition_temperature", None),
    # gapped coordination elides the verb of the SECOND chemistry's clause --
    # "Al2O3 was grown from TMA and H2O at 300 C and TiO2 from TiCl4 and H2O at
    # 110 C" -- so a deposition-chemistry clause ("from <reagents> at <T>") types
    # its temperature with or without its own verb
    (r"\bfrom\s+(?:(?!\bat\b)[^.;]){0,80}?\bat\s*(?:ca\.?|about|~)?\s*(NUM)\s*(TUNIT_T)",
     "deposition_temperature", None),
    (r"hot[- ]?wire\s+temperature[^.;,]{0,40}?(?:was|of|at|=|~)?\s*(NUM)\s*(TUNIT_T)",
     "hot_wire_temperature", None),
    (r"(NUM)\s*(TUNIT_T)\s+of\s+(?:the\s+)?hot[- ]?wire", "hot_wire_temperature", None),
    (r"(NUM)\s*(TUNIT_T)\s*of\s+substrate\s+temperature", "deposition_temperature", None),
    (r"(NUM)\s*()(?:ALD\s+)?cycles\b", "cycle_number", None),
    (r"(?:number of|typically|made in)[^.;,]{0,20}?(NUM)\s*()cycles", "cycle_number", None),
    (r"(?:flow rate[^.;,]{0,25}?of\s*)?(NUM)\s*(sccm)\b(?:\s*of\s+([A-Za-z][A-Za-z0-9]{0,6}))?",
     "flow_rate", 3),
    (r"(NUM)\s*(sccm)\s*(?:of\s+|\s+)?[A-Za-z][A-Za-z0-9]{0,6}\s*[- ]\s*carrier\s+gas\s*"
     r"\(\s*([A-Za-z][A-Za-z0-9]{0,6})\s*\)", "flow_rate", 3),
    (r"[A-Za-z][A-Za-z0-9]{0,6}[- ]carrier\s+gas\s*\(\s*([A-Za-z][A-Za-z0-9]{0,6})\s*\)"
     r"[^.;,]{0,20}?(NUM)\s*(sccm)", "flow_rate", 1),
    (r"(?:purge|purging)[^.;,]{0,30}?(NUM)\s*(TUNIT)", "purge_time", None),
    (r"(NUM)\s*(TUNIT)[- ]?(?:long\s+)?purge", "purge_time", None),
    (r"(?:pulse|dose|exposure)[^.;,]{0,30}?(?:time|length)?[^.;,]{0,10}?(NUM)\s*(TUNIT)",
     "pulse_time", None),
    (r"(NUM)\s*(TUNIT)[- ]?(?:long\s+)?(?:exposure|pulse)\s+to\s+"
     r"([A-Za-z][A-Za-z0-9]{0,6})", "pulse_time", 3),
    # a qualifier may sit between the structure word and the dimension word
    # ("channel GAP height", "trench TOP width"); two words bound the reach
    (r"(?:channel|feature|trench|cavity)\s+(?:\w+\s+){0,2}?height[^.;,]{0,30}?(NUM)\s*(LUNIT)",
     "feature_height", None),
    (r"(?:channel|feature|structure)\s+(?:\w+\s+){0,2}?length[^.;,]{0,30}?(NUM)\s*(LUNIT)",
     "feature_length", None),
    (r"(?:channel|feature|trench)\s+(?:\w+\s+){0,2}?width[^.;,]{0,30}?(NUM)\s*(LUNIT)",
     "feature_width", None),
    # the reversed statement order: "the length L of the channel was 1 mm"
    (r"\bheight(?:\s+[A-Za-z])?\s+of\s+the\s+(?:channel|feature|trench|cavity)"
     r"[^.;,]{0,30}?(NUM)\s*(LUNIT)", "feature_height", None),
    (r"\blength(?:\s+[A-Za-z])?\s+of\s+the\s+(?:channel|feature|structure)"
     r"[^.;,]{0,30}?(NUM)\s*(LUNIT)", "feature_length", None),
    (r"\bwidth(?:\s+[A-Za-z])?\s+of\s+the\s+(?:channel|feature|trench)"
     r"[^.;,]{0,30}?(NUM)\s*(LUNIT)", "feature_width", None),
    # a stated aspect ratio is a geometry condition; dimensionless
    (r"aspect\s+ratio[^.;,]{0,15}?(?:of|=|:|~)?\s*(NUM)()",
     "aspect_ratio", None),
    (r"(?:growth per cycle|GPC)[^.;,]{0,30}?(NUM)\s*(GUNIT)", "growth_per_cycle", None),
    # symbol forms used when a paper defines its geometry inline: "(d = 0.5 um, L = 5000 um)"
    (r"\bd\s*=\s*(NUM)\s*(LUNIT)", "feature_height", None),
    (r"\bL\s*=\s*(NUM)\s*(LUNIT)", "feature_length", None),
    (r"\bH\s*=\s*(NUM)\s*(LUNIT)", "feature_height", None),
    (r"\bw\s*=\s*(NUM)\s*(LUNIT)", "feature_width", None),
    (r"(NUM)\s*(GUNIT)\s*(?:/|per\s+)?\s*cycle", "growth_per_cycle", None),
    # value-before-phrase forms: "0.01 mbar of pressure", "1-min exposure to WF6",
    # "2-min purge", "100 sccm of H2" -- the standard caption style
    (r"(NUM)\s*(PUNIT)\s+of\s+(?:the\s+)?pressure", "working_pressure", None),
    (r"(NUM)\s*[- ]\s*(min|s|ms)\s+(?:long\s+)?(?:exposure|pulse)\s+to\s+"
     r"([A-Za-z][A-Za-z0-9-]{0,6})", "pulse_time", 3),
    (r"(NUM)\s*[- ]\s*(min|s|ms)\s+(?:long\s+)?purge", "purge_time", None),
    (r"(NUM)\s*(sccm)\s+of\s+([A-Za-z][A-Za-z0-9]{0,6})", "flow_rate", 3),
    (r"(?:with a )?GPC of\s*(NUM)\s*(GUNIT)", "growth_per_cycle", None),
]
_LUNIT = r"(?:nm|µm|um|μm|mm|cm|m)\b"
_GUNIT = r"(?:Å|A|nm|pm)\s*(?:/|per\s+)?\s*cycle|Å|nm"
_TUNIT_T = r"(?:°\s*C|1\s*C|K)\b"


def _compile_prose():
    out = []
    for pat, q, sp in PROSE_RULES:
        rx = (pat.replace("NUM", NUM).replace("PUNIT", PUNIT)
                 .replace("TUNIT_T", _TUNIT_T).replace("TUNIT", TUNIT)
                 .replace("LUNIT", _LUNIT).replace("GUNIT", _GUNIT))
        out.append((re.compile(rx, re.I), q, sp))
    return out


_PROSE = _compile_prose()
_REACTANT_OF = re.compile(r"\b(TMA|DEZ|H2O|H2S|O3|O2|NH3|N2|Ar|H2|WF6|TiCl4|TEMAZ|"
                          r"at-H|MoCl2O2)\b", re.I)
# papers name gases in words; the species must resolve to the same token either way
_SPECIES_WORD = {"nitrogen": "N2", "argon": "Ar", "hydrogen": "H2", "oxygen": "O2",
                 "ozone": "O3", "water": "H2O", "ammonia": "NH3",
                 "trimethylaluminum": "TMA", "trimethylaluminium": "TMA",
                 "atomic hydrogen": "at-H"}
_SPECIES_WORD_RX = re.compile(r"\b(%s)\b" % "|".join(sorted(_SPECIES_WORD, key=len,
                                                            reverse=True)), re.I)


def _species_in(text):
    m = _REACTANT_OF.search(text or "")
    if m:
        return m.group(1)
    m = _SPECIES_WORD_RX.search(text or "")
    return _SPECIES_WORD[m.group(1).lower()] if m else None


# A number inside a RANGE or a CAPABILITY statement is not a setting. Taking one
# endpoint of "temperatures ranging between 200 and 325 C" as the growth temperature
# is the same defect that once put a fabricated temperature on 278 experiments.
_RANGE_CUE = re.compile(
    r"\b(?:rang\w+|between|from\s+\d|window|varied\s+(?:from|between)|"
    r"\d\s*(?:-|–|to)\s*\d)", re.I)
_CAPABILITY_CUE = re.compile(
    r"\b(?:can reach|up to|as (?:high|low) as|maximum(?: of)?|minimum(?: of)?|"
    r"capable of|limited to|at most|at least)\b", re.I)


def _is_range_or_capability(window, matched):
    """True when the matched number is an endpoint of a range or a capability claim."""
    if _CAPABILITY_CUE.search(window):
        return "capability_statement"
    # a range cue must sit close to the number, not anywhere in the window
    near = window[max(0, len(window) // 2 - 90): len(window) // 2 + 90]
    if _RANGE_CUE.search(near) and not re.search(r"\bwas\b|\bof\b\s*$", matched):
        return "range_endpoint"
    return None


def _in_chemical_formula(text, m, num, unit):
    """True when the matched number+unit is really formula stoichiometry.

    Governing-phrase windows are permissive by design (a phrase may sit up to
    ~30 characters from its value), which lets a precursor formula inside the
    window supply the number: "dose times [Mo(iPrCp)2H2]" yields '2' + 'H' and
    a pulse time of two HOURS. The tell is purely typographic and
    paper-independent -- in a formula the digit and the element symbol abut
    other formula characters, whereas a real setting is delimited by
    whitespace or punctuation:

        ...PrCp)2H2...   digit preceded by ')' , symbol followed by a digit
        ...for 2 h...    digit preceded by space, symbol followed by space

    Only single-letter element-like units can be captured this way, so the
    check is restricted to them; 'ms', 'min', 'sccm', 'mbar' cannot occur as a
    formula fragment.
    """
    if not unit or len(unit.strip()) > 1:
        return False
    span = m.group(0)
    i = span.find(num)
    if i < 0:
        return False
    start = m.start() + i
    before = text[start - 1] if start > 0 else " "
    j = text.find(unit.strip(), start + len(num))
    if j < 0 or j - (start + len(num)) > 1:
        return False
    after = text[j + 1] if j + 1 < len(text) else " "
    return (before.isalpha() or before in ")]}") or after.isdigit()



# --------------------------------------------- coordinated timing statements
# The standard methods idiom states BOTH step durations in one clause:
#     "the AlMe3 pulse and purge times were 0.1 and 4.0 s, respectively"
#     "0.1 and 4.0 s H2O pulse and purge steps"
# Single-value phrase rules cannot read it: the first number carries no unit of
# its own, and the decimal point blocks their gap classes. The values distribute
# over the kind words IN ORDER ("purge and pulse" reverses them) -- ordinary
# English coordination, no quantity or paper named. Only the words pulse/purge
# participate: dose/exposure wordings keep their own timing semantics and are
# never rewritten into this pair.
_COORD_KIND = {"pulse": "pulse_time", "purge": "purge_time"}
_COORD_TIMING = [
    # phrase first: [species] pulse and purge times were|of A and B <unit>
    re.compile(r"(?:(?P<sp>[A-Za-z][A-Za-z0-9()]{1,12})\s+)?"
               r"(?P<k1>pulse|purge)\s+and\s+(?P<k2>pulse|purge)\s+"
               r"(?:times?|lengths?|durations?)\s*(?:were|are|of|was|:|=)?\s*"
               r"(?:also\s+)?(?P<v1>NUM)\s+and\s+(?P<v2>NUM)\s*(?P<u>TUNIT)\b",
               re.I),
    # values first: A and B <unit> [species] pulse and purge steps
    re.compile(r"(?P<v1>NUM)\s+and\s+(?P<v2>NUM)\s*(?P<u>TUNIT)\s+"
               r"(?:(?P<sp>[A-Za-z][A-Za-z0-9()]{1,12})\s+)?"
               r"(?P<k1>pulse|purge)\s+and\s+(?P<k2>pulse|purge)\s+"
               r"(?:steps?|times?|sequences?)\b", re.I),
]
_COORD_TIMING = [re.compile(rx.pattern.replace("NUM", NUM).replace("TUNIT", TUNIT),
                            re.I) for rx in _COORD_TIMING]


def _coordinated_timing(text, scope, source_kind, locator, **prov):
    """Assertions from coordinated pulse/purge statements, plus their spans."""
    out, spans = [], []
    for rx in _COORD_TIMING:
        for m in rx.finditer(text):
            k1, k2 = m.group("k1").lower(), m.group("k2").lower()
            if k1 == k2:
                continue                     # "pulse and pulse" states no pair
            sp = m.group("sp")
            if sp and not (_REACTANT_OF.fullmatch(sp) or _species_in(sp)
                           or re.fullmatch(r"[A-Z][A-Za-z0-9()]{1,11}", sp)):
                sp = None                    # an article or verb is not a species
            if sp and sp.lower() in ("the", "and", "with", "were", "reactant",
                                     "both", "each", "for", "its", "their"):
                sp = None
            ev = " ".join(m.group(0).split())[:160]
            for kind, val in ((k1, m.group("v1")), (k2, m.group("v2"))):
                out.append(assertion(
                    _COORD_KIND[kind], val, m.group("u"), ev, locator, scope,
                    _status(text[max(0, m.start() - 70):m.end() + 30]), source_kind,
                    evidence_kind=("model_input" if MODEL_CONTEXT.search(
                        text[max(0, m.start() - 160):m.end() + 160])
                        else "experimental_condition"),
                    species=sp, species_basis=("phrase" if sp else None),
                    confidence=0.85, **prov))
            spans.append((m.start(), m.end()))
    return out, spans


def conditions_from_prose(text, scope, source_kind, locator, **prov):
    """Every condition a governing phrase types, from methods/body prose.

    A bare '<number> <unit>' is deliberately NOT extracted: without a governing
    phrase there is no evidence of what the number is, and inventing a quantity for
    it is exactly the guessing this pipeline must not do."""
    text = fold_math(text or "")
    out, seen = [], {}
    coord, coord_spans = _coordinated_timing(text, scope, source_kind, locator, **prov)
    out.extend(coord)
    for rx, q, sp_idx in _PROSE:
        for m in rx.finditer(text):
            if any(a0 <= m.start() < b0 or a0 < m.end() <= b0
                   for a0, b0 in coord_spans):
                continue      # this clause was read as a coordinated pair already
            g = m.groups()
            num = next((x for x in g if x and re.fullmatch(NUM, x.strip())), None)
            if num is None:
                continue
            unit = None
            for x in g:
                if x and x.strip() and not re.fullmatch(NUM, x.strip()) and len(x.strip()) <= 12:
                    unit = x.strip()
                    break
            if q == "cycle_number":
                unit = "cycle"
            if q == "growth_per_cycle" and unit and "cycle" not in unit.lower():
                unit = unit + "/cycle"      # a GPC is per cycle by definition
            win = text[max(0, m.start() - 160): m.end() + 160]
            status_win = text[max(0, m.start() - 70): m.end() + 30]
            bad = _is_range_or_capability(win, m.group(0))
            if bad:
                continue          # not a setting; do not assert a value the paper never claims
            if _in_chemical_formula(text, m, num, unit):
                continue          # a stoichiometric subscript, not a measured value
            species = None
            if sp_idx and len(g) >= sp_idx and g[sp_idx - 1]:
                cand = g[sp_idx - 1].strip()
                if _REACTANT_OF.fullmatch(cand):
                    species = cand
            if q == "flow_rate" and species is None:
                # "<gas>-carrier gas (<species>)" -> the flowing species is in the
                # parentheses, never the gas being carried
                cm = re.search(r"[- ]\s*carrier\s+gas\s*\(\s*([A-Za-z][A-Za-z0-9]{0,6})\s*\)",
                               text[m.start(): m.end() + 45], re.I)
                if cm:
                    species = cm.group(1)
            if species is None and q == "deposition_temperature":
                # a chemistry clause types its own temperature ("from TiCl4 and
                # H2O at 110 C"); the reagent it names is what later
                # distinguishes same-scope values of two recipes
                species = _species_in(m.group(0))
            if species is None and q in ("pulse_time", "flow_rate"):
                # the match first; then a SHORT backward window, because a gas is
                # named just before its flow ("Nitrogen ... flow rate of 150 sccm").
                # Widening further attributed a neighbouring gas to the wrong value
                # ("50 sccm WF6-carrier gas (Ar)" was read as H2), so it is bounded.
                species = _species_in(m.group(0)) or _species_in(
                    text[max(0, m.start() - 45): m.end()])
            # a purge is not performed "on" a species unless the phrase says so;
            # taking one from the surrounding sentence invented a reactant binding
            if q == "purge_time" and species and not _species_in(m.group(0)):
                species = None
            in_match = _species_in(m.group(0)) is not None
            key = (q, str(num), str(unit))
            span = (m.start(), m.end())
            prev = None
            for cand in seen.get(key, []):
                a0, b0 = cand["span"]
                if span[0] < b0 and a0 < span[1]:      # spans overlap -> one condition
                    prev = cand
                    break
            if prev is not None:
                # same quantity+value from an OVERLAPPING span: one condition. A
                # species read from inside the match beats one read from the window;
                # two different in-match species means the text is ambiguous, so the
                # species is dropped rather than guessed.
                if in_match and not prev["in_match"]:
                    prev["assertion"]["species"] = species
                    prev["assertion"]["species_basis"] = "phrase"
                    prev["in_match"] = True
                elif in_match and prev["in_match"] and prev["assertion"].get("species") != species:
                    prev["assertion"]["species"] = None
                    prev["assertion"]["species_basis"] = None
                    prev["assertion"]["ambiguity"] = (
                        "two species named in the same span; none attributed")
                continue
            a = assertion(
                q, num, unit, " ".join(m.group(0).split())[:160], locator, scope,
                _status(status_win), source_kind,
                evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                               else "experimental_condition"),
                species=species, species_basis=("phrase" if species else None),
                confidence=0.85, **prov)
            seen.setdefault(key, []).append(
                {"assertion": a, "in_match": in_match, "span": span})
            out.append(a)
    return out


# ------------------------------------------------- reference-scoped assertions
# Papers state adopted/estimated inputs per CITED WORK, not per figure:
#   "For Ylilammi et al. [9] ... we estimate p_A = 325 mTorr; for Arts et al. [13],
#    t_p = 0.4 s"
# Such a sentence is nowhere near a "Fig. N" mention, so proximity cannot find it.
# Its scope is carried by the REFERENCE NAME, which is exactly what the figure's
# series labels contain ("Ylilammi 2018", "Arts 2019"). Bind by that.
REF_MENTION = re.compile(
    r"\b([A-Z][a-z]{2,}(?:\s+and\s+[A-Z][a-z]{2,})?)\s*(?:et al\.?)?\s*\[\s*[\d,\s]+\]")
# how far back a value may look for the reference that governs it
_REF_WINDOW = 240


def _nearest_reference(text, pos):
    """The cited work governing a value at `pos`.

    Sentence splitting cannot be used here: the construct is
    "For X et al. [9] ..., we estimate p_A = 325 mTorr ; for Y et al. [13], t_p = 0.4 s"
    and every naive splitter breaks on 'et al.' and on decimal points. Instead take
    the NEAREST PRECEDING reference mention, and refuse if another reference sits
    between it and the value (which would make the attribution ambiguous)."""
    best = None
    for m in REF_MENTION.finditer(text, 0, pos):
        best = m
    if best is None or pos - best.end() > _REF_WINDOW:
        return None, None
    between = text[best.end():pos]
    if REF_MENTION.search(between):
        return None, "another reference mention lies between the citation and the value"
    return re.sub(r"\s+", " ", best.group(1)).strip(), None


def reference_scoped_assertions(document, paper_id=None):
    """Assertions whose applicability is given by a CITED WORK rather than a figure.

    Papers state adopted/estimated inputs per reference, far from any "Fig. N"
    mention, so proximity to a figure cannot find them. The governing scope is the
    reference name, which is exactly what the figure's series labels carry
    ("Ylilammi 2018", "Arts 2019", "Yim and Ylivaara 2020")."""
    doc = fold_math(document or "")
    if not REF_MENTION.search(doc):
        return []
    out = []

    def emit(a, pos):
        ref, why = _nearest_reference(doc, pos)
        if ref:
            a["reference_work"] = ref
            a["series_selector"] = ref
            a["scope"] = "series"
            out.append(a)
        elif why:
            a["reference_work"] = None
            a["ambiguity"] = why
            a["scope"] = "figure"
            out.append(a)

    for m in PSYM_RX.finditer(doc):
        win = doc[max(0, m.start() - 300): m.end() + 300]
        sym = m.group(1).upper()
        kind, _ = _pressure_kind(win, sym)
        sp, basis = _species(win, sym)
        role, react = _reactant_role(kind, sym)
        emit(assertion(kind, m.group(2), m.group(3), " ".join(m.group(0).split()),
                       "reference-scoped statement in document.md", "series",
                       _status(win), "body",
                       evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                                      else "literature_condition"),
                       species=sp, species_basis=basis, reactant_role=role,
                       of_reactant=react, paper_id=paper_id, confidence=0.8), m.start())
    for m in EXPOSURE_RX.finditer(doc):
        win = doc[max(0, m.start() - 240): m.end() + 240]
        emit(assertion("exposure", m.group(1), m.group(2) + "*s",
                       " ".join(m.group(0).split()),
                       "reference-scoped statement in document.md", "series",
                       _status(win), "body",
                       evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                                      else "literature_condition"),
                       paper_id=paper_id, confidence=0.8), m.start())
    for m in LEGEND_VALUE.finditer(doc):
        sym, unit = m.group("sym"), m.group("unit")
        q = None
        if sym:
            if re.fullmatch(r"t\s*_?\s*p", sym, re.I):
                q = "pulse_time"
            else:
                for rx, qq in AXIS_QUANTITY:
                    if rx.search(sym):
                        q = qq
                        break
        if not q:
            continue
        win = doc[max(0, m.start() - 200): m.end() + 200]
        emit(assertion(q, m.group("num"), unit.replace(" ", ""),
                       " ".join(m.group(0).split()),
                       "reference-scoped statement in document.md", "series",
                       _status(win), "body",
                       evidence_kind=("model_input" if MODEL_CONTEXT.search(win)
                                      else "literature_condition"),
                       paper_id=paper_id, confidence=0.75), m.start())
    # governing-phrase conditions stated for a cited work: a sentence such as
    # "Arts et al. [13] report film thicknesses in trench-like structures
    #  (d = 0.5 um, L = 5000 um) ... after 400 ALD cycles with a GPC of 1.12 A"
    # names no figure at all, so only the reference anchor can place it.
    for a in conditions_from_prose(doc, "series", "body",
                                   "reference-scoped statement in document.md",
                                   paper_id=paper_id):
        pos = doc.find(a["raw_evidence"][:24]) if a.get("raw_evidence") else -1
        if pos >= 0:
            a["evidence_kind"] = "literature_condition"
            emit(a, pos)
    return out


# ------------------------------------------------------------------- binding
def _chem_key(label):
    """Chemical identity of a reagent spelling, via the ontology alias table."""
    from pipeline.canonical import chemical_identity as _CI
    return _CI.identity_key(str(label or ""))


def bind(assertions, entity, figure_varied_quantities=()):
    """Which assertions actually cover this entity, narrowest scope first.

    Returns (bound, ambiguous, unbound). An assertion whose scope names a figure /
    panel / series different from the entity's is NEVER bound. Conflicting
    candidates at the winning scope are returned as `ambiguous` and bound to
    nothing — never resolved by list order.

    `figure_varied_quantities` are the quantities some panel/series of this figure
    VARIES. A figure-scope value of such a quantity cannot be the figure's common
    value — it is one panel's setting — so it is withheld rather than broadcast
    onto the other panels."""
    applicable = []
    for a in assertions:
        if a.get("figure_index") and entity.get("fig_docling_index") and \
                str(a["figure_index"]) != str(entity["fig_docling_index"]):
            continue
        if a.get("panel") and entity.get("panel") and str(a["panel"]) != str(entity["panel"]):
            continue
        sel, lab = a.get("series_selector"), entity.get("source_series")
        if sel and lab:
            # exact label match, or a reference-name selector contained in the label
            if not (sel == lab or (a.get("reference_work") and sel in lab)):
                continue
        applicable.append(a)

    # Quantities that are PER SPECIES/REACTANT are keyed by it. Otherwise the
    # H2, WF6 and Ar flows of one reactor collapse into a single `flow_rate` and
    # look like a three-way conflict about one number.
    _PER_SPECIES = {"flow_rate", "pulse_time", "purge_time", "partial_pressure",
                    "precursor_partial_pressure", "co_reactant_partial_pressure",
                    "carrier_gas_partial_pressure", "exposure"}

    def _key(a):
        if a["quantity"] in _PER_SPECIES and (a.get("species") or a.get("of_reactant")):
            return (a["quantity"], a.get("species") or a.get("of_reactant"))
        return (a["quantity"], None)

    by_q = defaultdict(list)
    for a in applicable:
        by_q[_key(a)].append(a)

    # A generic quantity whose SPECIALISATION carries the same value at the same
    # scope is a duplicate of it ("temperature 300 C" beside "deposition_temperature
    # 300 C"; "generic_pressure 0.01 mbar" beside "working_pressure 0.01 mbar").
    # Keep the specific one; the generic adds no information and crowds the record.
    _SPECIALISES = {"temperature": {"deposition_temperature", "hot_wire_temperature"},
                    "generic_pressure": {"working_pressure", "base_pressure",
                                         "precursor_partial_pressure",
                                         "co_reactant_partial_pressure",
                                         "carrier_gas_partial_pressure",
                                         "bubbler_pressure"},
                    "time": {"pulse_time", "purge_time", "exposure"},
                    "length": {"feature_height", "feature_width", "feature_length"}}
    _vals_by_q = defaultdict(set)
    for a in applicable:
        _vals_by_q[a["quantity"]].add((str(a["value"]), str(a["unit"])))
    for generic, specifics in _SPECIALISES.items():
        gk = [k for k in by_q if k[0] == generic]
        for k in gk:
            covered = set()
            for sp in specifics:
                covered |= _vals_by_q.get(sp, set())
            keep = [a for a in by_q[k]
                    if (str(a["value"]), str(a["unit"])) not in covered]
            if keep:
                by_q[k] = keep
            else:
                del by_q[k]
    # Two DIFFERENT pressure kinds carrying the identical value at the same scope are
    # one assertion typed two ways. Keep the one whose evidence is strongest.
    _PRESSURE_KINDS = {"working_pressure", "base_pressure", "generic_pressure",
                       "precursor_partial_pressure", "co_reactant_partial_pressure",
                       "carrier_gas_partial_pressure", "bubbler_pressure"}
    _best = {}
    for k, cands in list(by_q.items()):
        if k[0] not in _PRESSURE_KINDS:
            continue
        for a in cands:
            sig = (str(a["value"]), str(a["unit"]), a["scope"])
            cur = _best.get(sig)
            if cur is None or (a.get("confidence") or 0) > (cur[1].get("confidence") or 0):
                _best[sig] = (k, a)
    for k, cands in list(by_q.items()):
        if k[0] not in _PRESSURE_KINDS:
            continue
        keep = [a for a in cands
                if _best.get((str(a["value"]), str(a["unit"]), a["scope"]), (k,))[0] == k]
        if keep:
            by_q[k] = keep
        else:
            del by_q[k]

    varied = set(figure_varied_quantities or ())
    bound, ambiguous = [], []
    for q, cands in by_q.items():
        cands.sort(key=lambda a: SCOPE_ORDER.index(a["scope"])
                   if a["scope"] in SCOPE_ORDER else len(SCOPE_ORDER))
        best_scope = cands[0]["scope"]
        at_scope = [a for a in cands if a["scope"] == best_scope]
        # A quantity this figure varies has no single figure-wide value -- UNLESS the
        # assertion comes from the caption's shared preamble, which states the standard
        # values that hold for every panel ("Standard parameter values: 0.01 mbar of
        # pressure, 100 sccm of H2 ..."). Those are genuinely figure-common; a panel
        # that varies one of them simply overrides it at series scope.
        _preamble_common = all(a.get("figure_common") for a in at_scope)
        if (q[0] if isinstance(q, tuple) else q) in varied and not _preamble_common and \
                best_scope in ("figure", "method", "paper"):
            ambiguous.append({
                "quantity": q[0] if isinstance(q, tuple) else q,
                "species": q[1] if isinstance(q, tuple) else None,
                "scope": best_scope,
                "candidates": sorted({"%s %s" % (a["value"], a["unit"]) for a in at_scope}),
                "status": Status.AMBIGUOUS,
                "reason": ("%s is varied by a panel/series of this figure, so a "
                           "%s-scope value is one panel's setting and cannot be "
                           "applied to this entity"
                           % (q[0] if isinstance(q, tuple) else q, best_scope)),
                "assertions": at_scope,
            })
            continue
        vals = {(str(a["value"]), str(a["unit"])) for a in at_scope}
        if len(vals) > 1:
            # a governing phrase outranks a window-typed guess before declaring a
            # conflict ("0.01 mbar of pressure" beats a pressure typed from a distant
            # mention of a carrier gas)
            top = max(a.get("confidence") or 0 for a in at_scope)
            strong = [a for a in at_scope if (a.get("confidence") or 0) >= top - 1e-9]
            if len({(str(a["value"]), str(a["unit"])) for a in strong}) == 1:
                at_scope = strong
                vals = {(str(a["value"]), str(a["unit"])) for a in at_scope}
        if len(vals) > 1:
            # The source often disambiguates same-scope values ITSELF by naming
            # each value's chemistry in its clause ("Al2O3 ... at 300 C and TiO2
            # from TiCl4 ... at 110 C"). When the entity's own reagents are known
            # (metal-paired to its material at the call site), a candidate whose
            # species is a DECLARED reagent of a different chemistry is that
            # recipe's value, not this one's, and is set aside before any
            # conflict is declared. A species outside the declared reagent lists
            # disambiguates nothing and discards nothing.
            declared = {_chem_key(x) for x in (entity.get("paper_reagents") or [])}
            mine = {_chem_key(x) for x in (entity.get("entity_reagents") or [])}
            if declared and mine:
                own = [a for a in at_scope
                       if not ((a.get("species") or a.get("of_reactant"))
                               and _chem_key(a.get("species") or a.get("of_reactant"))
                               in declared - mine)]
                if own and len({(str(a["value"]), str(a["unit"])) for a in own}) == 1:
                    for a in own:
                        a["chemistry_scope_basis"] = (
                            "same-scope alternatives named reagents of a different "
                            "chemistry of this paper and were set aside")
                    at_scope = own
                    vals = {(str(a["value"]), str(a["unit"])) for a in at_scope}
        if len(vals) > 1:
            ambiguous.append({
                "quantity": q[0] if isinstance(q, tuple) else q,
                "species": q[1] if isinstance(q, tuple) else None,
                "scope": best_scope,
                "candidates": sorted("%s %s" % v for v in vals),
                "status": Status.AMBIGUOUS,
                "reason": "%d distinct %s values at %s scope; no narrower evidence "
                          "distinguishes them, so none is applied"
                          % (len(vals), q[0] if isinstance(q, tuple) else q, best_scope),
                "assertions": at_scope,
            })
            continue
        winner = dict(at_scope[0])
        winner["binding_key"] = list(q) if isinstance(q, tuple) else [q, None]
        winner["bound_at_scope"] = best_scope
        winner["overrode_scopes"] = sorted({a["scope"] for a in cands[1:]})
        winner["corroborating_assertions"] = len(at_scope) - 1
        bound.append(winner)
    unbound = [a for a in assertions if a not in applicable]
    return bound, ambiguous, unbound

#: A written range whose hyphen was read as a minus sign. "10-120 ms" arriving as -120 is
#: the observed shape; the give-away is that the magnitude equals the upper bound of a
#: range still visible in the record's own evidence.
_RANGE_IN_TEXT = re.compile(r"(\d+(?:\.\d+)?)\s*[-\u2010-\u2015]\s*(\d+(?:\.\d+)?)")

#: Quantities that cannot be negative in any unit. Sign is not a matter of convention for
#: a duration, a count or a pressure -- a negative one describes nothing.
_STRICTLY_POSITIVE = ("time", "cycle", "pressure", "thickness", "height", "width",
                      "depth", "rate", "flow", "dose", "exposure", "purge", "number")


def strictly_positive_quantity(quantity):
    q = str(quantity or "").lower()
    return any(w in q for w in _STRICTLY_POSITIVE)


def sanitize_magnitude(quantity, value, evidence=None):
    """(value, range, reason) for a persisted scalar that cannot physically be negative.

    Two outcomes, and the difference matters. Where the record's own evidence still shows
    the range the number came from -- "ultrashort doses (10-120 ms)" reaching the record
    as -120 -- the scalar is REPAIRED into the range it always was, because the source did
    state both bounds. Where there is no such evidence the value is simply refused: a
    negative duration is not a weaker measurement of a real one, and passing it downstream
    lets every comparison inherit the sign error.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value, None, None
    if v >= 0 or not strictly_positive_quantity(quantity):
        return value, None, None
    m = _RANGE_IN_TEXT.search(str(evidence or ""))
    if m and abs(float(m.group(2)) - abs(v)) < 1e-9:
        lo, hi = float(m.group(1)), float(m.group(2))
        return None, [lo, hi], (
            "%r was persisted as %g; the evidence states the range %g-%g, so the hyphen "
            "of a written range had been read as a minus sign" % (quantity, v, lo, hi))
    return None, None, (
        "%r cannot be negative; %g is refused rather than propagated" % (quantity, v))

# ------------------------------------------------------------------ gas roles in prose
#: A gas can appear in a process in roles that are not reagent roles at all. "N2 was used
#: as the carrier gas and purging gas" is explicit structured information sitting in
#: prose: without it the same N2 is either invisible or, worse, mistaken for a reactant.
#: The two roles are kept apart -- a carrier gas transports the precursor, a purge gas
#: sweeps the chamber, and one species often does both but they are different statements.
CARRIER_GAS = "carrier_gas"
PURGE_GAS = "purge_gas"

#: A gas formula, captured only where the sentence gives it a ROLE. The token is matched
#: CASE-SENSITIVELY: a formula starts with a capital, and matching case-insensitively
#: turned ordinary words ("as", "and", "the") into species.
#: Excluded IN THE PATTERN, not after matching: a sentence-initial "A" would otherwise
#: consume the match and hide the real formula later in the same clause.
_GAS_STOP = (r"(?!(?:A|An|The|As|Is|Was|Were|In|On|At|By|Of|To|And|Or|It|This|That|"
             r"Both|All|One|Two)\b)")
_GAS_TOKEN = _GAS_STOP + r"([A-Z][a-z]?[0-9]?|argon|nitrogen|helium|Argon|Nitrogen|Helium)"

_CARRIER = r"[Cc]arrier\s+gas"
_PURGE = r"[Pp]urg\w*\s+gas"

_GAS_ROLE_PATTERNS = (
    (re.compile(_GAS_TOKEN + r"(?:[^.;]{0,45}?\bas\b[^.;]{0,25}?|\s+)" + _CARRIER), CARRIER_GAS),
    (re.compile(_CARRIER + r"[^.;]{0,25}?\b(?:was|is)\b\s*" + _GAS_TOKEN), CARRIER_GAS),
    (re.compile(_GAS_TOKEN + r"(?:[^.;]{0,45}?\bas\b[^.;]{0,25}?|\s+)" + _PURGE), PURGE_GAS),
    (re.compile(_PURGE + r"[^.;]{0,25}?\b(?:was|is)\b\s*" + _GAS_TOKEN), PURGE_GAS),
    (re.compile(r"purged\s+with\s+" + _GAS_TOKEN), PURGE_GAS),
)

#: Capitalised words that are not gases (sentence starts, common nouns).
_NOT_A_GAS = frozenset("A An The As Is Was Were In On At By Of To And Or It This That "
                       "He_ Both All One Two".split())


def gas_roles_from_text(text):
    """[{role, species, evidence}] for gas roles a passage states EXPLICITLY.

    Only a sentence that gives the gas a role is read. A gas mentioned without one -- a
    chamber backfilled with something, a formula in a table header -- yields nothing,
    because "present" and "used as the carrier" are different claims. A species may hold
    both roles, and each is reported separately with the sentence that states it.
    """
    out, seen = [], set()
    for sentence in re.split(r"(?<=[.;])\s+", str(text or "")):
        # a sentence can carry the species once and both roles ("carrier gas and purging
        # gas"), so every pattern is tried against the whole sentence
        for rx, role in _GAS_ROLE_PATTERNS:
            for m in rx.finditer(sentence):
                sp = (m.group(1) or "").strip()
                if not sp or sp in _NOT_A_GAS or len(sp) > 12:
                    continue
                sp = {"argon": "Ar", "nitrogen": "N2", "helium": "He"}.get(sp.lower(), sp)
                if (role, sp) in seen:
                    continue
                seen.add((role, sp))
                out.append({"role": role, "species": sp,
                            "evidence": sentence.strip()[:240]})
    return out

# ---------------------------------------------------- evidence-consistency guards
#: Words identifying the ROLE a role-qualified quantity claims. A quantity that names a
#: role must have that role in its own evidence, or it is a number that landed on the
#: wrong physical quantity.
_ROLE_QUALIFIED = {
    "carrier_gas_partial_pressure": r"carrier",
    "carrier_gas_flow": r"carrier",
    "purge_gas_flow": r"purg",
}

#: A comparator immediately before the magnitude makes the statement a BOUND.
_BOUND_BEFORE = re.compile(
    r"(<|>|\u2264|\u2265|&lt;|&gt;|less\s+than|greater\s+than|up\s+to|at\s+least|"
    r"below|above|under|over|approximately|about|~|\u223c)\s*$", re.I)


def species_is_a_unit(species):
    """Is this 'species' actually a unit token the parser mistook for a chemical?"""
    s = str(species or "").strip()
    if not s:
        return False
    try:
        from pipeline.canonical import units as _U
        _U.parse(s)
        return True
    except Exception:
        return False


def bound_in_evidence(value, evidence):
    """The comparator qualifying this magnitude in its own evidence, or None.

    "<2 Torr" is an upper bound on a pressure, not a pressure. Persisting it as an
    equality states something the source never claimed, and every comparison downstream
    then treats a limit as a setting.
    """
    ev, val = str(evidence or ""), str(value or "").strip()
    if not ev or not val:
        return None
    i = ev.find(val)
    while i > 0:
        m = _BOUND_BEFORE.search(ev[:i])
        if m:
            return m.group(1)
        i = ev.find(val, i + 1)
    return None


def role_unsupported_by_evidence(quantity, evidence):
    """True when a role-qualified quantity's own role is absent from its evidence."""
    pat = _ROLE_QUALIFIED.get(str(quantity or ""))
    if not pat:
        return False
    return not re.search(pat, str(evidence or ""), re.I)

def value_supported_by_evidence(value, evidence):
    """Does the evidence actually contain the magnitude it is offered as evidence for?

    An extractor keeps a window around what it matched, so a numeric condition whose own
    window does not contain its number was not read from that sentence at all. The pairing
    is broken, and a value nobody can check against its own quotation is worse than an
    absent one -- it looks sourced. Non-numeric values (a reagent name, a process type)
    are not checked here, and an assertion carrying no evidence at all is left alone
    rather than judged.
    """
    ev = str(evidence or "")
    if not ev.strip():
        return True
    try:
        v = float(str(value).strip())
    except (TypeError, ValueError):
        return True
    for m in re.finditer(r"-?\d+(?:\.\d+)?(?:\s*[eE]\s*[-+]?\d+)?", ev.replace(",", "")):
        try:
            if abs(float(m.group(0)) - v) < 1e-9:
                return True
        except ValueError:
            continue
    return False
