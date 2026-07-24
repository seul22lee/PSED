#!/usr/bin/env python3
"""
06_to_kb.py — Stage 4/5: methods gap-fill + resolve scout/vision records into the
0706_pipeline KB schema (output/{pid}/resolved/experiments.json), so new-chemistry
papers actually enter the KB alongside the existing corpus.

  1) methods gap-fill: ONE cheap LLM call on the methods/experimental section to fill
     ONLY the conditions the scout deferred (precursor/coreactant/T/pressure/dose/
     purge/cycles/carrier). Skipped entirely if the scout already has them.
  2) resolve: each vision figure-panel/series → an experiment record with canonical
     material/chemistry, role-tagged controlled conditions (recipe_role), measurand,
     coordinate, points, relevance (measured→experimental / simulated→model), a Recipe,
     and provenance. Written per paper.

Run with the psed310 env python.
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
PIPE = ROOT.parent / "02_extraction"
sys.path.insert(0, str(PIPE / "stages"))
sys.path.insert(0, str(PIPE))
import lib                                   # canon_*, family, recipe_role, species_prop
import recipe as recipe_mod
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
_spec = importlib.util.spec_from_file_location("ex", ROOT / "scripts" / "04_extract.py")
ex = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ex)   # section_text, _load_key

MODEL = "gemini-flash-latest"
OUT = PIPE / "output"

# light unit normalisation to KB conventions
# Feature dimensions are canonically nm in the ontology (feature_height/width are NanoM),
# so a channel width printed as "0.1 mm" and one printed as "100000 nm" must not sit in the
# KB as incomparable raw numbers. Only LENGTH units are converted here; dimensionless and
# model-parameter units (Pa^-1, m^-2) are left exactly as printed.
_LEN_TO_NM = {"nm": 1.0, "å": 0.1, "a": 0.1, "angstrom": 0.1,
              "µm": 1e3, "um": 1e3, "μm": 1e3, "micron": 1e3,
              "mm": 1e6, "cm": 1e7, "m": 1e9}
_LEN_Q = ("feature_height", "feature_width", "feature_length", "pore_diameter", "pore_radius")


def _norm_unit(q, val, unit):
    u = (unit or "").strip().lower()
    if val is None:
        return val, unit
    if q in ("growth_per_cycle",) and u in ("å/cycle", "a/cycle", "å", "a", "angstrom"):
        return val * 0.1, "nm"           # Å → nm
    if q in ("film_thickness", "penetration_depth") and u in ("µm", "um", "μm"):
        return val * 1000.0, "nm"        # µm → nm
    if q in _LEN_Q and u in _LEN_TO_NM:
        return val * _LEN_TO_NM[u], "nm"  # feature dimensions → nm (ontology canonical)
    return val, unit


METHODS_SCHEMA = """From the METHODS text, return ONLY JSON with the ALD PROCESS
conditions actually stated (null if absent — do NOT guess):
{"precursors":[..],"coreactants":[..],"process_type":"thermal"|"plasma"|"unknown",
 "temperature_C":num|null,"pressure_Pa":num|null,
 "pulse_time_s":{"precursor":num|null,"coreactant":num|null}|null,
 "purge_time_s":num|null,"ncycles":num|null,"carrier_gas":str|null,
 "_from_table":str|null,
 "_field_tables":{"<field name above>":"Table N"}|null}
The METHODS prose is primary. Consult the TABLES only when the prose or a figure
caption indicates a value is given in a table (e.g. 'listed in Table 1'), or when a
requested value is not in the prose but is clearly stated in a table. When you take a
value from a table, it must be the STANDARD/baseline process value, not one row of an
ablation series. Do NOT guess; leave null if not clearly stated.
- If a condition VARIES across the paper's samples/series (it appears as a range, or
  as several different values for different samples), leave that paper-level field
  NULL. Do not pick one of the values. A paper-level field is only for a single value
  that applies to the whole paper. Example: if films were grown at 70, 120 and 170 C,
  temperature_C is null — not 120.
- Do NOT take process conditions from a simulation / model-parameter / fitting table
  (e.g. a table of modelling inputs, fitted constants, or simulated cases). Only take
  values that describe how the FILMS WERE ACTUALLY GROWN. If the paper is a modelling
  study with no real deposition conditions stated, leave the fields null.
