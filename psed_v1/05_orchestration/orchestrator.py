"""
orchestrator.py  (M5 / Phase 6 — KB ↔ planner ↔ executors)
----------------------------------------------------------
The single entry point that makes the three roles a pipeline:

    query → INTENT → KB grounding → Recipe → EXECUTOR → result → write-back

The planner here is a deterministic keyword router (an LLM would replace only the
`parse_intent` step — the routing, grounding, executors, and provenance are the
same). Every capability is KB-grounded and cites its sources; every run is appended
to a derived store so the KB's memory grows (the write-back arrow that the stateless
Argonne agents lack).

Executors wired:
  identify              → process_id.identify        (KB processes + citations, Argonne JSON)
  predict_conformality  → channel_model twin         (M1/M3 penetration depth, param provenance)
  optimize_dose         → kb_bridge rate prior        (M4 saturation dose from real sticking data)
  warm_start            → kb_bridge.warm_start        (M2 controller seed from nearest process)
"""
import sys, json, re
from pathlib import Path

# psed_v1 layout: the KB stages live in 02_extraction and the twin in 04_twin_mpc.
# These two paths still named the pre-psed_v1 folders (0706_pipeline / PSED_MPC),
# so this report could not be regenerated at all.
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "02_extraction"))
sys.path.insert(0, str(REPO / "04_twin_mpc"))
import kb_service                      # noqa: E402
import process_id                      # noqa: E402
import recipe as recipe_mod            # noqa: E402
import kb_bridge                       # noqa: E402
from channel_model import channelModel, MODEL_ID  # noqa: E402

DERIVED = REPO / "02_extraction" / "kb_derived"
DERIVED.mkdir(parents=True, exist_ok=True)
STORE = DERIVED / "orchestrator_runs.json"

# common name/formula → KB material id
_MAT_ALIAS = {"alumina": "Al2O3", "aluminum oxide": "Al2O3", "aluminium oxide": "Al2O3",
              "titania": "TiO2", "titanium oxide": "TiO2", "silica": "SiO2",
              "hafnia": "HfO2", "hafnium oxide": "HfO2", "zinc oxide": "ZnO"}


def _material(q):
    mats = kb_service.materials()
    for m in mats:                                  # exact formula match
        if m.lower() in q:
            return m
    for name, m in _MAT_ALIAS.items():
        if name in q:
            return m
    return None


def _target(q):
    t = {}
    m = re.search(r"aspect[- ]?ratio\s*(?:of\s*)?(\d+)", q)
    if m:
        t["aspect_ratio"] = float(m.group(1))
    m = re.search(r"(\d+)\s*(?:°|deg|celsius|c\b)", q)
    if m:
        t["temperature"] = float(m.group(1))
    return t


# ---------------------------------------------------------------- planner
def parse_intent(query, channels=None):
    """NL(-ish) query → structured intent. Keyword router; an LLM would replace ONLY
    this function, emitting the same dict."""
    q = query.lower()
    if any(w in q for w in ("identify", "which process", "what process", "deposit", "recipe for", "grow ")):
        intent = "identify"
    elif any(w in q for w in ("dose", "saturat", "pulse time", "how long", "self-limit")):
        intent = "optimize_dose"
    elif any(w in q for w in ("conformal", "penetration", "aspect ratio", "high-ar", "coverage", "profile")):
        intent = "predict_conformality"
    elif any(w in q for w in ("warm", "seed", "control", "mpc", "prior", "start")):
        intent = "warm_start"
    else:
        intent = "identify"
    return {"intent": intent, "material": _material(q), "channels": channels,
            "target": _target(q), "query": query}


# ---------------------------------------------------------------- executors
def _identify(spec):
    chans = spec.get("channels") or ["TMA", "water", "DEZ", "TiCl4", "TDMAHf"]
    cands = process_id.identify(spec["material"], chans)
    if not cands:
        return {"ok": False, "msg": f"no KB process for {spec['material']} on {chans}"}
    top = cands[0]
    return {"ok": True, "recipe": {"precursor": top["precursor"], "coreactant": top["coreactant"],
            "cycle": top["recipe"].cycle_sequence, "argonne_json": top["argonne"],
            "installable": top["compatible"], "channels": top["channels"]},
            "grounding": {"support_n": top["support"], "source": top["source"]},
            "citations": top["papers"], "alternatives": len(cands) - 1}


