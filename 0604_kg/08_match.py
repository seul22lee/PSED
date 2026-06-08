"""
08_match.py
-----------
07_normalize 결과를 읽어서 experiment 간 유사도를 계산하고
matches.json 을 OUTPUT_DIR 루트에 저장한다.

매칭 전략:
  1차 필터 (hard): material 동일
  2차 필터 (hard): dependent variable canonical_name 겹치는 것 존재
  3차 스코어링:
    - indep_score : independent variable canonical_name Jaccard
    - ctrl_score  : controlled parameter(flat_params) 유사도
        · 교집합이 아니라 "합집합(union)" 기준, 각 파라미터 weight 1 로 평균낸다.
        · 둘 다 관측: agree = value_sim(va, vb)
        · 한쪽만 관측: agree = expected_sim(obs, population)
            = 빠진 값이 같은 material 의 분포에서 뽑힌다고 본 '기대 일치도'.
              관측값이 흔하면 높고, 드물면 낮고, 분포가 퍼질수록 전반적으로 낮다.
              (별도 신뢰도 가중 없이 이 값 자체가 불확실성을 반영)
        · score    = Σ agree / N           (N = 합집합 개수)
        · coverage = (둘 다 관측된 개수) / N  → 직접 측정 비율(추정 의존도의 반대)
    - total_score = INDEP_WEIGHT * indep_score + CTRL_WEIGHT * ctrl_score

대칭성: ctrl_similarity 는 a/b 순서와 무관 → exp_a↔exp_b 일치도가 항상 같다.
"""

import json
import re
from itertools import combinations
from pathlib import Path

from config import OUTPUT_DIR

OUT_PATH = OUTPUT_DIR / "matches.json"

INDEP_WEIGHT = 0.0
CTRL_WEIGHT  = 1.0


# ─────────────────────────────────────────
# 종속변수 family (dep_overlap 게이트 완화용)
# ─────────────────────────────────────────
# "두께를 무언가로 나눈/정규화한" 계열은 모두 thickness 로 묶는다.
# y값이 정확히 같은 비교 대상은 아니지만, dep_overlap 게이트는 함께 통과시킨다.
# 맵에 없는 이름은 자기 자신이 곧 family.
DEP_FAMILY = {
    "film_thickness":       "thickness",
    "normalized_thickness": "thickness",   # thickness 를 정규화
    "thickness_per_cycle":  "thickness",   # thickness / cycles
    # penetration_depth, dimensionless_distance 등은 두께 계열이 아니므로 제외
}


def dep_family(name: str) -> str:
    return DEP_FAMILY.get(name, name)


# ─────────────────────────────────────────
# 로드
# ─────────────────────────────────────────

def short_paper_name(paper_dir_name: str) -> str:
    """Yim et al. - 2020 - ... → Yim 2020"""
    m = re.match(r"([A-Za-z]+).*?(\d{4})", paper_dir_name)
    return f"{m.group(1)} {m.group(2)}" if m else paper_dir_name[:15]


def load_experiments(output_dir: Path) -> list[dict]:
    exps = []
    for paper_dir in sorted(output_dir.iterdir()):
        norm_dir = paper_dir / "07_normalize"
        if not norm_dir.exists():
            continue
        for f in sorted(norm_dir.glob("experiment-*.json")):
            raw = json.load(open(f, encoding="utf-8"))
            n   = raw.get("normalized", {})
            if not n.get("material"):
                continue  # normalize 안 된 것 skip

            # dep_canonical: canonical이 있는 것만
            # dep_orig: original_name (항상)
            # dep_key: 매칭에 쓸 키 — canonical 있으면 canonical, 없으면 original
            dep_vars = n.get("dependent_variables", [])
            dep_canonical = sorted([
                v["canonical_name"]
                for v in dep_vars
                if v.get("canonical_name")
            ])
            dep_orig = sorted([
                v["original_name"]
                for v in dep_vars
                if v.get("original_name")
            ])
            dep_key = sorted([
                v["canonical_name"] if v.get("canonical_name") else v["original_name"]
                for v in dep_vars
                if v.get("canonical_name") or v.get("original_name")
            ])

            # experiment_id 가 figure 마다 다시 매겨질 수 있어,
            # paper+experiment_id 만으로는 uid 가 충돌한다. figure_id 를 포함해 유일하게.
            fig_id = raw["figure"]["figure_id"]
            uid = f"{paper_dir.name}__{fig_id}__{raw['experiment_id']}"
            exps.append({
                "experiment_id":  uid,
                "experiment_id_orig": raw["experiment_id"],
                "paper":          paper_dir.name,
                "paper_short":    short_paper_name(paper_dir.name),
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
                "dep":          dep_key,        # 매칭용 (canonical 우선)
                "dep_canonical":dep_canonical,  # canonical만
                "dep_orig":     dep_orig,       # original_name만
                "flat": n.get("flat_params", {}),
                "file": str(f),
            })
    return exps


# ─────────────────────────────────────────
# population 통계 (imputation 용)
# ─────────────────────────────────────────
def build_param_pop(exps: list[dict]) -> dict:
    """
    material 별 controlled parameter 의 관측값 분포를 모은다.
    (material, key) -> [values...]
    결측치 추정 시, 빠진 값이 이 분포에서 뽑힌다고 보고 기대 일치도를 계산한다.
    """
    pop = {}
    for e in exps:
        mat = e["material"]
        for k, v in e["flat"].items():
            if v is None:
                continue
            pop.setdefault((mat, k), []).append(v)
    return pop


