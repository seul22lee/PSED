#!/usr/bin/env python3
"""P59: the representation metrics, computed from the data by one command (also printed at the end of check.py).

    python3 psed_v2/pilot/metrics.py

(a) coverage per paper: elements covered, elements with no knowledge (with a reason), elements missed, and the sentence-only gaps
    (the items of statements that no structured field covers, allowed one by one in sentence_only_allow.csv; P55) with their count
    of facts;
(b) compactness: the token count (characters / 4, the convention of the tool budget) of a once-only serialization of the unique
    content (every fact's structured fields and statement once, tree rows once, every caveat text once, the curves' points once)
    against the source text of the three papers (ingest/final/<paper_id>/document.md, untracked);
(c) the absorption curve: the dispositions of the pilot's quantity ids in ontology/pilot_map.csv as counts, the first data point.
Tokens are approximate (characters / 4); the ratio is what matters and it is computed the same way on both sides.
"""
import collections, csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from elements import PAPERS  # noqa: E402

KEYS = {v: k for k, v in PAPERS.items()}


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def tokens(s):
    return len(s) / 4


def coverage():
    allow = rd(HERE / "sentence_only_allow.csv")
    gaps = collections.Counter(r["fact_id"].split(":")[0] for r in allow)
    gap_facts = collections.defaultdict(set)
    for r in allow:
        gap_facts[r["fact_id"].split(":")[0]].add(r["fact_id"])
    out = {}
    for pid, k in PAPERS.items():
        c = collections.Counter(r["status"] for r in rd(HERE / f"{pid}.coverage.csv"))
        out[k] = dict(covered=c.get("covered", 0), no_knowledge=c.get("no knowledge", 0), missed=c.get("missed", 0), total=sum(c.values()),
                      sentence_only_items=gaps.get(k, 0), sentence_only_facts=len(gap_facts.get(k, ())))
    return out


def compactness():
    """Tokens of the unique content, once, per paper, and of the source text."""
    out = {}
    for pid, k in PAPERS.items():
        seen, chars = set(), 0
        for r in rd(HERE / f"{pid}.facts.csv"):
            body = "|".join(r[c] for c in ("type", "kind", "quantity", "qualifiers", "label_as_printed", "value", "value_min", "value_max", "censor", "unit", "value_text",
                                              "uncertainty", "uncertainty_kind", "uncertainty_n", "data_kind", "method", "statement", "stance", "cause", "effect", "relation"))
            if body not in seen:                                                # a spread copy or a repeated line counts once
                seen.add(body); chars += len(body)
        pj = HERE / f"{pid}.points.json"
        if pj.exists():
            chars += sum(len(json.dumps(v.get("points", []))) for v in json.loads(pj.read_text(encoding="utf-8")).values())
        src = HERE.parent.parent / "ingest" / "final" / pid / "document.md"
        out[k] = dict(kb_tokens=round(chars / 4), source_tokens=round(tokens(src.read_text(encoding="utf-8")) if src.exists() else 0))
    out["user"] = dict(kb_tokens=round(sum(len("|".join(r.values())) for r in rd(HERE / "user.facts.csv")) / 4), source_tokens=0)
    return out


def absorption():
    rows = rd(HERE.parent.parent / "ontology" / "pilot_map.csv")
    c = collections.Counter(r["disposition"] for r in rows if r["kind"] == "quantity")
    return dict(c), len([r for r in rows if r["kind"] == "quantity"])


def report():
    cov = coverage(); comp = compactness(); absd, n = absorption()
    print("== metrics (P59)")
    for k, c in cov.items():
        print(f"   coverage {k}: {c['covered']}/{c['total']} elements covered, {c['no_knowledge']} no knowledge, {c['missed']} missed; "
              f"sentence-only gaps: {c['sentence_only_items']} items in {c['sentence_only_facts']} facts")
    kb = sum(v["kb_tokens"] for v in comp.values()); src = sum(v["source_tokens"] for v in comp.values())
    per = "; ".join(f"{k} {v['kb_tokens']:,} of {v['source_tokens']:,}" for k, v in comp.items() if k != "user")
    print(f"   compactness: unique content once {kb:,} tokens against {src:,} tokens of source text ({kb / src:.2f}) · {per} · user facts {comp['user']['kb_tokens']:,}"
          if src else f"   compactness: unique content once {kb:,} tokens; source text not on disk (ingest/final)")
    print(f"   absorption ({n} pilot quantity ids): " + ", ".join(f"{d} {c}" for d, c in sorted(absd.items(), key=lambda x: -x[1])))
    return dict(coverage=cov, compactness=comp, absorption=absd)


if __name__ == "__main__":
    report()
