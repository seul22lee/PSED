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
    # added 2026-10-15 for the workbench filters: the film deposited and the test structure, as value_text from the lists below
    "material", "structure_type",
    "raman_shift",                                     # the abscissa of a Raman spectrum (x= of a curve)
    # derived quantities (DERIVED below): computed from facts, never stored
    "effective_channel_height", "exposure_per_run", "sheet_resistance", "h_per_metal", "density_relative_to_bulk", "moles_deposited",
    "moles_from_mass_gain", "shell_volume_fraction", "deposition_rate",
    "other",
})

# the process-defining settings, in the order the screens show them; a join or a natural series needs both entities to state the same
# ones (an entity that states no temperature is not the same experiment as one that does)
PRIMARY = ["reactor_type", "deposition_temperature", "plasma_gas_ratio", "process_pressure", "precursor_purity", "source_temperature", "pulse_time",
           "purge_time", "feature_height", "cycle_number", "substrate"]

# quantities that name a chosen input, never what a measurement found: an observation never carries one (check.py); a threshold
# the authors read off a series (the ratio from which films are crystalline) is an observation of quantity other
SETTING_QUANTITIES = {"deposition_temperature", "source_temperature", "annealing_temperature", "pulse_time", "purge_time", "cycle_time",
                      "cycle_number", "plasma_gas_ratio", "gas_flow_rate", "carrier_gas", "precursor_purity", "substrate", "pillar_layout",
                      "reactor_type", "objective_magnification", "probe_resolution", "process_pressure", "structure_type", "material"}

# the film material (material, value_text) and the test structure type (structure_type, value_text; Cremers 2019's taxonomy)
# of a process or group; the workbench filters list these ids
MATERIALS = ["Al2O3", "MoS2", "WS2", "TiS2", "ZnO"]

# panels that encode a value as a colour against a bar: a valued fact citing one says "read from colour" in its statement (check.py)
COLOUR_PANELS = {"mat22": {"fig7b": "GPC 0.50 to 1.75 Å/cycle, linear bar", "fig8": "resistivity 1e-3 to 1e3 Ω cm, log bar; black = above the detection limit"}}
STRUCTURES = ["planar", "lateral_channel", "trench", "hole", "pillar_array", "nanotube_array", "porous"]

TOKEN = re.compile(r"^[A-Za-z0-9+_.]+$")
QUALIFIERS = {          # key: allowed values (None = a chemical or element token)
    "step": {"reactant_A", "purge_A", "reactant_B", "purge_B", "plasma", "hold_A", "hold_B", "none"},
    "position": {"planar", "local", "top", "sidewall", "bottom", "entrance", "plateau", "outside", "interface"},
    "kind": {"set_point", "measured"},
    "reference": {"plateau", "entrance", "maximum", "stated", "planar", "assumed_saturation", "bulk"},
    "by": {"H", "2H", "d", "w", "lambda", "none"},
    "origin": {"entrance", "top_face", "hole_centre", "nearer_face", "opening_centre"},
    "level": {"50%", "front_start", "front_end", "maximum"},
    "stage": {"initial", "final"},
    "basis": {"AR", "EAR"},
    "species": None, "gas": None, "element": None,
    # a spread fact (P1): a value about the spread of the quantity it names, not a value of it. stat = what the number is; between =
    # what varies between the repeats (separate runs, pieces of one run, positions in one film, repeated measurement of one spot,
    # separately made items such as chips); n = the number of repeats, or not_stated. The condition it was measured at is its parent.
    "stat": {"sd", "relative_sd", "half_range", "tolerance", "minimum", "maximum"},
    "between": {"runs", "pieces", "position", "repeat_measurement", "items"},
    "n": None,
}
QUALIFIERS["x"] = set(QUANTITIES) - {"other"}         # the abscissa of a curve (every points_ref fact carries one), a quantity id
QUALIFIERS["ratio"] = None                            # the plasma_gas_ratio a recipe-level lookup setting belongs to (mat22 Table 2 flows per ratio)

METHODS = ["reflectometry", "ellipsometry", "sem", "sem_eds", "tem", "xps", "raman", "xrd", "afm", "electrical", "rbs",
           "process_monitor", "gravimetry", "photograph", "simulation", "calculation", "cited", "schematic", "tabulated",
           "optical_microscopy"]
CENSOR = {"", "<", ">", "<dl", ">dl"}

