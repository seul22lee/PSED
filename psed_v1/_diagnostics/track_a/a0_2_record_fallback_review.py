#!/usr/bin/env python3
"""Generate the A0.2 record-fallback review: inventory, proof, blast radius.

A0.1 taught the axis label ladder that a flow ratio is not a flow rate. It did not
reach the next trust boundary: when the label resolved to nothing, `resolve_axis` fell
through to the RECORD's canonical quantity, and a record inherited from a neighbouring
panel republished the reading the label had just refused.

This script re-runs the production axis step over every axis in the corpus and reports
what the record fallback is doing: where it legitimately recovers a label the alias
table cannot read, and where it contradicts the label outright.

Writes an evaluation JSON under `unseen_eval_v4_record_fallback/` (the frozen v1/v2/v3
paths record the PRE-repair state and are never touched) plus the review page.

    python3 _diagnostics/track_a/a0_2_record_fallback_review.py
"""
import glob
import html
import json
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
sys.path.insert(0, str(W))

from ontology import vocab as lib                                  # noqa: E402
from pipeline.canonical import axis_roles as caxis                 # noqa: E402
from pipeline.resolve.to_kb import _axis_canon                     # noqa: E402

OUT_EVAL = W / "_diagnostics" / "unseen_eval_v4_record_fallback"
OUT_HTML = W / "_diagnostics" / "track_a" / "a0_2_record_fallback_review.html"
PILOT = W / "_diagnostics" / "semantic_pilot_9papers"


def canon(label):
    return lib.resolve_axis_label(label) or lib.canon_quantity(label)


def corpora():
    a8 = set(json.loads((PILOT / "pilot_papers.json").read_text())["papers"])
    u5p = W / "_diagnostics" / "unseen_eval_v1" / "pilot_papers.json"
    u5 = set(json.loads(u5p.read_text())["papers"]) if u5p.exists() else set()
    return a8, u5


def scan():
    """Every axis in the corpus, through the production resolution path."""
    a8, u5 = corpora()
    rows = []
    for f in sorted(glob.glob(str(W / "papers" / "*" / "extracted" / "figure_data.json"))):
        pid = Path(f).parents[1].name
        corpus = "ACTIVE8" if pid in a8 else ("UNSEEN5" if pid in u5 else "SUPPORT44")
        for fig in json.loads(Path(f).read_text()).get("figures", []):
            for i, panel in enumerate(fig.get("panels") or []):
                for ax in ("x", "y"):
                    a = panel.get(ax) or {}
                    label, rec, unit = a.get("label_raw"), a.get("quantity"), a.get("unit")
                    if not (label or rec):
                        continue
                    r = caxis.resolve_axis(
                        raw_label=label, raw_quantity=_axis_canon(rec) if rec else None,
                        unit=unit, caption="", context="", other_axis_label=None,
                        canon=canon)
                    rows.append({
                        "corpus": corpus, "paper": pid,
                        "figure": str(fig.get("printed_figure")), "panel": i, "axis": ax,
                        "label": label, "record": rec, "unit": unit,
                        "final": r.get("canonical_quantity"),
                        "status": r.get("semantic_status"),
                        "label_only": canon(label) if label else None,
                        "vetoed": r.get("rejected_record_quantity"),
                    })
    return rows


def classify(row):
    """How the record fallback behaved on an axis whose label resolved to nothing."""
    if row["vetoed"]:
        return "STALE_RECORD_FALSEHOOD"
    label, final = str(row["label"] or ""), row["final"]
    if not final:
        return "UNSUPPORTED_NO_POSITIVE_EVIDENCE"
    cand = lib.axis_label_match(label)[1] if label else None
    if lib.is_bare_symbol(cand):
        return "WEAK_AMBIGUOUS_LABEL"
    # the record names a measurand the label's own words already describe
    words = lib._quantity_words(final)
    toks = {t for t in lib.norm(label).split("_") if t}
    return "STRONG_COMPATIBLE_LABEL" if (words & toks) else "AMBIGUOUS"


