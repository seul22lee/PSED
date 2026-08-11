#!/usr/bin/env python3
"""
04_extract.py — Stage 3 SCOUT pass: abstract + conclusion + figure/table captions → a
role-separated process card + a decision about which figures/sections to drill.

The token-efficient entry point (user's design): read only the cheap parts first
(abstract, conclusion, captions ≈ 1–2k tokens), let one ontology-constrained LLM call
decide (a) the chemistry + process window, (b) exactly which figures/tables hold
extractable data of which type, and (c) whether a deeper pass is warranted. Deep
digitization/extraction (Stage 3b) runs ONLY on what the scout flags.

Output per paper: extracted/{safe_doi}/scout.json  (+ usage tokens for accounting).
Needs google-genai and GOOGLE_API_KEY (environment, or resources/config/corpus/.env).
"""
import paths as P
import json, os, re, sys, time
from pathlib import Path
from pipeline.figures import inventory as _inventory

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = P.PAPERS                 # papers/<id>/extracted/
ONTO = json.loads((P.ONTOLOGY_JSON).read_text())

# --- load the Gemini key from the environment or resources/config (never hardcoded) ---
def _load_key():
    envf = P.RESOURCES / "config" / "corpus" / ".env"
    for line in envf.read_text().splitlines():
        if line.startswith("GOOGLE_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_API_KEY")

MODEL = "gemini-flash-latest"

# --- ontology controlled vocabulary (kept compact to save tokens) ---
MATERIALS = sorted({m["id"] for m in ONTO["individuals"]["materials"]})
MEASURANDS = ["growth_per_cycle", "film_thickness", "penetration_depth", "surface_coverage",
              "normalized_thickness", "density", "refractive_index", "resistivity",
              "impurity_content", "roughness"]
DATA_TYPES = ["gpc_vs_temperature", "gpc_vs_dose_saturation", "gpc_vs_cycles",
              "conformality_or_penetration_profile", "film_property_vs_condition",
              "xrd_or_spectrum", "other"]

