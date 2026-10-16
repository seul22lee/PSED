#!/usr/bin/env python3
"""Three ways to answer one question about the three pilot papers, side by side, with a number check.

    python3 psed_v2/pilot/ask.py "question" [--model vendor:model] [--arms model,text,kb]       # -> pilot/runs/asks.jsonl
    python3 psed_v2/pilot/ask.py --questions FILE --out RUNS.jsonl [--model vendor:model] [--arms model,text,kb]
                                 [--max-cost 20] [--max-calls 200]                            # -> RUNS.jsonl, RUNS.summary.csv

Arms (one model, its default settings, the same for all three; the three arms of a question run in parallel):
  model  Model only: the question, no documents, no tools.
  text   Paper text: every element of the three papers as "[id] text" in the system prompt (a table is one piece,
         <paper>:tabN, holding its caption and its markdown; figure panels have no text and are left out).
  kb     Knowledge base: the five query.py operations as tools; each returns plain text, one line per returned value or row,
         starting with its id in square brackets (format only, nothing computed here). At most 20 tool calls.
The models cite by writing ids in square brackets; nothing vendor-specific changes what a model sees (providers.py).
Number check: every number of the answer, sentence by sentence, against the texts of the ids cited in that sentence.
LLM API calls are allowed only in this file, providers.py and serve.py. Runs with conda env psed310 (the vendor SDKs).
"""
import argparse, concurrent.futures as cf, csv, datetime, json, math, re, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import elements as E  # noqa: E402
import lists as L  # noqa: E402
import providers as P  # noqa: E402
import query as Q  # noqa: E402

RUNS = HERE / "runs"
ARMS = ["model", "text", "kb"]
ARM_NAMES = {"model": "Model only", "text": "Paper text", "kb": "Knowledge base"}
TOOL_CAP = 20

# ---------------------------------------------------------------------------------------------------------------- prompts (fixed)
SHARED = """You answer questions from atomic layer deposition (ALD) researchers about three papers:
{papers}
Answer in English. Start with a direct answer in one or two sentences, then give the evidence.
For every number, give its unit and the conditions it was obtained under (material, process, temperature, structure or substrate, how it was measured), and say whether it was measured, read from a figure, computed by the authors, computed from other values, assumed, or taken from another work.
If the answer depends on conditions, say so and organize the answer by those conditions.
Say what your sources do not cover. State every assumption you make. If the question cannot be answered from what you have, say so and why."""

ARM_PROMPT = {
    "model": "You have no documents and no tools. Answer from your own knowledge. For each statement, say whether you know it from these papers specifically or from general knowledge, and how confident you are. Do not write source ids.",
    "text": "The full text of the three papers follows, split into pieces. Each piece starts with its id in square brackets. Base your answer on them. After every sentence that uses a piece, write the piece's id in square brackets, for example [yim20:s7.p5]. Cite only ids that appear below.",
    "kb": "You have tools that query a structured knowledge base built from the three papers. Use them. Every result line starts with its id in square brackets. After every sentence that uses a result, write the result's id in square brackets. Cite only ids the tools returned. Do not state a number from the papers that you did not obtain from a tool.",
}


def paper_lines():
    """One line per paper: authors (first author et al.), year, title, journal, DOI, from corpus/manifest.csv."""
    man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(encoding="utf-8"))}
    out = []
    for k, pid in Q.KEY.items():
        r = man[pid]
        first = r["authors"].split(";")[0].strip().split()[-1]
        out.append(f"- {first} et al. ({r['year']}). {r['title']}. {r['journal']}. DOI {r['doi']}.")
    return "\n".join(out)


def short_name(k):
    man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(encoding="utf-8"))}
    r = man[Q.KEY[k]]
    return f"{r['authors'].split(';')[0].strip().split()[-1]} {r['year']}"


_PIECES = {}


