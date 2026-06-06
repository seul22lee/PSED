"""
10_match.py
-----------
08_normalize 결과를 읽어서 experiment 간 유사도를 계산하고
matches.json 을 OUTPUT_DIR 루트에 저장한다.

매칭 전략:
  1차 필터 (hard): material 동일
  2차 필터 (hard): dependent variable canonical_name 겹치는 것 존재
  3차 스코어링:
    - indep_score  : independent variable canonical_name 일치 여부 (0 or 1)
    - ctrl_score   : controlled variable 공통 키의 값 유사도 평균 (0~1)
    - total_score  = 0.6 * indep_score + 0.4 * ctrl_score
"""

import json
from itertools import combinations
from pathlib import Path

from config import OUTPUT_DIR

OUT_PATH = OUTPUT_DIR / "matches.json"

INDEP_WEIGHT = 0.6
CTRL_WEIGHT  = 0.4


# ─────────────────────────────────────────
# 로드
# ─────────────────────────────────────────
def load_experiments(output_dir: Path) -> list[dict]:
    exps = []
    for paper_dir in sorted(output_dir.iterdir()):
        norm_dir = paper_dir / "08_normalize"
        if not norm_dir.exists():
            continue
        for f in sorted(norm_dir.glob("experiment-*.json")):
            raw = json.load(open(f, encoding="utf-8"))
            n   = raw.get("normalized", {})
            if not n.get("material"):
                continue  # normalize 안 된 것 skip

            exps.append({
                "experiment_id":  raw["experiment_id"],
                "paper":          paper_dir.name,
                "figure_id":      raw["figure"]["figure_id"],
                "series_name":    raw["figure"].get("series_name", ""),
                "material":       n["material"],
                "structure_type": n["structure_type"],
                "is_model_result":n["is_model_result"],
                "indep": sorted([
                    v["canonical_name"]
                    for v in n.get("independent_variables", [])
                    if v["canonical_name"]
                ]),
                "dep": sorted([
                    v["canonical_name"] or v["original_name"]
                    for v in n.get("dependent_variables", [])
                    if (v.get("canonical_name") or v.get("original_name"))
                ]),
                "dep_orig": sorted([
                    v["original_name"]
                    for v in n.get("dependent_variables", [])
                    if v.get("original_name")
                ]),
                "flat": n.get("flat_params", {}),
                "file": str(f),
            })
    return exps


# ─────────────────────────────────────────
# 유사도 계산
# ─────────────────────────────────────────
def indep_similarity(a: dict, b: dict) -> float:
    """independent variable canonical_name set 이 동일하면 1.0"""
    sa, sb = set(a["indep"]), set(b["indep"])
    if not sa and not sb:
        return 0.0
    intersection = sa & sb
    union        = sa | sb
    return len(intersection) / len(union)  # Jaccard


def ctrl_similarity(a: dict, b: dict) -> tuple[float, dict]:
    """공통 controlled parameter 값 유사도 평균 (ratio = min/max)"""
    common = set(a["flat"]) & set(b["flat"])
    if not common:
        return 0.0, {}
    details = {}
    total   = 0.0
    for k in common:
        va, vb = a["flat"][k], b["flat"][k]
        if va is None or vb is None:
            continue
        mx = max(abs(va), abs(vb))
        if mx == 0:
            ratio = 1.0
        else:
            ratio = 1.0 - abs(va - vb) / mx
        details[k] = {"a": va, "b": vb, "ratio": round(ratio, 4)}
        total += ratio
    score = total / len(common) if common else 0.0
    return score, details


def dep_overlap(a, b):
    # canonical이 있으면 canonical, 없으면 original로 각각 set 구성
    def dep_set(e):
        s = set()
        for v_can, v_orig in zip(e["dep"], e["dep_orig"]):
            s.add(v_can if v_can else v_orig)
        return s
    return sorted(dep_set(a) & dep_set(b))

def compute_matches(exps: list[dict], min_score: float = 0.0) -> list[dict]:
    matches = []
    for a, b in combinations(exps, 2):
        # 1차: material
        if a["material"] != b["material"]:
            continue

        # 2차: dep overlap
        dep_ov = dep_overlap(a, b)
        if not dep_ov:
            continue

        # 스코어
        i_score           = indep_similarity(a, b)
        c_score, c_detail = ctrl_similarity(a, b)
        total             = INDEP_WEIGHT * i_score + CTRL_WEIGHT * c_score

        if total < min_score:
            continue

        matches.append({
            "pair_id":       f"{a['experiment_id']}___{b['experiment_id']}",
            "exp_a":         a["experiment_id"],
            "exp_b":         b["experiment_id"],
            "paper_a":       a["paper"],
            "paper_b":       b["paper"],
            "is_cross_paper": a["paper"] != b["paper"],
            "material":      a["material"],
            "dep_overlap":   dep_ov,
            "scores": {
                "indep_similarity": round(i_score, 4),
                "ctrl_similarity":  round(c_score, 4),
                "total":            round(total,   4),
            },
            "ctrl_details": c_detail,
        })

    matches.sort(key=lambda x: -x["scores"]["total"])
    return matches


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    exps = load_experiments(OUTPUT_DIR)
    print(f"[INFO] loaded {len(exps)} experiments from {OUTPUT_DIR}")

    matches = compute_matches(exps, min_score=0.0)

    cross  = [m for m in matches if m["is_cross_paper"]]
    print(f"[INFO] total pairs:       {len(matches)}")
    print(f"[INFO] cross-paper pairs: {len(cross)}")
    if matches:
        print(f"[INFO] top score:         {matches[0]['scores']['total']:.3f}  ({matches[0]['exp_a']} ↔ {matches[0]['exp_b']})")

    out = {
        "experiments": {e["experiment_id"]: e for e in exps},
        "matches":     matches,
        "summary": {
            "n_experiments":        len(exps),
            "n_pairs":              len(matches),
            "n_cross_paper_pairs":  len(cross),
            "papers":               sorted(set(e["paper"] for e in exps)),
        },
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[DONE] saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
