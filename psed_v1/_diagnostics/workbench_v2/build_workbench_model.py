#!/usr/bin/env python3
"""Build the scientific comparison workbench model from the frozen semantic layers.

Every scientific decision in the workbench is made here, in Python, against the frozen
runtime -- comparability verdicts, which representations a series can reach, and the
actual transformed coordinates for each of them. The page renders; it does not reason.
That split is deliberate: the previous workbench let the browser decide what was
comparable from labels, and separately let a Y control change an axis title while the
plotted values stayed raw.

The model is a graph, not a tree. A ResultSeries reaches its Condition Cases through its
producer and may reach several; a MeasurementAct may span several cases. Both directions
are carried, because flattening either one silently deletes science.

    python3 _diagnostics/workbench_v2/build_workbench_model.py
"""
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W))

from pipeline.query import entity_identity as EI                       # noqa: E402
from pipeline.query import result_comparability as RC                  # noqa: E402
from pipeline.canonical import units as U                              # noqa: E402

OUT = W / "_diagnostics" / "workbench_v2"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
FREEZE = {"entity_identity": "fadd925", "result_comparability": "849c377",
          "condition_comparability": "600320a", "ontology_readiness": "14bff7b"}

PROFILE_X = {"spatial_coordinate", "dimensionless_distance", "penetration_depth",
             "aspect_ratio"}
PROFILE_Y = {"film_thickness", "normalized_thickness", "growth_per_cycle",
             "surface_coverage", "step_coverage"}

COND_GROUPS = [
    ("Chemistry", ("precursor", "coreactant", "carrier_gas")),
    ("Process", ("deposition_temperature", "temperature", "working_pressure",
                 "base_pressure", "total_pressure", "partial_pressure",
                 "carrier_gas_partial_pressure", "cycle_number", "flow_rate")),
    ("Recipe", ("pulse_time", "purge_time", "exposure_time", "exposure",
                "precursor_pulse_time", "precursor_purge_time",
                "coreactant_pulse_time", "coreactant_purge_time")),
    ("Geometry", ("feature_height", "feature_width", "feature_length", "feature_depth",
                  "aspect_ratio", "pillar_layout", "deposited_layer_thickness",
                  "deposited_structure")),
]


