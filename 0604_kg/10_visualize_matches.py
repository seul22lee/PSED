"""
visualize_matches.py
--------------------
matches.json 을 읽어 두 가지 HTML 시각화를 생성한다.

  output/viz_matrix.html   -- experiment x experiment similarity matrix
  output/viz_viewer.html   -- experiment 중심 interactive viewer

실행:
  python visualize_matches.py
"""

import json
from pathlib import Path

from config import OUTPUT_DIR

MATCHES_PATH = OUTPUT_DIR / "matches.json"
KG_PATH      = OUTPUT_DIR / "knowledge_graph.json"
OUT_MATRIX   = OUTPUT_DIR / "viz_matrix.html"
OUT_VIEWER   = OUTPUT_DIR / "viz_viewer.html"
OUT_KG       = OUTPUT_DIR / "kg.html"


def load_matches():
    if not MATCHES_PATH.exists():
        raise FileNotFoundError(f"먼저 10_match.py 를 실행하세요: {MATCHES_PATH}")
    return json.load(open(MATCHES_PATH, encoding="utf-8"))


# ─────────────────────────────────────────
# 1. Similarity Matrix
# ─────────────────────────────────────────
MATRIX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Similarity Matrix</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f4f0; padding: 24px; color: #2c2c2a; }
h1 { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
.subtitle { font-size: 12px; color: #888780; margin-bottom: 20px; }
.wrap { background: #fff; border-radius: 10px; padding: 20px;
        border: 1px solid #e0dfd8; display: inline-block; }
.legend { display: flex; align-items: center; gap: 8px; margin-top: 14px; font-size: 11px; color: #5f5e5a; }
.legend-grad { width: 120px; height: 10px; border-radius: 3px;
               background: linear-gradient(to right, #f5f4f0, #d4e9c3, #378ADD); }
.cross-note { margin-top: 8px; font-size: 11px; color: #888780; }
.cross-note span { display: inline-block; width: 10px; height: 10px;
                   border: 2px solid #E24B4A; border-radius: 2px;
                   margin-right: 4px; vertical-align: middle; }
#tooltip { position: fixed; background: rgba(44,44,42,0.92); color: #fff;
           padding: 6px 10px; border-radius: 6px; font-size: 12px;
           pointer-events: none; display: none; z-index: 999; white-space: nowrap; }
</style>
</head>
<body>
<h1>Experiment Similarity Matrix</h1>
<div class="subtitle">Hover over a cell to see details. Red border = cross-paper pair.</div>
<div class="wrap">
  <canvas id="matrix" role="img" aria-label="Similarity matrix heatmap"></canvas>
  <div class="legend">
    <span>0</span>
    <div class="legend-grad"></div>
    <span>1.0</span>
    <span style="margin-left:12px;color:#888780">similarity score</span>
  </div>
  <div class="cross-note"><span></span>cross-paper pair</div>
</div>
<div id="tooltip"></div>

<script>
const LABELS = __LABELS__;
const CELLS  = __CELLS__;
const N      = __N__;

const CELL   = 52;
const LABEL_W = 160;
const LABEL_H = 100;
const PAD     = 10;

const canvas = document.getElementById('matrix');
const ctx    = canvas.getContext('2d');
canvas.width  = LABEL_W + N * CELL + PAD;
canvas.height = LABEL_H + N * CELL + PAD;

function scoreToColor(score) {
  if (score === null) return '#f0eee8';
  if (score >= 0.999) return '#378ADD';
  const r = Math.round(245 + (55  - 245) * score);
  const g = Math.round(244 + (138 - 244) * score);
  const b = Math.round(240 + (221 - 240) * score);
  return `rgb(${r},${g},${b})`;
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.font = '10px system-ui';
  ctx.fillStyle = '#5f5e5a';
  ctx.textAlign = 'right';

  LABELS.forEach((lbl, j) => {
    ctx.save();
    ctx.translate(LABEL_W + j * CELL + CELL/2, LABEL_H - 6);
    ctx.rotate(-Math.PI / 4);
    ctx.fillText(lbl, 0, 0);
    ctx.restore();
  });

  LABELS.forEach((lbl, i) => {
    ctx.fillText(lbl, LABEL_W - 6, LABEL_H + i * CELL + CELL/2 + 4);
  });

  CELLS.forEach(c => {
    const x = LABEL_W + c.j * CELL;
    const y = LABEL_H + c.i * CELL;
    ctx.fillStyle = scoreToColor(c.score);
    ctx.fillRect(x+1, y+1, CELL-2, CELL-2);

    if (c.cross && c.score !== null) {
      ctx.strokeStyle = '#E24B4A';
      ctx.lineWidth = 2;
      ctx.strokeRect(x+2, y+2, CELL-4, CELL-4);
    }
    if (c.score !== null && !c.self) {
      ctx.fillStyle = c.score > 0.6 ? '#fff' : '#5f5e5a';
      ctx.font = 'bold 11px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText(c.score.toFixed(2), x + CELL/2, y + CELL/2 + 4);
    }
  });
}

draw();

const tip = document.getElementById('tooltip');
canvas.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const j  = Math.floor((mx - LABEL_W) / CELL);
  const i  = Math.floor((my - LABEL_H) / CELL);
  if (i >= 0 && i < N && j >= 0 && j < N) {
    const c = CELLS[i * N + j];
    tip.style.display = 'block';
    tip.style.left = (e.clientX + 12) + 'px';
    tip.style.top  = (e.clientY + 12) + 'px';
    tip.textContent = `${LABELS[i]} x ${LABELS[j]}: ${c.tip}`;
  } else {
    tip.style.display = 'none';
  }
});
canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
</script>
</body>
</html>"""


def build_matrix_html(data: dict) -> str:
    exps    = data["experiments"]
    matches = data["matches"]

    score_map = {}
    for m in matches:
        score_map[(m["exp_a"], m["exp_b"])] = m
        score_map[(m["exp_b"], m["exp_a"])] = m

    ids = sorted(exps.keys())

    def axis_label(eid):
        e = exps[eid]
        paper = e.get("paper_short") or e.get("paper_full") or e.get("paper") or ""
        fig   = e.get("figure_id") or ""
        return f"{paper} {fig}".strip() or eid

    labels = [axis_label(eid) for eid in ids]
    n = len(ids)

    cells = []
    for i, a in enumerate(ids):
        for j, b in enumerate(ids):
            if a == b:
                cells.append({"i": i, "j": j, "score": 1.0, "self": True,
                               "cross": False, "tip": "same experiment"})
            elif (a, b) in score_map:
                m = score_map[(a, b)]
                cells.append({
                    "i": i, "j": j,
                    "score": m["scores"]["total"],
                    "cross": m["is_cross_paper"],
                    "self": False,
                    "tip": (f"{m['scores']['total']:.2f} "
                            f"(cov {m['scores'].get('coverage', 1):.2f}) | "
                            f"dep: {', '.join(m['dep_overlap'])} | "
                            f"{'cross-paper' if m['is_cross_paper'] else 'same-paper'}")
                })
            else:
                cells.append({"i": i, "j": j, "score": None,
                               "cross": False, "self": False, "tip": "no match"})

    html = MATRIX_TEMPLATE
    html = html.replace("__LABELS__", json.dumps(labels, ensure_ascii=False))
    html = html.replace("__CELLS__",  json.dumps(cells,  ensure_ascii=False))
    html = html.replace("__N__",      str(n))
    return html


# ─────────────────────────────────────────
# 2. Experiment Viewer
# ─────────────────────────────────────────
VIEWER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Experiment Viewer</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f4f0; color: #2c2c2a; font-size: 14px; }
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
.sidebar { background: #fff; border-right: 1px solid #e0dfd8;
           display: flex; flex-direction: column; height: 100vh; position: sticky; top: 0; overflow: hidden; }
.sidebar-header { padding: 14px 16px; border-bottom: 1px solid #e0dfd8; flex-shrink: 0; }
.sidebar-header h2 { font-size: 13px; font-weight: 600; color: #5f5e5a; margin-bottom: 8px; }
.search { width: 100%; padding: 6px 10px; border: 1px solid #d3d1c7; border-radius: 6px;
          font-size: 12px; background: #f5f4f0; outline: none; }
.search:focus { border-color: #888780; }
.exp-list { flex: 1; overflow-y: auto; }
.exp-item { padding: 9px 16px; cursor: pointer; border-bottom: 0.5px solid #f1efe8; }
.exp-item:hover { background: #f8f7f3; }
.exp-item.active { background: #e6f1fb; border-left: 3px solid #378ADD; padding-left: 13px; }
.exp-item-id { font-size: 10px; color: #aaa89e; }
.exp-item-series { font-weight: 500; font-size: 13px; }
.exp-item-meta { font-size: 11px; color: #888780; margin-top: 2px; }
.main { padding: 20px 24px; overflow-y: auto; max-height: 100vh; }
.empty { display: flex; align-items: center; justify-content: center;
         height: 60vh; color: #888780; font-size: 13px; }
.card { background: #fff; border-radius: 10px; padding: 16px 20px;
        border: 1px solid #e0dfd8; margin-bottom: 14px; }
.exp-title { font-size: 17px; font-weight: 600; }
.exp-sub { font-size: 11px; color: #888780; margin-top: 3px; }
.tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 10px; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 4px; display: inline-block; }
.t-mat    { background: #faeeda; color: #854f0b; }
.t-struct { background: #f1efe8; color: #5f5e5a; }
.t-indep  { background: #e6f1fb; color: #185fa5; }
.t-dep    { background: #eaf3de; color: #3b6d11; }
.t-model  { background: #faeeda; color: #854f0b; }
.t-paper  { background: #f1efe8; color: #5f5e5a; }
.t-paper.p2 { background: #eaf3de; color: #3b6d11; }
.params { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.param-chip { background: #f5f4f0; border-radius: 5px; padding: 3px 9px; font-size: 11px; }
.param-chip b { color: #888780; font-weight: normal; margin-right: 3px; }
.sec-title { font-size: 11px; font-weight: 600; color: #5f5e5a; text-transform: uppercase;
             letter-spacing: 0.5px; margin-bottom: 10px; }
.match-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px,1fr));
              gap: 10px; margin-bottom: 20px; }
.match-card { background: #fff; border-radius: 8px; padding: 12px 14px;
              border: 1px solid #e0dfd8; cursor: pointer; transition: border-color .15s; }
.match-card:hover { border-color: #378ADD; }
.match-card.cross { border-left: 3px solid #E24B4A; padding-left: 11px; }
.match-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.match-series { font-weight: 500; font-size: 13px; }
.match-paper  { font-size: 11px; color: #888780; margin-top: 2px; }
.match-dep    { font-size: 11px; color: #5f5e5a; margin-top: 5px; }
.score-val { font-size: 18px; font-weight: 600; }
.sc-hi { color: #3b6d11; } .sc-md { color: #854f0b; } .sc-lo { color: #993556; }
.diff-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.diff-table td { padding: 3px 6px; }
.diff-table tr:nth-child(even) { background: #f8f7f3; }
.bar { height: 4px; border-radius: 2px; margin-top: 1px; }
.chart-wrap { position: relative; height: 260px; margin-top: 12px; }
.leg { display: flex; gap: 14px; font-size: 11px; color: #5f5e5a; margin-bottom: 8px; flex-wrap: wrap; }
.leg-item { display: flex; align-items: center; gap: 5px; }
.leg-line { width: 18px; height: 2px; border-radius: 1px; }
</style>
</head>
<body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>Experiments</h2>
      <input class="search" id="search" type="text" placeholder="search...">
    </div>
    <div class="exp-list" id="expList"></div>
  </div>
  <div class="main" id="main"><div class="empty">← select an experiment</div></div>
</div>

<script>
const DATA = __DATA__;

let selectedId = null;
let activeChart = null;

function paperClass(e) {
  return (e.paper_short||e.paper_short||e.paper_full||'').includes('Yim') ? '' : 'p2';
}
function fmtV(v) {
  if (v == null) return '—';
  if (Math.abs(v) >= 1e6) return (v/1e6).toFixed(1)+'M';
  if (Math.abs(v) >= 1e3) return (v/1e3).toFixed(0)+'k';
  return Number.isInteger(v) ? String(v) : v.toFixed(v < 10 ? 2 : 0);
}
function scClass(s) { return s >= 0.8 ? 'sc-hi' : s >= 0.5 ? 'sc-md' : 'sc-lo'; }

function expTitle(e) {
  const paper = e.paper_short || e.paper_full || '';
  const fig   = e.figure_id || '';
  const panel = e.panel ? '-' + e.panel : '';
  const t = (paper + ' ' + fig + panel).trim();
  return t || e.experiment_id;
}

function buildSidebar(q) {
  q = (q||'').toLowerCase();
  const list = document.getElementById('expList');
  list.innerHTML = '';
  Object.values(DATA.experiments)
    .filter(e => !q ||
      (e.experiment_id||'').includes(q) ||
      (e.series_name||'').toLowerCase().includes(q) ||
      (e.paper_short||e.paper_full||'').toLowerCase().includes(q) ||
      (e.material||'').toLowerCase().includes(q))
    .forEach(e => {
      const d = document.createElement('div');
      d.className = 'exp-item' + (selectedId === e.experiment_id ? ' active' : '');
      d.innerHTML =
        '<div class="exp-item-id">' + (e.paper_short||'') + ' · ' + e.experiment_id.replace('experiment-','exp-') + '</div>' +
        '<div class="exp-item-series">' + (e.series_name||'—') + '</div>' +
        '<div class="exp-item-meta">' +
          '<span class="tag t-paper ' + paperClass(e) + '">' + (e.paper_short||e.paper_full||'') + '</span> ' +
          (e.material||'') + (e.is_model_result ? ' · model' : '') +
        '</div>';
      d.onclick = () => selectExp(e.experiment_id);
      list.appendChild(d);
    });
}

document.getElementById('search').addEventListener('input', e => buildSidebar(e.target.value));

function selectExp(eid) {
  selectedId = eid;
  buildSidebar(document.getElementById('search').value);
  const exp = DATA.experiments[eid];
  const matches = getMatches(eid);
  const cross = matches.filter(m => m.is_cross_paper);
  const same  = matches.filter(m => !m.is_cross_paper);

  const flatChips = Object.entries(exp.flat||{}).map(([k,v]) =>
    '<div class="param-chip"><b>' + k.replace(/_/g,' ') + ':</b>' + fmtV(v) + '</div>'
  ).join('');

  const indepTags = (exp.indep||[]).map(i =>
    '<span class="tag t-indep">indep: ' + i + '</span>').join('');
  const depTags = (exp.dep_orig||[]).map(d =>
    '<span class="tag t-dep">dep: ' + d + '</span>').join('');

  let html =
    '<div class="card">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start">' +
        '<div>' +
          '<div class="exp-title">' + expTitle(exp) + '</div>' +
          '<div class="exp-sub">' + exp.experiment_id + ' · ' + (exp.figure_id||'') + ' ' + (exp.panel||'') + '</div>' +
        '</div>' +
        '<span class="tag t-paper ' + paperClass(exp) + '" style="font-size:11px;padding:3px 9px">' + (exp.paper_full||'') + '</span>' +
      '</div>' +
      '<div class="tags">' +
        '<span class="tag t-mat">' + (exp.material||'') + '</span>' +
        (exp.structure_type ? '<span class="tag t-struct">' + exp.structure_type + '</span>' : '') +
        (exp.is_model_result ? '<span class="tag t-model">model</span>' : '') +
        indepTags + depTags +
      '</div>' +
      (flatChips ? '<div class="params">' + flatChips + '</div>' : '') +
    '</div>';

  if (cross.length) {
    html += '<div class="sec-title">Cross-paper matches (' + cross.length + ')</div>' +
            '<div class="match-grid" id="crossGrid"></div>';
  }
  if (same.length) {
    html += '<div class="sec-title">Same-paper matches (' + same.length + ')</div>' +
            '<div class="match-grid" id="sameGrid"></div>';
  }
  if (!matches.length) {
    html += '<div class="empty" style="height:200px">No matches found</div>';
  }
  html += '<div id="chartArea"></div>';

  document.getElementById('main').innerHTML = html;

  if (cross.length) renderCards(cross, 'crossGrid', exp);
  if (same.length)  renderCards(same,  'sameGrid',  exp);
}

function getMatches(eid) {
  return DATA.matches
    .filter(m => m.exp_a === eid || m.exp_b === eid)
    .map(m => {
      const oid = m.exp_a === eid ? m.exp_b : m.exp_a;
      return Object.assign({}, m, {
        other_id: oid,
        other_paper: m.exp_a === eid ? m.paper_b : m.paper_a
      });
    })
    .sort((a,b) => b.scores.total - a.scores.total);
}

function renderCards(matches, containerId, selExp) {
  const cont = document.getElementById(containerId);
  if (!cont) return;
  matches.forEach(m => {
    const other = DATA.experiments[m.other_id];
    if (!other) return;
    const sc = m.scores.total;
    const card = document.createElement('div');
    card.className = 'match-card' + (m.is_cross_paper ? ' cross' : '');

    const ctrlRows = Object.entries(m.ctrl_details||{}).map(function(entry) {
      const k = entry[0], d = entry[1];
      const pct = Math.round(d.ratio * 100);
      const imp = d.kind === 'imputed';
      const bc = pct >= 95 ? '#639922' : pct >= 75 ? '#BA7517' : '#A32D2D';
      return '<tr' + (imp ? ' style="opacity:.55"' : '') + '>' +
        '<td style="color:#888780">' + k.replace(/_/g,' ') +
          (imp ? ' <span style="font-size:9px;color:#aaa">est</span>' : '') + '</td>' +
        '<td style="text-align:right">' + fmtV(d.va) + '</td>' +
        '<td style="text-align:right">' + fmtV(d.vb) + '</td>' +
        '<td style="width:50px"><div class="bar" style="width:' + pct + '%;background:' + bc + '"></div></td>' +
        '</tr>';
    }).join('');

    card.innerHTML =
      '<div class="match-top">' +
        '<div>' +
          '<div class="match-series">' + (other.series_name||'—') + '</div>' +
          '<div class="match-paper">' +
            '<span class="tag t-paper ' + paperClass(other) + '">' + (other.paper_full||'') + '</span> ' +
            other.experiment_id +
          '</div>' +
        '</div>' +
        '<div class="score-val ' + scClass(sc) + '">' + Math.round(sc*100) + '%</div>' +
      '</div>' +
      '<div class="match-dep">dep: ' + m.dep_overlap.join(', ') +
        (m.scores.coverage != null ? ' · cov ' + Math.round(m.scores.coverage*100) + '%' : '') +
      '</div>' +
      (ctrlRows ?
        '<table class="diff-table" style="margin-top:6px">' +
          '<tr style="color:#aaa;font-size:10px"><td>param</td>' +
            '<td style="text-align:right">A</td>' +
            '<td style="text-align:right">B</td><td></td></tr>' +
          ctrlRows +
        '</table>' : '');

    card.onclick = () => showChart(selExp, other, m);
    cont.appendChild(card);
  });
}

function showChart(a, b, m) {
  const area = document.getElementById('chartArea');
  if (!area) return;
  const hasData = a.points && a.points.length && b.points && b.points.length;

  const allKeys = Array.from(new Set(
    Object.keys(a.flat||{}).concat(Object.keys(b.flat||{}))
  ));

  const diffRows = allKeys.map(function(k) {
    const va = a.flat ? a.flat[k] : null;
    const vb = b.flat ? b.flat[k] : null;
    const ratio = (va != null && vb != null)
      ? 1 - Math.abs(va-vb) / Math.max(Math.abs(va), Math.abs(vb))
      : null;
    const pct = ratio != null ? Math.round(ratio*100) : null;
    const bc = pct == null ? '#d3d1c7' : pct >= 95 ? '#639922' : pct >= 75 ? '#BA7517' : '#A32D2D';
    const barHtml = pct != null
      ? '<div class="bar" style="width:' + pct + '%;background:' + bc + '"></div>' +
        '<span style="font-size:9px;color:' + bc + '">' + pct + '%</span>'
      : '—';
    return '<tr>' +
      '<td style="color:#888780">' + k.replace(/_/g,' ') + '</td>' +
      '<td style="text-align:right">' + (va != null ? fmtV(va) : '—') + '</td>' +
      '<td style="text-align:right">' + (vb != null ? fmtV(vb) : '—') + '</td>' +
      '<td style="width:80px">' + barHtml + '</td>' +
      '</tr>';
  }).join('');

  area.innerHTML =
    '<div class="card">' +
      '<div style="font-weight:600;margin-bottom:4px">Comparison</div>' +
      '<div style="font-size:11px;color:#888780;margin-bottom:12px">' +
        a.series_name + ' (' + a.paper_full + ') vs ' + b.series_name + ' (' + b.paper_full + ')' +
      '</div>' +
      (hasData ?
        '<div class="leg">' +
          '<span class="leg-item">' +
            '<span class="leg-line" style="background:#378ADD"></span>' +
            '<span class="tag t-paper ' + paperClass(a) + '">' + a.paper_full + '</span> ' + a.series_name +
          '</span>' +
          '<span class="leg-item">' +
            '<span class="leg-line" style="background:#E24B4A"></span>' +
            '<span class="tag t-paper ' + paperClass(b) + '">' + b.paper_full + '</span> ' + b.series_name +
          '</span>' +
        '</div>' +
        '<div class="chart-wrap"><canvas id="cmp" role="img" aria-label="Data comparison"></canvas></div>'
        : '<div style="color:#888780;padding:8px 0;font-size:12px">No plot data available.</div>') +
      '<div class="sec-title" style="margin-top:14px;margin-bottom:6px">Condition diff</div>' +
      '<table class="diff-table">' +
        '<tr style="color:#aaa;font-size:10px"><td>param</td>' +
          '<td style="text-align:right">' + a.series_name + '</td>' +
          '<td style="text-align:right">' + b.series_name + '</td><td></td></tr>' +
        diffRows +
      '</table>' +
    '</div>';

  if (hasData) {
    if (activeChart) activeChart.destroy();
    const ctx2 = document.getElementById('cmp').getContext('2d');
    activeChart = new Chart(ctx2, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: a.series_name,
            data: a.points.map(p => ({ x: p[0], y: p[1] })),
            borderColor: '#378ADD', backgroundColor: 'rgba(55,138,221,0.1)',
            pointRadius: 2, showLine: true, tension: 0.3, borderWidth: 2
          },
          {
            label: b.series_name,
            data: b.points.map(p => ({ x: p[0], y: p[1] })),
            borderColor: '#E24B4A', backgroundColor: 'rgba(226,75,74,0.1)',
            pointRadius: 2, showLine: true, tension: 0.3, borderWidth: 2,
            borderDash: [5, 3]
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { title: { display: true, text: a.x_label || b.x_label || 'x', font: { size: 11 } }, ticks: { font: { size: 10 } } },
          y: { title: { display: true, text: a.y_label || b.y_label || 'y', font: { size: 11 } }, ticks: { font: { size: 10 } } }
        }
      }
    });
  }
  area.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

buildSidebar('');
</script>
</body>
</html>"""


def build_viewer_html(data: dict) -> str:
    html = VIEWER_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    return html


# ─────────────────────────────────────────
# 3. Knowledge Graph (pure Canvas force simulation)
# ─────────────────────────────────────────
KG_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Knowledge Graph</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f4f0; color: #2c2c2a; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
#toolbar { padding: 10px 18px; background: #fff; border-bottom: 1px solid #e0dfd8;
           display: flex; align-items: center; gap: 14px; flex-wrap: wrap; flex-shrink: 0; }
h1 { font-size: 15px; font-weight: 600; }
.legend { display: flex; gap: 10px; }
.leg-item { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #5f5e5a; }
.leg-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
#filter { display: flex; gap: 8px; align-items: center; margin-left: auto; font-size: 12px; }
#filter select { font-size: 12px; padding: 3px 6px; border: 1px solid #ccc; border-radius: 4px; }
#filter label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
#filter button { padding: 3px 10px; cursor: pointer; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; }
#cvs { flex: 1; display: block; cursor: grab; }
#cvs:active { cursor: grabbing; }
#info { position: fixed; bottom: 16px; right: 16px; background: rgba(44,44,42,0.93);
        color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 12px;
        max-width: 340px; display: none; line-height: 1.7; pointer-events: none; }
</style>
</head>
<body>
<div id="toolbar">
  <h1>Knowledge Graph</h1>
  <div class="legend">
    <div class="leg-item"><div class="leg-dot" style="background:#378ADD"></div>experiment</div>
    <div class="leg-item"><div class="leg-dot" style="background:#E89C3A"></div>paper</div>
    <div class="leg-item"><div class="leg-dot" style="background:#639922"></div>material</div>
    <div class="leg-item"><div class="leg-dot" style="background:#9B6BBF"></div>variable</div>
  </div>
  <div id="filter">
    <label>paper <select id="selPaper"><option value="">all</option></select></label>
    <label>material <select id="selMat"><option value="">all</option></select></label>
    <label><input type="checkbox" id="chkCross"> cross-paper only</label>
    <button onclick="resetView()">reset</button>
  </div>
</div>
<canvas id="cvs"></canvas>
<div id="info"></div>

<script>
const RAW = __KG_DATA__;

const COLOR = { experiment:'#378ADD', paper:'#E89C3A', material:'#639922', variable:'#9B6BBF' };
const SIZE  = { experiment:9, paper:14, material:11, variable:7 };

// ── state ──
let nodes=[], edges=[], sim=null;
let transform = { x:0, y:0, k:1 };
let drag=null, hoverId=null;

// ── canvas setup ──
const cvs = document.getElementById('cvs');
const ctx = cvs.getContext('2d');

function resize() {
  cvs.width  = cvs.offsetWidth;
  cvs.height = cvs.offsetHeight;
  draw();
}
window.addEventListener('resize', resize);

// ── build graph data ──
function buildGraph() {
  const paper = document.getElementById('selPaper').value;
  const mat   = document.getElementById('selMat').value;
  const cross = document.getElementById('chkCross').checked;

  let expIds = new Set(RAW.nodes.filter(n=>n.ntype==='experiment').map(n=>n.id));
  if (paper) expIds = new Set([...expIds].filter(id=>{
    const n=RAW.nodes.find(x=>x.id===id); return n&&(n.paper||'').includes(paper);
  }));
  if (mat) expIds = new Set([...expIds].filter(id=>{
    const n=RAW.nodes.find(x=>x.id===id); return n&&n.material===mat;
  }));
  if (cross) {
    const cx=new Set();
    RAW.edges.forEach(e=>{ if(e.etype==='similar_to'&&e.is_cross_paper==='True'){cx.add(e.source);cx.add(e.target);} });
    expIds=new Set([...expIds].filter(id=>cx.has(id)));
  }

  const connIds = new Set(expIds);
  RAW.edges.forEach(e=>{
    if(expIds.has(e.source)) connIds.add(e.target);
    if(expIds.has(e.target)) connIds.add(e.source);
  });

  const W=cvs.width||800, H=cvs.height||600;
  const prev = {};
  nodes.forEach(n=>{ prev[n.id]={x:n.x,y:n.y}; });

  nodes = RAW.nodes.filter(n=>connIds.has(n.id)).map(n=>{
    const p=prev[n.id];
    return {
      id:n.id, ntype:n.ntype,
      label: (n.ntype==='experiment'?(n.series_name||''):(n.name||n.id||'')).slice(0,18),
      title: n.ntype==='experiment'
        ? `${n.series_name||''} · ${(n.paper||'').slice(0,50)}
${n.material||''}${n.is_model==='True'?' [model]':''}`
        : (n.name||n.id||''),
      x: p?p.x:W/2+(Math.random()-0.5)*300,
      y: p?p.y:H/2+(Math.random()-0.5)*300,
      vx:0, vy:0,
      r: SIZE[n.ntype]||8,
      color: COLOR[n.ntype]||'#aaa',
    };
  });

  const nodeIdx={};
  nodes.forEach((n,i)=>nodeIdx[n.id]=i);

  edges = RAW.edges
    .filter(e=>connIds.has(e.source)&&connIds.has(e.target))
    .map(e=>({
      s: nodeIdx[e.source], t: nodeIdx[e.target],
      etype: e.etype,
      cross: e.is_cross_paper==='True',
      score: e.score||0,
    })).filter(e=>e.s!=null&&e.t!=null);
}

// ── force simulation ──
function startSim() {
  if(sim) clearInterval(sim);
  let alpha=1;
  sim = setInterval(()=>{
    if(alpha<0.01){ clearInterval(sim); sim=null; return; }
    tick(alpha);
    alpha*=0.97;
    draw();
  }, 16);
}

function tick(alpha) {
  const N=nodes.length;
  const W=cvs.width, H=cvs.height;

  // repulsion
  for(let i=0;i<N;i++) for(let j=i+1;j<N;j++){
    const dx=nodes[j].x-nodes[i].x, dy=nodes[j].y-nodes[i].y;
    const d2=dx*dx+dy*dy+1, d=Math.sqrt(d2);
    const f=800/(d2)*alpha;
    nodes[i].vx-=f*dx/d; nodes[i].vy-=f*dy/d;
    nodes[j].vx+=f*dx/d; nodes[j].vy+=f*dy/d;
  }
  // attraction along edges
  edges.forEach(e=>{
    const a=nodes[e.s], b=nodes[e.t];
    const dx=b.x-a.x, dy=b.y-a.y;
    const d=Math.sqrt(dx*dx+dy*dy)+0.1;
    const tgt = e.etype==='similar_to'?120:60;
    const f=(d-tgt)*0.05*alpha;
    a.vx+=f*dx/d; a.vy+=f*dy/d;
    b.vx-=f*dx/d; b.vy-=f*dy/d;
  });
  // gravity to center
  nodes.forEach(n=>{
    n.vx+=(W/2-n.x)*0.01*alpha;
    n.vy+=(H/2-n.y)*0.01*alpha;
  });
  // integrate
  nodes.forEach(n=>{
    if(n===drag) return;
    n.vx*=0.7; n.vy*=0.7;
    n.x+=n.vx; n.y+=n.vy;
    n.x=Math.max(n.r,Math.min(W-n.r,n.x));
    n.y=Math.max(n.r,Math.min(H-n.r,n.y));
  });
}

// ── draw ──
function draw() {
  const W=cvs.width, H=cvs.height;
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(transform.x,transform.y);
  ctx.scale(transform.k,transform.k);

  // edges
  edges.forEach(e=>{
    const a=nodes[e.s], b=nodes[e.t];
    if(!a||!b) return;
    ctx.beginPath();
    ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
    if(e.etype==='similar_to'){
      ctx.strokeStyle = e.cross?'rgba(226,75,74,0.8)':'rgba(55,138,221,0.5)';
      ctx.lineWidth = e.cross?2:1;
      ctx.setLineDash([]);
      if(e.score>0){
        const mx=(a.x+b.x)/2, my=(a.y+b.y)/2;
        ctx.stroke();
        ctx.font='9px system-ui'; ctx.fillStyle='#888';
        ctx.textAlign='center';
        ctx.fillText(e.score.toFixed(2),mx,my-3);
      } else { ctx.stroke(); }
    } else {
      ctx.strokeStyle='rgba(180,178,170,0.4)';
      ctx.lineWidth=0.8;
      ctx.setLineDash([3,3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  });

  // nodes
  nodes.forEach(n=>{
    ctx.beginPath();
    ctx.arc(n.x,n.y,n.r,0,Math.PI*2);
    ctx.fillStyle = n.id===hoverId ? lighten(n.color) : n.color;
    ctx.fill();
    ctx.strokeStyle='#fff'; ctx.lineWidth=1.5;
    ctx.stroke();

    ctx.font = n.ntype==='paper'?'bold 10px system-ui':'10px system-ui';
    ctx.fillStyle='#2c2c2a';
    ctx.textAlign='center';
    ctx.fillText(n.label, n.x, n.y+n.r+11);
  });

  ctx.restore();
}

function lighten(hex){
  const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  return `rgb(${Math.min(255,r+40)},${Math.min(255,g+40)},${Math.min(255,b+40)})`;
}

// ── interaction ──
function canvasToWorld(cx,cy){
  return { x:(cx-transform.x)/transform.k, y:(cy-transform.y)/transform.k };
}
function hitTest(wx,wy){
  for(let i=nodes.length-1;i>=0;i--){
    const n=nodes[i], dx=wx-n.x, dy=wy-n.y;
    if(dx*dx+dy*dy<=n.r*n.r) return i;
  }
  return -1;
}

cvs.addEventListener('mousedown',e=>{
  const {x,y}=canvasToWorld(e.offsetX,e.offsetY);
  const i=hitTest(x,y);
  if(i>=0){ drag=nodes[i]; }
  else { drag=null; cvs._pan={x:e.offsetX-transform.x,y:e.offsetY-transform.y}; }
});
cvs.addEventListener('mousemove',e=>{
  if(drag){
    const {x,y}=canvasToWorld(e.offsetX,e.offsetY);
    drag.x=x; drag.y=y; drag.vx=0; drag.vy=0;
    draw(); return;
  }
  if(cvs._pan){
    transform.x=e.offsetX-cvs._pan.x;
    transform.y=e.offsetY-cvs._pan.y;
    draw(); return;
  }
  const {x,y}=canvasToWorld(e.offsetX,e.offsetY);
  const i=hitTest(x,y);
  const prev=hoverId;
  hoverId = i>=0?nodes[i].id:null;
  if(hoverId!==prev) draw();
  const info=document.getElementById('info');
  if(hoverId){
    const n=nodes[i];
    info.innerHTML='<b>'+n.ntype+'</b>: '+n.title.replace(/
/g,'<br>');
    info.style.display='block';
  } else { info.style.display='none'; }
});
cvs.addEventListener('mouseup',()=>{ drag=null; cvs._pan=null; });
cvs.addEventListener('mouseleave',()=>{ drag=null; cvs._pan=null; });
cvs.addEventListener('wheel',e=>{
  e.preventDefault();
  const factor=e.deltaY<0?1.1:0.9;
  const ox=e.offsetX, oy=e.offsetY;
  transform.x=ox-(ox-transform.x)*factor;
  transform.y=oy-(oy-transform.y)*factor;
  transform.k*=factor;
  draw();
},{passive:false});

// ── filters ──
const papers=[...new Set(RAW.nodes.filter(n=>n.ntype==='paper').map(n=>n.name||''))];
const mats  =[...new Set(RAW.nodes.filter(n=>n.ntype==='material').map(n=>n.name||''))];
papers.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p.slice(0,35);document.getElementById('selPaper').appendChild(o);});
mats.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m;document.getElementById('selMat').appendChild(o);});

document.getElementById('selPaper').onchange=()=>{buildGraph();startSim();};
document.getElementById('selMat').onchange  =()=>{buildGraph();startSim();};
document.getElementById('chkCross').onchange=()=>{buildGraph();startSim();};

function resetView(){
  document.getElementById('selPaper').value='';
  document.getElementById('selMat').value='';
  document.getElementById('chkCross').checked=false;
  transform={x:0,y:0,k:1};
  buildGraph(); startSim();
}

// ── init ──
resize();
buildGraph();
startSim();
</script>
</body>
</html>"""

NODE_COLOR = {"experiment":"#378ADD","paper":"#639922","material":"#D85A30","variable":"#BA7517"}
NODE_SHAPE = {"experiment":"dot","paper":"square","material":"diamond","variable":"triangle"}
NODE_SIZE  = {"experiment":14,"paper":24,"material":20,"variable":12}
EDGE_COLOR = {"similar_to":"#E24B4A","from_paper":"#B4B2A9","uses_material":"#D85A30",
              "has_indep":"#378ADD","has_ctrl":"#BA7517","has_dep":"#639922"}
EDGE_WIDTH = {"similar_to":3,"from_paper":1,"uses_material":1,"has_indep":1,"has_ctrl":1,"has_dep":1}

LEGEND_HTML = """
<div style="position:fixed;top:16px;right:16px;background:#fff;border:1px solid #ddd;
            border-radius:8px;padding:12px 16px;font-family:sans-serif;font-size:12px;z-index:999">
  <div style="font-weight:600;margin-bottom:8px">node type</div>
  <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#378ADD;margin-right:6px"></span>experiment</div>
  <div><span style="display:inline-block;width:10px;height:10px;background:#639922;margin-right:6px"></span>paper</div>
  <div><span style="display:inline-block;width:10px;height:10px;background:#D85A30;transform:rotate(45deg);margin-right:6px"></span>material</div>
  <div><span style="display:inline-block;width:10px;height:10px;background:#BA7517;margin-right:6px"></span>variable</div>
  <div style="font-weight:600;margin-top:10px;margin-bottom:8px">edge type</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#E24B4A;margin-right:6px;vertical-align:middle"></span>similar_to</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#378ADD;margin-right:6px;vertical-align:middle"></span>has_indep</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#BA7517;margin-right:6px;vertical-align:middle"></span>has_ctrl</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#639922;margin-right:6px;vertical-align:middle"></span>has_dep</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#D85A30;margin-right:6px;vertical-align:middle"></span>uses_material</div>
  <div><span style="display:inline-block;width:20px;height:2px;background:#B4B2A9;margin-right:6px;vertical-align:middle"></span>from_paper</div>
</div>"""

def build_kg_html() -> bool:
    try:
        from pyvis.network import Network
    except ImportError:
        print("[WARN] pyvis not installed. pip install pyvis")
        return False
    if not KG_PATH.exists():
        print(f"[WARN] knowledge_graph.json not found, skipping kg.html")
        return False

    data = json.load(open(KG_PATH, encoding="utf-8"))

    net = Network(height="860px", width="100%", directed=True,
                  bgcolor="#ffffff", font_color="#2C2C2A", notebook=False)
    net.set_options('''{"physics":{"enabled":true,"barnesHut":{"gravitationalConstant":-8000,
        "centralGravity":0.3,"springLength":120,"springConstant":0.04,"damping":0.09},
        "stabilization":{"iterations":200}},
      "interaction":{"hover":true,"tooltipDelay":100},
      "edges":{"smooth":{"type":"dynamic"}}}''')

    for node in data["nodes"]:
        ntype = node.get("ntype","")
        label = (node.get("series_name") or node.get("name") or node["id"].split("::")[-1])[:25]
        title = "<br>".join(f"{k}: {v}" for k,v in node.items() if k not in ("id","ntype"))
        net.add_node(node["id"], label=label, title=f"<b>{ntype.upper()}</b><br>{title}",
                     color=NODE_COLOR.get(ntype,"#888780"),
                     shape=NODE_SHAPE.get(ntype,"dot"),
                     size=NODE_SIZE.get(ntype,12))

    for edge in data["edges"]:
        etype = edge.get("etype","")
        width = EDGE_WIDTH.get(etype,1)
        if etype == "similar_to":
            width = max(1, int(float(edge.get("score",0.5))*6))
        title = "<br>".join(f"{k}: {v}" for k,v in edge.items() if k not in ("source","target","etype"))
        net.add_edge(edge["source"], edge["target"],
                     title=f"<b>{etype}</b><br>{title}",
                     color=EDGE_COLOR.get(etype,"#B4B2A9"),
                     width=width,
                     arrows="to" if etype!="similar_to" else "",
                     dashes=etype=="similar_to")

    net.save_graph(str(OUT_KG))
    html = OUT_KG.read_text(encoding="utf-8")
    html = html.replace("</body>", LEGEND_HTML + "\n</body>")
    OUT_KG.write_text(html, encoding="utf-8")
    return True


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    data = load_matches()
    print(f"[INFO] {len(data['experiments'])} experiments, {len(data['matches'])} matches")

    matrix_html = build_matrix_html(data)
    OUT_MATRIX.write_text(matrix_html, encoding="utf-8")
    print(f"[DONE] matrix → {OUT_MATRIX}")

    viewer_html = build_viewer_html(data)
    OUT_VIEWER.write_text(viewer_html, encoding="utf-8")
    print(f"[DONE] viewer → {OUT_VIEWER}")

    if build_kg_html():
        print(f"[DONE] kg     → {OUT_KG}")

    print()
    print("브라우저에서 열기:")
    print(f"  open {OUT_MATRIX}")
    print(f"  open {OUT_VIEWER}")
    print(f"  open {OUT_KG}")


if __name__ == "__main__":
    main()
