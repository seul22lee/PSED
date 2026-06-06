import json
import re
from pathlib import Path
import spacy

# -----------------------------
# NLP
# -----------------------------
nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

# -----------------------------
# patterns
# -----------------------------
FORMULA_PLACEHOLDER = re.compile(
    r'<!--\s*formula-not-decoded\s*-->',
    re.IGNORECASE
)
GLYPH_PATTERN = re.compile(r'^/?C\d+$')
GARBAGE_PATTERN = re.compile(r'^[ðÐ]+$')
ABBREV_PATTERN = re.compile(
    r'(figs?|figure|eq|equation|ref|table|dr|et al)\.$',
    re.IGNORECASE
)
FIG_PATTERN = re.compile(
    r'(figs?|figure)\.$',
    re.IGNORECASE
)
FIG_NUMBER_PATTERN = re.compile(
    r'^\d+[,\.\)]?',
    re.IGNORECASE
)
EQ_PATTERN = re.compile(
    r'(eq|equation)\.?\s*\($',
    re.IGNORECASE
)
EQ_NUMBER_PATTERN = re.compile(
    r'^\d+\)',
    re.IGNORECASE
)

# -----------------------------
# cleaning
# -----------------------------

def clean_line(line):
    line = line.strip()
    if not line:
        return None
    if GLYPH_PATTERN.match(line):
        return None
    if GARBAGE_PATTERN.match(line):
        return None
    return line
# -----------------------------
# sentence split
# -----------------------------

def split_sentences(text):
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 2]
    sentences = merge_abbreviations(sentences)
    sentences = merge_figure_refs(sentences)
    sentences = merge_equation_refs(sentences)
    return sentences
# -----------------------------
# merge rules
# -----------------------------

def merge_abbreviations(sentences):
    merged = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        if i + 1 < len(sentences):
            nxt = sentences[i+1]
            if ABBREV_PATTERN.search(s):
                s = s + " " + nxt
                i += 1
        merged.append(s)
        i += 1
    return merged
def merge_figure_refs(sentences):
    merged = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        if i + 1 < len(sentences):
            nxt = sentences[i+1]
            if FIG_PATTERN.search(s) and FIG_NUMBER_PATTERN.match(nxt):
                s = s + " " + nxt
                i += 1
        merged.append(s)
        i += 1
    return merged
def merge_equation_refs(sentences):
    merged = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        if i + 1 < len(sentences):
            nxt = sentences[i+1]
            if EQ_PATTERN.search(s) and EQ_NUMBER_PATTERN.match(nxt):
                s = s + nxt
                i += 1
            elif re.search(r'(eq|equation)\.?$', s, re.IGNORECASE) and re.match(r'^\(\d+\)', nxt):
                s = s + " " + nxt
                i += 1
        merged.append(s)
        i += 1
    return merged
# -----------------------------
# markdown parsing
# -----------------------------

def parse_markdown(md_path):
    blocks = []
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # equation placeholder
            if FORMULA_PLACEHOLDER.search(line):
                blocks.append(
                    {
                        "type": "equation"
                    }
                )
                continue
            # glyph removal
            line = clean_line(line)
            if not line:
                continue
            blocks.append(
                {
                    "type": "text",
                    "text": line
                }
            )
    return blocks
# -----------------------------
# build segments
# -----------------------------

def build_segments(md_path, out_dir):
    blocks = parse_markdown(md_path)
    segments = []
    sid = 1
    eid = 1
    for block in blocks:
        if block["type"] == "text":
            sentences = split_sentences(block["text"])
            for s in sentences:
                segments.append(
                    {
                        "segment_id": f"S{sid:05d}",
                        "type": "sentence",
                        "text": s
                    }
                )
                sid += 1
        elif block["type"] == "equation":
            segments.append(
                {
                    "segment_id": f"E{eid:05d}",
                    "type": "equation"
                }
            )
            eid += 1
    out_path = out_dir / "segments.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, indent=2, ensure_ascii=False)
    print("segments:", len(segments))
# -----------------------------
# main
# -----------------------------

def main():
    from config import OUTPUT_DIR, STEP
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if not paper_dir.is_dir(): continue
        md_path = paper_dir / STEP["01"] / "document.md"
        if not md_path.exists(): continue
        print("processing:", paper_dir.name)
        out_dir = paper_dir / STEP["04"]
        out_dir.mkdir(parents=True, exist_ok=True)
        build_segments(md_path, out_dir)
if __name__ == "__main__":
    main()