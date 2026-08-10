"""
canonical/axis_roles.py — what an axis MEANS, kept separate from what it implies
about experiment granularity.

Two failures motivate this module.

1. A lexical alias was allowed to beat physics. `canon_quantity` is an alias
   lookup over the ontology, so a GIWAXS axis labelled `Q (1/A)` matched the
   model symbol `q` and became `site_density`, and an impedance axis labelled
   `Z'` (ohms) matched the depth symbol `z` and became `spatial_coordinate`.
   Both are dimensionally impossible. A match is now rejected whenever the
   axis's own unit contradicts the quantity it matched.

2. One name, several roles. "temperature" on the x axis can be the deposition
   temperature of separately grown films (a process setting) or the measurement
   temperature of one film (a measurement condition); "cycle number" can be a
   progression within one in-situ run or a count of separately grown films.
   The role is therefore resolved from the unit, the raw label, the measurand on
   the other axis and the caption -- never from the quantity name alone.

Roles (the seven the review asked to be distinguished):

    process_condition       a recipe variable set before a run
    measurement_condition   a setting of the measurement, not of the process
    progression_coordinate  advances within one run/sample (time, cycles, ageing)
    spatial_coordinate      position within one sample
    measurement_coordinate  an instrument coordinate (2th, Q, binding energy, Z')
    output                  a measured result
    derived_representation  a transform of another axis (1000/T, log sigma, normalised)

The RAW label and quantity are always preserved next to the canonical reading,
and an axis this module cannot support is returned as `unsupported_preserved`
rather than being silently forced onto the nearest ontology term.
"""
from __future__ import annotations

import re

ROLES = ("process_condition", "measurement_condition", "progression_coordinate",
         "spatial_coordinate", "measurement_coordinate", "output",
         "derived_representation", "unknown")

# --------------------------------------------------------------- dimensions
#: unit token -> physical dimension. Only what the corpus actually plots.
_UNIT_DIM = [
    (r"^(s|sec|secs|second|seconds|ms|min|mins|minute|minutes|h|hr|hour|hours|d|day|days)$", "time"),
    (r"^(nm|um|µm|μm|mm|cm|m|a|å|angstrom|pm)$", "length"),
    (r"^(1/a|1/å|å-1|a-1|nm-1|1/nm|1/m|m-1)$", "reciprocal_length"),
    (r"^(°c|c|k|°k)$", "temperature"),
    (r"^(1/k|k-1|1000/k)$", "reciprocal_temperature"),
    (r"^(pa|kpa|mpa|mbar|bar|torr|mtorr|atm|hpa)$", "pressure"),
    (r"^(pa[·.*\-]?s|mbar[·.*\-]?s|torr[·.*\-]?s|l|langmuir)$", "dose"),
    (r"^(sccm|slm|ml/min)$", "flow"),
    (r"^(ohm|ohms|ω|Ω|kω|mω|ohm[·.]?cm|ω[·.]?cm)$", "resistance"),
    (r"^(s/cm|s/m|siemens/cm|ω-1cm-1)$", "conductivity"),
    (r"^(g|mg|ug|µg|ng|kg)$", "mass"),
    (r"^(ng/cm2|ug/cm2|µg/cm2|g/cm2|ng/cm²)$", "areal_mass"),
    (r"^(ev|kev|mev|j|kj/mol)$", "energy"),
    (r"^(w|kw|mw)$", "power"),
    (r"^(deg|degree|degrees|°|2θ|2theta)$", "angle"),
    (r"^(%|percent|at\.?%|at%|wt\.?%|wt%)$", "percent"),
    (r"^(cycle|cycles|count|counts|#)$", "count"),
    (r"^(nm/cycle|å/cycle|a/cycle|nm/cyc)$", "growth_per_cycle"),
    (r"^(arb\.?\s*u\.?|a\.u\.|au|arb|counts/s|cps)$", "arbitrary"),
]

#: the dimension each ontology quantity MUST have. A lexical match that lands on
#: one of these with an incompatible axis unit is rejected.
_QUANTITY_DIM = {
    "spatial_coordinate": {"length"},
    "feature_height": {"length"}, "feature_width": {"length"},
    "feature_length": {"length"}, "film_thickness": {"length"},
    "site_density": {"reciprocal_area", "count"},
    "pulse_time": {"time"}, "purge_time": {"time"}, "dose_time": {"time"},
    "exposure": {"dose"},
    "deposition_temperature": {"temperature"}, "temperature": {"temperature"},
    "hot_wire_temperature": {"temperature"},
    "working_pressure": {"pressure"}, "partial_pressure": {"pressure"},
    "base_pressure": {"pressure"}, "generic_pressure": {"pressure"},
    "flow_rate": {"flow"},
    "resistivity": {"resistance"},
    "growth_per_cycle": {"growth_per_cycle", "length"},
    "cycle_number": {"count"},
    "atomic_concentration": {"percent"},
}

