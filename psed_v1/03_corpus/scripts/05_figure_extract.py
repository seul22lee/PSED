#!/usr/bin/env python3
"""
05_figure_extract.py — Stage 3b DEEP pass: read ONLY the scout-drilled `measured`
figures with a vision LLM (Gemini), using the caption for context, → role-separated
experiment records with digitized data points → KB-ready.

Token-efficient by design:
  · only figures the scout flagged as measured data (not all figures),
  · GROUP drill items by their underlying image → one vision call per multi-panel figure,
  · downscale image to ~1100 px (plots stay readable, image tiles/tokens stay low),
  · caption + process-card given as cheap TEXT context; the model only digitizes data,
  · compact ontology-constrained JSON output.

Output per paper: extracted/{sd}/figure_data.json (+ token accounting) and
records.json (flattened role-separated experiment records for the KB).
Run with the psed310 env python.
"""
import json, os, re, sys, io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
MODEL = "gemini-flash-latest"
MAX_PX = 1100


def _load_key():
    for line in (ROOT / "config" / ".env").read_text().splitlines():
        if line.startswith("GOOGLE_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_API_KEY")


MEASURANDS = ["growth_per_cycle", "film_thickness", "penetration_depth", "surface_coverage",
              "normalized_thickness", "density", "refractive_index", "resistivity",
              "impurity_content", "roughness", "saturated_coverage"]
COORDINATES = ["deposition_temperature", "pulse_time", "exposure", "cycle_number",
               "spatial_coordinate", "aspect_ratio", "purge_time", "partial_pressure"]

VISION_SCHEMA = f"""You are digitizing a DATA figure from an ALD paper. Read the plotted
data precisely. Return ONLY JSON:
{{"panels":[
  {{"panel":"a",
    "x":{{"quantity":"<coordinate>","unit":"<unit>","log":false}},
    "y":{{"quantity":"<measurand>","unit":"<unit>","log":false}},
    "series_axis":"<REQUIRED for any multi-curve panel: the NAME of the variable that
       distinguishes the curves. Read it from the caption, legend title, or — if the
       curve labels themselves carry a unit — from that unit. Examples: labels
       '10 cycles','20 cycles' -> series_axis 'number of cycles'; labels '5ms','45ms'
       -> 'exposure time'; labels '150°C','200°C' -> 'temperature'; a caption 'Effect of
       H2 flow ratio' with labels '0.2','0.5' -> 'H2 flow ratio'; substrate legend
       'Al2O3','Si' -> 'substrate'. Only '' when there is a single curve. NEVER leave it
       blank for a multi-curve panel — if unsure, infer the physical quantity the labels
       measure.>",
    "series":[{{"label":"<this curve's label verbatim, e.g. '0.20' or 'Al2O3' or 'Methanol'>",
       "points":[[x,y],[x,y],...]}}],
    "conditions":{{"<name>":<numeric_value_with_unit_as_string>}}   // NUMERIC process
      // conditions held fixed in this panel (e.g. temperature "150 °C", pressure,
      // dose/pulse time, number of cycles). ONLY quantities with a numeric value.
  }}
]}}
Rules: x.quantity in {COORDINATES}; y.quantity in {MEASURANDS} (pick the closest; if none
fits, use the axis label verbatim).
For each series, read approximately 50 points evenly spaced across the curve's full
x-range (mouth to tail). If the curve has fewer than ~50 visible markers, read every
marker. Space the ~50 points to capture the shape faithfully — put more of them on
steep/curved sections (the knee and the decay) and fewer on flat plateaus. Read the
ACTUAL axis values; do not invent. Preserve x-order. Do NOT summarize a curve with a
handful of points, and do NOT exceed ~60.
Use the numeric axis scales (mind log axes).
Return one entry for EVERY panel shown in the figure — if the figure has panels
(a),(b),(c),(d),(e),(f), return all of them, including panels that are rescaled or
normalized versions of another panel. Do NOT invent panels that aren't shown, and do
NOT omit shown panels. A 6-panel figure must return 6 panels.
conditions = NUMERIC process
parameters held fixed in this panel (temperature, pressure, dose/pulse time, cycle
count), from the caption/legend, not guessed. Do NOT put material, precursor,
coreactant, substrate, or process type in conditions — those are identified separately
and are NOT conditions.
series_axis = what separates the curves, from caption/legend. Report it even when the
labels look like materials (e.g. curves 'Al2O3'/'Si'/'SiO2' under a caption about
substrates → series_axis 'substrate'; curves 'Methanol'/'Ethanol' → 'coreactant').
Do NOT decide whether a label is the deposited material — just copy the label verbatim
and name the axis. Whether a label is the film material is determined downstream.
For any panel with more than one curve, series_axis MUST be a non-empty name. If the
curve labels include a unit (cycles, ms, °C, %), name the corresponding quantity as the
axis and keep the value in the label. Do not put the axis name into the labels."""


