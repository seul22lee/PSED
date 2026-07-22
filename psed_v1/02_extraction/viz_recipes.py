"""
viz_recipes.py — review the per-experiment recipes emitted by s08 (M2, 1:1).
Produces m2_recipes.html: completeness distribution, a sample recipe table
(recipe=process vs structure=sample), and the Argonne-JSON a recipe emits once a
reactor config + species are supplied.
"""
import base64, io, json, glob
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import recipe as recipe_mod

BLUE, GREEN, GREY = "#2a78d6", "#1baf7a", "#8b919b"
ROOT = Path(__file__).parent


def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


def main():
    E = []
    for f in glob.glob(str(ROOT / "output/*/resolved/experiments.json")):
        E += json.load(open(f))
    R = [e for e in E if e.get("analysis_ready") and e.get("recipe")]
    comp = [e["recipe"]["completeness"] for e in R]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.hist(comp, bins=12, color=BLUE, edgecolor="white")
    ax.set_xlabel("recipe completeness"); ax.set_ylabel("# experiments")
    ax.set_title("1 recipe per experiment — completeness", fontsize=10)
    img = _png(fig)

    # sample table across papers/granularities
    seen, rows = set(), ""
    for e in sorted(R, key=lambda e: e.get("exp_id", "")):
        key = (e["exp_id"].split("-F")[0], e["granularity"])
        if key in seen:
            continue
        seen.add(key)
        r = e["recipe"]
        rx = ", ".join(f"{x['label']}:{x['role'][:4]} dose={x['dose_time']} p={x['partial_pressure']}"
                       for x in r["reactants"]) or "—"
        st = r.get("structure") or {}
        rows += (f"<tr><td class=m>{e['exp_id']}</td><td>{r['material']}</td><td class=m>{r['cycle_sequence']}</td>"
                 f"<td class=sm>{rx}</td><td class=m>{r['ncycles']}</td><td class=m>{r['temperature']}</td>"
                 f"<td class=sm>H={st.get('H')} W={st.get('W')}</td>"
                 f"<td class=m style='color:{BLUE}'>{r['completeness']}</td></tr>")
        if len(seen) >= 10:
            break

    # Argonne JSON demo: inject species for one Al2O3 recipe, resolve to a reactor
    e = next(e for e in R if e["material"] == "Al2O3" and e["recipe"]["reactants"])
    rec = recipe_mod.from_experiment(e)
    if rec.reactants:
        rec.reactants[0].species, rec.reactants[1].species = "TMA", "water"
    chan = ["TMA", "water", "DEZ", "TDMAHf", "Si2H6", "WF6", "TTIP", "MgCp2"]
    recipe_mod.resolve_channels(rec, chan)
    argo = json.dumps(recipe_mod.to_process(rec))

    html = f"""<title>M2 · recipes (1 per experiment)</title><style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1040px;margin:0 auto;padding:26px 22px}}h1{{font-size:22px;margin:0 0 2px}}
.sub{{color:#565c66;margin-bottom:16px}}.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}}table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8b919b;font-size:10.5px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:5px 8px;border-bottom:1px solid #eef0f3}}.m{{font-family:ui-monospace,Menlo,monospace}}.sm{{font-size:11px;color:#565c66}}
code{{background:#eef0f3;padding:2px 6px;border-radius:5px;font-size:12px}}
</style><div class=wrap>
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600">PSED · M2</div>
<h1>Recipes — one per experiment</h1>
<div class=sub>Each experiment carries its own <b>recipe</b> (reactor process: chemistry + dose/purge + ncycles + temperature),
kept separate from <b>structure</b> (sample H/W). {len(R)} analysis-ready experiments, all with a recipe.</div>
<div class=card><h2>Completeness</h2><img src="data:image/png;base64,{img}" style="max-width:520px">
<div class=sm>Process fields (chemistry, dose, pressure, T) populate well; the low tail is missing <b>purge_time / ncycles / species</b>
— the recipe fields that live in methods text / precursor identity (fixes #2, #3).</div></div>
<div class=card><h2>Sample recipes <span class=sm>(recipe = process · structure = sample, shown separately)</span></h2>
<table><tr><th>exp_id</th><th>material</th><th>seq</th><th>reactants (process)</th><th>ncycles</th><th>T</th><th>structure (sample)</th><th>complete</th></tr>{rows}</table></div>
<div class=card><h2>Reactor-ready (Argonne JSON)</h2>
<div class=sm>A recipe resolves against a reactor's channels and emits the exact Argonne answer format — once species are known
(here Al₂O₃ → A=TMA, B=water; species linkage is fix #2):</div>
<p><code>{argo}</code></p></div>
</div>"""
    out = ROOT / "m2_recipes.html"
    out.write_text(html)
    print("wrote", out, "|", len(R), "recipes, mean completeness",
          round(sum(comp) / len(comp), 2))


if __name__ == "__main__":
    main()
