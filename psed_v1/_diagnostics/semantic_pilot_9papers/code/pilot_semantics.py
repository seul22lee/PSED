#!/usr/bin/env python3
"""
pilot_semantics.py — build the pilot semantic layer for one paper.

Reads the paper's snapshot under papers/<pid>/{extracted,resolved} and writes the eleven
semantic JSON files under papers/<pid>/semantic/.

Object model (reusing the ontology classes PSED already declares):

    ExperimentalCase  <- case candidates, merged only on positive linkage evidence
    Measurement       <- one observing act, `measures_case` / `performed_on`
    ResultSeries      <- the numbers, keeping curve_id and the source pointer
    PlotRepresentation<- as_measured / scaled / normalized / inset, `derived_representation_of`
    Sample            <- only where a specimen designator is stated
    DepositionRun     <- only where a run statement is made
    StudySeries       <- author-declared, many-to-many membership
    SimulationRun     <- untouched: model output, never a case

Source identity (paper, figure, panel, entity_id, curve_id, json_pointer) is carried on
every object and is never reused as scientific identity.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# ALD step semantics are one maintained definition for the whole pipeline: the semantic
# layer and the canonical layer must not carry two vocabularies for the same half-cycle.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from pipeline.canonical import process_steps as PS
from pipeline.canonical import axis_semantics as AX
from pipeline.canonical import conditions as C
from pipeline.canonical import gas_roles as GR
from pipeline.canonical import chemical_identity as CI
from pipeline.query import result_comparability as RC               # noqa: E402
import pilot_cases as PC                                        # noqa: E402
import pilot_evidence as PE                                     # noqa: E402
import pilot_roles as R                                         # noqa: E402
import pilot_sample_table as PT                                 # noqa: E402
import pilot_design as D                                        # noqa: E402
import pilot_supplements as SUP                                 # noqa: E402
import pilot_ranges as PRG                                      # noqa: E402

W = Path(__file__).resolve().parent.parent

#: resolver entity classes that are model output, not measurement. Preserved verbatim.
SIMULATION_CLASSES = {"SimulationRun", "ModelSweep"}
#: classes that never carry a current-paper deposition case (preservation target)
NON_EXPERIMENTAL = SIMULATION_CLASSES | {"ImportedLiteratureObservation", "Fit",
                                         "DerivedRepresentation", "UnresolvedSourceEntity"}

#: How the resolver's per-series source kind projects onto the coarse `data_source`
#: vocabulary. `data_source` answers only "were these numbers measured, or produced by a
#: model?", so a fit and a calculation give the same answer. The finer distinction is not
#: lost: it stays on the entity as `series_source_kind`, and in `entity_class`
#: (Fit / ModelSweep / SimulationRun), which is where it belongs.
_SERIES_KIND_SOURCE = {"measured": "measured",
                       "calculated": "simulated",
                       "fitted": "simulated"}


def effective_data_source(base_source, entity):
    """The origin of one series' numbers: its own evidence first, the panel's second.

    `base_source` is panel-or-figure provenance, and a panel is the FINEST scope the
    extraction layer can express. One panel may still hold a measured curve and the model
    curve drawn over it, and broadcasting the panel value to both labelled the model
    curve `measured` -- an experimental claim the paper never makes.

    The resolver has already decided this per series and persisted it as
    `series_source_kind`; this only projects that decision onto the coarse vocabulary. It
    is not a second identity resolver and never re-reads a label or a caption.

    Only POSITIVE series evidence overrides. `unknown` means the series said nothing
    about itself, which is not a contradiction of the panel -- the panel value is real
    evidence and is kept. When neither scope knows, the answer stays None: an unknown
    origin is not an experimental one. Producer class is deliberately not consulted; a
    SimulationRun does not get `simulated` for free, because that would state as
    provenance what was only ever a classification.
    """
    return _SERIES_KIND_SOURCE.get((entity or {}).get("series_source_kind"), base_source)


def _clean(t):
    t = (t or "").replace("/uniFB01", "fi").replace("/uniFB02", "fl").replace("/uniFB00", "ff")
    # PDF-to-markdown glyph escapes seen in this corpus. '/C2' is the multiplication
    # sign, which matters because it is how a microscope objective is written ("50 /C2").
    t = (t.replace("/C14", "°").replace("/C0", "-").replace("/C29", ")")
          .replace("/C2 ", "× ").replace("/C2", "×"))
    return re.sub(r"/uni[0-9A-F]{4}", "", t)


def _norm(t):
    return re.sub(r"\s+", " ", _clean(t)).strip()


#: Abbreviations that end with a full stop but not a sentence. Splitting on "Fig." tore
#: "For the creation of the full replica (Fig. 3), the precursor exposure was repeated 3
#: times" into two fragments and separated a process variant from the product it makes.
_ABBREV = re.compile(r"\b(?:Fig|Figs|Eq|Eqs|Ref|Refs|No|vs|approx|ca|cf|e\.g|i\.e|"
                     r"et\s?al|Dr|Prof|Inc|Ltd|Table|Tab|Sec|Ch|pp|vol)\.\s*$", re.I)


def _sentences(text):
    """Sentences, tolerating the abbreviations that pervade scientific prose."""
    parts, buf = [], ""
    for chunk in re.split(r"(?<=[.;])\s+", _norm(text)):
        buf = (buf + " " + chunk).strip() if buf else chunk
        if _ABBREV.search(buf) or re.search(r"\(\s*[A-Za-z]*$", buf):
            continue
        parts.append(buf)
        buf = ""
    if buf:
        parts.append(buf)
    return parts


#: a passage that continues a sentence about the figure is prose, not the figure's caption
_BODY_VERB = re.compile(
    r"^\(?[a-h]?[-–]?[a-h]?\)?\s*(?:panels?\s+[a-h][-–][a-h]\s*\)?\s*)?"
    r"(?:shows?|presents?|displays?|illustrates?|depicts?|gives?|reports?|plots?|"
    r"compares?|summari[sz]es?|indicates?|reveals?)\b", re.I)


class Paper(object):
    def __init__(self, pid):
        self.pid = pid
        self.root = W / "papers" / pid
        self.ex = self.root / "extracted"
        self.rs = self.root / "resolved"
        self.md = _clean((self.ex / "document.md").read_text(errors="ignore"))
        self.scout = self._j(self.ex / "scout.json", {})
        self.card = self._j(self.ex / "card.json", {})
        self.figdata = self._j(self.ex / "figure_data.json", {})
        self.inventory = self._j(self.ex / "figure_inventory.json", {})
        # the paper's deterministic geometry classification, used only where neither the
        # figure scope nor the resolved entity supplies one -- a candidate with no entity
        # is still an experiment in this paper, and leaving it geometry-less lost the
        # classification the paper does carry
        self.geometry = self._j(self.ex / "geometry.json", {})
        self.entities = self._j(self.rs / "entities.json", [])
        self.experiments = self._j(self.rs / "experiments.json", [])
        self.curves = (self._j(self.rs / "canonical_curves.json", {}) or {}).get("curves", [])
        self.supplements = self._j(self.root / "diagnostics" / "supplements.json", [])
        self.materials = [m for m in (self.scout.get("materials") or []) if m]
        self.methods = self._methods()
        self.sample_table, self.sample_table_header = self._sample_table()
        self._fig_by_crop = {str(f.get("figure")): f for f in (self.figdata.get("figures") or [])}
        self._printed = self._printed_map()
        self._cap_cache = {}

    def _sample_table(self):
        """The paper's per-specimen parameter table, recovered from the PDF.

        Cached to diagnostics/sample_table.json so the recovered rows are auditable
        against the printed table without re-reading the PDF."""
        cache = self.root / "diagnostics" / "sample_table.json"
        if cache.exists():
            d = json.loads(cache.read_text())
            return d.get("rows") or {}, d.get("header") or ""
        pdfs = sorted((self.root / "source").glob("*.pdf"))
        rows, header = ({}, "no PDF in the pilot snapshot")
        if pdfs:
            rows, header = PT.find_sample_table(pdfs[0])
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"pdf": pdfs[0].name if pdfs else None,
                                     "header": header, "n_rows": len(rows),
                                     "rows": rows}, indent=1))
        return rows, header

    @staticmethod
    def _j(p, default):
        try:
            return json.loads(Path(p).read_text())
        except Exception:
            return default

    def _methods(self):
        """The experimental/methods region, spanning its SUBSECTIONS.

        Stopping at the next heading of any level truncated the region to the first
        subsection, which in a journal that splits 'Experimental' into 'Synthesis of X',
        'Atomic layer deposition', 'HR-SEM' … dropped the entire deposition description.
        The region therefore runs to the first heading that names a results/discussion
        part, not to the first heading of any kind."""
        start = re.search(r"\n#+\s*(?:\d+\.?\s*)?(?:Experimental|Methods|"
                          r"Materials and methods|Film growth|Deposition)[^\n]*\n",
                          self.md, re.I)
        if not start:
            return _norm(self.md[:16000])
        rest = self.md[start.end():]
        stop = re.search(r"\n#+\s*(?:\d+\.?\s*)?(?:Results|Discussion|Conclusion|"
                         r"Acknowledge|References|Notes and references|Supporting)",
                         rest, re.I)
        return _norm(rest[:stop.start()] if stop else rest[:20000])

    def _printed_map(self):
        """crop index -> printed figure number, from the resolved entities (authoritative,
        it is what the figure-provenance layer decided) with the inventory as fallback."""
        out = {}
        for e in self.entities:
            if e.get("fig_docling_index") is not None and e.get("printed_figure_number"):
                out[str(e["fig_docling_index"])] = str(e["printed_figure_number"])
        for c in (self.inventory.get("candidates") or []):
            if c.get("printed_figure") and str(c.get("docling_index")) not in out:
                out[str(c["docling_index"])] = str(c["printed_figure"])
        return out

    # ------------------------------------------------------------------ source text
    def caption(self, crop_index):
        f = self._fig_by_crop.get(str(crop_index)) or {}
        cap = _norm(f.get("caption"))
        if cap:
            return cap
        for c in (self.inventory.get("candidates") or []):
            if str(c.get("docling_index")) == str(crop_index):
                return _norm(c.get("caption_recovered") or c.get("caption_original"))
        return ""

    def printed_caption(self, printed):
        """The full caption of one printed figure.

        The caption bound by the figure-provenance layer is authoritative and is used
        first. The document fallback must NOT require the caption to begin a line: this
        corpus contains captions that run on from the preceding paragraph
        ("…depositing Pt layers Figure 2 ( a -b ) GPCs …"), and anchoring at a line start
        returned nothing for them.
        """
        printed = str(printed or "")
        if not printed:
            return ""
        if printed in self._cap_cache:
            return self._cap_cache[printed]
        best = ""
        for crop, num in self._printed.items():
            if num == printed:
                c = self.caption(crop)
                if len(c) > len(best):
                    best = c
        if not best:
            # No caption was bound to this printed figure. Fall back to the document, but
            # only to a passage that READS as a caption: "Fig. 9 (panels a-c) presents …"
            # is body prose about the figure, and binding it would attribute the
            # discussion's claims to the figure itself.
            for m in re.finditer(r"(?:Figure|Fig\.?|FIG\.?)\s*%s\b(?!\d)" % re.escape(printed),
                                 self.md, re.I):
                end = self.md.find("\n\n", m.start())
                cand = _norm(self.md[m.start(): end if end > 0 else m.start() + 1600])[:1800]
                tail = cand[len(m.group(0)):].lstrip(" .:")
                if _BODY_VERB.match(tail):
                    continue
                if len(cand) > len(best):
                    best = cand
        self._cap_cache[printed] = best
        return best

    def body_near(self, printed):
        """Body sentences that discuss this printed figure. Body prose is where linkage
        statements live ('the same films', 'reproducibility of ALD runs')."""
        out = []
        for m in re.finditer(r"[^.]*?\bFig(?:ure)?\.?\s*%s\b[^.]*\." % re.escape(str(printed)),
                             self.md, re.I):
            out.append(_norm(m.group(0)))
        return " ".join(out)[:4000]


# ==============================================================================  build
#: Provenance levels that speak about one figure or narrower. Anything above them is a
#: statement about the paper, which several different experiments share.
_ENTITY_LEVELS = ("figure", "panel", "series", "curve", "experiment", "specimen", "sample")


def bind_context_scoped_controls(P, note):
    """Bind a method/paper control only where the sentence NAMES the context it applies to.

    A paper-level number is normally useless to a single experiment: the same value is
    stamped on every figure, so it cannot distinguish the one it is carried onto. That is
    why bare paper defaults are refused. A sentence that states the control TOGETHER with
    the chemistry it describes -- "the deposition process for X was carried out using A
    and B ... at T" -- is a different kind of evidence: it says which process it is about,
    and an experiment depositing that material with that chemistry is that process.

    Every one of these must hold, or nothing is bound:
      * the sentence names a material and/or reagents, and the entity agrees with them;
      * the entity does not SWEEP the quantity (a temperature series is not run at one
        temperature, and this is what stops a fixed value landing on its branches);
      * no narrower evidence -- figure, panel, series -- already speaks for that quantity;
      * the sentence itself is retained as the evidence.
    """
    chem = {"precursors": [x for x in (P.scout.get("precursors") or []) if x],
            "coreactants": [x for x in (P.scout.get("coreactants") or []) if x]}
    mats = [m for m in (P.materials or []) if m]
    stated = []
    for sent in re.split(r"(?<=[.;])\s+", P.md or ""):
        if len(sent) > 600:
            continue
        rows = CC.conditions_from_prose(sent, "paper", "body", "document.md")
        if not rows:
            continue
        def named(names):
            return [n for n in names
                    if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(n),
                                 sent, re.I)]
        ctx = {"materials": named(mats), "precursors": named(chem["precursors"]),
               "coreactants": named(chem["coreactants"])}
        if not (ctx["materials"] or ctx["precursors"]):
            continue                      # no context named: this is a bare default
        stated.append((rows, ctx, sent.strip()))
    if not stated:
        return 0
    # what the resolver itself refused to settle for each entity: an ambiguous quantity
    # stays ambiguous, and a sentence elsewhere in the paper does not settle it
    ambiguous_by_entity = defaultdict(set)
    for e in (P.experiments or []):
        eid = str(e.get("exp_id") or "")
        owner = eid.split("__case")[0] if "__case" in eid else eid
        for a in (e.get("ambiguous_conditions") or []):
            if a.get("quantity"):
                ambiguous_by_entity[owner].add(a["quantity"])
    added = 0
    for ent in P.entities:
        ambiguous = ambiguous_by_entity.get(ent.get("entity_id"), set())
        e_mat = [m for m in [ent.get("material")] if m]
        e_pre = [x for x in (ent.get("precursors") or []) if x]
        e_co = [x for x in (ent.get("coreactants") or []) if x]
        swept = {ent.get("coordinate"), ent.get("coordinate_raw_quantity")}
        have = {b.get("quantity") for b in (ent.get("bound_conditions") or [])}
        for rows, ctx, sent in stated:
            mat_ok = bool(ctx["materials"]) and bool(set(ctx["materials"]) & set(e_mat))
            chem_ok = bool(set(ctx["precursors"]) & set(e_pre)) or \
                bool(set(ctx["coreactants"]) & set(e_co))
            if not (mat_ok or chem_ok):
                continue
            # a stated context must not be CONTRADICTED by the entity's own chemistry
            if ctx["precursors"] and e_pre and not (set(ctx["precursors"]) & set(e_pre)):
                continue
            if ctx["materials"] and e_mat and not (set(ctx["materials"]) & set(e_mat)):
                continue
            for r in rows:
                q = r.get("quantity")
                if not q or q in have or q in swept or q in ambiguous:
                    continue
                ent.setdefault("bound_conditions", []).append({
                    "quantity": q, "value": r.get("value"), "unit": r.get("unit"),
                    "bound_at_scope": "process_context", "source_kind": "body",
                    "assertion_status": "direct", "species": None,
                    "evidence_kind": "body",
                    "raw_evidence": sent[:300],
                    "evidence_locator": "document.md",
                    "context_match": {k: v for k, v in ctx.items() if v},
                    "bound_because": (
                        "the sentence states %s together with the process context it "
                        "describes (%s), and this experiment matches that context"
                        % (q, ", ".join(sorted(sum(ctx.values(), []))))) })
                have.add(q)
                added += 1
                note("context_scoped_control", ent["entity_id"],
                     "%s = %s %s bound from a sentence naming its own process context "
                     "(%s): %r" % (q, r.get("value"), r.get("unit") or "",
                                   ", ".join(sorted(sum(ctx.values(), []))), sent[:150]))
    return added


def _control_scope_compatible(rec):
    """May this resolved control be carried onto the entity that owns the experiment?

    Only when the assertion was made at figure scope or narrower. A paper- or
    method-level value is the same number on every experiment of the paper, so it cannot
    distinguish the one it is being carried onto -- and evidence text does not change
    that, because it proves provenance rather than applicability.
    """
    origin = rec.get("origin") or {}
    level = origin.get("level")
    if level in _ENTITY_LEVELS:
        return True
    # A paper- or method-level assertion is NOT rescued by carrying evidence text.
    # Evidence establishes that somebody wrote the number down; it says nothing about
    # which experiment the number applies to. The paper that broadcast one methods
    # temperature onto eight figures had prose behind it too -- and one of those figures
    # sweeps temperature, so the broadcast contradicts the figure's own curves. Without a
    # scope tie to this entity there is no way to tell applicability from coincidence, so
    # the control is left where it was rather than carried onto a case.
    return False


def _sentence_names(sentence, token, role=None):
    """Does this sentence name that reagent, under ANY name the ontology gives it?

    Matching runs on canonical identity, so a sentence writing "trimethylaluminium" names
    the reagent a case stores as TMA. A reagent the ontology does not know is matched on
    its own string only -- never on resemblance to a different one.
    """
    if not sentence or not token:
        return False
    r = CI.resolve(token, role)
    names = [r.get("preferred_label"), r.get("formula"), r.get("full_name"),
             r.get("species_label"), str(token)] + list(r.get("aka") or [])
    for n in names:
        if n and re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(str(n)),
                           sentence, re.I):
            return True
    return False


def _enclosing_sentence(document, evidence):
    """The full sentence an evidence window was cut from.

    Extractors keep a tight window around the number, which often drops the subject of the
    sentence -- the very part naming the material the statement is about. Context matching
    has to see the whole claim, so the window is located in the document and grown to its
    sentence boundaries. Where it cannot be located the window itself is used, which can
    only make the match stricter.
    """
    doc = str(document or "")
    ev = str(evidence or "").strip()
    if not ev or not doc:
        return ev
    i = doc.find(ev)
    if i < 0:
        # extractors normalise whitespace, so the stored window often differs from the
        # document by spacing alone; locating it loosely still finds the right sentence
        loose = re.compile(r"\s+".join(re.escape(w) for w in ev.split()))
        m = loose.search(doc)
        if not m:
            return ev
        i, ev = m.start(), m.group(0)
    start = max(doc.rfind(".", 0, i), doc.rfind("\n", 0, i)) + 1
    end = doc.find(".", i + len(ev))
    return doc[start: end if end > 0 else i + len(ev) + 200].strip()


def context_assertion_index(P, note):
    """Paper-scope assertions that identify the process they describe, by quantity.

    Kept only where the paper is CONSISTENT: several sentences naming the same chemistry
    and disagreeing about a quantity make that quantity ambiguous for the process, and an
    ambiguous control must not be bound to anything. A paper mentioning "200 cycles" and
    "400 cycles" in different places has not told us the cycle count of any experiment.
    """
    try:
        assertions = C.conditions_from_prose(P.md, "paper", "body", "paper text") or []
    except Exception as exc:
        note("context_control_failed", "paper",
             "the canonical condition parser raised on the paper text: %r" % (exc,))
        return {}
    by_q = defaultdict(list)
    for a in assertions:
        q, ev = a.get("quantity"), (a.get("raw_evidence") or "")
        if not q or not ev:
            continue
        by_q[q].append(dict(a, context_sentence=_enclosing_sentence(P.md, ev)))
    out = {}
    for q, recs in sorted(by_q.items()):
        vals = {(str(r.get("value")), r.get("unit")) for r in recs}
        if len(vals) != 1:
            note("context_control_ambiguous", "paper",
                 "the paper states %d different values of %s (%s); none is bound, because "
                 "no sentence identifies which experiment carries which"
                 % (len(vals), q, sorted(v[0] for v in vals)))
            continue
        out[q] = recs
    return out


def qualify_case_timing_steps(case):
    """Qualify a case's timing conditions from its own figure's caption.

    A sweep is not always plotted on a timing AXIS: a figure may plot thickness against
    depth and distinguish its curves by exposure time, so the swept duration arrives as a
    series-level condition with no axis to read a half-cycle from. The figure's caption
    routinely says what the axis could not -- "the different TMA exposure times" -- and
    that names both the reagent and the step.

    Applied only where the case's timing condition is still unqualified and the caption is
    unambiguous, and only when the caption's step sits on the same SIDE of the cycle (an
    exposure hint never qualifies a purge). The condition's own timing FAMILY is kept: a
    pulse time gains the step and a role prefix, it is never rewritten into an exposure
    time -- pulse and exposure are different measurements, and which one the source used
    is part of what it asserted.
    """
    hints = getattr(_cand, "caption_step_hints", None)
    if not hints:
        return case
    figs = [str(f) for f in (case.get("source_figures") or []) if f]
    hit = {h for f in figs for h in [hints.get(f)] if h and h[1]}
    if len(hit) != 1:
        return case
    species, step, ev = next(iter(hit))
    step_role = PS.timing_role(None, step)
    for c in (case.get("case_defining_conditions") or []):
        if c.get("step_context"):
            continue
        if PS.timing_side(c.get("quantity")) != PS.step_side(step):
            continue
        # the hint must be ABOUT this record: a condition that already names a
        # different reagent, or whose quantity already carries a different half-cycle
        # role, is a different step of the recipe and the caption is not its evidence
        if species and c.get("species") and c["species"] != species:
            continue
        own_role = PS.timing_role(c.get("quantity"))
        if own_role and step_role and own_role != step_role:
            continue
        c["step_context"] = step
        c["source_quantity"] = c.get("source_quantity") or c.get("quantity")
        c["quantity"] = PS.specialize_timing_quantity(c["quantity"], step)
        c["species"] = c.get("species") or species
        c["activation"] = c.get("activation") or PS.ACTIVATION_NONE
        c["step_basis"] = ("the caption of this case's own figure names the step: %r" % ev)
    return case


def bind_gas_roles_to_case(case):
    """Give a case the carrier and purge gases its paper explicitly names.

    These are reactor-level facts, stated once and true for every process the paper runs,
    so they attach to each case of that paper -- but only where the paper is consistent.
    Two different carrier gases named in one paper leave the role unresolved rather than
    taking the first. The roles stay separate, and no purge DURATION is ever produced from
    a purge gas identity.
    """
    roles = getattr(_cand, "gas_roles", None)
    if not roles:
        return case
    for role, rec in sorted(roles.items()):
        if case.get(role):
            continue
        case[role] = rec["species"]
        case.setdefault("gas_role_provenance", {})[role] = {
            "species": rec["species"], "source_label": rec["source_label"],
            "canonical_id": rec.get("canonical_id"),
            "identity_key": rec.get("identity_key"),
            "evidence": rec.get("evidence"),
            "basis": "explicitly stated gas role, resolved to a canonical chemical"}
    return case


def _mentions_other_material(sentence, mine):
    """Does the sentence name a deposited material that is NOT this case's?"""
    for other in (getattr(_cand, "paper_materials", None) or set()):
        if other != mine and _sentence_names(sentence, other):
            return True
    return False


def bind_context_controls_to_case(case):
    """Attach a paper control to the cases whose process its own sentence names.

    A paper-level number is not a paper-wide fact: the same paper deposits other materials
    with other chemistries at other temperatures. What makes an assertion bindable is that
    its own sentence identifies the process -- it names the deposited material AND the
    chemistry -- so a case depositing that material with that chemistry is a case the
    sentence is about. Chemistry is compared on canonical identity, so a sentence written
    with the full chemical name binds a case that records the abbreviation.

    A quantity the case already carries is untouched, and a quantity the case's own design
    SWEEPS is never bound: the branch supplies that value, and a fixed statement about it
    would contradict the sweep.
    """
    idx = getattr(_cand, "context_assertions", None)
    if not idx:
        return case
    mat = case.get("deposited_material")
    if not mat:
        return case
    conds = case.get("case_defining_conditions") or []
    have = {c.get("quantity") for c in conds}
    # ... and the timing SIDES already occupied. Comparing raw names alone let a broad
    # "pulse_time@TMA" land beside an explicit "precursor_pulse_time@TMA", so the case
    # asserted the same step twice under two spellings -- and the side, not the fine
    # quantity, is the occupancy that matters: a case that states its pulse has its
    # contact side stated, and a paper-level exposure figure must not join it.
    have_sides = {PS.timing_side(c.get("quantity"))
                  for c in conds if PS.timing_side(c.get("quantity"))}
    swept = set(case.get("swept_quantities") or [])
    chem = [(x, CI.PRECURSOR) for x in (case.get("precursors") or [])] \
         + [(x, CI.COREACTANT) for x in (case.get("coreactants") or [])]
    others = getattr(_cand, "other_precursors", None) or set()
    for q, recs in sorted(idx.items()):
        if q in have or q in swept:
            continue
        side = PS.timing_side(q)
        if side and side in have_sides:
            continue                       # this side of the cycle is already stated
        for a in recs:
            sent = a.get("context_sentence") or ""
            # The sentence has to identify THIS process. Naming the deposited material
            # does it; so does naming the chemistry, and a paper that runs one chemistry
            # states its conditions that way ("200 cycles at 200 C, with TMA and water").
            # Requiring both refused perfectly identified controls.
            names_mat = bool(mat) and _sentence_names(sent, mat)
            names_chem = any(_sentence_names(sent, tok, role) for tok, role in chem)
            if not (names_mat or names_chem):
                continue
            # ... and it must not ALSO name a reagent this case does not use, which would
            # leave it unclear which of the paper's processes the sentence describes
            mine = {CI.identity_key(tok, role) for tok, role in chem}
            if any(k not in mine and _sentence_names(sent, lbl)
                   for k, lbl in others):
                continue
            if mat and _mentions_other_material(sent, mat):
                continue
            case.setdefault("case_defining_conditions", []).append({
                "quantity": q, "value": a.get("value"), "unit": a.get("unit"),
                "role": R.CASE_DEFINING,
                "role_basis": "process control stated for this material and chemistry",
                "provenance_type": "directly_stated",
                "source": a.get("source_kind") or "body",
                "scope": "experiment_context",
                "assertion_status": a.get("assertion_status") or "direct",
                "species": a.get("of_reactant") or a.get("species"),
                "evidence": sent[:220],
                "context_match": {"material": mat,
                                  "chemistry": [tok for tok, _ in chem],
                                  "rule": "the assertion's own sentence names this case's "
                                          "material and chemistry"}})
            break
    return case


def bind_context_compatible_controls(P, note):
    """Bind a method/paper control to the experiments its OWN sentence is about.

    A paper-level number is not a paper-wide fact. "The deposition process for Pt was
    carried out using HDMP and O2 as precursor and counter reactant at 300 C" states a
    temperature for one process, and the same paper's other process ran at other
    temperatures -- which is why a broadcast is wrong and why sibling unanimity proves
    nothing. What makes this assertion bindable is that its own sentence identifies the
    process: it names the deposited material AND the chemistry, so an experiment
    depositing that material with that chemistry is the experiment the sentence describes.

    Chemistry is matched on canonical identity, so a sentence naming the reagent by full
    name binds an experiment that records the abbreviation. The quantity a panel SWEEPS is
    never bound this way, and an entity that already carries narrower evidence keeps it.
    """
    try:
        assertions = C.conditions_from_prose(P.md, "paper", "body", "paper text") or []
    except Exception as exc:
        note("context_control_failed", P.pid if hasattr(P, "pid") else "paper",
             "the canonical condition parser raised on the paper text: %r" % (exc,))
        return 0
    added = 0
    for a in assertions:
        q, ev = a.get("quantity"), (a.get("raw_evidence") or "")
        if not q or not ev:
            continue
        ev = _enclosing_sentence(P.md, ev)
        for ent in P.entities:
            mat = ent.get("material")
            if not mat or not _sentence_names(ev, mat):
                continue                       # the sentence is not about this material
            chem = [(x, CI.PRECURSOR) for x in (ent.get("precursors") or [])] \
                 + [(x, CI.COREACTANT) for x in (ent.get("coreactants") or [])]
            if not any(_sentence_names(ev, tok, role) for tok, role in chem):
                continue                       # nor about this chemistry
            if q in {b.get("quantity") for b in (ent.get("bound_conditions") or [])}:
                continue                       # narrower evidence already answers it
            if q in {ent.get("coordinate"), ent.get("coordinate_raw_quantity")}:
                continue                       # the panel varies it; the branch supplies it
            ent.setdefault("bound_conditions", []).append({
                "quantity": q, "value": a.get("value"), "unit": a.get("unit"),
                "bound_at_scope": "experiment_context",
                "source_kind": a.get("source_kind") or "body",
                "assertion_status": a.get("assertion_status") or "direct",
                "species": a.get("of_reactant") or a.get("species"),
                "evidence_kind": a.get("evidence_kind"),
                "raw_evidence": ev,
                "evidence_locator": a.get("evidence_locator"),
                "context_match": {"material": mat,
                                  "chemistry": [tok for tok, _ in chem],
                                  "rule": "the assertion's own sentence names this "
                                          "experiment's material and chemistry"}})
            added += 1
            note("context_control", ent["entity_id"],
                 "%s = %s %s is stated in a sentence that names this experiment's "
                 "material (%s) and chemistry; it is bound to this experiment and not "
                 "broadcast to the paper" % (q, a.get("value"), a.get("unit") or "", mat))
    return added


