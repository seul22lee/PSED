#!/usr/bin/env python3
"""Focused tests for the twin's semantic-backed evidence retrieval (M2/M3).

  A. The evidence interface reads ONLY the declared corpus: no review paper
     appears anywhere, and membership never comes from globbing.
  B. Chemistry is canonical everywhere: record chemistry lists and condition
     species are chemical identities, never alias spellings; unresolved
     chemicals stay distinct.
  C. Reactant slots (A/B) are assigned by chemical identity against the case's
     own chemistry; a foreign or unresolved species is never reinterpreted.
  D. Condition values arrive in the ontology's canonical unit for their
     quantity, or are withheld with the reason recorded.
  E. M3 candidates: experimental only, one representation per MeasurementAct,
     resolved single-case linkage, >= 6 canonical points, full funnel accounting.
  F. M2 chemistry-scoped priors resolve against the semantic corpus with
     paper-level provenance, and pool nothing across chemistries.

Run:  python3 tests/test_twin_semantic_evidence.py
"""
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

import paths as P                                               # noqa: E402
from pipeline.canonical import chemical_identity as CI          # noqa: E402
from twin import semantic_evidence as SE                        # noqa: E402
from twin import m2_chemistry as chem                           # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    import json
    mf = json.loads(P.corpus_manifest_path().read_text())
    included = {x["paper_id"] for x in mf["included"]}
    reviews = {x["paper_id"] for x in mf["excluded"]}
    recs = SE.case_records()
    cands, funnel, excl = SE.profile_candidates()

    print("=== A. declared corpus only ===")
    pids = {r["_pid"] for r in recs}
    ok("A: every evidence record is from an included paper", pids <= included,
       sorted(pids - included))
    ok("A: no review paper contributes any record", not (pids & reviews))
    ok("A: no review paper contributes any M3 candidate",
       not ({c["_pid"] for c in cands} & reviews))
    ok("A: the corpus meta names the manifest and the workbench build",
       SE.corpus_meta()["manifest"].endswith("corpus_manifest.json")
       and SE.corpus_meta()["workbench_head_sha"])

    print("=== B. canonical chemistry ===")
    def canon(x):
        return CI.preferred_label(x) or x
    bad_chem = [(r["exp_id"], x) for r in recs
                for x in r["precursors"] + r["coreactants"] if canon(x) != x]
    ok("B: record chemistry lists are canonical identities", not bad_chem,
       bad_chem[:3])
    bad_sp = [(r["exp_id"], c["species"]) for r in recs for c in r["controlled"]
              if c.get("species") and CI.resolve(c["species"]).get("resolved")
              and canon(c["species"]) != c["species"]]
    ok("B: condition species are canonical identities", not bad_sp, bad_sp[:3])

    print("=== C. slot assignment by chemical identity ===")
    pk = {CI.identity_key("TMA")}
    ck = {CI.identity_key("H2O")}
    ok("C: a precursor alias slots as A", SE._slot("AlMe3", None, pk, ck) == "A")
    ok("C: the co-reactant slots as B", SE._slot("H2O", None, pk, ck) == "B")
    ok("C: a carrier gas is NEVER a reactant slot",
       SE._slot("N2", None, pk, ck) is None)
    ok("C: an unresolved chemical is never reinterpreted",
       SE._slot("unobtainium", None, pk, ck) is None)
    ok("C: a role-prefixed quantity states its own slot",
       SE._slot(None, "precursor_pulse_time", pk, ck) == "A"
       and SE._slot(None, "coreactant_purge_time", pk, ck) == "B")

    print("=== D. canonical-unit contract ===")
    v, u, note = SE._canonical_value("feature_height", 0.5, "µm")
    ok("D: feature dimensions convert to the ontology canonical unit",
       v == 500.0 and u == "nm" and note, (v, u, note))
    v, u, note = SE._canonical_value("pulse_time", 0.1, "s")
    ok("D: an already-canonical value passes through unchanged",
       v == 0.1 and not note, (v, u))
    v, u, note = SE._canonical_value("working_pressure", 3, "widgets")
    ok("D: an unconvertible unit WITHHOLDS the value with the reason",
       v is None and "withheld" in str(note), (v, note))

    print("=== E. M3 candidate discipline ===")
    ok("E: every candidate is a measured (experimental) series",
       all(c["record_nature"] == "measured_profile" for c in cands))
    acts = [c["act_id"] for c in cands]
    ok("E: one representation per MeasurementAct — no duplicate counting",
       len(acts) == len(set(acts)))
    ok("E: sibling re-renderings are excluded WITH the act named",
       any(e["stage"] == "one_per_measurement_act" for e in excl))
    ok("E: every candidate has >= 6 canonical points and a resolved case",
       all(len(c["points"]) >= 6 and c.get("case_id") for c in cands))
    ok("E: the funnel is monotone and complete",
       funnel["semantic_result_series"] >= funnel["measured_series"]
       >= funnel["profile_compatible"] >= funnel["one_per_measurement_act"]
       >= funnel["resolved_single_case"] == len(cands), funnel)
    ok("E: no simulated series survives any stage past 'measured'",
       all("not experimental evidence" in e["reason"]
           for e in excl if e["stage"] == "measured_series"))
    ok("E: x/y representations are ontology targets",
       all(c["x_representation"]["target_id"].startswith("x|group:")
           and c["y_representation"]["target_id"].startswith("y|group:")
           for c in cands))

    print("=== F. chemistry-scoped priors on the semantic corpus ===")
    ctx_c, status, alts, _ = chem.resolve_chemistry(recs, "Al2O3",
                                                    precursor="TMA", co_reactant="H2O")
    pt = chem.scoped_condition_prior(recs, "precursor_pulse_time", "pulse_time", "A",
                                     "Al2O3", ctx_c.precursor_identity,
                                     ctx_c.co_reactant_identity)
    ok("F: an explicitly stated chemistry resolves", status == "fully_specified")
    ok("F: the species-slotted pulse prior resolves with paper provenance",
       pt.resolved and pt.n_records > 0 and len(pt.refs) > 0
       and pt.match_quality == "exact_chemistry", (pt.value, pt.n_records, pt.refs))
    ok("F: its supporting papers are included, never reviews",
       set(pt.refs) <= included and not (set(pt.refs) & reviews), pt.refs)
    for a in alts:
        ok("F: alternative '%s' cites no review" % a["label"],
           not (set(a["papers"]) & reviews), a["papers"])
    other = chem.scoped_condition_prior(recs, "precursor_pulse_time", "pulse_time", "A",
                                        "Al2O3", "TiCl4", "H2O")
    ok("F: a prior never pools across chemistries (wrong precursor -> no records)",
       other.n_records == 0, other.n_records)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
