import json
import re
from pathlib import Path
import spacy

nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

FIG_PATTERN = re.compile(r'^(?:\d+|\(\d+\)|\d+[a-z]?)')

# sentence splitter
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

MERGE_ABBREVIATIONS = (
    "Fig.",
    "Figure.",
    "Eq.",
    "Ref.",
    "Table.",
    "Dr.",
    "et al."
)


def split_sentences(text):

    doc = nlp(text)

    raw = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 2]

    merged = []

    i = 0

    while i < len(raw):

        sent = raw[i]

        # If sentence ends with Fig. / Eq. etc
        if sent.endswith(MERGE_ABBREVIATIONS):

            if i + 1 < len(raw):

                sent = sent + " " + raw[i + 1]

                i += 1

        merged.append(sent)

        i += 1

    return merged


def extract_page_nos(item):

    pages = []

    prov = item.get("prov")

    if not prov:
        return pages

    for p in prov:

        page = p.get("page_no")

        if page is not None:
            pages.append(page)

    return sorted(list(set(pages)))


def build_segments(doc_json_path, out_dir):

    with open(doc_json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    texts = doc.get("texts", [])

    segments = []

    sid = 1

    for item in texts:

        layer = item.get("content_layer")

        # remove headers / footers
        if layer != "body":
            continue

        text = item.get("text", "").strip()

        if not text:
            continue

        page_nos = extract_page_nos(item)

        sentences = split_sentences(text)

        for s in sentences:

            segments.append(
                {
                    "segment_id": f"S{sid:05d}",
                    "type": "sentence",
                    "page_nos": page_nos,
                    "text": s
                }
            )

            sid += 1

    out_path = out_dir / "segments.json"

    with open(out_path, "w", encoding="utf-8") as f:

        json.dump(segments, f, indent=2, ensure_ascii=False)

    print("segments:", len(segments))


def main():

    extracted_root = Path("extracted")

    for paper_dir in extracted_root.glob("*"):

        if not paper_dir.is_dir():
            continue

        doc_json = paper_dir / "document.json"

        if not doc_json.exists():
            continue

        print("processing:", paper_dir.name)

        build_segments(doc_json, paper_dir)


if __name__ == "__main__":
    main()