"""
canonical/chemistry_scope.py — resolve a curve's material and reactants from the
NARROWEST evidence that actually mentions them.

The defect this replaces was a single line in the figure-extraction stage:

    material = mats[0] if mats else None

Material was recovered only when a series legend happened to BE a material name;
for every other legend the paper's first material was assigned by list position.
A caption reading "thickness profiles of a 1000cycle deposition process of TiO2
from TiCl4 and H2O" produced material=Al2O3, precursor=TMA, because Al2O3 sorted
first in scout.materials. Nine of thirty-one papers collapsed this way.

The precedence ladder here is the fix, and its last rung is the important one:

    1. series legend label that is one of this paper's materials
    2. this panel's own clause of the caption
    3. the figure caption, when the figure does not vary material by panel
    4. scout drill note for this figure naming exactly one of them
    5. figure-linked body text naming exactly one of them
    6. single-material paper -> that material
    7. otherwise -> None, with the candidates and the reason recorded

Rung 7 refuses instead of guessing. `resolve_experiment_chemistry(None)` already
returns `ambiguous / unresolved_multi_material / confidence 0.0`, so refusing
yields an honest unresolved record rather than a confident wrong one. Nothing
here infers a material from a precursor, from element overlap, or from list
order.
"""
from __future__ import annotations

import re

#: "TiO2 from TiCl4 and H2O" / "Al2O3 from Al(CH3)3 and H2O" — an author stating
#: the full chemistry of one figure in one clause. This is the strongest
#: figure-level evidence there is and it outranks every paper-level default.
_FROM = re.compile(
    r"(?P<material>[A-Z][A-Za-z0-9]*)\s+from\s+"
    r"(?P<precursor>[A-Za-z][A-Za-z0-9()\[\]\-]{1,28}?)\s+and\s+"
    r"(?P<coreactant>[A-Za-z][A-Za-z0-9()\[\]\-]{1,28}?)\s*(?:[.,;)]|$|\s+in\b|\s+at\b)",
    re.I)

#: docling drops the spaces out of subscripts inconsistently: "Al2O3", "Al 2 O 3"
#: and "Al2 O3" all occur in the same corpus.
def _loose(formula):
    """Match a formula through docling's spacing AND the sub-stoichiometric
    spelling ALD papers use interchangeably: a film listed as MoS2 or WS2 is
    written MoSx / WSx wherever the composition is not exactly stoichiometric.
    Treating those as different materials split one film into two."""
    chars = [c for c in formula if not c.isspace()]
    parts = []
    for i, ch in enumerate(chars):
        if ch.isdigit() and i == len(chars) - 1:
            parts.append(r"(?:%s|[xy])" % re.escape(ch))
        else:
            parts.append(re.escape(ch))
    return r"\s*".join(parts)


def _named(text, materials):
    """Which of THIS paper's materials the text names verbatim.

    Anchoring on the paper's own material list is what keeps substrates and
    reactor parts (Si, SiO2, an Al2O3 barrier in a Bi2Te3 paper) from being read
    as the deposited film."""
    if not text:
        return []
    out = []
    for m in materials or []:
        if re.search(r"(?<![A-Za-z0-9])" + _loose(m) + r"(?![a-z0-9])", text, re.I):
            out.append(m)
    return out


def caption_chemistry(caption, materials):
    """The explicit '<material> from <precursor> and <coreactant>' statement.

    Returns None unless the material named is one of the paper's own, so a
    sentence about a reference process cannot rewrite this figure's chemistry.
    """
    if not caption:
        return None
    for m in _FROM.finditer(caption):
        mat = m.group("material")
        hit = _named(mat, materials)
        if not hit:
            continue
        return {
            "material": hit[0],
            "precursor": m.group("precursor").strip(),
            "coreactant": m.group("coreactant").strip(),
            "evidence": " ".join(m.group(0).split())[:200],
            "level": "figure_caption_explicit",
        }
    return None


