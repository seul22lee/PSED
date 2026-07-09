"""
build_recipes.py  (M2 — Phase 2: recipes as a first-class KB artifact)
----------------------------------------------------------------------
Lifts every resolved experiment into an actionable Recipe (the object the LLM
agent and the MPC twin both speak), fills the gaps from the KB / model cascade,
and writes two things:

  · output/recipes.json          — the queryable recipe store (recipe + sources +
                                    completeness before/after gap-fill)
  · recipes.html                 — an inspectable recipe view (dose/purge per
                                    reactant, cycle_sequence, ncycles, carrier,
                                    completeness bar, per-field source badges)

"some info may be missing but the model complements it": each filled value is
tagged extracted | kb | model so downstream control knows what is literature-
grounded vs assumed.  Run:  python3 build_recipes.py
"""
import json
from pathlib import Path
from collections import defaultdict

import kb_service as ks
import recipe as recipe_mod
import similarity as sim

ROOT = Path(__file__).parent
# a small set of model defaults the twin would supply when the KB is silent
MODEL_DEFAULTS = {"T": 573.0, "t_p": 0.1, "pA": 100.0, "pB": 300.0, "ncycles": None}


def build():
    experiments = ks._load()
    SC = sim.logscale(experiments)           # corpus log-spread, computed once
    rows = []
    for e in experiments:
        if not e.get("recipe"):
            continue
        # covariate-conditioned imputer: fills each missing field from the
        # experiments most similar to THIS one that have it (similarity-weighted)
        impute_fn = (lambda tgt: lambda q, r=None:
                     ks.impute(tgt, q, r, corpus=experiments, SC=SC))(e)
        rec = recipe_mod.from_experiment(e)
        before = rec.completeness()
        recipe_mod.fill_gaps(rec, impute_fn, MODEL_DEFAULTS)
        after = rec.completeness()
        d = rec.to_dict()
        d.update({
            "exp_id": e.get("exp_id"), "paper": e["_pid"],
            "analysis_ready": bool(e.get("analysis_ready")),
            "completeness_extracted": before, "completeness_filled": after,
        })
        rows.append(d)
    rows.sort(key=lambda r: (r.get("material") or "", -(r.get("completeness_filled") or 0)))
    (ROOT / "output" / "recipes.json").write_text(json.dumps(rows, indent=2, default=str))
    return rows


# =============================================================================
# viewer
# =============================================================================
CSS = """
:root{--bg:#f4f6f8;--panel:#fff;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;
 --line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;--c2:#1baf7a;--c3:#eda100;--c4:#4a3aa7;--c5:#e34948;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--ink:#eceef2;--ink2:#a8adb7;
 --ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;--c2:#199e70;--c3:#c98500;--c4:#9085e9;--c5:#e66767;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;--c2:#199e70;--c3:#c98500;--c4:#9085e9;--c5:#e66767;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;--c2:#1baf7a;--c3:#eda100;--c4:#4a3aa7;--c5:#e34948;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:26px 22px 60px}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-variant-numeric:tabular-nums}
h1{font-size:23px;margin:0 0 3px;font-weight:600}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);margin:2px 0 18px}
.bar{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 14px}
.stat b{font-size:19px;font-weight:600}.stat span{display:block;font-size:11px;color:var(--ink3)}
.ctl{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
select,input{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 9px;color:var(--ink);font-size:12.5px}
.mgroup{margin:22px 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);font-weight:600;border-bottom:1px solid var(--line);padding-bottom:5px}
table{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);color:var(--ink3);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td{padding:7px 9px;border-bottom:1px solid var(--line2);vertical-align:top}
tr:last-child td{border-bottom:0}
.rx{font-size:12px}
.lab{display:inline-block;min-width:15px;font-weight:700;color:var(--c4)}
.badge{display:inline-block;font-size:9.5px;padding:1px 5px;border-radius:6px;margin-left:4px;font-weight:600;letter-spacing:.02em;vertical-align:middle}
.b-extracted{background:rgba(27,175,122,.16);color:var(--c2)}
.b-kb{background:rgba(42,120,214,.16);color:var(--accent)}
.b-model{background:rgba(237,161,0,.18);color:var(--c3)}
.pbar{position:relative;height:8px;width:96px;background:var(--line2);border-radius:5px;overflow:hidden;display:inline-block;vertical-align:middle}
.pbar>i{position:absolute;left:0;top:0;bottom:0;border-radius:5px}
.pfill{background:var(--c2)}.pfrom{background:var(--accent);opacity:.55}
.carrier{color:var(--ink3);font-size:11.5px}
.dim{color:var(--ink3)}
"""

