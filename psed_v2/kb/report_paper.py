#!/usr/bin/env python3
"""P141: one page per paper, the pilot view of the gold tree and the compiled tree side by side, and the index of the pages.

    python3 psed_v2/kb/report_paper.py <paper key or id> ...      # kb/reports/paper_<pid>.html (gitignored: element text), kb/reports/papers.html

Both trees are loaded by the pilot code (query.Tree: kb/pilot/<pid>.facts.csv and kb/compiled/<pid>.facts.csv), restricted to their
facts.csv rows. P148: the experiment units (runs, specimens, simulations, model runs) pair by render.pair_units() (gold units vs the
pass-0 units the compiled tree is built from; one to one, a matched pair first); the other nodes match by evidence overlap (same
type), else by label; facts by compile.matches() (the P134 key, canonical
units, D13), one to one; a compiled fact of the same type and quantity on a shared element is a near match ("differs", the fields
shown). Sections: header, tree with the facts under each node, dropped records that would have matched (kb/compiled/<pid>.audit.csv
stage T4), elements with gold rows and no record. No model call.
"""
import collections
import csv
import html
import json
import re
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "kb" / "extract"))
import common as C   # noqa: E402
import compile as K  # noqa: E402
import query as Q    # noqa: E402

R = V2 / "kb" / "reports"
INDEX = R / "papers_index.csv"
NODE = ("paper", "activity", "entity", "comparison")
ORDER = ["setting", "observation", "derived", "model", "definition", "claim", "caveat", "cited"]
COLOUR = {"OK": "#c8f0c8", "missing": "#f6c0c0", "extra": "#dddddd", "differs": "#f8dfa0"}
STYLE = ("body{font:12px monospace;margin:16px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:1px 5px;"
         "vertical-align:top;text-align:left;overflow-wrap:anywhere}td.g,td.c{width:45%}h2{margin-top:24px}")


def rows_of(key, pid, compiled):
    """The pilot tree (query.Tree) of the gold or the compiled facts, restricted to the facts.csv rows."""
    d = K.OUT if compiled else V2 / "kb" / "pilot"
    ids = {r["fact_id"] for r in csv.DictReader((d / f"{pid}.facts.csv").open(encoding="utf-8"))}
    here, Q.HERE = Q.HERE, d
    try:
        T = Q.Tree(key)
    finally:
        Q.HERE = here
    return [r for r in T.rows if r["fact_id"] in ids]


def node_text(r):
    return f"{r['type']} {r['kind']}".strip() + (f" · {r['label_as_printed']}" if r["label_as_printed"] else "")


def fact_text(f):
    t = f["type"]
    v = f["censor"] + f["value"] if f["value"] else (f"{f['value_min']}–{f['value_max']}" if f["value_min"] or f["value_max"] else f["value_text"])
    if t == "definition":
        return f"{f['term'] or f['label_as_printed'] or '?'} → {f['quantity'] or '-'}"
    if t == "claim":
        return f"{f['cause'] or '?'} → {f['relation'] or '?'} → {f['effect'] or '?'} · {f['stance'] or '-'} · links {len([x for x in f['links'].split(';') if x])}"
    if t == "caveat":
        return f"{f['quantity'] or '-'} · links {len([x for x in f['links'].split(';') if x])}"
    if t == "cited":
        return f"{f['quantity'] or '-'} {v} {f['unit']}".strip() + (f" · {f['mentions']}" if f["mentions"] else "")
    q = f"{f['quantity']}" + (f" [{f['qualifiers']}]" if f["qualifiers"] else "")
    return f"{q} = {v} {f['unit']}".strip() + (f" · {f['data_kind']}" if f["data_kind"] else "")


def differs(g, c):
    out = [f"{k} {g[k]!r} vs {c[k]!r}" for k in ("quantity", "value_text", "qualifiers") if g[k] != c[k]]
    if K.canon(g) != K.canon(c):
        out.append(f"value {g['value'] or g['value_min']} {g['unit']} vs {c['value'] or c['value_min']} {c['unit']}")
    return "; ".join(out)


