#!/usr/bin/env python3
"""One flat table of the experiments, read off the trees: <paper_id>.experiments.csv per paper and experiments.csv for the three
papers together, one row per entity with observations (an entity whose measurement activities, or later activities, hold an
observation, derived or model fact).

    python3 psed_v2/pilot/experiments.py      # writes the four CSVs; prints rows, columns and the columns the three papers share

Columns: paper, run (the entity id), label, kind (entity), how (stated or inferred), parent, group (the groups or comparisons the entity
or an activity above it belongs to), group_label, purpose (their purpose facts) and claims (claim ids linked to the entity, to an
activity above it, to a fact of theirs or to its groups); then one column per setting of its condition vector, setting:<quantity>
[<qualifiers>] (quantity other: setting:other:<label_as_printed>): the settings of the non-measurement activities above the entity,
the nearest activity's value first; several distinct values at one activity are joined with "; "; a value is censor+value+unit, min–max
unit or the value_text; then one column per result, result:<quantity>[<qualifiers>]: the observation, derived and model facts under
the entity (its measurement and later activities, not a piece cut from it) that carry a value, a range, a value_text or points, each
value or, for a curve, its points_ref. Column order:
the fixed columns, then the settings by the number of runs carrying them, then the results likewise. The combined CSV has the union.
Cited works are rows too (kind cited): one row per cited work of the tree (:refs:N), its cited facts filling the columns (a quantity
goes to setting: or result: by how the three papers use it in their own facts), and `via` naming the citing paper and the elements
that cite it; a run's `via` is empty.
"""
import collections, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from elements import PAPERS  # noqa: E402

FIXED = ["paper", "run", "label", "kind", "how", "parent", "group", "group_label", "purpose", "claims", "via"]
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


MEAS = {"measurement"}


def table(pid, paper):
    rows = rd(HERE / f"{pid}.facts.csv")
    R = {r["fact_id"]: r for r in rows}
    K = collections.defaultdict(list)
    for r in rows:
        if r["parent"]:
            K[r["parent"]].append(r)
    NODE = ("activity", "entity", "run", "group", "process")

    def own(i):                                   # a node's own facts: its subtree, not crossing another node
        out = []
        for c in K.get(i, []):
            if c["type"] in NODE:
                continue
            if "#" in c["fact_id"]:
                out.append(c)
            out += own(c["fact_id"])
        return out

    def below(i):                                 # an entity's facts: its subtree, not crossing another entity (its measurement activities included)
        out = []
        for c in K.get(i, []):
            if c["type"] == "entity":
                continue
            if "#" in c["fact_id"]:
                out.append(c)
            out += below(c["fact_id"])
        return out

    def above(i):
        out, x = [], R[i]["parent"]
        while x in R:
            out.append(x); x = R[x]["parent"]
        return out

    def node_of(i):                               # the nearest node (activity, entity, group) at or above a row
        while i in R and R[i]["type"] not in NODE:
            i = R[i]["parent"]
        return i if i in R else ""

    claims = collections.defaultdict(set)
    for c in rows:
        if c["type"] == "claim":
            for l in filter(None, c["links"].split(";")):
                t = node_of(l)
                if t:
                    claims[t].add(c["fact_id"])
    groups = [g for g in rows if g["type"] in ("group", "comparison")]
    # how the papers use a quantity in their own facts: a setting or a result (for the cited works' columns)
    use = collections.Counter()
    for f in rows:
        if "#" in f["fact_id"] and f["quantity"] and f["type"] in ("setting",) + RESULT_TYPES:
            use[(f["quantity"], f["type"] == "setting")] += 1
    is_setting = lambda qn: use[(qn, True)] >= use[(qn, False)]
    out = []
    for e in rows:
        if e["type"] != "entity":
            continue
        res = collections.defaultdict(list)
        for f in below(e["fact_id"]):
            if f["type"] in RESULT_TYPES and f["quantity"] and (text(f) or f["points_ref"]):
                res[key(f)].append(f["points_ref"] or text(f))
        if not any(f["type"] in RESULT_TYPES for f in below(e["fact_id"])):
            continue                              # an experiment is an entity with observations (valued or not)
        chain = above(e["fact_id"])
        mine = {e["fact_id"]} | set(chain)
        gs = [g for g in groups if set(g["links"].split(";")[1:]) & mine]
        rec = dict(paper=paper, run=e["fact_id"], label=e["label_as_printed"], kind="entity", how=e["how"], parent=e["parent"],
                   group=";".join(g["fact_id"] for g in gs), group_label=";".join(g["label_as_printed"] for g in gs),
                   purpose=";".join(dict.fromkeys(g["links"].split(";")[0] for g in gs if g["links"] and "#" in g["links"].split(";")[0])),
                   claims=";".join(sorted(set().union(*(claims[n] for n in mine), *(claims[g["fact_id"]] for g in gs)))), via="")
        for x in chain:                           # the condition vector: settings of the non-measurement activities above, nearest first
            if R[x]["type"] != "activity" or R[x]["kind"] in MEAS:
                continue
            level = collections.defaultdict(list)
            for f in own(x):
                if f["type"] == "setting" and f["quantity"]:
                    level[key(f)].append(f)
            for k, fs in level.items():
                if "setting:" + k not in rec:
                    rec["setting:" + k] = "; ".join(dict.fromkeys(t for t in (text(f) for f in fs) if t))
        for k, vs in res.items():
            rec["result:" + k] = "; ".join(vs)
        out.append(rec)
    for w in rows:                                                              # cited works: their facts, via the citing paper
        if w["type"] != "cited" or "#" in w["fact_id"]:
            continue
        fs = [f for f in K.get(w["fact_id"], []) if "#" in f["fact_id"]]
        rec = dict(paper=paper, run=w["fact_id"], label=w["label_as_printed"], kind="cited", how="", parent=w["parent"], group="", group_label="",
                   purpose="", claims=";".join(sorted(claims[w["fact_id"]])),
                   via=paper + " " + ";".join(dict.fromkeys(e for f in fs for e in f["evidence"].split(";"))))
        cells = collections.defaultdict(list)
        for f in fs:
            if f["quantity"] and (text(f) or f["points_ref"]):
                cells[("setting:" if is_setting(f["quantity"]) else "result:") + key(f)].append(f["points_ref"] or text(f))
        for k, vs in cells.items():
            rec[k] = "; ".join(dict.fromkeys(vs))
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
        print(f"{paper}: {sum(r['kind'] != 'cited' for r in recs)} runs + {sum(r['kind'] == 'cited' for r in recs)} cited works, {len(cols)} columns "
              f"({sum(c.startswith('setting:') for c in cols)} settings, {sum(c.startswith('result:') for c in cols)} results)")
    cols = write(HERE / "experiments.csv", every)
    print(f"experiments.csv: {sum(r['kind'] != 'cited' for r in every)} runs + {sum(r['kind'] == 'cited' for r in every)} cited works, {len(cols)} columns "
          f"({sum(c.startswith('setting:') for c in cols)} settings, {sum(c.startswith('result:') for c in cols)} results)")
    shared = sorted(set.intersection(*per.values()) - set(FIXED))
    print(f"columns all three papers share ({len(shared)}):", ", ".join(shared))
