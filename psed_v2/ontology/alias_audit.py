#!/usr/bin/env python3
"""P131b: alias audit. For every setting, observation and derived record of the 12 papers' facts.csv with a quantity id (not other), the printed
form it was keyed from: its label_as_printed, else the longest alias of the id that occurs in the text of its evidence elements
(elements.texts(), read at run time, never written out), else unlocated. Status: matched (the printed form is an alias, the label or the name
of the entry, up to case, subscript underscores and spaces: fold()), spread (a record with a stat= qualifier: its printed label names the
statistic, "standard deviation of PD50%", not the quantity; listed, never an alias source), ambiguous (P131b-12b: the form is a key of
vocabularies.ambiguous_aliases), pending (the form is the label or an alias of a pending.csv row still pending), missing (none of these;
the target is 0), unlocated (no printed form found). Writes verify/d14/alias_audit.csv (entry id, printed form, paper, element, status;
one row per distinct entry, printed form, paper); counts printed.

    python3 psed_v2/ontology/alias_audit.py            # audit only
    python3 psed_v2/ontology/alias_audit.py --apply    # also add every missing printed form verbatim as an alias of its entry in ontology.yaml,
                                                       # with its evidence (paper, element) appended to the entry's evidence; then audit again

Sec. 11 rule 6 (12b): a missing printed form that is already an alias, label or name of another entry, or missing for two entries in the
same run, is a word with two definitions: it goes to vocabularies.ambiguous_aliases with every entry it would match (move_ambiguous(),
which also drops it from the entries' aliases, make_report check 4). One that an other[...] record carries as its label is not added
(the P78 slot rule, facts.rekey_structure_dimensions, would re-key that record): it is listed as stopped. Unlocated rows are listed, not fixed.
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


def pending_forms():
    """The labels and aliases of the pending.csv rows still pending, folded."""
    rows = list(csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8")))
    return {fold(a) for r in rows if r["status"] == "pending" for a in [r.get("label", "")] + (r.get("aliases") or "").split("|") if a}


def audit(onto):
    import elements
    entries = {e["id"]: e for e in onto["entries"]}
    ambiguous = {fold(a) for a in onto["vocabularies"].get("ambiguous_aliases") or {}}
    pend = pending_forms()
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
            status = ("unlocated" if not printed else "matched" if fold(printed) in names(entries[q])
                      else "spread" if any(x.startswith("stat=") for x in r["qualifiers"].split(";"))
                      else "ambiguous" if fold(printed) in ambiguous else "pending" if fold(printed) in pend else "missing")
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


def move_ambiguous(text, form, cands):
    """Sec. 11 rule 6: form becomes a key of vocabularies.ambiguous_aliases listing cands (merged with an existing key of the same fold), and
    leaves the aliases of every entry (make_report check 4: an ambiguous word in no entry's aliases)."""
    onto = yaml.safe_load(text)
    for e in onto["entries"]:
        if any(fold(a) == fold(form) for a in e.get("aliases") or []):
            text = set_field(text, e["id"], "aliases", [a for a in e["aliases"] if fold(a) != fold(form)])
    amb = onto["vocabularies"].get("ambiguous_aliases") or {}
    key = next((k for k in amb if fold(k) == fold(form)), None)
    head, rest = text.split("\n  ambiguous_aliases:\n", 1)
    lines = rest.split("\n")
    n = next(i for i, ln in enumerate(lines) if not ln.startswith("    "))
    block = lines[:n]
    if key is not None:
        merged = list(dict.fromkeys([str(x) for x in amb[key]] + sorted(cands)))
        i = next(i for i, ln in enumerate(block) if yaml.safe_load(ln.strip()) and key in yaml.safe_load(ln.strip()))
        block[i] = "    " + yaml.safe_dump({key: merged}, default_flow_style=None, allow_unicode=True, width=100000).strip()
    else:
        block.append("    " + yaml.safe_dump({form: sorted(cands)}, default_flow_style=None, allow_unicode=True, width=100000).strip() + "   # P131b-12b: Sec. 11 rule 6")
    return head + "\n  ambiguous_aliases:\n" + "\n".join(block + lines[n:])


def apply(rows, onto):
    entries = {e["id"]: e for e in onto["entries"]}
    owner = collections.defaultdict(set)
    for e in onto["entries"]:
        for a in names(e):
            owner[a].add(e["id"])
    free = {r["label_as_printed"] for p in glob.glob(str(V2 / "pilot" / "*.facts.csv")) for r in csv.DictReader(open(p, newline="", encoding="utf-8")) if r["quantity"] == "other"}
    add, stopped, amb = collections.defaultdict(dict), [], collections.defaultdict(set)
    batch = collections.defaultdict(set)
    for r in rows:
        if r["status"] == "missing":
            batch[fold(r["printed"])].add(r["entry"])
    for r in rows:
        if r["status"] != "missing":
            continue
        others = (owner.get(fold(r["printed"]), set()) | batch[fold(r["printed"])]) - {r["entry"]}
        if others:
            amb[r["printed"]] |= others | {r["entry"]}
            continue
        if r["printed"] in free:
            stopped.append(dict(r, why="the label of an other[...] record"))
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
    for form, cands in sorted(amb.items()):
        text = move_ambiguous(text, form, cands)
        print(f"ambiguous {form!r}: {', '.join(sorted(cands))}")
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
    print(f"{label}: {len(rows)} distinct (entry, printed form, paper): " + ", ".join(f"{k} {c[k]}" for k in ("matched", "missing", "unlocated", "spread", "ambiguous", "pending")))
    return c


def main():
    onto = yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))
    rows = distinct(audit(onto))
    counts(rows, "before")
    if "--apply" in sys.argv:
        n, ne, stopped = apply(rows, onto)
        print(f"added {n} aliases to {ne} entries")
        for s in stopped:
            print(f"STOPPED {s['entry']} {s['printed']!r} ({s['paper']} {s['element']}): {s['why']}")
        onto = yaml.safe_load((HERE / "ontology.yaml").read_text(encoding="utf-8"))
        rows = distinct(audit(onto))
        counts(rows, "after")
    write(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