SCHEMA = """Return ONLY a JSON object with this exact shape:
{
 "is_ald_process_paper": true|false,
 "study_type": "experimental"|"modeling"|"both"|"review",  // does the paper report its
                               // OWN measurements (experimental), only simulations
                               // (modeling), both, or is it a review?
 "materials": [ids],           // ALD film material(s), e.g. ["BaO","BaTiO3"]
 "precursors": [names],        // metal precursor(s)
 "coreactants": [names],       // e.g. "H2O","O3","O2 plasma"
 "process_type": "thermal"|"plasma"|"unknown",
 "temperature_window_C": [min,max] | null,   // if a growth/ALD window is stated
 "gpc_nm": number | null,      // saturated growth-per-cycle if stated
 "data": {                     // which DATA figures/tables exist and where
   "<data_type>": {"present": true, "where": ["F6","F13","F16"]} , ...
   // "where" is a LIST — include EVERY figure/panel that shows this data_type.
   // If three separate figures show saturation profiles, list all three tags.
 },                            // data_type in: %(dtypes)s
 "drill": [                    // one entry per data-bearing figure/panel
   {"where":"F7a","type":"<data_type>","measurand":"<measurand>",
    "source":"measured"|"simulated","why":"one phrase"}
   // "where" = figure [F#] tag + panel letter when panelled (F7a). Emit a SEPARATE
   // drill item for EVERY figure and EVERY data panel — do NOT collapse multiple
   // figures of the same data_type into one. If Fig 3, Fig 7, Fig 9 all show
   // measured saturation profiles, all three (with their data panels) get items.
   // Multi-panel: F9a,F9b,F9c,… one per data panel; skip SEM/schematic panels.
 ],
 "go_deeper": true|false       // is a methods+figure deep pass worth it?
}

CRITICAL COVERAGE RULE — never drop a data plot:
If a figure/panel clearly contains plotted DATA (points, curves, bars with numeric
axes), it MUST be drilled. Do NOT skip a data plot for ANY of these reasons:
  - "another figure of the same type is already listed" — WRONG: each data plot may
    carry values the others do not, so each must be drilled separately. This is a
    COVERAGE rule, not a claim about experiment identity: two figures may show the
    same sample and one figure may hold several process conditions. Whether curves
    belong to the same physical run is decided downstream from paper-global
    evidence, never here.
  - "it looks like a representative/duplicate" — WRONG: scaled/normalized/as-measured
    versions of the same measurement are all separate data panels; drill each.
  - "the caption is a classification/terminology figure" — if it ALSO shows real
    experimental data (e.g. "the experimental scaled saturation profile"), drill it.
You are not choosing the "best" or "representative" data figure — you are inventorying
EVERY data plot. Completeness across same-type figures, but ONLY for actual plots.

Rules: only include a data_type in "data" if a caption/text clearly shows it. Do NOT
invent. Prefer material ids from this list when they match: %(mats)s . measurand in:
%(meas)s .
DRILL A PANEL ONLY IF IT PLOTS DATA — i.e. it has numeric axes with points, curves,
or bars you could digitize into (x,y) values. The following are NEVER data panels,
even when the figure is about a measurement: SEM / TEM / STEM / AFM images and
micrographs, optical/photograph images, EDS/elemental maps, schematics, illustrations,
flow charts, logos. If a figure is entirely such images, it has NO drill items.
Do NOT hallucinate a data_type onto a microscopy/schematic figure. When a figure
MIXES an image panel and a plot panel (e.g. (a) SEM, (b) intensity plot), drill ONLY
the plot panel(s).
KEEP (do not weaken): if MULTIPLE separate figures each plot data of the same type,
list every one — never collapse same-type figures to a single representative. That
rule stays; this change only stops drilling non-plot panels. Listing them all is
about COVERAGE of results, not about how many physical experiments the paper ran.
For each drill item set source=simulated when the caption says simulated/calculated/
modeled/computed/predicted, else measured; if the whole paper is modeling, most/all
figures are simulated.
List EVERY figure that shows a given data_type, not just one, and drill each. A
caption saying "as-measured … profiles" or "experimental … profile" is measured
data — drill it even if another figure of the same type already exists.

FIGURE TAGS ARE IMAGE CROPS, NOT PRINTED FIGURES. Each [F#] is one image crop the
parser produced. The printed figure number is given in parentheses as context only —
ALWAYS write the [F#] tag in "where", never the printed number. Two consequences:
  - A printed figure may be split across SEVERAL crops. Those crops are marked "ONE
    CROP … shows only PART of what the caption describes". For such a crop the caption
    describes the WHOLE printed figure, so panels it names may live in a DIFFERENT
    crop. Drill such a crop at FIGURE level ([F16], no panel letter) and never assert
    which lettered panels it contains — you cannot know that from the caption.
  - Several crops may share one caption. Drill each crop that plausibly holds data;
    do not assume they duplicate each other, and do not collapse them into one item.
Only attach a panel letter (F7a) when the crop is NOT marked as a split crop and the
caption clearly enumerates panels belonging to that single image.

YOUR ROLE IS COVERAGE AND RELEVANCE, NOT EXPERIMENT IDENTITY. Do not decide, imply
or encode how many physical experiments a paper contains. In particular:
  - several figures may show the SAME sample, run or deposition;
  - one figure may contain SEVERAL distinct process conditions;
  - one physical case may appear across several figures;
  - measured, calculated, fitted, model, simulation, characterization and derived
    curves are different KINDS of result and must never be conflated.
Classify what a panel shows (quantitative experimental plot, characterization plot,
spatial/temporal profile, process sweep, simulation/model plot, table of quantitative
results) and set `source` accordingly. Physical experiment identity is resolved
downstream, from the whole paper.
""" % {"dtypes": DATA_TYPES, "mats": MATERIALS[:40], "meas": MEASURANDS}


def section_text(md, names, limit=1800):
    """Grab the body under any heading whose title matches one of `names`."""
    lines = md.splitlines()
    grab, buf = False, []
    for ln in lines:
        h = re.match(r"^#{1,4}\s+(.+)$", ln)
        if h:
            title = h.group(1).lower()
            grab = any(n in title for n in names)
            continue
        if grab:
            buf.append(ln)
        if sum(len(x) for x in buf) > limit:
            break
    return re.sub(r"\s+", " ", " ".join(buf)).strip()[:limit]


