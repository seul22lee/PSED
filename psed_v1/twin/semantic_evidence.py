"""
semantic_evidence.py — the twin's read of the PRODUCTION semantic corpus.

The one interface through which M2/M3 retrieve literature evidence. It replaces
the legacy resolved-Experiment reads (`kb_service._load`) with the declared
corpus authority:

    papers/_corpus/corpus_manifest.json          membership (41 included; the
                                                 excluded reviews are never read)
    papers/<id>/semantic/*.json                  ExperimentalCase / Measurement /
                                                 ResultSeries
    papers/_corpus/workbench/workbench_model.json  representation reachability --
                                                 the SAME identity/comparability
                                                 authority the Workbench uses

Records are emitted in the shape the twin's resolution cascade already consumes
(`material`, `precursors`, `controlled[{quantity, value, unit, of_reactant}]`,
`points`, ...), so the inverse solver, channel model and admissibility logic are
untouched. What changes is what the fields MEAN:

  * chemistry is canonical (chemical_identity): one chemical, one key, with the
    source spelling kept in provenance;
  * `of_reactant` slots (A = precursor, B = co-reactant) are assigned by
    chemical identity against the case's own chemistry -- a species that matches
    neither stays unslotted rather than being reinterpreted;
  * every condition carries its `condition_class`: direct case evidence, known
    context, derived, or interval/unresolved -- so downstream accounting can say
    which inputs were observed and which were context;
  * profile candidates come from ResultSeries whose representations REACH the
    ontology comparison targets (spatial coordinate in canonical µm; a
    thickness-family observable), through the Workbench's own reachability --
    including ontology-authorized derivations such as x/H -> x with a
    case-stated H. No legacy granularity/measurand fields are consulted.

Nothing here names a paper, DOI, figure, chemical or value.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths as P                                               # noqa: E402
from pipeline.canonical import chemical_identity as CI          # noqa: E402
from pipeline.canonical import comparison_targets as CT         # noqa: E402
from pipeline.query import entity_identity as EI                # noqa: E402

WB_MODEL = P.PAPERS / "_corpus" / "workbench" / "workbench_model.json"

#: provenance_type -> the evidence class the twin's accounting reports
_DIRECT = {"directly_stated", "figure_local_direct", "panel_caption_direct",
           "sample_table_direct", "directly_stated_range", "derived_from_table_recipe",
           "inherited_from_sample", "inherited_from_explicit_sample"}
_CONTEXT = {"methods_default", "paper_default"}


def condition_class(provenance_type):
    p = str(provenance_type or "")
    if p in _DIRECT:
        return "direct_case_evidence"
    if p in _CONTEXT:
        return "known_context"
    if p.startswith("derived_"):
        return "derived"
    return "other_evidence"


def _slot(species, quantity, prec_keys, core_keys):
    """A/B slot by CHEMICAL identity against the case's own chemistry.

    A species that resolves to the case's precursor is slot A; to a co-reactant,
    slot B. A species matching neither -- a carrier gas, another chemistry, an
    unresolved chemical -- stays unslotted: it is never reinterpreted as either
    reagent. Where no species is stated, a role-prefixed quantity
    (precursor_/coreactant_...) states the slot itself."""
    if species:
        k = CI.identity_key(str(species))
        if k in prec_keys:
            return "A"
        if k in core_keys:
            return "B"
        return None
    q = str(quantity or "")
    from pipeline.canonical import process_steps as PS
    role = PS.timing_role(q)
    if role == "precursor":
        return "A"
    if role in ("coreactant", "reactant"):
        return "B"
    return None


def _base_quantity(quantity):
    """The unprefixed quantity a role-qualified spelling specialises."""
    from pipeline.canonical import process_steps as PS
    q = str(quantity or "")
    role = PS.timing_role(q)
    if role and q.startswith(role + "_"):
        return q[len(role) + 1:]
    return q


def _num(v):
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def _canonical_value(quantity, value, unit):
    """(value, unit, note) in the ontology's canonical unit for the quantity.

    The twin's resolution cascade consumes one unit per quantity; the ontology
    declares which (nm for feature dimensions, s for step times, Pa for
    pressures, °C for deposition temperature, nm/cycle for GPC). Conversion runs
    through the unit registry; a value whose unit cannot be converted is
    WITHHELD (None) with the reason recorded, never passed through in a unit the
    consumer would misread."""
    if value is None:
        return None, unit, None
    cu = CT.canonical_unit_for(quantity)
    if not cu or not unit or CT.same_unit(unit, cu):
        return value, (cu or unit), None
    from pipeline.canonical import units as U
    try:
        return U.convert(value, unit, cu), cu, "converted from %s" % unit
    except Exception:
        return None, unit, ("unit %r not convertible to canonical %r; value "
                            "withheld" % (unit, cu))


def _controlled(case, prec_keys, core_keys):
    out = []
    for c in case.get("case_defining_conditions") or []:
        q = c.get("quantity")
        if q in ("precursor", "coreactant", "carrier_gas"):
            continue                       # chemistry identity, not a numeric setting
        v = _num(c.get("value"))
        bq = _base_quantity(q)
        v, cu, note = _canonical_value(bq, v, c.get("unit"))
        # the interface GUARANTEES canonical chemical identity regardless of the
        # artifact's vintage: idempotent for already-canonical records
        sp, src_sp = c.get("species"), c.get("source_species_label")
        if sp:
            r = CI.resolve(str(sp))
            if r.get("resolved"):
                canon = r.get("preferred_label") or r.get("canonical_id")
                if canon and str(canon) != str(sp):
                    sp, src_sp = str(canon), src_sp or str(sp)
        rec = {
            "quantity": bq, "source_quantity": q,
            "value": v, "unit": cu, "source_unit": c.get("unit"),
            "unit_note": note,
            "value_kind": c.get("value_kind") or ("scalar" if v is not None else None),
            "of_reactant": _slot(sp, q, prec_keys, core_keys),
            "species": sp,
            "source_species_label": src_sp,
            "source": c.get("source"), "scope": c.get("scope"),
            "provenance_type": c.get("provenance_type"),
            "condition_class": condition_class(c.get("provenance_type")),
            "evidence": (c.get("evidence") or "")[:200],
            "context_status": "resolved",
        }
        if c.get("value_kind") == "range":
            rec.update(value=None, value_lower=_num(c.get("value_lower")),
                       value_upper=_num(c.get("value_upper")),
                       condition_class="interval_evidence")
        out.append(rec)
    return out


def _case_record(pid, case, n_measured_series):
    prec = [str(x) for x in case.get("precursors") or []]
    core = [str(x) for x in case.get("coreactants") or []]
    prec_c = sorted({CI.preferred_label(x) or x for x in prec})
    core_c = sorted({CI.preferred_label(x) or x for x in core})
    prec_keys = {CI.identity_key(x) for x in prec}
    core_keys = {CI.identity_key(x) for x in core}
    return {
        "_pid": pid, "paper_id": pid,
        "exp_id": "%s::%s" % (pid, case.get("case_id")),
        "case_id": case.get("case_id"),
        "record_nature": "experimental_case", "relevance": "experimental",
        "analysis_ready": n_measured_series > 0,
        "material": case.get("deposited_material"),
        "precursors": prec_c, "coreactants": core_c,
        "source_chemistry_labels": {"precursors": prec, "coreactants": core},
        "reactants": ([{"species": s, "role": "precursor"} for s in prec_c]
                      + [{"species": s, "role": "coreactant"} for s in core_c]),
        "process_type": case.get("process_type"),
        "geometry_class": case.get("geometry"),
        "geometry_source": case.get("geometry_source"),
        "controlled": _controlled(case, prec_keys, core_keys),
        "n_measured_series": n_measured_series,
        "provenance": {"doi": pid, "case_id": case.get("case_id"),
                       "figures": case.get("source_figures"),
                       "fingerprint": case.get("nominal_fingerprint")},
    }


_CASES = None


def case_records():
    """One evidence record per ExperimentalCase of every INCLUDED paper.

    This is M2's literature: chemistry-scoped condition retrieval and the
    imputation donor pool both read it. Reviews are never loaded -- membership
    comes from the manifest, not the filesystem."""
    global _CASES
    if _CASES is not None:
        return _CASES
    out = []
    for pid in P.corpus_papers():
        D = EI.load_paper(P.PAPERS, pid)
        measured_by_case = {}
        meas_case = {m.get("measurement_id"): (m.get("measures_case") or [])
                     for m in D["measurements"]}
        for rs in D["result_series"]:
            if rs.get("data_source") != "measured":
                continue
            for cid in meas_case.get(rs.get("produced_by")) or []:
                measured_by_case[cid] = measured_by_case.get(cid, 0) + 1
        for case in D["experimental_cases"]:
            out.append(_case_record(pid, case,
                                    measured_by_case.get(case.get("case_id"), 0)))
    _CASES = out
    return out


# ------------------------------------------------------------------ M3 candidates
#: thickness-family observables the conformality twin predicts
_THICKNESS_QUANTITIES = ("film_thickness", "normalized_thickness")
_X_TARGET = "x|group:spatial_position"


def _reach(series, axis):
    """{target_id: representation} the Workbench authorises for one axis."""
    return {r["target_id"]: r
            for r in series["%s_representations" % axis].values()
            if r.get("available") and r.get("values") and r.get("target_id")
            and r.get("overlay_authorized") is not False}


def profile_candidates():
    """(candidates, funnel, exclusions) for M3, from the Workbench authority.

    Funnel stages (each candidate advances or is excluded WITH its reason):

        semantic measured ResultSeries
        -> profile-compatible (reaches the spatial-coordinate target in canonical
           µm AND a thickness-family observable; >= 6 usable points)
        -> one representation per MeasurementAct (sibling re-renderings of one
           act are alternates, not extra evidence)
        -> resolved single-case linkage

    Model-domain eligibility (geometry/thermal) is NOT applied here -- the
    validation flow keeps it as its explicit commensurability gate so the funnel
    reports it separately."""
    wbm = json.loads(WB_MODEL.read_text())
    included = set(P.corpus_papers())
    cases_by_key = {r["exp_id"]: r for r in case_records()}
    funnel = {"semantic_result_series": 0, "measured_series": 0,
              "profile_compatible": 0, "one_per_measurement_act": 0,
              "resolved_single_case": 0}
    excl, cands, act_seen = [], [], {}
    for sid, s in sorted(wbm["series"].items()):
        if s.get("paper_id") not in included:
            continue                     # never a review, never outside the manifest
        funnel["semantic_result_series"] += 1
        if s.get("data_source") != "measured":
            excl.append({"series": sid, "stage": "measured_series",
                         "reason": "data_source=%r is not experimental evidence"
                                   % s.get("data_source")})
            continue
        funnel["measured_series"] += 1
        xr = _reach(s, "x").get(_X_TARGET)
        yr = next((r for t, r in _reach(s, "y").items()
                   if r.get("quantity_id") in _THICKNESS_QUANTITIES), None)
        pts = []
        if xr and yr:
            pts = [(x, y) for x, y in zip(xr["values"], yr["values"])
                   if x is not None and y is not None]
        if not xr or not yr or len(pts) < 6:
            why = ("x does not reach the spatial-coordinate target" if not xr else
                   "y reaches no thickness-family observable" if not yr else
                   "fewer than 6 usable points")
            excl.append({"series": sid, "stage": "profile_compatible", "reason": why})
            continue
        funnel["profile_compatible"] += 1
        act = s.get("act_id")
        if act in act_seen:
            excl.append({"series": sid, "stage": "one_per_measurement_act",
                         "reason": "sibling representation of MeasurementAct %s "
                                   "(already represented by %s)"
                                   % (act, act_seen[act])})
            continue
        act_seen[act] = sid
        funnel["one_per_measurement_act"] += 1
        # the workbench already paper-scopes its case ids
        key = s.get("single_case") or ((s.get("all_case_ids") or [None])[0]
                                       if s.get("n_cases") == 1 else None)
        crec = cases_by_key.get(key)
        if not crec:
            excl.append({"series": sid, "stage": "resolved_single_case",
                         "reason": ("series spans %d cases; no single Condition "
                                    "Case supplies its settings" % s.get("n_cases", 0))
                                   if s.get("n_cases", 0) != 1 else
                                   "linked case not found in the semantic layer"})
            continue
        funnel["resolved_single_case"] += 1
        rec = dict(crec)
        rec.update({
            "exp_id": sid, "record_nature": "measured_profile",
            "series_id": sid, "act_id": act,
            "curve_id": (s.get("native_points") or {}).get("curve_id"),
            "figure": s.get("figure"), "panel": s.get("panel"),
            "series_label": s.get("series_label"),
            "points": [[float(x), float(y)] for x, y in pts],
            "x_representation": {"target_id": xr["target_id"], "id": xr.get("id"),
                                 "unit": xr.get("unit"),
                                 "transform": (xr.get("transform") or {}).get("kind"),
                                 "rule_id": (xr.get("transform") or {}).get("rule_id")},
            "y_representation": {"target_id": yr["target_id"], "id": yr.get("id"),
                                 "unit": yr.get("unit"),
                                 "quantity": yr.get("quantity_id")},
            "measurand": {"quantity": yr.get("quantity_id"), "unit": yr.get("unit")},
            "coordinate": "spatial_coordinate", "coordinate_unit": xr.get("unit"),
            "granularity": "profile",
            "provenance": {"doi": s.get("paper_id"), "figure": s.get("figure"),
                           "panel": s.get("panel"), "series_label": s.get("series_label"),
                           "case_id": crec.get("case_id"), "series_id": sid,
                           "measurement_act": act,
                           "extractor": "production semantic corpus (workbench model)"},
        })
        cands.append(rec)
    return cands, funnel, excl


def corpus_meta():
    """What the reports cite: the manifest and the workbench build it read."""
    mf = json.loads(P.corpus_manifest_path().read_text())
    meta = (json.loads(WB_MODEL.read_text()).get("meta") or {}) if WB_MODEL.exists() else {}
    return {"manifest": str(P.corpus_manifest_path().relative_to(P.REPO)),
            "included_papers": len(mf["included"]),
            "excluded_reviews": [x["paper_id"] for x in mf["excluded"]],
            "workbench_head_sha": meta.get("head_sha"),
            "workbench_code_sha": (meta.get("generating_code_sha256") or "")[:12]}
