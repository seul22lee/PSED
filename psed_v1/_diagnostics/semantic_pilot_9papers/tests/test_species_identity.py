#!/usr/bin/env python3
"""What may occupy `species`, and what that does to case identity.

`species` is the reagent dimension of the case fingerprint: WHICH chemical a setting
applies to. Two things that are not reagents had been landing in it. A unit --
`carrier_gas_partial_pressure = 1 bar` arrived carrying `species='bar'`, the pressure
unit copied into the chemical slot, in 19 of 19 instances. A film material -- a
`structural_identity` condition repeated the deposited material the case already holds
as `deposited_material`, constant across every instance and so distinguishing nothing.

Meanwhile the settings that genuinely belong to a named reagent carried nothing, so a
swept `Precursor Pulse` collided on the `(quantity, species)` de-duplication key with a
methods-default `pulse_time` and was silently discarded.

Both defects distort identity, in opposite directions, and the rule that fixes them is
one rule: the field holds a reagent, on evidence, or it holds nothing. Refusing a bad
value never invents a replacement -- MISSING is not SAME.

Run:  python3 tests/test_species_identity.py
"""
import io
import json
import re
import sys
import tokenize
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
sys.path.insert(0, str(W.parents[1]))

import pilot_semantics as PS                                       # noqa: E402
from pilot_semantics import PC                                     # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def repair(cond, prec=(), core=()):
    return PS.species_repair(dict(cond), list(prec), list(core))


def fingerprint(conditions):
    """The species-bearing part of the case fingerprint key, as pilot_semantics builds it."""
    return tuple(sorted((x["quantity"], str(x.get("species") or ""),
                         str(x.get("process_step") or ""), PC._fmt(x.get("value")))
                        for x in conditions))


def cases(pid):
    p = W / "papers" / pid / "semantic" / "experimental_cases.json"
    d = json.loads(p.read_text())
    return d.get("experimental_cases", d) if isinstance(d, dict) else d


def all_cases():
    for pid in json.loads((W / "pilot_papers.json").read_text())["papers"]:
        for c in cases(pid):
            yield pid, c


