#!/usr/bin/env python3
"""The one check of the pilot; prints the summary and exits 1 on any failure.

    python3 psed_v2/pilot/check.py

Facts (per paper, <paper_id>.*): fact ids unique; evidence ids and inputs resolve; vocabularies (type, quantity, qualifiers, data_kind, method,
censor); a quantity of "other" carries label_as_printed; a value or points_ref has a quantity and a data_kind; values
are numbers; every points_ref names a curve of <paper_id>.points.json and every curve is used; no two facts state the same thing (same type,
quantity, qualifiers, value, range, unit, points and mentions; or the same statement); no statement repeats eight or
more words of its element in a row (own words); coverage.csv lists every element once, nothing is "missed", covered
elements list facts that cite them, "no knowledge" has a reason.
Tree (stage 3, papers with a type=paper row): one root; every other row has a parent that exists; links resolve; no cycles;
every run and group has a child; every claim has a link; a setting that varies among sibling runs or groups is never "other";
tree rows (ids without "#") are not counted as facts.
Cases: paper_case.csv has no "candidate, not used" cell in Cases 1 to 13 (every candidate is used or excluded with a reason).
"""
import collections, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as C  # noqa: E402
import lists as L  # noqa: E402
import elements  # noqa: E402
from elements import PAPERS as KEYS  # noqa: E402


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def words(t):
    return re.findall(r"[a-z0-9]+", re.sub(r"\$|\\text\{|\\mathrm\{|[{}^_]", " ", t.lower()))


def check(pid):
    err = []
    els = {r["element_id"]: r for r in rd(HERE / f"{pid}.elements.csv")}
    rows = rd(HERE / f"{pid}.facts.csv")
    facts = [r for r in rows if "#" in r["fact_id"]]                 # tree rows (stage 3) have ids without "#"
    cov = rd(HERE / f"{pid}.coverage.csv")
    pts = json.loads((HERE / f"{pid}.points.json").read_text(encoding="utf-8")) if (HERE / f"{pid}.points.json").exists() else {}
    if not facts:
        return ["no facts.csv"], {}
    ids = [f["fact_id"] for f in facts]
    for i in {i for i in ids if ids.count(i) > 1}:
        err.append(f"duplicate fact_id {i}")
    F = {f["fact_id"]: f for f in facts}
    texts = elements.texts(pid)
    seen_key, seen_stmt = {}, {}
    used_points = set()
    for f in facts:
        fid = f["fact_id"]
        bad = lambda m: err.append(f"{fid}: {m}")
        ev = f["evidence"].split(";")
        for e in ev:
            if e not in els:
                bad(f"evidence {e} not an element")
        for i in filter(None, f["inputs"].split(";")):
            if i not in F:
                bad(f"input {i} not a fact")
        if f["type"] not in L.TYPES:
            bad(f"type {f['type']}")
        if f["quantity"] and f["quantity"] not in L.QUANTITIES:
            bad(f"quantity {f['quantity']}")
        if f["quantity"] == "other" and not f["label_as_printed"]:
            bad("quantity other without label_as_printed")
        for q in L.qualifiers_ok(f["qualifiers"]):
            bad(f"qualifier {q}")
        if f["data_kind"] and f["data_kind"] not in L.DATA_KINDS:
            bad(f"data_kind {f['data_kind']}")
        if f["method"] and f["method"] not in L.METHODS:
            bad(f"method {f['method']}")
        if f["censor"] not in L.CENSOR:
            bad(f"censor {f['censor']}")
        for k in ("value", "value_min", "value_max"):
            if f[k] and C.num(f[k]) is None:
                bad(f"{k} {f[k]!r} is not a number")
        if f["value"] or f["value_min"] or f["value_max"] or f["points_ref"]:
            if not f["quantity"]:
                bad("value without quantity")
            if not f["data_kind"]:
                bad("value without data_kind")
        if f["points_ref"]:
            used_points.add(f["points_ref"])
            if f["points_ref"] not in pts:
                bad(f"points_ref {f['points_ref']} not in {pid}.points.json")
        if not f["statement"].strip() or "\n" in f["statement"]:
            bad("statement empty or not one line")
        if f["value"] or f["value_min"] or f["value_max"] or f["points_ref"]:
            key = tuple(f[k] for k in ("type", "quantity", "qualifiers", "label_as_printed", "value", "value_min", "value_max",
                                       "censor", "unit", "points_ref", "data_kind")) + \
                (tuple(sorted(m.strip().lower() for m in f["mentions"].split(";"))),)
            if key in seen_key:
                bad(f"same as {seen_key[key]}")
            seen_key[key] = fid
        s = " ".join(words(f["statement"]))
        if s in seen_stmt:
            bad(f"same statement as {seen_stmt[s]}")
        seen_stmt[s] = fid
        sw = words(f["statement"])
        grams = {tuple(sw[i:i + 8]) for i in range(len(sw) - 7)}
        for e in ev:
            tw = words(texts.get(e, ""))
            if any(tuple(tw[i:i + 8]) in grams for i in range(len(tw) - 7)):
                bad(f"statement repeats eight words of {e} in a row")
    for p in sorted(set(pts) - used_points):
        err.append(f"points {p} not referenced")
    cids = [c["element_id"] for c in cov]
    if sorted(cids) != sorted(els):
        err.append(f"coverage.csv elements differ from elements.csv ({len(set(els) - set(cids))} missing, {len(set(cids) - set(els))} extra)")
    for c in cov:
        if c["status"] == "missed":
            err.append(f"{c['element_id']}: missed (no fact, no reason)")
        elif c["status"] == "covered":
            for i in c["fact_ids"].split(";"):
                if i not in F or c["element_id"] not in F[i]["evidence"].split(";"):
                    err.append(f"{c['element_id']}: covered by {i}, which does not cite it")
        elif c["status"] == "no knowledge" and not c["reason"]:
            err.append(f"{c['element_id']}: no knowledge without a reason")
    err += check_tree(rows, els)
    s = summary(els, facts, cov)
    s["tree"] = tree_summary(rows) if any(r["type"] == "paper" for r in rows) else {}
    return err, s


