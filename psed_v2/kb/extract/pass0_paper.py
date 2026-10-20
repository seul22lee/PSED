#!/usr/bin/env python3
"""P133 pass 0: one call per paper, the things it names (specimens, runs, simulations, cited works), against schema/form_pass0.json.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/extract/pass0_paper.py yli18

Prompt: the instruction, the pass-0 form, the element index of pilot/<pid>.elements.csv (id, kind, locator: the ids introduced_in
names) and the whole ingest/final/<pid>/document.md. Writes one line (pass 0, section "paper") to records/<pid>.jsonl.
"""
import json
import sys

import common as C

INSTRUCTION = """You read one ALD paper and list every specimen, run, simulation, model run, series and cited work it names.
One item per named thing:
- id: a short id you assign, unique in the paper (r1, s1, sim1, ser1, c1, ...); pass 1 uses it as a record's parent;
- name_as_printed: the name exactly as the paper prints it (copied, never rewritten or invented);
- role: one of specimen, run, simulation, model_run, series, cited_work.
  A run is one deposition the paper performs; samples coated in separate depositions are separate runs even with the same
  chemistry, temperature and structure; samples coated together share one run.
  A specimen is one physical sample measured; parent = its run.
  A simulation is one model; two solution methods or approximations of the same model are the same simulation.
  A model_run is one set of inputs whose result the paper reports (a curve, a table row); parent = its simulation.
  A series is a figure's set of specimens or model runs varying one quantity; members = the specimen or model_run ids it compares;
  parent = the simulation, run or specimen it belongs to (null only when the paper gives none).
  A cited work is another publication the paper names;
- parent: as defined per role above; null when the role has none;
- evidence_quote (runs): the words that say which samples the run made, copied verbatim from the paper;
- every field is present in every item; null when it does not apply;
- structure_class, specimen_class, experiment_kind: only values from the form's enums, and only when the paper states them;
- introduced_in: the id(s) of the element(s) where the thing is first named, then every figure or table element that shows it,
  taken from the element index below.
Answer with JSON matching the form."""


def example(pid, form):
    """P136b/P138/P139: one example list in the pass-0 form, from the gold tree of the last dev paper in index order other than pid
    (never held-out) whose gold has a series comparison: at most two items per role (run = a deposition activity, simulation =
    a simulation activity, specimen = an entity directly under a deposition, series = a comparison of kind series, cited_work = a
    cited tree row), id = role letter + number, name = label_as_printed, introduced_in = the row's evidence, parent = the item id of
    the gold parent (specimen: its deposition; series: the parent of its first member) when that is an item; validated against
    form_pass0.json."""
    import csv
    from jsonschema import Draft202012Validator
    PRE = {"run": "r", "simulation": "sim", "specimen": "s", "series": "ser", "cited_work": "c"}
    for p in [p for p in reversed(list(C.E.PAPERS)) if p != pid and p not in C.HELD_OUT]:
        f = C.V2 / "kb" / "pilot" / f"{p}.facts.csv"
        rows = [r for r in csv.DictReader(f.open(encoding="utf-8")) if "#" not in r["fact_id"]] if f.exists() else []
        R = {r["fact_id"]: r for r in rows}
        role = lambda r: ("run" if r["type"] == "activity" and r["kind"] == "deposition" else "simulation" if r["type"] == "activity" and r["kind"] == "simulation"
                          else "specimen" if r["type"] == "entity" and R.get(r["parent"], {}).get("kind") == "deposition"
                          else "series" if r["type"] == "comparison" and r["kind"] == "series" else "cited_work" if r["type"] == "cited" else "")
        items, n, ids = [], {}, {}
        for r in rows:
            k = role(r)
            if k and r["label_as_printed"] and r["evidence"] and n.get(k, 0) < 2:
                n[k] = n.get(k, 0) + 1
                ids[r["fact_id"]] = f"{PRE[k]}{n[k]}"
                gp = r["parent"] if k == "specimen" else next((R[m]["parent"] for m in r["links"].split(";")[1:] if m in R), "") if k == "series" else ""
                items.append(dict(id=ids[r["fact_id"]], name_as_printed=r["label_as_printed"], role=k, introduced_in=r["evidence"].split(";"), _gp=gp))
        for it in items:
            gp = it.pop("_gp")
            if gp in ids:
                it["parent"] = ids[gp]
        items = [{k: it.get(k) for k in form["items"]["required"]} for it in items]   # P139: every field present, null when not given
        if "series" in n and not list(Draft202012Validator(form).iter_errors(items)):
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
