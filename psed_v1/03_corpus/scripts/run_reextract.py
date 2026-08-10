#!/usr/bin/env python3
"""
run_reextract.py — scoped, resumable regeneration of every LLM-derived output for the
31 already-processed papers, using the CURRENT extraction implementation, then the
deterministic grounding + all downstream reports. Previous LLM-derived outputs are treated
as obsolete (ontology, canonical schema, pressure handling, figure extraction all changed).

LLM-derived units regenerated per paper (each an independent, resumable unit; every model
call goes through _genai_shim, which enforces the 31-DOI scope allow-list + the hard call
budget, preserves the raw response, and logs full reproducibility metadata):
  scout      04_extract.scout                -> scout.json
  figures    05_figure_extract.extract_paper -> figure_data.json, records.json
  geometry   09_geometry.classify_deterministic (NO LLM) + extract_quantities (LLM)
             -> geometry.json {class, structure, quantities}
  pressure   10_pressure.extract_pressures   -> pressure.json   (pressure handling CHANGED)
  card       06_to_kb.get_card (LLM methods-fill; stale card.json deleted first) -> card.json

Deterministic grounding (NO LLM), after all papers' units succeed:
  resolve    06_to_kb.main(['--resolve-only', *DOIs])  -> output/{doi}/resolved/experiments.json
             (injects card + geometry + pressure conditions from the regenerated caches)
  tag        09_geometry.tag_experiments()              -> geometry_class on every experiment

Reports (deterministic, subprocess): 02_extraction build_recipes/analysis/kg/dashboard,
corpus dashboard + status, M2 (m2_design), M3 (twin_validation).
Validation: the repo's test_*.py / invariant checks, pass/fail captured.

Phases:  --extract  ·  --downstream  ·  --reports  ·  --all (default)
Manifest 03_corpus/extraction_manifest.json · Call log 03_corpus/extraction_calls.jsonl
"""
import sys, os, json, time, hashlib, importlib.util, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                     # 03_corpus
REPO = ROOT.parent                     # psed_v1
EXTRACTED = ROOT / "extracted"
PIPE = REPO / "02_extraction"
TWIN = REPO / "04_twin_mpc"
MANIFEST = ROOT / "extraction_manifest.json"
CALLLOG = ROOT / "extraction_calls.jsonl"
MAX_CALLS = 600                        # hard budget ceiling (approved). Full base set ≈264 calls.

ALLOW = [
    "10.3762_bjnano.14.89", "10.1002_pssa.201532305", "10.1021_acs.chemmater.2c01154",
    "10.1039_c6dt03571j", "10.1039_c7ra07722j", "10.1039_d0cp03358h", "10.1039_d3ra05217f",
    "10.1016_j.tsf.2012.11.127", "10.1021_acs.chemmater.2c02292", "10.1039_d3dt01824e",
    "10.1063_1.5028178", "10.1116_1.4938104", "10.1116_6.0002154", "10.1116_6.0002436",
    "10.1116_6.0002804", "10.1016_j.sse.2022.108584", "10.1039_c5tc03561a",
    "10.1002_admi.202000318", "10.1002_celc.201600139", "10.3762_bjnano.5.25",
    "10.1021_acs.jpcc.9b08176", "10.1063_1.4867469", "10.1116_1.4892385",
    "10.1002_cnma.201700148", "10.1007_s11671-010-9676-0", "10.1007_s12274-010-0066-9",
    "10.1016_j.jcrysgro.2017.04.019", "10.1016_j.mee.2018.01.027", "10.1186_s11671-015-0872-9",
    "10.1016_j.matt.2019.12.026", "10.1016_j.mee.2018.01.033",
]
UNITS = ("scout", "figures", "geometry", "pressure", "card")


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, str(HERE / fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _key():
    for line in (ROOT / "config" / ".env").read_text().splitlines():
        if line.startswith("GOOGLE_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_API_KEY")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _src_hash(sd):
    """Hash of the REUSED source artifacts (Docling markdown + structure + figure images)."""
    d = EXTRACTED / sd
    h = hashlib.sha256()
    for f in ("document.md", "structure.json"):
        p = d / f
        h.update(p.read_bytes() if p.exists() else b"MISSING")
    figdir = d / "figures"
    if figdir.exists():
        for fp in sorted(figdir.iterdir()):
            h.update(fp.name.encode()); h.update(str(fp.stat().st_size).encode())
    return h.hexdigest()


def _load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"papers": {}, "started": time.time(), "scope": ALLOW, "units": list(UNITS),
            "max_calls": MAX_CALLS}


def _figures_ok(sd):
    fd = EXTRACTED / sd / "figure_data.json"
    if not fd.exists():
        return False
    try:
        j = json.loads(fd.read_text())
    except Exception:
        return False
    return not any("_parse_error" in (fig or {}) for fig in j.get("figures", []))


