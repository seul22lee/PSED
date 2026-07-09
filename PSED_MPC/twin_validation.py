"""
twin_validation.py  (M3 / Phase 4)
----------------------------------
Validate the KB-parameterised conformality twin against the MEASURED thickness
profiles in the knowledge base. For each experimental Al2O3 conformality profile,
we build channelModel.from_kb(...), set the dose / temperature / geometry from the
experiment's recipe, predict the normalised thickness profile, and score it against
the measurement with the SAME curve engine used for experiment-vs-experiment
comparison (similarity.curve_metrics: nRMSE, R², overlap) plus Δ(PD50).

The output is a validation report + a ranked list of discrepancies — where the twin
(or the literature parameters it was given) disagrees with reality. Those are the
highest-value next experiments (active learning, INTEGRATION_STRATEGY §5).
"""
import base64, io, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
PIPE = HERE.parent / "0706_pipeline"
sys.path.insert(0, str(PIPE))
from channel_model import channelModel, MODEL_ID
import similarity as sim
import kb_service as ks

BLUE, RED, GREEN, AMBER, PURPLE, INK, GREY = "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#9085e9", "#14161a", "#8b919b"
NM = 1e-9
PLAUSIBLE_GAP_M = (5e-8, 5e-6)          # a Pillarhall/LHAR gap height is ~0.1–2 µm
DEFAULT_H = 0.5e-6                        # LHAR standard gap when geometry is missing/suspect
DEFAULT_W = 1e-4                          # channel width ≫ height; exact value barely matters

_CORPUS = _SC = None


def _ctx():                              # corpus + similarity scale, for imputation
    global _CORPUS, _SC
    if _CORPUS is None:
        _CORPUS = ks._load()
        _SC = sim.logscale(_CORPUS)
    return _CORPUS, _SC


def _cond(exp, q, r=None):
    for c in exp.get("controlled") or []:
        if c.get("quantity") == q and (r is None or c.get("of_reactant") == r):
            v = c.get("value")
            if isinstance(v, (int, float)):
                return float(v)
    return None


def _input(exp, q, r=None, impute=True):
    """A twin input's (value, provenance): 'extracted' from THIS experiment, else
    'imputed' (covariate-conditioned KB estimate — only an estimate, so a candidate
    reason for any mismatch), else (None, 'default'). Geometry is not imputed."""
    v = _cond(exp, q, r)
    if v is not None:
        return v, "extracted"
    if impute:
        corpus, SC = _ctx()
        est = ks.impute(exp, q, r, corpus=corpus, SC=SC)
        if est:
            return est["value"], "imputed"
    return None, "default"


def build_twin(exp):
    """Construct a twin for this experiment. Process parameters (dose, T, pA, gpc)
    are taken from THIS experiment, else covariate-imputed from the KB, else the
    model default. Geometry (gap height H) is taken or assumed (never imputed —
    it's structure-specific). Returns the twin, notes, and `prov` = {input: state}
    where state is extracted | imputed | default."""
    mat = exp.get("material")
    prec = next((r.get("species") for r in exp.get("reactants") or [] if r.get("role") == "precursor"), None)
    carrier = (exp.get("carrier_gas") or {}).get("species") or "N2"
    m = channelModel.from_kb(mat, species={"A": prec} if prec else None, carrier=carrier)
    notes, prov = [], {}

    tp, prov["dose"] = _input(exp, "pulse_time", "A")
    if prov["dose"] == "default":
        tp, prov["dose"] = _input(exp, "pulse_time", "B")
    if tp:
        m.t_p = tp
    T, prov["T"] = _input(exp, "temperature")
    if T is not None:
        m.T = T + 273.15
    pA, prov["pA"] = _input(exp, "partial_pressure", "A")
    if pA:
        m.pA = pA
    gpc, prov["gpc"] = _input(exp, "growth_per_cycle")
    if gpc:
        m.gpc = gpc * NM
    # geometry: gap height H (diffusion-limiting) — extracted or assumed, not imputed
    H, _ = _input(exp, "feature_height", impute=False)
    Hm = H * NM if H else None
    if Hm and PLAUSIBLE_GAP_M[0] <= Hm <= PLAUSIBLE_GAP_M[1]:
        m.H = Hm; prov["H"] = "extracted"
    else:
        prov["H"] = "default"
        notes.append(f"feature_height {H:g} nm out of gap range → assumed {DEFAULT_H*1e6:g} µm"
                     if Hm else f"no feature_height → assumed {DEFAULT_H*1e6:g} µm gap")
        m.H = DEFAULT_H
    for k in ("dose", "T", "pA", "gpc"):                 # note imputed process inputs
        if prov[k] == "imputed":
            notes.append(f"{k} imputed (KB estimate)")
    W, _ = _input(exp, "feature_width", impute=False)
    m.W = W * NM if (W and W * NM > m.H) else DEFAULT_W
    return m, notes, prov


