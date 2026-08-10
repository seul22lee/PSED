#!/usr/bin/env python3
"""Repoint every per-paper path at papers/<doi>/. Run once, after the migration.

Two shapes exist in the code base and they are handled differently:

  OUTPUT / doi / "resolved" / f      -> PAPERS / doi / "resolved" / f
      identical shape, so the CONSTANT is redefined and no call site changes.

  EXTRACTED / doi / "extracted" / f                -> PAPERS / doi / "extracted" / f
      one segment deeper, so each call site is rewritten to extracted_dir(doi).

Corpus-level artifacts (knowledge_graph_onto.json, recipes.json,
recipe_accounting.json, _accuracy.json) belong to no paper and keep pointing at
02_extraction/output/.

Prints every file it touched; verify with `grep_stale_paths` afterwards.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# constant definitions -> new definition, per file
CONST = [
    # per-paper output roots: same shape, so only the definition moves
    (r'^OUTPUT = REPO / "02_extraction" / "output"$',
     'OUTPUT = REPO / "papers"          # papers/<doi>/{resolved,canonical}/'),
    (r'^KB = REPO / "02_extraction" / "output"$',
     'KB = REPO / "papers"              # papers/<doi>/resolved/'),
    (r'^OUT = PIPE / "output"$',
     'OUT = REPO_ROOT / "papers"        # papers/<doi>/{resolved,canonical}/'),
    (r'^OUT = ROOT\.parent / "02_extraction" / "output"$',
     'OUT = ROOT.parent / "papers"      # papers/<doi>/resolved/'),
    # extraction roots: one segment deeper, call sites rewritten below
    (r'^EXTRACTED = ROOT / "extracted"$',
     'EXTRACTED = ROOT.parent / "papers"   # papers/<doi>/extracted/'),
    (r'^EXTRACTED = HERE\.parent / "extracted"$',
     'EXTRACTED = HERE.parents[2] / "papers"   # papers/<doi>/extracted/'),
    (r'^CORPUS = REPO / "03_corpus" / "extracted"$',
     'CORPUS = REPO / "papers"          # papers/<doi>/extracted/'),
    (r'^CORPUS_CARDS = ROOT\.parent / "03_corpus" / "extracted"$',
     'CORPUS_CARDS = ROOT.parent / "papers"    # papers/<doi>/extracted/'),
    (r'^EXTRACTED = REPO / "03_corpus" / "extracted"$',
     'EXTRACTED = REPO / "papers"       # papers/<doi>/extracted/'),
    (r'^EXTRACT = ROOT / "03_corpus" / "extracted"$',
     'EXTRACT = ROOT / "papers"         # papers/<doi>/extracted/'),
]

# `<ROOT> / "output"` globs and joins that are per-paper
GLOBS = [
    (r'\(ROOT / "output"\)\.glob\("\*/(resolved|canonical)/',
     r'(ROOT.parent / "papers").glob("*/\1/'),
    (r'str\(ROOT / "output" / "\*" / "resolved"',
     r'str(ROOT.parent / "papers" / "*" / "resolved"'),
    (r'PIPE / "output" / sd / "(resolved|canonical)"',
     r'PAPERS / sd / "\1"'),
    (r'\(REPO / "02_extraction" / "output"\)',
     r'(REPO / "papers")'),
]

# EXTRACTED-family call sites: one segment deeper
DEEPER = re.compile(
    r'\b(EXTRACTED|EXTRACT|CORPUS|CORPUS_CARDS)\s*/\s*'
    r'(sd|p|s|paper|doi|CASE|pid|"\*")\s*/\s*(?=["\w])')
DEEPER_BARE = re.compile(
    r'\b(EXTRACTED|EXTRACT|CORPUS|CORPUS_CARDS)\s*/\s*'
    r'(sd|p|s|paper|doi|CASE|pid)\b(?!\s*/)')
ITERDIR = re.compile(r'\b(EXTRACTED|CORPUS|CORPUS_CARDS)\.iterdir\(\)')


def patch(path):
    src = path.read_text()
    out = src
    for pat, rep in CONST:
        out = re.sub(pat, rep, out, flags=re.M)
    for pat, rep in GLOBS:
        out = re.sub(pat, rep, out)
    out = DEEPER.sub(lambda m: '%s / %s / "extracted" / ' % (m.group(1), m.group(2)), out)
    out = DEEPER_BARE.sub(lambda m: '%s / %s / "extracted"' % (m.group(1), m.group(2)), out)
    # iterating the corpus root now yields paper folders, and the extraction
    # lives one level in; callers test `(d / "scout.json").exists()` etc., so the
    # iterator must yield the extraction directory itself
    out = ITERDIR.sub(lambda m: '(d / "extracted" for d in %s.iterdir() if d.is_dir())'
                      % m.group(1), out)
    if out != src:
        path.write_text(out)
        return True
    return False


def main():
    targets = []
    for d in ("01_ontology", "02_extraction", "03_corpus", "04_twin_mpc",
              "05_orchestration", "reports", "tools"):
        for p in (REPO / d).rglob("*.py"):
            if "third_party" in p.parts or "extract-line-chart-data" in p.parts:
                continue
            targets.append(p)
    changed = [p for p in sorted(targets) if patch(p)]
    print("patched %d of %d python files" % (len(changed), len(targets)))
    for p in changed:
        print("   %s" % p.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
