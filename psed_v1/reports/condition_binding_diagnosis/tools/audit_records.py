#!/usr/bin/env python3
"""READ-ONLY. §D/E/G/H — three-layer trace + annotation for every sampled record.

Layer 1 original paper   : document.md, caption, figure image path, PDF page hint
Layer 2 extracted        : figure_data.json, records.json, pressure.json, card.json,
                           geometry.json, scout.json
Layer 3 resolved         : resolved/experiments.json, series.json, canonical/curves.json,
                           recipes.json

Every condition mention found in Layer 1/2 is followed into Layer 3 and given a
§G status. The first divergence is recorded as first_failure_stage with a §H
root-cause code. Machine-decidable facts only; fields needing human judgement are
marked manual_review_required.
"""
import paths as P
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = P.PAPERS
EX = P.PAPERS

NUMU = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
_cache = {}


def J(p):
    p = Path(p)
    k = str(p)
    if k not in _cache:
        try:
            _cache[k] = json.loads(p.read_text())
        except Exception:
            _cache[k] = None
    return _cache[k]


def T(p):
    p = Path(p)
    k = "T:" + str(p)
    if k not in _cache:
        try:
            _cache[k] = p.read_text(errors="replace")
        except Exception:
            _cache[k] = ""
    return _cache[k]


PRESSURE_Q = {"generic_pressure", "working_pressure", "base_pressure", "total_pressure",
              "partial_pressure", "chamber_total_pressure", "bubbler_pressure",
              "precursor_partial_pressure", "co_reactant_partial_pressure",
              "reactant_A_partial_pressure", "reactant_B_partial_pressure",
              "carrier_gas_partial_pressure"}

# legend tokens that imply a structured condition (§C last bullet)
LEGEND_TOKENS = re.compile(
    r"(?P<num>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*"
    r"(?P<unit>°\s*C|K\b|mTorr|Torr|mbar|hPa|kPa|Pa\b|sccm|cycles?\b|ms\b|s\b|min\b|"
    r"nm\b|µm\b|um\b|μm\b|mm\b)", re.I)


def find_exp(doi, rid):
    for e in (J(P.resolved_json(doi, "experiments")) or []):
        if e.get("exp_id") == rid:
            return e
    return None


def panel_of(doi, exp):
    """The figure_data panel + series this record came from."""
    prov = exp.get("provenance") or {}
    fd = J(P.extracted_dir(doi) / "figure_data.json") or {}
    fi = str(prov.get("fig_docling_index") or "")
    pan = str(prov.get("panel") or "")
    for fig in fd.get("figures", []) or []:
        if str(fig.get("figure")) != fi:
            continue
        for p in fig.get("panels", []) or []:
            if str(p.get("panel") or "") == pan:
                return fig, p
        return fig, None
    return None, None


def source_curve_points(fig, panel, series_name):
    if not panel:
        return None
    lab = None
    if series_name and ":" in str(series_name):
        lab = str(series_name).split(":", 1)[1].strip()
    for s in panel.get("series", []) or []:
        if lab is not None and str(s.get("label", "")).strip() == lab:
            return len(s.get("points") or [])
    ser = panel.get("series") or []
    return len(ser[0].get("points") or []) if ser else None


