"""
expand_v02_quantities.py
------------------------
Idempotently add the quantities identified as missing when auditing the v0.1
ontology against the two authoritative ALD reviews:
  - Cremers, Puurunen, Dendooven, "Conformality in ALD" (Appl. Phys. Rev. 2019)
  - Kessels et al., "Atomic layer deposition" (Nat. Rev. Methods Primers 2025)

New domains introduced: conformality, film_property, precursor_property, model.
Run once; safe to re-run (keyed by canonical_name).
"""
import json
from pathlib import Path

DICT = Path(__file__).parent / "dictionary.json"

NEW = [
    # ---- conformality outputs (Cremers) ----
    {"canonical_name": "recombination_probability", "domain": "reaction", "symbols": ["r"],
     "aliases": ["recombination probability", "surface recombination probability",
                 "radical recombination probability", "recombination coefficient"]},
    {"canonical_name": "step_coverage", "domain": "conformality", "symbols": ["SC"],
     "aliases": ["step coverage", "bottom-top ratio", "sidewall-top ratio", "step-coverage"]},
    {"canonical_name": "coated_aspect_ratio", "domain": "conformality", "symbols": [],
     "aliases": ["coated aspect ratio", "coated EAR", "coated equivalent aspect ratio"]},
    {"canonical_name": "penetration_depth_50", "domain": "conformality", "symbols": ["PD50"],
     "aliases": ["PD50%", "half-thickness penetration depth", "50% penetration depth",
                 "50%-thickness-penetration-depth"]},
    {"canonical_name": "penetration_depth_80", "domain": "conformality", "symbols": ["PD80"],
     "aliases": ["PD80%", "80% penetration depth"]},
    {"canonical_name": "initial_sticking_coefficient", "domain": "reaction", "symbols": ["s0"],
     "aliases": ["initial sticking coefficient", "initial sticking probability", "s0"]},
    {"canonical_name": "saturated_coverage", "domain": "reaction", "symbols": ["Kmax"],
     "aliases": ["saturated coverage", "saturation coverage", "Kmax",
                 "saturated surface coverage", "saturated coverage per unit area"]},
    {"canonical_name": "conformality", "domain": "conformality", "symbols": [],
     "aliases": ["conformality", "film conformality", "conformity"]},
    {"canonical_name": "uniformity", "domain": "conformality", "symbols": [],
     "aliases": ["uniformity", "film uniformity", "thickness uniformity",
                 "non-uniformity", "within-wafer uniformity"]},
    {"canonical_name": "nucleation_delay", "domain": "deposition", "symbols": [],
     "aliases": ["nucleation delay", "incubation cycles", "incubation period",
                 "incubation time", "incubation behavior"]},
    {"canonical_name": "exposure", "domain": "process", "symbols": [],
     "aliases": ["exposure", "reactant exposure", "dose", "precursor dose", "reactant dose"]},
    # ---- transport / model quantities (Cremers §V) ----
    {"canonical_name": "scattering_length", "domain": "transport", "symbols": ["lambda_0"],
     "aliases": ["scattering length", "specific scattering length"]},
    {"canonical_name": "collision_cross_section", "domain": "transport", "symbols": ["sigma"],
     "aliases": ["collision cross section", "cross section", "molecular cross-section"]},
    {"canonical_name": "reactant_flux_to_wall", "domain": "transport", "symbols": ["J_wall"],
     "aliases": ["reactant flux to walls", "wall flux", "reactant flux per unit area"]},
    {"canonical_name": "precursor_density", "domain": "transport", "symbols": ["n"],
     "aliases": ["precursor density", "reactant density", "precursor concentration"]},
    {"canonical_name": "cvd_reaction_probability", "domain": "model", "symbols": ["p_reaction"],
     "aliases": ["CVD reaction probability", "reaction probability CVD", "preaction"]},
    {"canonical_name": "transition_probability", "domain": "model", "symbols": ["q_ji", "P_ij"],
     "aliases": ["transition probability", "transmission probability", "re-emission probability"]},
    {"canonical_name": "specific_surface_area", "domain": "geometry", "symbols": ["dAs"],
     "aliases": ["specific surface area", "surface area per unit volume", "area per unit volume"]},
    {"canonical_name": "adsorption_site_area", "domain": "reaction", "symbols": ["A0"],
     "aliases": ["average adsorption site area", "area per adsorption site"]},
    {"canonical_name": "pore_diameter", "domain": "geometry", "symbols": ["d_p"],
     "aliases": ["pore diameter", "feature diameter", "hole diameter"]},
    {"canonical_name": "tortuosity", "domain": "geometry", "symbols": [],
     "aliases": ["tortuosity"]},
    {"canonical_name": "porosity", "domain": "geometry", "symbols": [],
     "aliases": ["porosity", "void fraction"]},
    {"canonical_name": "residence_time", "domain": "process", "symbols": ["t_r"],
     "aliases": ["residence time"]},
    {"canonical_name": "mixing_time", "domain": "process", "symbols": ["t_m"],
     "aliases": ["mixing time", "characteristic mixing time"]},
    # ---- plasma (Cremers PE-ALD) ----
    {"canonical_name": "plasma_power", "domain": "plasma", "symbols": [],
     "aliases": ["plasma power", "RF power", "plasma RF power"]},
    {"canonical_name": "plasma_exposure_time", "domain": "plasma", "symbols": [],
     "aliases": ["plasma exposure time", "plasma pulse time"]},
    # ---- precursor properties (Kessels Experimentation) ----
    {"canonical_name": "vapour_pressure", "domain": "precursor_property", "symbols": [],
     "aliases": ["vapour pressure", "vapor pressure"]},
    {"canonical_name": "decomposition_temperature", "domain": "precursor_property", "symbols": [],
     "aliases": ["decomposition temperature", "thermal decomposition temperature"]},
    {"canonical_name": "melting_point", "domain": "precursor_property", "symbols": [],
     "aliases": ["melting point"]},
    {"canonical_name": "volatility", "domain": "precursor_property", "symbols": [],
     "aliases": ["volatility"]},
    {"canonical_name": "reactivity", "domain": "precursor_property", "symbols": [],
     "aliases": ["reactivity", "precursor reactivity"]},
    {"canonical_name": "temperature_window", "domain": "process", "symbols": [],
     "aliases": ["ALD window", "temperature window", "ALD temperature window",
                 "process window"]},
    {"canonical_name": "deposition_rate", "domain": "deposition", "symbols": [],
     "aliases": ["deposition rate", "growth rate per time"]},
    # ---- film / material properties (Kessels Results, Applications) ----
    {"canonical_name": "film_density", "domain": "film_property", "symbols": ["rho"],
     "aliases": ["film density", "density", "mass density"]},
    {"canonical_name": "resistivity", "domain": "film_property", "symbols": [],
     "aliases": ["resistivity", "electrical resistivity"]},
    {"canonical_name": "refractive_index", "domain": "film_property", "symbols": ["n_ref"],
     "aliases": ["refractive index"]},
    {"canonical_name": "dielectric_constant", "domain": "film_property", "symbols": ["k", "kappa"],
     "aliases": ["dielectric constant", "k-value", "permittivity", "relative permittivity"]},
    {"canonical_name": "equivalent_oxide_thickness", "domain": "film_property", "symbols": ["EOT"],
     "aliases": ["equivalent oxide thickness", "EOT"]},
    {"canonical_name": "work_function", "domain": "film_property", "symbols": [],
     "aliases": ["work function"]},
    {"canonical_name": "band_gap", "domain": "film_property", "symbols": ["Eg"],
     "aliases": ["band gap", "bandgap"]},
    {"canonical_name": "crystallinity", "domain": "film_property", "symbols": [],
     "aliases": ["crystallinity", "crystalline fraction"]},
    {"canonical_name": "grain_size", "domain": "film_property", "symbols": [],
     "aliases": ["grain size", "crystallite size"]},
    {"canonical_name": "surface_roughness", "domain": "film_property", "symbols": ["Ra", "Rq"],
     "aliases": ["surface roughness", "roughness", "RMS roughness"]},
    {"canonical_name": "impurity_content", "domain": "film_property", "symbols": [],
     "aliases": ["impurity content", "carbon content", "impurity concentration"]},
    {"canonical_name": "composition", "domain": "film_property", "symbols": [],
     "aliases": ["composition", "film composition", "stoichiometry", "atomic composition"]},
    {"canonical_name": "dopant_content", "domain": "film_property", "symbols": [],
     "aliases": ["dopant content", "doping concentration", "dopant concentration"]},
    {"canonical_name": "areal_density", "domain": "deposition", "symbols": [],
     "aliases": ["areal density", "atoms per nm2", "surface atom density"]},
    {"canonical_name": "film_stress", "domain": "film_property", "symbols": [],
     "aliases": ["film stress", "residual stress"]},
]


def main():
    d = json.loads(DICT.read_text())
    have = {e["canonical_name"] for e in d}
    added = 0
    for q in NEW:
        if q["canonical_name"] not in have:
            d.append(q)
            added += 1
    DICT.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    print(f"added {added} new quantities (total now {len(d)})")


if __name__ == "__main__":
    main()
