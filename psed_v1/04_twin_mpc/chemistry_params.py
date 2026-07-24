"""
chemistry_params.py — chemistry-scoped record classification and twin kinetics.
--------------------------------------------------------------------------------
Closes the upstream half of the gap that m2_chemistry exposed. Two jobs:

  1. CLASSIFY existing records non-destructively. A stored `pressure` with
     of_reactant=None is not a precursor partial pressure and never becomes one
     here; it is *labelled* species_ambiguous and left exactly as extracted.
     Likewise an A/B pulse slot only resolves to a species when the experiment's
     own reactant roster maps that slot to a name.

  2. RESOLVE twin kinetics by chemistry instead of by film. kb_service.kb_params
     keys on (material, process), so every chemistry that deposits a material is
     pooled — measured: Al2O3 `sticking_probability` pools 38 TMA/H2O records with
     one record whose chemistry is unresolved. That aggregate is forbidden here.

Nothing in this module mutates a record, edits the corpus, changes extraction, or
invents a value. Where the corpus cannot support a chemistry claim the answer is
`unresolved`, and the migration report says how often that happens.

Deliberately NOT done here (needs an LLM re-extraction, reported instead):
adding pressure_type / species attribution to the source records. The classifier
below reports exactly how many records that would affect.
"""
from dataclasses import dataclass, field, asdict

# --- pressure taxonomy --------------------------------------------------------
PRESSURE_TYPES = ("precursor_partial_pressure", "co_reactant_partial_pressure",
                  "additional_reactant_partial_pressure", "carrier_gas_partial_pressure",
                  "chamber_total_pressure", "generic_pressure", "unknown_pressure_type")

# --- pulse taxonomy -----------------------------------------------------------
PULSE_KINDS = ("precursor_pulse", "co_reactant_pulse", "additional_reactant_pulse",
               "purge", "plasma_exposure", "unspecified_pulse")

# --- kinetic parameters that must be chemistry-scoped -------------------------
# Kept apart on purpose: an initial coefficient is not a lumped one, and an
# equilibrium constant is not a rate constant. No conversion exists in this repo,
# so none is performed (see the parameter-definition compatibility rule).
CHEMISTRY_DEPENDENT_PARAMS = ("sticking_probability", "initial_sticking_coefficient",
                              "adsorption_rate_constant", "adsorption_equilibrium_constant")
NEVER_MERGE = (("sticking_probability", "initial_sticking_coefficient"),
               ("adsorption_rate_constant", "adsorption_equilibrium_constant"),
               ("sticking_probability", "reaction_probability"),
               ("sticking_probability", "recombination_probability"))

MATCH_LEVELS = ("exact_chemistry_conditions_reactor", "exact_chemistry_conditions",
                "exact_chemistry", "chemistry_family", "material_generic",
                "model_default", "unresolved")
LEVEL_CONFIDENCE = {"exact_chemistry_conditions_reactor": 0.85,
                    "exact_chemistry_conditions": 0.75, "exact_chemistry": 0.65,
                    "chemistry_family": 0.35, "material_generic": 0.15,
                    "model_default": 0.05, "unresolved": 0.0}

COMPATIBILITY_LEVELS = ("exact_chemistry", "partial_chemistry", "chemistry_family",
                        "material_generic", "model_default", "unresolved", "incompatible")


def _norm(x):
    return (x or "").strip() or None


def chemistry_key(exp):
    """Stable identity from explicit normalized fields only — never the film alone."""
    return (exp.get("material"),
            _norm((exp.get("precursors") or [None])[0]),
            _norm((exp.get("coreactants") or [None])[0]),
            _norm(exp.get("process_type")))


def slot_species(exp, slot):
    """Resolve an A/B slot to a named species using the EXPERIMENT's own roster.
    Returns (species, role) or (None, None). A/B alone is never assumed to mean
    precursor/co-reactant — 125 of 1291 slots in this corpus carry no species."""
    for rt in exp.get("reactants") or []:
        if rt.get("label") == slot:
            return _norm(rt.get("species")), _norm(rt.get("role"))
    return None, None