# ----------------------------------------------------------------------------------
# Phase 1 — LLM-derived regeneration (in-process, under the shim)
# ----------------------------------------------------------------------------------
def extract():
    import _genai_shim as shim
    shim.install()
    from google import genai
    m04 = _load("extract04", "04_extract.py")
    m05 = _load("figure05", "05_figure_extract.py")
    m06 = _load("tokb06", "06_to_kb.py")
    m09 = _load("geom09", "09_geometry.py")
    m10 = _load("press10", "10_pressure.py")

    onto = (REPO / "01_ontology" / "ald_ontology.json").read_bytes()
    schema = (getattr(m04, "SCHEMA", "") + getattr(m05, "VISION_SCHEMA", "")
              + getattr(m09, "QUANT_SCHEMA", "") + getattr(m10, "PRESSURE_SCHEMA", "")).encode()
    shim.STATE.update(allow=set(ALLOW), max_calls=MAX_CALLS, raw_root=EXTRACTED,
                      hashes={"ontology": _sha(onto), "schema": _sha(schema),
                              "prompt_version": _sha(schema + b"scout+vision+quant+pressure+card")})
    client = genai.Client(api_key=_key())
    man = _load_manifest()
    shim.STATE["calls"] = man.get("calls_made", 0)      # global budget across resumes
    if CALLLOG.exists():                                # accumulate the call log across resumes
        shim.STATE["log"] = [json.loads(l) for l in CALLLOG.read_text().splitlines() if l.strip()]

    def save():
        man["calls_made"] = shim.STATE["calls"]
        man["updated"] = time.time()
        MANIFEST.write_text(json.dumps(man, indent=1))
        with CALLLOG.open("w") as f:
            for rec in shim.STATE["log"]:
                f.write(json.dumps(rec) + "\n")

    # --- per-unit runners: each returns a short validation string, or raises ---
    def run_scout(sd):
        o = m04.scout(sd, client)
        if o.get("is_ald_process_paper") is None:
            raise RuntimeError("scout unresolved (is_ald None)")
        return f"is_ald={o.get('is_ald_process_paper')} drill={len(o.get('drill') or [])}"

    def run_figures(sd):
        # extract_paper returns [] and writes no figure_data.json when the scout drilled
        # nothing (a paper with no digitizable data figures) — that is a valid empty result,
        # NOT a failure. Success is judged on the returned records, not file presence: fail
        # only when a figure group actually parse-errored.
        results, records, ti, to = m05.extract_paper(sd, client)
        nfail = sum(1 for fr in results if "_parse_error" in fr)
        if nfail:
            raise RuntimeError(f"{nfail} figure(s) parse_error")
        drill0 = " (drill=0, no data figures)" if not results else ""
        return f"vision_calls~{len(results)} records={len(records)}{drill0}"

    def run_geometry(sd):
        gc, st, why = m09.classify_deterministic(sd)              # deterministic, NO LLM
        (EXTRACTED / sd / "geometry.json").write_text(json.dumps(
            {"geometry_class": gc, "structure": st, "method": "deterministic", "evidence": why}, indent=1))
        qs, (i, o) = m09.extract_quantities(sd, client)           # LLM, merges quantities
        return f"class={gc} quantities={len(qs)}"

    def run_pressure(sd):
        obs, (i, o) = m10.extract_pressures(sd, client)           # LLM, writes pressure.json
        return f"observations={len(obs)}"

    def run_card(sd):
        cf = EXTRACTED / sd / "card.json"
        if cf.exists():
            cf.unlink()                                           # obsolete cache -> force LLM rebuild
        scout = json.loads((EXTRACTED / sd / "scout.json").read_text())
        card, tok = m06.get_card(sd, scout, client)              # LLM methods-fill
        nonempty = sum(1 for k, v in card.items() if v not in (None, [], {}, ""))
        if nonempty == 0:
            raise RuntimeError("empty card")
        return f"card_fields={nonempty}"

    RUN = {"scout": run_scout, "figures": run_figures, "geometry": run_geometry,
           "pressure": run_pressure, "card": run_card}
    OUTPUTS = {
        "scout": {"scout_json": "scout.json"},
        "figures": {"figure_data_json": "figure_data.json", "records_json": "records.json"},
        "geometry": {"geometry_json": "geometry.json"},
        "pressure": {"pressure_json": "pressure.json"},
        "card": {"card_json": "card.json"},
    }

    for sd in ALLOW:
        p = man["papers"].setdefault(sd, {
            "doi": sd,
            "input_paths": {"document_md": f"extracted/{sd}/document.md",
                            "structure_json": f"extracted/{sd}/structure.json",
                            "figures": f"extracted/{sd}/figures/"},
            "source_artifact_sha256": _src_hash(sd),
            "units": {u: {"status": "pending", "attempts": 0, "calls": 0} for u in UNITS},
            "outputs": {}, "validation": {}, "notes": []})
        # a paper may pre-date the multi-unit manifest schema -> backfill missing unit slots
        for u in UNITS:
            p["units"].setdefault(u, {"status": "pending", "attempts": 0, "calls": 0})
        for u in UNITS:
            slot = p["units"][u]
            if slot["status"] == "succeeded":
                continue
            if u != "scout" and p["units"]["scout"]["status"] != "succeeded":
                slot["status"] = "blocked_on_scout"; save(); continue
            if shim.STATE["calls"] >= MAX_CALLS:
                p["notes"].append(f"budget reached before {u}"); save()
                print(f"[BUDGET] hard cap {MAX_CALLS} reached at {sd}/{u}"); return man
            shim.STATE["ctx"] = {"doi": sd, "unit": u, "src_hash": p["source_artifact_sha256"]}
            c0 = shim.STATE["calls"]
            try:
                detail = RUN[u](sd)
                slot["status"] = "succeeded"
                p["outputs"].update({k: f"extracted/{sd}/{v}" for k, v in OUTPUTS[u].items()})
                p["validation"][u] = f"ok: {detail}"
                print(f"[{u:8} OK]   {sd:32} {detail}  (calls {shim.STATE['calls']}/{MAX_CALLS})")
            except shim.BudgetExceeded:
                slot["status"] = "budget_stopped"; save()
                print(f"[BUDGET] {sd}/{u}"); return man
            except shim.ScopeViolation as e:
                slot["status"] = "scope_violation"; p["validation"][u] = str(e)
                print(f"[SCOPE] {sd}/{u}: {e}"); save(); return man
            except Exception as e:
                slot["status"] = "failed"
                p["validation"][u] = f"error: {type(e).__name__}: {str(e)[:200]}"
                p["notes"].append(f"{u} failed: {type(e).__name__}: {str(e)[:150]}")
                print(f"[{u:8} FAIL] {sd:32} {type(e).__name__}: {str(e)[:110]}")
            slot["attempts"] = shim.STATE["attempts"].get((sd, u), slot["attempts"])
            slot["calls"] = shim.STATE["calls"] - c0
            save()
    save()
    done = sum(1 for sd in ALLOW if all(man["papers"][sd]["units"][u]["status"] == "succeeded" for u in UNITS))
    print(f"\n[extract] DONE. papers fully succeeded={done}/{len(ALLOW)}  total calls={shim.STATE['calls']}/{MAX_CALLS}")
    return man


