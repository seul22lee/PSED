#!/usr/bin/env python3
"""
roles.py — the two role vocabularies the semantic layer needs, and nothing more.

  · condition role : CASE_DEFINING vs MEASUREMENT_SETTING (plus MODEL_PARAMETER and
    DERIVED, which already exist in the ontology and must not be collapsed into either)
  · material role  : DEPOSITED / SUBSTRATE / SUPPORT / TEMPLATE / STACK_COMPONENT

Both are deliberately small. The condition role is decided from the ontology's own
`recipe_role` wherever that is decisive, and from a generic instrument lexicon where it
is not. No paper, DOI or figure is named anywhere in this module.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import paths as _P                                              # noqa: E402

_ONTO = json.loads(_P.ONTOLOGY_JSON.read_text())
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
    # "The SiO2 was covered by an Al2O3 film" -- the covering layer is a component of the
    # stack, not a second thing this experiment set out to deposit. Without this the two
    # constituents of a capped film both read as DEPOSITED and the stack disappears.
    (STACK_COMPONENT, r"(?:covered|capped|overcoated|encapsulated)\s+(?:by|with)\s+"
                      r"(?:an?\s+|the\s+)?({M})"),
    (STACK_COMPONENT, r"({M})\s+(?:over|on\s+top\s+of)\s+(?:the\s+)?\w*\s*"
                      r"(?:film|layer)s?\b"),
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


#: The BULK property of a substance: how much of it remains, or how much heat it takes.
#: On its own this proves nothing -- a QCM curve also reports mass -- so it is only read
#: as a species property when the scope also identifies WHICH CHEMICAL is being weighed.
_SUBSTANCE_BULK = re.compile(
    r"^\s*(?:weight|mass|residual\s*(?:weight|mass)|tg|tga|dsc|dta|"
    r"heat\s*flow|derivative\s*weight)\b(?!\s*(?:gain|uptake|per\s*area))", re.I)
#: A ramped thermal-analysis abscissa. Its points are stages of ONE run, not specimens.
_RAMP_COORD = re.compile(r"^(?:temperature|time|inverse_temperature)$", re.I)


#: Unicode formula typography, mapped one character to one so a match position found in
#: the normalised text still points at the same place in the raw text. This is the
#: repository's conservative species normalisation -- subscripts and superscripts printed
#: as such -- and deliberately not a chemical-synonym resolver.
CHEM_NORM = str.maketrans({
    **{c: str(i) for i, c in enumerate("₀₁₂₃₄₅₆₇₈₉")},
    **{c: str(i) for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")},
    "ᵗ": "t", "ⁿ": "n", "ˢ": "s", "ᵇ": "b", "ⁱ": "i", "·": "-", "⋅": "-",
})

#: A character that CONTINUES a chemical token. A reagent running straight into one of
#: these is a fragment of a longer formula rather than the formula itself. Brackets are
#: directional: an opening bracket on the right starts a ligand (Y -> Y(sBuCp)3), a
#: closing bracket on the left ends one. Enclosing punctuation is therefore not
#: continuation, so a parenthesised "(Pt(acac)2)" still names Pt(acac)2.
_CHEM_LEFT = re.compile(r"[A-Za-z0-9)\]\-]")
_CHEM_RIGHT = re.compile(r"[A-Za-z0-9(\[\-]")


def chem_norm(s):
    return str(s or "").translate(CHEM_NORM)


def complete_species_span(text, species):
    """The longest reagent from `species` that occupies a COMPLETE chemical span in `text`.

    Substring containment is not naming. "H2O dose" contains the characters of H2 and
    "MoCl2O2 pulse" contains those of Mo, but neither label names that reagent: the
    letters belong to a longer formula. Attributing on such a match asserts the wrong
    chemical, and a longer reagent happening to also be present only hides the bad
    candidate rather than excluding it.

    So a candidate has to occupy a whole chemical span -- neither end running into a
    character that would continue the token -- before it is a candidate at all. Among
    those that do, the longest wins, which is specificity between real readings rather
    than a guard against false ones.
    """
    t = chem_norm(text)
    for sp in sorted([s for s in (species or []) if s], key=lambda x: len(str(x)),
                     reverse=True):
        pat = chem_norm(sp)
        if not pat:
            continue
        for m in re.finditer(re.escape(pat), t, re.I):
            i, j = m.start(), m.end()
            if i and _CHEM_LEFT.match(t[i - 1]):
                continue
            if j < len(t) and _CHEM_RIGHT.match(t[j]):
                continue
            return sp
    return None


def species_named_in(text, species):
    """The chemical from `species` that this text names outright, or None.

    A curve labelled with a precursor formula reports on THAT MOLECULE. The label is the
    author identifying the substance, which is exactly the context a bulk-property
    measurand needs before it can be read as characterisation rather than deposition.
    """
    t = str(text or "")
    for sp in sorted([s for s in (species or []) if s], key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(str(sp)), t, re.I):
            return sp
    return None


def is_species_property(measurand, coordinate=None, scope_label=None, species=()):
    """(True, reason) when a scope measures a property of a chemical, not of a film.

    Two independent routes. Either the measurand is inherently a property of a substance
    (a vapour pressure belongs to a molecule, never to a film), or it is a bulk property
    -- weight, heat flow -- measured against a thermal ramp on a curve whose own label
    names one of the paper's reagents. The second route is what distinguishes a
    thermogravimetric trace of a precursor from a QCM mass-gain curve of a growing film:
    both plot a mass, only one of them names the molecule it is weighing.
    """
    for q in (measurand, coordinate):
        qq = str(q or "")
        if qq in SPECIES_PROPERTY_MEASURANDS or _SPECIES_PROPERTY_HINT.search(qq):
            return True, ("%r is a property of a chemical species, not of a deposited "
                          "film" % qq)
    # A pressure plotted against INVERSE temperature is a Clausius-Clapeyron construction.
    # That transform exists to extract the enthalpy of vaporisation or sublimation of a
    # substance; it is never a deposition sweep, because 1/T is a way of drawing
    # temperature rather than a setting anyone dialled in.
    if (re.search(r"pressure", str(measurand or ""), re.I)
            and re.match(r"^inverse_temperature$", str(coordinate or ""), re.I)):
        sp = species_named_in(scope_label, species)
        return True, ("%r against %r is a Clausius-Clapeyron plot%s; it characterises the "
                      "volatility of a substance, not a film"
                      % (measurand, coordinate, (" for %s" % sp) if sp else ""))
    if _SUBSTANCE_BULK.search(str(measurand or "")) and _RAMP_COORD.search(
            str(coordinate or "")):
        sp = species_named_in(scope_label, species)
        if sp:
            return True, ("%r is measured against a %s ramp on a curve labelled %r, which "
                          "names the reagent %s; the scope weighs a chemical, not a film"
                          % (measurand, coordinate, scope_label, sp))
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
    # Most specific first. A lateral-channel scope routinely also says "high aspect
    # ratio", so the lateral wording must be tested before the vertical one -- and a
    # bare "aspect ratio" is the name of a QUANTITY every structured geometry has,
    # never evidence for one class, so it appears in no pattern at all.
    (re.compile(r"\blateral(?:ly)? (?:high[- ]aspect|channel)|\bLHAR\b|\bPillarHall\b"
                r"|\bchannel gap\b", re.I), "lateral_channel"),
    (re.compile(r"\bporous\b|\bmesoporous\b|\bnanoporous\b|\bAAO\b|\bmembrane\b|"
                r"\bpowder\b|\bparticles?\b", re.I), "porous_material"),
    # 'via' only in its interconnect sense -- the bare singular is the English
    # preposition (same demonstrated false-positive class as the paper-level
    # classifier's repair)
    (re.compile(r"\b(?:high[- ]aspect[- ]ratio|HAR)\b|\btrench(?:es)?\b|"
                r"\bvias\b|\bvia hole|\bvia structure|through[- ]silicon|"
                r"\bdeep hole", re.I), "vertical_structure"),
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


# ---------------------------------------------------------------- measurand repair
#: Physical family of a quantity token. Canonicalisation legitimately rewrites a raw
#: token into a synonym or a generalisation WITHIN a family (growth_per_cycle ->
#: growth_rate, partial_pressure -> total_pressure). It must never move a quantity
#: ACROSS families: that is a collision, not a normalisation.
_FAMILY = {
    "growth": ("growth_per_cycle", "growth_rate", "thickness_per_cycle", "gpc"),
    "length": ("thickness", "film_thickness", "depth", "height", "diameter",
               "roughness", "crystallite_size", "penetration_depth"),
    "pressure": ("pressure", "partial_pressure", "total_pressure", "vapor_pressure",
                 "working_pressure"),
    "temperature": ("temperature", "deposition_temperature", "substrate_temperature",
                    "growth_temperature", "source_temperature"),
    "time": ("pulse_time", "purge_time", "exposure_time", "deposition_time",
             "process_time", "residence_time"),
    "progression": ("cycle_number", "ncycles", "number_of_cycles"),
    "optical": ("refractive_index", "extinction_coefficient", "absorbance",
                "transmittance", "reflectance", "band_gap"),
    "mass": ("mass", "areal_mass", "mass_gain", "mass_per_cycle"),
    "electrical": ("resistivity", "conductivity", "sheet_resistance", "capacitance",
                   "current_density", "carrier_lifetime"),
    "composition": ("atomic_fraction", "concentration", "impurity_content", "density"),
}
_FAMILY_OF = {q: fam for fam, qs in _FAMILY.items() for q in qs}


def measurand_of(ent):
    """(quantity, unit, note) for an entity's measured quantity.

    The canonical quantity is used as-is unless it CONTRADICTS the raw axis label that
    the same record carries. A single-letter axis label is the usual cause: "n" is the
    refractive index on an optical plot and the cycle count on a growth plot, and a
    canonicaliser that resolves it without the label's own reading silently retypes the
    measurement. When both tokens have a known family and the families differ, the raw
    quantity wins -- it is what the author printed on the axis -- and the disagreement
    is recorded rather than hidden.
    """
    q = ent.get("measurand")
    unit = ent.get("measurand_unit")
    ys = ent.get("y_semantics") or {}
    raw = ys.get("raw_quantity")
    if not raw or not q or raw == q:
        return q, unit, None
    fr, fq = _FAMILY_OF.get(raw), _FAMILY_OF.get(q)
    if not fr or not fq or fr == fq:
        return q, unit, None
    return raw, (ys.get("raw_unit") or unit), (
        "the axis label %r reads as %s (%s) but the canonical quantity is %s (%s); the "
        "printed axis label is authoritative and the canonical value is a collision"
        % (ys.get("raw_label"), raw, fr, q, fq))


# ------------------------------------------------- deposited structure identity
#: A quantity that names the STRUCTURE of the deposited object rather than a setting of
#: the process that made it or a property measured afterwards. A film thickness is
#: normally an OUTCOME -- it is what the deposition produced -- but when it is what
#: distinguishes one specimen from another it identifies the deposited object itself, and
#: a specimen set that differs only in deposited structure has no other case-defining
#: dimension at all. The same holds for a layer sequence: "single layer A" and "A over B"
#: are different deposited objects however identical the recipe that grew each layer.
_STRUCTURE_QUANTITY = re.compile(
    r"\bthickness(?:es)?\b|\bnumber\s+of\s+layers\b|"
    r"\b(?:layer|stack|laminate|bilayer|multilayer|overlayer|coating)\s*"
    r"(?:structure|composition|sequence|configuration|design|status)?\b", re.I)
#: "12 nm SiO2", "SiO2 (12 nm)", "~30 nm Al2O3" -- one layer of a stack expression.
_LAYER = re.compile(
    r"(?:[~\u223c\u2248]?\s*(?P<t1>\d+(?:\.\d+)?)\s*(?P<u1>nm|\u00b5m|um|\u03bcm|\u00c5)\s*)?"
    r"(?P<mat>[A-Za-z][A-Za-z0-9]*(?:[A-Z][a-z]?\d*)*)"
    r"(?:\s*\(\s*[~\u223c\u2248]?\s*(?P<t2>\d+(?:\.\d+)?)\s*(?P<u2>nm|\u00b5m|um|\u03bcm|\u00c5)\s*\))?")


def is_structure_quantity(quantity):
    """(True, reason) when a quantity identifies the deposited structure."""
    q = str(quantity or "")
    m = _STRUCTURE_QUANTITY.search(q)
    if not m:
        return False, None
    return True, ("%r names the structure of the deposited object, not a process setting "
                  "or a measured outcome" % q)


def parse_layer_stack(text, materials=()):
    """[{order, material, thickness, unit}] for a stack expression, or [].

    A layer sequence is written the way the author draws it -- "12 nm SiO2 / 30 nm Al2O3",
    "ALD SiO2 / Al2O3" -- so the separator is the structure. Only materials the paper
    actually works with are accepted, which keeps a stray token from becoming a layer.
    """
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t:
        return []
    known = {str(m).lower() for m in (materials or []) if m}
    parts = [x.strip() for x in re.split(r"\s*/\s*", t) if x.strip()]
    if len(parts) < 2 and not known:
        return []
    layers = []
    for i, part in enumerate(parts):
        best = None
        for m in _LAYER.finditer(part):
            mat = m.group("mat")
            if not mat or (known and mat.lower() not in known):
                continue
            best = {"order": len(layers) + 1, "material": mat,
                    "thickness": float(m.group("t1") or m.group("t2"))
                    if (m.group("t1") or m.group("t2")) else None,
                    "unit": m.group("u1") or m.group("u2"),
                    "raw": part}
        if best:
            layers.append(best)
    return layers if len(layers) >= 1 else []


_CHEMISTRY_DISCRIMINATOR = re.compile(
    r"\bprecursor\b|\breactant\b|\bco-?reactant\b|\boxidant\b|\bchemistry\b", re.I)


def is_chemistry_discriminator(quantity):
    """Whether a between-curve discriminator names WHICH CHEMICAL each curve used."""
    return bool(_CHEMISTRY_DISCRIMINATOR.search(str(quantity or "")))