def _ws(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


_META = re.compile(r"cite this|received |accepted |^doi:|www\.|e-?mail|@|published on|"
                   r"licensed|©|issn|copyright|electronic supplementary|these authors", re.I)
# institution/affiliation words → NOT an author-name line
_INST = re.compile(r"department|universit|laborator|institut|college|school of|corporation|"
                   r"research alliance|showcasing|\.edu|\.com|technolog", re.I)
_NAME = re.compile(r"[A-Z][a-z]+(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]+")
_SUPER = re.compile(r"[‡†§*]")


def _is_author_line(ln):
    """An author list: several 'First Last' names joined by and/&/commas, short, with
    superscript affiliation markers — and NOT an institution/affiliation line."""
    if not (12 < len(ln) < 500):
        return False
    if _INST.search(ln) or _META.search(ln):
        return False
    if " and " not in ln and "&" not in ln and ln.count(",") < 2:
        return False
    names = len(_NAME.findall(ln))
    return names >= 2 and (bool(_SUPER.search(ln)) or names >= 3)


def abstract_of(md, limit=2200):
    # 1) an explicit "Abstract" heading/section (Elsevier/AIP style)
    ab = section_text(md, ["abstract"], limit)
    if len(ab) > 200:
        return ab
    lines = [l.strip() for l in md.splitlines()
             if l.strip() and l.strip() != "<!-- image -->"]
    # 2) after the AUTHOR LIST: among all author lines, take the one whose following
    #    prose paragraph is LONGEST (the real abstract, not a graphical-abstract blurb)
    best = ""
    for i, ln in enumerate(lines[:70]):
        if _is_author_line(ln):
            for nx in lines[i + 1:i + 6]:
                if len(nx) > 300 and not _META.search(nx) and not _INST.search(nx):
                    if len(nx) > len(best):
                        best = nx
                    break
    if len(best) > 300:
        return _ws(best)[:limit]
    # 3) fallback: longest early prose paragraph that isn't metadata/affiliation,
    #    preferring abstract-like phrasing
    cand = [l for l in lines[:45] if len(l) > 300 and not _META.search(l) and not _INST.search(l)]
    long = [c for c in cand if len(c) > 700] or cand    # prefer a real (long) abstract
    for c in long:
        if re.search(r"we report|we show|here we|in this (work|study|paper)|"
                     r"growth per cycle|self-limit", c, re.I):
            return _ws(c)[:limit]
    return _ws(max(long, key=len))[:limit] if long else _ws(" ".join(lines[:8]))[:limit]


def build_scout_input(sd):
    """Abstract + conclusion + the FIGURE INVENTORY (not a filtered caption list).

    This used to read `struct["figures"] if f["caption"]`, which deleted every crop
    Docling had failed to caption — 57% of all crops corpus-wide — before any decision
    was made about it. Genuine data plots were lost that way. The inventory stage
    (pipeline/figures/inventory.py) recovers captions from document.md and sibling
    crops and gives every crop an explicit disposition, so what reaches the scout is
    "everything with caption evidence", not "everything docling happened to bind".
    """
    d = P.extracted_dir(sd)
    md = (d / "document.md").read_text()
    struct = json.loads((d / "structure.json").read_text())
    abstract = abstract_of(md)
    conclusion = section_text(md, ["conclusion", "summary", "concluding"])
    inv = _inventory.load(sd)
    # Reference each crop by its MACHINE identity [F<docling_index>] — the routing id.
    # The printed figure number is shown only as human context; it is never the tag,
    # because one printed figure may be split across several crops.
    caps = []
    for c in inv["candidates"]:
        if not _inventory.is_offerable(c):
            continue
        cap = _inventory.caption_for(c)
        pf = c.get("printed_figure")
        note = f"printed Figure {pf}" if pf else "printed number unknown"
        sibs = c.get("siblings") or []
        if sibs:
            note += (f"; ONE CROP of that printed figure, which docling split across "
                     f"{len(sibs) + 1} crops — this crop shows only PART of what the "
                     f"caption describes")
        caps.append(f"[F{c['docling_index']}] ({note}) {cap}")
    caps += [f"[T{t['index']}] {t['caption']}" for t in struct["tables"] if t["caption"]]
    return abstract, conclusion, caps


def _loads_json(text):
    """Robust JSON parse: tolerate markdown fences / trailing prose that some
    models (e.g. gemini-flash-latest) emit even under response_mime_type=json."""
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


def _scout_call(client, model, prompt, budgets=(12288, 20000, 32000)):
    """max_output_tokens caps THINKING + OUTPUT combined on gemini-flash. Figure-heavy
    papers spend ~3,900 on thinking, so a 4096 budget left ~160 for JSON -> truncated
    mid-string -> parse failure -> an EMPTY scout that downstream reads as 'no data'.
    Start high, raise on truncation, and NEVER return a silent empty."""
    from google.genai import types
    last_raw, last_finish, last_tok = "", None, {}
    for i, budget in enumerate(budgets):
        r = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                               max_output_tokens=budget))
        last_finish = getattr(r.candidates[0], "finish_reason", None) if r.candidates else None
        last_raw = r.text or ""
        usage = getattr(r, "usage_metadata", None)
        last_tok = {"in": getattr(usage, "prompt_token_count", None),
                    "out": getattr(usage, "candidates_token_count", None),
                    "thoughts": getattr(usage, "thoughts_token_count", None),
                    "budget": budget} if usage else {"budget": budget}
        try:
            return _loads_json(last_raw), last_tok
        except Exception:
            print(f"    [scout retry {i+1}/{len(budgets)}] finish={last_finish} "
                  f"budget={budget} parse-fail, raising budget")
    # exhausted: do NOT return an empty scout that reads as 'no data'
    raise RuntimeError(f"SCOUT FAILED after {len(budgets)} budgets "
                       f"(finish={last_finish}); raw kept for diagnosis:\n{last_raw[:500]}")


