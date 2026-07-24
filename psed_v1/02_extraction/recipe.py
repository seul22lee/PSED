"""
recipe.py  (M0 + Argonne-interop refinements)
---------------------------------------------
The Recipe object — the bridge between the KB, the LLM agent, and the MPC twin
(INTEGRATION_STRATEGY.md §2.1). A Recipe is the actionable ALD process spec:
material, reactants (A/B/C/D with roles: precursor | coreactant | inhibitor),
cycle sequence (generalising to ABC / ABAC supercycles), ncycles, temperature,
geometry, and control targets — plus completeness + provenance.

Argonne interop (RSI 2026 SI): a Recipe resolves against a reactor channel list
and serialises to / parses from their answer JSON:
  single:     {"possible":1,"precursor":ch,"coreactant":ch,"ncycles":n}
  supercycle: {"possible":1,"sequence":[{precursor,coreactant,ncycles}],"supercycles":N}
  inhibitor:  {"possible":1,"inhibitor":ch,"ncycles":n}  (standalone or +precursor/coreactant)
  impossible: {"possible":0}
Channels are 1-indexed (channel 1 = channels[0]).
"""
import json as _json
from pathlib import Path as _Path
from dataclasses import dataclass, field, asdict

# quantity -> recipe_role (control_setting = in the recipe; else structure /
# species_property / model_parameter / derived / observable / coordinate)
_ONTO = _json.loads((_Path(__file__).parent.parent / "01_ontology" / "ald_ontology.json").read_text())
RECIPE_ROLE = {q["id"]: q.get("recipe_role") for q in _ONTO["quantity_kinds"]}


def partition_conditions(exp):
    """Group an experiment's controlled conditions by recipe_role — so 'what is
    the recipe' vs 'what is the sample / a model fit / a derived value' is explicit."""
    groups = {}
    for c in exp.get("controlled") or []:
        role = RECIPE_ROLE.get(c.get("quantity")) or "other"
        groups.setdefault(role, []).append(c)
    return groups

# species  <->  reactor-channel-name normalisation (from the SI background list)
ALIAS = {
    "water": "water", "h2o": "water",
    "tma": "tma", "trimethylaluminum": "tma", "al(ch3)3": "tma", "almе3": "tma",
    "dez": "dez", "diethylzinc": "dez", "zn(c2h5)2": "dez",
    "tdmahf": "tdmahf", "tetrakis dimethylamino hafnium": "tdmahf",
    "ticl4": "ticl4", "titanium tetrachloride": "ticl4",
    "ttip": "ttip", "titanium tetraisopropoxide": "ttip",
    "wf6": "wf6", "tungsten hexafluoride": "wf6",
    "si2h6": "si2h6", "disilane": "si2h6",
    "mgcp2": "mgcp2", "dmai": "dmai", "dimethylaluminum isopropoxide": "dmai",
    "hacac": "hacac", "dmadms": "dmadms", "o2": "o2", "oxygen": "o2",
    "h2s": "h2s", "hydrogen sulfide": "h2s", "mof6": "mof6",
}


def _norm(s):
    if not s:
        return None
    t = str(s).strip().lower()
    return ALIAS.get(t, t)


@dataclass
class Reactant:
    label: str                       # A, B, C, D …
    role: str                        # precursor | coreactant | inhibitor | reactant
    species: str = None
    dose_time: float = None
    purge_time: float = None
    partial_pressure: float = None


