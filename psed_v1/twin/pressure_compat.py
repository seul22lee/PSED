"""
pressure_compat.py — compatibility adapter between typed pressure evidence and the
legacy consumers (M2 ratio prior, M3 twin pA).
--------------------------------------------------------------------------------
Typed extraction now writes canonical pressure quantities (precursor_partial_pressure,
co_reactant_partial_pressure, …). M2 still queried `generic_pressure` and M3 still
queried `partial_pressure` / `reactant_A_partial_pressure`, so a genuine typed precursor
pressure reached the KB but was never read — the consumers stayed on the safe fallback.

This is a lookup-precedence adapter, NOT a redesign: extraction, the ontology, the KB
and the solvers are untouched. It only lets the existing consumers find a typed
precursor pressure when one exists, under a strict allow-list.

Precedence (first match wins):
  precursor  : precursor_partial_pressure > reactant_A_partial_pressure > partial_pressure
  co-reactant: co_reactant_partial_pressure > reactant_B_partial_pressure > (legacy)

A pressure of any OTHER type never satisfies a species partial-pressure lookup — a
chamber/working/base/generic/model/measured pressure is not a reactant partial pressure.
"""

PRECURSOR_PRESSURE_QUANTITIES = ("precursor_partial_pressure",
                                 "reactant_A_partial_pressure",
                                 "partial_pressure")
CO_REACTANT_PRESSURE_QUANTITIES = ("co_reactant_partial_pressure",
                                   "reactant_B_partial_pressure")

# Names that must NEVER satisfy a species partial-pressure lookup, even if the value
# is present. Enumerated so the guard is explicit and testable.
FORBIDDEN_FOR_PARTIAL = ("working_pressure", "chamber_total_pressure", "base_pressure",
                         "generic_pressure", "delivery_line_pressure", "bubbler_pressure",
                         "unknown_pressure_type", "vapor_pressure")


def _slot_ok(quantity, of_reactant, slot):
    """`reactant_A_/B_` encode the slot in the name, so accept of_reactant None or the
    slot; the other typed names must carry the explicit slot."""
    if quantity.startswith(f"reactant_{slot}_"):
        return of_reactant in (None, slot)
    return of_reactant == slot


def _first(exp, quantities, slot):
    for q in quantities:                       # strict precedence order
        for c in exp.get("controlled") or []:
            if c.get("quantity") != q:
                continue
            if not _slot_ok(q, c.get("of_reactant"), slot):
                continue
            v = c.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return v, c
    return None, None


def precursor_pressure(exp):
    """(value, condition) of the precursor partial pressure by precedence, else
    (None, None). Never returns a chamber/working/base/generic/etc. pressure."""
    return _first(exp, PRECURSOR_PRESSURE_QUANTITIES, "A")


def co_reactant_pressure(exp):
    """(value, condition) of the co-reactant partial pressure by precedence, else
    (None, None). Defined for completeness; the twin's pB is the background/collision
    gas, so no current consumer feeds a co-reactant pressure into it."""
    return _first(exp, CO_REACTANT_PRESSURE_QUANTITIES, "B")
