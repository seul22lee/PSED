#!/usr/bin/env python3
"""P133 pass 0: one call per paper, the things it names (specimens, runs, simulations, cited works), against schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass0_paper.py yli18

Prompt: the instruction, the pass-0 form, the element index of pilot/<pid>.elements.csv (id, kind, locator: the ids introduced_in
names) and the whole ingest/final/<pid>/document.md. Writes one line (pass 0, section "paper") to records/<pid>.jsonl.
"""
import json
import sys

import common as C

INSTRUCTION = """You read one ALD paper and list every specimen, run, simulation and cited work it names.
One item per named thing:
- name_as_printed: the name exactly as the paper prints it (copied, never rewritten or invented);
- role: one of specimen, run, simulation, cited_work. A run is one deposition sequence: a reactant pair at a temperature on a
  structure. A simulation is a model the paper solves, one item per model. A specimen is a physical sample the paper measures (a
  coated structure, a film, a substrate piece). A cited work is another publication the paper names;
- structure_class, specimen_class, experiment_kind: only values from the form's enums, and only when the paper states them;
- introduced_in: the id(s) of the element(s) where the thing is first named, then every figure or table element that shows it,
  taken from the element index below.
Answer with JSON matching the form."""


def example(pid, form):
    """P136b: one example list in the pass-0 form, from the gold tree of the first dev paper other than pid (never held-out) that has
    deposition and simulation activities: at most two items per role (run = a deposition activity, simulation = a simulation
    activity, specimen = an entity directly under a deposition, cited_work = a cited tree row), name = label_as_printed,
    introduced_in = the row's evidence; validated against form_pass0.json."""
    import csv
    from jsonschema import Draft202012Validator
    for p in [p for p in C.E.PAPERS if p != pid and p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        rows = [r for r in csv.DictReader(f.open(encoding="utf-8")) if "#" not in r["fact_id"]] if f.exists() else []
        R = {r["fact_id"]: r for r in rows}
        role = lambda r: ("run" if r["type"] == "activity" and r["kind"] == "deposition" else "simulation" if r["type"] == "activity" and r["kind"] == "simulation"
                          else "specimen" if r["type"] == "entity" and R.get(r["parent"], {}).get("kind") == "deposition" else "cited_work" if r["type"] == "cited" else "")
        items, n = [], {}
        for r in rows:
            k = role(r)
            if k and r["label_as_printed"] and r["evidence"] and n.get(k, 0) < 2:
                n[k] = n.get(k, 0) + 1
                items.append(dict(name_as_printed=r["label_as_printed"], role=k, introduced_in=r["evidence"].split(";")))
        if {"run", "simulation"} <= set(n) and not list(Draft202012Validator(form).iter_errors(items)):
            return json.dumps(items, ensure_ascii=False)
    return "[]"


def jobs(pid):
    form = C.schema("form_pass0.json")
    index = "\n".join(f"{r['element_id']}\t{r['kind']}\t{r['locator']}" for r in C.E.load(pid))
    doc = (C.V2 / "ingest" / "final" / pid / "document.md").read_text(encoding="utf-8")
    prompt = "\n\n".join([INSTRUCTION, "FORM (JSON Schema):\n" + json.dumps(form, ensure_ascii=False, separators=(",", ":")),
                          "EXAMPLE (another paper, in the form):\n" + example(pid, form),
                          "ELEMENT INDEX (id, kind, locator):\n" + index, "PAPER (document.md):\n" + doc])
    return [(0, "paper", prompt, C.provider_schema(form), [])]


THINKING = {"thinking_level": "LOW"}                                            # user, P133b: as pass 1; recorded in the line and the cache key


def main(arg):
    pid, key = C.resolve(arg)
    if "--plan" in sys.argv:                                                    # the planned call only, no call
        C.plan(pid, jobs(pid), THINKING)
        return 0
    out, _ = C.run(pid, jobs(pid), THINKING)
    items = C.loads_json(out[0]["response"])
    roles = {}
    for it in items if isinstance(items, list) else []:
        roles[it.get("role", "?")] = roles.get(it.get("role", "?"), 0) + 1
    print(f"{key} pass 0: {len(items) if isinstance(items, list) else 'not a list'} items, by role {roles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
