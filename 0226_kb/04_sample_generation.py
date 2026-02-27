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

MODEL = "llama-3.1-8b-instant"
MAX_CHARS = 12000


# ==========================================
# Safe JSON Extraction
# ==========================================

def safe_json_extract(text: str):

    text = text.strip()

    # Remove code fences
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end+1]

    return text


# ==========================================
# Load Relevant Text
# ==========================================

def load_relevant_text(paper_dir: Path):

    sections_path = paper_dir / "sections.json"
    document_path = paper_dir / "document.md"

    if sections_path.exists():
        sections = json.loads(sections_path.read_text())
        text = ""
        for key in ["experiment", "results"]:
            if key in sections:
                text += sections[key] + "\n\n"
        if text.strip():
            return text[:MAX_CHARS]

    if document_path.exists():
        return document_path.read_text(encoding="utf-8")[:MAX_CHARS]

    print("⚠️ No text source found.")
    return ""


# ==========================================
# Extract ProcessContext + Studies
# ==========================================

def extract_structure(text: str):

    if not text.strip():
        return fallback_structure()

    prompt = f"""
You are reconstructing the experimental design of a scientific paper.

Your task:

1. Extract fixed ProcessContext:
   - deposition method
   - precursor
   - plasma conditions
   - substrate temperature
   - substrate type
   - any constant fabrication parameters

2. Identify Studies.
   A Study = a set of experiments where fabrication variables were intentionally varied.

3. Do NOT create studies based on measurement type.

4. For each Study:
   - list varied fabrication variables
   - list sample conditions (fabrication or spatial only)
   - do NOT include measured results

5. If no variation exists, create one study with one empty sample.

Return STRICT JSON only:

{{
  "process_context": {{
    "deposition_method": "",
    "precursor": "",
    "plasma": "",
    "substrate_temperature_C": "",
    "substrate_type": "",
    "notes": ""
  }},
  "studies": [
    {{
      "study_id": "S1",
      "varied_variables": [],
      "description": "",
      "samples": [
        {{}}
      ]
    }}
  ]
}}

Text:
\"\"\"{text}\"\"\"
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt}
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        cleaned = safe_json_extract(content)
        return json.loads(cleaned)
    except Exception:
        print("⚠️ JSON parse failed.")
        print(content[:500])
        return fallback_structure()


# ==========================================
# Fallback Structure
# ==========================================

def fallback_structure():

    return {
        "process_context": {},
        "studies": [
            {
                "study_id": "S1",
                "varied_variables": [],
                "description": "Fallback single-condition study",
                "samples": [{}]
            }
        ]
    }


# ==========================================
# Deterministic Sample ID Assignment
# ==========================================

def assign_sample_ids(structure):

    for study in structure.get("studies", []):
        samples = study.get("samples", [])
        for i, sample in enumerate(samples):
            sample["sample_id"] = f"{study['study_id']}_{i+1}"
            sample["measurements"] = []  # prepare for next step

    return structure


# ==========================================
# Main
# ==========================================

def process_paper(paper_dir: Path):

    print("🔍 Loading relevant text...")
    text = load_relevant_text(paper_dir)

    print("🧠 Extracting experimental structure...")
    structure = extract_structure(text)

    structure = assign_sample_ids(structure)

    # Save unified file
    out_path = paper_dir / "structured_kb.json"

    out_path.write_text(
        json.dumps(structure, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"✅ structured_kb.json saved for {paper_dir.name}")


if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            process_paper(paper_dir)