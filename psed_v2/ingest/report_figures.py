#!/usr/bin/env python3
"""ingest/reports/figures.html: the figure stage output for review by eye (reads final/<id>/figures.json, writes the report only).
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/report_figures.py                 every paper with a figures.json
    ... report_figures.py <paper_id> [...]                                                  a subset (same file)
    ... report_figures.py --panels <dir>                                                    also one PNG per figure (crop + replots side by side)
                                                                                           into <dir>, for a judgement without a browser

Per figure: the crop(s) on the left; on the right, for each plot or spectrum panel, the extracted series re-plotted with matplotlib on
the stated x_range / y_range and log settings with the printed labels and the legend; under it panel_type, content, conditions and
the flags. Verdicts of ingest/answers/figures.json, when present, are shown with each panel. Self-contained (images embedded), gitignored.
"""
import base64, html, io, json, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

HERE = Path(__file__).resolve().parent
FINAL = HERE / "final"
OUT = HERE / "reports" / "figures.html"
ANSWERS = HERE / "answers" / "figures.json"
MAXW = 700


def img_uri(path):
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.width > MAXW:
                im = im.resize((MAXW, max(1, round(im.height * MAXW / im.width))), Image.LANCZOS)
            b = io.BytesIO(); im.save(b, "JPEG", quality=85)
            return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception as e:
        print(f"image not embedded: {path}: {e!r}", file=sys.stderr)
        return None


def replot(panel, title=""):
    """The extracted series of one plot/spectrum panel re-plotted on the stated ranges: PNG bytes (None without series)."""
    series = [s for s in panel.get("series") or [] if s["points"]]
    fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=110)
    for pk in panel.get("peaks") or []:                                          # a spectrum: its peaks as vertical lines with their labels
        ax.axvline(pk["x"], color="#c33", lw=1)
        ax.text(pk["x"], 0.98, pk["label"][:18], rotation=90, va="top", ha="right", fontsize=6, transform=ax.get_xaxis_transform())
    for c in panel.get("cells") or []:                                           # a map's printed cells at their positions
        ax.text(c["x"], c["y"], str(c["value"])[:10], ha="center", va="center", fontsize=6, bbox=dict(boxstyle="round,pad=0.15", fc="#fff3c4", ec="#c9a227", lw=0.5))
    for s in series:
        xs, ys = zip(*s["points"])
        monotone = all(a < b for a, b in zip(xs, xs[1:]))                      # a scatter (x not increasing) is drawn as markers only
        discrete = len(xs) <= 40 or not monotone or panel["panel_type"] == "map"
        ax.plot(xs, ys, marker="o" if discrete else None, ms=3, lw=1 if monotone else 0, label=s["label"] or None)
    x, y = panel.get("x") or {}, panel.get("y") or {}
    if x.get("log"):
        ax.set_xscale("log")
    if y.get("log"):
        ax.set_yscale("log")
    if panel.get("x_range"):
        ax.set_xlim(*panel["x_range"])
    if panel.get("y_range"):
        ax.set_ylim(*panel["y_range"])
    ax.set_xlabel((x.get("label_raw") or "")[:60], fontsize=8)
    ax.set_ylabel((y.get("label_raw") or "")[:60], fontsize=8)
    ax.tick_params(labelsize=7)
    if any(s["label"] for s in series):
        ax.legend(fontsize=6, title=(panel.get("series_axis") or None), title_fontsize=6)
    ax.set_title(title, fontsize=8)
    fig.tight_layout()
    b = io.BytesIO(); fig.savefig(b, format="png"); plt.close(fig)
    return b.getvalue()


def png_uri(png):
    return "data:image/png;base64," + base64.b64encode(png).decode()


def verdicts():
    if not ANSWERS.exists():
        return {}
    d = json.loads(ANSWERS.read_text(encoding="utf-8"))
    return {(v["paper_id"], str(v["figure"]), v["panel"]): v for v in d.get("items", [])}


