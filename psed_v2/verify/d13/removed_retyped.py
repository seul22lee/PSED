#!/usr/bin/env python3
"""verify/d13: removed.csv (claims P131 removed or marked duplicate) and retyped.csv (claims P131 re-typed or given a triple), from the
diff of each <pid>.facts.csv between 35c41a9 (pilot-v6) and HEAD; the duplicate targets and the removal reason from the RETYPE tables
in the per-paper facts.py at HEAD (read as text, no script run).

    python3 psed_v2/verify/d13/removed_retyped.py
"""
import csv, io, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEFORE, AFTER = "35c41a9", "HEAD"


def git(ref, path):
    return subprocess.run(["git", "show", f"{ref}:psed_v2/{path}"], capture_output=True, text=True, check=True, cwd=HERE).stdout


def full(r):
    return bool(r["cause"] and r["relation"] and r["effect"])


removed, retyped = [], []
pids = sorted(p.name[:-10] for p in (HERE.parent.parent / "pilot").glob("10.*.facts.csv"))
for pid in pids:
    b = {r["fact_id"]: r for r in csv.DictReader(io.StringIO(git(BEFORE, f"pilot/{pid}.facts.csv")))}
    a = {r["fact_id"]: r for r in csv.DictReader(io.StringIO(git(AFTER, f"pilot/{pid}.facts.csv")))}
    src = git(AFTER, f"pilot/{pid}.facts.py")
    key = src.split('K, PID = "', 1)[1].split('"', 1)[0]
    tab = {}
    if "RETYPE = {" in src:
        bg = eval(src.split("\nBG = ", 1)[1].split("\n", 1)[0])
        tab = eval(src.split("RETYPE = ", 1)[1].split("\n}\n", 1)[0] + "\n}", {"BG": bg})
    for i, r in b.items():
        if r["type"] != "claim" or full(r):
            continue
        spec = tab.get(i.split(":", 1)[1])
        if i not in a:
            act = spec[0] if spec else "?"
            reason = f"duplicate_of:{key}:{spec[1]}" if act == "duplicate" else ("background|motivation|prior_art|scope" if spec else "?")   # P131 used one combined category for removals
            removed.append(dict(fact_id=i, paper=key, action=act, reason=reason, statement=r["statement"]))
        else:
            n = a[i]
            retyped.append(dict(fact_id=i, paper=key, old_type=r["type"], new_type=n["type"], cause=n["cause"] if n["type"] == "claim" else "",
                                relation=n["relation"] if n["type"] == "claim" else "", effect=n["effect"] if n["type"] == "claim" else ""))
for name, rows in (("removed.csv", removed), ("retyped.csv", retyped)):
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
print("removed.csv", len(removed), dict(collections.Counter(r["action"] for r in removed)), dict(collections.Counter(r["reason"] for r in removed if r["action"] == "removed")))
print("retyped.csv", len(retyped), dict(collections.Counter(r["new_type"] for r in retyped)))
