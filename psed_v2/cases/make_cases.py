#!/usr/bin/env python3
"""Exploration: writes cases/reports/cases.html, eleven example case studies (profiles, checked candidates, the review as data,
and Cases 9 to 11 on the part E candidates S1, S2, S3 with S6).

    python3 psed_v2/cases/make_cases.py

Inputs: cases/figures.csv (row selection), cases/points.json (points read by eye from the crops),
ingest/final/<paper_id>/ (figure crops), corpus/manifest.csv (first author and year for labels);
for Cases 9 to 11 also quantity_matrix.csv (usable_for), sticking_reported.csv, exposure_ear.csv and recombination.csv
(values read by hand from the papers, own words).
The page embeds the crops as JPEG, so it is gitignored with the rest of cases/reports/.
Nothing here is extracted data: every plotted point was read by eye.
"""
import base64, csv, html, io, json, math, re
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
OUT = HERE / "reports" / "cases.html"
E = html.escape

Y, M, W = "10.1063_1.5028178", "10.1039_d0cp03358h", "10.1116_6.0001094"
A9, PP, J5 = "10.1021_acs.jpcc.9b08176", "10.1063_5.0168768", "10.1021_acs.jpcc.5c06502"
NC, BJ = "10.1038_s41467-022-35428-6", "10.3762_bjnano.5.25"
D09, D10, GAO, A21 = "10.1149_1.3072694", "10.1149_1.3301664", "10.1116_1.4903941", "10.1021_acs.jpcc.1c01505"
# colour follows the paper within a plot; the four papers added on 2026-10-13 reuse slots that are free in the plots they appear in
SLOT = {Y: 1, M: 2, W: 3, A9: 4, PP: 5, J5: 6, D09: 3, GAO: 4, A21: 1, D10: 2}
DASH = ["", "6 3", "2 3", "8 3 2 3"]

# ----------------------------------------------------------------------------- inputs

with (V2 / "corpus/manifest.csv").open(newline="", encoding="utf-8") as f:
    MAN = {r["paper_id"]: r for r in csv.DictReader(f)}
with (HERE / "figures.csv").open(newline="", encoding="utf-8") as f:
    FIG = list(csv.DictReader(f))
PTS = json.loads((HERE / "points.json").read_text(encoding="utf-8"))["series"]


def who(pid: str) -> str:
    if pid.startswith("10.1063_1.5060967"):
        return "Cremers 2019"
    r = MAN.get(pid, {})
    parts = (r.get("authors") or "").split(";")[0].strip().split(" ")
    i = next((k for k, w in enumerate(parts) if w in ("van", "von", "de", "der")), len(parts) - 1)
    first = " ".join(parts[i:]) or pid
    return f"{first} {r.get('year', '')}".strip()


def crop(pid: str, fig) -> str:
    """<img> with the crop of a numbered figure, at most 900 px wide, embedded as JPEG."""
    st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
    cap = next(c for c in st["captions"] if c["kind"] == "figure" and str(c["number"]) == str(fig))
    out = []
    for rel in cap["images"]:
        im = Image.open(V2 / f"ingest/final/{pid}/{rel}").convert("RGB")
        if im.width > 900:
            im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)
        out.append(f'<img alt="{E(who(pid))}, Fig. {fig}, crop as published" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">')
    return "".join(out)


def selected_rows() -> list[dict]:
    def ok(r):
        if r["kind"] != "plot" or "measured" not in r["data_kind"]:
            return False
        x, y = r["x_id"], r["y_id"]
        if x.startswith("film_thickness") and y == "distance":      # axes swapped on the figure
            return True
        return re.sub(r"\{.*", "", x) in ("distance", "dimensionless_distance") and y.startswith(
            ("film_thickness", "normalized_thickness", "growth_per_cycle{position=local}", "coated_aspect_ratio"))
    return [r for r in FIG if ok(r)]


# ----------------------------------------------------------------------------- svg

class Plot:
    def __init__(s, w, h, xr, yr, xlog=False, xl="", yl="", xt=(), yt=(), title=""):
        s.w, s.h, s.xr, s.yr, s.xlog, s.xl, s.yl, s.title = w, h, xr, yr, xlog, xl, yl, title
        s.l, s.r, s.t, s.b = 58, 16, 30, 46
        s.e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}"><text x="{s.l}" y="16" class="pt">{E(title)}</text>']
        for v in yt:
            s.e.append(f'<line x1="{s.l}" x2="{w - s.r}" y1="{s.Y(v):.1f}" y2="{s.Y(v):.1f}" class="grid"/><text x="{s.l - 8}" y="{s.Y(v) + 4:.1f}" class="tk" text-anchor="end">{v:g}</text>')
        for v in xt:
            s.e.append(f'<line x1="{s.X(v):.1f}" x2="{s.X(v):.1f}" y1="{s.t}" y2="{h - s.b}" class="grid"/><text x="{s.X(v):.1f}" y="{h - s.b + 16}" class="tk" text-anchor="middle">{v:g}</text>')
        s.e.append(f'<line x1="{s.l}" x2="{w - s.r}" y1="{h - s.b}" y2="{h - s.b}" class="ax"/>')
        s.e.append(f'<text x="{(s.l + w - s.r) / 2}" y="{h - 8}" class="al" text-anchor="middle">{E(xl)}</text>')
        s.e.append(f'<text transform="translate(14 {(s.t + h - s.b) / 2}) rotate(-90)" class="al" text-anchor="middle">{E(yl)}</text>')

    def X(s, v):
        a, b = s.xr
        f = (math.log10(v) - math.log10(a)) / (math.log10(b) - math.log10(a)) if s.xlog else (v - a) / (b - a)
        return s.l + f * (s.w - s.l - s.r)

    def Y(s, v):
        a, b = s.yr
        return s.h - s.b - (v - a) / (b - a) * (s.h - s.t - s.b)

    def series(s, pts, slot, n, tip, dash="", line=True, open_square=False, tag_level=None):
        c = f"var(--s{slot})"
        if line:
            d = " ".join(f"{'M' if i == 0 else 'L'}{s.X(x):.1f} {s.Y(y):.1f}" for i, (x, y) in enumerate(pts))
            s.e.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2" stroke-dasharray="{dash}" stroke-linejoin="round"/>')
        for x, y in pts:
            t = f"<title>{E(tip)}: x {x:g}, y {y:.3g}</title>"
            if open_square:
                s.e.append(f'<rect x="{s.X(x) - 4.5:.1f}" y="{s.Y(y) - 4.5:.1f}" width="9" height="9" fill="var(--surface)" stroke="{c}" stroke-width="2">{t}</rect>')
            else:
                s.e.append(f'<circle cx="{s.X(x):.1f}" cy="{s.Y(y):.1f}" r="4" fill="{c}" stroke="var(--surface)" stroke-width="1.5">{t}</circle>')
        if tag_level is not None:
            x, y = min(pts, key=lambda p: abs(p[1] - tag_level))
            s.tag(x, y, n)

    def tag(s, x, y, n, dx=13, dy=-9):
        cx, cy = s.X(x) + dx, s.Y(y) + dy
        s.e.append(f'<rect x="{cx - (7 + 3.5 * len(str(n))):.1f}" y="{cy - 9:.1f}" width="{14 + 7 * len(str(n))}" height="18" rx="9" class="tagc"/><text x="{cx:.1f}" y="{cy + 4:.1f}" class="tag" text-anchor="middle">{n}</text>')

    def raw(s, x):
        s.e.append(x)

    def svg(s):
        return "".join(s.e) + "</svg>"


def swatch(slot, dash="", square=False):
    mark = ('<rect x="15" y="2" width="9" height="9" fill="var(--surface)" stroke="var(--s%d)" stroke-width="2"/>' % slot if square
            else '<circle cx="19" cy="7" r="4" fill="var(--s%d)"/>' % slot)
    return f'<svg class="sw" viewBox="0 0 38 14"><line x1="1" x2="37" y1="7" y2="7" stroke="var(--s{slot})" stroke-width="2" stroke-dasharray="{dash}"/>{mark}</svg>'


