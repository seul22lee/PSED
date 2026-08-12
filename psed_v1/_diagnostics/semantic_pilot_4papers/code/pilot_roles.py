#!/usr/bin/env python3
"""
pilot_roles.py — the two role vocabularies the pilot needs, and nothing more.

  · condition role : CASE_DEFINING vs MEASUREMENT_SETTING (plus MODEL_PARAMETER and
    DERIVED, which already exist in the ontology and must not be collapsed into either)
  · material role  : DEPOSITED / SUBSTRATE / SUPPORT / TEMPLATE / STACK_COMPONENT

Both are deliberately small. The condition role is decided from the ontology's own
`recipe_role` wherever that is decisive, and from a generic instrument lexicon where it
is not. No paper, DOI or figure is named anywhere in this module.
"""
import json
import re
from pathlib import Path

_ONTO = json.loads((Path(__file__).resolve().parent.parent / "ontology"
                    / "ald_ontology.json").read_text())
_QK = {q["id"]: q for q in _ONTO["quantity_kinds"]}

CASE_DEFINING = "CASE_DEFINING"
MEASUREMENT_SETTING = "MEASUREMENT_SETTING"
MODEL_PARAMETER = "MODEL_PARAMETER"
DERIVED = "DERIVED"
UNRESOLVED_ROLE = "UNRESOLVED"

#: Quantities that configure an INSTRUMENT rather than a deposition. Matched on the
#: quantity id and on the raw axis/label text, because an instrument setting frequently
#: has no ontology QuantityKind at all (a reflectometer objective is not an ALD quantity).
_INSTRUMENT = re.compile(
    r"\b(?:objective|magnificat\w+|spot[\s_-]?size|numerical[\s_-]?aperture|"
    r"accelerating[\s_-]?voltage|beam[\s_-]?(?:current|energy|voltage)|"
    r"scan[\s_-]?(?:rate|speed|resolution|length|range|area)|"
    r"step[\s_-]?size|dwell[\s_-]?time|integration[\s_-]?time|"
    r"take[\s_-]?off[\s_-]?angle|incidence[\s_-]?angle|detector|"
    r"sputter(?:ing)?[\s_-]?(?:time|rate)|etch(?:ing)?[\s_-]?time|"
    r"pass[\s_-]?energy|resolution|working[\s_-]?distance|"
    r"reference[\s_-]?electrode|electrolyte|sweep[\s_-]?rate|"
    r"potential[\s_-]?window|frequency[\s_-]?range|amplitude)\b", re.I)

#: Instrument axes: an x axis of this kind is a measurement coordinate, so its points are
#: observations of one specimen and can never be separate depositions.
_MEASUREMENT_AXIS = {
    "binding_energy", "wavelength", "wavenumber", "photon_energy", "frequency",
    "potential", "angle", "two_theta", "2theta", "raman_shift", "sputter_depth",
    "sputtering_time", "etching_time", "magnetic_field", "energy",
}

#: Axis roles the ontology/axis layer already assigns to non-process axes.
_MEASUREMENT_AXIS_ROLES = {"measurement_coordinate", "spatial_coordinate",
                           "derived_coordinate", "response_coordinate"}


def condition_role(quantity, raw_label=None, evidence_kind=None, axis_role=None):
    """Role of one condition. Returns (role, basis).

    Order matters and is chosen so the most specific evidence wins:
      1. an explicit model-input provenance is a model parameter, never a deposition
         condition (this is what keeps the simulation branch separate);
      2. an instrument word in the quantity or its printed label is a measurement
         setting even if the ontology gave the quantity a control_setting role
         (`etching_time` is an ALD-shaped name for an XPS sputter clock);
      3. the ontology's own recipe_role decides the rest;
      4. anything else is UNRESOLVED — never silently case-defining.
    """
    q = str(quantity or "")
    lab = str(raw_label or "")
    if evidence_kind == "model_input":
        return MODEL_PARAMETER, "assertion evidence_kind = model_input"
    if _INSTRUMENT.search(q) or _INSTRUMENT.search(lab):
        m = _INSTRUMENT.search(q) or _INSTRUMENT.search(lab)
        return MEASUREMENT_SETTING, "instrument term %r in the quantity/label" % m.group(0)
    if q in _MEASUREMENT_AXIS or lab.strip().lower() in _MEASUREMENT_AXIS:
        return MEASUREMENT_SETTING, "%r is an instrument coordinate" % (q or lab)
    if axis_role in _MEASUREMENT_AXIS_ROLES:
        return MEASUREMENT_SETTING, "axis_role = %s" % axis_role
    rr = (_QK.get(q) or {}).get("recipe_role")
    if rr == "control_setting":
        return CASE_DEFINING, "ontology recipe_role = control_setting"
    if rr == "structure":
        return CASE_DEFINING, "ontology recipe_role = structure (sample geometry)"
    if rr == "model_parameter":
        return MODEL_PARAMETER, "ontology recipe_role = model_parameter"
    if rr in ("derived", "observable"):
        return DERIVED, "ontology recipe_role = %s" % rr
    if rr == "species_property":
        return DERIVED, "ontology recipe_role = species_property"
    return UNRESOLVED_ROLE, ("no ontology recipe_role for %r and no instrument term" % q
                             if q else "no quantity")


