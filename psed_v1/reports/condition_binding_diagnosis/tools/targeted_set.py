#!/usr/bin/env python3
"""READ-ONLY. §C — targeted diagnostic set, kept OUT of the random-sample statistics."""
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = REPO / "02_extraction" / "output"
EX = REPO / "03_corpus" / "extracted"
BASE = KB / "_archive" / "resolved_pre_canonical"

LEGEND_TOK = re.compile(r"(?:^|[\s,(])(T|p|d|H|L|AR)\s*[=:]|"
                        r"\d[\d.]*\s*(°\s*C|K|Pa|hPa|kPa|Torr|mTorr|mbar|sccm|cycles?|"
                        r"ms|s|min|nm|µm|um|μm)\b|\b(dose|exposure)\b", re.I)
PRESSURE_Q = {"generic_pressure", "working_pressure", "total_pressure", "partial_pressure",
              "chamber_total_pressure", "precursor_partial_pressure",
              "co_reactant_partial_pressure", "reactant_A_partial_pressure",
              "reactant_B_partial_pressure", "carrier_gas_partial_pressure"}


def J(p, d=None):
    p = Path(p)
    try:
        return json.loads(p.read_text())
    except Exception:
        return d


def main():
    pop = J(OUT / "corpus_population_manifest.json")
    papers = sorted(pop["per_paper"])
    cases, triggers = [], []

    val = J(OUT / "validation.json") if (OUT / "validation.json").exists() else None
    canon_val = J(REPO / "reports" / "canonical" / "validation.json", {})

    # 1. profile_split + mixed_role warnings from the canonical validator
    for w in (canon_val.get("warnings") or []):
        if w["check"] in ("granularity.profile_split", "granularity.mixed_roles"):
            cases.append({"case_type": w["check"], "ref": w["where"], "detail": w["message"]})

    # 2. model/simulation records that became Experiments
    model_exp = defaultdict(int)
    for r in pop["records"]:
        if r["is_model_result"] or r["relevance"] == "model":
            model_exp[r["paper_id"]] += 1
            if len(cases) < 100000:
                cases.append({"case_type": "model_point_became_experiment",
                              "ref": r["record_id"], "detail": "relevance=%s is_model=%s kind=%s"
                              % (r["relevance"], r["is_model_result"], r["kind"])})

    # 3. 20 largest series
    allser = []
    for doi in papers:
        for s in (J(KB / doi / "resolved" / "series.json", []) or []):
            allser.append((s["n_experiments"], doi, s["series_id"], s["series_varies"],
                           s["provenance"].get("figure_number"), s["provenance"].get("panel")))
    allser.sort(reverse=True)
    for n, doi, sid, varies, fig, pan in allser[:20]:
        cases.append({"case_type": "largest_series", "ref": sid,
                      "detail": "%d experiments from one curve (varies=%s, F%s%s)"
                      % (n, varies, fig, pan or "")})

    # 4. 10 papers with the largest experiment-count increase
    growth = []
    for doi in papers:
        before = len(J(BASE / doi / "experiments.json", []) or [])
        after = pop["per_paper"][doi]["experiments"]
        growth.append((after - before, doi, before, after))
    growth.sort(reverse=True)
    for delta, doi, b, a in growth[:10]:
        cases.append({"case_type": "largest_experiment_growth", "ref": doi,
                      "detail": "%d -> %d (+%d)" % (b, a, delta)})

    # 5-8. per-record condition pathologies
    for doi in papers:
        exps = J(KB / doi / "resolved" / "experiments.json", []) or []
        doc = (EX / doi / "document.md")
        txt = doc.read_text(errors="replace") if doc.exists() else ""
        text_pressure = bool(re.search(r"\d[\d.]*\s*(mTorr|Torr|mbar|hPa|kPa|Pa)\b", txt))
        fd = J(EX / doi / "figure_data.json", {}) or {}
        cap_by_idx = {str(f.get("figure")): (f.get("caption") or "") for f in fd.get("figures", [])}
        panel_conds = {}
        for f in fd.get("figures", []):
            for p in f.get("panels", []) or []:
                panel_conds[(str(f.get("figure")), str(p.get("panel") or ""))] = p.get("conditions") or {}
        for e in exps:
            ctrl = e.get("controlled") or []
            prov = e.get("provenance") or {}
            key = (str(prov.get("fig_docling_index") or ""), str(prov.get("panel") or ""))
            usable_p = [c for c in ctrl if c.get("quantity") in PRESSURE_Q
                        and c.get("context_status") != "ambiguous"]
            if text_pressure and not usable_p:
                cases.append({"case_type": "pressure_in_source_not_in_output",
                              "ref": e["exp_id"],
                              "detail": "document.md states a pressure; record has none usable"})
            if e.get("context_conflicts"):
                cases.append({"case_type": "conflicting_context",
                              "ref": e["exp_id"],
                              "detail": json.dumps(e["context_conflicts"])[:200]})
            pc = panel_conds.get(key, {})
            cap = cap_by_idx.get(key[0], "")
            if not pc and re.search(r"\d[\d.]*\s*(°\s*C|Pa|hPa|Torr|mTorr|mbar|s\b|cycles)", cap):
                cases.append({"case_type": "empty_conditions_despite_numeric_caption",
                              "ref": e["exp_id"],
                              "detail": "panel conditions {} but caption carries numerics"})
            lab = str(e.get("series_name") or "")
            if lab and LEGEND_TOK.search(lab):
                vals = {round(float(c["value"]), 9) for c in ctrl
                        if isinstance(c.get("value"), (int, float))}
                nums = {round(float(x), 9) for x in re.findall(r"[-+]?\d*\.?\d+", lab)}
                if nums and not (nums & vals):
                    cases.append({"case_type": "legend_condition_without_structured_binding",
                                  "ref": e["exp_id"],
                                  "detail": "label %r carries %s but no matching controlled value"
                                  % (lab, sorted(nums))})
            # figure-level geometry broadcast across unrelated figures
            geo = [c for c in ctrl if c.get("quantity") in
                   ("feature_height", "feature_width", "feature_length") and c.get("scope") == "paper"]
            if len({(c["quantity"], c["value"]) for c in geo}) > 1:
                cases.append({"case_type": "figure_geometry_broadcast_across_figures",
                              "ref": e["exp_id"],
                              "detail": "%d distinct paper-scope geometry values attached"
                              % len({(c["quantity"], c["value"]) for c in geo})})

    # ---- §K full-paper audit triggers ----
    by_paper_case = defaultdict(Counter)
    for c in cases:
        ref = str(c["ref"])
        doi = next((p for p in papers if ref.startswith(p)), ref if ref in papers else None)
        if doi:
            by_paper_case[doi][c["case_type"]] += 1
    for doi in papers:
        n = pop["per_paper"][doi]["experiments"]
        mdl = pop["per_paper"][doi]["model_records"]
        reasons = []
        if n and mdl / n > 0.5:
            reasons.append("more_than_half_records_are_model")
        if by_paper_case[doi].get("pressure_in_source_not_in_output"):
            reasons.append("pressure_present_in_paper_absent_downstream")
        if by_paper_case[doi].get("figure_geometry_broadcast_across_figures"):
            reasons.append("figure_geometry_broadcast")
        big = [s for s in allser if s[1] == doi and s[0] > 20]
        if big:
            reasons.append("series_creates_more_than_20_experiments")
        d = next((g for g in growth if g[1] == doi), None)
        if d and d[0] > 100:
            reasons.append("experiment_count_grew_by_more_than_100")
        if reasons:
            triggers.append({"paper_id": doi, "reasons": reasons,
                             "experiments": n, "model_records": mdl,
                             "case_counts": dict(by_paper_case[doi])})

    (OUT / "targeted_case_audit.json").write_text(json.dumps(
        {"n": len(cases), "by_type": dict(Counter(c["case_type"] for c in cases)),
         "cases": cases}, indent=1, ensure_ascii=False))
    with open(OUT / "targeted_case_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["case_type", "ref", "detail"])
        w.writeheader()
        for c in cases:
            w.writerow(c)
    (OUT / "full_paper_audit_triggers.json").write_text(json.dumps(
        {"n_triggered": len(triggers), "triggers": triggers}, indent=1))
    print("targeted cases: %d" % len(cases))
    for k, v in Counter(c["case_type"] for c in cases).most_common():
        print("   %-48s %d" % (k, v))
    print("\nfull-paper audit triggered for %d papers" % len(triggers))


if __name__ == "__main__":
    main()
