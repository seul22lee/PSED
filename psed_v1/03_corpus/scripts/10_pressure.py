#!/usr/bin/env python3
"""
10_pressure.py — typed, species-aware pressure extraction (PILOT).
------------------------------------------------------------------
A dedicated methods-aware pass that captures pressure OBSERVATIONS with their type,
species, role, context and verbatim evidence — the support the pressure audit found
missing (the scout has no pressure field; METHODS_SCHEMA asks only for one bare
paper-level scalar). Mirrors the 09_geometry --quantities pass: one cheap LLM call
per paper, constrained to the ontology vocabulary, written to
extracted/{sd}/pressure.json.

  python3 scripts/10_pressure.py <doi> [<doi> ...]   # extract (LLM)
  python3 scripts/10_pressure.py --show <doi> ...     # print cached pressure.json

This is a PILOT tool. It does NOT run the whole corpus and does NOT touch the model
defaults (recipe pA=100/pB=300 stay source=model). `pressure_facts` below is the
deterministic normaliser 06_to_kb reads at resolve time — and only papers that have a
pressure.json are affected, so wiring it in leaves the rest of the corpus untouched.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT.parent / "papers"   # papers/<doi>/extracted/
PIPE = ROOT.parent / "02_extraction"
sys.path.insert(0, str(PIPE / "stages"))
import lib
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
_spec = importlib.util.spec_from_file_location("ex", ROOT / "scripts" / "04_extract.py")
ex = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ex)

MODEL = "gemini-flash-latest"

# --- pressure taxonomy (ontology-aligned) ------------------------------------
PRESSURE_TYPES = ("precursor_partial_pressure", "co_reactant_partial_pressure",
                  "carrier_gas_partial_pressure", "chamber_total_pressure",
                  "working_pressure", "base_pressure", "delivery_line_pressure",
                  "bubbler_pressure", "vapor_pressure", "generic_pressure",
                  "unknown_pressure_type")
CONTEXTS = ("process_condition", "measured_response", "model_definition",
            "apparatus_setting", "unknown")
# Only these contexts describe how the film was ACTUALLY GROWN and may become a
# controlled process condition. A measured-response pressure (a figure's y-axis) and a
# model-definition symbol (p_A in an equation) never do.
FACT_CONTEXTS = ("process_condition", "apparatus_setting")
# A partial pressure is only real evidence with an explicit named species.
PARTIAL_TYPES = ("precursor_partial_pressure", "co_reactant_partial_pressure",
                 "carrier_gas_partial_pressure")

# unit -> Pa (partial/total pressures). vapor pressure uses the same conversions.
_P_TO_PA = {"pa": 1.0, "kpa": 1e3, "mpa": 1e6, "bar": 1e5, "mbar": 1e2, "µbar": 1e-1,
            "torr": 133.322, "mtorr": 0.133322, "atm": 101325.0, "psi": 6894.76}


def _to_pa(value, unit):
    if value is None:
        return None, unit
    u = (unit or "").strip().lower().replace("μ", "µ")
    f = _P_TO_PA.get(u)
    return (value * f, "Pa") if f else (value, unit)


PRESSURE_SCHEMA = """From this paper, extract every PRESSURE the text reports, with its
type and the exact words that support it. Return ONLY JSON:
{"pressures":[{"pressure_type":"<one of the list below>","value":<number or null>,
  "unit":"<as printed>","named_species":"<the species this pressure belongs to, or null>",
  "reactant_role":"precursor"|"co_reactant"|"carrier"|null,
  "context":"process_condition"|"measured_response"|"model_definition"|"apparatus_setting"|"unknown",
  "directly_reported":true|false,"source_section":"<methods|results|caption|table|abstract>",
  "evidence_text":"<short verbatim quote containing the number and the pressure word>",
  "confidence":0.0-1.0,"ambiguity_reason":"<why unsure, or null>"}]}

pressure_type — choose the MOST SPECIFIC the text justifies:
  precursor_partial_pressure     partial pressure of a NAMED precursor / its stream
  co_reactant_partial_pressure   partial pressure of a NAMED co-reactant (e.g. ozone)
  carrier_gas_partial_pressure   partial pressure of the carrier gas itself
  chamber_total_pressure         "chamber/reactor/total pressure"
  working_pressure               "working / operating pressure"
  base_pressure                  "base / ultimate pressure" (before/between runs)
  delivery_line_pressure         pressure in a delivery line
  bubbler_pressure               pressure at the bubbler/source vessel
  vapor_pressure                 equilibrium vapor pressure of a precursor at a stated
                                 source temperature (a SPECIES PROPERTY, not a process
                                 condition) — set context=apparatus_setting or unknown
  generic_pressure               an unqualified "pressure" with no type
  unknown_pressure_type          semantics unclear

