#!/usr/bin/env python3
"""P88: the pilot's hand-read curves (pilot/<paper_id>.points.json, pilot/points.json: read by eye, kept for the record, no longer
built) compared automatically against the curves the figure stage read and the importer kept (kb/<paper_id>.figures.json): the
same panel and series, matched by rule (the hand curve's name or series label against the imported series label, normalised),
the share of hand points with an imported point within 2 % of both axis ranges (raw printed units, the imported curve's ranges) and
the median point deviation. Writes pilot/figures_agreement.csv.

    python3 psed_v2/kb/figures_agreement.py
"""
import csv, json, re, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PILOT = V2 / "pilot"
sys.path.insert(0, str(PILOT))
from elements import PAPERS  # noqa: E402

TOL = 0.02


def norm(s):
    return re.sub(r"[\s_\-()]+", "", re.sub(r"\s*[\(\[].*$", "", str(s))).lower()


def match_series(hand_label, panel_curves):
    """The imported curve of the panel whose series label matches the hand label: equal after normalisation, or one ends with the other
    (fig11a_TMA0.1s ~ '0.1 s', fig7_X5 ~ 'X5 (50 µm)')."""
    h = norm(hand_label)
    cands = []
    for c in panel_curves:
        lab = norm(c["series"].get("label_raw", ""))
        if not lab and len(panel_curves) == 1:
            return c
        if lab and (lab == h or h.endswith(lab) or lab.endswith(h)):
            cands.append((abs(len(lab) - len(h)), c))
    return min(cands, key=lambda x: x[0])[1] if cands else None


def agreement(hand_pts, imp_pts):
    xs = [x for x, _ in imp_pts]; ys = [y for _, y in imp_pts]
    sx = (max(xs) - min(xs)) or 1.0; sy = (max(ys) - min(ys)) or 1.0
    devs = []
    for x, y in hand_pts:
        devs.append(min(max(abs(x - x2) / sx, abs(y - y2) / sy) for x2, y2 in imp_pts))
    hit = sum(1 for d in devs if d <= TOL)
    return hit / len(devs) if devs else 0.0, (statistics.median(devs) if devs else None)


def main():
    rows = []
    cases = json.loads((PILOT / "points.json").read_text(encoding="utf-8"))["series"]
    for pid, key in PAPERS.items():
        kbp = HERE / f"{pid}.figures.json"
        imported = json.loads(kbp.read_text(encoding="utf-8"))["curves"] if kbp.exists() else []
        by_panel = {}
        for c in imported:
            by_panel.setdefault((str(c["figure"]), c["panel"]), []).append(c)
        hand = []
        hp = PILOT / f"{pid}.points.json"
        if hp.exists():
            for name, d in json.loads(hp.read_text(encoding="utf-8")).items():
                m = re.match(r"^fig(\d+)([a-z]?)_(.+)$", name)
                if m:
                    hand.append((m.group(1), m.group(2), m.group(3), name, d["points"], f"{pid}.points.json"))
        for s_ in cases:
            if s_["paper"] == pid:
                hand.append((str(s_["figure"]), s_["panel"], s_["series"], f"points.json {s_['figure']}{s_['panel']} '{s_['series']}'", s_["points"], "points.json"))
        for fig, panel, label, name, pts, src in hand:
            cs = by_panel.get((fig, panel), [])
            c = match_series(label, cs) if cs else None
            if not c:
                rows.append(dict(paper_id=pid, key=key, figure=fig, panel=panel, hand=name, source=src, imported_curve="", n_hand=len(pts), n_imported=0, share_within_2pct="", median_deviation="",
                                 note="no imported curve for this panel and series" + (" (panel not imported)" if not cs else " (series label unmatched)")))
                continue
            raw = c["points_raw"]
            share, med = agreement(pts, raw)
            rows.append(dict(paper_id=pid, key=key, figure=fig, panel=panel, hand=name, source=src, imported_curve=c["id"], n_hand=len(pts), n_imported=len(raw), share_within_2pct=f"{share:.3f}",
                             median_deviation=f"{med:.4f}", note="raw printed units of the imported curve's axis ranges"))
    out = PILOT / "figures_agreement.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    matched = [r for r in rows if r["imported_curve"]]
    shares = [float(r["share_within_2pct"]) for r in matched]; meds = [float(r["median_deviation"]) for r in matched]
    print(f"{out}: {len(rows)} hand curves, {len(matched)} matched to an imported curve; mean share within 2 % {statistics.mean(shares):.2f} (median {statistics.median(shares):.2f}); "
          f"median of the median deviations {statistics.median(meds):.4f}" if matched else f"{out}: {len(rows)} hand curves, none matched")
    return rows


if __name__ == "__main__":
    main()
