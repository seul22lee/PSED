import json
from graphviz import Digraph
from pathlib import Path

# ==========================================
# JSON 경로 (여기만 바꾸면 됨)
# ==========================================

JSON_PATH = Path("/home/ftk3187/github/PSED/0226_kb/extracted/052401_1_online/structured_kb_with_measurements.json")
#JSON_PATH = Path("/home/ftk3187/github/PSED/0226_kb/extracted/132603_1_5.0169339/structured_kb_with_measurements.json")


# ==========================================
# Visualization
# ==========================================

def visualize_kb(json_path: Path):

    if not json_path.exists():
        print("JSON file not found.")
        return

    data = json.loads(json_path.read_text())

    dot = Digraph(comment="Structured KB")
    dot.attr(rankdir="TB")
    dot.attr("node", shape="box")

    # Root
    dot.node("ROOT", "Paper")

    # -------------------------
    # Process Context
    # -------------------------
    if "process_context" in data:
        dot.node("PROCESS", "ProcessContext")
        dot.edge("ROOT", "PROCESS")

        for key, value in data["process_context"].items():
            node_id = f"PC_{key}"
            label = f"{key}\n{value}"
            dot.node(node_id, label)
            dot.edge("PROCESS", node_id)

    # -------------------------
    # Studies
    # -------------------------
    for study in data.get("studies", []):

        study_id = study.get("study_id", "unknown")
        description = study.get("description", "")

        dot.node(study_id, f"{study_id}\n{description}")
        dot.edge("ROOT", study_id)

        # Samples
        for sample in study.get("samples", []):

            sample_id = sample.get("sample_id", "unknown_sample")

            dot.node(sample_id, sample_id)
            dot.edge(study_id, sample_id)

            # ---- Condition variables ----
            for key, value in sample.items():

                if key in ["sample_id", "measurements"]:
                    continue

                cond_node = f"{sample_id}_{key}"
                dot.node(cond_node, f"{key} = {value}")
                dot.edge(sample_id, cond_node)

            # ---- Measurements ----
            for idx, m in enumerate(sample.get("measurements", [])):

                quantity = m.get("quantity", "unknown")
                value = m.get("value", "")
                unit = m.get("unit", "")

                meas_node = f"{sample_id}_M{idx}"
                label = f"{quantity}\n{value} {unit}"

                dot.node(meas_node, label)
                dot.edge(sample_id, meas_node)

    # -------------------------
    # Render
    # -------------------------
    output_path = json_path.parent / "kb_visualization"
    dot.render(str(output_path), format="png", cleanup=True)

    print("Saved visualization to:", output_path.with_suffix(".png"))


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":
    visualize_kb(JSON_PATH)