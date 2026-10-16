#!/usr/bin/env python3
"""The Knowledge base arm's access layer: the tool schemas and descriptions, and run_tool, which answers a tool call from query.py
as plain text, one line per returned value or row, starting with its id in square brackets (format and paging only; the tool
layer computes nothing). Also the page targets of ids (open_target). Used by ask.py; no model call here."""
import csv, difflib, json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import query as Q  # noqa: E402


def short_name(k):
    man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(encoding="utf-8"))}
    r = man[Q.KEY[k]]
    return f"{r['authors'].split(';')[0].strip().split()[-1]} {r['year']}"


# ---------------------------------------------------------------------------------------------------------------- tools (fixed)
QUANT = sorted(set(L.QUANTITIES) | set(L.DERIVED))
QUANT_WORDS = "; ".join(f"{q} ({L.NAMES[q]})" if L.NAMES.get(q, q) != q else q for q in QUANT)
NUMERIC_UNITS = "; ".join(f"{q} in {u}" for q, u in sorted(L.UNITS.items()) if u)
PAPER_KEYS = list(Q.KEY)
PAPER_WORDS = ", ".join(f"{k} = {short_name(k)}" for k in PAPER_KEYS)

VOCAB_BUDGET = 3000                 # tokens (chars/4); above it the vocabulary lists the names only (P41)


def vocabulary_text():
    """The vocabulary generated from the data (P41): every result and setting name with the papers it occurs in and how many
    experiments have it, and the record types search returns with their counts; names only when it would exceed VOCAB_BUDGET."""
    v = Q.vocabulary()
    types = Counter(r["type"] for r in Q.search_records())
    full = lambda kind: "; ".join(f"{n} ({', '.join(f'{p} {c}' for p, c in ps.items())})" for n, ps in sorted(v[kind].items(), key=lambda x: x[0].lower()))
    bare = lambda kind: "; ".join(sorted(v[kind], key=str.lower))
    text = lambda f: (f"Result names: {f('result')}. Setting names: {f('setting')}. Record types: "
                      + ", ".join(f"{t} ({types[t]})" for t in Q.SEARCH_TYPES if types[t]) + ".")
    t = text(full)
    return t if len(t) / 4 <= VOCAB_BUDGET else text(bare)


VOCAB = vocabulary_text()
PAGE_LINES = 25
MAX_LINE = 300
DETAIL_PARTS = ["what", "differs", "results", "recipe", "claims"]
DETAIL_DEFAULT = ["what", "differs", "results"]

