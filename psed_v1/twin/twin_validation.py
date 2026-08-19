"""
twin_validation.py  (M3 / Phase 4)
----------------------------------
Validate the KB-parameterised conformality twin against the MEASURED thickness
profiles in the knowledge base. For each experimental Al2O3 conformality profile,
we build channelModel.from_kb(...), set the dose / temperature / geometry from the
experiment's recipe, predict the normalised thickness profile, and score it against
the measurement with the SAME curve engine used for experiment-vs-experiment
comparison (similarity.curve_metrics: nRMSE, R², overlap) plus Δ(PD50).

The output is a validation report + a ranked list of discrepancies — where the twin
(or the literature parameters it was given) disagrees with reality. Those are the
highest-value next experiments (active learning, INTEGRATION_STRATEGY §5).
"""
import paths as P
import base64, io, json, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
from twin.channel_model import channelModel, MODEL_ID
from scipy.optimize import minimize
from pipeline.canonical import similarity as sim
from pipeline.resolve import kb_service as ks

# the geometry classes this twin's ontology model is valid for (geometry-scoped validation)
_ONTO = json.load(open(P.ONTOLOGY_JSON))
TWIN_GEOMETRY = next((m.get("applies_to_geometry") for m in _ONTO.get("models", [])
                      if m["id"] == MODEL_ID), None) or []

BLUE, RED, GREEN, AMBER, PURPLE, INK, GREY = "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#9085e9", "#14161a", "#8b919b"
NM = 1e-9
PLAUSIBLE_GAP_M = (5e-8, 5e-6)          # a Pillarhall/LHAR gap height is ~0.1–2 µm
DEFAULT_H = 0.5e-6                        # LHAR standard gap when geometry is missing/suspect
DEFAULT_W = 1e-4                          # channel width ≫ height; exact value barely matters

_CORPUS = _SC = None


def _ctx():                              # corpus + similarity scale, for imputation
    """Imputation donors come from the PRODUCTION semantic corpus (declared
    41-paper manifest, canonical chemistry) -- never the legacy resolved load."""
    global _CORPUS, _SC
    if _CORPUS is None:
        from twin import semantic_evidence as SE
        _CORPUS = SE.case_records()
        _SC = sim.logscale(_CORPUS)
    return _CORPUS, _SC


def _cond(exp, q, r=None):
    """First numeric value for quantity `q` (a name or a precedence tuple of
    names -- semantic records say deposition_temperature where the legacy layer
    said temperature) in reactant slot `r`."""
    for qq in ((q,) if isinstance(q, str) else q):
        for c in exp.get("controlled") or []:
            if c.get("quantity") == qq and (r is None or c.get("of_reactant") == r):
                v = c.get("value")
                if isinstance(v, (int, float)):
                    return float(v)
    return None


def _input(exp, q, r=None, impute=True):
    """A twin input's (value, provenance): 'extracted' from THIS experiment, else
    'imputed' (covariate-conditioned KB estimate — only an estimate, so a candidate
    reason for any mismatch), else (None, 'default'). Geometry is not imputed."""
    v = _cond(exp, q, r)
    if v is not None:
        return v, "extracted"
    if impute:
        corpus, SC = _ctx()
        est = ks.impute(exp, q if isinstance(q, str) else q[0], r,
                        corpus=corpus, SC=SC)
        if est:
            return est["value"], "imputed"
    return None, "default"


# =============================================================================
# build_twin input-resolution transparency. Every model input's resolution is
# recorded INSIDE the resolution path (candidates, precedence, conversion, final
# value), captured on the SAME twin object used for the prediction (m.resolution_
# trace). Provenance CATEGORY and resolution OUTCOME are distinct and both kept.
# The frozen precursor-pressure precedence (pressure_compat) is preserved exactly.
# =============================================================================
RESOLUTION_OUTCOMES = ("directly_resolved", "resolved_with_conversion", "resolved_by_derivation",
                       "resolved_by_imputation", "resolved_by_default", "unresolved",
                       "conflicting_evidence")
PROVENANCE_CATEGORIES = ("literature_reported", "extracted", "derived", "imputed",
                         "model_default", "inverse_fitted", "unresolved")
_ONTO_QK = ({qk.get("id") for qk in _ONTO.get("quantity_kinds", [])}
            | {a for qk in _ONTO.get("quantity_kinds", []) for a in (qk.get("aliases") or [])})


def _onto_status(name):
    if name is None:
        return "model_specific_unresolved_mapping"
    return "ontology_supported" if name in _ONTO_QK else "not_represented_in_ontology"


def _cands(exp, q, r=None):
    """Every numeric controlled candidate for (quantity, reactant) with its source/unit."""
    out = []
    qs = (q,) if isinstance(q, str) else tuple(q)
    for cc in exp.get("controlled") or []:
        if cc.get("quantity") in qs and (r is None or cc.get("of_reactant") == r):
            v = cc.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append({"value": float(v), "unit": cc.get("unit"), "of_reactant": cc.get("of_reactant"),
                            "source": cc.get("source") or ((cc.get("origin") or {}).get("from")),
                            "card_status": (((cc.get("origin") or {}).get("card_provenance") or {}).get("status"))})
    return out


def _rec(canonical, canonical_path, attr, value, unit, display, provenance, outcome, **kw):
    return {"canonical": canonical, "canonical_path": canonical_path, "attr": attr, "value": value,
            "unit": unit, "display": display, "provenance": provenance, "outcome": outcome,
            "source": kw.get("source"), "selection_rule": kw.get("selection_rule"),
            "fallback_chain": kw.get("fallback_chain", []), "candidates": kw.get("candidates", []),
            "selected": kw.get("selected"), "reason_selected": kw.get("reason_selected"),
            "rejected": kw.get("rejected", []), "transform": kw.get("transform"),
            "role": kw.get("role", "fixed"), "assumption": kw.get("assumption", ""),
            "evidence_status": kw.get("evidence_status"),
            "ontology_support": kw.get("ontology_support", _onto_status(canonical))}


def _kb_rec(m, attr, canonical, unit, display, role="fixed", assumption="", ontology_support=None):
    """Resolution record for a from_kb-resolved model attribute, read from the twin's own
    kb_provenance (produced by kb_bridge.params_for at build time — not reconstructed)."""
    p = (getattr(m, "kb_provenance", {}) or {}).get(attr) or {}
    s = p.get("source")
    if s == "kb":
        prov, out = "literature_reported", ("resolved_with_conversion" if p.get("unit") else "directly_resolved")
        src = f"KB[{p.get('quantity')}]" + (f" refs {','.join(p.get('refs', []))}" if p.get("refs") else "")
        ev = f"n={p.get('n')}, sigma={p.get('sigma')}"
        transform = (f"{p.get('unit')} → SI" if p.get("unit") else None)
    elif s == "precursor":
        prov, out = "literature_reported", "resolved_with_conversion"
        src = f"precursor ontology.{p.get('property')} ({p.get('species')})"; ev = None
        transform = "ontology unit → SI"
    elif s == "material":
        prov, out = "literature_reported", "directly_resolved"
        src = f"material ontology.{p.get('property')}"; ev = None; transform = None
    else:
        prov, out = "model_default", "resolved_by_default"
        src = "channelModel default"; ev = None; transform = None
    if ontology_support is None:
        # precursor/material properties are ontology individuals (grounded even if not a quantity_kind id)
        ontology_support = "ontology_supported" if s in ("precursor", "material") else _onto_status(canonical)
    return _rec(canonical, f"KB/ontology[{canonical or attr}]", attr, getattr(m, attr), unit, display,
                prov, out, source=src, selection_rule="species/material ontology property > KB median > model default",
                fallback_chain=["precursor/material ontology property", "KB literature median", "model default"],
                candidates=[], selected=(s or "default"), reason_selected="params_for cascade (kb_bridge)",
                transform=transform, role=role, assumption=assumption, evidence_status=ev,
                ontology_support=ontology_support)


def build_twin(exp):
    """Construct a twin for this experiment. Process parameters (dose, T, pA, gpc) are taken
    from THIS experiment, else covariate-imputed from the KB, else the model default. Geometry
    (gap height H) is taken or assumed (never imputed). Returns the twin, notes, and
    `prov` = {input: state}. Also attaches `m.resolution_trace`: a full per-input resolution
    record captured inside this resolution path."""
    mat = exp.get("material")
    prec = next((r.get("species") for r in exp.get("reactants") or [] if r.get("role") == "precursor"), None)
    carrier = (exp.get("carrier_gas") or {}).get("species") or "N2"
    m = channelModel.from_kb(mat, species={"A": prec} if prec else None,
                             carrier=carrier, corpus=_ctx()[0])
    notes, prov, trace = [], {}, []
    from twin import pressure_compat as _pc

    # ---- pulse time t_p — precedence: A-extracted > A-imputed > B-extracted > B-imputed > default
    tp, prov["dose"] = _input(exp, "pulse_time", "A")
    slot = "A"
    if prov["dose"] == "default":
        tp, prov["dose"] = _input(exp, "pulse_time", "B")
        slot = "B" if prov["dose"] != "default" else "A"
    if tp:
        m.t_p = tp
    cA, cB = _cands(exp, "pulse_time", "A"), _cands(exp, "pulse_time", "B")
    conflict = len({round(x["value"], 9) for x in (cA if slot == "A" else cB)}) > 1
    tp_out = ("conflicting_evidence" if conflict else "directly_resolved" if prov["dose"] == "extracted"
              else "resolved_by_imputation" if prov["dose"] == "imputed" else "resolved_by_default")
    trace.append(_rec("pulse_time", f"controlled[pulse_time, of_reactant={slot}]", "t_p", m.t_p, "s",
        f"{m.t_p:.4g} s", _prov_cat(prov["dose"]), tp_out,
        source=("controlled" if prov["dose"] == "extracted" else "KB impute" if prov["dose"] == "imputed" else "model default"),
        selection_rule="A-extracted > A-imputed > B-extracted > B-imputed > model default",
        fallback_chain=["controlled[pulse_time,A]", "KB impute[pulse_time,A]", "controlled[pulse_time,B]",
                        "KB impute[pulse_time,B]", "model default"],
        candidates=[{**x, "slot": "A"} for x in cA] + [{**x, "slot": "B"} for x in cB],
        selected=f"{prov['dose']} (slot {slot})", reason_selected=f"first available by precedence",
        rejected=([{"value": x["value"], "reason": "same-slot alternate value (not selected)"} for x in (cA if slot == "A" else cB)[1:]]),
        role=("adjustable (calibration probe)" if prov["dose"] != "extracted" else "fixed"),
        assumption=("KB estimate (imputed)" if prov["dose"] == "imputed" else "model default t_p" if prov["dose"] == "default" else "")))

    # ---- temperature T — extracted > imputed > default; conversion °C → K
    T, prov["T"] = _input(exp, ("deposition_temperature", "temperature"))
    if T is not None:
        m.T = T + 273.15
    cT = _cands(exp, ("deposition_temperature", "temperature"))
    T_out = ("conflicting_evidence" if len({round(x["value"], 6) for x in cT}) > 1 else
             "resolved_with_conversion" if prov["T"] == "extracted" else
             "resolved_by_imputation" if prov["T"] == "imputed" else "resolved_by_default")
    trace.append(_rec("temperature", "controlled[temperature]", "T", m.T, "K", f"{m.T-273.15:.4g} °C",
        _prov_cat(prov["T"]), T_out, source=("controlled" if prov["T"] == "extracted" else "KB impute" if prov["T"] == "imputed" else "default"),
        selection_rule="extracted > KB impute > model default", candidates=cT,
        fallback_chain=["controlled[temperature]", "KB impute[temperature]", "model default"],
        selected=prov["T"], reason_selected="first available by precedence",
        rejected=[{"value": x["value"], "reason": "alternate value (not selected)"} for x in cT[1:]],
        transform=("+273.15 (°C → K)" if prov["T"] != "default" else None),
        assumption=("KB estimate (imputed)" if prov["T"] == "imputed" else "")))

    # ---- precursor partial pressure pA — FROZEN pressure_compat precedence, then impute, then default
    _pav, _pac = _pc.precursor_pressure(exp)
    if _pav is not None:
        pA, prov["pA"] = _pav, "extracted"
    else:
        pA, prov["pA"] = _input(exp, "partial_pressure", "A")
    if pA:
        m.pA = pA
    press_cands = []
    for cc in exp.get("controlled") or []:
        q = cc.get("quantity")
        v = cc.get("value")
        if q and "pressure" in q and isinstance(v, (int, float)) and not isinstance(v, bool):
            accepted = (q in _pc.PRECURSOR_PRESSURE_QUANTITIES and _pc._slot_ok(q, cc.get("of_reactant"), "A"))
            status = ("accepted" if accepted else "rejected: forbidden type"
                      if q in _pc.FORBIDDEN_FOR_PARTIAL else "rejected: wrong type/slot")
            press_cands.append({"value": float(v), "unit": cc.get("unit"), "quantity": q,
                                "of_reactant": cc.get("of_reactant"), "acceptance": status})
    pA_out = ("directly_resolved" if prov["pA"] == "extracted" else
              "resolved_by_imputation" if prov["pA"] == "imputed" else "resolved_by_default")
    trace.append(_rec("precursor_partial_pressure",
        f"controlled[{(_pac or {}).get('quantity', 'precursor_partial_pressure')}, of_reactant=A]", "pA", m.pA, "Pa",
        f"{m.pA:.4g} Pa", _prov_cat(prov["pA"]), pA_out,
        source=(f"pressure_compat:{(_pac or {}).get('quantity')}" if prov["pA"] == "extracted"
                else "KB impute[partial_pressure,A]" if prov["pA"] == "imputed" else "model default pA=100 Pa"),
        selection_rule="FROZEN: precursor_partial_pressure > reactant_A_partial_pressure > partial_pressure "
                       "(forbidden types excluded) > KB impute > model default",
        fallback_chain=list(_pc.PRECURSOR_PRESSURE_QUANTITIES) + ["KB impute[partial_pressure,A]", "model default"],
        candidates=press_cands, selected=((_pac or {}).get("quantity") if prov["pA"] == "extracted" else prov["pA"]),
        reason_selected=("typed precursor partial pressure accepted by frozen precedence" if prov["pA"] == "extracted"
                         else "no accepted typed precursor pressure; " + prov["pA"]),
        rejected=[{"value": c["value"], "reason": c["acceptance"]} for c in press_cands if c["acceptance"].startswith("rejected")],
        assumption=("KB estimate (imputed)" if prov["pA"] == "imputed" else "model default pA=100 Pa" if prov["pA"] == "default" else "")))

    # ---- growth per cycle gpc — extracted > imputed > default; conversion nm → m
    gpc, prov["gpc"] = _input(exp, "growth_per_cycle")
    if gpc:
        m.gpc = gpc * NM
    cG = _cands(exp, "growth_per_cycle")
    g_out = ("resolved_with_conversion" if prov["gpc"] == "extracted" else
             "resolved_by_imputation" if prov["gpc"] == "imputed" else "resolved_by_default")
    trace.append(_rec("growth_per_cycle", "controlled[growth_per_cycle]", "gpc", m.gpc, "m",
        f"{m.gpc*1e9:.4g} nm/cyc", _prov_cat(prov["gpc"]), g_out,
        source=("controlled" if prov["gpc"] == "extracted" else "KB impute" if prov["gpc"] == "imputed" else "default"),
        selection_rule="extracted > KB impute > model default", candidates=cG,
        fallback_chain=["controlled[growth_per_cycle]", "KB impute[growth_per_cycle]", "model default"],
        selected=prov["gpc"], reason_selected="first available by precedence",
        transform=("×1e-9 (nm → m)" if prov["gpc"] != "default" else None),
        assumption=("KB estimate (imputed)" if prov["gpc"] == "imputed" else "")))

    # ---- gap height H — extracted (plausibility-checked, NOT imputed) else default; nm → m
    H, _ = _input(exp, "feature_height", impute=False)
    Hm = H * NM if H else None
    rej_H = []
    if Hm and PLAUSIBLE_GAP_M[0] <= Hm <= PLAUSIBLE_GAP_M[1]:
        m.H = Hm; prov["H"] = "extracted"; H_out = "resolved_with_conversion"
    else:
        prov["H"] = "default"; H_out = "resolved_by_default"; m.H = DEFAULT_H
        if Hm:
            rej_H = [{"value": H, "reason": f"out of plausible gap range [{PLAUSIBLE_GAP_M[0]*1e9:g},{PLAUSIBLE_GAP_M[1]*1e9:g}] nm"}]
            notes.append(f"feature_height {H:g} nm out of gap range → assumed {DEFAULT_H*1e6:g} µm")
        else:
            notes.append(f"no feature_height → assumed {DEFAULT_H*1e6:g} µm gap")
    trace.append(_rec("feature_height", "controlled[feature_height]", "H", m.H, "m", f"{m.H*1e6:.4g} µm",
        _prov_cat(prov["H"]), H_out, source=("controlled" if prov["H"] == "extracted" else "model default gap"),
        selection_rule="extracted-in-plausible-range (NOT imputed — structure-specific) > model default",
        fallback_chain=["controlled[feature_height] within plausible gap range", "model default DEFAULT_H"],
        candidates=_cands(exp, "feature_height"), selected=prov["H"],
        reason_selected=("extracted, within plausible gap range" if prov["H"] == "extracted" else "no accepted extracted value → default"),
        rejected=rej_H, transform=("×1e-9 (nm → m)" if prov["H"] == "extracted" else None),
        assumption=("assumed default gap (not extracted)" if prov["H"] == "default" else "")))

    # ---- channel width W — extracted (must exceed H) else default; nm → m
    W, _ = _input(exp, "feature_width", impute=False)
    if W and W * NM > m.H:
        m.W = W * NM; W_prov, W_out, W_rej = "extracted", "resolved_with_conversion", []
    else:
        m.W = DEFAULT_W; W_prov, W_out = "default", "resolved_by_default"
        W_rej = ([{"value": W, "reason": "not greater than gap height H"}] if W else [])
    trace.append(_rec("feature_width", "controlled[feature_width]", "W", m.W, "m", f"{m.W*1e3:.4g} mm",
        _prov_cat(W_prov), W_out, source=("controlled" if W_prov == "extracted" else "model default width"),
        selection_rule="extracted feature_width (must exceed gap height H) > model default",
        fallback_chain=["controlled[feature_width] with width > H", "model default DEFAULT_W"],
        candidates=_cands(exp, "feature_width"), selected=W_prov, rejected=W_rej,
        transform=("×1e-9 (nm → m)" if W_prov == "extracted" else None)))

    # ---- from_kb-resolved model coefficients / species properties (kb_provenance) ----
    trace.append(_kb_rec(m, "c", None, "dimensionless", f"{m.c:.4g}",
        role="fixed in forward prediction; adjustable in calibration probe",
        assumption=f"{C_LABEL}; ontology mapping to sticking_probability: {C_ONTOLOGY_STATUS}",
        ontology_support="model_specific_unresolved_mapping"))
    trace.append(_kb_rec(m, "K", "adsorption_rate_constant", "1/Pa", f"{m.K:.4g} 1/Pa"))
    trace.append(_kb_rec(m, "da", "molecular_diameter", "m", f"{m.da*1e12:.4g} pm"))
    trace.append(_kb_rec(m, "MA", "molecular_mass", "kg/mol", f"{m.MA*1e3:.4g} g/mol"))

    # ---- derived exposure ----
    trace.append(_rec(None, "derived", "exposure", m.pA * m.t_p, "Pa·s", f"{m.pA*m.t_p:.4g} Pa·s",
        "derived", "resolved_by_derivation", source="pA × t_p",
        selection_rule="derivation from pA and t_p", fallback_chain=["pA × t_p"],
        selected="derived", reason_selected="exposure = pA × t_p",
        role=("adjustable via t_p" if prov["dose"] != "extracted" else "fixed"),
        assumption="DERIVED from pA and t_p; never independently fitted",
        ontology_support="derived"))

    for k in ("dose", "T", "pA", "gpc"):
        if prov[k] == "imputed":
            notes.append(f"{k} imputed (KB estimate)")
    m.resolution_trace = trace
    return m, notes, prov


