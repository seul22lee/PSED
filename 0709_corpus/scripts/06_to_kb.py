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
PIPE = ROOT.parent / "0706_pipeline"
sys.path.insert(0, str(PIPE / "stages"))
sys.path.insert(0, str(PIPE))
import lib                                   # canon_*, family, recipe_role, species_prop
import recipe as recipe_mod
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
_spec = importlib.util.spec_from_file_location("ex", ROOT / "scripts" / "04_extract.py")
ex = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ex)   # section_text, _load_key

MODEL = "gemini-2.5-flash"
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


def methods_fill(sd, scout, client):
    """Fill scout-deferred conditions from methods. One call, only if something's missing."""
    need = (not scout.get("precursors") or not scout.get("coreactants")
            or not scout.get("temperature_window_C"))
    md = (EXTRACTED / sd / "document.md").read_text()
    methods = ex.section_text(md, ["experimental", "methods", "deposition", "film growth",
                                   "materials and methods"], limit=4000)
    base = {"precursors": scout.get("precursors") or [],
            "coreactants": scout.get("coreactants") or [],
            "process_type": scout.get("process_type") or "unknown",
            "temperature_C": (scout.get("temperature_window_C") or [None])[0],
            "pressure_Pa": None, "pulse_time_s": None, "purge_time_s": None,
            "ncycles": None, "carrier_gas": None}
    if not methods:
        return base, {}
    from google.genai import types
    r = client.models.generate_content(
        model=MODEL, contents=f"{METHODS_SCHEMA}\n\n=== METHODS ===\n{methods}",
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    u = getattr(r, "usage_metadata", None)
    tok = {"in": getattr(u, "prompt_token_count", 0) or 0, "out": getattr(u, "candidates_token_count", 0) or 0}
    try:
        m = json.loads(r.text)
    except Exception:
        return base, tok
    # prefer scout chemistry, fill the rest from methods
    for k in ("precursors", "coreactants"):
        if not base[k] and m.get(k):
            base[k] = m[k]
    for k in ("process_type", "temperature_C", "pressure_Pa", "pulse_time_s",
              "purge_time_s", "ncycles", "carrier_gas"):
        if base.get(k) in (None, "unknown", []) and m.get(k) not in (None, ""):
            base[k] = m[k]
    return base, tok


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
    return sd.split("_")[-1] if "_" in sd else sd


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
        panel_ctrl = [c for c in (_ctrl(k, _num(v), _unit(v), source="caption")
                                  for k, v in (r.get("controlled") or {}).items()) if c]
        mat = lib.canon_material(r.get("material")) or (scout.get("materials") or [None])[0]
        fig = (r.get("provenance") or {}).get("figure", "F?").replace("Fig ", "F").replace(" ", "")
        panel = (r.get("provenance") or {}).get("panel") or ""
        e = {
            "material": mat, "material_raw": r.get("material"),
            "precursors": [prec_c] if prec_c else [], "coreactants": [core_c] if core_c else [],
            "reactants": reactants, "carrier_gas": carrier, "process_type": ptype,
            "cycle_sequence": "AB" if core_c else "A",
            "controlled": base_ctrl + panel_ctrl,
            "measurand": {"quantity": mq, "unit": (r.get("measurand") or {}).get("unit"),
                          "family": lib.family(mq)},
            "coordinate": cq, "coordinate_family": lib.family(cq),
            "points": pts, "granularity": "profile" if len(pts) > 1 else "single",
            "relevance": "experimental" if r.get("source") == "measured" else "model",
            "is_model_result": r.get("source") == "simulated",
            "analysis_ready": bool(pts and mq),
            "exp_id": f"{pid}-{fig}{panel}-{len(exps)}",
            "provenance": {**(r.get("provenance") or {}), "doi": sd},
            "series_name": None, "structure": None, "varies": [], "dependent": [],
            "issues": [] if pts else ["no-points"],
        }
        r_obj = recipe_mod.from_experiment(e)
        e["recipe"] = r_obj.to_dict(); e["recipe"]["completeness"] = r_obj.completeness()
        exps.append(e)
    return pid, exps


def _num(v):
    if isinstance(v, (int, float)):
        return v
    m = re.search(r"-?\d+\.?\d*(?:e-?\d+)?", str(v))
    return float(m.group()) if m else None


def _unit(v):
    m = re.search(r"[a-zµμÅ%/·]+\s*$", str(v).strip())
    return m.group().strip() if m else ""


def main(sds):
    from google import genai
    client = genai.Client(api_key=ex._load_key())
    TI = TO = 0
    for sd in sds:
        d = EXTRACTED / sd
        scout = json.loads((d / "scout.json").read_text())
        records = json.loads((d / "records.json").read_text()) if (d / "records.json").exists() else []
        card, tok = methods_fill(sd, scout, client)
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
