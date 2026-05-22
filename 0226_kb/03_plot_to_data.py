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
# 2. Root 경로
# -----------------------------
ROOT_DIR = "/home/ftk3187/github/PSED/0226_kb/extracted"


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
def process_folder(pdf_folder):

    image_dir = os.path.join(pdf_folder, "filtered_figures")
    output_dir = os.path.join(pdf_folder, "extracted_data")

    os.makedirs(output_dir, exist_ok=True)

    image_files = glob.glob(os.path.join(image_dir, "*.png"))

    if not image_files:
        print(f"No images found in {image_dir}")
        return

    print(f"\nProcessing folder: {pdf_folder}")
    print(f"Found {len(image_files)} images")

    for img_path in image_files:

        file_name = os.path.basename(img_path)
        print(f"Processing: {file_name}")

        try:

            with open(img_path, "rb") as f:
                image_bytes = f.read()

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/png"
                    )
                ],
                config=config
            )

            result_text = response.text

            output_path = os.path.join(
                output_dir,
                f"{os.path.splitext(file_name)[0]}.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result_text)

            print(f"Saved: {output_path}")

            time.sleep(5)

        except Exception as e:
            print(f"Failed at {file_name}: {e}")
            time.sleep(10)


# -----------------------------
# 6. 전체 PDF 폴더 순회
# -----------------------------
def run_extraction():

    pdf_folders = [
        f for f in glob.glob(os.path.join(ROOT_DIR, "*"))
        if os.path.isdir(f)
    ]

    print(f"Found {len(pdf_folders)} PDF folders")

    for folder in pdf_folders:
        process_folder(folder)


# -----------------------------
# 7. 실행
# -----------------------------
if __name__ == "__main__":
    run_extraction()