#!/usr/bin/env python3
"""
scripts/parse_candidates.py — Docling the acquisition inbox for TRIAGE only.

    python3 scripts/parse_candidates.py [--limit N] [--force]

Reads corpus/acquisition/pdf_inbox/*.pdf and writes, per candidate:

    corpus/acquisition/candidates/<candidate_id>/document.md
    corpus/acquisition/candidates/<candidate_id>/structure.json
    corpus/acquisition/candidates/<candidate_id>/meta.json
    corpus/acquisition/candidates/<candidate_id>/figures/fig_N.png

Deliberately NOT under papers/. A paper becomes part of the live corpus by being
in papers/<id>/extracted/, so writing candidate Docling output there would silently
enrol every candidate the moment it was parsed. paths.papers() would pick it up and
resolve, canonical, the KG and every report would follow. Keeping candidates in
their own tree means parsing one costs nothing but disk.

Resumable: a candidate whose document.md already exists is skipped unless --force.
No LLM, no network — Docling only, the same converter the live parse stage uses.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                          # noqa: E402
from pipeline.parse import docling_parse as DP             # noqa: E402

CANDIDATES = P.REPO / "corpus" / "acquisition" / "candidates"
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")


def norm_doi(d):
    d = (d or "").strip().lower().rstrip(".,;)")
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def head_text(pdf, pages=2):
    """First pages of raw text, for identity only — no Docling needed."""
    try:
        import fitz
        doc = fitz.open(pdf)
        t = "\n".join(doc[i].get_text() for i in range(min(pages, doc.page_count)))
        n = doc.page_count
        doc.close()
        return t, n
    except Exception:
        return "", None


def identity(pdf):
    """(candidate_id, doi, title_guess). DOI in the document text wins; the filename
    is only a fallback, because acquisition filenames do not reliably encode a DOI."""
    txt, npages = head_text(pdf)
    doi = None
    m = DOI_RE.search(txt)
    if m:
        doi = norm_doi(m.group(0))
    fm = re.match(r"(10\.\d{4,9})[_.](.+)\.pdf$", pdf.name)
    doi_fn = norm_doi("%s/%s" % (fm.group(1), fm.group(2))) if fm else None
    doi = doi or doi_fn
    lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 25]
    title = max(lines[:12], key=len)[:250] if lines else None
    cid = re.sub(r"[^A-Za-z0-9._-]", "_", (doi or pdf.stem).lower())
    return cid, doi, doi_fn, title, npages, len(txt)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    pdfs = sorted(P.PDF_INBOX.glob("*.pdf"))
    if a.limit:
        pdfs = pdfs[:a.limit]
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    ok = skipped = failed = 0
    for i, pdf in enumerate(pdfs, 1):
        cid, doi, doi_fn, title, npages, nchars = identity(pdf)
        out = CANDIDATES / cid
        if (out / "document.md").exists() and not a.force:
            skipped += 1
            continue
        out.mkdir(parents=True, exist_ok=True)
        print("[%2d/%d] %s -> %s" % (i, len(pdfs), pdf.name, cid), flush=True)
        try:
            md, struct = DP.run(str(pdf), figdir=out / "figures")
            if len(md) < 500:
                md, struct = DP.run(str(pdf), force_ocr=True, figdir=out / "figures")
                struct["ocr_forced"] = True
            (out / "document.md").write_text(md)
            (out / "structure.json").write_text(json.dumps(struct, indent=1))
            (out / "meta.json").write_text(json.dumps({
                "candidate_id": cid, "pdf": str(pdf.relative_to(P.REPO)),
                "doi": doi, "doi_from_filename": doi_fn, "title_from_pdf": title,
                "pdf_pages": npages, "pdf_head_chars": nchars,
                "md_chars": len(md), "n_figures": struct.get("n_figures"),
                "n_tables": struct.get("n_tables"),
                "ocr_forced": bool(struct.get("ocr_forced")),
            }, indent=1))
            ok += 1
        except Exception as e:
            failed += 1
            (out / "meta.json").write_text(json.dumps({
                "candidate_id": cid, "pdf": str(pdf.relative_to(P.REPO)),
                "doi": doi, "error": "%s: %s" % (type(e).__name__, e)}, indent=1))
            print("   FAILED %s: %s" % (type(e).__name__, e), flush=True)
    print("\ncandidates: %d  parsed: %d  skipped(existing): %d  failed: %d"
          % (len(pdfs), ok, skipped, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
