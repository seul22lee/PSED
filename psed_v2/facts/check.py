#!/usr/bin/env python3
"""Checks facts/<paper_id>/ of every pilot paper and prints the summary; exits 1 on any failure.

    python3 psed_v2/facts/check.py

Checks: fact ids unique; evidence ids and inputs resolve; vocabularies (type, quantity, qualifiers, data_kind, method,
censor); a quantity of "other" carries label_as_printed; a value or points_ref has a quantity and a data_kind; values
are numbers; points_ref files exist and every points file is used; no two facts state the same thing (same type,
quantity, qualifiers, value, range, unit, points and mentions; or the same statement); no statement repeats eight or
more words of its element in a row (own words); coverage.csv lists every element once, nothing is "missed", covered
elements list facts that cite them, "no knowledge" has a reason.
"""
import collections, csv, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import elements  # noqa: E402

KEYS = {"10.1039_d0cp03358h": "yim20", "10.1021_acs.chemmater.2c01154": "mat22", "10.1116_6.0003182": "gre23"}


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def words(t):
    return re.findall(r"[a-z0-9]+", re.sub(r"\$|\\text\{|\\mathrm\{|[{}^_]", " ", t.lower()))


def check(pid):
    d = HERE / pid
    E, err = [], []
    els = {r["element_id"]: r for r in rd(d / "elements.csv")}
    facts = rd(d / "facts.csv")
    cov = rd(d / "coverage.csv")
    if not facts:
        return ["no facts.csv"], {}
    ids = [f["fact_id"] for f in facts]
    for i in {i for i in ids if ids.count(i) > 1}:
        err.append(f"duplicate fact_id {i}")
    F = {f["fact_id"]: f for f in facts}
    texts = C.element_texts(pid)
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
        if f["type"] not in C.TYPES:
            bad(f"type {f['type']}")
        if f["quantity"] and f["quantity"] not in C.L.QUANTITIES:
            bad(f"quantity {f['quantity']}")
        if f["quantity"] == "other" and not f["label_as_printed"]:
            bad("quantity other without label_as_printed")
        for q in C.L.qualifiers_ok(f["qualifiers"]):
            bad(f"qualifier {q}")
        if f["data_kind"] and f["data_kind"] not in C.DATA_KINDS:
            bad(f"data_kind {f['data_kind']}")
        if f["method"] and f["method"] not in C.METHODS:
            bad(f"method {f['method']}")
        if f["censor"] not in C.L.CENSOR:
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
            if not (d / f["points_ref"]).exists():
                bad(f"points_ref {f['points_ref']} missing")
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
    for p in (d / "points").glob("*.json") if (d / "points").exists() else []:
        if f"points/{p.name}" not in used_points:
            err.append(f"points/{p.name} not referenced")
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
    return err, summary(els, facts, cov)


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


if __name__ == "__main__":
    bad = 0
    for pid, k in KEYS.items():
        err, s = check(pid)
        print(f"== {k} {pid}: {'OK' if not err else f'{len(err)} problems'}")
        for e in err[:40]:
            print("  ", e)
        if s:
            print("   elements:", s["elements"])
            print("   facts:", s["n_facts"], s["facts"], "| quantity other:", s["quantity_other"])
            print("   panels:", s["panels"])
            for lab, (r, n) in (("text", s["text_numbers"]), ("table", s["table_numbers"])):
                print(f"   numbers in {lab} reaching a fact: {r}/{n} ({100 * r / max(n, 1):.0f}%)")
        bad += bool(err)
    sys.exit(1 if bad else 0)
