"""
validate.py
-----------
1. Integrity checks on the compiled ontology (broken parents, dangling
   domain/range, unresolved derived_from/couples, duplicate ids, bad IRIs).
2. Coverage report against the existing KG (0604_kg): how many of the KG's
   `variable` and `material` nodes resolve to an ontology QuantityKind /
   individual, and which do NOT (== ontology gaps to fill next).

Run after build_ontology.py.
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
ONTO = ROOT / "ald_ontology.json"
KG = ROOT.parent / "0604_kg" / "output" / "knowledge_graph.json"


def load_onto():
    return json.loads(ONTO.read_text())


def integrity(o) -> list[str]:
    errors = []
    class_ids = {c["id"] for c in o["classes"]}
    qk_ids = {q["id"] for q in o["quantity_kinds"]}

    # duplicate ids
    for kind, items in [("class", o["classes"]), ("relation", o["relations"]),
                        ("quantity", o["quantity_kinds"])]:
        seen, ids = set(), [i["id"] for i in items]
        for i in ids:
            if i in seen:
                errors.append(f"duplicate {kind} id: {i}")
            seen.add(i)

    # class parents resolve
    for c in o["classes"]:
        p = c.get("parent")
        if p is not None and p not in class_ids:
            errors.append(f"class {c['id']}: parent '{p}' not defined")

    # relation domain/range resolve
    for r in o["relations"]:
        for slot in ("domain", "range"):
            v = r.get(slot)
            if v and v not in class_ids:
                errors.append(f"relation {r['id']}: {slot} '{v}' not a class")

    # individuals point at real classes
    for group, items in o["individuals"].items():
        for it in items:
            if it["class"] not in class_ids:
                errors.append(f"individual {group}/{it['id']}: class '{it['class']}' not defined")

    # quantity derived_from / couples resolve
    for q in o["quantity_kinds"]:
        for slot in ("derived_from", "couples"):
            for ref in q.get(slot, []) or []:
                if ref not in qk_ids:
                    errors.append(f"quantity {q['id']}: {slot} ref '{ref}' not a quantity")

    # IRIs well-formed
    for c in o["classes"]:
        if not str(c.get("iri", "")).startswith("http"):
            errors.append(f"class {c['id']}: bad IRI {c.get('iri')}")
    return errors


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def coverage(o):
    """Map existing KG variable/material node names onto the ontology."""
    # alias index: normalized alias/name -> canonical quantity id
    qindex = {}
    for q in o["quantity_kinds"]:
        qindex[norm(q["id"])] = q["id"]
        for a in q.get("aliases", []):
            qindex[norm(a)] = q["id"]
    # material index from individuals
    mindex = {}
    for it in o["individuals"].get("materials", []):
        mindex[norm(it["id"])] = it["id"]
        mindex[norm(it.get("formula", ""))] = it["id"]

    if not KG.exists():
        print(f"\n(no KG found at {KG} — skipping coverage)")
        return
    kg = json.loads(KG.read_text())
    vars_, mats = set(), set()
    for n in kg["nodes"]:
        if n.get("ntype") == "variable":
            vars_.add(n["name"])
        elif n.get("ntype") == "material":
            mats.add(n["name"])

    v_hit = {v for v in vars_ if norm(v) in qindex}
    v_miss = sorted(vars_ - v_hit)
    m_hit = {m for m in mats if norm(m) in mindex}
    m_miss = sorted(mats - m_hit)

    print("\n=== COVERAGE vs existing KG (0604_kg) ===")
    print(f"variables : {len(v_hit)}/{len(vars_)} resolve to a QuantityKind")
    if v_miss:
        print("  UNMAPPED variables (ontology gaps):")
        for v in v_miss:
            print(f"    - {v}")
    print(f"materials : {len(m_hit)}/{len(mats)} resolve to a seed individual")
    if m_miss:
        print("  UNMAPPED materials (add to individuals.materials):")
        for m in m_miss:
            print(f"    - {m}")


def main():
    o = load_onto()
    errs = integrity(o)
    print("=== INTEGRITY ===")
    if errs:
        for e in errs:
            print("  ERROR:", e)
        print(f"  {len(errs)} error(s)")
    else:
        print("  OK — no structural errors")
    coverage(o)
    return errs


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