def is_case_defining(quantity, raw_label=None, evidence_kind=None, axis_role=None):
    return condition_role(quantity, raw_label, evidence_kind, axis_role)[0] == CASE_DEFINING


# --------------------------------------------------------------------- material role
DEPOSITED = "DEPOSITED"
SUBSTRATE = "SUBSTRATE"
SUPPORT = "SUPPORT"
TEMPLATE = "TEMPLATE"
STACK_COMPONENT = "STACK_COMPONENT"

#: Each pattern has ONE capture group for the material name. `{M}` is substituted with an
#: alternation of the paper's own material names, so a role is only ever assigned to a
#: material the paper actually reports.
_ROLE_PATTERNS = [
    (SUBSTRATE, r"(?:on|onto|over)\s+(?:an?\s+|the\s+)?(?:\S+\s+){0,2}?({M})\s+"
                r"(?:substrates?|wafers?|slides?)"),
    (SUBSTRATE, r"({M})\s+(?:substrates?|wafers?)"),
    (SUBSTRATE, r"(?:substrates?|wafers?)\s+of\s+({M})"),
    (SUBSTRATE, r"(?:on\s+top\s+of|deposited\s+on\s+top\s+of|over)\s+"
                r"(?:\S+\s+){0,3}?({M})\s+layers?"),
    (SUPPORT, r"({M})\s+(?:supports?|particles?|powders?|nanoparticles?|nanotubes?|"
              r"scaffolds?|membranes?|frameworks?)"),
    (SUPPORT, r"(?:supported\s+on|deposited\s+on|grown\s+on|coated\s+on)\s+"
              r"(?:an?\s+|the\s+)?({M})\b"),
    (TEMPLATE, r"({M})\s+(?:templates?|moulds?|molds?|sacrificial\s+\w+)"),
    (TEMPLATE, r"(?:templates?|moulds?|molds?)\s+of\s+({M})"),
    (STACK_COMPONENT, r"({M})\s*/\s*\w+\s+(?:stacks?|bilayers?|laminates?|multilayers?)"),
    (STACK_COMPONENT, r"\w+\s*/\s*({M})\s+(?:stacks?|bilayers?|laminates?|multilayers?)"),
    (STACK_COMPONENT, r"({M})\s+(?:capping|cap|barrier|passivation|encapsulation)\s+layers?"),
    (DEPOSITED, r"(?:ALD|atomic layer deposition|deposition|deposit\w*|growth|grown|"
                r"gr[eo]w\w*|coating|coated)\s+(?:of\s+|the\s+)?(?:\S+\s+){0,2}?({M})\b"),
    (DEPOSITED, r"({M})\s+(?:films?|layers?|coatings?|thin films?|replicas?|"
                r"nanotubes?\s+grown)"),
    (DEPOSITED, r"(?:deposit\w*|grow\w*|coat\w*)\s+({M})\b"),
]


#: A clause stating what a chemical is FOR is not a record of a deposition. "…the SAM.24
#: precursor used for ALD of SiO2… This precursor is commonly used for ALD of Al2O3" is a
#: precursor-property sentence, and reading it as two depositions is how a vapour-pressure
#: figure acquired a two-material stack context.
_PURPOSE = re.compile(r"\b(?:used|usable|use|suitable|employed|applied|intended|known|"
                      r"popular|common|commonly|typical|typically|standard)\b", re.I)


def _is_purpose_clause(text, start):
    """True when the material mention at `start` is governed by a purpose phrase.

    The window is the current sentence only, so a purpose word in a previous sentence
    cannot suppress a genuine deposition statement in this one.
    """
    head = text[max(0, start - 90):start]
    cut = max(head.rfind(". "), head.rfind("; "))
    sentence = head[cut + 1:] if cut >= 0 else head
    return bool(_PURPOSE.search(sentence) and re.search(r"\bfor\b", sentence, re.I))


