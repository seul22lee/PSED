"""
canonical/axis_semantics.py — evidence-backed resolution of what a plot axis means.

Two jobs:

  1. AXIS ROLE  — coordinate (the curve is one profile) vs condition (each point
     is its own experiment) vs output. Taken from the ontology's `axis_role`, not
     from the point count.

  2. AXIS KIND + NORMALIZATION DEFINITION — for dimensionless axes, WHICH
     normalization it is (x/H vs x/L vs t/t0 vs t/tmax ...). This is never
     guessed: a definition is assigned only when a pattern matches a quoted span
     in a real source, and the span is stored with the assignment.

Evidence priority (spec §2.2):
    1 raw axis label      2 figure caption      3 panel caption text
    4 nearby figure discussion in document.md   5 equations/definitions
    6 structure.json      7 figure image (selective re-extraction)  8 PDF page

Anything unresolved stays unresolved with a structured reason.
"""
from __future__ import annotations
import re as _re

import re

from .schema import (NORMALIZATION_DEFINITIONS, COMPARISON_GROUPS, QK_META,
                     Evidence, Status)

# --- ontology-derived lookups --------------------------------------------
_ALIAS = {}
for _q in QK_META.values():
    def _n(s):
        return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
    _ALIAS[_n(_q["id"])] = _q["id"]
    for _a in (_q.get("aliases") or []):
        _ALIAS.setdefault(_n(_a), _q["id"])
    for _s in (_q.get("symbols") or []):
        _ALIAS.setdefault(_n(_s), _q["id"])


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def canon_quantity(name):
    return _ALIAS.get(_norm(name)) if name else None


def axis_role_of(qid):
    return (QK_META.get(qid) or {}).get("axis_role")


# =========================================================================
# Normalization pattern table.
#
# Each entry: (compiled regex, normalization_definition_id, confidence).
# Patterns are deliberately SPECIFIC — a bare "H" or "normalized thickness"
# never matches, because that would be inference, not evidence.
# =========================================================================
_X = r"(?:x|z|l|d|X|Z|L|D|ã|ẽ|ũ|distance|position|depth|location)"

POSITION_PATTERNS = [
    # explicit ratio forms
    (re.compile(r"(?<![A-Za-z0-9])[xzXZ]\s*(?:̃|~|tilde)?\s*=?\s*/\s*H(?![a-z0-9])"), "x_over_feature_height", 0.95),
    (re.compile(r"(?<![A-Za-z0-9])[xzXZ]\s*(?:̃|~|tilde)?\s*=?\s*/\s*L(?![a-z0-9])"), "x_over_channel_length", 0.95),
    (re.compile(r"(?<![A-Za-z0-9])[xzXZ]\s*/\s*D\s*_?\s*h(?![a-z0-9])"), "x_over_hydraulic_diameter", 0.95),
    (re.compile(r"(?<![A-Za-z0-9])[xzXZ]\s*/\s*w(?![a-z0-9])"), "x_over_feature_width", 0.9),
    # spelled-out denominators
    (re.compile(r"(?:normali[sz]ed|divided|scaled|relative)\s+(?:by|to)\s+(?:the\s+)?"
                r"(?:channel|feature|cavity|trench|via|pore)?\s*(?:height|depth of the (?:channel|feature))",
                re.I), "x_over_feature_height", 0.8),
    (re.compile(r"(?:normali[sz]ed|divided|scaled|relative)\s+(?:by|to)\s+(?:the\s+)?"
                r"(?:channel|feature|structure)?\s*length", re.I), "x_over_channel_length", 0.8),
    (re.compile(r"(?:normali[sz]ed|divided|scaled|relative)\s+(?:by|to)\s+(?:the\s+)?"
                r"(?:hydraulic\s+diameter)", re.I), "x_over_hydraulic_diameter", 0.85),
    (re.compile(r"(?:normali[sz]ed|divided|scaled|relative)\s+(?:by|to)\s+(?:the\s+)?"
                r"(?:feature\s+depth|etch\s+depth)", re.I), "x_over_feature_depth", 0.8),
    # "distance / cavity height" style
    (re.compile(r"(?:distance|position)\s*/\s*(?:cavity|channel|feature)\s*height", re.I),
     "x_over_feature_height", 0.9),
]