def _fignum(s):
    """Parse the docling figure INDEX from a drill 'where' like 'F7a' / 'F7' / 'Fig 7'."""
    m = re.search(r"[Ff](?:ig(?:ure)?)?\.?\s*(\d+)", str(s))
    return m.group(1) if m else None


def _panel_letter(s):
    """Panel letter from a drill tag: 'F7a' -> 'a'; 'F7' -> '' (figure-level).
    Lets each panel keep its OWN measured/simulated source instead of collapsing a
    mixed figure to 'both' and mislabelling its measured panel as model."""
    m = re.search(r"[Ff](?:ig(?:ure)?)?\.?\s*\d+\s*([a-hA-H])\b", str(s))
    return m.group(1).lower() if m else ""


def caption_fig_index(structure):
    """docling figure INDEX (as string) -> figure {index,image,caption}. The scout
    references figures by their [F#] index tag, so we map by index, not paper number."""
    return {str(f["index"]): f for f in structure["figures"] if f.get("image")}


def downscaled_png(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if max(im.size) > MAX_PX:
        r = MAX_PX / max(im.size)
        im = im.resize((int(im.size[0] * r), int(im.size[1] * r)))
    b = io.BytesIO(); im.save(b, format="PNG")
    return b.getvalue()


def extract_paper(sd, client):
    d = EXTRACTED / sd
    scout = json.loads((d / "scout.json").read_text())
    # Gate on DRILL ONLY, not go_deeper. An empty drill means there is nothing to read,
    # so vision is skipped (this is what stops hallucinated-drill spend on microscopy
    # papers, since those score go_deeper=False AND tend to drill nothing real).
    # go_deeper is NOT used: the scout sets it False on papers that do contain real data
    # plots (e.g. 10.1063_1.4867469 has XRD + C-V; 10.1016_j.sse.2022.108584 has 9
    # measured records), so gating on it silently drops genuine measured data.
    if not scout.get("drill"):
        print(f"[05 skip] {sd}: drill=0 — nothing to read (go_deeper={scout.get('go_deeper')})")
        return [], [], 0, 0
    struct = json.loads((d / "structure.json").read_text())
    fig_by_num = caption_fig_index(struct)

    # group ALL scout-DRILLED data figures (measured AND simulated) by their image.
    # We do NOT exclude simulated figures — model curves are valuable (they drive twin
    # validation); we just LABEL each figure's source so downstream never conflates
    # experimental data with model output.
    groups = {}   # image_path -> {"fig":num, "caption":..., "items":[...], "source":...}
    for it in scout.get("drill", []):
        num = _fignum(it.get("where", ""))
        fig = fig_by_num.get(num)
        if not fig or not fig.get("image"):
            continue
        g = groups.setdefault(fig["image"], {"fig": num, "caption": fig["caption"],
                                             "items": [], "sources": set(), "panel_source": {}})
        g["items"].append(it)
        g["sources"].add(it.get("source") or "measured")
        # Keep each panel's OWN source. A figure like Fig 3 mixes an ideal *simulated*
        # panel (a) with the *experimental* panel (b); collapsing them to "both" made 06
        # label the measured panel as model.
        _pl = _panel_letter(it.get("where", ""))
        if _pl:
            g["panel_source"][_pl] = it.get("source") or "measured"
        else:
            g["panel_source"]["_fig"] = it.get("source") or "measured"
    for g in groups.values():
        # figure-level summary kept for reporting only — NEVER used to stamp a panel
        g["source"] = "simulated" if g["sources"] == {"simulated"} else \
                       ("both" if len(g["sources"]) > 1 else "measured")

    from google.genai import types
    card = {k: scout.get(k) for k in ("materials", "precursors", "coreactants",
                                      "process_type", "temperature_window_C")}
    results, tok_in, tok_out = [], 0, 0
    for image, g in groups.items():
        png = downscaled_png(d / image)
        # The drill tag names a panel of INTEREST (e.g. 'F16a'); it must never leak into
        # the prompt as a restriction, or vision returns only that panel and the other
        # five are silently lost. Give the data types at FIGURE level and demand all panels.
        data_types = sorted({it.get("type", "") for it in g["items"] if it.get("type")})
        hint = ("This figure contains data of type(s): " + ", ".join(data_types) + ". "
                "The scout flagged specific panels as most relevant, but READ EVERY PANEL "
                "PRESENT in the figure (a, b, c, …), returning one entry per panel — "
                "including panels that are scaled/normalized versions of another. Do not "
                "restrict to the flagged panel.")
        prompt = (f"{VISION_SCHEMA}\n\nPAPER PROCESS CARD: {json.dumps(card)}\n"
                  f"FIGURE CAPTION: {g['caption']}\n{hint}")
        # Retry on BOTH failure modes, keeping the best response seen:
        #  - parse failure: a transient malformed reply otherwise drops the paper to 0
        #    records silently (observed on celc). Keep FULL raw text on final failure.
        #  - panel under-extraction: vision returning fewer panels than the caption
        #    declares silently loses whole datasets (observed on d0cp03358h Fig 9: 1/6).
        # Expect the DATA panels scout drilled, not every caption-declared panel: a
        # caption may declare (a),(b) where (a) is an SEM image. Scout lists all data
        # panels, so image/schematic panels are never expected and never burn retries.
        drilled_panels = {_panel_letter(it.get("where", "")) for it in g["items"]}
        drilled_panels.discard("")
        expected = len(drilled_panels) if drilled_panels else _caption_panel_count(g["caption"])
        obj, last_raw, best, best_n = None, None, None, -1
        for attempt in range(3):
            r = client.models.generate_content(
                model=MODEL,
                contents=[types.Part.from_bytes(data=png, mime_type="image/png"), prompt],
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
            u = getattr(r, "usage_metadata", None)
            tok_in += getattr(u, "prompt_token_count", 0) or 0
            tok_out += getattr(u, "candidates_token_count", 0) or 0
            last_raw = r.text
            try:
                cand = _loads_json(r.text)
            except Exception as e:
                print(f"    [parse retry {attempt+1}/3] {g['fig']}: {type(e).__name__} {str(e)[:60]}")
                continue
            got = len(cand.get("panels") or [])
            if got > best_n:
                best, best_n = cand, got
            if not expected or got >= expected:       # complete (or nothing to compare to)
                break
            if attempt < 2:
                print(f"    [panel retry {attempt+1}] fig {g['fig']}: {got}/{expected} panels")
        obj = best
        if obj is None:
            obj = {"_parse_error": last_raw}          # FULL raw, not truncated
        elif expected and best_n < expected:
            print(f"    [WARN] fig {g['fig']}: kept {best_n}/{expected} panels after 3 attempts")
        results.append({"figure": g["fig"], "image": image, "caption": g["caption"],
                        "source": g["source"], "panel_source": g["panel_source"], **obj})

    (d / "figure_data.json").write_text(json.dumps(
        {"doi": sd, "process_card": card, "figures": results,
         "_tokens": {"in": tok_in, "out": tok_out}}, indent=1))

    # flatten to role-separated experiment records (KB-ready)
    records = flatten_records(sd, scout, results)
    (d / "records.json").write_text(json.dumps(records, indent=1))
    return results, records, tok_in, tok_out


def _cap_fignum(caption):
    """The paper's REAL figure number, parsed from the caption text (e.g. 'FIG. 3',
    'Figure 10:'). This is the citable number — NOT docling's image-extraction index."""
    m = re.search(r"\b(?:fig(?:ure)?|scheme)\.?\s*0*([0-9]+)", (caption or "").lower())
    return m.group(1) if m else None


def _clean_panel(p):
    """Keep only a real panel letter (a/b/c…); drop drill-tag pollution."""
    p = str(p or "").strip()
    return p.lower() if re.fullmatch(r"[A-Za-z]", p) else ""


import re as _re


# Defense-in-depth backstop: a condition must have a NUMERIC value. The vision prompt is
# the real fix (it no longer offers 'precursor' as an example and excludes categorical
# fields); this should be a no-op when the prompt behaves. Categorical values are captured
# properly elsewhere — material via the material field, precursor/coreactant via chemistry.
def _clean_conditions(cond):
    if not isinstance(cond, dict):
        return {}
    return {k: v for k, v in cond.items()
            if k and _re.match(r"^\s*[-+]?\.?\d", str(v))}


# A COMPLETE number (optional unit). The unit class excludes '-', so '2-propanol' is a
# name, not a number — this is what makes numeric-vs-categorical decidable here, once.
_NUMU = _re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-zµμÅ°%/·^]*)\s*\Z")


