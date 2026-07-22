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
import sys
from pathlib import Path
from collections import Counter
from lib import (papers, OUTPUT, canon_material, canon_structure, canon_precursor,
                 canon_coreactant, canon_quantity, resolve_axis_label, axis_role, QK_META,
                 family, TRANSFORMS, species_prop)
sys.path.insert(0, str(Path(__file__).parent.parent))
import recipe as recipe_mod  # noqa: E402  (Recipe: 1 per experiment)
from caption_params import parse as parse_caption, REACTANT_QUANTITIES
import methods_recipe

LEN = {"nm": 1, "å": .1, "angstrom": .1, "um": 1e3, "µm": 1e3, "μm": 1e3, "mm": 1e6, "cm": 1e7, "m": 1e9}
PRE = {"pa": 1, "kpa": 1e3, "torr": 133.322, "mtorr": .133322, "bar": 1e5, "mbar": 1e2, "atm": 101325}
TIM = {"s": 1, "ms": 1e-3, "min": 60, "h": 3600}
# QUDT unit tokens (fed to the LLM via the ontology) -> readable units the maps understand
QUDT = {"nanom": "nm", "microm": "µm", "millim": "mm", "centim": "cm", "metre": "m",
        "angstrom": "å", "sec": "s", "milli-s": "ms", "deg_c": "°c", "k": "k",
        "gm-per-mol": "g/mol", "unitless": "", "per-m2": "1/m²", "per-m3": "1/m³",
        "m2-per-sec": "m²/s", "pa": "pa", "w": "W", "ev": "eV", "torr": "torr", "num": "",
        "pa-1": "1/Pa", "per-pa": "1/Pa", "pa-per-s": "Pa/s"}
QUDT.update({"percent": "%", "celsius": "°C", "degreecelsius": "°C"})
# dimensionless quantities: report unit "1" (not None) so overlays/compares are honest
DIMLESS = {"normalized_thickness", "surface_coverage", "maximum_surface_coverage",
           "channel_filling_fraction", "reaction_probability", "recombination_probability",
           "aspect_ratio", "step_coverage", "conformality", "saturation_ratio",
           "dimensionless_distance", "sticking_probability"}
# canonical display form for readable unit tokens (case/spelling)
UNIT_CANON = {"pa": "Pa", "°c": "°C", "c": "°C", "nm": "nm", "µm": "µm", "um": "µm",
              "μm": "µm", "s": "s", "sec": "s", "cycles": "cycles", "cycle": "cycles",
              "g/mol": "g/mol", "%": "%", "1/pa": "1/Pa", "1/m²": "1/m²", "1/m2": "1/m²",
              "pa·s": "Pa·s", "nm/cycle": "nm/cycle", "nm/s": "nm/s"}
# physical dimension per quantity (SI base exponents, symbolic). Enables
# same-dimension comparability + value<->value/area bridging. L length, M mass,
# T time, Θ temperature, N amount; "1" dimensionless.
DIM = {
    "film_thickness": "L", "penetration_depth": "L", "feature_height": "L",
    "feature_width": "L", "feature_length": "L", "pore_diameter": "L",
    "precursor_molecular_diameter": "L", "spatial_coordinate": "L", "growth_per_cycle": "L",
    "normalized_thickness": "1", "surface_coverage": "1", "maximum_surface_coverage": "1",
    "reaction_probability": "1", "recombination_probability": "1", "aspect_ratio": "1",
    "channel_filling_fraction": "1", "step_coverage": "1", "dimensionless_distance": "1",
    "cycle_number": "1", "sticking_probability": "1",
    "partial_pressure": "M L^-1 T^-2", "reactant_A_partial_pressure": "M L^-1 T^-2",
    "reactant_B_partial_pressure": "M L^-1 T^-2",
    "pulse_time": "T", "purge_time": "T", "plasma_exposure_time": "T",
    "cycle_time": "T", "process_time": "T",
    "temperature": "Θ", "deposition_temperature": "Θ",
    "molecular_mass": "M N^-1", "exposure": "M L^-1 T^-1",
    "site_density": "L^-2", "saturated_coverage": "L^-2", "collision_flux": "L^-2 T^-1",
    "adsorption_site_area": "L^2", "adsorption_rate_constant": "M^-1 L T^2",
}
def _f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
def clean_unit(u):
    if not u: return u
    t = str(u); t = t.split("/")[-1] if t.startswith("http") else t
    t = t.replace("unit:", "").strip()
    return QUDT.get(t.lower(), t)
