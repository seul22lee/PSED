"""
chemistry_propagation.py — material-aware chemistry resolution for experiments.
--------------------------------------------------------------------------------
Replaces the unconditional first-element selection in 06_to_kb.to_experiments:

    prec = (scout.get("precursors") or card.get("precursors") or [None])[0]

That line ignored the experiment's deposited material entirely. Measured on the
corpus: 265 of 672 experiments sit in papers where it is questionable, and 5
papers are genuinely ambiguous (multi-material AND multi-precursor). It produced
at least one demonstrable mis-attribution — 10.1116_1.4938104 lists 6 materials
and precursors ['DEZ','TMA'], so its Al2O3 experiment was assigned DEZ purely
because DEZ sorts first. That is the `DEZ + H2O -> Al2O3` grouping the earlier
chemistry audit flagged as suspicious: not bad extraction, bad propagation.

The scout schema emits `materials`, `precursors` and `coreactants` as three
INDEPENDENT parallel lists with no mapping between them, so list position carries
no information and is never used here. An optional `material_chemistry` mapping is
read when present so a future re-scout can supply explicit pairs; it is absent from
every current record and nothing is invented in its place.

Resolution is conservative by construction: where a unique mapping cannot be
established from the source, the answer is `ambiguous` or `unresolved`, and every
candidate is preserved.
"""
from dataclasses import dataclass, field, asdict

STATUSES = ("fully_resolved", "precursor_only", "co_reactant_only",
            "ambiguous", "unresolved", "conflicting")
METHODS = ("experiment_explicit", "card_material_mapping", "paper_material_mapping",
           "material_element_match", "single_material_single_species",
           "unresolved_multi_material", "conflicting_evidence", "no_candidates")

# Which metal a precursor supplies, inferred ONLY from the compound name already in
# the record. This selects among candidates the source itself lists for the film's own
# element; it never introduces a species the paper did not name, and never overwrites
# an extracted value. Shared vocabulary with chemistry_params.chemistry_consistency.
ELEMENT_HINTS = {
    "Al": ("TMA", "TRIMETHYLALUMIN", "AL(CH3)3", "ALME3", "DMAI", "TDMAAL", "TMAL"),
    "Zn": ("DEZ", "DIETHYLZINC", "ZN(C2H5)2", "DMZ"),
    "Ti": ("TICL4", "TTIP", "TDMAT", "TITANIUM"),
    "Hf": ("TDMAHF", "HAFNIUM", "HFCL4"),
    "Si": ("BDEAS", "3DMAS", "SIH", "DISILANE", "SILAN"),
    "Y": ("YTTRIUM", "Y(SBUCP)3", "CP3Y"),
    "Ba": ("BARIUM", "PY-BA"),
    "Sr": ("STRONTIUM",),
    "Zr": ("ZR(", "ZIRCON"),
    "Fe": ("FE(", "FERROCENE"),
    "Bi": ("BI", "BISMUTH"),
    "Mo": ("MO(", "MOCL"),
    "Sn": ("SNI4", "TIN(" ),
    "W":  ("WF6",),
}


@dataclass
class ChemistryResolution:
    """Structured outcome of propagating paper-level chemistry to one experiment."""
    precursor: str = None
    co_reactant: str = None
    additional_reactants: tuple = ()
    resolution_status: str = "unresolved"
    resolution_method: str = "no_candidates"
    confidence: float = 0.0
    supporting_evidence: str = None
    ambiguity_reason: str = None
    candidate_mappings: dict = field(default_factory=dict)
    source_level: str = None            # experiment | card | scout | methods
    directly_extracted: bool = False    # False => deterministically propagated
    material_scope: str = None

    def to_dict(self):
        d = asdict(self)
        d["additional_reactants"] = list(self.additional_reactants)
        return d


def _norm(x):
    return (x or "").strip() or None


def _dedupe(names, canon=None):
    """Canonicalise then de-duplicate. Without this, a paper that names one compound
    twice (e.g. 'tris(sec-butylcyclopentadienyl)yttrium' and 'Y(sBuCp)3') looks like
    two precursors and is wrongly called ambiguous."""
    out, seen = [], set()
    for n in names or []:
        n = _norm(n)
        if not n:
            continue
        c = (canon(n) if canon else None) or n
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def material_metals(material):
    """Metal element symbols present in a film formula, restricted to the ones we have
    hints for. A ternary such as BaTiO3 returns two — which is exactly why the
    single-metal rule below must not fire for it."""
    import re
    m = _norm(material)
    if not m:
        return []
    syms = set(re.findall(r"[A-Z][a-z]?", m))
    return [el for el in ELEMENT_HINTS if el in syms]


def _element_candidates(material, candidates):
    """Candidates whose name carries the film's metal. Returns (matches, rule_applied).

    Applies ONLY to single-metal films. A multi-metal film needs one precursor per
    metal, so matching on the first metal alone would pick a precursor that supplies
    just part of the film (BaTiO3 would take the Ba source and drop Ti)."""
    metals = material_metals(material)
    if len(metals) != 1:
        return [], False
    hints = ELEMENT_HINTS[metals[0]]
    return [c for c in candidates if any(h in c.upper() for h in hints)], True