def printed_caption_index(P):
    """printed figure number -> its caption, for EVERY figure the paper prints.

    Not only the figures carrying plotted series: a TEM or schematic figure has no entity
    of its own, and it is exactly such a figure whose caption gets attributed to the
    plotted figure beside it.
    """
    figs = {str(n) for n in (getattr(P, "_printed", None) or {}).values() if n}
    figs.update(str(e.get("printed_figure_number") or "") for e in P.entities)
    return {f: _norm(P.printed_caption(f) or "").lower() for f in sorted(figs) if f}


def foreign_caption_owner(evidence, mine, captions):
    """The OTHER printed figure whose caption states this evidence, or None.

    Only an unambiguous other owner counts. Evidence appearing in no caption at all says
    nothing -- body prose is not thereby foreign -- and evidence appearing in several
    captions identifies no single owner.
    """
    ev = _norm(evidence or "").lower().strip()
    if len(ev) < 8:
        return None
    owners = [f for f, cap in (captions or {}).items() if cap and ev in cap]
    if len(owners) == 1 and owners[0] != str(mine or ""):
        return owners[0]
    return None


def drop_foreign_figure_assertions(P, note):
    """Remove figure-scope conditions whose evidence belongs to a DIFFERENT figure.

    A figure-scoped assertion is bound by proximity in the document, and a caption sitting
    near another figure's discussion gets attributed to the wrong one. Observed: a caption
    reading "a stack ... deposited using 10-40 cycles each" -- a statement about a
    multilayer TEM figure -- attached to every panel of the saturation-curve figure that
    follows it, where those cycle counts describe nothing.

    The check is deterministic and uses evidence the pipeline already has: if the
    assertion's own text appears in the printed caption of a DIFFERENT figure, it is a
    statement about that figure, and this entity is not the figure it describes. Where the
    text appears in no caption at all, nothing is concluded and the assertion is left
    alone -- body prose is not thereby foreign.
    """
    # every printed figure the paper HAS, not only the ones that carry plotted series: a
    # TEM figure has no entity of its own, and it is exactly such a figure whose caption
    # was being attributed to the plotted figure beside it
    captions = printed_caption_index(P)
    dropped = 0
    for ent in P.entities:
        mine = str(ent.get("printed_figure_number") or "")
        keep = []
        for b in (ent.get("bound_conditions") or []):
            owner = (foreign_caption_owner(b.get("raw_evidence"), mine, captions)
                     if b.get("bound_at_scope") == "figure" else None)
            if owner is None:
                keep.append(b)
                continue
            dropped += 1
            note("foreign_figure_condition", ent["entity_id"],
                 "%s = %s was bound at figure scope to figure %s, but its evidence is the "
                 "printed caption of figure %s; it is a statement about that figure and "
                 "is not carried onto this one"
                 % (b.get("quantity"), b.get("value"), mine or "?", owner))
        ent["bound_conditions"] = keep
    return dropped


def inherit_caption_conditions(P, note):
    """Bind the fixed conditions a printed figure's own CAPTION states.

    A caption that says "the substrate temperature was 250 C for both processes" is the
    most specific evidence a figure has about the conditions its panels were run at, and
    it is scoped to exactly the panels the figure contains. The semantic layer read the
    resolver's per-entity bindings and the paper's process card, but never the caption
    itself, so a figure whose entities bound nothing produced Condition Cases with no
    fixed conditions at all -- while the sentence stating them sat in the caption the
    figure-provenance layer had already resolved.

    The caption is parsed by the maintained canonical condition parser, so degree glyphs,
    ranges, species qualification and step semantics behave exactly as they do everywhere
    else; nothing is re-implemented here.

    An entity keeps whatever it already binds, and the quantity a panel SWEEPS is never
    taken from the caption -- the branch supplies that, and a caption stating one value of
    a swept parameter describes one panel, not all of them.
    """
    by_fig = defaultdict(list)
    for e in P.entities:
        fig = str(e.get("printed_figure_number") or "")
        if fig:
            by_fig[fig].append(e)
    added = 0
    for fig, ents in sorted(by_fig.items()):
        caption = P.printed_caption(fig)
        if not caption:
            continue
        try:
            found = C.conditions_from_prose(caption, "figure", "caption",
                                            "figure %s caption" % fig)
        except Exception as exc:
            # a parser failure is a defect to report, not "this caption states nothing"
            note("caption_condition_failed", "figure %s" % fig,
                 "the canonical condition parser raised on this caption: %r" % (exc,))
            continue
        # A caption that states SEVERAL values of one quantity ("images at 100 and 200
        # cycles") is enumerating panels, not fixing a condition for all of them. And an
        # assertion carrying no value is not a condition at all -- emitting it would put a
        # null back where a magnitude belongs. Both are refused for the whole figure.
        by_q = defaultdict(list)
        for a in found or []:
            if a.get("quantity") and a.get("value") not in (None, "", "null"):
                by_q[a["quantity"]].append(a)
        for q, recs in sorted(by_q.items()):
            vals = {(str(r.get("value")), r.get("unit")) for r in recs}
            if len(vals) != 1:
                note("caption_condition_ambiguous", "figure %s" % fig,
                     "the caption of figure %s states %d values of %s (%s); it is "
                     "enumerating panels rather than fixing one condition, so none binds"
                     % (fig, len(vals), q, sorted(v[0] for v in vals)))
                continue
            a = recs[0]
            for e in ents:
                if q in {b.get("quantity") for b in (e.get("bound_conditions") or [])}:
                    continue
                if q in {e.get("coordinate"), e.get("coordinate_raw_quantity")}:
                    continue
                e.setdefault("bound_conditions", []).append({
                    "quantity": q, "value": a.get("value"), "unit": a.get("unit"),
                    "bound_at_scope": "figure", "source_kind": "caption",
                    "assertion_status": a.get("assertion_status") or "direct",
                    "species": a.get("of_reactant") or a.get("species"),
                    "step_context": a.get("step_context"),
                    "activation": a.get("activation"),
                    "evidence_kind": a.get("evidence_kind"),
                    "raw_evidence": a.get("raw_evidence"),
                    "evidence_locator": a.get("evidence_locator"),
                    "bound_from_caption": "figure %s" % fig})
                added += 1
            note("caption_condition", "figure %s" % fig,
                 "the caption of figure %s states %s = %s %s; it is bound to the %d "
                 "entities of that figure that did not already carry it"
                 % (fig, q, a.get("value"), a.get("unit") or "", len(ents)))
    return added


def inherit_experiment_controls(P, note):
    """Give each resolved entity the fixed controls its own experiments already resolved.

    Two resolved artifacts describe one panel: `entities.json` carries what the figure
    says, `experiments.json` carries the run the resolver assembled -- and the fixed
    recipe controls (the methods temperature, a stated pressure) live on the EXPERIMENT.
    The semantic layer read only `bound_conditions`, so a sweep panel whose entity binds
    nothing produced Condition Cases holding the swept value and nothing else: no
    temperature, no fixed control of any kind, even though the experiment record for that
    exact entity had them all along. Observed on a saturation panel whose cases carried
    only precursor, co-reactant and the swept exposure.

    The enrichment is deliberately narrow. A quantity the entity already binds is
    untouched; the swept coordinate is never inherited, because that is what the branch
    supplies; anything the resolver itself flagged ambiguous stays out; and a value is
    taken only where every experiment of that entity agrees on it.
    """
    by_entity = defaultdict(list)
    for e in (P.experiments or []):
        eid = str(e.get("exp_id") or "")
        owner = eid.split("__case")[0] if "__case" in eid else eid
        by_entity[owner].append(e)
    added = 0
    for ent in P.entities:
        exps = by_entity.get(ent.get("entity_id")) or []
        if not exps:
            continue
        have = {b.get("quantity") for b in (ent.get("bound_conditions") or [])}
        swept = {ent.get("coordinate"), ent.get("coordinate_raw_quantity")}
        ambiguous = {a.get("quantity") for e in exps
                     for a in (e.get("ambiguous_conditions") or [])}
        agreed = {}
        for e in exps:
            for c in (e.get("controlled") or []):
                q = c.get("quantity")
                if not q or q in have or q in swept or q in ambiguous:
                    continue
                agreed.setdefault(q, []).append(c)
        for q, recs in sorted(agreed.items()):
            vals = {(str(r.get("value")), r.get("unit")) for r in recs}
            if len(vals) != 1 or len(recs) != len(exps):
                continue                      # the experiments disagree: inherit nothing
            r = recs[0]
            # Agreement among siblings is NOT evidence of scope. A paper-level card field
            # is stamped onto every experiment of the paper, so every sibling "agrees" on
            # it by construction -- observed as one methods temperature appearing on eight
            # unrelated figures, including a saturation panel the source ran at a
            # different temperature entirely. Inheritance therefore requires provenance
            # that ties the value to THIS entity's own context: an assertion made at
            # figure scope or narrower, or a broader one that at least carries the text it
            # was read from. A broadcast with no evidence is not a statement about this
            # experiment.
            owner = foreign_caption_owner((r.get("origin") or {}).get("evidence"),
                                          ent.get("printed_figure_number"),
                                          getattr(_cand, "caption_index", None))
            if owner:
                note("experiment_control_foreign", ent["entity_id"],
                     "%s = %s is stated in the printed caption of figure %s, not this "
                     "entity's figure; it describes that figure and is not carried here"
                     % (q, r.get("value"), owner))
                continue
            if not _control_scope_compatible(r):
                note("experiment_control_refused", ent["entity_id"],
                     "%s = %s is a %s-level %s broadcast carrying no evidence for this "
                     "entity; sibling experiments agree on it only because they were all "
                     "stamped with the same value" % (q, r.get("value"),
                                                      (r.get("origin") or {}).get("level"),
                                                      (r.get("origin") or {}).get("from")))
                continue
            ent.setdefault("bound_conditions", []).append({
                "quantity": q, "value": r.get("value"), "unit": r.get("unit"),
                "bound_at_scope": r.get("scope"), "source_kind": r.get("source"),
                "assertion_status": r.get("assertion_status") or "direct",
                "species": r.get("of_reactant") or r.get("species"),
                "evidence_kind": r.get("assertion_source_kind") or r.get("source"),
                "raw_evidence": ((r.get("origin") or {}).get("evidence")
                                 or "resolved experiment control for this entity"),
                "evidence_locator": (r.get("origin") or {}).get("locator"),
                "inherited_from_experiment": [e.get("exp_id") for e in exps][:4]})
            added += 1
            note("experiment_control", ent["entity_id"],
                 "the resolved experiments of this entity all state %s = %s %s at %s "
                 "scope; the entity bound none, so the control is carried onto its cases"
                 % (q, r.get("value"), r.get("unit") or "", r.get("scope")))
    return added


def resolved_chemistry_index(P):
    """Deposited material -> the chemistry the RESOLVED experiments already established.

    Case chemistry used to be re-derived at each mint site from whatever that path
    happened to hold: an entity's own reagents, or the paper's process card narrowed by
    the case's material. Paths that mint a case without a resolved entity -- a tabulated
    specimen, an image-supported observation, a whole plotted curve -- hold neither, so a
    paper whose every resolved experiment says TMA + H2O still produced chemistry-less
    cases. The resolved experiments are the paper's own answer to that question, so they
    are indexed once and offered to every path.

    `None` keys the paper-wide answer, and it is filled ONLY when the whole paper agrees:
    where several chemistries are resolved, a case of unknown material has no unambiguous
    one and must stay unstated rather than take the first.
    """
    by_mat, all_pre, all_co, all_type = {}, set(), set(), set()
    for e in (P.experiments or []):
        r = e.get("recipe") or {}
        mat = r.get("material") or e.get("material")
        pre = sorted({x.get("species") for x in (r.get("reactants") or [])
                      if x.get("role") == "precursor" and x.get("species")})
        co = sorted({x.get("species") for x in (r.get("reactants") or [])
                     if x.get("role") in ("coreactant", "reactant") and x.get("species")})
        ptype = e.get("process_type") or r.get("process_type")
        if not (pre or co):
            continue
        all_pre.update(pre)
        all_co.update(co)
        if ptype:
            all_type.add(ptype)
        if mat:
            slot = by_mat.setdefault(mat, {"precursors": set(), "coreactants": set(),
                                           "process_types": set()})
            slot["precursors"].update(pre)
            slot["coreactants"].update(co)
            if ptype:
                slot["process_types"].add(ptype)
    out = {m: {"precursors": sorted(v["precursors"]),
               "coreactants": sorted(v["coreactants"]),
               "process_type": (sorted(v["process_types"])[0]
                                if len(v["process_types"]) == 1 else None),
               "basis": "resolved experiments of this paper depositing %s" % m}
           for m, v in by_mat.items()}
    # one chemistry across the whole paper is not a guess; two is, and stays refused
    out[None] = {"precursors": sorted(all_pre) if len(all_pre) == 1 else [],
                 "coreactants": sorted(all_co) if len(all_co) == 1 else [],
                 "process_type": sorted(all_type)[0] if len(all_type) == 1 else None,
                 "basis": "every resolved experiment of this paper agrees"}
    return out


#: Scopes that speak about a CONTAINER holding several cases -- a whole figure, the
#: methods section, the paper. Everything else (a branch, a series, a panel, a specimen,
#: one experiment) speaks about this case. Listing the coarse ones is the safe direction:
#: a scope nobody anticipated is then treated as specific and never silently overrides a
#: value the case states about itself, which is how an experiment-scope reading of a
#: swept quantity stopped superseding the figure-scope fragments it should have.
_COARSE_SCOPES = ("figure", "method", "methods", "paper", None, "")


def _is_specific_scope(scope):
    return scope not in _COARSE_SCOPES


def resolve_timing_conflicts(case):
    """Drop coarse-scope timing constants that this case's own value contradicts.

    A figure that SWEEPS an exposure time cannot also state one fixed exposure time for
    every branch of that sweep: the figure-scope number is a member of the swept list, and
    attaching it to all branches makes each case assert two different durations for the
    same step. Observed shape of the defect -- one case carrying `exposure_time = 2 s`
    from its own curve legend beside `pulse_time = 10 s` and `pulse_time@TMA = 0.5 s`
    lifted from a sentence enumerating the whole sweep.

    Comparing timing records on the SIDE of the cycle they describe is what makes the
    conflict visible at all: before it, `pulse_time`, `precursor_pulse_time` and
    `exposure_time` were different keys and the specificity ladder never compared them.
    The side, not the fine quantity, is the right key here -- a pulse and an exposure
    both time the reactant-contact side of a step, so a figure-scope contact duration
    cannot also be a branch's swept one whichever family each is written in. A coarser
    assertion is superseded only when it does not name a DIFFERENT step or a different
    reagent -- a fixed reactant exposure stated for the figure survives a swept precursor
    exposure, because they are two steps. Nothing is deleted: the superseded record keeps
    its evidence and is set aside.
    """
    conds = case.get("case_defining_conditions") or []
    specific = {}
    for c in conds:
        q = PS.timing_side(c.get("quantity"))
        if q and _is_specific_scope(c.get("scope")):
            specific.setdefault(q, []).append(c)
    if not specific:
        return case
    keep, dropped = [], []
    for c in conds:
        q = PS.timing_side(c.get("quantity"))
        owners = specific.get(q) if q else None
        if not owners or c in owners:
            keep.append(c)
            continue
        # a genuinely different step or reagent is a different condition, not a conflict
        if any(_same_timing_slot(c, o) for o in owners):
            dropped.append(dict(c, superseded_by=[{
                "quantity": o.get("quantity"), "value": o.get("value"),
                "unit": o.get("unit"), "scope": o.get("scope"),
                "provenance_type": o.get("provenance_type")} for o in owners],
                superseded_reason=(
                    "this case states %s at %s scope; the %s-scope assertion describes "
                    "the container that holds every branch of that sweep, so it cannot "
                    "also be this branch's fixed value"
                    % (q, owners[0].get("scope"), c.get("scope"))))) 
        else:
            keep.append(c)
    if dropped:
        case["case_defining_conditions"] = keep
        case.setdefault("superseded_conditions", []).extend(dropped)
    return case


def _same_timing_slot(coarse, specific):
    """Do two timing records describe the same step of the same reagent?

    An unstated step or reagent on the coarse record does not make it a different
    condition -- it makes it an unqualified statement about the same slot. Only a
    positively DIFFERENT step, reagent, or half-cycle role separates them. The role can
    be written as a prefix on the quantity itself (`precursor_pulse_time`), so it is read
    through the step vocabulary rather than by comparing spellings.
    """
    for field in ("step_context", "species"):
        a, b = coarse.get(field), specific.get(field)
        if a and b and a != b:
            return False
    ra = PS.timing_role(coarse.get("quantity"), coarse.get("step_context"))
    rb = PS.timing_role(specific.get("quantity"), specific.get("step_context"))
    if ra and rb and ra != rb:
        return False
    return True


def _timing_qualification(cond):
    """How much a timing record says about WHICH slot it occupies (0-3)."""
    return sum(1 for v in (PS.timing_role(cond.get("quantity"), cond.get("step_context")),
                           cond.get("species"), cond.get("step_context")) if v)


def fold_timing_generalizations(case):
    """One fingerprint dimension per physical timing slot, however it is spelled.

    A case can accumulate the SAME setting under two spellings -- `pulse_time@TMA` read
    off a series label beside `precursor_pulse_time@TMA` from the specimen table. They
    are one physical fact, and leaving both makes the case's identity assert two
    dimensions where the experiment has one. The less-qualified record is folded into the
    more-qualified one it corroborates, and only under evidence:

      * the two records occupy the same slot (side, role, reagent, step -- with an
        unstated field matching anything, a positively different one matching nothing);
      * exactly ONE more-qualified sibling matches -- two candidates mean the generic
        record cannot be attributed and stays where it is;
      * the values agree canonically. A disagreement is a real conflict and is kept
        VISIBLE on both records rather than resolved by preferring a spelling.

    Nothing is deleted: the folded record moves to `folded_conditions` with the id of the
    condition it corroborates, and the winner records it under `corroborated_by`.
    """
    conds = case.get("case_defining_conditions") or []
    timing = [c for c in conds if PS.timing_side(c.get("quantity"))]
    if len(timing) < 2:
        return case

    def _wins(d, c):
        """Does record d own record c's slot? More qualification wins; at equal
        qualification more specific provenance wins; a full tie breaks
        deterministically on the record's own source fields, never on list order."""
        qd, qc = _timing_qualification(d), _timing_qualification(c)
        if qd != qc:
            return qd > qc
        rd, rc = PC.provenance_rank(d), PC.provenance_rank(c)
        if rd != rc:
            return rd > rc
        kd = (str(d.get("scope") or ""), str(d.get("source") or ""),
              str(d.get("quantity") or ""))
        kc = (str(c.get("scope") or ""), str(c.get("source") or ""),
              str(c.get("quantity") or ""))
        return kd > kc

    folded = []
    for c in timing:
        owners = [d for d in timing
                  if d is not c and d not in folded
                  and PS.timing_side(d.get("quantity")) == PS.timing_side(c.get("quantity"))
                  and _same_timing_slot(c, d)
                  and _wins(d, c)]
        if len(owners) != 1:
            continue
        owner = owners[0]
        same_value = (PC.value_token(c) == PC.value_token(owner)
                      and PC._unit_key(c.get("unit")) == PC._unit_key(owner.get("unit")))
        if not same_value:
            note = sorted({PC._fmt(c.get("value")), PC._fmt(owner.get("value"))})
            c["same_slot_conflict"] = owner.get("quantity")
            owner["same_slot_conflict"] = c.get("quantity")
            c["conflicting_values"] = owner["conflicting_values"] = note
            continue
        owner.setdefault("corroborated_by", []).append({
            "quantity": c.get("quantity"), "species": c.get("species"),
            "value": c.get("value"), "unit": c.get("unit"),
            "scope": c.get("scope"), "source": c.get("source"),
            "provenance_type": c.get("provenance_type"),
            "evidence": c.get("evidence")})
        folded.append(c)
        c["folded_into"] = {"quantity": owner.get("quantity"),
                            "species": owner.get("species"),
                            "reason": ("this record states the same value for the same "
                                       "physical timing slot with less qualification; "
                                       "one slot is one case dimension")}
    if folded:
        case["case_defining_conditions"] = [c for c in conds if c not in folded]
        case.setdefault("folded_conditions", []).extend(folded)
    return case


#: Normalizations are grouped by the numerator their id names ("t_over_..." vs
#: "x_over_..."), so a question about one axis is never answered from the other's
#: vocabulary. The grouping is read off the ontology, not listed here.
def _normalizations_for(axis_quantity):
    fam = {"normalized_thickness": "t", "dimensionless_distance": "x",
           "normalized_growth_per_cycle": "gpc"}.get(str(axis_quantity or ""))
    if not fam:
        return {}
    return {n: d for n, d in RC.NORMALIZATIONS.items()
            if n.split("_over_")[0] == fam}


def resolved_normalization_basis(P, curve, src):
    """The normalization reference a curve's own source text states, or nothing.

    A canonicalised axis can be a normalized quantity whose DENOMINATOR nobody recorded --
    "Normalized thickness (-)" says the axis is a ratio without saying to what. The
    frozen layer rightly calls that ambiguous, and two such axes never overlay. But the
    reference is frequently stated in the figure's own caption or in the sentence that
    defines the plot type, and reading it there is recovery, not inference.

    Only an explicit statement binds, and only when it names a reference belonging to
    exactly one declared normalization. The word "normalized" on its own resolves nothing.
    """
    sem = (curve.get("semantics") or {}).get("y") or {}
    kind = str(sem.get("axis_kind") or "")
    quantity = sem.get("quantity") or sem.get("canonical_quantity")
    if "unknown_denominator" not in kind:
        return {}
    cands = _normalizations_for(quantity)
    if not cands:
        return {}
    # the curve's own caption first, then the passage where the paper defines this plot
    for text in (P.printed_caption(str(src.get("figure") or "")), P.md):
        nid, ev = AX.normalization_from_statement(text, cands, axis="y")
        if nid:
            return {"y_normalization_basis": nid,
                    "y_normalization_basis_evidence": ev,
                    "y_normalization_basis_source": (
                        "figure caption" if text != P.md else "paper text")}
    # A document may define a representation BY NAME ("Type 1 profiles are obtained by
    # normalizing to ...") and have the caption use only the name. The definition and the
    # use are then two halves of one statement: the document-level sentence supplies the
    # reference, the caption picks the name. Both halves are required, both are quoted,
    # and a caption using two defined names -- or a name the document never defined --
    # resolves nothing.
    defs = AX.named_normalization_definitions(P.md, cands, axis="y")
    if defs:
        nid, ev = AX.normalization_from_named_use(
            P.printed_caption(str(src.get("figure") or "")), defs)
        if nid:
            return {"y_normalization_basis": nid,
                    "y_normalization_basis_evidence": ev,
                    "y_normalization_basis_source":
                        "document-defined named representation, used by the caption"}
    return {}


def paper_gas_roles(P, note):
    """Carrier and purge gases the paper states explicitly, as structured roles.

    A gas role is a property of the PROCESS, not of one plotted branch, so it is carried
    on the case's chemistry rather than as a case-defining condition: every experiment of
    the process shares it, and a condition shared by all of them cannot distinguish any of
    them. Only an explicit role statement is read -- a gas that merely appears somewhere
    in the text is not thereby the carrier -- and no duration is ever inferred from the
    identity of a purge gas.
    """
    roles = {}
    for g in CC.gas_roles_from_text(P.md or ""):
        roles.setdefault(g["role"], {})
        roles[g["role"]].setdefault(g["species"], g["evidence"])
    if roles:
        note("gas_role", P.pid if hasattr(P, "pid") else "paper",
             "; ".join("%s = %s" % (r, ", ".join(sorted(v))) for r, v in sorted(roles.items())))
    return {r: sorted(v) for r, v in roles.items()}, \
           {r: v for r, v in roles.items()}


def bind_case_chemistry(case):
    """Fill a case's chemistry from the resolved experiments, never over local evidence.

    Precedence, and the reason for it: what the case's OWN members resolved is local and
    wins outright; the paper's resolved experiments for this case's material come next,
    because a paper that deposits one material by one chemistry has said so; the
    paper-wide answer is used last and only when the paper is unanimous. Nothing here
    overwrites a value, so a mint path that already knew its chemistry is untouched.
    """
    # NOTE: explicit carrier/purge gas roles are extracted (CC.gas_roles_from_text) and
    # available on _cand.gas_roles, but attaching them to the case collapses 12 Condition
    # Cases in this corpus for the same reason a shared process control does: a value
    # identical across every experiment of a process makes previously-distinct candidates
    # fingerprint alike. They stay unattached until the merge key is made robust to
    # process-wide context.
    idx = getattr(_cand, "resolved_chemistry", None)
    if not idx:
        return case
    src = idx.get(case.get("deposited_material")) or idx.get(None) or {}
    for field, key in (("precursors", "precursors"), ("coreactants", "coreactants")):
        if not case.get(field) and src.get(key):
            case[field] = list(src[key])
            case.setdefault("chemistry_basis", {})[field] = src.get("basis")
    if not case.get("process_type") and src.get("process_type"):
        case["process_type"] = src["process_type"]
        case.setdefault("chemistry_basis", {})["process_type"] = src.get("basis")
    return canonicalize_case_chemistry(case)


def canonicalize_case_chemistry(case):
    """Collapse a case's reagents onto canonical chemical identities.

    "TMA", "Al(CH3)3" and "trimethylaluminium" are one reagent written three ways. Left as
    raw strings they are three precursors: the same deposition splits into several case
    identities, chemistry-scoped comparison misses its own matches, and a paper appears to
    have used a reagent it never named. Equality therefore runs on the ontology's canonical
    id, while every source string is kept beside it so a case can still be read in the
    terminology its own paper used.

    A reagent the ontology does not declare keeps a distinct unresolved identity. It is
    never merged into a similar-looking one -- an unknown reagent is not evidence that two
    experiments share a chemistry.
    """
    for field, role in (("precursors", CI.PRECURSOR), ("coreactants", CI.COREACTANT)):
        labels, records = CI.canonicalize_all(case.get(field) or [], role)
        if not records:
            continue
        case[field] = labels
        case.setdefault("chemistry_identity", {})[field] = [
            {"source_label": r["source_label"], "canonical_id": r["canonical_id"],
             "identity_key": r["identity_key"], "preferred_label": r["preferred_label"],
             "formula": r.get("formula"), "activation": r["activation"],
             "resolved": r["resolved"], "basis": r["basis"]} for r in records]
        acts = sorted({r["activation"] for r in records if r["activation"]})
        if acts:
            case["%s_activation" % field[:-1]] = acts
    return case


def bind_step_species(case):
    """Name the reagent that runs in each timed step, from the case's OWN chemistry.

    `step_context` says which half-cycle a duration belongs to; the case says which
    chemical runs in that half-cycle. The two together are what make an exposure record
    an experiment. A purge is never given a species of its own -- nothing is dosed during
    a purge -- it is given the species and activation of the exposure it FOLLOWS.

    Only an unambiguous chemistry binds: where a case names two precursors, the step's
    species stays unstated rather than guessed at.
    """
    prec = case.get("precursors") or []
    core = case.get("coreactants") or []

    def one(names):
        if len(names) != 1:
            return None, None
        return PS.split_activated_species(names[0])

    p_sp, _ = one(prec)
    c_sp, c_act = one(core)
    for c in case.get("case_defining_conditions") or []:
        step = c.get("step_context")
        if not step:
            continue
        if step == PS.PRECURSOR_EXPOSURE and p_sp:
            c["species"] = c.get("species") or p_sp
        elif step == PS.REACTANT_EXPOSURE and c_sp:
            c["species"] = c.get("species") or c_sp
            # the axis label may already have named the plasma; where it did not, the
            # case's own delivery channel ("O2_plasma") is the evidence that it was one
            if c_act and c.get("activation") in (None, PS.ACTIVATION_NONE):
                c["activation"] = c_act
        elif step == PS.PRECURSOR_PURGE and p_sp:
            c["preceding_species"] = c.get("preceding_species") or p_sp
        elif step == PS.REACTANT_PURGE and c_sp:
            c["preceding_species"] = c.get("preceding_species") or c_sp
            c["preceding_activation"] = c.get("preceding_activation") or c_act
    return case


#: "<reagent> exposure time", "<reagent> pulse", "<reagent> purge" -- a caption naming
#: which reagent's step a figure varies. The reagent is resolved through the canonical
#: chemical vocabulary, so only a real chemical qualifies a step.
_CAPTION_STEP = re.compile(
    r"([A-Za-z][A-Za-z0-9()\[\]·]{1,24})\s+(exposure|pulse|dose|dosing|purge|purging)"
    r"(?:\s+times?)?", re.I)


