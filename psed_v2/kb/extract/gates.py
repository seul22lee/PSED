#!/usr/bin/env python3
"""P172: the gates of grow.py run (papers 14+), their reference values from the twelve development papers, and the call plan. No provider call.

    python3 psed_v2/kb/extract/gates.py reference              # the twelve development papers -> ontology/gates.csv (metric, worst value, paper)
    python3 psed_v2/kb/extract/gates.py plan <paper> ...        # planned provider calls and dollars per step, as JSON (grow.py run prints it)
    python3 psed_v2/kb/extract/gates.py pass0 <paper>           # the pass-0 gate: exit 0 pass, 3 stop; the gate table printed
    python3 psed_v2/kb/extract/gates.py pass1 <paper>           # the pass-1 gate (after compile): exit 0 pass, 3 stop

Metrics (P174: ontology/gates.csv column direction, read by the gate: 'lower is worse' for units per 100 elements, 'higher is worse' for
the rest):
  pass 0  units per 100 elements: the pass-0 units and the units compile.bind derives (P177b) per 100 elements.csv rows;
          unbound items (pass0_paper.consistency); units named after a measurement (pass0_paper.measurement_named); panels with no layout:
          the share of pass 0's panel_layouts whose layout is null (a share, so the paper's size does not decide it).
          Gate a (no reference value): pass 0 lists no run and no simulation, or fewer than 3 units in all.
  pass 1  form failures: the share of the paper's records (compile's records, validated as compile validates them) that fail form.json;
          quotes not found: the share of records compile drops at step d (quote_not_found).
A value worse than the worst of the twelve stops the run (gate b; a provider error or a cached-prefix failure, gate c, is grow.py's)."""
import collections
import csv
import json
import re
import sys
from pathlib import Path

import common as C
import compile as K
import pass0_paper as P0

GATES = C.V2 / "ontology" / "gates.csv"
COLS = ["metric", "stage", "direction", "worst_dev_value", "paper"]
LOWER_IS_WORSE = {"units per 100 elements"}


def dev_papers():
    """The twelve development papers: the index's papers with a gold file."""
    return [(pid, k) for pid, k in C.E.PAPERS.items() if (C.V2 / "kb" / "pilot" / f"{pid}.facts.csv").exists()]


def pass0_values(pid):
    obj = C.loads_json(C.lines(pid, 0)[-1]["response"])
    units = [u for u in obj.get("units") or [] if isinstance(u, dict)]
    n_el = len(C.E.load(pid))
    D = K.bind(pid, obj, None)["units"]                                         # P177b: the derived units of compile.bind
    pl = obj.get("panel_layouts") or []
    roles = collections.Counter(u.get("role") for u in units)
    return {"units per 100 elements": round(100 * (len(units) + len(D)) / max(n_el, 1), 2),
            "unbound items": sum(r["unbound"] for r in P0.consistency(pid, obj)),
            "units named after a measurement": sum(1 for r in P0.measurement_named(pid, obj) if r["flag"]),
            "panels with no layout (share)": round(sum(1 for x in pl if not (x or {}).get("layout")) / max(len(pl), 1), 3)}, roles, len(units)


def pass1_values(pid):
    from jsonschema import Draft202012Validator
    form = C.schema("form.json")
    val, pre = Draft202012Validator(form), Draft202012Validator(K.before_freeze(form))
    run = K.Run(pid)
    recs = run.resolve_other(run.read())
    n = len(recs)
    bad = sum(1 for r in recs if any(True for _ in (val if r.get("form_version") else pre).iter_errors({**{k: None for k in form["required"]}, **r["rec"]})))
    dropped = [r for r in csv.DictReader((K.OUT / f"{pid}.dropped.csv").open(encoding="utf-8"))] if (K.OUT / f"{pid}.dropped.csv").exists() else []
    nq = sum(1 for r in dropped if r["step"] == "d" and r["reason"] == "quote_not_found")
    return {"form failures (share of records)": round(bad / max(n, 1), 3), "quotes not found (share of records)": round(nq / max(n, 1), 3)}, n