def measured_profile(exp):
    """(x_µm, y_norm) of a mouth-to-tail conformality profile: x from the channel
    mouth (≥0), y normalised to the mouth plateau. Returns None if it isn't a
    standard decaying profile (guards degenerate / inverted / flat extractions)."""
    pts = sorted([p for p in (exp.get("points") or []) if p and p[0] is not None and p[1] is not None])
    pts = [(x, y) for x, y in pts if x >= 0]
    if len(pts) < 6:
        return None
    ys_raw = [y for _, y in pts]
    k = max(1, len(pts) // 10)
    plateau = sum(ys_raw[:k]) / k                        # mean of the first ~10% (mouth)
    ymax = max(ys_raw)
    tail = sum(ys_raw[-k:]) / k
    # must be a real decaying profile: mouth near the max, tail well below the mouth
    if plateau <= 0 or plateau < 0.6 * ymax or tail > 0.6 * plateau:
        return None
    xs = [x for x, _ in pts]
    ys = [max(y, 0.0) / plateau for _, y in pts]
    return xs, ys


def pd50(xs, ys):
    """Half-thickness penetration: x where the (normalised) profile crosses 0.5."""
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), list(zip(xs, ys))[1:]):
        if (y0 - 0.5) * (y1 - 0.5) <= 0 and y1 != y0:
            return x0 + (0.5 - y0) * (x1 - x0) / (y1 - y0)
    return None


DRIVERS = ["dose", "H"]          # the inputs that set absolute penetration


def _is_thermal(exp):
    """The Ylilammi twin models THERMAL, precursor-diffusion-limited ALD. Plasma
    (PEALD) conformality is recombination-limited — a different physical model
    (Arts/Aguinsky), so those profiles are out of this twin's scope."""
    pt = (exp.get("process_type") or "").lower()
    return "plasma" not in pt and "peald" not in pt


# =============================================================================
# M3 redesign — one discovery-support run: framing → scoping → per-comparison
# → ENSEMBLE BARRIER → patterns/diagnosability → scientific interpretation →
# EVIDENCE CLOSURE → inquiry → FREEZE → Interpretation Brief.
# It ORGANIZES and PROPOSES; it never concludes. Every emitted claim carries a
# machine-readable epistemic status. The forward-model primitives above
# (build_twin, measured_profile, pd50, inverse_fit, curve_metrics, figures) are
# reused unchanged. Legacy verdict/report code below is kept DORMANT.
# =============================================================================

# ---- R0: closed epistemic-status vocabulary (every emitted claim carries one) ----
STATUS = ("observation", "model_prediction", "comparison_result", "assumption",
          "supported_interpretation", "challenged_interpretation",
          "candidate_explanation", "alternative_explanation", "insight",
          "open_question", "discriminating_question", "evidence_needed",
          "preserved_anomaly", "non_comparable", "insufficient_evidence",
          "calibration_datum", "unresolved", "untested_region")
# statuses M3 must NEVER emit in its own voice (finality / discovery / validation)
FORBIDDEN_STATUS = ("proven", "true", "false", "discovered", "new_physics_confirmed",
                    "definitively_caused_by", "fully_validated", "validated",
                    "verified", "confirmed", "refuted", "established",
                    "model_correct", "model_wrong", "causally_determined")
# the six co-equal explanatory loci — the model is one of six, never the default suspect
LOCI = ("model_structure", "parameterization", "auxiliary_assumptions",
        "measurement", "extraction", "ontology")


def _valid_status(s):
    return s in STATUS and s not in FORBIDDEN_STATUS


# ---- R1: framing + scoping ---------------------------------------------------
DEFAULT_QUESTION = ("Does the KB-parameterised Ylilammi channel twin reproduce the measured "
                    "conformality profile (normalised thickness vs depth; PD50) for in-scope "
                    "thermal lateral-channel ALD experiments in the current corpus?")

# comparability criteria = observable-based membership predicate (reproduces the legacy
# candidate set exactly) + the model's declared validity domain (used for coverage/untested
# and for the commensurability gate).
DEFAULT_CRITERIA = {
    "observable": {"measurand": ("film_thickness", "normalized_thickness"),
                   "coordinate": "spatial_coordinate", "granularity": "profile",
                   "relevance": "experimental", "min_points": 6,
                   "definition": "mouth-to-tail normalised conformality profile on an absolute-distance "
                                 "axis; PD50 = depth at 50% of the mouth thickness"},
    "model_validity": {"geometry": tuple(TWIN_GEOMETRY), "thermal_only": True},
}


def _member(exp, crit):
    o = crit["observable"]
    return (exp.get("granularity") == o["granularity"]
            and exp.get("relevance") == o["relevance"]
            and (exp.get("measurand") or {}).get("quantity") in o["measurand"]
            and exp.get("coordinate") == o["coordinate"]
            and bool(exp.get("points")) and len(exp["points"]) >= o["min_points"])


_FUNNEL = _EXCLUSIONS = None


def _targets(criteria=DEFAULT_CRITERIA):
    """Candidate ensemble from the PRODUCTION semantic corpus.

    Membership is by representation reachability under the Workbench's own
    identity/comparability authority (semantic_evidence.profile_candidates):
    measured ResultSeries whose x reaches the spatial-coordinate target and
    whose y reaches a thickness-family observable, one representation per
    MeasurementAct, with a resolved single Condition Case. The legacy
    granularity/measurand fields on resolved Experiment records are not
    consulted. Model-domain (geometry/thermal) stays a separate,
    reported commensurability gate."""
    global _FUNNEL, _EXCLUSIONS
    from twin import semantic_evidence as SE
    cands, _FUNNEL, _EXCLUSIONS = SE.profile_candidates()
    o = criteria["observable"]
    return [c for c in cands if len(c.get("points") or []) >= o["min_points"]]


def _coverage(targets, criteria=DEFAULT_CRITERIA):
    """Census over candidates + untested regions (model-valid geometry buckets with zero
    candidates). Descriptive; uses candidates only, never outcome."""
    from collections import Counter
    by_geo = Counter(e.get("geometry_class") for e in targets)
    by_mat = Counter(e.get("material") for e in targets)
    by_src = Counter(_paper_of(e) for e in targets)
    valid_geo = criteria["model_validity"]["geometry"]
    untested = [{"dimension": "geometry_class", "value": g, "status": "untested_region",
                 "note": f"model-valid geometry '{g}' has no candidate profile in the corpus"}
                for g in valid_geo if by_geo.get(g, 0) == 0]
    return {"n_candidates": len(targets), "by_geometry_class": dict(by_geo),
            "by_material": dict(by_mat), "by_source": dict(by_src),
            "n_sources": len(by_src), "untested_regions": untested}


def _frame(question, criteria, targets, is_default):
    cov = _coverage(targets, criteria)
    from twin import semantic_evidence as SE
    from collections import Counter as _Counter
    excl = _EXCLUSIONS or []
    return {"research_question": question, "is_default": bool(is_default),
            "comparability_criteria": criteria, "coverage": cov,
            "untested_regions": cov["untested_regions"],
            # what the twin was and was not validated against, stage by stage
            "candidate_funnel": dict(_FUNNEL or {}),
            "exclusions_by_stage": dict(_Counter(e["stage"] for e in excl)),
            "exclusions": excl,
            "corpus": SE.corpus_meta()}


# ---- R2: refuse-first commensurability + provenance --------------------------
def _commensurability(exp, criteria=DEFAULT_CRITERIA):
    """Is this pairing a meaningful comparison for the twin? Observable equivalence is
    guaranteed by membership; here we test the model's VALIDITY DOMAIN (geometry + thermal).
    A non-comparable pairing is refused as a test and yields a boundary open-question
    instead. Returns (verdict, reasons, boundary_question)."""
    reasons, bq = [], None
    gc = exp.get("geometry_class")
    valid_geo = criteria["model_validity"]["geometry"]
    geom_ok = (gc is None) or (not valid_geo) or (gc in valid_geo)
    thermal = _is_thermal(exp)
    if not geom_ok:
        reasons.append({"code": "geometry_out_of_domain",
                        "detail": f"geometry_class '{gc}' is outside the {MODEL_ID} validity domain {list(valid_geo)}"})
        bq = {"status": "open_question", "provenance": "m3_generated_question", "kind": "domain_boundary",
              "text": f"Where does the twin's applicability end for '{gc}' geometry? A {gc}-specific transport "
                      f"model would be needed before a comparison here is meaningful."}
    if not thermal:
        reasons.append({"code": "regime_out_of_domain",
                        "detail": "plasma / recombination-limited process; the thermal precursor-diffusion twin does not model it"})
        bq = {"status": "open_question", "provenance": "m3_generated_question", "kind": "domain_boundary",
              "text": "Plasma conformality is recombination-limited; a recombination model (e.g. Arts/Aguinsky) "
                      "would be needed before a comparison here is meaningful."}
    verdict = "admissible" if (geom_ok and thermal) else "non_comparable"
    return verdict, reasons, bq


def _obs_provenance(exp):
    """Provenance of the measured profile AS EVIDENCE — a fallible extraction, NOT ground
    truth. Reads the record's own provenance + per-value extraction metadata. The corpus
    carries no measurement uncertainty and no calibration flag, so both stay unresolved."""
    p = exp.get("provenance") or {}
    classes = sorted({c.get("condition_class") for c in exp.get("controlled") or []
                      if c.get("condition_class")})
    return {"doi": p.get("doi"), "figure": p.get("figure"), "panel": p.get("panel"),
            "series_label": p.get("series_label"),
            "result_series": p.get("series_id") or exp.get("series_id"),
            "measurement_act": p.get("measurement_act") or exp.get("act_id"),
            "experimental_case": p.get("case_id") or exp.get("case_id"),
            "extractor": p.get("extractor"),
            "condition_evidence_classes": classes or ["unspecified"],
            "calibration_status": "unresolved",          # no calibration flag in the corpus
            "measurement_uncertainty": "unresolved"}     # no measurement σ in the corpus


# ---- R3: combined tolerance + test severity ----------------------------------
_MODEL_SIGMA_PARAMS = ("H", "T", "W", "gpc")


def _combined_tolerance(twin):
    """Assemble the combined-uncertainty budget from what the evidence actually has: model
    σ from the twin's KB provenance (geometry/T), and measurement/input σ that are ABSENT in
    the corpus (→ unresolved). Missing measurement σ is why quantitative agreement stays
    insufficient_evidence — it is NOT fabricated."""
    prov = getattr(twin, "kb_provenance", {}) or {}
    model_sigma = {p: prov[p].get("sigma") for p in _MODEL_SIGMA_PARAMS
                   if prov.get(p, {}).get("source") == "kb" and prov.get(p, {}).get("sigma")}
    return {"model_sigma": {k: float(v) for k, v in model_sigma.items()},
            "model_sigma_available": bool(model_sigma),
            "measurement_sigma": "unresolved", "input_sigma": "unresolved",
            "note": "no measurement uncertainty is extracted in the corpus; agreement cannot be "
                    "made uncertainty-relative"}


def _severity(xm, ym):
    """How much could this comparison have failed? A descriptive per-comparison severity
    from the profile's dynamic range and point count. It is capped LOW / non-quantitative
    because no measurement uncertainty exists to calibrate it."""
    dyn = (max(ym) - min(ym)) if ym else 0.0
    npts = len(xm) if xm else 0
    if npts < 8 or dyn < 0.5:
        level, basis = "low", "few points or small dynamic range — the observable barely varies here"
    else:
        level, basis = "moderate", "the profile has real dynamic range, but severity is not quantitative " \
                                   "without measurement uncertainty"
    return {"level": level, "basis": basis, "dynamic_range": round(float(dyn), 3),
            "n_points": npts, "quantitative": False}


