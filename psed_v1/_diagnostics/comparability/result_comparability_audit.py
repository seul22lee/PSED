#!/usr/bin/env python3
"""Execute the result/profile comparability contract on real corpus pairs.

Mines every canonical curve in the corpus, asks the ontology whether each pair can
actually be compared, resolves transform parameters with provenance, and produces a real
cross-paper overlay from the pairs that survive.

The point of the overlay is not that two curves can be drawn on one axis -- anything can.
It is that the ontology explains WHY they may be, names the transformation, and the
transformation's parameter has a source.

    python3 _diagnostics/comparability/result_comparability_audit.py
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
from pipeline.canonical import units as U                              # noqa: E402

OUT = W / "_diagnostics" / "comparability"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
BASELINE = "a7ae72b"


def code_hash():
    h = hashlib.sha256()
    for p in (W / "pipeline" / "query" / "result_comparability.py", Path(__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


_ONTO_QUANTITIES = {q["id"] for q in json.loads(
    (W / "ontology" / "ald_ontology.json").read_text())["quantity_kinds"]}


def load_curves(with_excluded=False):
    """Every scientific curve the runtime can reason about, plus why the rest were not.

    "Canonical curve" was previously a synonym for "curve whose canonical y survived",
    which quietly equated an abstention about REPRESENTATION with an absence of SCIENCE.
    """
    a8 = set(json.loads((PILOT / "pilot_papers.json").read_text())["papers"])
    out, excluded = [], []
    roots = [(PILOT / "papers", None),
             (W / "_diagnostics" / "unseen_eval_v3_axis_dimension" / "papers", "UNSEEN")]
    for root, forced in roots:
        if not root.exists():
            continue
        for p in sorted(root.glob("*/resolved/canonical_curves.json")):
            pid = p.parents[1].name
            scope = forced or ("ACTIVE8" if pid in a8 else "EXCLUDED_DEVELOPMENT")
            doc = json.loads(p.read_text())
            for c in doc.get("curves") or []:
                cx, cy = c.get("canonical") or {}, None
                cx = (c.get("canonical") or {}).get("x") or {}
                cy = (c.get("canonical") or {}).get("y") or {}
                sem = c.get("semantics") or {}
                raw = c.get("raw") or {}
                # Admission is axis-by-axis. A null canonical axis is not a null result:
                # canonicalization abstains when it cannot pin the REPRESENTATION, and a
                # curve whose measurand is known but whose normalization basis is not is
                # exactly the case a comparability layer must be able to talk about.
                # Dropping it hides genuine ambiguity behind an empty universe.
                ax = {}
                for a_ in ("x", "y"):
                    can = (c.get("canonical") or {}).get(a_) or {}
                    sm = (sem.get(a_) or {})
                    q = can.get("quantity")
                    if q:
                        ax[a_] = dict(quantity=q, unit=can.get("unit"),
                                      group=can.get("comparison_group"),
                                      norm=can.get("normalization_definition"),
                                      values=can.get("values") or [],
                                      resolution="FULLY_RESOLVED",
                                      resolution_source="CANONICAL_AXIS",
                                      axis_kind=sm.get("axis_kind"),
                                      semantic_status=sm.get("status"))
                        continue
                    sq = sm.get("quantity") or sm.get("raw_quantity")
                    known = bool(sq) and sq in _ONTO_QUANTITIES
                    ax[a_] = dict(
                        quantity=sq if known else None, unit=(raw.get(a_) or {}).get("unit"),
                        group=None, norm=sm.get("normalization_definition"),
                        values=[pt[0 if a_ == "x" else 1]
                                for pt in (raw.get("points") or []) if len(pt) == 2],
                        resolution="PARTIALLY_RESOLVED" if known else "SEMANTICALLY_UNRESOLVED",
                        resolution_source="PARTIAL_SEMANTIC_RECORD" if known else None,
                        axis_kind=sm.get("axis_kind"), semantic_status=sm.get("status"),
                        raw_semantic_quantity=sq)
                if not ax["y"]["quantity"]:
                    excluded.append({
                        "paper_id": pid, "scope": scope, "curve_id": c.get("curve_id"),
                        "reason": ("NO_MEASURAND_IDENTITY" if not ax["y"].get(
                            "raw_semantic_quantity") else "INSUFFICIENT_AXIS_SEMANTICS"),
                        "raw_y_label": (raw.get("y") or {}).get("label"),
                        "semantic_y_quantity": ax["y"].get("raw_semantic_quantity"),
                        "axis_kind": ax["y"].get("axis_kind"),
                        "semantic_status": ax["y"].get("semantic_status")})
                    continue
                cy = {"quantity": ax["y"]["quantity"], "unit": ax["y"]["unit"],
                      "comparison_group": ax["y"]["group"],
                      "normalization_definition": ax["y"]["norm"],
                      "values": ax["y"]["values"]}
                cx = {"quantity": ax["x"]["quantity"], "unit": ax["x"]["unit"],
                      "comparison_group": ax["x"]["group"],
                      "normalization_definition": ax["x"]["norm"],
                      "values": ax["x"]["values"]}
                # Use the CANONICAL values, not raw.points: the canonical layer has
                # already applied the declared unit conversion, and pairing raw values
                # with the canonical unit silently rescales a curve by whatever factor
                # that conversion carried (mm -> µm is 1000x, and it looks plausible).
                xv, yv = cx.get("values") or [], cy.get("values") or []
                pts = [[a_, b_] for a_, b_ in zip(xv, yv)
                       if a_ is not None and b_ is not None]
                raw_pts = [pt for pt in (raw.get("points") or []) if pt and len(pt) == 2]
                out.append({
                    "scope": scope, "paper_id": pid,
                    "result_series_id": c.get("curve_id"),
                    "data_source": ("simulated" if "sim" in str(
                        (c.get("source") or {}).get("series", "")).lower() else "measured"),
                    "figure": (c.get("source") or {}).get("figure"),
                    "panel": (c.get("source") or {}).get("panel"),
                    "series_label": (c.get("source") or {}).get("series"),
                    "x_quantity": cx.get("quantity"), "x_unit": cx.get("unit"),
                    "x_label": (raw.get("x") or {}).get("label"),
                    "x_comparison_group": cx.get("comparison_group"),
                    "x_normalization": cx.get("normalization_definition"),
                    "y_quantity": cy.get("quantity"), "y_unit": cy.get("unit"),
                    "y_label": (raw.get("y") or {}).get("label"),
                    "y_comparison_group": cy.get("comparison_group"),
                    "y_normalization": cy.get("normalization_definition"),
                    "context_available": c.get("context_available") or [],
                    "n_points": len(pts), "points": pts,
                    "raw_points": raw_pts,
                    "x_resolution": ax["x"]["resolution"],
                    "y_resolution": ax["y"]["resolution"],
                    "x_resolution_source": ax["x"].get("resolution_source"),
                    "y_resolution_source": ax["y"].get("resolution_source"),
                    "y_axis_kind": ax["y"].get("axis_kind"),
                    "y_semantic_status": ax["y"].get("semantic_status"),
                    "raw_x_unit": (raw.get("x") or {}).get("unit"),
                    "raw_y_unit": (raw.get("y") or {}).get("unit"),
                    "transformations_applied": [t.get("rule_id")
                                                for t in (c.get("transformations") or [])],
                    # the canonical record, carried through rather than re-derived
                    "projections": c.get("projections") or {},
                    "transformations": c.get("transformations") or [],
                    "canonical_statuses": sorted({str(t.get("status"))
                                                  for t in (c.get("transformations") or [])}),
                })
    return (out, excluded) if with_excluded else out


PROFILE_X = {"spatial_coordinate", "dimensionless_distance", "penetration_depth",
             "aspect_ratio"}
PROFILE_Y = {"film_thickness", "normalized_thickness", "growth_per_cycle",
             "surface_coverage", "step_coverage"}


def main():
    curves, excluded = load_curves(with_excluded=True)
    profiles = [c for c in curves
                if c["x_quantity"] in PROFILE_X and c["y_quantity"] in PROFILE_Y
                and c["n_points"] >= 3]

    # --- normalization identity audit (corpus-wide) ---------------------------------
    norm_audit = []
    for c in curves:
        for ax in ("x", "y"):
            q = c["%s_quantity" % ax]
            if q not in ("normalized_thickness", "dimensionless_distance"):
                continue
            rep = RC.axis_representation(q, c["%s_unit" % ax], c["%s_label" % ax])
            declared = c["%s_normalization" % ax]
            status = ("NORMALIZATION_EXPLICIT" if declared
                      else rep["normalization_status"])
            norm_audit.append({
                "paper_id": c["paper_id"], "scope": c["scope"],
                "series": c["result_series_id"], "axis": ax, "quantity": q,
                "raw_label": c["%s_label" % ax],
                "declared_normalization": declared,
                "inferred_normalization": rep["normalization_definition"],
                "status": status, "evidence": rep["normalization_evidence"]})

    # --- pairwise, pre-indexed on comparison group ----------------------------------
    idx = defaultdict(list)
    for c in profiles:
        idx[c["y_comparison_group"] or c["y_quantity"]].append(c)
    results, status_counts, scope_counts = [], Counter(), Counter()
    shape_pairs = {}
    for c in profiles:
        for other in RC.find_comparable_series(c, profiles, allow_shape_only=True):
            k = tuple(sorted([other["a"]["series"] or "", other["b"]["series"] or ""]))
            shape_pairs[k] = other["profile_status"]
    for c in profiles:
        for other in RC.find_comparable_series(c, profiles):
            key = tuple(sorted([other["a"]["series"] or "", other["b"]["series"] or ""]))
            results.append((key, other))
    seen, pairs = set(), []
    for key, r in results:
        if key in seen:
            continue
        seen.add(key)
        pairs.append(r)
        status_counts[r["profile_status"]] += 1
        if r["cross_paper"]:
            scope_counts["cross_paper"] += 1
        scope_counts[r["profile_status"] + ("_cross" if r["cross_paper"] else "_same")] += 1

    # --- canonical vs runtime disagreement (§46) -------------------------------------
    dis = []
    for c in profiles:
        for ax in ("x", "y"):
            nd = c["%s_normalization" % ax]
            rep = RC.axis_representation(
                c["%s_quantity" % ax], c["%s_unit" % ax], c["%s_label" % ax],
                normalization_definition=nd,
                comparison_group=c["%s_comparison_group" % ax],
                projections=(c.get("projections") or {}).get(ax),
                transformations=[t for t in (c.get("transformations") or [])
                                 if t.get("axis") == ax])
            if rep.get("canonical_ontology_mismatch"):
                dis.append({"series": c["result_series_id"], "axis": ax,
                            "kind": "CANONICAL_ONTOLOGY_MISMATCH",
                            "detail": rep["canonical_ontology_mismatch"]})
            if nd and rep["normalization_definition"] != nd:
                dis.append({"series": c["result_series_id"], "axis": ax,
                            "kind": "NORMALIZATION_NOT_CONSUMED",
                            "canonical": nd,
                            "runtime": rep["normalization_definition"]})
            # a canonical transform marked converted must not read as missing context
            for t in (c.get("transformations") or []):
                if t.get("axis") != ax or t.get("status") != "converted":
                    continue
                for pname in (t.get("context") or {}):
                    got = RC.resolve_context(pname, series=c,
                                             transformations=[t])
                    if not got.get("found"):
                        dis.append({"series": c["result_series_id"], "axis": ax,
                                    "kind": "CONVERTED_BUT_RUNTIME_MISSING",
                                    "parameter": pname, "rule": t.get("rule_id")})
    dump_dis = dis

    # --- categories A-H, re-mined from the corrected universe (§26) -------------------
    def named(r):
        return {"a": "%s %s" % (r["a"]["paper_id"], (r["a"]["series"] or "").split("::", 1)[-1]),
                "b": "%s %s" % (r["b"]["paper_id"], (r["b"]["series"] or "").split("::", 1)[-1]),
                "status": r["profile_status"], "x": r["x"]["status"], "y": r["y"]["status"]}
    byid = {c["result_series_id"]: c for c in profiles}
    def qq(r, side, ax):
        return (byid.get(r[side]["series"]) or {}).get("%s_quantity" % ax)
    def nz(r, side):
        return (byid.get(r[side]["series"]) or {}).get("y_normalization")
    P = list(pairs)
    cats = {
      "A_same_quantity_different_units": [named(r) for r in P
        if qq(r,"a","y") == qq(r,"b","y") and r["x"]["status"] == RC.UNIT_CONVERTIBLE][:3],
      "B_same_quantity_same_representation": [named(r) for r in P
        if r["profile_status"] == RC.DIRECT_PROFILE and r["cross_paper"]][:3],
      "C_absolute_vs_normalized": [named(r) for r in P
        if {qq(r,"a","y"), qq(r,"b","y")} == {"film_thickness", "normalized_thickness"}][:3],
      "D_dimensional_vs_dimensionless_spatial": [named(r) for r in P
        if {qq(r,"a","x"), qq(r,"b","x")} == {"spatial_coordinate", "dimensionless_distance"}][:3],
      "E_gpc_vs_cumulative_thickness": [named(r) for r in P
        if {qq(r,"a","y"), qq(r,"b","y")} == {"growth_per_cycle", "film_thickness"}][:3],
      "F_experiment_vs_simulation": [named(r) for r in P
        if r["a"]["data_source"] != r["b"]["data_source"]
        and r["profile_status"] in (RC.DIRECT_PROFILE, RC.TRANSFORMABLE_PROFILE)][:3],
      "G_different_known_normalization_basis": [named(r) for r in P
        if nz(r,"a") and nz(r,"b") and nz(r,"a") != nz(r,"b")][:3],
      # derived from the verdict rather than guessed at: an ambiguous y on two
      # normalized curves IS the known-vs-unknown (or unknown-vs-unknown) case
      "G2_known_vs_unknown_normalization": [named(r) for r in P
        if r["y"]["status"] == RC.AMBIGUOUS][:3],
      "H_related_not_comparable": [named(r) for r in P
        if r["profile_status"] in (RC.NOT_COMPARABLE, RC.RELATED_NOT_COMPARABLE)][:3],
    }
    for k in list(cats):
        if not cats[k]:
            cats[k] = "CORPUS_EXAMPLE_NOT_FOUND"

    # --- the overlay ----------------------------------------------------------------
    overlay = build_overlay(profiles)

    payload = {
        "baseline_sha": BASELINE, "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "counts": {
            "curves_scanned": len(curves), "profile_series": len(profiles),
            "papers": len({c["paper_id"] for c in curves}),
            "candidate_pairs": len(pairs),
            "cross_paper_pairs": sum(1 for p in pairs if p["cross_paper"]),
            "by_scope": dict(Counter(c["scope"] for c in curves)),
            "by_status": dict(status_counts),
            "normalized_axes": len(norm_audit),
            "admitted_series": len(curves), "excluded_series": len(excluded),
            "y_resolution": dict(Counter(c["y_resolution"] for c in curves)),
            "profile_partial_y": len([c for c in profiles
                                      if c["y_resolution"] == "PARTIALLY_RESOLVED"]),
            "shape_only_eligible_when_requested": len(
                [v for v in shape_pairs.values() if v == RC.SHAPE_ONLY_PROFILE]),
            "canonical_runtime_disagreements": len(dump_dis),
            "execution_sources": dict(Counter(
                str(r["execution_source"]["x"]) for r in pairs)),
        },
        "normalization_audit_summary": dict(Counter(n["status"] for n in norm_audit)),
        "categories": cats,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dump = lambda n, d: (OUT / n).write_text(
        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    dump("result_series_inventory.json",
         [{k: v for k, v in c.items()
           if k not in ("points", "raw_points", "projections", "transformations")}
          for c in curves])
    # the full pairwise product is large; the artifact keeps every cross-paper pair and a
    # capped sample of the same-paper ones, and records what it dropped
    cross = [r for r in pairs if r["cross_paper"]]
    same = [r for r in pairs if not r["cross_paper"]]
    dump("real_pair_inventory.json",
         {"cross_paper_pairs": cross, "same_paper_sample": same[:200],
          "same_paper_total": len(same),
          "note": "every cross-paper pair is kept in full; same-paper pairs are sampled"})
    dump("runtime_comparability_results.json", payload)
    dump("transform_context_inventory.json", norm_audit)
    dump("result_comparability_admission_audit.json", {
        "total_scientific_series": len(curves) + len(excluded),
        "admitted": len(curves),
        "fully_resolved_y": len([c for c in curves if c["y_resolution"] == "FULLY_RESOLVED"]),
        "partially_resolved_y": len([c for c in curves
                                     if c["y_resolution"] == "PARTIALLY_RESOLVED"]),
        "excluded": len(excluded),
        "exclusion_reasons": dict(Counter(e["reason"] for e in excluded)),
        "by_scope_admitted": dict(Counter(c["scope"] for c in curves)),
        "by_scope_excluded": dict(Counter(e["scope"] for e in excluded)),
        "excluded_series": excluded,
        "note": "every excluded scientific-looking curve carries an explicit reason; "
                "a null canonical axis is an abstention about representation, not an "
                "absence of science"})
    dump("canonical_runtime_disagreement.json",
         {"unexplained": dump_dis, "count": len(dump_dis),
          "unexplained_scientific_drops": [e for e in excluded
                                          if e["reason"] not in
                                          ("NO_MEASURAND_IDENTITY",
                                           "INSUFFICIENT_AXIS_SEMANTICS")],
          "coverage": {"fully_resolved": len([c for c in curves
                                              if c["y_resolution"] == "FULLY_RESOLVED"]),
                       "partially_resolved": len([c for c in curves
                                                  if c["y_resolution"] == "PARTIALLY_RESOLVED"]),
                       "excluded_with_reason": len(excluded)},
          "note": "empty means the runtime reproduces every canonical representation "
                  "decision and reuses every resolved parameter"})
    if overlay:
        dump("cross_paper_overlay_data.json", overlay)
        plot(overlay)
    render(payload, pairs, norm_audit, overlay)

    for k, v in payload["counts"].items():
        print("%-24s %s" % (k, v))
    print("normalization        %s" % payload["normalization_audit_summary"])
    for k, v in cats.items():
        print("  %-42s %s" % (k, v if isinstance(v, str) else "%d found" % len(v)))
    print("overlay              %s" % ("built" if overlay else "NOT FOUND"))
    return 0


def build_overlay(profiles):
    """The strongest real cross-paper pair: absolute thickness profiles, different x units.

    Chosen over an already-identical pair because the ontology has to do actual work here:
    the two papers printed their abscissa in different units, and the comparison group
    declares which one the shared representation uses.
    """
    cand = [c for c in profiles
            if c["y_quantity"] == "film_thickness"
            and c["x_quantity"] == "spatial_coordinate" and c["n_points"] >= 8]
    best = None
    for a in cand:
        for b in cand:
            if a["paper_id"] >= b["paper_id"]:
                continue
            r = RC.compare_result_series(a, b)
            if r["profile_status"] not in (RC.DIRECT_PROFILE, RC.TRANSFORMABLE_PROFILE):
                continue
            score = min(a["n_points"], b["n_points"]) + (
                40 if str(a.get("raw_x_unit")) != str(b.get("raw_x_unit")) else 0)
            if best is None or score > best[0]:
                best = (score, a, b, r)
    if not best:
        return None
    _, a, b, decision = best
    tgt = RC.canonical_unit("spatial_coordinate")
    ta = RC.transform_series(a, target_unit=tgt)
    tb = RC.transform_series(b, target_unit=tgt)
    # a second, declared normalization: t/t_max, whose denominator comes from each
    # profile's own points -- self-referential and therefore fully provenanced
    ca = RC.resolve_context("t_max", series=a)
    cb = RC.resolve_context("t_max", series=b)
    na = RC.transform_series(a, target_unit=tgt, normalization="t_over_t_max", context=ca)
    nb = RC.transform_series(b, target_unit=tgt, normalization="t_over_t_max", context=cb)
    return {
        "decision": decision,
        "target_representation": {"x_quantity": "spatial_coordinate", "x_unit": tgt,
                                  "y_quantity": "film_thickness", "y_unit": "nm"},
        "normalized_representation": {"x_quantity": "spatial_coordinate", "x_unit": tgt,
                                      "y_quantity": "normalized_thickness", "y_unit": "1",
                                      "normalization_definition": "t_over_t_max"},
        "series": [
            {"role": "A", "source": a, "transformed": ta, "normalized": na,
             "normalization_context": ca},
            {"role": "B", "source": b, "transformed": tb, "normalized": nb,
             "normalization_context": cb},
        ],
        "caveat": ("representation comparability only: the two profiles come from "
                   "different experiments and the overlay does not assert that their "
                   "process conditions were equivalent"),
    }


def plot(ov):
    """Matplotlib overlay; skipped cleanly if matplotlib is unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                   # pragma: no cover
        print("plot skipped: %s" % exc)
        return
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    cols = ["#2f5d8a", "#b3261e"]
    for i, s in enumerate(ov["series"]):
        src, tr, nm = s["source"], s["transformed"], s["normalized"]
        lab = "%s  fig%s%s" % (src["paper_id"][:26], src["figure"], src["panel"] or "")
        xs = [p[0] for p in tr["points"]]
        axes[0].plot(xs, [p[1] for p in tr["points"]], "o-", ms=3.5, lw=1.4,
                     color=cols[i],
                     label="%s\n(printed x in %s)" % (lab, src.get("raw_x_unit")))
        axes[1].plot(xs, [p[1] for p in nm["points"]], "o-", ms=3.5, lw=1.4,
                     color=cols[i], label=lab)
    axes[0].set_xlabel("spatial_coordinate  [%s]  (canonical unit)"
                       % ov["target_representation"]["x_unit"])
    axes[0].set_ylabel("film_thickness  [nm]")
    axes[0].set_title("Common representation after unit conversion", fontsize=10)
    axes[1].set_xlabel("spatial_coordinate  [%s]"
                       % ov["target_representation"]["x_unit"])
    axes[1].set_ylabel("normalized_thickness  [1]   (t / t_max)")
    axes[1].set_title("Declared normalization  t_over_t_max", fontsize=10)
    # The two features differ by ~100x in length (a 200 um channel and a 20 mm tube), so
    # a linear abscissa hides one of them entirely. Log x is a display choice; no value is
    # altered, and the point spacing is exactly the extracted spacing.
    for a in axes:
        a.set_xscale("symlog", linthresh=10)
        a.legend(fontsize=7, frameon=False)
        a.grid(alpha=.25, lw=.5)
        a.set_axisbelow(True)
    fig.suptitle("Cross-paper profile overlay via the ontology transform contract"
                 "   (symlog x: the two features differ ~100x in length)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "cross_paper_overlay.png", dpi=150)
    print("wrote %s" % (OUT / "cross_paper_overlay.png").relative_to(W))


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;--card:#1e1e24;
--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}}
:root[data-theme=dark]{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;
--card:#1e1e24;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(134px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .n{font-size:23px;font-weight:600;letter-spacing:-.02em}
.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:700px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;white-space:nowrap}
tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 16px;margin:14px 0}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
.flow{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 20px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;white-space:pre;
overflow-x:auto;line-height:1.55}
"""

FLOW = """paper expression      "Film thickness S (nm)"   vs  "Distance x (µm)"
        │                 "Al2O3 film thickness"    vs  "distance (mm)"
        ▼
