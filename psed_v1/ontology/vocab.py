"""
ontology/vocab.py — the ontology's canonicalisation vocabulary.

Ported from the pre-psed_v1 `stages/lib.py`, which mixed three unrelated jobs:
this alias/canonicalisation table, a paper registry that indexed a historical
docling tree, and a Gemini client that loaded its key from outside the project.
Only the vocabulary is used by the live pipeline, so only the vocabulary is
kept; the two historical halves are gone with their paths.

Every canon_* function is byte-for-byte the original behaviour — the port is a
move, not a rewrite. `tests/unit/test_vocab_port.py` pins that equivalence.
"""
import paths as P
import json
import re
from pathlib import Path

ONTOLOGY_JSON = Path(__file__).resolve().parent / "ald_ontology.json"
ONTO = json.loads(ONTOLOGY_JSON.read_text())


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _alias_index(groups):
    idx = {}
    for g in groups:
        for it in ONTO["individuals"].get(g, []):
            idx[norm(it["id"])] = it["id"]
            for f in ("formula", "full_name"):
                if it.get(f):
                    idx.setdefault(norm(it[f]), it["id"])
            for a in it.get("aka", []):
                idx.setdefault(norm(a), it["id"])
    return idx


MAT = _alias_index(["materials"])
STRUCT = _alias_index(["structures"])
PREC = _alias_index(["precursors"])
CORE = _alias_index(["coreactants"])
PROC = _alias_index(["process_types"])
QK = {}                      # quantity alias -> canonical id
QK_META = {q["id"]: q for q in ONTO["quantity_kinds"]}
for q in ONTO["quantity_kinds"]:
    QK[norm(q["id"])] = q["id"]
    for a in q.get("aliases", []):
        QK.setdefault(norm(a), q["id"])
    for s in q.get("symbols", []):
        QK.setdefault(norm(s), q["id"])


def canon_material(s):    return MAT.get(norm(s))
def canon_structure(s):   return STRUCT.get(norm(s))
def canon_precursor(s):   return PREC.get(norm(s))
def canon_coreactant(s):  return CORE.get(norm(s))
def canon_process(s):     return PROC.get(norm(s))
def canon_quantity(s):    return QK.get(norm(s))
def axis_role(qid):       return (QK_META.get(qid) or {}).get("axis_role")

# ---- quantity families + transforms (comparability layer, P1) -------------
_QR = ONTO.get("quantity_relations", {}) or {}
FAMILIES = _QR.get("families", {}) or {}
TRANSFORMS = _QR.get("transforms", []) or []
FAMILY = {q["id"]: q.get("family") for q in ONTO["quantity_kinds"]}
def family(qid):          return FAMILY.get(qid)
RECIPE_ROLE = {q["id"]: q.get("recipe_role") for q in ONTO["quantity_kinds"]}
def recipe_role(qid):     return RECIPE_ROLE.get(qid)   # control_setting=in recipe

# species intrinsic properties (molar_mass, molecular_diameter, central_atoms)
SPECIES_PROP = {}
for _g in ("precursors", "coreactants"):
    for _it in ONTO["individuals"].get(_g, []):
        _p = {k: _it[k] for k in ("molar_mass", "molecular_diameter", "central_atoms") if k in _it}
        for _k in [_it["id"], _it.get("formula"), _it.get("full_name")] + (_it.get("aka") or []):
            if _k:
                SPECIES_PROP[str(_k)] = _p
def species_prop(sp, prop): return (SPECIES_PROP.get(str(sp)) or {}).get(prop) if sp else None


#: the part of an axis label that states its UNIT -- parenthesised, bracketed, or after a
#: '/' or ',' separator. Words from here describe the scale, not the quantity, so they may
#: be dropped without losing meaning.
_UNIT_REGION = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]|[/,]\s*(.+)$")


def _unit_words(label):
    return {t for m in _UNIT_REGION.finditer(str(label))
            for g in [next((x for x in m.groups() if x), "")]
            for t in re.sub(r"[^a-z0-9 ]", " ", g.lower()).split()}


