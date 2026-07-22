#!/usr/bin/env python3
import json
from pathlib import Path
import networkx as nx
from pyvis.network import Network


# ============================================================
#  Utility – canonical stringify (list/dict → stable string)
# ============================================================
def canonical_id(x):
    """Convert lists/dicts/non-hashables into stable strings."""
    if isinstance(x, (list, dict)):
        return json.dumps(x, sort_keys=True, ensure_ascii=False)
    return str(x)


# ============================================================
#  Convert attribute to GraphML-safe format
# ============================================================
def graphml_safe(value):
    """
    GraphML은 None, dict, list 등을 허용하지 않는다.
    이 함수는 모든 edge/node attribute를 안전한 string으로 변환한다.
    """
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    try:
        return str(value)
    except:
        return repr(value)


# ============================================================
#  Knowledge Graph Builder + HTML Renderer
# ============================================================
def build_knowledge_graph(rr_json_path: str, output_dir: str = "./kg_output"):

    rr_file = Path(rr_json_path)
    if not rr_file.exists():
        raise FileNotFoundError(f"[ERROR] RelationReasoning JSON not found:\n{rr_json_path}")

    print(f"[INFO] Loading RelationReasoning JSON:\n  {rr_json_path}")

    # Load JSON content
    data = json.loads(rr_file.read_text(encoding="utf8"))

    # Flatten structure: {filename: [relations]}
    if isinstance(data, dict):
        key = next(iter(data))  # e.g. "205301_1_online.pdf"
        relations = data[key]
    else:
        relations = data

    print(f"[INFO] Loaded {len(relations)} relations")

    # Prepare output folder
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # NetworkX graph
    G = nx.DiGraph()

    nodes = set()
    edges = []

    # ============================================================
    #  Build graph
    # ============================================================
    for r in relations:

        src = canonical_id(r.get("source"))
        tgt = canonical_id(r.get("target"))

        rtype = r.get("type", "relation")
        direction = r.get("direction", "unknown")
        evidence = r.get("evidence", "")
        evidence_type = r.get("evidence_type", "")
        eqid = r.get("equation_id")

        # Add nodes
        nodes.add(src)
        nodes.add(tgt)

        if src not in G:
            G.add_node(src, label=src)
        if tgt not in G:
            G.add_node(tgt, label=tgt)

        # Add edge (raw edge list for pyvis)
        edge = {
            "source": src,
            "target": tgt,
            "type": rtype,
            "direction": direction,
            "evidence_type": evidence_type,
            "evidence": evidence,
            "equation_id": eqid,
        }
        edges.append(edge)

        # Edge attributes must be GraphML-safe
        G.add_edge(
            src,
            tgt,
            type=graphml_safe(rtype),
            direction=graphml_safe(direction),
            evidence=graphml_safe(evidence),
            evidence_type=graphml_safe(evidence_type),
            equation_id=graphml_safe(eqid),
        )

    # Save nodes & edges JSON
    with open(out_dir / "kg_nodes.json", "w", encoding="utf8") as f:
        json.dump(list(nodes), f, indent=2, ensure_ascii=False)

    with open(out_dir / "kg_edges.json", "w", encoding="utf8") as f:
        json.dump(edges, f, indent=2, ensure_ascii=False)

    # ============================================================
    #  Save GraphML (SAFE)
    # ============================================================
    try:
        nx.write_graphml(G, out_dir / "kg_graph.graphml")
        print("[INFO] Saved kg_graph.graphml")
    except Exception as e:
        print("[WARN] GraphML saving failed — continuing without GraphML.")
        print(f"       Reason: {e}")

    # ============================================================
    #  Build HTML interactive graph
    # ============================================================
    print("[INFO] Building HTML interactive graph...")

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#000000",
        directed=True,
    )

    net.barnes_hut()  # better physics

    # Add nodes
    for n in nodes:
        net.add_node(
            n,
            label=n,
            title=n,
            shape="dot",
            size=15
        )

    # Add edges
    for e in edges:
        label = e["type"]
        tooltip = (
            f"<b>Relation:</b> {e['type']}<br>"
            f"<b>Direction:</b> {e['direction']}<br>"
            f"<b>Evidence Type:</b> {e['evidence_type']}<br>"
            f"<b>Equation:</b> {e['equation_id']}<br>"
            f"<b>Evidence:</b> {e['evidence']}"
        )

        net.add_edge(
            e["source"],
            e["target"],
            label=label,
            title=tooltip,
            arrows="to"
        )

    html_path = out_dir / "kg_graph.html"
    net.show(str(html_path))


    print(f"[INFO] HTML graph saved to:\n  {html_path}\n")
    print("[INFO] DONE.")


# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    RR_PATH = "/home/ftk3187/github/PSED/aldmodeling_agent/outputs/agent_logs/RelationReasoning__205301_1_online.pdf.json"
    build_knowledge_graph(RR_PATH)