# ------------------------------------------------------- explicit semantics
#: (label pattern, unit dimension or None, quantity id, role, note)
#: Ordered; the first match wins. These are the readings that a bare alias
#: lookup gets wrong, stated once, with the reason they are unambiguous.
_EXPLICIT = [
    # --- reciprocal space -------------------------------------------------
    (r"^\s*q\b|scattering vector|momentum transfer", "reciprocal_length",
     "scattering_vector_q", "measurement_coordinate",
     "reciprocal-space coordinate of a GIWAXS/GISAXS scan, not a site density"),
    (r"2\s*θ|2\s*theta|^\s*2th\b", None, "diffraction_angle",
     "measurement_coordinate", "diffraction angle of an XRD/XRR scan"),
    (r"binding energy", None, "binding_energy", "measurement_coordinate",
     "photoelectron binding energy of an XPS scan"),
    (r"raman shift|wavenumber", None, "wavenumber", "measurement_coordinate",
     "vibrational spectrum coordinate"),
    (r"wavelength", None, "wavelength", "measurement_coordinate",
     "optical spectrum coordinate"),
    # --- electrochemical impedance ---------------------------------------
    (r"^\s*-?\s*z\s*['′]\s*['′]|^\s*-?\s*z\s*''|imag.*imped|z_?im",
     None, "impedance_imaginary", "measurement_coordinate",
     "imaginary part of a complex impedance (Nyquist axis), not a position"),
    (r"^\s*-?\s*z\s*['′](?!['′])|real.*imped|z_?re", None,
     "impedance_real", "measurement_coordinate",
     "real part of a complex impedance (Nyquist axis), not a position"),
    (r"\bR_?SEI\b|interfacial resistance|charge transfer resistance",
     None, "interfacial_resistance", "output", "an electrochemical resistance"),
    # --- conductivity vs resistivity -------------------------------------
    (r"(log\s*)?\bsigma\b|(log\s*)?σ|conductivit", "conductivity",
     "ionic_conductivity", "output",
     "a conductivity; resistivity is its reciprocal and is a different quantity"),
    # --- transformed representations --------------------------------------
    (r"1000\s*/\s*t\b|1000/t|\b1/t\s*\(", None, "inverse_temperature",
     "derived_representation",
     "an Arrhenius abscissa: a transform of temperature, not a new quantity"),
    (r"^\s*log\b|^\s*ln\b|normali[sz]ed", None, None, "derived_representation",
     "a transformed representation of another quantity"),
    # --- depth profiling ---------------------------------------------------
    (r"sputter\w*\s*(time|depth)|etch\w*\s*(time|depth)|ion milling",
     None, "sputter_depth", "measurement_coordinate",
     "depth-profiling coordinate of one specimen, not a process setting"),
    # --- ageing / cycling / storage ---------------------------------------
    (r"storage\s*(time|duration)|ageing|aging|shelf", "time",
     "storage_time", "progression_coordinate",
     "elapsed time on ONE stored sample, not an ALD pulse"),
    (r"cycling\s*(number|index)|cycle\s*index|\bcycle\s*number\b.*(cell|batter|"
     r"coulombic|efficien)|(coulombic|efficien).*cycle", None,
     "cycling_number", "progression_coordinate",
     "electrochemical cycling trajectory of one cell"),
    # --- outputs commonly mis-typed ---------------------------------------
    (r"coulombic efficien", None, "coulombic_efficiency", "output", None),
    (r"atomic (concentration|percent|fraction)|at\.?\s*%", None,
     "atomic_concentration", "output",
     "a measured composition, never a process setting"),
    (r"areal mass|mass (gain|change|uptake)|^\s*mass\b|Δm|delta m", None,
     "areal_mass", "output", "a QCM mass reading"),
    (r"hysteresis", None, "hysteresis_voltage", "output", None),
    (r"applied power|plasma power|rf power|icp power", "power",
     "applied_power", "process_condition", None),
    # --- exposure: duration vs integrated dose ----------------------------
    (r"exposure\s*time|dose\s*time|pulse\s*(length|time|duration)|"
     r"\bat-?h\s*exposure", "time", "exposure_time", "process_condition",
     "a DURATION in s/min; the integrated dose (pressure x time) is a different "
     "quantity with different units"),
    (r"exposure|dose", "dose", "exposure_dose", "process_condition",
     "an integrated dose in pressure x time"),
]

