#!/usr/bin/env python3
"""P184 (user): the pass-0 extension, one call per paper. Input: the paper as pass 0 reads it (CODEBOOK, TABLES, FIGURES with every
figures.json panel, ELEMENT INDEX, document.md) and its current pass-0 units; output: the units missing under the P184 TERMS (runs,
specimens, measurements; a simulation or model run too) with distinguished_by, introduced_in, evidence_quote, and the method of each
image panel. The response holds only the new units: the current ones stay as they are (asserted: the merge keeps every current unit
byte-identical; a new id that repeats a current one is listed and left out). One records line of pass compile.EXTEND_PASS; compile
adds its units to pass 0's.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/pass0_extend.py yli18 [--plan]
"""
import collections
import json
import sys

import common as C
import compile as K
import pass0_paper as P0
import process_mode_fill as PM
import render
from lists import TERMS

THINKING = P0.THINKING                                                          # pass 0's level
IMAGE_TYPES = ("micrograph", "photo", "map", "spectrum")                       # figures.json inventory panel types that are images


def image_panels(pid):
    """The figure panel element ids whose figures.json inventory type is an image (IMAGE_TYPES)."""
    ids = {r["element_id"] for r in C.E.load(pid)}
    return [e for e in (f"fig{x['figure']}{x.get('panel', '')}" for x in render._figures_json(pid).get("inventory", [])
                        if x.get("panel_type") in IMAGE_TYPES) if e in ids]


def instruction():
    terms = "\n".join(f"- {k}: {v}" for k, v in TERMS.items())
    units = P0.instruction().split("UNITS:", 1)[1].split("TABLE LAYOUTS", 1)[0].strip()
    return f"""You read one ALD paper whose experiment units were listed before (CURRENT UNITS below) and list the units missing from that
list under the TERMS below: runs, specimens and measurements (a simulation or a model run too, if one is missing). Then give the method
of each image panel (IMAGE PANELS).

TERMS (from the codebook):
{terms}

UNITS: {units}

Rules of this request:
- list only units that CURRENT UNITS does not hold; never repeat, change or replace a current unit;
- a new unit's id is new (none of the CURRENT UNITS ids); its parent is a current unit's id or a new unit's id;
- a unit without a printed name: distinguished_by (its distinguishing conditions), evidence_quote = the words that state them;
- IMAGE PANELS: for each listed panel, the ontology method id that made the image, null when the paper names none.

Every field is present; null when it does not apply. Answer with JSON matching the form."""


def job(pid):
    """(pass, section, prompt, response schema, element ids)."""
    form = C.schema("form_pass0.json")
    item = form["properties"]["units"]["items"]                                 # P206b: a plain array (nullable before)
    _, _, units = PM.pass0_line(pid)
    cur = "\n".join(json.dumps({**{k: u.get(k) for k in ("id", "role", "parent", "name_as_printed", "introduced_in")},
                                "data": [d.get("id") for d in u.get("data") or [] if isinstance(d, dict)] or None}, ensure_ascii=False) for u in units)
    panels = image_panels(pid)
    methods = sorted(m for m, x in K.V.METHOD_MEASUREMENT.items() if x)
    prompt = "\n\n".join([instruction(), "CODEBOOK:\n" + render.codebook(), "TABLES (markdown, then cell ids):\n" + render.tables(pid),
                          "FIGURES (caption, panels: id | type | what it shows, curves: id | panel | series label | x | y | conditions):\n" + render.figures(pid),
                          "ELEMENT INDEX (id, kind, locator):\n" + render.index(pid), "PAPER (document.md):\n" + render.document(pid),
                          "CURRENT UNITS (one per line):\n" + cur, "IMAGE PANELS:\n" + (", ".join(panels) or "(none)")])
    schema = {"type": "object", "additionalProperties": False, "required": ["units", "panel_methods"], "$defs": form["$defs"],
              "properties": {"units": {"type": "array", "items": item},
                             "panel_methods": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["panel", "method"],
                                                                          "properties": {"panel": {"enum": panels or ["none"]},
                                                                                         "method": {"anyOf": [{"enum": methods}, {"type": "null"}]}}}}}}
    return (K.EXTEND_PASS, "units", prompt, C.provider_schema(schema), [])      # P206b (user): the id fields plain strings, as pass 0's


def main(arg):
    pid, key = C.resolve(arg)
    j = job(pid)
    if "--plan" in sys.argv:
        C.plan(pid, [j], THINKING)
        print(f"{key}: prompt {len(j[2])} chars (~{int(len(j[2]) / 3.1)} tokens)")
        return 0
    _, _, units = PM.pass0_line(pid)                                            # P187: the current units, read before the new line is written
    out, _ = C.run(pid, [j], THINKING)
    resp = C.loads_json(out[0]["response"])
    have = {u.get("id") for u in units}
    new = [u for u in resp.get("units") or [] if isinstance(u, dict)]
    rep = [u.get("id") for u in new if u.get("id") in have]
    merged = list(units) + [u for u in new if u.get("id") not in have]
    assert json.dumps(merged[:len(units)], sort_keys=True) == json.dumps(units, sort_keys=True), "current units changed"
    print(f"{key}: {len(new)} new units ({dict(collections.Counter(u.get('role') for u in new))}); repeated current ids (left out): {rep or 'none'}; "
          f"panel methods {sum(1 for x in resp.get('panel_methods') or [] if x.get('method'))} / {len(resp.get('panel_methods') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(C.main(main))