def _predict_conformality(spec):
    mat = spec["material"]
    E = [e for e in kb_service._load() if e.get("material") == mat and e.get("reactants")]
    prec = next((r.get("species") for e in E for r in e["reactants"] if r.get("role") == "precursor"), None)
    carrier = next(((e.get("carrier_gas") or {}).get("species") for e in E if e.get("carrier_gas")), "N2")
    twin = channelModel.from_kb(mat, species={"A": prec} if prec else None, carrier=carrier)
    ar = spec["target"].get("aspect_ratio")
    if ar:
        twin.W = twin.H * ar                        # geometry from the requested aspect ratio
    if spec["target"].get("temperature"):
        twin.T = spec["target"]["temperature"] + 273.15
    pd = twin.penetration_depth()
    prov = twin.kb_provenance
    src = {s: sum(1 for p in prov.values() if p.get("source") == s) for s in ("kb", "precursor", "material")}
    src["default"] = len(["gpc", "K", "c", "da", "db", "MA", "MB", "M", "rho", "b_film", "b_a",
                          "H", "W", "T", "pA", "pB", "t_p"]) - sum(src.values())
    return {"ok": True, "model": MODEL_ID, "material": mat, "precursor": prec, "carrier": carrier,
            "penetration_depth_um": round(pd * 1e6, 2), "aspect_ratio": ar,
            "param_provenance": src,
            "citations": sorted({r for p in prov.values() for r in p.get("refs", [])})}


def _optimize_dose(spec):
    mat = spec["material"]
    pr = kb_bridge.saturation_prior_from_kb(mat)
    if not pr:
        return {"ok": False, "msg": f"KB lacks the kinetic data (sticking/pressure/site density) to derive a dose for {mat}"}
    return {"ok": True, "material": mat,
            "recommended_precursor_dose_s": round(pr["t_sat_s"], 5),
            "basis": f"k1≈{pr['k1']:.0f}/s from sticking s0={pr['inputs']['c']:.1e} ({pr['inputs']['c_source']})",
            "self_limited": pr["self_limited"],
            "caveat": "flat-surface saturation time; high-AR features need longer dosing (use predict_conformality)",
            "citations": pr.get("refs", [])}


def _warm_start(spec):
    w = kb_bridge.warm_start(spec["material"], target=spec.get("target") or None)
    p = w["priors"]
    return {"ok": w["pA0"] is not None or w["tp0"] is not None,
            "material": spec["material"], "pA0": w["pA0"], "tp0": w["tp0"], "r_star": w["r_star"],
            "gpc_expected_nm": p.get("gpc_expected"), "self_limited": p.get("self_limited"),
            "nearest_process": w["provenance"]["nearest"], "similarity": w["provenance"]["similarity"],
            "citations": [w["provenance"]["nearest"].split("-")[0]] if w["provenance"]["nearest"] else []}


def _twin_for(material):
    E = [e for e in kb_service._load() if e.get("material") == material and e.get("reactants")]
    prec = next((r.get("species") for e in E for r in e["reactants"] if r.get("role") == "precursor"), None)
    carrier = next(((e.get("carrier_gas") or {}).get("species") for e in E if e.get("carrier_gas")), "N2")
    twin = channelModel.from_kb(material, species={"A": prec} if prec else None, carrier=carrier)
    return twin, prec, carrier


def _pd_at(twin, tp):
    twin.t_p = tp; twin.prepare(); return twin.penetration_depth()


def _solve_dose(twin, target_pen, lo=0.02, hi=60.0):
    """Smallest precursor dose whose PD50 ≥ target penetration; None if even hi can't."""
    if _pd_at(twin, hi) < target_pen:
        return None
    for _ in range(40):
        mid = (lo * hi) ** 0.5
        if _pd_at(twin, mid) >= target_pen:
            hi = mid
        else:
            lo = mid
    return hi


