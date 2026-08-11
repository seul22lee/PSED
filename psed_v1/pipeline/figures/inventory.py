#!/usr/bin/env python3
"""
pipeline/figures/inventory.py — stage 1b: Docling artifacts -> figure inventory. NO LLM.

    python3 cli.py inventory <paper_id> [<paper_id> ...]

Why this stage exists
---------------------
Docling fails to bind a caption to ~57% of the PictureItems it extracts (319/561
across this corpus). The Scout input builder used to express that as

    caps = [... for f in struct["figures"] if f["caption"]]

which does not drop a *caption* — it drops the whole PictureItem. An uncaptioned
crop stopped existing before any decision was made about it, silently, with no
counter and no review record. Genuine digitizable plots were lost that way
(see reports/DOCLING_TO_CANONICAL_INFORMATION_LOSS_AUDIT.md).

This module rebuilds the provenance Docling lost, deterministically, without
re-parsing any PDF and without an LLM, and gives EVERY PictureItem an explicit
disposition so nothing can vanish silently again.

The positional anchor
---------------------
`document.md` carries one `<!-- image -->` placeholder per PictureItem, in
document order. Across all 32 corpus papers the marker count equals
`structure.json["n_figures"]` exactly, so the Nth marker IS docling picture N.
That gives each crop a character offset in the document, which is what makes
caption recovery evidence-based rather than a guess.

Evidence order (deterministic first, as required):
  1. the caption Docling itself bound                      -> "docling"
  2. an unclaimed printed caption adjacent to the marker   -> "document_md"
  3. membership of a sibling run that ends at a captioned
     crop of the same printed figure                       -> "sibling"
  4. no evidence -> cheap visual triage decides MANUAL_REVIEW vs SKIP_WITH_REASON

Ambiguity is never resolved by proximity alone: a caption is bound only when it
is unclaimed AND the nearest competing crop is not closer to it. Anything else
becomes MANUAL_REVIEW rather than a silent bind or a silent drop.

Machine identity is kept strictly separate from printed identity:
  candidate_id / docling_index  -> routing (what the pipeline addresses)
  printed_figure / panel        -> citation (what the paper calls it)
One printed figure may own several crops; one crop is never assumed to be a
whole printed figure.
"""
import paths as P
import json
import re
import sys
from pathlib import Path

#: how far after a marker a caption may start and still be considered "adjacent"
CAPTION_WINDOW = 260
#: how far before a caption a crop may sit and still count as a sibling of it
SIBLING_WINDOW = 300

#: explicit, exhaustive dispositions — every PictureItem gets exactly one
DRILL = "DRILL"
SKIP_WITH_REASON = "SKIP_WITH_REASON"
MANUAL_REVIEW = "MANUAL_REVIEW"
MERGED_INTO_PRINTED_FIGURE = "MERGED_INTO_PRINTED_FIGURE"
#: interim state written by this stage; the scout stage resolves it to DRILL or
#: SKIP_WITH_REASON. It must never survive into a finished run.
OFFERED = "OFFERED_TO_SCOUT"

_MARKER = re.compile(r"<!--\s*image\s*-->")

# "Figure 2.", "FIG. 1.", "Figure 1:", "Figure 7 ．", "Scheme 2." — the number must be
# followed by a caption delimiter. That single requirement is what separates a caption
# from a body reference: "Figure 1b shows the mass changes…" has no delimiter after the
# number and is therefore prose, not a caption.
_CAPTION = re.compile(
    r"(?:^|\n)[ \t>*]*"
    r"((?:Figure|Fig|FIG|Scheme|SCHEME)\s*\.?\s*(\d+)\s*[a-hA-H]?\s*[.:：．)]\s*\S[^\n]*)")
#: verbs that mark a sentence about a figure rather than the figure's own caption
_BODY_VERB = re.compile(
    r"^\s*(?:shows?|presents?|displays?|illustrates?|depicts?|gives?|reports?|"
    r"summari[sz]es?|compares?|indicates?|reveals?|plots?|contains?|is\b|are\b|was\b|were\b)",
    re.I)


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _norm_key(s):
    """Aggressive normalisation for matching a docling caption to a markdown caption:
    docling and the markdown export differ in whitespace and in a few unicode
    punctuation choices (e.g. 'Figure 7 ．' vs 'Figure 7.')."""
    s = _norm(s).lower()
    s = s.replace("．", ".").replace("：", ":")
    return re.sub(r"[^a-z0-9]+", "", s)


