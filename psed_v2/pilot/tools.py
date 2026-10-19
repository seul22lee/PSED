#!/usr/bin/env python3
"""The Knowledge base arm's access layer: the tool schemas and descriptions, and run_tool, which answers a tool call from query.py
as plain text, one line per returned value or row, starting with its id in square brackets (format and paging only; the tool
layer computes nothing). Also the page targets of ids (open_target). Used by ask.py; no model call here."""
import collections, csv, difflib, json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import query as Q  # noqa: E402
import concept as CN  # noqa: E402


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


# ---------------------------------------------------------------------------------------------------------------- the renderer (P68)
# Every provenance word, basis phrase and caveat any of the five tools prints comes through these functions, from the ontology's
# closed tables: a kind as its phrase (vocab.PHRASES; in a values cell a mark (kN) that the output's legend binds to the phrase), a
# ± with its basis (vocab.BASES: the phrase after the number, or in a cell the basis id that the legend binds to the phrase; one
# wording when the paper gives none), a caveat as '[id]' on every line that carries it and its text once per output ('caveat · <text>'
# at its first use; values collects the texts at the end). check.py scans a probe battery of tool outputs for any wording outside
# the tables.
KIND_MARK = {k: f"k{n}" for n, k in enumerate([k for k in L.KINDS if k in L.KIND_WORDS], 1)}     # a mark per marked kind; measured and stated unmarked (P57)


def kind_phrase(k):
    """The provenance words of a kind: only the ontology's phrase table (P57); a kind outside it is an error, never printed raw."""
    return L.PHRASES[k]


def kind_text(k):
    return f"kind: {kind_phrase(k)}"


def kinds_text(ks):
    """The kinds of several values on one line: 'kind: <phrase>' or 'kinds: <phrase>; <phrase>' in the table's order."""
    ks = [k for k in L.KINDS if k in set(ks)]
    return ("kind: " if len(ks) == 1 else "kinds: ") + "; ".join(kind_phrase(k) for k in ks)


def unc_text(u, compact=False):
    """A ± with its basis (P48, P60): ' ± v (<basis phrase>; <what the number is>)' through query.unc_note; compact, for a cell of
    values, ' ± v (<basis id>)' with the legend binding the id to its phrase, or '(basis not stated)' when the paper gives none."""
    if not u:
        return ""
    if isinstance(u, str):
        return " " + u
    fid = f" [{u['fact']}]" if u.get("fact") else ""                            # a spread stated as its own fact (P1): cited by id (P79)
    if compact:
        return f" ± {u.get('value')} ({u.get('basis') if u.get('basis') in L.BASES else 'basis not stated'})" + fid
    return f" ± {u.get('value')}" + Q.unc_note(u) + fid


def cmark(rec):
    """The caveat ids on a line that carries a caveat (P45): ' · caveat [id]'."""
    cs = (rec or {}).get("caveats") or []
    return (" · caveat " if len(cs) == 1 else " · caveats ") + ", ".join(f"[{c['id']}]" for c in cs) if cs else ""


def clines(rec):
    """The caveat texts of a value: (id, 'caveat · text') after the line that first carries it; paginate keeps a text once per output."""
    return [(c["id"], f"caveat · {c['text']}") for c in (rec or {}).get("caveats") or []]


KIND_LIST = "; ".join(kind_phrase(k) for k in L.KINDS)                          # the phrase table (P57): the only provenance words
KB = kind_phrase("computed_by_kb")
PAGE_LINES = 25
MAX_LINE = 300
DETAIL_PARTS = ["what", "differs", "results", "recipe", "claims", "computed", "table"]
DETAIL_DEFAULT = ["what", "differs", "results"]

