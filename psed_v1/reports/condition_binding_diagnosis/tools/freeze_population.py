#!/usr/bin/env python3
"""READ-ONLY. §A — freeze the audit population before sampling.

Writes corpus_population_manifest.json. Touches nothing else.
"""
import paths as P
import json, glob, hashlib, subprocess, os
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # psed_v1/
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = P.PAPERS
EX = P.PAPERS


def sh(*a):
    try:
        return subprocess.check_output(a, cwd=str(REPO), stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def sha(p):
    p = Path(p)
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def main():
    papers = sorted((json.loads((REPO / "03_corpus" / "extraction_manifest.json").read_text())
                     .get("papers") or {}).keys())
    records, checks, per_paper = [], {}, {}
    kinds = Counter(); rel = Counter(); gran = Counter()
    for doi in papers:
        ep = P.resolved_json(doi, "experiments")
        sp = P.resolved_json(doi, "series")
        cp = P.curves_json(doi)
        exps = json.loads(ep.read_text()) if ep.exists() else []
        ser = json.loads(sp.read_text()) if sp.exists() else []
        curves = (json.loads(cp.read_text()).get("curves", []) if cp.exists() else [])
        for f in (ep, sp, cp, P.extracted_dir(doi) / "figure_data.json", P.extracted_dir(doi) / "records.json",
                  P.extracted_dir(doi) / "pressure.json", P.extracted_dir(doi) / "card.json",
                  P.extracted_dir(doi) / "geometry.json", P.extracted_dir(doi) / "document.md"):
            if f.exists():
                checks[str(f.relative_to(REPO))] = sha(f)
        for e in exps:
            # population kind (§A) — model-labelled records are NOT excluded
            if e.get("in_series"):
                kind = "series_member_experiment"
            elif e.get("granularity") == "profile":
                kind = "profile_experiment"
            elif e.get("is_paper_level"):
                kind = "paper_level_record"
            elif e.get("granularity") in ("unresolved", None):
                kind = "unresolved_experiment_record"
            elif e.get("granularity") == "correlation":
                kind = "correlation_record"
            else:
                kind = "single_experiment"
            if e.get("is_model_result") or e.get("relevance") == "model":
                kind_model = "model_record_in_experiments_json"
            else:
                kind_model = None
            prov = e.get("provenance") or {}
            records.append({
                "record_id": e.get("exp_id"), "paper_id": doi,
                "kind": kind, "model_overlay": kind_model,
                "relevance": e.get("relevance"),
                "granularity": e.get("granularity"),
                "is_model_result": bool(e.get("is_model_result")),
                "in_series": e.get("in_series"),
                "figure_number": prov.get("figure_number"),
                "fig_docling_index": prov.get("fig_docling_index"),
                "panel": prov.get("panel"),
                "series_name": e.get("series_name"),
                "coordinate": e.get("coordinate"),
                "measurand": (e.get("measurand") or {}).get("quantity"),
                "n_points": len(e.get("points") or []),
                "has_context_conflicts": bool(e.get("context_conflicts")),
                "ctrl_quantities": sorted({c.get("quantity") for c in (e.get("controlled") or [])
                                           if c.get("quantity")}),
            })
            kinds[kind] += 1; rel[e.get("relevance")] += 1; gran[e.get("granularity")] += 1
        per_paper[doi] = {"experiments": len(exps), "series": len(ser), "curves": len(curves),
                          "model_records": sum(1 for e in exps if e.get("is_model_result")
                                               or e.get("relevance") == "model"),
                          "experimental_records": sum(1 for e in exps
                                                      if e.get("relevance") == "experimental"),
                          "unresolved_records": sum(1 for e in exps
                                                    if e.get("granularity") in ("unresolved", None))}
    man = {
        "frozen_at_git_commit": sh("git", "rev-parse", "HEAD"),
        "git_describe": sh("git", "describe", "--always", "--dirty"),
        "working_tree_dirty": bool(sh("git", "status", "--porcelain")),
        "working_tree_status_lines": len((sh("git", "status", "--porcelain") or "").splitlines()),
        "generation_timestamp_source": "mtime of resolved/experiments.json per paper",
        "generation_commands": [
            "python3 -m ontology.build_ontology",
            "python3 02_extraction/canonical/recover_axis_semantics.py --all",
            "<psed310> 02_extraction/canonical/reextract_figures.py --priority high",
            "<psed310> 03_corpus/scripts/06_to_kb.py --all --resolve-only",
            "python3 02_extraction/canonical/build_canonical.py --all",
            "python3 02_extraction/build_kg.py",
        ],
        "n_papers": len(papers),
        "n_experiment_like_records": len(records),
        "n_series": sum(v["series"] for v in per_paper.values()),
        "n_curves": sum(v["curves"] for v in per_paper.values()),
        "n_model_labeled": sum(v["model_records"] for v in per_paper.values()),
        "n_experimental_labeled": sum(v["experimental_records"] for v in per_paper.values()),
        "n_unresolved": sum(v["unresolved_records"] for v in per_paper.values()),
        "population_kind_counts": dict(kinds),
        "relevance_counts": {str(k): v for k, v in rel.items()},
        "granularity_counts": {str(k): v for k, v in gran.items()},
        "per_paper": per_paper,
        "checksums": checks,
        "records": records,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "corpus_population_manifest.json").write_text(json.dumps(man, indent=1))
    print("papers=%d records=%d series=%d curves=%d" %
          (man["n_papers"], man["n_experiment_like_records"], man["n_series"], man["n_curves"]))
    print("kinds:", dict(kinds))
    print("relevance:", man["relevance_counts"])
    print("-> corpus_population_manifest.json")


if __name__ == "__main__":
    main()