- A condition stated as a WINDOW or RANGE anywhere — in a table OR in the prose (e.g.
  "a broad temperature window from 175-300 C", "grown at temperatures ranging from
  175 to 300 C", "0-3 mbar") — is NOT a single value. Leave that paper-level field
  null. Never take one endpoint of a range (neither the low nor the high one) as the
  value. Only fill the field if ONE specific value is stated as applying to the films
  of the whole paper. If a specific value is given only for a particular experiment
  or figure (e.g. "the saturation study was performed at 225 C"), that belongs to
  that experiment, NOT to the paper-level card — still leave the paper-level field
  null.
If a value comes from a table, note which table in the "_from_table" field, and list
that field in "_field_tables" ({"purge_time_s":"Table 4"}) so each value can be traced
to its own source. Fields absent from "_field_tables" are taken to come from the prose."""


# --- process-window semantics (INTENDED USE — not implemented in this patch) ---
# `temperature_window_C = [min,max]` is paper-level process metadata: the range over
# which the paper reports the process operating. A future integration MAY use it as:
#     · an admissible range for recipe search / design
#     · an optimization bound
#     · a sanity-check constraint on a proposed condition
#     · a validation constraint on an imputed value (is the impute inside the window?)
# It MUST NOT be turned back into a point estimate. Specifically, the lower endpoint,
# the upper endpoint, the midpoint and the median are all forbidden as a paper-level
# extracted temperature unless a separate source states that scalar explicitly.
# Collapsing the window to its lower endpoint is exactly the defect this code removed
# (it put a fabricated growth temperature on 278 experiments across 8 papers).
def _scalar_from_degenerate_range(value):
    """A [min,max] window is a paper-level RANGE, not a deposition condition.
    Return a scalar ONLY when the window is degenerate (min == max, i.e. the paper
    really states one temperature). A genuine window returns None — taking an
    endpoint would assert a growth temperature the paper never claims
    (e.g. [175,300] -> 175 made 8 papers report their window's low end as fact)."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    lo, hi = value
    if isinstance(lo, bool) or isinstance(hi, bool):          # bools are ints in python
        return None
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        return None
    return lo if float(lo) == float(hi) else None


# --- paper-level field provenance -------------------------------------------
# Provenance is CREATED at the stage that creates or transforms the value, never
# inferred afterwards from the number itself (a value of 175 tells you nothing about
# whether it was stated, tabulated, or collapsed out of a [175,300] window — that is
# exactly the confusion this layer removes).
PAPER_ORIGINS = ("scout", "scout_window", "methods_prose", "table", "derived", "unknown")
PAPER_STATUSES = ("direct", "range", "derived", "unresolved")

# Card fields the methods/table pass may fill, in merge order.
CARD_MERGE_FIELDS = ("process_type", "temperature_C", "pressure_Pa", "pulse_time_s",
                     "purge_time_s", "ncycles", "carrier_gas")


def _pprov(origin, status, evidence=None, **extra):
    """One paper-level provenance record. `evidence` is a human-readable pointer
    (e.g. a table ref) or None — never a re-derivation of the value."""
    assert origin in PAPER_ORIGINS and status in PAPER_STATUSES, (origin, status)
    d = {"level": "paper", "origin": origin, "status": status, "evidence": evidence}
    d.update(extra)
    return d


def base_card(scout):
    """Process card from the scout alone (no LLM).

    `temperature_window_C` is preserved as-is (paper-level process metadata, list
    form kept for backward compatibility). `temperature_C` is the paper-level SCALAR
    deposition condition and is only set when the window is degenerate; otherwise it
    stays None and the methods/table pass may still fill a genuine single value.

    `_field_provenance` records, per field, WHERE the value came from. It is written
    here for the two fields this function itself creates: the window (a scout range)
    and — only when the window is degenerate — the scalar derived from it. A
    non-degenerate window yields NO `temperature_C` entry, because no scalar exists."""
    window = scout.get("temperature_window_C")
    scalar = _scalar_from_degenerate_range(window)
    prov = {}
    if scout.get("process_type"):
        prov["process_type"] = _pprov("scout", "direct")
    if window is not None:
        prov["temperature_window_C"] = _pprov("scout_window", "range")
    if scalar is not None:
        prov["temperature_C"] = _pprov("derived", "derived",
                                       transformation="degenerate_range_to_scalar",
                                       from_field="temperature_window_C")
    return {"precursors": scout.get("precursors") or [],
            "coreactants": scout.get("coreactants") or [],
            "process_type": scout.get("process_type") or "unknown",
            "temperature_C": scalar,
            "temperature_window_C": window,
            "pressure_Pa": None, "pulse_time_s": None, "purge_time_s": None,
            "ncycles": None, "carrier_gas": None,
            "_field_provenance": prov}


def methods_fill(sd, scout, client):
    """Fill scout-deferred conditions from the methods section. One LLM call."""
    base = base_card(scout)
    md = (EXTRACTED / sd / "document.md").read_text()
    methods = ex.section_text(md, ["experimental", "methods", "deposition", "film growth",
                                   "materials and methods"], limit=4000)
    if not methods:
        return base, {}
    # Tables the paper reports (from docling) — given to the SAME card-building call as a
    # reference the LLM consults only when pointed to a table or when a value is missing
    # from the prose (e.g. a standard TMA pulse listed only in a pulse-purge-sequence table).
    st = json.loads((EXTRACTED / sd / "structure.json").read_text())
    tables_md = "\n\n".join(
        f"[TABLE {t.get('index')}] {t.get('caption', '')}\n{t.get('markdown', '')}"
        for t in st.get("tables", []) if t.get("markdown"))
    contents = f"{METHODS_SCHEMA}\n\n=== METHODS ===\n{methods}"
    if tables_md:
        contents += ("\n\n=== TABLES (consult ONLY if the methods/captions refer to a "
                     "table, or a value above is absent and appears in a table) ===\n"
                     + tables_md)
    from google.genai import types
    r = client.models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    u = getattr(r, "usage_metadata", None)
    tok = {"in": getattr(u, "prompt_token_count", 0) or 0, "out": getattr(u, "candidates_token_count", 0) or 0}
    try:
        m = ex._loads_json(r.text)
    except Exception:
        return base, tok
    if not isinstance(m, dict):          # model sometimes returns a bare list/scalar
        return base, tok
    for k in ("precursors", "coreactants"):
        if not base[k] and m.get(k):
            base[k] = m[k]
    # Per-field table attribution when the model supplied it; otherwise a card-wide
    # `_from_table` says a table was consulted but NOT for which field — that is an
    # honest `unknown`, never an assumed "table" or "methods_prose".
    ftab = m.get("_field_tables") if isinstance(m.get("_field_tables"), dict) else {}
    card_wide_table = m.get("_from_table")
    prov = base.setdefault("_field_provenance", {})
    for k in CARD_MERGE_FIELDS:
        if base.get(k) in (None, "unknown", []) and m.get(k) not in (None, ""):
            base[k] = m[k]                                   # the value …
            if ftab.get(k):                                  # … and its provenance, together
                prov[k] = _pprov("table", "direct", evidence=str(ftab[k]))
            elif card_wide_table:
                prov[k] = _pprov("unknown", "direct", evidence=str(card_wide_table))
            else:
                prov[k] = _pprov("methods_prose", "direct")
    if card_wide_table:
        base["_from_table"] = card_wide_table       # retained for backward compatibility
    return base, tok


def backfill_card_provenance(card, scout):
    """Deterministic provenance for a card built BEFORE this layer existed (no LLM).

    Only rules, never the numeric value, decide the origin:
      · a window in the scout is a scout range;
      · if that window is DEGENERATE, base_card is what set `temperature_C`, so the
        scalar is `derived` — this follows from the code path, not from comparing
        numbers;
      · every other populated field was filled by the methods/table pass, whose
        per-field origin was not recorded at the time and is unrecoverable without an
        LLM rebuild, so it is `unknown` (§8) — `_from_table`, when present, is carried
        as evidence but is card-wide and does NOT identify which field it explains."""
    prov = dict(card.get("_field_provenance") or {})
    scout = scout or {}
    window = scout.get("temperature_window_C")
    if window is not None and "temperature_window_C" not in prov:
        prov["temperature_window_C"] = _pprov("scout_window", "range")
    if scout.get("process_type") and "process_type" not in prov:
        prov["process_type"] = _pprov("scout", "direct")   # base_card, not the merge
    degenerate = _scalar_from_degenerate_range(window) is not None
    for k in CARD_MERGE_FIELDS:
        if k in prov or card.get(k) in (None, "", [], {}, "unknown"):
            continue
        if k == "temperature_C" and degenerate:
            prov[k] = _pprov("derived", "derived",
                             transformation="degenerate_range_to_scalar",
                             from_field="temperature_window_C")
        else:
            prov[k] = _pprov("unknown", "direct", evidence=card.get("_from_table"))
    card["_field_provenance"] = prov
    return card


def get_card(sd, scout, client):
    """The methods-filled process card — CACHED to card.json so it's computed once.
    On re-resolve (client=None) it loads the cache (or the scout base), NO LLM."""
    cf = EXTRACTED / sd / "card.json"
    if cf.exists():
        card = json.loads(cf.read_text())
        if "_field_provenance" not in card:       # legacy card: backfill, no LLM
            cf.write_text(json.dumps(backfill_card_provenance(card, scout), indent=1))
        return card, {}
    card, tok = (methods_fill(sd, scout, client) if client else (base_card(scout), {}))
    cf.write_text(json.dumps(card, indent=1))
    return card, tok


# A COMPLETE number (+ optional unit). The unit class excludes '-', so 'Al2O3' and
# '2-propanol' are names, not numbers. Same rule the series path uses in 05 — a condition
# value must BE a number, never merely contain a digit.
_NUMU = re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-zµμÅ°%/·^]*)\s*\Z")


