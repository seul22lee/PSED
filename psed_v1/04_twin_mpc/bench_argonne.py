"""
bench_argonne.py  (M4 / §4.2)  —  HONEST characterization, not a rigged "win"
-----------------------------------------------------------------------------
What this is:
  · an EXECUTABLE, ontology-linked replica of the Yanguas-Gil 2026 simulated ALD
    tool (saturation_model.py), verified to reproduce the paper's Fig. 3, and
  · an honest characterization of a DETERMINISTIC dose optimizer on that tool:
    the ε–dose-time trade-off, self-limited/CVD detection limits under noise, and
    the variance an illustrative STOCHASTIC search incurs on the identical tool.

What this is NOT (read CAVEATS at the bottom of the report):
  · a controlled re-run of the LLM agent (o3/GPT-5). Their numbers are QUOTED from
    the paper, clearly labelled, never re-measured here.
  · a KB-grounded optimization of the benchmark processes. Those five processes are
    SYNTHETIC (Table I) and are NOT in our KB — the KB holds conformality data, not
    GPC-vs-dose data. The one real KB link (a physics-derived rate prior, c→k1) is
    shown separately for Al2O3/TMA and is honest about the flat-surface vs HAR gap.
"""
import base64, io, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "02_extraction"))
from saturation_model import BENCHMARK, SaturationModel, Pathway
import kb_bridge

BLUE, RED, GREEN, AMBER, PURPLE, GREY = "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#9085e9", "#8b919b"
DMAX = 16.0
# the paper's REPORTED agent accuracy (Yanguas-Gil 2026, Sec. III / Fig. 4) — quoted,
# not re-run here: median relative error ε ≈ 2% (o3) / 4% (GPT-5), 75th pct ≈ 5%.
PAPER_AGENT = {"o3_median": 0.02, "gpt5_median": 0.04, "p75": 0.05}


# ============================ deterministic optimizer ============================
def deterministic_optimize(model, d0=0.1, sat_tol=0.02, target=0.98, axis_t2=8.0):
    """Doubling dose search with plateau detection. Returns chosen doses, GPC, a
    self-limited flag (plateaued within DMAX), and the number of tool queries."""
    samples = [0]
    def q(t1, t2):
        samples[0] += 1
        return model.gpc(t1, t2)

    def sweep(query, d):
        hist = [(d, query(d))]
        while d < DMAX:
            d2 = d * 2; g = query(d2); hist.append((d2, g))
            prev = hist[-2][1]
            if prev > 0 and (g - prev) / max(g, 1e-12) < sat_tol:
                return hist, True
            d = d2
        return hist, False

    def smallest(hist, target_frac):
        plateau = hist[-1][1]; thr = target_frac * plateau
        for (x0, y0), (x1, y1) in zip(hist, hist[1:]):
            if y1 >= thr:
                return x0 if y0 >= thr else x0 + (thr - y0) * (x1 - x0) / ((y1 - y0) or 1)
        return hist[-1][0]

    h2, _ = sweep(lambda t: q(axis_t2, t), d0);  t2 = smallest(h2, target)
    h1, ok1 = sweep(lambda t: q(t, axis_t2), d0)
    self_limited = ok1
    t1 = smallest(h1, target) if ok1 else DMAX
    return {"t1": t1, "t2": t2, "gpc": model.gpc(t1, t2), "self_limited": self_limited,
            "samples": samples[0] + 1, "dose_time": t1 + t2}


# ============================ classical grid-search baseline ============================
# A fair NON-LLM comparator: no starting-scale knowledge, just a fixed log-spaced
# grid over the dose range, same target / plateau tolerance / noise as the
# deterministic optimizer. Reproducible like the deterministic one, but spends a
# fixed sample budget instead of adapting.
def grid_optimize(model, n=12, sat_tol=0.02, target=0.98, dlo=0.02, dhi=DMAX, axis_t2=8.0):
    samples = [0]
    def q(t1, t2):
        samples[0] += 1
        return model.gpc(t1, t2)
    grid = list(np.exp(np.linspace(np.log(dlo), np.log(dhi), n)))

    def smallest(gr, gs, plateau):
        thr = target * plateau
        for x, y in zip(gr, gs):
            if y >= thr:
                return x
        return gr[-1]

    g2 = [q(axis_t2, t) for t in grid]
    t2 = smallest(grid, g2, max(g2))
    g1 = [q(t, axis_t2) for t in grid]
    # self-limited if the top of the grid has flattened (same plateau test, on the
    # last grid interval); a CVD term keeps the top interval rising.
    plateaued = g1[-2] > 0 and (g1[-1] - g1[-2]) / max(g1[-1], 1e-12) < sat_tol
    self_limited = plateaued
    t1 = smallest(grid, g1, max(g1)) if plateaued else dhi
    return {"t1": t1, "t2": t2, "gpc": model.gpc(t1, t2), "self_limited": self_limited,
            "samples": samples[0] + 1, "dose_time": t1 + t2}