_TRANSFORMED = re.compile(r"^\s*(log|ln|log10)\b|normali[sz]ed|\bscaled\b|1000\s*/", re.I)


def unit_dimension(unit):
    """Physical dimension of a unit string, or None when unrecognised."""
    if not unit:
        return None
    u = str(unit).strip().lower()
    u = re.sub(r"^\((.*)\)$", r"\1", u).strip()
    u = u.replace("·", "").replace(" ", "")
    for pat, dim in _UNIT_DIM:
        if re.match(pat, u):
            return dim
    return None


def _label_unit(label):
    """The unit a raw axis label carries in parentheses: 'Q (1/A)' -> '1/A'."""
    if not label:
        return None
    m = re.search(r"[\(\[]\s*([^)\]]{1,18})\s*[\)\]]\s*$", str(label))
    return m.group(1).strip() if m else None


def dimensionally_compatible(quantity, dim):
    """False only when we can PROVE the pairing is impossible.

    Silent when either side is unknown -- the guard exists to reject
    demonstrable contradictions, not to demand a complete unit table.
    """
    if not quantity or not dim:
        return True
    want = _QUANTITY_DIM.get(quantity)
    if not want:
        return True
    return dim in want


def resolve_axis(raw_label, raw_quantity, unit, caption="", context="",
                 other_axis_label="", canon=None):
    """Resolve one axis. Returns a dict; never raises, never invents.

    `canon` is the existing alias lookup (`lib.canon_quantity`), injected so this
    module stays importable without the ontology.
    """
    label = str(raw_label or raw_quantity or "").strip()
    unit = unit or _label_unit(label)
    dim = unit_dimension(unit)
    blob = " ".join(str(x or "") for x in (label, caption, context))

    out = {
        "raw_label": raw_label, "raw_quantity": raw_quantity, "raw_unit": unit,
        "unit_dimension": dim, "canonical_quantity": None,
        "axis_role": "unknown", "semantic_status": "unresolved",
        "evidence": None, "rejected_lexical_match": None,
    }

    # 1. explicit readings, checked against the axis's own dimension
    for pat, want_dim, qid, role, note in _EXPLICIT:
        if not re.search(pat, label, re.I):
            continue
        if want_dim and dim and dim != want_dim:
            continue
        out.update(canonical_quantity=qid, axis_role=role,
                   semantic_status="resolved" if qid else "resolved_role_only",
                   evidence=note or "explicit axis-label reading %r" % label)
        return out

    # 2. the alias lookup -- but only when physics does not contradict it.
    #    A leading chemical-element token is stripped first: "W thickness (nm)"
    #    is tungsten thickness, and matching the bare symbol W made it
    #    `feature_width`, which no dimensional check can catch (both lengths).
    q = None
    if canon:
        stripped = re.sub(
            r"^\s*(?:[A-Z][a-z]?\d*)(?:O\d*|N\d*|S\d*|C\d*)?\s+(?=[a-z])",
            "", str(label))
        if stripped != label and len(stripped) > 3:
            q = canon(stripped)
            if q:
                out["evidence"] = ("alias match on %r after removing the leading "
                                   "chemical-element token of %r" % (stripped, label))
        if not q:
            q = canon(label)
    if q is None and raw_quantity and canon:
        q = canon(raw_quantity)
    if q is None and raw_quantity and str(raw_quantity) in (
            set(_QUANTITY_DIM) | set(_PROCESS_QUANTITIES)
            | set(_MEASUREMENT_COORDS) | set(_PROGRESSION)):
        # the record already carries a canonical id; an alias table that has no
        # entry for the id itself must not throw it away
        q = str(raw_quantity)
    if q and not dimensionally_compatible(q, dim):
        out["rejected_lexical_match"] = q
        out["semantic_status"] = "unsupported_preserved"
        out["evidence"] = (
            "alias match %r rejected: the axis is in %r (%s) and %r must be %s"
            % (q, unit, dim, q, "/".join(sorted(_QUANTITY_DIM.get(q, ())))))
        q = None
        # The rejected match came from the LABEL. When the record's own quantity
        # is dimensionally consistent with the axis, it is the better reading:
        # a panel whose recovered x label is the between-curve variable
        # ("H2 flow ratio") still has a deposition_temperature abscissa in C.
        if raw_quantity and dimensionally_compatible(str(raw_quantity), dim) \
                and _QUANTITY_DIM.get(str(raw_quantity)):
            q = str(raw_quantity)
            out["semantic_status"] = "resolved_from_record_quantity"
            out["evidence"] += ("; the record's own quantity %r is consistent "
                                "with the axis unit and is used instead"
                                % raw_quantity)
    # a generic label under a specific recorded quantity keeps the specific one
    # ("Temperature (C)" on a record whose coordinate is deposition_temperature)
    if q in ("temperature", "pressure") and raw_quantity and \
            str(raw_quantity).endswith(q):
        q = raw_quantity
    if q:
        out["canonical_quantity"] = q
        out["semantic_status"] = "resolved"
        out["evidence"] = "ontology alias match on %r" % label

    # 3. a transformed axis stays flagged as such even when the base resolves
    if _TRANSFORMED.search(label or ""):
        out["axis_role"] = "derived_representation"
        out.setdefault("evidence", None)
        return out

    # 4. role, from the quantity plus context
    out["axis_role"] = axis_role_for(q, dim, label, blob, other_axis_label)
    if out["semantic_status"] == "unresolved" and out["axis_role"] != "unknown":
        out["semantic_status"] = "role_only"
    return out


