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
import pilot_supplements as SUP                                 # noqa: E402

W = Path(__file__).resolve().parent.parent

#: resolver entity classes that are model output, not measurement. Preserved verbatim.
SIMULATION_CLASSES = {"SimulationRun", "ModelSweep"}
#: classes that never carry a current-paper deposition case (preservation target)
NON_EXPERIMENTAL = SIMULATION_CLASSES | {"ImportedLiteratureObservation", "Fit",
                                         "DerivedRepresentation", "UnresolvedSourceEntity"}


def _clean(t):
    t = (t or "").replace("/uniFB01", "fi").replace("/uniFB02", "fl").replace("/uniFB00", "ff")
    t = t.replace("/C14", "°").replace("/C0", "-").replace("/C29", ")")
    return re.sub(r"/uni[0-9A-F]{4}", "", t)


def _norm(t):
    return re.sub(r"\s+", " ", _clean(t)).strip()


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
                           "study_series", "simulation_runs", "links", "evidence",
                           "unresolved")}
    ev = out["evidence"]
    sample_by_code = {}

    def note(kind, subject, detail, **kw):
        rec = {"evidence_id": "EV-%s-%03d" % (pid[:6].upper(), len(ev) + 1),
               "kind": kind, "subject": subject, "detail": detail}
        rec.update(kw)
        ev.append(rec)
        return rec["evidence_id"]

    # ---------------------------------------------------------------- 1. paper scope
    paper_chem = {"precursor": P.scout.get("precursors") or [],
                  "coreactant": P.scout.get("coreactants") or []}
    paper_mat_roles = R.material_roles(P.methods + "\n" + P.md[:20000], P.materials)
    for mat, recs in sorted(paper_mat_roles.items()):
        note("material_role", mat,
             "roles read from the methods/body: %s" % sorted({r["role"] for r in recs}),
             roles=recs[:6])

    # ------------------------------------------ 2. specimens from the paper's own table
    # A per-specimen parameter table is authoritative for specimen identity, for study
    # series membership, and for which variable each series varies. When the paper has no
    # such table this whole block simply produces nothing.
    table_cols = PT.column_map(P.sample_table_header, 24)
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
                          "provenance_type": "directly_stated", "source": "sample_table",
                          "evidence": "specimen table row for specimen %r, column %r"
                                      % (code, q)})
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
    for sent in re.split(r"(?<=[.;])\s+", _norm(P.md)):
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
    # Curve -> entity. The explicit link is preferred; where a curve carries none (it is
    # populated for 40 of 70 curves in one pilot paper and 0 of 4 in another) the SOURCE
    # SLICE is the join, because both sides name the same figure_data.json coordinates.
    # No curve is ever attached by guessing.
    curve_by_entity = defaultdict(list)
    slice_index = {}
    for c in P.curves:
        src = c.get("source") or {}
        slice_index[(str(src.get("figure_index")), str(src.get("panel") or "").lower(),
                     _norm(src.get("series")))] = c
    joined = set()
    for c in P.curves:
        for eid in ((c.get("source") or {}).get("linked_experiment_ids") or []):
            base = str(eid).split("__case")[0]
            curve_by_entity[base].append(c)
            joined.add(c["curve_id"])
    for ent in P.entities:
        if curve_by_entity.get(ent["entity_id"]):
            continue
        lab = _norm(ent.get("source_series"))
        lab = "" if lab in ("<single>", "primary", "None") else lab
        key = (str(ent.get("fig_docling_index")), (ent.get("panel") or "").lower(), lab)
        c = slice_index.get(key)
        if c is not None and c["curve_id"] not in joined:
            curve_by_entity[ent["entity_id"]].append(c)
            joined.add(c["curve_id"])
    out["_unjoined_curves"] = [c["curve_id"] for c in P.curves if c["curve_id"] not in joined]

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
        axis_tech = _tech_from_axes(ent)
        cap_tech = PE.techniques(clause) or PE.techniques(preamble) or PE.techniques(body)
        mid = "M::%s" % eid
        cd, ms, other = PC.entity_conditions(ent)
        # every material of the paper that THIS scope names, with the role it names it in
        scope_text = " ".join([clause, preamble])
        scope_mat = R.material_roles(scope_text, P.materials)
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
            "measured_quantity": ent.get("measurand"),
            "measured_unit": ent.get("measurand_unit"),
            "coordinate": ent.get("coordinate"), "coordinate_unit": ent.get("coordinate_unit"),
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
        legend_codes = PE.sample_codes(ent.get("source_series") or "")
        codes = legend_codes or PE.sample_codes(clause) or PE.sample_codes(preamble)
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
        sweep, x_role, x_basis, sweep_note = PC.sweep_cases(ent)
        if sweep:
            for k, sc in enumerate(sweep):
                candidates.append(_cand(pid, eid, printed, panel, cd + [sc], mid,
                                        rs_ids, ent, "sweep_point",
                                        note("sweep_normalisation", eid, sc["evidence"],
                                             quantity=sc["quantity"], value=sc["value"],
                                             unit=sc["unit"], role_basis=x_basis),
                                        _scope_ctx))
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

    # ------------------------------------------------ 4. text-supported deposition cases
    for tc in text_cases(P):
        candidates.append(_cand(pid, None, tc["printed_figure"], "", tc["conditions"],
                                None, [], None, "text_supported",
                                note("text_supported_case", tc["label"], tc["evidence"],
                                     sentence=tc["sentence"])))
        candidates[-1]["label"] = tc["label"]
        candidates[-1]["deposited_material"] = tc["material"]

    # ---------------------------------------------------------- 5. linkage between candidates
    codes_of_meas = defaultdict(set)
    for sm in out["samples"]:
        for m in sm["measurement_ids"]:
            codes_of_meas[m].add(sm["source_sample_code"])
    for c in candidates:
        c["sample_codes"] = sorted(codes_of_meas.get(c.get("measurement_id")) or [])
        if len(c["sample_codes"]) == 1:
            sm = sample_by_code.get(c["sample_codes"][0]) or {}
            for tc in sm.get("case_defining_conditions") or []:
                if not any(x["quantity"] == tc["quantity"] for x in c["case_conditions"]):
                    rec = dict(tc)
                    rec["provenance_type"] = "inherited_from_explicit_sample"
                    rec["evidence"] = ("specimen %r is named for this result; its row of "
                                       "the paper's specimen table gives %s = %s"
                                       % (c["sample_codes"][0], tc["quantity"], tc["value"]))
                    c["case_conditions"].append(rec)
    cand_links = discover_links(P, candidates, sample_by_code, out, note,
                                series_members, table_cols)

    # ---------------------------------------------------------- 6. resolve identities
    groups, decisions = PC.resolve_cases(candidates, cand_links)
    out["links"] = [dict(d) for d in decisions]
    by_id = {c["candidate_id"]: c for c in candidates}

    for i, g in enumerate(sorted(groups, key=lambda x: x[0]), 1):
        members = [by_id[c] for c in g]
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

    # ---------------------------------------------------------- 7. study series
    for letter in sorted(series_members) or sorted(series_ev):
        codes = sorted(series_members.get(letter, []))
        sids = [sample_by_code[c]["sample_id"] for c in codes if c in sample_by_code]
        varied, vrole, vev = table_series_variable(P, table_cols, codes)
        ambiguous_var = None
        if not varied:
            ambiguous_var = vev          # "N varying columns" — a real ambiguity, kept
            varied, vrole, vev = series_variable(P, letter)
            if varied and ambiguous_var:
                vrole = R.UNRESOLVED_ROLE
                vev = "%s; prose names %r but the table does not single it out" % (
                    ambiguous_var, varied)
        out["study_series"].append({
            "series_id": "SER::%s::%s" % (pid, letter), "paper_id": pid,
            "author_series_name": "Series %s" % letter,
            "member_sample_codes": codes, "member_sample_ids": sids,
            "member_case_ids": sorted({c for s in sids
                                       for c in _sample_cases(out, s)}),
            "varied_variable": varied, "varied_variable_role": vrole,
            "purpose": vev, "evidence": note("study_series", "Series %s" % letter,
                                             (series_ev.get(letter) or {}).get("span", ""),
                                             members=codes),
        })

    # ---------------------------------------------------------- 8. deposition runs
    # After the series, because a run statement identifies its specimens through the
    # series it names ("grown in the same ALD run … (Series A in Table 1)").
    out["deposition_runs"] = deposition_runs(P, out, sample_by_code, note)
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

    # ---------------------------------------------------------- 9. unresolved links
    out["unresolved"] = PC.unresolved_pairs(candidates, groups)
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
            "reason": ("no deposition case is established for this result: "
                       + ("the extraction stage holds no data for this panel"
                          if m.get("data_recovered") is False else
                          "the source does not state which deposition produced the "
                          "specimen it was measured on")),
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


