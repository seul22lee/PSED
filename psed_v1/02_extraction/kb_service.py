"""
kb_service.py  (M0)
-------------------
The single interface the LLM agent and the MPC twin use to read the knowledge
base. Pure functions over the resolved corpus + the ontology. Every value carries
provenance (source, uncertainty σ, sample count n, and the papers it came from).

M0 implements the parameter/prior/target reads; retrieval (RAG) and find_similar
are thin wrappers to be fleshed out in later milestones.
"""
import json
import glob
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
_MATERIALS = {m["id"]: m for m in ONTO["individuals"].get("materials", [])}
# precursor/coreactant species -> individual (indexed by id, formula, full_name, aka)
_SPECIES = {}
for _g in ("precursors", "coreactants"):
    for _it in ONTO["individuals"].get(_g, []):
        for _key in [_it["id"], _it.get("formula"), _it.get("full_name")] + (_it.get("aka") or []):
            if _key:
                _SPECIES[str(_key).strip().lower()] = _it


def _load(include_non_experimental=True):
    """Resolved records for KB questions, tagged with their paper id.

    `experiments.json` now holds ONLY current-paper experimental cases, so a
    modelling paper (whose curves are simulations or re-plotted literature) has
    none. Chemistry/condition questions must still see those papers — the process
    they study is real evidence even when the plotted curve is not this paper's
    experiment — so the typed entity records are folded in, each tagged with its
    `record_nature`. Callers that need experiments only can filter on it."""
    out = []
    for f in sorted(glob.glob(str(ROOT.parent / "papers" / "*" / "resolved" / "experiments.json"))):
        pid = f.split("/papers/")[1].split("/")[0]
        for e in json.loads(Path(f).read_text()):
            e["_pid"] = pid
            e.setdefault("record_nature", "experimental_case")
            out.append(e)
    if not include_non_experimental:
        return out
    for f in sorted(glob.glob(str(ROOT.parent / "papers" / "*" / "resolved" / "entities.json"))):
        pid = f.split("/papers/")[1].split("/")[0]
        for ent in json.loads(Path(f).read_text()):
            if ent.get("is_current_paper_experiment"):
                continue          # already present as an experimental case
            out.append({
                "_pid": pid, "exp_id": ent["entity_id"],
                "record_nature": ent["classification"],
                "entity_id": ent["entity_id"], "entity_class": ent["entity_class"],
                "material": ent.get("material"),
                "precursors": ent.get("precursors") or [],
                "coreactants": ent.get("coreactants") or [],
                "reactants": ent.get("reactants") or [],
                "process_type": ent.get("process_type"),
                "structure": ent.get("structure"),
                "geometry_class": ent.get("geometry_class"),
                "chemistry_provenance": ent.get("chemistry_provenance"),
                "controlled": [
                    {"quantity": b.get("quantity"), "value": b.get("value"),
                     "unit": b.get("unit"), "of_reactant": b.get("of_reactant"),
                     "source": b.get("source_kind"), "scope": b.get("bound_at_scope"),
                     "context_status": "resolved"}
                    for b in (ent.get("bound_conditions") or [])],
                "measurand": {"quantity": ent.get("measurand"),
                              "unit": ent.get("measurand_unit")},
                "coordinate": ent.get("coordinate"),
                "points": [[o.get("x_raw"), o.get("y_raw")] for o in ent.get("observations") or []],
                "relevance": ("model" if ent["classification"] in
                              ("simulation", "model_sweep") else "experimental"),
                "is_model_result": ent["classification"] in ("simulation", "model_sweep"),
                "analysis_ready": bool(ent.get("observations")),
                "provenance": ent.get("provenance") or {},
            })
    return out


