#!/usr/bin/env python3
"""
build_canonical.py — post-process the existing figure-derived JSON into a
comparison-ready canonical layer.

Reads (read-only):
    papers/{doi}/extracted/figure_data.json  + records/card/geometry/pressure/document
    papers/{doi}/extracted/recovery/figure_semantics_v1.json   (if built)
    papers/{doi}/resolved/experiments.json

Writes (new files only — no raw file is touched):
    papers/{doi}/canonical/curves.json

Usage:
    python3 02_extraction/canonical/build_canonical.py --all
    python3 02_extraction/canonical/build_canonical.py --paper 10.1039_d0cp03358h
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "canonical"

from . import sources as S                                    # noqa: E402
from . import axis_semantics as AX                            # noqa: E402
from .canonicalize import canonicalize_axis                   # noqa: E402
from .schema import REPO, code_version, build_timestamp       # noqa: E402


def curve_id(c):
    """Deterministic across rebuilds: derived only from source coordinates."""
    return "%s::F%s::%s::%d" % (c["doi"], c["figure_number"], c["panel"] or "-",
                                c["series_index"])


def build_curve(c):
    sem_x = AX.resolve_x_axis(c["x_raw"].get("quantity"), c["x_raw"].get("unit"),
                              c["x_label"], c["texts_x"])
    sem_y = AX.resolve_y_axis(c["y_raw"].get("quantity"), c["y_raw"].get("unit"),
                              c["y_label"], c["texts_y"])
    pool = S.build_context_pool(c["doi"], c["_fig"], c["_panel"], c["_series"],
                                c.get("experiment"))

    can_x, proj_x, tr_x = canonicalize_axis(c, "x", sem_x, pool)
    can_y, proj_y, tr_y = canonicalize_axis(c, "y", sem_y, pool)

    representation, gran_reason = AX.resolve_granularity(sem_x, len(c["points"]))
    prev = (c.get("experiment") or {}).get("granularity")

    return {
        "curve_id": curve_id(c),
        "source": {
            "paper_id": c["doi"], "doi": c["doi"],
            "figure": c["figure_number"], "figure_index": c["figure"],
            "panel": c["panel"], "series": c.get("series_label"),
            "series_index": c["series_index"], "series_axis": c.get("series_axis"),
            "source_file": c["source_file"],
            "json_pointer": c["json_pointer"],
            "source_checksum": c["source_checksum"],
            "linked_experiment_ids": [c["experiment_id"]] if c.get("experiment_id") else [],
            "data_source": c.get("panel_source") or c.get("source"),
            "caption": c.get("caption"),
        },
        # RAW: copied verbatim from figure_data.json, never modified
        "raw": {
            "x": {"label": c["x_label"], "quantity": c["x_raw"].get("quantity"),
                  "unit": c["x_raw"].get("unit"), "log": c["x_raw"].get("log")},
            "y": {"label": c["y_label"], "quantity": c["y_raw"].get("quantity"),
                  "unit": c["y_raw"].get("unit"), "log": c["y_raw"].get("log")},
            "points": c["points"],
        },
        "semantics": {"x": sem_x, "y": sem_y},
        "canonical": {"x": can_x, "y": can_y},
        "projections": {"x": proj_x, "y": proj_y},
        "transformations": tr_x + tr_y,
        "granularity": {
            "axis_role": sem_x.get("axis_role"),
            "previous_representation": prev,
            "resolved_representation": representation,
            "changed": bool(prev and _norm_rep(prev) != _norm_rep(representation)),
            "reason": gran_reason,
            "n_points": len(c["points"]),
        },
        "context_available": pool.quantities(),
    }


def _norm_rep(r):
    return {"profile": "profile", "single": "single", "series": "series",
            "correlation": "correlation", "unresolved": "unresolved"}.get(r, r)


def build_paper(doi, out_root=None):
    curves = [build_curve(c) for c in S.iter_curves(doi)]
    out_root = out_root or (REPO / "papers")
    outdir = Path(out_root) / doi / "canonical"
    outdir.mkdir(parents=True, exist_ok=True)
    doc = {
        "doi": doi,
        "generator": "02_extraction/canonical/build_canonical.py",
        "code_version": code_version(),
        "created_at": build_timestamp(),
        "ontology": "01_ontology/ald_ontology.json",
        "n_curves": len(curves),
        "curves": curves,
    }
    (outdir / "curves.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="every paper in the manifest")
    ap.add_argument("--paper", action="append", default=[], help="one paper id (repeatable)")
    a = ap.parse_args(argv)
    ids = a.paper or (S.papers() if a.all else [])
    if not ids:
        ap.error("pass --all or --paper <id>")
    total = 0
    for doi in ids:
        if not S.paper_paths(doi)["figure_data"].exists():
            print("  %-38s no figure_data.json — skipped" % doi)
            continue
        doc = build_paper(doi)
        total += doc["n_curves"]
        print("  %-38s %4d curves" % (doi, doc["n_curves"]))
    print("\nwrote canonical curves for %d paper(s), %d curves total" % (len(ids), total))
    print("-> papers/<doi>/canonical/curves.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
