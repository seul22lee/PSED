"""
s09_kg.py  (Phase B3)  — no LLM
-------------------------------
Build the ontology-grounded knowledge graph from the RESOLVED experiments (s08).
Typed nodes + typed edges, with the granularity relations made explicit:
  Experiment --varies--> QuantityKind        (profile axis)
  Experiment --in_series--> ExperimentSeries
  ExperimentSeries --series_varies--> QuantityKind
Shared individuals (material/precursor/coreactant/quantity) give exact cross-
experiment links; similarity is not used as a primary edge. Background-tagged
experiments are kept but flagged (not linked as deposits).

Output: output/knowledge_graph_onto.{json,graphml}
"""
import json
from collections import Counter
import networkx as nx
from lib import papers, OUTPUT, ONTO

CLASS_IRI = {c["id"]: c["iri"] for c in ONTO["classes"]}
QK_IRI = {q["id"]: q["iri"] for q in ONTO["quantity_kinds"]}


def nid(kind, key):
    return f"{kind}::{key}"


def add(G, node_id, **a):
    if node_id not in G:
        G.add_node(node_id, **a)
    return node_id


def qvalue(G, exp_nid, eid, var, role):
    qk = var.get("quantity")
    if not qk:
        return
    qk_nid = add(G, nid("qk", qk), ntype="QuantityKind", name=qk,
                 onto_iri=QK_IRI.get(qk), flagged=(qk not in QK_IRI))
    qv_nid = add(G, nid("qv", f"{eid}__{qk}__{role}__{var.get('symbol','')}"),
                 ntype="QuantityValue", role=role,
                 value="" if var.get("value") is None else str(var.get("value")),
                 unit=var.get("unit") or "", of_reactant=var.get("of_reactant") or "")
    G.add_edge(exp_nid, qv_nid, etype="reports", role=role)
    G.add_edge(qv_nid, qk_nid, etype="of_kind")


def build():
    G = nx.MultiDiGraph()
    for p in papers():
        pid = p["pid"]
        rf = OUTPUT / pid / "resolved" / "experiments.json"
        if not rf.exists():
            continue
        exps = json.loads(rf.read_text())
        paper_nid = add(G, nid("paper", pid), ntype="Paper",
                        onto_class=CLASS_IRI["Paper"], name=pid)
        # series nodes
        sf = OUTPUT / pid / "resolved" / "series.json"
        series = json.loads(sf.read_text()) if sf.exists() else {}
        for key, s in series.items():
            s_nid = add(G, nid("series", f"{pid}__{key}"), ntype="ExperimentSeries",
                        onto_class=CLASS_IRI["ExperimentSeries"], figure=s["figure"])
            if s.get("series_varies"):
                qk_nid = add(G, nid("qk", s["series_varies"]), ntype="QuantityKind",
                             name=s["series_varies"], onto_iri=QK_IRI.get(s["series_varies"]))
                G.add_edge(s_nid, qk_nid, etype="series_varies")

        for i, e in enumerate(exps):
            eid = f"{pid}__{i:04d}"
            exp_nid = add(G, nid("exp", eid), ntype="Experiment",
                          onto_class=CLASS_IRI["Experiment"], series_name=e.get("series_name") or "",
                          granularity=e.get("granularity") or "", relevance=e.get("relevance") or "",
                          is_model=str(e.get("is_model_result", False)))
            G.add_edge(exp_nid, paper_nid, etype="from_paper")
            # material (only link when experimental; background flagged on node)
            if e.get("material"):
                m_nid = add(G, nid("mat", e["material"]), ntype="Material", name=e["material"],
                            onto_iri=CLASS_IRI.get("Material"))
                G.add_edge(exp_nid, m_nid, etype="deposits", relevance=e.get("relevance") or "")
            if e.get("structure"):
                s_nid = add(G, nid("struct", e["structure"]), ntype="Structure", name=e["structure"])
                G.add_edge(exp_nid, s_nid, etype="has_geometry")
            for pr in e.get("precursors", []) or []:
                if pr:
                    G.add_edge(exp_nid, add(G, nid("prec", pr), ntype="Precursor", name=pr),
                               etype="uses_precursor")
            for co in e.get("coreactants", []) or []:
                if co:
                    G.add_edge(exp_nid, add(G, nid("core", co), ntype="Coreactant", name=co),
                               etype="with_coreactant")
            for v in e.get("controlled", []) or []:
                qvalue(G, exp_nid, eid, v, "controlled")
            for v in e.get("dependent", []) or []:
                qvalue(G, exp_nid, eid, v, "dependent")
            for qk in e.get("varies", []) or []:
                qk_nid = add(G, nid("qk", qk), ntype="QuantityKind", name=qk, onto_iri=QK_IRI.get(qk))
                G.add_edge(exp_nid, qk_nid, etype="varies")
            if e.get("in_series"):
                G.add_edge(exp_nid, nid("series", f"{pid}__{e['in_series']}"), etype="in_series")
    return G


def main():
    G = build()
    Gml = G.copy()
    for _, d in Gml.nodes(data=True):
        for k, val in list(d.items()):
            if val is None: d[k] = ""
    for *_, d in Gml.edges(data=True):
        for k, val in list(d.items()):
            if val is None: d[k] = ""
    nx.write_graphml(Gml, OUTPUT / "knowledge_graph_onto.graphml")
    (OUTPUT / "knowledge_graph_onto.json").write_text(
        json.dumps(nx.node_link_data(G, edges="links"), indent=2, ensure_ascii=False))
    nt = Counter(d.get("ntype") for _, d in G.nodes(data=True))
    et = Counter(d.get("etype") for *_, d in G.edges(data=True))
    print("nodes:", dict(nt))
    print("edges:", dict(et))
    print(f"-> {OUTPUT/'knowledge_graph_onto.json'}")


if __name__ == "__main__":
    main()