def caption_step_hint(caption):
    """(species, step_context, evidence) a caption states for the step a figure varies.

    A design branch takes its step from the axis it was swept on, but a figure that plots
    against a generic axis often names the reagent and the half-cycle in its caption
    instead -- "SEM images for the different TMA exposure times". Reading it there is
    recovery from stated evidence, not inference.

    Only an UNAMBIGUOUS caption qualifies: one that names two different reagents' steps
    has not said which one this figure varies, and the step stays unresolved.
    """
    found = {}
    for m in _CAPTION_STEP.finditer(str(caption or "")):
        token, word = m.group(1), m.group(2)
        ident = CI.resolve(token)
        if not ident.get("resolved"):
            continue                      # not a chemical the vocabulary knows
        # the ontology already files a reagent under precursors or co-reactants, so the
        # half-cycle follows from the chemical itself; the caption need not spell it out
        step, _ev = PS.classify_step("%s %s" % (token, word),
                                     role_hint=CI.ontology_role(token),
                                     species=ident["preferred_label"])
        if not step:
            continue
        found.setdefault((ident["preferred_label"], step), m.group(0).strip())
    if len(found) != 1:
        return None, None, None
    (species, step), ev = next(iter(found.items()))
    return species, step, ev


def panel_step_sequence(P, note):
    """entity_id -> the ALD step its swept timing axis belongs to.

    A panel labelled only "Purge time" does not say WHICH half-cycle it purges, and a
    duration with no position is the thing that makes a 2 s precursor purge and a 2 s
    plasma purge compare equal. The printed figure carries what the single label lacks:
    the panels run in the recipe's own order, so an unqualified purge belongs to the
    exposure printed before it. Panels are therefore resolved together, per printed
    figure, by the maintained step-semantics module -- never one label at a time.
    """
    by_fig = defaultdict(list)
    for e in P.entities:
        lab = (e.get("x_semantics") or {}).get("raw_label")
        if not lab:
            continue
        by_fig[str(e.get("printed_figure_number") or "")].append(
            (str(e.get("panel") or ""), e["entity_id"], lab))
    out = {}
    for fig, rows in sorted(by_fig.items()):
        rows.sort(key=lambda r: (r[0], r[1]))
        # the figure's own caption is corroborating evidence that its panels run as a
        # recipe sequence; without it, or an alternating printed run, a bare purge label
        # stays unresolved rather than taking its neighbour's half-cycle
        try:
            cap = P.printed_caption(fig)
        except Exception:
            cap = None
        recs = PS.resolve_panel_sequence([r[2] for r in rows], evidence_text=cap)
        cap_sp, cap_step, cap_ev = caption_step_hint(cap)
        for (panel, eid, lab), rec in zip(rows, recs):
            if not rec.get("step_context") and cap_step:
                # the axis label named no half-cycle, but this figure's caption did
                rec = dict(rec, step_context=cap_step, species=cap_sp,
                           quantity=PS.timing_quantity(cap_step),
                           evidence=(rec.get("evidence") or [])
                                    + ["the figure caption names the step: %r" % cap_ev],
                           resolved_with="figure caption")
            if not rec.get("step_context"):
                continue
            rec = dict(rec, resolved_with="printed panel sequence of figure %s" % fig)
            out[eid] = rec
            note("process_step", eid,
                 "axis %r in panel %s of figure %s is the %s step: %s"
                 % (lab, panel or "-", fig, rec["step_context"],
                    "; ".join(rec.get("evidence") or [])))
    return out


