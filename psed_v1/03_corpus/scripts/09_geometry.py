#!/usr/bin/env python3
"""
09_geometry.py — extract the ALD TEST-STRUCTURE geometry for each paper and ground it in
the ontology's geometry_class layer (Cremers 2019 classification: lateral / vertical /
porous / …). One cheap LLM call per paper on abstract + methods, constrained to the
ontology vocabulary. Writes extracted/{sd}/geometry.json, then tags every KB experiment
with `geometry` (structure) + `geometry_class` so geometry-scoped model validation works.

  python3 scripts/09_geometry.py            # extract + tag all papers in the KB
  python3 scripts/09_geometry.py --tag-only # re-tag experiments from cached geometry.json (no LLM)
"""
import json, sys, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT.parent / "papers"   # papers/<doi>/extracted/
PIPE = ROOT.parent / "02_extraction"
OUT = ROOT.parent / "papers"        # papers/<doi>/{resolved,canonical}/
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
MODEL = "gemini-flash-latest"
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
_spec = importlib.util.spec_from_file_location("ex", ROOT / "scripts" / "04_extract.py")
ex = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ex)

sys.path.insert(0, str(PIPE / "stages"))
import lib as _lib                       # canon_quantity: the ontology's alias table
lib_canon = _lib.canon_quantity

GC = ONTO.get("geometry_classes", {})
STRUCTS = {s["id"]: s.get("geometry_class") for s in ONTO["individuals"].get("structures", [])}
ALIASES = {}
for s in ONTO["individuals"].get("structures", []):
    for a in [s["id"]] + (s.get("aka") or []):
        ALIASES[a.lower()] = s["id"]

SCHEMA = f"""Classify the PRIMARY ALD test structure / substrate geometry used in this paper.
Return ONLY JSON:
{{"geometry_class":"<one of {list(GC.keys())}>",
  "structure":"<one of {list(STRUCTS.keys())} or ''>",
  "is_conformality_study": true|false,
  "evidence":"<short quote/paraphrase>"}}
Definitions (Cremers 2019 review): lateral_channel = lateral high-aspect-ratio (LHAR/PillarHall);
vertical_structure = trench/via/hole; porous_material = AAO, membranes, mesoporous films/powders,
MOF, opal, fibers (tortuous or parallel-pore networks); nanostructure_array = external coating of
nanowires/nanorods/CNTs/pillars; planar = flat wafer, no 3D feature (most GPC/property studies);
cavity = enclosed cavity. If the film is grown/characterised only on a flat wafer, use planar."""


