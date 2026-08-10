#!/usr/bin/env python3
"""
reextract_figures.py — Stage D, part 2: SELECTIVE figure re-extraction.

Only the figures flagged by recover_axis_semantics.py are re-read, and only
their AXIS METADATA is re-read. Digitized points are never re-requested and
never replaced (spec §8.2): the historical extraction dropped verbatim axis
labels, not the data.

Improved schema (spec §2.1) — per axis:
    label_raw, unit_raw, unit_normalized, is_normalized,
    normalization_expression, normalization_denominator_symbol,
    axis_scale, annotations, plus series/legend mapping per panel.

Output (new file, never overwrites figure_data.json):
    papers/{doi}/extracted/recovery/figure_semantics_v1.json

build_canonical.py picks that file up automatically and uses `label_raw` as
evidence source 1.

Needs the psed310 environment (google-genai) and 03_corpus/config/.env:
    /home/ftk3187/miniconda3/envs/psed310/bin/python \
        02_extraction/canonical/reextract_figures.py --priority high
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "canonical"

from . import sources as S                                     # noqa: E402
from .schema import REPO, code_version, build_timestamp        # noqa: E402

REPORTS = REPO / "reports" / "canonical"
CANDIDATES = REPORTS / "reextraction_candidates.json"
MODEL = os.environ.get("PSED_VISION_MODEL", "gemini-flash-latest")
MAX_PX = 1100

SCHEMA = """You are re-reading ONE figure from an ALD paper. Your ONLY job is to
transcribe the AXIS METADATA VERBATIM. Do NOT digitize data points.