#: Words that make the axis a DIFFERENT measurand from the quantity named beside them.
#: A ratio of two flows is not a flow, so truncating "flow ratio" to "flow" changes what
#: is being measured -- unlike qualifiers ("above background", "degree", "by XRR"), which
#: describe the same measurand and must keep resolving.
#:
#: One word, because one word is what the corpus evidences. "fraction", "percentage",
#: "proportion" and "quotient" were carried here on the same intuition and are removed:
#: none was needed for any observed correction, and "fraction" is actively wrong --
#: "coverage fraction" IS a surface coverage, but the word is absent from that quantity's
#: vocabulary, so a blanket veto refuses a correct reading. Plausibility is not evidence;
#: a word joins this set when a real label proves it must.
#:
#: A quantity whose own vocabulary contains the word is exempt, so "aspect ratio" still
#: resolves to aspect_ratio.
_TRANSFORMS_MEASURAND = {"ratio"}


def _quantity_words(qid):
    """Every word the ontology itself uses for this quantity."""
    m = QK_META.get(qid) or {}
    return {t for s in [m.get("id", "")] + list(m.get("aliases") or [])
            for t in str(s).lower().replace("_", " ").split()}


def resolve_axis_label(label):
    """Canonicalise a plot AXIS LABEL to a quantity id. Strips '(units)',
    ln/log wrappers and symbol subscripts, then tries the full label and
    progressively shorter prefixes against ontology aliases (so a trailing
    'x' / 'x̃' subscript doesn't block the match).

    The prefix ladder used to have no floor: it dropped trailing words until ANY candidate
    matched, so a label opening with a one-letter symbol always found that symbol's
    quantity no matter what followed. "H_2 flow ratio" resolved to feature_height on the
    bare "h" -- a dimensionless gas ratio asserted to be a geometric height, on a planar
    film with no features. "W thickness" became feature_width, "Ar Sputter Time" became
    aspect_ratio.

    So a BARE SYMBOL may only win if nothing meaningful was thrown away to reach it. A
    dropped word is meaningless here when it is a digit, a single letter (a subscript), a
    word from the label's unit region, or a word the ontology already uses for that very
    quantity -- which is what keeps the genuine subscript forms working: "deposition"
    belongs to deposition_temperature, "chamber" to total_pressure, "channel" to
    feature_length. "flow" and "ratio" belong to no reading of feature_height, so the
    match is refused and the axis stays honestly unresolved.

    Refusing is the whole point: the ontology has no flow-ratio quantity, and an
    unresolved axis keeps its raw label and values while claiming nothing.
    """
    return axis_label_match(label)[0]


def axis_label_match(label):
    """-> (quantity_id, winning_candidate) for the ladder above.

    The candidate is what the caller needs to judge how STRONG the reading is: a match on
    a spelled-out name or a multi-word alias states the quantity outright, while a match
    on a bare one- or two-character symbol is the weakest evidence the ontology admits --
    the same letter routinely means different things in different fields ("j" is a
    molecular flux here and a current density in electrochemistry). Callers that hold
    independent evidence can use that distinction; this function never guesses for them.
    """
    if not label:
        return None, None
    units = _unit_words(label)
    s = str(label).lower()
    s = re.sub(r"\b(ln|log10|log)\b", " ", s)        # drop log wrappers (keyword)
    s = re.sub(r"[^a-z0-9 ]", " ", s)                # drop ALL symbols incl. parens (keep content)
    toks = [t for t in s.split() if t]
    cands = [(label, None)]
    for k in range(len(toks), 0, -1):                # full -> drop trailing tokens
        cands.append(("_".join(toks[:k]), k))
        cands.append((" ".join(toks[:k]), k))
    for c, k in cands:
        qid = QK.get(norm(c))
        if not qid:
            continue
        if k is not None:
            words = _quantity_words(qid)
            dropped = toks[k:]
            # A discarded word that TRANSFORMS the measurand is fatal at any match
            # length. "flow ratio" truncated to "flow" became flow_rate -- but a
            # dimensionless ratio of two flows is not a flow. The bare-symbol rule below
            # never caught it, because "flow" is four characters. Qualifiers that merely
            # describe the same measurand are untouched: an intensity above background is
            # still an intensity, a coverage degree is still a coverage.
            if any(t in _TRANSFORMS_MEASURAND and t not in words for t in dropped):
                continue
            if len(norm(c)) <= 2 and any(
                    not (t.isdigit() or len(t) <= 1 or t in units or t in words)
                    for t in dropped):
                continue                             # descriptive text this reading ignores
        return qid, c
    return None, None


