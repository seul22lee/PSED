#!/usr/bin/env python3
"""READ-ONLY. Stage 0 step 1 — collapse the inflated record nodes into UNIQUE SOURCE
ENTITIES and gather every evidence layer for each, including the PDF page.

Stable entity key:
    {paper_id}|{fig_docling_index}|{printed_figure_number}|{panel}|{source_series}|{representation}

`representation` distinguishes several depictions of the SAME underlying data inside
one paper (as-measured / scaled / normalised panels of one experiment), so that
duplicated representations are visible rather than silently merged.

Run with psed310 (needs PyMuPDF for page numbers):
  /home/ftk3187/miniconda3/envs/psed310/bin/python .../stage0_entities.py
"""
import paths as P
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis" / "stage0"
DIAG = REPO / "reports" / "condition_binding_diagnosis"
KB = P.PAPERS
EX = P.PAPERS
PDFS = REPO / "03_corpus" / "pdfs"


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def norm_math(t):
    """docling writes symbols as Mathematical-Italic Unicode; fold to ASCII."""
    o = []
    for ch in t:
        c = ord(ch)
        if 0x1D400 <= c <= 0x1D7FF:
            for base, start in ((0x41, 0x1D434), (0x61, 0x1D44E), (0x41, 0x1D400),
                                (0x61, 0x1D41A), (0x41, 0x1D468), (0x61, 0x1D482)):
                if start <= c < start + 26:
                    o.append(chr(base + c - start))
                    break
            else:
                o.append(ch)
        else:
            o.append(ch)
    return "".join(o)


# ---- PDF page index -------------------------------------------------------
_PDF = {}


def pdf_pages(doi):
    if doi in _PDF:
        return _PDF[doi]
    p = PDFS / (doi + ".pdf")
    pages = []
    if p.exists():
        try:
            import fitz
            d = fitz.open(str(p))
            pages = [norm_math(pg.get_text()) for pg in d]
            d.close()
        except Exception:
            pages = []
    _PDF[doi] = pages
    return pages


def find_page(doi, needle, minlen=18):
    """1-based PDF page containing `needle` (whitespace-insensitive)."""
    if not needle:
        return None
    pages = pdf_pages(doi)
    if not pages:
        return None
    key = re.sub(r"\s+", "", needle)[:60]
    if len(key) < minlen:
        return None
    for i, t in enumerate(pages):
        if key in re.sub(r"\s+", "", t):
            return i + 1
    # fall back to a distinctive shorter prefix
    key = key[:28]
    for i, t in enumerate(pages):
        if len(key) >= minlen and key in re.sub(r"\s+", "", t):
            return i + 1
    return None


# ---- representation label -------------------------------------------------
REPR_RULES = [
    (re.compile(r"as[- ]measured", re.I), "as_measured"),
    (re.compile(r"\bscaled\b", re.I), "scaled"),
    (re.compile(r"normali[sz]ed", re.I), "normalized"),
    (re.compile(r"\binset\b", re.I), "inset"),
]


def representation_of(caption, panel, x_q, y_q):
    """Which depiction of the data this panel is. Panel-clause first."""
    clause = ""
    if panel:
        m = re.search(r"\(\s*%s\s*\)" % re.escape(panel), caption or "", re.I)
        if m:
            nxt = re.search(r"\(\s*[a-h]\s*\)", caption[m.end():], re.I)
            clause = caption[m.start(): m.end() + (nxt.start() if nxt else 200)]
    for rx, lab in REPR_RULES:
        if clause and rx.search(clause):
            return lab
    return "primary"


