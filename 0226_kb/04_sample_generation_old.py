import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ==========================================
# Setup
# ==========================================

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 🔥 가벼운 모델 사용
MODEL = "llama-3.1-8b-instant"

# 🔥 토큰 폭발 방지
MAX_CHARS = 12000


# ==========================================
# Safe JSON Extraction
# ==========================================

def safe_json_extract(text):

    text = text.strip()

    # 코드블록 제거
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

    # JSON 배열 부분만 추출
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1:
        text = text[start:end+1]

    return text


# ==========================================
# Load Relevant Sections Only
# ==========================================

def load_relevant_text(paper_dir: Path):

    sections_path = paper_dir / "sections.json"

    if sections_path.exists():
        sections = json.loads(sections_path.read_text())
        text = ""
        for key in ["experiment", "results"]:
            if key in sections:
                text += sections[key] + "\n\n"
        if text.strip():
            return text[:MAX_CHARS]

    # fallback
    text = (paper_dir / "document.md").read_text(encoding="utf-8")
    return text[:MAX_CHARS]


# ==========================================
# Study + Condition Detection
# ==========================================

def detect_studies_and_conditions(text: str):

    prompt = f"""
You are analyzing experimental structure in a scientific paper.

IMPORTANT RULES:

- A condition must represent an intentionally controlled experimental setup.
- Only include fabrication or spatial variables (e.g., thickness, bias power, wafer position, substrate type).
- DO NOT include measured properties (e.g., roughness, resistivity, Tc, grain size, density).
- DO NOT include results.
- Conditions must reflect how the experiment was designed, not what was measured.

If a quantity varies because of position,
but position is the controlled factor,
then the condition should only include position.

If no intentional variation exists,
return one study with one empty condition.

Return STRICT JSON ONLY in this format:

[
  {{
    "study_id": "S1",
    "study_type": "comparative | mapping | single_condition",
    "description": "...",
    "varied_factor": "...",
    "conditions": [
      {{"thickness_nm": 7}},
      {{"thickness_nm": 40}}
    ]
  }}
]

Text:
\"\"\"{text}\"\"\"
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "You extract experimental study structures in strict JSON."},
            {"role": "user", "content": prompt}
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        cleaned = safe_json_extract(content)
        return json.loads(cleaned)
    except Exception:
        print("⚠️ JSON parse failed after cleanup.")
        print(content[:500])
        return []


# ==========================================
# Deterministic Sample Builder
# ==========================================

def build_samples(studies):

    all_samples = []

    if not studies:
        studies = [{
            "study_id": "S1",
            "study_type": "single_condition",
            "description": "Single condition fallback",
            "varied_factor": None,
            "conditions": [{}]
        }]

    for study in studies:

        conditions = study.get("conditions", [])

        if not conditions:
            conditions = [{}]

        for i, cond in enumerate(conditions):
            sample = {
                "sample_id": f"{study['study_id']}_{i+1}",
                "study_id": study["study_id"],
                "condition": cond
            }
            all_samples.append(sample)

    return all_samples


# ==========================================
# Main
# ==========================================

def process_paper(paper_dir: Path):

    print("🔍 Loading relevant sections...")
    text = load_relevant_text(paper_dir)

    print("🧠 Detecting studies and conditions...")
    studies = detect_studies_and_conditions(text)

    samples = build_samples(studies)

    # Save outputs
    (paper_dir / "studies.json").write_text(
        json.dumps(studies, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (paper_dir / "samples.json").write_text(
        json.dumps(samples, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"✅ Generated {len(samples)} samples for {paper_dir.name}")


if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            process_paper(paper_dir)