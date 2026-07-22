import json
from pathlib import Path
from config import OUTPUT_DIR, STEP
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def build_evidence_pool(paper_stem, tag_file, tag_key, output_file):
    step04 = OUTPUT_DIR / paper_stem / STEP["04"]
    step05 = OUTPUT_DIR / paper_stem / STEP["05"]
    step06 = OUTPUT_DIR / paper_stem / STEP["06"]
    step06.mkdir(parents=True, exist_ok=True)
    segments = load_json(step04 / "segments.json")
    tags = load_json(step05 / tag_file)
    segment_map = {s["segment_id"]: s for s in segments}
    evidence = [segment_map[t["segment_id"]] for t in tags if t.get(tag_key) and t["segment_id"] in segment_map]
    save_json({"paper": paper_stem, "segments": evidence}, step06 / output_file)
def process_paper(paper_stem):
    print(f"\n[PROCESS] {paper_stem}")
    build_evidence_pool(paper_stem, "transport_tags.json", "transport_relevant", "transport_evidence.json")
    build_evidence_pool(paper_stem, "reaction_tags.json",  "reaction_relevant",  "reaction_evidence.json")
    build_evidence_pool(paper_stem, "geometry_tags.json",  "geometry_relevant",  "geometry_evidence.json")
def main():
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_paper(paper_dir.name)
if __name__ == "__main__":
    main()