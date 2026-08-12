#!/usr/bin/env python3
"""
pilot_supplements.py — recover source evidence the extraction stage lost.

Two independent losses are known in the pilot set, and both are handled by ONE generic
rule rather than by naming the papers:

    a printed figure has a caption panel clause describing a measurement, and no
    extracted entity covers that (printed figure, panel)

Such a panel is a real measurement the paper reports whose numbers PSED does not hold.
The pilot emits it as a Measurement carrying its caption evidence and NO ResultSeries,
because inventing points would be worse than recording the gap. Every supplement records
WHY it was needed, so the two causes stay distinguishable:

  · caption grammar — the panel marker was written '( a )' with internal spaces, which
    the production caption parser rejects, so the whole figure lost its caption and never
    reached the vision stage. The pilot's copy of the parser accepts the spaced form.
  · missing crop — Docling emitted no PictureItem for the panel, so no image ever
    existed to digitise. The panel region is rendered from the PDF for visual review.

Local and deterministic throughout: the pilot's copy of the caption parser, and PyMuPDF
page rendering. No API, no vision model.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_evidence as PE                                     # noqa: E402

#: a panel clause that reports a MEASUREMENT rather than a photograph or a schematic
_MEASUREMENT_CLAUSE = re.compile(
    r"\b(?:response|change|stabilit\w+|voltammetr\w+|voltammogram|impedance|spectra|"
    r"spectrum|profile|curve|plot|dependence|as a function of|versus|vs\.?|"
    r"capacit\w+|resistiv\w+|thickness|growth rate|conductiv\w+|current|potential|"
    r"cycl\w+|retention|hysteresis)\b", re.I)
#: clauses that are images, not plotted measurements
_NON_PLOT = re.compile(
    r"\b(?:photograph|photo|schematic|illustration|diagram|"
    r"(?:SEM|TEM|FESEM|HRTEM|AFM|optical)\s+images?|"
    r"images?\s+(?:of|showing)|micrograph|cross[- ]section\s+images?|top[- ]view|"
    r"configuration|setup|layout)\b", re.I)
#: A caption that reports a DEPOSITION performed on a described structure. Such a figure
#: documents a real experimental case even when its evidence is an electron micrograph
#: rather than an x-y curve — experiment existence does not require a digitisable plot.
_DEPOSITION_CLAUSE = re.compile(
    r"\b(?:coated|deposited|grown|conformal\w*|deposition)\b", re.I)
#: process/geometry quantities a caption of that kind states outright
DEPOSITION_HINTS = [
    (re.compile(r"\b(?:coated by|using|with|after)?\s*\d[\d.,\s-]*\s*cycles\b", re.I),
     "cycle_number", "cycle"),
    (re.compile(r"\baspect ratio\b", re.I), "aspect_ratio", None),
    (re.compile(r"\bdepth\b", re.I), "feature_height", "µm"),
    (re.compile(r"\b(?:average\s+)?width\b", re.I), "feature_width", "µm"),
    (re.compile(r"\btemperature\b", re.I), "deposition_temperature", "°C"),
]

#: printed figure numbers as they appear at the head of a caption in the document
_CAPTION_HEAD = re.compile(r"(?:Figure|Fig\.?|FIG\.?)\s*(\d{1,2})\b(?!\d)")


def _norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def missing_panels(paper):
    """Caption panels that describe a measurement and have no extracted entity.

    `paper` is a pilot_semantics.Paper. Returns a list of supplement records.
    """
    covered = set()
    for e in paper.entities:
        pf = str(e.get("printed_figure_number") or "")
        if pf:
            covered.add((pf, (e.get("panel") or "").lower()))
    # Printed figures that have a crop, PLUS printed figures that appear only as a
    # caption in the document. A figure whose caption the production parser rejected has
    # no crop at all, so scanning crops alone can never find it — which is exactly how a
    # whole printed figure of data goes missing without leaving a trace.
    from_crops = set(paper._printed.values())
    from_doc = set(_CAPTION_HEAD.findall(paper.md))
    printed = sorted(from_crops | from_doc, key=lambda x: (len(x), x))
    out = []
    for pf in printed:
        cap = paper.printed_caption(pf)
        if not cap:
            continue
        clauses = PE.panel_clauses(cap)
        for panel, clause in sorted(clauses.items()):
            if not panel or (pf, panel) in covered:
                continue
            if _NON_PLOT.search(clause) or not _MEASUREMENT_CLAUSE.search(clause):
                continue
            out.append({
                "paper_id": paper.pid, "printed_figure": pf, "panel": panel,
                "caption_clause": _norm(clause)[:400],
                "techniques": [t["technique"] for t in PE.techniques(clause)],
                "cause": None, "data_recovered": False,
                "reason": "the printed caption describes a plotted measurement for this "
                          "panel and no extracted entity covers it",
            })
    return out


def image_supported_cases(paper, note=None):
    """Figures whose caption reports a deposition on a described structure.

    Yields one record per such figure holding the case-defining conditions the caption
    states and the geometry it describes. No x-y points are produced and none are claimed:
    the record exists because the paper documents the experiment, not because a curve was
    digitised.
    """
    import pilot_ranges as PRG
    import pilot_roles as R
    covered = {str(e.get("printed_figure_number")) for e in paper.entities
               if e.get("printed_figure_number")}
    from_doc = set(_CAPTION_HEAD.findall(paper.md))
    out = []
    for pf in sorted((set(paper._printed.values()) | from_doc) - covered,
                     key=lambda x: (len(x), x)):
        cap = paper.printed_caption(pf)
        if not cap or not _DEPOSITION_CLAUSE.search(cap):
            continue
        conds = PRG.quantities_from_text(cap, DEPOSITION_HINTS)
        roles = R.material_roles(cap, paper.materials)
        deposited = [m for m, recs in roles.items()
                     if R.primary_role(recs) == R.DEPOSITED]
        # A deposition case needs a deposited material AND a process condition. Without
        # the material requirement a device-cycling caption ("stability … for over 10 000
        # cycles") reads as an ALD cycle count, which is a different quantity entirely.
        if not conds or not deposited:
            continue
        gc, gmatch = R.geometry_in_scope(cap)
        out.append({
            "paper_id": paper.pid, "printed_figure": pf, "caption": cap[:600],
            "conditions": conds, "material_roles": {m: R.primary_role(v)
                                                    for m, v in roles.items()},
            "deposited_materials": sorted(deposited),
            "geometry": gc, "geometry_evidence": gmatch,
            "techniques": [t["technique"] for t in PE.techniques(cap)],
            "data_recovered": False,
            "evidence_kind": "caption_and_image",
            "reason": ("the caption reports a deposition on a described structure and "
                       "states its process conditions; the figure's evidence is an image, "
                       "so no x-y points exist or are claimed"),
        })
    return out


def classify_cause(paper, supplements):
    """Why each missing panel is missing: a rejected caption, or an absent crop."""
    inv = paper.inventory or {}
    cands = inv.get("candidates") or []
    bound_figs = {str(c.get("printed_figure")) for c in cands if c.get("printed_figure")}
    for s in supplements:
        pf = s["printed_figure"]
        if pf not in bound_figs:
            s["cause"] = "caption_not_associated"
            s["cause_detail"] = ("no crop of this printed figure carries a caption, so the "
                                 "figure never reached the extraction stage")
        else:
            crops = [c for c in cands if str(c.get("printed_figure")) == pf]
            s["cause"] = "panel_absent_from_crop"
            s["cause_detail"] = ("printed figure %s has %d crop(s) and they cover panel(s) "
                                 "%s; no PictureItem exists for panel (%s)"
                                 % (pf, len(crops),
                                    sorted({str(c.get("panel")) for c in crops}), s["panel"]))
    return supplements


def render_page(pdf_path, printed_figure, caption_text, outdir, dpi=150):
    """Render the PDF page that carries a figure's caption, as local visual evidence.

    Page-level, not panel-level: cropping to a panel would require locating it, and a
    wrong crop is worse evidence than the whole page. No API involved.
    """
    try:
        import fitz
    except ImportError:
        return None, "PyMuPDF unavailable"
    doc = fitz.open(str(pdf_path))
    probe = _norm(caption_text)[:60]
    if not probe:
        return None, "no caption text to locate"
    for pno in range(doc.page_count):
        text = _norm(doc[pno].get_text())
        if probe[:40] and probe[:40] in text:
            page = doc[pno]
            pix = page.get_pixmap(dpi=dpi)
            Path(outdir).mkdir(parents=True, exist_ok=True)
            name = "supplement_fig%s_p%d.png" % (re.sub(r"\W", "", printed_figure), pno + 1)
            pix.save(str(Path(outdir) / name))
            return name, "PDF page %d rendered at %d dpi (local, no API)" % (pno + 1, dpi)
    return None, "caption text not located in the PDF"


def build(paper, assets_dir):
    """All supplements for one paper, with their local page renders."""
    sup = classify_cause(paper, missing_panels(paper))
    pdfs = sorted((paper.root / "source").glob("*.pdf"))
    for s in sup:
        s["measurement_id"] = "M::SUP::%s::F%s%s" % (paper.pid, s["printed_figure"], s["panel"])
        s["result_series_ids"] = []
        s["evidence_kind"] = "caption_only"
        if pdfs:
            img, why = render_page(pdfs[0], s["printed_figure"],
                                   paper.printed_caption(s["printed_figure"]), assets_dir)
            s["page_render"] = img
            s["page_render_note"] = why
    (paper.root / "diagnostics").mkdir(parents=True, exist_ok=True)
    (paper.root / "diagnostics" / "supplements.json").write_text(
        json.dumps(sup, indent=1, ensure_ascii=False))
    return sup
