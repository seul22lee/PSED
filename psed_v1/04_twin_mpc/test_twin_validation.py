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
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "02_extraction"))
import twin_validation as tv

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

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
