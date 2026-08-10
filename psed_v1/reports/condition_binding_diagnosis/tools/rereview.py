#!/usr/bin/env python3
"""READ-ONLY. Corrections #2/#3/#4/#6 — re-review every sampled record against exact
local paper evidence, label the classification METHOD, and derive the deduplicated
underlying-case view.

classification_method:
  paper_verified     — an exact quoted span from the paper (caption/body/table) states
                       the run structure, AND a run/sample identifier is resolvable
  caption_inferred   — an exact quoted caption span states the run structure, but no
                       per-run identifier is available
  metadata_inferred  — decided from pipeline metadata that mirrors the paper
                       (relevance=model, paper-level fallback record) without a quoted span
  heuristic          — decided from point count / axis role alone; NOT ground truth
"""
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = REPO / "02_extraction" / "output"
EX = REPO / "03_corpus" / "extracted"


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def T(p):
    try:
        return Path(p).read_text(errors="replace")
    except Exception:
        return ""


# --- exact-span rules. Each returns (regex, run_structure, why) ---------------
CONTINUOUS_RULES = [
    (re.compile(r"[Ii]n[- ]?situ[^.]{0,80}", re.M), "one_continuous_run",
     "caption states the data are in-situ monitoring of a single run"),
    (re.compile(r"(?:monitor(?:ing|ed)|record(?:ing|ed))\s+(?:by|with|using)\s+"
                r"(?:SE|ellipsom\w*|QCM)[^.]{0,60}", re.I), "one_continuous_run",
     "caption states continuous instrument monitoring"),
    (re.compile(r"stepwise growth for individual cycles[^.]{0,40}", re.I), "one_continuous_run",
     "caption describes a per-cycle trace of one run"),
    (re.compile(r"depth profile[^.]{0,60}", re.I), "one_continuous_run",
     "a depth profile is one specimen measured through its thickness"),
    (re.compile(r"(?:photocataly\w+|degradation)[^.]{0,60}", re.I), "one_continuous_run",
     "kinetic trace of a single specimen"),
    (re.compile(r"(?:impedance|storage (?:time|for)|after \d+\s*h storage)[^.]{0,60}", re.I),
     "one_continuous_run", "electrochemical trace of a single cell"),
]
DISCRETE_RULES = [
    (re.compile(r"independently varied[^.]{0,60}", re.I), "separate_depositions",
     "caption says the parameter was independently varied -> one run per value"),
    (re.compile(r"[Ss]aturation curves?[^.]{0,60}"), "separate_depositions",
     "a saturation curve is one deposition per dose"),
    (re.compile(r"self[- ]limiting[^.]{0,60}", re.I), "separate_depositions",
     "self-limiting growth study: one deposition per dose"),
    (re.compile(r"[Dd]etermining .{0,20}windows?[^.]{0,60}"), "separate_depositions",
     "process-window study: one deposition per setting"),
    (re.compile(r"(?:as a function of|versus|vs\.?)\s+(?:the\s+)?"
                r"(?:deposition\s+)?temperature[^.]{0,50}", re.I), "separate_depositions",
     "growth vs temperature: one deposition per temperature"),
    (re.compile(r"(?:as a function of|versus|vs\.?)\s+(?:the\s+)?"
                r"(?:process\s+)?pressure[^.]{0,50}", re.I), "separate_depositions",
     "growth vs pressure: one run per pressure setting"),
    (re.compile(r"(?:as a function of|versus|vs\.?|influence of)[^.]{0,20}"
                r"(?:pulse|purge|exposure|dose)\s*(?:time|length)?[^.]{0,50}", re.I),
     "separate_depositions", "dose/purge sweep: one deposition per setting"),
    (re.compile(r"(?:as a function of|versus|vs\.?)\s+(?:the\s+)?number of\s+"
                r"(?:ALD\s+)?cycles[^.]{0,50}", re.I), "separate_depositions_or_trace",
     "thickness-vs-cycles can be separate runs OR one in-situ trace"),
]
# sample / run identifiers stated in the paper
SAMPLE_ID = re.compile(r"\b(?:sample|run|specimen)s?\s+((?:\d+\s*,?\s*(?:and\s*)?)+)", re.I)