def _reconcile_dispositions(sd, obj):
    """Close the loop: every crop the inventory OFFERED becomes either DRILL or
    SKIP_WITH_REASON once the scout has ruled. After this, no PictureItem in the
    paper is left without an explicit, final disposition."""
    inv = _inventory.load(sd)
    drilled = {}
    for it in obj.get("drill") or []:
        m = re.search(r"[Ff](?:ig(?:ure)?)?\.?\s*(\d+)", str(it.get("where") or ""))
        if m:
            drilled.setdefault(int(m.group(1)), []).append(it.get("where"))
    for c in inv["candidates"]:
        if not _inventory.is_offerable(c):
            continue
        hit = drilled.get(c["docling_index"])
        if hit:
            c["disposition"] = _inventory.DRILL
            c["disposition_reason"] = "scout selected: %s" % ", ".join(str(h) for h in hit)
        else:
            c["disposition"] = _inventory.SKIP_WITH_REASON
            c["disposition_reason"] = "scout saw the caption and judged it non-digitizable"
    inv["scout_reconciled"] = True
    (P.extracted_dir(sd) / "figure_inventory.json").write_text(json.dumps(inv, indent=1))
    return inv


#: how many independent scout samples to union. Coverage selection is a recall task, so
#: a figure named by ANY sample is kept.
SCOUT_SAMPLES = 2


def _drill_key(d):
    """Identity of a drill item for de-duplication across samples."""
    return (str(d.get("where") or "").strip().lower(), str(d.get("type") or ""),
            str(d.get("measurand") or ""))


def union_drill(primary, extra):
    """Union the drill lists of two scout results, keeping `primary` order.

    The scout is a COVERAGE selector, and its own schema says a data plot must never be
    dropped — but the model is sampled, and at temperature 0 it still varies between
    runs. A single sample therefore loses real figures at random: 10.1063/1.5028178
    FIG. 2 (a four-series pressure-vs-position plot) was drilled in one run and silently
    omitted in the next from a byte-identical caption line. Unioning independent samples
    turns that silent loss into at most a duplicate vision call, which the figure stage
    already tolerates — an unknown [F#] tag is skipped and a repeated one is grouped.
    """
    out = list(primary or [])
    seen = {_drill_key(d) for d in out}
    seen_idx = {re.sub(r"[^0-9]", "", str(d.get("where") or "")) for d in out}
    for d in (extra or []):
        k = _drill_key(d)
        idx = re.sub(r"[^0-9]", "", str(d.get("where") or ""))
        if k in seen or not idx or idx in seen_idx:
            continue                          # already covered, at item or figure level
        item = dict(d)
        item["_from_sample"] = 2
        out.append(item)
        seen.add(k)
    return out


