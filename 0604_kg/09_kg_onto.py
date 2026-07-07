"""
09_kg_onto.py  —  ontology-grounded KG builder (v1.1)
-----------------------------------------------------
Replaces the ad-hoc graph in 09_kg.py. Every node is typed against the ALD
ontology (0706_ontology/ald_ontology.json) and carries its ontology IRI/class.

Key differences from 09_kg.py
  - `variable` is split: QuantityKind (shared, context-free) + QuantityValue
    (per-experiment, carries role independent/controlled/dependent + value).
  - materials/structures resolve to shared ontology individuals -> exact
    cross-paper/cross-experiment linking (no reliance on similar_to).
  - typed edges from the ontology relation vocabulary (deposits, has_geometry,
    reports, of_kind, from_paper, shown_in). similar_to kept as SECONDARY.
  - nothing is silently dropped: unresolved terms become flagged nodes and are
    reported at the end (== ontology gaps to fill).

Input : output/matches.json          (from 08_match.py)
        ../0706_ontology/ald_ontology.json
Output: output/knowledge_graph_onto.graphml
        output/knowledge_graph_onto.json
"""

import json
import re
from pathlib import Path

import networkx as nx

from config import OUTPUT_DIR

ONTO_PATH    = Path(__file__).parent.parent / "0706_ontology" / "ald_ontology.json"
MATCHES_PATH = OUTPUT_DIR / "matches.json"
OUT_GRAPHML  = OUTPUT_DIR / "knowledge_graph_onto.graphml"
OUT_JSON     = OUTPUT_DIR / "knowledge_graph_onto.json"

SIMILARITY_THRESHOLD = 0.1


# ─────────────────────────────────────────────────────────────────────────
# ontology indices
# ─────────────────────────────────────────────────────────────────────────
def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


class Ontology:
    def __init__(self, path: Path):
        o = json.loads(path.read_text())
        self.classes = {c["id"]: c for c in o["classes"]}
        # quantity kind resolution: alias/id/symbol -> quantity record
        self.q_index = {}
        self.quantity = {q["id"]: q for q in o["quantity_kinds"]}
        for q in o["quantity_kinds"]:
            self.q_index[norm(q["id"])] = q
            for a in q.get("aliases", []):
                self.q_index.setdefault(norm(a), q)
            for s in q.get("symbols", []):
                self.q_index.setdefault(norm(s), q)
        # individual resolution per group
        self.ind = {}          # group -> {norm(key): record}
        self.ind_by_id = {}
        for group, items in o["individuals"].items():
            idx = {}
            for it in items:
                self.ind_by_id[it["id"]] = it
                idx[norm(it["id"])] = it
                if it.get("formula"):
                    idx[norm(it["formula"])] = it
                for a in it.get("aka", []):
                    idx.setdefault(norm(a), it)
            self.ind[group] = idx

    def resolve_quantity(self, name):
        return self.q_index.get(norm(name))

    def resolve_individual(self, group, name):
        return self.ind.get(group, {}).get(norm(name))

    def class_iri(self, cid):
        c = self.classes.get(cid)
        return c["iri"] if c else None


# ─────────────────────────────────────────────────────────────────────────
# graph build
# ─────────────────────────────────────────────────────────────────────────
def nid(kind, key):
    return f"{kind}::{key}"