def _num_cond(k, v, origin=None):
    """Caption condition -> controlled entry, ONLY when the value is a complete number.
    Without this, _num('Al2O3') returns 2.0 and a categorical caption field becomes a
    fabricated measurement."""
    m = _NUMU.fullmatch(str(v))
    if not m:
        return None
    return _ctrl(k, float(m.group(1)), (m.group(2) or None), source="caption", origin=origin)


def _ctrl(q, v, u, react=None, source="methods", origin=None):
    """One controlled condition. `origin` (optional) is the structured record of WHERE
    the value came from — paper card vs this experiment's caption/series — carried
    alongside the existing free-standing `source` label, which is left untouched."""
    if v is None:
        return None
    cq = lib.canon_quantity(q) or q
    v, u = _norm_unit(cq, v, u)
    c = {"quantity": cq, "value": v, "unit": u, "of_reactant": react,
         "source": source, "recipe_role": lib.recipe_role(cq)}
    if origin:
        c["origin"] = origin
    return c


def _exp_origin(kind, pid, exp_id, prov=None):
    """Experiment-level origin. Figure/panel are included only when the record
    actually carries them — never invented."""
    o = {"level": "experiment", "from": kind, "paper_id": pid, "experiment_id": exp_id}
    fig = (prov or {}).get("figure")
    panel = (prov or {}).get("panel")
    if fig:
        o["figure"] = fig
    if panel:
        o["panel"] = panel
    return o