def audit(rec):
    doi, rid = rec["paper_id"], rec["record_id"]
    exp = find_exp(doi, rid)
    row = {k: rec.get(k) for k in ("sample_index", "paper_id", "record_id", "_stratum")}
    row["sampling_stratum"] = rec.get("_stratum")
    row["doi"] = doi
    row["current_record_id"] = rid
    row["current_series_id"] = (exp or {}).get("in_series")
    prov = (exp or {}).get("provenance") or {}
    row["printed_figure_number"] = prov.get("figure_number")
    row["fig_docling_index"] = prov.get("fig_docling_index")
    row["panel"] = prov.get("panel")
    row["series_label"] = (exp or {}).get("series_name")
    row["current_record_kind"] = rec["kind"]
    row["current_relevance"] = (exp or {}).get("relevance")
    row["current_granularity"] = (exp or {}).get("granularity")
    row["current_source_kind"] = prov.get("extractor")
    row["current_is_model_result"] = bool((exp or {}).get("is_model_result"))

    fig, panel = panel_of(doi, exp or {})
    cap = (fig or {}).get("caption") or ""
    row["source_caption"] = cap[:400]
    row["source_pdf_page"] = None            # docling does not record page; see notes
    row["figure_image"] = (fig or {}).get("image")

    ctrl = (exp or {}).get("controlled") or []
    ctrl_by_q = defaultdict(list)
    for c in ctrl:
        ctrl_by_q[c.get("quantity")].append(c)
    row["resolved_conditions"] = sorted(ctrl_by_q)
    row["kb_visible_conditions"] = sorted(
        q for q, v in ctrl_by_q.items()
        if any(x.get("context_status") != "ambiguous" for x in v))

    # ---------- Layer 2 evidence ----------
    fd_conds = dict((panel or {}).get("conditions") or {})
    row["figure_data_conditions"] = json.dumps(fd_conds, ensure_ascii=False)
    recs = J(P.extracted_dir(doi) / "records.json") or []
    rc = {}
    for r in recs:
        p = r.get("provenance") or {}
        if str(p.get("fig_docling_index") or "") == str(row["fig_docling_index"] or "") and \
           str(p.get("panel") or "") == str(row["panel"] or ""):
            rc = dict(r.get("controlled") or {})
            break
    row["records_conditions"] = json.dumps(rc, ensure_ascii=False)
    pj = (J(P.extracted_dir(doi) / "pressure.json") or {}).get("pressures") or []
    row["pressure_json_conditions"] = json.dumps(
        [{"type": p.get("pressure_type"), "value": p.get("value"), "unit": p.get("unit"),
          "context": p.get("context"), "species": p.get("named_species")} for p in pj],
        ensure_ascii=False)[:600]

    recipe = (exp or {}).get("recipe") or {}
    row["recipe_conditions"] = json.dumps(
        {k: recipe.get(k) for k in ("temperature", "ncycles", "flow_rate", "carrier_gas")
         if recipe.get(k) is not None}, ensure_ascii=False)

    # ---------- §G condition-by-condition status ----------
    cond_status, missing, incorrect, over, dup = {}, [], [], [], []

    # (1) panel conditions declared in figure_data must appear on the record
    for k, v in fd_conds.items():
        m = NUMU.fullmatch(str(v))
        if not m:
            cond_status[k] = "preserved_as_text_but_not_structured"
            continue
        hit = [c for c in ctrl if _same_quantity(c.get("quantity"), k)]
        if not hit:
            cond_status[k] = "structured_but_not_bound"
            missing.append("%s=%s(panel)" % (k, v))
        elif all(h.get("context_status") == "ambiguous" for h in hit):
            cond_status[k] = "hidden_by_fallback"
            missing.append("%s=%s(ambiguous_at_paper_scope)" % (k, v))
        else:
            scopes = {h.get("scope") for h in hit}
            cond_status[k] = ("correctly_extracted_and_bound"
                              if scopes & {"panel", "figure", "curve", "point", "experiment"}
                              else "bound_at_wrong_scope")

    # (2) numeric tokens in the SERIES LABEL must have a structured condition
    lab = str(row["series_label"] or "")
    for m in LEGEND_TOKENS.finditer(lab):
        tok = m.group(0)
        val = float(m.group("num"))
        near = [c for c in ctrl
                if isinstance(c.get("value"), (int, float))
                and abs(float(c["value"]) - val) <= 1e-6 * max(1.0, abs(val))]
        key = "legend:" + tok.strip()
        if near:
            cond_status[key] = "correctly_extracted_and_bound"
        else:
            # unit conversion may have rescaled it; accept an order-of-magnitude match
            loose = [c for c in ctrl if isinstance(c.get("value"), (int, float))
                     and val != 0 and 0.9 <= abs(float(c["value"]) / val) <= 1.1e3]
            cond_status[key] = ("bound_with_wrong_quantity" if loose
                                else "present_in_source_but_not_extracted")
            if not loose:
                missing.append("legend " + tok.strip())

    # (3) pressure specifically
    pres_ctrl = [c for c in ctrl if c.get("quantity") in PRESSURE_Q]
    usable_pres = [c for c in pres_ctrl if c.get("context_status") != "ambiguous"
                   and c.get("quantity") != "base_pressure"]
    cap_pres = bool(re.search(r"\d[\d.]*\s*(mbar|mTorr|Torr|Pa|hPa|kPa)", cap, re.I))
    row["pressure_in_caption"] = cap_pres
    row["pressure_in_pressure_json"] = bool(pj)
    row["pressure_on_record_usable"] = bool(usable_pres)
    if (cap_pres or pj) and not usable_pres:
        cond_status["pressure"] = ("hidden_by_fallback" if pres_ctrl
                                   else "present_in_source_but_not_extracted")
        missing.append("pressure")
    elif usable_pres:
        cond_status.setdefault("pressure", "correctly_extracted_and_bound")

    # (4) paper-scope broadcast of conflicting values
    for cf in (exp or {}).get("context_conflicts") or []:
        over.append("%s@%s:%s" % (cf.get("quantity"), cf.get("scope"), cf.get("values")))
        cond_status[cf.get("quantity")] = "incorrectly_broadcast"

    # (5) duplicated identical bindings
    seen = Counter((c.get("quantity"), c.get("value"), c.get("unit")) for c in ctrl)
    for k, n in seen.items():
        if n > 1:
            dup.append("%s=%s x%d" % (k[0], k[1], n))

    row["condition_status"] = json.dumps(cond_status, ensure_ascii=False)
    row["missing_conditions"] = ";".join(missing)
    row["incorrect_conditions"] = ";".join(incorrect)
    row["over_broadcast_conditions"] = ";".join(over)
    row["duplicate_evidence_bindings"] = ";".join(dup)
    row["fallback_substitutions"] = ";".join(
        sorted({c.get("source") for c in ctrl if c.get("source") in ("species", "geometry")}))

    # ---------- §F is this actually a physical experiment? ----------
    n_src = source_curve_points(fig, panel, row["series_label"])
    row["source_curve_n_points"] = n_src
    verdict, gt_kind, why, manual = _entity_verdict(rec, exp or {}, panel, cap, n_src)
    row["supported_as_physical_experiment"] = verdict
    row["paper_ground_truth_entity_kind"] = gt_kind
    row["ground_truth_basis"] = why
    row["manual_review_required"] = manual

    # ---------- §H first failure + root cause ----------
    stage, cause, conf = _root_cause(row, rec, exp or {}, fd_conds, rc, pj, cond_status)
    row["first_failure_stage"] = stage
    row["root_cause_category"] = cause
    row["responsible_code_path"] = _code_path(cause)
    row["confidence"] = conf
    return row


