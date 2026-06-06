import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
# --------------------------------------------------
# Config
# --------------------------------------------------
from config import OUTPUT_DIR, STEP, PROMPTS_TAGGING_DIR
TRANSPORT_PROMPT_FILE = PROMPTS_TAGGING_DIR / "transport_tagging.md"
REACTION_PROMPT_FILE  = PROMPTS_TAGGING_DIR / "reaction_tagging.md"
GEOMETRY_PROMPT_FILE  = PROMPTS_TAGGING_DIR / "geometry_tagging.md"
MODEL_NAME = "gemini-2.5-flash"
CHUNK_SIZE = 40
SLEEP_BETWEEN_CALLS = 1.0
# --------------------------------------------------
# Env / Client
# --------------------------------------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env")
client = genai.Client(api_key=api_key)
# --------------------------------------------------
# Prompt loading
# --------------------------------------------------

def load_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
# --------------------------------------------------
# JSON cleaning / parsing
# --------------------------------------------------

def clean_json_text(text: str) -> str:
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return text
def safe_parse_json(text: str) -> Any:
    cleaned = clean_json_text(text)
    return json.loads(cleaned)
# --------------------------------------------------
# Chunking
# --------------------------------------------------

def chunk_segments(segments: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
    return [segments[i:i + chunk_size] for i in range(0, len(segments), chunk_size)]
def build_segment_block(chunk: List[Dict[str, Any]]) -> str:
    lines = []
    for seg in chunk:
        seg_id = seg.get("segment_id", "")
        seg_type = seg.get("type", "")
        seg_text = seg.get("text", "")
        # equation text가 없을 수도 있으므로 type을 함께 넣음
        # 나중에 equation text를 추가하면 그대로 반영 가능
        if seg_text:
            lines.append(f"[{seg_type.upper()}] {seg_id}: {seg_text}")
        else:
            lines.append(f"[{seg_type.upper()}] {seg_id}")
    return "\n".join(lines)
# --------------------------------------------------
# LLM call
# --------------------------------------------------

def call_gemini(prompt_text: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    if not hasattr(response, "text") or response.text is None:
        raise ValueError("Gemini response has no text content.")
    return response.text
# --------------------------------------------------
# Tagging
# --------------------------------------------------

def build_full_prompt(base_prompt: str, chunk: List[Dict[str, Any]]) -> str:
    segment_block = build_segment_block(chunk)
    full_prompt = f"""
{base_prompt}
Segments
{segment_block}
"""
    return full_prompt.strip()
def tag_chunk(base_prompt: str, chunk: List[Dict[str, Any]], tag_key: str) -> List[Dict[str, Any]]:
    prompt = build_full_prompt(base_prompt, chunk)
    raw_output = call_gemini(prompt)
    # print("\n========== PROMPT SENT ==========\n")
    # print(prompt[:2000])
    # print("\n=================================\n")
    print("\nRAW OUTPUT:\n")
    print(raw_output)
    print("\nEND RAW OUTPUT\n")
    parsed = safe_parse_json(raw_output)
    if isinstance(parsed, dict) and "results" in parsed:
        parsed = parsed["results"]
    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON list from model output. Got: {type(parsed)} / output={raw_output[:500]}")
    return [normalize_tag_record(x, tag_key) for x in parsed]
def normalize_tag_record(record: Dict[str, Any], tag_key: str) -> Dict[str, Any]:
    """
    모델 출력이 조금 흔들려도 최소한 맞춰줌.
    기대 형식:
      {"segment_id": "S00001", "transport_relevant": true}
    """
    segment_id = record.get("segment_id", "")
    if tag_key not in record:
        # 혹시 transport / reaction / geometry 같은 짧은 키로 주면 보정
        fallback_keys = [
            tag_key.replace("_relevant", ""),
            tag_key.split("_")[0],
        ]
        value = False
        for k in fallback_keys:
            if k in record:
                value = bool(record[k])
                break
    else:
        value = bool(record[tag_key])
    return {
        "segment_id": segment_id,
        tag_key: value
    }
def run_single_tagging_pass(
    paper_stem: str,
    prompt_path: Path,
    output_filename: str,
    tag_key: str
) -> None:
    segments_path = OUTPUT_DIR / paper_stem / STEP["04"] / "segments.json"
    if not segments_path.exists():
        print(f"[SKIP] segments.json not found: {segments_path}"); return
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    base_prompt = load_prompt(prompt_path)
    chunks = chunk_segments(segments, CHUNK_SIZE)
    all_results: List[Dict[str, Any]] = []
    print(f"  - {output_filename}: {len(chunks)} chunks")
    for idx, chunk in enumerate(chunks, start=1):
        print(f"    chunk {idx}/{len(chunks)}")
        try:
            tagged = tag_chunk(base_prompt, chunk, tag_key)
            all_results.extend(tagged)
        except Exception as e:
            print(f"    [ERROR] {paper_stem} / {output_filename} / chunk {idx}: {e}")
            for seg in chunk:
                all_results.append({"segment_id": seg.get("segment_id", ""), tag_key: False})
        time.sleep(SLEEP_BETWEEN_CALLS)
    out_dir = OUTPUT_DIR / paper_stem / STEP["05"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename
    out_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> saved: {out_path}")
# --------------------------------------------------
# Per-paper workflow
# --------------------------------------------------

def process_paper(paper_stem: str) -> None:
    print(f"\n[PROCESS] {paper_stem}")
    run_single_tagging_pass(paper_stem, TRANSPORT_PROMPT_FILE, "transport_tags.json", "transport_relevant")
    run_single_tagging_pass(paper_stem, REACTION_PROMPT_FILE,  "reaction_tags.json",  "reaction_relevant")
    run_single_tagging_pass(paper_stem, GEOMETRY_PROMPT_FILE,  "geometry_tags.json",  "geometry_relevant")
# --------------------------------------------------
# Main
# --------------------------------------------------

def main() -> None:
    for pf in [TRANSPORT_PROMPT_FILE, REACTION_PROMPT_FILE, GEOMETRY_PROMPT_FILE]:
        if not pf.exists(): raise FileNotFoundError(f"Missing prompt: {pf}")
    paper_stems = sorted([p.name for p in OUTPUT_DIR.iterdir() if p.is_dir()])
    if not paper_stems: raise FileNotFoundError(f"No paper directories in {OUTPUT_DIR}")
    for stem in paper_stems:
        process_paper(stem)
    print("\n[DONE] Step 05 tagging finished.")
if __name__ == "__main__":
    main()