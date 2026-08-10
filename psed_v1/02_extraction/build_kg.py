"""
build_kg.py  (Phase E — KG viewer, v2 role-aware)
-------------------------------------------------
Render the ontology-grounded knowledge graph as a standalone, interactive
node-link view: kg_viewer.html — built from the resolved experiments so it
carries the full role model.

Meaningful structure:
  · every Experiment links to its PAPER node (from_paper) and its MATERIAL.
  · quantity nodes are DIFFERENTIATED by role — Independent (x / varies),
    Dependent (y / property of interest), Condition (held fixed) — coloured by
    the quantity's dominant role across the corpus.
  · edges are typed by the ACTUAL per-experiment role: varies · measures · controls.

QuantityValues are aggregated into experiment→quantity edges so the backbone
stays legible. Self-contained (CSP-safe, theme-aware). Tracked in the repo.
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).parent
ONTO = json.loads((ROOT.parent / "01_ontology" / "ald_ontology.json").read_text())
# species -> intrinsic properties (molar_mass, molecular_diameter, central_atoms)
SPECIES_PROPS = {}
for _g in ("precursors", "coreactants"):
    for _it in ONTO["individuals"].get(_g, []):
        _p = {k: _it[k] for k in ("molar_mass", "molecular_diameter", "central_atoms") if k in _it}
        for _k in (_it["id"], _it.get("formula"), _it.get("full_name")):
            if _k:
                SPECIES_PROPS[str(_k)] = _p


def _load_canonical():
    """Canonical curves produced by 02_extraction/canonical/build_canonical.py."""
    out = []
    for d in sorted((ROOT / "output").glob("*/canonical/curves.json")):
        try:
            out.extend(json.loads(d.read_text()).get("curves", []))
        except Exception:
            pass
    return out

def _emit_tbox(node, link, present_q, rules, groups, ndefs,
               used_rules, used_groups, used_ndefs):
    """TBox nodes for the rules / groups / normalization definitions actually used.

    Emitted in dependency order — normalization definitions before the comparison
    groups that reference them — because link() drops any edge whose endpoint does
    not exist yet."""
    for nd in sorted(used_ndefs):
        spec = ndefs[nd]
        node("nd::" + nd, "NormalizationDefinition", nd,
             semantic_label=spec.get("semantic_label"),
             formula=spec.get("formula"),
             denominator_role=spec.get("normalization_denominator_role"),
             reference_location=spec.get("reference_location"))
        for slot, edge in (("numerator", "normalization_numerator"),
                           ("denominator", "normalization_denominator")):
            if spec.get(slot) in present_q:
                link("nd::" + nd, "q::" + spec[slot], edge)
    for g in sorted(used_groups):
        spec = groups[g]
        node("grp::" + g, "ComparisonGroup", g,
             canonical_quantity=spec.get("canonical_quantity"),
             canonical_unit=spec.get("canonical_unit"),
             dimension=spec.get("dimension"))
        if spec.get("canonical_quantity") in present_q:
            link("grp::" + g, "q::" + spec["canonical_quantity"], "group_canonical_kind")
        if spec.get("normalization_definition") in ndefs:
            link("grp::" + g, "nd::" + spec["normalization_definition"], "group_normalization")
    for rid in sorted(used_rules):
        r = rules[rid]
        node("rule::" + rid, "TransformationRule", rid, version=r.get("version"),
             ttype=r.get("type"), implementation=r.get("implementation_id"),
             output_unit=r.get("output_unit"), invertible=bool(r.get("invertible")),
             required_context=", ".join(r.get("required_context") or []),
             assumptions=" | ".join(r.get("assumptions") or []))
        for q in r.get("required_context") or []:
            if q in present_q:
                link("rule::" + rid, "q::" + q, "requires_context")
        for slot, edge in (("source_quantity_kind", "rule_source_kind"),
                           ("target_quantity_kind", "rule_target_kind")):
            if r.get(slot) in present_q:
                link("rule::" + rid, "q::" + r[slot], edge)
        if r.get("normalization_definition") in ndefs:
            link("rule::" + rid, "nd::" + r["normalization_definition"],
                 "has_normalization_definition")


def _add_comparability_layer(node, link, links, nodes, present_q):
    """Instantiate TransformationRule / TransformationExecution /
    NormalizationDefinition / ComparisonGroup and wire canonical values back to
    the raw evidence they came from. Unresolved transformations are represented
    too — they are the audit trail, not noise to be hidden."""
    qr = ONTO.get("quantity_relations", {}) or {}
    groups = qr.get("comparison_groups", {}) or {}
    ndefs = {n["id"]: n for n in qr.get("normalization_definitions", []) or []}
    rules = {r["id"]: r for r in qr.get("transformation_rules", []) or []}

    curves = _load_canonical()

    # PRE-SCAN: TBox nodes must exist before any edge points at them.
    used_rules, used_groups, used_ndefs = set(), set(), set()
    for c in curves:
        for axis in ("x", "y"):
            can = (c.get("canonical") or {}).get(axis)
            if can:
                if can.get("comparison_group") in groups:
                    used_groups.add(can["comparison_group"])
                if can.get("normalization_definition") in ndefs:
                    used_ndefs.add(can["normalization_definition"])
            for proj in ((c.get("projections") or {}).get(axis) or []):
                if proj.get("comparison_group") in groups:
                    used_groups.add(proj["comparison_group"])
        for t in c.get("transformations") or []:
            if t.get("rule_id") in rules:
                used_rules.add(t["rule_id"])
            if t.get("comparison_group") in groups:
                used_groups.add(t["comparison_group"])
            if t.get("normalization_definition") in ndefs:
                used_ndefs.add(t["normalization_definition"])
    for g in list(used_groups):
        if groups[g].get("normalization_definition") in ndefs:
            used_ndefs.add(groups[g]["normalization_definition"])
    for rid in list(used_rules):
        if rules[rid].get("normalization_definition") in ndefs:
            used_ndefs.add(rules[rid]["normalization_definition"])
    _emit_tbox(node, link, present_q, rules, groups, ndefs,
               used_rules, used_groups, used_ndefs)

    exp_by_label = {n.get("label"): nid for nid, n in nodes.items()
                    if n.get("type") == "Experiment"}

    for c in curves:
        src = c.get("source") or {}
        cid = "curve::" + c["curve_id"]
        node(cid, "Curve", c["curve_id"], paper=src.get("doi"),
             figure=src.get("figure"), panel=src.get("panel"),
             series=src.get("series"),
             points=len(c.get("raw", {}).get("points") or []))
        if src.get("doi"):
            node("p::" + src["doi"], "Paper", src["doi"])
            link(cid, "p::" + src["doi"], "from_paper")
        fid = "fig::%s::%s" % (src.get("doi"), src.get("figure"))
        node(fid, "Figure", "%s Fig %s" % (src.get("doi"), src.get("figure")),
             paper=src.get("doi"))
        link(cid, fid, "shown_in")
        for exp_id in src.get("linked_experiment_ids") or []:
            if exp_id in exp_by_label:
                link(exp_by_label[exp_id], cid, "shown_in")

        for axis in ("x", "y"):
            sem = (c.get("semantics") or {}).get(axis) or {}
            raw = (c.get("raw") or {}).get(axis) or {}
            rawid = "rawv::%s::%s" % (c["curve_id"], axis)
            node(rawid, "RawQuantityValue", "%s %s (raw)" % (axis, raw.get("quantity")),
                 quantity=raw.get("quantity"), unit=raw.get("unit"),
                 axis_label=raw.get("label"), axis=axis,
                 axis_role=sem.get("axis_role"), axis_kind=sem.get("axis_kind"),
                 semantics_status=sem.get("status"),
                 unresolved_reason=sem.get("unresolved_reason"),
                 evidence=("; ".join(str(e.get("span") or "")[:80]
                                     for e in (sem.get("evidence") or [])) or None),
                 source_file=src.get("source_file"),
                 json_pointer=src.get("json_pointer"),
                 checksum=src.get("source_checksum"))
            link(cid, rawid, "has_raw_value")
            if sem.get("quantity") in present_q:
                link(rawid, "q::" + sem["quantity"], "of_kind")

            can = (c.get("canonical") or {}).get(axis)
            if can:
                canid = "canv::%s::%s" % (c["curve_id"], axis)
                node(canid, "CanonicalQuantityValue",
                     "%s %s [%s]" % (axis, can.get("quantity"), can.get("unit")),
                     quantity=can.get("quantity"), unit=can.get("unit"), axis=axis,
                     group=can.get("comparison_group"),
                     n=len(can.get("values") or []))
                link(canid, rawid, "derived_from_value")
                if can.get("quantity") in present_q:
                    link(canid, "q::" + can["quantity"], "of_kind")
                if can.get("comparison_group") in groups:
                    link(canid, "grp::" + can["comparison_group"], "in_comparison_group")
                if can.get("normalization_definition") in ndefs:
                    link(canid, "nd::" + can["normalization_definition"],
                         "has_normalization_definition")

            # PROJECTIONS: the same axis expressed in a SECOND comparison group
            # once its denominator resolved (x/H + H -> spatial_position in µm).
            for proj in ((c.get("projections") or {}).get(axis) or []):
                pg = proj.get("comparison_group")
                pvid = "canv::%s::%s::proj::%s" % (c["curve_id"], axis, pg)
                node(pvid, "CanonicalQuantityValue",
                     "%s %s [%s] (projected)" % (axis, proj.get("quantity"), proj.get("unit")),
                     quantity=proj.get("quantity"), unit=proj.get("unit"), axis=axis,
                     group=pg, projected=True, n=len(proj.get("values") or []))
                link(pvid, rawid, "derived_from_value")
                if proj.get("quantity") in present_q:
                    link(pvid, "q::" + proj["quantity"], "of_kind")
                if pg in groups:
                    link(pvid, "grp::" + pg, "in_comparison_group")

        for i, t in enumerate(c.get("transformations") or []):
            rid = t.get("rule_id")
            if rid not in rules:
                continue
            xid = "tx::%s::%d" % (c["curve_id"], i)
            node(xid, "TransformationExecution",
                 "%s [%s]" % (rid, t.get("status")),
                 rule=rid, status=t.get("status"), axis=t.get("axis"),
                 formula=t.get("formula"),
                 original_unit=t.get("original_unit"),
                 canonical_unit=t.get("canonical_unit"),
                 comparison_group=t.get("comparison_group"),
                 unresolved_reason=t.get("unresolved_reason"),
                 confidence=t.get("confidence"),
                 code_version=t.get("code_version"),
                 created_at=t.get("created_at"))
            link(xid, "rule::" + rid, "used_rule")
            link(xid, "rawv::%s::%s" % (c["curve_id"], t.get("axis")), "derived_from_value")
            if t.get("status") in ("converted", "already_canonical"):
                for suffix in ("", "::proj::%s" % t.get("comparison_group")):
                    vid = "canv::%s::%s%s" % (c["curve_id"], t.get("axis"), suffix)
                    if vid in nodes and nodes[vid].get("group") == t.get("comparison_group"):
                        link(vid, xid, "produced_by")
            for q, ctx in (t.get("context") or {}).items():
                bid = "ctx::%s::%d::%s" % (c["curve_id"], i, q)
                node(bid, "ContextBinding",
                     "%s = %s %s" % (q, ctx.get("value"), ctx.get("unit") or ""),
                     quantity=q, value=ctx.get("value"), unit=ctx.get("unit"),
                     scope=ctx.get("scope"), status=ctx.get("status"),
                     source_file=ctx.get("source_file"),
                     source_location=ctx.get("source_location"),
                     unresolved_reason=ctx.get("unresolved_reason"))
                link(xid, bid, "used_context")
                if q in present_q:
                    link(bid, "q::" + q, "context_of_kind")


# module-level so the entity layer can validate a quantity without main()'s locals
QK_IDS = {q["id"] for q in ONTO["quantity_kinds"]}
# node type -> ontology class IRI, for the machine-readable graph
ONTO_IRI = {c["id"]: c.get("iri") for c in ONTO["classes"]}


def _load_entities():
    """Typed source entities: what each digitised curve actually is."""
    out = []
    for d in sorted((ROOT / "output").glob("*/resolved/entities.json")):
        try:
            for e in json.loads(d.read_text()):
                e["_pid"] = d.parent.parent.name
                out.append(e)
        except Exception:
            pass
    return out


# entity class -> KG node type. A PlotSeries is evidence, never an Experiment.
_ENTITY_NODE = {
    "ContinuousTrace": "ContinuousTrace",
    "ExperimentalProfile": "ExperimentalProfile",
    "MultiOutputMeasurement": "MultiOutputMeasurement",
    "ExperimentSeries": "ExperimentSeries",
    "SimulationRun": "SimulationRun",
    "ModelSweep": "ModelSweep",
    "ImportedLiteratureObservation": "ImportedLiteratureObservation",
    "Fit": "Fit",
    "DerivedRepresentation": "DerivedRepresentation",
    "UnresolvedSourceEntity": "UnresolvedSourceEntity",
}


def _add_entity_layer(node, link, nodes, present_q):
    """Instantiate the source-entity layer: every curve as a PlotSeries plus its
    typed underlying entity, its observations count, and its bound conditions.
    Non-experimental entities are deliberately NOT Experiment nodes."""
    ents = _load_entities()
    exp_by_id = {n.get("entity_id"): nid for nid, n in nodes.items()
                 if n.get("type") == "Experiment" and n.get("entity_id")}
    for e in ents:
        pid = e["_pid"]
        ps = "ps::" + e["entity_id"]
        node(ps, "PlotSeries", "%s F%s%s %s" % (pid, e.get("printed_figure_number"),
                                                e.get("panel") or "", e.get("source_series")),
             paper=pid, figure=e.get("printed_figure_number"), panel=e.get("panel"),
             series=e.get("source_series"), representation=e.get("representation"),
             observations=e.get("n_observations"))
        node("p::" + pid, "Paper", pid)
        link(ps, "p::" + pid, "from_paper")
        fid = "fig::%s::%s" % (pid, e.get("printed_figure_number"))
        node(fid, "Figure", "%s Fig %s" % (pid, e.get("printed_figure_number")), paper=pid)
        link(ps, fid, "shown_in")

        ntype = _ENTITY_NODE.get(e.get("entity_class"))
        # A sweep already has its ExperimentSeries node built from series.json;
        # reuse it instead of minting a second node for the same series.
        if e.get("entity_class") == "ExperimentSeries" and e.get("experimental_series_id"):
            uid = "es::" + e["experimental_series_id"]
        else:
            uid = "ent::" + e["entity_id"]
        node(uid, ntype or "UnresolvedSourceEntity",
             "%s [%s]" % (e["entity_id"], e.get("classification")),
             paper=pid, classification=e.get("classification"),
             confidence=e.get("classification_confidence"),
             method=e.get("classification_method"),
             evidence="; ".join(e.get("classification_evidence") or [])[:200],
             unresolved_reason=e.get("unresolved_reason"),
             observations=e.get("n_observations"),
             is_current_paper_experiment=bool(e.get("is_current_paper_experiment")),
             cases=e.get("experimental_case_count"),
             case_status=e.get("experimental_case_status"))
        link(uid, ps, "depicted_by")
        link(uid, "p::" + pid, "from_paper")

        # imported literature keeps BOTH papers
        if e.get("classification") == "imported_literature_data":
            link(uid, "p::" + pid, "reported_in")
            if e.get("originally_reported_in"):
                src = "cite::" + e["originally_reported_in"]
                node(src, "Paper", e["originally_reported_in"], cited_work=True)
                link(uid, src, "originally_reported_in")

        # a scaled/normalized panel is a representation of the same measurement
        if e.get("representation") in ("scaled", "normalized", "inset"):
            node(uid, ntype or "DerivedRepresentation", nodes[uid]["label"])
            link(uid, ps, "represents_same_as")

        # the experimental cases minted from this entity
        for nid, n in nodes.items():
            if n.get("type") == "Experiment" and n.get("entity_id") == e["entity_id"]:
                link(nid, uid, "depicted_by")

        for b in e.get("bound_conditions") or []:
            q = b.get("quantity")
            # Mint the QuantityKind node when the condition introduces one. Requiring
            # it to pre-exist silently dropped every assertion whose quantity no
            # experiment happened to measure (working_pressure, purge_time, flow_rate
            # ...), which is exactly the set this layer exists to carry.
            if q and q in QK_IDS:
                if ("q::" + q) not in nodes:
                    node("q::" + q, "Condition", q)
                    present_q.add(q)
            if q in present_q:
                # include the species: an entity can legitimately hold a pulse time
                # for TMA and another for the co-reactant, and a shared id dropped
                # the second one
                bid = "ca::%s::%s::%s" % (e["entity_id"], q,
                                          b.get("species") or b.get("of_reactant") or "-")
                node(bid, "ConditionAssertion",
                     "%s = %s %s" % (q, b.get("value"), b.get("unit") or ""),
                     quantity=q, value=b.get("value"), unit=b.get("unit"),
                     scope=b.get("bound_at_scope"), status=b.get("assertion_status"),
                     evidence_kind=b.get("evidence_kind"), species=b.get("species"),
                     of_reactant=b.get("of_reactant"),
                     evidence=(b.get("raw_evidence") or "")[:160],
                     locator=b.get("evidence_locator"))
                link(uid, bid, "asserts_condition")
                link(bid, "q::" + q, "assertion_of_kind")
        for a in e.get("ambiguous_conditions") or []:
            q = a.get("quantity")
            if q and q in QK_IDS and ("q::" + q) not in nodes:
                node("q::" + q, "Condition", q)
                present_q.add(q)
            if q in present_q:
                aid = "caamb::%s::%s::%s" % (e["entity_id"], q, a.get("species") or "-")
                node(aid, "ConditionAssertion", "%s = AMBIGUOUS" % q,
                     quantity=q, scope=a.get("scope"), status="ambiguous",
                     candidates="; ".join(a.get("candidates") or []),
                     unresolved_reason=a.get("reason"))
                link(uid, aid, "asserts_condition")


def main():
    exps = []
    series_recs = []
    for d in sorted((ROOT / "output").glob("*/resolved/experiments.json")):
        pid = d.parent.parent.name
        for i, e in enumerate(json.loads(d.read_text())):
            e["_pid"], e["_id"] = pid, f"{pid}:{i}"
            exps.append(e)
        sp = d.parent / "series.json"
        if sp.exists():
            for s in json.loads(sp.read_text()):
                s["_pid"] = pid
                series_recs.append(s)

    # dominant role per quantity (across the corpus) -> node type
    role = defaultdict(Counter)
    for e in exps:
        iv = e.get("coordinate")
        if iv: role[iv]["Independent"] += 1
        poi = (e.get("measurand") or {}).get("quantity")
        if poi: role[poi]["Dependent"] += 1
        for c in e.get("controlled") or []:
            q = c.get("quantity")
            if q and q != iv: role[q]["Condition"] += 1
    qtype = {q: cc.most_common(1)[0][0] for q, cc in role.items()}

    nodes, links = {}, []
    def node(nid, ntype, label, **extra):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, **extra}
        return nodes[nid]
    def link(s, t, etype):
        if s in nodes and t in nodes: links.append({"s": s, "t": t, "e": etype})

    for e in exps:
        eid = "e::" + e["_id"]
        reacts = e.get("reactants") or []
        cyc = " · ".join(f"{r['label']}={r.get('species') or r.get('role')}" for r in reacts) or None
        cg = e.get("carrier_gas") or {}
        carrier_str = (cg["species"] + (f" ({cg['flow_sccm']} sccm)" if cg.get("flow_sccm") else "")) if cg.get("species") else None
        node(eid, "Experiment", e.get("exp_id") or e["_id"],
             entity_id=e.get("entity_id"), record_kind=e.get("record_kind"),
             measurement_class=e.get("measurement_class"),
             series=e.get("series_name"),
             relevance=e.get("relevance"), granularity=e.get("granularity"),
             poi=(e.get("measurand") or {}).get("quantity"), paper=e["_pid"],
             material=e.get("material"), cycle=e.get("cycle_sequence"), reactants=cyc,
             carrier=carrier_str, ready=bool(e.get("analysis_ready")))
        if cg.get("species"):                   # carrier/background gas (its own node type)
            node("ca::" + cg["species"], "Carrier", cg["species"], **SPECIES_PROPS.get(cg["species"], {}))
            links.append({"s": eid, "t": "ca::" + cg["species"], "e": "carrier_gas"})
        node("p::" + e["_pid"], "Paper", e["_pid"])
        link(eid, "p::" + e["_pid"], "from_paper")
        if e.get("material"):
            node("m::" + e["material"], "Material", e["material"]); link(eid, "m::" + e["material"], "deposits")
        for r in reacts:                        # precursor / coreactant / carrier from species
            sp, role, lab = r.get("species"), r.get("role"), r.get("label")
            if not sp:
                continue
            if role == "coreactant":
                node("co::" + sp, "Coreactant", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "co::" + sp, "e": "with_coreactant", "reactant": lab})
            elif role == "carrier":
                node("ca::" + sp, "Carrier", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "ca::" + sp, "e": "carrier_gas", "reactant": lab})
            else:
                node("pre::" + sp, "Precursor", sp, **SPECIES_PROPS.get(sp, {}))
                links.append({"s": eid, "t": "pre::" + sp, "e": "uses_precursor", "reactant": lab})
        # role-typed quantity edges
        iv = e.get("coordinate")
        if iv:
            node("q::" + iv, qtype.get(iv, "Condition"), iv); link(eid, "q::" + iv, "varies")
        poi = (e.get("measurand") or {}).get("quantity")
        if poi:
            node("q::" + poi, qtype.get(poi, "Dependent"), poi); link(eid, "q::" + poi, "measures")
        for c in e.get("controlled") or []:
            q = c.get("quantity")
            if q and q != iv:
                node("q::" + q, qtype.get(q, "Condition"), q); link(eid, "q::" + q, "controls")

    # ---- ExperimentSeries: a condition sweep is a SERIES of experiments -----
    # Each point of a condition-axis curve is its own Experiment; the curve is the
    # series that varies the condition across them. Spatial profiles are NOT
    # series — they stay single profile experiments.
    _exp_by_label = {}
    for nid, n in nodes.items():
        if n.get("type") == "Experiment":
            _exp_by_label[n.get("label")] = nid
    for s in series_recs:
        sid = "es::" + s["series_id"]
        node(sid, "ExperimentSeries", s["series_id"],
             paper=s.get("doi") or s["_pid"],
             varies=s.get("series_varies"), unit=s.get("series_varies_unit"),
             n=s.get("n_experiments"), material=s.get("material"),
             measurand=(s.get("measurand") or {}).get("quantity"),
             relevance=s.get("relevance"),
             replaced=s.get("replaced_experiment_id"))
        node("p::" + (s.get("doi") or s["_pid"]), "Paper", s.get("doi") or s["_pid"])
        link(sid, "p::" + (s.get("doi") or s["_pid"]), "from_paper")
        if s.get("series_varies"):
            node("q::" + s["series_varies"], qtype.get(s["series_varies"], "Condition"),
                 s["series_varies"])
            link(sid, "q::" + s["series_varies"], "series_varies")
        for eid_label in s.get("experiment_ids") or []:
            nid = _exp_by_label.get(eid_label)
            if nid:
                link(nid, sid, "in_series")

    # ---- ONTOLOGY LAYER: quantity↔quantity relations from the ontology ----
    # (shows that e.g. normalized_thickness & film_thickness are related, via a
    #  shared Family node + a transform edge, plus specializes / same_as)
    present_q = {nid[3:] for nid in nodes if nid.startswith("q::")}
    QK = {q["id"]: q for q in ONTO["quantity_kinds"]}
    qr = ONTO.get("quantity_relations", {})
    for fam, spec in (qr.get("families") or {}).items():
        members = [m for m in spec.get("members", []) if m in present_q]
        if len(members) >= 1:
            fn = "fam::" + fam
            node(fn, "Family", fam, canonical=spec.get("canonical"))
            for m in members:
                link("q::" + m, fn, "in_family")
    for cat, members in (qr.get("categories") or {}).items():        # semantic categories
        ms = [m for m in members if m in present_q]
        if ms:
            cn = "cat::" + cat
            node(cn, "Category", cat)
            for m in ms:
                link("q::" + m, cn, "in_category")
    for t in qr.get("transforms", []) or []:
        if t.get("from") in present_q and t.get("to") in present_q:
            links.append({"s": "q::" + t["from"], "t": "q::" + t["to"], "e": "transforms_to",
                          "bridge": t.get("bridge")})
    for qid in present_q:
        q = QK.get(qid, {})
        if q.get("specializes") in present_q:
            links.append({"s": "q::" + qid, "t": "q::" + q["specializes"], "e": "specializes"})
        if q.get("same_as") in present_q:
            links.append({"s": "q::" + qid, "t": "q::" + q["same_as"], "e": "same_as"})

    # ---- COMPARABILITY LAYER -------------------------------------------------
    # Canonical values are linked back to the raw evidence that produced them and
    # to the rule that produced them, so nothing in the graph is a bare number:
    #
    #   Experiment --has_raw_value--> RawQuantityValue
    #   CanonicalQuantityValue --derived_from_value--> RawQuantityValue
    #   CanonicalQuantityValue --produced_by--> TransformationExecution
    #   TransformationExecution --used_rule--> TransformationRule
    #   TransformationExecution --used_context--> ContextBinding
    #   CanonicalQuantityValue --in_comparison_group--> ComparisonGroup
    #   ComparisonGroup --group_normalization--> NormalizationDefinition
    _add_entity_layer(node, link, nodes, present_q)
    _add_comparability_layer(node, link, links, nodes, present_q)

    # ---- MODEL LAYER: kinetic/transport MODELS as ontology objects ----
    # each Model links to its family, the quantities it consumes (shared with the
    # experiments that measure them), the paper it comes from, and related models.
    fams = ONTO.get("model_families", {}) or {}
    models = ONTO.get("models", []) or []
    model_ids = {m["id"] for m in models}
    for fid, spec in fams.items():
        node("mfam::" + fid, "ModelFamily", spec.get("name", fid), base=spec.get("base"))
    for m in models:
        mid = "mdl::" + m["id"]
        node(mid, "Model", m.get("name", m["id"]),
             branch=m.get("branch"), predicts=", ".join(m.get("predicts", []) or [])[:120],
             paper=(m.get("reference") or {}).get("ref_tag"),
             equations=len(m.get("equations", []) or []),
             implemented_by=m.get("implemented_by"))
        if m.get("family"):
            link(mid, "mfam::" + m["family"], "in_model_family")
        for inp in m.get("inputs", []) or []:                 # model consumes a quantity
            q = inp.get("quantity")
            if q in present_q:
                link(mid, "q::" + q, "model_consumes")
        ref = (m.get("reference") or {}).get("ref_tag")
        if ref and ("p::" + ref) in nodes:                    # model ← its paper
            link(mid, "p::" + ref, "model_from_paper")
        for rel in ([m.get("related_to")] if isinstance(m.get("related_to"), str) else (m.get("related_to") or [])) \
                + (m.get("shares_base_kinetics_with") or []):
            if rel in model_ids:
                links.append({"s": mid, "t": "mdl::" + rel, "e": "model_related"})

    # dedup identical edges, compute degree
    seen, uniq = set(), []
    for l in links:
        k = (l["s"], l["t"], l["e"])
        if k not in seen: seen.add(k); uniq.append(l)
    links = uniq
    deg = defaultdict(int)
    for l in links: deg[l["s"]] += 1; deg[l["t"]] += 1
    for n in nodes.values(): n["deg"] = deg[n["id"]]

    counts = Counter(n["type"] for n in nodes.values())
    data = {"nodes": list(nodes.values()), "links": links, "counts": dict(counts),
            "edgeCounts": dict(Counter(l["e"] for l in links)),
            "papers": sorted({e["_pid"] for e in exps}),
            "materials": sorted({e["material"] for e in exps if e.get("material")}),
            "relevances": sorted({e.get("relevance") for e in exps if e.get("relevance")})}
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data))
    (ROOT / "kg_viewer.html").write_text(html)
    # Also write the machine-readable graph. Until now only the HTML was rebuilt, so
    # knowledge_graph_onto.json stayed frozen at the version the (dead) s09_kg.py
    # produced months ago, and every consumer of it -- 01_ontology/validate.py,
    # build_dashboard.py -- was reading a stale graph.
    onto_nodes = []
    for n in nodes.values():
        m = {"id": n["id"], "ntype": n.get("type"), "name": n.get("label"),
             "onto_class": ONTO_IRI.get(n.get("type"))}
        for k, v in n.items():
            if k not in ("id", "type", "label"):
                m[k] = v
        onto_nodes.append(m)
    graph = {"directed": True, "multigraph": True, "graph": {},
             "nodes": onto_nodes,
             "links": [{"source": l["s"], "target": l["t"], "key": l["e"],
                        "etype": l["e"],
                        **{k: v for k, v in l.items() if k not in ("s", "t", "e")}}
                       for l in links],
             "counts": data.get("counts"), "edgeCounts": data.get("edgeCounts")}
    (ROOT / "output" / "knowledge_graph_onto.json").write_text(json.dumps(graph, indent=1))
    print(f"wrote kg_viewer.html  ({len(html)//1024} KB)  {len(nodes)} nodes, {len(links)} edges")
    print(f"wrote output/knowledge_graph_onto.json")
    print("   node types:", dict(counts))
    print("   edge types:", data["edgeCounts"])


TEMPLATE = r"""<title>ALD Knowledge Graph</title>
<style>
:root{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--Independent:#0f9bd8;--Dependent:#eda100;--Condition:#9aa0aa;--Precursor:#e34948;--Coreactant:#e87ba4;--Carrier:#7a8b99;--e-carrier_gas:#7a8b99;--Family:#7d5ba6;--Model:#d81b60;--ModelFamily:#8e24aa;--Category:#c65d3b;--e-in_family:#7d5ba6;--e-in_category:#c65d3b;--e-transforms_to:#0f9bd8;--e-specializes:#1baf7a;--e-same_as:#9aa0aa;
 --e-varies:#0f9bd8;--e-measures:#eda100;--e-controls:#c3c7cd;--e-from_paper:#4a3aa7;--e-deposits:#1baf7a;--e-uses_precursor:#e34948;--e-with_coreactant:#e87ba4;--e-in_model_family:#8e24aa;--e-model_consumes:#d81b60;--e-model_from_paper:#7d5ba6;--e-model_related:#d81b60;}
@media(prefers-color-scheme:dark){:root{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--Independent:#33a9dd;--Dependent:#c98500;--Condition:#6b7079;--Precursor:#e66767;--Coreactant:#d55181;--Carrier:#8b9aa8;--e-carrier_gas:#8b9aa8;--Family:#a98cd6;--Model:#ec407a;--ModelFamily:#ab47bc;--Category:#e07a54;--e-in_family:#a98cd6;--e-in_category:#e07a54;--e-transforms_to:#33a9dd;--e-specializes:#199e70;--e-same_as:#767c86;
 --e-varies:#33a9dd;--e-measures:#c98500;--e-controls:#3a3d44;--e-from_paper:#9085e9;--e-deposits:#199e70;--e-uses_precursor:#e66767;--e-with_coreactant:#d55181;--e-in_model_family:#ab47bc;--e-model_consumes:#ec407a;--e-model_from_paper:#a98cd6;--e-model_related:#ec407a;}}
:root[data-theme="dark"]{--bg:#131417;--panel:#1c1e22;--surface:#1a1a19;--ink:#eceef2;--ink2:#a8adb7;--ink3:#767c86;--line:#2b2e34;--line2:#232529;--accent:#3987e5;
 --Paper:#9085e9;--Experiment:#3987e5;--Material:#199e70;--Independent:#33a9dd;--Dependent:#c98500;--Condition:#6b7079;--Precursor:#e66767;--Coreactant:#d55181;--Carrier:#8b9aa8;--e-carrier_gas:#8b9aa8;--Family:#a98cd6;--Model:#ec407a;--ModelFamily:#ab47bc;--Category:#e07a54;--e-in_family:#a98cd6;--e-in_category:#e07a54;--e-transforms_to:#33a9dd;--e-specializes:#199e70;--e-same_as:#767c86;
 --e-varies:#33a9dd;--e-measures:#c98500;--e-controls:#3a3d44;--e-from_paper:#9085e9;--e-deposits:#199e70;--e-uses_precursor:#e66767;--e-with_coreactant:#d55181;--e-in_model_family:#ab47bc;--e-model_consumes:#ec407a;--e-model_from_paper:#a98cd6;--e-model_related:#ec407a;}
:root[data-theme="light"]{--bg:#f4f6f8;--panel:#fff;--surface:#fcfcfb;--ink:#14161a;--ink2:#565c66;--ink3:#8b919b;--line:#e6e8ec;--line2:#eef0f3;--accent:#2a78d6;
 --Paper:#4a3aa7;--Experiment:#2a78d6;--Material:#1baf7a;--Independent:#0f9bd8;--Dependent:#eda100;--Condition:#9aa0aa;--Precursor:#e34948;--Coreactant:#e87ba4;--Carrier:#7a8b99;--e-carrier_gas:#7a8b99;--Family:#7d5ba6;--Model:#d81b60;--ModelFamily:#8e24aa;--Category:#c65d3b;--e-in_family:#7d5ba6;--e-in_category:#c65d3b;--e-transforms_to:#0f9bd8;--e-specializes:#1baf7a;--e-same_as:#9aa0aa;
 --e-varies:#0f9bd8;--e-measures:#eda100;--e-controls:#c3c7cd;--e-from_paper:#4a3aa7;--e-deposits:#1baf7a;--e-uses_precursor:#e34948;--e-with_coreactant:#e87ba4;--e-in_model_family:#8e24aa;--e-model_consumes:#d81b60;--e-model_from_paper:#7d5ba6;--e-model_related:#d81b60;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1320px;margin:0 auto;padding:22px 20px 40px}
h1{font-size:23px;margin:0 0 2px;font-weight:600;font-family:"Iowan Old Style",Georgia,serif}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:600}
.sub{color:var(--ink2);margin-bottom:12px}
.bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
.grp{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);margin:0 2px}
.chip{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:4px 11px 4px 8px;color:var(--ink2);font-size:12px;cursor:pointer;user-select:none}
.chip.off{opacity:.32;text-decoration:line-through}
.dot{width:10px;height:10px;border-radius:3px;flex:none}.edg{width:16px;border-top:3px solid;flex:none}
details.ms{position:relative}
details.ms>summary{list-style:none;cursor:pointer;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:5px 10px;font-size:12px;color:var(--ink2)}
details.ms>summary::-webkit-details-marker{display:none}
details.ms[open]>summary{border-color:var(--accent)}
.mspanel{position:absolute;z-index:20;top:110%;left:0;min-width:150px;max-height:260px;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:6px;box-shadow:0 8px 24px rgba(0,0,0,.14)}
.mspanel label{display:flex;align-items:center;gap:7px;padding:4px 6px;font-size:12px;border-radius:6px;cursor:pointer}
.mspanel label:hover{background:var(--line2)}
input[type=search]{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:5px 9px;color:var(--ink);font-size:12px;min-width:160px}
button.mini,select.mini{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:5px 10px;color:var(--accent);font-size:12px;cursor:pointer}
select.mini{color:var(--ink)}
button.mini:hover,select.mini:hover{border-color:var(--accent)}
.stage{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-top:6px}
svg{display:block;width:100%;aspect-ratio:1280/720;height:auto;touch-action:none;cursor:grab;background:
 radial-gradient(circle at 50% 42%,color-mix(in srgb,var(--accent) 5%,transparent),transparent 62%)}
svg.drag{cursor:grabbing}
.info{position:absolute;top:12px;right:12px;width:262px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 13px;font-size:12.5px;display:none;max-height:88%;overflow:auto;box-shadow:0 8px 24px rgba(0,0,0,.10)}
.info h3{margin:0 0 6px;font-size:13.5px}.info .k{color:var(--ink3);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.info .row{margin:5px 0}.info .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.ichip{font-size:11px;padding:1px 7px;border-radius:5px;background:var(--line2);color:var(--ink2)}
.zoom{position:absolute;left:12px;bottom:12px;display:flex;flex-direction:column;gap:6px;z-index:6}
.zoom button{width:34px;height:34px;border-radius:9px;border:1px solid var(--line);background:var(--panel);color:var(--ink2);font-size:18px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.08)}
.zoom button:hover{border-color:var(--accent);color:var(--ink)}
.ov{position:absolute;left:50%;top:14px;transform:translateX(-50%);display:flex;gap:9px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:7px 15px;font-size:12px;color:var(--ink2);z-index:12;box-shadow:0 6px 20px rgba(0,0,0,.16)}
.ov[hidden]{display:none}
.spin{width:15px;height:15px;border-radius:50%;border:2px solid var(--line);border-top-color:var(--accent);animation:sp .8s linear infinite}
.spin[hidden]{display:none}
@keyframes sp{to{transform:rotate(360deg)}}
.err{position:absolute;left:12px;right:12px;top:12px;z-index:30;background:#fdecea;color:#7a1c12;border:1px solid #f5c6c0;border-radius:10px;padding:11px 14px;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;max-height:60%;overflow:auto;box-shadow:0 8px 24px rgba(0,0,0,.16)}
@media(prefers-color-scheme:dark){.err{background:#3a1c1a;color:#f4b6ae;border-color:#5c2a25}}
.err[hidden]{display:none}
.hint{font-size:12px;color:var(--ink3);margin-top:8px}
</style>
<div class="wrap">
<div class="eyebrow">ALD Knowledge Base · ontology-grounded KG</div>
<h1>Knowledge graph</h1>
<div class="sub" id="sub"></div>
<div class="bar">
  <span class="grp">layout</span>
  <select class="mini" id="mode" title="layout mode">
    <option value="force">force-directed</option>
    <option value="hier">hierarchical</option>
    <option value="radial">radial</option>
  </select>
  <span class="grp">filter</span>
  <details class="ms" id="msPaper"><summary>paper: all</summary><div class="mspanel"></div></details>
  <details class="ms" id="msMat"><summary>material: all</summary><div class="mspanel"></div></details>
  <details class="ms" id="msRel"><summary>relevance: all</summary><div class="mspanel"></div></details>
  <input type="search" id="search" placeholder="search label… (↵ to centre)">
  <button class="mini" id="btnFit">fit to screen</button>
  <button class="mini" id="btnReset">reset layout</button>
  <button class="mini" id="btnClear">clear</button>
</div>
<div class="bar" id="legNodes"><span class="grp">node types</span></div>
<div class="bar" id="legEdges"><span class="grp">edge types</span></div>
<div class="stage">
  <svg id="svg"></svg>
  <div class="info" id="info"></div>
  <div class="zoom">
    <button id="zin" title="zoom in">+</button>
    <button id="zout" title="zoom out">&minus;</button>
    <button id="zfit" title="fit to screen">&#9974;</button>
  </div>
  <div class="ov" id="ov" hidden><div class="spin" id="ovspin"></div><span id="ovtx">stabilizing…</span></div>
  <div class="err" id="err" hidden></div>
</div>
<div class="hint"><b>drag a node</b> to move it · <b>drag the background</b> to pan · <b>scroll</b> to zoom · <b>click a node</b> to inspect &amp; highlight its neighbourhood · type in <b>search</b> then ↵ to centre on a node · node/edge chips and the dropdowns hide categories without changing the graph.</div>
</div>
<script>
"use strict";
/* ---------- global runtime error surface: visible in-page + console ---------- */
function showError(msg){try{var e=document.getElementById("err");if(e){e.hidden=false;e.textContent="⚠ viewer error\n"+msg;}var ov=document.getElementById("ov");if(ov)ov.hidden=true;}catch(_){}}
window.addEventListener("error",function(ev){showError((ev.error&&ev.error.stack)||ev.message||String(ev));});
window.addEventListener("unhandledrejection",function(ev){showError("unhandled promise rejection: "+((ev.reason&&ev.reason.stack)||ev.reason||ev));});
var T0=performance.now();
function tlog(s){try{console.log("[kg] "+s+"  @ "+(performance.now()-T0).toFixed(0)+"ms");}catch(_){}}

try { boot(); } catch(err){ showError((err&&err.stack)||String(err)); try{console.error(err);}catch(_){}}

function boot(){
tlog("boot() entered");
const D=/*DATA*/;
tlog("data parsed — "+D.nodes.length+" nodes, "+D.links.length+" edges");
const NS="http://www.w3.org/2000/svg",el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a||{})e.setAttribute(k,a[k]);return e;};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const fin=Number.isFinite;
const VBW=1280,VBH=720,CX=VBW/2,CY=VBH/2;
const NT=["Paper","Experiment","Material","Independent","Dependent","Condition","Category","Family","Model","ModelFamily","Precursor","Coreactant","Carrier"].filter(t=>D.counts[t]);
const ET=["from_paper","deposits","varies","measures","controls","in_category","in_family","transforms_to","specializes","same_as","in_model_family","model_consumes","model_from_paper","model_related","uses_precursor","with_coreactant","carrier_gas"].filter(t=>D.edgeCounts[t]);
const offN=new Set(["Family","Precursor","Coreactant"].filter(t=>D.counts[t]));
const offE=new Set(["controls","in_family","uses_precursor","with_coreactant"].filter(t=>D.edgeCounts[t]));
const selPaper=new Set(), selMat=new Set(), selRel=new Set();
document.getElementById("sub").textContent=`${D.nodes.length} nodes · ${D.links.length} edges · `+NT.map(t=>`${D.counts[t]} ${t}`).join(" · ");

// ---- indices, neighbours, incident edges (cached ONCE — never queried in the loop) ----
const idx=Object.fromEntries(D.nodes.map(n=>[n.id,n]));
const nbr=Object.fromEntries(D.nodes.map(n=>[n.id,new Set()]));
D.nodes.forEach(n=>n._inc=[]);
D.links.forEach(l=>{l._a=idx[l.s];l._b=idx[l.t];if(l._a&&l._b){nbr[l.s].add(l.t);nbr[l.t].add(l.s);l._a._inc.push(l);l._b._inc.push(l);}});
function radiusOf(n){return n.type==="Experiment"?4.4:n.type==="Paper"?clamp(11+n.deg*0.25,11,22):clamp(7+n.deg*0.5,7,19);}
D.nodes.forEach(n=>{n.r=radiusOf(n);n.q=9+Math.min(n.deg,60)*0.6;});

// ---- multi-select dropdowns ----
function fillMS(id,opts,set,label){
  const d=document.getElementById(id),panel=d.querySelector(".mspanel"),sum=d.querySelector("summary");
  panel.innerHTML=opts.map(o=>`<label><input type="checkbox" value="${o}">${o}</label>`).join("");
  panel.querySelectorAll("input").forEach(cb=>cb.onchange=()=>{cb.checked?set.add(cb.value):set.delete(cb.value);
    sum.textContent=`${label}: ${set.size?[...set].join(", ").slice(0,22)+(set.size>1?` (${set.size})`:""):"all"}`;render();});
}
fillMS("msPaper",D.papers,selPaper,"paper");
fillMS("msMat",D.materials,selMat,"material");
fillMS("msRel",D.relevances,selRel,"relevance");
document.addEventListener("click",e=>{document.querySelectorAll("details.ms[open]").forEach(d=>{if(!d.contains(e.target))d.open=false;});});

// ---- node-type + edge-type chips (temporary hide, graph unchanged) ----
document.getElementById("legNodes").insertAdjacentHTML("beforeend",NT.map(t=>`<span class="chip ${offN.has(t)?"off":""}" data-t="${t}" onclick="togN('${t}')"><span class="dot" style="background:var(--${t})"></span>${t} <span style="color:var(--ink3)">${D.counts[t]}</span></span>`).join(""));
document.getElementById("legEdges").insertAdjacentHTML("beforeend",ET.map(t=>`<span class="chip ${offE.has(t)?"off":""}" data-e="${t}" onclick="togE('${t}')"><span class="edg" style="border-color:var(--e-${t})"></span>${t} <span style="color:var(--ink3)">${D.edgeCounts[t]}</span></span>`).join(""));
window.togN=t=>{offN.has(t)?offN.delete(t):offN.add(t);document.querySelector(`[data-t="${t}"]`).classList.toggle("off");render();};
window.togE=t=>{offE.has(t)?offE.delete(t):offE.add(t);document.querySelector(`[data-e="${t}"]`).classList.toggle("off");render();};

// =====================================================================
//  LAYOUT — grid-accelerated force (default) + hierarchical + radial.
//  Startup collision uses NODE RADIUS ONLY (no text bounding boxes).
// =====================================================================
let MODE="force", settling=false, partial=false, simRAF=null, rafCount=0, watchdog=null, finished=false, alpha=1;
const layerOf=t=>({Paper:0,ModelFamily:0,Model:0,Category:0,Family:0,Experiment:1,Material:2,Independent:2,Dependent:2,Condition:2,Precursor:3,Coreactant:3,Carrier:3}[t]??2);
const ROWY=[95,290,490,655], RINGR=[70,195,305,398];
// NB: every ring radius is > 0 and each node is jittered by index — NO two nodes may share
// a coordinate, otherwise d²=0 gives an infinite repulsion kick and the sim explodes.
function seedForce(){const ring={Paper:34,Category:70,Family:110,ModelFamily:92,Model:120,Material:150,Dependent:200,Independent:210,Condition:270,Precursor:320,Coreactant:350,Carrier:365,Experiment:455};
  D.nodes.forEach((n,i)=>{const r=(ring[n.type]??400)+(i%9)*3,a=i*2.399963;n.x=CX+r*Math.cos(a);n.y=CY+r*Math.sin(a);n.vx=0;n.vy=0;});}
function byLayer(){const g={};D.nodes.forEach(n=>{const L=layerOf(n.type);(g[L]=g[L]||[]).push(n);});return g;}
function seedRadial(){const g=byLayer();Object.keys(g).forEach(L=>{const arr=g[L];arr.sort((a,b)=>(a.type+a.label).localeCompare(b.type+b.label));
  const R=RINGR[L]??430;arr.forEach((n,i)=>{const a=2*Math.PI*i/Math.max(arr.length,1)-Math.PI/2;n._R=R;n.x=CX+R*Math.cos(a);n.y=CY+R*Math.sin(a);n.vx=n.vy=0;});});}
function seedHier(){const g=byLayer();Object.keys(g).forEach(L=>{const arr=g[L];arr.sort((a,b)=>((a.paper||a.type)+a.label).localeCompare((b.paper||b.type)+b.label));
  const y=ROWY[L]??690,pad=70,w=VBW-2*pad;arr.forEach((n,i)=>{n._layer=+L;n.y=y;n.x=pad+(arr.length<2?w/2:w*i/(arr.length-1));n.vx=n.vy=0;});});}

// uniform spatial grid → repulsion + collision are O(N·k), not O(N²)
function gridBuild(C){const G=new Map();for(const n of D.nodes){const k=Math.floor(n.x/C)+"|"+Math.floor(n.y/C);let a=G.get(k);if(!a)G.set(k,a=[]);a.push(n);}return G;}
// GUARD: a non-finite cell index would make `for(ix=Infinity;ix<=Infinity;ix++)` loop
// forever and freeze the tab. Never iterate on non-finite coordinates.
function eachNear(n,G,C,fn){const gx=Math.floor(n.x/C),gy=Math.floor(n.y/C);
  if(!fin(gx)||!fin(gy))return;
  for(let ix=gx-1;ix<=gx+1;ix++)for(let iy=gy-1;iy<=gy+1;iy++){const a=G.get(ix+"|"+iy);if(a)for(const m of a)if(m!==n)fn(m);}}
const BOUND=2600;                                   // hard world clamp — coords can never overflow
function collide(project){const C=64,G=gridBuild(C);
  for(const n of D.nodes){if(n.fx!=null)continue;eachNear(n,G,C,m=>{
    let dx=n.x-m.x,dy=n.y-m.y,d=Math.sqrt(dx*dx+dy*dy);if(d<0.5)d=0.5;const minD=n.r+m.r+9;
    if(d<minD){const p=(minD-d)*0.5;n.x=clamp(n.x+dx/d*p,CX-BOUND,CX+BOUND);n.y=clamp(n.y+dy/d*p,CY-BOUND,CY+BOUND);}});}
  if(project)D.nodes.forEach(project);}
function tickForce(){const N=D.nodes,C=70,G=gridBuild(C);
  for(const n of N){eachNear(n,G,C,m=>{
    let dx=n.x-m.x,dy=n.y-m.y,d=Math.sqrt(dx*dx+dy*dy);if(d<2)d=2;      // distance floor: no singular kick
    let f=n.q*m.q/(d*d);const minD=n.r+m.r+8;if(d<minD)f+=(minD-d)*0.85/d;
    if(f>180)f=180;f*=alpha;                                           // cap repulsion + cooling
    n.vx+=dx/d*f;n.vy+=dy/d*f;});}
  for(const l of D.links){const a=l._a,b=l._b;if(!a||!b)continue;
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,rest=52+a.r+b.r,f=(d-rest)*0.02*alpha;
    const ux=dx/d,uy=dy/d;a.vx+=ux*f;a.vy+=uy*f;b.vx-=ux*f;b.vy-=uy*f;}
  let mv=0;for(const n of N){if(n.fx!=null){n.x=n.fx;n.y=n.fy;n.vx=n.vy=0;continue;}
    n.vx+=(CX-n.x)*0.004*alpha;n.vy+=(CY-n.y)*0.004*alpha;
    n.vx=clamp(n.vx*0.86,-70,70);n.vy=clamp(n.vy*0.86,-70,70);         // velocity cap → cannot explode
    n.x=clamp(n.x+n.vx,CX-BOUND,CX+BOUND);n.y=clamp(n.y+n.vy,CY-BOUND,CY+BOUND);   // hard coord clamp
    mv+=Math.abs(n.vx)+Math.abs(n.vy);}
  alpha*=0.972;                          // cooling: temperature decays → movement settles → clean convergence
  return mv/N.length;}
function tickRadial(){for(const n of D.nodes){if(n.fx!=null)continue;let sx=0,sy=0,c=0;
    for(const m of nbr[n.id]){const o=idx[m];sx+=o.x;sy+=o.y;c++;}if(c){n.x+=(sx/c-n.x)*0.05;n.y+=(sy/c-n.y)*0.05;}}
  collide(n=>{const a=Math.atan2(n.y-CY,n.x-CX);n.x=CX+n._R*Math.cos(a);n.y=CY+n._R*Math.sin(a);});
  return 0.2;}
function tickHier(){for(const n of D.nodes){if(n.fx!=null)continue;let sx=0,c=0;
    for(const m of nbr[n.id]){sx+=idx[m].x;c++;}if(c)n.x+=(sx/c-n.x)*0.08;}
  const rows={};D.nodes.forEach(n=>{(rows[n._layer]=rows[n._layer]||[]).push(n);});
  Object.values(rows).forEach(arr=>{arr.sort((a,b)=>a.x-b.x);const pad=60;
    for(let i=1;i<arr.length;i++){const g=arr[i-1].r+arr[i].r+8;if(arr[i].x-arr[i-1].x<g)arr[i].x=arr[i-1].x+g;}
    arr.forEach(n=>n.x=clamp(n.x,pad,VBW-pad));});
  D.nodes.forEach(n=>n.y=ROWY[n._layer]??690);
  return 0.2;}
const SEED={force:seedForce,radial:seedRadial,hier:seedHier};
const STEP={force:tickForce,radial:tickRadial,hier:tickHier};

// hard stabilization budget — the sim can NEVER run indefinitely
const BUDGET_MS=3500, ITERS_PER_FRAME=6, STOP_MOVE=0.30;
const MAXIT={force:300,radial:120,hier:90};
function sanitize(){let bad=0;D.nodes.forEach((n,i)=>{if(!fin(n.x)||!fin(n.y)){const a=i*2.399963,r=70+(i%16)*24;n.x=CX+r*Math.cos(a);n.y=CY+r*Math.sin(a);n.vx=0;n.vy=0;bad++;}});return bad;}
function deterministicFallback(reason){tlog("FALLBACK ("+reason+") → deterministic radial placement");
  try{seedRadial();}catch(_){D.nodes.forEach((n,i)=>{const a=i*2.399963,r=70+(i%16)*24;n.x=CX+r*Math.cos(a);n.y=CY+r*Math.sin(a);n.vx=n.vy=0;});}
  sanitize();partial=true;}

// =====================================================================
//  PERSISTENT DOM  — colours resolved ONCE via inline var(); the render
//  loop never calls getComputedStyle (that was the freeze).
// =====================================================================
const svg=el("svg",{viewBox:`0 0 ${VBW} ${VBH}`,preserveAspectRatio:"xMidYMid meet"});svg.id="svg";
document.getElementById("svg").replaceWith(svg);
const view=el("g");svg.appendChild(view);
let gL=el("g"),gN=el("g");view.appendChild(gL);view.appendChild(gN);
tlog("SVG created");
D.links.forEach(l=>{l._el=el("line",{"stroke-linecap":"round"});l._el.style.stroke=`var(--e-${l.e}, var(--line))`;gL.appendChild(l._el);});
tlog("edges rendered (DOM built, deferred until settle)");
D.nodes.forEach(n=>{n._g=el("g");n._c=el("circle",{"stroke-width":1.3});
  n._c.style.fill=`var(--${n.type})`;n._c.style.stroke="var(--surface)";
  n._t=el("text",{"font-size":11,"pointer-events":"none"});n._t.style.fill="var(--ink2)";n._t.style.display="none";
  n._t.textContent=n.label.length>22?n.label.slice(0,21)+"…":n.label;
  n._g.appendChild(n._c);n._g.appendChild(n._t);gN.appendChild(n._g);
  n._c.addEventListener("pointerdown",ev=>startDrag(ev,n));});
tlog("nodes rendered (DOM built)");

let tx=0,ty=0,scale=1,sel=null,q="";
function updateView(){if(fin(tx)&&fin(ty)&&fin(scale))view.setAttribute("transform",`translate(${tx} ${ty}) scale(${scale})`);}

function visibleNodes(){
  const vis=new Set();
  D.nodes.forEach(n=>{if(n.type!=="Experiment")return;if(offN.has("Experiment"))return;
    if(selPaper.size&&!selPaper.has(n.paper))return;
    if(selRel.size&&!selRel.has(n.relevance))return;
    if(selMat.size&&!selMat.has(n.material))return;
    vis.add(n.id);});
  D.nodes.forEach(n=>{if(n.type==="Experiment"||offN.has(n.type))return;
    for(const m of nbr[n.id])if(vis.has(m)){vis.add(n.id);break;}});
  return vis;
}
function applyNodeVisibility(){const vis=visibleNodes();for(const n of D.nodes)n._g.style.display=vis.has(n.id)?"":"none";return vis;}

// positions only (used during stabilization) — edges untouched, labels untouched
function drawNodes(){for(const n of D.nodes){if(n._g.style.display==="none")continue;
  const x=n.x,y=n.y;if(!fin(x)||!fin(y))continue;
  n._c.setAttribute("cx",x);n._c.setAttribute("cy",y);n._c.setAttribute("r",n.r);}}

// full styled recompute (post-settle & on interaction) — NO getComputedStyle
function render(){
  const vis=visibleNodes(),hi=sel,ql=q.toLowerCase();
  for(const l of D.links){const on=vis.has(l.s)&&vis.has(l.t)&&!offE.has(l.e),a=l._a,b=l._b;
    if(!on||!a||!b||!(fin(a.x)&&fin(a.y)&&fin(b.x)&&fin(b.y))){l._el.style.display="none";continue;}
    l._el.style.display="";
    const near=hi&&(l.s===hi||l.t===hi),dim=hi&&!near;
    l._el.setAttribute("x1",a.x);l._el.setAttribute("y1",a.y);l._el.setAttribute("x2",b.x);l._el.setAttribute("y2",b.y);
    l._el.setAttribute("stroke-width",near?2:(l.e==="from_paper"||l.e==="deposits"?1.1:.7));
    l._el.setAttribute("opacity",dim?.05:(l.e==="controls"?.28:.6));}
  for(const n of D.nodes){const on=vis.has(n.id);
    if(!on||!fin(n.x)||!fin(n.y)){n._g.style.display="none";continue;}
    n._g.style.display="";
    const near=!hi||n.id===hi||nbr[hi].has(n.id),match=!ql||n.label.toLowerCase().includes(ql);
    n._c.setAttribute("cx",n.x);n._c.setAttribute("cy",n.y);n._c.setAttribute("r",n.r);
    n._c.setAttribute("opacity",(near&&match)?1:.12);
    if(n.id===hi){n._c.setAttribute("stroke-width",2.4);n._c.style.stroke="var(--ink)";}
    else{n._c.setAttribute("stroke-width",1.3);n._c.style.stroke="var(--surface)";}
    const showT=(n.id===hi)||(hi&&nbr[hi].has(n.id))||(n.type==="Paper")||(n.type!=="Experiment"&&n.deg>=2)||(ql&&match);
    if(showT){n._t.style.display="";n._t.setAttribute("x",n.x+n.r+3);n._t.setAttribute("y",n.y+3.5);
      n._t.setAttribute("font-weight",(n.type==="Paper"||n.id===hi)?600:400);n._t.setAttribute("opacity",(near&&match)?1:.12);}
    else n._t.style.display="none";}
}

// cheap single-node update while dragging (cached incident edges)
function dragUpdate(n){if(!fin(n.x)||!fin(n.y))return;
  n._c.setAttribute("cx",n.x);n._c.setAttribute("cy",n.y);
  if(n._t.style.display!=="none"){n._t.setAttribute("x",n.x+n.r+3);n._t.setAttribute("y",n.y+3.5);}
  for(const l of n._inc){if(l._el.style.display==="none")continue;const a=l._a,b=l._b;
    if(fin(a.x)&&fin(a.y)&&fin(b.x)&&fin(b.y)){l._el.setAttribute("x1",a.x);l._el.setAttribute("y1",a.y);l._el.setAttribute("x2",b.x);l._el.setAttribute("y2",b.y);}}}

// =====================================================================
//  STABILIZATION LOOP — single rAF, budget-capped, edges deferred
// =====================================================================
const ovEl=document.getElementById("ov"),ovTx=document.getElementById("ovtx"),ovSpin=document.getElementById("ovspin");
function overlay(on,text,spin){ovEl.hidden=!on;if(text!=null)ovTx.textContent=text;ovSpin.hidden=(spin===false);}

function runLayout(){
  if(simRAF){cancelAnimationFrame(simRAF);simRAF=null;}
  if(watchdog){clearTimeout(watchdog);watchdog=null;}
  settling=true;partial=false;finished=false;rafCount=0;alpha=1;sel=null;showInfo(null);overlay(true,"stabilizing…",true);
  tlog("stabilize() entered — mode="+MODE);
  try{SEED[MODE]();}catch(e){tlog("EXIT: seed threw");showError("seed failed: "+((e&&e.stack)||e));deterministicFallback("seed threw");}
  const sc=sanitize();if(sc)tlog("seed sanitize fixed "+sc+" non-finite coords");
  gL.style.display="none";              // progressive: defer edges during stabilization
  applyNodeVisibility();                 // node display per filters (no colour work)
  drawNodes();                           // first usable paint — nodes visible immediately
  tlog("layout initialized ("+MODE+") — edges deferred, first node paint done");
  const tStart=performance.now();let it=0;const maxit=MAXIT[MODE]||200;
  // WALL-CLOCK WATCHDOG — independent of rAF; guarantees the overlay is removed by 5s
  watchdog=setTimeout(function(){ if(!finished){ tlog("WATCHDOG 5000ms fired — force-aborting stabilization"); partial=(MODE==="force"); finishStabilize("watchdog-5s",it,performance.now()-tStart,NaN); } },5000);
  tlog("stabilization started — budget="+BUDGET_MS+"ms maxit="+maxit+" itersPerFrame="+ITERS_PER_FRAME);
  simRAF=requestAnimationFrame(function frame(){
    if(finished)return;                  // rAF loop terminates once finished
    rafCount++;
    let mv=1;
    try{ for(let k=0;k<ITERS_PER_FRAME&&it<maxit;k++,it++) mv=STEP[MODE](); }
    catch(e){ tlog("EXIT: exception in STEP at it="+it+" — "+((e&&e.message)||e)); showError("layout step failed: "+((e&&e.stack)||e)); deterministicFallback("step threw"); return finishStabilize("exception",it,performance.now()-tStart,mv); }
    const sf=sanitize(); if(sf){ tlog("EXIT: fallback — "+sf+" non-finite coords during sim at it="+it); deterministicFallback("non-finite"); return finishStabilize("fallback-nonfinite",it,performance.now()-tStart,mv); }
    drawNodes();                         // DOM refresh once per ITERS_PER_FRAME iterations
    const elapsed=performance.now()-tStart;
    if(rafCount<=3||rafCount%15===0) tlog("frame "+rafCount+": it="+it+" avgMove="+mv.toExponential(2)+" elapsed="+elapsed.toFixed(0)+"ms");
    if((MODE==="force") ? (mv<STOP_MOVE) : (it>=maxit)){ tlog("budget check → CONVERGED (avgMove="+mv.toFixed(3)+")"); partial=false; return finishStabilize("converged",it,elapsed,mv); }
    if(it>=maxit){ tlog("budget check → MAX-ITERS ("+it+"/"+maxit+")"); partial=(MODE==="force"); return finishStabilize("max-iters",it,elapsed,mv); }
    if(elapsed>=BUDGET_MS){ tlog("budget check → TIME-BUDGET ("+elapsed.toFixed(0)+"ms ≥ "+BUDGET_MS+")"); partial=(MODE==="force"); return finishStabilize("time-budget",it,elapsed,mv); }
    simRAF=requestAnimationFrame(frame);
  });
}
function finishStabilize(reason,it,elapsed,mv){
  if(finished)return; finished=true; settling=false;      // idempotent — runs exactly once
  if(simRAF){cancelAnimationFrame(simRAF);simRAF=null;}
  if(watchdog){clearTimeout(watchdog);watchdog=null;}
  tlog("stabilize() EXIT path = "+reason+" | iters="+it+" elapsed="+(elapsed||0).toFixed(0)+"ms avgMove="+(fin(mv)?mv.toFixed(3):"n/a")+" rAFcount="+rafCount);
  try{
    gL.style.display="";                 // reveal edges — positioned ONCE here, not per-iter
    render();
    fitScreen(true);                     // one fit-to-screen after first usable layout
  }catch(e){ tlog("EXIT: render/finish threw — "+((e&&e.message)||e)); showError("finish/render failed: "+((e&&e.stack)||e)); }
  overlay(false);                         // <-- overlay removed here, unconditionally
  tlog("overlay removed · interaction enabled"+(partial?" (partial)":""));
  if(partial){overlay(true,"partially stabilized",false);setTimeout(()=>{if(finished)overlay(false);},2600);}
  tlog("stabilize() completed");
}

// =====================================================================
//  CAMERA  (smooth zoom / pan / fit / centre) — all finite-guarded
// =====================================================================
let camRAF=null;
function animateCam(TX,TY,S,ms){if(!(fin(TX)&&fin(TY)&&fin(S)))return;if(camRAF)cancelAnimationFrame(camRAF);
  if(!ms){tx=TX;ty=TY;scale=S;updateView();return;}
  const tx0=tx,ty0=ty,s0=scale,t0=performance.now();
  (function f(now){let k=clamp((now-t0)/ms,0,1);k=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
    tx=tx0+(TX-tx0)*k;ty=ty0+(TY-ty0)*k;scale=s0+(S-s0)*k;updateView();
    if(k<1)camRAF=requestAnimationFrame(f);})(t0);}
function fitScreen(animate){const V=[...visibleNodes()].map(id=>idx[id]).filter(n=>fin(n.x)&&fin(n.y));
  const P=V.length?V:D.nodes.filter(n=>fin(n.x)&&fin(n.y));if(!P.length){tx=0;ty=0;scale=1;updateView();return;}
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;P.forEach(n=>{x0=Math.min(x0,n.x-n.r);y0=Math.min(y0,n.y-n.r);x1=Math.max(x1,n.x+n.r);y1=Math.max(y1,n.y+n.r);});
  const pad=44,w=x1-x0||1,h=y1-y0||1,s=clamp(Math.min((VBW-2*pad)/w,(VBH-2*pad)/h),0.15,4);
  animateCam((VBW-s*(x0+x1))/2,(VBH-s*(y0+y1))/2,s,animate?480:0);}
function centreOn(n){if(!fin(n.x)||!fin(n.y))return;const s=clamp(Math.max(scale,1.6),.2,6);animateCam(CX-n.x*s,CY-n.y*s,s,500);}
function zoomBy(f){const w={x:(CX-tx)/scale,y:(CY-ty)/scale},s=clamp(scale*f,.2,6);animateCam(CX-w.x*s,CY-w.y*s,s,200);}

// =====================================================================
//  INTERACTION  (disabled while settling)
// =====================================================================
function toVB(ev){const r=svg.getBoundingClientRect();return {x:(ev.clientX-r.left)/r.width*VBW,y:(ev.clientY-r.top)/r.height*VBH};}
function toWorld(vb){return {x:(vb.x-tx)/scale,y:(vb.y-ty)/scale};}
let drag=null,pan=null,moved=0;
function startDrag(ev,n){if(settling)return;ev.stopPropagation();ev.preventDefault();
  const w=toWorld(toVB(ev));drag={n,ox:w.x-n.x,oy:w.y-n.y};moved=0;svg.classList.add("drag");n.fx=n.x;n.fy=n.y;}
svg.addEventListener("pointerdown",ev=>{if(drag||settling)return;pan={vb:toVB(ev)};moved=0;svg.classList.add("drag");});
svg.addEventListener("pointermove",ev=>{
  if(drag){const w=toWorld(toVB(ev));drag.n.x=w.x-drag.ox;drag.n.y=w.y-drag.oy;drag.n.fx=drag.n.x;drag.n.fy=drag.n.y;moved++;dragUpdate(drag.n);}
  else if(pan){const vb=toVB(ev);tx+=vb.x-pan.vb.x;ty+=vb.y-pan.vb.y;pan.vb=vb;moved++;updateView();}});
function endDrag(){
  if(drag){if(moved<3){sel=(sel===drag.n.id?null:drag.n.id);showInfo(sel?drag.n:null);render();}
    drag.n.fx=null;drag.n.fy=null;drag=null;}
  pan=null;svg.classList.remove("drag");}
svg.addEventListener("pointerup",endDrag);svg.addEventListener("pointerleave",endDrag);
svg.addEventListener("click",ev=>{if(ev.target===svg||ev.target===view){sel=null;showInfo(null);render();}});
svg.addEventListener("wheel",ev=>{if(settling)return;ev.preventDefault();const vb=toVB(ev),w=toWorld(vb),f=ev.deltaY<0?1.12:0.89;
  scale=clamp(scale*f,.2,6);tx=vb.x-w.x*scale;ty=vb.y-w.y*scale;updateView();},{passive:false});
svg.addEventListener("dblclick",ev=>{if(settling)return;ev.preventDefault();const w=toWorld(toVB(ev)),s=clamp(scale*1.7,.2,6);animateCam(CX-w.x*s,CY-w.y*s,s,260);});

// search: dim on input; ↵ locate + centre + highlight
const inp=document.getElementById("search");
function searchCentre(){q=inp.value.trim();if(!q){render();return;}
  const vis=visibleNodes(),ql=q.toLowerCase();
  let m=D.nodes.find(n=>vis.has(n.id)&&n.label.toLowerCase()===ql)||D.nodes.find(n=>vis.has(n.id)&&n.label.toLowerCase().includes(ql));
  if(m){sel=m.id;showInfo(m);centreOn(m);}render();}
inp.addEventListener("input",e=>{q=e.target.value;render();});
inp.addEventListener("keydown",e=>{if(e.key==="Enter")searchCentre();});

// controls
document.getElementById("mode").addEventListener("change",e=>{MODE=e.target.value;runLayout();});
document.getElementById("btnFit").onclick=()=>fitScreen(true);
document.getElementById("btnReset").onclick=()=>runLayout();
document.getElementById("btnClear").onclick=()=>resetAll();
document.getElementById("zin").onclick=()=>zoomBy(1.25);
document.getElementById("zout").onclick=()=>zoomBy(0.8);
document.getElementById("zfit").onclick=()=>fitScreen(true);

function showInfo(n){const box=document.getElementById("info");
  if(!n){box.style.display="none";return;}box.style.display="block";
  const ls=D.links.filter(l=>l.s===n.id||l.t===n.id);const byRel={};
  ls.forEach(l=>{const o=idx[l.s===n.id?l.t:l.s];if(!o)return;
    let lab=o.label;
    if(l.e==="transforms_to"&&l.bridge)lab=`${o.label} (via ${l.bridge})`;
    else if(l.reactant)lab=`${l.reactant}: ${o.label}`;
    (byRel[l.e]=byRel[l.e]||new Set()).add(lab);});
  box.innerHTML=`<h3 style="color:var(--${n.type})">${n.label}</h3><div class="k">${n.type}</div>
    ${n.reactants?`<div class="row"><span class="k">reactants (cycle ${n.cycle||""})</span> ${n.reactants}</div>`:""}
    ${n.carrier?`<div class="row"><span class="k">carrier gas</span> ${n.carrier}</div>`:""}
    ${n.series?`<div class="row"><span class="k">series</span> ${n.series}</div>`:""}
    ${n.canonical?`<div class="row"><span class="k">canonical basis</span> ${n.canonical}</div>`:""}
    ${n.molar_mass?`<div class="row"><span class="k">molar mass</span> ${n.molar_mass} g/mol</div>`:""}
    ${n.molecular_diameter?`<div class="row"><span class="k">molecular diameter</span> ${n.molecular_diameter} pm</div>`:""}
    ${n.central_atoms?`<div class="row"><span class="k">metal atoms / molecule</span> ${n.central_atoms}</div>`:""}
    ${n.material?`<div class="row"><span class="k">material</span> ${n.material}</div>`:""}
    ${n.relevance?`<div class="row"><span class="k">relevance</span> ${n.relevance}${n.ready===false?" · ⚠ quarantined":""}</div>`:""}
    ${n.poi?`<div class="row"><span class="k">measurand</span> ${n.poi}</div>`:""}
    ${n.branch?`<div class="row"><span class="k">family branch</span> ${n.branch}</div>`:""}
    ${n.predicts?`<div class="row"><span class="k">predicts</span> ${n.predicts}</div>`:""}
    ${n.equations?`<div class="row"><span class="k">equations</span> ${n.equations}</div>`:""}
    ${n.paper?`<div class="row"><span class="k">from paper</span> ${n.paper}</div>`:""}
    ${n.implemented_by?`<div class="row"><span class="k">implemented by</span> ${n.implemented_by}</div>`:""}
    ${n.base?`<div class="row"><span class="k">base</span> ${n.base}</div>`:""}
    <div class="row"><span class="k">links (${ls.length})</span></div>
    ${Object.entries(byRel).map(([e,s])=>`<div class="row"><span style="color:var(--e-${e},var(--ink2))">${e}</span> <span style="color:var(--ink3)">(${s.size})</span><div class="chips">${[...s].slice(0,10).map(x=>`<span class="ichip">${x}</span>`).join("")}${s.size>10?`<span class="ichip">+${s.size-10}</span>`:""}</div></div>`).join("")}`;
}

function resetAll(){selPaper.clear();selMat.clear();selRel.clear();q="";sel=null;inp.value="";
  document.querySelectorAll(".mspanel input").forEach(cb=>cb.checked=false);
  document.querySelectorAll("details.ms summary").forEach(su=>su.textContent=su.textContent.split(":")[0]+": all");
  showInfo(null);render();fitScreen(true);}
window.resetAll=resetAll;

// go
updateView();
runLayout();
tlog("boot() completed (stabilization runs asynchronously; watchdog armed for 5000ms)");
}
</script>
"""

if __name__ == "__main__":
    main()