@dataclass
class Recipe:
    material: str = None
    reactants: list = field(default_factory=list)
    cycle_sequence: str = None                     # "AB", "ABC", "ABAC"…
    supercycle: list = None                        # [{"precursor":lbl,"coreactant":lbl,"n":int}] | None
    supercycle_repeats: int = None                 # total supercycles
    ncycles: int = None                            # simple (non-super) process
    temperature: float = None                       # deposition temperature (°C)
    flow_rate: float = None                         # carrier/total gas flow (sccm)
    carrier_gas: dict = None                        # {species, flow_sccm} — background gas, not a cycle reactant
    structure: dict = None
    targets: dict = None
    provenance: str = "extracted"
    possible: bool = None                          # compatible with a given reactor config
    channel_map: dict = None                       # {label: channel_number}
    param_sources: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    # ---- completeness ----
    FIELDS = ["material", "reactants", "cycle_sequence", "ncycles", "temperature", "flow_rate"]
    REACTANT_FIELDS = ["species", "dose_time", "purge_time", "partial_pressure"]

    def completeness(self):
        have = sum(bool(getattr(self, f)) for f in self.FIELDS)
        rtot = rhave = 0
        for r in self.reactants:
            for rf in self.REACTANT_FIELDS:
                rtot += 1
                rhave += getattr(r, rf) is not None
        denom = len(self.FIELDS) + rtot
        return round((have + rhave) / denom, 3) if denom else 0.0

    def validate(self):
        p = []
        if not self.material and not self.reactants:
            p.append("empty recipe")
        labs = [r.label for r in self.reactants]
        if self.cycle_sequence and any(c not in labs for c in set(self.cycle_sequence)):
            p.append(f"cycle_sequence {self.cycle_sequence} uses labels not in {labs}")
        return p

    def role(self, role):
        return next((r for r in self.reactants if r.role == role), None)


# ---- channel resolution against a reactor config ----
def resolve_channels(recipe, channels):
    """Map each reactant species to a 1-indexed channel and set `possible`."""
    idx = {}
    for i, ch in enumerate(channels):
        idx[_norm(ch)] = i + 1
    cmap, ok = {}, True
    for r in recipe.reactants:
        ch = idx.get(_norm(r.species))
        cmap[r.label] = ch
        if ch is None:
            ok = False
    recipe.channel_map = cmap
    recipe.possible = ok
    return cmap, ok


# ---- Argonne JSON: recipe -> their answer process dict ----
def to_process(recipe):
    if recipe.possible is False:
        return {"possible": 0}
    cm = recipe.channel_map or {}
    if recipe.supercycle:
        seq = [{"precursor": cm.get(b["precursor"]), "coreactant": cm.get(b["coreactant"]),
                "ncycles": b["n"]} for b in recipe.supercycle]
        return {"possible": 1, "sequence": seq, "supercycles": recipe.supercycle_repeats}
    d = {"possible": 1}
    inh, prec, core = recipe.role("inhibitor"), recipe.role("precursor"), recipe.role("coreactant")
    if inh:
        d["inhibitor"] = cm.get(inh.label)
    if prec:
        d["precursor"] = cm.get(prec.label)
    if core:
        d["coreactant"] = cm.get(core.label)
    if recipe.ncycles is not None:
        d["ncycles"] = int(recipe.ncycles)
    return d


def to_argonne_json(recipes):
    """A query answer is a list of processes."""
    if isinstance(recipes, Recipe):
        recipes = [recipes]
    return [to_process(r) for r in recipes]


# ---- Argonne JSON: their answer process dict -> recipe ----
def from_process(process, channels):
    def sp(ch):
        return channels[ch - 1] if isinstance(ch, int) and 1 <= ch <= len(channels) else None
    if process.get("possible", 1) == 0:
        return Recipe(possible=False, provenance="agent")
    reactants, labels = [], iter("ABCDEFGH")
    if "sequence" in process:                       # supercycle
        blk, spmap = [], {}
        for e in process["sequence"]:
            for role, ch in (("precursor", e.get("precursor")), ("coreactant", e.get("coreactant"))):
                s = sp(ch)
                if s and s not in spmap:
                    lab = next(labels)
                    spmap[s] = lab
                    reactants.append(Reactant(lab, role, s))
            blk.append({"precursor": spmap.get(sp(e.get("precursor"))),
                        "coreactant": spmap.get(sp(e.get("coreactant"))), "n": e.get("ncycles")})
        return Recipe(reactants=reactants, supercycle=blk,
                      supercycle_repeats=process.get("supercycles"), provenance="agent")
    for role in ("inhibitor", "precursor", "coreactant"):
        if role in process:
            reactants.append(Reactant(next(labels), role, sp(process[role])))
    seq = "".join(r.label for r in reactants if r.role != "inhibitor")
    return Recipe(reactants=reactants, cycle_sequence=seq or None,
                  ncycles=process.get("ncycles"), provenance="agent")


