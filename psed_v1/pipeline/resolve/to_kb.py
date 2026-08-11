#!/usr/bin/env python3
"""
06_to_kb.py — Stage 4/5: methods gap-fill + resolve scout/vision records into the
KB schema (papers/{pid}/resolved/experiments.json), so new-chemistry
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
import paths as P
import json, os, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = P.REPO
EXTRACTED = P.PAPERS                 # papers/<id>/extracted/
OUT = P.PAPERS                       # papers/<id>/{resolved,canonical}/

from ontology import vocab as lib
from pipeline.resolve import recipe as recipe_mod
from pipeline.canonical import live as clive           # unit conversion, axis-role granularity, scoping
from pipeline.canonical import sources as csources     # recovered verbatim axis labels
from pipeline.canonical import entities as centities   # what a digitised curve actually IS
from pipeline.canonical import conditions as ccond     # ConditionAssertion recovery + binding
from pipeline.canonical import chemistry_scope as cschem  # material/reactants by narrowest evidence
from pipeline.canonical import series_identity as csid    # measured vs calculated, per series
from pipeline.canonical import axis_roles as caxis        # what an axis MEANS
from pipeline.canonical import granularity as cgran       # does variation mean separate runs
from pipeline.text import chemistry_propagation as cprop
from pipeline.text import pressure as pressure10
from pipeline.scout import scout as ex

MODEL = "gemini-flash-latest"
OUT = P.PAPERS

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
    """Scalar unit normalisation for a single controlled value.

    Delegates to the shared, dimension-aware converter so the KB and the
    canonical layer agree. Two behaviours changed here on purpose:
      * `Å/cycle` now becomes `nm/cycle`, NOT `nm` — the /cycle dimension is
        part of the quantity and dropping it made GPC incomparable with lengths.
      * a value is only rescaled when its unit is genuinely convertible; an
        unparseable or dimension-conflicting unit leaves the value untouched.
    """
    if val is None:
        return val, unit
    vals, out_unit, _rec = clive.normalize_measurand(q, unit, [val])
    return (vals[0] if vals else val), out_unit


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
    md = (P.extracted_dir(sd) / "document.md").read_text()
    methods = ex.section_text(md, ["experimental", "methods", "deposition", "film growth",
                                   "materials and methods"], limit=4000)
    if not methods:
        return base, {}
    # Tables the paper reports (from docling) — given to the SAME card-building call as a
    # reference the LLM consults only when pointed to a table or when a value is missing
    # from the prose (e.g. a standard TMA pulse listed only in a pulse-purge-sequence table).
    st = json.loads((P.extracted_dir(sd) / "structure.json").read_text())
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
    cf = P.extracted_dir(sd) / "card.json"
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
        # `pressure_Pa` on the card is the reactor's TOTAL pressure — METHODS_SCHEMA asks
        # for one paper-level pressure with no species and no reactant role. Emitting it
        # as chamber_total_pressure names that plainly, so it can never be read as a
        # reactant partial pressure.
        _ctrl("chamber_total_pressure", card.get("pressure_Pa"), "Pa", origin=po("pressure_Pa")),
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


def geometry_material(q, materials):
    """The material a geometry/model parameter belongs to, when its evidence says.

    A model-parameter table is one row per material:

        Al 2 O 3 | 500 | 500 | 147 | 0.00572 | 219
        TiO 2    | 1000 | 500 | 25.7 | 0.1   | 0.252

    Both rows were extracted at PAPER scope, so an Al2O3 experiment was offered
    TiO2's sticking probability and adsorption constant as equally valid
    candidates; the conflict then surfaced as "3 distinct sticking_probability
    values at paper scope". The row's own evidence names its material, which
    makes the split deterministic instead of ambiguous.
    """
    hits = cschem._named(q.get("evidence") or "", materials)
    return hits[0] if len(hits) == 1 else None


def geometry_facts(sd, materials=None, material=None):
    """(structure, geometry_class, [controlled conditions]) from extracted/{sd}/geometry.json.

    When `material` is given, a parameter whose evidence row names a DIFFERENT
    material is dropped: it is that other film's parameter, not this one's.

    Only `directly_reported` / `derived_from_reported_dimensions` quantities become
    conditions — an `inferred_from_context` value stays in geometry.json for audit but is
    never asserted as fact. Each condition keeps its raw label, evidence quote and status,
    and all copies share ONE evidence id so paper-level fan-out is not mistaken for
    independent observations."""
    gf = P.extracted_dir(sd) / "geometry.json"
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
        qmat = geometry_material(q, materials)
        if material and qmat and qmat != material:
            continue                      # another film's row of the same table
        origin = {"level": "material" if qmat else "paper", "from": "geometry",
                  "material_scope": qmat,
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



_PRESSURE_Q = ("chamber_total_pressure", "generic_pressure", "total_pressure", "pressure",
               "working_pressure", "base_pressure", "precursor_partial_pressure",
               "co_reactant_partial_pressure", "carrier_gas_partial_pressure")


def _dedup_pressures(conds):
    """Cross-source pressure dedup. When a pressure from the pressure-extraction pass and
    a card/methods pressure share the same normalised value, the extraction one wins
    (it is typed and evidence-backed) and the card duplicate is dropped. Non-pressure
    conditions and genuinely different pressure values are untouched."""
    ext_vals = [c["value"] for c in conds
                if c.get("source") == "pressure_extraction"
                and isinstance(c.get("value"), (int, float))]

    def _matches_ext(v):
        # relative tolerance: the card often rounds (750 mtorr -> exactly 99.99 Pa) while
        # the pass computes 99.9915 Pa from the unit conversion. 1% catches that without
        # merging genuinely distinct values (0.01 vs 1 mbar stay separate).
        return any(abs(v - e) <= 0.01 * max(abs(v), abs(e), 1e-12) for e in ext_vals)

    out = []
    for c in conds:
        q, v = c.get("quantity"), c.get("value")
        if (c.get("source") != "pressure_extraction" and q in _PRESSURE_Q
                and isinstance(v, (int, float)) and _matches_ext(v)):
            continue                        # card/methods duplicate of a typed pressure
        out.append(c)
    return out


_LABEL_CACHE = {}


def _canon_axis(label):
    """Alias lookup used by axis_roles: the label resolver first (it strips
    units and log/ln wrappers), then the plain alias table."""
    if not label:
        return None
    return lib.resolve_axis_label(label) or lib.canon_quantity(label)


def _axis_labels(sd, record):
    """Verbatim axis labels recovered by the selective re-extraction pass, if any.
    They let the live path repair a unit with EVIDENCE (a label reading
    'Thickness/cycles S/N (nm)' proves the quantity is per-cycle) instead of
    guessing. Returns {} when no recovery file exists for this paper."""
    if sd not in _LABEL_CACHE:
        idx = {}
        # 1. labels captured by the CURRENT extraction schema (05_figure_extract.py
        #    now records label_raw). Future papers need no recovery pass at all.
        try:
            fd = json.loads((P.extracted_dir(sd) / "figure_data.json").read_text())
            for fig in fd.get("figures") or []:
                for pan in fig.get("panels") or []:
                    key = (str(fig.get("figure")), str(pan.get("panel") or "").lower())
                    idx[key] = {"x": (pan.get("x") or {}).get("label_raw"),
                                "y": (pan.get("y") or {}).get("label_raw")}
        except Exception:
            pass
        # 2. labels recovered afterwards for papers extracted with the old schema.
        #    Kept in SEPARATE namespaces: printed figure numbers and docling
        #    indices are different numbering systems, and merging them made a
        #    lookup of printed "7" return docling-7's labels -- a different
        #    figure. That is how an XPS depth profile acquired the axes of an
        #    in-situ thickness trace.
        printed = {}
        try:
            rc = csources.recovery_index(sd)
            for ns, target in (("by_docling", idx), ("by_printed", printed)):
                for key, rec in (rc.get(ns) or {}).items():
                    lab = {"x": (rec.get("x") or {}).get("label_raw"),
                           "y": (rec.get("y") or {}).get("label_raw")}
                    if lab["x"] or lab["y"]:
                        target.setdefault(key, lab)
        except Exception:
            pass
        _LABEL_CACHE[sd] = {"by_docling": idx, "by_printed": printed}
    maps = _LABEL_CACHE[sd]
    prov = record.get("provenance") or {}
    panel = str(prov.get("panel") or "").lower()
    for ns, key in (("by_docling", str(prov.get("fig_docling_index") or "")),
                    ("by_printed", str(prov.get("figure_number") or ""))):
        if not key:
            continue
        rec = (maps.get(ns) or {}).get((key, panel))
        if rec and (rec.get("x") or rec.get("y")):
            return rec
    return {}


def _entity_context(sd, e):
    """Evidence bundle for one source entity (one digitised curve)."""
    prov = e.get("provenance") or {}
    fi = str(prov.get("fig_docling_index") or "")
    fn = str(prov.get("figure_number") or "")
    pan = str(prov.get("panel") or "")
    fd = _figure_data(sd)
    fig, panel, panel_ord = {}, {}, None
    sname_probe = e.get("series_name") or ""
    slabel_probe = (sname_probe.split(":", 1)[1].strip() if ":" in sname_probe
                    else (sname_probe or "<single>"))
    for f in fd.get("figures", []) or []:
        if str(f.get("figure")) == fi:
            fig = f
            cands = [(i, pp) for i, pp in enumerate(f.get("panels", []) or [])
                     if str(pp.get("panel") or "") == pan]
            # When the panel LETTER is missing, several panels of one figure share the
            # empty key. Disambiguate by the panel that actually carries this curve's
            # coordinate and label, and record its ordinal so the entity key stays
            # unique (two panels of Fig 5 both lost their letter in 10.1116_6.0002804).
            if len(cands) > 1:
                best = [(i, pp) for i, pp in cands
                        if (pp.get("x") or {}).get("quantity") == e.get("coordinate")
                        and any(str(sx.get("label", "")).strip() == slabel_probe
                                for sx in (pp.get("series") or []))]
                cands = best or cands
            if cands:
                panel_ord, panel = cands[0]
            break
    sname = e.get("series_name") or ""
    slabel = sname.split(":", 1)[1].strip() if ":" in sname else (sname or "<single>")
    cap = fig.get("caption") or ""
    return {
        "caption": cap,
        "body_mentions": _figure_body(sd, fn),
        "source_series": slabel,
        "panel_series_axis": panel.get("series_axis"),
        "coordinate": e.get("coordinate"),
        "granularity": e.get("granularity"),
        "relevance": e.get("relevance"),
        "is_model_result": e.get("is_model_result"),
        "panel_source_flag": (fig.get("panel_source") or {}).get(pan),
        "figure_source_flag": fig.get("source"),
        "representation": _representation(cap, pan),
        "n_source_points": len(e.get("points") or []),
        "table_captions": [t.get("caption") for t in (_structure(sd).get("tables") or [])],
        "fig_docling_index": fi, "figure_number": fn, "panel": pan,
        "panel_key": pan or ("#%d" % panel_ord if panel_ord is not None else "-"),
        "panel_conditions": panel.get("conditions") or {},
        # every label drawn in this panel: a fit can only be attached to the
        # measured curve it was fitted to if we can see its siblings
        "panel_series_labels": [str(s.get("label") or "").strip()
                                for s in (panel.get("series") or [])],
        "panel_x_quantity": (panel.get("x") or {}).get("quantity"),
        # lets a "as presented in Figure N" cross-reference be resolved against
        # the figures this paper actually has
        "paper_figure_numbers": [
            (r.get("provenance") or {}).get("figure_number")
            for r in _records(sd)],
    }


_FD_CACHE, _ST_CACHE, _DOC_CACHE, _REF_CACHE = {}, {}, {}, {}
_RECS_CACHE = {}


def _records(sd):
    if sd not in _RECS_CACHE:
        f = P.extracted_dir(sd) / "records.json"
        _RECS_CACHE[sd] = json.loads(f.read_text()) if f.exists() else []
    return _RECS_CACHE[sd]


def _reference_assertions(sd):
    if sd not in _REF_CACHE:
        _REF_CACHE[sd] = ccond.reference_scoped_assertions(_document(sd), paper_id=sd)
    return _REF_CACHE[sd]


_VARIED_CACHE = {}


def _figure_varied(sd, fig_index):
    """Quantities that some panel/series of this figure VARIES.

    A figure-scope value of such a quantity is one panel's setting, not the
    figure's common value, so it must not be broadcast to the other panels
    (Fig. 11 of 10.1039_d0cp03358h varies pulse time in (a) and purge time in (b);
    panel (a)'s 0.4 s was reaching panel (b))."""
    key = (sd, str(fig_index))
    if key in _VARIED_CACHE:
        return _VARIED_CACHE[key]
    out = set()
    for f in (_figure_data(sd).get("figures") or []):
        if str(f.get("figure")) != str(fig_index):
            continue
        for pan in (f.get("panels") or []):
            axis = pan.get("series_axis") or ""
            for a in ccond.from_series_label(
                    " ".join(str(sx.get("label", "")) for sx in (pan.get("series") or [])),
                    axis):
                out.add(a["quantity"])
            q, _ = ccond.quantity_for(axis, None)
            if q:
                out.add(q)
    _VARIED_CACHE[key] = out
    return out


_METH_CACHE = {}


def _method_assertions(sd):
    if sd not in _METH_CACHE:
        m = _methods(sd)
        _METH_CACHE[sd] = (ccond.conditions_from_prose(m, "method", "methods",
                                                       "methods section", paper_id=sd)
                           + ccond.pressures_from_text(m, "method", "methods",
                                                       "methods section", paper_id=sd))
    return _METH_CACHE[sd]


def _figure_data(sd):
    if sd not in _FD_CACHE:
        f = P.extracted_dir(sd) / "figure_data.json"
        _FD_CACHE[sd] = json.loads(f.read_text()) if f.exists() else {}
    return _FD_CACHE[sd]


_DRILL_CACHE = {}


_MCHEM_CACHE = {}


def _methods_mapping(sd, materials):
    """{material: precursor} from an explicit 'respectively' sentence in the
    methods. Cached per paper: the regex runs over the whole methods section."""
    if sd not in _MCHEM_CACHE:
        _MCHEM_CACHE[sd] = cschem.methods_chemistry_mapping(
            _methods(sd), materials)
    return _MCHEM_CACHE[sd]


def _figure_caption(sd, fig_docling_index):
    """The figure's FULL caption. The copy on a record is truncated to 200
    characters, which is enough to spot a material but not to split panel
    clauses out of a six-panel caption."""
    for f in (_figure_data(sd).get("figures") or []):
        if str(f.get("figure")) == str(fig_docling_index or ""):
            return f.get("caption") or ""
    return ""


def _drill_why(sd, fig_docling_index):
    """The scout's own one-line note for this figure ("...profiles of TiO2 in
    lateral channel"). Written per figure at extraction time, so it is
    figure-level evidence and ranks above any paper-level default."""
    if sd not in _DRILL_CACHE:
        f = P.extracted_dir(sd) / "scout.json"
        sc = json.loads(f.read_text()) if f.exists() else {}
        _DRILL_CACHE[sd] = {str(d.get("where") or "").lstrip("Ff"): d.get("why")
                            for d in (sc.get("drill") or [])}
    return _DRILL_CACHE[sd].get(str(fig_docling_index or ""))


def _structure(sd):
    if sd not in _ST_CACHE:
        f = P.extracted_dir(sd) / "structure.json"
        _ST_CACHE[sd] = json.loads(f.read_text()) if f.exists() else {}
    return _ST_CACHE[sd]


def _document(sd):
    if sd not in _DOC_CACHE:
        f = P.extracted_dir(sd) / "document.md"
        _DOC_CACHE[sd] = ccond.fold_math(f.read_text(errors="replace")) if f.exists() else ""
    return _DOC_CACHE[sd]


def _figure_body(sd, fignum, window=620):
    if not fignum:
        return ""
    txt = _document(sd)
    out = []
    for m in re.finditer(r"[Ff]ig(?:ure)?s?\.?\s*%s(?![0-9])" % re.escape(str(fignum)), txt):
        out.append(txt[max(0, m.start() - 260): m.end() + window])
        if len(out) >= 3:
            break
    return "\n---\n".join(out)


# Markdown SECTION HEADINGS, not a bare word match. A plain search for "method"
# matched "method of choice for conformal thin film growth" in the INTRODUCTION of
# 10.1039_d0cp03358h and returned 6000 characters of intro, so every methods-scope
# condition in that paper (300 C, 500 cycles, 3 hPa, 150 sccm) was invisible.
_METHOD_HEADING = re.compile(
    r"(?im)^\s{0,3}#{1,4}\s*(?:[A-Z0-9]{1,3}[.)]\s*)?"
    r"((?:experimental|methods?|materials and methods|experimental (?:section|details|setup)|"
    r"atomic layer deposition|ald (?:process|growth|deposition)|film (?:growth|deposition)|"
    r"deposition(?: process| conditions)?|sample preparation|synthesis|"
    r"characteri[sz]ation)\b[^\n]*)$")


def _methods(sd):
    """Every methods-like SECTION of the paper, concatenated.

    Papers split their conditions across 'Atomic layer deposition',
    'Sample preparation' and 'Characterisation' sections, so all matching headings
    are collected rather than only the first."""
    txt = _document(sd)
    spans = []
    heads = list(_METHOD_HEADING.finditer(txt))
    for m in heads:
        nxt = re.search(r"(?m)^\s{0,3}#{1,4}\s+\S", txt[m.end():])
        end = m.end() + (nxt.start() if nxt else 4000)
        spans.append(txt[m.start():end])
    if spans:
        return "\n\n".join(spans)[:20000]
    m = re.search(r"(?is)\b(experimental|materials and methods)\b(.{0,6000})", txt)
    return m.group(0) if m else txt[:6000]


_REPR = [(re.compile(r"as[- ]measured", re.I), "as_measured"),
         (re.compile(r"\bscaled\b", re.I), "scaled"),
         (re.compile(r"normali[sz]ed", re.I), "normalized"),
         (re.compile(r"\binset\b", re.I), "inset")]


def _representation(caption, panel):
    clause = ""
    if panel:
        m = re.search(r"\(\s*%s\s*\)" % re.escape(panel), caption or "", re.I)
        if m:
            nxt = re.search(r"\(\s*[a-h]\s*\)", caption[m.end():], re.I)
            clause = caption[m.start(): m.end() + (nxt.start() if nxt else 200)]
    for rx, lab in _REPR:
        if clause and rx.search(clause):
            return lab
    return "primary"


def figure_slug(printed_figure_number, panel):
    """`Fig7a` from the figure's own caption number and its panel letter.

    Both come from extraction provenance and neither is invented: a figure whose
    printed number was never resolved becomes `FigIdx<n>` (the docling index,
    visibly marked as such) or `NoFig`, and a panel is appended ONLY when the
    source gives one. A single-panel figure therefore reads `Fig7`, not `Fig7a`.
    """
    fn = str(printed_figure_number or "").strip()
    slug = "Fig%s" % re.sub(r"[^A-Za-z0-9.]", "", fn) if fn else None
    pan = str(panel or "").strip().lower()
    if slug and re.fullmatch(r"[a-z]", pan):
        slug += pan
    return slug


def assign_experiment_ids(entities, pid):
    """`<doi>__Fig7a__exp01` — paper, figure, panel, and a suffix only when the
    same figure/panel yields more than one record.

    The old id was `<doi>-E017`: a running index that said nothing about where
    the record came from, so reviewing a paper figure by figure meant joining
    back to the entity table for every row. Ids are assigned after all entities
    of a paper exist, because whether a suffix is needed is a property of the
    GROUP, not of one record.
    """
    groups = defaultdict(list)
    for e in entities:
        slug = figure_slug(e.get("printed_figure_number"), e.get("panel"))
        if not slug:
            idx = str(e.get("fig_docling_index") or "").strip()
            slug = "FigIdx%s" % idx if idx else "NoFig"
        e["_slug"] = slug
        groups[slug].append(e)

    out = {}
    for slug, members in groups.items():
        multi = len(members) > 1
        for i, e in enumerate(members, 1):
            eid = "%s__%s" % (pid, slug)
            if multi:
                eid += "__exp%02d" % i
            e["experiment_id"] = eid
            e["figure_slug"] = slug
            e["id_has_panel"] = bool(re.search(r"[a-z]$", slug))
            e["id_suffix_reason"] = (
                "%d records share %s" % (len(members), slug) if multi else None)
            out[id(e)] = eid
        members.sort(key=lambda x: x.get("experiment_id") or "")
    for e in entities:
        e.pop("_slug", None)
    return out


def resolve_source_entities(sd, exps, pid):
    """Turn per-curve records into TYPED SOURCE ENTITIES.

    Contract, enforced here:
      * a drawn curve is a PlotSeries and is never itself an Experiment;
      * its digitised points are Observations by default;
      * an ExperimentalCase is minted only when the paper ENUMERATES the settings;
      * simulations, model sweeps, fits, imported literature and derived
        representations never become current-paper Experiments;
      * `unknown` entities are preserved whole, unsplit and unpromoted.

    Returns (entities, experiment_cases, series, assertions).
    """
    methods = _methods(sd)
    entities, cases, series, assertions = [], [], [], []
    _panel_identity = {}                      # (fig, panel_key) -> csid.resolve_panel
    for idx, e in enumerate(exps):
        ctx = _entity_context(sd, e)
        # ---- measured vs calculated, resolved for the PANEL as a whole -------
        # A figure flagged "measured" may still hold a calculated line; the flag
        # is inherited by every series unless the caption and the labels say
        # otherwise. Resolving the panel together is what lets a fit be linked
        # to the measured curve instead of minting a second deposition.
        _pkey = (ctx["fig_docling_index"], ctx["panel_key"])
        if _pkey not in _panel_identity:
            _panel_identity[_pkey] = csid.resolve_panel(
                ctx.get("panel_series_labels") or [ctx["source_series"]],
                ctx["caption"], ctx.get("figure_source_flag"))
        _sid = _panel_identity[_pkey].get(ctx["source_series"]) or {
            "kind": "unknown", "confidence": None, "evidence": None, "fit_of": None}
        ctx["series_source_kind"] = _sid["kind"]

        # ---- axis SEMANTICS, then GRANULARITY, as two separate questions ----
        _labels = _axis_labels(sd, e)
        _xsem = caxis.resolve_axis(
            raw_label=_labels.get("x"), raw_quantity=e.get("coordinate"),
            unit=e.get("coordinate_unit"), caption=ctx["caption"],
            context=ctx["body_mentions"], other_axis_label=_labels.get("y"),
            canon=_canon_axis)
        _ysem = caxis.resolve_axis(
            raw_label=_labels.get("y"),
            raw_quantity=(e.get("measurand") or {}).get("quantity"),
            unit=(e.get("measurand") or {}).get("unit"), caption=ctx["caption"],
            context=ctx["body_mentions"], other_axis_label=_labels.get("x"),
            canon=_canon_axis)
        _gran, _gran_ev, _gran_review = cgran.classify(
            x_role=_xsem["axis_role"], source_kind=_sid["kind"],
            caption=ctx["caption"], methods=methods, body=ctx["body_mentions"],
            panel_labels=ctx.get("panel_series_labels") or [],
            series_label=ctx["source_series"], n_points=len(e.get("points") or []),
            measurand_role=_ysem["axis_role"])
        # write the RESOLVED semantics back: the stale canonical coordinate is
        # what the old structural gates read, and it is what turned a Nyquist
        # plot into a spatial profile. Raw label and raw quantity are kept.
        if _xsem["canonical_quantity"]:
            e["coordinate_raw_quantity"] = e.get("coordinate")
            e["coordinate"] = _xsem["canonical_quantity"]
        if _ysem["canonical_quantity"]:
            _md = e.get("measurand") or {}
            _md["raw_quantity"] = _md.get("quantity")
            _md["quantity"] = _ysem["canonical_quantity"]
            e["measurand"] = _md
        e["x_semantics"], e["y_semantics"] = _xsem, _ysem
        ctx["coordinate"] = e.get("coordinate")
        ctx["x_axis_role"] = _xsem["axis_role"]
        ctx["granularity_kind"] = _gran
        ctx["granularity_evidence"] = _gran_ev
        cls = centities.classify(ctx, methods)
        model = centities.CLASS_MODEL[cls["classification"]]
        prov = e.get("provenance") or {}
        ekey = "%s|%s|%s|%s|%s|%s" % (pid, ctx["fig_docling_index"] or "-",
                                      ctx["figure_number"] or "-", ctx["panel_key"],
                                      ctx["source_series"], ctx["representation"])
        eid = "%s-E%03d" % (pid, idx)
        pts = e.get("points") or []
        cpts = e.get("points_canonical") or pts

        # ---- condition assertions for this entity (deterministic) -------------
        prov_kw = dict(paper_id=sd, figure_index=ctx["fig_docling_index"],
                       figure_number=ctx["figure_number"], panel=ctx["panel"])
        ent_assertions = []
        ent_assertions += ccond.from_series_label(ctx["source_series"],
                                                  ctx["panel_series_axis"], **prov_kw)
        # A multi-panel caption states different conditions per panel. The clause for
        # THIS panel is panel-scoped; only the shared preamble is figure-scoped.
        _clauses, _preamble = ccond.caption_panel_clauses(ctx["caption"])
        _my_clause = _clauses.get((ctx["panel"] or "").lower())
        _fig_text = _preamble if _clauses else ctx["caption"]
        _preamble_assertions = (
            ccond.from_caption(_fig_text, **prov_kw)
            # governing-phrase conditions from the caption preamble: a paper's stated
            # process conditions (300 C, 500 cycles, 3 hPa, 150 sccm N2) only became
            # assertions once this ran
            + ccond.conditions_from_prose(
                _fig_text, "figure", "caption",
                "figure %s caption" % ctx["figure_number"], **prov_kw))
        for _a in _preamble_assertions:
            # the shared preamble states values that hold for EVERY panel
            _a["figure_common"] = True
        ent_assertions += _preamble_assertions
        if _my_clause:
            _pk = dict(prov_kw)
            _pk["panel"] = ctx["panel"]
            ent_assertions += ccond.from_caption(_my_clause, **_pk)
            ent_assertions += ccond.conditions_from_prose(
                _my_clause, "panel", "caption",
                "figure %s caption, panel (%s)" % (ctx["figure_number"], ctx["panel"]),
                **_pk)
            ent_assertions += ccond.pressures_from_text(
                _my_clause, "panel", "caption",
                "figure %s caption, panel (%s)" % (ctx["figure_number"], ctx["panel"]),
                **_pk)
        ent_assertions += ccond.conditions_from_prose(
            ctx["body_mentions"], "figure", "body",
            "document.md near Fig %s" % ctx["figure_number"], **prov_kw)
        ent_assertions += _method_assertions(sd)
        ent_assertions += ccond.pressures_from_text(
            ctx["caption"], "figure", "caption", "figure %s caption" % ctx["figure_number"],
            **prov_kw)
        ent_assertions += ccond.pressures_from_text(
            ctx["body_mentions"], "figure", "body",
            "document.md near Fig %s" % ctx["figure_number"], **prov_kw)
        ent_assertions += ccond.pressures_from_text(
            methods, "method", "methods", "methods section", paper_id=sd)
        # adopted/estimated inputs stated per CITED WORK rather than per figure
        ent_assertions += _reference_assertions(sd)
        for a in ent_assertions:
            a["source_entity"] = ekey
        bound, ambiguous, _ = ccond.bind(ent_assertions, ctx,
                                         _figure_varied(sd, ctx["fig_docling_index"]))
        assertions.extend(ent_assertions)

        observations = [{"index": i, "x_raw": p[0], "y_raw": p[1],
                         "x_canonical": (cpts[i][0] if i < len(cpts) else None),
                         "y_canonical": (cpts[i][1] if i < len(cpts) else None)}
                        for i, p in enumerate(pts)]

        ent = {
            "entity_id": eid,
            "entity_key": ekey,
            "entity_class": centities.ENTITY_CLASS[cls["classification"]],
            "classification": cls["classification"],
            "classification_confidence": cls["confidence"],
            "classification_method": cls["method"],
            "classification_evidence": cls["evidence"],
            "signal_families": cls["signal_families"],
            "unresolved_reason": cls["unresolved_reason"],
            "is_current_paper_experiment": model["is_experiment"],
            "paper_id": sd,
            "fig_docling_index": ctx["fig_docling_index"],
            "printed_figure_number": ctx["figure_number"],
            "panel": ctx["panel"],
            "panel_key": ctx["panel_key"],
            "source_series": ctx["source_series"],
            "representation": ctx["representation"],
            "plot_series": True,
            "coordinate": e.get("coordinate"),
            "coordinate_unit": e.get("coordinate_unit_normalized") or e.get("coordinate_unit"),
            "measurand": (e.get("measurand") or {}).get("quantity"),
            "measurand_unit": (e.get("measurand") or {}).get("unit"),
            "measurement_class": model["measurement"],
            "samples_are": model["samples_are"],
            "n_observations": len(observations),
            "observations": observations,
            "between_curve_condition": cls["between_curve_condition"],
            "between_curve_value": cls["between_curve_value"],
            "bound_conditions": bound,
            "ambiguous_conditions": ambiguous,
            "originally_reported_in": cls["originally_reported_in"],
            "reported_in": sd if cls["classification"] == "imported_literature_data" else None,
            "material": e.get("material"), "material_raw": e.get("material_raw"),
            "material_scope_level": e.get("material_scope_level"),
            "material_evidence": e.get("material_evidence"),
            "material_candidates": e.get("material_candidates") or [],
            "material_ambiguity_reason": e.get("material_ambiguity_reason"),
            "multi_material_paper": e.get("multi_material_paper"),
            "chemistry_consistent": e.get("chemistry_consistent"),
            "chemistry_inconsistency": e.get("chemistry_inconsistency"),
            # series-level source identity, independent of the figure flag
            "granularity_kind": _gran,
            "granularity_evidence": _gran_ev,
            "granularity_review_reason": _gran_review,
            "x_axis_role": _xsem["axis_role"],
            "y_axis_role": _ysem["axis_role"],
            "x_semantics": _xsem, "y_semantics": _ysem,
            "series_source_kind": _sid["kind"],
            "series_source_confidence": _sid["confidence"],
            "series_source_evidence": _sid["evidence"],
            "fit_of_series_label": _sid["fit_of"],
            "fit_of_entity": None,          # resolved to an entity_id below
            "geometry_class": e.get("geometry_class"),
            "structure": e.get("structure"),
            # chemistry travels with the entity: a modelling or literature curve still
            # identifies the process the paper studies, and the KB must see it even
            # though the curve is not this paper's experiment
            "precursors": e.get("precursors") or [],
            "coreactants": e.get("coreactants") or [],
            "reactants": e.get("reactants") or [],
            "carrier_gas": e.get("carrier_gas"),
            "process_type": e.get("process_type"),
            "cycle_sequence": e.get("cycle_sequence"),
            "chemistry_provenance": e.get("chemistry_provenance"),
            "provenance": prov,
            "source_record_id": e.get("exp_id"),
        }

        # ---- case minting ---------------------------------------------------
        n_cases, case_status, case_reason = 0, "not_an_experiment", None
        if model["is_experiment"]:
            if model["case"] == 1:
                n_cases, case_status = 1, "supported"
            elif model["case"] == "from_evidence":
                # Case minting FOLLOWS the granularity decision. The old gate
                # re-derived its own axis kind here and could contradict it --
                # a curve typed `independent_process_sweep` then minted nothing
                # because a separate table said its axis was "within run".
                _distinct = sorted({o["x_raw"] for o in observations
                                    if o["x_raw"] is not None})
                if ctx.get("granularity_kind") != "independent_process_sweep":
                    n_cases, case_status = 0, "not_an_independent_sweep"
                    case_reason = ("granularity is %r: its points are observations "
                                   "of one execution, not separate executions"
                                   % ctx.get("granularity_kind"))
                elif len(_distinct) < 2:
                    n_cases, case_status = 1, "single_setting_only"
                    case_reason = "one setting plotted; one execution"
                elif len(_distinct) <= centities.MAX_UNENUMERATED_SETTINGS:
                    n_cases, case_status = len(_distinct), "independent_process_sweep"
                    case_reason = ("%d separately executed settings on a %s axis; %s"
                                   % (len(_distinct), ctx.get("x_axis_role"),
                                      ctx.get("granularity_evidence")))
                else:
                    # too dense to be markers: a saturation curve digitised at 20
                    # points is a line through ~6 films, and guessing which is
                    # which would fabricate depositions
                    n_cases, case_status = 0, "unresolved_settings"
                    case_reason = (
                        "%d distinct x values exceed the %d beyond which digitisation "
                        "density cannot be told from real markers; the paper "
                        "does not enumerate the settings, so the count stays "
                        "unresolved (granularity: %s)"
                        % (len(_distinct), centities.MAX_UNENUMERATED_SETTINGS,
                           ctx.get("granularity_evidence")))
        ent["experimental_case_count"] = n_cases
        ent["experimental_case_status"] = case_status
        ent["experimental_case_reason"] = case_reason
        # lower bound: a corroborated sweep varies its axis, so at least two distinct
        # settings were prepared. This is a property of the sweep, not of how densely
        # the curve was digitised.
        ent["experimental_case_lower_bound"] = (
            n_cases if case_status in ("supported", "enumerated_in_source")
            else (2 if case_status == "unresolved_settings" else 0))
        ent["distinct_setting_values_observed"] = (
            len({o["x_raw"] for o in observations}) if case_status == "unresolved_settings" else None)
        ent["observation_count_unresolved_as_cases"] = (
            len(observations) if case_status == "unresolved_settings" else 0)

        # A "sweep" with a single observation is not a sweep: there is nothing to
        # vary across. It is one measurement at one setting, so it yields exactly one
        # case and no series.
        _degenerate_sweep = (cls["classification"] == "discrete_experimental_sweep"
                             and len(observations) <= 1)
        if _degenerate_sweep:
            n_cases, case_status = (1 if observations else 0), "single_setting_only"
            case_reason = ("classified as a sweep but only %d observation was digitised; "
                           "a sweep requires at least two settings" % len(observations))
            ent["experimental_case_count"] = n_cases
            ent["experimental_case_status"] = case_status
            ent["experimental_case_reason"] = case_reason
            ent["experimental_case_lower_bound"] = n_cases
            ent["distinct_setting_values_observed"] = None

        # a sweep is an ExperimentalSeries regardless of how many cases it supports
        if cls["classification"] == "discrete_experimental_sweep" and not _degenerate_sweep:
            sid = "%s-S%03d" % (pid, len(series))
            ent["experimental_series_id"] = sid
            series.append({
                "series_id": sid, "doi": sd, "entity_id": eid, "entity_key": ekey,
                "series_varies": e.get("coordinate"),
                "series_varies_unit": ent["coordinate_unit"],
                "measurand": e.get("measurand"),
                "n_observations": len(observations),
                "supported_case_count": n_cases,
                "case_count_lower_bound": ent["experimental_case_lower_bound"],
                "distinct_setting_values_observed": ent["distinct_setting_values_observed"],
                "case_count_status": case_status,
                "case_count_reason": case_reason,
                "between_curve_condition": cls["between_curve_condition"],
                "between_curve_value": cls["between_curve_value"],
                "provenance": prov, "series_name": e.get("series_name"),
                "material": e.get("material"), "relevance": e.get("relevance"),
            })

        entities.append(ent)

        # ---- backward-compatible ExperimentalCase records --------------------
        if model["is_experiment"] and n_cases >= 1:
            for k in range(n_cases):
                c = json.loads(json.dumps(e))
                c["exp_id"] = eid if n_cases == 1 else "%s-C%02d" % (eid, k)
                c["entity_id"] = eid
                c["entity_key"] = ekey
                # the paper is a FIELD, never something to parse back out of the
                # id: `exp_id.split("-")[0]` already broke on hyphenated DOIs
                # (10.1007_s11671-010-9676-0 -> "10.1007_s11671")
                c["paper_id"] = sd
                c["doi"] = sd
                c["printed_figure_number"] = ctx["figure_number"]
                c["panel"] = ctx["panel"]
                c["figure_slug"] = None      # filled by assign_experiment_ids
                c["entity_class"] = "ExperimentalCase"
                c["record_kind"] = "ExperimentalCase"
                c["measurement_class"] = model["measurement"]
                c["classification"] = cls["classification"]
                c["classification_confidence"] = cls["confidence"]
                c["granularity"] = {"continuous_trace": "trace",
                                    "experimental_profile": "profile",
                                    "multi_output_measurement": "multi_output"}.get(
                                        cls["classification"], "case")
                c["points"] = pts
                c["points_canonical"] = cpts
                c["n_observations"] = len(observations)
                c["observations_are_experiments"] = False
                if cls["classification"] == "discrete_experimental_sweep":
                    c["in_series"] = ent.get("experimental_series_id")
                    c["case_index"] = k
                for b in bound:
                    if b.get("quantity") and b.get("value") is not None:
                        c.setdefault("controlled", []).append({
                            "quantity": b["quantity"], "value": _f(b["value"]),
                            "unit": b.get("unit"), "of_reactant": b.get("of_reactant"),
                            # keep the ORIGINAL evidence kind as the source label
                            # (caption / series_label / body / methods) so downstream
                            # provenance checks still see where the value came from
                            "source": {"caption": "caption", "series_label": "series",
                                       "body": "body", "methods": "methods",
                                       "table": "table"}.get(b.get("source_kind"),
                                                             b.get("source_kind") or "condition_assertion"),
                            "assertion_source_kind": b.get("source_kind"),
                            "scope": b.get("bound_at_scope"),
                            "context_status": "resolved",
                            "assertion_status": b.get("assertion_status"),
                            "species": b.get("species"),
                            "origin": {"level": b.get("bound_at_scope"),
                                       "from": b.get("source_kind"),
                                       "evidence": b.get("raw_evidence"),
                                       "locator": b.get("evidence_locator")},
                        })
                if ambiguous:
                    c["ambiguous_conditions"] = ambiguous
                c["controlled"], _cf = clive.mark_ambiguous_context(c.get("controlled") or [])
                if _cf:
                    c["context_conflicts"] = _cf
                r_obj = recipe_mod.from_experiment(c)
                c["recipe"] = r_obj.to_dict()
                c["recipe"]["completeness"] = r_obj.completeness()
                cases.append(c)
    # ---- attach each fit/calculated curve to the measurement it describes ----
    # Done after the loop because the measured sibling may be resolved later than
    # the fit. A fit links to a measurement; it never mints a DepositionRun or a
    # Sample of its own, which is what `experimental_case_count == 0` already
    # guarantees for the `fit` class.
    _by_panel_label = {}
    for ent in entities:
        _by_panel_label[(ent["fig_docling_index"], ent["panel_key"],
                         ent["source_series"])] = ent["entity_id"]
    for ent in entities:
        lab = ent.get("fit_of_series_label")
        if not lab:
            continue
        tgt = _by_panel_label.get((ent["fig_docling_index"], ent["panel_key"], lab))
        if tgt and tgt != ent["entity_id"]:
            ent["fit_of_entity"] = tgt

    # ---- ProcessRun / MeasurementEvent / ResultSeries ---------------------
    # One plot series is NOT one physical experiment. Several channels of one
    # measurement (the six XPS elements of a depth profile) are one measurement
    # event on one sample; the entity that carries the case is the first of the
    # group and the rest link to it instead of minting five more depositions.
    _events = defaultdict(list)
    for ent in entities:
        key = (ent.get("fig_docling_index"), ent.get("panel_key"),
               ent.get("granularity_kind"))
        _events[key].append(ent)
    for (fig, pan, gran), members in _events.items():
        shared = (gran == "multi_output_measurement" and len(members) > 1)
        holder = members[0]
        for i, ent in enumerate(members):
            ent["measurement_event_id"] = None      # filled after ids exist
            ent["shares_measurement_event"] = shared
            ent["shares_physical_case_with"] = None
            if shared and i:
                # the channel carries no separate physical case
                ent["experimental_case_count"] = 0
                ent["experimental_case_status"] = "shared_measurement_event"
                ent["experimental_case_reason"] = (
                    "one of %d channels of a single measurement event on the same "
                    "sample; the physical case is carried by the first channel"
                    % len(members))
                ent["_shares_with"] = holder

    # ---- final, figure-anchored experiment ids ---------------------------
    # Assigned last because "does this figure/panel need a suffix?" is a property
    # of the GROUP: a figure contributing one record keeps a clean `Fig7a`, and
    # only a shared figure/panel gains `__exp01`, `__exp02`.
    assign_experiment_ids(entities, pid)
    remap = {}
    for ent in entities:
        remap[ent["entity_id"]] = ent["experiment_id"]
    for ent in entities:
        ent["provisional_entity_id"] = ent["entity_id"]
        ent["entity_id"] = ent["experiment_id"]
        if ent.get("fit_of_entity"):
            ent["fit_of_entity"] = remap.get(ent["fit_of_entity"], ent["fit_of_entity"])
    for c in cases:
        old = c.get("entity_id")
        new = remap.get(old, old)
        # a figure/panel that yields several CASES from one curve keeps its
        # per-case suffix, appended to the new id rather than the old one
        suffix = ""
        m = re.search(r"-C(\d+)$", str(c.get("exp_id") or ""))
        if m:
            suffix = "__case%s" % m.group(1)
        c["entity_id"] = new
        c["exp_id"] = new + suffix
        for ctrl in c.get("controlled") or []:
            o = ctrl.get("origin") or {}
            if o.get("experiment_id"):
                o["experiment_id"] = c["exp_id"]
    for ent in entities:
        holder = ent.pop("_shares_with", None)
        if holder is not None:
            ent["shares_physical_case_with"] = holder["entity_id"]
        ent["result_series_id"] = ent["entity_id"]
        ent["physical_case_id"] = (
            ent.get("shares_physical_case_with") or ent["entity_id"]
        ) if (ent.get("experimental_case_count") or
              ent.get("shares_physical_case_with")) else None
    # a measurement event is shared by every channel of one panel measurement
    for (fig, pan, gran), members in _events.items():
        eid = members[0]["entity_id"] + ("__meas" if len(members) > 1 else "")
        for ent in members:
            ent["measurement_event_id"] = eid
    for s in series:
        s["entity_id"] = remap.get(s.get("entity_id"), s.get("entity_id"))
        if s.get("series_id"):
            s["series_id"] = "%s__series" % s["entity_id"]
    return entities, cases, series, assertions


#: which of the nine entity classes each result row reports under. Kept explicit
#: rather than derived so a new class cannot silently fall out of the summary.
RESULT_KIND = {
    "continuous_trace": "continuous_experimental_run",
    "experimental_profile": "experimental_profile",
    "multi_output_measurement": "multi_output_measurement",
    "discrete_experimental_sweep": "discrete_experimental_sweep",
    "simulation": "simulation",
    "model_sweep": "model_curve",
    "fit": "fit_or_calculated_representation",
    "imported_literature_data": "imported_literature_data",
    "derived_representation": "derived_representation",
    "conceptual_figure": "conceptual_figure",
    "unknown": "unresolved",
}


def build_results_view(sd, pid, entities, curve_records):
    """One row per SOURCE SERIES — the complete extraction result for a paper.

    The regression diagnosis found no data loss anywhere: 659 raw series became
    659 records and 663 entities, with zero orphans. What it found was that the
    result was split across experiments.json (physical cases), series.json
    (sweeps) and entities.json (everything else), and every consumer read only
    the first. A 19-curve paper therefore looked like a 4-record paper.

    This view is the fix. It carries the identity, granularity decision,
    chemistry and provenance of every curve, so no consumer needs to know how
    the other files are partitioned.
    """
    by_key = {}
    for r in curve_records:
        prov = r.get("provenance") or {}
        by_key[(str(prov.get("fig_docling_index") or ""),
                str(prov.get("panel") or ""),
                str(r.get("series_value") or ""))] = r
    rows = []
    for ent in entities:
        rec = by_key.get((str(ent.get("fig_docling_index") or ""),
                          str(ent.get("panel") or ""),
                          str(ent.get("source_series") or ""))) or {}
        prov = ent.get("provenance") or {}
        rows.append({
            "result_id": ent["entity_id"],
            "paper_id": sd,
            "fig_docling_index": ent.get("fig_docling_index"),
            "printed_figure_number": ent.get("printed_figure_number"),
            "panel": ent.get("panel"),
            # the figure/panel anchor carried by the id, so a consumer can group
            # by figure without re-parsing the id
            "figure_slug": ent.get("figure_slug"),
            "id_has_panel": ent.get("id_has_panel"),
            "id_suffix_reason": ent.get("id_suffix_reason"),
            "source_series_id": ent.get("entity_key"),
            "source_series_label": ent.get("source_series"),
            "n_points": ent.get("n_observations"),
            "points": ent.get("observations"),
            "representation": ent.get("representation"),
            # ---- identity -------------------------------------------------
            "source_kind": ent.get("series_source_kind"),
            "source_kind_confidence": ent.get("series_source_confidence"),
            "source_kind_evidence": ent.get("series_source_evidence"),
            "figure_source_flag": (rec.get("source") if rec else None),
            # the review's vocabulary: granularity first, entity class as the
            # fallback for the classes granularity does not decide (fits,
            # imported literature, conceptual figures)
            # Granularity names the kind for MEASURED curves. It must never
            # override a provenance decision: a simulated curve stays a model
            # however spatial its x axis is, and a re-plot stays a re-plot.
            "result_kind": (
                RESULT_KIND.get(ent.get("classification"), "unresolved")
                if ent.get("classification") in (
                    "simulation", "model_sweep", "fit", "derived_representation",
                    "imported_literature_data", "conceptual_figure")
                else (ent.get("granularity_kind")
                      if ent.get("granularity_kind") in cgran.KINDS
                      and ent.get("granularity_kind") != "unresolved"
                      else RESULT_KIND.get(ent.get("classification"),
                                           "unresolved"))),
            "granularity_kind": ent.get("granularity_kind"),
            "granularity_evidence": ent.get("granularity_evidence"),
            "granularity_review_reason": ent.get("granularity_review_reason"),
            "x_axis_role": ent.get("x_axis_role"),
            "y_axis_role": ent.get("y_axis_role"),
            "x_semantics": ent.get("x_semantics"),
            "y_semantics": ent.get("y_semantics"),
            "physical_case_id": ent.get("physical_case_id"),
            "measurement_event_id": ent.get("measurement_event_id"),
            "result_series_id": ent.get("result_series_id") or ent["entity_id"],
            "shares_physical_case_with": ent.get("shares_physical_case_with"),
            "entity_class": ent.get("entity_class"),
            "classification": ent.get("classification"),
            "classification_confidence": ent.get("classification_confidence"),
            "classification_method": ent.get("classification_method"),
            "classification_evidence": ent.get("classification_evidence"),
            "is_current_paper_experiment": ent.get("is_current_paper_experiment"),
            # ---- granularity ----------------------------------------------
            "granularity": ("point_level"
                            if (ent.get("experimental_case_count") or 0) > 1
                            else "curve_level"
                            if (ent.get("experimental_case_count") or 0) == 1
                            else "no_physical_case"),
            "experimental_case_count": ent.get("experimental_case_count"),
            "experimental_case_status": ent.get("experimental_case_status"),
            "experimental_case_reason": ent.get("experimental_case_reason"),
            "experimental_case_lower_bound": ent.get("experimental_case_lower_bound"),
            "samples_are": ent.get("samples_are"),
            # ---- links ------------------------------------------------------
            "measurement_class": ent.get("measurement_class"),
            "fit_of_entity": ent.get("fit_of_entity"),
            "fit_of_series_label": ent.get("fit_of_series_label"),
            "originally_reported_in": ent.get("originally_reported_in"),
            # ---- chemistry --------------------------------------------------
            "material": ent.get("material"),
            "material_scope_level": ent.get("material_scope_level"),
            "material_evidence": ent.get("material_evidence"),
            "material_candidates": ent.get("material_candidates") or [],
            "material_ambiguity_reason": ent.get("material_ambiguity_reason"),
            "multi_material_paper": ent.get("multi_material_paper"),
            "precursors": ent.get("precursors") or [],
            "coreactants": ent.get("coreactants") or [],
            "chemistry_provenance": ent.get("chemistry_provenance"),
            "chemistry_consistent": ent.get("chemistry_consistent"),
            "chemistry_inconsistency": ent.get("chemistry_inconsistency"),
            # ---- axes + provenance ------------------------------------------
            "coordinate": ent.get("coordinate"),
            "coordinate_unit": ent.get("coordinate_unit"),
            "measurand": ent.get("measurand"),
            "measurand_unit": ent.get("measurand_unit"),
            "caption": prov.get("caption"),
            "provenance": prov,
            "bound_condition_count": len(ent.get("bound_conditions") or []),
            "ambiguous_condition_count": len(ent.get("ambiguous_conditions") or []),
        })
    return {
        "paper_id": sd,
        "source_series_total": len(entities),
        "result_records": len(rows),
        "summary": _result_summary(rows),
        "results": rows,
    }


def _result_summary(rows):
    from collections import Counter
    kinds = Counter(r["result_kind"] for r in rows)
    ids = lambda k: sorted(r["result_id"] for r in rows if r["result_kind"] == k)
    return {
        # --- the review's reporting vocabulary, each count auditable ---------
        "source_figure_series_ids": sorted(r["result_id"] for r in rows),
        "physical_case_ids": sorted({r["physical_case_id"] for r in rows
                                     if r.get("physical_case_id")}),
        "measurement_event_ids": sorted({r["measurement_event_id"] for r in rows
                                         if r.get("measurement_event_id")}),
        "physical_process_runs": len({r["physical_case_id"] for r in rows
                                      if r.get("physical_case_id")}),
        "measurement_events": len({r["measurement_event_id"] for r in rows
                                   if r.get("measurement_event_id")}),
        "result_series": len(rows),
        "independent_sweep_cases_minted": sum(
            r["experimental_case_count"] or 0 for r in rows
            if r["result_kind"] == "independent_process_sweep"),
        "independent_process_sweeps": kinds.get("independent_process_sweep", 0),
        "continuous_or_longitudinal_runs": kinds.get(
            "continuous_or_longitudinal_run", 0),
        "spatial_profiles_g": kinds.get("spatial_profile", 0),
        "measurement_scans": kinds.get("measurement_scan", 0),
        "multi_output_measurements_g": kinds.get("multi_output_measurement", 0),
        "models_and_simulations": kinds.get("model_or_simulation", 0)
        + kinds.get("simulation", 0) + kinds.get("model_curve", 0),
        "unresolved_granularity": sum(
            1 for r in rows
            if r.get("granularity_kind") in (None, "unresolved")),
        "unresolved_granularity_ids": sorted(
            r["result_id"] for r in rows
            if r.get("granularity_kind") in (None, "unresolved")),
        "granularity_review_queue": sorted(
            (r["result_id"], r.get("granularity_review_reason"))
            for r in rows if r.get("granularity_review_reason")),
        "source_figure_series": len(rows),
        "resolved_result_records": len(rows),
        "physical_experimental_cases": sum(r["experimental_case_count"] or 0
                                           for r in rows),
        "continuous_experimental_runs": kinds.get("continuous_experimental_run", 0)
        + kinds.get("continuous_or_longitudinal_run", 0),
        "discrete_experimental_sweeps": kinds.get("discrete_experimental_sweep", 0)
        + kinds.get("independent_process_sweep", 0),
        "discrete_experimental_cases": sum(
            r["experimental_case_count"] or 0 for r in rows
            if r["result_kind"] == "discrete_experimental_sweep"),
        "experimental_profiles": kinds.get("experimental_profile", 0)
        + kinds.get("spatial_profile", 0),
        "multi_output_measurements": kinds.get("multi_output_measurement", 0)
        + kinds.get("measurement_scan", 0),
        "fits_or_calculated_representations": kinds.get(
            "fit_or_calculated_representation", 0),
        "simulations": kinds.get("simulation", 0)
        + kinds.get("model_or_simulation", 0),
        "model_curves": kinds.get("model_curve", 0),
        "imported_literature_data": kinds.get("imported_literature_data", 0),
        "derived_representations": kinds.get("derived_representation", 0),
        "unresolved_series": kinds.get("unresolved", 0),
        # A generic model curve (reactant A into a channel) has no film material,
        # which is not an ambiguity. Only a MEASURED series without a resolved
        # material is one.
        "material_ambiguities": sum(
            1 for r in rows
            if r["material"] is None and r["is_current_paper_experiment"]),
        "material_not_applicable_model_curves": sum(
            1 for r in rows
            if r["material"] is None and not r["is_current_paper_experiment"]),
        "chemistry_inconsistencies": sum(1 for r in rows
                                         if r["chemistry_consistent"] is False),
        "sweeps_with_unresolved_settings": sum(
            1 for r in rows
            if r["experimental_case_status"] == "unresolved_settings"),
    }


def write_review_manifest(sd, pid, paper_dir, results, entities):
    """papers/<doi>/review.json — the paper-by-paper review entry point.

    Lists the files in this folder and the figure-by-figure result table, so a
    reviewer can work through one paper without querying the corpus.
    """
    figs = defaultdict(list)
    for r in results["results"]:
        # group by the ACTUAL figure/panel, from provenance. `figure_slug` is
        # the id anchor and is right, but fall back to the printed number and
        # panel rather than dropping every record into one "?" bucket.
        slug = r.get("figure_slug")
        if not slug:
            fn = str(r.get("printed_figure_number") or "").strip()
            pan = str(r.get("panel") or "").strip().lower()
            slug = ("Fig%s%s" % (fn, pan if len(pan) == 1 else "")) if fn \
                else ("FigIdx%s" % r.get("fig_docling_index")
                      if r.get("fig_docling_index") else "NoFig")
        figs[slug].append(r)
    by_figure = []
    for slug in sorted(figs, key=lambda s: (len(s), s)):
        rows = figs[slug]
        by_figure.append({
            "figure_slug": slug,
            "printed_figure_number": rows[0]["printed_figure_number"],
            "panel": rows[0]["panel"],
            "fig_docling_index": rows[0]["fig_docling_index"],
            "n_series": len(rows),
            # ids split by what they identify, so a reviewer can tell a
            # deposition from a spectrum from a simulated curve
            "physical_case_ids": sorted({r["physical_case_id"] for r in rows
                                         if r.get("physical_case_id")}),
            "measurement_event_ids": sorted({r["measurement_event_id"]
                                             for r in rows
                                             if r.get("measurement_event_id")}),
            "result_series_ids": [r["result_id"] for r in rows],
            "model_or_simulation_ids": sorted(
                r["result_id"] for r in rows
                if r["result_kind"] in ("model_or_simulation", "simulation",
                                        "model_curve",
                                        "fit_or_calculated_representation")),
            "unresolved_ids": sorted(
                r["result_id"] for r in rows
                if r.get("granularity_kind") in (None, "unresolved")),
            "result_kinds": sorted({r["result_kind"] for r in rows}),
            "materials": sorted({r["material"] for r in rows if r["material"]}),
            "physical_cases": sum(r["experimental_case_count"] or 0 for r in rows),
            "caption": (rows[0]["caption"] or "")[:300],
        })
    manifest = {
        "paper_id": pid,
        "doi": sd,
        "folder": "papers/%s" % pid,
        "files": {
            "pdf": "paper.pdf" if (paper_dir / "paper.pdf").exists() else None,
            "extracted": sorted(x.name for x in P.extracted_dir(pid).iterdir())
            if P.extracted_dir(pid).exists() else [],
            "resolved": sorted(x.name for x in P.resolved_dir(pid).iterdir())
            if P.resolved_dir(pid).exists() else [],
            "canonical": sorted(x.name for x in P.canonical_dir(pid).iterdir())
            if P.canonical_dir(pid).exists() else [],
        },
        "experiment_id_format": (
            "<doi>__Fig<N>[<panel>][__exp<NN>] — figure number and panel come "
            "from extraction provenance; the __exp suffix appears only when one "
            "figure/panel yields several records"),
        "summary": results["summary"],
        "by_figure": by_figure,
    }
    (paper_dir / "review.json").write_text(json.dumps(manifest, indent=1,
                                                      ensure_ascii=False))
    return manifest


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def to_experiments(sd, scout, records, card):
    # Chemistry is resolved PER MATERIAL, never by list position. The scout emits
    # materials/precursors/coreactants as three independent lists, so `[0]` carried no
    # information — it assigned DEZ to an Al2O3 experiment in 10.1116_1.4938104 simply
    # because DEZ sorted first. Ambiguity is preferred over an unsupported guess.
    # Resolved per EXPERIMENT MATERIAL (cached), so a multi-material paper gives each
    # film its own chemistry instead of all of them sharing element zero.
    _chem_cache = {}

    def _chem_for(material):
        if material not in _chem_cache:
            _chem_cache[material] = cprop.resolve_experiment_chemistry(
                material, None, card, scout,
                canon_precursor=lib.canon_precursor, canon_coreactant=lib.canon_coreactant)
        return _chem_cache[material]

    def _reactants_for(ch):
        rs = [{"label": "A", "role": "precursor", "species": ch.precursor}]
        if ch.co_reactant:
            rs.append({"label": "B", "role": "coreactant", "species": ch.co_reactant})
        return rs

    def _chem_prov(ch):
        # Inferred chemistry stays distinguishable from explicitly stated chemistry:
        # material_element_match is a deterministic inference, NOT a source mapping.
        return {"resolution_status": ch.resolution_status,
                "resolution_method": ch.resolution_method,
                "confidence": ch.confidence, "source_level": ch.source_level,
                "directly_extracted": ch.directly_extracted,
                "material_scope": ch.material_scope,
                "supporting_evidence": ch.supporting_evidence,
                "ambiguity_reason": ch.ambiguity_reason,
                "candidate_mappings": ch.candidate_mappings}
    carrier = {"species": card.get("carrier_gas")} if card.get("carrier_gas") else None
    ptype = lib.canon_process(card.get("process_type")) or card.get("process_type")
    base_ctrl = paper_conditions(card)
    # geometry/model parameters are re-read PER MATERIAL below; only the
    # material-independent ones belong in the shared base
    geom_struct, geom_class, _geom_all = geometry_facts(sd, scout.get("materials"))
    _geom_cache = {}

    def _geom_for(mat):
        if mat not in _geom_cache:
            _geom_cache[mat] = geometry_facts(
                sd, scout.get("materials"), material=mat)[2]
        return _geom_cache[mat]
    pid = short_pid(sd)
    exps = []
    for r in records:
        mq = lib.canon_quantity((r.get("measurand") or {}).get("quantity")) or (r.get("measurand") or {}).get("quantity")
        cq = lib.canon_quantity(r.get("coordinate")) or r.get("coordinate")
        pts = [p for p in (r.get("points") or []) if isinstance(p, list) and len(p) == 2]

        # ---- units: convert VALUES together with the unit -------------------
        # The previous code called _norm_unit(mq, None, unit): with value=None the
        # converter returned immediately, so the unit label was kept but the y
        # values were never rescaled. Å/cycle and nm/cycle sat side by side as
        # bare numbers. Both axes are now converted for real, and the RAW axis
        # metadata is preserved next to the converted values.
        raw_mu = (r.get("measurand") or {}).get("unit")
        raw_cu = r.get("coordinate_unit")
        labels = _axis_labels(sd, r)
        ys, mu, y_conv = clive.normalize_measurand(mq, raw_mu, [p[1] for p in pts],
                                                   label=labels.get("y"))
        raw_cu_out, cu_norm, c_dimensionless = clive.coordinate_unit(
            cq, raw_cu, label=labels.get("x"))
        xs, cu_conv = [p[0] for p in pts], None
        if cu_norm:
            xs, cu_target, c_conv = clive.normalize_measurand(cq, cu_norm,
                                                              [p[0] for p in pts],
                                                              label=labels.get("x"))
            if c_conv.get("values_rescaled"):
                cu_norm, cu_conv = cu_target, c_conv
        canon_pts = [[x, y] for x, y in zip(xs, ys)]
        # ---- material from the NARROWEST evidence, never by list position ----
        # `r["material"]` is trustworthy only when stage 05 read it off the series
        # legend; for every other legend it wrote scout.materials[0], which
        # assigned Al2O3 to a caption that says "TiO2 from TiCl4 and H2O". The
        # ladder re-resolves from the caption/scout note the record already
        # carries, and REFUSES on a multi-material paper with no figure-level
        # evidence rather than falling back to element zero.
        _prov_r = r.get("provenance") or {}
        # the caption is stored truncated on the record; the figure's own full
        # caption is what the panel clause has to be split out of
        _full_cap = _figure_caption(sd, _prov_r.get("fig_docling_index")) \
            or _prov_r.get("caption")
        _pan_clauses, _ = ccond.caption_panel_clauses(_full_cap or "")
        # does this figure hand a DIFFERENT material to different panels?
        _panel_mats = {m for cl in _pan_clauses.values()
                       for m in cschem._named(cl, scout.get("materials"))}
        _scoped = cschem.resolve_material(
            panel_assigns_materials=(len(_panel_mats) > 1),
            series_label=r.get("material_raw"),
            caption=_full_cap,
            panel_clause=_pan_clauses.get(str(_prov_r.get("panel") or "").lower()),
            drill_why=_drill_why(sd, _prov_r.get("fig_docling_index")),
            body=_figure_body(sd, _prov_r.get("figure_number")),
            materials=scout.get("materials"),
            legend_is_material=(r.get("material")
                                if r.get("series_kind") == "material" else None))
        mat = lib.canon_material(_scoped["material"]) or _scoped["material"]
        # an explicit "<material> from <precursor> and <coreactant>" in THIS
        # figure's caption outranks any paper-level default
        _cap_chem = cschem.caption_chemistry(_prov_r.get("caption"),
                                             scout.get("materials"))
        # an explicit methods mapping ("... for the growth of SiO2, TiO2, Al2O3
        # and HfO2, respectively") beats element matching, which depends on a
        # hand-curated hint table and left SiO2 and HfO2 with no precursor at all
        _meth_chem = _methods_mapping(sd, scout.get("materials")).get(mat)
        if _meth_chem and not _cap_chem:
            prec_c = lib.canon_precursor(_meth_chem["precursor"]) or _meth_chem["precursor"]
            _ch = _chem_for(mat)
            core_c = _ch.co_reactant
            _chem_prov_extra = {
                "resolution_status": "fully_resolved" if core_c else "precursor_only",
                "resolution_method": "methods_respectively_mapping",
                "confidence": 0.9, "source_level": "paper_methods",
                "directly_extracted": True, "material_scope": mat,
                "supporting_evidence": _meth_chem["evidence"],
                "ambiguity_reason": None, "candidate_mappings": None}
        elif _cap_chem and mat and _cap_chem["material"] == _scoped["material"]:
            prec_c = lib.canon_precursor(_cap_chem["precursor"]) or _cap_chem["precursor"]
            core_c = lib.canon_coreactant(_cap_chem["coreactant"]) or _cap_chem["coreactant"]
            _ch = _chem_for(mat)
            _chem_prov_extra = {
                "resolution_status": "fully_resolved",
                "resolution_method": "figure_caption_explicit",
                "confidence": 0.95, "source_level": "figure",
                "directly_extracted": True, "material_scope": mat,
                "supporting_evidence": _cap_chem["evidence"],
                "ambiguity_reason": None, "candidate_mappings": None}
        else:
            _ch = _chem_for(mat)
            prec_c, core_c = _ch.precursor, _ch.co_reactant
            _chem_prov_extra = None
        reactants = ([{"label": "A", "role": "precursor", "species": prec_c}]
                     if prec_c else [])
        if core_c:
            reactants.append({"label": "B", "role": "coreactant", "species": core_c})
        # The element check is a heuristic over a symbol/name table; an explicit
        # statement in the source is not. When the paper itself pairs the film
        # with its precursor ("... for the growth of SiO2, TiO2, Al2O3 and HfO2,
        # respectively"), the source wins -- otherwise TDMACpH, whose trailing H
        # is the hafnium, reads as a contradiction of HfO2.
        if (_chem_prov_extra or {}).get("directly_extracted"):
            _consistent, _incons = True, None
        else:
            _consistent, _incons = cschem.consistent(mat, prec_c, core_c)
        press_ctrl = pressure10.pressure_facts(sd, reactants)
        geom_ctrl = _geom_for(mat)
        base_ctrl_m = base_ctrl + geom_ctrl
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
        # ---- granularity from the ONTOLOGY AXIS ROLE, not the point count ----
        # Old rule: "profile" if len(pts) > 1. That made every 5-point temperature
        # sweep a single "profile experiment". A coordinate axis (position, depth)
        # is one profile; a CONDITION axis (temperature, cycles, pulse time) means
        # each point is its own experiment and the curve is an ExperimentSeries.
        _granularity, _gran_reason = clive.axis_granularity(cq, len(pts))
        e = {
            "material": mat, "material_raw": r.get("material"),
            "material_scope_level": _scoped["scope_level"],
            "material_evidence": _scoped["evidence"],
            "material_candidates": _scoped["candidates"],
            "material_ambiguity_reason": _scoped["ambiguity_reason"],
            "multi_material_paper": _scoped["multi_material_paper"],
            "chemistry_consistent": _consistent,
            "chemistry_inconsistency": _incons,
            "precursors": [prec_c] if prec_c else [], "coreactants": [core_c] if core_c else [],
            "reactants": reactants, "carrier_gas": carrier, "process_type": ptype,
            "cycle_sequence": "AB" if core_c else "A",
            "controlled": _dedup_pressures(base_ctrl_m + panel_ctrl + series_ctrl + press_ctrl),
            # measurand/coordinate keep the RAW unit AND the canonical unit side
            # by side; `unit` stays the KB-canonical one so existing consumers
            # keep working, `raw_unit` is the untouched source value.
            "measurand": {"quantity": mq, "unit": mu, "raw_unit": raw_mu,
                          "family": lib.family(mq), "unit_conversion": y_conv},
            "coordinate": cq, "coordinate_family": lib.family(cq),
            # spec §2.3: a coordinate number is never stored without its unit.
            # `coordinate_unit_normalized` is None only when the unit could not be
            # resolved, and then `coordinate_unit_status` says why.
            "coordinate_unit": raw_cu_out,
            "coordinate_unit_normalized": cu_norm,
            "coordinate_is_dimensionless": c_dimensionless,
            "coordinate_unit_status": ("resolved" if cu_norm else "unresolved"),
            "coordinate_unit_reason": (None if cu_norm else
                                       "no parseable unit for coordinate %r and the "
                                       "ontology does not declare it dimensionless" % cq),
            "coordinate_unit_conversion": cu_conv,
            "points": pts,                       # RAW digitized points, unchanged
            "points_canonical": canon_pts,       # same points in canonical units
            "granularity": _granularity,
            "relevance": "experimental" if r.get("source") == "measured" else "model",
            "is_model_result": r.get("source") == "simulated",
            "analysis_ready": bool(pts and mq),
            "exp_id": exp_id,
            "provenance": {**(r.get("provenance") or {}), "doi": sd},
            "series_name": series_name,             # display only; built from structure, never re-parsed
            "phase": r.get("phase"),                # crystallographic phase (e.g. "c-MoS2") or None
            "structure": geom_struct, "geometry_class": geom_class,
            "chemistry_provenance": _chem_prov_extra or _chem_prov(_ch),
            # dependent = the measured output; varies = the swept coordinate (profiles).
            # Populated so the shared 0706 consumers (evaluate_kb, kg, similarity) see the
            # measured/swept quantities the same way as old-pipeline records.
            # `varies` is the swept COORDINATE of a profile. A condition sweep does
            # not "vary" inside one experiment — it varies ACROSS the experiments of
            # its ExperimentSeries, which is recorded as series_varies below.
            "varies": [cq] if (cq and _granularity == "profile") else [],
            "series_varies": cq if (cq and _granularity == "series") else None,
            "granularity_reason": _gran_reason,
            "axis_role": clive.axis_role_of(clive.canon_quantity(cq) or cq),
            "dependent": [{"quantity": mq, "unit": mu, "raw_unit": raw_mu,
                           "family": lib.family(mq)}] if mq else [],
            "issues": [] if pts else ["no-points"],
        }
        # scope every controlled value and flag same-scope conflicts so a paper-level
        # geometry value with several candidates is NOT broadcast (spec §2.7)
        e["controlled"], _conflicts = clive.mark_ambiguous_context(e["controlled"])
        if _conflicts:
            e["context_conflicts"] = _conflicts
        r_obj = recipe_mod.from_experiment(e)
        e["recipe"] = r_obj.to_dict(); e["recipe"]["completeness"] = r_obj.completeness()
        exps.append(e)
    if not exps:
        # No figure data digitized — still admit the paper as ONE paper-level experiment
        # (attached to its Paper node in the KG) carrying chemistry + conditions + the data
        # modalities the scout saw (XRD, spectra, imaging …), so the paper enters the KB.
        _pm = lib.canon_material((scout.get("materials") or [None])[0]) \
            or (scout.get("materials") or [None])[0]
        _pch = _chem_for(_pm)
        exps.append(paper_level_experiment(sd, scout, card, pid, _reactants_for(_pch), carrier,
                                           ptype, _pch.precursor, _pch.co_reactant,
                                           base_ctrl, geom_struct, geom_class,
                                           _chem_prov(_pch)))
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
    # Re-scope AFTER the species properties are appended, so every controlled value —
    # including the ontology reference data added here — carries its applicability
    # scope and any same-scope conflict flag. Doing this only inside the record loop
    # left the late-appended species values unscoped.
    for e in exps:
        e["controlled"], _c = clive.mark_ambiguous_context(e.get("controlled") or [])
        if _c:
            e["context_conflicts"] = _c
    return pid, exps


def paper_level_experiment(sd, scout, card, pid, reactants, carrier, ptype, prec_c, core_c,
                           base_ctrl, geom_struct=None, geom_class=None, chem_prov=None):
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
        "controlled": _dedup_pressures(base_ctrl + pressure10.pressure_facts(sd, reactants)),
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
        "chemistry_provenance": chem_prov,
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
    want_all = "--all" in sds
    sds = [s for s in sds if not s.startswith("--")]
    if want_all or not sds:
        # every paper in the corpus manifest (the authoritative 31-paper list)
        sds = csources.papers()
        sds = [s for s in sds if (P.extracted_dir(s) / "scout.json").exists()]
        print("[to-kb] --all: %d paper(s) from the manifest" % len(sds))
    client = None
    if not resolve_only:
        from google import genai
        client = genai.Client(api_key=ex._load_key())
    TI = TO = 0
    for sd in sds:
        d = P.extracted_dir(sd)
        scout = json.loads((d / "scout.json").read_text())
        records = json.loads((d / "records.json").read_text()) if (d / "records.json").exists() else []
        card, tok = get_card(sd, scout, client)   # cached; LLM only first time (skipped on --resolve-only)
        TI += tok.get("in", 0); TO += tok.get("out", 0)
        pid, curve_records = to_experiments(sd, scout, records, card)
        # Each curve becomes a TYPED SOURCE ENTITY. Experimental cases are minted
        # only where the paper supports them; observations stay observations.
        entities, exps, series, assertions = resolve_source_entities(sd, curve_records, pid)
        outdir = P.resolved_dir(pid)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "entities.json").write_text(json.dumps(entities, indent=1))
        (outdir / "experiments.json").write_text(json.dumps(exps, indent=1))
        (outdir / "series.json").write_text(json.dumps(series, indent=1))
        (outdir / "assertions.json").write_text(json.dumps(assertions, indent=1))
        (outdir / "counts.json").write_text(json.dumps(_counts(entities, exps, series), indent=1))
        # THE authoritative extraction-result surface: one row per source curve,
        # complete on its own. experiments.json stays a derived physical-experiment
        # view; nobody should have to join three files to find out what a paper's
        # figures contain.
        _results = build_results_view(sd, pid, entities, curve_records)
        (outdir / "results.json").write_text(json.dumps(_results, indent=1))
        # per-paper review manifest: what this folder holds and what it says, so
        # a reviewer opening papers/<doi>/ sees the whole paper at a glance
        write_review_manifest(sd, pid, outdir.parent, _results, entities)
        mats = sorted({e.get("material") for e in exps if e.get("material")})
        ready = sum(1 for e in exps if e.get("analysis_ready"))
        exp = sum(1 for e in exps if e.get("relevance") == "experimental")
        _c = _counts(entities, exps, series)
        print(f"[to-kb] {sd} → papers/{pid}/  {len(entities)} entities → "
              f"{_c['experimental_cases']} cases, {_c['experimental_series']} series, "
              f"{_c['simulation_runs']}sim/{_c['model_sweeps']}sweep/"
              f"{_c['imported_literature_profiles']}lit/{_c['unresolved_source_entities']}unres "
              f"materials={mats} chem={card.get('precursors')}+{card.get('coreactants')} T={card.get('temperature_C')}")
    print(f"[to-kb] methods gap-fill tokens: in={TI} out={TO}")




