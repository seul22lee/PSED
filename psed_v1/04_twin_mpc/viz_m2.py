"""
viz_m2.py — visual review of M2 (recipes in the KB + warm-start). Produces
`m2_report.html` with two panels:

  1. Recipe grounding — every experiment lifted to a Recipe, gaps filled from the
     KB/model cascade. Per-material completeness (extracted -> filled) + how many
     fields came from covariate-conditioned KB inference vs model defaults.  (reads 02_extraction/output/recipes.json)

  2. Warm-start convergence — a controller that tunes precursor dose to hit a
     conformality target, seeded from the nearest literature process (KB) vs a
     cold mid-range guess. Warm starts nearer the answer -> fewer iterations,
     mirroring Argonne P2's -33%-samples-from-a-prior result.
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


# ---------------- panel 2: warm-start convergence ----------------
def _controller(model, D0, r, target, Dlo, Dhi, Kp=0.6, tol=0.01, N=40):
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


def warmstart_fig(material="Al2O3", target_pd=1.2e-4):
    model = channelModel.from_kb(material)
    w = kb_bridge.warm_start(material, target={"aspect_ratio": 30})
    r = w["r_star"] or 1000.0
    pAb, tpb = (1, 200), (0.01, 5)
    Dlo = max(pAb[0] ** 2 / r, tpb[0] ** 2 * r)
    Dhi = min(pAb[1] ** 2 / r, tpb[1] ** 2 * r)
    D_warm = (w["pA0"] or 100) * (w["tp0"] or 0.1)
    D_cold = np.sqrt(Dlo * Dhi)                       # neutral mid-range guess
    tw = _controller(model, D_warm, r, target_pd, Dlo, Dhi)
    tc = _controller(model, D_cold, r, target_pd, Dlo, Dhi)
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.plot(range(len(tc)), tc, "-o", color=GREY, ms=3, lw=1.6, label=f"cold start ({len(tc)} iters)")
    ax.plot(range(len(tw)), tw, "-o", color=BLUE, ms=3, lw=1.8,
            label=f"KB warm start ({len(tw)} iters)")
    ax.axhline(1, color=RED, ls="--", lw=.8); ax.text(0.5, 1.2, "1% tolerance", color=RED, fontsize=8)
    ax.set_xlabel("controller iteration"); ax.set_ylabel("|penetration error| (%)")
    ax.set_title(f"{material}: warm-start from nearest literature process", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    red = 100 * (1 - len(tw) / len(tc)) if tc else 0
    stats = {"r": r, "D_warm": D_warm, "D_cold": D_cold, "nearest": w["provenance"]["nearest"],
             "sim": w["provenance"]["similarity"], "iters_warm": len(tw), "iters_cold": len(tc),
             "reduction": red, "e0_warm": tw[0], "e0_cold": tc[0], "gpc": w["priors"]["gpc_expected"]}
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

<div class=card><h2>2 · Warm-start convergence</h2><img src="data:image/png;base64,{img2}">
<div class=legend>A dose controller tuning precursor exposure to a conformality target. The <b>KB warm start</b> seeds dose from the
nearest literature process (<span class=mono>{nearest}</span>, similarity {sim:.2f}); the cold start uses a mid-range guess.</div>
<div class=kv>
 <div><b>{iters_cold} → {iters_warm}</b><span>iterations to 1% (cold → warm)</span></div>
 <div><b>{reduction:.0f}%</b><span>fewer iterations</span></div>
 <div><b>{e0_cold:.0f}% → {e0_warm:.0f}%</b><span>starting error (cold → warm)</span></div>
 <div><b>{gpc}</b><span>GPC prior (nm) seeded into feedforward</span></div>
</div></div>
</div>"""


def main():
    img1 = grounding_fig()
    img2, s = warmstart_fig()
    out = HERE / "m2_report.html"
    out.write_text(HTML.format(img1=img1, img2=img2, **s))
    print("wrote", out)
    print(f"  warm-start: {s['iters_cold']} -> {s['iters_warm']} iters "
          f"({s['reduction']:.0f}% fewer), nearest={s['nearest']} sim={s['sim']:.2f}")


if __name__ == "__main__":
    main()
