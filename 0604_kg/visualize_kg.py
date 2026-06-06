"""
visualize_kg.py
---------------
knowledge_graph.json 을 읽어 pyvis HTML 로 렌더링한다.
실행 후 output/kg.html 을 브라우저에서 열면 된다.

  pip install pyvis
  python visualize_kg.py
"""

import json
from pathlib import Path
from pyvis.network import Network

from config import OUTPUT_DIR

KG_PATH  = OUTPUT_DIR / "knowledge_graph.json"
OUT_HTML = OUTPUT_DIR / "kg.html"

# ─────────────────────────────────────────
# 노드/엣지 스타일
# ─────────────────────────────────────────
NODE_COLOR = {
    "experiment": "#378ADD",
    "paper":      "#639922",
    "material":   "#D85A30",
    "variable":   "#BA7517",
}
NODE_SHAPE = {
    "experiment": "dot",
    "paper":      "square",
    "material":   "diamond",
    "variable":   "triangle",
}
NODE_SIZE = {
    "experiment": 14,
    "paper":      24,
    "material":   20,
    "variable":   12,
}
EDGE_COLOR = {
    "similar_to":    "#E24B4A",
    "from_paper":    "#B4B2A9",
    "uses_material": "#D85A30",
    "has_indep":     "#378ADD",
    "has_ctrl":      "#BA7517",
    "has_dep":       "#639922",
}
EDGE_WIDTH = {
    "similar_to":    3,
    "from_paper":    1,
    "uses_material": 1,
    "has_indep":     1,
    "has_ctrl":      1,
    "has_dep":       1,
}


def node_label(node: dict) -> str:
    ntype = node.get("ntype", "")
    if ntype == "experiment":
        return node.get("series_name") or node["id"].split("::")[-1]
    if ntype == "paper":
        # 논문 이름 앞 20자
        name = node.get("name", node["id"].split("::")[-1])
        return name[:25] + "…" if len(name) > 25 else name
    return node.get("name") or node["id"].split("::")[-1]


def node_title(node: dict) -> str:
    """hover tooltip"""
    lines = [f"<b>{node.get('ntype','').upper()}</b>"]
    for k, v in node.items():
        if k in ("id", "ntype"): continue
        lines.append(f"{k}: {v}")
    return "<br>".join(lines)


def edge_title(edge: dict) -> str:
    lines = [f"<b>{edge.get('etype','')}</b>"]
    for k, v in edge.items():
        if k in ("source","target","etype"): continue
        lines.append(f"{k}: {v}")
    return "<br>".join(lines)


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    if not KG_PATH.exists():
        raise FileNotFoundError(f"먼저 11_kg.py 를 실행하세요: {KG_PATH}")

    data = json.load(open(KG_PATH, encoding="utf-8"))
    print(f"[INFO] nodes={len(data['nodes'])}, edges={len(data['edges'])}")

    net = Network(
        height="860px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#2C2C2A",
        notebook=False,
    )

    # 물리 엔진 설정 (노드가 겹치지 않게)
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 120,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "stabilization": { "iterations": 200 }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      },
      "edges": {
        "smooth": { "type": "dynamic" }
      }
    }
    """)

    # 노드 추가
    for node in data["nodes"]:
        ntype = node.get("ntype", "")
        net.add_node(
            node["id"],
            label = node_label(node),
            title = node_title(node),
            color = NODE_COLOR.get(ntype, "#888780"),
            shape = NODE_SHAPE.get(ntype, "dot"),
            size  = NODE_SIZE.get(ntype, 12),
        )

    # 엣지 추가
    for edge in data["edges"]:
        etype = edge.get("etype", "")
        width = EDGE_WIDTH.get(etype, 1)

        # similar_to: score 에 따라 굵기 조절
        if etype == "similar_to":
            score = float(edge.get("score", 0.5))
            width = max(1, int(score * 6))

        net.add_edge(
            edge["source"],
            edge["target"],
            title = edge_title(edge),
            color = EDGE_COLOR.get(etype, "#B4B2A9"),
            width = width,
            arrows= "to" if etype != "similar_to" else "",
            dashes= etype == "similar_to",
        )

    # 범례 HTML 주입
    legend_html = """
    <div style="position:fixed;top:16px;right:16px;background:#fff;border:1px solid #ddd;
                border-radius:8px;padding:12px 16px;font-family:sans-serif;font-size:12px;z-index:999">
      <div style="font-weight:600;margin-bottom:8px">node type</div>
      <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#378ADD;margin-right:6px"></span>experiment</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#639922;margin-right:6px"></span>paper</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#D85A30;transform:rotate(45deg);margin-right:6px"></span>material</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#BA7517;margin-right:6px"></span>variable</div>
      <div style="font-weight:600;margin-top:10px;margin-bottom:8px">edge type</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#E24B4A;margin-right:6px;vertical-align:middle"></span>similar_to</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#378ADD;margin-right:6px;vertical-align:middle"></span>has_indep</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#BA7517;margin-right:6px;vertical-align:middle"></span>has_ctrl</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#639922;margin-right:6px;vertical-align:middle"></span>has_dep</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#D85A30;margin-right:6px;vertical-align:middle"></span>uses_material</div>
      <div><span style="display:inline-block;width:20px;height:2px;background:#B4B2A9;margin-right:6px;vertical-align:middle"></span>from_paper</div>
    </div>
    """

    # HTML 저장 후 범례 주입
    net.save_graph(str(OUT_HTML))

    html = OUT_HTML.read_text(encoding="utf-8")
    html = html.replace("</body>", legend_html + "\n</body>")
    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"[DONE] → {OUT_HTML}")
    print(f"       브라우저에서 열어주세요: open {OUT_HTML}")


if __name__ == "__main__":
    main()