TOOLS = [
    dict(name="search",
         description=("Searches the text of every record of the knowledge base by words (lexical: lowercase, plurals folded, _ and - as "
                      "spaces, numbers and units kept; no synonyms). Returns the records ranked by how well they match, at most "
                      f"{PAGE_LINES} lines per call, each '[id] record type · one line'; records with the same line are shown once with "
                      "their count. A last line gives the offset of the next page. The knowledge base's names, generated from its data: " + VOCAB),
         parameters=dict(type="object", properties=dict(
             words=dict(type="string", description="The words to look for."),
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             offset=dict(type="integer", description="Skip this many results (default 0).")),
             required=["words"])),
    dict(name="values",
         description=("Returns every value of one result (or stated setting) in the three papers, never a representative, grouped by the "
                      "comparison set its experiment belongs to (a series, grid or replicate set; one more group per paper for values "
                      "outside any set). A group header gives once: the paper, the set id, what the set varies, the conditions its "
                      "members share, and the result's definition when it is not the default or the paper defines it. A row gives the "
                      "settings that vary within the set, the value with uncertainty and unit, its kind (measured, stated, read from "
                      "figure, computed by the authors, computed here, model, cited, assumed) and its id. A group footer gives the ids of "
                      "the claims about the set; a last line says what differs between the groups (material, structure, reactor, process, "
                      "measurement). A quantity's base name covers all its definitions; a specific name only its own. "
                      f"At most {PAGE_LINES} lines per call; a last line gives the offset of the next page. "
                      "The knowledge base's names, generated from its data: " + VOCAB),
         parameters=dict(type="object", properties=dict(
             result=dict(type="string", description="A result or setting name from the list in this description, or a quantity id."),
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             where=dict(type="object", description="Only experiments whose stated settings match: {setting name: a value (number or text), or [min, max] (either may be null)}; numbers in the setting's unit as the values lines show it.",
                        additionalProperties={}),
             offset=dict(type="integer", description="Skip this many lines (default 0).")),
             required=["result"])),
    dict(name="find",
         description=("Lists the experiments of the three papers (deposited specimens and model runs), and the works the papers cite that "
                      "give values, that pass the given filters, grouped under the comparisons the authors made (a series, grid or "
                      "replicate set). A group line gives a comparison's id, label and members. A row gives the paper, the experiment's "
                      "name and id, one or two conditions that tell it apart from the other members of its comparison, and, when a result "
                      "quantity is given, each value of that quantity the experiment has: value and unit, kind (measured, stated, read from "
                      f"figure, computed by the authors, computed here from other values, model, cited, assumed), any non-default "
                      f"definition, the source element, and the paper's definition of the quantity when it has one (shortened; source gives it in full). At most {PAGE_LINES} lines per call; a last line gives the number of further "
                      "items and the offset that returns them."),
         parameters=dict(type="object", properties=dict(
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             material=dict(type="string", enum=list(L.MATERIALS), description="Only experiments whose film material is this."),
             structure=dict(type="string", enum=list(L.STRUCTURES), description="Only experiments on this kind of structure."),
             result=dict(type="string", enum=QUANT, description="Only experiments that have a value of this quantity, and list those values. Quantity ids with plain names: " + QUANT_WORDS + "."),
             conditions=dict(type="array", description="Only experiments whose stated condition lies in the range; numbers in the quantity's unit: " + NUMERIC_UNITS + ".",
                             items=dict(type="object", properties=dict(quantity=dict(type="string", enum=QUANT), low=dict(type="number"), high=dict(type="number")),
                                        required=["quantity"])),
             cited=dict(type="boolean", description="Include the cited works that give values (default true)."),
             offset=dict(type="integer", description="Skip this many items (default 0).")))),
    dict(name="detail",
         description=("Returns what the knowledge base holds about one item, given its id, in the parts asked for. For an experiment or an "
                      "input (a thing measured before deposition): what (role, material, substrate, inputs, the comparisons it belongs to, "
                      "identity statements), differs (the conditions that distinguish it from the other members of its comparison), "
                      "results (every result: value and unit, kind, definition when not the default, method, in situ or ex situ, "
                      "uncertainty, source element, the ids of other candidate values, the paper's definition of the quantity when it has "
                      "one, and for a value computed here its formula, inputs and assumed facts), recipe (every condition with value, unit, kind and source), claims (the claims that point at it "
                      "or its comparisons). For a comparison: what (purpose, what it varies, members), differs (the conditions that also "
                      "differ among the members), results (main results with the size of the effect against the scatter between repeats, "
                      "power-law fits with any confounder correction, these three computed here, not by the authors; values stated for "
                      "the whole set), claims. For a cited work: "
                      "what, recipe (its conditions), results (its values), claims. Claims are not in the default parts; claims with "
                      "linked=<id> also returns them."),
         parameters=dict(type="object", properties=dict(
             id=dict(type="string", description="An experiment, input, comparison or cited-work id as returned by find, detail, compare or claims."),
             parts=dict(type="array", items=dict(type="string", enum=DETAIL_PARTS), description="Any of what, differs, results, recipe, claims (default what, differs, results).")),
             required=["id"])),
    dict(name="compare",
         description=("Sets several experiments side by side: the conditions they share, the conditions that differ with each item's "
                      "value, and every result with each item's value (unit, kind, definition, source, the paper's definition of the "
                      "quantity when it has one); for two items, the ratio or difference of each shared result (computed here); a note where values cannot be set beside each other (different definitions); "
                      "measured curves as their points; and the ids of the claims linked to two or more of the items."),
         parameters=dict(type="object", properties=dict(
             ids=dict(type="array", items=dict(type="string"), description="Two or more experiment ids."),
             result=dict(type="string", enum=QUANT, description="Only this result quantity.")),
             required=["ids"])),
    dict(name="claims",
         description=("Returns the claims of the papers (and the user's claims across papers), one line each: its stance (asserted, "
                      "hedged, open, limitation), the statement, cause and effect in words, the range of conditions it covers (computed here), the "
                      "comparisons it reaches, its source element, and the ids of the stated results it rests on (source returns each "
                      f"in full). At most {PAGE_LINES} lines per call; a last line gives the number of further claims and the offset that "
                      "returns them."),
         parameters=dict(type="object", properties=dict(
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             variable=dict(type="string", description="Only claims whose cause or effect is this quantity id (" + ", ".join(QUANT) + ") or mechanism token (" + ", ".join("mechanism:" + m for m in L.MECHANISMS) + ")."),
             linked=dict(type="string", description="Only claims that point at this experiment or comparison id."),
             author=dict(type="string", enum=["user"], description="Only the user's claims across papers."),
             offset=dict(type="integer", description="Skip this many claims (default 0).")))),
    dict(name="source",
         description=("Returns the source of a fact or an element: the paper element (a paragraph, table cell, caption, equation or figure "
                      "panel), its locator, its text (figure panels have none), whether the knowledge base covers it, and every value the "
                      "facts of that element carry, each with the statement of the fact."),
         parameters=dict(type="object", properties=dict(id=dict(type="string", description="A fact id (as in the result lines) or an element id written <paper>:<element>.")),
                         required=["id"])),
]


