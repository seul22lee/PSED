#!/usr/bin/env python3
"""P133 pass 1: one call per section of pilot/<pid>.elements.csv; every element answered with form records or NK:<reason>.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass1_elements.py yli18     # after pass0_paper.py

Sections: the elements.csv section column (elements.py maps equations into their section); a group whose section is not abs/abstract
or s<n> (figures, tables, a table's cells) is unmapped and runs as its own group. Prompt, in this order: the section's elements as
"<id>: <text>"; the pass-0 items (id, role, name, parent; P138) and the figure/table/equation element ids; the form (schema/form.json,
compact) with the field rules; the kind vocabulary with its ontology glosses (vocab.PHRASES). Response (P133 option 2): {"answers": [{"id", "answer": [record, ...]
or "NK:<reason>"}]}; variables as a list of {symbol, quantity}. Prints the tallies; local validation against the full form.json is a count only (the compiler validates, P134).
"""
import collections
import json
import re
import sys

import yaml

import common as C
from vocab import MECHANISMS, NAMES, PHRASES

NK = ["citation_line", "boilerplate", "no_knowledge"]
NK_FORM = ["citation_line", "boilerplate", "duplicate", "no_knowledge"]      # the nk enum of the response (duplicate: duplicate_of names the element)
MAPPED = re.compile(r"^(abs|abstract|s\d+)$")
RULES = """TYPES (one per record):
- setting: a condition the authors chose, including the measurement setup (objective, resolution, scan length, precision).
- observation: a measured result on a specimen.
- derived: a number the authors computed from their data (fit parameters, values derived in a table).
- model: an equation or a model statement; quantity = what the equation gives, variables = its symbols. An equation is a model, not
  a definition.
- definition: a symbol or term the paper defines; term = the symbol as printed, quantity = the entry it stands for when one exists.
- claim: a causal statement or an interpretation of results, with cause and effect (ids of the cause/effect enum), relation and
  stance; see the claim example below. An abstract, introduction or conclusion paragraph that states a result or an interpretation
  is a claim, never NK.
- caveat: a limitation or assumption the authors state about their own method or data (not a claim).
- cited: a value or statement the paper attributes to another work (not a setting).

FIELD RULES
- Every field of a record is present; write null when it does not apply.
- Answer every element id below, once: nk = none with its records, or, when the element holds no knowledge, nk = citation_line,
  boilerplate, duplicate (duplicate_of = the element id it repeats) or no_knowledge, with records empty:
  boilerplate: headings, author lines, acknowledgements; citation_line: a reference-list entry; duplicate: a statement already
  recorded from another element; no_knowledge: the element states nothing the form can hold.
- quote: words copied verbatim from the element, as few as identify the record; every record has one.
- note: at most 20 words, on claims and definitions only.
- quantity: an id of QUANTITY IDS only when it is the same concept as printed (its aliases, unit and note tell you); otherwise
  "other", with a candidate: the paper's own definition copied verbatim (never written by you), the unit as printed, its dimension
  and symbol. Examples:
  "rms thickness error" -> other, not thickness_nonuniformity; "10 min stabilisation" -> other, not time; "c = 0.01" ->
  initial_sticking_coefficient when the paper's own table says so, never reaction_stoichiometry.
- label_as_printed: the paper's own label of the quantity, on every record with a quantity.
- kind: on every record with a value, value_min, value_max or value_text.
- parent: the id (from PASS-0 ITEMS) of the run, simulation, series or specimen the record belongs to; "paper" for claims,
  definitions, caveats, cited records and paper-wide settings (reactor, carrier gas).
- links (claims and caveats): the element ids of the evidence the claim or caveat rests on.
- statement: one sentence in your own words when the record carries no quantity and no value (never a copy of the element).
- statement is never null on claim, caveat and cited records (one sentence, your words).
- a name the paper gives a set of runs or samples ("Series A", "set 2") is a setting of quantity other with label_as_printed = the
  name and mentions = each member it names; the compiler attaches it.
- variables (models and definitions): each symbol -> its quantity id, or null when no id fits.
- cause, relation, effect: all three or none (claims only).
- value, value_min, value_max, value_text: as printed; unit: a string as printed, never inferred or converted; the value_text of
  material, substrate, reactant_A, reactant_B and structure is an id of the form; for a reactor or an instrument, the name only.
- mentions: only names from PASS-0 ITEMS (name as printed), exactly as listed."""