# ─────────────────────────────────────────
# 유사도 계산
# ─────────────────────────────────────────
def value_sim(x: float, y: float) -> float:
    """두 스칼라 값의 유사도 0~1 (상대 차이 기반, 음수는 0으로 clamp)."""
    if x == y:
        return 1.0
    denom = max(abs(x), abs(y))
    if denom == 0:
        return 1.0
    return max(0.0, 1.0 - abs(x - y) / denom)


def expected_sim(obs: float, values: list) -> float:
    """
    결측치 기대 일치도: 빠진 값이 population 분포에서 뽑힌다고 보고,
    관측값 obs 와 분포 전체의 평균 유사도를 반환한다. (= E_v[value_sim(obs, v)])
    obs 가 흔한 값이면 높고, 드문 값이면 낮다. 분포가 퍼질수록 전반적으로 낮아진다.
    """
    if not values:
        return 0.0
    return sum(value_sim(obs, v) for v in values) / len(values)


def indep_similarity(a: dict, b: dict) -> float:
    """independent variable canonical_name set Jaccard."""
    sa, sb = set(a["indep"]), set(b["indep"])
    if not sa and not sb:
        return 0.0
    intersection = sa & sb
    union        = sa | sb
    return len(intersection) / len(union)


def ctrl_similarity(a: dict, b: dict, pop: dict):
    """
    합집합 기반 controlled parameter 유사도 + 결측치 imputation(E[sim]).

    각 합집합 파라미터마다 일치도 agree 를 구하고(weight 1), 평균낸다.
      - 둘 다 관측: agree = value_sim(va, vb)
      - 한쪽만 관측: agree = expected_sim(obs, population)
          → 빠진 값이 분포에서 뽑힌다고 본 '기대 일치도'.
            흔한 값이면 높고 드문 값이면 낮으며, 분포가 퍼지면 전반적으로 낮다.
            (별도 신뢰도 가중 없이 이 값 자체가 불확실성을 반영)
    score    = Σ agree / N         (N = 합집합 개수)
    coverage = (둘 다 관측된 개수) / N   → 직접 측정된 비율(추정 의존도의 반대)

    반환: (score, details, coverage)
      details : 파라미터별 {va, vb, ratio(=agree), kind}
    """
    mat  = a["material"]
    keys = set(a["flat"]) | set(b["flat"])
    if not keys:
        return 0.0, {}, 0.0

    total = 0.0
    n_obs = 0
    details = {}
    for k in keys:
        va, vb = a["flat"].get(k), b["flat"].get(k)

        if va is not None and vb is not None:
            agree, kind = value_sim(va, vb), "observed"
            n_obs += 1
        else:
            obs   = va if va is not None else vb
            agree = expected_sim(obs, pop.get((mat, k), []))
            kind  = "imputed"

        details[k] = {"va": va, "vb": vb, "ratio": round(agree, 4), "kind": kind}
        total += agree

    n        = len(keys)
    score    = total / n
    coverage = n_obs / n
    return score, details, coverage


def dep_overlap(a: dict, b: dict) -> list[str]:
    """
    dep 매칭 '게이트': family 단위로 비교한다.
    (normalized_thickness / film_thickness / thickness_per_cycle 처럼
     y값은 달라도 같은 계열이면 비교 후보로 함께 통과)
    canonical family 교집합이 있으면 그 family 들을 반환,
    없으면 original_name 교집합으로 fallback.
    """
    fam_a = {dep_family(x) for x in a["dep_canonical"]}
    fam_b = {dep_family(x) for x in b["dep_canonical"]}
    fam_overlap = fam_a & fam_b
    if fam_overlap:
        return sorted(fam_overlap)
    orig_overlap = set(a["dep_orig"]) & set(b["dep_orig"])
    return sorted(orig_overlap)


def compute_matches(exps: list[dict], min_score: float = 0.0) -> list[dict]:
    pop = build_param_pop(exps)

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
        i_score                     = indep_similarity(a, b)
        c_score, c_detail, coverage = ctrl_similarity(a, b, pop)
        total                       = INDEP_WEIGHT * i_score + CTRL_WEIGHT * c_score

        if total < min_score:
            continue

        matches.append({
            "pair_id":       f"{a['experiment_id']}___{b['experiment_id']}",
            "exp_a":         a["experiment_id"],
            "exp_b":         b["experiment_id"],
            "exp_a_orig":    a["experiment_id_orig"],
            "exp_b_orig":    b["experiment_id_orig"],
            "paper_a":       a["paper"],
            "paper_short_a": a["paper_short"],
            "paper_b":       b["paper"],
            "paper_short_b": b["paper_short"],
            "is_cross_paper": a["paper"] != b["paper"],
            "material":      a["material"],
            "dep_overlap":   dep_ov,            # 이제 family 라벨 (예: ["thickness"])
            "scores": {
                "indep_similarity": round(i_score, 4),
                "ctrl_similarity":  round(c_score, 4),
                "coverage":         round(coverage, 4),
                "uncertainty":      round(1 - coverage, 4),
                "total":            round(total, 4),
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

    cross = [m for m in matches if m["is_cross_paper"]]
    print(f"[INFO] total pairs:       {len(matches)}")
    print(f"[INFO] cross-paper pairs: {len(cross)}")
    if matches:
        top = matches[0]
        print(f"[INFO] top score:         {top['scores']['total']:.3f}  "
              f"(coverage {top['scores']['coverage']:.2f})  "
              f"({top['exp_a']} ↔ {top['exp_b']})")

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