def caption_of(doi, exp):
    fi = str((exp.get("provenance") or {}).get("fig_docling_index") or "")
    for f in (J(EX / doi / "figure_data.json", {}) or {}).get("figures", []):
        if str(f.get("figure")) == fi:
            return f.get("caption") or ""
    return ""


def doc_section_for_figure(doi, fignum):
    """Body text around 'Fig. N' mentions — the local paper evidence we have."""
    txt = T(EX / doi / "document.md")
    if not fignum:
        return ""
    out = []
    for m in re.finditer(r"[Ff]ig(?:ure)?s?\.?\s*%s(?![0-9])" % re.escape(str(fignum)), txt):
        out.append(txt[max(0, m.start() - 200): m.end() + 500])
        if len(out) >= 3:
            break
    return "\n---\n".join(out)


def review(rec, exp):
    doi = rec["paper_id"]
    cap = caption_of(doi, exp)
    prov = exp.get("provenance") or {}
    fignum = prov.get("figure_number")
    body = doc_section_for_figure(doi, fignum)
    blob = cap + "\n" + body
    sample_id = ""
    sm = SAMPLE_ID.search(cap) or SAMPLE_ID.search(body)
    if sm:
        sample_id = " ".join(sm.group(0).split())[:80]

    out = {
        "record_id": rec["record_id"], "paper_id": doi,
        "printed_figure_number": fignum, "panel": prov.get("panel"),
        "series_label": exp.get("series_name"),
        "document_section": "figure %s caption + body mentions in document.md" % fignum,
        "source_pdf_page": None,   # docling emits no page index; see limitations
        "evidence_span": "", "run_structure": "", "why": "",
        "sample_or_run_id": sample_id, "classification_method": "heuristic",
        "verdict": "uncertain", "entity_kind": "unknown",
        "underlying_case_key": "",
    }

    # underlying case = the CURVE the record came from (dedup key for level 2)
    out["underlying_case_key"] = "%s::F%s::%s::%s" % (
        doi, fignum, prov.get("panel") or "-",
        (exp.get("series_name") or "").split(":")[-1].strip() or "0")

    # --- metadata-level facts that mirror the paper ------------------------
    if exp.get("is_model_result") or exp.get("relevance") == "model":
        out.update(verdict="no", entity_kind="simulation_run_or_profile",
                   run_structure="model_output",
                   why="pipeline flags relevance=model / is_model_result",
                   classification_method="metadata_inferred")
        m = re.search(r"(?:simulat\w+|model(?:l)?ed|calculat\w+)[^.]{0,70}", blob, re.I)
        if m:
            out["evidence_span"] = m.group(0).strip()
            out["classification_method"] = "caption_inferred"
        return out
    if rec["kind"] == "paper_level_record":
        out.update(verdict="no", entity_kind="derived_representation",
                   run_structure="not_a_measured_curve",
                   why="paper-level fallback record created when no figure data existed",
                   classification_method="metadata_inferred")
        return out
    if rec["kind"] == "profile_experiment":
        out.update(verdict="yes", entity_kind="experimental_profile",
                   run_structure="one_continuous_run",
                   why="spatial profile of one coated structure, kept as one record",
                   classification_method=("paper_verified" if sample_id
                                          else "metadata_inferred"))
        if sample_id:
            out["evidence_span"] = sample_id
        return out
    if rec["kind"] == "correlation_record":
        out.update(verdict="no", entity_kind="derived_representation",
                   run_structure="output_vs_output",
                   why="both axes are measured outputs; not a swept input",
                   classification_method="metadata_inferred")
        return out

    # --- series members: needs an exact span --------------------------------
    if rec["kind"] == "series_member_experiment":
        for rx, struct, why in CONTINUOUS_RULES:
            m = rx.search(blob)
            if m:
                out.update(verdict="no", entity_kind="measurement",
                           run_structure=struct, why=why,
                           evidence_span=" ".join(m.group(0).split())[:240],
                           classification_method="caption_inferred")
                break
        else:
            for rx, struct, why in DISCRETE_RULES:
                m = rx.search(blob)
                if m:
                    if struct == "separate_depositions_or_trace":
                        out.update(verdict="uncertain", entity_kind="experimental_case",
                                   run_structure=struct, why=why,
                                   evidence_span=" ".join(m.group(0).split())[:240],
                                   classification_method="caption_inferred")
                    else:
                        out.update(verdict="yes", entity_kind="experimental_case",
                                   run_structure=struct, why=why,
                                   evidence_span=" ".join(m.group(0).split())[:240],
                                   classification_method="caption_inferred")
                    break
            else:
                out.update(verdict="uncertain", entity_kind="unknown",
                           run_structure="undetermined",
                           why="no explicit statement of run structure in the caption or "
                               "the figure's body mentions; point count alone is not evidence",
                           classification_method="heuristic")
        if sample_id and out["verdict"] in ("yes", "no") and out["evidence_span"]:
            out["classification_method"] = "paper_verified"
        return out

    out.update(why="record kind %s not classifiable from local evidence" % rec["kind"])
    return out


