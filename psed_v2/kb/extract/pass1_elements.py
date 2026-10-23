#!/usr/bin/env python3
"""P133 pass 1: one call per section of pilot/<pid>.elements.csv; every element answered with form records or NK:<reason>.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/pass1_elements.py yli18 [--plan]     # after pass0_paper.py

Sections: the elements.csv section column (elements.py maps equations into their section); a group whose section is not abs/abstract
or s<n> (figures, tables, a table's cells) is unmapped and runs as its own group. P148 prompt: a fixed prefix, the same for every
group of a paper and sent as Gemini cached content (common.run): the instruction line, CODEBOOK.md whole (in place of form.json; the
provider schema still constrains the response), RULES (only what the codebook does not say), EXAMPLES (one gold record per type and
element kind, from the other dev papers), PASS-0 UNITS (id | role | name | parent | data, from the latest pass-0 line); then the
group's elements as render.group() writes them (the blocks pass 0 uses). Response (P133 option 2): {"answers": [{"id", "nk",
"duplicate_of", "records"}]}; variables as a list of {symbol, quantity}. Prints the tallies; local validation against the full
form.json is a count only (the compiler validates, P134).
"""
import collections
import json
import re
import sys

import yaml

import common as C
import render
from lists import NK_REASONS

NK = ["citation_line", "boilerplate", "no_knowledge"]
NK_FORM = list(NK_REASONS)                                                     # P148: the nk enum of the response, from the codebook's NK reasons
MAPPED = re.compile(r"^(abs|abstract|s\d+)$")
MERGE_TOKENS, TOKEN_CHARS = 6000, 3.1                                           # P148-cost: merge sections up to 6k tokens; 3.1 chars/token measured on the P146 pass-0 lines (3.00-3.26)
FORM_ONLY = {"quote": None, "candidate": "quantity", "variables": ("model", "definition")}   # P148-cost: form fields no gold column holds
INTRO = "You extract the knowledge of an ALD paper, one group of its elements per request, into records of the response form."
RULES = """RULES (what the codebook does not say)
Answer
- Answer every element id of ELEMENTS once: nk = none with its records, or nk = one of the codebook's NK reasons with records empty
  (duplicate: duplicate_of = the element id it repeats).
Fields
- Every field of a record is present; write null when it does not apply.
- quote: words copied verbatim from the element, as few as identify the record; every record has one.
- about: the PASS-0 UNITS id of the run, specimen, simulation or model run the record is about; "paper" when it is about none of them.
- note: at most 20 words, on claims and definitions only.
- quantity, a qualifier's quantity, variables[].quantity and each cause/effect item: an id of the codebook's quantities (d); cause and
  effect may also be a mechanism id (f).
- quantity: an id only when it is the same concept as printed (its aliases, unit and note tell you); otherwise "other", with a
  candidate: the paper's own definition copied verbatim (never written by you), the unit as printed, its dimension and symbol.
  Examples: "rms thickness error" -> other, not thickness_nonuniformity; "10 min stabilisation" -> other, not time; "c = 0.01" ->
  initial_sticking_coefficient when the paper's own table says so, never reaction_stoichiometry.
- label_as_printed: the paper's own label of the quantity, on every record with a quantity.
- kind: on every record with a value, value_min, value_max or value_text.
- links (claims and caveats): the element ids of the evidence the claim or caveat rests on.
- statement: one sentence in your own words when the record carries no quantity and no value (never a copy of the element).
- statement is never null on claim, caveat and cited records (one sentence, your words).
- a name the paper gives a set of runs or samples ("Series A", "set 2") is a setting of quantity other with label_as_printed = the
  name and mentions = each member it names; the compiler attaches it.
- cause, relation, effect: all three or none (claims only).
- value, value_min, value_max, value_text: as printed; unit: a string as printed, never inferred or converted; the value_text of
  material, substrate, reactant_A, reactant_B and structure is an id of the codebook's species, materials and structures (f); for
  a reactor or an instrument, the name only.
- mentions: only names from PASS-0 UNITS (name as printed), exactly as listed."""


def container(eid):
    """The figure, table or equation an element id belongs to, from the id as elements.py writes it: fig<n>.cap, fig<n>, fig<n><panel>
    -> fig<n>; tab<x>.cap, tab<x>.r<i>c<j>, tabu<k>.r<i>c<j> -> tab<x> / tabu<k>; eq<n> -> eq<n>."""
    head = eid.split(".")[0]
    return re.sub(r"^(fig\d+)[a-z]+$", r"\1", head)


