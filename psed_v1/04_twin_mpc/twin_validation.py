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
import base64, io, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
PIPE = HERE.parent / "02_extraction"
sys.path.insert(0, str(PIPE))
from channel_model import channelModel, MODEL_ID
from scipy.optimize import minimize
import similarity as sim
import kb_service as ks

# the geometry classes this twin's ontology model is valid for (geometry-scoped validation)
_ONTO = json.load(open(HERE.parent / "01_ontology" / "ald_ontology.json"))
TWIN_GEOMETRY = next((m.get("applies_to_geometry") for m in _ONTO.get("models", [])
                      if m["id"] == MODEL_ID), None) or []

BLUE, RED, GREEN, AMBER, PURPLE, INK, GREY = "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#9085e9", "#14161a", "#8b919b"
NM = 1e-9
PLAUSIBLE_GAP_M = (5e-8, 5e-6)          # a Pillarhall/LHAR gap height is ~0.1–2 µm
DEFAULT_H = 0.5e-6                        # LHAR standard gap when geometry is missing/suspect
DEFAULT_W = 1e-4                          # channel width ≫ height; exact value barely matters

_CORPUS = _SC = None


def _ctx():                              # corpus + similarity scale, for imputation
    global _CORPUS, _SC
    if _CORPUS is None:
        _CORPUS = ks._load()
        _SC = sim.logscale(_CORPUS)
    return _CORPUS, _SC


def _cond(exp, q, r=None):
    for c in exp.get("controlled") or []:
        if c.get("quantity") == q and (r is None or c.get("of_reactant") == r):
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
        est = ks.impute(exp, q, r, corpus=corpus, SC=SC)
        if est:
            return est["value"], "imputed"
    return None, "default"


def build_twin(exp):
    """Construct a twin for this experiment. Process parameters (dose, T, pA, gpc)
    are taken from THIS experiment, else covariate-imputed from the KB, else the
    model default. Geometry (gap height H) is taken or assumed (never imputed —
    it's structure-specific). Returns the twin, notes, and `prov` = {input: state}
    where state is extracted | imputed | default."""
    mat = exp.get("material")
    prec = next((r.get("species") for r in exp.get("reactants") or [] if r.get("role") == "precursor"), None)
    carrier = (exp.get("carrier_gas") or {}).get("species") or "N2"
    m = channelModel.from_kb(mat, species={"A": prec} if prec else None, carrier=carrier)
    notes, prov = [], {}

    tp, prov["dose"] = _input(exp, "pulse_time", "A")
    if prov["dose"] == "default":
        tp, prov["dose"] = _input(exp, "pulse_time", "B")
    if tp:
        m.t_p = tp
    T, prov["T"] = _input(exp, "temperature")
    if T is not None:
        m.T = T + 273.15
    # Typed precursor partial pressure (precedence: precursor_partial_pressure >
    # reactant_A_partial_pressure > partial_pressure) takes priority; a
    # chamber/working/base/generic pressure can never satisfy this. Falls back to the
    # legacy imputing path only when no typed precursor pressure exists.
    import pressure_compat as _pc
    _pav, _pac = _pc.precursor_pressure(exp)
    if _pav is not None:
        pA, prov["pA"] = _pav, "extracted"
    else:
        pA, prov["pA"] = _input(exp, "partial_pressure", "A")
    if pA:
        m.pA = pA
    gpc, prov["gpc"] = _input(exp, "growth_per_cycle")
    if gpc:
        m.gpc = gpc * NM
    # geometry: gap height H (diffusion-limiting) — extracted or assumed, not imputed
    H, _ = _input(exp, "feature_height", impute=False)
    Hm = H * NM if H else None
    if Hm and PLAUSIBLE_GAP_M[0] <= Hm <= PLAUSIBLE_GAP_M[1]:
        m.H = Hm; prov["H"] = "extracted"
    else:
        prov["H"] = "default"
        notes.append(f"feature_height {H:g} nm out of gap range → assumed {DEFAULT_H*1e6:g} µm"
                     if Hm else f"no feature_height → assumed {DEFAULT_H*1e6:g} µm gap")
        m.H = DEFAULT_H
    for k in ("dose", "T", "pA", "gpc"):                 # note imputed process inputs
        if prov[k] == "imputed":
            notes.append(f"{k} imputed (KB estimate)")
    W, _ = _input(exp, "feature_width", impute=False)
    m.W = W * NM if (W and W * NM > m.H) else DEFAULT_W
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


def _targets(criteria=DEFAULT_CRITERIA):
    """Candidate ensemble for the criteria — membership by observable/scope only, never by
    outcome or commensurability. Reproduces the legacy run() filter exactly."""
    E = []
    for f in sorted((PIPE / "output").glob("*/resolved/experiments.json")):
        E += json.load(open(f))
    return [e for e in E if _member(e, criteria)]


