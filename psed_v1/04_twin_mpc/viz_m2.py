"""
viz_m2.py — LEGACY, NON-CANONICAL M2 visualisation.

The canonical M2 report is produced by m2_design.py at 04_twin_mpc/m2_report.html.
This module no longer writes any artifact; its two figure builders remain importable
so the canonical report (or an ad-hoc review) can reuse them. Two panels:

  1. Recipe grounding — every experiment lifted to a Recipe, gaps filled from the
     KB/model cascade. Per-material completeness (extracted -> filled) + how many
     fields came from covariate-conditioned KB inference vs model defaults.  (reads 02_extraction/output/recipes.json)

  2. Target dose by twin inversion — given a target penetration depth and a fixed
     pA/tp ratio, solve F(D;r) = PD_target directly for the dose, by bracketed root
     finding on the channel model (inverse_solver.solve_target_dose). This is
     one-dimensional target matching at a fixed ratio, NOT general ALD recipe
     optimisation and not a controller: feasibility is decided from the achievable
     PD range before any iteration, so an unreachable target is reported as such
     instead of running to an iteration cap. The KB warm start supplies the ratio
     and a literature reference dose; the root does not depend on it.
"""
import base64, io, json, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "02_extraction"))
from channel_model import channelModel
import kb_bridge, kb_service
import inverse_solver

BLUE, RED, GREEN, AMBER, INK, GREY = "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#14161a", "#8b919b"
RECIPES = HERE.parent / "02_extraction" / "output" / "recipes.json"


def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