STRICT RULES — follow exactly, they decide whether a value is trustworthy:
- A partial pressure (precursor/co_reactant/carrier) is allowed ONLY when the source
  explicitly names the species or its stream, e.g. "the partial pressure of ozone was
  1.1 Torr". Fill named_species with that species.
- NEVER infer a partial pressure from: pulse order, an A/B position, common ALD
  practice, a chamber/total/working pressure, a flow rate, a bubbler temperature, a
  vapor-pressure table not stated as the operating condition, or a reactor model symbol.
- A symbolic p_A or p_B appearing in a THEORETICAL EQUATION is context=model_definition,
  NOT a reported process condition. Set value only if the paper states a numeric case.
- "reactor / chamber / total pressure" -> chamber_total_pressure;
  "working / operating pressure" -> working_pressure; "base pressure" -> base_pressure;
  an unqualified "pressure" -> generic_pressure.
- A y-axis pressure that is MEASURED/plotted (a saturation profile p(x)) is
  context=measured_response, not a process condition.
- If a partial pressure is named but VARIES across experiments with no single value
  ("the partial pressure of TMA depended on pulse time"), report it with value=null and
  ambiguity_reason describing the variation — do NOT invent a number.
- TABLES: a bare number in a table cell is NOT a pressure unless that column's HEADER
  explicitly names a pressure (e.g. "p (Pa)", "pressure", "chamber pressure"). Do not
  read a numeric cell as pressure just because a nearby column or the caption mentions
  pressure. If you cannot point to a pressure-named header for the cell, omit it.
- An isolated number with no pressure word next to it is never a pressure. Every entry
  must have an evidence_text that contains BOTH the number AND an explicit pressure
  term (pressure / p_A / partial pressure / mbar-of-pressure / etc.). If the quote
  would not contain a pressure word, do not emit the entry.
