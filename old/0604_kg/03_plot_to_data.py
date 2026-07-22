import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# -----------------------------
# 1. 환경 변수 로드
# -----------------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env")
print(f"API Key loaded: {api_key[:4]}...{api_key[-4:]}")
client = genai.Client(api_key=api_key)

# -----------------------------
# 2. 모델 설정
# -----------------------------
MODEL_ID = "gemini-2.5-flash"

# -----------------------------
# 3. Prompt — 포인트 수 20개로 줄임
# -----------------------------
prompt = """
You are a scientific data extraction system.
Your task is to extract numerical data from a plotted scientific graph image.
IMPORTANT RULES:
- Do NOT guess or estimate values
- Do NOT smooth or interpolate
- Only extract values that can be visually confirmed from the plot
- If a value is unclear, skip it
- All extracted points must lie within the axis bounds
Follow these steps:
1. Identify metadata:
   - title
   - x-axis label
   - y-axis label
   - legend entries (each curve name)
2. Identify axis scales:
   - x-axis min and max
   - y-axis min and max
   - tick spacing
   - assume linear scale unless clearly logarithmic
3. Build coordinate mapping:
   - Convert pixel positions into actual axis values based on tick marks
4. Extract data points:
   - For each curve (legend entry)
   - Trace the curve visually
   - Extract approximately 40 evenly spaced points along the curve
   - Use only visible curve positions (no inference)
5. Output ONLY valid JSON in the following format:
{
  "metadata": {
    "title": "",
    "x_label": "",
    "y_label": "",
    "legend": []
  },
  "data": [
    {
      "series": "legend_name",
      "points": [[x,y],[x,y]]
    }
  ]
}
Do not include any explanations.
Only output JSON.
"""

config = types.GenerateContentConfig(
    temperature=0,
    response_mime_type="application/json"
)


# -----------------------------
# 4. JSON 복구 함수
# -----------------------------
def try_parse_json(text: str):
    """완전한 JSON 파싱 시도. 실패 시 잘린 JSON 복구 시도."""
    # 1차: 그대로 파싱
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2차: 마지막으로 완성된 series까지 복구
    # "points": [...] 가 닫힌 마지막 위치를 찾아서 거기까지만 파싱
    try:
        # 마지막 완전한 }] 패턴 찾기
        # data 배열의 마지막 완전한 series 항목까지 자르기
        last_complete = -1
        depth = 0
        in_data = False
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 1:  # data 배열 안에서 series 하나 닫힘
                    last_complete = i

        if last_complete > 0:
            # last_complete 위치까지 + ]}} 로 닫기
            truncated = text[:last_complete + 1].rstrip().rstrip(',')
            # metadata + data 구조 복구
            recovered = truncated + "\n  ]\n}"
            return json.loads(recovered)
    except Exception:
        pass

    # 3차: metadata만이라도 반환
    try:
        meta_end = text.find('"data"')
        if meta_end > 0:
            meta_part = text[:meta_end].rstrip().rstrip(',') + '}'
            meta = json.loads(meta_part)
            return {"metadata": meta.get("metadata", {}), "data": []}
    except Exception:
        pass

    return {"metadata": {}, "data": []}


# -----------------------------
# 5. 이미지 extraction
# -----------------------------
def process_folder(paper_stem: str, output_dir):
    image_dir = Path(output_dir) / paper_stem / "02_figure_filter" / "filtered"
    out_dir   = Path(output_dir) / paper_stem / "03_plot_to_data"
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(image_dir.glob("*.png"))
    if not image_files:
        print(f"No images found in {image_dir}"); return

    print(f"\nProcessing: {paper_stem} ({len(image_files)} images)")

    for img_path in image_files:
        print(f"Processing: {img_path.name}")
        try:
            with open(img_path, "rb") as f:
                image_bytes = f.read()

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
                config=config
            )

            raw_text = response.text

            # JSON 파싱 (잘린 경우 복구 시도)
            parsed = try_parse_json(raw_text)

            series_count = len(parsed.get("data", []))
            print(f"  → {series_count} series parsed")

            # 복구된 경우 경고 출력
            try:
                json.loads(raw_text)
            except json.JSONDecodeError:
                print(f"  ⚠ JSON was truncated, recovered {series_count} series")

            out_path = out_dir / f"{img_path.stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)

            print(f"  Saved: {out_path}")
            time.sleep(5)

        except Exception as e:
            print(f"Failed at {img_path.name}: {e}")
            time.sleep(10)


# -----------------------------
# 6. 실행
# -----------------------------
if __name__ == "__main__":
    from config import OUTPUT_DIR
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_folder(paper_dir.name, OUTPUT_DIR)