def paper_conditions(card):
    """Paper-level controlled conditions from the (gap-filled) process card.

    Each carries a paper-level origin naming the CARD FIELD it came from, plus that
    field's own provenance when the card records one — so a condition can say not just
    'methods' but 'card.temperature_C, which was derived from a degenerate window'."""
    fp = card.get("_field_provenance") or {}

    def po(card_field):
        o = {"level": "paper", "from": "card", "card_field": card_field}
        if fp.get(card_field):
            o["card_provenance"] = fp[card_field]
        return o

    cs = []
    for c in [
        _ctrl("temperature", card.get("temperature_C"), "C", origin=po("temperature_C")),
        _ctrl("total_pressure", card.get("pressure_Pa"), "Pa", origin=po("pressure_Pa")),
        _ctrl("cycle_number", card.get("ncycles"), "cycles", origin=po("ncycles")),
        _ctrl("purge_time", card.get("purge_time_s"), "s", origin=po("purge_time_s")),
    ]:
        if c:
            cs.append(c)
    pt = card.get("pulse_time_s") or {}
    if isinstance(pt, dict):
        cs += [x for x in (_ctrl("pulse_time", pt.get("precursor"), "s", "A",
                                 origin=po("pulse_time_s")),
                           _ctrl("pulse_time", pt.get("coreactant"), "s", "B",
                                 origin=po("pulse_time_s"))) if x]
    return cs


