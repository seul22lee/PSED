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
def build(pid):
    P = Paper(pid)
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
                "data_source": src.get("data_source"),
                "x_quantity": ((c.get("semantics") or {}).get("x") or {}).get("canonical_quantity")
                              or (c.get("raw") or {}).get("x", {}).get("quantity"),
                "y_quantity": ((c.get("semantics") or {}).get("y") or {}).get("canonical_quantity")
                              or (c.get("raw") or {}).get("y", {}).get("quantity"),
                "n_points": len(((c.get("raw") or {}).get("points") or [])),
                "n_transformations": len(c.get("transformations") or []),
                "join_method": join_method.get(c["curve_id"]),
                "produced_by": None, "resolved_entity_id": eid,
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
        axis_tech = _tech_from_axes(ent, meas_q)
        cap_tech = PE.techniques(clause) or PE.techniques(preamble) or PE.techniques(body)
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
        for bc in between_curve_conditions(ent, P.materials, note):
            if bc.get("progression_stage"):
                _prog_stage = bc
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
        meas = {
            "measurement_id": mid, "paper_id": pid,
            "technique": axis_tech or [t["technique"] for t in cap_tech],
            "technique_basis": ("measured quantity" if axis_tech
                                else "caption clause" if cap_tech else "unresolved"),
            "technique_evidence": cap_tech[:3],
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
                      "scope_geometry_match": geo_match}
        # the material this SCOPE names, not the paper-wide value: the two halves of a
        # saturation figure deposit different materials and must not share a design
        _scope_dep = sorted({m for m, recs in (scope_mat or {}).items()
                             if R.primary_role(recs) == R.DEPOSITED})
        sweep, x_role, x_basis, sweep_note, design = PC.sweep_cases(
            ent, scope_text, P.methods,
            material=(_scope_dep[0] if len(_scope_dep) == 1 else ent.get("material")))
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
            "technique": sp["techniques"], "technique_basis": "caption clause",
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
                                    "tabulated_specimen", tbl_ev))
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
                             PC._fmt(x.get("value")))
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
        if m["measures_case"] or not m.get("technique"):
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


#: measurand/coordinate -> the technique that produces it. The measured quantity is a
#: far more reliable technique signal than a caption clause, which a panel range marker
#: can spread across panels that measure different things.
_AXIS_TECH = {"growth_per_cycle": "growth_per_cycle", "gpc": "growth_per_cycle",
              "thickness": "thickness", "film_thickness": "thickness",
              "resistivity": "resistivity", "sheet_resistance": "resistivity",
              "current_density": "cyclic_voltammetry", "impedance": "impedance_spectroscopy",
              "|z|": "impedance_spectroscopy", "capacitance": "capacitance",
              "refractive_index": "ellipsometry", "roughness": "AFM"}
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


