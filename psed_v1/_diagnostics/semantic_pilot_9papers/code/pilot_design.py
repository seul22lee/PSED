#!/usr/bin/env python3
"""
pilot_design.py — ExperimentalDesign and DesignBranch, plus the axis-role classifier.

The nine-paper run exposed that the resolver can fail in opposite directions at once:

  UNDER-SPLIT (JES)  a saturation panel plotting GPC against six dose values is ONE case,
                     when the author varied one recipe parameter across six settings and
                     therefore ran six depositions.

  OVER-SPLIT (Yim)   six specimens sharing one recipe, one channel height, one layout and
                     one cycle count are six cases, when they are six realisations of ONE
                     nominal condition.

Both come from the same missing abstraction: nothing between "a plotted point" and "a
case". This module supplies it.

    ExperimentalDesign   the author's plan — one varied variable, a set of branch values,
                         and the conditions held fixed
    DesignBranch         one value of that variable — the unit that a deposition realises

A branch is then NORMALISED on its case-defining conditions, so several branches that
agree on every deposition-defining value collapse to one nominal case while several values
of a genuinely varied parameter stay apart.

No paper, DOI or figure number appears anywhere in this module.
"""
import re
from collections import defaultdict

import pilot_ranges as PRG
import pilot_roles as R

from pipeline.canonical import process_steps as PS

# ------------------------------------------------------------------- axis semantic role
CASE_DEFINING_PROCESS_SETTING = "CASE_DEFINING_PROCESS_SETTING"
PROCESS_PROGRESSION = "PROCESS_PROGRESSION"
MEASUREMENT_COORDINATE = "MEASUREMENT_COORDINATE"
SPATIAL_COORDINATE = "SPATIAL_COORDINATE"
TIME_EVOLUTION = "TIME_EVOLUTION"
REPRESENTATION_COORDINATE = "REPRESENTATION_COORDINATE"

#: Axes that track the PROGRESSION of one growth rather than a set of separate depositions.
#: A thickness-vs-cycle-number curve is one film measured repeatedly, and reading each
#: cycle count as an independent specimen invents depositions the paper never performed.
_PROGRESSION_Q = {"cycle_number", "ncycles", "number_of_cycles", "deposition_time",
                  "process_time", "growth_time", "elapsed_time"}
#: …unless the source says the points ARE separately prepared specimens.
_SEPARATE_SPECIMENS = re.compile(
    r"\b(?:separately|individually)\s+(?:prepared|grown|deposited)\b|"
    r"\bdifferent\s+samples?\s+(?:were\s+)?(?:prepared|grown|deposited)\b|"
    r"\bone\s+sample\s+(?:per|for each)\b|\ba\s+series\s+of\s+samples?\s+(?:was|were)\b",
    re.I)
#: …and the opposite: an explicitly longitudinal monitoring statement.
_LONGITUDINAL = re.compile(
    r"\bmonitored\b[^.]{0,80}\bby\s+taking\s+data\s+points\b|"
    r"\bafter\s+a\s+certain\s+number\s+of\s+cycles\b|"
    r"\bas\s+a\s+function\s+of\s+(?:the\s+)?(?:deposition|process|elapsed)\s+time\b|"
    r"\bduring\s+(?:the\s+)?(?:growth|deposition)\b", re.I)
#: "in situ" is a MEASUREMENT MODE. On its own it says nothing about how many depositions
#: were performed, and treating it as single-run evidence is a documented failure.
_IN_SITU_ONLY = re.compile(r"\bin[\s-]?situ\b", re.I)

_SPATIAL_Q = {"spatial_coordinate", "dimensionless_distance", "position", "depth",
              "distance", "feature_depth", "penetration_depth", "axial_position",
              "normalized_distance", "normalized_position"}

#: A position INSIDE one specimen, written as a ratio against a feature dimension:
#: "x/H", "x/L", "z/D", "normalized distance", "dimensionless depth". Every point of such
#: an axis is the same specimen measured at a different place, so the axis can never be
#: case-defining however the canonicaliser typed it. Any conformality or step-coverage
#: study that plots along a feature uses this convention.
_SPATIAL_LABEL = re.compile(
    r"(?:^|[^A-Za-z])[xyzrl]\s*/\s*[HLDWRhldwr]\b"
    r"|\b(?:normali[sz]ed|dimensionless|relative|fractional|reduced)\s+"
    r"(?:axial\s+|radial\s+|lateral\s+|vertical\s+)?"
    r"(?:distance|position|depth|length|coordinate)\b", re.I)


