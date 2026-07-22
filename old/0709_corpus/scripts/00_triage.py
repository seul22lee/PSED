#!/usr/bin/env python3
"""
00_triage.py — Stage 0 of the efficient extraction framework (NO LLM).

Gate the ~967 candidate DOIs down to the relevant, extractable ALD papers BEFORE any
expensive stage, using free Crossref metadata + the ontology's controlled vocabulary.

  0a. metadata enrichment: Crossref GET works/{doi} → title + abstract + type + journal
      (only 244/967 references carry a title). Cached to refsets/metadata.jsonl (resumable).
  0b. relevance scoring: match title+abstract against ontology materials/precursors/
      coreactants (+aliases) and keyword sets → relevance_score, tier, predicted content.

Output: refsets/triage.csv  (doi, tier, relevance_score, chem_hits, has_* flags, title, journal)
Only tier in {high, med} should proceed to structure/extraction.

  python3 scripts/00_triage.py            # all merged DOIs (enrich + score)
  python3 scripts/00_triage.py --limit 40 # test
  python3 scripts/00_triage.py --score-only   # rescore from cache, no network
"""
import argparse, csv, json, os, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
REFSETS = ROOT / "refsets"
ONTO = json.loads((ROOT.parent / "0706_ontology" / "ald_ontology.json").read_text())
META = REFSETS / "metadata.jsonl"
SLEEP_S = 1.0

EMAIL = os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("CROSSREF_EMAIL")
if not EMAIL:
    cfg = ROOT / "config" / "email.txt"
    EMAIL = cfg.read_text().strip() if cfg.exists() else None
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"PSED-corpus/0.1 (mailto:{EMAIL or 'anon'})"})


# ---- ontology-derived vocabulary ----
def _terms(group, fields=("id", "full_name", "formula")):
    out = set()
    for it in ONTO["individuals"].get(group, []):
        for f in fields:
            v = it.get(f)
            if v and len(str(v)) > 1:
                out.add(str(v).lower())
        for a in it.get("aka") or []:
            if len(str(a)) > 1:
                out.add(str(a).lower())
    return out

MATERIALS = _terms("materials")
PRECURSORS = _terms("precursors")
COREACTANTS = _terms("coreactants")
CHEM = MATERIALS | PRECURSORS | COREACTANTS

ALD_CORE = ["atomic layer deposition", "atomic layer etching", " ald ", "ald,", "ald.",
            "self-limit", "self limit", "peald", "plasma-enhanced atomic", "plasma enhanced atomic"]
CONFORMALITY = ["conformal", "step coverage", "penetration depth", "aspect ratio", "high-aspect",
                "high aspect", "trench", "nanostructure", "pore", "lateral high", "3d structure"]
SATURATION = ["growth per cycle", "gpc", "growth rate", "saturation", "self-limiting growth",
              "dose", "exposure", "saturat"]
KINETICS = ["sticking", "reaction probability", "recombination probability", "nucleation",
            "reactivity", "kinetic"]
PROPERTIES = ["density", "refractive index", "resistivity", "impurity", "composition",
              "crystallin", "roughness", "stoichiometr", "band gap", "work function"]
PROCESS = ["temperature", "precursor", "coreactant", "co-reactant", "reactant", "pulse",
           "purge", "cycle", "plasma", "thermal", "reactor"]
NEG = ["review", "perspective", "roadmap", "tutorial", "overview"]

JATS = re.compile(r"<[^>]+>")


