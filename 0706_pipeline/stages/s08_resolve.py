"""
s08_resolve.py  (Phase B2)  — no LLM
------------------------------------
Turn raw per-series extractions (s07) into correctly-grained, ontology-normalised
experiment records.

Granularity is decided from the PLOT AXIS LABELS (ground truth), not the LLM's
role guesses: the x-axis label IS the independent variable.
  - x-axis canonicalises to a COORDINATE  -> ONE profile experiment (varies x),
    the y-curve is its data; any condition among s07's variables stays controlled.
  - x-axis canonicalises to a CONDITION    -> SPLIT each data point into its own
    experiment (series_varies x); y-label is the measured dependent.
  - x-axis unknown -> fall back to s07 roles.

Also: ontology normalisation + SI units, unit-variant reconciliation (same_as),
material inheritance (series name / profile), and relevance tagging
(experimental / model / background).

Output: output/<pid>/resolved/experiments.json  and  series.json
"""
import json
import re
from collections import Counter
from lib import (papers, OUTPUT, canon_material, canon_structure, canon_precursor,
                 canon_coreactant, canon_quantity, resolve_axis_label, axis_role, QK_META)

LEN = {"nm": 1, "å": .1, "angstrom": .1, "um": 1e3, "µm": 1e3, "μm": 1e3, "mm": 1e6, "cm": 1e7, "m": 1e9}
PRE = {"pa": 1, "kpa": 1e3, "torr": 133.322, "mtorr": .133322, "bar": 1e5, "mbar": 1e2, "atm": 101325}
TIM = {"s": 1, "ms": 1e-3, "min": 60, "h": 3600}
# QUDT unit tokens (fed to the LLM via the ontology) -> readable units the maps understand
QUDT = {"nanom": "nm", "microm": "µm", "millim": "mm", "centim": "cm", "metre": "m",
        "angstrom": "å", "sec": "s", "milli-s": "ms", "deg_c": "°c", "k": "k",
        "gm-per-mol": "g/mol", "unitless": "", "per-m2": "1/m²", "per-m3": "1/m³",
        "m2-per-sec": "m²/s", "pa": "pa", "w": "W", "ev": "eV", "torr": "torr", "num": "",
        "pa-1": "1/Pa", "per-pa": "1/Pa", "pa-per-s": "Pa/s"}
def _f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
def clean_unit(u):
    if not u: return u
    t = str(u); t = t.split("/")[-1] if t.startswith("http") else t
    t = t.replace("unit:", "").strip()
    return QUDT.get(t.lower(), t)
def norm_unit(val, unit):
    cu = clean_unit(unit)                 # readable unit (e.g. 'g/mol', 'nm')
    v = _f(val); u = (cu or "").strip().lower()
    if v is None: return val, cu
    if u in LEN: return v * LEN[u], "nm"
    if u in PRE: return v * PRE[u], "Pa"
    if u in TIM: return v * TIM[u], "s"
    if u in ("k", "kelvin"): return v - 273.15, "°C"
    if u in ("°c", "c", "degc", "deg c", "celsius"): return v, "°C"
    return v, cu
def reconcile(qid):
    return (QK_META.get(qid) or {}).get("same_as") or qid
def normvar(v):
    qid = canon_quantity(v.get("quantity") or v.get("name") or v.get("symbol") or "")
    qid = reconcile(qid) if qid else None
    val, unit = norm_unit(v.get("value"), v.get("unit"))
    out = {"quantity": qid, "raw": v.get("quantity"), "symbol": v.get("symbol"),
           "value": val, "unit": unit}
    if v.get("of_reactant"): out["of_reactant"] = v["of_reactant"]
    return out


MODEL_KW = ("model", "fit", "simulat", "calculat", "gordon", "ylilammi", "theoret",
            "predict", "analytic", "langmuir")
def is_model_series(series_name, base_flag):
    s = (series_name or "").lower()
    if "measur" in s or "experiment" in s:
        return base_flag
    return base_flag or any(k in s for k in MODEL_KW)


