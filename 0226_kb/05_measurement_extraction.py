import os
import json
import re
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
# Sentence Split
# ==========================================

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def make_blocks(sentences, window_size=4, stride=2):
    blocks = []
    for i in range(0, len(sentences), stride):
        block = " ".join(sentences[i:i+window_size])
        if block:
            blocks.append(block)
    return blocks


# ==========================================
# LLM Call
# ==========================================

def detect_measurement(block):

    prompt = f"""
Does the following text contain explicitly reported numerical physical measurements?

Text:
\"\"\"{block}\"\"\"

Answer only YES or NO.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return "YES" in response.choices[0].message.content.upper()


def extract_measurements(block, samples):

    prompt = f"""
You are extracting structured experimental measurements.

KNOWN SAMPLE CONDITIONS:
{json.dumps(samples, indent=2)}

Allowed variables:
Tc_K, delta_T_K, rho_uohm_cm, grain_size_nm,
RMS_roughness_nm, density_g_cm3,
oxygen_content_atpct, carbon_content_atpct,
growth_rate_A_per_cycle, inhomogeneity_percent,
peak_position_deg, FWHM_deg,
crystallite_size_nm, Jc, RRR

Extract only explicitly reported numerical values.
Return JSON list. If none, return [].

Text:
\"\"\"{block}\"\"\"
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except:
        return []


# ==========================================
# Main Extraction Loop
# ==========================================

def process_paper(paper_dir: Path):

    text_path = paper_dir / "document.md"
    samples_path = paper_dir / "samples.json"

    if not text_path.exists():
        print("No document.md")
        return

    if not samples_path.exists():
        print("No samples.json")
        return

    text = text_path.read_text(encoding="utf-8")
    samples = json.loads(samples_path.read_text())

    sentences = split_sentences(text)
    blocks = make_blocks(sentences)

    all_measurements = []

    for block in blocks:

        if not detect_measurement(block):
            continue

        extracted = extract_measurements(block, samples)

        if extracted:
            all_measurements.extend(extracted)

    out_path = paper_dir / "measurements.json"
    out_path.write_text(json.dumps(all_measurements, indent=2, ensure_ascii=False))

    print(f"Measurements extracted for {paper_dir.name}")


# ==========================================
# Run
# ==========================================

if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            process_paper(paper_dir)