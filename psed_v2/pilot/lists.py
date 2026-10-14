"""The one set of controlled lists of the pilot: quantity ids, qualifier keys and values, method ids, fact types, data kinds,
censor marks and canonical units (UNITS, for the unit standardization of stage 4). Used by facts.py and check.py."""
import re

# quantity ids: those used in cases 1 to 13 plus those needed by two or more of the three papers; anything else is "other"
# (feature_height: the gap of a lateral channel, H; plasma_gas_ratio: a gas's share of the plasma feed, gas=; mass_gain and
# porosity in %; gas_moles_per_cycle / deposited_moles_per_cycle: Δn_g / Δn_s; pressure_rise: δp, pressure_rate: its slope;
# signal_intensity: a detector signal against position or energy, element= or species=; reaction_stoichiometry: ligands
# released per precursor (x, ȳ); pillar_layout: a named layout, value in the statement; fit_r2: goodness of a fit)
QUANTITIES = sorted({
    "aspect_ratio", "carrier_gas", "coated_aspect_ratio", "composition", "crystallinity", "cycle_number", "cycle_time",
    "deposition_temperature", "dimensionless_distance", "distance", "equivalent_aspect_ratio", "exposure", "feature_depth",
    "feature_height", "feature_width", "film_density", "film_thickness", "front_slope", "gas_flow_rate", "growth_per_cycle",
    "initial_sticking_coefficient", "knudsen_number", "lumped_sticking_coefficient", "mean_free_path", "normalized_exposure",
    "normalized_thickness", "open_fraction", "partial_pressure", "penetration_depth", "precursor_purity", "probe_resolution",
    "process_pressure", "pulse_time", "purge_time", "reactor_type", "recombination_probability", "resistivity",
    "saturation_density", "source_temperature", "step_coverage", "substrate", "surface_coverage", "thickness_nonuniformity",
    # added 2026-10-14 so that what a group varies and what its runs mainly observe are never "other"
    "plasma_gas_ratio", "mass_gain", "porosity", "crystallite_size", "gas_moles_per_cycle", "deposited_moles_per_cycle",
    "pressure_rise", "pressure_rate", "time_to_maximum", "roughness", "binding_energy", "atoms_per_cycle",
    "carrier_concentration", "carrier_mobility", "pillar_layout", "objective_magnification", "fit_r2", "fill_fraction",
    "signal_intensity", "reaction_stoichiometry", "annealing_temperature",
    "other",
})

TOKEN = re.compile(r"^[A-Za-z0-9+_.]+$")
QUALIFIERS = {          # key: allowed values (None = a chemical or element token)
    "step": {"reactant_A", "purge_A", "reactant_B", "purge_B", "plasma", "hold_A", "hold_B", "none"},
    "position": {"planar", "local", "top", "sidewall", "bottom", "entrance", "plateau", "outside", "interface"},
    "kind": {"set_point", "measured"},
    "reference": {"plateau", "entrance", "maximum", "stated", "planar", "assumed_saturation"},
    "by": {"H", "2H", "d", "w", "lambda", "none"},
    "origin": {"entrance", "top_face", "hole_centre", "nearer_face", "opening_centre"},
    "level": {"50%", "front_start", "front_end", "maximum"},
    "stage": {"initial", "final"},
    "basis": {"AR", "EAR"},
    "species": None, "gas": None, "element": None,
    "run": {"deposition", "specimen", "simulation"}, "how": {"stated", "inferred"},   # tree rows (stage 3)
    "sample": None, "sim": None,
}

METHODS = ["reflectometry", "ellipsometry", "sem", "sem_eds", "tem", "xps", "raman", "xrd", "afm", "electrical", "rbs",
           "process_monitor", "gravimetry", "photograph", "simulation", "calculation", "cited", "schematic", "tabulated",
           "optical_microscopy"]
CENSOR = {"", "<", ">", "<dl", ">dl"}

# facts (stage 2): fact types and data kinds
TYPES = ["setting", "observation", "derived", "model", "definition", "claim", "cited"]
NODE_TYPES = ["paper", "process", "group", "run"]     # tree rows of stage 3 (cited works use type cited)
DATA_KINDS = ["assumed", "calculated", "chosen input", "fit", "literature", "measured"]


def qualifiers_ok(q):
    """q: 'k=v;k=v' -> list of problems."""
    bad = []
    for part in filter(None, q.split(";")):
        if "=" not in part:
            bad.append(part); continue
        k, v = part.split("=", 1)
        allowed = QUALIFIERS.get(k, "missing")
        if allowed == "missing" or (allowed is None and not TOKEN.match(v)) or (allowed and v not in allowed):
            bad.append(part)
    return bad

# canonical units (for stage 4): a fact with one of these quantities carries exactly this unit
UNITS = {"deposition_temperature": "°C", "source_temperature": "°C", "pulse_time": "s", "purge_time": "s", "cycle_time": "s",
         "process_pressure": "Pa", "partial_pressure": "Pa", "exposure": "Pa s", "film_thickness": "nm", "feature_width": "nm",
         "feature_depth": "nm", "feature_height": "nm", "distance": "µm", "penetration_depth": "µm", "growth_per_cycle": "Å", "gas_flow_rate": "sccm",
         "resistivity": "Ω cm", "film_density": "g/cm3", "mean_free_path": "µm", "cycle_number": "", "aspect_ratio": "",
         "coated_aspect_ratio": "", "equivalent_aspect_ratio": "", "lumped_sticking_coefficient": "", "initial_sticking_coefficient": "",
         "recombination_probability": "", "knudsen_number": "", "normalized_thickness": "", "dimensionless_distance": "",
         "step_coverage": "%", "saturation_density": "nm-2", "plasma_gas_ratio": "", "mass_gain": "%", "porosity": "%",
         "crystallite_size": "nm", "gas_moles_per_cycle": "µmol", "deposited_moles_per_cycle": "µmol", "pressure_rise": "Torr",
         "pressure_rate": "mTorr/min", "time_to_maximum": "min", "roughness": "nm", "binding_energy": "eV", "atoms_per_cycle": "nm-2",
         "carrier_concentration": "cm-3", "carrier_mobility": "cm2/Vs", "objective_magnification": "", "fit_r2": "", "fill_fraction": "%",
         "signal_intensity": "", "reaction_stoichiometry": "", "annealing_temperature": "°C"}