def design(material, channels, structure, target=None, tp_literature=0.1):
    """Composite task: AUTOMATE the manual expert workflow for conformal recipe design
    by chaining KB-grounded chemistry ID, parameter retrieval, physics conformality
    evaluation, inverse solving, and a control seed — reproducibly and with provenance.
    (Not "only this can solve it": a well-posed problem an expert or a good LLM can also
    reason about; the value is automation + calibration + citations.)

    NOTE: the *properly-posed* version of this task — full recipe, exposure-first
    (pA·t_p at the reactor's fixed pressure), thickness step-coverage criterion, and
    held-out calibration — lives in eval/eval_design.py (paper-aligned). This function
    is the earlier pulse-time sketch, kept for the orchestrator demo; prefer the eval.

    structure = {aspect_ratio, gap_um}; target = {fill_fraction (default 0.9)}."""
    tr = []
    fill = (target or {}).get("fill_fraction", 0.9)
    H = (structure.get("gap_um") or 0.5) * 1e-6
    AR = structure["aspect_ratio"]
    L_req = AR * H
    pen_target = fill * L_req

    # 1 — chemistry from the KB, checked against the installed channels (+ citations)
    cands = process_id.identify(material, channels)
    if not cands or not cands[0]["compatible"]:
        return {"ok": False, "stage": "identify",
                "msg": f"no installable {material} chemistry on {channels}", "trace": tr}
    chem = cands[0]
    tr.append({"step": "identify (KB)", "out": f"{chem['precursor']}+{chem['coreactant']} cycle {chem['recipe'].cycle_sequence}",
               "cite": chem["papers"]})

    # 2 — parameters: temperature imputed from similar experiments (covariate-conditioned)
    corpus = kb_service._load(); import similarity as _sim; SC = _sim.logscale(corpus)
    probe = {"material": material, "process_type": "thermal",
             "precursors": [chem["precursor"]], "coreactants": [chem["coreactant"]], "controlled": []}
    T_est = kb_service.impute(probe, "temperature", None, corpus=corpus, SC=SC)
    T_C = T_est["value"] if T_est else 250.0
    tr.append({"step": "parameters (KB imputation)",
               "out": f"T≈{T_C:.0f}°C" + (f" (68% CI {T_est['ci_lo']:.0f}–{T_est['ci_hi']:.0f}, n={T_est['n_donors']})" if T_est else ""),
               "cite": [d["exp_id"].split("-")[0] for d in (T_est or {}).get("donors", [])[:3]]})

    # 3 — physics: does the STANDARD literature dose actually fill THIS geometry?
    twin, prec, carrier = _twin_for(material)
    twin.H = H; twin.W = max(1e-4, H * 5); twin.T = T_C + 273.15
    pd_lit = _pd_at(twin, tp_literature)
    fills_lit = pd_lit / H
    tr.append({"step": "physics check (twin @ literature dose)",
               "out": f"t_p={tp_literature}s → PD50={pd_lit*1e6:.0f}µm, fills AR≈{fills_lit:.0f} "
                      f"(need L={L_req*1e6:.0f}µm for AR={AR:.0f})",
               "flag": "SHORT" if pd_lit < pen_target else "ok"})

    # 4 — inverse solve: if short, find the dose that meets the target (or prove infeasible)
    if pd_lit >= pen_target:
        tp_req, feasible = tp_literature, True
    else:
        tp_req = _solve_dose(twin, pen_target)
        feasible = tp_req is not None
    if feasible:
        pd_req = _pd_at(twin, tp_req)
        tr.append({"step": "inverse design (physics search)",
                   "out": f"required t_p={tp_req:.2f}s → PD50={pd_req*1e6:.0f}µm ≥ target {pen_target*1e6:.0f}µm"
                          + (" (literature dose already sufficient)" if tp_req == tp_literature else
                             f"  —  {tp_req/tp_literature:.0f}× the standard dose")})
    else:
        pd_max = _pd_at(twin, 60.0); ar_max = pd_max / H
        tr.append({"step": "inverse design (physics search)", "flag": "INFEASIBLE",
                   "out": f"even a 60s dose reaches only PD50={pd_max*1e6:.0f}µm (AR≈{ar_max:.0f}); "
                          f"AR={AR:.0f} is UNFILLABLE for this chemistry/geometry"})

    # 5 — control: warm-start the deposition controller (fewer run-to-run iterations)
    w = kb_bridge.warm_start(material, target={"aspect_ratio": AR})
    tr.append({"step": "control seed (warm-start)",
               "out": f"nearest process {w['provenance']['nearest']} (sim {w['provenance']['similarity']}), "
                      f"self-limited={w['priors'].get('self_limited')}",
               "cite": [w["provenance"]["nearest"].split("-")[0]] if w["provenance"]["nearest"] else []})

    # confidence from parameter grounding
    prov = twin.kb_provenance
    grounded = sum(1 for p in prov.values() if p.get("source") in ("kb", "precursor", "material"))
    recipe = {"material": material, "precursor": prec, "coreactant": chem["coreactant"],
              "cycle": chem["recipe"].cycle_sequence, "temperature_C": round(T_C),
              "precursor_dose_s": round(tp_req, 2) if feasible else None,
              "aspect_ratio": AR, "gap_um": H * 1e6,
              "argonne_json": chem["argonne"]}
    return {"ok": feasible, "feasible": feasible, "recipe": recipe, "trace": tr,
            "predicted_fill_AR": round((pd_req if feasible else _pd_at(twin, 60.0)) / H),
            "confidence": f"{grounded}/{len(prov)} twin params literature-grounded",
            "citations": sorted(set(sum([s.get("cite", []) for s in tr], []))),
            "model": MODEL_ID}