# facts (stage 2): fact types and data kinds
TYPES = ["setting", "observation", "derived", "model", "definition", "claim", "cited", "bridge", "comparison"]   # bridge: user facts only;
#   comparison: the authors' comparison intent (a series, a grid, a replicate set), a fact with members, not a parent
STANCES = ["asserted", "hedged", "open", "limitation"]
# mechanism tokens for a claim's cause and effect (mechanism:<token>), beside the quantity ids
MECHANISMS = ["surface_OH", "excess_S", "fin_growth", "Zn_metal", "residual_H2O", "membrane_sagging", "channel_plugging", "channel_narrowing",
              "water_readsorption", "H_incorporation", "precursor_adsorption", "pillar_effect", "nanostep", "native_oxide", "optical_model",
              "scan_angle", "interaction_volume", "averaging", "channel_length", "run_variation", "surface_chemistry", "plasma_chemistry",
              "edge_reactivity", "thiol_groups", "S_vacancy", "surface_oxidation", "self_limiting", "side_reaction", "gas_diffusion",
              "gas_generation", "leak", "reaction_diffusion", "desorption", "percolation", "cracks", "reabsorption", "CVD_growth"]


def variables_ok(s):
    """'a;b' of quantity ids or mechanism:<token> -> list of problems."""
    return [t for t in s.split(";") if t and not (t in QUANTITIES and t != "other") and not (t.startswith("mechanism:") and t[10:] in MECHANISMS)]   # a claim's stance, from the paper's own wording ("likely", "may" -> hedged;
#   "cannot be excluded", "further work" -> open; a stated shortcoming of the study or method -> limitation)
# tree rows (stage 3): the paper, activities (something done, with settings: kind from ACTIVITY_KINDS, order when several apply to one
# entity, how stated or inferred) and entities (a physical thing or its state: a specimen, a piece cut from it, a position, a model
# run; how stated or inferred). The tree is physical provenance only: paper -> recipe -> deposition -> entity -> later activities ->
# facts. The authors' comparison intent is a fact of type comparison (kind, the varied quantity, links = purpose + members), not a parent.
NODE_TYPES = ["paper", "activity", "entity"]
ACTIVITY_KINDS = ["recipe", "deposition", "anneal", "plasma_treatment", "measurement", "simulation"]
COMPARISON_KINDS = ["series", "grid", "replicate"]
HOW = ["stated", "inferred"]
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
         "signal_intensity": "", "reaction_stoichiometry": "", "annealing_temperature": "°C", "raman_shift": "cm-1",
         "effective_channel_height": "nm", "exposure_per_run": "Torr s", "sheet_resistance": "Ω/sq", "h_per_metal": "", "density_relative_to_bulk": "%",
         "moles_deposited": "mmol", "moles_from_mass_gain": "mmol", "shell_volume_fraction": "%", "deposition_rate": "nm/h"}

# unit normalisation: spellings the facts use for one unit, and every unit's dimension and factor to that dimension's base unit;
# convert() turns a value from one unit into another of the same dimension (°C and K by offset)
UNIT_ALIAS = {"g/cm^3": "g/cm3", "Å/cyc": "Å", "Å/cycle": "Å", "nm/cycle": "nm", "nm/cyc": "nm", "µmol/cyc": "µmol", "Torr-s": "Torr s", "Ω-cm": "Ω cm",
              "at. %": "%", "at.%": "%", "wt%": "%", "SCCM": "sccm", "at/nm2/cycle": "nm-2", "kg m-3": "kg/m3", "mol-1": "1/mol", "nm^-2": "nm-2"}
UNIT_BASE = {"pm": ("length", 1e-3), "Å": ("length", 0.1), "nm": ("length", 1.0), "µm": ("length", 1e3), "mm": ("length", 1e6), "cm": ("length", 1e7),
             "m": ("length", 1e9), "s": ("time", 1.0), "min": ("time", 60.0), "h": ("time", 3600.0), "Pa": ("pressure", 1.0), "mTorr": ("pressure", 0.133322),
             "Torr": ("pressure", 133.322), "Pa s": ("exposure", 1.0), "Torr s": ("exposure", 133.322), "g/cm3": ("density", 1.0), "kg/m3": ("density", 1e-3),
             "mol": ("amount", 1.0), "mmol": ("amount", 1e-3), "µmol": ("amount", 1e-6), "%": ("fraction", 0.01), "": ("fraction", 1.0),
             "°C": ("temperature", 1.0), "K": ("temperature", 1.0), "g/mol": ("molar mass", 1.0), "g": ("mass", 1.0), "nm-2": ("areal density", 1.0),
             "Ω cm": ("resistivity", 1.0), "Ω m": ("resistivity", 100.0), "Ω/sq": ("sheet resistance", 1.0), "nm/h": ("rate", 1.0), "1/mol": ("per mole", 1.0),
             "J/K": ("energy per kelvin", 1.0), "sccm": ("flow", 1.0), "W": ("power", 1.0), "eV": ("energy", 1.0)}