#: A measurement that RAMPS its own abscissa: thermogravimetry, DSC/DTA, temperature-
#: programmed desorption. The instrument sweeps temperature (or time) while recording a
#: bulk property of whatever was loaded into it. Every point is the same specimen a moment
#: later -- so however the abscissa canonicalises, it cannot be a set of depositions.
_RAMPED_MEASURAND = re.compile(
    r"^\s*(?:weight|mass|residual\s*(?:weight|mass)|tg|tga|dsc|dta|heat\s*flow|"
    r"derivative\s*weight|desorption\s*(?:rate|signal))\b"
    r"(?!\s*(?:gain|uptake|per\s*area))", re.I)
_RAMP_ABSCISSA = re.compile(r"^(?:temperature|deposition_temperature|time|"
                            r"process_time|inverse_temperature)$", re.I)


def axis_role(coordinate, x_axis_role=None, scope_text="", methods_text="",
              raw_label=None, measurand=None):
    """(role, basis) for a plotted x axis.

    Order: an instrument coordinate first (it can never be a deposition setting), then a
    ramped analysis abscissa, then a spatial or progression axis, then the ontology's own
    case-defining verdict.
    """
    q = str(coordinate or "")
    role, basis = R.condition_role(q, None, None, x_axis_role)
    if role == R.MEASUREMENT_SETTING:
        return MEASUREMENT_COORDINATE, basis
    if _RAMPED_MEASURAND.search(str(measurand or "")) and _RAMP_ABSCISSA.search(q):
        return (MEASUREMENT_COORDINATE,
                "%r is measured while the instrument ramps %r; the points are one "
                "specimen recorded through the ramp, not separate depositions"
                % (measurand, q))
    if q in _SPATIAL_Q or x_axis_role == "spatial_coordinate":
        return SPATIAL_COORDINATE, "%r is a spatial coordinate of one specimen" % q
    m = _SPATIAL_LABEL.search(raw_label or "")
    if m:
        return (SPATIAL_COORDINATE,
                "the axis label %r reads as a position within one specimen (%r), so its "
                "points are places on a sample rather than separate depositions"
                % (raw_label, m.group(0).strip()))
    if q in _PROGRESSION_Q:
        text = " ".join([scope_text or "", methods_text or ""])
        if _SEPARATE_SPECIMENS.search(text):
            return (CASE_DEFINING_PROCESS_SETTING,
                    "%r would be a progression axis, but the source states the points are "
                    "separately prepared specimens" % q)
        why = "%r tracks the progression of one growth" % q
        m = _LONGITUDINAL.search(text)
        if m:
            why += "; the source describes it longitudinally (%r)" % (
                re.sub(r"\s+", " ", m.group(0))[:60])
        elif _IN_SITU_ONLY.search(text):
            why += ("; note that the 'in situ' statement in scope is a MEASUREMENT MODE and "
                    "is not by itself evidence either way")
        return PROCESS_PROGRESSION, why
    if role == R.CASE_DEFINING:
        return CASE_DEFINING_PROCESS_SETTING, basis
    return MEASUREMENT_COORDINATE, basis or "no case-defining role for %r" % q


# ------------------------------------------------------------------ design signature
#: A canonical quantity is not a design identity. "Purge time" and "Plasma purge" both
#: canonicalise to `purge_time`, and a SiO2 dose and an Al2O3 dose are both
#: `exposure_time` — merging on quantity+value alone fused eight independent saturation
#: designs into three. The PROCESS STEP and the deposited MATERIAL are part of the identity.
_STEP = [
    (re.compile(r"\bplasma\s*purge\b", re.I), "plasma_purge"),
    (re.compile(r"\bplasma\s*(?:time|exposure|step)\b", re.I), "plasma_exposure"),
    (re.compile(r"\b(?:precursor\s*)?purge\b", re.I), "precursor_purge"),
    (re.compile(r"\b(?:dose|dosing)\s*time\b|\bprecursor\s*(?:dose|exposure|pulse)\b", re.I),
     "precursor_dose"),
    (re.compile(r"\bco-?reactant\s*(?:pulse|dose|exposure)\b", re.I), "coreactant_dose"),
]