# --- numeric test-structure geometry + transport/kinetic model parameters ------
# Separate LLM call from the class above: these are VALUES with units, scope and an
# evidence quote, not a classification. Nothing here may be guessed — a field the paper
# does not state must simply be absent (see `status`, which the resolver filters on).
QUANT_SCHEMA = """From this paper, extract the NUMERIC test-structure geometry and any
transport / adsorption MODEL PARAMETERS it reports. Return ONLY JSON:
{"quantities":[{"quantity":"<canonical name, see list>","raw_label":"<the paper's own words>",
  "symbol":"<e.g. H, W, L, AR, c, K, s0 — or null>","value":<number>,"unit":"<as printed, or null>",
  "basis":"<for a ratio: what over what, e.g. 'channel length / channel height'; else null>",
  "status":"directly_reported"|"derived_from_reported_dimensions"|"inferred_from_context",
  "scope":"paper"|"model"|"figure","of_reactant":"A"|"B"|null,
  "model_context":"<equation / model name the parameter belongs to, or null>",
  "parameter_status":"fitted"|"assumed"|"literature"|"measured"|null,
  "evidence":"<short verbatim quote containing the value>"}]}

Canonical names to use when they fit: feature_height (channel/trench/gap HEIGHT or depth),
feature_width (channel/trench/gap WIDTH, pore diameter, lateral opening), feature_length
(channel LENGTH along the transport direction), aspect_ratio (dimensionless ratio),
sticking_probability (sticking/adsorption probability or coefficient, dimensionless),
initial_sticking_coefficient (use this when the paper says INITIAL sticking probability /
coefficient, e.g. s0 or beta_0 — it is a distinct quantity, not the same as a lumped
sticking_probability), adsorption_rate_constant (KINETIC rate constant for adsorption),
adsorption_equilibrium_constant (Langmuir EQUILIBRIUM constant K, often Pa^-1 — this is
NOT a rate constant), reaction_probability, recombination_probability, site_density,
diffusion_coefficient.
If the paper's parameter has no good canonical name (e.g. an EQUILIBRIUM constant, which is
NOT a rate constant), put its own words in "quantity" — do not force it into a near-miss name.

RULES — these decide whether the value is usable, so follow them exactly:
- Only report a value the paper actually prints. Never infer, average, or carry over a
  typical literature value. If it is not stated, omit the entry entirely.
- status: "directly_reported" only when the number appears as such. Use
  "derived_from_reported_dimensions" ONLY if you computed it from two stated dimensions,
  and then put the arithmetic in "basis". Use "inferred_from_context" if you are reading
  between the lines — such entries are recorded but NOT used as fact.
- Do NOT confuse feature_width with feature_height, feature_length, film thickness or
  penetration depth. Width is the transverse/lateral opening.
- Do NOT merge sticking_probability with reaction_probability or recombination_probability,
  and do NOT merge an adsorption RATE constant with an adsorption EQUILIBRIUM constant.
  Keep whatever distinction the paper makes.
- Keep the unit exactly as printed (e.g. "Pa^-1", "nm", "µm"); use null for dimensionless.
- scope: "paper" if it describes the test structures generally, "model" if it is an input or
  fitted value of a simulation, "figure" if it applies only to one figure's case.
- A RANGE (e.g. "2:1 to 10 000:1") is not a single value — omit it rather than picking an end."""


def _title(md):
    for line in md.splitlines():
        t = line.strip("# ").strip()
        if len(t) > 25 and not t.lower().startswith(("abstract", "introduction")):
            return t[:250]
    return ""


GEOM_Q = {"feature_height", "feature_width", "feature_length", "aspect_ratio",
          "coated_aspect_ratio", "pore_diameter", "pore_radius", "channel_filling_fraction",
          "penetration_depth", "normalized_thickness"}


def _paper_quants(sd):
    f = OUT / sd / "resolved" / "experiments.json"
    qs = set()
    if f.exists():
        for e in json.loads(f.read_text()):
            for c in (e.get("controlled") or []):
                qs.add(c.get("quantity"))
            qs.add((e.get("measurand") or {}).get("quantity"))
            if e.get("coordinate"):
                qs.add(e.get("coordinate"))
    return qs


def classify_deterministic(sd):
    """Reproducible geometry classification from the paper text + the geometry quantities
    the extracted experiments carry. Keyword priority follows the Cremers taxonomy."""
    md = (EXTRACTED / sd / "extracted" / "document.md").read_text()
    txt = (_title(md) + " \n " + ex.abstract_of(md)).lower()
    q = _paper_quants(sd)
    conf = bool(q & GEOM_Q)
    def kw(pat): return re.search(pat, txt) is not None
    if kw(r"porous|anodic alumin|\baao\b|mesoporous|\bsofc\b|membrane|\bmof\b|\bpowder|opal|aerogel|nanoporous"):
        st = "aao" if kw(r"\baao\b|anodic alumin") else ("mesoporous_powder" if kw(r"powder") else "mesoporous_film")
        return "porous_material", st, "keyword: porous/AAO/membrane"
    if conf and kw(r"nanowire|nanorod|nanotube|\bcnt\b|carbon nanotube|nanopillar"):
        st = "cnt" if kw(r"nanotube|\bcnt\b") else ("nanowire" if kw(r"nanowire") else "nanorod")
        return "nanostructure_array", st, "keyword: nanostructure + conformality"
    if kw(r"lateral high|\blhar\b|pillarhall|lateral (high[- ])?aspect|lateral channel|lateral trench|macroscopic lateral"):
        return "lateral_channel", "pillarhall_lhar", "keyword: lateral HAR"
    if "channel_filling_fraction" in q or "feature_length" in q:
        return "lateral_channel", "lhar_channel", "quantity signature: feature_length / channel_filling"
    if conf and kw(r"\btrench|\bvia\b|through[- ]silicon|3d nand|finfet|deep hole|nanolaminate.*trench"):
        return "vertical_structure", "trench", "keyword: trench/via + conformality"
    if conf and (q & {"aspect_ratio", "feature_height", "penetration_depth", "normalized_thickness"}):
        return "vertical_structure", "trench", "generic HAR conformality (single-feature default)"
    return "planar", "planar_wafer", "no 3D test structure found"


