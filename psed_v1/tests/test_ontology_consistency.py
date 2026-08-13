#!/usr/bin/env python3
"""Ontology structural integrity: every relation must point at something real.

The ontology's job is to let heterogeneous papers say the same physics in one language,
and the part that carries that job is not the quantity list but the relations between
quantities -- comparison groups, normalization definitions, typed transforms. A relation
whose target does not exist is worse than a missing relation: it reads as a capability
and behaves as a hole, and only at query time.

So these tests check reachability rather than taste. They deliberately do NOT demand zero
alias collisions: several are intentional generic-to-specific surfaces that explicit
resolver rules decide, and forbidding them would push the ambiguity somewhere less
visible. What they demand is that every collision be inventoried, and that the resolver
give a deterministic answer for each.

Run:  python3 tests/test_ontology_consistency.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from ontology import vocab as lib                                  # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


ONTO = json.loads((W / "ontology" / "ald_ontology.json").read_text())
QR = ONTO["quantity_relations"]
Q = {q["id"]: q for q in ONTO["quantity_kinds"]}

#: Ids production code carries for a reason other than naming a quantity. `dose_time` is
#: a Reactant dataclass field in the recipe layer; it is not, and never was, an ontology
#: quantity, which is why it was removed from the quantity-id collections that listed it.
EXTERNAL_IDS = {"dose_time"}

#: The resolver's quantity collections are DEFENSIVE: a record may arrive spelling a
#: quantity the way a paper wrote it, so these lists also carry alias surfaces and a few
#: concepts the ontology has not needed to define. Each is classified rather than deleted,
#: because an entry that never matches costs nothing while removing one that does is a
#: silent behaviour change. None has any corpus record today.
CLASSIFIED_NON_QUANTITY_IDS = {
    "growth_temperature": "alias surface of temperature/deposition_temperature",
    "substrate_temperature": "alias surface of temperature/deposition_temperature",
    "pressure": "alias surface of generic_pressure",
    "raman_shift": "alias surface of wavenumber",
    "duty_cycle": "plasma concept with no ontology entry and no corpus record",
    "flow_ratio": "deliberately undefined -- see the ratio architecture decision",
    "precursor_ratio": "composition concept with no ontology entry or corpus record",
    "source_temperature": "delivery-line concept with no ontology entry or corpus record",
    "photon_energy": "spectroscopy coordinate with no ontology entry or corpus record",
}


def main():
    print("=== A. every quantity is well formed ===")
    ok("A: quantity ids are unique",
       len(Q) == len(ONTO["quantity_kinds"]), len(ONTO["quantity_kinds"]) - len(Q))
    ok("A: every id is a snake-case token",
       all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k) for k in Q),
       [k for k in Q if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k)][:4])
    ok("A: every quantity carries aliases", all(q.get("aliases") is not None
                                                for q in Q.values()))

    print("=== B. relation targets exist ===")
    bad = [(k, v) for k, v in QR["specializes"].items() if v not in Q]
    ok("B: every specializes target is a defined quantity", not bad, bad[:4])
    bad = [(g, v.get("canonical_quantity")) for g, v in QR["comparison_groups"].items()
           if v.get("canonical_quantity") not in Q]
    ok("B: every comparison group names a defined canonical quantity", not bad, bad[:4])
    bad = [(n.get("id"), n.get(f)) for n in QR["normalization_definitions"]
           for f in ("numerator", "denominator") if n.get(f) and n[f] not in Q]
    ok("B: every normalization numerator/denominator exists", not bad, bad[:4])
    bad = [(t.get("from"), t.get(f)) for t in QR["transforms"]
           for f in ("from", "to", "bridge") if t.get(f) and t[f] not in Q]
    ok("B: every transform endpoint and bridge exists", not bad, bad[:4])
    bad = [(k, v) for k, v in QR["same_as"].items() if k not in Q or v not in Q]
    ok("B: every same_as pair exists", not bad, bad[:4])
    types = {t["id"] for t in QR["transformation_types"]}
    bad = [r.get("id") for r in QR["transformation_rules"] if r.get("type") not in types]
    ok("B: every transformation rule has a declared type", not bad, bad[:4])
    bad = [q.get("quantity") for q in QR["qualifiers"] if q.get("quantity") not in Q]
    ok("B: every qualifier names a defined quantity", not bad, bad[:4])

    print("=== C. families are a registry, not free text ===")
    declared = {q.get("family") for q in Q.values() if q.get("family")}
    ok("C: every family a quantity declares is registered",
       not (declared - set(QR["families"])), sorted(declared - set(QR["families"])))
    bad = [(f, m) for f, v in QR["families"].items()
           for m in (v.get("members") or []) if m not in Q]
    ok("C: every family member is a defined quantity", not bad, bad[:4])
    bad = [f for f, v in QR["families"].items()
           if v.get("canonical") and v["canonical"] not in Q]
    ok("C: every family canonical is a defined quantity", not bad, bad[:4])
    # family groups quantities; it does NOT assert they are the same quantity
    ok("C: family membership does not imply identity",
       lib.family("pulse_time") == "exposure_time" and "pulse_time" != "exposure_time"
       and QR["families"]["exposure_time"]["canonical"] == "pulse_time",
       lib.family("pulse_time"))

    print("=== D. transformation types are usable by an engine ===")
    for t in QR["transformation_types"]:
        ok("D: %-32s declares invertibility and context" % t["id"],
           "invertible" in t and "needs_context" in t, t)
    ok("D: statuses separate 'converted' from 'context missing'",
       {"converted", "missing_context", "ambiguous"}
       <= {s["id"] for s in QR["transformation_statuses"]})
    ok("D: every status explains itself",
       all(s.get("meaning") for s in QR["transformation_statuses"]))
    # a normalization has to say what the denominator IS, or "normalized" means nothing
    ok("D: every normalization names a denominator role",
       all(n.get("denominator") and n.get("semantic_label")
           for n in QR["normalization_definitions"]))

    print("=== E. alias collisions are inventoried, not forbidden ===")
    rev = defaultdict(set)
    for k, q in Q.items():
        rev[lib.norm(k)].add(k)
        for a in (q.get("aliases") or []):
            rev[lib.norm(a)].add(k)
    coll = {a: sorted(v) for a, v in rev.items() if len(v) > 1}
    ok("E: collisions exist and that is allowed", coll, len(coll))
    # the requirement is determinism, not absence
    ok("E: every colliding alias resolves to exactly one quantity",
       all(lib.canon_quantity(a.replace("_", " ")) in Q or
           lib.canon_quantity(a) in Q for a in coll),
       [a for a in coll if lib.canon_quantity(a.replace("_", " ")) not in Q
        and lib.canon_quantity(a) not in Q][:4])
    ok("E: resolution is stable across repeated calls",
       all(lib.canon_quantity(a) == lib.canon_quantity(a) for a in coll))
    # the pair Track A3 settled at the resolver rather than by deleting aliases
    ok("E: pulse/exposure wording is still a recorded collision",
       {"pulse_time", "exposure_time"} <= set(coll.get("pulse_length", []))
       | set(coll.get("pulse_duration", [])), coll.get("pulse_length"))
    ok("E: and the resolver still sends pulse-worded axes to pulse_time",
       lib.canon_quantity("pulse length") == "pulse_time"
       and lib.canon_quantity("pulse time") == "pulse_time")
    ok("E: while a bare exposure time stays exposure_time",
       lib.canon_quantity("exposure time") == "exposure_time")
    # the audit artifact must agree with what the ontology currently says
    art = W / "_diagnostics" / "ontology" / "alias_collisions.json"
    if art.exists():
        ok("E: the published collision inventory is current",
           {x["alias"] for x in json.loads(art.read_text())} == set(coll),
           len(coll))

    print("=== F. production quantity ids exist or are explicitly external ===")
    # ids listed in the resolver's own quantity collections must be real quantities
    from pipeline.canonical import axis_roles as caxis                  # noqa: E402
    for name, ids in (("_QUANTITY_DIM", set(caxis._QUANTITY_DIM)),
                      ("_PROCESS_QUANTITIES", set(caxis._PROCESS_QUANTITIES)),
                      ("_MEASUREMENT_COORDS", set(caxis._MEASUREMENT_COORDS))):
        unknown = ({i for i in ids if i not in Q} - EXTERNAL_IDS
                   - set(CLASSIFIED_NON_QUANTITY_IDS))
        ok("F: %-22s carries nothing unclassified" % name, not unknown,
           sorted(unknown)[:6])
    ok("F: dose_time is gone from the quantity-id collections",
       "dose_time" not in caxis._QUANTITY_DIM
       and "dose_time" not in caxis._PROCESS_QUANTITIES)
    # ...but it is still a live recipe field, and removing that would be a regression
    ok("F: dose_time survives where it is a recipe field, not a quantity",
       "dose_time" in (W / "pipeline" / "resolve" / "recipe.py").read_text())
    ok("F: and it is not silently reintroduced as a quantity",
       "dose_time" not in Q)
    # the alias-surface entries must keep resolving, which is why they are kept
    for i, why in CLASSIFIED_NON_QUANTITY_IDS.items():
        if "alias surface" in why:
            ok("F: %-20s still resolves to a real quantity" % i,
               lib.canon_quantity(i.replace("_", " ")) in Q,
               lib.canon_quantity(i.replace("_", " ")))
    ok("F: no classified entry has quietly become a quantity",
       not (set(CLASSIFIED_NON_QUANTITY_IDS) & set(Q)),
       sorted(set(CLASSIFIED_NON_QUANTITY_IDS) & set(Q)))

    print("=== G. qualifier semantics the comparison layer depends on ===")
    byq = defaultdict(set)
    for q in QR["qualifiers"]:
        byq[q["by"]].add(q["quantity"])
    ok("G: reactant qualifiers exist", byq.get("reactant"), dict(byq))
    ok("G: position qualifiers exist for result quantities",
       byq.get("position") and "film_thickness" in byq["position"], dict(byq))
    ok("G: every qualifier declares its allowed values",
       all(q.get("values") for q in QR["qualifiers"]))
    # Track A3 reads this; if it moved, condition comparison would silently change
    for q in ("pulse_time", "purge_time", "partial_pressure", "exposure"):
        ok("G: %-18s still requires a species" % q, lib.quantity_requires_species(q))
    for q in ("deposition_temperature", "cycle_number", "exposure_time"):
        ok("G: %-18s still does not" % q, not lib.quantity_requires_species(q))

    print("=== H. the readiness artifacts are consistent with the ontology ===")
    d = W / "_diagnostics" / "ontology"
    for n in ("ontology_inventory.json", "comparability_matrix.json",
              "transformation_readiness.json"):
        ok("H: %s exists" % n, (d / n).exists())
    if (d / "ontology_inventory.json").exists():
        inv = json.loads((d / "ontology_inventory.json").read_text())
        ok("H: the inventory covers every defined quantity",
           {i["id"] for i in inv} == set(Q), len(inv))
    if (d / "comparability_matrix.json").exists():
        mx = json.loads((d / "comparability_matrix.json").read_text())
        ok("H: every matrix row states a tier", all(m.get("comparison_tier") for m in mx))
        ok("H: semantic and operational transformability are separate fields",
           all("semantically_transformable" in m
               and "operationally_transformable_now" in m for m in mx))
        # a transform needing a parameter nobody extracted is not operational
        bad = [m for m in mx if m.get("required_parameter")
               and m["parameter_availability"] != "AVAILABLE_IN_KG"
               and m["operationally_transformable_now"]]
        ok("H: a missing parameter never reads as operational", not bad, bad[:2])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