def pretty_unit(u):
    """normalise a readable unit token to canonical display form (pa->Pa, °c->°C)."""
    if u is None: return None
    t = str(u).strip()
    return UNIT_CANON.get(t.lower(), t) if t else t
def canon_unit(qid):
    """ontology canonical unit for a quantity, cleaned to readable form."""
    return pretty_unit(clean_unit((QK_META.get(qid) or {}).get("unit"))) if qid else None
def unit_from_label(label):
    """parse a trailing '(unit)' off an axis label, e.g. 'Pressure p_A (Pa)' -> 'Pa'."""
    if not label: return None
    m = re.search(r"\(([^)]{1,8})\)\s*$", str(label))
    if m and re.match(r"^[a-zµμ°%/·0-9.\-^ ]+$", m.group(1).strip(), re.I):
        return pretty_unit(m.group(1).strip())
    return None
def resolve_unit(qid, given, label=None):
    """unit priority: given > axis-label parenthetical > ontology canonical > '1' if dimensionless."""
    g = pretty_unit(clean_unit(given))
    if g: return g
    lab = unit_from_label(label)
    if lab: return lab
    if qid in DIMLESS: return "1"
    return canon_unit(qid)
def norm_unit(val, unit):
    cu = clean_unit(unit)                 # readable unit (e.g. 'g/mol', 'nm')
    v = _f(val); u = (cu or "").strip().lower()
    if v is None: return val, pretty_unit(cu)
    if u in LEN: return v * LEN[u], "nm"
    if u in PRE: return v * PRE[u], "Pa"
    if u in TIM: return v * TIM[u], "s"
    if u in ("k", "kelvin"): return v - 273.15, "°C"
    if u in ("°c", "c", "degc", "deg c", "celsius"): return v, "°C"
    return v, pretty_unit(cu)
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
            # the swept quantity is this point's coordinate value — drop any shared
            # copy of it from s07_ctrl so it isn't both varied and "fixed".
            keep = [c for c in s07_ctrl if c.get("quantity") != x_qid]
            out.append(dict(base, granularity="sweep_point", point_index=i, varies=[],
                            controlled=keep + [{"quantity": x_qid, "value": xv, "unit": xu}],
                            dependent=[dict(d, value=y) for d in dep]))
        if not points:
            out = [dict(base, granularity="sweep_nopoints", varies=[],
                        controlled=s07_ctrl + indep_conds, dependent=dep)]
        return out, x_qid
    else:                                        # unknown x -> single record
        return [dict(base, granularity="single", varies=([x_qid] if x_qid else []),
                     controlled=s07_ctrl + indep_conds, dependent=dep, points=points)], None


