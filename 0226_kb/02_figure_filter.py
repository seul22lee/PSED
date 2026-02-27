import os
import json
import base64
import shutil
import re
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from PIL import Image
from groq import Groq


# ==========================================
# Setup
# ==========================================

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

client = Groq(api_key=GROQ_API_KEY)


# ==========================================
# Caption 보강 로직
# ==========================================

def extract_caption_candidates(doc_json: Dict, picture_self_ref: str) -> str:
    """
    doc.texts에서 caption 후보를 수집
    - "Fig" / "Figure" 패턴 탐색
    - 그림 아래쪽 텍스트 proximity 기반 수집
    """

    texts = doc_json.get("texts", [])
    caption_candidates = []

    fig_pattern = re.compile(r"(fig\.?|figure)\s*\d+", re.IGNORECASE)

    for t in texts:
        text = t.get("text", "")
        if not text:
            continue

        if fig_pattern.search(text):
            caption_candidates.append(text)

    # fallback: caption label 있는 경우
    for t in texts:
        if t.get("label") == "CAPTION":
            caption_candidates.append(t.get("text", ""))

    return " ".join(caption_candidates[:3])  # 너무 길지 않게 제한


# ==========================================
# Vision LLM 호출
# ==========================================

def encode_image_base64(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ask_vision_llm(image_path: Path, caption_text: str) -> Dict[str, Any]:

    base64_image = encode_image_base64(image_path)

    prompt = f"""
You are analyzing an image extracted from a scientific research paper.

Determine if this image is a REAL scientific figure
(e.g., plot, graph, chart, microscopy image, schematic, data visualization)
OR a decorative element (logo, header, footer, page number, icon).

Caption context (may be partial):
{caption_text}

Focus on actual visual content:
- axes
- curves
- bar charts
- microscopy texture
- labeled panels (a), (b)
- data plots

Return ONLY valid JSON:
{{
  "is_scientific_figure": true or false,
  "confidence": 0.0-1.0,
  "reason": "short explanation"
}}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        temperature=0,
    )

    content = response.choices[0].message.content.strip()
    print("VISION RAW RESPONSE:")
    print(content)

    content = content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "is_scientific_figure": False,
            "confidence": 0.0,
            "reason": "Invalid JSON",
        }


# ==========================================
# Main Filtering
# ==========================================

def filter_figures(paper_dir: Path):

    figures_dir = paper_dir / "figures"
    figures_json_path = figures_dir / "figures.json"
    doc_json_path = paper_dir / "document.json"

    if not figures_json_path.exists():
        print("figures.json not found.")
        return

    if not doc_json_path.exists():
        print("document.json not found.")
        return

    with open(figures_json_path, "r", encoding="utf-8") as f:
        figures = json.load(f)

    with open(doc_json_path, "r", encoding="utf-8") as f:
        doc_json = json.load(f)

    filtered_dir = paper_dir / "filtered_figures"
    rejected_dir = paper_dir / "rejected_figures"

    filtered_dir.mkdir(exist_ok=True)
    rejected_dir.mkdir(exist_ok=True)

    kept_records = []

    for fig in figures:

        image_path = Path(fig.get("image_path", ""))
        if not image_path.exists():
            continue

        # Caption 보강
        enhanced_caption = extract_caption_candidates(
            doc_json,
            fig.get("self_ref", "")
        )

        # Vision LLM 판단
        llm_result = ask_vision_llm(image_path, enhanced_caption)

        is_valid = llm_result.get("is_scientific_figure", False)
        confidence = llm_result.get("confidence", 0.0)

        fig["enhanced_caption"] = enhanced_caption
        fig["vision_decision"] = llm_result

        if is_valid and confidence >= 0.5:
            print("KEEP:", image_path.name)
            shutil.copy(str(image_path), filtered_dir / image_path.name)
            kept_records.append(fig)
        else:
            print("REJECT:", image_path.name)
            shutil.copy(str(image_path), rejected_dir / image_path.name)

    with open(filtered_dir / "filtered_figures.json", "w", encoding="utf-8") as f:
        json.dump(kept_records, f, indent=2, ensure_ascii=False)

    print(f"\nFiltering complete. Kept {len(kept_records)} figures.")


# ==========================================
# CLI
# ==========================================

if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            filter_figures(paper_dir)