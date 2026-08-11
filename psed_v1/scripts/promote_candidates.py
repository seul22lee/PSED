#!/usr/bin/env python3
"""
scripts/promote_candidates.py — promote audited candidates into the live corpus.

    python3 scripts/promote_candidates.py [--dry-run]

Selection is read from reports/exact_overlap_audit.json and is restricted to
verdict == TRUE_DEPOSITION_EXACT_OVERLAP: the paper must itself DEPOSIT a material
the live corpus already has. A material appearing as substrate, support, template,
electrode or cited literature does not qualify — that distinction is the whole point
of the audit, and rebuilding the set from the older `exact_overlap` field or from
priority rank would reintroduce the false overlaps it removed.

Copies the already-staged Docling artifacts from
corpus/acquisition/candidates/<id>/ into papers/<id>/extracted/. Docling is NOT
re-run: the staged output is the same converter the live parse stage uses.

Writes reports/true_deposition_overlap_12_selection.json as the frozen manifest that
every later stage targets, so no stage has to re-derive the set.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                              # noqa: E402

AUDIT = P.REPORTS / "exact_overlap_audit.json"
MANIFEST = P.REPORTS / "true_deposition_overlap_12_selection.json"
CANDIDATES = P.REPO / "corpus" / "acquisition" / "candidates"
VERDICT = "TRUE_DEPOSITION_EXACT_OVERLAP"
REQUIRED = ("document.md", "structure.json")


def select():
    audit = json.loads(AUDIT.read_text())
    rows = [r for r in audit["candidates"] if r["verdict"] == VERDICT]
    return audit, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    audit, rows = select()
    live_before = sorted(P.papers())
    ids = [r["candidate_id"] for r in rows]

    assert len(rows) == 12, "expected 12 TRUE_DEPOSITION_EXACT_OVERLAP, got %d" % len(rows)
    inter = sorted(set(ids) & set(live_before))
    assert not inter, "already in live corpus: %s" % inter

    ready, missing = [], []
    for cid in ids:
        d = CANDIDATES / cid
        gaps = [f for f in REQUIRED if not (d / f).exists()]
        (missing if gaps else ready).append((cid, gaps))
    assert not missing, "missing staged artifacts: %s" % missing

    manifest = {
        "selection_source": str(AUDIT.relative_to(P.REPO)),
        "selection_verdict": VERDICT,
        "audit_note": audit.get("note"),
        "live_papers_before": len(live_before),
        "selected_count": len(rows),
        "docling_reruns": 0,
        "papers": [],
    }
    for r in rows:
        cid = r["candidate_id"]
        src = CANDIDATES / cid
        meta = json.loads((src / "meta.json").read_text()) if (src / "meta.json").exists() else {}
        st = json.loads((src / "structure.json").read_text())
        manifest["papers"].append({
            "paper_id": cid, "doi": meta.get("doi"), "title": r.get("title"),
            "deposited_material": r["deposited_material"],
            "substrate_support_material": r["substrate_support_material"],
            "true_overlap_material": r["true_corpus_overlap"],
            "supporting_sentence": r["supporting_sentence"],
            "source_candidate_dir": str(src.relative_to(P.REPO)),
            "pdf": meta.get("pdf"),
            "n_figures": st.get("n_figures"), "n_tables": st.get("n_tables"),
            "md_chars": meta.get("md_chars"),
        })

    if a.dry_run:
        print(json.dumps(manifest, indent=1)[:1500])
        print("\n[dry-run] would promote %d paper(s)" % len(rows))
        return 0

    promoted = []
    for cid in ids:
        src, dst = CANDIDATES / cid, P.extracted_dir(cid)
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("document.md", "structure.json"):
            shutil.copy2(src / name, dst / name)
        if (src / "figures").is_dir():
            shutil.copytree(src / "figures", dst / "figures", dirs_exist_ok=True)
        # keep the staging provenance next to the artifacts it produced
        if (src / "meta.json").exists():
            shutil.copy2(src / "meta.json", dst / "candidate_meta.json")
        promoted.append(cid)

    live_after = sorted(P.papers())
    manifest["live_papers_after"] = len(live_after)
    manifest["promoted"] = promoted
    MANIFEST.write_text(json.dumps(manifest, indent=1))

    print("live papers before : %d" % len(live_before))
    print("newly promoted     : %d" % len(promoted))
    print("live papers after  : %d" % len(live_after))
    assert len(live_after) == len(live_before) + 12, "unexpected live corpus size"
    # duplicate guard on DOI and title
    dois = [p["doi"] for p in manifest["papers"] if p["doi"]]
    titles = [(p["title"] or "").strip().lower() for p in manifest["papers"]]
    assert len(dois) == len(set(dois)), "duplicate DOI in selection"
    assert len(titles) == len(set(titles)), "duplicate title in selection"
    print("no duplicate DOI/title : True")
    print("wrote %s" % MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
