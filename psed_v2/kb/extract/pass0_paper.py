#!/usr/bin/env python3
"""P133/P144 pass 0: one call per paper: its experiment units, the layout of each table and of each figure panel, against
kb/schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/pass0_paper.py yli18 [--plan]

Prompt (P144, kb/extract/render.py): the instruction (TERMS and the layout definitions quoted from their sources), CODEBOOK.md whole,
the example (another dev paper's gold units and layouts with their sources), TABLES (markdown + cell ids), FIGURES (captions, panel
ids, figures.json curves), the element index, document.md whole. The provider schema (form_pass0.json) constrains the response.
Writes one line (pass 0, section "paper") to kb/records/<pid>.jsonl.
"""
import collections
import json
import re
import sys

import common as C
import render
from lists import TERMS
from export import layouts, LAYOUT_OTHER


def instruction():
    """P144: the terms and layouts quoted from lists.TERMS and ontology.yaml layouts: (P177b; P143 before), the rules of the directive added."""
    terms = "\n".join(f"- {k}: {v}" for k, v in TERMS.items())
    tables = "\n".join(f"- {k}: {d}" for k, d, _ in layouts("table")) + f"\n- {LAYOUT_OTHER}: none of these; describe the layout (description)."   # P177b
    panels = "\n".join(f"- {k}: {d} Example: {ex}." for k, d, ex in layouts("panel")) + f"\n- {LAYOUT_OTHER}: none of these; describe the layout (description)."
    return f"""You read one ALD paper and list its experiment units, the layout of each of its tables and the layout of each figure panel.

TERMS (from the codebook):
{terms}

UNITS: one item per run, specimen, measurement, simulation and model run.
- role: run, specimen, measurement, simulation or model_run; parent: a specimen's run, a measurement's specimen (or run or model run),
  a model run's simulation; null otherwise.
- method: a measurement's ontology method id (required); null on every other unit. One measurement per distinct measurement the paper
  reports, introduced_in = the panel or element that reports it.
- distinguished_by: a unit without a printed name is identified by its distinguishing conditions, each a quantity id, the value and
  the unit as printed (evidence_quote = the words that state them); null when the unit has a printed name.
- list every run even when several share all conditions; list a shared run once when the paper says the samples were coated together.
- evidence_quote (every unit, never null) is copied from the paper: the words that state the deposition of a run, that name a
  specimen, a simulation or a model run.
- parent: never null on a specimen (its run) or a model run (its simulation).
- data: the figures.json ids (FIGURES below: curve, cell and peak ids) whose results belong to this unit, each with its role from
  the caption: measured (read from a specimen), fitted (a line fitted or simulated to match that specimen's measurement) or
  simulated (a model run's result); null when none.
- a least-squares fit to experimental data is not a simulation: its curve is fitted data of the experimental series it fits (data
  role fitted on that series' unit); list no simulation or model run for a fit.
- a unit established by a table row or a grid point: introduced_in = that row's name cell / that cell id, evidence_quote = the
  cell's text.
- introduced_in: the element ids where the unit is named, then every table or figure element that shows it (ELEMENT INDEX).
- structure_class, specimen_class, experiment_kind: only values of the form's enums, only when the paper states them.
- recipe fields of a run (P181, P185, P187): reactant_A, reactant_B, carrier_gas (species ids), process_mode (one of the form's values),
  material (the film material id) and steps (the cycle's step sequence in order, step values), each only when the paper states it for that run, with <field>_quote copied from the paper (the words that state it); null otherwise, never
  inferred. A simulation or model run: the same fields when the paper states them for the model, else null.
- assumptions of a simulation (P188): what the model includes or excludes (its physics, its assumptions), in the paper's words, with
  assumptions_quote copied from the paper; null when the paper states none.

TABLE LAYOUTS (one per table of TABLES below):
{tables}
- unit_name_cells: the cell ids that name the units; units: the unit ids in the order the table gives them.

PANEL LAYOUTS (one per figure panel of FIGURES below):
{panels}
- unit: the one unit of a panel_one_unit panel; axis_quantities and value_quantity: the quantity ids of a point_per_unit panel.
- method: an image panel's (micrograph, photograph, map, spectrum) ontology method id; null otherwise.

Every field is present; null when it does not apply. Answer with JSON matching the form."""