TOOLS = [
    dict(name="concept",
         description=("Arguments: words (required). Resolves the words against the knowledge base's concepts by the ontology's rules (entry names "
                      "and aliases, families, species, mechanisms, categorical values; an ambiguous word lists its candidates) and returns one "
                      "line per matched concept: id · definition · unit · family and sibling ids · qualifier keys · per-paper counts of values, "
                      "claims and settings · 'not studied in: <papers>' · an attribute flag where set · up to five edges. A phrase with a qualifier "
                      "('thickness in the channel', 'phase (metallic Mo)', 'H2O exposure') resolves to the quantity with that qualifier's counts first; "
                      "words naming nothing return the three nearest ids (no error). About 2,000 tokens per call. Use it first, "
                      "to learn what exists, where and under which id, before values, detail or search."),
         parameters=dict(type="object", properties=dict(words=dict(type="string", description="A concept in words: a quantity, a species, a mechanism, a family.")),
                         required=["words"])),
    dict(name="search",
         description=("Arguments: words (required), paper, offset. Without paper: the matching concepts, then one line per paper for the six "
                      "best-scoring papers: paper key · its best hit · the count of further hits · the comparison sets of that paper that hold "
                      "the quantity the words name; search(words, paper=…) then opens one paper: its records whose text matches the words, best "
                      "first, one line each: '[id] record type · line' (lexical: lowercase, plurals folded, _ and - as spaces, numbers and units kept; no "
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
         description=("Arguments: result or set (one of the two), paper, where; or paper alone. With paper alone: the paper's quantity index, one line per quantity it holds values for "
                      "(label, id, value counts by home, range with unit, the set ids that hold it, claims), the figure panels and model inputs as counts; never a value with its id. "
                      "With result as a list of up to 8 names: the single-quantity outputs as consecutive blocks, each under its own columns header, legends and footer once, within k times the per-call budget (at most 8,000 tokens); over it whole blocks fold from the last into one line naming how to open them (P121). With set (a comparison set id): one table of everything the set measured, "
                      "rows = every member of the set (every cell of a grid) and first the set itself for the values stated for it, columns = every "
                      "result quantity with a value among them in the ontology's order, cells = value, kind mark, fact id, ± with its basis; over the "
                      "budget the last columns collapse into one line naming them, rows are never dropped. With result: returns every value of one result or stated setting as comparison-set "
                      "summaries, never a representative: per set one header line (set id · what it varies · the conditions its members share · "
                      "n rows · the columns), then one row per specimen with the result's values side by side across its qualifier variants "
                      "(inside and outside a channel on one row), each value with its kind (" + KIND_LIST + "), its ± with the basis of the "
                      "uncertainty, its fact id and the id of any caveat. Sets whose comparability axes differ are separated by a 'not comparable: "
                      "<axes>' divider; sets whose uncertainty bases differ are flagged. Values computed by this knowledge base are counted, not "
                      "listed (detail with parts computed shows them). Conditions every set of a paper shares, and the usual ones, are printed once "
                      "above its sets; the caveats on every row once at the end. When the full listing would exceed about 2,000 tokens the "
                      "output gives way in steps: model-run sets collapse to their range and count, then the caveat texts go (their ids stay "
                      "on the rows), then specimen sets collapse, the largest first; a line says how many sets collapsed and that detail(ids) "
                      "opens them. Narrow with paper or where to see more rows. A paper that holds no value of the result but claims, curves, figure panels "
                      "or definitions of it answers with one line of those counts. A setting (a process parameter, a reactor or a test-structure "
                      "setting: temperature, pulse, purge, flow, pressure, cycles, feature width, substrate, ...) comes as a settings table per paper "
                      "instead: one row per distinct level or combination of coupled levels, with the fact ids and the count and set ids of the "
                      "specimens that use it; values of it computed by this knowledge base are named in one line, never listed. The last line says "
                      "where else the concept lives. Use it to see how one result or setting varies across experiments and conditions. "
                      "The knowledge base's names, generated from its data: " + VOCAB),
         parameters=dict(type="object", properties=dict(
             result=dict(description="A result or setting name from the list in this description, a quantity id or a qualifier phrase; or a list of up to 8 of them (P121: one call, one block per quantity)."),
             set=dict(type="string", description="A comparison set id (<paper>:cmp:<name>, as values, detail or the map return it): the set-wide table instead of result; takes no paper or where."),
             paper=dict(type="string", enum=PAPER_KEYS, description=f"Only this paper: {PAPER_WORDS}."),
             where=dict(type="object", description="Only experiments whose stated settings match: {setting name: a value (number or text), or [min, max] (either may be null)}; numbers in the setting's unit as the values lines show it.",
                        additionalProperties={})),
             required=[])),
    dict(name="papers",
         description=("Arguments: material, structure, process, quantity, offset (all optional). Returns one line per paper of the knowledge base: key · "
                      "material · process (reactant A / reactant B) · structure class · experiment and claim counts · main outcome quantities with "
                      "their value counts · panels and curves. Filters: material (a species id, formula or name), structure (a structure class or id), "
                      "process (words of a reactant, or a mode: thermal, plasma, ozone), quantity (an id or name: only papers with values, claims or settings of it). At most 20 lines "
                      "per call, then 'more: offset=N'. Use it after the map to see which papers to open."),
         parameters=dict(type="object", properties=dict(
             material=dict(type="string", description="A material: a species id (al2o3), its formula or its printed name (Al2O3)."),
             structure=dict(type="string", description="A structure class (lateral_channel, planar, porous_body, trench, …) or a structure id."),
             process=dict(type="string", description="Words of a reactant (TMA, H2O) or a process mode: thermal, plasma, ozone."),
             quantity=dict(type="string", description="A quantity id or name; only papers that hold values, claims or settings of it."),
             offset=dict(type="integer", description="Skip this many lines (default 0).")),
             required=[])),
    dict(name="detail",
         description=("Arguments: ids (required, up to 8), parts, offset. Returns what the knowledge base holds about each id, under one budget. An experiment or input: "
                      "what (role, material, substrate, inputs, the methods its results were measured by, its comparison sets, identity "
                      "statements, its caveats), differs (the conditions that set it apart in its set), results (value, unit, kind, "
                      "definition, method, in situ or ex situ, uncertainty, source element, caveats), recipe (every condition), claims, "
                      "computed (values " + KB + ", with formula, inputs and assumed facts). A comparison set: what, its members as one "
                      "table of the settings that vary, results (values stated for the set), claims, computed (each effect with its "
                      "minimum and maximum members and the scatter between repeats, and power-law fits). A claim: the statement, stance, "
                      "cause and effect, its scope (" + KB + "), the results it rests on, the facts that give its size, its caveats. A "
                      "cited work: what, recipe, results, claims. Any other id (a value, setting, definition, caveat, note, process step): "
                      "the record, what it belongs to, its source element and caveats; a caveat also lists what it qualifies. A location id "
                      "(a paragraph <paper>:sN.pM, a table cell <paper>:tabN.rXcY, a figure panel <paper>:figNx or a figure <paper>:figN) returns the "
                      "records located there: facts, values, curves, cells, peaks and the panel's inventory line, in page order. parts "
                      "(default what, differs, results) applies to experiments, inputs, sets and cited works. About 2,000 tokens per call, "
                      "then 'more: offset=N'. Use it for more about one id that search or values returned."),
         parameters=dict(type="object", properties=dict(
             ids=dict(type="array", items=dict(type="string"), minItems=1, maxItems=8, description="One to eight ids as search, values or detail returned them; one output budget for all of them, nothing printed twice."),
             parts=dict(type="array", items=dict(type="string", enum=DETAIL_PARTS), description="Any of what, differs, results, recipe, claims, computed, table (default what, differs, results); table, for a comparison set, is the set-wide table values(set=...) gives."),
             offset=dict(type="integer", description="Skip this many output units (default 0).")),
             required=["ids"])),
    dict(name="curve",
         description=("Arguments: id (required). Returns one curve read from a figure by the figure stage and imported by rule: its axes "
                      "(quantity, canonical unit, the label as printed), its series label and the conditions it was obtained under, its kind "
                      "(read from a figure, or simulated by the paper's authors), its comparison set, the values this knowledge base derived "
                      "from it (plateau, half-value crossing, slope), its flags, and its points (x, y) in canonical units, at most 40, evenly "
                      "thinned when the curve has more. About 2,000 tokens per call. Use it after values or detail returned a curve id "
                      "(<paper>:fig<N><panel>#c<n>) to read the points themselves."),
         parameters=dict(type="object", properties=dict(id=dict(type="string", description="A curve id as values, detail or search returned it.")),
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
    source element, the ids of other candidates; for a value computed by this knowledge base its formula, inputs and assumed facts; with full, the
    fact's statement and the measurement settings."""
    if not r:
        return name + ": no value"
    bits = [f"{name}: {r.get('text', '')}" if name else r.get("text", "")]
    if r.get("curve") and r["curve"].get("points"):
        bits.append(f"curve against {r['curve'].get('x') or 'x'}, points (x, y): " + ", ".join(f"({x}, {y})" for x, y in r["curve"]["points"]))
    bits.append(kind_text(r.get("kind", "")))
    if r.get("definition"):
        bits.append(("formula: " if r.get("kind") == "computed_by_kb" else "definition: ") + r["definition"])
    if r.get("method") and r.get("method") != "calculation":
        bits.append("method: " + r["method"] + (f", {_mode(r.get('mode'))}" if _mode(r.get("mode")) else ""))
    if r.get("uncertainty"):
        bits.append("uncertainty:" + unc_text(r["uncertainty"]))
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
            + (f" · relation: {c['relation']}" if c.get("relation") else "") + (f" · effect: {', '.join(c['effect'])}" if c.get("effect") else "") + (f" · scope (kind: {KB}): {c['scope']}" if c.get("scope") else "")
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
        if "maxItems" in sch and len(v) > sch["maxItems"]:
            return f"{where}: at most {sch['maxItems']} items, got {len(v)}"
        if "minItems" in sch and len(v) < sch["minItems"]:
            return f"{where}: at least {sch['minItems']} item"
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
    import concept as CN
    return r in _names() or r in QUANT or bool(Q.concept_ids(r)) or bool(CN.resolve_phrase(r)["ids"])   # P105/P111: a qualifier or species phrase resolves


def nearest_results(r):
    """P105: the three result or setting names, quantity ids or concept ids nearest to r by word overlap, then by spelling."""
    import concept as CN
    qw = set(CN.words_of(r))
    pool = sorted(_names()) + sorted(QUANT)
    scored = sorted(((-len(qw & set(CN.words_of(n))), len(n), n) for n in pool if qw & set(CN.words_of(n))))
    near = [n for _, _, n in scored[:3]]
    if not near:
        near = CN.resolve_phrase(r)["nearest"][:3] or difflib.get_close_matches(r, pool, n=3, cutoff=0.0)
    return near


def nearest_papers(p):
    """P105: the three paper keys nearest to p (keys and short names)."""
    names = {k: k for k in Q.TREES} | {short_name(k).lower(): k for k in Q.TREES}
    near = list(dict.fromkeys(names[x] for x in difflib.get_close_matches(str(p).lower(), list(names), n=6, cutoff=0.3)))[:3]
    return near or list(Q.TREES)[:3]


def _where_err(where):
    for k, x in where.items():
        if k not in _names("setting") and k not in QUANT:
            near = difflib.get_close_matches(k, sorted(_names("setting")), n=5, cutoff=0.4)
            return f"where: unknown setting {k!r}" + (f"; nearest: {', '.join(near)}" if near else "") + "; setting names are listed in the description"
        ok = isinstance(x, (str, int, float)) and not isinstance(x, bool) or (isinstance(x, list) and len(x) == 2 and all(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)) for v in x))
        if not ok:
            return f"where.{k}: give a number, a text, or [min, max] (numbers or null)"
    return ""


def _comparison(i):
    """Whether an id names a comparison set."""
    T = Q.TREES.get(str(i).split(":")[0])
    return bool(T and i in T.byid and T.byid[i]["type"] == "comparison")


def _record(i):
    """Whether an id names a record of the knowledge base (any row but a paper's), a location (P92) or a concept, model, mechanism,
    species, structure or family id (P110)."""
    if i in L.ENTRIES or (i.startswith("family:") and i[7:] in L.FAMILIES) or i in Q.TREES:   # P110, P117 (a paper key: its index)
        return True
    T = Q.TREES.get(i.split(":")[0])
    return bool(T and i in T.byid and T.byid[i]["type"] != "paper") or Q.located(i) is not None


def _curve(i):
    """Whether an id names an imported curve."""
    T = Q.TREES.get(str(i).split(":")[0])
    return bool(T and i in T.curves)


IDS = {("curve", "id"): (_curve, "no curve of the knowledge base has this id (curve ids read <paper>:fig<N><panel>#c<n>)"),
       ("detail", "ids"): (_record, "no record of the knowledge base has this id"),
       ("source", "id"): (_source, "no fact or paper element has this id")}


def validate(name, args):
    """An error text for a call the tool cannot answer as asked, else "" (P39): an unknown tool or argument, a wrong type, a value
    outside the vocabulary, an id that names nothing. An argument given as null counts as not given."""
    if name not in SCHEMA:
        return f"unknown tool {name}; tools: {', '.join(SCHEMA)}"
    if not isinstance(args, dict):
        return f"{name}: the arguments must be an object"
    e = _check("", {k: v for k, v in args.items() if not (k == "paper" and name in ("search", "values") and isinstance(v, str))}, SCHEMA[name])   # P105: an unknown paper name suggests, never errors
    if e:
        return f"{name}: {e.lstrip('.')}" if not e.startswith(":") else f"{name}{e}"
    if name == "values":                                                        # P77: result or set, one of the two; P117: paper alone = the paper's quantity index
        if args.get("result") is None and args.get("set") is None and args.get("paper") is None:
            return "values: missing result, set or paper"
        r = args.get("result")
        if r is not None and not (isinstance(r, str) or (isinstance(r, list) and r and len(r) <= 8 and all(isinstance(x, str) and x.strip() for x in r))):
            return "values: result must be a name, id or qualifier phrase, or a list of 1 to 8 of them (P121)"
        if args.get("result") is not None and args.get("set") is not None:
            return "values: give result or set, not both"
        if args.get("set") is not None:
            if not _comparison(args["set"]):
                near = difflib.get_close_matches(args["set"], [c["fact_id"] for T in Q.TREES.values() for c in T.comps], n=5, cutoff=0.4)
                return f"values: set {args['set']!r}: no comparison set has this id" + (f"; nearest: {', '.join(near)}" if near else "")
            if args.get("paper") is not None or args.get("where") is not None:
                return "values: set takes no paper or where"
    if name == "values" and isinstance(args.get("where"), dict):
        e = _where_err(args["where"])
        if e:
            return f"values: {e}"
    for (tool, arg), (ok, why) in IDS.items():                                   # P105: an unknown result name is no error (values suggests the nearest three)
        if tool == name and args.get(arg) is not None:
            for v in (args[arg] if isinstance(args[arg], list) else [args[arg]]):
                if not ok(v):
                    return f"{name}: {arg} {v!r}: {why}"
    return ""


def run_tool(name, args):
    """(lines, error): lines = [(id, text)] formatted from what query.py returns; the tool layer computes nothing; no line over MAX_LINE; at
    most BUDGET_TOKENS (chars/4) per call, then 'more: offset=N' (P44). A call that fails validation, or whose filters match
    nothing, returns an error text, never an unfiltered or empty result."""
    err = validate(name, args)
    if err:
        return [], "error: " + err
    args = {k: v for k, v in args.items() if v is not None}
    k_list = len(args["result"]) if name == "values" and isinstance(args.get("result"), list) else 1
    _CALL_BUDGET.append(BUDGET_CHARS * min(k_list, LIST_BUDGET_MAX))            # P121b: k listed quantities, k × the per-call budget (at most 4×)
    try:
        blocks, err = _run(name, args)
        lines = [] if err else paginate(blocks, args.get("offset"), PAGE_LINES if name == "search" else 20 if name == "papers" else None)
    finally:
        _CALL_BUDGET.pop()
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
    """An effect of a comparison on one result: its range with both endpoints, and the judgement against noise (computed by this knowledge base)."""
    unit = f" {e['unit']}" if e.get("unit") else ""
    return (f"effect on {e['name']}{' (main result)' if e.get('main') else ''} (kind: {KB}): range {e['effect']}{unit} over {e['n']}: "
            + endpoints(e) + f" · {e['sentence']}")


def _pairs(ps):
    """Group pairs (a, b) as 'groups 1–9' with b: [(span of the a's, b)]."""
    by = {}
    for a, b in ps:
        by.setdefault(b, []).append(a)
    return [(_span(a_s) if len(a_s) > 1 else str(a_s[0]), b) for b, a_s in by.items()]


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


def _cell(rec, marks, fact=True):
    """One value as a cell: text, the kind's mark (the legend gives its phrase; measured and stated unmarked, P57), ± with its basis id
    (the basis legend gives the phrase), the fact id; the caveat ids go on the row, once (values_blocks). The one cell wording of
    every table the tools print (P68): values, the settings tables (P76) and the set-wide tables (P77)."""
    unc = unc_text(rec.get("uncertainty"), compact=True)
    k = rec.get("kind", "")
    mark = ""
    if k in KIND_MARK:
        marks.add(k); mark = f" ({KIND_MARK[k]})"
    return f"{rec.get('text') or 'curve'}{mark}{unc}" + (f" [{rec['fact']}]" if fact and rec.get("fact") else "")


def _cells(rec, marks, fact=True):
    """Every record of one key on one row as one cell (P42, P79): the chosen record first, then the other candidates (a value read from
    a figure beside the table's, a component beside the main one), each as _cell prints it, joined by '; '."""
    return "; ".join(_cell(r, marks, fact) for r in [rec] + list(rec.get("alternatives") or []))


HOME_KINDS = {"inputs": "inputs", "aggregate": "set-level", "paper": "paper-level", "cited": "cited works"}   # the P79 homes rendered as groups before the comparison sets


def grid_lines(g, names, keys, marks, legend_cav, legend_basis, collapse=0):
    """P80: a grid set as matrices, one per result key: rows = the levels of the first axis, columns = the levels of the second, a cell =
    every record of the key on that cell (_cells), '—' for a tested cell with no value of it, 'n.t.' for an untested combination; a row or
    column level with no value of the key is left out and its tested cells counted in the key's line (shown + left out = every cell);
    caveats on every cell once above the matrices, the others after their cell. Then the variants (the same-process experiments at a
    cell's levels: one line per cell with their records), the child series (views, not printed again) and the set-level records of those
    children. collapse = how many kept row levels, from the last, fold into one 'range · n cells' line per key (over the budget; a
    column is never dropped). Returns [(id, text)]."""
    gi, sid = g["grid"], g["id"]
    by_ent = {}
    for r in g["rows"]:
        by_ent.setdefault(r["entity"], {})[r["key"]] = r
    vs = set(gi["variants"])
    cells = {gi["level_of"][e]: e for e in gi["cells"] if e in gi["level_of"]}
    tested = set(cells)
    rows_, cols = gi["rows"], gi["cols"]
    two = len(gi["axes"]) > 1
    lv_of = lambda rl, cl: (rl, cl) if two else (rl,)
    cell_cav = [{c["id"] for rr in [by_ent[e][kk]["record"]] + list(by_ent[e][kk]["record"].get("alternatives") or []) for c in rr.get("caveats") or []}
                for e in cells.values() for kk in keys if kk in by_ent.get(e, {})]
    common = set.intersection(*cell_cav) if cell_cav else set()                 # caveats on every cell: once, above the matrices
    out = [(sid, f"matrix: rows {gi['axes'][0][1]} ({len(rows_)} levels) × columns {gi['axes'][1][1] if two else 'one column'} ({len(cols)} levels) · {len(gi['cells'])} cells, "
                 f"{len(rows_) * len(cols) - len(tested)} combinations n.t. · '—' = no value in a tested cell · a level with no value is left out, its cells counted")]
    if common:
        out.append((sid, "caveats on every cell: " + ", ".join(f"[{c}]" for c in sorted(common))))
    empty = []
    for kk in keys:
        has = {lv for lv, e in cells.items() if kk in by_ent.get(e, {})}
        if not has:                                                             # no cell holds the quantity: it lives on variants or set-level records only
            empty.append(names[kk]); continue
        krows = [rl for rl in rows_ if any(lv[0] == rl for lv in has)]
        kcols = [cl for cl in cols if any(lv[1] == cl for lv in has)] if two else [""]
        keep = krows[:len(krows) - collapse] if collapse else krows
        shown = sum(1 for lv in tested if lv[0] in krows and (not two or lv[1] in kcols))
        out.append((sid, f"{names[kk]} · {shown} of {len(gi['cells'])} cells shown ({len(gi['cells']) - shown} in rows or columns left out)" + (" · columns: " + " | ".join(kcols) if two else "")))
        for rl in keep:
            cs = []
            for cl in kcols:
                lv = lv_of(rl, cl)
                if lv not in tested:
                    cs.append("n.t."); continue
                r = by_ent.get(cells[lv], {}).get(kk)
                if not r:
                    cs.append("—"); continue
                rec = r["record"]
                cav = sorted({c["id"] for rr in [rec] + list(rec.get("alternatives") or []) for c in rr.get("caveats") or []} - common)
                for rr in [rec] + list(rec.get("alternatives") or []):
                    legend_cav.update({c["id"]: c["text"] for c in rr.get("caveats") or []})
                    if (rr.get("uncertainty") or {}).get("basis") in L.BASES:
                        legend_basis.add(rr["uncertainty"]["basis"])
                cs.append(_cells(rec, marks) + (" · caveats " + ", ".join(f"[{c}]" for c in cav) if cav else ""))
            out.append((sid, f"{rl} · " + " | ".join(cs)))
        if collapse and len(krows) > len(keep):
            gone = krows[len(keep):]
            vals = [(by_ent[e][kk]["record"].get("value"), by_ent[e][kk]["record"].get("unit", "")) for lv, e in cells.items() if lv[0] in gone and kk in by_ent.get(e, {})]
            nums = [v for v, _ in vals if v is not None]
            out.append((sid, f"rows {', '.join(gone)} collapsed to stay within the budget: {names[kk]} " + (f"range {Q.g(min(nums), 3)}–{Q.g(max(nums), 3)} {vals[0][1]}".strip() + f" over {len(nums)} values" if nums else "no numeric value")
                        + f" in {sum(1 for lv in has if lv[0] in gone)} cells · open with values(set={sid!r}) or detail(ids=[cell ids])"))
    if empty:
        out.append((sid, "no cell holds: " + ", ".join(empty) + " (variants or set-level records only)"))
    for lv, e in sorted(cells.items(), key=lambda x: tuple(Q._num_prefix(t) for t in x[0])):
        vv = [v for v in gi["variants"] if gi["level_of"].get(v) == lv and v in by_ent and any(kk in by_ent[v] for kk in keys)]
        if vv:
            parts = []
            for v in vv:
                recs = "; ".join(f"{names[kk]} {_cells(by_ent[v][kk]['record'], marks)}" for kk in keys if kk in by_ent[v])
                for kk in keys:
                    if kk in by_ent[v]:
                        for rr in [by_ent[v][kk]["record"]] + list(by_ent[v][kk]["record"].get("alternatives") or []):
                            legend_cav.update({c["id"]: c["text"] for c in rr.get("caveats") or []})
                parts.append(f"{Q.TREES[g['paper']].label(v)} [{v}]: {recs}")
            out.append((sid, f"variants of the cell {', '.join(lv)} (+{len(vv)}): " + " · ".join(parts)))
    if gi["children"]:
        out.append((sid, "child series (views of this grid, not printed again; values(set=<id>) opens one): " + ", ".join(f"[{cid}]" for cid, _ in gi["children"])))
    for cid, own in gi["child_own"].items():
        by_key = {}
        for kk, name, rec in own:
            by_key.setdefault((kk, name), []).append(rec)
            legend_cav.update({c["id"]: c["text"] for c in rec.get("caveats") or []})
        out.append((cid, f"set-level records of the child series [{cid}]: " + " | ".join(f"{name} " + "; ".join(_cell(r, marks) for r in recs) for (kk, name), recs in by_key.items())))
    return out


def _usual_names(groups, paper, usual):
    """(key, name) of the usual conditions of a paper (values_blocks)."""
    return {(x["key"], x["name"]) for g in groups if g["paper"] == paper for x in g["shared"] if (x["key"], x["record"]["text"]) in usual}


def _common_usual(groups):
    """Per paper (P44, P65): the conditions every specimen set shares (common) and the usual ones (shared by most sets; no key with two
    usual values), as sets of (key, text), for the paper's shared-conditions header."""
    common, usual = {}, {}
    for k in dict.fromkeys(g["paper"] for g in groups):
        gs = [g for g in groups if g["paper"] == k and g.get("roles", ["specimen"]) == ["specimen"]]
        sets = [{(x["key"], x["record"]["text"]) for x in g["shared"]} for g in gs]
        common[k] = set.intersection(*sets) if len(gs) > 1 else set()
        cnt = collections.Counter(c for s in sets for c in s)
        usual[k] = {c for c, n in cnt.items() if n * 2 > len(gs) and c not in common[k]} if len(gs) > 2 else set()
        if len({x[0] for x in usual[k]}) < len(usual[k]):                       # two values of one key both usual: lift neither
            usual[k] = set()
    return common, usual


def _shared_head(groups, k, common, usual):
    """The paper's shared-conditions line (id <paper>:shared): what every specimen set shares and the usual conditions; None when the
    paper has neither."""
    if not (common.get(k) or usual.get(k)):
        return None
    every = [g2 for g2 in groups if g2["paper"] == k]
    txt = {(x["key"], x["record"]["text"]): f"{x['name']} {x['record']['text']}" for g2 in every for x in g2["shared"]}
    return (f"{k}:shared", f"{short_name(k)}" + (" · every specimen set of this paper shares: " + "; ".join(txt[c] for c in sorted(common[k], key=txt.get)) if common[k] else "")
            + (" · usual, unless a set varies it or lacks it: " + "; ".join(txt[c] for c in sorted(usual[k], key=txt.get)) if usual[k] else ""))


SETTINGS_ROW = re.compile(r" \| \d+ (specimens?|model runs?|experiments?|inputs?)(,|\b)")       # the specimens column that ends every settings-table row (P76; inputs counted, P79)


def settings_blocks(groups, result, S, extras, where=None):
    """P76: a settings entry as a settings table per paper, never a specimen list. The paper's shared-conditions header as in values_blocks;
    one header line naming the columns (the entry's coupled keys: the qualifier variants that go together on one specimen) and
    'specimens' last; one row per distinct level or level combination, its cells as values() prints them (_cell: text, kind mark, ±
    with its basis id) with the first fact id that states the level and how many more do, then the specimens that use the level (count
    and the ids of their sets) and the caveat ids of its records; then, where the paper states no level for some experiments, which;
    the quantity's values computed by this knowledge base in one line that names how to open them (never a k3 column); its results
    that are not settings, one line each; the legends, the caveat texts once and the cross-paper footer (P67) at the end."""
    common, usual = _common_usual(groups)
    legend_cav, legend_basis, marks, out = {}, set(), set(), []
    papers = [k for k in Q.TREES if any(g["paper"] == k for g in groups) or k in extras]
    name = L.NAMES.get(S, S)
    for k in papers:
        T = Q.TREES[k]
        gs = [g for g in groups if g["paper"] == k]
        lines = [x for x in [_shared_head(groups, k, common, usual)] if x]
        rows = [dict(r, record=Q.with_hold(T, r["entity"], r["key"], r["record"])) for g in gs for r in g["rows"]]   # P106: a dose cell carries its hold
        keys = list(dict.fromkeys(r["key"] for r in rows))
        names = {kk: next(r["result_name"] for r in rows if r["key"] == kk) for kk in keys}
        home = {r["entity"]: g["id"] for g in gs for r in g["rows"]}
        by_ent = {}
        for r in rows:
            by_ent.setdefault(r["entity"], {})[r["key"]] = r
        levels = {}
        paper_rows = [r for r in rows if r["entity"] == f"{k}:paper"]           # P79: settings no experiment inherits (an instrument's probe spot, an option)
        by_ent = {e: c for e, c in by_ent.items() if e != f"{k}:paper"}
        for e, cells in by_ent.items():
            level = tuple(_cells(cells[kk]["record"], marks, fact=False) if kk in cells else "—" for kk in keys)
            lv = levels.setdefault(level, dict(ents=[], facts={kk: [] for kk in keys}, recs={}, cav=set()))
            lv["ents"].append(e)
            for kk, r in cells.items():
                rec = r["record"]
                for rr in [rec] + list(rec.get("alternatives") or []):           # P79: every fact that states the level is cited
                    if rr.get("fact") and rr["fact"] not in lv["facts"][kk]:
                        lv["facts"][kk].append(rr["fact"])
                lv["recs"].setdefault(kk, rec)
                lv["cav"] |= {c["id"] for c in rec.get("caveats") or []}
                legend_cav.update({c["id"]: c["text"] for c in rec.get("caveats") or []})
                for rr in [rec] + list(rec.get("alternatives") or []):           # every ± printed in the cell has its basis in the legend (P68)
                    if (rr.get("uncertainty") or {}).get("basis") in L.BASES:
                        legend_basis.add(rr["uncertainty"]["basis"])
        if by_ent:
            lines.append((f"{k}:settings", f"settings table · {short_name(k)} · {name}: one row per distinct level, every fact that states it · columns: " + " | ".join(names[kk] for kk in keys) + " | specimens"))

        def order(item):
            r0 = item[1]["recs"].get(keys[0])
            v = r0.get("value") if r0 else None
            return (0, v, "") if isinstance(v, (int, float)) else (1, 0, item[0][0])
        for level, lv in sorted(levels.items(), key=order):
            cells = [txt + "".join(f" [{f}]" for f in fs) for txt, fs in zip(level, (lv["facts"][kk] for kk in keys))]
            roles = [Q.role(T, e) for e in lv["ents"]]
            n_in = roles.count("input"); exps = [e for e, r in zip(lv["ents"], roles) if r != "input"]
            rs = set(roles) - {"input"}
            noun = ("specimen" if rs == {"specimen"} else "model run" if rs == {"model run"} else "experiment") + ("s" if len(exps) != 1 else "")
            count = (f"{len(exps)} {noun}" if exps else "") + (f"{', ' if exps else ''}{n_in} input{'s' if n_in != 1 else ''}" if n_in else "")
            sets = [s for s in dict.fromkeys(home[e] for e in exps)]
            ids = [s for s in sets if s]
            place = ((("sets " if len(ids) > 1 else "set ") + ", ".join(f"[{s}]" for s in ids)) if ids else "") + (" and outside any set" if ids and "" in sets else "outside any set" if not ids and exps else "")
            first = next((lv["facts"][kk][0] for kk in keys if lv["facts"][kk]), f"{k}:settings")
            lines.append((first, " | ".join(cells) + f" | {count}" + (f" · {place}" if place else "") + (" · caveats " + ", ".join(f"[{c}]" for c in sorted(lv["cav"])) if lv["cav"] else "")))
        for r in paper_rows:                                                    # P79: paper-level settings, one line each
            rec = r["record"]
            lines.append((rec.get("fact") or f"{k}:paper", f"paper-level · under {r['settings'][0]['text'] if r['settings'] else 'the paper'} · {r['result_name']}: {_cells(rec, marks)}" + cmark(rec)))
            legend_cav.update({c["id"]: c["text"] for c in rec.get("caveats") or []})
        if by_ent and not where:
            missing = [e for e in Q.experiments(T) if e not in by_ent]
            if missing:
                lines.append((f"{k}:settings", f"not stated for {len(missing)} of {len(Q.experiments(T))} experiments: " + ", ".join(missing[:12]) + (" …" if len(missing) > 12 else "")))
        if not by_ent and not paper_rows:
            lines.append((f"{k}:settings", f"{short_name(k)} states no {name} as a setting" + (" under this where" if where else "")))
        ex = extras.get(k, {})
        for kk, d in ex.get("derived", {}).items():
            if kk in L.DERIVED and kk not in Q.settings_entries():
                how = f'open with values(result="{d["name"]}", paper="{k}")'
            else:
                how = 'open with detail(ids=[…], parts=["computed"]) on its experiments: ' + ", ".join(d["entities"])
            lines.append((f"{k}:derived", f"derived: {d['name']} — {len(d['entities'])} values {KB} ({d['formula']}) — {how}"))
        for e, kk, nm, rec in ex.get("results", []):
            who = "paper-level" if e == f"{k}:paper" else f"{T.label(e)} [{e}]"
            lines.append((rec.get("fact") or e, f"result, not a setting · {who} · {nm}: {_cells(rec, marks)}" + cmark(rec)))
            legend_cav.update({c["id"]: c["text"] for c in rec.get("caveats") or []})
            for rr in [rec] + list(rec.get("alternatives") or []):
                if (rr.get("uncertainty") or {}).get("basis") in L.BASES:
                    legend_basis.add(rr["uncertainty"]["basis"])
        out.append(block([wrap(*x) for x in lines]))
    tail = ([("legend", "kinds: " + "; ".join(f"({KIND_MARK[k]}) {kind_phrase(k)}" for k in L.KINDS if k in marks) + "; unmarked: measured or stated")] if marks else []) \
        + [("legend", f"basis {b}: {L.BASES[b]}") for b in sorted(legend_basis)] \
        + [(i, f"caveat · {t}") for i, t in legend_cav.items()] \
        + [("between", CN.footer([S], paper=papers[0] if len(papers) == 1 and len(Q.TREES) > 1 else None))]
    out.append(block([], head=[x for i, t in tail for x in wrap(i, t)]))
    return out


def values_blocks(groups, asked):
    """P65: comparison-set summaries. Per set a header (id, kind, label, what it varies, the shared conditions, n rows, the columns),
    then one row per specimen with the result's values across its qualifier variants as columns; a 'not comparable: <axes>' divider
    between consecutive sets whose axes differ (P53), a 'different basis' flag where the uncertainty bases differ (Sec. 19.4); values
    computed by the knowledge base counted, not listed, unless the set has nothing else; the caveats' texts and the basis phrases
    once at the end, then the cross-paper footer (P67). Returns (full blocks, collapsed blocks)."""
    legend_cav, legend_basis, marks, full, collapsed, grid_versions = {}, set(), set(), [], [], {}
    verdict = {(a, b): ax for k, a, b, ax in Q.group_verdicts(groups) for _ in [0]} if len(groups) > 1 else {}
    pair_axes = {}
    for k, a, b, ax in Q.group_verdicts(groups):
        pair_axes.setdefault((a, b), set()).update(ax)
    qids = sorted({r["key"].split("{")[0].split("[")[0] for g in groups for r in g["rows"]})
    prev_bases = None
    def ent_cav(g):                                                             # the caveats of each row (entity) of a set: the union over its cells
        d = {}
        for r in g["rows"]:
            d.setdefault(r["entity"], set()).update(c["id"] for c in r["record"].get("caveats") or [])
        return d
    spec = [g for g in groups if g.get("roles", ["specimen"]) == ["specimen"]]     # the caveats on every specimen row of the output: once, at the end
    common_cav = set.intersection(*[s for g in spec for s in ent_cav(g).values()]) if spec and any(g["rows"] for g in spec) else set()
    all_spec = len(spec) == len(groups)
    one_paper = len({g["paper"] for g in groups}) == 1
    cols_all = []                                                               # the column list once at the top when every set has the same columns
    for g in groups:
        rows_ = [r for r in g["rows"] if r["record"].get("kind") != "computed_by_kb"] or g["rows"]
        cols_all.append(tuple(dict.fromkeys([r["result_name"] for r in rows_] + [name for _, name, _ in g.get("own", [])])))
    same_cols = len(set(cols_all)) == 1
    n_kb = sum(1 for g in groups for r in g["rows"] if r["record"].get("kind") == "computed_by_kb")
    common, usual = _common_usual(groups)                                       # conditions every specimen set of a paper shares, and the usual ones: once, at the top (P44)
    for n, g in enumerate(groups, 1):
        T = Q.TREES[g["paper"]]
        sid = g["id"] or f"{g['paper']}:outside"
        own = [r for r in g["rows"] if r["record"].get("kind") != "computed_by_kb"]
        kb = [r for r in g["rows"] if r["record"].get("kind") == "computed_by_kb"]
        stored = [r for r in kb if r["record"].get("fact")]                       # P86: a stored derived record (a scalar of a curve) is listed after the stated values, marked; a value computed on request is counted
        rows = (own + stored) if (own or stored) else kb
        keys = list(dict.fromkeys(r["key"] for r in rows))
        names = {k: next(r["result_name"] for r in rows if r["key"] == k) for k in keys}
        by_ent = {}
        for r in rows:
            by_ent.setdefault(r["entity"], {})[r["key"]] = r
        is_spec = g.get("roles", ["specimen"]) == ["specimen"]
        lifted = (common[g["paper"]] | usual[g["paper"]]) if is_spec else set()
        shared = "; ".join(f"{x['name']} {x['record']['text']}" for x in g["shared"] if (x["key"], x["record"]["text"]) not in lifted)
        present = {x["key"] for x in g["shared"]} | {x["key"] for r in rows for x in r["settings"]}
        missing = [name for key, name in sorted(_usual_names(groups, g["paper"], usual[g["paper"]])) if is_spec and key not in present]
        head = []
        if (common[g["paper"]] or usual[g["paper"]]) and (n == 1 or groups[n - 2]["paper"] != g["paper"]):
            head.append(_shared_head(groups, g["paper"], common, usual))
        if g["kind"] in HOME_KINDS:                                            # P79: a home that is not a comparison set
            head += [(sid, f"{HOME_KINDS[g['kind']]} [{sid}]" + ("" if one_paper else f" · {short_name(g['paper'])}") + f" · {g['label']}" + f" · {len(by_ent)} rows" + ("" if same_cols else " · columns: " + " | ".join(names[k] for k in keys)))]
        else:
            head += [(sid, f"set [{sid}] ({g['kind'] or 'outside any set'})" + ("" if one_paper else f" · {short_name(g['paper'])}") + f" · {g['label']}" + (f" · varies: {', '.join(g['varies'])}" if g["varies"] else "")
                     + (f" · shared: {shared}" if shared else "") + (f" · lacks: {', '.join(missing)}" if missing else "") + f" · {len(by_ent)} rows" + ("" if same_cols else " · columns: " + " | ".join(names[k] for k in keys)))]
        if n == 1 and same_cols:
            head.insert(0, ("columns", "columns of every row: " + " | ".join(names[k] for k in keys) + (f" · {n_kb} values {KB} are not listed here (detail, parts computed)" if n_kb else "")))
        if n > 1:
            ax = pair_axes.get((n - 1, n), set())
            if ax:
                head.insert(0, ("between", f"— not comparable with set {n - 1}: " + "; ".join(sorted(ax)) + " —"))
        own_cav = (set.intersection(*ent_cav(g).values()) - (common_cav if is_spec else set())) if rows else set()
        if own_cav:
            head.append((sid, "caveats on every row of this set: " + ", ".join(f"[{c}]" for c in sorted(own_cav))))
        bases = {(r["record"].get("uncertainty") or {}).get("basis") or "not stated" for r in rows if r["record"].get("uncertainty")}
        if len(bases) > 1:
            head.append((sid, "different basis within this set: " + " vs ".join(sorted(bases))))
        if prev_bases and bases and bases != prev_bases:
            head.append((sid, f"different basis from set {n - 1}: " + " vs ".join(sorted(bases)) + f" vs {' / '.join(sorted(prev_bases))}"))
        prev_bases = bases or prev_bases
        legend_basis |= {b for b in bases if b in L.BASES}
        out_rows, ranges = [], {}
        for e, cells in by_ent.items():
            r0 = next(iter(cells.values()))
            table_q = {kk.split("{")[0].split("[")[0] for kk in keys}
            st = ", ".join(f"{x['name']} {x['text']}" + (f" [{x['fact']}]" if x.get("fact") and x.get("quantity") in table_q else "") for x in r0["settings"])   # P79: a varied input of the result's own quantity (a set sticking coefficient against the extracted one) carries its id
            row_cav = {c["id"] for r in cells.values() for c in r["record"].get("caveats") or []} - (common_cav if is_spec else set()) - own_cav
            line = f"{r0['name']}" + (f" · {st}" if st else "") + " · " + " | ".join(_cells(cells[k]["record"], marks) if k in cells else "—" for k in keys) \
                + (" · caveats " + ", ".join(f"[{c}]" for c in sorted(row_cav)) if row_cav else "")
            out_rows.append([(e, line)])
            for k, r in cells.items():
                for rr in [r["record"]] + list(r["record"].get("alternatives") or []):
                    legend_cav.update({c["id"]: c["text"] for c in rr.get("caveats") or []})
                    if (rr.get("uncertainty") or {}).get("basis") in L.BASES:
                        legend_basis.add(rr["uncertainty"]["basis"])
                v = r["record"].get("value")
                if v is not None:
                    ranges.setdefault(k, []).append((v, r["record"].get("unit", "")))
        if g.get("grid"):                                                       # P80: a grid set renders as matrices from its full member list
            out_rows = [[(sid, t)] for sid, t in [(x[0], x[1]) for x in grid_lines(g, names, keys, marks, legend_cav, legend_basis)]]
            n_cells = len(g["grid"]["cells"])
            head[-1] = (sid, head[-1][1].replace(f" · {len(by_ent)} rows", f" · {n_cells} cells" + (f" + {len(g['grid']['variants'])} variants" if g["grid"]["variants"] else "")))
            grid_versions[n - 1] = [block([[x] for x in grid_lines(g, names, keys, marks, legend_cav, legend_basis, collapse=j)], head=head, foot=[]) for j in range(1, len(g["grid"]["rows"]) + 1)]
        if g.get("own"):                                                        # P79: the set's own records of the quantity, first row of its block
            by_key = {}
            for kk, name, rec in g["own"]:
                by_key.setdefault(kk, []).append(rec)
                if kk not in names:
                    keys.append(kk); names[kk] = name
            own_cav = sorted({c["id"] for recs in by_key.values() for r in recs for c in r.get("caveats") or []})
            for recs in by_key.values():
                for r in recs:
                    legend_cav.update({c["id"]: c["text"] for c in r.get("caveats") or []})
            out_rows.insert(0, [(sid, "set (values stated for the set, its statistics) · " + " | ".join("; ".join(_cell(r, marks) for r in by_key[k]) if k in by_key else "—" for k in keys)
                                 + (" · caveats " + ", ".join(f"[{c}]" for c in own_cav) if own_cav else ""))])
            head[-1] = (sid, head[-1][1].replace(f" · {len(by_ent)} rows", f" · {len(by_ent)} rows + the set's own records"))
        foot = [(sid, ("claims about this set: " + ", ".join(f"[{c}]" for c in g["claims"])) if len(g["claims"]) <= 8 else
                      f"{len(g['claims'])} claims about this set: open with detail(ids=[{sid!r}], parts=[\"claims\"])")] if g["claims"] else []      # P44: more than eight claims are named by their count
        full.append(block(out_rows, head=head, foot=foot))
        rng = "; ".join(f"{names[k]} {Q.g(min(v for v, _ in vs), 3)}–{Q.g(max(v for v, _ in vs), 3)} {vs[0][1]}".strip() + f" ({len(vs)})" for k, vs in ranges.items())
        if g["kind"] == "figure":                                               # P84: a collapsed figure set names its curves and the ranges of the scalars derived from them
            n_curves = sum(1 for r in own if r["record"].get("curve") or (r["record"].get("text") or "").startswith("curve"))
            rng = f"{n_curves} curves" + (f" · {rng}" if rng else "")
        opener = (f"open with values(set={sid!r})" if g["kind"] == "figure" else f"open with detail(ids=[{sid!r}]) or narrow with where" if g["kind"] not in ("inputs", "paper") else
                  f"open with detail(ids=[{', '.join(repr(e) for e in list(by_ent)[:8])}])" if g["kind"] == "inputs" else "open each with source(id)")
        only_hit = sum(1 for g2 in groups if g2["paper"] == g["paper"]) == 1   # P96: a set with no range and no count is left out unless it is the paper's only hit
        if not rng and not only_hit:
            collapsed.append(block([], head=([head[0]] if head[0][0] == "between" else [])))
            continue
        collapsed.append(block([], head=([head[0]] if head[0][0] == "between" else []) + [(sid, f"{HOME_KINDS.get(g['kind'], 'set')} [{sid}] · {short_name(g['paper'])} · {g['label']} · {len(by_ent)} rows · " + (rng or "no numeric values") + f" · {opener}")]))
    tail = ([("legend", "kinds: " + "; ".join(f"({KIND_MARK[k]}) {kind_phrase(k)}" for k in L.KINDS if k in marks) + "; unmarked: measured or stated")] if marks else []) \
        + [("legend", f"basis {b}: {L.BASES[b]}") for b in sorted(legend_basis)] \
        + ([("legend", ("caveats on every row above: " if all_spec else "caveats on every specimen row above: ") + ", ".join(f"[{c}]" for c in sorted(common_cav)))] if common_cav else [])
    tail.append(("between", CN.footer(qids, paper=groups[0]["paper"] if len({g["paper"] for g in groups}) == 1 and len(Q.TREES) > 1 and all(g["paper"] == groups[0]["paper"] for g in groups) else None)))
    merged_c = []                                                               # P84: the collapsed figure sets of one paper fold into one line naming them
    for n, g in enumerate(groups):
        if g["kind"] == "figure" and merged_c and merged_c[-1][0] == g["paper"]:
            merged_c[-1][1].append(n)
        elif g["kind"] == "figure":
            merged_c.append((g["paper"], [n]))
    for paper, ns in merged_c:
        if len(ns) > 1:
            ids = [groups[n]["id"] for n in ns]
            n_curves = sum(1 for n in ns for r in groups[n]["rows"] if (r["record"].get("text") or "").startswith("curve"))
            if n_curves == 0 and len(ns) < sum(1 for g2 in groups if g2["paper"] == paper):   # P96: no "0 curves of this quantity" line
                for n in ns:
                    collapsed[n] = block([], head=[])
                continue
            line = (ids[0], f"{len(ns)} figure sets of {short_name(paper)} with {n_curves} curves of this quantity: " + ", ".join(f"[{i}]" for i in ids) + " · open one with values(set=<id>)")
            collapsed[ns[0]] = block([], head=[line])
            for n in ns[1:]:
                collapsed[n] = block([], head=[])
    full.append(block([], head=tail)); collapsed.append(block([], head=[tail[-1]]))
    for n, vs in grid_versions.items():                                         # P80: a grid's own-row and foot travel with every collapsed version
        for b in vs:
            b["rows"] = ([full[n]["rows"][0]] if full[n]["rows"] and full[n]["rows"][0][0][1].startswith("set (values stated") else []) + b["rows"]
            b["foot"] = full[n]["foot"]
    return full, collapsed, legend_cav, grid_versions


def set_blocks(d, budget=True):
    """P77: one table for a comparison set (query.set_table): a header (set id, kind, paper, label, what it varies, the member count,
    the columns), one first row 'set' for the records the set owns when it has any, then one row per member of the full list (its label,
    its distinguishing conditions, one cell per column as values() prints cells (_cell), the caveat ids of its records); a value
    computed by this knowledge base is counted in one line, not a column. Over the budget the columns collapse from the last into one
    line naming them and how to open each (values(result=<name>, paper=<paper>)); rows are never dropped; the caveat texts go first
    (P78a, the P65 order). Then the legends, the caveat texts once and the cross-paper footer (P67)."""
    T = Q.TREES[d["paper"]]
    cols = list(d["columns"])

    def render(shown, texts):
        legend_cav, legend_basis, marks = {}, set(), set()

        def cell(recs):
            for r in recs:
                legend_cav.update({c["id"]: c["text"] for c in r.get("caveats") or []})
                for rr in [r] + list(r.get("alternatives") or []):               # every ± the cell prints has its basis in the legend (P68)
                    if (rr.get("uncertainty") or {}).get("basis") in L.BASES:
                        legend_basis.add(rr["uncertainty"]["basis"])
            return "; ".join(_cells(r, marks) for r in recs) if recs else "—"
        rows = []
        row_cav = {row: {c["id"] for k, _ in shown for r in d["cells"][row].get(k, []) for c in r.get("caveats") or []} for row in d["members"]}
        common = set.intersection(*row_cav.values()) if row_cav and all(row_cav.values()) else set()     # caveats on every member row: once, in the header
        for row in (["set"] if "set" in d["cells"] else []) + d["members"]:
            cs = d["cells"][row]
            cav = sorted({c["id"] for k, _ in shown for r in cs.get(k, []) for c in r.get("caveats") or []} - (common if row != "set" else set()))
            if row == "set":
                lab = "set (values stated for the set, its statistics)"
            else:
                st = ", ".join(f"{x['name']} {x['text']}" for x in d["settings"].get(row, []))
                lab = T.label(row) + (f" · {st}" if st else "")
            rows.append((d["id"] if row == "set" else row, lab + " · " + " | ".join(cell(cs.get(k, [])) for k, _ in shown) + (" · caveats " + ", ".join(f"[{c}]" for c in cav) if cav else "")))
        head = [(d["id"], f"set [{d['id']}] ({d['kind']}) · {short_name(d['paper'])} · {d['label']}" + (f" · varies: {', '.join(d['varies'])}" if d["varies"] else "")
                 + f" · {len(d['members'])} members" + (" + the set's own records" if "set" in d["cells"] else "") + " · columns: member | " + " | ".join(n for _, n in shown))]
        if common:
            head.append((d["id"], "caveats on every member row: " + ", ".join(f"[{c}]" for c in sorted(common))))
        foot = []
        hidden = cols[len(shown):]
        if hidden:
            foot.append((d["id"], f"{len(hidden)} more quantities not shown to stay within the budget: " + ", ".join(n for _, n in hidden) + f' — open each with values(result=<name>, paper="{d["paper"]}")'))
        if d["kb"]:
            foot.append((d["id"], f"{d['kb']} values {KB} are not listed here (detail(ids=[member ids], parts=[\"computed\"]))"))
        cited = [i for i in legend_cav if any(f"[{i}]" in t for _, t in rows)]
        tail = ([("legend", "kinds: " + "; ".join(f"({KIND_MARK[k]}) {kind_phrase(k)}" for k in L.KINDS if k in marks) + "; unmarked: measured or stated")] if marks else []) \
            + [("legend", f"basis {b}: {L.BASES[b]}") for b in sorted(legend_basis)] \
            + ([(i, f"caveat · {legend_cav[i]}") for i in cited] if texts else
               ([("legend", f"the texts of the {len(cited)} caveats cited above are not shown, to stay within the budget: open them with detail(ids=[caveat ids])")] if cited else [])) \
            + [("between", CN.footer(sorted({k.split("{")[0].split("[")[0] for k, _ in shown} & set(L.ENTRIES)), paper=d["paper"] if len(Q.TREES) > 1 else None))]
        W = lambda pairs: [x for i, t in pairs for x in wrap(i, t)]
        return [block([W([r]) for r in rows], head=W(head), foot=W(foot)), block([], head=W(tail))]
    steps = [(cols, True)] + [(cols[:n], False) for n in range(len(cols), -1, -1)]      # P78a: the caveat texts go before any column (the P65 order)
    for shown, texts in steps:
        out = render(shown, texts)
        if not (budget and BUDGET) or paginate(out, 0)[-1][0] != "more":
            return out
    return out


SEARCH_LINE = 200
SEARCH_PAPERS = 6                                                               # P93: papers in the cross-paper search view


TAIL_IDS = ("legend", "between")                                                 # the legend and cross-paper footer lines of a values output


def flat_lines(blocks):
    """Every line of a block list in order, unpaginated: [(id, text)]."""
    out = []
    for b in blocks:
        out += list(b["head"])
        for r in b["rows"]:
            out += list(r)
        out += list(b["foot"])
    return out


def split_tail(lines):
    """A values output's lines split into its body and its tail (legend and footer lines, and the caveat texts shown at the end)."""
    body, tail = [], []
    for i, t in lines:
        if i in TAIL_IDS or (t.startswith("caveat · ") and i not in TAIL_IDS and any(x in TAIL_IDS for x, _ in lines[lines.index((i, t)):])):
            tail.append((i, t))
        else:
            body.append((i, t))
    return body, tail


def multi_values_blocks(results, paper, where):
    """P121: values(result=[q1, …, qk], paper): the k single-quantity outputs as consecutive blocks, each under its own 'columns' header,
    the legends, caveat texts and the cross-paper footer once at the end (deduplicated by text). Over the per-call budget the P65 collapse
    has already run inside each block; then whole blocks collapse from the last into one line 'q: n values in m sets — open with
    values(result=q, paper=p)', never the first. An item that resolves to nothing gets its P105 nearest line; the others render."""
    import concept as CN
    parts, tails, seen_tail, marks, qids = [], [], set(), {}, []
    for r in results:
        blocks, e = _run("values", {k: v for k, v in dict(result=r, paper=paper, where=where).items() if v is not None})
        lines = flat_lines(blocks) if not e else [("none", e)]
        body, tail = split_tail(lines)
        for i, t in tail:
            if t.startswith("kinds: ("):                                         # the kind legends merge into one
                marks.update(dict(re.findall(r"\((k\d+)\) ([^;]+)", t)))
            elif i == "between":
                continue                                                        # the cross-paper footer comes once, over every quantity
            elif t not in seen_tail:
                seen_tail.add(t); tails.append((i, t))
        qids += [q for q in CN.resolve_phrase(r)["ids"] if q in L.ENTRIES]
        parts.append((r, body))
    if marks:
        tails.insert(0, ("legend", "kinds: " + "; ".join(f"({m}) {ph.strip()}" for m, ph in sorted(marks.items())) + "; unmarked: measured or stated"))
    if qids:
        foot = CN.footer(list(dict.fromkeys(qids)), paper if paper and len(Q.TREES) > 1 else None)
        if foot:
            tails.append(("between", foot))

    def collapsed(r, k_):
        qids = CN.resolve_phrase(r)["ids"] or [r]
        n = sum(CN.counts().get(q, {}).get(kk, {}).get("values", 0) for q in qids for kk in ([k_] if k_ else Q.TREES))
        m = sum(len(Q.sets_with_quantity(Q.TREES[kk], set(qids))) for kk in ([k_] if k_ else Q.TREES))
        return [(f"{k_ or 'all'}:folded", f"{r}: {n} values in {m} sets — open with values(result={json.dumps(r, ensure_ascii=False)}" + (f", paper=\"{k_}\"" if k_ else "") + ")")]
    out = [dict(block([[x] for x in body], head=[]), scope=n + 1) for n, (_, body) in enumerate(parts)]   # each block dedupes within itself
    out[0]["tail"] = tails                                                       # the legends and the footer close every page (paginate appends a block's tail to each page)
    assemble = lambda: list(out)
    k = len(parts) - 1
    over = lambda: (pg := paginate(assemble(), 0))[-1][0] == "more" or sum(len(t) + len(i) + 4 for i, t in pg) > call_budget()   # the page with its tail within the ordinary per-call budget
    while BUDGET and k > 0 and over():                                          # whole blocks fold from the last, never the first nor a one-line block (a nearest line)
        if len(parts[k][1]) > 1:
            out[k] = block([], head=collapsed(parts[k][0], paper))
        k -= 1
    return assemble()


def empty_pair_blocks(result, paper):
    """P94: values(result, paper) with no value row but claims, curves, panels or definitions of the quantity in the paper: one line of
    counts; [] (an error upstream) when the paper holds nothing of it or the words name no quantity."""
    if not paper:
        return []
    d = Q.empty_pair(result, paper)
    if not d or not any(d[x] for x in ("claims", "curves", "panels", "definitions")):
        return []
    opens = []
    if d["claims"]:
        opens.append("detail(ids=[<claim ids from search>])")
    if d["curves"]:
        opens.append(f"values(set=<a set of {paper}>) or curve(id)")
    if d["panels"]:
        opens.append("detail(ids=[<paper>:fig<N><panel>])")
    line = (f"{paper}: 0 values · {d['claims']} claims · {d['curves']} curves · {d['panels']} panels" + (f" · {d['definitions']} definitions" if d["definitions"] else "")
            + f" of {', '.join(dict.fromkeys(L.NAMES.get(q, q) for q in d['qids']))} — open with " + " / ".join(opens or ["search(words, paper)"]))
    return [block([], head=[(f"{paper}:none", line)])]
BUDGET = True                       # False: values renders everything, no set collapses (the homing check of P79 reads the full rendering)
BUDGET_TOKENS = 2000
BUDGET_CHARS = BUDGET_TOKENS * 4
LIST_BUDGET_MAX = 4                 # P121b: a values call with k listed quantities has a budget of min(k, 4) × BUDGET_TOKENS (at most 8,000 tokens)
_CALL_BUDGET = [BUDGET_CHARS]       # the budget of the call being answered (chars); paginate and the P65 collapse read it


def call_budget():
    return _CALL_BUDGET[-1]
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
            if sum(len(t) + len(i) + 4 for i, t in u) > call_budget() - 400:        # a unit larger than a page goes line by line
                units += [(b, kind, [x]) for x in u]
            else:
                units.append((b, kind, u))
    offset = max(0, int(offset or 0))
    out, scopes, n, size = [], [], offset, 0
    if 0 < offset < len(units):
        b0 = units[offset][0]
        out += b0["context"] + ([b0["short"]] if units[offset][1] != "head" and b0["short"] else [])
        scopes += [b0.get("scope", 0)] * len(out)
        size += sum(len(t) + len(i) + 4 for i, t in out)
    while n < len(units):
        u = units[n][2]
        cost = sum(len(t) + len(i) + 4 for i, t in u)
        if (out and size + cost > call_budget() - 60) or (max_lines and out and len(out) + len(u) > max_lines - 1):
            break
        out += u; scopes += [units[n][0].get("scope", 0)] * len(u); size += cost; n += 1
    seen_lines, seen_defs, page, dropped = set(), set(), [], False
    for (i, t), sc in zip(out, scopes):                                         # P121: a block with its own scope dedupes within itself (one quantity's block of a multi-quantity call)
        for m in DEF_FRAG.finditer(t):                                          # a paper definition once per page
            if m.group(1) in seen_defs:
                t = t.replace(m.group(0), "")
            seen_defs.add(m.group(1))
        key = (sc, i, t) if t.startswith("… ") else (sc, t)                      # a text once per page (per scope), whatever its id; a wrapped continuation belongs to its own line (P68: caveat ids on every fact)
        if t.startswith("… ") and dropped:                                      # the continuation of a dropped duplicate goes with it (P121: blocks share their headers)
            continue
        dropped = False
        if key not in seen_lines:
            page.append((i, t)); seen_lines.add(key)
        else:
            dropped = not t.startswith("… ")
    for b in blocks:                                                            # a block's tail closes every page (the cross-paper footer, P67)
        page += [x for x in b.get("tail", []) if x not in page]
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
    return f"{n} {what} {KB} hidden: parts [\"computed\"] shows them"


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
        if name in ("values", "search") and args.get("paper") and args["paper"] not in Q.TREES:   # P105: an unknown paper name: the nearest three, executed
            return [block([wrap("none", f"no paper named {args['paper']!r}; nearest: " + ", ".join(nearest_papers(args["paper"])) + " · the keys: " + ", ".join(Q.TREES))])], ""
        if name == "values" and args.get("set"):                                # P77: one table for a comparison set
            return set_blocks(Q.set_table(args["set"])), ""
        if name == "values" and isinstance(args.get("result"), list):           # P121: several quantities, one block each, legends and footer once
            return multi_values_blocks(args["result"], args.get("paper"), args.get("where")), ""
        if name == "values" and args.get("result") is None:                     # P117: values(paper=p): the paper's quantity index
            return [block([wrap(*x) for x in CN.paper_index(args["paper"], short_name(args["paper"]))])], ""
        if name == "values" and not _result_ok(args["result"]):                 # P105: an unknown result name: the nearest three, executed
            return [block([wrap("none", f"no result named {args['result']!r}; nearest: " + ", ".join(nearest_results(args["result"])))])], ""
        if name == "values":
            groups = Q.values(args["result"], args.get("paper"), args.get("where"))
            S = Q.settings_entry(args["result"])
            if S:                                                               # P76: a settings entry is a settings table, never a specimen list
                extras = Q.setting_extras(S, args["result"], args.get("paper"), args.get("where"))
                if not groups and not extras:
                    return empty_pair_blocks(args["result"], args.get("paper")), ""
                return settings_blocks(groups, args["result"], S, extras, args.get("where")), ""
            if not groups:
                return empty_pair_blocks(args["result"], args.get("paper")), ""
            full, collapsed, legend_cav, grid_versions = values_blocks(groups, args["result"])
            for blocks in (full, collapsed, *grid_versions.values()):
                for b in blocks:
                    b["head"], b["foot"] = W(b["head"]), W(b["foot"])
                    b["rows"] = [W(r) for r in b["rows"]]
            # over the budget, the output gives way in steps (P65): the model-run sets collapse to their range and count, then the caveat
            # texts go (the ids stay on the rows: caveats are by reference), then the specimen sets collapse, the largest first;
            # the caveat texts, when shown, are only those cited on the lines shown, once, at the end (P68)
            size = lambda b: sum(len(t) + len(i) + 4 for u in [b["head"]] + b["rows"] + [b["foot"]] for i, t in u)
            spec = [n for n in range(len(groups)) if groups[n].get("roles", ["specimen"]) == ["specimen"]]
            order = sorted(set(range(len(groups))) - set(spec), key=lambda n: -size(full[n])) + ["texts"] + sorted(spec, key=lambda n: -size(full[n]))
            order = [x for n in order for x in ([("grid", n, j) for j in range(len(grid_versions[n]))] if n in grid_versions else [n])]   # P80: a grid folds row by row, never a column

            def with_legend(out, k):
                text = "\n".join(t for b in out for u in [b["head"]] + b["rows"] + [b["foot"]] for _, t in u)
                cited = [i for i in legend_cav if f"[{i}]" in text]
                texts = "texts" not in order[:k]
                cav = [(i, f"caveat · {legend_cav[i]}") for i in cited] if texts else \
                    ([("legend", f"the texts of the {len(cited)} caveats cited above are not shown, to stay within the budget: open them with detail(ids=[caveat ids])")] if cited else [])
                n_sets = len({x for x in order[:k] if x != "texts" and not isinstance(x, tuple)})
                note = [("between", f"{n_sets} of {len(groups)} sets collapsed to their range and count to stay within the budget; open them with detail(ids=[set ids]) or narrow with where")] if n_sets else []
                return out[:-1] + [block([], head=note + out[-1]["head"][:-1] + W(cav) + out[-1]["head"][-1:])]
            out = list(full)
            k = 0
            while BUDGET and k < len(order) and paginate(with_legend(out, k), 0)[-1][0] == "more":
                if isinstance(order[k], tuple):
                    out[order[k][1]] = grid_versions[order[k][1]][order[k][2]]
                elif order[k] != "texts":
                    out[order[k]] = collapsed[order[k]]
                k += 1
            if BUDGET and paginate(with_legend(out, k), 0)[-1][0] == "more":    # the last step: a paper's collapsed sets fold into one line naming them, the largest paper first
                size_of = lambda b: sum(len(t) + len(i) + 4 for u in [b["head"]] + b["rows"] + [b["foot"]] for i, t in u)
                papers = sorted({g["paper"] for g in groups}, key=lambda pk: -sum(size_of(out[n]) for n, g in enumerate(groups) if g["paper"] == pk))
                for pk in papers:
                    idxs = [n for n, g in enumerate(groups) if g["paper"] == pk]
                    line = (f"{pk}:folded", f"{len(idxs)} sets of {short_name(pk)} folded to stay within the budget: " + ", ".join(f"[{groups[n]['id'] or pk + ':outside'}]" for n in idxs)
                            + f' · open them with values(result="{args["result"]}", paper="{pk}") or values(set=<id>)')
                    out[idxs[0]] = block([], head=[line])
                    for n in idxs[1:]:
                        out[n] = block([], head=[])
                    if paginate(with_legend(out, k), 0)[-1][0] != "more":
                        break
            return with_legend(out, k), ""
        if name == "papers":
            lines = CN.papers_lines(args.get("material"), args.get("structure"), args.get("process"), args.get("quantity"))
            if not lines:
                return [], ""
            return [block([wrap(*x) for x in lines])], ""
        if name == "concept":
            if not Q.tokens(args["words"]):
                return [], "error: concept: words has no letters or numbers"
            lines = CN.concept_lines(args["words"])
            if not lines:
                return [], ""
            return [block([wrap(*x) for x in lines])], ""
        if name == "search" and not args.get("paper"):                        # P93: the cross-paper view, one line per paper
            if not Q.tokens(args["words"]):
                return [], "error: search: words has no letters or numbers"
            hits = Q.search(args["words"])
            items = [[x for x in wrap(h["id"], Q.render_hit(h)[0])] for h in hits if h["type"] == "concept"][:3]
            by_paper = {}
            for h in hits:
                if h["type"] != "concept" and h["paper"]:
                    by_paper.setdefault(h["paper"], []).append(h)
            cids = [h["id"] for h in hits if h["type"] == "concept"][:3] or CN.resolve(args["words"])[0][:3]
            qids = {c for c in cids if c in L.ENTRIES and L.ENTRIES[c]["type"] in ("quantity", "categorical")}
            qname = ", ".join(L.NAMES.get(q, q) for q in sorted(qids))
            for pk in list(by_paper)[:SEARCH_PAPERS]:
                hs = by_paper[pk]; best = hs[0]
                line, cav = Q.render_hit(best)
                sets = Q.sets_with_quantity(Q.TREES[pk], qids) if qids else []
                qw = set(CN.words_of(args["words"]))                            # P113: the sets by word overlap with the query, the stored order breaking ties
                sets = sorted(sets, key=lambda c: -len(qw & set(CN.words_of((Q.TREES[pk].byid[c].get("label_as_printed") or "") + " " + Q.TREES[pk].byid[c]["statement"]))))
                if len(line) > 130:
                    line = line[:128].rsplit(" ", 1)[0] + " …"
                text = (f"{pk} ({short_name(pk)}) · [{best['id']}] {line}" + (f" · +{len(hs) - 1} hits" if len(hs) > 1 else "")
                        + (" · sets: " + ", ".join(f"[{c}]" for c in sets[:4]) + (f" +{len(sets) - 4}" if len(sets) > 4 else "") if sets else ""))
                rec = dict(caveats=list(cav.values()))
                items.append([x for x in wrap(pk, text + cmark(rec))])          # the caveat ids stay on the line; their texts come with the paper view
            rest = list(by_paper)[SEARCH_PAPERS:]
            foot = "open a paper with search(words, paper=<key>)" + (f"; sets hold {qname}" if qids and any(Q.sets_with_quantity(Q.TREES[pk], qids) for pk in list(by_paper)[:SEARCH_PAPERS]) else "")
            if rest:
                foot += f" · further papers with hits: {', '.join(rest)}"
            b = block(items); b["tail"] = W([("between", foot)]) if foot else []
            return [b], ""
        if name == "search":
            if not Q.tokens(args["words"]):
                return [], "error: search: words has no letters or numbers"
            hits, items, seen = Q.search(args["words"], args.get("paper")), [], {}
            for h in hits:            # values and settings: one line per paper and quantity; other records: a line shown once with its count
                if h["type"] == "concept":
                    items.append([x for x in wrap(h["id"], Q.render_hit(h)[0])]); continue
                if h["type"] in ("value", "setting"):
                    T = Q.TREES[h["paper"]]; f = T.byid[h["id"]]
                    key = (h["paper"], h["type"], Q.name_of(Q.ckey(f), f))
                    g = seen.setdefault(key, [h, 0, [], {}, set()])
                    g[1] += 1
                    rec = Q.record(T, f)
                    if rec["text"] not in g[2]:                                 # P107: a derived slot's text carries its source here too
                        g[2].append(rec["text"])
                    g[3].update({c["id"]: c for c in rec["caveats"]})                       # the caveats of any value in the line
                    g[4].add(rec["kind"])                                                   # the kinds of the values on the line (P68)
                    continue
                line, cav = Q.render_hit(h)                                      # P84e: every other kind through the one registry (a figure-inventory record is no tree row)
                g = seen.setdefault((h["type"], line), [h, 0, None, {}, set(), line])
                g[1] += 1
                g[3].update(cav)
            for key, (h, n, vals, cav, kinds, *rest) in seen.items():
                if vals is not None:
                    shown = ", ".join(vals[:8]) + (f", … ({len(vals)} distinct)" if len(vals) > 8 else "")
                    line = f"{h['type']}s of {key[2]} in {short_name(key[0])}: {n} record{'s' if n > 1 else ''} · {kinds_text(kinds)} · {shown}"
                else:
                    line = rest[0] + (f" · {n} records with this line" if n > 1 else "")
                if len(line) > SEARCH_LINE:
                    line = line[:SEARCH_LINE - 2].rsplit(" ", 1)[0] + " …"
                rec = dict(caveats=list(cav.values()))
                items.append([x for y in [(h["id"], line + cmark(rec))] + clines(rec) for x in wrap(*y)])
            cids = [h["id"] for h in hits if h["type"] == "concept"][:3] or CN.resolve(args["words"])[0][:3]
            foot = CN.footer([c for c in cids if c in L.ENTRIES], args.get("paper")) if cids else ""
            b = block(items); b["tail"] = W([("between", foot)]) if foot else []     # on every page (P67)
            return [b], ""
        if name == "detail":
            parts = [p for p in (args.get("parts") or DETAIL_DEFAULT) if p in DETAIL_PARTS] or DETAIL_DEFAULT
            if "ids" in args:                                                   # P66: several ids, one budget; the page dedupes lines across them
                out, errs = [], []
                for i in dict.fromkeys(args["ids"]):
                    b, e = _run("detail", {"id": i, "parts": parts})
                    out += b; errs += [e] if e else []
                return out, "; ".join(errs)
            if args["id"] in Q.TREES:                                           # P117: a paper key: its quantity index
                return [block([wrap(*x) for x in CN.paper_index(args["id"], short_name(args["id"]))])], ""
            if args["id"] in L.ENTRIES or args["id"].startswith("family:"):      # P110: a concept, model, mechanism, species, structure or family id: its card
                return [block([wrap(*x) for x in CN.concept_lines(args["id"])])], ""
            T0 = Q.tree_of(args["id"]); n0 = T0.byid.get(args["id"])
            if n0 is None:                                                      # P92: a location id: the records located there, in page order
                loc = Q.located(args["id"])
                out = [(loc["id"], f"location [{loc['id']}] · {short_name(loc['paper'])} · {loc['kind']} · {len(loc['facts'])} records" + (f" · {len(loc['inventory'])} panel{'s' if len(loc['inventory']) != 1 else ''}" if loc["inventory"] else ""))]
                for inv in loc["inventory"]:
                    out.append((inv["id"], f"figure panel · Fig. {inv['figure']}{(' panel ' + inv['panel']) if inv['panel'] else ''} · {inv['panel_type']} · {inv['content']} · {inv['status']}"))
                for f in loc["facts"]:
                    out += record_detail(T0, f)[:1]
                return [block([wrap(*x) for x in out])], ""
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
                comp = [r for r in d["results"] if r["record"].get("kind") == "computed_by_kb"]
                own = [r for r in d["results"] if r["record"].get("kind") != "computed_by_kb"]
                show = "computed" in parts or not own                                     # values computed by the knowledge base only when asked or nothing else exists
                if "results" in parts:
                    out += [y for r in own for y in [(r["record"].get("fact") or i, "result · " + value_line(r["record"], r["name"]) + defined_as(d["paper"], r["key"]) + cmark(r["record"]))] + clines(r["record"])]
                    if comp and not show:
                        out.append((i, _hidden(len(comp))))
                if show:
                    out += [y for r in comp for y in [(i, "result · " + value_line(r["record"], r["name"]) + defined_as(d["paper"], r["key"]) + cmark(r["record"]))] + clines(r["record"])]
                if "recipe" in parts:
                    T_ = Q.tree_of(i)
                    cyc = Q.cycle_block(T_, i, {c["key"]: c for c in d["recipe"]})   # P106: the cycle's steps in the paper's stated order, a hold on its dose line
                    used = {k for b in cyc for k in b["keys"]}
                    for n, b in enumerate(cyc, 1):
                        out.append((b["facts"][0] if b["facts"] else i, f"cycle step {n} ({'stated order' if b['stated'] else 'role order dose → hold → purge'}) · {b['text']}" + (" · " + ", ".join(f"[{x}]" for x in b["facts"][1:]) if len(b["facts"]) > 1 else "")))
                    out += [y for c in d["recipe"] if c["key"] not in used for y in [(c["record"].get("fact") or i, "condition · " + value_line(c["record"], c["name"]) + cmark(c["record"]))] + clines(c["record"])]
            elif d["type"] == "comparison":
                T = Q.tree_of(i)
                if "what" in parts:
                    out.append((i, f"comparison ({short_name(d['paper'])}): {d['label']} · set kind: {d['kind']} · varies: {', '.join(d['varies']) or 'nothing stated'}"
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
                        out.append((i, f"fit (kind: {KB}): {f_['name']} ∝ {f_['x']}^{f_['exponent']} (residual {f_['residual']}, {f_['n']} points)"
                                    + "".join(f" · correction (kind: {KB}) for {c['condition']} to {c['to']}: exponent {c['exponent']} (residual {c['residual']}); "
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
            extra = set_blocks(Q.set_table(i)) if d["type"] == "comparison" and "table" in parts else []     # P77: the set-wide table, the same renderer
            return [block([wrap(*x) for x in out])] + extra, ""
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
        if name == "curve":                                                     # P84 access layer: one curve, its points within the budget
            c = Q.curve(args["id"])
            r = Q.record(Q.TREES[c["paper"]], Q.TREES[c["paper"]].byid[c["id"]])
            out = [(c["id"], f"curve [{c['id']}] · {short_name(c['paper'])} Fig. {c['figure']}{c['panel']}" + (f" · series '{c['label']}'" if c["label"] else "") + f" · {c['n_points']} points"
                   + (f", {len(c['points'])} shown (evenly thinned)" if c["thinned"] else "") + f" · {kind_text(c['kind'])}" + (f" · set [{c['set']}]" if c["set"] else "")),
                   (c["id"], f"x: {c['x']['name']} ({c['x']['quantity']}) in {c['x']['unit'] or 'no unit'} · printed label '{c['x']['label_raw']}'" + (f" · transform {c['x']['transform']} undone" if c["x"]["transform"] else "")),
                   (c["id"], f"y: {c['y']['name']} ({c['y']['quantity']}) in {c['y']['unit'] or 'no unit'} · printed label '{c['y']['label_raw']}'" + (f" · transform {c['y']['transform']} undone" if c["y"]["transform"] else ""))]
            if c["conditions"]:
                out.append((c["id"], "conditions: " + "; ".join(f"{x['name']} {x['text']}" for x in c["conditions"])))
            if c["derived"]:
                out.append((c["id"], f"values {KB}: " + "; ".join(f"{d['name']} {d['value']} {d['unit']} by {d['method'].replace('_', ' ')} [{d['id']}]" for d in c["derived"])))
            if c["uncertainty"]:
                out.append((c["id"], "uncertainty:" + unc_text(c["uncertainty"])))
            if c["flags"]:
                out.append((c["id"], "flags of the figure stage: " + ", ".join(sorted(set(c["flags"]))) + " (a flag marks the figure for review; it deletes nothing)"))
            out.append((c["id"], "points (x, y): " + ", ".join(f"({x}, {y})" for x, y in c["points"])))
            cv = c.get("converted")                                             # P109: the converted series, rendered here only
            if cv and cv.get("context"):
                out.append((c["id"], f"converted {cv['axis']} ({KB}): {L.NAMES.get(cv['quantity'], cv['quantity'])} ({cv['quantity']}) in {cv['unit']} by {cv['rule']} with {L.NAMES.get(cv['requires'], cv['requires'])} "
                                     f"{cv['context_value']:g} {cv['context_unit']} [{cv['context']}] · points (x, y): " + ", ".join(f"({x}, {y})" for x, y in cv["points"])))
            elif cv:
                out.append((c["id"], f"converts to {cv['quantity']} given {cv['requires']}: not computed ({cv.get('reason', '')})"))
            out.append((c["id"], f"provenance: {c['provenance'].get('extractor', 'vlm')} {c['provenance'].get('model', '')}, prompt {str(c['provenance'].get('prompt_sha256', ''))[:12]}"))
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
        return dict(type="none")                                                # also a concept id (an entry, not a record of a paper)
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
