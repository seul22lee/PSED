#!/usr/bin/env python3
"""Tests for the M3 discovery-support redesign (twin_validation.py).

M3 ORGANIZES and PROPOSES; it never concludes. These tests pin the governing
invariants of the frozen scientific contract:

  · every emitted claim carries a valid, machine-readable epistemic status, and
    no forbidden (finality / discovery / validation) token is ever emitted;
  · non-comparable pairings are refused as tests (never scored);
  · agreement is not truth; disagreement is not model failure; literature is not
    ground truth (measurement is a co-equal explanatory locus);
  · explanation sets stay plural and non-exclusive; interpretations carry the full
    bundle; missing uncertainty stays insufficient_evidence; missing calibration
    stays unresolved; preserved anomalies are not over-claimed;
  · inquiry proposals are suggestions, not findings.

  python3 test_twin_validation.py
"""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
from twin import twin_validation as tv

FAIL = []


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


def check(name, got, want):
    ok(name, got == want, f"got {got!r}, want {want!r}")


def _statuses(o, acc):
    if isinstance(o, dict):
        s = o.get("status")
        if isinstance(s, str):
            acc.add(s)
        for v in o.values():
            _statuses(v, acc)
    elif isinstance(o, list):
        for v in o:
            _statuses(v, acc)
    return acc


# One real run over the corpus (the analysis is deterministic).
A = tv.analyze()
F, COMPS, ADM = A["frame"], A["comparisons"], A["admissible"]
ENS, CLO, INQ = A["ensemble"], A["closure"], A["inquiry"]
DIAG = ENS["diagnosability"]

print("1) epistemic-status discipline: vocabulary is closed and forbidden-free")
ok("STATUS is a non-empty closed set", isinstance(tv.STATUS, tuple) and len(tv.STATUS) >= 15)
ok("FORBIDDEN and STATUS are disjoint", not (set(tv.STATUS) & set(tv.FORBIDDEN_STATUS)))
ok("six explanatory loci defined", len(tv.LOCI) == 6 and "measurement" in tv.LOCI
   and "extraction" in tv.LOCI and "model_structure" in tv.LOCI)
emitted = _statuses(A, set())
ok("every emitted status is in the vocabulary", emitted <= set(tv.STATUS), sorted(emitted - set(tv.STATUS)))
ok("NO forbidden status is ever emitted", not (emitted & set(tv.FORBIDDEN_STATUS)),
   sorted(emitted & set(tv.FORBIDDEN_STATUS)))

print("2) explicit framing + ensemble scoping + coverage")
ok("frame has the required fields",
   {"research_question", "is_default", "comparability_criteria", "coverage", "untested_regions"} <= set(F))
ok("default run is flagged is_default", F["is_default"] is True)
cov = F["coverage"]
ok("candidates counted", cov["n_candidates"] == len(COMPS), (cov["n_candidates"], len(COMPS)))
ok("geometry census present", "lateral_channel" in cov["by_geometry_class"])
ok("untested region names vertical_structure (model-valid, no candidate)",
   any(u["value"] == "vertical_structure" for u in F["untested_regions"]))
ok("untested items carry the untested_region status",
   all(u["status"] == "untested_region" for u in F["untested_regions"]))
ok("membership is NOT filtered by outcome (porous candidates are admitted then refused)",
   cov["by_geometry_class"].get("porous_material", 0) > 0)

print("3) refuse-first commensurability: non-comparable is NEVER scored")
noncmp = [c for c in COMPS if c["status"] == "non_comparable"]
ok("some pairings are refused (porous / plasma out of domain)", len(noncmp) > 0)
ok("refused pairings carry NO comparison score",
   all(c.get("r2") is None and c.get("quantitative_agreement_status") is None for c in noncmp))
ok("refused pairings yield a boundary open-question",
   all((c.get("boundary_question") or {}).get("status") == "open_question" for c in noncmp))
ok("refusal is attributed to the pairing/domain, not to model or experiment",
   all(any("out_of_domain" in r["code"] for r in c["commensurability"]["reasons"]) for c in noncmp))

print("4) provenance: observation is a fallible extraction, not ground truth")
c0 = ADM[0]
op = c0["observation_provenance"]
ok("observation provenance records the extractor (fallible)", "extractor" in op)
check("calibration provenance stays unresolved", op["calibration_status"], "unresolved")
check("measurement uncertainty stays unresolved", op["measurement_uncertainty"], "unresolved")

print("5) uncertainty-aware comparison: missing measurement σ -> insufficient_evidence")
ok("every admissible comparison withholds quantitative agreement",
   all(c["quantitative_agreement_status"] == "insufficient_evidence" for c in ADM))
