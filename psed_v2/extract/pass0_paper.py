#!/usr/bin/env python3
"""P133 pass 0: one call per paper, the things it names (specimens, runs, simulations, cited works), against schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass0_paper.py yli18

Prompt: the instruction, the pass-0 form, the element index of pilot/<pid>.elements.csv (id, kind, locator: the ids introduced_in
names) and the whole ingest/final/<pid>/document.md. Writes one line (pass 0, section "paper") to records/<pid>.jsonl.
"""
import json

import common as C

INSTRUCTION = """You read one ALD paper and list every specimen, run, simulation and cited work it names.
One item per named thing:
- name_as_printed: the name exactly as the paper prints it (copied, never rewritten or invented);
- role: one of specimen, run, simulation, cited_work;
- structure_class, specimen_class, experiment_kind: only values from the form's enums, and only when the paper states them;
- introduced_in: the id(s) of the element(s) where the thing is first named, taken from the element index below.
Answer with JSON matching the form."""


def jobs(pid):
    form = C.schema("form_pass0.json")
    index = "\n".join(f"{r['element_id']}\t{r['kind']}\t{r['locator']}" for r in C.E.load(pid))
    doc = (C.V2 / "ingest" / "final" / pid / "document.md").read_text(encoding="utf-8")
    prompt = "\n\n".join([INSTRUCTION, "FORM (JSON Schema):\n" + json.dumps(form, ensure_ascii=False, separators=(",", ":")),
                          "ELEMENT INDEX (id, kind, locator):\n" + index, "PAPER (document.md):\n" + doc])
    return [(0, "paper", prompt, C.provider_schema(form), [])]


def main(arg):
    pid, key = C.resolve(arg)
    out, _ = C.run(pid, jobs(pid))
    items = C.loads_json(out[0]["response"])
    roles = {}
    for it in items if isinstance(items, list) else []:
        roles[it.get("role", "?")] = roles.get(it.get("role", "?"), 0) + 1
    print(f"{key} pass 0: {len(items) if isinstance(items, list) else 'not a list'} items, by role {roles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
