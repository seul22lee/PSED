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


def build_prompt(
    enriched_fig: Dict[str, Any],
    plot_json: Dict[str, Any],
    series_name: str,
    series_index: int,
    series_data: Dict[str, Any],
) -> str:
    meta = plot_json.get("metadata", {})

    payload = {
        "figure_id": enriched_fig.get("figure_id"),
        "figure_index": enriched_fig.get("figure_index"),
        "figure_no": enriched_fig.get("figure_no"),
        "title": enriched_fig.get("title"),
        "caption": enriched_fig.get("caption"),
        "page_nos": enriched_fig.get("page_nos", []),
        "series_name": series_name,
        "series_index": series_index,
        "all_series_in_figure": enriched_fig.get("series", []),
        "figure_contexts": enriched_fig.get("figure_contexts", []),
        "subfigure_contexts": enriched_fig.get("subfigure_contexts", {}),
        "plot_metadata": meta,
        "series_points": series_data.get("points", []),
    }

    return f"""
{EXPERIMENT_SCHEMA_PROMPT}

INPUT DATA
----------
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


def run_llm(prompt: str) -> Dict[str, Any]:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    return json.loads(clean_json(response.text))


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


def process_figure(enriched_path: Path, out_dir: Path, start_index: int) -> int:
    enriched_fig = load_json(enriched_path)
    plot_json = load_plot_data(enriched_fig)

    series_names = enriched_fig.get("series", [])
    if not series_names:
        series_names = [d.get("series", "") for d in plot_json.get("data", [])]

    count = start_index

    for series_index, series_name in enumerate(series_names):
        if not series_name:
            continue

        series_data = find_series_data(plot_json, series_name)
        if not series_data:
            print(f"[WARN] series data not found: {enriched_path.name} / {series_name}")
            continue

        experiment_id = f"experiment-{count:05d}"
        prompt = build_prompt(
            enriched_fig=enriched_fig,
            plot_json=plot_json,
            series_name=series_name,
            series_index=series_index,
            series_data=series_data,
        )

        try:
            exp = run_llm(prompt)
            exp = normalize_experiment(
                exp=exp,
                enriched_fig=enriched_fig,
                plot_json=plot_json,
                series_name=series_name,
                series_index=series_index,
                series_data=series_data,
                experiment_id=experiment_id,
            )

            fig_id = enriched_fig.get("figure_id", enriched_path.stem)
            fname = f"{experiment_id}_{fig_id}_{safe_name(series_name)}.json"
            save_json(exp, out_dir / fname)

            print(f"[OK] {experiment_id} | {fig_id} | {series_name}")
            count += 1
            time.sleep(1)

        except Exception as e:
            print(f"[FAIL] {enriched_path.name} / {series_name}: {e}")
            time.sleep(3)

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