# --- test-structure geometry + model parameters (from 09_geometry) ------------
# Read at RESOLVE time rather than patched in afterwards: 09_geometry used to tag
# experiments.json directly, so every re-resolve silently erased the structure class
# (all 672 experiments carried structure=None). Reading the cached geometry.json here
# makes the geometry survive re-grounding, deterministically and at zero token cost.
FACTUAL_STATUS = ("directly_reported", "derived_from_reported_dimensions")


def geometry_facts(sd):
    """(structure, geometry_class, [controlled conditions]) from extracted/{sd}/geometry.json.

    Only `directly_reported` / `derived_from_reported_dimensions` quantities become
    conditions — an `inferred_from_context` value stays in geometry.json for audit but is
    never asserted as fact. Each condition keeps its raw label, evidence quote and status,
    and all copies share ONE evidence id so paper-level fan-out is not mistaken for
    independent observations."""
    gf = EXTRACTED / sd / "geometry.json"
    if not gf.exists():
        return None, None, []
    try:
        g = json.loads(gf.read_text())
    except Exception:
        return None, None, []
    cs = []
    for i, q in enumerate(g.get("quantities") or []):
        if q.get("status") not in FACTUAL_STATUS:
            continue
        origin = {"level": "paper", "from": "geometry",
                  "evidence_id": f"{sd}::geometry::{q.get('quantity')}::{i}",
                  "raw_label": q.get("raw_label"), "symbol": q.get("symbol"),
                  "status": q.get("status"), "scope": q.get("scope"),
                  "evidence": q.get("evidence")}
        for k in ("basis", "model_context", "parameter_status"):
            if q.get(k):
                origin[k] = q[k]
        c = _ctrl(q.get("quantity"), q.get("value"), q.get("unit"),
                  react=q.get("of_reactant"), source="geometry", origin=origin)
        if c:
            cs.append(c)
    return (g.get("structure") or None), (g.get("geometry_class") or None), cs


def short_pid(sd):
    # Unified paper id = the filesystem-safe full DOI (the extracted dir name),
    # so extracted/ and output/ share ONE identifier: the DOI.
    return sd


