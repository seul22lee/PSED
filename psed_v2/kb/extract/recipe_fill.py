#!/usr/bin/env python3
"""P181 (user): the recipe fields of each pass-0 run, one call per paper with runs (the P179 process_mode fill's mechanism, process_mode_fill.py):
reactant_A, reactant_B, carrier_gas (species entries) and process_mode (the ontology's values), each with the quote that states it and the
element holding it, or null when the text does not state it. Input: the runs of the pass-0 line compile uses (id, name, evidence quote,
the reactant, step and plasma settings pass 1 gave them or the paper) and every text element of the paper (process_mode_fill.TEXT_KINDS;
P182 (user): no section-name selection). The response is one records
line of pass RECIPE_FILL_PASS (compile and the pass-1 prompt read the latest fill); nothing else of pass 0 changes (asserted: the units
without the recipe fields are byte-identical).

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/recipe_fill.py yli18 [--plan] [--refill]

P182 (user): --refill calls only for a paper whose latest fill leaves a recipe field null on at least one run (null_fields). The
response schema makes each quote a required string (empty for a null field); compile.recipe_fill, the importer, keeps a value only when
its quote is found (compile.quote_found) and lists the others.
"""
import json
import sys

import common as C
import compile as K
import process_mode_fill as PM

THINKING = {"thinking_level": "LOW"}
FIELDS = C.X.RECIPE_FIELDS
DROP = tuple(f + x for f in FIELDS for x in ("", "_quote", "_element"))


def job(pid, fields=FIELDS):
    """(pass, section, prompt, response schema, element ids) or None when the paper has no run. P185: fields, the recipe fields asked
    (a material-only refill: ['material']; compile.recipe_fill merges each field from the latest line holding it)."""
    base = PM.job(pid)                                                          # the runs, their settings and the text, as the P179 fill reads them
    if base is None:
        return None
    _, _, pm_prompt, pm_schema, els = base
    head, rest = pm_prompt.split("\n\nRECIPES", 1)
    runs = pm_schema["properties"]["recipes"]["items"]["properties"]["id"]["enum"]
    species = [i for i, e in K.V.ENTRIES.items() if e.get("type") == "species"]
    values = list(K.V.CATEGORICAL_VALUES["process_mode"])
    mats = list(K.V.MATERIALS)
    ids = {f: (values if f == "process_mode" else mats if f == "material" else species) for f in fields}
    defs = "; ".join(f"{f}: {K.V.ENTRIES[f]['definition']}" for f in fields)
    prompt = (
        "You read the text of one ALD paper and give, for each recipe (a deposition run) listed below, its recipe fields: "
        + "; ".join(f"{f} (one of {', '.join(ids[f])})" for f in fields) + f". The fields: {defs}. "
        "A field is stated for a run when the text states it for that run, for a set of runs it belongs to, or for every deposition of the paper; a "
        "run's own name in the text stating it states it too. reactant_A and reactant_B are the reactants in the order the text gives the cycle "
        "(the precursor dosed first, then the co-reactant). For each field give the quote copied verbatim from the TEXT (the words that state it) "
        "and the id of the element holding it. A field the text does not state: the value null, its quote an empty string, its element null. Never infer a "
        "field from another field, a number or a typical process."
        "\n\nRECIPES" + rest)
    item = {"id": {"enum": runs}}
    for f in fields:
        item[f] = {"anyOf": [{"enum": ids[f]}, {"type": "null"}]}
        item[f + "_quote"] = {"type": "string"}                                # P182 (user): a required string; the importer checks it
        item[f + "_element"] = {"anyOf": [{"enum": els}, {"type": "null"}]}
    schema = {"type": "object", "additionalProperties": False, "required": ["recipes"],
              "properties": {"recipes": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": list(item), "properties": item}}}}
    return (K.RECIPE_FILL_PASS, "recipe", prompt, schema, els)


def null_fields(pid):
    """P182: {run id: [fields null]} of the pass-0 runs after the latest fill line (compile.recipe_fill: its contract applied); a field
    the user decided (history.csv kind recipe_field) is not null in this sense; runs with none left out."""
    _, fill, listed = K.recipe_fill(pid)
    decided = {(x["run"], x["field"]) for x in listed if x["reason"].startswith("the user's recipe decision")}
    _, _, units = PM.pass0_line(pid)
    out = {u["id"]: [f for f in FIELDS if not (fill.get(u["id"]) or {}).get(f) and (u["id"], f) not in decided] for u in units if u.get("role") == "run" and u.get("id")}
    return {i: fs for i, fs in out.items() if fs}


def main(arg):
    pid, key = C.resolve(arg)
    fields = sys.argv[sys.argv.index("--fields") + 1].split(",") if "--fields" in sys.argv else FIELDS   # P185: e.g. --fields material
    assert set(fields) <= set(FIELDS), fields
    j = job(pid, fields)
    if j is None:
        print(f"{key}: no run in pass 0: no call")
        return 0
    if "--refill" in sys.argv and not null_fields(pid):
        print(f"{key}: no null recipe field: no call")
        return 0
    if "--plan" in sys.argv:
        C.plan(pid, [j], THINKING)
        print(f"{key}: prompt {len(j[2])} chars (~{int(len(j[2]) / 3.1)} tokens), {len(j[3]['properties']['recipes']['items']['properties']['id']['enum'])} runs")
        return 0
    out, _ = C.run(pid, [j], THINKING)
    fill = {x["id"]: x for x in C.loads_json(out[0]["response"]).get("recipes") or []}
    _, _, units = PM.pass0_line(pid)
    merged = json.loads(json.dumps(units))
    for u in merged:
        if u.get("id") in fill:
            u.update({k: v for k, v in fill[u["id"]].items() if k != "id"})
    strip = [{k: v for k, v in u.items() if k not in DROP} for u in merged]
    assert json.dumps(strip, ensure_ascii=False, sort_keys=True) == json.dumps([{k: v for k, v in u.items() if k not in DROP} for u in units], ensure_ascii=False, sort_keys=True), \
        "pass-0 units changed beyond the recipe fields"
    text = C.E.texts(pid)
    for u in units:
        if u.get("id") in fill:
            x = fill[u["id"]]
            cells = []
            for f in fields:
                how, _ = K.quote_found(pid, x.get(f + "_quote"), K.normalize(text.get(x.get(f + "_element") or "", "")), x.get(f + "_element"))
                found = "-" if not x.get(f) else ("found" if how else "NOT FOUND")       # P182: compile.quote_found, the importer's check
                cells.append(f"{f} {x.get(f) or 'null'} [{x.get(f + '_element') or '-'}; quote {found}] {x.get(f + '_quote') or ''}")
            print(f"{key} | {u['id']} | " + " | ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(C.main(main))
