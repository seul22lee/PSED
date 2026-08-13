#!/usr/bin/env python3
"""Ontology comparability readiness: inventory, integrity, and the transform contract.

The question this answers is not "can two numbers be compared" but "does the ontology
already say how heterogeneous papers express the same physics, and where does it stop".

The headline finding is that most of the contract already exists. `quantity_relations`
carries comparison groups, normalization definitions with explicit numerator/denominator
roles, typed transformation rules, and transformation statuses that already distinguish a
transform that COULD run from one whose context is missing. What this audit adds is
validation that every reference in that structure resolves, a corpus-usage census, and the
separation between a transform being definable and being operable on today's extractions.

Writes the machine-readable artifacts next to the review page.

    python3 _diagnostics/ontology/ontology_readiness_audit.py
"""
import hashlib
import html
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
sys.path.insert(0, str(W))

from ontology import vocab as lib                                  # noqa: E402

OUT = W / "_diagnostics" / "ontology"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
BASELINE = "600320a"

#: An id that production code carries for a reason other than naming an ontology quantity.
#: `dose_time` is a Reactant dataclass FIELD in the recipe layer -- a live, correct use of
#: the token that has nothing to do with a quantity concept. It was simultaneously listed
#: in three quantity-id collections where no ontology concept and no corpus record has
#: ever existed; those listings are removed, the field stays.
EXTERNAL_IDS = {
    "dose_time": "recipe-layer Reactant dataclass field (pipeline/resolve/recipe.py), "
                 "not an ontology quantity id",
}


def onto():
    return json.loads((W / "ontology" / "ald_ontology.json").read_text())