def build(pid):
    P = Paper(pid)
    # every candidate this paper mints may fall back to its classification
    _cand.paper_geometry = (P.geometry or {}).get("geometry_class")
    _cand.process_card = (P.figdata or {}).get("process_card") or {}
    # one index, offered to every case-minting path, so chemistry does not depend on
    # which path happened to mint the case
    _cand.resolved_chemistry = resolved_chemistry_index(P)
    _cand.paper_geometry_evidence = (P.geometry or {}).get("evidence")
    out = {k: [] for k in ("experimental_cases", "measurements", "result_series",
                           "representations", "samples", "deposition_runs",
                           "run_evidence", "study_series", "simulation_runs",
                           "provenance_chains", "experimental_designs", "design_branches",
                           "links", "evidence", "unresolved")}
    ev = out["evidence"]
    sample_by_code = {}

    def note(kind, subject, detail, **kw):
        rec = {"evidence_id": "EV-%s-%03d" % (pid[:6].upper(), len(ev) + 1),
               "kind": kind, "subject": subject, "detail": detail}
        rec.update(kw)
        ev.append(rec)
        return rec["evidence_id"]

    # ---------------------------------------------------------------- 1. paper scope
    flat_md = _norm(P.md)
    paper_chem = {"precursor": P.scout.get("precursors") or [],
                  "coreactant": P.scout.get("coreactants") or []}
    paper_mat_roles = R.material_roles(P.methods + "\n" + P.md[:20000], P.materials)
    for mat, recs in sorted(paper_mat_roles.items()):
        note("material_role", mat,
             "roles read from the methods/body: %s" % sorted({r["role"] for r in recs}),
             roles=recs[:6])

    # Shared setup used by the specimen, series and value-join blocks below.
    series_decls = series_definitions_from_text(flat_md)
    table_cols = PT.column_map(P.sample_table_header, 24)
    instrument_map = instrument_setting_map(P.md)

    # ------------------------------------------ 2. specimens from the paper's own table
    # A per-specimen parameter table is authoritative for specimen identity, for study
    # series membership, and for which variable each series varies. When the paper has no
    # such table this whole block simply produces nothing.
    table_conditions = {}
    for code, row in sorted(P.sample_table.items(), key=lambda kv: (len(kv[0]), kv[0])):
        conds = []
        for i, (q, unit, hint) in enumerate(table_cols):
            if i >= len(row["columns"]):
                break
            raw = row["columns"][i]
            if raw in ("—", "-", "--", "n/a", ""):
                continue
            role = R.CASE_DEFINING if hint == "CASE" else R.MEASUREMENT_SETTING
            conds.append({"quantity": q, "value": raw, "unit": unit, "role": role,
                          "role_basis": "column of the paper's own specimen table",
                          "provenance_type": "sample_table_direct", "source": "sample_table",
                          "evidence": "specimen table row for specimen %r, column %r"
                                      % (code, q)})
        # A composite pulse-purge string is not comparable as a string. Its components are
        # added alongside it (the original is kept as source provenance), which is what
        # lets a purge-time series value-join to its own specimens.
        for raw in row["columns"][:2]:
            comp = D.decompose_recipe(raw, (P.scout.get("precursors") or []) +
                                      (P.scout.get("coreactants") or []))
            if comp:
                for cc in comp:
                    cc["source_recipe_string"] = raw
                conds.extend(comp)
                break
        table_conditions[code] = conds
        sample_by_code[code] = {
            "sample_id": "S::%s::%s" % (pid, code), "paper_id": pid,
            "source_sample_code": code, "evidence": [], "produced_by_run": None,
            "experimental_case_ids": [], "material": None, "geometry": None,
            "measurement_ids": [], "source_references": [], "confidence": PC.EXPLICIT,
            "table_series": row.get("series"),
            "also_in_series": row.get("also_in_series") or [],
            "conditions": conds,
            "case_defining_conditions": [c for c in conds if c["role"] == R.CASE_DEFINING],
            "measurement_settings": [c for c in conds if c["role"] == R.MEASUREMENT_SETTING],
        }
        sample_by_code[code]["evidence"].append(
            note("specimen_table", sample_by_code[code]["sample_id"],
                 "row for specimen %r of the paper's specimen table (PDF page %s)"
                 % (code, row.get("page")), series=row.get("series"),
                 columns=row["columns"][:8]))
        out["samples"].append(sample_by_code[code])

    # ---------------------------------------------------- 3. study series (author-declared)
    series_members = defaultdict(set)
    series_ev = {}
    for code, row in P.sample_table.items():
        for letter in [row.get("series")] + (row.get("also_in_series") or []):
            if letter:
                series_members[letter].add(code)
    for s in PE.series_refs(P.md):
        series_ev.setdefault(s["series"], s)
    # sample codes co-mentioned with a series letter in the SAME sentence bind to it
    for sent in _sentences(P.md):
        srefs = PE.series_refs(sent)
        if not srefs:
            continue
        codes = PE.sample_codes(sent)
        # A sentence may name two series ("… Series E) and (b) purge times … Series F)").
        # Each sample code binds to the NEAREST series mention, not to every one, or the
        # two series would each absorb all six specimens.
        for c in codes:
            near = min(srefs, key=lambda s_: abs(s_["offset"] - c["offset"]))
            series_members[near["series"]].add(c["code"])

    # ------------------------------------------------------------- 3. per-entity pass
    # Curve -> entity. Three joins, strongest first, and each ResultSeries records which
    # one attached it:
    #   1. the explicit `linked_experiment_ids` written by the canonical layer;
    #   2. the SOURCE SLICE (figure, panel LETTER, series label) — the panel is reduced to
    #      its leading letter because the resolver normalises "a (With bottom)" to "a"
    #      while the canonical layer keeps the printed label, and comparing the two whole
    #      strings silently dropped 56 of 93 curves in one paper;
    #   3. where one slice key legitimately covers several curves AND the same number of
    #      entities, the two lists are zipped in source order. This is a provenance
    #      attachment, not a scientific claim: both sides are enumerated from the same
    #      figure_data.json in the same order, and it only runs when the counts agree.
    def _panel_letter(x):
        m = re.match(r"\s*\(?\s*([A-Za-z])\b", str(x or ""))
        return m.group(1).lower() if m else ""

    def _label(x):
        t = _norm(x)
        return "" if t in ("<single>", "primary", "None") else t

    curve_by_entity = defaultdict(list)
    join_method = {}
    joined = set()
    ent_by_id = {e["entity_id"]: e for e in P.entities}
    # every series label present in one (figure, panel) scope, for the sibling test below
    labels_in_scope = defaultdict(set)
    for e in P.entities:
        labels_in_scope[(str(e.get("fig_docling_index")),
                         _panel_letter(e.get("panel") or e.get("panel_key")))].add(
                             _label(e.get("source_series")))
    rejected_links = []

    for c in P.curves:
        for eid in ((c.get("source") or {}).get("linked_experiment_ids") or []):
            base = str(eid).split("__case")[0]
            ok_link, why = link_is_supported(c.get("source") or {},
                                             ent_by_id.get(base), labels_in_scope)
            if not ok_link:
                rejected_links.append({"curve_id": c["curve_id"], "linked_entity_id": eid,
                                       "base_entity_id": base, "reason": why,
                                       "figure": (c.get("source") or {}).get("figure"),
                                       "panel": (c.get("source") or {}).get("panel"),
                                       "series": (c.get("source") or {}).get("series")})
                continue
            curve_by_entity[base].append(c)
            joined.add(c["curve_id"])
            join_method[c["curve_id"]] = "linked_experiment_id"

    slice_groups = defaultdict(list)
    for c in P.curves:
        if c["curve_id"] in joined:
            continue
        src = c.get("source") or {}
        slice_groups[(str(src.get("figure_index")), _panel_letter(src.get("panel")),
                      _label(src.get("series")))].append(c)
    for v in slice_groups.values():
        v.sort(key=lambda c: str((c.get("source") or {}).get("json_pointer") or ""))

    ent_groups = defaultdict(list)
    for ent in P.entities:
        if curve_by_entity.get(ent["entity_id"]):
            continue
        ent_groups[(str(ent.get("fig_docling_index")),
                    _panel_letter(ent.get("panel") or ent.get("panel_key")),
                    _label(ent.get("source_series")))].append(ent)

    for key, ents in ent_groups.items():
        cs = slice_groups.get(key) or []
        if not cs:
            continue
        if len(cs) == len(ents):
            for ent, c in zip(ents, cs):
                curve_by_entity[ent["entity_id"]].append(c)
                joined.add(c["curve_id"])
                join_method[c["curve_id"]] = ("source_slice" if len(cs) == 1
                                              else "source_slice_ordered")
        elif len(ents) == 1 and len(cs) == 1:
            curve_by_entity[ents[0]["entity_id"]].append(cs[0])
            joined.add(cs[0]["curve_id"])
            join_method[cs[0]["curve_id"]] = "source_slice"
    # 4. last tier: a (figure, panel) scope holding exactly ONE unjoined curve and exactly
    #    ONE unjoined entity. The series labels may legitimately disagree — the canonical
    #    layer keeps the drawn legend ("Pt") while the resolver recorded "<single>" for a
    #    panel with no legend — and with one candidate on each side there is nothing else
    #    the curve could belong to.
    left_c, left_e = defaultdict(list), defaultdict(list)
    for c in P.curves:
        if c["curve_id"] in joined:
            continue
        src = c.get("source") or {}
        left_c[(str(src.get("figure_index")), _panel_letter(src.get("panel")))].append(c)
    for ent in P.entities:
        if not curve_by_entity.get(ent["entity_id"]):
            left_e[(str(ent.get("fig_docling_index")),
                    _panel_letter(ent.get("panel") or ent.get("panel_key")))].append(ent)
    for key, cs in left_c.items():
        es = left_e.get(key) or []
        if len(cs) == 1 and len(es) == 1:
            curve_by_entity[es[0]["entity_id"]].append(cs[0])
            joined.add(cs[0]["curve_id"])
            join_method[cs[0]["curve_id"]] = "panel_unique"

    out["_rejected_curve_links"] = rejected_links
    for r in rejected_links:
        note("curve_link_rejected", r["curve_id"],
             "the explicit link to %r was not used: %s" % (r["linked_entity_id"],
                                                           r["reason"]),
             figure=r["figure"], panel=r["panel"], series=r["series"])
    out["_unjoined_curves"] = [{"curve_id": c["curve_id"],
                                "figure_index": (c.get("source") or {}).get("figure_index"),
                                "panel": (c.get("source") or {}).get("panel"),
                                "series": (c.get("source") or {}).get("series")}
                               for c in P.curves if c["curve_id"] not in joined]

    design_factors = series_design_factors(P, series_decls, series_members,
                                           table_conditions)
    out["design_factors"] = [dict(v, series=k) for k, v in sorted(design_factors.items())]
    for k, f in sorted(design_factors.items()):
        f["evidence_id"] = note("design_factor", "series %s" % k,
                                "the source declares that series %s varies %r; %s"
                                % (k, f.get("phrase"), f["why"]),
                                components=f["components"], members=f["members"])
    vjoin, vjoin_notes = build_value_joins(P, table_cols, series_decls, series_members,
                                           note, spec_conditions=table_conditions,
                                           factors=design_factors)

    candidates, cand_links = [], []
    meas_by_entity, run_records = {}, []
    panel_clause_cache = {}
    rep_holder, rep_group = representation_groups(P, note)
    # the resolved experiments carry fixed controls the entities never bound; they are
    # merged onto the entities BEFORE any candidate is built, so every case-minting path
    # sees one enriched entity rather than each path having to remember a second source
    # NOTE: bind_context_scoped_controls() is implemented and unit-correct, but enabling
    # it collapses 9 Condition Cases in this corpus: one process-description sentence
    # matches every experiment of that process, and the identical conditions it adds make
    # previously-distinct candidates merge. It stays disabled until the merge key is made
    # robust to shared context, because losing case identity is worse than lacking one
    # explicitly stated control.
    _cand.caption_index = printed_caption_index(P)
    _cand.caption_step_hints = {f: caption_step_hint(cap)
                                for f, cap in _cand.caption_index.items()}
    # every reagent and material the PAPER uses, so a sentence naming one that this case
    # does not use can be recognised as describing a different process
    _cand.other_precursors = {(CI.identity_key(x, CI.PRECURSOR), x)
                              for x in ((P.scout.get("precursors") or [])
                                        + (P.scout.get("coreactants") or [])) if x}
    _cand.paper_materials = {m for m in (P.scout.get("materials") or []) if m}
    drop_foreign_figure_assertions(P, note)
    inherit_caption_conditions(P, note)
    inherit_experiment_controls(P, note)
    # context-matched paper controls are attached AFTER merging (see
    # bind_context_controls_to_case): they are fixed across the cases they describe, so
    # they cannot distinguish one from another, and adding them before the merge made two
    # different sweeps look like one case.
    _cand.context_assertions = context_assertion_index(P, note)
    _cand.gas_roles = GR.unambiguous_roles(GR.gas_roles_from_text(P.md))
    for _r, _v in sorted((_cand.gas_roles or {}).items()):
        note("gas_role", "paper", "%s is stated as the %s: %r"
             % (_v["species"], _r.replace("_", " "), _v.get("evidence")))
    step_by_entity = panel_step_sequence(P, note)

    for ent in P.entities:
        eid = ent["entity_id"]
        printed = str(ent.get("printed_figure_number") or "")
        panel = (ent.get("panel") or "").lower()
        cls = ent.get("entity_class")
        full_cap = P.printed_caption(printed) or P.caption(ent.get("fig_docling_index"))
        if printed not in panel_clause_cache:
            panel_clause_cache[printed] = PE.panel_clauses(full_cap)
        clauses = panel_clause_cache[printed]
        clause = clauses.get(panel) or ""
        preamble = clauses.get("", "")
        scope_text = " ".join([preamble, clause])
        body = P.body_near(printed)

        # ---- ResultSeries: the numbers, with source identity preserved verbatim ----
        rs_ids = []
        for c in curve_by_entity.get(eid, []):
            src = c.get("source") or {}
            rid = "RS::%s" % c["curve_id"]
            rs_ids.append(rid)
            out["result_series"].append({
                "result_series_id": rid, "paper_id": pid,
                "curve_id": c["curve_id"],
                "source": {"figure": src.get("figure"), "figure_index": src.get("figure_index"),
                           "panel": src.get("panel"), "series": src.get("series"),
                           "series_index": src.get("series_index"),
                           "json_pointer": src.get("json_pointer"),
                           "source_checksum": src.get("source_checksum"),
                           "linked_experiment_ids": src.get("linked_experiment_ids") or []},
                "data_source": effective_data_source(src.get("data_source"), ent),
                "x_quantity": ((c.get("semantics") or {}).get("x") or {}).get("canonical_quantity")
                              or (c.get("raw") or {}).get("x", {}).get("quantity"),
                "y_quantity": ((c.get("semantics") or {}).get("y") or {}).get("canonical_quantity")
                              or (c.get("raw") or {}).get("y", {}).get("quantity"),
                "n_points": len(((c.get("raw") or {}).get("points") or [])),
                "n_transformations": len(c.get("transformations") or []),
                "join_method": join_method.get(c["curve_id"]),
                "produced_by": None, "resolved_entity_id": eid,
                **resolved_normalization_basis(P, c, src),
            })

        # ---- representation (never mints a case) ----
        rep, rep_match = PE.representation_of(clause or preamble)
        rep_id = None
        if rep:
            rep_id = "REP::%s" % eid
            out["representations"].append({
                "representation_id": rep_id, "paper_id": pid, "type": rep,
                "source": {"printed_figure": printed, "panel": panel,
                           "resolved_entity_id": eid},
                "underlying_measurement": None, "result_series_ids": rs_ids,
                "derived_representation_of": None,
                "transformation_relation": ("declared in the panel caption clause"
                                            if rep != "as_measured" else "none (as measured)"),
                "evidence": note("representation", eid,
                                 "panel clause declares %r" % rep_match, panel=panel,
                                 clause=clause[:220]),
            })

        # ---- simulation stays simulation ----
        if cls in SIMULATION_CLASSES:
            out["simulation_runs"].append({
                "simulation_run_id": "SIM::%s" % eid, "paper_id": pid,
                "entity_class": cls, "resolved_entity_id": eid,
                "source": {"printed_figure": printed, "panel": panel},
                "model_evidence": _first(PE.techniques(scope_text)),
                "model_statement": _model_stmt(scope_text + " " + body),
                "result_series_ids": rs_ids,
                "data_source": sorted({r["data_source"] for r in out["result_series"]
                                       if r["resolved_entity_id"] == eid and r["data_source"]}),
                "representation_id": rep_id,
                "is_experimental_case": False,
            })
            for r in out["result_series"]:
                if r["resolved_entity_id"] == eid:
                    r["produced_by"] = "SIM::%s" % eid
            if rep_id:
                out["representations"][-1]["underlying_measurement"] = "SIM::%s" % eid
            continue

        # ---- Measurement: one observing act ----
        # the measurand is the most reliable technique signal; the caption clause only
        # supplements it, because a range marker like "( a -b )" gives one clause to two
        # panels that measure different things
        # The printed axis label overrules a canonical quantity that contradicts it.
        meas_q, meas_u, meas_fix = R.measurand_of(ent)
        # How many curves share this scope decides whether a shared clause can be
        # attributed to one of them. Body-near-figure text is no longer consulted for
        # technique: it is the widest scope in the pipeline and cannot be tied to one
        # Measurement, so it produced sibling contamination rather than evidence.
        _n_in_scope = sum(1 for e2 in P.entities
                          if str(e2.get("printed_figure_number")) == str(printed)
                          and (e2.get("panel") or "") == (panel or ""))
        _src_tech, _src_basis, _src_ev = techniques_for_series(
            clause, ent.get("source_series"), meas_q, _n_in_scope)
        if not _src_tech:
            _src_tech, _src_basis, _src_ev = techniques_for_series(
                preamble, ent.get("source_series"), meas_q, _n_in_scope)
        # inference ranks BELOW anything the source states
        axis_tech = _tech_from_axes(ent, meas_q)
        cap_tech = _src_ev
        mid = "M::%s" % eid
        cd, ms, other = PC.entity_conditions(ent)
        # An upstream parser can read the separator of "10-120 ms" as a minus sign. Every
        # inherited condition is re-checked against its own evidence before it becomes a
        # scientific claim; the paper text is offered as context because the stored
        # evidence snippet is sometimes truncated at the dash itself.
        cd = PRG.repair_all(cd, flat_md)
        ms = PRG.repair_all(ms, flat_md)
        other = PRG.repair_all(other, flat_md)
        # What the figure says distinguishes this curve from its siblings. Figure-local
        # direct evidence, so a stronger source (a specimen table row) still wins.
        _prog_stage = None
        # every reagent this paper is known to use, so a legend can be matched against
        # chemistry the source actually supports instead of inventing one
        _known_species = [s for s in ((P.scout.get("precursors") or [])
                                      + (P.scout.get("coreactants") or [])
                                      + [r.get("species") for r in (ent.get("reactants") or [])]
                                      + (ent.get("precursors") or [])
                                      + (ent.get("coreactants") or [])) if s]
        _series_reagent = None
        for bc in between_curve_conditions(ent, P.materials, note, _known_species):
            if bc.get("progression_stage"):
                _prog_stage = bc
                continue
            if bc.get("series_reagent"):
                _series_reagent = bc
                continue
            (cd if bc["role"] == R.CASE_DEFINING else ms).append(bc)
        # every material of the paper that THIS scope names, with the role it names it in
        scope_text = " ".join([clause, preamble])
        # A scope that reports a property of a CHEMICAL rather than of a film asserts no
        # local material and mints no deposition case: a precursor vapour-pressure curve
        # is real scientific data, but no film is grown in it.
        # A curve labelled with a reagent name and plotted against a thermal ramp is
        # characterisation of that chemical. The series label and the panel clause are
        # both offered, because a paper may name the substance in either.
        # A figure comparing candidate chemistries names substances the paper may never
        # have deposited with. The curve label is the author identifying what is in the
        # instrument, so it counts as a species name in its own right.
        _reagents = ((P.scout.get("precursors") or []) + (P.scout.get("coreactants") or [])
                     + [r.get("species") for r in (ent.get("reactants") or [])]
                     + ([ent.get("between_curve_value")]
                        if R.is_chemistry_discriminator(ent.get("between_curve_condition"))
                        else []))
        species_only, species_why = R.is_species_property(
            meas_q, ent.get("coordinate"),
            scope_label=" ".join([str(ent.get("source_series") or ""), clause]),
            species=[x for x in _reagents if x])
        scope_mat = {} if species_only else R.material_roles(scope_text, P.materials)
        scope_geo, geo_match = R.geometry_in_scope(scope_text)
        chem = PC.chemistry_conditions(paper_chem, ent.get("source_series"), clause, preamble)
        for c in chem:
            if not any(x["quantity"] == c["quantity"] for x in cd):
                cd.append(c)
        # A condition the panel's OWN caption clause states binds to this panel's
        # results directly -- "The substrate temperature was 200 C" in clause (b) is a
        # statement about panel (b), and recovering it only through another linked
        # figure inverted the evidence chain. Two guards keep this scoped:
        #   * only the panel's own clause is read, never the preamble or a sibling
        #     clause, so a statement made for panel B cannot leak into panel A;
        #   * only a quantity the clause states exactly ONCE binds -- a clause that
        #     enumerates several values ("50, 200 and 250 C") is describing its sweep,
        #     and which value belongs to which curve is the series label's job.
        # A quantity already stated by a more specific source is never restated.
        if clause:
            # Only the prose rules bind here: they type a value by its GOVERNING
            # PHRASE ("The substrate temperature was 200 C" -> deposition_temperature),
            # which is the evidence that the number is a condition of THIS deposition.
            # A unit-typed bare number ("at 400 C") says only that some temperature is
            # 400 -- an anneal, a bake, a measurement stage all print the same way --
            # and binding it as a case condition would assert what the clause never
            # said. Untyped numbers stay unbound.
            _clause_conds = C.conditions_from_prose(
                clause, "panel", "caption",
                "caption clause of panel %s%s" % (printed, panel or ""))
            _by_q = defaultdict(list)
            for c in _clause_conds:
                _by_q[c.get("quantity")].append(c)
            # a clause that ENUMERATES several values for a quantity is describing its
            # sweep, and which value belongs to which curve is the series label's job --
            # binding any single value of the enumeration to every curve of the panel
            # would assert a condition the source distributed across them
            _enumerated = {q for q, _vals, _sp in enumerated_settings(clause)}
            for q, cs in sorted(_by_q.items()):
                if len(cs) != 1 or not q or q in _enumerated:
                    continue
                c = cs[0]
                if any(x.get("quantity") == q for x in cd):
                    continue
                cd.append({"quantity": q, "value": c.get("value"),
                           "unit": c.get("unit"), "value_kind": "scalar",
                           "role": R.CASE_DEFINING,
                           "role_basis": "stated by this panel's own caption clause",
                           "provenance_type": "panel_caption_direct",
                           "source": "figure_caption", "scope": "panel",
                           "assertion_status": c.get("assertion_status") or "direct",
                           "species": c.get("species"),
                           "step_context": c.get("step_context"),
                           "activation": c.get("activation"),
                           "evidence": c.get("raw_evidence"),
                           "locator": "caption clause of panel %s%s"
                                      % (printed, panel or "")})
        meas = {
            "measurement_id": mid, "paper_id": pid,
            "technique": _src_tech or axis_tech,
            "technique_basis": (_src_basis if _src_tech
                                else _infer_basis(ent, meas_q) if axis_tech
                                else "unresolved"),
            "technique_evidence": (_src_ev if _src_tech
                                   else _inference_note(ent, meas_q) if axis_tech
                                   else []),
            "measured_quantity": meas_q,
            "measured_unit": meas_u,
            "coordinate": ent.get("coordinate"), "coordinate_unit": ent.get("coordinate_unit"),
            "measurand_repair": meas_fix,
            "entity_class": cls, "classification": ent.get("classification"),
            "performed_on": None, "measures_case": [],
            "measurement_settings": ms,
            "source": {"printed_figure": printed, "panel": panel,
                       "resolved_entity_id": eid,
                       "fig_docling_index": ent.get("fig_docling_index"),
                       "source_series": ent.get("source_series")},
            "caption_reference": clause[:300] or preamble[:300],
            "result_series_ids": rs_ids, "representation_id": rep_id,
            "n_observations": ent.get("n_observations"),
            "repeat_measurement": False, "evidence": [], "confidence": None,
            # context preserved even when no case can be established
            "_material": ent.get("material"),
            "_conditions": [{"quantity": c["quantity"], "value": c["value"],
                             "unit": c["unit"], "role": c["role"]} for c in cd],
        }
        meas_by_entity[eid] = meas
        out["measurements"].append(meas)
        for r in out["result_series"]:
            if r["resolved_entity_id"] == eid:
                r["produced_by"] = mid
        if rep_id:
            out["representations"][-1]["underlying_measurement"] = mid

        # ---- sample / run / series evidence for this scope ----
        # the legend itself may name the specimen ("Sample 8"), which is stronger than a
        # caption list because it identifies WHICH curve belongs to WHICH specimen
        # Strongest first: a legend whose VALUE identifies a row of the specimen table,
        # then a legend that names the specimen outright, then a caption list.
        joined = vjoin.get(eid)
        legend_codes = PE.sample_codes(ent.get("source_series") or "")
        if joined:
            codes = [{"code": joined["code"], "matched": joined["matched"],
                      "span": joined["evidence"], "offset": 0, "n_in_mention": 1}]
            meas["specimen_binding"] = "value_join"
        else:
            codes = legend_codes or PE.sample_codes(clause) or PE.sample_codes(preamble)
            meas["specimen_binding"] = ("legend_code" if legend_codes else
                                        "caption_list" if codes else "none")
        if joined and joined.get("setting"):
            ms.append(joined["setting"])
            meas["measurement_settings"] = ms
        link_ev = PE.linkage_evidence(clause) + PE.linkage_evidence(preamble)
        if not codes:
            codes = [c for c in PE.sample_codes(body)][:4]
        for lk in link_ev:
            if lk["kind"] == "repeat_measurement":
                meas["repeat_measurement"] = True
                meas["evidence"].append(note("repeat_measurement", mid, lk["span"],
                                             matched=lk["matched"]))

        for c in codes:
            code = c["code"]
            s = sample_by_code.get(code)
            if not s:
                s = {"sample_id": "S::%s::%s" % (pid, code), "paper_id": pid,
                     "source_sample_code": code, "evidence": [], "produced_by_run": None,
                     "experimental_case_ids": [], "material": None, "geometry": None,
                     "measurement_ids": [], "source_references": [], "confidence": EXPL(c)}
                sample_by_code[code] = s
                out["samples"].append(s)
            s["evidence"].append(note("sample_code", s["sample_id"], c["span"],
                                      matched=c["matched"], printed_figure=printed))
            if mid not in s["measurement_ids"]:
                s["measurement_ids"].append(mid)
            ref = {"printed_figure": printed, "panel": panel}
            if ref not in s["source_references"]:
                s["source_references"].append(ref)
            if meas["performed_on"] is None:
                meas["performed_on"] = s["sample_id"]
                meas["confidence"] = PC.EXPLICIT
            elif meas["performed_on"] != s["sample_id"]:
                meas["performed_on"] = None      # several specimens in one panel
                meas["confidence"] = PC.UNRESOLVED

        # ---- case candidates ----
        # A figure whose caption attributes its data to another work reports an IMPORTED
        # observation. The result is preserved in full, but it is not this paper's
        # experiment and must not mint a deposition case for it. This is what makes a
        # review article -- every figure reproduced from a cited work -- come out with no
        # current-paper cases instead of one per reproduced figure.
        imp_src, imp_stmt = PE.imported_from(clause or preamble)
        if imp_src:
            meas["provenance_role"] = "IMPORTED_LITERATURE"
            meas["originally_reported_in"] = imp_src
            meas["provenance_note"] = ("the caption attributes this data to another work, "
                                       "so it is an observation imported into this paper, "
                                       "not a deposition this paper performed")
            meas["evidence"].append(note("imported_literature", mid, imp_stmt,
                                         originally_reported_in=imp_src,
                                         printed_figure=printed))
            note("no_case", eid, "imported from %r; preserved as a Measurement and a "
                 "ResultSeries with both attributions kept" % imp_src)
            continue
        if species_only:
            meas["reports_species_property"] = True
            meas["evidence"].append(note("species_property_scope", mid, species_why))
            note("no_case", eid, "%s; the result is preserved as a Measurement and a "
                 "ResultSeries, but no deposition case is minted and no local material "
                 "role is asserted" % species_why)
            continue
        holder = rep_holder.get(eid)
        if holder and holder != eid:
            # This panel is another VIEW of a measurement shown elsewhere in the same
            # printed figure. A representation never creates an experimental case.
            note("representation_group", eid,
                 "same series label %r as %s in printed figure %s, declaring a different "
                 "representation; no case is minted for a redrawn view"
                 % (ent.get("source_series"), holder, printed))
            if rep_id:
                out["representations"][-1]["derived_representation_of"] = "M::%s" % holder
                out["representations"][-1]["underlying_measurement"] = "M::%s" % holder
                out["representations"][-1]["represents_same_as"] = holder
            meas["represents_same_measurement_as"] = "M::%s" % holder
            continue
        if cls in NON_EXPERIMENTAL:
            note("no_case", eid, "entity_class %r never carries a current-paper deposition "
                 "case; its results are preserved as Measurement/ResultSeries" % cls)
            continue
        _scope_ctx = {"scope_materials": scope_mat, "scope_geometry": scope_geo,
                      "scope_geometry_match": geo_match,
                      # the paper's own classification, for a candidate that resolves to
                      # no entity: it is still an experiment in this paper
                      "paper_geometry": (P.geometry or {}).get("geometry_class"),
                      "paper_geometry_evidence": (P.geometry or {}).get("evidence")}
        # the material this SCOPE names, not the paper-wide value: the two halves of a
        # saturation figure deposit different materials and must not share a design
        _scope_dep = sorted({m for m, recs in (scope_mat or {}).items()
                             if R.primary_role(recs) == R.DEPOSITED})
        sweep, x_role, x_basis, sweep_note, design = PC.sweep_cases(
            ent, scope_text, P.methods,
            material=(_scope_dep[0] if len(_scope_dep) == 1 else ent.get("material")),
            step=step_by_entity.get(eid))
        if design:
            # One printed panel may carry SEVERAL swept series (three precursors, each
            # with its own temperature sweep). Keying the design on figure+panel+quantity
            # alone gave them one id, which made design identity ambiguous and let a
            # consolidation pass delete the survivor along with its duplicates.
            design["design_id"] = "DES::%s::F%s%s::%s::%s" % (
                pid, printed, panel, design["varied_quantity"], eid)
            design["evidence_id"] = note("experimental_design", design["design_id"],
                                         design["evidence"],
                                         varied=design["varied_quantity"],
                                         branches=design["branch_values"],
                                         axis_role=design["axis_role"])
            out["experimental_designs"].append(design)
            for _b in sweep:
                _b["design_id"] = design["design_id"]
        if sweep and _series_reagent:
            # The legend named which side of the cycle this curve's dose belongs to. It
            # qualifies the swept quantity, so an exposure of the precursor and the same
            # exposure of the co-reactant stay distinct settings of distinct steps -- the
            # `species` dimension the case fingerprint already carries.
            for sc in sweep:
                sc["species"] = _series_reagent["series_reagent"]
                sc["species_basis"] = _series_reagent["role_basis"]
                sc["species_evidence"] = _series_reagent["evidence"]
        if sweep:
            for k, sc in enumerate(sweep):
                candidates.append(_cand(pid, eid, printed, panel, cd + [sc], mid,
                                        rs_ids, ent, "design_branch",
                                        note("sweep_normalisation", eid, sc["evidence"],
                                             quantity=sc["quantity"], value=sc["value"],
                                             unit=sc["unit"], role_basis=x_basis),
                                        _scope_ctx))
                candidates[-1]["design_id"] = design["design_id"] if design else None
                candidates[-1]["branch_value"] = sc["value"]
                out["design_branches"].append({
                    "branch_id": "BR::%s::%s::%s" % (pid, (design or {}).get("design_id",
                                                                             ""), sc["value"]),
                    "design_id": (design or {}).get("design_id"),
                    "paper_id": pid, "quantity": sc["quantity"], "value": sc["value"],
                    "unit": sc["unit"],
                    "source": {"printed_figure": printed, "panel": panel,
                               "resolved_entity_id": eid},
                    "measurement_id": mid, "candidate_id": candidates[-1]["candidate_id"],
                    "evidence": sc["evidence"]})
        else:
            basis = ("x axis %r is %s (%s); its points are observations of one specimen"
                     % (ent.get("coordinate"), x_role, x_basis))
            if sweep_note:
                basis += " | " + sweep_note
            if (ent.get("experimental_case_count") or 0) == 0 and \
                    ent.get("experimental_case_status") in ("unresolved_settings",
                                                            "shared_measurement_event"):
                # the resolver could not resolve how many settings this curve holds, or the
                # case is carried by a sibling channel. Either way no case is minted here,
                # and the result is preserved as a Measurement.
                note("no_case", eid, "%s: %s" % (ent.get("experimental_case_status"),
                                                 ent.get("experimental_case_reason") or ""))
                continue
            candidates.append(_cand(pid, eid, printed, panel, cd, mid, rs_ids, ent,
                                    "whole_curve", note("case_scope", eid, basis),
                                    _scope_ctx))
            if x_role == D.PROCESS_PROGRESSION:
                # this curve's x axis TRAVERSES the quantity: any fixed assertion of it
                # that reaches the merged case through linked context describes one
                # member's own interval, never a defining condition of the whole case
                candidates[-1]["progression_coordinate"] = ent.get("coordinate")
            if _prog_stage:
                candidates[-1]["progression_stage"] = _prog_stage["value"]
                candidates[-1]["progression_quantity"] = _prog_stage["quantity"]
                # ONLY this figure's own scope. Paper-wide or Methods prose describes
                # other work and cannot authorise a merge between these curves.
                _verdict, _why = D.progression_continuity(scope_text)
                candidates[-1]["progression_continuity"] = _verdict
                candidates[-1]["progression_continuity_reason"] = _why
            # (E) the scope's own caption may describe the deposition it shows
            _syn = local_synthesis_evidence(" ".join([clause, preamble]),
                                            _paper_default_values(P))
            if _syn:
                candidates[-1]["local_synthesis"] = _syn
                candidates[-1]["evidence"].append(
                    note("local_synthesis", eid,
                         "the scope describes the deposited object it shows: %r" % _syn))

    # ------------------------------ 3b. measurements the extraction stage never reached
    # A caption panel that reports a measurement PSED holds no numbers for is still a
    # result the paper reports. It is emitted as a Measurement with its caption evidence
    # and no ResultSeries; it mints no deposition case, because appearing in another
    # figure is not a new deposition.
    for sp in SUP.build(P, P.root / "diagnostics" / "assets"):
        out["measurements"].append({
            "measurement_id": sp["measurement_id"], "paper_id": pid,
            "technique": sp["techniques"],
            "technique_basis": "source_reported_panel" if sp["techniques"] else "unresolved",
            "technique_evidence": [], "measured_quantity": None, "measured_unit": None,
            "coordinate": None, "coordinate_unit": None,
            "entity_class": None, "classification": "caption_only_measurement",
            "performed_on": None, "measures_case": [], "measurement_settings": [],
            "source": {"printed_figure": sp["printed_figure"], "panel": sp["panel"],
                       "resolved_entity_id": None, "fig_docling_index": None,
                       "source_series": None},
            "caption_reference": sp["caption_clause"],
            "result_series_ids": [], "representation_id": None,
            "n_observations": 0, "repeat_measurement": False,
            "data_recovered": False, "recovery_cause": sp["cause"],
            "recovery_detail": sp["cause_detail"],
            "page_render": sp.get("page_render"),
            "evidence": [note("extraction_gap", sp["measurement_id"],
                              "%s | %s" % (sp["cause_detail"], sp["caption_clause"][:200]),
                              cause=sp["cause"], printed_figure=sp["printed_figure"],
                              panel=sp["panel"])],
            "confidence": PC.UNRESOLVED,
        })

    # ------------------------------- 3c. deposition cases carried by an image, not a curve
    # A figure whose caption reports a deposition on a described structure documents a
    # real experimental case. Its evidence is an electron micrograph, so it has no
    # ResultSeries and claims none — experiment existence does not require a plot.
    for ic in SUP.image_supported_cases(P):
        conds = [dict(c, role=R.CASE_DEFINING,
                      role_basis="stated in the caption of an image-supported figure",
                      provenance_type="figure_local_direct", source="figure_caption",
                      evidence=c.get("span")) for c in ic["conditions"]]
        # An image of a characterised specimen is evidence that a MEASUREMENT happened. It
        # is evidence of a distinct DEPOSITION only when the caption says something the
        # paper's default recipe does not already say. A micrograph captioned with exactly
        # the standard process identifies no particular deposition, so its result is
        # preserved and its case link is left unresolved rather than invented.
        distinguishing = [c for c in conds
                          if not _matches_default(c, _paper_default_values(P))]
        if not distinguishing and not local_synthesis_evidence(ic["caption"],
                                                               _paper_default_values(P)):
            note("case_not_minted", "figure %s" % ic["printed_figure"],
                 "this figure is characterisation: every deposition condition its caption "
                 "states (%s) repeats the paper's default process, and no specimen, case "
                 "or local synthesis statement identifies which deposition it shows; the "
                 "measurement is preserved and its case link is left unresolved"
                 % ", ".join("%s=%s" % (c["quantity"], c.get("value")) for c in conds))
            out["unresolved"].append({
                "paper_id": pid, "kind": "case_link", "source_figure": ic["printed_figure"],
                "measurement_id": "M::IMG::%s::F%s" % (pid, ic["printed_figure"]),
                "reason": "the figure characterises a specimen but no source statement "
                          "identifies which deposition produced it; its stated conditions "
                          "only repeat the paper-wide default process",
                "class": "CONDITION_ONLY_NO_POSITIVE_LINK"})
            _emit_image_measurement(out, pid, ic, note, minted_case=False)
            continue
        cev = note("image_supported_case", "figure %s" % ic["printed_figure"],
                   ic["caption"][:300], geometry=ic["geometry"],
                   materials=ic["deposited_materials"],
                   conditions=[(c["quantity"], c.get("value") if c.get("value") is not None
                                else [c.get("value_lower"), c.get("value_upper")])
                               for c in ic["conditions"]])
        candidates.append(_cand(pid, None, ic["printed_figure"], "", conds, None, [], None,
                                "image_supported", cev,
                                # every role the caption states, not only the deposited
                                # one: a capping layer and a substrate are part of what
                                # this case IS, and dropping them loses the stack
                                {"scope_materials": {m: [{"role": role,
                                                          "matched": "caption",
                                                          "span": ic["caption"][:200]}]
                                                     for m, role in
                                                     sorted((ic.get("material_roles")
                                                             or {}).items())},
                                 "scope_geometry": ic["geometry"],
                                 "scope_geometry_match": ic["geometry_evidence"]}))
        candidates[-1]["deposited_material"] = (ic["deposited_materials"][0]
                                                if len(ic["deposited_materials"]) == 1 else None)
        _syn_i = local_synthesis_evidence(ic["caption"], _paper_default_values(P))
        if _syn_i:
            candidates[-1]["local_synthesis"] = _syn_i
        candidates[-1]["measurement_id"] = _emit_image_measurement(
            out, pid, ic, note, minted_case=True, ev=cev,
            material=candidates[-1]["deposited_material"])

    # ------------------------------------------------ 4. text-supported deposition cases
    for tc in text_cases(P):
        candidates.append(_cand(pid, None, tc["printed_figure"], "", tc["conditions"],
                                None, [], None, "text_supported",
                                note("text_supported_case", tc["label"], tc["evidence"],
                                     sentence=tc["sentence"])))
        candidates[-1]["label"] = tc["label"]
        candidates[-1]["synthesis_label"] = tc.get("synthesis_label")
        candidates[-1]["deposited_material"] = tc["material"]

    # -------------------------------------- 4b. cases the paper's own specimen table defines
    # A specimen table IS the author stating the design. Its rows, normalised on the
    # deposition-defining columns alone, are the nominal cases of the study -- including
    # the ones no figure happens to plot, which would otherwise be silently lost. A
    # measurement setting (a magnification, a frequency) never participates in the key.
    table_case_of_code = {}
    if sample_by_code:
        nominal = defaultdict(list)
        for code, sm in sorted(sample_by_code.items(), key=_code_sort):
            k = D.nominal_key(sm.get("case_defining_conditions") or [])
            if k:
                nominal[k].append(code)
        for k, codes in sorted(nominal.items(), key=lambda kv: _code_sort((kv[1][0], None))):
            proto = sample_by_code[codes[0]]
            conds = [dict(c, provenance_type="derived_from_table_recipe",
                          evidence="row %s of the paper's specimen table gives %s = %s"
                                   % (codes[0], c["quantity"], c.get("value")))
                     for c in proto.get("case_defining_conditions") or []]
            tbl_ev = note("tabulated_case", "TBL::%s::%s" % (pid, "+".join(codes)),
                          "the specimen table defines this set of deposition conditions; "
                          "specimen%s %s realise%s it"
                          % ("" if len(codes) == 1 else "s", ", ".join(codes),
                             "s" if len(codes) == 1 else ""),
                          specimens=codes)
            candidates.append(_cand(pid, None, None, "", conds, None, [], None,
                                    "tabulated_specimen", tbl_ev,
                                    {"paper_geometry": (P.geometry or {}).get(
                                        "geometry_class"),
                                     "paper_geometry_evidence": (P.geometry or {}).get(
                                        "evidence")}))
            candidates[-1]["table_specimen_codes"] = codes
            candidates[-1]["sample_codes"] = list(codes)
            for code in codes:
                table_case_of_code[code] = candidates[-1]["candidate_id"]

    # ---------------------------------------------------------- 5. linkage between candidates
    codes_of_meas = defaultdict(set)
    for sm in out["samples"]:
        for m in sm["measurement_ids"]:
            codes_of_meas[m].add(sm["source_sample_code"])
    for c in candidates:
        if c.get("kind") == "tabulated_specimen":
            continue
        c["sample_codes"] = sorted(codes_of_meas.get(c.get("measurement_id")) or [],
                                   key=lambda x: _code_sort((x, None)))
        if len(c["sample_codes"]) == 1:
            sm = sample_by_code.get(c["sample_codes"][0]) or {}
            # The specimen's own row is added WHATEVER a weaker source already said. It is
            # the most specific evidence there is about this specimen, and withholding it
            # because a paper-wide default got there first left the result carrying a
            # value the table contradicts.
            for tc in sm.get("case_defining_conditions") or []:
                rec = dict(tc)
                rec["provenance_type"] = "inherited_from_sample"
                rec["evidence"] = ("specimen %r is named for this result; its row of "
                                   "the paper's specimen table gives %s = %s"
                                   % (c["sample_codes"][0], tc["quantity"], tc["value"]))
                c["case_conditions"].append(rec)
            c["case_conditions"] = PC.resolve_conditions(c["case_conditions"])
    cand_links = discover_links(P, candidates, sample_by_code, out, note,
                                series_members, table_cols)
    cand_links += tabulated_case_links(candidates, table_case_of_code, note)
    cand_links += progression_stage_links(candidates, note)
    design_blocks = []
    cand_links += nominal_identity_links(P, candidates, sample_by_code, note,
                                         blocked=design_blocks)

    # ---------------------------------------------------------- 6. resolve identities
    groups, decisions = PC.resolve_cases(candidates, cand_links)
    out["links"] = [dict(d) for d in decisions] + design_blocks
    by_id = {c["candidate_id"]: c for c in candidates}

    i = 0
    for g in sorted(groups, key=lambda x: x[0]):
        members = [by_id[c] for c in g]
        anchored, why = _anchors_deposition_case(members)
        if not anchored:
            for m in members:
                note("case_not_minted", m["candidate_id"], why)
                out["unresolved"].append({
                    "paper_id": pid, "kind": "case_link",
                    "source_figure": m.get("source_figure"),
                    "source_panel": m.get("source_panel"),
                    "measurement_id": m.get("measurement_id"),
                    "reason": why, "class": "CONDITION_ONLY_NO_POSITIVE_LINK"})
            continue
        i += 1
        out["experimental_cases"].append(_case(pid, i, members, P, paper_mat_roles,
                                               meas_by_entity, sample_by_code, note))

    # back-references
    case_of_cand = {}
    for case in out["experimental_cases"]:
        for cid in case["candidate_ids"]:
            case_of_cand[cid] = case["case_id"]
    for case in out["experimental_cases"]:
        for mid in case["measurement_ids"]:
            m = next((x for x in out["measurements"] if x["measurement_id"] == mid), None)
            if m and case["case_id"] not in m["measures_case"]:
                m["measures_case"].append(case["case_id"])
        for sid in case["sample_ids"]:
            s = sample_by_code.get(sid.split("::")[-1])
            if s and case["case_id"] not in s["experimental_case_ids"]:
                s["experimental_case_ids"].append(case["case_id"])
                s["material"] = s["material"] or case["deposited_material"]
                s["geometry"] = s["geometry"] or case["geometry"]

    # ---- nominal identity: what actually distinguishes each case from the others ------
    # A case's identity is its complete case-defining condition set TOGETHER with the other
    # case-defining dimensions the model represents -- the deposited material, the geometry,
    # the design branch it realises. Two cases that agree on all of them are not
    # distinguished by anything the model holds; that is recorded on the case rather than
    # hidden, because the alternative is presenting them as distinct depositions on the
    # strength of nothing more than being drawn as separate curves.
    _fp = defaultdict(list)
    for c in out["experimental_cases"]:
        # A step-scoped quantity is identified by its STEP as well as its value: a 2 s
        # purge after the precursor and a 2 s purge after the plasma are different
        # settings of different steps that happen to share a number. The design layer
        # already resolves the step; dropping it here made the two indistinguishable.
        key = (tuple(sorted((x["quantity"], str(x.get("species") or ""),
                             str(x.get("process_step") or ""),
                             str(PC.value_token(x)))
                            for x in c.get("case_defining_conditions") or [])),
               c.get("deposited_material"), c.get("geometry"),
               tuple(sorted(c.get("study_series_ids") or [])),
               tuple(sorted(s.rsplit("::", 1)[-1] for s in c.get("sample_ids") or [])))
        c["nominal_fingerprint"] = "|".join(
            ["%s%s%s=%s" % (q, ("@" + sp) if sp else "",
                            ("/" + st) if st else "", v)
             for q, sp, st, v in key[0]]
            + ["material=%s" % (key[1] or "?"), "geometry=%s" % (key[2] or "?")])
        _fp[key].append(c)
    for key, group in _fp.items():
        dims = []
        if key[0]:
            dims.append("case-defining conditions")
        if key[1]:
            dims.append("deposited material")
        if key[2]:
            dims.append("geometry")
        if key[4]:
            dims.append("named specimens")
        for c in group:
            c["identity_distinguished_by"] = dims
            if len(group) == 1:
                c["identity_status"] = "DISTINGUISHED"
                continue
            # several cases share every represented dimension
            c["identity_status"] = "INDISTINGUISHABLE_FROM_SIBLING"
            c["indistinguishable_from"] = sorted(x["case_id"] for x in group
                                                 if x["case_id"] != c["case_id"])
            c["identity_reason"] = (
                "this case shares every case-defining dimension the model represents "
                "(%s) with %s; they are separate only because the source draws them as "
                "separate results, which is not deposition evidence. The count is "
                "PROVISIONAL pending a source-positive identity audit."
                % (", ".join(dims) or "no represented dimension",
                   ", ".join(x["case_id"] for x in group if x["case_id"] != c["case_id"])))
            c.setdefault("warnings", []).append("INDISTINGUISHABLE_NOMINAL_IDENTITY")
            note("indistinguishable_case", c["case_id"], c["identity_reason"])

    # ---- annotate every decision with what became of its endpoints --------------------
    # A BLOCKED edge between candidates that never became cases is a decision about
    # objects the graph does not contain. Recording that keeps a moot decision from
    # reading as an active scientific contradiction, without deleting the record.
    _case_of_cand = {cid: c["case_id"] for c in out["experimental_cases"]
                     for cid in c.get("candidate_ids") or []}
    _cand_by_id = {c["candidate_id"]: c for c in candidates}
    for lk in out["links"]:
        ca, cb = _case_of_cand.get(lk.get("a")), _case_of_cand.get(lk.get("b"))
        lk["a_case_id"], lk["b_case_id"] = ca, cb
        clash = (lk.get("detail") or {}).get("clash") if isinstance(lk.get("detail"),
                                                                   dict) else None
        superseded = []
        for q in {x.get("quantity") for x in (clash or [])}:
            for side in (lk.get("a"), lk.get("b")):
                for c in (_cand_by_id.get(side) or {}).get("case_conditions") or []:
                    if c.get("quantity") == q and c.get("superseded"):
                        superseded.append("%s on %s" % (q, side))
        lk["superseded_conditions"] = sorted(set(superseded))
        if lk.get("action") != "BLOCKED":
            lk["decision_status"] = "APPLIED"
        elif not ca or not cb:
            lk["decision_status"] = "MOOT_NO_CASE"
            lk["decision_note"] = (
                "one endpoint never became an ExperimentalCase (%s / %s), so this "
                "contradiction is recorded but is not active in the graph"
                % (ca or "no case", cb or "no case"))
        elif superseded:
            lk["decision_status"] = "STALE_SUPERSEDED"
            lk["decision_note"] = ("the clashing value has been superseded by more "
                                   "specific evidence on the same object (%s)"
                                   % "; ".join(sorted(set(superseded))))
        elif clash:
            lk["decision_status"] = "ACTIVE_CONTRADICTION"
        else:
            # blocked on design IDENTITY (different quantity, step, material, or a field
            # that is not positively known), which is a different thing from two sources
            # disagreeing about the value of one condition
            lk["decision_status"] = "DESIGN_IDENTITY_BLOCK"

    # ---------------------------------------------------------- 7. study series
    for letter in sorted(series_members) or sorted(series_ev):
        codes = sorted(series_members.get(letter, []))
        sids = [sample_by_code[c]["sample_id"] for c in codes if c in sample_by_code]
        # Precedence: what the AUTHOR declared > caption/prose > column differencing.
        decl = series_decls.get(letter)
        tvar, trole, tev = table_series_variable(P, table_cols, codes)
        co_varying = table_co_variation(P, table_cols, codes)
        if decl:
            varied, vrole = decl["quantity"], decl["role"]
            vev = decl["evidence"]
            var_source = "author_declaration"
            co_varying = [c for c in co_varying if c["quantity"] != varied]
        elif tvar:
            varied, vrole, vev = tvar, trole, tev
            var_source = "specimen_table_column_differencing"
            co_varying = []
        else:
            varied, vrole, vev = series_variable(P, letter)
            var_source = "caption_or_prose" if varied else "unresolved"
            if not varied:
                vrole = R.UNRESOLVED_ROLE
        out["study_series"].append({
            "series_id": "SER::%s::%s" % (pid, letter), "paper_id": pid,
            "author_series_name": "Series %s" % letter,
            "member_sample_codes": codes, "member_sample_ids": sids,
            "member_case_ids": sorted({c for s in sids
                                       for c in _sample_cases(out, s)}),
            "varied_variable": varied, "varied_variable_role": vrole,
            "varied_variable_source": var_source,
            # The intended variable and incidental co-variation are different facts. A
            # specimen that also differs in another tabulated column does not change what
            # the series is ABOUT, and erasing either is a loss.
            "co_varying_context": co_varying,
            "purpose": vev, "evidence": note("study_series", "Series %s" % letter,
                                             (series_ev.get(letter) or {}).get("span", ""),
                                             members=codes),
        })

    # ---------------------------------------------------------- 8. deposition runs
    # After the series, because a run statement identifies its specimens through the
    # series it names ("grown in the same ALD run … (Series A in Table 1)").
    # An identifiable process execution and an assertion that several runs exist are
    # different objects. Only the first is a DepositionRun; counting the second as one
    # made "3 runs" mean "1 run and 2 statements about runs".
    all_runs = deposition_runs(P, out, sample_by_code, note)
    out["deposition_runs"] = [r for r in all_runs if r["kind"] == "SHARED_RUN"
                              and r["sample_ids"]]
    out["run_evidence"] = [dict(r, evidence_kind=r["kind"]) for r in all_runs
                           if r not in out["deposition_runs"]]
    for r in out["deposition_runs"]:
        for sid in r["sample_ids"]:
            sm = next((x for x in out["samples"] if x["sample_id"] == sid), None)
            if sm:
                sm["produced_by_run"] = r["run_id"]
        for cid in r["experimental_case_ids"]:
            c = next((x for x in out["experimental_cases"] if x["case_id"] == cid), None)
            if c and r["run_id"] not in c["deposition_run_ids"]:
                c["deposition_run_ids"].append(r["run_id"])
    for ser in out["study_series"]:
        for cid in ser["member_case_ids"]:
            c = next((x for x in out["experimental_cases"] if x["case_id"] == cid), None)
            if c and ser["series_id"] not in c["study_series_ids"]:
                c["study_series_ids"].append(ser["series_id"])

    # ---------------- 7b. one design per DESIGN, not per panel that displays it --------
    # Two panels of one printed figure that sweep the same fully-known design are two
    # VIEWS of one experiment: the author varied one parameter and measured two outputs.
    # Emitting a design and a branch set per panel duplicated the objects and left the
    # branch identity to be reconstructed downstream at case level. Consolidation requires
    # positive shared-design evidence -- same printed figure, and every design field
    # positively known and equal on both sides -- so an unknown never licenses a merge.
    fig_designs = [x for x in out["experimental_designs"]
                   if (x.get("source") or {}).get("printed_figure")]
    groups = defaultdict(list)
    for x in fig_designs:
        groups[str((x.get("source") or {}).get("printed_figure"))].append(x)
    canonical_of = {}
    for fig, members_ in sorted(groups.items()):
        keep = []
        for x in members_:
            for k in keep:
                if k["design_id"] == x["design_id"]:
                    continue                       # never fold a design into itself
                same, why = D.signatures_identify_same_design(x.get("signature"),
                                                              k.get("signature"))
                if same:
                    canonical_of[x["design_id"]] = k["design_id"]
                    k.setdefault("displayed_in_panels",
                                 [(k.get("source") or {}).get("panel")])
                    k["displayed_in_panels"].append((x.get("source") or {}).get("panel"))
                    k["consolidated_from"] = sorted(
                        set(k.get("consolidated_from") or []) | {x["design_id"]})
                    k["consolidation_evidence"] = note(
                        "shared_design", k["design_id"],
                        "panels %s of figure %s sweep the same design (%s); %s"
                        % ("/".join(str(pp) for pp in sorted(
                            set(k["displayed_in_panels"]), key=str)), fig,
                           ", ".join(k.get("signature") or []), why))
                    break
            else:
                keep.append(x)
    if canonical_of:
        out["experimental_designs"] = [x for x in out["experimental_designs"]
                                       if x["design_id"] not in canonical_of]
        merged_branches, seen_branch = [], {}
        for b in out["design_branches"]:
            did = canonical_of.get(b.get("design_id"), b.get("design_id"))
            key = (did, PC._fmt(b.get("value")))
            if key in seen_branch:
                tgt = seen_branch[key]
                for f_, v_ in (("measurement_ids", b.get("measurement_id")),
                               ("candidate_ids", b.get("candidate_id"))):
                    if v_ and v_ not in tgt[f_]:
                        tgt[f_].append(v_)
                tgt["displayed_in_panels"] = sorted(
                    set(tgt["displayed_in_panels"]
                        + [(b.get("source") or {}).get("panel")]), key=str)
                continue
            b = dict(b, design_id=did,
                     branch_id="BR::%s::%s::%s" % (pid, did, PC._fmt(b.get("value"))))
            b["measurement_ids"] = [b["measurement_id"]] if b.get("measurement_id") else []
            b["candidate_ids"] = [b["candidate_id"]] if b.get("candidate_id") else []
            b["displayed_in_panels"] = [(b.get("source") or {}).get("panel")]
            seen_branch[key] = b
            merged_branches.append(b)
        out["design_branches"] = merged_branches
    # A design's branch list is DERIVED from its branch objects, never carried separately.
    # Keeping a second copy let the two disagree the moment designs were consolidated.
    _by_design = defaultdict(list)
    for b in out["design_branches"]:
        _by_design[b.get("design_id")].append(b)
    for x in out["experimental_designs"]:
        own = _by_design.get(x["design_id"])
        if own is None:
            continue
        vals, seen_v = [], set()
        for b in sorted(own, key=lambda r: (PRG._f(r.get("value")) is None,
                                            PRG._f(r.get("value")) or 0,
                                            str(r.get("value")))):
            v = PC._fmt(b.get("value"))
            if v not in seen_v:
                seen_v.add(v)
                vals.append(v)
        x["branch_values"] = vals
        x["n_branches"] = len(vals)
        x["branch_ids"] = [b["branch_id"] for b in own]
        x["source_branch_appearances"] = sum(
            len(b.get("measurement_ids") or [b.get("measurement_id")]) for b in own)

    # ------------------- 7c. designs the SOURCE declares, as first-class objects --------
    # An author-declared series IS an experimental design: a named factor, varied over a
    # stated set of specimens. Instantiating it here makes the design layer independent of
    # whether any figure happened to plot the sweep. Nothing is created without positive
    # design evidence -- a declared factor with resolved structured components and at least
    # two specimens that differ in it.
    for ser in out["study_series"]:
        f = (design_factors or {}).get((ser.get("author_series_name") or "").split()[-1])
        codes = sorted(ser.get("member_sample_codes") or [], key=lambda x: (len(x), x))
        if not f or not f.get("components") or len(codes) < 2:
            continue
        vals, raws, unit = _factor_levels(f["components"], table_conditions, codes)
        if len(set(vals.values())) < 2:
            # the declared factor does not actually vary across the stated members: the
            # source names a design the table does not realise, so none is asserted
            note("design_not_instantiated", ser["series_id"],
                 "the source declares that %s varies %r, but its specimens (%s) do not "
                 "differ in %s; no design is asserted"
                 % (ser.get("author_series_name"), f.get("phrase"), ", ".join(codes),
                    " + ".join(f["components"])))
            continue
        did = "DES::%s::%s" % (pid, (ser.get("author_series_name") or "").replace(" ", ""))
        design = {
            "design_id": did, "paper_id": pid,
            "varied_quantity": f["quantity"],
            "design_factor": {
                "factor_id": "FAC::%s::%s" % (pid, f["quantity"]),
                "declared_as": f.get("phrase"),
                "quantity": f["quantity"],
                "components": list(f["components"]),
                "is_compound": len(f["components"]) > 1,
                "role": f["role"],
                "evidence": f.get("evidence"),
                "resolution": f.get("why"),
            },
            "unit": unit,
            "signature": list(D.design_signature(f["quantity"], f.get("phrase"), unit,
                                                 None)),
            "process_step": D.process_step(f.get("phrase"), f["quantity"]),
            "material": None,
            "branch_values": [PC._fmt(v) for v in sorted(set(vals.values()))],
            "n_branches": len(set(vals.values())),
            "axis_role": D.CASE_DEFINING_PROCESS_SETTING,
            "axis_role_basis": "declared by the author as the variable this series varies",
            "declared_by": ser["series_id"],
            "source": {"printed_figure": None, "panel": None,
                       "resolved_entity_id": None, "specimen_table": True},
            "evidence": "the source declares that %s varies %r"
                        % (ser.get("author_series_name"), f.get("phrase")),
        }
        design["evidence_id"] = note("experimental_design", did, design["evidence"],
                                     varied=f["quantity"], components=f["components"],
                                     branches=design["branch_values"], specimens=codes)
        out["experimental_designs"].append(design)
        by_val = defaultdict(list)
        for code, v in sorted(vals.items(), key=lambda kv: (len(kv[0]), kv[0])):
            by_val[v].append(code)
        for v in sorted(by_val):
            members = by_val[v]
            out["design_branches"].append({
                "branch_id": "BR::%s::%s::%s" % (pid, did, PC._fmt(v)),
                "design_id": did, "paper_id": pid,
                "design_factor_id": design["design_factor"]["factor_id"],
                "quantity": f["quantity"], "value": v, "unit": unit,
                "raw_value": raws.get(members[0]),
                "components": list(f["components"]),
                "source": {"specimen_table": True, "series": ser["series_id"]},
                "realised_by_sample_codes": members,
                "realised_by_sample_ids": [sample_by_code[c]["sample_id"]
                                           for c in members if c in sample_by_code],
                "realises_case_ids": sorted({cid for c in members
                                             for cid in (sample_by_code.get(c) or {})
                                             .get("experimental_case_ids") or []}),
                "measurement_id": None, "candidate_id": None,
                "evidence": "specimen%s %s of %s %s %s = %s"
                            % ("" if len(members) == 1 else "s", ", ".join(members),
                               ser.get("author_series_name"),
                               "has" if len(members) == 1 else "have",
                               " + ".join(f["components"]), PC._fmt(v)),
            })

    # ---- specimen-side provenance, so no membership depends on a plotted curve --------
    # A DepositionRun is provenance, not identity: it records which specimens were grown
    # together. Its members may realise DIFFERENT cases, and a shared run is never a reason
    # to merge them.
    for run in out["deposition_runs"]:
        for code in run.get("sample_codes") or []:
            sm_ = sample_by_code.get(code)
            if sm_:
                sm_["produced_by_run"] = run["run_id"]
    # StudySeries is a grouping relation over specimens. Recording it on the specimen keeps
    # a member that has no figure result, and the cases a series covers stay DERIVED from
    # its specimens rather than stored as a second identity.
    for ser in out["study_series"]:
        for code in ser.get("member_sample_codes") or []:
            sm_ = sample_by_code.get(code)
            if sm_ is not None:
                ids = sm_.setdefault("study_series_ids", [])
                if ser["series_id"] not in ids:
                    ids.append(ser["series_id"])

    # ------------------------------------------- 8b. produced-material provenance chains
    # A characterisation result may acquire a deposition case when the source states that
    # the material that case PRODUCED was placed on the thing that was measured. A legend
    # naming a control ("bare", "uncoated") is a comparison and is never attached.
    out["provenance_chains"] = produced_material_chain(P, out["experimental_cases"], note)
    resolved_chains = [c for c in out["provenance_chains"] if c["status"] == "RESOLVED"]
    for m in out["measurements"]:
        if not provenance_eligible(m):
            continue
        is_ref, ref_word = is_reference_series(m["source"].get("source_series"))
        if is_ref:
            m["provenance_role"] = "REFERENCE"
            m["provenance_note"] = ("the legend %r names a comparison control, so this "
                                    "result is not attributed to a deposition case"
                                    % m["source"].get("source_series"))
            m["evidence"].append(note("reference_series", m["measurement_id"],
                                      m["provenance_note"], matched=ref_word))
            continue
        resolved_chain = next(
            (c for c in resolved_chains
             if str(m["source"].get("printed_figure")) in (c.get("covers_figures") or [])),
            None)
        if not resolved_chain:
            m["provenance_role"] = "CASE_UNRESOLVED"
            m["provenance_note"] = (
                "no statement in the section reporting this figure identifies which "
                "synthesis produced the measured specimen")
            continue
        m["provenance_role"] = "PRODUCT_OF_CASE"
        m["measures_case"] = list(resolved_chain["case_ids"])
        m["provenance_chain"] = {
            "case_id": resolved_chain["case_ids"][0],
            "product": "%s %s" % (resolved_chain["product_material"],
                                  resolved_chain["product_form"]),
            "device": resolved_chain["device"],
            "statement": resolved_chain["statement"]}
        m["confidence"] = PC.SUPPORTED
        m["evidence"].append(note("provenance_chain", m["measurement_id"],
                                  resolved_chain["statement"],
                                  case=resolved_chain["case_ids"][0],
                                  device=resolved_chain["device"]))
        for c in out["experimental_cases"]:
            if c["case_id"] in resolved_chain["case_ids"] \
                    and m["measurement_id"] not in c["measurement_ids"]:
                c["measurement_ids"].append(m["measurement_id"])

    # ---------------------------------------------------------- 9. unresolved links
    out["unresolved"] = [dict(u, reason_class="CONDITION_ONLY_NO_POSITIVE_LINK")
                         for u in PC.unresolved_pairs(candidates, groups)]
    for u in out["unresolved"]:
        u["a_case"] = case_of_cand.get(u["a"])
        u["b_case"] = case_of_cand.get(u["b"])
    # A measurement with no case link is itself an unresolved link, and the most
    # important kind: a characterisation result whose producing deposition the source
    # does not identify. It is kept as a scientific result and NOT forced onto a case.
    for m in out["measurements"]:
        if m["measures_case"]:
            continue
        out["unresolved"].append({
            "kind": "measurement_without_case",
            "measurement_id": m["measurement_id"],
            "printed_figure": m["source"]["printed_figure"],
            "panel": m["source"]["panel"],
            "technique": m["technique"],
            "status": PC.UNRESOLVED,
            "reason_class": ("REFERENCE_BY_DESIGN" if m.get("provenance_role") == "REFERENCE"
                             else "PROVENANCE_CHAIN_INCOMPLETE"
                             if m.get("provenance_role") == "CASE_UNRESOLVED"
                             else "MEASUREMENT_ONLY_FIGURE"
                             if m.get("reports_species_property") else
                             "SOURCE_TRULY_UNSPECIFIED"),
            "reason": (m.get("provenance_note")
                       or ("no deposition case is established for this result: "
                           + ("the extraction stage holds no data for this panel"
                              if m.get("data_recovered") is False else
                              "the source does not state which deposition produced the "
                              "specimen it was measured on"))),
            "preserved_context": {
                "material": m.get("_material"), "conditions": m.get("_conditions") or [],
            },
        })

    # A redrawn view observes the SAME deposition as the measurement it redraws. It mints
    # no case of its own -- that would double-count the experiment -- but it must REACH
    # the case the original established, or a panel showing the same data per cycle
    # arrives with no process context at all. Run as a closure so a chain of
    # representations resolves however the panels were ordered.
    _by_mid = {m.get("measurement_id"): m for m in (out.get("measurements") or [])}

    def _holder_chain(mid):
        """Walk the represents-same chain, refusing to loop.

        A cycle would mean two panels each claiming to re-render the other, which
        establishes no original and must not be resolved by picking one.
        """
        seen, cur = set(), mid
        while cur and cur not in seen:
            seen.add(cur)
            nxt = (_by_mid.get(cur) or {}).get("represents_same_measurement_as")
            if nxt == cur:
                return None, "self-reference"
            cur = nxt
            if cur in seen:
                return None, "cycle"
            if cur and (_by_mid.get(cur) or {}).get("measures_case"):
                return _by_mid[cur], None
        return None, "no case anywhere in the chain"

    for _ in range(len(_by_mid) or 1):
        moved = 0
        for m in (out.get("measurements") or []):
            # an existing case is never overwritten: a panel that established its own
            # deposition outranks anything it happens to re-render
            if m.get("measures_case"):
                continue
            if not m.get("represents_same_measurement_as"):
                continue
            holder, why = _holder_chain(m.get("measurement_id"))
            if holder is None:
                if why in ("cycle", "self-reference"):
                    m["measures_case_basis"] = (
                        "not inherited: the represents-same chain forms a %s, so no "
                        "original measurement is established" % why)
                continue
            m["measures_case"] = list(holder["measures_case"])
            m["measures_case_basis"] = (
                "inherited from %s, which this panel re-renders"
                % holder.get("measurement_id"))
            moved += 1
        if not moved:
            break

    outdir = P.root / "semantic"
    outdir.mkdir(parents=True, exist_ok=True)
    diag = P.root / "diagnostics"
    diag.mkdir(parents=True, exist_ok=True)
    (diag / "unjoined_curves.json").write_text(
        json.dumps(out.pop("_unjoined_curves", []), indent=1))
    for k, v in out.items():
        (outdir / ("%s.json" % k)).write_text(json.dumps(v, indent=1, ensure_ascii=False))
    return out


