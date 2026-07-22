"""
s07_experiment.py  (Phase B1)
-----------------------------
Per-figure experiment extraction, ontology-grounded. Each plotted series -> one
raw experiment, with fields emitted as CANONICAL ontology ids (materials by
formula, quantities by canonical name), inheriting the paper study_profile as
shared context. Granularity/normalisation/relevance are handled in s08.

Reuses 0604_kg's 05_enrich_figures output (caption + figure_contexts + series +
x/y labels). LLM (gemini). Resumable (skips existing). YOU authorised runs.

Output: output/<pid>/experiments/<figure_id>.json  (list of experiments)
"""
import json
from lib import papers, enrich_dir, OUTPUT, vocab, run_llm


def build_prompt(profile, fig):
    mats, procs, quant = vocab()
    qlines = "\n".join(
        f"  {qid}" + (f" (aka {', '.join(al)})" if al else "") + (f" [{unit}]" if unit else "")
        for qid, al, unit in quant)
    ctx = "\n".join(fig.get("figure_contexts", []) or [])
    sub = fig.get("subfigure_contexts", [])
    if isinstance(sub, dict):
        sub = [x for v in sub.values() for x in (v if isinstance(v, list) else [v])]
    ctx += "\n" + "\n".join(map(str, sub or []))
    return f"""You extract atomic layer deposition (ALD) experiments from ONE figure.
Each plotted SERIES = one experiment. Extract ONLY what the caption / context /
axis labels / series names state. Use null / [] when not stated.
Map every material to a canonical FORMULA and every quantity to a canonical NAME
from the vocabularies below. Return ONLY JSON.

PAPER CONTEXT (shared conditions — inherit unless a series overrides; do NOT add
materials that are not deposited films in THIS study):
{json.dumps(profile, ensure_ascii=False)}

VOCAB — materials (formula): {', '.join(mats)}
VOCAB — process_types: {', '.join(procs)}
VOCAB — quantities (canonical <- aliases [unit]):
{qlines}

FIGURE
  figure_id: {fig.get('figure_id')}
  caption: {fig.get('caption')}
  x_label: {fig.get('x_label')}   y_label: {fig.get('y_label')}
  series: {fig.get('series')}
  context:
{ctx}

For EACH series output an experiment. Put the X-AXIS quantity in "independent",
the plotted Y in "dependent", and every FIXED condition (including the value in
the series label, e.g. "500 nm" -> feature_height) in "controlled".
Tag pulse_time / purge_time / partial_pressure / exposure with of_reactant
("A_precursor" or "B_coreactant") when known.

{{
  "experiments": [
    {{
      "series_name": "",
      "material_deposited": "",
      "process_type": "",
      "structure_type": "",
      "precursors": [],
      "coreactants": [],
      "is_model_result": false,
      "variables": {{
        "independent": [{{"quantity": "", "symbol": "", "value": null, "unit": "", "of_reactant": null}}],
        "controlled":  [{{"quantity": "", "symbol": "", "value": null, "unit": "", "of_reactant": null}}],
        "dependent":   [{{"quantity": "", "symbol": "", "unit": ""}}]
      }}
    }}
  ]
}}
"""


def main():
    for p in papers():
        pid, pdir = p["pid"], p["dir"]
        prof_f = OUTPUT / pid / "profile.json"
        profile = json.loads(prof_f.read_text()) if prof_f.exists() else {}
        edir = enrich_dir(pdir)
        if not edir.exists():
            print(f"[skip] {pid}: no enriched figures"); continue
        out_dir = OUTPUT / pid / "experiments"
        out_dir.mkdir(parents=True, exist_ok=True)
        for ef in sorted(edir.glob("figure-*.json")):
            fig = json.loads(ef.read_text())
            out_f = out_dir / ef.name
            if out_f.exists():
                print(f"[skip] {pid}/{ef.stem} exists"); continue
            print(f"[llm] {pid}/{ef.stem}  series={fig.get('series')}")
            res = run_llm(build_prompt(profile, fig))
            exps = res.get("experiments", [])
            for e in exps:                      # keep provenance
                e["provenance"] = {"figure_id": fig.get("figure_id"),
                                   "caption": fig.get("caption"),
                                   "plot_data_path": fig.get("plot_data_path"),
                                   "paper": pid}
            out_f.write_text(json.dumps(exps, indent=2, ensure_ascii=False))
            print(f"       -> {ef.name}: {len(exps)} experiments")
    print("done s07. next: s08_resolve.py")


if __name__ == "__main__":
    main()
