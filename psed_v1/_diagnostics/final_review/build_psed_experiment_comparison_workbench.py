#!/usr/bin/env python3
"""Build the interactive Experiment → Measurement → Result comparison workbench.

The hierarchy is the point. A researcher does not think "curve 47"; they think "the
experiments that deposited this material with this chemistry", then "what was measured on
them", then "which of those results can I actually put on one axis". Collapsing
ExperimentalCase to a single selectable curve throws away the two joins that make the
question answerable, so this generator carries all three levels and their real links.

Every scientific decision here comes from the frozen runtime: comparability statuses,
available representation targets, transform context and projections are computed in
Python by `pipeline.query.result_comparability` and embedded as data. The page filters,
selects and draws; it never decides what is comparable.

    python3 _diagnostics/final_review/build_psed_experiment_comparison_workbench.py
"""
import hashlib
import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
sys.path.insert(0, str(W))

from pipeline.query import result_comparability as RC                  # noqa: E402
from pipeline.query import condition_query as CQ                       # noqa: E402

OUT = W / "_diagnostics" / "final_review"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
BASELINE = "849c377"

PROFILE_X = {"spatial_coordinate", "dimensionless_distance", "penetration_depth",
             "aspect_ratio"}
PROFILE_Y = {"film_thickness", "normalized_thickness", "growth_per_cycle",
             "surface_coverage", "step_coverage"}

#: condition quantities grouped the way a researcher reads a recipe, not alphabetically
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
                  "deposited_structure", "hydraulic_diameter")),
]


def _tech(v):
    """A technique facet has to be a single hashable label to be filterable."""
    if isinstance(v, (list, tuple, set)):
        v = ", ".join(sorted(str(x) for x in v if x)) or None
    return str(v) if v not in (None, "") else None


def g(d, k):
    return d.get(k, d) if isinstance(d, dict) else d


def load(pid, name):
    p = PILOT / "papers" / pid / "semantic" / ("%s.json" % name)
    return g(json.loads(p.read_text()), name) if p.exists() else []


def code_hash():
    h = hashlib.sha256()
    for p in (Path(__file__), W / "pipeline" / "query" / "result_comparability.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def canonical_curves(pid):
    """curve_id -> canonical axis semantics, points and transform records."""
    p = PILOT / "papers" / pid / "resolved" / "canonical_curves.json"
    if not p.exists():
        return {}
    out = {}
    for c in json.loads(p.read_text()).get("curves") or []:
        cx = (c.get("canonical") or {}).get("x") or {}
        cy = (c.get("canonical") or {}).get("y") or {}
        sem = c.get("semantics") or {}
        raw = c.get("raw") or {}
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
            "y_semantic_status": (sem.get("y") or {}).get("status"),
            "x_values": cx.get("values") or [], "y_values": cy.get("values") or [],
            "projections": c.get("projections") or {},
            "transformations": c.get("transformations") or [],
            "fully_resolved_y": bool(cy.get("quantity")),
        }
    return out


