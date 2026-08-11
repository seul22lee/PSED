"""
ontology/vocab.py — the ontology's canonicalisation vocabulary.

Ported from the pre-psed_v1 `stages/lib.py`, which mixed three unrelated jobs:
this alias/canonicalisation table, a paper registry that indexed a historical
docling tree, and a Gemini client that loaded its key from outside the project.
Only the vocabulary is used by the live pipeline, so only the vocabulary is
kept; the two historical halves are gone with their paths.

Every canon_* function is byte-for-byte the original behaviour — the port is a
move, not a rewrite. `tests/unit/test_vocab_port.py` pins that equivalence.
"""
import paths as P
import json
import re
from pathlib import Path

ONTOLOGY_JSON = Path(__file__).resolve().parent / "ald_ontology.json"
ONTO = json.loads(ONTOLOGY_JSON.read_text())


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


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