def parse_captions(md):
    """Every printed figure caption in the document, with its offset and number.

    Body references are rejected (see _CAPTION / _BODY_VERB), because binding a crop
    to "Figure 1b shows the mass changes…" would invent provenance that does not
    exist. Returns [{offset, printed_figure, text}] in document order.
    """
    out = []
    for m in _CAPTION.finditer(md):
        text, num = _norm(m.group(1)), m.group(2)
        # the caption delimiter is the last char of the matched prefix; what follows it
        # must read as a caption body, not as a predicate about the figure
        tail = text.split(None, 2)
        rest = tail[2] if len(tail) > 2 else ""
        if _BODY_VERB.match(rest):
            continue
        out.append({"offset": m.start(1), "printed_figure": num, "text": text})
    return out


def _extend_caption(md, cap):
    """Grow a caption to its full paragraph so a recovered caption is as informative
    as one Docling bound itself (the vision stage uses it as context)."""
    end = md.find("\n\n", cap["offset"])
    if end < 0:
        end = len(md)
    return _norm(md[cap["offset"]:end])[:1200] or cap["text"]


def crop_stats(path):
    """Cheap deterministic triage of a crop. Only consulted for crops that have NO
    caption evidence — it decides MANUAL_REVIEW vs SKIP_WITH_REASON, never a bind,
    and never sends anything to the vision stage on its own."""
    try:
        from PIL import Image
    except Exception:
        return {"width": 0, "height": 0, "klass": "unknown"}
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return {"width": 0, "height": 0, "klass": "unknown"}
    w, h = im.size
    small = im.resize((min(w, 160), min(h, 160)))
    px = list(small.getdata())
    n = len(px) or 1
    white = sum(1 for r, g, b in px if r > 235 and g > 235 and b > 235) / n
    colors = len({(r >> 4, g >> 4, b >> 4) for r, g, b in px})
    grey = sum(1 for r, g, b in px if abs(r - g) < 12 and abs(g - b) < 12) / n
    if w * h < 40000 or min(w, h) < 120:
        klass = "fragment"
    elif w >= 3.0 * h and h < 220:
        klass = "banner_or_logo"
    elif white > 0.45 and colors < 260:
        klass = "plot_like"          # mostly white ground with limited ink → a chart
    elif grey > 0.80 and white < 0.30:
        klass = "micrograph_like"    # dense greyscale → SEM/TEM/AFM
    else:
        klass = "image_like"
    return {"width": w, "height": h, "white_frac": round(white, 3),
            "distinct_colors": colors, "grey_frac": round(grey, 3), "klass": klass}