#: "The precursors used were A (a), B (b), and C (c) for the growth of X, Y, and
#: Z, respectively." A methods sentence that maps precursors to materials
#: EXPLICITLY, in the author's own words. It is far better evidence than an
#: element-hint table, and it is the construction ALD methods sections use
#: whenever a paper deposits more than one film.
_RESPECTIVELY = re.compile(
    r"precursors?[^.]{0,40}?\bwere\b(?P<precursors>[^.]{5,400}?)"
    r"\bfor the (?:growth|deposition) of\b(?P<materials>[^.]{3,200}?)"
    r",?\s*respectively", re.I | re.S)


def _split_list(text):
    """Split 'A (a), B (b), and C (c)' into ['A (a)', 'B (b)', 'C (c)'] without
    breaking on the commas INSIDE a formula's parentheses."""
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    out = []
    for p in parts:
        p = re.sub(r"^\s*and\s+", "", p.strip()).strip(" .;")
        if p:
            out.append(p)
    return out


def _preferred_name(item):
    """'SiH2(N(C2H5)2)2 (BDEAS)' -> 'BDEAS'. The parenthetical acronym is the
    name the rest of the paper and the ontology use; the formula is kept as a
    fallback when there is no acronym."""
    m = re.search(r"\(([A-Za-z][A-Za-z0-9\-]{1,14})\)\s*$", item.strip())
    if m:
        return m.group(1)
    return item.strip()


def methods_chemistry_mapping(methods_text, materials):
    """{material: precursor} stated explicitly by a 'respectively' sentence.

    Returns {} unless the two lists are the same length -- an unequal pairing
    means the sentence was not the simple one-to-one mapping it looked like, and
    guessing an alignment would be exactly the list-order error this module
    exists to remove.
    """
    if not methods_text:
        return {}
    for m in _RESPECTIVELY.finditer(methods_text):
        precs = [_preferred_name(x) for x in _split_list(m.group("precursors"))]
        mats_raw = _split_list(m.group("materials"))
        mats = []
        for raw in mats_raw:
            hit = _named(raw, materials)
            mats.append(hit[0] if len(hit) == 1 else None)
        if len(precs) != len(mats) or not precs:
            continue
        if any(x is None for x in mats):
            continue
        return {mat: {"precursor": pre,
                      "evidence": " ".join(m.group(0).split())[:260],
                      "level": "methods_respectively_mapping"}
                for mat, pre in zip(mats, precs)}
    return {}


def resolve_material(series_label, caption, drill_why, body, materials,
                     legend_is_material=None, panel_clause=None,
                     panel_assigns_materials=False):
    """Walk the ladder. Returns a dict, never a bare string.

    `legend_is_material` lets the caller pass the figure-extraction stage's own
    legend decision (which is evidence-based and already correct) so this
    function does not have to re-derive it.
    """
    mats = [m for m in (materials or []) if m]
    single = len(set(mats)) == 1

    def out(material, level, evidence, candidates=None, reason=None):
        return {"material": material, "scope_level": level, "evidence": evidence,
                "candidates": candidates or [], "ambiguity_reason": reason,
                "multi_material_paper": len(set(mats)) > 1}

    # 1. the legend names the material outright
    if legend_is_material:
        return out(legend_is_material, "series_legend",
                   "series label %r is one of this paper's materials" % series_label)
    lab = _named(series_label, mats)
    if len(lab) == 1:
        return out(lab[0], "series_legend", "series label %r" % series_label)

    # 2. this PANEL's own caption clause. A multi-panel caption routinely gives
    #    one material per panel ("Raman spectra of (a) WSx and (b) TiSx films"),
    #    so the whole caption names several and the panel clause names one. The
    #    panel is narrower than the figure and therefore ranks above it.
    pan_hits = _named(panel_clause, mats)
    if len(pan_hits) == 1:
        return out(pan_hits[0], "panel_caption_clause",
                   " ".join((panel_clause or "").split())[:220])

    # 3. the caption names exactly one of this paper's materials.
    #    Skipped when this figure assigns materials PER PANEL: the caption then
    #    describes several panels at once, and letting a panel inherit from it
    #    gave panel (a), a WSx figure, the TiS2 named in panel (b)'s clause.
    cap_hits = _named(caption, mats)
    if panel_assigns_materials:
        return out(None, "unresolved", None, sorted(set(cap_hits or mats)),
                   "this figure names a different material per panel and this "
                   "panel's clause names none; a figure-level material would be "
                   "another panel's")
    if len(cap_hits) == 1:
        return out(cap_hits[0], "figure_caption",
                   " ".join((caption or "").split())[:220])

    # 4. the scout's own per-figure note
    dw_hits = _named(drill_why, mats)
    if len(dw_hits) == 1:
        return out(dw_hits[0], "figure_scout_note",
                   " ".join((drill_why or "").split())[:200])

    # 5. body text linked to this figure
    bd_hits = _named(body, mats)
    if len(bd_hits) == 1:
        return out(bd_hits[0], "figure_body",
                   " ".join((body or "").split())[:220])

    # 6. the paper only ever deposits one thing
    if single:
        return out(mats[0], "paper_single_material",
                   "the paper reports exactly one material")

    # 7. refuse. Candidates are kept so the ambiguity is inspectable.
    cands = sorted(set(cap_hits or dw_hits or bd_hits or mats))
    if not mats:
        return out(None, "unresolved", None, [], "the paper names no material")
    return out(None, "unresolved", None, cands,
               "multi-material paper (%s) with no figure-level evidence naming "
               "exactly one; material is NOT assigned by list order" %
               ", ".join(sorted(set(mats))))