def jobs(pid):
    form = C.schema("form_pass0.json")
    prompt = "\n\n".join([instruction(), "CODEBOOK:\n" + render.codebook(), "EXAMPLE (another paper's gold, in the form):\n" + render.example(pid, form),
                          "TABLES (markdown, then cell ids):\n" + render.tables(pid), "FIGURES (caption, panels: id | type | what it shows, curves: id | panel | series label | x | y | "
                          "conditions):\n" + render.figures(pid), "ELEMENT INDEX (id, kind, locator):\n" + render.index(pid),
                          "PAPER (document.md):\n" + render.document(pid)])
    return [(0, "paper", prompt, C.provider_schema(form), [])]                  # P206b (user): the id fields plain strings again (P202's enums withdrawn); compile drops and lists an unknown id


THINKING = {"thinking_level": "MEDIUM"}                                         # user, P138 (was LOW, P133b); recorded in the line and the cache key


def consistency(pid, obj):
    """P160 B, part of every pass-0 run; P177b (user): per figure panel, compile.bind()'s items on this pass-0 line (no pass-1 records yet:
    pass 0's own data refs, the layout's unit, the panel or figure an introduced_in names, else a derived unit): held by a pass-0 unit,
    by a derived unit, or unbound with its reason (no layout, ambiguous, no unit named, layout other). The invariant's count (the gate's
    'unbound items'); it replaces the curve check, the method-legend flag and the image flag."""
    import compile as K                                                         # P161
    obj = obj if isinstance(obj, dict) else {}
    B = K.bind(pid, obj, None)
    out = []
    for pel, P in B["panels"].items():
        its = P["items"]
        if not its:
            continue
        unb = [it for it in its if not it["unit"]]
        reasons = collections.Counter(it["reason"].split(":")[0] for it in unb)
        out.append(dict(panel=pel, layout=P["layout"], kind=P["kind"], items=len(its), held_pass0=sum(1 for it in its if it["unit"] and it.get("origin") == "pass-0"),
                        held_derived=sum(1 for it in its if it["unit"] and it.get("origin") == "derived"), unbound=len(unb),
                        unit_ids=";".join(sorted({it["unit"] for it in its if it["unit"]})), unbound_ids=";".join(it["ref"] for it in unb),
                        flag=("unbound: " + ", ".join(f"{k} {n}" for k, n in reasons.items())) if unb else ""))
    return out


def model_named(pid, obj):
    """P166 (user), part of every pass-0 run: each ontology model entry (vocab.ENTRIES, type model) whose name or an alias occurs in
    document.md as a whole phrase, case ignored; flagged "model named, no simulation unit" when the pass-0 units hold no simulation."""
    import vocab as V
    doc = render.document(pid)
    units = (obj.get("units") or []) if isinstance(obj, dict) else []
    sims = [u.get("id") for u in units if isinstance(u, dict) and u.get("role") == "simulation"]
    out = []
    for i, e in V.ENTRIES.items():
        if e.get("type") != "model" or e.get("replaced_by"):
            continue
        for t in [e.get("name", "")] + list(e.get("aliases") or []):
            if t and re.search(rf"(?<!\w){re.escape(t)}(?!\w)", doc, re.I):
                out.append(dict(model=i, named=t, simulations=";".join(sims), flag="" if sims else "model named, no simulation unit"))
    return out


DEPOSITION_WORDS = re.compile(r"\b(deposit\w*|grown|grow\w*|growth|coat\w*|ALD|cycles?)\b", re.I)