def build(paper_id, with_crop_stats=True):
    """Build the figure inventory for one paper. Pure function of the Docling
    artifacts on disk — no LLM, no network, no writes."""
    d = P.extracted_dir(paper_id)
    md = (d / "document.md").read_text()
    struct = json.loads((d / "structure.json").read_text())
    figures = struct.get("figures") or []

    markers = [m.start() for m in _MARKER.finditer(md)]
    aligned = len(markers) == len(figures)
    caps = parse_captions(md)

    # --- 1. which printed captions did Docling already claim? -------------------
    by_key = {}
    for c in caps:
        by_key.setdefault(_norm_key(c["text"])[:120], []).append(c)
    claimed = {}                       # caption offset -> docling index that owns it
    printed_of = {}                    # docling index -> printed figure number
    for f in figures:
        cap = _norm(f.get("caption"))
        if not cap:
            continue
        k = _norm_key(cap)[:120]
        hit = by_key.get(k) or []
        if not hit:                    # docling caption not found verbatim in the md
            pre = _norm_key(cap)[:60]
            hit = [c for c in caps if _norm_key(c["text"])[:60] == pre]
        if len(hit) == 1:
            claimed[hit[0]["offset"]] = f["index"]
            printed_of[f["index"]] = hit[0]["printed_figure"]
        else:
            m = re.match(r"(?:figure|fig|scheme)\s*\.?\s*(\d+)", cap, re.I)
            if m:
                printed_of[f["index"]] = m.group(1)

    # --- 2. recover a caption for each unbound crop from adjacency ---------------
    cand = []
    for f in figures:
        i = f["index"]
        off = markers[i] if aligned and i < len(markers) else None
        cand.append({
            "candidate_id": "P%d" % i,
            "docling_index": i,
            "image": f.get("image") or "",
            "md_offset": off,
            "page": f.get("page"),
            "bbox": f.get("bbox"),
            "caption_original": _norm(f.get("caption")),
            "caption_recovered": "",
            "caption_source": "docling" if _norm(f.get("caption")) else "none",
            "caption_confidence": 1.0 if _norm(f.get("caption")) else 0.0,
            "printed_figure": printed_of.get(i),
            "panel": None,
            "siblings": [],
            "printed_group_id": None,
            "disposition": None,
            "disposition_reason": "",
        })

    unclaimed = [c for c in caps if c["offset"] not in claimed]
    for c in cand:
        if c["caption_source"] == "docling" or c["md_offset"] is None:
            continue
        off = c["md_offset"]
        near = [x for x in unclaimed if 0 <= x["offset"] - off <= CAPTION_WINDOW]
        if not near:
            continue
        target = min(near, key=lambda x: x["offset"] - off)
        # Unambiguous only if no OTHER crop sits between this crop and the caption —
        # otherwise the closer crop is the better owner and this one is a sibling.
        between = [o for o in (markers or []) if off < o < target["offset"]]
        if between:
            continue
        c["caption_recovered"] = _extend_caption(md, target)
        c["caption_source"] = "document_md"
        c["caption_confidence"] = 0.9
        c["printed_figure"] = target["printed_figure"]
        claimed[target["offset"]] = c["docling_index"]
        unclaimed = [x for x in unclaimed if x["offset"] != target["offset"]]

    # --- 3. sibling runs: crops that share one printed figure --------------------
    # A printed figure split across several crops leaves the caption bound to (or
    # recovered by) exactly one of them; the crops immediately around it, with no
    # other caption in between, belong to the same printed figure.
    owner_offset = {v: k for k, v in claimed.items()}
    for c in cand:
        idx = c["docling_index"]
        if idx not in owner_offset:
            continue
        cap_off = owner_offset[idx]
        group = [idx]
        for other in cand:
            j = other["docling_index"]
            if j == idx or other["md_offset"] is None:
                continue
            dist = cap_off - other["md_offset"]
            if 0 < dist <= SIBLING_WINDOW and other["caption_source"] in ("none",):
                inter = [x for x in caps if other["md_offset"] < x["offset"] < cap_off]
                if not inter:
                    group.append(j)
        if len(group) > 1:
            gid = "printed:%s" % (c["printed_figure"] or ("idx%d" % idx))
            for j in group:
                cj = cand[j]
                cj["printed_group_id"] = gid
                cj["siblings"] = sorted(x for x in group if x != j)
                if cj["caption_source"] == "none":
                    cj["caption_recovered"] = c["caption_recovered"] or c["caption_original"]
                    cj["caption_source"] = "sibling"
                    cj["caption_confidence"] = 0.6
                    cj["printed_figure"] = c["printed_figure"]

    # --- 4. disposition for every PictureItem — nothing may be left unset --------
    for c in cand:
        if with_crop_stats and c["image"]:
            c["crop"] = crop_stats(d / c["image"])
        klass = (c.get("crop") or {}).get("klass", "unknown")
        if not c["image"]:
            c["disposition"] = SKIP_WITH_REASON
            c["disposition_reason"] = "docling produced no image crop"
        elif c["caption_source"] == "sibling" and klass in ("fragment", "banner_or_logo"):
            # part of a split printed figure, but this crop is a label strip or rule —
            # it carries no data of its own and must not become a second vision call
            c["disposition"] = MERGED_INTO_PRINTED_FIGURE
            c["disposition_reason"] = ("%s crop of printed figure %s; content covered by "
                                       "sibling crop(s)" % (klass, c["printed_figure"]))
        elif c["caption_source"] in ("docling", "document_md", "sibling"):
            c["disposition"] = OFFERED
            c["disposition_reason"] = "caption available via %s" % c["caption_source"]
        elif klass in ("fragment", "banner_or_logo"):
            c["disposition"] = SKIP_WITH_REASON
            c["disposition_reason"] = "no caption evidence; crop is a %s" % klass
        elif klass in ("plot_like",):
            c["disposition"] = MANUAL_REVIEW
            c["disposition_reason"] = ("no caption evidence but crop looks like a plot — "
                                       "needs a human decision, not silent discard")
        else:
            c["disposition"] = SKIP_WITH_REASON
            c["disposition_reason"] = "no caption evidence; crop is %s" % klass

    # --- 5. duplicate-crop guard within a printed figure -------------------------
    # Docling sometimes emits both a whole-figure crop and per-panel crops of the same
    # printed figure. Digitizing both would duplicate the same plot, so a crop that is
    # a near-copy of an earlier sibling is merged rather than read twice.
    seen = {}
    for c in cand:
        if c["disposition"] != OFFERED or not c["printed_group_id"]:
            continue
        st = c.get("crop") or {}
        key = (c["printed_group_id"], st.get("width"), st.get("height"),
               st.get("distinct_colors"))
        if all(k is not None for k in key[1:]) and key in seen:
            c["disposition"] = MERGED_INTO_PRINTED_FIGURE
            c["disposition_reason"] = ("near-duplicate crop of %s within printed figure %s"
                                       % (seen[key], c["printed_figure"]))
        else:
            seen[key] = c["candidate_id"]

    n_recovered = sum(1 for c in cand if c["caption_source"] in ("document_md", "sibling"))
    return {
        "doi": paper_id,
        "marker_alignment": "exact" if aligned else "MISALIGNED",
        "n_pictures": len(figures),
        "n_captioned_by_docling": sum(1 for c in cand if c["caption_source"] == "docling"),
        "n_captions_recovered": n_recovered,
        "n_manual_review": sum(1 for c in cand if c["disposition"] == MANUAL_REVIEW),
        "candidates": cand,
    }


