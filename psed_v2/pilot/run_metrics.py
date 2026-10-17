#!/usr/bin/env python3
"""The process metrics of a Knowledge base answer (P69): what the tools delivered against what the answer used, from the stored
record alone (no model call); ask.py stores them next to the number check.

Definitions:
- executed calls: error == ""; refused: the cap or a validation error; duplicate: 'identical to call N' (P69).
- ids: every match of [<paper>:<rest>] in an executed call's stored output, counted as occurrences in call order.
- re-delivered share: occurrences whose id already appeared in a previous call of the same question / all occurrences; duplicates
  within one call do not count; the seen set updates after each call.
- delivered ids: the distinct ids over the executed calls; cited ids: the keys of the record's cited dict; utilization = cited / delivered.
- tool output tokens: the sum of each executed call's tokens (the vendor's counts, shared by length within a turn; ask.py).
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
    re-delivered share, the cited ids and the utilization (cited / delivered)."""
    seen, occurrences, redelivered, tokens = set(), 0, 0, 0
    executed = refused = duplicates = 0
    for c in tool_calls:
        e = c.get("error") or ""
        if e.startswith(DUPLICATE):
            duplicates += 1; continue
        if e:
            refused += 1; continue
        executed += 1
        tokens += c.get("tokens") or 0
        ids = ID.findall(c.get("output") or "")
        occurrences += len(ids)
        redelivered += sum(1 for i in ids if i in seen)
        seen |= set(ids)
    cited = [i for i in dict.fromkeys(cited)]
    return dict(calls=len(tool_calls), executed=executed, refused=refused, duplicates=duplicates, tool_output_tokens=tokens,
                delivered=len(seen), delivered_ids=sorted(seen), id_occurrences=occurrences,
                redelivered_share=round(redelivered / occurrences, 4) if occurrences else 0.0,
                cited=len(cited), cited_ids=cited, utilization=round(len(cited) / len(seen), 4) if seen else 0.0)