#: A quantity whose meaning DEPENDS on which half-cycle it belongs to. A purge time is
#: only defined relative to a step: "4 s purge" is a different parameter after the
#: precursor than after the plasma. A deposition temperature, a chamber pressure or a
#: plasma power belongs to the whole run and is fully identified without a step.
_STEP_SCOPED = re.compile(r"pulse|purge|dose|exposure|residence|soak", re.I)

#: The step field for a quantity that HAS no step. Distinct from UNKNOWN: "not
#: applicable" is a positively known fact about the quantity, whereas "unknown" is the
#: absence of evidence and must never license a merge.
NOT_APPLICABLE = "n/a"


def process_step(raw_label, quantity=None):
    """The recipe step a swept axis belongs to.

    Three outcomes, and the difference between the last two matters:
      * a step name, read from the axis label the paper printed;
      * NOT_APPLICABLE, when the quantity is not step-scoped at all;
      * None, when the quantity IS step-scoped but the label does not say which step --
        a genuine unknown, which must block any identification with another design.
    """
    for rx, step in _STEP:
        if rx.search(str(raw_label or "")):
            return step
    if not _STEP_SCOPED.search("%s %s" % (raw_label or "", quantity or "")):
        return NOT_APPLICABLE
    return None


#: A field whose value is not known. Two such fields are NOT equal — an unknown material
#: is not evidence that two designs deposit the same thing, it is the absence of evidence.
UNKNOWN = "?"


def design_signature(quantity, raw_label=None, unit=None, material=None):
    """The identity of an ExperimentalDesign — what makes two sweeps THE SAME design.

    Two panels share a design only when they vary the same quantity, in the same recipe
    step, in the same units, on the same deposited material.
    """
    return ("q=%s" % (quantity or UNKNOWN),
            "step=%s" % (process_step(raw_label, quantity) or UNKNOWN),
            "unit=%s" % (unit or UNKNOWN),
            "material=%s" % (material or UNKNOWN))


def signatures_identify_same_design(a, b):
    """(same, reason) for two design signatures.

    Equality of the tuples is NOT sufficient. Every field must be POSITIVELY known on
    both sides and equal; a field that is unknown anywhere blocks the identification.
    This is the generic form of "missing is not the same as same", applied to design
    identity rather than to conditions.
    """
    a, b = list(a or []), list(b or [])
    if not a or not b or len(a) != len(b):
        return False, "one or both designs have no signature"
    for fa, fb in zip(a, b):
        name, _, va = fa.partition("=")
        _, _, vb = fb.partition("=")
        if va == UNKNOWN or vb == UNKNOWN:
            return False, ("%s is not positively known on both sides (%r vs %r); unknown "
                           "is not evidence of sameness" % (name, va, vb))
        if va != vb:
            return False, "%s differs: %r vs %r" % (name, va, vb)
    return True, "every design field is positively known and equal"


# ----------------------------------------------------------------- design construction
def _fmt(v):
    f = PRG._f(v)
    return ("%g" % f) if f is not None else str(v)


