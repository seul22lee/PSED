#!/usr/bin/env python3
"""The process metrics of a Knowledge base answer (P69) and the reporter over a run file (P74): what the tools delivered against
what the answer used, from the stored records alone (no model call); ask.py stores them next to the number check.

    python3 psed_v2/pilot/run_metrics.py RUNS.jsonl [--arm kb] [--no-summary]   # per question and total; rewrites RUNS.summary.csv

Definitions (these reproduce the reference numbers on A10_v2.jsonl: 98 executed and 18 refused calls, re-delivery 30-56 % per
question, utilization 7-18 %):
- executed calls: error == ""; refused: the cap, a wall or a tool error; duplicate (identical): 'identical to call N' (P69).
- errors (P75): the refused calls that were tool errors (an unresolved name, a bad argument, nothing matches), not the cap or a wall;
  wall_hit: 'total' or 'errors' when a refusal of the question names that wall (ask.TOTAL_WALL, ask.ERROR_WALL), else 'none'.
  The columns of P74 keep their definitions: executed, refused and duplicates are unchanged by P75.
- ids: every match of [<paper>:<rest>] in an executed call's stored output, counted as occurrences in call order.
- re-delivered share: occurrences whose id already appeared in a previous call of the same question / all occurrences; duplicates
  within one call do not count; the seen set updates after each call.
- delivered ids: the distinct ids over the executed calls; cited ids: the keys of the record's cited dict; utilization = cited / delivered.
- tool output tokens: the sum of each executed call's tokens (the vendor's counts, shared by length within a turn; ask.py).
- homeless_records (P79): the value records of the knowledge base no values() output renders (homeless.count), a property of the
  knowledge base the run was made against, the same for every row.
"""
import csv, json, re, sys
from pathlib import Path

ID = re.compile(r"\[([a-z0-9]+:[^\]\s]+)\]")
DUPLICATE = "identical to call "


def normalized(name, args):
    """The key of a tool call for the duplicate rule (P69): the tool name and its arguments with keys sorted, strings lowercased and
    their whitespace collapsed, lists in their order, null arguments dropped."""
    def norm(v):
        if isinstance(v, str):
            return " ".join(v.lower().split())
        if isinstance(v, dict):
            return {str(k).lower(): norm(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0])) if x is not None}
        if isinstance(v, list):
            return [norm(x) for x in v]
        return v
    return json.dumps([name.lower(), norm(args if isinstance(args, dict) else {})], sort_keys=True, ensure_ascii=False)


def process(tool_calls, cited=()):
    """The process metrics of one question: calls, executed, refused, duplicates, tool output tokens, the delivered ids, the
    re-delivered share, the cited ids and the utilization (cited / delivered); P75: errors (tool errors), identical (= duplicates,
    the directive's name) and wall_hit (none, total or errors)."""
    seen, occurrences, redelivered, tokens = set(), 0, 0, 0
    executed = refused = duplicates = errors = 0
    wall = "none"
    for c in tool_calls:
        e = c.get("error") or ""
        if e.startswith(DUPLICATE):
            duplicates += 1; continue
        if e:
            refused += 1
            if e.startswith("wall:"):
                wall = e[5:] if wall == "none" else wall
            elif e != "cap":
                errors += 1
            continue
        executed += 1
        tokens += c.get("tokens") or 0
        ids = ID.findall(c.get("output") or "")
        occurrences += len(ids)
        redelivered += sum(1 for i in ids if i in seen)
        seen |= set(ids)
    cited = [i for i in dict.fromkeys(cited)]
    return dict(calls=len(tool_calls), executed=executed, refused=refused, duplicates=duplicates, errors=errors, identical=duplicates, wall_hit=wall, tool_output_tokens=tokens,
                delivered=len(seen), delivered_ids=sorted(seen), id_occurrences=occurrences,
                redelivered_share=round(redelivered / occurrences, 4) if occurrences else 0.0,
                cited=len(cited), cited_ids=cited, utilization=round(len(cited) / len(seen), 4) if seen else 0.0)


