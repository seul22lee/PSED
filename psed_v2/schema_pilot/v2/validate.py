#!/usr/bin/env python3
"""Checks the v2 tables of every pilot paper and prints coverage shares; exits 1 on any failure.

    python3 psed_v2/schema_pilot/v2/validate.py

Checks: ids unique and resolving (parents, members, sample_id, from_series, reused_from, equation ids in relation);
vocabularies of lists.py (quantity, qualifiers, method, kinds, data_kind, censor, canonical units); no duplicate rows; one
condition per sample + quantity + label + qualifiers + kind, and no condition that repeats a "*" row for one sample; every
measured or fit value whose sample has a series of the same quantity names a from_series; every evidence starts with
inventory element ids; every inventory element appears once in coverage.csv, a covered element lists rows that exist and
cite it, a "no knowledge" element gives a reason; every sample has a condition, series or value.
Coverage shares: table cells, figure panels and equations covered; numbers in paragraphs that reach a row citing the paragraph.
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import lists as L
from inventory import PAPERS, numbers, build

TABLES = ["paper", "sample", "condition", "series", "value"]
ID = re.compile(r"^(abs\.g\d+|s\d+\.(?:h|p\d+|x\d+)|fig[\dA-Za-z]+(?:\.cap)?|tab[\dIVX]+(?:\.cap|\.r\d+c\d+)|eq\d+)$")


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def ev_ids(ev):
    out = []
    for tok in re.split(r"[;,\s]+", ev or ""):
        if ID.match(tok):
            out.append(tok)
        elif out:
            break
        else:
            break
    return out


def num(x):
    try:
        return float(str(x).replace("−", "-").replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def nums_of(text):
    out = set()
    for t in re.findall(r"[-−]?\d+(?:[.,]\d+)?(?:[eE][-−+]?\d+)?", text or ""):
        v = num(t)
        if v is not None:
            out.add(round(v, 9)); out.add(round(abs(v), 9))
    return out


def check(pid):
    D = HERE / pid
    T = {t: rd(D / f"{t}.csv") for t in TABLES}
    INV = {r["element_id"]: r for r in rd(D / "inventory.csv")}
    COV = rd(D / "coverage.csv")
    err = []
    E = err.append
    if not T["sample"]:
        return {t: 0 for t in TABLES}, ["no tables"], {}
    S = {s["sample_id"]: s for s in T["sample"]}
    rowid = {"sample": "sample_id", "condition": "condition_id", "series": "series_id", "value": "value_id"}
    allrows = {}
    for t, k in rowid.items():
        ids = [r[k] for r in T[t]]
        if len(set(ids)) != len(ids):
            E(f"duplicate {k}: {sorted({i for i in ids if ids.count(i) > 1})[:3]}")
        for r in T[t]:
            allrows[r[k]] = (t, r)
        rows = [tuple(v for c, v in r.items() if c != k) for r in T[t]]
        if t != "sample" and len(set(rows)) != len(rows):           # two pieces of one run may share every identity column
            E(f"{len(rows) - len(set(rows))} duplicate rows in {t}")
        for r in T[t]:
            ids_ = ev_ids(r.get("evidence", ""))
            if not ids_:
                E(f"{t} {r[k]}: evidence does not start with an element id ({r.get('evidence', '')[:40]})")
            for i in ids_:
                if i not in INV: E(f"{t} {r[k]}: element {i} not in the inventory")
    for s in T["sample"]:
        if s["kind"] not in L.SAMPLE_KINDS: E(f"sample kind {s['kind']}")
        if s["parent_sample"] and s["parent_sample"] not in S: E(f"parent {s['parent_sample']} not found")
        for m in filter(None, s["members"].split(";")):
            if m not in S: E(f"member {m} of {s['sample_id']} not found")
        if s["kind"] == "group" and not s["members"]: E(f"group {s['sample_id']} without members")
    SER = {r["series_id"]: r for r in T["series"]}
    eqs = {i for i in INV if i.startswith("eq")}
    for t in ("condition", "series", "value"):
        for r in T[t]:
            rid = r[rowid[t]]; sid = r["sample_id"]
            if sid == "*" and t != "condition": E(f"'*' in {t} {rid}")
            elif sid and sid != "*" and sid not in S: E(f"{t} {rid}: sample {sid} not found")
            if not sid:
                if t == "condition" or (t == "series" and r["data_kind"] != "cited") or (t == "value" and r["data_kind"] != "literature"):
                    E(f"{t} {rid}: no sample")
            q = r.get("quantity")
            if q is not None:
                if q not in L.QUANTITIES: E(f"{t} {rid}: quantity {q}")
                if q == "other" and not r["label_as_printed"]: E(f"{t} {rid}: other without label")
                if q in L.UNITS and r["unit"] != L.UNITS[q] and (r["value"] or r["value_min"] if t == "value" else r["value"]):
                    E(f"{t} {rid}: unit '{r['unit']}' for {q} (expected '{L.UNITS[q]}')")
            for qc in ("qualifiers", "x_qualifiers", "y_qualifiers"):
                if r.get(qc) and L.qualifiers_ok(r[qc]): E(f"{t} {rid}: qualifiers {L.qualifiers_ok(r[qc])}")
            for ax in ("x_id", "y_id", "z_id"):
                if r.get(ax) and r[ax] not in L.QUANTITIES: E(f"series {rid}: {ax} {r[ax]}")
            if r.get("method") and r["method"] not in L.METHODS: E(f"{t} {rid}: method {r['method']}")
    for r in T["condition"]:
        if r["kind"] not in L.CONDITION_KINDS: E(f"condition {r['condition_id']} kind {r['kind']}")
        if r["data_kind"] not in L.DATA_KINDS_CONDITION: E(f"condition {r['condition_id']} data_kind {r['data_kind']}")
    key = lambda r: (r["sample_id"], r["kind"], r["quantity"], r["label_as_printed"], r["qualifiers"], r["applies_when"])
    seen = {}
    for r in T["condition"]:
        if key(r) in seen: E(f"conditions {seen[key(r)]} and {r['condition_id']} share sample, quantity and qualifiers")
        seen[key(r)] = r["condition_id"]
    star = {(r["kind"], r["quantity"], r["label_as_printed"], r["qualifiers"], r["value"], r["unit"]) for r in T["condition"] if r["sample_id"] == "*"}
    for r in T["condition"]:
        if r["sample_id"] != "*" and (r["kind"], r["quantity"], r["label_as_printed"], r["qualifiers"], r["value"], r["unit"]) in star:
            E(f"condition {r['condition_id']} repeats a '*' row for {r['sample_id']}")
    for r in T["series"]:
        if r["kind"] not in L.SERIES_KINDS: E(f"series {r['series_id']} kind {r['kind']}")
        if r["data_kind"] not in L.DATA_KINDS_SERIES: E(f"series {r['series_id']} data_kind {r['data_kind']}")
        if r["points"]:
            try: json.loads(r["points"])
            except ValueError: E(f"series {r['series_id']}: points not JSON")
        if r["data_kind"] == "schematic" and r["points"]: E(f"series {r['series_id']}: points on a schematic")
        rf = (r["reused_from"] or "").split(" ")[0].rstrip(";,")
        if rf and ":" in rf and rf not in SER: E(f"series {r['series_id']}: reused_from {rf} not found")
    groups = {g["sample_id"]: set(g["members"].split(";")) for g in T["sample"] if g["kind"] == "group"}
    for v in T["value"]:
        if v["data_kind"] not in L.DATA_KINDS_VALUE: E(f"value {v['value_id']} data_kind {v['data_kind']}")
        if v["censor"] not in L.CENSOR: E(f"value {v['value_id']} censor {v['censor']}")
        if v["from_series"] and v["from_series"] not in SER: E(f"value {v['value_id']}: from_series {v['from_series']} not found")
        m = re.match(r"^(eq\d+)", v["relation"] or "")
        if m and m.group(1) not in eqs: E(f"value {v['value_id']}: relation {m.group(1)} not in the inventory")
        if v["data_kind"] in ("measured", "fit") and not v["from_series"] and v["quantity"] != "other":
            same = [s for s in T["series"] if (s["sample_id"] == v["sample_id"] or v["sample_id"] in groups.get(s["sample_id"], ())) and s["y_id"] == v["quantity"]
                    and s["data_kind"] in ("measured", "fit")]
            if same: E(f"value {v['value_id']} ({v['quantity']}) has a series of the same measurement ({same[0]['series_id']}) but no from_series")
    used = {r["sample_id"] for t in ("condition", "series", "value") for r in T[t]}
    for gid, mem in groups.items():
        if gid in used: used |= mem
    parents = {s["parent_sample"] for s in T["sample"] if s["parent_sample"]}
    for sid in S:
        if sid not in used and sid not in parents: E(f"sample {sid} has no condition, series or value")
    # coverage
    cov = {}
    for c in COV:
        if c["element_id"] in cov: E(f"coverage: {c['element_id']} twice")
        cov[c["element_id"]] = c
    for eid in INV:
        c = cov.get(eid)
        if not c: E(f"coverage: element {eid} missing"); continue
        if c["status"] == "covered":
            rows = [x for x in re.split(r"[;,\s]+", c["rows"]) if x]
            if not rows: E(f"coverage {eid}: covered without rows")
            for x in rows:
                if x not in allrows: E(f"coverage {eid}: row {x} not found")
                elif eid not in ev_ids(allrows[x][1].get("evidence", "")): E(f"coverage {eid}: row {x} does not cite it")
        elif c["status"] == "no knowledge":
            if not c["reason"]: E(f"coverage {eid}: no knowledge without a reason")
        else:
            E(f"coverage {eid}: status {c['status']}")
    for c in cov:
        if c not in INV: E(f"coverage: {c} not in the inventory")
    # shares
    cites = {}
    for rid, (t, r) in allrows.items():
        for i in ev_ids(r.get("evidence", "")):
            cites.setdefault(i, []).append(r)
    share = {}
    for kind, lab in (("table_cell", "table cells"), ("panel", "figure panels"), ("equation", "equations")):
        els = [e for e, r in INV.items() if r["kind"] == kind]
        share[lab] = (sum(1 for e in els if cov.get(e, {}).get("status") == "covered"), len(els))
    tot = hit = 0
    text = build(pid)[1]                                       # element texts straight from ingest/final
    for e, r in INV.items():
        if r["kind"] != "paragraph" or e not in text:
            continue
        got = set()
        for row in cites.get(e, []):
            got |= nums_of(" ".join(str(v) for v in row.values()))
        for n in numbers(text[e]):
            v = num(re.sub(r"\s*[×x].*", "", n))
            tot += 1
            if v is not None and (round(v, 9) in got or round(abs(v), 9) in got):
                hit += 1
    share["numbers in the text"] = (hit, tot)
    return {t: len(T[t]) for t in TABLES}, err, share


if __name__ == "__main__":
    bad = 0
    for pid in PAPERS:
        n, err, share = check(pid)
        print(pid, n, "OK" if not err else f"{len(err)} problems", {k: f"{a}/{b} ({a / b:.0%})" if b else "0/0" for k, (a, b) in share.items()} if share else "")
        for e in err[:30]:
            print("   ", e)
        bad += len(err)
    sys.exit(1 if bad else 0)
