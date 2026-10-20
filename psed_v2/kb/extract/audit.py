#!/usr/bin/env python3
"""P135b: where the pipeline loses each gold row of one paper. No provider call; no fix.

    python3 psed_v2/kb/extract/audit.py yli18 [--unit P136]      # report tables go to kb/reports/<unit>.*.csv (default P135b)

Per gold row of kb/pilot/<pid>.facts.csv the first stage test that fails:
  T0 tree      a tree row (no '#' in fact_id, or type paper/activity/entity/comparison/identity); a setting with no quantity, value
               or value_text is stage judgment
  T1 ontology  quantity not in the form's quantity enum; unit not in units.yaml (vocab.UNIT_ALIAS / UNIT_BASE); value_text of a
               species/structure quantity not among its ids
  T2 form      the row cast into a form record (form_roundtrip.cast; quote = the first 15 words of the statement) fails form.json
               (first error; P135c: a quantity without label_as_printed gets the quantity id, quantity other without candidate a stub
               candidate, both listed in cast_fills); gold columns with no form slot go to no_slot and are not a failure
  T3 prompt    no record of the 22 lines in use (compile.py input rule) on an evidence element with the gold type
  T3q          such records exist, none with the gold quantity (P135c)
  T4 compiler  the matching record was dropped (compile.py step, reason, field)
  T5 mismatch  the matching record reached facts.csv but the P134 match (type, quantity, value in canonical units, value_text) fails
  (P136: the rows compile.py builds from figures.json count as records of their evidence elements)
  T6 matched
  parent (P138, T5/T6 rows): the compiled row's parent class (type kind) against the gold row's: correct, wrong, or paper (the
  compiled row sits on the paper where the gold's does not)
Several matching records: the first that reached facts.csv decides (T6 if any matches, else T5), else the first dropped (T4).
The compiler is re-run in memory (outputs to a temporary folder) so that each record is followed to its drop or its fact row.
Writes kb/compiled/<pid>.audit.csv (gold side) and .audit_reverse.csv (compiled facts no gold row matches); the element text goes
only to the gitignored kb/reports/<unit>.text.csv (paper text stays out of git).
"""
import collections
import csv
import json
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

import common as C
import compile as K
import form_roundtrip as RT

import lists as L  # noqa: E402  (kb/pilot/, on the path through common)
import vocab as V  # noqa: E402

TREE_TYPES = {"paper", "activity", "entity", "comparison", "identity"}
NO_SLOT = ("links", "inputs", "parent", "figure_ref")
COLS = ["fact_id", "type", "quantity", "value", "unit", "value_text", "evidence", "stage", "detail", "cast_fills", "no_slot", "same_element_same_type",
        "same_element_same_type_same_quantity", "parent", "parent_flagged", "parent_source", "jsonl_record", "compiled_row"]
REV = ["fact_id", "type", "quantity", "value", "unit", "value_text", "evidence", "nearest_gold", "why"]


def matches(g, c):
    """compile.matches: the P134 match with canonical units (1d) and D13."""
    return K.matches(g, c)


def same(x, f):
    """x is the row compile.dedupe kept for f: a definition by its normalized term (P136 1a), any other row by DEDUPE_KEY."""
    if K.text_key(f) is not None:                                               # P138: claims, caveats, definitions keyed with the quote
        return K.text_key(x) == K.text_key(f)
    return all(x[k] == f[k] for k in K.DEDUPE_KEY)


