#!/usr/bin/env python3
"""Ingest stage "figures": every captioned figure of a paper read once by a vision model (VLM), the result kept in
final/<paper_id>/figures.json, checked by rules (flags F1-F6), reviewed on reports/figures.html (report_figures.py).

    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/figures.py --ids <paper_id> [...]   the named papers (skips manifest figures = ok)
    ... figures.py --all                                                                   every in-scope paper with final/ output, skipping ok rows
    ... figures.py --redo --ids <paper_id> [...]                                            overwrite
    ... figures.py --repeat --ids <paper_id> [...]                                          re-read 10 % of the plot/spectrum figures (at least 12,
                                                                                           fixed seed) -> figures_repeat.json; agreement printed
    ... figures.py --reflag --ids <paper_id> [...]                                          recompute the flags of existing figures.json by the current
                                                                                           rules (no model call; the panels are untouched)

Input per paper (never a PDF): final/<id>/structure.json captions with kind == "figure" and a non-empty images list (tables, schemes
and pictures without a caption are never sent); the crops final/<id>/figures/*; the paper title (corpus/manifest.csv) and the abstract
(structure.json). One call per caption; a caption owning several image files sends them all in that call, in order; each image
downscaled so its long side is at most MAX_PX (1100). Model and key come only from psed_v2/.env: PSED_VLM_MODEL (vendor:model) and
GOOGLE_API_KEY; the stage stops with a message when either is missing. Like Marker, one run and keep: corpus/manifest.csv column
`figures` (ok | failed | blank); --all skips ok rows; a failed row is resumed (the figures its figures.json already holds from the same prompt and
model are kept, the rest read); --redo overwrites. A paper over TOKEN_CAP tokens stops the run with a report.

Output final/<id>/figures.json: {paper_id, model, prompt_sha256, run_at, figures: [{number, page, caption, images, tokens{in,out},
panels[...], flags[...], raw_response}], totals{figures, panels_by_type, points, tokens}}. raw_response is kept verbatim for every call.
Panels: the v1 VISION_SCHEMA (panel, x/y with label_raw, unit_raw, log, is_normalized, normalization_expression,
normalization_denominator_symbol; series_axis; series[{label, points}]; conditions) plus panel_type (plot, spectrum, micrograph, photo,
schematic, map, table_image, other), x_range, y_range (as printed; null without axes) and content (one line). A plot carries series with
points (every marker of a discrete series, a continuous line sampled at <= 40 points); a spectrum is not sampled: peaks [{x, label}] for
the peaks the figure labels or marks, no series; a map whose cells carry printed values (numbers or category labels in a grid) returns
cells [{x, y, value}] with the value as printed, and may carry series with categorical labels; a colour-scale map returns no data. A plot or
spectrum drawn inside a schematic panel is not read (a known limit, ERRORS.md).

Flags, computed after the call without a model, per figure (a flag deletes nothing; it marks a figure for the review and the importer):
  F1 panel-count: the panel letters of the caption differ from the panels returned;
  F2 out-of-range: a point (a spectrum peak, a map cell) outside the panel's x_range or y_range (tolerance 2 % of the range);
  F3 duplicate-x: two points of one series at the same x (panel_type plot only);
  F4 unit-missing: unit_raw empty while label_raw holds "(...)" or "[...]";
  F5 unreadable: the response is not valid JSON or fails the schema (the figure keeps raw_response, no panels);
  F6 empty-plot: a plot panel with no series, or a series with fewer than 2 points (not a spectrum: it carries peaks, not series).

--repeat agreement: a series of the first run agrees when at least 80 % of its points have a point of the second run (same panel,
same label) within 2 % of both axis ranges; the share of agreeing series and the median point deviation (in range units) are printed
and stored in figures_repeat.json.

The reading part (prompt schema, the downscale, one call per figure, JSON parsing, panel flattening) is ported from psed_v1
pipeline/figures/figure_extract.py; nothing is imported from psed_v1 and no path into it is used.
"""
import csv, datetime, hashlib, io, json, os, random, re, statistics, sys, time, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINAL = HERE / "final"
MANIFEST = ROOT / "corpus" / "manifest.csv"
ENV = ROOT / ".env"
MAX_PX = 1100
TOKEN_CAP = 200_000
PANEL_TYPES = ("plot", "spectrum", "micrograph", "photo", "schematic", "map", "table_image", "other")
TRIES, BACKOFF = 5, 2.0
REPEAT_SHARE, REPEAT_MIN, REPEAT_SEED = 0.10, 12, 20261017