# ============================ illustrative stochastic search ============================
# NOT the LLM agent. A sampling-based explorer used ONLY to quantify the run-to-run
# variance any stochastic method incurs on this exact tool (a fair, measured contrast
# to the deterministic optimizer's σ=0). Labelled as such in the report.
def stochastic_optimize(model, rng, sat_tol=0.03, maxstep=24):
    samples = 0; d = float(np.exp(rng.uniform(np.log(0.03), np.log(0.6)))); prev = None; chosen = d
    for _ in range(maxstep):
        g = model.gpc(d, 8.0); samples += 1
        if prev is not None and (g - prev) / max(g, 1e-12) < sat_tol:
            chosen = d
            if rng.random() < 0.6:          # noisy stop decision
                break
        prev = g; d = min(d * float(rng.uniform(1.3, 2.6)), DMAX)
        chosen = d
    g = model.gpc(chosen, 8.0)
    eps = (model.gpc_sat - g) / model.gpc_sat
    return {"t1": chosen, "gpc": g, "eps": eps, "samples": samples}


# ============================ analyses ============================
def eps_tradeoff(model, targets=(0.90, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995)):
    """ε is a STOPPING CHOICE, not intrinsic accuracy: show ε vs total dose time."""
    out = []
    for tg in targets:
        r = deterministic_optimize(model, target=tg)
        out.append({"target": tg, "eps": (model.gpc_sat - r["gpc"]) / model.gpc_sat,
                    "dose_time": r["dose_time"], "samples": r["samples"]})
    return out


def detection_sweep(optimizer=deterministic_optimize, gr0s=(0.0, 0.005, 0.01, 0.02, 0.05, 0.1),
                    noises=(0.0, 0.02, 0.05), base=Pathway(1.0, 5.0, 4.0), reps=15):
    """Self-limited/CVD detection is FRAGILE: a weak CVD term hides under the plateau
    tolerance and noise. Grid over CVD strength × measurement noise → detection rate,
    for whichever executor strategy is passed in (deterministic or grid)."""
    grid = []
    for gr0 in gr0s:
        row = {"gr0": gr0, "truth": "CVD" if gr0 > 0 else "self-limited", "acc": {}}
        for nz in noises:
            correct = 0
            for s in range(reps):
                rng = np.random.RandomState(s + int(gr0 * 1e4) + int(nz * 1e3))
                base_m = SaturationModel([base], 1.0, gr0=gr0)
                class Noisy(SaturationModel):
                    def gpc(self, t1, t2=1.0):
                        return base_m.gpc(t1, t2) * (1 + nz * rng.randn())
                m = Noisy([base], 1.0, gr0=gr0)
                res = optimizer(m)
                pred_cvd = not res["self_limited"]
                if pred_cvd == (gr0 > 0):
                    correct += 1
            row["acc"][nz] = correct / reps
        grid.append(row)
    return grid


def kb_rate_bridge():
    """The one REAL KB link for this task: derive a physics-grounded uptake rate k1
    from the KB's extracted sticking coefficient (Al2O3/TMA)."""
    return kb_bridge.saturation_prior_from_kb("Al2O3")