def traced_run(pid):
    """compile.Run in a temporary folder, with each record followed: {id(rec): ('drop', step, reason, field) | ('fact', row)}."""
    K.OUT = Path(tempfile.mkdtemp(prefix="audit_"))
    run = K.Run(pid)
    fate, made, fig_records = {}, {}, []
    drop, fact_row, dedupe = run.drop, run.fact_row, run.dedupe

    def drop_t(step, eid, rec, reason, field=""):
        fate.setdefault(id(rec), ("drop", step, reason, field))
        return drop(step, eid, rec, reason, field)

    def fact_row_t(r, parent):
        f = fact_row(r, parent)
        made[id(f)] = id(r["rec"])
        return f

    def dedupe_t(items):
        out = dedupe(items)
        kept = {id(f) for f in out}
        for f in items:                                                         # a merged row: its record lives on in the row it merged into
            if id(f) not in made:                                               # P136: a row from figures.json (compile 1c) stands in as its own record
                rec = dict(type=f["type"], quantity=f["quantity"], source="figures.json", label_as_printed=f["label_as_printed"])
                fig_records.append(dict(eid=f["evidence"].split(";")[0], rec=rec, evidence=f["evidence"].split(";")))
                made[id(f)] = id(rec)
            g = f if id(f) in kept else next(x for x in out if same(x, f) and set(f["evidence"].split(";")) <= set(x["evidence"].split(";")))
            fate[made[id(f)]] = ("fact", g)
        return out
    run.drop, run.fact_row, run.dedupe = drop_t, fact_row_t, dedupe_t
    records = run.read()                                                        # the records as compile.py reads them (variables mapped)
    run.read = lambda: records
    rows = run.run()
    return run, records + fig_records, fate, rows


def ontology_test(g, qids):
    bad = []
    for q in filter(None, g["quantity"].split(";")):
        if q not in qids:
            bad.append(f"quantity {q} not in the form enum")
    if g["unit"] and V.UNIT_ALIAS.get(g["unit"], g["unit"]) not in V.UNIT_BASE:
        bad.append(f"unit {g['unit']!r} not in units.yaml")
    if g["quantity"] in K.SPECIES_Q and g["value_text"] and g["value_text"] not in K.SPECIES_Q[g["quantity"]]:
        bad.append(f"{g['quantity']} {g['value_text']!r} not an id")
    return "; ".join(bad)


def form_test(g, val, props):
    rec, lost = RT.cast(g, props)
    rec["quote"] = " ".join(g["statement"].split()[:15])
    if g.get("term") and "term" in props:                                       # P136: the form has term now
        rec["term"] = g["term"]
    fills = []
    if g.get("statement") and "statement" in props:                            # P138: the form has statement now (own words)
        rec["statement"] = g["statement"]; fills.append("statement=gold statement")
    if isinstance(rec.get("quantity"), str) and ";" in rec["quantity"]:        # P138: a caveat's several quantities are a list in the form
        rec["quantity"] = rec["quantity"].split(";"); fills.append("quantity split into a list")
    if rec.get("quantity") and not rec.get("label_as_printed"):                 # P135c: gold's filing convention, not expressibility
        rec["label_as_printed"] = ";".join(rec["quantity"]) if isinstance(rec["quantity"], list) else rec["quantity"]; fills.append("label_as_printed=quantity id")
    if rec.get("quantity") == "other" and "candidate" not in rec:
        rec["candidate"] = dict(definition_quote=g["statement"], unit_as_printed=g["unit"], dimension="dimensionless", symbol=g["label_as_printed"] or "?")
        fills.append("candidate=stub")
    for k in props:                                                             # P139: every field present, null when the gold has none
        rec.setdefault(k, None)
    no_slot = [c for c, _ in lost] + [c for c in NO_SLOT if g.get(c)]
    errs = sorted(val.iter_errors(rec), key=lambda e: list(e.absolute_path))
    if not errs:
        return "", no_slot, fills
    field, reason = RT.explain(errs[0], rec)
    return f"{field}: {reason}", no_slot, fills


def rec_json(r):
    return json.dumps(dict(element=r["eid"], **r["rec"]), ensure_ascii=False)


def differing(g, c):
    """The fields that differ; value and unit compared in canonical units (compile.canon), the raw strings shown beside them."""
    out = []
    for k in ("type", "quantity", "value_text"):
        a, b = g[k], c[k]
        if (a.lower() if k == "value_text" else a) != (b.lower() if k == "value_text" else b):
            out.append(f"{k} {a!r} vs {b!r}")
    cg, cc = K.canon(g), K.canon(c)
    if cg != cc:
        out.append(f"value {g['value']!r} {g['unit']!r} vs {c['value']!r} {c['unit']!r} (canonical {cg} vs {cc})")
    return "; ".join(out) or "evidence shares no element"