# =============================================================================
# probabilistic estimation — likelihood over the literature, not a bare median
# =============================================================================
def estimate(values, weights=None, rel_sd_default=0.2, z=1.0):
    """Likelihood-based point estimate + predictive credible interval for a
    physical quantity, from a (optionally weighted) set of literature values.
    Positive quantities are modelled log-normal (their natural scale), so the
    point estimate is the weighted geometric mean = MLE of the log-normal scale;
    others are Gaussian. `weights` (e.g. covariate similarity) let closer
    experiments count more. Returns value/mode/sd/ci + effective sample size."""
    data = [(float(v), (weights[i] if weights else 1.0)) for i, v in enumerate(values)
            if isinstance(v, (int, float))]
    data = [(v, w) for v, w in data if w > 0]
    if not data:
        return None
    positive = all(v > 0 for v, _ in data)
    tf = math.log if positive else (lambda x: x)
    inv = math.exp if positive else (lambda x: x)
    W = sum(w for _, w in data)
    W2 = sum(w * w for _, w in data)
    mu = sum(w * tf(v) for v, w in data) / W
    n_eff = (W * W) / W2 if W2 else 1.0
    denom = W - W2 / W
    if len(data) >= 2 and denom > 1e-9:
        var = sum(w * (tf(v) - mu) ** 2 for v, w in data) / denom
    else:                                            # single (effective) observation
        var = (rel_sd_default ** 2) if positive else (abs(mu) * rel_sd_default) ** 2
    s = math.sqrt(max(var, 1e-12))
    se = s * math.sqrt(1.0 + 1.0 / n_eff)            # predictive: a new experiment's value
    sig = lambda x: float(f"{x:.6g}")                # strip log/exp float noise
    return {"value": sig(inv(mu)), "mode": sig(inv(mu - var) if positive else mu),
            "sd": sig((inv(mu + s) - inv(mu)) if positive else s),
            "ci_lo": sig(inv(mu - z * se)), "ci_hi": sig(inv(mu + z * se)),
            "n": len(data), "n_eff": round(n_eff, 2),
            "dist": "lognormal" if positive else "normal", "method": "weighted-loglik"}


# quantities that mean the same thing for imputation (merge donor pools)
_ALIAS_Q = {"temperature": {"temperature", "deposition_temperature"},
            "deposition_temperature": {"temperature", "deposition_temperature"}}


def impute(target, quantity, reactant=None, corpus=None, SC=None,
           ready_only=True, gamma=2.0, min_sim=0.15, topk=8):
    """Fill a missing value for `target` by covariate-conditioned probabilistic
    inference: gather every experiment that HAS this (quantity, reactant), weight
    each by its configuration similarity to the target (condition_similarity ^ gamma),
    and draw a similarity-weighted likelihood estimate. So a missing dose/temperature
    is inferred from the experiments most like this one, not a global median — and it
    reports which experiments (and how similar) it leaned on."""
    import similarity as sim
    E = corpus if corpus is not None else _load()
    if SC is None:
        SC = sim.logscale(E + [target])
    qset = _ALIAS_Q.get(quantity, {quantity})
    tid = target.get("exp_id")
    donors = []
    for e in E:
        if e is target or (tid and e.get("exp_id") == tid):
            continue
        if ready_only and not e.get("analysis_ready"):
            continue
        # HARD same-material filter: a donor must be the SAME deposited material, not
        # merely similar in other conditions. Material is a gate, not a weight — otherwise
        # a ZrO2 paper's 10 s pulse could win an Al2O3 dose on matching temperature/geometry.
        if e.get("material") != target.get("material"):
            continue
        val = None
        for c in e.get("controlled") or []:
            if (c.get("quantity") in qset and isinstance(c.get("value"), (int, float))
                    and (reactant is None or c.get("of_reactant") == reactant)):
                val = c["value"]
                break
        if val is None:
            continue
        cs = sim.condition_similarity(target, e, SC)
        s = cs["score"]
        if s is None or s < min_sim:
            continue
        donors.append((val, s, e.get("exp_id")))
    if not donors:
        return None
    donors.sort(key=lambda d: -d[1])
    use = donors[:topk] if topk else donors
    est = estimate([v for v, _, _ in use], [s ** gamma for _, s, _ in use])
    if not est:
        return None
    est.update({"source": "kb", "n_donors": len(donors),
                "donors": [{"exp_id": i, "sim": round(s, 3), "value": v} for v, s, i in use[:5]]})
    return est


def kb_params(material, process=None, ready_only=True):
    """Aggregate every numeric controlled condition for a material (optionally a
    process) into {(quantity, reactant): {value(median), sigma, n, min, max, unit,
    source, refs}}. This is the raw parameter store the bridge maps to a model."""
    agg, units, refs = defaultdict(list), {}, defaultdict(set)
    for e in _load():
        if material and e.get("material") != material:
            continue
        if process and e.get("process_type") != process:
            continue
        if ready_only and not e.get("analysis_ready"):
            continue
        for c in e.get("controlled") or []:
            q, v, r = c.get("quantity"), c.get("value"), c.get("of_reactant")
            if q and isinstance(v, (int, float)):
                agg[(q, r)].append(v)
                units[(q, r)] = c.get("unit")
                refs[(q, r)].add(e["_pid"])
    out = {}
    for key, vs in agg.items():
        est = estimate(vs)                            # likelihood point estimate + CI
        out[key] = {"value": est["value"], "n": len(vs),
                    "sigma": est["sd"], "ci": [est["ci_lo"], est["ci_hi"]],
                    "dist": est["dist"], "n_eff": est["n_eff"],
                    "min": min(vs), "max": max(vs), "unit": units[key],
                    "source": "kb", "refs": sorted(refs[key])}
    return out