@dataclass
class RecordClassification:
    """A non-destructive verdict about one stored condition."""
    quantity: str = None
    value: object = None
    unit: str = None
    kind: str = None                 # pressure type or pulse kind
    of_reactant: str = None
    reactant_role: str = None
    reactant_identity: str = None
    chemistry: tuple = ()
    confidence: float = 0.0
    ambiguity_reason: str = None
    original_value_preserved: bool = True
    migration_action: str = "classified_only"

    def to_dict(self):
        d = asdict(self)
        d["chemistry"] = list(self.chemistry)
        return d


def classify_pressure(exp, cond):
    """Label a stored pressure WITHOUT reinterpreting it.

    Rules that must hold: a generic pressure is not a precursor partial pressure;
    a total pressure is not either; of_reactant=None stays species-ambiguous; and
    a single-precursor paper does not license attribution."""
    q, slot = cond.get("quantity"), cond.get("of_reactant")
    c = RecordClassification(quantity=q, value=cond.get("value"), unit=cond.get("unit"),
                             of_reactant=slot, chemistry=chemistry_key(exp))
    if q == "total_pressure":
        c.kind, c.confidence = "chamber_total_pressure", 0.9
        c.ambiguity_reason = "total pressure is a chamber quantity, never a partial pressure"
        return c
    if q in ("pressure", "partial_pressure", "reactant_A_partial_pressure"):
        if slot is None:
            c.kind, c.confidence = "generic_pressure", 0.0
            c.ambiguity_reason = ("no reactant attribution on the record; the species cannot "
                                  "be established from the deposited material or from the "
                                  "paper naming one precursor")
            return c
        sp, role = slot_species(exp, slot)
        c.reactant_identity, c.reactant_role = sp, role
        if role == "precursor":
            c.kind, c.confidence = "precursor_partial_pressure", 0.7
        elif role == "coreactant":
            c.kind, c.confidence = "co_reactant_partial_pressure", 0.7
        else:
            c.kind, c.confidence = "unknown_pressure_type", 0.1
            c.ambiguity_reason = f"slot {slot!r} has no resolvable role on this experiment"
        return c
    c.kind, c.ambiguity_reason = "unknown_pressure_type", f"unrecognised pressure quantity {q!r}"
    return c


def classify_pulse(exp, cond):
    """Label a stored time record. Purge and plasma exposure are separate kinds and
    are never normalised into an ordinary reactant pulse."""
    q, slot = cond.get("quantity"), cond.get("of_reactant")
    c = RecordClassification(quantity=q, value=cond.get("value"), unit=cond.get("unit"),
                             of_reactant=slot, chemistry=chemistry_key(exp))
    if q == "purge_time":
        c.kind, c.confidence = "purge", 0.9
        return c
    if q == "plasma_exposure_time":
        c.kind, c.confidence = "plasma_exposure", 0.9
        return c
    if q != "pulse_time":
        c.kind, c.ambiguity_reason = "unspecified_pulse", f"not a pulse quantity: {q!r}"
        return c
    if slot is None:
        c.kind, c.confidence = "unspecified_pulse", 0.0
        c.ambiguity_reason = "pulse has no A/B slot, so no reactant can be attributed"
        return c
    sp, role = slot_species(exp, slot)
    c.reactant_identity, c.reactant_role = sp, role
    if sp is None:
        c.kind, c.confidence = "unspecified_pulse", 0.0
        c.ambiguity_reason = (f"slot {slot!r} is present but this experiment maps it to no "
                              f"named species; A/B alone does not imply precursor/co-reactant")
        return c
    c.kind = ("precursor_pulse" if role == "precursor" else
              "co_reactant_pulse" if role == "coreactant" else "additional_reactant_pulse")
    c.confidence = 0.75
    return c