def parent_class(rows, fid):
    """The (type, kind) of a row's parent ('paper' for the paper row)."""
    p = rows.get(rows.get(fid, {}).get("parent", ""), {})
    return "paper" if p.get("type") == "paper" else f"{p.get('type', '')} {p.get('kind', '')}".strip() or "none"


def main(arg):
    pid, key_ = C.resolve(arg)
    form = C.schema("form.json")
    val, props, qids = Draft202012Validator(form), form["properties"], set(form["$defs"]["quantity_id"]["enum"]) | {"other"}
    gold = list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{pid}.facts.csv").open(encoding="utf-8")))
    run, records, fate, rows = traced_run(pid)
    comp = [r for r in rows if "#" in r["fact_id"]]
    CR, GR = {r["fact_id"]: r for r in rows}, {r["fact_id"]: r for r in gold}
    out, texts, matched_c = [], [], set()
    for g in gold:
        ev = [e for e in g["evidence"].split(";") if e]
        a = {c: g[c] for c in COLS if c in g}
        a.update(parent="", parent_flagged="", parent_source="", stage="", detail="", cast_fills="", no_slot="", same_element_same_type="", same_element_same_type_same_quantity="", jsonl_record="", compiled_row="")
        texts.append(dict(fact_id=g["fact_id"], element_text=" | ".join(f"{e}: {run.text.get(e, '')}" for e in ev)))
        if "#" not in g["fact_id"] or g["type"] in TREE_TYPES:
            a.update(stage="T0 tree", detail=g["type"]); out.append(a); continue
        if g["type"] == "setting" and not (g["quantity"] or g["value"] or g["value_text"]):
            a.update(stage="T0 judgment", detail="setting without quantity, value or value_text"); out.append(a); continue
        o = ontology_test(g, qids)
        if o:
            a.update(stage="T1 ontology", detail=o); out.append(a); continue
        err, no_slot, fills = form_test(g, val, props)
        a["no_slot"], a["cast_fills"] = ";".join(no_slot), ";".join(fills)
        if err:
            a.update(stage="T2 form", detail=err); out.append(a); continue
        on_el = [r for r in records if (set(r.get("evidence") or [r["eid"]]) & set(ev))]
        typed = [r for r in on_el if r["rec"].get("type") == g["type"]]
        valueless_model = g["type"] == "model" and not (g["value"] or g["value_min"] or g["value_max"] or g["value_text"])   # D13
        hits = [r for r in typed if not g["quantity"] or valueless_model or r["rec"].get("quantity") == g["quantity"]]
        a.update(same_element_same_type=len(typed), same_element_same_type_same_quantity=len(hits))
        if typed and not hits:
            a.update(stage="T3q", detail=f"quantities of the {len(typed)} {g['type']} records: {dict(collections.Counter(r['rec'].get('quantity', '') for r in typed))}")
            out.append(a); continue
        if not hits:
            a.update(stage="T3 prompt", detail=f"{len(on_el)} records on the evidence elements, of types {dict(collections.Counter(r['rec'].get('type') for r in on_el))}")
            out.append(a); continue
        facts = [(r, fate[id(r["rec"])][1]) for r in hits if fate.get(id(r["rec"]), ("",))[0] == "fact"]
        drops = [(r, fate[id(r["rec"])]) for r in hits if fate.get(id(r["rec"]), ("",))[0] == "drop"]
        good = [(r, c) for r, c in facts if matches(g, c)]
        if good:
            r, c = good[0]
            matched_c.add(c["fact_id"])
            a.update(stage="T6 matched", jsonl_record=rec_json(r), compiled_row=c["fact_id"])
            pc, pg = parent_class(CR, c["fact_id"]), parent_class(GR, g["fact_id"])
            a["parent"] = "paper" if pc == "paper" and pg != "paper" else "correct" if pc == pg else f"wrong ({pc} vs gold {pg})"
            a["parent_flagged"] = "yes" if c.get("_parent_filled") else "no"           # P140 C3: the record's parent was null or unknown
            a["parent_source"] = c.get("_source") or ("derived()" if c.get("data_kind") == "computed_by_kb" else "figures()")
        elif facts:
            r, c = facts[0]
            d = differing(g, c)
            a.update(stage="T5 mismatch", detail=d, jsonl_record=rec_json(r), compiled_row=f"{c['fact_id']}: {d}")
            pc, pg = parent_class(CR, c["fact_id"]), parent_class(GR, g["fact_id"])
            a["parent"] = "paper" if pc == "paper" and pg != "paper" else "correct" if pc == pg else f"wrong ({pc} vs gold {pg})"
            a["parent_flagged"] = "yes" if c.get("_parent_filled") else "no"           # P140 C3: the record's parent was null or unknown
            a["parent_source"] = c.get("_source") or ("derived()" if c.get("data_kind") == "computed_by_kb" else "figures()")
        elif drops:
            r, (_, step, reason, field) = drops[0]
            a.update(stage="T4 compiler", detail=f"step {step}: {reason}" + (f" ({field})" if field else ""), jsonl_record=rec_json(r))
        else:
            a.update(stage="T4 compiler", detail="record neither dropped nor in facts.csv", jsonl_record=rec_json(hits[0]))
        out.append(a)
    rev = []
    for c in comp:
        if c["fact_id"] in matched_c or any(matches(g, c) for g in gold if "#" in g["fact_id"]):
            continue
        same = [g for g in gold if "#" in g["fact_id"] and set(g["evidence"].split(";")) & set(c["evidence"].split(";"))]
        near = sorted(same, key=lambda g: (g["type"] != c["type"], g["quantity"] != c["quantity"]))
        rev.append(dict({k: c[k] for k in REV[:7]}, nearest_gold=near[0]["fact_id"] if near else "",
                        why=differing(near[0], c) if near else "no gold row on this element"))
    D = C.V2 / "kb" / "compiled"
    K.write_csv(D / f"{pid}.audit.csv", COLS, out)
    K.write_csv(D / f"{pid}.audit_reverse.csv", REV, rev)
    R = C.V2 / "kb" / "reports"
    unit = sys.argv[sys.argv.index("--unit") + 1] if "--unit" in sys.argv else "P135b"
    K.write_csv(R / f"{unit}.text.csv", ["fact_id", "element_text"], texts)            # gitignored: paper text
    st = collections.Counter((a["stage"], a["type"]) for a in out)
    types = sorted({a["type"] for a in out}, key=lambda t: -sum(v for (s, ty), v in st.items() if ty == t))
    stages = sorted({a["stage"] for a in out})
    with (R / f"{unit}.stage_type.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["stage"] + types + ["total"])
        for s in stages:
            w.writerow([s] + [st[(s, t)] for t in types] + [sum(st[(s, t)] for t in types)])
        w.writerow(["total"] + [sum(st[(s, t)] for s in stages) for t in types] + [len(out)])
    for name, stage in (("t2_errors", "T2 form"), ("t4_reasons", "T4 compiler")):
        c = collections.Counter(a["detail"] for a in out if a["stage"] == stage)
        with (R / f"{unit}.{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["detail", "rows"])
            w.writerows(c.most_common())
    with (R / f"{unit}.t3_split.csv").open("w", newline="", encoding="utf-8") as fh:  # P135c: T3 (no record of the type) vs T3q (no record with the quantity)
        w = csv.writer(fh)
        w.writerow(["type", "T3 prompt", "T3q"])
        w.writerows([t, st[("T3 prompt", t)], st[("T3q", t)]] for t in types if st[("T3 prompt", t)] or st[("T3q", t)])
    print(f"{key_}: {len(out)} gold rows, {len(rev)} compiled facts without a gold match")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
