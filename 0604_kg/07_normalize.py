"""
08_normalize.py
---------------
experiment JSON에 "normalized" 섹션을 추가한다.
- 타입 통일 (string → float)
- 단위 통일 (길이: nm, 압력: Pa, 시간: s, 온도: °C)
- 변수명 → canonical_name (dictionary.json 활용)
- 재료명 / 구조 타입 통일
"""

import json
import copy
from pathlib import Path
from collections import defaultdict

from config import OUTPUT_DIR

DICT_PATH = Path(__file__).parent / "dictionary.json"

# ─────────────────────────────────────────
# 재료명 사전
# ─────────────────────────────────────────
MATERIAL_MAP = {
    "al2o3":          "Al2O3",
    "al₂o₃":          "Al2O3",
    "aluminum oxide": "Al2O3",
    "alumina":        "Al2O3",
    "tio2":           "TiO2",
    "tio₂":           "TiO2",
    "titanium dioxide":"TiO2",
    "titanium oxide": "TiO2",
    "hfo2":           "HfO2",
    "hfo₂":           "HfO2",
    "hafnium dioxide": "HfO2",
    "hafnium oxide":  "HfO2",
    "zno":            "ZnO",
    "zinc oxide":     "ZnO",
    "zro2":           "ZrO2",
    "zirconia":       "ZrO2",
    "sin":            "SiN",
    "silicon nitride":"SiN",
    "sio2":           "SiO2",
    "sio₂":           "SiO2",
    "silicon oxide":  "SiO2",
    "silicon dioxide":"SiO2",
    "sin_x":          "SiN",
}

# ─────────────────────────────────────────
# 구조 타입 사전
# ─────────────────────────────────────────
STRUCTURE_MAP = {
    "pillarhall":                "PillarHall",
    "pillar hall":               "PillarHall",
    "pillar-hall":               "PillarHall",
    "pillarhall channel":        "PillarHall",
    "lhar":                      "PillarHall",
    "lhar channel":              "PillarHall",
    "lhar channels":             "PillarHall",
    "rectangular lhar":          "PillarHall",
    "rectangular lhar channel":  "PillarHall",
    "rectangular lhar channels": "PillarHall",
    "lateral high aspect ratio": "PillarHall",
    "trench":                    "trench",
    "deep trench":               "trench",
    "hole":                      "hole",
    "via":                       "hole",
    "cylindrical hole":          "hole",
    "pore":                      "pore",
    "anodic aluminum oxide":     "AAO",
    "aao":                       "AAO",
    "nanotube":                  "nanotube",
}

# ─────────────────────────────────────────
# 단위 변환
# ─────────────────────────────────────────
LENGTH_TO_NM = {
    "nm": 1, "um": 1e3, "µm": 1e3, "μm": 1e3,
    "mm": 1e6, "cm": 1e7, "m": 1e9,
    "pm": 1e-3, "angstrom": 0.1, "å": 0.1,
}
PRESSURE_TO_PA = {
    "pa": 1, "kpa": 1e3, "mpa": 1e6, "hpa": 1e2,
    "bar": 1e5, "mbar": 1e2,
    "torr": 133.322, "mtorr": 0.133322, "atm": 101325,
}
TIME_TO_S = {
    "s": 1, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "min": 60, "h": 3600,
}
TEMP_CELSIUS = {"°c", "c", "celsius", "degc", "deg c"}
TEMP_KELVIN  = {"k", "kelvin"}