def code_hash():
    h = hashlib.sha256()
    for p in (Path(__file__), W / "pipeline" / "query" / "entity_identity.py",
              W / "pipeline" / "query" / "result_comparability.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def canonical_curves(pid):
    p = PILOT / "papers" / pid / "resolved" / "canonical_curves.json"
    if not p.exists():
        return {}
    out = {}
    for c in json.loads(p.read_text()).get("curves") or []:
        cx = (c.get("canonical") or {}).get("x") or {}
        cy = (c.get("canonical") or {}).get("y") or {}
        sem, raw = c.get("semantics") or {}, c.get("raw") or {}
        xv, yv = cx.get("values") or [], cy.get("values") or []
        out[c["curve_id"]] = {
            "x_quantity": cx.get("quantity") or (sem.get("x") or {}).get("quantity"),
            "y_quantity": cy.get("quantity") or (sem.get("y") or {}).get("quantity"),
            "x_unit": cx.get("unit"), "y_unit": cy.get("unit"),
            "x_raw_unit": (raw.get("x") or {}).get("unit"),
            "y_raw_unit": (raw.get("y") or {}).get("unit"),
            "x_label": (raw.get("x") or {}).get("label"),
            "y_label": (raw.get("y") or {}).get("label"),
            "x_group": cx.get("comparison_group"), "y_group": cy.get("comparison_group"),
            "x_norm": cx.get("normalization_definition"),
            "y_norm": cy.get("normalization_definition"),
            "y_axis_kind": (sem.get("y") or {}).get("axis_kind"),
            # points are canonical VALUES paired with canonical UNITS. Pairing raw values
            # with a canonical unit silently rescales by whatever conversion the canonical
            # layer already applied -- 1000x for mm -> um, and entirely plausible-looking.
            "points": [[a, b] for a, b in zip(xv, yv) if a is not None and b is not None],
            "projections": c.get("projections") or {},
            "transformations": c.get("transformations") or [],
            "y_resolution": "FULLY_RESOLVED" if cy.get("quantity") else "PARTIALLY_RESOLVED",
        }
    return out


def target_id(axis, quantity, normalization, unit):
    """The scientific identity of a plotting target.

    Two series share a target only when they share this signature. The previous model
    keyed representations by a local name, and every series has one called "native", so
    a film thickness in nm and a refractive index intersected to a "common" native target
    and were drawn on one physical axis.
    """
    dim = None
    try:
        dim = U.dimension_name(unit) if unit else None
    except Exception:
        dim = None
    return "|".join([axis, str(quantity), str(normalization or ""), str(dim or ""),
                     str(unit or "")]), dim


def _sig(axis, rep):
    tid, dim = target_id(axis, rep.get("quantity"), rep.get("normalization"),
                         rep.get("unit"))
    rep["target_id"] = tid
    rep["quantity_id"] = rep.get("quantity")
    rep["normalization_id"] = rep.get("normalization")
    rep["dimension"] = dim
    rep["display_label"] = rep.get("label")
    rep["axis"] = axis
    return rep


def derived_representations(s, cur):
    """Every representation this series can reach, WITH the coordinates already computed.

    The page never transforms anything. If an option is offered, its numbers are already
    here; if the numbers cannot be produced, the option is not offered. That is what makes
    a Y control that does not move the curve structurally impossible.
    """
    pts = cur["points"]
    if not pts:
        return {}, {}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xr, yr = {}, {}

    xr["native"] = {"id": "native", "quantity": cur["x_quantity"], "unit": cur["x_unit"],
                    "label": "%s [%s]" % (cur["x_quantity"], cur["x_unit"]),
                    "values": xs, "transform": None, "available": True}
    for i, pj in enumerate((cur["projections"].get("x") or [])):
        vals = pj.get("values") or []
        if len(vals) != len(xs):
            continue
        xr["proj:%s" % pj.get("quantity")] = {
            "id": "proj:%s" % pj.get("quantity"), "quantity": pj.get("quantity"),
            "unit": pj.get("unit"),
            "label": "%s [%s]" % (pj.get("quantity"), pj.get("unit")),
            "values": vals, "available": True,
            "transform": {"kind": "CANONICAL_PROJECTION",
                          "from_normalization": pj.get("from_normalization"),
                          "provenance": "computed by the canonical layer and read back",
                          "parameters": _proj_params(cur, pj)}}

    ylab = "%s [%s]" % (cur["y_quantity"], cur["y_unit"])
    if cur["y_norm"]:
        ylab += ", %s" % cur["y_norm"]
    elif cur["y_quantity"] in RC._NORMALIZED_QUANTITIES:
        ylab += " (basis unresolved)"
    yr["native"] = {"id": "native", "quantity": cur["y_quantity"], "unit": cur["y_unit"],
                    "label": ylab, "values": ys, "transform": None, "available": True,
                    "normalization": cur["y_norm"]}
    # t/t_max is the one normalization whose denominator is derivable from the series
    # itself; t_entrance and t_planar need a reference this corpus does not carry, so
    # they are described as unavailable rather than quietly approximated by the maximum.
    if cur["y_quantity"] == "film_thickness":
        ctx = RC.resolve_context("t_max", series={"points": pts, "y_unit": cur["y_unit"],
                                                  "result_series_id": s["series_id"]})
        if ctx.get("found") and ctx.get("value"):
            ref = ctx["value"]
            yr["norm:t_over_t_max"] = {
                "id": "norm:t_over_t_max", "quantity": "normalized_thickness", "unit": "1",
                "label": "normalized_thickness [1], t_over_t_max",
                "values": [v / ref for v in ys], "available": True,
                "normalization": "t_over_t_max",
                "transform": {"kind": "reference_value_normalization",
                              "rule_id": "t_over_t_max",
                              "definition": RC.NORMALIZATIONS["t_over_t_max"].get(
                                  "semantic_label"),
                              "parameters": {"reference": ref, "unit": ctx.get("unit")},
                              "parameter_provenance": ctx}}
        for nid in ("t_over_t_entrance", "t_over_t_planar"):
            nd = RC.NORMALIZATIONS[nid]
            yr["norm:%s" % nid] = {
                "id": "norm:%s" % nid, "quantity": "normalized_thickness", "unit": "1",
                "label": nd.get("semantic_label"), "values": None, "available": False,
                "normalization": nid,
                "unavailable_reason":
                    "%s needs its own reference (%s, %s), which is not resolved for this "
                    "series" % (nid, nd.get("denominator"),
                                nd.get("semantic_label"))}
    return xr, yr


def _proj_params(cur, pj):
    for t in cur["transformations"]:
        if t.get("axis") == "x" and (t.get("context") or {}):
            return {k: {"value": v.get("value"), "unit": v.get("unit"),
                        "evidence": v.get("evidence"), "status": v.get("status")}
                    for k, v in t["context"].items()}
    return {}


def build():
    papers = json.loads((PILOT / "pilot_papers.json").read_text())["papers"]
    cases, acts, series, samples, runs, measurements = {}, {}, {}, {}, {}, {}
    excluded = []

    for pid in papers:
        D = EI.load_paper(PILOT, pid)
        cur = canonical_curves(pid)
        smap = {s["sample_id"]: s for s in D["samples"] if s.get("sample_id")}
        pcases = EI.producer_case_index(D["measurements"], D["simulation_runs"])
        agroups, act_of = EI.measurement_acts(D["measurements"])
        K = lambda i: "%s::%s" % (pid, i)

        for c in D["experimental_cases"]:
            real = EI.realizations(c, smap, None)
            cases[K(c["case_id"])] = {
                "id": K(c["case_id"]), "case_id": c["case_id"], "paper_id": pid,
                "entity": "CONDITION_CASE",
                "material": c.get("deposited_material"), "geometry": c.get("geometry"),
                "fingerprint": c.get("nominal_fingerprint"),
                "conditions": [{"quantity": x.get("quantity"), "value": x.get("value"),
                                "unit": x.get("unit"), "species": x.get("species"),
                                "scope": EI.CASE_CONTEXT,
                                "provenance_type": x.get("provenance_type")}
                               for x in (c.get("case_defining_conditions") or [])],
                "chemistry": _chem(c),
                "realization": {
                    "source_sample_records": real["n_samples_resolved"],
                    "physical_specimen_identity": "unresolved",
                    "samples": [{"sample_id": x["sample_id"],
                                 "source_sample_code": x["source_sample_code"],
                                 "physical_specimen": None,
                                 "deposition_run": x["produced_by_run"],
                                 "run_status": x["run_status"]}
                                for x in real["samples"]],
                    "runs_observed": [dict(r) for r in EI.case_run_links(c, smap)],
                    "run_link_semantics": EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS},
                "act_ids": [], "series_ids": []}
        for sid, s in smap.items():
            samples[K(sid)] = {"id": K(sid), "sample_id": sid, "paper_id": pid,
                               "source_sample_code": s.get("source_sample_code"),
                               "physical_specimen": None,
                               "physical_identity_status": EI.SPECIMEN_UNRESOLVED,
                               "deposition_run": s.get("produced_by_run")}
        for r in D["deposition_runs"]:
            rid, members = EI.run_members(r, list(smap.values()))
            if rid:
                runs[K(rid)] = {"id": K(rid), "run_id": rid, "paper_id": pid,
                                "sample_members": members, "scope": "SAMPLE_SCOPED"}
        for m in D["measurements"]:
            measurements[K(m["measurement_id"])] = {
                "id": K(m["measurement_id"]), "measurement_id": m["measurement_id"],
                "paper_id": pid, "act_id": K(act_of.get(m["measurement_id"], "")),
                "technique": _tech(m.get("technique") or m.get("classification")),
                "measurand": m.get("measured_quantity"),
                "settings": [{"quantity": x.get("quantity"), "value": x.get("value"),
                              "unit": x.get("unit")}
                             for x in (m.get("measurement_settings") or [])][:10],
                "performed_on": m.get("performed_on")}
        mby = {m["measurement_id"]: m for m in D["measurements"]}
        for aid, members in agroups.items():
            cs = sorted({c for m in members for c in pcases.get(m, ())})
            first = mby.get(members[0], {})
            acts[K(aid)] = {
                "id": K(aid), "act_id": aid, "paper_id": pid, "entity": "MEASUREMENT_ACT",
                "kind": "MEASUREMENT",
                "technique": _tech(first.get("technique") or first.get("classification")),
                "measurand": first.get("measured_quantity"),
                "member_measurement_ids": members, "n_members": len(members),
                "case_ids": [K(c) for c in cs], "n_cases": len(cs),
                "sample_ids": sorted({K(mby[m]["performed_on"]) for m in members
                                      if mby.get(m, {}).get("performed_on")}),
                "grouping_evidence": EI.act_evidence(D["measurements"], members),
                "series_ids": []}
            for c in cs:
                if K(c) in cases:
                    cases[K(c)]["act_ids"].append(K(aid))
        for s in D["simulation_runs"]:
            sid = s.get("simulation_run_id") or s.get("id")
            if not sid:
                continue
            cs = sorted(set(s.get("realises_case_ids") or []))
            acts[K(sid)] = {
                "id": K(sid), "act_id": sid, "paper_id": pid, "entity": "MEASUREMENT_ACT",
                "kind": "SIMULATION_RUN",
                "technique": s.get("model_family") or s.get("model") or "simulation",
                "measurand": None, "member_measurement_ids": [], "n_members": 0,
                "case_ids": [K(c) for c in cs], "n_cases": len(cs), "sample_ids": [],
                "grouping_evidence": ["simulation run; not a physical observing act"],
                "series_ids": []}
            for c in cs:
                if K(c) in cases:
                    cases[K(c)]["act_ids"].append(K(sid))

        for r in D["result_series"]:
            rid, prod = r["result_series_id"], r.get("produced_by")
            cu = cur.get(r.get("curve_id")) or {}
            # A series whose measurand does not resolve to an ontology quantity is still a
            # real scientific result: it is visible, keeps its full case membership, and is
            # simply not comparable. Dropping it would delete case links and quietly shrink
            # the denominator.
            if not cu:
                excluded.append({"series_id": rid, "paper_id": pid,
                                 "reason": "NO_CANONICAL_CURVE_RECORD"})
                continue
            unresolved_y = not cu.get("y_quantity")
            cs = [K(c) for c in EI.cases_for_result_series(r, pcases)]
            one, status = EI.single_case_for_series(r, pcases)
            src = r.get("source") or {}
            rec = {
                "id": K(rid), "series_id": rid, "paper_id": pid,
                "entity": "RESULT_SERIES",
                "act_id": K(act_of[prod]) if prod in act_of else K(prod),
                "producer_id": K(prod) if prod else None,
                "data_source": r.get("data_source"),
                "figure": src.get("figure"), "panel": src.get("panel"),
                "series_label": src.get("series"),
                "n_points": r.get("n_points"),
                # named all_case_ids because there is no other kind: a sweep belongs to
                # every case it traverses and none of them is primary
                "all_case_ids": cs, "n_cases": len(cs),
                "single_case": K(one) if one else None,
                "case_cardinality_status": status,
                "is_profile": (not unresolved_y and cu["x_quantity"] in PROFILE_X
                               and cu["y_quantity"] in PROFILE_Y),
                "x": {k: cu[k] for k in ("x_quantity", "x_unit", "x_raw_unit", "x_label",
                                         "x_group", "x_norm")},
                "y": {k: cu[k] for k in ("y_quantity", "y_unit", "y_raw_unit", "y_label",
                                         "y_group", "y_norm", "y_axis_kind")},
                "y_resolution": ("UNRESOLVED" if unresolved_y else cu["y_resolution"]),
                "measurand_status": ("UNRESOLVED_MEASURAND" if unresolved_y
                                     else "RESOLVED"),
                "normalization_basis": (cu["y_norm"] or
                                        ("unresolved"
                                         if cu["y_quantity"] in RC._NORMALIZED_QUANTITIES
                                         else None)),
            }
            xr, yr = derived_representations(rec, cu)
            rec["x_representations"] = {k: _sig("x", v) for k, v in xr.items()}
            rec["y_representations"] = {k: _sig("y", v) for k, v in yr.items()}
            series[K(rid)] = rec
            if rec["act_id"] in acts:
                acts[rec["act_id"]]["series_ids"].append(K(rid))
            for c in cs:
                if c in cases:
                    cases[c]["series_ids"].append(K(rid))
    return cases, acts, series, samples, runs, measurements, excluded


def _chem(c):
    out = {}
    for x in (c.get("case_defining_conditions") or []):
        if x.get("quantity") in ("precursor", "coreactant"):
            out.setdefault(x["quantity"], set()).add(str(x.get("value")))
    return {k: sorted(v) for k, v in out.items()}


def _tech(v):
    if isinstance(v, (list, tuple, set)):
        v = ", ".join(sorted(str(x) for x in v if x)) or None
    return str(v) if v not in (None, "") else None


def comparability(series):
    """Frozen-runtime pair verdicts. The browser reads these; it never derives them."""
    # a profile without materialised native coordinates cannot be compared as a profile
    prof = [s for s in series.values()
            if s["is_profile"] and s["n_points"]
            and "native" in s["x_representations"] and "native" in s["y_representations"]]
    rt = {s["id"]: {"paper_id": s["paper_id"], "result_series_id": s["id"],
                    "data_source": s["data_source"],
                    "x_quantity": s["x"]["x_quantity"], "x_unit": s["x"]["x_unit"],
                    "x_label": s["x"]["x_label"], "x_normalization": s["x"]["x_norm"],
                    "x_comparison_group": s["x"]["x_group"],
                    "y_quantity": s["y"]["y_quantity"], "y_unit": s["y"]["y_unit"],
                    "y_label": s["y"]["y_label"], "y_normalization": s["y"]["y_norm"],
                    "y_comparison_group": s["y"]["y_group"],
                    "points": [list(t) for t in
                               zip(s["x_representations"]["native"]["values"],
                                   s["y_representations"]["native"]["values"])],
                    "projections": {}, "transformations": []} for s in prof}
    pairs, counts = {}, Counter()
    ids = sorted(rt)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = rt[a], rt[b]
            if ra["y_comparison_group"] != rb["y_comparison_group"] and not \
                    RC.transform_for(ra["y_quantity"], rb["y_quantity"])[0]:
                continue
            d = RC.compare_result_series(ra, rb)
            ds = RC.compare_result_series(ra, rb, allow_shape_only=True)
            counts[d["profile_status"]] += 1
            st = d["profile_status"]
            pairs["%s|%s" % (a, b)] = {
                "status": st,
                "shape_only_status": ds["profile_status"],
                # what the frozen verdict permits on a shared PHYSICAL axis. ambiguous,
                # missing_context and not-comparable never overlay by default; shape-only
                # is a separate, explicitly requested mode.
                "physical_overlay_allowed": st in ("DIRECT_PROFILE",
                                                   "TRANSFORMABLE_PROFILE"),
                "shape_only_eligible": ds["profile_status"] == "SHAPE_ONLY_PROFILE",
                "cross_paper": d["cross_paper"],
                "x_status": d["x"]["status"], "x_reason": d["x"]["reason"],
                "y_status": d["y"]["status"], "y_reason": d["y"]["reason"],
                "missing": sorted(set(d["x"]["missing_context"] + d["y"]["missing_context"])),
            }
    return pairs, counts


#: Facet declarations. `scope` is the whole contract: a Condition Case-scoped facet must
#: be satisfied together with every other case-scoped constraint on ONE case, while
#: MeasurementAct- and ResultSeries-scoped facets are properties of the result itself.
#: Adding a facet is a change here, not a change to the filtering algorithm.
FACET_DEFS = [
    {"id": "material", "label": "Deposited material", "scope": "Condition Case"},
    {"id": "precursor", "label": "Precursor", "scope": "Condition Case"},
    {"id": "coreactant", "label": "Co-reactant", "scope": "Condition Case"},
    {"id": "geometry", "label": "Geometry", "scope": "Condition Case"},
    {"id": "paper", "label": "Paper", "scope": "Condition Case"},
    {"id": "technique", "label": "Measurement technique", "scope": "MeasurementAct"},
    {"id": "quantity", "label": "Result quantity", "scope": "ResultSeries"},
    {"id": "coordinate", "label": "Result coordinate", "scope": "ResultSeries"},
    {"id": "normalization", "label": "Normalization basis", "scope": "ResultSeries"},
    {"id": "data_source", "label": "Result type", "scope": "ResultSeries"},
]
CASE_SCOPE = "Condition Case"


def case_scoped_facet_ids():
    return [f["id"] for f in FACET_DEFS if f["scope"] == CASE_SCOPE]


def facets(cases, acts, series):
    """Facet option -> the entity ids it is compatible with, precomputed."""
    idx = defaultdict(lambda: defaultdict(lambda: {"cases": set(), "series": set()}))

    def add(f, v, cid, sid):
        if v in (None, ""):
            return
        e = idx[f][str(v)]
        if cid:
            e["cases"].add(cid)
        if sid:
            e["series"].add(sid)

    for s in series.values():
        for cid in (s["all_case_ids"] or [None]):
            add("quantity", s["y"]["y_quantity"], cid, s["id"])
            add("coordinate", s["x"]["x_quantity"], cid, s["id"])
            add("data_source", s["data_source"], cid, s["id"])
            add("normalization", s["normalization_basis"], cid, s["id"])
            a = acts.get(s["act_id"])
            if a:
                add("technique", a["technique"], cid, s["id"])
            c = cases.get(cid) if cid else None
            if c:
                add("material", c["material"], cid, s["id"])
                add("geometry", c["geometry"], cid, s["id"])
                add("paper", c["paper_id"], cid, s["id"])
                for p in c["chemistry"].get("precursor", []):
                    add("precursor", p, cid, s["id"])
                for p in c["chemistry"].get("coreactant", []):
                    add("coreactant", p, cid, s["id"])
    return {f: {v: {"cases": sorted(e["cases"]), "series": sorted(e["series"])}
                for v, e in vals.items()} for f, vals in idx.items()}


_NUMRE = __import__("re").compile(r"^\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*$")


def _num(v):
    """A numeric condition value, or None. Ranges must compare physics, not text."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and _NUMRE.match(v):
        return float(v)
    return None


def condition_field_id(quantity, species):
    """The identity of a numeric condition. A TMA pulse and an H2O pulse are two
    quantities, not one quantity written twice, and the frozen condition layer already
    says so -- this only has to avoid throwing the qualifier away again."""
    return "%s@%s" % (quantity, species) if species else str(quantity)


def numeric_conditions(cases):
    """Canonical numeric condition values, so a range filter compares physics not text.

    Each entry carries its quantity and species as fields. Downstream code must read
    those, never re-derive them by splitting the key: `key.split("@")[0]` is how a TMA
    pulse time and an H2O pulse time became one ambiguous facet.
    """
    out = {}
    for cid, c in cases.items():
        vals = {}
        for x in c["conditions"]:
            n = _num(x.get("value"))
            if n is None:
                continue
            sp = x.get("species")
            norm = None
            try:
                if x.get("unit"):
                    fu = U.parse(x["unit"])
                    norm = float(n) * fu.factor + fu.offset
            except Exception:
                norm = None
            vals.setdefault(condition_field_id(x["quantity"], sp), []).append(
                {"raw": n, "unit": x.get("unit"), "canonical": norm,
                 "quantity": x["quantity"], "species": sp})
        out[cid] = vals
    return out


#: A numeric field is offered as a range filter once this many Condition Cases carry it.
#: Every qualified sibling of an offered quantity is then offered too -- showing an H2O
#: pulse time without its TMA counterpart is its own kind of misleading.
_RANGE_MIN_CASES = 10


def _label(quantity, species):
    """'pulse_time', 'TMA' -> 'TMA pulse time'. The species leads because that is what
    distinguishes it from its siblings."""
    words = str(quantity).replace("_", " ")
    if species:
        return "%s %s" % (species, words)
    return words[:1].upper() + words[1:]


def range_fields(numeric):
    """Numeric quantities offered as range filters, in the unit the filter runs in.

    Two separate lies were possible here. The range box used to advertise the unit the
    paper wrote (°C) while comparing canonical magnitudes (K). And the field identity was
    the quantity alone, so one "Pulse time" box silently addressed whichever of
    pulse_time@TMA / pulse_time@H2O the browser happened to find first. A field is now
    the exact condition key, and it carries its species so no consumer has to parse it
    back out of a string.
    """
    cov, units, canon, meta = Counter(), defaultdict(set), Counter(), {}
    for fields in numeric.values():
        for fid, entries in fields.items():
            cov[fid] += 1
            for e in entries:
                meta.setdefault(fid, (e.get("quantity"), e.get("species")))
                if e.get("unit"):
                    units[fid].add(e["unit"])
                if e.get("canonical") is not None:
                    canon[fid] += 1

    # a quantity is in scope on coverage; its qualified siblings come with it
    quantities = {meta[f][0] for f in cov if cov[f] >= _RANGE_MIN_CASES and f in meta}
    scope = [f for f in cov if f in meta and (cov[f] >= _RANGE_MIN_CASES
                                              or meta[f][0] in quantities)]

    out, dropped = [], []
    for fid in sorted(scope, key=lambda f: (-cov[f], f)):
        quantity, species = meta[fid]
        bases = set()
        for u in units[fid]:
            try:
                bases.add(U.base_symbol(u))
            except Exception:
                bases.add(None)
        if len(bases) != 1 or None in bases or not canon[fid]:
            dropped.append({"field_id": fid, "reason": "no single canonical dimension"})
            continue
        out.append({"id": fid, "field_id": fid, "quantity_id": quantity,
                    "species_or_role": species,
                    "label": _label(quantity, species),
                    "display_label": _label(quantity, species),
                    "canonical_unit": bases.pop(), "cases_covered": cov[fid],
                    "raw_units": sorted(units[fid]),
                    "comparison_basis": "canonical magnitude"})

    # an unqualified field sitting beside qualified siblings is not "all of them"
    by_quantity = defaultdict(list)
    for f in out:
        by_quantity[f["quantity_id"]].append(f)
    for q, fs in by_quantity.items():
        if len(fs) > 1:
            for f in fs:
                f["has_qualified_siblings"] = True
                if not f["species_or_role"]:
                    f["display_label"] += " (species unattributed)"
        else:
            fs[0]["has_qualified_siblings"] = False
    if dropped:
        print("range fields not offered: %s" % dropped)
    return out


def presentation(cases, acts, series):
    """Where each ResultSeries belongs in the results UI, decided once, in Python.

    A single-case series belongs inside its case. A multi-case series belongs to the
    sweep section and to NO case: it traverses several nominal condition cases and none
    of them is primary. The previous page picked the lowest case id as a "home", which
    invented a scientific primacy the data does not carry.

    Each case also gets its producers partitioned by entity kind, because a SimulationRun
    under a heading that says "measurement acts" is a false claim about how the numbers
    were obtained.
    """
    for cid, c in cases.items():
        c["case_local_series_ids"] = []
        c["traversed_by_series_ids"] = []
        c["measurement_act_ids"] = []
        c["simulation_run_ids"] = []
    sweeps, nocase = [], []
    for sid, s in series.items():
        cs = s["all_case_ids"]
        if len(cs) == 1:
            s["placement"] = "CASE_LOCAL"
            s["placement_case_id"] = cs[0]
            cases[cs[0]]["case_local_series_ids"].append(sid)
        elif cs:
            # no placement_case_id: there is no case this series belongs to more than
            # the others, and offering one field for it would invite exactly that claim
            s["placement"] = "MULTI_CASE_SWEEP"
            s["placement_case_id"] = None
            sweeps.append(sid)
            for x in cs:
                cases[x]["traversed_by_series_ids"].append(sid)
        else:
            # a series whose producer carries no case link is not a sweep; it is a result
            # whose process context was never extracted, which is a different statement
            s["placement"] = "NO_CASE"
            s["placement_case_id"] = None
            nocase.append(sid)
    for cid, c in cases.items():
        seen = []
        for sid in c["case_local_series_ids"]:
            aid = series[sid]["act_id"]
            if aid in seen:
                continue
            seen.append(aid)
            a = acts.get(aid)
            key = ("simulation_run_ids" if a and a["kind"] == "SIMULATION_RUN"
                   else "measurement_act_ids")
            c[key].append(aid)
        for k in ("case_local_series_ids", "traversed_by_series_ids",
                  "measurement_act_ids", "simulation_run_ids"):
            c[k] = sorted(c[k])
    return sorted(sweeps), sorted(nocase)


def main():
    cases, acts, series, samples, runs, measurements, excluded = build()
    pairs, counts = comparability(series)
    sweeps, nocase = presentation(cases, acts, series)
    nums = numeric_conditions(cases)
    model = {
        "meta": {"freeze": FREEZE, "generating_code_sha256": code_hash(),
                 "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                            cwd=str(W), capture_output=True,
                                            text=True).stdout.strip(),
                 "semantic_model": "entity-identity frozen at %s" % FREEZE["entity_identity"],
                 "comparison_model": "Result/Profile Comparability frozen at %s"
                                     % FREEZE["result_comparability"],
                 "physical_specimen_completeness": "partial: no traceable specimen "
                                                   "identifier is present in this corpus"},
        "cases": cases, "acts": acts, "series": series, "samples": samples,
        "runs": runs, "measurements": measurements,
        "pairs": pairs, "facets": facets(cases, acts, series),
        "facet_defs": FACET_DEFS,
        "numeric_conditions": nums,
        "range_fields": range_fields(nums),
        "sweep_series_ids": sweeps,
        "no_case_series_ids": nocase,
        "excluded_series": excluded,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "workbench_model.json").write_text(
        json.dumps(model, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    val = validate(model, counts)
    (OUT / "workbench_validation.json").write_text(
        json.dumps(val, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    render(model, val)
    for k, v in val["counts"].items():
        print("%-34s %s" % (k, v))
    print("pair statuses %s" % dict(counts))
    print("invariants ok: %s" % val["invariants_ok"])
    print("wrote %s" % (OUT / "psed_scientific_comparison_workbench.html").relative_to(W))
    return 0 if val["invariants_ok"] else 1


def validate(m, counts):
    cases, acts, series = m["cases"], m["acts"], m["series"]
    numeric = m["numeric_conditions"]
    meas = m["measurements"]
    multi_case = [s for s in series.values() if s["n_cases"] > 1]
    multi_act = [a for a in acts.values() if a["n_members"] > 1]
    c = {
        "condition_cases": len(cases),
        "measurement_records": len(meas),
        "measurement_acts": len([a for a in acts.values() if a["kind"] == "MEASUREMENT"]),
        "simulation_runs": len([a for a in acts.values() if a["kind"] == "SIMULATION_RUN"]),
        "result_series_persisted": len(series) + len(m["excluded_series"]),
        "result_series_searchable": len(series),
        "result_series_excluded": len(m["excluded_series"]),
        "multi_case_result_series": len(multi_case),
        "max_cases_per_result_series": max([s["n_cases"] for s in series.values()] or [0]),
        "multi_member_measurement_acts": len(multi_act),
        "max_members_per_act": max([a["n_members"] for a in acts.values()] or [0]),
        "source_sample_records": len(m["samples"]),
        "physical_specimens_resolved": 0,
        "known_runs": len(m["runs"]),
        "profile_series": len([s for s in series.values() if s["is_profile"]]),
        "indexed_pairs": len(m["pairs"]),
    }
    inv = {
        "condition_cases_182": c["condition_cases"] == 182,
        "measurement_records_213": c["measurement_records"] == 213,
        "measurement_acts_201": c["measurement_acts"] == 201,
        "multi_member_acts_6": c["multi_member_measurement_acts"] == 6,
        "result_series_231": c["result_series_persisted"] == 231,
        "all_231_searchable": c["result_series_searchable"] == 231,
        "multi_case_series_22": c["multi_case_result_series"] == 22,
        "max_cases_10": c["max_cases_per_result_series"] == 10,
        "no_first_case_collapse": all(
            s["single_case"] is None or s["n_cases"] == 1 for s in series.values()),
        "every_series_reaches_its_act": all(s["act_id"] in acts for s in series.values()),
        "every_act_case_resolves": all(x in cases for a in acts.values()
                                       for x in a["case_ids"]),
        "every_series_case_resolves": all(x in cases for s in series.values()
                                          for x in s["all_case_ids"]),
        "derived_values_present": all(
            r.get("values") is not None
            for s in series.values() for r in s["y_representations"].values()
            if r.get("available")),
        "every_offered_rep_has_values": all(
            (not r.get("available")) or (r.get("values") and
             len(r["values"]) == len(s["x_representations"]["native"]["values"]))
            for s in series.values() if "native" in s["x_representations"]
            for r in list(s["x_representations"].values())
                   + list(s["y_representations"].values())),
    }
    # ---- semantic overlay metrics, computed by replaying the page's own decisions ----
    # Each of these was a literal 0 in the previous build, which measures nothing. They
    # are now derived by mirroring the UI rule in Python and checking the invariant it is
    # supposed to guarantee, exhaustively, over the whole corpus.
    sig = defaultdict(set)
    for s2 in series.values():
        for ax in ("x_representations", "y_representations"):
            for r in s2[ax].values():
                if r.get("available"):
                    sig[r["target_id"]].add(s2["id"])
    native_y = defaultdict(set)
    for s2 in series.values():
        r = s2["y_representations"].get("native")
        if r:
            native_y[r["target_id"]].add(s2["id"])
    c["distinct_y_native_targets"] = len(native_y)
    c["distinct_semantic_targets"] = len(sig)

    pairs = m["pairs"]

    def pair_of(a, b):
        return pairs.get("%s|%s" % (a, b)) or pairs.get("%s|%s" % (b, a))

    def overlay_allowed(group):
        """The page's gate: every pair in the selection must be authorised."""
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                p = pair_of(group[i], group[j])
                if not p or not p.get("physical_overlay_allowed"):
                    return False
        return True

    def reps_by_target(sid, axis):
        return {r["target_id"]: r
                for r in series[sid][axis + "_representations"].values()
                if r.get("available") and r.get("values")}

    def offered_targets(group, axis):
        """Exactly what commonTargets() offers for this selection."""
        if not overlay_allowed(group):
            return set()
        common = None
        for sid in group:
            t = set(reps_by_target(sid, axis))
            common = t if common is None else (common & t)
        return common or set()

    def semantics_agree(group, axis, tid):
        """Every participant must mean the same thing by this target, not merely
        possess a key that spells it the same way."""
        seen = set()
        for sid in group:
            r = reps_by_target(sid, axis).get(tid)
            if r is None:
                return False
            seen.add((r.get("quantity_id"), r.get("normalization_id"),
                      r.get("dimension"), r.get("unit"), r.get("axis")))
        return len(seen) == 1

    OVERLAY_OK = ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")
    sids = sorted(series)
    false_common = incompat = 0
    key_based_false_common = 0        # what the pre-repair rule would have produced
    pairs_offered_overlay = 0
    for i in range(len(sids)):
        for j in range(i + 1, len(sids)):
            g = [sids[i], sids[j]]
            offers = {ax: offered_targets(g, ax) for ax in ("x", "y")}
            n_off = len(offers["x"]) + len(offers["y"])
            if n_off:
                pairs_offered_overlay += 1
                p = pair_of(*g)
                if not p or p["status"] not in OVERLAY_OK:
                    incompat += 1
                for ax in ("x", "y"):
                    for tid in offers[ax]:
                        if not semantics_agree(g, ax, tid):
                            false_common += 1
            # counterfactual: intersecting representation KEYS, as the page used to
            for ax in ("x", "y"):
                ka = {k for k, r in series[g[0]][ax + "_representations"].items()
                      if r.get("available") and r.get("values")}
                kb = {k for k, r in series[g[1]][ax + "_representations"].items()
                      if r.get("available") and r.get("values")}
                for k in (ka & kb):
                    ta = series[g[0]][ax + "_representations"][k]["target_id"]
                    tb = series[g[1]][ax + "_representations"][k]["target_id"]
                    p = pair_of(*g)
                    if ta != tb or not p or not p.get("physical_overlay_allowed"):
                        key_based_false_common += 1
    c["false_common_native_targets"] = false_common
    c["key_based_false_common_targets"] = key_based_false_common
    c["incompatible_plotted_pair_violations"] = incompat
    c["pairs_offered_a_physical_overlay"] = pairs_offered_overlay

    # 3+ series: exhaustive over every trio the model could put on one target, not a
    # single hand-picked example
    trio_violations = trios = 0
    for ax in ("x", "y"):
        per_target = defaultdict(list)
        for sid in sids:
            for tid in reps_by_target(sid, ax):
                per_target[tid].append(sid)
        for tid, members in per_target.items():
            members = sorted(members)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    for k in range(j + 1, len(members)):
                        g = [members[i], members[j], members[k]]
                        if tid not in offered_targets(g, ax):
                            continue
                        trios += 1
                        p_ok = all(
                            (pair_of(g[a], g[b]) or {}).get("status") in OVERLAY_OK
                            for a in range(3) for b in range(a + 1, 3))
                        if not semantics_agree(g, ax, tid) or not p_ok:
                            trio_violations += 1
    c["multi_series_target_sets_checked"] = trios
    c["multi_series_target_violations"] = trio_violations

    # ---- result presentation: one entry per series, no invented primary case ---------
    entries = Counter()
    for cid, cc in cases.items():
        for sid in cc["case_local_series_ids"]:
            entries[sid] += 1
    for sid in m["sweep_series_ids"] + m["no_case_series_ids"]:
        entries[sid] += 1
    c["primary_result_entries"] = sum(entries.values())
    c["multi_case_result_series"] = len(multi_case)
    c["multi_case_primary_entries"] = len(
        [s2 for s2 in multi_case if entries[s2["id"]] == 1])
    c["duplicate_primary_entries"] = len([x for x, n in entries.items() if n > 1])
    c["result_series_without_primary_entry"] = len(
        [x for x in series if entries[x] == 0])
    c["multi_case_series_with_primary_case"] = len(
        [s2 for s2 in multi_case if s2.get("placement_case_id") is not None])
    c["case_local_series"] = sum(len(cc["case_local_series_ids"])
                                 for cc in cases.values())
    c["sweep_series"] = len(m["sweep_series_ids"])
    c["no_case_series"] = len(m["no_case_series_ids"])

    # ---- numeric facet identity ------------------------------------------------------
    nfields = ncanon = nmissing = 0
    for vals in numeric.values():
        for k, arr in vals.items():
            nfields += len(arr)
            ncanon += len([x for x in arr if x.get("canonical") is not None])
            nmissing += len([x for x in arr if x.get("canonical") is None])
    c["numeric_fields_indexed"] = nfields
    c["numeric_with_canonical"] = ncanon
    c["numeric_without_canonical"] = nmissing

    rfields = m["range_fields"]
    c["numeric_range_fields"] = len(rfields)
    c["qualified_numeric_range_fields"] = len(
        [f for f in rfields if f.get("species_or_role")])
    # a field loses its qualifier if its id does not encode the species its own entries
    # carry -- i.e. if something stripped it on the way through
    losing = 0
    for f in rfields:
        want = condition_field_id(f["quantity_id"], f.get("species_or_role"))
        if f["field_id"] != want:
            losing += 1
            continue
        for fields in numeric.values():
            for e in fields.get(f["field_id"], []):
                if (e.get("species") or None) != (f.get("species_or_role") or None):
                    losing += 1
                    break
    c["qualified_range_fields_losing_qualifier"] = losing

    per_base = defaultdict(set)
    multi_species_cases = 0
    for cid, fields in numeric.items():
        by_q = defaultdict(set)
        for fid, entries_ in fields.items():
            for e in entries_:
                by_q[e.get("quantity")].add(e.get("species"))
                per_base[e.get("quantity")].add(e.get("species"))
        if any(len(v) > 1 for v in by_q.values()):
            multi_species_cases += 1
    c["cases_with_multiple_species_for_same_base_quantity"] = multi_species_cases
    c["base_quantities_with_several_species"] = len(
        [q for q, sp in per_base.items() if len(sp) > 1])

    # exact addressing: a field must inspect exactly the key it names, and a lookup that
    # could reach more than one key is ambiguous. The counterfactual shows the teeth.
    ambiguous = prefix_ambiguous = 0
    for f in rfields:
        fid = f["field_id"]
        for cid, fields in numeric.items():
            if len([k for k in fields if k == fid]) > 1:
                ambiguous += 1
            hits = [k for k in fields if k == fid or k.startswith(fid + "@")]
            if len(hits) > 1:
                prefix_ambiguous += 1
    c["ambiguous_first_match_range_lookups"] = ambiguous
    c["prefix_match_ambiguous_lookups_avoided"] = prefix_ambiguous

    # ---- case-scoped filter conjunction ---------------------------------------------
    # Exhaustive over an explicitly defined universe: every ResultSeries linked to more
    # than one Condition Case, every ordered pair of its cases (A, B), every case-scoped
    # facet option that A satisfies and B does not, paired with every numeric field where
    # B carries a canonical value that A does not reach. Under such a filter NO single
    # linked case satisfies both constraints, so admitting the series is a false positive.
    # The universe size is reported alongside the count: a zero over an empty universe is
    # not evidence, and this corpus must be allowed to say so.
    fidx = m["facets"]
    case_facets = case_scoped_facet_ids()

    def case_has(cid, fid, v):
        e = fidx.get(fid, {}).get(v)
        return bool(e and cid in e["cases"])

    def canon_values(cid, field):
        return [e["canonical"] for e in numeric.get(cid, {}).get(field, [])
                if e.get("canonical") is not None]

    fields = sorted({f for fs in numeric.values() for f in fs})
    universe = old_admits = new_admits = 0
    for s2 in series.values():
        cs = s2["all_case_ids"]
        if len(cs) < 2:
            continue
        for a in cs:
            for b in cs:
                if a == b:
                    continue
                for fid in case_facets:
                    for v in fidx.get(fid, {}):
                        if not case_has(a, fid, v) or case_has(b, fid, v):
                            continue
                        for field in fields:
                            vb = canon_values(b, field)
                            if not vb:
                                continue
                            lo = max(vb)
                            # the band admits b and must not admit a
                            if any(x >= lo for x in canon_values(a, field)):
                                continue
                            # ... nor any other linked case that also carries the option
                            if any(case_has(c, fid, v)
                                   and any(x >= lo for x in canon_values(c, field))
                                   for c in cs):
                                continue
                            universe += 1
                            # the pre-repair rule: facet checked against the SERIES, band
                            # against ANY case -- two different cases could answer
                            series_level = any(case_has(c, fid, v) for c in cs) and any(
                                any(x >= lo for x in canon_values(c, field)) for c in cs)
                            if series_level:
                                old_admits += 1
                            # the repaired rule: one case must satisfy both
                            if any(case_has(c, fid, v)
                                   and any(x >= lo for x in canon_values(c, field))
                                   for c in cs):
                                new_admits += 1
    c["cross_case_constraint_universe"] = universe
    c["cross_case_constraint_false_positive_violations"] = new_admits
    c["cross_case_false_positives_under_series_level_rule"] = old_admits
    # why the universe is the size it is: a sweep whose cases all share their categorical
    # values cannot express a cross-case contradiction at all
    hetero = 0
    for s2 in series.values():
        cs = s2["all_case_ids"]
        if len(cs) < 2:
            continue
        for fid in case_facets:
            vals = {frozenset(v for v in fidx.get(fid, {}) if case_has(cid, fid, v))
                    for cid in cs}
            if len(vals) > 1:
                hetero += 1
                break
    c["multi_case_series_with_varying_case_facets"] = hetero

    c["physical_specimens_resolved"] = len(
        {x["physical_specimen"] for x in m["samples"].values()
         if x.get("physical_specimen")})
    c["producers_total"] = c["measurement_acts"] + c["simulation_runs"]
    c["cases_with_both_producer_kinds"] = len(
        [cc for cc in cases.values()
         if cc["measurement_act_ids"] and cc["simulation_run_ids"]])
    c["per_case_producer_partition_total"] = sum(
        len(cc["measurement_act_ids"]) + len(cc["simulation_run_ids"])
        for cc in cases.values())

    inv["measurement_acts_exclude_simulations"] = c["measurement_acts"] == 201
    inv["every_representation_has_target_id"] = all(
        r.get("target_id") for s2 in series.values()
        for ax in ("x_representations", "y_representations") for r in s2[ax].values())
    inv["native_targets_are_not_universal"] = len(native_y) > 1
    inv["every_pair_declares_overlay_eligibility"] = all(
        "physical_overlay_allowed" in p for p in m["pairs"].values())
    # these are the gates: a nonzero computed violation must fail the build, not be filed
    inv["no_false_common_targets"] = false_common == 0
    inv["no_incompatible_plotted_pairs"] = incompat == 0
    inv["no_multi_series_target_violations"] = trio_violations == 0
    inv["no_duplicate_primary_entries"] = c["duplicate_primary_entries"] == 0
    inv["every_series_has_one_primary_entry"] = (
        c["result_series_without_primary_entry"] == 0
        and c["primary_result_entries"] == len(series))
    inv["no_multi_case_series_has_a_primary_case"] = (
        c["multi_case_series_with_primary_case"] == 0)
    inv["multi_case_series_all_have_a_sweep_entry"] = (
        c["multi_case_primary_entries"] == c["multi_case_result_series"])
    inv["no_range_field_loses_its_qualifier"] = losing == 0
    inv["no_ambiguous_range_lookups"] = ambiguous == 0
    inv["no_cross_case_constraint_false_positives"] = new_admits == 0
    inv["every_facet_declares_a_scope"] = all(
        f.get("scope") for f in m["facet_defs"])
    inv["key_based_intersection_would_have_been_wrong"] = key_based_false_common > 0
    return {"counts": c, "invariants": inv, "invariants_ok": all(inv.values()),
            "pair_statuses": dict(counts),
            "multi_case_examples": sorted(
                [{"series": s["id"], "n_cases": s["n_cases"], "cases": s["all_case_ids"]}
                 for s in multi_case], key=lambda x: -x["n_cases"])[:25],
            "multi_member_acts": [{"act": a["id"], "members": a["member_measurement_ids"],
                                   "series": a["series_ids"],
                                   "evidence": a["grouping_evidence"]}
                                  for a in multi_act]}


def render(model, val):
    tpl = Path(__file__).parent / "_workbench_v2_template.html"
    doc = tpl.read_text().replace("/*__MODEL__*/",
                                  json.dumps(model, ensure_ascii=False,
                                             separators=(",", ":")))
    (OUT / "psed_scientific_comparison_workbench.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