ok("combined tolerance marks measurement σ unresolved (not fabricated)",
   all(c["combined_tolerance"]["measurement_sigma"] == "unresolved" for c in ADM))
ok("per-comparison severity is present and non-quantitative",
   all(c.get("severity") and c["severity"]["quantitative"] is False for c in ADM))

print("6) ensemble pattern + diagnosability (honest about single-source weakness)")
ok("diagnosability is weak on this single-source-dominated ensemble", DIAG["verdict"] == "weak", DIAG["verdict"])
ok("weak diagnosability yields explicit unresolved attributions", len(DIAG["unresolved_attributions"]) > 0)
ok("interpretation happens AFTER the barrier (only admissible carry interpretation)",
   all("interpretation" in c for c in ADM) and all("interpretation" not in c for c in noncmp))

print("7) scientific interpretation: full bundle, plural, non-exclusive, model not privileged")
challenges = CLO["challenges"]
ok("there are challenged interpretations", len(challenges) > 0)
BUNDLE = {"challenge_basis", "scope", "test_severity", "dependency_assumptions", "alternatives_remaining_open"}
ok("every challenged interpretation carries the full bundle",
   all(BUNDLE <= set(i) for i in challenges))
for i in CLO["supports"]:
    ok("every supported interpretation carries the full bundle",
       {"support_basis", "scope", "test_severity", "dependency_assumptions", "alternatives_remaining_open"} <= set(i))
# plurality across the six co-equal loci
c = ADM[[j for j, x in enumerate(ADM) if x.get("shape_fit") != "close"][0]]
loci = {e["locus"] for e in c["explanations"]}
ok("explanation space is plural (>= 4 loci)", len(loci) >= 4, sorted(loci))
ok("measurement AND extraction AND ontology are live loci (literature not ground truth)",
   {"measurement", "extraction", "ontology"} <= loci)
ok("model_structure is ONE locus among several — not the default suspect",
   "model_structure" in loci and len(loci) > 1)
ok("no explanation is marked selected/adopted (plural, non-exclusive)",
   all("selected" not in e and "chosen" not in e for e in c["explanations"]))

print("8) preserved anomalies are not over-claimed under weak diagnosability")
check("no preserved anomaly declared when diagnosability is weak", len(CLO["preserved_anomalies"]), 0)
ok("but the discrepancies remain visible as challenged", len(challenges) > 0)

print("9) evidence closure separates 'what was learned' from 'what to ask next'")
ok("closure statement present", CLO["closure_statement"].startswith("No additional interpretation"))
ok("closure does not contain inquiry proposals",
   "discriminating" not in CLO["closure_statement"].lower())
ok("closure enumerates the honest inventory",
   {"supports", "challenges", "unresolved", "non_comparable", "insufficient_evidence",
    "untested_regions", "load_bearing_assumptions", "live_explanations", "preserved_anomalies"} <= set(CLO))

print("10) inquiry: proposals with provenance, ranked, never findings")
ok("there are discriminating questions", len(INQ) > 0)
ok("every inquiry item is a question / evidence need (not a finding)",
   all(x["status"] in ("discriminating_question", "evidence_needed", "open_question") for x in INQ))
ok("every inquiry item is m3-generated provenance",
   all(x["provenance"] == "m3_generated_question" for x in INQ))
ok("every inquiry item names what it separates", all(x.get("separates") for x in INQ))
ok("ranking is a transparent heuristic that DISCLAIMS information-gain",
   all("transparent heuristic" in x["rank_basis"] and "NOT expected-information-gain" in x["rank_basis"]
       for x in INQ))
ok("inquiry is sorted by rank (descending)", [x["rank_score"] for x in INQ] == sorted((x["rank_score"] for x in INQ), reverse=True))

print("11) backward-compatible entry points")
rf = tv.run_framed()                      # one extra analysis; reuse it for both checks
ok("run_framed() returns {frame, comparisons, analysis}",
   {"frame", "comparisons", "analysis"} <= set(rf))
ok("comparisons is the per-comparison list", isinstance(rf["comparisons"], list))
ok("every comparison carries a status", all("status" in c for c in rf["comparisons"]))

print("12) the Interpretation Brief renders, neutral, no validation language")
with tempfile.TemporaryDirectory() as td:
    p = tv.render_brief(A, out_path=Path(td) / "brief.html")
    h = p.read_text()
