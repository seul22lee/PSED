#!/usr/bin/env python3
"""Checks the five tables of every pilot paper; exits 1 on any failure.

    python3 psed_v2/schema_pilot/validate.py

Checks: every id resolves (sample parents and group members, condition/series/value sample_id, value.from_series,
series.reused_from when it names a series); ids are unique; qualifiers, methods, quantities and enums come from lists.py;
no duplicate rows; every sample (other than a group's members' parents) has a condition, series or value, directly or
through a group it belongs to; a "*" sample_id appears only in condition; sample_id is empty only for literature values and cited series.
"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L
from convert import PAPERS, COLS


def check(pid):
    T = {t: list(csv.DictReader((HERE / pid / f"{t}.csv").open(encoding="utf-8"))) for t in COLS}
    err = []
    E = lambda m: err.append(m)
    S = {s["sample_id"]: s for s in T["sample"]}
    if len(S) != len(T["sample"]):
        E("duplicate sample_id")
    for t, k in (("condition", "condition_id"), ("series", "series_id"), ("value", "value_id")):
        ids = [r[k] for r in T[t]]
        if len(set(ids)) != len(ids):
            E(f"duplicate {k}: {sorted({i for i in ids if ids.count(i) > 1})[:3]}")
    for t in COLS:
        rows = [tuple(v for k, v in r.items() if not k.endswith("_id") or k == "sample_id") for r in T[t]]
        if len(set(rows)) != len(rows):
            E(f"duplicate rows in {t}: {len(rows) - len(set(rows))}")
    for s in T["sample"]:
        if s["kind"] not in L.SAMPLE_KINDS: E(f"sample kind {s['kind']} ({s['sample_id']})")
        if s["parent_sample"] and s["parent_sample"] not in S: E(f"parent {s['parent_sample']} of {s['sample_id']} not found")
        for m in filter(None, s["members"].split(";")):
            if m not in S: E(f"member {m} of {s['sample_id']} not found")
        if s["kind"] == "group" and not s["members"]: E(f"group {s['sample_id']} has no members")
    SER = {r["series_id"] for r in T["series"]}
    for t in ("condition", "series", "value"):
        for r in T[t]:
            sid = r["sample_id"]
            if sid == "*" and t != "condition": E(f"'*' in {t}")
            elif sid and sid != "*" and sid not in S: E(f"{t} {r.get(t + '_id')}: sample {sid} not found")
            if not sid and t == "condition": E(f"condition {r['condition_id']}: no sample")
            if not sid and t == "series" and r["data_kind"] != "cited": E(f"series {r['series_id']}: no sample and not cited")
            q = r.get("quantity")
            if q is not None:
                if q not in L.QUANTITIES: E(f"{t} {r.get(t + '_id')}: quantity {q} not in list")
                if q == "other" and not r["label_as_printed"]: E(f"{t} {r.get(t + '_id')}: other without label")
            for qc in ("qualifiers", "x_qualifiers", "y_qualifiers"):
                if r.get(qc) and L.qualifiers_ok(r[qc]): E(f"{t} {r.get(t + '_id')}: qualifiers {L.qualifiers_ok(r[qc])}")
            for ax in ("x_id", "y_id"):
                if r.get(ax) and r[ax] not in L.QUANTITIES: E(f"series {r['series_id']}: {ax} {r[ax]} not in list")
            if r.get("method") and r["method"] not in L.METHODS: E(f"{t} {r.get(t + '_id')}: method {r['method']}")
    for r in T["condition"]:
        if r["kind"] not in L.CONDITION_KINDS: E(f"condition kind {r['kind']}")
        if r["data_kind"] not in L.DATA_KINDS_CONDITION: E(f"condition data_kind {r['data_kind']}")
    for r in T["series"]:
        if r["kind"] not in L.SERIES_KINDS: E(f"series kind {r['kind']}")
        if r["data_kind"] not in L.DATA_KINDS_SERIES: E(f"series data_kind {r['data_kind']}")
        if not r["method"]: E(f"series {r['series_id']}: no method")
        if r["points"]:
            try:
                json.loads(r["points"])
            except ValueError:
                E(f"series {r['series_id']}: points not JSON")
        if r["data_kind"] == "schematic" and r["points"]: E(f"series {r['series_id']}: points on a schematic")
        rf = r["reused_from"].split(" ")[0].rstrip(";,") if r["reused_from"] else ""
        if rf.startswith(pid.split("_")[0]) or (rf and ":" in rf and rf.split(":")[0] == r["series_id"].split(":")[0]):
            if rf not in SER: E(f"series {r['series_id']}: reused_from {rf} not found")
    for r in T["value"]:
        if r["data_kind"] not in L.DATA_KINDS_VALUE: E(f"value data_kind {r['data_kind']}")
        if r["from_series"] and r["from_series"] not in SER: E(f"value {r['value_id']}: from_series {r['from_series']} not found")
        if not r["sample_id"] and r["data_kind"] != "literature": E(f"value {r['value_id']}: no sample and not literature")
        if r["censor"] not in L.CENSOR: E(f"value {r['value_id']}: censor {r['censor']}")
    used = {r["sample_id"] for t in ("condition", "series", "value") for r in T[t]}
    for gid, g in S.items():                                  # a sample is covered through any group it belongs to
        if gid in used and g["members"]:
            used |= set(g["members"].split(";"))
    parents = {s["parent_sample"] for s in T["sample"] if s["parent_sample"]}
    for sid, s in S.items():
        if sid not in used and not (sid in parents and any(c in used for c in [x["sample_id"] for x in T["sample"] if x["parent_sample"] == sid])):
            E(f"sample {sid} has no condition, series or value")
    return {t: len(T[t]) for t in COLS}, err


if __name__ == "__main__":
    bad = 0
    for pid in PAPERS:
        n, err = check(pid)
        print(pid, n, "OK" if not err else f"{len(err)} problems")
        for e in err[:25]:
            print("   ", e)
        bad += len(err)
    sys.exit(1 if bad else 0)