def _tech_from_axes(ent):
    q = str(ent.get("measurand") or "").lower()
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
            if k not in conds or c.get("provenance_type") == "directly_stated":
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
    sids = sorted({s["sample_id"] for s in sample_by_code.values()
                   if any(mm in s["measurement_ids"] for mm in mids)})
    strengths = [e for m in members for e in m["evidence"]]
    conf = (PC.EXPLICIT if len(members) > 1 and any(m["kind"] == "text_supported" for m in members)
            else PC.SUPPORTED if len(members) > 1 else PC.EXPLICIT)
    roles = {}
    for mat in context_mats:
        roles[mat] = (R.primary_role(scope_named.get(mat) or [])
                      or R.primary_role(paper_mat_roles.get(mat) or [])
                      or R.DEPOSITED)
    warn = []
    if not mats:
        warn.append("deposited material UNRESOLVED at the source scope of every member")
    if len(mats) > 1:
        warn.append("several deposited materials linked into one case: %s" % mats)
    if len(geos) > 1:
        warn.append("several geometries: %s" % geos)
    if not conds:
        warn.append("no case-defining condition value is known for this case")
    label = next((m.get("label") for m in members if m.get("label")), None)
    return {
        "case_id": "CASE-%s-%03d" % (pid[:6].upper(), i),
        "paper_id": pid, "label": label,
        "deposited_material": mats[0] if len(mats) == 1 else None,
        "deposited_materials": mats,
        "context_materials": context_mats, "material_roles": roles,
        "multi_material_context": len(context_mats) > 1,
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
        by_fig[printed][_norm(ent.get("source_series"))].append(ent)

    holder_of, groups = {}, []
    for printed, by_label in sorted(by_fig.items()):
        for label, ents in sorted(by_label.items()):
            if len(ents) < 2 or not label:
                continue
            kinds = {reps[e["entity_id"]] for e in ents}
            if len(kinds) < 2:
                continue                     # same view repeated: not a representation set
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
    for sent in re.split(r"(?<=[.])\s+", _norm(P.methods)):
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
            variants.append({"quantity": quantity, "value": val, "sentence": _norm(sent)[:300],
                             "matched": _norm(m.group(0))})
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
        out.append({"label": "%s per cycle = %d" % (v["quantity"], v["value"]),
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
    for sent in re.split(r"(?<=[.])\s+", _norm(P.md)):
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


def series_variable(P, letter):
    """What a named Series varies, and the role of that variable."""
    for m in re.finditer(r"[^.]*\bSeries\s+%s\b[^.]*\." % re.escape(letter), P.md, re.I):
        sent = _norm(m.group(0))
        for rx, q, role in _SERIES_VAR:
            if rx.search(sent):
                return q, role, sent[:260]
    return None, R.UNRESOLVED_ROLE, None
