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
import paths as P
import json
from pathlib import Path
from collections import defaultdict

from pipeline.resolve import kb_service as ks
from pipeline.resolve import recipe as recipe_mod
from pipeline.canonical import similarity as sim

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
        n_ext, n_tot = _field_counts(rec)          # populated BEFORE any gap-fill
        recipe_mod.fill_gaps(rec, impute_fn, MODEL_DEFAULTS)
        after = rec.completeness()
        d = rec.to_dict()
        d.update({
            "exp_id": e.get("exp_id"), "paper": e["_pid"],
            "analysis_ready": bool(e.get("analysis_ready")),
            "completeness_extracted": before, "completeness_filled": after,
            "fields_extracted_n": n_ext, "fields_total_n": n_tot,
        })
        rows.append(d)
    rows.sort(key=lambda r: (r.get("material") or "", -(r.get("completeness_filled") or 0)))
    (P.CORPUS_OUT / "recipes.json").write_text(json.dumps(rows, indent=2, default=str))
    (P.CORPUS_OUT / "recipe_accounting.json").write_text(
        json.dumps(field_accounting(rows, experiments), indent=2, default=str))
    return rows


# --- where each recipe field actually came from -----------------------------
# "filled completeness" alone is NOT recipe readiness: it counts an imputed or
# defaulted field the same as a measured one. This breakdown keeps the two apart.
CORPUS_CARDS = P.PAPERS


def _field_counts(rec):
    """(populated, total) recipe fields — the count behind completeness(). Called
    BEFORE fill_gaps so it measures what the literature actually supplied."""
    have = sum(bool(getattr(rec, f)) for f in rec.FIELDS)
    tot = rhave = 0
    for r in rec.reactants:
        for rf in rec.REACTANT_FIELDS:
            tot += 1
            rhave += getattr(r, rf) is not None
    return have + rhave, len(rec.FIELDS) + tot


def _window_papers():
    """Papers whose card carries a non-degenerate temperature WINDOW.

    A window is paper-level process metadata (an admissible RANGE), NOT a scalar
    deposition condition — it is deliberately never counted as a completed recipe
    field. See the process-window semantics note in pipeline/resolve/to_kb.py."""
    out = {}
    if not CORPUS_CARDS.is_dir():
        return out
    for d in sorted((P.extracted_dir(x) for x in P.papers())):
        cf = d / "card.json"
        if not cf.is_file():
            continue
        try:
            w = json.loads(cf.read_text()).get("temperature_window_C")
        except Exception:
            continue
        if (isinstance(w, list) and len(w) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w)
                and float(w[0]) != float(w[1])):
            out[d.parent.name] = w
    return out


