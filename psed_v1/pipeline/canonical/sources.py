"""
canonical/sources.py — read-only access to the existing corpus JSON.

Nothing in this module writes. It assembles, per digitized curve:

  * the RAW axis metadata and points, plus a JSON pointer and file checksum so
    the canonical record can be traced back to the exact source slice;
  * the prioritised TEXT EVIDENCE list used for axis-semantic recovery
    (axis label -> caption -> panel text -> figure discussion -> equations);
  * a scope-tagged ContextPool (panel/curve/figure/experiment/method/paper).

Inputs (all pre-existing):
    papers/{doi}/extracted/figure_data.json    panels, axes, series, points
    papers/{doi}/extracted/records.json        flattened curves (keeps coordinate_unit)
    papers/{doi}/extracted/card.json           paper-level process card
    papers/{doi}/extracted/geometry.json       geometry quantities (paper scope)
    papers/{doi}/extracted/pressure.json       pressure observations
    papers/{doi}/extracted/document.md         parsed full text
    papers/{doi}/extracted/structure.json      figure/section structure
    papers/{doi}/extracted/recovery/figure_semantics_v1.json   (optional, Stage D)
    papers/{doi}/resolved/experiments.json          resolved experiments
"""
from __future__ import annotations
import paths as P

import hashlib
import json
import re
from pathlib import Path

from pipeline.figures.figure_extract import effective_axis
from .context import ContextPool
from .schema import REPO

CORPUS = P.PAPERS
OUTPUT = P.PAPERS
MANIFEST = P.REPORTS / "extraction_runs" / "extraction_manifest.json"

_CACHE = {}


def _read_json(path):
    key = str(path)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.loads(Path(path).read_text())
        except Exception:
            _CACHE[key] = None
    return _CACHE[key]


def checksum(path):
    p = Path(path)
    if not p.exists():
        return None
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except Exception:
        return str(path)


def papers():
    """Corpus paper ids — the papers that exist on disk with an extraction.

    This used to read reports/extraction_runs/extraction_manifest.json and call it
    "the authoritative list". That file is the frozen log of a July extraction run:
    its input_paths still point at the pre-refactor extracted/<doi>/ layout, and it
    has no entry for a paper added since. Because every downstream stage resolves its
    corpus through this function, a paper missing from that log was silently absent
    from resolve, canonical, the KG and every report no matter how much data it
    contributed -- cremers2019 has 93 source series and appeared nowhere. The live
    corpus is the filesystem; the manifest stays where it is as run provenance.
    """
    return P.papers()


def paper_paths(doi):
    d = P.extracted_dir(doi)
    return {
        "figure_data": d / "figure_data.json",
        "records": d / "records.json",
        "card": d / "card.json",
        "geometry": d / "geometry.json",
        "pressure": d / "pressure.json",
        "scout": d / "scout.json",
        "structure": d / "structure.json",
        "document": d / "document.md",
        "figures_dir": d / "figures",
        "recovery": d / "recovery" / "figure_semantics_v1.json",
        "experiments": P.resolved_json(doi, "experiments"),
    }


# --- document text --------------------------------------------------------
_DOC_CACHE = {}


def document_text(doi):
    p = paper_paths(doi)["document"]
    if doi not in _DOC_CACHE:
        try:
            _DOC_CACHE[doi] = p.read_text(errors="replace")
        except Exception:
            _DOC_CACHE[doi] = ""
    return _DOC_CACHE[doi]


