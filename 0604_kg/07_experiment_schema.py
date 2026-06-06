import os
import re
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import OUTPUT_DIR, STEP

MODEL = "gemini-2.5-flash"

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found")

client = genai.Client(api_key=api_key)


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clean_json(text: str) -> str:
    return text.replace("```json", "").replace("```", "").strip()


def safe_name(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w가-힣µ]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")[:80] or "series"


def load_plot_data(enriched_fig: Dict[str, Any]) -> Dict[str, Any]:
    plot_path = Path(enriched_fig["plot_data_path"])
    return load_json(plot_path)


def find_series_data(plot_json: Dict[str, Any], series_name: str) -> Optional[Dict[str, Any]]:
    for item in plot_json.get("data", []):
        if item.get("series", "").strip() == series_name.strip():
            return item
    return None


EXPERIMENT_SCHEMA_PROMPT = """
You are an information extraction system for scientific ALD papers.

Your task:
Create ONE experiment-level JSON object for ONE plotted data series.

Important definitions:
- A figure can contain multiple series.
- Each series corresponds to one experiment.
- The figure caption and related paragraphs may contain common conditions shared by all series.
- The current series name usually contains the variable value that distinguishes this experiment.
- Do NOT infer values that are not supported by evidence.
- Use null when unknown.
- Preserve units exactly when possible.
- Extract only information supported by caption, paragraph context, or series name.

Return ONLY valid JSON.

Required output schema:

{
  "experiment_type": null,

  "figure": {
    "figure_id": null,
    "figure_index": null,
    "figure_no": null,
    "title": null,
    "series_name": null,
    "series_index": null
  },

  "variables": {
    "independent_variables": [
      {
        "name": null,
        "symbol": null,
        "value": null,
        "unit": null,
        "role": "varied"
      }
    ],
    "controlled_variables": [
      {
        "name": null,
        "symbol": null,
        "value": null,
        "unit": null,
        "role": "controlled"
      }
    ],
    "dependent_variables": [
      {
        "name": null,
        "symbol": null,
        "unit": null,
        "role": "measured_or_calculated"
      }
    ]
  },

  "process": {
    "process_type": null,
    "material_deposited": null,
    "precursors": [
      {
        "name": null,
        "symbol": null,
        "partial_pressure": null,
        "partial_pressure_unit": null,
        "pulse_time": null,
        "pulse_time_unit": null,
        "molar_mass": null,
        "molar_mass_unit": null,
        "molecular_diameter": null,
        "molecular_diameter_unit": null
      }
    ],
    "reactant_sequence": null,
    "cycles": null,
    "temperature": null,
    "temperature_unit": null,
    "gpc_sat": null,
    "gpc_sat_unit": null
  },

  "geometry": {
    "structure_type": null,

    "H": null,
    "H_unit": null,
    "L": null,
    "L_unit": null,
    "W": null,
    "W_unit": null,
    "pillar_layout": null,
    "generation": null,

    "trench_width": null,
    "trench_width_unit": null,
    "trench_depth": null,
    "trench_depth_unit": null,

    "hole_diameter": null,
    "hole_diameter_unit": null,
    "hole_depth": null,
    "hole_depth_unit": null,
    "hole_shape": null,

    "pore_diameter": null,
    "pore_diameter_unit": null,
    "pore_length": null,
    "pore_length_unit": null,
    "porosity": null,

    "substrate_material": null
  },

  "modeling": {
    "is_model_result": null,
    "model_name": null,
    "adsorption_model": null,
    "diffusion_model": null,
    "reaction_assumption": null,
    "parameters": [
      {
        "name": null,
        "symbol": null,
        "value": null,
        "unit": null
      }
    ]
  },

  "data": {
    "x_label": null,
    "y_label": null,
    "points": []
  },

  "provenance": {
    "caption": null,
    "paragraphs": [],
    "evidence_notes": []
  }
}
"""


def build_prompt(enriched_fig,plot_json):

    payload={
        "figure_id":enriched_fig.get("figure_id"),
        "figure_index":enriched_fig.get("figure_index"),
        "figure_no":enriched_fig.get("figure_no"),
        "title":enriched_fig.get("title"),
        "caption":enriched_fig.get("caption"),
        "page_nos":enriched_fig.get("page_nos",[]),
        "figure_contexts":enriched_fig.get("figure_contexts",[]),
        "subfigure_contexts":enriched_fig.get("subfigure_contexts",{}),
        "plot_metadata":plot_json.get("metadata",{}),
        "series":plot_json.get("data",[])
    }

    return f"""
{EXPERIMENT_SCHEMA_PROMPT}

Create experiment objects for ALL series.

Return ONLY valid JSON:

{{
  "experiments":[]
}}

INPUT
-----
{json.dumps(payload,ensure_ascii=False,indent=2)}
"""