def validate_one(exp, criteria=DEFAULT_CRITERIA):
    """Phase 2 — one per-comparison assessment (alignment → commensurability gate →
    comparison evaluation). REFUSE-FIRST: a non-comparable pairing is never scored as a
    test. Produces per-comparison FACTS + provenance + a machine-readable status; it does
    NOT attribute cause or interpret (those are ensemble-level, after the barrier). Legacy
    verdict fields are computed for admissible comparisons and kept DORMANT."""
    meas = measured_profile(exp)
    if not meas:
        return None
    xm, ym = meas
    twin, notes, prov = build_twin(exp)
    obs_prov = _obs_provenance(exp)
    verdict, reasons, bq = _commensurability(exp, criteria)

    base = {"exp_id": exp.get("exp_id"), "material": exp.get("material"),
            "paper": _paper_of(exp),
            "geometry_class": exp.get("geometry_class"), "thermal": _is_thermal(exp),
            "observation_provenance": obs_prov, "prov": prov, "notes": notes,
            "measured": sorted(k for k, s in prov.items() if s == "extracted"),
            "imputed": sorted(k for k, s in prov.items() if s == "imputed"),
            "commensurability": {"verdict": verdict, "reasons": reasons},
            "_meas": (xm, ym)}

    if verdict == "non_comparable":                     # refuse-first: never scored as a test
        base.update({"status": "non_comparable", "boundary_question": bq,
                     "r2": None, "nrmse": None, "overlap": None,
                     "pd_meas": None, "pd_twin": None, "pd_rel": None, "_twin": ([], []),
                     "combined_tolerance": None, "severity": None,
                     "quantitative_agreement_status": None, "shape_fit": None})
        return base

    # --- admissible: comparison evaluation ---
    xg = np.linspace(0, max(xm) * 1e-6, 300)
    twin.prepare()
    th, _, _ = twin.approx(xg, np.zeros_like(xg))
    t0 = th[0] if th[0] > 0 else (th.max() or 1)
    xt_um = list(xg * 1e6)
    yt = list(np.clip(th / t0, 0, None))
    cm = sim.curve_metrics(xm, ym, xt_um, yt)
    pd_m, pd_t = pd50(xm, ym), pd50(xt_um, yt)
    dpd = abs(pd_m - pd_t) if (pd_m and pd_t) else None
    rel = (dpd / pd_m) if (dpd and pd_m) else None
    r2 = cm.get("r2") if cm else None
    tol = _combined_tolerance(twin)
    # descriptive SHAPE agreement (not truth, not uncertainty-relative)
    shape = ("close" if (r2 is not None and r2 >= 0.9) else
             "partial" if (r2 is not None and r2 >= 0.5) else "poor")

    # legacy verdict (DORMANT — retained for migration; not rendered by the Brief)
    dstates = [prov.get(k) for k in DRIVERS]
    if r2 is not None and r2 >= 0.5 and (rel is None or rel <= 0.3):
        lverdict, lkind, lagree = "agrees", None, True
    elif "default" in dstates:
        lverdict, lkind, lagree = "data gap", f"assumed {', '.join(k for k in DRIVERS if prov.get(k)=='default')}", False
    elif "imputed" in dstates:
        lverdict, lkind, lagree = "estimation gap", f"{', '.join(k for k in DRIVERS if prov.get(k)=='imputed')} imputed", False
    else:
        lverdict, lkind, lagree = "model gap", "dose+gap measured, twin still misses", False

    dose_free = prov.get("dose") != "extracted"
    base.update({"status": "comparison_result",
                 "r2": r2, "nrmse": cm.get("nrmse") if cm else None,
                 "overlap": cm.get("overlap") if cm else None,
                 "pd_meas": pd_m, "pd_twin": pd_t, "pd_rel": rel,
                 "combined_tolerance": tol, "severity": _severity(xm, ym),
                 "quantitative_agreement_status": "insufficient_evidence",  # measurement σ unresolved
                 "shape_fit": shape,
                 "t_p": twin.t_p, "T": twin.T - 273.15, "H_um": twin.H * 1e6,
                 # runtime resolution trace, captured on the SAME twin used to predict
                 "model_resolution_trace": twin.resolution_trace,
                 "model_input_trace": twin.resolution_trace,   # alias: value table reads the same records
                 "dose_free": dose_free, "predicted_pd50_um": pd_t,
                 "_twin": (xt_um, yt),
                 "verdict": lverdict, "kind": lkind, "agree": lagree})  # dormant legacy
    return base


# ---- R4: ensemble patterns + diagnosability (after the barrier) --------------
def _paper_of(exp):
    """The paper an experiment belongs to, from its own field.

    This used to be `exp_id.split("-")[0]`, which silently truncated every
    hyphenated DOI (10.1007_s11671-010-9676-0 -> "10.1007_s11671") and broke
    outright once ids became figure-anchored. The record carries the paper; read
    it."""
    return (exp.get("paper_id") or exp.get("doi")
            or (exp.get("provenance") or {}).get("paper_id") or "unknown")


def _ensemble_patterns(admissible):
    from collections import Counter
    n = len(admissible)
    by_src = Counter(r["paper"] for r in admissible)
    by_geo = Counter(r["geometry_class"] for r in admissible)
    shapes = Counter(r.get("shape_fit") for r in admissible)
    signs = [(r["pd_twin"] - r["pd_meas"]) for r in admissible if r.get("pd_meas") and r.get("pd_twin")]
    n_under = sum(1 for s in signs if s < 0)
    n_over = sum(1 for s in signs if s > 0)
    bias = ("predicts-shallower" if n_under > 1.5 * max(1, n_over) else
            "predicts-deeper" if n_over > 1.5 * max(1, n_under) else "mixed")
    return {"n": n, "by_source": dict(by_src), "n_sources": len(by_src),
            "by_geometry": dict(by_geo), "shape_fit": dict(shapes),
            "pd_bias": {"direction": bias, "n_shallower": n_under, "n_deeper": n_over}}


def _diagnosability(patterns):
    """Given the ensemble structure, can explanatory loci be separated? With one source
    dominating, source/extraction systematics cannot be told apart from model or parameter
    behaviour — this is stated, not hidden."""
    n = patterns["n"]
    by_src = patterns["by_source"]
    dom = max(by_src.values()) if by_src else 0
    dom_frac = (dom / n) if n else 0.0
    dom_src = max(by_src, key=by_src.get) if by_src else "—"
    single_source = patterns["n_sources"] <= 1 or dom_frac >= 0.7
    if single_source:
        verdict = "weak"
        basis = (f"{dom}/{n} admissible comparisons come from a single source ({dom_src}); "
                 f"source / extraction / lab systematics cannot be separated from model or "
                 f"parameter behaviour with this ensemble")
        unresolved = [{"status": "unresolved",
                       "detail": "isolated-vs-systematic and measurement-vs-model attributions are not "
                                 "separable from single-source systematics; a unique cause cannot be assigned"}]
    else:
        verdict = "limited"
        basis = f"{patterns['n_sources']} sources; limited cross-source separation is possible but the ensemble is small"
        unresolved = [{"status": "unresolved",
                       "detail": "the ensemble is small; attributions remain provisional"}]
    return {"verdict": verdict, "basis": basis, "dominant_source": dom_src,
            "dominant_source_fraction": round(dom_frac, 2), "n_sources": patterns["n_sources"],
            "unresolved_attributions": unresolved}


# =============================================================================
# ARCHITECTURAL TODO (documented technical debt — DO NOT IMPLEMENT HERE) ·······
# -----------------------------------------------------------------------------
# Make the M3 report FULLY EVIDENCE-DERIVED instead of TEMPLATE-DERIVED.
#
# The report is already deterministic (no LLM call), which is good. But several
# scientific statements are still emitted from manually-authored templates /
# fixed registries rather than being derived from evidence. Known examples:
#   · _global_assumptions() emits a FIXED assumption list;
#   · _explanation_space() / the six loci are largely TEMPLATE-driven;
#   · several interpretation sentences are PRE-AUTHORED and only interpolate
#     runtime numbers.
# Maintenance problem: if extraction coverage improves, the ontology changes,
# new evidence types appear, or the model evolves, the report logic will NOT
# adapt automatically — the templates themselves must be edited. Not desired.
#
# Long-term principle — every scientific statement in the report should be a
# DETERMINISTIC CONSEQUENCE of:
#     extracted evidence + runtime model-resolution trace + ontology state
#     + numerical results + explicit scientific rules
# NOT of manually-authored templates.
#
# Future architecture — each emitted statement should carry: origin, rule_id,
# trigger condition, evidence references, affected conclusions, discharge
# condition. Statements (assumptions, explanation loci) become active ONLY when
# their triggering evidence exists, and DISCHARGE automatically when it changes.
#   Example — claim `kinetics_are_model_defaults`:
#     origin   = runtime resolution trace
#     trigger  = provenance(c)==model_default OR provenance(K)==model_default
#                OR provenance(gpc)==model_default
#     evidence = the run-level model-resolution/provenance summary
#     discharge= disappears automatically once those parameters resolve from
#                accepted evidence.
#
# STATUS: architectural TODO only. Do NOT change current behavior in this task;
# this note is preserved so a future refactor can move report generation toward
# a fully evidence-derived scientific reporting engine.
# =============================================================================
# ---- R5: scientific interpretation (plural, non-exclusive, never a conclusion) ----
def _dependency_assumptions(r):
    a = []
    if r["prov"].get("H") == "default":
        a.append("gap height H is assumed (not extracted)")
    for k in r.get("imputed", []):
        a.append(f"{k} is a KB estimate (imputed), not measured")
    a.append("twin kinetics (sticking c, adsorption K, GPC) are model defaults — not chemistry-specific")
    a.append("measurement uncertainty is unresolved (not extracted)")
    a.append("calibration provenance is unresolved (literature kinetics may have been fit on such profiles)")
    a.append("observable equivalence assumed: the model's PD50 / normalised profile ≡ the extracted profile definition")
    return a


def _explanation_space(r, inv):
    """Plural, non-exclusive candidate explanations for a discrepancy across the six
    co-equal loci. None is selected. Testability is annotated. `inv` = inverse_fit."""
    recovered = bool(inv and (inv["r2_fit"] - inv["r2_warm"] > 0.05) and inv["r2_fit"] >= 0.7)
    exps = []
    exps.append({"status": "candidate_explanation", "locus": "parameterization",
                 "evidence_for": (f"a bounded change to the pulse time t_p (where adjustable) and the "
                                  f"model-specific lumped coefficient c recovers the profile "
                                  f"(R² {inv['r2_warm']:.2f}→{inv['r2_fit']:.2f}; feasible fit, not a unique estimate)"
                                  if inv else
                                  "twin kinetics are model defaults, free to be off for this chemistry"),
                 "evidence_against": ("" if recovered or not inv else
                                      "even a fitted parameter change does not fully recover the profile"),
                 "testability": "chemistry-specific sticking c / GPC with provenance would test this"})
    if r.get("imputed") or r["prov"].get("dose") != "extracted" or r["prov"].get("H") == "default":
        exps.append({"status": "candidate_explanation", "locus": "auxiliary_assumptions",
                     "evidence_for": f"penetration-setting inputs are assumed/imputed (imputed={r.get('imputed') or []}, "
                                     f"H={r['prov'].get('H')})",
                     "evidence_against": "", "testability": "measuring dose and gap height for this experiment would test this"})
    exps.append({"status": "candidate_explanation", "locus": "measurement",
                 "evidence_for": f"the profile is an extraction ({r['observation_provenance'].get('extractor')}) "
                                 f"with no reported uncertainty",
                 "evidence_against": "", "testability": "an independent measurement of the same feature would test this"})
    exps.append({"status": "candidate_explanation", "locus": "extraction",
                 "evidence_for": "the profile was digitised from a figure by an automated extractor; digitisation error is possible",
                 "evidence_against": "", "testability": "re-extraction or author-provided raw data would test this"})
    exps.append({"status": "candidate_explanation", "locus": "ontology",
                 "evidence_for": "the observable / geometry mapping (what PD50 means here, geometry_class) is assumed commensurable",
                 "evidence_against": "", "testability": "checking the source's profile definition against the model's would test this"})
    exps.append({"status": "candidate_explanation" if not recovered else "alternative_explanation",
                 "locus": "model_structure",
                 "evidence_for": ("a fitted parameter change does not recover the profile, so the Ylilammi structure "
                                  "may be inadequate here" if not recovered else
                                  "the Ylilammi structure is one possible account, but a parameter change already fits"),
                 "evidence_against": ("a parameter change already recovers the profile" if recovered else ""),
                 "testability": "an independent-source profile at matched conditions would help separate structure from parameters"})
    return exps, recovered


def _interpret_one(r, inv, diagn):
    """A supported or challenged interpretation for one admissible comparison, carrying the
    mandatory bundle, plus its plural explanation space. Never a conclusion."""
    dep = _dependency_assumptions(r)
    scope = f"{r['material']} / {r.get('geometry_class')} / this single experiment ({r['exp_id']})"
    sev = (r.get("severity") or {}).get("level", "low")
    exps, recovered = _explanation_space(r, inv)
    if r.get("shape_fit") == "close":
        interp = {"status": "supported_interpretation", "exp_id": r["exp_id"],
                  "claim": "the twin reproduces the observed conformality profile SHAPE for this experiment",
                  "support_basis": f"descriptive shape agreement (R²={r['r2']:.2f}); NOT uncertainty-relative "
                                   f"(measurement σ unresolved → quantitative agreement is insufficient_evidence)",
                  "scope": scope, "test_severity": sev, "dependency_assumptions": dep,
                  "alternatives_remaining_open": [
                      "compensating errors could yield shape agreement for the wrong reasons",
                      "single-source systematics are not separable (see diagnosability)",
                      "measurement / extraction fidelity is unverified"]}
    else:
        rel_s = ("%.0f%%" % (r["pd_rel"] * 100)) if r.get("pd_rel") is not None else "—"
        interp = {"status": "challenged_interpretation", "exp_id": r["exp_id"],
                  "claim": "the twin does not reproduce the observed profile for this experiment",
                  "challenge_basis": f"descriptive shape disagreement (R²={r['r2']:.2f}, ΔPD50 rel={rel_s})",
                  "scope": scope, "test_severity": sev, "dependency_assumptions": dep,
                  "alternatives_remaining_open": [e["locus"] for e in exps]}
    return interp, exps, recovered


def _preserved_anomaly(r, exps, recovered, diagn):
    """A robust discrepancy that no testable explanation accommodates, kept OPEN rather than
    explained away. A preserved anomaly requires that mundane explanations be ruled OUT — which
    needs cross-corroborating, independent evidence. Under WEAK diagnosability (e.g. single-
    source), that robustness cannot be established, so NO anomaly is declared; such discrepancies
    remain visible as challenged + unresolved instead (they are not explained away, and they are
    not over-claimed as anomalies)."""
    if diagn.get("verdict") == "weak":
        return None
    if r.get("shape_fit") == "poor" and not recovered:
        return {"status": "preserved_anomaly", "exp_id": r["exp_id"],
                "detail": (f"the profile is not reproduced (R²={r['r2']:.2f}) and a fitted parameter change does "
                           f"not recover it; no single testable explanation accommodates it — preserved, not "
                           f"explained away"),
                "live_explanations": [e["locus"] for e in exps]}
    return None


def _global_assumptions(frame):
    cov = frame["coverage"]
    dom = max(cov["by_source"].values()) if cov["by_source"] else 0
    return [
        {"status": "assumption", "name": "kinetics_are_model_defaults",
         "detail": "sticking c, adsorption K and GPC come from the twin's built-in defaults, not chemistry-specific measurements",
         "affects": "every prediction's absolute penetration, and the parameterization explanation"},
        {"status": "assumption", "name": "measurement_uncertainty_unresolved",
         "detail": "no measurement σ is extracted in the corpus",
         "affects": "quantitative agreement (kept insufficient_evidence) and test severity"},
        {"status": "assumption", "name": "calibration_provenance_unresolved",
         "detail": "whether the literature kinetics were fit on these very profiles is unknown",
         "affects": "possible calibration circularity; out-of-sample status cannot be certified"},
        {"status": "assumption", "name": "observable_equivalence",
         "detail": "the model's PD50 / normalised-thickness profile is assumed to mean the same as each extracted profile",
         "affects": "the commensurability of every comparison"},
        {"status": "assumption", "name": "single_source_dominance",
         "detail": f"{dom} of {cov['n_candidates']} candidate profiles come from one source",
         "affects": "diagnosability (weak) and every attribution"},
    ]


# ---- EVIDENCE CLOSURE --------------------------------------------------------
CLOSURE_STATEMENT = ("No additional interpretation may be extracted from the current evidence "
                     "without introducing new evidence, new assumptions, or researcher judgment.")


def _evidence_closure(comparisons, admissible, interps, exps_all, assumptions, preserved,
                      frame, diagn, insights):
    supports = [i for i in interps if i["status"] == "supported_interpretation"]
    challenges = [i for i in interps if i["status"] == "challenged_interpretation"]
    non_comparable = [c for c in comparisons if c["status"] == "non_comparable"]
    insufficient = [c["exp_id"] for c in admissible if c.get("quantitative_agreement_status") == "insufficient_evidence"]
    live = sorted({e["locus"] for exps in exps_all for e in exps})
    return {"supports": supports, "challenges": challenges, "insights": insights,
            "unresolved": diagn["unresolved_attributions"],
            "non_comparable": non_comparable, "insufficient_evidence": insufficient,
            "untested_regions": frame["untested_regions"],
            "load_bearing_assumptions": assumptions, "live_explanations": live,
            "preserved_anomalies": preserved, "closure_statement": CLOSURE_STATEMENT}


# ---- Inquiry formulation (proposals, never findings; transparent heuristic) ----
def _discriminating_questions(closure, diagn, frame):
    Q = []

    def q(text, separates, feasibility, kind="discriminating_question"):
        Q.append({"status": kind, "provenance": "m3_generated_question", "text": text,
                  "separates": separates, "feasibility": feasibility})

    if diagn["verdict"] == "weak":
        q("Obtain an in-scope conformality profile from an INDEPENDENT source (different lab/paper) at comparable conditions.",
          ["measurement", "extraction", "model_structure", "parameterization"], "high")
    q("Extract or obtain REPORTED MEASUREMENT UNCERTAINTY for the profiles.",
      ["insufficient_evidence -> supported/challenged"], "medium")
    q("Obtain CHEMISTRY-SPECIFIC kinetic parameters (sticking c, GPC) with provenance for the deposited chemistry.",
      ["parameterization", "model_structure"], "medium")
    q("Establish CALIBRATION PROVENANCE — were the literature kinetics fit on these very profiles?",
      ["parameterization (calibration circularity)"], "medium")
    for pa in closure["preserved_anomalies"]:
        q(f"For {pa['exp_id']}: measure the penetration-setting inputs and obtain an independent profile to localise the preserved anomaly.",
          pa["live_explanations"], "medium")
    for u in frame["untested_regions"]:
        q(f"Acquire a conformality profile for the untested geometry '{u['value']}' (model-valid but unrepresented).",
          ["untested_region -> coverage"], "medium", kind="evidence_needed")
    fw = {"high": 3, "medium": 2, "low": 1}
    for x in Q:
        x["rank_score"] = len(x["separates"]) * fw.get(x["feasibility"], 1)
        x["rank_basis"] = "separating_power x feasibility (transparent heuristic; NOT expected-information-gain)"
    Q.sort(key=lambda x: -x["rank_score"])
    return Q


