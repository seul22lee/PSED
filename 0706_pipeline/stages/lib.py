"""
stages/lib.py — shared helpers for the ontology-grounded extraction pipeline.
Paths, paper registry, ontology vocab/canonicalisation, and the Gemini client
(reused from 0604_kg: dotenv -> GOOGLE_API_KEY, gemini-2.5-flash).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent            # 0706_pipeline/
REPO = ROOT.parent                             # PSED/
KG0604 = REPO / "0604_kg" / "output"           # source docling/enrich outputs
BENCH = ROOT / "benchmark"                     # evidence slices + profiles
OUTPUT = ROOT / "output"                       # our stage outputs
ONTO = json.loads((REPO / "0706_ontology" / "ald_ontology.json").read_text())


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


# ---- paper registry (pid <-> full docling dir name) -----------------------
def paper_id(name):
    m = re.match(r"([A-Za-z]+) et al\. - (\d{4})", name)
    return f"{m.group(1)}{m.group(2)}".lower() if m else re.sub(r"\W+", "_", name)[:24].lower()


def papers():
    """Every paper processed through 05_enrich (dynamic — scales to new papers)."""
    out = []
    for d in sorted(KG0604.iterdir()):
        if d.is_dir() and (d / "05_enrich_figures").exists():
            out.append({"pid": paper_id(d.name), "dir": d.name})
    return out


def enrich_dir(paper_dir_name):
    return KG0604 / paper_dir_name / "05_enrich_figures"


def read_evidence(paper_dir_name):
    """Assemble the evidence region (abstract+conclusion+captions+figure/table
    contexts) for a paper, for the s06 study-profile extraction."""
    pdir = KG0604 / paper_dir_name
    parts, seen = [], set()

    def add(tag, txt):
        txt = str(txt).strip()
        if txt and txt not in seen:
            seen.add(txt); parts.append(f"{tag}{txt}" if tag else txt)

    sec = pdir / "01_docling" / "sections.json"
    if sec.exists():
        s = json.loads(sec.read_text())
        add("[ABSTRACT] ", s.get("abstract") or "")
        add("[CONCLUSION] ", s.get("conclusion") or "")
    ed = pdir / "05_enrich_figures"
    if ed.exists():
        for jf in sorted(ed.glob("figure-*.json")):
            j = json.loads(jf.read_text())
            add("[FIGURE CAPTION] ", j.get("caption") or "")
            for lbl in (j.get("x_label"), j.get("y_label")):
                add("[AXIS] ", lbl or "")
            for c in j.get("figure_contexts", []) or []:
                add("", c)
            sub = j.get("subfigure_contexts", [])
            for v in (sub.values() if isinstance(sub, dict) else sub) or []:
                add("", v if isinstance(v, str) else " ".join(map(str, v)))
    td = pdir / "01_docling" / "tables"
    if td.exists():
        for csv in sorted(td.glob("*.csv")):
            add("[TABLE]\n", csv.read_text()[:2000])
    return "\n\n".join(parts)


# ---- ontology canonicalisation indices ------------------------------------
def _alias_index(groups):
    idx = {}
    for g in groups:
        for it in ONTO["individuals"].get(g, []):
            idx[norm(it["id"])] = it["id"]
            for f in ("formula", "full_name"):
                if it.get(f):
                    idx.setdefault(norm(it[f]), it["id"])
            for a in it.get("aka", []):
                idx.setdefault(norm(a), it["id"])
    return idx


MAT = _alias_index(["materials"])
STRUCT = _alias_index(["structures"])
PREC = _alias_index(["precursors"])
CORE = _alias_index(["coreactants"])
PROC = _alias_index(["process_types"])
QK = {}                      # quantity alias -> canonical id
QK_META = {q["id"]: q for q in ONTO["quantity_kinds"]}
for q in ONTO["quantity_kinds"]:
    QK[norm(q["id"])] = q["id"]
    for a in q.get("aliases", []):
        QK.setdefault(norm(a), q["id"])
    for s in q.get("symbols", []):
        QK.setdefault(norm(s), q["id"])


def canon_material(s):    return MAT.get(norm(s))
def canon_structure(s):   return STRUCT.get(norm(s))
def canon_precursor(s):   return PREC.get(norm(s))
def canon_coreactant(s):  return CORE.get(norm(s))
def canon_process(s):     return PROC.get(norm(s))
def canon_quantity(s):    return QK.get(norm(s))
def axis_role(qid):       return (QK_META.get(qid) or {}).get("axis_role")

# ---- quantity families + transforms (comparability layer, P1) -------------
_QR = ONTO.get("quantity_relations", {}) or {}
FAMILIES = _QR.get("families", {}) or {}
TRANSFORMS = _QR.get("transforms", []) or []
FAMILY = {q["id"]: q.get("family") for q in ONTO["quantity_kinds"]}
def family(qid):          return FAMILY.get(qid)
RECIPE_ROLE = {q["id"]: q.get("recipe_role") for q in ONTO["quantity_kinds"]}
def recipe_role(qid):     return RECIPE_ROLE.get(qid)   # control_setting=in recipe

# species intrinsic properties (molar_mass, molecular_diameter, central_atoms)
SPECIES_PROP = {}
for _g in ("precursors", "coreactants"):
    for _it in ONTO["individuals"].get(_g, []):
        _p = {k: _it[k] for k in ("molar_mass", "molecular_diameter", "central_atoms") if k in _it}
        for _k in [_it["id"], _it.get("formula"), _it.get("full_name")] + (_it.get("aka") or []):
            if _k:
                SPECIES_PROP[str(_k)] = _p
def species_prop(sp, prop): return (SPECIES_PROP.get(str(sp)) or {}).get(prop) if sp else None


def resolve_axis_label(label):
    """Canonicalise a plot AXIS LABEL to a quantity id. Strips '(units)',
    ln/log wrappers and symbol subscripts, then tries the full label and
    progressively shorter prefixes against ontology aliases (so a trailing
    'x' / 'x̃' subscript doesn't block the match)."""
    if not label:
        return None
    s = str(label).lower()
    s = re.sub(r"\b(ln|log10|log)\b", " ", s)        # drop log wrappers (keyword)
    s = re.sub(r"[^a-z0-9 ]", " ", s)                # drop ALL symbols incl. parens (keep content)
    toks = [t for t in s.split() if t]
    cands = [label]
    for k in range(len(toks), 0, -1):                # full -> drop trailing tokens
        cands.append("_".join(toks[:k]))
        cands.append(" ".join(toks[:k]))
    for c in cands:
        qid = QK.get(norm(c))
        if qid:
            return qid
    return None


# ---- compact ontology vocab for prompts -----------------------------------
def vocab():
    mats = [m["formula"] for m in ONTO["individuals"]["materials"] if m.get("formula")]
    procs = [p["id"] for p in ONTO["classes"] if p.get("parent") == "ProcessType"]
    quant = [(q["id"], (q.get("aliases") or [])[:2], q.get("unit"))
             for q in ONTO["quantity_kinds"]]
    return mats, procs, quant


# ---- Gemini ---------------------------------------------------------------
def run_llm(prompt):
    import os
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    load_dotenv(REPO / "0604_kg" / ".env")
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    resp = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    return json.loads(resp.text.replace("```json", "").replace("```", "").strip())