def convert(v, from_unit, to_unit):
    a, b = UNIT_ALIAS.get(from_unit, from_unit), UNIT_ALIAS.get(to_unit, to_unit)
    if a == b:
        return v
    if {a, b} == {"°C", "K"}:
        return v + 273.15 if b == "K" else v - 273.15
    (da, fa), (db, fb) = UNIT_BASE[a], UNIT_BASE[b]
    if da != db:
        raise ValueError(f"cannot convert {a} to {b}")
    return v * fa / fb


# derived quantities: defined once here, computed never stored (questions.derive(); the workbench's derived axis). Each has the
# inputs it reads (name; a quantity id, or other:<label>, alternatives with |; the qualifiers a fact must carry, @material and @A
# standing for the entity's film material and reactant A; the unit the formula expects; optional: pick = qualifier sets to prefer
# when several facts match, default = the value when none does, all = every matching fact as a list, scope = paper to search the
# whole paper's facts, not only the entity's), the formula in words and as a function, the result's unit. An input no paper fact
# serves comes from an assumed fact (user.facts.csv, data_kind assumed), and the result says so. A derived id that is also a stated
# quantity (growth_per_cycle, atoms_per_cycle, exposure, mean_free_path, knudsen_number, cycle_time) is a second route to it: the
# stated fact wins unless the route is asked for.
def _in(name, q, quals="", unit="", pick=None, default=None, all=False, scope="entity"):
    return dict(name=name, q=q, quals=quals, unit=unit, pick=pick, default=default, all=all, scope=scope)


