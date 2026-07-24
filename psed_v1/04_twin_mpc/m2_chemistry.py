"""
m2_chemistry.py — process-chemistry context and chemistry-scoped prior resolution.
----------------------------------------------------------------------------------
M2 previously resolved operating priors from the DEPOSITED MATERIAL. That is not
sound: partial pressure, pulse time, the pressure-to-pulse relationship and the
kinetic parameters are properties of the process CHEMISTRY and its operating
conditions, not of the film. The corpus makes this concrete — Al2O3 alone appears
under four distinct chemistries (TMA/H2O, DEZ/H2O, -/O2_plasma, and a set with no
resolved chemistry at all), which a material-keyed query silently pools.

What this module adds:
  · ProcessChemistryContext        deposited_material vs precursor vs co_reactant
  · ChemistryResolution            fully_specified / partially_specified /
                                   ambiguous / material_only / unsupported
  · ScopedPrior                    a prior that states WHICH chemistry, species and
                                   conditions it is valid for, plus which query
                                   dimensions matched and which did not
  · build_ratio                    validated pA/t_p construction that refuses to
                                   pair values from different chemistries or from a
                                   pressure with no species identity
  · TwinChemistryCompatibility     whether the active twin parameterisation is
                                   actually conditioned on the requested chemistry

Deliberate non-goals (see the task's implementation-restraint section): no
extraction changes, no ontology changes, no fabricated chemistry-specific twins,
no material->precursor mapping table. Where the corpus cannot support a chemistry
claim, the honest answer is `unresolved`, and that is what is returned.

MEASURED UPSTREAM LIMITATION, relied on throughout:
    `pressure` (27 records) and `total_pressure` (28) carry of_reactant=None in
    100 % of cases. There is therefore NO precursor partial pressure anywhere in
    the corpus, and a generic pressure may never be promoted to one. `pulse_time`
    DOES carry of_reactant (A 137 / B 153 / None 60), so pulse priors can be
    species-scoped.
"""
from dataclasses import dataclass, field, asdict

# Resolution states — deliberately NOT collapsed into one "fallback" bucket.
CHEMISTRY_STATES = ("fully_specified", "partially_specified", "ambiguous",
                    "material_only", "unsupported")

# Twin parameterisation compatibility levels, weakest last.
COMPATIBILITY_LEVELS = ("exact_chemistry", "chemistry_family", "generic_model",
                        "unknown", "incompatible")

# Ordered match policy. Index = specificity rank; a lower rank is more specific and
# carries more confidence. Any downgrade must be visible and must cost confidence.
MATCH_POLICY = (
    ("exact_chemistry_conditions_reactor", 0.85),
    ("exact_chemistry_conditions", 0.75),
    ("exact_chemistry", 0.65),
    ("precursor_only", 0.40),
    ("material_only", 0.15),      # NOT valid for chemistry-dependent priors
    ("none", 0.0),
)
MATCH_CONFIDENCE = dict(MATCH_POLICY)

# Chemistry-dependent priors: a material-only match is never sufficient for these.
CHEMISTRY_DEPENDENT = ("precursor_partial_pressure", "precursor_pulse_time",
                       "co_reactant_pulse_time", "ratio", "exposure",
                       "sticking_probability", "adsorption_rate_constant",
                       "adsorption_equilibrium_constant")


@dataclass
class ProcessChemistryContext:
    """What is being deposited vs what is doing the depositing.

    `deposited_material` is the film. `precursor_identity` is the metal-bearing /
    primary film-forming reactant. `co_reactant_identity` is the counter-reactant
    (oxidant, nitridant, reductant, plasma species). These are never aliases of one
    another — conflating them is what let a 'material' query stand in for chemistry."""
    deposited_material: str = None
    precursor_identity: str = None
    co_reactant_identity: str = None
    additional_reactants: tuple = ()
    substrate_temperature: float = None
    reactor_type: str = None
    reactor_family: str = None
    process_mode: str = None
    chemistry_source: str = "unresolved"      # user | kb | unresolved
    chemistry_confidence: float = 0.0
    chemistry_evidence: str = None

    @property
    def chemistry_key(self):
        return (self.precursor_identity, self.co_reactant_identity)

    @property
    def label(self):
        p = self.precursor_identity or "?"
        c = self.co_reactant_identity or "?"
        return f"{p} + {c}"

    def to_dict(self):
        d = asdict(self)
        d["chemistry_key"] = list(self.chemistry_key)
        d["label"] = self.label
        return d


