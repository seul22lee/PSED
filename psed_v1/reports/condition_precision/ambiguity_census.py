#!/usr/bin/env python3
"""Census of every withheld-ambiguous condition group.

The 559 withheld rows in the completeness matrix are not 559 independent
decisions: they collapse to a small number of distinct
(paper, quantity, species, scope, candidate-set) patterns replicated across the
entities that share a scope. Enumerating the patterns turns what would have been
a sample into a complete census, so the three questions the audit asks --

  1. is the ambiguity scientifically real?
  2. could a deterministic rule safely resolve it?
  3. was the candidate generated spuriously?

-- are answered for the whole withheld population, with no extrapolation.

Read-only. Writes reports/condition_precision/ambiguity_census.{json,md}.
"""
import paths as P
import json
import glob
import re
import sys
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "papers"          # papers/<doi>/resolved/


def load(paper, name):
    p = P.resolved_dir(paper) / (name + ".json")
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    return d if isinstance(d, list) else d.get(name, [])


def patterns():
    pat = collections.OrderedDict()
    for f in sorted(glob.glob(str(OUT / "*" / "resolved" / "entities.json"))):
        paper = Path(f).parents[1].name
        d = json.loads(Path(f).read_text())
        ents = d if isinstance(d, list) else d.get("entities", [])
        for e in ents:
            for a in e.get("ambiguous_conditions") or []:
                key = (paper, a["quantity"], a.get("species"), a["scope"],
                       tuple(sorted(a["candidates"])))
                rec = pat.setdefault(key, {
                    "paper": paper, "quantity": a["quantity"],
                    "species": a.get("species"), "scope": a["scope"],
                    "candidates": list(sorted(a["candidates"])),
                    "reason": a.get("reason"),
                    "n_candidates": len(a["candidates"]),
                    "entity_rows": 0, "entities": [], "evidence": [],
                    "source_kinds": set(), "locators": set(),
                })
                rec["entity_rows"] += 1
                if len(rec["entities"]) < 6:
                    rec["entities"].append(e["entity_id"])
                for sub in a.get("assertions") or []:
                    rec["source_kinds"].add(sub.get("source_kind"))
                    rec["locators"].add(sub.get("evidence_locator"))
                    ev = (sub.get("value"), sub.get("unit"), sub.get("raw_evidence"),
                          sub.get("source_kind"), sub.get("evidence_locator"),
                          sub.get("figure_number"), sub.get("panel"),
                          sub.get("series_selector"), sub.get("species"),
                          sub.get("assertion_status"))
                    if ev not in rec["evidence"]:
                        rec["evidence"].append(ev)
    for r in pat.values():
        r["source_kinds"] = sorted(x for x in r["source_kinds"] if x)
        r["locators"] = sorted(x for x in r["locators"] if x)
    return list(pat.values())


# ---------------------------------------------------------------- adjudication
# Each rule below states a checkable structural property of the candidate set.
# The verdicts are derived from those properties, never from the candidate order
# and never from a preference for "more bindings".

def distinct_values(rec):
    """Candidates that differ in NUMBER, ignoring unit spelling."""
    seen = set()
    for c in rec["candidates"]:
        m = re.match(r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*)$", c)
        if not m:
            seen.add((None, c.strip()))
            continue
        seen.add((float(m.group(1)), re.sub(r"\s+", "", m.group(2))))
    return seen


def same_number_different_unit(rec):
    nums = {v for v, _u in distinct_values(rec) if v is not None}
    units = {u for _v, u in distinct_values(rec)}
    return len(nums) == 1 and len(units) > 1


