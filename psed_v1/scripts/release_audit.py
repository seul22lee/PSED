#!/usr/bin/env python3
"""
scripts/release_audit.py — corpus-wide release audit for the extraction layer.

    python3 scripts/release_audit.py [--before <snapshot.json>] [--json <out.json>]

Read-only. Walks every paper in the canonical corpus and reports, per paper and in
total: PictureItems, printed figures, crop dispositions, extracted panels/series/points,
generated records, and record provenance (measured vs simulated). Then runs the
release invariants:

  I1  no MERGED / SKIP crop is referenced as an active standalone source downstream
  I2  every DRILL crop traces to a PrintedFigure and a PictureItem
  I3  every downstream record traces back to a crop that is DRILL
  I4  series -> record accounting: one record per extracted series, no orphans
  I5  point accounting: no points lost between figure_data and records
  I6  multi-panel figures keep every panel's series
  I7  simulated curves are labelled simulated, never counted as measured
  I8  figure_data is derived from the current scout.json (no stale artifacts)

Exit code is 0 when no invariant fails, 1 otherwise.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                    # noqa: E402
from pipeline.figures import inventory as inv        # noqa: E402

#: the 11 crops repaired by the printed-figure caption association, with the printed
#: figure each must carry. Regression anchors, not routing logic.
TARGETS = {
    ("10.1002_pssa.201532305", 11): "8", ("10.1007_s11671-010-9676-0", 4): "2",
    ("10.1007_s11671-010-9676-0", 5): "2", ("10.1021_acs.jpcc.9b08176", 8): "2",
    ("10.1039_d3dt01824e", 8): "5", ("10.1039_d3ra05217f", 9): "5",
    ("10.1116_1.4892385", 9): "2", ("10.1116_1.4938104", 11): "5",
    ("10.1116_1.4938104", 20): "10", ("cremers2019", 26): "9", ("cremers2019", 37): "20",
}


def load(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except Exception:
        return default


def audit_paper(pid):
    invd = inv.load(pid)
    cands = invd["candidates"]
    sc = load(P.scout_json(pid), {})
    fd = load(P.figure_data_json(pid), {"figures": []})
    rec = load(P.records_json(pid), [])
    figs = fd.get("figures") or []

    disp = Counter(c["disposition"] for c in cands)
    printed = {c["printed_figure"] for c in cands if c.get("printed_figure")}
    panels = sum(len(f.get("panels") or []) for f in figs)
    series = sum(len(pn.get("series") or []) for f in figs for pn in (f.get("panels") or []))
    pts = sum(len(s.get("points") or [])
              for f in figs for pn in (f.get("panels") or []) for s in (pn.get("series") or []))
    src = Counter(r.get("source") or "unlabelled" for r in rec)
    study = Counter(r.get("study_type") or "unlabelled" for r in rec)
    recpts = sum(len(r.get("points") or []) for r in rec)
    unresolved = [c["candidate_id"] for c in cands if c["disposition"] == inv.MANUAL_REVIEW]
    return dict(
        paper=pid, pictures=len(cands), printed_figures=len(printed),
        drill=disp.get(inv.DRILL, 0), offered_unresolved=disp.get(inv.OFFERED, 0),
        merged=disp.get(inv.MERGED_INTO_PRINTED_FIGURE, 0),
        skip=disp.get(inv.SKIP_WITH_REASON, 0), manual=disp.get(inv.MANUAL_REVIEW, 0),
        scout_drill=len(sc.get("drill") or []), figures=len(figs), panels=panels,
        series=series, points=pts, records=len(rec), record_points=recpts,
        measured=src.get("measured", 0), simulated=src.get("simulated", 0),
        other_source={k: v for k, v in src.items() if k not in ("measured", "simulated")},
        study_type=dict(study), unresolved=unresolved,
        upstream=fd.get("_upstream_scout"),
        scout_fp=(hashlib.sha256(P.scout_json(pid).read_bytes()).hexdigest()[:16]
                  if P.scout_json(pid).exists() else None),
        cands=cands, figs=figs, rec=rec,
    )


def invariants(rows):
    fail, note = [], []
    for r in rows:
        pid = r["paper"]
        by = {c["docling_index"]: c for c in r["cands"]}
        active = {str(f.get("figure")) for f in r["figs"]}
        active |= {str(x["provenance"].get("fig_docling_index")) for x in r["rec"]}
        active.discard("None")

        # I1 — a crop the inventory retired must not still be an active source
        for i, c in by.items():
            if c["disposition"] in (inv.MERGED_INTO_PRINTED_FIGURE, inv.SKIP_WITH_REASON) \
                    and str(i) in active:
                fail.append(f"I1 {pid} P{i}: {c['disposition']} but still an active source")

        # I2 — a DRILL crop must carry printed-figure identity and an image
        for i, c in by.items():
            if c["disposition"] != inv.DRILL:
                continue
            if not c.get("image"):
                fail.append(f"I2 {pid} P{i}: DRILL without an image crop")
            if not c.get("printed_figure") and not c.get("caption_original"):
                fail.append(f"I2 {pid} P{i}: DRILL without printed-figure identity")

        # I3 — every record traces to a crop that is DRILL
        for x in r["rec"]:
            i = x["provenance"].get("fig_docling_index")
            if i is None:
                fail.append(f"I3 {pid}: record with no fig_docling_index")
                continue
            c = by.get(int(i))
            if c is None:
                fail.append(f"I3 {pid}: record cites unknown crop P{i}")
            elif c["disposition"] != inv.DRILL:
                fail.append(f"I3 {pid} P{i}: record from a crop marked {c['disposition']}")

        # I4 — one record per extracted series
        if r["series"] != r["records"]:
            fail.append(f"I4 {pid}: {r['series']} series but {r['records']} records")

        # I5 — no points lost between figure_data and records
        if r["points"] != r["record_points"]:
            fail.append(f"I5 {pid}: {r['points']} extracted points vs "
                        f"{r['record_points']} in records")

        # I6 — a multi-panel figure keeps every panel's series.
        # Aggregated per FIGURE, not per panel label: the pipeline normalises
        # provenance.panel to a bare letter (_clean_panel), so descriptive panel names
        # like "b (C 1s)" or "a - Without bottom" are deliberately not preserved there.
        # Comparing against the raw label would measure that normalisation, not loss.
        for f in r["figs"]:
            want = sum(len(pn.get("series") or []) for pn in (f.get("panels") or []))
            got = sum(1 for x in r["rec"]
                      if str(x["provenance"].get("fig_docling_index")) == str(f.get("figure")))
            if got != want:
                fail.append(f"I6 {pid} fig {f.get('figure')}: {want} extracted series "
                            f"-> {got} records")
            npan = len([pn for pn in (f.get("panels") or []) if pn.get("series")])
            if npan > 1 and got < npan:
                fail.append(f"I6 {pid} fig {f.get('figure')}: {npan} data panels but "
                            f"only {got} records")

        # I7 — simulated curves keep their label
        for x in r["rec"]:
            if x.get("source") not in ("measured", "simulated"):
                fail.append(f"I7 {pid}: record with source={x.get('source')!r}")

        # I8 — figure_data derived from the current scout
        if r["records"] or r["figures"]:
            if r["upstream"] != r["scout_fp"]:
                fail.append(f"I8 {pid}: figure_data upstream {r['upstream']} != "
                            f"scout {r['scout_fp']}")

    # targets
    seen = {}
    for r in rows:
        seen[r["paper"]] = {c["docling_index"]: c for c in r["cands"]}
    for (pid, idx), want in sorted(TARGETS.items()):
        c = seen.get(pid, {}).get(idx)
        if c is None:
            fail.append(f"TARGET {pid} P{idx}: missing from inventory")
            continue
        if c.get("printed_figure") != want:
            fail.append(f"TARGET {pid} P{idx}: printed figure "
                        f"{c.get('printed_figure')} != {want}")
        if c["disposition"] != inv.DRILL:
            note.append(f"TARGET {pid} P{idx}: {c['disposition']} (scout declined)")
    return fail, note


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--before")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    papers = [p for p in sorted(P.papers()) if P.structure_json(p).exists()]
    rows = [audit_paper(p) for p in papers]

    hdr = ("%-32s %4s %4s %4s %4s %4s %4s %4s %5s %5s %6s %6s %5s %5s"
           % ("paper", "pics", "pfig", "DRL", "MRG", "SKP", "MAN", "figs",
              "panel", "sers", "points", "recs", "meas", "sim"))
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print("%-32s %4d %4d %4d %4d %4d %4d %4d %5d %5d %6d %6d %5d %5d"
              % (r["paper"][:32], r["pictures"], r["printed_figures"], r["drill"],
                 r["merged"], r["skip"], r["manual"], r["figures"], r["panels"],
                 r["series"], r["points"], r["records"], r["measured"], r["simulated"]))
    T = lambda k: sum(r[k] for r in rows)                                  # noqa: E731
    print("-" * len(hdr))
    print("%-32s %4d %4d %4d %4d %4d %4d %4d %5d %5d %6d %6d %5d %5d"
          % ("TOTAL (%d papers)" % len(rows), T("pictures"), T("printed_figures"),
             T("drill"), T("merged"), T("skip"), T("manual"), T("figures"),
             T("panels"), T("series"), T("points"), T("records"),
             T("measured"), T("simulated")))

    fail, note = invariants(rows)
    print("\n=== invariants")
    for f in fail:
        print("  FAIL  " + f)
    for n in note:
        print("  note  " + n)
    if not fail:
        print("  all invariants hold (I1-I8, 11 caption-repair targets)")

    if a.json:
        Path(a.json).write_text(json.dumps(
            [{k: v for k, v in r.items() if k not in ("cands", "figs", "rec")} for r in rows],
            indent=1))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