# --------------------------------------------------------------------------- helpers
def EXPL(c):
    return PC.EXPLICIT


def _first(xs):
    return xs[0] if xs else None


def _model_stmt(text):
    m = re.search(r"[^.]*\b(?:model|simulat\w+|calculat\w+)\b[^.]*\.", text or "", re.I)
    return _norm(m.group(0))[:260] if m else None


#: measurand -> the technique that MOST LIKELY produced it. This is an INFERENCE, not a
#: reading of the source, so it ranks below any technique the paper actually states and is
#: recorded with an inferred basis. Entries whose output was merely the quantity again
#: ("growth_per_cycle" -> "growth_per_cycle") are gone: they answered "what was measured"
#: when the field asks "with what instrument", and they made 87 of 169 assignments a
#: measurand wearing a technique's name.
_AXIS_TECH = {"current_density": "cyclic_voltammetry",
              "impedance": "impedance_spectroscopy",
              "|z|": "impedance_spectroscopy",
              "refractive_index": "ellipsometry",
              "roughness": "AFM"}
_COORD_TECH = {"binding_energy": "XPS", "two_theta": "XRD", "2theta": "XRD",
               "raman_shift": "Raman", "wavenumber": "FTIR", "frequency": "impedance_spectroscopy",
               "potential": "cyclic_voltammetry", "wavelength": "spectroscopy",
               "sputtering_time": "XPS_depth_profile", "etching_time": "XPS_depth_profile"}


def _tech_from_axes(ent, measurand=None):
    q = str(measurand if measurand is not None else ent.get("measurand") or "").lower()
    if q in _AXIS_TECH:
        return [_AXIS_TECH[q]]
    c = str(ent.get("coordinate") or "").lower()
    if c in _COORD_TECH:
        return [_COORD_TECH[c]]
    return []


#: elements written as the leading metal of a deposited compound
_METAL = __import__("re").compile(r"^([A-Z][a-z]?)")


def _card_reagents(card, material, key):
    """Reagents the paper's process card offers for ONE deposited material.

    A card that lists two precursors for two materials says nothing about which goes with
    which -- until the material's own metal is matched against the reagent formula, which
    is the same rule the resolver already uses for channel selection. A material whose
    metal matches no reagent, or matches several, gets none: guessing between them would
    assert a chemistry the paper did not.
    """
    if not material:
        return []
    m = _METAL.match(str(material))
    if not m:
        return []
    metal = m.group(1)
    hits = [r for r in (card or {}).get(key) or [] if metal in str(r)]
    return hits if len(hits) == 1 else []


def _cand(pid, eid, printed, panel, conds, mid, rs_ids, ent, kind, ev, scope=None):
    scope = scope or {}
    # A candidate built without a figure scope and without a resolved entity is still an
    # experiment in this paper, and the paper's deterministic classification still applies
    # to it. Held here rather than at each call site so a new builder cannot omit it.
    scope = dict(scope)
    scope.setdefault("process_card", getattr(_cand, "process_card", None))
    scope.setdefault("paper_geometry", getattr(_cand, "paper_geometry", None))
    scope.setdefault("paper_geometry_evidence",
                     getattr(_cand, "paper_geometry_evidence", None))
    return {"candidate_id": "C%04d::%s" % (len(_cand.counter), pid) if False else
            "CAND-%s-%03d" % (pid[:6].upper(), next(_counter)),
            "paper_id": pid, "resolved_entity_id": eid, "source_figure": printed,
            "source_panel": panel, "case_conditions": [c for c in conds
                                                       if c.get("role") == R.CASE_DEFINING],
            "other_conditions": [c for c in conds if c.get("role") != R.CASE_DEFINING],
            "measurement_id": mid, "result_series_ids": rs_ids, "kind": kind,
            "deposited_material": (ent or {}).get("material"),
            "geometry": (scope.get("scope_geometry") or (ent or {}).get("geometry_class")
                         or scope.get("paper_geometry")),
            # provenance is reported, never promoted: a value that came from the paper's
            # classification says so even after it reaches a case
            "geometry_source": ("figure/panel caption" if scope.get("scope_geometry")
                                else ((ent or {}).get("geometry_source")
                                      or "paper-level deterministic classification")),
            "geometry_evidence": (scope.get("scope_geometry_match")
                                  or (ent or {}).get("geometry_evidence")
                                  or scope.get("paper_geometry_evidence")),
            "scope_materials": scope.get("scope_materials") or {},
            # the entity's own chemistry, or the paper's process card narrowed to this
            # case's material where the entity resolved none
            "precursors": ((ent or {}).get("precursors")
                           or _card_reagents(scope.get("process_card"),
                                             (ent or {}).get("material")
                                             or scope.get("scope_material"),
                                             "precursors")),
            "coreactants": ((ent or {}).get("coreactants")
                            or _card_reagents(scope.get("process_card"),
                                              (ent or {}).get("material")
                                              or scope.get("scope_material"),
                                              "coreactants")
                            or (scope.get("process_card") or {}).get("coreactants") or []),
            "process_type": (ent or {}).get("process_type"),
            "evidence": [ev]}


def _mk_counter():
    n = [0]
    while True:
        n[0] += 1
        yield n[0]


_counter = _mk_counter()


def _sample_cases(out, sample_id):
    s = next((x for x in out["samples"] if x["sample_id"] == sample_id), None)
    return s["experimental_case_ids"] if s else []


#: a word in an axis label that names a REAGENT ROLE rather than a chemical. The role is
#: only usable when the paper's own inventory binds it to exactly one reagent.
_ROLE_WORD = (
    (re.compile(r"\bprecursor\b", re.I), "precursors"),
    (re.compile(r"\b(?:co[-\s]?reactant|counter[-\s]?reactant|reactant)\b", re.I),
     "coreactants"),
)


def species_repair(c, precursors, coreactants, note=None, cid=None):
    """Correct `species` on one condition, and attribute it where evidence allows.

    `species` is the reagent dimension of the case fingerprint: WHICH chemical this
    setting applies to. Two things had been landing in it that are not reagents.

    A unit: `carrier_gas_partial_pressure = 1 bar` arrived carrying `species='bar'`, the
    pressure unit copied into the chemical slot. The carrier gas is never named.

    A film material: a `structural_identity` condition describes the deposited object,
    and the material of that object already has its own places to live -- the case's
    `deposited_material`, and the condition's own `stack_materials`. Repeating it as
    `species` asserts the film was the dosed reagent.

    Neither is deleted for looking wrong; both are refused because the field means
    something they are not. What replaces them is nothing: a condition whose reagent is
    unknown stays unknown, because MISSING is not SAME and an unattributed setting must
    not silently fingerprint as an attributed one.

    Attribution runs only on positive evidence in the label the axis actually carried:
    a chemical the paper's own reagent inventory lists (tier A), or a role word the
    inventory binds to exactly one reagent (tier B). An inventory naming two candidates
    resolves nothing and is left alone.
    """
    sp = c.get("species")
    label = str(c.get("raw_axis_label") or "")
    if sp:
        why = None
        if str(sp).strip().lower() == str(c.get("unit") or "").strip().lower():
            why = ("%r is the unit of this condition, not a chemical species" % sp)
        elif c.get("structural_identity"):
            why = ("%r names the material of the deposited structure, which is not the "
                   "reagent a process setting applies to" % sp)
        if why:
            c = dict(c, species=None, species_removed=sp, species_basis=None,
                     species_evidence=why)
            if note and cid:
                note("invalid_species_removed", cid, why)
        return c
    if not label:
        return c
    named = R.complete_species_span(label, list(precursors or []) + list(coreactants or []))
    if named:
        return dict(c, species=str(named), species_basis="EXPLICIT_LABEL_SPECIES",
                    species_evidence="the axis label %r names %r outright, a reagent this "
                                     "paper's inventory lists" % (label, named))
    for pat, field in _ROLE_WORD:
        if not pat.search(label):
            continue
        pool = [x for x in ((precursors if field == "precursors" else coreactants) or []) if x]
        if len(pool) == 1:
            # The ROLE is explicit and local; the SPECIES is not. It is reached by the
            # paper's inventory listing exactly one reagent in that role, which is a
            # paper-wide uniqueness argument and weaker than the label naming the
            # chemical. The tier says which of the two actually happened.
            return dict(c, species=str(pool[0]), species_basis="ROLE_LABEL_PAPER_UNIQUE",
                        species_evidence="the axis label %r names the %s role explicitly; "
                                         "the species is resolved paper-wide, this paper's "
                                         "inventory listing exactly one %s: %r"
                                         % (label, field[:-1], field[:-1], pool[0]))
    return c


def progression_local(cond, member, progression_q):
    """Is this assertion PROVEN local to a member's progression, so it moves to
    progression context instead of fixing the case?

    Member/provenance scoped: only two proofs exist. The stating member itself
    traverses the quantity (its own axis sweeps it, so its statement describes
    its sweep), or the stated value is an interval -- an interval is a
    description of a sweep, never a fixed setting. A scalar stated by a member
    that does NOT traverse the quantity is that member's own fixed assertion and
    stays a candidate case condition, even when a sibling member sweeps the same
    quantity."""
    q = cond.get("quantity")
    if q not in progression_q:
        return False
    return (member.get("progression_coordinate") == q
            or cond.get("value_kind") == "range")


def _case(pid, i, members, P, paper_mat_roles, meas_by_entity, sample_by_code, note):
    """One ExperimentalCase from its merged candidates."""
    _prec = (P.scout.get("precursors") or []) if getattr(P, "scout", None) else []
    _core = (P.scout.get("coreactants") or []) if getattr(P, "scout", None) else []
    conds = {}
    # Quantities a member's own x axis TRAVERSES are progression coordinates of that
    # observation, not fixed settings of the nominal case: a stack caption's
    # "10-40 cycles" and a growth curve's cycle axis describe local intervals, and
    # promoting either to a case-defining condition would assert one fixed value for
    # an experiment the case's own members sweep. They are preserved as
    # progression context, with the member that stated them.
    progression_q = {m.get("progression_coordinate") for m in members
                     if m.get("progression_coordinate")}
    progression_ctx = []
    for m in members:
        for c in m["case_conditions"]:
            c = species_repair(c, _prec, _core)
            if progression_local(c, m, progression_q):
                progression_ctx.append(dict(
                    c, scope_note=("local to the stating member; this case's own "
                                   "members traverse %r as a progression coordinate"
                                   % c.get("quantity")),
                    stated_by=m.get("candidate_id")))
                continue
            k = (c["quantity"], c.get("species") or "")
            # A repaired interval outranks a scalar carrying the same key: it is the
            # value the source actually states. Directly-stated scalars outrank inherited
            # ones, as before.
            prev = conds.get(k)
            if prev is None:
                conds[k] = c
            elif c.get("value_kind") == "range" and prev.get("value_kind") != "range":
                conds[k] = c
            elif (prev.get("value_kind") != "range"
                  and c.get("provenance_type") == "directly_stated"):
                conds[k] = c
    mats = sorted({m["deposited_material"] for m in members if m.get("deposited_material")})
    scope_named = {}
    for m in members:
        for mat, recs in (m.get("scope_materials") or {}).items():
            scope_named.setdefault(mat, []).extend(recs)
    context_mats = sorted(set(mats) | set(scope_named))
    geos = sorted({m["geometry"] for m in members if m.get("geometry")})
    figs = sorted({m["source_figure"] for m in members if m.get("source_figure")})
    mids = sorted({m["measurement_id"] for m in members if m.get("measurement_id")})
    # A specimen realises a case because the SOURCE says so, not because a curve was
    # plotted from it. Requiring a Measurement here silently dropped every specimen whose
    # case the paper defines in its table but never plots.
    named_codes = {c for m in members
                   for c in (m.get("table_specimen_codes") or m.get("sample_codes") or [])}
    sids = sorted({s["sample_id"] for code, s in sample_by_code.items()
                   if code in named_codes
                   or any(mm in s["measurement_ids"] for mm in mids)},
                  key=lambda x: (len(x), x))
    strengths = [e for m in members for e in m["evidence"]]
    conf = (PC.EXPLICIT if len(members) > 1 and any(m["kind"] == "text_supported" for m in members)
            else PC.SUPPORTED if len(members) > 1 else PC.EXPLICIT)
    # A role is ASSERTED only from local evidence — the scope's own text, or the
    # resolver's own per-record material decision. The paper-wide inventory may propose a
    # CANDIDATE and nothing more, so a case can never publish "{M: DEPOSITED}" while its
    # deposited material is unresolved.
    roles, candidates_mat = {}, {}
    for mat in context_mats:
        local = R.primary_role(scope_named.get(mat) or [])
        if local:
            roles[mat] = local
        elif mat in mats:
            roles[mat] = R.DEPOSITED
        else:
            candidates_mat[mat] = (R.primary_role(paper_mat_roles.get(mat) or [])
                                   or R.DEPOSITED)
    asserted = sorted(roles)
    # The case's DEPOSITION TARGET is decided by evidence SPECIFICITY, not by union.
    # `mats` holds each member's own resolved target material — the measurand's film,
    # the process a text case describes. A member whose scope names SEVERAL deposited
    # layers (a stack micrograph, a multilayer caption) describes its SPECIMEN'S
    # composition; that is context about what the specimen is, and a specimen can
    # realise many depositions. Specimen-wide composition therefore never overrides a
    # more specific target: the target materials decide `deposited`, and every other
    # deposited-role material stays on the case as specimen context with its role and
    # provenance intact. Only where NO member resolves a target of its own does the
    # scope-level deposited set speak alone — the case a source documents purely as a
    # multi-material structure genuinely is one.
    scope_deposited = sorted(m for m, r in roles.items() if r == R.DEPOSITED)
    deposited = mats if mats else scope_deposited
    specimen_context = [
        {"material": m, "role": roles[m],
         "basis": ("named with role %s by a linked scope; not this case's deposition "
                   "target, which %s establishes more specifically"
                   % (roles[m], "the result/measurement evidence"
                      if mats else "nothing")),
         "evidence": [dict(rec) for rec in (scope_named.get(m) or [])][:4]}
        for m in sorted(roles)
        if mats and m not in mats]
    material_status = ("ASSERTED" if asserted else
                       "CANDIDATE_ONLY" if candidates_mat else "UNRESOLVED")
    material_status_reason = {
        "ASSERTED": None,
        "CANDIDATE_ONLY": ("no local evidence names a material for this result; %s comes "
                           "only from the paper-wide inventory"
                           % ", ".join(sorted(candidates_mat))),
        "UNRESOLVED": "no material evidence at any scope for this result",
    }[material_status]
    warn = []
    if not asserted:
        warn.append("material %s: %s" % (material_status, material_status_reason))
    if len(mats) > 1:
        warn.append("members of this case target different deposited materials: %s"
                    % mats)
    elif not mats and len(deposited) > 1:
        warn.append("no member resolves a single target material; the source documents "
                    "this case as a multi-material structure: %s" % deposited)
    if len(geos) > 1:
        warn.append("several geometries: %s" % geos)
    if not conds:
        warn.append("no case-defining condition value is known for this case")
    label = next((m.get("label") for m in members if m.get("label")), None)
    synth = next((m.get("synthesis_label") for m in members if m.get("synthesis_label")), None)
    _merged_material = deposited[0] if len(deposited) == 1 else None
    return fold_timing_generalizations(
        resolve_timing_conflicts(qualify_case_timing_steps(bind_gas_roles_to_case(
        bind_context_controls_to_case(
        bind_step_species(bind_case_chemistry({
        "case_id": "CASE-%s-%03d" % (pid[:6].upper(), i),
        "paper_id": pid, "label": label, "synthesis_label": synth,
        "deposited_material": _merged_material,
        "deposited_materials": deposited,
        # the linked specimen's OTHER deposited layers -- what the specimen is made of,
        # as distinct from what this case deposits. Kept with roles and evidence so a
        # multilayer stays queryable as structure without corrupting the case target.
        "specimen_context_materials": specimen_context,
        "context_materials": asserted, "material_roles": roles,
        "material_candidates": candidates_mat,
        "material_status": material_status,
        "material_status_reason": material_status_reason,
        "material_evidence_scope": ("figure/panel scope" if scope_named else
                                    "resolver per-record decision" if mats else
                                    "paper_candidate_only" if candidates_mat else None),
        "multi_material_context": len(asserted) > 1,
        "process_type": next((m["process_type"] for m in members if m.get("process_type")), None),
        # A member may resolve no chemistry of its own while the merged case does know its
        # deposited material. The paper's process card is then narrowed to that material by
        # its metal -- the same rule the resolver uses to pick a channel -- so a panel whose
        # own record named no reagent still reports the one the paper ran.
        "precursors": (sorted({p for m in members for p in (m.get("precursors") or [])})
                       or _card_reagents(getattr(_cand, "process_card", None),
                                         _merged_material, "precursors")),
        "coreactants": (sorted({p for m in members for p in (m.get("coreactants") or [])})
                        or _card_reagents(getattr(_cand, "process_card", None),
                                          _merged_material, "coreactants")
                        or (getattr(_cand, "process_card", None) or {}).get(
                            "coreactants") or []),
        "case_defining_conditions": [conds[k] for k in sorted(conds)],
        # member-local sweep/progression intervals, preserved with their member and
        # never part of the case's nominal identity
        "progression_context_conditions": progression_ctx,
        # a merged case has one geometry when its members agree; where they disagree it
        # genuinely has none, which is a statement about the members and not a gap
        "geometry": geos[0] if len(geos) == 1 else None,
        "geometries": geos,
        # the source travels with the value instead of being restated as a default
        "geometry_source": next(
            (m.get("geometry_source") for m in members
             if m.get("geometry_source") == "figure/panel caption"),
            next((m.get("geometry_source") for m in members if m.get("geometry_source")),
                 "paper-level deterministic classification")),
        "geometry_evidence": next((m.get("geometry_evidence") for m in members
                                   if m.get("geometry_evidence")), None),
        "measurement_ids": mids, "sample_ids": sids, "deposition_run_ids": [],
        "study_series_ids": [], "candidate_ids": [m["candidate_id"] for m in members],
        "source_figures": figs,
        "source_panels": sorted({"%s%s" % (m["source_figure"], m["source_panel"])
                                 for m in members if m.get("source_figure")}),
        "n_members": len(members), "member_kinds": sorted({m["kind"] for m in members}),
        # the quantity each sweep member was expanded on, so the invariant "a swept case
        # carries its own varied value" can be checked rather than asserted
        "swept_quantities": sorted({c["quantity"] for m in members
                                    if m["kind"] == "sweep_point"
                                    for c in m["case_conditions"]
                                    if c.get("provenance_type") == "derived_from_sweep_axis"}),
        "identity_evidence": strengths, "confidence": conf, "warnings": warn,
    })))))))