ok("brief is non-trivial", len(h) > 5000, len(h))
ok("titled Interpretation Brief", "Interpretation Brief" in h)
ok("uses neutral 'prediction versus observation'", "prediction versus observation" in h)
for bad in ("versus reality", "vs reality", "validated", "validation against", "twin disagrees with reality"):
    ok(f"no validation-against-reality language: {bad!r}", bad.lower() not in h.lower())
for tok in (">proven<", ">refuted<", ">discovered<"):
    ok(f"no forbidden finality token rendered: {tok!r}", tok not in h)
for sect in ("What was compared", "What the evidence supports", "What the evidence challenges",
             "Load-bearing assumptions", "Unresolved, non-comparable, insufficient, untested",
             "Preserved anomalies", "Evidence closure", "Discriminating questions"):
    ok(f"brief has section: {sect!r}", sect in h)
ok("brief states the closure statement", "No additional interpretation may be extracted" in h)
ok("brief carries the disclaimer (organizes and proposes, never concludes)",
   "discovery-support brief, not a verdict" in h)
ok("pressure caveat is not corpus-wide", "in this processed corpus" in h and "NOT a claim that it is absent" in h)

print("13) inverse-fit correctness: dimensionality, bounds, exposure, c honesty, identifiability")
invs = [(r, r["_inverse_fit"]) for r in ADM if r.get("_inverse_fit")]
ok("there are calibration probes", len(invs) > 0)
# no inert parameter: active vars match dose_free; optimizer vector dimension == #active
ok("dose-extracted fits optimize ONLY c (1-D, no inert t_p)",
   all(f["active_variables"] == ["c"] for _, f in invs if not f["dose_free"]))
ok("dose-free fits optimize t_p AND c (2-D)",
   all(f["active_variables"] == ["t_p", "c"] for _, f in invs if f["dose_free"]))
ok("optimizer dimensionality equals the number of active variables",
   all(len(f["active_variables"]) == (2 if f["dose_free"] else 1) for _, f in invs))
# fixed vs active matches runtime behaviour
ok("t_p role is 'fixed' exactly when dose was extracted",
   all((f["variables"]["t_p"]["role"] == "fixed") == (not f["dose_free"]) for _, f in invs))
# explicit bounds present for every fitted variable
ok("every fitted variable has explicit lower & upper bounds",
   all(isinstance(f["variables"]["c"]["lower"], float) and isinstance(f["variables"]["c"]["upper"], float)
       and isinstance(f["variables"]["t_p"]["lower"], float) for _, f in invs))
ok("c bounds are the declared physical range", all(f["variables"]["c"]["lower"] == tv.C_BOUNDS[0]
   and f["variables"]["c"]["upper"] == tv.C_BOUNDS[1] for _, f in invs))
# boundary hits reported
ok("boundary status is reported for c (at_lower/at_upper/interior)",
   all(f["variables"]["c"]["bound_status"] in ("at_lower", "at_upper", "interior") for _, f in invs))
ok("boundary_limited flag is set and at least one fit is boundary-limited",
   any(f["boundary_limited"] for _, f in invs))
ok("a boundary-limited fit has a c or t_p bound_status at a bound",
   all((f["variables"]["c"]["bound_status"] in ("at_lower", "at_upper")
        or f["variables"]["t_p"]["bound_status"] in ("at_lower", "at_upper"))
       for _, f in invs if f["boundary_limited"]))
# exposure is DERIVED from pA and t_p (never independently fitted)
ok("exposure_fit == pA * t_p (derived, not independently fitted)",
   all(abs(f["exposure_fit"] - f["pA"]["value"] * f["variables"]["t_p"]["fitted"]) < 1e-6 * max(1.0, f["exposure_fit"])
       for _, f in invs))
ok("exposure note declares it derived, pA fixed", all("DERIVED" in f["exposure_note"]
   and "independently fitted" in f["exposure_note"] for _, f in invs))
# pA provenance retained
ok("pA provenance is retained on every fit",
   all(f["pA"]["provenance"] in ("extracted", "imputed", "model_default", "unresolved") for _, f in invs))
# displayed runtime trace equals actual model inputs (t_p and pA)
ok("model_input_trace exists per admissible comparison", all("model_input_trace" in r for r in ADM))
def _trace_val(r, attr):
    return next((x["value"] for x in r["model_input_trace"] if x["attr"] == attr), None)
ok("trace t_p equals the runtime t_p used for the prediction",
   all(abs(_trace_val(r, "t_p") - r["t_p"]) < 1e-12 for r in ADM))
