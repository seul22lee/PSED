#!/usr/bin/env python3
"""READ-ONLY. §F — source-grounded verdict on whether each sampled record is a
separately conducted physical experiment.

The discriminator is NOT the x-axis quantity. It is whether the curve is a
CONTINUOUS trace of one sample, or a set of DISCRETE separately-prepared runs.
Each rule quotes the caption/text span it fired on, so every verdict is auditable.
"""
import json, re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = REPO / "02_extraction" / "output"
EX = REPO / "03_corpus" / "extracted"

# --- continuous single-sample measurement (one run, sampled densely) --------
CONTINUOUS = [
    (re.compile(r"\bin[- ]?situ\b", re.I), "in-situ monitoring of a single run"),
    (re.compile(r"\bspectroscopic ellipsom|VASE\b|\bSE\b(?!M)", re.I), "in-situ ellipsometry trace"),
    (re.compile(r"\bQCM\b|quartz crystal", re.I), "QCM trace"),
    (re.compile(r"\breal[- ]time\b", re.I), "real-time trace"),
    (re.compile(r"\bversus time\b|\bvs\.? time\b|\bover time\b", re.I), "time trace"),
    (re.compile(r"depth profile|sputter(ing)? (time|depth)", re.I), "depth profile of one sample"),
    (re.compile(r"photocataly|degradation of|C/C0", re.I), "kinetic trace of one sample"),
    (re.compile(r"impedance|storage time|cycling of", re.I), "electrochemical trace of one cell"),
]
# --- discrete separately-prepared runs --------------------------------------
DISCRETE = [
    (re.compile(r"saturation curve|self[- ]limiting", re.I), "saturation curve: one deposition per dose"),
    (re.compile(r"ALD window|growth (per cycle|rate).{0,40}(as a )?function of .{0,20}temperature", re.I),
     "ALD-window sweep: one deposition per temperature"),
    (re.compile(r"as a function of .{0,30}(pulse|exposure|dose|purge) (time|length)", re.I),
     "dose sweep: one deposition per pulse time"),
    (re.compile(r"independently varied", re.I), "explicitly independently varied parameter"),
]


def caption_for(doi, exp):
    prov = exp.get("provenance") or {}
    fd = json.loads((EX / doi / "figure_data.json").read_text()) if (EX / doi / "figure_data.json").exists() else {}
    for fig in fd.get("figures", []) or []:
        if str(fig.get("figure")) == str(prov.get("fig_docling_index") or ""):
            return fig.get("caption") or ""
    return ""


def classify(rec, exp, cap, n_src):
    """-> (verdict, ground_truth_kind, basis, evidence_span, human_checkable)"""
    if exp.get("is_model_result") or exp.get("relevance") == "model":
        return ("no", "simulation_run" if rec["kind"] == "series_member_experiment"
                else "simulation_profile",
                "record carries is_model_result / relevance=model", "", True)
    if rec["kind"] == "paper_level_record":
        return ("no", "derived_representation", "paper-level fallback record", "", True)
    if rec["kind"] == "profile_experiment":
        return ("yes", "experimental_profile", "spatial profile kept as one experiment", "", True)

    if rec["kind"] == "series_member_experiment":
        for rx, why in CONTINUOUS:
            m = rx.search(cap)
            if m:
                return ("no", "measurement", why,
                        cap[max(0, m.start() - 50):m.end() + 50].strip(), True)
        # very dense sampling of a smooth line is digitiser density, not runs
        if n_src and n_src >= 15:
            return ("no", "measurement",
                    "curve digitised at %d points; the extractor is instructed to read "
                    "~50 evenly spaced points along the line, so the count reflects "
                    "digitisation density rather than separate depositions" % n_src,
                    "", True)
        for rx, why in DISCRETE:
            m = rx.search(cap)
            if m:
                return ("yes", "experimental_case", why,
                        cap[max(0, m.start() - 50):m.end() + 50].strip(), True)
        if n_src and n_src <= 12:
            return ("uncertain", "experimental_case",
                    "sparse condition sweep (%d points) with no explicit caption cue" % n_src,
                    "", False)
        return ("uncertain", "unknown", "no decisive caption cue", "", False)

    if rec["kind"] == "correlation_record":
        return ("no", "derived_representation",
                "both axes are measured outputs; this is a correlation plot", "", True)
    if rec["kind"] == "unresolved_experiment_record":
        return ("uncertain", "unknown", "axis role unresolved by the ontology", "", False)
    return ("uncertain", "unknown", "", "", False)


def main():
    audit = json.loads((OUT / "random_sample_audit.json").read_text())
    man = json.loads((OUT / "random_sample_manifest.json").read_text())
    by_id = {r["record_id"]: r for r in man["records"]}
    exps_cache = {}
    for row in audit["rows"]:
        doi, rid = row["paper_id"], row["record_id"]
        if doi not in exps_cache:
            exps_cache[doi] = {e["exp_id"]: e for e in
                               json.loads((KB / doi / "resolved" / "experiments.json").read_text())}
        exp = exps_cache[doi].get(rid, {})
        cap = caption_for(doi, exp)
        v, k, basis, span, checkable = classify(by_id[rid], exp, cap, row["source_curve_n_points"])
        row["supported_as_physical_experiment"] = v
        row["paper_ground_truth_entity_kind"] = k
        row["ground_truth_basis"] = basis
        row["ground_truth_evidence_span"] = span
        row["manual_review_required"] = not checkable
    (OUT / "random_sample_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
    import csv
    cols = list(audit["rows"][0].keys())
    with open(OUT / "random_sample_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in audit["rows"]:
            w.writerow(r)
    print("verdict:", dict(Counter(r["supported_as_physical_experiment"] for r in audit["rows"])))
    print("kind   :", dict(Counter(r["paper_ground_truth_entity_kind"] for r in audit["rows"])))
    print("needs human review:", sum(1 for r in audit["rows"] if r["manual_review_required"]))


if __name__ == "__main__":
    main()