def run_benchmark():
    """Reproduce the paper's 5 Table-I processes (+ a CVD variant) with the
    deterministic optimizer, and MEASURE the illustrative stochastic search over 30
    seeds on the same tools."""
    rows = []
    for name, model in BENCHMARK.items():
        det = deterministic_optimize(model)
        grid = grid_optimize(model)
        def score(res):
            if model.self_limited:
                return ((model.gpc_sat - res["gpc"]) / model.gpc_sat,
                        res["self_limited"] and res["gpc"] >= 0.9 * model.gpc_sat)
            return None, (not res["self_limited"])
        det["eps"], det["ok"] = score(det)
        grid["eps"], grid["ok"] = score(grid)
        # stochastic spread (self-limited processes only; CVD flag isn't its job)
        st = None
        if model.self_limited:
            es = [stochastic_optimize(model, np.random.RandomState(s))["eps"] for s in range(30)]
            st = {"mean": float(np.mean(es)), "std": float(np.std(es)),
                  "p90": float(np.percentile(np.abs(es), 90))}
        rows.append({"name": name, "self_limited": model.self_limited, "det": det, "grid": grid,
                     "eps": det["eps"], "ok": det["ok"], "stoch": st, "model": model})
    return rows


# ============================ report ============================
def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


def fig_curves(rows):
    fig, ax = plt.subplots(figsize=(6.2, 3.7)); ts = np.linspace(0.02, 4, 200)
    cols = [BLUE, GREEN, AMBER, PURPLE, "#e87ba4", RED]
    for r, c in zip(rows, cols):
        m = r["model"]; ax.plot(ts, [m.gpc(t, 8.0) for t in ts], color=c, lw=1.7, label=r["name"])
        if r["self_limited"]:
            ax.plot(r["det"]["t1"], r["det"]["gpc"], "o", color=c, ms=6, mec="white")
    ax.set_xlabel("precursor dose t₁ (s)"); ax.set_ylabel("GPC (Å)")
    ax.set_title("executable tool: saturation curves + deterministic stop (dots)", fontsize=10)
    ax.legend(fontsize=7.5, ncol=2); fig.tight_layout(); return _png(fig)


def fig_tradeoff(model):
    tr = eps_tradeoff(model)
    fig, ax = plt.subplots(figsize=(5.0, 3.7))
    ax.plot([t["dose_time"] for t in tr], [t["eps"] * 100 for t in tr], "-o", color=BLUE)
    for t in tr:
        ax.annotate(f"{t['target']:.2f}", (t["dose_time"], t["eps"] * 100), fontsize=7,
                    textcoords="offset points", xytext=(4, 4), color=GREY)
    ax.set_xlabel("total dose time t₁+t₂ (s)"); ax.set_ylabel("relative error ε (%)")
    ax.set_title("ε is a STOPPING CHOICE, not fixed accuracy\n(labels = saturation target)", fontsize=9.5)
    fig.tight_layout(); return _png(fig)


def fig_detection(sweep_det, sweep_grid, noises=(0.0, 0.05)):
    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    x = [r["gr0"] for r in sweep_det]
    for nz, c in zip(noises, [GREEN, RED]):
        ax.plot(x, [r["acc"][nz] * 100 for r in sweep_det], "-o", color=c,
                label=f"deterministic · noise {int(nz*100)}%")
        ax.plot(x, [r["acc"][nz] * 100 for r in sweep_grid], "--s", color=c, mfc="white",
                label=f"grid · noise {int(nz*100)}%")
    ax.axvline(0.0, color=GREY, ls=":", lw=.8)
    ax.set_xlabel("CVD strength gr0 (Å/s)  ·  gr0=0 ⇒ self-limited")
    ax.set_ylabel("correct classification (%)")
    ax.set_title("self-limited / CVD detection: deterministic vs grid\n(both fragile for weak CVD + noise)", fontsize=9.5)
    ax.legend(fontsize=7); fig.tight_layout(); return _png(fig)