def measured_profile(exp):
    """(x_µm, y_norm) of a mouth-to-tail conformality profile: x from the channel
    mouth (≥0), y normalised to the mouth plateau. Returns None if it isn't a
    standard decaying profile (guards degenerate / inverted / flat extractions)."""
    pts = sorted([p for p in (exp.get("points") or []) if p and p[0] is not None and p[1] is not None])
    pts = [(x, y) for x, y in pts if x >= 0]
    if len(pts) < 6:
        return None
    ys_raw = [y for _, y in pts]
    k = max(1, len(pts) // 10)
    plateau = sum(ys_raw[:k]) / k                        # mean of the first ~10% (mouth)
    ymax = max(ys_raw)
    tail = sum(ys_raw[-k:]) / k
    # must be a real decaying profile: mouth near the max, tail well below the mouth
    if plateau <= 0 or plateau < 0.6 * ymax or tail > 0.6 * plateau:
        return None
    xs = [x for x, _ in pts]
    ys = [max(y, 0.0) / plateau for _, y in pts]
    return xs, ys


def pd50(xs, ys):
    """Half-thickness penetration: x where the (normalised) profile crosses 0.5."""
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), list(zip(xs, ys))[1:]):
        if (y0 - 0.5) * (y1 - 0.5) <= 0 and y1 != y0:
            return x0 + (0.5 - y0) * (x1 - x0) / (y1 - y0)
    return None


DRIVERS = ["dose", "H"]          # the inputs that set absolute penetration


def _is_thermal(exp):
    """The Ylilammi twin models THERMAL, precursor-diffusion-limited ALD. Plasma
    (PEALD) conformality is recombination-limited — a different physical model
    (Arts/Aguinsky), so those profiles are out of this twin's scope."""
    pt = (exp.get("process_type") or "").lower()
    return "plasma" not in pt and "peald" not in pt


def validate_one(exp):
    meas = measured_profile(exp)
    if not meas:
        return None
    xm, ym = meas
    twin, notes, prov = build_twin(exp)
    xmax_m = max(xm) * 1e-6
    xg = np.linspace(0, xmax_m, 300)
    twin.prepare()
    th, _, _ = twin.approx(xg, np.zeros_like(xg))
    t0 = th[0] if th[0] > 0 else (th.max() or 1)
    xt_um = list(xg * 1e6)
    yt = list(np.clip(th / t0, 0, None))
    cm = sim.curve_metrics(xm, ym, xt_um, yt)
    pd_m, pd_t = pd50(xm, ym), pd50(xt_um, yt)
    dpd = abs(pd_m - pd_t) if (pd_m and pd_t) else None
    rel = (dpd / pd_m) if (dpd and pd_m) else None
    r2 = cm.get("r2") if cm else None
    thermal = _is_thermal(exp)
    agree = thermal and (r2 is not None and r2 >= 0.5) and (rel is None or rel <= 0.3)

    # provenance of the two penetration-setting inputs decides the verdict:
    #   any assumed  -> DATA gap        (no info; measure it)
    #   any imputed  -> ESTIMATION gap  (KB estimate may be the cause, not the model)
    #   all extracted-> MODEL gap       (real Ylilammi physics / literature K,c miss)
    dstates = [prov.get(k) for k in DRIVERS]
    if not thermal:
        verdict, kind = "out of scope", "plasma / recombination-limited — needs the Arts/Aguinsky model, not the thermal twin"
    elif agree:
        verdict, kind = "agrees", None
    elif "default" in dstates:
        miss = [k for k in DRIVERS if prov.get(k) == "default"]
        verdict, kind = "data gap", f"assumed {', '.join(miss)} → measure to resolve"
    elif "imputed" in dstates:
        imp = [k for k in DRIVERS if prov.get(k) == "imputed"]
        verdict, kind = "estimation gap", f"{', '.join(imp)} is a KB ESTIMATE — the imputed value may be the cause, not the model"
    else:
        verdict, kind = "model gap", "dose + geometry both measured, twin still misses → Ylilammi physics / literature K,c"
    if verdict not in ("agrees", "out of scope") and pd_m and pd_t:
        kind = ("twin under-penetrates; " if pd_t < pd_m else "twin over-penetrates; ") + (kind or "")
    measured = sorted(k for k, s in prov.items() if s == "extracted")
    imputed = sorted(k for k, s in prov.items() if s == "imputed")
    return {"exp_id": exp.get("exp_id"), "material": exp.get("material"),
            "paper": exp.get("exp_id", "").split("-")[0], "thermal": thermal,
            "r2": r2, "nrmse": cm.get("nrmse") if cm else None,
            "overlap": cm.get("overlap") if cm else None,
            "pd_meas": pd_m, "pd_twin": pd_t, "pd_rel": rel,
            "agree": agree, "verdict": verdict, "kind": kind,
            "prov": prov, "measured": measured, "imputed": imputed,
            "t_p": twin.t_p, "T": twin.T - 273.15, "H_um": twin.H * 1e6, "notes": notes,
            "_meas": (xm, ym), "_twin": (xt_um, yt)}