def table(head, rows, cls=""):
    return (f'<div class="tw"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


def before(cards):
    return '<div class="crops">' + "".join(
        f'<figure><figcaption><b>{E(who(pid))}</b> · Fig. {fig}{(" " + panel) if panel else ""}<span class="pid">{pid}</span></figcaption>{crop(pid, fig)}'
        + "<dl>" + "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in meta) + "</dl></figure>" for pid, fig, panel, meta in cards) + "</div>"


ILL = '<p class="ill">Illustrative: read by eye, not extracted data.</p>'
code = lambda t: f"<code>{E(t)}</code>"

# ----------------------------------------------------------------------------- case 1

def case1():
    ser = [p for p in PTS if p["case"] == 1]
    seen, plots, legend, half = {}, {}, [], {}

    def xhalf(pts):                                   # x/H where the curve crosses one half, by linear interpolation
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if ya >= 0.5 > yb:
                return xa + (ya - 0.5) * (xb - xa) / (ya - yb)
        return None
    for key, title in (("thermal", "Thermal ALD: 0.1 to 2 µm channels and one 0.1 mm hole"), ("plasma", "Plasma ALD, 0.5 µm channels"), ("macro", "Plasma ALD, macroscopic holes (shown apart)")):
        plots[key] = Plot(560, 380, (1, 2000), (0, 1.2), xlog=True, xt=(1, 3, 10, 30, 100, 300, 1000), yt=(0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2),
                          xl="distance / channel height, x/H (log scale)", yl="thickness / reference", title=title)
    levels = [0.82, 0.66, 0.5, 0.34, 0.18]
    for n, p in enumerate(ser, 1):
        key = "thermal" if p["process"] == "thermal" else "macro" if (p["H_um"] or 0) >= 100 else "plasma"
        half.setdefault(key, []).append(xhalf([(x * ((p["x_to_um"] / p["H_um"]) if p["H_um"] else 1.0), y / p["ref_value"]) for x, y in p["points"]]))
        k = seen.setdefault(p["paper"], []); k.append(n)
        dash = DASH[(len(k) - 1) % len(DASH)]
        fx = (p["x_to_um"] / p["H_um"]) if p["H_um"] else 1.0
        pts = [(x * fx, y / p["ref_value"]) for x, y in p["points"] if x * fx >= 1]
        chosen = p["reference_note"].startswith("NO PLATEAU")
        plots[key].series(pts, SLOT[p["paper"]], f"{n}*" if chosen else n, f"{n}. {who(p['paper'])}, {p['series']} [{p['reference']}]" + (" (no plateau, reference chosen)" if chosen else ""), dash=dash, tag_level=levels[n % len(levels)])
        legend.append([f'<span class="num">{n}</span>', swatch(SLOT[p["paper"]], dash), f"{E(who(p['paper']))}, Fig. {p['figure']}{p['panel']}", E(p["series"]), E(p["process"]),
                       code(f"normalized_thickness{{reference={p['reference']}}}"), ("<b>Reference chosen for this page.</b> " if chosen else "") + E(p["reference_note"].replace("NO PLATEAU: ", ""))])
    pl = plots["plasma"]
    pl.raw(f'<text x="{pl.w - pl.r - 6}" y="{pl.Y(1.13):.1f}" class="warn" text-anchor="end">* no plateau on this curve: the reference was chosen for this page</text>')
    pm = plots["macro"]
    pm.raw(f'<line x1="{pm.X(20):.1f}" x2="{pm.X(20):.1f}" y1="{pm.t}" y2="{pm.h - pm.b}" stroke="var(--text2)" stroke-dasharray="3 3"/><text x="{pm.X(20) + 6:.1f}" y="{pm.t + 14}" class="warn">ends of the two holes, x/H = 20 and 40</text>')
    pm.raw(f'<line x1="{pm.X(40):.1f}" x2="{pm.X(40):.1f}" y1="{pm.t + 20}" y2="{pm.h - pm.b}" stroke="var(--text2)" stroke-dasharray="3 3"/>')
    hp = [v for v in half["plasma"] if v]; ht = [v for v in half["thermal"] if v]; hm = [v for v in half["macro"] if v]
    cards_new = [
        (D09, 5, "", [("axes as printed", "depth (mm) / relative thickness"), ("normalization", "by the authors; reference not printed, curves start at 1"), ("structure", "macroscopic rectangular hole, 5 x 20 mm, aspect ratio 33, 50, 100"), ("conditions", "Al2O3 from TMA and water, 200 °C, 150 cycles, TMA 4 s at about 0.3 Pa (body text)"), ("data kind", "measured (ellipsometry)")]),
        (GAO, 5, "a-b", [("axes as printed", "Distance (µm), with Aspect Ratio on top / Thickness (nm); Aspect Ratio / Thickness (nm)"), ("normalization", "none"), ("structure", "lateral channel, gap 200, 500, 1000 nm"), ("conditions", "Al2O3 at 300 °C, 1109 cycles; TiO2 at 110 °C, 2000 cycles; 0.1 s pulses, no partial pressure given"), ("data kind", "measured (reflectometer, spot about 5 µm)")]),
        (A21, 2, "A", [("axes as printed", "Distance / cavity height / Normalized thickness"), ("normalization", "over the thickness just inside the cavity (stated)"), ("structure", "PillarHall, gap 500 nm"), ("conditions", "SiO2 from BDEAS and O2/Ar plasma, 50 mTorr, four table temperatures, 12 s plasma"), ("data kind", "measured (reflectometry)")]),
        (D10, 2, "a-b", [("axes as printed", "depth inside the test structure (mm) / film thickness (nm)"), ("normalization", "none"), ("structure", "macroscopic rectangular hole, 5 x 20 mm, aspect ratio 5, 10, 22, 50"), ("conditions", "Al2O3 from TMA with water (a) or O2 plasma (b), 200 °C, 200 cycles, same exposures (stated)"), ("data kind", "measured (ellipsometry)")]),
    ]
    cards = [
        (Y, 6, "", [("axes as printed", "Location (µm) / Film thickness (nm)"), ("normalization", "none"), ("structure", "PillarHall prototype 3, gap 0.5 µm nominal, AR 2000"), ("conditions", "Al2O3 from TMA and water, 500 cycles; temperature only in the body text"), ("data kind", "measured points with a fitted model curve")]),
        (M, 9, "a-f", [("axes as printed", "Distance inside the channel x (µm) / Film thickness S (nm); x̃ / S/N (nm); x̃ / Normalized thickness (-)"), ("normalization", "three forms of the same data, the last over the flat-region value, or over the entrance value where there is no flat region (H 100 nm)"), ("structure", "PillarHall, H 100, 500, 2000 nm"), ("conditions", "Al2O3 from TMA and water, 300 °C, 250 to 1000 cycles; samples defined in Table 1"), ("data kind", "measured")]),
        (W, 12, "", [("axes as printed", "Depth (m) / Coverage, with Thickness (nm) on a second axis"), ("normalization", "over an assumed saturated thickness of 22 nm (body text)"), ("structure", "macroscopic lateral trench, opening 1 mm, depth 20 mm, AR 20"), ("conditions", "Al2O3 from TMA and oxygen plasma, 150 W, 5 s, 120 °C (body text)"), ("data kind", "measured points with fitted curves")]),
        (A9, 2, "B", [("axes as printed", "Distance / cavity height, with Distance (µm) on top / Normalized thickness"), ("normalization", "reference not printed; curves start near 1"), ("structure", "PillarHall, gap 500 nm (body text)"), ("conditions", "four oxides, oxygen plasma 3.8 to 120 s, 50 mTorr, 200 °C (body text)"), ("data kind", "measured")]),
        (PP, 2, "a-b", [("axes as printed", "Distance / cavity height, with Distance (µm) on top / Thickness (nm)"), ("normalization", "none"), ("structure", "PillarHall LHAR4, gap 500 nm (body text)"), ("conditions", "SiO2 and TiO2, atmospheric-pressure spatial plasma ALD, 100 °C, plasma 0.24 to 0.73 s"), ("data kind", "measured")]),
        (J5, 10, "b", [("axes as printed", "Depth (µm) / Thickness (nm)"), ("normalization", "none"), ("structure", "PillarHall, gap 500 nm (body text)"), ("conditions", "IrOx, atmospheric-pressure spatial plasma ALD; samples A to D defined in Table 1"), ("data kind", "measured (optical grey scale scaled by ellipsometry)")]),
    ]
    onto = table(["Printed label", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["Location (µm); Distance inside the channel x (µm); Depth (µm); Depth (m)", code("distance"), code("x_over_width") + ": x / w with w = " + code("feature_width") + " → " + code("dimensionless_distance{by=H}"), "nothing; but H is only in the body text for three of the six papers"],
        ["Dimensionless distance x̃; Distance / cavity height", code("dimensionless_distance{by=H}"), "none", "the " + code("by") + " qualifier is not in the v0 qualifier list (added in this exploration)"],
        ["Film thickness (nm); Film thickness S (nm); Thickness (nm)", code("film_thickness"), code("normalize_thickness") + ": d(x) / d_ref → " + code("normalized_thickness{reference=…}"), "a reference value for a profile without a flat region; the v0 list has top, planar, assumed_saturation, and no value for “maximum” or “chosen”"],
        ["Normalized thickness (-)", code("normalized_thickness{reference=plateau}") + " (Yim, H 500 and 2000 nm), " + code("{reference=entrance}") + " (Yim, H 100 nm: no flat region), " + code("{reference=entrance}") + " (Arts, reference not printed)", "none", "“plateau” and “entrance” are not in the v0 list either"],
        ["Coverage", code("normalized_thickness{reference=assumed_saturation}"), "none", "“coverage” is an ambiguous alias (surface_coverage or normalized_thickness); resolved from the body text, not from the figure"],
    ])
    return f"""
<section id="c1"><h2>Case 1. Profiles across papers</h2>
<p class="q"><b>Question.</b> Once position is counted in channel heights and thickness in units of its own reference, how do thermal and plasma profiles from ten papers compare?</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards + cards_new)}
<h3><span class="step">Ontology step</span> From printed labels to one pair of ids</h3>{onto}
<h3><span class="step">After</span> All on <code>dimensionless_distance{{by=H}}</code> against <code>normalized_thickness</code></h3>{ILL}
<div class="plots">{plots['thermal'].svg()}{plots['plasma'].svg()}{plots['macro'].svg()}</div>
{table(["#", "", "Source", "Series", "Process", "y id with its reference", "How the reference was set"], legend, "leg")}
<p class="take"><b>Takeaway.</b> The half-thickness depth of the six thermal alumina profiles lies between x/H of {min(ht):.0f} and {max(ht):.0f}, from four papers and channel heights from 0.1 µm to 0.1 mm; five of the six fall between {sorted(ht)[1]:.0f} and {max(ht):.0f}. Among the 0.5 µm channels alone, the plasma profiles run from about {min(hp):.0f} to {max(hp):.0f} channel heights, a factor of {max(hp) / min(hp):.0f}. The two macroscopic plasma holes add nothing to that spread: they reach one half at x/H of {" and ".join(f"{v:.0f}" for v in hm)}, close to their ends at 20 and 40, so they are limited by their own length and are drawn apart. Only three of the nine plasma curves in microscopic channels, all SiO2, have a flat or nearly flat region to normalize by.</p>
<p class="lim"><b>Limits.</b> Points were read by eye from the crops. Curves marked * depend on a reference chosen here, so their height is a convention, not a result. One macroscopic hole uses its authors' assumed 22 nm, and its points near the entrance sit above 1. The 0.1 mm thermal hole ends at x/H = 200, close to its front. Cycles, pulse times and partial pressures still differ between curves; this view removes only the units and the normalization. Channel narrowing by film growth is not corrected.</p>
</section>"""


# ----------------------------------------------------------------------------- case 2

def case2():
    ser = [p for p in PTS if p["case"] == 2]
    pl = Plot(760, 430, (-2, 5.4), (0, 1000), xt=(-2, -1, 0, 1, 2, 3, 4, 5), yt=(0, 200, 400, 600, 800, 1000),
              xl="ln(plasma time per cycle / s)", yl="half-thickness depth / cavity height", title="Half-thickness penetration against log plasma time")
    x0 = pl.X(-2); xm = pl.X(0.05)
    pl.raw(f'<text x="{pl.X(1.2):.1f}" y="{pl.Y(900):.1f}" class="reg">low pressure, 50 mTorr · filled circles</text>')
    pl.raw(f'<text x="{x0 + 8:.1f}" y="{pl.Y(330):.1f}" class="reg">atmospheric pressure · open squares</text>')
    rows = []
    for n, p in enumerate(ser, 1):
        atm = p["regime"].startswith("atmospheric")
        slot = SLOT[p["paper"]]
        dash = "" if p["series"].startswith("SiO2") else "6 3" if p["series"].startswith("TiO2") else "2 3"
        (xa, ya), (xb, yb) = p["fit_line_as_drawn"]
        if xb > pl.xr[1]:                                   # keep the line inside the plot area
            yb, xb = ya + (yb - ya) * (pl.xr[1] - xa) / (xb - xa), pl.xr[1]
        pl.raw(f'<line x1="{pl.X(xa):.1f}" y1="{pl.Y(ya):.1f}" x2="{pl.X(xb):.1f}" y2="{pl.Y(yb):.1f}" stroke="var(--s{slot})" stroke-width="2" stroke-dasharray="{dash}"/>')
        pl.series(p["points"], slot, n, f"{n}. {who(p['paper'])}, {p['series']}, {p['regime']}", line=False, open_square=atm)
        x, y = p["points"][-1]
        pl.tag(x, y, n, dx=14 if n < 6 else -16, dy=-10 if n not in (2, 8) else 14)
        slope = (yb - ya) / (xb - xa)
        rows.append([f'<span class="num">{n}</span>', swatch(slot, dash, atm), f"{E(who(p['paper']))}, Fig. {p['figure']} {p['panel']}", E(p["series"]), E(p["regime"]), f"{slope:.0f}", E(p["r_printed"]), E(p["source"])])
    r = 6e-5
    cards = [
        (A9, 3, "", [("axes as printed", "ln(Plasma time (s)) / PD50% / cavity height"), ("structure", "PillarHall, gap 500 nm (body text)"), ("conditions", "SiO2 and TiO2, oxygen plasma at 50 mTorr, 200 °C (body text)"), ("relation printed on the plot", "r = (4/3)·(Δln t / Δz̃)²"), ("data kind", "measured points with linear fits")]),
        (PP, 3, "", [("axes as printed", "Ln(Plasma time (s)) / PD50% / cavity height"), ("structure", "PillarHall LHAR4, gap 500 nm (body text)"), ("conditions", "SiO2 and TiO2, atmospheric-pressure spatial plasma ALD, 100 °C"), ("relation printed on the plot", "slope = 1 / √(4.26 r)"), ("data kind", "measured points with linear fits")]),
        (A21, 2, "B", [("axes as printed", "ln(Plasma time (s)) / PD50% / cavity height"), ("structure", "PillarHall, gap 500 nm"), ("conditions", "SiO2 and TiO2, O2/Ar plasma; table temperature 100 to 400 °C at 50 mTorr, and 12 to 130 mTorr at 200 °C"), ("relation used", "the low-pressure relation, written in the paper"), ("data kind", "measured points with linear fits; Figs. 3 and 4 have the same layout")]),
        (J5, 10, "b inset", [("axes as printed", "ln(plasma time (s)) / PD50% / h"), ("structure", "PillarHall, gap 500 nm (body text)"), ("conditions", "IrOx, atmospheric-pressure spatial plasma ALD; four samples in Table 1"), ("relation used", "the atmospheric relation (body text)"), ("data kind", "measured points with a linear fit; inset too small to read, values taken from Table 1")]),
    ]
    onto = table(["Printed label", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["PD50% / cavity height; PD50% / h", code("coated_aspect_ratio{basis=AR}"), code("coated_ar") + ": PD / w, already applied by the authors", "nothing"],
        ["ln(Plasma time (s))", code("pulse_time{step=reactant_B}"), "natural logarithm of the value", "no transform for a logarithm; the axis is unmapped in the inventory for that reason"],
        ["plasma time per cycle (spatial reactors)", code("pulse_time{step=reactant_B}"), "none", "in a spatial reactor this is a transit time under the plasma head, set by rotation speed; the entry does not distinguish it from a timed pulse"],
        ["pressure regime", code("process_pressure") + ", " + code("reactor_type") + " = atmospheric", "none", "no Knudsen number or diffusion-regime entry; the regime decides which slope relation applies"],
        ["r (written on two plots)", code("recombination_probability{species=o_atom, surface=<material>}"), "from the slope, by the relation of the regime", "the two relations are not model entries; data_kind is fit"],
    ])
    return f"""
<section id="c2"><h2>Case 2. O-radical recombination</h2>
<p class="q"><b>Question.</b> Does the recombination probability of oxygen radicals depend on the material and on the pressure regime?</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> Same pair of ids, different meaning of the slope</h3>{onto}
<h3><span class="step">After</span> One plot, pressure regime marked</h3>{ILL}
<div class="plots one">{pl.svg()}</div>
{table(["#", "", "Source", "Material", "Pressure regime", "Slope of the line as drawn", "r printed by the authors", "Where the points come from"], rows, "leg")}
<p class="note"><b>Equal slopes do not mean equal probabilities.</b> With the two relations printed on the plots, one probability of {r:g} gives a slope of {math.sqrt(4 / (3 * r)):.0f} at low pressure and {1 / math.sqrt(4.26 * r):.0f} at atmospheric pressure. TiO2 shows this: its two lines differ in slope by more than a factor of two (lines 2 and 4), yet the authors report nearly the same probability in both regimes. A slope can be compared only inside one regime.</p>
<p class="take"><b>Takeaway.</b> The three papers share both axis ids, so they can be put on one plot, but the result to compare is the probability with its regime attached, not the slope.</p>
<p class="lim"><b>Limits.</b> Points and line ends were read by eye; slopes here are those of the lines as drawn, not refits. The IrOx points are the four table values. The first atmospheric TiO2 point may not be recombination limited, as its authors note. Plasma power, gas mixture and temperature differ between the papers and are not on this plot. Lines 6 to 8 are three of the twelve conditions of one paper, added on 2026-10-13: within one regime and one reactor the slope still changes by a factor of two with temperature.</p>
</section>"""


# ----------------------------------------------------------------------------- case 3

def card(title, cond, panels, link, crops, kind=""):
    return (f'<div class="card"><div class="cardtxt"><h4>{E(title)}</h4><p>{E(cond)}</p>'
            + table(["Panel", "Method", "Location on the sample", "What it shows"], [[E(a), E(b), E(c), E(d)] for a, b, c, d in panels])
            + (f'<p class="link"><b>Kind of link.</b> {E(kind)}</p>' if kind else "") + f'<p class="link"><b>Link evidence.</b> {E(link)}</p></div><div class="cardimg">' + "".join(
                f'<figure><figcaption><b>{E(who(pid))}</b> · Fig. {fig}<span class="pid">{pid}</span></figcaption>{crop(pid, fig)}</figure>' for pid, fig in crops) + "</div></div>")


def case3():
    sets = [r for r in FIG if r["sample"] and not r["sample"].startswith(("u:", "possibly", "cited")) and r["paper_id"] in (M, A9, NC, BJ)]
    cards = [
        card(f"{who(M)} · sample S11", "Al2O3 from TMA and water, 300 °C, 1000 cycles, PillarHall channel with 500 nm design height. Sample 11 of the paper's Table 1 (cycle series).",
             [("Fig. 5a", "SEM with EDS map", "top view of the opened channel, both sides of the opening", "where Al is present, as a colour overlay"),
              ("Fig. 5b", "SEM-EDS line scan", "across the opening, origin at its centre", "Al, O and Si signal against distance; a signal, not a thickness"),
              ("Fig. 9d-f", "reflectometry line scan", "from the channel entrance inward", "the 1000-cycle thickness profile, in three forms")],
             "Stated. The captions of Fig. 5 and Fig. 9 both name sample 11 of Table 1.", [(M, 5), (M, 9)]),
        card(f"{who(A9)} · samples LH1 to LH8", "Eight depositions in PillarHall channels (gap 500 nm): SiO2 at four plasma times, TiO2 at two, Al2O3 and HfO2 at one. Oxygen plasma at 50 mTorr, 200 °C (body text).",
             [("Fig. 2A", "optical microscopy", "top view of the opened channel, entrance at the top", "the coated area as a darker band, with the half-thickness aspect ratio written under each image"),
              ("Fig. 2B", "reflectometry with a 10 µm spot (body text)", "from the channel entrance inward", "normalized thickness against distance over cavity height"),
              ("Fig. 3", "derived from Fig. 2B", "not applicable", "half-thickness depth against log plasma time, for SiO2 and TiO2")],
             "Stated. Panels A and B are one figure of the same structures, and the numbers under the images are the half-thickness depths of the profiles; the caption of Fig. 3 says its data are those presented in Fig. 2.", [(A9, 2)]),
        card(f"{who(NC)} · samples H0, H40, H60, H40w", "TiO2 from TDMAT, nominal 40 nm, in tapered holes 1600 nm deep (100 nm opening, 50 nm bottom), after no inhibitor, 40 s, 60 s, and 40 s with a water pulse.",
             [("Fig. 4a", "TEM cross-section", "whole hole, top to bottom", "the film in the hole; seam without inhibitor, filled bottom with it"),
              ("Fig. 4b", "TEM, thickness read along the hole", "sidewall, from the top down to about 1200 nm", "thickness against depth; thinnest at the top when the inhibitor is used"),
              ("Fig. 4c", "derived from Fig. 4b", "same positions", "selectivity against depth")],
             "Stated. One figure; the caption gives panel b as growth in these holes and panel c as calculated from the TEM results.", [(NC, 4)]),
        card(f"{who(BJ)} · sample S400", "TiO2 on a vertically aligned carbon nanotube array, 400 cycles. Exposure and temperature only in the body text.",
             [("Fig. 6a", "SEM cross-section", "whole array, with close-ups at about 5, 25 and 80 µm depth", "thick closed coating near the top, beads at mid depth, only nuclei deep down"),
              ("Fig. 6b", "SEM, tube diameter", "depth 0 to 40 µm", "oxide thickness against depth, for 400 and 200 cycles")],
             "Stated. One figure; the caption says the image is the 400-cycle array and that the thickness in panel b was obtained from the coated tube diameters.", [(BJ, 6)]),
    ]
    onto = table(["What has to be recorded", "Where it goes", "Missing"], [
        ["which physical sample a panel shows", "the sample key of the gold tables (" + code("experiment_kind = sample") + ")", "nothing in the vocabulary; the link itself has to be extracted, with its evidence"],
        ["how each panel was obtained", code("measurement_method") + " (reflectometry, sem, sem_eds, optical_microscopy, afm, …)", "tem is not in the v0 list; “derived from another panel” has no value"],
        ["where on the sample", code("position") + " qualifier (planar, top, sidewall, bottom) and " + code("distance"), "no field for the location of an image (entrance, depth, magnification)"],
        ["why two panels are the same sample", "a link with its source: " + code("condition_source") + " = caption, body or table", "no status for “possibly”; " + code("condition_status") + " has stated, approximated, inferred"],
    ])
    return f"""
<section id="c3"><h2>Case 3. One sample, several measurements</h2>
<p class="q"><b>Question.</b> Which thickness profiles can be tied to an image of the very same sample, and on what evidence?</p>
<h3><span class="step">Before</span> In the papers the link is spread over captions and tables</h3>
<p>Among the selected profile papers, four sample sets pair a profile with an image and state the link. The crops are shown inside each card below.</p>
<h3><span class="step">Ontology step</span> What a sample link needs</h3>{onto}
<h3><span class="step">After</span> One card per sample</h3>{''.join(cards)}
<p class="take"><b>Takeaway.</b> A profile becomes checkable when its sample key also points to an image: here four sample sets carry such a stated link, three inside one figure and one across two figures through a sample number.</p>
<p class="lim"><b>Limits.</b> Only stated links are shown; links that rest on matching conditions alone are listed as “possibly” in CANDIDATES.md and left out here. Three of the four are links inside a single figure, which are the easy case. No points were read for this case. {len(sets)} inventory rows of these four papers carry a named sample key.</p>
</section>"""


# ----------------------------------------------------------------------------- case 4 (N1 + N2)

SSE, D1, NSR, SEP, ADEM, KEU, D4 = ("10.1016_j.sse.2022.108584", "10.1039_d1cp04758b", "10.1093_nsr_nwaf247", "10.3390_separations11010024",
                                    "10.1002_adem.202201901", "10.1116_1.4892385", "10.1039_d4cp00131a")
TAB = '<p class="ill">Values from the papers\' tables and captions, not read by eye.</p>'


def case4():
    cards = [
        (Y, 6, "", [("role", "original measurement, with the authors' own fit"), ("axes as printed", "Location (µm) / Film thickness (nm)"), ("sample", "alumina, 500 cycles, gap 0.5 µm"), ("data kind", "measured; fit")]),
        (M, 11, "a", [("role", "original measurement"), ("axes as printed", "Distance inside the channel x (µm) / Film thickness S (nm)"), ("samples", "TMA pulse 0.1, 0.2, 0.4 s (Table 1)"), ("data kind", "measured")]),
        (SSE, 6, "", [("role", "re-use: calibration of a new model"), ("axes as printed", "z position (µm) / Al2O3 thickness (nm)"), ("what is re-used", "the profile of the first crop, two of the three of the second, and one from a paper outside the corpus"), ("data kind", "cited; fit (by hand and by eye, stated)")]),
        (SSE, 7, "", [("role", "re-use: prediction with the same parameters"), ("axes as printed", "z position (µm) / Al2O3 thickness (nm)"), ("what is re-used", "the three channel heights of the next crop, panel a"), ("data kind", "cited; simulation")]),
        (M, 9, "a-f", [("role", "original measurement"), ("axes as printed", "three forms, see case 1"), ("samples", "three heights, three cycle numbers (Table 1)"), ("data kind", "measured")]),
        (M, 10, "a-f", [("role", "the authors' own simulation, laid out like the measurement"), ("axes as printed", "same as the previous crop"), ("inputs", "listed with the figure; sticking coefficient 0.012"), ("data kind", "simulation, not adjusted to the previous crop")]),
    ]
    onto = table(["What is on the page", "Ontology id or field", "Transform", "Missing in the ontology"], [
        ["a profile copied from another paper", code("data_kind = cited") + " on the series", "none", "no link from a cited series to the figure and sample it was taken from"],
        ["a curve adjusted to the points", code("data_kind = fit") + " (the authors write “calculated” or “simulation”)", "none", "nothing; the rule is in CRITERIA (first match: adjusted to measured data)"],
        ["a curve run with parameters from an earlier fit", code("data_kind = simulation"), "none", "no field for where the parameters came from, so a prediction looks like any simulation"],
        ["c, c_TMA, β0", code("initial_sticking_coefficient{species=tma}"), "none", "a model entry for the newer coverage model; a parameter for its evaporation flux"],
        ["z position (µm); Location (µm); Distance inside the channel x (µm)", code("distance"), code("x_over_width") + " for the after view", "nothing"],
    ])
    lineage = table(["Original", "Reappears in", "As", "Stated by the later paper"], [
        [f"{E(who(Y))} Fig. 6 (alumina, 500 cycles)", f"{E(who(SSE))} Fig. 6", "cited; fit", "yes, by reference"],
        [f"{E(who(M))} Fig. 11a (pulse 0.1 and 0.2 s)", f"{E(who(SSE))} Fig. 6", "cited; fit", "yes, by reference and pulse time"],
        [f"{E(who(M))} Fig. 9a (H 100, 500, 2000 nm)", f"{E(who(SSE))} Fig. 7", "cited; simulation (parameters of Table 2, not re-adjusted; diffusivity formula changed for 2 µm)", "yes, in text and caption"],
        ["Arts 2019 (10.1116/1.5093620, no PDF)", f"{E(who(SSE))} Fig. 4 and Fig. 6", "cited; fit", "yes"],
        [f"{E(who(Y))} Fig. 2 and Fig. 3 (model output)", f"{E(who(D1))} Fig. 2a-b", "simulation with the same inputs", "yes, in the caption"],
        [f"{E(who(A21))} Fig. 5A (r at 100 °C: SiO2 about 1e-4, TiO2 about 4e-5)", f"{E(who(PP))} Table I and Fig. 4, low-pressure lines", "cited (9e-5 and 4e-5), then calculated", "yes; the source is now in the corpus and its figure agrees. These are not the values of " + E(who(A9))],
        ["a literature table of sticking and recombination values in " + E(who("10.1149_1.3491381")) + " (Tables I, II)", "Tables V and VII of the 2019 review", "cited, with rows added", "yes, in the table captions"],
        ["a TMA sticking value quoted in " + E(who("10.1021_cm0303080")) + " from an earlier paper and used as a model input", "that literature table, then Table V of the review, as a Monte Carlo result", "cited twice; the method label changes on the way", "no"],
    ])
    # sticking coefficient of TMA from the same alumina profiles
    vals = [("Arts 2019, slope method (quoted range)", 0.5e-3, 2e-3, "cited"), (f"{who(M)}, slope method, Table 2", 4e-3, None, "calculated"), (f"{who(Y)}, model fit, Table I", 5.72e-3, None, "fit"),
            (f"{who(SSE)}, model fit by hand, Table 2", 7.5e-3, None, "fit"), (f"{who(M)}, input of the Fig. 10 simulation", 0.012, None, "simulation input")]
    w, h, l, r, t = 820, 250, 330, 170, 34
    X = lambda v: l + (math.log10(v) - math.log10(2e-4)) / (math.log10(3e-2) - math.log10(2e-4)) * (w - l - r)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Sticking coefficient of TMA by paper"><text x="12" y="16" class="pt">Sticking coefficient of TMA drawn from the same alumina profiles</text>']
    for v in (3e-4, 1e-3, 3e-3, 1e-2, 3e-2):
        e.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{h - 40}" class="grid"/><text x="{X(v):.1f}" y="{h - 24}" class="tk" text-anchor="middle">{v:g}</text>')
    e.append(f'<text x="{(l + w - r) / 2}" y="{h - 6}" class="al" text-anchor="middle">initial sticking coefficient (log scale)</text>')
    for i, (lab, a, b, kind) in enumerate(vals):
        y = t + 18 + i * 34
        e.append(f'<text x="{l - 12}" y="{y + 4}" class="tk" text-anchor="end" style="font-size:12px">{E(lab)}</text>')
        tip = f"<title>{E(lab)}: {a:g}{(' to %g' % b) if b else ''} ({kind})</title>"
        if b:
            e.append(f'<line x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{y}" y2="{y}" stroke="var(--s1)" stroke-width="6" stroke-linecap="round">{tip}</line>')
        elif kind == "fit":
            e.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="6" fill="var(--s1)">{tip}</circle>')
        else:
            e.append(f'<rect x="{X(a) - 5.5:.1f}" y="{y - 5.5}" width="11" height="11" fill="var(--surface)" stroke="var(--s1)" stroke-width="2.5">{tip}</rect>')
        e.append(f'<text x="{X(b or a) + 12:.1f}" y="{y + 4}" class="tk" style="font-size:12px">{a:g}{(" to %g" % b) if b else ""} · {kind}</text>')
    dot = "".join(e) + "</svg>"
    # measured against simulated, Yim Fig. 9c and 10c
    ser = [p for p in PTS if p["case"] == 4]
    pl = Plot(760, 400, (0, 320), (0, 1.1), xt=(0, 50, 100, 150, 200, 250, 300), yt=(0, 0.2, 0.4, 0.6, 0.8, 1.0), xl="distance / channel height, x/H", yl="thickness / plateau value",
              title="Measured (points) against simulated with chosen inputs (dashed)")
    hs = {"100 nm": 1, "500 nm": 2, "2000 nm": 3}
    leg = []
    for n, p in enumerate(ser, 1):
        slot, simu = hs[p["H"]], p["kind"] == "simulation"
        if simu:
            d = " ".join(f"{'M' if i == 0 else 'L'}{pl.X(x):.1f} {pl.Y(y):.1f}" for i, (x, y) in enumerate(p["points"]))
            pl.raw(f'<path d="{d}" fill="none" stroke="var(--s{slot})" stroke-width="2" stroke-dasharray="6 4"><title>{E(p["series"])}</title></path>')
            x, y = min(p["points"], key=lambda q: abs(q[1] - 0.2)); pl.tag(x, y, n, dx=16, dy=6)
        else:
            pl.series(p["points"], slot, n, f"{n}. {p['series']}", tag_level=0.72)
        leg.append([f'<span class="num">{n}</span>', swatch(slot, "6 4" if simu else "") if not simu else f'<svg class="sw" viewBox="0 0 38 14"><line x1="1" x2="37" y1="7" y2="7" stroke="var(--s{slot})" stroke-width="2" stroke-dasharray="6 4"/></svg>',
                    f"{E(who(p['paper']))}, Fig. {p['figure']}{p['panel']}", E(p["series"]), code("data_kind = " + p["kind"]), code(f"normalized_thickness{{reference={p.get('reference', 'plateau')}}}")])
    return f"""
<section id="c4"><h2>Case 4. One experiment through the literature, and fit against prediction</h2>
<p class="q"><b>Question.</b> Which curves in later papers are new evidence, which are the same samples again, and which model curves were adjusted to the data they are drawn with?</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> The data kind and the source of each curve</h3>{onto}
<h3><span class="step">After</span> A lineage, the numbers drawn from it, and one measured-against-simulated view</h3>
{lineage}{TAB}<div class="plots one">{dot}</div>{ILL}<div class="plots one">{pl.svg()}</div>
{table(["#", "", "Source", "Series", "Data kind", "y id"], leg, "leg")}
<p class="take"><b>Takeaway.</b> Three samples of two papers carry four later figures, and the sticking coefficient attached to them runs from 0.5e-3 to 12e-3 depending on the model and on whether the number is a fit, a slope formula or a chosen input.</p>
<p class="lim"><b>Limits.</b> The lineage rests on the later papers' own references; the last three rows were added on 2026-10-13 when the sources were obtained; the re-drawn points were not compared with the originals point by point. In the prediction figure only two of the three profiles are new to the model, and one of them needs a different diffusivity formula. The simulated curves in the last plot were not adjusted to the measured ones, so their agreement is neither a fit nor an independent test. Points were read by eye; the measured 500 nm and 100 nm curves end in spikes that are left out.</p>
</section>"""


# ----------------------------------------------------------------------------- case 5 (N3)

N3 = [
    (Y, "3", "Surface coverage (θ)", "covered site fraction after one pulse", "surface_coverage"),
    ("10.1039_d3cp01829f", "2, 3", "Surface coverage θ", "covered fraction after one exposure; called a saturation profile", "surface_coverage"),
    (D4, "1a", "s/N over gpc_sat, and θ, on one axis", "thickness per cycle over its saturation value, set equal to coverage", "normalized_thickness{reference=assumed_saturation}; equal to surface_coverage only without channel narrowing"),
    (W, "11, 12", "Coverage", "thickness after 200 cycles over an assumed 22 nm (body text)", "normalized_thickness{reference=assumed_saturation}"),
    (KEU, "2", "Degree of surface coverage 1-Θ", "Θ is the free fraction, so the plotted quantity is the covered one", "surface_coverage = 1 − Θ"),
    (NSR, "1b, 1d, 1f", "-OH surface coverage", "hydroxyl groups left unreacted after the TMA step", "1 − surface_coverage of the TMA step"),
    (NSR, "3a, 3d", "DMA(ads)+MMA(ads) surface coverage", "adsorbed aluminium species, the product side", "surface_coverage"),
    (NC, "2e", "Areal coverage (%)", "area fraction taken by inhibitor molecules, saturating near 50%", "surface_coverage on an area basis; no qualifier for the basis"),
    (SSE, "5b", "θ_sat", "coverage at saturation, below 1 because adsorption is reversible", "surface_coverage at long exposure; no entry"),
    (Y, "5", "Penetration depth x_p", "front position of the model after one pulse", "penetration_depth{level=other:model front}"),
    (M, "Table 1", "x50%, PD50%", "depth of half the thickness", "penetration_depth{level=50%}"),
    ("10.1039_d3cp01829f", "4", "x̃ at θ = 0.5", "depth of half coverage, in channel heights", "coated_aspect_ratio{basis=AR}, on coverage; no qualifier for coverage against thickness"),
    ("10.1039_d3cp05639b", "2 to 8", "r at θ = 1/2", "both the depth coordinate of a profile and the half-coverage depth", "distance in one use, penetration_depth{level=50%} in the other"),
    (SSE, "5b", "SC_sat", "coverage at the bottom over coverage at the top, at saturation", "not step_coverage, which is a thickness ratio"),
    ("10.1021_acs.jpclett.4c03545", "1, 2", "SC", "bottom thickness over top thickness: 1 and 1.6", "step_coverage{position=bottom}"),
    ("10.1021_acsami.0c06879", "S2", "SC", "shell thickness at two points 900 nm apart along a wire", "step_coverage, with no matching position value"),
]


def case5():
    cards = [
        (Y, 3, "", [("printed", "Surface coverage (θ)"), ("means", "covered fraction after one pulse"), ("data kind", "simulation")]),
        (W, 11, "", [("printed", "Coverage"), ("means", "thickness after 200 cycles over an assumed 22 nm; points exceed 1"), ("data kind", "measured; fit")]),
        (KEU, 2, "a-b", [("printed", "Degree of surface coverage 1-Θ"), ("means", "Θ is the free fraction"), ("data kind", "simulation")]),
        (NSR, 1, "b, d, f", [("printed", "-OH surface coverage"), ("means", "sites left unreacted: low is good"), ("data kind", "simulation")]),
        (D4, 1, "a", [("printed", "s/N over gpc_sat and θ on one axis"), ("means", "a thickness ratio set equal to a coverage"), ("data kind", "sketch, no values")]),
    ]
    onto = table(["Printed word", "Candidate ids", "How it was decided", "Missing in the ontology"], [
        ["coverage", code("surface_coverage") + " or " + code("normalized_thickness"), "by what was counted: sites after one exposure, or thickness after many cycles; twice only the body text says", "already an ambiguous alias in v0; a basis qualifier (sites, area) and a complement transform are missing"],
        ["penetration depth", code("penetration_depth{level=…}") + " or " + code("coated_aspect_ratio"), "by the level (half thickness, half coverage, model front) and by whether it is divided by the width", "not in the v0 list of ambiguous aliases; the level qualifier cannot say coverage or thickness"],
        ["step coverage, SC", code("step_coverage{position=…}"), "by the two positions and by whether thickness or coverage is compared", "not in the v0 list of ambiguous aliases; no position value for two points along a wire"],
    ])
    after = table(["Paper", "Figure", "Printed symbol", "What it means", "Ontology id with qualifier"],
                  [[f"{E(who(pid))}<span class='pid'>{pid}</span>", E(fig), E(sym), E(mean), code(oid)] for pid, fig, sym, mean, oid in N3])
    return f"""
<section id="c5"><h2>Case 5. One symbol, several meanings</h2>
<p class="q"><b>Question.</b> Which printed words for coverage, penetration and step coverage name the same quantity, and which do not?</p>
<h3><span class="step">Before</span> Five figures that all say “coverage”</h3>{before(cards)}
<h3><span class="step">Ontology step</span> Three words that need a decision each time</h3>{onto}
<h3><span class="step">After</span> The table</h3>
<p>No plot and no points in this case: the comparable view is the mapping itself.</p>{after}
<p class="take"><b>Takeaway.</b> Matching on the printed label would merge six different quantities under “coverage”, one of them the complement of another; the id has to be assigned from what was counted and when.</p>
<p class="lim"><b>Limits.</b> The reading of Θ as a free fraction rests on the axis label alone. The 22 nm and the meaning of the hydroxyl coverage are stated only in the body text. The table covers the papers with a PDF, not the field.</p>
</section>"""


# ----------------------------------------------------------------------------- case 6 (N5)

def case6():
    ser = [p for p in PTS if p["case"] == 6]
    panels = {"part": ("Points on a 3D part", (0.5, 11.5), tuple(range(1, 12)), "point number on the part (as printed: Location)"),
              "tube": ("Spots along a tube", (0.5, 5.5), (1, 2, 3, 4, 5), "spot number from the inlet (as printed: Measurement position)"),
              "batch": ("Slots of a wafer batch", (0, 26), (1, 5, 10, 20, 25), "slot number in the carrier (as printed: Wafer slot)")}
    plots = {k: Plot(430, 330, xr, (0, 2.4), xt=xt, yt=(0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4), xl=xl, yl="growth per cycle / series mean", title=t) for k, (t, xr, xt, xl) in panels.items()}
    count, rows = {}, []
    for n, p in enumerate(ser, 1):
        k = p["panel_key"]; i = count.get(k, 0); count[k] = i + 1
        ys = [y for _, y in p["points"]]; mean = sum(ys) / len(ys)
        pts = [(x, y / mean) for x, y in p["points"]]
        plots[k].series(pts, i + 1, n, f"{n}. {who(p['paper'])}, {p['series']}", dash=DASH[i])
        x, y = pts[-1]; plots[k].tag(x, y, n, dx=-2, dy=-16 if i % 2 == 0 else 18)
        rows.append([f'<span class="num">{n}</span>', swatch(i + 1, DASH[i]), f"{E(who(p['paper']))}, Fig. {p['figure']}{p['panel']}", E(p["series"]), len(ys), f"{min(ys):g} to {max(ys):g}",
                     f"{(max(ys) - min(ys)) / (2 * mean) * 100:.0f}%", E(p["printed_spread"])])
    cards = [
        (NSR, 3, "a, d", [("position given as", "a point number, 1 to 11, on a drawing of the part"), ("axes as printed", "Location / GPC (Å cycle-1), with coverage, refractive index and etch rate stacked above and below"), ("conditions", "alumina from TMA and water, without and with baffles"), ("data kind", "measured, with a simulated coverage in the top strip")]),
        (SEP, 3, "", [("position given as", "a spot number, 1 to 5, along a 100 mm strip in the tube; spacing not on the figure"), ("axes as printed", "Measurement position (-) / GPC (Å)"), ("conditions", "titania from TiCl4 and water, atmospheric pressure, 125 °C, three carrier flows"), ("data kind", "measured")]),
        (ADEM, 3, "a-b", [("position given as", "none: one percentage per wafer"), ("axes as printed", "Precursor dose (Torr) or Temperature (°C) / Non-uniformity (%)"), ("conditions", "alumina from TMA and water, pump-type batch reactor"), ("data kind", "measured; the percentage is defined in the paper from maximum, minimum and mean")]),
        (ADEM, 4, "a", [("position given as", "a slot number, 1 to 25, in the wafer carrier"), ("axes as printed", "Wafer slot / GPC (Å/cycle), with Non-uniformity (%) on a second axis"), ("conditions", "loads of 5 and 25 wafers"), ("data kind", "measured")]),
    ]
    onto = table(["Printed label", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["GPC (Å cycle-1); GPC (Å); GPC (Å/cycle)", code("growth_per_cycle{position=local}") + " for the part and the tube, " + code("{position=planar}") + " per wafer", "divided by the mean of its series, for the after view only", "nothing for the quantity"],
        ["Location; Measurement position (-); Wafer slot", "unmapped", "none possible: these are labels, not lengths", "no entry for a position label, and no coordinate system for a part, a tube or a batch"],
        ["Non-uniformity (%); NU", code("thickness_nonuniformity"), "none", "no qualifier for the scope (within a wafer, across a batch, over a part) or for the formula"],
        ["surface coverage (simulated, same positions)", code("surface_coverage"), "none", "the simulated counterpart of a measured thickness is a different quantity"],
    ])
    return f"""
<section id="c6"><h2>Case 6. Reactor-scale uniformity</h2>
<p class="q"><b>Question.</b> How even is growth over a part, along a tube and across a batch, and can the three be put on one scale?</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> The quantity maps, the position does not</h3>{onto}
<h3><span class="step">After</span> Side by side, not overlaid: each series over its own mean, against the position label as given</h3>{ILL}
<div class="plots">{plots['part'].svg()}{plots['tube'].svg()}{plots['batch'].svg()}</div>
{table(["#", "", "Source", "Series", "Points", "Range read (Å per cycle)", "Half-range over mean, from the points read", "Spread printed by the authors"], rows, "leg")}
<p class="take"><b>Takeaway.</b> The three studies can share a y axis but not an x axis: what can be compared is one spread per series, from a few percent in a wafer batch to tens of percent on a 3D part without baffles.</p>
<p class="lim"><b>Limits.</b> Points were read by eye. The half-range over mean computed here follows the formula one of the papers prints; whether the other paper's printed percentages use the same formula is not stated, and they do not match the values computed here. The three x axes are labels and must not be read as distances; the panels are separate for that reason. The wafer-batch series carries a within-wafer value on a second axis that is a different scope.</p>
</section>"""


# ----------------------------------------------------------------------------- case 7

ZN, NI, JES, MO, WC, LAN = "10.1116_6.0003182", "10.1021_acsami.0c06879", "10.1149_2.067203jes", "10.1116_6.0002804", "10.1021_acs.chemmater.6c00816", "10.1021_acs.langmuir.6b03119"


def case7():
    cards = [
        card(f"{who(ZN)} · runs C120, C160, Ccyc", "ZnO from diethylzinc and water inside pressed alumina nanoparticle compacts about 1.5 mm thick, 20 cycles, each dose a pulse followed by a long static hold. Three runs: 120 °C, 160 °C, and cycled between the two.",
             [("Fig. 2a-c", "chamber pressure gauge", "the reactor, during the run (first five cycles shown)", "pressure against time for each run"),
              ("Fig. 2d", "temperature record", "the reactor, cycled run", "the temperature programme"),
              ("Fig. 3a-c", "chamber pressure gauge, with derived quantities", "the reactor, one hold and all 20 cycles", "pressure rise during a hold, gas released per cycle, final slope: steady rise at 160 °C"),
              ("Fig. 5", "XRD", "the coated compact; position on it not stated", "metallic zinc only in the 160 °C run"),
              ("Fig. 6a-c", "SEM with EDS maps", "cross-section through the full thickness", "Al and Zn maps for each run"),
              ("Fig. 6d-f", "SEM-EDS line scan", "from one face to the other, 0 to 1.5 mm", "Zn level flat at 120 °C and cycled, uneven at 160 °C")],
             "Stated, at the level of the run: every caption names the run by its temperature schedule. The mass gains carry a sample-to-sample spread, so a run holds more than one compact, and which piece was sectioned is not stated.",
             [(ZN, 2), (ZN, 3), (ZN, 5), (ZN, 6)], kind="Process monitor to outcome: an in-process record of the run tied to post-process measurements of what it made."),
        card(f"{who(NI)} · samples c1, c5, c7, c10", "Nickel shells on GaAs nanowires precoated with 5 nm alumina, one sample per value of the cycle parameter c (1, 5, 7, 10); 170 °C, annealed at 350 °C.",
             [("Fig. 4a-d", "TEM with diffraction inset", "interface between wire and shell", "roughness and crystallinity of the shell"),
              ("Fig. 4e-h", "dark-field STEM", "a wire segment", "continuity of the shell"),
              ("Fig. 4i-l", "STEM-EDS map", "the same segment, with the scan window marked", "Ga in the core, Ni in the shell"),
              ("Fig. 4m-p", "STEM-EDS line scan", "across the wire, inside the marked window", "shell thickness on each side, written on the plot: 15 and 17, 17 and 17, 35 and 35, 16 and 17 nm"),
              ("Fig. 2a-f", "AFM, XRD", "planar films with the same four values of c", "roughness and phase of planar films")],
             "Stated for Fig. 4: the caption says each column of panels is one sample. Only possibly for the planar films of Fig. 2: they share the value of c and the text compares their roughness trend, but they are different substrates and the paper does not say they were coated in the same run.",
             [(NI, 4), (NI, 2)], kind="Several methods on one sample (image, map, line scan), plus a second link across substrates that is only possibly."),
        card(f"{who(JES)} · stack ST1", "A stack of alternating alumina and SiO2 layers on silicon, 10 to 40 cycles per layer, 200 °C.",
             [("Fig. 3", "TEM cross-section", "the whole stack, with the cycles of each layer written on it", "eight layers, thicker where more cycles were used"),
              ("Fig. 2b", "TEM (stars) and in-situ ellipsometry (circles)", "the SiO2 layers of the same stack", "thickness against cycles; read by eye: 0.9 and 1.3 nm at 10 cycles, 2.4 and 2.5 at 20, 2.9 and 3.1 at 25, 4.6 and 4.8 at 40")],
             "Stated: the caption of Fig. 2b says its thicknesses were taken from the image of Fig. 3 and compared with ellipsometry on the same sample; the caption of Fig. 3 points back to Fig. 2b.",
             [(JES, 3), (JES, 2)], kind="Image to number: values read from one micrograph become data points in a plot of another figure."),
        card(f"{who(MO)} · trench piece", "Molybdenum from MoCl2O2 and atomic hydrogen on silicon trenches with an SiO2 cap; trench aspect ratios from 2 to 10 on the piece (body text).",
             [("Fig. 9a", "STEM cross-section", "four trenches side by side; arrows at the top, the sidewall and the bottom of one", "written on the image: 100% at the top, 95% on the sidewall, 90% at the bottom"),
              ("Fig. 9b", "TEM with Fourier transform", "one trench", "continuous film, crystalline")],
             "Stated, and the definition is in the body text only: thickness at a position over thickness on top, for the trench of aspect ratio 3. No thickness in nanometres is given.",
             [(MO, 9)], kind="The image is the measurement: the numbers exist only as annotations on the micrograph."),
        card(f"{who(WC)} · trench piece", "Tungsten carbide from a carbonyl precursor and hydrogen plasma, 200 cycles, 250 °C, 200 W, on a trench 392 nm high and 260 nm wide at the bottom (aspect ratio about 1.5).",
             [("Fig. 4a", "TEM cross-section", "top, two points on the sidewall, bottom", "written on the image: 20.08 nm at the top, 15.96 and 15.45 nm on the sidewall, 15.96 nm at the bottom"),
              ("Fig. 4b", "STEM-EDS map", "the same trench", "W along the whole wall"),
              ("Fig. 4c", "high-resolution TEM", "film on top of the trench", "lattice fringes")],
             "Stated: one figure, and the caption repeats the values rounded (about 20 and about 16 nm, step coverage about 80%). From the image, bottom over top is 15.96 / 20.08 = 0.79.",
             [(WC, 4)], kind="The image is the measurement: thickness values with their positions are annotations on the micrograph."),
        card(f"Contrast · {who(LAN)}, the 5 s nanotube layer", "Alumina from TMA and water in a 20 µm titania nanotube layer. Fig. 2 shows a layer coated with 5 s exposure at four depths; Fig. 3a has a 5 s series among four.",
             [("Fig. 2a-d", "SEM", "top, near top, centre, bottom of a layer coated with 5 s exposure", "coating at four depths"),
              ("Fig. 3a", "SEM, coating thickness", "four depths, four exposure times", "thickness against tube diameter and depth, including a 5 s series"),
              (f"{who(M)} Fig. 8b", "reflectometry", "four chips from four runs with the same recipe", "fronts that differ by tens of µm although the conditions are nominally equal")],
             "Possibly, not stated: the conditions match (5 s exposure) but no caption or sentence says the layer of Fig. 2 is the one measured in Fig. 3. The third crop is the reason this matters: nominally equal runs do not give equal profiles, so equal conditions cannot stand in for a sample link.",
             [(LAN, 2), (LAN, 3), (M, 8)], kind="No link: matching conditions only."),
    ]
    onto = table(["What the knowledge base has to hold", "Where it goes in v0", "What v0 lacks"], [
        ["a key for the physical sample, and one for the run that made it", code("experiment_kind") + " = sample or in_situ_run", "no relation between a run record and the samples it produced; no level (run, piece)"],
        ["how each panel was obtained", code("measurement_method") + ": reflectometry, spectroscopic_ellipsometry, xrr, optical_microscopy, sem, sem_eds, afm, oes, eqp", "tem, stem, stem_eds, xrd, a pressure or temperature record of the process, a photograph"],
        ["where on the sample", code("position") + " qualifier: planar, top, sidewall, bottom; " + code("distance"), "view (top view, cross-section), depth of an image, the window a line scan was taken in"],
        ["that two panels show the same sample, and why", code("condition_source") + " (caption, methods, table, body) and " + code("condition_status") + " (stated, approximated, inferred)", "a link record of its own; a status for “possibly”; a place for the sentence that states the link"],
        ["that a number was taken from another panel", "none", "“derived from panel” as a method or as a relation between series"],
        ["a value written on an image", code("panel_type") + " = image, " + code("series_structure") + " = image", "an image panel cannot carry values with positions; today such numbers would be lost or filed as caption text"],
    ])
    return f"""
<section id="c7"><h2>Case 7. One sample, many measurements, across figures and methods</h2>
<p class="q"><b>Question.</b> Outside the profile papers, which samples are seen by several figures or methods, what kind of link ties them, and what must the knowledge base hold to keep that link?</p>
<h3><span class="step">Before</span> The links as the papers give them</h3>
<p>Five stated sample sets from part B of CANDIDATES.md, and one contrast. The crops are inside each card.</p>
<h3><span class="step">Ontology step</span> What a link needs</h3>{onto}
<h3><span class="step">After</span> One card per sample</h3>{''.join(cards)}
<p class="take"><b>Takeaway.</b> Four kinds of link occur: a process record tied to its outcome, several methods on one sample, an image turned into numbers, and an image that is itself the measurement. Each is stated in a caption, and none can be recovered from matching conditions alone.</p>
<p class="lim"><b>Limits.</b> The thickness pairs of the stack were read by eye and are illustrative. For the compacts the link holds for the run, not for a named piece. The percentages on the molybdenum image have no nanometre values behind them in the paper. The contrast card shows one of 18 “possibly” links; the others are in CANDIDATES.md.</p>
</section>"""


# ----------------------------------------------------------------------------- case 8

def review_crop(page, box, label):
    """A region of a page of the review PDF (fractions of the page: left, top, right, bottom), at most 900 px wide."""
    import subprocess, tempfile
    pdf = V2 / "corpus/raw/10.1063_1.5060967.pdf"
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "130", "-f", str(page), "-l", str(page), "-jpeg", str(pdf), d + "/p"], check=True)
        im = Image.open(next(Path(d).glob("p-*.jpg"))).convert("RGB")
    w, h = im.size
    im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    if im.width > 900:
        im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=78, optimize=True)
    return f'<img alt="{E(label)}, crop as published" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def case8():
    import runpy
    B = runpy.run_path(str(HERE / "cremers" / "build.py"))
    T = lambda head, rows: table([E(str(h)) for h in head], [[E(str(c)) for c in r] for r in rows])
    crops = [
        ("Table II (first page)", 15, (0.05, 0.07, 0.95, 0.56), [("film (process)", "deposited material with precursor and co-reactant"), ("substrate, EAR", "test structure and its equivalent aspect ratio, converted by the review's authors"), ("exposure", "in 10³ L; blank in most rows"), ("coated EAR", "equal to the structure's EAR when fully coated (a lower bound); the half-thickness depth when marked with an asterisk"), ("D", "a thickness profile was published")]),
        ("Table IV (first page)", 18, (0.05, 0.07, 0.95, 0.56), [("plasma configuration", "C, I, R, RE as defined in the caption"), ("other columns", "as Table II"), ("note", "most coated values equal the structure value")]),
        ("Table V", 19, (0.05, 0.37, 0.95, 0.78), [("species, deposited material", "reactant and the film it grows"), ("method", "how the value was obtained, as the review labels it"), ("sticking probability", "header says sticking probability; the checked sources give initial values")]),
        ("Table VII", 20, (0.5, 0.07, 0.95, 0.62), [("atom, surface", "O, N or H on a named surface; no temperature, pressure or method column"), ("r", "recombination probability, some with an uncertainty")]),
    ]
    bef = '<div class="crops">' + "".join(f'<figure><figcaption><b>Cremers 2019</b> · {E(t)}<span class="pid">10.1063_1.5060967</span></figcaption>{review_crop(pg, box, t)}<dl>' + "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in meta) + "</dl></figure>" for t, pg, box, meta in crops) + "</div>"
    onto = table(["In the review", "Ontology id with qualifiers", "Transform", "What v0 lacks"], [
        ["coated EAR, with or without an asterisk", code("coated_aspect_ratio{basis=EAR}"), "none", "a qualifier for the reading: complete (the structure was fully coated, so a lower bound) or PD50 (a measured depth); v0's basis says only AR or EAR"],
        ["every table value", code("data_kind = cited") + " with the reference number", "none", "a link from a cited value to the source and to where in it the value stands; a status for the source check (agree, differ, not found)"],
        ["exposure in 10³ L", code("exposure{species=…}") + " in Pa·s", "1 L = 10⁻⁶ Torr s = 1.33 × 10⁻⁴ Pa s", "L is an accepted unit in v0; the species is often not said (precursor or co-reactant), and the tables mix both"],
        ["EAR of the structure", code("equivalent_aspect_ratio"), "from depth, width and structure class: hole L/w, trench L/(2w), elongated hole L(w+z)/(2wz)", "v0 records EAR as reported and has one plain " + code("aspect_ratio") + " transform; no rule per structure class, and nothing for pores open at both ends"],
        ["recombination probability r", code("recombination_probability{species, surface}"), "none", "temperature, pressure and the kind of surface (sintered ceramic or growing film) as conditions of the value; method"],
        ["sticking probability", code("initial_sticking_coefficient{species}"), "none", "the model behind a fitted value, whether it is a result or an input, and the co-reactant of the process"],
    ])
    binc = T(["Point", "What the page says", "After checking"], [
        ["Unit relation, Sec. II D", "1 L = 10^6 Torr s = 7500 Pa s", "wrong as printed (it is 10^-6 Torr s, and 1 Pa s = 7500 L); the tables use the right relation"],
        ["PD50% mark", f"{len(B['unmarked'])} rows with a coated value below the structure value and no mark; {len(B['pd_eq'])} rows with the mark and equal values", "one marked row is contradicted by its source (ref. 178: the profile never falls to one half)"],
        ["One structure, two values", "a 65 nm by 50 µm membrane as 770 and as 700; holes of 130 nm by 2 µm as 20 and as 15.3", "770 and 15.4 follow from the dimensions"],
        ["Text against tables", "ozone Al2O3 20:1 in the text, a reference in the table; O on Pyrex 0.000094 in the text, 0.000045 in the table", "not resolved here"],
    ])
    return f"""
<section id="c8"><h2>Case 8. The review read as data</h2>
<p class="q"><b>Question.</b> What can the tables of the 2019 review tell once they are typed in, and what can they not?</p>
<h3><span class="step">Before</span> Four of the six tables as published</h3>{bef}
<h3><span class="step">Ontology step</span> What a table row becomes</h3>{onto}
<h3><span class="step">After</span> The tables joined, counted and checked against {len(B['SC'])} source rows</h3>
<h4>a. Coated EAR against exposure, TMA and water</h4><p class="ill">Transcribed from Cremers 2019, cited data; orange marks read by eye in the sources.</p>
<div class="plots one">{B['pa']}</div>
{T(["Exposure (10³ L)", "Coated EAR", "Reading", "Structure", "Where"], [[x, y, {"lower": "lower bound", "measured": "measured, by eye", "upper": "upper bound"}[k], lab, wh] for x, y, k, lab, wh in B['A_SRC']])}
<p class="note">The square law of ref. 62, evaluated for TMA, predicts an aspect ratio of {B['gordon_a'](9e3):.0f} at 9 × 10³ L; ref. 67 measures 47 to 53. For the membrane of ref. 65 it asks for {B['gordon_L'](385) / 1e3:.0f} × 10³ L when the pores are entered from both ends, and the source finds the centre coated between 150 and 450. So the model overestimates the need there by about 1.2 to 3.5 times. The review's row for that membrane (770 at 4500) is a fully coated structure at about eight times the predicted need and at twice the diffusion length. The source states that both faces of the membrane are exposed and models the pores as entered from both ends.</p>
<h4>c. Recombination probability against coated EAR, plasma ALD</h4><p class="ill">Transcribed from Cremers 2019, cited data.</p>
<div class="plots one">{B['pc']}</div>
<p class="note">Only {sum(1 for r in B['c_rows'] if r['basis'] == 'PD50')} of the {len(B['c_rows'])} matched rows are measured depths; the rest are bounds set by the structure. One of the two measured rows does not survive its source check (0.3, not 0.75).</p>
<p class="ill">Transcribed from Cremers 2019, cited data, beside values from the papers' own tables and figures.</p><div class="plots one">{B['pr']}</div>
<p class="note"><b>Titania.</b> The Table VII value (0.014) is for a sintered ceramic at 300 K in a 110 Pa air plasma, where r rises with temperature. On the growing ALD film in a lateral channel r is about 4 × 10⁻⁵ and falls with temperature. The two differ by a factor of 350 or more and move in opposite directions, so a Table VII value cannot stand in for the growth surface.</p>
<h4>d. Same film, different oxidant</h4><p class="ill">Transcribed from Cremers 2019, cited data; the last two rows read by eye in the sources.</p>
{T(["Film", "Structure matched on", "Thermal", "Ozone", "Plasma", "Remark"], B['D'])}
<h4>e. Sticking values</h4><p class="ill">Transcribed from Cremers 2019, cited data, beside values from the papers' own tables and text. Open squares are simulation inputs or quotations, not results.</p>
<div class="plots one">{B['ps']}</div>
<h4>f. How many coated values are bounds</h4><p class="ill">Transcribed from Cremers 2019, cited data.</p>
{T(["Table", "complete (lower bound)", "PD50% (measured)", "conformal (no number)", "blank or other"], B['f_cnt'])}
<h4>b. Internal consistency of the review</h4>{binc}
<h4>g. Rows with a published profile (marked D)</h4>
{T(["Ref.", "DOI", "Films (table)", "Year", "PDF", "Open access"], B['g_rows'])}
<p class="take"><b>Takeaway.</b> Typed in, the tables give counts the review does not state: an exposure in 27 of 140 rows, and a measured depth in 20, against 87 lower bounds. Joined to their sources, they give two results the review could not: the square law of ref. 62 for TMA and water matches one source (ref. 67) and overestimates the needed exposure for the other (ref. 65) by about 1.2 to 3.5 times, and the recombination values listed for oxide surfaces are not those of growing films. Values from 10.1016_j.cattod.2003.11.022 (Guyon 2004) are marked: that paper is out of scope as not an ALD paper and is used only as a cited source.</p>
<p class="lim"><b>Limits.</b> {len(B['SC'])} of 208 table rows were checked against a source ({B['sc_cnt']['agree']} agree, {B['sc_cnt']['differ']} differ, {B['sc_cnt']['not found']} not found); the rest are as printed. Source values marked "by eye" were read from figures. The square-law line assumes a saturation density taken from another paper. The joins in c use a surface match chosen here, and 30 plasma rows have no fair match. Only {sum(1 for g in B['g_rows'] if g[4] == 'have it')} of the {len(B['g_rows'])} profile sources have a PDF.</p>
</section>"""


# ----------------------------------------------------------------------------- case 9 (S1)

CM, KR, GD, KIM, SC, FB = "10.1021_cm0303080", "10.1116_1.4971196", "10.1149_1.2789802", "10.1063_1.2714685", "10.1016_j.surfcoat.2012.02.038", "10.1002_cvde.200390005"
AP9, AP10, CNT, ZR, BJ2, LG, PT = "10.1016_j.apsusc.2009.02.055", "10.1016_j.apsusc.2010.01.025", "10.1021_acs.chemmater.1c03164", "10.1116_1.4892385", "10.3762_bjnano.5.25", "10.1021_acs.langmuir.6b03119", "10.1116_6.0003182"
with (HERE / "quantity_matrix.csv").open(newline="", encoding="utf-8") as f:
    QM = {r["paper_id"]: r for r in csv.DictReader(f)}
USE = lambda tag: [p for p, r in QM.items() if tag in r["usable_for"].split("; ")]
with (HERE / "sticking_reported.csv").open(newline="", encoding="utf-8") as f:
    REP = list(csv.DictReader(f))


def slope_method(p):
    """Slope |dθ/dx̃| at the front from the points in 0.2 <= θ <= 0.8 (least squares), x̃ = x / H for channels and cavities,
    x / (d/2) for holes and pores; θ = y / plateau (the highest point when no plateau was read). Returns slope, band points, x̃ at θ = 0.5."""
    pl = p["plateau"] or max(y for _, y in p["points"])
    if p["x_unit_um"] is None:
        f = 1.0
    else:
        f = p["x_unit_um"] / (p["H_um"] if ("channel" in p["geometry"] or "cavity" in p["geometry"]) else p["H_um"] / 2)
    pts = sorted((x * f, y / pl) for x, y in p["points"])
    band = [(x, y) for x, y in pts if 0.2 <= y <= 0.8]
    x50 = next((xa + (ya - 0.5) * (xb - xa) / (ya - yb) for (xa, ya), (xb, yb) in zip(pts, pts[1:]) if ya >= 0.5 > yb), None)
    if len(band) < 2 or x50 is None:
        return None, len(band), x50
    mx = sum(x for x, _ in band) / len(band); my = sum(y for _, y in band) / len(band)
    sxx = sum((x - mx) ** 2 for x, _ in band)
    return (abs(sum((x - mx) * (y - my) for x, y in band) / sxx) if sxx else None), len(band), x50


def logdots(rows, title, xr=(1e-6, 1), w=860):
    """Rows: (label, [(value, kind, tip)]) on a log x axis; kind: re (filled circle), fit (open square), input (open diamond), lit (cross)."""
    L, R, T, B, lab = 300, 20, 34, 46, 290
    h = T + B + 26 * len(rows)
    X = lambda v: L + (math.log10(v) - math.log10(xr[0])) / (math.log10(xr[1]) - math.log10(xr[0])) * (w - L - R)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}"><text x="12" y="18" class="pt">{E(title)}</text>']
    for k in range(round(math.log10(xr[0])), round(math.log10(xr[1])) + 1):
        e.append(f'<line x1="{X(10 ** k):.1f}" x2="{X(10 ** k):.1f}" y1="{T}" y2="{h - B}" class="grid"/><text x="{X(10 ** k):.1f}" y="{h - B + 16}" class="tk" text-anchor="middle">1e{k}</text>')
    e.append(f'<text x="{(L + w - R) / 2}" y="{h - 8}" class="al" text-anchor="middle">sticking value (log scale)</text>')
    for i, (label, marks) in enumerate(rows):
        y = T + 13 + 26 * i
        e.append(f'<line x1="{L}" x2="{w - R}" y1="{y}" y2="{y}" stroke="var(--grid)" stroke-dasharray="2 3"/><text x="{lab}" y="{y + 4}" class="tk" text-anchor="end" style="font-size:12px">{E(label)}</text>')
        for v, kind, tip in marks:
            x, t = X(min(max(v, xr[0]), xr[1])), f"<title>{E(tip)}</title>"
            if kind == "re":
                e.append(f'<circle cx="{x:.1f}" cy="{y}" r="5.5" fill="var(--s1)" stroke="var(--surface)" stroke-width="1.5">{t}</circle>')
            elif kind == "fit":
                e.append(f'<rect x="{x - 5:.1f}" y="{y - 5}" width="10" height="10" fill="var(--surface)" stroke="var(--s2)" stroke-width="2">{t}</rect>')
            elif kind == "input":
                e.append(f'<path d="M{x:.1f} {y - 7} L{x + 7:.1f} {y} L{x:.1f} {y + 7} L{x - 7:.1f} {y} Z" fill="var(--surface)" stroke="var(--s4)" stroke-width="2">{t}</path>')
            else:
                e.append(f'<path d="M{x - 5:.1f} {y - 5} L{x + 5:.1f} {y + 5} M{x - 5:.1f} {y + 5} L{x + 5:.1f} {y - 5}" stroke="var(--text2)" stroke-width="2">{t}</path>')
    return "".join(e) + "</svg>"


