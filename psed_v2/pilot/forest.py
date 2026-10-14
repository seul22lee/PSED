#!/usr/bin/env python3
"""The forest: the three paper trees (<paper_id>.facts.csv with parent/links) read together.

    python3 psed_v2/pilot/forest.py          # Cases 9 and 10 rebuilt from the forest, against the hand-made CSVs (see __main__)

Used by report.py for the quantity picker and scatter of the Facts tab. The rules, all local to a tree:
- leaves(q): every fact of quantity q with a numeric value (or a range) in any paper; cited when its type is cited or a
  cited work (:refs:N) is among its ancestors; scope = the nearest run, group, process or cited work above it.
- context(leaf): the nearest-scope settings. Walk up the parent chain; at each ancestor take the ancestor itself and its
  children; the first fact with a value seen for a quantity is that quantity's context. When two siblings at the same
  level carry the same quantity (e.g. three design heights under process), that quantity is "ambiguous" at that level
  and is not taken from farther up; one exact value beside censored bounds (17000 Torr-s beside ">1e4") wins.
- flags(leaves): for the quantity's leaves across all papers, the majority value of every qualifier key (absent counts)
  and the majority unit; a leaf is flagged with each key, or "unit", where it differs from the majority.
No unit conversion and no merging: values are as printed, so a scatter mixes units unless the flag says otherwise.
"""
import collections, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from elements import PAPERS  # noqa: E402
from facts import num  # noqa: E402

SCOPES = ("run", "group", "process", "cited", "paper")


def quals(s):
    return dict(p.split("=", 1) for p in s.split(";") if "=" in p)


def value_of(row):
    """(value, low, high): a single value, or a range with value = its midpoint (geometric when both are positive)."""
    v, lo, hi = num(row["value"]), num(row["value_min"]), num(row["value_max"])
    if v is None and lo is not None and hi is not None:
        v = (lo * hi) ** 0.5 if lo > 0 and hi > 0 else (lo + hi) / 2
    elif v is None:
        v = lo if lo is not None else hi
    return v, lo, hi


class Forest:
    def __init__(self):
        self.papers = {}
        for pid, key in PAPERS.items():
            rows = list(csv.DictReader((HERE / f"{pid}.facts.csv").open(encoding="utf-8")))
            kids = collections.defaultdict(list)
            for r in rows:
                if r.get("parent"):
                    kids[r["parent"]].append(r)
            self.papers[key] = dict(pid=pid, rows=rows, byid={r["fact_id"]: r for r in rows}, kids=kids)

    def ancestors(self, key, fid):
        P, out, i = self.papers[key], [], self.papers[key]["byid"][fid].get("parent", "")
        while i and i in P["byid"] and i not in out:
            out.append(i); i = P["byid"][i].get("parent", "")
        return out

    def cited(self, key, fid):
        P = self.papers[key]
        return P["byid"][fid]["type"] == "cited" or any(":refs:" in a for a in self.ancestors(key, fid))

    def scope(self, key, fid):
        P = self.papers[key]
        return next((a for a in self.ancestors(key, fid) if P["byid"][a]["type"] in SCOPES), "")

    def context(self, key, fid):
        """quantity -> row (nearest scope first) or "ambiguous"."""
        P, ctx = self.papers[key], {}
        for a in self.ancestors(key, fid):
            seen = collections.Counter()
            cands = [P["byid"][a]] + P["kids"].get(a, [])
            for c in cands:
                if "#" in c["fact_id"] and c["fact_id"] != fid and c["quantity"] and c["quantity"] != "other" and value_of(c)[0] is not None:
                    seen[c["quantity"]] += 1
            exact = collections.Counter(c["quantity"] for c in cands if c["quantity"] in seen and not c["censor"]
                                        and "#" in c["fact_id"] and c["fact_id"] != fid and value_of(c)[0] is not None)
            for c in cands:
                q = c["quantity"]
                if q in seen and q not in ctx:
                    if seen[q] == 1:
                        ctx[q] = c
                    elif exact[q] == 1:                       # one exact value beside bounds: the value wins
                        ctx[q] = next(x for x in cands if x["quantity"] == q and not x["censor"] and "#" in x["fact_id"] and x["fact_id"] != fid)
                    else:
                        ctx[q] = "ambiguous"
        return ctx

    def leaves(self, quantities):
        qs = {quantities} if isinstance(quantities, str) else set(quantities)
        out = []
        for key, P in self.papers.items():
            for r in P["rows"]:
                if "#" in r["fact_id"] and r["quantity"] in qs:
                    v, lo, hi = value_of(r)
                    if v is None:
                        continue
                    out.append(dict(key=key, fid=r["fact_id"], row=r, value=v, low=lo, high=hi, unit=r["unit"], censor=r["censor"],
                                    quals=quals(r["qualifiers"]), cited=self.cited(key, r["fact_id"]), scope=self.scope(key, r["fact_id"]),
                                    ctx=self.context(key, r["fact_id"])))
        return out

    @staticmethod
    def flags(leaves):
        """fid -> the qualifier keys (or "unit") where the leaf differs from the majority of these leaves."""
        keys = {k for l in leaves for k in l["quals"]}
        maj = {k: collections.Counter(l["quals"].get(k, "") for l in leaves).most_common(1)[0][0] for k in keys}
        unit = collections.Counter(l["unit"] for l in leaves).most_common(1)[0][0] if leaves else ""
        out = {}
        for l in leaves:
            f = [k for k in sorted(keys) if l["quals"].get(k, "") != maj[k]] + (["unit"] if l["unit"] != unit else [])
            if f:
                out[l["fid"]] = f
        return out

    def quantities(self):
        """quantity -> number of leaves (numeric, any paper), without "other"."""
        c = collections.Counter()
        for P in self.papers.values():
            for r in P["rows"]:
                if "#" in r["fact_id"] and r["quantity"] and r["quantity"] != "other" and value_of(r)[0] is not None:
                    c[r["quantity"]] += 1
        return dict(c)

    def page_fields(self):
        """Per paper key: fid -> dict(ctx, cited, scope, flag) for every numeric leaf, as report.py embeds them."""
        out = {k: {} for k in self.papers}
        for q in self.quantities():
            ls = self.leaves(q)
            fl = self.flags(ls)
            for l in ls:
                ctx = {q2: ("ambiguous" if r == "ambiguous" else [r["censor"] + r["value"] + (f"{r['value_min']}–{r['value_max']}" if r["value_min"] else "") + (" " + r["unit"] if r["unit"] else ""),
                                                                  value_of(r)[0], r["fact_id"], value_of(r)[1], value_of(r)[2]]) for q2, r in l["ctx"].items()}
                out[l["key"]][l["fid"]] = dict(ctx=ctx, cited=l["cited"], scope=l["scope"], flag=fl.get(l["fid"], []))
        return out


if __name__ == "__main__":
    F = Forest()
    print("leaves per quantity:", dict(sorted(F.quantities().items(), key=lambda x: -x[1])))
