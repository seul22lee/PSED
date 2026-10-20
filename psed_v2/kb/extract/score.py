#!/usr/bin/env python3
"""P138: one command over any list of papers: compile, check --dir, audit against the gold, gold diff, experiments side by side and
values per quantity gold vs compiled (query.values on both trees). No provider call.

    python3 psed_v2/kb/extract/score.py P138 yli18 yim20      # tables to kb/reports/<unit>.<key>.*.csv and kb/reports/<unit>.score.csv

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
    """check.py's per-paper check on kb/compiled, every problem (not the printed first 40)."""
    code = (f"import sys, json; sys.argv = ['check.py', '--dir', {str(K.OUT)!r}]; sys.path.insert(0, {str(C.V2 / 'kb' / 'pilot')!r}); "
            f"import check; print(json.dumps(check.check({pid!r})[0]))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    import json
    return json.loads(out.stdout.strip().splitlines()[-1])


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
    summary = []
    for arg in papers:
        pid, key = C.resolve(arg)
        run = K.Run(pid)
        run.run()
        table, extra = K.diff(run)
        log = run.log + [f"step {s}: {dict(c)}" for s, c in run.steps.items()] + ["diff against the gold:"] + \
            [f"  {d['type']:<12} {d['gold']:>4} {d['compiled']:>4} {d['matched']:>4} {d['precision']:>5} {d['recall']:>5}" for d in table] + extra
        (K.OUT / f"{pid}.compile.log").write_text("\n".join(log) + "\n", encoding="utf-8")
        K.write_csv(R / f"{unit}.{key}.diff.csv", ["type", "gold", "compiled", "matched", "precision", "recall"], table)
        errs = check_dir(pid)
        K.write_csv(R / f"{unit}.{key}.check_dir.csv", ["problem"], [dict(problem=e) for e in errs])
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
        summary.append(dict(paper=key, check_dir_problems=len(errs), matched_T6=tot.get("T6 matched", "0"), gold_rows=tot.get("total", ""),
                            **{f"diff_{d['type']}": f"{d['matched']}/{d['gold']}" for d in table}))
        print(f"{key}: check --dir {len(errs)} problems; T6 {tot.get('T6 matched')}/{tot.get('total')}")
    fields = list(dict.fromkeys(k for s in summary for k in s))
    K.write_csv(R / f"{unit}.score.csv", fields, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