# probe and lateral resolution of each profile, as stated in the papers (µm; None = not stated)
RES = {Y: ("reflectometer, 50× objective", 5, "text: roughly 5 µm spot"), M: ("reflectometer, 50× objective", 6, "text: 5–6 µm spot for Fig. 9 (25 and 50 µm in Fig. 7)"),
       GAO: ("reflectometer, 50×", 5, "text: about 5 × 5 µm² spot"), D09: ("spectroscopic ellipsometer", None, "spot not stated"), D10: ("spectroscopic ellipsometer", None, "spot not stated"),
       CM: ("EPMA line scan", 5, "text: 3–5 µm spatial resolution"), KR: ("micro-spot ellipsometer", 10, "text: 10 µm spot"),
       GD: ("TEM", None, "not stated (nm scale)"), AP9: ("TEM", None, "not stated (nm scale)"), AP10: ("TEM", None, "not stated (nm scale)")}
# the papers' own values for the channel profiles, split by kind (from sticking_reported.csv)
FIT = {(Y, "TMA"): 5.72e-3, (M, "TMA"): 4e-3, (M, "H2O"): 3e-4, (Y, "TiCl4"): 0.10}
CHOSEN = {(Y, "TMA"): 0.01, (D09, "TMA"): 0.1, (D10, "TMA"): 0.1, (D10, "H2O"): 0.05}


