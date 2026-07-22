"""
bench_extract.py
----------------
Run ONE self-contained, ontology-grounded, TEXT-ONLY extraction per
(paper x scope). The only variable across runs is the input text scope, so the
result isolates "how much does scope matter".

  dry-run (default):  builds every prompt, writes it to prompts/, prints a cost
                      estimate. NO LLM call, no keys needed.
  --run            :  actually calls Gemini (gemini-2.5-flash) and writes
                      out/<paper>__<scope>.json.   <-- you run this step.

Reuses the same client/keys as 0604_kg (dotenv -> GOOGLE_API_KEY).
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
SLICES = HERE / "slices"
PROMPTS = HERE / "prompts"
OUT = HERE / "out"
ONTO = json.loads((HERE.parent.parent / "0706_ontology" / "ald_ontology.json").read_text())

SCOPES = ["abstract", "abstract_conclusion", "evidence", "full"]

# quantities the benchmark cares about (text-stated numbers), by canonical name
BENCH_QUANTITIES = [
    "deposition_temperature", "temperature", "growth_per_cycle", "film_thickness",
    "sticking_probability", "initial_sticking_coefficient", "recombination_probability",
    "reaction_probability", "exposure", "partial_pressure", "total_pressure",
    "pulse_time", "purge_time", "cycle_number", "aspect_ratio", "equivalent_aspect_ratio",
    "coated_aspect_ratio", "step_coverage", "penetration_depth_50", "mean_free_path",
    "knudsen_number", "effective_diffusion_coefficient", "surface_area", "pore_diameter",
]


def ontology_vocab():
    mats = [m["formula"] for m in ONTO["individuals"].get("materials", []) if m.get("formula")]
    procs = [p["id"] for p in ONTO["classes"] if p.get("parent") == "ProcessType"]
    q_alias = {}
    for q in ONTO["quantity_kinds"]:
        if q["id"] in BENCH_QUANTITIES:
            q_alias[q["id"]] = q.get("aliases", [])[:3]
    return mats, procs, q_alias


def build_prompt(text):
    mats, procs, q_alias = ontology_vocab()
    qlist = "\n".join(f"    - {k}  (aka: {', '.join(a)})" for k, a in q_alias.items())
    return f"""You are an information-extraction system for atomic layer deposition (ALD) papers.
Extract ONLY what is explicitly stated in the TEXT below. Do NOT infer or use outside knowledge.
Use null / empty list when something is not stated. Return ONLY valid JSON.

Use these CANONICAL vocabularies where applicable:
  materials (deposited film, use formula): {', '.join(mats)}
  process_types: {', '.join(procs)}
  quantities (map any stated numeric quantity to its canonical name):
{qlist}

Output schema (return exactly this shape):
{{
  "study_profile": {{
    "materials_deposited": [],
    "process_types": [],
    "structures_or_apparatus": [],
    "precursors": [],
    "coreactants": [],
    "reactor_types": [],
    "deposition_temperature_C": {{"min": null, "max": null}}
  }},
  "quantitative_mentions": [
    {{"quantity": "<canonical name>", "value": <number>, "unit": "<unit>"}}
  ],
  "claims": ["<short qualitative finding explicitly stated>"]
}}

TEXT
----
{text}
"""


def dry_run():
    PROMPTS.mkdir(exist_ok=True)
    index = json.loads((SLICES / "index.json").read_text())
    total_chars = 0
    print("DRY RUN — building prompts, no LLM calls\n")
    print(f"{'paper':14}{'scope':22}{'input chars':>12}  prompt file")
    jobs = 0
    for rec in index:
        pid = rec["paper_id"]
        for scope in SCOPES:
            slice_f = SLICES / pid / f"{scope}.txt"
            text = slice_f.read_text() if slice_f.exists() else ""
            if scope == "abstract" and not text.strip():
                print(f"{pid:14}{scope:22}{'(skip: empty)':>12}")
                continue
            prompt = build_prompt(text)
            (PROMPTS / f"{pid}__{scope}.txt").write_text(prompt)
            total_chars += len(prompt)
            jobs += 1
            print(f"{pid:14}{scope:22}{len(text):>12}  prompts/{pid}__{scope}.txt")
    # ~4 chars/token; gemini-2.5-flash input ~ $0.30 / 1M tokens (output tiny)
    toks = total_chars / 4
    print(f"\njobs: {jobs}   ~{toks/1000:.0f}K input tokens total   "
          f"est. cost < ${toks/1e6*0.30 + 0.02:.2f} on gemini-2.5-flash")
    print("prompts written to prompts/ for inspection.")
    print("\nTo execute the extractions yourself:")
    print("    python bench_extract.py --run          # needs GOOGLE_API_KEY in .env")
    print("then score with:  python bench_score.py")


def live_run():
    import os
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    # key lives in 0604_kg/.env (sibling subtree); load it explicitly
    env_path = HERE.parent.parent / "0604_kg" / ".env"
    load_dotenv(env_path if env_path.exists() else None)
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("GOOGLE_API_KEY not found in environment/.env")
    client = genai.Client(api_key=key)
    OUT.mkdir(exist_ok=True)
    index = json.loads((SLICES / "index.json").read_text())
    for rec in index:
        pid = rec["paper_id"]
        for scope in SCOPES:
            slice_f = SLICES / pid / f"{scope}.txt"
            text = slice_f.read_text() if slice_f.exists() else ""
            if scope == "abstract" and not text.strip():
                continue
            out_f = OUT / f"{pid}__{scope}.json"
            if out_f.exists():
                print(f"[skip] {out_f.name} exists"); continue
            print(f"[llm] {pid} / {scope} ({len(text)} chars)...")
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=build_prompt(text),
                config=types.GenerateContentConfig(
                    temperature=0, response_mime_type="application/json"),
            )
            data = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
            out_f.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"       -> {out_f.name}")
    print("done. now: python bench_score.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="actually call the LLM (costs)")
    a = ap.parse_args()
    live_run() if a.run else dry_run()