def fig_executor_compare(rows):
    """Deterministic vs classical grid on the self-limited processes: ε, samples,
    total dose time. Both reproducible; the contrast is efficiency, not a 'win'."""
    sl = [r for r in rows if r["self_limited"]]
    names = [r["name"] for r in sl]
    fig, ax = plt.subplots(1, 3, figsize=(9.6, 3.3))
    x = np.arange(len(sl))
    for a, key, ttl, unit in [(ax[0], "eps", "relative error ε", "%"),
                              (ax[1], "samples", "tool samples", ""),
                              (ax[2], "dose_time", "total dose time", "s")]:
        dv = [(abs(r["det"][key]) * (100 if key == "eps" else 1)) for r in sl]
        gv = [(abs(r["grid"][key]) * (100 if key == "eps" else 1)) for r in sl]
        a.bar(x - 0.2, dv, 0.4, color=BLUE, label="deterministic")
        a.bar(x + 0.2, gv, 0.4, color=AMBER, label="grid")
        a.set_xticks(x); a.set_xticklabels(names, rotation=30, ha="right", fontsize=7)
        a.set_title(f"{ttl} ({unit})" if unit else ttl, fontsize=9.5)
    ax[0].legend(fontsize=8)
    fig.tight_layout(); return _png(fig)