def _coverage(targets, criteria=DEFAULT_CRITERIA):
    """Census over candidates + untested regions (model-valid geometry buckets with zero
    candidates). Descriptive; uses candidates only, never outcome."""
    from collections import Counter
    by_geo = Counter(e.get("geometry_class") for e in targets)
    by_mat = Counter(e.get("material") for e in targets)
    by_src = Counter((e.get("exp_id") or "").split("-")[0] for e in targets)
    valid_geo = criteria["model_validity"]["geometry"]
    untested = [{"dimension": "geometry_class", "value": g, "status": "untested_region",
                 "note": f"model-valid geometry '{g}' has no candidate profile in the corpus"}
                for g in valid_geo if by_geo.get(g, 0) == 0]
    return {"n_candidates": len(targets), "by_geometry_class": dict(by_geo),
            "by_material": dict(by_mat), "by_source": dict(by_src),
            "n_sources": len(by_src), "untested_regions": untested}


def _frame(question, criteria, targets, is_default):
    cov = _coverage(targets, criteria)
    return {"research_question": question, "is_default": bool(is_default),
            "comparability_criteria": criteria, "coverage": cov,
            "untested_regions": cov["untested_regions"]}


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
    statuses = set()
    for c in exp.get("controlled") or []:
        st = (((c.get("origin") or {}).get("card_provenance") or {}).get("status"))
        if st:
            statuses.add(st)
    return {"doi": p.get("doi"), "figure": p.get("figure"), "extractor": p.get("extractor"),
            "extraction_status": sorted(statuses) or ["unspecified"],
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
            "paper": (exp.get("exp_id") or "").split("-")[0],
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

    base.update({"status": "comparison_result",
                 "r2": r2, "nrmse": cm.get("nrmse") if cm else None,
                 "overlap": cm.get("overlap") if cm else None,
                 "pd_meas": pd_m, "pd_twin": pd_t, "pd_rel": rel,
                 "combined_tolerance": tol, "severity": _severity(xm, ym),
                 "quantitative_agreement_status": "insufficient_evidence",  # measurement σ unresolved
                 "shape_fit": shape,
                 "t_p": twin.t_p, "T": twin.T - 273.15, "H_um": twin.H * 1e6,
                 "_twin": (xt_um, yt),
                 "verdict": lverdict, "kind": lkind, "agree": lagree})  # dormant legacy
    return base


# ---- R4: ensemble patterns + diagnosability (after the barrier) --------------
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
                 "evidence_for": (f"a plausible change to exposure / sticking c recovers the profile "
                                  f"(R² {inv['r2_warm']:.2f}→{inv['r2_fit']:.2f})" if inv else
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
                 "text": (f"the forward twin on DEFAULT kinetics reproduces few profile shapes; a fitted change "
                          f"to exposure / sticking c recovers {n_rec}/{len(admissible)} of them, so "
                          f"'parameterization' is a strongly live explanation for the shortfall — this is a "
                          f"calibration probe, not out-of-sample support")}]
    # ===== EVIDENCE CLOSURE =====
    closure = _evidence_closure(comparisons, admissible, interps, exps_all, assumptions,
                                preserved, frame, diagn, insights)
    inquiry = _discriminating_questions(closure, diagn, frame)
    # ===== FREEZE ===== (the returned object is immutable by contract)
    return {"frame": frame, "comparisons": comparisons, "admissible": admissible,
            "ensemble": {"patterns": patterns, "diagnosability": diagn},
            "closure": closure, "inquiry": inquiry}


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


# ---------- inverse fit: recover the ASSUMED (imputed) conditions -------------
def _r2(y, yt):
    y = np.asarray(y, float); yt = np.asarray(yt, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yt) ** 2) / ss) if ss > 0 else -9.0