# ------------------------------------------------------------------------------------------------------------ prompt
AXIS = """{{"label_raw":"<the axis label EXACTLY as printed, including any expression and unit: 'x/H', 'Distance (µm)', 'GPC (Å/cycle)';
          transcribe symbols faithfully; null if the axis has no label>",
       "unit_raw":"<the unit EXACTLY as printed, '' if none is shown>",
       "log":false,
       "is_normalized":true|false,
       "normalization_expression":"<the ratio EXACTLY as printed if this axis is normalized or dimensionless: 'x/H', 't(x)/t(0)'; null otherwise>",
       "normalization_denominator_symbol":"<just the denominator symbol printed: 'H', 'L', 't(0)'; null otherwise>"}}"""

VISION_SCHEMA = f"""You are reading one captioned figure of an atomic layer deposition (ALD) paper. All the image(s) below belong to this
one figure. Return ONLY JSON of this form:
{{"panels":[
  {{"panel":"<the panel letter as printed, 'a', 'b', ...; '' when the figure has one unlettered panel>",
    "panel_type":"<one of plot, spectrum, micrograph, photo, schematic, map, table_image, other>",
    "content":"<one line of at most 20 words saying what the panel shows>",
    "x_range":[<min>,<max>] or null, "y_range":[<min>,<max>] or null,
    "x":{AXIS},
    "y":{AXIS},
    "series_axis":"<for a multi-curve panel: the NAME of the variable that distinguishes the curves, read from the caption, the legend
       title or the unit of the curve labels ('10 cycles','20 cycles' -> 'number of cycles'; '150°C','200°C' -> 'temperature';
       'Al2O3','Si' under a caption about substrates -> 'substrate'); '' when there is a single curve>",
    "series":[{{"label":"<this curve's label verbatim, '' when it has none>", "points":[[x,y],[x,y],...]}}],
    "peaks":[{{"x":<position on the x axis>, "label":"<the peak's printed label or assignment, '' when only marked>"}}],
    "cells":[{{"x":<x of the cell>, "y":<y of the cell>, "value":<the printed value: a number, or a string for a category label>}}],
    "conditions":{{"<name>":"<numeric value with unit as a string>"}}
  }}
]}}
Rules.
- panel_type: plot = a graph with numeric axes (data points or curves against x and y); spectrum = an intensity against wavenumber,
  energy, angle, m/z or wavelength; micrograph = SEM, TEM, AFM or optical microscope image; photo = a photograph; schematic = a
  drawing, flow chart or illustration; map = an elemental or thickness map or a spatial image with a colour scale; table_image = a
  table drawn as an image; other = anything else.
- x_range and y_range: the numeric extent of the axes AS PRINTED (the first and last tick labels, or the axis limits), in the
  axis units; a log axis gives its printed tick values (not exponents); null when the panel has no numeric axes.
- Points are read ONLY for panel_type plot (and map, below). A discrete series (markers, bars, isolated symbols): read EVERY
  marker exactly, at its actual axis values; a continuous line (no markers): sample it at no more than 40 points, with more points
  on steep or curved sections and fewer on plateaus, in x order. Ignore error bars. Mind log axes. Never invent points.
- A spectrum is NOT sampled: it returns its axes, x_range, y_range and "peaks", one entry per peak the figure labels or marks (a
  printed assignment, a dashed line, an arrow, a symbol), with its x position and the printed label; series stays empty.
- A map returns its axes and ranges. A map whose cells carry printed values (numbers or category labels in a grid, e.g.
  temperature x ratio) returns "cells", one entry per cell with its x, y and the value as printed (a number, or the category label
  as a string; a colour alone that the legend names is that category's label); it may also carry series with categorical labels and
  points. A colour-scale map without printed values returns no cells and no series.
- A panel of another type (micrograph, photo, schematic, table_image, other) returns panel_type and content only (and the panel
  letter): no axes, series, peaks or conditions. A plot or spectrum drawn inside a schematic panel is part of that schematic.
- Labels are mandatory for plots and spectra: label_raw is the printed axis text, transcribed, not interpreted ('x/H' stays 'x/H').
  normalization_denominator_symbol must be a symbol actually PRINTED on the axis or in the plot; an axis reading only 'Normalized
  thickness' has is_normalized true and both normalization fields null.
- Curves that differ only in sample, species, technique or provenance share the panel's axes; series_axis names what
  distinguishes them and must be a non-empty name for every multi-curve panel. Copy the curve labels verbatim; do not put the
  axis name into the labels.
- conditions = NUMERIC process parameters held fixed in the panel (temperature, pressure, pulse or dose time, cycle count), from
  the caption or legend, never guessed; no material, precursor, substrate or process name.
- Return one entry for EVERY panel the image(s) show, including panels that are rescaled or normalized versions of another; do not
  invent panels that are not shown and do not omit shown panels."""