CSS = """body{font-family:system-ui,sans-serif;margin:12px;background:#fafafa;color:#222}h1{font-size:20px}h2{font-size:16px;margin-top:28px;border-top:2px solid #ccc;padding-top:8px}
.fig{display:flex;gap:16px;margin:14px 0;padding:10px;background:#fff;border:1px solid #ddd;border-radius:6px}.left{flex:0 0 720px}.right{flex:1;min-width:0}
.cap{font-size:12px;color:#444;margin:6px 0}.panel{display:flex;gap:10px;margin:6px 0;padding:6px;border:1px solid #eee;border-radius:4px;background:#fcfcfc}
.meta{font-size:12px}.meta b{color:#333}.flag{display:inline-block;background:#fde8c8;border:1px solid #e3a94d;border-radius:3px;padding:0 5px;margin:1px 2px;font-size:11px}
.verdict{display:inline-block;border-radius:3px;padding:0 6px;font-size:11px;background:#e2f3e2;border:1px solid #6a6}.verdict.bad{background:#f8dede;border-color:#c66}
.tok{color:#777;font-size:11px}code{font-size:11px;background:#f0f0f0;padding:0 3px}img{max-width:100%}summary{cursor:pointer;font-size:12px;color:#555}pre{font-size:10px;white-space:pre-wrap;max-height:300px;overflow:auto}"""


def figure_html(pid, f, V, panel_dir=None):
    crops = [img_uri(FINAL / pid / im) for im in f["images"]]
    L = ['<div class="fig"><div class="left">']
    for u, im in zip(crops, f["images"]):
        L.append(f'<img src="{u}" alt="{html.escape(im)}">' if u else f'<span>no image {html.escape(im)}</span>')
    L.append(f'<div class="cap"><b>Fig. {html.escape(str(f["number"]))}</b> (p. {f["page"]}) {html.escape(f["caption"])}</div>')
    L.append(f'<div class="tok">tokens in {f["tokens"]["in"]} out {f["tokens"]["out"]}; {len(f["panels"])} panels; flags: '
             + ("".join(f'<span class="flag" title="{html.escape(x["detail"])}">{x["flag"]}</span>' for x in f["flags"]) or "none") + "</div>")
    if f.get("error"):
        L.append(f'<div class="meta"><b>error</b> {html.escape(f["error"])}</div>')
    L.append("</div><div class=\"right\">")
    replots = []
    for p in f["panels"]:
        v = V.get((pid, str(f["number"]), p["panel"]))
        vh = (f'<span class="verdict{"" if v["verdict"] == "ok" else " bad"}">{html.escape(v["verdict"])}{": " + html.escape(v.get("note", "")) if v.get("note") else ""}</span>' if v else "")
        L.append('<div class="panel">')
        if p["panel_type"] in ("plot", "spectrum", "map") and (p.get("series") or p.get("peaks") or p.get("cells")):
            png = replot(p, f"panel {p['panel'] or '-'}")
            replots.append((p, png))
            L.append(f'<div style="flex:0 0 470px"><img src="{png_uri(png)}"></div>')
        x, y = p.get("x") or {}, p.get("y") or {}
        meta = [f'<b>panel {html.escape(p["panel"] or "-")}</b> · {p["panel_type"]} {vh}', html.escape(p.get("content") or "")]
        if p["panel_type"] in ("plot", "spectrum", "map"):
            meta.append(f'x: <code>{html.escape(str(x.get("label_raw")))}</code> unit <code>{html.escape(x.get("unit_raw") or "")}</code> range {p.get("x_range")}{" log" if x.get("log") else ""}'
                        f'{" normalized " + html.escape(str(x.get("normalization_expression"))) if x.get("is_normalized") else ""}')
            meta.append(f'y: <code>{html.escape(str(y.get("label_raw")))}</code> unit <code>{html.escape(y.get("unit_raw") or "")}</code> range {p.get("y_range")}{" log" if y.get("log") else ""}'
                        f'{" normalized " + html.escape(str(y.get("normalization_expression"))) if y.get("is_normalized") else ""}')
            if p.get("series"):
                meta.append("series (" + html.escape(p.get("series_axis") or "-") + "): " + ", ".join(f'{html.escape(s["label"] or "(unlabelled)")} [{len(s["points"])}]' for s in p["series"]))
            if p.get("cells"):
                meta.append(f"cells: {len(p['cells'])}: " + ", ".join(f'({c["x"]:g}, {c["y"]:g}) {html.escape(str(c["value"]))}' for c in p["cells"][:40]))
            if p.get("peaks"):
                meta.append("peaks: " + ", ".join(f'{pk["x"]:g} {html.escape(pk["label"])}' for pk in p["peaks"]))
            if p.get("conditions"):
                meta.append("conditions: " + html.escape(json.dumps(p["conditions"], ensure_ascii=False)))
            if p.get("dropped_points"):
                meta.append(f"{p['dropped_points']} malformed points dropped")
        L.append('<div class="meta">' + "<br>".join(meta) + "</div></div>")
    L.append(f'<details><summary>raw response</summary><pre>{html.escape((f.get("raw_response") or "")[:20000])}</pre></details>')
    L.append("</div></div>")
    if panel_dir is not None and replots:
        panel_png(pid, f, replots, panel_dir)
    return "\n".join(L)