def run():
    E = []
    for f in sorted((PIPE / "output").glob("*/resolved/experiments.json")):
        E += json.load(open(f))
    # ALL 4 papers, all materials, thermal + plasma conformality profiles
    targets = [e for e in E if e.get("granularity") == "profile"
               and e.get("relevance") == "experimental"
               and (e.get("measurand") or {}).get("quantity") in ("film_thickness", "normalized_thickness")
               and e.get("points") and len(e["points"]) >= 6]
    results = [r for r in (validate_one(e) for e in targets) if r]
    # thermal (in-scope) first, best R² last; plasma/out-of-scope grouped at the end
    results.sort(key=lambda r: (r["verdict"] == "out of scope",
                                r["r2"] if r["r2"] is not None else -9))
    return results


# ---------------- report ----------------
def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


def overlay_fig(results, worst_n=3, best_n=3):
    ins = [r for r in results if r["thermal"]]           # quantitative comparison = thermal only
    picks = ins[:worst_n] + ins[-best_n:] if len(ins) > worst_n + best_n else ins
    n = len(picks)
    fig, axes = plt.subplots(1, n, figsize=(2.7 * n, 3.0), squeeze=False)
    for ax, r in zip(axes[0], picks):
        xm, ym = r["_meas"]; xt, yt = r["_twin"]
        ax.plot(xm, ym, "o", color=INK, ms=3, label="measured")
        ax.plot(xt, yt, "-", color=(GREEN if r["agree"] else RED), lw=2, label="twin")
        ax.axhline(0.5, color=GREY, ls=":", lw=.8)
        ax.set_title(f"{r['exp_id']}\nR²={r['r2']}", fontsize=8)
        ax.set_xlabel("x (µm)", fontsize=8); ax.set_ylim(-0.05, 1.15)
        ax.tick_params(labelsize=7)
    axes[0][0].set_ylabel("normalised thickness", fontsize=8)
    axes[0][-1].legend(fontsize=7)
    fig.tight_layout()
    return _png(fig)


VCOLOR = {"agrees": GREEN, "model gap": RED, "estimation gap": PURPLE,
          "data gap": AMBER, "out of scope": GREY}


def scatter_fig(results):
    ins = [r for r in results if r["thermal"]]
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    for r in ins:
        if r["pd_meas"] and r["pd_twin"]:
            ax.plot(r["pd_meas"], r["pd_twin"], "o", ms=6, color=VCOLOR[r["verdict"]], alpha=.8)
    lim = max([r["pd_meas"] for r in ins if r["pd_meas"]] +
              [r["pd_twin"] for r in ins if r["pd_twin"]] + [1])
    ax.plot([0, lim], [0, lim], "--", color=GREY, lw=1)
    ax.set_xlabel("measured PD50 (µm)"); ax.set_ylabel("twin PD50 (µm)")
    ax.set_title("penetration depth: twin vs measured", fontsize=10)
    fig.tight_layout()
    return _png(fig)