def extract_one(sd, client):
    md = (EXTRACTED / sd / "extracted" / "document.md").read_text()
    ab = ex.abstract_of(md)
    methods = ex.section_text(md, ["experimental", "methods", "substrate", "test structure",
                                   "sample preparation", "deposition"], limit=3500)
    from google.genai import types
    r = client.models.generate_content(
        model=MODEL, contents=(f"{SCHEMA}\n\n=== TITLE ===\n{_title(md)}\n\n"
                               f"=== ABSTRACT ===\n{ab}\n\n=== METHODS ===\n{methods}"),
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                           max_output_tokens=1024))
    u = getattr(r, "usage_metadata", None)
    tok = (getattr(u, "prompt_token_count", 0) or 0, getattr(u, "candidates_token_count", 0) or 0)
    try:
        g = ex._loads_json(r.text)
        if not isinstance(g, dict):
            g = {}
    except Exception:
        g = {"_parse_error": (r.text or "")[:300]}
    # normalise structure -> canonical + derive class from ontology
    st = g.get("structure") or ""
    st = ALIASES.get(str(st).lower(), st if st in STRUCTS else "")
    g["structure"] = st
    gc = g.get("geometry_class")
    if st and STRUCTS.get(st):
        gc = STRUCTS[st]                 # ontology is the source of truth for the class
    if gc not in GC:
        gc = "planar"
    g["geometry_class"] = gc
    (EXTRACTED / sd / "extracted" / "geometry.json").write_text(json.dumps(g, indent=1))
    return g, tok


# statuses whose values may be used as FACT downstream (§ do not conflate extraction and
# derivation). "inferred_from_context" is retained in geometry.json for audit but never
# emitted as a controlled condition.
FACTUAL_STATUS = ("directly_reported", "derived_from_reported_dimensions")