# ---------------------------------------------------------------------------------------------------------------- tool lines
def _mode(m):
    return {"in_situ": "in situ", "ex_situ": "ex situ"}.get(m, "")


def value_line(r, name="", full=False):
    """A value record as one line: the value with its unit, kind, definition when not the default, method and mode, uncertainty,
    source element, the ids of other candidates; for a value computed here its formula, inputs and assumed facts; with full, the
    fact's statement and the measurement settings."""
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
        bits.append("uncertainty: " + (u if isinstance(u, str) else f"± {u.get('value')}" + (f" ({u.get('stat') or 'spread'} between {u['kind'].replace('_', ' ')}" + (f", n {u['n']}" if u.get("n") and u.get("n") != "not_stated" else "") + ")" if u.get("kind") and u["kind"] != "not_stated" else "")))
    if r.get("inputs"):
        bits.append("inputs: " + "; ".join(f"{i['name']} = {i['value']} {i['unit']}".strip() + (f" [{i['fact']}]" if i.get("fact") else "") for i in r["inputs"]))
    if r.get("assumed"):
        bits.append("assumed facts: " + ", ".join(r["assumed"]))
    if r.get("readings"):
        bits.append("readings: " + "; ".join(f"{x['value']} if {x['label']}" for x in r["readings"]))
    if r.get("source"):
        bits.append(f"source element: {r.get('paper')}:{r['source']}")
    if r.get("alternatives"):
        bits.append("other candidates: " + ", ".join(f"[{a['fact']}]" for a in r["alternatives"] if a.get("fact")))
    if full and r.get("statement"):
        bits.append("statement: " + r["statement"])
    if full and r.get("settings"):
        bits.append("measurement settings: " + "; ".join(f"{s['name']} {s['text']}" for s in r["settings"]))
    return " · ".join(b for b in bits if b)


_DEFS = {}


def defined_as(paper, key):
    """The paper's definition of a result key's quantity (a definition fact with that quantity whose qualifiers the key carries;
    the most specific one), as ' · defined as: "<short>" [id]'; source(id) gives it in full (P36)."""
    if paper not in Q.TREES:
        return ""
    if paper not in _DEFS:
        _DEFS[paper] = [(f["quantity"], set(filter(None, f["qualifiers"].split(";"))), f) for f in Q.TREES[paper].rows if f["type"] == "definition" and f["quantity"]]
    q = key.split("{")[0].split("[")[0]
    kq = set(filter(None, key.split("{", 1)[1].split("}")[0].split(";"))) if "{" in key else set()
    hits = sorted([(len(dq), f) for qq, dq, f in _DEFS[paper] if qq == q and dq <= kq], key=lambda x: -x[0])
    if not hits:
        return ""
    f = hits[0][1]
    st = f["statement"]
    short = st if len(st) <= 90 else st[:90].rsplit(" ", 1)[0] + " …"
    return f' · defined as: "{short}" [{f["fact_id"]}]'


def claim_line(c):
    """A claim as one line; the results it rests on as ids (source returns each in full)."""
    who = "by the user" if c.get("author") == "user" else short_name(c["paper"]) if c.get("paper") in Q.KEY else c.get("paper", "")
    return (c["id"], f"claim ({who}), {c['stance']}: {c['statement']}" + (f" · cause: {', '.join(c['cause'])}" if c.get("cause") else "")
            + (f" · effect: {', '.join(c['effect'])}" if c.get("effect") else "") + (f" · scope (kind: computed here): {c['scope']}" if c.get("scope") else "")
            + (f" · comparisons: {', '.join(c['comparisons'])}" if c.get("comparisons") else "")
            + (f" · source element: {c['paper']}:{c['source']}" if c.get("source") and c.get("paper") else "")
            + (" · rests on: " + ", ".join(f"[{r['fact']}]" for r in c["rests_on"] if r.get("fact")) if c.get("rests_on") else ""))