DERIVED = {
    "effective_channel_height": dict(unit="nm", formula="H − 2·S_IIb: the design height minus twice the plateau thickness",
                                     inputs=[_in("H", "feature_height", "", "nm"), _in("S", "film_thickness", "position=plateau", "nm")], fn=lambda H, S: H - 2 * S),
    "exposure": dict(unit="Torr s", formula="partial pressure of reactant A × its pulse time",
                     inputs=[_in("p", "partial_pressure", "step=reactant_A", "Torr"), _in("t", "pulse_time", "step=reactant_A", "s")], fn=lambda p, t: p * t),
    "exposure_per_run": dict(unit="Torr s", formula="exposure per pulse × cycle number",
                             inputs=[_in("E", "exposure", "", "Torr s"), _in("N", "cycle_number", "", "")], fn=lambda E, N: E * N),
    "sheet_resistance": dict(unit="Ω/sq", formula="resistivity / film thickness",
                             inputs=[_in("rho", "resistivity", "", "Ω cm"), _in("t", "film_thickness", "", "cm")], fn=lambda rho, t: rho / t),
    "growth_per_cycle": dict(unit="nm", formula="atoms per cycle × M / (ρ N_A): the thickness the deposited metal atoms make at the film's density",
                             inputs=[_in("n", "atoms_per_cycle", "", "nm-2"), _in("M", "other:molar mass", "species=@material", "g/mol"), _in("rho", "film_density", "", "g/cm3"),
                                     _in("NA", "other:Avogadro constant", "", "1/mol")], fn=lambda n, M, rho, NA: n * M / (NA * rho * 1e-21)),
    "atoms_per_cycle": dict(unit="nm-2", formula="GPC × ρ_bulk N_A / M: metal atoms per nm² per cycle at the bulk density",
                            inputs=[_in("gpc", "growth_per_cycle", "", "nm", pick=["", "position=plateau"]), _in("rho", "film_density", "reference=bulk;species=@material", "g/cm3", scope="paper"),
                                    _in("M", "other:molar mass", "species=@material", "g/mol"), _in("NA", "other:Avogadro constant", "", "1/mol")],
                            fn=lambda gpc, rho, M, NA: gpc * rho * 1e-21 * NA / M),
    "h_per_metal": dict(unit="", formula="H at.% / Mo at.%, with Mo at.% = (100 − H − N − O at.%) / (1 + S/Mo)",
                        inputs=[_in("H", "composition", "element=H", "%"), _in("SMo", "composition", "element=S", ""), _in("N", "composition", "element=N", "%", default=0),
                                _in("O", "composition", "element=O", "%", default=0)], fn=lambda H, SMo, N, O: H / ((100 - H - N - O) / (1 + SMo))),
    "density_relative_to_bulk": dict(unit="%", formula="film density / bulk density",
                                     inputs=[_in("rho", "film_density", "", "g/cm3"), _in("rb", "film_density", "reference=bulk;species=@material", "g/cm3", scope="paper")], fn=lambda rho, rb: 100 * rho / rb),
    "moles_deposited": dict(unit="mmol", formula="Δn_s per cycle × cycle number",
                            inputs=[_in("dn", "deposited_moles_per_cycle", "", "mmol"), _in("N", "cycle_number", "", "")], fn=lambda dn, N: dn * N),
    "moles_from_mass_gain": dict(unit="mmol", formula="mass gain × powder mass per compact × compacts per run / M",
                                 inputs=[_in("mg", "mass_gain", "", ""), _in("m0", "other:powder mass", "", "g"), _in("k", "other:NPCs per run", "", ""),
                                         _in("M", "other:molar mass", "species=@material", "g/mol")], fn=lambda mg, m0, k, M: 1000 * mg * m0 * k / M),
    "shell_volume_fraction": dict(unit="%", formula="(1 − φ_i) × ((d_NP + 2 t)³ / d_NP³ − 1): the coating's share of the compact volume, spherical particles",
                                  inputs=[_in("phi", "porosity", "stage=initial", ""), _in("d", "other:d_NP", "", "nm"), _in("t", "film_thickness", "", "nm")],
                                  fn=lambda phi, d, t: 100 * (1 - phi) * ((d + 2 * t) ** 3 / d ** 3 - 1)),
    "mean_free_path": dict(unit="µm", formula="k_B T / (√2 π d² p) for reactant A at the deposition temperature and its partial pressure",
                           inputs=[_in("T", "deposition_temperature", "", "K"), _in("p", "partial_pressure", "", "Pa", pick=["", "step=reactant_A"]),
                                   _in("d", "other:molecular diameter", "species=@A", "nm"), _in("kB", "other:Boltzmann constant", "", "J/K")],
                           fn=lambda T, p, d, kB: 1e6 * kB * T / (2 ** 0.5 * 3.141592653589793 * (d * 1e-9) ** 2 * p)),
    "knudsen_number": dict(unit="", formula="mean free path / characteristic size (the hydraulic diameter, the pore or particle diameter, the feature width)",
                           inputs=[_in("lam", "mean_free_path", "", "µm"), _in("h", "other:hydraulic diameter h|other:d_NP|feature_width", "", "µm")], fn=lambda lam, h: lam / h),
    "cycle_time": dict(unit="s", formula="the sum of the pulse, hold and purge times of one cycle",
                       inputs=[_in("t", "pulse_time|purge_time|other:DEZ hold|other:H2O hold", "", "s", all=True)], fn=lambda t: sum(t)),
    "deposition_rate": dict(unit="nm/h", formula="GPC × 3600 / cycle time",
                            inputs=[_in("gpc", "growth_per_cycle", "", "nm", pick=["", "position=plateau"]), _in("tc", "cycle_time", "", "s")], fn=lambda gpc, tc: gpc * 3600 / tc),
}
assert all(k in QUANTITIES for k in DERIVED), "DERIVED key not a quantity id"

