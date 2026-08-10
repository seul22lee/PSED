#!/usr/bin/env python3
"""Move the three per-paper trees into one folder per paper. MOVES, never copies.

    03_corpus/extracted/<doi>/*          -> papers/<doi>/extracted/*
    02_extraction/output/<doi>/resolved  -> papers/<doi>/resolved
    02_extraction/output/<doi>/canonical -> papers/<doi>/canonical
    03_corpus/pdfs/<doi>.pdf             -> papers/<doi>/paper.pdf

Uses `git mv` where the file is tracked so history follows, plain rename
otherwise. Verifies afterwards that every source file arrived and that nothing
was left behind: the check is on file COUNT and CONTENT HASH, not on the move
returning success.

PDFs with no extraction are candidates, not corpus papers; they stay in
03_corpus/pdfs/. Corpus-wide outputs (knowledge_graph_onto.json, recipes.json)
belong to no paper and stay in 02_extraction/output/.

Usage:  migrate_to_paper_folders.py [--dry-run]
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OLD_EXTRACTED = REPO / "03_corpus" / "extracted"
OLD_OUTPUT = REPO / "02_extraction" / "output"
OLD_PDFS = REPO / "03_corpus" / "pdfs"
PAPERS = REPO / "papers"

#: these live in 02_extraction/output/ but describe the whole corpus
CORPUS_LEVEL = {"knowledge_graph_onto.json", "knowledge_graph_onto.graphml",
                "recipes.json", "recipe_accounting.json", "_accuracy.json",
                "_archive"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked(p):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(p)],
                       cwd=str(REPO), capture_output=True)
    return r.returncode == 0


def move(src, dst, dry):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry:
        return
    if tracked(src):
        r = subprocess.run(["git", "mv", str(src), str(dst)],
                           cwd=str(REPO), capture_output=True)
        if r.returncode == 0:
            return
    shutil.move(str(src), str(dst))


def inventory(root):
    """relative path -> (size, sha) for every file below root."""
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = (p.stat().st_size, sha(p))
    return out


def main():
    dry = "--dry-run" in sys.argv
    dois = sorted(d.name for d in OLD_EXTRACTED.iterdir() if d.is_dir()) \
        if OLD_EXTRACTED.exists() else []
    if not dois:
        print("nothing to migrate (03_corpus/extracted is absent or empty)")
        return 0

    before = {}
    for doi in dois:
        before[doi] = {
            "extracted": inventory(OLD_EXTRACTED / doi),
            "resolved": inventory(OLD_OUTPUT / doi / "resolved"),
            "canonical": inventory(OLD_OUTPUT / doi / "canonical"),
            "pdf": (sha(OLD_PDFS / (doi + ".pdf"))
                    if (OLD_PDFS / (doi + ".pdf")).exists() else None),
        }

    moved = {"extracted": 0, "resolved": 0, "canonical": 0, "pdf": 0}
    for doi in dois:
        dest = PAPERS / doi
        if (OLD_EXTRACTED / doi).exists():
            move(OLD_EXTRACTED / doi, dest / "extracted", dry)
            moved["extracted"] += 1
        for sub in ("resolved", "canonical"):
            src = OLD_OUTPUT / doi / sub
            if src.exists():
                move(src, dest / sub, dry)
                moved[sub] += 1
        pdf = OLD_PDFS / (doi + ".pdf")
        if pdf.exists():
            move(pdf, dest / "paper.pdf", dry)
            moved["pdf"] += 1

    if dry:
        print("DRY RUN — would move: %s" % moved)
        return 0

    # ---- verify: every file arrived, byte for byte -----------------------
    problems = []
    for doi in dois:
        dest = PAPERS / doi
        for sub in ("extracted", "resolved", "canonical"):
            want = before[doi][sub]
            got = inventory(dest / sub)
            if want != got:
                missing = sorted(set(want) - set(got))
                changed = [k for k in set(want) & set(got) if want[k] != got[k]]
                problems.append((doi, sub, missing[:5], changed[:5]))
        if before[doi]["pdf"]:
            p = dest / "paper.pdf"
            if not p.exists() or sha(p) != before[doi]["pdf"]:
                problems.append((doi, "pdf", ["paper.pdf"], []))

    # ---- verify nothing was left behind ----------------------------------
    leftovers = []
    if OLD_EXTRACTED.exists():
        leftovers += [str(p.relative_to(REPO)) for p in OLD_EXTRACTED.rglob("*")
                      if p.is_file()]
    if OLD_OUTPUT.exists():
        for d in OLD_OUTPUT.iterdir():
            if d.is_dir() and d.name not in CORPUS_LEVEL:
                leftovers += [str(p.relative_to(REPO)) for p in d.rglob("*")
                              if p.is_file()]

    for d in (OLD_EXTRACTED,):
        if d.exists() and not any(d.rglob("*")):
            d.rmdir()
    for d in sorted(OLD_OUTPUT.glob("*")) if OLD_OUTPUT.exists() else []:
        if d.is_dir() and d.name not in CORPUS_LEVEL and not any(d.rglob("*")):
            d.rmdir()

    print("moved: %s" % moved)
    print("papers now under papers/: %d" % len(list(PAPERS.iterdir())))
    print("content mismatches: %d" % len(problems))
    for x in problems[:10]:
        print("   %s" % (x,))
    print("files left in the old trees: %d" % len(leftovers))
    for x in leftovers[:10]:
        print("   %s" % x)
    (REPO / "tools" / "migration_report.json").write_text(json.dumps({
        "papers": len(dois), "moved": moved,
        "content_mismatches": problems, "leftovers": leftovers,
        "pdfs_left_as_candidates": len(list(OLD_PDFS.glob("*.pdf")))
        if OLD_PDFS.exists() else 0,
    }, indent=1))
    return 1 if (problems or leftovers) else 0


if __name__ == "__main__":
    sys.exit(main())