def parse_label_conditions(series_name):
    """A series label like '2000 nm' or '500 cycles' deterministically names the
    varied CONDITION (channel height / cycle count). Returns [(qid, value_SI, unit)]."""
    out = []
    for m in re.finditer(r"([\d.]+)\s*(nm|µm|um|μm|cycles?)\b", series_name or "", re.I):
        num, u = float(m.group(1)), m.group(2).lower()
        if u == "nm":
            out.append(("feature_height", num, "nm"))
        elif u in ("µm", "um", "μm"):
            out.append(("feature_height", num * 1000, "nm"))
        elif u.startswith("cycle"):
            out.append(("cycle_number", num, "cycles"))
    return out


def apply_label(ctrl, series_name):
    """Override/repair controlled conditions from the (deterministic) series label,
    dropping values the LLM mis-assigned to the wrong quantity."""
    labels = parse_label_conditions(series_name)
    if not labels:
        return ctrl
    claimed = {round(v, 6) for _, v, _ in labels}
    lqids = {q for q, _, _ in labels}
    # drop items holding a label value under the WRONG quantity (the mis-assignment)
    ctrl = [c for c in ctrl if not (c.get("value") is not None and
            round(float(c["value"]), 6) in claimed and c.get("quantity") not in lqids)]
    for q, v, u in labels:
        ctrl = [c for c in ctrl if c.get("quantity") != q]      # replace existing
        ctrl.append({"quantity": q, "value": v, "unit": u, "from_label": True})
    return ctrl


def derive_quantities(controlled):
    """Compute quantities from the ontology's defined_by equations when all inputs
    are present (C3 enrichment): exposure = P*t, growth_rate = GPC/cycle_time."""
    idx = {c["quantity"]: c["value"] for c in controlled
           if c.get("quantity") and c.get("value") is not None}
    have = {c["quantity"] for c in controlled if c.get("quantity")}
    out = []
    if {"partial_pressure", "pulse_time"} <= set(idx) and "exposure" not in have:
        out.append({"quantity": "exposure", "value": idx["partial_pressure"] * idx["pulse_time"],
                    "unit": "Pa·s", "derived": "partial_pressure*pulse_time"})
    if {"growth_per_cycle", "cycle_time"} <= set(idx) and "growth_rate" not in have:
        out.append({"quantity": "growth_rate", "value": idx["growth_per_cycle"] / idx["cycle_time"],
                    "unit": "nm/s", "derived": "growth_per_cycle/cycle_time"})
    return out


def load_plot(plot_path, series_name):
    """-> (points, x_label, y_label) for the series (axis labels = ground truth)."""
    try:
        pj = json.loads(open(plot_path).read())
    except Exception:
        return [], None, None
    panels = pj if isinstance(pj, list) else [pj]
    for pan in panels:
        meta = pan.get("metadata", {})
        for d in pan.get("data", []):
            if str(d.get("series", "")).strip() == str(series_name).strip():
                return d.get("points", []), meta.get("x_label"), meta.get("y_label")
    m0 = panels[0].get("metadata", {}) if panels else {}
    return [], m0.get("x_label"), m0.get("y_label")