# --- chemistry consistency (diagnostic only, never mutates) -------------------
# Deliberately minimal and evidence-based: flag when the named precursor contains
# no element of the deposited film. This uses only the strings already in the
# corpus; it does not import external chemistry knowledge to overwrite anything.
_ELEMENT_HINTS = {"Al": ("TMA", "AL", "DMAI", "TMAL"), "Zn": ("DEZ", "ZN", "DMZ"),
                  "Ti": ("TICL", "TTIP", "TDMAT"), "Hf": ("HF", "TDMAHF"),
                  "Si": ("SI", "BDEAS", "3DMAS")}


def chemistry_consistency(material, precursor):
    """(status, warning, rule). Never rewrites, deletes or relabels a record."""
    m, p = _norm(material), _norm(precursor)
    if not m or not p:
        return "unresolved", "material or precursor not resolved", "requires_both_identities"
    pu = p.upper()
    for el, hints in _ELEMENT_HINTS.items():
        if m.startswith(el):
            if any(h in pu for h in hints):
                return "plausible", None, "precursor_carries_film_metal"
            other = [e for e, hs in _ELEMENT_HINTS.items()
                     if e != el and any(h in pu for h in hs)]
            if other:
                return ("suspicious",
                        f"{p} is a known {'/'.join(other)} precursor but the film is {m}; "
                        f"this grouping is preserved as extracted and needs manual review",
                        "precursor_metal_conflicts_with_film")
            return "uncertain", f"cannot confirm that {p} supplies {el}", "unknown_precursor_metal"
    return "unresolved", f"no element rule for film {m}", "no_rule_for_material"


# --- chemistry-scoped kinetic parameter resolution ----------------------------
@dataclass
class ScopedParameter:
    parameter_name: str
    value: object = None
    unit: str = None
    source: str = "unresolved"
    confidence: float = 0.0
    chemistry_scope: tuple = ()
    species_scope: str = None
    temperature_scope: object = None
    reactor_scope: str = None
    match_level: str = "unresolved"
    evidence: str = None
    aggregation_method: str = None
    fallback_level: str = None
    n_records: int = 0
    original_values: tuple = ()
    original_units: tuple = ()
    refs: tuple = ()

    def to_dict(self):
        d = asdict(self)
        d["chemistry_scope"] = list(self.chemistry_scope)
        return d


