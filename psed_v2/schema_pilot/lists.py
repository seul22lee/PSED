"""The fixed lists of the pilot schema: quantity ids, qualifier keys and values, method ids, and the enums of each table.
Shared by convert.py, validate.py and make_report.py; SCHEMA.md prints the same lists."""
import re

# quantity ids: those used in cases 1 to 13 plus those needed by two or more of the three papers; anything else is "other"
QUANTITIES = sorted({
    "aspect_ratio", "carrier_gas", "coated_aspect_ratio", "composition", "crystallinity", "cycle_number", "cycle_time",
    "deposition_temperature", "dimensionless_distance", "distance", "equivalent_aspect_ratio", "exposure", "feature_depth",
    "feature_width", "film_density", "film_thickness", "front_slope", "gas_flow_rate", "growth_per_cycle",
    "initial_sticking_coefficient", "knudsen_number", "lumped_sticking_coefficient", "mean_free_path", "normalized_exposure",
    "normalized_thickness", "open_fraction", "partial_pressure", "penetration_depth", "precursor_purity", "probe_resolution",
    "process_pressure", "pulse_time", "purge_time", "reactor_type", "recombination_probability", "resistivity",
    "saturation_density", "source_temperature", "step_coverage", "substrate", "surface_coverage", "thickness_nonuniformity",
    "other",
})
ALIASES = {"reactor": "reactor_type", "measurement_instrument": "other", "spot_size": "probe_resolution",
           "reflectometer_magnification": "other", "cycles": "cycle_number"}

TOKEN = re.compile(r"^[A-Za-z0-9+_.]+$")
QUALIFIERS = {          # key: allowed values (None = a chemical or element token)
    "step": {"reactant_A", "purge_A", "reactant_B", "purge_B", "plasma", "hold_A", "hold_B", "none"},
    "position": {"planar", "local", "top", "sidewall", "bottom", "entrance", "plateau", "outside"},
    "kind": {"set_point", "measured"},
    "reference": {"plateau", "entrance", "maximum", "stated", "planar", "assumed_saturation"},
    "by": {"H", "2H", "d", "w", "lambda", "none"},
    "origin": {"entrance", "top_face", "hole_centre", "nearer_face", "opening_centre"},
    "level": {"50%", "front_start", "front_end"},
    "basis": {"AR", "EAR"},
    "species": None, "gas": None, "element": None,
}

METHODS = ["reflectometry", "ellipsometry", "sem", "sem_eds", "tem", "xps", "raman", "xrd", "afm", "electrical", "rbs",
           "process_monitor", "gravimetry", "photograph", "simulation", "calculation", "cited", "schematic", "tabulated"]
METHOD_RULES = [  # first match wins; applied to the draft's free-text method
    (r"ICDD|reference powder|literature|cited", "cited"), (r"illustration|schematic|sketch", "schematic"),
    (r"simulat|model|MATLAB|ylilammi|Monte Carlo", "simulation"), (r"EDS|EDX", "sem_eds"), (r"\bS?TEM\b", "tem"),
    (r"\bSEM\b|secondary-electron", "sem"), (r"reflectomet", "reflectometry"), (r"\bSE\b|ellipsom|M-2000", "ellipsometry"),
    (r"XPS", "xps"), (r"Raman", "raman"), (r"XRD|diffract", "xrd"), (r"AFM", "afm"),
    (r"four-point|Hall|transistor|resistiv|I-V|electr|probe station", "electrical"), (r"RBS", "rbs"),
    (r"pressure|Baratron|thermocouple|gauge|QCM|temperature log", "process_monitor"),
    (r"photo", "photograph"), (r"mass|weigh|BET|porosit|adsorption", "gravimetry"),
    (r"analysis|calculat|derived|fit|classification|ratio", "calculation"), (r"table|Table", "tabulated")]

SAMPLE_KINDS = {"run", "piece", "channel", "reference", "group", "model_run"}
SERIES_KINDS = {"plot", "image", "map", "spectrum", "table"}
CONDITION_KINDS = {"process", "measurement", "substrate_prep"}
DATA_KINDS_SERIES = {"measured", "fit", "simulation", "calculated", "cited", "schematic"}
DATA_KINDS_VALUE = {"measured", "fit", "chosen input", "literature", "assumed", "calculated"}
DATA_KINDS_CONDITION = {"stated", "calculated", "assumed"}
CENSOR = {"", "<", ">", "<dl", ">dl"}


def method_id(text):
    if not text:
        return ""
    for rx, m in METHOD_RULES:
        if re.search(rx, text, re.I):
            return m
    return "calculation"


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