def field_accounting(rows, experiments=None):
    """Per-source field counts + process-window accounting for the recipe report.

    Counts come from the recipes' own `param_sources`, which since the provenance layer
    carries an entry for EXTRACTED fields as well as imputed/defaulted ones. Nothing here
    re-derives a source from a value."""
    win = _window_papers()
    by_src = defaultdict(int)
    by_from = defaultdict(int)
    for r in rows:
        for k, m in (r.get("param_sources") or {}).items():
            if k == "_exp_id" or not isinstance(m, dict) or not m.get("source"):
                continue
            by_src[m["source"]] += 1
            by_from[m.get("from") or "unknown"] += 1
    n_paper, n_exp = by_src["paper"], by_src["experiment"]
    n_derived, n_kb, n_model = by_src["derived"], by_src["kb"], by_src["model"]
    n_ext = n_paper + n_exp + n_derived          # literature-grounded, however sourced
    n_tot = sum(r.get("fields_total_n") or 0 for r in rows)
    n_unresolved = max(0, n_tot - (n_ext + n_kb + n_model))
    win_recipes = [r for r in rows if r.get("paper") in win]
    # per-experiment temperature (caption/series) is legitimate; a PAPER-LEVEL scalar on a
    # window paper is the defect this fix removed and must stay at 0.
    # Now exact: read the temperature's recorded source instead of testing presence.
    # (The previous form looked up "temperature" while fill_gaps writes "temperature::",
    # so it never matched and counted KB-imputed temperatures as per-experiment ones.)
    win_per_exp = sum(1 for r in win_recipes
                      if ((r.get("param_sources") or {}).get("temperature::") or {}
                          ).get("source") == "experiment")
    win_paper_scalar = 0
    for e in (experiments or []):
        if e.get("_pid") not in win:
            continue
        if any(c.get("quantity") == "temperature" and c.get("source") == "methods"
               for c in (e.get("controlled") or [])):
            win_paper_scalar += 1
    return {
        "recipes": len(rows),
        "fields_directly_extracted": n_ext,
        "fields_paper_direct": n_paper,
        "fields_experiment_direct": n_exp,
        "fields_derived": n_derived,
        "fields_kb_imputed": n_kb,
        "fields_model_default": n_model,
        "fields_unresolved": n_unresolved,
        "fields_total": n_tot,
        "fields_by_origin": dict(sorted(by_from.items())),
        "process_window_papers": len(win),
        "process_window_recipes": len(win_recipes),
        "window_recipes_with_per_experiment_temperature": win_per_exp,
        "window_recipes_with_paper_level_scalar_temperature": win_paper_scalar,
        "windows": win,
        "note": ("A non-degenerate temperature_window_C is an admissible RANGE, not a "
                 "scalar condition, and is NOT counted as a completed recipe field. "
                 "Scalar temperatures previously produced by collapsing such a range to "
                 "its lower endpoint have been removed; the resulting drop in "
                 "'filled completeness' is a truthfulness correction, not a regression. "
                 "'filled completeness' counts imputed and defaulted fields alongside "
                 "extracted ones and is therefore NOT a measure of recipe readiness — "
                 "read it together with fields_directly_extracted. Counts are read from "
                 "each recipe's param_sources (provenance recorded where the value was "
                 "created); fields_directly_extracted = paper + experiment + derived."),
    }


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
.b-paper{background:rgba(27,175,122,.16);color:var(--c2)}
.b-exp{background:rgba(27,175,122,.26);color:var(--c2)}
.b-derived{background:rgba(74,58,167,.16);color:var(--c4)}
.b-kb{background:rgba(42,120,214,.16);color:var(--accent)}
.b-model{background:rgba(237,161,0,.18);color:var(--c3)}
.pbar{position:relative;height:8px;width:96px;background:var(--line2);border-radius:5px;overflow:hidden;display:inline-block;vertical-align:middle}
.pbar>i{position:absolute;left:0;top:0;bottom:0;border-radius:5px}
.pfill{background:var(--c2)}.pfrom{background:var(--accent);opacity:.55}
.carrier{color:var(--ink3);font-size:11.5px}
.dim{color:var(--ink3)}
"""

LEGEND = ('<span class="badge b-paper">paper</span> stated for the whole paper (methods/table) · '
          '<span class="badge b-exp">experiment</span> read from this experiment’s caption or series · '
          '<span class="badge b-derived">derived</span> deterministic transformation · '
          '<span class="badge b-kb">kb</span> inferred from the most similar experiments '
          '(hover: value, 68% CI, donor experiments) · '
          '<span class="badge b-model">model</span> filled from a twin default'
          ' — hover any badge for its exact origin')


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
    acct = field_accounting(rows)

    def badge(exp_id, field):
        meta = src.get(exp_id, {}).get(field)
        if not meta:
            return ""
        s = meta["source"]
        frm = meta.get("from") or "unknown"
        if s in ("paper", "experiment", "derived"):
            where = {"paper": "paper-level", "experiment": "this experiment",
                     "derived": "deterministic transformation"}[s]
            tip = f"{where} · {frm}"
            for k in ("card_field", "figure", "panel", "ref", "transformation"):
                if meta.get(k):
                    tip += f" · {k} {meta[k]}"
            cls = {"paper": "b-paper", "experiment": "b-exp", "derived": "b-derived"}[s]
            return f'<span class="badge {cls}" title="{tip}">{s}</span>'
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
<div class="bar">
 <div class="stat"><b>{acct['fields_paper_direct']}</b><span>paper-level direct</span></div>
 <div class="stat"><b>{acct['fields_experiment_direct']}</b><span>experiment-level direct</span></div>
 <div class="stat"><b>{acct['fields_derived']}</b><span>deterministically derived</span></div>
 <div class="stat"><b>{acct['fields_kb_imputed']}</b><span>fields KB-imputed</span></div>
 <div class="stat"><b>{acct['fields_model_default']}</b><span>fields model-default</span></div>
 <div class="stat"><b>{acct['fields_unresolved']}</b><span>unresolved</span></div>
</div>
<div class="bar">
 <div class="stat"><b>{acct['process_window_recipes']}</b><span>recipes with a process window (range, not a scalar)</span></div>
 <div class="stat"><b>{acct['window_recipes_with_per_experiment_temperature']}</b><span>window recipes with a per-experiment T</span></div>
 <div class="stat"><b>{acct['window_recipes_with_paper_level_scalar_temperature']}</b><span>paper-level scalar temps from a range (must be 0)</span></div>
</div>
<div class="sub" style="font-size:12px"><b>Read completeness with care.</b> “Filled completeness” counts KB-imputed and
model-default fields alongside measured ones, so it is <b>not</b> a measure of recipe readiness — read it together with
<i>fields directly extracted</i>. A non-degenerate <code>temperature_window_C</code> is an admissible <b>range</b>, not a
scalar condition, and is never counted as a completed recipe field. Scalar temperatures previously produced by collapsing
such a range to its lower endpoint have been removed, so any drop in filled completeness here is a
<b>truthfulness correction, not a model regression</b>.</div>
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
    a = field_accounting(rows)
    print(f"  fields by origin: {a['fields_by_origin']}")
    print(f"  fields: {a['fields_directly_extracted']} extracted "
          f"(paper {a['fields_paper_direct']} · experiment {a['fields_experiment_direct']} · "
          f"derived {a['fields_derived']}) · unresolved {a['fields_unresolved']} · "
          f"{a['fields_kb_imputed']} kb-imputed · {a['fields_model_default']} model-default")
    print(f"  process windows: {a['process_window_papers']} papers / "
          f"{a['process_window_recipes']} recipes (range, NOT counted as a scalar); "
          f"{a['window_recipes_with_per_experiment_temperature']} have a per-experiment T; "
          f"{a['window_recipes_with_paper_level_scalar_temperature']} paper-level scalars (must be 0)")
    print("  NOTE: filled completeness includes imputed+default fields — not recipe readiness.")