THICKNESS_PATTERNS = [
    # t(x)/t(0) and friends
    (re.compile(r"(?<![A-Za-z0-9])([tdSG])\s*\(\s*[xz]\s*\)\s*/\s*\1\s*\(\s*0\s*\)"), "t_over_t_entrance", 0.95),
    (re.compile(r"(?<![A-Za-z0-9])([td])\s*/\s*\1\s*_?\s*0(?![a-z0-9.])"), "t_over_t_entrance", 0.9),
    (re.compile(r"(?:normali[sz]ed|divided|relative)\s+(?:by|to)\s+(?:the\s+)?(?:thickness|value)?\s*"
                r"(?:at\s+)?(?:the\s+)?(?:feature\s+)?(?:entrance|mouth|opening|inlet|top surface)", re.I),
     "t_over_t_entrance", 0.85),
    # t/tmax
    (re.compile(r"(?<![A-Za-z0-9])([td])\s*(?:\(\s*[xz]\s*\)\s*)?/\s*\1\s*_?\s*\{?\s*max", re.I), "t_over_t_max", 0.95),
    (re.compile(r"(?:normali[sz]ed|divided|relative)\s+(?:by|to)\s+(?:the\s+)?maximum\s+"
                r"(?:thickness|value)", re.I), "t_over_t_max", 0.85),
    # t/t_planar
    (re.compile(r"(?<![A-Za-z0-9])([td])\s*(?:\(\s*[xz]\s*\)\s*)?/\s*\1\s*_?\s*\{?\s*"
                r"(?:planar|flat|plane)", re.I), "t_over_t_planar", 0.95),
    (re.compile(r"(?:normali[sz]ed|divided|relative)\s+(?:by|to)\s+(?:the\s+)?"
                r"(?:thickness\s+on\s+(?:a\s+)?)?(?:planar|flat|blanket)\s*(?:surface|reference|film)?", re.I),
     "t_over_t_planar", 0.8),
    # step coverage bottom/top
    (re.compile(r"(?<![A-Za-z0-9])([td])\s*_?\s*\{?\s*bottom\s*\}?\s*/\s*\1\s*_?\s*\{?\s*top", re.I),
     "t_bottom_over_t_top", 0.95),
    (re.compile(r"\b(?:step[- ]coverage|bottom[- ]to[- ]top ratio|bottom/top)\b", re.I),
     "t_bottom_over_t_top", 0.8),
    (re.compile(r"(?<![A-Za-z0-9])([td])\s*_?\s*\{?\s*bottom\s*\}?\s*/\s*\1\s*_?\s*\{?\s*"
                r"(?:planar|flat)", re.I), "t_bottom_over_t_planar", 0.9),
    # local/planar GPC
    (re.compile(r"GPC\s*(?:\(\s*[xz]\s*\)\s*)?/\s*GPC\s*_?\s*\{?\s*(?:planar|flat|0)", re.I),
     "gpc_local_over_gpc_planar", 0.95),
    (re.compile(r"(?:local|normali[sz]ed)\s+(?:GPC|growth per cycle)\s*/\s*"
                r"(?:planar|flat)\s+(?:GPC|growth per cycle)", re.I),
     "gpc_local_over_gpc_planar", 0.9),
]

# Symbol -> which normalization definitions could own it (used to explain
# ambiguity when several distinct definitions match the same source).
DEF_OF = {d: NORMALIZATION_DEFINITIONS[d] for d in NORMALIZATION_DEFINITIONS}


def _search(patterns, text):
    """Return [(definition_id, confidence, matched_span)] for every hit."""
    if not text:
        return []
    hits = []
    for rx, ndef, conf in patterns:
        m = rx.search(text)
        if m:
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            hits.append((ndef, conf, text[start:end].strip()))
    return hits


# Confidence decays with evidence distance from the axis itself. A verbatim axis
# label is direct evidence; a match in the surrounding prose is circumstantial and
# must not be reported with the same certainty.
SOURCE_WEIGHT = {
    "axis_label": 1.0,
    "panel_caption": 0.9,
    "figure_caption": 0.8,
    "document_text": 0.55,
    # a targeted "<symbol> = <ratio>" definition anywhere in the paper is
    # stronger evidence than loose surrounding prose, but weaker than the caption
    "document_symbol_definition": 0.7,
    "equations": 0.5,
    "figure_image": 0.95,
}
# Below this, an assignment is kept but queued for manual review.
REVIEW_THRESHOLD = 0.6