def finalize(exp):
    """Backfill units, then set the explicit role model + comparability layer (P2):
      measurand  = primary measured y-quantity (was property_of_interest)
      coordinate = independent x-quantity      (was independent_var)
    Each carries its family (measurand_family/coordinate_family). The
    comparability_key groups on FAMILIES (loose: are these about the same things?);
    comparability_signature keeps EXACT quantities (strict: Tier-0/1). `bridges`
    lists, per relevant transform, whether the bridge quantity is present in this
    record (present -> Tier-2 aligned; absent -> Tier-3 latent)."""
    yl = exp.get("y_label")
    dep0 = next((d for d in (exp.get("dependent") or []) if d.get("quantity")), None)
    ctrl = exp.get("controlled") or []
    # S3: profile-derived reference_thickness (thickness at the feature MOUTH = value
    # at min-x) for absolute film_thickness profiles -> supplies the
    # film_thickness->normalized_thickness bridge so they align to canonical (Tier-2).
    if dep0 and dep0.get("quantity") == "film_thickness" and exp.get("points") \
       and not any(c.get("quantity") == "reference_thickness" for c in ctrl):
        pts = sorted([p for p in exp["points"] if p and p[0] is not None and p[1] is not None])
        if len(pts) >= 3 and isinstance(pts[0][1], (int, float)) and pts[0][1] > 0:
            ctrl.append({"quantity": "reference_thickness", "value": round(pts[0][1], 4),
                         "unit": "nm", "derived": "profile_mouth"})
            exp["controlled"] = ctrl
    ctrl_qs = {c.get("quantity") for c in ctrl if c.get("quantity")}
    for d in exp.get("dependent") or []:
        d["unit"] = resolve_unit(d.get("quantity"), d.get("unit"), yl)
        d["dimension"] = DIM.get(d.get("quantity"))
        d["family"] = family(d.get("quantity"))
    for c in ctrl:
        c["unit"] = resolve_unit(c.get("quantity"), c.get("unit"))
    meas = dep0
    measq = meas["quantity"] if meas else None
    if meas:
        exp["measurand"] = {"quantity": measq, "unit": meas.get("unit"),
                            "dimension": DIM.get(measq), "family": family(measq)}
    coord = (exp.get("varies") or [None])[0]
    if not coord and exp.get("in_series"):
        coord = exp["in_series"].split("::")[-1]
    exp["coordinate"] = coord
    exp["coordinate_family"] = family(coord)
    exp["measurand_family"] = family(measq)
    exp["comparability_key"] = f"{exp['coordinate_family'] or '·'} ~ {exp['measurand_family'] or '·'}"
    exp["comparability_signature"] = f"{coord or '·'} ~ {measq or '·'}"     # exact (Tier-0/1)
    ends = {coord, measq}
    exp["bridges"] = [
        {"transform": f"{t['from']}→{t['to']}", "family": t.get("family"),
         "bridge": t["bridge"], "present": t["bridge"] in ctrl_qs}
        for t in TRANSFORMS if (t.get("from") in ends or t.get("to") in ends)]
    # S1: quality gate — analysis_ready + issues (deterministic, from the record)
    pts_all = exp.get("points") or []
    xs = [p[0] for p in pts_all if p and p[0] is not None]
    ys = [p[1] for p in pts_all if p and p[1] is not None]
    has_depval = any(d.get("value") is not None for d in (exp.get("dependent") or []))
    issues = []
    if not exp.get("material"): issues.append("no-material")
    if not measq: issues.append("no-measurand")
    if measq and coord and measq == coord: issues.append("measurand==coordinate")
    if not pts_all and not has_depval and exp.get("granularity") != "sweep_point":
        issues.append("no-data")
    if xs and max(xs) == min(xs): issues.append("degenerate-x")
    if ys and max(ys) == min(ys): issues.append("degenerate-y")
    exp["issues"] = issues
    exp["analysis_ready"] = not issues
    # ---- reactant model (generalises to ABC / ABAC supercycles) ----
    # normalise reactant labels to letters, then dedup (the LLM used 'A_precursor',
    # the caption 'A' — same reactant), then derive reactants[] + cycle_sequence
    # from the labels ACTUALLY present (not the paper-level precursor union).
    remap = {"a_precursor": "A", "b_coreactant": "B", "c_reactant": "C", "d_reactant": "D"}
    for c in exp.get("controlled") or []:
        r = c.get("of_reactant")
        if r:
            c["of_reactant"] = remap.get(str(r).lower().replace(" ", ""), str(r)[:1].upper())
    seen, dd = set(), []
    for c in exp.get("controlled") or []:
        v = round(c["value"], 6) if isinstance(c.get("value"), (int, float)) else c.get("value")
        k = (c.get("quantity"), c.get("of_reactant"), v)
        if k in seen: continue
        seen.add(k); dd.append(c)
    exp["controlled"] = dd
    labs = sorted({c.get("of_reactant") for c in dd if c.get("of_reactant")})
    prec, core = exp.get("precursors") or [], exp.get("coreactants") or []
    reactants = []
    for L in labs:
        role = "precursor" if L == "A" else "coreactant" if L == "B" else "reactant"
        sp = (prec[0] if L == "A" else core[0]) if (len(labs) == 2 and len(prec) == 1 and len(core) == 1) else None
        reactants.append({"label": L, "role": role, **({"species": sp} if sp else {})})
    exp["reactants"] = reactants
    exp["cycle_sequence"] = "".join(labs) or None
    return exp