def verdict_agreement():
    """P173 (user): the figure verdict rule (kb/figures_import.py: no figure-stage flag -> pass, any flag -> flagged) against the human
    verdicts of the twelve (ingest/answers/figures.json: ok -> pass agrees, any other verdict -> flagged agrees), per judged panel; every
    panel written to kb/reports/gates_verdict_agreement.csv. Returns (agreement rate, agreeing, judged)."""
    ans = json.loads((C.V2 / "ingest" / "answers" / "figures.json").read_text(encoding="utf-8"))["items"]
    flags = {}
    for pid in {v["paper_id"] for v in ans}:
        f = C.V2 / "ingest" / "final" / pid / "figures.json"
        for g in json.loads(f.read_text(encoding="utf-8")).get("figures", []) if f.exists() else []:
            flags[(pid, str(g["number"]))] = [x["flag"] for x in g.get("flags") or []]
    rows = []
    for v in ans:
        fl = flags.get((v["paper_id"], str(v["figure"])), [])
        rule = "pass" if not fl else "flagged"
        agree = (v["verdict"] == "ok") == (rule == "pass")
        rows.append(dict(paper=C.E.PAPERS.get(v["paper_id"], v["paper_id"]), figure=v["figure"], panel=v["panel"], human_verdict=v["verdict"],
                         flags=";".join(fl), rule_verdict=rule, agree="yes" if agree else "NO", note=v.get("note", "")))
    with (C.V2 / "kb" / "reports" / "gates_verdict_agreement.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "figure", "panel", "human_verdict", "flags", "rule_verdict", "agree", "note"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    n_ag = sum(1 for r in rows if r["agree"] == "yes")
    return round(n_ag / max(len(rows), 1), 3), n_ag, len(rows)


def reference():
    rows, per = {}, []
    for pid, key in dev_papers():
        v0, _, _ = pass0_values(pid)
        v1, _ = pass1_values(pid)
        for stage, vals in (("pass0", v0), ("pass1", v1)):
            for m, v in vals.items():
                per.append(dict(paper=key, stage=stage, metric=m, value=v))
                cur = rows.get(m)
                if cur is None or ((v < cur["worst_dev_value"]) if m in LOWER_IS_WORSE else (v > cur["worst_dev_value"])):
                    rows[m] = dict(metric=m, stage=stage, direction="lower is worse" if m in LOWER_IS_WORSE else "higher is worse", worst_dev_value=v, paper=key)
    rate, n_ag, n_all = verdict_agreement()                                     # P173: a reference, not a gate
    rows["figure verdict rule agreement"] = dict(metric="figure verdict rule agreement", stage="reference (not a gate)", direction="",
                                                 worst_dev_value=rate, paper=f"{n_ag} of {n_all} human-judged panels of the twelve")
    with GATES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows.values())
    with (C.V2 / "kb" / "reports" / "gates_dev_values.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "stage", "metric", "value"], lineterminator="\n")
        w.writeheader()
        w.writerows(per)
    for r in rows.values():
        print(r)
    return 0


def gate(stage, pid, key):
    ref = {r["metric"]: r for r in csv.DictReader(GATES.open(encoding="utf-8"))}
    if stage == "pass0":
        vals, roles, n_units = pass0_values(pid)
        extra = []
        if not (roles.get("run") or roles.get("simulation")):
            extra.append("gate a: pass 0 lists no run and no simulation")
        if n_units < 3:
            extra.append(f"gate a: fewer than 3 units ({n_units})")
    else:
        vals, n_rec = pass1_values(pid)
        extra = []
    rows, stop = [], list(extra)
    for m, v in vals.items():
        r = ref[m]
        if r["direction"] not in ("lower is worse", "higher is worse"):        # P174: the gate reads the direction from gates.csv
            raise SystemExit(f"ontology/gates.csv: {m}: direction {r['direction']!r} is neither 'lower is worse' nor 'higher is worse'")
        worse = v < float(r["worst_dev_value"]) if r["direction"] == "lower is worse" else v > float(r["worst_dev_value"])
        rows.append(dict(paper=key, stage=stage, metric=m, value=v, worst_dev_value=r["worst_dev_value"], worst_dev_paper=r["paper"], verdict="STOP" if worse else "pass"))
        if worse:
            stop.append(f"gate b: {m} {v} is worse than the worst development value {r['worst_dev_value']} ({r['paper']})")
    out = C.V2 / "kb" / "reports" / f"RUN_{key}.gate_{stage}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "stage", "metric", "value", "worst_dev_value", "worst_dev_paper", "verdict"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{'metric':<40} {'value':>8} {'worst dev':>10}  verdict")
    for r in rows:
        print(f"{r['metric']:<40} {r['value']:>8} {r['worst_dev_value']:>10}  {r['verdict']} ({r['worst_dev_paper']})")
    for s in stop:
        print("STOP " + s)
    return 3 if stop else 0


