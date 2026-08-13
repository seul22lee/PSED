#!/usr/bin/env python3
"""Produced-material provenance eligibility.

Eligibility answers "could one of this paper's ExperimentalCases have produced the thing
that was measured?". Whether the paper named the INSTRUMENT is irrelevant to that
question, so `technique` must never appear in the predicate. Only categories the resolver
has already classified as not-a-local-product are excluded.

Run:  python3 tests/test_provenance_eligibility.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
import pilot_semantics as PS          # noqa: E402

PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]
E = PS.provenance_eligible
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def sem(pid, n):
    return json.loads((W / "papers" / pid / "semantic" / ("%s.json" % n)).read_text())


def base(**kw):
    m = {"measurement_id": "M::x", "measures_case": [], "technique": [],
         "entity_class": "ExperimentSeries", "source": {"source_series": "A"}}
    m.update(kw)
    return m


def main():
    print("=== A. technique invariance (the central invariant) ===")
    m1, m2 = base(technique=[]), base(technique=["XRR"])
    ok("A: eligibility is identical with and without a technique", E(m1) == E(m2),
       (E(m1), E(m2)))
    ok("A: technique appears nowhere in the predicate",
       "technique" not in (PS.provenance_eligible.__code__.co_names))

    print("=== B/C. technique-empty Measurements are still evaluated ===")
    ok("B: an ordinary technique-empty Measurement is eligible", E(base()) is True)
    ok("C: a technique-empty Measurement may still become PRODUCT_OF_CASE",
       E(base(technique=[])) is True)

    print("=== D. REFERENCE is reached regardless of technique ===")
    # eligibility is what gates reference detection; the legend decides the role
    ok("D: a technique-empty reference Measurement is still evaluated",
       E(base(technique=[], source={"source_series": "uncoated"})) is True)

    print("=== E-H. explicit non-product categories stay excluded ===")
    ok("E: imported literature is excluded even with a technique",
       E(base(provenance_role="IMPORTED_LITERATURE", technique=["XRR"])) is False)
    ok("F: a species/reagent property is excluded even with a technique",
       E(base(reports_species_property=True, technique=["XRR"])) is False)
    ok("G: a duplicate representation is excluded",
       E(base(represents_same_measurement_as="M::other")) is False)
    for cls in sorted(PS._NOT_A_LOCAL_PRODUCT):
        ok("H: %-30s cannot be a local product" % cls[:30],
           E(base(entity_class=cls)) is False)
    # UnresolvedSourceEntity is in NON_EXPERIMENTAL but is NOT excluded here. That
    # constant prevents CASE MINTING from entity classification alone; an unresolved
    # entity cannot mint a case, yet it may still be LINKED to an existing case when
    # independent produced-material evidence establishes the relationship. An unresolved
    # entity KIND and an unresolved product provenance are different uncertainties.
    ok("H: an unresolved entity class stays provenance-eligible",
       E(base(entity_class="UnresolvedSourceEntity")) is True)
    ok("H: it is eligible whether or not a technique is known",
       E(base(entity_class="UnresolvedSourceEntity", technique=[]))
       == E(base(entity_class="UnresolvedSourceEntity", technique=["XRR"])) is True)

    print("=== unresolved entity class: positive and negative provenance ===")
    # Both directions are checked on the real outputs, but the papers are DISCOVERED by
    # scanning for the entity class -- no identifier, figure or wording is named here.
    pos, neg, bad_none = [], [], []
    for pid in PAPERS:
        for m in sem(pid, "measurements"):
            if m.get("entity_class") != "UnresolvedSourceEntity":
                continue
            role = m.get("provenance_role")
            if role == "PRODUCT_OF_CASE":
                pos.append((pid, m))
            elif role == "CASE_UNRESOLVED":
                neg.append((pid, m))
            elif role is None and E(m):
                bad_none.append((pid, m["measurement_id"]))
    ok("positive: an unresolved-class Measurement CAN reach PRODUCT_OF_CASE",
       len(pos) >= 1, len(pos))
    ok("positive: that link is backed by produced-material chain evidence",
       all(m.get("provenance_chain", {}).get("case_id") and m.get("measures_case")
           for _, m in pos),
       [(m["measurement_id"], m.get("measures_case")) for _, m in pos][:2])
    ok("negative: without a chain it is CASE_UNRESOLVED with no case links",
       len(neg) >= 1 and all(not m.get("measures_case") for _, m in neg), len(neg))
    ok("negative: an eligible unresolved-class Measurement is never left unevaluated",
       not bad_none, bad_none[:3])
    ok("already-linked Measurements are not re-resolved",
       E(base(measures_case=["CASE-1"])) is False)

    print("=== I. the XRR / GPC panel ===")
    # their techniques differ; their eligibility must not
    gpc, xrr = base(technique=[]), base(technique=["XRR"])
    ok("I: GPC and XRR are equally eligible", E(gpc) == E(xrr) is True)

    print("=== corpus safeguards ===")
    sp = dup = ne = imp = 0
    bad = []
    for pid in PAPERS:
        for m in sem(pid, "measurements"):
            if m.get("reports_species_property"):
                sp += 1
            if m.get("represents_same_measurement_as"):
                dup += 1
            if m.get("entity_class") in PS.NON_EXPERIMENTAL:
                ne += 1
            if m.get("provenance_role") == "IMPORTED_LITERATURE":
                imp += 1
            # an excluded Measurement must never carry a resolved product role
            if not E(m) and m.get("provenance_role") in ("PRODUCT_OF_CASE", "REFERENCE",
                                                         "CASE_UNRESOLVED"):
                if not m.get("measures_case"):
                    bad.append((pid, m["measurement_id"], m.get("provenance_role")))
    print("    [safeguards] species_property=%d duplicate=%d non_experimental=%d "
          "imported=%d" % (sp, dup, ne, imp))
    ok("corpus: no excluded Measurement acquired a product-provenance role", not bad,
       bad[:3])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