def group9(p):
    if p["paper"] == GAO:
        return "Al2O3 (TMA/H2O), limiting species not stated" if p["series"].startswith("Al2O3") else "TiO2 (TiCl4/H2O), limiting species not stated"
    return "H2O" if p["species_limiting"].startswith("H2O") else p["species_limiting"].split(" ")[0]


def case9():
    ser = [p for p in PTS if p["case"] == 9]
    slope_ok, model = USE("S1 slope"), USE("S1 model")
    rows, per, reslim = [], {}, []
    for n, p in enumerate(ser, 1):
        is_model = p["series"].startswith("model curve")
        s, nb, x50 = slope_method(p)
        c = 13.9 * s * s if s else None
        w_char = p["H_um"] if ("channel" in p["geometry"] or "cavity" in p["geometry"]) else p["H_um"] / 2
        width = w_char / s if s else None                       # 1 / |dθ/dx| in µm: the front width
        probe, spot, src = RES.get(p["paper"], ("", None, "not stated"))
        lim = bool(width and spot and not is_model and width < 3 * spot)
        dup = "same as" in p["series"] or "same curve" in p["series"]   # one sample plotted twice (10.1039_d0cp03358h Fig. 9c/9f, 10.1149_1.3301664 Fig. 2a/6a)
        if lim:
            reslim.append(f"{who(p['paper'])} Fig. {p['figure']}{p['panel']} {p['series']}")
        per.setdefault(p["paper"], []).append((c, p, is_model or dup, lim))
        rows.append([f'<span class="num">{n}</span>', f"{E(who(p['paper']))}, Fig. {p['figure']}{E(p['panel'])}", E(p["series"]), E(p["geometry"]), f"{p['H_um']:g}", E(group9(p)),
                     str(nb), f"{x50:.0f}" if x50 else "—", f"{s:.3g}" if s else "—", f"{c:.2g}" if c else "—", E(f"{probe}; {src}"),
                     f"{width:.3g}" if width else "—", f"{width / spot:.1f}" if (width and spot) else "—", "<b>yes</b> (c is a lower bound)" if lim else "no" if (width and spot) else "—",
                     ("model curve, not data; " if is_model else "") + ("duplicate of the sample above, not counted; " if dup else "") + E(p["quality"])])
    good = lambda pid, g=None: sorted(c for c, p, m, l in per.get(pid, []) if c and not m and not p["quality"].startswith("poor") and (g is None or group9(p) == g))
    med = lambda v: (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] * v[len(v) // 2]) ** 0.5) if v else None    # geometric middle for an even count

    def summary(pids):
        out, plot = [], []
        for pid in pids:
            vals = good(pid)
            rep = [r for r in REP if r["paper_id"] == pid and r["quantity"] != "none" and not r["quantity"].startswith("slope")]
            redo = (f"{med(vals):.2g}" + (f" (range {vals[0]:.2g} to {vals[-1]:.2g}, {len(vals)} series)" if len(vals) > 1 else " (1 series)")) if vals else "no usable front"
            out.append([f"{E(who(pid))}<span class='pid'>{pid}</span>", "<br>".join(E(f"{r['species']}: {r['value']}") for r in rep) or "none",
                        "<br>".join(E(r["quantity"]) for r in rep) or "—", "<br>".join(E(r["method"]) for r in rep) or "—", "<br>".join(E(r["model"]) for r in rep) or "—",
                        "<br>".join(E(r["data_kind"]) for r in rep) or "—", E(redo)])
            marks = [(c, "re", f"re-derived here, Fig. {p['figure']}{p['panel']} {p['series']}") for c, p, m, l in per.get(pid, []) if c and not m and not p["quality"].startswith("poor")]
            for r in rep:
                if "EA =" in r["value"] or ">>" in r["value"]:         # an activation energy or a bound, not a sticking value
                    continue
                txt = re.sub(r"\((\d+(?:\.\d+)?) \+- [\d.]+\)(e-?\d+)", r"\1\2", r["value"])
                txt = re.sub(r"\([^)]*\)", "", txt)
                txt = re.split(r"recombination|RC ", re.sub(r"Fig\. ?\d+\w*", "", txt))[0]
                for v in re.findall(r"(?<![\w.^-])(\d+(?:\.\d+)?(?:e-?\d+)?)(?: ?(?:x|×) ?10\^?(-?\d+))?", txt):
                    val = float(v[0]) * (10 ** int(v[1]) if v[1] else 1)
                    if 1e-9 < val <= 1:
                        marks.append((val, {"fit": "fit", "model input": "input", "literature": "lit"}.get(r["data_kind"], "fit"), f"{r['species']}: {r['value']} ({r['method']})"))
            plot.append((who(pid), marks))
        return out, plot
    sa, pa = summary(slope_ok)
    sb, pb = summary(model)
    # by limiting species: re-derived against the papers' fits, chosen inputs and quoted literature, kept apart
    G = [("TMA", Y), ("TMA", M), ("TMA", D09), ("Al2O3 (TMA/H2O), limiting species not stated", GAO), ("TiO2 (TiCl4/H2O), limiting species not stated", GAO), ("H2O", D10)]
    sp = {"TMA": "TMA", "H2O": "H2O"}
    grows, redo = [], {}
    for g, pid in G:
        v = good(pid, g); redo[(g, pid)] = v
        k = sp.get(g.split(" ")[0], "TiCl4" if g.startswith("TiO2") else "TMA")
        grows.append([E(g), E(who(pid)), (f"{med(v):.2g}" + (f" ({v[0]:.2g} to {v[-1]:.2g}, {len(v)} series)" if len(v) > 1 else " (1 series)")) if v else "—",
                      f"{FIT[(pid, k)]:g}" if (pid, k) in FIT else "—", f"{CHOSEN[(pid, k)]:g}" if (pid, k) in CHOSEN else "—"])
    grows.append(["for comparison", E(who(M)) + ", water-limited sample 14 (profile not read here)", "—", "3e-4", "—"])
    grows.append(["for comparison", E(who(Y)) + ", TiO2 from TiCl4 (no plateau, not re-derived)", "—", "0.1", "—"])
    tma = [med(redo[("TMA", p)]) for p in (Y, M, D09)]
    al = med(redo[(G[3])]); ti = redo[G[4]]; h2o = med(redo[G[5]])
    hs = {h: next(c for c, p, m, l in per[M] if c and f"H {h} nm" in p["series"]) for h in (100, 500, 2000)}
    wid = {h: (h / 1000) / math.sqrt(hs[h] / 13.9) for h in hs}
    d0 = [c for c, p, m, l in per[M] if c and "H 500 nm" in p["series"] and "500 cycles" in p["series"]]
    cards = [
        (Y, 6, "", [("structure", "PillarHall, gap 0.5 µm"), ("paper's value", "c = 0.0057 for TMA, fit of a diffusion-adsorption model (Table I)"), ("probe", "reflectometer, about 5 µm spot"), ("data kind", "measured points, fitted curve")]),
        (M, 9, "c, f", [("structure", "PillarHall, H 100, 500, 2000 nm"), ("paper's value", "c = 0.004 for TMA from the slope of the normalized profile (Table 2)"), ("probe", "reflectometer, 5–6 µm spot"), ("data kind", "measured")]),
        (D09, 5, "", [("structure", "macroscopic rectangular channel, aspect ratio 33, 50, 100"), ("paper's value", "s0 = 0.1, chosen for a simulation, no fit"), ("probe", "ellipsometer, spot not stated"), ("data kind", "measured")]),
        (D10, 2, "a", [("structure", "macroscopic rectangular channel, aspect ratio 22, 50"), ("paper's value", "s0 = 0.1 (TMA), 0.05 (water), chosen for simulations; the thermal profile is water-limited"), ("probe", "ellipsometer, spot not stated"), ("data kind", "measured")]),
        (GAO, 5, "a-b", [("structure", "lateral channel, gap 200 to 1000 nm"), ("paper's value", "none"), ("probe", "reflectometer, about 5 µm spot"), ("data kind", "measured")]),
        (CM, 5, "a", [("structure", "anodic alumina, 65 nm pores, entered from both faces"), ("paper's value", "S = 0.007 for DEZ, chosen for Monte Carlo runs"), ("probe", "EPMA, 3–5 µm resolution"), ("data kind", "measured")]),
        (KR, 8, "", [("structure", "cavity 4.5 µm high entered through one hole (radial)"), ("paper's value", "SC = 0.02 for TMA, Monte Carlo fit"), ("probe", "micro-spot ellipsometer, 10 µm spot"), ("data kind", "measured")]),
    ]
    onto = table(["Printed label or value", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["Location (µm); Distance; depth (mm); Aspect Ratio; x̃", code("distance") + ", " + code("dimensionless_distance{by=H}"), code("x_over_width") + " with H for slits and cavities, d/2 for holes and pores", "the choice of width per geometry (H, d/2, hydraulic diameter) is a rule, not a stored qualifier"],
        ["thickness, relative thickness, GPC, Zn signal", code("normalized_thickness{reference=plateau|entrance|maximum}"), code("normalize_thickness"), "“maximum” (the EPMA scans are scaled to their highest value) is not in the reference list"],
        ["slope of the front at one half (Table 1 of 10.1039_d0cp03358h)", code("front_slope{at=PD50, by=H}") + " (new)", "least-squares slope of θ against x̃ for 0.2 ≤ θ ≤ 0.8", "no entry for a front slope"],
        ["spot size, objective, EPMA resolution", code("probe_resolution{method}") + " (new)", "front width 1/|dθ/dx| over the spot", "no entry; without it a front narrower than the probe cannot be flagged"],
        ["c (lumped), s0, β0, SC, S, Γ", code("initial_sticking_coefficient") + " for all of them in v0", code("slope_to_sticking") + ": c = 13.9 · slope² (new, valid only for Kn ≫ 1 and a rectangular channel)", "a lumped c is not an initial s0: the ontology needs a quantity per kind, and method, model, limiting species and the fit, chosen-input or literature status as attributes of the value"],
    ])
    rl = "; ".join(reslim) if reslim else "none"
    return f"""
<section id="c9"><h2>Case 9. One method for every sticking value</h2>
<p class="q"><b>Question.</b> Applied to every usable measured profile, does one method (the slope method used by 10.1039_d0cp03358h) bring the sticking values of different papers closer than the values the papers report? Papers: {len(slope_ok)} where the method's geometry holds, {len(model)} that need a geometry model (shown apart).</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> One transform, many quantities</h3>{onto}
<h3><span class="step">After</span> Re-derived next to reported</h3>{ILL}
<h4>a. Rectangular channels in the free-molecular regime ({len(slope_ok)} papers): the slope method applies</h4>
<div class="plots one">{logdots(pa, "Re-derived (filled circles) and reported values (squares: fit, diamonds: chosen input, crosses: literature)")}</div>
{table(["Limiting species", "Paper", "Re-derived here: c = 13.9 · slope² (median)", "Reported, fit", "Reported, chosen for a simulation"], grows)}
<details><summary>The papers' reported values with quantity, method, model and data kind</summary>{table(["Paper", "Reported value", "Quantity (s or s0)", "Method", "Model", "data_kind", "Re-derived here"], sa)}</details>
<h4>b. Other geometries ({len(model)} papers): indicative only, the slope relation is not derived for them</h4>
<div class="plots one">{logdots(pb, "Holes, pores, radial cavity, forests and porous bodies: indicative re-derivation where a width exists")}</div>
{table(["Paper", "Reported value", "Quantity (s or s0)", "Method", "Model", "data_kind", "Re-derived here (indicative)"], sb)}
<h4>c. Every series, with the probe's stated resolution</h4>
<p class="note">Front width = 1/|dθ/dx|, the distance over which the fitted front falls from 1 to 0. A series is marked resolution-limited when that width is below three spots (the upper end of a stated range); its slope is then too shallow and its c a lower bound.</p>
<details><summary>All {len(ser)} series</summary>{table(["#", "Source", "Series", "Geometry", "H or d (µm)", "Limiting species", "Points in 0.2–0.8", "x̃ at one half", "Slope", "c", "Probe and resolution (stated)", "Front width (µm)", "Width in spots", "Resolution-limited", "Quality"], rows)}</details>
<p class="note"><b>Check of the eye reading.</b> For the 0.5 µm channel, 500 cycles, of 10.1039_d0cp03358h the points read here give c = {d0[0]:.1e}; the paper's own Table 1 slope (0.019) gives {13.9 * 0.019 ** 2:.1e}.</p>
<p class="take"><b>Takeaway.</b> Like with like, the two fitted TMA values in 0.5 µm channels are 0.004 (Yim 2020) and 0.0057 (Ylilammi 2018), a factor of 1.4; re-derived by one method from their own profiles they are {tma[1]:.1e} and {tma[0]:.1e}, a factor of {max(tma[:2]) / min(tma[:2]):.1f}, so for fitted values one method adds nothing. Grouped by limiting species, TMA spans {min(tma):.1e} to {max(tma):.1e} (a factor of {max(tma) / min(tma):.1f}) over three papers; the 0.1 reported for the third is a value chosen for a simulation, not a fit. With Gao 2015's Al2O3, whose limiting species is not stated, at {al:.1e}, the spread becomes a factor of {max(tma) / al:.0f}. For water the one water-limited profile (Dendooven 2010) gives {h2o:.1e} against the 3e-4 fitted by Yim 2020, a factor of {h2o / 3e-4:.0f}; Gao's TiO2 ({ti[0]:.1e} to {ti[-1]:.1e}) is about {0.1 / med(ti):.0f} times below Ylilammi's TiCl4 fit of 0.1. So one method removes a chosen value from the TMA comparison but leaves factors of {max(tma) / min(tma):.0f} to {max(max(tma) / al, h2o / 3e-4, 0.1 / med(ti)):.0f} between papers. In Yim 2020 the front is {wid[100]:.0f}, {wid[500]:.0f} and {wid[2000]:.0f} µm wide at H 0.1, 0.5 and 2 µm, {wid[100] / 6:.1f} to {wid[2000] / 5:.1f} spots of its 5–6 µm reflectometer spot: above three spots, so resolution alone does not explain the constant width. Resolution-limited: {E(rl)}.</p>
<p class="lim"><b>Limits.</b> Points read by eye; the slope comes from 2 to 15 points per front. The macroscopic channels of 10.1149_1.3072694 have no stated height (derived from the paper's aspect-ratio formula) and neither Dendooven paper states the ellipsometer spot, so their fronts cannot be tested for resolution. Channel narrowing by film growth also widens fronts. The re-derivations in part b use a width the slope relation was not derived for; the EPMA scans are scaled to their maximum, not to a plateau. Model curves read from three papers are listed but not used.</p>
</section>"""


# ----------------------------------------------------------------------------- case 10 (S2)

def loglog(w, h, xr, yr, xl, yl, title, xt, yt):
    """Log-log frame (same layout as cremers/build.py); returns the element list and the two scale functions."""
    L, R, Tp, B = 62, 20, 32, 46
    X = lambda v: L + (math.log10(v) - math.log10(xr[0])) / (math.log10(xr[1]) - math.log10(xr[0])) * (w - L - R)
    Y = lambda v: h - B - (math.log10(v) - math.log10(yr[0])) / (math.log10(yr[1]) - math.log10(yr[0])) * (h - Tp - B)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}"><text x="{L}" y="16" class="pt">{E(title)}</text>']
    for v in yt: e.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{L - 8}" y="{Y(v) + 4:.1f}" class="tk" text-anchor="end">{v:g}</text>')
    for v in xt: e.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{Tp}" y2="{h - B}" class="grid"/><text x="{X(v):.1f}" y="{h - B + 16}" class="tk" text-anchor="middle">{v:g}</text>')
    e.append(f'<text x="{(L + w - R) / 2}" y="{h - 8}" class="al" text-anchor="middle">{E(xl)}</text><text transform="translate(14 {(Tp + h - B) / 2}) rotate(-90)" class="al" text-anchor="middle">{E(yl)}</text>')
    return e, X, Y