def build(data, onto: Ontology):
    G = nx.MultiDiGraph()
    unresolved = {"material": set(), "structure": set(), "quantity": set()}

    def add(node_id, **attrs):
        if node_id not in G:
            G.add_node(node_id, **attrs)
        return node_id

    def add_quantity_value(exp_id, exp_nid, qname, role, value=None):
        """exp -reports-> QuantityValue -of_kind-> QuantityKind (shared)."""
        q = onto.resolve_quantity(qname)
        if q is None:
            unresolved["quantity"].add(qname)
            qk_id = nid("qk", f"UNMAPPED::{norm(qname)}")
            add(qk_id, ntype="QuantityKind", name=qname, onto_iri=None,
                domain=None, unit=None, flagged=True)
        else:
            qk_id = nid("qk", q["id"])
            add(qk_id, ntype="QuantityKind", name=q["id"], onto_iri=q["iri"],
                domain=q.get("domain"), unit=q.get("unit"),
                qudt=q.get("qudt_quantitykind"), flagged=False)
        qv_id = nid("qv", f"{exp_id}__{norm(qname)}__{role}")
        add(qv_id, ntype="QuantityValue", role=role,
            value="" if value is None else str(value),
            unit=(q.get("unit") if q else None),
            of_quantity=(q["id"] if q else qname))
        G.add_edge(exp_nid, qv_id, etype="reports", role=role)
        G.add_edge(qv_id, qk_id, etype="of_kind")

    for eid, e in data["experiments"].items():
        exp_nid = add(nid("exp", eid), ntype="Experiment",
            onto_class=onto.class_iri("Experiment"),
            experiment_id=eid, series_name=e.get("series_name", ""),
            paper_short=e.get("paper_short", ""),
            is_model=str(e.get("is_model_result", False)),
            figure_id=e.get("figure_id", ""))

        # paper
        paper_nid = add(nid("paper", e["paper"]), ntype="Paper",
            onto_class=onto.class_iri("Paper"), name=e["paper"][:90])
        G.add_edge(exp_nid, paper_nid, etype="from_paper")

        # figure
        if e.get("figure_id"):
            fig_nid = add(nid("fig", f'{e["paper_short"]}__{e["figure_id"]}'),
                ntype="Figure", onto_class=onto.class_iri("Figure"),
                name=e["figure_id"], paper=e.get("paper_short", ""))
            G.add_edge(exp_nid, fig_nid, etype="shown_in")

        # material -> shared ontology individual (typed)
        mat = e.get("material")
        if mat:
            ind = onto.resolve_individual("materials", mat)
            if ind:
                mat_nid = add(nid("mat", ind["id"]), ntype="Material",
                    name=ind["id"], onto_iri=ind["iri"],
                    onto_class=onto.class_iri(ind["class"]),
                    material_class=ind["class"], flagged=False)
            else:
                unresolved["material"].add(mat)
                mat_nid = add(nid("mat", f"UNMAPPED::{norm(mat)}"),
                    ntype="Material", name=mat, onto_iri=None, flagged=True)
            G.add_edge(exp_nid, mat_nid, etype="deposits")

        # structure -> shared ontology individual (typed)
        struct = e.get("structure_type")
        if struct:
            ind = onto.resolve_individual("structures", struct)
            if ind:
                s_nid = add(nid("struct", ind["id"]), ntype="Structure",
                    name=ind["id"], onto_iri=ind["iri"],
                    onto_class=onto.class_iri(ind["class"]),
                    structure_class=ind["class"], flagged=False)
            else:
                unresolved["structure"].add(struct)
                s_nid = add(nid("struct", f"UNMAPPED::{norm(struct)}"),
                    ntype="Structure", name=struct, onto_iri=None, flagged=True)
            G.add_edge(exp_nid, s_nid, etype="has_geometry")

        # quantities -> QuantityValue(role) -> QuantityKind(shared)
        flat = e.get("flat", {}) or {}
        for v in e.get("indep", []):
            add_quantity_value(eid, exp_nid, v, "independent")
        for v in e.get("dep", []):
            add_quantity_value(eid, exp_nid, v, "dependent")
        for v, val in flat.items():
            if v not in e.get("indep", []):
                add_quantity_value(eid, exp_nid, v, "controlled", val)

    # similar_to — SECONDARY now (shared nodes are the primary link)
    for m in data.get("matches", []):
        if m["scores"]["total"] < SIMILARITY_THRESHOLD:
            continue
        a, b = nid("exp", m["exp_a"]), nid("exp", m["exp_b"])
        if a in G and b in G:
            G.add_edge(a, b, etype="similar_to", secondary=True,
                score=round(m["scores"]["total"], 4),
                is_cross_paper=str(m.get("is_cross_paper", "")))

    return G, unresolved


def summarize(G, unresolved):
    from collections import Counter
    ntypes = Counter(d.get("ntype") for _, d in G.nodes(data=True))
    etypes = Counter(d.get("etype") for *_, d in G.edges(data=True))
    flagged = sum(1 for _, d in G.nodes(data=True) if d.get("flagged"))

    print("\n=== ontology-grounded KG ===")
    print("nodes by type:", dict(ntypes))
    print("edges by type:", dict(etypes))
    print(f"flagged (unmapped) nodes: {flagged}")
    for k, s in unresolved.items():
        if s:
            print(f"  UNMAPPED {k}: {sorted(s)}")
    if not any(unresolved.values()):
        print("  all materials / structures / quantities resolved to the ontology")


def main():
    onto = Ontology(ONTO_PATH)
    data = json.loads(MATCHES_PATH.read_text())
    G, unresolved = build(data, onto)

    # GraphML can't serialize None -> write a sanitized copy ("" for None)
    Gml = G.copy()
    for _, d in Gml.nodes(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
    for *_, d in Gml.edges(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
    nx.write_graphml(Gml, OUT_GRAPHML)

    payload = nx.node_link_data(G, edges="links")
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    summarize(G, unresolved)
    print(f"\n-> {OUT_GRAPHML.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()
