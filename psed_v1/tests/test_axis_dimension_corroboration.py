#!/usr/bin/env python3
"""Weak-symbol dimension corroboration, and the three contracts around it.

A one-letter symbol is the weakest evidence the ontology admits: the same letter is a
molecular flux in one field and a current density in another. So a symbol-only reading is
checked against physics -- the quantity's declared dimension against the axis unit.

The scope of that check is the whole point of this file. An earlier attempt fed the
derived dimensions into the general guard as well, and it promptly destroyed correct
readings: `Intensity (counts)` died because the ontology says `a.u.` while the axis says
`counts`, and `Thickness/cycles S/N` was displaced by `growth_per_cycle` -- the same
physical quantity under a different id. Physics was being asked to arbitrate meaning it
cannot see.

Three contracts, tested separately:

    A  strong lexical evidence is self-sufficient and needs no dimensional corroboration
    B  weak/bare symbols must be corroborated, and abstain when they cannot be
    C  dimension is a VETO on the impossible, never a chooser between two quantities
       that share one

Run:  python3 tests/test_axis_dimension_corroboration.py
"""
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from ontology import vocab as lib                              # noqa: E402
from pipeline.canonical import axis_roles as caxis             # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def R(label, record=None, unit=None):
    return caxis.resolve_axis(
        raw_label=label, raw_quantity=record, unit=unit, caption="", context="",
        other_axis_label=None,
        canon=lambda l: lib.resolve_axis_label(l) or lib.canon_quantity(l)
    ).get("canonical_quantity")


def main():
    print("=== A. strong lexical evidence needs no dimensional corroboration ===")
    # An exact canonical name or a multi-word alias states the quantity outright. The
    # ontology's declared unit may be spelled differently from the axis unit without that
    # being a contradiction -- `a.u.` and `counts` are both "a reporting scale".
    for lab, unit, want in (("Intensity (counts)", "counts", "intensity"),
                            ("intensity (counts)", "counts", "intensity"),
                            ("Thickness/cycles S/N (nm)", "nm", "thickness_per_cycle"),
                            ("Current density, A/cm²", "A/cm²", "current_density"),
                            ("Thickness (nm)", "nm", "film_thickness")):
        ok("A: %-28r -> %s" % (lab, want), R(lab, None, unit) == want, R(lab, None, unit))
    ok("A: the ontology unit and the axis unit genuinely disagree here",
       lib.quantity_unit("intensity") == "a.u." and caxis.unit_dimension("counts") == "count")
    ok("A: and the general guard is NOT consulted for that pairing",
       caxis.dimensionally_compatible("intensity", "count"))

    print("=== B. weak/bare symbols must be corroborated ===")
    # positively contradicted
    ok("B: a length symbol under an impedance unit is refused",
       R("H (kΩ)", None, "kΩ") != "feature_height", R("H (kΩ)", None, "kΩ"))
    # no corroboration available -- the quantity has no dimension the ontology can state
    ok("B: a symbol whose quantity has no derivable dimension abstains",
       R("j / µA cm⁻²", "j", "µA cm⁻²") is None, R("j / µA cm⁻²", "j", "µA cm⁻²"))
    ok("B: absence of corroboration is not a contradiction, it is an abstention",
       caxis.symbol_dimension("collision_flux") is None)
    # a symbol standing alone, with nothing to contradict it, still resolves
    for lab, unit, want in (("H", None, "feature_height"), ("H (nm)", "nm", "feature_height"),
                            ("P_chamber (Pa)", "Pa", "total_pressure"),
                            ("T_deposition (°C)", "°C", "deposition_temperature"),
                            ("L_channel (um)", "um", "feature_length"),
                            ("2Θ (°)", "°", "diffraction_angle")):
        ok("B: %-22r still resolves" % lab, R(lab, None, unit) == want, R(lab, None, unit))

    print("=== C. dimension vetoes, it never selects ===")
    # thickness_per_cycle and growth_per_cycle are the SAME physics (both nm/cycle,
    # family film_amount). Nothing dimensional may prefer one over the other; only the
    # label's own words may.
    got = R("Thickness/cycles S/N (nm)", None, "nm")
    ok("C: the label's own alias decides", got == "thickness_per_cycle", got)
    ok("C: and it is NOT displaced by the same-dimension sibling",
       got != "growth_per_cycle", got)
    ok("C: the two really do share a dimension",
       lib.quantity_unit("thickness_per_cycle") == lib.quantity_unit("growth_per_cycle"))
    ok("C: the general guard's evidence stays the explicit table",
       caxis.dimensionally_compatible("intensity", "count")
       and not caxis.dimensionally_compatible("feature_height", "pressure"))

    print("=== D. no opportunistic retyping ===")
    # 'Time (cycles)' arguably IS a cycle count, but nothing here is authorised to decide
    # that; a plausible improvement produced by the wrong mechanism is still a defect.
    ok("D: 'Time (cycles)' keeps its existing reading",
       R("Time (cycles)", "time", "cycles") == "time", R("Time (cycles)", "time", "cycles"))

    print("=== E. Stage 2 precedence is unchanged ===")
    ok("E: a supported record semantic outranks a weak label symbol",
       R("j / mA cm⁻²", "current_density", "mA cm⁻²") == "current_density")
    ok("E: an unsupported raw record promotes nothing",
       R("j / µA cm⁻²", "j", "µA cm⁻²") is None)
    ok("E: junk in the record never wins",
       R("T_deposition (°C)", "some_unknown_token", "°C") == "deposition_temperature")

    print("=== F. the weak-symbol corrections, by mechanism ===")
    for lab, rec, unit in (("Ψ (°)", "Psi", "°"), ("Δ (°)", "Delta", "°"),
                           ("C (fF/µm²)", "C", "fF/µm²"), ("C/A, µF/cm²", "C/A", "µF/cm²"),
                           ("C/C_0", "C/C_0", ""), ("q_y (nm^-1)", "q_y", "nm^-1"),
                           ("(αhν)² (cm⁻¹ eV)²", None, "(cm⁻¹ eV)²")):
        ok("F: %-22r abstains" % lab, R(lab, rec, unit) is None, R(lab, rec, unit))

    print("=== G. genericity ===")
    import io
    import re
    import tokenize
    for mod in ("pipeline/canonical/axis_roles.py", "ontology/vocab.py"):
        src = (W / mod).read_text()
        code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                       for t in tokenize.generate_tokens(io.StringIO(src).readline))
        ok("G: no DOI in %s" % mod, not re.search(r"10\.\d{4}[_/]", code))
        for lit in ("collision_flux", "sticking_probability", "Ag/AgCl", "intensity"):
            ok("G: no %-22r literal in %s" % (lit, mod.split("/")[-1]), lit not in code)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