# A dimensionless axis usually carries only a SYMBOL ("Dimensionless distance x̃",
# "Normalized distance ξ"), while the paper defines that symbol elsewhere
# ("... the dimensionless distance x̃ (x̃ = x/H)"). Resolving the symbol's own
# definition is a general mechanism — papers routinely define their dimensionless
# variables — and avoids hard-coding any paper's private terminology.
_SYMBOL_IN_LABEL = re.compile(
    r"(?:^|\s)([A-Za-zξζχηθ][̀-ͯ]?(?:\s*[˜~])?)\s*(?:\([^)]*\))?\s*$")


def _axis_symbol(label):
    """The trailing symbol of an axis label, e.g. 'Dimensionless distance x̃' -> 'x̃'."""
    if not label:
        return None
    m = _SYMBOL_IN_LABEL.search(str(label).strip())
    if not m:
        return None
    sym = re.sub(r"\s+", "", m.group(1))
    return sym if 1 <= len(sym) <= 3 else None


_MARKS = "̃~˜"          # combining tilde, ASCII tilde, small tilde


def _symbol_definition_spans(symbol, text):
    """Spans where `symbol` is DEFINED as a ratio: '<sym> = <expr>'.

    Diacritic-EXACT. A paper that writes x̃ = x/H and x = x/L is using the tilde
    as the discriminator, so a tilde-optional match would collapse two distinct
    definitions into a false ambiguity. `x̃` therefore matches only the tilde
    form, and `x` only the bare form."""
    if not symbol or not text:
        return []
    core = symbol[0]
    if any(m in symbol for m in _MARKS):
        sym_re = r"%s\s*[%s]" % (re.escape(core), _MARKS)
    else:
        sym_re = r"%s(?!\s*[%s])" % (re.escape(core), _MARKS)
    rx = re.compile(r"(?<![A-Za-z0-9])%s\s*=\s*[^,.;)]{1,40}" % sym_re)
    return [m.group(0) for m in rx.finditer(text)]


def detect_normalization(axis, texts, patterns, label=None):
    """Run the pattern table over prioritised (source_name, source_file, text)
    tuples. First source with hits wins; conflicting hits in that source produce
    an AMBIGUOUS result rather than a pick.

    Before falling back to whole-source scanning, the axis SYMBOL's own
    definition is looked up: that is narrower evidence than the surrounding
    prose and disambiguates a caption that describes several panels.

    Returns (definition_id|None, Evidence|None, status, reason)."""
    sym = _axis_symbol(label)
    if sym:
        for source, source_file, source_location, text in texts:
            defs = set()
            best = None
            for span in _symbol_definition_spans(sym, text):
                for ndef, conf, matched in _search(patterns, span):
                    defs.add(ndef)
                    if best is None:
                        best = (ndef, conf, span)
            if not defs:
                continue
            if len(defs) > 1:
                return (None, Evidence.make(
                    source, source_file, source_location, span=best[2],
                    method="symbol_definition", confidence=0.0), Status.AMBIGUOUS,
                    "symbol %r is defined %d different ways in %s: %s"
                    % (sym, len(defs), source, ", ".join(sorted(defs))))
            ndef, conf, span = best
            c = round(conf * SOURCE_WEIGHT.get(source, 0.5), 3)
            ev = Evidence.make(source, source_file, source_location, span=span,
                               method="symbol_definition:%s(%s)" % (source, sym),
                               confidence=c, automatic=c >= REVIEW_THRESHOLD)
            ev["needs_manual_review"] = c < REVIEW_THRESHOLD
            ev["axis_symbol"] = sym
            return (ndef, ev, "resolved", None)

    for source, source_file, source_location, text in texts:
        if source == "document_symbol_definition":
            continue     # whole-paper text: only the targeted symbol path may use it
        hits = _search(patterns, text)
        if not hits:
            continue
        defs = sorted({h[0] for h in hits})
        if len(defs) > 1:
            return (None, Evidence.make(source, source_file, source_location,
                                        span=hits[0][2], method="pattern_match",
                                        confidence=0.0),
                    Status.AMBIGUOUS,
                    "source %r matches %d different normalization definitions: %s"
                    % (source, len(defs), ", ".join(defs)))
        ndef, conf, span = hits[0]
        conf = round(conf * SOURCE_WEIGHT.get(source, 0.5), 3)
        ev = Evidence.make(source, source_file, source_location, span=span,
                           method="pattern_match:" + source, confidence=conf,
                           automatic=conf >= REVIEW_THRESHOLD)
        ev["needs_manual_review"] = conf < REVIEW_THRESHOLD
        return (ndef, ev, "resolved", None)
    return (None, None, Status.MISSING_CONTEXT,
            "no normalization expression found in axis label, caption, panel text, "
            "figure discussion or equations")