ok("trace pA equals the inverse-fit fixed pA (same runtime object)",
   all(abs(_trace_val(r, "pA") - r["_inverse_fit"]["pA"]["value"]) < 1e-9 for r in ADM if r.get("_inverse_fit")))
ok("every model input has value, unit, provenance and source",
   all(all(k in row and row[k] is not None for k in ("value", "unit", "provenance", "source"))
       for r in ADM for row in r["model_input_trace"]))
# c honesty: never literature-reported; model-specific label + ontology status disclosed
ok("fitted c provenance is 'inverse_fitted', never literature-reported",
   all(f["variables"]["c"]["provenance_fitted"] == "inverse_fitted" for _, f in invs))
ok("c has NO canonical literature field (not equated with a canonical quantity)",
   all(f["variables"]["c"]["canonical"] is None for _, f in invs))
ok("c is labelled a model-specific lumped reaction coefficient",
   "model-specific lumped reaction coefficient" in tv.C_LABEL)
ok("c ontology mapping status is disclosed on every fit",
   all(f["variables"]["c"]["ontology_mapping_status"] == tv.C_ONTOLOGY_STATUS for _, f in invs))
check("c ontology mapping status is unresolved", tv.C_ONTOLOGY_STATUS, "unresolved")
# optimizer / objective disclosed
ok("optimizer, objective, residual, weighting disclosed on every fit",
   all(f["optimizer"] and f["objective"] and f["residual"] and f["weighting"] for _, f in invs))
ok("objective before/after and metrics before/after are reported",
   all(all(k in f for k in ("sse_before", "sse_after", "r2_warm", "r2_fit", "n_eval", "converged")) for _, f in invs))
# identifiability: never a unique estimate
ok("every fit carries a local identifiability classification",
   all(f["identifiability"]["class"] in
       ("narrow_isolated_optimum", "moderate_feasible_interval", "broad_feasible_region",
        "pulse_time_c_tradeoff_ridge", "unassessed") for _, f in invs))
ok("every fit uses the non-uniqueness label",
   all(f["identifiability"]["label"] == "feasible fitted parameterization, not a unique physical parameter estimate"
       for _, f in invs))
# run-level provenance summary
ips = A["input_provenance_summary"]
ok("run-level input provenance summary present",
   {"by_provenance", "fitted_variables", "boundary_limited_fits", "ridge_or_broad_fits"} <= set(ips))
ok("provenance summary counts model_default and literature_reported distinctly",
   "model_default" in ips["by_provenance"] and "literature_reported" in ips["by_provenance"])

print("14) the report exposes the computational trace and never mislabels fitted c")
hp = h                                     # reuse the Brief rendered in section 12 (expensive to render)
ok("report has the per-experiment model resolution trace", "Model Resolution Trace" in hp)
ok("report shows the calibration-probe setup with optimizer + objective",
   "Calibration-probe setup" in hp and "smooth log-sigmoid bounded transform" in hp)
ok("report shows exposure as derived, not independently fitted",
   "derived exposure = pA×t_p" in hp and "never independently fitted" in hp)
ok("report labels c as a model-specific lumped reaction coefficient",
   "model-specific lumped reaction coefficient c" in hp)
ok("report never presents fitted c as a literature sticking probability",
   "never a literature-reported sticking probability" in hp or "never a literature sticking probability" in hp)
ok("report carries the non-identifiability label",
   "feasible fitted parameterization, not a unique" in hp)
ok("report shows boundary-limited status", "boundary-limited" in hp.lower())
ok("report shows the run-level model-input provenance summary", "Model-input provenance summary" in hp)
ok("report shows readable input labels (not bare H/T/dose pills)",
   "pulse time" in hp and "gap height" in hp and "precursor pressure" in hp)

print("15) build_twin resolution transparency: trace, provenance vs outcome, precedence, conversions")
from twin import pressure_compat as pc
# capture-in-path: the trace lives on the twin object used to predict
tw, _notes, _prov = tv.build_twin(tv._targets()[0])
ok("build_twin attaches a resolution_trace", hasattr(tw, "resolution_trace") and len(tw.resolution_trace) > 0)
ATTRS = ("t_p", "T", "pA", "gpc", "H", "W", "c", "K", "da", "MA")
ok("every resolution value EXACTLY equals the runtime twin attribute",
   all(abs(r["value"] - getattr(tw, r["attr"])) < 1e-12 for r in tw.resolution_trace if r["attr"] in ATTRS))
ok("every resolution row has provenance AND outcome (distinct, both valid)",
   all(r["provenance"] in tv.PROVENANCE_CATEGORIES and r["outcome"] in tv.RESOLUTION_OUTCOMES
       for r in tw.resolution_trace))