# ---------------------------------------------------------------- representation groups
def representation_groups(P, note):
    """{entity_id: holder_entity_id} for panels that are REDRAWN VIEWS of one measurement.

    Within one printed figure, curves carrying the same series legend are the same
    underlying measurement: Fig. 9's '100 nm' curve appears in the as-measured panel, the
    scaled panel and the normalized panel. A group is only formed when the panels declare
    at least two DIFFERENT representation types, so an ordinary multi-panel figure whose
    panels merely share a legend is untouched.

    The holder is the as-measured (or otherwise primary) panel; it alone carries the case.
    """
    by_fig = defaultdict(lambda: defaultdict(list))
    reps = {}
    for ent in P.entities:
        printed = str(ent.get("printed_figure_number") or "")
        panel = (ent.get("panel") or "").lower()
        if not printed or not panel:
            continue
        clause = PE.panel_clauses(P.printed_caption(printed)).get(panel, "")
        rep, _ = PE.representation_of(clause)
        reps[ent["entity_id"]] = rep or "primary"
        # A panel with NO legend gives no evidence of depicting the same thing as its
        # neighbours. Grouping on the empty label made the eight panels of a saturation
        # figure — each varying a DIFFERENT recipe parameter — look like representations
        # of one measurement, and swallowed 7 of 8 design sweeps.
        lab = _norm(ent.get("source_series"))
        if lab in ("<single>", "primary", "None", ""):
            continue
        by_fig[printed][lab].append(ent)

    holder_of, groups = {}, []
    for printed, by_label in sorted(by_fig.items()):
        for label, ents in sorted(by_label.items()):
            if len(ents) < 2 or not label:
                continue
            kinds = {reps[e["entity_id"]] for e in ents}
            if len(kinds) < 2:
                continue                     # same view repeated: not a representation set
            # A representation redraws ONE measurement. Panels that sweep different
            # case-defining quantities are different experiments, however alike their
            # legends look.
            swept = {str(e.get("coordinate") or "") for e in ents
                     if D.axis_role(e.get("coordinate"), e.get("x_axis_role"),
                                    raw_label=(e.get("x_semantics") or {}).get("raw_label"))[0]
                     == D.CASE_DEFINING_PROCESS_SETTING}
            if len(swept) > 1:
                note("representation_group_declined", "figure %s / %r" % (printed, label),
                     "panels sweep different case-defining quantities (%s), so they are "
                     "different experiments rather than views of one measurement"
                     % ", ".join(sorted(swept)))
                continue
            ents = sorted(ents, key=lambda e: (e.get("panel") or ""))
            holder = next((e for e in ents if reps[e["entity_id"]] == "as_measured"),
                          next((e for e in ents if reps[e["entity_id"]] == "primary"),
                               ents[0]))
            for e in ents:
                holder_of[e["entity_id"]] = holder["entity_id"]
            groups.append({"printed_figure": printed, "series_label": label,
                           "holder": holder["entity_id"],
                           "members": [{"entity_id": e["entity_id"], "panel": e.get("panel"),
                                        "representation": reps[e["entity_id"]]}
                                       for e in ents]})
            note("representation_group", "figure %s / %r" % (printed, label),
                 "panels %s show one measurement in %d representations (%s); the "
                 "as-measured panel carries the case"
                 % (", ".join(e.get("panel") or "?" for e in ents), len(kinds),
                    ", ".join(sorted(kinds))))
    return holder_of, groups


# ------------------------------------------------------------------- text-only cases
_PER_CYCLE = [
    (re.compile(r"\b(?:exposure|pulse|dose)\w*\s+was\s+repeated\s+(\d+|one|two|three|four)\s+"
                r"times?\s+for\s+one\b", re.I), "precursor_exposures_per_cycle"),
    (re.compile(r"\brepeated\s+(\d+|one|two|three|four)\s+times?\s+for\s+one\s+\S+\s+exposure\b",
                re.I), "precursor_exposures_per_cycle"),
    (re.compile(r"\bonly\s+(one|1)\s+(?:precursor\s+)?(?:pulse|exposure)\s+was\s+applied\b",
                re.I), "precursor_exposures_per_cycle"),
    (re.compile(r"\b(\d+|one|two|three|four)\s+(?:precursor\s+)?(?:pulses|exposures)\s+"
                r"(?:were\s+)?applied\s+during\s+each\s+(?:ALD\s+)?cycle\b", re.I),
     "precursor_exposures_per_cycle"),
]
_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4}


def text_cases(P):
    """Deposition cases stated in prose, for papers whose process variants are described
    but never plotted as an x-y process curve.

    A variant is only emitted when the SAME case-defining quantity takes DIFFERENT values
    in different sentences of the methods — i.e. the text itself contrasts two process
    executions. A single uncontrasted statement adds no case the figures do not already
    carry, so it is not emitted.
    """
    variants = []
    for sent in _sentences(P.methods):
        for rx, quantity in _PER_CYCLE:
            m = rx.search(sent)
            if not m:
                continue
            raw = m.group(1).lower()
            val = _WORD_NUM.get(raw, None)
            if val is None:
                try:
                    val = int(raw)
                except ValueError:
                    continue
            prod = re.search(r"\bfor the (?:creation|synthesis|preparation|fabrication) "
                             r"of (?:the |a |an )?([^,(.]{3,60})", sent, re.I)
            variants.append({"quantity": quantity, "value": val, "sentence": _norm(sent)[:300],
                             "matched": _norm(m.group(0)),
                             "product": _norm(prod.group(1)) if prod else None})
            break
    vals = {v["value"] for v in variants}
    if len(vals) < 2:
        return []
    shared = _shared_process_conditions(P)
    mat = P.materials[0] if len(P.materials) == 1 else None
    out = []
    for v in sorted(variants, key=lambda x: x["value"]):
        conds = list(shared) + [{
            "quantity": v["quantity"], "value": v["value"], "unit": None,
            "role": R.CASE_DEFINING,
            "role_basis": "per-cycle process repetition stated in the methods",
            "provenance_type": "directly_stated", "source": "methods",
            "evidence": v["sentence"]}]
        out.append({"label": (v["product"] or "%s per cycle = %d"
                              % (v["quantity"], v["value"])),
                    "synthesis_label": v.get("product"),
                    "conditions": conds, "material": mat, "printed_figure": None,
                    "sentence": v["sentence"],
                    "evidence": "the methods contrast %d distinct per-cycle process "
                                "executions; this is one of them" % len(vals)})
    return out


def _shared_process_conditions(P):
    """Case-defining conditions the methods state for the whole process."""
    out = []
    for q, key in (("cycle_number", "ncycles"), ("deposition_temperature", "temperature_C")):
        v = P.card.get(key)
        if v is not None:
            out.append({"quantity": q, "value": v,
                        "unit": "cycle" if q == "cycle_number" else "°C",
                        "role": R.CASE_DEFINING, "role_basis": "paper process card",
                        "provenance_type": "methods_default", "source": "methods",
                        "evidence": "paper-level process card field %r" % key})
    m = re.search(r"\b(\d{2,5})\s+ALD\s+cycles\s+were\s+applied", P.methods, re.I)
    if m and not any(c["quantity"] == "cycle_number" for c in out):
        out.append({"quantity": "cycle_number", "value": int(m.group(1)), "unit": "cycle",
                    "role": R.CASE_DEFINING, "role_basis": "stated cycle count",
                    "provenance_type": "directly_stated", "source": "methods",
                    "evidence": _norm(m.group(0))})
    return out


# ------------------------------------------------------------------- link discovery
def discover_links(P, candidates, sample_by_code, out, note,
                   series_members=None, table_cols=None):
    """Positive linkage records between case candidates.

    Three generic sources, in descending strength:
      1. EXPLICIT — two candidates whose source scopes name the SAME specimen code.
      2. EXPLICIT — a scope that states 'the same films/sample/run' and cites another
         figure, linking this scope to that figure's candidates.
      3. SUPPORTED — a caption that enumerates the case-defining values it shows
         ("films grown at 100 and 300 C") and another scope that sweeps the same
         quantity over values including them.

    Nothing else licenses a merge.
    """
    links = []
    by_scope = defaultdict(list)
    for c in candidates:
        by_scope[(c["source_figure"], c["source_panel"])].append(c)

    # -- 1. the SAME, UNAMBIGUOUSLY identified specimen ---------------------------
    # A caption that lists three specimens for three curves without saying which is which
    # identifies no curve's specimen. Only a candidate measured on exactly one named
    # specimen can carry a specimen-based link; anything else is an absence of evidence,
    # and absence never licenses a merge.
    by_code = defaultdict(list)
    for c in candidates:
        codes = c.get("sample_codes") or []
        if len(codes) == 1:
            by_code[codes[0]].append(c)
    for code, group in sorted(by_code.items()):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if (a["source_figure"], a["source_panel"]) == \
                        (b["source_figure"], b["source_panel"]):
                    continue
                links.append({"a": a["candidate_id"], "b": b["candidate_id"],
                              "strength": PC.EXPLICIT,
                              "reason": "both results are measured on specimen %r" % code,
                              "evidence": note("shared_sample_code",
                                               "%s <-> %s" % (a["candidate_id"],
                                                              b["candidate_id"]),
                                               "specimen %r identifies both figure %s%s and "
                                               "figure %s%s"
                                               % (code, a["source_figure"], a["source_panel"],
                                                  b["source_figure"], b["source_panel"]))})

    # -- 2. explicit same-thing statement citing another figure -------------------
    # Evidence scope follows the STATEMENT's own position. A same-sample sentence in
    # one panel's caption clause speaks about that panel's results and links only that
    # panel's candidates; a statement in the caption preamble or the body text near the
    # figure is figure-wide and links every panel. Letting a panel clause act
    # figure-wide is how one panel's specimen identity leaked onto siblings that merely
    # share the printed caption.
    #
    # The citation is read at the same precision the source wrote it: "Fig. 2b" cites
    # PANEL b of figure 2 and links only that panel's candidates; "Fig. 2" cites the
    # whole figure.
    _CITE = re.compile(r"\bFig(?:ure)?s?\.?\s*(\d+)\s*([a-h])?\b", re.I)
    for (printed, panel), group in by_scope.items():
        if not printed:
            continue
        clauses = PE.panel_clauses(P.printed_caption(printed)) or {}
        own_clause = clauses.get(panel or "", "") if panel else ""
        figure_wide = " ".join([clauses.get("", "") or
                                ("" if clauses else P.printed_caption(printed)),
                                P.body_near(printed)])
        scoped = ([(own_clause, "panel %s%s caption clause" % (printed, panel))]
                  if own_clause else []) + [(figure_wide, "figure-wide text")]
        for text, where in scoped:
            for e in [x for x in PE.linkage_evidence(text)
                      if x["kind"] == "explicit_same"]:
                for cf, cp in {(mm.group(1), (mm.group(2) or "").lower())
                               for mm in _CITE.finditer(e["span"])}:
                    if cf == printed and (not cp or cp == (panel or "").lower()):
                        continue                      # a self-citation links nothing new
                    targets = [c for c in candidates
                               if c["source_figure"] == cf
                               and (not cp or (c["source_panel"] or "").lower() == cp)]
                    for a in group:
                        for b in targets:
                            links.append({
                                "a": a["candidate_id"], "b": b["candidate_id"],
                                "strength": PC.EXPLICIT,
                                "reason": "explicit %r in %s citing figure %s%s"
                                          % (e["label"], where, cf, cp),
                                "evidence": note("explicit_same_statement",
                                                 "fig %s%s -> fig %s%s"
                                                 % (printed, panel or "", cf, cp),
                                                 e["span"], matched=e["matched"],
                                                 statement_scope=where)})

    # -- 4. an author series whose ONLY varying tabulated column is an instrument
    #       setting: its specimens share the nominal deposition case by the paper's own
    #       tabulated parameters. This is positive evidence, not an absence of evidence —
    #       the table states every case-defining column and they are equal.
    for letter, codes in sorted((series_members or {}).items()):
        codes = sorted(codes)
        q, role, ev = table_series_variable(P, table_cols or [], codes)
        if role != R.MEASUREMENT_SETTING:
            continue
        # Restricted to the panels of ONE printed figure that cites this series. Across
        # figures the specimens are separately identified and their own conditions decide;
        # letting this rule reach across figures chained unrelated cases together.
        cited = {c["source_figure"] for c in candidates
                 if c["source_figure"] and re.search(r"\bSeries\s+%s\b" % re.escape(letter),
                                                     P.printed_caption(c["source_figure"]),
                                                     re.I)}
        members = [c for c in candidates if c["source_figure"] in cited]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                links.append({
                    "a": members[i]["candidate_id"], "b": members[j]["candidate_id"],
                    "strength": PC.SUPPORTED,
                    "reason": "specimens of Series %s differ only in %r, an instrument "
                              "setting; every case-defining column of the paper's "
                              "specimen table is equal" % (letter, q),
                    "evidence": note("measurement_setting_series",
                                     "Series %s" % letter, ev or "", varied=q,
                                     role=role, members=codes)})

    # -- 3. caption enumerating the case-defining values it shows -----------------
    for (printed, panel), group in by_scope.items():
        if not printed:
            continue
        clause = PE.panel_clauses(P.printed_caption(printed)).get(panel or "", "") or \
            P.printed_caption(printed)
        for quantity, values, span in enumerated_settings(clause):
            for a in group:
                akeys = {(c["quantity"], PC._fmt(c["value"])) for c in a["case_conditions"]}
                if not any(q == quantity for q, _ in akeys):
                    continue
                aval = next(v for q, v in akeys if q == quantity)
                if aval not in {PC._fmt(v) for v in values}:
                    continue
                for b in candidates:
                    # a different PANEL of the SAME printed figure: 2a, 2b and 2c are
                    # exactly the cross-result link this rule exists to find. The
                    # enumeration is the caption describing what ITS OWN figure shows,
                    # so it licenses nothing beyond that figure -- reaching further
                    # turned every shared setting value into a corpus-wide chain and
                    # fused unrelated experiments that merely reused a temperature.
                    if b["source_figure"] != printed:
                        continue
                    if (b["source_figure"], b["source_panel"]) == (printed, panel):
                        continue
                    if b["candidate_id"] == a["candidate_id"]:
                        continue
                    bkeys = {(c["quantity"], PC._fmt(c["value"])) for c in b["case_conditions"]}
                    if (quantity, aval) in bkeys:
                        links.append({
                            "a": a["candidate_id"], "b": b["candidate_id"],
                            "strength": PC.SUPPORTED,
                            "reason": "the caption of figure %s enumerates %s = %s, which "
                                      "figure %s also reports" % (printed, quantity,
                                                                  ", ".join(PC._fmt(v) for v in values),
                                                                  b["source_figure"]),
                            "evidence": note("enumerated_settings",
                                             "%s <-> %s" % (a["candidate_id"], b["candidate_id"]),
                                             span, quantity=quantity,
                                             values=[PC._fmt(v) for v in values])})
    return links


#: "grown at the temperatures of 100 and 300 C" / "at 100, 200 and 300 C" -- and the
#: per-value-unit form a caption prefers: "temperatures of 50 C, 200 C and 250 C".
#: Each enumerated value may carry the unit itself, or the list may state it once at
#: the end; both are one enumeration of one quantity.
_ENUM_UNIT = r"°?\s?C\b|s\b|cycles?\b|nm\b|Torr\b|Pa\b|mbar\b|K\b"
_ENUM = re.compile(
    r"\b(?:at|of|to|using|with)\s+(?:the\s+)?(?:temperatures?|pulse times?|purge times?|"
    r"cycles?|exposure times?)?\s*(?:of\s+)?"
    r"((?:\d+(?:\.\d+)?(?:\s*(?:%(u)s))?)(?:\s*(?:,|and)\s*"
    r"\d+(?:\.\d+)?(?:\s*(?:%(u)s))?)+)" % {"u": _ENUM_UNIT}, re.I)
_ENUM_UNIT_RX = re.compile(_ENUM_UNIT, re.I)
_UNIT_Q = [(re.compile(r"^°?\s?C$", re.I), "deposition_temperature"),
           (re.compile(r"^s$", re.I), None),
           (re.compile(r"^cycles?$", re.I), "cycle_number"),
           (re.compile(r"^nm$", re.I), None)]
_CTX_Q = [(re.compile(r"temperature", re.I), "deposition_temperature"),
          (re.compile(r"pulse", re.I), "pulse_time"),
          (re.compile(r"purge", re.I), "purge_time"),
          (re.compile(r"cycle", re.I), "cycle_number"),
          (re.compile(r"exposure", re.I), "exposure_time")]


def enumerated_settings(text):
    """(quantity, [values], span) for each explicit enumeration of settings in a caption.

    Unicode degree variants are folded first, so "50 ◦ C, 200 ◦ C and 250 ◦ C" reads the
    same as "50, 200 and 250 °C". The unit may sit on each value or once at the end.
    """
    out = []
    text = C.fold_math(text or "")
    for m in _ENUM.finditer(text):
        vals = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group(1))]
        um = _ENUM_UNIT_RX.search(m.group(1)) or _ENUM_UNIT_RX.match(text[m.end():m.end() + 10].lstrip())
        unit = (um.group(0) if um else "").strip()
        q = None
        for rx, qq in _UNIT_Q:
            if rx.match(unit) and qq:
                q = qq
                break
        if not q:
            head = text[max(0, m.start() - 90):m.start()]
            for rx, qq in _CTX_Q:
                if rx.search(head) or rx.search(m.group(0)):
                    q = qq
                    break
        if q and len(vals) >= 2:
            out.append((q, vals, _norm(text[max(0, m.start() - 80):m.end() + 40])))
    return out


# ---------------------------------------------------------------------- deposition runs
def deposition_runs(P, out, sample_by_code, note):
    """DepositionRun objects, only where the source makes a run statement.

    An explicit shared-run sentence that also names specimens produces one run holding
    those specimens. An explicit different-run statement produces a run SET marker
    recording that the samples behind that scope were made in distinct runs — it never
    invents numbered runs that the paper does not name.
    """
    runs = []
    seen = set()
    for sent in _sentences(P.md):
        for e in PE.linkage_evidence(sent):
            if e["label"] == "same_run":
                ctx = sent
                codes = [c["code"] for c in PE.sample_codes(ctx)]
                sers = [s["series"] for s in PE.series_refs(ctx)]
                if not codes and sers:
                    codes = sorted({c for s in sers
                                    for c in _series_codes(out, s)})
                key = ("SAME", tuple(sorted(codes)), e["matched"].lower())
                if key in seen:
                    continue
                seen.add(key)
                sids = [sample_by_code[c]["sample_id"] for c in codes if c in sample_by_code]
                runs.append({
                    "run_id": "RUN::%s::%02d" % (P.pid, len(runs) + 1), "paper_id": P.pid,
                    "kind": "SHARED_RUN", "sample_codes": codes, "sample_ids": sids,
                    "experimental_case_ids": sorted({c for s in sids
                                                     for c in _sample_cases(out, s)}),
                    "same_run_evidence": _norm(e["span"]),
                    "matched": e["matched"], "series_reference": sers,
                    "confidence": PC.EXPLICIT,
                    "evidence": note("deposition_run", "shared run",
                                     _norm(e["span"]), samples=codes)})
            elif e["label"] == "different_run":
                key = ("DIFF", e["matched"].lower(), _norm(sent)[:60])
                if key in seen:
                    continue
                seen.add(key)
                figs = sorted(set(re.findall(r"\bFig(?:ure)?\.?\s*(\d+)", sent, re.I)))
                runs.append({
                    "run_id": "RUNSET::%s::%02d" % (P.pid, len(runs) + 1), "paper_id": P.pid,
                    "kind": "DISTINCT_RUNS", "sample_codes": [], "sample_ids": [],
                    "experimental_case_ids": [],
                    "same_run_evidence": None,
                    "different_run_evidence": _norm(e["span"]),
                    "matched": e["matched"], "source_figures": figs,
                    "note": "the source states that these results come from DIFFERENT runs "
                            "realising the same nominal process settings; the individual "
                            "runs are not numbered by the paper, so no numbered run "
                            "objects are invented",
                    "confidence": PC.EXPLICIT,
                    "evidence": note("deposition_run", "distinct runs",
                                     _norm(e["span"]), figures=figs)})
    return runs


def _series_codes(out, letter):
    s = next((x for x in out["study_series"]
              if x["author_series_name"].endswith(" %s" % letter)), None)
    return s["member_sample_codes"] if s else []


_SERIES_VAR = [
    (re.compile(r"pillar (?:layout|design|densit\w+)", re.I), "pillar_layout", "SAMPLE_GEOMETRY"),
    (re.compile(r"(?:objective|magnificat\w+|spot[\s-]?size)", re.I), "reflectometer_spot_size",
     R.MEASUREMENT_SETTING),
    (re.compile(r"channel height", re.I), "feature_height", "SAMPLE_GEOMETRY"),
    (re.compile(r"number of (?:ALD )?cycles|cycle number", re.I), "cycle_number", R.CASE_DEFINING),
    (re.compile(r"(?:TMA |precursor )?pulse time", re.I), "pulse_time", R.CASE_DEFINING),
    (re.compile(r"purge time", re.I), "purge_time", R.CASE_DEFINING),
]


#: "<variable phrase> for Series <X>" — how a table footnote declares what each series
#: varies. Semicolon-separated lists are the normal form.
_SERIES_DECL = re.compile(r"([A-Za-z][A-Za-z0-9 /()\-]{2,60}?)\s+for\s+(?:the\s+)?"
                          r"Series\s+([A-Z])\b", re.I)
#: variable phrase -> (quantity, role). Matched on the phrase the AUTHOR wrote.
_DECL_QUANTITY = [
    # Which precursor/co-reactant was used is a case-defining choice of process
    # chemistry, not a setting of it: two films grown from different precursors are
    # different depositions however identical the temperatures and timings.
    (re.compile(r"\bco-?reactant\b|\bcounter[-\s]?reactant\b|\boxidant\b", re.I),
     "coreactant", R.CASE_DEFINING),
    # `precursor` only. A bare "reactant" used to land here, which inverted the role it
    # names: in ALD prose "reactant" contrasted with "precursor" IS the counter-reactant,
    # so the rule asserted the oxidant was the metal source. It is not remapped to
    # `coreactant` either -- alone the word is genuinely ambiguous, and an unresolved
    # discriminator asserts nothing. "chemistry" was dropped for the same reason: naming
    # the topic is not evidence of which side of the cycle a curve varies.
    (re.compile(r"\bprecursor\b", re.I), "precursor", R.CASE_DEFINING),
    (re.compile(r"pillar\s*(?:layout|design)", re.I), "pillar_layout", R.CASE_DEFINING),
    (re.compile(r"(?:reflectomet\w+\s*)?magnificat\w+|objective|spot\s*size", re.I),
     "reflectometer_magnification", R.MEASUREMENT_SETTING),
    (re.compile(r"channel\s*height|feature\s*height|trench\s*depth", re.I),
     "feature_height", R.CASE_DEFINING),
    (re.compile(r"(?:ALD\s*)?cycles?|cycle\s*number", re.I), "cycle_number", R.CASE_DEFINING),
    (re.compile(r"(?:\w+\s+)?pulse\s*time|dose\s*time|precursor\s*pulse", re.I),
     "pulse_time", R.CASE_DEFINING),
    (re.compile(r"purge\s*time|purge", re.I), "purge_time", R.CASE_DEFINING),
    (re.compile(r"temperature", re.I), "deposition_temperature", R.CASE_DEFINING),
    (re.compile(r"pressure", re.I), "working_pressure", R.CASE_DEFINING),
    (re.compile(r"exposure\s*time|exposure", re.I), "exposure_time", R.CASE_DEFINING),
]

#: the two sides of an ALD cycle, as a discriminator may name them
_PRECURSOR_TOKEN = re.compile(r"\bprecursor\b", re.I)
_COREACTANT_TOKEN = re.compile(r"\b(?:co-?|counter[-\s]?)?reactant\b|\boxidant\b", re.I)
#: quantities that are a DOSE of one reagent, so a sweep of them belongs to one side of
#: the cycle. A temperature or a cycle count is shared by both and cannot be so scoped.
_REAGENT_SCOPED_Q = {"exposure_time", "pulse_time", "dose", "purge_time"}


def reagent_scoped_quantity(q):
    """Whether the reagent is part of this quantity's identity, in any spelling.

    A timed-step quantity is reagent-scoped however it is written -- bare
    (`pulse_time`) or role-specialised (`precursor_pulse_time`) -- because the valve
    opens for one named chemical either way. Asked structurally so a spelling this
    module has never seen behaves the same.
    """
    return str(q or "") in _REAGENT_SCOPED_Q or PS.timing_kind(q) is not None


def compound_reagent_discriminator(q_raw):
    """Whether a between-curve discriminator names BOTH sides of the ALD cycle.

    "precursor/reactant" does not say the curves used different precursors -- it says one
    curve belongs to the precursor and the other to the counter-reactant. Read as a single
    role it collapsed to `precursor` and asserted the oxidant was the metal source.

    Generic over the phrasings that name two roles at once (precursor/reactant,
    precursor/co-reactant, precursor and oxidant); a discriminator naming ONE role is a
    genuine chemistry choice and is left alone.
    """
    t = str(q_raw or "")
    if not (_PRECURSOR_TOKEN.search(t) and _COREACTANT_TOKEN.search(t)):
        return False
    # "precursor" inside "co-reactant"-free text must be a separate token from the
    # reactant word, otherwise "precursor" alone would match both patterns
    return _COREACTANT_TOKEN.sub("", _PRECURSOR_TOKEN.sub("", t)).strip(" /,&-") != t


def series_definitions_from_text(text):
    """{series_letter: {quantity, role, phrase, evidence}} declared by the AUTHOR.

    A table footnote or a methods sentence that says what each series varies outranks any
    inference from the table's own columns: when two columns of a series differ, only the
    author knows which one the series is ABOUT.
    """
    out = {}
    for m in _SERIES_DECL.finditer(text or ""):
        phrase = _norm(m.group(1))
        letter = m.group(2).upper()
        # trim a leading connective ("and purge time for Series F", "; ALD cycles for …")
        phrase = re.sub(r"^(?:and|or|the|a|an|different|varying|varied)\s+", "", phrase,
                        flags=re.I).strip()
        q = role = None
        for rx, qq, rr in _DECL_QUANTITY:
            if rx.search(phrase):
                q, role = qq, rr
                break
        if not q or letter in out:
            continue
        out[letter] = {"quantity": q, "role": role, "phrase": phrase,
                       "evidence": _norm(text[max(0, m.start() - 60):m.end() + 30])[:240]}
    return out