# =========================================================================
# axis resolution
# =========================================================================
def _is_dimensionless_unit(unit):
    return str(unit or "").strip() in ("", "1", "-", "dimensionless", "unitless",
                                       "a.u.", "ratio", "fraction")


# =========================================================================
# Evidence-backed unit recovery from a verbatim axis label.
#
# Two cases, both requiring the label to actually say so — never inferred:
#   (a) the unit is printed in the label but was not captured
#       "GPC (Å/cycle)" with unit_raw "" -> Å/cycle
#   (b) the label divides by cycles while the printed unit is a bare length
#       "Thickness/cycles S/N (nm)" -> nm/cycle
#       This is the corpus-wide GPC-labelled-"nm" problem. It is only applied
#       when the label CONTAINS the division; a bare "GPC (nm)" stays conflicted.
# =========================================================================
_UNIT_IN_LABEL = re.compile(r"[\(\[]\s*([^)\]]{1,16}?)\s*[\)\]]\s*$")
_PER_CYCLE = re.compile(r"(?:/\s*(?:cycle|cycles|cyc|N)\b|\bper\s+cycle\b)", re.I)


def recover_unit(raw_unit, label, quantity):
    """-> (unit, Evidence|None). Returns raw_unit unchanged when there is no
    documentary evidence for anything better."""
    if not label:
        return raw_unit, None
    label = str(label)

    # (a) unit printed in the label, missing from the structured field
    if not str(raw_unit or "").strip():
        m = _UNIT_IN_LABEL.search(label)
        if m:
            cand = m.group(1).strip()
            if cand not in ("-", "") and re.match(r"^[A-Za-zÅåµμ°%/·.\-^0-9 ]+$", cand):
                from . import units as _U
                if _U.try_parse(cand) is not None:
                    return cand, Evidence.make(
                        "axis_label", None, None, span=label,
                        method="unit_printed_in_axis_label", confidence=0.9)

    # (b) the label divides by cycles but the unit is a bare length
    if quantity in ("growth_per_cycle", "thickness_per_cycle") and _PER_CYCLE.search(label):
        from . import units as _U
        u = _U.try_parse(raw_unit)
        if u is not None and _U.DIM_NAME.get(u.dimension) == "length":
            recovered = u.symbol + "/cycle"
            if _U.try_parse(recovered) is not None:
                return recovered, Evidence.make(
                    "axis_label", None, None, span=label,
                    method="per_cycle_division_printed_in_axis_label", confidence=0.9)
    return raw_unit, None


