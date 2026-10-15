#!/usr/bin/env python3
"""One flat table of the runs, read off the trees: <paper_id>.experiments.csv per paper and experiments.csv for the three papers
together, one row per run (a tree row of type run).

    python3 psed_v2/pilot/experiments.py      # writes the four CSVs; prints rows, columns and the columns the three papers share

Columns: paper, run, label, kind (the run= qualifier), how, parent, group (the nearest group above the run), group_label, purpose
(that group's purpose fact) and claims (claim ids linked to the run, to a fact of its own subtree or to its group); then one column
per setting the run inherits, setting:<quantity>[<qualifiers>] (quantity other: setting:other:<label_as_printed>), holding the
nearest value: the run's own facts first, then each ancestor's own facts up to the paper, where a node's own facts are its subtree
not crossing another run or group; several distinct values at that level are joined with "; "; a value is censor+value+unit, min–max unit
or the value_text; then one column per result on the run, result:<quantity>[<qualifiers>]: the observation, derived and model facts
of its own subtree that carry a value, a range, a value_text or points, each value or, for a curve, its points_ref. Column order:
the fixed columns, then the settings by the number of runs carrying them, then the results likewise. The combined CSV has the union.
"""
import collections, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from elements import PAPERS  # noqa: E402

FIXED = ["paper", "run", "label", "kind", "how", "parent", "group", "group_label", "purpose", "claims"]
RESULT_TYPES = ("observation", "derived", "model")


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def key(f):
    q = f"other:{f['label_as_printed']}" if f["quantity"] == "other" else f["quantity"]
    return q + (f"[{f['qualifiers']}]" if f["qualifiers"] else "")


def text(f):
    """The value as one string: censor+value+unit, min–max unit, or the value_text."""
    unit = f" {f['unit']}" if f["unit"] else ""
    if f["value"]:
        return f["censor"] + f["value"] + unit
    if f["value_min"] and f["value_max"]:
        return f"{f['censor']}{f['value_min']}–{f['value_max']}{unit}"
    if f["value_min"] or f["value_max"]:
        return f["censor"] + (f["value_min"] or f["value_max"]) + unit
    return f["value_text"]


def quals(s):
    return dict(p.split("=", 1) for p in s.split(";") if "=" in p)


def table(pid, paper):
    rows = rd(HERE / f"{pid}.facts.csv")
    R = {r["fact_id"]: r for r in rows}
    K = collections.defaultdict(list)
    for r in rows:
        if r["parent"]:
            K[r["parent"]].append(r)

    def own(i):                                   # a node's own facts: its subtree, not crossing another run or group
        out = []
        for c in K.get(i, []):
            if c["type"] in ("run", "group"):
                continue
            if "#" in c["fact_id"]:
                out.append(c)
            out += own(c["fact_id"])
        return out

    def row_of(i):                                # the nearest run or group at or above a row
        while i in R and R[i]["type"] not in ("run", "group"):
            i = R[i]["parent"]
        return i if i in R else ""

    claims = collections.defaultdict(set)
    for c in rows:
        if c["type"] == "claim":
            for l in filter(None, c["links"].split(";")):
                t = row_of(l)
                if t:
                    claims[t].add(c["fact_id"])
    out = []
    for run in rows:
        if run["type"] != "run":
            continue
        q = quals(run["qualifiers"])
        grp, x = "", run["parent"]
        while x in R:
            if R[x]["type"] == "group":
                grp = x; break
            x = R[x]["parent"]
        rec = dict(paper=paper, run=run["fact_id"], label=run["label_as_printed"], kind=q.get("run", ""), how=q.get("how", ""),
                   parent=run["parent"], group=grp, group_label=R[grp]["label_as_printed"] if grp else "",
                   purpose=R[grp]["links"].split(";")[0] if grp and R[grp]["links"] else "",
                   claims=";".join(sorted(claims[run["fact_id"]] | (claims[grp] if grp else set()))))
        x = run["fact_id"]
        while x in R:                             # settings: the nearest level wins
            level = collections.defaultdict(list)
            for f in own(x):
                if f["type"] == "setting" and f["quantity"]:
                    level[key(f)].append(f)
            for k, fs in level.items():
                if "setting:" + k not in rec:
                    rec["setting:" + k] = "; ".join(dict.fromkeys(t for t in (text(f) for f in fs) if t))
            x = R[x]["parent"]
        res = collections.defaultdict(list)
        for f in own(run["fact_id"]):
            if f["type"] in RESULT_TYPES and f["quantity"] and (text(f) or f["points_ref"]):
                res[key(f)].append(f["points_ref"] or text(f))
        for k, vs in res.items():
            rec["result:" + k] = "; ".join(vs)
        out.append(rec)
    return out


def columns(recs):
    n = collections.Counter(k for r in recs for k in r if k not in FIXED and r[k] != "")
    cols = sorted((k for k in {k for r in recs for k in r} if k not in FIXED), key=lambda k: (not k.startswith("setting:"), -n[k], k))
    return FIXED + cols


def write(path, recs):
    cols = columns(recs)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval=""); w.writeheader(); w.writerows(recs)
    return cols


if __name__ == "__main__":
    every, per = [], {}
    for pid, paper in PAPERS.items():
        recs = table(pid, paper)
        cols = write(HERE / f"{pid}.experiments.csv", recs)
        per[paper] = set(cols)
        every += recs
        print(f"{paper}: {len(recs)} runs, {len(cols)} columns ({sum(c.startswith('setting:') for c in cols)} settings, "
              f"{sum(c.startswith('result:') for c in cols)} results)")
    cols = write(HERE / "experiments.csv", every)
    print(f"experiments.csv: {len(every)} runs, {len(cols)} columns ({sum(c.startswith('setting:') for c in cols)} settings, "
          f"{sum(c.startswith('result:') for c in cols)} results)")
    shared = sorted(set.intersection(*per.values()) - set(FIXED))
    print(f"columns all three papers share ({len(shared)}):", ", ".join(shared))
