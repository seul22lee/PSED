#!/usr/bin/env python3
"""
scripts/build_figure_inventory_report.py — browsable HTML of every figure crop.

    python3 scripts/build_figure_inventory_report.py

Writes reports/figure_inventory.html: one card per Docling PictureItem in the corpus,
with its crop, its caption (original or recovered), where the caption came from, and
its disposition. Section A is the manual-review audit — the crops that carry no caption
evidence but look like plots, each with a human verdict recorded in VERDICTS below.

Read-only with respect to papers/: inventories are built in memory, never written.
Self-contained output — images are embedded as data URIs.
"""
import base64
import html
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                    # noqa: E402
from pipeline.figures import inventory as inv        # noqa: E402

THUMB = 260          # px, long edge, for the full listing
BIG = 620            # px, long edge, for the manual-review audit

#: verdicts from the manual visual audit of every MANUAL_REVIEW crop.
#: (paper, docling_index) -> (verdict, what it is, note)
VERDICTS = {
    ("10.1002_cnma.201700148", 0): (
        "SKIP", "HAL 'open science' repository logo",
        "Triage false positive: a logo on white reads as plot-like."),
    ("10.1002_pssa.201532305", 0): (
        "SKIP", "physica status solidi journal logo", ""),
    ("10.1002_pssa.201532305", 11): (
        "DRILL", "Growth rate (nm/cycle) vs substrate temperature, 3 pressure series with error bars",
        "A real ALD temperature-window dataset — currently lost."),
    ("10.1007_s11671-010-9676-0", 4): (
        "DRILL", "XPS survey spectrum, c/s vs binding energy, panel (a)", ""),
    ("10.1007_s11671-010-9676-0", 5): (
        "DRILL", "Iron concentration (%) vs ALD cycles, 4 points, panel (b)",
        "This paper is the corpus's only vision-stage failure (drill=1, records=0)."),
    ("10.1016_j.jcrysgro.2017.04.019", 1): (
        "SKIP", "Chemical reaction scheme for the Bi precursor synthesis", ""),
    ("10.1016_j.jcrysgro.2017.04.019", 9): (
        "SKIP", "Graphical abstract / TOC cycle diagram", ""),
    ("10.1016_j.jcrysgro.2017.04.019", 11): (
        "SKIP", "DuEPublico repository cover page (text only)", ""),
    ("10.1021_acs.jpcc.9b08176", 8): (
        "DRILL", "Normalized thickness vs distance / cavity height; SiO2, TiO2, Al2O3, HfO2 at several exposures",
        "Penetration profiles for four materials — a large, clearly digitizable loss."),
    ("10.1039_c5tc03561a", 1): ("SKIP", "Royal Society of Chemistry logo", ""),
    ("10.1039_c6dt03571j", 1): ("SKIP", "Royal Society of Chemistry logo", ""),
    ("10.1039_d3dt01824e", 8): (
        "DRILL", "Thickness (Å) vs number of ALD cycles, Si, with linear fit y=0.315x-65.602",
        "Directly yields GPC; currently lost."),
    ("10.1039_d3ra05217f", 3): (
        "AMBIGUOUS", "Table 1 (ALD precursor comparison) rendered as an image",
        "Not an x-y plot, so the figure route should skip it — but it is a TABLE "
        "delivered as a picture, so the table route cannot see it either. Needs a "
        "routing decision, not a drill decision."),
    ("10.1039_d3ra05217f", 9): (
        "DRILL", "Five-panel saturation study: growth rate vs H2O purge, precursor supply, "
                 "precursor purge; thickness vs cycles; growth rate vs deposition temperature",
        "A complete saturation + temperature-window dataset — the largest single loss found."),
    ("10.1116_1.4892385", 9): (
        "DRILL", "Degree of surface coverage 1-Θ vs position in porous substrate, three β0 curves",
        "Model output — drill with source=simulated."),
    ("10.1116_1.4938104", 11): (
        "DRILL", "Ultimate tensile strength (MPa) vs number of infiltration cycles, DEZ and TMA",
        ""),
    ("10.1116_1.4938104", 20): (
        "DRILL", "Response (Ion/Ioff) vs weight, with a current-vs-time inset",
        "Device-performance data; in scope as film_property_vs_condition."),
    ("cremers2019", 26): (
        "DRILL", "Composite: relative ZnO coverage vs distance, and wall thickness vs distance "
                 "with 2nd derivative, alongside SEM/TEM panels",
        "Mixed figure — the plot panels are digitizable, the micrographs are not."),
    ("cremers2019", 37): (
        "DRILL", "Gordon vs Monte-Carlo model grid: coverage (%) vs EAR, with and without bottom, "
                 "for s0 = 1 … 0.001",
        "Clearly digitizable simulation data; its PRINTED number is genuinely ambiguous "
        "(sits between FIG. 19 and FIG. 20, adjacent to neither)."),
}