def consistent(material, precursor, coreactant):
    """Does the precursor carry the metal the material claims?

    A deliberately weak check: it only reports a contradiction it can prove from
    element symbols, and stays silent (True) whenever it cannot. Its purpose is
    to catch a TiO2 film credited to TMA, not to validate coordination
    chemistry.
    """
    if not material or not precursor:
        return (True, None)
    metals = re.findall(r"[A-Z][a-z]?", material)
    metals = [m for m in metals if m not in ("O", "N", "S", "C", "H")]
    if not metals:
        return (True, None)
    metal = metals[0]
    # the precursor must mention the film's metal, unless it is a known
    # metal-free co-reagent spelling that legitimately omits it
    if re.search(r"(?<![a-z])" + re.escape(metal) + r"(?![a-z])", precursor):
        return (True, None)
    # Most precursors are named, not formulated: "tris(...)erbium(III)" and
    # "tert-butylferrocene" carry their metal as a WORD, so a symbol-only check
    # reports 47 contradictions that are all spelling.
    NAME = {
        "Al": ("alumin",), "Ti": ("titan",), "Zr": ("zircon",), "Hf": ("hafn",),
        "Zn": ("zinc",), "Mo": ("molybden",), "W": ("tungst", "wolfram"),
        "Ru": ("ruthen",), "Sn": ("stann", "tin("), "Y": ("yttri",),
        "Er": ("erbi",), "Ba": ("bari",), "Li": ("lithi",), "Fe": ("iron", "ferr"),
        "Ir": ("iridi",), "Pt": ("platin",), "Bi": ("bismuth",), "Te": ("tellur",),
        "Si": ("silic", "silan", "silyl"), "Ni": ("nickel",), "Co": ("cobalt",),
        "Cu": ("copper", "cupr"), "Ta": ("tantal",), "Nb": ("niob",),
        "Ga": ("galli",), "In": ("indi",), "Mg": ("magnes",), "La": ("lanthan",),
    }
    low = precursor.lower()
    if any(n in low for n in NAME.get(metal, ())):
        return (True, None)
    ALIAS = {"Al": ("TMA", "AlMe3", "DMAI", "TEA"), "Zn": ("DEZ", "DEZn"),
             "Ti": ("TTIP", "TDMAT", "TEMAT"), "Hf": ("TDMAH", "TEMAH"),
             "Zr": ("TDMAZ", "TEMAZ"), "Si": ("BDEAS", "BTBAS", "3DMAS"),
             "Mo": ("MoCl5",), "W": ("WF6",)}
    if any(a.lower() == precursor.strip().lower() for a in ALIAS.get(metal, ())):
        return (True, None)
    return (False, "material %s contains %s but precursor %r names neither the "
                   "symbol nor the element" % (material, metal, precursor))