def wrap(i, text):
    """A line of at most MAX_LINE characters, continued on further lines with the same id when longer (cut at ' · ', '; ', ', ' or
    a space)."""
    out, t = [], text
    while len(t) > MAX_LINE - 2:
        cut = max((t.rfind(sep, 0, MAX_LINE - 2) for sep in (" · ", "; ", ", ", " ")), default=-1)
        cut = cut if cut > MAX_LINE // 3 else MAX_LINE - 2
        out.append((i, t[:cut].rstrip()))
        t = "… " + t[cut:].lstrip(" ·;,")
    out.append((i, t))
    return out


def page(items, offset, what):
    """Items (each a list of lines) from offset, at most PAGE_LINES lines, then a line naming how many items are left."""
    offset = max(0, int(offset or 0))
    lines, n = [], offset
    while n < len(items) and len(lines) + len(items[n]) <= PAGE_LINES - 1:
        lines += items[n]; n += 1
    if n < len(items):
        lines.append(("more", f"{len(items) - n} more {what}: call again with offset={n}"))
    return lines


def name_of_id(i):
    try:
        T = Q.tree_of(i)
        return T.label(i) if i in T.byid and T.byid[i]["type"] == "entity" else Q.detail(i).get("name") or Q.detail(i).get("label") or i
    except Exception:
        return i


def _closed(schema):
    """additionalProperties false on every object of a schema (P39)."""
    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)
        for v in schema.get("properties", {}).values():
            _closed(v)
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        _closed(schema["items"])
    return schema


for _t in TOOLS:
    _closed(_t["parameters"])
SCHEMA = {t["name"]: t["parameters"] for t in TOOLS}
TYPES = {"string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,), "array": (list,), "object": (dict,)}


def _check(where, v, sch):
    """The first error of a value against its schema: type, enum, the properties of an object, the items of an array."""
    t = sch.get("type")
    if t and (not isinstance(v, TYPES[t]) or (t in ("integer", "number") and isinstance(v, bool))):
        return f"{where} must be {'an' if t[0] in 'aeiou' else 'a'} {t}, not {type(v).__name__}"
    if "enum" in sch and v not in sch["enum"]:
        near = difflib.get_close_matches(str(v), [str(x) for x in sch["enum"]], n=5, cutoff=0.4)
        listed = ", ".join(map(str, sch["enum"])) if len(sch["enum"]) <= 12 else f"{len(sch['enum'])} names (see the description)"
        return f"{where}: unknown value {v!r}" + (f"; nearest: {', '.join(near)}" if near else "") + f"; valid: {listed}"
    if t == "object":
        props = sch.get("properties", {})
        bad = [k for k in v if k not in props] if sch.get("additionalProperties") is False else []
        if bad:
            return f"{where}: unknown argument{'s' if len(bad) > 1 else ''} {', '.join(bad)}; valid arguments: {', '.join(props)}"
        miss = [k for k in sch.get("required", []) if v.get(k) is None]
        if miss:
            return f"{where}: missing {', '.join(miss)}"
        for k, x in v.items():
            if x is not None and k in props:
                e = _check(f"{where}.{k}" if where else k, x, props[k])
                if e:
                    return e
    if t == "array":
        for n, x in enumerate(v):
            e = _check(f"{where}[{n}]", x, sch.get("items", {}))
            if e:
                return e
    return ""


def _item(i):
    """Whether an id names an experiment, input, comparison or cited work."""
    T = Q.TREES.get(i.split(":")[0])
    return bool(T and i in T.byid and T.byid[i]["type"] in ("entity", "comparison", "cited") and "#" not in i)


def _source(i):
    """Whether an id names a fact or a paper element (<paper>:<element>)."""
    k, _, rest = i.partition(":")
    if k not in Q.TREES or not rest:
        return False
    if i in Q.TREES[k].byid:
        return True
    return any(r["element_id"] == rest for r in csv.DictReader((HERE / f"{Q.KEY[k]}.elements.csv").open(encoding="utf-8")))


def _names(kind=None):
    v = Q.vocabulary()
    return set(v["result"]) | set(v["setting"]) if kind is None else set(v[kind])


def _result_ok(r):
    return r in _names() or r in QUANT


def _where_err(where):
    for k, x in where.items():
        if k not in _names("setting") and k not in QUANT:
            near = difflib.get_close_matches(k, sorted(_names("setting")), n=5, cutoff=0.4)
            return f"where: unknown setting {k!r}" + (f"; nearest: {', '.join(near)}" if near else "") + "; setting names are listed in the description"
        ok = isinstance(x, (str, int, float)) and not isinstance(x, bool) or (isinstance(x, list) and len(x) == 2 and all(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)) for v in x))
        if not ok:
            return f"where.{k}: give a number, a text, or [min, max] (numbers or null)"
    return ""