HTML = """<title>M3 · Twin validation against KB curves</title>
<style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#131417;color:#eceef2}}.card{{background:#1c1e22 !important;border-color:#2b2e34 !important}}th{{color:#767c86 !important}}}}
.wrap{{max-width:1040px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:18px}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}} img{{max-width:100%}}
.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:5px 8px;border-bottom:1px solid #eef0f3}}.m{{font-family:ui-monospace,Menlo,monospace}}
.flag{{color:#e34948;font-weight:600}}.ok{{color:#1baf7a;font-weight:600}}
.kv{{display:flex;gap:22px;flex-wrap:wrap;margin:8px 0 2px}} .kv div b{{display:block;font-size:18px}} .kv div span{{color:#8b919b;font-size:11px}}
.note{{font-size:11px;color:#8b919b}}
</style>
<div class=wrap>
<div class=eyebrow>PSED · M3 · Phase 4</div>
<h1>Twin validation against measured KB profiles</h1>
<div class=sub>The KB-parameterised Ylilammi twin (<span class=m>{model}</span>) is run against every measured conformality
profile across <b>all four papers</b> and scored with the same curve engine used across the KB. Missing twin inputs are covariate-imputed from the KB — and because an imputed value is only an <b>estimate</b>, it is a candidate cause of any mismatch, tracked separately below.</div>
<div class=card><div class=kv>
 <div><b>{nt}</b><span>thermal profiles (in scope)</span></div>
 <div><b class=ok>{npass}</b><span>agree</span></div>
 <div><b style="color:#e34948">{nmodel}</b><span>model gap (all inputs measured)</span></div>
 <div><b style="color:#9085e9">{nest}</b><span>estimation gap (an input imputed)</span></div>
 <div><b style="color:#eda100">{ndata}</b><span>data gap (an input assumed)</span></div>
 <div><b style="color:#8b919b">{noos}</b><span>out of scope (plasma)</span></div>
</div>
<div class=note style="margin-top:8px">Verdict is set by the provenance of the two penetration-setting inputs (dose &amp; gap height):
<b style="color:#e34948">model gap</b> = both measured, twin still misses → real Ylilammi-physics / literature-K,c limit ·
<b style="color:#9085e9">estimation gap</b> = an input is a <b>KB estimate</b>, which may itself be the cause, not the model ·
<b style="color:#eda100">data gap</b> = an input was assumed → measure it ·
<b style="color:#8b919b">out of scope</b> = plasma / recombination-limited (Arts), which the thermal twin doesn't model — see future work.</div></div>
<div class=card><h2>Twin vs measured — worst &amp; best fits</h2><img src="data:image/png;base64,{ov}"></div>
<div class=card><h2>Penetration depth: twin vs measured</h2><img src="data:image/png;base64,{sc}">
<div class=note>On the diagonal = the twin reproduces the measured penetration. Off-diagonal reds are where literature parameters + the Ylilammi physics miss the real profile.</div></div>
<div class=card><h2>Per-profile results</h2>
<table><tr><th>exp id</th><th>R²</th><th>PD50 meas</th><th>PD50 twin</th><th>ΔPD50</th><th>inputs measured</th><th>verdict</th></tr>
{rows}
</table></div>
</div>"""


def main():
    results = run()
    ov = overlay_fig(results)
    sc = scatter_fig(results)
    ins = [r for r in results if r["thermal"]]
    nt = len(ins)
    nmodel = sum(r["verdict"] == "model gap" for r in results)
    nest = sum(r["verdict"] == "estimation gap" for r in results)
    ndata = sum(r["verdict"] == "data gap" for r in results)
    noos = sum(r["verdict"] == "out of scope" for r in results)
    npass = sum(r["agree"] for r in results)
    vlabel = {"agrees": "✓ agrees", "model gap": "⚑ model gap", "estimation gap": "≈ estimation gap",
              "data gap": "○ data gap", "out of scope": "— out of scope"}
    vstyle = {"agrees": "color:#1baf7a;font-weight:600", "model gap": "color:#e34948;font-weight:600",
              "estimation gap": "color:#9085e9;font-weight:600", "data gap": "color:#eda100;font-weight:600",
              "out of scope": "color:#8b919b"}
    rows = ""
    for r in results:
        rel = f"{r['pd_rel']*100:.0f}%" if r["pd_rel"] is not None else "—"
        st = f'<span style="{vstyle[r["verdict"]]}">{vlabel[r["verdict"]]}</span>'
        kind = f'<div class=note>{r["kind"]}</div>' if r["kind"] else ""
        note = f'<div class=note>{"; ".join(r["notes"])}</div>' if r["notes"] else ""
        inputs = " · ".join(f'<span style="color:#1baf7a">{k}</span>' for k in r["measured"]) \
            + ("".join(f' · <span style="color:#9085e9">{k}~</span>' for k in r["imputed"]))
        rows += (f"<tr><td class=m>{r['exp_id']}{note}</td><td class=m>{r['r2']}</td>"
                 f"<td class=m>{_um(r['pd_meas'])}</td><td class=m>{_um(r['pd_twin'])}</td><td class=m>{rel}</td>"
                 f"<td style='font-size:11px'>{inputs or '—'}</td><td>{st}{kind}</td></tr>")
    out = HERE / "m3_validation.html"
    out.write_text(HTML.format(model=MODEL_ID, nt=nt, npass=npass, nmodel=nmodel,
                               nest=nest, ndata=ndata, noos=noos, ov=ov, sc=sc, rows=rows))
    print("wrote", out)
    print(f"  {len(results)} profiles ({nt} thermal, {noos} plasma) · {npass} agree · "
          f"{nmodel} model · {nest} estimation · {ndata} data gaps")
    for r in ins[:6]:
        print(f"  {r['verdict']:14} {r['exp_id']:20} R²={r['r2']}  "
              f"meas={_um(r['pd_meas'])} twin={_um(r['pd_twin'])}  in:{r['measured']}+imp{r['imputed']}")


def _um(v):
    return f"{v:.1f}µm" if isinstance(v, (int, float)) else "—"


if __name__ == "__main__":
    main()