LEGEND = ('<span class="badge b-extracted">extracted</span> from the figure/methods · '
          '<span class="badge b-kb">kb</span> inferred from the most similar experiments '
          '(hover: value, 68% CI, donor experiments) · '
          '<span class="badge b-model">model</span> filled from a twin default')


def _fmt(v, unit=""):
    if v is None:
        return '<span class="dim">—</span>'
    if isinstance(v, float):
        v = round(v, 4)
    return f'{v}{unit}'


def render(rows):
    src = {}                       # exp_id -> {field: full provenance meta} for badges
    for r in rows:
        ps = r.get("param_sources") or {}
        src[r["exp_id"]] = {k: meta for k, meta in ps.items()
                            if isinstance(meta, dict) and meta.get("source")}

    by_mat = defaultdict(list)
    for r in rows:
        by_mat[r.get("material") or "—"].append(r)

    n = len(rows)
    ready = sum(r["analysis_ready"] for r in rows)
    avg_e = round(sum(r["completeness_extracted"] for r in rows) / n, 2) if n else 0
    avg_f = round(sum(r["completeness_filled"] for r in rows) / n, 2) if n else 0

    def badge(exp_id, field):
        meta = src.get(exp_id, {}).get(field)
        if not meta:
            return ""
        s = meta["source"]
        if s == "kb":                              # covariate-conditioned imputation
            ci = meta.get("ci") or [None, None]
            don = meta.get("donors") or []
            tip = f"imputed ≈ {meta['value']:.4g}"
            if ci[0] is not None:
                tip += f"  |  68% CI {ci[0]:.3g}–{ci[1]:.3g}"
            if meta.get("n_eff"):
                tip += f"  |  n_eff {meta['n_eff']} of {meta.get('n_donors','?')}"
            if don:
                tip += "  |  from " + ", ".join(f"{d['exp_id']}~{d['sim']}" for d in don[:3])
            return f'<span class="badge b-kb" title="{tip}">kb</span>'
        if s == "model":
            return f'<span class="badge b-model" title="model default {meta.get("value")}">model</span>'
        return ""

    def reactants_cell(r):
        out = []
        for rt in r.get("reactants") or []:
            lab, sp, role = rt.get("label"), rt.get("species") or "?", (rt.get("role") or "")[:4]
            dose = _fmt(rt.get("dose_time"), " s")
            purge = _fmt(rt.get("purge_time"), " s")
            pp = _fmt(rt.get("partial_pressure"), " Pa")
            db = badge(r["exp_id"], f"pulse_time::{lab}")
            pb = badge(r["exp_id"], f"purge_time::{lab}")
            ppb = badge(r["exp_id"], f"partial_pressure::{lab}")
            out.append(f'<div class="rx"><span class="lab">{lab}</span> {sp} '
                       f'<span class="dim">({role})</span> · dose {dose}{db} · purge {purge}{pb} '
                       f'· p {pp}{ppb}</div>')
        cg = r.get("carrier_gas") or {}
        if cg.get("species"):
            fl = f" · {cg['flow_sccm']} sccm" if cg.get("flow_sccm") else ""
            out.append(f'<div class="carrier">carrier: {cg["species"]}{fl}</div>')
        return "".join(out) or '<span class="dim">—</span>'

    def compl_cell(r):
        e, f = r["completeness_extracted"], r["completeness_filled"]
        return (f'<span class="pbar"><i class="pfrom" style="width:{f*100:.0f}%"></i>'
                f'<i class="pfill" style="width:{e*100:.0f}%"></i></span> '
                f'<span class="mono dim">{e:.2f}→{f:.2f}</span>')

    sections = []
    for mat in sorted(by_mat):
        rs = by_mat[mat]
        trs = []
        for r in rs:
            seq = r.get("cycle_sequence") or "—"
            nc = _fmt(r.get("ncycles")) + badge(r["exp_id"], "cycle_number::")
            T = _fmt(r.get("temperature"), " °C") + badge(r["exp_id"], "temperature::")
            flow = _fmt(r.get("flow_rate"), " sccm") + badge(r["exp_id"], "flow_rate::")
            trs.append(
                f'<tr><td class="mono">{r["exp_id"]}</td>'
                f'<td>{reactants_cell(r)}</td>'
                f'<td class="mono">{seq}</td>'
                f'<td class="mono">{nc}</td>'
                f'<td class="mono">{T}</td>'
                f'<td class="mono">{flow}</td>'
                f'<td>{compl_cell(r)}</td></tr>')
        sections.append(
            f'<div class="mgroup">{mat} · {len(rs)} recipe{"s" if len(rs)!=1 else ""}</div>'
            '<table><thead><tr><th>exp id</th><th>reactants (dose · purge · pressure)</th>'
            '<th>cycle</th><th>ncycles</th><th>dep. temp</th><th>flow</th><th>completeness</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table>')

    html = f"""<!doctype html><meta charset="utf-8"><title>ALD Recipe Store</title>
<style>{CSS}</style><div class="wrap">
<div class="eyebrow">PSED · knowledge base</div>
<h1>Recipe store</h1>
<div class="sub">Every experiment lifted into an actionable Recipe — the object the LLM agent and the MPC twin both consume. Missing values are inferred <b>probabilistically from the most similar experiments</b> (covariate-conditioned), not a global median — each carries a credible interval and cites its donors.</div>
<div class="bar">
 <div class="stat"><b>{n}</b><span>recipes</span></div>
 <div class="stat"><b>{ready}</b><span>analysis-ready</span></div>
 <div class="stat"><b>{len(by_mat)}</b><span>materials</span></div>
 <div class="stat"><b>{avg_e:.2f} → {avg_f:.2f}</b><span>avg completeness (extracted → filled)</span></div>
</div>
<div class="sub" style="font-size:12px">{LEGEND}</div>
<div class="ctl"><input id="q" placeholder="filter by exp id / species / material…" style="min-width:280px" oninput="flt()"></div>
{"".join(sections)}
</div>
<script>
function flt(){{var q=document.getElementById('q').value.toLowerCase();
 document.querySelectorAll('tbody tr').forEach(function(tr){{
   tr.style.display = tr.textContent.toLowerCase().indexOf(q)>=0 ? '' : 'none';}});
 document.querySelectorAll('.mgroup').forEach(function(g){{
   var t=g.nextElementSibling, vis=t.querySelectorAll('tbody tr:not([style*="none"])').length;
   g.style.display=t.style.display=vis?'':'none';}});}}
</script>"""
    (ROOT / "recipes.html").write_text(html)
    return html


if __name__ == "__main__":
    rows = build()
    render(rows)
    n = len(rows)
    ae = sum(r["completeness_extracted"] for r in rows) / n
    af = sum(r["completeness_filled"] for r in rows) / n
    nkb = sum(1 for r in rows for m in (r.get("param_sources") or {}).values()
              if isinstance(m, dict) and m.get("source") == "kb")
    nmodel = sum(1 for r in rows for m in (r.get("param_sources") or {}).values()
                 if isinstance(m, dict) and m.get("source") == "model")
    print(f"wrote output/recipes.json + recipes.html  ({n} recipes)")
    print(f"  completeness  extracted {ae:.2f}  ->  filled {af:.2f}")
    print(f"  gap-fills: {nkb} from KB medians, {nmodel} from model defaults")