IDS = {("values", "result"): (_result_ok, "not a result or setting name of the knowledge base, nor a quantity id (names are listed in the description)"),
       ("detail", "id"): (_item, "no experiment, input, comparison or cited work has this id"),
       ("source", "id"): (_source, "no fact or paper element has this id"),
       ("compare", "ids"): (lambda i: _item(i) and Q.TREES[i.split(":")[0]].byid[i]["type"] == "entity", "no experiment has this id"),
       ("claims", "linked"): (_item, "no experiment or comparison has this id"),
       ("claims", "variable"): (lambda v: v in QUANT or (v.startswith("mechanism:") and v.split(":", 1)[1] in L.MECHANISMS), "not a quantity id or mechanism token")}


def validate(name, args):
    """An error text for a call the tool cannot answer as asked, else "" (P39): an unknown tool or argument, a wrong type, a value
    outside the vocabulary, an id that names nothing. An argument given as null counts as not given."""
    if name not in SCHEMA:
        return f"unknown tool {name}; tools: {', '.join(SCHEMA)}"
    if not isinstance(args, dict):
        return f"{name}: the arguments must be an object"
    e = _check("", args, SCHEMA[name])
    if e:
        return f"{name}: {e.lstrip('.')}" if not e.startswith(":") else f"{name}{e}"
    if name == "values" and isinstance(args.get("where"), dict):
        e = _where_err(args["where"])
        if e:
            return f"values: {e}"
    if name == "values" and args.get("result") is not None and not _result_ok(args["result"]):
        near = difflib.get_close_matches(args["result"], sorted(_names()), n=5, cutoff=0.4)
        return f"values: result {args['result']!r}: not a result or setting name of the knowledge base, nor a quantity id" + (f"; nearest: {', '.join(near)}" if near else "")
    for (tool, arg), (ok, why) in IDS.items():
        if tool == name and args.get(arg) is not None:
            for v in (args[arg] if isinstance(args[arg], list) else [args[arg]]):
                if not ok(v):
                    return f"{name}: {arg} {v!r}: {why}"
    return ""


def run_tool(name, args):
    """(lines, error): lines = [(id, text)] formatted from what query.py returns; nothing computed here; no line over MAX_LINE.
    A call that fails validation, or whose filters match nothing, returns an error text, never an unfiltered or empty result."""
    err = validate(name, args)
    if err:
        return [], "error: " + err
    args = {k: v for k, v in args.items() if v is not None}
    lines, err = _run(name, args)
    if not err and not [x for x in lines if x[0] != "more"]:
        err = f"error: {name}: nothing matches " + ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items()) \
              + ("" if name != "find" or "offset" not in args else " (or the offset is past the last item)")
    return lines, err


SEARCH_LINE = 200


def endpoints(e):
    """The minimum and maximum members of a set-level range, with their values and the settings that differ between them (P43)."""
    lo, hi = e["low"], e["high"]
    btw = "; ".join(f"{x['name']} {x['low']} vs {x['high']}" for x in e.get("between") or [])
    return (f"min {lo['name']} {lo['text']} [{lo['fact']}], max {hi['name']} {hi['text']} [{hi['fact']}]"
            + (f" (differ in: {btw})" if btw else " (no stated setting differs between them)"))


def effect_line(e):
    """An effect of a comparison on one result: its range with both endpoints, and the judgement against noise (computed here)."""
    unit = f" {e['unit']}" if e.get("unit") else ""
    return (f"effect on {e['name']}{' (main result)' if e.get('main') else ''} (kind: computed here): range {e['effect']}{unit} over {e['n']}: "
            + endpoints(e) + f" · {e['sentence']}")


def _unc(r):
    u = r.get("uncertainty")
    if not u:
        return ""
    if isinstance(u, str):
        return " " + u
    return f" ± {u.get('value')}" + (f" ({u.get('stat') or 'spread'} between {u['kind'].replace('_', ' ')}" + (f", n {u['n']}" if u.get("n") and u.get("n") != "not_stated" else "") + ")" if u.get("kind") and u["kind"] != "not_stated" else "")


def _span(nums):
    """Group numbers 1, 2, 3, 5 as '1–3, 5'."""
    out, run = [], []
    for n in sorted(nums):
        if run and n == run[-1] + 1:
            run.append(n)
        else:
            if run:
                out.append(f"{run[0]}–{run[-1]}" if len(run) > 2 else ", ".join(map(str, run)))
            run = [n]
    if run:
        out.append(f"{run[0]}–{run[-1]}" if len(run) > 2 else ", ".join(map(str, run)))
    return ", ".join(out)


