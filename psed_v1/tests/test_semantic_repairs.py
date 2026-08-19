#!/usr/bin/env python3
"""Regression tests for the figure-provenance repairs.

Each section pins one GENERAL semantic rule, exercised on synthetic constructions and
then audited over the live corpus. No test names a DOI-specific expectation: the corpus
assertions quantify over every paper, so an analogous defect in an unseen paper fails
the same check.

  A. X representation reachability is independent of Y, and vice versa.
  B. Alternate representations of one MeasurementAct are reachable, and are a DIFFERENT
     relation from a derived transform.
  C. Document-defined named representations resolve generically; without document
     evidence they stay unresolved.
  D. Overlay authorisation, comparability status, and missing-context report read one
     authority and cannot contradict.
  E. Pulse-time role specialisation: species/role evidence specialises, never rewrites
     the timing family; exposure_time only exists where the source said so.
  F. One physical timing slot is one condition dimension per case.
  G. Known context is never rendered as unknown, and never leaks across a paper's
     chemistries.

Run:  python3 tests/test_semantic_repairs.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
sys.path.insert(0, str(W / "_diagnostics" / "workbench_v2"))
sys.path.insert(0, str(W / "_diagnostics" / "semantic_pilot_9papers" / "code"))

from pipeline.canonical import axis_semantics as AX             # noqa: E402
from pipeline.canonical import conditions as COND               # noqa: E402
from pipeline.canonical import process_steps as PS              # noqa: E402
from pipeline.query import condition_query as CQ                # noqa: E402
from pipeline.query import result_comparability as RC           # noqa: E402
import build_workbench_model as WBM                             # noqa: E402

WB = W / "_diagnostics" / "workbench_v2"
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def _series_stub(x_vals, y_vals, x_meta, y_meta):
    pts = [{"x": a, "y": b} for a, b in zip(x_vals, y_vals)]
    return {"series_id": "S1", "native_points": {"points": pts,
                                                 "x": dict(x_meta, values=list(x_vals)),
                                                 "y": dict(y_meta, values=list(y_vals))}}


def main():
    M = json.loads((WB / "workbench_model.json").read_text())
    SER, CASES, PAIRS = M["series"], M["cases"], M["pairs"]

    print("=== A. axis reachability is per axis, never gated on the other ===")
    # Synthetic: a resolved, normalised x whose y never canonicalised. The canonical
    # record has NO paired points, an x projection on disk, and a y with no quantity.
    cur = {"points": [], "x_quantity": "dimensionless_distance", "x_unit": "1",
           "x_norm": "x_over_feature_height", "y_quantity": None, "y_unit": None,
           "y_norm": None, "y_resolution": "PARTIALLY_RESOLVED",
           "x_values": [0.1, 0.5, 0.9], "y_values": [],
           "projections": {"x": [{"quantity": "spatial_coordinate", "unit": "µm",
                                  "values": [0.05, 0.25, 0.45],
                                  "from_normalization": "x_over_feature_height"}]},
           "transformations": []}
    s = _series_stub([0.1, 0.5, 0.9], [1.0, 0.9, 0.2],
                     {"quantity": "dimensionless_distance", "unit": "1",
                      "label": "x/H"},
                     {"quantity": None, "unit": None, "label": "mystery"})
    xr, yr = WBM.derived_representations(s, cur)
    ok("A: the resolved x still materialises its canonical native",
       "native" in xr and xr["native"]["values"], sorted(xr))
    ok("A: the x projection the canonical layer computed is offered",
       "proj:spatial_coordinate" in xr
       and xr["proj:spatial_coordinate"]["values"] == [0.05, 0.25, 0.45], sorted(xr))
    ok("A: the unresolved y stays honestly absent",
       "native" not in yr and "native_source" in yr, sorted(yr))

    # ... and the mirror: resolved y, unresolved x
    cur2 = {"points": [], "y_quantity": "film_thickness", "y_unit": "nm",
            "y_norm": None, "x_quantity": None, "x_unit": None, "x_norm": None,
            "y_resolution": "FULLY_RESOLVED", "x_values": [], "y_values": [10., 20.],
            "projections": {"y": [{"quantity": "growth_per_cycle", "unit": "nm/cycle",
                                   "values": [0.1, 0.2],
                                   "from_normalization": None}]},
            "transformations": []}
    s2 = _series_stub([1.0, 2.0], [10.0, 20.0],
                      {"quantity": None, "unit": None, "label": "?"},
                      {"quantity": "film_thickness", "unit": "nm", "label": "t"})
    xr2, yr2 = WBM.derived_representations(s2, cur2)
    ok("A: a y transform survives an unresolved x",
       "native" in yr2 and "proj:growth_per_cycle" in yr2, sorted(yr2))
    ok("A: the unresolved x stays honestly absent",
       "native" not in xr2, sorted(xr2))

    # Live corpus: no series with declared+resolvable x transforms lost them to y
    starved = []
    for sid, sr in SER.items():
        if sr["y_resolution"] == "FULLY_RESOLVED":
            continue
        xn = sr["x_representations"].get("native")
        if not xn or not xn.get("values") or not xn.get("normalization"):
            continue
        has_transform = any(r.get("available") and r.get("transform")
                            for r in sr["x_representations"].values())
        declared = [t for t in RC.TRANSFORMS
                    if t.get("op") == "divide" and t.get("to") == xn["quantity"]]
        if declared and not has_transform:
            bc = WBM.bridge_case(sr, CASES)
            if bc and any(RC.resolve_context(t["bridge"], case=bc).get("found")
                          for t in declared):
                starved.append(sid)
    ok("A: corpus-wide, no resolvable x transform is lost to an unresolved y",
       not starved, starved[:3])

    print("=== B. same-measurement alternates: reachable, and a distinct relation ===")
    with_alt = [s for s in SER.values() if s.get("same_measurement_series")]
    ok("B: alternates exist wherever an act has several series",
       all(len(a.get("series_ids") or []) < 2
           or all(SER[x].get("same_measurement_series")
                  for x in a["series_ids"] if x in SER)
           for a in M["acts"].values()))
    ok("B: every alternate names the relation and the caveat",
       all(x["relation"] == WBM.SAME_MEASUREMENT_REPRESENTATION
           and x.get("independently_digitized") is True and x.get("caveat")
           for s in with_alt for x in s["same_measurement_series"]))
    ok("B: the relation vocabulary separates it from a derived transform",
       WBM.SAME_MEASUREMENT_REPRESENTATION != WBM.DERIVED_TRANSFORM)
    ok("B: no derived representation claims to BE the sibling series",
       all((r.get("transform") or {}).get("kind") != WBM.SAME_MEASUREMENT_REPRESENTATION
           for s in SER.values() for ax in ("x_representations", "y_representations")
           for r in s[ax].values()))
    ok("B: alternates carry the act's own grouping evidence",
       all(x.get("basis") for s in with_alt for x in s["same_measurement_series"]))
    # alternates never imply overlay permission by themselves
    viol = 0
    for s in with_alt:
        for x in s["same_measurement_series"]:
            p = (PAIRS.get("%s|%s" % (s["id"], x["series_id"]))
                 or PAIRS.get("%s|%s" % (x["series_id"], s["id"])))
            if p and p["status"] not in ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE") \
                    and p.get("physical_overlay_allowed"):
                viol += 1
    ok("B: same measurement never implies a shared physical axis", viol == 0, viol)

    print("=== C. document-defined named representations ===")
    cands = {n: d for n, d in RC.NORMALIZATIONS.items()
             if str(n).startswith("t_over")}
    doc = ("Thickness profiles are reported in two normalisations. "
           "Alpha profiles are obtained by normalizing the thickness to the value at "
           "the channel entrance. "
           "Beta profiles are obtained by normalizing the thickness to the maximum "
           "thickness along the channel.")
    defs = AX.named_normalization_definitions(doc, cands, axis="y")
    ok("C: the document's own definitions are captured, one id per name",
       {k: v["id"] for k, v in defs.items()} ==
       {"alpha": "t_over_t_entrance", "beta": "t_over_t_max"}, defs)
    nid, ev = AX.normalization_from_named_use("Alpha normalized thickness profiles.",
                                              defs)
    ok("C: a caption using the name binds to the definition",
       nid == "t_over_t_entrance" and ev and "Alpha" in ev, (nid, ev))
    ok("C: a caption using two defined names identifies nothing",
       AX.normalization_from_named_use("Alpha and Beta compared.", defs)[0] is None)
    ok("C: a name the document never defined resolves nothing",
       AX.normalization_from_named_use("Gamma profiles.", defs)[0] is None)
    ok("C: with no document definition, nothing binds",
       AX.normalization_from_named_use("Alpha profiles.", {})[0] is None)
    ok("C: a non-discriminating 'name' is refused",
       "normalized thickness" not in AX.named_normalization_definitions(
           "Normalized thickness is defined as thickness normalized to a reference.",
           cands, axis="y"))
    # evidence quotes both halves
    ok("C: the binding quotes definition and use",
       "definition" in (ev or ""), ev)

    print("=== D. one authority for overlay, comparability and missing context ===")
    def reach(sid, ax):
        return {r["target_id"]: r for r in SER[sid][ax + "_representations"].values()
                if r.get("available") and r.get("values") and r.get("target_id")
                and r.get("overlay_authorized") is not False}
    def semk(r):
        return (r.get("quantity_id"), r.get("normalization_id"), r.get("dimension"),
                r.get("unit"), r.get("axis"))
    OKL = ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")
    n_mismatch = n_used_missing = n_reach_missing = 0
    for key, p in PAIRS.items():
        a, b = key.split("|")
        reachable = all(
            any(t in reach(b, ax) and semk(reach(a, ax)[t]) == semk(reach(b, ax)[t])
                for t in reach(a, ax)) for ax in ("x", "y"))
        if p["physical_overlay_allowed"] != (p["status"] in OKL and reachable):
            n_mismatch += 1
        used = {r for ax in ("x", "y")
                for t in (p.get("overlay_targets") or {}).get(ax) or []
                for r in [(t.get("a_route") or {}).get("bridge"),
                          (t.get("b_route") or {}).get("bridge")] if r}
        if used & set(p.get("missing") or []):
            n_used_missing += 1
        if p["status"] == "missing_context" and reachable:
            n_reach_missing += 1
    ok("D: overlay permission equals verdict + reachability, every pair",
       n_mismatch == 0, n_mismatch)
    ok("D: no pair claims missing a bridge its own overlay routes use",
       n_used_missing == 0, n_used_missing)
    ok("D: no missing-context pair is actually reachable", n_reach_missing == 0,
       n_reach_missing)
    ok("D: every pair names its authority",
       all(p.get("verdict_authority") for p in PAIRS.values()))
    promoted = [p for p in PAIRS.items()
                if "VIA_REPRESENTATION" in (p[1].get("x_status") or "")
                or "VIA_REPRESENTATION" in (p[1].get("y_status") or "")]
    ok("D: promoted pairs carry per-side context provenance",
       all(p.get("context_provenance") for _, p in promoted)
       and (not promoted or all(
           s.get("source_object") for _, p in promoted
           for q in p["context_provenance"] for s in q["sources"])),
       len(promoted))

    print("=== E. role-aware timing specialisation, without family rewrites ===")
    ok("E: pulse and exposure are different canonical kinds",
       PS.canonical_timing_quantity("pulse_time") == "pulse_time"
       and PS.canonical_timing_quantity("exposure_time") == "exposure_time")
    ok("E: both time the same SIDE of the cycle",
       PS.timing_side("pulse_time") == PS.timing_side("exposure_time")
       == PS.EXPOSURE_SIDE
       and PS.timing_side("precursor_pulse_time") == PS.EXPOSURE_SIDE)
    ok("E: role evidence specialises without changing family",
       PS.specialize_timing_quantity("pulse_time", PS.PRECURSOR_EXPOSURE)
       == "precursor_pulse_time"
       and PS.specialize_timing_quantity("pulse_time", PS.REACTANT_EXPOSURE)
       == "coreactant_pulse_time"
       and PS.specialize_timing_quantity("purge_time", PS.REACTANT_PURGE)
       == "coreactant_purge_time")
    ok("E: no role evidence, no specialisation",
       PS.specialize_timing_quantity("pulse_time") == "pulse_time")
    ok("E: label wording types the family; dose types neither family",
       PS.timing_family_from_label("TMA dose time") == PS.DOSE_TIME
       and PS.timing_family_from_label("O2 exposure time") == "exposure_time"
       and PS.timing_family_from_label("soak duration") == "exposure_time")
    # a series label on a dose axis with a resolved precursor step: role specialises,
    # the dose kind survives, and no pulse or exposure family is invented
    conds = COND.from_series_label("0.4 s", "TMA dose time")
    tc = [c for c in conds if PS.timing_side(c.get("quantity"))]
    ok("E: a swept dose with species evidence lands role-specialised, kind kept",
       tc and tc[0]["quantity"] == "precursor_dose_time"
       and tc[0]["species"] == "TMA"
       and tc[0]["step_context"] == PS.PRECURSOR_EXPOSURE, tc)
    ok("E: the source's own word is preserved beside it",
       tc and tc[0].get("source_quantity") == "dose_time", tc)
    # ... and a pulse-worded axis still lands in the pulse family when its step resolves
    pconds = COND.from_series_label("0.4 s", "precursor pulse time")
    ptc = [c for c in pconds if PS.timing_side(c.get("quantity"))]
    ok("E: a pulse-worded axis with role evidence specialises within the pulse family",
       ptc and ptc[0]["quantity"] == "precursor_pulse_time", ptc)
    ok("E: no exposure_time was created from a pulse statement",
       all(PS.timing_kind(c["quantity"]) != "exposure_time" for c in tc), tc)
    # corpus audit: every exposure-KIND condition traces to exposure wording or an
    # upstream exposure-named source, never to a pulse source_quantity
    bad = [(c["paper_id"], x.get("quantity"), x.get("source_quantity"))
           for c in CASES.values() for x in c["conditions"]
           if PS.timing_kind(x.get("quantity")) == "exposure_time"
           and PS.timing_kind(x.get("source_quantity")) == "pulse_time"]
    ok("E: corpus-wide, no exposure_time condition was minted from a pulse source",
       not bad, bad[:3])
    print("=== E2. dose commits to neither family; unresolved stays unresolved ===")
    ok("E2: dose is its own kind, not pulse and not exposure",
       PS.timing_kind("dose_time") == PS.DOSE_TIME
       and PS.DOSE_TIME not in (PS.PULSE_TIME, PS.EXPOSURE_TIME))
    ok("E2: a dose-kind quantity resolves NO family",
       PS.timing_family_resolved("dose_time") is None
       and PS.timing_family_resolved("precursor_dose_time") is None)
    ok("E2: dose wording in a label names the dose kind, never a family",
       PS.timing_family_from_label("TMA dose time") == PS.DOSE_TIME
       and PS.timing_family_from_label("dosing duration") == PS.DOSE_TIME)
    ok("E2: pulse and exposure wording keep their resolved families",
       PS.timing_family_resolved(PS.timing_family_from_label("pulse length"))
       == PS.PULSE_TIME
       and PS.timing_family_resolved(PS.timing_family_from_label("soak time"))
       == PS.EXPOSURE_TIME)
    dose_conds = COND.from_series_label("0.4 s", "TMA dose time")
    dtc = [c for c in dose_conds if PS.timing_side(c.get("quantity"))]
    ok("E2: a dose axis specialises by role but keeps the dose kind",
       dtc and dtc[0]["quantity"] == "precursor_dose_time"
       and PS.timing_family_resolved(dtc[0]["quantity"]) is None, dtc)
    ok("E2: still one contact-side slot for dedup purposes",
       PS.timing_side("precursor_dose_time") == PS.EXPOSURE_SIDE)

    print("=== E3. point-case timing identity: family-strict, side only as last "
          "unambiguous resort ===")
    mkc = lambda q, sp, step: {"quantity": q, "species": sp, "step_context": step,
                               "value": 0.4, "unit": "s"}
    pp = mkc("precursor_pulse_time", "X1", PS.PRECURSOR_EXPOSURE)
    pe = mkc("precursor_exposure_time", "X1", PS.PRECURSOR_EXPOSURE)
    both = [pp, pe]
    # resolved family on both sides: match only on equality
    ok("E3: a pulse axis matches the pulse condition, family to family",
       WBM._timing_identity_basis(pp, "pulse_time", PS.PULSE_TIME, both, None, None)
       == "timing family identity")
    ok("E3: a pulse axis REFUSES the exposure condition on the same precursor side",
       WBM._timing_identity_basis(pe, "pulse_time", PS.PULSE_TIME, both, None, None)
       is None)
    ok("E3: an exposure axis refuses the pulse condition symmetrically",
       WBM._timing_identity_basis(pp, "exposure_time", PS.EXPOSURE_TIME, both,
                                  None, None) is None)
    # unresolved axis family + BOTH kinds present on one side: ambiguous, refuse both
    ok("E3: with the family unresolved and pulse+exposure coexisting on the side, "
       "neither is matched",
       WBM._timing_identity_basis(pp, "pulse_time", None, both, None, None) is None
       and WBM._timing_identity_basis(pe, "pulse_time", None, both, None, None) is None)
    # unresolved axis family + exactly one kind: unambiguous side identification
    ok("E3: with one candidate kind the side identification is accepted and NAMED",
       "cycle-side identity" in (WBM._timing_identity_basis(
           pe, "pulse_time", None, [pe], None, None) or ""))
    ok("E3: a purge condition never matches a contact-side axis",
       WBM._timing_identity_basis(
           mkc("precursor_purge_time", "X1", PS.PRECURSOR_PURGE),
           "pulse_time", None, [pe], None, None) is None)
    # the axis family authority: printed label first, contested -> unresolved
    ok("E3: label and quantity agreeing resolve the axis family",
       WBM.axis_timing_family("pulse_time", "X1 pulse time (s)") == PS.PULSE_TIME)
    ok("E3: a dose-worded label leaves the axis family unresolved",
       WBM.axis_timing_family("pulse_time", "Dose time (ms)") is None)
    ok("E3: label/quantity family contradiction leaves the axis contested",
       WBM.axis_timing_family("pulse_time", "Exposure time (s)") is None)
    ok("E3: a label naming no timing kind lets the quantity speak",
       WBM.axis_timing_family("pulse_time", "time (s)") == PS.PULSE_TIME)
    ok("E3: every corpus side-fallback resolution is recorded with its basis",
       all(l.get("identity_basis")
           for rec in M["point_case_links"].values()
           for l in rec.get("links") or []
           if l.get("resolution_status") == "RESOLVED"))

    # an extracted timing quantity that contradicts its own printed label is SURFACED
    # verbatim, never silently renamed: the record stays what extraction asserted, the
    # disagreement is on the series, and binding does not depend on the family choice
    disc = [(sid, d) for sid, sr in SER.items()
            for d in sr.get("axis_family_discrepancies") or []]
    ok("E: label-vs-quantity family disagreements are surfaced with both spellings",
       all(d.get("recorded_quantity") and d.get("label_family")
           and d.get("label") for _, d in disc), disc[:2])
    ok("E: the surfaced record keeps the extracted quantity untouched",
       all(SER[sid]["x_representations"].get("native_source", {}).get("quantity")
           == d["recorded_quantity"]
           for sid, d in disc if d["axis"] == "x"), disc[:2])

    print("=== F. one physical timing slot, one case dimension ===")
    dup = []
    for cid, c in CASES.items():
        slots = defaultdict(list)
        for x in c["conditions"]:
            if x.get("same_slot_conflict"):
                continue
            sl = PS.timing_slot(x.get("quantity"), x.get("step_context"),
                                x.get("species"))
            if sl:
                slots[sl].append(x["quantity"])
        dup += [(cid, sl, qs) for sl, qs in slots.items() if len(qs) > 1]
    ok("F: no case carries two condition dimensions for one timing slot",
       not dup, dup[:3])
    ok("F: queries by the bare name still reach the specialised spelling",
       CQ.timing_quantity_matches("precursor_pulse_time", "pulse_time")
       and CQ.timing_quantity_matches("coreactant_pulse_time", "pulse_time"))
    ok("F: but a role-qualified question is never widened",
       not CQ.timing_quantity_matches("coreactant_pulse_time",
                                      "precursor_pulse_time")
       and not CQ.timing_quantity_matches("pulse_time", "precursor_pulse_time"))
    ok("F: and pulse never answers an exposure question",
       not CQ.timing_quantity_matches("precursor_pulse_time", "exposure_time"))

    print("=== G. known context vs case-defining condition; scope safety ===")
    gaps = [(cid, role) for cid, c in CASES.items()
            for role in ("precursor", "coreactant")
            if (c.get("chemistry") or {}).get(role)
            and not (c.get("resolved_facts") or {}).get(role)]
    ok("G: resolved chemistry always reaches the case facts view", not gaps, gaps[:3])
    ok("G: facts distinguish case-defining from known context",
       all(e.get("fact_role") in (WBM.FACT_CASE_DEFINING, WBM.FACT_KNOWN_CONTEXT)
           for c in CASES.values() for arr in (c.get("resolved_facts") or {}).values()
           for e in arr))
    ok("G: every known-context fact carries a basis",
       all(e.get("basis")
           for c in CASES.values() for arr in (c.get("resolved_facts") or {}).values()
           for e in arr if e.get("fact_role") == WBM.FACT_KNOWN_CONTEXT))
    # scope safety: a case's chemistry facts must equal ITS OWN resolved chemistry --
    # never the union of the paper's. Quantified over every multi-chemistry paper.
    by_paper = defaultdict(list)
    for c in CASES.values():
        by_paper[c["paper_id"]].append(c)
    multi = leaks = 0
    for pid, cs in by_paper.items():
        prece = {p for c in cs for p in (c.get("chemistry") or {}).get("precursor", [])}
        if len(prece) < 2:
            continue
        multi += 1
        for c in cs:
            own = set((c.get("chemistry") or {}).get("precursor", []))
            facts = {e["value"] for e in (c.get("resolved_facts") or {}).get(
                "precursor", []) if e.get("fact_role") == WBM.FACT_KNOWN_CONTEXT}
            if not facts <= own:
                leaks += 1
    ok("G: the corpus exercises the multi-chemistry situation", multi > 0, multi)
    ok("G: no case's facts carry another process's chemistry", leaks == 0, leaks)
    # the facts view never overrides a recorded condition
    ok("G: a recorded condition is never restated by context in the same fact list",
       all(not (any(e["fact_role"] == WBM.FACT_CASE_DEFINING for e in arr)
                and any(e["fact_role"] == WBM.FACT_KNOWN_CONTEXT
                        and e.get("provenance_type") == "resolved_chemistry"
                        for e in arr)
                and fid not in ("precursor", "coreactant"))
           for c in CASES.values()
           for fid, arr in (c.get("resolved_facts") or {}).items()))

    print("=== H. specimen identity is not Condition Case identity ===")
    import pilot_cases as PCA
    import pilot_ranges as PRG
    import pilot_semantics as PSEM
    from pilot_supplements import DEPOSITION_HINTS

    def cand(cid, mat, conds, fig="1", pan="a"):
        return {"candidate_id": cid, "deposited_material": mat,
                "case_conditions": conds, "source_figure": fig, "source_panel": pan}
    T = lambda v: {"quantity": "deposition_temperature", "value": v, "unit": "°C"}
    same = [{"a": "A", "b": "B", "strength": PCA.EXPLICIT,
             "evidence": "the same sample"}]
    # same_sample alone never merges different deposition targets
    groups, dec = PCA.resolve_cases(
        [cand("A", "SiO2", [T("200")]), cand("B", "Al2O3", [T("200")], pan="b")], same)
    ok("H: same-sample link between different target materials is BLOCKED",
       ["A"] in groups and ["B"] in groups
       and any(d["action"] == "BLOCKED"
               and d["reason"] == "different deposition target materials"
               for d in dec), dec)
    # ... which is exactly one specimen linked to TWO Condition Cases
    ok("H: one specimen may realise several Condition Cases", len(groups) == 2, groups)
    # a member with no target of its own (multilayer image) blocks nothing
    groups2, dec2 = PCA.resolve_cases(
        [cand("A", "SiO2", [T("200")]), cand("B", None, [T("200")], fig="2")], same)
    ok("H: multi-material scope evidence (no single target) does not block the merge",
       sorted(map(sorted, groups2)) == [["A", "B"]], (groups2, dec2))
    # material identity is chemical, not spelling
    groups3, _ = PCA.resolve_cases(
        [cand("A", "SiO2", [T("200")]), cand("B", "SiO 2", [T("200")], pan="b")], same)
    ok("H: material identity is compared chemically, not by spelling",
       sorted(map(sorted, groups3)) == [["A", "B"]], groups3)

    print("=== H2. target material vs specimen composition ===")
    # corpus-wide: no case whose members resolve a single target material is
    # multi-material merely because a linked scope names more layers
    viol = []
    for cid, c in CASES.items():
        ctx = c.get("specimen_context_materials") or []
        if ctx and not c.get("material"):
            viol.append(cid)
    ok("H2: specimen context never leaves the case target unresolved", not viol,
       viol[:3])
    ok("H2: specimen context is separated from the target, with role and basis",
       all(x.get("material") and x.get("role") and x.get("basis")
           for c in CASES.values() for x in c.get("specimen_context_materials") or []))
    ok("H2: a specimen-context material never enters the material facet",
       all(c["id"] not in set((M["facets"].get("material") or {}).get(x["material"])
                              or [])
           for c in CASES.values() for x in c.get("specimen_context_materials") or []
           if x["material"] != c.get("material")))
    ok("H2: specimen composition is queryable as specimen_material facts",
       all(any(e.get("provenance_type") == "specimen_context"
               for e in (c.get("resolved_facts") or {}).get("specimen_material") or [])
           for c in CASES.values() if c.get("specimen_context_materials")))

    print("=== H3. quantity-local numeric parsing ===")
    got = {c["quantity"]: c for c in PRG.quantities_from_text(
        "layers deposited using 10-40 cycles each. The substrate temperature was "
        "200 \u00b0 C.", DEPOSITION_HINTS)}
    ok("H3: the cycle expression reads ITS OWN range, never a later number",
       got.get("cycle_number", {}).get("value_kind") == "range"
       and got["cycle_number"]["value_lower"] == 10.0
       and got["cycle_number"]["value_upper"] == 40.0, got.get("cycle_number"))
    ok("H3: the temperature is parsed independently",
       got.get("deposition_temperature", {}).get("value") == 200.0,
       got.get("deposition_temperature"))
    ok("H3: scalar, approximate and head-positioned forms survive",
       PRG.quantities_from_text("coated by 830 cycles", DEPOSITION_HINTS)[0]["value"]
       == 830.0
       and PRG.quantities_from_text("an aspect ratio of ~30",
                                    DEPOSITION_HINTS)[0]["value"] == 30.0)
    ok("H3: a number beyond a sentence boundary is never consumed",
       not [c for c in PRG.quantities_from_text(
            "films were deposited by ALD cycles. The pressure was 3 Torr at 250 "
            "\u00b0 C.", [(PSEM.re.compile(r"\bcycles\b"), "cycle_number", "cycle")])
            if c["quantity"] == "cycle_number"])

    print("=== H4. panel-scope discipline ===")
    ok("H4: an enumerating clause binds no single value to its panel",
       PSEM.enumerated_settings(
           "Substrate temperatures of 50 \u25e6 C, 200 \u25e6 C and 250 \u25e6 C.")
       and PSEM.enumerated_settings("at 100 and 300 C"))
    # The binding is proven two ways. Mechanically: a prose-typed single-value clause
    # yields the specifically-typed condition (never the unit-generic reading).
    _pc = PSEM.C.conditions_from_prose(
        "Thickness extracted from the image, measured on the same films. The "
        "substrate temperature was 175 \u00b0C.", "panel", "caption", "t")
    ok("H4: a panel clause's own statement binds with its governing-phrase type",
       [(x["quantity"], x["value"]) for x in _pc]
       == [("deposition_temperature", "175")], _pc)
    # And in the persisted record: a merge licensed by a panel-clause statement is
    # corroborated by agreeing conditions the clause itself supplied -- the evidence
    # chain runs panel clause -> panel candidates -> merge, never through a leak.
    import glob as _glob
    clause_merges = [r for f in _glob.glob(str(
        W / "_diagnostics" / "semantic_pilot_9papers" / "papers" / "*" / "semantic"
        / "links.json"))
        for r in json.loads(Path(f).read_text())
        if r.get("action") == "MERGED" and "caption clause" in str(r.get("reason"))]
    ok("H4: panel-clause statements license merges in the corpus", clause_merges,
       len(clause_merges))
    ok("H4: every such merge is corroborated by an agreeing condition, none clashes",
       all((r["detail"].get("agree") and not r["detail"].get("clash"))
           for r in clause_merges),
       [(r["a"], r["b"], r["detail"]) for r in clause_merges][:1])
    # any panel-bound condition that survives case assembly names its own panel
    pcd = [(cid, x) for cid, c in CASES.items() for x in c["conditions"]
           if x.get("provenance_type") == "panel_caption_direct"]
    ok("H4: surviving panel-clause conditions carry their panel locator",
       all(("caption clause of panel" in str(x.get("locator") or ""))
           for _, x in pcd), (len(pcd), pcd[:1]))
    # no ResultSeries or points lost, no case identities invented or destroyed
    ok("H4: 231 ResultSeries and 182 Condition Cases, none lost or invented",
       len(SER) == 231 and len(CASES) == 182, (len(SER), len(CASES)))
    ok("H4: every series keeps its native points",
       all((s.get("native_points") or {}).get("points") or s["n_points"] in (0, None)
           for s in SER.values()))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