def stack_row(ims):
    row = Image.new("RGB", (sum(i.width for i in ims) + 10 * (len(ims) - 1), max(i.height for i in ims)), "white")
    x = 0
    for i in ims:
        row.paste(i, (x, 0)); x += i.width + 10
    return row


def panel_png(pid, f, replots, out_dir):
    """One PNG per figure: the crop(s) above, the replots in a row below (for a judgement without a browser)."""
    crops = [Image.open(FINAL / pid / im).convert("RGB") for im in f["images"]]
    plots = [Image.open(io.BytesIO(png)).convert("RGB") for _, png in replots]
    if len(plots) > 3:                                                           # at most three replots per row
        rows_ = [plots[i:i + 3] for i in range(0, len(plots), 3)]
        plots = [stack_row(r) for r in rows_]
    W = max(max(c.width for c in crops), max(p.width for p in plots), 400)
    scale = min(1.0, 1400 / W)
    H = sum(c.height for c in crops) + 20 + sum(p.height for p in plots)
    canvas = Image.new("RGB", (W, H), "white")
    y = 0
    for c in crops:
        canvas.paste(c, (0, y)); y += c.height
    y += 20
    for p in plots:
        canvas.paste(p, (0, y)); y += p.height
    if scale < 1:
        canvas = canvas.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    canvas.save(Path(out_dir) / f"{pid}__fig{f['number']}.png")


def main(argv):
    panel_dir = None
    if "--panels" in argv:
        i = argv.index("--panels"); panel_dir = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    pids = argv or sorted(p.name for p in FINAL.iterdir() if (p / "figures.json").exists())
    V = verdicts()
    H = [f"<!doctype html><html><head><meta charset='utf-8'><title>Ingest figures</title><style>{CSS}</style></head><body>",
         f"<h1>Figure stage (VLM): {len(pids)} papers</h1><p class='meta'>Left the crop(s) sent, right the extracted series re-plotted on the printed ranges; verdicts from answers/figures.json.</p>"]
    for pid in pids:
        d = json.loads((FINAL / pid / "figures.json").read_text(encoding="utf-8"))
        t = d.get("totals", {})
        H.append(f"<h2 id='{html.escape(pid)}'>{html.escape(pid)}</h2><p class='meta'>model {html.escape(d['model'])}, prompt {d['prompt_sha256'][:12]}, run {d['run_at']}; "
                 f"{t.get('figures')} figures, panels {html.escape(json.dumps(t.get('panels_by_type')))}, {t.get('points')} points, tokens {html.escape(json.dumps(t.get('tokens')))}, flags {html.escape(json.dumps(t.get('flags')))}</p>")
        for f in d["figures"]:
            H.append(figure_html(pid, f, V, panel_dir))
    H.append("</body></html>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(H), encoding="utf-8")
    print(f"{OUT} written: {len(pids)} papers, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
