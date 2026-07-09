"""
methods_recipe.py — deterministically extract the RECIPE (per-reactant pulse/purge
times, ncycles, carrier gas + flow, chamber pressure) from a paper's methods text
(01_docling/document.md), which is where recipe timing lives (not in figures).

Systematic (regex over common phrasings), not per-experiment manual. Returns a
per-material recipe dict. An LLM pass would generalise further; this handles the
standard "X pulse and purge times were a and b s … repeated for N cycles" style.
"""
import re
from lib import KG0604

CARRIER = {"nitrogen": "N2", "n2": "N2", "argon": "Ar", "ar": "Ar"}


def _md(paper_dir):
    f = KG0604 / paper_dir / "01_docling" / "document.md"
    return f.read_text() if f.exists() else ""


def parse(paper_dir):
    md = _md(paper_dir)
    if not md:
        return {}
    out = {}

    def rec(mat):
        return out.setdefault(mat, {"pulse": {}, "purge": {}})

    # explicit precursor + coreactant pulse/purge:
    #   "For Al2O3 growth, the AlMe3 pulse and purge times were 0.1 and 4.0 s,
    #    respectively, followed by 0.1 and 4.0 s H2O pulse and purge"
    for m in re.finditer(
        r"[Ff]or\s+([A-Za-z0-9]+)\s+growth,.*?([A-Za-z0-9()]+)\s+pulse and purge times were\s+"
        r"([\d.]+)\s+and\s+([\d.]+)\s*s.*?followed by\s+([\d.]+)\s+and\s+([\d.]+)\s*s\s+"
        r"([A-Za-z0-9()]+)\s+pulse and purge", md, re.S):
        r = rec(m.group(1))
        r["precursor_name"], r["coreactant_name"] = m.group(2), m.group(7)
        r["pulse"]["A"], r["purge"]["A"] = float(m.group(3)), float(m.group(4))
        r["pulse"]["B"], r["purge"]["B"] = float(m.group(5)), float(m.group(6))

    # shared pulse/purge: "In the TiO2 growth, the reactant pulse and purge times were also 0.1 and 4.0 s"
    for m in re.finditer(
        r"[Ii]n the\s+([A-Za-z0-9]+)\s+(?:growth|deposition),\s+the reactant pulse and purge times were\s+"
        r"(?:also\s+)?([\d.]+)\s+and\s+([\d.]+)\s*s", md):
        r = rec(m.group(1))
        for lab in ("A", "B"):
            r["pulse"].setdefault(lab, float(m.group(2)))
            r["purge"].setdefault(lab, float(m.group(3)))

    # ncycles: "repeated for 500 cycles" -> nearest preceding "For X growth";
    #          "In the TiO2 deposition, the number of pulse sequences was 1000"
    for m in re.finditer(r"repeated for\s+(\d+)\s+cycles", md):
        pre = list(re.finditer(r"[Ff]or\s+([A-Za-z0-9]+)\s+growth", md[:m.start()]))
        if pre:
            rec(pre[-1].group(1))["ncycles"] = int(m.group(1))
    for m in re.finditer(r"[Ii]n the\s+([A-Za-z0-9]+)\s+deposition,\s+the number of pulse sequences was\s+(\d+)", md):
        rec(m.group(1))["ncycles"] = int(m.group(2))

    # carrier gas + flow, chamber pressure (global -> applied to all materials)
    cm = re.search(r"(Nitrogen|Argon|N2|Ar)\s+flow rates?\s+(?:were|was)\s+([\d.]+)\s*sccm", md, re.I)
    pm = re.search(r"[Cc]hamber pressures?\s+.*?([\d.]+)\s*Pa", md)
    carrier = CARRIER.get(cm.group(1).lower()) if cm else None
    flow = float(cm.group(2)) if cm else None
    press = float(pm.group(1)) if pm else None
    for mat, r in out.items():
        if carrier: r["carrier"], r["carrier_flow"] = carrier, flow
        if press: r["chamber_pressure"] = press
    return out


if __name__ == "__main__":
    import glob
    d = glob.glob(str(KG0604 / "Ylilammi*"))
    if d:
        r = parse(d[0].split("/output/")[1])
        import json
        print(json.dumps(r, indent=2))