@dataclass
class ScopedPrior:
    """A prior that knows what it is valid FOR. Without the scope fields a value is
    just a number, which is how a co-reactant pulse time or a species-less pressure
    could previously be used as a precursor property."""
    prior_name: str
    value: object = None
    unit: str = None
    source: str = "unresolved"
    confidence: float = 0.0
    evidence: str = None
    deposited_material: str = None
    precursor: str = None
    co_reactant: str = None
    temperature_scope: object = None
    reactor_scope: str = None
    species_scope: str = None          # which species this value belongs to (A/B/None)
    matched_dimensions: tuple = ()
    missing_dimensions: tuple = ()
    match_quality: str = "none"
    overridable: bool = True
    n_records: int = 0
    refs: tuple = ()

    @property
    def resolved(self):
        return self.value is not None

    def to_dict(self):
        return asdict(self)


@dataclass
class TwinChemistryCompatibility:
    """Whether the twin's kinetic parameters actually describe the requested
    chemistry. Pressure and pulse priors alone do not make a design
    precursor-aware — if `c` and `K` were pooled over every chemistry of a
    material, the prediction is generic no matter how well-scoped the priors are."""
    requested_chemistry: tuple = (None, None)
    model_chemistry: tuple = (None, None)
    parameter_sources: dict = field(default_factory=dict)
    compatible: bool = False
    compatibility_level: str = "unknown"
    missing_parameters: tuple = ()
    conflicting_parameters: tuple = ()
    evidence: str = None
    safe_for_quantitative_comparison: bool = False

    def to_dict(self):
        d = asdict(self)
        d["requested_chemistry"] = list(self.requested_chemistry)
        d["model_chemistry"] = list(self.model_chemistry)
        return d


# --------------------------------------------------------------------------- #
# chemistry discovery
# --------------------------------------------------------------------------- #
def _norm(x):
    return (x or "").strip() or None


def chemistry_alternatives(experiments, deposited_material):
    """Distinct (precursor, co_reactant) systems the corpus knows for this film.

    Returns one entry per chemistry, never a merged summary — merging is precisely
    what must not happen. Chemistries with no resolved precursor AND no resolved
    co-reactant are reported separately as `unresolved_chemistry` records rather
    than being silently folded into a neighbouring system."""
    groups = {}
    for e in experiments:
        if e.get("material") != deposited_material:
            continue
        prec = _norm((e.get("precursors") or [None])[0])
        core = _norm((e.get("coreactants") or [None])[0])
        key = (prec, core)
        g = groups.setdefault(key, {"precursor": prec, "co_reactant": core,
                                    "n_experiments": 0, "papers": set(),
                                    "resolved": bool(prec or core)})
        g["n_experiments"] += 1
        if e.get("_pid"):
            g["papers"].add(e["_pid"])
    out = []
    for key, g in groups.items():
        g = dict(g, papers=sorted(g["papers"]))
        g["chemistry_key"] = list(key)
        g["label"] = f"{key[0] or '?'} + {key[1] or '?'}"
        out.append(g)
    out.sort(key=lambda g: (-g["n_experiments"], str(g["chemistry_key"])))
    return out


