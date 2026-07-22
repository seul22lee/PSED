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

EXTRACTED_ROOT = Path("extracted")

PROMPT_ROOT = Path("prompt_07")
SCHEMA_MD_ROOT = Path("schema/md")
SCHEMA_JSON_ROOT = Path("schema/json")

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

    evidence_files = list(EXTRACTED_ROOT.rglob("*_evidence.json"))

    if not evidence_files:
        print("No extracted evidence files found.")
        return

    for evidence_path in evidence_files:

        print(f"Processing {evidence_path}")

        evidence = load_json(evidence_path)

        evidence_text = evidence_to_text(evidence)

        evidence_name = evidence_path.name

        if "geometry" in evidence_name:

            prompt_guide = load_text(PROMPT_ROOT / "geometry_schema.md")

            schema_md = load_text(
                SCHEMA_MD_ROOT / "geometry_model_schema_with_links.md"
            )

            json_template = load_json(
                SCHEMA_JSON_ROOT / "geometry_model_schema_template_with_annotation.json"
            )

        elif "reaction" in evidence_name:

            prompt_guide = load_text(PROMPT_ROOT / "reaction_schema.md")

            schema_md = load_text(
                SCHEMA_MD_ROOT / "reaction_model_schema_with_links.md"
            )

            json_template = load_json(
                SCHEMA_JSON_ROOT / "reaction_model_schema_template_with_annotation.json"
            )

        elif "transport" in evidence_name:

            prompt_guide = load_text(PROMPT_ROOT / "transport_schema.md")

            schema_md = load_text(
                SCHEMA_MD_ROOT / "transport_model_schema_with_links.md"
            )

            json_template = load_json(
                SCHEMA_JSON_ROOT / "transport_model_schema_template_with_annotation.json"
            )

        else:
            raise ValueError(f"Unknown evidence type: {evidence_name}")

        prompt = build_prompt(
            prompt_guide,
            schema_md,
            json_template,
            evidence_text
        )

        result = run_llm(prompt)

        print("LLM OUTPUT ↓")
        print(result)
        print("-----")

        result_clean = clean_llm_json(result)

        try:
            result_json = json.loads(result_clean)
        except Exception:
            print("JSON parse failed")
            print(result_clean)
            continue

        output_path = evidence_path.with_name(
            evidence_path.stem.replace("_evidence", "_schema") + ".json"
        )

        print("Saving to:", output_path)
        save_json(result_json, output_path)

        print(f"Saved → {output_path}")

        time.sleep(1)

if __name__ == "__main__":
    main()