# ----------------------------------------------------------------------------------
# Phase 2 — deterministic grounding (NO LLM)
# ----------------------------------------------------------------------------------
def ground():
    m06 = _load("tokb06", "06_to_kb.py")
    m09 = _load("geom09", "09_geometry.py")
    print("\n===== GROUND: 06 --resolve-only (deterministic) =====")
    m06.main(["--resolve-only", *ALLOW])      # rebuild resolved/experiments.json from caches
    print("\n===== GROUND: 09 tag_experiments (deterministic) =====")
    m09.tag_experiments()


# ----------------------------------------------------------------------------------
# Phase 3 — reports + validation (deterministic, subprocess)
# ----------------------------------------------------------------------------------
def _run(cmd, cwd, timeout=1200):
    print(f"\n$ {' '.join(str(c) for c in cmd)}  (cwd={cwd.name})")
    try:
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd),
                           capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        print(f"  EXC {type(e).__name__}: {e}"); return -1
    tail = (r.stdout or "")[-500:] + (("\nERR:" + (r.stderr or "")[-500:]) if r.returncode else "")
    print(tail)
    return r.returncode


def reports():
    # invoke by ABSOLUTE path so each script's Path(__file__).parent resolves correctly
    # regardless of cwd (a bare filename makes __file__ relative, collapsing .parent.parent)
    rc = {}
    for s in ("build_recipes.py", "build_analysis.py", "build_kg.py", "build_dashboard.py"):
        if (PIPE / s).exists():
            rc[f"02_extraction/{s}"] = _run([sys.executable, str(PIPE / s)], PIPE)
    for s in ("build_corpus_dashboard.py", "status.py"):
        if (HERE / s).exists():
            rc[f"03_corpus/{s}"] = _run([sys.executable, str(HERE / s)], HERE)
    rc["m2:m2_design.py"] = _run([sys.executable, str(TWIN / "m2_design.py")], TWIN)
    rc["m3:twin_validation.py"] = _run([sys.executable, str(TWIN / "twin_validation.py")], TWIN)
    return rc


def validate():
    rc = {}
    checks = [
        (HERE, "test_pressure_extraction.py"), (HERE, "test_geometry_model_params.py"),
        (HERE, "test_chemistry_propagation.py"), (HERE, "test_provenance.py"),
        (HERE, "test_card_temperature.py"), (HERE, "check_card_invariants.py"),
        (TWIN, "test_report_freshness.py"), (TWIN, "test_twin_validation.py"),
    ]
    for cwd, s in checks:
        if (cwd / s).exists():
            rc[s] = _run([sys.executable, str(cwd / s)], cwd, timeout=600)
    return rc


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "--all"
    summary = {}
    if phase in ("--extract", "--downstream", "--all"):
        extract()
    if phase in ("--downstream", "--all"):
        ground()
    if phase in ("--reports", "--all"):
        print("\n########## REPORTS ##########")
        summary["reports"] = reports()
        print("\n########## VALIDATION ##########")
        summary["validation"] = validate()
        (ROOT / "reextract_downstream_summary.json").write_text(json.dumps(summary, indent=1))
        print("\nreport/validation return codes:\n" + json.dumps(summary, indent=1))
    print("\n[run_reextract] phase", phase, "complete")
