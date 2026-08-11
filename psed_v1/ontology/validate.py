"""
validate.py
-----------
1. Integrity checks on the compiled ontology (broken parents, dangling
   domain/range, unresolved derived_from/couples, duplicate ids, bad IRIs).
2. Coverage report against the LIVE ontology-grounded KG: how many of its
   `variable` and `material` nodes resolve to an ontology QuantityKind /
   individual, and which do NOT (== ontology gaps to fill next).

Run after build_ontology.py.
"""

from __future__ import annotations   # this repo runs on Python 3.8; `list[str]` needs it
import paths as P

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ONTO = ROOT / "ald_ontology.json"
# The live KG is the ontology-grounded one built by pipeline/review/build_kg.py.

KG = P.knowledge_graph_json()


def load_onto():
    return json.loads(ONTO.read_text())


def comparability(o) -> list[str]:
    """Integrity of the comparability layer (transformation rules, normalization
    definitions, comparison groups). build_ontology.py already fails hard on these,
    so anything found here means a hand-edited ald_ontology.json."""
    errors = []
    qr = o.get("quantity_relations", {}) or {}
    qk_ids = {q["id"] for q in o["quantity_kinds"]}
    class_ids = {c["id"] for c in o["classes"]}
    for need in ("TransformationRule", "TransformationExecution",
                 "NormalizationDefinition", "ComparisonGroup", "ContextBinding",
                 "AxisSemantics"):
        if need not in class_ids:
            errors.append(f"comparability class missing: {need}")
    groups = qr.get("comparison_groups", {}) or {}
    ndefs = {n["id"]: n for n in qr.get("normalization_definitions", []) or []}
    if not groups:
        errors.append("no comparison_groups declared")
    if not ndefs:
        errors.append("no normalization_definitions declared")
    for nid, n in ndefs.items():
        for slot in ("numerator", "denominator"):
            if n.get(slot) and n[slot] not in qk_ids:
                errors.append(f"normalization_definition {nid}: {slot} '{n[slot]}' not a quantity")
        if n.get("comparison_group") not in groups:
            errors.append(f"normalization_definition {nid}: unknown comparison_group")
    seen_rule = set()
    for r in qr.get("transformation_rules", []) or []:
        if r["id"] in seen_rule:
            errors.append(f"duplicate transformation_rule id: {r['id']}")
        seen_rule.add(r["id"])
        if r.get("normalization_definition") and r["normalization_definition"] not in ndefs:
            errors.append(f"transformation_rule {r['id']}: unknown normalization_definition")
    for gid, g in groups.items():
        if g.get("canonical_quantity") not in qk_ids:
            errors.append(f"comparison_group {gid}: canonical_quantity not a quantity")
    return errors


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
        # live KG (build_kg.py) types: QuantityKind / Material. The pre-ontology
        # legacy node names (variable / material) are accepted too so an older graph
        # still reports instead of silently scoring 0/0.
        nt = n.get("ntype")
        if nt in ("QuantityKind", "variable"):
            vars_.add(n.get("name") or n.get("id"))
        elif nt in ("Material", "material"):
            mats.add(n.get("name") or n.get("id"))

    v_hit = {v for v in vars_ if norm(v) in qindex}
    v_miss = sorted(vars_ - v_hit)
    m_hit = {m for m in mats if norm(m) in mindex}
    m_miss = sorted(mats - m_hit)

    print("\n=== COVERAGE vs live KG (papers/_corpus/knowledge_graph_onto.json) ===")
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
    errs = integrity(o) + comparability(o)
    print("=== INTEGRITY ===")
    if errs:
        for e in errs:
            print("  ERROR:", e)
        print(f"  {len(errs)} error(s)")
    else:
        print("  OK — no structural errors")
    c = o.get("_counts", {})
    print("=== COMPARABILITY LAYER ===")
    for k in ("transformation_rules", "transformation_types", "transformation_statuses",
              "normalization_definitions", "comparison_groups"):
        print(f"  {k:<28}{c.get(k)}")
    coverage(o)
    return errs


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