def inverse_fit(exp):
    """Hold the EXTRACTED conditions fixed, warm-start the IMPUTED ones, and optimise the
    two identifiable free parameters — exposure (pA·t_p) and the lumped sticking coefficient
    c — to reproduce the measured profile on its own coordinate. This mirrors how the source
    papers extract c by fitting the Ylilammi model to the saturation profile. Returns the
    recovered values, the warm→fit R², and the search trajectory for visualisation."""
    twin, notes, prov = build_twin(exp)
    meas = measured_profile(exp)
    if not meas:
        return None
    xm, ym = meas
    xg = np.array(xm) * 1e-6
    ym = np.array(ym, float)
    wtp, wc, pA = twin.t_p, twin.c, twin.pA
    dose_free = prov.get("dose") != "extracted"     # free exposure only if dose was NOT extracted

    def curve(lm, lc):
        twin.t_p = wtp * np.exp(lm) if dose_free else wtp
        twin.c = float(np.clip(wc * np.exp(lc), 1e-5, 1.0))
        twin.prepare()
        th, _, _ = twin.approx(xg, np.zeros_like(xg))
        t0 = th[0] if th[0] > 0 else (th.max() or 1)
        return np.clip(th / t0, 0, None)

    lm_grid = np.linspace(-2.5, 2.5, 11) if dose_free else np.array([0.0])
    grid = [(lm, lc) for lm in lm_grid for lc in np.linspace(-2.5, 2.5, 11)]
    best = min(grid, key=lambda p: float(np.mean((curve(*p) - ym) ** 2)))   # robust warm-start
    traj = []
    def sse(p):
        yt = curve(p[0], p[1]); traj.append((float(p[0]), float(p[1]), _r2(ym, yt)))
        return float(np.mean((yt - ym) ** 2))
    res = minimize(sse, list(best), method="Nelder-Mead",
                   options={"maxiter": 120, "xatol": 1e-3, "fatol": 1e-7})
    lm, lc = res.x
    # ~7 representative curves along the search, ordered warm→converged by R²
    cand = {(0.0, 0.0), tuple(best), (lm, lc)} | {(a, b) for a, b, _ in traj}
    scored = sorted((_r2(ym, curve(a, b)), a, b) for a, b in cand)
    picks = [scored[int(i)] for i in np.linspace(0, len(scored) - 1, min(7, len(scored)))]
    curves = [(round(r, 3), list(curve(a, b))) for r, a, b in picks]
    return {
        "exp_id": exp["exp_id"], "geometry_class": exp.get("geometry_class"),
        "dose_free": dose_free, "niter": len(traj),
        "r2_warm": _r2(ym, curve(0, 0)), "r2_fit": _r2(ym, curve(lm, lc)),
        "expo_warm": wtp * pA, "expo_fit": (wtp * np.exp(lm) if dose_free else wtp) * pA,
        "c_warm": wc, "c_fit": float(np.clip(wc * np.exp(lc), 1e-5, 1)),
        "xm": list(xm), "ym": list(ym), "curves": curves,
        "r2track": [t[2] for t in traj],
    }


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

    # ---- 2 what was compared (prediction vs observation) ----
    sc = _brief_scatter(adm)
    rows = ""
    order = sorted(comps, key=lambda c: (c["status"] != "comparison_result",
                                         -(c.get("r2") or -9)))
    for c in order:
        st = c["status"]
        if st == "comparison_result":
            prov_in = " ".join(f"<span class=pill>{esc(k)}</span>" for k in c["measured"]) \
                + "".join(f"<span class=pill>{esc(k)}~</span>" for k in c["imputed"])
            png = _brief_profile_png(c)
            detail = (f"<tr class=disc><td colspan=7><img class=pfit src='data:image/png;base64,{png}'>"
                      f"<div class=note>shape fit is descriptive only; quantitative agreement is "
                      f"<b>insufficient_evidence</b> (no measurement uncertainty).</div></td></tr>")
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
    s2 = (f"<div class=note>Each admissible pairing is a <b>prediction versus observation</b> on the "
          f"same observable, evaluated relative to the available uncertainty. Non-comparable pairings "
          f"are <b>refused as tests</b> (never scored) and yield a boundary question instead. Observed "
          f"profiles are extractions, not ground truth.</div>"
          f"<div style='text-align:center;margin:6px 0'><img style='max-width:460px' "
          f"src='data:image/png;base64,{sc}'></div>"
          f"<table><tr><th>experiment</th><th>source</th><th>status</th><th>shape fit</th>"
          f"<th>severity</th><th>PD50 obs / pred</th><th>input provenance</th></tr>{rows}</table>")

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
        fjson = c["_inverse_fit"]
        png = inverse_png(fjson)
        inv_rows += (f"<tr class=prow onclick='tog(this)'><td class=mono>▸ {esc(c['exp_id'])}</td>"
                     f"<td class=mono>R² {fjson['r2_warm']:.2f}→{fjson['r2_fit']:.2f}</td>"
                     f"<td class=mono>exposure {fjson['expo_warm']:.1f}→{fjson['expo_fit']:.1f} Pa·s</td>"
                     f"<td class=mono>c {fjson['c_warm']:.3f}→{fjson['c_fit']:.4f}</td></tr>"
                     f"<tr class=disc><td colspan=4><img class=pfit style='max-width:640px' "
                     f"src='data:image/png;base64,{png}'></td></tr>")
    prov_note = ("<div class=note>Observed profiles are digitised extractions "
                 f"(extractor: <span class=mono>{esc(str((comps[0].get('observation_provenance') or {}).get('extractor')))}</span>), "
                 "each a fallible hypothesis. The corpus carries <b>no measurement uncertainty</b> and "
                 "<b>no calibration flag</b>, so both remain <span class=mono>unresolved</span>. Precursor "
                 "partial-pressure evidence being absent <i>in this processed corpus</i> is NOT a claim that "
                 "it is absent from the literature — full pressure extraction is not complete.</div>")
    s10 = (prov_note
           + "<div class=note style='margin-top:8px'><b>Parameterization exhibit</b> — holding extracted "
           "conditions fixed and fitting exposure + sticking c (the same inverse procedure the source "
           "papers use to extract c). This is a <b>calibration probe</b> that evidences the "
           "'parameterization' explanation; it is not out-of-sample support. "
           f"Showing {len(show)} of {len(recs)} admissible profiles (largest recovery first).</div>"
           f"<table><tr><th>experiment</th><th>R² warm→fit</th><th>exposure warm→fit</th>"
           f"<th>c warm→fit</th></tr>{inv_rows}</table>")

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
</div>"""
    out = Path(out_path) if out_path else HERE / "m3_validation.html"
    out.write_text(body)
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