def resolve_x_axis(raw_quantity, raw_unit, raw_label, texts):
    """Resolve the semantics of an x axis.

    Returns a dict: axis_role, axis_kind, quantity, normalization_definition,
    comparison_group, evidence[], status, unresolved_reason."""
    qid = canon_quantity(raw_quantity)
    role = axis_role_of(qid)
    unit, unit_ev = recover_unit(raw_unit, raw_label, qid)
    out = {
        "raw_quantity": raw_quantity, "raw_unit": raw_unit, "raw_label": raw_label,
        "unit": unit, "unit_recovered": unit != raw_unit,
        "quantity": qid, "axis_role": role, "axis_kind": None,
        "normalization_definition": None, "comparison_group": None,
        "evidence": [unit_ev] if unit_ev else [], "status": None,
        "unresolved_reason": None,
    }
    if qid is None:
        out["status"] = Status.UNSUPPORTED
        out["axis_kind"] = "unknown"
        out["unresolved_reason"] = (
            "x quantity %r does not resolve to any ontology QuantityKind" % raw_quantity)
        return out

    dimensionless = _is_dimensionless_unit(unit)

    # A position-family axis with no unit is the signature of a normalized
    # coordinate that lost its label. Try to recover WHICH normalization it is.
    if qid in ("spatial_coordinate", "dimensionless_distance", "aspect_ratio") and dimensionless:
        ndef, ev, status, reason = detect_normalization("x", texts, POSITION_PATTERNS,
                                                        label=raw_label)
        if ndef:
            spec = NORMALIZATION_DEFINITIONS[ndef]
            out.update({
                "axis_kind": "normalized_spatial_coordinate",
                "quantity": "dimensionless_distance" if qid != "aspect_ratio" else "aspect_ratio",
                "axis_role": "coordinate",
                "normalization_definition": ndef,
                "comparison_group": spec.get("comparison_group"),
                "status": "resolved",
            })
            out["evidence"] = out["evidence"] + [ev]
            return out
        out.update({
            "axis_kind": "dimensionless_position_of_unknown_denominator",
            "axis_role": "coordinate",
            "status": status,
            "unresolved_reason": reason,
        })
        out["evidence"] = out["evidence"] + ([ev] if ev else [])
        return out

    if qid == "spatial_coordinate":
        out.update({"axis_kind": "spatial_coordinate", "axis_role": "coordinate",
                    "comparison_group": "spatial_position", "status": "resolved"})
        return out

    # Everything else: role straight from the ontology.
    out["axis_kind"] = {"coordinate": "coordinate", "condition": "condition_sweep",
                        "output": "output"}.get(role, "unknown")
    out["comparison_group"] = _group_for_quantity(qid, role)
    out["status"] = "resolved" if out["comparison_group"] else Status.NOT_APPLICABLE
    if not out["comparison_group"]:
        out["unresolved_reason"] = (
            "quantity %r is not a comparison target (no comparison group declares it)" % qid)
    return out


def resolve_y_axis(raw_quantity, raw_unit, raw_label, texts):
    """Resolve the semantics of a y axis (the measurand)."""
    qid = canon_quantity(raw_quantity)
    role = axis_role_of(qid)
    unit, unit_ev = recover_unit(raw_unit, raw_label, qid)
    out = {
        "raw_quantity": raw_quantity, "raw_unit": raw_unit, "raw_label": raw_label,
        "unit": unit, "unit_recovered": unit != raw_unit,
        "quantity": qid, "axis_role": role, "axis_kind": None,
        "normalization_definition": None, "comparison_group": None,
        "evidence": [unit_ev] if unit_ev else [], "status": None,
        "unresolved_reason": None,
    }
    if qid is None:
        out["status"] = Status.UNSUPPORTED
        out["axis_kind"] = "unknown"
        out["unresolved_reason"] = (
            "y quantity %r does not resolve to any ontology QuantityKind" % raw_quantity)
        return out

    # Any normalized/ratio measurand must name WHICH normalization it is.
    if qid in ("normalized_thickness", "step_coverage", "conformality"):
        ndef, ev, status, reason = detect_normalization("y", texts, THICKNESS_PATTERNS,
                                                        label=raw_label)
        if ndef:
            spec = NORMALIZATION_DEFINITIONS[ndef]
            out.update({
                "axis_kind": "normalized_" + spec.get("normalization_denominator_role", "thickness"),
                "normalization_definition": ndef,
                "comparison_group": spec.get("comparison_group"),
                "status": "resolved",
            })
            out["evidence"] = out["evidence"] + [ev]
            return out
        out.update({
            "axis_kind": "normalized_thickness_of_unknown_denominator",
            "status": status, "unresolved_reason": reason,
        })
        out["evidence"] = out["evidence"] + ([ev] if ev else [])
        return out

    out["axis_kind"] = {"output": "output", "condition": "condition",
                        "coordinate": "coordinate"}.get(role, "unknown")
    out["comparison_group"] = _group_for_quantity(qid, role)
    out["status"] = "resolved" if out["comparison_group"] else Status.NOT_APPLICABLE
    if not out["comparison_group"]:
        out["unresolved_reason"] = (
            "quantity %r is not a comparison target (no comparison group declares it)" % qid)
    return out


