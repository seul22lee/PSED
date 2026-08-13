#!/usr/bin/env python3
"""Species-aware condition comparison: what may be called the same control.

A condition is not identified by its quantity. The ontology qualifies `pulse_time` BY
REACTANT, because a valve opens for one named chemical, so a 2 s SnI4 pulse and a 2 s H2O
pulse are different controls that happen to share a number and a unit. Comparing them on
quantity alone answers a different question than the one asked, and answering it
confidently is worse than abstaining.

The rule for an unknown species is the identity rule this repository already runs on:
MISSING is not SAME. A condition whose reagent was never attributed is not thereby the
same control as one that was, so it is reported unresolved rather than quietly matched --
and the case-level verdict keeps what was PROVEN separate from what merely was not
contradicted.

Run:  python3 tests/test_condition_comparability.py
"""
import io
import re
import sys
import tokenize
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.query import condition_query as Q                # noqa: E402

_pass, _fail = [], []
CORPUS = W / "_diagnostics" / "semantic_pilot_9papers" / "papers"


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def C(q, sp=None, v=None, u=None, step=None):
    return {"quantity": q, "species": sp, "value": v, "unit": u, "process_step": step}


def outcome(a, b):
    return Q.compare_conditions(a, b)[0]


def main():
    print("=== A. the comparison key is not the quantity ===")
    ok("A: the key carries quantity, species and step",
       Q.condition_key(C("pulse_time", "SnI4", 2, "s", "dose"))
       == ("pulse_time", "SnI4", "dose"))
    ok("A: an empty species is absence, not a species",
       Q.species_of(C("pulse_time", "")) is None and Q.species_of(C("pulse_time")) is None)
    ok("A: two species give two different keys",
       Q.condition_key(C("pulse_time", "SnI4")) != Q.condition_key(C("pulse_time", "H2O")))

    print("=== B. negative controls: refusing false equivalence ===")
    ok("B: pulse_time@SnI4 is not pulse_time@H2O",
       outcome(C("pulse_time", "SnI4", 2, "s"), C("pulse_time", "H2O", 2, "s"))
       == Q.DIFFERENT_SPECIES)
    # the values are identical; only the reagent differs, and that is enough
    ok("B: identical value and unit do not rescue it",
       outcome(C("pulse_time", "SnI4", 2, "s"), C("pulse_time", "H2O", 2, "s"))
       != Q.EXACT_MATCH)
    ok("B: a named species is not matched to an unattributed one",
       outcome(C("pulse_time", "SnI4", 2, "s"), C("pulse_time", None, 2, "s"))
       == Q.SPECIES_UNRESOLVED)
    ok("B: two unattributed conditions are also unresolved, not equal",
       outcome(C("pulse_time", None, 2, "s"), C("pulse_time", None, 2, "s"))
       == Q.SPECIES_UNRESOLVED)
    ok("B: different quantities are different conditions",
       outcome(C("pulse_time", "H2O", 2, "s"), C("purge_time", "H2O", 2, "s"))
       == Q.DIFFERENT_QUANTITY)
    ok("B: the same quantity at different steps is a different control",
       outcome(C("purge_time", "H2O", 2, "s", "after_precursor"),
               C("purge_time", "H2O", 2, "s", "after_plasma")) == Q.DIFFERENT_STEP)
    # a unit is not a species and a film material is not a reagent -- A2's contract,
    # restated here because comparison is where a bad species would do its damage
    ok("B: 'bar' never appears as a species in the corpus",
       not [i for i in Q.condition_inventory(Q.load_cases(CORPUS)) if i["species"] == "bar"])
    ok("B: 'SiO2' never appears as a reagent species in the corpus",
       not [i for i in Q.condition_inventory(Q.load_cases(CORPUS))
            if i["species"] == "SiO2"])

    print("=== C. positive controls ===")
    ok("C: same quantity, species and value is an exact match",
       outcome(C("pulse_time", "H2O", 2, "s"), C("pulse_time", "H2O", 2, "s"))
       == Q.EXACT_MATCH)
    ok("C: same condition, different value",
       outcome(C("pulse_time", "H2O", 2, "s"), C("pulse_time", "H2O", 3, "s"))
       == Q.SAME_CONDITION_DIFFERENT_VALUE)
    o, d = Q.compare_conditions(C("pulse_time", "H2O", 500, "ms"),
                                C("pulse_time", "H2O", 0.5, "s"))
    ok("C: 500 ms and 0.5 s are the same pulse", o == Q.EXACT_MATCH, (o, d))
    ok("C: and the conversion is recorded", d.get("unit_converted") is True, d)
    ok("C: a converted value that differs is still a difference",
       outcome(C("pulse_time", "H2O", 500, "ms"), C("pulse_time", "H2O", 2, "s"))
       == Q.SAME_CONDITION_DIFFERENT_VALUE)
    ok("C: string and numeric spellings of one value agree",
       outcome(C("pulse_time", "H2O", "2", "s"), C("pulse_time", "H2O", 2.0, "s"))
       == Q.EXACT_MATCH)

    print("=== D. abstention when magnitudes cannot be compared ===")
    ok("D: incomparable units abstain rather than guess",
       outcome(C("pulse_time", "H2O", 2, "s"), C("pulse_time", "H2O", 2, "nm"))
       == Q.NOT_COMPARABLE)
    ok("D: a missing unit on one side abstains",
       outcome(C("pulse_time", "H2O", 2, "s"), C("pulse_time", "H2O", 2, None))
       == Q.NOT_COMPARABLE)
    ok("D: a non-numeric value under compatible units abstains",
       outcome(C("pulse_time", "H2O", "1-8 s (short)", "s"),
               C("pulse_time", "H2O", 2, "ms")) == Q.UNIT_CONVERTIBLE)
    ok("D: identical non-numeric literals still match",
       outcome(C("pulse_time", "H2O", "short", "s"), C("pulse_time", "H2O", "short", "s"))
       == Q.EXACT_MATCH)

    print("=== E. the corpus answers species-conditioned questions ===")
    cases = Q.load_cases(CORPUS)
    ok("E: cases load from the authoritative case artifact", len(cases) >= 182, len(cases))
    ok("E: every case carries its paper and id",
       all(c.get("paper_id") and c.get("case_id") for c in cases))
    h2o = Q.cases_with_condition(cases, "pulse_time", species="H2O")
    ok("E: pulse_time@H2O has matches", h2o, len(h2o))
    ok("E: every match really carries that species",
       all(x["species"] == "H2O" and x["quantity"] == "pulse_time" for x in h2o))
    # the precision switch: an unattributed condition is not an answer about H2O
    ok("E: unattributed conditions are excluded by default",
       all(x["species_resolved"] for x in h2o))
    wide = Q.cases_with_condition(cases, "pulse_time", species="H2O",
                                  require_species=False)
    ok("E: and only a widened query admits them", len(wide) >= len(h2o), (len(wide), len(h2o)))
    ok("E: a species absent from the corpus returns nothing",
       Q.cases_with_condition(cases, "pulse_time", species="NoSuchReagent") == [])

    print("=== F. query results carry their provenance ===")
    for x in h2o[:5]:
        ok("F: %s/%s answers paper, case, condition and evidence"
           % (x["paper_id"][:18], x["case_id"]),
           all(x.get(k) is not None for k in ("paper_id", "case_id", "quantity", "value"))
           and "nominal_fingerprint" in x, x)
    ok("F: attributed species carry their evidence tier",
       all(x.get("species_basis") or x.get("species_evidence")
           for x in Q.cases_with_condition(cases, "purge_time", species="Y(DPfAMD)3")))

    print("=== G. sweeps are found by identity, not by label ===")
    sweeps = Q.cases_varying_condition(cases)
    ok("G: sweeps are detected", sweeps, len(sweeps))
    ok("G: every sweep is species-attributed", all(s["species"] for s in sweeps))
    ok("G: every sweep has at least two values", all(s["n_values"] >= 2 for s in sweeps))
    prec = [s for s in sweeps if s["species"] == "Y(DPfAMD)3" and s["quantity"] == "pulse_time"]
    ok("G: the precursor pulse sweep is one sweep, not merged with the coreactant",
       len(prec) == 1 and prec[0]["n_values"] >= 4, prec)
    ok("G: it is not confused with pulse_time@H2O",
       all(s["species"] != "Y(DPfAMD)3"
           for s in sweeps if s["quantity"] == "pulse_time" and s["species"] == "H2O"))
    ok("G: sweep members carry provenance",
       all(m.get("case_id") and m.get("paper_id") for s in sweeps for m in s["cases"]))

    print("=== H. differ-only-in separates proven from merely-consistent ===")
    a = {"paper_id": "p", "case_id": "A", "case_defining_conditions": [
        C("pulse_time", "H2O", 2, "s"), C("deposition_temperature", None, 200, "degC")]}
    b = {"paper_id": "p", "case_id": "B", "case_defining_conditions": [
        C("pulse_time", "H2O", 3, "s"), C("deposition_temperature", None, 200, "degC")]}
    r = Q.compare_cases(a, b, focus=("pulse_time", "H2O"))
    # the temperature carries no species, so it is unresolved and the strong claim fails
    ok("H: an unresolved shared condition blocks the strong verdict",
       r["verdict"] == Q.MATCH_ON_SHARED_CONDITIONS, r)
    ok("H: the differing condition is still reported",
       ["pulse_time", "H2O", None] in r["differing"], r["differing"])
    ok("H: and the unresolved one is named, not hidden", r["unresolved"], r)
    a2 = {"paper_id": "p", "case_id": "A", "case_defining_conditions": [
        C("pulse_time", "H2O", 2, "s"), C("purge_time", "H2O", 5, "s")]}
    b2 = {"paper_id": "p", "case_id": "B", "case_defining_conditions": [
        C("pulse_time", "H2O", 3, "s"), C("purge_time", "H2O", 5, "s")]}
    ok("H: fully attributed and otherwise equal gives the strong verdict",
       Q.compare_cases(a2, b2, focus=("pulse_time", "H2O"))["verdict"]
       == Q.PROVEN_DIFFER_ONLY_IN)
    # an extra condition on one side is not nothing
    b3 = dict(b2, case_defining_conditions=b2["case_defining_conditions"]
              + [C("plasma_power", "Ar", 100, "W")])
    r3 = Q.compare_cases(a2, b3, focus=("pulse_time", "H2O"))
    ok("H: an unshared condition prevents 'differ only in'",
       r3["verdict"] == Q.MATCH_ON_SHARED_CONDITIONS and r3["only_in_b"], r3)
    ok("H: a different species in the focus is not the requested difference",
       Q.compare_cases(a2, {"paper_id": "p", "case_id": "C",
                            "case_defining_conditions": [C("pulse_time", "SnI4", 3, "s"),
                                                         C("purge_time", "H2O", 5, "s")]},
                       focus=("pulse_time", "H2O"))["verdict"]
       == Q.MATCH_ON_SHARED_CONDITIONS)

    print("=== I. real corpus differ-only-in ===")
    d = Q.cases_differing_only_in(cases, "pulse_time", species="Y(DPfAMD)3")
    ok("I: the precursor pulse sweep yields case pairs", d, len(d))
    ok("I: every pair names the requested condition as differing",
       all(any(k[0] == "pulse_time" and k[1] == "Y(DPfAMD)3" for k in
               [tuple(x) for x in r["differing"]]) for r in d))
    ok("I: every pair states a verdict from the vocabulary",
       all(r["verdict"] in (Q.MATCH_ON_SHARED_CONDITIONS, Q.PROVEN_DIFFER_ONLY_IN)
           for r in d))
    ok("I: pairs stay within one paper by default",
       all(r["a"]["paper_id"] == r["b"]["paper_id"] for r in d))

    print("=== J. the inventory describes the corpus ===")
    inv = Q.condition_inventory(cases)
    ok("J: the inventory is non-empty", inv, len(inv))
    ok("J: species-conditioned identities exist", [i for i in inv if i["species"]])
    ok("J: every entry counts cases and papers",
       all(i["n_cases"] >= 1 and i["n_papers"] >= 1 for i in inv))
    ok("J: one quantity can appear under several species",
       len({i["species"] for i in inv if i["quantity"] == "pulse_time"}) >= 2,
       sorted(str(i["species"]) for i in inv if i["quantity"] == "pulse_time"))

    print("=== K. this layer reads identity, it does not write it ===")
    src = (W / "pipeline" / "query" / "condition_query.py").read_text()
    code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                   for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("K: nothing here writes a fingerprint or a case id",
       "nominal_fingerprint\"]=" not in code.replace(" ", "")
       and "write_text" not in code and "json.dump" not in code)
    ok("K: no DOI in executable query code", not re.search(r"10\.\d{4}[_/]", code))
    for lit in ("SnI4", "H2O", "Y(DPfAMD)3", "TMA"):
        ok("K: no literal %-12r in executable code" % lit, lit not in code)
    ok("K: unit conversion is delegated, not reimplemented",
       "U.convert" in src and "pipeline.canonical" in src)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
