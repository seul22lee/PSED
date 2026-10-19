#!/usr/bin/env python3
"""P132 round trip: every record of the 12 gold pilot/<paper_id>.facts.csv cast into the extraction form and validated against schema/form.json.

    python3 psed_v2/scripts/form_roundtrip.py      # writes verify/d15/roundtrip.csv and roundtrip_summary.txt

The cast maps columns 1:1 (ontology/export.py form_field), drops the compiler-only columns, and does no repair and no inference: a
'k=v;k=v' qualifier string becomes an object, a ';' list of mentions a list, a number column (and a number-valued qualifier) a number
when the text parses as one. There is no quote column in facts.FIELDS, so every record fails with quote: absent (not fabricated).
A non-empty column with no form field is a failure of that column. Rows of the tree types (paper, activity, entity) and of comparison
and identity are not form records and are not cast. Needs jsonschema (draft 2020-12).
"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ontology"))
import export as X  # noqa: E402

OUT = ROOT / "verify" / "d15"
GOLD = sorted((ROOT / "pilot").glob("10.*.facts.csv"))


def numeric(p):
    return p.get("type") == "number" or any(x.get("type") == "number" for x in p.get("anyOf", []))


def as_number(x):
    try:
        return float(x)
    except ValueError:
        return x


def cast(row, props):
    """facts.csv row -> (form record, [(field, reason)] for the columns the form cannot take)."""
    rec, lost = {}, []
    for c, v in row.items():
        if not v or c in X.COMPILER_ONLY:
            continue
        f = X.form_field(c)
        if f not in props:
            lost.append((c, "no form field"))
        elif f == "qualifiers":
            q = {}
            for part in filter(None, v.split(";")):
                k, _, val = part.partition("=")
                qp = props["qualifiers"]["properties"].get(k, {})
                q[k] = as_number(val) if numeric(qp) else val
            rec[f] = q
        elif f == "mentions":
            rec[f] = [m.strip() for m in v.split(";") if m.strip()]
        else:
            rec[f] = as_number(v) if numeric(props[f]) else v
    return rec, lost


def explain(e, rec):
    """A jsonschema error -> (field, reason)."""
    path = [str(p) for p in e.absolute_path]
    if e.validator in ("required", "dependentRequired"):
        names = re.findall(r"'([^']+)'", e.message)
        return names[0], "missing" if e.validator == "required" else f"missing (required with {names[1]})"
    field = ".".join(path) or "(record)"
    if e.validator == "enum":
        return field, f"not in enum: {e.instance}"
    if e.schema is False or e.validator == "False schema":
        return field, f"forbidden on type {rec.get('type')}"
    if e.validator == "type":
        return field, f"not a {e.validator_value}"
    if e.validator == "additionalProperties":
        return field, "unknown key: " + ", ".join(sorted(set(e.instance) - set(e.schema.get("properties", {}))))
    if e.validator == "pattern":
        return field, "pattern"
    return field, f"{e.validator}: {e.message[:80]}"


def generic(reason):
    return re.sub(r"^(not in enum|unknown key): .*", r"\1", reason)


def main():
    schema = json.loads((ROOT / "schema" / "form.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    val = Draft202012Validator(schema)
    fails, n, bad, skipped = [], 0, set(), collections.Counter()
    by_type_total = collections.Counter()
    for path in GOLD:
        pid = path.name[: -len(".facts.csv")]
        for row in csv.DictReader(path.open(newline="", encoding="utf-8")):
            if row["type"] not in X.FORM_TYPES:
                skipped[row["type"]] += 1
                continue
            n += 1
            by_type_total[row["type"]] += 1
            rec, lost = cast(row, props)
            errs = [(f, r) for f, r in lost] + [("quote", "absent")]
            errs += [x for x in (explain(e, rec) for e in val.iter_errors(rec)) if x != ("quote", "missing")]   # absent quote reported once
            for f, r in errs:
                fails.append(dict(pid=pid, fact_id=row["fact_id"], type=row["type"], field=f, reason=r))
            bad.add((pid, row["fact_id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "roundtrip.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pid", "fact_id", "field", "reason"], extrasaction="ignore")
        w.writeheader()
        w.writerows(fails)
    beyond = [x for x in fails if x["field"] != "quote"]
    bad_beyond = {(x["pid"], x["fact_id"]) for x in beyond}
    rec_type = {(x["pid"], x["fact_id"]): x["type"] for x in fails}
    L = [f"P132 round trip: {len(GOLD)} gold pilot/<paper_id>.facts.csv against schema/form.json (ontology sha256 {X.ontology_hash()})",
         f"not cast (not form types): {sum(skipped.values())} rows ({', '.join(f'{k} {v}' for k, v in sorted(skipped.items()))})",
         f"records total {n}, pass {n - len(bad)}, fail {len(bad)}",
         f"without the quote failure (every record): pass {n - len(bad_beyond)}, fail {len(bad_beyond)}", "",
         "failures by field (records failing on the field, failure rows):"]
    recs_by_field = collections.defaultdict(set)
    for x in fails:
        recs_by_field[x["field"]].add((x["pid"], x["fact_id"]))
    rows_by_field = collections.Counter(x["field"] for x in fails)
    L += [f"  {k:24s} {len(recs_by_field[k]):5d} {rows_by_field[k]:6d}" for k, _ in rows_by_field.most_common()]
    L += ["", "failures by type, without the quote failure (failing records / records of the type):"]
    ft = collections.Counter(rec_type[k] for k in bad_beyond)
    L += [f"  {t:12s} {ft[t]:5d} / {by_type_total[t]}" for t in X.FORM_TYPES]
    L += ["", "top reasons (failure rows, field: reason):"]
    L += [f"  {c:6d}  {k}" for k, c in collections.Counter(f"{x['field']}: {generic(x['reason'])}" for x in fails).most_common(15)]
    L += ["", "top values behind 'not in enum' / 'unknown key' (failure rows):"]
    L += [f"  {c:6d}  {k}" for k, c in collections.Counter(f"{x['field']}: {x['reason']}" for x in fails if generic(x["reason"]) != x["reason"]).most_common(20)]
    (OUT / "roundtrip_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