def resolve(e, profile):
    v = e.get("variables", {}) or {}
    s07_ctrl = apply_label([normvar(x) for x in v.get("controlled", []) if x], e.get("series_name"))
    s07_indep = [normvar(x) for x in v.get("independent", []) if x]
    # any condition the LLM parked in "independent" is really a controlled label
    indep_conds = [x for x in s07_indep if x["quantity"] and axis_role(x["quantity"]) == "condition"]

    series_name = e.get("series_name")
    plot_path = (e.get("provenance") or {}).get("plot_data_path")
    points, x_label, y_label = load_plot(plot_path, series_name)
    x_qid = resolve_axis_label(x_label)
    x_qid = reconcile(x_qid) if x_qid else None
    y_qid = resolve_axis_label(y_label)
    y_qid = reconcile(y_qid) if y_qid else None
    xrole = axis_role(x_qid) if x_qid else None
    # log/transformed axes carry ln(quantity), not the quantity -> don't split per point
    x_is_log = bool(re.search(r"\b(ln|log10|log)\b", str(x_label or ""), re.I))

    # ---- material inheritance + relevance -----------------------------------
    studied = set(profile.get("studied_materials_canonical", []))
    prof_mats = [canon_material(m) for m in (profile.get("materials_deposited") or []) if canon_material(m)]
    primary = prof_mats[0] if prof_mats else (next(iter(studied)) if len(studied) == 1 else None)
    # inherit the paper's primary film when a series doesn't name its own material
    mat = (canon_material(e.get("material_deposited") or "") or canon_material(series_name or "")
           or primary)
    is_model = is_model_series(series_name, bool(e.get("is_model_result")))
    if mat and studied and mat not in studied:
        relevance = "background"        # material explicitly OUTSIDE the studied set (intro noise)
    elif is_model:
        relevance = "model"
    else:
        relevance = "experimental"

    base = {
        "series_name": series_name, "material": mat, "material_raw": e.get("material_deposited"),
        "relevance": relevance, "structure": canon_structure(e.get("structure_type") or ""),
        "process_type": e.get("process_type"),
        "precursors": [canon_precursor(p) or p for p in e.get("precursors", []) or []],
        "coreactants": [canon_coreactant(c) or c for c in e.get("coreactants", []) or []],
        "is_model_result": is_model, "x_label": x_label, "y_label": y_label,
        "provenance": e.get("provenance", {}),
    }
    dep = [{"quantity": y_qid, "raw": y_label, "unit": None}] if y_qid else [normvar(x) for x in v.get("dependent", []) if x]

    if xrole == "coordinate":                    # PROFILE (authoritative)
        exp = dict(base, granularity="profile", varies=[x_qid],
                   controlled=s07_ctrl + indep_conds, dependent=dep, points=points)
        return [exp], ([c["quantity"] for c in indep_conds] or None)
    elif xrole == "condition" and x_is_log:      # log/transformed axis -> keep as one record
        return [dict(base, granularity="single", varies=[x_qid],
                     controlled=s07_ctrl + indep_conds, dependent=dep, points=points)], None
    elif xrole == "condition":                   # CONDITION SWEEP -> split per point
        out = []
        for i, pt in enumerate(points):
            x = pt[0] if isinstance(pt, (list, tuple)) and pt else None
            y = pt[1] if isinstance(pt, (list, tuple)) and len(pt) > 1 else None
            xv, xu = norm_unit(x, None)
            out.append(dict(base, granularity="sweep_point", point_index=i, varies=[],
                            controlled=s07_ctrl + [{"quantity": x_qid, "value": xv, "unit": xu}],
                            dependent=[dict(d, value=y) for d in dep]))
        if not points:
            out = [dict(base, granularity="sweep_nopoints", varies=[],
                        controlled=s07_ctrl + indep_conds, dependent=dep)]
        return out, x_qid
    else:                                        # unknown x -> single record
        return [dict(base, granularity="single", varies=([x_qid] if x_qid else []),
                     controlled=s07_ctrl + indep_conds, dependent=dep, points=points)], None


def main():
    for p in papers():
        pid = p["pid"]
        exp_dir = OUTPUT / pid / "experiments"
        if not exp_dir.exists():
            print(f"[skip] {pid}: run s07 first"); continue
        profile = json.loads((OUTPUT / pid / "profile.json").read_text())
        resolved, series = [], {}
        for ef in sorted(exp_dir.glob("figure-*.json")):
            for e in json.loads(ef.read_text()):
                exps, sv = resolve(e, profile)
                for x in exps:                       # C3: derived quantities (exposure=P*t, ...)
                    x["controlled"] = (x.get("controlled") or []) + derive_quantities(x.get("controlled") or [])
                svq = (sv[0] if isinstance(sv, list) else sv) if sv else None
                if svq:
                    key = f"{ef.stem}::{svq}"
                    series.setdefault(key, {"figure": ef.stem, "series_varies": svq, "members": 0})
                    series[key]["members"] += len(exps)
                    for x in exps:
                        x["in_series"] = key
                resolved.extend(exps)
        out_dir = OUTPUT / pid / "resolved"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "experiments.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False))
        (out_dir / "series.json").write_text(json.dumps(series, indent=2, ensure_ascii=False))
        g = Counter(x["granularity"] for x in resolved)
        r = Counter(x["relevance"] for x in resolved)
        print(f"[{pid}] {len(resolved)} exps  granularity={dict(g)}  relevance={dict(r)}  series={len(series)}")


if __name__ == "__main__":
    main()