def _caption_panel_count(caption):
    """How many panels the caption declares, e.g. '(a) … (b) … (f)' -> 6. Deterministic;
    used to detect under-extraction of multi-panel figures."""
    return len(set(_re.findall(r"\(([a-h])\)", str(caption).lower())))


def _loads_json(text):
    """Robust JSON parse: tolerate markdown fences / trailing prose that some
    models (e.g. gemini-flash-latest) emit even under response_mime_type=json.
    Same hardening as 04_extract.py — a transient malformed response must not
    silently zero a paper's figure data."""
    if text is None:
        raise ValueError("empty response")
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t); t = re.sub(r"\n?```\s*$", "", t)
    try:
        return json.loads(t)
    except Exception:
        i, depth = t.find("{"), 0            # extract the first balanced {...} block
        if i >= 0:
            for j in range(i, len(t)):
                depth += (t[j] == "{") - (t[j] == "}")
                if depth == 0:
                    return json.loads(t[i:j + 1])
        raise


def _strip_phase(s):
    """Strip phase/stack prefixes ('a-', 'c-', 'Mo/') without touching stoichiometry
    digits — 'c-WS2' -> 'WS2', never 'WS'. Bounded repeat resolves stacked prefixes
    ('Mo/c-MoS2' -> 'c-MoS2' -> 'MoS2')."""
    prev = None
    out = s.strip()
    for _ in range(4):                      # bounded: resolve stacked prefixes
        if out == prev:
            break
        prev = out
        out = _re.sub(r"^(a-|c-|amorphous |crystalline |[A-Za-z]{1,3}/)\s*", "", out).strip()
    return out