def values_blocks(groups, asked):
    """The values output as blocks: per group a header (once), its rows, its footer; then the line on what differs between groups."""
    blocks = []
    for n, g in enumerate(groups, 1):
        T = Q.TREES[g["paper"]]
        names = list(dict.fromkeys(r["result_name"] for r in g["rows"]))
        bydef = {}                                                              # one line per distinct definition, naming its results
        for key in dict.fromkeys(r["key"] for r in g["rows"]):
            rec = next(r["record"] for r in g["rows"] if r["key"] == key)
            nm = next(r["result_name"] for r in g["rows"] if r["key"] == key)
            d = (rec.get("definition") if rec.get("kind") != "computed here" else f"formula {rec.get('definition')}") or ""
            pdef = defined_as(g["paper"], key)
            if d or pdef:
                bydef.setdefault("; ".join(x for x in (d, pdef.replace(' · defined as: ', 'the paper: ')) if x), []).append(nm)
        defs = [f"{', '.join(ns)}: {d}" for d, ns in bydef.items()]
        sid = g["id"] or f"{g['paper']}:outside"
        head = (f"group {n} · {short_name(g['paper'])} · " + (f"set [{g['id']}] ({g['kind']}): {g['label']}" if g["id"] else g["label"])
                + (f" · varies: {', '.join(g['varies'])}" if g["varies"] else "")
                + (" · shared: " + "; ".join(f"{x['name']} {x['record']['text']}" for x in g["shared"]) if g["shared"] else "")
                + (f" (+{g['more_shared']} more shared conditions: detail of the set)" if g["more_shared"] and g["id"] else ""))
        hl = [(sid, head)] + [(sid, "definition · " + d) for d in defs]
        rows = []
        for r in g["rows"]:
            rec = r["record"]
            st = ", ".join(f"{x['name']} {x['text']}" for x in r["settings"])
            val = (rec.get("text") or "curve") + _unc(rec)
            if rec.get("curve") and rec["curve"].get("points"):
                val = f"curve against {rec['curve'].get('x') or 'x'}: " + ", ".join(f"({x}, {y})" for x, y in rec["curve"]["points"])
            rows.append([(rec.get("fact") or r["entity"], f"{r['name']}" + (f" · {st}" if st else "") + f" · {val} · {rec.get('kind')}"
                          + (f" · {r['result_name']}" if len(names) > 1 or r["result_name"] != asked else "") + (f" · experiment [{r['entity']}]" if rec.get("fact") else ""))])
        foot = [(sid, "claims about this set: " + ", ".join(f"[{c}]" for c in g["claims"]))] if g["claims"] else []
        blocks.append(dict(head=hl, rows=rows, foot=foot, short=(sid, f"group {n} continued · {short_name(g['paper'])} · {g['label']}")))
    if len(groups) > 1:
        diff = []
        for aspect in ("material", "structure", "reactor", "process", "measurement"):
            by = {}
            for n, g in enumerate(groups, 1):
                for v in g[aspect] or ["not stated"]:
                    by.setdefault(v, []).append(n)
            if len(by) > 1:
                diff.append(f"{aspect}: " + "; ".join(f"{v} (group{'s' if len(ns) > 1 else ''} {_span(ns)})" for v, ns in by.items()))
        last = ("between groups, not one series: " + " · ".join(diff)) if diff else "the groups share material, structure, reactor, process and measurement"
        blocks.append(dict(head=[("between", last)], rows=[], foot=[], short=None))
    return blocks


def page_blocks(blocks, offset, budget_lines=PAGE_LINES):
    """Lines from offset (counted over all lines), at most budget_lines with a header repeated short when a page starts inside a
    group, then a line with the offset of the next page."""
    flat = []
    for b in blocks:
        flat += [(b, x) for x in b["head"]] + [(b, x) for r in b["rows"] for x in r] + [(b, x) for x in b["foot"]]
    offset = max(0, int(offset or 0))
    out, n = [], offset
    if 0 < offset < len(flat) and flat[offset][1] not in flat[offset][0]["head"] and flat[offset][0]["short"]:
        out.append(flat[offset][0]["short"])
    while n < len(flat) and len(out) < budget_lines - 1:
        out.append(flat[n][1]); n += 1
    if n < len(flat):
        out.append(("more", f"more: offset={n} ({len(flat) - n} lines left)"))
    return out


