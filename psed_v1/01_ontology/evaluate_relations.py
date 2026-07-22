"""
evaluate_relations.py
---------------------
Evaluate how well the ontology's RELATIONS are represented in the ontology map
(not just how many there are). Reports five representation-quality dimensions:

  1. Typing        - does every relation have a resolvable domain and range?
  2. Connectivity  - is every class reachable through some relation (no orphans
                     in the relation map), and where are the hubs?
  3. Balance       - relationship richness: relations vs. pure taxonomy (is the
                     map a rich web or just a class tree?)
  4. Semantics     - relation characteristics (inverse / symmetric / transitive /
                     functional / acyclic) declared where they should be?
  5. Competency    - can the relation set actually answer the KB's target
                     questions? (the real test of "well represented")

Also reports ABox usage: which relations are instantiated in the current KG.
"""
import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).parent
ONTO = json.loads((ROOT / "ald_ontology.json").read_text())
KG_PATH = ROOT.parent / "0604_kg" / "output" / "knowledge_graph_onto.json"

CLASSES = {c["id"]: c for c in ONTO["classes"]}
RELATIONS = ONTO["relations"]
GENERIC = {"broader", "related"}  # SKOS navigation, not domain-specific

# children map for inheritance propagation
CHILDREN = defaultdict(list)
for c in ONTO["classes"]:
    if c.get("parent"):
        CHILDREN[c["parent"]].append(c["id"])


def descendants(cid):
    out, stack = set(), [cid]
    while stack:
        n = stack.pop()
        for ch in CHILDREN.get(n, []):
            if ch not in out:
                out.add(ch); stack.append(ch)
    return out


def bar(x, n=24):
    f = int(round(x * n))
    return "█" * f + "·" * (n - f)


# ---------------------------------------------------------------- 1. Typing
def typing():
    ok = sum(1 for r in RELATIONS if r.get("domain") in CLASSES and r.get("range") in CLASSES)
    print("1. TYPING  (every relation constrained by domain + range)")
    print(f"   {ok}/{len(RELATIONS)} relations fully typed   {bar(ok/len(RELATIONS))}")
    for r in RELATIONS:
        if r.get("domain") not in CLASSES or r.get("range") not in CLASSES:
            print(f"     ! {r['id']}: domain/range unresolved")
    return ok == len(RELATIONS)


# --------------------------------------------------------- 2. Connectivity
def connectivity():
    # a class is 'in the relation map' if it (or an ancestor) is a domain/range
    # of a domain-specific relation, propagated down to subclasses.
    covered = set()
    for r in RELATIONS:
        if r["id"] in GENERIC:
            continue
        for slot in ("domain", "range"):
            c = r.get(slot)
            if c in CLASSES:
                covered.add(c)
                covered |= descendants(c)
    orphans = sorted(set(CLASSES) - covered - {"Entity"})
    deg = Counter()
    for r in RELATIONS:
        if r["id"] in GENERIC:
            continue
        deg[r["domain"]] += 1
        deg[r["range"]] += 1
    print("\n2. CONNECTIVITY  (is every class wired into the relation map?)")
    cov = len(covered) / (len(CLASSES) - 1)
    print(f"   {len(covered)}/{len(CLASSES)-1} classes reachable via a relation   {bar(cov)} {cov:.0%}")
    print(f"   hubs (most-connected classes): " +
          ", ".join(f"{c}({n})" for c, n in deg.most_common(5)))
    if orphans:
        print(f"   ORPHAN branches — no domain-specific relation attaches ({len(orphans)}):")
        # collapse to top-most orphan ancestors for readability
        roots = [o for o in orphans if CLASSES[o].get("parent") not in orphans]
        for o in roots:
            kids = [k for k in orphans if k != o and o in _ancestors(k)]
            tag = f"  (+{len(kids)} subclasses)" if kids else ""
            print(f"     - {o}{tag}")
    return orphans


def _ancestors(cid):
    out, c = set(), CLASSES[cid].get("parent")
    while c:
        out.add(c); c = CLASSES.get(c, {}).get("parent")
    return out


# ------------------------------------------------------------- 3. Balance
def balance():
    S = sum(1 for c in ONTO["classes"] if c.get("parent"))  # is-a edges
    R = len([r for r in RELATIONS if r["id"] not in GENERIC])
    rr = R / (R + S)
    print("\n3. BALANCE  (relationship richness = non-taxonomic edges / all edges)")
    print(f"   {R} relations vs {S} is-a edges  ->  RR = {rr:.2f}   {bar(rr)}")
    verdict = ("web-like" if rr > 0.4 else "balanced" if rr > 0.25 else "taxonomy-heavy")
    print(f"   map character: {verdict.upper()} "
          f"(low RR => expressive power sits in the class tree, not the relations)")
    return rr


# ----------------------------------------------------------- 4. Semantics
def semantics():
    print("\n4. SEMANTICS  (are logical characteristics declared where they matter?)")
    self_ref = [r for r in RELATIONS if r.get("domain") == r.get("range")]
    have_char = [r for r in RELATIONS if any(k in r for k in
                 ("inverse", "symmetric", "transitive", "functional", "acyclic"))]
    print(f"   self-referential relations (need symmetric/transitive/acyclic): "
          f"{', '.join(r['id'] for r in self_ref)}")
    print(f"   relations with a declared characteristic: {len(have_char)}/{len(RELATIONS)}")
    print(f"   relations with a declared inverse:        "
          f"{sum(1 for r in RELATIONS if 'inverse' in r)}/{len(RELATIONS)}")
    # semantic smell: 'X governed_by Model' reads backwards (a regime isn't
    # governed by a model; a model applies to a regime)
    smells = []
    for r in RELATIONS:
        if r["id"] == "governed_by":
            smells.append("governed_by: ProcessRegime->Model reads backwards; "
                          "consider Model --applies_to--> ProcessRegime")
        if r["id"] == "reaction_pathway":
            smells.append("reaction_pathway is a noun; verb form (has_reaction_pathway/"
                          "induces_reaction) is more consistent")
    for s in smells:
        print(f"   smell: {s}")


