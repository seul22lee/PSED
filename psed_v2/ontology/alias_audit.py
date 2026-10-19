#!/usr/bin/env python3
"""P131b: alias audit. For every setting, observation and derived record of the 12 papers' facts.csv with a quantity id (not other), the printed
form it was keyed from: its label_as_printed, else the longest alias of the id that occurs in the text of its evidence elements
(elements.texts(), read at run time, never written out), else unlocated. Status: matched (the printed form is an alias, the label or the name
of the entry, up to case, subscript underscores and spaces: fold()), missing (it is none of them), unlocated (no printed form found), spread (a record with a stat= qualifier: its printed label
names the statistic, "standard deviation of PD50%", not the quantity; listed, never an alias source). Writes verify/d14/alias_audit.csv (entry id, printed form,
paper, element, status; one row per distinct entry, printed form, paper); counts printed.

    python3 psed_v2/ontology/alias_audit.py            # audit only
    python3 psed_v2/ontology/alias_audit.py --apply    # also add every missing printed form verbatim as an alias of its entry in ontology.yaml,
                                                       # with its evidence (paper, element) appended to the entry's evidence; then audit again

A missing printed form that is already an alias, label or name of another entry, an ambiguous alias, or missing for two entries in the same
run, is not added (it would put one word in two entries, make_report check 4); nor is one that an other[...] record carries as its label
(the P78 slot rule, facts.rekey_structure_dimensions, would re-key that record to the entry): it is listed as stopped. Unlocated rows are listed, not fixed.
"""
import collections, csv, glob, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "pilot"))
OUT = V2 / "verify" / "d14" / "alias_audit.csv"
TYPES = ("setting", "observation", "derived")


def fold(a):
    """A printed form up to case, subscript underscores and spaces (make_report check 4 compares aliases lowercased; 'S_I/N (GPC_I)' and
    'SI/N (GPCI)' are one printed form, the text layer drops the subscript mark)."""
    return re.sub(r"[_\s]", "", str(a)).lower()


def names(e):
    """The entry's aliases, label and name, folded."""
    return {fold(a) for a in e.get("aliases") or []} | {fold(e.get("label") or ""), fold(e.get("name") or "")} - {""}


def audit(entries):
    import elements
    rows = []
    for p in sorted(glob.glob(str(V2 / "pilot" / "10.*.facts.csv"))):
        pid = Path(p).name[:-len(".facts.csv")]
        texts = None
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            q = r["quantity"]
            if r["type"] not in TYPES or not q or q == "other" or q not in entries:
                continue
            els = [x for x in r["evidence"].split(";") if x]
            printed, el = r["label_as_printed"].strip(), els[0] if els else ""
            if not printed:
                texts = texts if texts is not None else elements.texts(pid)
                found = [(len(a), a, x) for a in entries[q].get("aliases") or [] for x in els if a and a in texts.get(x, "")]
                if found:
                    _, printed, el = max(found)
            status = "unlocated" if not printed else "matched" if fold(printed) in names(entries[q]) else "spread" if any(x.startswith("stat=") for x in r["qualifiers"].split(";")) else "missing"
            rows.append(dict(entry=q, printed=printed, paper=r["fact_id"].split(":")[0], element=el, status=status, fact_id=r["fact_id"]))
    return rows


def distinct(rows):
    seen = {}
    for r in rows:
        seen.setdefault((r["entry"], r["printed"], r["paper"], r["status"]), r)
    return list(seen.values())


def set_field(text, eid, field, value):
    """Replace (or add before evidence:) the one-line flow field of entry eid in the entries: section."""
    head, rest = text.split("\nentries:\n", 1)
    body, tail = rest.split("\nfamilies:", 1)
    blocks = re.split(r"(?m)^(?=  - id: )", body)
    i = next(k for k, b in enumerate(blocks) if re.match(rf"  - id: {re.escape(eid)}\n", b))
    line = f"    {field}: " + yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=100000).strip()
    b = blocks[i]
    if re.search(rf"(?m)^    {field}:.*$", b):
        b = re.sub(rf"(?m)^    {field}:.*$", lambda m: line, b, count=1)
    else:
        b = re.sub(r"(?m)^    evidence:", lambda m: line + "\n    evidence:", b, count=1) if "\n    evidence:" in b else b.rstrip("\n") + "\n" + line + "\n" + ("\n" if b.endswith("\n\n") else "")
    blocks[i] = b
    return head + "\nentries:\n" + "".join(blocks) + "\nfamilies:" + tail


def apply(rows, onto):
    entries = {e["id"]: e for e in onto["entries"]}
    owner = collections.defaultdict(set)
    for e in onto["entries"]:
        for a in names(e):
            owner[a].add(e["id"])
    ambiguous = {fold(a) for a in onto["vocabularies"].get("ambiguous_aliases", {})}
    free = {r["label_as_printed"] for p in glob.glob(str(V2 / "pilot" / "*.facts.csv")) for r in csv.DictReader(open(p, newline="", encoding="utf-8")) if r["quantity"] == "other"}
    add, stopped = collections.defaultdict(dict), []
    batch = collections.defaultdict(set)
    for r in rows:
        if r["status"] == "missing":
            batch[fold(r["printed"])].add(r["entry"])
    for r in rows:
        if r["status"] != "missing":
            continue
        others = (owner.get(fold(r["printed"]), set()) | batch[fold(r["printed"])]) - {r["entry"]}
        if others or fold(r["printed"]) in ambiguous or r["printed"] in free:
            stopped.append(dict(r, why=f"already a name of {', '.join(sorted(others))}" if others else "an ambiguous alias" if fold(r["printed"]) in ambiguous
                                else "the label of an other[...] record"))
            continue
        add[r["entry"]].setdefault(r["printed"], []).append(f"{r['paper']} {r['element']}")
    text = (HERE / "ontology.yaml").read_text(encoding="utf-8")
    n = 0
    for eid, forms in sorted(add.items()):
        e = entries[eid]
        al = list(e.get("aliases") or [])
        for f in forms:
            if fold(f) not in {fold(a) for a in al}:                           # one spelling per printed form
                al.append(f)
        ev = list(e.get("evidence") or []) + [f"alias {f!r}: {'; '.join(sorted(set(w)))} (P131b alias audit)" for f, w in forms.items()]
        text = set_field(text, eid, "aliases", al)
        text = set_field(text, eid, "evidence", ev)
        n += len(forms)
    (HERE / "ontology.yaml").write_text(text, encoding="utf-8")
    yaml.safe_load(text)
    return n, len(add), stopped


def write(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entry", "printed", "paper", "element", "status"], extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(sorted(rows, key=lambda r: (r["status"], r["entry"], r["printed"], r["paper"])))


def counts(rows, label):
    c = collections.Counter(r["status"] for r in rows)
    print(f"{label}: {len(rows)} distinct (entry, printed form, paper): matched {c['matched']}, missing {c['missing']}, unlocated {c['unlocated']}, spread {c['spread']}")
    return c


def main():
    onto = yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))
    entries = {e["id"]: e for e in onto["entries"]}
    rows = distinct(audit(entries))
    counts(rows, "before")
    if "--apply" in sys.argv:
        n, ne, stopped = apply(rows, onto)
        print(f"added {n} aliases to {ne} entries")
        for s in stopped:
            print(f"STOPPED {s['entry']} {s['printed']!r} ({s['paper']} {s['element']}): {s['why']}")
        onto = yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))
        rows = distinct(audit({e["id"]: e for e in onto["entries"]}))
        counts(rows, "after")
    write(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