def case10():
    with (HERE / "exposure_ear.csv").open(newline="", encoding="utf-8") as f:
        V = list(csv.DictReader(f))
    kB, u = 1.380649e-23, 1.6605e-27
    need = lambda a: 1 + 4.75 * a + 1.5 * a * a              # Gordon, ref. 62: Pt / (S sqrt(2 pi m k T)) needed to coat aspect ratio a
    pids = sorted({v["paper_id"] for v in V}, key=lambda p: QM[p]["year"])
    slot = {p: i % 8 + 1 for i, p in enumerate(pids)}
    e, X, Y = loglog(860, 480, (1e2, 1e10), (3, 2e4), "exposure of the limiting step / flat-surface exposure  (Pt / (S·√(2πmkT)))", "EAR (coated, or bound)", "Coated EAR against the exposure of the limiting step", [10 ** k for k in range(2, 11)], (3, 10, 30, 100, 300, 1000, 3000, 10000))
    pts = []
    for v in V:
        S = float(v["sat_density_per_nm2"]) * 1e18
        flat = S * math.sqrt(2 * math.pi * float(v["mass_amu"]) * u * kB * (float(v["T_C"]) + 273.15))
        x, a = float(v["exposure_pa_s"]) / flat, float(v["ear"])
        v["x"], v["R"] = x, x / need(a)
        pts.append(v)
        c = f"var(--s{slot[v['paper_id']]})"; xx, yy = X(x), Y(a)
        tip = f"{who(v['paper_id'])}: {v['species']}, {v['structure']}, EAR {a:g} ({v['reading']}), exposure {float(v['exposure_pa_s']):.3g} Pa s; ratio to the square law {v['R']:.2g}"
        if v["reading"] == "measured":
            e.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="5.5" fill="{c}" stroke="var(--surface)" stroke-width="1.5"><title>{E(tip)}</title></circle>')
        elif v["reading"] == "lower":
            e.append(f'<path d="M{xx - 6:.1f} {yy + 5:.1f} L{xx + 6:.1f} {yy + 5:.1f} L{xx:.1f} {yy - 7:.1f} Z" fill="var(--surface)" stroke="{c}" stroke-width="2"><title>{E(tip)}</title></path><line x1="{xx:.1f}" x2="{xx:.1f}" y1="{yy - 7:.1f}" y2="{yy - 18:.1f}" stroke="{c}" stroke-width="2"/>')
        else:
            e.append(f'<path d="M{xx - 6:.1f} {yy - 5:.1f} L{xx + 6:.1f} {yy - 5:.1f} L{xx:.1f} {yy + 7:.1f} Z" fill="var(--surface)" stroke="{c}" stroke-width="2"><title>{E(tip)}</title></path><line x1="{xx:.1f}" x2="{xx:.1f}" y1="{yy + 7:.1f}" y2="{yy + 18:.1f}" stroke="{c}" stroke-width="2"/>')
    ga = [a for a in (10 ** (k / 20) for k in range(0, 90)) if 1e2 <= need(a) <= 1e10 and 3 <= a <= 2e4]
    gl = " ".join(f"{'M' if i == 0 else 'L'}{X(need(a)):.1f} {Y(a):.1f}" for i, a in enumerate(ga))
    e.append(f'<path d="{gl}" fill="none" stroke="var(--text2)" stroke-width="1.5" stroke-dasharray="5 4"/><text x="{X(8e9):.1f}" y="{Y(400):.1f}" class="warn" text-anchor="end">dashed: square law of ref. 62 (Gordon), 1 + 19a/4 + 3a²/2</text>')
    e.append(f'<text x="{X(1.3e2):.1f}" y="{Y(14000):.1f}" class="warn">filled circles: measured depth · up triangles: fully coated (lower bound) · down triangles: not reached (upper bound)</text>')
    leg = table(["", "Paper", "Species, structure", "Records", "Saturation density used"], [
        [f'<svg class="sw" viewBox="0 0 38 14"><circle cx="19" cy="7" r="5" fill="var(--s{slot[p]})"/></svg>', f"{E(who(p))}<span class='pid'>{p}</span>",
         E("; ".join(sorted({f"{v['species']}, {v['structure']}" for v in pts if v["paper_id"] == p}))), str(sum(v["paper_id"] == p for v in pts)),
         E("; ".join(sorted({f"{v['sat_density_per_nm2']} per nm² ({v['sat_density_source']})" for v in pts if v["paper_id"] == p})))] for p in pids])
    rec = table(["Paper", "Where", "Species", "Structure", "EAR", "Reading", "Exposure (Pa s)", "Kind", "Exposure / need of the square law", "Note"], [
        [E(who(v["paper_id"])), E(v["where"]), E(v["species"]), E(v["structure"]), v["ear"], E(v["reading"]), f"{float(v['exposure_pa_s']):.3g}", E(v["exposure_kind"]), f"{v['R']:.2g}", E(v["depth_note"])] for v in pts])
    meas = sorted(v["R"] for v in pts if v["reading"] == "measured")
    within = sum(1 for r in meas if 0.67 <= r <= 1.5)
    contra = [v for v in pts if (v["reading"] == "lower" and v["R"] < 1) or (v["reading"] == "upper" and v["R"] > 1)]
    by = {p: sorted(v["R"] for v in pts if v["paper_id"] == p and v["reading"] == "measured") for p in pids}
    within3 = sum(1 for r in meas if 1 / 3 <= r <= 3)
    def spr(p):
        m = by[p]; lo = [v for v in pts if v["paper_id"] == p and v["reading"] == "lower"]; up = [v for v in pts if v["paper_id"] == p and v["reading"] == "upper"]
        out = (f"{m[0]:.2g}" if len(m) == 1 else f"{m[0]:.2g} to {m[-1]:.2g}") + f" ({len(m)} measured)" if m else "no measured depth"
        if lo: out += f", lower bounds {sum(v['R'] >= 1 for v in lo)} of {len(lo)} consistent"
        if up: out += f", upper bounds {sum(v['R'] <= 1 for v in up)} of {len(up)} consistent"
        return out
    spread = {p: spr(p) for p in pids}
    cards = [
        (D09, 5, "", [("exposure", "TMA about 0.3 Pa for 4 s (text); the authors set water higher so TMA limits"), ("reading", "AR 33 fully coated; half thickness inside AR 50 and 100")]),
        (CM, 5, "a", [("exposure", "DEZ 0.068 Torr for 1 to 30 s; pores entered from both faces"), ("reading", "half-thickness depth per exposure, by eye")]),
        (FB, 2, "", [("exposure", "Hf amide in Langmuir per cycle: 2, 4, 30 × 10³"), ("reading", "coated quarter, three quarters, full")]),
        (KIM, 7, "", [("exposure", "TMA about 0.01 Torr times injection time"), ("reading", "bottom over flat growth at aspect ratio 10")]),
        (SC, 5, "", [("exposure", "TMA 0.08 Pa for 2, 8, 30 s"), ("reading", "half-value depths drawn by the authors in a fibre-filled hole")]),
    ]
    onto = table(["In the papers", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["TMA 0.3 Pa, 4 s; 0.068 Torr; 2 × 10³ L; 17,000 Torr s; 6.8e19 cm⁻²", code("exposure{species, step=precursor|co-reactant|plasma}"), "partial pressure × time, or units to Pa s (1 L = 1.33e-4 Pa s)", "the step is not a qualifier in v0; nor is whether the value is measured, calculated, assumed or fitted, nor whether that step limits"],
        ["“fully coated”, “half thickness at”, “bottom not reached”", code("coated_aspect_ratio{basis=EAR, reading=lower|measured|upper}"), "EAR per structure class: hole L/d, two-sided pore (L/2)/d, slot L·p/(4A)", "the reading qualifier and the one- or two-sided entry (as in Case 8)"],
        ["growth per cycle, Hf per cycle, Kmax", code("saturation_density{species}") + " (new)", "from growth per cycle and film density when not stated", "no entry; Gordon's law needs it to compare species"],
        ["Pt / (S√(2πmkT))", code("normalized_exposure") + " (new)", "divide by the flat-surface exposure of that species at that temperature", "a derived quantity that makes TMA, DEZ, water and the Hf amide comparable"],
    ])
    return f"""
<section id="c10"><h2>Case 10. Coated EAR against the exposure of the limiting step</h2>
<p class="q"><b>Question.</b> When the exposure is that of the step that limits conformality, do holes, pores, slots, fibre plugs and particle compacts fall on Gordon's square law? Papers: {len(pids)} (those with <code>limiting_step_exposure = yes</code> in the matrix), {len(pts)} records.</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> Exposure of which step, and what the depth means</h3>{onto}
<h3><span class="step">After</span> One dimensionless exposure for every species</h3>{ILL}
<div class="plots one">{"".join(e)}</svg></div>{leg}
{table(["Paper", "Exposure over predicted need, per paper (measured depths; bounds consistent when a fully coated structure has a ratio of 1 or more, an uncoated one 1 or less)"], [[E(who(p)), E(spread[p])] for p in pids])}
<details><summary>All {len(pts)} records</summary>{rec}</details>
<p class="take"><b>Takeaway.</b> Of the {len(meas)} measured depths, {within} ({within / len(meas):.0%}) lie within a factor of 1.5 of Gordon's square law and {within3} ({within3 / len(meas):.0%}) within a factor of 3 (exposure over predicted need, {meas[0]:.2g} to {meas[-1]:.2g}). Per paper: {"; ".join(f"{who(p)} {spread[p]}" for p in pids)}. The lowest point, {min(by[SC]):.2g}, is the fibre plug's 2 s run, which its authors single out as reaching deeper than their simulation and attribute to a pressure build-up at the start of the pulse that a constant-pressure model leaves out. The water-limited slot of 10.1149_1.3301664 sits at {by[D10][0]:.0f} times the predicted need, but that ratio rests on an assumed saturation density for water (1.5 molecules per Al). {len(contra)} bounds disagree with the law: the TMA-coated membrane of {who(CM)} is fully coated at {next(v["R"] for v in contra if v["paper_id"] == CM):.2g} of the predicted need (the overestimate found in Case 8), and {who(KIM)}'s shortest injection does not reach the hole bottom at {next(v["R"] for v in contra if v["paper_id"] == KIM):.1f} times the need, where even the flat surface is not yet saturated.</p>
<p class="lim"><b>Limits.</b> Saturation densities are stated in four papers and assumed in the rest (named in the legend); a factor of two there moves a point by a factor of two. The EAR of the fibre plug and of the CNT forest are computed here (area to depth over four times the opening, and depth over the mean flight path) and are not those of Gordon's derivation. The 10.1063_1.2714685 records are plasma ALD with the TMA step limiting at short injection; its 0.2 s point lies where even the flat surface is not saturated. Depths at one half were read by eye; the alumina-pore depths are EPMA signals scaled to their maximum.</p>
</section>"""