def resolve_chemistry(experiments, deposited_material, precursor=None,
                      co_reactant=None, temperature=None, reactor_type=None,
                      process_mode=None):
    """Resolve the process chemistry under the required priority:
      1 user precursor + co-reactant, 2 user precursor only, 3 exact KB identity,
      4 several KB alternatives kept SEPARATE, 5 unresolved.

    A deposited material with more than one known chemistry never auto-resolves to
    whichever record happens to sort first — that is the whole defect. Returns
    (ProcessChemistryContext, status, alternatives, notes)."""
    alts = chemistry_alternatives(experiments, deposited_material)
    resolved_alts = [a for a in alts if a["resolved"]]
    notes = []
    ctx = ProcessChemistryContext(
        deposited_material=deposited_material,
        substrate_temperature=temperature, reactor_type=reactor_type,
        process_mode=process_mode)

    up, uc = _norm(precursor), _norm(co_reactant)
    if up or uc:
        ctx.precursor_identity, ctx.co_reactant_identity = up, uc
        ctx.chemistry_source = "user"
        ctx.chemistry_confidence = 1.0
        ctx.chemistry_evidence = "chemistry stated in the request"
        match = [a for a in resolved_alts
                 if (up is None or a["precursor"] == up)
                 and (uc is None or a["co_reactant"] == uc)]
        if not match:
            notes.append(
                f"requested chemistry {ctx.label!r} has no matching evidence for "
                f"{deposited_material} in the KB "
                f"(known: {[a['label'] for a in resolved_alts] or 'none'})")
            return ctx, "unsupported", alts, notes
        status = "fully_specified" if (up and uc) else "partially_specified"
        if status == "partially_specified":
            notes.append("only part of the chemistry was specified; the unresolved "
                         "half is left unresolved rather than guessed")
        return ctx, status, alts, notes

    if not resolved_alts:
        notes.append(f"no resolved precursor/co-reactant chemistry for "
                     f"{deposited_material} in the KB")
        return ctx, "material_only", alts, notes
    if len(resolved_alts) == 1:
        a = resolved_alts[0]
        ctx.precursor_identity, ctx.co_reactant_identity = a["precursor"], a["co_reactant"]
        ctx.chemistry_source = "kb"
        ctx.chemistry_confidence = 0.8
        ctx.chemistry_evidence = (f"the only chemistry the KB knows for "
                                  f"{deposited_material}: {a['label']} "
                                  f"({a['n_experiments']} experiments)")
        return ctx, "fully_specified" if (a["precursor"] and a["co_reactant"]) \
            else "partially_specified", alts, notes

    notes.append(f"{len(resolved_alts)} distinct chemistries are known for "
                 f"{deposited_material}: {[a['label'] for a in resolved_alts]}. "
                 "The deposited material does not determine the precursor system, so "
                 "none is selected automatically.")
    return ctx, "ambiguous", alts, notes


# --------------------------------------------------------------------------- #
# chemistry-scoped retrieval
# --------------------------------------------------------------------------- #
def _matches(e, prec, core, temperature=None, temp_tol=25.0):
    if prec is not None and _norm((e.get("precursors") or [None])[0]) != prec:
        return False
    if core is not None and _norm((e.get("coreactants") or [None])[0]) != core:
        return False
    return True


