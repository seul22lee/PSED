import json
from pyvis.network import Network

# ------------------------------
# Load KG file
# ------------------------------
KG_FILE = "/home/ftk3187/github/PSED/aldmodeling_agent/outputs/agent_logs/6_KGBuilder__205301_1_online.pdf.json"

with open(KG_FILE, "r", encoding="utf8") as f:
    kg = json.load(f)

nodes = kg["nodes"]
edges = kg["edges"]

# ----------------------------------------------------------
# STEP 1: Build degree table
# ----------------------------------------------------------
degree = {n["id"]: 0 for n in nodes}

for e in edges:
    degree[e["source"]] += 1
    degree[e["target"]] += 1

# ----------------------------------------------------------
# STEP 2: Remove nodes with degree < 2
# ----------------------------------------------------------
kept_node_ids = {node_id for node_id, deg in degree.items() if deg >= 2}

filtered_nodes = [n for n in nodes if n["id"] in kept_node_ids]

# ----------------------------------------------------------
# STEP 3: Remove edges tied to removed nodes
# ----------------------------------------------------------
filtered_edges = [
    e for e in edges
    if e["source"] in kept_node_ids and e["target"] in kept_node_ids
]

# ----------------------------------------------------------
# PyVis visualization
# ----------------------------------------------------------
net = Network(height="850px", width="100%", directed=True)
net.barnes_hut()

# --- JSON STRICT (NO JavaScript) ---
net.set_options("""
{
  "nodes": {
    "font": { "size": 30 },
    "scaling": { "min": 20, "max": 30 }
  },
  "edges": {
    "font": { "size": 20 },
    "arrows": { "to": { "enabled": true, "scaleFactor": 1.2 } },
    "smooth": {
      "enabled": true,
      "type": "curvedCW",
      "roundness": 0.3
    },
    "width": 2
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -20000,
      "springLength": 150,
      "springConstant": 0.003
    }
  }
}
""")

# ----------------------------------------------------------
# Add nodes
# ----------------------------------------------------------
for n in filtered_nodes:
    node_id = n["id"]
    label = n.get("label", node_id)
    ntype = n.get("type", "unknown")

    color = {
        "variable": "#1f77b4",
        "equation": "#ff7f0e",
        "parameter": "#2ca02c",
    }.get(ntype, "#7f7f7f")

    net.add_node(
        node_id,
        label=label,
        color=color,
        size=24,  # much smaller nodes (1/5 size)
        title=json.dumps(n, indent=2, ensure_ascii=False)
    )

# ----------------------------------------------------------
# Add edges
# ----------------------------------------------------------
for e in filtered_edges:
    net.add_edge(
        e["source"], e["target"],
        label=e.get("relation", ""),
        title=json.dumps(e, indent=2, ensure_ascii=False),
        width=2
    )

# ----------------------------------------------------------
# Output HTML
# ----------------------------------------------------------
net.show("knowledge_graph.html")
print("Saved to knowledge_graph.html")