# ---- one M3 run (frozen execution order) -------------------------------------
def analyze(question=DEFAULT_QUESTION, criteria=DEFAULT_CRITERIA, is_default=True):
    """One M3 run: framing → scoping → per-comparison → ENSEMBLE BARRIER →
    patterns/diagnosability → interpretation → EVIDENCE CLOSURE → inquiry → FREEZE.
    Researcher judgment is OUTSIDE this run. Returns the frozen analysis object."""
    targets = _targets(criteria)
    frame = _frame(question, criteria, targets, is_default)
    comparisons = [c for c in (validate_one(e, criteria) for e in targets) if c]
    # ===== ENSEMBLE BARRIER =====
    admissible = [c for c in comparisons if c["status"] == "comparison_result"]
    patterns = _ensemble_patterns(admissible)
    diagn = _diagnosability(patterns)
    byid = {e.get("exp_id"): e for e in targets}
    interps, exps_all, preserved = [], [], []
    for r in admissible:
        inv = inverse_fit(byid[r["exp_id"]]) if r["exp_id"] in byid else None
        r["_inverse_fit"] = inv
        interp, exps, recovered = _interpret_one(r, inv, diagn)
        r["interpretation"], r["explanations"] = interp, exps
        interps.append(interp)
        exps_all.append(exps)
        pa = _preserved_anomaly(r, exps, recovered, diagn)
        if pa:
            preserved.append(pa)
            r["preserved_anomaly"] = pa
    assumptions = _global_assumptions(frame)
    # parameterization-recovery insight: how many forward shortfalls a fitted parameter
    # change (exposure + sticking c) can recover — evidence that 'parameterization' is a
    # strongly live explanation, NOT a validation of the model.
    n_rec = sum(1 for r in admissible if r.get("_inverse_fit")
                and (r["_inverse_fit"]["r2_fit"] - r["_inverse_fit"]["r2_warm"] > 0.05)
                and r["_inverse_fit"]["r2_fit"] >= 0.7)
    insights = [{"status": "insight",
                 "text": (f"the forward twin on DEFAULT kinetics reproduces few profile shapes; a fitted change to "
                          f"the pulse time t_p (where adjustable) and the model-specific lumped coefficient c recovers "
                          f"{n_rec}/{len(admissible)} of them, so 'parameterization' is a strongly live explanation for "
                          f"the shortfall — this is a calibration probe (feasible fitted parameterization), not "
                          f"out-of-sample support and not a unique physical estimate")}]
    # run-level model-input provenance + fit summary
    from collections import Counter
    pcount = Counter()
    for r in admissible:
        for row in r.get("model_input_trace", []):
            pcount[row["provenance"]] += 1
    invs = [r["_inverse_fit"] for r in admissible if r.get("_inverse_fit")]
    input_provenance_summary = {
        "by_provenance": dict(pcount),
        "fitted_variables": {"c": len(invs), "t_p": sum(1 for f in invs if f["dose_free"])},
        "boundary_limited_fits": sum(1 for f in invs if f.get("boundary_limited")),
        "ridge_or_broad_fits": sum(1 for f in invs
                                   if f.get("identifiability", {}).get("class")
                                   in ("pulse_time_c_tradeoff_ridge", "broad_feasible_region")),
        "n_2d_fits": sum(1 for f in invs if f["dose_free"]),
        "n_1d_fits": sum(1 for f in invs if not f["dose_free"]),
        "c_ontology_mapping_status": C_ONTOLOGY_STATUS,
    }
    # run-level Model Resolution Summary + evidence coverage (from the per-experiment traces)
    mrs, coverage = _resolution_summary(admissible)
    # ===== EVIDENCE CLOSURE =====
    closure = _evidence_closure(comparisons, admissible, interps, exps_all, assumptions,
                                preserved, frame, diagn, insights)
    inquiry = _discriminating_questions(closure, diagn, frame)
    # ===== FREEZE ===== (the returned object is immutable by contract)
    return {"frame": frame, "comparisons": comparisons, "admissible": admissible,
            "ensemble": {"patterns": patterns, "diagnosability": diagn},
            "input_provenance_summary": input_provenance_summary,
            "model_resolution_summary": mrs, "evidence_coverage": coverage,
            "closure": closure, "inquiry": inquiry}


# descriptive, non-conclusive consequence of each model-consumed input's evidence status
_INPUT_CONSEQUENCE = {
    "t_p": "pulse time / exposure scale; sets penetration when adjustable",
    "pA": "fixed precursor pressure; calibration interpretation depends on fixed pressure provenance",
    "H": "transport length scale; weakly grounded if defaulted",
    "gpc": "per-cycle thickness scale",
    "T": "diffusion / kinetics temperature",
    "W": "channel width (secondary to the gap height)",
    "c": "model-specific lumped reaction coefficient; parameterization remains confounded (fitted in the probe)",
    "K": "adsorption rate constant (model default; transport/uptake)",
    "da": "precursor molecular diameter (transport scale)",
    "MA": "precursor molar mass (transport scale)",
    "exposure": "derived from pA and t_p",
}
# inputs whose default/unresolved state is load-bearing for the forward prediction
_LOAD_BEARING = {"t_p", "pA", "H", "gpc", "c"}


def _resolution_summary(admissible):
    """Run-level resolution counts (by outcome / provenance / parameter / experiment / source) and
    a per-parameter evidence-coverage table. NO single confidence score — evidence composition only."""
    from collections import Counter, defaultdict
    outc, provc = Counter(), Counter()
    by_param = defaultdict(Counter)
    by_exp = defaultdict(Counter)
    by_source = defaultdict(Counter)
    param_meta = {}
    total = 0
    fitted_tp = any(r["_inverse_fit"]["dose_free"] for r in admissible if r.get("_inverse_fit"))
    for r in admissible:
        for row in r.get("model_resolution_trace", []):
            total += 1
            o, p, a = row["outcome"], row["provenance"], row["attr"]
            outc[o] += 1; provc[p] += 1
            by_param[a][o] += 1; by_exp[r["exp_id"]][o] += 1; by_source[r["paper"]][o] += 1
            pm = param_meta.setdefault(a, {"canonical": row["canonical"], "attr": a,
                "ontology_support": row["ontology_support"], "accepted_direct": 0, "derived": 0,
                "imputed": 0, "defaulted": 0, "unresolved": 0, "conflicting": 0, "n": 0})
            pm["n"] += 1
            if o in ("directly_resolved", "resolved_with_conversion"):
                pm["accepted_direct"] += 1
            elif o == "resolved_by_derivation":
                pm["derived"] += 1
            elif o == "resolved_by_imputation":
                pm["imputed"] += 1
            elif o == "resolved_by_default":
                pm["defaulted"] += 1
            elif o == "unresolved":
                pm["unresolved"] += 1
            if o == "conflicting_evidence":
                pm["conflicting"] += 1

    def cnts(counter, keys):
        return {k: counter.get(k, 0) for k in keys}

    def defrac(c):
        t = sum(c.values()); return (c.get("resolved_by_default", 0) / t) if t else 0.0

    def dirfrac(c):
        t = sum(c.values())
        return ((c.get("directly_resolved", 0) + c.get("resolved_with_conversion", 0)) / t) if t else 0.0

    coverage = []
    for a, pm in param_meta.items():
        pm = dict(pm)
        pm["fitted_in_probe"] = (a == "c") or (a == "t_p" and fitted_tp)
        cons = _INPUT_CONSEQUENCE.get(a, "")
        if pm["defaulted"] >= max(1, pm["n"]) * 0.5:
            cons = ("prediction depends on a model default; " + cons) if cons else "prediction depends on a model default"
        if pm["unresolved"] > 0:
            cons = "no accepted canonical evidence in the current corpus; " + cons
        pm["consequence"] = cons
        pm["load_bearing"] = a in _LOAD_BEARING
        coverage.append(pm)
    coverage.sort(key=lambda p: -(p["defaulted"] / max(1, p["n"])))

    mrs = {"total_resolved_instances": total,
           "by_outcome": cnts(outc, RESOLUTION_OUTCOMES),
           "by_provenance": cnts(provc, PROVENANCE_CATEGORIES),
           "by_parameter": {k: dict(v) for k, v in by_param.items()},
           "parameters_most_defaulted": sorted(((k, v.get("resolved_by_default", 0)) for k, v in by_param.items()),
                                               key=lambda x: -x[1])[:6],
           "parameters_most_imputed": sorted(((k, v.get("resolved_by_imputation", 0)) for k, v in by_param.items()),
                                             key=lambda x: -x[1])[:6],
           "parameters_conflicting": [k for k, v in by_param.items() if v.get("conflicting_evidence", 0) > 0],
           "parameters_unresolved": [k for k, v in by_param.items() if v.get("unresolved", 0) > 0],
           "experiments_highest_default_dependence": [(k, round(defrac(v), 2)) for k, v in
                                                      sorted(by_exp.items(), key=lambda kv: -defrac(kv[1]))[:5]],
           "experiments_strongest_direct_evidence": [(k, round(dirfrac(v), 2)) for k, v in
                                                     sorted(by_exp.items(), key=lambda kv: -dirfrac(kv[1]))[:5]],
           "by_source": {k: dict(v) for k, v in by_source.items()}}
    return mrs, coverage


def run_framed(question=DEFAULT_QUESTION, criteria=DEFAULT_CRITERIA):
    """Full run object {frame, comparisons, analysis}. New public entry for tests + Brief."""
    is_default = (question == DEFAULT_QUESTION and criteria is DEFAULT_CRITERIA)
    a = analyze(question, criteria, is_default=is_default)
    return {"frame": a["frame"], "comparisons": a["comparisons"], "analysis": a}


def run(question=DEFAULT_QUESTION, criteria=DEFAULT_CRITERIA):
    """Backward-compatible: returns the per-comparison list (now status-tagged)."""
    return run_framed(question, criteria)["comparisons"]


# ---------------- report ----------------
def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


def overlay_fig(results, worst_n=3, best_n=3):
    # only profiles the twin is actually meant to fit — exclude out-of-scope (plasma AND
    # geometry mismatch), else out-of-scope porous profiles masquerade as "best fits".
    ins = [r for r in results if r["verdict"] != "out of scope"]
    picks = ins[:worst_n] + ins[-best_n:] if len(ins) > worst_n + best_n else ins
    n = len(picks)
    fig, axes = plt.subplots(1, n, figsize=(2.7 * n, 3.0), squeeze=False)
    for ax, r in zip(axes[0], picks):
        xm, ym = r["_meas"]; xt, yt = r["_twin"]
        ax.plot(xm, ym, "o", color=INK, ms=3, label="measured")
        ax.plot(xt, yt, "-", color=(GREEN if r["agree"] else RED), lw=2, label="twin")
        ax.axhline(0.5, color=GREY, ls=":", lw=.8)
        ax.set_title(f"{r['exp_id']}\nR²={r['r2']}", fontsize=8)
        ax.set_xlabel("x (µm)", fontsize=8); ax.set_ylim(-0.05, 1.15)
        ax.tick_params(labelsize=7)
    axes[0][0].set_ylabel("normalised thickness", fontsize=8)
    axes[0][-1].legend(fontsize=7)
    fig.tight_layout()
    return _png(fig)


def _profile_png(r):
    """A single twin-vs-measured plot for one profile (click-to-reveal in the table)."""
    xm, ym = r.get("_meas") or ([], [])
    xt, yt = r.get("_twin") or ([], [])
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    if xm:
        ax.plot(xm, ym, "o", color=INK, ms=3, label="measured")
    if xt:
        ax.plot(xt, yt, "-", color=(GREEN if r["agree"] else RED), lw=2, label="twin")
    ax.axhline(0.5, color=GREY, ls=":", lw=.8)
    ax.set_xlabel("x (µm)", fontsize=8); ax.set_ylabel("norm. thickness", fontsize=8)
    ax.set_ylim(-0.05, 1.15); ax.tick_params(labelsize=7)
    if xm or xt:
        ax.legend(fontsize=7)
    fig.tight_layout()
    return _png(fig)


# =============================================================================
# Calibration probe (inverse_fit) — dimensionally correct, bounded, provenance-
# aware, and honest about non-identifiability. It fits the ADJUSTABLE model
# parameter(s) to reproduce the observed profile; it is NOT validation and NOT a
# unique physical estimate. Fitted variables:
#   · c   — a MODEL-SPECIFIC lumped reaction coefficient (channelModel.c), always
#           adjustable; its default is the model default, and its ontology mapping
#           to a literature sticking_probability is UNRESOLVED (never asserted).
#   · t_p — pulse time, adjustable ONLY when the dose was NOT extracted (else fixed
#           and NOT in the optimizer vector). Exposure = pA·t_p is DERIVED.
# Bounds are explicit and enforced by a smooth log-sigmoid transform (no clipping
# plateaus). A local objective-surface diagnostic classifies identifiability.
# =============================================================================
C_BOUNDS = (1e-5, 1.0)                    # model-supported range for the lumped coefficient c
C_LABEL = "model-specific lumped reaction coefficient c"
C_ONTOLOGY_STATUS = "unresolved"          # NOT equated with a literature sticking_probability
TP_LOG_WINDOW = 2.5                       # fitting policy: t_p may vary within exp(±2.5)·warm
FIT_OPTIMIZER = "Nelder-Mead in a smooth log-sigmoid bounded transform"
FIT_OBJECTIVE = "mean squared error of normalised thickness vs observed depth"
FIT_RESIDUAL = "predicted_norm(x) - observed_norm(x) at each observed depth"
FIT_WEIGHTING = "uniform (unweighted)"


def _r2(y, yt):
    y = np.asarray(y, float); yt = np.asarray(yt, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yt) ** 2) / ss) if ss > 0 else -9.0


def _blog(z, lo, hi):
    """Smooth, strictly-in-bounds log transform: physical value in (lo, hi) for any real z.
    No clipping, so the objective never develops a large flat plateau at a bound."""
    ulo, uhi = math.log(lo), math.log(hi)
    return math.exp(ulo + (uhi - ulo) / (1.0 + math.exp(-z)))


def _bz0(p0, lo, hi):
    ulo, uhi = math.log(lo), math.log(hi)
    fr = min(max((math.log(p0) - ulo) / (uhi - ulo), 1e-6), 1 - 1e-6)
    return math.log(fr / (1 - fr))


def _prov_cat(state):
    return {"extracted": "extracted", "imputed": "imputed",
            "default": "model_default"}.get(state, "unresolved")


def _identifiability(sse_fn, wtp, tp_fit, c_fit, dose_free, tpb, cb, sse_fit):
    """Lightweight LOCAL diagnostic — evaluate the objective around the optimum and classify.
    NEVER claims formal identifiability. Default label is 'feasible fitted parameterization,
    not a unique physical parameter estimate'."""
    c_lo, c_hi = cb; tp_lo, tp_hi = tpb
    label = "feasible fitted parameterization, not a unique physical parameter estimate"
    if not dose_free:
        cs = np.geomspace(c_lo, c_hi, 41)
        vals = [(c, sse_fn(wtp, c)) for c in cs]
        gmin = min(v for _, v in vals)              # reference the grid's own minimum
        tol = max(sse_fit, gmin) * 1.10 + 1e-12     # 'acceptable' = within 10% of the min SSE
        acc = [c for c, v in vals if v <= tol]
        if not acc:
            return {"class": "unassessed", "label": label, "dimensions": 1, "detail": "no acceptable region found"}
        width = (math.log(max(acc)) - math.log(min(acc))) / (math.log(c_hi) - math.log(c_lo))
        klass = ("broad_feasible_region" if width > 0.5 else
                 "narrow_isolated_optimum" if width < 0.12 else "moderate_feasible_interval")
        return {"class": klass, "label": label, "dimensions": 1,
                "acceptable_c_logfrac_width": round(width, 3),
                "acceptable_c_range": [float(min(acc)), float(max(acc))],
                "detail": f"1-D c fit; acceptable-c region spans {width*100:.0f}% of the log-c range"}
    tol = sse_fit * 1.10 + 1e-12                    # 2-D: within 10% of the min SSE
    dl = 0.6
    tps = [math.exp(math.log(tp_fit) + d) for d in np.linspace(-dl, dl, 7)]
    cs = [math.exp(math.log(c_fit) + d) for d in np.linspace(-dl, dl, 7)]
    acc = []
    for tp in tps:
        for c in cs:
            if tp_lo <= tp <= tp_hi and c_lo <= c <= c_hi and sse_fn(tp, c) <= tol:
                acc.append((math.log(tp) - math.log(tp_fit), math.log(c) - math.log(c_fit)))
    if len(acc) <= 1:
        klass = "narrow_isolated_optimum"
    else:
        dtp = [a for a, _ in acc]; dc = [b for _, b in acc]
        span_tp, span_c = max(dtp) - min(dtp), max(dc) - min(dc)
        corr = 0.0
        if len(acc) >= 3 and span_tp > 1e-9 and span_c > 1e-9:
            mt, mc = sum(dtp) / len(dtp), sum(dc) / len(dc)
            num = sum((a - mt) * (b - mc) for a, b in acc)
            den = (sum((a - mt) ** 2 for a in dtp) * sum((b - mc) ** 2 for b in dc)) ** 0.5
            corr = num / den if den else 0.0
        if span_tp > 0.8 and span_c > 0.8 and corr < -0.5:
            klass = "pulse_time_c_tradeoff_ridge"
        elif span_tp > 0.8 or span_c > 0.8:
            klass = "broad_feasible_region"
        else:
            klass = "narrow_isolated_optimum"
    return {"class": klass, "label": label, "dimensions": 2, "n_acceptable_local": len(acc),
            "detail": f"2-D (t_p,c) local surface; {len(acc)}/49 neighbours within 10% of the min SSE"}