def check_tree(rows, els):
    """Stage 3, for a paper that has its tree (a type=paper row): one root; every other row has a parent that exists; links
    resolve; no cycles; every run has a child; every claim has a link; tree rows use the node types (cited works: cited)."""
    if not any(r["type"] == "paper" for r in rows):
        return []
    err = []
    R = {r["fact_id"]: r for r in rows}
    roots = [r["fact_id"] for r in rows if not r.get("parent")]
    if [R[i]["type"] for i in roots] != ["paper"]:
        err.append(f"tree: roots {roots[:5]} (want one paper row)")
    for r in rows:
        i, p = r["fact_id"], r.get("parent", "")
        if p and p not in R:
            err.append(f"{i}: parent {p} does not exist")
        for l in filter(None, r.get("links", "").split(";")):
            if l not in R:
                err.append(f"{i}: link {l} does not exist")
        if "#" not in i:
            if r["type"] not in L.NODE_TYPES + ["cited"]:
                err.append(f"{i}: tree row type {r['type']}")
            for e in filter(None, r["evidence"].split(";")):
                if e not in els:
                    err.append(f"{i}: evidence {e} not an element")
            for q in L.qualifiers_ok(r["qualifiers"]):
                err.append(f"{i}: qualifier {q}")
        if r["type"] == "claim" and not r.get("links"):
            err.append(f"{i}: claim without links")
    for r in rows:                                                      # walk up: must reach the root without a repeat
        seen, i = set(), r["fact_id"]
        while i in R and R[i].get("parent"):
            if i in seen:
                err.append(f"{r['fact_id']}: cycle through {i}"); break
            seen.add(i); i = R[i]["parent"]
    kids = collections.Counter(r.get("parent") for r in rows)
    for r in rows:
        if r["type"] in ("run", "group") and not kids[r["fact_id"]]:
            err.append(f"{r['fact_id']}: {r['type']} without children")
    # what a group varies is never "other": among sibling runs (or sibling groups, each taken with its own facts and its
    # runs' facts), a setting present in two siblings with different values
    K = collections.defaultdict(list)
    for r in rows:
        if r.get("parent"):
            K[r["parent"]].append(r)
    def sub(i, deep=False):
        out = []
        for ch in K.get(i, []):
            if ch["type"] in ("run", "group"):
                if deep:
                    out += sub(ch["fact_id"], True)
                continue
            if "#" in ch["fact_id"]:
                out.append(ch)
            out += sub(ch["fact_id"], deep)
        return out
    for r in rows:
        runs = [ch for ch in K.get(r["fact_id"], []) if ch["type"] in ("run", "group")]   # sibling runs, or sibling groups
        if len(runs) < 2:
            continue
        per = collections.defaultdict(dict)
        for run in runs:
            for f in sub(run["fact_id"], run["type"] == "group"):
                if f["type"] == "setting" and f["quantity"]:
                    key = (f["quantity"], f["qualifiers"], f["label_as_printed"] if f["quantity"] == "other" else "")
                    v = f["censor"] + f["value"] + f["unit"] if f["value"] else f["statement"].split(": ", 1)[-1]
                    per[key][run["fact_id"]] = per[key].get(run["fact_id"], "") + "|" + v
        for key, m in per.items():
            if key[0] == "other" and len(set(m.values())) > 1:
                err.append(f"{r['fact_id']}: varies setting other '{key[2]}' among its runs; give it an id in lists.py")
    return err