def design_from_sweep(entity, scope_text, methods_text, note=None, material=None,
                      step=None):
    """An ExperimentalDesign for one plotted sweep, or None.

    One design per (varied quantity, scope). Its branches are the distinct plotted values.
    Returns (design, branches, role, basis).
    """
    q = entity.get("coordinate")
    raw_label = (entity.get("x_semantics") or {}).get("raw_label")
    role, basis = axis_role(q, entity.get("x_axis_role"), scope_text, methods_text,
                            raw_label=raw_label, measurand=entity.get("measurand"))
    if role != CASE_DEFINING_PROCESS_SETTING:
        return None, [], role, basis
    xs = []
    for o in entity.get("observations") or []:
        v = PRG._f(o.get("x_canonical"))
        if v is None:
            v = PRG._f(o.get("x_raw"))
        if v is not None:
            xs.append(v)
    seen, vals = set(), []
    for v in xs:
        k = round(v, 6)
        if k not in seen:
            seen.add(k)
            vals.append(v)
    if len(vals) < 2:
        return None, [], role, "%s; only %d distinct value plotted" % (basis, len(vals))
    vals.sort()
    unit = entity.get("coordinate_unit")
    sig = design_signature(q, raw_label, unit, material)
    design = {
        "varied_quantity": q, "unit": unit, "n_branches": len(vals),
        "signature": list(sig), "process_step": process_step(raw_label, q),
        "raw_axis_label": raw_label, "material": material,
        "branch_values": [_fmt(v) for v in vals],
        "axis_role": role, "axis_role_basis": basis,
        "source": {"printed_figure": entity.get("printed_figure_number"),
                   "panel": entity.get("panel"),
                   "resolved_entity_id": entity.get("entity_id")},
        "evidence": ("the panel plots %s against %d distinct values of %s; the source "
                     "varies one recipe parameter while holding the others fixed"
                     % (entity.get("measurand"), len(vals), q)),
    }
    # Every branch carries its DESIGN identity. Without it the merge key degenerates to
    # (figure, quantity, value) and fuses independent designs whose numbers coincide.
    # The ALD step is structure, not a name: a timing branch carries WHICH half-cycle it
    # belongs to, whether that step was activated, and -- for a purge -- which exposure it
    # follows. Without it `purge_time = 2 s` is the same record in four different places
    # of the recipe. `quantity` is SPECIALISED by the resolved step's role -- pulse_time
    # with precursor-step evidence becomes precursor_pulse_time -- and never rewritten to
    # a different timing family: a swept pulse stays a pulse, because "pulse" vs
    # "exposure" is part of what the source asserted. The source's own word is kept as
    # `source_quantity`.
    stepf = {}
    if step and step.get("step_context"):
        stepf = {"step_context": step["step_context"],
                 "activation": step.get("activation"),
                 "plasma_type": step.get("plasma_type"),
                 "follows": step.get("follows"),
                 "preceding_species": step.get("preceding_species"),
                 "preceding_activation": step.get("preceding_activation"),
                 "step_evidence": step.get("evidence"),
                 "step_basis": step.get("resolved_with"),
                 "source_quantity": q}
        design["step_context"] = step["step_context"]
    # ... and only a step on the SAME side of the cycle may qualify it: a purge-step
    # resolution cannot specialise a pulse quantity, that disagreement stays visible
    bq = (PS.specialize_timing_quantity(q, stepf.get("step_context"))
          if stepf.get("step_context") and PS.timing_side(q) is not None
          and PS.timing_side(q) == PS.step_side(stepf["step_context"]) else q)
    branches = [dict(stepf, **{"quantity": bq, "value": v, "unit": unit,
                 "role": R.CASE_DEFINING,
                 "role_basis": basis,
                 "provenance_type": "derived_from_design_branch",
                 "scope": "branch",
                 "source": "design_branch",
                 "design_signature": list(sig),
                 "process_step": design["process_step"],
                 "design_material": material,
                 "raw_axis_label": raw_label,
                 "evidence": "branch %s of the %s design plotted in this panel"
                             % (_fmt(v), q)}) for v in vals]
    return design, branches, role, basis


# ------------------------------------------------------- composite recipe decomposition
#: "0.1-4.0-0.1-4.0" — a pulse/purge sequence written as one string. Leaving it opaque is
#: what stops a purge-time series from value-joining to its own specimens.
_RECIPE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*-\s*"
                     r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")
#: default component order for a 4-field ALD pulse-purge sequence
_RECIPE_FIELDS = ("precursor_pulse_time", "precursor_purge_time",
                  "coreactant_pulse_time", "coreactant_purge_time")


def decompose_recipe(text, reactants=None, unit="s"):
    """[{quantity, value, unit, component_index}] for a composite pulse-purge string.

    The original string is preserved by the caller as source provenance; this only adds
    the components so they can be compared and joined. Species names are taken from the
    paper's own reactant list when it supplies exactly two.
    """
    m = _RECIPE.match(str(text or ""))
    if not m:
        return []
    names = list(_RECIPE_FIELDS)
    species = [None, None, None, None]
    rl = [r for r in (reactants or []) if r]
    if len(rl) >= 2:
        species = [rl[0], rl[0], rl[1], rl[1]]
    out = []
    for i, (name, raw) in enumerate(zip(names, m.groups())):
        out.append({"quantity": name, "value": float(raw), "unit": unit,
                    "species": species[i], "component_index": i,
                    "role": R.CASE_DEFINING,
                    "role_basis": "component of the source's composite recipe string",
                    "provenance_type": "derived_from_table_recipe",
                    "scope": "sample",
                    "source": "composite_recipe",
                    "evidence": "field %d of the recipe %r" % (i + 1, text)})
    return out