def table_series_variable(P, table_cols, codes):
    """The column of the specimen table whose value actually DIFFERS across a series'
    members — that is what the series varies, and the column's own role says whether it
    is a deposition condition or an instrument setting.

    This is preferable to reading the series description in prose because it is derived
    from the paper's own tabulated parameters, and it types Series B's magnification as a
    MEASUREMENT_SETTING without any statement having to say so.
    """
    if not codes or len(codes) < 2:
        return None, R.UNRESOLVED_ROLE, None
    rows = [P.sample_table.get(c) for c in codes if c in P.sample_table]
    rows = [r for r in rows if r]
    if len(rows) < 2:
        return None, R.UNRESOLVED_ROLE, None
    varying = []
    for i, (q, unit, hint) in enumerate(table_cols):
        vals = {r["columns"][i] for r in rows if i < len(r["columns"])}
        if len(vals) > 1:
            varying.append((q, hint, sorted(vals)))
    if len(varying) != 1:
        return None, R.UNRESOLVED_ROLE, (
            "specimen table shows %d varying columns for this series (%s)"
            % (len(varying), ", ".join(v[0] for v in varying)) if varying else None)
    q, hint, vals = varying[0]
    role = R.CASE_DEFINING if hint == "CASE" else R.MEASUREMENT_SETTING
    return q, role, ("specimens %s differ only in %r (%s) in the paper's specimen table"
                     % (", ".join(codes), q, ", ".join(vals)))


def table_co_variation(P, table_cols, codes):
    """Every tabulated column that differs across a series' members.

    Reported alongside the declared variable so an incidental difference — one specimen
    also carrying a different pillar layout — is preserved as context rather than either
    erased or promoted to the series' purpose."""
    rows = [P.sample_table.get(c) for c in codes if c in P.sample_table]
    rows = [r for r in rows if r]
    if len(rows) < 2:
        return []
    out = []
    for i, (q, unit, hint) in enumerate(table_cols):
        vals = sorted({r["columns"][i] for r in rows if i < len(r["columns"])})
        if len(vals) > 1:
            out.append({"quantity": q, "unit": unit,
                        "role": R.CASE_DEFINING if hint == "CASE" else R.MEASUREMENT_SETTING,
                        "values": vals,
                        "evidence": "specimens %s differ in %r (%s) in the paper's "
                                    "specimen table" % (", ".join(codes), q, ", ".join(vals))})
    return out


def series_variable(P, letter):
    """What a named Series varies, and the role of that variable."""
    for m in re.finditer(r"[^.]*\bSeries\s+%s\b[^.]*\." % re.escape(letter), P.md, re.I):
        sent = _norm(m.group(0))
        for rx, q, role in _SERIES_VAR:
            if rx.search(sent):
                return q, role, sent[:260]
    return None, R.UNRESOLVED_ROLE, None


# ------------------------------------------------------- value-based specimen binding
_LEGEND_NUM = re.compile(r"(?:(?P<pre>[Xx×])\s*(?P<a>\d+(?:\.\d+)?)"
                         r"|(?P<b>\d+(?:\.\d+)?)\s*(?P<post>[Xx×])(?![A-Za-z])"
                         r"|(?P<c>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-zµμ°%/]+)?)")


def legend_values(label):
    """[{value, marker, unit}] for the numbers a curve legend carries.

    'X50 (5 µm)' yields 50 with a magnification marker and 5 with unit 'µm'. Keeping the
    marker and the unit is what makes the join decidable: a number carrying a unit can
    only match a column whose values carry that unit.
    """
    out = []
    for m in _LEGEND_NUM.finditer(str(label or "")):
        if m.group("a"):
            out.append({"value": float(m.group("a")), "marker": "magnification", "unit": None})
        elif m.group("b"):
            out.append({"value": float(m.group("b")), "marker": "magnification", "unit": None})
        elif m.group("c"):
            out.append({"value": float(m.group("c")), "marker": None,
                        "unit": (m.group("unit") or "").strip() or None})
    return out


def _num(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def value_join_specimens(entities, codes, values_by_code, col_unit):
    """{entity_id: specimen_code} when curve legends identify specimens BY VALUE.

    Not positional matching: each legend carries the value of the series' varied variable
    and that value names a row of the specimen table. A legend number carrying a unit the
    column does not use is ignored, which is what separates 'X50' (a magnification) from
    the '(5 µm)' spot size printed beside it.

    The join is accepted only when it is unique and total — every curve bound, every
    specimen used at most once, and exactly one such assignment possible. Anything less
    stays unbound.
    """
    want = {}
    for c in codes:
        v = values_by_code.get(c)
        if v is None:
            return {}, "specimen %r has no value for the joined quantity" % c
        want.setdefault(v, []).append(c)
    if any(len(v) > 1 for v in want.values()):
        return {}, "the joined column does not distinguish these specimens"
    options = {}
    for e in entities:
        hits = []
        for lv in legend_values(e.get("source_series")):
            if lv["unit"] and not _same_unit(lv["unit"], col_unit):
                continue                      # a unit the column does not use
            if lv["value"] in want:
                hits.append(want[lv["value"]][0])
        options[e["entity_id"]] = sorted(set(hits))
    if not options or any(not v for v in options.values()):
        return {}, "at least one curve legend carries no value matching the column"
    # enumerate assignments; accept only a unique perfect matching
    ids = sorted(options)
    solutions = []

    def walk(i, used, acc):
        if len(solutions) > 1:
            return
        if i == len(ids):
            solutions.append(dict(acc))
            return
        for c in options[ids[i]]:
            if c in used:
                continue
            acc[ids[i]] = c
            walk(i + 1, used | {c}, acc)
            acc.pop(ids[i], None)

    walk(0, set(), {})
    if len(solutions) != 1:
        return {}, ("%d assignments are consistent with the legends; the join is not "
                    "unique" % len(solutions))
    return solutions[0], None


#: "<n>× objective … estimated spot size of <v> µm", including the "…and…, respectively"
#: list form. Generic: it relates an instrument setting to a derived instrument quantity.
_SETTING_DERIVED = re.compile(
    r"(?P<mags>\d+(?:\.\d+)?(?:\s*[×xX])?(?:\s*and\s*\d+(?:\.\d+)?(?:\s*[×xX])?)*)"
    r"\s*[×xX]?\s*objective\s+lens(?:es)?[^.]{0,80}?spot\s+size\s+of\s+"
    r"(?P<vals>[^.]{1,60}?)\s*"
    r"(?P<unit>[µμu]\s?m|m\s?m|nm)", re.I)


def instrument_setting_map(text):
    """{magnification_value: {"spot_size": v, "unit": u, "evidence": …}} from the methods.

    Handles both the single form ("a 50× objective lens with an estimated spot size of
    5-6 µm") and the paired form ("10× and 5× objective lenses with an estimated spot size
    of 25 and 50 µm, respectively").
    """
    out = {}
    for m in _SETTING_DERIVED.finditer(_norm(text or "")):
        mags = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group("mags"))]
        raw_vals = m.group("vals")
        iv = PRG.parse_interval(raw_vals)
        vals = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw_vals)]
        unit = re.sub(r"\s+", "", m.group("unit"))
        unit = "µm" if unit in ("um", "μm", "mm", "µm") and "n" not in unit else unit
        ev = _norm(m.group(0))[:220]
        if len(mags) == len(vals) and len(mags) > 1:
            for mag, v in zip(mags, vals):
                out.setdefault(mag, {"spot_size": v, "unit": unit, "evidence": ev})
        elif len(mags) == 1:
            v = (iv["lower"] + iv["upper"]) / 2.0 if iv else (vals[0] if vals else None)
            rec = {"spot_size": v, "unit": unit, "evidence": ev}
            if iv:
                rec.update({"spot_size_lower": iv["lower"], "spot_size_upper": iv["upper"],
                            "value_kind": "range"})
            out.setdefault(mags[0], rec)
    return out


def nominal_identity_links(P, candidates, sample_by_code, note, blocked=None):
    """DESIGN_BRANCH_LINK — the source's own design says two results are the same case.

    Two situations, and only these two. Both require the SOURCE to have specified a
    COMPLETE nominal condition set; neither is condition equality inferred from partial
    overlap, which remains forbidden.

    1. **Same design branch.** Two panels of one printed figure plot different outputs
       against the same varied quantity at the same value — GPC in one panel and the
       refractive index in the other, both at 250 C. The author varied one parameter and
       measured two things; that is one deposition with two outputs.

    2. **Same tabulated specimen conditions.** Two results are measured on specimens whose
       rows in the paper's own specimen table agree on every deposition-defining column.
       The table is the author stating the design, so equality across a complete tabulated
       condition set is a positive statement, not an absence of contradiction. A
       measurement setting never participates.
    """
    links = []
    blocked = [] if blocked is None else blocked

    # ---- 1. same design branch, different output ---------------------------------
    by_branch = defaultdict(list)
    for c in candidates:
        if c.get("kind") != "design_branch":
            continue
        bv = [x for x in c["case_conditions"]
              if x.get("provenance_type") == "derived_from_design_branch"]
        if not bv:
            # The same reasoning applies when the figure states what distinguishes its
            # curves instead of sweeping it on an axis: two panels showing curves under
            # the SAME stated label are two outputs of one experiment. The author's label
            # is the positive statement; only the way it is drawn differs.
            bv = [x for x in c["case_conditions"]
                  if x.get("source") == "between_curve_legend"
                  and x.get("role") == R.CASE_DEFINING]
        if not bv:
            continue
        b = bv[0]
        # Keyed on the DESIGN SIGNATURE, not on figure+quantity+value. Keying on the
        # latter merged the SiO2 precursor dose with the Al2O3 precursor dose, and the
        # precursor purge with the plasma purge, purely because the numbers coincided.
        by_branch[(c["source_figure"], b.get("quantity"),
                   PC._fmt(b["value"]))].append((c, b))
    for (fig, _q, val), pairs in sorted(by_branch.items(), key=lambda kv: str(kv[0])):
        group = [c for c, _ in pairs]
        sig_of = {c["candidate_id"]: (b.get("design_signature") or ())
                  for c, b in pairs}
        panels = {c["source_panel"] for c in group}
        if len(group) < 2 or len(panels) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[i]["source_panel"] == group[j]["source_panel"]:
                    continue
                # Sharing a number is not sharing a design. Every design field must be
                # POSITIVELY known on both sides and equal; two unknowns are not a match.
                sig = sig_of[group[i]["candidate_id"]]
                sig_b = sig_of[group[j]["candidate_id"]]
                if not sig and not sig_b:
                    # a legend-labelled pair: the label itself is the identity, and the
                    # grouping key already required the same quantity and value
                    same, why = True, ("both panels label this curve with the same "
                                       "case-defining value")
                else:
                    same, why = D.signatures_identify_same_design(sig, sig_b)
                if not same:
                    blocked.append({
                        "a": group[i]["candidate_id"], "b": group[j]["candidate_id"],
                        "action": "BLOCKED", "strength": PC.SUPPORTED,
                        "reason": "same branch value %s in figure %s but not the same "
                                  "design: %s" % (val, fig, why),
                        "detail": why, "link_evidence": None})
                    continue
                links.append({
                    "a": group[i]["candidate_id"], "b": group[j]["candidate_id"],
                    "strength": PC.SUPPORTED, "link_class": "DESIGN_BRANCH_LINK",
                    "reason": "panels %s of figure %s plot different outputs at the same "
                              "design branch (%s) = %s"
                              % ("/".join(sorted(panels)), fig, ", ".join(sig), val),
                    "evidence": note("design_branch_link",
                                     "%s <-> %s" % (group[i]["candidate_id"],
                                                    group[j]["candidate_id"]),
                                     "same design branch (%s) = %s in figure %s, measured "
                                     "as %s" % (", ".join(sig), val, fig,
                                                " and ".join(sorted(panels))))})

    # ---- 2. specimens the paper's own table gives identical nominal conditions ----
    if P.sample_table:
        keyed = defaultdict(list)
        for code, sm in sample_by_code.items():
            k = D.nominal_key(sm.get("case_defining_conditions") or [])
            if k:
                keyed[k].append(code)
        code_of = {}
        for c in candidates:
            codes = c.get("sample_codes") or []
            if len(codes) == 1:
                code_of[c["candidate_id"]] = codes[0]
        for k, codes in sorted(keyed.items()):
            if len(codes) < 2:
                continue
            group = [c for c in candidates if code_of.get(c["candidate_id"]) in codes]
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    if code_of[a["candidate_id"]] == code_of[b["candidate_id"]]:
                        continue
                    links.append({
                        "a": a["candidate_id"], "b": b["candidate_id"],
                        "strength": PC.SUPPORTED,
                        "link_class": "DESIGN_BRANCH_LINK",
                        "reason": "specimens %s and %s have identical deposition-defining "
                                  "conditions in the paper's own specimen table"
                                  % (code_of[a["candidate_id"]], code_of[b["candidate_id"]]),
                        "evidence": note("tabulated_nominal_identity",
                                         "%s <-> %s" % (a["candidate_id"], b["candidate_id"]),
                                         "the specimen table gives both %s"
                                         % "; ".join("%s=%s" % (q, v) for q, _, v in k),
                                         specimens=sorted(codes))})
    return links


def design_factor(declared_quantity, phrase, spec_conditions, codes):
    """The structured condition components that ONE author-declared factor controls.

    An author declares a factor in words -- "TMA pulse time", "purge time", "ALD cycles".
    A structured recipe holds that factor as one or more components, and which components
    it means is a question the source answers, not a numeric coincidence:

      * the declared quantity selects the components of that KIND
        ("purge time" -> precursor_purge_time and coreactant_purge_time);
      * a species or step named in the phrase narrows it to that component
        ("TMA pulse time" -> the TMA component alone);
      * components that move TOGETHER across the series' specimens are ONE compound
        factor, not competing explanations. A purge series that advances both purges at
        once is a single varied factor whose value happens to be written twice.

    Returns (components, why) where components is a list of quantity names.
    """
    if not declared_quantity:
        return [], "the source declares no varied factor for this series"
    base = re.sub(r"^(?:precursor|coreactant|plasma)_", "", declared_quantity)
    cand = []
    for code in codes:
        for cd in (spec_conditions or {}).get(code) or []:
            q = cd["quantity"]
            if q in cand:
                continue
            if q == declared_quantity or q.endswith("_" + base) or q == base:
                cand.append(q)
    if not cand:
        return [], "no structured condition component matches %r" % declared_quantity
    # a species or step named in the declaration selects its own component
    named = []
    for code in codes:
        for cd in (spec_conditions or {}).get(code) or []:
            sp = cd.get("species")
            if (cd["quantity"] in cand and sp
                    and re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(str(sp)),
                                  phrase or "", re.I)
                    and cd["quantity"] not in named):
                named.append(cd["quantity"])
    if named:
        return named, ("the declaration %r names the reagent, selecting %s"
                       % (phrase, ", ".join(named)))
    if len(cand) == 1:
        return cand, "the declared factor %r is held by %s" % (phrase, cand[0])
    # several components of the declared kind: the ones that MOVE are the factor
    moving = [q for q in cand
              if len({str(cd.get("value"))
                      for code in codes
                      for cd in (spec_conditions or {}).get(code) or []
                      if cd["quantity"] == q}) > 1]
    if moving:
        return moving, ("the declared factor %r is carried by %s, which vary together "
                        "across these specimens and are therefore one factor"
                        % (phrase, " and ".join(moving)))
    return cand, ("the declared factor %r is held by %s"
                  % (phrase, " and ".join(cand)))


def series_design_factors(P, series_decls, series_members, spec_conditions):
    """{series_letter: {quantity, components, role, phrase, why}} -- the generic mapping
    from an author-declared experimental factor to the structured fields it controls."""
    out = {}
    for letter, decl in sorted((series_decls or {}).items()):
        codes = sorted(series_members.get(letter) or [], key=lambda x: (len(x), x))
        comps, why = design_factor(decl["quantity"], decl.get("phrase"),
                                   spec_conditions, codes)
        out[letter] = {"quantity": decl["quantity"], "components": comps,
                       "role": decl["role"], "phrase": decl.get("phrase"),
                       "members": codes, "why": why,
                       "evidence": decl.get("evidence")}
    return out


def build_value_joins(P, table_cols, series_decls, series_members, note,
                      spec_conditions=None, factors=None):
    """{entity_id: {code, matched, evidence, setting}} for curves that identify their
    specimen BY VALUE.

    Generalised from the earlier series-scoped version, which only fired when a figure
    named one series whose declared variable happened to be a table column and whose
    specimen count equalled the curve count. That missed every figure showing two series
    at once, and every figure whose legend carries a value of a column the series
    declaration does not name.

    The rule now: within one printed figure, take the specimens its caption names, and try
    each tabulated column in turn. A column is accepted only when the curve legends'
    values give a UNIQUE and TOTAL assignment onto those specimens — every curve bound,
    every specimen used at most once, exactly one such assignment possible. This is a
    value join, never list order; ambiguity leaves the binding unresolved.
    """
    out, notes = {}, []
    if not P.sample_table or not table_cols:
        return out, notes
    # Every quantity a specimen HAS, not every column the table prints. A composite recipe
    # cell ("0.1-4.0-0.1-4.0") is one column but four quantities, and the series that vary
    # inside it can only be joined once those components are addressable in their own
    # right. Roles come from the condition itself, so a tabulated instrument setting stays
    # a measurement setting.
    joinable_num, joinable_raw, roles = defaultdict(dict), defaultdict(dict), {}
    for code, conds in (spec_conditions or {}).items():
        for cd in conds:
            key = (cd["quantity"], cd.get("unit"))
            v = _num(cd.get("value"))
            if v is None:
                continue
            joinable_num[key][code] = v
            joinable_raw[key][code] = cd.get("value")
            roles[key] = "MEAS" if cd.get("role") == R.MEASUREMENT_SETTING else "CASE"
    # The fallback set is the table's OWN columns -- not every derived component. A
    # decomposed recipe field is only ever joined when the source declares the factor it
    # belongs to.
    col_names = {q for q, _u, _h in table_cols}
    joinable_cols = [(q, unit, roles[(q, unit)], vals)
                     for (q, unit), vals in sorted(joinable_num.items(),
                                                   key=lambda kv: str(kv[0]))
                     if q in col_names]
    instrument = instrument_setting_map(P.md)
    by_fig = defaultdict(list)
    for e in P.entities:
        pf = str(e.get("printed_figure_number") or "")
        if pf:
            by_fig[pf].append(e)
    for pf, ents in sorted(by_fig.items()):
        cap = P.printed_caption(pf)
        # A caption may enumerate SEVERAL specimen groups — "Sample 7, 8, and 9 (Series C)
        # … Sample 8, 10 and 11 (Series D)" — one per row of panels. Pooling them makes the
        # joined column stop distinguishing the specimens, so each enumeration is kept as
        # its own candidate group and tried separately.
        # Which specimens a panel shows is scoped by the author two ways, and a figure may
        # use either: a sentence per group of panels ("Sample 7, 8, and 9 (Series C).") or
        # a panel marker inside one sentence ("(a) … (sample 12, 13, 14 … Series E) and
        # (b) … (sample 12, 15, 16 … Series F)"). Reading only sentences pools the second
        # form into one group of five specimens that no factor can distinguish.
        groups = []

        def _add(text, scope_panel):
            codes = [c["code"] for c in PE.sample_codes(text)]
            letters = [s_["series"] for s_ in PE.series_refs(text)]
            for L in letters:
                codes += sorted(series_members.get(L) or [])
            codes = sorted({c for c in codes if c in P.sample_table},
                           key=lambda x: (len(x), x))
            if len(codes) >= 2 and (codes, scope_panel) not in [(g[0], g[2])
                                                               for g in groups]:
                groups.append((codes, sorted(set(letters)), scope_panel))

        for sent in _sentences(cap):
            _add(sent, None)
        for letter, clause in sorted(PE.panel_clauses(cap).items()):
            if letter:
                _add(clause, letter)
        if not groups:
            continue
        # group the figure's entities by panel: each panel is one display of the series
        by_panel = defaultdict(list)
        for e in ents:
            by_panel[(e.get("panel") or "").lower()].append(e)
        for panel, pents in sorted(by_panel.items()):
            if len(pents) < 2:
                continue
            best, hits = None, []
            for named, letters, scope_panel in groups:
                if scope_panel and scope_panel != panel:
                    continue          # a panel-scoped enumeration speaks only for its panel
                # The AUTHOR-DECLARED factor decides which field is joined. Scanning every
                # numeric field and taking whichever matched would let an unrelated column
                # that happens to share a number decide specimen identity.
                declared = [(L, (factors or {}).get(L)) for L in letters]
                declared = [(L, f) for L, f in declared if f and f.get("components")]
                if declared:
                    for L, f in declared:
                        vals, raws, unit = _factor_values(f["components"], spec_conditions,
                                                          named)
                        if not vals:
                            continue
                        joined, why = value_join_specimens(pents, named, vals, unit)
                        if joined:
                            hint = "MEAS" if f["role"] == R.MEASUREMENT_SETTING else "CASE"
                            q = "+".join(f["components"])
                            joinable_raw[(q, unit)] = raws
                            hits.append((q, unit, hint, joined))
                    continue
                # No declaration: fall back to the table's own columns, and only when one
                # of them explains the legends on its own.
                for q, unit, hint, vals in joinable_cols:
                    joined, why = value_join_specimens(pents, named, vals, unit)
                    if joined:
                        hits.append((q, unit, hint, joined))
            seen_assign, uniq = set(), []
            for h in hits:
                k = tuple(sorted(h[3].items()))
                if k not in seen_assign:
                    seen_assign.add(k)
                    uniq.append(h)
            hits = uniq
            if len(hits) == 1:
                best = hits[0]
            elif len(hits) > 1:
                # several (group, column) pairs explain the same legends: not unique
                notes.append({"figure": pf, "panel": panel,
                              "reason": "%d specimen-group/column combinations explain "
                                        "these legends" % len(hits)})
                note("value_join_declined", "figure %s panel %s" % (pf, panel),
                     "%d combinations are consistent; the join is not unique" % len(hits))
            if not best:
                continue
            q, unit, hint, joined = best
            for eid, code in joined.items():
                val = joinable_raw.get((q, unit), {}).get(code)
                setting = None
                if hint == "MEAS" and val is not None:
                    setting = {"quantity": q, "value": _numish(val), "unit": unit,
                               "role": R.MEASUREMENT_SETTING,
                               "role_basis": "tabulated instrument setting",
                               "provenance_type": "directly_stated",
                               "source": "specimen_table", "scope": "sample",
                               "evidence": "specimen %s is %s = %s" % (code, q, val)}
                    der = instrument.get(_numish(val))
                    if der:
                        setting["derived_quantity"] = {
                            "quantity": "spot_size", "value": der.get("spot_size"),
                            "unit": der.get("unit"), "value_kind": der.get("value_kind"),
                            "value_lower": der.get("spot_size_lower"),
                            "value_upper": der.get("spot_size_upper"),
                            "role": R.MEASUREMENT_SETTING,
                            "provenance_type": "directly_stated",
                            "evidence": der.get("evidence")}
                out[eid] = {
                    "code": code, "matched": "%s = %s" % (q, val),
                    "evidence": ("the curve legend carries the value of %s that the "
                                 "specimen table gives for specimen %s" % (q, code)),
                    "setting": setting}
                note("value_join", eid, out[eid]["evidence"], specimen=code,
                     quantity=q, value=val, printed_figure=pf, panel=panel)
    return out, notes


