#!/usr/bin/env python3
"""Decompose the `N / 72 unresolved entities` figure into its three real counts.

The headline "46 / 72" conflated two different things: how many unresolved
source entities the corpus contains, and how many of them ended up carrying a
condition. It says nothing about whether the missing ones were *supposed* to
carry any, so it cannot distinguish a loss from a source that is simply silent.

This splits it:

  (a) unresolved entities for which the source supplies at least one applicable
      condition (bound or deliberately withheld);
  (b) of those, how many retained EVERY such condition (nothing withheld,
      nothing dropped);
  (c) unresolved entities for which the source supplies no applicable condition
      at all -- these can never carry one, and counting them as a shortfall is
      what made the original ratio misleading.

Read-only. Writes reports/condition_precision/unresolved_metric.{json,md}.
"""
import json
import glob
import sys
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "papers"          # papers/<doi>/resolved/


def main():
    rows = []
    for f in sorted(glob.glob(str(OUT / "*" / "resolved" / "entities.json"))):
        paper = Path(f).parents[1].name
        d = json.loads(Path(f).read_text())
        ents = d if isinstance(d, list) else d.get("entities", [])
        for e in ents:
            if e.get("entity_class") != "UnresolvedSourceEntity":
                continue
            bound = e.get("bound_conditions") or []
            withheld = e.get("ambiguous_conditions") or []
            # "applicable" = the resolver considered it for THIS entity, i.e. it
            # survived the figure/panel/series applicability filter. Bound and
            # withheld groups are both such candidates.
            n_applicable_q = len({b["quantity"] for b in bound}) + \
                len({a["quantity"] for a in withheld})
            rows.append({
                "paper": paper,
                "entity_id": e["entity_id"],
                "unresolved_reason": e.get("unresolved_reason"),
                "n_bound": len(bound),
                "n_withheld_groups": len(withheld),
                "bound_quantities": sorted({b["quantity"] for b in bound}),
                "withheld_quantities": sorted({a["quantity"] for a in withheld}),
                "has_applicable": n_applicable_q > 0,
                "retained_all": bool(bound) and not withheld,
                "source_silent": n_applicable_q == 0,
            })

    total = len(rows)
    a = [r for r in rows if r["has_applicable"]]
    b = [r for r in a if r["retained_all"]]
    c = [r for r in rows if r["source_silent"]]
    partial = [r for r in a if not r["retained_all"]]

    summ = {
        "unresolved_entities_total": total,
        "a_with_supported_applicable_conditions": len(a),
        "b_retained_all_such_conditions": len(b),
        "b_partial_some_withheld_as_ambiguous": len(partial),
        "c_source_provides_no_applicable_condition": len(c),
        "carrying_at_least_one_bound_condition": sum(1 for r in rows if r["n_bound"]),
        "by_unresolved_reason": dict(collections.Counter(
            r["unresolved_reason"] or "unstated" for r in rows)),
        "by_paper": dict(collections.Counter(r["paper"] for r in rows)),
    }
    assert len(a) + len(c) == total, "every unresolved entity is in exactly one of (a),(c)"

    d = Path(__file__).resolve().parent
    (d / "unresolved_metric.json").write_text(
        json.dumps({"summary": summ, "entities": rows}, indent=1))

    L = ["# The `unresolved entities` metric, decomposed", "",
         "| count | meaning |", "|---:|---|",
         "| %d | unresolved source entities in the corpus |" % total,
         "| %d | **(a)** have at least one applicable condition in the source |" % len(a),
         "| %d | **(b)** of (a), retained *every* such condition |" % len(b),
         "| %d | of (a), retained some and withheld the rest as ambiguous |" % len(partial),
         "| %d | **(c)** the source supplies no applicable condition at all |" % len(c),
         "| %d | carry at least one bound condition (the old headline numerator) |"
         % summ["carrying_at_least_one_bound_condition"], "",
         "(a) + (c) = %d = the total, by construction." % total, "",
         "## Why the old ratio was misleading", "",
         "It divided the entities that happen to carry a condition by *all* "
         "unresolved entities, including the %d for which no applicable condition "
         "exists in the paper. Those %d can never move the numerator, so the ratio "
         "understated retention by construction. Against the population that can "
         "actually carry a condition, retention is %d/%d complete and %d/%d partial "
         "(partial meaning conditions were withheld as ambiguous, not lost)." %
         (len(c), len(c), len(b), len(a), len(partial), len(a)), "",
         "## Unresolved-entity reasons", ""]
    L += ["- `%s` — %d" % (k, v) for k, v in
          sorted(summ["by_unresolved_reason"].items(), key=lambda kv: -kv[1])]
    (d / "unresolved_metric.md").write_text("\n".join(L) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