#: Measurands that are properties of a CHEMICAL SPECIES rather than of a deposited film.
#: A scope reporting one of these is precursor/reagent characterisation: it has no
#: deposited material of its own, so it may contribute material candidates but never an
#: asserted local role, and it never mints a deposition case.
SPECIES_PROPERTY_MEASURANDS = {
    "vapor_pressure", "vapour_pressure", "molar_mass", "molecular_mass",
    "molecular_diameter", "precursor_molecular_diameter", "boiling_point",
    "melting_point", "sublimation_enthalpy", "vapour_density", "viscosity",
    "decomposition_temperature", "thermogravimetric_mass", "mass_loss",
}
_SPECIES_PROPERTY_HINT = re.compile(r"vapou?r[_\s-]?pressure|molar[_\s-]?mass|"
                                    r"molecular[_\s-]?(?:mass|weight|diameter)|"
                                    r"sublimation|thermogravimetric", re.I)


def is_species_property(measurand, coordinate=None):
    """(True, reason) when a scope measures a property of a chemical, not of a film."""
    for q in (measurand, coordinate):
        qq = str(q or "")
        if qq in SPECIES_PROPERTY_MEASURANDS or _SPECIES_PROPERTY_HINT.search(qq):
            return True, ("%r is a property of a chemical species, not of a deposited "
                          "film" % qq)
    return False, None


def _alt(materials):
    return "|".join(re.escape(m) for m in sorted(materials, key=len, reverse=True) if m)


def material_roles(text, materials):
    """Roles for each of the paper's materials, from one block of source text.

    Returns {material: [{role, matched, span, pattern_role}]}. A material may legitimately
    receive several roles across a paper (SiO2 is deposited in one figure and is the
    substrate in another); nothing here collapses them.
    """
    mats = [m for m in (materials or []) if m]
    if not mats or not text:
        return {}
    alt = _alt(mats)
    lower = {m.lower(): m for m in mats}
    out = {}
    for role, tmpl in _ROLE_PATTERNS:
        rx = re.compile(tmpl.replace("{M}", alt), re.I)
        for m in rx.finditer(text):
            name = lower.get(m.group(1).lower())
            if not name:
                continue
            if role == DEPOSITED and _is_purpose_clause(text, m.start(1)):
                continue
            a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
            rec = {"role": role, "matched": re.sub(r"\s+", " ", m.group(0)).strip()[:120],
                   "span": re.sub(r"\s+", " ", text[a:b]).strip()}
            bucket = out.setdefault(name, [])
            if not any(r["role"] == role and r["matched"] == rec["matched"] for r in bucket):
                bucket.append(rec)
    return out


#: geometry evidence in a figure/panel scope, mapped onto the ontology's own
#: geometry_class vocabulary. A scope that says nothing yields nothing — the paper-level
#: default is then used, and the fact that it IS a default is recorded.
_GEOMETRY_SCOPE = [
    (re.compile(r"\b(?:high[- ]aspect[- ]ratio|HAR)\b|\baspect ratio\b|\btrench(?:es)?\b|"
                r"\bvia(?:s)?\b|\bdeep hole", re.I), "vertical_structure"),
    (re.compile(r"\blateral(?:ly)? (?:high[- ]aspect|channel)|\bLHAR\b|\bPillarHall\b",
                re.I), "lateral_channel"),
    (re.compile(r"\bporous\b|\bmesoporous\b|\bnanoporous\b|\bAAO\b|\bmembrane\b|"
                r"\bpowder\b|\bparticles?\b", re.I), "porous_material"),
    (re.compile(r"\bplanar\b|\bblanket\b|\bflat (?:wafer|substrate)\b|"
                r"\bSi\(100\)\b|\bsilicon wafer\b", re.I), "planar"),
]


def geometry_in_scope(text):
    """(geometry_class, matched_text) declared by one figure/panel scope, or (None, None).

    The most specific match wins: a caption that says both "trench" and "planar" is
    reporting a structured feature, and reading it as planar would erase the point of the
    experiment. `planar` is therefore tested last.
    """
    for rx, gc in _GEOMETRY_SCOPE:
        m = rx.search(text or "")
        if m:
            return gc, re.sub(r"\s+", " ", m.group(0))
    return None, None


def primary_role(role_records):
    """The single role best supported for one material in one scope, or None.

    DEPOSITED needs to lose to a more specific role when both fire, because "ALD of Pt on
    the TiO2 support" matches the deposition pattern for Pt AND the support pattern for
    TiO2 — the specific role is the informative one.
    """
    if not role_records:
        return None
    order = [SUBSTRATE, SUPPORT, TEMPLATE, STACK_COMPONENT, DEPOSITED]
    counts = {}
    for r in role_records:
        counts[r["role"]] = counts.get(r["role"], 0) + 1
    for role in order:
        if role in counts:
            return role
    return None