def tree_summary(rows):
    R = {r["fact_id"]: r for r in rows}
    root = next(r["fact_id"] for r in rows if r["type"] == "paper")
    under = [r for r in rows if r.get("parent") == root and "#" in r["fact_id"]]
    runs = collections.Counter(re.search(r"run=(\w+)", r["qualifiers"]).group(1) for r in rows if r["type"] == "run")
    return dict(tree_rows=collections.Counter(r["type"] for r in rows if "#" not in r["fact_id"]), runs=dict(runs),
                under_paper=collections.Counter(r["type"] for r in under),
                claims_unlinked=sum(1 for r in rows if r["type"] == "claim" and not r.get("links")))


def summary(els, facts, cov):
    st = {c["element_id"]: c["status"] for c in cov}
    kinds = collections.Counter((els[e]["kind"], st.get(e, "?")) for e in els)
    by_el = collections.defaultdict(list)
    for f in facts:
        for e in f["evidence"].split(";"):
            by_el[e].append(f)
    panels = collections.Counter()
    for e, r in els.items():
        if r["kind"] != "panel":
            continue
        fs = by_el.get(e, [])
        panels["with points" if any(f["points_ref"] for f in fs) else "stated values only" if any(f["value"] or f["value_min"] or f["value_max"] for f in fs)
               else "facts, no values" if fs else "no knowledge"] += 1
    nn = sum(int(c["n_numbers"] or 0) for c in cov if els[c["element_id"]]["kind"] in ("paragraph", "abstract"))
    nr = sum(int(c["n_numbers_reached"] or 0) for c in cov if els[c["element_id"]]["kind"] in ("paragraph", "abstract"))
    tn = sum(int(c["n_numbers"] or 0) for c in cov if els[c["element_id"]]["kind"] == "table_cell")
    tr = sum(int(c["n_numbers_reached"] or 0) for c in cov if els[c["element_id"]]["kind"] == "table_cell")
    return dict(elements={k: {s: n for (k2, s), n in kinds.items() if k2 == k} for k in sorted({k for k, _ in kinds})},
                facts=dict(collections.Counter(f["type"] for f in facts)), n_facts=len(facts), panels=dict(panels),
                text_numbers=(nr, nn), table_numbers=(tr, tn),
                quantity_other=sum(f["quantity"] == "other" for f in facts))


def check_cases():
    rows = rd(HERE / "paper_case.csv")
    left = [(k, r["paper_id"]) for r in rows for k in (f"c{i}" for i in range(1, 14)) if r.get(k, "").startswith("candidate")]
    return [f"paper_case.csv: {k} {p} is a candidate not resolved" for k, p in left] + ([] if rows else ["no paper_case.csv"])


if __name__ == "__main__":
    bad = 0
    err = check_cases()
    print(f"== cases: {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    for pid, k in KEYS.items():
        err, s = check(pid)
        print(f"== {k} {pid}: {'OK' if not err else f'{len(err)} problems'}")
        for e in err[:40]:
            print("  ", e)
        if s:
            print("   elements:", s["elements"])
            print("   facts:", s["n_facts"], s["facts"], "| quantity other:", s["quantity_other"])
            if s.get("tree"):
                t = s["tree"]
                print("   tree rows:", dict(t["tree_rows"]), "| runs:", t["runs"], "| facts directly under the paper:",
                      sum(t["under_paper"].values()), dict(t["under_paper"]), "| claims without links:", t["claims_unlinked"])
            print("   panels:", s["panels"])
            for lab, (r, n) in (("text", s["text_numbers"]), ("table", s["table_numbers"])):
                print(f"   numbers in {lab} reaching a fact: {r}/{n} ({100 * r / max(n, 1):.0f}%)")
        bad += bool(err)
    sys.exit(1 if bad else 0)