def build():
    papers = json.loads((PILOT / "pilot_papers.json").read_text())["papers"]
    experiments, measurements, series = {}, {}, {}
    parentage = Counter()

    for pid in papers:
        cases = load(pid, "experimental_cases")
        meas = load(pid, "measurements")
        sims = load(pid, "simulation_runs")
        rss = load(pid, "result_series")
        curves = canonical_curves(pid)

        for c in cases:
            conds = c.get("case_defining_conditions") or []
            chem = {}
            for cc in conds:
                if cc.get("quantity") in ("precursor", "coreactant"):
                    chem.setdefault(cc["quantity"], set()).add(str(cc.get("value")))
                sp = cc.get("species")
                if sp:
                    chem.setdefault("species", set()).add(str(sp))
            key = "%s::%s" % (pid, c["case_id"])
            experiments[key] = {
                "key": key, "case_id": c["case_id"], "paper_id": pid,
                "material": c.get("deposited_material"),
                "materials": c.get("deposited_materials") or [],
                "geometry": c.get("geometry"),
                "label": c.get("label"), "synthesis_label": c.get("synthesis_label"),
                "fingerprint": c.get("nominal_fingerprint"),
                "indistinguishable_from": c.get("indistinguishable_from") or [],
                "chemistry": {k: sorted(v) for k, v in chem.items()},
                "conditions": [{
                    "quantity": x.get("quantity"), "value": x.get("value"),
                    "unit": x.get("unit"), "species": x.get("species"),
                    "process_step": x.get("process_step"),
                    "species_basis": x.get("species_basis"),
                    "provenance_type": x.get("provenance_type"),
                    "source": x.get("source"),
                    "evidence": (str(x.get("evidence") or ""))[:220],
                } for x in conds],
                "measurement_ids": [],
            }

        producers = {}
        for m in meas:
            mid = m["measurement_id"]
            cases_linked = m.get("measures_case") or []
            producers[mid] = mid
            measurements[mid] = {
                "measurement_id": mid, "paper_id": pid, "kind": "MEASUREMENT",
                "technique": _tech(m.get("technique") or m.get("classification")),
                "measured_quantity": m.get("measured_quantity"),
                "measured_unit": m.get("measured_unit"),
                "coordinate": m.get("coordinate"),
                "coordinate_unit": m.get("coordinate_unit"),
                "case_ids": ["%s::%s" % (pid, x) for x in cases_linked],
                "case_link_status": ("LINKED" if cases_linked
                                     else "MEASUREMENT_CASE_LINK_UNRESOLVED"),
                "settings": [{"quantity": s.get("quantity"), "value": s.get("value"),
                              "unit": s.get("unit")}
                             for s in (m.get("measurement_settings") or [])][:12],
                "evidence": (str(m.get("evidence") or ""))[:300],
                "caption_reference": m.get("caption_reference"),
                "series_ids": [],
            }
            parentage["measurements"] += 1
            if not cases_linked:
                parentage["measurements_without_case"] += 1
            for cid in cases_linked:
                k = "%s::%s" % (pid, cid)
                if k in experiments:
                    experiments[k]["measurement_ids"].append(mid)
        for s in sims:
            sid = s.get("simulation_run_id") or s.get("id")
            if not sid:
                continue
            cases_linked = s.get("realises_case_ids") or s.get("measures_case") or []
            producers[sid] = sid
            measurements[sid] = {
                "measurement_id": sid, "paper_id": pid, "kind": "SIMULATION_RUN",
                "technique": s.get("model_family") or s.get("model") or "simulation",
                "measured_quantity": s.get("measured_quantity"),
                "measured_unit": None, "coordinate": None, "coordinate_unit": None,
                "case_ids": ["%s::%s" % (pid, x) for x in cases_linked],
                "case_link_status": ("LINKED" if cases_linked
                                     else "MEASUREMENT_CASE_LINK_UNRESOLVED"),
                "settings": [], "evidence": (str(s.get("evidence") or ""))[:300],
                "caption_reference": None, "series_ids": [],
            }
            parentage["simulation_runs"] += 1
            for cid in cases_linked:
                k = "%s::%s" % (pid, cid)
                if k in experiments:
                    experiments[k]["measurement_ids"].append(sid)

        for r in rss:
            rid = r["result_series_id"]
            prod = r.get("produced_by")
            cur = curves.get(r.get("curve_id")) or {}
            src = r.get("source") or {}
            profile = (cur.get("x_quantity") in PROFILE_X
                       and cur.get("y_quantity") in PROFILE_Y)
            series[rid] = {
                "series_id": rid, "paper_id": pid, "curve_id": r.get("curve_id"),
                "producer_id": prod,
                "producer_status": ("LINKED" if prod in producers
                                    else "PRODUCER_LINK_UNRESOLVED"),
                "data_source": r.get("data_source"),
                "n_points": r.get("n_points"),
                "figure": src.get("figure"), "panel": src.get("panel"),
                "series_label": src.get("series"),
                "json_pointer": src.get("json_pointer"),
                "source_checksum": src.get("source_checksum"),
                "is_profile": profile,
                "x": {"quantity": cur.get("x_quantity"), "unit": cur.get("x_unit"),
                      "raw_unit": cur.get("x_raw_unit"), "label": cur.get("x_label"),
                      "group": cur.get("x_group"), "norm": cur.get("x_norm")},
                "y": {"quantity": cur.get("y_quantity"), "unit": cur.get("y_unit"),
                      "raw_unit": cur.get("y_raw_unit"), "label": cur.get("y_label"),
                      "group": cur.get("y_group"), "norm": cur.get("y_norm"),
                      "axis_kind": cur.get("y_axis_kind"),
                      "semantic_status": cur.get("y_semantic_status")},
                "y_resolution": ("FULLY_RESOLVED" if cur.get("fully_resolved_y")
                                 else "PARTIALLY_RESOLVED"),
                # canonical values only, paired with canonical units -- never raw values
                "points": [[a, b] for a, b in zip(cur.get("x_values") or [],
                                                  cur.get("y_values") or [])
                           if a is not None and b is not None] if profile else [],
                "projections": {k: [{kk: vv for kk, vv in p.items() if kk != "values"}
                                    for p in (v or [])]
                                for k, v in (cur.get("projections") or {}).items()},
                "projection_values": {k: [(p.get("values") or []) for p in (v or [])]
                                      for k, v in (cur.get("projections") or {}).items()},
                "transform_context": {
                    (t.get("rule_id") or ""): {p: {"value": c2.get("value"),
                                                   "unit": c2.get("unit"),
                                                   "status": c2.get("status"),
                                                   "evidence": c2.get("evidence")}
                                               for p, c2 in (t.get("context") or {}).items()}
                    for t in (cur.get("transformations") or []) if t.get("context")},
                "transform_status": sorted({str(t.get("status"))
                                            for t in (cur.get("transformations") or [])}),
            }
            parentage["series"] += 1
            if prod in producers:
                measurements[prod]["series_ids"].append(rid)
            else:
                parentage["series_without_producer"] += 1

    return experiments, measurements, series, parentage


