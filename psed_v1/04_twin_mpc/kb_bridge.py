"""
kb_bridge.py  (M1)
------------------
Turns the digital twin's hardcoded parameters into a KB lookup. `params_for` runs
the parameter-resolution cascade (INTEGRATION_STRATEGY.md §2.3):

  1. KB literature value   (kb_service.kb_params — extracted, with σ across papers)
  2. Material property     (ontology material individual: molar_mass, density, …)
  3. Model default         (channelModel's own hardcoded value — the fallback)

Each resolved parameter carries its source, so downstream control knows which
numbers are literature-grounded vs assumed, and can use the σ for robust/uncertain
control (later milestone).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "02_extraction"))
import kb_service  # noqa: E402

# ---- unit converters: KB unit -> channelModel SI ----
C = {
    "nm2m": lambda v: v * 1e-9,
    "pm2m": lambda v: v * 1e-12,        # pm -> m (precursor molecular_diameter)
    "gmol2kg": lambda v: v * 1e-3,      # g/mol -> kg/mol
    "C2K": lambda v: v + 273.15,        # °C -> K
    "gcc2si": lambda v: v * 1000.0,     # g/cm^3 -> kg/m^3
    "id": lambda v: v,
}

# (model attr, reactant label, species property, converter) — resolved from the
# precursor/coreactant INDIVIDUAL when the species is known (tier 0, most
# authoritative: an intrinsic species property, not a per-experiment number).
SPECIES_MAP = [
    ("da", "A", "molecular_diameter", "pm2m"),
    ("db", "B", "molecular_diameter", "pm2m"),
    ("MA", "A", "molar_mass", "gmol2kg"),
    ("MB", "B", "molar_mass", "gmol2kg"),
    ("b_a", "A", "central_atoms", "id"),
]

# (model attr, quantity id, reactant, converter)   — the ~1:1 mapping
PARAM_MAP = [
    ("gpc", "growth_per_cycle", None, "nm2m"),
    ("K",  "adsorption_rate_constant", None, "id"),
    ("c",  "reaction_probability", None, "id"),
    ("da", "precursor_molecular_diameter", "A", "nm2m"),
    ("db", "precursor_molecular_diameter", "B", "nm2m"),
    ("MA", "molecular_mass", "A", "gmol2kg"),
    ("MB", "molecular_mass", "B", "gmol2kg"),
    ("H",  "feature_height", None, "nm2m"),
    ("W",  "feature_width", None, "nm2m"),
    ("T",  "temperature", None, "C2K"),
    ("pA", "reactant_A_partial_pressure", None, "id"),
    ("pB", "reactant_B_partial_pressure", None, "id"),
    ("t_p", "pulse_time", "A", "id"),
]
# (model attr, material property, converter)
MATERIAL_MAP = [
    ("M", "molar_mass", "gmol2kg"),
    ("rho", "density", "gcc2si"),
    ("b_film", "metal_atoms", "id"),
]


def params_for(material, process=None, species=None):
    """Return (resolved {attr: value}, provenance {attr: {...}}).
    `species` = {"A": "TMA", "B": "H2O"} resolves species-intrinsic properties
    (diameter, mass, central atoms) from the ontology precursor individuals."""
    kp = kb_service.kb_params(material, process)
    resolved, prov = {}, {}
    if species:                                             # tier 0: species property
        for attr, lab, prop, conv in SPECIES_MAP:
            sp = species.get(lab)
            val = kb_service.precursor_property(sp, prop)
            if val is not None:
                resolved[attr] = C[conv](val)
                prov[attr] = {"source": "precursor", "species": sp, "property": prop, "raw": val}
    for attr, q, r, conv in PARAM_MAP:                       # tier 1: KB literature
        if attr in resolved:
            continue
        rec = kp.get((q, r)) or (kp.get((q, None)) if r else None)
        if rec is not None:
            f = C[conv]
            resolved[attr] = f(rec["value"])
            prov[attr] = {"source": "kb", "quantity": q, "reactant": r,
                          "raw": rec["value"], "unit": rec["unit"],
                          "sigma": abs(f(rec["value"] + rec["sigma"]) - f(rec["value"])),
                          "n": rec["n"], "refs": rec["refs"]}
    for attr, prop, conv in MATERIAL_MAP:                    # tier 2: material property
        if attr in resolved:
            continue
        val = kb_service.material_property(material, prop)
        if val is not None:
            resolved[attr] = C[conv](val)
            prov[attr] = {"source": "material", "property": prop, "raw": val}
    # tier 3 (model default) is implicit: anything not in `resolved` keeps the
    # channelModel.__init__ value; mark those in provenance at build time.
    return resolved, prov


def saturation_prior_from_kb(material, process=None):
    """Derive a REAL, physics-grounded precursor uptake rate k1 (1/s) for the 0-D
    saturation model from the KB's extracted kinetics — the honest link between the
    conformality data we have and the dose-saturation task.

        k1 = c · Φ / q ,   Φ = pA / sqrt(2π m kB T)   (Hertz-Knudsen arrival flux)

    where c = reaction_probability (sticking), q = saturated site density, pA =
    precursor partial pressure, m = MA/N0. Returns k1 + the inputs it used + the
    implied saturation dose t_sat≈3/k1, all with provenance, or None if the KB lacks
    the sticking coefficient. NOTE: this is grounded for a REAL chemistry (e.g.
    Al2O3/TMA); the synthetic Yanguas-Gil benchmark processes are NOT in the KB."""
    import math
    kp = kb_service.kb_params(material, process)
    def kv(q, r=None):
        rec = kp.get((q, r)) or kp.get((q, None))
        return rec["value"] if rec else None
    q_site = kv("saturated_coverage")
    pA = kv("reactant_A_partial_pressure") or kv("partial_pressure", "A")
    T_C = kv("temperature") or 220
    # prefer the REAL per-species INITIAL sticking probability (Arts 2019, curated
    # into the ontology) over the lumped conformality-fit c; fall back to c.
    prec = "TMA" if material == "Al2O3" else None
    s0 = kb_service.precursor_property(prec, "sticking_probability") if prec else None
    c_source = "species_sticking(arts2019)" if s0 else "lumped_c(ylilammi)"
    c = s0 or kv("reaction_probability")
    if not (c and q_site and pA):
        return None
    MA_gmol = kb_service.precursor_property("TMA", "molar_mass") if material == "Al2O3" else None
    MA = (MA_gmol or 72.09) * 1e-3                     # kg/mol
    T = T_C + 273.15
    m = MA / 6.022e23                                  # mass per molecule (kg)
    flux = pA / math.sqrt(2 * math.pi * m * 1.380649e-23 * T)   # molecules/m^2/s
    k1 = c * flux / q_site                             # 1/s
    return {"k1": k1, "t_sat_s": 3.0 / k1,
            "inputs": {"c": c, "c_source": c_source, "q_site": q_site, "pA": pA, "MA": MA, "T": T},
            "refs": (kp.get(("reaction_probability", None)) or {}).get("refs", []),
            "self_limited": True}       # a saturating reaction_probability ⇒ self-limited


def warm_start(material, target=None, structure=None, process=None, k=5, min_coverage=2.0):
    """Seed a controller from the closest literature process (Approach 5 /
    Phase 5). Returns (pA0, tp0, r_star, priors, provenance):

      pA0, tp0  — starting precursor partial pressure & dose/pulse time, from the
                  nearest similar experiment's recipe, else the material's KB median.
      r_star    — pA0/tp0, the cost-optimal-ratio seed for run_pid (skips its grid search).
      priors    — expected GPC (±σ), self-limited?, from kb_service.get_priors.

    Argonne P2 got −33% samples from a single prior; a literature warm-start seeds
    the MPC/PID with grounded values instead of a cold mid-range guess."""
    q = {"material": material, "process_type": process}
    if structure:
        q["structure"] = structure
    q["controlled"] = ([{"quantity": "temperature", "value": target["temperature"]}]
                       if target and target.get("temperature") else [])
    if target and target.get("aspect_ratio"):
        q["controlled"].append({"quantity": "aspect_ratio", "value": target["aspect_ratio"]})

    hits = [h for h in kb_service.find_similar(q, k=k) if h["coverage"] >= min_coverage]
    kp = kb_service.kb_params(material, process)

    def from_hit_or_kb(q_time, q_press):
        pA = tp = None
        src_exp = None
        for h in hits:                                   # nearest recipe with dose info
            r = h.get("recipe") or {}
            for rt in r.get("reactants") or []:
                if rt.get("role") == "precursor":
                    tp = tp if tp is not None else rt.get("dose_time")
                    pA = pA if pA is not None else rt.get("partial_pressure")
            if tp is not None or pA is not None:
                src_exp = h["exp_id"]
                break
        # fall back to material KB median for whatever the nearest recipe lacks
        if tp is None:
            rec = kp.get((q_time, "A")) or kp.get((q_time, None))
            tp = rec["value"] if rec else None
        if pA is None:
            rec = kp.get((q_press, "A")) or kp.get((q_press, None))
            pA = rec["value"] if rec else None
        return pA, tp, src_exp

    pA0, tp0, src_exp = from_hit_or_kb("pulse_time", "reactant_A_partial_pressure")
    priors = kb_service.get_priors(material, process)
    r_star = (pA0 / tp0) if (pA0 and tp0) else None
    prov = {"nearest": src_exp, "similarity": (hits[0]["score"] if hits else None),
            "n_similar": len(hits),
            "pA0_source": "kb" if pA0 else "none", "tp0_source": "kb" if tp0 else "none"}
    return {"pA0": pA0, "tp0": tp0, "r_star": r_star, "priors": priors, "provenance": prov}


if __name__ == "__main__":
    for mat in ("Al2O3", "TiO2", "HfO2"):
        res, prov = params_for(mat)
        kb = sum(1 for p in prov.values() if p["source"] == "kb")
        matn = sum(1 for p in prov.values() if p["source"] == "material")
        print(f"{mat:6}: {kb} params from KB, {matn} from material props, "
              f"{len(PARAM_MAP)+len(MATERIAL_MAP)-len(res)} default")
    print("\n== warm-start (Phase 5): seed controller from nearest literature process ==")
    for mat, tgt in (("Al2O3", {"aspect_ratio": 30}), ("TiO2", None), ("HfO2", None)):
        w = warm_start(mat, target=tgt)
        p = w["priors"]
        print(f"{mat:6}: pA0={w['pA0']}  tp0={w['tp0']}  r*={w['r_star'] and round(w['r_star'],2)}  "
              f"gpc_exp={p['gpc_expected']}  self_limited={p['self_limited']}  "
              f"nearest={w['provenance']['nearest']} (sim={w['provenance']['similarity']})")