BADGE = {"DRILL": "b-drill", "SKIP": "b-skip", "MERGE": "b-merge", "AMBIGUOUS": "b-amb"}
DISP_CLASS = {
    inv.DRILL: "b-drill", inv.OFFERED: "b-offer", inv.SKIP_WITH_REASON: "b-skip",
    inv.MANUAL_REVIEW: "b-amb", inv.MERGED_INTO_PRINTED_FIGURE: "b-merge",
}


def thumb(path, long_edge):
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        im.thumbnail((long_edge, long_edge))
        b = io.BytesIO()
        im.save(b, format="JPEG", quality=72, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ""


def esc(s):
    return html.escape(str(s or ""))


def card(pid, c, long_edge, verdict=None, paper=None):
    src = thumb(P.extracted_dir(pid) / c["image"], long_edge) if c.get("image") else ""
    cap = inv.caption_for(c)
    pf = c.get("printed_figure")
    bits = []
    if verdict:
        v, what, note = verdict
        bits.append(f'<span class="badge {BADGE[v]}">{esc(v)}</span>')
    bits.append(f'<span class="badge {DISP_CLASS.get(c["disposition"], "b-skip")}">'
                f'{esc(c["disposition"])}</span>')
    if c.get("printed_group_id"):
        bits.append(f'<span class="badge b-merge">split · {esc(c["printed_group_id"])}</span>')
    crop = c.get("crop") or {}
    meta = (f'{crop.get("width", "?")}×{crop.get("height", "?")} · {esc(crop.get("klass"))} · '
            f'caption via <b>{esc(c["caption_source"])}</b>'
            + (f' · {esc(c.get("association_method"))}' if c.get("association_method") else ""))
    body = ""
    if verdict:
        v, what, note = verdict
        body = (f'<p class="what">{esc(what)}</p>'
                + (f'<p class="note">{esc(note)}</p>' if note else ""))
    who = f'<span class="pf">{esc(paper)}</span>' if paper else \
          f'<span class="pf">printed {esc(pf) if pf else "—"}</span>'
    return f"""<div class="card{' flag' if verdict else ''}">
  <div class="hd"><span class="cid">{esc(c['candidate_id'])}
    {'· printed ' + esc(pf) if (paper and pf) else ''}</span>{who}</div>
  {'<img src="' + src + '">' if src else '<div class="noimg">no crop</div>'}
  <div class="badges">{''.join(bits)}</div>
  <div class="meta">{meta}</div>
  {body}
  <div class="cap">{esc(cap[:420]) if cap else '<i>no caption evidence</i>'}</div>
  <div class="why">{esc(c['disposition_reason'])}</div>
</div>"""


# Design notes. Subject: thin-film deposition provenance — a lab instrument's output,
# read by one scientist deciding which crops to keep. Utilitarian, scanned not read, so
# the craft goes into information design rather than an editorial hero.
#   Colour  ground #f6f7f9 / ink #171a21 with neutrals biased cool toward the accent;
#           accent #0f7c8a, the teal of interference fringes on a coated wafer, used
#           only for structure (rules, links, the audit marker). Verdict colours are
#           SEMANTIC and deliberately separate from the accent.
#   Type    three roles, all locally resolvable so the CSP can never cause a silent
#           webfont fallback: a serif for headings (Iowan/Charter/Georgia), the system
#           sans for prose, ui-monospace for identifiers and measurements.
#   Layout  summary tiles first, then the audit at large scale, then the full listing
#           grouped per paper — papers needing attention open, the rest collapsed.
CSS = """
:root{
  --bg:#f6f7f9; --card:#ffffff; --fg:#171a21; --mut:#5a6472; --line:#dde2e8;
  --accent:#0f7c8a; --accent-soft:#e2f0f2;
  --ok:#0f6c3d; --warn:#9a6208; --info:#1a5fb4; --merge:#6a4bab; --off:#54606f;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12151b; --card:#1a1f27; --fg:#e6eaf0; --mut:#98a3b3; --line:#2b323d;
  --accent:#4fc3d1; --accent-soft:#123034;
  --ok:#4cc38a; --warn:#e0a758; --info:#7cb0f0; --merge:#b39ae8; --off:#8b97a6;
}}
:root[data-theme="dark"]{
  --bg:#12151b; --card:#1a1f27; --fg:#e6eaf0; --mut:#98a3b3; --line:#2b323d;
  --accent:#4fc3d1; --accent-soft:#123034;
  --ok:#4cc38a; --warn:#e0a758; --info:#7cb0f0; --merge:#b39ae8; --off:#8b97a6;
}
*{box-sizing:border-box}
body{margin:0 auto;padding:34px 26px 72px;max-width:1500px;background:var(--bg);
 color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 font-variant-numeric:tabular-nums;}
h1,h2{font-family:"Iowan Old Style","Charter",Georgia,"Times New Roman",serif;
 font-weight:600;text-wrap:balance;}
h1{font-size:30px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:21px;margin:44px 0 6px;padding-bottom:7px;border-bottom:2px solid var(--accent)}
.sub{color:var(--mut);margin:0 0 16px;max-width:78ch}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 6px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:10px 14px;min-width:132px}
.stat b{display:block;font-size:23px;line-height:1.15}
.stat span{color:var(--mut);font-size:11.5px;text-transform:uppercase;letter-spacing:.06em}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:10px 0 0;font-size:12.5px;color:var(--mut)}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(288px,1fr))}
.grid.big{grid-template-columns:repeat(auto-fill,minmax(432px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:12px;overflow:hidden;display:flex;flex-direction:column;gap:7px}
.card.flag{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}
.card img{width:100%;height:auto;background:#fff;border-radius:7px;display:block;
 border:1px solid var(--line)}
.noimg{padding:26px;text-align:center;color:var(--mut);border:1px dashed var(--line);
 border-radius:7px;font-size:13px}
.hd{display:flex;justify-content:space-between;align-items:baseline;gap:8px;
 font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.cid{font-weight:700;color:var(--accent)} .pf{color:var(--mut)}
.badges{display:flex;flex-wrap:wrap;gap:5px}
.badge{font-size:10.5px;padding:2.5px 8px;border-radius:20px;font-weight:700;
 letter-spacing:.03em;white-space:nowrap;color:#fff}
.b-drill{background:var(--ok)}.b-skip{background:var(--off)}
.b-merge{background:var(--merge)}.b-amb{background:var(--warn)}
.b-offer{background:var(--info)}
.meta{font-size:11.5px;color:var(--mut);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.what{margin:0;font-weight:600;font-size:13.5px}
.note{margin:0;font-size:12.5px;color:var(--mut)}
.cap{font-size:12.5px;border-top:1px solid var(--line);padding-top:8px;margin-top:auto}
.why{font-size:11.5px;color:var(--mut);font-style:italic}
details{margin:12px 0;border:1px solid var(--line);border-radius:12px;
 background:var(--card);overflow:hidden}
details>summary{cursor:pointer;padding:11px 14px;font-family:ui-monospace,SFMono-Regular,
 Menlo,monospace;font-size:13px;list-style:none;display:flex;flex-wrap:wrap;gap:12px;
 align-items:baseline}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"▸";color:var(--accent);font-size:11px}
details[open]>summary::before{content:"▾"}
details>summary:hover{background:var(--accent-soft)}
details>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
summary .nm{font-weight:700} summary .ct{color:var(--mut);font-size:12px}
.body{padding:0 14px 14px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def main():
    papers = [p for p in sorted(P.papers()) if P.structure_json(p).exists()]
    invs = {p: inv.build(p) for p in papers}

    mr = [(p, c) for p in papers for c in invs[p]["candidates"]
          if c["disposition"] == inv.MANUAL_REVIEW]
    tot = sum(i["n_pictures"] for i in invs.values())
    capd = sum(i["n_captioned_by_docling"] for i in invs.values())
    rec = sum(i["n_captions_recovered"] for i in invs.values())
    counts = {}
    for i in invs.values():
        for c in i["candidates"]:
            counts[c["disposition"]] = counts.get(c["disposition"], 0) + 1
    vc = {}
    for p, c in mr:
        v = VERDICTS.get((p, c["docling_index"]))
        if v:
            vc[v[0]] = vc.get(v[0], 0) + 1

    out = [f"<title>PSED figure inventory — every crop and caption</title><style>{CSS}</style>",
           "<h1>Figure inventory — every Docling crop and its caption</h1>",
           f'<p class="sub">{len(papers)} papers · {tot} PictureItems · built read-only from '
           "papers/&lt;id&gt;/extracted. Machine identity (P&lt;docling index&gt;) is kept "
           "separate from printed figure number throughout.</p>",
           '<div class="stats">',
           f'<div class="stat"><b>{tot}</b><span>PictureItems</span></div>',
           f'<div class="stat"><b>{capd}</b><span>captioned by Docling</span></div>',
           f'<div class="stat"><b>{rec}</b><span>captions recovered</span></div>']
    for k in (inv.DRILL, inv.OFFERED, inv.MERGED_INTO_PRINTED_FIGURE,
              inv.MANUAL_REVIEW, inv.SKIP_WITH_REASON):
        if counts.get(k):
            out.append(f'<div class="stat"><b>{counts[k]}</b><span>{esc(k.lower())}</span></div>')
    out.append("</div>")
    out.append('<div class="legend">'
               '<span><span class="badge b-drill">DRILL</span> digitized by the vision stage</span>'
               '<span><span class="badge b-skip">SKIP_WITH_REASON</span> excluded, reason recorded</span>'
               '<span><span class="badge b-merge">MERGED</span> part of a split printed figure</span>'
               '<span><span class="badge b-amb">MANUAL_REVIEW</span> needs a human decision</span>'
               "</div>")

    out.append(f"<h2>Manual-review audit — {len(mr)} crops carrying no caption evidence</h2>")
    out.append('<p class="sub">These are the only crops the pipeline will not decide on its '
               "own: no caption could be recovered for them, but they do not look like "
               "logos or layout fragments either. Every one was opened and classified by "
               "eye. The verdict badge is the human call; the badge after it is what the "
               "pipeline currently does. — "
               + " · ".join(f"<b>{esc(k)}</b> {v}" for k, v in sorted(vc.items())) + "</p>")
    out.append('<div class="grid big">')
    for p, c in mr:
        v = VERDICTS.get((p, c["docling_index"]))
        out.append(card(p, c, BIG, v, paper=p))
    out.append("</div>")

    resolved = [(p, c) for p in papers for c in invs[p]["candidates"]
                if (p, c["docling_index"]) in VERDICTS
                and c["disposition"] != inv.MANUAL_REVIEW]
    if resolved:
        out.append(f"<h2>Resolved by printed-figure association — {len(resolved)} crops</h2>")
        out.append('<p class="sub">These carried no Docling caption and previously needed a '
                   "human decision. Each now has a printed-figure identity recovered from "
                   "structural evidence in the document, and the badge records which "
                   "evidence was used.</p>")
        out.append('<div class="grid big">')
        for p, c in resolved:
            out.append(card(p, c, BIG, VERDICTS.get((p, c["docling_index"])), paper=p))
        out.append("</div>")

    out.append("<h2>Full listing — every crop, every paper</h2>")
    out.append('<p class="sub">All %d PictureItems, grouped by paper. Papers with a '
               "recovered caption, a split printed figure or a manual-review crop are "
               "open; the rest are collapsed." % tot)
    for p in papers:
        i = invs[p]
        n_mr = sum(1 for c in i["candidates"] if c["disposition"] == inv.MANUAL_REVIEW)
        n_split = len({c["printed_group_id"] for c in i["candidates"] if c["printed_group_id"]})
        interesting = i["n_captions_recovered"] or n_split or n_mr
        flags = []
        if i["n_captions_recovered"]:
            flags.append(f'{i["n_captions_recovered"]} recovered')
        if n_split:
            flags.append(f"{n_split} split")
        if n_mr:
            flags.append(f"{n_mr} manual")
        out.append(f'<details{" open" if interesting else ""}><summary>'
                   f'<span class="nm">{esc(p)}</span>'
                   f'<span class="ct">{i["n_pictures"]} crops · '
                   f'{i["n_captioned_by_docling"]} docling captions'
                   + (" · " + " · ".join(flags) if flags else "") + "</span></summary>"
                   '<div class="body"><div class="grid">')
        for c in i["candidates"]:
            out.append(card(p, c, THUMB))
        out.append("</div></div></details>")

    dest = ROOT / "reports" / "figure_inventory.html"
    dest.write_text("\n".join(out))
    mb = dest.stat().st_size / 1e6
    print(f"wrote {dest}  ({mb:.1f} MB, {tot} crops, {len(mr)} manual-review)")
    return dest


if __name__ == "__main__":
    main()
