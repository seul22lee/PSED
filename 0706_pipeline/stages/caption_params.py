"""
caption_params.py — deterministically extract FIGURE-LEVEL conditions from a figure
caption, so parameters shared by every curve (cycle count, temperature, the whole
"Parameter values used:" block) are captured completely and CONSISTENTLY, instead of
relying on per-curve LLM extraction.

Handles the OCR artifacts docling leaves in physics captions:
  '¼' -> '='   'l m'/'lm' -> 'µm'   '/C2' -> '×'   '/C0' -> '-' (superscript minus)

Returns [(quantity, value_SI, unit, of_reactant)] figure-level conditions. The caller
(s08) merges these into every experiment of the figure WITHOUT overriding a value the
curve already carries (the varied parameter wins).
"""
import re

OCR = [("¼", "="), ("/C214", "×"), ("/C2", "×"), ("/C0", "-"), ("⁄", "/")]

# symbol (spaces removed, lowercased) -> (quantity, of_reactant label A/B/C/D or None).
# Reactant labels are generic letters so the model extends to ternary / supercycle
# chemistries (ABC, ABAC, nanolaminates), not just binary A+B.
SYM = {
    "h": ("feature_height", None), "w": ("feature_width", None),
    "pa0": ("reactant_A_partial_pressure", None), "pa": ("reactant_A_partial_pressure", None),
    "pb0": ("reactant_B_partial_pressure", None), "pb": ("reactant_B_partial_pressure", None),
    "ma": ("molecular_mass", "A"), "mb": ("molecular_mass", "B"),
    "mc": ("molecular_mass", "C"), "md": ("molecular_mass", "D"),
    "da": ("precursor_molecular_diameter", "A"), "db": ("precursor_molecular_diameter", "B"),
    "dc": ("precursor_molecular_diameter", "C"), "dd": ("precursor_molecular_diameter", "D"),
    "q": ("site_density", None), "t": ("temperature", None),
    "k": ("adsorption_rate_constant", None), "c": ("reaction_probability", None),
    "gpcsat": ("growth_per_cycle", None), "gpc": ("growth_per_cycle", None),
    # pulse / purge are per-reactant process variables (tp = precursor pulse, tpA/tpB…)
    "tp": ("pulse_time", None), "tpa": ("pulse_time", "A"), "tpb": ("pulse_time", "B"),
    "tpc": ("pulse_time", "C"), "tpd": ("pulse_time", "D"),
    "tpurge": ("purge_time", None), "tpurgea": ("purge_time", "A"), "tpurgeb": ("purge_time", "B"),
    "t0": ("purge_time", None), "t0a": ("purge_time", "A"), "t0b": ("purge_time", "B"),
}
# quantities that are reactant-resolved (may carry an of_reactant label)
REACTANT_QUANTITIES = {"molecular_mass", "precursor_molecular_diameter", "pulse_time",
                       "purge_time", "partial_pressure", "exposure"}


def normalize(text):
    t = text
    for a, b in OCR:
        t = t.replace(a, b)
    t = re.sub(r"\bl\s*m\b", "µm", t)          # 'l m' / 'lm' -> µm (OCR of µm)
    t = re.sub(r"\s*×\s*10\s*(-?\d+)", r"e\1", t)   # '5 × 10 18' -> '5e18'
    return t


def _value(s):
    m = re.search(r"-?\d+\.?\d*(?:e-?\d+)?", s.replace(" ", ""))
    return float(m.group(0)) if m else None


def _to_si(qty, val, unit):
    """Convert caption value+unit to the KB's stored SI-ish convention."""
    u = unit.lower().replace(" ", "")
    if val is None:
        return None, ""
    if qty in ("feature_height", "feature_width", "precursor_molecular_diameter"):
        if u.startswith("pm"): return val * 1e-3, "nm"          # 591 pm -> 0.591 nm
        if u.startswith("µm") or u.startswith("um"): return val * 1e3, "nm"
        if u.startswith("mm"): return val * 1e6, "nm"
        if u.startswith("nm"): return val, "nm"
        return val, "nm"
    if qty == "molecular_mass":
        return (val * 1e3, "g/mol") if "kg" in u else (val, "g/mol")   # kg/mol -> g/mol
    if qty in ("reactant_A_partial_pressure", "reactant_B_partial_pressure"):
        return val, "Pa"
    if qty == "temperature":
        return (val - 273.15, "°C") if u.startswith("k") else (val, "°C")
    if qty == "growth_per_cycle":
        return (val * 1e-3, "nm/cycle") if u.startswith("pm") else (val, "nm/cycle")
    if qty == "site_density":
        return val, "1/m²"
    if qty == "adsorption_rate_constant":
        return val, "1/Pa"
    if qty == "pulse_time" or qty == "purge_time":
        return val, "s"
    return val, unit.strip()


def parse(caption):
    if not caption:
        return []
    t = normalize(caption)
    out = []

    def add(qty, val, unit, react=None):
        v, u = _to_si(qty, val, unit)
        if v is not None:
            out.append((qty, v, u, react))

    m = re.search(r"after\s+(\d+)\s+cycles", t, re.I)          # 'after 1000 cycles'
    if m:
        add("cycle_number", float(m.group(1)), "cycles")
    m = re.search(r"pulse\s+length\s+t\s*p\s*([A-D])?\s*=\s*([\d.]+)\s*s", t, re.I)  # tp / tpA…
    if m:
        add("pulse_time", float(m.group(2)), "s", (m.group(1) or "").upper() or None)

    blk = re.split(r"parameter values used\s*:", t, flags=re.I)
    if len(blk) > 1:
        for part in re.split(r",|\band\b", blk[1]):
            m = re.match(r"\s*([A-Za-z][A-Za-z0-9 _]*?)\s*=\s*(-?[\d. ×e]+)\s*([^,]*)", part)
            if not m:
                continue
            sym = re.sub(r"[\s_]", "", m.group(1)).lower()
            spec = SYM.get(sym)
            if not spec:
                continue
            qty, react = spec
            add(qty, _value(m.group(2)), m.group(3), react)
    # dedup by (quantity, reactant) — keep first
    seen, uniq = set(), []
    for row in out:
        k = (row[0], row[3])
        if k not in seen:
            seen.add(k); uniq.append(row)
    return uniq


if __name__ == "__main__":       # quick self-test on the real ylilammi Fig. 4 caption
    cap = ('FIG. 4. Film thickness profiles after 1000 cycles calculated by the approximate '
           'model when the original channel heights are H ¼ 2, 1, 0.5, or 0.2 l m. Reactant '
           'pulse length t p ¼ 0.1 s. In the last case, the channel entrance is completely '
           'plugged up. Parameter values used: H ¼ 0.5 l m , W ¼ 0.1 mm, p A0 ¼ 100Pa, M A ¼ '
           '0.0749 kg/mol, d A ¼ 591pm, M B ¼ 0.028 kg/mol, d B ¼ 374pm, p B ¼ 300Pa, q ¼ 5 '
           '/C2 10 18 m /C0 2 , T ¼ 500K, K ¼ 100Pa /C0 1 , c ¼ 0.01, and gpc sat ¼ 106pm.')
    for row in parse(cap):
        print(f"  {row[0]:32} {row[1]:<12} {row[2]:8} {row[3] or ''}")
