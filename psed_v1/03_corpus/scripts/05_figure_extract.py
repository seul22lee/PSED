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
    "series":[{{"label":"<series/material or ''>","points":[[x,y],[x,y],...]}}],
    "conditions":{{"<name>":<value_with_unit_as_string>}}   // conditions fixed in this panel,
                                                          // read from the caption/axes/legend
  }}
]}}
Rules: x.quantity in {COORDINATES}; y.quantity in {MEASURANDS} (pick the closest; if none
fits, use the axis label verbatim). Read every visible data point in order; if a curve is
dense, sample ~10-20 representative points. Use the numeric axis scales (mind log axes).
Do NOT invent panels or series that are not shown. conditions = things held fixed (e.g.
temperature, precursor, number of cycles) taken from the caption/legend, not guessed."""


def _fignum(s):
    """Parse the docling figure INDEX from a drill 'where' like 'F7a' / 'F7' / 'Fig 7'."""
    m = re.search(r"[Ff](?:ig(?:ure)?)?\.?\s*(\d+)", str(s))
    return m.group(1) if m else None


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
                                             "items": [], "sources": set()})
        g["items"].append(it)
        g["sources"].add(it.get("source") or "measured")
    for g in groups.values():
        g["source"] = "simulated" if g["sources"] == {"simulated"} else \
                       ("both" if len(g["sources"]) > 1 else "measured")

    from google.genai import types
    card = {k: scout.get(k) for k in ("materials", "precursors", "coreactants",
                                      "process_type", "temperature_window_C")}
    results, tok_in, tok_out = [], 0, 0
    for image, g in groups.items():
        png = downscaled_png(d / image)
        prompt = (f"{VISION_SCHEMA}\n\nPAPER PROCESS CARD: {json.dumps(card)}\n"
                  f"FIGURE CAPTION: {g['caption']}\n"
                  f"Panels of interest: {[it.get('where') + '=' + it.get('type','') for it in g['items']]}")
        r = client.models.generate_content(
            model=MODEL,
            contents=[types.Part.from_bytes(data=png, mime_type="image/png"), prompt],
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
        u = getattr(r, "usage_metadata", None)
        tok_in += getattr(u, "prompt_token_count", 0) or 0
        tok_out += getattr(u, "candidates_token_count", 0) or 0
        try:
            obj = json.loads(r.text)
        except Exception:
            obj = {"_parse_error": r.text[:200]}
        results.append({"figure": g["fig"], "image": image, "caption": g["caption"],
                        "source": g["source"], **obj})

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


def flatten_records(sd, scout, figresults):
    mats = scout.get("materials") or []
    recs = []
    for fr in figresults:
        realnum = _cap_fignum(fr.get("caption"))
        fig_label = f"Fig {realnum}" if realnum else f"Fig {fr['figure']}"   # caption number, fallback docling index
        for p in fr.get("panels", []):
            x, y = p.get("x", {}), p.get("y", {})
            for s in p.get("series", []):
                recs.append({
                    "doi": sd, "material": (s.get("label") or (mats[0] if mats else None)),
                    "measurand": {"quantity": y.get("quantity"), "unit": y.get("unit")},
                    "coordinate": x.get("quantity"), "coordinate_unit": x.get("unit"),
                    "points": s.get("points", []),
                    "controlled": p.get("conditions", {}),
                    "chemistry": {"precursors": scout.get("precursors"),
                                  "coreactants": scout.get("coreactants")},
                    "source": fr.get("source", "measured"),   # measured | simulated | both
                    "study_type": scout.get("study_type"),
                    "provenance": {"figure": fig_label, "fig_index": fr["figure"],
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
