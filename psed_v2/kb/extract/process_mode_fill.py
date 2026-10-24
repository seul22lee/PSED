#!/usr/bin/env python3
"""P179 (user): the process_mode of each pass-0 recipe (a unit of role run), one call per paper with runs. Input: the runs of the pass-0
line compile uses (id, name, evidence quote, the reactant, step and plasma settings pass 1 gave them or the paper) and the text of the
method / experimental elements (the sections whose heading names an experiment, a method, a procedure or the materials, and the
sections where a run is introduced). Output per run: process_mode (the ontology's values) or null, the quote that states it and the
element id holding it. The response is one records line of pass PROCESS_MODE_PASS (compile reads the latest and merges the three fields
into the runs); nothing else of pass 0 changes (asserted: the units without the new fields are byte-identical).

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/process_mode_fill.py yli18 [--plan]
"""
import json
import re
import sys

import common as C
import compile as K

THINKING = {"thinking_level": "LOW"}                                            # P179: a small reading task (pass 1's level)
METHOD_HEADING = re.compile(r"(?i)experiment|method|procedure|material")
SETTING_Q = ("reactant_A", "reactant_B", "carrier_gas", "plasma_power", "plasma_configuration", "plasma_gas_ratio", "pulse_time", "purge_time")
FIELDS = ("process_mode", "process_mode_quote", "process_mode_element")


def pass0_line(pid):
    """(line number, units) of the pass-0 line compile uses (Run.read: the one the pass-1 lines in use were written against)."""
    run = K.Run(pid)
    run.read()
    lines = C.lines(pid)
    n = next(n for n in run.lines_used if lines[n - 1]["pass"] == 0)
    obj = C.loads_json(lines[n - 1]["response"])
    return n, run, [u for u in (obj.get("units") or []) if isinstance(u, dict)]


def job(pid):
    """(pass, section, prompt, response schema, element ids) or None when the paper has no run."""
    n, run, units = pass0_line(pid)
    runs = [u for u in units if u.get("role") == "run" and u.get("id")]
    if not runs:
        return None
    recs = run.resolve_other(run.read())
    sets = {}
    for r in recs:
        rec = r["rec"]
        if rec.get("type") == "setting" and rec.get("quantity") in SETTING_Q and rec.get("about") in [u["id"] for u in runs] + ["paper"]:
            q = rec.get("qualifiers") if isinstance(rec.get("qualifiers"), dict) else {}
            qs = ";".join(f"{k}={v}" for k, v in q.items() if k in ("step", "species", "gas") and v)
            v = rec.get("value_text") or (f"{rec.get('value')} {rec.get('unit') or ''}".strip() if rec.get("value") is not None else "")
            sets.setdefault(rec["about"], []).append(f"{rec['quantity']}{'{' + qs + '}' if qs else ''}={v}")
    rows = C.E.load(pid)
    text = C.E.texts(pid)
    sec_of = {r["element_id"]: r["section"] for r in rows}
    secs = {r["section"] for r in rows if r["kind"] == "heading" and METHOD_HEADING.search(text.get(r["element_id"], ""))}
    secs |= {sec_of[e] for u in runs for e in u.get("introduced_in") or [] if e in sec_of and sec_of[e] not in ("figures", "")}
    els = [r["element_id"] for r in rows if (r["section"] in secs and r["kind"] in ("heading", "paragraph"))
           or r["element_id"] in {e for u in runs for e in u.get("introduced_in") or []}]   # and where each run is introduced (its name)
    values = list(K.V.CATEGORICAL_VALUES["process_mode"])
    defs = K.V.ENTRIES["process_mode"]["definition"]
    prompt = "\n\n".join([
        f"You read the method / experimental text of one ALD paper and give, for each recipe (a deposition run) listed below, its process mode: one "
        f"of {', '.join(values)} ({defs}). The mode is stated for a run when the text states it for that run, for a set of runs it belongs to, or for "
        "every deposition of the paper (for example 'the films were deposited by plasma-enhanced ALD'); a run's own name in the text stating the mode "
        "states it too. Give the quote copied verbatim from the TEXT (the words that state the mode) and the id of the element holding it. A run "
        "whose mode the text does not state: process_mode null, quote null, element null. Never infer the mode from the reactants, the reactant "
        "order or a number.",
        "RECIPES (id | name as printed | evidence quote | settings):\n" + "\n".join(
            f"{u['id']} | {u.get('name_as_printed') or '-'} | {u.get('evidence_quote') or '-'} | {'; '.join(sets.get(u['id'], [])) or '-'}" for u in runs)
        + (f"\nsettings of the paper (all runs): {'; '.join(sets['paper'])}" if sets.get("paper") else ""),
        "TEXT (element id: text):\n" + "\n".join(f"{e}: {text[e]}" for e in els)])
    schema = {"type": "object", "additionalProperties": False, "required": ["recipes"],
              "properties": {"recipes": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["id", "process_mode", "quote", "element"],
                                                                     "properties": {"id": {"enum": [u["id"] for u in runs]},
                                                                                    "process_mode": {"anyOf": [{"enum": values}, {"type": "null"}]},
                                                                                    "quote": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
                                                                                    "element": {"anyOf": [{"enum": els}, {"type": "null"}]}}}}}}
    return (K.PROCESS_MODE_PASS, "process_mode", prompt, schema, els)


def merged(units, fill):
    """The pass-0 units with the fill's three fields on its runs."""
    out = json.loads(json.dumps(units))
    for u in out:
        x = fill.get(u.get("id"))
        if x and u.get("role") == "run":
            u.update(process_mode=x.get("process_mode"), process_mode_quote=x.get("quote"), process_mode_element=x.get("element"))
    return out


def main(arg):
    pid, key = C.resolve(arg)
    j = job(pid)
    if j is None:
        print(f"{key}: no run in pass 0: no call")
        return 0
    if "--plan" in sys.argv:
        C.plan(pid, [j], THINKING)
        print(f"{key}: prompt {len(j[2])} chars (~{int(len(j[2]) / 3.1)} tokens), {len(j[3]['properties']['recipes']['items']['properties']['id']['enum'])} runs")
        return 0
    out, _ = C.run(pid, [j], THINKING)
    resp = C.loads_json(out[0]["response"])
    fill = {x["id"]: x for x in resp.get("recipes") or []}
    _, _, units = pass0_line(pid)
    m = merged(units, fill)
    strip = [{k: v for k, v in u.items() if k not in FIELDS} for u in m]
    assert json.dumps(strip, ensure_ascii=False, sort_keys=True) == json.dumps(units, ensure_ascii=False, sort_keys=True), "pass-0 units changed beyond process_mode"
    text = C.E.texts(pid)
    for u in units:
        if u.get("role") == "run":
            x = fill.get(u["id"], {})
            q, t = K.normalize(x.get("quote") or ""), K.normalize(text.get(x.get("element") or "", ""))
            found = bool(q) and (q in t or K.in_order(q.split(), t))                # compile's step d test
            print(f"{key} | {u['id']} | {x.get('process_mode') or 'null'} | {x.get('element') or '-'} | quote {'found' if found else ('-' if not x.get('quote') else 'NOT FOUND')} | {x.get('quote') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(C.main(main))
