import os
import json
import shutil
import re
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# Setup
# ==========================================

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env")
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# ==========================================
# Caption 보강 로직
# ==========================================

def extract_caption_candidates(doc_json: Dict, picture_self_ref: str) -> str:
    """
    1. picture의 page_no 파악
    2. 같은 page의 caption label 텍스트 반환
    3. 없으면 figure 번호 기준으로 순서 매칭
    """
    texts = doc_json.get("texts", [])
    pictures = doc_json.get("pictures", [])

    # self_ref로 picture 찾아서 page_no 파악
    # self_ref 형식: "#/pictures/8" → index 8
    m = re.match(r"#/pictures/(\d+)", picture_self_ref)
    if not m:
        return ""
    pic_idx = int(m.group(1))
    pic = pictures[pic_idx] if pic_idx < len(pictures) else None
    if not pic:
        return ""

    # picture의 page_no
    prov = pic.get("prov", [])
    pic_pages = set(p.get("page_no") for p in prov if p.get("page_no"))
    if not pic_pages:
        return ""

    # 같은 page의 caption label 텍스트 수집
    captions_on_page = []
    for t in texts:
        if t.get("label") not in ("caption", "CAPTION"):
            continue
        t_prov = t.get("prov", [])
        t_pages = set(p.get("page_no") for p in t_prov if p.get("page_no"))
        if pic_pages & t_pages:
            captions_on_page.append(t.get("text", ""))

    return " ".join(captions_on_page[:2])


def ask_vision_llm(image_path: Path, caption_text: str) -> Dict[str, Any]:
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
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
    )
    content = response.text.strip()
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

def filter_figures(paper_stem: str, output_dir: Path):
    step01 = output_dir / paper_stem / "01_docling"
    figures_json_path = step01 / "figures" / "figures.json"
    doc_json_path = step01 / "document.json"
    if not figures_json_path.exists():
        print("figures.json not found."); return
    if not doc_json_path.exists():
        print("document.json not found."); return
    with open(figures_json_path, "r", encoding="utf-8") as f:
        figures = json.load(f)
    with open(doc_json_path, "r", encoding="utf-8") as f:
        doc_json = json.load(f)
    step02 = output_dir / paper_stem / "02_figure_filter"
    filtered_dir, rejected_dir = step02 / "filtered", step02 / "rejected"
    filtered_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
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
        time.sleep(2)
        is_valid = llm_result.get("is_scientific_figure", False)
        confidence = llm_result.get("confidence", 0.0)
        fig["enhanced_caption"] = enhanced_caption
        # ↓ 추가: caption이 없으면 enhanced_caption으로 채움
        if not fig.get("caption") and enhanced_caption:
            fig["caption"] = enhanced_caption
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
    from config import OUTPUT_DIR
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            filter_figures(paper_dir.name, OUTPUT_DIR)