Return ONLY JSON:
{"panels":[
  {"panel":"a",
   "x":{"label_raw":"<the x-axis label EXACTLY as printed, including any
            expression and unit, e.g. 'x/H', 'x̃ = x/H', 'Distance (µm)',
            'GPC (Å/cycle)'. Transcribe symbols faithfully. Empty string if
            the axis genuinely has no label.>",
        "unit_raw":"<ONLY the unit as printed, e.g. 'µm', 'Å/cycle', '' if the
            axis is dimensionless or unlabelled>",
        "is_normalized":true|false,
        "normalization_expression":"<the ratio EXACTLY as printed if the axis is
            a normalized/dimensionless quantity, e.g. 'x/H', 'x/L', 't(x)/t(0)',
            't/tmax'. null if not normalized.>",
        "normalization_denominator_symbol":"<just the denominator symbol, e.g.
            'H', 'L', 'D_h', 't(0)', 'tmax'. null if not normalized.>",
        "axis_scale":"linear"|"log"},
   "y":{ ...same fields... },
   "series_legend":[{"label":"<curve label verbatim>",
                     "condition":"<what that label means, if the legend or an
                        axis title says so, e.g. '500 nm channel height'; null
                        otherwise>"}],
   "annotations":["<any text printed inside the plot area that states a
        condition or a definition, verbatim>"]
  }
]}

RULES:
- Transcribe, do not interpret. If the axis reads 'x/H', return 'x/H' — do NOT
  expand it to 'distance divided by feature height'.
- If you cannot read a label, return null for it. NEVER invent a label, a unit,
  or a denominator.
- normalization_denominator_symbol must be a symbol that is actually PRINTED on
  the axis or in the plot. If the axis just says 'Normalized thickness' with no
  ratio shown, return is_normalized true and BOTH normalization fields null.
- Return one entry for EVERY panel present in the image, using the printed panel
  letters. Do not invent or omit panels.
- Do NOT return data points."""


def _load_key():
    for line in (REPO / "03_corpus" / "config" / ".env").read_text().splitlines():
        if line.startswith("GOOGLE_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_API_KEY")


def _downscaled_png(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if max(im.size) > MAX_PX:
        r = MAX_PX / max(im.size)
        im = im.resize((int(im.size[0] * r), int(im.size[1] * r)))
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def _call(client, image_bytes, caption):
    from google.genai import types
    prompt = SCHEMA + "\n\nFIGURE CAPTION (context, may name the normalization):\n" + (caption or "")
    resp = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/png"), prompt],
        config=types.GenerateContentConfig(temperature=0,
                                           response_mime_type="application/json"))
    txt = (resp.text or "").replace("```json", "").replace("```", "").strip()
    data = json.loads(txt)
    # the model sometimes returns the bare panel list instead of {"panels": [...]}
    if isinstance(data, list):
        data = {"panels": data}
    if not isinstance(data, dict):
        raise ValueError("unexpected response shape: %s" % type(data).__name__)
    return data


def reextract(doi, figures, client, dry_run=False, resume=True):
    """figures: [{figure, figure_index, image, panels, reasons}] for ONE paper."""
    paths = S.paper_paths(doi)
    base = paths["figure_data"].parent
    out_path = base / "recovery" / "figure_semantics_v1.json"
    existing = {}
    if out_path.exists():
        prev = json.loads(out_path.read_text())
        existing = {(str(p.get("figure")), str(p.get("panel") or "")): p
                    for p in prev.get("panels", [])}

    fd = json.loads(paths["figure_data"].read_text())
    cap_by_index = {str(f.get("figure")): f.get("caption") for f in fd.get("figures", [])}

    panels_out = list(existing.values())
    done_figs = {str(p.get("figure_index")) for p in panels_out}
    calls = 0
    for fig in figures:
        if resume and str(fig["figure_index"]) in done_figs:
            continue                       # already recovered; do not re-bill the call
        img = base / (fig.get("image") or "")
        if not fig.get("image") or not img.exists():
            print("     ! %s fig %s: image missing (%s)" % (doi, fig["figure"], fig.get("image")))
            continue
        if dry_run:
            calls += 1
            continue
        try:
            data = _call(client, _downscaled_png(img), cap_by_index.get(str(fig["figure_index"])))
            calls += 1
        except Exception as exc:
            print("     ! %s fig %s: %s: %s" % (doi, fig["figure"], type(exc).__name__, str(exc)[:120]))
            continue
        for p in data.get("panels", []) or []:
            rec = {
                "figure": str(fig["figure"]),
                "figure_index": str(fig["figure_index"]),
                "panel": str(p.get("panel") or "").strip().lower(),
                "x": p.get("x") or {},
                "y": p.get("y") or {},
                "series_legend": p.get("series_legend") or [],
                "annotations": p.get("annotations") or [],
                "recovery": {
                    "method": "selective_vision_reextraction",
                    "model": MODEL,
                    "source": "figure_image",
                    "source_file": S.rel(img),
                    "source_location": "figure %s panel %s" % (fig["figure"], p.get("panel")),
                    "triggered_by": fig.get("reasons"),
                    "automatic": True,
                    "points_replaced": False,
                },
            }
            key = (rec["figure"], rec["panel"])
            panels_out = [q for q in panels_out
                          if (str(q.get("figure")), str(q.get("panel") or "")) != key]
            panels_out.append(rec)
        time.sleep(0.4)

    if dry_run:
        return calls, 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "doi": doi,
        "schema_version": 1,
        "kind": "selective_figure_axis_reextraction",
        "generator": "02_extraction/canonical/reextract_figures.py",
        "model": MODEL,
        "code_version": code_version(),
        "created_at": build_timestamp(),
        "note": ("Axis METADATA only. Digitized points are NOT re-read and NOT "
                 "replaced; figure_data.json is never modified."),
        "n_panels": len(panels_out),
        "panels": panels_out,
    }, indent=1, ensure_ascii=False))
    return calls, len(panels_out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--priority", default="high",
                    choices=["high", "medium", "low", "all"],
                    help="which flagged tier to re-extract (default: high)")
    ap.add_argument("--paper", action="append", default=[])
    ap.add_argument("--limit", type=int, default=None, help="max figures (cost guard)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-resume", action="store_true",
                    help="re-run figures already present in figure_semantics_v1.json")
    a = ap.parse_args(argv)

    if not CANDIDATES.exists():
        ap.error("run recover_axis_semantics.py --all first (%s missing)" % CANDIDATES)
    cand = json.loads(CANDIDATES.read_text())
    figs = [f for f in cand["figures"]
            if (a.priority == "all" or f["priority"] == a.priority)
            and (not a.paper or f["doi"] in a.paper)]
    if a.limit:
        figs = figs[:a.limit]
    if not figs:
        print("no figures match the filter")
        return 0

    client = None
    if not a.dry_run:
        try:
            from google import genai
        except ImportError:
            print("ERROR: google-genai is not installed in this interpreter.\n"
                  "Re-run with the psed310 environment:\n"
                  "  /home/ftk3187/miniconda3/envs/psed310/bin/python %s"
                  % " ".join(sys.argv))
            return 2
        client = genai.Client(api_key=_load_key())

    by_paper = {}
    for f in figs:
        by_paper.setdefault(f["doi"], []).append(f)

    total_calls, total_panels, log = 0, 0, []
    for doi, fl in sorted(by_paper.items()):
        calls, npanels = reextract(doi, fl, client, a.dry_run, resume=not a.no_resume)
        total_calls += calls
        total_panels += npanels
        log.append({"doi": doi, "figures": [f["figure"] for f in fl],
                    "vision_calls": calls, "panels_recovered": npanels,
                    "reasons": sorted({r for f in fl for r in f["reasons"]})})
        print("  %-38s %2d figure(s) -> %d call(s), %d panel record(s)"
              % (doi, len(fl), calls, npanels))

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "reextracted_figures.json").write_text(json.dumps({
        "priority": a.priority, "dry_run": a.dry_run, "model": MODEL,
        "code_version": code_version(),
        "figures_selected": len(figs), "papers": len(by_paper),
        "vision_calls": total_calls, "panel_records": total_panels,
        "papers_detail": log,
        "selection_rule": ("only figures whose blocked axis semantics prevent a "
                           "comparison group; points are never re-read"),
    }, indent=1, ensure_ascii=False))
    print("\n%d figure(s), %d vision call(s), %d panel record(s)"
          % (len(figs), total_calls, total_panels))
    print("-> %s" % (REPORTS / "reextracted_figures.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
