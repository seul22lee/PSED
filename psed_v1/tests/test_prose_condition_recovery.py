#!/usr/bin/env python3
"""Regression tests for source-supported conditions lost between prose and case.

Each section pins one GENERAL rule on synthetic constructions; the last section
uses one corpus paper (10.1063_1.5028178, the PillarHall LHAR growth-model
paper) as a WITNESS that the rules compose end-to-end. The paper appears only
here and in audit output — never in production branching logic.

  A. Coordinated timing statements distribute their values over the kind words.
  B. Docling glyph ligatures (µ as 'l', ° as '/C14') are repaired before parsing.
  C. Feature-dimension phrases parse with qualifiers and in reversed order;
     a stated aspect ratio is a condition.
  D. Gapped coordination types the second chemistry's temperature; the clause's
     reagent rides on the assertion as its species.
  E. bind() lets the source's own chemistry naming disambiguate same-scope
     values instead of declaring a conflict; unrelated species discard nothing.
  F. A species-qualified condition never enters a case of a different chemistry.
  G. Caption-scope geometry: the specific structure word wins; a bare "aspect
     ratio" is a quantity, not a geometry class.
  W. Corpus witness: the paper's two cases carry the full stated recipe, the
     model figures stay simulations, and nothing leaks across the chemistries.

Run:  python3 tests/test_prose_condition_recovery.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from pipeline.canonical import conditions as CC                 # noqa: E402
from pipeline.semantic import build_semantic as BS              # noqa: E402
from pipeline.semantic import roles as R                        # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def prose(text, scope="method"):
    out = CC.conditions_from_prose(text, scope, "methods", "methods", paper_id="T")
    return {(a["quantity"], str(a["value"]), a.get("species")): a for a in out}


def main():
    print("=== A. coordinated timing statements ===")
    got = prose("The precursor pulse and purge times were 0.2 and 6.0 s, respectively.")
    ok("A: 'pulse and purge times were A and B s' distributes in order",
       ("pulse_time", "0.2", None) in got and ("purge_time", "6.0", None) in got,
       sorted(got))
    got = prose("purge and pulse durations were 8 and 0.5 s")
    ok("A: reversed kind order reverses the assignment",
       ("purge_time", "8", None) in got and ("pulse_time", "0.5", None) in got,
       sorted(got))
    got = prose("followed by 0.3 and 5.0 s NH3 pulse and purge steps.")
    ok("A: the value-first form carries its clause's species",
       ("pulse_time", "0.3", "NH3") in got and ("purge_time", "5.0", "NH3") in got,
       sorted(got))
    got = prose("the pulse and pulse times were 1 and 2 s")
    ok("A: 'pulse and pulse' states no pair and asserts nothing paired",
       not any(q == "purge_time" for q, _, _ in got), sorted(got))

    print("=== B. docling glyph ligatures ===")
    ok("B: a number followed by 'l m' is µm",
       CC.fold_math("a gap height of 0.75 l m.") == "a gap height of 0.75 µm.")
    ok("B: prose letters are never rewritten",
       CC.fold_math("all metal layers") == "all metal layers")
    ok("B: '/C14 C' after a number is °C",
       "°C" in CC.fold_math("grown at 250 /C14 C in"))

    print("=== C. feature-dimension phrases ===")
    got = prose("with a nominal channel gap height of 0.4 µm", scope="figure")
    ok("C: a qualifier between structure and dimension word still parses",
       ("feature_height", "0.4", None) in got, sorted(got))
    got = prose("The width w of the trench was 80 nm", scope="figure")
    ok("C: the reversed statement order parses",
       ("feature_width", "80", None) in got, sorted(got))
    got = prose("which gives a structural aspect ratio of 1500.", scope="figure")
    ok("C: a stated aspect ratio is a condition",
       ("aspect_ratio", "1500", None) in got, sorted(got))

    print("=== D. gapped coordination of chemistries ===")
    got = prose("FilmA was grown from reagent (TMA) and water (H2O) at 200 °C and "
                "FilmB from reagent (TiCl4) and H2O at 90 °C.")
    temps = {(v, a.get("species")) for (q, v, _), a in got.items()
             if q == "deposition_temperature"}
    ok("D: both clauses' temperatures extract, each with its clause's reagent",
       ("200", "TMA") in temps and ("90", "TiCl4") in temps, temps)

    print("=== E. bind() chemistry disambiguation ===")
    a1 = dict(quantity="deposition_temperature", value="200", unit="°C",
              scope="method", species="TMA", raw_evidence="from TMA at 200 C",
              confidence=0.85, source_kind="methods")
    a2 = dict(quantity="deposition_temperature", value="90", unit="°C",
              scope="method", species="TiCl4", raw_evidence="from TiCl4 at 90 C",
              confidence=0.85, source_kind="methods")
    ent = {"fig_docling_index": None, "panel": None, "source_series": None,
           "paper_reagents": ["TMA", "TiCl4", "H2O"],
           "entity_reagents": ["TiCl4", "H2O"]}
    bound, amb, _ = CC.bind([dict(a1), dict(a2)], ent)
    ok("E: the entity's own chemistry selects its clause's value; no conflict",
       len(amb) == 0 and len(bound) == 1 and bound[0]["value"] == "90", (bound, amb))
    ent2 = dict(ent, entity_reagents=[])
    bound, amb, _ = CC.bind([dict(a1), dict(a2)], ent2)
    ok("E: with no chemistry to check against, the conflict stays a conflict",
       len(bound) == 0 and len(amb) == 1, (bound, amb))
    a3 = dict(a1, species="N2")     # not reagent-competitive
    bound, amb, _ = CC.bind([dict(a3), dict(a2)], dict(ent))
    ok("E: a species outside the declared reagents discards nothing",
       len(amb) == 1, (bound, amb))

    print("=== F. species-scoped case conditions ===")
    BS._cand.paper_reagents = {"precursor": ["TMA", "TiCl4"], "coreactant": ["H2O"]}
    case = {"precursors": ["TiCl4"], "coreactants": ["H2O"],
            "case_defining_conditions": [
                {"quantity": "pulse_time", "value": "0.1", "species": "AlMe3"},
                {"quantity": "pulse_time", "value": "0.1", "species": "H2O"},
                {"quantity": "flow_rate", "value": "150", "species": "N2"},
                {"quantity": "working_pressure", "value": "300", "species": None}]}
    out = BS.drop_foreign_species_conditions(dict(case))
    kept = {(c["quantity"], c.get("species")) for c in out["case_defining_conditions"]}
    ok("F: a foreign-chemistry reagent's condition is excluded, with a warning",
       ("pulse_time", "AlMe3") not in kept and out.get("warnings"), (kept, out.get("warnings")))
    ok("F: shared and non-reagent species stay",
       ("pulse_time", "H2O") in kept and ("flow_rate", "N2") in kept
       and ("working_pressure", None) in kept, kept)
    case2 = dict(case, precursors=[], coreactants=[])
    out2 = BS.drop_foreign_species_conditions(dict(case2))
    ok("F: an unresolved-chemistry case filters nothing",
       len(out2["case_defining_conditions"]) == 4)

    print("=== G. caption-scope geometry ===")
    gc, _ = R.geometry_in_scope("in PillarHall prototype with a structural aspect "
                                "ratio of 2000")
    ok("G: the named lateral structure wins over an aspect-ratio mention",
       gc == "lateral_channel", gc)
    gc, _ = R.geometry_in_scope("deposited in deep trenches with aspect ratio 30")
    ok("G: a trench caption still classifies vertical", gc == "vertical_structure", gc)
    gc, _ = R.geometry_in_scope("film thickness plotted versus aspect ratio")
    ok("G: a bare aspect-ratio mention claims NO geometry", gc is None, gc)
    gc, _ = R.geometry_in_scope("determined via ellipsometry on the samples")
    ok("G: the preposition 'via' claims no geometry", gc is None, gc)

    print("=== W. corpus witness: 10.1063_1.5028178 ===")
    d = W / "papers" / "10.1063_1.5028178" / "semantic"
    cases = json.loads((d / "experimental_cases.json").read_text())
    ok("W: the paper has exactly two experimental cases", len(cases) == 2, len(cases))
    by_fig = {tuple(c.get("source_figures") or []): c for c in cases}
    c6, c7 = by_fig.get(("6",)), by_fig.get(("7",))

    def cond(c, q, sp=None):
        return next((x for x in c["case_defining_conditions"]
                     if x["quantity"] == q and (x.get("species") or None) == sp), None)
    ok("W: Fig.6 carries the stated recipe (pulse/purge, T, gap, length, AR)",
       c6 is not None
       and cond(c6, "pulse_time", "AlMe3") and cond(c6, "purge_time", "AlMe3")
       and cond(c6, "pulse_time", "H2O") and cond(c6, "purge_time", "H2O")
       and float((cond(c6, "deposition_temperature", "TMA") or {}).get("value") or 0) == 300.0
       and cond(c6, "feature_height") and cond(c6, "feature_length")
       and cond(c6, "aspect_ratio"))
    ok("W: Fig.7 carries ITS chemistry's temperature (previously absent)",
       c7 is not None
       and float((cond(c7, "deposition_temperature", "TiCl4") or {}).get("value") or 0) == 110.0)
    ok("W: the other chemistry's step never leaks into Fig.7",
       c7 is not None and not cond(c7, "pulse_time", "AlMe3")
       and any("different chemistry" in str(w) for w in c7.get("warnings") or []))
    ok("W: both cases are lateral-channel, not vertical",
       all(c.get("geometry") == "lateral_channel" for c in cases),
       [c.get("geometry") for c in cases])
    sims = json.loads((d / "simulation_runs.json").read_text())
    ok("W: the model figures stay simulations and none founds a case",
       len(sims) >= 10 and not any(s.get("is_experimental_case") for s in sims),
       len(sims))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