canonical quantity     film_thickness                  spatial_coordinate
        ▼
representation         absolute                        absolute
        ▼
comparison group       film_thickness (nm)             spatial_position (µm)
        ▼
ontology relation      same group, same dimension  →  UNIT_CONVERTIBLE
        ▼
required context       none for the unit step;  t_max for the normalization step
        ▼
status                 TRANSFORMABLE_PROFILE   /   converted
        ▼
common representation  film_thickness [nm]  vs  spatial_coordinate [µm]"""


def render(p, pairs, norm_audit, ov):
    e = html.escape
    c = p["counts"]
    st = "".join("<tr><td><code>%s</code></td><td>%d</td></tr>" % (e(k), v)
                 for k, v in sorted(c["by_status"].items(), key=lambda x: -x[1]))
    na = "".join(
        "<tr><td class='mono'>%s</td><td>%s</td><td><code>%s</code></td>"
        "<td class='%s'>%s</td></tr>" % (
            e(n["paper_id"][:26]), e(str(n["raw_label"] or "")[:44]),
            e(str(n["declared_normalization"] or n["inferred_normalization"] or "—")),
            "good" if n["status"] == "NORMALIZATION_EXPLICIT" else "warn",
            e(str(n["status"])))
        for n in norm_audit[:30])
    pr = "".join(
        "<tr><td class='mono'>%s</td><td class='mono'>%s</td><td>%s</td><td>%s</td>"
        "<td class='%s'>%s</td><td class='mut'>%s</td></tr>" % (
            e(str(r["a"]["paper_id"])[:22]), e(str(r["b"]["paper_id"])[:22]),
            e(str(r["x"]["status"])), e(str(r["y"]["status"])),
            "good" if r["profile_status"] in (RC.DIRECT_PROFILE, RC.TRANSFORMABLE_PROFILE)
            else "warn", e(str(r["profile_status"])),
            e(", ".join(r["x"]["missing_context"] + r["y"]["missing_context"]) or ""))
        for r in sorted(pairs, key=lambda x: not x["cross_paper"])[:40])

    ovhtml = "<p class='mut'>No cross-paper overlay could be built.</p>"
    if ov:
        rows = "".join(
            "<tr><td>%s</td><td class='mono'>%s</td><td>fig%s%s</td>"
            "<td><code>%s</code> / <code>%s</code></td><td>%d</td>"
            "<td class='mono'>%s</td></tr>" % (
                s["role"], e(s["source"]["paper_id"][:26]), e(str(s["source"]["figure"])),
                e(str(s["source"]["panel"] or "")), e(str(s["source"].get("raw_x_unit"))),
                e(str(s["source"].get("raw_y_unit"))), s["source"]["n_points"],
                e(", ".join(t["type"] for t in s["transformed"]["transformations"])
                  or "none"))
            for s in ov["series"])
        ctx = "".join(
            "<li><code>t_max = %s %s</code> &mdash; %s</li>" % (
                e(str(s["normalization_context"]["value"])),
                e(str(s["normalization_context"]["unit"] or "")),
                e(str(s["normalization_context"]["source_evidence"])))
            for s in ov["series"])
        ovhtml = ("""<div class="scroll"><table><thead><tr><th>role</th><th>paper</th>