def is_section(key):
    """A section group: every part of its name (P148-cost: merged sections are joined with +) is abs/abstract or s<n>."""
    return all(MAPPED.match(x) for x in key.split("+"))


def groups(pid):
    """P133b: a section group per mapped section (abstract, s<n>); an element with no section mapping goes to its container (one group
    per figure: caption + panels; per table: caption + cells; an equation alone). P148-cost: consecutive section groups are merged
    (names joined with +) while their element text, as render.group() writes it, stays under MERGE_TOKENS (at TOKEN_CHARS chars per
    token); a section over the limit stays alone; tables, figures and equations stay their own groups. Returns (groups, unpaired):
    unpaired lists the containers that have a caption and no body, or a body and no caption."""
    g = collections.OrderedDict()
    for r in C.E.load(pid):
        g.setdefault(r["section"] if MAPPED.match(r["section"]) else container(r["element_id"]), []).append(r)
    unpaired = [k for k, rs in g.items() if not MAPPED.match(k) and not k.startswith("eq")
                and len({r["kind"] == "caption" for r in rs}) == 1]
    text = C.E.texts(pid)
    size = lambda rs: sum(len(f"{r['element_id']}: {render.strip_markup(text[r['element_id']])}") + 1 for r in rs)   # noqa: E731
    out, cur = collections.OrderedDict(), None
    for k, rs in g.items():
        if MAPPED.match(k) and cur is not None and size(out[cur] + rs) < MERGE_TOKENS * TOKEN_CHARS:
            out[f"{cur}+{k}"] = out.pop(cur) + rs
            cur = f"{cur}+{k}"
            continue
        out[k] = list(rs)
        cur = k if MAPPED.match(k) else None
    return out, unpaired


THINKING = {"thinking_level": "LOW"}                                            # user, P133: the lowest the model takes (MINIMAL: 400 on gemini-3.8-flash); recorded in the line