ok("every row records a fallback chain, candidates field, and a selected value",
   all(("fallback_chain" in r and "candidates" in r and "selected" in r) for r in tw.resolution_trace))
# provenance category and resolution outcome are DISTINCT concepts
ok("model_default provenance <-> resolved_by_default outcome",
   all((r["provenance"] == "model_default") == (r["outcome"] == "resolved_by_default")
       for r in tw.resolution_trace if r["attr"] in ATTRS))
ok("an extracted value with a unit conversion is resolved_with_conversion (e.g. T °C->K)",
   any(r["attr"] == "T" and r["provenance"] == "extracted" and r["outcome"] == "resolved_with_conversion"
       and r["transform"] for r in tw.resolution_trace) or
   all(r["attr"] != "T" or r["provenance"] != "extracted" for r in tw.resolution_trace))
# defaults never labelled extracted; imputed never literature_reported
for r in ADM:
    for row in r["model_resolution_trace"]:
        if row["outcome"] == "resolved_by_default":
            ok(f"default not labelled extracted ({row['attr']})", row["provenance"] in ("model_default",))
        if row["provenance"] == "imputed":
            ok(f"imputed not labelled literature ({row['attr']})", row["outcome"] == "resolved_by_imputation")
# FROZEN precursor-pressure precedence preserved and displayed from the real logic
pA_rec = next(x for x in tw.resolution_trace if x["attr"] == "pA")
ok("pA fallback chain begins with the FROZEN precursor-pressure precedence",
   pA_rec["fallback_chain"][:len(pc.PRECURSOR_PRESSURE_QUANTITIES)] == list(pc.PRECURSOR_PRESSURE_QUANTITIES))
ok("pulse_time precedence encodes A>B>impute>default",
   "A-extracted" in next(x for x in tw.resolution_trace if x["attr"] == "t_p")["selection_rule"])
# a rejected forbidden-type pressure candidate is recorded somewhere in the corpus
any_rej = any(any(str(rej.get("reason", "")).startswith("rejected: forbidden")
                  for rej in next(x for x in r["model_resolution_trace"] if x["attr"] == "pA")["rejected"])
              for r in ADM)
ok("a forbidden-type pressure candidate is recorded as rejected (frozen precedence visible)", any_rej)
# run-level counts equal the sum of per-comparison trace rows
mrs = A["model_resolution_summary"]
ok("run-level total == sum of per-comparison resolution rows",
   mrs["total_resolved_instances"] == sum(len(r["model_resolution_trace"]) for r in ADM))
ok("run-level by_outcome sums to the total",
   sum(mrs["by_outcome"].values()) == mrs["total_resolved_instances"])
ok("run-level by_provenance sums to the total",
   sum(mrs["by_provenance"].values()) == mrs["total_resolved_instances"])
# coverage exhibit distinguishes ontology support and never claims literature absence
cov = A["evidence_coverage"]
ok("coverage lists every model-consumed parameter", len(cov) >= 8)
ok("coverage records ontology support status per parameter",
   all(p["ontology_support"] in ("ontology_supported", "not_represented_in_ontology",
       "model_specific_unresolved_mapping", "derived") for p in cov))
ok("c keeps model-specific unresolved ontology mapping in coverage",
   any(p["attr"] == "c" and p["ontology_support"] == "model_specific_unresolved_mapping" for p in cov))

print("16) the report exposes resolution transparency and never claims literature absence")
ok("report has the per-experiment Model Resolution Trace", "Model Resolution Trace" in hp)
ok("report has the run-level resolution outcome breakdown", "By resolution outcome" in hp)
ok("report has the Model Input Evidence Coverage exhibit", "Model Input Evidence Coverage" in hp)
ok("report shows readable provenance AND resolution outcome in tables",
   "resolved_by_default" in hp and "resolved_with_conversion" in hp)
ok("report shows the frozen forbidden-type pressure rejection", "rejected: forbidden type" in hp)
ok("report describes missing evidence as corpus-absence, NOT literature-absence",
   "no accepted canonical evidence in the current corpus" in hp)
for bad in ("does not report", "not reported in the literature"):
    ok(f"report avoids absence-from-literature wording: {bad!r}", bad.lower() not in hp.lower())
ok("report explicitly disavows a single confidence score", "not a confidence score" in hp)
ok("report does NOT introduce an aggregate model-confidence score",
   "model confidence:" not in hp.lower() and "confidence score:" not in hp.lower())
ok("report shows per-comparison model-input evidence composition", "Model-input evidence composition" in hp)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
