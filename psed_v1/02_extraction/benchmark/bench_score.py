"""
bench_score.py  (per-field, fair-matching)
-------------------------------------------
Score the scope benchmark with full-manuscript extraction as the silver
standard, reporting recall PER FIELD (materials, process, structures, precursors,
coreactants, dep_temp, quantitative, claims) so the per-stage picture is visible
rather than hidden in one aggregate.

Matching is made fair: materials/quantities via ontology canonicalisation,
process/structure/precursor/coreactant/claims via ontology aliases with a
token-overlap fallback (so 'oxygen (O) atoms' == 'O atoms').

No LLM calls — re-scores out/*.json. Usage: python bench_score.py [out_dir]
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
ONTO = json.loads((HERE.parent.parent / "01_ontology" / "ald_ontology.json").read_text())
NARROW = ["abstract", "abstract_conclusion", "evidence"]


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def toks(s):
    return set(re.findall(r"[a-z0-9]+", str(s).lower())) - {
        "the", "a", "an", "of", "and", "in", "for", "is", "to", "with", "on",
        "was", "were", "by", "at", "as", "or", "structures", "structure"}


def alias_index(groups):
    idx = {}
    for g in groups:
        for it in ONTO["individuals"].get(g, []):
            canon = it["id"]
            idx[norm(it["id"])] = canon
            for f in ("formula", "full_name"):
                if it.get(f):
                    idx[norm(it[f])] = canon
            for a in it.get("aka", []):
                idx.setdefault(norm(a), canon)
    return idx


MAT = alias_index(["materials"])
PROC = alias_index(["process_types"])
STRUCT = alias_index(["structures"])
PREC = alias_index(["precursors"])
CORE = alias_index(["coreactants"])
QIDX = {}
for q in ONTO["quantity_kinds"]:
    QIDX[norm(q["id"])] = q["id"]
    for a in q.get("aliases", []):
        QIDX.setdefault(norm(a), q["id"])


def canon(idx, s):
    return idx.get(norm(s))


# ---- per-field item extraction (canonicalised where possible) --------------
def fields(doc):
    p = doc.get("study_profile", {}) or {}
    out = {
        "material":   [(canon(MAT, v) or norm(v), v) for v in p.get("materials_deposited", []) or []],
        "process":    [(canon(PROC, v) or norm(v), v) for v in p.get("process_types", []) or []],
        "structure":  [(canon(STRUCT, v) or norm(v), v) for v in p.get("structures_or_apparatus", []) or []],
        "precursor":  [(canon(PREC, v) or norm(v), v) for v in p.get("precursors", []) or []],
        "coreactant": [(canon(CORE, v) or norm(v), v) for v in p.get("coreactants", []) or []],
    }
    t = p.get("deposition_temperature_C") or {}
    out["dep_temp"] = [("present", "T")] if (t.get("min") is not None or t.get("max") is not None) else []
    q = []
    for m in doc.get("quantitative_mentions", []) or []:
        try:
            q.append((QIDX.get(norm(m.get("quantity")), norm(m.get("quantity"))), round(float(m.get("value")), 4)))
        except (TypeError, ValueError):
            pass
    out["quantitative"] = q
    out["claims"] = [(None, c) for c in doc.get("claims", []) or []]
    return out


def match(field, a, b):
    if field == "quantitative":
        if a[0] != b[0]:
            return False
        return abs(a[1] - b[1]) <= 0.1 * max(abs(a[1]), abs(b[1]), 1e-9)
    if field in ("material", "process", "dep_temp"):
        return a[0] == b[0]  # canonical id equality
    # structure/precursor/coreactant/claims: canonical-equal OR token overlap
    if a[0] is not None and a[0] == b[0]:
        return True
    ta, tb = toks(a[1]), toks(b[1])
    return bool(ta) and bool(tb) and len(ta & tb) / len(ta | tb) >= 0.5


def recall(field, narrow, full):
    if not full:
        return None
    hit = sum(any(match(field, n, f) for n in narrow) for f in full)
    return hit / len(full)


FIELDS = ["material", "process", "structure", "precursor", "coreactant",
          "dep_temp", "quantitative", "claims"]


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
    index = json.loads((HERE / "slices" / "index.json").read_text())
    # scope -> field -> [per-paper recalls], and raw full-set sizes
    rec = {s: defaultdict(list) for s in NARROW}
    sizes = defaultdict(int)

    for r in index:
        pid = r["paper_id"]
        ff = out_dir / f"{pid}__full.json"
        if not ff.exists():
            continue
        full = fields(json.loads(ff.read_text()))
        for f in FIELDS:
            sizes[f] += len(full[f])
        for scope in NARROW:
            sf = out_dir / f"{pid}__{scope}.json"
            if not sf.exists():
                continue
            nar = fields(json.loads(sf.read_text()))
            for f in FIELDS:
                v = recall(f, nar[f], full[f])
                if v is not None:
                    rec[scope][f].append(v)

    def pct(v):
        return f"{100*v:3.0f}%" if v is not None else "  -"

    label = {"abstract": "abstract", "abstract_conclusion": "abs+concl",
             "evidence": "evidence"}
    print("PER-FIELD RECALL vs full-text silver standard  (mean across papers)\n")
    hdr = f"{'field':13}{'full items':>11}   " + "".join(f"{label.get(s,s):>11}" for s in NARROW)
    print(hdr)
    print("-" * len(hdr))
    macro = {s: [] for s in NARROW}
    for f in FIELDS:
        row = f"{f:13}{sizes[f]:>11}   "
        for scope in NARROW:
            vals = rec[scope][f]
            m = sum(vals) / len(vals) if vals else None
            if m is not None:
                macro[scope].append(m)
            row += f"{pct(m):>11}"
        print(row)
    print("-" * len(hdr))
    mrow = f"{'MEAN':13}{'':>11}   "
    for scope in NARROW:
        vals = macro[scope]
        mrow += f"{pct(sum(vals)/len(vals) if vals else None):>11}"
    print(mrow)
    print("\nNOTE: 'full items' is the silver-standard count; full-text extraction is")
    print("itself over-inclusive (instruments as 'structure', intro materials), so read")
    print("per-field DIRECTION, and prefer 'evidence' if it matches full at lower cost.")


if __name__ == "__main__":
    main()