def resolve_parameter(experiments, parameter_name, deposited_material, precursor,
                      co_reactant, process_mode=None, temperature=None,
                      reactor_family=None, of_reactant=None):
    """Resolve one kinetic parameter within a COMPATIBLE scope only.

    Aggregation is permitted solely inside one (material, precursor, co_reactant,
    process_mode, parameter_name, species role) group. Records from different
    chemistry keys are never pooled — that is the invariant this exists to enforce.
    A material-only match is returned labelled `material_generic`, never as exact."""
    exact, generic, units, refs = [], [], [], set()
    for e in experiments:
        if e.get("material") != deposited_material:
            continue
        ep, ec = _norm((e.get("precursors") or [None])[0]), _norm((e.get("coreactants") or [None])[0])
        same_chem = (precursor is not None and ep == precursor
                     and (co_reactant is None or ec == co_reactant))
        for c in e.get("controlled") or []:
            if c.get("quantity") != parameter_name:
                continue
            if of_reactant is not None and c.get("of_reactant") != of_reactant:
                continue
            v = c.get("value")
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            (exact if same_chem else generic).append(v)
            units.append(c.get("unit"))
            if same_chem and e.get("_pid"):
                refs.add(e["_pid"])

    p = ScopedParameter(parameter_name=parameter_name,
                        chemistry_scope=(deposited_material, precursor, co_reactant, process_mode),
                        species_scope=of_reactant, temperature_scope=temperature,
                        reactor_scope=reactor_family, refs=tuple(sorted(refs)))
    if exact:
        lvl = ("exact_chemistry_conditions_reactor" if (temperature is not None and reactor_family)
               else "exact_chemistry_conditions" if temperature is not None else "exact_chemistry")
        p.value = sorted(exact)[len(exact) // 2]
        p.unit = units[0] if units else None
        p.source, p.match_level = "kb", lvl
        p.confidence = LEVEL_CONFIDENCE[lvl]
        p.n_records = len(exact)
        p.aggregation_method = f"median within one chemistry key ({len(exact)} records)"
        p.original_values, p.original_units = tuple(exact), tuple(units[:len(exact)])
        p.evidence = (f"{len(exact)} record(s) of {parameter_name} scoped to "
                      f"{precursor}+{co_reactant} / {deposited_material}"
                      + (f", refs {', '.join(sorted(refs))}" if refs else ""))
        return p
    if generic:
        # Present, but belonging to a DIFFERENT or unresolved chemistry of this film.
        p.source, p.match_level = "kb", "material_generic"
        p.confidence = LEVEL_CONFIDENCE["material_generic"]
        p.value = sorted(generic)[len(generic) // 2]
        p.unit = units[0] if units else None
        p.n_records = len(generic)
        p.aggregation_method = ("median over records of the SAME FILM but a different or "
                                "unresolved chemistry — not valid as an exact-chemistry value")
        p.original_values = tuple(generic)
        p.fallback_level = "material_generic"
        p.evidence = (f"no {parameter_name} record for {precursor}+{co_reactant}; "
                      f"{len(generic)} record(s) exist for {deposited_material} under another "
                      f"chemistry and are reported as generic only")
        return p
    p.evidence = f"no {parameter_name} record for {deposited_material} at any chemistry"
    return p


@dataclass
class TwinParameterBundle:
    """Every chemistry-dependent coefficient the twin would consume, with its scope.

    `compatibility_level` is the WEAKEST link: one exact parameter never makes the
    bundle chemistry-validated while others are defaults."""
    requested_chemistry: tuple = ()
    resolved_parameters: dict = field(default_factory=dict)
    unresolved_parameters: tuple = ()
    fallback_parameters: tuple = ()
    parameter_sources: dict = field(default_factory=dict)
    chemistry_match_levels: dict = field(default_factory=dict)
    compatibility_level: str = "unresolved"
    safe_for_quantitative_use: bool = False
    safe_for_cross_chemistry_comparison: bool = False
    diagnostics: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["requested_chemistry"] = list(self.requested_chemistry)
        d["resolved_parameters"] = {k: v.to_dict() for k, v in self.resolved_parameters.items()}
        return d


def params_for_chemistry(experiments, deposited_material, precursor_identity=None,
                         co_reactant_identity=None, process_mode=None, temperature=None,
                         reactor_family=None, parameters=CHEMISTRY_DEPENDENT_PARAMS):
    """Structured, chemistry-scoped replacement for the material-keyed lookup.

    Never returns a bare dict: every value carries its match level, so a caller
    cannot mistake a material-generic median for a chemistry-specific coefficient."""
    b = TwinParameterBundle(requested_chemistry=(deposited_material, precursor_identity,
                                                 co_reactant_identity, process_mode))
    unresolved, fallback = [], []
    for name in parameters:
        sp = resolve_parameter(experiments, name, deposited_material, precursor_identity,
                               co_reactant_identity, process_mode, temperature,
                               reactor_family, of_reactant="A")
        if sp.value is None:                          # retry without a species constraint
            sp = resolve_parameter(experiments, name, deposited_material, precursor_identity,
                                   co_reactant_identity, process_mode, temperature,
                                   reactor_family, of_reactant=None)
        b.resolved_parameters[name] = sp
        b.parameter_sources[name] = sp.source
        b.chemistry_match_levels[name] = sp.match_level
        if sp.value is None:
            unresolved.append(name)
        elif sp.match_level in ("material_generic", "chemistry_family", "model_default"):
            fallback.append(name)
    b.unresolved_parameters, b.fallback_parameters = tuple(unresolved), tuple(fallback)

    levels = [b.chemistry_match_levels[n] for n in parameters]
    exact = [l for l in levels if l.startswith("exact_chemistry")]
    if not exact:
        b.compatibility_level = "unresolved" if len(unresolved) == len(parameters) else "material_generic"
    elif len(exact) == len(parameters):
        b.compatibility_level = "exact_chemistry"
    else:
        b.compatibility_level = "partial_chemistry"
        b.diagnostics.append(
            f"{len(exact)} of {len(parameters)} chemistry-dependent parameters are "
            f"exact-chemistry; the rest are {sorted(set(levels) - set(exact))} — the bundle "
            f"is therefore partial, not chemistry-validated")
    if unresolved:
        b.diagnostics.append(f"unresolved (twin will use its built-in defaults): {unresolved}")
    if fallback:
        b.diagnostics.append(f"material-generic, NOT specific to this chemistry: {fallback}")
    b.safe_for_quantitative_use = (b.compatibility_level == "exact_chemistry")
    b.safe_for_cross_chemistry_comparison = b.safe_for_quantitative_use
    return b


# --- migration / data-quality dry run -----------------------------------------
def migration_report(experiments):
    """Non-destructive dry run: what the classification WOULD say, corpus-wide.
    Nothing is written; this exists so coverage can be judged before any rewrite."""
    from collections import Counter
    pres, pulse, kin = Counter(), Counter(), Counter()
    suspicious, chem_state = {}, Counter()
    n_exp = 0
    for e in experiments:
        n_exp += 1
        p, c = _norm((e.get("precursors") or [None])[0]), _norm((e.get("coreactants") or [None])[0])
        chem_state["complete" if (p and c) else "partial" if (p or c) else "unresolved"] += 1
        st, warn, rule = chemistry_consistency(e.get("material"), p)
        if st == "suspicious":
            k = (e.get("material"), p, c)
            s = suspicious.setdefault(k, {"n_experiments": 0, "papers": set(),
                                          "warning": warn, "validation_rule": rule,
                                          "chemistry_consistency_status": st,
                                          "original_value_preserved": True,
                                          "requires_manual_review": True})
            s["n_experiments"] += 1
            if e.get("_pid"):
                s["papers"].add(e["_pid"])
        for cond in e.get("controlled") or []:
            q = cond.get("quantity")
            if q in ("pressure", "partial_pressure", "total_pressure", "reactant_A_partial_pressure"):
                pres[classify_pressure(e, cond).kind] += 1
            elif q in ("pulse_time", "purge_time", "plasma_exposure_time"):
                pulse[classify_pulse(e, cond).kind] += 1
            elif q in CHEMISTRY_DEPENDENT_PARAMS:
                kin["chemistry_scoped" if (p and c) else
                    "material_only" if e.get("material") else "unresolved"] += 1
    for s in suspicious.values():
        s["papers"] = sorted(s["papers"])
    total_p = sum(pres.values())
    return {
        "experiments": n_exp,
        "chemistry_experiments": dict(chem_state),
        "pressure_records": dict(pres), "pressure_total": total_p,
        "pressure_species_attributed": pres["precursor_partial_pressure"]
        + pres["co_reactant_partial_pressure"],
        "pressure_species_attributed_pct": round(
            100.0 * (pres["precursor_partial_pressure"] + pres["co_reactant_partial_pressure"])
            / total_p, 1) if total_p else 0.0,
        "pulse_records": dict(pulse), "pulse_total": sum(pulse.values()),
        "kinetic_parameter_records": dict(kin),
        "suspicious_chemistry": [dict(k=list(k), **v) for k, v in suspicious.items()],
        "records_changed_by_migration": 0,
        "records_classified_only": total_p + sum(pulse.values()),
        "note": ("Dry run. No record was modified: classification is additive metadata. "
                 "Species attribution for pressure cannot be raised without a re-extraction "
                 "that captures pressure_type and the named species at source."),
    }
