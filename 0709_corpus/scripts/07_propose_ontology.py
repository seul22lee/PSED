#!/usr/bin/env python3
"""
07_propose_ontology.py — the auto-propose loop: turn unmapped extraction terms into
CANDIDATE ontology entries for review, so new-paper data becomes grounded instead of
loose strings.

  1) gather (deterministic, no LLM): every material/precursor/coreactant/quantity the
     extracted papers produced that does NOT canonicalise against the current ontology,
     with provenance (which DOIs) and observed units.
  2) propose (one ontology-constrained LLM call): valid entries slotted into the
     ontology's own vocabulary — material/precursor classes, quantity category/family/
     recipe_role, QUDT-ish units — new categories/families allowed but flagged `new:true`.
  3) write proposed/proposed_ontology.yaml (status: pending) for quick human review;
     08_merge_ontology.py folds the approved ones into core.yaml.

Run with the psed310 env python.
"""
import json, os, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
PROPOSED = ROOT / "proposed"; PROPOSED.mkdir(exist_ok=True)
PIPE = ROOT.parent / "0706_pipeline"
sys.path.insert(0, str(PIPE / "stages"))
import lib
ONTO = json.loads((ROOT.parent / "0706_ontology" / "ald_ontology.json").read_text())
MODEL = "gemini-flash-latest"


def _key():
    for l in (ROOT.parent / "0604_kg" / ".env").read_text().splitlines():
        if l.startswith("GOOGLE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_API_KEY")


CATS = list((ONTO["quantity_relations"].get("categories") or {}).keys())
FAMS = list((ONTO["quantity_relations"].get("families") or {}).keys())
ROLES = sorted({q.get("recipe_role") for q in ONTO["quantity_kinds"] if q.get("recipe_role")})
MAT_CLASSES = sorted({m.get("class") for m in ONTO["individuals"]["materials"] if m.get("class")})
PREC_CLASSES = ["HomolepticPrecursor", "HeterolepticPrecursor", "Precursor"]
LIGANDS = [x["id"] for x in ONTO["individuals"].get("ligand_families", [])]


def gather_unmapped():
    """type -> {item -> {dois:set, units:set}} for everything that doesn't canonicalise."""
    out = {"materials": {}, "precursors": {}, "coreactants": {}, "quantities": {}}
    for d in sorted(p for p in EXTRACTED.iterdir() if (p / "scout.json").exists()):
        sd = d.name
        sc = json.loads((d / "scout.json").read_text())
        for m in sc.get("materials") or []:
            if m and not lib.canon_material(m):
                out["materials"].setdefault(m, {"dois": set(), "units": set()})["dois"].add(sd)
        for p in sc.get("precursors") or []:
            if p and not lib.canon_precursor(p):
                out["precursors"].setdefault(p, {"dois": set(), "units": set()})["dois"].add(sd)
        for c in sc.get("coreactants") or []:
            if c and not lib.canon_coreactant(c):
                out["coreactants"].setdefault(c, {"dois": set(), "units": set()})["dois"].add(sd)
        recs = (d / "records.json")
        if recs.exists():
            for r in json.loads(recs.read_text()):
                for q, u in [((r.get("measurand") or {}).get("quantity"), (r.get("measurand") or {}).get("unit")),
                             (r.get("coordinate"), r.get("coordinate_unit"))]:
                    if q and not lib.canon_quantity(q):
                        e = out["quantities"].setdefault(q, {"dois": set(), "units": set()})
                        e["dois"].add(sd)
                        if u:
                            e["units"].add(u)
                for k in (r.get("controlled") or {}):
                    if k and not lib.canon_quantity(k):
                        out["quantities"].setdefault(k, {"dois": set(), "units": set()})["dois"].add(sd)
    return out


SCHEMA = f"""You extend an ALD ontology. For each UNMAPPED term, propose a valid entry.
Return ONLY JSON:
{{"materials":[{{"id":"<formula, e.g. BaO>","class":"<one of {MAT_CLASSES} or a new one>",
    "formula":"","metal_atoms":<int>,"aka":[],"new_class":false}}],
 "precursors":[{{"id":"<short id>","class":"<one of {PREC_CLASSES}>","full_name":"",
    "has_ligand":"<one of {LIGANDS} or ''>","deposits":["<material>"],"aka":[]}}],
 "coreactants":[{{"id":"","class":"Oxidant|Reductant|NitrogenSource|PurgeGas|Plasma","full_name":"","aka":[]}}],
 "quantity_kinds":[{{"id":"<snake_case canonical>","label":"<raw term>",
    "category":"<one of {CATS} or a new short id>","new_category":false,
    "family":"<one of {FAMS} or a new short id or ''>","new_family":false,
    "unit":"<SI/plain unit, e.g. 'A', 'A/cm^2', 'F', '1' for dimensionless>",
    "recipe_role":"<one of {ROLES}>","symbols":[]}}]}}
Rules: map to EXISTING classes/categories/families/roles when they fit; only invent a
new category/family when clearly needed (e.g. electrical, optical, composition,
spectral) and set new_*:true. Give canonical snake_case ids for quantities (e.g.
"leakage_current_density","dielectric_constant","atomic_ratio"). Do NOT invent terms
that were not provided."""