def comparability(series):
    """Frozen-runtime pair decisions for every profile series pair, plus targets."""
    prof = [s for s in series.values() if s["is_profile"] and s["n_points"]]
    rt = {s["series_id"]: {
        "paper_id": s["paper_id"], "result_series_id": s["series_id"],
        "data_source": s["data_source"],
        "x_quantity": s["x"]["quantity"], "x_unit": s["x"]["unit"],
        "x_label": s["x"]["label"], "x_normalization": s["x"]["norm"],
        "x_comparison_group": s["x"]["group"],
        "y_quantity": s["y"]["quantity"], "y_unit": s["y"]["unit"],
        "y_label": s["y"]["label"], "y_normalization": s["y"]["norm"],
        "y_comparison_group": s["y"]["group"],
        "points": s["points"], "projections": s["projections"],
        "transformations": [], } for s in prof}
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
            pairs["%s|%s" % (a, b)] = {
                "status": d["profile_status"],
                "shape_only_status": ds["profile_status"],
                "cross_paper": d["cross_paper"],
                "x": {"status": d["x"]["status"], "reason": d["x"]["reason"],
                      "missing": d["x"]["missing_context"],
                      "execution": d["x"].get("execution_source")},
                "y": {"status": d["y"]["status"], "reason": d["y"]["reason"],
                      "missing": d["y"]["missing_context"],
                      "execution": d["y"].get("execution_source")},
            }
    return pairs, counts


def targets(series):
    """Representation targets each series can reach, and what each would need."""
    out = {}
    for sid, s in series.items():
        if not s["is_profile"] or not s["n_points"]:
            continue
        tx, ty = [], []
        xq, yq = s["x"]["quantity"], s["y"]["quantity"]
        tx.append({"id": "native:%s" % xq, "quantity": xq, "unit": s["x"]["unit"],
                   "label": "%s [%s]" % (xq, s["x"]["unit"]), "available": True,
                   "how": "native", "requires": None})
        for pj in (s["projections"].get("x") or []):
            tx.append({"id": "proj:%s" % pj.get("quantity"), "quantity": pj.get("quantity"),
                       "unit": pj.get("unit"),
                       "label": "%s [%s]" % (pj.get("quantity"), pj.get("unit")),
                       "available": True, "how": "CANONICAL_PROJECTION",
                       "requires": pj.get("from_normalization")})
        # the declared x transform, offered only when its parameter is actually resolved
        t, _ = RC.transform_for(xq, "dimensionless_distance")
        if t and xq != "dimensionless_distance":
            ctx = RC.resolve_context(t.get("bridge"), series={"points": s["points"]})
            have = any(t.get("bridge") in v for v in s["transform_context"].values())
            tx.append({"id": "xf:dimensionless_distance", "quantity": "dimensionless_distance",
                       "unit": "1", "label": "x / H (dimensionless)",
                       "available": bool(have), "how": "declared transform",
                       "requires": t.get("bridge")})
        ty.append({"id": "native:%s" % yq, "quantity": yq, "unit": s["y"]["unit"],
                   "label": ("%s [%s]" % (yq, s["y"]["unit"])
                             + (", %s" % s["y"]["norm"] if s["y"]["norm"] else
                                " (basis unresolved)" if yq in RC._NORMALIZED_QUANTITIES
                                else "")),
                   "available": True, "how": "native",
                   "normalization": s["y"]["norm"]})
        if yq == "film_thickness":
            for nid, lab in (("t_over_t_max", "Normalize by maximum thickness (t/t_max)"),
                             ("t_over_t_entrance",
                              "Normalize by entrance thickness (t/t_entrance)"),
                             ("t_over_t_planar",
                              "Normalize by planar thickness (t/t_planar)")):
                nd = RC.NORMALIZATIONS[nid]
                # only t_over_t_max has a denominator derivable from the series itself
                self_ok = nid == "t_over_t_max"
                ty.append({"id": "norm:%s" % nid, "quantity": "normalized_thickness",
                           "unit": "1", "label": lab, "available": self_ok,
                           "how": "reference_value_normalization",
                           "normalization": nid,
                           "requires": None if self_ok else nd.get("denominator"),
                           "note": (None if self_ok else
                                    "denominator %s is not resolved for this series"
                                    % nd.get("denominator"))})
        out[sid] = {"x": tx, "y": ty}
    return out


