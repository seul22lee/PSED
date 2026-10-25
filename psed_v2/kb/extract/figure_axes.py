#!/usr/bin/env python3
"""P201 (user): the figure-label job, records pass '0ax' (compile.AXES_PASS), one call per paper. The labels are those the figure import
and the legend parsing ask compile.figure_quantity (collect mode: kb/figures_import.py run without writing, then compile.parse_legend on
every curve's series label): each with its panel, kind (x axis, y axis, denominator, series axis, series-axis part, condition key with
its printed value, legend key, legend part) and text as printed. Prompt: the instruction, the CODEBOOK, per figure the caption and its
panel lines (id | type | content), the numbered labels; no quantity id of the import. Answer per label: {id, label_as_printed, answer (a
quantity id of the form, element / species / step for a series axis, series-axis part or legend key, or other), candidate (a short concept
name when other), quote}. A response missing a listed id or answering an unlisted one is a failed call (common.failure). The line
carries the labels (id, panel, kind, text, context); compile.figure_quantity reads the latest 0ax line.

    ~/miniconda3/bin/conda run -n psed310 python psed_v2/kb/extract/figure_axes.py ela03 [--plan] [--labels]
"""
import collections
import sys

import common as C
import compile as K
import pass0_paper as P0
import render

THINKING = P0.THINKING                                                          # pass 0's level
INSTRUCTION = ("Name the concept each axis or legend parameter measures, from its printed label, the caption and the panel text; an "
               "abbreviation, a misspelling or a broken character in the label does not change the concept; if no listed quantity is that "
               "concept, answer other with a candidate.")


def collect(pid):
    """The labels the import and the legend parsing ask figure_quantity, in the order first asked: [dict(id, panel, kind, text, context)]."""
    sys.path.insert(0, str(C.V2 / "kb"))
    import figures_import as FI
    K.COLLECT = {}
    try:
        imp = FI.Importer().paper(pid, write=False)
        axes = K.series_axis(pid)
        for c in imp["curves"]:
            pel = f"fig{c['figure']}{c.get('panel', '')}"
            K.parse_legend(pid, (c.get("series") or {}).get("label_raw", ""), axes.get(pel, ""), pel)
        asked = [(p, k, t, x) for (q, p, k, t), x in K.COLLECT.items() if q == pid]
    finally:
        K.COLLECT = None
    return [dict(id=f"L{n}", panel=p, kind=k, text=t, context=x) for n, (p, k, t, x) in enumerate(asked, 1)]


def figures_block(pid):
    """Per figure: its caption, then its panel lines (id | type | content) as the FIGURES block gives them, without the import's curves."""
    rows, text = C.E.load(pid), C.E.texts(pid)
    inv = render._by_figure(pid)[4]
    out = []
    for r in rows:
        if r["kind"] == "caption" and r["element_id"].startswith("fig"):
            n = r["element_id"][3:].split(".")[0]
            out.append("\n".join([f"FIGURE fig{n}: caption {r['element_id']}: {text[r['element_id']]}"]
                                 + [f"panel fig{n}{x.get('panel', '')} | {x.get('panel_type', '')} | {x.get('content', '')}" for x in inv.get(n, [])]))
    return "\n\n".join(out) or "(no figures)"


def job(pid, labels):
    """(pass, section, prompt, response schema, label ids, no prefix, line fields)."""
    ids = [x["id"] for x in labels]
    answers = sorted(K.AXIS_ANSWERS) + list(K.QUALIFIER_AXES) + ["other"]
    lab = "\n".join(f"{x['id']} | {x['panel']} | {x['kind']} | {x['text']}" + (f" (printed value: {x['context']})" if x["context"] else "") for x in labels)
    prompt = "\n\n".join([
        f"""You read the figures of one ALD paper. {INSTRUCTION}

Rules of this request:
- answer every listed label once, by its id; list no other id;
- answer: a quantity id of the CODEBOOK; for a series axis, a series-axis part or a legend key that names a qualifier (element, species, step)
  rather than a quantity, that qualifier key; else other;
- candidate: a short concept name when the answer is other, else null;
- label_as_printed and quote: the label's text as listed.

Answer with JSON matching the form.""",
        "CODEBOOK:\n" + render.codebook(),
        "FIGURES (caption, then its panels: id | type | content):\n" + figures_block(pid),
        "LABELS (id | panel | kind | text as printed):\n" + (lab or "(none)")])
    schema = {"type": "object", "additionalProperties": False, "required": ["answers"],
              "properties": {"answers": {"type": "array", "items": {
                  "type": "object", "additionalProperties": False, "required": ["id", "label_as_printed", "answer", "candidate", "quote"],
                  "properties": {"id": {"enum": ids or ["none"]}, "label_as_printed": {"type": "string"}, "answer": {"enum": answers},
                                 "candidate": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "quote": {"type": "string"}}}}}}
    ps = C.provider_schema(schema)
    ps["properties"]["answers"]["items"]["properties"]["id"]["enum"] = ids or ["none"]   # P202 (user): set after provider_schema (no length limit)
    return (K.AXES_PASS, "axes", prompt, ps, ids, "", {"labels": labels})


def main(arg):
    pid, key = C.resolve(arg)
    labels = collect(pid)
    j = job(pid, labels)
    print(f"{key}: {len(labels)} labels ({dict(collections.Counter(x['kind'] for x in labels))})")
    if "--labels" in sys.argv:
        for x in labels:
            print(f"  {x['id']} | {x['panel']} | {x['kind']} | {x['text']}" + (f" ({x['context']})" if x["context"] else ""))
    if "--plan" in sys.argv or not labels:
        C.plan(pid, [j], THINKING)
        print(f"{key}: prompt {len(j[2])} chars (~{int(len(j[2]) / 3.1)} tokens)")
        return 0
    out, _ = C.run(pid, [j], THINKING)
    if not out:
        print(f"{key}: no answer line (failed calls listed in records/failed_calls.csv)")
        return 1
    got = C.loads_json(out[0]["response"]).get("answers") or []
    print(f"{key}: answers {dict(collections.Counter('other' if a.get('answer') == 'other' else 'qualifier' if a.get('answer') in K.QUALIFIER_AXES else 'quantity' if a.get('answer') in K.AXIS_ANSWERS else 'no id' for a in got))}")
    return 0


if __name__ == "__main__":
    sys.exit(C.main(main))
