"""The controlled lists of the pilot. The vocabularies (quantity ids, qualifier keys and values, method ids, materials, structures,
species, labels and names) are generated from the ontology into vocab.py (python3 psed_v2/ontology/export.py; P49) and imported
here, never hand-edited; this file keeps the rules that use them: fact types, data kinds, censor marks, canonical units, derived
quantities, display names of qualifier combinations. Used by facts.py, check.py and query.py."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vocab import (STRUCTURE_CLASSES, TRANSFORMS, CATEGORICAL_VALUES, CONCEPTS, ATTRIBUTES, TO_ABSORB, TRANSFORM_OUTPUTS, REPLACED, QUANTITIES, QUALIFIERS, METHODS, METHOD_CLASS,  # noqa: F401
                   METHOD_DEFINITION, SPECIES, MATERIALS, STRUCTURES, STRUCTURE_CLASS, TO_ABSORB_VALUES, FAMILIES, MECHANISMS as _MECH,
                   RELATIONS, KINDS, PHRASES, SPECIMEN_CLASSES, PILOT_MAP, OUTPUTS, AMBIGUOUS, BASES, ENTRIES, HIERARCHY, AMBIGUOUS_ALIASES, VALUE_ALIASES,
                   LABELS as _LABELS, NAMES as _NAMES, FROM_OTHER)


# the process-defining settings, in the order the screens show them; a join or a natural series needs both entities to state the same
# ones (an entity that states no temperature is not the same experiment as one that does)
PRIMARY = ["reactor", "reactor_type", "deposition_temperature", "plasma_gas_ratio", "process_pressure", "precursor_purity", "source_temperature", "pulse_time",
           "purge_time", "feature_width", "cycle_number", "substrate"]

# substance-scoped settings (P50): a setting of one of these quantities is about one substance and must say which (species= or gas=);
# for pulse_time only the reactant and hold steps (a plasma step names its feed through the gas settings of the same recipe)
SUBSTANCE_SCOPED = {"precursor_purity", "source_temperature", "partial_pressure", "exposure", "gas_flow_rate", "plasma_gas_ratio", "pulse_time"}
SUBSTANCE_STEPS = {"reactant_A", "reactant_B", "hold_A", "hold_B"}


def substance_scoped(f):
    """Whether a setting fact must carry a species or gas qualifier."""
    if f["type"] != "setting" or f["quantity"] not in SUBSTANCE_SCOPED:
        return False
    q = dict(p.split("=", 1) for p in f["qualifiers"].split(";") if "=" in p)
    return f["quantity"] != "pulse_time" or q.get("step") in SUBSTANCE_STEPS


# quantities that name a chosen input, never what a measurement found: an observation never carries one (check.py); a threshold
# the authors read off a series (the ratio from which films are crystalline) is an observation of quantity other
SETTING_QUANTITIES = {"deposition_temperature", "source_temperature", "annealing_temperature", "pulse_time", "purge_time", "cycle_time",
                      "cycle_number", "plasma_gas_ratio", "gas_flow_rate", "carrier_gas", "precursor_purity", "substrate", "pillar_layout",
                      "reactor", "reactor_type", "objective_magnification", "probe_resolution", "process_pressure", "structure", "material"}

# metal atoms per formula unit of each film material, read from its formula in the ontology (the first element of the formula);
# a value text not yet a species id (TO_ABSORB_VALUES) keeps its hand count until P50
FORMULA_METALS = {i: int(re.match(r"[A-Z][a-z]?(\d*)", s["formula"]).group(1) or 1) for i, s in SPECIES.items() if s["kind"] == "material" and s["formula"]}
FORMULA_METALS.update({"Al2O3": 2, "MoS2": 1, "WS2": 1, "TiS2": 1, "ZnO": 1})


def species_text(v):
    """A species id as the screen prints it (its first alias, the name the papers print: TMA, H2O, MoS2, glassy carbon), any other
    value as it is."""
    return SPECIES[v]["name"] or v if v in SPECIES else v

# panels that encode a value as a colour against a bar: a valued fact citing one says "read from colour" in its statement (check.py)
COLOUR_PANELS = {"mat22": {"fig7b": "GPC 0.50 to 1.75 Å/cycle, linear bar", "fig8": "resistivity 1e-3 to 1e3 Ω cm, log bar; black = above the detection limit"}}

TOKEN = re.compile(r"^[A-Za-z0-9+_.]+$")
# QUALIFIERS (vocab.py): key -> the closed set of values, or None for an open value (a species id, an element symbol, a number). The
# keys and their meaning: step, position, kind (set_point, measured, default: what most entities used (inherited); option: used by
# some, which is not stated (not inherited); target: an aimed value), reference, by, origin, level, stage, basis, species, gas,
# element; stat/between/n (a spread fact, P1: the statistic, what varies between the repeats, the number of repeats); relative_to
# (what a fraction is a fraction of, P4); over (what a per-cycle value is averaged over, P5); mode (in situ or ex situ, P6);
# x (a curve's abscissa); ratio (the plasma_gas_ratio a keyed setting belongs to, P17).
QUALIFIERS = {k: (set(v) if v is not None else None) for k, v in QUALIFIERS.items()}
PHASE_VALUES = {"detected", "not detected"}
# quantities on which a ratio means nothing (P24): interval scales (°C temperatures, positions, shifts) and signed quantities (slopes,
# rates that change sign); two values of these are compared by their difference
NOT_RATIO_SCALE = {"deposition_temperature", "source_temperature", "annealing_temperature", "distance", "pressure_rate", "front_slope",
                   "binding_energy", "raman_shift"}
# whether entities with equal conditions are one physical thing (P23): an identity fact (type identity, kind one of these, links the
# entities) records it; only 'different' makes them repeats
IDENTITY_KINDS = {"same", "different", "not_stated"}

# the mode a measurement method has unless a paper says otherwise (ellipsometry and generic measurements are set per activity)
METHOD_MODE = {"process_monitor": "in_situ", "oes": "in_situ", "calibration": "in_situ", "xrd": "ex_situ", "xps": "ex_situ", "raman": "ex_situ",
               "sem": "ex_situ", "sem_eds": "ex_situ", "tem": "ex_situ", "afm": "ex_situ", "four_point_probe": "ex_situ", "two_point_through_thickness": "ex_situ",
               "hall": "ex_situ", "transistor_iv": "ex_situ", "rbs": "ex_situ",
               "reflectometry": "ex_situ", "gravimetry": "ex_situ", "weighing_before": "ex_situ", "photograph": "ex_situ",
               "optical_microscopy": "ex_situ", "metrology": "ex_situ"}
# the definition a quantity has when none is named: the screen names a definition only when it differs from this
DEFAULT_DEFINITION = {"growth_per_cycle": {"over": "run"}, "atoms_per_cycle": {"over": "run"}, "plasma_gas_ratio": {"relative_to": "reactive_gases"},
                      "phase_fraction": {"relative_to": "crystalline_phases"}, "mass_gain": {"relative_to": "initial_mass"}, "porosity": {"relative_to": "total_volume"}}
QUALIFIERS["x"] = set(QUANTITIES) - {"other"}         # the abscissa of a curve (every points_ref fact carries one), a quantity id
# a keyed setting (P17): qualifier key -> the setting whose value it names; inherited only by a node whose own value of that setting matches
KEYED = {"ratio": "plasma_gas_ratio"}

CENSOR = {"", "<", ">", "<dl", ">dl"}
# what a ± is (P2): between pieces of one run, between runs, between positions in one film, a repeated measurement, a fit error, a
# measurement uncertainty the paper states (electrode area, weighing), the spread of literature values, propagated from inputs, or
# not stated by the paper
UNCERTAINTY_KINDS = {"pieces", "runs", "position", "repeat_measurement", "fit", "measurement", "literature", "propagated", "not_stated"}
# the basis of an uncertainty (Sec. 19, P60; vocab.BASES holds the closed list and its phrases): from what the ± spans (P2's kind)
# or, for a spread fact, from what varies between its repeats and its statistic; not_stated gives no basis
BASIS_OF_KIND = {"pieces": "within_run", "position": "within_run", "repeat_measurement": "instrument", "measurement": "instrument", "runs": "run_to_run",
                 "fit": "fit", "literature": "literature", "propagated": "propagated", "not_stated": ""}
BASIS_OF_SPREAD = {"items": "tolerance", "runs": "run_to_run", "pieces": "within_run", "position": "within_run", "repeat_measurement": "instrument"}


def basis_of(kind="", between="", stat=""):
    """The Sec. 19 basis of a ± (kind, P2) or of a spread fact (between and stat, P1); '' when the paper does not say."""
    if stat == "tolerance":
        return "tolerance"
    if between:
        return BASIS_OF_SPREAD.get(between, "")
    return BASIS_OF_KIND.get(kind, "")


assert all(b in BASES for b in set(BASIS_OF_KIND.values()) | set(BASIS_OF_SPREAD.values()) if b), "a basis outside the Sec. 19 list"

# facts (stage 2): fact types and data kinds
TYPES = ["setting", "observation", "derived", "model", "definition", "claim", "cited", "bridge", "comparison", "identity", "caveat"]   # bridge: user facts only;
#   comparison: the authors' comparison intent (a series, a grid, a replicate set), a fact with members, not a parent
STANCES = ["asserted", "hedged", "open", "limitation"]
# the mechanisms a claim's cause or effect may name (vocab.MECHANISMS, from the ontology's mechanism entries: id -> name, definition,
# aliases; P54) and the closed relation vocabulary (vocab.RELATIONS)
MECHANISMS = _MECH


def variables_ok(s):
    """'a;b' of entry ids (quantities) or mechanism ids -> list of problems."""
    return [t for t in s.split(";") if t and not (t in QUANTITIES and t != "other") and t not in MECHANISMS]   # a claim's stance, from the paper's own wording ("likely", "may" -> hedged;
#   "cannot be excluded", "further work" -> open; a stated shortcoming of the study or method -> limitation)
#   asserted: stated as a finding, without hedging words (P143b)
# tree rows (stage 3): the paper, activities (something done, with settings: kind from ACTIVITY_KINDS, order when several apply to one
# entity, how stated or inferred) and entities (a physical thing or its state: a specimen, a piece cut from it, a position, a model
# run; how stated or inferred). The tree is physical provenance only: paper -> recipe -> deposition -> entity -> later activities ->
# facts. The authors' comparison intent is a fact of type comparison (kind, the varied quantity, links = purpose + members), not a parent.
NODE_TYPES = ["paper", "activity", "entity"]
ACTIVITY_KINDS = ["recipe", "deposition", "anneal", "plasma_treatment", "measurement", "simulation"]
COMPARISON_KINDS = ["series", "grid", "replicate"]
# P148: the record types, the NK reasons and the equation rule (moved from kb/extract/pass1_elements.py RULES, text unchanged); CODEBOOK.md
# reads them (ontology/export.py), the pass-1 prompt carries them through the codebook only
RECORD_TYPES = {
    "setting": "a condition the authors chose, including the measurement setup (objective, resolution, scan length, precision).",
    "observation": "a measured result on a specimen.",
    "derived": "a number the authors computed from their data (fit parameters, values derived in a table).",
    "model": "an equation or a model statement; quantity = what the equation gives, variables = its symbols. An equation is a model, not "
             "a definition.",
    "definition": "a symbol or term the paper defines; term = the symbol as printed, quantity = the entry it stands for when one exists.",
    "claim": "a causal statement or an interpretation of results, with cause and effect (ids of the cause/effect enum), relation and "
             "stance; see the claim example below. An abstract, introduction or conclusion paragraph that states a result or an "
             "interpretation is a claim, never NK.",
    "caveat": "a limitation or assumption the authors state about their own method or data (not a claim).",
    "cited": "a value or statement the paper attributes to another work (not a setting).",
}
NK_REASONS = {
    "boilerplate": "headings, author lines, acknowledgements",
    "citation_line": "a reference-list entry",
    "duplicate": "a statement already recorded from another element (duplicate_of = the element id it repeats)",
    "no_knowledge": "the element states nothing the form can hold",
}
EQUATION_VARIABLES = "variables (models and definitions): each symbol -> its quantity id, or null when no id fits."   # with RECORD_TYPES["model"]
# P143b (user-approved): the tree terms; CODEBOOK.md reads this dict (ontology/export.py)
TERMS = {
    "run": "one deposition the paper performs. A run exists where the paper STATES a deposition — in the experimental section, a caption "
           "(\"deposited at … using … cycles\", \"films grown on glassy carbon\"), a table row, a grid point. A stated deposition is a run even "
           "when no data of it is in the figures; data without a stated deposition is not a run. Specimens coated together share one run; "
           "separate depositions are separate runs even with the same chemistry, temperature and structure.",   # P146 (user)
    "specimen": "one physical sample that is measured (a coated structure, a film, a substrate piece); it comes from one run.",
    "input entity": "a thing that exists before any deposition (a substrate, a porous body), placed under the recipe and named in a "
                    "deposition activity's inputs.",
    "simulation": "one model. The paper's own model and a model it compares against are separate simulations.",   # P146 (user)
    "model run": "one set of inputs of a simulation whose result the paper reports. Two solution methods or approximations of the same "
                 "inputs are one model run.",   # P146 (user)
    "fitted or simulated curve of a specimen": "a curve fitted or simulated to match a measured specimen is a result of that specimen, "
                                                "not a model run.",   # P145
    "series / replicate / grid (comparisons)": "never a parent and never asked of the extractor; the compiler derives them from the "
        "condition vectors of the experiment units — series: members differ in exactly one quantity; replicate: in none; grid: in two. "
        "A name the authors give such a set (\"Series A\") is kept as its label.",
}
HOW = ["stated", "inferred"]
DATA_KINDS = list(KINDS)                              # the stored kinds (vocab.KINDS, Sec. 18.5); the phrases are vocab.PHRASES


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
UNITS = {"body_thickness": "mm", "body_diameter": "mm", "particle_diameter": "nm", "specific_surface_area": "m2/g", "deposition_temperature": "°C", "source_temperature": "°C", "pulse_time": "s", "purge_time": "s", "cycle_time": "s",
         "process_pressure": "Pa", "partial_pressure": "Pa", "exposure": "Pa s", "film_thickness": "nm", "feature_width": "nm",
         "feature_depth": "nm", "distance": "µm", "penetration_depth": "µm", "growth_per_cycle": "Å/cycle", "gas_flow_rate": "sccm",
         "resistivity": "Ω cm", "film_density": "g/cm3", "element_fraction": "at. %", "element_ratio": "", "phase_fraction": "wt%", "mean_free_path": "µm", "cycle_number": "", "aspect_ratio": "",
         "coated_aspect_ratio": "", "equivalent_aspect_ratio": "", "initial_sticking_coefficient": "",
         "recombination_probability": "", "knudsen_number": "", "normalized_thickness": "", "dimensionless_distance": "",
         "step_coverage": "%", "saturation_density": "nm-2", "plasma_gas_ratio": "", "mass_gain": "%", "porosity": "%",
         "crystallite_size": "nm", "gas_moles_per_cycle": "µmol", "deposited_moles_per_cycle": "µmol", "pressure_rise": "Torr",
         "pressure_rate": "mTorr/min", "time_to_maximum": "min", "roughness": "nm", "binding_energy": "eV", "atoms_per_cycle": "nm-2",
         "carrier_density": "cm-3", "mobility": "cm2/Vs", "objective_magnification": "", "fit_r2": "", "fill_fraction": "%",
         "signal_intensity": "", "reaction_stoichiometry": "", "annealing_temperature": "°C", "raman_shift": "cm-1",
         "sheet_resistance": "Ω/sq", "h_per_metal": "", "density_relative_to_bulk": "%",
         "moles_deposited": "mmol", "moles_from_mass_gain": "mmol", "shell_volume_fraction": "%", "deposition_rate": "nm/h", "coating_mass_fraction": "%"}

# unit normalisation: spellings the facts use for one unit, and every unit's dimension and factor to that dimension's base unit;
# convert() turns a value from one unit into another of the same dimension (°C and K by offset)
# P122: the unit tables are generated by ontology/export.py from ontology/units.yaml (vocab.UNIT_BASE: spelling -> (dimension, factor to the
# dimension's canonical unit); vocab.UNIT_ALIAS: variant -> symbol; vocab.DIMENSION_OF: dimension -> itself); never hand-edited here.
from vocab import UNIT_BASE, UNIT_ALIAS, DIMENSION_OF  # noqa: E402, F401


def convert(v, from_unit, to_unit):
    a, b = UNIT_ALIAS.get(from_unit, from_unit), UNIT_ALIAS.get(to_unit, to_unit)
    if a == b:
        return v
    if {a, b} == {"°C", "K"}:
        return v + 273.15 if b == "K" else v - 273.15
    (da, fa), (db, fb) = UNIT_BASE[a], UNIT_BASE[b]
    if DIMENSION_OF.get(da, da) != DIMENSION_OF.get(db, db):                    # P136 2b: length_per_cycle converts with length
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
def _in(name, q, quals="", unit="", pick=None, default=None, all=False, scope="entity", basis=None):
    return dict(name=name, q=q, quals=quals, unit=unit, pick=pick, default=default, all=all, scope=scope, basis=basis)


# a fraction stated on one basis expressed on another (P4): {quantity: {(from, to): f}} on fractions (0.284, not 28.4 %). An input
# that names a basis takes a fact of another basis through f; a fact whose basis is not_stated gives one reading per basis listed.
BASIS = {"mass_gain": {("initial_mass", "initial_mass"): lambda x: x, ("final_mass", "initial_mass"): lambda x: x / (1 - x)}}


DERIVED = {
    "feature_width{stage=final}": dict(unit="nm", qualifiers="stage=final", formula="H − 2·S_IIb: the design height minus twice the plateau thickness, the channel height at the end of the run",
                                     inputs=[_in("H", "feature_width", "", "nm"), _in("S", "film_thickness", "position=plateau", "nm")], fn=lambda H, S: H - 2 * S),
    "exposure": dict(unit="Torr s", formula="partial pressure of reactant A × its pulse time",
                     inputs=[_in("p", "partial_pressure", "step=reactant_A", "Torr"), _in("t", "pulse_time", "step=reactant_A", "s")], fn=lambda p, t: p * t),
    "exposure{over=run}": dict(unit="Torr s", qualifiers="over=run", formula="exposure per pulse × cycle number",
                             inputs=[_in("E", "exposure", "", "Torr s"), _in("N", "cycle_number", "", "")], fn=lambda E, N: E * N),
    "sheet_resistance": dict(unit="Ω/sq", formula="resistivity / film thickness",
                             inputs=[_in("rho", "resistivity", "", "Ω cm"), _in("t", "film_thickness", "", "cm")], fn=lambda rho, t: rho / t),
    "growth_per_cycle": dict(unit="nm/cycle", qualifiers="over=run", formula="atoms per cycle × M / (ρ N_A): the thickness the deposited metal atoms make at the film's density",
                             inputs=[_in("n", "atoms_per_cycle", "", "nm-2"), _in("M", "other:molar mass", "species=@material", "g/mol"), _in("rho", "film_density", "", "g/cm3"),
                                     _in("NA", "other:Avogadro constant", "", "1/mol")], fn=lambda n, M, rho, NA: n * M / (NA * rho * 1e-21)),
    "atoms_per_cycle": dict(unit="nm-2", qualifiers="over=run", formula="GPC × ρ N_A / M × metal atoms per formula unit: metal atoms per nm² per cycle at the film's own density",
                            inputs=[_in("gpc", "growth_per_cycle", "", "nm/cycle", pick=["", "position=plateau"]), _in("rho", "film_density", "", "g/cm3"),
                                    _in("M", "other:molar mass", "species=@material", "g/mol"), _in("NA", "other:Avogadro constant", "", "1/mol"),
                                    _in("b", "@formula_metals")],
                            fn=lambda gpc, rho, M, NA, b: gpc * rho * 1e-21 * NA / M * b),
    "element_ratio{element=H;reference_element=Mo}": dict(unit="", qualifiers="element=H;reference_element=Mo", formula="H at.% / Mo at.%, with Mo at.% = (100 − H − N − O at.%) / (1 + S/Mo)",
                        inputs=[_in("H", "element_fraction", "element=H", "%"), _in("SMo", "element_ratio", "element=S;reference_element=Mo", ""), _in("N", "element_fraction", "element=N", "%", default=0),
                                _in("O", "element_fraction", "element=O", "%", default=0)], fn=lambda H, SMo, N, O: H / ((100 - H - N - O) / (1 + SMo))),
    "density_relative_to_bulk": dict(unit="%", formula="film density / bulk density",
                                     inputs=[_in("rho", "film_density", "", "g/cm3"), _in("rb", "film_density", "reference=bulk;species=@material", "g/cm3", scope="paper")], fn=lambda rho, rb: 100 * rho / rb),
    "moles_deposited": dict(unit="mmol", formula="Δn_s per cycle × cycle number",
                            inputs=[_in("dn", "deposited_moles_per_cycle", "", "mmol"), _in("N", "cycle_number", "", "")], fn=lambda dn, N: dn * N),
    "moles_from_mass_gain": dict(unit="mmol", formula="mass gain × powder mass per compact × compacts per run / M",
                                 inputs=[_in("mg", "mass_gain", "", "", basis="initial_mass"), _in("m0", "other:powder mass", "", "g"), _in("k", "other:NPCs per run", "", ""),
                                         _in("M", "other:molar mass", "species=@material", "g/mol")], fn=lambda mg, m0, k, M: 1000 * mg * m0 * k / M),
    "growth_per_cycle{kind=target;over=run}": dict(unit="nm", qualifiers="kind=target;over=run", formula="thickness target / cycles: the growth per cycle the chosen cycle count implies",
                                    inputs=[_in("t", "film_thickness", "kind=target", "nm"), _in("N", "cycle_number", "", "")], fn=lambda t, N: t / N),
    "plasma_gas_ratio{gas=h2;relative_to=all_gases}": dict(unit="%", qualifiers="gas=h2;relative_to=all_gases", formula="H2 flow / (H2S + H2 + Ar flow): the H2 share of the whole plasma feed",
                               inputs=[_in("h2", "gas_flow_rate", "gas=h2;step=plasma", "sccm"), _in("h2s", "gas_flow_rate", "gas=h2s;step=plasma", "sccm"),
                                       _in("ar", "gas_flow_rate", "gas=ar;step=plasma", "sccm")], fn=lambda h2, h2s, ar: 100 * h2 / (h2 + h2s + ar)),
    "coating_mass_fraction": dict(unit="%", formula="the coating's share of the coated sample's mass: mass gain / (1 + mass gain), mass gain relative to the initial mass",
                                  inputs=[_in("mg", "mass_gain", "", "", basis="initial_mass")], fn=lambda mg: 100 * mg / (1 + mg)),
    "shell_volume_fraction": dict(unit="%", formula="(1 − φ_i) × ((d_NP + 2 t)³ / d_NP³ − 1): the coating's share of the compact volume, spherical particles",
                                  inputs=[_in("phi", "porosity", "stage=initial", ""), _in("d", "particle_diameter", "", "nm"), _in("t", "film_thickness", "", "nm")],
                                  fn=lambda phi, d, t: 100 * (1 - phi) * ((d + 2 * t) ** 3 / d ** 3 - 1)),
    "mean_free_path": dict(unit="µm", formula="k_B T / (√2 π d² p) for reactant A at the deposition temperature and its partial pressure",
                           inputs=[_in("T", "deposition_temperature", "", "K"), _in("p", "partial_pressure", "", "Pa", pick=["", "step=reactant_A"]),
                                   _in("d", "other:molecular diameter", "species=@A", "nm"), _in("kB", "other:Boltzmann constant", "", "J/K")],
                           fn=lambda T, p, d, kB: 1e6 * kB * T / (2 ** 0.5 * 3.141592653589793 * (d * 1e-9) ** 2 * p)),
    "knudsen_number": dict(unit="", formula="mean free path / characteristic size (the hydraulic diameter, the pore or particle diameter, the feature width)",
                           inputs=[_in("lam", "mean_free_path", "", "µm"), _in("h", "other:hydraulic diameter h|particle_diameter|feature_width", "", "µm")], fn=lambda lam, h: lam / h),
    "cycle_time": dict(unit="s", formula="the sum of the pulse, hold and purge times of one cycle",
                       inputs=[_in("t", "pulse_time|purge_time|other:DEZ hold|other:H2O hold", "", "s", all=True)], fn=lambda t: sum(t)),
    "deposition_rate": dict(unit="nm/h", formula="GPC × 3600 / cycle time",
                            inputs=[_in("gpc", "growth_per_cycle", "", "nm/cycle", pick=["", "position=plateau"]), _in("tc", "cycle_time", "", "s")], fn=lambda gpc, tc: gpc * 3600 / tc),
}


def derived_key(k):
    """A DERIVED key split into (quantity id, {qualifier: value}): 'exposure{over=run}' -> ('exposure', {'over': 'run'})."""
    q, _, rest = k.partition("{")
    return q, dict(p.split("=", 1) for p in rest.rstrip("}").split(";") if "=" in p)


assert all(derived_key(k)[0] in QUANTITIES for k in DERIVED), "DERIVED key not a quantity id"
assert all(derived_key(k)[1].items() <= dict(p.split("=", 1) for p in D.get("qualifiers", "").split(";") if "=" in p).items() for k, D in DERIVED.items()), \
    "a DERIVED key's qualifiers are not among its definition's"

# short display labels, used by every screen: one per quantity id, and one per common quantity{qualifiers} combination
# (qualifiers written as in the facts, without x=). A combination not listed shows the quantity's label followed by the
# qualifier values ("composition S", "BE Mo"); a curve shows "<y label> vs <x label>".
LABELS = {**_LABELS, "other": "other",   # the id labels come from the ontology (vocab.py); the combinations below are display rules of the screen
    "pulse_time{step=reactant_A;species=tma}": "TMA pulse", "pulse_time{step=reactant_B;species=h2o}": "H2O pulse",
    "pulse_time{step=reactant_A;species=dez}": "DEZ pulse", "pulse_time{step=reactant_A}": "pulse A", "pulse_time{step=plasma}": "plasma step",
    "purge_time{step=purge_A}": "purge A", "purge_time{step=purge_B}": "purge B",
    "deposition_temperature{kind=set_point}": "T set point", "deposition_temperature{step=reactant_A}": "T (A dose)",
    "deposition_temperature{step=purge_A}": "T (purge A)", "deposition_temperature{step=reactant_B}": "T (B dose)",
    "deposition_temperature{step=purge_B}": "T (purge B)",
    "coated_aspect_ratio{basis=AR}": "x̃50", "penetration_depth{level=50%;origin=entrance}": "PD50",
    "penetration_depth{origin=entrance}": "PD", "front_slope{by=H}": "slope d(S/N)/dx̃", "front_slope{by=H;reference=entrance}": "slope dθ/dx̃",
    "film_thickness{position=plateau}": "S_plateau", "film_thickness{position=outside}": "S_outside", "film_thickness{position=interface}": "S_interface",
    "growth_per_cycle{position=plateau}": "GPC_plateau", "growth_per_cycle{position=outside}": "GPC_outside",
    "normalized_thickness{reference=entrance}": "S/S_entry", "plasma_gas_ratio{gas=h2;relative_to=reactive_gases}": "H2 ratio", "plasma_gas_ratio{gas=h2;relative_to=all_gases}": "H2 share of feed",
    "feature_width{stage=final}": "H_eff", "exposure{over=run}": "exposure per run", "growth_per_cycle{kind=target;over=run}": "GPC target",
    "gas_flow_rate{step=plasma;gas=h2s}": "H2S flow", "gas_flow_rate{step=plasma;gas=h2}": "H2 flow", "gas_flow_rate{step=plasma;gas=ar}": "Ar flow (plasma)",
    "gas_flow_rate{gas=n2}": "N2 flow", "gas_flow_rate{gas=ar}": "Ar purge flow", "gas_flow_rate{gas=ar;step=reactant_A}": "Ar carrier flow",
    "process_pressure{step=plasma}": "p (plasma)", "process_pressure{step=reactant_A;kind=set_point}": "p set point (A)",
    "initial_sticking_coefficient{species=tma}": "c_TMA", "initial_sticking_coefficient{species=h2o}": "c_H2O",
    "porosity{stage=initial}": "φ_i", "porosity{stage=final}": "φ_f", "pressure_rise{level=maximum}": "δp_max", "element_ratio{element=S;reference_element=Mo}": "S/Mo", "element_ratio{element=S;reference_element=W}": "S/W",
    "element_ratio{element=H;reference_element=Mo}": "H per Mo",
    }
assert all(k.split("{")[0] in QUANTITIES for k in LABELS), "LABELS key not a quantity id"
assert all(q in LABELS for q in QUANTITIES), "quantity without a label"

# plain English names for the screen (no symbol that needs a legend): one per quantity id and per common keyed combination; a key not
# listed reads "<quantity name> (<qualifier values>)"
NAMES = {**_NAMES, "other": "other",
    "pulse_time{species=tma;step=reactant_A}": "TMA pulse", "pulse_time{species=h2o;step=reactant_B}": "water pulse",
    "pulse_time{species=dez;step=reactant_A}": "DEZ pulse", "pulse_time{step=reactant_A}": "precursor pulse", "pulse_time{step=plasma}": "plasma step",
    "purge_time{step=purge_A}": "purge after precursor", "purge_time{step=purge_B}": "purge after co-reactant",
    "deposition_temperature{kind=set_point}": "temperature set point", "deposition_temperature{step=reactant_A}": "temperature in the precursor dose",
    "deposition_temperature{step=purge_A}": "temperature in the precursor purge", "deposition_temperature{step=reactant_B}": "temperature in the water dose",
    "deposition_temperature{step=purge_B}": "temperature in the water purge",
    "coated_aspect_ratio{basis=AR}": "coated aspect ratio (half-thickness depth over height)", "penetration_depth{level=50%;origin=entrance}": "penetration depth at 50 %",
    "penetration_depth{origin=entrance}": "penetration depth", "front_slope{by=H}": "front slope of S/N", "front_slope{by=H;reference=entrance}": "front slope, normalized",
    "film_thickness{position=plateau}": "thickness in the channel", "film_thickness{position=outside}": "thickness outside the channel",
    "film_thickness{position=interface}": "interface layer thickness", "film_thickness{kind=target}": "thickness target",
    "growth_per_cycle{over=run;position=plateau}": "growth per cycle in the channel", "growth_per_cycle{over=run;position=outside}": "growth per cycle outside the channel",
    "plasma_gas_ratio{gas=h2;relative_to=reactive_gases}": "H2 flow ratio", "plasma_gas_ratio{gas=h2;relative_to=all_gases}": "H2 share of the plasma feed",
    "feature_width{stage=final}": "effective channel height", "exposure{over=run}": "exposure per run", "growth_per_cycle{kind=target;over=run}": "growth per cycle implied by the thickness target",
    "gas_flow_rate{gas=h2s;step=plasma}": "H2S flow", "gas_flow_rate{gas=h2;step=plasma}": "H2 flow", "gas_flow_rate{gas=ar;step=plasma}": "Ar flow in the plasma",
    "gas_flow_rate{gas=n2}": "N2 flow", "gas_flow_rate{gas=ar}": "Ar purge flow", "gas_flow_rate{gas=ar;step=reactant_A}": "Ar carrier flow",
    "initial_sticking_coefficient{species=tma}": "TMA sticking coefficient",
    "initial_sticking_coefficient{species=h2o}": "water sticking coefficient", "porosity{relative_to=total_volume;stage=initial}": "initial porosity",
    "porosity{relative_to=total_volume;stage=final}": "final porosity", "pressure_rise{level=maximum}": "maximum pressure rise",
    "element_ratio{element=S;reference_element=Mo}": "S/Mo", "element_ratio{element=S;reference_element=W}": "S/W", "element_ratio{element=H;reference_element=Mo}": "H per Mo atom",
    "element_fraction{element=H}": "H content", "element_fraction{element=N}": "N content", "element_fraction{element=O}": "O content",
    "element_fraction{element=C}": "C content", "phase_fraction{phase=zno;relative_to=not_stated}": "ZnO content (XRD)",
    "phase_fraction{phase=zn;relative_to=not_stated}": "Zn content (XRD)", "atoms_per_cycle{element=Mo;over=run;relative_to=all_atoms}": "Mo atoms per cycle",
    "atoms_per_cycle{element=Mo;over=run}": "Mo atoms per cycle", "crystallite_size{species=zno}": "ZnO crystallite size", "crystallite_size{species=zn}": "Zn crystallite size",
    "precursor_purity{species=h2s}": "H2S purity", "precursor_purity{species=h2}": "H2 purity", "precursor_purity{species=ar}": "Ar purity",
    "precursor_purity{species=dez}": "DEZ purity", "process_pressure{kind=set_point;step=reactant_A}": "pressure set point in the dose",
}
# words for a definition that is not the default (P5, P4, P18): shown beside a value only then
DEF_WORDS = {("over", "first_100_cycles"): "averaged over the first 100 cycles", ("over", "saturation"): "saturation value",
             ("over", "not_stated"): "averaging not stated", ("relative_to", "not_stated"): "basis not stated",
             ("relative_to", "initial_mass"): "relative to the initial mass", ("relative_to", "final_mass"): "relative to the final mass",
             ("relative_to", "crystalline_phases"): "of the crystalline phases", ("relative_to", "reactive_gases"): "of the reactive feed gases", ("relative_to", "all_gases"): "of the whole plasma feed", ("kind", "target"): "target", ("kind", "set_point"): "set point", ("kind", "estimated"): "estimated by the paper",
             ("reference", "bulk"): "bulk value", ("mode", "in_situ"): "in situ", ("mode", "ex_situ"): "ex situ"}
# the provenance words of a value (P57): only the phrase table of the ontology (vocab.PHRASES); a screen leaves measured and stated
# values unmarked (UNMARKED) and marks every other kind with its phrase
UNMARKED = {"measured", "stated"}

# P99: an element word alone names an element, never a gas species ("oxygen" -> O, the element qualifier's business); the molecule
# needs its formula (O2) or a gas phrase ("oxygen gas", "hydrogen plasma" -> h2, the plasma being the process); a supplier's name
# in a purity phrase ("Air Liquide") is no species.
ELEMENT_WORDS = {"oxygen": "O", "hydrogen": "H", "nitrogen": "N", "sulfur": "S", "sulphur": "S", "chlorine": "Cl", "fluorine": "F"}
GAS_WORDS = {"gas", "gases", "plasma", "molecule", "molecules", "flow", "atmosphere", "ambient", "carrier"}
MOLECULAR_WORDS = {"molecular", "diatomic"}
SUPPLIERS = ["Air Liquide", "Air Products", "Strem Chemicals", "Strem", "Sigma-Aldrich", "Sigma Aldrich", "Linde", "Praxair", "Matheson", "Messer",
             "Pegasus Chemicals", "Dockweiler", "Alfa Aesar", "Merck", "Westfalen", "Nippon Sanso", "Taiyo Nippon Sanso"]
SUPPLIER_RX = re.compile(r"\b(" + "|".join(re.escape(x) for x in sorted(SUPPLIERS, key=len, reverse=True)) + r")\b", re.I)


def element_word(word, before="", after=""):
    """('element', symbol) for a bare element word, ('species', id) when a gas word follows or 'molecular' precedes it and the
    diatomic molecule is a species of the ontology, else None (not an element word)."""
    w = str(word).strip().lower()
    if w not in ELEMENT_WORDS:
        return None
    sym = ELEMENT_WORDS[w]
    if str(after).strip().lower().rstrip(".,;:)") in GAS_WORDS or str(before).strip().lower() in MOLECULAR_WORDS:
        sid = next((i for i, s in SPECIES.items() if s["formula"] == sym + "2"), "")
        if sid:
            return ("species", sid)
    return ("element", sym)
KIND_WORDS = {k: p for k, p in PHRASES.items() if k not in UNMARKED}
assert set(KIND_WORDS) | UNMARKED == set(KINDS), "a kind without a phrase"

