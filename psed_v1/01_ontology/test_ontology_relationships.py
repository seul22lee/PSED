#!/usr/bin/env python3
"""Checks for relationship rendering in ontology.html.

The viewer embeds the full ontology but previously drew only the class taxonomy and
the relation-type table; the quantity-to-quantity relationships (specializes, same_as,
transforms, in_family, related, defines) were never rendered. These checks pin that
they are now built from the ontology, endpoint-validated, deduplicated, and present in
the generated HTML — and that aliases are NOT invented as edges.

  python3 test_ontology_relationships.py
"""
import importlib.util as u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_sp = u.spec_from_file_location("viz", HERE / "visualize_ontology.py")
viz = u.module_from_spec(_sp); _sp.loader.exec_module(viz)
ONTO = json.loads((HERE / "ald_ontology.json").read_text())
HTML = (HERE / "ontology.html").read_text()

FAIL = []


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


edges, warnings = viz.build_relationship_edges(ONTO)
node_ids = ({c["id"] for c in ONTO["classes"]} | {q["id"] for q in ONTO["quantity_kinds"]})

print("1) edges exist when source relationships exist")
ok("edge count > 0", len(edges) > 0, len(edges))
ok("more than one relationship type", len({e["kind"] for e in edges}) > 1,
   sorted({e["kind"] for e in edges}))

print("2) every edge endpoint resolves to a node (or is reported, never silent)")
unresolved = [e for e in edges if e["source"] not in node_ids or e["target"] not in node_ids]
ok("all endpoints resolve", not unresolved, unresolved[:3])
ok("warnings list matches unresolved", len(warnings) == len(unresolved))

print("3) no duplicate edges")
keys = [(e["source"], e["predicate"], e["target"]) for e in edges]
ok("keys unique", len(keys) == len(set(keys)), len(keys) - len(set(keys)))

print("4) relationship labels preserved and distinct")
for kind in ("specializes", "in_family", "transforms", "defines"):
    ok(f"{kind} edges present", any(e["kind"] == kind for e in edges))
ok("directed flag set on directed kinds",
   all(e["directed"] for e in edges if e["kind"] in ("specializes", "transforms", "in_family", "defines")))
ok("same_as marked undirected",
   all(not e["directed"] for e in edges if e["kind"] == "same_as") or
   not any(e["kind"] == "same_as" for e in edges))

print("5) aliases are NOT turned into edges")
ok("no alias predicate", not any(e["predicate"] in ("alias", "alias_of") for e in edges))
body = HTML.split("def build_relationship_edges", 1)  # HTML has no python; check the generator instead
gen = (HERE / "visualize_ontology.py").read_text()
fn = gen.split("def build_relationship_edges", 1)[1].split("\ndef main", 1)[0]
ok("builder never reads the aliases field", "aliases" not in fn)

print("6) genuine relationships are semantically correct (spot checks)")
def has(s, p, t):
    return any(e["source"] == s and e["predicate"] == p and e["target"] == t for e in edges)
ok("initial_sticking_coefficient specializes sticking_probability",
   has("initial_sticking_coefficient", "specializes", "sticking_probability"))
ok("reactant_A_partial_pressure specializes partial_pressure",
   has("reactant_A_partial_pressure", "specializes", "partial_pressure"))
ok("total_pressure in_family partial_pressure",
   has("total_pressure", "in_family", "partial_pressure"))
ok("film_thickness transforms_to normalized_thickness",
   has("film_thickness", "transforms_to", "normalized_thickness"))

print("7) generated ontology.html embeds the edges and renders them")
D = json.loads(HTML.split("const DATA = ", 1)[1].split(";\n", 1)[0])
ok("_edges embedded", len(D.get("_edges", [])) == len(edges), len(D.get("_edges", [])))
ok("_edge_warnings embedded", "_edge_warnings" in D)
for token in ("Quantity relationships", "edgeFilter", "drawEdges", "in_family", "transforms_to"):
    ok(f"HTML renders {token!r}", token in HTML)
ok("header shows the edge count", f">{len(edges)}<" in HTML)

print("8) current pressure ontology terms present in ontology.html")
for t in ("chamber_total_pressure", "generic_pressure", "precursor_partial_pressure",
          "co_reactant_partial_pressure", "working_pressure", "base_pressure"):
    ok(f"{t} present", t in HTML)

print("9) graph panel emitted in ontology.html")
ok("graph <svg> container present", '<svg id="graph"' in HTML or "id=\"graph\"" in HTML)
ok("graph container has non-zero height CSS", "#graph{" in HTML and "height:560px" in HTML)
ok("Relationship Graph panel present", "Relationship Graph" in HTML)
ok("arrowhead marker code present", 'setAttribute("id","arw-"' in HTML or "arw-" in HTML)
ok("force layout present (no CDN/library)", "function simulate(" in HTML)
import re as _re
_loads = _re.findall(r'(?:src|href)\s*=\s*["\']https?://[^"\']+', HTML)
ok("no remote resource loads (portable/offline; QUDT/OBO strings are data, not loads)",
   not _loads, _loads[:3])
ok("legend/type-filter present", "glegend" in HTML and "selKinds" in HTML)
ok("connected-edge highlighting present", "function focus(" in HTML)
ok("zoom/pan present", "applyTransform" in HTML and "wheel" in HTML)
ok("browser test hooks exposed", "__GRAPH_READY__" in HTML and "__GRAPH_STATS__" in HTML)
ok("deterministic build fingerprint in footer",
   "ontology build " in HTML and __import__("re").search(r"ontology build [0-9a-f]{12}", HTML) is not None)
ok("relationship TABLE still present (secondary view)", 'id="edges"' in HTML and "drawEdges" in HTML)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