# --------------------------------------------------------------- nominal case identity
def nominal_key(conditions, exclude_roles=(R.MEASUREMENT_SETTING,)):
    """The fingerprint that decides whether two things are the SAME nominal case.

    Only case-defining conditions with a known value participate. A measurement setting
    never does — which is what keeps three specimens differing only in the reflectometer
    objective from becoming three depositions.
    """
    d = {}
    for c in conditions or []:
        if c.get("role") in exclude_roles:
            continue
        if c.get("role") != R.CASE_DEFINING:
            continue
        v = c.get("value")
        if v is None and c.get("value_kind") != "range":
            continue
        key = (c.get("quantity"), c.get("species") or "")
        val = ("%s..%s" % (c.get("value_lower"), c.get("value_upper"))
               if c.get("value_kind") == "range" else _fmt(v))
        d[key] = val
    return tuple(sorted((k[0], k[1], v) for k, v in d.items()))


def normalise_branches(items, key_fn):
    """{nominal_key: [items]} — several realisations collapsing onto one nominal case.

    Items with an EMPTY key are never collapsed together: an unknown condition set is not
    evidence that two things are the same, so each keeps its own group.
    """
    groups, anon = defaultdict(list), []
    for it in items:
        k = key_fn(it)
        if k:
            groups[k].append(it)
        else:
            anon.append(it)
    out = dict(groups)
    for i, it in enumerate(anon):
        out[("__unkeyed__", i)] = [it]
    return out


#: Statements that assert ONE PHYSICAL GROWTH was followed. Each asserts continuity of the
#: growth itself. Deliberately excluded, because each is equally true of independently
#: prepared specimens: "after N cycles" (a specimen set can be made at N different cycle
#: counts), "in situ" (a measurement MODE), and unqualified "during growth" language that
#: is not tied to the results in hand.
_CONTINUOUS_GROWTH = re.compile(
    r"\bcontinuous(?:ly)?\s+(?:monitor\w*|measur\w*|record\w*)|"
    r"\brepeated(?:ly)?\s+(?:measur\w*|scan\w*)\s+(?:of\s+)?the\s+same\b|"
    r"\bthe\s+same\s+(?:film|sample|specimen|substrate|wafer)\b[^.]{0,70}"
    r"\b(?:was|were)\b[^.]{0,30}?\b(?:re-?)?(?:measured|analy[sz]ed|scanned|imaged)\b|"
    r"\bwithout\s+(?:breaking\s+(?:the\s+)?vacuum|removing\s+the\s+(?:sample|substrate))\b|"
    r"\balong\s+(?:one|a\s+single)\s+deposition\b|"
    r"\bduring\s+(?:one|a\s+single)\s+(?:run|deposition|growth)\b|"
    r"\b(?:in|within)\s+the\s+same\s+(?:deposition\s+)?run\b", re.I)


def progression_continuity(local_text):
    """(verdict, why) for whether curves differing in a progression quantity are ONE growth.

    `local_text` must be attributable to THESE results -- the panel clause and the figure's
    own caption. A continuity phrase elsewhere in the paper, or in generic Methods prose,
    describes some other part of the work and cannot authorise a merge here.

    The default is the opposite of the default for an x axis, and deliberately so. Points
    along an axis are prima facie one series. Separate CURVES are prima facie separate
    objects: the author drew them apart. Merging them therefore needs a positive statement
    that one growth produced them, never merely the absence of a contradiction.

    Returns CONTINUOUS / SEPARATE / UNRESOLVED.
    """
    t = local_text or ""
    m = _SEPARATE_SPECIMENS.search(t)
    if m:
        return "SEPARATE", ("this scope states separately prepared specimens (%r)"
                            % re.sub(r"\s+", " ", m.group(0))[:70])
    m = _CONTINUOUS_GROWTH.search(t)
    if m:
        return "CONTINUOUS", ("this scope states that one growth was followed (%r)"
                              % re.sub(r"\s+", " ", m.group(0))[:70])
    if _IN_SITU_ONLY.search(t):
        return "UNRESOLVED", ("this scope says only that the measurement was in situ, "
                              "which is a measurement MODE and says nothing about how "
                              "many depositions were performed")
    return "UNRESOLVED", ("no statement in this figure's own scope says these curves "
                          "follow one growth; a shared panel, a shared progression "
                          "variable and compatible conditions are not continuity evidence")