# ---------------------------------------------------------- 5. Competency
# Each competency question maps to the relation(s) whose composition answers it.
CQS = [
    ("Which precursor+coreactant produce material M?",      ["uses_precursor", "with_coreactant", "deposits"]),
    ("What sticking probability did precursor P give?",      ["uses_precursor", "reports", "of_kind"]),
    ("Which models apply in regime R?",                     ["applies_to"]),
    ("What ligands does precursor P carry?",                ["has_ligand"]),
    ("How is quantity Q derived from other quantities?",    ["derived_from"]),
    ("Which experiments compare cross-paper on quantity Q?",["reports", "of_kind"]),
    ("What assumptions does model X make?",                 ["makes_assumption"]),
    ("What flow regime does STRUCTURE S impose?",           ["imposes_flow_regime"]),
    ("Which measurement method measures QUANTITY Q?",       ["measured_by_method"]),
    ("Which applications directly cite MATERIAL M?",        ["used_in"]),
]
REL_IDS = {r["id"] for r in RELATIONS}


def competency():
    print("\n5. COMPETENCY  (can the relations actually answer the KB's questions?)")
    ok = 0
    for q, need in CQS:
        missing = [n for n in need if not n.startswith("__") and n not in REL_IDS]
        synthetic = [n for n in need if n.startswith("__")]
        if not missing and not synthetic:
            print(f"   [✓] {q}")
            ok += 1
        elif synthetic:
            print(f"   [ ] {q}")
            print(f"        gap: no direct relation ({synthetic[0].strip('_')}); "
                  f"only answerable indirectly via Experiment, if at all")
        else:
            print(f"   [~] {q}   missing: {missing}")
    print(f"   directly answerable: {ok}/{len(CQS)}   {bar(ok/len(CQS))}")


# ---------------------------------------------------------- ABox usage
def abox_usage():
    print("\nABOX USAGE  (which declared relations are actually instantiated?)")
    if not KG_PATH.exists():
        print("   (no KG found)"); return
    kg = json.loads(KG_PATH.read_text())
    used = Counter(e.get("etype") for e in kg["links"])
    onto_used = {e for e in used if e in REL_IDS}
    non_onto = {e for e in used if e not in REL_IDS}
    unused = sorted(REL_IDS - onto_used)
    print(f"   instantiated ontology relations: {sorted(onto_used)}")
    print(f"   declared-but-unused ({len(unused)}): {unused}")
    if non_onto:
        print(f"   edges in KG NOT backed by an ontology relation: {sorted(non_onto)} "
              f"(e.g. 'similar_to' is a computed link, not an ontology relation)")


# ------------------------------------------------------ 6. Quantity web
def quantity_web():
    qks = {q["id"]: q for q in ONTO["quantity_kinds"]}
    ids = set(qks)
    print("\n6. QUANTITY WEB  (the quantity<->quantity relations — the physics)")

    # specialization: resolves + acyclic
    spec = {i: q["specializes"] for i, q in qks.items() if q.get("specializes")}
    unresolved = [c for c, p in spec.items() if p not in ids]
    def cyclic(c):
        seen, cur = set(), c
        while cur in spec:
            if cur in seen:
                return True
            seen.add(cur); cur = spec[cur]
        return False
    cyc = [c for c in spec if cyclic(c)]
    print(f"   specializations: {len(spec)}   "
          f"unresolved parent: {len(unresolved)}   cyclic: {len(cyc)}")
    if unresolved: print(f"     ! parent not a quantity: {unresolved}")
    if cyc:        print(f"     ! specialization cycle: {cyc}")

    # equation closure: every input quantity must exist
    eqs = [(i, q["defined_by"]) for i, q in qks.items() if q.get("defined_by")]
    closed = 0
    for q, d in eqs:
        missing = [x for x in d.get("inputs", []) if x not in ids]
        if missing:
            print(f"     ! {q}: inputs not defined -> {missing}")
        else:
            closed += 1
    print(f"   defining equations: {len(eqs)}   closed (all inputs exist): "
          f"{closed}/{len(eqs)}   {bar(closed/len(eqs) if eqs else 1)}")

    # quantity-web edge count: before (v0.1) vs now
    couples = sum(len(q.get("couples", []) or []) for q in qks.values())
    derived = sum(len(q.get("derived_from", []) or []) for q in qks.values())
    same_as = sum(1 for q in qks.values() if q.get("same_as"))
    related = sum(len(q.get("related", []) or []) for q in qks.values())
    input_edges = sum(len(d.get("inputs", [])) for _, d in eqs)
    before = couples + derived
    now = before + len(spec) + input_edges + same_as + related
    print(f"   quantity-web edges:  before (derived_from+couples) = {before}"
          f"   ->  now = {now}   ({now/before:.1f}x)" if before else f"   edges now = {now}")
    print(f"     breakdown: specializes={len(spec)}, equation-inputs={input_edges}, "
          f"couples={couples}, derived_from={derived}, same_as={same_as}, related={related}")


def main():
    print("=" * 70)
    print("RELATION REPRESENTATION QUALITY —", ONTO["meta"]["name"], "v" + str(ONTO["meta"]["version"]))
    print("=" * 70)
    typing(); connectivity(); balance(); semantics(); competency(); quantity_web(); abox_usage()


if __name__ == "__main__":
    main()