def container(eid):
    """The figure, table or equation an element id belongs to, from the id as elements.py writes it: fig<n>.cap, fig<n>, fig<n><panel>
    -> fig<n>; tab<x>.cap, tab<x>.r<i>c<j>, tabu<k>.r<i>c<j> -> tab<x> / tabu<k>; eq<n> -> eq<n>."""
    head = eid.split(".")[0]
    return re.sub(r"^(fig\d+)[a-z]+$", r"\1", head)


def groups(pid):
    """P133b: a section group per mapped section (abstract, s<n>); an element with no section mapping goes to its container (one group
    per figure: caption + panels; per table: caption + cells; an equation alone). Returns (groups, unpaired): unpaired lists the
    containers that have a caption and no body, or a body and no caption."""
    g = collections.OrderedDict()
    for r in C.E.load(pid):
        g.setdefault(r["section"] if MAPPED.match(r["section"]) else container(r["element_id"]), []).append(r)
    unpaired = [k for k, rs in g.items() if not MAPPED.match(k) and not k.startswith("eq")
                and len({r["kind"] == "caption" for r in rs}) == 1]
    return g, unpaired


THINKING = {"thinking_level": "LOW"}                                            # user, P133: the lowest the model takes (MINIMAL: 400 on gemini-3.8-flash); recorded in the line