- A missing pressure is a valid result. Never manufacture a value. Keep the exact
  evidence quote for every entry."""


def extract_pressures(sd, client):
    md = (EXTRACTED / sd / "extracted" / "document.md").read_text()
    ab = ex.abstract_of(md)
    methods = ex.section_text(md, ["experimental", "methods", "deposition", "apparatus",
                                   "reactor", "setup", "film growth"], limit=6000)
    st = json.loads((EXTRACTED / sd / "extracted" / "structure.json").read_text()) \
        if (EXTRACTED / sd / "extracted" / "structure.json").exists() else {}
    tables = "\n\n".join(f"[TABLE {t.get('index')}] {t.get('caption','')}\n{t.get('markdown','')}"
                         for t in st.get("tables", []) if t.get("markdown"))[:4000]
    caps = "\n".join(f"[{f.get('index')}] {f.get('caption','')}"
                     for f in st.get("figures", []) if f.get("caption"))[:2500]
    from google.genai import types
    contents = (f"{PRESSURE_SCHEMA}\n\n=== ABSTRACT ===\n{ab}\n\n=== METHODS / APPARATUS ===\n{methods}")
    if tables:
        contents += f"\n\n=== TABLES ===\n{tables}"
    if caps:
        contents += f"\n\n=== FIGURE CAPTIONS ===\n{caps}"
    r = client.models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                           max_output_tokens=8192))
    u = getattr(r, "usage_metadata", None)
    tok = (getattr(u, "prompt_token_count", 0) or 0, getattr(u, "candidates_token_count", 0) or 0)
    try:
        d = ex._loads_json(r.text)
        obs = d.get("pressures") if isinstance(d, dict) else (d if isinstance(d, list) else [])
    except Exception:
        obs = []
    out = []
    _PWORDS = ("pressure", "p_a", "p a", "p_b", "p b", "mbar", "torr", "pa", "bar", "psi")
    for o in obs or []:
        if not isinstance(o, dict):
            continue
        # Deterministic backstop for the table-cell false positive: an observation whose
        # own evidence quote contains no pressure word is not a pressure statement, no
        # matter what type the model assigned. Recall is unaffected — a genuine pressure
        # sentence always names a pressure unit or the word "pressure".
        _ev = (o.get("evidence_text") or "").lower()
        if not any(w in _ev for w in _PWORDS):
            continue
        pt = o.get("pressure_type")
        pt = pt if pt in PRESSURE_TYPES else "unknown_pressure_type"
        ctx = o.get("context") if o.get("context") in CONTEXTS else "unknown"
        val = o.get("value")
        val = val if isinstance(val, (int, float)) and not isinstance(val, bool) else None
        v_pa, u_pa = _to_pa(val, o.get("unit"))
        # A partial pressure with no named species is downgraded here — the model cannot
        # override the "explicit species" rule by simply asserting the type.
        species = (o.get("named_species") or "").strip() or None
        if pt in PARTIAL_TYPES and not species:
            pt = "generic_pressure"
        out.append({"pressure_type": pt, "value": val, "unit": o.get("unit"),
                    "value_pa": v_pa, "unit_pa": u_pa,
                    "named_species": species,
                    "reactant_role": o.get("reactant_role")
                    if o.get("reactant_role") in ("precursor", "co_reactant", "carrier") else None,
                    "context": ctx,
                    "directly_reported": bool(o.get("directly_reported")),
                    "source_section": (o.get("source_section") or "")[:40] or None,
                    "evidence_text": (o.get("evidence_text") or "")[:400],
                    "confidence": o.get("confidence") if isinstance(o.get("confidence"), (int, float)) else None,
                    "ambiguity_reason": (o.get("ambiguity_reason") or None)})
    # Observation-level dedup: identical (type, value, unit, species, context, evidence)
    # entries are the same statement returned twice (the model sometimes repeats p_A0 /
    # p_B). Distinct observations differ on at least one key and are all kept.
    deduped, seen = [], set()
    for o in out:
        k = (o["pressure_type"], o["value"], (o["unit"] or "").lower(),
             (o["named_species"] or "").lower(), o["context"],
             (o["evidence_text"] or "").strip().lower())
        if k in seen:
            continue
        seen.add(k); deduped.append(o)
    (EXTRACTED / sd / "extracted" / "pressure.json").write_text(
        json.dumps({"pressures": deduped}, indent=1))
    return deduped, tok


# --- deterministic normaliser (read by 06_to_kb at resolve time) -------------
def _slot_for(role, reactants):
    for rt in reactants or []:
        if rt.get("role") == ("coreactant" if role == "co_reactant" else role):
            return rt.get("label")
    return None


def pressure_facts(sd, reactants=None):
    """Controlled conditions from extracted/{sd}/pressure.json.

    ONLY process_condition / apparatus_setting observations WITH a numeric value become
    conditions. measured_response (a plotted p(x)) and model_definition (a symbol in an
    equation) never do. A partial pressure carries its named species and reactant slot;
    a chamber/working/base pressure never carries a species. Every condition keeps a
    verbatim evidence quote and paper provenance, and shares one evidence id per
    observation. Returns []; the model defaults are untouched (they live in recipes)."""
    pf = EXTRACTED / sd / "extracted" / "pressure.json"
    if not pf.exists():
        return []
    try:
        obs = json.loads(pf.read_text()).get("pressures") or []
    except Exception:
        return []
    cs = []
    _seen = set()
    for i, o in enumerate(obs):
        if o.get("context") not in FACT_CONTEXTS:
            continue
        v = o.get("value_pa")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        # Deterministic within-paper dedup: two observations that agree on paper, type,
        # normalised value, unit, species AND evidence quote are the same statement read
        # twice (e.g. a base pressure quoted in two sentences). Genuinely different
        # observations differ on at least one key and are both kept.
        key = (o.get("pressure_type"), round(v, 6), (o.get("named_species") or "").lower(),
               (o.get("evidence_text") or "").strip().lower())
        if key in _seen:
            continue
        _seen.add(key)
        pt = o.get("pressure_type")
        react = _slot_for(o.get("reactant_role"), reactants) if pt in PARTIAL_TYPES else None
        origin = {"level": "paper", "from": "pressure_extraction",
                  "evidence_id": f"{sd}::pressure::{pt}::{i}",
                  "pressure_type": pt, "named_species": o.get("named_species"),
                  "reactant_role": o.get("reactant_role"), "context": o.get("context"),
                  "source_section": o.get("source_section"),
                  "directly_reported": o.get("directly_reported"),
                  "confidence": o.get("confidence"),
                  "evidence": o.get("evidence_text"),
                  "original_value": o.get("value"), "original_unit": o.get("unit")}
        cs.append({"quantity": pt, "value": v, "unit": "Pa", "of_reactant": react,
                   "source": "pressure_extraction",
                   "recipe_role": lib.recipe_role(pt) or "control_setting", "origin": origin})
    return cs


def main(argv):
    if argv and argv[0] == "--show":
        for sd in argv[1:]:
            pf = EXTRACTED / sd / "extracted" / "pressure.json"
            print(f"\n=== {sd} ===")
            print(pf.read_text() if pf.exists() else "  (no pressure.json)")
        return
    from google import genai
    client = genai.Client(api_key=ex._load_key())
    tin = tout = 0
    for sd in argv:
        obs, (i, o) = extract_pressures(sd, client)
        tin += i; tout += o
        print(f"\n[pressure] {sd} -> {len(obs)} observations")
        for x in obs:
            print(f"   {x['pressure_type']:28} {str(x['value']):>7} {x['unit'] or '':6} "
                  f"-> {str(round(x['value_pa'],4)) if x['value_pa'] is not None else '—':>10} Pa  "
                  f"[{x['context']}] species={x['named_species']}")
            print(f"        \"{(x['evidence_text'] or '')[:88]}\"")
    print(f"\n[pressure] tokens in={tin} out={tout}")


if __name__ == "__main__":
    main(sys.argv[1:])