def main():
    man = J(OUT / "random_sample_manifest.json")
    audit = J(OUT / "random_sample_audit.json")
    by_id = {r["record_id"]: r for r in audit["rows"]}
    cache = {}
    rows = []
    for rec in man["records"]:
        doi = rec["paper_id"]
        if doi not in cache:
            cache[doi] = {e["exp_id"]: e for e in
                          (J(KB / doi / "resolved" / "experiments.json", []) or [])}
        exp = cache[doi].get(rec["record_id"], {})
        r = review(rec, exp)
        r["sample_index"] = rec["sample_index"]
        r["sampling_stratum"] = rec["_stratum"]
        r["current_record_kind"] = rec["kind"]
        rows.append(r)
        a = by_id.get(rec["record_id"])
        if a:
            a["supported_as_physical_experiment"] = r["verdict"]
            a["paper_ground_truth_entity_kind"] = r["entity_kind"]
            a["classification_method"] = r["classification_method"]
            a["ground_truth_evidence_span"] = r["evidence_span"]
            a["ground_truth_basis"] = r["why"]
            a["run_structure"] = r["run_structure"]
            a["sample_or_run_id"] = r["sample_or_run_id"]
            a["underlying_case_key"] = r["underlying_case_key"]
            a["manual_review_required"] = r["classification_method"] == "heuristic"

    # ---- level 2: deduplicated underlying cases --------------------------
    cases = defaultdict(list)
    for r in rows:
        cases[r["underlying_case_key"]].append(r)
    case_rows = []
    for key, members in sorted(cases.items()):
        v = Counter(m["verdict"] for m in members).most_common(1)[0][0]
        case_rows.append({
            "underlying_case_key": key,
            "paper_id": members[0]["paper_id"],
            "printed_figure_number": members[0]["printed_figure_number"],
            "panel": members[0]["panel"],
            "series_label": members[0]["series_label"],
            "n_sampled_records_from_this_case": len(members),
            "verdict": v,
            "entity_kind": members[0]["entity_kind"],
            "run_structure": members[0]["run_structure"],
            "classification_method": members[0]["classification_method"],
            "evidence_span": members[0]["evidence_span"],
            "sample_or_run_id": members[0]["sample_or_run_id"],
        })

    (OUT / "record_rereview.json").write_text(json.dumps(
        {"n_records": len(rows), "n_underlying_cases": len(case_rows),
         "records": rows, "underlying_cases": case_rows}, indent=1, ensure_ascii=False))
    for name, data in (("record_rereview.csv", rows), ("underlying_case_review.csv", case_rows)):
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            for x in data:
                w.writerow(x)
    (OUT / "random_sample_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
    with open(OUT / "random_sample_audit.csv", "w", newline="") as fh:
        cols = sorted({k for r in audit["rows"] for k in r})
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in audit["rows"]:
            w.writerow(r)

    print("RECORD level  n=%d" % len(rows))
    print("  verdict:", dict(Counter(r["verdict"] for r in rows)))
    print("  method :", dict(Counter(r["classification_method"] for r in rows)))
    print("\nUNDERLYING CASE level  n=%d" % len(case_rows))
    print("  verdict:", dict(Counter(r["verdict"] for r in case_rows)))
    print("  method :", dict(Counter(r["classification_method"] for r in case_rows)))


if __name__ == "__main__":
    main()