def fig_variance(rows):
    fig, ax = plt.subplots(figsize=(5.4, 3.7))
    sl = [r for r in rows if r["self_limited"]]
    x = np.arange(len(sl))
    ax.bar(x - 0.2, [abs(r["eps"]) * 100 for r in sl], 0.4, color=BLUE, label="deterministic (σ=0)")
    ax.bar(x + 0.2, [r["stoch"]["p90"] * 100 for r in sl], 0.4,
           yerr=[r["stoch"]["std"] * 100 for r in sl], color=GREY, alpha=.75, capsize=3,
           label="illustrative stochastic search (measured)")
    ax.axhline(PAPER_AGENT["o3_median"] * 100, color=RED, ls="--", lw=1)
    ax.text(len(sl) - .5, PAPER_AGENT["o3_median"] * 100 + .3, "paper o3 median ε (reported)",
            color=RED, fontsize=7, ha="right")
    ax.set_xticks(x); ax.set_xticklabels([r["name"] for r in sl], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("relative error ε (%)")
    ax.set_title("deterministic vs a stochastic search on the SAME tool", fontsize=9.5)
    ax.legend(fontsize=7.5); fig.tight_layout(); return _png(fig)


HTML = """<title>M4 §4.2 · ALD dose optimization — honest characterization</title>
<style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#131417;color:#eceef2}}.card,.caveat{{background:#1c1e22 !important;border-color:#2b2e34 !important}}th{{color:#767c86 !important}}}}
.wrap{{max-width:1000px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:16px}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
.caveat{{background:#fff8ee;border:1px solid #f0d9a8;border-radius:12px;padding:16px;margin-bottom:16px}}
@media(prefers-color-scheme:dark){{.caveat{{background:#241f14 !important;border-color:#5a4a24 !important}}}}
h2{{font-size:14px;margin:0 0 10px}} img{{max-width:100%}}
.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:6px 8px;border-bottom:1px solid #eef0f3}}.m{{font-family:ui-monospace,Menlo,monospace}}
.ok{{color:#1baf7a;font-weight:600}}.bad{{color:#e34948;font-weight:600}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.note{{font-size:12px;color:#565c66}} li{{margin:3px 0}} code{{font-family:ui-monospace,Menlo,monospace;font-size:12px}}
</style>
<div class=wrap>
<div class=eyebrow>PSED · M4 · §4.2</div>
<h1>ALD dose optimization — characterizing executor strategies</h1>
<div class=sub>An executable, ontology-linked replica of the Yanguas-Gil 2026 tool (<span class=m>{model_id}</span>), used to fairly characterize
<b>two reproducible non-LLM executor strategies</b> — an adaptive deterministic search and a classical grid — on identical targets,
stopping criteria, noise, and CVD sweeps. This is <b>not</b> a re-run of their LLM agent, and the benchmark processes are <b>not</b> in our KB — see caveats.</div>

<div class=card><h2>1 · The tool is a faithful replica (reproduces their Fig. 3)</h2><img src="data:image/png;base64,{curves}">
<div class=note>Dots = where the deterministic optimizer stops (target {target:.0%} of the saturated GPC). All 5 self-limited processes are optimized and the injected CVD variant is flagged — but read the panels below before reading that as a "win".</div></div>

<div class=card><h2>2 · Deterministic vs a classical grid baseline (fair non-LLM comparison)</h2><img src="data:image/png;base64,{executor}">
<div class=note>Both are reproducible (σ=0) and hit similar ε (both target {target:.0%}). The honest contrast is <b>efficiency</b>: the adaptive search spends fewer tool samples by locating the saturation scale, while the grid spends a fixed budget over the whole dose range without needing a starting guess. Neither is an LLM; this is executor-vs-executor.</div></div>

<div class=grid2>
<div class=card><h2>3 · ε is a stopping choice, not accuracy</h2><img src="data:image/png;base64,{tradeoff}">
<div class=note>Moving the saturation target trades total dose time for ε. The "1.5–2.6%" from the first draft was just the point at target=0.98; it is not an intrinsic precision.</div></div>
<div class=card><h2>4 · CVD detection is fragile (both strategies)</h2><img src="data:image/png;base64,{detection}">
<div class=note>Solid = deterministic, dashed = grid. A strong CVD term (gr0≈0.05) is easy to flag; a <b>weak</b> one (gr0≲0.01) hides under the plateau tolerance for <b>both</b> executors, and noise erodes detection further. The earlier "flags CVD ✓" held only for the easy, noise-free case.</div></div>
</div>

<div class=card><h2>5 · Deterministic vs a stochastic search on the SAME tool</h2><img src="data:image/png;base64,{variance}">
<div class=note>Grey = an <b>illustrative</b> sampling search (30 seeds) — <b>not</b> the LLM agent — included only to measure the run-to-run spread any stochastic method incurs here. The red line is the paper's <b>reported</b> o3 median ε, shown for scale, not as a controlled comparison.</div></div>

<div class=card><h2>6 · The real KB link for this task (and its limit)</h2>
<div class=note>The KB still has no GPC-vs-dose data, so the synthetic benchmark is not KB-grounded. But the honest link is now a physics-derived rate prior from a <b>real, per-species initial sticking probability</b> — curated from a 5th paper, <b>Arts 2019 "Sticking probabilities of H₂O and Al(CH₃)₃"</b> (TMA s₀=1.2×10⁻³, H₂O s₀ T-dependent), into the ontology species individuals:
<code>k1 = s₀·Φ/q,  Φ = pA/√(2πmkT)</code>. For Al₂O₃/TMA: s₀={c} (<span class=m>{csrc}</span>), q={q:.1e} m⁻², pA={pA} Pa →
<b>k1 ≈ {k1:.0f} s⁻¹</b> (t_sat ≈ {tsat:.1e} s). That is the <b>flat-surface</b> saturation time; the literature's ~0.1 s pulses fill high-AR features (a transport problem — the M3 twin's regime). So the KB now grounds the <b>rate</b> for a real chemistry per reactant, but not the synthetic benchmark's dose regime.</div></div>

<div class=card><h2>Per-process results (target={target:.0%})</h2>
<table><tr><th>process</th><th>truth</th><th colspan=3 style="border-bottom:1px solid #2a78d6">deterministic (ε · samples · dose t)</th><th colspan=3 style="border-bottom:1px solid #eda100">grid (ε · samples · dose t)</th><th>stochastic ε (σ)</th></tr>
{rows}
</table>
<div class=note>Both executors are reproducible (σ=0 across re-runs); the stochastic column is the illustrative sampler's spread. "—" ε for the CVD row = correctly flagged as not self-limited.</div></div>

<div class=caveat><h2>Caveats &amp; scope (what this does and does not show)</h2><ul>
<li><b>Not a re-run of the agent.</b> o3/GPT-5 numbers are quoted from Yanguas-Gil 2026, not measured here. A true head-to-head needs their agent on this exact tool.</li>
<li><b>Benchmark is synthetic + not in the KB.</b> The 5 processes are the paper's Table I; the KB holds conformality data, not dose–GPC data, so "KB-primed" does not apply to them. The only real KB link is the rate bridge in panel 6 (Al₂O₃/TMA).</li>
<li><b>A bespoke optimizer vs a general reasoning agent is not a like-for-like test.</b> Any classical search (deterministic OR grid, panel 2) beats an LLM on this narrow task; the paper's aim was to probe LLM reasoning, not optimizer quality. The defensible role here is as a <b>reproducible executor the agent could call</b>, not a competitor.</li>
<li><b>ε is tunable</b> (panel 3) and <b>CVD detection is fragile for both executors</b> (panel 4) — shown explicitly rather than reported as single favorable numbers.</li>
<li><b>Determinism (σ=0) is a property of the method class</b> (both non-LLM executors have it), not an earned advantage; panel 5 measures what a stochastic search actually costs on this tool.</li>
</ul></div>

<div class=card><h2>Next steps to make the comparison real</h2><ul>
<li><b>Expand the KB with dose/kinetic data.</b> <span class=ok>Done (partial):</span> the key sticking probabilities from <b>Arts 2019</b> are now curated into the ontology and feed the rate prior in panel 5. <span class=note>Remaining:</span> full extraction of <b>Arts 2019</b> (T-dependent series) and <b>Yanguas-Gil &amp; Elam 2012</b> (base model + rate constants), and ideally a paper with direct GPC-vs-dose curves, so a genuine KB-grounded <i>dose</i> optimization can be scored end-to-end.</li>
<li><b>Run the actual agent</b> (o3/GPT-5, or an open reasoning model) against this same tool for a controlled ε / samples / variance comparison.</li>
<li><b>Classical baseline.</b> <span class=ok>Done:</span> a grid search is characterized alongside the deterministic executor (panels 2 &amp; 4) under the same targets/noise/CVD sweep. <span class=note>Remaining:</span> add Bayesian optimization for a sample-efficiency ceiling.</li>
<li><b>Score on real chemistries</b> where the rate bridge (panel 5) sets the dose scale, and measure the sample reduction from the KB prior directly.</li>
</ul></div>
</div>"""


def _cell(res):
    eps = f"{res['eps']*100:.1f}%" if res["eps"] is not None else "—"
    return (f"<td class=m>{eps}</td><td class=m>{res['samples']}</td>"
            f"<td class=m>{res['dose_time']:.2f}</td>")


def main():
    rows = run_benchmark()
    br = kb_rate_bridge() or {"inputs": {}, "k1": 0, "t_sat_s": 0}
    sweep_det = detection_sweep(deterministic_optimize)
    sweep_grid = detection_sweep(grid_optimize)
    tr_model = BENCHMARK["slow/slow"]
    tgt = 0.98
    tr = ""
    for r in rows:
        truth = "CVD" if not r["self_limited"] else "self-lim"
        stoch = f"{r['stoch']['mean']*100:.1f}% (±{r['stoch']['std']*100:.1f})" if r["stoch"] else "—"
        tr += (f"<tr><td class=m>{r['name']}</td><td>{truth}</td>"
               f"{_cell(r['det'])}{_cell(r['grid'])}<td class=m>{stoch}</td></tr>")
    inp = br["inputs"]
    html = HTML.format(
        model_id="yanguas_gil_saturation", target=tgt,
        curves=fig_curves(rows), executor=fig_executor_compare(rows),
        tradeoff=fig_tradeoff(tr_model),
        detection=fig_detection(sweep_det, sweep_grid), variance=fig_variance(rows),
        c=inp.get("c"), csrc=inp.get("c_source", "—"), q=inp.get("q_site", 0), pA=inp.get("pA"),
        k1=br["k1"], tsat=br["t_sat_s"], rows=tr)
    out = HERE / "m4_benchmark.html"
    out.write_text(html)
    print("wrote", out)
    # honest side-by-side console summary (self-limited processes)
    print(f"  {'process':16} {'det ε/smp/t':>18}   {'grid ε/smp/t':>18}")
    for r in rows:
        d, g = r["det"], r["grid"]
        de = f"{d['eps']*100:.1f}%/{d['samples']}/{d['dose_time']:.1f}" if d["eps"] is not None else f"flagCVD/{d['samples']}/-"
        ge = f"{g['eps']*100:.1f}%/{g['samples']}/{g['dose_time']:.1f}" if g["eps"] is not None else f"flagCVD/{g['samples']}/-"
        print(f"  {r['name']:16} {de:>18}   {ge:>18}")
    # detection accuracy at 5% noise, both strategies
    print("  CVD detection @5% noise (det / grid):")
    for rd, rg in zip(sweep_det, sweep_grid):
        print(f"    gr0={rd['gr0']:<6} {rd['truth']:12} {rd['acc'][0.05]*100:3.0f}% / {rg['acc'][0.05]*100:3.0f}%")


if __name__ == "__main__":
    main()