def plan(pids):
    """The planned provider calls and dollars per step: the figure stage (one vision call per captioned figure with images, when figures.json
    is missing; the mean cost of the figure calls on record), pass 0 (one call; the mean of the development papers' latest pass-0 calls),
    pass 1 (one call per group of pass1_elements.groups; the mean cost per call of the development papers' cached-prefix pass-1 lines)."""
    import pass1_elements as P1
    pr = {r["model"]: r for r in csv.DictReader((C.V2 / "kb" / "pilot" / "prices.csv").open(encoding="utf-8"))}
    def usd(x):
        p = pr.get(x.get("model", ""))
        if not p:
            return None
        u = x["usage"]
        hit = min(u.get("cache_read_tokens", 0) or 0, u["input_tokens"])
        return ((u["input_tokens"] - hit) * float(p["input_per_mtok"]) + hit * float(p["cache_hit_per_mtok"]) + u["output_tokens"] * float(p["output_per_mtok"])) / 1e6
    p0, p1 = [], []
    for pid, _ in dev_papers():
        lines = [json.loads(x) for x in (C.RECORDS / f"{pid}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        z = [x for x in lines if x["pass"] == 0]
        if z and usd(z[-1]) is not None:
            p0.append(usd(z[-1]))
        p1 += [usd(x) for x in lines if x["pass"] == 1 and x.get("prefix_hash") and usd(x) is not None]
    vin = vout = nfig = 0
    for f in (C.V2 / "ingest" / "final").glob("*/figures.json"):
        for g in json.loads(f.read_text(encoding="utf-8")).get("figures", []):
            t = g.get("tokens") or {}
            vin += t.get("in", 0) or 0
            vout += t.get("out", 0) or 0
            nfig += 1
    vp = pr.get("gemini-3.8-flash")
    fig_usd = ((vin / max(nfig, 1)) * float(vp["input_per_mtok"]) + (vout / max(nfig, 1)) * float(vp["output_per_mtok"])) / 1e6
    out = []
    for a in pids:
        pid, key = C.resolve(a)
        st = json.loads((C.V2 / "ingest" / "final" / pid / "structure.json").read_text(encoding="utf-8"))
        nf = 0 if (C.V2 / "ingest" / "final" / pid / "figures.json").exists() else sum(1 for c in st["captions"] if c["kind"] == "figure" and c.get("images"))
        have0 = any(x["pass"] == 0 and x.get("form_version") == C.X.FORM_VERSION for x in (json.loads(y) for y in ((C.RECORDS / f"{pid}.jsonl").read_text(encoding="utf-8").splitlines() if (C.RECORDS / f"{pid}.jsonl").exists() else []) if y.strip()))
        ng = len(P1.groups(pid)[0]) if (C.V2 / "kb" / "pilot" / f"{pid}.elements.csv").exists() else 0
        done1 = {x["section"] for x in (json.loads(y) for y in ((C.RECORDS / f"{pid}.jsonl").read_text(encoding="utf-8").splitlines() if (C.RECORDS / f"{pid}.jsonl").exists() else []) if y.strip()) if x["pass"] == 1 and x.get("form_version") == C.X.FORM_VERSION}
        n1 = sum(1 for g in (P1.groups(pid)[0] if ng else {}) if g not in done1)
        out.append(dict(paper=key, pid=pid, figure_calls=nf, figure_usd=round(nf * fig_usd, 3), pass0_calls=0 if have0 else 1,
                        pass0_usd=0 if have0 else round(sum(p0) / max(len(p0), 1), 3), pass1_calls=n1, pass1_usd=round(n1 * sum(p1) / max(len(p1), 1), 3),
                        note="pass-1 groups from elements.csv as it stands (built again after the figure stage)"))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main(argv):
    if argv[:1] == ["reference"]:
        return reference()
    if argv[:1] == ["plan"]:
        return plan(argv[1:])
    if argv[:1] in (["pass0"], ["pass1"]):
        pid, key = C.resolve(argv[1])
        return gate(argv[0], pid, key)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
