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
def _norm_unit(q, val, unit):
    u = (unit or "").strip().lower()
    if val is None:
        return val, unit
    if q in ("growth_per_cycle",) and u in ("å/cycle", "a/cycle", "å", "a", "angstrom"):
        return val * 0.1, "nm"           # Å → nm
    if q in ("film_thickness", "penetration_depth") and u in ("µm", "um", "μm"):
        return val * 1000.0, "nm"        # µm → nm
    return val, unit


METHODS_SCHEMA = """From the METHODS text, return ONLY JSON with the ALD PROCESS
conditions actually stated (null if absent — do NOT guess):
{"precursors":[..],"coreactants":[..],"process_type":"thermal"|"plasma"|"unknown",
 "temperature_C":num|null,"pressure_Pa":num|null,
 "pulse_time_s":{"precursor":num|null,"coreactant":num|null}|null,
 "purge_time_s":num|null,"ncycles":num|null,"carrier_gas":str|null}"""


def base_card(scout):
    """Process card from the scout alone (no LLM)."""
    return {"precursors": scout.get("precursors") or [],
            "coreactants": scout.get("coreactants") or [],
            "process_type": scout.get("process_type") or "unknown",
            "temperature_C": (scout.get("temperature_window_C") or [None])[0],
            "pressure_Pa": None, "pulse_time_s": None, "purge_time_s": None,
            "ncycles": None, "carrier_gas": None}


def methods_fill(sd, scout, client):
    """Fill scout-deferred conditions from the methods section. One LLM call."""
    base = base_card(scout)
    md = (EXTRACTED / sd / "document.md").read_text()
    methods = ex.section_text(md, ["experimental", "methods", "deposition", "film growth",
                                   "materials and methods"], limit=4000)
    if not methods:
        return base, {}
    from google.genai import types
    r = client.models.generate_content(
        model=MODEL, contents=f"{METHODS_SCHEMA}\n\n=== METHODS ===\n{methods}",
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
    for k in ("process_type", "temperature_C", "pressure_Pa", "pulse_time_s",
              "purge_time_s", "ncycles", "carrier_gas"):
        if base.get(k) in (None, "unknown", []) and m.get(k) not in (None, ""):
            base[k] = m[k]
    return base, tok


def get_card(sd, scout, client):
    """The methods-filled process card — CACHED to card.json so it's computed once.
    On re-resolve (client=None) it loads the cache (or the scout base), NO LLM."""
    cf = EXTRACTED / sd / "card.json"
    if cf.exists():
        return json.loads(cf.read_text()), {}
    card, tok = (methods_fill(sd, scout, client) if client else (base_card(scout), {}))
    cf.write_text(json.dumps(card, indent=1))
    return card, tok


# A COMPLETE number (+ optional unit). The unit class excludes '-', so 'Al2O3' and
# '2-propanol' are names, not numbers. Same rule the series path uses in 05 — a condition
# value must BE a number, never merely contain a digit.
_NUMU = re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-zµμÅ°%/·^]*)\s*\Z")


def _num_cond(k, v):
    """Caption condition -> controlled entry, ONLY when the value is a complete number.
    Without this, _num('Al2O3') returns 2.0 and a categorical caption field becomes a
    fabricated measurement."""
    m = _NUMU.fullmatch(str(v))
    if not m:
        return None
    return _ctrl(k, float(m.group(1)), (m.group(2) or None), source="caption")


def _ctrl(q, v, u, react=None, source="methods"):
    if v is None:
        return None
    cq = lib.canon_quantity(q) or q
    v, u = _norm_unit(cq, v, u)
    return {"quantity": cq, "value": v, "unit": u, "of_reactant": react,
            "source": source, "recipe_role": lib.recipe_role(cq)}


def paper_conditions(card):
    """Paper-level controlled conditions from the (gap-filled) process card."""
    cs = []
    for c in [
        _ctrl("temperature", card.get("temperature_C"), "C"),
        _ctrl("total_pressure", card.get("pressure_Pa"), "Pa"),
        _ctrl("cycle_number", card.get("ncycles"), "cycles"),
        _ctrl("purge_time", card.get("purge_time_s"), "s"),
    ]:
        if c:
            cs.append(c)
    pt = card.get("pulse_time_s") or {}
    if isinstance(pt, dict):
        cs += [x for x in (_ctrl("pulse_time", pt.get("precursor"), "s", "A"),
                           _ctrl("pulse_time", pt.get("coreactant"), "s", "B")) if x]
    return cs


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
    pid = short_pid(sd)
    exps = []
    for r in records:
        mq = lib.canon_quantity((r.get("measurand") or {}).get("quantity")) or (r.get("measurand") or {}).get("quantity")
        cq = lib.canon_quantity(r.get("coordinate")) or r.get("coordinate")
        mv, mu = _norm_unit(mq, None, (r.get("measurand") or {}).get("unit"))
        pts = [p for p in (r.get("points") or []) if isinstance(p, list) and len(p) == 2]
        panel_ctrl = [c for c in (_num_cond(k, v)
                                  for k, v in (r.get("controlled") or {}).items()) if c]
        mat = lib.canon_material(r.get("material")) or (scout.get("materials") or [None])[0]
        fig = (r.get("provenance") or {}).get("figure", "F?").replace("Fig ", "F").replace(" ", "")
        panel = (r.get("provenance") or {}).get("panel") or ""
        panel = panel.lower() if re.fullmatch(r"[A-Za-z]", str(panel).strip()) else ""   # only a real panel letter
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
                                 source="series")]
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
            "exp_id": f"{pid}-{fig}{panel}-{len(exps)}",
            "provenance": {**(r.get("provenance") or {}), "doi": sd},
            "series_name": series_name,             # display only; built from structure, never re-parsed
            "phase": r.get("phase"),                # crystallographic phase (e.g. "c-MoS2") or None
            "structure": None,
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
        exps.append(paper_level_experiment(sd, scout, card, pid, reactants, carrier, ptype, prec_c, core_c, base_ctrl))
    return pid, exps


def paper_level_experiment(sd, scout, card, pid, reactants, carrier, ptype, prec_c, core_c, base_ctrl):
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
        "series_name": None, "phase": None, "structure": None, "varies": [],
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
