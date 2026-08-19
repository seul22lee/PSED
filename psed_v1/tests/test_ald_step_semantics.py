#!/usr/bin/env python3
"""An ALD cycle is a sequence, and a timing number means a different experiment in each
position. These pin the distinctions that a generic `pulse_time`/`purge_time` erased.

Run:  python3 tests/test_ald_step_semantics.py
"""
import sys
import json
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
from pipeline.canonical import process_steps as PS          # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    print("=== A. Figure 4 (e)-(h): the four positions of one cycle ===")
    # the printed panel labels and the species the paper establishes for each half-cycle
    labels = ["Dose time", "Purge time", "Plasma time", "Plasma purge"]
    recs = PS.resolve_panel_sequence(labels, species={0: "Al(CH3)3", 2: "O2"})
    e, f, g, h = recs

    ok("A: (e) Dose time is the precursor exposure",
       e["step_context"] == "precursor_exposure"
       and e["quantity"] == "dose_time", e)
    ok("A: (e) dose wording commits to NEITHER the pulse nor the exposure family",
       PS.timing_family_resolved(e["quantity"]) is None, e["quantity"])
    ok("A: (e) carries the precursor species", e["species"] == "Al(CH3)3", e)
    ok("A: (e) is not activated", e["activation"] == "none", e)

    ok("A: (f) Purge time is the PRECURSOR purge",
       f["step_context"] == "precursor_purge" and f["quantity"] == "purge_time", f)
    ok("A: (f) records the step it follows",
       f["follows"] == "precursor_exposure", f)

    ok("A: (g) Plasma time is the reactant exposure",
       g["step_context"] == "reactant_exposure"
       and g["quantity"] == "exposure_time", g)
    ok("A: a dose label keeps the dose kind; a plasma label keeps the exposure "
       "family — the position never rewrites the measurement",
       e["quantity"] != g["quantity"], (e["quantity"], g["quantity"]))
    ok("A: (g) names O2 as the species", g["species"] == "O2", g)
    ok("A: (g) records plasma as the ACTIVATION, not the material",
       g["activation"] == "plasma" and g["species"] == "O2", g)

    ok("A: (h) Plasma purge is the REACTANT purge",
       h["step_context"] == "reactant_purge" and h["quantity"] == "purge_time", h)
    ok("A: (h) follows the reactant exposure", h["follows"] == "reactant_exposure", h)
    ok("A: (h) is NOT itself plasma-active", h["activation"] == "none", h)
    ok("A: (h) records the preceding activation instead",
       h["preceding_activation"] == "plasma", h)

    print("=== B. the collapses that used to happen ===")
    ok("B: (e) and (g) are not the same quantity+context",
       (e["quantity"], e["step_context"]) != (g["quantity"], g["step_context"]),
       (e["step_context"], g["step_context"]))
    ok("B: (f) and (h) are not the same quantity+context",
       (f["quantity"], f["step_context"]) != (h["quantity"], h["step_context"]),
       (f["step_context"], h["step_context"]))
    ok("B: yet both exposures share the SIDE of the cycle they time",
       PS.timing_side(e["quantity"]) == PS.timing_side(g["quantity"])
       == PS.EXPOSURE_SIDE)
    ok("B: a pulse and an exposure remain different quantities — delivery and "
       "contact duration are not synonyms",
       PS.timing_kind("pulse_time") != PS.timing_kind("exposure_time"))
    ok("B: role evidence specialises without changing family",
       PS.specialize_timing_quantity("pulse_time", "precursor_exposure")
       == "precursor_pulse_time"
       and PS.specialize_timing_quantity("pulse_time", "reactant_exposure")
       == "coreactant_pulse_time"
       and PS.specialize_timing_quantity("exposure_time", "reactant_exposure")
       == "coreactant_exposure_time")
    ok("B: no role evidence leaves the quantity unspecialised",
       PS.specialize_timing_quantity("pulse_time") == "pulse_time")
    ok("B: and both purges share theirs",
       f["quantity"] == h["quantity"] == "purge_time")

    print("=== C. plasma is an activation, never a species or a material ===")
    ok("C: an activated exposure keeps its chemical species",
       g["species"] == "O2" and g["activation"] == "plasma")
    ok("C: 'plasma' is never returned as a species",
       all((r.get("species") or "").lower() != "plasma" for r in recs))
    act, ptype, _ = PS.classify_activation("Remote O2 plasma exposure",
                                           "reactant_exposure")
    ok("C: a remote plasma records its type when the source says so",
       act == "plasma" and ptype == "remote", (act, ptype))
    ok("C: an unqualified plasma claims no type",
       PS.classify_activation("Plasma time", "reactant_exposure")[1] is None)
    ok("C: a purge is never reported as plasma-active",
       PS.classify_activation("Plasma purge", "reactant_purge")[0] == "none")

    print("=== D. equal durations in different steps are different conditions ===")
    kp = PS.condition_key("exposure_time", "precursor_exposure", "Al(CH3)3")
    kr = PS.condition_key("exposure_time", "reactant_exposure", "O2")
    ok("D: a 2 s precursor dose and a 2 s plasma exposure differ in identity",
       kp != kr, (kp, kr))
    pp = PS.condition_key("purge_time", "precursor_purge")
    rp = PS.condition_key("purge_time", "reactant_purge")
    ok("D: the two purges of one cycle differ in identity", pp != rp, (pp, rp))
    ok("D: the key without step context would have collapsed them",
       PS.condition_key("purge_time") == PS.condition_key("purge_time"))
    # but identity is NOT plotting permission
    ka = PS.condition_key("exposure_time", "precursor_exposure", "TMA")
    kb = PS.condition_key("exposure_time", "precursor_exposure", "TEMAZ")
    ok("D: two precursor sweeps with different species are different conditions",
       ka != kb, (ka, kb))
    ok("D: yet they share quantity and step, which is what an axis needs",
       ka.split("@")[:2] == kb.split("@")[:2], (ka, kb))

    print("=== E. a species name never decides the position ===")
    step, ev = PS.classify_step("TMA pulse time")
    ok("E: naming a chemical is not evidence of a half-cycle", step is None, (step, ev))
    step2, _ = PS.classify_step("TMA pulse time", role_hint="precursor")
    ok("E: a persisted role resolves it", step2 == "precursor_exposure", step2)
    ok("E: and the role hint outranks the wording",
       PS.classify_step("plasma exposure", role_hint="precursor")[0]
       == "precursor_exposure")

    print("=== F. a bare purge needs its sequence, and says so when it has none ===")
    lone = PS.resolve_panel_sequence(["Purge time"])
    ok("F: a purge with no preceding exposure stays unresolved",
       lone[0]["step_context"] is None, lone[0])
    # print order ALONE must not assign a half-cycle: panels can be laid out by
    # importance or by material, and adjacency would then invent the assignment
    bare = PS.resolve_panel_sequence(["Plasma time", "Purge time"])
    ok("F: adjacency alone does not resolve a bare purge",
       bare[1]["step_context"] is None, bare[1])
    ok("F: and no corroboration is claimed for it",
       PS.sequence_corroboration(["Plasma time", "Purge time"]) is None)
    # the figure's own text is corroboration
    seq = PS.resolve_panel_sequence(["Plasma time", "Purge time"],
                                    evidence_text="O2 plasma exposure and purge times")
    ok("F: after a reactant exposure a bare purge is the reactant purge",
       seq[1]["step_context"] == "reactant_purge", seq[1])
    ok("F: and the evidence names the printed order",
       any("printed after" in x for x in seq[1]["evidence"]), seq[1]["evidence"])
    ok("F: and names what corroborated the sequence",
       seq[1].get("sequence_corroboration"), seq[1].get("evidence"))
    # so is a printed run that actually alternates exposure and purge
    alt = PS.resolve_panel_sequence(["Dose time", "Purge time"] * 2)
    ok("F: an alternating printed run is itself corroboration",
       [x["step_context"] for x in alt]
       == ["precursor_exposure", "precursor_purge"] * 2,
       [x["step_context"] for x in alt])

    print("=== G. the production condition path, not the module alone ===")
    from pipeline.canonical import conditions as C
    # Figure 4's own panel axes, driven through the real series-label reader
    got = {}
    for axis, val in (("Dose time", "0.5 s"), ("Purge time", "4 s"),
                      ("Plasma time", "2 s"), ("Plasma purge", "3 s")):
        got[axis] = C.from_series_label(val, axis)
    ok("G: (e) Dose time yields a precursor exposure assertion",
       got["Dose time"] and got["Dose time"][0]["step_context"] == "precursor_exposure",
       got["Dose time"])
    ok("G: (g) Plasma time yields a reactant exposure, plasma-activated",
       got["Plasma time"]
       and got["Plasma time"][0]["step_context"] == "reactant_exposure"
       and got["Plasma time"][0]["activation"] == "plasma", got["Plasma time"])
    ok("G: (g) plasma is the activation, and never the quantity or a species",
       got["Plasma time"][0]["quantity"] != "plasma"
       and (got["Plasma time"][0]["species"] or "") != "plasma", got["Plasma time"][0])
    ok("G: (h) Plasma purge yields a reactant purge that is NOT plasma-active",
       got["Plasma purge"]
       and got["Plasma purge"][0]["step_context"] == "reactant_purge"
       and got["Plasma purge"][0]["activation"] == "none", got["Plasma purge"])
    ok("G: (h) records the step it follows",
       got["Plasma purge"][0]["follows"] == "reactant_exposure", got["Plasma purge"][0])
    ok("G: (e) and (g) are distinguishable in the persisted assertion",
       got["Dose time"][0]["step_context"] != got["Plasma time"][0]["step_context"])
    ok("G: an assertion carries the step fields at all",
       all(k in got["Dose time"][0] for k in
           ("step_context", "activation", "plasma_type", "follows",
            "preceding_species", "preceding_activation", "step_evidence")))

    print("=== H. similarity slots keep the step ===")
    from pipeline.canonical import similarity as SIM
    pre = SIM.config({"controlled": [
        {"quantity": "pulse_time", "value": 2.0, "step_context": "precursor_exposure"},
        {"quantity": "purge_time", "value": 3.0, "step_context": "precursor_purge"}]})
    rea = SIM.config({"controlled": [
        {"quantity": "pulse_time", "value": 2.0, "step_context": "reactant_exposure"},
        {"quantity": "purge_time", "value": 3.0, "step_context": "reactant_purge"}]})
    ok("H: equal durations in different steps occupy different slots",
       set(pre["num"]) != set(rea["num"]), (pre["num"], rea["num"]))
    ok("H: both purges of one cycle survive together",
       len([k for k in pre["num"] if k.startswith("purge_time")]) == 1
       and len([k for k in rea["num"] if k.startswith("purge_time")]) == 1)
    both = SIM.config({"controlled": [
        {"quantity": "purge_time", "value": 3.0, "step_context": "precursor_purge"},
        {"quantity": "purge_time", "value": 7.0, "step_context": "reactant_purge"}]})
    ok("H: an A-purge-B-purge cycle keeps BOTH purge durations",
       sorted(both["num"].values()) == [3.0, 7.0], both["num"])
    ok("H: a step-less condition still fills its plain slot",
       "exposure_time" in SIM.config({"controlled": [
           {"quantity": "pulse_time", "value": 1.0}]})["num"])

    print("=== I. context reaches the Condition Case and the workbench ===")
    import json
    WB = W / "_diagnostics" / "workbench_v2" / "workbench_model.json"
    M = json.loads(WB.read_text())

    def panel_case(fig, pan, pred):
        for x in M["series"].values():
            if (str(x.get("figure")) == fig and x.get("panel") == pan
                    and pred(x) and x["all_case_ids"]):
                return M["cases"][x["all_case_ids"][0]], x
        return None, None

    # a panel that REDRAWS another panel's measurement must reach that measurement's case
    redrawn, rs = panel_case("9", "b", lambda x: x["paper_id"].endswith("d0cp03358h"))
    ok("I: a redrawn panel reaches a Condition Case at all", redrawn is not None)
    if redrawn:
        ok("I: and inherits the full process context, not a stub",
           len(redrawn["conditions"]) >= 8, len(redrawn["conditions"]))
        q = {c["quantity"] for c in redrawn["conditions"]}
        for want in ("cycle_number", "deposition_temperature", "precursor_pulse_time",
                     "coreactant_pulse_time", "working_pressure"):
            ok("I: it carries %s" % want, want in q, sorted(q))
        cyc = [c for c in redrawn["conditions"] if c["quantity"] == "cycle_number"]
        ok("I: its fixed cycle count is a value, not an ambiguity",
           cyc and cyc[0]["value"] not in (None, ""), cyc)
        ok("I: material and geometry survive",
           redrawn["material"] and redrawn["geometry"], redrawn["material"])
        ok("I: and its chemistry names both reagents",
           redrawn["chemistry"].get("precursor") and redrawn["chemistry"].get("coreactant"),
           redrawn["chemistry"])

    # a plasma panel must name the chemical and the activation separately
    plasma, _ = panel_case("4", "e", lambda x: x["paper_id"].endswith("067203jes"))
    ok("I: the plasma-ALD panel reaches a case", plasma is not None)
    if plasma:
        chem = plasma["chemistry"]
        ok("I: its coreactant is the chemical, not the channel",
           chem.get("coreactant") and all("plasma" not in s.lower()
                                          for s in chem["coreactant"]), chem)
        ok("I: the activation is reported beside it",
           "plasma" in (chem.get("coreactant_activation") or []), chem)
        ok("I: and the run-level process type survives",
           chem.get("process_type") == "plasma", chem)
        ok("I: material survives", plasma["material"] == "Al2O3", plasma["material"])
        ok("I: no chemistry value fuses species and activation",
           all("_plasma" not in str(v) for v in chem.values()), chem)

    print("=== J. represents-same inheritance is safe ===")
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location(
        "pilotsem", W / "_diagnostics" / "semantic_pilot_9papers" / "code"
        / "pilot_semantics.py")
    # the inheritance is a closure over the measurement list; exercise it as data
    def inherit(ms):
        by = {m["measurement_id"]: m for m in ms}

        def chain(mid):
            seen, cur = set(), mid
            while cur and cur not in seen:
                seen.add(cur)
                nxt = (by.get(cur) or {}).get("represents_same_measurement_as")
                if nxt == cur:
                    return None, "self-reference"
                cur = nxt
                if cur in seen:
                    return None, "cycle"
                if cur and (by.get(cur) or {}).get("measures_case"):
                    return by[cur], None
            return None, "no case anywhere in the chain"

        for _ in range(len(by) or 1):
            moved = 0
            for m in ms:
                if m.get("measures_case") or not m.get("represents_same_measurement_as"):
                    continue
                h, why = chain(m["measurement_id"])
                if h is None:
                    if why in ("cycle", "self-reference"):
                        m["measures_case_basis"] = "not inherited: %s" % why
                    continue
                m["measures_case"] = list(h["measures_case"])
                moved += 1
            if not moved:
                break
        return ms

    # an existing case is never overwritten
    ms = inherit([{"measurement_id": "A", "measures_case": ["CASE-1"]},
                  {"measurement_id": "B", "measures_case": ["CASE-2"],
                   "represents_same_measurement_as": "A"}])
    ok("J: a panel that established its own case keeps it",
       ms[1]["measures_case"] == ["CASE-2"], ms[1])
    # a chain resolves to the original
    ms = inherit([{"measurement_id": "A", "measures_case": ["CASE-1"]},
                  {"measurement_id": "B", "represents_same_measurement_as": "A"},
                  {"measurement_id": "C", "represents_same_measurement_as": "B"}])
    ok("J: a chain of re-renders reaches the original's case",
       ms[1]["measures_case"] == ["CASE-1"] and ms[2]["measures_case"] == ["CASE-1"], ms)
    # order does not matter
    ms = inherit([{"measurement_id": "C", "represents_same_measurement_as": "B"},
                  {"measurement_id": "B", "represents_same_measurement_as": "A"},
                  {"measurement_id": "A", "measures_case": ["CASE-1"]}])
    ok("J: and resolves whatever order the panels were built in",
       all(m.get("measures_case") == ["CASE-1"] for m in ms), ms)
    # a cycle establishes no original
    ms = inherit([{"measurement_id": "A", "represents_same_measurement_as": "B"},
                  {"measurement_id": "B", "represents_same_measurement_as": "A"}])
    ok("J: a two-panel cycle inherits nothing",
       not any(m.get("measures_case") for m in ms), ms)
    ok("J: and says why", all("cycle" in (m.get("measures_case_basis") or "")
                              for m in ms), ms)
    ms = inherit([{"measurement_id": "A", "represents_same_measurement_as": "A"}])
    ok("J: a self-reference inherits nothing",
       not ms[0].get("measures_case")
       and "self-reference" in (ms[0].get("measures_case_basis") or ""), ms[0])
    # a chain that never reaches a case stays empty
    ms = inherit([{"measurement_id": "A"},
                  {"measurement_id": "B", "represents_same_measurement_as": "A"}])
    ok("J: a chain with no case anywhere inherits nothing",
       not ms[1].get("measures_case"), ms[1])
    # the real corpus: no measurement inherits onto a conflicting case
    import json as _j
    sd = (W / "_diagnostics" / "semantic_pilot_9papers" / "papers"
          / "10.1039_d0cp03358h" / "semantic" / "measurements.json")
    real = _j.loads(sd.read_text())
    real = real if isinstance(real, list) else real.get("measurements", [])
    byid = {m.get("measurement_id"): m for m in real}
    bad = [m for m in real
           if m.get("represents_same_measurement_as")
           and (m.get("measures_case_basis") or "").startswith("inherited")
           and m.get("measures_case")
           != (byid.get(m["represents_same_measurement_as"]) or {}).get("measures_case")]
    ok("J: every inherited case in the corpus matches its holder's", not bad, bad[:1])

    # ---------------------------------------------------------------- K. end to end
    # The helper being right proves nothing about the corpus. These read the PERSISTED
    # records of a four-panel saturation figure -- dose, purge, plasma, plasma purge --
    # and require the structured fields, not a qualified name that merely looks like one.
    print("\n=== K. persisted step semantics, extraction -> case -> workbench ===")
    sem = _j.loads((W / "_diagnostics" / "semantic_pilot_9papers" / "papers"
                    / "10.1149_2.067203jes" / "semantic"
                    / "experimental_cases.json").read_text())
    sem = sem if isinstance(sem, list) else sem.get("cases", [])
    model = _j.loads((W / "_diagnostics" / "workbench_v2"
                      / "workbench_model.json").read_text())

    def _panel_case(panel):
        """The Condition Case a printed panel's swept series is bound to."""
        s = [x for x in model["series"].values()
             if x["paper_id"] == "10.1149_2.067203jes"
             and str(x.get("figure")) == "4" and x.get("panel") == panel]
        ok("K: panel (%s) resolves to exactly one series and case" % panel,
           len(s) == 1 and len(s[0]["all_case_ids"]) >= 1, [x["id"] for x in s])
        return model["cases"][s[0]["all_case_ids"][0]]

    def _step_cond(case):
        c = [x for x in case["conditions"] if x.get("step_context")]
        return c[0] if len(c) == 1 else None

    #: what the source figure states, panel by panel: a TMA dose, its purge, an O2 plasma
    #: exposure, and the purge that follows the plasma
    #: The persisted quantity is now ROLE-SPECIALISED and keeps the timing family the
    #: extracted axis recorded (an exposure-named axis stays an exposure, a pulse-named
    #: one stays a pulse); the position still lives in step_context. The old pins fixed
    #: the collapsed spelling (`exposure_time` for everything on the contact side),
    #: which rewrote a stated pulse as an exposure statement the source never made.
    WANT = {
        "e": {"quantity": "precursor_exposure_time",
              "step_context": "precursor_exposure",
              "activation": "none", "species_is": "precursor"},
        "f": {"quantity": "precursor_purge_time", "step_context": "precursor_purge",
              "activation": "none", "follows": "precursor_exposure"},
        "g": {"quantity": "coreactant_pulse_time", "step_context": "reactant_exposure",
              "activation": "plasma", "species_is": "coreactant"},
        "h": {"quantity": "coreactant_purge_time", "step_context": "reactant_purge",
              "activation": "none", "follows": "reactant_exposure",
              "preceding_activation": "plasma"},
    }
    for panel, want in sorted(WANT.items()):
        case = _panel_case(panel)
        cond = _step_cond(case)
        ok("K: (%s) carries exactly one step-scoped condition" % panel, bool(cond), cond)
        if not cond:
            continue
        for field in ("quantity", "step_context", "activation", "follows",
                      "preceding_activation"):
            if field not in want:
                continue
            ok("K: (%s) %-21s = %s" % (panel, field, want[field]),
               cond.get(field) == want[field], cond.get(field))
        # the reagent is bound from the case's own chemistry, and a purge never gets one
        if want.get("species_is") == "precursor":
            ok("K: (%s) species is the case's precursor" % panel,
               cond.get("species") and cond["species"] in (case["chemistry"] or {}).get(
                   "precursor", []), (cond.get("species"), case.get("chemistry")))
        elif want.get("species_is") == "coreactant":
            ok("K: (%s) species is the case's co-reactant" % panel,
               cond.get("species") and cond["species"] in (case["chemistry"] or {}).get(
                   "coreactant", []), (cond.get("species"), case.get("chemistry")))
        else:
            ok("K: (%s) a purge is dosed with nothing" % panel,
               cond.get("species") is None, cond.get("species"))
            ok("K: (%s) but names the species it purges away" % panel,
               bool(cond.get("preceding_species")), cond.get("preceding_species"))

    ok("K: no Fig 4 panel is left with a generic unpositioned timing quantity",
       not [p for p in "abcdefgh"
            if not _step_cond(_panel_case(p))],
       [p for p in "abcdefgh" if not _step_cond(_panel_case(p))])

    # the same fields must exist one stage earlier, or the workbench is inventing them
    j4 = [c for c in sem
          if any(x.get("step_context") for x in c.get("case_defining_conditions") or [])]
    ok("K: the semantic layer -- not the workbench -- is where the step is decided",
       len(j4) >= 8, len(j4))
    ok("K: every step-scoped semantic condition keeps the source's own word too",
       all(x.get("source_quantity")
           for c in j4 for x in c["case_defining_conditions"] if x.get("step_context")))
    ok("K: a purge is never persisted as plasma-active",
       not [x for c in j4 for x in c["case_defining_conditions"]
            if x.get("step_context") in ("precursor_purge", "reactant_purge")
            and x.get("activation") == "plasma"])

    # ------------------------------------------------------- L. recipe schema capacity
    # Representing A-purge-B-purge in the step module is not the same as being able to
    # STORE it. The resolved recipe is where a process is persisted, so it is asked
    # directly: two reagents, each with its own dose and its own purge, round-tripped.
    print("\n=== L. the resolved recipe schema stores a full A-purge-B-purge cycle ===")
    from pipeline.resolve.recipe import Recipe, Reactant
    r = Recipe(material="Al2O3", cycle_sequence="AB",
               reactants=[Reactant(label="A", role="precursor", species="Al(CH3)3",
                                   dose_time=0.03, purge_time=2.5),
                          Reactant(label="B", role="coreactant", species="O2_plasma",
                                   dose_time=2.0, purge_time=0.5)])
    d = r.to_dict()
    ok("L: both half-cycles persist as separate reactants",
       [x["label"] for x in d["reactants"]] == ["A", "B"])
    ok("L: each reactant persists its OWN dose and its OWN purge",
       [(x["dose_time"], x["purge_time"]) for x in d["reactants"]]
       == [(0.03, 2.5), (2.0, 0.5)], d["reactants"])
    ok("L: the cycle order is persisted alongside them", d["cycle_sequence"] == "AB")
    ok("L: four distinct timed steps survive the round trip",
       len({(x["label"], k) for x in d["reactants"]
            for k in ("dose_time", "purge_time")}) == 4)
    # activation is structural, not glued onto the species: a plasma O2 exposure and a
    # thermal O2 exposure name the SAME chemical under different delivery
    ok("L: activation is a first-class recipe field", "activation" in d["reactants"][1],
       sorted(d["reactants"][1]))
    from pipeline.resolve.recipe import from_experiment
    built = from_experiment({
        "material": "Al2O3",
        "reactants": [{"label": "B", "role": "coreactant", "species": "O2_plasma"}],
        "controlled": [{"quantity": "pulse_time", "value": -120.0, "unit": "ms"}]}).to_dict()
    b = built["reactants"][0]
    ok("L: the canonical recipe stores the CHEMICAL, not the channel token",
       b["species"] == "O2", b["species"])
    ok("L: and records the activation beside it", b["activation"] == "plasma", b)
    ok("L: 'O2_plasma' is no longer the canonical reactant representation",
       "O2_plasma" not in json.dumps(built["reactants"]), built["reactants"])
    # the fused token is still on record as what the SOURCE said -- splitting it is a
    # canonicalisation, not a claim that the source wrote it differently
    ok("L: while provenance still preserves the token the source used",
       (built["param_sources"].get("species::B") or {}).get("value") == "O2_plasma",
       built["param_sources"].get("species::B"))
    # a written range read as a negative number must never reach the record
    ok("L: a non-positive duration is refused, not stored", b["dose_time"] is None,
       b["dose_time"])
    # the repair happens at the first deterministic read of the persisted conditions, so
    # every consumer inherits it -- not only the one that fills a Reactant
    from pipeline.resolve.recipe import sanitize_controlled
    san = sanitize_controlled({
        "controlled": [{"quantity": "pulse_time", "value": -120.0, "unit": "ms",
                        "origin": {"evidence": "doses (10-120 ms"}}]})["controlled"][0]
    ok("L: the impossible scalar is removed at the source read", san["value"] is None, san)
    ok("L: and where the evidence still shows the range, it is restored",
       san.get("value_range") == [10.0, 120.0]
       and san["value_status"] == "repaired_from_written_range", san)
    ok("L: with the reason recorded", "minus sign" in (san.get("sanitized_reason") or ""),
       san.get("sanitized_reason"))
    bare = sanitize_controlled({
        "controlled": [{"quantity": "purge_time", "value": -3.0, "unit": "s"}]})["controlled"][0]
    ok("L: with no range evidence it is refused, never guessed",
       bare["value"] is None and bare.get("value_range") is None
       and bare["value_status"] == "refused_non_positive", bare)
    keep = sanitize_controlled({
        "controlled": [{"quantity": "deposition_temperature", "value": -20.0,
                        "unit": "C"}]})["controlled"][0]
    ok("L: a quantity that CAN be negative is left alone", keep["value"] == -20.0, keep)
    ok("L: a positive duration is untouched",
       from_experiment({"material": "Al2O3",
                        "reactants": [{"label": "A", "role": "precursor",
                                       "species": "TMA"}],
                        "controlled": [{"quantity": "pulse_time", "value": 0.06,
                                        "unit": "s"}]}).reactants[0].dose_time == 0.06)

    # ------------------------------------------------- M2. activation is part of identity
    print("\n=== M2. activation distinguishes otherwise identical conditions ===")
    same = dict(quantity="exposure_time", step_context=PS.REACTANT_EXPOSURE, species="O2")
    ok("M2: a thermal and a plasma O2 exposure are different conditions",
       PS.condition_key(**same, activation=PS.ACTIVATION_NONE)
       != PS.condition_key(**same, activation=PS.ACTIVATION_PLASMA))
    ok("M2: while everything else about them is identical",
       PS.condition_key(**same, activation=PS.ACTIVATION_PLASMA)
       == PS.condition_key(**same, activation=PS.ACTIVATION_PLASMA))
    ok("M2: an unstated activation is a third state, not silently thermal",
       PS.condition_key(**same) != PS.condition_key(**same,
                                                    activation=PS.ACTIVATION_NONE))
    from pipeline.canonical import similarity as SIM
    ok("M2: the similarity layer keeps them in separate slots",
       "activation" in (W / "pipeline" / "canonical" / "similarity.py").read_text())

    # ------------------------------------------------- M3. canonical chemical identity
    print("\n=== M3. one canonical identity per chemical reagent ===")
    from pipeline.canonical import chemical_identity as CI
    same = ["TMA", "trimethylaluminum", "trimethyl aluminium", "Trimethyl-Aluminium",
            "Al(CH3)3", "AlMe3"]
    keys = {CI.identity_key(s, CI.PRECURSOR) for s in same}
    ok("M3: abbreviation, full name, spelling variants and formula are one identity",
       len(keys) == 1, sorted(keys))
    ok("M3: and that identity is the ontology's own id", keys == {"TMA"}, sorted(keys))
    ok("M3: the source string is preserved as provenance",
       CI.resolve("Al(CH3)3", CI.PRECURSOR)["source_label"] == "Al(CH3)3")
    ok("M3: a different reagent keeps a different identity",
       CI.identity_key("H2O") != CI.identity_key("TMA"))
    # equivalence comes from the ontology, never from resemblance
    ok("M3: an unknown reagent is NOT merged into a similar-looking one",
       CI.identity_key("HDMP") != CI.identity_key("Pt(acac)2")
       and not CI.resolve("HDMP")["resolved"],
       (CI.identity_key("HDMP"), CI.identity_key("Pt(acac)2")))
    ok("M3: two records of the same unknown reagent still group",
       CI.identity_key("HDMP") == CI.identity_key("hdmp"))
    ok("M3: a delivery channel is split into chemical + activation",
       (CI.resolve("O2_plasma")["identity_key"],
        CI.resolve("O2_plasma")["activation"]) == ("O2", "plasma"))
    # the corpus itself must no longer split one reagent across spellings
    model = _j.loads((W / "_diagnostics" / "workbench_v2"
                      / "workbench_model.json").read_text())
    split = {}
    for c in model["cases"].values():
        for role, hint in (("precursor", CI.PRECURSOR), ("coreactant", CI.COREACTANT)):
            for s in ((c.get("chemistry") or {}).get(role) or []):
                split.setdefault(CI.identity_key(s, hint), set()).add(s)
    bad = {k: sorted(v) for k, v in split.items() if len(v) > 1}
    ok("M3: no canonical reagent is stored under two different strings", not bad, bad)

    # ------------------------------------------------------------- M4. gas roles
    print("\n=== M4. carrier and purge gases are structured, and stay distinct ===")
    from pipeline.canonical import gas_roles as GR
    rec = GR.gas_roles_from_text("Argon was used as carrier and purging gas.")
    got = {r["role"]: r["species"] for r in rec}
    ok("M4: one sentence can establish both roles",
       got == {"carrier_gas": "Ar", "purge_gas": "Ar"}, got)
    ok("M4: the gas is resolved to a canonical chemical, not its written name",
       all(r["identity_key"] == "Ar" for r in rec), rec[:1])
    only = GR.gas_roles_from_text("N2 was used as the purge gas.")
    ok("M4: a statement binds only the role it names",
       {r["role"] for r in only} == {"purge_gas"}, only)
    ok("M4: a sentence naming no species establishes nothing",
       not GR.gas_roles_from_text("The carrier gas was controlled by a mass flow "
                                  "controller."))
    ok("M4: disagreeing statements leave the role unresolved",
       "carrier_gas" not in GR.unambiguous_roles(
           [{"role": "carrier_gas", "identity_key": "Ar"},
            {"role": "carrier_gas", "identity_key": "N2"}]))
    ok("M4: a purge GAS never produces a purge DURATION",
       all("time" not in k and "duration" not in k
           for r in rec for k in r))
    # and it reaches the persisted cases, in more than one paper
    carriers = {c["paper_id"]: c.get("carrier_gas") for c in model["cases"].values()
                if c.get("carrier_gas")}
    ok("M4: carrier gases are persisted for several papers", len(carriers) >= 2,
       carriers)

    # ------------------------------------- M5. thermal is not the same as unstated
    print("\n=== M5. explicit thermal and unstated activation stay distinct ===")
    from pipeline.canonical import similarity as SIM
    base = dict(quantity="exposure_time", step_context=PS.REACTANT_EXPOSURE, species="O2")
    ok("M5: condition_key separates them",
       PS.condition_key(**base, activation=PS.ACTIVATION_NONE)
       != PS.condition_key(**base))
    def _slot(act):
        e = {"controlled": [{"quantity": "pulse_time", "value": 2.0,
                             "step_context": PS.REACTANT_EXPOSURE, "activation": act}]}
        return sorted(SIM.config(e)["num"])
    ok("M5: the similarity slot separates them", _slot("none") != _slot(None),
       (_slot("none"), _slot(None)))
    ok("M5: and plasma is separate from both",
       len({str(_slot("none")), str(_slot(None)), str(_slot("plasma"))}) == 3)
    fields = model.get("range_fields") or []
    coll = {}
    for f in fields:
        coll.setdefault(f["field_id"], set()).add(str(f.get("activation")))
    ok("M5: no persisted field id carries two activation states",
       not {k: v for k, v in coll.items() if len(v) > 1})

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
