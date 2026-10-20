#!/usr/bin/env python3
"""verify/d13: the P130/P131 before/after table per paper, from the facts tables at tag pilot-v6 (git) against the working tree.

claims, claims with a full triple, nodes (distinct triples of the paper's claims; a node shared with other papers counts in each),
removed (background and the like) and duplicate (an existing caveat states it), re-typed by target type, the record type
distribution before and after. Ids only, no paper text.

    python3 psed_v2/verify/d13/counts.py [--before REF]      # writes verify/d13/counts.md and prints it
"""
import collections, csv, io, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent.parent / "pilot"
REF = sys.argv[sys.argv.index("--before") + 1] if "--before" in sys.argv else "pilot-v6"
sys.path.insert(0, str(PILOT))


def rows_at(pid, ref):
    text = subprocess.run(["git", "show", f"{ref}:psed_v2/pilot/{pid}.facts.csv"], capture_output=True, text=True, check=True, cwd=PILOT).stdout
    return list(csv.DictReader(io.StringIO(text)))


def full(r):
    return bool(r["cause"] and r["relation"] and r["effect"])


def main():
    pids = sorted(p.name[:-10] for p in PILOT.glob("10.*.facts.csv"))
    out, tot = [], collections.Counter()
    head = ["paper", "claims before", "full triple before", "nodes before", "claims after", "nodes after", "removed", "duplicate",
            "→ claim (triple filled)", "→ model", "→ caveat", "→ setting", "→ observation", "→ cited"]
    out.append("| " + " | ".join(head) + " |"); out.append("|" + "---|" * len(head))
    types_b, types_a = {}, {}
    for pid in pids:
        b = {r["fact_id"]: r for r in rows_at(pid, REF)}
        a = {r["fact_id"]: r for r in csv.DictReader((PILOT / f"{pid}.facts.csv").open(encoding="utf-8"))}
        key = next(iter(a)).split(":")[0]
        cb = [r for r in b.values() if r["type"] == "claim"]
        ca = [r for r in a.values() if r["type"] == "claim"]
        nb = {(r["cause"], r["relation"], r["effect"]) for r in cb if full(r)}
        na = {(r["cause"], r["relation"], r["effect"]) for r in ca if full(r)}
        loose = [r for r in cb if not full(r)]
        gone = [r for r in loose if r["fact_id"] not in a]
        dup = [r for r in gone if r["fact_id"] in DUP]
        moved = collections.Counter(a[r["fact_id"]]["type"] for r in loose if r["fact_id"] in a)
        row = dict(paper=key, cb=len(cb), fb=len(cb) - len(loose), nb=len(nb), ca=len(ca), na=len(na), rem=len(gone) - len(dup), dup=len(dup),
                   claim=moved["claim"], model=moved["model"], caveat=moved["caveat"], setting=moved["setting"], observation=moved["observation"], cited=moved["cited"])
        tot.update({k: v for k, v in row.items() if k != "paper"})
        out.append("| " + " | ".join(str(v) for v in row.values()) + " |")
        types_b[key] = collections.Counter(r["type"] for r in b.values() if "#" in r["fact_id"])
        types_a[key] = collections.Counter(r["type"] for r in a.values() if "#" in r["fact_id"])
    out.append("| total | " + " | ".join(str(tot[k]) for k in ("cb", "fb", "nb", "ca", "na", "rem", "dup", "claim", "model", "caveat", "setting", "observation", "cited")) + " |")
    out.append("")
    out.append("nodes before / after per paper count the paper's distinct triples; across the 12 papers (and the user's 2 claims) see check.txt (claim nodes, P130).")
    out.append("")
    ts = ["claim", "observation", "setting", "derived", "model", "cited", "definition", "caveat", "comparison", "identity"]
    out.append("Record types per paper, before → after (fact rows; tree rows not counted):")
    out.append("")
    out.append("| paper | " + " | ".join(ts) + " |"); out.append("|" + "---|" * (len(ts) + 1))
    for k in types_b:
        out.append(f"| {k} | " + " | ".join(f"{types_b[k][t]} → {types_a[k][t]}" if types_b[k][t] != types_a[k][t] else str(types_a[k][t]) for t in ts) + " |")
    text = "\n".join(out) + "\n"
    (HERE / "counts.md").write_text(text, encoding="utf-8")
    print(text)


DUP = set()
if __name__ == "__main__":
    for p in PILOT.glob("10.*.facts.py"):                                       # the duplicate targets, from each RETYPE table's text (no paper script is run)
        src = p.read_text(encoding="utf-8")
        if "RETYPE = {" in src:
            key = src.split('K, PID = "', 1)[1].split('"', 1)[0]
            tab = eval(src.split("RETYPE = ", 1)[1].split("\n}\n", 1)[0] + "\n}", {"BG": ""})
            DUP |= {f"{key}:{s}" for s, v in tab.items() if v[0] == "duplicate"}
    main()