def _snake(s):
    import re
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def skeleton(unmapped):
    """Deterministic fallback when the LLM is unavailable: raw terms → minimal
    candidates (needs_classification), so the review file is still produced."""
    return {
        "materials": [{"id": m, "class": None, "needs_classification": True}
                      for m in unmapped["materials"]],
        "precursors": [{"id": p, "class": None, "needs_classification": True}
                       for p in unmapped["precursors"]],
        "coreactants": [{"id": c, "class": None, "needs_classification": True}
                        for c in unmapped["coreactants"]],
        "quantity_kinds": [{"id": _snake(q), "label": q, "unit": (sorted(meta["units"]) or [""])[0],
                            "category": None, "family": None, "recipe_role": None,
                            "needs_classification": True}
                           for q, meta in unmapped["quantities"].items()],
    }


def propose(unmapped, client):
    import time
    lines = []
    for t, items in unmapped.items():
        if items:
            lines.append(f"== {t} ==")
            for it, meta in items.items():
                u = f" [units seen: {sorted(meta['units'])}]" if meta["units"] else ""
                lines.append(f"  {it}{u}")
    from google.genai import types
    for attempt in range(3):
        try:
            r = client.models.generate_content(
                model=MODEL, contents=f"{SCHEMA}\n\nUNMAPPED TERMS:\n" + "\n".join(lines),
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
            u = getattr(r, "usage_metadata", None)
            tok = (getattr(u, "prompt_token_count", 0) or 0, getattr(u, "candidates_token_count", 0) or 0)
            return json.loads(r.text), tok
        except Exception as e:
            print(f"  LLM attempt {attempt+1}/3 failed: {type(e).__name__} {str(e)[:80]}")
            time.sleep(4 * (attempt + 1))
    print("  LLM unavailable → writing deterministic skeleton (re-run to classify).")
    return skeleton(unmapped), (0, 0)


def main():
    from google import genai
    unmapped = gather_unmapped()
    n = sum(len(v) for v in unmapped.values())
    print(f"[propose] {n} unmapped terms: " + ", ".join(f"{k}={len(v)}" for k, v in unmapped.items()))
    if not n:
        print("  nothing to propose."); return
    client = genai.Client(api_key=_key())
    proposals, tok = propose(unmapped, client)

    # attach provenance + review status
    prov = {t: {it: sorted(meta["dois"]) for it, meta in items.items()} for t, items in unmapped.items()}
    doc = {"_meta": {"status_values": ["pending", "approved", "rejected"],
                     "note": "review each entry, set status: approved to merge via 08_merge_ontology.py",
                     "tokens": {"in": tok[0], "out": tok[1]}}}
    for section, key in [("materials", "materials"), ("precursors", "precursors"),
                         ("coreactants", "coreactants"), ("quantity_kinds", "quantities")]:
        entries = proposals.get(section) or []
        for e in entries:
            label = e.get("id") or e.get("label")
            src = None
            for raw, dois in prov[key].items():
                if raw.lower().replace(" ", "").replace("(", "").replace(")", "") in \
                   str(e).lower().replace(" ", "") or (e.get("label") or "").lower() == raw.lower():
                    src = dois; break
            e["status"] = "pending"
            e["provenance"] = src or sorted({d for v in prov[key].values() for d in v})
        doc[section] = entries
    out = PROPOSED / "proposed_ontology.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    print(f"[propose] wrote {sum(len(proposals.get(s) or []) for s in ('materials','precursors','coreactants','quantity_kinds'))} "
          f"candidates → proposed/proposed_ontology.yaml  (tokens in={tok[0]} out={tok[1]})")
    for s in ("materials", "precursors", "coreactants", "quantity_kinds"):
        for e in proposals.get(s) or []:
            extra = (f"cat={e.get('category')}{'*' if e.get('new_category') else ''} "
                     f"fam={e.get('family')}{'*' if e.get('new_family') else ''} unit={e.get('unit')} role={e.get('recipe_role')}"
                     if s == "quantity_kinds" else
                     f"class={e.get('class')} deposits={e.get('deposits','')}")
            print(f"  [{s[:4]}] {e.get('id'):26} {extra}")


if __name__ == "__main__":
    main()
