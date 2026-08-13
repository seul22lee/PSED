#!/usr/bin/env python3
"""Record fallback must not resurrect a reading the label already refused.

A0.1 taught the label ladder that "H2 flow ratio" is not a flow_rate: a dimensionless
ratio of two gas flows is not a flow. But that refusal returns a bare `None`, which at
the next trust boundary is indistinguishable from "the label had no opinion" -- so
`resolve_axis` fell through to the record semantic and published `partial_pressure`.
The label had said the axis measures a ratio; the record, inherited from a neighbouring
panel, said it measures a pressure; the record won silently.

The rule under test is a trust boundary, not a new parser. A record may stand in for a
label the alias table cannot read. It may not stand in for a label that says the axis
measures something else. It is a veto and never a selector: it can only withhold the
record's own answer, never choose a different one, and it fires only on positive lexical
evidence in the label -- so weak, symbolic and silent labels keep their record fallback.

Run:  python3 tests/test_record_fallback_veto.py
"""
import io
import re
import sys
import tokenize
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from ontology import vocab as lib                              # noqa: E402
from pipeline.canonical import axis_roles as caxis             # noqa: E402
from pipeline.resolve.to_kb import _axis_canon                 # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


CANON = lambda l: lib.resolve_axis_label(l) or lib.canon_quantity(l)   # noqa: E731


def final(label, record=None, unit=None):
    """The production path: record canonicalisation, then axis resolution."""
    return caxis.resolve_axis(
        raw_label=label, raw_quantity=_axis_canon(record) if record else None,
        unit=unit, caption="", context="", other_axis_label=None,
        canon=CANON).get("canonical_quantity")


def full(label, record=None, unit=None):
    return caxis.resolve_axis(
        raw_label=label, raw_quantity=_axis_canon(record) if record else None,
        unit=unit, caption="", context="", other_axis_label=None, canon=CANON)