_GROUP_BY_QUANTITY = {}
for _gid, _g in COMPARISON_GROUPS.items():
    # groups WITHOUT a normalization definition own their canonical quantity
    # outright; normalized groups are only reachable via evidence.
    if not _g.get("normalization_definition"):
        _GROUP_BY_QUANTITY.setdefault(_g["canonical_quantity"], _gid)


def _group_for_quantity(qid, role):
    """Direct (non-normalized) comparison group for a quantity, if any."""
    if qid in _GROUP_BY_QUANTITY:
        return _GROUP_BY_QUANTITY[qid]
    meta = QK_META.get(qid) or {}
    # a specialization inherits its parent's group (deposition_temperature ->
    # process_temperature) so sweeps land in the right bucket.
    parent = meta.get("specializes")
    if parent and parent in _GROUP_BY_QUANTITY:
        return _GROUP_BY_QUANTITY[parent]
    same = meta.get("same_as")
    if same and same in _GROUP_BY_QUANTITY:
        return _GROUP_BY_QUANTITY[same]
    return None


# =========================================================================
# granularity
# =========================================================================
def resolve_granularity(x_semantics, n_points):
    """Ontology-backed granularity.

      coordinate axis -> ONE profile experiment holding the ordered points
      condition axis  -> each point is its own experiment; the curve is an
                         ExperimentSeries that series_varies the condition

    Returns (representation, reason)."""
    role = x_semantics.get("axis_role")
    if n_points <= 1:
        return "single", "only %d point" % n_points
    if role == "coordinate":
        return "profile", "x axis %r is an ontology coordinate" % x_semantics.get("quantity")
    if role == "condition":
        return "series", "x axis %r is an ontology condition; each point is one experiment" \
            % x_semantics.get("quantity")
    if role == "output":
        return "correlation", ("x axis %r is an ontology OUTPUT, so the curve relates two "
                               "measured outputs rather than sweeping an input"
                               % x_semantics.get("quantity"))
    return "unresolved", "x axis role could not be determined"


# --- ontology-declared axis units --------------------------------------------------
#: A figure axis often prints no unit because the quantity carries it: "Number of ALD
#: cycles" needs no "(cycle)" beside it for a reader to know what the numbers count. The
#: ontology already declares that unit, so an axis whose quantity resolved is not
#: unitless -- it is a quantity whose unit was not reprinted.
def ontology_axis_unit(quantity, source_unit=None):
    """(unit, basis). The source unit wins; the ontology fills a silent axis.

    Returns (None, reason) when neither the source nor the ontology establishes a unit --
    an axis that genuinely has no resolved unit, which must stay unresolved rather than
    being treated as dimensionless.
    """
    if source_unit not in (None, "", " "):
        return source_unit, "unit printed on the source axis"
    if not quantity:
        return None, "no semantic quantity resolved for this axis"
    from ontology import vocab as _v
    u = _v.quantity_unit(quantity)
    if u in (None, "", " "):
        return None, ("ontology declares no unit for %r, and the source axis printed none"
                      % quantity)
    return u, ("ontology-declared unit for %r; the source axis printed none" % quantity)

# --------------------------------------------------------- normalization from evidence
#: Words that carry no discriminating meaning in a normalization label.
_NORM_STOPWORDS = frozenset(
    "a an the of to on at by and or per its it is was were for from in into with local "
    "value values thickness position axial growth cycle coverage profile reference "
    "adjacent number amount".split())

#: A sentence only states a normalization when it SAYS so. "normalized", "scaled to",
#: "relative to" and "divided by" are the statements; the bare word "dimensionless" is not.
_NORM_STATEMENT = _re.compile(
    r"normali[sz]ed|scaled\s+to|relative\s+to|divided\s+by|expressed\s+as\s+a\s+"
    r"fraction\s+of", _re.I)


def _norm_keywords(defn):
    """Discriminating words of one normalization, taken from the ontology's own label."""
    text = " ".join(str(defn.get(k) or "") for k in ("semantic_label", "denominator", "id"))
    words = {w for w in _re.findall(r"[a-z_]{3,}", text.lower()) if w not in _NORM_STOPWORDS}
    return {w for word in words for w in (word.split("_") if "_" in word else [word])
            if len(w) >= 4 and w not in _NORM_STOPWORDS}