COLUMNS = ["calls", "executed", "refused", "duplicates", "errors", "identical", "wall_hit", "tool_output_tokens", "redelivered_share", "delivered", "cited", "utilization", "words", "cost", "homeless_records"]
NO_TOTAL = ("redelivered_share", "utilization", "wall_hit", "homeless_records")
_HOMELESS = {}


def homeless_records():
    """P79: the number of value records of the knowledge base no values() output renders (homeless.count), computed once per process:
    a property of the knowledge base the run was made against, the same for every row."""
    if "n" not in _HOMELESS:
        import homeless
        _HOMELESS["n"] = homeless.count()
    return _HOMELESS["n"]


def metrics_of(r):
    """The process metrics of a stored record, recomputed from its tool calls and cited ids (P74), with its words and cost."""
    p = process(r.get("tool_calls") or [], list((r.get("cited") or {}).keys()))
    p["words"] = r.get("words", 0); p["cost"] = r.get("cost"); p["homeless_records"] = homeless_records()
    return p


def report(path, arm="kb", summary=True):
    """Per question and total, printed; rewrites <run>.summary.csv with ask.SUMMARY's columns (the process columns included) for
    every record of the file; returns the rows of the chosen arm."""
    recs = [json.loads(line) for line in Path(path).open(encoding="utf-8")]
    if summary:
        import ask                                                              # here, not at the top: ask imports this module
        summ = Path(path).with_suffix(".summary.csv")
        with summ.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ask.SUMMARY); w.writeheader(); w.writerows(ask.summary_row(r) for r in recs)
    rows = []
    for r in recs:
        if arm and r.get("arm") != arm:
            continue
        p = metrics_of(r)
        rows.append(dict(question=r["question"], arm=r["arm"], model=r["model"], **{k: p[k] for k in COLUMNS}))
    tot = {k: sum((x[k] or 0) for x in rows) for k in COLUMNS if k not in NO_TOTAL}
    rs = [x["redelivered_share"] for x in rows]; us = [x["utilization"] for x in rows]
    walls = sum(1 for x in rows if x["wall_hit"] != "none")
    for n, x in enumerate(rows, 1):
        print(f"{n:3d} calls {x['calls']:3d} (executed {x['executed']}, refused {x['refused']}, duplicates {x['duplicates']}; errors {x['errors']}, identical {x['identical']}, wall {x['wall_hit']}) · tool output {x['tool_output_tokens']:,} tokens · "
              f"re-delivered {100 * x['redelivered_share']:.0f} % · delivered {x['delivered']} ids, cited {x['cited']}, utilization {100 * x['utilization']:.0f} % · {x['words']} words · "
              f"{'cost not set' if x['cost'] is None else '$%.4f' % x['cost']}")
    if rows:
        print(f"knowledge base: {rows[0]['homeless_records']} homeless records (P79)")
        print(f"total {len(rows)} questions: calls {tot['calls']} (executed {tot['executed']}, refused {tot['refused']}, duplicates {tot['duplicates']}; errors {tot['errors']}, identical {tot['identical']}, walls hit in {walls} questions) · tool output {tot['tool_output_tokens']:,} tokens · "
              f"re-delivered {100 * min(rs):.0f}–{100 * max(rs):.0f} % · delivered {tot['delivered']} ids, cited {tot['cited']} · utilization {100 * min(us):.0f}–{100 * max(us):.0f} % · "
              f"{tot['words']} words · ${tot['cost']:.4f}")
    return rows


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--") and (sys.argv[sys.argv.index(a) - 1] != "--arm")]
    arm = sys.argv[sys.argv.index("--arm") + 1] if "--arm" in sys.argv else "kb"
    if not args:
        print(__doc__); sys.exit(0)
    report(args[0], arm, summary="--no-summary" not in sys.argv)