PROMPT_SHA256 = hashlib.sha256(VISION_SCHEMA.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------------------------- env
def load_env():
    """psed_v2/.env into os.environ (values never printed); same reading as pilot/providers.load_env."""
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip() and not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def model_and_key():
    """(vendor, model, key) from PSED_VLM_MODEL and the vendor's key; a clear exit when either is missing."""
    load_env()
    m = os.environ.get("PSED_VLM_MODEL", "")
    if ":" not in m:
        sys.exit("figures.py: PSED_VLM_MODEL is not set in psed_v2/.env (expected vendor:model, e.g. google:gemini-2.5-flash)")
    vendor, name = m.split(":", 1)
    if vendor != "google":
        sys.exit(f"figures.py: the figure stage supports the google vendor only; PSED_VLM_MODEL names {vendor}")
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        sys.exit("figures.py: GOOGLE_API_KEY is not set in psed_v2/.env")
    return vendor, name, key


def client_for(vendor, key):
    from google import genai
    return genai.Client(api_key=key)


def retryable(e):
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    return code in (429, 503, 529) or type(e).__name__ in ("ResourceExhausted", "ServerError", "ServiceUnavailable") or "RESOURCE_EXHAUSTED" in str(e) \
        or "503" in str(e)[:40] or "429" in str(e)[:40]


def call(client, model, images_png, prompt):
    """One vision call: (text, tokens{in,out}); API errors of the rate-limit kind retried with backoff, at most TRIES in all."""
    from google.genai import types
    parts = [types.Part.from_bytes(data=b, mime_type="image/png") for b in images_png] + [prompt]
    for k in range(TRIES):
        try:
            r = client.models.generate_content(model=model, contents=parts,
                                               config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
            u = getattr(r, "usage_metadata", None)
            tok = {"in": getattr(u, "prompt_token_count", 0) or 0, "out": (getattr(u, "candidates_token_count", 0) or 0) + (getattr(u, "thoughts_token_count", 0) or 0)}
            return r.text or "", tok
        except Exception as e:
            if k == TRIES - 1 or not retryable(e):
                raise
            time.sleep(BACKOFF * 2 ** k)


# ------------------------------------------------------------------------------------------------------------ inputs
def manifest_rows():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader); fields = list(reader.fieldnames or [])
    if "figures" not in fields:
        fields.append("figures")
    for r in rows:
        r.setdefault("figures", "")
    return rows, fields


def write_manifest(rows, fields):
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    tmp.replace(MANIFEST)


def captioned_figures(pid):
    """The structure.json captions of kind figure with a caption text and a non-empty images list, in document order (an unnumbered
    picture without caption text is never sent)."""
    d = json.loads((FINAL / pid / "structure.json").read_text(encoding="utf-8"))
    figs = [c for c in d.get("captions", []) if c.get("kind") == "figure" and c.get("images") and (c.get("caption") or "").strip()]
    return figs, d.get("abstract") or ""


def downscaled_png(path):
    """The crop as PNG bytes with its long side at most MAX_PX (ported from v1)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if max(im.size) > MAX_PX:
        r = MAX_PX / max(im.size)
        im = im.resize((int(im.size[0] * r), int(im.size[1] * r)))
    b = io.BytesIO(); im.save(b, format="PNG")
    return b.getvalue()


def prompt_for(title, abstract, caption, n_images):
    many = f"\nThis figure comes as {n_images} image files, shown in order; read them as one figure." if n_images > 1 else ""
    return f"{VISION_SCHEMA}\n\nPAPER TITLE: {title}\nABSTRACT: {abstract}\nFIGURE CAPTION: {caption}{many}"


# ----------------------------------------------------------------------------------------------------------- parsing
def loads_json(text):
    """Tolerant JSON parse: fences and trailing prose stripped, else the first balanced {...} block (ported from v1)."""
    if text is None:
        raise ValueError("empty response")
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t); t = re.sub(r"\n?```\s*$", "", t)
    try:
        return json.loads(t)
    except Exception:
        i, depth = t.find("{"), 0
        if i >= 0:
            for j in range(i, len(t)):
                depth += (t[j] == "{") - (t[j] == "}")
                if depth == 0:
                    return json.loads(t[i:j + 1])
        raise


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def _rng(v):
    if isinstance(v, (list, tuple)) and len(v) == 2:
        a, b = _num(v[0]), _num(v[1])
        if a is not None and b is not None:
            return [a, b]
    return None


def _axis(a):
    a = a if isinstance(a, dict) else {}
    return {"label_raw": a.get("label_raw") if isinstance(a.get("label_raw"), str) else None,
            "unit_raw": a.get("unit_raw") if isinstance(a.get("unit_raw"), str) else "",
            "log": bool(a.get("log")), "is_normalized": bool(a.get("is_normalized")),
            "normalization_expression": a.get("normalization_expression") if isinstance(a.get("normalization_expression"), str) else None,
            "normalization_denominator_symbol": a.get("normalization_denominator_symbol") if isinstance(a.get("normalization_denominator_symbol"), str) else None}


def panels_of(obj):
    """The schema applied to a parsed response: the panels list flattened to the stored fields (ported from v1's flattening);
    ValueError when the response is no panels object. Points not a numeric pair are dropped (counted in the panel's dropped_points).
    A plot carries series; a spectrum carries peaks [{x, label}] and no series; a map may carry series with categorical labels."""
    if isinstance(obj, list):
        obj = {"panels": obj}
    if not isinstance(obj, dict) or not isinstance(obj.get("panels"), list):
        raise ValueError("no panels list")
    out = []
    for p in obj["panels"]:
        if not isinstance(p, dict):
            raise ValueError("a panel is not an object")
        t = str(p.get("panel_type") or "other").strip().lower()
        if t not in PANEL_TYPES:
            t = "other"
        q = {"panel": str(p.get("panel") or "").strip(), "panel_type": t, "content": str(p.get("content") or "").strip()}
        if t in ("plot", "spectrum", "map"):
            q.update(x_range=_rng(p.get("x_range")), y_range=_rng(p.get("y_range")), x=_axis(p.get("x")), y=_axis(p.get("y")),
                     series_axis=str(p.get("series_axis") or "").strip(), series=[], dropped_points=0,
                     conditions={str(k): str(v) for k, v in (p.get("conditions") or {}).items()} if isinstance(p.get("conditions"), dict) else {})
            if t == "map":
                q["cells"] = [{"x": _num(c.get("x")), "y": _num(c.get("y")), "value": (c.get("value") if isinstance(c.get("value"), (int, float, str)) else str(c.get("value")))}
                              for c in (p.get("cells") or []) if isinstance(c, dict) and _num(c.get("x")) is not None and _num(c.get("y")) is not None]
            if t == "spectrum":
                q["peaks"] = [{"x": _num(pk.get("x")), "label": str(pk.get("label") or "").strip()} for pk in (p.get("peaks") or []) if isinstance(pk, dict) and _num(pk.get("x")) is not None]
            for s in (p.get("series") or []) if t != "spectrum" else []:
                if not isinstance(s, dict):
                    continue
                pts = []
                for xy in s.get("points") or []:
                    if isinstance(xy, (list, tuple)) and len(xy) == 2 and _num(xy[0]) is not None and _num(xy[1]) is not None:
                        pts.append([_num(xy[0]), _num(xy[1])])
                    else:
                        q["dropped_points"] += 1
                q["series"].append({"label": str(s.get("label") or "").strip(), "points": pts})
        out.append(q)
    return out


# ------------------------------------------------------------------------------------------------------------- flags
CAP_PANEL = re.compile(r"(?:(?<=[\s,;:.])|^)(?:\(([a-pA-P])\)|([a-hA-H])\))(?=[\s,;:.–\-)]|$)")   # '(x)' any letter a-p; a bare 'x)' only a-h
CAP_RANGE = re.compile(r"\(?([a-pA-P])\)?\s*[–-]\s*\(?([a-pA-P])\)(?=[\s,;:.–\-)]|$)")


def caption_panels(caption):
    """The panel letters a caption names: '(a)', 'a)', '(A)' and the ranges '(a)–(c)', '(a–c)', as sorted lower-case letters; a
    bracketed letter may be any of a-p, a bare 'x)' only a-h (a symbol such as 'p)' in running text is not a panel)."""
    seen = []
    text = caption or ""
    for m in CAP_RANGE.finditer(text):
        a, b = m.group(1).lower(), m.group(2).lower()
        if a < b:
            for c in range(ord(a), ord(b) + 1):
                if chr(c) not in seen:
                    seen.append(chr(c))
    for m in CAP_PANEL.finditer(text):
        c = (m.group(1) or m.group(2)).lower()
        if c not in seen:
            seen.append(c)
    return sorted(seen)


def panel_key(p):
    m = re.match(r"^\(?\s*([A-Za-z])\s*\)?\s*(?:[-–—.:,)]|\(|$|\s)", p or "")
    return m.group(1).lower() if m else ""


def flags_of(caption, panels, unreadable=False):
    """F1-F6 for one figure, each a dict(flag, detail)."""
    fl = []
    if unreadable:
        fl.append({"flag": "F5", "detail": "response not valid JSON or failing the schema"})
        return fl
    cap = caption_panels(caption)
    got = [panel_key(p["panel"]) for p in panels]
    got_set = {g for g in got if g}
    if cap and set(cap) != got_set or not cap and len(panels) > 1 and got_set:
        fl.append({"flag": "F1", "detail": f"caption names {','.join(cap) or 'no letters'}; panels returned {','.join(got) or 'none'}"})
    for p in panels:
        if p["panel_type"] not in ("plot", "spectrum", "map"):
            continue
        tag = f"panel {p['panel'] or '-'}"
        xr, yr = p.get("x_range"), p.get("y_range")
        if p["panel_type"] == "plot" and (not p["series"] or any(len(s["points"]) < 2 for s in p["series"])):
            fl.append({"flag": "F6", "detail": f"{tag}: {'no series' if not p['series'] else 'a series with fewer than 2 points'}"})
        n_out = sum(1 for pk in p.get("peaks") or [] if xr and not within(pk["x"], xr))
        n_out += sum(1 for c in p.get("cells") or [] if xr and not within(c["x"], xr) or yr and not within(c["y"], yr))
        for s in p["series"]:
            for x, y in s["points"]:
                if xr and not within(x, xr) or yr and not within(y, yr):
                    n_out += 1
            if p["panel_type"] == "plot":
                xs = [x for x, _ in s["points"]]
                if len(set(xs)) < len(xs):
                    fl.append({"flag": "F3", "detail": f"{tag}, series '{s['label']}': duplicate x"})
        if n_out:
            fl.append({"flag": "F2", "detail": f"{tag}: {n_out} points outside the printed ranges"})
        for ax in ("x", "y"):
            a = p[ax]
            if not a["unit_raw"] and a["label_raw"] and re.search(r"\(.+\)|\[.+\]", a["label_raw"]):
                fl.append({"flag": "F4", "detail": f"{tag}, {ax}: unit_raw empty for label '{a['label_raw']}'"})
    return fl


def within(v, r, tol=0.02):
    lo, hi = min(r), max(r)
    pad = tol * (hi - lo) if hi > lo else tol * abs(hi or 1)
    return lo - pad <= v <= hi + pad


# ------------------------------------------------------------------------------------------------------------- run
def read_figure(client, model, pid, title, abstract, cap):
    """One captioned figure read once: the stored figure record."""
    pngs = [downscaled_png(FINAL / pid / img) for img in cap["images"]]
    prompt = prompt_for(title, abstract, cap["caption"], len(pngs))
    raw, tok = call(client, model, pngs, prompt)                                # an API error propagates: the paper fails, nothing is F5
    panels, unreadable, err = [], False, ""
    try:
        panels = panels_of(loads_json(raw))
    except Exception as e:
        unreadable, err = True, f"{type(e).__name__}: {str(e)[:200]}"
    rec = {"number": cap.get("number"), "page": cap.get("page"), "caption": cap["caption"], "images": list(cap["images"]), "tokens": tok,
           "panels": panels, "flags": flags_of(cap["caption"], panels, unreadable), "raw_response": raw}
    if err:
        rec["error"] = err
    return rec


def totals_of(figs):
    by = {t: 0 for t in PANEL_TYPES}
    pts = peaks = cells = 0
    for f in figs:
        for p in f["panels"]:
            by[p["panel_type"]] += 1
            pts += sum(len(s["points"]) for s in p.get("series") or [])
            peaks += len(p.get("peaks") or [])
            cells += len(p.get("cells") or [])
    tok = {"in": sum(f["tokens"]["in"] for f in figs), "out": sum(f["tokens"]["out"] for f in figs)}
    return {"figures": len(figs), "panels_by_type": {k: v for k, v in by.items() if v}, "points": pts, "peaks": peaks, "cells": cells, "tokens": tok, "flags": flag_counts(figs)}


def flag_counts(figs):
    c = {}
    for f in figs:
        for fl in f["flags"]:
            c[fl["flag"]] = c.get(fl["flag"], 0) + 1
    return dict(sorted(c.items()))


def write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def run_paper(client, model, pid, title, out_name="figures.json", only=None, resume=False):
    """Every captioned figure of pid read once; figures.json written after each figure (a crash keeps what was read; resume=True
    keeps the figures an interrupted run of the same prompt and model already read and reads the rest). Stops the run (SystemExit)
    when the paper passes TOKEN_CAP tokens."""
    caps, abstract = captioned_figures(pid)
    if only is not None:
        caps = [c for c in caps if str(c.get("number")) in only]
    figs, done = [], {}
    out = FINAL / pid / out_name
    if resume and out.exists():                                                  # a run stopped by a quota continues: figures already read, same prompt and model, are kept
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("prompt_sha256") == PROMPT_SHA256 and old.get("model") == model:
            done = {(str(f["number"]), f["page"]): f for f in old["figures"] if not f.get("error")}
    rec = {"paper_id": pid, "model": model, "prompt_sha256": PROMPT_SHA256, "run_at": datetime.datetime.now().isoformat(timespec="seconds"), "figures": figs}
    for c in caps:
        f = done.get((str(c.get("number")), c.get("page"))) or read_figure(client, model, pid, title, abstract, c)
        figs.append(f)
        rec["totals"] = totals_of(figs)
        write_json(FINAL / pid / out_name, rec)
        tok = rec["totals"]["tokens"]
        print(f"  fig {f['number']}: {len(f['panels'])} panels, {sum(len(s['points']) for p in f['panels'] for s in p.get('series') or [])} points, "
              f"tokens in {f['tokens']['in']} out {f['tokens']['out']}, flags {','.join(x['flag'] for x in f['flags']) or '-'}", flush=True)
        if tok["in"] + tok["out"] > TOKEN_CAP:
            sys.exit(f"figures.py: {pid} exceeds {TOKEN_CAP:,} tokens ({tok['in'] + tok['out']:,}) after figure {f['number']}; stopped")
    rec["totals"] = totals_of(figs)
    write_json(FINAL / pid / out_name, rec)
    return rec


# ---------------------------------------------------------------------------------------------------------- repeat
def repeat(client, model, pids, titles):
    """10 % of the plot/spectrum figures of pids (at least REPEAT_MIN, fixed seed) read a second time into figures_repeat.json;
    agreement per series and the median point deviation printed and stored."""
    pool = []
    for pid in pids:
        p = FINAL / pid / "figures.json"
        if not p.exists():
            print(f"[repeat] {pid}: no figures.json, skipped"); continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for f in d["figures"]:
            if any(q["panel_type"] in ("plot", "spectrum", "map") for q in f["panels"]):
                pool.append((pid, str(f["number"])))
    n = max(REPEAT_MIN, round(REPEAT_SHARE * len(pool)))
    chosen = sorted(random.Random(REPEAT_SEED).sample(pool, min(n, len(pool))))
    print(f"[repeat] {len(chosen)} of {len(pool)} plot/spectrum figures chosen (seed {REPEAT_SEED})")
    agree, total, devs = 0, 0, []
    for pid in sorted({p for p, _ in chosen}):
        nums = {num for p, num in chosen if p == pid}
        first = {str(f["number"]): f for f in json.loads((FINAL / pid / "figures.json").read_text(encoding="utf-8"))["figures"]}
        print(f"[repeat] {pid}: figures {', '.join(sorted(nums, key=lambda s: (len(s), s)))}")
        rec = run_paper(client, model, pid, titles[pid], "figures_repeat.json", only=nums)
        comp = []
        for f2 in rec["figures"]:
            f1 = first[str(f2["number"])]
            a, t, dv, rows = compare(f1, f2)
            agree += a; total += t; devs += dv
            comp.append({"number": f2["number"], "series": t, "agreeing": a, "rows": rows})
        rec["comparison"] = comp
        write_json(FINAL / pid / "figures_repeat.json", rec)
    med = statistics.median(devs) if devs else None
    print(f"[repeat] series agreeing: {agree} of {total} ({100 * agree / total:.0f} %); median point deviation {med:.4f} of the axis range" if total else "[repeat] nothing to compare")
    return {"figures": len(chosen), "pool": len(pool), "series": total, "agreeing": agree, "share": round(agree / total, 4) if total else None, "median_deviation": med}


def compare(f1, f2, tol=0.02):
    """Series of f1 (plot/spectrum panels) against f2 by panel key and label: (agreeing, total, deviations, rows)."""
    def key(p):
        return panel_key(p["panel"]) or p["panel"]
    p2 = {key(p): p for p in f2["panels"] if p["panel_type"] in ("plot", "spectrum", "map")}
    agree, total, devs, rows = 0, 0, [], []
    for p in f1["panels"]:
        if p["panel_type"] not in ("plot", "spectrum", "map"):
            continue
        q = p2.get(key(p))
        xr = p.get("x_range") or (q or {}).get("x_range"); yr = p.get("y_range") or (q or {}).get("y_range")
        if p["panel_type"] == "map" and p.get("cells"):                          # a map's cells are one series matched on x and y with the same value
            c1 = p["cells"]; c2 = (q or {}).get("cells") or []
            total += 1
            sx = (max(xr) - min(xr)) if xr and max(xr) > min(xr) else (max(abs(c["x"]) for c in c1) or 1.0)
            sy = (max(yr) - min(yr)) if yr and max(yr) > min(yr) else (max(abs(c["y"]) for c in c1) or 1.0)
            hit = 0
            for c in c1:
                d = min((max(abs(c["x"] - e["x"]) / sx, abs(c["y"] - e["y"]) / sy) for e in c2 if str(e["value"]).strip().lower() == str(c["value"]).strip().lower()), default=1.0)
                devs.append(min(d, 1.0)); hit += d <= tol
            ok = hit >= 0.8 * len(c1); agree += ok
            rows.append({"panel": p["panel"], "label": "cells", "agree": ok, "matched": hit, "points": len(c1), "points_second": len(c2)})
        if p["panel_type"] == "spectrum":                                        # a spectrum's peak list is one series: peaks matched on x alone
            pk1 = [[pk["x"], 0.0] for pk in p.get("peaks") or []]; pk2 = [[pk["x"], 0.0] for pk in (q or {}).get("peaks") or []]
            if pk1:
                total += 1
                sx = (max(xr) - min(xr)) if xr and max(xr) > min(xr) else (max(abs(x) for x, _ in pk1) or 1.0)
                hit = 0
                for x, _ in pk1:
                    d = min(abs(x - x2) / sx for x2, _ in pk2) if pk2 else 1.0
                    devs.append(min(d, 1.0)); hit += d <= tol
                ok = hit >= 0.8 * len(pk1); agree += ok
                rows.append({"panel": p["panel"], "label": "peaks", "agree": ok, "matched": hit, "points": len(pk1), "points_second": len(pk2)})
            continue
        for s in p["series"]:
            total += 1
            s2 = next((t for t in (q or {}).get("series", []) if t["label"].strip().lower() == s["label"].strip().lower()), None) if q else None
            if s2 is None or not s["points"]:
                rows.append({"panel": p["panel"], "label": s["label"], "agree": False, "reason": "no matching series in the second run"}); continue
            sx = (max(xr) - min(xr)) if xr and max(xr) > min(xr) else (max(abs(x) for x, _ in s["points"]) or 1.0)
            sy = (max(yr) - min(yr)) if yr and max(yr) > min(yr) else (max(abs(y) for _, y in s["points"]) or 1.0)
            hit = 0
            for x, y in s["points"]:
                d = min(max(abs(x - x2) / sx, abs(y - y2) / sy) for x2, y2 in s2["points"]) if s2["points"] else float("inf")
                devs.append(d if d != float("inf") else 1.0)
                hit += d <= tol
            ok = hit >= 0.8 * len(s["points"])
            agree += ok
            rows.append({"panel": p["panel"], "label": s["label"], "agree": ok, "matched": hit, "points": len(s["points"]), "points_second": len(s2["points"])})
    return agree, total, devs, rows


# ------------------------------------------------------------------------------------------------------------ main
def reflag(pids):
    """The flags of every figure of the existing figures.json recomputed by the current rules; nothing else changes."""
    for pid in pids:
        p = FINAL / pid / "figures.json"
        if not p.exists():
            print(f"[reflag] {pid}: no figures.json, skipped"); continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for f in d["figures"]:
            f["flags"] = flags_of(f["caption"], f["panels"], unreadable=bool(f.get("error")))
        d["totals"] = totals_of(d["figures"])
        write_json(p, d)
        print(f"[reflag] {pid}: flags {d['totals']['flags']}")


def main(argv):
    redo = "--redo" in argv; rep = "--repeat" in argv; allp = "--all" in argv
    if "--reflag" in argv:
        ids = [i for i in argv[argv.index("--ids") + 1:] if not i.startswith("--")] if "--ids" in argv else []
        return reflag(ids or sorted(p.name for p in FINAL.iterdir() if (p / "figures.json").exists()))
    ids = argv[argv.index("--ids") + 1:] if "--ids" in argv else []
    ids = [i for i in ids if not i.startswith("--")]
    if not (ids or allp):
        sys.exit(__doc__)
    rows, fields = manifest_rows()
    by_id = {r["paper_id"]: r for r in rows if r["paper_id"]}
    titles = {r["paper_id"]: r.get("title", "") for r in rows}
    if allp:
        ids = [r["paper_id"] for r in rows if r.get("in_scope") == "yes" and (FINAL / r["paper_id"] / "structure.json").exists()]
    unknown = [i for i in ids if i not in by_id or not (FINAL / i / "structure.json").exists()]
    if unknown:
        sys.exit(f"figures.py: not in the manifest or without final/ output: {unknown}")
    vendor, model, key = model_and_key()
    client = client_for(vendor, key)
    if rep:
        return repeat(client, model, ids, titles)
    grand = {"in": 0, "out": 0}
    for pid in ids:
        r = by_id[pid]
        if r.get("figures") == "ok" and not redo:
            print(f"[figures] {pid}: already ok, skipped (use --redo to overwrite)"); continue
        print(f"[figures] {pid} ({model}) ...", flush=True)
        try:
            rec = run_paper(client, model, pid, titles[pid], resume=not redo)
            r["figures"] = "ok"
            t = rec["totals"]
            grand["in"] += t["tokens"]["in"]; grand["out"] += t["tokens"]["out"]
            print(f"  {t['figures']} figures, panels {t['panels_by_type']}, {t['points']} points, tokens in {t['tokens']['in']:,} out {t['tokens']['out']:,}, flags {t['flags']}")
        except SystemExit:
            r["figures"] = "failed"; write_manifest(rows, fields); raise
        except Exception:
            traceback.print_exc(); r["figures"] = "failed"
        write_manifest(rows, fields)
    print(f"[figures] total tokens in {grand['in']:,} out {grand['out']:,} for {len(ids)} papers")


if __name__ == "__main__":
    main(sys.argv[1:])
