"""
chemical_identity.py — one canonical identity per chemical reagent.

A reagent arrives from the sources under whatever name the author used: an abbreviation
("TMA"), the written-out name ("trimethylaluminium", and the American spelling, and the
spaced form), or a condensed formula ("Al(CH3)3"). Stored as raw strings, those are four
different precursors: they split one Condition Case into several, they defeat every
chemistry-scoped comparison, and they make an experiment look like it used a reagent the
paper never mentions.

The equivalences are NOT decided here. They come from the maintained ontology, where each
individual carries its `id`, `full_name`, `formula` and `aka` list, so extending the
vocabulary extends this without touching any code. What this module adds is:

  * one stable canonical id per chemical, with its preferred label and formula;
  * an identity KEY safe to compare on, including for reagents the ontology does not know;
  * separator-insensitivity, so "trimethyl aluminium" and "trimethylaluminium" are one
    name written two ways;
  * the source's own string, preserved as provenance on every resolution.

What it deliberately does NOT do is guess. Two reagents are the same only when the
ontology says so. A formula that merely looks similar, an unrecognised abbreviation and a
structurally ambiguous name all stay distinct and are reported unresolved -- an unknown
reagent is not evidence that two experiments used the same chemistry.
"""
import re

from ontology import vocab as _V
from pipeline.canonical import process_steps as _PS

#: Roles the ontology indexes separately. A token is resolved against the role it is used
#: in first, then against the other -- a chemical does not stop being itself because a
#: paper fed it through the other half-cycle.
PRECURSOR = "precursor"
COREACTANT = "coreactant"
_ROLE_LOOKUP = {PRECURSOR: (_V.canon_precursor, _V.canon_coreactant),
                COREACTANT: (_V.canon_coreactant, _V.canon_precursor)}

#: Prefix marking an identity the ontology could not resolve. It still compares equal to
#: ITSELF, so two records of the same unknown reagent group, while two different unknowns
#: never merge.
UNRESOLVED_PREFIX = "unresolved:"


def _squash(s):
    """A name with every separator removed: 'trimethyl aluminium' -> 'trimethylaluminium'.

    Only separators are dropped. Nothing about the chemistry is normalised away, so this
    can merge two spellings of one name but never two different names.
    """
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _build_squashed_index():
    """squashed name -> canonical id, straight from the ontology's own individuals."""
    idx = {}
    for group in ("precursors", "coreactants", "materials"):
        for it in (_V.ONTO.get("individuals", {}).get(group) or []):
            names = [it.get("id"), it.get("formula"), it.get("full_name")]
            names += list(it.get("aka") or [])
            for n in names:
                key = _squash(n)
                if not key:
                    continue
                # a name that already points somewhere else is ambiguous across
                # individuals, and an ambiguous name must not resolve to either of them
                if key in idx and idx[key] != it["id"]:
                    idx[key] = None
                else:
                    idx.setdefault(key, it["id"])
    return {k: v for k, v in idx.items() if v}


_SQUASHED = _build_squashed_index()


def resolve(token, role=None):
    """The canonical identity of one reagent string, with its provenance.

    `role` is a hint, not a constraint: it decides which half of the vocabulary is
    consulted first. The returned record always carries the source's own string.
    """
    source = None if token is None else str(token)
    species, activation = _PS.split_activated_species(source)
    out = {"source_label": source, "species_label": species, "activation": activation,
           "canonical_id": None, "preferred_label": None, "formula": None, "aka": [],
           "resolved": False, "basis": None, "role_hint": role}
    if not species:
        out["basis"] = "no reagent named"
        out["identity_key"] = None
        return out

    first, second = _ROLE_LOOKUP.get(role, (_V.canon_precursor, _V.canon_coreactant))
    cid = first(species) or second(species)
    if cid:
        out["basis"] = "ontology alias table (id, formula, full name or aka)"
    else:
        cid = _SQUASHED.get(_squash(species))
        if cid:
            out["basis"] = ("ontology name with separators removed: the source wrote one "
                            "name with different spacing or punctuation")
    if not cid:
        out["basis"] = ("no ontology individual declares this reagent; it stays a "
                        "distinct unresolved identity rather than being merged by "
                        "resemblance")
        out["identity_key"] = "%s%s" % (UNRESOLVED_PREFIX, _squash(species))
        return out

    it = _individual(cid) or {}
    out.update(canonical_id=cid, resolved=True,
               preferred_label=it.get("id") or cid,
               formula=it.get("formula"),
               full_name=it.get("full_name"),
               aka=list(it.get("aka") or []),
               identity_key=cid)
    return out


def _individual(cid):
    for group in ("precursors", "coreactants", "materials"):
        for it in (_V.ONTO.get("individuals", {}).get(group) or []):
            if it.get("id") == cid:
                return it
    return None


def ontology_role(token):
    """Which half-cycle the ontology files this reagent under, or None.

    The vocabulary lists precursors and co-reactants separately, so it already knows that
    TMA is a precursor and O2 a co-reactant. Reading the role from there lets a caption
    naming "TMA exposure" resolve to a PRECURSOR exposure without any wording about
    precursors in the sentence -- and leaves an unknown reagent's role unresolved.
    """
    r = resolve(token)
    cid = r.get("canonical_id")
    if not cid:
        return None
    for group, role in (("precursors", PRECURSOR), ("coreactants", COREACTANT)):
        for it in (_V.ONTO.get("individuals", {}).get(group) or []):
            if it.get("id") == cid:
                return role
    return None


def identity_key(token, role=None):
    """What equality is decided on. Never None for a named reagent."""
    return resolve(token, role).get("identity_key")


def preferred_label(token, role=None):
    """The name to SHOW. The source's own string where the ontology knows nothing."""
    r = resolve(token, role)
    return r["preferred_label"] or r["species_label"] or r["source_label"]


def canonicalize_all(tokens, role=None):
    """Collapse a list of reagent strings onto canonical identities.

    Returns (labels, records): `labels` is the deduplicated preferred-label list to store
    and compare on, `records` keeps every source string that produced them, so a case can
    still show the terminology its own paper used.
    """
    labels, records, seen = [], [], set()
    for tok in tokens or []:
        r = resolve(tok, role)
        key = r.get("identity_key")
        if key is None:
            continue
        records.append(r)
        if key in seen:
            continue
        seen.add(key)
        labels.append(r["preferred_label"] or r["species_label"])
    return labels, records
