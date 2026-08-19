#!/usr/bin/env python3
"""Two failures that both came from demanding corroboration the record need not carry.

A paper titled "... TiO2 Nanotube Layers" was classified planar because no numeric
geometry quantity happened to be extracted, and a "Number of ALD cycles" axis was called
unresolved because the figure did not reprint a unit the ontology already declares. In
both cases the strongest evidence available was discarded for want of a weaker one.

Run:  python3 tests/test_geometry_and_count_axis.py
"""
import json
import sys
from pathlib import Path
from unittest import mock

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
PILOT = W / "_diagnostics" / "semantic_pilot_9papers" / "papers"
WB = W / "_diagnostics" / "workbench_v2"

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def _classify(sd, quants):
    from pipeline.text import geometry as G
    with mock.patch.object(G.P, "extracted_dir", lambda x: sd / "extracted"), \
         mock.patch.object(G, "_paper_quants", lambda x: set(quants)):
        return G.classify_deterministic(sd)


def main():
    print("=== A. a named structure does not need a numeric quantity ===")
    # the paper is found by its own evidence, not by its identifier
    cands = [p for p in PILOT.iterdir()
             if (p / "extracted" / "document.md").exists()
             and "nanotube" in (p / "extracted" / "document.md").read_text()[:2000].lower()]
    ok("A: a paper naming nanotubes in its opening text exists", bool(cands),
       [p.name for p in PILOT.iterdir()][:3])
    if not cands:
        print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
        return 1 if _fail else 0
    sd = cands[0]

    klass, struct, why = _classify(sd, set())          # NO geometry quantities at all
    ok("A: explicit nanotube wording alone establishes a non-planar geometry",
       klass != "planar", (klass, struct, why))
    ok("A: and names the structure", klass == "nanostructure_array" and struct == "cnt",
       (klass, struct))
    ok("A: the evidence says the quantity was absent, rather than hiding it",
       "no numeric geometry quantity" in why, why)

    klass2, struct2, why2 = _classify(sd, {"aspect_ratio"})
    ok("A: a numeric quantity corroborates rather than changes the class",
       (klass2, struct2) == (klass, struct), (klass2, struct2))
    ok("A: and the evidence records the corroboration",
       "conformality quantities" in why2, why2)

    print("=== B. a quantity's declared unit survives a silent axis ===")
    from pipeline.canonical.axis_semantics import ontology_axis_unit
    from ontology import vocab
    ok("B: the ontology declares a unit for the cycle count",
       vocab.quantity_unit("cycle_number") == "cycle", vocab.quantity_unit("cycle_number"))
    u, basis = ontology_axis_unit("cycle_number", "")
    ok("B: an axis that printed no unit takes the ontology's", u == "cycle", (u, basis))
    ok("B: and says where it came from", "ontology-declared" in basis, basis)
    ok("B: a printed unit always wins",
       ontology_axis_unit("cycle_number", "cycle")[0] == "cycle"
       and "source axis" in ontology_axis_unit("cycle_number", "cycle")[1])
    ok("B: a quantity the ontology gives no unit stays unresolved",
       ontology_axis_unit("deposition_temperature", "")[0] is None)
    ok("B: and so does an axis whose quantity never resolved",
       ontology_axis_unit(None, "")[0] is None)
    ok("B: a blank unit is never silently called dimensionless",
       ontology_axis_unit("__no_such_quantity__", "")[0] is None)

    print("=== C. the count axis reaches the workbench as an overlay target ===")
    M = json.loads((WB / "workbench_model.json").read_text())
    count_series = [s for s in M["series"].values()
                    if ((s.get("native_points") or {}).get("x") or {}).get("quantity")
                    == "cycle_number"]
    ok("C: the corpus carries cycle-count axes", len(count_series) >= 2, len(count_series))
    silent = [s for s in count_series
              if not (s["native_points"]["x"] or {}).get("unit")]
    ok("C: some of them print no unit on the axis", bool(silent), len(silent))
    ok("C: every one of those still resolves an overlay target",
       all(s["x_representations"]["native_source"]["overlay_target_id"] for s in silent),
       [s["series_id"] for s in silent
        if not s["x_representations"]["native_source"]["overlay_target_id"]][:2])
    ok("C: on the ontology's count unit",
       all(s["x_representations"]["native_source"]["unit"] == "cycle" for s in silent))
    ok("C: and the target names the count dimension",
       all("cycle" in s["x_representations"]["native_source"]["overlay_target_id"]
           for s in silent))

    print("=== D. the two reported cases share both axes ===")
    # case_id is unique only within its paper, so the pair is scoped by paper -- found
    # by the axis semantics under test, not by naming a DOI
    want = ("CASE-10.103-011", "CASE-10.103-012")
    cand = [c for c in M["cases"].values() if c["case_id"] in want]
    papers = {c["paper_id"] for c in cand
              if any(((M["series"][s].get("native_points") or {}).get("x") or {}).get(
                  "quantity") == "cycle_number" for s in c["series_ids"])}
    sids = [sid for c in cand if c["paper_id"] in papers for sid in c["series_ids"]
            if ((M["series"][sid].get("native_points") or {}).get("x") or {}).get(
                "quantity") == "cycle_number"]
    ok("D: both cases are present", len(sids) == 2, len(sids))
    if len(sids) == 2:
        a, b = (M["series"][x] for x in sids)
        xa = a["x_representations"]["native_source"]["overlay_target_id"]
        xb = b["x_representations"]["native_source"]["overlay_target_id"]
        ya = a["y_representations"]["native_source"]["overlay_target_id"]
        yb = b["y_representations"]["native_source"]["overlay_target_id"]
        ok("D: they share one x target", xa and xa == xb, (xa, xb))
        ok("D: and one y target", ya and ya == yb, (ya, yb))
        # the differing precursor is a property of the series, never an overlay veto
        prec = {p for c in cand if c["paper_id"] in papers
                for p in (c["chemistry"].get("precursor") or [])}
        ok("D: their precursors really do differ", len(prec) == 2, sorted(prec))
        ok("D: which does not appear in either axis target",
           not any(p in (xa or "") + (ya or "") for p in prec), sorted(prec))

    print("=== E. local geometry outranks the paper-level fallback ===")
    from pipeline.text import geometry as GG
    # a paper that deposits on nanotubes AND on a planar reference: the local value must
    # survive the paper-level classification
    mixed = [{"experiment_id": "E1", "geometry_class": "planar",
              "structure": "planar_wafer", "geometry_source": "figure/panel caption",
              "geometry_evidence": "caption: planar reference coupon"},
             {"experiment_id": "E2"},
             {"experiment_id": "E3", "geometry_evidence": "caption: trench array"}]
    ok("E: an experiment naming its own geometry is recognised as local",
       GG._has_local_geometry(mixed[0]) and GG._has_local_geometry(mixed[2]))
    ok("E: one with none is not", not GG._has_local_geometry(mixed[1]))
    # the tagger fills only the silent one
    import json as _j
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pid = "__fixture_paper__"
        (root / pid / "extracted").mkdir(parents=True)
        (root / pid / "resolved").mkdir(parents=True)
        (root / pid / "extracted" / "geometry.json").write_text(_j.dumps(
            {"geometry_class": "nanostructure_array", "structure": "cnt",
             "evidence": "keyword: nanostructure"}))
        (root / pid / "resolved" / "experiments.json").write_text(_j.dumps(mixed))
        (root / pid / "resolved" / "entities.json").write_text(_j.dumps(
            [{"experiment_id": e["experiment_id"]} for e in mixed]))
        import paths as _P
        prev = _P.set_corpus_root(root)
        try:
            GG.tag_experiments([pid])
            GG.refresh_entities([pid])
            got = _j.loads((root / pid / "resolved" / "experiments.json").read_text())
            ents = _j.loads((root / pid / "resolved" / "entities.json").read_text())
        finally:
            _P.set_corpus_root(prev)
    by = {e["experiment_id"]: e for e in got}
    ok("E: the planar reference keeps its own geometry",
       by["E1"]["geometry_class"] == "planar", by["E1"])
    ok("E: the silent experiment takes the paper-level fallback",
       by["E2"]["geometry_class"] == "nanostructure_array"
       and by["E2"]["geometry_source"] == "paper-level deterministic classification",
       by["E2"])
    ok("E: the one with its own evidence is untouched",
       by["E3"].get("geometry_class") != "nanostructure_array"
       or by["E3"].get("geometry_source") != "paper-level deterministic classification",
       by["E3"])
    ok("E: so one paper carries two geometries",
       len({e.get("geometry_class") for e in got}) > 1,
       [e.get("geometry_class") for e in got])
    eb = {e["experiment_id"]: e for e in ents}
    # the source travels with the value: a caption-derived geometry stays caption-derived
    # rather than being relabelled once it reaches the entity
    ok("E: entities inherit the experiment-local value where one exists",
       eb["E1"]["geometry_class"] == "planar"
       and eb["E1"]["geometry_source"] == "figure/panel caption", eb["E1"])
    ok("E: and a paper-level value is never promoted to local evidence",
       eb["E2"]["geometry_source"] == "paper-level deterministic classification",
       eb["E2"])
    ok("E: and the fallback elsewhere",
       eb["E2"]["geometry_class"] == "nanostructure_array", eb["E2"])

    print("=== F. the corrected geometry survives regeneration ===")
    corp = W / "_diagnostics" / "semantic_pilot_9papers" / "papers"
    tgt = [p for p in corp.iterdir()
           if (p / "extracted" / "document.md").exists()
           and "nanotube" in (p / "extracted" / "document.md").read_text()[:2000].lower()]
    ok("F: the nanotube paper is in the pilot corpus", bool(tgt))
    if tgt:
        g = json.loads((tgt[0] / "extracted" / "geometry.json").read_text())
        ok("F: its regenerated geometry.json is non-planar",
           g["geometry_class"] != "planar", g)
        ents = json.loads((tgt[0] / "resolved" / "entities.json").read_text())
        ents = ents if isinstance(ents, list) else ents.get("entities", [])
        ok("F: its resolved entities are non-planar",
           ents and all(e.get("geometry_class") != "planar" for e in ents),
           {e.get("geometry_class") for e in ents})
        cases = json.loads((tgt[0] / "semantic" / "experimental_cases.json").read_text())
        cases = cases["experimental_cases"] if isinstance(cases, dict) else cases
        ok("F: its Condition Cases are non-planar",
           all(c.get("geometry") != "planar" for c in cases),
           {c.get("geometry") for c in cases})
        wb = [c for c in M["cases"].values() if c["paper_id"] == tgt[0].name]
        ok("F: and the workbench shows them non-planar",
           wb and all(c["geometry"] != "planar" for c in wb),
           {c["geometry"] for c in wb})

    print("=== E. local geometry outranks the paper-level fallback ===")
    from pipeline.text import geometry as GG
    # a paper that deposits on nanotubes AND on a planar reference: the local value must
    # survive the paper-level classification
    mixed = [{"experiment_id": "E1", "geometry_class": "planar",
              "structure": "planar_wafer", "geometry_source": "figure/panel caption",
              "geometry_evidence": "caption: planar reference coupon"},
             {"experiment_id": "E2"},
             {"experiment_id": "E3", "geometry_evidence": "caption: trench array"}]
    ok("E: an experiment naming its own geometry is recognised as local",
       GG._has_local_geometry(mixed[0]) and GG._has_local_geometry(mixed[2]))
    ok("E: one with none is not", not GG._has_local_geometry(mixed[1]))
    # the tagger fills only the silent one
    import json as _j
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pid = "__fixture_paper__"
        (root / pid / "extracted").mkdir(parents=True)
        (root / pid / "resolved").mkdir(parents=True)
        (root / pid / "extracted" / "geometry.json").write_text(_j.dumps(
            {"geometry_class": "nanostructure_array", "structure": "cnt",
             "evidence": "keyword: nanostructure"}))
        (root / pid / "resolved" / "experiments.json").write_text(_j.dumps(mixed))
        (root / pid / "resolved" / "entities.json").write_text(_j.dumps(
            [{"experiment_id": e["experiment_id"]} for e in mixed]))
        import paths as _P
        prev = _P.set_corpus_root(root)
        try:
            GG.tag_experiments([pid])
            GG.refresh_entities([pid])
            got = _j.loads((root / pid / "resolved" / "experiments.json").read_text())
            ents = _j.loads((root / pid / "resolved" / "entities.json").read_text())
        finally:
            _P.set_corpus_root(prev)
    by = {e["experiment_id"]: e for e in got}
    ok("E: the planar reference keeps its own geometry",
       by["E1"]["geometry_class"] == "planar", by["E1"])
    ok("E: the silent experiment takes the paper-level fallback",
       by["E2"]["geometry_class"] == "nanostructure_array"
       and by["E2"]["geometry_source"] == "paper-level deterministic classification",
       by["E2"])
    ok("E: the one with its own evidence is untouched",
       by["E3"].get("geometry_class") != "nanostructure_array"
       or by["E3"].get("geometry_source") != "paper-level deterministic classification",
       by["E3"])
    ok("E: so one paper carries two geometries",
       len({e.get("geometry_class") for e in got}) > 1,
       [e.get("geometry_class") for e in got])
    eb = {e["experiment_id"]: e for e in ents}
    # the source travels with the value: a caption-derived geometry stays caption-derived
    # rather than being relabelled once it reaches the entity
    ok("E: entities inherit the experiment-local value where one exists",
       eb["E1"]["geometry_class"] == "planar"
       and eb["E1"]["geometry_source"] == "figure/panel caption", eb["E1"])
    ok("E: and a paper-level value is never promoted to local evidence",
       eb["E2"]["geometry_source"] == "paper-level deterministic classification",
       eb["E2"])
    ok("E: and the fallback elsewhere",
       eb["E2"]["geometry_class"] == "nanostructure_array", eb["E2"])

    print("=== F. the corrected geometry survives regeneration ===")
    corp = W / "_diagnostics" / "semantic_pilot_9papers" / "papers"
    tgt = [p for p in corp.iterdir()
           if (p / "extracted" / "document.md").exists()
           and "nanotube" in (p / "extracted" / "document.md").read_text()[:2000].lower()]
    ok("F: the nanotube paper is in the pilot corpus", bool(tgt))
    if tgt:
        g = json.loads((tgt[0] / "extracted" / "geometry.json").read_text())
        ok("F: its regenerated geometry.json is non-planar",
           g["geometry_class"] != "planar", g)
        ents = json.loads((tgt[0] / "resolved" / "entities.json").read_text())
        ents = ents if isinstance(ents, list) else ents.get("entities", [])
        ok("F: its resolved entities are non-planar",
           ents and all(e.get("geometry_class") != "planar" for e in ents),
           {e.get("geometry_class") for e in ents})
        cases = json.loads((tgt[0] / "semantic" / "experimental_cases.json").read_text())
        cases = cases["experimental_cases"] if isinstance(cases, dict) else cases
        ok("F: its Condition Cases are non-planar",
           all(c.get("geometry") != "planar" for c in cases),
           {c.get("geometry") for c in cases})
        wb = [c for c in M["cases"].values() if c["paper_id"] == tgt[0].name]
        ok("F: and the workbench shows them non-planar",
           wb and all(c["geometry"] != "planar" for c in wb),
           {c["geometry"] for c in wb})

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