# ---- lift a resolved KB experiment into a (partial) Recipe ----
def _cond(exp, quantity, reactant=None):
    for c in exp.get("controlled") or []:
        if c.get("quantity") == quantity and (reactant is None or c.get("of_reactant") == reactant):
            return c.get("value")
    return None


# ---- provenance: recorded where the value is chosen, never inferred from it ----
# One vocabulary, two axes:
#   source : paper | experiment | derived | kb | model   (which LEVEL supplied it)
#   from   : methods_prose | table | caption | series | degenerate_range | scout |
#            experiment_record | kb_imputation | model_default | unknown
# `experiment_record` covers the recipe fields carried on the experiment itself
# (material, cycle_sequence, reactants, species) rather than by a controlled condition.
# `unknown` exists because cards built before this layer recorded no per-field origin;
# claiming methods_prose for them would be a fabrication (see 06_to_kb §8 backfill).
PARAM_SOURCES = ("paper", "experiment", "derived", "kb", "model")
PARAM_FROM = ("methods_prose", "table", "caption", "series", "degenerate_range",
              "experiment_record", "scout", "kb_imputation", "model_default", "unknown")

# card provenance origin -> (param source, param from)
_CARD_ORIGIN = {"methods_prose": ("paper", "methods_prose"),
                "table": ("paper", "table"),
                "derived": ("derived", "degenerate_range"),
                "scout": ("paper", "scout"),
                "scout_window": ("paper", "unknown"),
                "unknown": ("paper", "unknown")}


def _param_source(exp, c):
    """Translate a controlled condition's own recorded origin into a recipe-level
    param_sources entry. Reads `origin`/`source` off the condition — the numeric value
    is never consulted."""
    o = c.get("origin") or {}
    label = c.get("source")
    if label == "methods" or o.get("level") == "paper":
        cp = o.get("card_provenance") or {}
        src, frm = _CARD_ORIGIN.get(cp.get("origin"), ("paper", "unknown"))
        m = {"source": src, "from": frm, "value": c.get("value"),
             "paper_id": exp.get("_pid"), "card_field": o.get("card_field")}
        if cp.get("evidence"):
            m["ref"] = cp["evidence"]
        if cp.get("transformation"):
            m["transformation"] = cp["transformation"]
        return m
    if label in ("caption", "series"):
        m = {"source": "experiment", "from": label, "value": c.get("value"),
             "paper_id": o.get("paper_id") or exp.get("_pid"),
             "experiment_id": o.get("experiment_id") or exp.get("exp_id")}
        for k in ("figure", "panel"):
            if o.get(k):
                m[k] = o[k]
        return m
    return {"source": "experiment", "from": "unknown", "value": c.get("value"),
            "experiment_id": exp.get("exp_id")}


def _cond_meta(exp, quantity, reactant=None):
    """(value, param_sources entry) for the first matching condition — the same
    selection `_cond` makes, with the origin it carried. `_cond` is untouched."""
    for c in exp.get("controlled") or []:
        if c.get("quantity") == quantity and (reactant is None or c.get("of_reactant") == reactant):
            return c.get("value"), _param_source(exp, c)
    return None, None


def _first(*pairs):
    """First truthy value — mirrors the existing `_cond(..) or _cond(..)` chain exactly,
    including its fall-through to the LAST candidate when none is truthy."""
    for v, m in pairs:
        if v:
            return v, m
    return pairs[-1]