# ---------------- panel 1: recipe grounding ----------------
def grounding_fig():
    rows = json.loads(RECIPES.read_text())
    by = defaultdict(list)
    for r in rows:
        by[r.get("material") or "—"].append(r)
    mats = sorted(by, key=lambda m: -len(by[m]))
    ext = [np.mean([r["completeness_extracted"] for r in by[m]]) for m in mats]
    fil = [np.mean([r["completeness_filled"] for r in by[m]]) for m in mats]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    y = np.arange(len(mats))
    ax[0].barh(y, fil, color=BLUE, alpha=.35, label="after KB/model fill")
    ax[0].barh(y, ext, color=GREEN, label="extracted from paper")
    ax[0].set_yticks(y); ax[0].set_yticklabels([f"{m} (n={len(by[m])})" for m in mats])
    ax[0].set_xlim(0, 1); ax[0].invert_yaxis()
    ax[0].set_xlabel("recipe completeness"); ax[0].legend(fontsize=8, loc="lower right")
    ax[0].set_title("recipes get fuller from the cascade", fontsize=10)
    # source mix
    nkb = sum(1 for r in rows for m in (r.get("param_sources") or {}).values()
              if isinstance(m, dict) and m.get("source") == "kb")
    nmodel = sum(1 for r in rows for m in (r.get("param_sources") or {}).values()
                 if isinstance(m, dict) and m.get("source") == "model")
    ax[1].bar(["KB inferred\n(similar exps)", "model default"], [nkb, nmodel], color=[BLUE, AMBER])
    ax[1].set_ylabel("# fields filled")
    ax[1].set_title(f"gap-fills across {len(rows)} recipes", fontsize=10)
    for i, v in enumerate([nkb, nmodel]):
        ax[1].text(i, v, str(v), ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    return _png(fig)


# ---------------- panel 2: target dose by twin inversion ----------------
def _legacy_controller(model, D0, r, target, Dlo, Dhi, Kp=0.6, tol=0.01, N=40):
    """LEGACY / INTERNAL — retained only so tests can compare against the solver.

    The former primary M2 path: multiply the dose by (1 + Kp·e), clamp, repeat. It
    cannot distinguish "this target needs more iterations" from "this target is
    outside the model's range" — both saturate at a bound and stop at the iteration
    cap. Not exposed in the report; see inverse_solver.solve_target_dose."""
    def pen(D):
        model.pA = float(np.sqrt(D * r)); model.t_p = float(np.sqrt(D / r))
        model.prepare(); return model.penetration_depth()
    D, traj = D0, []
    for _ in range(N):
        e = (target - pen(D)) / target
        traj.append(abs(e) * 100)
        if abs(e) < tol:
            break
        D = min(max(D * (1 + Kp * e), Dlo), Dhi)
    return traj


#  demo configuration — provenance of every constant below:
#   target_pd 1.2e-4 m  demonstration constant chosen for this figure; NOT from a paper.
#   PA_BOUNDS (1,200) Pa / TP_BOUNDS (0.01,5) s  reactor-plausible operating limits for
#       the solver's bracket; demonstration constants, not extracted.
#   ratio r  = pA0/tp0 from the KB warm start when both exist, else RATIO_FALLBACK.
#   RATIO_FALLBACK 1000 Pa/s  documented fallback (was an inline `or 1000.0`). The KB
#       currently supplies no precursor partial pressure, so r_star is None and this
#       fallback is what actually runs — recorded as ratio_source="fallback".
#   geometry / temperature / species come from channelModel.from_kb(material).
PA_BOUNDS, TP_BOUNDS = (1.0, 200.0), (0.01, 5.0)
RATIO_FALLBACK = 1000.0


def solve_fig(material="Al2O3", target_pd=1.2e-4):
    """Panel 2 — solve the dose that makes the twin hit `target_pd` (metres).

    One-dimensional target matching at a fixed pA/tp ratio, by bracketed root finding
    on the real channel model. The KB warm start supplies the RATIO and a reference
    dose; it is not needed to start an iteration, and the root does not depend on it."""
    model = channelModel.from_kb(material)
    w = kb_bridge.warm_start(material, target={"aspect_ratio": 30})
    r_star = w["r_star"]
    r = r_star or RATIO_FALLBACK
    ratio_source = "kb" if r_star else "fallback"
    D_ref = (w["pA0"] * w["tp0"]) if (w["pA0"] and w["tp0"]) else None   # literature reference dose

    prov = {"ratio_source": ratio_source,
            "pA0_source": w["provenance"]["pA0_source"], "tp0_source": w["provenance"]["tp0_source"],
            "nearest": w["provenance"]["nearest"], "similarity": w["provenance"]["similarity"],
            "bounds_source": "demo_constant", "target_source": "demo_constant"}
    sol = inverse_solver.solve_target_dose(
        model, target_pd, r, pressure_bounds=PA_BOUNDS, pulse_time_bounds=TP_BOUNDS,
        reference={"pA0": w["pA0"], "tp0": w["tp0"], "dose": D_ref}, provenance=prov)

    lo, hi = sol.effective_dose_bounds
    Ds = np.geomspace(lo, hi, 160)
    ev = inverse_solver._Evaluator(channelModel.from_kb(material), r)
    PD = np.array([ev(d) for d in Ds]) * 1e6
    pd_min, pd_max = float(PD.min()), float(PD.max())

    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    ax.fill_between(Ds, pd_min, pd_max, color=BLUE, alpha=.06)
    ax.plot(Ds, PD, color=BLUE, lw=1.8, label="twin forward model PD(dose)")
    ax.axhline(target_pd * 1e6, color=RED, ls="--", lw=1.1)
    ax.text(Ds[0], target_pd * 1e6, f"  target {target_pd*1e6:.0f} µm", color=RED,
            fontsize=8, va="bottom")
    if D_ref:
        ax.axvline(D_ref, color=GREY, ls=":", lw=1.2)
        ax.text(D_ref, pd_min, " literature\n reference", color=GREY, fontsize=7.5, va="bottom")
    if sol.feasible:
        ax.plot([sol.dose], [sol.achieved_pd * 1e6], "o", color=GREEN, ms=9, zorder=5,
                label=f"solved  effective dose = {sol.effective_dose:.3g} Pa·s")
        ax.vlines(sol.dose, pd_min, sol.achieved_pd * 1e6, color=GREEN, lw=1, ls="--")
        ttl = f"{material}: dose solved by twin inversion"
    else:
        yb = pd_max if sol.status == "infeasible_high" else pd_min
        ax.plot([hi if sol.status == "infeasible_high" else lo], [yb], "X", color=AMBER,
                ms=11, zorder=5, label=f"boundary of achievable range ({yb:.0f} µm)")
        ttl = f"{material}: target outside achievable range ({sol.status})"
    ax.set_xscale("log")
    ax.set_xlabel("effective dose = pA · t_p  (Pa·s)"); ax.set_ylabel("penetration depth PD50 (µm)")
    ax.set_title(ttl, fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()

    stats = {"r": r, "ratio_source": ratio_source, "status": sol.status,
             "feasible": sol.feasible, "target_um": target_pd * 1e6,
             "pd_min_um": pd_min, "pd_max_um": pd_max,
             "dose": sol.dose, "pA": sol.pA, "tp": sol.pulse_time,
             "achieved_um": (sol.achieved_pd * 1e6) if sol.achieved_pd else None,
             "resid_nm": (sol.residual * 1e9) if sol.residual is not None else None,
             "evals": sol.model_evaluations, "method": sol.method or "—",
             "D_ref": D_ref, "reason": sol.reason or "",
             "nearest": w["provenance"]["nearest"], "sim": w["provenance"]["similarity"],
             "Dlo": lo, "Dhi": hi}
    return _png(fig), stats


HTML = """<title>M2 · Recipes in the KB + warm-start</title>
<style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#131417;color:#eceef2}}.card{{background:#1c1e22 !important;border-color:#2b2e34 !important}}}}
.wrap{{max-width:1000px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:18px}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}} img{{max-width:100%}}
.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600}}
.legend{{font-size:12px;color:#565c66;margin-top:8px}}.legend b{{color:#2a78d6}}
.kv{{display:flex;gap:22px;flex-wrap:wrap;font-size:12.5px;margin-top:10px}}
.kv div b{{display:block;font-size:17px}} .kv div span{{color:#8b919b;font-size:11px}}
</style>
<div class=wrap>
<div class=eyebrow>PSED · M2</div>
<h1>Recipes in the KB, and a literature warm-start for control</h1>
<div class=sub>Every experiment is lifted into an actionable <b>Recipe</b> — the object the LLM agent and the MPC twin both speak —
with missing fields filled from the <b style="color:#2a78d6">KB literature</b> / <b style="color:#eda100">model</b> cascade.
The controller then seeds itself from the nearest literature process instead of a cold guess.</div>

<div class=card><h2>1 · Recipe grounding</h2><img src="data:image/png;base64,{img1}">
<div class=legend>Left: mean recipe completeness per material — <b style="color:#1baf7a">extracted</b> from the paper vs
<b>after</b> filling gaps by covariate-conditioned inference from similar experiments / model defaults. Right: how many fields the cascade filled, and from where.
Every filled value is source-tagged (see <span class=mono>recipes.html</span>).</div></div>

<div class=card><h2>2 · Target dose by twin inversion</h2><img src="data:image/png;base64,{img2}">
<div class=legend>Given a target penetration depth and a fixed pressure-to-pulse-time ratio
<span class=mono>r = pA/t_p = {r:.0f} Pa/s</span> (source: <b>{ratio_source}</b>), the dose
<span class=mono>effective dose = pA·t_p</span> is solved directly from the twin by <b>bracketed root finding</b>
(<span class=mono>{method}</span>) — not by a controller and not by gradient descent. Feasibility is
decided from the achievable PD range <b>before</b> solving. The literature reference dose is shown for
comparison; it is a ratio prior, so the solved dose is <b>model-inverted under a literature-informed
ratio</b>, not itself literature-derived.</div>
<div class=kv>
 <div><b>{status}</b><span>solver status</span></div>
 <div><b>{pd_min_um:.0f} – {pd_max_um:.0f} µm</b><span>achievable PD range (D {Dlo:.3g}–{Dhi:.3g} Pa·s)</span></div>
 <div><b>{target_um:.0f} µm</b><span>target penetration depth</span></div>
 <div><b>{dose_s}</b><span>solved dose (Pa·s)</span></div>
 <div><b>{pA_s}</b><span>pA (Pa) · t_p (s) = {tp_s}</span></div>
 <div><b>{resid_s}</b><span>residual vs target</span></div>
 <div><b>{evals}</b><span>model evaluations</span></div>
</div>{reason_html}</div>
</div>"""


def main():
    """LEGACY / NON-CANONICAL. The canonical M2 report is produced by m2_design.py at
    04_twin_mpc/m2_report.html. This entry point no longer writes an artifact, so two
    files can never both look like the official M2 result; the figure builders above
    remain importable."""
    print("viz_m2 is legacy and non-canonical — it writes no artifact.\n"
          "The canonical M2 report is m2_design.py -> 04_twin_mpc/m2_report.html.")
    return


def _legacy_render():
    img1 = grounding_fig()
    img2, s = solve_fig()
    f = s["feasible"]
    fmt = dict(s,
               dose_s=f"{s['dose']:.4g}" if f else "—",
               pA_s=f"{s['pA']:.4g}" if f else "—",
               tp_s=f"{s['tp']:.4g}" if f else "—",
               resid_s=(f"{s['resid_nm']:+.2g} nm" if f else "—"),
               reason_html=("" if f else
                            f'<div class=legend style="color:#eda100"><b>Not solved — '
                            f'{s["status"]}.</b> {s["reason"]}</div>'))
    out = HERE / "m2_report.html"
    out.write_text(HTML.format(img1=img1, img2=img2, **fmt))
    print("wrote", out)
    print(f"  ratio r={s['r']:.4g} Pa/s (source: {s['ratio_source']}); "
          f"achievable PD {s['pd_min_um']:.2f}–{s['pd_max_um']:.2f} µm "
          f"over D {s['Dlo']:.3g}–{s['Dhi']:.3g} Pa·s")
    if f:
        print(f"  target {s['target_um']:.1f} µm -> {s['status']}: D={s['dose']:.5g} Pa·s "
              f"(pA={s['pA']:.4g} Pa, t_p={s['tp']:.4g} s), achieved {s['achieved_um']:.4f} µm "
              f"(residual {s['resid_nm']:+.2g} nm) in {s['evals']} model evaluations [{s['method']}]")
    else:
        print(f"  target {s['target_um']:.1f} µm -> {s['status']} after {s['evals']} "
              f"model evaluations: {s['reason']}")


if __name__ == "__main__":
    main()