def scout(sd, client):
    _inventory.write(sd)                              # provenance first, then decide
    abstract, conclusion, caps = build_scout_input(sd)
    prompt = (f"{SCHEMA}\n\n=== ABSTRACT ===\n{abstract}\n\n=== CONCLUSION ===\n{conclusion}"
              f"\n\n=== FIGURE/TABLE CAPTIONS ===\n" + "\n".join(caps))
    obj, tok = _scout_call(client, MODEL, prompt)     # raises loudly rather than emptying
    n_first = len(obj.get("drill") or [])
    for _ in range(SCOUT_SAMPLES - 1):
        try:
            alt, tok2 = _scout_call(client, MODEL, prompt)
        except Exception as e:                        # a failed extra sample must never
            print(f"  [scout sample skipped] {e}")    # weaken the primary result
            continue
        obj["drill"] = union_drill(obj.get("drill"), alt.get("drill"))
        for k in ("in", "out"):
            if tok.get(k) is not None and tok2.get(k) is not None:
                tok[k] = tok[k] + tok2[k]
    gained = len(obj.get("drill") or []) - n_first
    obj["_scout_samples"] = SCOUT_SAMPLES
    if gained:
        print(f"  [scout union] +{gained} figure(s) recovered from sample 2")
    obj["_tokens"] = tok
    obj["_scout_input_chars"] = len(prompt)
    (P.extracted_dir(sd) / "scout.json").write_text(json.dumps(obj, indent=1))
    inv = _reconcile_dispositions(sd, obj)
    mr = [c["candidate_id"] for c in inv["candidates"]
          if c["disposition"] == _inventory.MANUAL_REVIEW]
    if mr:
        print(f"  [manual-review] {len(mr)} uncaptioned plot-like crop(s) need a human "
              f"decision: {', '.join(mr)}")
    return obj


def dump_inputs(sd):
    """Write + print the exact scout inputs (no LLM) so they can be checked vs the PDF."""
    abstract, conclusion, caps = build_scout_input(sd)
    inv = _inventory.build(sd)
    n_fig = inv["n_pictures"]
    n_empty = n_fig - inv["n_captioned_by_docling"]
    held = [c for c in inv["candidates"] if not _inventory.is_offerable(c)]
    txt = (f"=== ABSTRACT ({len(abstract)} chars) ===\n{abstract}\n\n"
           f"=== CONCLUSION ({len(conclusion)} chars) ===\n{conclusion or '(none found)'}\n\n"
           f"=== FIGURE INVENTORY ({len(caps)} offered to scout; {n_fig} crops, "
           f"{n_empty} uncaptioned by docling, {inv['n_captions_recovered']} captions "
           f"recovered) ===\n" + "\n".join(caps)
           + "\n\n=== NOT OFFERED (explicit disposition, never a silent drop) ===\n"
           + "\n".join(f"[F{c['docling_index']}] {c['disposition']}: {c['disposition_reason']}"
                       for c in held))
    (P.extracted_dir(sd) / "scout_input.txt").write_text(txt)
    print(f"\n########## {sd} ##########")
    print(txt)
    print(f"\n[check] abstract {'OK' if len(abstract) > 200 else '⚠ short/empty'} · "
          f"conclusion {'OK' if conclusion else '⚠ NOT FOUND'} · "
          f"{len(caps)} crops offered · {inv['n_captions_recovered']} captions recovered · "
          f"{inv['n_manual_review']} manual-review")