def unit_pairs(pid, key):
    """P148: gold unit id -> compiled unit row id, from render.pair_units on the pass-0 units compile.py reads (its input rule); a
    matched pair first, then the first pass-0 unit of a merged or split component; one to one."""
    import render
    run = K.Run(pid)
    run.read()
    run.tree()
    pu = render.pair_units(pid, key, [it for it in run.pass0 if isinstance(it, dict)])
    m, used = {}, set()
    for want in (True, False):
        for g, ys in pu["pair_of"].items():
            if g in m or (pu["status_g"][g] == "matched") != want:
                continue
            c = next((run.node[y][0] for y in ys if y in run.node and run.node[y][0] not in used), None)
            if c:
                m[g] = c; used.add(c)
    return m


def match_nodes(G, Cn, pre=None):
    """gold node id -> compiled node id: P148 the unit pairs (pre) first; then evidence overlap (same type), best first; then equal
    labels."""
    pairs = []
    pre = {g: c for g, c in (pre or {}).items() if any(r["fact_id"] == g for r in G) and any(r["fact_id"] == c for r in Cn)}
    for g in G:
        ge = set(filter(None, g["evidence"].split(";")))
        for c in Cn:
            if g["type"] != c["type"]:
                continue
            ce = set(filter(None, c["evidence"].split(";")))
            j = len(ge & ce) / max(len(ge | ce), 1)
            if j > 0:
                pairs.append((-j, g["fact_id"], c["fact_id"]))
    m, used = dict(pre), set(pre.values())
    for _, g, c in sorted(pairs):
        if g not in m and c not in used:
            m[g] = c; used.add(c)
    lab = lambda r: re.sub(r"\W+", " ", r["label_as_printed"].lower()).strip()   # noqa: E731
    for g in G:
        if g["fact_id"] in m or not lab(g):
            continue
        c = next((c for c in Cn if c["type"] == g["type"] and c["fact_id"] not in used and lab(c) == lab(g)), None)
        if c:
            m[g["fact_id"]] = c["fact_id"]; used.add(c["fact_id"])
    gp = next(r["fact_id"] for r in G if r["type"] == "paper")
    cp = next((r["fact_id"] for r in Cn if r["type"] == "paper"), None)
    if cp:
        m[gp] = cp
    return m