def main():
    trig = {t["paper_id"] for t in J(DIAG / "full_paper_audit_triggers.json")["triggers"]}
    pop = J(DIAG / "corpus_population_manifest.json")
    entities = {}
    node_counts = Counter()

    for doi in sorted(trig):
        exps = J(P.resolved_json(doi, "experiments"), []) or []
        series = {s["series_id"]: s for s in (J(P.resolved_json(doi, "series"), []) or [])}
        fd = J(P.extracted_dir(doi) / "figure_data.json", {}) or {}
        struct = J(P.extracted_dir(doi) / "structure.json", {}) or {}
        doc = norm_math(Path(P.extracted_dir(doi) / "document.md").read_text(errors="replace")
                        if (P.extracted_dir(doi) / "document.md").exists() else "")
        fig_by_idx = {str(f.get("figure")): f for f in fd.get("figures", [])}
        tables = struct.get("tables", []) or []

        for e in exps:
            node_counts[doi] += 1
            prov = e.get("provenance") or {}
            fi = str(prov.get("fig_docling_index") or "")
            fn = str(prov.get("figure_number") or "")
            pan = str(prov.get("panel") or "")
            # source series = the ORIGINAL curve label, stripped of the axis prefix
            sname = e.get("series_name") or ""
            slabel = sname.split(":", 1)[1].strip() if ":" in sname else (sname or "<single>")
            fig = fig_by_idx.get(fi, {})
            cap = fig.get("caption") or ""
            rep = representation_of(cap, pan, e.get("coordinate"),
                                    (e.get("measurand") or {}).get("quantity"))
            key = "%s|%s|%s|%s|%s|%s" % (doi, fi or "-", fn or "-", pan or "-", slabel, rep)

            ent = entities.get(key)
            if ent is None:
                panel = None
                for p in fig.get("panels", []) or []:
                    if str(p.get("panel") or "") == pan:
                        panel = p
                        break
                src_series = None
                plist = (panel or {}).get("series", []) or []
                for s in plist:
                    if str(s.get("label", "")).strip() == slabel:
                        src_series = s
                        break
                if src_series is None and slabel == "<single>" and len(plist) == 1:
                    src_series = plist[0]      # sole unlabelled curve of the panel
                ent = entities[key] = {
                    "entity_key": key,
                    "paper_id": doi,
                    "fig_docling_index": fi or None,
                    "printed_figure_number": fn or None,
                    "panel": pan or None,
                    "source_series": slabel,
                    "representation": rep,
                    "figure_image": fig.get("image"),
                    "caption": cap,
                    "caption_pdf_page": find_page(doi, cap[:70]),
                    "panel_conditions": (panel or {}).get("conditions") or {},
                    "panel_series_axis": (panel or {}).get("series_axis"),
                    "panel_x": (panel or {}).get("x"),
                    "panel_y": (panel or {}).get("y"),
                    "figure_source_flag": fig.get("source"),
                    "panel_source_flag": (fig.get("panel_source") or {}).get(pan),
                    "n_source_points": len((src_series or {}).get("points") or []),
                    "record_node_ids": [],
                    "record_node_count": 0,
                    "series_ids": set(),
                    "coordinate": e.get("coordinate"),
                    "measurand": (e.get("measurand") or {}).get("quantity"),
                    "measurand_unit": (e.get("measurand") or {}).get("unit"),
                    "relevance": e.get("relevance"),
                    "is_model_result": bool(e.get("is_model_result")),
                    "granularity": e.get("granularity"),
                }
            ent["record_node_ids"].append(e["exp_id"])
            ent["record_node_count"] += 1
            if e.get("in_series"):
                ent["series_ids"].add(e["in_series"])

        # attach paper-level evidence once
        for k, ent in entities.items():
            if ent["paper_id"] != doi or "_doc" in ent:
                continue
            ent["_doc"] = True
            fn = ent["printed_figure_number"]
            body = []
            if fn:
                for m in re.finditer(r"[Ff]ig(?:ure)?s?\.?\s*%s(?![0-9])" % re.escape(fn), doc):
                    body.append(doc[max(0, m.start() - 260): m.end() + 620])
                    if len(body) >= 3:
                        break
            ent["body_mentions"] = "\n---\n".join(body)
            ent["body_pdf_page"] = find_page(doi, body[0][:70]) if body else None
            ent["table_captions"] = [t.get("caption") for t in tables]

    for ent in entities.values():
        ent["series_ids"] = sorted(ent["series_ids"])
        ent.pop("_doc", None)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "source_entities.json").write_text(json.dumps(
        {"n_triggered_papers": len(trig),
         "n_record_nodes": sum(node_counts.values()),
         "n_source_entities": len(entities),
         "node_counts_per_paper": dict(node_counts),
         "entities": list(entities.values())}, indent=1, ensure_ascii=False))
    per = Counter(e["paper_id"] for e in entities.values())
    print("triggered papers: %d" % len(trig))
    print("record nodes    : %d" % sum(node_counts.values()))
    print("source entities : %d" % len(entities))
    print("\n%-36s %8s %8s %6s" % ("paper", "nodes", "entities", "ratio"))
    for doi in sorted(trig):
        n, u = node_counts[doi], per[doi]
        print("%-36s %8d %8d %6.1fx" % (doi, n, u, n / u if u else 0))
    pdfok = sum(1 for e in entities.values() if e.get("caption_pdf_page"))
    print("\nentities with a resolved PDF page: %d/%d" % (pdfok, len(entities)))


if __name__ == "__main__":
    main()