# short display labels, used by every screen: one per quantity id, and one per common quantity{qualifiers} combination
# (qualifiers written as in the facts, without x=). A combination not listed shows the quantity's label followed by the
# qualifier values ("composition S", "BE Mo"); a curve shows "<y label> vs <x label>".
LABELS = {
    "aspect_ratio": "AR", "carrier_gas": "carrier gas", "coated_aspect_ratio": "coated AR", "composition": "composition",
    "crystallinity": "crystallinity", "cycle_number": "N", "cycle_time": "cycle time", "deposition_temperature": "T",
    "dimensionless_distance": "x̃", "distance": "x", "equivalent_aspect_ratio": "EAR", "exposure": "exposure", "feature_depth": "depth",
    "feature_height": "H", "feature_width": "w", "film_density": "density", "film_thickness": "S", "front_slope": "front slope",
    "gas_flow_rate": "flow", "growth_per_cycle": "GPC", "initial_sticking_coefficient": "s0", "knudsen_number": "Kn",
    "lumped_sticking_coefficient": "c", "mean_free_path": "λ", "normalized_exposure": "normalized exposure",
    "normalized_thickness": "normalized S", "open_fraction": "open fraction", "partial_pressure": "p_partial",
    "penetration_depth": "PD", "precursor_purity": "purity", "probe_resolution": "spot", "process_pressure": "p",
    "pulse_time": "pulse", "purge_time": "purge", "reactor_type": "reactor", "recombination_probability": "r",
    "resistivity": "ρ", "saturation_density": "q_sat", "source_temperature": "T_source", "step_coverage": "step coverage",
    "substrate": "substrate", "surface_coverage": "θ", "thickness_nonuniformity": "nonuniformity", "plasma_gas_ratio": "gas ratio",
    "mass_gain": "mass gain", "porosity": "porosity", "crystallite_size": "crystallite size", "gas_moles_per_cycle": "Δn_g",
    "deposited_moles_per_cycle": "Δn_s", "pressure_rise": "δp", "pressure_rate": "TS", "time_to_maximum": "t_max", "roughness": "Rq",
    "binding_energy": "BE", "atoms_per_cycle": "atoms/cycle", "carrier_concentration": "carriers", "carrier_mobility": "mobility",
    "pillar_layout": "pillar layout", "objective_magnification": "objective", "fit_r2": "R²", "fill_fraction": "fill",
    "signal_intensity": "intensity", "reaction_stoichiometry": "ȳ", "annealing_temperature": "T_anneal", "material": "material",
    "structure_type": "structure", "raman_shift": "Raman shift", "other": "other",
    "pulse_time{step=reactant_A;species=TMA}": "TMA pulse", "pulse_time{step=reactant_B;species=H2O}": "H2O pulse",
    "pulse_time{step=reactant_A;species=DEZ}": "DEZ pulse", "pulse_time{step=reactant_A}": "pulse A", "pulse_time{step=plasma}": "plasma step",
    "purge_time{step=purge_A}": "purge A", "purge_time{step=purge_B}": "purge B",
    "deposition_temperature{kind=set_point}": "T set point", "deposition_temperature{step=reactant_A}": "T (A dose)",
    "deposition_temperature{step=purge_A}": "T (purge A)", "deposition_temperature{step=reactant_B}": "T (B dose)",
    "deposition_temperature{step=purge_B}": "T (purge B)",
    "dimensionless_distance{level=50%;by=H}": "x̃50", "penetration_depth{level=50%;origin=entrance}": "PD50",
    "penetration_depth{origin=entrance}": "PD", "front_slope{by=H}": "slope d(S/N)/dx̃", "front_slope{by=H;reference=entrance}": "slope dθ/dx̃",
    "film_thickness{position=plateau}": "S_plateau", "film_thickness{position=outside}": "S_outside", "film_thickness{position=interface}": "S_interface",
    "growth_per_cycle{position=plateau}": "GPC_plateau", "growth_per_cycle{position=outside}": "GPC_outside",
    "normalized_thickness{reference=entrance}": "S/S_entry", "plasma_gas_ratio{gas=H2}": "H2 ratio",
    "gas_flow_rate{step=plasma;gas=H2S}": "H2S flow", "gas_flow_rate{step=plasma;gas=H2}": "H2 flow", "gas_flow_rate{step=plasma;gas=Ar}": "Ar flow (plasma)",
    "gas_flow_rate{gas=N2}": "N2 flow", "gas_flow_rate{gas=Ar}": "Ar purge flow", "gas_flow_rate{gas=Ar;step=reactant_A}": "Ar carrier flow",
    "gas_flow_rate{step=plasma}": "plasma flow", "process_pressure{step=plasma}": "p (plasma)", "process_pressure{step=reactant_A;kind=set_point}": "p set point (A)",
    "lumped_sticking_coefficient{species=TMA}": "c_TMA", "lumped_sticking_coefficient{species=H2O}": "c_H2O",
    "porosity{stage=initial}": "φ_i", "porosity{stage=final}": "φ_f", "pressure_rise{level=maximum}": "δp_max", "composition{element=S}": "S/Mo",
    "effective_channel_height": "H_eff", "exposure_per_run": "exposure per run", "sheet_resistance": "R_sheet", "h_per_metal": "H per metal",
    "density_relative_to_bulk": "ρ/ρ_bulk", "moles_deposited": "moles deposited", "moles_from_mass_gain": "moles from mass gain",
    "shell_volume_fraction": "coating volume fraction", "deposition_rate": "nm per hour",
}
assert all(k.split("{")[0] in QUANTITIES for k in LABELS), "LABELS key not a quantity id"
assert all(q in LABELS for q in QUANTITIES), "quantity without a label"
