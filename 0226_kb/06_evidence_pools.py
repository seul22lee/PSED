import json
from pathlib import Path

EXTRACTED_ROOT = Path("extracted")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_evidence_pool(paper_dir, tag_file, tag_key, output_file):

    segments = load_json(paper_dir / "segments.json")
    tags = load_json(paper_dir / tag_file)

    segment_map = {s["segment_id"]: s for s in segments}

    evidence = []

    for t in tags:

        if t.get(tag_key):

            sid = t["segment_id"]

            if sid in segment_map:

                evidence.append(segment_map[sid])

    save_json(
        {
            "paper": paper_dir.name,
            "segments": evidence
        },
        paper_dir / output_file
    )


def process_paper(paper_dir):

    print(f"\n[PROCESS] {paper_dir.name}")

    build_evidence_pool(
        paper_dir,
        "transport_tags.json",
        "transport_relevant",
        "transport_evidence.json"
    )

    build_evidence_pool(
        paper_dir,
        "reaction_tags.json",
        "reaction_relevant",
        "reaction_evidence.json"
    )

    build_evidence_pool(
        paper_dir,
        "geometry_tags.json",
        "geometry_relevant",
        "geometry_evidence.json"
    )


def main():

    for paper_dir in sorted(EXTRACTED_ROOT.glob("*")):

        if not paper_dir.is_dir():
            continue

        process_paper(paper_dir)


if __name__ == "__main__":
    main()