_EXEC = {"identify": _identify, "predict_conformality": _predict_conformality,
         "optimize_dose": _optimize_dose, "warm_start": _warm_start}


# ---------------------------------------------------------------- loop + memory
def write_back(record):
    """Append a run to the derived KB store — memory grows with every query."""
    log = json.loads(STORE.read_text()) if STORE.exists() else []
    log.append(record)
    STORE.write_text(json.dumps(log, indent=2, default=str))
    return len(log)


def run(query, channels=None):
    spec = parse_intent(query, channels)
    if not spec["material"]:
        result = {"ok": False, "msg": "could not identify a target material in the query"}
    else:
        result = _EXEC[spec["intent"]](spec)
    n = write_back({"query": query, "intent": spec["intent"], "material": spec["material"],
                    "target": spec["target"], "result": result})
    return {"spec": spec, "result": result, "run_id": n}


DEMOS = [
    ("What process deposits Al2O3 on a reactor with TMA and water?", ["TMA", "water", "DEZ"]),
    ("Predict the conformality of Al2O3 in an aspect-ratio 50 feature", None),
    ("How long should the TMA dose be to saturate Al2O3?", None),
    ("Warm-start the controller for TiO2", None),
    ("Grow HfO2 on a reactor with only TMA and water", ["TMA", "water"]),
]

INTENT_DESC = {
    "identify": ("process_id → KB processes + citations", "#2a78d6"),
    "predict_conformality": ("channel_model twin → penetration depth", "#1baf7a"),
    "optimize_dose": ("kb_bridge rate prior → saturation dose", "#eda100"),
    "warm_start": ("kb_bridge.warm_start → controller seed", "#9085e9"),
}