def inverse_fit(exp):
    """Calibration probe for the 'parameterization' locus (§4). Holds the EXTRACTED conditions
    fixed and fits the ADJUSTABLE model parameter(s) to reproduce the observed profile on its own
    depth grid. Correct dimensionality: 1-D over c when the dose was extracted (t_p fixed, not in
    the vector); 2-D over (t_p, c) when the dose was not extracted. Explicit bounds via a smooth
    log-sigmoid transform. Returns a FEASIBLE fitted parameterization with full traceability and a
    local identifiability diagnostic — never a unique physical estimate."""
    twin, notes, prov = build_twin(exp)
    meas = measured_profile(exp)
    if not meas:
        return None
    xm, ym = meas
    xg = np.array(xm) * 1e-6
    ym = np.array(ym, float)
    n_obs = len(xm)
    wtp, wc, pA = float(twin.t_p), float(twin.c), float(twin.pA)
    dose_free = prov.get("dose") != "extracted"     # t_p adjustable only if dose was NOT extracted

    c_lo, c_hi = C_BOUNDS
    tp_lo, tp_hi = wtp * math.exp(-TP_LOG_WINDOW), wtp * math.exp(TP_LOG_WINDOW)

    def predict(tp, c):
        twin.t_p = float(tp); twin.c = float(c); twin.prepare()
        th, _, _ = twin.approx(xg, np.zeros_like(xg))
        t0 = th[0] if th[0] > 0 else (th.max() or 1)
        return np.clip(th / t0, 0, None)

    def sse(tp, c):
        return float(np.mean((predict(tp, c) - ym) ** 2))

    evals = {"n": 0}
    if dose_free:                                    # ---- 2-D over (t_p, c) ----
        active = ["t_p", "c"]
        def obj(z):
            evals["n"] += 1
            return sse(_blog(z[0], tp_lo, tp_hi), _blog(z[1], c_lo, c_hi))
        best_tp, best_c = min(((tp, c) for tp in np.geomspace(tp_lo, tp_hi, 9)
                               for c in np.geomspace(c_lo, c_hi, 13)), key=lambda p: sse(*p))
        z0 = [_bz0(best_tp, tp_lo, tp_hi), _bz0(best_c, c_lo, c_hi)]
        res = minimize(obj, z0, method="Nelder-Mead",
                       options={"maxiter": 200, "xatol": 1e-3, "fatol": 1e-9})
        tp_fit = _blog(res.x[0], tp_lo, tp_hi); c_fit = _blog(res.x[1], c_lo, c_hi)
    else:                                            # ---- 1-D over c (t_p fixed) ----
        active = ["c"]
        def obj(z):
            evals["n"] += 1
            return sse(wtp, _blog(z[0], c_lo, c_hi))
        best_c = min(np.geomspace(c_lo, c_hi, 21), key=lambda c: sse(wtp, c))
        z0 = [_bz0(best_c, c_lo, c_hi)]
        res = minimize(obj, z0, method="Nelder-Mead",
                       options={"maxiter": 200, "xatol": 1e-3, "fatol": 1e-9})
        tp_fit = wtp; c_fit = _blog(res.x[0], c_lo, c_hi)

    r2_warm, r2_fit = _r2(ym, predict(wtp, wc)), _r2(ym, predict(tp_fit, c_fit))
    sse_warm, sse_fit = sse(wtp, wc), sse(tp_fit, c_fit)

    def _pos(p, lo, hi):
        return (math.log(p) - math.log(lo)) / (math.log(hi) - math.log(lo))
    c_pos = _pos(c_fit, c_lo, c_hi)
    c_bound = "at_lower" if c_pos <= 0.02 else "at_upper" if c_pos >= 0.98 else "interior"
    if dose_free:
        tp_pos = _pos(tp_fit, tp_lo, tp_hi)
        tp_bound = "at_lower" if tp_pos <= 0.02 else "at_upper" if tp_pos >= 0.98 else "interior"
    else:
        tp_bound = "fixed"
    boundary_limited = (c_bound != "interior") or (tp_bound in ("at_lower", "at_upper"))
    ident = _identifiability(sse, wtp, tp_fit, c_fit, dose_free, (tp_lo, tp_hi), (c_lo, c_hi), sse_fit)

    # representative warm→fit curves for the exhibit figure (log-interpolated)
    def _blend(a, b, t):
        return math.exp(math.log(a) + t * (math.log(b) - math.log(a)))
    ts = np.linspace(0, 1, 6)
    curves = [(round(_r2(ym, predict(_blend(wtp, tp_fit, t) if dose_free else wtp, _blend(wc, c_fit, t))), 3),
               list(predict(_blend(wtp, tp_fit, t) if dose_free else wtp, _blend(wc, c_fit, t)))) for t in ts]

    return {
        "exp_id": exp["exp_id"], "geometry_class": exp.get("geometry_class"),
        "dose_free": dose_free,
        "active_variables": active,
        "fixed_variables": (["pulse_time_t_p"] if not dose_free else []) + ["precursor_partial_pressure_pA"],
        "variables": {
            "t_p": {"canonical": "pulse_time", "meaning": "precursor pulse time", "unit": "s",
                    "role": ("adjustable" if dose_free else "fixed"),
                    "initial": wtp, "lower": (tp_lo if dose_free else wtp),
                    "upper": (tp_hi if dose_free else wtp), "fitted": tp_fit,
                    "bound_status": tp_bound, "provenance": _prov_cat(prov.get("dose"))},
            "c": {"canonical": None, "meaning": C_LABEL, "unit": "dimensionless (probability-like)",
                  "role": "adjustable", "initial": wc, "lower": c_lo, "upper": c_hi, "fitted": c_fit,
                  "bound_status": c_bound, "provenance_initial": "model_default",
                  "provenance_fitted": "inverse_fitted", "ontology_mapping_status": C_ONTOLOGY_STATUS},
        },
        "pA": {"value": pA, "provenance": _prov_cat(prov.get("pA")), "role": "fixed",
               "canonical": "precursor_partial_pressure"},
        "exposure_warm": wtp * pA, "exposure_fit": tp_fit * pA,
        "exposure_note": "exposure = pA x t_p (DERIVED; pA fixed, never independently fitted)",
        "optimizer": FIT_OPTIMIZER, "objective": FIT_OBJECTIVE, "residual": FIT_RESIDUAL,
        "weighting": FIT_WEIGHTING, "n_obs": n_obs, "n_eval": evals["n"], "converged": bool(res.success),
        "sse_before": sse_warm, "sse_after": sse_fit,
        "boundary_limited": boundary_limited, "identifiability": ident,
        # legacy-compatible keys for the existing exhibit figure/table
        "niter": evals["n"], "r2_warm": r2_warm, "r2_fit": r2_fit,
        "expo_warm": wtp * pA, "expo_fit": tp_fit * pA, "c_warm": wc, "c_fit": c_fit,
        "xm": list(xm), "ym": list(ym), "curves": curves, "r2track": [c[0] for c in curves],
    }


def _model_input_trace(exp, twin, prov, dose_free):
    """Every runtime input actually used by the forward model for THIS prediction, read from the
    SAME twin object that produced the profile. Chain: canonical evidence -> resolved runtime input
    -> model attribute -> predicted profile -> predicted PD50."""
    kp = getattr(twin, "kb_provenance", {}) or {}

    def kbcat(attr):
        s = (kp.get(attr) or {}).get("source")
        return {"kb": "literature_reported", "precursor": "literature_reported",
                "material": "literature_reported"}.get(s, "model_default")

    def kbsrc(attr, fallback):
        m = kp.get(attr) or {}
        return m.get("quantity") or m.get("property") or fallback

    rows = [
        {"canonical": "pulse_time", "attr": "t_p", "value": twin.t_p, "unit": "s",
         "provenance": _prov_cat(prov.get("dose")),
         "source": "controlled[pulse_time A/B] else KB impute else model default",
         "role": ("adjustable (calibration probe)" if dose_free else "fixed"),
         "assumption": ("KB estimate (imputed)" if prov.get("dose") == "imputed"
                        else "model default t_p" if prov.get("dose") == "default" else "")},
        {"canonical": "temperature", "attr": "T", "value": twin.T - 273.15, "unit": "°C",
         "provenance": _prov_cat(prov.get("T")), "source": "controlled[temperature] else KB impute else default",
         "role": "fixed", "assumption": ("KB estimate (imputed)" if prov.get("T") == "imputed" else "")},
        {"canonical": "precursor_partial_pressure", "attr": "pA", "value": twin.pA, "unit": "Pa",
         "provenance": _prov_cat(prov.get("pA")),
         "source": "pressure_compat.precursor_pressure else controlled[partial_pressure A] else default",
         "role": "fixed",
         "assumption": ("KB estimate (imputed)" if prov.get("pA") == "imputed"
                        else "model default pA=100 Pa" if prov.get("pA") == "default" else "")},
        {"canonical": "growth_per_cycle", "attr": "gpc", "value": twin.gpc * 1e9, "unit": "nm/cycle",
         "provenance": _prov_cat(prov.get("gpc")), "source": "controlled[growth_per_cycle] else KB impute else default",
         "role": "fixed", "assumption": ("KB estimate (imputed)" if prov.get("gpc") == "imputed" else "")},
        {"canonical": "feature_height", "attr": "H", "value": twin.H * 1e6, "unit": "µm",
         "provenance": _prov_cat(prov.get("H")), "source": "controlled[feature_height] (not imputed) else default",
         "role": "fixed", "assumption": ("assumed default gap (not extracted)" if prov.get("H") == "default" else "")},
        {"canonical": None, "attr": "c", "value": twin.c, "unit": "dimensionless",
         "provenance": ("literature_reported" if (kp.get("c") or {}).get("source") == "kb" else "model_default"),
         "source": "KB reaction_probability (absent here) else channelModel default",
         "role": "fixed in forward prediction; adjustable in calibration probe",
         "assumption": f"{C_LABEL}; ontology mapping to sticking_probability: {C_ONTOLOGY_STATUS}"},
        {"canonical": "adsorption_rate_constant", "attr": "K", "value": twin.K, "unit": "1/Pa",
         "provenance": ("literature_reported" if (kp.get("K") or {}).get("source") == "kb" else "model_default"),
         "source": kbsrc("K", "KB adsorption_rate_constant else channelModel default"),
         "role": "fixed", "assumption": ""},
        {"canonical": "molecular_diameter(A)", "attr": "da", "value": twin.da * 1e12, "unit": "pm",
         "provenance": kbcat("da"), "source": kbsrc("da", "precursor ontology / model default"),
         "role": "fixed", "assumption": ""},
        {"canonical": "molar_mass(A)", "attr": "MA", "value": twin.MA * 1e3, "unit": "g/mol",
         "provenance": kbcat("MA"), "source": kbsrc("MA", "precursor ontology / model default"),
         "role": "fixed", "assumption": ""},
        {"canonical": None, "attr": "exposure = pA·t_p", "value": twin.pA * twin.t_p, "unit": "Pa·s",
         "provenance": "derived", "source": "pA × t_p",
         "role": ("adjustable via t_p" if dose_free else "fixed"),
         "assumption": "DERIVED from pA and t_p; not independently fitted"},
    ]
    return rows


