"""
viz_m1.py — visual review of the M0/M1 result: the conformality twin, now
parameterised from the KB. Produces a self-contained report `m1_report.html`
(+ PNGs) showing (1) per-parameter provenance (hardcoded default vs KB value,
source, σ, papers) and (2) the reactant-penetration profile with hardcoded vs
KB parameters, PD50 marked.
"""
import base64, io, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


from twin.channel_model import channelModel, PARAMS
from twin import kb_bridge

BLUE, RED, GREEN, INK, GREY = "#2a78d6", "#e34948", "#1baf7a", "#14161a", "#8b919b"


def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(b.getvalue()).decode()


def profile_fig(material="Al2O3"):
    hard = channelModel()                               # hardcoded defaults
    kb = channelModel.from_kb(material)                 # KB-parameterised
    xmax = 1.25 * max(_xs(hard), _xs(kb))
    x = np.linspace(0, xmax, 500)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for m, c, lab in [(hard, RED, "hardcoded default"), (kb, BLUE, f"KB ({material})")]:
        m.prepare()
        _, _, info = m.approx(x.copy(), np.zeros_like(x))
        pn = info["pA"] / info["pA"][0]
        ax[0].plot(x * 1e6, pn, color=c, lw=2, label=lab)
        pd = m.penetration_depth() * 1e6
        ax[0].axvline(pd, color=c, ls=":", lw=1)
        ax[0].plot([pd], [0.5], "o", color=c)
    ax[0].axhline(0.5, color=GREY, ls="--", lw=.8)
    ax[0].set_xlabel("channel position x (µm)"); ax[0].set_ylabel("reactant pressure p$_A$/p$_A$(0)")
    ax[0].set_title("penetration profile — PD50 marked", fontsize=10); ax[0].legend(fontsize=8)
    # coverage-per-material bar
    mats = ["Al2O3", "TiO2", "HfO2", "SiO2"]
    kbn, matn, defn = [], [], []
    tot = len(kb_bridge.PARAM_MAP) + len(kb_bridge.MATERIAL_MAP)
    for mm in mats:
        _, prov = kb_bridge.params_for(mm)
        kbn.append(sum(1 for p in prov.values() if p["source"] == "kb"))
        matn.append(sum(1 for p in prov.values() if p["source"] == "material"))
        defn.append(tot - kbn[-1] - matn[-1])
    b = np.arange(len(mats))
    ax[1].bar(b, kbn, color=BLUE, label="from KB")
    ax[1].bar(b, matn, bottom=kbn, color=GREEN, label="material prop")
    ax[1].bar(b, defn, bottom=np.array(kbn) + np.array(matn), color="#d0d3d8", label="default")
    ax[1].set_xticks(b); ax[1].set_xticklabels(mats); ax[1].set_ylabel("# parameters")
    ax[1].set_title("parameter grounding per material", fontsize=10); ax[1].legend(fontsize=8)
    fig.tight_layout()
    return _png(fig)


def _xs(m):
    m.prepare()
    _, _, info = m.approx(np.array([0.0]), np.array([0.0]))
    return info["xs"]


def prov_table(material="Al2O3"):
    hard = channelModel()
    kb = channelModel.from_kb(material)
    rows = ""
    for p in PARAMS:
        pr = kb.kb_provenance.get(p, {"source": "default"})
        src = pr["source"]
        col = {"kb": BLUE, "material": GREEN, "default": GREY}[src]
        extra = (f"±{pr.get('sigma',0):.3g} · n={pr.get('n')} · {','.join(pr.get('refs',[]))}"
                 if src == "kb" else (pr.get("property", "") if src == "material" else "channelModel default"))
        rows += (f"<tr><td class=m>{p}</td><td class=m>{getattr(hard,p):.4g}</td>"
                 f"<td class=m style='color:{col}'>{getattr(kb,p):.4g}</td>"
                 f"<td style='color:{col}'>{src}</td><td class=sm>{extra}</td></tr>")
    return rows


HTML = """<title>M1 · KB-parameterised conformality twin</title>
<style>
body{{margin:0;background:#f4f6f8;color:#14161a;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1000px;margin:0 auto;padding:26px 22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:#565c66;margin-bottom:18px}}
.card{{background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:16px;margin-bottom:16px}}
h2{{font-size:14px;margin:0 0 10px}}
img{{max-width:100%}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{text-align:left;color:#8b919b;font-size:11px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #e6e8ec}}
td{{padding:5px 8px;border-bottom:1px solid #eef0f3}}.m{{font-family:ui-monospace,Menlo,monospace}}.sm{{font-size:11px;color:#565c66}}
.legend{{font-size:12px;color:#565c66;margin-top:6px}}.legend b{{color:#2a78d6}}
</style>
<div class=wrap>
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8b919b;font-weight:600">PSED · M1</div>
<h1>Conformality twin, parameterised from the KB</h1>
<div class=sub>The Ylilammi channel model no longer hardcodes one process — each parameter is resolved
<b style="color:#2a78d6">KB literature</b> → <b style="color:#1baf7a">material property</b> → <b style="color:#8b919b">model default</b>.</div>
<div class=card><h2>Penetration profile &amp; parameter grounding</h2><img src="data:image/png;base64,{img}">
<div class=legend>Left: reactant-pressure penetration for the <b style="color:#e34948">hardcoded</b> vs <b>KB-grounded</b> twin (Al₂O₃), PD50 marked.
Right: how many of the 16 twin parameters are literature-grounded per material.</div></div>
<div class=card><h2>Parameter provenance — Al₂O₃</h2>
<table><tr><th>param</th><th>hardcoded</th><th>KB value (SI)</th><th>source</th><th>detail (σ · n · papers)</th></tr>{rows}</table></div>
</div>"""


def main():
    img = profile_fig("Al2O3")
    rows = prov_table("Al2O3")
    out = Path(__file__).parent / "m1_report.html"
    out.write_text(HTML.format(img=img, rows=rows))
    print("wrote", out)


if __name__ == "__main__":
    main()
