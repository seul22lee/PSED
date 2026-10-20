#!/usr/bin/env python3
"""P133 pass 0: one call per paper, the things it names (specimens, runs, simulations, cited works), against schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass0_paper.py yli18

Prompt: the instruction, the pass-0 form, the element index of pilot/<pid>.elements.csv (id, kind, locator: the ids introduced_in
names) and the whole ingest/final/<pid>/document.md. Writes one line (pass 0, section "paper") to records/<pid>.jsonl.
"""
import json
import sys

import common as C

INSTRUCTION = """You read one ALD paper and list its experiment units: every run, specimen, simulation and model run it reports.
One item per unit:
- id: a short id you assign, unique in the paper (r1, s1, sim1, m1, ...); pass 1 uses it as a record's parent;
- name_as_printed: the name exactly as the paper prints it (copied, never rewritten or invented);
- role: one of run, specimen, simulation, model_run.
  A run is one deposition the paper performs; samples coated in separate depositions are separate runs even with the same
  chemistry, temperature and structure; samples coated together share one run.
  A specimen is one physical sample measured; parent = its run.
  A simulation is one model; two solution methods or approximations of the same model are the same simulation.
  A model_run is one set of inputs whose result the paper reports (a curve, a table row); parent = its simulation;
- parent: as defined per role above; null when the role has none;
- evidence_quote (runs): the words that say which samples the run made, copied verbatim from the paper;
- curves (runs, specimens, model runs): the ids from CURVES below that show this unit; null when none does;
- every field is present in every item; null when it does not apply;
- structure_class, specimen_class, experiment_kind: only values from the form's enums, and only when the paper states them;
- introduced_in: the id(s) of the element(s) where the unit is first named, then every figure or table element that shows it,
  taken from the element index below.
Sets of units (a series in a figure, replicates) and cited works are not items.
Answer with JSON matching the form."""


def example(pid, form):
    """P136b/P138/P139/P143b: one example list in the pass-0 form, from the gold tree of the last dev paper in index order other than
    pid (never held-out) whose gold has runs, specimens, a simulation and model runs: at most two items per role (run = a deposition
    activity, specimen = an entity with a deposition above it, simulation = a simulation activity, model_run = an entity with a
    simulation above it), id = role prefix + number, name = label_as_printed, introduced_in = the row's evidence, parent = the item id
    of the nearest deposition (specimen) or simulation (model_run) when that is an item; every field present (null when not given);
    validated against form_pass0.json."""
    import csv
    from jsonschema import Draft202012Validator
    PRE = {"run": "r", "simulation": "sim", "specimen": "s", "model_run": "m"}
    for p in [p for p in reversed(list(C.E.PAPERS)) if p != pid and p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        rows = [r for r in csv.DictReader(f.open(encoding="utf-8")) if "#" not in r["fact_id"]] if f.exists() else []
        R = {r["fact_id"]: r for r in rows}

        def up(r, kind):
            x = r["parent"]
            while x in R:
                if R[x]["type"] == "activity" and R[x]["kind"] == kind:
                    return x
                x = R[x]["parent"]
            return ""
        role = lambda r: ("run" if r["type"] == "activity" and r["kind"] == "deposition" else "simulation" if r["type"] == "activity" and r["kind"] == "simulation"
                          else "model_run" if r["type"] == "entity" and up(r, "simulation") else "specimen" if r["type"] == "entity" and up(r, "deposition") else "")
        items, n, ids = [], {}, {}
        for r in rows:
            k = role(r)
            if k and r["label_as_printed"] and r["evidence"] and n.get(k, 0) < 2:
                n[k] = n.get(k, 0) + 1
                ids[r["fact_id"]] = f"{PRE[k]}{n[k]}"
                items.append(dict(id=ids[r["fact_id"]], name_as_printed=r["label_as_printed"], role=k, introduced_in=r["evidence"].split(";"),
                                  _gp=up(r, "deposition") if k == "specimen" else up(r, "simulation") if k == "model_run" else ""))
        for it in items:
            gp = it.pop("_gp")
            if gp in ids:
                it["parent"] = ids[gp]
        items = [{k: it.get(k) for k in form["items"]["required"]} for it in items]   # P139: every field present, null when not given
        if {"run", "specimen", "simulation", "model_run"} <= set(n) and not list(Draft202012Validator(form).iter_errors(items)):
            return json.dumps(items, ensure_ascii=False)
    return "[]"


def curves(pid):
    """P143b: the figures.json curves of the paper as 'id | figure panel | kind | series label | x -> y' lines (for the curves field)."""
    p = C.V2 / "kb" / f"{pid}.figures.json"
    if not p.exists():
        return "(no figures.json)"
    F = json.loads(p.read_text(encoding="utf-8"))
    return "\n".join(f"{c['id']} | fig{c['figure']}{c.get('panel', '')} | {c['kind']} | {c.get('series', {}).get('label_raw', '')} | "
                     f"{c['x'].get('quantity', '')} -> {c['y'].get('quantity', '')}" for c in F.get("curves", [])) or "(none)"


def jobs(pid):
    form = C.schema("form_pass0.json")
    index = "\n".join(f"{r['element_id']}\t{r['kind']}\t{r['locator']}" for r in C.E.load(pid))
    doc = (C.V2 / "ingest" / "final" / pid / "document.md").read_text(encoding="utf-8")
    prompt = "\n\n".join([INSTRUCTION, "FORM (JSON Schema):\n" + json.dumps(form, ensure_ascii=False, separators=(",", ":")),
                          "EXAMPLE (another paper, in the form):\n" + example(pid, form),
                          "ELEMENT INDEX (id, kind, locator):\n" + index,
                          "CURVES (figures.json: id | figure panel | kind | series label | x -> y), for the curves field:\n" + curves(pid),   # P143b
                          "PAPER (document.md):\n" + doc])
    return [(0, "paper", prompt, C.provider_schema(form), [])]


THINKING = {"thinking_level": "MEDIUM"}                                         # user, P138 (was LOW, P133b); recorded in the line and the cache key


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