def caption_for(c):
    """The best caption available for a candidate, whatever its source."""
    return c.get("caption_recovered") or c.get("caption_original") or ""


def is_offerable(c):
    """Whether this crop should be put in front of the scout.

    Derived from the EVIDENCE (does it have an image and a caption from any source),
    never from `disposition`. Disposition is a record of what happened on a given run
    and is rewritten to DRILL / SKIP_WITH_REASON once the scout has ruled; keying
    eligibility off it would make a second scout run on the same paper see an empty
    figure list and silently drop every figure in the paper.
    """
    return (bool(c.get("image"))
            and c.get("caption_source") in ("docling", "document_md", "sibling")
            and c.get("disposition") != MERGED_INTO_PRINTED_FIGURE)


def load(paper_id):
    """Read the inventory, building it on demand if the stage has not been run."""
    p = P.extracted_dir(paper_id) / "figure_inventory.json"
    if p.exists():
        return json.loads(p.read_text())
    return build(paper_id)


def write(paper_id):
    inv = build(paper_id)
    (P.extracted_dir(paper_id) / "figure_inventory.json").write_text(json.dumps(inv, indent=1))
    return inv


def main(ids):
    ids = ids or sorted(P.papers())
    for pid in ids:
        if not P.structure_json(pid).exists():
            print("[inventory] %s: no structure.json — skipped" % pid)
            continue
        inv = write(pid)
        groups = {c["printed_group_id"] for c in inv["candidates"] if c["printed_group_id"]}
        print("[inventory] %-34s pics=%-3d docling_caps=%-3d recovered=%-3d "
              "manual=%-2d split_groups=%d %s"
              % (pid, inv["n_pictures"], inv["n_captioned_by_docling"],
                 inv["n_captions_recovered"], inv["n_manual_review"], len(groups),
                 "" if inv["marker_alignment"] == "exact" else "*** " + inv["marker_alignment"]))


if __name__ == "__main__":
    main(sys.argv[1:])