def build(arg):
    pid, key = C.resolve(arg)
    gold, comp = rows_of(key, pid, False), rows_of(key, pid, True)
    G = [r for r in gold if r["type"] in NODE and "#" not in r["fact_id"]]
    Cn = [r for r in comp if r["type"] in NODE and "#" not in r["fact_id"]]
    gf = [r for r in gold if r not in G]
    cf = [r for r in comp if r not in Cn]
    nm = match_nodes(G, Cn, unit_pairs(pid, key))
    inv = {c: g for g, c in nm.items()}
    CB = {r["fact_id"]: r for r in comp}
    used, fm = set(), {}
    for g in gf:                                                               # facts: exact matches, then near matches
        c = next((c for c in cf if c["fact_id"] not in used and K.matches(g, c)), None)
        if c:
            fm[g["fact_id"]] = ("OK", c); used.add(c["fact_id"])
    for g in gf:
        if g["fact_id"] in fm:
            continue
        ge = set(g["evidence"].split(";"))
        c = next((c for c in cf if c["fact_id"] not in used and c["type"] == g["type"] and c["quantity"] == g["quantity"] and ge & set(c["evidence"].split(";"))), None)
        if c:
            fm[g["fact_id"]] = ("differs", c); used.add(c["fact_id"])
    kids_g, kids_c = collections.defaultdict(list), collections.defaultdict(list)
    for r in G:
        kids_g[r["parent"]].append(r)
    for r in Cn:
        kids_c[r["parent"]].append(r)
    facts_g, facts_c = collections.defaultdict(list), collections.defaultdict(list)
    for f in gf:
        facts_g[f["parent"]].append(f)
    for f in cf:
        if f["fact_id"] not in used:
            facts_c[f["parent"]].append(f)
    tally = collections.Counter()
    out = []

    def cell(st, extra=""):
        base = st.split(":")[0]
        return f'<td style="background:{COLOUR.get(base, "#fff")}">{html.escape(st + extra)}</td>'

    def facts_rows(gid, cid, depth):
        pad = "&nbsp;" * (depth * 2 + 2)
        gl = sorted(facts_g.get(gid, []), key=lambda f: (ORDER.index(f["type"]) if f["type"] in ORDER else 99, f["fact_id"]))
        for f in gl:
            st, c = fm.get(f["fact_id"], ("missing", None))
            extra = ""
            if c is not None:
                if st == "differs":
                    extra = ": " + differs(f, c)
                if c["parent"] != cid:
                    st = "differs"
                    p = CB.get(c["parent"], {})
                    extra += f"{': ' if not extra else '; '}parent = {node_text(p) if p else c['parent'] or '(none)'}"
            tally[(f["type"], st.split(":")[0])] += 1
            out.append(f"<tr><td class=g>{pad}{html.escape(f['type'])}: {html.escape(fact_text(f))} <small>[{html.escape(f['evidence'])}]</small></td>"
                       f"<td class=c>{pad + html.escape(c['type'] + ': ' + fact_text(c)) + ' <small>[' + html.escape(c['evidence']) + ']</small>' if c else ''}</td>{cell(st, extra)}</tr>")
        for c in sorted(facts_c.get(cid, []) if cid else [], key=lambda f: (ORDER.index(f["type"]) if f["type"] in ORDER else 99, f["fact_id"])):
            tally[(c["type"], "extra")] += 1
            out.append(f"<tr><td class=g></td><td class=c>{pad}{html.escape(c['type'])}: {html.escape(fact_text(c))} <small>[{html.escape(c['evidence'])}]</small></td>{cell('extra')}</tr>")

    def extra_node(c, depth):
        pad = "&nbsp;" * (depth * 2)
        tally[("node", "extra")] += 1
        out.append(f"<tr><td class=g></td><td class=c>{pad}<b>{html.escape(node_text(c))}</b></td>{cell('extra')}</tr>")
        facts_rows(None, c["fact_id"], depth)
        for k in kids_c.get(c["fact_id"], []):
            if k["fact_id"] not in inv:
                extra_node(k, depth + 1)

    def gold_node(g, depth):
        pad = "&nbsp;" * (depth * 2)
        cid = nm.get(g["fact_id"])
        c = CB.get(cid) if cid else None
        st = "missing" if c is None else ("OK" if (c["type"], c["kind"]) == (g["type"], g["kind"]) else f"differs: kind {g['kind']} vs {c['kind']}")
        tally[("node", st.split(":")[0])] += 1
        out.append(f"<tr><td class=g>{pad}<b>{html.escape(node_text(g))}</b></td><td class=c>{pad + '<b>' + html.escape(node_text(c)) + '</b>' if c else ''}</td>{cell(st)}</tr>")
        facts_rows(g["fact_id"], cid, depth)
        for k in sorted(kids_g.get(g["fact_id"], []), key=lambda r: (r["type"] != "activity", r["type"] != "entity", r["kind"], r["fact_id"])):
            gold_node(k, depth + 1)
        for k in kids_c.get(cid, []) if cid else []:
            if k["fact_id"] not in inv:
                extra_node(k, depth + 1)
    root = next(r for r in G if r["type"] == "paper")
    gold_node(root, 0)
    for c in Cn:                                                               # compiled nodes whose parent chain reaches no matched node
        if c["fact_id"] not in inv and c["parent"] not in CB and c["type"] != "paper":
            extra_node(c, 1)
    # dropped records that would have matched (audit T4)
    au = list(csv.DictReader((V2 / "kb" / "compiled" / f"{pid}.audit.csv").open(encoding="utf-8")))
    GB = {r["fact_id"]: r for r in gold}
    drops = []
    for a in au:
        if a["stage"] != "T4 compiler":
            continue
        rec = json.loads(a["jsonl_record"]) if a["jsonl_record"] else {}
        g = GB.get(a["fact_id"])
        drops.append(f"<tr><td class=g>{html.escape(g['type'] + ': ' + fact_text(g)) if g else a['fact_id']} <small>[{html.escape(a['evidence'])}]</small></td>"
                     f"<td class=c>{html.escape(rec.get('element', ''))}: {html.escape(str(rec.get('quote', '')))}</td><td>{html.escape(a['detail'])}</td></tr>")
    # elements with gold rows and no record of any type
    run = K.Run(pid)
    recs = run.read()
    have = {r["eid"] for r in recs}
    kinds = {r["element_id"]: r["kind"] for r in run.els}
    with_gold = sorted({e for f in gf for e in f["evidence"].split(";") if e in kinds}, key=lambda e: run.order.get(e, 0))
    notread = [f"<tr><td>{html.escape(e)}</td><td>{html.escape(kinds[e])}</td><td>{html.escape(' '.join(run.text.get(e, '').split()[:10]))}</td></tr>"
               for e in with_gold if e not in have]
    man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus" / "manifest.csv").open(encoding="utf-8"))}
    title = man.get(pid, {}).get("title", "")
    matched = sum(1 for s, _ in fm.values() if s == "OK")
    page = [f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(key)}</title><style>{STYLE}</style></head><body>",
            f"<h1>{html.escape(key)} · {html.escape(pid)}</h1><p>{html.escape(title)}</p>",
            f"<p>gold rows {len(gold)} / compiled rows {len(comp)} / matched {matched}</p>",
            "<h2>Tree and facts</h2><table><tr><th>gold</th><th>compiled</th><th>status</th></tr>", *out, "</table>",
            "<h2>Dropped records that would have matched a gold row</h2><table><tr><th>gold</th><th>record (element: quote)</th><th>drop</th></tr>", *drops, "</table>",
            "<h2>Elements with gold rows and no record</h2><table><tr><th>element</th><th>kind</th><th>first 10 words</th></tr>", *notread, "</table></body></html>"]
    (R / f"paper_{pid}.html").write_text("\n".join(page), encoding="utf-8")
    row = dict(paper=key, pid=pid, nodes_OK=tally[("node", "OK")], nodes_missing=tally[("node", "missing")], nodes_extra=tally[("node", "extra")],
               nodes_differs=tally[("node", "differs")])
    for t in ORDER:
        for s in ("OK", "missing", "extra", "differs"):
            row[f"{t}_{s}"] = tally[(t, s)]
    return row


def index(rows):
    old = {r["paper"]: r for r in csv.DictReader(INDEX.open(encoding="utf-8"))} if INDEX.exists() else {}
    old.update({r["paper"]: r for r in rows})
    fields = list(next(iter(old.values())).keys())
    with INDEX.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(old.values())
    head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r[f]))}</td>" if f != "paper" else f"<td><a href='paper_{r['pid']}.html'>{html.escape(r[f])}</a></td>"
                                   for f in fields) + "</tr>" for r in old.values())
    (R / "papers.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>papers</title><style>{STYLE}</style></head><body>"
                                   f"<h1>papers</h1><table><tr>{head}</tr>{body}</table></body></html>", encoding="utf-8")
    return old


if __name__ == "__main__":
    done = [build(a) for a in sys.argv[1:]]
    for r in index(done).values():
        print(r["paper"], {k: v for k, v in r.items() if k not in ("paper", "pid") and str(v) != "0"})