def _same_quantity(canon, raw):
    if not canon or not raw:
        return False
    a, b = str(canon).lower(), str(raw).lower()
    if a == b:
        return True
    if b in a or a in b:
        return True
    if b.startswith("press") and a in PRESSURE_Q:
        return True
    if b.startswith("temp") and "temperature" in a:
        return True
    return False


def _entity_verdict(rec, exp, panel, cap, n_src):
    """Machine verdict + basis. Anything not decidable from structure is flagged."""
    if exp.get("is_model_result") or exp.get("relevance") == "model":
        return ("no", "simulation_run" if rec["kind"] == "series_member_experiment"
                else "simulation_profile",
                "record is flagged is_model_result/relevance=model in experiments.json", False)
    if rec["kind"] == "paper_level_record":
        return ("no", "derived_representation",
                "paper-level fallback record, not tied to a measured curve", False)
    if rec["kind"] == "series_member_experiment":
        # a curve digitised at ~n points became n experiments
        if n_src and n_src >= 12:
            return ("no", "measurement",
                    ("one of %d digitised points of a single continuous curve; the "
                     "digitiser samples ~%d points along the line, so point count "
                     "reflects digitisation density, not the number of depositions" % (n_src, n_src)),
                    False)
        return ("uncertain", "experimental_case",
                "condition sweep with %s digitised points; whether each point is a "
                "separate deposition needs the paper" % n_src, True)
    if rec["kind"] == "profile_experiment":
        return ("yes", "experimental_profile",
                "spatial profile retained as one experiment", False)
    if rec["kind"] == "correlation_record":
        return ("uncertain", "derived_representation",
                "both axes are ontology outputs", True)
    if rec["kind"] == "unresolved_experiment_record":
        return ("uncertain", "unknown", "axis role unresolved", True)
    return ("uncertain", "unknown", "", True)