def metal_of(material):
    m = re.match(r"([A-Z][a-z]?)", material or "")
    return m.group(1) if m else None


def match_precursor(material, precs):
    """Pick the profile precursor for this material: single -> use it; else the one
    whose name contains the material's metal (Al2O3 -> Al(CH3)3, TiO2 -> TiCl4)."""
    if len(precs) == 1:
        return precs[0]
    metal = (metal_of(material) or "").lower()
    for p in precs:
        if metal and metal in str(p).lower():
            return p
    return None


def fig_label(prov):
    """Real figure label from the caption ('Figure 3.'->'3'), + panel letter from the
    internal id ('figure-017a'->'9a' when caption says Fig 9). Used to build exp_id."""
    prov = prov or {}
    cap, fid = prov.get("caption") or "", prov.get("figure_id") or ""
    m = re.match(r"\s*(?:figure|fig)\.?\s*([0-9]+)", cap, re.I)
    num = m.group(1) if m else (re.search(r"(\d+)", fid).group(1) if re.search(r"\d", fid) else "?")
    pm = re.search(r"\d+([a-z])$", fid, re.I)
    return f"{num}{pm.group(1) if pm else ''}"


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

        # ---- FIGURE-LEVEL conditions: shared by every curve in a figure ----
        # (a) deterministic caption parse (the "Parameter values used:" block etc.),
        # (b) cross-curve propagation of any single-valued condition. Both add a
        # quantity only when it is ABSENT from a curve, so a per-curve varied value
        # (e.g. the channel height that differs between curves) always wins.
        byfig = {}
        for x in resolved:
            byfig.setdefault((x.get("provenance") or {}).get("figure_id"), []).append(x)
        for grp in byfig.values():
            def coord_of(x):
                return (x.get("varies") or [None])[0] or (
                    (x.get("in_series") or "").split("::")[-1] if x.get("in_series") else None)
            cap = next(((x.get("provenance") or {}).get("caption") for x in grp
                        if (x.get("provenance") or {}).get("caption")), None)
            for qty, val, unit, react in parse_caption(cap):        # (a) caption params
                for x in grp:
                    ctrl = x.get("controlled") or []; x["controlled"] = ctrl
                    if react and qty in REACTANT_QUANTITIES:
                        # tag an existing untagged copy whose value matches, else add tagged
                        m = next((c for c in ctrl if c.get("quantity") == qty and not c.get("of_reactant")
                                  and isinstance(c.get("value"), (int, float))
                                  and abs(c["value"] - val) <= abs(val) * 0.03 + 1e-9), None)
                        if m:
                            m["of_reactant"] = react
                        elif not any(c.get("quantity") == qty and c.get("of_reactant") == react for c in ctrl):
                            ctrl.append({"quantity": qty, "value": val, "unit": unit,
                                         "of_reactant": react, "from_caption": True})
                    elif not any(c.get("quantity") == qty for c in ctrl):
                        c = {"quantity": qty, "value": val, "unit": unit, "from_caption": True}
                        if react: c["of_reactant"] = react
                        ctrl.append(c)
            info = {}                                               # (b)
            for x in grp:
                for c in x.get("controlled") or []:
                    q, v = c.get("quantity"), c.get("value")
                    if isinstance(v, (int, float)) and q != coord_of(x):
                        d = info.setdefault(q, {"vals": set(), "unit": c.get("unit")})
                        d["vals"].add(round(v, 6))
                        if not d["unit"] and c.get("unit"): d["unit"] = c.get("unit")
            for q, d in info.items():
                if len(d["vals"]) == 1:
                    v = next(iter(d["vals"]))
                    for x in grp:
                        if not any(c.get("quantity") == q for c in x.get("controlled") or []):
                            x["controlled"].append({"quantity": q, "value": v,
                                                    "unit": d["unit"] or "", "propagated": True})

        resolved = [finalize(x) for x in resolved]     # units + role model + comparability
        # fix #2: resolve which precursor/coreactant is reactant A / B from the paper's
        # chemistry. Metal-match on the RAW name (before canonicalisation strips the
        # metal, e.g. Al(CH3)3 -> TMA), then canonicalise the winner.
        raw_pp = profile.get("precursors") or []
        pc = [canon_coreactant(c) or c for c in (profile.get("coreactants") or [])]
        for x in resolved:
            a_raw = match_precursor(x.get("material"), raw_pp)
            a_sp = (canon_precursor(a_raw) or a_raw) if a_raw else None
            b_sp = pc[0] if len(pc) == 1 else None
            if not (a_sp or b_sp):
                continue
            rs = {r["label"]: r for r in (x.get("reactants") or [])}
            rs.setdefault("A", {"label": "A", "role": "precursor"})
            rs.setdefault("B", {"label": "B", "role": "coreactant"})
            if a_sp and not rs["A"].get("species"): rs["A"]["species"] = a_sp
            if b_sp and not rs["B"].get("species"): rs["B"]["species"] = b_sp
            x["reactants"] = [rs[k] for k in sorted(rs)]
            # cycle_sequence follows the CHEMISTRY (the reactants actually present),
            # not which reactant's parameters a given figure happened to tabulate —
            # an AB process is AB even if only B's dose was swept in that panel.
            x["cycle_sequence"] = "".join(sorted(rs))
            # NOTE: molecular_mass/diameter from a MODEL caption (e.g. Ylilammi's
            # MB=28, dB=374) are the transport model's collision partner = the
            # BACKGROUND/CARRIER gas (N2), NOT the ALD coreactant (H2O). They are
            # left as extracted (model parameters); species properties of the
            # actual reactants are looked up separately from the ontology.

        # fix #3: capture the RECIPE (per-reactant pulse/purge, ncycles, carrier gas
        # + flow, chamber pressure) from the methods text (document.md), per material.
        mr = methods_recipe.parse(p["dir"])
        for x in resolved:
            rr = mr.get(x.get("material"))
            if not rr:
                continue
            ctrl = x.get("controlled") or []
            coord = x.get("coordinate")
            def put(q, v, u, react=None):
                if q == coord:                       # don't clobber a swept coordinate
                    return
                ctrl[:] = [c for c in ctrl if not (c.get("quantity") == q and c.get("of_reactant") == react)]
                ctrl.append({"quantity": q, "value": v, "unit": u, "of_reactant": react, "source": "methods"})
            if coord != "pulse_time":                # drop shared pulse/purge -> per-reactant
                ctrl[:] = [c for c in ctrl if not (c.get("quantity") in ("pulse_time", "purge_time")
                                                   and c.get("of_reactant") is None)]
            for lab in ("A", "B"):
                if rr["purge"].get(lab) is not None: put("purge_time", rr["purge"][lab], "s", lab)
                if rr["pulse"].get(lab) is not None: put("pulse_time", rr["pulse"][lab], "s", lab)
            if rr.get("ncycles") and not any(c.get("quantity") == "cycle_number" for c in ctrl):
                ctrl.append({"quantity": "cycle_number", "value": rr["ncycles"], "unit": "cycles", "source": "methods"})
            if rr.get("chamber_pressure"): put("total_pressure", rr["chamber_pressure"], "Pa")
            if rr.get("carrier_flow"): put("flow_rate", rr["carrier_flow"], "sccm")
            x["controlled"] = ctrl
            if rr.get("carrier"):                    # carrier/background gas is a PROCESS
                x["carrier_gas"] = {"species": rr["carrier"],   # species, NOT a cycle
                                    "flow_sccm": rr.get("carrier_flow")}   # reactant (no A/B/C label)

        # species properties from the ontology for each CYCLE reactant (A precursor,
        # B coreactant, …) — consistent & correct (TMA 72.09, H2O 18.02). The carrier
        # gas keeps its properties on its own species individual (N2 28.01), read where
        # needed (transport model) — not stored as a per-experiment reactant condition.
        for x in resolved:
            for r in x.get("reactants") or []:
                sp, lab = r.get("species"), r["label"]
                if not sp:
                    continue
                mm, dpm = species_prop(sp, "molar_mass"), species_prop(sp, "molecular_diameter")
                x["controlled"] = [c for c in (x.get("controlled") or [])
                                   if not (c.get("quantity") in ("molecular_mass", "precursor_molecular_diameter")
                                           and c.get("of_reactant") == lab)]
                if mm is not None:
                    x["controlled"].append({"quantity": "molecular_mass", "value": round(mm, 4),
                                            "unit": "g/mol", "of_reactant": lab, "source": "species"})
                if dpm is not None:
                    x["controlled"].append({"quantity": "precursor_molecular_diameter", "value": round(dpm * 1e-3, 4),
                                            "unit": "nm", "of_reactant": lab, "source": "species"})
        # S2: dedup identical curves within a paper (same series + points)
        seen = {}
        for x in resolved:
            if x.get("points"):
                sig = (x.get("series_name"), json.dumps(x.get("points")))
                if sig in seen:
                    x["duplicate_of"] = seen[sig]
                    if "duplicate" not in x["issues"]: x["issues"].append("duplicate")
                    x["analysis_ready"] = False
                else:
                    seen[sig] = (x.get("provenance") or {}).get("figure_id")
        # S2: cross-source reproduction tag (series named after another paper's author)
        self_author = re.match(r"[a-z]+", pid).group(0)
        for x in resolved:
            sn = (x.get("series_name") or "").lower()
            for a in ("arts", "yim", "ylilammi", "aguinsky", "cremers", "ylivaara"):
                if a in sn and a != self_author:
                    x["reproduced_from"] = a; break
        # S6: model<->experiment pairing within a figure (same measurand + coordinate)
        groups = {}
        for x in resolved:
            k = ((x.get("provenance") or {}).get("figure_id"), x.get("coordinate"),
                 (x.get("measurand") or {}).get("quantity"))
            groups.setdefault(k, []).append(x)
        for grp in groups.values():
            rels = {x.get("relevance") for x in grp}
            if {"model", "experimental"} <= rels:
                for x in grp: x["has_model_pair"] = True
        fc = {}                                # stable structured id: <pid>-F<fig><panel>-<k>
        for x in resolved:
            lab = fig_label(x.get("provenance"))
            fc[lab] = fc.get(lab, 0) + 1
            x["exp_id"] = f"{pid}-F{lab}-{fc[lab]}"
        for x in resolved:                     # 1 recipe per experiment (its own process)
            r = recipe_mod.from_experiment(x)
            x["recipe"] = r.to_dict()
            x["recipe"]["completeness"] = r.completeness()
        out_dir = OUTPUT / pid / "resolved"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "experiments.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False))
        (out_dir / "series.json").write_text(json.dumps(series, indent=2, ensure_ascii=False))
        g = Counter(x["granularity"] for x in resolved)
        r = Counter(x["relevance"] for x in resolved)
        print(f"[{pid}] {len(resolved)} exps  granularity={dict(g)}  relevance={dict(r)}  series={len(series)}")


if __name__ == "__main__":
    main()
