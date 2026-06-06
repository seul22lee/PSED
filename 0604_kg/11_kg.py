"""
11_kg.py
--------
10_match.py 가 생성한 matches.json 을 읽어
NetworkX Knowledge Graph 를 빌드하고 GraphML + JSON 으로 export 한다.

노드 타입:
  experiment  — 개별 실험 series
  paper       — 논문
  material    — 재료 (Al2O3, TiO2, ...)
  variable    — canonical variable (feature_height, cycle_number, ...)

엣지 타입:
  from_paper      experiment → paper
  uses_material   experiment → material
  has_indep       experiment → variable  (independent)
  has_ctrl        experiment → variable  (controlled, value 포함)
  has_dep         experiment → variable  (dependent)
  similar_to      experiment ↔ experiment  (undirected, score 포함)
"""

import json
from pathlib import Path

import networkx as nx

from config import OUTPUT_DIR

MATCHES_PATH = OUTPUT_DIR / "matches.json"
OUT_GRAPHML  = OUTPUT_DIR / "knowledge_graph.graphml"
OUT_JSON     = OUTPUT_DIR / "knowledge_graph.json"

SIMILARITY_THRESHOLD = 0.5  # 이 이상만 similar_to 엣지 생성


# ─────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────
def node_id(ntype: str, name: str) -> str:
    return f"{ntype}::{name}"


def add_node(G: nx.Graph, nid: str, **attrs):
    if nid not in G:
        G.add_node(nid, **attrs)


# ─────────────────────────────────────────
# 그래프 빌드
# ─────────────────────────────────────────
def build_graph(data: dict) -> nx.Graph:
    G = nx.MultiDiGraph()

    exps     = data["experiments"]
    matches  = data["matches"]

    # ── 노드 & 기본 엣지 ──────────────────
    for eid, e in exps.items():
        exp_nid = node_id("experiment", eid)
        add_node(G, exp_nid,
            ntype        = "experiment",
            experiment_id= eid,
            series_name  = e["series_name"],
            paper        = e["paper"][:60],
            material     = e.get("material", ""),
            structure    = e.get("structure_type", ""),
            is_model     = str(e.get("is_model_result", False)),
            figure_id    = e.get("figure_id", ""),
        )

        # paper 노드
        paper_nid = node_id("paper", e["paper"])
        add_node(G, paper_nid, ntype="paper", name=e["paper"][:80])
        G.add_edge(exp_nid, paper_nid, etype="from_paper")

        # material 노드
        if e.get("material"):
            mat_nid = node_id("material", e["material"])
            add_node(G, mat_nid, ntype="material", name=e["material"])
            G.add_edge(exp_nid, mat_nid, etype="uses_material")

        # variable 노드 & 엣지
        flat = e.get("flat", {})
        for vname in e.get("indep", []):
            v_nid = node_id("variable", vname)
            add_node(G, v_nid, ntype="variable", name=vname, domain="independent")
            val = flat.get(vname)
            G.add_edge(exp_nid, v_nid, etype="has_indep",
                       value=str(val) if val is not None else "")

        for vname in e.get("dep", []):
            v_nid = node_id("variable", vname)
            add_node(G, v_nid, ntype="variable", name=vname, domain="dependent")
            G.add_edge(exp_nid, v_nid, etype="has_dep")

        for vname, val in flat.items():
            if vname not in e.get("indep", []):
                v_nid = node_id("variable", vname)
                add_node(G, v_nid, ntype="variable", name=vname, domain="controlled")
                G.add_edge(exp_nid, v_nid, etype="has_ctrl",
                           value=str(val) if val is not None else "")

    # ── similar_to 엣지 ───────────────────
    for m in matches:
        if m["scores"]["total"] < SIMILARITY_THRESHOLD:
            continue
        a_nid = node_id("experiment", m["exp_a"])
        b_nid = node_id("experiment", m["exp_b"])
        G.add_edge(a_nid, b_nid,
            etype            = "similar_to",
            score            = round(m["scores"]["total"], 4),
            indep_sim        = round(m["scores"]["indep_similarity"], 4),
            ctrl_sim         = round(m["scores"]["ctrl_similarity"], 4),
            is_cross_paper   = str(m["is_cross_paper"]),
            dep_overlap      = ",".join(m["dep_overlap"]),
            material         = m["material"],
        )

    return G


# ─────────────────────────────────────────
# JSON export (vis.js / D3 친화적)
# ─────────────────────────────────────────
def graph_to_json(G: nx.Graph) -> dict:
    nodes = []
    for nid, attrs in G.nodes(data=True):
        nodes.append({"id": nid, **attrs})

    edges = []
    for u, v, attrs in G.edges(data=True):
        edges.append({"source": u, "target": v, **attrs})

    return {"nodes": nodes, "edges": edges}


# ─────────────────────────────────────────
# 통계 출력
# ─────────────────────────────────────────
def print_stats(G: nx.Graph):
    from collections import Counter
    ntypes = Counter(d["ntype"] for _, d in G.nodes(data=True))
    etypes = Counter(d.get("etype","?") for _, _, d in G.edges(data=True))

    print(f"\n[GRAPH STATS]")
    print(f"  nodes: {G.number_of_nodes()}")
    for t, c in sorted(ntypes.items()):
        print(f"    {t:20s}: {c}")
    print(f"  edges: {G.number_of_edges()}")
    for t, c in sorted(etypes.items()):
        print(f"    {t:20s}: {c}")

    sim_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("etype") == "similar_to"]
    cross     = [e for e in sim_edges if e[2].get("is_cross_paper") == "True"]
    if sim_edges:
        scores = [e[2]["score"] for e in sim_edges]
        print(f"\n  similar_to edges (>= {SIMILARITY_THRESHOLD}):")
        print(f"    total:       {len(sim_edges)}")
        print(f"    cross-paper: {len(cross)}")
        print(f"    score max:   {max(scores):.3f}")
        print(f"    score mean:  {sum(scores)/len(scores):.3f}")
        print(f"\n  top cross-paper pairs:")
        for u, v, d in sorted(cross, key=lambda x: -x[2]["score"])[:5]:
            print(f"    {u.split('::')[1]} ↔ {v.split('::')[1]}  score={d['score']}  dep={d['dep_overlap']}")


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    if not MATCHES_PATH.exists():
        raise FileNotFoundError(f"먼저 10_match.py 를 실행하세요: {MATCHES_PATH}")

    data = json.load(open(MATCHES_PATH, encoding="utf-8"))
    print(f"[INFO] {len(data['experiments'])} experiments, {len(data['matches'])} pairs loaded")

    G = build_graph(data)
    print_stats(G)

    # GraphML export
    nx.write_graphml(G, OUT_GRAPHML)
    print(f"\n[DONE] GraphML → {OUT_GRAPHML}")

    # JSON export
    g_json = graph_to_json(G)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(g_json, f, indent=2, ensure_ascii=False)
    print(f"[DONE] JSON    → {OUT_JSON}")


if __name__ == "__main__":
    main()