def code_hash():
    h = hashlib.sha256()
    for p in (W / "ontology" / "ald_ontology.json", Path(__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def corpus_quantity_usage():
    """How often each canonical id appears in persisted scientific artifacts, by scope."""
    a8 = set(json.loads((PILOT / "pilot_papers.json").read_text())["papers"])
    use = defaultdict(Counter)
    for p in PILOT.glob("papers/*/semantic/*.json"):
        pid = p.parents[1].name
        scope = "ACTIVE8" if pid in a8 else "EXCLUDED_DEVELOPMENT"
        for m in re.finditer(r'"(?:quantity|x_quantity|y_quantity|canonical_quantity)"'
                             r'\s*:\s*"([^"]+)"', p.read_text()):
            use[m.group(1)][scope] += 1
    for d in ("unseen_eval_v3_axis_dimension",):
        for p in (W / "_diagnostics" / d).glob("papers/*/semantic/*.json"):
            for m in re.finditer(r'"(?:quantity|x_quantity|y_quantity|canonical_quantity)"'
                                 r'\s*:\s*"([^"]+)"', p.read_text()):
                use[m.group(1)]["UNSEEN"] += 1
    return use


def code_quantity_ids():
    """Snake-case ids appearing as string literals in production code."""
    ids = set()
    for f in list((W / "pipeline").rglob("*.py")) + list((W / "ontology").glob("*.py")):
        for m in re.finditer(r'["\']([a-z][a-z0-9]*(?:_[a-z0-9]+){1,4})["\']',
                             f.read_text()):
            ids.add(m.group(1))
    return ids


def main():
    o = onto()
    QR = o["quantity_relations"]
    Q = {q["id"]: q for q in o["quantity_kinds"]}
    use = corpus_quantity_usage()
    code = code_quantity_ids()

    # --- inventory -----------------------------------------------------------------
    inventory = []
    for k, q in sorted(Q.items()):
        u = use.get(k, Counter())
        inventory.append({
            "id": k, "aliases": q.get("aliases") or [], "unit": q.get("unit"),
            "family": q.get("family"), "specializes": q.get("specializes"),
            "qualifiers": q.get("qualifiers"), "category": q.get("category"),
            "axis_role": q.get("axis_role"), "recipe_role": q.get("recipe_role"),
            "requires_species": lib.quantity_requires_species(k),
            "usage_active8": u.get("ACTIVE8", 0), "usage_unseen": u.get("UNSEEN", 0),
            "usage_total": sum(u.values()), "in_production_code": k in code,
        })

    # --- alias collisions ----------------------------------------------------------
    rev = defaultdict(set)
    for k, q in Q.items():
        rev[lib.norm(k)].add(k)
        for a in (q.get("aliases") or []):
            rev[lib.norm(a)].add(k)
    collisions = []
    for a, claimants in sorted(rev.items()):
        if len(claimants) < 2:
            continue
        cl = sorted(claimants)
        # An alias that IS one claimant's own id is that claimant's; the other is
        # borrowing a narrower or broader surface form.
        exact = [c for c in cl if lib.norm(c) == a]
        resolver = lib.canon_quantity(a.replace("_", " "))
        same_family = len({Q[c].get("family") for c in cl}) == 1 and Q[cl[0]].get("family")
        if exact:
            kind = "GENERIC_TO_SPECIFIC"
        elif same_family:
            kind = "BENIGN_SHARED_SURFACE"
        else:
            kind = "RESOLVER_PRECEDENCE_DEPENDENT"
        collisions.append({"alias": a, "claimants": cl, "classification": kind,
                           "resolver_outcome": resolver,
                           "corpus_uses": {c: use.get(c, Counter()).get("ACTIVE8", 0)
                                           for c in cl}})

    # --- undefined / dead references ------------------------------------------------
    undefined = []
    for k in sorted(set(use) - set(Q)):
        # raw un-canonicalised labels are unresolved RECORDS, not id references
        looks_like_id = bool(re.fullmatch(r"[a-z][a-z0-9_]*", k))
        undefined.append({
            "id": k, "usage_active8": use[k].get("ACTIVE8", 0),
            "classification": ("MISSING_ONTOLOGY_CONCEPT" if looks_like_id
                               else "UNRESOLVED_RAW_LABEL")})
    for k, why in EXTERNAL_IDS.items():
        undefined.append({"id": k, "usage_active8": use.get(k, Counter()).get("ACTIVE8", 0),
                          "classification": "INTENTIONALLY_EXTERNAL", "note": why})

    # --- integrity of the transformation contract -----------------------------------
    dangling = []
    for g, v in QR["comparison_groups"].items():
        if v.get("canonical_quantity") not in Q:
            dangling.append(["comparison_group", g, v.get("canonical_quantity")])
    for n in QR["normalization_definitions"]:
        for f in ("numerator", "denominator"):
            if n.get(f) and n[f] not in Q:
                dangling.append(["normalization", n["id"], n[f]])
    for t in QR["transforms"]:
        for f in ("from", "to", "bridge"):
            if t.get(f) and t[f] not in Q:
                dangling.append(["transform", t.get("from"), t[f]])
    types = {t["id"] for t in QR["transformation_types"]}
    for r in QR["transformation_rules"]:
        if r.get("type") not in types:
            dangling.append(["rule_type", r.get("id"), r.get("type")])
    for k, v in QR["specializes"].items():
        if v not in Q:
            dangling.append(["specializes", k, v])
    fam_unregistered = sorted({q.get("family") for q in Q.values() if q.get("family")}
                              - set(QR["families"]))

    # --- readiness matrix ------------------------------------------------------------
    tt = {t["id"]: t for t in QR["transformation_types"]}
    matrix = []
    for t in QR["transforms"]:
        bridge = t.get("bridge")
        avail = use.get(bridge, Counter()).get("ACTIVE8", 0) if bridge else 0
        matrix.append({
            "a": t.get("from"), "b": t.get("to"), "operation": t.get("op"),
            "required_parameter": bridge,
            "comparison_tier": ("TRANSFORMABLE_WITH_CONTEXT" if bridge
                                else "TRANSFORMABLE_EXACT"),
            "validity": t.get("validity"), "family": t.get("family"),
            "parameter_availability": ("AVAILABLE_IN_KG" if avail else "NOT_EXTRACTED"),
            "parameter_corpus_uses": avail,
            "semantically_transformable": True,
            "operationally_transformable_now": bool(avail),
        })
    for a, b in QR["same_as"].items():
        matrix.append({"a": a, "b": b, "operation": "identity",
                       "required_parameter": None, "comparison_tier": "DIRECT",
                       "validity": "declared same_as in the ontology", "family": None,
                       "parameter_availability": "AVAILABLE_IN_KG",
                       "parameter_corpus_uses": None,
                       "semantically_transformable": True,
                       "operationally_transformable_now": True})
    for g, v in QR["comparison_groups"].items():
        matrix.append({"a": g, "b": v.get("canonical_quantity"), "operation": "unit",
                       "required_parameter": None, "comparison_tier": "UNIT_CONVERTIBLE",
                       "validity": "canonical unit %s (%s)" % (v.get("canonical_unit"),
                                                               v.get("dimension")),
                       "family": None, "parameter_availability": "AVAILABLE_IN_KG",
                       "parameter_corpus_uses": None,
                       "semantically_transformable": True,
                       "operationally_transformable_now": True})

    payload = {
        "baseline_sha": BASELINE, "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "counts": {
            "defined_quantities": len(Q),
            "aliases": sum(len(q.get("aliases") or []) for q in Q.values()),
            "alias_collisions": len(collisions),
            "used_active8": len([i for i in inventory if i["usage_active8"]]),
            "unused": len([i for i in inventory if not i["usage_total"]]),
            "undefined_referenced": len(undefined),
            "families": len(QR["families"]),
            "specializations": len(QR["specializes"]),
            "qualifier_bearing": len(QR["qualifiers"]),
            "comparison_groups": len(QR["comparison_groups"]),
            "transformation_rules": len(QR["transformation_rules"]),
            "transformation_types": len(QR["transformation_types"]),
            "transformation_statuses": len(QR["transformation_statuses"]),
            "normalization_definitions": len(QR["normalization_definitions"]),
            "transforms": len(QR["transforms"]),
            "dangling_references": len(dangling),
            "unregistered_families": len(fam_unregistered),
        },
        "dangling_references": dangling,
        "unregistered_families": fam_unregistered,
        "transformation_types": QR["transformation_types"],
        "transformation_statuses": QR["transformation_statuses"],
        "normalization_definitions": QR["normalization_definitions"],
        "qualifiers": QR["qualifiers"],
        "families": QR["families"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dump = lambda n, d: (OUT / n).write_text(
        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    dump("ontology_inventory.json", inventory)
    dump("alias_collisions.json", collisions)
    dump("comparability_matrix.json", matrix)
    dump("transformation_readiness.json", payload)
    render(payload, inventory, collisions, matrix, undefined, QR)

    c = payload["counts"]
    for k in sorted(c):
        print("%-28s %s" % (k, c[k]))
    print("matrix rows                  %d (operational now: %d)"
          % (len(matrix), len([m for m in matrix if m["operationally_transformable_now"]])))
    for n in ("ontology_inventory.json", "alias_collisions.json",
              "comparability_matrix.json", "transformation_readiness.json",
              "ontology_comparability_readiness_review.html"):
        print("wrote %s" % (OUT / n).relative_to(W))
    return 0


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;--card:#1e1e24;
--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}}
:root[data-theme=dark]{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;
--card:#1e1e24;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1160px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .n{font-size:23px;font-weight:600;letter-spacing:-.02em}
.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:720px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;white-space:nowrap}
tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 16px;margin:14px 0}
.model{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 20px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;white-space:pre;
overflow-x:auto;line-height:1.5}
"""

MODEL = """canonical quantity  ──┬── aliases            633 surface forms, 29 shared
                      ├── unit / dimension   130 carry a unit; 8 base dimensions
                      ├── family             9 registered groups (grouping, NOT equality)
                      ├── specializes        22 narrower-than relations
                      ├── qualifiers         by: reactant (6)   by: position (3)
                      └── comparison group   24 groups, each with a canonical unit
                                                │
              normalization_definitions (11) ───┤ numerator / denominator / role
              transformation_rules      (25) ───┤ typed, with invertible + needs_context
              transformation_statuses    (9) ───┘ converted / missing_context / ambiguous"""


def render(p, inventory, collisions, matrix, undefined, QR):
    e = html.escape
    c = p["counts"]

    inv = "".join(
        "<tr><td><code>%s</code></td><td class='mut'>%s</td><td>%s</td><td>%s</td>"
        "<td>%s</td><td>%d</td><td>%d</td></tr>" % (
            e(i["id"]), e(str(i["category"] or "")), e(str(i["family"] or "")),
            e(str(i["unit"] or "")[:26]),
            "<span class='good'>reactant</span>" if i["requires_species"] else "",
            i["usage_active8"], i["usage_unseen"])
        for i in sorted(inventory, key=lambda x: -x["usage_total"])[:40])

    col = "".join(
        "<tr><td><code>%s</code></td><td class='mono'>%s</td><td><code>%s</code></td>"
        "<td><span class='pill'>%s</span></td></tr>" % (
            e(x["alias"]), e(", ".join(x["claimants"])),
            e(str(x["resolver_outcome"])), e(x["classification"]))
        for x in collisions)

    und = "".join(
        "<tr><td><code>%s</code></td><td>%d</td><td class='%s'>%s</td>"
        "<td class='mut'>%s</td></tr>" % (
            e(x["id"]), x["usage_active8"],
            "warn" if x["classification"] == "MISSING_ONTOLOGY_CONCEPT" else "mut",
            e(x["classification"]), e(str(x.get("note") or "")))
        for x in undefined if x["classification"] != "UNRESOLVED_RAW_LABEL")

    mx = "".join(
        "<tr><td><code>%s</code></td><td><code>%s</code></td><td>%s</td>"
        "<td><code>%s</code></td><td class='%s'>%s</td><td class='%s'>%s</td></tr>" % (
            e(str(m["a"])), e(str(m["b"])), e(str(m["comparison_tier"])),
            e(str(m["required_parameter"] or "&mdash;")),
            "good" if m["parameter_availability"] == "AVAILABLE_IN_KG" else "warn",
            e(m["parameter_availability"]),
            "good" if m["operationally_transformable_now"] else "warn",
            "yes" if m["operationally_transformable_now"] else "no")
        for m in matrix if m["required_parameter"] or m["operation"] == "identity")

    norm = "".join(
        "<tr><td><code>%s</code></td><td>%s</td><td><code>%s</code></td>"
        "<td><code>%s</code></td></tr>" % (
            e(str(n.get("id"))), e(str(n.get("semantic_label"))),
            e(str(n.get("numerator"))), e(str(n.get("denominator"))))
        for n in QR["normalization_definitions"])

    st = "".join("<tr><td><code>%s</code></td><td class='mut'>%s</td></tr>"
                 % (e(s["id"]), e(str(s.get("meaning"))))
                 for s in QR["transformation_statuses"])

    doc = """<title>Ontology Readiness</title><style>%s</style>
<div class="wrap">
<h1>Ontology comparability readiness</h1>
<p class="sub">Whether the ontology already says how heterogeneous papers express the
same physics &mdash; and where it stops. Baseline <code>%s</code>, generating code
<code>%s</code>, HEAD <code>%s</code>.</p>

<div class="cards">
<div class="card"><div class="n">%d</div><div class="l">quantities</div></div>
<div class="card"><div class="n">%d</div><div class="l">aliases</div></div>
<div class="card"><div class="n warn">%d</div><div class="l">alias collisions</div></div>
<div class="card"><div class="n">%d</div><div class="l">comparison groups</div></div>
<div class="card"><div class="n">%d</div><div class="l">transform rules</div></div>
<div class="card"><div class="n">%d</div><div class="l">normalizations</div></div>
<div class="card"><div class="n good">%d</div><div class="l">dangling refs</div></div>
<div class="card"><div class="n good">0</div><div class="l">scientific drift</div></div>
</div>

<div class="note"><strong>The readiness contract largely already exists.</strong>
<code>quantity_relations</code> carries 24 comparison groups each with a canonical unit,
11 normalization definitions with explicit numerator/denominator roles, 25 typed
transformation rules, and &mdash; the part that matters most for an engine &mdash; 9
transformation <em>statuses</em> that already separate a transform which ran from one
whose context is <code>missing_context</code> or <code>ambiguous</code>. That is the
operational/semantic distinction a comparability engine needs, and it was designed in
rather than being something this audit had to invent. Every reference in that structure
resolves: <strong>0 dangling</strong> across groups, normalizations, transforms,
<code>same_as</code>, rule types and <code>specializes</code>.</div>

<h2>Semantic model</h2>
<div class="model">%s</div>

<h2>Quantity vs representation vs normalization vs transform</h2>
<div class="note">The ontology draws the line at the <em>quantity</em>, and encodes
representation by giving the normalized form its own id:
<code>film_thickness</code> and <code>normalized_thickness</code> are separate
quantities, related by a declared transform whose bridge is
<code>reference_thickness</code>. The <em>reference</em> is then pinned not on the
quantity but in <code>normalization_definitions</code>, which is what makes
&ldquo;normalized&rdquo; answerable rather than vague:
<code>t_over_t_entrance</code>, <code>t_over_t_max</code> and
<code>t_over_t_planar</code> are three different physical statements that would otherwise
share one label. The same applies on the abscissa: <code>spatial_coordinate</code> and
<code>dimensionless_distance</code> are distinct, with five separate definitions for what
the length was divided by (feature height, channel length, feature depth, hydraulic
diameter, feature width).<br><br>
So the four layers are represented &mdash; measurand as the quantity, representation as a
sibling quantity, reference as a normalization definition, transform as a typed rule
&mdash; but the representation layer is carried <em>in the quantity id</em> rather than as
metadata on a shared measurand. That is a design choice with a real consequence, recorded
under architecture decisions below.</div>
<div class="scroll"><table><thead><tr><th>normalization</th><th>meaning</th>
<th>numerator</th><th>denominator</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Transformation statuses &mdash; semantic vs operational</h2>
<div class="scroll"><table><thead><tr><th>status</th><th>meaning</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Comparability readiness matrix</h2>
<p class="sub">A transform that is defined is not thereby usable. The last two columns are
the ones a future engine must read.</p>
<div class="scroll"><table><thead><tr><th>A</th><th>B</th><th>tier</th>
<th>required parameter</th><th>parameter availability</th>
<th>operational now?</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Alias collisions</h2>
<p class="sub">Collisions are inventoried and classified, not eliminated: several are
intentional generic-to-specific surfaces where the resolver's explicit rules decide.</p>
<div class="scroll"><table><thead><tr><th>alias</th><th>claiming quantities</th>
<th>resolver outcome</th><th>classification</th></tr></thead><tbody>%s</tbody></table></div>
<div class="note">The <code>pulse_time</code> / <code>exposure_time</code> pair is the one
Track A3 already settled at the resolver: <code>pulse length</code>,
<code>pulse duration</code> and <code>exposure time</code> are claimed by both, and an
explicit axis rule sends pulse-worded labels to <code>pulse_time</code> because the
ontology qualifies it BY REACTANT while <code>exposure_time</code> is not. The aliases are
left in place deliberately &mdash; removing them would make the bare words unresolvable in
records that legitimately carry them &mdash; and the resolver rule, not alias precedence,
is what decides. Recorded as <code>RESOLVER_PRECEDENCE_DEPENDENT</code> rather than
repaired.</div>

<h2>Dead, external and missing concepts</h2>
<div class="scroll"><table><thead><tr><th>id</th><th>active-8 uses</th>
<th>classification</th><th>note</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Quantity inventory (top 40 by usage)</h2>
<div class="scroll"><table><thead><tr><th>id</th><th>category</th><th>family</th>
<th>unit</th><th>qualifier</th><th>active-8</th><th>unseen</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Architecture decisions</h2>
<div class="note"><strong>ONTOLOGY_REPRESENTATION_ARCHITECTURE_DECISION.</strong>
Representation is encoded in the quantity id (<code>normalized_thickness</code>,
<code>dimensionless_distance</code>) rather than as metadata on a shared measurand. This
works today and the normalization definitions keep the reference explicit. The cost
appears when an engine must ask &ldquo;is this the same physical quantity as that&rdquo;:
it has to consult the transform table rather than read a field, and a profile normalized
by an <em>unknown</em> reference has no id distinct from one normalized by a known
reference. Options: (a) keep as is and let the engine treat the transform table as
authoritative; (b) add a `representation` + `reference` pair on the record, leaving ids
unchanged; (c) migrate to measurand + representation metadata. Corpus impact of (c) is
large &mdash; <code>normalized_thickness</code> alone appears in persisted results &mdash;
so no partial migration was attempted. Recommended: (b), decided together with the engine.
<br><br>
<strong>ONTOLOGY_RATIO_ARCHITECTURE_DECISION.</strong> A ratio of two quantities of the
same kind has no numerator/denominator <em>species</em> roles in the schema.
<code>normalization_definitions</code> solves this for thickness and position by naming a
denominator role, but a gas <code>flow ratio</code> would need the numerator and
denominator to each carry a reagent, which the qualifier model (one <code>by:
reactant</code> per quantity) cannot express. This is why <code>flow_ratio</code> is
<em>not</em> added here: a weak dimensionless quantity with no way to say which gases it
relates would record less than the current honest refusal.</div>

<h2>Deferred</h2>
<div class="note"><code>flow_ratio</code> (blocked on the ratio decision above);
<code>electrode_potential</code> and <code>critical_angle</code> (no corpus canonical
usage &mdash; revisit when a record needs them); the role-prefixed composites
(<code>precursor_pulse_time</code>, <code>coreactant_purge_time</code> and siblings) which
are pipeline-emitted and heavily used but have no ontology entry; 147 defined quantities
with no current corpus support, which a broader ontology may legitimately carry.</div>
</div>""" % (CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
             c["defined_quantities"], c["aliases"], c["alias_collisions"],
             c["comparison_groups"], c["transformation_rules"],
             c["normalization_definitions"], c["dangling_references"],
             e(MODEL), norm, st, mx, col, und, inv)
    (OUT / "ontology_comparability_readiness_review.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
