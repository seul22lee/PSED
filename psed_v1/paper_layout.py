"""
paper_layout.py — where a paper's files live. One definition, used everywhere.

Before this module the same paper was spread over three trees:

    03_corpus/pdfs/<doi>.pdf
    03_corpus/extracted/<doi>/{scout,card,records,figure_data,...}.json
    02_extraction/output/<doi>/{resolved,canonical}/...

Reviewing one paper meant opening three directories, and every consumer
hard-coded its own path constant, so a move would have broken about fifty call
sites. Everything now lives under one deterministic, DOI-named folder:

    papers/<doi>/
        paper.pdf              the source PDF
        extracted/             docling + LLM extraction for this paper
        resolved/              entities, experiments, series, assertions, results
        canonical/             the canonical curve layer
        review.json            manifest: what is here, and the paper's counts

`<doi>` is the filesystem-safe DOI already used as the paper id throughout the
pipeline (`10.1063/1.5028178` -> `10.1063_1.5028178`), so the folder name is
derivable from the DOI alone and never invented.

Corpus-level artifacts are NOT per paper and stay outside:
`02_extraction/output/knowledge_graph_onto.json`, `recipes.json`,
`recipe_accounting.json`.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
PAPERS = REPO / "papers"

#: corpus-wide outputs, which belong to no single paper
CORPUS_OUT = REPO / "02_extraction" / "output"
#: PDFs fetched but not yet extracted — candidates, not corpus papers
PDF_INBOX = REPO / "03_corpus" / "pdfs"

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def paper_id(doi):
    """Filesystem-safe, deterministic folder name for a DOI.

    Idempotent: an already-safe id passes through unchanged, so callers may hand
    over either form without checking.
    """
    return _SAFE.sub("_", str(doi).strip().strip("/"))


def paper_dir(doi):
    return PAPERS / paper_id(doi)


def extracted_dir(doi):
    return paper_dir(doi) / "extracted"


def resolved_dir(doi):
    return paper_dir(doi) / "resolved"


def canonical_dir(doi):
    return paper_dir(doi) / "canonical"


def pdf_path(doi):
    """The paper's own PDF. Falls back to the un-extracted inbox so a candidate
    paper that has no folder yet is still findable."""
    p = paper_dir(doi) / "paper.pdf"
    if p.exists():
        return p
    return PDF_INBOX / ("%s.pdf" % paper_id(doi))


def review_manifest(doi):
    return paper_dir(doi) / "review.json"


def papers(require=("extracted",)):
    """Every paper folder, sorted. `require` names subpaths that must exist, so
    callers can ask for "papers with extraction" or "papers with results"
    without re-implementing the check."""
    if not PAPERS.exists():
        return []
    out = []
    for d in sorted(PAPERS.iterdir()):
        if not d.is_dir():
            continue
        if all((d / r).exists() for r in require):
            out.append(d.name)
    return out


def glob_resolved(name):
    """Every papers/*/resolved/<name> path, sorted. Replaces the old
    `output/*/resolved/<name>` glob one-for-one."""
    return sorted(PAPERS.glob("*/resolved/%s" % name))


def glob_canonical(name):
    return sorted(PAPERS.glob("*/canonical/%s" % name))
