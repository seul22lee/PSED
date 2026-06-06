import os
import glob
import time
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
# 3. 모델 설정
# -----------------------------
MODEL_ID = "gemini-2.5-flash"
# -----------------------------
# 4. Prompt
# -----------------------------
# prompt = """
# Extract all data points from this scientific plot.
# Return STRICT JSON format:
# {
#   "metadata": {
#     "title": "",
#     "x_label": "",
#     "y_label": "",
#     "legend": []
#   },
#   "data": [
#     {
#       "series": "legend_name",
#       "points": [[x,y],[x,y]]
#     }
#   ]
# }
# """
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
   - Extract approximately 50 evenly spaced points along the curve
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
# 5. 이미지 extraction
# -----------------------------
def process_folder(paper_stem: str, output_dir):
    from pathlib import Path
    image_dir = Path(output_dir) / paper_stem / "02_figure_filter" / "filtered"
    out_dir = Path(output_dir) / paper_stem / "03_plot_to_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    image_files = list(image_dir.glob("*.png"))
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
            out_path = out_dir / f"{img_path.stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Saved: {out_path}")
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

            
# -----------------------------
# Equation Prompt
# -----------------------------
equation_prompt="""
You are a scientific equation analysis system.

Analyze the equation image.

Rules:
- Extract variables exactly as written.
- Preserve subscripts.
- Ignore numbers and operators when listing variables.
- lhs contains variables being defined.
- rhs_symbols contains variables appearing on the right side.
- dependency_edges are [source,target].
- Do not guess.
- Return JSON only.

{
  "lhs":[{"symbol":"","original":""}],
  "rhs_symbols":[{"symbol":"","original":""}],
  "dependency_edges":[["",""]],
  "equation_type":""
}
"""

equation_config=types.GenerateContentConfig(
    temperature=0,
    response_mime_type="application/json"
)

# -----------------------------
# Equation Extraction
# -----------------------------
def process_equations(paper_stem:str,output_dir):
    from pathlib import Path
    import json,time

    image_dir=Path(output_dir)/paper_stem/"01_docling"/"formulas"
    out_dir=Path(output_dir)/paper_stem/"03_formula_to_data"
    out_dir.mkdir(parents=True,exist_ok=True)

    image_files=sorted(image_dir.glob("equation-*.png"))
    if not image_files:
        print(f"No equations found in {image_dir}")
        return

    results=[]

    print(f"\nProcessing equations: {paper_stem} ({len(image_files)})")

    for img_path in image_files:
        print(f"Processing: {img_path.name}")

        try:
            with open(img_path,"rb") as f:
                image_bytes=f.read()

            response=client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    equation_prompt,
                    types.Part.from_bytes(data=image_bytes,mime_type="image/png")
                ],
                config=equation_config
            )

            try:
                eq_json=json.loads(response.text)
            except Exception:
                eq_json={"raw_response":response.text}

            eq_json["equation_image"]=img_path.name
            results.append(eq_json)

            time.sleep(2)

        except Exception as e:
            print(f"Failed: {img_path.name}: {e}")
            time.sleep(5)

    out_path=out_dir/"equations.json"

    with open(out_path,"w",encoding="utf-8") as f:
        json.dump(results,f,ensure_ascii=False,indent=2)

    print(f"Saved: {out_path}")

# -----------------------------
# Equation Run
# -----------------------------
if __name__=="__main__":
    from config import OUTPUT_DIR

    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_equations(paper_dir.name,OUTPUT_DIR)