# ----------------------------------------------------------------------------- case 11 (S3, S6)

def case11():
    with (HERE / "recombination.csv").open(newline="", encoding="utf-8") as f:
        RC = list(csv.DictReader(f))
    pl = [r for r in RC if r["use"] == "plotted"]
    mat = lambda r: r["surface"].split(" ")[0]
    slot = {"SiO2": 1, "TiO2": 2, "Al2O3": 3, "HfO2": 4, "IrOx": 5}
    fl = lambda v: float(v) if v not in ("", None) else None

    def mark(e, x, y, r, s):
        c = f"var(--s{slot[mat(r)]})"; atm = r["regime"].startswith("atmospheric")
        lo, hi = fl(r["r_lo"]), fl(r["r_hi"])
        tip = E(f"{who(r['paper_id'])}, {r['where']}: {mat(r)}, r {r['r'] or 'range'} ({r['r_lo'] or '?'} to {r['r_hi'] or '?'}), {r['T_C'] or 'T not stated'} °C, {float(r['pressure_Pa']):g} Pa, {r['regime']}; {r['data_kind']}, {r['reading']}")
        if lo and hi:
            e.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{s(lo):.1f}" y2="{s(hi):.1f}" stroke="{c}" stroke-width="{2 if fl(r["r"]) else 6}" opacity="{1 if fl(r["r"]) else 0.5}"><title>{tip}</title></line>')
        v = fl(r["r"])
        if v is None:
            return
        if not lo and hi and abs(hi - v) < 1e-12:      # upper limit
            e.append(f'<path d="M{x - 6:.1f} {s(v) - 5:.1f} L{x + 6:.1f} {s(v) - 5:.1f} L{x:.1f} {s(v) + 7:.1f} Z" fill="var(--surface)" stroke="{c}" stroke-width="2"><title>{tip}</title></path>')
        elif atm:
            e.append(f'<rect x="{x - 5:.1f}" y="{s(v) - 5:.1f}" width="10" height="10" fill="var(--surface)" stroke="{c}" stroke-width="2.5"><title>{tip}</title></rect>')
        else:
            e.append(f'<circle cx="{x:.1f}" cy="{s(v):.1f}" r="5.5" fill="{c}" stroke="var(--surface)" stroke-width="1.5"><title>{tip}</title></circle>')

    # r against substrate temperature
    w, h, L, Rr, Tp, B = 760, 400, 62, 20, 32, 46
    X = lambda t: L + (t - 80) / (260 - 80) * (w - L - Rr)
    Yl = lambda v: h - B - (math.log10(v) + 5.3) / (math.log10(0.2) + 5.3) * (h - Tp - B)
    e = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="r against temperature"><text x="{L}" y="16" class="pt">Recombination probability of O against substrate temperature</text>']
    for v in (1e-5, 1e-4, 1e-3, 1e-2, 1e-1):
        e.append(f'<line x1="{L}" x2="{w - Rr}" y1="{Yl(v):.1f}" y2="{Yl(v):.1f}" class="grid"/><text x="{L - 8}" y="{Yl(v) + 4:.1f}" class="tk" text-anchor="end">{v:g}</text>')
    for t in range(100, 261, 40):
        e.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{Tp}" y2="{h - B}" class="grid"/><text x="{X(t):.1f}" y="{h - B + 16}" class="tk" text-anchor="middle">{t}</text>')
    e.append(f'<text x="{(L + w - Rr) / 2}" y="{h - 8}" class="al" text-anchor="middle">substrate temperature (°C; real values where the paper separates them from the set point)</text><text transform="translate(14 {(Tp + h - B) / 2}) rotate(-90)" class="al" text-anchor="middle">r (log scale)</text>')
    off = {}
    for r in pl:
        if not r["T_C"] or (fl(r["pressure_Pa"]) or 0) not in (6.67, 100000.0):
            continue
        k = (r["T_C"], mat(r)); off[k] = off.get(k, -1) + 1
        mark(e, X(float(r["T_C"])) + 7 * off[k] + {"SiO2": 0, "TiO2": -6, "Al2O3": 10, "HfO2": 22, "IrOx": 0}[mat(r)], 0, r, Yl)
    e.append(f'<text x="{X(84):.1f}" y="{Yl(0.12):.1f}" class="warn">filled: 50 mTorr (6.7 Pa) · open squares: atmospheric pressure · bars: range or error · down triangle: upper limit</text>')
    p1 = "".join(e) + "</svg>"
    # r against pressure, with the Knudsen number of a 0.5 µm channel on top
    e, Xp, Yp = loglog(760, 400, (1, 3e5), (1e-5, 1e-2), "total pressure during the plasma step (Pa, log scale)", "r (log scale)", "Recombination probability of O against pressure", (1, 10, 100, 1000, 1e4, 1e5), (1e-5, 1e-4, 1e-3, 1e-2))
    for r in pl:
        if mat(r) in ("SiO2", "TiO2") and r["T_C"] in ("100", "180", "100.0", "180.0") and fl(r["r"]):
            mark(e, Xp(float(r["pressure_Pa"])) + (5 if mat(r) == "TiO2" else 0), 0, r, Yp)
    e.append(f'<line x1="{Xp(2e4):.1f}" x2="{Xp(2e4):.1f}" y1="34" y2="354" stroke="var(--text2)" stroke-dasharray="3 3"/><text x="{Xp(1.8e4):.1f}" y="48" class="warn" text-anchor="end">Kn of a 0.5 µm channel falls below 1 near here</text>')
    p2 = "".join(e) + "</svg>"
    # S6: does depth in channel heights keep the free-molecular scaling?
    low = {("SiO2", "100"): (119.4, 9.3e-5), ("TiO2", "100"): (189.6, 3.65e-5)}
    atm = {("SiO2", "100"): (25.0, 4e-4), ("TiO2", "100"): (63.1, 6e-5)}
    s6 = []
    for m in ("SiO2", "TiO2"):
        sl, rl = low[(m, "100")]; sa, ra = atm[(m, "100")]
        s6.append([m, f"{sl:.0f} (r {rl:.2g}, low-pressure relation)", f"{sa:.0f} (r {ra:.2g}, atmospheric relation)", f"{4 / (3 * sa * sa):.1e}", f"{4 / (3 * sa * sa) / rl:.0f}"])
    kn = table(["Paper", "Channel", "Pressure", "Mean free path (as stated or estimated)", "Kn", "Regime"], [
        [E(who(A21)), "PillarHall, H 0.5 µm", "1.6 to 17 Pa (12 to 130 mTorr)", "about 0.1 mm (stated)", "about 200", "free molecular"],
        [E(who(A9)), "PillarHall, H 0.5 µm", "6.7 Pa", "as above (same reactor)", "about 200", "free molecular"],
        [E(who(PP)), "PillarHall, H 0.5 µm", "1e5 Pa, 2% O2 in N2", "0.2 µm (stated O scattering length)", "0.4", "transition"],
        [E(who(J5)), "PillarHall, H 0.5 µm", "atmospheric, 1% O2", "as above (relation reused)", "about 0.4", "transition"],
        [E(who(W)), "macroscopic trench, 1 mm", "0.06 to 1 Pa", "7 to 100 mm (estimated)", "10 to 100", "free molecular (r held fixed in the fit, not plotted)"],
    ])
    cards = [
        (A21, 5, "", [("axes as printed", "temperature (A) and pressure (B) against r"), ("data kind", "fit: r from the slope of PD50/H against ln t, by the low-pressure relation")]),
        (A9, 3, "", [("axes as printed", "ln(Plasma time (s)) / PD50% / cavity height"), ("data kind", "fit, the relation printed on the plot")]),
        (PP, 3, "", [("axes as printed", "Ln(Plasma time (s)) / PD50% / cavity height"), ("data kind", "fit, by a relation for atmospheric pressure (constant 4.26)")]),
        (J5, 10, "b", [("axes as printed", "Depth (µm) / Thickness (nm), inset ln t / PD50% / h"), ("data kind", "fit, relation of the previous paper reused")]),
    ]
    onto = table(["In the papers", "Ontology id with qualifiers", "Transform", "Missing in the ontology"], [
        ["r, recombination probability, loss probability", code("recombination_probability{species=o_atom, surface=<material>}"), "none", "temperature, pressure and the kind of surface (growing film, ceramic) as conditions of the value"],
        ["table temperature 200 °C, real about 180 °C", code("deposition_temperature{kind=set_point|measured}"), "none", "the set-point and real-temperature distinction"],
        ["50 mTorr; atmospheric, 2% O2 in N2", code("process_pressure") + ", " + code("reactor_type"), "units to Pa", "a Knudsen number (mean free path over channel height) as a derived quantity"],
        ["r = (4/3)(Δln t / Δx̃)² and slope = 1/√(4.26 r)", "relation of the value, not a quantity", "slope of PD50/H against ln t to r", "the relation used, and the regime it is valid in, as attributes of the fitted value"],
    ])
    rows = table(["Paper", "Where", "Surface", "r", "Range or error", "T (°C)", "Pressure (Pa)", "Regime", "Kind", "Reading"], [
        [E(who(r["paper_id"])), E(r["where"]), E(r["surface"]), r["r"] or "—", f"{r['r_lo'] or '—'} to {r['r_hi'] or '—'}", r["T_C"] or "not stated", f"{float(r['pressure_Pa']):g}", E(r["regime"]), E(r["data_kind"]), E(r["reading"])] for r in pl])
    sio = sorted((float(r["T_C"]), float(r["r"])) for r in pl if mat(r) == "SiO2" and r["paper_id"] == A21 and float(r["pressure_Pa"]) == 6.67)
    sp = sorted((float(r["pressure_Pa"]), float(r["r"])) for r in RC if mat(r) == "SiO2" and r["paper_id"] == A21 and r["where"] == "Fig. 5B")   # all four pressures
    lit = [r for r in RC if r["use"].startswith("not plotted: literature")]
    papers = sorted({r["paper_id"] for r in pl})
    return f"""
<section id="c11"><h2>Case 11. Recombination against temperature and pressure, and where depth in channel heights stops scaling</h2>
<p class="q"><b>Question.</b> Across the plasma papers, how does the recombination probability of O on growing films change with substrate temperature and pressure (S3)? And does the free-molecular scaling of depth in channel heights still hold outside the Knudsen regime (S6)? Papers: {len(papers)} with values of their own; {len(lit)} literature values are listed in the CSV but not plotted.</p>
<h3><span class="step">Before</span> The crops as published</h3>{before(cards)}
<h3><span class="step">Ontology step</span> A value with its conditions and its relation</h3>{onto}
<h3><span class="step">After</span> One axis for temperature, one for pressure</h3>{ILL}
<div class="plots">{p1}{p2}</div>
<p class="note">{" · ".join(f'<span style="color:var(--s{v})">●</span> {k}' for k, v in slot.items())} (growing films). IrOx (atmospheric, no stated temperature) is in the table below, on neither plot.</p>
<details><summary>The {len(pl)} plotted values</summary>{rows}</details>
<h4>Does depth in channel heights keep its free-molecular scaling at atmospheric pressure?</h4>{kn}
{table(["Film, 100 °C", "Slope of PD50/H against ln t at 50 mTorr (r as reported)", "Slope at atmospheric pressure (r as reported)", "r from the atmospheric slope read with the low-pressure relation", "That r over the 50 mTorr r"], s6)}
<p class="take"><b>Takeaway.</b> In one reactor at 50 mTorr, r of O on growing SiO2 falls from {sio[0][1]:.1e} at {sio[0][0]:.0f} °C to {sio[-1][1]:.1e} at {sio[-1][0]:.0f} °C (a factor of {sio[0][1] / sio[-1][1]:.1f}). At about 180 °C it falls with pressure from {sp[0][1]:.1e} at {sp[0][0]:.1f} Pa to {sp[-1][1]:.1e} at {sp[-1][0]:.0f} Pa, a factor of {sp[0][1] / sp[-1][1]:.0f}; without the 1.6 Pa point, whose error bar spans a factor of ten, it falls from {sp[1][1]:.1e} at {sp[1][0]:.1f} Pa to {sp[-1][1]:.1e}, a factor of {sp[1][1] / sp[-1][1]:.1f}. TiO2 stays near 4e-5 up to 180 °C and drops below 1e-5 at 240 °C; Al2O3 and HfO2 are one to three orders higher. Read with one relation (the low-pressure one), the atmospheric slopes give r {s6[0][4]} times (SiO2) and {s6[1][4]} times (TiO2) the 50 mTorr values at the same 100 °C; the atmospheric papers' own relation brings this to {0.0004 / 9.3e-5:.1f} and {6e-5 / 3.65e-5:.1f} times. These data cannot separate a change of r from a change of transport regime: each regime has two papers, one relation, and no overlap in pressure.</p>
<p class="lim"><b>Limits.</b> {len(papers)} papers, two of them from one group and one reactor; the atmospheric papers share one relation, and one of them carries an erratum notice whose content is not in the ingested text. Fig. 5 values and error bars were read by eye. No paper measures the gas temperature, so mean free paths are as stated or estimated from the substrate temperature. The 50 mTorr and atmospheric comparisons are both at 100 °C but differ in O2 fraction, plasma source and flow. No thermal profile in the corpus is outside the Knudsen regime, so the S6 check rests on plasma data; in Case 10 the thermal depths from 65 nm pores to 0.3 mm slots, all at Kn well above 1, lie mostly within a factor of 3 of Gordon's law.</p>
</section>"""