def figure_discussion(doi, figure_number, window=900):
    """Text around every in-text mention of 'Fig. N' — spec evidence source 4."""
    text = document_text(doi)
    if not text or figure_number is None:
        return ""
    rx = re.compile(r"[Ff]ig(?:ure)?s?\.?\s*%s(?![0-9])" % re.escape(str(figure_number)))
    chunks = []
    for m in rx.finditer(text):
        chunks.append(text[max(0, m.start() - window // 3): m.end() + window])
        if len(chunks) >= 6:
            break
    return "\n---\n".join(chunks)


def equation_context(doi):
    """Lines that define a symbol via '=' plus a ratio — spec evidence source 5.
    Kept narrow so it does not become a full-text grep."""
    text = document_text(doi)
    if not text:
        return ""
    out = []
    for line in text.splitlines():
        if "=" in line and "/" in line and len(line) < 400:
            if re.search(r"(?:x|z|t|d|S|GPC)\s*(?:\(|_|̃|~)?", line):
                out.append(line.strip())
        if len(out) >= 120:
            break
    return "\n".join(out)


# --- recovery overlay -----------------------------------------------------
def recovery_index(doi):
    """{(figure_key, panel): axis-recovery record} from the Stage-D output.

    Returns {"by_docling": {...}, "by_printed": {...}} -- two SEPARATE
    namespaces.

    They used to share one dict, keyed under both numbers at once. The two
    numbering systems differ (in 10.1002_pssa.201532305 printed 5 is docling 7,
    printed 7 is docling 9), so a lookup of printed "7" collided with docling
    "7" and silently returned a different figure's axis labels -- which is how
    an XPS depth profile acquired the axes of an in-situ thickness trace.
    Callers must look up with the key type they actually hold.
    """
    rec = _read_json(paper_paths(doi)["recovery"])
    if not rec:
        return {"by_docling": {}, "by_printed": {}}
    by_docling, by_printed = {}, {}
    for e in rec.get("panels", []) or []:
        panel = str(e.get("panel") or "")
        if e.get("figure_index") is not None:
            by_docling.setdefault((str(e["figure_index"]), panel), e)
        if e.get("figure") is not None:
            by_printed.setdefault((str(e["figure"]), panel), e)
    return {"by_docling": by_docling, "by_printed": by_printed}


# --- resolved experiments -------------------------------------------------
def experiments(doi):
    return _read_json(paper_paths(doi)["experiments"]) or []


def experiment_index(doi):
    """(figure_number, panel) -> [experiment, ...] in figure order."""
    idx = {}
    for e in experiments(doi):
        p = e.get("provenance") or {}
        key = (str(p.get("figure_number") or ""), str(p.get("panel") or ""))
        idx.setdefault(key, []).append(e)
    return idx


# --- numeric parsing ------------------------------------------------------
_NUM_UNIT = re.compile(r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(.*?)\s*$")


def split_value_unit(raw):
    """'10 s' -> (10.0, 's'); '500' -> (500.0, None); 'high' -> (None, None)."""
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    m = _NUM_UNIT.match(str(raw))
    if not m:
        return None, None
    try:
        val = float(m.group(1))
    except ValueError:
        return None, None
    unit = (m.group(2) or "").strip() or None
    return val, unit


# =========================================================================
# context pool assembly
# =========================================================================
def build_context_pool(doi, fig, panel, series, experiment):
    """Scope-tagged context for ONE curve.

    Scope assignment is deliberate:
      curve      <- this series' own label (numeric sweep value)
      panel      <- figure_data panel.conditions (held fixed in this panel)
      figure     <- numbers stated in the caption
      experiment <- resolved conditions whose origin.level == 'experiment'
      method     <- card.json / methods-derived conditions
      paper      <- geometry.json + paper-level card conditions
    """
    pool = ContextPool()
    paths = paper_paths(doi)
    fd_file = rel(paths["figure_data"])

    # --- curve scope: the series' own label -----------------------------
    label = (series or {}).get("label")
    if label:
        for qid, val, unit in _parse_label_quantities(label):
            pool.add(qid, val, unit, "curve", fd_file,
                     "figure %s panel %s series %r" % (fig.get("figure"), panel.get("panel"), label),
                     evidence=label, confidence=0.9,
                     origin={"from": "series_label"})

    # --- panel scope: conditions held fixed in this panel ----------------
    for k, v in (panel.get("conditions") or {}).items():
        qid = _canon(k)
        val, unit = split_value_unit(v)
        if qid and val is not None:
            pool.add(qid, val, unit, "panel", fd_file,
                     "figure %s panel %s conditions.%s" % (fig.get("figure"), panel.get("panel"), k),
                     evidence="%s = %s" % (k, v), confidence=0.9,
                     origin={"from": "panel_conditions"})

    # --- figure scope: numbers stated in the caption ---------------------
    for qid, val, unit, span in _parse_caption_quantities(fig.get("caption") or ""):
        pool.add(qid, val, unit, "figure", fd_file,
                 "figure %s caption" % fig.get("figure"),
                 evidence=span, confidence=0.75, origin={"from": "figure_caption"})

    # --- experiment / method / paper scope from the resolved record ------
    if experiment:
        exp_file = rel(paths["experiments"])
        for c in experiment.get("controlled") or []:
            qid, val, unit = c.get("quantity"), c.get("value"), c.get("unit")
            if qid is None or val is None:
                continue
            origin = c.get("origin") or {}
            lvl = origin.get("level")
            src = c.get("source")
            if lvl == "experiment":
                scope = "experiment"
            elif src in ("methods", "card"):
                scope = "method"
            else:
                scope = "paper"
            pool.add(qid, val, unit, scope, exp_file,
                     "%s controlled[%s] (origin.level=%s, source=%s)"
                     % (experiment.get("exp_id"), qid, lvl, src),
                     evidence=origin.get("evidence") or origin.get("raw_label"),
                     confidence=0.8 if scope == "paper" else 0.9, origin=origin)
    return pool


_CANON_CACHE = {}


def _canon(name):
    from .axis_semantics import canon_quantity
    if name not in _CANON_CACHE:
        _CANON_CACHE[name] = canon_quantity(name)
    return _CANON_CACHE[name]


# Series labels like '2000 nm', '500 cycles', '150 °C' name the swept condition
# deterministically. Unit -> quantity mapping only; never a bare number.
_LABEL_UNITS = [
    (re.compile(r"([-+]?[0-9]*\.?[0-9]+)\s*(nm|µm|um|μm|mm)\b", re.I), "feature_height"),
    (re.compile(r"([-+]?[0-9]*\.?[0-9]+)\s*cycles?\b", re.I), "cycle_number"),
    (re.compile(r"([-+]?[0-9]*\.?[0-9]+)\s*(?:°|deg\s*)?C\b"), "deposition_temperature"),
    (re.compile(r"([-+]?[0-9]*\.?[0-9]+)\s*(s|ms|min)\b", re.I), "pulse_time"),
]


def _parse_label_quantities(label):
    out = []
    for rx, qid in _LABEL_UNITS:
        m = rx.search(str(label))
        if m:
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            if qid == "deposition_temperature":
                unit = "°C"
            elif qid == "cycle_number":
                unit = "cycle"
            out.append((qid, val, unit))
    return out


# Caption phrases that state a geometry/cycle value for the whole figure.
_CAPTION_RULES = [
    (re.compile(r"channel height\s*H?\s*(?:of|=|:)?\s*([-+]?[0-9]*\.?[0-9]+)\s*(nm|µm|um|μm|mm)", re.I),
     "feature_height"),
    (re.compile(r"(?:feature|trench|via)\s+(?:height|depth)\s*(?:of|=|:)?\s*([-+]?[0-9]*\.?[0-9]+)\s*(nm|µm|um|μm|mm)", re.I),
     "feature_height"),
    (re.compile(r"channel length\s*L?\s*(?:of|=|:)?\s*([-+]?[0-9]*\.?[0-9]+)\s*(nm|µm|um|μm|mm)", re.I),
     "feature_length"),
    (re.compile(r"(?:constant\s+)?number of cycles\s*N?\s*(?:of|=|:)?\s*([-+]?[0-9]*\.?[0-9]+)", re.I),
     "cycle_number"),
    (re.compile(r"([-+]?[0-9]*\.?[0-9]+)\s*(?:ALD\s+)?cycles\b", re.I), "cycle_number"),
]


def _parse_caption_quantities(caption):
    out = []
    for rx, qid in _CAPTION_RULES:
        for m in rx.finditer(caption):
            try:
                val = float(m.group(1))
            except (ValueError, IndexError):
                continue
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else (
                "cycle" if qid == "cycle_number" else None)
            span = caption[max(0, m.start() - 30):m.end() + 30].strip()
            out.append((qid, val, unit, span))
    return out


# =========================================================================
# curve iteration
# =========================================================================
def iter_curves(doi):
    """Yield one dict per digitized curve, with raw axes, points, locator,
    checksum, text-evidence list and the linked resolved experiment."""
    paths = paper_paths(doi)
    fd = _read_json(paths["figure_data"])
    if not fd:
        return
    fd_file = rel(paths["figure_data"])
    fd_sum = checksum(paths["figure_data"])
    recov = recovery_index(doi)
    exp_idx = experiment_index(doi)
    doc_file = rel(paths["document"])

    for fi, fig in enumerate(fd.get("figures", []) or []):
        fignum = str(fig.get("figure"))
        caption = fig.get("caption") or ""
        discussion = figure_discussion(doi, _paper_fignum(caption) or fignum)
        equations = equation_context(doi)
        doc_text = document_text(doi)
        for pi, panel in enumerate(fig.get("panels", []) or []):
            pname = str(panel.get("panel") or "")
            x = dict(panel.get("x") or {})
            y = dict(panel.get("y") or {})
            # `fignum` is figure_data's own key, i.e. the DOCLING index
            rec = recov["by_docling"].get((fignum, pname)) or {}
            # recovered verbatim labels take priority as evidence source 1
            x_label = rec.get("x", {}).get("label_raw") or x.get("label_raw") or x.get("label")
            y_label = rec.get("y", {}).get("label_raw") or y.get("label_raw") or y.get("label")
            panel_caption = _panel_caption(caption, pname)

            # Evidence order. The PANEL clause is tried before the whole-figure
            # caption: it is a strictly narrower slice of the same source, and a
            # multi-panel caption naming several different normalizations ("(c)
            # ... x/H ... (d) ... x/L") must resolve per panel rather than come
            # back ambiguous for every panel in the figure.
            def _texts(axis_label, axis):
                return [t for t in [
                    ("axis_label", rel(paths["recovery"]) if rec else fd_file,
                     "figure %s panel %s %s.label_raw" % (fignum, pname, axis), axis_label),
                    ("panel_caption", fd_file,
                     "figure %s panel %s caption clause" % (fignum, pname), panel_caption),
                    ("figure_caption", fd_file, "figure %s caption" % fignum, caption),
                    ("document_text", doc_file, "figure %s discussion" % fignum, discussion),
                    ("equations", doc_file, "equation lines", equations),
                    # whole-paper text, consumed ONLY by the symbol-definition
                    # path (a targeted "<symbol> = <ratio>" match). A paper
                    # defines its dimensionless variables once, usually far from
                    # the figure that plots them.
                    ("document_symbol_definition", doc_file,
                     "symbol definition in document.md", doc_text),
                ] if t[3]]

            texts_x = _texts(x_label, "x")
            texts_y = _texts(y_label, "y")

            exps = exp_idx.get((_paper_fignum(caption) or fignum, pname)) or \
                exp_idx.get((fignum, pname)) or []
            for si, series in enumerate(panel.get("series", []) or []):
                pts = [p for p in (series.get("points") or [])
                       if isinstance(p, (list, tuple)) and len(p) == 2]
                exp = exps[si] if si < len(exps) else (exps[0] if exps else None)
                # A curve is read against ONE axis. That is the panel's axis unless the
                # figure shows this curve on its own, in which case the series carries it.
                s_x, x_is_own = effective_axis(x, series.get("x"))
                s_y, y_is_own = effective_axis(y, series.get("y"))
                # A series that owns its axis owns its LABEL too: the panel's recovered
                # label describes the panel axis and would otherwise be re-applied to a
                # curve that was never read against it.
                s_x_label = (s_x.get("label_raw") or s_x.get("label")) if x_is_own \
                    else x_label
                s_y_label = (s_y.get("label_raw") or s_y.get("label")) if y_is_own \
                    else y_label
                s_texts_x = _texts(s_x_label, "x") if x_is_own else texts_x
                s_texts_y = _texts(s_y_label, "y") if y_is_own else texts_y
                yield {
                    "doi": doi,
                    "figure": fignum,
                    "figure_number": _paper_fignum(caption) or fignum,
                    "panel": pname,
                    "series_index": si,
                    "series_label": series.get("label"),
                    "series_axis": panel.get("series_axis"),
                    "caption": caption,
                    "panel_caption": panel_caption,
                    "x_raw": s_x, "y_raw": s_y,
                    "x_label": s_x_label, "y_label": s_y_label,
                    "x_axis_scope": "series" if x_is_own else "panel",
                    "y_axis_scope": "series" if y_is_own else "panel",
                    "recovery": rec or None,
                    "points": pts,
                    "source_file": fd_file,
                    "source_checksum": fd_sum,
                    "json_pointer": "/figures/%d/panels/%d/series/%d" % (fi, pi, si),
                    "texts_x": s_texts_x, "texts_y": s_texts_y,
                    "experiment": exp,
                    "experiment_id": (exp or {}).get("exp_id"),
                    "source": fig.get("source"),
                    "panel_source": (fig.get("panel_source") or {}).get(pname),
                    "_fig": fig, "_panel": panel, "_series": series,
                }


def _paper_fignum(caption):
    """The paper's own figure number from the caption ('FIG. 4. ...' -> '4').
    figure_data's `figure` key is the docling index, not the printed number."""
    m = re.match(r"\s*(?:FIG|Fig|Figure|FIGURE)\.?\s*([0-9]+)", caption or "")
    return m.group(1) if m else None


def _panel_caption(caption, panel):
    """The '(c) ...' clause of a multi-panel caption — spec evidence source 3."""
    if not caption or not panel:
        return ""
    rx = re.compile(r"\(\s*%s\s*\)" % re.escape(panel), re.I)
    m = rx.search(caption)
    if not m:
        return ""
    nxt = re.compile(r"\(\s*[a-h]\s*\)", re.I).search(caption, m.end())
    return caption[m.start(): nxt.start() if nxt else len(caption)].strip()
