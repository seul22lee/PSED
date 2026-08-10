#!/usr/bin/env python3
"""READ-ONLY. §13 — per-condition case matrix for the two deep case-study papers.
Each row is one condition mention verified by hand against the source, traced
through every layer."""
import csv, json, re
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


SSE = "10.1016_j.sse.2022.108584"
D0CP = "10.1039_d0cp03358h"

# hand-verified condition mentions (source text quoted from document.md / captions)
CASES = [
    # ---- SSE Fig. 2 (docling idx 4) -------------------------------------
    (SSE, "2", "4", "a", "*", "feature_width", 1, "µm",
     "cylindrical structure with d = 1μm", "caption", "reported", "figure"),
    (SSE, "2", "4", "a", "*", "feature_length", 100, "µm",
     "L = 100μm", "caption", "reported", "figure"),
    (SSE, "2", "4", "a", "*", "adsorption_site_area", 2e-19, "m2",
     "fictitious chemistry with s0 = 2 x 10-19 m2", "caption", "reported", "figure"),
    (SSE, "2", "4", "a", "*", "collision_flux", 1e24, "m-2 s-1",
     "Γ0 = 10^24 m-2 s-1", "caption", "reported", "figure"),
    (SSE, "2", "4", "a", "*", "chemistry_is_fictitious", None, None,
     "in a fictitious chemistry", "caption", "reported", "figure"),
    # ---- SSE Fig. 4 (idx 6) ---------------------------------------------
    (SSE, "4", "6", "a", "Arts 2019, 310 °C", "deposition_temperature", 310, "°C",
     "legend 'Arts 2019, 310 °C'", "legend", "reported", "series"),
    (SSE, "4", "6", "a", "Model, 310 °C", "deposition_temperature", 310, "°C",
     "legend 'Model, 310 °C'", "legend", "reported", "series"),
    (SSE, "4", "6", "a", "*", "feature_width", 0.5, "µm",
     "trench-like structures (d = 0.5 μm, L = 5000 μm)", "in_text", "reported", "figure"),
    (SSE, "4", "6", "a", "*", "feature_length", 5000, "µm",
     "trench-like structures (d = 0.5 μm, L = 5000 μm)", "in_text", "reported", "figure"),
    (SSE, "4", "6", "a", "Arts 2019*", "exposure", 750, "mTorr.s",
     "an H2O dose of approximately 750 mTorr s", "in_text", "reported", "reference_series"),
    (SSE, "4", "6", "a", "Arts 2019*", "cycle_number", 400, "cycle",
     "after 400 ALD cycles", "in_text", "reported", "reference_series"),
    (SSE, "4", "6", "a", "Arts 2019*", "growth_per_cycle", 1.12, "Å/cycle",
     "with a GPC of 1.12 Å", "in_text", "reported", "reference_series"),
    # ---- SSE Fig. 5 (idx 7) ---------------------------------------------
    (SSE, "5", "7", "a", "Gamma_ev", "measurand_identity", None, None,
     "(a) Arrhenius analysis of β0 and Γev", "caption", "reported", "series"),
    (SSE, "5", "7", "b", "theta_sat", "measurand_identity", None, None,
     "θsat at z = L", "caption", "reported", "series"),
    (SSE, "5", "7", "b", "SC_sat", "measurand_identity", None, None,
     "and SCsat", "caption", "reported", "series"),
    # ---- SSE Fig. 6 (idx 8) ---------------------------------------------
    (SSE, "6", "8", "a", "Ylilammi 2018", "precursor_partial_pressure", 325, "mTorr",
     "For Ylilammi et al. [9] ... we estimate pA = 325 mTorr", "in_text", "estimated",
     "reference_series"),
    (SSE, "6", "8", "a", "Arts 2019", "pulse_time", 0.4, "s",
     "for Arts et al. [13], tp = 0.4 s", "in_text", "estimated", "reference_series"),
    (SSE, "6", "8", "a", "Yim and Ylivaara 2020, t_p = 0.2 s", "pulse_time", 0.2, "s",
     "legend 'Yim and Ylivaara 2020, t_p = 0.2 s'", "legend", "reported", "series"),
    # ---- SSE Fig. 7 (idx 9) ---------------------------------------------
    (SSE, "7", "9", "a", "Yim and Ylivaara 2020, d = 2.0 µm", "feature_width", 2.0, "µm",
     "legend 'Yim and Ylivaara 2020, d = 2.0 µm'", "legend", "reported", "series"),
    (SSE, "7", "9", "a", "Yim and Ylivaara 2020, d = 0.1 µm", "feature_width", 0.1, "µm",
     "legend 'Yim and Ylivaara 2020, d = 0.1 µm'", "legend", "reported", "series"),
    # ---- D0CP methods ----------------------------------------------------
    (D0CP, "methods", None, None, "*", "working_pressure", 3, "hPa",
     "The process pressure was ca. 3 hPa.", "methods", "reported", "paper"),
    (D0CP, "methods", None, None, "*", "cycle_number", 500, "cycle",
     "typically ca. 50 nm made in 500 ALD cycles", "methods", "reported", "paper"),
    (D0CP, "methods", None, None, "*", "flow_rate", 150, "sccm",
     "Nitrogen ... with a constant flow rate of 150 sccm", "methods", "reported", "paper"),
    (D0CP, "methods", None, None, "*", "carrier_gas", None, None,
     "Nitrogen (purity 6.0) ... used as the carrier and purge gas", "methods", "reported", "paper"),
    # ---- D0CP Fig. 10 (idx 18) simulation --------------------------------
    (D0CP, "10", "18", "a", "*", "reactant_A_partial_pressure", 65, "Pa",
     "p A0 = 65 Pa (A = TMA)", "caption", "assumed_model_input", "figure"),
    (D0CP, "10", "18", "a", "*", "carrier_gas_partial_pressure", 300, "Pa",
     "p B = 300 Pa (B = N2)", "caption", "assumed_model_input", "figure"),
    (D0CP, "10", "18", "a", "*", "pulse_time", 0.10, "s",
     "t P = 0.10 s", "caption", "assumed_model_input", "figure"),
    # ---- D0CP Fig. 11 (idx 19) experiments -------------------------------
    (D0CP, "11", "19", "a", "0.1 s", "pulse_time", 0.1, "s",
     "different TMA pulse times", "legend+caption", "reported", "series"),
    (D0CP, "11", "19", "b", "4 s", "purge_time", 4, "s",
     "(b) purge times", "legend+caption", "reported", "series"),
    (D0CP, "11", "19", "a", "*", "feature_height", 500, "nm",
     "design channel height of 500 nm", "caption", "reported", "figure"),
    (D0CP, "11", "19", "a", "*", "working_pressure", 3, "hPa",
     "The process pressure was ca. 3 hPa.", "methods", "reported", "paper"),
]