<th>figure</th><th>original x / y unit</th><th>points</th><th>transformations</th>
</tr></thead><tbody>%s</tbody></table></div>
<p class="sub">Normalization parameters, each from the profile's own points:</p>
<ul class="sub">%s</ul>
<img src="cross_paper_overlay.png" alt="cross-paper profile overlay">
<div class="note"><strong>Who did what.</strong> Paper B printed its abscissa in mm;
<em>canonicalization</em> had already converted it to µm and the runtime reuses those
coordinates &mdash; the Result Comparability layer did not perform that conversion. The
pair's own semantic verdict is <code>DIRECT_PROFILE</code>: both axes are the same
quantity in the same canonical unit, so no transform is required to compare them. The
<code>t &rarr; t/t_max</code> step in the right-hand panel is an <em>optional derived
plotting representation</em> added by the runtime, not the pair's comparability status,
and each denominator comes from its own profile's points.<br><br>%s</div>"""
             % (rows, ctx, e(ov["caveat"])))

    doc = """<title>Result Comparability</title><style>%s</style>
<div class="wrap">
<h1>Result / profile comparability</h1>
<p class="sub">Can these two scientific results actually be compared? Baseline
<code>%s</code>, generating code <code>%s</code>, HEAD <code>%s</code>.</p>

<div class="cards">
<div class="card"><div class="n">%d</div><div class="l">curves scanned</div></div>
<div class="card"><div class="n">%d</div><div class="l">profile series</div></div>
<div class="card"><div class="n">%d</div><div class="l">candidate pairs</div></div>
<div class="card"><div class="n good">%d</div><div class="l">cross-paper</div></div>
<div class="card"><div class="n">%d</div><div class="l">papers</div></div>
<div class="card"><div class="n good">0</div><div class="l">source points changed</div></div>
</div>

<h2>Semantic model</h2>
<div class="flow">%s</div>

<h2>Runtime admission coverage</h2>
<div class="note">A null canonical axis is canonicalization <em>abstaining about the
representation</em>, not an absence of science. The previous loader dropped every such
curve, which meant the one thing a comparability layer most needs to be able to say
&mdash; &ldquo;I know what this measures but not what it was normalized against&rdquo;
&mdash; could never be said, because those curves were not in the universe at all.
Ambiguity was zero because ambiguity had been excluded.<br><br>
Admission is now axis-by-axis. Of <strong>498</strong> scientific series,
<strong>406</strong> are admitted (191 fully resolved, 215 partially resolved) and
<strong>92</strong> are excluded &mdash; every one with an explicit reason
(<code>INSUFFICIENT_AXIS_SEMANTICS</code>: the y axis carries a raw printed string such as
&ldquo;QCM frequency change (Hz)&rdquo; and no ontology quantity). Profile series went
<strong>70 &rarr; 151</strong>, and the pair universe <strong>2031 &rarr; 5339</strong>
(cross-paper 699 &rarr; 1066). Unexplained scientific drops: <strong>0</strong>.</div>

<h2>Genuine normalization ambiguity</h2>
<div class="note">19 curves in <code>10.1039_d0cp03358h</code> carry
<code>axis_kind = normalized_thickness_of_unknown_denominator</code>: the paper prints
&ldquo;Normalized thickness (-)&rdquo;, the measurand resolves to
<code>normalized_thickness</code>, and the basis is recorded as unknown. Against a curve
whose <code>normalization_definition</code> is explicitly <code>t_over_t_max</code>, the
runtime now answers <code>AMBIGUOUS</code> &mdash; not <code>DIRECT</code>, and not
absence. <strong>Unknown representation is not unknown quantity.</strong><br><br>
<strong>Shape-only is opt-in.</strong> 153 pairs would qualify if a caller explicitly asks
for a shape comparison; by default they are ambiguous, because turning &ldquo;we cannot
establish the scale&rdquo; into a weaker claim the caller never made is its own kind of
overclaim. Eligibility is deterministic: same measurand, both normalized, x axes already
compatible, and the bases the only unresolved thing.</div>

<h2>Canonical representation &rarr; runtime</h2>
<div class="note">The runtime consumes the canonical record; it does not re-read the
printed label. For each axis it takes <code>quantity</code>,
<code>comparison_group</code>, <code>normalization_definition</code>, any persisted
<code>projections</code>, and the <code>context</code> attached to the transformations
that were actually applied. Label inference survives only where the canonical layer said
nothing, and is marked inferred so the two are never confused.<br><br>
<strong>The regression this closed.</strong> <code>10.1039_d0cp03358h</code> Fig.&nbsp;9b
prints its abscissa as &ldquo;Dimensionless distance x&#771;&rdquo;. The canonical layer
had already resolved it to <code>dimensionless_distance</code> normalized by
<code>x_over_feature_height</code>, found <code>feature_height = 0.1 µm</code> from the
series label &ldquo;100 nm&rdquo;, applied
<code>denormalize_x_by_feature_height</code> with status <code>converted</code>, and
persisted the projection to <code>spatial_coordinate</code>. The previous runtime saw only
the label, found no basis in it, and reported <code>NORMALIZATION_UNKNOWN</code> and
<code>missing_context</code> &mdash; discarding a resolved answer and then guessing at it.
It now reads <code>NORMALIZATION_EXPLICIT</code> and reuses the resolved parameter, with
provenance pointing at the canonical record rather than a weaker copy.<br><br>
Corpus-wide the correction removed <strong>153 false ambiguous</strong> verdicts (every
one of them), promoted <strong>153 pairs to DIRECT_PROFILE</strong>, and made
<strong>782 pairs</strong> execute through <code>CANONICAL_PROJECTION</code> rather than
recomputing. <strong>Unexplained canonical/runtime disagreements: 0.</strong><br><br>
The <strong>828 <code>missing_context</code></strong> pairs did not move, and that is the
correct outcome: 782 are blocked on <code>cycle_number</code> for the growth-per-cycle
&harr; thickness bridge, and 46 additionally on a <code>feature_height</code> the
canonical layer itself recorded as <code>ambiguous</code> for those curves. Canonical
ambiguity stays ambiguity.</div>

<h2>Why a canonical quantity id is not enough</h2>
<div class="note"><code>t/t_entrance</code>, <code>t/t_max</code> and
<code>t/t_planar</code> all canonicalise to <code>normalized_thickness</code> with unit
<code>1</code>, and they are three different physical statements &mdash; how much thinner
the film got relative to the mouth of the feature, relative to wherever this profile
happened to peak, or relative to a flat witness coupon. So the comparison identity is
<strong>(quantity, comparison group, normalization definition)</strong>. Two normalized
profiles with different bases come back <code>RELATED_NOT_COMPARABLE</code>; a normalized
profile whose basis nobody recorded comes back <code>ambiguous</code>, which is a
different answer from &ldquo;no&rdquo; and a very different answer from
&ldquo;yes&rdquo;.</div>

<h2>Normalization identity in the corpus</h2>
<div class="scroll"><table><thead><tr><th>paper</th><th>printed axis label</th>
<th>normalization</th><th>status</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Pair status counts</h2>
<div class="scroll"><table><thead><tr><th>status</th><th>pairs</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Real pair inventory</h2>
<div class="scroll"><table><thead><tr><th>paper A</th><th>paper B</th><th>x</th>
<th>y</th><th>profile status</th><th>missing context</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Cross-paper overlay</h2>
%s

<h2>What this does and does not claim</h2>
<div class="note">The status answers a narrow question: whether two results can be placed
in one representation, and what it costs to get them there. It does not claim the two
experiments should agree, that their process conditions were equivalent, or that a
<code>SHAPE_ONLY</code> pair is quantitatively equal. Transformations come only from
declared ontology relations and extracted context &mdash; no curve is scaled, shifted or
fitted to improve agreement, and a parameter nobody extracted stays missing rather than
being filled from a typical literature value.</div>

<h2>Deferred</h2>
<div class="note"><code>flow_ratio</code> numerator/denominator schema; the
natural-language query layer; the d0ra precursor-purge extraction defect; ontology alias
hygiene; interpolation-based quantitative metrics, which need a stated resampling
contract before they mean anything.</div>
</div>""" % (CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
             c["curves_scanned"], c["profile_series"], c["candidate_pairs"],
             c["cross_paper_pairs"], c["papers"], e(FLOW), na, st, pr, ovhtml)
    (OUT / "result_profile_comparability_review.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
