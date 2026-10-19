#!/usr/bin/env python3
"""P133 pass 1: one call per section of pilot/<pid>.elements.csv; every element answered with form records or NK:<reason>.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass1_elements.py yli18     # after pass0_paper.py

Sections: the elements.csv section column (elements.py maps equations into their section); a group whose section is not abs/abstract
or s<n> (figures, tables, a table's cells) is unmapped and runs as its own group. Prompt, in this order: the section's elements as
"<id>: <text>"; the pass-0 names (the only mentions vocabulary) and the figure/table/equation element ids; the form (schema/form.json,
compact) with the field rules; the kind vocabulary with its ontology glosses (vocab.PHRASES). Response (P133 option 2): {"answers": [{"id", "answer": [record, ...]
or "NK:<reason>"}]}; variables as a list of {symbol, quantity}. Prints the tallies; local validation against the full form.json is a count only (the compiler validates, P134).
"""
import collections
import json
import re
import sys

import common as C
from vocab import MECHANISMS, NAMES, PHRASES

NK = ["citation_line", "boilerplate", "no_knowledge"]
NK_FORM = ["citation_line", "boilerplate", "duplicate", "no_knowledge"]      # the nk enum of the response (duplicate: duplicate_of names the element)
MAPPED = re.compile(r"^(abs|abstract|s\d+)$")
RULES = """FIELD RULES
- Answer every element id below, once: nk = none with its records, or, when the element holds no knowledge, nk = citation_line,
  boilerplate, duplicate (duplicate_of = the element id it repeats) or no_knowledge, with records empty.
- quote: at most 15 words copied verbatim from the element; every record has one.
- note: at most 20 words, on claims and definitions only.
- quantity: an id of the form; "other" only when no id fits, and then candidate is required, with the paper's own definition copied
  verbatim (never written by you), the unit as printed, its dimension and symbol.
- label_as_printed: the paper's own label of the quantity, on every record with a quantity.
- cause, relation, effect: all three or none (claims only).
- value, value_min, value_max, value_text: as printed; unit: a string as printed, never inferred or converted.
- mentions: only names from the MENTIONS list, exactly as listed."""


def groups(pid):
    g = collections.OrderedDict()
    for r in C.E.load(pid):
        g.setdefault(r["section"], []).append(r)
    return g


THINKING = {"thinking_level": "LOW"}                                            # user, P133: the lowest the model takes (MINIMAL: 400 on gemini-3.8-flash); recorded in the line


def response_schema(form, ids):
    """{"answers": [{"id", "nk", "duplicate_of", "records"}]} (user, P133: element ids are values, not keys; no union: nk = none means
    the records apply, else records is empty); the record is the provider form, its variables written as a list of {symbol, quantity}
    (the compiler maps it back to the object)."""
    rec = C.provider_schema(form)
    var = form["properties"]["variables"]["additionalProperties"]
    rec["properties"]["variables"] = {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["symbol", "quantity"], "properties": {
        "symbol": {"type": "string", "minLength": 1}, "quantity": C.provider_schema(var, form["$defs"])}}}
    item = {"type": "object", "required": ["id", "nk", "records"], "properties": {"id": {"type": "string", "enum": ids},
            "nk": {"type": "string", "enum": ["none"] + NK_FORM}, "duplicate_of": {"type": "string"}, "records": {"type": "array", "items": rec}}}
    return {"type": "object", "required": ["answers"], "properties": {"answers": {"type": "array", "items": item}}}


def answers(resp):
    """The response as {element id: [record, ...] or "NK:<reason>"} (the jsonl keeps the raw text)."""
    out = {}
    for a in (resp.get("answers") or []) if isinstance(resp, dict) else []:
        if isinstance(a, dict) and "id" in a:
            nk = a.get("nk", "none")
            out[a["id"]] = a.get("records") or [] if nk == "none" else f"NK:{nk}" + (f":{a.get('duplicate_of', '')}" if nk == "duplicate" else "")
    return out


def jobs(pid):
    p0 = C.lines(pid, 0)
    if not p0:
        raise C.Stop("no pass-0 line in records/: run pass0_paper.py first")
    items = C.loads_json(p0[-1]["response"])
    names = sorted({it["name_as_printed"] for it in items if isinstance(it, dict) and it.get("name_as_printed")})
    rows = C.E.load(pid)
    refs = [r["element_id"] for r in rows if r["kind"] in ("caption", "panel", "equation")]
    form = C.schema("form.json")
    text = C.E.texts(pid)
    kinds = "\n".join(f"- {k}: {PHRASES.get(k, '')}" for k in C.X._pilot()[0].KINDS)
    qids = "\n".join(f"{q}: {NAMES.get(q, q)}" for q in form["$defs"]["quantity_id"]["enum"])
    mids = "\n".join(f"{m}: {MECHANISMS[m]['name']}" for m in form["$defs"]["cause_effect"]["enum"] if m in MECHANISMS)
    out = []
    for sec, rs in groups(pid).items():
        ids = [r["element_id"] for r in rs]
        prompt = "\n\n".join([
            "You extract the knowledge of one section of an ALD paper into records of the form below.",
            "ELEMENTS:\n" + "\n".join(f"{i}: {text[i]}" for i in ids),
            "MENTIONS (the only allowed mentions):\n" + "\n".join(names) + "\nElement ids that may be mentioned: " + ", ".join(refs),
            "FORM (JSON Schema, one record):\n" + json.dumps(form, ensure_ascii=False, separators=(",", ":")) + "\n\n" + RULES,
            "KIND (how a value is known):\n" + kinds,
            "QUANTITY IDS (id: name). quantity must be one of them or \"other\"; qualifier x, variables[].quantity and each cause/effect item "
            "must be one of them (cause/effect may also be a mechanism id):\n" + qids,
            "MECHANISM IDS (id: name), for cause/effect:\n" + mids])
        out.append((1, sec, prompt, response_schema(form, ids), ids))
    return out


def main(arg):
    from jsonschema import Draft202012Validator
    pid, key = C.resolve(arg)
    js = jobs(pid)
    if len(sys.argv) > 2:                                                       # optional: only these sections
        js = [j for j in js if j[1] in sys.argv[2:]]
    unmapped = [j[1] for j in js if not MAPPED.match(j[1])]
    print(f"{key} pass 1: {len(js)} sections ({', '.join(j[1] for j in js)}); unmapped groups: {', '.join(unmapped) or 'none'}")
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
                    bad += any(True for _ in val.iter_errors(rec))
    print(f"{key} pass 1: {nrec} records by type {dict(types.most_common())}; NK {dict(nk.most_common())}; elements missing {missing}; "
          f"records failing form.json {bad}; unparsed responses {unparsed or 'none'}")
    tin = sum(x["usage"]["input_tokens"] for x in C.lines(pid)); tout = sum(x["usage"]["output_tokens"] for x in C.lines(pid))
    print(f"{key} records/{pid}.jsonl: {len(C.lines(pid))} lines, tokens in {tin} out {tout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