# ----------------------------------------------------------------------------- page

CSS = """
:root{--surface:#fcfcfb;--panel:#f3f2ee;--text:#1f1f1c;--text2:#55544e;--line:#d9d7cf;--grid:#e8e6df;--accent:#184f95;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#7a5195;--s8:#8c6d31}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--grid:#2e2d2a;--accent:#9ec5f4;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#a37cc4;--s8:#b8935a}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#242422;--text:#f0efec;--text2:#c3c2b7;--line:#3a3935;--grid:#2e2d2a;--accent:#9ec5f4;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#a37cc4;--s8:#b8935a}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1500px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:21px;margin:48px 0 6px;padding-top:20px;border-top:2px solid var(--line)}
h3{font-size:16px;margin:26px 0 10px}h4{margin:0 0 6px;font-size:15px}.sub{color:var(--text2);margin:0 0 18px;max-width:80ch}p{max-width:95ch}
.step{display:inline-block;background:var(--accent);color:var(--surface);font-size:12px;font-weight:600;padding:2px 9px;border-radius:10px;margin-right:8px;vertical-align:1px}
.q{font-size:16px}.flow{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 0;color:var(--text2);font-size:13px}.flow span{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:3px 10px}
.crops{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}figure{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;min-width:0}
figcaption{font-size:13px;margin-bottom:8px}.pid{display:block;color:var(--text2);font-size:11px;font-family:ui-monospace,monospace;overflow-wrap:anywhere}
img{max-width:100%;height:auto;display:block;background:#fff;border-radius:4px;margin:0 auto 6px}
dl{margin:8px 0 0;font-size:12.5px;display:grid;grid-template-columns:auto 1fr;gap:2px 10px}dt{color:var(--text2)}dd{margin:0}
.tw{overflow-x:auto;margin:8px 0}table{border-collapse:collapse;font-size:13px;width:100%}th,td{text-align:left;vertical-align:top;padding:6px 10px;border-bottom:1px solid var(--line)}
th{color:var(--text2);font-weight:600;font-size:12px}code{font:12px ui-monospace,monospace;background:var(--panel);padding:1px 4px;border-radius:3px;overflow-wrap:anywhere}
.plots{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}.plots.one{grid-template-columns:minmax(0,820px)}
.plots svg{width:100%;height:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px}
.grid{stroke:var(--grid);stroke-width:1}.ax{stroke:var(--text2);stroke-width:1}.tk{fill:var(--text2);font-size:11px}.al{fill:var(--text2);font-size:12px}.pt{fill:var(--text);font-size:13px;font-weight:600}
.tag{fill:var(--text);font-size:11px;font-weight:600}.tagc{fill:var(--surface);stroke:var(--text2);stroke-width:1}.warn{fill:var(--text);font-size:11px;font-style:italic}.reg{fill:var(--text2);font-size:12px;font-weight:600}
.sw{width:38px;height:14px;display:block}.num{display:inline-block;min-width:20px;text-align:center;border:1px solid var(--text2);border-radius:10px;font-size:11px;font-weight:600}
.ill{display:inline-block;border:1px dashed var(--text2);border-radius:6px;padding:3px 10px;font-size:13px;font-weight:600;margin:0 0 10px}
.take{background:var(--panel);border-left:4px solid var(--accent);padding:10px 14px;border-radius:0 6px 6px 0}.lim,.note{color:var(--text2);font-size:13.5px}.note{color:var(--text)}
.card{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:16px;border:1px solid var(--line);border-radius:8px;padding:14px;margin:14px 0}.cardimg{display:grid;gap:10px;align-content:start}
.link{font-size:13.5px}@media (max-width:900px){.card{grid-template-columns:1fr}}details{margin:10px 0}summary{cursor:pointer;color:var(--text2)}
"""