def to_experiments(sd, scout, records, card):
    prec = (scout.get("precursors") or card.get("precursors") or [None])[0]
    core = (scout.get("coreactants") or card.get("coreactants") or [None])[0]
    prec_c, core_c = lib.canon_precursor(prec) or prec, lib.canon_coreactant(core) or core
    reactants = [{"label": "A", "role": "precursor", "species": prec_c}]
    if core_c:
        reactants.append({"label": "B", "role": "coreactant", "species": core_c})
    carrier = {"species": card.get("carrier_gas")} if card.get("carrier_gas") else None
    ptype = lib.canon_process(card.get("process_type")) or card.get("process_type")
    base_ctrl = paper_conditions(card)
    geom_struct, geom_class, geom_ctrl = geometry_facts(sd)
    base_ctrl = base_ctrl + geom_ctrl
    pid = short_pid(sd)
    exps = []
    for r in records:
        mq = lib.canon_quantity((r.get("measurand") or {}).get("quantity")) or (r.get("measurand") or {}).get("quantity")
        cq = lib.canon_quantity(r.get("coordinate")) or r.get("coordinate")
        mv, mu = _norm_unit(mq, None, (r.get("measurand") or {}).get("unit"))
        pts = [p for p in (r.get("points") or []) if isinstance(p, list) and len(p) == 2]
        mat = lib.canon_material(r.get("material")) or (scout.get("materials") or [None])[0]
        fig = (r.get("provenance") or {}).get("figure", "F?").replace("Fig ", "F").replace(" ", "")
        panel = (r.get("provenance") or {}).get("panel") or ""
        panel = panel.lower() if re.fullmatch(r"[A-Za-z]", str(panel).strip()) else ""   # only a real panel letter
        # exp_id is resolved BEFORE the conditions so each condition's origin can name
        # the experiment it belongs to (unchanged value — same expression as before).
        exp_id = f"{pid}-{fig}{panel}-{len(exps)}"
        panel_ctrl = [c for c in (
            _num_cond(k, v, origin=_exp_origin("caption", pid, exp_id, r.get("provenance")))
            for k, v in (r.get("controlled") or {}).items()) if c]
        # Series identity arrives STRUCTURED from 05 — no string is parsed here. Only a
        # numeric_sweep contributes a controlled condition; categorical/material series
        # never do. This is what makes value fabrication (LTB:H2S -> 2.0, 2-propanol ->
        # 2.0) structurally impossible rather than merely guarded against.
        series_ctrl = []
        if r.get("series_kind") == "numeric_sweep" and r.get("series_value_num") is not None:
            # Naming the axis is vision's job (05). 06 never reconstructs it — a blank
            # axis becomes a VISIBLE flag so it stands out in QA instead of hiding behind
            # a meaningless 'series_value'.
            _axis = (r.get("series_axis") or "").strip() or "unnamed_series_axis"
            series_ctrl = [_ctrl(_axis, r.get("series_value_num"), r.get("series_unit"),
                                 source="series",
                                 origin=_exp_origin("series", pid, exp_id, r.get("provenance")))]
        series_ctrl = [c for c in series_ctrl if c]
        # display metadata only — never split or coerced downstream
        series_name = (f'{r.get("series_axis") or "series"}: {r.get("series_value")}'
                       if r.get("series_kind") in ("numeric_sweep", "categorical")
                       and r.get("series_value") else None)
        e = {
            "material": mat, "material_raw": r.get("material"),
            "precursors": [prec_c] if prec_c else [], "coreactants": [core_c] if core_c else [],
            "reactants": reactants, "carrier_gas": carrier, "process_type": ptype,
            "cycle_sequence": "AB" if core_c else "A",
            "controlled": base_ctrl + panel_ctrl + series_ctrl,
            "measurand": {"quantity": mq, "unit": (r.get("measurand") or {}).get("unit"),
                          "family": lib.family(mq)},
            "coordinate": cq, "coordinate_family": lib.family(cq),
            "points": pts, "granularity": "profile" if len(pts) > 1 else "single",
            "relevance": "experimental" if r.get("source") == "measured" else "model",
            "is_model_result": r.get("source") == "simulated",
            "analysis_ready": bool(pts and mq),
            "exp_id": exp_id,
            "provenance": {**(r.get("provenance") or {}), "doi": sd},
            "series_name": series_name,             # display only; built from structure, never re-parsed
            "phase": r.get("phase"),                # crystallographic phase (e.g. "c-MoS2") or None
            "structure": geom_struct, "geometry_class": geom_class,
            # dependent = the measured output; varies = the swept coordinate (profiles).
            # Populated so the shared 0706 consumers (evaluate_kb, kg, similarity) see the
            # measured/swept quantities the same way as old-pipeline records.
            "varies": [cq] if (cq and len(pts) > 1) else [],
            "dependent": [{"quantity": mq, "unit": (r.get("measurand") or {}).get("unit"),
                           "family": lib.family(mq)}] if mq else [],
            "issues": [] if pts else ["no-points"],
        }
        r_obj = recipe_mod.from_experiment(e)
        e["recipe"] = r_obj.to_dict(); e["recipe"]["completeness"] = r_obj.completeness()
        exps.append(e)
    if not exps:
        # No figure data digitized — still admit the paper as ONE paper-level experiment
        # (attached to its Paper node in the KG) carrying chemistry + conditions + the data
        # modalities the scout saw (XRD, spectra, imaging …), so the paper enters the KB.
        exps.append(paper_level_experiment(sd, scout, card, pid, reactants, carrier, ptype, prec_c, core_c,
                                       base_ctrl, geom_struct, geom_class))
    # Species properties from the ontology for each cycle reactant (A precursor,
    # B coreactant, …) — ported verbatim from the old s08_resolve, which the new
    # 06 path never ran, so 662 experiments had lost molecular_mass / diameter that
    # the twin (and similarity) rely on. Applied to BOTH panel and paper-level records.
    for e in exps:
        for r in e.get("reactants") or []:
            sp, lab = r.get("species"), r.get("label")
            if not sp:
                continue
            mm = lib.species_prop(sp, "molar_mass")
            dpm = lib.species_prop(sp, "molecular_diameter")
            e["controlled"] = [c for c in (e.get("controlled") or [])
                               if not (c.get("quantity") in ("molecular_mass", "precursor_molecular_diameter")
                                       and c.get("of_reactant") == lab)]
            # ontology reference data, not a measurement of this paper — the origin
            # names the species it was looked up for
            so = {"level": "ontology", "from": "species_property", "species": sp}
            if mm is not None:
                e["controlled"].append({"quantity": "molecular_mass", "value": round(mm, 4),
                                        "unit": "g/mol", "of_reactant": lab, "source": "species",
                                        "origin": {**so, "property": "molar_mass"}})
            if dpm is not None:
                e["controlled"].append({"quantity": "precursor_molecular_diameter", "value": round(dpm * 1e-3, 4),
                                        "unit": "nm", "of_reactant": lab, "source": "species",
                                        "origin": {**so, "property": "molecular_diameter"}})
    return pid, exps


