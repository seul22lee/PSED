#!/usr/bin/env python3
"""reextract_coverage.py — deterministic coverage + provenance diagnostics for the scoped
re-extraction. Reads the manifest, the per-call log, and the regenerated resolved KB for the
31 in-scope papers; writes 03_corpus/reextract_coverage.json and prints a summary.
No LLM, no network. Safe to re-run.
"""
import json
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT.parent / "02_extraction" / "output"
MANIFEST = ROOT / "extraction_manifest.json"
CALLLOG = ROOT / "extraction_calls.jsonl"
UNITS = ("scout", "figures", "geometry", "pressure", "card")


def main():
    man = json.loads(MANIFEST.read_text())
    papers = man["papers"]
    log = [json.loads(l) for l in CALLLOG.read_text().splitlines()] if CALLLOG.exists() else []

    # --- extraction-side coverage ---
    # NOTE on "attempts": the shim counts one attempt per model call keyed by (doi, unit).
    # For the single-call units (scout/geometry/pressure/card) attempts>1 is a genuine
    # in-module retry (e.g. scout's token-budget ladder). For `figures` the counter also
    # increments once per figure-GROUP call, so attempts there ≈ figure groups + per-group
    # retries — NOT a retry signal. We therefore report those separately.
    SINGLE = ("scout", "geometry", "pressure", "card")
    unit_status = {u: Counter() for u in UNITS}
    in_module_retries, failed_units, per_paper, figures_calls = [], [], {}, {}
    for sd, p in papers.items():
        st = {u: p["units"].get(u, {}).get("status", "absent") for u in UNITS}
        for u in UNITS:
            unit_status[u][st[u]] += 1
            a = p["units"].get(u, {}).get("attempts", 0)
            if u in SINGLE and a and a > 1:
                in_module_retries.append({"doi": sd, "unit": u, "attempts": a})
            if st[u] not in ("succeeded",):
                failed_units.append({"doi": sd, "unit": u, "status": st[u],
                                     "detail": p.get("validation", {}).get(u, "")})
        figures_calls[sd] = p["units"].get("figures", {}).get("calls", 0)
        per_paper[sd] = {"units": st, "calls": sum(p["units"].get(u, {}).get("calls", 0) for u in UNITS)}
    fully = [sd for sd in papers if all(
        papers[sd]["units"].get(u, {}).get("status") == "succeeded" for u in UNITS)]

    # true second-pass retries: units that FAILED in the run1 snapshot but succeeded finally
    second_pass = []
    run1 = ROOT / "extraction_manifest.run1.json"
    if run1.exists():
        r1 = json.loads(run1.read_text())["papers"]
        for sd, p in papers.items():
            for u in UNITS:
                was = r1.get(sd, {}).get("units", {}).get(u, {}).get("status")
                now = p["units"].get(u, {}).get("status")
                if was not in (None, "succeeded") and now == "succeeded":
                    second_pass.append({"doi": sd, "unit": u, "run1_status": was,
                                        "detail_run1": r1[sd].get("validation", {}).get(u, "")})

    # --- call-log accounting ---
    calls_by_unit = Counter(r["unit"] for r in log)
    http_bad = [r for r in log if r.get("http_status") not in (200, None)]
    non_json = [{"doi": r["doi"], "unit": r["unit"], "attempt": r["attempt"]}
                for r in log if r.get("response_is_json") is False]
    tok_in = sum((r.get("usage") or {}).get("in") or 0 for r in log)
    tok_out = sum((r.get("usage") or {}).get("out") or 0 for r in log)

    # --- KB-side coverage (regenerated resolved experiments) ---
    kb = {"papers_with_kb": 0, "experiments": 0, "analysis_ready": 0,
          "experimental": 0, "model": 0, "with_pressure_condition": 0,
          "materials": Counter(), "geometry_class": Counter()}
    for sd in papers:
        f = OUT / sd / "resolved" / "experiments.json"
        if not f.exists():
            continue
        exps = json.loads(f.read_text())
        kb["papers_with_kb"] += 1
        kb["experiments"] += len(exps)
        for e in exps:
            kb["analysis_ready"] += 1 if e.get("analysis_ready") else 0
            if e.get("relevance") == "experimental":
                kb["experimental"] += 1
            else:
                kb["model"] += 1
            if e.get("material"):
                kb["materials"][e["material"]] += 1
            if e.get("geometry_class"):
                kb["geometry_class"][e["geometry_class"]] += 1
            if any((c.get("source") == "pressure_extraction") or ("pressure" in str(c.get("quantity", "")))
                   for c in (e.get("controlled") or [])):
                kb["with_pressure_condition"] += 1
    kb["materials"] = dict(kb["materials"].most_common())
    kb["geometry_class"] = dict(kb["geometry_class"])

    out = {
        "scope_papers": len(papers),
        "fully_succeeded": len(fully),
        "not_fully_succeeded": [sd for sd in papers if sd not in fully],
        "unit_status": {u: dict(unit_status[u]) for u in UNITS},
        "calls_made_total": man.get("calls_made"),
        "calls_by_unit": dict(calls_by_unit),
        "in_module_retries": in_module_retries,
        "second_pass_retries": second_pass,
        "figures_calls_by_paper": figures_calls,
        "remaining_failed_units": failed_units,
        "http_non200": [{"doi": r["doi"], "unit": r["unit"], "status": r["http_status"]} for r in http_bad],
        "non_json_responses": non_json,
        "tokens": {"in": tok_in, "out": tok_out},
        "kb_coverage": kb,
    }
    (ROOT / "reextract_coverage.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("per_paper",)}, indent=1))
    print(f"\nwrote {ROOT/'reextract_coverage.json'}")
    return out


if __name__ == "__main__":
    main()
