import re
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ==========================================================
# Environment Setup
# ==========================================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment.")

client = Groq(api_key=api_key)

MODEL_NAME = "llama-3.3-70b-versatile"

# ==========================================================
# Cleaning / Preprocessing
# ==========================================================

def clean_markdown(text: str):

    cleaned_lines = []

    for line in text.split("\n"):
        line_strip = line.strip()

        # Remove image placeholders
        if "<!--" in line_strip:
            continue

        # Remove figure captions
        if re.match(r"^FIG\.", line_strip):
            continue

        # Remove page numbers
        if re.match(r"^\d+\s*$", line_strip):
            continue

        # Remove DOI header lines
        if "doi.org" in line_strip.lower():
            continue

        # Remove emails (likely author info)
        if "@" in line_strip and "doi" not in line_strip.lower():
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def split_paragraphs(text: str):
    """
    Merge wrapped lines properly into paragraphs.
    """
    paragraphs = []
    current = []

    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
        else:
            current.append(line.strip())

    if current:
        paragraphs.append(" ".join(current).strip())

    return paragraphs


# ==========================================================
# Heading-based Split
# ==========================================================

SECTION_MAP = {
    "experiment": ["experiment", "experimental", "materials and methods", "methods"],
    "results": ["results"],
    "discussion": ["discussion"],
}

STOP_SECTIONS = ["references", "acknowledgment", "acknowledgements"]


def is_heading(line: str) -> bool:
    line_stripped = line.strip()

    if not line_stripped:
        return False

    if line_stripped.startswith("#"):
        return True

    if (
        len(line_stripped) < 60
        and line_stripped.upper() == line_stripped
        and any(c.isalpha() for c in line_stripped)
    ):
        return True

    return False

def classify_single_paragraph(paragraph: str) -> str:

    prompt = """
Classify this paragraph into exactly one of:

Background
Process
Characterization
Measurement
Interpretation
Other

Return only the category word.
Do not explain.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a scientific paper classifier."},
            {"role": "user", "content": prompt + "\n\n" + paragraph},
        ],
    )

    label = response.choices[0].message.content.strip()

    if label not in CATEGORIES:
        return "Other"

    return label


def classify_heading(line: str):
    line_lower = line.lower()

    for stop in STOP_SECTIONS:
        if stop in line_lower:
            return "stop"

    for section, keywords in SECTION_MAP.items():
        for keyword in keywords:
            if re.search(rf"\b{keyword}\b", line_lower):
                return section

    return None


def split_sections(markdown_text: str):
    lines = markdown_text.split("\n")
    section_positions = {}
    stop_position = None

    for i, line in enumerate(lines):
        if not is_heading(line):
            continue

        section_type = classify_heading(line)

        if section_type == "stop":
            stop_position = i
            break

        if section_type and section_type not in section_positions:
            section_positions[section_type] = i

    sorted_sections = sorted(section_positions.items(), key=lambda x: x[1])
    results = {}

    for idx, (section_name, start_line) in enumerate(sorted_sections):
        if idx + 1 < len(sorted_sections):
            end_line = sorted_sections[idx + 1][1]
        elif stop_position:
            end_line = stop_position
        else:
            end_line = len(lines)

        section_text = "\n".join(lines[start_line:end_line])
        results[section_name] = section_text

    return results


def is_section_split_sufficient(sections: dict) -> bool:
    return "results" in sections or "experiment" in sections


# ==========================================================
# Semantic Split (LLM)
# ==========================================================

CATEGORIES = [
    "Background",
    "Process",
    "Characterization",
    "Measurement",
    "Interpretation",
    "Other",
]


def extract_json_array(text: str):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


def classify_paragraphs_batch(paragraphs):

    prompt = """
You are classifying scientific paper paragraphs.

For each paragraph, return a number separated by commas.

0 = Background
1 = Process
2 = Characterization
3 = Measurement
4 = Interpretation
5 = Other

Return only numbers separated by commas.
Do NOT include explanation.
"""

    for i, p in enumerate(paragraphs):
        prompt += f"\n[{i}] {p}\n"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a scientific paper classifier."},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content.strip()

    # 숫자만 추출
    numbers = re.findall(r"\d+", raw_output)

    if len(numbers) != len(paragraphs):
        print("⚠️ Label count mismatch. Falling back to Other.")
        return ["Other"] * len(paragraphs)

    mapping = {
        "0": "Background",
        "1": "Process",
        "2": "Characterization",
        "3": "Measurement",
        "4": "Interpretation",
        "5": "Other",
    }

    return [mapping.get(n, "Other") for n in numbers]


def semantic_split(markdown_text: str):

    markdown_text = clean_markdown(markdown_text)
    paragraphs = split_paragraphs(markdown_text)

    if not paragraphs:
        return {}

    results = {}
    current_label = None
    current_block = []

    for para in paragraphs:

        label = classify_single_paragraph(para)

        if label != current_label:
            if current_label is not None:
                results.setdefault(current_label, []).append(
                    "\n\n".join(current_block)
                )
            current_label = label
            current_block = [para]
        else:
            current_block.append(para)

    if current_label is not None:
        results.setdefault(current_label, []).append(
            "\n\n".join(current_block)
        )

    return results


# ==========================================================
# Unified Split
# ==========================================================

def split_sections_with_fallback(markdown_text: str):

    heading_sections = split_sections(markdown_text)

    if is_section_split_sufficient(heading_sections):
        print("Using heading-based split.")
        return heading_sections

    print("Using LLM semantic split.")
    return semantic_split(markdown_text)


# ==========================================================
# Main
# ==========================================================

def process_paper(paper_dir: Path):

    md_path = paper_dir / "document.md"

    if not md_path.exists():
        print("document.md not found.")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    sections = split_sections_with_fallback(markdown_text)

    out_path = paper_dir / "sections.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    print(f"Sections extracted for {paper_dir.name}")


if __name__ == "__main__":

    base_dir = Path("extracted")

    for paper_dir in base_dir.iterdir():
        if paper_dir.is_dir():
            print(f"\nProcessing {paper_dir.name}")
            process_paper(paper_dir)