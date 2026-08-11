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

#: distance under which an association is called "positional_adjacent" rather than
#: "structural_local_search". This is a LABEL threshold, not a gate: association is
#: decided by intervening structure (markers and other captions), never by distance.
CAPTION_WINDOW = 260
#: two candidate captions are treated as equally plausible — and the crop is therefore
#: left for a human — when the runner-up is within this factor of the nearest.
AMBIGUITY_RATIO = 1.5
#: max characters between two consecutive image markers for them to count as crops of
#: ONE printed figure. Document adjacency, not caption search: genuine siblings are 16
#: characters apart in every case observed in this corpus.
CLUSTER_GAP = 200

#: explicit, exhaustive dispositions — every PictureItem gets exactly one
DRILL = "DRILL"
SKIP_WITH_REASON = "SKIP_WITH_REASON"
MANUAL_REVIEW = "MANUAL_REVIEW"
MERGED_INTO_PRINTED_FIGURE = "MERGED_INTO_PRINTED_FIGURE"
#: interim state written by this stage; the scout stage resolves it to DRILL or
#: SKIP_WITH_REASON. It must never survive into a finished run.
OFFERED = "OFFERED_TO_SCOUT"

_MARKER = re.compile(r"<!--\s*image\s*-->")

# A caption line: "Figure 2. a) …", "FIG. 1. Saturation …", "Fig. 5 Dependence of …",
# "Fig. 5 (a) Growth rate …", "Fig. 2 a Typical XPS …", "Figure 7 ． Scheme of …".
#
# An earlier version required a delimiter (. : ) ．) right after the figure number. That
# is Wiley/ACS/AIP house style, but Springer and RSC print "Fig. 5 Dependence of …" with
# no delimiter at all — so the parser returned ZERO captions for 11 of 32 corpus papers
# and caption recovery was silently disabled for a third of the corpus. The delimiter is
# now optional; what separates a caption from a body reference is handled by
# _caption_body() below, which is a stronger test than punctuation.
_CAPTION = re.compile(
    r"(?:^|\n)[ \t>*]*"
    r"((?:Figure|Fig|FIG|Scheme|SCHEME)\s*\.?\s*(\d+)\s*[.:：．]?\s*\S[^\n]*)")
#: an optional panel marker directly after the figure number: "a", "(a)", "a)", "a."
_PANEL_HEAD = re.compile(r"^\(?([a-hA-H])\)?[.,:]?\s+")
#: verbs that mark a sentence about a figure rather than the figure's own caption
_BODY_VERB = re.compile(
    r"^\s*(?:shows?|presents?|displays?|illustrates?|depicts?|gives?|reports?|"
    r"summari[sz]es?|compares?|indicates?|reveals?|plots?|contains?|is\b|are\b|was\b|were\b)",
    re.I)


def _caption_body(text):
    """The caption text after 'Fig N' and an optional panel marker, or None if this
    reads as prose about the figure rather than the figure's own caption.

    Two independent signals, both needed because journals differ:
      · a body reference continues a sentence, so it starts with a lower-case function
        word — "Fig. 5 for films grown on Si(100) …" — while a caption starts with a
        capitalised noun or a panel marker;
      · an explicit predicate — "Fig. 5(a) shows that …" — is prose even when a panel
        marker precedes it.
    """
    m = re.match(r"(?:Figure|Fig|FIG|Scheme|SCHEME)\s*\.?\s*\d+\s*[.:：．]?\s*(.*)$",
                 text, re.S)
    if not m:
        return None
    rest = m.group(1).strip()
    pm = _PANEL_HEAD.match(rest)
    if pm:                                   # "a Typical XPS …" / "(a) Growth rate …"
        rest = rest[pm.end():].strip()
    if not rest or _BODY_VERB.match(rest):
        return None
    if not (rest[0].isupper() or rest[0].isdigit()):
        return None                          # "for films grown …" — a continued sentence
    return rest


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
        if _caption_body(text) is None:
            continue
        out.append({"offset": m.start(1), "printed_figure": num, "text": text})
    return out


