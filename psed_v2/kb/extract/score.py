#!/usr/bin/env python3
"""P138: one command over any list of papers: compile, check --dir, audit against the gold, gold diff, experiments side by side and
values per quantity gold vs compiled (query.values on both trees). No provider call.

    python3 psed_v2/kb/extract/score.py P138 yli18 yim20      # tables to kb/reports/<unit>.<key>.*.csv and kb/reports/<unit>.score.csv

P148: also kb/compiled/score_summary.csv, one row per (paper, section, item): type (gold, compiled, matched, precision, recall per
record type, compile.diff), check_tree (check.py check_tree errors on the compiled tree, by class: the message with its ids,
numbers and quoted values masked), drops (dropped.csv by step and reason), about (the pass-1 records by about: a pass-0 unit id,
"paper", null, unknown), placement (the gold/compiled pairs of compile.diff: the parent's type and kind equal, or the two kinds).

Held-out papers are refused (common.resolve).
"""
import collections
import csv
import subprocess
import sys

import common as C
import compile as K

R = C.V2 / "kb" / "reports"


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def check_dir(pid):
    """check.py's per-paper check on kb/compiled, every problem (not the printed first 40); P148: and the check_tree part of them."""
    code = (f"import sys, json; sys.argv = ['check.py', '--dir', {str(K.OUT)!r}]; sys.path.insert(0, {str(C.V2 / 'kb' / 'pilot')!r}); "
            f"import check; els = {{r['element_id']: r for r in check.rd(check.HERE / {pid + '.elements.csv'!r})}}; "
            f"print(json.dumps([check.check({pid!r})[0], check.check_tree(check.rd(check.DIR / {pid + '.facts.csv'!r}), els)]))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    import json
    return json.loads(out.stdout.strip().splitlines()[-1])


def err_class(e):
    """P148: a check message as its class: the leading row id dropped; ids, numbers and quoted values masked."""
    import re
    t = re.sub(r"^\S+: ", "", e)
    t = re.sub(r"'[^']*'|\"[^\"]*\"", "'·'", t)
    return re.sub(r"\b[\w.:#-]*\d[\w.:#-]*\b|\b\w+:[\w.:#-]+", "·", t)


def parent_kind(R, fid):
    p = R.get(R.get(fid, {}).get("parent", ""), {})
    return f"{p.get('type', 'missing')} {p.get('kind', '')}".strip()


def score_rows(key, run, table, tree_errs):
    """P148: the score_summary.csv rows of one paper (see the module docstring)."""
    out = [dict(paper=key, section="type", item=d["type"], gold=d["gold"], compiled=d["compiled"], matched=d["matched"],
                precision=d["precision"], recall=d["recall"], count="") for d in table]
    row = lambda sec, item, n: dict(paper=key, section=sec, item=item, gold="", compiled="", matched="", precision="", recall="", count=n)   # noqa: E731
    out += [row("check_tree", c, n) for c, n in collections.Counter(map(err_class, tree_errs)).most_common()]
    out += [row("drops", f"{s_}:{r_}", n) for (s_, r_), n in collections.Counter((d["step"], d["reason"]) for d in run.dropped).most_common()]
    ab = collections.Counter()
    for a in run.answers.values():
        for rec in (a if isinstance(a, list) else []):
            x = rec.get("about")
            ab["paper" if x == "paper" else "null" if not x else "filled (a pass-0 unit)" if x in run.node else "unknown"] += 1
    out += [row("about", k, n) for k, n in ab.most_common()]
    gold = list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{run.pid}.facts.csv").open(encoding="utf-8")))
    G, CR = {g["fact_id"]: g for g in gold}, {c["fact_id"]: c for c in run.rows}
    free, pk = list(range(len(gold))), collections.Counter()
    for c in run.rows:                                                          # the pairs of compile.diff: one gold row per compiled row, first come
        j = next((j for j in free if K.matches(gold[j], c)), None)
        if j is None:
            continue
        free.remove(j)
        a, b = parent_kind(G, gold[j]["fact_id"]), parent_kind(CR, c["fact_id"])
        pk["parent kind = gold" if a == b else f"differs: gold {a} / compiled {b}"] += 1
    out += [row("placement", k, n) for k, n in pk.most_common()]
    return out


def experiments(pid):
    out = []
    for src, p in (("gold", C.V2 / "kb" / "pilot" / f"{pid}.experiments.csv"), ("compiled", K.OUT / f"{pid}.experiments.csv")):
        for r in rd(p):
            out.append(dict(source=src, run=r["run"], label=r["label"], kind=r["kind"], parent=r["parent"],
                            settings=sum(1 for k, v in r.items() if k.startswith("setting:") and v),
                            results=sum(1 for k, v in r.items() if k.startswith("result:") and v),
                            setting_columns=";".join(sorted(k[8:] for k, v in r.items() if k.startswith("setting:") and v))))
    return out


def values(pid, key):
    """query.values per result quantity on the gold tree and on the compiled tree (swapped in for the call)."""
    import query as Q
    here, Q.HERE = Q.HERE, K.OUT
    try:
        T = Q.Tree(key)
    finally:
        Q.HERE = here
    gold = Q.TREES[key]
    qs = sorted({f["quantity"] for T_ in (gold, T) for f in T_.rows if "#" in f["fact_id"] and f["type"] in ("observation", "derived", "model")
                 and f["quantity"] and f["quantity"] != "other" and ";" not in f["quantity"]})
    out = []
    for q in qs:
        got = {}
        for side, tree in (("gold", gold), ("compiled", T)):
            saved = Q.TREES[key]
            Q.TREES[key] = tree
            try:
                gs = Q.values(q, paper=key)
            except Exception as e:                                              # a quantity query.values cannot answer: reported, not hidden
                gs = []
                got[side + "_error"] = f"{type(e).__name__}: {e}"[:120]
            finally:
                Q.TREES[key] = saved
            recs = [r["record"] for g in gs for r in g.get("rows", []) if isinstance(r.get("record"), dict)]
            got[side] = [(K.canon(dict(value=str(x.get("value") if x.get("value") is not None else ""), unit=x.get("unit") or "", quantity=q)),
                          f"{x.get('value')} {x.get('unit') or ''} [{x.get('fact', '')}]".strip()) for x in recs]
        gk = collections.Counter(c for c, _ in got["gold"] if c is not None)
        ck = collections.Counter(c for c, _ in got["compiled"] if c is not None)
        out.append(dict(quantity=q, gold_values=len(got["gold"]), compiled_values=len(got["compiled"]), same_value=sum((gk & ck).values()),
                        gold=" | ".join(t for _, t in got["gold"]), compiled=" | ".join(t for _, t in got["compiled"]),
                        error="; ".join(v for k, v in got.items() if k.endswith("_error"))))
    return out


def main(argv):
    unit, papers = argv[0], argv[1:]
    import audit as A
    summary, scores = [], []
    for arg in papers:
        pid, key = C.resolve(arg)
        run = K.Run(pid)
        run.run()
        table, extra = K.diff(run)
        log = run.log + [f"step {s}: {dict(c)}" for s, c in run.steps.items()] + ["diff against the gold:"] + \
            [f"  {d['type']:<12} {d['gold']:>4} {d['compiled']:>4} {d['matched']:>4} {d['precision']:>5} {d['recall']:>5}" for d in table] + extra
        (K.OUT / f"{pid}.compile.log").write_text("\n".join(log) + "\n", encoding="utf-8")
        K.write_csv(R / f"{unit}.{key}.diff.csv", ["type", "gold", "compiled", "matched", "precision", "recall"], table)
        errs, tree_errs = check_dir(pid)
        K.write_csv(R / f"{unit}.{key}.check_dir.csv", ["problem"], [dict(problem=e) for e in errs])
        scores += score_rows(key, run, table, tree_errs)
        sys.argv = ["audit.py", arg, "--unit", f"{unit}.{key}"]
        out = K.OUT
        try:
            A.main(arg)                                                         # the audit re-runs the compiler in a temporary folder
        finally:
            K.OUT = out
        ex = experiments(pid)
        K.write_csv(R / f"{unit}.{key}.experiments.csv", list(ex[0]) if ex else ["source"], ex)
        vs = values(pid, key)
        K.write_csv(R / f"{unit}.{key}.values.csv", ["quantity", "gold_values", "compiled_values", "same_value", "gold", "compiled", "error"], vs)
        st = rd(R / f"{unit}.{key}.stage_type.csv")
        tot = {r["stage"]: r["total"] for r in st}
        au = rd(C.V2 / "kb" / "compiled" / f"{pid}.audit.csv")
        pf = collections.Counter(r["parent_flagged"] for r in au if r["stage"] in ("T5 mismatch", "T6 matched"))
        summary.append(dict(paper=key, check_dir_problems=len(errs), matched_T6=tot.get("T6 matched", "0"), gold_rows=tot.get("total", ""),
                            parent_flagged_yes=pf["yes"], parent_flagged_no=pf["no"],
                            **{f"diff_{d['type']}": f"{d['matched']}/{d['gold']}" for d in table}))
        print(f"{key}: check --dir {len(errs)} problems; T6 {tot.get('T6 matched')}/{tot.get('total')}")
    fields = list(dict.fromkeys(k for s in summary for k in s))
    K.write_csv(R / f"{unit}.score.csv", fields, summary)
    K.write_csv(K.OUT / "score_summary.csv", ["paper", "section", "item", "gold", "compiled", "matched", "precision", "recall", "count"], scores)   # P148
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