def response_schema(form, ids):
    """{"answers": [{"id", "nk", "duplicate_of", "records"}]} (user, P133: element ids are values, not keys; no union: nk = none means
    the records apply, else records is empty); the record is the provider form, its variables written as a list of {symbol, quantity}
    (the compiler maps it back to the object)."""
    rec = C.provider_schema(form)
    vobj = next(x for x in form["properties"]["variables"]["anyOf"] if x.get("type") == "object")   # P139: the nullable object's object branch
    var = vobj["additionalProperties"]
    rec["properties"]["variables"] = {"type": ["array", "null"], "minItems": 1, "items": {"type": "object", "required": ["symbol", "quantity"], "properties": {
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


def TYPES(form):
    """The record types of the form (P139: the enum inside the nullable type)."""
    return next(x for x in form["properties"]["type"]["anyOf"] if "enum" in x)["enum"]


def examples(pid, form):
    """P136 3b: one example record per type, from the gold facts.csv of the dev papers other than pid (never a held-out paper): the
    first row of the type (with a quantity where the type takes one) that, cast into the form (form_roundtrip.cast; term kept; quote =
    the first 12 words of its first evidence element), validates against form.json. Rendered as JSON, one line per type."""
    import csv as _csv
    from jsonschema import Draft202012Validator
    import form_roundtrip as RT
    val, props, out = Draft202012Validator(form), form["properties"], {}
    for p in [p for p in C.E.PAPERS if p != pid and p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        if not f.exists():
            continue
        text = C.E.texts(p)
        for row in _csv.DictReader(f.open(encoding="utf-8")):
            t = row["type"]
            if t in out or t not in TYPES(form) or "#" not in row["fact_id"]:
                continue
            if t in ("setting", "observation", "derived", "model", "definition") and not row["quantity"]:
                continue
            if t == "claim" and not all(row[x] for x in ("cause", "relation", "effect", "stance")):     # P136b: the claim example carries all four
                continue
            rec, lost = RT.cast(row, props)
            if t == "definition":
                rec["term"] = row["term"]
            if not (rec.get("quantity") or any(k in rec for k in ("value", "value_min", "value_max", "value_text"))) and len(row["statement"].split()) <= 40:
                rec["statement"] = row["statement"]                             # P138: the gold's own-words statement
            if t in ("claim", "definition", "caveat", "cited"):
                rec["parent"] = "paper"
            words = text.get(row["evidence"].split(";")[0], "").split()[:12]
            if lost or not words:
                continue
            rec["quote"] = " ".join(words)
            rec = {k: rec.get(k) for k in form["required"]}                     # P139: every field present, null when it does not apply
            if not list(val.iter_errors(rec)):
                out[t] = rec
    return "\n".join(f"- {t}: " + json.dumps(out[t], ensure_ascii=False) for t in TYPES(form) if t in out)


def jobs(pid):
    p0 = C.lines(pid, 0)
    if not p0:
        raise C.Stop("no pass-0 line in records/: run pass0_paper.py first")
    items = C.loads_json(p0[-1]["response"])
    items = [it for it in items if isinstance(it, dict) and it.get("name_as_printed")]
    p0 = "\n".join(f"{it.get('id', '')} | {it.get('role', '')} | {it['name_as_printed']} | parent {it.get('parent', '') or '-'}" for it in items)   # P138
    rows = C.E.load(pid)
    refs = [r["element_id"] for r in rows if r["kind"] in ("caption", "panel", "equation")]
    form = C.schema("form.json")
    text = C.E.texts(pid)
    kinds = "\n".join(f"- {k}: {PHRASES.get(k, '')}" for k in C.X._pilot()[0].KINDS)
    E = {e["id"]: e for e in yaml.safe_load((C.V2 / "ontology" / "ontology.yaml").read_text(encoding="utf-8"))["entries"]}   # P138: from the ontology
    qids = "\n".join(f"{q}: {E.get(q, {}).get('name') or NAMES.get(q, q)}" + (f" | aliases: {'; '.join(map(str, E[q].get('aliases') or []))}" if E.get(q, {}).get("aliases") else "")
                     + (f" | unit: {E[q]['unit']}" if E.get(q, {}).get("unit") else "") + (f" | note: {E[q]['note']}" if E.get(q, {}).get("note") else "")
                     for q in form["$defs"]["quantity_id"]["enum"])
    mids = "\n".join(f"{m}: {MECHANISMS[m]['name']}" for m in form["$defs"]["cause_effect"]["enum"] if m in MECHANISMS)
    ex = examples(pid, form)
    out = []
    for sec, rs in groups(pid)[0].items():
        ids = [r["element_id"] for r in rs]
        prompt = "\n\n".join([
            "You extract the knowledge of one section of an ALD paper into records of the form below.",
            "ELEMENTS:\n" + "\n".join(f"{i}: {text[i]}" for i in ids),
            "PASS-0 ITEMS (id | role | name as printed | parent): parent takes an id; mentions take a name\n" + p0
            + "\nElement ids that may be mentioned or linked: " + ", ".join(refs),
            "FORM (JSON Schema, one record):\n" + json.dumps(form, ensure_ascii=False, separators=(",", ":")) + "\n\n" + RULES,
            "EXAMPLES (one record per type, from other papers):\n" + ex,
            "KIND (how a value is known):\n" + kinds,
            "QUANTITY IDS (id: name | aliases | canonical unit | note). quantity must be one of them or \"other\"; qualifier x, variables[].quantity and each cause/effect item "
            "must be one of them (cause/effect may also be a mechanism id):\n" + qids,
            "MECHANISM IDS (id: name), for cause/effect:\n" + mids])
        out.append((1, sec, prompt, response_schema(form, ids), ids))
    return out


def main(arg):
    from jsonschema import Draft202012Validator
    pid, key = C.resolve(arg)
    js = jobs(pid)
    only = [a for a in sys.argv[2:] if not a.startswith("--")]
    if only:                                                                    # optional: only these groups
        js = [j for j in js if j[1] in only]
    unmapped = [j[1] for j in js if not MAPPED.match(j[1])]
    print(f"{key} pass 1: {len(js)} groups ({', '.join(j[1] for j in js)}); figure/table/equation groups: {', '.join(unmapped) or 'none'}; "
          f"unpaired: {', '.join(groups(pid)[1]) or 'none'}")
    if "--plan" in sys.argv:                                                    # the planned calls only, no call
        C.plan(pid, js, THINKING)
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
                    bad += any(True for _ in val.iter_errors(rec))
    print(f"{key} pass 1: {nrec} records by type {dict(types.most_common())}; NK {dict(nk.most_common())}; elements missing {missing}; "
          f"records failing form.json {bad}; unparsed responses {unparsed or 'none'}")
    tin = sum(x["usage"]["input_tokens"] for x in C.lines(pid)); tout = sum(x["usage"]["output_tokens"] for x in C.lines(pid))
    print(f"{key} records/{pid}.jsonl: {len(C.lines(pid))} lines, tokens in {tin} out {tout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