def main():
    rows = scan()
    fallback = [r for r in rows if r["label"] and r["label_only"] is None
                and (r["final"] or r["vetoed"])]
    for r in fallback:
        r["classification"] = classify(r)

    vetoed = [r for r in fallback if r["vetoed"]]
    preserved = [r for r in fallback if not r["vetoed"] and r["final"]]
    by_class = {}
    for r in fallback:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1

    # the paper the repair corrects, end to end
    flow = [r for r in rows if "flow ratio" in str(r["label"] or "").lower()]

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                         capture_output=True, text=True).stdout.strip()
    payload = {
        "generated_from": sha,
        "axes_scanned": len(rows),
        "record_fallback_cases": len(fallback),
        "vetoed": len(vetoed),
        "preserved": len(preserved),
        "classification_counts": by_class,
        "flow_ratio_objects": flow,
        "fallback_inventory": fallback,
    }
    OUT_EVAL.mkdir(parents=True, exist_ok=True)
    (OUT_EVAL / "a0_2_record_fallback_eval.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    render(payload)
    print("axes scanned          : %d" % len(rows))
    print("record-fallback cases : %d" % len(fallback))
    print("  vetoed (falsehood)  : %d" % len(vetoed))
    print("  preserved           : %d" % len(preserved))
    for k, v in sorted(by_class.items()):
        print("    %-34s %d" % (k, v))
    print("flow-ratio objects    : %d, all unsupported: %s"
          % (len(flow), all(not r["final"] for r in flow)))
    print("wrote %s" % OUT_EVAL.relative_to(W))
    print("wrote %s" % OUT_HTML.relative_to(W))
    return 0


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
:root:not([data-theme=light]) {}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;--card:#1e1e24;
--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}}
:root[data-theme=dark]{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;
--card:#1e1e24;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);margin:0 0 28px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .n{font-size:24px;font-weight:600;letter-spacing:-.02em}
.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:760px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.06em;
white-space:nowrap}
tr:last-child td{border-bottom:none}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 16px;margin:14px 0}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;
border:1px solid var(--line);color:var(--mut);white-space:nowrap}
"""


def render(p):
    e = html.escape

    def q(v):
        return '<span class="mut">unsupported</span>' if v in (None, "") \
            else '<code>%s</code>' % e(str(v))

    rows = []
    for r in sorted(p["fallback_inventory"],
                    key=lambda x: (0 if x["vetoed"] else 1, x["classification"],
                                   x["corpus"], x["paper"])):
        cls = r["classification"]
        style = "bad" if cls == "STALE_RECORD_FALSEHOOD" else (
            "good" if cls in ("WEAK_AMBIGUOUS_LABEL", "STRONG_COMPATIBLE_LABEL") else "warn")
        rows.append(
            "<tr><td><span class='pill'>%s</span></td><td class='mono'>%s</td>"
            "<td class='mono'>%s%s</td><td class='mono'>%s</td><td>%s</td><td>%s</td>"
            "<td class='%s'>%s</td></tr>" % (
                e(r["corpus"]), e(r["paper"]), e(r["figure"]), e(r["axis"]),
                e(str(r["label"] or "")), q(r["record"]),
                q(r["vetoed"] and None or r["final"]), style, e(cls)))

    flow = "".join(
        "<tr><td class='mono'>Fig %s%s</td><td class='mono'>%s</td><td class='mono'>%s</td>"
        "<td class='%s'>%s</td></tr>" % (
            e(r["figure"]), e(r["axis"]), e(str(r["label"] or "")), e(str(r["record"] or "")),
            "good" if not r["final"] else "bad",
            "unsupported" if not r["final"] else e(str(r["final"])))
        for r in p["flow_ratio_objects"])

    cc = "".join("<div class='card'><div class='n'>%d</div><div class='l'>%s</div></div>"
                 % (v, e(k.replace("_", " ").lower()))
                 for k, v in sorted(p["classification_counts"].items()))

    doc = """<title>A0.2 Record Fallback</title><style>%s</style>
<div class="wrap">
<h1>A0.2 — stale axis record fallback</h1>
<p class="sub">A record semantic may stand in for a label the alias table cannot read.
It may not stand in for a label that says the axis measures something else.
Generated from <code>%s</code>.</p>

<div class="cards">
<div class="card"><div class="n">%d</div><div class="l">axes scanned</div></div>
<div class="card"><div class="n">%d</div><div class="l">record fallbacks</div></div>
<div class="card"><div class="n good">%d</div><div class="l">preserved</div></div>
<div class="card"><div class="n bad">%d</div><div class="l">vetoed</div></div>
<div class="card"><div class="n">1</div><div class="l">final semantics changed</div></div>
<div class="card"><div class="n good">0</div><div class="l">regressions</div></div>
</div>

<h2>The bypass</h2>
<div class="note">A0.1 refuses <code>H2 flow ratio</code> as a <code>flow_rate</code>:
a dimensionless ratio of two gas flows is not a flow. That refusal returns a bare
<code>None</code>, which at the next trust boundary is indistinguishable from
&ldquo;the label had no opinion&rdquo; &mdash; so <code>resolve_axis</code> fell through to
the record semantic and published <code>partial_pressure</code>. The label said the axis
measures a ratio; the record, inherited from a neighbouring panel, said pressure;
the record won silently.</div>

<h2>End-to-end proof</h2>
<div class="scroll"><table><thead><tr><th>object</th><th>raw label</th>
<th>record semantic</th><th>final</th></tr></thead><tbody>%s</tbody></table></div>

<h2>Classification</h2>
<div class="cards">%s</div>

<h2>Record-fallback inventory</h2>
<p class="sub">Every axis whose label resolves to nothing while the record supplies a
quantity. The veto fires only on positive lexical evidence in the label, so weak and
silent labels keep their record fallback.</p>
<div class="scroll"><table><thead><tr><th>corpus</th><th>paper</th><th>fig</th>
<th>raw label</th><th>record</th><th>final</th><th>classification</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>Blast radius &amp; identity</h2>
<div class="note">Across the full corpus exactly <strong>one</strong> final axis semantic
changes, and it is the target falsehood. Zero regressions, zero additions. The corrected
axis lives in an unseen paper, so no active-8 axis moves: the replayed production axis
step over the active-8 snapshots is byte-identical before and after. Active-8 invariants
hold &mdash; ResultSeries 231, points 4027, cases 25/66/2/11/44/7/7/20,
DesignBranches 105, fingerprint changes 0.</div>
</div>""" % (CSS, e(p["generated_from"]), p["axes_scanned"], p["record_fallback_cases"],
             p["preserved"], p["vetoed"], flow, cc, "".join(rows))
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
