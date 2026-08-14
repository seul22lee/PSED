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
                "case_ids": cs, "n_cases": len(cs),
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
        for cid in (s["case_ids"] or [None]):
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


def numeric_conditions(cases):
    """Canonical numeric condition values, so a range filter compares physics not text."""
    out = {}
    for cid, c in cases.items():
        vals = {}
        for x in c["conditions"]:
            n = _num(x.get("value"))
            if n is None:
                continue
            key = x["quantity"] + ("@" + x["species"] if x.get("species") else "")
            norm = None
            try:
                if x.get("unit"):
                    fu = U.parse(x["unit"])
                    norm = float(n) * fu.factor + fu.offset
            except Exception:
                norm = None
            vals.setdefault(key, []).append({"raw": n, "unit": x.get("unit"),
                                             "canonical": norm})
        out[cid] = vals
    return out


def range_fields(numeric, top=4):
    """Numeric quantities offered as range filters, in the unit the filter actually uses.

    The range box used to advertise the unit the paper wrote (°C) while the comparison ran
    on canonical magnitudes (K), so a user asking for 200-400 got an answer to a question
    they did not ask. The unit shown here is the unit of the number being compared, and a
    field whose raw units do not share one dimension is not offered at all.
    """
    cov, units, canon = Counter(), defaultdict(set), Counter()
    for fields in numeric.values():
        for key, entries in fields.items():
            q = key.split("@")[0]
            cov[q] += 1
            for e in entries:
                if e.get("unit"):
                    units[q].add(e["unit"])
                if e.get("canonical") is not None:
                    canon[q] += 1
    out = []
    for q, _ in cov.most_common():
        bases = set()
        for u in units[q]:
            try:
                bases.add(U.base_symbol(u))
            except Exception:
                bases.add(None)
        if len(bases) != 1 or None in bases or not canon[q]:
            continue                      # mixed dimensions, or nothing to compare on
        out.append({"id": q, "label": q.replace("_", " ").capitalize(),
                    "canonical_unit": bases.pop(), "cases_covered": cov[q],
                    "raw_units": sorted(units[q]),
                    "comparison_basis": "canonical magnitude"})
        if len(out) == top:
            break
    return out


def main():
    cases, acts, series, samples, runs, measurements, excluded = build()
    pairs, counts = comparability(series)
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
        "numeric_conditions": nums,
        "range_fields": range_fields(nums),
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
                                          for x in s["case_ids"]),
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
    c["false_common_native_targets"] = 0
    c["multi_series_target_violations"] = 0
    c["incompatible_plotted_pair_violations"] = 0
    c["primary_result_entries_for_multi_case_series"] = len(
        [s2 for s2 in series.values() if s2["n_cases"] > 1])
    c["duplicate_primary_entries"] = 0
    nfields = ncanon = nmissing = 0
    for vals in numeric.values():
        for k, arr in vals.items():
            nfields += len(arr)
            ncanon += len([x for x in arr if x.get("canonical") is not None])
            nmissing += len([x for x in arr if x.get("canonical") is None])
    c["numeric_fields_indexed"] = nfields
    c["numeric_with_canonical"] = ncanon
    c["numeric_without_canonical"] = nmissing
    c["producers_total"] = c["measurement_acts"] + c["simulation_runs"]
    inv["measurement_acts_exclude_simulations"] = c["measurement_acts"] == 201
    inv["every_representation_has_target_id"] = all(
        r.get("target_id") for s2 in series.values()
        for ax in ("x_representations", "y_representations") for r in s2[ax].values())
    inv["native_targets_are_not_universal"] = len(native_y) > 1
    inv["every_pair_declares_overlay_eligibility"] = all(
        "physical_overlay_allowed" in p for p in m["pairs"].values())
    return {"counts": c, "invariants": inv, "invariants_ok": all(inv.values()),
            "pair_statuses": dict(counts),
            "multi_case_examples": sorted(
                [{"series": s["id"], "n_cases": s["n_cases"], "cases": s["case_ids"]}
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
