import os
import json
from pathlib import Path
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
# --------------------------------
# Paths
# --------------------------------
from config import OUTPUT_DIR, STEP, PROMPTS_SCHEMA_DIR, SCHEMA_MD_DIR, SCHEMA_JSON_DIR
MODEL = "gemini-2.5-flash"
# --------------------------------
# API setup
# --------------------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env")
client = genai.Client(api_key=api_key)
# --------------------------------
# Utils
# --------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def clean_llm_json(text):
    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return text.strip()
# --------------------------------
# Evidence → prompt text
# --------------------------------

def evidence_to_text(evidence):
    lines = []
    for seg in evidence["segments"]:
        sid = seg["segment_id"]
        if "text" in seg:
            lines.append(f"{sid}: {seg['text']}")
        else:
            lines.append(f"{sid}: [EQUATION]")
    return "\n".join(lines)
# --------------------------------
# Prompt builder
# --------------------------------

def build_prompt(prompt_guide, schema_md, json_template, evidence_text):
    if isinstance(json_template, dict):
        json_template = json.dumps(json_template, indent=2, ensure_ascii=False)
    prompt = f"""
{prompt_guide}
------------------------------------------------
SCHEMA SPECIFICATION
------------------------------------------------
Use the following schema description as reference
when interpreting fields and canonical variables.
{schema_md}
------------------------------------------------
JSON TEMPLATE
------------------------------------------------
Fill the following JSON template.
Rules:
- Do NOT modify the structure
- Do NOT remove fields
- Only fill values supported by evidence
- Leave unknown fields empty
JSON TEMPLATE:
{json_template}
------------------------------------------------
EVIDENCE
------------------------------------------------
Use only the following evidence segments.
{evidence_text}
"""
    return prompt

# --------------------------------
# LLM call
# --------------------------------

def run_llm(prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0
        )
    )
    return response.text
# --------------------------------
# Main pipeline
# --------------------------------

def main():
    evidence_files = list((OUTPUT_DIR).rglob("*_evidence.json"))
    if not evidence_files:
        print("No evidence files found."); return
    for evidence_path in evidence_files:
        print(f"Processing {evidence_path}")
        evidence = load_json(evidence_path)
        evidence_text = evidence_to_text(evidence)
        name = evidence_path.name
        if "geometry" in name:
            prompt_guide = load_text(PROMPTS_SCHEMA_DIR / "geometry_schema.md")
            schema_md    = load_text(SCHEMA_MD_DIR   / "geometry_model_schema_with_links.md")
            json_template = load_json(SCHEMA_JSON_DIR / "geometry_model_schema_template_with_annotation.json")
        elif "reaction" in name:
            prompt_guide = load_text(PROMPTS_SCHEMA_DIR / "reaction_schema.md")
            schema_md    = load_text(SCHEMA_MD_DIR   / "reaction_model_schema_with_links.md")
            json_template = load_json(SCHEMA_JSON_DIR / "reaction_model_schema_template_with_annotation.json")
        elif "transport" in name:
            prompt_guide = load_text(PROMPTS_SCHEMA_DIR / "transport_schema.md")
            schema_md    = load_text(SCHEMA_MD_DIR   / "transport_model_schema_with_links.md")
            json_template = load_json(SCHEMA_JSON_DIR / "transport_model_schema_template_with_annotation.json")
        else:
            raise ValueError(f"Unknown evidence type: {name}")
        prompt = build_prompt(prompt_guide, schema_md, json_template, evidence_text)
        result = run_llm(prompt)
        print("LLM OUTPUT ↓"); print(result); print("-----")
        result_clean = clean_llm_json(result)
        try:
            result_json = json.loads(result_clean)
        except Exception:
            print("JSON parse failed"); print(result_clean); continue
        # 07_schema_extraction/ 폴더에 저장
        paper_stem = evidence_path.parts[-3]  # output/<stem>/06_evidence_pools/...
        out_dir = OUTPUT_DIR / paper_stem / STEP["07"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (evidence_path.stem.replace("_evidence", "_schema") + ".json")
        print("Saving to:", out_path)
        save_json(result_json, out_path)
        print(f"Saved → {out_path}")
        time.sleep(1)
if __name__ == "__main__":
    main()