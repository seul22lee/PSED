#!/usr/bin/env python3
"""
08_merge_ontology.py — close the auto-propose loop: fold APPROVED candidates from
proposed/proposed_ontology.yaml into ontology/core_extensions.yaml (a safe overlay
that build_ontology.py merges — the hand-curated core.yaml is never edited).

  python3 scripts/08_merge_ontology.py            # merge status: approved only
  python3 scripts/08_merge_ontology.py --approve-all   # (demo) treat all as approved
Then: python3 -m ontology.build_ontology     # rebuild the ontology JSON.
"""
import paths as P
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROPOSED = ROOT / "proposed" / "proposed_ontology.yaml"
EXT = P.ONTOLOGY_DIR / "core_extensions.yaml"

MAT_KEYS = ["id", "class", "formula", "molar_mass", "density", "metal_atoms", "aka"]
PREC_KEYS = ["id", "class", "full_name", "has_ligand", "deposits", "molar_mass",
             "central_atoms", "molecular_diameter", "aka"]
CORE_KEYS = ["id", "class", "full_name", "aka"]
Q_KEYS = ["id", "unit", "category", "family", "recipe_role", "symbols", "domain", "label"]


def _clean(e, keys):
    return {k: e[k] for k in keys if e.get(k) not in (None, "", [])}


def main():
    approve_all = "--approve-all" in sys.argv
    doc = yaml.safe_load(PROPOSED.read_text())
    ext = yaml.safe_load(EXT.read_text()) if EXT.exists() else {}
    ext.setdefault("individuals", {})
    ext.setdefault("quantity_kinds", [])
    ext.setdefault("categories", {})
    have_ind = {g: {x["id"] for x in ext["individuals"].get(g, [])} for g in ext["individuals"]}
    have_q = {q["id"] for q in ext["quantity_kinds"]}

    def approved(entries):
        return [e for e in (entries or []) if approve_all or e.get("status") == "approved"]

    n = {"materials": 0, "precursors": 0, "coreactants": 0, "quantity_kinds": 0}
    for section, keys in [("materials", MAT_KEYS), ("precursors", PREC_KEYS), ("coreactants", CORE_KEYS)]:
        for e in approved(doc.get(section)):
            if e.get("needs_classification") or not e.get("class"):
                continue
            if e["id"] in have_ind.get(section, set()):
                continue
            ext["individuals"].setdefault(section, []).append(_clean(e, keys))
            n[section] += 1
    for e in approved(doc.get("quantity_kinds")):
        if e.get("needs_classification") or not e.get("category") or e["id"] in have_q:
            continue
        q = _clean(e, Q_KEYS)
        if q.get("label"):                       # keep raw term as an alias
            q["aliases"] = [q.pop("label")]
        q.setdefault("domain", q.get("category"))
        ext["quantity_kinds"].append(q)
        ext["categories"].setdefault(q["category"], []).append(q["id"])
        n["quantity_kinds"] += 1

    EXT.write_text(yaml.safe_dump(ext, sort_keys=False, allow_unicode=True))
    print(f"[merge] added {n} → {EXT.relative_to(ROOT.parent)}")
    print(f"  new categories: {sorted(set(ext['categories']) )}")
    print("  now run: python3 -m ontology.build_ontology")


if __name__ == "__main__":
    main()