def _to_float(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _unit(unit):
    return str(unit).strip() if unit else ""


def convert_length(value, unit):
    v = _to_float(value)
    if v is None:
        return None, "nm"
    f = LENGTH_TO_NM.get(_unit(unit).lower())
    return (v * f, "nm") if f else (v, _unit(unit))


def convert_pressure(value, unit):
    v = _to_float(value)
    if v is None:
        return None, "Pa"
    f = PRESSURE_TO_PA.get(_unit(unit).lower())
    return (v * f, "Pa") if f else (v, _unit(unit))


def convert_time(value, unit):
    v = _to_float(value)
    if v is None:
        return None, "s"
    f = TIME_TO_S.get(_unit(unit).lower())
    return (v * f, "s") if f else (v, _unit(unit))


def convert_temperature(value, unit):
    v = _to_float(value)
    if v is None:
        return None, "°C"
    u = _unit(unit).lower()
    if u in TEMP_KELVIN:
        return v - 273.15, "°C"
    return v, "°C"


def convert_by_unit(value, unit):
    """단위 보고 자동으로 변환"""
    u = _unit(unit).lower()
    if u in LENGTH_TO_NM:
        return convert_length(value, unit)
    if u in PRESSURE_TO_PA:
        return convert_pressure(value, unit)
    if u in TIME_TO_S:
        return convert_time(value, unit)
    if u in TEMP_CELSIUS or u in TEMP_KELVIN:
        return convert_temperature(value, unit)
    return _to_float(value), unit


# ─────────────────────────────────────────
# dictionary 로드
# ─────────────────────────────────────────
def load_dictionary(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    alias_map  = defaultdict(set)  # alias  → set of canonicals
    symbol_map = defaultdict(set)  # symbol → set of canonicals

    for entry in entries:
        canonical = entry["canonical_name"]
        for alias in entry.get("aliases", []):
            alias_map[alias.lower()].add(canonical)
        for sym in entry.get("symbols", []):
            symbol_map[sym.lower()].add(canonical)

    return alias_map, symbol_map


def lookup_canonical(name, symbol, alias_map, symbol_map):
    """name 우선 exact match → symbol fallback. 충돌 시 가장 specific(긴) canonical 선택."""
    if name:
        hits = alias_map.get(str(name).lower().strip())
        if hits:
            return max(hits, key=len)
    if symbol:
        hits = symbol_map.get(str(symbol).lower().strip())
        if hits:
            return max(hits, key=len)
    return None


# ─────────────────────────────────────────
# 변수 리스트 정규화
# ─────────────────────────────────────────
def normalize_variable_list(var_list, alias_map, symbol_map):
    result = []
    for v in var_list:
        name   = v.get("name")
        symbol = v.get("symbol")
        value  = v.get("value")
        unit   = v.get("unit")

        canonical         = lookup_canonical(name, symbol, alias_map, symbol_map)
        norm_value, norm_unit = convert_by_unit(value, unit)

        result.append({
            "original_name": name,
            "canonical_name": canonical,
            "symbol":        symbol,
            "value":         norm_value,
            "unit":          norm_unit,
            "role":          v.get("role"),
        })
    return result


# ─────────────────────────────────────────
# 핵심 정규화
# ─────────────────────────────────────────
def normalize_experiment(exp: dict, alias_map, symbol_map) -> dict:
    n = {}

    # 재료
    raw_mat = (exp.get("process", {}).get("material_deposited") or "")
    n["material"] = MATERIAL_MAP.get(raw_mat.strip().lower(), raw_mat.strip() or None)

    # 구조 타입
    raw_struct = (exp.get("geometry", {}).get("structure_type") or "")
    n["structure_type"] = STRUCTURE_MAP.get(raw_struct.strip().lower(), raw_struct.strip() or None)

    # 모델 결과 여부 (null → 실험값으로 간주)
    is_model = exp.get("modeling", {}).get("is_model_result")
    n["is_model_result"] = False if is_model is None else bool(is_model)

    # 변수 정규화 (모든 variable에서 canonical_name + 단위 통일)
    variables = exp.get("variables", {})
    n["independent_variables"] = normalize_variable_list(
        variables.get("independent_variables", []), alias_map, symbol_map)
    n["controlled_variables"]  = normalize_variable_list(
        variables.get("controlled_variables", []),  alias_map, symbol_map)
    n["dependent_variables"]   = normalize_variable_list(
        variables.get("dependent_variables", []),   alias_map, symbol_map)

    # flat_params: canonical_name → value (matching용)
    flat = {}
    all_vars = n["independent_variables"] + n["controlled_variables"]
    for v in all_vars:
        cn = v["canonical_name"]
        if cn and v["value"] is not None:
            flat[cn] = v["value"]

    # geometry에서 직접 뽑아서 flat 보완 (변수 리스트에 없을 때 fallback)
    geom = exp.get("geometry", {})
    if "feature_height" not in flat:
        h, _ = convert_length(geom.get("H"), geom.get("H_unit"))
        if h is not None:
            flat["feature_height"] = h
    if "feature_length" not in flat:
        l, _ = convert_length(geom.get("L"), geom.get("L_unit"))
        if l is not None:
            flat["feature_length"] = l

    # process에서 직접 뽑아서 flat 보완
    proc = exp.get("process", {})
    if "cycle_number" not in flat:
        c = _to_float(proc.get("cycles"))
        if c is not None:
            flat["cycle_number"] = c
    if "temperature" not in flat:
        t, _ = convert_temperature(proc.get("temperature"), proc.get("temperature_unit"))
        if t is not None:
            flat["temperature"] = t
    if "growth_per_cycle" not in flat:
        g = _to_float(proc.get("gpc_sat"))
        if g is not None:
            flat["growth_per_cycle"] = g

    n["flat_params"] = flat

    return n


# ─────────────────────────────────────────
# 파일 처리
# ─────────────────────────────────────────
def process_paper(paper_dir: Path, alias_map, symbol_map):
    in_dir  = paper_dir / "06_experiment_schema"
    out_dir = paper_dir / "07_normalize"

    if not in_dir.exists():
        print(f"[SKIP] {paper_dir.name}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob("experiment-*.json"))
    for f in files:
        exp     = json.load(open(f, encoding="utf-8"))
        enriched = copy.deepcopy(exp)
        enriched["normalized"] = normalize_experiment(exp, alias_map, symbol_map)

        out_path = out_dir / f.name
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(enriched, fp, indent=2, ensure_ascii=False)

        print(f"[OK] {f.name}")

    print(f"[DONE] {paper_dir.name}: {len(files)} experiments normalized")


def main():
    alias_map, symbol_map = load_dictionary(DICT_PATH)
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_paper(paper_dir, alias_map, symbol_map)


if __name__ == "__main__":
    main()