def _run(name, args):
    try:
        W = lambda pairs: [x for i, t in pairs for x in wrap(i, t)]
        if name == "values":
            groups = Q.values(args["result"], args.get("paper"), args.get("where"))
            if not groups:
                return [], ""
            blocks = values_blocks(groups, args["result"])
            for b in blocks:
                b["head"], b["foot"] = W(b["head"]), W(b["foot"])
                b["rows"] = [W(r) for r in b["rows"]]
            return page_blocks(blocks, args.get("offset")), ""
        if name == "search":
            if not Q.tokens(args["words"]):
                return [], "error: search: words has no letters or numbers"
            hits, items, seen = Q.search(args["words"], args.get("paper")), [], {}
            for h in hits:            # values and settings: one line per paper and quantity; other records: a line shown once with its count
                if h["type"] in ("value", "setting"):
                    T = Q.TREES[h["paper"]]; f = T.byid[h["id"]]
                    key = (h["paper"], h["type"], Q.name_of(Q.ckey(f), f))
                    g = seen.setdefault(key, [h, 0, []])
                    g[1] += 1
                    if Q.text_of(f) not in g[2]:
                        g[2].append(Q.text_of(f))
                    continue
                g = seen.setdefault((h["type"], h["line"]), [h, 0, None])
                g[1] += 1
            for key, (h, n, vals) in seen.items():
                if vals is not None:
                    shown = ", ".join(vals[:8]) + (f", … ({len(vals)} distinct)" if len(vals) > 8 else "")
                    line = f"{h['type']}s of {key[2]} in {short_name(key[0])}: {n} record{'s' if n > 1 else ''}, {shown}"
                else:
                    line = f"{h['type']} · {h['line']}" + (f" · {n} records with this line" if n > 1 else "")
                if len(line) > SEARCH_LINE:
                    line = line[:SEARCH_LINE - 2].rsplit(" ", 1)[0] + " …"
                items.append([(h["id"], line)])
            return page(items, args.get("offset"), "results"), ""
        W = lambda pairs: [x for i, t in pairs for x in wrap(i, t)]
        if name == "find":
            conds = {c["quantity"]: (c.get("low"), c.get("high")) for c in args.get("conditions") or []}
            f = Q.find(paper=args.get("paper"), material=args.get("material"), structure=args.get("structure"), result=args.get("result"),
                       conditions=conds or None, cited=args.get("cited", True))
            items = []
            for gr in f["groups"]:
                items.append(W([(gr["id"], f"comparison ({short_name(gr['paper'])}): {gr['label']} · kind: {gr['kind']} · members: "
                                 + ", ".join(f"[{m}]" for m in gr["all_members"] if m in f["rows"]))]))
            for i, r in f["rows"].items():
                d = "; ".join(f"{x['name']} {x['text']}" for x in r["distinguish"])
                head = f"{short_name(r['paper'])} · {r['name']}" + (" (inferred: not named by the paper)" if r["inferred"] else "") + f" · {r['role']}" + (f" · {d}" if d else "")
                if r["result"]:
                    items.append(W([(x["record"].get("fact") or i, f"{head} · experiment [{i}] · {value_line(x['record'], x['name'])}{defined_as(r['paper'], x['key'])}") for x in r["result"]]))
                else:
                    items.append(W([(i, head)]))
            return page(items, args.get("offset"), "items"), ""
        if name == "detail":
            parts = [p for p in (args.get("parts") or DETAIL_DEFAULT) if p in DETAIL_PARTS] or DETAIL_DEFAULT
            d = Q.detail(args["id"])
            i = d["id"]
            out = []
            if d["type"] == "entity":
                w = d["what"]
                if "what" in parts:
                    out.append((i, f"{short_name(d['paper'])} · {d['name']}" + (" (inferred: not named by the paper)" if d["inferred"] else "")
                                + f" · role: {d['role']}" + (f" · material: {w['material']}" if w.get("material") else "") + (f" · substrate: {w['substrate']}" if w.get("substrate") else "")
                                + (f" · made from: {', '.join(f'{n} [{x}]' for n, x in zip(w['inputs'], w['input_ids']))}" if w.get("inputs") else "")
                                + (f" · part of: [{w['parent']}]" if w.get("parent") else "") + (f" · statement: {d['statement']}" if d.get("statement") else "")))
                    out += [(c["id"], f"comparison it belongs to: {c['label']}") for c in d["comparisons"]]
                    out += [(i, f"identity ({x['kind']}): {x['statement']} · others: {', '.join(x['others'])}") for x in d["identity"]]
                if "differs" in parts and d["differs"]:
                    out.append((i, "distinguished by: " + "; ".join(f"{x['name']} {x['text']}" for x in d["differs"])))
                if "results" in parts:
                    out += [(r["record"].get("fact") or i, "result · " + value_line(r["record"], r["name"]) + defined_as(d["paper"], r["key"])) for r in d["results"]]
                if "recipe" in parts:
                    out += [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"])) for c in d["recipe"]]
            elif d["type"] == "comparison":
                if "what" in parts:
                    out.append((i, f"comparison ({short_name(d['paper'])}): {d['label']} · kind: {d['kind']} · varies: {', '.join(d['varies']) or 'nothing stated'}"
                                + (f" · statement: {d['statement']}" if d.get("statement") else "") + (f" · purpose: {d['purpose']}" if d.get("purpose") else "")))
                    out += [(m, f"member: {name_of_id(m)}") for m in d["members"]]
                if "differs" in parts and d["confounders"]:
                    out.append((i, "also differs among the members: " + json.dumps(d["confounders"], ensure_ascii=False, default=str)))
                if "results" in parts:
                    for e in d["effects"]:
                        out.append((i, effect_line(e)))
                    for f_ in d["fits"]:
                        out.append((i, f"fit (kind: computed here): {f_['name']} ∝ {f_['x']}^{f_['exponent']} (residual {f_['residual']}, {f_['n']} points)"
                                    + "".join(f" · correction (kind: computed here) for {c['condition']} to {c['to']}: exponent {c['exponent']} (residual {c['residual']}); "
                                              + "; ".join(f"{name_of_id(x['id'])} {x['frm']} × {x['factor']} = {x['value']} from {x['by']}" for x in c["changes"]) for c in f_["corrected"])))
                    out += [(v.get("fact") or i, "stated for the set · " + value_line(v)) for v in d["values"]]
            else:
                if "what" in parts:
                    out.append((i, f"cited work ({short_name(d['paper'])}): {d['name']} · statement: {d['statement']}"))
                if "recipe" in parts:
                    out += [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"])) for c in d["recipe"]]
                if "results" in parts:
                    out += [(r["record"].get("fact") or i, "value · " + value_line(r["record"], r["name"])) for r in d["results"]]
            if "claims" in parts:
                out += [claim_line(c) for c in d.get("claims", [])]
            return W(out), ""
        if name == "compare":
            c = Q.compare(args["ids"], result=args.get("result"))
            nm = {it["id"]: it["name"] for it in c["items"]}
            out = [(it["id"], f"item: {short_name(it['paper'])} · {it['name']}") for it in c["items"]]
            out += [(c["items"][0]["id"], f"shared condition: {s['name']} {s['text']}") for s in c["shared"]]
            for dff in c["differing"]:
                out += [(i, f"differing condition: {dff['name']}: {nm[i]} {v if v is not None else 'not stated'}") for i, v in dff["values"].items()]
            for r in c["results"]:
                for i, cell in r["cells"].items():
                    out.append(((cell or {}).get("fact") or i, f"result · {nm[i]} · " + (value_line(cell, r["name"]) + defined_as(cell.get("paper", ""), r["key"]) if cell else f"{r['name']}: no value")
                                + (f" · note: {r['note']}" if r.get("note") else "")))
                if r.get("relation"):
                    rel = r["relation"]
                    out.append((c["items"][0]["id"], f"{r['name']}: {rel['how']} {nm[c['items'][0]['id']]} to {nm[c['items'][1]['id']]} = {rel['value']} {rel['unit']}".strip() + " (kind: computed here)"))
            if c["claims"]:
                out.append((c["items"][0]["id"], "claims linked to two or more items: " + ", ".join(f"[{cl['id']}]" for cl in c["claims"])))
            return W(out), ""
        if name == "claims":
            cs = Q.claims(paper=args.get("paper"), variable=args.get("variable"), linked=args.get("linked"), author=args.get("author"))
            return page([wrap(*claim_line(c)) for c in cs], args.get("offset"), "claims"), ""
        if name == "source":
            s = Q.source(args["id"])
            eid = f"{s['paper']}:{s['element']}"
            out = [(eid, f"element {eid} ({s['kind']}, {s['locator']})" + (f" · covered: {s['coverage']}" if s.get("coverage") else "") + (f" · text: {s['text']}" if s.get("text") else " · no text (a figure panel)"))]
            out += [(v.get("fact") or eid, value_line(v, full=True)) for v in s["values"]]
            out += [(eid, f"statement without a value: {t}") for t in s["statements"]]
            return W(out), ""
        return [], f"error: unknown tool {name}"
    except Exception as e:
        return [], f"error: {type(e).__name__}: {e}"


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