def run_llm(prompt,max_retry=5):
    for _ in range(max_retry):
        try:
            response=client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )
            return json.loads(clean_json(response.text))
        except Exception as e:
            msg=str(e)
            if "RESOURCE_EXHAUSTED" in msg:
                m=re.search(r"retry in (\d+)",msg,re.I)
                wait=int(m.group(1))+5 if m else 60
                print(f"[RATE LIMIT] sleep {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("max retry exceeded")


def normalize_experiment(
    exp: Dict[str, Any],
    enriched_fig: Dict[str, Any],
    plot_json: Dict[str, Any],
    series_name: str,
    series_index: int,
    series_data: Dict[str, Any],
    experiment_id: str,
) -> Dict[str, Any]:
    meta = plot_json.get("metadata", {})

    exp["experiment_id"] = experiment_id

    exp.setdefault("figure", {})
    exp["figure"].update(
        {
            "figure_id": enriched_fig.get("figure_id"),
            "figure_index": enriched_fig.get("figure_index"),
            "figure_no": enriched_fig.get("figure_no"),
            "title": enriched_fig.get("title"),
            "series_name": series_name,
            "series_index": series_index,
        }
    )

    exp.setdefault("data", {})
    exp["data"]["x_label"] = exp["data"].get("x_label") or meta.get("x_label")
    exp["data"]["y_label"] = exp["data"].get("y_label") or meta.get("y_label")
    exp["data"]["points"] = series_data.get("points", [])

    exp.setdefault("provenance", {})
    exp["provenance"]["caption"] = enriched_fig.get("caption")
    exp["provenance"]["paragraphs"] = enriched_fig.get("figure_contexts", [])
    exp["provenance"]["plot_data_path"] = enriched_fig.get("plot_data_path")
    exp["provenance"]["image_path"] = enriched_fig.get("image_path")
    exp["provenance"]["page_nos"] = enriched_fig.get("page_nos", [])

    return exp


def process_figure(enriched_path, out_dir, start_index):
    enriched_fig = load_json(enriched_path)
    plot_json = load_plot_data(enriched_fig)

    # 03_plot_to_data 결과가 멀티패널 list인 경우, panel 정보로 올바른 패널 선택
    if isinstance(plot_json, list):
        if not plot_json:
            return start_index
        panel = enriched_fig.get("panel")  # 06에서 "a","b"... 또는 None
        if panel:
            panel_i = ord(panel) - ord("a")
            plot_json = plot_json[panel_i] if panel_i < len(plot_json) else plot_json[0]
        else:
            plot_json = plot_json[0]

    # # ← 추가
    # if isinstance(plot_json, list):
    #     if not plot_json:
    #         return start_index
    #     plot_json = plot_json[0]

    count = start_index
    prompt = build_prompt(enriched_fig, plot_json)
    result=run_llm(prompt)
    experiments=result.get("experiments",[])

    for exp in experiments:
        exp_id=f"experiment-{count:05d}"
        exp["experiment_id"]=exp_id
        out_file=out_dir/f"{exp_id}.json"
        if out_file.exists():
            count+=1
            continue
        save_json(exp,out_file)
        print("[OK]",exp_id)
        count+=1

    return count


def process_paper(paper_dir: Path) -> None:
    enriched_dir = paper_dir / STEP["06"]
    out_dir = paper_dir / "07_experiment_schema"

    if not enriched_dir.exists():
        print(f"[SKIP] no enriched figures: {paper_dir.name}")
        return

    enriched_files = sorted(enriched_dir.glob("figure-*.json"))
    if not enriched_files:
        print(f"[SKIP] no figure json files: {paper_dir.name}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    count = 1
    for enriched_path in enriched_files:
        count = process_figure(enriched_path, out_dir, count)

    print(f"[DONE] {paper_dir.name}: {count - 1} experiments")


def main():
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_paper(paper_dir)


if __name__ == "__main__":
    main()