def _ws(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def clean_abstract(a):
    return _ws(JATS.sub(" ", a)) if a else ""


def fetch_meta(doi):
    try:
        r = SESSION.get(f"https://api.crossref.org/works/{doi}",
                        params={"mailto": EMAIL}, timeout=25)
        if r.status_code != 200:
            return {"doi": doi, "title": "", "abstract": "", "journal": "", "type": "",
                    "fetch": f"http_{r.status_code}"}
        m = r.json()["message"]
        return {"doi": doi,
                "title": (m.get("title") or [""])[0],
                "abstract": clean_abstract(m.get("abstract", "")),
                "journal": (m.get("container-title") or [""])[0],
                "type": m.get("type", ""), "fetch": "ok"}
    except requests.RequestException as e:
        return {"doi": doi, "title": "", "abstract": "", "journal": "", "type": "",
                "fetch": f"err_{type(e).__name__}"}


def load_cache():
    cache = {}
    if META.exists():
        for line in META.read_text().splitlines():
            if line.strip():
                d = json.loads(line); cache[d["doi"]] = d
    return cache


def count(text, terms):
    return sum(1 for t in terms if t in text)


def score(meta):
    text = f" {meta.get('title','')} {meta.get('abstract','')} ".lower()
    chem = count(text, CHEM)
    ald = count(text, ALD_CORE)
    conf = count(text, CONFORMALITY)
    sat = count(text, SATURATION)
    kin = count(text, KINETICS)
    prop = count(text, PROPERTIES)
    proc = count(text, PROCESS)
    neg = count(text, NEG)
    data_signal = conf + sat + kin + prop
    rel = 3 * min(ald, 2) + 2 * min(chem, 3) + 2 * min(data_signal, 4) + min(proc, 3) - 2 * min(neg, 1)
    # tiers
    if ald and chem and (data_signal or proc >= 2):
        tier = "high"
    elif ald and (chem or data_signal):
        tier = "med"
    elif ald or chem:
        tier = "low"
    else:
        tier = "reject"
    if neg and not (chem and data_signal):     # pure review/perspective → down-tier
        tier = "low" if tier in ("high", "med") else tier
    return {"relevance_score": rel, "tier": tier, "chem_hits": chem, "ald": ald,
            "has_conformality": int(bool(conf)), "has_saturation": int(bool(sat)),
            "has_kinetics": int(bool(kin)), "has_properties": int(bool(prop)),
            "has_process": int(proc >= 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--score-only", action="store_true", help="rescore from cache, no network")
    args = ap.parse_args()

    merged = REFSETS / "merged_refs.csv"
    if not merged.exists():
        sys.exit("run 01_refs_to_dois.py first")
    rows = list(csv.DictReader(merged.open()))
    if args.limit:
        rows = rows[:args.limit]
    cache = load_cache()

    # 0a enrichment
    if not args.score_only:
        if not EMAIL:
            sys.exit("set $UNPAYWALL_EMAIL for the Crossref polite pool")
        n_new = 0
        with META.open("a") as mf:
            for i, r in enumerate(rows, 1):
                doi = r["doi"].strip().lower()
                if not doi or doi in cache:
                    continue
                m = fetch_meta(doi)
                cache[doi] = m
                mf.write(json.dumps(m) + "\n"); mf.flush()
                n_new += 1
                time.sleep(SLEEP_S)
                if n_new % 25 == 0:
                    print(f"  enriched {n_new} new (…{i}/{len(rows)})")
        print(f"[0a] metadata: {len(cache)} cached ({n_new} newly fetched)")

    # 0b scoring
    out, tiers = [], {}
    for r in rows:
        doi = r["doi"].strip().lower()
        m = cache.get(doi, {"doi": doi, "title": "", "abstract": "", "journal": r.get("journal", "")})
        s = score(m)
        tiers[s["tier"]] = tiers.get(s["tier"], 0) + 1
        out.append({"doi": doi, "cited_by": r.get("cited_by", ""), **s,
                    "journal": _ws(m.get("journal") or r.get("journal", "")),
                    "title": _ws(m.get("title") or r.get("article_title", ""))[:140]})
    out.sort(key=lambda x: -x["relevance_score"])
    cols = ["doi", "tier", "relevance_score", "chem_hits", "ald", "has_conformality",
            "has_saturation", "has_kinetics", "has_properties", "has_process",
            "cited_by", "journal", "title"]
    with (REFSETS / "triage.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for x in out:
            w.writerow({k: x.get(k, "") for k in cols})
    proceed = tiers.get("high", 0) + tiers.get("med", 0)
    print(f"[0b] tiers: {tiers}  →  {proceed}/{len(out)} proceed (high+med). "
          f"reject/low gated out with 0 LLM tokens.")
    print(f"  → refsets/triage.csv")


if __name__ == "__main__":
    main()
