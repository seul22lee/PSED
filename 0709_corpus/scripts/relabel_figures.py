#!/usr/bin/env python3
"""
relabel_figures.py — one-off deterministic fix (no LLM, no re-extraction): the figure
id in provenance/exp_id was docling's IMAGE-EXTRACTION INDEX, not the paper's real
figure number. The real number lives in the stored caption ('FIG. 3', 'Figure 10:').
This rewrites provenance.figure + the exp_id figure token from the caption, and cleans
the panel token, across the active KB and the extracted records.json. Values unchanged.
"""
import json, re, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # 0709_corpus
OUT = ROOT.parent / "0706_pipeline" / "output"


def cap_fignum(cap):
    m = re.search(r"\b(?:fig(?:ure)?|scheme)\.?\s*0*([0-9]+)", (cap or "").lower())
    return m.group(1) if m else None


def clean_panel(exp, pid):
    p = str((exp.get("provenance") or {}).get("panel") or "").strip()
    if re.fullmatch(r"[A-Za-z]", p):
        return p.lower()
    m = re.match(re.escape(pid) + r"-F\d+([a-z]?)", exp.get("exp_id") or "")   # recover from exp_id
    return m.group(1) if m else ""


def _idx_from(pv):
    for k in ("figure", "figure_id", "fig_index"):
        if pv.get(k):
            m = re.search(r"(\d+)", str(pv[k]))
            if m:
                return m.group(1)
    return None


def main():
    kb_changed = kb_total = 0
    for f in sorted(glob.glob(str(OUT / "*" / "resolved" / "experiments.json"))):
        pid = f.split("/output/")[1].split("/")[0]
        exps = json.loads(Path(f).read_text())
        dirty = False
        for i, e in enumerate(exps):
            pv = e.setdefault("provenance", {})
            realnum = cap_fignum(pv.get("caption"))
            if not realnum:
                continue
            kb_total += 1
            if "fig_index" not in pv:
                idx = _idx_from(pv)
                if idx:
                    pv["fig_index"] = idx           # keep docling index for traceability
            new_fig = f"Fig {realnum}"
            panel = clean_panel(e, pid)
            new_id = f"{pid}-F{realnum}{panel}-{i}"
            if pv.get("figure") != new_fig or e.get("exp_id") != new_id:
                pv["figure"] = new_fig
                e["exp_id"] = new_id
                dirty = True
                kb_changed += 1
        if dirty:
            Path(f).write_text(json.dumps(exps, indent=1))
    print(f"[relabel] KB experiments: {kb_changed} relabeled / {kb_total} with a caption number")

    rec_changed = 0
    for f in sorted(glob.glob(str(ROOT / "extracted" / "*" / "records.json"))):
        recs = json.loads(Path(f).read_text())
        dirty = False
        for r in recs:
            pv = r.get("provenance") or {}
            realnum = cap_fignum(pv.get("caption"))
            if not realnum:
                continue
            new_fig = f"Fig {realnum}"
            new_panel = str(pv.get("panel") or "").strip().lower()
            new_panel = new_panel if re.fullmatch(r"[a-z]", new_panel) else ""
            if pv.get("figure") != new_fig or pv.get("panel") != new_panel:
                if "fig_index" not in pv:
                    idx = _idx_from(pv)
                    if idx:
                        pv["fig_index"] = idx
                pv["figure"] = new_fig
                pv["panel"] = new_panel
                dirty = True
                rec_changed += 1
        if dirty:
            Path(f).write_text(json.dumps(recs, indent=1))
    print(f"[relabel] records.json entries relabeled: {rec_changed}")


if __name__ == "__main__":
    main()