def extract_quantities(sd, client):
    """Second, separate LLM pass: numeric geometry + model parameters WITH evidence.
    Merged into geometry.json under `quantities`; the classification above is untouched."""
    md = (EXTRACTED / sd / "extracted" / "document.md").read_text()
    ab = ex.abstract_of(md)
    methods = ex.section_text(md, ["experimental", "methods", "substrate", "test structure",
                                   "sample preparation", "deposition", "model", "theory",
                                   "simulation"], limit=6000)
    st = json.loads((EXTRACTED / sd / "extracted" / "structure.json").read_text())
    tables = "\n\n".join(f"[TABLE {t.get('index')}] {t.get('caption','')}\n{t.get('markdown','')}"
                         for t in st.get("tables", []) if t.get("markdown"))[:6000]
    caps = "\n".join(f"[{f.get('index')}] {f.get('caption','')}"
                     for f in st.get("figures", []) if f.get("caption"))[:3000]
    from google.genai import types
    contents = (f"{QUANT_SCHEMA}\n\n=== TITLE ===\n{_title(md)}\n\n=== ABSTRACT ===\n{ab}"
                f"\n\n=== METHODS / MODEL ===\n{methods}")
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
        qs = d.get("quantities") if isinstance(d, dict) else (d if isinstance(d, list) else [])
    except Exception:
        qs = []
    out = []
    for q in qs or []:
        if not isinstance(q, dict):
            continue
        name, val = q.get("quantity"), q.get("value")
        if not name or not isinstance(val, (int, float)) or isinstance(val, bool):
            continue                                   # a value is required; never invent one
        cq = lib_canon(name) or lib_canon(q.get("raw_label") or "") or str(name).strip()
        out.append({"quantity": cq, "raw_label": q.get("raw_label") or name,
                    "symbol": q.get("symbol"), "value": val, "unit": q.get("unit"),
                    "basis": q.get("basis"),
                    "status": q.get("status") if q.get("status") in
                    FACTUAL_STATUS + ("inferred_from_context",) else "inferred_from_context",
                    "scope": q.get("scope") if q.get("scope") in ("paper", "model", "figure") else "paper",
                    "of_reactant": q.get("of_reactant") if q.get("of_reactant") in ("A", "B") else None,
                    "model_context": q.get("model_context"),
                    "parameter_status": q.get("parameter_status"),
                    "evidence": (q.get("evidence") or "")[:400]})
    gf = EXTRACTED / sd / "extracted" / "geometry.json"
    g = json.loads(gf.read_text()) if gf.exists() else {}
    g["quantities"] = out
    gf.write_text(json.dumps(g, indent=1))
    return out, tok


def kb_dirs():
    return sorted(f.split("/output/")[1].split("/")[0]
                  for f in glob.glob(str(OUT / "*" / "resolved" / "experiments.json")))


def tag_experiments():
    """Write geometry + geometry_class into every KB experiment (deterministic)."""
    n = 0
    for sd in kb_dirs():
        gf = EXTRACTED / sd / "extracted" / "geometry.json"
        g = json.loads(gf.read_text()) if gf.exists() else {}
        gc, st = g.get("geometry_class", "planar"), g.get("structure", "")
        f = OUT / sd / "resolved" / "experiments.json"
        exps = json.loads(f.read_text())
        for e in exps:
            e["geometry_class"] = gc
            e["structure"] = st or e.get("structure")
        f.write_text(json.dumps(exps, indent=1))
        n += len(exps)
    print(f"[geometry] tagged {n} experiments across {len(kb_dirs())} papers")


def main(argv):
    if "--tag-only" in argv:
        tag_experiments()
        return
    if "--quantities" in argv:
        # numeric geometry + model parameters (LLM). Optional explicit paper list, so a
        # single paper can be re-extracted without touching the rest of the corpus.
        sds = [a for a in argv if not a.startswith("--")] or kb_dirs()
        from google import genai
        client = genai.Client(api_key=ex._load_key())
        tin = tout = 0
        for sd in sds:
            qs, (i, o) = extract_quantities(sd, client)
            tin += i; tout += o
            print(f"  {sd:28} -> {len(qs)} quantities: "
                  f"{sorted(set(q['quantity'] for q in qs))}")
            for q in qs:
                print(f"       {q['quantity']:26} {q['value']} {q['unit'] or ''} "
                      f"[{q['status']}/{q['scope']}] {(q['evidence'] or '')[:60]}")
        print(f"[geometry-quantities] tokens in={tin} out={tout}")
        return
    for sd in kb_dirs():
        if not (EXTRACTED / sd / "extracted" / "document.md").exists():
            print(f"  [skip] {sd} (no document.md)"); continue
        gc, st, why = classify_deterministic(sd)
        g = {"geometry_class": gc, "structure": st, "method": "deterministic", "evidence": why}
        (EXTRACTED / sd / "extracted" / "geometry.json").write_text(json.dumps(g, indent=1))
        print(f"  {sd:28} -> {gc:18} struct={st:16} | {why}")
    tag_experiments()


if __name__ == "__main__":
    main(sys.argv[1:])
