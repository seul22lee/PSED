import json
from pathlib import Path
from collections import defaultdict

def is_filled(value):
    if value is None: return False
    if isinstance(value, bool): return True
    if isinstance(value, str): return value.strip() != ""
    if isinstance(value, dict):
        if "evidence" in value:
            return value.get("evidence", "").strip() != ""
        return any(is_filled(v) for v in value.values())
    if isinstance(value, list): return len(value) > 0
    return True

def flatten_schema(obj, prefix=""):
    fields = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "annotation":
                fields[prefix + ".annotation"] = v; continue
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                fields.update(flatten_schema(v, new_prefix))
            else:
                fields[new_prefix] = v
    return fields

def analyze(schema_dirs: list):
    # { schema_type: { field_path: [paper_stem, ...] } }
    filled_by = defaultdict(lambda: defaultdict(list))
    all_fields = defaultdict(set)
    paper_stems = []

    for d in schema_dirs:
        d = Path(d)
        stem = d.parent.name
        paper_stems.append(stem)
        for stype in ["transport", "reaction", "geometry"]:
            f = d / f"{stype}_schema.json"
            if not f.exists(): continue
            root = next(iter(json.loads(f.read_text()).values()))
            for path, val in flatten_schema(root).items():
                all_fields[stype].add(path)
                if is_filled(val):
                    filled_by[stype][path].append(stem)
    return filled_by, all_fields, paper_stems

def print_report(filled_by, all_fields, paper_stems):
    n = len(paper_stems)
    print(f"\nPapers analyzed: {n}")
    for sname in paper_stems:
        print(f"  - {sname[:60]}")

    for stype in ["transport", "reaction", "geometry"]:
        fields = all_fields[stype]
        if not fields: continue
        print(f"\n{'='*65}")
        print(f"  {stype.upper()} SCHEMA  (n={n})")
        print(f"{'='*65}")

        # 채워진 비율 기준 정렬
        sorted_fields = sorted(
            fields,
            key=lambda p: -len(filled_by[stype].get(p, []))
        )
        always_filled, sometimes, never = [], [], []
        for path in sorted_fields:
            cnt = len(filled_by[stype].get(path, []))
            if cnt == n: always_filled.append((path, cnt))
            elif cnt == 0: never.append((path, cnt))
            else: sometimes.append((path, cnt))

        print(f"\n  ✅ Always filled ({len(always_filled)} fields)")
        for path, cnt in always_filled:
            print(f"     {path}")

        print(f"\n  ⚠️  Partially filled ({len(sometimes)} fields)")
        for path, cnt in sometimes:
            bar = "█"*cnt + "░"*(n-cnt)
            print(f"     {bar} {cnt}/{n}  {path}")

        print(f"\n  ❌ Never filled ({len(never)} fields)")
        for path, cnt in never:
            print(f"     {path}")

if __name__ == "__main__":
    from config import OUTPUT_DIR, STEP
    schema_dirs = [
        p / STEP["07"]
        for p in sorted(OUTPUT_DIR.iterdir())
        if p.is_dir() and (p / STEP["07"]).exists()
    ]
    if not schema_dirs:
        print("No schema dirs found. Check OUTPUT_DIR and STEP config.")
    else:
        filled_by, all_fields, paper_stems = analyze(schema_dirs)
        print_report(filled_by, all_fields, paper_stems)
