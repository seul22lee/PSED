#!/usr/bin/env python3
"""
pipeline/review/candidate_section.py — render the candidate-expansion section.

Pure rendering. Every number and label comes from reports/candidate_corpus_expansion.json,
which scripts/triage_candidates.py generates from local Docling text; nothing is decided
here. corpus_status.py calls render() and appends the result after the live-corpus table,
so the two sections stay independent and the candidate analysis is never trapped in HTML.

Returns [] when the JSON is absent, so corpus status still builds on its own.
"""
import html
import json

import paths as P

CANDIDATE_JSON = P.REPORTS / "candidate_corpus_expansion.json"

CSS = """
<style>
.cand-wrap{margin-top:26px}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 16px}
.card{border:1px solid #ccc;border-radius:8px;padding:8px 12px;min-width:132px;background:#fafafa}
.card b{display:block;font-size:20px;line-height:1.2}
.card span{font-size:11px;color:#555;text-transform:uppercase;letter-spacing:.04em}
.badge{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 6px;border-radius:9px;
 border:1px solid #999;white-space:nowrap}
.b-exact{background:#c8e6c9;border-color:#2e7d32;color:#14361a}
.b-family{background:#fff3c4;border-color:#b8860b;color:#5a4300}
.b-new{background:#eceff1;border-color:#90a4ae;color:#37474f}
.b-exp{background:#e3f2fd;border-color:#1565c0;color:#0d3c69}
.b-sim{background:#f3e5f5;border-color:#6a1b9a;color:#3d0f52}
.b-rev{background:#ffe0b2;border-color:#e65100;color:#5d2200}
.b-high{background:#2e7d32;border-color:#1b5e20;color:#fff}
.b-med{background:#fff;border-color:#888;color:#333}
.b-low{background:#f5f5f5;border-color:#bbb;color:#777}
.filters{margin:8px 0 12px;font-size:12px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.filters label{cursor:pointer}
#candtbl th{cursor:pointer;background:#f0f0f0;position:sticky;top:0}
#candtbl th:hover{background:#e4e4e4}
#candtbl td{vertical-align:top;font-size:12px}
#candtbl tr.detail td{background:#fbfbfb;font-size:11.5px;color:#333}
.hint{color:#666;font-size:11.5px}
.note{border-left:4px solid #b8860b;background:#fffdf3;padding:8px 12px;margin:10px 0;font-size:12px}
details summary{cursor:pointer}
</style>
"""

