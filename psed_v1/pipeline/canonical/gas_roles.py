"""
gas_roles.py — the gases a process uses, and what it uses them FOR.

An ALD reactor runs on gases that never appear in the recipe's chemistry: a carrier that
transports the precursor, and a purge that clears the chamber between half-cycles. Papers
state them plainly ("Argon was used as carrier and purging gas"), but the structured
record kept only the reagents, so the role went with the prose.

Two things this module is careful about.

The ROLES ARE DISTINCT. One gas commonly serves both, and many processes carry with one
gas and purge with another; collapsing them into "the gas" loses the difference. A
statement binds only the roles it actually names.

A ROLE IS NOT A DURATION. Knowing that N2 is the purge gas says nothing about how long the
purge lasted, and nothing here ever produces a purge time.

The species is resolved through the canonical chemical identity layer, so a carrier named
by formula in one paper and by name in another is one gas.
"""
import re

from pipeline.canonical import chemical_identity as _CI

CARRIER = "carrier_gas"
PURGE = "purge_gas"

#: A role word, and the role it establishes.
_ROLE_WORDS = ((r"carrier", CARRIER), (r"purg\w*", PURGE))

#: A species token: a formula or a name, never an article or a bare noun. Requiring a
#: leading capital keeps "the carrier gas" and "a carrier gas" -- which name no species --
#: out, instead of binding whatever word precedes the phrase.
#: A subscript that survived conversion as a separate character ("N 2" for N2) is a
#: document artefact, not a different chemical, so a space immediately before a digit is
#: allowed inside the token and removed before the chemical is resolved.
_SPECIES = r"[A-Z](?:[A-Za-z0-9()\[\]·.]|\s(?=\d)){0,20}"

#: "<species> ... used as (the) carrier and purging gas" / "<species> carrier gas"
_STATEMENTS = (
    re.compile(r"(?P<sp>%s)\s+(?:gas\s+)?(?:was|were|is|are)\s+used\s+(?:as|for)\s+"
               r"(?:both\s+)?(?:the\s+|a\s+)?(?P<roles>[^.]{0,60}?)gas" % _SPECIES),
    re.compile(r"(?P<sp>%s)\s+(?:was|were|is|are)\s+(?:the\s+|a\s+)?"
               r"(?P<roles>[^.]{0,40}?)gas" % _SPECIES),
    re.compile(r"(?P<sp>%s)\s+(?P<roles>(?:carrier|purg\w*)(?:\s+and\s+\w+)?)\s+gas"
               % _SPECIES),
)

#: Words that are never a chemical, however capitalised a sentence start makes them.
_NOT_SPECIES = frozenset("The A An This That These Those It Its All Both Each Gas "
                         "Ultra High Pure Purity Dry Inert".split())


def roles_in_statement(fragment):
    """Which gas roles a matched fragment actually names."""
    found = []
    for pat, role in _ROLE_WORDS:
        if re.search(pat, fragment or "", re.I) and role not in found:
            found.append(role)
    return found


def gas_roles_from_text(text):
    """[{species, identity_key, roles, evidence}] for every EXPLICIT role statement.

    Only a statement naming both a species and a role produces a record. A sentence that
    mentions "the carrier gas" without saying which gas it is establishes nothing, and is
    left alone rather than attached to whatever word happens to precede it.
    """
    doc = str(text or "")
    out, seen = [], set()
    for pat in _STATEMENTS:
        for m in pat.finditer(doc):
            sp = re.sub(r"\s+", "", m.group("sp") or "")
            if not sp or sp in _NOT_SPECIES:
                continue
            # "N2 carrier gas and purging gas" states two roles for one gas; the second
            # sits just past the match, so the immediate continuation is read too
            tail = doc[m.end(): m.end() + 60]
            cont = re.match(r"\s*and\s+(?:the\s+)?([a-z]+)\s+gas", tail, re.I)
            roles = roles_in_statement(m.group("roles")
                                       + (" " + cont.group(1) if cont else ""))
            if not roles:
                continue
            ident = _CI.resolve(sp)
            key = ident.get("identity_key")
            if not key:
                continue
            label = ident.get("preferred_label") or ident.get("species_label") or sp
            for role in roles:
                if (key, role) in seen:
                    continue
                seen.add((key, role))
                out.append({"species": label, "source_label": sp,
                            "identity_key": key,
                            "canonical_id": ident.get("canonical_id"),
                            "resolved": ident.get("resolved"),
                            "role": role,
                            "evidence": m.group(0).strip()[:200]})
    return out


def unambiguous_roles(records):
    """role -> the single gas that fills it, or nothing where the source disagrees.

    A paper naming two different carrier gases has not told us which one a given
    experiment used, so the role stays unresolved rather than taking the first.
    """
    by_role = {}
    for r in records or []:
        by_role.setdefault(r["role"], []).append(r)
    out = {}
    for role, recs in by_role.items():
        keys = {r["identity_key"] for r in recs}
        if len(keys) == 1:
            out[role] = recs[0]
    return out