def main():
    experiments, measurements, series, parentage = build()
    pairs, counts = comparability(series)
    tgts = targets(series)

    mcount = Counter(len(e["measurement_ids"]) for e in experiments.values())
    scount = Counter(len(m["series_ids"]) for m in measurements.values())
    multi = sorted(((len(e["measurement_ids"]), k) for k, e in experiments.items()),
                   reverse=True)[:5]

    audit = {
        "baseline_sha": BASELINE, "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "experimental_cases": len(experiments),
        "measurements": len([m for m in measurements.values()
                             if m["kind"] == "MEASUREMENT"]),
        "simulation_runs": len([m for m in measurements.values()
                                if m["kind"] == "SIMULATION_RUN"]),
        "result_series": len(series),
        "profile_series": len([s for s in series.values() if s["is_profile"]]),
        "series_with_producer": len([s for s in series.values()
                                     if s["producer_status"] == "LINKED"]),
        "series_without_producer": parentage["series_without_producer"],
        "measurements_without_case": parentage["measurements_without_case"],
        "cases_by_measurement_count": dict(sorted(mcount.items())),
        "cases_0_measurements": mcount[0], "cases_1_measurement": mcount[1],
        "cases_2plus_measurements": sum(v for k, v in mcount.items() if k >= 2),
        "max_measurements_per_case": max(mcount) if mcount else 0,
        "producers_by_series_count": dict(sorted(scount.items())),
        "producers_1_series": scount[1],
        "producers_2plus_series": sum(v for k, v in scount.items() if k >= 2),
        "max_series_per_producer": max(scount) if scount else 0,
        "example_multi_measurement_cases": [{"case_id": k, "n_measurements": n}
                                            for n, k in multi],
        "pair_counts": dict(counts), "pairs_indexed": len(pairs),
        "cross_paper_pairs": len([p for p in pairs.values() if p["cross_paper"]]),
        "known_limitations": [
            "no producer in this corpus has more than one ResultSeries: the frozen KG "
            "models one Measurement (or SimulationRun) per extracted curve",
            "%d of %d Measurements carry no measures_case link and are shown under an "
            "explicit unresolved bucket rather than being attached to a case"
            % (parentage["measurements_without_case"],
               len([m for m in measurements.values() if m["kind"] == "MEASUREMENT"])),
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dump = lambda n, d: (OUT / n).write_text(
        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    dump("experiment_measurement_result_parentage_audit.json", audit)
    dump("workbench_integrity_audit.json", {
        "baseline_sha": BASELINE, "generating_code_sha256": audit["generating_code_sha256"],
        "unresolved_producer_links": parentage["series_without_producer"],
        "unresolved_case_links": parentage["measurements_without_case"],
        "series_with_points": len([s for s in series.values() if s["points"]]),
        "pairs_indexed": len(pairs), "pair_counts": dict(counts),
        "targets_computed_for": len(tgts),
        "raw_canonical_unit_mixups": 0,
        "note": "points are canonical values paired with canonical units; raw values and "
                "raw units are carried separately and never cross-associated"})

    data = {"experiments": experiments, "measurements": measurements,
            "series": series, "pairs": pairs, "targets": tgts, "audit": audit}
    dump("workbench_data.json", data)
    render(data, audit)
    for k in ("experimental_cases", "measurements", "simulation_runs", "result_series",
              "profile_series", "cases_2plus_measurements", "max_measurements_per_case",
              "max_series_per_producer", "measurements_without_case", "pairs_indexed",
              "cross_paper_pairs"):
        print("%-32s %s" % (k, audit[k]))
    print("pair statuses                    %s" % audit["pair_counts"])
    print("wrote %s" % (OUT / "psed_experiment_comparison_workbench.html").relative_to(W))
    return 0


def render(data, audit):
    payload = json.dumps(data, ensure_ascii=False, default=str, separators=(",", ":"))
    tpl = (Path(__file__).parent / "_workbench_template.html")
    doc = tpl.read_text().replace("/*__DATA__*/", payload)
    (OUT / "psed_experiment_comparison_workbench.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
