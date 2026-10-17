#!/usr/bin/env python3
"""The whole knowledge base serialized once, compactly, for the dump arm of ask.py (P71): the L0 map, then per paper its tree in
order (every activity with its own settings, every entity and cited work with its own settings and results), its comparison sets
(kind, what they vary, members, purpose), its claims (stance, statement, cause, relation, effect, scope, the results they rest on)
and its caveats once by id; one legend for the kind marks and the basis phrases at the end. Every record starts with or carries
its id in square brackets, as the tools print them (the renderer of tools.py: P68), so the number check and the kind check read it
the same way. Definitions, notes and process steps are left out (search reaches them; the dump holds the evidence).

    python3 psed_v2/pilot/dump.py [--out FILE]      # prints the token size (chars/4) and the line count; --out writes the text
"""
import collections, re, sys
from pathlib import Path

ID = re.compile(r"\[([^\[\]\s]+)\]")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import concept as CN  # noqa: E402
import lists as L  # noqa: E402
import query as Q  # noqa: E402
import tools as TL  # noqa: E402


def serialize():
    """The serialization as one text; returns (text, counts)."""
    marks, bases, counts = set(), set(), collections.Counter()
    out = [CN.l0_map(), ""]

    def cell(rec, lifted=()):
        """A value as the values tool prints it (text, kind mark, ± with its basis id, fact id) and its caveat ids, except those lifted
        to the node."""
        c = TL._cell(rec, marks)
        u = rec.get("uncertainty")
        if u and not isinstance(u, str) and u.get("basis") in L.BASES:
            bases.add(u["basis"])
        own = [x for x in rec.get("caveats") or [] if x["id"] not in lifted]
        return c + TL.cmark(dict(caveats=own))

    for k, T in Q.TREES.items():
        out.append(f"== {k} · {TL.short_name(k)} ==")
        cav_ids = set()

        def walk(i, depth):
            n = T.byid[i]
            if n["type"] in ("activity", "entity", "cited") and "#" not in i:            # a node, not a cited value fact
                ent = T.ent_of(i)
                head = f"{n['type']}{' ' + n['kind'] if n['type'] == 'activity' and n.get('kind') else ''} [{i}]"
                if n["type"] != "activity":
                    head += f" {T.label(i)}" + (" (inferred)" if n.get("how") == "inferred" else "") + (f" · role {Q.role(T, i)}" if n["type"] == "entity" else "")
                if n["type"] == "activity" and n.get("inputs"):
                    head += " · inputs " + ", ".join(f"[{x}]" for x in n["inputs"].split(";") if x)
                counts[n["type"]] += 1
                sets_, res, comp = [], [], []                                      # (name, record) lists
                if n["type"] == "cited":
                    cond, res_ = Q.cited_records(T, i)
                    sets_ = [(v["name"], v["record"]) for v in cond.values()]; res = [(v["name"], v["record"]) for v in res_.values()]
                else:
                    for f in T.own(i):
                        if f["type"] == "setting" and Q.text_of(f):
                            sets_.append((Q.name_of(Q.ckey(f), f), Q.record(T, f, ent=ent)))
                        elif f["type"] in Q.RESULT_TYPES and (Q.text_of(f) or f["points_ref"]):
                            res.append((Q.name_of(Q.ckey(f), f), Q.record(T, f, ent=ent)))
                if n["type"] == "entity" and i in experiments:                        # the values the knowledge base computes for an experiment (lists.DERIVED)
                    comp = [(x["name"], x["record"]) for x in Q.result_records(T, i).values() if x["record"]["kind"] == "computed_by_kb"]
                counts["settings"] += len(sets_); counts["results"] += len(res); counts["computed"] += len(comp)
                recs = [r for _, r in sets_ + res + comp]
                for r in recs:
                    cav_ids.update(c["id"] for c in r.get("caveats") or [])
                def group(label, items, formula=False):                           # a group's caveats shared by every value of it: once, on the group
                    if not items:
                        return ""
                    lifted = set.intersection(*[{c["id"] for c in r.get("caveats") or []} for _, r in items]) if len(items) > 1 else set()
                    return f" · {label}" + (" (caveats on every one: " + ", ".join(f"[{c}]" for c in sorted(lifted)) + ")" if lifted else "") + ": " \
                        + "; ".join(f"{nm} {cell(r, lifted)}" + (f" = {r['definition']}" if formula else "") for nm, r in items)
                line = "  " * depth + head + group("settings", sets_) + group("results", res) + group("computed", comp, formula=True)
                out.append(line)
                depth += 1
            for c in T.kids.get(i, []):
                if c["type"] in ("activity", "entity", "cited") and "#" not in c["fact_id"]:
                    walk(c["fact_id"], depth)

        root = next(r["fact_id"] for r in T.rows if r["type"] == "paper")
        experiments = set(Q.experiments(T))
        walk(root, 0)
        for c in T.comps:
            ms = T.members(c)
            purpose = T.byid[c["links"].split(";")[0]]["statement"] if c["links"].split(";")[0] in T.byid else ""
            out.append(f"set [{c['fact_id']}] ({c['kind']}) {Q.comparison_label(T, c)} · varies {', '.join(L.NAMES.get(q, q) for q in c['quantity'].split(';') if q) or 'nothing stated'}"
                       f" · members {', '.join(f'[{m}]' for m in ms)}" + (f" · purpose: {purpose}" if purpose else "")); counts["sets"] += 1
        for f in T.rows:
            if f["type"] != "claim":
                continue
            cr = Q.claim_record(T, f)
            line = f"claim [{f['fact_id']}] ({cr['stance']}) {cr['statement']}"
            if cr["cause"] or cr["effect"]:
                line += f" · {', '.join(cr['cause']) or '?'} {cr['relation'] or '→'} {', '.join(cr['effect']) or '?'}"
            if cr["scope"] and cr["entities"]:
                line += f" · scope ({TL.KB}): {cr['scope']}"
            if cr["rests_on"]:
                line += " · rests on " + ", ".join(f"[{r['fact']}]" for r in cr["rests_on"] if r.get("fact"))
            if cr["sized_by"]:
                line += " · sized by " + ", ".join(f"[{r['fact']}]" for r in cr["sized_by"])
            line += TL.cmark(cr)
            cav_ids.update(c["id"] for c in cr.get("caveats", []))
            out.append(line); counts["claims"] += 1
        for cid in sorted(cav_ids):
            out.append(f"caveat [{cid}] {T.byid[cid]['statement']}"); counts["caveats"] += 1
        out.append("")
    out.append("legend · kinds: " + "; ".join(f"({TL.KIND_MARK[k]}) {TL.kind_phrase(k)}" for k in L.KINDS if k in marks) + "; unmarked: measured or stated by the paper")
    out += [f"legend · basis {b}: {L.BASES[b]}" for b in sorted(bases)]
    return "\n".join(out), counts


def given(text):
    """{id: its lines} for the number check: every line that starts with or names the id, as ask.py builds it from tool lines."""
    out = {}
    for ln in text.splitlines():
        for i in dict.fromkeys(ID.findall(ln)):
            if ":" in i:
                out[i] = (out.get(i, "") + "\n" + ln).strip()
    return out


if __name__ == "__main__":
    text, counts = serialize()
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(text, encoding="utf-8")
    print(f"{round(len(text) / 4):,} tokens ({len(text):,} characters), {text.count(chr(10)) + 1} lines; " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