def pieces():
    """[(id, text)] of the three papers in elements.py order: abstract groups, headings, paragraphs, equations, captions, tables
    (one piece per table: caption and markdown, id <paper>:tabN or <paper>:tabuK); panels left out (no text)."""
    if _PIECES:
        return _PIECES["list"]
    out = []
    for k, pid in Q.KEY.items():
        rows, tx = E.build(pid)
        st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
        tables = {str(c["number"]): c for c in st["captions"] if c["kind"] == "table" and c.get("number")}
        untabs = [c for c in st["captions"] if c["kind"] == "table" and not c.get("number") and c.get("table")]
        seen = set()
        for r in rows:
            eid, kind = r["element_id"], r["kind"]
            if kind == "panel":
                continue
            m = re.match(r"tab([0-9IVXLC]+)\.cap$", eid)
            if m:
                c = tables[m.group(1)]
                out.append((f"{k}:tab{m.group(1)}", (c.get("caption") or "").strip() + "\n" + (c.get("table") or "").strip()))
                continue
            if kind == "table_cell":
                m = re.match(r"(tabu\d+)\.", eid)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    out.append((f"{k}:{m.group(1)}", (untabs[int(m.group(1)[4:]) - 1].get("table") or "").strip()))
                continue
            out.append((f"{k}:{eid}", tx[eid].strip()))
    _PIECES["list"] = out
    return out


def system_prompt(arm):
    s = SHARED.format(papers=paper_lines()) + "\n\n" + ARM_PROMPT[arm]
    if arm == "text":
        parts, cur = [], None
        for pid_, text in pieces():
            k = pid_.split(":")[0]
            if k != cur:
                parts.append(f"\n=== {short_name(k)} ({k}) ===")
                cur = k
            parts.append(f"[{pid_}] {text}")
        s += "\n\n" + "\n\n".join(parts)
    return s


# ---------------------------------------------------------------------------------------------------------------- tools (fixed)
QUANT = sorted(set(L.QUANTITIES) | set(L.DERIVED))
QUANT_WORDS = "; ".join(f"{q} ({L.NAMES[q]})" if L.NAMES.get(q, q) != q else q for q in QUANT)
NUMERIC_UNITS = "; ".join(f"{q} in {u}" for q, u in sorted(L.UNITS.items()) if u)
PAPER_KEYS = list(Q.KEY)
PAPER_WORDS = ", ".join(f"{k} = {short_name(k)}" for k in PAPER_KEYS)

TOOLS = [
    dict(name="find",
         description=("Lists the experiments of the three papers (deposited specimens and model runs), and the works the papers cite that "
                      "give values, that pass the given filters. Experiments are grouped under the comparisons the authors made (a series, "
                      "grid or replicate set). Each row gives the paper, the experiment's name, one or two conditions that tell it apart "
                      "from the other members of its comparison, and, when a result quantity is given, every value of that quantity the "
                      "experiment has, each with its unit, kind (measured, stated, read from figure, computed by the authors, computed "
                      "here from other values, model, cited, assumed), any non-default definition and its source element. Group lines "
                      "give each comparison's id, label and members. With no filter it lists everything."),
         parameters=dict(type="object", properties=dict(
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             material=dict(type="string", enum=list(L.MATERIALS), description="Only experiments whose film material is this."),
             structure=dict(type="string", enum=list(L.STRUCTURES), description="Only experiments on this kind of structure."),
             result=dict(type="string", enum=QUANT, description="Only experiments that have a value of this quantity, and list those values. Quantity ids with plain names: " + QUANT_WORDS + "."),
             conditions=dict(type="array", description="Only experiments whose stated condition lies in the range; numbers in the quantity's unit: " + NUMERIC_UNITS + ".",
                             items=dict(type="object", properties=dict(quantity=dict(type="string", enum=QUANT), low=dict(type="number"), high=dict(type="number")),
                                        required=["quantity"])),
             cited=dict(type="boolean", description="Include the cited works that give values (default true).")))),
    dict(name="detail",
         description=("Returns everything the knowledge base holds about one item, given its id. For an experiment or an input (a thing "
                      "measured before deposition): what it is (role, material, substrate, inputs), the conditions that distinguish it, its "
                      "full recipe (every condition with value, unit, kind and source), every result (value, unit, kind, definition when not "
                      "the default, method, in situ or ex situ, uncertainty, source element, other candidate values, and for a value "
                      "computed here its formula, inputs and assumed facts), the comparisons it belongs to, identity statements, and the "
                      "claims that point at it. For a comparison: its purpose, what it varies, its members, its main results with the size "
                      "of the effect against the scatter between repeats, power-law fits with any stated confounder correction, the "
                      "conditions that also differ, the values stated for the whole set, and its claims. For a cited work: its conditions, "
                      "values and claims."),
         parameters=dict(type="object", properties=dict(id=dict(type="string", description="An experiment, input, comparison or cited-work id as returned by find, detail, compare or claims.")),
                         required=["id"])),
    dict(name="compare",
         description=("Sets several experiments side by side: the conditions they share, the conditions that differ with each item's "
                      "value, and every result with each item's value (unit, kind, definition, source); for two items, the ratio or "
                      "difference of each shared result; a note where values cannot be set beside each other (different definitions); "
                      "measured curves as their points; and the claims linked to two or more of the items."),
         parameters=dict(type="object", properties=dict(
             ids=dict(type="array", items=dict(type="string"), description="Two or more experiment ids."),
             result=dict(type="string", enum=QUANT, description="Only this result quantity."),
             x=dict(type="string", description="The condition key to use as the abscissa of the plot specification (a key from the differing conditions).")),
             required=["ids"])),
    dict(name="claims",
         description=("Returns the claims of the papers (and the user's claims across papers): each with its stance (asserted, hedged, open, "
                      "limitation), the statement, cause and effect in words, the range of conditions it covers, the comparisons and "
                      "experiments it reaches, and the stated results it rests on (each a value line with its own id)."),
         parameters=dict(type="object", properties=dict(
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             variable=dict(type="string", description="Only claims whose cause or effect is this quantity id (" + ", ".join(QUANT) + ") or mechanism token (" + ", ".join("mechanism:" + m for m in L.MECHANISMS) + ")."),
             linked=dict(type="string", description="Only claims that point at this experiment or comparison id."),
             author=dict(type="string", enum=["user"], description="Only the user's claims across papers.")))),
    dict(name="source",
         description=("Returns the source of a fact or the element itself: the paper element (a paragraph, table cell, caption, equation or "
                      "figure panel), its locator, its text (figure panels have none), whether the knowledge base covers it, and every value "
                      "the facts of that element carry."),
         parameters=dict(type="object", properties=dict(id=dict(type="string", description="A fact id (as in the result lines) or an element id written <paper>:<element>.")),
                         required=["id"])),
]