def _classify_label(label, mats):
    """Return (cls, matched). cls in {material, condition, empty}. When cls=='material',
    `matched` is the CANONICAL scout material it maps to (e.g. c-WS2 -> WS2), so the
    record can store the clean material and keep the phase separately.

    Anchored on scout.materials so real formulas that are merely substrates/barriers
    (Al2O3, Si, SiO2 in a Bi2Te3 paper) are NOT treated as the material."""
    if not label:
        return ("empty", None)
    lab = label.strip()
    base = _strip_phase(lab)
    base_nox = _re.sub(r"\+[xy]$", "", base)   # only a trailing '+x'/'+y' (non-stoich), NOT digits
    for m in (mats or []):
        mbase = _strip_phase(m)
        if lab in (m, mbase) or base in (m, mbase) or base_nox in (m, mbase):
            return ("material", m)          # canonical scout material
    return ("condition", None)


def flatten_records(sd, scout, figresults):
    mats = scout.get("materials") or []
    recs = []
    for fr in figresults:
        paper_fig = _cap_fignum(fr.get("caption"))          # citable paper number (from caption)
        docling_idx = fr.get("figure")                       # docling extraction index (from scout drill)
        # unresolved captions stay visibly flagged as an index, never shown as a paper number
        fig_label = f"Fig {paper_fig}" if paper_fig else f"Fig {docling_idx} (idx)"
        for p in fr.get("panels", []):
            x, y = p.get("x", {}), p.get("y", {})
            # each panel keeps its own measured/simulated source; figure-level only as fallback
            _pl = (p.get("panel") or "").strip().lower()
            _src = (fr.get("panel_source", {}).get(_pl)
                    or fr.get("panel_source", {}).get("_fig")
                    or "measured")
            # series_axis is only a NAME for the condition. scout.materials is the decider
            # of material-vs-condition, so a legend that looks like a formula but isn't this
            # paper's film (substrate Al2O3/Si, coreactant Methanol) stays a condition.
            axis = (p.get("series_axis") or "").strip()
            for s in p.get("series", []):
                lab = (s.get("label") or "").strip()
                _cls, _match = _classify_label(lab, mats)          # scout.materials anchor
                if _cls == "empty":                                # single-curve panel, no legend
                    series_kind = series_axis_out = None
                    series_value_num = series_unit = None
                    material = (mats[0] if mats else None)
                    phase = None
                elif _cls == "material":
                    series_kind, series_value_num, series_unit = "material", None, None
                    material = _match
                    phase = lab if lab != _match else None          # c-MoS2 vs MoS2
                    series_axis_out = None
                else:
                    material = (mats[0] if mats else None)
                    phase = None
                    m = _NUMU.fullmatch(lab)
                    if m:                                          # a real numeric sweep value
                        series_kind = "numeric_sweep"
                        series_value_num = float(m.group(1))
                        series_unit = m.group(2) or None
                    else:                                          # categorical (substrate, coreactant, ...)
                        series_kind = "categorical"
                        series_value_num = None
                        series_unit = None
                    series_axis_out = (axis or None)
                recs.append({
                    "doi": sd,
                    "material": material,
                    "material_raw": lab,
                    "phase": phase,
                    "series_axis": series_axis_out,     # "H2 flow ratio" / "substrate" / None
                    "series_value": lab,                # raw value/name of this curve
                    "series_kind": series_kind,         # numeric_sweep | categorical | material
                    "series_value_num": series_value_num,  # float, only when numeric_sweep
                    "series_unit": series_unit,            # unit, only when numeric_sweep
                    "measurand": {"quantity": y.get("quantity"), "unit": y.get("unit")},
                    "coordinate": x.get("quantity"), "coordinate_unit": x.get("unit"),
                    "points": s.get("points", []),
                    "controlled": _clean_conditions(p.get("conditions", {})),
                    "chemistry": {"precursors": scout.get("precursors"),
                                  "coreactants": scout.get("coreactants")},
                    "source": _src,                          # measured | simulated (never "both")
                    "study_type": scout.get("study_type"),
                    "provenance": {"figure": fig_label,
                                   "figure_number": paper_fig,        # paper's real figure number, or None
                                   "fig_docling_index": docling_idx,  # extraction index (scout drill tag)
                                   "panel": _clean_panel(p.get("panel")),
                                   "caption": fr["caption"][:200], "extractor": "vision-llm"},
                })
    return recs


def main(sds):
    from google import genai
    client = genai.Client(api_key=_load_key())
    TI = TO = 0
    for sd in sds:
        print(f"\n[figure-extract] {sd}")
        results, records, ti, to = extract_paper(sd, client)
        TI += ti; TO += to
        print(f"  vision calls: {len(results)}  tokens: in={ti} out={to}")
        for fr in results:
            for p in fr.get("panels", []):
                npts = sum(len(s.get("points", [])) for s in p.get("series", []))
                print(f"    Fig {fr['figure']}{p.get('panel','')}: "
                      f"{(p.get('y') or {}).get('quantity')} vs {(p.get('x') or {}).get('quantity')} "
                      f"| {len(p.get('series', []))} series, {npts} pts | cond={p.get('conditions')}")
        print(f"  → {len(records)} KB records")
    print(f"\n[figure-extract] total vision tokens: in={TI} out={TO} for {len(sds)} papers")


if __name__ == "__main__":
    main(sys.argv[1:])