def measurement_named(pid, obj):
    """P170 (user), part of every pass-0 run, a flag only: a run or specimen unit whose printed name names a measurement-method entry
    (compile.legend_methods: one to three consecutive words, or the name, resolve to a method vocab.METHOD_MEASUREMENT marks) and whose
    evidence quote states no deposition (none of DEPOSITION_WORDS) -> "unit named after a measurement". Nothing is created or removed."""
    import compile as K
    out = []
    for u in (obj.get("units") or []) if isinstance(obj, dict) else []:
        if not isinstance(u, dict) or u.get("role") not in ("run", "specimen"):
            continue
        ms = K.legend_methods(pid, u.get("name_as_printed") or "")
        dep = DEPOSITION_WORDS.search(u.get("evidence_quote") or "")
        out.append(dict(unit=u.get("id"), role=u.get("role"), name=u.get("name_as_printed") or "", methods="; ".join(f"{m}: {w!r}" for m, w in ms.items()),
                        deposition_word=dep.group(0) if dep else "", flag="unit named after a measurement" if ms and not dep else ""))
    return out


def main(arg):
    pid, key = C.resolve(arg)
    if "--check" in sys.argv:                                                   # P160: the consistency check on the latest pass-0 line, no call
        import compile as K
        lines = [json.loads(x) for x in (C.RECORDS / f"{pid}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        bad = K.failed_lines(lines)                                             # P206b (user): a failed pass-0 line is skipped, listed
        if bad:
            print(f"{key}: {K.failed_note(lines, bad)}")
        latest = next(x for n, x in reversed(list(enumerate(lines, 1))) if x["pass"] == 0 and n not in bad)
        rows = consistency(pid, C.loads_json(latest["response"]))
        for r in rows:
            print(f"{key} {r['panel']} {r['layout']}: {r['items']} items, {r['held_pass0']} held by pass 0, {r['held_derived']} by derived units {r['flag']}")
        obj = C.loads_json(latest["response"])
        for r in model_named(pid, obj):                                         # P166
            print(f"{key} model {r['model']} named ({r['named']!r}); simulations: {r['simulations'] or 'none'} {r['flag']}")
        for r in measurement_named(pid, obj):                                   # P170
            if r["flag"]:
                print(f"{key} {r['role']} {r['unit']} ({r['name']!r}): {r['flag']} ({r['methods']})")
        return 0
    if "--plan" in sys.argv:                                                    # the planned call only, no call
        js = jobs(pid)
        C.plan(pid, js, THINKING)
        print(f"{key}: prompt {len(js[0][2])} chars, ~{len(js[0][2]) // 4} tokens")
        return 0
    out, _ = C.run(pid, jobs(pid), THINKING)
    if not out:                                                                 # P206b: a failed call (no unit among the reasons) writes no line
        print(f"{key} pass 0: no line written (a failed call: kb/records/failed_calls.csv)")
        return 1
    obj = C.loads_json(out[0]["response"])
    units = (obj or {}).get("units") or [] if isinstance(obj, dict) else []
    roles = {}
    for it in units:
        roles[it.get("role", "?")] = roles.get(it.get("role", "?"), 0) + 1
    print(f"{key} pass 0: {len(units)} units, by role {roles}; table layouts {len((obj or {}).get('table_layouts') or [])}, "
          f"panel layouts {len((obj or {}).get('panel_layouts') or [])}")
    for r in consistency(pid, obj or {}):                                       # P160 B, P162: the items of a per-unit panel no unit holds
        if r["flag"]:
            print(f"{key} {r['panel']} {r['layout']}: {r['items']} items, {r['held_pass0']} held by pass 0, {r['held_derived']} by derived units: {r['flag']}")
    for r in model_named(pid, obj or {}):                                       # P166: a model the paper names, no simulation unit
        if r["flag"]:
            print(f"{key} model {r['model']} named ({r['named']!r}): {r['flag']}")
    for r in measurement_named(pid, obj or {}):                                 # P170: a unit named after a measurement (flag only)
        if r["flag"]:
            print(f"{key} {r['role']} {r['unit']} ({r['name']!r}): {r['flag']} ({r['methods']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
