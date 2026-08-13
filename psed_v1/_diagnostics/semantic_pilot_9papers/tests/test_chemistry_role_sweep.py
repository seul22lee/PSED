#!/usr/bin/env python3
"""Reagent roles, and whose dose a saturation curve sweeps.

A saturation panel plots growth against exposure time with one curve per reagent. The
legend says WHICH reagent's dose each curve varies -- it does not say the curves used
different chemistry. Read as a chemistry choice, a curve labelled with the oxidant
asserted that the oxidant was the metal source: the inverse of what the paper states.

Two things are fixed here and both are tested generically. A discriminator naming both
sides of the cycle qualifies the swept quantity with a species instead of minting a
chemistry condition; and the bare word "reactant" no longer normalises to `precursor`,
because contrasted with "precursor" it means the counter-reactant.

Synthetic symbols throughout -- no real chemical drives any rule. The active corpus is
used only as an integration check at the end.

Run:  python3 tests/test_chemistry_role_sweep.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
import pilot_semantics as PS          # noqa: E402
import pilot_roles as R               # noqa: E402

PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]
_pass, _fail = [], []

#: synthetic reagents: a metal source and a counter-reactant, named nothing like reality
KNOWN = ["Xprec", "Yox"]


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def decl(text):
    """The canonical quantity `_DECL_QUANTITY` gives this discriminator, or None."""
    for rx, q, _ in PS._DECL_QUANTITY:
        if rx.search(text):
            return q
    return None


def bcc(disc, legend, coordinate="exposure_time", known=KNOWN):
    return PS.between_curve_conditions(
        {"entity_id": "E::x", "between_curve_condition": disc,
         "between_curve_value": legend, "coordinate": coordinate},
        [], None, known)


def main():
    print("=== A. compound discriminators are recognised generically ===")
    for d in ("precursor/reactant", "precursor/coreactant", "precursor/co-reactant",
              "precursor/oxidant", "precursor and counter-reactant",
              "Precursor / Reactant", "reactant/precursor"):
        ok("A: %-32r names both sides" % d, PS.compound_reagent_discriminator(d))
    for d in ("precursor", "coreactant", "co-reactant", "oxidant", "reactant",
              "chemistry", "temperature", "cycle number", "sample type"):
        ok("A: %-32r names one side or none" % d,
           not PS.compound_reagent_discriminator(d))

    print("=== B. bare 'reactant' never becomes precursor (§22) ===")
    ok("B: bare 'reactant' resolves to no quantity", decl("reactant") is None,
       decl("reactant"))
    ok("B: it is not silently remapped to coreactant either",
       decl("reactant") != "coreactant", decl("reactant"))
    ok("B: an unresolved discriminator asserts no condition",
       bcc("reactant", "Yox") == [], bcc("reactant", "Yox"))

    print("=== C. 'chemistry' never defaults to precursor (§23) ===")
    ok("C: bare 'chemistry' resolves to no quantity", decl("chemistry") is None,
       decl("chemistry"))
    ok("C: it asserts no condition", bcc("chemistry", "Xprec") == [])

    print("=== D. explicit precursor choice still works (§20) ===")
    ok("D: 'precursor' -> precursor", decl("precursor") == "precursor")
    got = bcc("precursor", "Xprec", coordinate="growth_temperature")
    ok("D: a real chemistry-choice panel still mints a precursor condition",
       len(got) == 1 and got[0]["quantity"] == "precursor", got)
    ok("D: its value is the normalised species", got and got[0]["value"] == "Xprec",
       got and got[0]["value"])

    print("=== E. co-reactant aliases map to the one canonical role (§21) ===")
    # NB singular forms only: `\bprecursor\b` and `\boxidant\b` have never matched their
    # plurals. That predates this repair, no active discriminator uses a plural, and
    # widening it is a separate change.
    for d in ("co-reactant", "coreactant", "counter-reactant", "counter reactant",
              "oxidant", "a different oxidant"):
        ok("E: %-22r -> coreactant" % d, decl(d) == "coreactant", decl(d))
    got = bcc("co-reactant", "Yox", coordinate="growth_temperature")
    ok("E: a genuine co-reactant comparison mints a coreactant condition",
       len(got) == 1 and got[0]["quantity"] == "coreactant", got)
    ok("E: no new canonical role was introduced",
       {q for _, q, _ in PS._DECL_QUANTITY} & {"reactant", "oxidant", "counter_reactant"}
       == set())

    print("=== F. compound + sweep -> species on the swept quantity, no chemistry "
          "condition (§19, §13) ===")
    for coord in ("exposure_time", "pulse_time", "dose", "purge_time"):
        a = bcc("precursor/reactant", "Xprec(precursor)", coordinate=coord)
        b = bcc("precursor/reactant", "Yox(reactant)", coordinate=coord)
        ok("F: %-13s yields a reagent marker, not a condition" % coord,
           len(a) == len(b) == 1 and a[0]["quantity"] is None and b[0]["quantity"] is None,
           (a, b))
        ok("F: %-13s resolves each series to its own reagent" % coord,
           a[0].get("series_reagent") == "Xprec" and b[0].get("series_reagent") == "Yox",
           (a[0].get("series_reagent"), b[0].get("series_reagent")))
    a = bcc("precursor/reactant", "Yox(reactant)")
    ok("F: the co-reactant series is NOT called a precursor",
       not any(x.get("quantity") == "precursor" for x in a), a)
    ok("F: no fake chemistry condition carries the legend annotation",
       not any("(" in str(x.get("value") or "") for x in a), a)

    print("=== G. species is normalised, annotation stripped (§12, §24) ===")
    for legend, want in (("Xprec(precursor)", "Xprec"), ("Yox(reactant)", "Yox"),
                         ("Xprec", "Xprec"), ("Yox (oxidant)", "Yox")):
        got = bcc("precursor/reactant", legend)
        ok("G: %-20r -> species %r" % (legend, want),
           got and got[0].get("series_reagent") == want,
           got and got[0].get("series_reagent"))

    print("=== H. no species -> role table, and one species may play different roles "
          "(§18) ===")
    # the SAME symbol resolves as the swept reagent in one paper's pool and not at all in
    # another's -- role comes from context, never from the chemical's identity
    ok("H: a species unknown to the paper resolves to nothing",
       bcc("precursor/reactant", "Zother(reactant)") == [],
       bcc("precursor/reactant", "Zother(reactant)"))
    ok("H: the same symbol is the swept reagent when the paper does use it",
       (bcc("precursor/reactant", "Yox(reactant)", known=["Xprec", "Yox"])[0]
        .get("series_reagent")) == "Yox")
    # the identical legend is a precursor choice or a co-reactant choice purely by
    # discriminator, with no lookup of what the species "is"
    ok("H: one legend, two roles, decided by the discriminator alone",
       bcc("precursor", "Yox", coordinate="growth_temperature")[0]["quantity"] == "precursor"
       and bcc("oxidant", "Yox", coordinate="growth_temperature")[0]["quantity"] == "coreactant")
    src = (W / "code" / "pilot_semantics.py").read_text()
    ok("H: no chemical literal drives the repair",
       not any(t in src for t in ('== "O2"', "== 'O2'", "KNOWN_OXIDANTS", '"HDMP"')))

    print("=== I. unresolved attribution is never faked (§36) ===")
    ok("I: compound + unmatched legend asserts nothing",
       bcc("precursor/reactant", "unlabelled") == [])
    ok("I: compound + non-dose sweep asserts nothing",
       bcc("precursor/reactant", "Yox(reactant)", coordinate="deposition_temperature") == [])
    ok("I: neither falls back to precursor",
       not any(x.get("quantity") == "precursor"
               for x in bcc("precursor/reactant", "unlabelled")
               + bcc("precursor/reactant", "Yox(reactant)", coordinate="cycle_number")))

    print("=== J. cardinality: N values x 2 reagents stays 2N (§25) ===")
    # the fingerprint dimension that keeps them apart is (quantity, species, step, value)
    def key(species, v):
        return ("exposure_time", str(species or ""), "", str(v))
    N = [0.0, 1.0, 2.0, 4.0, 6.0]
    two = {key(s, v) for s in ("Xprec", "Yox") for v in N}
    ok("J: %d values x 2 reagents -> %d distinct cases" % (len(N), 2 * len(N)),
       len(two) == 2 * len(N), len(two))
    none = {key(None, v) for s in ("Xprec", "Yox") for v in N}
    ok("J: without species attribution they would collapse to %d" % len(N),
       len(none) == len(N), len(none))

    print("=== K. active corpus integration (§26) ===")
    # A chemical formula legitimately contains brackets -- Pt(acac)2 is a name, not an
    # annotation. What must not survive is the legend's ROLE tag.
    import re as _re
    _ANNOT = _re.compile(r"\((?:pre)?cursor|\(\s*(?:co-?|counter[-\s]?)?reactant"
                         r"|\(\s*oxidant", _re.I)
    for pid in PAPERS:
        cs = json.loads((W / "papers" / pid / "semantic"
                         / "experimental_cases.json").read_text())
        bad = [(c["case_id"], x.get("value")) for c in cs
               for x in (c.get("case_defining_conditions") or [])
               if x.get("quantity") in ("precursor", "coreactant")
               and _ANNOT.search(str(x.get("value") or ""))]
        ok("K: %-26s no chemistry value keeps a role annotation" % pid[:26],
           not bad, bad[:3])
    # a species named as a reagent must not be asserted as the opposite side of the cycle
    inverted = []
    for pid in PAPERS:
        for c in json.loads((W / "papers" / pid / "semantic"
                             / "experimental_cases.json").read_text()):
            cd = {x["quantity"]: x.get("value")
                  for x in (c.get("case_defining_conditions") or [])}
            if cd.get("precursor") and cd.get("precursor") == cd.get("coreactant"):
                inverted.append((c["case_id"], cd.get("precursor")))
    ok("K: no case names one species as BOTH precursor and co-reactant", not inverted,
       inverted[:3])
    # `species` is an established condition dimension with several producers (layer
    # stacks, per-reactant pulse times). Only the ones this repair attributes carry
    # `species_basis`, so the assertions below are scoped to those.
    qual = [x for pid in PAPERS
            for c in json.loads((W / "papers" / pid / "semantic"
                                 / "experimental_cases.json").read_text())
            for x in (c.get("case_defining_conditions") or []) if x.get("species_basis")]
    ok("K: the corpus exercises legend-attributed sweep species", len(qual) > 0, len(qual))
    ok("K: every legend-attributed sweep cites its series evidence",
       all(x.get("species_evidence") for x in qual),
       [x for x in qual if not x.get("species_evidence")][:2])
    ok("K: legend attribution qualifies a dose quantity, never a shared one",
       all(x["quantity"] in PS._REAGENT_SCOPED_Q for x in qual),
       sorted({x["quantity"] for x in qual}))
    ok("K: it never overwrites a species another producer had already resolved",
       all(x.get("species") for x in qual))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