def resolve_experiment_chemistry(deposited_material, experiment_reactants=None,
                                 card=None, scout=None, source_evidence=None,
                                 canon_precursor=None, canon_coreactant=None):
    """Material-aware chemistry for ONE experiment.

    Ordered policy (first that yields a unique answer wins):
      1 experiment_explicit        a species already attached to this experiment
      2 card_material_mapping      explicit {material: {...}} on the card
      3 paper_material_mapping     explicit mapping on the scout
      4 material_element_match     exactly one candidate carries the film's metal
      5 single_material_single_species  one material, one candidate
      otherwise -> ambiguous / unresolved / conflicting

    List position is never consulted."""
    card, scout = card or {}, scout or {}
    mats = _dedupe(scout.get("materials") or card.get("materials"))
    precs = _dedupe(scout.get("precursors") or card.get("precursors"), canon_precursor)
    cores = _dedupe(scout.get("coreactants") or card.get("coreactants"), canon_coreactant)
    r = ChemistryResolution(material_scope=deposited_material,
                            candidate_mappings={"precursors": list(precs),
                                                "coreactants": list(cores),
                                                "materials": list(mats)})

    # --- priority 1: the experiment already names its own species ---------------
    exp_prec = exp_core = None
    for rt in experiment_reactants or []:
        if _norm(rt.get("species")):
            if rt.get("role") == "precursor":
                exp_prec = _norm(rt.get("species"))
            elif rt.get("role") == "coreactant":
                exp_core = _norm(rt.get("species"))
    if exp_prec or exp_core:
        # A paper-level candidate set that excludes the experiment's own species is a
        # conflict, not something to silently resolve one way or the other.
        if exp_prec and precs and exp_prec not in precs:
            r.resolution_status, r.resolution_method = "conflicting", "conflicting_evidence"
            r.ambiguity_reason = (f"experiment names precursor {exp_prec!r} but the paper-level "
                                 f"candidates are {precs}")
            r.precursor, r.co_reactant = exp_prec, exp_core
            r.source_level, r.directly_extracted = "experiment", True
            return r
        r.precursor, r.co_reactant = exp_prec, exp_core
        r.resolution_method, r.source_level, r.directly_extracted = \
            "experiment_explicit", "experiment", True
        r.confidence = 0.9
        r.supporting_evidence = "species stated on the experiment record itself"
        r.resolution_status = ("fully_resolved" if (exp_prec and exp_core) else
                               "precursor_only" if exp_prec else "co_reactant_only")
        return r

    # --- priorities 2 & 3: an explicit material -> chemistry mapping -------------
    # Absent from every current record; read here so a re-scout can supply it without
    # another code change. Nothing is fabricated when it is missing.
    for src, lvl in ((card.get("material_chemistry"), "card"),
                     (scout.get("material_chemistry"), "scout")):
        if isinstance(src, dict) and deposited_material in src:
            m = src[deposited_material] or {}
            r.precursor = _norm(m.get("precursor"))
            r.co_reactant = _norm(m.get("co_reactant"))
            r.resolution_method = ("card_material_mapping" if lvl == "card"
                                   else "paper_material_mapping")
            r.source_level, r.confidence = lvl, 0.85
            r.supporting_evidence = m.get("evidence") or f"explicit {lvl} material mapping"
            r.resolution_status = ("fully_resolved" if (r.precursor and r.co_reactant) else
                                   "precursor_only" if r.precursor else
                                   "co_reactant_only" if r.co_reactant else "unresolved")
            return r

    # --- co-reactant (same conservative policy, no element rule available) -------
    if len(cores) == 1:
        r.co_reactant = cores[0]
    elif len(cores) > 1:
        r.ambiguity_reason = f"{len(cores)} co-reactants listed with no material mapping: {cores}"

    # --- priority 4: exactly one candidate carries the film's metal -------------
    if not precs:
        r.resolution_status = "co_reactant_only" if r.co_reactant else "unresolved"
        r.resolution_method = "no_candidates"
        r.ambiguity_reason = r.ambiguity_reason or "no precursor candidate in scout or card"
        r.source_level = "scout" if r.co_reactant else None
        return r
    hits, rule_applied = _element_candidates(deposited_material, precs)
    if len(hits) == 1:
        r.precursor = hits[0]
        r.resolution_method, r.confidence, r.source_level = "material_element_match", 0.7, "scout"
        r.supporting_evidence = (f"of the candidates {precs} listed by the paper, only "
                                 f"{hits[0]!r} carries the metal of {deposited_material}")
    elif len(hits) > 1:
        r.resolution_status, r.resolution_method = "ambiguous", "unresolved_multi_material"
        r.ambiguity_reason = (f"{len(hits)} candidates carry the metal of {deposited_material}: "
                              f"{hits}; the source provides no mapping to choose between them")
        return r
    elif len(precs) == 1 and len(mats) <= 1 and len(material_metals(deposited_material)) <= 1:
        # priority 5: nothing to confuse it with
        r.precursor = precs[0]
        r.resolution_method, r.confidence, r.source_level = \
            "single_material_single_species", 0.6, "scout"
        r.supporting_evidence = (f"the paper reports one material ({mats or [deposited_material]}) "
                                 f"and one precursor ({precs[0]!r})")
    else:
        r.resolution_status, r.resolution_method = "ambiguous", "unresolved_multi_material"
        r.ambiguity_reason = (
            f"{len(precs)} precursor candidate(s) {precs} and {len(mats)} material(s) {mats}; "
            f"no unique candidate carries the metal of {deposited_material} "
            f"(metals: {material_metals(deposited_material) or 'unknown'}) and the source "
            f"provides no material-to-precursor mapping — list position is not evidence")
        return r

    r.directly_extracted = False           # propagated, not stated on the experiment
    r.resolution_status = ("fully_resolved" if (r.precursor and r.co_reactant) else
                           "precursor_only" if r.precursor else
                           "co_reactant_only" if r.co_reactant else "unresolved")
    return r