def main():
    print("=== A. a unit is never a species ===")
    r = repair({"quantity": "carrier_gas_partial_pressure", "value": "1",
                "unit": "bar", "species": "bar"})
    ok("A: species equal to the condition's own unit is refused", r["species"] is None, r)
    ok("A: the refused value is preserved for review", r.get("species_removed") == "bar", r)
    ok("A: and the reason is recorded", "unit" in str(r.get("species_evidence")), r)
    ok("A: nothing is invented in its place", r["species"] is None)
    # case-insensitive, and not fooled by spacing
    for u, s in (("Bar", "bar"), ("bar", " bar "), ("Torr", "torr")):
        ok("A: unit=%-6r species=%-7r refused" % (u, s),
           repair({"quantity": "q", "unit": u, "species": s})["species"] is None)
    # a real reagent that merely coexists with a unit survives
    ok("A: a genuine species under a unit is untouched",
       repair({"quantity": "pulse_time", "unit": "s", "species": "H2O"})["species"] == "H2O")

    print("=== B. a deposited film material is not the dosed reagent ===")
    r = repair({"quantity": "deposited_layer_thickness", "value": 5.0, "unit": "nm",
                "structural_identity": True, "species": "SiO2"})
    ok("B: species on a structural condition is refused", r["species"] is None, r)
    ok("B: the reason names the structure, not the string",
       "deposited structure" in str(r.get("species_evidence")), r)
    ok("B: the same material on a PROCESS condition is untouched",
       repair({"quantity": "pulse_time", "unit": "s", "species": "SiO2"})["species"] == "SiO2")

    print("=== C. attribution requires positive evidence in the label ===")
    # tier A: the label names a chemical the paper's own inventory lists
    r = repair({"quantity": "pulse_time", "unit": "s",
                "raw_axis_label": "SnI4 pulse length, s"}, prec=["SnI4"], core=["H2O"])
    ok("C: an explicit chemical in the label attributes it", r["species"] == "SnI4", r)
    ok("C: tier A is recorded", r["species_basis"] == "AXIS_LABEL_EXPLICIT", r)
    # tier B: a role word the inventory binds uniquely
    r = repair({"quantity": "purge_time", "unit": "s",
                "raw_axis_label": "Precursor Purge (s)"},
               prec=["Y(DPfAMD)3"], core=["H2O"])
    ok("C: a role word with one candidate attributes it", r["species"] == "Y(DPfAMD)3", r)
    ok("C: tier B is recorded", r["species_basis"] == "LOCAL_ROLE_EXPLICIT", r)
    # ambiguity resolves nothing
    r = repair({"quantity": "purge_time", "raw_axis_label": "Precursor Purge (s)"},
               prec=["TMA", "TDMAT"], core=["H2O"])
    ok("C: two candidates for the role resolve nothing", r.get("species") is None, r)
    ok("C: no label, no attribution",
       repair({"quantity": "pulse_time"}, prec=["TMA"])  .get("species") is None)
    ok("C: a label naming no reagent and no role attributes nothing",
       repair({"quantity": "pulse_time", "raw_axis_label": "Dose time (ms)"},
              prec=["TMA"]).get("species") is None)
    # the longest inventory match wins, so a substring cannot shadow a longer name
    r = repair({"quantity": "pulse_time", "raw_axis_label": "MoCl2O2 pulse (s)"},
               prec=["Mo", "MoCl2O2"])
    ok("C: the longest matching reagent wins", r["species"] == "MoCl2O2", r)

    print("=== D. negative controls: things that are not species ===")
    for lab, pool in (("Number of bending cycles", ["TMA"]),
                      ("Deposition temperature", ["TMA"]),
                      ("H2 flow ratio", ["TMA"]),
                      ("Thickness (nm)", ["TMA"])):
        ok("D: %-26r attributes nothing" % lab,
           repair({"quantity": "pulse_time", "raw_axis_label": lab},
                  prec=pool).get("species") is None)
    # a substrate/film material in the label is not a dosed reagent unless the paper lists it
    ok("D: a film material absent from the inventory is not attributed",
       repair({"quantity": "pulse_time", "raw_axis_label": "SiO2 thickness (nm)"},
              prec=["TMA"], core=["H2O"]).get("species") is None)
    ok("D: 'bar' is never introduced as a species by attribution",
       repair({"quantity": "q", "raw_axis_label": "pressure (bar)"},
              prec=["TMA"]).get("species") is None)

    print("=== E. species distinguishes, and absence does not impersonate presence ===")
    a = fingerprint([{"quantity": "pulse_time", "value": 1, "species": "A"}])
    b = fingerprint([{"quantity": "pulse_time", "value": 1, "species": "B"}])
    n = fingerprint([{"quantity": "pulse_time", "value": 1, "species": None}])
    ok("E: two species on one quantity/value are different identities", a != b, (a, b))
    ok("E: unknown is not the same identity as a named species", n != a and n != b, (n, a))
    ok("E: unknown equals unknown", n == fingerprint(
        [{"quantity": "pulse_time", "value": 1}]))
    ok("E: an empty string and None are the same unknown",
       fingerprint([{"quantity": "pulse_time", "value": 1, "species": ""}]) == n)
    # determinism: the key is order-independent
    two = [{"quantity": "purge_time", "value": 2, "species": "B"},
           {"quantity": "pulse_time", "value": 1, "species": "A"}]
    ok("E: the fingerprint does not depend on condition order",
       fingerprint(two) == fingerprint(list(reversed(two))))
    ok("E: removing an invalid species changes identity",
       fingerprint([{"quantity": "q", "value": 1, "species": "bar"}]) !=
       fingerprint([{"quantity": "q", "value": 1, "species": None}]))

    print("=== F. the persisted corpus carries no invalid species ===")
    bad_unit, bad_struct, vals = [], [], set()
    for pid, c in all_cases():
        for x in c.get("case_defining_conditions") or []:
            s = x.get("species")
            if not s:
                continue
            vals.add(s)
            if str(s).strip().lower() == str(x.get("unit") or "").strip().lower():
                bad_unit.append((pid, c["case_id"], x["quantity"], s))
            if x.get("structural_identity"):
                bad_struct.append((pid, c["case_id"], x["quantity"], s))
    ok("F: no condition carries its own unit as a species", not bad_unit, bad_unit[:3])
    ok("F: no structural condition carries a species", not bad_struct, bad_struct[:3])
    ok("F: 'bar' is gone from the corpus", "bar" not in vals, sorted(vals))
    ok("F: 'SiO2' is gone from the corpus", "SiO2" not in vals, sorted(vals))
    ok("F: real reagents survive", {"H2O", "TMA"} <= vals, sorted(vals))

    print("=== G. every persisted species is evidenced or pre-existing, never invented ===")
    attributed = [(pid, c["case_id"], x) for pid, c in all_cases()
                  for x in c.get("case_defining_conditions") or []
                  if x.get("species_basis") in ("AXIS_LABEL_EXPLICIT", "LOCAL_ROLE_EXPLICIT")]
    ok("G: attribution actually ran on the corpus", attributed, len(attributed))
    ok("G: every attributed condition records its evidence",
       all(x.get("species_evidence") for _, _, x in attributed))
    ok("G: every attributed condition names the label it read",
       all(x.get("raw_axis_label") for _, _, x in attributed))
    ok("G: the attributed species appears in its own evidence string",
       all(str(x["species"]) in str(x["species_evidence"]) for _, _, x in attributed))

    print("=== H. identity structure is preserved ===")
    per = {}
    for pid, c in all_cases():
        per.setdefault(pid, []).append(c)
    ok("H: the active-8 case vector is unchanged",
       [len(per[p]) for p in json.loads((W / "pilot_papers.json").read_text())["papers"]]
       == [25, 66, 2, 11, 44, 7, 7, 20],
       [len(v) for v in per.values()])
    ok("H: 182 cases in total", sum(len(v) for v in per.values()) == 182)
    ok("H: every case id is unique within its paper",
       all(len({c["case_id"] for c in v}) == len(v) for v in per.values()))
    ok("H: every case carries a fingerprint",
       all(c.get("nominal_fingerprint") for v in per.values() for c in v))
    # the migration map is the machine-readable record of what moved
    mp = W.parent / "track_a" / "track_a2_migration_map.json"
    ok("H: the migration map exists", mp.exists(), str(mp))
    if mp.exists():
        m = json.loads(mp.read_text())
        ok("H: it records that no case ID moved",
           m["counts"]["case_ids_changed"] == 0 and not m["case_id_migration_required"], m["counts"])
        ok("H: it records the code that generated it, not only HEAD",
           len(str(m.get("generating_code_sha256") or "")) >= 8, m.get("generating_code_sha256"))
        ok("H: every relabeled case names a reason",
           all(x.get("reason") for x in m["migrated_cases"]))

    print("=== I. references still resolve (no case ID moved, so none should break) ===")
    dangling = []
    for pid in json.loads((W / "pilot_papers.json").read_text())["papers"]:
        ids = {c["case_id"] for c in cases(pid)}
        d = W / "papers" / pid / "semantic"
        for name, field in (("measurements.json", "measures_case"),
                            ("result_series.json", "experimental_case_ids"),
                            ("study_series.json", "member_case_ids")):
            f = d / name
            if not f.exists():
                continue
            obj = json.loads(f.read_text())
            for x in (obj.get(name[:-5], obj) if isinstance(obj, dict) else obj):
                for ref in (x.get(field) or []) if isinstance(x, dict) else []:
                    if ref not in ids:
                        dangling.append((pid, name, field, ref))
    ok("I: no reference points at a case that does not exist", not dangling, dangling[:4])

    print("=== J. genericity ===")
    src = (W / "code" / "pilot_semantics.py").read_text()
    code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                   for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("J: no DOI in executable pilot code", not re.search(r"10\.\d{4}[_/]", code))
    for lit in ("bar", "SiO2", "Y(DPfAMD)3", "SnI4", "TMA"):
        ok("J: no literal %-12r in executable code" % lit, lit not in code)
    ok("J: the rule reads the paper's own inventory, not a table",
       "scout" in src and "precursors" in src)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