def _root_cause(row, rec, exp, fd_conds, rc, pj, cond_status):
    st = set(cond_status.values())
    # over-splitting dominates when present
    if row["supported_as_physical_experiment"] == "no" and \
       rec["kind"] == "series_member_experiment" and not row["current_is_model_result"]:
        return ("06_to_kb.split_condition_series", "P", 0.95)
    if row["current_is_model_result"] and rec["kind"] in (
            "series_member_experiment", "profile_experiment", "single_experiment"):
        return ("06_to_kb.to_experiments (model curve stored in experiments.json)", "S", 0.9)
    if "hidden_by_fallback" in st:
        return ("06_to_kb._dedup_pressures / ambiguity flagging", "I", 0.9)
    if "structured_but_not_bound" in st:
        return ("06_to_kb.to_experiments panel_ctrl", "H", 0.85)
    if "incorrectly_broadcast" in st:
        return ("10_pressure.pressure_facts -> paper-scope broadcast", "J", 0.85)
    if "present_in_source_but_not_extracted" in st:
        return ("05_figure_extract (legend value not structured)", "A", 0.7)
    if "preserved_as_text_but_not_structured" in st:
        return ("06_to_kb._num_cond (non-numeric caption condition)", "B", 0.8)
    if "bound_at_wrong_scope" in st:
        return ("06_to_kb scope assignment", "E", 0.7)
    if row["current_granularity"] in ("unresolved", None):
        return ("canonical.axis_semantics (axis role unresolved)", "C", 0.7)
    return ("none_detected", "", 0.6)


CODE = {
    "P": "03_corpus/scripts/06_to_kb.py::split_condition_series",
    "S": "03_corpus/scripts/06_to_kb.py::to_experiments (relevance=model still written to experiments.json)",
    "I": "03_corpus/scripts/06_to_kb.py::_dedup_pressures",
    "H": "03_corpus/scripts/06_to_kb.py::to_experiments panel_ctrl / _num_cond",
    "J": "03_corpus/scripts/10_pressure.py::pressure_facts + 06_to_kb base_ctrl",
    "A": "03_corpus/scripts/05_figure_extract.py::VISION_SCHEMA (series_axis/conditions)",
    "B": "03_corpus/scripts/06_to_kb.py::_num_cond",
    "E": "02_extraction/canonical/live.py::scope_of",
    "C": "02_extraction/canonical/axis_semantics.py::resolve_x_axis",
    "": "",
}


def _code_path(c):
    return CODE.get(c, "")


def main():
    man = json.loads((OUT / "random_sample_manifest.json").read_text())
    rows = [audit(r) for r in man["records"]]
    (OUT / "random_sample_audit.json").write_text(json.dumps(
        {"n": len(rows), "seed": man["random_seed"], "rows": rows}, indent=1, ensure_ascii=False))
    cols = list(rows[0].keys())
    with open(OUT / "random_sample_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("audited %d records" % len(rows))
    print("physical experiment?", dict(Counter(r["supported_as_physical_experiment"] for r in rows)))
    print("ground truth kind :", dict(Counter(r["paper_ground_truth_entity_kind"] for r in rows)))
    print("root cause        :", dict(Counter(r["root_cause_category"] for r in rows)))
    print("manual review req :", sum(1 for r in rows if r["manual_review_required"]))


if __name__ == "__main__":
    main()