def from_experiment(exp):
    src = {"_exp_id": exp.get("exp_id")}

    def take(key, *pairs):
        v, m = _first(*pairs)
        if v is not None and m is not None:
            src[key] = m
        return v

    reactants = []
    for r in exp.get("reactants") or []:
        lab = r["label"]
        if r.get("species"):
            src[f"species::{lab}"] = {"source": "experiment", "from": "experiment_record",
                                      "value": r.get("species"), "experiment_id": exp.get("exp_id")}
        reactants.append(Reactant(
            label=lab, role=r.get("role"), species=r.get("species"),
            dose_time=take(f"pulse_time::{lab}",
                           _cond_meta(exp, "pulse_time", lab), _cond_meta(exp, "pulse_time")),
            purge_time=take(f"purge_time::{lab}",
                            _cond_meta(exp, "purge_time", lab), _cond_meta(exp, "purge_time")),
            partial_pressure=take(f"partial_pressure::{lab}",
                                  _cond_meta(exp, f"reactant_{lab}_partial_pressure"),
                                  _cond_meta(exp, "partial_pressure", lab))))
    H, W = _cond(exp, "feature_height"), _cond(exp, "feature_width")
    meas = (exp.get("measurand") or {}).get("quantity")
    targets = {}
    if _cond(exp, "growth_per_cycle"):
        targets["gpc_sat"] = _cond(exp, "growth_per_cycle")
    if meas == "penetration_depth":
        targets["penetration_depth"] = "measured-in-figure"
    # `reactants` is itself one of Recipe.FIELDS (the roster, distinct from the per-reactant
    # species/timing fields), so it needs its own entry or the accounting under-counts by
    # exactly one field per recipe.
    for f, v in (("material", exp.get("material")), ("cycle_sequence", exp.get("cycle_sequence")),
                 ("reactants", [r.label for r in reactants] or None)):
        if v:
            src[f"{f}::"] = {"source": "experiment", "from": "experiment_record",
                             "value": v, "experiment_id": exp.get("exp_id")}
    return Recipe(
        material=exp.get("material"), reactants=reactants,
        cycle_sequence=exp.get("cycle_sequence"),
        ncycles=take("cycle_number::", _cond_meta(exp, "cycle_number")),
        temperature=take("temperature::", _cond_meta(exp, "temperature"),
                         _cond_meta(exp, "deposition_temperature")),
        flow_rate=take("flow_rate::", _cond_meta(exp, "flow_rate")),
        carrier_gas=exp.get("carrier_gas"),
        structure={"H": H, "W": W} if (H or W) else None,
        targets=targets or None, provenance="extracted",
        param_sources=src)


