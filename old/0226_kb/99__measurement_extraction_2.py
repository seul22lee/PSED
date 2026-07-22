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
WINDOW_SIZE = 8
MAX_SENTENCES = 500


# ==========================================
# Sentence Split
# ==========================================

def split_sentences(text):
    sentences = []
    for part in text.replace("\n", " ").split("."):
        s = part.strip()
        if len(s) > 10:
            sentences.append(s + ".")
    return sentences[:MAX_SENTENCES]


def sliding_windows(sentences, size):
    for i in range(0, len(sentences), size):
        yield sentences[i:i+size]


# ==========================================
# Safe JSON extraction
# ==========================================

def safe_json(text):
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end+1]
    return text


# ==========================================
# Canonical Mapping
# ==========================================

def canonicalize(quantity_raw):

    q = quantity_raw.lower()

    if "critical temperature" in q or q == "tc":
        return "Tc"
    if "transition width" in q:
        return "delta_T"
    if "residual resistivity" in q:
        return "rho0"
    if "rrr" in q:
        return "RRR"
    if "roughness" in q:
        return "roughness"
    if "grain" in q:
        return "grain_size"
    if "density" in q:
        return "density"
    if "thickness" in q:
        return "thickness"
    if "growth rate" in q:
        return "growth_rate"

    return None


# ==========================================
# LLM Extraction (Window-level)
# ==========================================

def extract_from_window(window_text):

    prompt = f"""
Extract experimentally measured material or device properties.

DO NOT extract:
- publication dates
- journal info
- wafer size unless it is a measured variable
- wavelengths unless part of measurement result
- descriptive words (e.g., ultrathin, wafer-level)
- device names

Only extract:
- superconducting properties
- transport properties
- structural properties
- surface properties
- composition values
- thickness
- density
- growth rate
- roughness
- grain size

If uncertain, skip.

Return STRICT JSON:

{{
  "extractions": [
    {{
      "quantity_raw": "",
      "value": "",
      "unit": "",
      "sample_hint": ""
    }}
  ]
}}

Text:
\"\"\"{window_text}\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": prompt}
            ],
        )

        content = response.choices[0].message.content
        cleaned = safe_json(content)
        return json.loads(cleaned).get("extractions", [])

    except Exception as e:
        print("⚠️ LLM extraction failed:", e)
        return []


# ==========================================
# Main
# ==========================================

def process_paper(paper_dir: Path):

    print(f"\nProcessing {paper_dir.name}")

    kb_path = paper_dir / "structured_kb.json"
    doc_path = paper_dir / "document.md"

    if not kb_path.exists():
        print("No structured_kb.json found")
        return

    if not doc_path.exists():
        print("No document.md found")
        return

    kb = json.loads(kb_path.read_text())
    text = doc_path.read_text(encoding="utf-8")

    sentences = split_sentences(text)
    print(f"Total sentences used: {len(sentences)}")

    total_extractions = 0

    for window in sliding_windows(sentences, WINDOW_SIZE):

        window_text = " ".join(window)
        extractions = extract_from_window(window_text)

        for item in extractions:

            quantity_raw = item.get("quantity_raw", "")
            canonical = canonicalize(quantity_raw)

            measurement = {
                "quantity_raw": quantity_raw,
                "quantity": canonical,
                "value": item.get("value"),
                "unit": item.get("unit"),
                "sample_hint": item.get("sample_hint")
            }

            # Store at study level if no clear sample match yet
            if "global_measurements" not in kb:
                kb["global_measurements"] = []

            kb["global_measurements"].append(measurement)
            total_extractions += 1

    print(f"Total extracted measurements: {total_extractions}")

    kb_path.write_text(json.dumps(kb, indent=2, ensure_ascii=False))
    print("Saved updated KB.")


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            process_paper(paper_dir)