# ---------------------------------------------------------------------------------------------------------------- tool lines
def _mode(m):
    return {"in_situ": "in situ", "ex_situ": "ex situ"}.get(m, "")


def value_line(r, name="", of=""):
    """A value record as one line: the value with its unit, kind, definition when not the default, method and mode, uncertainty,
    source element, other candidates; for a value computed here its formula, inputs and assumed facts."""
    if not r:
        return name + ": no value"
    bits = [f"{name}: {r.get('text', '')}" if name else r.get("text", "")]
    if r.get("curve") and r["curve"].get("points"):
        bits.append(f"curve against {r['curve'].get('x') or 'x'}, points (x, y): " + ", ".join(f"({x}, {y})" for x, y in r["curve"]["points"]))
    bits.append(f"kind: {r.get('kind', '')}")
    if r.get("definition"):
        bits.append(("formula: " if r.get("kind") == "computed here" else "definition: ") + r["definition"])
    if r.get("method") and r.get("method") != "calculation":
        bits.append("method: " + r["method"] + (f", {_mode(r.get('mode'))}" if _mode(r.get("mode")) else ""))
    u = r.get("uncertainty")
    if u:
        bits.append("uncertainty: " + (u if isinstance(u, str) else f"± {u.get('value')}" + (f" ({u.get('stat') or 'spread'} between {u['kind'].replace('_', ' ')}" + (f", n {u['n']}" if u.get("n") and u.get("n") != "not_stated" else "") + ")" if u.get("kind") else "")))
    if r.get("inputs"):
        bits.append("inputs: " + "; ".join(f"{i['name']} = {i['value']} {i['unit']}".strip() + (f" [{i['fact']}]" if i.get("fact") else "") for i in r["inputs"]))
    if r.get("assumed"):
        bits.append("assumed facts: " + ", ".join(r["assumed"]))
    if r.get("readings"):
        bits.append("readings: " + "; ".join(f"{x['value']} if {x['label']}" for x in r["readings"]))
    if r.get("source"):
        bits.append(f"source element: {r.get('paper')}:{r['source']}")
    if r.get("statement"):
        bits.append("statement: " + r["statement"])
    if r.get("settings"):
        bits.append("measurement settings: " + "; ".join(f"{s['name']} {s['text']}" for s in r["settings"]))
    if r.get("alternatives"):
        bits.append("other candidates: " + "; ".join(f"{a['text']} ({a['kind']}, {a.get('fact', '')})" for a in r["alternatives"]))
    if of:
        bits.append("of: " + of)
    return " · ".join(b for b in bits if b)


