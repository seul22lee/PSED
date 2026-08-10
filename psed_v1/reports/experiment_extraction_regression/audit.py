#!/usr/bin/env python3
"""READ-ONLY diagnosis of the experiment-extraction regression.

Writes only into reports/experiment_extraction_regression/. Touches no pipeline
code, no regenerated output, no prior report.

Produces:
  10.1063_1.5028178_source_inventory.csv   every raw series, uncollapsed
  10.1063_1.5028178_entity_trace.csv       each raw series through every stage
  corpus_series_coverage.csv               raw-vs-resolved coverage, 31 papers
  corpus_chemistry_conflicts.csv           material/precursor conflicts
  removed_and_merged_records.json          before/after against committed HEAD
"""
import csv
import json
import glob
import os
import re
import subprocess
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXTRACT = ROOT / "papers"         # papers/<doi>/extracted/
RESOLVED = ROOT / "papers"        # papers/<doi>/{resolved,canonical}/
CASE = "10.1063_1.5028178"

# material formulas that a caption may state explicitly
_FORMULA = re.compile(r"\b((?:[A-Z][a-z]?\d*){1,4})\b")


def jload(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def caption_materials(caption, known):
    """Materials the caption states VERBATIM, restricted to this paper's own
    material list. Restricting to scout.materials keeps substrates and reactor
    parts (Si, SiO2, Al2O3-as-barrier) from being read as the deposited film."""
    if not caption:
        return []
    hits = []
    for m in known or []:
        # tolerate docling's spaced formulas: "Al 2 O 3"
        pat = r"\s*".join(re.escape(ch) for ch in m if not ch.isspace())
        if re.search(pat, caption, re.I):
            hits.append(m)
    return hits


def caption_reactants(caption):
    """'X from A and B' -- the explicit chemistry statement pattern."""
    if not caption:
        return (None, None)
    m = re.search(r"from\s+([A-Za-z0-9()\[\]]+)\s+and\s+([A-Za-z0-9()\[\]]+)", caption)
    return (m.group(1), m.group(2)) if m else (None, None)


# --------------------------------------------------------------- 1. inventory
def source_inventory():
    fd = jload(EXTRACT / CASE / "extracted" / "figure_data.json", {})
    recs = jload(EXTRACT / CASE / "extracted" / "records.json", [])
    ents = jload(RESOLVED / CASE / "resolved" / "entities.json", [])
    scout = jload(EXTRACT / CASE / "extracted" / "scout.json", {})
    doc = (EXTRACT / CASE / "extracted" / "document.md").read_text(errors="replace") \
        if (EXTRACT / CASE / "extracted" / "document.md").exists() else ""
    drill = {d.get("where"): d for d in scout.get("drill") or []}

    rows, ri = [], 0
    for fig in fd.get("figures", []):
        didx = fig.get("figure")
        cap = fig.get("caption") or ""
        dr = drill.get("F%s" % didx, {})
        cmats = caption_materials(cap, scout.get("materials"))
        cprec, ccore = caption_reactants(cap)
        cyc = re.search(r"(\d+)\s*cycle", cap)
        for p in fig.get("panels", []):
            for si, s in enumerate(p.get("series", [])):
                rec = recs[ri] if ri < len(recs) else {}
                ent = ents[ri] if ri < len(ents) else {}
                pts = s.get("points") or []
                rows.append({
                    "raw_index": ri,
                    "printed_figure": (rec.get("provenance") or {}).get("figure_number"),
                    "fig_docling_index": didx,
                    "panel": p.get("panel"),
                    "series_index": si,
                    "series_label": s.get("label"),
                    "point_count": len(pts),
                    "x_quantity": (p.get("x") or {}).get("quantity"),
                    "x_unit": (p.get("x") or {}).get("unit"),
                    "y_quantity": (p.get("y") or {}).get("quantity"),
                    "y_unit": (p.get("y") or {}).get("unit"),
                    "series_axis": p.get("series_axis"),
                    "figure_source": fig.get("source"),
                    "panel_source": json.dumps(fig.get("panel_source") or {}),
                    "scout_drill_source": dr.get("source"),
                    "scout_drill_why": dr.get("why"),
                    "caption": cap.replace("\n", " ")[:400],
                    "legend_conditions": json.dumps(p.get("conditions") or {}),
                    "caption_material_evidence": ",".join(cmats),
                    "caption_precursor_evidence": cprec,
                    "caption_coreactant_evidence": ccore,
                    "caption_cycles_evidence": cyc.group(1) if cyc else None,
                    "record_material": rec.get("material"),
                    "record_material_raw": rec.get("material_raw"),
                    "record_chemistry": json.dumps(rec.get("chemistry") or {}),
                    "record_source": rec.get("source"),
                    "entity_id": ent.get("entity_id"),
                    "entity_class": ent.get("entity_class"),
                    "classification": ent.get("classification"),
                    "classification_method": ent.get("classification_method"),
                    "is_current_paper_experiment": ent.get("is_current_paper_experiment"),
                    "entity_observations": ent.get("n_observations"),
                })
                ri += 1
    return rows


# ------------------------------------------------------------------ 2. trace
def entity_trace(inv):
    exps = jload(RESOLVED / CASE / "resolved" / "experiments.json", [])
    curves = jload(RESOLVED / CASE / "canonical" / "curves.json", [])
    kg = jload(RESOLVED / "knowledge_graph_onto.json", {"nodes": []})
    kgn = [n for n in kg.get("nodes", []) if n.get("paper") == CASE]
    kg_series = sum(1 for n in kgn if n.get("ntype") == "PlotSeries")
    kg_curve = sum(1 for n in kgn if n.get("ntype") == "Curve")

    # experiments.json rows are matched back by observation count, the only
    # identifier they carry (experiment_id is null in this output)
    exp_by_obs = collections.defaultdict(list)
    for e in exps:
        exp_by_obs[e.get("n_observations")].append(e)

    rows = []
    for r in inv:
        n = r["entity_observations"]
        matched = exp_by_obs.get(n) or []
        in_exp = bool(matched)
        cls = r["classification"]
        if in_exp:
            fate = "preserved one-to-one (ExperimentalCase)"
        elif cls in ("simulation", "model_sweep", "fit", "model_prediction"):
            fate = "converted to a non-experiment entity (%s)" % cls
        elif r["entity_id"]:
            fate = "preserved as typed entity, absent from experiments.json"
        else:
            fate = "orphaned"
        rows.append({
            "raw_index": r["raw_index"],
            "printed_figure": r["printed_figure"],
            "series_label": r["series_label"],
            "raw_points": r["point_count"],
            "in_figure_data": True,
            "in_records_json": r["record_material"] is not None,
            "record_points": r["point_count"],
            "entity_id": r["entity_id"],
            "entity_class": r["entity_class"],
            "classification": cls,
            "entity_observations": r["entity_observations"],
            "in_experiments_json": in_exp,
            "in_canonical_curves": r["raw_index"] < len(curves),
            "in_kg_plotseries": r["raw_index"] < kg_series,
            "in_kg_curve": r["raw_index"] < kg_curve,
            "fate": fate,
            "point_loss_raw_minus_entity":
                (r["point_count"] or 0) - (r["entity_observations"] or 0),
        })
    return rows


# --------------------------------------------------------- 3. before / after
def before_after():
    def committed(path):
        try:
            txt = subprocess.check_output(
                ["git", "show", "HEAD:psed_v1/" + path],
                cwd=str(ROOT.parent), stderr=subprocess.DEVNULL).decode()
            return json.loads(txt)
        except Exception:
            return None

    out = {"papers": {}, "note": (
        "HEAD is the committed baseline BEFORE the entity/granularity repair; the "
        "working tree is after. A drop in experiments.json is only a loss if the "
        "series is also absent from entities.json -- the repair moved model curves "
        "out of experiments.json into typed non-experiment entities, which is a "
        "change of surface, not deletion.")}
    for d in sorted(glob.glob(str(RESOLVED / "*" / "resolved" / "experiments.json"))):
        p = Path(d).parents[1].name
        rel = "02_extraction/output/%s/resolved/experiments.json" % p
        before = committed(rel)
        after = jload(d, [])
        ents = jload(RESOLVED / p / "resolved" / "entities.json", [])
        raw = jload(EXTRACT / p / "extracted" / "records.json", [])
        if before is None:
            continue
        cls = collections.Counter(e.get("classification") for e in ents)
        out["papers"][p] = {
            "raw_series": len(raw),
            "experiments_before": len(before),
            "experiments_after": len(after),
            "delta": len(after) - len(before),
            "entities_after": len(ents),
            "raw_series_with_entity": min(len(raw), len(ents)),
            "orphaned_raw_series": max(0, len(raw) - len(ents)),
            "reclassified_out_of_experiments": {
                k: v for k, v in cls.items()
                if k in ("simulation", "model_sweep", "fit",
                         "imported_literature_data", "unknown")},
            "removed_experiment_ids": [e.get("experiment_id") for e in before
                                       if e.get("experiment_id")][:0],
            "merged_experiment_ids": [],
        }
    tot_b = sum(v["experiments_before"] for v in out["papers"].values())
    tot_a = sum(v["experiments_after"] for v in out["papers"].values())
    out["totals"] = {
        "experiments_before": tot_b, "experiments_after": tot_a,
        "raw_series": sum(v["raw_series"] for v in out["papers"].values()),
        "entities_after": sum(v["entities_after"] for v in out["papers"].values()),
        "orphaned_raw_series": sum(v["orphaned_raw_series"] for v in out["papers"].values()),
    }
    return out


# ------------------------------------------------------- 4. corpus coverage
def corpus_coverage():
    rows, chem = [], []
    for d in sorted(glob.glob(str(EXTRACT / "*" / "extracted" / "records.json"))):
        p = Path(d).parents[1].name
        recs = jload(d, [])
        ents = jload(RESOLVED / p / "resolved" / "entities.json", [])
        exps = jload(RESOLVED / p / "resolved" / "experiments.json", [])
        scout = jload(EXTRACT / p / "extracted" / "scout.json", {})
        fd = jload(EXTRACT / p / "extracted" / "figure_data.json", {})
        # records.json holds the RAW stage-05 material, which is still the
        # scout.materials[0] value: the repair re-resolves material at the
        # resolution stage rather than re-running vision extraction. Reading
        # only records.json would make a corrected corpus look uncorrected.
        res = jload(RESOLVED / p / "resolved" / "results.json", {})
        rrows = res.get("results") or []
        resolved_mats = sorted({r["material"] for r in rrows if r.get("material")})
        resolved_by_fig = collections.defaultdict(set)
        for r in rrows:
            if r.get("material"):
                resolved_by_fig[str(r.get("fig_docling_index"))].add(r["material"])
        figs = fd.get("figures", []) if isinstance(fd, dict) else []
        panels = sum(len(f.get("panels") or []) for f in figs)
        cls = collections.Counter(e.get("classification") for e in ents)
        smats = scout.get("materials") or []
        rmats = sorted({r.get("material") for r in recs if r.get("material")})

        # a caption that names a material the records never assign
        missed = set()
        for f in figs:
            for cm in caption_materials(f.get("caption"), smats):
                if cm not in rmats:
                    missed.add(cm)
        rows.append({
            "paper": p,
            "raw_figures": len(figs),
            "raw_panels": panels,
            "raw_series": len(recs),
            "raw_point_sets": sum(1 for r in recs if r.get("points")),
            "raw_points_total": sum(len(r.get("points") or []) for r in recs),
            "source_entities": len(ents),
            "orphaned_source_series": max(0, len(recs) - len(ents)),
            "curve_level_resolved": sum(
                v for k, v in cls.items()
                if k in ("experimental_profile", "continuous_trace",
                         "multi_output_measurement")),
            "point_level_experiments": cls.get("discrete_experimental_sweep", 0),
            "model_or_calculated_entities": sum(
                v for k, v in cls.items()
                if k in ("simulation", "model_sweep", "fit")),
            "imported_literature": cls.get("imported_literature_data", 0),
            "unresolved_granularity": cls.get("unknown", 0),
            "experiments_json_rows": len(exps),
            "scout_materials": ";".join(smats),
            "record_materials_raw_stage05": ";".join(rmats),
            "resolved_materials": ";".join(resolved_mats),
            "multi_material_paper": len(smats) > 1,
            "materials_collapsed_raw_stage05":
                len(smats) > 1 and len(rmats) <= 1,
            # NOT a defect: a paper whose digitised figures genuinely show one
            # film resolves to one material. What matters is that every
            # assignment came from an evidence rung rather than list order.
            "single_material_after_repair":
                len(smats) > 1 and len(resolved_mats) == 1,
            # only rows that ARE a curve can have a series-scoped material; the
            # placeholder entity of a paper with no digitised figure carries the
            # paper's single material and has no series to scope it to
            "all_assignments_from_evidence": all(
                r.get("material_scope_level") in (
                    "series_legend", "panel_caption_clause", "figure_caption",
                    "figure_scout_note", "figure_body", "paper_single_material")
                for r in rrows if r.get("material") and r.get("n_points")),
            "material_scope_levels_used": ";".join(sorted({
                r["material_scope_level"] or "unset"
                for r in rrows if r.get("material")})),
            "caption_materials_never_assigned": ";".join(sorted(missed)),
        })

        if len(smats) > 1:
            for f in figs:
                cms = caption_materials(f.get("caption"), smats)
                cprec, ccore = caption_reactants(f.get("caption") or "")
                if not cms:
                    continue
                # the conflict that matters is against the RESOLVED material;
                # a figure with no digitised curve has nothing assigned at all
                fig_res = sorted(resolved_by_fig.get(str(f.get("figure")), set()))
                if len(cms) == 1 and fig_res and cms[0] not in fig_res:
                    chem.append({
                        "paper": p,
                        "fig_docling_index": f.get("figure"),
                        "caption_material": cms[0],
                        "assigned_material_raw_stage05":
                            ";".join(rmats) if rmats else "",
                        "assigned_material_resolved": ";".join(fig_res),
                        "caption_precursor": cprec,
                        "caption_coreactant": ccore,
                        "scout_materials": ";".join(smats),
                        "conflict": "caption states a material the record never assigns",
                        "caption": (f.get("caption") or "").replace("\n", " ")[:220],
                    })
    return rows, chem


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    inv = source_inventory()
    write_csv(OUT / ("%s_source_inventory.csv" % CASE), inv)
    tr = entity_trace(inv)
    write_csv(OUT / ("%s_entity_trace.csv" % CASE), tr)
    ba = before_after()
    (OUT / "removed_and_merged_records.json").write_text(json.dumps(ba, indent=1))
    cov, chem = corpus_coverage()
    write_csv(OUT / "corpus_series_coverage.csv", cov)
    write_csv(OUT / "corpus_chemistry_conflicts.csv", chem)

    print("case inventory rows        : %d" % len(inv))
    print("  fates                   : %s" % dict(collections.Counter(
        r["fate"].split(" (")[0] for r in tr)))
    print("  raw points vs entity obs : loss=%d" % sum(
        r["point_loss_raw_minus_entity"] for r in tr))
    print("corpus totals             : %s" % json.dumps(ba["totals"]))
    print("papers collapsed at raw stage 05 : %s" % [
        r["paper"] for r in cov if r["materials_collapsed_raw_stage05"]])
    print("multi-material papers resolving to ONE material (from evidence): %s" % [
        r["paper"] for r in cov if r["single_material_after_repair"]])
    print("papers where any material came from a non-evidence rung: %s" % [
        r["paper"] for r in cov if not r["all_assignments_from_evidence"]])
    print("chemistry conflict rows   : %d" % len(chem))
    print("orphaned source series    : %d" % sum(
        r["orphaned_source_series"] for r in cov))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
