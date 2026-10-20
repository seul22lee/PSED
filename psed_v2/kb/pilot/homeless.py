#!/usr/bin/env python3
"""P79: every value record has a home in values(). Lists every value record of the page data (const D of reports/pilot.html:
sources[*].values with a fact id and an entry quantity; the same records from the facts when the page is not built) that no
values(result=<its entry>, paper=<its paper>) output renders in its full form (tools.BUDGET off: no set collapses), by paper, kind and
the home it needs; the count is the homeless_records column of run_metrics.py and must be 0 (check.py).

    python3 psed_v2/pilot/homeless.py            # the list and the count
"""
import collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import query as Q  # noqa: E402

PAGE = HERE / "reports" / "pilot.html"
_CACHE = {}


def records():
    """{fact id: (paper, quantity id, kind)} of every value record with an entry: from the page's D when it exists, else from the facts
    by the page's own rule (report.build: observation, derived, model and setting facts with text)."""
    out = {}
    if PAGE.exists():
        m = re.search(r"const D=(\{.*?\}), IM=", PAGE.read_text(encoding="utf-8"), re.S)
        D = json.loads(m.group(1))
        for s in D["sources"].values():
            for v in s["values"]:
                f = v.get("fact")
                k = f.split(":")[0] if f else ""
                if f and k in Q.TREES and f in Q.TREES[k].byid:
                    q = Q.TREES[k].byid[f]["quantity"]
                    if q in L.ENTRIES:
                        out[f] = (k, q, v.get("kind", ""))
        return out, "page"
    for k, T in Q.TREES.items():
        for f in T.rows:
            if "#" in f["fact_id"] and f["type"] in ("observation", "derived", "model", "setting") and Q.text_of(f) and f["quantity"] in L.ENTRIES:
                out[f["fact_id"]] = (k, f["quantity"], f["data_kind"])
    return out, "facts"


def rendered(q, k):
    """The ids values(result=q, paper=k) renders in full (every [id] in its lines)."""
    import tools
    if (q, k) not in _CACHE:
        old, old_chars = tools.BUDGET, tools.BUDGET_CHARS
        tools.BUDGET, tools.BUDGET_CHARS = False, 10 ** 9                       # the full rendering: no collapse and no page cut (P84: the figure sets lengthen a paper's listing)
        try:
            lines, _ = tools.run_tool("values", {"result": q, "paper": k})
        finally:
            tools.BUDGET, tools.BUDGET_CHARS = old, old_chars
        _CACHE[(q, k)] = {i for _, t in lines for i in re.findall(r"\[([a-z0-9]+:[^\]\s]+)\]", t)} | {i for i, _ in lines}
    return _CACHE[(q, k)]


def home_needed(f):
    """Which home a record needs: input (on an input entity), piece (on a piece of a specimen), set (owned by a comparison set),
    paper (no entity, no set), specimen (on an experiment but not the chosen record of its key), model_run."""
    k = f.split(":")[0]; T = Q.TREES[k]
    e = T.ent_of(f)
    if e:
        r = Q.role(T, e)
        if r == "input":
            return "input"
        if r == "model run":
            return "model_run"
        return "specimen" if e in Q.experiments(T) else "piece"
    chain = T.chain(f)
    if any(T.byid[x]["type"] == "comparison" for x in chain):
        return "set"
    if any(f in {g["fact_id"] for fs in T.vector(e).values() for g in fs} for e in Q.experiments(T) + Q.inputs(T)):
        return "condition"                                                      # a stated condition some experiment or input inherits
    return "paper"


def report(verbose=True):
    recs, src = records()
    miss = {f: v for f, v in recs.items() if f not in rendered(v[1], v[0])}
    by = collections.Counter((v[0], home_needed(f)) for f, v in miss.items())
    if verbose:
        print(f"{len(recs)} value records with an entry ({src}); {len(miss)} homeless")
        for (k, h), n in sorted(by.items()):
            print(f"  {k} {h}: {n}")
        for f, (k, q, kind) in sorted(miss.items()):
            print(f"    {f} {q} ({kind}) -> {home_needed(f)}")
    return miss


def count():
    return len(report(verbose=False))


if __name__ == "__main__":
    report()