def _numish(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return x


# ------------------------------------------------- produced-material provenance chain
#: "the <qualifier> <material> replica/powder/film was deposited on the test electrodes"
#: The product named with the qualifier that identifies WHICH synthesis made it.
_PRODUCT_NAMED = re.compile(
    r"\b(?:the|a|an)\s+(?P<what>[A-Za-z0-9 \-]{0,40}?)\s*(?P<mat>{M})\s*"
    r"(?:[A-Za-z0-9\-]+\s+){0,3}?"
    r"(?P<form>replicas?|powders?|films?|coatings?|nanotubes?|particles?|materials?)\b",
    re.I)
#: A placement of something onto the thing that is subsequently measured. Searched in a
#: bounded window AFTER the product is named, because the two are routinely separate
#: sentences ("… replica was dispersed … The resulting suspension was deposited on the
#: test electrodes").
_PLACEMENT = re.compile(
    r"\b(?:was|were)\s+(?:then\s+)?(?P<verb>deposited|drop[\s-]?cast|micropipett\w+|"
    r"placed|applied|loaded|transferred|dispensed)\b[^.]{0,120}", re.I)
#: the measurement substrate a product is placed onto
_DEVICE = re.compile(r"\b(?:test\s+)?electrodes?|electrode\s+array|substrates?|"
                     r"current\s+collector|support|grid|chip\b", re.I)
#: a legend naming a control rather than the coated specimen
_REFERENCE_LABEL = re.compile(r"\b(?:bare|uncoated|blank|pristine|reference|control|"
                              r"without|as[\s-]?received|flat|planar\s+reference)\b", re.I)


def is_reference_series(label):
    """True when a curve legend names a comparison control rather than the product."""
    m = _REFERENCE_LABEL.search(str(label or ""))
    return (True, m.group(0)) if m else (False, None)


_SUFFIX = ("ular", "ical", "ally", "ing", "ers", "ar", "al", "ic", "es", "s")


def _figures_naming_product(P, material, form):
    """Printed figures whose own caption names this product (material AND form word).

    A caption that says "Impedance spectra of Pt electrode … with and without Pt replica
    deposited" identifies the replica; one that says "the bare platinum support and Pt
    Zeotile-4 coated electrode" does not say WHICH product coated it, and must not inherit
    a chain resolved elsewhere in the paper.
    """
    stem = _stem(str(form or ""))
    out = []
    for pf in sorted({str(e.get("printed_figure_number")) for e in P.entities
                      if e.get("printed_figure_number")}, key=lambda x: (len(x), x)):
        cap = P.printed_caption(pf)
        if not cap or material.lower() not in cap.lower():
            continue
        if any(_stem(w) == stem for w in re.split(r"[^A-Za-z0-9]+", cap) if len(w) > 3):
            out.append(pf)
    return out


def _figures_in_section(P, offset):
    """Printed figure numbers cited in the document section containing `offset`.

    Sections are delimited by markdown headings; the placement statement and the results
    it explains sit in the same one."""
    text = _norm(P.md)
    heads = [m.start() for m in re.finditer(r"#{1,6}\s", text)]
    lo = max([h for h in heads if h <= offset] or [0])
    hi = min([h for h in heads if h > offset] or [len(text)])
    return sorted({n for n in re.findall(r"Fig(?:ure)?\.?\s*(\d{1,2})\b",
                                         text[lo:hi], re.I)}, key=lambda x: (len(x), x))


def _stem(w):
    """Crude but sufficient: strip one common English suffix so a paper's own adjective
    matches its own noun ('tubular' / 'tubes' -> 'tub')."""
    w = w.lower()
    for suf in _SUFFIX:
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def produced_material_chain(P, cases, note):
    """Chains of the form  synthesis case -> product -> device -> measurement.

    A characterisation result acquires a deposition case only when the source states that
    the material the case PRODUCED was placed on the thing that was measured, and only
    when the qualifier in that sentence identifies exactly one case. "The replica was
    deposited on the support" names no protocol, so it identifies no case and the chain
    is recorded with its final hop left open.
    """
    mats = [m for m in (P.materials or []) if m]
    if not mats or not cases:
        return []
    alt = "|".join(re.escape(m) for m in sorted(mats, key=len, reverse=True))
    rx = re.compile(_PRODUCT_NAMED.pattern.replace("{M}", alt), re.I)
    text = _norm(P.md)
    chains, seen = [], set()
    for m in rx.finditer(text):
        window = text[m.end():m.end() + 500]
        pm = _PLACEMENT.search(window)
        if not pm:
            continue
        tail = _norm(m.group(0) + " … " + pm.group(0))
        if not _DEVICE.search(pm.group(0)):
            continue
        qual = _norm(m.group("what")).lower()
        qual_words = {_stem(w) for w in re.split(r"[^a-z0-9]+", qual) if len(w) > 3}
        hits = []
        for c in cases:
            label = _norm("%s %s" % (c.get("label") or "",
                                     c.get("synthesis_label") or "")).lower()
            terms = {_stem(w) for w in re.split(r"[^a-z0-9]+", label) if len(w) > 3}
            if qual_words & terms:
                hits.append(c)
        figs = _figures_naming_product(P, m.group("mat"), m.group("form"))
        key = (m.group("mat"), qual, _norm(pm.group(0))[:60])
        if key in seen:
            continue
        seen.add(key)
        chains.append({
            "product_material": m.group("mat"), "product_form": m.group("form"),
            "qualifier": qual or None,
            "device": _norm(_DEVICE.search(pm.group(0)).group(0)),
            "statement": _norm(tail)[:320],
            # A placement statement governs the figures whose own caption names the
            # PRODUCT it placed. Another section may prepare a different electrode and
            # describe it without naming the product; its results must not inherit this
            # chain merely because one resolved chain exists in the paper.
            "covers_figures": figs,
            "case_ids": [c["case_id"] for c in hits],
            "status": ("RESOLVED" if len(hits) == 1 else
                       "AMBIGUOUS_QUALIFIER" if len(hits) > 1 else
                       "PROVENANCE_CHAIN_INCOMPLETE"),
            "reason": (None if len(hits) == 1 else
                       "the qualifier %r matches %d synthesis cases" % (qual, len(hits))
                       if len(hits) > 1 else
                       "the statement names no qualifier that identifies one synthesis case"),
            "evidence": note("produced_material_placement",
                             "%s %s -> %s" % (m.group("mat"), m.group("form"),
                                              _norm(_DEVICE.search(pm.group(0)).group(0))),
                             _norm(tail)[:300]),
        })
    return chains


def _code_sort(item):
    """Specimen codes sort numerically when they are numbers, lexically otherwise."""
    c = str(item[0])
    return (0, int(c), "") if c.isdigit() else (1, 0, c)


def tabulated_case_links(candidates, table_case_of_code, note):
    """Link a figure result to the tabulated case of the specimen it names.

    The paper's table already states this specimen's deposition conditions, so a result
    measured on that specimen belongs to that case. This is positive linkage from a
    source statement -- the figure names the specimen and the table describes it -- not
    an inference from condition overlap. A result naming SEVERAL specimens links to none
    of them: which curve is which is exactly what is unstated.
    """
    links = []
    for c in candidates:
        if c.get("kind") == "tabulated_specimen":
            continue
        codes = c.get("sample_codes") or []
        if len(codes) != 1:
            continue
        tid = table_case_of_code.get(codes[0])
        if not tid:
            continue
        links.append({
            "a": tid, "b": c["candidate_id"], "strength": PC.EXPLICIT,
            "link_class": "TABULATED_NOMINAL_IDENTITY",
            "reason": "this result is measured on specimen %s, whose deposition "
                      "conditions the paper's specimen table states" % codes[0],
            "evidence": note("tabulated_case_link", c["candidate_id"],
                             "figure %s names specimen %s, which the specimen table "
                             "describes" % (c.get("source_figure"), codes[0]),
                             specimen=codes[0])})
    return links


def _factor_levels(components, spec_conditions, codes):
    """({code: level}, {code: raw}, unit) for one DesignFactor, numeric or not.

    A design factor need not be a number. "Pillar layout v1a / v1b / v2a" is three settings
    of one declared factor exactly as three purge times are; only the VALUE JOIN needs
    numbers, because only it compares against plotted legends.
    """
    vals, raws, unit = {}, {}, None
    for code in codes:
        seen = {}
        for cd in (spec_conditions or {}).get(code) or []:
            if cd["quantity"] in components and cd.get("value") is not None:
                v = _num(cd.get("value"))
                key = v if v is not None else str(cd.get("value")).strip()
                seen[key] = cd.get("value")
                unit = unit or cd.get("unit")
        if len(seen) == 1:
            k = list(seen)[0]
            vals[code], raws[code] = k, seen[k]
    return vals, raws, unit


def _factor_values(components, spec_conditions, codes):
    """({code: numeric value}, {code: raw value}, unit) for one DesignFactor.

    A factor with several co-varying components has ONE value per specimen -- the value
    those components share. When they genuinely disagree the specimen has no single factor
    value and is left out, which blocks the join rather than guessing.
    """
    vals, raws, unit = {}, {}, None
    for code in codes:
        seen = {}
        for cd in (spec_conditions or {}).get(code) or []:
            if cd["quantity"] in components:
                v = _num(cd.get("value"))
                if v is not None:
                    seen[v] = cd.get("value")
                    unit = unit or cd.get("unit")
        if len(seen) == 1:
            v = list(seen)[0]
            vals[code], raws[code] = v, seen[v]
    return vals, raws, unit


def _same_unit(a, b):
    """Whether two unit strings denote the same unit.

    A legend prints "1000 cycles" where the table column head says "cycles N" and the
    parsed unit is "cycle"; a legend prints "500 nm" against a column in "nm". Comparing
    the raw strings makes a plural or a stray case difference look like a different
    physical quantity and silently refuses a correct join.
    """
    def norm(u):
        u = re.sub(r"[\s.]+", "", str(u or "")).lower()
        return u[:-1] if len(u) > 2 and u.endswith("s") else u
    return norm(a) == norm(b)


def _paper_default_values(P):
    """{quantity: {values}} the paper states as its DEFAULT process.

    These are the values a result inherits by saying nothing. A figure that repeats one of
    them has told us nothing about which deposition it shows.
    """
    out = defaultdict(set)
    for c in _shared_process_conditions(P):
        out[c["quantity"]].add(PC._fmt(c["value"]))
    for e in P.entities:
        for b in e.get("bound_conditions") or []:
            if (b.get("source_kind") == "methods" or b.get("bound_at_scope") == "paper") \
                    and b.get("quantity") and b.get("value") is not None:
                out[b["quantity"]].add(PC._fmt(b["value"]))
    return out


def _matches_default(cond, defaults):
    """Whether this condition merely restates the paper's default value for its quantity.

    A quantity the paper states no default for is always distinguishing: the caption is
    then the only source for it.
    """
    vals = defaults.get(cond.get("quantity"))
    if not vals:
        return False
    return PC._fmt(cond.get("value")) in vals


def _emit_image_measurement(out, pid, ic, note, minted_case, ev=None, material=None):
    """The Measurement for an image-only figure. Emitted whether or not the figure
    supports a deposition case -- the paper reports this observation either way."""
    mid_i = "M::IMG::%s::F%s" % (pid, ic["printed_figure"])
    out["measurements"].append({
        "measurement_id": mid_i, "paper_id": pid,
        "technique": ic["techniques"],
        "technique_basis": "source_reported_panel" if ic["techniques"] else "unresolved",
        "technique_evidence": [], "measured_quantity": None, "measured_unit": None,
        "coordinate": None, "coordinate_unit": None,
        "entity_class": None, "classification": "image_supported_characterisation",
        "performed_on": None, "measures_case": [], "measurement_settings": [],
        "source": {"printed_figure": ic["printed_figure"], "panel": "",
                   "resolved_entity_id": None, "fig_docling_index": None,
                   "source_series": None},
        "caption_reference": ic["caption"][:400],
        "result_series_ids": [], "representation_id": None, "n_observations": 0,
        "repeat_measurement": False, "data_recovered": False,
        "recovery_cause": "image_only_figure",
        "recovery_detail": ic["reason"],
        "supports_deposition_case": minted_case,
        "case_link_status": "LINKED" if minted_case else "UNRESOLVED",
        "_material": material,
        "_conditions": [{"quantity": c["quantity"], "value": c.get("value"),
                         "unit": c.get("unit"), "role": R.CASE_DEFINING}
                        for c in ic["conditions"]],
        "evidence": [ev] if ev else [note("image_only_measurement", mid_i,
                                          ic["caption"][:300])],
        "confidence": PC.EXPLICIT if minted_case else PC.UNRESOLVED,
    })
    return mid_i


#: A candidate anchors a deposition case only on evidence of THIS deposition. These
#: provenance types each carry such evidence: the specimen table speaks about one
#: specimen, a design branch about one branch, a figure-local statement about what this
#: figure shows. A methods or paper-wide default speaks about the study as a whole and so
#: identifies no particular deposition.
_CASE_ANCHORING_PROVENANCE = {
    "sample_table_direct", "derived_from_table_recipe", "inherited_from_sample",
    "inherited_from_explicit_sample", "directly_stated", "figure_local_direct",
    "directly_stated_range", "derived_from_design_branch", "derived_from_sweep_axis",
}
#: Kinds that ARE a deposition statement in themselves.
_CASE_ANCHORING_KINDS = {"tabulated_specimen", "text_supported", "design_branch"}


#: A clause that describes a deposition happening, as opposed to a measurement of one.
_SYNTHESIS_CLAUSE = re.compile(
    r"\b(?:deposited|grown|coated|prepared|synthesi[sz]ed|covered\s+by|capped\s+with)\b",
    re.I)
#: A structural descriptor that distinguishes one deposited object from another: a layer
#: thickness, a stack, a layer count. "A 45 nm SiO2 film" and "a 12 nm SiO2 / 30 nm Al2O3
#: stack" are different depositions even when the recipe behind them is the same.
_STRUCTURE_DESCRIPTOR = re.compile(
    r"(\d+(?:\.\d+)?)\s*(nm|µm|um|μm|Å|A)\b|\b(?:single\s+layer|bilayer|stack|"
    r"nanolaminate|multilayer)\b", re.I)


def local_synthesis_evidence(caption, defaults):
    """The clause by which a caption describes THIS deposition, or None.

    A caption that says a film was deposited, and says how thick or how layered it is,
    is describing a particular deposited object. That is a source statement about which
    deposition the figure shows -- criterion (E) -- and it anchors a case even without a
    specimen code. A caption that only repeats the paper's default recipe describes the
    study's standard process and identifies nothing.
    """
    cap = _norm(caption or "")
    if not _SYNTHESIS_CLAUSE.search(cap):
        return None
    m = _STRUCTURE_DESCRIPTOR.search(cap)
    if not m:
        return None
    val = m.group(1)
    if val is not None:
        # a thickness that merely restates a paper default is not distinguishing
        for vals in (defaults or {}).values():
            if PC._fmt(val) in vals:
                return None
    return cap[max(0, m.start() - 90):m.end() + 60]


def _anchors_deposition_case(members):
    """(bool, why) -- whether this group of candidates identifies a deposition.

    A result that characterises a film is evidence that a measurement happened. Turning it
    into an ExperimentalCase additionally requires evidence about WHICH deposition it
    shows: a named specimen, an author-defined design branch or table row, or a local
    statement of the synthesis. Inherited defaults are not that evidence -- every result
    in the paper carries them, so a case minted from them alone is a case per figure
    rather than per deposition.
    """
    for m in members:
        if m.get("kind") in _CASE_ANCHORING_KINDS:
            return True, ""
        if m.get("sample_codes"):
            return True, ""
        if m.get("label") or m.get("synthesis_label"):
            return True, ""
        if m.get("local_synthesis"):
            return True, ""
        for c in m.get("case_conditions") or []:
            if c.get("provenance_type") in _CASE_ANCHORING_PROVENANCE:
                return True, ""
    figs = sorted({str(m.get("source_figure")) for m in members if m.get("source_figure")})
    return False, ("every deposition condition here is inherited from the paper's default "
                   "process and no specimen, design branch or local synthesis statement "
                   "identifies which deposition produced it (figure%s %s); the measurement "
                   "and its results are preserved and the case link is left unresolved"
                   % ("" if len(figs) == 1 else "s", ", ".join(figs) or "-"))


#: A unit of length. A deposited-layer thickness is only a thickness when it has one.
_LENGTH_UNIT = re.compile(r"^\s*(?:nm|\u00b5m|um|\u03bcm|\u00c5|A|mm|cm|m)\s*$", re.I)


def between_curve_conditions(ent, materials, note=None, known_species=()):
    """The condition that distinguishes THIS curve from its siblings, or [].

    A multi-curve figure usually says what differs between its curves -- the extraction
    records it as `between_curve_condition` with this curve's `between_curve_value`. That
    statement is figure-local direct evidence about this result and is exactly what tells
    two curves of one panel apart; without it, curves that differ in the source are
    indistinguishable in the model and either mint unsupported cases or collapse.

    Classification reuses the vocabulary already used for author-declared design factors
    and for x-axis roles, so a discriminator is typed the same way whether the source puts
    it on an axis, in a series declaration, or in a legend:

      * a PROGRESSION quantity is skipped -- stages of one growth are not specimens, and
        the specimen's own cycle count comes from stronger evidence elsewhere;
      * a STRUCTURE quantity identifies the deposited object (see is_structure_quantity);
      * otherwise the ontology's own role decides, and an UNRESOLVED discriminator
        contributes nothing rather than guessing.
    """
    q_raw = ent.get("between_curve_condition")
    v_raw = ent.get("between_curve_value")
    if not q_raw or v_raw in (None, "", "<single>"):
        return []

    # ---- both sides of the cycle named at once: WHOSE dose is swept, not which chemical
    if compound_reagent_discriminator(q_raw):
        sp = R.species_named_in(v_raw, known_species)
        scoped = str(ent.get("coordinate") or "") in _REAGENT_SCOPED_Q
        if sp and scoped:
            # Not a condition. The curve does not change the process chemistry -- the
            # paper's precursor and co-reactant are the same for both curves. It says the
            # swept dose belongs to THIS reagent, so the species qualifies the sweep
            # rather than standing beside it as a second, contradictory chemistry claim.
            return [{"series_reagent": sp, "quantity": None, "role": None,
                     "provenance_type": "figure_local_direct",
                     "source": "between_curve_legend", "scope": "series",
                     "role_basis": "the reagent whose dose this curve varies",
                     "evidence": "this curve is labelled %r where the figure distinguishes "
                                 "its curves by %r, naming both sides of the cycle; the "
                                 "label says which reagent's %s is swept, not which "
                                 "chemical the film was grown with"
                                 % (_norm(str(v_raw)), q_raw, ent.get("coordinate"))}]
        if note:
            note("between_curve_reagent_unresolved", ent.get("entity_id"),
                 "curves are distinguished by %r, which names both sides of the cycle, but "
                 "%s; no chemistry condition is asserted"
                 % (q_raw, ("the swept quantity %r is not a dose of one reagent"
                            % ent.get("coordinate")) if sp else
                    "the label %r matches none of the paper's known reagents %s"
                    % (_norm(str(v_raw)), sorted(known_species or []))))
        return []

    quantity = None
    for rx, qq, _role in _DECL_QUANTITY:
        if rx.search(str(q_raw)):
            quantity = qq
            break

    structural, why_struct = R.is_structure_quantity(q_raw)
    if not structural and quantity in D._PROGRESSION_Q:
        # A window or stage of one growth, not a separately prepared specimen. This is a
        # POSITIVE statement about identity: curves that differ only in how far the same
        # growth had advanced show one deposition observed more than once.
        if note:
            note("between_curve_progression", ent.get("entity_id"),
                 "curves differ in %r, which advances within one growth; they are stages "
                 "of one deposition, not separately prepared specimens" % q_raw)
        return [{"quantity": quantity, "value": _norm(str(v_raw)), "unit": None,
                 "role": R.DERIVED, "progression_stage": True,
                 "role_basis": "a stage of one growth, not a deposition setting",
                 "provenance_type": "figure_local_direct",
                 "source": "between_curve_legend", "scope": "series",
                 "evidence": "this curve is labelled %r where the figure distinguishes "
                             "its curves by %r, which advances within one growth"
                             % (_norm(str(v_raw)), q_raw)}]

    vals = legend_values(str(v_raw))
    num = vals[0] if len(vals) == 1 else None

    if structural:
        # A THICKNESS must carry a length unit. Without one the number is not a
        # measurement: the digits in a chemical formula would otherwise be read as a
        # thickness, turning a structure name into a spurious quantity.
        if num and not _LENGTH_UNIT.match(str(num.get("unit") or "")):
            num = None
        layers = R.parse_layer_stack(v_raw, materials)
        rec = {"quantity": "deposited_layer_thickness" if num else "deposited_structure",
               "value": num["value"] if num else _norm(str(v_raw)),
               "unit": (num or {}).get("unit"),
               "role": R.CASE_DEFINING,
               "role_basis": why_struct,
               "structural_identity": True,
               "provenance_type": "figure_local_direct",
               "source": "between_curve_legend", "scope": "series",
               "evidence": "this curve is labelled %r where the figure distinguishes its "
                           "curves by %r" % (_norm(str(v_raw)), q_raw)}
        if layers:
            rec["layer_stack"] = layers
            rec["n_layers"] = len(layers)
            rec["stack_materials"] = [x["material"] for x in layers]
            # a thickness qualified by ONE material belongs to that material's layer
            if num and len(layers) == 1:
                rec["species"] = layers[0]["material"]
        if not layers and num:
            m = R.species_named_in(q_raw, materials)
            if m:
                rec["species"] = m
        return [rec]

    if not quantity:
        return []
    if quantity in ("precursor", "coreactant"):
        # the value is the name of a chemical, so it is kept verbatim; a digit inside a
        # formula is part of the name and never a measurement
        return [{"quantity": quantity, "value": _norm(str(v_raw)), "unit": None,
                 "role": R.CASE_DEFINING,
                 "role_basis": "the process chemistry this curve was grown with",
                 "provenance_type": "figure_local_direct",
                 "source": "between_curve_legend", "scope": "series",
                 "evidence": "this curve is labelled %r where the figure distinguishes "
                             "its curves by %r" % (_norm(str(v_raw)), q_raw)}]
    role, basis = R.condition_role(quantity, None, None, None)
    if role not in (R.CASE_DEFINING, R.MEASUREMENT_SETTING):
        if note:
            note("between_curve_unresolved", ent.get("entity_id"),
                 "curves differ in %r, for which the ontology gives no role; no condition "
                 "is asserted" % q_raw)
        return []
    return [{"quantity": quantity,
             "value": num["value"] if num else _norm(str(v_raw)),
             "unit": (num or {}).get("unit"),
             "role": role, "role_basis": basis,
             "provenance_type": "figure_local_direct",
             "source": "between_curve_legend", "scope": "series",
             "evidence": "this curve is labelled %r where the figure distinguishes its "
                         "curves by %r" % (_norm(str(v_raw)), q_raw)}]


def progression_stage_links(candidates, note):
    """Link curves that differ ONLY in how far the same growth had advanced.

    The mirror of a design-branch link. A design branch says "these are different
    depositions measured the same way"; a progression stage says "this is one deposition
    measured at different points in its growth". Both are positive source statements about
    identity, and reading the second as the first turns one experiment into several.

    The link is only made within one panel and only when the candidates agree on every
    case-defining condition they do carry, so a figure that varies a real setting AND
    shows stages is not collapsed.
    """
    links = []
    by_panel = defaultdict(list)
    for c in candidates:
        if c.get("progression_stage") is None:
            continue
        by_panel[(c["source_figure"], c["source_panel"],
                  c.get("progression_quantity"))].append(c)
    for (fig, panel, q), group in sorted(by_panel.items(), key=lambda kv: str(kv[0])):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if PC.compatibility(PC._cond_key(a["case_conditions"]),
                                    PC._cond_key(b["case_conditions"]))[0] == "CONTRADICTS":
                    continue
                # POSITIVE continuity evidence is required on both sides. Sharing a panel
                # and a progression variable says only that the author drew them together;
                # without a statement that one growth produced them, independent specimens
                # would merge on the absence of a contradiction, which is exactly the
                # inference the identity rule forbids.
                # Strongest evidence first: the source naming the SAME specimen, or the
                # same deposition run, is a statement of physical identity. Failing that,
                # this figure's own scope must state that one growth was followed.
                shared_codes = (set(a.get("sample_codes") or [])
                                & set(b.get("sample_codes") or []))
                shared_runs = (set(a.get("run_ids") or []) & set(b.get("run_ids") or []))
                if shared_codes or shared_runs:
                    strength, ident = PC.EXPLICIT, (
                        "the source measures both on the same %s"
                        % ("specimen %s" % ", ".join(sorted(shared_codes)) if shared_codes
                           else "deposition run %s" % ", ".join(sorted(shared_runs))))
                elif {a.get("progression_continuity"),
                      b.get("progression_continuity")} == {"CONTINUOUS"}:
                    strength, ident = PC.SUPPORTED, (a.get("progression_continuity_reason")
                                                     or "")
                else:
                    note("progression_stage_unresolved",
                         "%s <-> %s" % (a["candidate_id"], b["candidate_id"]),
                         "curves labelled %r and %r differ only in %s, and neither a "
                         "shared specimen, a shared deposition run, nor a statement in "
                         "this figure's own scope establishes that one growth produced "
                         "them: %s. Their identities are left UNRESOLVED rather than "
                         "merged."
                         % (a["progression_stage"], b["progression_stage"], q,
                            a.get("progression_continuity_reason")
                            or b.get("progression_continuity_reason")))
                    continue
                links.append({
                    "a": a["candidate_id"], "b": b["candidate_id"],
                    "strength": strength, "link_class": "PROGRESSION_STAGE_LINK",
                    "reason": "panel %s of figure %s shows the same growth at %s = %s and "
                              "%s; a progression is not a second deposition"
                              % (panel, fig, q, a["progression_stage"],
                                 b["progression_stage"]),
                    "evidence": note("progression_stage_link",
                                     "%s <-> %s" % (a["candidate_id"], b["candidate_id"]),
                                     "curves labelled %r and %r differ only in how far the "
                                     "same growth had advanced; %s"
                                     % (a["progression_stage"], b["progression_stage"],
                                        a.get("progression_continuity_reason")))})
    return links


def panel_letter(x):
    """The leading letter of a panel label. The canonical layer keeps the printed label
    ("a (With bottom)") while the resolver normalises it to "a"."""
    m = re.match(r"\s*\(?\s*([A-Za-z])\b", str(x or ""))
    return m.group(1).lower() if m else ""


def series_label(x):
    """A series label, or "" when the source drew no distinguishing legend."""
    t = _norm(x)
    return "" if t in ("<single>", "primary", "None") else t


def link_is_supported(curve_source, entity, labels_in_scope):
    """(ok, reason) -- may a curve be attributed to the semantic entity its link names?

    An explicit `linked_experiment_id` is CANDIDATE EVIDENCE about which semantic object
    produced a curve, not a fact that outranks the curve's own provenance. Two things go
    wrong with it, and both are visible by comparing the two source scopes:

      A. it names an entity in a different figure or panel than the curve itself reports.
         That is a positive contradiction between two locally attributable provenances,
         so the link cannot be used here.
      B. it collapses onto a sibling carrying a DIFFERENT series label while the curve's
         own label matches another entity in the same panel. Case-suffixed ids
         (`…exp01__case00`, `…exp01__case01`) share a base, so stripping the suffix puts
         every curve of the panel on one entity and silently discards the distinction the
         source drew. The curve's own label recovers it.

    Absence of information is never a contradiction: a missing figure, panel or label on
    either side leaves the link acceptable, because nothing positively opposes it. Equality
    of conditions is never consulted -- this decides which object PRODUCED a curve, not
    which experiments are the same.

    A rejected link is not an attribution: the curve is left for the source-slice matching
    that follows, and stays unresolved if that cannot place it either.
    """
    if entity is None:
        return True, ""                        # nothing to compare against
    src = curve_source or {}
    for got, want, what in (
            (str(src.get("figure") or ""),
             str(entity.get("printed_figure_number") or ""), "figure"),
            (str(src.get("figure_index") or ""),
             str(entity.get("fig_docling_index") or ""), "figure index"),
            (panel_letter(src.get("panel")),
             panel_letter(entity.get("panel") or entity.get("panel_key")), "panel")):
        if got and want and got != want:
            return False, ("the curve reports %s %s while the linked entity belongs to "
                           "%s %s" % (what, got, what, want))
    c_lab = series_label(src.get("series"))
    e_lab = series_label(entity.get("source_series"))
    if c_lab and e_lab and c_lab != e_lab:
        scope = (str(src.get("figure_index")), panel_letter(src.get("panel")))
        if c_lab in (labels_in_scope or {}).get(scope, set()):
            return False, ("the curve is labelled %r but the linked entity is %r, and "
                           "another entity in the same panel carries %r"
                           % (c_lab, e_lab, c_lab))
    return True, ""


#: A clause splits into segments at the connectives that separate one statement about one
#: curve from the next. "GPC on temperature and the critical angle obtained from XRR"
#: is two statements, and only the second is about the critical angle.
_SEGMENT = re.compile(r"\s*(?:;|,| and | but | while | whereas |\. )\s*", re.I)
#: an explicit statement that one method covers everything the scope shows
_SHARED_TECHNIQUE = re.compile(
    r"\b(?:both|all|each|every|either)\b[^.]{0,60}\b(?:were|was|are|is)\b|"
    r"\ball\s+(?:profiles|curves|samples|films|spectra|measurements)\b", re.I)


#: Words that name the SCAFFOLDING of a figure rather than one curve in it. They appear
#: in every segment of a caption, so they identify nothing.
_GENERIC_LABEL_WORDS = {"the", "and", "for", "with", "from", "series", "sample", "samples",
                        "curve", "curves", "panel", "profile", "profiles", "data",
                        "measurement", "measurements", "plot", "line", "lines"}


def _identifiers(series_label, measurand):
    """((long, short)) -- the tokens that identify ONE curve inside a shared clause.

    Long tokens carry meaning and are matched case-insensitively. Short ones are usually
    bare label letters ("A", "B"), which match only case-sensitively: lower-case "a" is
    the English article and would attach a technique to whichever segment happened to
    contain it.
    """
    long_, short = set(), set()
    for src in (series_label, measurand):
        for w in re.findall(r"[A-Za-z0-9\u0370-\u03ff]+", str(src or "")):
            if w.lower() in _GENERIC_LABEL_WORDS:
                continue
            (long_ if len(w) >= 3 else short).add(w.lower() if len(w) >= 3 else w)
    return long_, short


def techniques_for_series(clause, series_label, measurand, n_series_in_scope):
    """(techniques, basis, evidence) for ONE Measurement, from shared scope text.

    A caption clause describes a whole panel. Handing every technique it mentions to
    every curve in that panel is how one curve acquires its sibling's instrument. So a
    technique is attributed to THIS curve only when the evidence ties it to this curve:

      * the clause names one technique and the scope holds one curve -- nothing else it
        could belong to;
      * the source says the method covers all of them ("both profiles were measured
        by X");
      * or the technique sits in the same segment of the sentence as a word that
        identifies this curve -- its own legend, or its own measured quantity.

    Anything else is left unattributed. A curve whose instrument the source does not
    make attributable keeps no technique at all, which is the honest answer and is
    preferable to inheriting a sibling's.
    """
    hits = PE.techniques(clause or "")
    if not hits:
        return [], None, []
    if n_series_in_scope <= 1:
        return ([h["technique"] for h in hits], "source_reported_panel", hits[:3])
    if _SHARED_TECHNIQUE.search(clause or ""):
        return ([h["technique"] for h in hits], "source_reported_panel_shared", hits[:3])
    ident_long, ident_short = _identifiers(series_label, measurand)
    if not (ident_long or ident_short):
        return [], None, []
    segs, pos = [], 0
    for m in _SEGMENT.finditer(clause or ""):
        segs.append((pos, m.start()))
        pos = m.end()
    segs.append((pos, len(clause or "")))
    keep, ev = [], []
    for h in hits:
        seg = next((clause[a:b] for a, b in segs if a <= h["offset"] < b), "")
        toks = re.findall(r"[A-Za-z0-9\u0370-\u03ff]+", seg)
        long_hit = ident_long & {w.lower() for w in toks if len(w) >= 3}
        short_hit = ident_short & {w for w in toks if len(w) < 3}
        if long_hit or short_hit:
            keep.append(h["technique"])
            ev.append(h)
    if keep:
        return keep, "source_reported_series", ev[:3]
    return [], None, []


def _infer_basis(ent, measurand):
    """Which side of the record an inferred technique came from."""
    q = str(measurand if measurand is not None else ent.get("measurand") or "").lower()
    return "inferred_from_measurand" if q in _AXIS_TECH else "inferred_from_coordinate"


def _inference_note(ent, measurand):
    """Evidence for an INFERRED technique. It must not look like a source match: the
    paper never said this, the resolver concluded it from the quantity."""
    q = str(measurand if measurand is not None else ent.get("measurand") or "").lower()
    if q in _AXIS_TECH:
        return [{"technique": _AXIS_TECH[q], "inferred": True,
                 "matched": None,
                 "basis": "the measured quantity %r is characteristically produced by "
                          "this technique; the source does not state it" % q}]
    c = str(ent.get("coordinate") or "").lower()
    if c in _COORD_TECH:
        return [{"technique": _COORD_TECH[c], "inferred": True,
                 "matched": None,
                 "basis": "the plotted coordinate %r is characteristic of this "
                          "technique; the source does not state it" % c}]
    return []


#: Entity classes that cannot be an observation of a locally deposited product: model
#: output, a fit, a redrawn view, and data imported from another work.
#:
#: NON_EXPERIMENTAL is used earlier to prevent CASE MINTING from entity classification
#: alone. An UnresolvedSourceEntity cannot mint a case, but it may still be LINKED to an
#: existing case when independent, positive produced-material evidence establishes that
#: relationship -- an unresolved entity KIND and an unresolved product provenance are
#: different uncertainties. So the provenance set is narrower than the minting set.
_NOT_A_LOCAL_PRODUCT = NON_EXPERIMENTAL - {"UnresolvedSourceEntity"}


def provenance_eligible(m):
    """Whether a Measurement should be resolved against the paper's produced-material
    chains.

    The question this gate answers is "could one of this paper's ExperimentalCases have
    produced the thing that was measured?" -- which has nothing to do with whether the
    paper named the instrument. Eligibility used to require a non-empty `technique`, so
    correcting the technique field silently removed 31 Measurements from provenance
    resolution and added 4, with no change to their identity, quantity, source or case
    candidates. Instrument knowledge is not provenance evidence.

    Only categories the resolver has ALREADY classified as not-a-local-product are
    excluded, each on its own recorded evidence:

      * `measures_case`  -- provenance is already established; do not re-resolve it.
      * IMPORTED_LITERATURE -- the caption attributes the observation to another work.
      * `reports_species_property` -- a property of a chemical, not of a deposited film;
        no local material role was asserted for it and none may be acquired here.
      * `represents_same_measurement_as` -- a redrawn view of a Measurement represented
        elsewhere; attaching provenance again would duplicate the relation.
      * an entity class in NON_EXPERIMENTAL -- model output, fits and imported
        observations never carry a current-paper deposition product.
    """
    if m.get("measures_case"):
        return False
    if m.get("provenance_role") == "IMPORTED_LITERATURE":
        return False
    if m.get("reports_species_property"):
        return False
    if m.get("represents_same_measurement_as"):
        return False
    if m.get("entity_class") in _NOT_A_LOCAL_PRODUCT:
        return False
    return True