#: quantities that are recipe settings when swept BETWEEN runs
_PROCESS_QUANTITIES = {
    "deposition_temperature", "growth_temperature", "substrate_temperature",
    "hot_wire_temperature", "source_temperature", "temperature",
    "pulse_time", "purge_time", "dose_time",
    "exposure_time", "exposure_dose", "exposure", "ozone_exposure_per_cycle",
    "flow_rate", "flow_ratio",
    "working_pressure", "partial_pressure", "base_pressure", "generic_pressure",
    "pressure", "applied_power", "plasma_power", "duty_cycle", "precursor_ratio",
}
_MEASUREMENT_COORDS = {
    "scattering_vector_q", "diffraction_angle", "binding_energy", "wavenumber",
    "wavelength", "impedance_real", "impedance_imaginary", "sputter_depth",
    "photon_energy", "raman_shift",
}
_PROGRESSION = {"cycle_number", "cycling_number", "storage_time", "time",
                "process_time", "deposition_time"}

#: a temperature axis measured ON a finished film is a measurement condition
_MEASUREMENT_CONTEXT = re.compile(
    r"measurement temperature|measured at|annealing|anneal\b|post[- ]deposition|"
    r"as a function of (?:the )?measurement|impedance|conductivit|arrhenius|"
    r"during cycling|of the cell|symmetric cell", re.I)


def axis_role_for(quantity, dim, label, blob, other_axis_label=""):
    """The role of an axis, from quantity + dimension + surrounding words."""
    if quantity in _MEASUREMENT_COORDS or dim in ("reciprocal_length", "angle",
                                                  "energy", "resistance"):
        return "measurement_coordinate"
    if quantity == "spatial_coordinate" or dim == "length" and re.search(
            r"depth|position|distance|along|lateral|penetrat", label or "", re.I):
        return "spatial_coordinate"
    if quantity in _PROGRESSION:
        return "progression_coordinate"
    if quantity in _PROCESS_QUANTITIES:
        # the same quantity name is a MEASUREMENT condition when the paper is
        # measuring a finished film rather than depositing a new one
        if _MEASUREMENT_CONTEXT.search(blob or ""):
            return "measurement_condition"
        return "process_condition"
    # model-space coordinates behave like spatial ones: a normalised distance
    # into a feature is a position within a single structure
    if quantity in ("dimensionless_distance", "diffusion_length"):
        return "spatial_coordinate"
    # a geometry/model PARAMETER swept by a model, or a measurement index
    if quantity in ("aspect_ratio", "feature_height", "feature_width",
                    "feature_length", "recombination_probability",
                    "site_density", "sticking_probability",
                    "knudsen_diffusion_coefficient", "reaction_probability"):
        return "process_condition"
    if re.search(r"measurement number|scan number|run number|index$",
                 label or "", re.I):
        return "progression_coordinate"
    if re.search(r"^1\s*/\s*t\b", label or "", re.I):
        return "derived_representation"
    if quantity in ("film_thickness", "voltage", "visibility"):
        return "output"
    if dim in ("percent", "growth_per_cycle", "arbitrary", "conductivity",
               "areal_mass", "mass"):
        return "output"
    if dim == "count":
        return "progression_coordinate"
    return "unknown"
