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
EXTRACTED = ROOT / "extracted"
PIPE = ROOT.parent / "02_extraction"
OUT = PIPE / "output"
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
MODEL = "gemini-flash-latest"
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
_spec = importlib.util.spec_from_file_location("ex", ROOT / "scripts" / "04_extract.py")
ex = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ex)

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
    md = (EXTRACTED / sd / "document.md").read_text()
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
    md = (EXTRACTED / sd / "document.md").read_text()
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
    (EXTRACTED / sd / "geometry.json").write_text(json.dumps(g, indent=1))
    return g, tok


def kb_dirs():
    return sorted(f.split("/output/")[1].split("/")[0]
                  for f in glob.glob(str(OUT / "*" / "resolved" / "experiments.json")))


def tag_experiments():
    """Write geometry + geometry_class into every KB experiment (deterministic)."""
    n = 0
    for sd in kb_dirs():
        gf = EXTRACTED / sd / "geometry.json"
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
    for sd in kb_dirs():
        if not (EXTRACTED / sd / "document.md").exists():
            print(f"  [skip] {sd} (no document.md)"); continue
        gc, st, why = classify_deterministic(sd)
        g = {"geometry_class": gc, "structure": st, "method": "deterministic", "evidence": why}
        (EXTRACTED / sd / "geometry.json").write_text(json.dumps(g, indent=1))
        print(f"  {sd:28} -> {gc:18} struct={st:16} | {why}")
    tag_experiments()


if __name__ == "__main__":
    main(sys.argv[1:])