def adjudicate(rec):
    """-> (ambiguity_real, deterministic_rule_available, spurious, note)"""
    vals = distinct_values(rec)
    evid = rec["evidence"]

    # (a) The quantity is the figure's own swept axis. There is no conflict
    #     between candidates; the refusal is that a broad-scope value cannot be
    #     broadcast onto entities that each sit at a DIFFERENT point of that
    #     sweep ("temperature was varied from 200 to 350 C" must not become
    #     350 C on every entity). The ambiguity is real -- the source does not
    #     say which entity holds which value -- and no rule resolves it without
    #     inventing an assignment.
    if "varied by a panel/series" in (rec["reason"] or ""):
        return (True, False, False,
                "quantity is the swept axis of this figure; a %s-scope value "
                "cannot be assigned to an individual point of the sweep" %
                rec["scope"])

    # (b) A single surviving candidate outside the varied-axis guard: nothing
    #     was actually in conflict.
    if rec["n_candidates"] == 1:
        return (False, True, False,
                "single candidate withheld with no competing value")

    # (c) Same number, different unit spelling -> a normalisation artifact, not
    #     a scientific disagreement.
    if same_number_different_unit(rec):
        return (False, True, True,
                "identical numeric value under two unit spellings; a unit "
                "normalisation makes the group collapse to one value")

    # (c) Every candidate carries a DIFFERENT species/reactant -> the paper is
    #     not ambiguous, the assertions are simply per-reactant and were keyed
    #     together.
    sp = {e[8] for e in evid}
    if len(sp - {None}) > 1 and len(sp - {None}) == len(evid):
        return (False, True, False,
                "each candidate belongs to a different reactant; keying the "
                "group by species separates them deterministically")

    # (d) Candidates that came from DIFFERENT narrower locators (distinct panels
    #     or series selectors) are separable by scope, not truly ambiguous.
    narrow = {(e[5], e[6], e[7]) for e in evid}
    if len(narrow) == len(evid) and len(narrow) > 1 and \
            any(x[1] or x[2] for x in narrow):
        return (False, True, False,
                "candidates originate from distinct panels/series; a narrower "
                "scope key separates them")

    # (e) Otherwise the source genuinely states several values for one quantity
    #     at one scope with nothing to distinguish them.
    return (True, False, False,
            "the source states %d different values for this quantity at %s "
            "scope with no narrower evidence selecting one" %
            (len({v for v, _ in vals}), rec["scope"]))


def main():
    pats = patterns()
    rows = []
    for r in pats:
        real, rule, spur, note = adjudicate(r)
        rows.append(dict(r, ambiguity_real=real,
                         deterministic_rule_available=rule,
                         spurious_candidate=spur, adjudication=note))
    rows.sort(key=lambda r: (-r["entity_rows"], r["paper"], r["quantity"]))

    n_rows = sum(r["entity_rows"] for r in rows)
    summ = {
        "distinct_patterns": len(rows),
        "withheld_entity_condition_rows": n_rows,
        "ambiguity_real": sum(1 for r in rows if r["ambiguity_real"]),
        "ambiguity_real_rows": sum(r["entity_rows"] for r in rows if r["ambiguity_real"]),
        "deterministic_rule_available": sum(1 for r in rows if r["deterministic_rule_available"]),
        "deterministic_rule_available_rows":
            sum(r["entity_rows"] for r in rows if r["deterministic_rule_available"]),
        "spurious_candidate": sum(1 for r in rows if r["spurious_candidate"]),
        "spurious_candidate_rows": sum(r["entity_rows"] for r in rows if r["spurious_candidate"]),
        "by_quantity": dict(collections.Counter(r["quantity"] for r in rows)),
        "by_scope": dict(collections.Counter(r["scope"] for r in rows)),
        "by_n_candidates": dict(collections.Counter(r["n_candidates"] for r in rows)),
        "resolution_class": dict(collections.Counter(r["adjudication"].split(";")[0]
                                                     for r in rows)),
    }

    d = Path(__file__).resolve().parent
    (d / "ambiguity_census.json").write_text(
        json.dumps({"summary": summ, "patterns": rows}, indent=1))

    L = ["# Withheld-ambiguity census", "",
         "Every withheld group, not a sample: the %d withheld entity-condition rows "
         "collapse to **%d distinct (paper, quantity, species, scope, candidate-set) "
         "patterns**, all of which are adjudicated below." %
         (n_rows, len(rows)), "",
         "| | patterns | entity rows |", "|---|---:|---:|",
         "| ambiguity is scientifically real | %d | %d |" %
         (summ["ambiguity_real"], summ["ambiguity_real_rows"]),
         "| a deterministic rule could resolve it | %d | %d |" %
         (summ["deterministic_rule_available"], summ["deterministic_rule_available_rows"]),
         "| candidate was generated spuriously | %d | %d |" %
         (summ["spurious_candidate"], summ["spurious_candidate_rows"]), "",
         "## Every pattern", "",
         "| paper | quantity | scope | candidates | rows | real? | rule? | spurious? | basis |",
         "|---|---|---|---|---:|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s%s | %s | %s | %d | %s | %s | %s | %s |" % (
            r["paper"], r["quantity"],
            (" (%s)" % r["species"]) if r["species"] else "",
            r["scope"], "; ".join(r["candidates"])[:70], r["entity_rows"],
            "yes" if r["ambiguity_real"] else "no",
            "yes" if r["deterministic_rule_available"] else "no",
            "yes" if r["spurious_candidate"] else "no",
            r["adjudication"]))
    (d / "ambiguity_census.md").write_text("\n".join(L) + "\n")

    print(json.dumps(summ, indent=1))
    for r in rows:
        if not r["ambiguity_real"]:
            print("  RESOLVABLE %-26s %-22s %-7s %s" %
                  (r["paper"][:26], r["quantity"], r["scope"],
                   "; ".join(r["candidates"])[:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
