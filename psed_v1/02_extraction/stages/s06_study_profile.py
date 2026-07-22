"""
s06_study_profile.py  (Phase B1 / C5)
-------------------------------------
Paper-level study profile on the EVIDENCE scope: material system, process type,
reactor, precursors/coreactants. Serves as shared context for per-figure
experiments and the RELEVANCE anchor.

For the benchmarked papers it reuses the evidence extraction already produced;
for NEW papers it extracts the profile itself (LLM on the evidence region) — so
the stage scales to any paper processed through 05_enrich.

Output: output/<pid>/profile.json
"""
import json
from lib import papers, BENCH, OUTPUT, read_evidence, run_llm, vocab, canon_material, canon_process


def build_prompt(evidence):
    mats, procs, _ = vocab()
    return f"""Extract the STUDY PROFILE of this atomic layer deposition (ALD) paper from the
evidence below (abstract, conclusion, figure/table captions and their context).
List only the DEPOSITED FILM materials actually studied in THIS paper (not
background/intro examples). Use canonical formulas. Return ONLY JSON.

materials vocab: {', '.join(mats)}
process_types: {', '.join(procs)}

{{
  "materials_deposited": [], "process_types": [], "reactor_types": [],
  "precursors": [], "coreactants": [],
  "deposition_temperature_C": {{"min": null, "max": null}}
}}

EVIDENCE
--------
{evidence[:14000]}
"""


def main():
    for p in papers():
        pid, pdir = p["pid"], p["dir"]
        ev = BENCH / "out" / f"{pid}__evidence.json"
        if ev.exists():                                   # benchmarked papers: reuse
            prof = json.loads(ev.read_text()).get("study_profile", {}) or {}
        else:                                             # new papers: extract now
            evidence = read_evidence(pdir)
            if not evidence.strip():
                print(f"[skip] {pid}: no evidence"); continue
            print(f"[llm] {pid}: extracting study profile...")
            prof = run_llm(build_prompt(evidence))
        prof["studied_materials_canonical"] = sorted(
            {canon_material(m) or m for m in prof.get("materials_deposited", [])})
        prof["process_types_canonical"] = sorted(
            {canon_process(x) or x for x in prof.get("process_types", [])})
        d = OUTPUT / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "profile.json").write_text(json.dumps(prof, indent=2, ensure_ascii=False))
        print(f"[profile] {pid}: materials={prof['studied_materials_canonical']} "
              f"process={prof['process_types_canonical']}")


if __name__ == "__main__":
    main()