def paper_level_experiment(sd, scout, card, pid, reactants, carrier, ptype, prec_c, core_c,
                           base_ctrl, geom_struct=None, geom_class=None):
    raw_mat = (scout.get("materials") or [None])[0]
    mat = lib.canon_material(raw_mat) or raw_mat
    gpc = scout.get("gpc_nm")
    mq = "growth_per_cycle" if gpc is not None else None
    modalities = sorted(k for k, v in (scout.get("data") or {}).items()
                        if isinstance(v, dict) and v.get("present"))
    e = {
        "material": mat, "material_raw": raw_mat,
        "precursors": [prec_c] if prec_c else [], "coreactants": [core_c] if core_c else [],
        "reactants": reactants, "carrier_gas": carrier, "process_type": ptype,
        "cycle_sequence": "AB" if core_c else "A",
        "controlled": base_ctrl,
        "measurand": {"quantity": mq, "unit": "nm" if mq else None,
                      "family": lib.family(mq) if mq else None},
        "coordinate": None, "coordinate_family": None,
        "points": [], "granularity": "single",
        "relevance": "experimental", "is_model_result": False, "is_paper_level": True,
        "analysis_ready": False,
        "exp_id": f"{pid}-paper-0",
        "provenance": {"doi": sd, "source": "paper-level", "figure": "paper",
                       "study_type": scout.get("study_type"), "modalities": modalities},
        "series_name": None, "phase": None, "varies": [],
        "structure": geom_struct, "geometry_class": geom_class,
        "dependent": ([{"quantity": mq, "value": gpc, "unit": "nm", "family": lib.family(mq)}]
                      if mq else []),
        "issues": ["paper-level (no figure data extracted)"],
    }
    r_obj = recipe_mod.from_experiment(e)
    e["recipe"] = r_obj.to_dict(); e["recipe"]["completeness"] = r_obj.completeness()
    return e


def _num(v):
    if isinstance(v, (int, float)):
        return v
    m = re.search(r"-?\d+\.?\d*(?:e-?\d+)?", str(v))
    return float(m.group()) if m else None


def _unit(v):
    m = re.search(r"[a-zµμÅ%/·]+\s*$", str(v).strip())
    return m.group().strip() if m else ""


def main(sds):
    resolve_only = "--resolve-only" in sds        # deterministic re-grounding, NO LLM
    sds = [s for s in sds if not s.startswith("--")]
    client = None
    if not resolve_only:
        from google import genai
        client = genai.Client(api_key=ex._load_key())
    TI = TO = 0
    for sd in sds:
        d = EXTRACTED / sd
        scout = json.loads((d / "scout.json").read_text())
        records = json.loads((d / "records.json").read_text()) if (d / "records.json").exists() else []
        card, tok = get_card(sd, scout, client)   # cached; LLM only first time (skipped on --resolve-only)
        TI += tok.get("in", 0); TO += tok.get("out", 0)
        pid, exps = to_experiments(sd, scout, records, card)
        outdir = OUT / pid / "resolved"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "experiments.json").write_text(json.dumps(exps, indent=1))
        mats = sorted({e["material"] for e in exps if e["material"]})
        ready = sum(1 for e in exps if e["analysis_ready"])
        exp = sum(1 for e in exps if e["relevance"] == "experimental")
        print(f"[to-kb] {sd} → output/{pid}/  {len(exps)} exps ({ready} ready, {exp} exp / {len(exps)-exp} model) "
              f"materials={mats} chem={card.get('precursors')}+{card.get('coreactants')} T={card.get('temperature_C')}")
    print(f"[to-kb] methods gap-fill tokens: in={TI} out={TO}")


if __name__ == "__main__":
    main(sys.argv[1:])
