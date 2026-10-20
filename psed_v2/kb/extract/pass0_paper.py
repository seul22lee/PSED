#!/usr/bin/env python3
"""P133/P144 pass 0: one call per paper: its experiment units, the layout of each table and of each figure panel, against
kb/schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/pass0_paper.py yli18 [--plan]

Prompt (P144, kb/extract/render.py): the instruction (TERMS and the layout definitions quoted from their sources), CODEBOOK.md whole,
the example (another dev paper's gold units and layouts with their sources), TABLES (markdown + cell ids), FIGURES (captions, panel
ids, figures.json curves), the element index, document.md whole. The provider schema (form_pass0.json) constrains the response.
Writes one line (pass 0, section "paper") to kb/records/<pid>.jsonl.
"""
import sys

import common as C
import render
from lists import TERMS
from export import P143_TABLE_LAYOUTS, P143_PANEL_LAYOUTS


def instruction():
    """P144: the terms and layouts quoted from lists.TERMS and ontology/export.py (P143), the rules of the directive added."""
    terms = "\n".join(f"- {k}: {v}" for k, v in TERMS.items())
    tables = "\n".join(f"- {k}: {d}" for k, d in P143_TABLE_LAYOUTS)
    panels = "\n".join(f"- {k}: {d} Example: {ex}." for k, d, ex in P143_PANEL_LAYOUTS)
    return f"""You read one ALD paper and list its experiment units, the layout of each of its tables and the layout of each figure panel.

TERMS (from the codebook):
{terms}

UNITS: one item per run, specimen, simulation and model run.
- role: run, specimen, simulation or model_run; parent: a specimen's run, a model run's simulation; null otherwise.
- list every run even when several share all conditions; list a shared run once when the paper says the samples were coated together.
- evidence_quote is copied from the paper: the words that say which samples a run made (for a specimen or a model run, the words
  that name it).
- data: the figures.json ids (FIGURES below: curve, cell and peak ids) whose results belong to this unit; null when none.
- a unit established by a table row or a grid point: introduced_in = that row's name cell / that cell id, evidence_quote = the
  cell's text.
- introduced_in: the element ids where the unit is named, then every table or figure element that shows it (ELEMENT INDEX).
- structure_class, specimen_class, experiment_kind: only values of the form's enums, only when the paper states them.

TABLE LAYOUTS (one per table of TABLES below):
{tables}
- unit_name_cells: the cell ids that name the units; units: the unit ids in the order the table gives them.

PANEL LAYOUTS (one per figure panel of FIGURES below):
{panels}
- unit: the one unit of a panel_one_unit panel; axis_quantities and value_quantity: the quantity ids of a point_per_unit panel.

Every field is present; null when it does not apply. Answer with JSON matching the form."""


def jobs(pid):
    form = C.schema("form_pass0.json")
    prompt = "\n\n".join([instruction(), "CODEBOOK:\n" + render.codebook(), "EXAMPLE (another paper's gold, in the form):\n" + render.example(pid, form),
                          "TABLES (markdown, then cell ids):\n" + render.tables(pid), "FIGURES (caption, panels, curves: id | panel | series label | x | y | "
                          "conditions):\n" + render.figures(pid), "ELEMENT INDEX (id, kind, locator):\n" + render.index(pid),
                          "PAPER (document.md):\n" + render.document(pid)])
    return [(0, "paper", prompt, C.provider_schema(form), [])]


THINKING = {"thinking_level": "MEDIUM"}                                         # user, P138 (was LOW, P133b); recorded in the line and the cache key


def main(arg):
    pid, key = C.resolve(arg)
    if "--plan" in sys.argv:                                                    # the planned call only, no call
        js = jobs(pid)
        C.plan(pid, js, THINKING)
        print(f"{key}: prompt {len(js[0][2])} chars, ~{len(js[0][2]) // 4} tokens")
        return 0
    out, _ = C.run(pid, jobs(pid), THINKING)
    obj = C.loads_json(out[0]["response"])
    units = (obj or {}).get("units") or [] if isinstance(obj, dict) else []
    roles = {}
    for it in units:
        roles[it.get("role", "?")] = roles.get(it.get("role", "?"), 0) + 1
    print(f"{key} pass 0: {len(units)} units, by role {roles}; table layouts {len((obj or {}).get('table_layouts') or [])}, "
          f"panel layouts {len((obj or {}).get('panel_layouts') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