def _counts(entities, cases, series):
    """Differentiated counts. There is deliberately NO single 'experiment count':
    the contract requires each kind to be reported separately, and any count that
    would have to be inferred from digitisation density is reported as unresolved."""
    from collections import Counter
    cls = Counter(e["classification"] for e in entities)
    return {
        "source_entities": len(entities),
        "plot_series": len(entities),
        "experimental_cases": len(cases),
        "experimental_cases_lower_bound": len(cases) + sum(
            e.get("experimental_case_lower_bound", 0) for e in entities
            if e.get("experimental_case_status") == "unresolved_settings"),
        "deposition_runs": sum(1 for c in cases
                               if (c.get("measurand") or {}).get("quantity") in
                               ("film_thickness", "growth_per_cycle", "growth_rate",
                                "normalized_thickness", "step_coverage")),
        "unique_samples": len({(c.get("material"), c.get("entity_id")) for c in cases}),
        "measurements": sum(1 for e in entities if e.get("measurement_class")),
        "experimental_profiles": cls.get("experimental_profile", 0),
        "continuous_traces": cls.get("continuous_trace", 0),
        "multi_output_measurements": cls.get("multi_output_measurement", 0),
        "experimental_series": len(series),
        "series_with_unresolved_case_count": sum(
            1 for s in series if s.get("case_count_status") == "unresolved_settings"),
        "observations_pending_case_resolution": sum(
            e.get("observation_count_unresolved_as_cases", 0) for e in entities),
        "imported_literature_profiles": cls.get("imported_literature_data", 0),
        "simulation_runs": cls.get("simulation", 0),
        "model_sweeps": cls.get("model_sweep", 0),
        "model_prediction_points": sum(e["n_observations"] for e in entities
                                       if e["classification"] in ("model_sweep", "simulation")),
        "fits": cls.get("fit", 0),
        "derived_representations": sum(
            1 for e in entities if e.get("representation") in ("scaled", "normalized", "inset")),
        "unresolved_source_entities": cls.get("unknown", 0),
        "total_observations": sum(e["n_observations"] for e in entities),
        "classification_breakdown": dict(cls),
    }


if __name__ == "__main__":
    main(sys.argv[1:])