def main():
    print("=== A. the live falsehood, through the whole production path ===")
    # the exact shape that shipped: label refused by A0.1, record supplied a supported id
    ok("A: a flow ratio is not a partial pressure",
       final("H2 flow ratio", "partial_pressure") is None,
       final("H2 flow ratio", "partial_pressure"))
    ok("A: nor a flow rate", final("H2 flow ratio", "flow_rate") is None,
       final("H2 flow ratio", "flow_rate"))
    # _axis_canon is an axis-only gate and passes a valid ontology id straight through --
    # the bypass therefore has to be closed downstream of it, not inside it
    ok("A: the record really does canonicalise to a supported quantity",
       _axis_canon("partial_pressure") == "partial_pressure"
       and CANON("partial_pressure") == "partial_pressure")
    ok("A: so the refusal has to come from the trust boundary, not the alias table",
       CANON("H2 flow ratio") is None)
    r = full("H2 flow ratio", "partial_pressure")
    ok("A: the refusal is recorded, not silent",
       r.get("rejected_record_quantity") == "partial_pressure", r)
    ok("A: and the axis is marked unsupported rather than resolved",
       r.get("semantic_status") != "resolved", r.get("semantic_status"))
    ok("A: the evidence names the transforming word",
       "ratio" in str(r.get("evidence") or ""), r.get("evidence"))

    print("=== B. spelling variants and the weak-record form agree ===")
    for rec in ("partial_pressure", "flow_rate", "H2 flow ratio", None):
        for lab in ("H2 flow ratio", "H_2 flow ratio"):
            ok("B: %-16r + record=%-18r -> unsupported" % (lab, rec),
               final(lab, rec) is None, final(lab, rec))

    print("=== C. the veto is a veto, never a selector ===")
    # it may only withhold the record's answer; it must not go shopping for another one
    for rec in ("partial_pressure", "flow_rate", "total_pressure", "cycle_number"):
        ok("C: refusing %-16r yields nothing, not a substitute" % rec,
           final("H2 flow ratio", rec) is None, final("H2 flow ratio", rec))

    print("=== D. legitimate record recovery is untouched (Stage-2 contract) ===")
    # a weak bare symbol plus an independently supported record: the record still wins
    for lab, rec, unit, want in (("j", "current_density", "mA cm^-2", "current_density"),
                                 ("j / mA cm^-2", "current_density", "mA cm^-2",
                                  "current_density"),
                                 ("C", "capacitance", "F", "capacitance")):
        ok("D: %-14r + record=%-16r -> %s" % (lab, rec, want),
           final(lab, rec, unit) == want, final(lab, rec, unit))
    # a label the alias table cannot read, with a record that names the same measurand
    for lab, rec, unit, want in (("SiO2 thickness (nm)", "film_thickness", "nm",
                                  "film_thickness"),
                                 ("Depth (µm)", "spatial_coordinate", "µm",
                                  "spatial_coordinate"),
                                 ("No. of Cycles", "cycle_number", None, "cycle_number"),
                                 ("Precursor Pulse (s)", "pulse_time", "s", "pulse_time")):
        ok("D: %-22r -> %s" % (lab, want), final(lab, rec, unit) == want,
           final(lab, rec, unit))
    ok("D: a strong compatible label keeps resolving",
       final("Current density", "current_density", "A/cm2") == "current_density")

    print("=== E. the exemption: the quantity's own vocabulary ===")
    # "ratio" belongs to aspect_ratio, so it is not a transform of aspect_ratio
    ok("E: 'aspect ratio' + record=aspect_ratio -> aspect_ratio",
       final("aspect ratio", "aspect_ratio") == "aspect_ratio",
       final("aspect ratio", "aspect_ratio"))
    ok("E: 'ratio' is vocabulary of aspect_ratio",
       "ratio" in lib._quantity_words("aspect_ratio"))
    ok("E: 'ratio' is not vocabulary of partial_pressure",
       "ratio" not in lib._quantity_words("partial_pressure"))

    print("=== F. transform_conflict reports the word, or nothing ===")
    ok("F: it names the offending token",
       lib.transform_conflict("H2 flow ratio", "partial_pressure") == "ratio",
       lib.transform_conflict("H2 flow ratio", "partial_pressure"))
    ok("F: exempt when the quantity owns the word",
       lib.transform_conflict("aspect ratio", "aspect_ratio") is None)
    for lab in ("Current density", "SiO2 thickness (nm)", "j", "", None):
        ok("F: %-22r makes no transform claim" % lab,
           lib.transform_conflict(lab, "film_thickness") is None,
           lib.transform_conflict(lab, "film_thickness"))
    ok("F: no quantity, no claim",
       lib.transform_conflict("H2 flow ratio", None) is None)

    print("=== G. absence of evidence is not evidence (no new refusals) ===")
    # the veto must never fire on a label that simply says little
    for lab, rec in (("", "film_thickness"), (None, "film_thickness"),
                     ("x", "spatial_coordinate"), ("t (s)", "pulse_time")):
        ok("G: %-8r + record=%-20r still resolves" % (lab, rec),
           final(lab, rec) is not None, final(lab, rec))

    print("=== H. A0.1 remains closed ===")
    for lab, unit, want in (("H2 flow ratio", None, None), ("flow ratio", None, None),
                            ("coverage fraction", None, "surface_coverage"),
                            ("aspect ratio", None, "aspect_ratio"),
                            ("Flow rate (sccm)", "sccm", "flow_rate"),
                            ("Gas flow (sccm)", "sccm", "flow_rate"),
                            ("H2 flow (sccm)", "sccm", "flow_rate"),
                            ("Flow (sccm)", "sccm", "flow_rate")):
        ok("H: %-20r -> %s" % (lab, want), final(lab, None, unit) == want,
           final(lab, None, unit))
    ok("H: no flow_ratio quantity was invented",
       lib.canon_quantity("flow_ratio") is None
       and lib.canon_quantity("flow ratio") is None)

    print("=== I. genericity ===")
    # EXECUTABLE code only: docstrings quote the motivating labels, which is
    # documentation, not dispatch.
    for mod in (W / "ontology" / "vocab.py",
                W / "pipeline" / "canonical" / "axis_roles.py"):
        src = mod.read_text()
        code = "".join(
            "" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
            for t in tokenize.generate_tokens(io.StringIO(src).readline))
        ok("I: %-14s carries no DOI in executable code" % mod.name,
           not re.search(r"10\.\d{4}[_/]", code))
        for lit in ("H2", "H_2", "flow", "ratio", "partial_pressure", "chemmater"):
            ok("I: %-14s has no literal %-18r" % (mod.name, lit), lit not in code)
    ok("I: the transform set is still the single evidence-backed word",
       lib._TRANSFORMS_MEASURAND == {"ratio"}, lib._TRANSFORMS_MEASURAND)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