#: How a source names the axis a normalization statement is about. A whole document
#: mentions every reference somewhere, so a statement only counts when it says WHICH axis
#: it describes -- otherwise one paper's mention of a planar witness would resolve another
#: figure's entrance normalization.
_AXIS_WORDS = {
    "y": _re.compile(r"vertical axis|y[- ]axis|ordinate", _re.I),
    "x": _re.compile(r"horizontal axis|x[- ]axis|abscissa", _re.I),
}

_SENTENCE = _re.compile(r"(?<=[.;])\s+")


def normalization_from_statement(text, normalizations, quantity=None, axis=None):
    """(normalization_id, evidence) that a source statement EXPLICITLY identifies.

    The reference an axis was divided by is a physical claim, so it is only ever read from
    a sentence that states it. Two conditions must both hold: the passage has to make a
    normalization STATEMENT at all, and it has to name a reference that belongs to exactly
    ONE declared normalization. The bare word "normalized" identifies nothing -- a
    normalized thickness may be referenced to the entrance, to the maximum or to a planar
    witness, and those are three different curves -- so a statement that does not
    discriminate leaves the basis unresolved, which is the honest answer.

    Keywords come from the ontology's own labels, so adding a normalization there extends
    this without touching any code here.
    """
    passage = str(text or "")
    if not passage:
        return None, None
    axis_rx = _AXIS_WORDS.get(axis)
    # a long passage is read sentence by sentence: the claim has to be made in ONE
    # statement, not assembled from words scattered across a document
    sentences = [s for s in _SENTENCE.split(passage) if _NORM_STATEMENT.search(s)]
    if axis_rx is not None and len(sentences) > 1:
        sentences = [s for s in sentences if axis_rx.search(s)]
    if not sentences:
        return None, None
    candidates = dict(normalizations or {})
    kw = {n: _norm_keywords(d) for n, d in candidates.items()}
    # a word shared by several normalizations cannot discriminate between them
    shared = {w for a in kw for b in kw if a != b for w in (kw[a] & kw[b])}
    found = {}
    for s in sentences:
        low = s.lower()
        hit = {n: sorted(w for w in words - shared
                         if _re.search(r"\b%s" % _re.escape(w), low))
               for n, words in kw.items()}
        hit = {n: w for n, w in hit.items() if w}
        if len(hit) == 1:
            nid, words = next(iter(hit.items()))
            found.setdefault(nid, (words, s))
    if len(found) != 1:
        return None, None
    nid, (words, sentence) = next(iter(found.items()))
    return nid, ("the source states the normalization and names its reference (%s): %r"
                 % (", ".join(words), sentence.strip()[:260]))


# ------------------------------------------------- document-defined named normalizations
#: Constructions a document uses to BIND A NAME to a definition. Generic by design: the
#: name is whatever short phrase the construction captures, so "Type 1", "scheme A" or
#: "relative intensity" in an unseen paper all bind the same way, and no name from any
#: particular paper appears here.
#: a DEFINITION may use any inflection ("normalizing the thickness to ..."), unlike the
#: direct-statement path, which reads assertions about a drawn axis
_NORM_DEF_STATEMENT = _re.compile(
    r"normali[sz]|scaled\s+to|relative\s+to|divided\s+by|expressed\s+as\s+a\s+"
    r"fraction\s+of", _re.I)

_NAMED_DEF_PATTERNS = [
    # "... normalized to the entrance value, referred to as Type 1 (profiles)"
    _re.compile(r"(?:referred\s+to\s+as|denoted(?:\s+(?:as|by))?|termed|called|"
                r"labell?ed|named|designated(?:\s+as)?)\s+[\"'“‘]?"
                r"(?P<name>[A-Za-z][\w\-]*(?:\s+[\w\-]+){0,4})",
                _re.I),
    # '"Type 1" (is) defined as thickness normalized to ...'
    _re.compile(r"[\"'“‘](?P<name>[A-Za-z][\w\- ]{1,30})[\"'”’]\s*"
                r"(?:is|are)?\s*(?:defined\s+as|denotes?|refers?\s+to|"
                r"corresponds?\s+to|means)", _re.I),
    # "Type 1 profiles are obtained by normalizing to ..." (sentence-initial name)
    _re.compile(r"^\s*(?P<name>[A-Z][\w\-]*(?:\s+[\w\-]+){0,3}?)\s+"
                r"(?:profiles?|curves?|data|representations?|normali[sz]ations?)?\s*"
                r"(?:is|are)\s+(?:defined\s+as|obtained\s+by|computed\s+(?:as|by)|"
                r"calculated\s+(?:as|by))", _re.I),
]


