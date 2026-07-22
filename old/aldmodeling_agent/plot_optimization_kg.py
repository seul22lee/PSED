import json
from pathlib import Path
from pyvis.network import Network

def visualize_optimization_kg_html(pdf_name="205301_1_online.pdf"):
    base = Path("./outputs") / pdf_name
    kg_path = base / "optimization_knowledge_graph.json"

    if not kg_path.exists():
        raise FileNotFoundError(f"KG not found: {kg_path}")

    with open(kg_path, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg["nodes"]
    edges = kg["edges"]

    net = Network(height="900px", width="100%", directed=True, bgcolor="#ffffff")

    # ======================================================
    # 1) Build initial node ID set
    # ======================================================
    node_ids = {n["id"] for n in nodes}

    # ======================================================
    # 2) Add missing nodes from edges
    # ======================================================
    for e in edges:
        if e["source"] not in node_ids:
            nodes.append({
                "id": e["source"],
                "type": "derived",
                "label": e["source"],
                "metadata": {"source": "auto_added"}
            })
            node_ids.add(e["source"])

        if e["target"] not in node_ids:
            nodes.append({
                "id": e["target"],
                "type": "derived",
                "label": e["target"],
                "metadata": {"source": "auto_added"}
            })
            node_ids.add(e["target"])

    # ======================================================
    # 3) Remove orphan nodes (nodes not in any edge)
    # ======================================================
    connected_nodes = set()
    for e in edges:
        connected_nodes.add(e["source"])
        connected_nodes.add(e["target"])

    nodes = [n for n in nodes if n["id"] in connected_nodes]

    # ======================================================
    # 4) Node classification
    # ======================================================
    def classify_node(name: str):
        if name in ["T", "p_A0", "p_A", "pulse_time", "purge_time", "c", "p_B"]:
            return "process"
        if name in ["H", "W", "L", "AR", "h"]:
            return "geometry"
        if name in ["M_A", "M_B", "ρ", "d_A", "d_B"]:
            return "material"
        if name in ["N_0", "R", "k_B"]:
            return "constant"
        if name in ["gP", "conformality"]:
            return "objective"
        return "derived"

    node_color_map = {
        "process": "#FFB347",     # orange
        "geometry": "#C2C2F0",    # light purple
        "material": "#76D7C4",    # mint
        "constant": "#D5D8DC",    # gray
        "derived": "#B0E57C",     # green-ish
        "objective": "#FF9999",   # pink
    }

    # ======================================================
    # 5) Edge styles by relation
    # ======================================================
    edge_color_map = {
        "increases": "#2ecc71",          # green
        "positive_influence": "#2ecc71",
        "decreases": "#e74c3c",          # red
        "negative_influence": "#e74c3c",
        "depends_on": "#3498db",         # blue
        "objective_of": "#f39c12",       # orange
        "constraint_of": "#d35400",      # dark orange
        "design_variable": "#8e44ad",    # purple
        "decision_variable": "#c0392b",  # dark red
    }
    default_edge_color = "#555"

    # ======================================================
    # 6) Add nodes (include font color red for process nodes)
    # ======================================================
    for n in nodes:
        nid = n["id"]
        ntype = classify_node(nid)
        color = node_color_map.get(ntype, "#FFFFFF")
        font_color = "red" if ntype == "process" else "black"

        net.add_node(
            nid,
            label=n["label"],
            title=f"type: {ntype}",
            color=color,
            font={"color": font_color}
        )

    # ======================================================
    # 7) Add edges with color + width + style
    # ======================================================
    for e in edges:
        if e["source"] not in connected_nodes or e["target"] not in connected_nodes:
            continue

        rel = e["relation"]
        color = edge_color_map.get(rel, default_edge_color)

        width = 2
        if rel in ["increases", "positive_influence"]:
            width = 3
        elif rel in ["decreases", "negative_influence"]:
            width = 3

        net.add_edge(
            e["source"],
            e["target"],
            label=rel,
            color=color,
            width=width,
            arrows="to"
        )

    # ======================================================
    # 8) Output HTML
    # ======================================================
    out_html = base / "optimization_kg_graph.html"
    net.show(str(out_html))

    print(f"✔ Saved interactive optimization KG → {out_html}")


if __name__ == "__main__":
    visualize_optimization_kg_html()
