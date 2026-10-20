#!/usr/bin/env python3
"""P131b: every pending.csv row with status accepted becomes an entry in ontology.yaml (under entries:, after the last entry), by code.

    python3 psed_v2/ontology/merge_pending.py            # merge, print what was merged, skipped or stopped
    python3 psed_v2/ontology/merge_pending.py --dry-run  # print only

The entry is export.pending_entry(row), the dict the vocabulary already carried for the row, without the pending flag and empty fields; a
method keeps its class. Added from the row: citation, cq, base {}, deviation {type: added, reason: the P98 rule from pending_decisions.csv},
evidence (the evidence column: paper key and element ids, pending_decide.naming()) and, for a row made from a free label
(pending_decide.candidate()), from_other: the printed labels whose other[...] records facts.write() re-keys to the entry. The merged rows
leave pending.csv and pending_decisions.csv (make_report check 14: a pending row clashes with no entry); the rows that stay pending keep
their evidence column. An id already in ontology.yaml with the same definition and dimension is skipped (not duplicated); aliases that differ only by case keep the
first spelling (make_report check 4 compares aliases lowercased). The same id with another definition or dimension stops the script before anything is written, and is reported, not resolved.
Also (P131b): the qualifier value kind=estimated gets its evidence, the records that carry it. 12b: an entry made from a free label takes
its printed label as name, definition_status: template and category_status: provisional (the user decides both); an alias that two entries
carry up to case after the merge is a word with two definitions (Sec. 11 rule 6): alias_audit.move_ambiguous() moves it to
vocabularies.ambiguous_aliases with both entries.
"""
import csv, glob, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import export          # noqa: E402
import pending_decide  # noqa: E402

ORDER = ["id", "type", "label", "name", "origin", "role", "category", "category_status", "definition", "definition_status", "dimension", "unit", "kind", "formula", "class", "model_type",
         "parameters", "aliases", "converts_to", "citation", "cq", "base", "deviation", "from_other", "evidence"]


def read(name):
    with (HERE / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, rows, fields):
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)


def entry(r, dec):
    e = export.pending_entry(r)
    e.pop("pending")
    if r["kind"] == "method":
        e["class"] = r.get("class") or r["id"]
    d = dec[r["id"]]
    e.update(citation=r["citation"], cq=r.get("cq", ""), base={},
             deviation=dict(type="added", reason=f"P98 rule {d['rule']}" + (f" ({d['section']})" if d["section"] else "") + f", papers {d['papers']}; merged from pending.csv (P131b)"),
             evidence=[x for x in r.get("evidence", "").split("; ") if x])
    if e.get("aliases"):                                                        # a case variant of an earlier alias is the same word (make_report check 4)
        e["aliases"] = list({a.lower(): a for a in reversed(e["aliases"])}.values())[::-1]
    if r["id"] in pending_decide.FREE:                                         # 12b: a free-label entry is named as printed; its definition is the
        e["from_other"] = [a for a in r["aliases"].split("|") if a]            # candidate() template and its category export's default, both for the user
        e.update(name=r["label"], definition_status="template", category_status="provisional")
    return {k: e[k] for k in ORDER if k in e and e[k] not in ("", [], None)}


def block(e):
    text = yaml.safe_dump([e], sort_keys=False, allow_unicode=True, width=100000, default_flow_style=None)
    return "".join("  " + ln + "\n" for ln in text.splitlines()) + "\n"


def estimated_evidence():
    out = []
    for p in sorted(glob.glob(str(V2 / "kb" / "pilot" / "*.facts.csv"))):
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            if "kind=estimated" in r["qualifiers"].split(";"):
                out.append(f"{r['fact_id']} ({r['evidence']})")
    return out


def main():
    dry = "--dry-run" in sys.argv
    rows, decs = read("pending.csv"), read("pending_decisions.csv")
    dec = {d["id"]: d for d in decs}
    pending_decide.FREE.update(r["id"] for r in rows if r["definition"].startswith(f"{r['label']}: the free label of "))
    text = (HERE / "ontology.yaml").read_text(encoding="utf-8")
    onto = yaml.safe_load(text)
    have = {e["id"]: e for e in onto["entries"]}
    # P142b: the measurement methods are entries now (the vocabularies block is gone)
    new, skipped, conflicts = [], [], []
    for r in rows:
        if r["status"] != "accepted":
            continue
        e = entry(r, dec)
        old = have.get(r["id"])
        if old is None:
            new.append(e)
        elif old.get("definition") == e.get("definition") and str(old.get("dimension", "")) == str(e.get("dimension", "")):
            skipped.append(r["id"])
        else:
            conflicts.append(f"{r['id']}: in ontology.yaml with definition {old.get('definition')!r} dimension {old.get('dimension', '')!r}; "
                             f"pending.csv has {e.get('definition')!r} dimension {e.get('dimension', '')!r}")
    print(f"accepted rows {sum(r['status'] == 'accepted' for r in rows)}: new {len(new)}, already present {len(skipped)}, conflicts {len(conflicts)}")
    if conflicts:
        print("STOPPED, nothing written:\n  " + "\n  ".join(conflicts))
        return 1
    for e in new:
        print(f"  + {e['id']} ({e['type']})")
    if dry:
        return 0
    if new:
        mark = "\nfamilies:"
        assert text.count(mark) == 1
        head, tail = text.split(mark)
        text = head.rstrip("\n") + "\n\n  # ---------------------------------------------------------------- P131b: merged from pending.csv (accepted by the P98 rules)\n" \
            + "".join(block(e) for e in new).rstrip("\n") + "\n" + mark + tail
    import alias_audit
    onto2 = yaml.safe_load(text)
    carriers = {}
    for e in onto2["entries"]:
        for a in e.get("aliases") or []:
            carriers.setdefault(a.lower(), {}).setdefault(a, set()).add(e["id"])
    for low, spell in sorted(carriers.items()):
        ids = set().union(*spell.values())
        if len(ids) > 1:
            for a in spell:
                text = alias_audit.move_ambiguous(text, a, ids)
                print(f"ambiguous {a!r}: {', '.join(sorted(ids))} (Sec. 11 rule 6)")
    ev = estimated_evidence()
    line = re.search(r"(?m)^  kind: +\{values: \[[^\]]*\bestimated\b[^\]]*\], log: \"[^\"]*\"(, evidence: \[[^\]]*\])?\}$", text)
    assert line, "qualifier kind=estimated not found"
    old_line = line.group(0)
    new_line = re.sub(r"(, evidence: \[[^\]]*\])?\}$", "", old_line) + ", evidence: " + yaml.safe_dump(ev, default_flow_style=True, allow_unicode=True, width=100000).strip() + "}"
    text = text.replace(old_line, new_line)
    print(f"kind=estimated evidence: {len(ev)} records")
    (HERE / "ontology.yaml").write_text(text, encoding="utf-8")
    merged = {e["id"] for e in new} | set(skipped)
    keep = [r for r in rows if r["id"] not in merged]
    write("pending.csv", keep, list(rows[0].keys()))
    write("pending_decisions.csv", [d for d in decs if d["id"] not in merged], list(decs[0].keys()))
    yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))           # still parses
    print(f"pending.csv: {len(rows)} -> {len(keep)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
