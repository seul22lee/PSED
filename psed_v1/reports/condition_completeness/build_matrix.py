#!/usr/bin/env python3
"""Condition-completeness matrix: one row per SOURCE-SUPPORTED condition, traced
from the mention to the KG.

Success is not "how many ConditionAssertion objects exist". It is whether each
condition the paper states reaches the correct entity with provenance, and stays
visible downstream. Every row records the first stage at which it is absent.
"""
import csv, json, glob, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "condition_completeness"
KB = REPO / "02_extraction" / "output"


def _num(v):
    """Canonical string form of a value so "3" and 3.0 compare equal."""
    try:
        return "%.12g" % float(v)
    except (TypeError, ValueError):
        return str(v)


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def main():
    kg = J(KB / "knowledge_graph_onto.json", {}) or {}
    kg_assert = set()
    for n in kg.get("nodes", []):
        if n.get("ntype") == "ConditionAssertion":
            kg_assert.add((str(n.get("quantity")), _num(n.get("value")), str(n.get("unit"))))
    canon_papers = {p.parent.parent.name for p in KB.glob("*/canonical/curves.json")}

    rows = []
    for ef in sorted(KB.glob("*/resolved/entities.json")):
        doi = ef.parent.parent.name
        ents = J(ef, []) or []
        cases = J(ef.parent / "experiments.json", []) or []
        asserts = J(ef.parent / "assertions.json", []) or []
        by_entity_case = defaultdict(list)
        for c in cases:
            by_entity_case[c.get("entity_id")].append(c)
        # every assertion the paper supports, whether or not it bound
        a_index = defaultdict(list)
        for a in asserts:
            a_index[(a["quantity"], str(a["value"]), str(a["unit"]))].append(a)

        for e in ents:
            eid = e["entity_id"]
            ecases = by_entity_case.get(eid, [])
            bound = {(b["quantity"], _num(b["value"]), str(b["unit"])): b
                     for b in e.get("bound_conditions") or []}
            amb = {a["quantity"]: a for a in e.get("ambiguous_conditions") or []}
            # rows for BOUND conditions
            for key, b in bound.items():
                key = (b["quantity"], _num(b["value"]), str(b["unit"]))
                def _same(x, y):
                    """Numeric comparison. The assertion keeps the printed string
                    ("3"); the case stores the parsed float (3.0)."""
                    try:
                        return abs(float(x) - float(y)) <= 1e-9 * max(1.0, abs(float(y)))
                    except (TypeError, ValueError):
                        return str(x) == str(y)

                in_case = any(any(c.get("quantity") == b["quantity"] and
                                  _same(c.get("value"), b["value"])
                                  for c in (cs.get("controlled") or []))
                              for cs in ecases)
                in_recipe = any((cs.get("recipe") or {}).get(
                    {"deposition_temperature": "temperature", "cycle_number": "ncycles",
                     "flow_rate": "flow_rate"}.get(b["quantity"], "_none")) is not None
                    for cs in ecases)
                rows.append({
                    "paper": doi,
                    "figure_panel_series": "F%s%s/%s" % (e["printed_figure_number"],
                                                         e["panel"] or "", e["source_series"]),
                    "target_entity": eid,
                    "target_entity_class": e["entity_class"],
                    "quantity": b["quantity"], "species": b.get("species"),
                    "value": b["value"], "unit": b["unit"],
                    "source_evidence": (b.get("raw_evidence") or "")[:120],
                    "evidence_locator": b.get("evidence_locator"),
                    "source_kind": b.get("source_kind"),
                    "assertion_status": b.get("assertion_status"),
                    "evidence_kind": b.get("evidence_kind"),
                    "expected_scope": b.get("scope"),
                    "bound_at_scope": b.get("bound_at_scope"),
                    "mention_recovered": True,
                    "assertion_created": True,
                    "applicability_resolved": True,
                    "binding_status": "bound",
                    "resolved_output_status": "present" if ecases else
                        ("entity_only(no case: %s)" % e["classification"]),
                    "inherited_by_case": in_case if ecases else None,
                    "recipe_status": "present" if in_recipe else "not_a_recipe_field",
                    "kb_status": "present",
                    "kg_status": "present" if key in kg_assert else "absent",
                    "canonical_status": "present" if doi in canon_papers else "absent",
                    "first_missing_stage": (
                        "" if (not ecases or in_case) and key in kg_assert
                        else ("case_inheritance" if ecases and not in_case else "kg")),
                })
            # rows for AMBIGUOUS conditions (assertion exists, deliberately unbound)
            for q, a in amb.items():
                rows.append({
                    "paper": doi,
                    "figure_panel_series": "F%s%s/%s" % (e["printed_figure_number"],
                                                         e["panel"] or "", e["source_series"]),
                    "target_entity": eid, "target_entity_class": e["entity_class"],
                    "quantity": q, "species": a.get("species"),
                    "value": "; ".join(a.get("candidates") or []), "unit": "",
                    "source_evidence": (a.get("reason") or "")[:160],
                    "evidence_locator": None, "source_kind": None,
                    "assertion_status": None, "evidence_kind": None,
                    "expected_scope": a.get("scope"), "bound_at_scope": None,
                    "mention_recovered": True, "assertion_created": True,
                    "applicability_resolved": False,
                    "binding_status": "ambiguous_withheld",
                    "resolved_output_status": "candidates_preserved",
                    "inherited_by_case": False,
                    "recipe_status": "withheld", "kb_status": "candidates_preserved",
                    "kg_status": "present", "canonical_status": "n/a",
                    "first_missing_stage": "applicability",
                })
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "condition_completeness_matrix.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    (OUT / "condition_completeness_matrix.json").write_text(
        json.dumps({"n": len(rows), "rows": rows}, indent=1, ensure_ascii=False))

    b = [r for r in rows if r["binding_status"] == "bound"]
    a = [r for r in rows if r["binding_status"] == "ambiguous_withheld"]
    with_case = [r for r in b if r["inherited_by_case"] is not None]
    print("condition rows: %d  (bound %d, ambiguous-withheld %d)" % (len(rows), len(b), len(a)))
    print("  bound and inherited by an experimental case : %d/%d"
          % (sum(1 for r in with_case if r["inherited_by_case"]), len(with_case)))
    print("  bound on entities with no case (sim/lit/unknown): %d" % (len(b) - len(with_case)))
    print("  visible in KG                                : %d/%d"
          % (sum(1 for r in b if r["kg_status"] == "present"), len(b)))
    print("\nby quantity:")
    for k, v in Counter(r["quantity"] for r in b).most_common(12):
        print("   %-30s %4d" % (k, v))
    print("\nby source kind:")
    for k, v in Counter(str(r["source_kind"]) for r in b).most_common():
        print("   %-30s %4d" % (k, v))
    print("\nby bound scope:")
    for k, v in Counter(str(r["bound_at_scope"]) for r in b).most_common():
        print("   %-30s %4d" % (k, v))
    print("\nfirst missing stage (bound rows):")
    for k, v in Counter(r["first_missing_stage"] or "none" for r in b).most_common():
        print("   %-30s %4d" % (k, v))


if __name__ == "__main__":
    main()
