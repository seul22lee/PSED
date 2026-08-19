"""
paths.py — the ONE path API. Every runtime module resolves locations through it.

Before this module the tree had two authoritative per-paper roots and each stage
built its own: two numbered trees, plus ad-hoc `ROOT.parent / "papers"` and
`ROOT / "extracted"` expressions. A half-finished migration left
the Docling stage writing to a directory no other stage read, and a printed
figure number could be looked up against a docling index because two key spaces
shared one dict.

There is now exactly one per-paper root:

    papers/<paper_id>/
        paper.pdf              the source PDF
        extracted/             parse + scout + figure extraction artifacts
        resolved/              entities, experiments, series, assertions, results
        canonical/             the canonical curve layer
        review.json            per-paper review manifest

`<paper_id>` is the filesystem-safe DOI (`10.1063/1.5028178` ->
`10.1063_1.5028178`), so a folder name is derivable from the DOI alone.

Corpus-level artifacts belong to no single paper and live in `papers/_corpus/`.
Candidate PDFs that have not been parsed yet are not papers and live in
`corpus/acquisition/pdf_inbox/`.

Nothing here resolves into a pre-psed_v1 tree; `tests/integration/test_standalone.py`
asserts that for the whole package.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent

#: The corpus the stages read and write. Overridable so an alternate corpus -- the
#: semantic pilot snapshot, a scratch corpus in a test -- can be regenerated through the
#: same maintained commands instead of an inline path hack. Set PSED_CORPUS_ROOT, or call
#: set_corpus_root() from a stage's --corpus-root flag.
PAPERS = Path(__import__("os").environ.get("PSED_CORPUS_ROOT") or (REPO / "papers"))


def set_corpus_root(root):
    """Point every path helper at another corpus. Returns the previous root."""
    global PAPERS
    prev, PAPERS = PAPERS, Path(root)
    return prev
#: outputs that describe the whole corpus, not one paper
CORPUS_OUT = PAPERS / "_corpus"
#: fetched-but-not-yet-parsed PDFs: candidates, not corpus papers
PDF_INBOX = REPO / "corpus" / "acquisition" / "pdf_inbox"

ONTOLOGY_DIR = REPO / "ontology"
ONTOLOGY_JSON = ONTOLOGY_DIR / "ald_ontology.json"
RESOURCES = REPO / "resources"
REPORTS = REPO / "reports"

#: `papers/_corpus` is an output bucket, never a paper
_RESERVED = {"_corpus"}
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def paper_id(doi):
    """Filesystem-safe, deterministic folder name for a DOI. Idempotent, so a
    caller may pass either form without checking."""
    return _SAFE.sub("_", str(doi).strip().strip("/"))


def paper_dir(doi):
    return PAPERS / paper_id(doi)


def pdf_path(doi):
    """The paper's own PDF, falling back to the un-parsed inbox so a candidate
    that has no paper folder yet is still locatable."""
    p = paper_dir(doi) / "paper.pdf"
    return p if p.exists() else PDF_INBOX / ("%s.pdf" % paper_id(doi))


def extracted_dir(doi):
    return paper_dir(doi) / "extracted"


def resolved_dir(doi):
    return paper_dir(doi) / "resolved"


def canonical_dir(doi):
    return paper_dir(doi) / "canonical"


def review_path(doi):
    return paper_dir(doi) / "review.json"


def figures_dir(doi):
    return extracted_dir(doi) / "figures"


def recovery_dir(doi):
    return extracted_dir(doi) / "recovery"


# --- named artifacts, so no caller spells a filename twice -----------------
def document_md(doi):
    return extracted_dir(doi) / "document.md"


def structure_json(doi):
    return extracted_dir(doi) / "structure.json"


def scout_json(doi):
    return extracted_dir(doi) / "scout.json"


def card_json(doi):
    return extracted_dir(doi) / "card.json"


def figure_data_json(doi):
    return extracted_dir(doi) / "figure_data.json"


def records_json(doi):
    return extracted_dir(doi) / "records.json"


def geometry_json(doi):
    return extracted_dir(doi) / "geometry.json"


def pressure_json(doi):
    return extracted_dir(doi) / "pressure.json"


def resolved_json(doi, name):
    """entities | experiments | series | assertions | counts | results"""
    return resolved_dir(doi) / ("%s.json" % name)


def curves_json(doi):
    return canonical_dir(doi) / "curves.json"


def knowledge_graph_json():
    return CORPUS_OUT / "knowledge_graph_onto.json"


# --- enumeration -----------------------------------------------------------
def papers(require=("extracted",)):
    """Every paper folder, sorted. `require` names subpaths that must exist, so
    callers can ask for "papers with extraction" or "papers with results"
    without re-implementing the check."""
    if not PAPERS.exists():
        return []
    out = []
    for d in sorted(PAPERS.iterdir()):
        if not d.is_dir() or d.name in _RESERVED:
            continue
        if all((d / r).exists() for r in require):
            out.append(d.name)
    return out


def glob_resolved(name):
    """Every papers/*/resolved/<name>, sorted, excluding the corpus bucket."""
    return sorted(p for p in PAPERS.glob("*/resolved/%s" % name)
                  if p.parts[-3] not in _RESERVED)


def glob_canonical(name):
    return sorted(p for p in PAPERS.glob("*/canonical/%s" % name)
                  if p.parts[-3] not in _RESERVED)


def glob_extracted(name):
    return sorted(p for p in PAPERS.glob("*/extracted/%s" % name)
                  if p.parts[-3] not in _RESERVED)
