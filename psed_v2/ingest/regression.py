#!/usr/bin/env python3
"""Regression of the final output against the answer set ingest/answers/body_flags.json.
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/regression.py            check, exit 1 on a failure
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/regression.py --update   also rewrite the baseline

Three checks on ingest/final/<paper_id>/structure.json:
  1. every judged real error is still detected: its flag key is present, or a repair of body_repairs covers it
     (same page, the number in the repaired token, sentence or restored line), or another flagged key of the same
     paper, page and error type still names the error (a token of the same error), or the error is the margin-number
     kind that line_numbers.py removes;
  2. no judged not-error is newly flagged as a number or letter flag: a not-error key present now but absent from the
     baseline answers/flag_keys_baseline.json (the keys of the last accepted run) is a failure;
  3. every repair is intact in document.md (the replaced token or the restored line is in the text, no doubled sign)
     and no repair was undone.
The baseline is a list of flag keys (ids only, no paper text). "Not checkable" flags are not part of the keys.
A flag key is paper_id|page|kind[:6]|number, as in the answer set.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL = HERE / "final"
ANSWERS = HERE / "answers" / "body_flags.json"
BASELINE = HERE / "answers" / "flag_keys_baseline.json"


def flag_key(pid, f):
    return f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}"


def _plain(s):
    return re.sub(r"<[^>]+>|[_^{}$\\]", "", s or "")


def main(argv):
    update = argv[:1] == ["--update"]
    ans = json.load(open(ANSWERS))["items"]
    by_key = {a["flag_key"]: a for a in ans}
    now, repairs, undone, texts = Counter(), {}, {}, {}
    for d in sorted(p for p in FINAL.iterdir() if (p / "structure.json").exists()):
        pid = d.name
        st = json.load(open(d / "structure.json"))
        texts[pid] = (d / "document.md").read_text()
        for f in st["body_flags"]:
            if f["kind"] != "not checkable":
                now[flag_key(pid, f)] += 1
        repairs[pid] = st.get("body_repairs", [])
        undone[pid] = st.get("body_repairs_undone", [])
    baseline = set(json.load(open(BASELINE))) if BASELINE.exists() else None
    failures = []

    # 1. known real errors
    def repaired(pid, page, num):
        for r in repairs.get(pid, []):
            if r["page"] != page:
                continue
            if num == "None":
                if r["kind"].startswith("dropped line"):
                    return True
            else:
                n = num.lstrip("-")
                if any(num in x or n in x for x in (_plain(r["from"]), _plain(r["to"]), r.get("sentence", ""))):
                    return True
        return False
    flagged_now = {k for k in now}
    real = [a for a in ans if a["verdict"] == "real error"]
    kept_flag = kept_rep = kept_other = 0
    for a in real:
        k = a["flag_key"]
        pid, page, _, num = k.split("|")
        page = int(page)
        if k in flagged_now:
            kept_flag += 1
        elif repaired(pid, page, num) or "margin" in a.get("error_type", ""):
            kept_rep += 1
        elif any(b["flag_key"] in flagged_now and b["flag_key"].split("|")[0] == pid and b["flag_key"].split("|")[1] == str(page)
                 and b.get("error_type") == a.get("error_type") for b in real):
            kept_other += 1                      # the same error still flagged by another of its tokens
        else:
            failures.append(("known real error lost", k, a.get("error_type", "")[:60]))
    print(f"real errors: {len(real)} keys; flagged {kept_flag}, repaired or removed by rule {kept_rep}, "
          f"still flagged by another token of the same error {kept_other}, lost {len(real) - kept_flag - kept_rep - kept_other}")

    # 2. known not-errors newly flagged
    notk = [a for a in ans if a["verdict"] != "real error"]
    still = [a["flag_key"] for a in notk if a["flag_key"] in flagged_now]
    if baseline is None:
        print(f"not-errors: {len(notk)} keys; {len(still)} flagged now; no baseline yet (run with --update to write it)")
    else:
        newly = [k for k in still if k not in baseline]
        print(f"not-errors: {len(notk)} keys; {len(still)} flagged now, {len(newly)} newly flagged against the baseline")
        for k in newly:
            failures.append(("known not-error newly flagged", k, by_key[k].get("measurement_cause", "")[:60]))
    unjudged = sorted(k for k in flagged_now if k not in by_key)
    print(f"flags now: {sum(now.values())} ({len(flagged_now)} keys), unjudged keys: {len(unjudged)}", unjudged if len(unjudged) <= 12 else "")

    # 3. repairs intact
    n_rep = sum(len(r) for r in repairs.values())
    n_und = sum(len(u) for u in undone.values())
    for pid, rs in repairs.items():
        for r in rs:
            if r["kind"].startswith("number replaced"):
                if r["to"] not in texts[pid]:
                    failures.append(("repair not in text", pid, r["to"]))
                if "--" in r["to"]:
                    failures.append(("doubled sign", pid, r["to"]))
            elif r["to"] not in texts[pid]:
                failures.append(("restored line not in text", pid, r["to"][:60]))
    for pid, us in undone.items():
        for u in us:
            failures.append(("repair undone", pid, u.get("to", "")[:60]))
    print(f"repairs: {n_rep} applied, {n_und} undone")

    if baseline is not None:
        gone = sorted(k for k in baseline if k not in flagged_now)
        added = sorted(k for k in flagged_now if k not in baseline)
        print(f"against the baseline: {len(added)} keys added, {len(gone)} gone")
    if update:
        json.dump(sorted(flagged_now), open(BASELINE, "w"), indent=1)
        print(f"baseline written: {BASELINE.name} ({len(flagged_now)} keys)")
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  ", f)
        return 1
    print("OK: every known real error kept, no known not-error newly flagged, repairs intact")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