def verify_all():
    """Stage-1 QA gate across every docling'd paper: flag the few needing a human look
    (docling failure, missing abstract/conclusion, high empty-caption ratio) → CSV."""
    import csv as _csv
    rows = []
    for d in sorted(P.extracted_dir(x) for x in P.papers() if P.extracted_dir(x).joinpath("structure.json").exists()):
        sd = d.parent.name
        md = (d / "document.md").read_text() if (d / "document.md").exists() else ""
        struct = json.loads((d / "structure.json").read_text())
        abstract = abstract_of(md)
        conclusion = section_text(md, ["conclusion", "summary", "concluding"])
        nfig = struct["n_figures"]
        nempty = sum(1 for f in struct["figures"] if not f["caption"])
        flags = []
        if len(md) < 500:
            flags.append("docling_fail")
        if len(abstract) < 200:
            flags.append("no_abstract")
        if not conclusion:
            flags.append("no_conclusion")
        if nfig and nempty > nfig * 0.5:
            flags.append("empty_captions")
        status = "FAIL" if "docling_fail" in flags else ("REVIEW" if flags else "OK")
        rows.append({"doi": sd, "status": status, "md_chars": len(md),
                     "abstract_chars": len(abstract), "conclusion_found": bool(conclusion),
                     "figs": nfig, "empty_caps": nempty, "flags": "|".join(flags)})
    out = ROOT / "refsets" / "extraction_qa.csv"
    with out.open("w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                            ["doi", "status", "md_chars", "abstract_chars", "conclusion_found",
                             "figs", "empty_caps", "flags"])
        w.writeheader(); w.writerows(rows)
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print(f"[verify] {len(rows)} papers: {dict(c)}  → refsets/extraction_qa.csv")
    for r in rows:
        if r["status"] != "OK":
            print(f"  {r['status']:6} {r['doi']:26} md={r['md_chars']} abs={r['abstract_chars']} "
                  f"concl={r['conclusion_found']} empty_caps={r['empty_caps']}/{r['figs']}  [{r['flags']}]")


def main(sds):
    if sds and sds[0] == "--verify":
        verify_all()
        return
    if sds and sds[0] == "--dump":
        for sd in sds[1:]:
            dump_inputs(sd)
        return
    from google import genai
    client = genai.Client(api_key=_load_key())
    tot_in = tot_out = 0
    failed = []
    for sd in sds:
        print(f"\n[scout] {sd}")
        try:
            o = scout(sd, client)
        except Exception as e:
            # Loud, and NO scout.json written — an empty scout would read downstream as
            # "this paper has no data" and the paper would vanish from the KB unnoticed.
            print(f"  [SCOUT FAILED - EMPTY] {sd}: {e}")
            failed.append(sd)
            continue
        tk = o.get("_tokens", {})
        tot_in += tk.get("in") or 0; tot_out += tk.get("out") or 0
        print(f"  tokens: in={tk.get('in')} out={tk.get('out')}  (input {o.get('_scout_input_chars')} chars)")
        drill = o.get("drill") or []
        meas = sum(1 for d in drill if d.get("source") == "measured")
        sim = sum(1 for d in drill if d.get("source") == "simulated")
        print(f"  study_type={o.get('study_type')}  material={o.get('materials')} precursor={o.get('precursors')} "
              f"coreactant={o.get('coreactants')} T={o.get('temperature_window_C')} gpc={o.get('gpc_nm')}")
        print(f"  data types found: {list((o.get('data') or {}).keys())}")
        print(f"  DRILL ({len(drill)}: {meas} measured / {sim} simulated): " +
              "; ".join(f"{d['where']}→{d['type']}[{(d.get('source') or '?')[:3]}]" for d in drill))
        print(f"  go_deeper={o.get('go_deeper')}")
    print(f"\n[scout] total tokens: in={tot_in} out={tot_out} for {len(sds)} papers "
          f"(~{(tot_in+tot_out)//max(len(sds),1)}/paper)")
    if failed:
        print(f"[scout] *** {len(failed)} PAPER(S) FAILED — not scouted, NOT in the KB: {failed}")
        sys.exit(1)          # non-zero so a batch run cannot report success while dropping papers


if __name__ == "__main__":
    main(sys.argv[1:])