def claim_lines(c):
    """A claim as one line; the results it rests on inline as [id] value (kind), each in full through source(id)."""
    out = [(c["id"], f"claim ({'by the user' if c.get('author') == 'user' else short_name(c['paper']) if c.get('paper') in Q.KEY else c.get('paper', '')}), {c['stance']}: {c['statement']}"
                     + (f" · cause: {', '.join(c['cause'])}" if c.get("cause") else "") + (f" · effect: {', '.join(c['effect'])}" if c.get("effect") else "")
                     + (f" · scope: {c['scope']}" if c.get("scope") else "") + (f" · comparisons: {', '.join(c['comparisons'])}" if c.get("comparisons") else "")
                     + (f" · source element: {c['paper']}:{c['source']}" if c.get("source") and c.get("paper") else "")
                     + (" · rests on: " + "; ".join(f"[{r['fact']}] {r.get('text', '')} ({r.get('kind', '')})" for r in c["rests_on"] if r.get("fact")) if c.get("rests_on") else ""))]
    return out


def name_of_id(i):
    try:
        T = Q.tree_of(i)
        return T.label(i) if i in T.byid and T.byid[i]["type"] == "entity" else Q.detail(i).get("name") or Q.detail(i).get("label") or i
    except Exception:
        return i


def run_tool(name, args):
    """(lines, error): lines = [(id, text)] formatted from what query.py returns; nothing computed here."""
    try:
        if name == "find":
            conds = {c["quantity"]: (c.get("low"), c.get("high")) for c in args.get("conditions") or []}
            f = Q.find(paper=args.get("paper"), material=args.get("material"), structure=args.get("structure"), result=args.get("result"),
                       conditions=conds or None, cited=args.get("cited", True))
            lines = []
            for gr in f["groups"]:
                lines.append((gr["id"], f"comparison ({short_name(gr['paper'])}): {gr['label']} · kind: {gr['kind']} · members here: " + ", ".join(f"{f['rows'][m]['name']} [{m}]" for m in gr["all_members"] if m in f["rows"])))
            for i, r in f["rows"].items():
                d = "; ".join(f"{x['name']} {x['text']}" for x in r["distinguish"])
                head = f"{short_name(r['paper'])} · {r['name']}" + (" (inferred: not named by the paper)" if r["inferred"] else "") + f" · {r['role']}" + (f" · {d}" if d else "")
                if r["result"]:
                    for x in r["result"]:
                        lines.append((x["record"].get("fact") or i, f"{head} · {value_line(x['record'], x['name'])} · experiment id: {i}"))
                else:
                    lines.append((i, head))
            return lines, ""
        if name == "detail":
            d = Q.detail(args["id"])
            i = d["id"]
            lines = []
            if d["type"] == "entity":
                w = d["what"]
                lines.append((i, f"{short_name(d['paper'])} · {d['name']}" + (" (inferred: not named by the paper)" if d["inferred"] else "")
                              + f" · role: {d['role']}" + (f" · material: {w['material']}" if w.get("material") else "") + (f" · substrate: {w['substrate']}" if w.get("substrate") else "")
                              + (f" · made from: {', '.join(f'{n} [{x}]' for n, x in zip(w['inputs'], w['input_ids']))}" if w.get("inputs") else "")
                              + (f" · part of: {w['parent']}" if w.get("parent") else "") + (f" · statement: {d['statement']}" if d.get("statement") else "")))
                if d["differs"]:
                    lines.append((i, "distinguished by: " + "; ".join(f"{x['name']} {x['text']}" for x in d["differs"])))
                lines += [(c["id"], f"comparison: {c['label']}") for c in d["comparisons"]]
                lines += [(i, f"identity ({x['kind']}): {x['statement']} · others: {', '.join(x['others'])}") for x in d["identity"]]
                lines += [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"])) for c in d["recipe"]]
                lines += [(r["record"].get("fact") or i, "result · " + value_line(r["record"], r["name"])) for r in d["results"]]
            elif d["type"] == "comparison":
                lines.append((i, f"comparison ({short_name(d['paper'])}): {d['label']} · kind: {d['kind']} · varies: {', '.join(d['varies']) or 'nothing stated'}"
                              + (f" · statement: {d['statement']}" if d.get("statement") else "") + (f" · purpose: {d['purpose']}" if d.get("purpose") else "")))
                lines += [(m, f"member: {name_of_id(m)}") for m in d["members"]]
                for e in d["effects"]:
                    lines.append((i, f"effect on {e['name']}{' (main result)' if e.get('main') else ''}: " + "; ".join(f"{k} {v}" for k, v in e.items() if k not in ("key", "name", "main") and v not in ("", None, []))))
                for f_ in d["fits"]:
                    lines.append((i, f"fit: {f_['name']} ∝ {f_['x']}^{f_['exponent']} (residual {f_['residual']}, {f_['n']} points)"
                                  + "".join(f" · corrected for {c['condition']} to {c['to']}: exponent {c['exponent']} (residual {c['residual']}); "
                                            + "; ".join(f"{name_of_id(x['id'])} {x['frm']} × {x['factor']} = {x['value']} from {x['by']}" for x in c["changes"]) for c in f_["corrected"])))
                if d["confounders"]:
                    lines.append((i, "also differs among the members: " + json.dumps(d["confounders"], ensure_ascii=False, default=str)))
                lines += [(v.get("fact") or i, "stated for the set · " + value_line(v)) for v in d["values"]]
            else:
                lines.append((i, f"cited work ({short_name(d['paper'])}): {d['name']} · statement: {d['statement']}"))
                lines += [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"])) for c in d["recipe"]]
                lines += [(r["record"].get("fact") or i, "value · " + value_line(r["record"], r["name"])) for r in d["results"]]
            for c in d.get("claims", []):
                lines += claim_lines(c)
            return lines, ""
        if name == "compare":
            c = Q.compare(args["ids"], result=args.get("result"), x=args.get("x"))
            nm = {it["id"]: it["name"] for it in c["items"]}
            lines = [(it["id"], f"item: {short_name(it['paper'])} · {it['name']}") for it in c["items"]]
            lines += [(c["items"][0]["id"], f"shared condition: {s['name']} {s['text']}") for s in c["shared"]]
            for dff in c["differing"]:
                lines += [(i, f"differing condition: {dff['name']}: {nm[i]} {v if v is not None else 'not stated'}") for i, v in dff["values"].items()]
            for r in c["results"]:
                for i, cell in r["cells"].items():
                    lines.append(((cell or {}).get("fact") or i, f"result · {nm[i]} · " + (value_line(cell, r["name"]) if cell else f"{r['name']}: no value")
                                  + (f" · note: {r['note']}" if r.get("note") else "")))
                if r.get("relation"):
                    rel = r["relation"]
                    lines.append((c["items"][0]["id"], f"{r['name']}: {rel['how']} {nm[c['items'][0]['id']]} to {nm[c['items'][1]['id']]} = {rel['value']} {rel['unit']}".strip()))
            for cl in c["claims"]:
                lines += claim_lines(cl)
            return lines, ""
        if name == "claims":
            cs = Q.claims(paper=args.get("paper"), variable=args.get("variable"), linked=args.get("linked"), author=args.get("author"))
            return [ln for c in cs for ln in claim_lines(c)], ""
        if name == "source":
            s = Q.source(args["id"])
            eid = f"{s['paper']}:{s['element']}"
            lines = [(eid, f"element {eid} ({s['kind']}, {s['locator']})" + (f" · covered: {s['coverage']}" if s.get("coverage") else "") + (f" · text: {s['text']}" if s.get("text") else " · no text (a figure panel)"))]
            lines += [(v.get("fact") or eid, value_line(v)) for v in s["values"]]
            lines += [(eid, f"statement without a value: {t}") for t in s["statements"]]
            return lines, ""
        return [], f"unknown tool {name}"
    except Exception as e:
        return [], f"error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------------------------------------------- number check
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
ABBR = ["et al.", "e.g.", "i.e.", "Figs.", "Fig.", "Eqs.", "Eq.", "refs.", "ref.", "Ref.", "vs.", "approx.", "ca.", "cf.", "No.", "resp.", "Ref.", "Refs."]
MARK = re.compile(r"\[([^\[\]\n]+)\]")
ID = re.compile(r"^[A-Za-z0-9_]+:\S+$")
SCI = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[×x·*]\s*10\s*\^\s*\(?\s*([-+]?\d+)\s*\)?|(?<![\w.^])10\s*\^\s*\(?\s*([-+]?\d+)\s*\)?|(?<![\w.])(\d+(?:\.\d+)?)[eE]([-+]?\d+)(?![\w])")
PLAIN = re.compile(r"(?<![\w.^\u0300-\u036f])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")
SKIP = re.compile(r"\b(?:Fig(?:ure)?s?\.?|Tables?|Eq(?:uation)?s?\.?|[Rr]efs?\.?|[Rr]eferences?|[Ss]amples?|Series)\s*\(?\d+[a-z]?", re.I)


def normalize(t):
    t = t.translate(SUP)
    t = re.sub(r"\\(?:times)", "×", t)
    t = re.sub(r"\\(?:cdot)", "·", t)
    t = re.sub(r"\\(?:text|mathrm|mathit)\s*", "", t)
    t = t.replace("$", "").replace("{", "").replace("}", "").replace("\\,", "").replace("−", "-").replace("–", " – ")
    t = re.sub(r"(?<=\d)[\u2009\u202f\u00a0](?=\d{3}\b)", "", t)                     # 17 000 with a thin space
    return t


def nums(t, skip=False):
    """[(value, half of the last digit's unit, text)] of a text: a × 10^b, 10^b, aEb, then plain numbers; digits attached to a letter
    (formulas, units, labels like PD50) are not numbers; with skip, numbers that follow Fig., Table, Eq., ref., sample or Series and
    years are left out."""
    t = normalize(t)
    out = []

    def sci(m):
        if m.group(3) is not None:
            e = int(m.group(3)); out.append((10.0 ** e, 0.0, m.group(0)))
        else:
            a, e = (m.group(1), m.group(2)) if m.group(1) is not None else (m.group(4), m.group(5))
            d = len(a.split(".")[1]) if "." in a else 0
            out.append((float(a) * 10.0 ** int(e), 0.5 * 10.0 ** (int(e) - d), m.group(0)))
        return " "
    t = SCI.sub(sci, t)
    if skip:
        t = SKIP.sub(" ", t)
    t = re.sub(r"(?<=[A-Za-zµÅΩ\u0300-\u036f_])\^?-?\d+(?:\.\d+)?", " ", t)
    for m in PLAIN.finditer(t):
        ip, fp = m.group(1).replace(",", ""), m.group(2)
        v = float(ip + ("." + fp if fp else ""))
        if skip and not fp and "," not in m.group(1) and len(ip) == 4 and 1900 <= v <= 2100 and not re.match(r"\s*[A-Za-zµÅΩ°%]", t[m.end():]):
            continue                                                              # a year
        out.append((v, 0.5 * 10.0 ** (-len(fp) if fp else 0), m.group(0)))
    return out


def sentences(text):
    """[(sentence text without markers, [cited ids])]: lines, then sentences; markers right after a sentence's end belong to it."""
    out = []
    for line in text.splitlines():
        s = line
        for i, a in enumerate(ABBR):
            s = s.replace(a, f"\x00{i}\x00")
        parts = re.split(r"(?<=[.!?])((?:\s*\[[^\[\]\n]+\])*)\s+(?=[A-Z(*\"“#-])", s)
        segs = [parts[0]]
        for j in range(1, len(parts), 2):
            segs[-1] += parts[j] or ""
            segs.append(parts[j + 1])
        for seg in segs:
            seg = re.sub("\x00(\\d+)\x00", lambda m: ABBR[int(m.group(1))], seg)
            ids = []
            for m in MARK.finditer(seg):
                toks = [x.strip().rstrip(".,;") for x in re.split(r"[,;]\s*|\s+", m.group(1)) if x.strip()]
                if toks and all(ID.match(x) for x in toks):
                    ids += toks
            clean = MARK.sub(lambda m: " " if all(ID.match(x.strip().rstrip(".,;")) for x in re.split(r"[,;]\s*|\s+", m.group(1)) if x.strip()) else m.group(0), seg)
            if clean.strip() or ids:
                out.append((clean, ids))
    return out


def number_check(text, arm, given):
    """Per number: matches (in the text of an id cited in its sentence, allowing for rounding of the last digit), mismatch (the
    sentence cites ids, none holds it), not in any source (no id cited); and the cited ids not given to the model."""
    rows, unknown, cited = [], [], []
    for sent, ids in sentences(text):
        known = [i for i in ids if i in given]
        unknown += [i for i in ids if i not in given and i not in unknown]
        cited += [i for i in known if i not in cited]
        pool = [n for i in known for n in nums(given[i])]
        for v, half, raw in nums(sent, skip=True):
            if arm == "model" or not ids:
                st = "not in any source"
            elif any(abs(abs(v) - abs(c)) <= max(half, 1e-12 * abs(v)) * (1 + 1e-9) or abs(v) == abs(c) for c, _, _ in pool):
                st = "matches"
            else:
                st = "mismatch"
            rows.append(dict(number=raw.strip(), value=v, status=st, sentence=sent.strip()[:300], ids=ids))
    c = {k: sum(r["status"] == k for r in rows) for k in ("matches", "mismatch", "not in any source")}
    return dict(numbers=len(rows), match=c["matches"], mismatch=c["mismatch"], not_in_source=c["not in any source"],
                unknown_ids=len(unknown), unknown=unknown, cited=cited, per_number=rows)


def check_line(nc):
    parts = [f"{nc['numbers']} numbers"] + [f"{nc[k]} {w}" for k, w in (("match", "match"), ("mismatch", "mismatch"), ("not_in_source", "not in any source")) if nc[k]]
    return " · ".join(parts + [f"{nc['unknown_ids']} unknown ids"])


# ---------------------------------------------------------------------------------------------------------------- page targets
def open_target(i):
    """What the page opens for an id: a detail panel (experiment, input, comparison, cited work) or a source panel (an element;
    a fact opens the source panel of its first element; <paper>:tabN opens tabN.cap; <paper>:tabuK its first cell)."""
    k, _, rest = i.partition(":")
    if k not in Q.TREES:
        return dict(type="none")
    T = Q.TREES[k]
    if i in T.byid:
        n = T.byid[i]
        if n["type"] in ("entity", "comparison", "cited") and "#" not in i:
            return dict(type="comparison" if n["type"] == "comparison" else "detail", id=i)
        ev = (n.get("evidence") or "").split(";")[0]
        return dict(type="source", id=f"{k}:{ev}", fact=i) if ev else dict(type="none")
    if re.match(r"tab[0-9IVXLC]+$", rest):
        return dict(type="source", id=f"{i}.cap")
    if re.match(r"tabu\d+$", rest):
        return dict(type="source", id=f"{i}.r0c0")
    return dict(type="source", id=i)


# ---------------------------------------------------------------------------------------------------------------- prices, records
def price(model):
    vendor, name = model.split(":", 1)
    f = HERE / "prices.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if r.get("vendor") == vendor and r.get("model") == name and r.get("input_per_mtok") and r.get("output_per_mtok"):
                return float(r["input_per_mtok"]), float(r["output_per_mtok"])
    return None


def cost_of(model, usage):
    p = price(model)
    return None if p is None else (usage["input"] * p[0] + usage["output"] * p[1]) / 1e6


_LOCK = threading.Lock()


def append(path, rec):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------------------------------------------- arms
def run_arm(arm, question, model):
    t0 = time.time()
    usage = dict(input=0, output=0, cache_read=0, cache_write=0)
    calls, tool_calls, given, text, error = 0, [], {}, "", ""
    try:
        s = P.session(model, system_prompt(arm), TOOLS if arm == "kb" else None)
        if arm == "text":
            given = dict(pieces())
        t = s.send(question); calls += 1
        for k in usage:
            usage[k] += t.usage.get(k, 0)
        while t.calls and arm == "kb":
            results = []
            for c in t.calls:
                if len(tool_calls) >= TOOL_CAP:
                    results.append(dict(id=c["id"], name=c["name"], content=f"error: the limit of {TOOL_CAP} tool calls is reached", error=True))
                    tool_calls.append(dict(name=c["name"], arguments=c["arguments"], results=0, error="cap")); continue
                lines, err = run_tool(c["name"], c["arguments"])
                for i, ln in lines:                                       # an id's text: every returned line that starts with it or names it
                    for j in dict.fromkeys([i] + MARK.findall(ln)):
                        given[j] = (given.get(j, "") + "\n" + ln).strip()
                results.append(dict(id=c["id"], name=c["name"], content=err or "\n".join(f"[{i}] {ln}" for i, ln in lines) or "no results", error=bool(err)))
                tool_calls.append(dict(name=c["name"], arguments=c["arguments"], results=len(lines), error=err))
            t = s.send(results=results); calls += 1
            for k in usage:
                usage[k] += t.usage.get(k, 0)
            if calls > TOOL_CAP + 10:
                break
        text = t.text
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    nc = number_check(text, arm, given)
    return dict(time=datetime.datetime.now().isoformat(timespec="seconds"), question=question, arm=arm, model=model, answer=text,
                cited={i: dict(text=given[i], open=open_target(i)) for i in nc["cited"]}, unknown_ids=nc["unknown"], tool_calls=tool_calls,
                number_check={k: v for k, v in nc.items() if k not in ("cited", "unknown")}, check_line=check_line(nc), usage=usage, model_calls=calls,
                cost=cost_of(model, usage), seconds=round(time.time() - t0, 1), error=error)


def ask(question, model=None, arms=None, out=None):
    """The arms of one question in parallel; each record appended to out (default runs/asks.jsonl)."""
    model = model or P.default_model()
    arms = arms or ARMS
    with cf.ThreadPoolExecutor(len(arms)) as ex:
        recs = list(ex.map(lambda a: run_arm(a, question, model), arms))
    for r in recs:
        append(out or RUNS / "asks.jsonl", r)
    return recs


def last_records(question, model, path=None):
    """The last record of each arm for this question and model, from runs/asks.jsonl."""
    path = Path(path or RUNS / "asks.jsonl")
    last = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["question"].strip() == question.strip() and r["model"] == model:
                last[r["arm"]] = r
    return [last[a] for a in ARMS if a in last]


SUMMARY = ["question", "arm", "model", "numbers", "match", "mismatch", "not_in_source", "unknown_ids", "tool_calls", "input_tokens", "output_tokens",
           "cache_read_tokens", "cost", "seconds", "error"]


def summary_row(r):
    nc = r["number_check"]
    return dict(question=r["question"], arm=r["arm"], model=r["model"], numbers=nc["numbers"], match=nc["match"], mismatch=nc["mismatch"],
                not_in_source=nc["not_in_source"], unknown_ids=nc["unknown_ids"], tool_calls=len(r["tool_calls"]), input_tokens=r["usage"]["input"],
                output_tokens=r["usage"]["output"], cache_read_tokens=r["usage"]["cache_read"], cost="" if r["cost"] is None else round(r["cost"], 4),
                seconds=r["seconds"], error=r["error"])


def batch(qfile, out, model, arms, max_cost, max_calls):
    qs = [l.strip() for l in Path(qfile).read_text(encoding="utf-8").splitlines() if l.strip()]
    out = Path(out)
    rows, spent, calls = [], 0.0, 0
    priced = price(model) is not None
    for n, q in enumerate(qs, 1):
        if (priced and spent >= max_cost) or (not priced and calls >= max_calls):
            print(f"stopped before question {n}: {'cost' if priced else 'model calls'} limit reached"); break
        for r in ask(q, model, arms, out):
            rows.append(summary_row(r)); spent += r["cost"] or 0; calls += r["model_calls"]
            print(f"{n:3d} {ARM_NAMES[r['arm']]:15s} {r['check_line']}{' · ERROR ' + r['error'][:80] if r['error'] else ''}")
    summ = out.with_suffix(".summary.csv")
    with summ.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY); w.writeheader(); w.writerows(rows)
    print("totals per arm:")
    for a in arms:
        rs = [r for r in rows if r["arm"] == a]
        tot = {k: sum(r[k] for r in rs) for k in ("numbers", "match", "mismatch", "not_in_source", "unknown_ids", "tool_calls", "input_tokens", "output_tokens")}
        cost = sum(r["cost"] for r in rs if r["cost"] != "") if priced else "cost not set"
        print(f"  {ARM_NAMES[a]:15s} {tot} cost {cost} · failed: {sum(1 for r in rs if r['error'])}")
    print(f"records {out}; summary {summ}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--questions"); ap.add_argument("--out"); ap.add_argument("--model"); ap.add_argument("--arms", default="model,text,kb")
    ap.add_argument("--max-cost", type=float, default=20.0); ap.add_argument("--max-calls", type=int, default=200)
    a = ap.parse_args()
    model, arms = a.model or P.default_model(), a.arms.split(",")
    if a.questions:
        batch(a.questions, a.out or str(RUNS / "batch.jsonl"), model, arms, a.max_cost, a.max_calls)
    elif a.question:
        for r in ask(a.question, model, arms):
            print(f"== {ARM_NAMES[r['arm']]} ({r['model']}) · {r['check_line']} · {r['usage']['input']} in / {r['usage']['output']} out tokens · "
                  f"{'cost not set' if r['cost'] is None else '$%.3f' % r['cost']} · {r['seconds']} s")
            print(r["error"] or r["answer"]); print()
    else:
        ap.print_help()
