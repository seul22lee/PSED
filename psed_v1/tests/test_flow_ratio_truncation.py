#!/usr/bin/env python3
"""A truncated prefix may not change what the axis measures.

The label ladder walks prefixes, dropping trailing words until one matches. "H2 flow
ratio" lost its chemical prefix to the existing element stripper, then truncated "flow
ratio" to "flow" and resolved flow_rate -- asserting that a dimensionless ratio of two gas
flows is a flow rate.

The existing meaningful-discarded-text guard could not catch it: that guard only runs when
the winning candidate is a bare one- or two-character symbol, and "flow" is four.

The rule added here is narrower than "discarded text is meaningful", which was tried and
rejected: applied to every truncation it destroyed 31 correct readings -- an intensity
above background is still an intensity, a coverage degree is still a coverage, a thickness
of Al2O3 is still a thickness. Only words that TRANSFORM the measurand are fatal.

Run:  python3 tests/test_flow_ratio_truncation.py
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


def R(label, unit=None):
    """Through the REAL resolver, so the chemical-prefix stripper is exercised too."""
    return caxis.resolve_axis(
        raw_label=label, raw_quantity=None, unit=unit, caption="", context="",
        other_axis_label=None,
        canon=lambda l: lib.resolve_axis_label(l) or lib.canon_quantity(l)
    ).get("canonical_quantity")


def main():
    print("=== A. the falsehood is gone ===")
    ok("A: 'flow ratio' is not a flow rate", R("flow ratio") is None, R("flow ratio"))
    # through resolve_axis, so the element stripper removes H2 first -- this is the
    # production path, not the label ladder alone
    ok("A: 'H2 flow ratio' is not a flow rate", R("H2 flow ratio") is None,
       R("H2 flow ratio"))
    ok("A: and it is not rescued into some other quantity",
       R("H2 flow ratio") is None and R("H_2 flow ratio") is None)

    print("=== B. refusal is caused by the transforming word, not by the chemical ===")
    # same label minus 'ratio' still resolves; same label minus 'H2' still refuses
    ok("B: dropping 'ratio' restores the reading", R("H2 flow (sccm)", "sccm") == "flow_rate")
    ok("B: dropping 'H2' does not restore it", R("flow ratio") is None)
    ok("B: 'ratio' is the transforming token", "ratio" in lib._TRANSFORMS_MEASURAND)
    ok("B: 'ratio' is not vocabulary of flow_rate",
       "ratio" not in lib._quantity_words("flow_rate"))

    print("=== C. true flow-rate labels are untouched ===")
    for lab, unit in (("Flow rate (sccm)", "sccm"), ("Gas flow (sccm)", "sccm"),
                      ("H2 flow (sccm)", "sccm"), ("Flow (sccm)", "sccm")):
        ok("C: %-20r -> flow_rate" % lab, R(lab, unit) == "flow_rate", R(lab, unit))
    ok("C: the word 'flow' is not globally suppressed",
       lib.canon_quantity("flow") == "flow_rate")

    print("=== D. qualifiers that describe rather than transform still resolve ===")
    # these are exactly the readings the broader 'any meaningful text' rule destroyed
    for lab, unit, want in (("Intensity above background (a.u.)", "a.u.", "intensity"),
                            ("Coverage degree (%)", "%", "surface_coverage"),
                            ("Thickness Al2O3 (nm)", "nm", "film_thickness"),
                            ("GPC SE (Å)", "Å", "growth_per_cycle"),
                            ("Thickness by XRR, Å", "Å", "film_thickness"),
                            ("Capacitance Density [pF/cm²]", "pF/cm²", "capacitance"),
                            ("W thickness (nm)", "nm", "film_thickness")):
        ok("D: %-34r -> %s" % (lab, want), R(lab, unit) == want, R(lab, unit))

    print("=== E1. the guard carries only the word the corpus evidences ===")
    # "fraction" was in this set on plausibility alone and is actively wrong: a coverage
    # fraction IS a surface coverage, but the word is absent from that quantity's
    # vocabulary, so a blanket veto refuses a correct reading. This test fails under the
    # wider set and passes with the guard restricted to what the evidence supports.
    ok("E1: 'coverage fraction' still reads as a surface coverage",
       R("coverage fraction") == "surface_coverage", R("coverage fraction"))
    ok("E1: the guard holds exactly one word", lib._TRANSFORMS_MEASURAND == {"ratio"},
       sorted(lib._TRANSFORMS_MEASURAND))
    for w in ("fraction", "percentage", "proportion", "quotient"):
        ok("E1: %-11r is NOT a blanket veto" % w, w not in lib._TRANSFORMS_MEASURAND)

    print("=== E. a quantity that IS a ratio keeps its own word ===")
    # the exemption: a transforming word belonging to the quantity's own vocabulary
    ok("E: aspect_ratio owns 'ratio'", "ratio" in lib._quantity_words("aspect_ratio"))
    ok("E: so an aspect ratio still resolves",
       lib.canon_quantity("aspect ratio") == "aspect_ratio")

    print("=== F. no ontology quantity was invented ===")
    for q in ("flow_ratio", "gas_flow_ratio", "H2_flow_ratio"):
        ok("F: %-18r is still absent" % q, lib.canon_quantity(q) is None)

    print("=== G. genericity ===")
    import io
    import re
    import tokenize
    src = (W / "ontology" / "vocab.py").read_text()
    code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                   for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("G: no DOI in executable code", not re.search(r"10\.\d{4}[_/]", code))
    for lit in ("H2", "flow", "sccm"):
        ok("G: no %-8r literal in executable code" % lit, lit not in code)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