def _cand(pid, eid, printed, panel, conds, mid, rs_ids, ent, kind, ev, scope=None):
    scope = scope or {}
    return {"candidate_id": "C%04d::%s" % (len(_cand.counter), pid) if False else
            "CAND-%s-%03d" % (pid[:6].upper(), next(_counter)),
            "paper_id": pid, "resolved_entity_id": eid, "source_figure": printed,
            "source_panel": panel, "case_conditions": [c for c in conds
                                                       if c.get("role") == R.CASE_DEFINING],
            "other_conditions": [c for c in conds if c.get("role") != R.CASE_DEFINING],
            "measurement_id": mid, "result_series_ids": rs_ids, "kind": kind,
            "deposited_material": (ent or {}).get("material"),
            "geometry": scope.get("scope_geometry") or (ent or {}).get("geometry_class"),
            "geometry_source": ("figure/panel caption" if scope.get("scope_geometry")
                                else "paper-level default"),
            "geometry_evidence": scope.get("scope_geometry_match"),
            "scope_materials": scope.get("scope_materials") or {},
            "precursors": (ent or {}).get("precursors") or [],
            "coreactants": (ent or {}).get("coreactants") or [],
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


def _case(pid, i, members, P, paper_mat_roles, meas_by_entity, sample_by_code, note):
    """One ExperimentalCase from its merged candidates."""
    conds = {}
    for m in members:
        for c in m["case_conditions"]:
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
    deposited = sorted(m for m, r in roles.items() if r == R.DEPOSITED)
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
    if len(deposited) > 1:
        warn.append("several deposited materials linked into one case: %s" % deposited)
    if len(geos) > 1:
        warn.append("several geometries: %s" % geos)
    if not conds:
        warn.append("no case-defining condition value is known for this case")
    label = next((m.get("label") for m in members if m.get("label")), None)
    synth = next((m.get("synthesis_label") for m in members if m.get("synthesis_label")), None)
    return {
        "case_id": "CASE-%s-%03d" % (pid[:6].upper(), i),
        "paper_id": pid, "label": label, "synthesis_label": synth,
        "deposited_material": deposited[0] if len(deposited) == 1 else None,
        "deposited_materials": deposited,
        "context_materials": asserted, "material_roles": roles,
        "material_candidates": candidates_mat,
        "material_status": material_status,
        "material_status_reason": material_status_reason,
        "material_evidence_scope": ("figure/panel scope" if scope_named else
                                    "resolver per-record decision" if mats else
                                    "paper_candidate_only" if candidates_mat else None),
        "multi_material_context": len(asserted) > 1,
        "process_type": next((m["process_type"] for m in members if m.get("process_type")), None),
        "precursors": sorted({p for m in members for p in (m.get("precursors") or [])}),
        "coreactants": sorted({p for m in members for p in (m.get("coreactants") or [])}),
        "case_defining_conditions": [conds[k] for k in sorted(conds)],
        "geometry": geos[0] if len(geos) == 1 else None,
        "geometries": geos,
        "geometry_source": next((m.get("geometry_source") for m in members
                                 if m.get("geometry_source") == "figure/panel caption"),
                                "paper-level default"),
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
    }


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
    for (printed, panel), group in by_scope.items():
        if not printed:
            continue
        text = " ".join([P.printed_caption(printed), P.body_near(printed)])
        sames = [e for e in PE.linkage_evidence(text) if e["kind"] == "explicit_same"]
        if not sames:
            continue
        for e in sames:
            cited = set(re.findall(r"\bFig(?:ure)?\.?\s*(\d+)", e["span"], re.I)) - {printed}
            for cf in cited:
                for a in group:
                    for b in [c for c in candidates if c["source_figure"] == cf]:
                        links.append({"a": a["candidate_id"], "b": b["candidate_id"],
                                      "strength": PC.EXPLICIT,
                                      "reason": "explicit %r citing figure %s" % (e["label"], cf),
                                      "evidence": note("explicit_same_statement",
                                                       "fig %s -> fig %s" % (printed, cf),
                                                       e["span"], matched=e["matched"])})

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
                    # a different SCOPE, not merely a different figure: 2a, 2b and 2c are
                    # three panels of one printed figure and are exactly the cross-result
                    # link this rule exists to find
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


#: "grown at the temperatures of 100 and 300 C" / "at 100, 200 and 300 C"
_ENUM = re.compile(
    r"\b(?:at|of|to|using|with)\s+(?:the\s+)?(?:temperatures?|pulse times?|purge times?|"
    r"cycles?|exposure times?)?\s*(?:of\s+)?"
    r"((?:\d+(?:\.\d+)?)(?:\s*(?:,|and)\s*\d+(?:\.\d+)?)+)\s*"
    r"(°?\s?C|s\b|cycles?\b|nm\b|Torr\b|Pa\b|mbar\b)", re.I)
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
    """(quantity, [values], span) for each explicit enumeration of settings in a caption."""
    out = []
    for m in _ENUM.finditer(text or ""):
        vals = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group(1))]
        unit = (m.group(2) or "").strip()
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
    (re.compile(r"\bco-?reactant\b|\boxidant\b", re.I), "coreactant", R.CASE_DEFINING),
    (re.compile(r"\bprecursor\b|\breactant\b|\bchemistry\b", re.I), "precursor",
     R.CASE_DEFINING),
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
        "technique": ic["techniques"], "technique_basis": "caption clause",
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


def between_curve_conditions(ent, materials, note=None):
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