def _name_is_identifying(name, candidates):
    """A captured name must ADD identity beyond the normalization vocabulary itself.

    "normalized thickness" is not a name -- every candidate's own definition contains
    those words, and binding on them would make any caption match any definition. At
    least one token of the name has to be foreign to every candidate's keyword set and to
    the generic normalization words.
    """
    generic = set(_NORM_STOPWORDS) | {"normalized", "normalised", "scaled", "relative",
                                      "profile", "profiles", "curve", "curves", "data"}
    for words in (_norm_keywords(d) for d in (candidates or {}).values()):
        generic |= words
    toks = [t.lower() for t in _re.findall(r"[\w\-]+", str(name or "")) if t]
    return bool(toks) and any(t not in generic for t in toks)


def named_normalization_definitions(text, normalizations, axis=None):
    """{name: {"id": nid, "evidence": defining sentence}} the document itself defines.

    A definition needs three things IN ONE SENTENCE: a normalization statement, a
    reference that discriminates exactly one declared normalization, and a naming
    construction that binds a phrase to it. A paper that defines several named
    representations yields several entries -- which is precisely the situation where
    `normalization_from_statement` must refuse (two discriminating sentences, no way to
    pick), and where a caption's USE of one name resolves the ambiguity.

    A name that two definitions claim is dropped: it identifies nothing.
    """
    passage = str(text or "")
    if not passage:
        return {}
    candidates = dict(normalizations or {})
    if not candidates:
        return {}
    kw = {n: _norm_keywords(d) for n, d in candidates.items()}
    shared = {w for a in kw for b in kw if a != b for w in (kw[a] & kw[b])}
    defs, claimed = {}, {}
    for sentence in _SENTENCE.split(passage):
        if not _NORM_DEF_STATEMENT.search(sentence):
            continue
        low = sentence.lower()
        hit = {n: sorted(w for w in words - shared
                         if _re.search(r"\b%s" % _re.escape(w), low))
               for n, words in kw.items()}
        hit = {n: w for n, w in hit.items() if w}
        if len(hit) != 1:
            continue
        nid = next(iter(hit))
        for rx in _NAMED_DEF_PATTERNS:
            for m in rx.finditer(sentence):
                name = " ".join(str(m.group("name") or "").split()).strip(" .,;:")
                # a leading article is not part of a name
                name = _re.sub(r"^(?:the|a|an)\s+", "", name, flags=_re.I)
                if not name or not _name_is_identifying(name, candidates):
                    continue
                key = name.lower()
                if key in claimed and claimed[key] != nid:
                    defs.pop(key, None)      # two definitions claim one name: not a name
                    claimed[key] = None
                    continue
                if claimed.get(key) is None and key in claimed:
                    continue
                claimed[key] = nid
                defs[key] = {"id": nid, "name": name,
                             "evidence": sentence.strip()[:260]}
    return defs


def normalization_from_named_use(text, named_defs):
    """(normalization_id, evidence) when a passage USES a document-defined name.

    Only for an axis already known to be a ratio: the caller has established that the
    curve is normalized and only the basis is open, so the name alone -- "Type 1
    profiles" in a caption -- is the binding, exactly as the document set it up. A
    passage that uses two different defined names identifies nothing and stays
    unresolved.
    """
    passage = str(text or "")
    if not passage or not named_defs:
        return None, None
    low = passage.lower()
    used = {}
    for key, d in named_defs.items():
        if d and _re.search(r"\b%s\b" % _re.escape(key), low):
            used[d["id"]] = d
    # a longer name containing a shorter one is the more specific statement
    if len(used) != 1:
        return None, None
    d = next(iter(used.values()))
    return d["id"], ("the caption uses the representation the document defines as %r; "
                     "definition: %r" % (d["name"], d["evidence"]))