def inverse_png(f):
    fig, (ax, axr) = plt.subplots(1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [2, 1]})
    ax.plot(f["xm"], f["ym"], "o", color=INK, ms=3, label="measured", zorder=5)
    n = len(f["curves"])
    for i, (r, yt) in enumerate(f["curves"]):
        last = (i == n - 1)
        ax.plot(f["xm"], yt, "-", color=(GREEN if last else RED),
                lw=(2.2 if last else 1), alpha=(0.2 + 0.8 * (i / max(1, n - 1))),
                label=("fit" if last else ("warm start" if i == 0 else None)))
    ax.axhline(0.5, color=GREY, ls=":", lw=.8); ax.set_ylim(-0.05, 1.15)
    ax.set_xlabel("x (µm)", fontsize=8); ax.set_ylabel("norm. thickness", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title(f"R² {f['r2_warm']:.2f} → {f['r2_fit']:.2f}    exposure {f['expo_warm']:.1f}→{f['expo_fit']:.1f} Pa·s"
                 f"    c {f['c_warm']:.3f}→{f['c_fit']:.4f}", fontsize=7.5)
    ax.legend(fontsize=7, loc="upper right")
    axr.plot(range(1, len(f["r2track"]) + 1), f["r2track"], "-", color=PURPLE, lw=1.3)
    axr.set_xlabel("iteration", fontsize=8); axr.set_ylabel("R²", fontsize=8)
    axr.set_ylim(-1.05, 1.05); axr.tick_params(labelsize=7); axr.set_title("convergence", fontsize=8)
    fig.tight_layout(); return _png(fig)


VCOLOR = {"agrees": GREEN, "model gap": RED, "estimation gap": PURPLE,
          "data gap": AMBER, "out of scope": GREY}


def scatter_fig(results):
    ins = [r for r in results if r["thermal"]]
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    for r in ins:
        if r["pd_meas"] and r["pd_twin"]:
            ax.plot(r["pd_meas"], r["pd_twin"], "o", ms=6, color=VCOLOR[r["verdict"]], alpha=.8)
    lim = max([r["pd_meas"] for r in ins if r["pd_meas"]] +
              [r["pd_twin"] for r in ins if r["pd_twin"]] + [1])
    ax.plot([0, lim], [0, lim], "--", color=GREY, lw=1)
    ax.set_xlabel("measured PD50 (µm)"); ax.set_ylabel("twin PD50 (µm)")
    ax.set_title("penetration depth: twin vs measured", fontsize=10)
    fig.tight_layout()
    return _png(fig)


_LEGACY_HTML = """<title>M3 · Twin validation against KB curves</title>
<style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#131417;color:#eceef2}}.card{{background:#1c1e22 !important;border-color:#2b2e34 !important}}th{{color:#767c86 !important}}}}
.wrap{{max-width:1040px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:18px}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}} img{{max-width:100%}}
.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:5px 8px;border-bottom:1px solid #eef0f3}}.m{{font-family:ui-monospace,Menlo,monospace}}
.flag{{color:#e34948;font-weight:600}}.ok{{color:#1baf7a;font-weight:600}}
.kv{{display:flex;gap:22px;flex-wrap:wrap;margin:8px 0 2px}} .kv div b{{display:block;font-size:18px}} .kv div span{{color:#8b919b;font-size:11px}}
.note{{font-size:11px;color:#8b919b}}
.prow{{cursor:pointer}} .prow:hover td{{background:#f4f6f8}}
.detail{{display:none}} .detail td{{background:#fafbfc;text-align:center}}
img.pfit{{max-width:400px;width:100%;height:auto}}
</style>
<script>function tog(r){{var d=r.nextElementSibling; if(d&&d.classList.contains('detail')) d.style.display = d.style.display==='table-row'?'none':'table-row';}}</script>
<div class=wrap>
<div class=eyebrow>PSED · M3 · Phase 4</div>
<h1>Twin validation against measured KB profiles</h1>
<div class=sub>The KB-parameterised Ylilammi twin (<span class=m>{model}</span>) is run against every measured conformality
profile across <b>all four papers</b> and scored with the same curve engine used across the KB. Missing twin inputs are covariate-imputed from the KB — and because an imputed value is only an <b>estimate</b>, it is a candidate cause of any mismatch, tracked separately below.</div>
<div class=card><div class=kv>
 <div><b>{nt}</b><span>thermal profiles (in scope)</span></div>
 <div><b class=ok>{npass}</b><span>agree</span></div>
 <div><b style="color:#e34948">{nmodel}</b><span>model gap (all inputs measured)</span></div>
 <div><b style="color:#9085e9">{nest}</b><span>estimation gap (an input imputed)</span></div>
 <div><b style="color:#eda100">{ndata}</b><span>data gap (an input assumed)</span></div>
 <div><b style="color:#8b919b">{noos}</b><span>out of scope (plasma)</span></div>
</div>
<div class=note style="margin-top:8px">Verdict is set by the provenance of the two penetration-setting inputs (dose &amp; gap height):
<b style="color:#e34948">model gap</b> = both measured, twin still misses → real Ylilammi-physics / literature-K,c limit ·
<b style="color:#9085e9">estimation gap</b> = an input is a <b>KB estimate</b>, which may itself be the cause, not the model ·
<b style="color:#eda100">data gap</b> = an input was assumed → measure it ·
<b style="color:#8b919b">out of scope</b> = plasma / recombination-limited (Arts), which the thermal twin doesn't model — see future work.</div></div>
<div class=card><h2>Twin vs measured — worst &amp; best fits</h2><img src="data:image/png;base64,{ov}"></div>
<div class=card><h2>Penetration depth: twin vs measured</h2><img src="data:image/png;base64,{sc}">
<div class=note>On the diagonal = the twin reproduces the measured penetration. Off-diagonal reds are where literature parameters + the Ylilammi physics miss the real profile.</div></div>
<div class=card><h2>Inverse fit — recovering the assumed conditions</h2>
<div class=note style="margin-bottom:8px">The forward twin above runs on KB-imputed inputs. Here we instead <b>hold the EXTRACTED
conditions fixed</b>, warm-start the <b>imputed</b> ones, and optimise the two identifiable free
parameters — <b>exposure</b> (pA·t_p, sets penetration depth) and the <b>lumped sticking coefficient
c</b> (sets front sharpness) — to fit each profile on its own coordinate. This is the same inverse
procedure the source papers use to <b>extract c</b>. Click a row to watch the fit converge (warm→fit)
and read the recovered values.</div>
{invsummary}
<table><tr><th>exp id</th><th>geometry</th><th>R² warm→fit</th><th>exposure warm→fit (Pa·s)</th><th>c warm→fit</th></tr>
{invrows}
</table></div>
<div class=card><h2>Per-profile results (forward twin)</h2>
<table><tr><th>exp id</th><th>R²</th><th>PD50 meas</th><th>PD50 twin</th><th>ΔPD50</th><th>inputs measured</th><th>verdict</th></tr>
{rows}
</table></div>
</div>"""


def _legacy_main():                       # DORMANT — retained for migration, not called
    results = run()
    ov = overlay_fig(results)
    sc = scatter_fig(results)
    ins = [r for r in results if r.get("thermal")]
    nt = len(ins)
    nmodel = sum(r.get("verdict") == "model gap" for r in results)
    nest = sum(r["verdict"] == "estimation gap" for r in results)
    ndata = sum(r["verdict"] == "data gap" for r in results)
    noos = sum(r["verdict"] == "out of scope" for r in results)
    npass = sum(r["agree"] for r in results)
    vlabel = {"agrees": "✓ agrees", "model gap": "⚑ model gap", "estimation gap": "≈ estimation gap",
              "data gap": "○ data gap", "out of scope": "— out of scope"}
    vstyle = {"agrees": "color:#1baf7a;font-weight:600", "model gap": "color:#e34948;font-weight:600",
              "estimation gap": "color:#9085e9;font-weight:600", "data gap": "color:#eda100;font-weight:600",
              "out of scope": "color:#8b919b"}
    rows = ""
    for r in results:
        rel = f"{r['pd_rel']*100:.0f}%" if r["pd_rel"] is not None else "—"
        st = f'<span style="{vstyle[r["verdict"]]}">{vlabel[r["verdict"]]}</span>'
        kind = f'<div class=note>{r["kind"]}</div>' if r["kind"] else ""
        note = f'<div class=note>{"; ".join(r["notes"])}</div>' if r["notes"] else ""
        inputs = " · ".join(f'<span style="color:#1baf7a">{k}</span>' for k in r["measured"]) \
            + ("".join(f' · <span style="color:#9085e9">{k}~</span>' for k in r["imputed"]))
        png = _profile_png(r)
        rows += (f"<tr class=prow onclick=\"tog(this)\"><td class=m>▸ {r['exp_id']}{note}</td><td class=m>{r['r2']}</td>"
                 f"<td class=m>{_um(r['pd_meas'])}</td><td class=m>{_um(r['pd_twin'])}</td><td class=m>{rel}</td>"
                 f"<td style='font-size:11px'>{inputs or '—'}</td><td>{st}{kind}</td></tr>"
                 f"<tr class=detail><td colspan=7><img class=pfit src=\"data:image/png;base64,{png}\"></td></tr>")
    # ---- inverse fit: recover the assumed conditions for in-scope profiles ----
    byid = {e.get("exp_id"): e for e in ks._load()}
    inscope = [r["exp_id"] for r in results if r["verdict"] != "out of scope"]
    fits = [f for f in (inverse_fit(byid[i]) for i in inscope if i in byid) if f]
    fits.sort(key=lambda f: -(f["r2_fit"] - f["r2_warm"]))     # biggest recovery first
    improved = sum(1 for f in fits if f["r2_fit"] - f["r2_warm"] > 0.05)
    mean_warm = sum(f["r2_warm"] for f in fits) / len(fits) if fits else 0
    mean_fit = sum(f["r2_fit"] for f in fits) / len(fits) if fits else 0
    invsummary = (f'<div class=kv><div><b>{len(fits)}</b><span>profiles fitted</span></div>'
                  f'<div><b>{mean_warm:.2f} → {mean_fit:.2f}</b><span>mean R² (warm → fit)</span></div>'
                  f'<div><b>{improved}</b><span>materially recovered (ΔR²&gt;0.05)</span></div></div>')
    invrows = ""
    for f in fits:
        d = "▲" if f["r2_fit"] - f["r2_warm"] > 0.05 else ""
        png = inverse_png(f)
        invrows += (f"<tr class=prow onclick=\"tog(this)\"><td class=m>▸ {f['exp_id']}</td>"
                    f"<td>{f['geometry_class']}</td>"
                    f"<td class=m>{f['r2_warm']:.2f} → {f['r2_fit']:.2f} {d}</td>"
                    f"<td class=m>{f['expo_warm']:.1f} → {f['expo_fit']:.1f}{'' if f['dose_free'] else ' (fixed)'}</td>"
                    f"<td class=m>{f['c_warm']:.3f} → {f['c_fit']:.4f}</td></tr>"
                    f"<tr class=detail><td colspan=5><img class=pfit style='max-width:660px' "
                    f"src=\"data:image/png;base64,{png}\"></td></tr>")
    out = HERE / "m3_validation.html"
    out.write_text(_LEGACY_HTML.format(model=MODEL_ID, nt=nt, npass=npass, nmodel=nmodel,
                                       nest=nest, ndata=ndata, noos=noos, ov=ov, sc=sc, rows=rows,
                                       invsummary=invsummary, invrows=invrows))
    print("wrote", out)
    print(f"  inverse fit: {len(fits)} profiles, mean R² {mean_warm:.2f}→{mean_fit:.2f}, {improved} recovered")
    print(f"  {len(results)} profiles ({nt} thermal, {noos} plasma) · {npass} agree · "
          f"{nmodel} model · {nest} estimation · {ndata} data gaps")
    for r in ins[:6]:
        print(f"  {r['verdict']:14} {r['exp_id']:20} R²={r['r2']}  "
              f"meas={_um(r['pd_meas'])} twin={_um(r['pd_twin'])}  in:{r['measured']}+imp{r['imputed']}")


def _um(v):
    return f"{v:.1f}µm" if isinstance(v, (int, float)) else "—"


# =============================================================================
# Interpretation Brief — the canonical M3 report. Organized around the scientific
# result (what was compared / supported / challenged / unresolved / next), in the
# frozen contract order. Neutral language throughout ("prediction versus
# observation"), never "versus reality". Reuses inverse_fit + the matplotlib
# primitives; figures are neutral exhibits.
# =============================================================================
import html as _H

# status -> (short label, css class) — makes every epistemic status visibly distinct
_BADGE = {
    "comparison_result": ("comparison", "s-cmp"), "non_comparable": ("non-comparable", "s-non"),
    "insufficient_evidence": ("insufficient", "s-ins"), "unresolved": ("unresolved", "s-unr"),
    "untested_region": ("untested", "s-unt"), "supported_interpretation": ("supported", "s-sup"),
    "challenged_interpretation": ("challenged", "s-chl"), "candidate_explanation": ("candidate", "s-can"),
    "alternative_explanation": ("alternative", "s-can"), "assumption": ("assumption", "s-asm"),
    "preserved_anomaly": ("preserved anomaly", "s-ano"), "insight": ("insight", "s-ins2"),
    "discriminating_question": ("discriminating Q", "s-q"), "evidence_needed": ("evidence needed", "s-q"),
    "open_question": ("open Q", "s-q"),
}


def _badge(status):
    lbl, cls = _BADGE.get(status, (status, "s-unr"))
    return f'<span class="badge {cls}">{_H.escape(lbl)}</span>'


_BRIEF_CSS = """
body{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media(prefers-color-scheme:dark){body{background:#131417;color:#eceef2}
 .card{background:#1c1e22 !important;border-color:#2b2e34 !important}.stat{background:#1c1e22 !important;border-color:#2b2e34 !important}
 th{color:#a8adb7 !important}td{border-color:#2b2e34 !important}.mut{color:#8b919b !important}.disc{background:#17181c !important}}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 64px}
h1{font-size:23px;margin:0 0 2px}h2{font-size:15px;margin:0 0 10px}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}
.sub{color:#565c66;margin-bottom:16px;font-size:13px}
.card{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px 18px;margin-bottom:15px}
.disclaimer{border-left:3px solid #2a78d6;background:rgba(42,120,214,.06);padding:10px 14px;border-radius:8px;font-size:12.5px;color:#334}
@media(prefers-color-scheme:dark){.disclaimer{color:#c7d2e0}}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{text-align:left;padding:6px 8px;border-bottom:1px solid #e6e8ec;color:#565c66;font-size:10px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid #eef0f3;vertical-align:top}
.bar{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 4px}
.stat{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:8px 13px;min-width:96px}
.stat b{font-size:19px;display:block}.stat span{font-size:10.5px;color:#8b919b}
.note{font-size:12px;color:#565c66;margin-top:9px}
.badge{display:inline-block;font-size:9.5px;font-weight:700;padding:1.5px 7px;border-radius:20px;letter-spacing:.02em;white-space:nowrap}
.s-cmp{background:rgba(42,120,214,.15);color:#2a78d6}.s-non{background:rgba(139,145,155,.20);color:#6b7280}
.s-ins{background:rgba(237,161,0,.20);color:#b37a00}.s-ins2{background:rgba(27,175,122,.16);color:#1baf7a}
.s-unr{background:rgba(237,161,0,.16);color:#b37a00}.s-unt{background:rgba(144,133,233,.20);color:#6c5ce7}
.s-sup{background:rgba(27,175,122,.18);color:#1baf7a}.s-chl{background:rgba(227,73,72,.16);color:#e34948}
.s-can{background:rgba(20,22,26,.10);color:#334}.s-asm{background:rgba(144,133,233,.18);color:#6c5ce7}
.s-ano{background:rgba(227,73,72,.22);color:#c62b2b}.s-q{background:rgba(42,120,214,.14);color:#2a78d6}
@media(prefers-color-scheme:dark){.s-can{background:rgba(200,205,215,.14);color:#c7ccd6}}
.prow{cursor:pointer}.prow:hover td{background:#f4f6f8}@media(prefers-color-scheme:dark){.prow:hover td{background:#17181c}}
.disc{display:none}.disc td{background:#fafbfc}.pfit{max-width:420px;width:100%}
ul{margin:6px 0 0 18px;padding:0}li{margin:2px 0}
.pill{display:inline-block;background:#eef0f3;border-radius:6px;padding:1px 6px;font-size:11px;margin:1px}
@media(prefers-color-scheme:dark){.pill{background:#24262b}}
img{max-width:100%}
"""

_BRIEF_JS = "<script>function tog(r){var d=r.nextElementSibling;if(d&&d.classList.contains('disc'))d.style.display=d.style.display==='table-row'?'none':'table-row';}</script>"


def _brief_scatter(admissible):
    xs = [r["pd_meas"] for r in admissible if r.get("pd_meas") and r.get("pd_twin")]
    ys = [r["pd_twin"] for r in admissible if r.get("pd_meas") and r.get("pd_twin")]
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    ax.plot(xs, ys, "o", ms=6, color=BLUE, alpha=.7)
    lim = max((xs + ys) or [1] + [1])
    ax.plot([0, lim], [0, lim], "--", color=GREY, lw=1)
    ax.set_xlabel("observed PD50 (µm)"); ax.set_ylabel("predicted PD50 (µm)")
    ax.set_title("prediction versus observation (PD50)", fontsize=10)
    fig.tight_layout(); return _png(fig)


def _brief_profile_png(r):
    xm, ym = r.get("_meas") or ([], [])
    xt, yt = r.get("_twin") or ([], [])
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    if xm:
        ax.plot(xm, ym, "o", color=INK, ms=3, label="observation")
    if xt:
        ax.plot(xt, yt, "-", color=BLUE, lw=2, label="prediction")
    ax.axhline(0.5, color=GREY, ls=":", lw=.8); ax.set_ylim(-0.05, 1.15)
    ax.set_xlabel("depth x (µm)", fontsize=8); ax.set_ylabel("norm. thickness", fontsize=8)
    ax.tick_params(labelsize=7)
    if xm or xt:
        ax.legend(fontsize=7)
    fig.tight_layout(); return _png(fig)


# provenance category -> css class (defaults / unresolved are made prominent)
_PROV_CLS = {"literature_reported": "s-sup", "extracted": "s-cmp", "derived": "s-can",
             "imputed": "s-ins", "model_default": "s-ano", "inverse_fitted": "s-asm",
             "unresolved": "s-ano"}
_KEY_INPUT = {"t_p": "pulse time", "T": "temperature", "pA": "precursor pressure",
              "gpc": "GPC", "H": "gap height"}


def _pbadge(p):
    return f'<span class="badge {_PROV_CLS.get(p, "s-ano")}">{_H.escape(str(p))}</span>'


# resolution outcome -> css class (defaults/unresolved/conflicting made prominent)
_OUTCOME_CLS = {"directly_resolved": "s-sup", "resolved_with_conversion": "s-cmp",
                "resolved_by_derivation": "s-can", "resolved_by_imputation": "s-ins",
                "resolved_by_default": "s-ano", "unresolved": "s-ano", "conflicting_evidence": "s-ano"}


def _obadge(o):
    return f'<span class="badge {_OUTCOME_CLS.get(o, "s-ano")}">{_H.escape(str(o))}</span>'


def _fmtv(v):
    return f"{v:.4g}" if isinstance(v, (int, float)) else _H.escape(str(v))


def _resolution_table_html(c):
    """The Model Resolution Trace: for every model input, canonical evidence → candidates →
    precedence/fallback decision → conversion/derivation → final model value → attribute.
    Provenance AND resolution outcome are readable in the main table (not only tooltips);
    defaulted / unresolved / conflicting rows are visually prominent."""
    esc = _H.escape
    rows = ""
    for r in c.get("model_resolution_trace", []):
        cands = r.get("candidates") or []
        cand_txt = "; ".join(
            f"{_fmtv(x.get('value'))}{(' ' + str(x.get('unit'))) if x.get('unit') else ''}"
            + (f" [{esc(str(x.get('quantity')))}]" if x.get("quantity") else "")
            + (f" ({esc(str(x['acceptance']))})" if x.get("acceptance") else "")
            for x in cands) or "—"
        rej = r.get("rejected") or []
        rej_txt = ("; ".join(f"{_fmtv(x['value'])} — {esc(str(x['reason']))}" for x in rej)) if rej else ""
        prom = (r["outcome"] in ("resolved_by_default", "unresolved", "conflicting_evidence"))
        hl = ' style="background:rgba(227,73,72,.05)"' if prom else ''
        rows += (f"<tr{hl}>"
                 f"<td class=mono>{esc(str(r['canonical']) if r['canonical'] else '—')}"
                 f"<div class=mut style='font-size:10.5px'>{esc(r['canonical_path'])}</div></td>"
                 f"<td class=mono>{esc(r['attr'])}</td>"
                 f"<td>{_pbadge(r['provenance'])}</td><td>{_obadge(r['outcome'])}</td>"
                 f"<td class=mono>{esc(r['display'])}</td>"
                 f"<td class=mut style='font-size:11px'>{esc(r['selection_rule'])}"
                 f"<div>selected: <b>{esc(str(r['selected']))}</b></div></td>"
                 f"<td class=mut style='font-size:11px'>{cand_txt}"
                 + (f"<div style='color:#c62b2b'>rejected: {rej_txt}</div>" if rej_txt else "") + "</td>"
                 f"<td class=mut style='font-size:11px'>{esc(str(r['transform'])) if r['transform'] else '—'}</td>"
                 f"<td class=mut style='font-size:11px'>{esc(r['assumption'])}</td></tr>")
    return (f"<div class=note><b>Model Resolution Trace</b> — how each runtime input was resolved "
            f"(canonical evidence → candidates → precedence decision → conversion → final value → "
            f"attribute). Model-default / unresolved / conflicting rows are highlighted.</div>"
            f"<div style='overflow-x:auto'><table><tr><th>canonical evidence</th><th>attr</th><th>provenance</th>"
            f"<th>resolution outcome</th><th>final value</th><th>selection rule / selected</th>"
            f"<th>candidates &amp; rejections</th><th>conversion</th><th>assumption</th></tr>{rows}</table></div>")


def _evidence_composition(c):
    """Per-comparison model-input evidence composition (NOT a confidence score). Counts the
    comparison's inputs by resolution outcome and names its load-bearing defaulted inputs."""
    from collections import Counter
    tr = c.get("model_resolution_trace", [])
    oc = Counter(r["outcome"] for r in tr)
    load = [r["attr"] for r in tr if r["outcome"] in ("resolved_by_default", "unresolved")
            and r["attr"] in _LOAD_BEARING]
    parts = " · ".join(f"{v} {_obadge(k)}" for k, v in oc.items())
    lb = (f" <b>Load-bearing defaulted/unresolved inputs:</b> "
          f"<span class=mono>{_H.escape(', '.join(load))}</span>." if load else "")
    return (f"<div class=note><b>Model-input evidence composition</b> (not a confidence score; parameters "
            f"are not equally important): {parts}.{lb}</div>")


def _trace_html(c):
    """The per-comparison expandable computational trace (8 parts): observed-data provenance,
    forward-model inputs, forward prediction, comparison metrics, calibration-probe setup,
    calibration-probe result, bounds & convergence, identifiability & provenance caveats."""
    esc = _H.escape
    f = c.get("_inverse_fit")
    op = c["observation_provenance"]
    t1 = (f"<div class=note><b>1 · Observed-data trace.</b> profile extracted from "
          f"<span class=mono>{esc(str(op.get('doi')))} {esc(str(op.get('figure')))}</span> by "
          f"<span class=mono>{esc(str(op.get('extractor')))}</span> — a fallible extraction, not ground truth. "
          f"extraction status {esc(str(op.get('extraction_status')))}; measurement uncertainty "
          f"<b>{esc(op['measurement_uncertainty'])}</b>; calibration status <b>{esc(op['calibration_status'])}</b>. "
          f"Observable: normalised thickness vs depth; PD50 = depth at 50% of mouth thickness.</div>")
    # 2 · Model Resolution Trace (how each runtime input was resolved) + evidence composition
    t2 = ("<div class=note><b>2 · Forward-model input resolution.</b> The values below are the actual "
          "runtime attributes passed into <span class=mono>build_twin()</span> and used to produce the "
          "prediction, with how each was resolved.</div>"
          + _resolution_table_html(c) + _evidence_composition(c))
    t3 = (f"<div class=note><b>3 · Forward prediction.</b> chain: canonical evidence → resolved runtime input "
          f"→ model attribute → predicted normalised profile → predicted PD50 = "
          f"<b>{_um(c.get('predicted_pd50_um'))}</b> (observed PD50 = {_um(c.get('pd_meas'))}).</div>"
          f"<div style='text-align:center'><img class=pfit src='data:image/png;base64,{_brief_profile_png(c)}'></div>")
    r2 = c.get("r2")
    t4 = (f"<div class=note><b>4 · Comparison metrics (descriptive).</b> "
          f"R²={r2:.3f}, shape fit <b>{esc(str(c.get('shape_fit')))}</b>, severity "
          f"{(c.get('severity') or {}).get('level')}. Quantitative agreement: <b>insufficient_evidence</b> "
          f"(measurement σ unresolved) — not uncertainty-relative and not truth.</div>")
    if not f:
        return t1 + t2 + t3 + t4
    v = f["variables"]
    t5 = (f"<div class=note><b>5 · Calibration-probe setup.</b> optimizer: "
          f"<span class=mono>{esc(f['optimizer'])}</span>; objective: {esc(f['objective'])}; residual: "
          f"{esc(f['residual'])}; weighting: {esc(f['weighting'])}; n_obs={f['n_obs']}. "
          f"<b>active fitted variables:</b> {esc(', '.join(f['active_variables']))}; "
          f"<b>fixed:</b> {esc(', '.join(f['fixed_variables']))}.</div>"
          f"<table><tr><th>variable</th><th>meaning</th><th>unit</th><th>role</th><th>initial</th>"
          f"<th>lower</th><th>upper</th><th>fitted</th><th>bound</th></tr>"
          f"<tr><td class=mono>t_p</td><td>{esc(v['t_p']['meaning'])}</td><td class=mono>s</td>"
          f"<td class=mono>{esc(v['t_p']['role'])}</td><td class=mono>{_fmtv(v['t_p']['initial'])}</td>"
          f"<td class=mono>{_fmtv(v['t_p']['lower'])}</td><td class=mono>{_fmtv(v['t_p']['upper'])}</td>"
          f"<td class=mono>{_fmtv(v['t_p']['fitted'])}</td><td class=mono>{esc(v['t_p']['bound_status'])}</td></tr>"
          f"<tr><td class=mono>c</td><td>{esc(v['c']['meaning'])} <i>(ontology mapping: "
          f"{esc(v['c']['ontology_mapping_status'])})</i></td><td class=mono>—</td>"
          f"<td class=mono>{esc(v['c']['role'])}</td><td class=mono>{_fmtv(v['c']['initial'])}</td>"
          f"<td class=mono>{v['c']['lower']:.0e}</td><td class=mono>{v['c']['upper']:.1f}</td>"
          f"<td class=mono>{_fmtv(v['c']['fitted'])}</td><td class=mono>{esc(v['c']['bound_status'])}</td></tr></table>")
    t6 = (f"<div class=note><b>6 · Calibration-probe result.</b> "
          f"t_p (fitted) = {_fmtv(v['t_p']['fitted'])} s [{_pbadge(v['t_p']['provenance'])}], "
          f"pA (fixed) = {_fmtv(f['pA']['value'])} Pa [{_pbadge(f['pA']['provenance'])}], "
          f"<b>derived exposure = pA×t_p = {_fmtv(f['exposure_warm'])} → {_fmtv(f['exposure_fit'])} Pa·s</b> "
          f"(<i>{esc(f['exposure_note'])}</i>); c = {_fmtv(v['c']['initial'])} → {_fmtv(v['c']['fitted'])} "
          f"[{_pbadge('inverse_fitted')}]. SSE {f['sse_before']:.4g}→{f['sse_after']:.4g}; "
          f"R² {f['r2_warm']:.2f}→{f['r2_fit']:.2f}.</div>"
          f"<div style='text-align:center'><img class=pfit style='max-width:640px' "
          f"src='data:image/png;base64,{inverse_png(f)}'></div>")
    t7 = (f"<div class=note><b>7 · Bounds & convergence.</b> converged={f['converged']}, "
          f"evaluations={f['n_eval']}; boundary-limited: <b>{f['boundary_limited']}</b>"
          + (" — the fit sits ON a bound (a boundary solution, not an interior optimum)"
             if f['boundary_limited'] else "") + ".</div>")
    idn = f["identifiability"]
    t8 = (f"<div class=note><b>8 · Identifiability & provenance caveats.</b> local diagnostic: "
          f"<b>{esc(idn['class'])}</b> — {esc(idn.get('detail', ''))}. <b>{esc(idn['label'])}</b>. "
          f"c is a {esc(C_LABEL)} (ontology mapping {esc(C_ONTOLOGY_STATUS)}); an inverse-fitted c is "
          f"<b>never</b> a literature-reported sticking probability. A better fit does not validate the "
          f"model; a failed fit is not proof of model failure.</div>")
    return t1 + t2 + t3 + t4 + t5 + t6 + t7 + t8


def render_brief(analysis, out_path=None):
    """Render the frozen analysis into the canonical Interpretation Brief. Composition
    only — it changes no status, collapses no plural set, and adds no conclusion."""
    f = analysis["frame"]
    cov = f["coverage"]
    comps = analysis["comparisons"]
    adm = analysis["admissible"]
    ens = analysis["ensemble"]
    diag = ens["diagnosability"]
    clo = analysis["closure"]
    inq = analysis["inquiry"]
    esc = _H.escape

    def card(title, body):
        return f"<div class=card><h2>{esc(title)}</h2>{body}</div>"

    # ---- 0 disclaimer ----
    disc = ("<div class=disclaimer><b>This is a discovery-support brief, not a verdict.</b> M3 "
            "organizes evidence and proposes questions; it does not conclude, validate, or discover. "
            "Every claim carries an epistemic status. Agreement is not truth; disagreement is not model "
            "failure; the measured profiles are fallible extractions, not ground truth. Scientific "
            "judgement — choosing among explanations, adopting questions — remains with the researcher, "
            "outside this run.</div>")

    # ---- 1 executive summary ----
    n_non = sum(1 for c in comps if c["status"] == "non_comparable")
    s1 = (disc
          + "<div class=note style='margin-top:12px'><b>Research question.</b> "
          + esc(f["research_question"]) + "</div>"
          + f"<div class=bar>"
          f"<div class=stat><b>{cov['n_candidates']}</b><span>candidate profiles</span></div>"
          f"<div class=stat><b>{len(adm)}</b><span>admissible comparisons</span></div>"
          f"<div class=stat><b>{n_non}</b><span>non-comparable (refused)</span></div>"
          f"<div class=stat><b>{len(clo['insufficient_evidence'])}</b><span>insufficient evidence</span></div>"
          f"<div class=stat><b>{len(cov['untested_regions'])}</b><span>untested regions</span></div>"
          f"<div class=stat><b>{cov['n_sources']}</b><span>evidence sources</span></div>"
          f"</div>"
          f"<div class=note><b>Diagnosability: {esc(diag['verdict'])}.</b> {esc(diag['basis'])}. "
          f"Because of this, no unique cause is attributed and no anomaly is over-claimed.</div>")

    # ---- 1b corpus + candidate funnel: what the twin was (not) validated against ----
    corpus = f.get("corpus") or {}
    funnel = f.get("candidate_funnel") or {}
    exclc = f.get("exclusions_by_stage") or {}
    stage_label = {
        "semantic_result_series": "semantic ResultSeries (declared corpus)",
        "measured_series": "experimental (measured) series",
        "profile_compatible": "profile-compatible representation (ontology targets, ≥6 points)",
        "one_per_measurement_act": "one representation per MeasurementAct",
        "resolved_single_case": "resolved single Condition Case"}
    frows = "".join(
        f"<tr><td>{esc(stage_label.get(k, k))}</td><td class=m>{v}</td>"
        f"<td class=m>{exclc.get(k, '')}</td></tr>"
        for k, v in funnel.items())
    frows += (f"<tr><td>actually evaluated (admissible comparisons)</td>"
              f"<td class=m>{len(adm)}</td><td class=m></td></tr>")
    s1 += (
        f"<div class=note style='margin-top:12px'><b>Evidence source.</b> All validation "
        f"candidates come from the <b>production semantic corpus</b>: "
        f"{corpus.get('included_papers', '?')} papers declared by "
        f"<span class=m>{esc(str(corpus.get('manifest')))}</span>; excluded reviews "
        f"({esc(', '.join(corpus.get('excluded_reviews') or []))}) are never read. "
        f"Candidate identity and representation reachability are the Workbench "
        f"authority (build {esc(str(corpus.get('workbench_head_sha')))}, code "
        f"{esc(str(corpus.get('workbench_code_sha')))}); observations are source "
        f"ResultSeries points on canonical ontology representations, and conditions "
        f"come from each series' linked ExperimentalCase.</div>"
        f"<table><tr><th>candidate funnel</th><th>count</th><th>excluded here</th></tr>"
        f"{frows}</table>")

    # ---- run-level Model Input Provenance Summary (defaults/unresolved made prominent) ----
    ips = analysis.get("input_provenance_summary", {})
    bp = ips.get("by_provenance", {})
    prov_stats = "".join(
        f"<div class=stat><b>{_pbadge(k)}</b><span>{v} model inputs</span></div>"
        for k, v in sorted(bp.items(), key=lambda x: -x[1]))
    fit_stats = (f"<div class=stat><b>{ips.get('n_1d_fits', 0)}</b><span>1-D fits (c only, dose extracted)</span></div>"
                 f"<div class=stat><b>{ips.get('n_2d_fits', 0)}</b><span>2-D fits (t_p &amp; c)</span></div>"
                 f"<div class=stat><b style='color:#c62b2b'>{ips.get('boundary_limited_fits', 0)}</b>"
                 f"<span>boundary-limited fits</span></div>"
                 f"<div class=stat><b>{ips.get('ridge_or_broad_fits', 0)}</b>"
                 f"<span>broad / ridge (weak identifiability)</span></div>")
    # run-level Model Resolution Summary (outcome counts, most-defaulted, per-experiment dependence)
    mrs = analysis.get("model_resolution_summary", {})
    bo = mrs.get("by_outcome", {})
    out_stats = "".join(
        f"<div class=stat><b>{_obadge(k)}</b><span>{v}</span></div>"
        for k, v in sorted(bo.items(), key=lambda x: -x[1]) if v)
    most_def = ", ".join(f"<span class=mono>{esc(a)}</span>×{n}" for a, n in mrs.get("parameters_most_defaulted", []) if n)
    most_imp = ", ".join(f"<span class=mono>{esc(a)}</span>×{n}" for a, n in mrs.get("parameters_most_imputed", []) if n)
    confl = mrs.get("parameters_conflicting", [])
    unres = mrs.get("parameters_unresolved", [])
    s_prov = (f"<div class=note><b>Model-input provenance summary</b> across the {len(adm)} admissible "
              f"comparisons ({mrs.get('total_resolved_instances', 0)} resolved input instances). Model-default "
              f"and unresolved inputs are the weakest — the calibration probe (§10 and per-row) then fits the "
              f"adjustable parameters. Fitted c is a <span class=mono>{esc(C_LABEL)}</span>; its ontology "
              f"mapping to a literature sticking probability is "
              f"<b>{esc(ips.get('c_ontology_mapping_status', 'unresolved'))}</b>.</div>"
              f"<div class=note><b>By provenance category:</b></div><div class=bar>{prov_stats}</div>"
              f"<div class=note><b>By resolution outcome:</b></div><div class=bar>{out_stats}</div>"
              f"<div class=note><b>Calibration probes:</b></div><div class=bar>{fit_stats}</div>"
              f"<div class=note><b>Parameters most defaulted:</b> {most_def or '—'} · "
              f"<b>most imputed:</b> {most_imp or '—'} · <b>conflicting evidence:</b> "
              f"{('<span class=mono>' + esc(', '.join(confl)) + '</span>') if confl else 'none'} · "
              f"<b>unresolved:</b> {('<span class=mono>' + esc(', '.join(unres)) + '</span>') if unres else 'none'}.</div>"
              f"<div class=note><b>Experiments with the highest default dependence:</b> "
              + ", ".join(f"<span class=mono>{esc(e)}</span> ({int(fr*100)}% default)"
                          for e, fr in mrs.get("experiments_highest_default_dependence", [])[:3])
              + ". Evidence composition is shown so the researcher can judge it — no single confidence score "
              "is computed.</div>")

    # ---- 2 what was compared (prediction vs observation) ----
    sc = _brief_scatter(adm)
    rows = ""
    order = sorted(comps, key=lambda c: (c["status"] != "comparison_result",
                                         -(c.get("r2") or -9)))
    for c in order:
        st = c["status"]
        if st == "comparison_result":
            # readable input chips (name shown; value/unit/provenance in the tooltip)
            chips = []
            for r in c.get("model_input_trace", []):
                if r["attr"] in _KEY_INPUT:
                    title = f"{_KEY_INPUT[r['attr']]} = {_fmtv(r['value'])} {r['unit']} · {r['provenance']}"
                    chips.append(f'<span class="badge {_PROV_CLS.get(r["provenance"], "s-ano")}" '
                                 f'title="{esc(title)}">{esc(_KEY_INPUT[r["attr"]])}</span>')
            prov_in = " ".join(chips)
            detail = (f"<tr class=disc><td colspan=7>{_trace_html(c)}</td></tr>")
            rows += (f"<tr class=prow onclick='tog(this)'><td class=mono>▸ {esc(c['exp_id'])}</td>"
                     f"<td class=mono>{esc(c['paper'])}</td><td>{_badge(st)}</td>"
                     f"<td class=mono>{esc(str(c.get('shape_fit')))}</td>"
                     f"<td class=mono>{(c.get('severity') or {}).get('level','—')}</td>"
                     f"<td class=mono>{_um(c.get('pd_meas'))} / {_um(c.get('pd_twin'))}</td>"
                     f"<td>{prov_in or '—'}</td></tr>{detail}")
        else:
            bq = c.get("boundary_question") or {}
            why = "; ".join(r["detail"] for r in c["commensurability"]["reasons"])
            rows += (f"<tr><td class=mono>{esc(c['exp_id'])}</td><td class=mono>{esc(c['paper'])}</td>"
                     f"<td>{_badge(st)}</td><td colspan=4 class=mut>{esc(why)} "
                     f"→ <i>{esc(bq.get('text',''))}</i></td></tr>")
    s2 = (s_prov
          + f"<div class=note style='margin-top:12px'>Each admissible pairing is a <b>prediction versus "
          f"observation</b> on the same observable. Non-comparable pairings are <b>refused as tests</b> "
          f"(never scored) and yield a boundary question instead. Observed profiles are extractions, not "
          f"ground truth. <b>Click any row</b> for its full computational trace (observed data → model "
          f"inputs → prediction → metrics → calibration probe → bounds → identifiability).</div>"
          f"<div style='text-align:center;margin:6px 0'><img style='max-width:460px' "
          f"src='data:image/png;base64,{sc}'></div>"
          f"<table><tr><th>experiment</th><th>source</th><th>status</th><th>shape fit</th>"
          f"<th>severity</th><th>PD50 obs / pred</th><th>key inputs (hover)</th></tr>{rows}</table>")

    # ---- 3 what the evidence supports ----
    if clo["supports"]:
        sup_rows = "".join(
            f"<li>{_badge(i['status'])} <b>{esc(i['claim'])}</b> "
            f"<div class=note>basis: {esc(i['support_basis'])} · scope: {esc(i['scope'])} · "
            f"severity: {esc(str(i['test_severity']))}</div>"
            f"<div class=note>alternatives still open: {esc('; '.join(i['alternatives_remaining_open']))}</div></li>"
            for i in clo["supports"])
        s3 = f"<ul>{sup_rows}</ul>"
    else:
        s3 = ("<div class=note>No forward prediction reached the descriptive shape-agreement threshold, "
              "so <b>no supported interpretation is claimed</b> from the forward comparison.</div>")
    for ins in clo.get("insights", []):
        s3 += f"<div class=note>{_badge('insight')} {esc(ins['text'])}</div>"

    # ---- 4 what the evidence challenges + plural explanation space ----
    from collections import Counter
    locus_live = Counter()
    for i in clo["challenges"]:
        for lo in i["alternatives_remaining_open"]:
            locus_live[lo] += 1
    live_rows = "".join(
        f"<tr><td class=mono>{esc(lo)}</td><td class=mono>{n}</td></tr>"
        for lo, n in sorted(locus_live.items(), key=lambda x: -x[1]))
    ch_rows = ""
    for i in clo["challenges"][:12]:
        c = next((x for x in adm if x["exp_id"] == i["exp_id"]), None)
        exps = (c or {}).get("explanations", [])
        ex_list = "".join(
            f"<li>{_badge(e['status'])} <b>{esc(e['locus'])}</b> — {esc(e['evidence_for'])}"
            + (f" <span class=mut>(against: {esc(e['evidence_against'])})</span>" if e.get('evidence_against') else "")
            + f"<div class=note>testability: {esc(e['testability'])}</div></li>" for e in exps)
        ch_rows += (f"<tr class=prow onclick='tog(this)'><td class=mono>▸ {esc(i['exp_id'])}</td>"
                    f"<td class=mut>{esc(i['challenge_basis'])}</td>"
                    f"<td class=mono>{len(i['alternatives_remaining_open'])} live loci</td></tr>"
                    f"<tr class=disc><td colspan=3><div class=note>Plural, non-exclusive explanations — "
                    f"none is selected:</div><ul>{ex_list}</ul></td></tr>")
    more = ("" if len(clo["challenges"]) <= 12 else
            f"<div class=note>Showing 12 of {len(clo['challenges'])} challenged comparisons "
            f"(full set in the analysis object).</div>")
    s4 = (f"<div class=note>The forward twin on <b>default kinetics</b> does not reproduce most observed "
          f"profiles. Each discrepancy is left with a <b>plural, non-exclusive</b> explanation space across "
          f"the six co-equal loci; none is selected. The model is one locus of six — disagreement is not "
          f"model failure.</div>"
          f"<div class=note><b>Live explanations across challenged comparisons</b> (how many list each locus):</div>"
          f"<table><tr><th>explanatory locus</th><th>appears in N challenges</th></tr>{live_rows}</table>"
          f"<div class=note style='margin-top:10px'><b>Per-comparison explanation space</b> "
          f"(click to expand):</div>"
          f"<table><tr><th>experiment</th><th>challenge basis</th><th>explanations</th></tr>{ch_rows}</table>{more}")

    # ---- 5 assumptions ----
    a_rows = "".join(
        f"<tr><td>{_badge('assumption')}</td><td class=mono>{esc(a['name'])}</td>"
        f"<td>{esc(a['detail'])}</td><td class=mut>{esc(a['affects'])}</td></tr>"
        for a in clo["load_bearing_assumptions"])
    s5 = (f"<div class=note>Everything the brief rests on that was not measured for this run. Each names "
          f"the conclusion that depends on it.</div>"
          f"<table><tr><th></th><th>assumption</th><th>detail</th><th>affects</th></tr>{a_rows}</table>")

    # ---- 6 unresolved / non-comparable / insufficient / untested ----
    unr = "".join(f"<li>{_badge('unresolved')} {esc(u['detail'])}</li>" for u in clo["unresolved"])
    noncmp = "".join(
        f"<li>{_badge('non_comparable')} <span class=mono>{esc(c['exp_id'])}</span> — "
        f"{esc('; '.join(r['detail'] for r in c['commensurability']['reasons']))}</li>"
        for c in clo["non_comparable"])
    unt = "".join(f"<li>{_badge('untested_region')} {esc(u['note'])}</li>" for u in clo["untested_regions"])
    s6 = (f"<div class=note>These are first-class results, kept visibly distinct — not swept into a verdict.</div>"
          f"<div class=note><b>Unresolved attributions.</b><ul>{unr or '<li>none</li>'}</ul></div>"
          f"<div class=note><b>Insufficient evidence.</b> {_badge('insufficient_evidence')} "
          f"Quantitative agreement is unavailable for all {len(clo['insufficient_evidence'])} admissible "
          f"comparisons because no measurement uncertainty is extracted in the corpus — confidence is "
          f"withheld, not fabricated.</div>"
          f"<div class=note><b>Non-comparable (refused as tests).</b><ul>{noncmp or '<li>none</li>'}</ul></div>"
          f"<div class=note><b>Untested regions.</b><ul>{unt or '<li>none</li>'}</ul></div>")

    # ---- 7 preserved anomalies ----
    if clo["preserved_anomalies"]:
        pa_rows = "".join(
            f"<li>{_badge('preserved_anomaly')} <span class=mono>{esc(p['exp_id'])}</span> — {esc(p['detail'])}"
            f"<div class=note>live explanations: {esc(', '.join(p['live_explanations']))}</div></li>"
            for p in clo["preserved_anomalies"])
        s7 = f"<div class=note>Robust discrepancies kept open, never explained away.</div><ul>{pa_rows}</ul>"
    else:
        s7 = ("<div class=note>{b} <b>No preserved anomaly can be robustly established</b> under "
              "<b>{v}</b> diagnosability: with the evidence dominated by a single source and no "
              "measurement uncertainty, mundane explanations (parameterization, inputs, measurement, "
              "extraction) cannot be ruled out for any discrepancy. The discrepancies are retained as "
              "challenged + unresolved (§4, §6) — not explained away, and not over-claimed as anomalies."
              ).format(b=_badge('preserved_anomaly'), v=esc(diag['verdict']))

    # ---- 8 evidence closure ----
    s8 = (f"<div class=note>The account of what the current evidence can support is now closed — before "
          f"asking what evidence should come next.</div>"
          f"<div class=disclaimer style='border-color:#b37a00;background:rgba(237,161,0,.07)'>"
          f"<b>{esc(clo['closure_statement'])}</b></div>")

    # ---- 9 discriminating questions ----
    q_rows = "".join(
        f"<tr><td>{_badge(x['status'])}</td><td>{esc(x['text'])}</td>"
        f"<td>{''.join(f'<span class=pill>{esc(s)}</span>' for s in x['separates'])}</td>"
        f"<td class=mono>{x['feasibility']}</td><td class=mono>{x['rank_score']}</td></tr>" for x in inq)
    s9 = (f"<div class=note>Proposals for the researcher — <b>not findings and not an adopted agenda</b>. "
          f"Ranked by a transparent heuristic (separating power × feasibility), <b>not</b> "
          f"expected-information-gain. Each is M3-generated and names the explanations it would separate.</div>"
          f"<table><tr><th>type</th><th>question / evidence need</th><th>separates</th>"
          f"<th>feasibility</th><th>rank</th></tr>{q_rows}</table>")

    # ---- 10 provenance appendix + parameterization exhibit ----
    byid = {e.get("exp_id"): e for e in _targets()}
    recs = sorted((c for c in adm if c.get("_inverse_fit")),
                  key=lambda c: -(c["_inverse_fit"]["r2_fit"] - c["_inverse_fit"]["r2_warm"]))
    show = recs[:8]
    inv_rows = ""
    for c in show:
        fj = c["_inverse_fit"]
        v = fj["variables"]
        png = inverse_png(fj)
        bl = ("<span class='badge s-ano'>boundary-limited</span>" if fj["boundary_limited"] else "")
        inv_rows += (f"<tr class=prow onclick='tog(this)'><td class=mono>▸ {esc(c['exp_id'])}</td>"
                     f"<td class=mono>{esc('+'.join(fj['active_variables']))} "
                     f"({'2-D' if fj['dose_free'] else '1-D'})</td>"
                     f"<td class=mono>R² {fj['r2_warm']:.2f}→{fj['r2_fit']:.2f}</td>"
                     f"<td class=mono>c {v['c']['initial']:.3f}→{v['c']['fitted']:.4f} "
                     f"[{esc(v['c']['bound_status'])}]</td>"
                     f"<td class=mono>{_fmtv(fj['exposure_warm'])}→{_fmtv(fj['exposure_fit'])} Pa·s</td>"
                     f"<td>{esc(fj['identifiability']['class'])} {bl}</td></tr>"
                     f"<tr class=disc><td colspan=6>{_trace_html(c)}</td></tr>")
    prov_note = ("<div class=note>Observed profiles are digitised extractions "
                 f"(extractor: <span class=mono>{esc(str((comps[0].get('observation_provenance') or {}).get('extractor')))}</span>), "
                 "each a fallible hypothesis. The corpus carries <b>no measurement uncertainty</b> and "
                 "<b>no calibration flag</b>, so both remain <span class=mono>unresolved</span>. Precursor "
                 "partial-pressure evidence being absent <i>in this processed corpus</i> is NOT a claim that "
                 "it is absent from the literature — full pressure extraction is not complete.</div>")
    s10 = (prov_note
           + "<div class=note style='margin-top:8px'><b>Parameterization exhibit (calibration probe).</b> "
           "Holding the extracted conditions fixed and fitting the ADJUSTABLE model parameter(s): the "
           f"<span class=mono>{esc(C_LABEL)}</span> (always), and the pulse time t_p only when the dose was "
           "not extracted. <b>Exposure = pA×t_p is DERIVED, never independently fitted.</b> Bounds are "
           "explicit; the fit reports a <b>feasible fitted parameterization, not a unique physical "
           "estimate</b>. This evidences the 'parameterization' explanation; it is not out-of-sample support, "
           "and an inverse-fitted c is never a literature sticking probability. "
           f"Showing {len(show)} of {len(recs)} admissible profiles (largest recovery first); "
           "click a row for the full computational trace.</div>"
           f"<table><tr><th>experiment</th><th>fitted vars</th><th>R² warm→fit</th>"
           f"<th>c warm→fit [bound]</th><th>derived exposure warm→fit</th><th>identifiability</th></tr>{inv_rows}</table>")

    # ---- 11 Model Input Evidence Coverage (coverage-gap exhibit) ----
    cov = analysis.get("evidence_coverage", [])
    _ONTO_LBL = {"ontology_supported": ("ontology-supported", "s-sup"),
                 "not_represented_in_ontology": ("not in ontology", "s-ins"),
                 "model_specific_unresolved_mapping": ("model-specific (unresolved mapping)", "s-asm"),
                 "derived": ("derived", "s-can")}
    cov_rows = ""
    for pm in cov:
        lbl, cls = _ONTO_LBL.get(pm["ontology_support"], (pm["ontology_support"], "s-ano"))
        weak = (pm["defaulted"] >= max(1, pm["n"]) * 0.5) or pm["unresolved"] > 0 or pm["conflicting"] > 0
        hlw = ' style="background:rgba(227,73,72,.05)"' if weak else ''
        cov_rows += (f"<tr{hlw}>"
                     f"<td class=mono>{esc(str(pm['canonical']) if pm['canonical'] else '—')}</td>"
                     f"<td class=mono>{esc(pm['attr'])}</td>"
                     f"<td><span class='badge {cls}'>{esc(lbl)}</span></td>"
                     f"<td class=mono>{pm['accepted_direct']}</td><td class=mono>{pm['derived']}</td>"
                     f"<td class=mono>{pm['imputed']}</td>"
                     f"<td class=mono style='color:#c62b2b'>{pm['defaulted']}</td>"
                     f"<td class=mono>{pm['unresolved']}</td><td class=mono>{pm['conflicting']}</td>"
                     f"<td class=mono>{'yes' if pm['fitted_in_probe'] else '—'}</td>"
                     f"<td class=mut style='font-size:11px'>{esc(pm['consequence'])}</td></tr>")
    s11 = (f"<div class=note>For every model-consumed parameter: its ontology support status and how its "
           f"evidence resolved across the {len(adm)} admissible comparisons. Missing evidence is described as "
           f"<b>no accepted canonical evidence in the current corpus</b> — <b>not</b> as absence from the "
           f"literature (extraction coverage is incomplete). Defaulted counts are highlighted; the "
           f"consequence column is descriptive, not a verdict, and parameters are not equally important.</div>"
           f"<div style='overflow-x:auto'><table><tr><th>canonical</th><th>attr</th><th>ontology support</th>"
           f"<th>direct/extracted</th><th>derived</th><th>imputed</th><th>defaulted</th><th>unresolved</th>"
           f"<th>conflicting</th><th>fitted in probe</th><th>consequence of missing evidence</th></tr>"
           f"{cov_rows}</table></div>")

    body = f"""<title>M3 · Interpretation Brief</title><style>{_BRIEF_CSS}</style>{_BRIEF_JS}
<div class=wrap>
<div class=eyebrow>PSED · M3 · discovery support</div>
<h1>M3 · Interpretation Brief</h1>
<div class=sub>Prediction versus observation for the KB-parameterised conformality twin — organized for
researcher interpretation. Model: <span class=mono>{esc(MODEL_ID)}</span>.</div>
{card("1 · Executive summary", s1)}
{card("2 · What was compared (prediction versus observation)", s2)}
{card("3 · What the evidence supports", s3)}
{card("4 · What the evidence challenges — plural explanation space", s4)}
{card("5 · Load-bearing assumptions", s5)}
{card("6 · Unresolved, non-comparable, insufficient, untested", s6)}
{card("7 · Preserved anomalies", s7)}
{card("8 · Evidence closure", s8)}
{card("9 · Discriminating questions (proposals for the researcher)", s9)}
{card("10 · Provenance and parameterization exhibit", s10)}
{card("11 · Model Input Evidence Coverage", s11)}
</div>"""
    out = Path(out_path) if out_path else HERE / "m3_validation.html"
    out.write_text(body)
    if out_path is None:
        import shutil
        dst = HERE.parent / "reports" / "04_twin_mpc__m3_validation.html"
        shutil.copyfile(out, dst)
        print(f"copied -> {dst}")
    return out


def main():
    analysis = analyze()
    out = render_brief(analysis)
    f, ens, clo = analysis["frame"], analysis["ensemble"], analysis["closure"]
    print("wrote", out, "  (M3 Interpretation Brief)")
    print(f"  research question    = {f['research_question'][:70]}…")
    print(f"  candidates           = {f['coverage']['n_candidates']} "
          f"({f['coverage']['n_sources']} sources); untested = "
          f"{[u['value'] for u in f['untested_regions']]}")
    print(f"  admissible / refused = {len(analysis['admissible'])} / "
          f"{sum(1 for c in analysis['comparisons'] if c['status']=='non_comparable')}")
    print(f"  diagnosability       = {ens['diagnosability']['verdict']}")
    print(f"  supports/challenges  = {len(clo['supports'])} / {len(clo['challenges'])}  "
          f"insufficient={len(clo['insufficient_evidence'])} preserved_anomalies={len(clo['preserved_anomalies'])}")
    print(f"  live explanations    = {clo['live_explanations']}")
    print(f"  discriminating Qs    = {len(analysis['inquiry'])}")


if __name__ == "__main__":
    main()