def material_property(material, prop):
    """Look up a material property (molar_mass, density, metal_atoms, formula)
    from the ontology material individuals. Returns None if absent."""
    m = _MATERIALS.get(material)
    return (m or {}).get(prop)


def precursor_property(species, prop):
    """Intrinsic property of a precursor/coreactant SPECIES (molar_mass,
    molecular_diameter, central_atoms) from the ontology — not per-experiment.
    Accepts id / formula / full_name / alias. Returns None if unknown."""
    if not species:
        return None
    return (_SPECIES.get(str(species).strip().lower()) or {}).get(prop)


def get_priors(material, process=None):
    """Process priors for warm-starting an optimizer (expected GPC, whether the
    process is known self-limited, typical dose)."""
    kp = kb_params(material, process)
    gpc = kp.get(("growth_per_cycle", None))
    pulse = kp.get(("pulse_time", "A")) or kp.get(("pulse_time", None))
    # self-limited if the corpus shows saturating GPC (has a growth_per_cycle at all
    # + a reaction_probability); a CVD paper would lack clean saturation
    return {"gpc_expected": gpc["value"] if gpc else None,
            "gpc_sigma": gpc["sigma"] if gpc else None,
            "dose_typical_s": pulse["value"] if pulse else None,
            "self_limited": bool(gpc) and ("reaction_probability", None) in kp,
            "n_papers": len({r for v in kp.values() for r in v["refs"]})}


def get_targets(material):
    """Extracted conformality targets a controller could aim for (penetration)."""
    kp = kb_params(material)
    pen = kp.get(("penetration_depth", None))
    return {"penetration_depth": pen["value"] if pen else None,
            "penetration_sigma": pen["sigma"] if pen else None}


def get_recipe(exp_id):
    """The recipe (reactor process) of a single experiment — 1 recipe per experiment."""
    for e in _load():
        if e.get("exp_id") == exp_id:
            return e.get("recipe")
    return None


def list_recipes(material=None, ready_only=True, min_completeness=0.0):
    """Every experiment's recipe, optionally filtered."""
    out = []
    for e in _load():
        if ready_only and not e.get("analysis_ready"):
            continue
        if material and e.get("material") != material:
            continue
        r = e.get("recipe")
        if r and r.get("completeness", 0) >= min_completeness:
            out.append({"exp_id": e.get("exp_id"), **r})
    return out


def materials():
    return sorted({e.get("material") for e in _load() if e.get("material")})


def find_similar(query, k=5, ready_only=True, exclude_id=None):
    """Rank known experiments by configuration similarity to `query` (a partial
    experiment: material / process_type / precursors / coreactants / controlled
    conditions). Returns the k nearest, each with its recipe + dose conditions —
    the basis for warm-starting a controller from the closest literature process.

    Reuses similarity.condition_similarity (coverage-aware Gower). `query` only
    needs the fields you know; missing fields simply don't contribute."""
    import similarity as sim
    E = [e for e in _load() if (not ready_only or e.get("analysis_ready"))
         and e.get("exp_id") != exclude_id]
    SC = sim.logscale(E + [query])
    scored = []
    for e in E:
        cs = sim.condition_similarity(query, e, SC)
        if cs["score"] is None:
            continue
        scored.append({"exp_id": e.get("exp_id"), "material": e.get("material"),
                       "score": cs["score"], "coverage": cs["coverage"],
                       "parts": cs["parts"], "recipe": e.get("recipe"),
                       "refs": [e["_pid"]]})
    scored.sort(key=lambda s: -s["score"])
    return scored[:k]


if __name__ == "__main__":
    for mat in materials():
        p = get_priors(mat)
        print(f"{mat:6}  gpc_expected={p['gpc_expected']}  self_limited={p['self_limited']}  "
              f"papers={p['n_papers']}")
    print("\nAl2O3 raw params (quantity, reactant) -> median [n, ±σ, refs]:")
    for (q, r), v in sorted(kb_params("Al2O3").items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        print(f"  {q:30} r={str(r):4} {v['value']:.4g} {str(v['unit'] or ''):8} "
              f"[n={v['n']}, ±{v['sigma']:.3g}, {','.join(v['refs'])}]")