# ---- fill missing recipe fields from the KB / model cascade -----------------
#   priority: extracted (already on the recipe) > KB inference > model default.
#   The KB inference is COVARIATE-CONDITIONED and probabilistic: `impute_fn(q, r)`
#   (built per-target from kb_service.impute) draws the value from the experiments
#   most similar to THIS one that have it, weighted by that similarity — not a
#   global median. Every filled value is tagged in param_sources with its source,
#   uncertainty, and the donor experiments it leaned on.
def fill_gaps(recipe, impute_fn, model_defaults=None):
    """impute_fn(quantity, reactant) -> {value, sd, ci_lo, ci_hi, n_eff, donors} | None
    (covariate-conditioned similarity-weighted estimate). model_defaults: optional
    {field: value} last-resort fallback. Mutates + returns the recipe."""
    md = model_defaults or {}
    src = recipe.param_sources

    def fill(getter, setter, q, r=None, mdkey=None):
        if getter() is not None:
            return                                  # extracted — keep, most authoritative
        key = q + "::" + (r or "")                  # matches the Compare-tab condition key
        rec = impute_fn(q, r)
        if rec is not None:
            setter(rec["value"])
            src[key] = {
                "source": "kb", "from": "kb_imputation", "quantity": q, "reactant": r,
                "value": rec["value"], "sd": rec.get("sd"),
                "ci": [rec.get("ci_lo"), rec.get("ci_hi")], "n_eff": rec.get("n_eff"),
                "n_donors": rec.get("n_donors"), "donors": rec.get("donors"),
                "method": rec.get("method")}
        elif mdkey and mdkey in md and md[mdkey] is not None:
            setter(md[mdkey])
            src[key] = {"source": "model", "from": "model_default",
                        "quantity": q, "reactant": r, "value": md[mdkey]}

    # process-level fields
    fill(lambda: recipe.ncycles, lambda v: setattr(recipe, "ncycles", v), "cycle_number", None, "ncycles")
    fill(lambda: recipe.temperature, lambda v: setattr(recipe, "temperature", v), "temperature", None, "T")
    fill(lambda: recipe.flow_rate, lambda v: setattr(recipe, "flow_rate", v), "flow_rate", None)
    # per-reactant timing / pressure
    for rt in recipe.reactants:
        lab = rt.label
        fill(lambda rt=rt: rt.dose_time, lambda v, rt=rt: setattr(rt, "dose_time", v), "pulse_time", lab, "t_p")
        fill(lambda rt=rt: rt.purge_time, lambda v, rt=rt: setattr(rt, "purge_time", v), "purge_time", lab)
        fill(lambda rt=rt: rt.partial_pressure, lambda v, rt=rt: setattr(rt, "partial_pressure", v),
             "partial_pressure", lab, ("pA" if lab == "A" else "pB"))
    return recipe


if __name__ == "__main__":
    import json
    print("== 1. round-trip an Argonne challenge (parse -> Recipe -> back to JSON) ==")
    # supercycle: 20× (10×DEZ/H2O + 1×TMA/H2O)  == Al-doped ZnO 9:1-ish
    chan = ["TMA", "water", "DEZ", "TDMAHf", "Si2H6", "WF6", "TTIP", "MgCp2"]
    ans = {"possible": 1, "sequence": [{"precursor": 3, "coreactant": 2, "ncycles": 10},
                                        {"precursor": 1, "coreactant": 2, "ncycles": 1}], "supercycles": 20}
    r = from_process(ans, chan)
    resolve_channels(r, chan)
    print("   parsed reactants:", [(x.label, x.role, x.species) for x in r.reactants])
    print("   back to JSON:", json.dumps(to_process(r)))
    print("   round-trip ok:", to_process(r) == ans)

    print("\n== 2. inhibitor / functionalization ==")
    inh = {"possible": 1, "inhibitor": 4, "ncycles": 1}
    ri = from_process(inh, ["DMAI", "water", "Hacac", "TDMAHf", "Si2H6", "WF6", "TTIP", "MgCp2"])
    resolve_channels(ri, ["DMAI", "water", "Hacac", "TDMAHf", "Si2H6", "WF6", "TTIP", "MgCp2"])
    print("   inhibitor recipe:", [(x.label, x.role, x.species) for x in ri.reactants], "->", to_process(ri))

    print("\n== 3. lift a KB experiment, resolve to a reactor, emit Argonne JSON ==")
    import glob
    E = []
    for f in glob.glob("output/*/resolved/experiments.json"):
        E += json.load(open(f))
    e = next(x for x in E if x.get("material") == "Al2O3" and x.get("reactants"))
    rec = from_experiment(e)
    # give the generic A/B reactants species so channel resolution can work
    if rec.reactants and not rec.reactants[0].species:
        rec.reactants[0].species, rec.reactants[1].species = "TMA", "water"
    resolve_channels(rec, chan)
    print(f"   [{e.get('exp_id')}] {rec.material} completeness={rec.completeness()} "
          f"possible={rec.possible} channels={rec.channel_map}")
    print("   Argonne JSON:", json.dumps(to_process(rec)))