def _first_or_none(xs):
    return xs[0] if xs else None


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
            "printed_figure_id": None,
            "panel": None,
            "siblings": [],
            "printed_group_id": None,
            # how the caption identity was obtained; original Docling evidence in
            # caption_original is never overwritten
            "association_method": "docling_bound" if _norm(f.get("caption")) else "unresolved",
            "disposition": None,
            "disposition_reason": "",
        })

    # --- 2. group crops into PRINTED FIGURES -------------------------------------
    # The unit a caption governs is not a PictureItem, it is a run of CONSECUTIVE
    # PictureItems with no caption text between them. Docling routinely splits one
    # printed figure into several crops and binds the caption to whichever crop it
    # happened to associate — sometimes the first of the run, sometimes the last.
    # Treating each crop as independently captioned lost every other member of the
    # run; grouping first makes the association direction irrelevant.
    # Two crops share a printed figure only when the document says they sit together:
    # they are consecutive, separated by nothing but the marker separator, with no
    # caption between them, and they do not each carry a different Docling caption
    # (two captions mean two printed figures). CLUSTER_GAP measures DOCUMENT ADJACENCY
    # — "were these printed as one figure" — it is not a caption-search radius. Real
    # siblings sit 16 characters apart (just "<!-- image -->\n\n"); the nearest false
    # candidate observed in this corpus is 327 away, so the threshold is not delicate.
    def _own_cap(i):
        return _norm_key(cand[i]["caption_original"])[:60] or None

    def _splits(i):
        """Does a caption printed between crops i-1 and i separate two printed figures?

        Only if it belongs to neither of them. A figure split across crops often has
        its caption printed BETWEEN those crops — 10.1116/6.0002436 FIG. 1 sits between
        its own second and third crop — so treating any intervening caption as a
        boundary cuts a printed figure in half at exactly its own caption.
        """
        for c in caps:
            if not (markers[i - 1] < c["offset"] < markers[i]):
                continue
            if claimed.get(c["offset"]) in (i, i - 1):
                continue                     # it is their own caption, not a boundary
            return True
        return False

    clusters = []
    if aligned and markers:
        cur = [0]
        for i in range(1, len(markers)):
            gap = markers[i] - markers[i - 1]
            # If the pair's OWN caption is printed between them, its text is what makes
            # the gap large, so it is discounted from the measurement — but only its
            # own length. Waiving the adjacency test outright instead would let a crop
            # 6748 characters away join the group just because a caption sat somewhere
            # in between (observed on cremers2019 P17/P18).
            own_len = sum(len(c["text"]) for c in caps
                          if markers[i - 1] < c["offset"] < markers[i]
                          and claimed.get(c["offset"]) in (i, i - 1))
            split = (_splits(i)
                     or (gap - own_len > CLUSTER_GAP)
                     or (_own_cap(i) and _own_cap(i - 1) and _own_cap(i) != _own_cap(i - 1)))
            if split:
                clusters.append(cur)
                cur = [i]
            else:
                cur.append(i)
        clusters.append(cur)
    else:
        clusters = [[f["index"]] for f in figures]

    # A crop whose OWN adjacent caption is unclaimed owns that caption outright; it must
    # not inherit a neighbour's. Splitting these out before inheritance is what stops
    # d3dt01824e P8 (its own "Fig. 5" sits 16 chars later) being labelled with P7's Fig 4.
    def _adjacent_unclaimed(i, pool):
        off = markers[i]
        hits = []
        for cap in pool:
            o = cap["offset"]
            lo, hi = min(o, off), max(o, off)
            if any(lo < m < hi for m in markers):
                continue
            if any(lo < c["offset"] < hi for c in caps if c["offset"] != o):
                continue
            hits.append((abs(o - off), cap))
        hits.sort(key=lambda t: t[0])
        return hits

    if aligned and markers:
        pool = [c for c in caps if c["offset"] not in claimed]
        refined = []
        for cl in clusters:
            if len(cl) == 1:
                refined.append(cl)
                continue
            run, has_anchor = [], False
            for i in cl:
                hits = _adjacent_unclaimed(i, pool) if not cand[i]["caption_original"] else []
                own = (cand[i]["caption_source"] == "docling"
                       or (hits and hits[0][0] <= CLUSTER_GAP))
                # Split only on a SECOND anchor. Splitting on the first would separate a
                # trailing captioned crop from the siblings that precede it — the very
                # arrangement this grouping exists to capture (6.0002436 FIG. 1 is bound
                # to the LAST of its three crops).
                if own and has_anchor:
                    refined.append(run)
                    run, has_anchor = [i], True
                else:
                    run.append(i)
                    has_anchor = has_anchor or own
            if run:
                refined.append(run)
        clusters = refined

    unclaimed = [c for c in caps if c["offset"] not in claimed]

    # Is this document's caption coverage COMPLETE? Collect every printed figure number
    # the text refers to, and every number for which a caption exists from any source
    # (Docling-bound or parsed from the markdown). A number that is referenced but has
    # no caption anywhere means that figure's caption never became text — typically
    # because it is baked into the image crop. In such a paper an uncaptioned crop is
    # more likely to BE one of those missing figures than to be a sibling of a captioned
    # one, so caption inheritance across a cluster is not evidence, it is a guess.
    # 10.1186/s11671-015-0872-9 is the case: 8 crops, captions only for Figures 1, 3, 4,
    # and crops that are printed Figures 2, 5 and 6 would otherwise inherit 3 and 4.
    referenced = {m.group(1) for m in
                  re.finditer(r"\b(?:Figure|Fig|FIG)\.?\s*(\d+)", md)}
    have_caption = {c["printed_figure"] for c in caps}
    have_caption |= {v for v in printed_of.values() if v}
    missing_numbers = {n for n in referenced if n not in have_caption}
    inheritance_ok = not missing_numbers

    def _bind(cluster, cap, method, conf, anchor=None):
        """Give every member of a printed-figure cluster the same caption identity,
        recording HOW each member obtained it. Never overwrites caption_original."""
        text = _extend_caption(md, cap) if cap else None
        gid = "printed:%s" % (cap["printed_figure"] if cap else "idx%d" % cluster[0])
        for j in cluster:
            cj = cand[j]
            cj["printed_group_id"] = gid
            cj["siblings"] = sorted(x for x in cluster if x != j)
            cj["printed_figure_id"] = ("Figure %s" % cap["printed_figure"]) if cap else None
            if cj["caption_source"] == "docling":
                cj["association_method"] = "docling_bound"
                continue
            cj["caption_recovered"] = text
            cj["printed_figure"] = cap["printed_figure"] if cap else None
            if j == anchor:
                cj["caption_source"] = "document_md"
                cj["caption_confidence"] = conf
                cj["association_method"] = method
            else:
                cj["caption_source"] = "sibling"
                cj["caption_confidence"] = round(conf - 0.15, 2)
                cj["association_method"] = "shared_printed_figure"

    for cluster in clusters:
        owners = [j for j in cluster if cand[j]["caption_source"] == "docling"]
        if owners:
            # Evidence: a member already carries a Docling-bound caption. Every other
            # member of the same run belongs to that printed figure. This is the case
            # the old code could not express, and it accounts for 5 of the 11 losses.
            j0 = owners[0]
            off0 = _first_or_none([o for o, i in claimed.items() if i == j0])
            cap0 = next((c for c in caps if c["offset"] == off0), None)
            if cap0 is None:
                pf = printed_of.get(j0)
                cap0 = {"offset": None, "printed_figure": pf, "text": cand[j0]["caption_original"]}
                text = cand[j0]["caption_original"]
            else:
                text = _extend_caption(md, cap0)
            gid = "printed:%s" % (cap0["printed_figure"] or "idx%d" % j0)
            if not inheritance_ok and len(cluster) > 1:
                # captions are missing for figures this paper cites — see above
                for j in cluster:
                    if cand[j]["caption_source"] != "docling":
                        cand[j]["association_method"] = "unresolved"
                        cand[j]["disposition_reason"] = (
                            "caption inheritance withheld: this document cites figure(s) "
                            "%s with no caption text anywhere, so an uncaptioned crop may "
                            "be one of them" % ", ".join(sorted(missing_numbers)))
                continue
            for j in cluster:
                cj = cand[j]
                cj["printed_group_id"] = gid if len(cluster) > 1 else None
                cj["siblings"] = sorted(x for x in cluster if x != j)
                cj["printed_figure_id"] = ("Figure %s" % cap0["printed_figure"]) if cap0["printed_figure"] else None
                if cj["caption_source"] == "docling":
                    cj["association_method"] = "docling_bound"
                else:
                    cj["caption_recovered"] = text
                    cj["caption_source"] = "sibling"
                    cj["caption_confidence"] = 0.75
                    cj["printed_figure"] = cap0["printed_figure"]
                    cj["association_method"] = "shared_printed_figure"
            continue

        # No member is captioned. Look for ONE unclaimed caption structurally adjacent
        # to the run: nothing but body text between it and the run — no other image
        # marker (which would be a better owner) and no other caption (which would be
        # a better match). Distance is evidence, not the test, so a caption separated
        # from its figure by a paragraph of reading-order displacement is still found,
        # while a caption with any competing crop or caption in between is refused.
        first, last = markers[cluster[0]], markers[cluster[-1]]
        cands = []
        for cap in unclaimed:
            o = cap["offset"]
            if o < first:
                lo, hi, anchor = o, first, cluster[0]
            elif o > last:
                lo, hi, anchor = last, o, cluster[-1]
            else:
                continue                     # inside the run — the run would have split
            if any(lo < m < hi for m in markers):
                continue                     # a nearer crop can claim it
            if any(lo < c["offset"] < hi for c in caps if c["offset"] != o):
                continue                     # a nearer caption competes
            cands.append((abs(o - (first if o < first else last)), cap, anchor))
        if not cands:
            continue
        cands.sort(key=lambda t: t[0])
        if len(cands) > 1 and cands[1][0] <= cands[0][0] * AMBIGUITY_RATIO:
            continue                         # two captions equally plausible — leave it
        dist, cap, anchor = cands[0]
        method = "positional_adjacent" if dist <= CAPTION_WINDOW else "structural_local_search"
        conf = 0.9 if dist <= CAPTION_WINDOW else 0.8
        _bind(cluster, cap, method, conf, anchor=anchor)
        claimed[cap["offset"]] = anchor
        unclaimed = [x for x in unclaimed if x["offset"] != cap["offset"]]

    # --- 4. disposition for every PictureItem — nothing may be left unset --------
    for c in cand:
        if with_crop_stats and c["image"]:
            c["crop"] = crop_stats(d / c["image"])
        klass = (c.get("crop") or {}).get("klass", "unknown")
        if not c["image"]:
            c["disposition"] = SKIP_WITH_REASON
            c["disposition_reason"] = "docling produced no image crop"
        elif klass in ("fragment", "banner_or_logo") and c["caption_source"] != "docling":
            # A label strip or running-header band carries no data whatever caption it
            # ended up with. Keying this off the crop CLASS rather than the association
            # method matters: once captions can also be recovered positionally, a
            # fragment that happens to sit next to a caption would otherwise be promoted
            # to a vision call (observed on 6.0002804 P24/P26).
            if c["printed_group_id"]:
                c["disposition"] = MERGED_INTO_PRINTED_FIGURE
                c["disposition_reason"] = ("%s crop of printed figure %s; content covered "
                                           "by sibling crop(s)" % (klass, c["printed_figure"]))
            else:
                c["disposition"] = SKIP_WITH_REASON
                c["disposition_reason"] = ("%s crop; carries a caption (%s) but no data"
                                           % (klass, c["association_method"]))
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