PRESSURE_Q = {"generic_pressure", "working_pressure", "total_pressure", "partial_pressure",
              "chamber_total_pressure", "precursor_partial_pressure",
              "co_reactant_partial_pressure", "reactant_A_partial_pressure",
              "reactant_B_partial_pressure", "carrier_gas_partial_pressure", "base_pressure"}


def status_row(c):
    (doi, pfig, idx, panel, sel, q, val, unit, ev, evsrc, vstatus, scope) = c
    fd = J(EX / doi / "figure_data.json", {}) or {}
    doc = T(EX / doi / "document.md")
    pj = (J(EX / doi / "pressure.json", {}) or {}).get("pressures") or []
    exps = J(KB / doi / "resolved" / "experiments.json", []) or []

    # layer: figure_data panel conditions
    fdstat = "n/a"
    if idx:
        for f in fd.get("figures", []):
            if str(f.get("figure")) != str(idx):
                continue
            for p in f.get("panels", []) or []:
                if panel and str(p.get("panel") or "") != panel:
                    continue
                conds = p.get("conditions") or {}
                fdstat = "present" if any(q.split("_")[0] in k.lower() or
                                          (val is not None and str(val) in str(v))
                                          for k, v in conds.items()) else "absent"
    # layer: document.md
    docstat = "present" if ev and ev[:24].split("(")[0].strip()[:14] in doc.replace(" ", " ") else "present(paraphrase)"
    # layer: pressure.json
    pstat = "n/a"
    if "pressure" in q:
        pstat = "present" if any(str(val) == str(x.get("value")) for x in pj) else (
            "EMPTY" if not pj else "absent")
    # layer: resolved
    sel_exps = [e for e in exps
                if (not idx or str((e.get("provenance") or {}).get("fig_docling_index") or "") == str(idx))
                and (sel == "*" or sel.rstrip("*") in str(e.get("series_name") or ""))]
    found, scope_found = "absent", ""
    for e in sel_exps:
        for cc in e.get("controlled") or []:
            same_q = q in str(cc.get("quantity")) or str(cc.get("quantity")) in q
            same_v = val is None or (isinstance(cc.get("value"), (int, float))
                                     and abs(float(cc["value"]) - float(val)) <=
                                     max(1e-9, 0.05 * abs(float(val))))
            conv_v = val is not None and isinstance(cc.get("value"), (int, float)) and val != 0 \
                and 0.95 <= abs(float(cc["value"]) / float(val)) <= 1.05e3
            if same_q and (same_v or conv_v):
                found = "present" if cc.get("context_status") != "ambiguous" else "present_but_ambiguous"
                scope_found = cc.get("scope") or ""
                break
        if found.startswith("present"):
            break
    # first failure
    if found.startswith("present") and found != "present_but_ambiguous":
        first, cause = "", ""
    elif pstat == "EMPTY" and "pressure" in q:
        first, cause = "10_pressure.py (pressure.json empty)", "M"
    elif fdstat == "absent" and evsrc in ("caption", "in_text", "methods"):
        first, cause = "05_figure_extract.py conditions{} / 06_to_kb (text never parsed)", "B"
    elif evsrc == "legend" and found == "absent":
        first, cause = "06_to_kb.to_experiments (series label not parsed into a condition)", "A"
    elif found == "present_but_ambiguous":
        first, cause = "06_to_kb ambiguity flagging over paper-scope broadcast", "J"
    else:
        first, cause = "06_to_kb.to_experiments", "H"
    return {
        "paper_id": doi, "printed_figure": pfig, "fig_docling_index": idx, "panel": panel,
        "series": sel, "condition_quantity": q, "expected_value": val, "expected_unit": unit,
        "evidence_text": ev, "evidence_source": evsrc, "value_status": vstatus,
        "expected_scope": scope,
        "figure_data_status": fdstat, "records_status": fdstat,
        "pressure_json_status": pstat, "resolved_status": found,
        "resolved_scope": scope_found,
        "recipe_status": "n/a", "kb_status": "n/a", "kg_status": "n/a",
        "first_failure_stage": first, "responsible_code": {
            "M": "03_corpus/scripts/10_pressure.py (PILOT; not run corpus-wide)",
            "B": "03_corpus/scripts/05_figure_extract.py::VISION_SCHEMA conditions{}",
            "A": "03_corpus/scripts/06_to_kb.py::to_experiments (series_ctrl only for numeric_sweep)",
            "J": "03_corpus/scripts/10_pressure.py::pressure_facts + 06_to_kb base_ctrl",
            "H": "03_corpus/scripts/06_to_kb.py::to_experiments",
            "": "",
        }.get(cause, ""),
        "failure_category": cause,
    }


def main():
    rows = [status_row(c) for c in CASES]
    (OUT / "case_matrix.json").write_text(json.dumps(
        {"n": len(rows), "papers": [SSE, D0CP], "rows": rows}, indent=1, ensure_ascii=False))
    cols = list(rows[0].keys())
    with open(OUT / "case_matrix.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    ok = sum(1 for r in rows if r["resolved_status"] == "present")
    print("case matrix: %d conditions, %d correctly bound, %d lost/mis-scoped"
          % (len(rows), ok, len(rows) - ok))
    for r in rows:
        print("  %-9s F%-4s %-30s %-10s -> %-22s %s" % (
            r["paper_id"].split("_")[-1][:9], r["printed_figure"], r["condition_quantity"],
            str(r["expected_value"]), r["resolved_status"], r["failure_category"]))


if __name__ == "__main__":
    main()