def main() -> None:
    sel = selected_rows()
    papers = sorted({r["paper_id"] for r in sel})
    seltab = table(["Paper", "Figure", "Panel", "x id → y id", "Structure", "Used in"], [
        [f"{E(who(r['paper_id']))}<span class='pid'>{r['paper_id']}</span>", r["figure"], r["panel"], code(r["x_id"]) + " → " + code(r["y_id"]), E(r["structure"]),
         {Y: "case 1", M: "cases 1, 3", W: "case 1", A9: "cases 1, 2, 3", PP: "cases 1, 2", J5: "cases 1, 2", NC: "case 3", BJ: "case 3", D09: "case 1", GAO: "case 1", A21: "cases 1, 2", D10: "case 1",
          "10.1116_1.4892385": "not used: porous body, no channel height", "10.1016_j.surfcoat.2012.02.038": "not used: fibre-filled hole", "10.1116_1.4971196": "not used: cavity entered through a hole, radial geometry",
          "10.1021_cm0303080": "not used: X-ray signal across a membrane", "10.1063_1.4972120": "not used: fully coated, no front", "10.1016_j.apsusc.2009.02.055": "not used: four points", "10.1016_j.apsusc.2010.01.025": "not used: four or five points",
          "10.1149_1.2789802": "not used: one hole, seven values", "10.1063_1.2714685": "not used: model outline only"}.get(r["paper_id"], "not used")] for r in sel])
    ptab = table(["Case", "Source", "Series", "x as printed", "y as printed", "Points (x, y)"], [
        [p["case"], f"{E(who(p['paper']))}, Fig. {p['figure']}{p['panel']}", E(p["series"]), E(p["x_label_as_printed"]), E(p["y_label_as_printed"]), E("; ".join(f"{x:g}, {y:g}" for x, y in p["points"]))] for p in PTS])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PSED case studies</title><style>{CSS}</style></head><body><main>
<h1>Eleven case studies from the ingested papers</h1>
<p class="sub">Examples of what the pipeline is meant to deliver, made by hand. Cases 1 to 3 are built on thickness profiles from {len(papers)} papers; cases 4 to 6 come from the checked candidates N1 and N2, N3 and N5; case 7 follows single samples across figures and methods; case 8 reads the 2019 review's tables as data; cases 9 to 11 carry the part E candidates S1, S2, and S3 with S6, on the hand-read quantity matrix. Fifteen papers were added on 2026-10-13; Cases 1, 2 and 4 use them. Exploration only: every plotted point was read by eye from a published figure crop, and nothing here is extracted data. Each case runs in three steps.</p>
<div class="flow"><span>Before: the source crops as published</span><span>→ Ontology step: printed label to id, transform, gaps</span><span>→ After: the comparable view</span></div>
<h2>Selected profile panels</h2>
<p>Measured plot rows of the figure inventory whose x is a distance (plain or divided by a length) and whose y is a film thickness, a normalized thickness, a local growth per cycle or a coated aspect ratio: {len(sel)} rows in {len(papers)} papers.</p>{seltab}
{case1()}{case2()}{case3()}{case4()}{case5()}{case6()}{case7()}{case8()}{case9()}{case10()}{case11()}
<h2>Points read by eye</h2><p>The same content as <code>points.json</code>, as a table.</p><details><summary>Show the {sum(len(p['points']) for p in PTS)} points of {len(PTS)} series</summary>{ptab}</details>
</main></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {OUT.stat().st_size / 1e6:.2f} MB; selected rows {len(sel)} in {len(papers)} papers; series plotted {len(PTS)}")


if __name__ == "__main__":
    main()