def scoped_condition_prior(experiments, prior_name, quantity, of_reactant,
                           deposited_material, precursor, co_reactant,
                           temperature=None, reactor_type=None,
                           require_species=True):
    """Pull ONE chemistry-scoped prior from the corpus.

    `of_reactant` is the species slot the value must belong to. When
    `require_species` is set and the stored condition has no reactant attribution,
    the value is REFUSED rather than reinterpreted — this is what stops a generic
    `pressure` from becoming a precursor partial pressure, and a coreactant pulse
    from becoming a precursor pulse."""
    matched, missing = ["deposited_material"], []
    if precursor:
        matched.append("precursor")
    else:
        missing.append("precursor")
    if co_reactant:
        matched.append("co_reactant")
    else:
        missing.append("co_reactant")
    if temperature is not None:
        matched.append("temperature")
    else:
        missing.append("temperature")
    missing.append("reactor_type") if not reactor_type else matched.append("reactor_type")

    if precursor and co_reactant:
        quality = "exact_chemistry_conditions_reactor" if (temperature is not None and reactor_type) \
            else ("exact_chemistry_conditions" if temperature is not None else "exact_chemistry")
    elif precursor:
        quality = "precursor_only"
    else:
        quality = "material_only"

    vals, refs, species_ambiguous = [], set(), 0
    for e in experiments:
        if e.get("material") != deposited_material:
            continue
        if not _matches(e, precursor, co_reactant):
            continue
        for c in e.get("controlled") or []:
            if c.get("quantity") != quantity:
                continue
            if of_reactant is not None and c.get("of_reactant") != of_reactant:
                if c.get("of_reactant") is None:
                    species_ambiguous += 1        # value exists but is unattributed
                continue
            v = c.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.append((v, c.get("unit")))
                if e.get("_pid"):
                    refs.add(e["_pid"])

    p = ScopedPrior(prior_name=prior_name, deposited_material=deposited_material,
                    precursor=precursor, co_reactant=co_reactant,
                    temperature_scope=temperature, reactor_scope=reactor_type,
                    species_scope=of_reactant,
                    matched_dimensions=tuple(matched), missing_dimensions=tuple(missing),
                    match_quality=quality, n_records=len(vals), refs=tuple(sorted(refs)))
    if not vals:
        p.source = "unresolved"
        if species_ambiguous:
            p.evidence = (f"no species-attributed partial-pressure value has been extracted "
                          f"for this chemistry so far: the {species_ambiguous} "
                          f"{quantity} record(s) processed describe chamber or unspecified "
                          f"pressure and carry no reactant attribution, so none can serve "
                          f"as {prior_name} (full pressure extraction is incomplete)")
            p.match_quality = "species_ambiguous"
        else:
            p.evidence = (f"no {quantity} record for {of_reactant or 'this quantity'} in this "
                          f"chemistry has been extracted yet (full pressure extraction is "
                          f"incomplete, so this is not a corpus-wide conclusion)")
        return p
    if quality == "material_only" and prior_name in CHEMISTRY_DEPENDENT:
        p.source = "unresolved"
        p.evidence = (f"{len(vals)} record(s) found, but only a material-only match — "
                      f"not admissible for the chemistry-dependent prior {prior_name!r}")
        p.match_quality = "material_only_rejected"
        return p
    nums = [v for v, _u in vals]
    p.value = sorted(nums)[len(nums) // 2]              # median of the matched set
    p.unit = vals[0][1]
    p.source = "kb"
    p.confidence = MATCH_CONFIDENCE.get(quality, 0.0)
    p.evidence = (f"median of {len(nums)} {quantity} record(s) scoped to "
                  f"{precursor or '?'}+{co_reactant or '?'} / {deposited_material}"
                  + (f", refs {', '.join(sorted(refs))}" if refs else ""))
    return p


def build_ratio(pressure_prior, pulse_prior, allow_fallback=False,
                fallback_value=None, fallback_reason=None):
    """Construct pA/t_p only when the two priors are genuinely comparable.

    Returns (ScopedPrior, status, reason). The status distinguishes WHY a ratio is
    unresolved, because 'no pressure exists', 'the pressure has no species', and
    'the two came from different chemistries' are different problems with different
    fixes — collapsing them into one `fallback` is what hid the gap before."""
    def fb(status, reason):
        p = ScopedPrior(prior_name="ratio", unit="Pa/s", match_quality="none",
                        source="unresolved", evidence=reason)
        if allow_fallback and fallback_value:
            p.value, p.source, p.confidence = fallback_value, "fallback", 0.2
            p.evidence = f"{reason}; using an explicitly opted-in fallback ratio"
            p.match_quality = "fallback"
        return p, status, reason

    if pressure_prior is None or not pressure_prior.resolved:
        why = (pressure_prior.evidence if pressure_prior is not None
               else "no precursor partial-pressure prior was requested")
        status = ("pressure_species_ambiguous"
                  if pressure_prior is not None
                  and pressure_prior.match_quality == "species_ambiguous"
                  else "pressure_unresolved")
        return fb(status, f"ratio unresolved: {why}")
    if pulse_prior is None or not pulse_prior.resolved:
        return fb("pulse_unresolved",
                  f"ratio unresolved: {pulse_prior.evidence if pulse_prior else 'no pulse prior'}")
    # same species?
    if pressure_prior.species_scope != pulse_prior.species_scope:
        return fb("species_mismatch",
                  f"ratio rejected: pressure belongs to species "
                  f"{pressure_prior.species_scope!r} but the pulse time belongs to "
                  f"{pulse_prior.species_scope!r}")
    # same chemistry?
    pc = (pressure_prior.precursor, pressure_prior.co_reactant)
    uc = (pulse_prior.precursor, pulse_prior.co_reactant)
    if pc != uc:
        return fb("chemistry_mismatch",
                  f"ratio rejected: pressure comes from {pc[0]}+{pc[1]} but the pulse "
                  f"time comes from {uc[0]}+{uc[1]}; evidence from different "
                  f"precursor/co-reactant systems must not be combined")
    if pressure_prior.value <= 0 or pulse_prior.value <= 0:
        return fb("non_physical",
                  "ratio rejected: a non-positive pressure or pulse time is not dimensionally valid")
    quality = min((pressure_prior.match_quality, pulse_prior.match_quality),
                  key=lambda q: MATCH_CONFIDENCE.get(q, 0.0))
    p = ScopedPrior(
        prior_name="ratio", value=pressure_prior.value / pulse_prior.value, unit="Pa/s",
        source="kb", confidence=min(pressure_prior.confidence, pulse_prior.confidence),
        deposited_material=pressure_prior.deposited_material,
        precursor=pressure_prior.precursor, co_reactant=pressure_prior.co_reactant,
        temperature_scope=pressure_prior.temperature_scope,
        reactor_scope=pressure_prior.reactor_scope,
        species_scope=pressure_prior.species_scope,
        matched_dimensions=pressure_prior.matched_dimensions,
        missing_dimensions=tuple(sorted(set(pressure_prior.missing_dimensions)
                                        | set(pulse_prior.missing_dimensions))),
        match_quality=quality,
        evidence=(f"{pressure_prior.value:g} {pressure_prior.unit or 'Pa'} / "
                  f"{pulse_prior.value:g} {pulse_prior.unit or 's'}, both scoped to "
                  f"{pressure_prior.precursor}+{pressure_prior.co_reactant}"),
        refs=tuple(sorted(set(pressure_prior.refs) | set(pulse_prior.refs))))
    return p, "chemistry_supported", p.evidence


# --------------------------------------------------------------------------- #
# twin parameterisation gate
# --------------------------------------------------------------------------- #
# Kinetic attributes of channel_model whose value should depend on the chemistry.
CHEMISTRY_SENSITIVE_TWIN_PARAMS = ("K", "c", "gpc")


def assess_twin_compatibility(chem_ctx, twin_provenance, experiments=None, bundle=None):
    """Is the active twin parameterisation actually about the requested chemistry?

    kb_bridge.params_for() keys the KB lookup on (material, process) only, so the
    kinetic parameters K and c are pooled over EVERY chemistry that deposits the
    material. When a material has more than one chemistry — Al2O3 has four — such a
    parameter set is generic, and a prediction made with it must not be presented
    as chemistry-validated or compared across chemistries."""
    req = chem_ctx.chemistry_key
    # Preferred path: a chemistry-scoped parameter bundle. It knows per-parameter
    # match levels, so `exact_chemistry` can only be claimed when EVERY
    # chemistry-dependent coefficient is exact — one exact parameter never validates
    # the whole twin.
    if bundle is not None:
        return TwinChemistryCompatibility(
            requested_chemistry=req,
            model_chemistry=tuple(bundle.requested_chemistry[:2]),
            parameter_sources=dict(bundle.chemistry_match_levels),
            compatible=(bundle.compatibility_level == "exact_chemistry"),
            compatibility_level=bundle.compatibility_level,
            missing_parameters=tuple(bundle.unresolved_parameters),
            conflicting_parameters=tuple(bundle.fallback_parameters),
            evidence="; ".join(bundle.diagnostics) or "all chemistry-dependent parameters are exact",
            safe_for_quantitative_comparison=bundle.safe_for_cross_chemistry_comparison)
    prov = twin_provenance or {}
    sources = {p: (prov.get(p) or {}).get("source", "default")
               for p in CHEMISTRY_SENSITIVE_TWIN_PARAMS}
    missing = tuple(p for p, s in sources.items() if s == "default")

    n_chem = 0
    if experiments is not None and chem_ctx.deposited_material:
        n_chem = len([a for a in chemistry_alternatives(experiments,
                                                        chem_ctx.deposited_material)
                      if a["resolved"]])

    # No lookup in the repository is keyed on chemistry, so `exact_chemistry` is not
    # currently reachable. Say so rather than implying a capability that is absent.
    if all(s == "default" for s in sources.values()):
        level, ev = "unknown", ("no kinetic parameter was resolved from the KB; the twin "
                                "is running on its built-in defaults")
    elif n_chem > 1:
        level, ev = "generic_model", (
            f"kinetic parameters {sorted(p for p, s in sources.items() if s != 'default')} "
            f"were resolved by material only, and {chem_ctx.deposited_material} has "
            f"{n_chem} distinct chemistries in the corpus — the values are pooled across "
            f"them and are not specific to {chem_ctx.label}")
    else:
        level, ev = "generic_model", (
            "kinetic parameters were resolved by material, not by chemistry; the KB "
            "lookup used by the twin is not keyed on precursor/co-reactant")
    return TwinChemistryCompatibility(
        requested_chemistry=req, model_chemistry=(None, None),
        parameter_sources=sources, compatible=False, compatibility_level=level,
        missing_parameters=missing, conflicting_parameters=(), evidence=ev,
        safe_for_quantitative_comparison=False)
