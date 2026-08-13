#!/usr/bin/env python3
"""Axis-label resolution: a bare symbol must not outrank the words beside it.

`resolve_axis_label` walks a prefix ladder, dropping trailing words until something
matches an ontology alias. That ladder had no floor, so any label opening with a
one-letter symbol eventually matched THAT symbol's quantity regardless of what followed:
"H_2 flow ratio" became feature_height -- a dimensionless gas ratio asserted to be a
geometric height on a planar film with no features.

The rule under test: a bare-symbol match only stands when nothing meaningful was thrown
away to reach it. Genuine subscript notation still resolves, because the dropped word
belongs to that quantity's own vocabulary ("deposition" -> deposition_temperature).

These are lexical tests. The dimension guard in axis_roles is a separate, unmodified
defence and is checked here only to prove it still behaves as before.

Run:  python3 tests/test_axis_symbol_precedence.py
"""
import re
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


def R(label):
    return lib.resolve_axis_label(label)


def main():
    print("=== A. a one-letter symbol does not outrank descriptive words ===")
    # generic shape: <symbol>_<subscript> <words the symbol's quantity never uses>
    for lab in ("H_2 flow ratio", "W thickness (nm)", "Ar Sputter Time (s)",
                "At-H pulse time (s)"):
        ok("A: %-24r is not resolved by its leading symbol" % lab, R(lab) is None, R(lab))
    ok("A: the refused reading is specifically feature_height",
       R("H_2 flow ratio") != "feature_height")

    print("=== B. H2-like label, no unit: lexical rule must decide ===")
    # there is no unit to contradict, so the dimension guard cannot help here
    ok("B: unresolved rather than a false stronger claim", R("H_2 flow ratio") is None)
    ok("B: not silently downgraded to flow_rate", R("H_2 flow ratio") != "flow_rate")
    ok("B: the ontology genuinely has no flow-ratio quantity",
       lib.canon_quantity("flow ratio") is None and lib.canon_quantity("gas flow ratio") is None)

    print("=== C. spelling variants do not contradict each other ===")
    a, b = R("H_2 flow ratio"), R("H2 flow ratio")
    ok("C: both spellings agree", a == b, (a, b))
    ok("C: and neither invents a quantity", a is None and b is None, (a, b))

    print("=== D/E/F. genuine symbol-subscript notation still resolves ===")
    for lab, want in (("T_deposition (°C)", "deposition_temperature"),
                      ("P_chamber (Pa)", "total_pressure"),
                      ("L_channel (um)", "feature_length"),
                      ("t_p (s)", "pulse_time"),
                      ("D_k (cm^2/s)", "knudsen_diffusion_coefficient"),
                      ("R_SEI (ohms)", "interfacial_resistance")):
        ok("D: %-20r -> %s" % (lab, want), R(lab) == want, R(lab))
    # the dropped word is part of the quantity's OWN vocabulary -- that is what saves it
    ok("D: 'deposition' is vocabulary of deposition_temperature",
       "deposition" in lib._quantity_words("deposition_temperature"))
    ok("D: 'flow'/'ratio' are not vocabulary of feature_height",
       not ({"flow", "ratio"} & lib._quantity_words("feature_height")))

    print("=== G. an isolated legitimate one-letter symbol still works ===")
    for lab in ("H", "H (nm)", "H (µm)"):
        ok("G: %-10r -> feature_height" % lab, R(lab) == "feature_height", R(lab))
    ok("G: a spelled-out label is unaffected", R("feature height H") == "feature_height")
    # unit words are droppable, so a symbol followed only by its unit survives
    ok("G: unit words never count as descriptive text",
       "nm" in lib._unit_words("H (nm)") and "degrees" in lib._unit_words("2Θ (Degrees)"))
    for lab in ("2Θ (Degrees)", "2θ (degrees)", "2θ, degree"):
        ok("G: %-16r -> diffraction_angle" % lab, R(lab) == "diffraction_angle", R(lab))

    print("=== H/I. the dimension guard is unchanged ===")
    # positive contradiction still rejects
    r = caxis.resolve_axis(raw_label="H (kΩ)", raw_quantity=None, unit="kΩ",
                           caption="", context="", other_axis_label="",
                           canon=lib.resolve_axis_label)
    ok("H: a length quantity under an incompatible unit is rejected",
       r.get("canonical_quantity") != "feature_height", r.get("canonical_quantity"))
    # The rejection must leave a trace, whichever layer caught it: the general
    # dimension guard records `rejected_lexical_match`, the weak-symbol corroboration
    # records `uncorroborated_symbol_match`. Both are a refusal with a reason attached;
    # neither is silent.
    ok("H: and the rejection is recorded, not silent",
       "feature_height" in (r.get("rejected_lexical_match"),
                            r.get("uncorroborated_symbol_match"))
       or r.get("semantic_status") == "unsupported_preserved", r)
    # absence of a unit is NOT contradiction
    r2 = caxis.resolve_axis(raw_label="H (nm)", raw_quantity=None, unit="nm",
                            caption="", context="", other_axis_label="",
                            canon=lib.resolve_axis_label)
    ok("I: a compatible unit still resolves", r2.get("canonical_quantity") == "feature_height",
       r2.get("canonical_quantity"))
    r3 = caxis.resolve_axis(raw_label="H", raw_quantity=None, unit=None,
                            caption="", context="", other_axis_label="",
                            canon=lib.resolve_axis_label)
    ok("I: a missing unit is not itself a veto",
       r3.get("canonical_quantity") == "feature_height", r3.get("canonical_quantity"))

    print("=== J. genericity ===")
    # EXECUTABLE code only: the docstring deliberately quotes the motivating labels, which
    # is documentation, not dispatch. Strings and comments are stripped before checking.
    import io
    import tokenize
    src = (W / "ontology" / "vocab.py").read_text()
    code = "".join(
        "" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
        for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("J: no DOI appears in executable resolver code",
       not re.search(r"10\.\d{4}[_/]", code))
    for lit in ("H_2", "H2", "flow", "ratio", "thickness", "Sputter"):
        ok("J: no literal %-10r in executable code" % lit, lit not in code)
    ok("J: the docstring may still explain the defect", "H_2 flow ratio" in src)
    ok("J: no new ontology quantity was introduced",
       lib.canon_quantity("flow_ratio") is None
       and lib.canon_quantity("gas_flow_ratio") is None)
    ok("J: 'H' remains a legitimate ontology symbol",
       lib.canon_quantity("H") == "feature_height")

    print("=== K. the rule is bounded: only BARE symbols are affected ===")
    # a multi-token candidate keeps winning regardless of residual text
    ok("K: a multi-word alias match is never second-guessed",
       R("deposition temperature during growth") == "deposition_temperature",
       R("deposition temperature during growth"))
    ok("K: an exact quantity id still resolves", R("film_thickness") == "film_thickness")

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