def fields_by_type(form):
    """P148-cost: the form fields each record type uses, by the REVIEW §1a rule (kb/reports/review/1a_fields_by_type.csv): the
    facts.csv columns with a non-empty value in a row of that type in any dev gold (held-out papers never read), each as its form
    field (parent -> about); plus the form fields no gold column holds where the rules need them (FORM_ONLY): quote on every type,
    candidate where quantity is, variables on models and definitions. {type: [field, ...]} in the form's field order."""
    import csv as _csv
    used = collections.defaultdict(set)
    for p in [p for p in C.E.PAPERS if p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        for row in (_csv.DictReader(f.open(encoding="utf-8")) if f.exists() else []):
            if "#" in row["fact_id"]:
                used[row["type"]] |= {"about" if c == "parent" else C.X.form_field(c) for c, v in row.items() if v}
    out = {}
    for t in TYPES(form):
        u = used[t] | {"type", "quote"} | ({"candidate"} if "quantity" in used[t] else set()) | ({"variables"} if t in FORM_ONLY["variables"] else set())
        out[t] = [k for k in form["required"] if k in u]
    return out


def variables_schema(form):
    """The provider's variables: a list of {symbol, quantity} (the compiler maps it back to the form's object)."""
    vobj = next(x for x in form["properties"]["variables"]["anyOf"] if x.get("type") == "object")   # P139: the nullable object's object branch
    return {"type": ["array", "null"], "minItems": 1, "items": {"type": "object", "required": ["symbol", "quantity"], "properties": {
        "symbol": {"type": "string", "minLength": 1}, "quantity": C.provider_schema(vobj["additionalProperties"], form["$defs"])}}}


SHARED = ("qualifiers",)                                                        # P148-cost2: defined once in $defs, referenced from every branch


def record_schema(form):
    """P148-cost: the provider schema of one record by type, each branch keyed by its type (a one-value enum, never null) and listing
    only that type's fields (fields_by_type), every one required and nullable. P148-cost2: the branches joined by anyOf (a top-level
    oneOf drew a bare 400); the SHARED fields written once under $defs and referenced as #/$defs/<field> (provider_schema() inlines
    every $ref, P133, so the reference is put in after it). Returns (record schema, $defs)."""
    var, defs, out = variables_schema(form), {k: C.provider_schema(form["properties"][k], form["$defs"]) for k in SHARED}, []
    for t, fs in fields_by_type(form).items():
        props = {k: ({"type": "string", "enum": [t]} if k == "type" else var if k == "variables" else {"$ref": f"#/$defs/{k}"} if k in SHARED
                     else C.provider_schema(form["properties"][k], form["$defs"])) for k in fs}
        out.append({"type": "object", "required": fs, "properties": props})
    return {"anyOf": out}, defs


def flat_schema(form):
    """The P139 record: the whole provider form, every field required and nullable, variables as the list."""
    rec = C.provider_schema(form)
    rec["properties"]["variables"] = variables_schema(form)
    return rec


def response_schema(form, ids, flat=False):
    """{"answers": [{"id", "nk", "duplicate_of", "records"}]} (user, P133: element ids are values, not keys; no union: nk = none means
    the records apply, else records is empty); the record is record_schema() (by type, P148-cost2), or with flat the P139 record."""
    rec, defs = (flat_schema(form), {}) if flat else record_schema(form)
    item = {"type": "object", "required": ["id", "nk", "records"], "properties": {"id": {"type": "string", "enum": ids},
            "nk": {"type": "string", "enum": ["none"] + NK_FORM}, "duplicate_of": {"type": "string"}, "records": {"type": "array", "items": rec}}}
    return {"type": "object", "required": ["answers"], "properties": {"answers": {"type": "array", "items": item}}, **({"$defs": defs} if defs else {})}


def answers(resp):
    """The response as {element id: [record, ...] or "NK:<reason>"} (the jsonl keeps the raw text)."""
    out = {}
    for a in (resp.get("answers") or []) if isinstance(resp, dict) else []:
        if isinstance(a, dict) and "id" in a:
            nk = a.get("nk", "none")
            out[a["id"]] = a.get("records") or [] if nk == "none" else f"NK:{nk}" + (f":{a.get('duplicate_of', '')}" if nk == "duplicate" else "")
    return out


def TYPES(form):
    """The record types of the form (P139: the enum inside the nullable type)."""
    return next(x for x in form["properties"]["type"]["anyOf"] if "enum" in x)["enum"]


EXAMPLE_KINDS = {"abstract": "paragraph", "paragraph": "paragraph", "table_cell": "table cell", "caption": "caption", "equation": "equation"}


def _about(R, units, fid):
    """The gold unit a gold row is about: the first run, specimen, simulation or model run (render.gold_units) above it; "paper"
    when none."""
    i = R.get(fid, {}).get("parent", "")
    while i in R:
        if i in units:
            return i
        i = R[i]["parent"]
    return "paper"


def _quote(row, text, check):
    """A quote for a gold row from its first evidence element's text (render.strip_markup), never its first words: a table cell or
    an equation whole; else the sentence that holds the row's value, label or term as printed (cut to 8 words either side of it when
    longer than 25 words), else the sentence sharing the most words with the gold statement; kept only when check() (the compiler's
    D11 on the element) passes and it has at most 40 words."""
    e = row["evidence"].split(";")[0]
    t = render.strip_markup(text.get(e, "")).strip()
    if re.fullmatch(r"(tab\w*\.r\d+c\d+|eq\d+)", e):
        return t if t and check(e, t) else None
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", t) if x.strip()]
    keys = [k.lower() for k in (row["value"], row["label_as_printed"], row["term"], row["value_text"]) if k]
    q = None
    for sent in sents:
        hit = next((k for k in keys if k in sent.lower()), None)
        if hit:
            w = sent.split()
            at = next((n for n in range(len(w)) if hit in " ".join(w[n:n + len(hit.split()) + 1]).lower()), 0)
            q = " ".join(w[max(0, at - 8):at + 9]) if len(w) > 25 else sent
            break
    if q is None:
        words = lambda x: set(re.findall(r"[a-z0-9]+", x.lower()))             # noqa: E731
        best = max(sents, key=lambda x: len(words(row["statement"]) & words(x)), default="")
        q = best if best and words(row["statement"]) & words(best) else None
    return q if q and len(q.split()) <= 40 and check(e, q) else None


def examples(pid, form):
    """P148 (A3): one example record per record type and element kind (paragraph, table cell, caption, equation), from the gold
    facts.csv of the dev papers other than pid (never a held-out paper), in paper order: the first row of that type whose first
    evidence element is of that kind (a quantity and its label as printed where the type takes one; when no row of the type and kind
    has both, a second pass takes one without them, a setting, observation or derived still with a quantity; a claim with all four
    claim fields) that, cast into
    the form (form_roundtrip.cast; term kept), validates against form.json; about = the gold unit it is about (_about; an
    observation or derived example names one), quote = _quote() (the compiler's D11 check). Rendered as JSON with the type's fields
    only (fields_by_type), one line each, with the paper, the type and the element kind."""
    import csv as _csv
    from jsonschema import Draft202012Validator
    import compile as K
    import form_roundtrip as RT
    val, props, out, fbt = Draft202012Validator(form), form["properties"], {}, fields_by_type(form)
    for strict, p in [(st, p) for st in (True, False) for p in C.E.PAPERS if p != pid and p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        if not f.exists():
            continue
        text, kinds = C.E.texts(p), {r["element_id"]: r["kind"] for r in C.E.load(p)}
        rows = list(_csv.DictReader(f.open(encoding="utf-8")))
        R = {r["fact_id"]: r for r in rows}
        units = {u["gid"] for u in render.gold_units(p)}

        def check(e, q):
            return K.normalize(q) in K.normalize(text.get(e, ""))
        for row in rows:
            t, ek = row["type"], EXAMPLE_KINDS.get(kinds.get(row["evidence"].split(";")[0], ""))
            if (t, ek) in out or ek is None or t not in TYPES(form) or "#" not in row["fact_id"]:
                continue
            if strict and t in ("setting", "observation", "derived", "model", "definition") and not (row["quantity"] and row["label_as_printed"]):
                continue                                                        # P148: a quantity with its label as printed (RULES); else a second pass
            if t in ("setting", "observation", "derived") and not row["quantity"]:
                continue
            if t == "claim" and not all(row[x] for x in ("cause", "relation", "effect", "stance")):     # P136b: the claim example carries all four
                continue
            rec, lost = RT.cast(row, props)
            if lost:
                continue
            if t == "definition":
                rec["term"] = row["term"]
            if not (rec.get("quantity") or any(k in rec for k in ("value", "value_min", "value_max", "value_text"))) and len(row["statement"].split()) <= 40:
                rec["statement"] = row["statement"]                             # P138: the gold's own-words statement
            rec["about"] = "paper" if t in ("claim", "definition", "caveat", "cited") else _about(R, units, row["fact_id"])
            if t in ("observation", "derived") and rec["about"] == "paper":       # a result example names its unit
                continue
            q = _quote(row, text, check)
            if not q:
                continue
            rec["quote"] = q
            rec = {k: rec.get(k) for k in form["required"]}                     # P139: every field present, null when it does not apply
            if not list(val.iter_errors(rec)):
                out[(t, ek)] = (C.E.PAPERS[p], {k: rec[k] for k in fbt[t]})       # P148-cost: the type's fields only (the response schema's)
    order = [(t, k) for t in TYPES(form) for k in dict.fromkeys(EXAMPLE_KINDS.values()) if (t, k) in out]
    return "\n".join(f"- {t} / {k} ({out[(t, k)][0]}): " + json.dumps(out[(t, k)][1], ensure_ascii=False) for t, k in order)


def units_block(pid):
    """P148 (A5): PASS-0 UNITS, one line per unit of the latest pass-0 line: id | role | name | parent | data (id:role ...). P161: then
    the units compile.curve_units() derives from the curves no pass-0 unit names, each line ending | <origin>; none, no line."""
    import compile as K                                                         # P161 (compile imports this module)
    p0 = C.lines(pid, 0)
    if not p0:
        raise C.Stop("no pass-0 line in records/: run pass0_paper.py first")
    obj = C.loads_json(p0[-1]["response"])
    items = (obj.get("units") or []) if isinstance(obj, dict) else obj       # P144: pass 0 is {units, table_layouts, panel_layouts}
    data = lambda it: " ".join(f"{d.get('id')}" + (f" point {d['point']}" if d.get("point") else "") + f":{d.get('role')}" if isinstance(d, dict) else str(d)   # noqa: E731
                               for d in (it.get("data") or [])) or "-"
    line = lambda it: f"{it.get('id', '')} | {it.get('role', '')} | {it.get('name_as_printed') or '-'} | {it.get('parent') or '-'} | {data(it)}"   # noqa: E731
    der = K.curve_units(pid, obj)
    return "\n".join([line(it) for it in items if isinstance(it, dict)]
                     + (["Units the compiler derived from figure curves (one per curve, or point, no unit above names; name = the legend label):"] if der else [])
                     + [f"{line(it)} | {it['origin']}" for it in der])


def prefix(pid, form):
    """P148 (A1): the fixed prefix of every group of the paper, in this order: the instruction line, CODEBOOK.md whole, RULES,
    EXAMPLES, PASS-0 UNITS (with the caption, panel and equation ids a link may name)."""
    rows = C.E.load(pid)
    refs = [r["element_id"] for r in rows if r["kind"] in ("caption", "panel", "equation")]
    return "\n\n".join([INTRO, "CODEBOOK:\n" + render.codebook(), RULES,
                         "EXAMPLES (one gold record per type and element kind, from other papers; their about ids are those papers' units):\n" + examples(pid, form),
                         "PASS-0 UNITS (id | role | name | parent | data id:role): about takes an id; mentions take a name\n" + units_block(pid)
                         + "\nElement ids that may be linked: " + ", ".join(refs)]) + "\n\n"


def jobs(pid, flat=True):
    """[(1, group, prompt, response schema, element ids, prefix)]: prompt = the prefix, then the group's ELEMENTS (render.group);
    flat (the default, P148-cost2): the P139 record schema, accepted with the cached prefix; flat=False: record_schema() by type,
    rejected (400) as a oneOf and as an anyOf with $defs."""
    form = C.schema("form.json")
    pre = prefix(pid, form)
    text, rows = C.E.texts(pid), C.E.load(pid)
    out = []
    for sec, rs in groups(pid)[0].items():
        ids = [r["element_id"] for r in rs]
        out.append((1, sec, pre + f"ELEMENTS (group {sec}):\n" + render.group(pid, sec, rs, text, rows), response_schema(form, ids, flat), ids, pre))
    return out


def main(arg):
    from jsonschema import Draft202012Validator
    pid, key = C.resolve(arg)
    js = jobs(pid, flat="--schema=typed" not in sys.argv)                      # P148-cost2: flat (P139) by default; the by-type schema drew a 400
    only = [a for a in sys.argv[2:] if not a.startswith("--")]
    if only:                                                                    # optional: only these groups
        js = [j for j in js if j[1] in only]
    unmapped = [j[1] for j in js if not is_section(j[1])]
    print(f"{key} pass 1: {len(js)} groups ({', '.join(j[1] for j in js)}); figure/table/equation groups: {', '.join(unmapped) or 'none'}; "
          f"unpaired: {', '.join(groups(pid)[1]) or 'none'}")
    if "--plan" in sys.argv:                                                    # the planned calls only, no call
        C.plan(pid, js, THINKING)
        pre, rest = len(js[0][5]) if js else 0, [len(j[2]) - len(j[5]) for j in js]
        print(f"{key}: prefix {pre} chars (~{pre // 4} tokens at 4 chars/token), sent once as cached content; group parts {sum(rest)} chars in all, "
              f"largest {max(rest, default=0)} ({max(js, key=lambda j: len(j[2]) - len(j[5]))[1] if js else '-'})")
        return 0
    out, _ = C.run(pid, js, THINKING)
    val = Draft202012Validator(C.schema("form.json"))
    types, nk, missing, bad, nrec, unparsed = collections.Counter(), collections.Counter(), 0, 0, 0, []
    for line in out:
        try:
            resp = answers(C.loads_json(line["response"]))
        except Exception:
            unparsed.append(line["section"])
            continue
        for i in line["element_ids"]:
            a = resp.get(i)
            if a is None:
                missing += 1
            elif isinstance(a, str):
                nk[re.sub(r"^NK:(duplicate):.*", r"\1", a).removeprefix("NK:")] += 1
            else:
                for rec in a:
                    nrec += 1
                    types[rec.get("type", "?") if isinstance(rec, dict) else "?"] += 1
                    if isinstance(rec, dict) and isinstance(rec.get("variables"), list):   # the provider's list back to the form's object
                        rec = {**rec, "variables": {v.get("symbol"): v.get("quantity") for v in rec["variables"] if isinstance(v, dict)}}
                    if isinstance(rec, dict):                                   # P148-cost: a field the type does not use is null
                        rec = {**{k: None for k in C.schema("form.json")["required"]}, **rec}
                    bad += any(True for _ in val.iter_errors(rec))
    print(f"{key} pass 1: {nrec} records by type {dict(types.most_common())}; NK {dict(nk.most_common())}; elements missing {missing}; "
          f"records failing form.json {bad}; unparsed responses {unparsed or 'none'}")
    tin, tout, tcr = (sum(x["usage"].get(k, 0) for x in out) for k in ("input_tokens", "output_tokens", "cache_read_tokens"))
    print(f"{key} this run: {len(out)} lines, tokens in {tin} (cache read {tcr}) out {tout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