def make_report(runs):
    def cell(r):
        res = r["result"]
        if not res.get("ok"):
            return f'<span style="color:#e34948">✗ {res.get("msg","infeasible")}</span>'
        body = {k: v for k, v in res.items() if k not in ("ok", "citations", "caveat", "model", "material")}
        s = json.dumps(body, default=str)
        s = (s[:150] + "…") if len(s) > 150 else s
        cav = f'<div class=cav>⚠ {res["caveat"]}</div>' if res.get("caveat") else ""
        cit = (f'<div class=cite>cites: {", ".join(res["citations"])}</div>' if res.get("citations") else "")
        return f'<span class=m>{s}</span>{cav}{cit}'
    trows = ""
    for r in runs:
        s = r["spec"]; col = INTENT_DESC.get(s["intent"], ("", "#8b919b"))[1]
        trows += (f'<tr><td>{s["query"]}</td>'
                  f'<td><span class=badge style="background:{col}22;color:{col}">{s["intent"]}</span></td>'
                  f'<td class=m>{s["material"] or "—"}</td><td>{cell(r)}</td></tr>')
    stages = [("query", "natural-language ask", "#8b919b"),
              ("planner", "intent + material + target<br><span style='font-size:10px'>(keyword router; LLM-swappable)</span>", "#4a3aa7"),
              ("KB grounding", "kb_service · process_id · impute", "#2a78d6"),
              ("executor", "twin · rate prior · warm-start", "#1baf7a"),
              ("write-back", "kb_derived/ store grows", "#eda100")]
    flow = "".join(
        f'<div class=stage style="border-color:{c}"><b style="color:{c}">{n}</b><div class=sd>{d}</div></div>'
        + ("<div class=arrow>→</div>" if i < len(stages) - 1 else "")
        for i, (n, d, c) in enumerate(stages))
    legend = " · ".join(f'<span style="color:{c}">{k}</span>: {d}' for k, (d, c) in INTENT_DESC.items())
    html = f"""<!doctype html><meta charset=utf-8><title>M5 · Orchestration loop</title><style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#131417;color:#eceef2}}.card{{background:#1c1e22 !important;border-color:#2b2e34 !important}}th{{color:#767c86 !important}}.stage{{background:#1c1e22 !important}}}}
.wrap{{max-width:1040px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:16px}}
.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}}
.flow{{display:flex;align-items:stretch;gap:6px;flex-wrap:wrap}}
.stage{{flex:1;min-width:120px;background:#fff;border:1.5px solid;border-radius:10px;padding:9px 11px}}
.stage b{{font-size:13px}}.sd{{font-size:11px;color:#565c66;margin-top:3px}}
.arrow{{display:flex;align-items:center;color:#8b919b;font-size:18px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:8px 8px;border-bottom:1px solid #eef0f3;vertical-align:top}}
.m{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px}}
.badge{{font-size:11px;padding:2px 7px;border-radius:6px;font-weight:600}}
.cav{{font-size:11px;color:#b9770a;margin-top:3px}}.cite{{font-size:11px;color:#2a78d6;margin-top:2px}}
.note{{font-size:12px;color:#565c66}}
</style><div class=wrap>
<div class=eyebrow>PSED · M5 · Phase 6</div>
<h1>Orchestration loop — KB ↔ planner ↔ executors</h1>
<div class=sub>One entry point turns a query into a grounded, cited action by routing an intent to the right executor and writing the result back so the KB's memory grows. The planner is a keyword router today; an LLM would replace only that step.</div>
<div class=card><h2>The loop</h2><div class=flow>{flow}</div>
<div class=note style="margin-top:10px">Intents → executors: {legend}</div></div>
<div class=card><h2>Example runs (end-to-end, grounded &amp; cited)</h2>
<table><tr><th>query</th><th>intent</th><th>material</th><th>result</th></tr>{trows}</table>
<div class=note style="margin-top:8px">Each run is appended to <span class=m>02_extraction/kb_derived/orchestrator_runs.json</span> — the write-back arrow the stateless Argonne agents lack. Every result carries provenance (papers, parameter sources) so downstream can trust and cite it.</div></div>
</div>"""
    (ROOT / "m5_orchestration.html").write_text(html)
    return html


if __name__ == "__main__":
    runs = []
    for q, ch in DEMOS:
        out = run(q, ch)
        runs.append(out)
        s, r = out["spec"], out["result"]
        print(f"\nQ: {q}")
        print(f"   intent={s['intent']}  material={s['material']}  target={s['target'] or '—'}")
        if r.get("ok"):
            cite = f"  cites={r.get('citations')}" if r.get("citations") else ""
            body = {k: v for k, v in r.items() if k not in ("ok", "citations", "caveat")}
            print(f"   ✓ {json.dumps(body, default=str)[:180]}{cite}")
            if r.get("caveat"):
                print(f"     ⚠ {r['caveat']}")
        else:
            print(f"   ✗ {r.get('msg')}")
    make_report(runs)
    print(f"\n[memory] {STORE.relative_to(REPO)} now holds {len(json.loads(STORE.read_text()))} runs")
    print("wrote m5_orchestration.html")