JS = """
<script>
(function(){
 var tbl=document.getElementById('candtbl'); if(!tbl) return;
 var tb=tbl.tBodies[0];
 function rows(){return Array.prototype.slice.call(tb.querySelectorAll('tr.row'));}
 // sort
 Array.prototype.forEach.call(tbl.tHead.rows[0].cells,function(th,i){
  th.addEventListener('click',function(){
   var dir=th.dataset.dir==='asc'?-1:1;
   Array.prototype.forEach.call(tbl.tHead.rows[0].cells,function(o){delete o.dataset.dir;});
   th.dataset.dir=dir===1?'asc':'desc';
   var rs=rows().map(function(r){return [r,r.nextElementSibling];});
   rs.sort(function(a,b){
    var x=a[0].cells[i].dataset.sort||a[0].cells[i].textContent.trim();
    var y=b[0].cells[i].dataset.sort||b[0].cells[i].textContent.trim();
    var nx=parseFloat(x),ny=parseFloat(y);
    if(!isNaN(nx)&&!isNaN(ny))return (nx-ny)*dir;
    return x.localeCompare(y)*dir;});
   rs.forEach(function(p){tb.appendChild(p[0]); if(p[1]&&p[1].classList.contains('detail'))tb.appendChild(p[1]);});
  });});
 // filters
 function apply(){
  var mat=document.getElementById('f-mat').value;
  var ex=document.getElementById('f-exact').checked;
  var xp=document.getElementById('f-exp').checked;
  var har=document.getElementById('f-har').checked;
  var hi=document.getElementById('f-high').checked;
  var shown=0;
  rows().forEach(function(r){
   var d=r.dataset, ok=true;
   if(mat && (d.materials||'').split('|').indexOf(mat)<0) ok=false;
   if(ex && d.exact!=='1') ok=false;
   if(xp && d.experimental!=='1') ok=false;
   if(har && d.har!=='1') ok=false;
   if(hi && d.value!=='HIGH') ok=false;
   r.style.display=ok?'':'none';
   var det=r.nextElementSibling;
   if(det&&det.classList.contains('detail')) det.style.display=ok?'':'none';
   if(ok)shown++;});
  document.getElementById('f-count').textContent=shown+' of '+rows().length+' candidates shown';
 }
 ['f-mat','f-exact','f-exp','f-har','f-high'].forEach(function(id){
  var el=document.getElementById(id); el.addEventListener('change',apply);});
 document.getElementById('f-reset').addEventListener('click',function(){
  document.getElementById('f-mat').value='';
  ['f-exact','f-exp','f-har','f-high'].forEach(function(i){document.getElementById(i).checked=false;});
  apply();});
 apply();
})();
</script>
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def _value_badge(v):
    cls = {"HIGH": "b-high", "MEDIUM": "b-med"}.get(v, "b-low")
    return f'<span class="badge {cls}">{esc(v)}</span>'


def _overlap_badge(r):
    if r["exact_overlap"]:
        return ('<span class="badge b-exact">EXACT</span> '
                + esc(", ".join(r["exact_overlap"])))
    if r.get("family_overlap"):
        pairs = "; ".join("%s~%s" % (k, "/".join(v)) for k, v in r["family_overlap"].items())
        return f'<span class="badge b-family">FAMILY</span> {esc(pairs)}'
    return '<span class="badge b-new">NEW</span>'


def _study_badge(r):
    st = r.get("study_type") or "unclear"
    if st in ("experimental", "experimental_inferred", "mixed"):
        label = {"experimental": "EXPERIMENTAL", "experimental_inferred": "EXPERIMENTAL?",
                 "mixed": "MIXED"}[st]
        return f'<span class="badge b-exp">{label}</span>'
    if st == "simulation":
        return '<span class="badge b-sim">SIMULATION</span>'
    if st == "review":
        return '<span class="badge b-rev">REVIEW</span>'
    return '<span class="badge b-new">UNCLEAR</span>'


def render():
    if not CANDIDATE_JSON.exists():
        return []
    d = json.loads(CANDIDATE_JSON.read_text())
    cands = d.get("candidates") or []
    cov = d.get("material_coverage") or []
    h = [CSS, '<div class="cand-wrap">', "<h2>Candidate corpus expansion</h2>",
         '<div class="note"><b>Document-level triage only.</b> '
         + esc(d.get("disclaimer", "")) +
         ' Generated by <code>scripts/triage_candidates.py</code> from '
         '<code>corpus/acquisition/candidates/*/document.md</code>; the machine-readable '
         'companion is <code>reports/candidate_corpus_expansion.json</code>. '
         'Nothing here has been added to the live corpus.</div>']

    h.append('<div class="cards">')
    for label, key in (("live corpus papers", "live_corpus_papers"),
                       ("remaining candidates", "candidate_count"),
                       ("exact-overlap", "exact_overlap_candidates"),
                       ("experimental exact-overlap", "experimental_exact_overlap"),
                       ("HIGH-value exact-overlap", "high_value_exact_overlap"),
                       ("no readable text", "no_text_candidates")):
        h.append(f'<div class="card"><b>{esc(d.get(key, 0))}</b><span>{esc(label)}</span></div>')
    h.append("</div>")

    # ---- material coverage ------------------------------------------------
    h += ["<h3>Material coverage / expansion opportunity</h3>",
          '<p class="hint">Sorted by expansion opportunity: high-value candidates first, '
          'then candidate count, then how sparse the material currently is.</p>',
          "<table><tr><th>material</th><th>current corpus papers</th>"
          "<th>current series</th><th>remaining candidate papers</th>"
          "<th>high-value candidates</th><th>candidate ids</th></tr>"]
    for c in cov:
        sparse = ' style="background:#fff8e1"' if c["current_papers"] <= 2 and c["candidate_papers"] else ""
        h.append(
            f'<tr{sparse}><td><b>{esc(c["material"])}</b></td>'
            f'<td>{c["current_papers"]}</td><td>{c.get("current_series", 0)}</td>'
            f'<td>{c["candidate_papers"]}</td><td>{c["high_value_candidates"]}</td>'
            f'<td class="hint">{esc(", ".join(c["candidate_ids"][:8]))}'
            f'{"…" if len(c["candidate_ids"]) > 8 else ""}</td></tr>')
    h.append("</table>")

    # ---- filters ----------------------------------------------------------
    mats = sorted({m for r in cands for m in (r.get("materials") or [])})
    h.append('<h3>Candidates</h3><div class="filters">'
             '<label>material <select id="f-mat"><option value="">(any)</option>'
             + "".join(f'<option>{esc(m)}</option>' for m in mats) + "</select></label>"
             '<label><input type="checkbox" id="f-exact"> exact overlap only</label>'
             '<label><input type="checkbox" id="f-exp"> experimental only</label>'
             '<label><input type="checkbox" id="f-har"> HAR / porous only</label>'
             '<label><input type="checkbox" id="f-high"> HIGH extraction value</label>'
             '<button type="button" id="f-reset">reset</button>'
             '<span class="hint" id="f-count"></span></div>')

    h.append('<table id="candtbl"><thead><tr><th>rank</th><th>candidate</th><th>title</th>'
             "<th>material</th><th>current overlap</th><th>papers for material</th>"
             "<th>process</th><th>study</th><th>geometry</th>"
             "<th>expected quantitative data</th><th>value</th><th>reason / evidence</th>"
             "</tr></thead><tbody>")
    for r in cands:
        har = 1 if r.get("geometry_context") in ("HAR/trench/via", "porous") else 0
        cur = r.get("current_material_counts") or {}
        curtxt = ", ".join(f"{k}:{v}" for k, v in sorted(cur.items())) or "—"
        h.append(
            f'<tr class="row" data-materials="{esc("|".join(r.get("materials") or []))}" '
            f'data-exact="{1 if r.get("exact_overlap") else 0}" '
            f'data-experimental="{1 if r.get("experimental") else 0}" '
            f'data-har="{har}" data-value="{esc(r.get("extraction_value"))}">'
            f'<td data-sort="{r.get("priority_rank") or 999}">{esc(r.get("priority_rank"))}</td>'
            f'<td><code>{esc(r["candidate_id"])}</code></td>'
            f'<td>{esc((r.get("title") or "")[:120])}</td>'
            f'<td>{esc(", ".join(r.get("materials") or []) or "—")}</td>'
            f'<td>{_overlap_badge(r)}</td>'
            f'<td data-sort="{max(cur.values()) if cur else 0}">{esc(curtxt)}</td>'
            f'<td>{esc(r.get("process_type"))}</td>'
            f'<td>{_study_badge(r)}</td>'
            f'<td>{esc(r.get("geometry_context"))}</td>'
            f'<td class="hint">{esc(", ".join(r.get("expected_data_types") or []) or "—")}</td>'
            f'<td data-sort="{r.get("priority_score", 0)}">{_value_badge(r.get("extraction_value"))}</td>'
            f'<td class="hint">{esc(r.get("priority_reason"))}</td></tr>')
        ev = r.get("material_evidence") or []
        h.append(
            '<tr class="detail"><td colspan="12"><details><summary>evidence and sources</summary>'
            f'<p><b>DOI:</b> {esc(r.get("doi") or "not found locally")} · '
            f'<b>figures:</b> {esc(r.get("n_figures"))} · <b>tables:</b> {esc(r.get("n_tables"))}</p>'
            f'<p><b>Abstract (local):</b> {esc(r.get("abstract_summary") or "—")}</p>'
            + "".join(f'<p><b>Material evidence — {esc(e["material"])}:</b> {esc(e["evidence"])}</p>'
                      for e in ev)
            + f'<p><b>Precursors:</b> {esc(", ".join(r.get("precursors") or []) or "—")} · '
              f'<b>Coreactants:</b> {esc(", ".join(r.get("coreactants") or []) or "—")}</p>'
              f'<p><b>Process evidence:</b> {esc(r.get("process_evidence") or "—")}</p>'
              f'<p><b>Study evidence:</b> {esc(r.get("study_evidence") or "—")}</p>'
              f'<p><b>Geometry evidence:</b> {esc(r.get("geometry_evidence") or "—")}</p>'
              f'<p><b>Source files:</b> <code>{esc(", ".join(r.get("source_paths") or []) or r.get("pdf") or "—")}</code></p>'
              f'<p><b>Uncertainty:</b> {esc(r.get("uncertainty") or "none noted")}</p>'
            + "</details></td></tr>")
    h.append("</tbody></table>")
    h.append('<p class="hint">Badges carry text as well as colour: EXACT / FAMILY / NEW, '
             'EXPERIMENTAL / EXPERIMENTAL? (inferred from figure captions) / MIXED / '
             'SIMULATION / REVIEW / UNCLEAR, and HIGH / MEDIUM / LOW extraction value. '
             'Click a column header to sort.</p>')
    h.append("</div>")
    h.append(JS)
    return h
