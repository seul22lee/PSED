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
DETAIL_PARTS = ["what", "differs", "results", "recipe", "claims", "computed"]
DETAIL_DEFAULT = ["what", "differs", "results"]

TOOLS = [
    dict(name="search",
         description=("Arguments: words (required), paper, offset. Returns the records whose text matches the words, best first, one line "
                      "each: '[id] record type · line' (lexical: lowercase, plurals folded, _ and - as spaces, numbers and units kept; no "
                      "synonyms). The values and settings of one quantity come as one line with their distinct values; a line whose value "
                      "has a caveat carries the caveat's id, and the caveat's text follows once. At most 25 lines and about 2,000 tokens "
                      "per call, then 'more: offset=N'. Use it to find where something is discussed and what the knowledge base calls it. "
                      "The knowledge base's names, generated from its data: " + VOCAB),
         parameters=dict(type="object", properties=dict(
             words=dict(type="string", description="The words to look for."),
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             offset=dict(type="integer", description="Skip this many results (default 0).")),
             required=["words"])),
    dict(name="values",
         description=("Arguments: result (required), paper, where, offset. Returns every value of one result or stated setting, never a "
                      "representative, grouped by the comparison set its experiment belongs to (a series, grid or replicate set; one more "
                      "group per paper for values outside any set). A group header gives once the paper, the set id, what the set varies, "
                      "the conditions its members share (those every group of a paper shares are given once) and the result's definition "
                      "when it is not the default or the paper defines it; a row gives the settings that vary within the set, the value "
                      "with uncertainty and unit, its kind (measured, stated, read from figure, computed by the authors, computed here, "
                      "model, cited, assumed), its id and the id of any caveat; under the group come the caveats' texts and the ids of the "
                      "claims about the set; a last line says what differs between the groups (material, structure, reactor, process, "
                      "measurement). A quantity's base name covers all its definitions, a specific name only its own. About 2,000 tokens "
                      "per call, then 'more: offset=N'. Use it to see how one result or setting varies across experiments and conditions. "
                      "The knowledge base's names, generated from its data: " + VOCAB),
         parameters=dict(type="object", properties=dict(
             result=dict(type="string", description="A result or setting name from the list in this description, or a quantity id."),
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             where=dict(type="object", description="Only experiments whose stated settings match: {setting name: a value (number or text), or [min, max] (either may be null)}; numbers in the setting's unit as the values lines show it.",
                        additionalProperties={}),
             offset=dict(type="integer", description="Skip this many output units (default 0).")),
             required=["result"])),
    dict(name="detail",
         description=("Arguments: id (required), parts, offset. Returns what the knowledge base holds about one id. An experiment or input: "
                      "what (role, material, substrate, inputs, the methods its results were measured by, its comparison sets, identity "
                      "statements, its caveats), differs (the conditions that set it apart in its set), results (value, unit, kind, "
                      "definition, method, in situ or ex situ, uncertainty, source element, caveats), recipe (every condition), claims, "
                      "computed (values computed here, with formula, inputs and assumed facts). A comparison set: what, its members as one "
                      "table of the settings that vary, results (values stated for the set), claims, computed (each effect with its "
                      "minimum and maximum members and the scatter between repeats, and power-law fits). A claim: the statement, stance, "
                      "cause and effect, its scope (computed here), the results it rests on, the facts that give its size, its caveats. A "
                      "cited work: what, recipe, results, claims. Any other id (a value, setting, definition, caveat, note, process step): "
                      "the record, what it belongs to, its source element and caveats; a caveat also lists what it qualifies. parts "
                      "(default what, differs, results) applies to experiments, inputs, sets and cited works. About 2,000 tokens per call, "
                      "then 'more: offset=N'. Use it for more about one id that search or values returned."),
         parameters=dict(type="object", properties=dict(
             id=dict(type="string", description="An id as search, values or detail returned it."),
             parts=dict(type="array", items=dict(type="string", enum=DETAIL_PARTS), description="Any of what, differs, results, recipe, claims, computed (default what, differs, results)."),
             offset=dict(type="integer", description="Skip this many output units (default 0).")),
             required=["id"])),
    dict(name="source",
         description=("Arguments: id (required), offset. Returns the paper element behind a fact or element id: its locator, its text "
                      "(figure panels have none), whether the knowledge base covers it, and every value the facts of that element carry, "
                      "with their statements and caveats. About 2,000 tokens per call, then 'more: offset=N'. Use it to read the paper's "
                      "own words behind an id."),
         parameters=dict(type="object", properties=dict(
             id=dict(type="string", description="A fact id or an element id written <paper>:<element>."),
             offset=dict(type="integer", description="Skip this many output units (default 0).")),
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
        bits.append("uncertainty: " + (u if isinstance(u, str) else f"± {u.get('value')}" + Q.unc_note(u)))
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


def cmark(rec):
    """The caveat marker of a value line (P45): ' · caveat [id]'."""
    cs = (rec or {}).get("caveats") or []
    return (" · caveat " if len(cs) == 1 else " · caveats ") + ", ".join(f"[{c['id']}]" for c in cs) if cs else ""


def clines(rec):
    """The caveat lines of a value: (id, 'caveat: text'), printed once per page (paginate)."""
    return [(c["id"], f"caveat · {c['text']}") for c in (rec or {}).get("caveats") or []]


def claim_line(c):
    """A claim as one line; the results it rests on as ids (source returns each in full)."""
    who = "by the user" if c.get("author") == "user" else short_name(c["paper"]) if c.get("paper") in Q.KEY else c.get("paper", "")
    return (c["id"], f"claim ({who}), {c['stance']}: {c['statement']}" + (f" · cause: {', '.join(c['cause'])}" if c.get("cause") else "")
            + (f" · effect: {', '.join(c['effect'])}" if c.get("effect") else "") + (f" · scope (kind: computed here): {c['scope']}" if c.get("scope") else "")
            + (f" · comparisons: {', '.join(c['comparisons'])}" if c.get("comparisons") else "")
            + (f" · source element: {c['paper']}:{c['source']}" if c.get("source") and c.get("paper") else "")
            + (" · rests on: " + ", ".join(f"[{r['fact']}]" for r in c["rests_on"] if r.get("fact")) if c.get("rests_on") else "")
            + (" · sized by: " + ", ".join(f"[{r['fact']}]" for r in c["sized_by"]) if c.get("sized_by") else "") + cmark(c))


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


def _record(i):
    """Whether an id names a record of the knowledge base (any row but a paper's)."""
    T = Q.TREES.get(i.split(":")[0])
    return bool(T and i in T.byid and T.byid[i]["type"] != "paper")


IDS = {("values", "result"): (_result_ok, "not a result or setting name of the knowledge base, nor a quantity id (names are listed in the description)"),
       ("detail", "id"): (_record, "no record of the knowledge base has this id"),
       ("source", "id"): (_source, "no fact or paper element has this id")}


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
    """(lines, error): lines = [(id, text)] formatted from what query.py returns; nothing computed here; no line over MAX_LINE; at
    most BUDGET_TOKENS (chars/4) per call, then 'more: offset=N' (P44). A call that fails validation, or whose filters match
    nothing, returns an error text, never an unfiltered or empty result."""
    err = validate(name, args)
    if err:
        return [], "error: " + err
    args = {k: v for k, v in args.items() if v is not None}
    blocks, err = _run(name, args)
    lines = [] if err else paginate(blocks, args.get("offset"), PAGE_LINES if name == "search" else None)
    if not err and not [x for x in lines if x[0] != "more"]:
        err = f"error: {name}: nothing matches " + ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items()) \
              + (" (or the offset is past the end)" if args.get("offset") else "")
    return lines, err




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
    return f" ± {u.get('value')}" + Q.unc_note(u)


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
    common = {}                                                                 # conditions every group of a paper shares: once, per paper (P44)
    for k in dict.fromkeys(g["paper"] for g in groups):
        gs = [g for g in groups if g["paper"] == k]
        sets = [{(x["key"], x["record"]["text"]) for x in g["shared"]} for g in gs]
        common[k] = set.intersection(*sets) if len(gs) > 1 else set()
    for n, g in enumerate(groups, 1):
        T = Q.TREES[g["paper"]]
        ctx = []
        if common[g["paper"]]:
            cs = [x for x in g["shared"] if (x["key"], x["record"]["text"]) in common[g["paper"]]]
            ctx = [(g["id"] or f"{g['paper']}:outside", f"{short_name(g['paper'])} · every group of this paper shares: "
                    + "; ".join(f"{x['name']} {x['record']['text']}{cmark(x['record'])}" for x in cs))] + [y for x in cs for y in clines(x["record"])]
            if n == 1 or groups[n - 2]["paper"] != g["paper"]:
                blocks.append(block([], head=ctx))
        own_shared = [x for x in g["shared"] if (x["key"], x["record"]["text"]) not in common[g["paper"]]]
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
                + (" · shared: " + "; ".join(f"{x['name']} {x['record']['text']}{cmark(x['record'])}" for x in own_shared) if own_shared else "")
                + (f" (+{g['more_shared']} more shared conditions: detail of the set)" if g["more_shared"] and g["id"] else ""))
        hl = [(sid, head)] + [(sid, "definition · " + d) for d in defs] + [x for s_ in own_shared for x in clines(s_["record"])]
        rows = []
        for r in g["rows"]:
            rec = r["record"]
            st = ", ".join(f"{x['name']} {x['text']}" for x in r["settings"])
            val = (rec.get("text") or "curve") + _unc(rec)
            if rec.get("curve") and rec["curve"].get("points"):
                val = f"curve against {rec['curve'].get('x') or 'x'}: " + ", ".join(f"({x}, {y})" for x, y in rec["curve"]["points"])
            rows.append([(rec.get("fact") or r["entity"], f"{r['name']}" + (f" · {st}" if st else "") + f" · {val} · {rec.get('kind')}{cmark(rec)}"
                          + (f" · {r['result_name']}" if len(names) > 1 or r["result_name"] != asked else "") + (f" · experiment [{r['entity']}]" if rec.get("fact") else ""))])
        foot = list(dict.fromkeys(x for r in g["rows"] for x in clines(r["record"])))                    # each caveat once, under its group
        foot += [(sid, "claims about this set: " + ", ".join(f"[{c}]" for c in g["claims"]))] if g["claims"] else []
        blocks.append(block(rows, head=hl, foot=foot, short=(sid, f"group {n} continued · {short_name(g['paper'])} · {g['label']}"), context=ctx))
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
        blocks.append(block([], head=[("between", last)]))
    return blocks


SEARCH_LINE = 200
BUDGET_TOKENS = 2000
BUDGET_CHARS = BUDGET_TOKENS * 4
DEF_FRAG = re.compile(r' · defined as: "[^"]*" \[([^\]]+)\]')


def block(rows, head=(), foot=(), short=None, context=()):
    """A part of an output: a header shown once, rows (each a list of lines kept together), a footer; short is the header repeated
    when a page starts inside it; context are lines repeated at the top of any later page that starts in it."""
    return dict(head=list(head), rows=[list(r) for r in rows], foot=list(foot), short=short, context=list(context))


def paginate(blocks, offset, max_lines=None):
    """The units (a header, a row, a footer) from offset, within BUDGET_CHARS and max_lines, then 'more: offset=N'. Within a page a
    line is never printed twice and a paper definition only at its first use (P44)."""
    units = []
    for b in blocks:
        for kind, u in [("head", b["head"])] + [("row", r) for r in b["rows"]] + [("foot", b["foot"])]:
            if not u:
                continue
            if sum(len(t) + len(i) + 4 for i, t in u) > BUDGET_CHARS - 400:          # a unit larger than a page goes line by line
                units += [(b, kind, [x]) for x in u]
            else:
                units.append((b, kind, u))
    offset = max(0, int(offset or 0))
    out, n, size = [], offset, 0
    if 0 < offset < len(units):
        b0 = units[offset][0]
        out += b0["context"] + ([b0["short"]] if units[offset][1] != "head" and b0["short"] else [])
        size += sum(len(t) + len(i) + 4 for i, t in out)
    while n < len(units):
        u = units[n][2]
        cost = sum(len(t) + len(i) + 4 for i, t in u)
        if (out and size + cost > BUDGET_CHARS - 60) or (max_lines and out and len(out) + len(u) > max_lines - 1):
            break
        out += u; size += cost; n += 1
    seen_lines, seen_defs, page = set(), set(), []
    for i, t in out:
        for m in DEF_FRAG.finditer(t):                                          # a paper definition once per page
            if m.group(1) in seen_defs:
                t = t.replace(m.group(0), "")
            seen_defs.add(m.group(1))
        if t not in seen_lines:                                                # a text once per page, whatever its id
            page.append((i, t)); seen_lines.add(t)
    if n < len(units):
        page.append(("more", f"more: offset={n}"))
    return page


def members_table(T, ms, cols=5):
    """A set's members as one table of the settings that vary among them (P44): process-defining first, keyed settings left out."""
    vt = {m: Q.vtext(T, m) for m in ms}
    keyed = {k for m in ms for k, fs in T.vector(m).items() if any(set(Q.quals(f)) & set(L.KEYED) for f in fs)}
    keys = [k for k in dict.fromkeys(k for m in ms for k in vt[m]) if k not in keyed and len({vt[m].get(k) for m in ms}) > 1]
    keys.sort(key=lambda k: (L.PRIMARY.index(k.split("{")[0]) if k.split("{")[0] in L.PRIMARY else len(L.PRIMARY), k))
    shown = keys[:cols]
    names = [Q.name_of(k, next(T.vector(m)[k][0] for m in ms if k in T.vector(m))) for k in shown]
    head = "members, by the settings that vary among them: member | " + " | ".join(names) + (f" (+{len(keys) - cols} more vary)" if len(keys) > cols else "")
    return head, [[(m, f"{T.label(m)} | " + " | ".join(vt[m].get(k) or "not stated" for k in shown))] for m in ms]


def _hidden(n, what="values"):
    return f"{n} computed-here {what} hidden: parts [\"computed\"] shows them"


def record_detail(T, f):
    """detail of a record that is not an experiment, input, set or cited work: a claim, a caveat, a definition, a process step, or one
    value or setting (P47)."""
    i, typ = f["fact_id"], Q.record_type(T, f)
    src = f" · source element: {T.key}:{f['evidence'].split(';')[0]}" if f.get("evidence") else ""
    if f["type"] == "claim":
        c = Q.claim_record(T, f)
        return [claim_line(c)] + clines(c) + [y for r in c.get("sized_by", []) for y in [(r["fact"], "size · " + value_line(r) + cmark(r))] + clines(r)]
    if f["type"] == "caveat":
        tg = Q.caveat_targets(T, f)
        return [(i, f"caveat · {f['statement']}{src}"), (i, f"qualifies {len(tg)} record{'s' if len(tg) != 1 else ''}: " + ", ".join(f"[{x}]" for x in tg[:40]) + (" …" if len(tg) > 40 else ""))]
    if f["type"] == "activity":
        own = [x for x in T.own(i) if x["type"] == "setting" and Q.text_of(x)]
        return [(i, f"{typ} ({f['kind']}): {f['statement']}" + (f" · under [{f['parent']}]" if f.get("parent") else ""))] + \
               [y for x in own for y in [(x["fact_id"], "setting · " + value_line(Q.record(T, x), Q.name_of(Q.ckey(x), x)) + cmark(Q.record(T, x)))] + clines(Q.record(T, x))]
    if (Q.text_of(f) or f["points_ref"]) and f["type"] in ("observation", "setting", "derived", "model", "cited"):
        e = T.ent_of(i); r = Q.record(T, f, ent=e)
        return [(i, f"{typ} · " + value_line(r, Q.name_of(Q.ckey(f), f), full=True) + cmark(r))] + clines(r) + \
               [(e or f["parent"], f"belongs to: {T.label(e)} [{e}]" if e else f"under: [{f['parent']}]")]
    q = f" · defines: {Q.name_of(Q.ckey(f), f)}" if f["type"] == "definition" and f["quantity"] else ""
    r = dict(caveats=Q.cav_list(Q.caveats_for(T, f, T.ent_of(i)))) if f["type"] in ("observation", "setting", "derived", "model", "cited") else {}
    return [(i, f"{typ}: {f['statement']}{q}{src}{cmark(r)}")] + clines(r) + ([(f["parent"], f"under: [{f['parent']}]")] if f.get("parent") else [])


def _run(name, args):
    """(blocks, error) of one call."""
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
                if b["short"]:
                    b["short"] = W([b["short"]])[0]
                b["context"] = W(b["context"])
            return blocks, ""
        if name == "search":
            if not Q.tokens(args["words"]):
                return [], "error: search: words has no letters or numbers"
            hits, items, seen = Q.search(args["words"], args.get("paper")), [], {}
            for h in hits:            # values and settings: one line per paper and quantity; other records: a line shown once with its count
                if h["type"] in ("value", "setting"):
                    T = Q.TREES[h["paper"]]; f = T.byid[h["id"]]
                    key = (h["paper"], h["type"], Q.name_of(Q.ckey(f), f))
                    g = seen.setdefault(key, [h, 0, [], {}])
                    g[1] += 1
                    if Q.text_of(f) not in g[2]:
                        g[2].append(Q.text_of(f))
                    g[3].update({c["id"]: c for c in Q.record(T, f)["caveats"]})            # the caveats of any value in the line
                    continue
                g = seen.setdefault((h["type"], h["line"]), [h, 0, None, {}])
                g[1] += 1
                f = Q.TREES[h["paper"]].byid[h["id"]]
                if "#" in h["id"] and f["type"] in ("observation", "setting", "derived", "model", "cited"):             # a note's caveats
                    g[3].update({c["id"]: c for c in Q.cav_list(Q.caveats_for(Q.TREES[h["paper"]], f, Q.TREES[h["paper"]].ent_of(h["id"])))})
            for key, (h, n, vals, cav) in seen.items():
                if vals is not None:
                    shown = ", ".join(vals[:8]) + (f", … ({len(vals)} distinct)" if len(vals) > 8 else "")
                    line = f"{h['type']}s of {key[2]} in {short_name(key[0])}: {n} record{'s' if n > 1 else ''}, {shown}"
                else:
                    line = f"{h['type']} · {h['line']}" + (f" · {n} records with this line" if n > 1 else "")
                if len(line) > SEARCH_LINE:
                    line = line[:SEARCH_LINE - 2].rsplit(" ", 1)[0] + " …"
                rec = dict(caveats=list(cav.values()))
                items.append([x for y in [(h["id"], line + cmark(rec))] + clines(rec) for x in wrap(*y)])
            return [block(items)], ""
        if name == "detail":
            parts = [p for p in (args.get("parts") or DETAIL_DEFAULT) if p in DETAIL_PARTS] or DETAIL_DEFAULT
            T0 = Q.tree_of(args["id"]); n0 = T0.byid[args["id"]]
            if n0["type"] not in ("entity", "comparison", "cited") or "#" in args["id"]:
                return [block([wrap(*x) for x in record_detail(T0, n0)])], ""
            d = Q.detail(args["id"])
            i = d["id"]
            out = []
            if d["type"] == "entity":
                w = d["what"]
                if "what" in parts:
                    out.append((i, f"{short_name(d['paper'])} · {d['name']}" + (" (inferred: not named by the paper)" if d["inferred"] else "")
                                + f" · role: {d['role']}" + (f" · material: {w['material']}" if w.get("material") else "") + (f" · reactants: {' / '.join(w['reactants'])}" if w.get("reactants") else "")
                                + (f" · substrate: {w['substrate']}" if w.get("substrate") else "")
                                + (f" · made from: {', '.join(f'{n} [{x}]' for n, x in zip(w['inputs'], w['input_ids']))}" if w.get("inputs") else "")
                                + (f" · part of: [{w['parent']}]" if w.get("parent") else "") + (f" · statement: {d['statement']}" if d.get("statement") else "")))
                    meth = list(dict.fromkeys(r["record"]["method"].replace("_", " ") + (f" ({_mode(r['record'].get('mode'))})" if _mode(r["record"].get("mode")) else "")
                                              for r in d["results"] if r["record"].get("method") and r["record"]["method"] != "calculation"))
                    if meth:
                        out.append((i, "its results were measured by: " + "; ".join(meth)))
                    out += [(c["id"], f"comparison it belongs to: {c['label']}") for c in d["comparisons"]]
                    out += [(i, f"identity ({x['kind']}): {x['statement']} · others: {', '.join(x['others'])}") for x in d["identity"]]
                    out += [(c["id"], f"caveat on this experiment: {c['text']}") for c in d.get("caveats", [])]
                if "differs" in parts and d["differs"]:
                    out.append((i, "distinguished by: " + "; ".join(f"{x['name']} {x['text']}" for x in d["differs"])))
                comp = [r for r in d["results"] if r["record"].get("kind") == "computed here"]
                own = [r for r in d["results"] if r["record"].get("kind") != "computed here"]
                show = "computed" in parts or not own                                     # computed here only when asked or nothing else exists
                if "results" in parts:
                    out += [y for r in own for y in [(r["record"].get("fact") or i, "result · " + value_line(r["record"], r["name"]) + defined_as(d["paper"], r["key"]) + cmark(r["record"]))] + clines(r["record"])]
                    if comp and not show:
                        out.append((i, _hidden(len(comp))))
                if show:
                    out += [y for r in comp for y in [(i, "result · " + value_line(r["record"], r["name"]) + defined_as(d["paper"], r["key"]) + cmark(r["record"]))] + clines(r["record"])]
                if "recipe" in parts:
                    out += [y for c in d["recipe"] for y in [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"]) + cmark(c["record"]))] + clines(c["record"])]
            elif d["type"] == "comparison":
                T = Q.tree_of(i)
                if "what" in parts:
                    out.append((i, f"comparison ({short_name(d['paper'])}): {d['label']} · kind: {d['kind']} · varies: {', '.join(d['varies']) or 'nothing stated'}"
                                + (f" · statement: {d['statement']}" if d.get("statement") else "") + (f" · purpose: {d['purpose']}" if d.get("purpose") else "")))
                if "differs" in parts or "what" in parts:
                    head, rows = members_table(T, d["members"])
                    out.append((i, head)); out += [x for r in rows for x in r]
                if "results" in parts:
                    out += [y for v in d["values"] for y in [(v.get("fact") or i, "stated for the set · " + value_line(v) + cmark(v))] + clines(v)]
                    if (d["effects"] or d["fits"]) and "computed" not in parts:
                        out.append((i, _hidden(len(d["effects"]) + len(d["fits"]), "effect and fit lines")))
                if "computed" in parts:
                    out += [(i, effect_line(e)) for e in d["effects"]]
                    for f_ in d["fits"]:
                        out.append((i, f"fit (kind: computed here): {f_['name']} ∝ {f_['x']}^{f_['exponent']} (residual {f_['residual']}, {f_['n']} points)"
                                    + "".join(f" · correction (kind: computed here) for {c['condition']} to {c['to']}: exponent {c['exponent']} (residual {c['residual']}); "
                                              + "; ".join(f"{name_of_id(x['id'])} {x['frm']} × {x['factor']} = {x['value']} from {x['by']}" for x in c["changes"]) for c in f_["corrected"])))
            else:
                if "what" in parts:
                    out.append((i, f"cited work ({short_name(d['paper'])}): {d['name']} · statement: {d['statement']}"))
                if "recipe" in parts:
                    out += [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"])) for c in d["recipe"]]
                if "results" in parts:
                    out += [(r["record"].get("fact") or i, "value · " + value_line(r["record"], r["name"])) for r in d["results"]]
            if "claims" in parts:
                out += [y for c in d.get("claims", []) for y in [claim_line(c)] + clines(c)]
            return [block([wrap(*x) for x in out])], ""
        if name == "source":
            s = Q.source(args["id"])
            eid = f"{s['paper']}:{s['element']}"
            out = [(eid, f"element {eid} ({s['kind']}, {s['locator']})" + (f" · covered: {s['coverage']}" if s.get("coverage") else "") + (f" · text: {s['text']}" if s.get("text") else " · no text (a figure panel)"))]
            out += [y for v in s["values"] for y in [(v.get("fact") or eid, value_line(v, full=True) + cmark(v))] + clines(v)]
            T_ = Q.TREES[s["paper"]]
            for f in [f for f in T_.rows if "#" in f["fact_id"] and s["element"] in f["evidence"].split(";") and not Q.text_of(f) and f["type"] != "claim"]:
                r = dict(caveats=Q.cav_list(Q.caveats_for(T_, f, T_.ent_of(f["fact_id"])))) if f["type"] in ("observation", "setting", "derived", "model", "cited") else {}
                out += [(f["fact_id"], f"statement without a value: {f['statement']}{cmark(r)}")] + clines(r)
            return [block([wrap(*x) for x in out])], ""
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
