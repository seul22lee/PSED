"""
c1_accuracy.py  (Phase C1)  — no LLM
------------------------------------
Conformance says the records are machine-readable; accuracy asks whether the
VALUES are right. This grounds each resolved record against its SOURCE (figure
caption + the paragraphs that discuss it):

  material_grounded : the material's formula/name appears in caption/series/context
  axis_grounded     : the varies/dependent quantity's alias appears in the axis label
  value_grounded    : each stated controlled NUMBER appears in the caption/context text
  has_points        : profile experiments carry a digitized curve

Prints aggregate grounding rates + a sampled side-by-side for eyeballing.
Not a substitute for reading the figures, but catches hallucinated fields.
"""
import json
import re
import random
from collections import Counter
from lib import papers, enrich_dir, OUTPUT, ONTO

random.seed(7)

# material -> surface forms (formula, id, aka, common names)
MAT_FORMS = {}
for m in ONTO["individuals"]["materials"]:
    forms = {m["id"].lower(), (m.get("formula") or "").lower()}
    for a in m.get("aka", []): forms.add(a.lower())
    if m.get("emmo_todo"): forms.add(m["emmo_todo"].lower())
    MAT_FORMS[m["id"]] = {f for f in forms if f}
QALIAS = {q["id"]: [q["id"]] + [a.lower() for a in q.get("aliases", [])] for q in ONTO["quantity_kinds"]}


def norm_txt(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ./=-]", " ", str(s).lower()))


def fig_text(paper_dir, figure_id):
    """caption + axis labels + discussing paragraphs for the record's figure."""
    if not figure_id:
        return ""
    d = enrich_dir(paper_dir)
    if not d.exists():
        return ""
    num = re.search(r"(\d+)", figure_id)
    num = num.group(1) if num else None
    best = None
    for f in sorted(d.glob("figure-*.json")):
        j = json.loads(f.read_text())
        fid = j.get("figure_id", "")
        if fid == figure_id:
            best = j; break
        if num and num in fid and best is None:
            best = j
    if not best:
        return ""
    parts = [best.get("caption") or "", best.get("x_label") or "", best.get("y_label") or ""]
    parts += best.get("figure_contexts", []) or []
    sub = best.get("subfigure_contexts", [])
    parts += (list(sub.values()) if isinstance(sub, dict) else sub) or []
    flat = []
    for x in parts:
        flat += [str(y) for y in x] if isinstance(x, list) else [str(x)]
    return norm_txt(" ".join(flat))


def val_forms(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return []
    out = set()
    if f == int(f): out.add(str(int(f)))
    out.add(f"{f:g}"); out.add(f"{f:.1f}"); out.add(f"{f:.2f}")
    # also the pre-SI form (e.g. 120 s stored as 120, or converted nm)
    return [o for o in out if o and o != "0"]


def main():
    agg = Counter(); tot = Counter(); samples = []
    dir_of = {p["pid"]: p["dir"] for p in papers()}
    for p in papers():
        pid = p["pid"]
        exps = json.loads((OUTPUT / pid / "resolved" / "experiments.json").read_text())
        for e in exps:
            txt = fig_text(dir_of[pid], (e.get("provenance") or {}).get("figure_id"))
            # material grounded
            mat = e.get("material"); mg = None
            if mat and mat in MAT_FORMS:
                hay = txt + " " + norm_txt(e.get("series_name") or "")
                mg = any(f in hay for f in MAT_FORMS[mat])
                tot["material"] += 1; agg["material"] += int(mg)
            # axis grounded (varies/dependent alias in figure text)
            for qid in (e.get("varies") or []) + [d.get("quantity") for d in e.get("dependent", [])]:
                if qid and qid in QALIAS:
                    tot["axis"] += 1
                    agg["axis"] += int(any(a in txt for a in QALIAS[qid]))
            # value grounded (controlled numbers appear in text)
            for c in e.get("controlled", []):
                if c.get("value") is not None:
                    tot["value"] += 1
                    agg["value"] += int(any(vf in txt for vf in val_forms(c["value"])))
            if e.get("granularity") == "profile":
                tot["points"] += 1; agg["points"] += int(len(e.get("points") or []) > 0)
            if len(samples) < 40:
                samples.append((pid, e, txt[:180]))

    print("=== C1 ACCURACY — grounding rates (field appears in source caption/context) ===")
    for k in ["material", "axis", "value", "points"]:
        if tot[k]:
            print(f"  {k:9}: {agg[k]}/{tot[k]}  ({100*agg[k]//tot[k]}%)")
    print("\n=== sampled records (field  |  source snippet) ===")
    for pid, e, snip in random.sample(samples, 7):
        ctrl = ", ".join(f"{c.get('quantity')}={c.get('value')}" for c in (e.get("controlled") or [])[:4] if c.get("value") is not None)
        print(f"\n[{pid}] {e.get('series_name')}  ({e.get('granularity')}, {e.get('relevance')})")
        print(f"   material={e.get('material')}  varies={e.get('varies')}  dep={[d.get('quantity') for d in e.get('dependent',[])]}")
        print(f"   controlled: {ctrl or '—'}")
        print(f"   source: “{snip}…”")


if __name__ == "__main__":
    main()