def is_bare_symbol(candidate):
    """Whether a winning label candidate is only a short ontology symbol."""
    return bool(candidate) and len(norm(candidate)) <= 2


# ---- physical dimension, derived from the ontology's own unit ---------------
#: QUDT locals the ontology uses, spelled the way the unit parser reads them. This is a
#: TRANSCRIPTION of an IRI into a unit string, not a second opinion about physics: the
#: dimension still comes from parsing the unit the ontology already declares.
_QUDT_UNIT = {
    "DEG_C": "°C", "K": "K", "SEC": "s", "HR": "h", "MIN": "min",
    "NanoM": "nm", "MicroM": "um", "MilliM": "mm", "CentiM": "cm", "M": "m",
    "ANGSTROM": "A", "PA": "Pa", "KiloPA": "kPa", "BAR": "bar", "TORR": "torr",
    "PERCENT": "%", "UNITLESS": "1", "NUM": "1", "DEG": "deg", "RAD": "rad",
}

#: Quantities whose dimension the ontology states in a form the parser cannot read, and
#: which are scientifically unambiguous. Kept deliberately tiny -- this is an EXCEPTION
#: list, not a dimension registry. A long list here would mean the derivation is wrong.
#: Each entry names the ontology unit it stands in for.
_DIM_OVERRIDE = {
    # ontology unit "1/m2" / "1/(m2 s)" -- an inverse-area count the parser has no
    # dimension for; site density is unambiguous.
    "site_density": ({"reciprocal_area", "count"}, "ontology unit 1/m2 not parseable"),
}


def _unit_for_dimension(unit):
    """The ontology's declared unit as a string the unit parser can attempt."""
    if not unit:
        return None
    s = str(unit)
    return _QUDT_UNIT.get(s.rsplit("/", 1)[-1], s) if s.startswith("http") else s


def quantity_unit(qid):
    """The unit the ontology declares for a quantity, as a parseable string.

    Returned as a STRING rather than a dimension so the caller can derive the dimension
    with the very function it uses for observed units. Two derivations would otherwise
    speak two vocabularies -- one saying `dimensionless` where the other says `percent` --
    and the guard would reject correct pairings on a naming difference alone.
    """
    meta = QK_META.get(qid) or {}
    return _unit_for_dimension(meta.get("unit"))


def quantity_dimension(qid):
    """-> (set_of_dimension_names or None, basis)

    The ontology already records what each quantity is measured in. Deriving the
    dimension from that declaration keeps ONE source of truth: a hand-kept table beside
    it can only drift, and the table that existed covered 21 of 181 quantities, which is
    why a current density could be read as a molecular flux and a capacitance as a
    probability -- neither had a dimension for the guard to check.

    `None` means genuinely unknown, and unknown is a legitimate answer: it is not the
    same as dimensionless, and nothing is invented to fill the gap.
    """
    if not qid:
        return None, "no quantity"
    if qid in _DIM_OVERRIDE:
        dims, why = _DIM_OVERRIDE[qid]
        return set(dims), "override: %s" % why
    meta = QK_META.get(qid) or {}
    raw = meta.get("unit")
    u = _unit_for_dimension(raw)
    if not u:
        return None, "ontology declares no unit"
    if u in ("1", "%") or "UNITLESS" in str(raw):
        return {"dimensionless"}, "ontology declares the quantity unitless"
    try:
        from pipeline.canonical import units as _U
        p = _U.try_parse(u)
        d = _U.DIM_NAME.get(p.dimension) if p else None
    except Exception:
        d = None
    if d:
        return {d}, "derived from ontology unit %r" % u
    return None, "ontology unit %r is not parseable" % u


# ---- compact ontology vocab for prompts -----------------------------------
def vocab():
    mats = [m["formula"] for m in ONTO["individuals"]["materials"] if m.get("formula")]
    procs = [p["id"] for p in ONTO["classes"] if p.get("parent") == "ProcessType"]
    quant = [(q["id"], (q.get("aliases") or [])[:2], q.get("unit"))
             for q in ONTO["quantity_kinds"]]
    return mats, procs, quant


# ---- Gemini ---------------------------------------------------------------
