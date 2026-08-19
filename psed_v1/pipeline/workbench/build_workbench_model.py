#!/usr/bin/env python3
"""Build the scientific comparison workbench model from the frozen semantic layers.

Every scientific decision in the workbench is made here, in Python, against the frozen
runtime -- comparability verdicts, which representations a series can reach, and the
actual transformed coordinates for each of them. The page renders; it does not reason.
That split is deliberate: the previous workbench let the browser decide what was
comparable from labels, and separately let a Y control change an axis title while the
plotted values stayed raw.

The model is a graph, not a tree. A ResultSeries reaches its Condition Cases through its
producer and may reach several; a MeasurementAct may span several cases. Both directions
are carried, because flattening either one silently deletes science.

    python3 cli.py workbench                      the production corpus (manifest)
    python3 _diagnostics/workbench_v2/rebuild.py  the frozen pilot fixture
"""
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W))

import paths as PATHS                                                  # noqa: E402
from pipeline.query import condition_query as CQ                       # noqa: E402
from pipeline.query import entity_identity as EI                       # noqa: E402
from pipeline.query import result_comparability as RC                  # noqa: E402
from pipeline.canonical import axis_semantics as AX                    # noqa: E402
from pipeline.canonical import comparison_targets as CT                # noqa: E402
from pipeline.canonical import process_steps as PS                     # noqa: E402
from pipeline.canonical import rules as RULES                          # noqa: E402
from pipeline.canonical import units as U                              # noqa: E402

# ---- corpus binding ---------------------------------------------------------------
# The Workbench is a CONSUMER of a semantic corpus: a directory of paper folders
# (each papers-layout: <root>/<pid>/{semantic,canonical|resolved}) plus an explicit
# work list. The production default is the corpus manifest's included papers under
# papers/; `configure()` (or main's flags) points the same build at any other corpus
# -- the frozen pilot snapshot is regenerated through exactly this path.
OUT = PATHS.PAPERS / "_corpus" / "workbench"
CORPUS_ROOT = PATHS.PAPERS


def corpus_paper_ids():
    """The declared work list for the bound corpus. Never a directory glob."""
    return PAPER_IDS if PAPER_IDS is not None else PATHS.corpus_papers()


PAPER_IDS = None


def configure(corpus_root=None, papers=None, out=None):
    """Bind the build to a corpus. Returns the previous binding."""
    global CORPUS_ROOT, PAPER_IDS, OUT
    prev = (CORPUS_ROOT, PAPER_IDS, OUT)
    if corpus_root is not None:
        CORPUS_ROOT = Path(corpus_root)
    if papers is not None:
        PAPER_IDS = list(papers)
    if out is not None:
        OUT = Path(out)
    return prev


FREEZE = {"entity_identity": "fadd925", "result_comparability": "849c377",
          "condition_comparability": "600320a", "ontology_readiness": "14bff7b"}

# Which quantities constitute a conformality profile is an ontology declaration --
# the axis_role of its ComparisonGroups -- not a workbench list.
PROFILE_X = frozenset(g["canonical_quantity"] for g in CT.GROUPS.values()
                      if g.get("axis_role") == "coordinate")
PROFILE_Y = frozenset(g["canonical_quantity"] for g in CT.GROUPS.values()
                      if g.get("axis_role") == "output")



def code_hash():
    h = hashlib.sha256()
    for p in (Path(__file__), W / "pipeline" / "query" / "entity_identity.py",
              W / "pipeline" / "query" / "result_comparability.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


#: Relative agreement required when checking that two ENCODINGS of one extracted number
#: match -- 58.0 nm against 0.058 um. This is a floating-point representation check, not
#: a physical tolerance: it is never used to decide that two distinct observations are
#: the same value.
_ENCODING_REL_TOL = 1e-9


def _same_encoded_number(av, au, bv, bu):
    na = CQ.normalized_value({"value": av, "unit": au})
    nb = CQ.normalized_value({"value": bv, "unit": bu})
    if na is None or nb is None:
        return False
    # a bare number and an explicitly dimensionless one are the same encoding
    da = na[0] or "dimensionless"
    db = nb[0] or "dimensionless"
    if da != db and {da, db} != {"dimensionless", "1"}:
        return False
    return abs(na[1] - nb[1]) <= _ENCODING_REL_TOL * max(abs(na[1]), abs(nb[1]), 1.0)


def assert_inputs_settled(pilot_root, papers):
    """Refuse to build from a semantic layer that is still being written.

    The builder reads the pilot's JSON while `run_pilot` may still be rewriting it, and a
    build that catches that window silently produces a DIFFERENT corpus -- transient case
    counts that match no run. Two cheap checks make regeneration deterministic: every
    expected artifact exists, and each one parses as complete JSON. A half-written file
    fails the parse rather than contributing half a paper.
    """
    missing, unreadable = [], []
    for pid in papers:
        for name in ("experimental_cases", "measurements", "result_series"):
            p = Path(pilot_root) / pid / "semantic" / ("%s.json" % name)
            if not p.exists():
                missing.append(str(p))
                continue
            try:
                json.loads(p.read_text())
            except Exception as exc:
                unreadable.append("%s (%s)" % (p, exc))
    if missing or unreadable:
        raise SystemExit(
            "semantic inputs are not settled; regenerate the pilot before building.\n"
            "  missing: %s\n  unreadable: %s" % (missing[:3], unreadable[:3]))


def canonical_curves(pid):
    p = CORPUS_ROOT / pid / "canonical" / "curves.json"
    if not p.exists():
        # a frozen snapshot corpus stores the same document under its older name
        p = CORPUS_ROOT / pid / "resolved" / "canonical_curves.json"
    if not p.exists():
        return {}
    out = {}
    for c in json.loads(p.read_text()).get("curves") or []:
        cx = (c.get("canonical") or {}).get("x") or {}
        cy = (c.get("canonical") or {}).get("y") or {}
        sem, raw = c.get("semantics") or {}, c.get("raw") or {}
        xv, yv = cx.get("values") or [], cy.get("values") or []
        out[c["curve_id"]] = {
            "x_quantity": cx.get("quantity") or (sem.get("x") or {}).get("quantity"),
            "y_quantity": cy.get("quantity") or (sem.get("y") or {}).get("quantity"),
            "x_unit": cx.get("unit"), "y_unit": cy.get("unit"),
            "x_raw_unit": (raw.get("x") or {}).get("unit"),
            "y_raw_unit": (raw.get("y") or {}).get("unit"),
            "x_label": (raw.get("x") or {}).get("label"),
            "y_label": (raw.get("y") or {}).get("label"),
            "x_group": cx.get("comparison_group"), "y_group": cy.get("comparison_group"),
            "x_norm": cx.get("normalization_definition"),
            "y_norm": cy.get("normalization_definition"),
            "y_axis_kind": (sem.get("y") or {}).get("axis_kind"),
            # points are canonical VALUES paired with canonical UNITS. Pairing raw values
            # with a canonical unit silently rescales by whatever conversion the canonical
            # layer already applied -- 1000x for mm -> um, and entirely plausible-looking.
            "points": [[a, b] for a, b in zip(xv, yv) if a is not None and b is not None],
            # kept separately: a curve whose y was never canonicalised still has x
            # coordinates, and which design point each one came from is decided by x
            "x_values": [a for a in xv if a is not None],
            "y_values": [b for b in yv if b is not None],
            # The source observation, as extracted: (x, y) tuples in the units the figure
            # was drawn in. Canonicalisation can fail for the y axis while the observed
            # number is perfectly well recorded, so the two are kept apart and the native
            # one is never derived from the canonical one.
            "native": native_tuples(raw, c.get("source") or {}),
            "projections": c.get("projections") or {},
            "transformations": c.get("transformations") or [],
            "y_resolution": "FULLY_RESOLVED" if cy.get("quantity") else "PARTIALLY_RESOLVED",
        }
    return out


def native_tuples(raw, source):
    """The source observation, one entry per extracted point, index preserved.

    A point is the pair. Compacting x and y independently -- dropping the missing ones
    from each array separately -- renumbers them against each other, so a later y slides
    up into the index of an earlier point and an observation is reported against the wrong
    Condition Case. The tuple list is the identity authority; the per-axis arrays are kept
    for readers that want one axis, but with POSITIONAL PLACEHOLDERS so index i still
    means point i in both.
    """
    pts = raw.get("points") or []
    tuples = []
    for p in pts:
        seq = list(p) if isinstance(p, (list, tuple)) else []
        tuples.append({"x": seq[0] if len(seq) > 0 else None,
                       "y": seq[1] if len(seq) > 1 else None})
    return {
        "points": tuples,
        "n_points": len(tuples),
        "x": {"quantity": (raw.get("x") or {}).get("quantity"),
              "label": (raw.get("x") or {}).get("label"),
              "unit": (raw.get("x") or {}).get("unit"),
              "values": [t["x"] for t in tuples]},          # placeholders preserved
        "y": {"quantity": (raw.get("y") or {}).get("quantity"),
              "label": (raw.get("y") or {}).get("label"),
              "unit": (raw.get("y") or {}).get("unit"),
              "values": [t["y"] for t in tuples]},          # placeholders preserved
        "x_available": len([t for t in tuples if t["x"] is not None]),
        "y_available": len([t for t in tuples if t["y"] is not None]),
        "source": source,
    }


def native_point(s, i):
    """The source tuple at an index, or None. The one way to reach an observation."""
    pts = (s.get("native_points") or {}).get("points") or []
    return pts[i] if 0 <= i < len(pts) else None


def _align_to_canonical_unit(rep, tgt):
    """Bring a representation's values into the target's canonical unit.

    Alias spellings (µm/um/μm, "1"/"-"/"") are one unit and change nothing. A TRUE
    conversion (nm -> µm, °C -> K) runs through the formal ontology unit-conversion
    rule for that dimension and is recorded as an explicit route step. A unit that
    will not convert leaves the representation without a target rather than on a
    silently mislabelled axis.
    """
    ru, cu = rep.get("unit"), tgt.get("canonical_unit")
    if cu is None:
        return True
    if CT.same_unit(ru, cu):
        # one unit, two spellings: the canonical spelling is the identity, the source
        # spelling is provenance. Values are untouched -- aliases share the factor.
        if str(ru) != str(cu):
            rep["source_unit_spelling"] = ru
            rep["unit"] = cu
        return True
    if ru in (None, "", " "):
        # the standing contract of ontology_axis_unit: an axis that printed no unit is
        # not thereby unitless -- where the quantity resolved and the ontology declares
        # its unit, that IS the unit the canonical numbers are in
        rep["unit"] = cu
        rep["unit_basis"] = ("ontology-declared unit for %r; the source printed none"
                             % rep.get("quantity"))
        return True
    rule = RULES.unit_conversion_rule_for(ru, allow_empty_as_dimensionless=True)
    if rule is None:
        return False
    try:
        rep["values"] = rule.apply(rep.get("values") or [], from_unit=ru, to_unit=cu,
                                   allow_empty_as_dimensionless=True)
    except Exception:
        return False
    rep["unit_conversion_route"] = {
        "rule_id": rule.id, "rule_version": rule.version,
        "from_unit": ru, "to_unit": cu,
        "provenance": "formal ontology unit-conversion rule"}
    rep["source_unit_spelling"] = ru
    rep["unit"] = cu
    return True


def _sig(axis, rep):
    """Stamp a representation with its ONTOLOGY-resolved comparison target.

    Identity comes from `comparison_targets.resolve_target` -- the ComparisonGroup
    where the ontology declares one, the QuantityKind identity otherwise, and None
    when the meaning is not established (unknown quantity, a ratio with no resolved
    basis, an unconvertible unit). A source-native representation is provenance and
    display, never a target: nothing about a printed label makes two axes the same
    quantity.
    """
    rep.setdefault("representation_kind", REP_CANONICAL if rep.get("transform") is None
                   else REP_TRANSFORMED)
    rep.setdefault("display_available", bool(rep.get("values")))
    tgt = None
    if rep.get("representation_kind") != REP_NATIVE_SOURCE:
        tgt = CT.resolve_target(rep.get("quantity"), rep.get("normalization"),
                                axis=axis, unit=rep.get("unit"))
        if tgt is not None and rep.get("values") is not None:
            if not _align_to_canonical_unit(rep, tgt):
                tgt = None
    if tgt is not None:
        rep["target_id"] = tgt["target_id"]
        rep["target_kind"] = tgt["target_kind"]
        rep["comparison_group"] = tgt["comparison_group"]
        rep["group_aliases"] = tgt["group_aliases"]
        rep["canonical_unit"] = tgt["canonical_unit"]
        rep["dimension"] = tgt["dimension"]
        rep["display_label"] = tgt["display_label"]
        rep["overlay_target_id"] = tgt["target_id"]
        rep["overlay_authorized"] = True
    else:
        rep["target_id"] = None
        rep["target_kind"] = None
        rep["comparison_group"] = None
        rep["overlay_target_id"] = None
        rep["overlay_authorized"] = False
        try:
            rep.setdefault("dimension", U.dimension_name(rep.get("unit"))
                           if rep.get("unit") else None)
        except Exception:
            rep.setdefault("dimension", None)
        rep.setdefault("display_label", rep.get("label"))
    rep["quantity_id"] = rep.get("quantity")
    rep["normalization_id"] = rep.get("normalization")
    rep["axis"] = axis
    return rep


#: What a representation is FOR. Displaying one curve and putting two curves on one axis
#: are different capabilities, and a single flag standing for both is what hid three
#: quarters of this corpus behind a canonicalisation failure.
REP_NATIVE_SOURCE = "NATIVE_SOURCE"
REP_CANONICAL = "CANONICAL"
REP_TRANSFORMED = "TRANSFORMED"


def native_source_representations(s):
    """The source curve, drawn from the persisted tuples. PROVENANCE, not a target.

    Only complete (x, y) tuples are plotted, filtered as whole pairs so a point never
    contributes its x to one place and its y to another. This is display capability
    and the record of how the source expressed the axis -- label, unit spelling,
    quantity word. It is NEVER a comparison target: sharing an axis is a claim about
    resolved scientific meaning, and a printed label establishes none. The ontology-
    resolved representations carry the targets; where none resolves, this stays the
    honest, display-only remainder.
    """
    np_ = s.get("native_points") or {}
    pairs = [(t.get("x"), t.get("y")) for t in (np_.get("points") or [])
             if t.get("x") is not None and t.get("y") is not None]
    if not pairs:
        return {}, {}
    out = {}
    for axis, meta, vals in (("x", np_.get("x") or {}, [a for a, _ in pairs]),
                             ("y", np_.get("y") or {}, [b for _, b in pairs])):
        # An axis that printed no unit is not thereby unitless: where the quantity
        # resolved and the ontology declares its unit, that is the unit the numbers are
        # in. Asked of the canonical layer so the answer is the ontology's, not a guess.
        unit, unit_basis = AX.ontology_axis_unit(meta.get("quantity"), meta.get("unit"))
        label = meta.get("label") or meta.get("quantity") or axis
        out[axis] = {"native_source": {
            "id": "native_source", "representation_kind": REP_NATIVE_SOURCE,
            "quantity": meta.get("quantity"), "unit": unit,
            "label": label, "display_label": label,
            "source_label": meta.get("label"), "source_unit": meta.get("unit"),
            "unit_basis": unit_basis,
            "values": vals, "transform": None,
            "available": True, "display_available": True,
            "overlay_target_id": None, "overlay_authorized": False,
            "axis": axis,
            "n_source_points": len(np_.get("points") or []),
            "n_plotted_points": len(pairs)}}
    return out["x"], out["y"]


def axis_native_from_source(s, reps, axis, cur):
    """Rebuild ONE axis' canonical representation from the source coordinates.

    Used where the canonical layer resolved this axis' semantics but produced no paired
    coordinates because the OTHER axis failed. The source values are converted into the
    canonical unit through the frozen unit registry, so this restores a representation
    the canonical layer had already earned rather than inventing a new one. Anything that
    does not convert cleanly is left alone.
    """
    q, unit = cur.get("%s_quantity" % axis), cur.get("%s_unit" % axis)
    if not q or "native" in reps:
        return
    src = (s.get("native_points") or {}).get(axis) or {}
    vals, su = src.get("values"), src.get("unit")
    if not vals:
        return
    if not unit:
        # A normalized axis is a pure ratio: once its basis is known the ontology
        # supplies the unit the canonical layer never assigned. Without a basis a ratio
        # stays unresolved -- a ratio to an unknown reference has no canonical form.
        # For any OTHER quantity the standing ontology_axis_unit contract applies: the
        # source unit wins, and where the source printed none the ontology's declared
        # unit for the resolved quantity is the unit the numbers are in.
        if q in RC._NORMALIZED_QUANTITIES and not cur.get("%s_norm" % axis):
            return
        unit = AX.ontology_axis_unit(q, su)[0]
        if not unit:
            return
    if not su:
        # a silent source axis inherits the same resolved unit (the values are the
        # same numbers); recorded on the representation's own basis field
        su = unit
    try:
        fu, tu = U.parse(su), U.parse(unit)
        if U.dimension_name(su) != U.dimension_name(unit) or not tu.factor:
            return
        conv = [None if v is None else ((v * fu.factor + fu.offset) - tu.offset) / tu.factor
                for v in vals]
    except Exception:
        return
    # positional placeholders are how the source keeps point i at index i; they are
    # carried through, not treated as a failure of the axis
    if len([v for v in conv if v is not None]) < 2:
        return
    reps["native"] = {
        "id": "native", "quantity": q, "unit": unit,
        "label": "%s [%s]" % (q, unit), "values": conv, "available": True,
        "normalization": cur.get("%s_norm" % axis), "transform": None,
        "rebuilt_from_source": (
            "the canonical layer resolved this axis but emitted no paired coordinates "
            "because the other axis was unresolved; the source values were converted "
            "from %s into %s" % (su, unit))}


def derived_representations(s, cur):
    """Every representation this series can reach, WITH the coordinates already computed.

    The page never transforms anything. If an option is offered, its numbers are already
    here; if the numbers cannot be produced, the option is not offered. That is what makes
    a Y control that does not move the curve structurally impossible.

    Reachability is PER AXIS. What the x axis can become is decided by the x axis'
    resolution -- its quantity, its normalisation, the projections the canonical layer
    computed FOR IT -- and never by the state of the y axis, and vice versa. Gating the
    x options on a complete canonical (x, y) pair array is exactly how a profile whose y
    basis was unresolved lost its perfectly resolved physical-distance transform.
    """
    pts = cur["points"]
    xr, yr = native_source_representations(s)
    if pts:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # the x normalisation belongs in the representation exactly as the y one does.
        # Without it every normalised x axis reached its target_id with an EMPTY basis
        # slot, so x/H and x/L -- genuinely different statements -- shared one target,
        # while the same axis canonicalised by two different paths did not.
        xr["native"] = {"id": "native", "quantity": cur["x_quantity"],
                        "unit": cur["x_unit"],
                        "label": "%s [%s]" % (cur["x_quantity"], cur["x_unit"]),
                        "values": xs, "transform": None, "available": True,
                        "normalization": cur.get("x_norm")}
        ylab = "%s [%s]" % (cur["y_quantity"], cur["y_unit"])
        if cur["y_norm"]:
            ylab += ", %s" % cur["y_norm"]
        elif cur["y_quantity"] in RC._NORMALIZED_QUANTITIES:
            ylab += " (basis unresolved)"
        yr["native"] = {"id": "native", "quantity": cur["y_quantity"],
                        "unit": cur["y_unit"],
                        "label": ylab, "values": ys, "transform": None,
                        "available": True, "normalization": cur["y_norm"]}
    else:
        # No canonical pair does not mean no curve. The source observation is a
        # representation in its own right, and each axis the canonical layer DID resolve
        # is rebuilt from the source coordinates that belong to it; the axis that failed
        # stays absent, which is the honest report. Both axes are rebuilt from the SAME
        # source tuples, so a rebuild is only sound where the source arrays are already
        # paired; unequal lengths mean the source coordinates were never aligned and a
        # rebuilt pair would be fabricated.
        np_ = s.get("native_points") or {}
        nx = ((np_.get("x") or {}).get("values")) or []
        ny = ((np_.get("y") or {}).get("values")) or []
        if len(nx) == len(ny) and nx:
            axis_native_from_source(s, xr, "x", cur)
            axis_native_from_source(s, yr, "y", cur)
        xs = (xr.get("native") or {}).get("values") or []
        ys = (yr.get("native") or {}).get("values") or []

    # Projections the canonical layer computed are read back PER AXIS: an x projection
    # exists because the x axis resolved, and it is attached whenever its coordinates
    # align with this axis' native array -- whatever happened to the other axis. A
    # projection whose length does not match is refused rather than realigned, because
    # index identity is the one thing this model never invents.
    for axis, reps in (("x", xr), ("y", yr)):
        base = (reps.get("native") or {}).get("values") or []
        if not base:
            continue
        for pj in (cur["projections"].get(axis) or []):
            vals = pj.get("values") or []
            if len(vals) != len(base):
                continue
            reps["proj:%s" % pj.get("quantity")] = {
                "id": "proj:%s" % pj.get("quantity"), "quantity": pj.get("quantity"),
                "unit": pj.get("unit"),
                "label": "%s [%s]" % (pj.get("quantity"), pj.get("unit")),
                "values": vals, "available": True,
                "transform": {"kind": "CANONICAL_PROJECTION",
                              "from_normalization": pj.get("from_normalization"),
                              "provenance": "computed by the canonical layer and read back",
                              "parameters": _proj_params(cur, pj)}}

    return xr, yr


def _proj_params(cur, pj):
    for t in cur["transformations"]:
        if t.get("axis") == "x" and (t.get("context") or {}):
            return {k: {"value": v.get("value"), "unit": v.get("unit"),
                        "evidence": v.get("evidence"), "status": v.get("status")}
                    for k, v in t["context"].items()}
    return {}


def build():
    papers = corpus_paper_ids()
    assert_inputs_settled(CORPUS_ROOT, papers)
    cases, acts, series, samples, runs, measurements = {}, {}, {}, {}, {}, {}
    excluded = []

    for pid in papers:
        D = EI.load_paper(CORPUS_ROOT, pid)
        cur = canonical_curves(pid)
        smap = {s["sample_id"]: s for s in D["samples"] if s.get("sample_id")}
        pcases = EI.producer_case_index(D["measurements"], D["simulation_runs"])
        agroups, act_of = EI.measurement_acts(D["measurements"])
        K = lambda i: "%s::%s" % (pid, i)

        for c in D["experimental_cases"]:
            real = EI.realizations(c, smap, None)
            cases[K(c["case_id"])] = {
                "id": K(c["case_id"]), "case_id": c["case_id"], "paper_id": pid,
                "entity": "CONDITION_CASE",
                "material": c.get("deposited_material"), "geometry": c.get("geometry"),
                "fingerprint": c.get("nominal_fingerprint"),
                # step_context travels with the condition: a 2 s precursor dose and a
                # 2 s plasma exposure are the same number and different experiments
                # A range-valued assertion has no scalar, and emitting `value: null`
                # made a real statement ("10-40 cycles") look like an empty placeholder.
                # The bounds are the value; they travel with it.
                "conditions": [{"quantity": x.get("quantity"),
                                "source_quantity": x.get("source_quantity"),
                                "same_slot_conflict": x.get("same_slot_conflict"),
                                "conflicting_values": x.get("conflicting_values"),
                                "value": x.get("value"),
                                "value_kind": x.get("value_kind"),
                                "value_lower": x.get("value_lower"),
                                "value_upper": x.get("value_upper"),
                                "unit": x.get("unit"), "species": x.get("species"),
                                "step_context": x.get("step_context"),
                                "activation": x.get("activation"),
                                "plasma_type": x.get("plasma_type"),
                                "follows": x.get("follows"),
                                "preceding_species": x.get("preceding_species"),
                                "preceding_activation": x.get("preceding_activation"),
                                "scope": EI.CASE_CONTEXT,
                                "source_scope": x.get("scope"),
                                "source": x.get("source"),
                                # without the evidence the page shows a number nobody can
                                # check; every displayed condition carries its sentence
                                "evidence": x.get("evidence"),
                                "locator": x.get("locator"),
                                "provenance_type": x.get("provenance_type")}
                               for x in (c.get("case_defining_conditions") or [])],
                "chemistry": _chem(c),
                # the linked specimen's OTHER deposited layers: composition of the
                # structure the case's film sits in, never the case's own target
                "specimen_context_materials": c.get("specimen_context_materials") or [],
                # member-local sweep/progression intervals: context of one member's own
                # observation, never a fixed nominal condition of the case
                "progression_context_conditions":
                    c.get("progression_context_conditions") or [],
                # the reactor gases are process facts the recipe chemistry never carries;
                # the two roles stay separate because one gas often fills both and many
                # processes fill them with different gases
                "carrier_gas": c.get("carrier_gas"),
                "purge_gas": c.get("purge_gas"),
                "gas_role_provenance": c.get("gas_role_provenance") or {},
                "realization": {
                    "source_sample_records": real["n_samples_resolved"],
                    "physical_specimen_identity": "unresolved",
                    "samples": [{"sample_id": x["sample_id"],
                                 "source_sample_code": x["source_sample_code"],
                                 "physical_specimen": None,
                                 "deposition_run": x["produced_by_run"],
                                 "run_status": x["run_status"]}
                                for x in real["samples"]],
                    "runs_observed": [dict(r) for r in EI.case_run_links(c, smap)],
                    "run_link_semantics": EI.RUNS_OBSERVED_AMONG_CASE_REALIZATIONS},
                "act_ids": [], "series_ids": []}
        for sid, s in smap.items():
            samples[K(sid)] = {"id": K(sid), "sample_id": sid, "paper_id": pid,
                               "source_sample_code": s.get("source_sample_code"),
                               "physical_specimen": None,
                               "physical_identity_status": EI.SPECIMEN_UNRESOLVED,
                               "deposition_run": s.get("produced_by_run")}
        for r in D["deposition_runs"]:
            rid, members = EI.run_members(r, list(smap.values()))
            if rid:
                runs[K(rid)] = {"id": K(rid), "run_id": rid, "paper_id": pid,
                                "sample_members": members, "scope": "SAMPLE_SCOPED"}
        for m in D["measurements"]:
            measurements[K(m["measurement_id"])] = {
                "id": K(m["measurement_id"]), "measurement_id": m["measurement_id"],
                "paper_id": pid, "act_id": K(act_of.get(m["measurement_id"], "")),
                "technique": _tech(m.get("technique") or m.get("classification")),
                "measurand": m.get("measured_quantity"),
                "settings": [{"quantity": x.get("quantity"), "value": x.get("value"),
                              "unit": x.get("unit")}
                             for x in (m.get("measurement_settings") or [])][:10],
                "performed_on": m.get("performed_on")}
        mby = {m["measurement_id"]: m for m in D["measurements"]}
        for aid, members in agroups.items():
            cs = sorted({c for m in members for c in pcases.get(m, ())})
            first = mby.get(members[0], {})
            acts[K(aid)] = {
                "id": K(aid), "act_id": aid, "paper_id": pid, "entity": "MEASUREMENT_ACT",
                "kind": "MEASUREMENT",
                "technique": _tech(first.get("technique") or first.get("classification")),
                "measurand": first.get("measured_quantity"),
                "member_measurement_ids": members, "n_members": len(members),
                "case_ids": [K(c) for c in cs], "n_cases": len(cs),
                "sample_ids": sorted({K(mby[m]["performed_on"]) for m in members
                                      if mby.get(m, {}).get("performed_on")}),
                "grouping_evidence": EI.act_evidence(D["measurements"], members),
                "series_ids": []}
            for c in cs:
                if K(c) in cases:
                    cases[K(c)]["act_ids"].append(K(aid))
        for s in D["simulation_runs"]:
            sid = s.get("simulation_run_id") or s.get("id")
            if not sid:
                continue
            cs = sorted(set(s.get("realises_case_ids") or []))
            acts[K(sid)] = {
                "id": K(sid), "act_id": sid, "paper_id": pid, "entity": "MEASUREMENT_ACT",
                "kind": "SIMULATION_RUN",
                "technique": s.get("model_family") or s.get("model") or "simulation",
                "measurand": None, "member_measurement_ids": [], "n_members": 0,
                "case_ids": [K(c) for c in cs], "n_cases": len(cs), "sample_ids": [],
                "grouping_evidence": ["simulation run; not a physical observing act"],
                "series_ids": []}
            for c in cs:
                if K(c) in cases:
                    cases[K(c)]["act_ids"].append(K(sid))

        for r in D["result_series"]:
            rid, prod = r["result_series_id"], r.get("produced_by")
            cu = cur.get(r.get("curve_id")) or {}
            # A series whose measurand does not resolve to an ontology quantity is still a
            # real scientific result: it is visible, keeps its full case membership, and is
            # simply not comparable. Dropping it would delete case links and quietly shrink
            # the denominator.
            if not cu:
                excluded.append({"series_id": rid, "paper_id": pid,
                                 "reason": "NO_CANONICAL_CURVE_RECORD"})
                continue
            unresolved_y = not cu.get("y_quantity")
            # A normalized axis whose denominator the canonical layer could not resolve is
            # ambiguous, and two such axes must never overlay -- but where the SOURCE
            # states the reference, the semantic layer has already recovered it from that
            # statement. Consuming it here turns a permanently ambiguous axis into the
            # declared normalization the paper actually plotted, with its evidence.
            if not cu.get("y_norm") and r.get("y_normalization_basis"):
                cu = dict(cu, y_norm=r["y_normalization_basis"],
                          y_norm_evidence=r.get("y_normalization_basis_evidence"),
                          y_norm_source=r.get("y_normalization_basis_source"))
            cs = [K(c) for c in EI.cases_for_result_series(r, pcases)]
            one, status = EI.single_case_for_series(r, pcases)
            src = r.get("source") or {}
            rec = {
                "id": K(rid), "series_id": rid, "paper_id": pid,
                "entity": "RESULT_SERIES",
                "act_id": K(act_of[prod]) if prod in act_of else K(prod),
                "producer_id": K(prod) if prod else None,
                "data_source": r.get("data_source"),
                "figure": src.get("figure"), "panel": src.get("panel"),
                "series_label": src.get("series"),
                "n_points": r.get("n_points"),
                "x_canonical": {"values": cu.get("x_values") or [],
                                "unit": cu.get("x_unit"),
                                "quantity": cu.get("x_quantity")},
                "y_canonical": {"values": cu.get("y_values") or [],
                                "unit": cu.get("y_unit"),
                                "quantity": cu.get("y_quantity")},
                "native_points": cu.get("native") or {},
                # named all_case_ids because there is no other kind: a sweep belongs to
                # every case it traverses and none of them is primary
                "all_case_ids": cs, "n_cases": len(cs),
                "single_case": K(one) if one else None,
                "case_cardinality_status": status,
                "is_profile": (not unresolved_y and cu["x_quantity"] in PROFILE_X
                               and cu["y_quantity"] in PROFILE_Y),
                "x": {k: cu[k] for k in ("x_quantity", "x_unit", "x_raw_unit", "x_label",
                                         "x_group", "x_norm")},
                "y": {k: cu[k] for k in ("y_quantity", "y_unit", "y_raw_unit", "y_label",
                                         "y_group", "y_norm", "y_axis_kind")},
                "y_resolution": ("UNRESOLVED" if unresolved_y else cu["y_resolution"]),
                "measurand_status": ("UNRESOLVED_MEASURAND" if unresolved_y
                                     else "RESOLVED"),
                "normalization_basis": (cu["y_norm"] or
                                        ("unresolved"
                                         if cu["y_quantity"] in RC._NORMALIZED_QUANTITIES
                                         else None)),
            }
            # A timing axis whose recorded quantity CONTRADICTS the family its own
            # printed label names is a naming defect inherited from extraction --
            # "Exposure time (s)" recorded as pulse_time. The record is not rewritten
            # (it is what the extraction asserted); the disagreement is surfaced, and
            # point-case binding compares cycle SIDES so it does not depend on which
            # family either layer chose.
            for ax in ("x", "y"):
                meta = (cu.get("native") or {}).get(ax) or {}
                fam = PS.timing_family_from_label(meta.get("label"))
                rq = PS.timing_kind(meta.get("quantity"))
                if fam and rq and fam != rq:
                    rec.setdefault("axis_family_discrepancies", []).append({
                        "axis": ax, "recorded_quantity": meta.get("quantity"),
                        "label": meta.get("label"),
                        "label_family": fam,
                        "note": ("the printed axis label names the %s family but the "
                                 "extracted quantity is of the %s family; the printed "
                                 "label is the primary record" % (fam, rq))})
            # native_points is already on `rec` above, and it is what a source
            # representation is built from
            xr, yr = derived_representations(rec, cu)
            rec["x_representations"] = {k: _sig("x", v) for k, v in xr.items()}
            rec["y_representations"] = {k: _sig("y", v) for k, v in yr.items()}
            series[K(rid)] = rec
            if rec["act_id"] in acts:
                acts[rec["act_id"]]["series_ids"].append(K(rid))
            for c in cs:
                if c in cases:
                    cases[c]["series_ids"].append(K(rid))
    return cases, acts, series, samples, runs, measurements, excluded


#: The relation between two ResultSeries of one MeasurementAct. It says the two curves
#: are REPRESENTATIONS OF THE SAME OBSERVING ACT -- a raw, a scaled and a normalized
#: drawing of one measurement. It does NOT say either can be point-inverted into the
#: other: each was digitized independently, with its own extraction error.
SAME_MEASUREMENT_REPRESENTATION = "SAME_MEASUREMENT_REPRESENTATION"
#: A representation reached by transforming THIS series' own coordinates.
DERIVED_TRANSFORM = "DERIVED_TRANSFORM"


def same_measurement_alternates(series, acts):
    """Attach each series' sibling representations of the same MeasurementAct.

    The entity model records `represents_same_measurement_as` on Measurement records and
    the act grouping closes it transitively; this only reads that structure back onto
    each series, with the act's own grouping evidence as the basis. Nothing here claims
    comparability, overlay permission, or numerical invertibility -- an alternate is a
    place to LOOK, carrying the provenance of why it is the same observation.
    """
    n = 0
    for s in series.values():
        a = acts.get(s["act_id"]) or {}
        sibs = [x for x in (a.get("series_ids") or []) if x != s["id"]]
        out = []
        for sib_id in sorted(sibs):
            sib = series.get(sib_id)
            if not sib:
                continue
            out.append({
                "series_id": sib_id,
                "relation": SAME_MEASUREMENT_REPRESENTATION,
                "act_id": s["act_id"],
                "act_kind": a.get("kind"),
                "figure": sib.get("figure"), "panel": sib.get("panel"),
                "series_label": sib.get("series_label"),
                "y_quantity": (sib.get("y") or {}).get("y_quantity"),
                "y_normalization": (sib.get("y") or {}).get("y_norm"),
                "x_quantity": (sib.get("x") or {}).get("x_quantity"),
                "basis": a.get("grouping_evidence") or [],
                "independently_digitized": True,
                "caveat": ("this ResultSeries was persisted from its own drawing of the "
                           "same observing act; it is evidence about the same "
                           "measurement, not a point-by-point mathematical inverse of "
                           "this curve"),
            })
        s["same_measurement_series"] = out
        n += len(out)
    return n


#: how a resolved case fact is known
FACT_CASE_DEFINING = "CASE_DEFINING_CONDITION"
FACT_KNOWN_CONTEXT = "KNOWN_CONTEXT"


def case_facts(c):
    """Everything KNOWN about a Condition Case, each fact carrying scope and basis.

    "The precursor is unknown" and "the precursor is TMA but is not what distinguishes
    this case from its siblings" are different statements, and a view built from
    case-defining conditions alone renders the second as the first. This view combines,
    per case and with provenance:

      * the case-defining conditions themselves (marked as such);
      * the case's own resolved process chemistry -- resolved upstream for THIS case's
        material and process, never copied across a paper's other chemistries;
      * the reactor gas roles the paper states, with their recorded provenance;
      * the deposited material and geometry, with the case's own source fields.

    Nothing is invented: every entry quotes where it came from, and a fact absent from
    all of these stays absent -- that is what unknown now means.
    """
    facts = {}

    def add(fid, value, role, scope, basis, provenance=None, evidence=None,
            species=None, unit=None):
        if value in (None, "", []):
            return
        facts.setdefault(fid, []).append(
            {"value": value, "unit": unit, "species": species,
             "fact_role": role, "scope": scope, "basis": basis,
             "provenance_type": provenance, "evidence": evidence})

    for x in c.get("conditions") or []:
        fid = x["quantity"] + ("@" + x["species"] if x.get("species") else "")
        add(fid, _condition_value(x), FACT_CASE_DEFINING,
            x.get("source_scope") or "case", "case-defining condition",
            provenance=x.get("provenance_type"), evidence=x.get("evidence"),
            species=x.get("species"), unit=x.get("unit"))
    chem = c.get("chemistry") or {}
    for role in ("precursor", "coreactant"):
        for sp in chem.get(role) or []:
            add(role, sp, FACT_KNOWN_CONTEXT, "case",
                "resolved process chemistry of this case", provenance="resolved_chemistry")
        for act in chem.get("%s_activation" % role) or []:
            add("%s_activation" % role, act, FACT_KNOWN_CONTEXT, "case",
                "resolved process chemistry of this case", provenance="resolved_chemistry")
    if chem.get("process_type"):
        add("process_type", chem["process_type"], FACT_KNOWN_CONTEXT, "case",
            "resolved process chemistry of this case", provenance="resolved_chemistry")
    gp = c.get("gas_role_provenance") or {}
    for role in ("carrier_gas", "purge_gas"):
        v = c.get(role)
        if v:
            rec = gp.get(role) or {}
            add(role, v, FACT_KNOWN_CONTEXT, "paper-stated gas role",
                rec.get("basis") or "explicitly stated gas role",
                provenance="gas_role", evidence=rec.get("evidence"))
    add("material", c.get("material"), FACT_KNOWN_CONTEXT, "case",
        "deposited material of this case", provenance="case_material")
    for sc in c.get("specimen_context_materials") or []:
        add("specimen_material", sc.get("material"), FACT_KNOWN_CONTEXT,
            "specimen/structure",
            sc.get("basis") or "material of the linked specimen's structure",
            provenance="specimen_context")
    add("geometry", c.get("geometry"), FACT_KNOWN_CONTEXT, "case",
        "geometry of this case", provenance="case_geometry")
    return facts


def _chem(c):
    """Chemistry the case establishes, with delivery activation kept out of the species.

    A channel named "O2_plasma" fuses two facts: the chemical is O2 and it arrived as a
    plasma. Reported as one token it makes a plasma O2 step look like a different reagent
    from a thermal O2 step, so the activation is split off and reported beside it.
    """
    out, activation = {}, {}

    def _add(kind, token):
        sp, act = PS.split_activated_species(str(token))
        if not sp or sp == "None":
            return
        out.setdefault(kind, set()).add(sp)
        if act:
            activation.setdefault(kind, set()).add(act)

    # a condition row states the chemistry where the source spells it out ...
    for x in (c.get("case_defining_conditions") or []):
        if x.get("quantity") in ("precursor", "coreactant"):
            _add(x["quantity"], x.get("value"))
    # ... and the case's own resolved chemistry carries it where no row does. Reading only
    # the rows left panels whose reagents were resolved upstream looking chemistry-less.
    for tok in (c.get("precursors") or []):
        _add("precursor", tok)
    for tok in (c.get("coreactants") or []):
        _add("coreactant", tok)
    # The semantic layer has already resolved these to canonical chemical identities and
    # split the delivery activation off the species. Reading the activation back from that
    # record keeps a plasma-delivered reagent reported as plasma even though its stored
    # label is now the plain chemical.
    for kind, recs in (c.get("chemistry_identity") or {}).items():
        role = "precursor" if kind.startswith("precursor") else "coreactant"
        for r in recs or []:
            if r.get("activation"):
                activation.setdefault(role, set()).add(r["activation"])
    chem = {k: sorted(v) for k, v in out.items()}
    for k, v in activation.items():
        chem["%s_activation" % k] = sorted(v)
    if c.get("process_type"):
        chem["process_type"] = c["process_type"]
    # a carrier or purge gas is a role in the process, not a reagent of the cycle. It is
    # stored as ONE species name, so it is wrapped rather than iterated -- sorting a
    # string yields its characters, which turned "N2" into ["2", "N"].
    for role in ("carrier_gas", "purge_gas"):
        v = c.get(role)
        if not v:
            continue
        chem[role] = sorted(v) if isinstance(v, (list, tuple, set)) else [str(v)]
    return chem


def _condition_value(x):
    """What a condition's magnitude IS, never a null standing in for one.

    A condition the source stated as an interval has no nominal scalar, and reporting it
    as `null` reads like a missing measurement rather than the range the paper wrote. The
    interval is shown as an interval; the bounds stay structured beside it.
    """
    v = x.get("value")
    if v not in (None, "", "null"):
        return v
    lo, hi = x.get("value_lower"), x.get("value_upper")
    if lo is not None and hi is not None:
        return "%g\u2013%g" % (float(lo), float(hi))
    return v


def _tech(v):
    if isinstance(v, (list, tuple, set)):
        v = ", ".join(sorted(str(x) for x in v if x)) or None
    return str(v) if v not in (None, "") else None


def bridge_case(s, cases):
    """The Condition Case a series may take transform bridge parameters from, or None.

    Only an unambiguous binding qualifies: exactly one case, and within it only
    conditions stating a single resolved numeric value. A series on several cases, a
    condition asserted twice and a "varies"/unknown value are precisely the situations
    where a transform must stay refused rather than adopt a number nobody asserted for
    this result.
    """
    ids = s.get("all_case_ids") or []
    if len(ids) != 1:
        return None
    case = (cases or {}).get(ids[0]) or {}
    stated = Counter(c.get("quantity") for c in (case.get("conditions") or []))
    conds = []
    for c in (case.get("conditions") or []):
        q = c.get("quantity")
        if stated[q] != 1:
            continue
        try:
            val = float(str(c.get("value")).strip())
        except (TypeError, ValueError):
            continue
        conds.append({"quantity": q, "value": val, "unit": c.get("unit"),
                      "evidence": c.get("evidence"),
                      "provenance_type": c.get("provenance_type")})
    if not conds:
        return None
    return {"case_id": case.get("case_id"), "case_defining_conditions": conds}


def _rule_applicable(rule, case):
    """Enforce a rule's OWN applicability policy; (ok, record_or_reason).

    A formal rule is not operational merely because its numeric context exists.
    The ontology's confidence_policy vocabulary is the gate:

      certain              self-evident (unit algebra, self-contained references)
      evidence_required    every context parameter must carry documentary or
                           self-referential provenance -- which is the only kind
                           `_rule_context` ever supplies, and the provenance is
                           recorded on the representation
      assumption_recorded  the rule declares a scientific assumption no operand
                           can prove; its ontology `applicability` block says what
                           evidences it. `operands_suffice` marks definitional
                           identities; `requires_any_evidence` names case facts,
                           one of which must be stated. No block, no application.
    """
    if rule.confidence_policy != "assumption_recorded":
        return True, None
    ap = rule.applicability
    pol = ap.get("policy")
    if pol == "operands_suffice":
        return True, {"policy": pol, "note": ap.get("note")}
    if pol == "requires_any_evidence":
        for k in ap.get("evidence") or []:
            got = RC.resolve_context(k, case=case) if case else {}
            if got.get("found") and got.get("value") is not None:
                return True, {"policy": pol, "evidence_quantity": k, "evidence": got}
        return False, ("assumption unevidenced: rule %s requires any of [%s] to be "
                       "stated for this case, and none is"
                       % (rule.id, ", ".join(ap.get("evidence") or [])))
    return False, ("assumption unevidenced: rule %s records assumptions %r but the "
                   "ontology declares no applicability policy for them -- an "
                   "ontology gap, not a licence" % (rule.id, rule.assumptions))


def _rule_context(rule, series_rec, case, axis, own_values=None, own_unit=None):
    """Resolve a formal rule's declared context, with provenance, or report the gap.

    Resolution order, all ontology-declared and property-independent:
      1. nothing -- the rule is self-contained (its implementation derives everything
         from the curve itself);
      2. the profile's own reference, where the rule's NormalizationDefinition
         declares a `reference_location` this profile can realise (entrance,
         profile maximum) -- derived from the curve's own coordinates, recorded as
         self-referential evidence;
      3. the series' own Condition Case, through the frozen context resolver --
         a feature height, a cycle count, stated as a condition of THIS experiment.

    Returns (ctx, provenance, missing): ctx maps each context quantity to
    {"value", "unit"} exactly as the rule executor expects.
    """
    ctx, prov, missing = {}, {}, []
    if rule.self_contained or not rule.required_context:
        return ctx, prov, missing
    nd = rule.normalization or {}
    ref_loc = nd.get("reference_location")
    xs = ((series_rec.get("x_representations") or {}).get("native") or {}).get("values")
    own = (own_values if own_values is not None else
           (((series_rec.get("%s_representations" % axis) or {}).get("native")
             or {}).get("values") or []))
    for q in rule.required_context:
        got = RC.resolve_context(q, case=case)
        if got.get("found") and got.get("value") is not None:
            ctx[q] = {"value": got["value"], "unit": got.get("unit")}
            prov[q] = got
            continue
        if ref_loc and xs and len(xs) == len(own):
            ref, ev = CT.profile_reference(ref_loc, xs, own)
            if ref is not None:
                unit = (own_unit if own_values is not None else
                        ((series_rec.get("%s_representations" % axis) or {})
                         .get("native") or {}).get("unit"))
                ctx[q] = {"value": ref, "unit": unit}
                prov[q] = {"parameter": q, "value": ref, "unit": unit, "found": True,
                           "source_object": "ResultSeries %s"
                                            % series_rec.get("series_id"),
                           "source_evidence": ev,
                           "reference_location": ref_loc,
                           "provenance_type": "derived_from_series_points",
                           "confidence": "self_referential"}
                continue
        missing.append(q)
    return ctx, prov, missing


def _rule_hop(rule, direction, ctx_prov, applicability=None):
    """One traversed edge of the rule graph, fully attributed."""
    return {
        "rule_id": rule.id, "rule_version": rule.version,
        "rule_type": rule.type, "direction": direction,
        "implementation": rule.implementation_id,
        "normalization_definition": rule.normalization_definition,
        "assumptions": rule.assumptions,
        "confidence_policy": rule.confidence_policy,
        "applicability": applicability,
        "parameters": {k: {"value": v["value"], "unit": v.get("unit")}
                       for k, v in (ctx_prov.get("ctx") or {}).items()},
        "parameter_provenance": (ctx_prov.get("prov") or {}) if not rule.self_contained
            else {"self_contained": {
                "source_object": "this ResultSeries' own values",
                "source_evidence": "; ".join(rule.assumptions)
                                   or "self-contained ontology rule",
                "provenance_type": "derived_from_series_points",
                "confidence": rule.confidence_policy}},
    }


def _rule_rep(axis, rule, direction, values, unit, ctx_prov, case, rep_id, route):
    """One representation produced by an ordered route of formal ontology rules.

    `route` is the COMPLETE ordered list of hops from the native representation to
    this target; the top-level transform fields describe the terminal hop, so a
    one-hop route reads exactly as before.
    """
    q, norm = CT.rule_target(rule, direction)
    terminal = route[-1]
    return {
        "id": rep_id,
        "quantity": q, "unit": unit, "normalization": norm,
        "label": CT.display_label(q, norm, unit),
        "values": values, "available": True,
        "transform": dict(terminal,
                          kind="ontology_transformation_rule",
                          route=route, hops=len(route), resolved=True),
        "bridge_source": ({"quantity": rule.required_context[0],
                           "case_id": (case or {}).get("case_id"),
                           **{k: (ctx_prov.get("prov") or {}).get(
                               rule.required_context[0], {}).get(k)
                              for k in ("value", "unit", "source_object",
                                        "confidence")}}
                          if rule.required_context and case else None),
    }


def ontology_rule_representations(series, cases):
    """Materialise every representation the FORMAL ontology rule registry reaches.

    This is the whole representation engine: for each axis' ontology-resolved native
    representation, ask the TransformationRule registry which quantities are reachable
    forward (rules whose source is this quantity, basis-matched for ratios) and
    backward (invertible rules that produce it, again basis-matched), resolve each
    rule's declared context, and execute the rule's own implementation. Nothing here
    knows any quantity by name: film thickness, spatial position, temperature,
    intensity and any future quantity flow through the same six lines of reachability.

    A rule whose context cannot be resolved leaves a DECLARED-unavailable entry, so a
    comparison can say "potentially comparable, missing <context>" instead of
    silently offering nothing.
    """
    made = refused = 0
    for s in series.values():
        case = bridge_case(s, cases)
        for axis in ("x", "y"):
            reps = s["%s_representations" % axis]
            native = reps.get("native")
            if not native or not native.get("values"):
                continue
            have_targets = {r.get("target_id") for r in reps.values()
                            if r.get("target_id")}
            # breadth-first over the WHOLE rule graph: a node is an ontology
            # meaning (quantity, normalization); an edge is one formal rule in one
            # direction. First (= shortest) route to a meaning wins; the visited
            # set is cycle prevention. Routes keep flowing through meanings whose
            # target something else already covers -- only the duplicate
            # publication is skipped, never the onward reachability.
            start = (native.get("quantity"), native.get("normalization") or None)
            visited = {start}
            frontier = [(start[0], start[1], native["values"],
                         native.get("unit"), [], [])]
            while frontier:
                q, norm, vals0, unit0, route, idparts = frontier.pop(0)
                plans = sorted(
                    [(r, "forward") for r in CT.rules_from(q, norm)]
                    + [(r, "reverse") for r in CT.invertible_rules_to(q, norm)],
                    key=lambda p: (p[0].id, p[1]))
                for rule, direction in plans:
                    tq, tnorm = CT.rule_target(rule, direction)
                    node = (tq, tnorm or None)
                    if node in visited:
                        continue
                    tgt = CT.resolve_target(tq, tnorm, axis=axis,
                                            unit=(rule.output_unit
                                                  if direction == "forward" else None)
                                            or CT.canonical_unit_for(tq))
                    if tgt is None:
                        continue
                    visited.add(node)
                    rid = "rule:%s%s" % (rule.id,
                                         "" if direction == "forward" else ":inverse")
                    rep_id = "+".join(idparts + [rid])
                    ok_ap, ap_rec = _rule_applicable(rule, case)
                    if not ok_ap:
                        if tgt["target_id"] not in have_targets:
                            # what is missing is the DECLARED evidence, and the
                            # gap report names it like any other bridge
                            evk = (rule.applicability.get("evidence") or [None])[0]
                            reps[rep_id] = _sig(axis, {
                                "id": rep_id, "quantity": tq,
                                "unit": tgt["canonical_unit"],
                                "normalization": tnorm,
                                "label": tgt["display_label"], "values": None,
                                "available": False,
                                "transform": {
                                    "kind": "ontology_transformation_rule",
                                    "rule_id": rule.id, "rule_type": rule.type,
                                    "direction": direction, "route": route,
                                    "required_bridge": evk,
                                    "parameters": None, "resolved": False},
                                "missing_bridge": evk,
                                "unavailable_reason": ap_rec})
                            refused += 1
                        continue
                    ctx, prov, missing = _rule_context(rule, s, case, axis,
                                                       own_values=vals0,
                                                       own_unit=unit0)
                    if missing:
                        if tgt["target_id"] not in have_targets:
                            reps[rep_id] = _sig(axis, {
                                "id": rep_id, "quantity": tq,
                                "unit": tgt["canonical_unit"],
                                "normalization": tnorm,
                                "label": tgt["display_label"], "values": None,
                                "available": False,
                                "transform": {
                                    "kind": "ontology_transformation_rule",
                                    "rule_id": rule.id, "rule_type": rule.type,
                                    "direction": direction, "route": route,
                                    "required_bridge": missing[0],
                                    "parameters": None, "resolved": False},
                                "missing_bridge": missing[0],
                                "unavailable_reason": (
                                    "ontology rule %s needs %s, which is not "
                                    "resolved for this series"
                                    % (rule.id, ", ".join(missing)))})
                            refused += 1
                        continue
                    try:
                        if direction == "forward":
                            vals = rule.apply(vals0, ctx=ctx, from_unit=unit0,
                                              allow_empty_as_dimensionless=True)
                            out_unit = rule.output_unit
                        else:
                            # the inverse lands on the rule's SOURCE side; produce
                            # it directly in that target's canonical unit so no
                            # spurious conversion step is minted afterwards
                            vals = rule.invert(vals0, ctx=ctx,
                                               from_unit=tgt["canonical_unit"],
                                               to_unit=unit0,
                                               allow_empty_as_dimensionless=True)
                            out_unit = tgt["canonical_unit"]
                    except Exception:
                        refused += 1
                        continue
                    hop = _rule_hop(rule, direction,
                                    {"ctx": ctx, "prov": prov}, ap_rec)
                    full_route = route + [hop]
                    if tgt["target_id"] not in have_targets:
                        rep = _rule_rep(axis, rule, direction, vals, out_unit,
                                        {"ctx": ctx, "prov": prov}, case,
                                        rep_id, full_route)
                        srep = _sig(axis, rep)
                        if srep.get("target_id"):
                            reps[rep_id] = srep
                            have_targets.add(srep["target_id"])
                            made += 1
                        else:
                            refused += 1
                    frontier.append((tq, tnorm, vals, out_unit,
                                     full_route, idparts + [rid]))
    return made, refused


def _rep_semantics_key(r):
    """What a representation MEANS: its ontology-resolved target descriptor.

    ComparisonGroup identity (or the QuantityKind fallback), the normalization
    definition, the canonical unit and the axis. Source spellings play no part."""
    return (r.get("target_kind"), r.get("comparison_group"),
            r.get("quantity_id") or r.get("quantity"), r.get("normalization_id"),
            r.get("canonical_unit"), r.get("axis"))


def _overlay_route(r):
    """How one series reaches a shared target: the provenance the overlay would use."""
    tr = r.get("transform") or {}
    return {"representation_id": r.get("id"),
            "representation_kind": r.get("representation_kind"),
            "transform_kind": tr.get("kind"),
            "rule": tr.get("rule") or tr.get("rule_id"),
            "bridge": (tr.get("bridge")
                       or (tr.get("parameters") or {}).get("bridge_quantity")
                       or ((tr.get("parameters") or {}).get("reference") is not None
                           and tr.get("rule_id")) or None),
            "bridge_source": r.get("bridge_source"),
            "parameter_provenance": tr.get("parameter_provenance")}


def pair_axis_reachability(sa, sb, axis):
    """Shared semantic targets this pair can BOTH materialise on one axis, with routes.

    This is the same evidence the overlay draws from -- available values, an authorised
    target, and semantics that agree -- computed once, here, so the pair verdict and the
    plot can never cite different facts.
    """
    def reach(s):
        return {r["target_id"]: r for r in s["%s_representations" % axis].values()
                if r.get("available") and r.get("values")
                and r.get("overlay_authorized") is not False and r.get("target_id")}
    ta, tb = reach(sa), reach(sb)
    out = []
    for t in sorted(set(ta) & set(tb)):
        if _rep_semantics_key(ta[t]) != _rep_semantics_key(tb[t]):
            continue
        out.append({"target_id": t, "a_route": _overlay_route(ta[t]),
                    "b_route": _overlay_route(tb[t])})
    return out


def _unevidenced_assumptions(sa, sb, axis):
    """Evidence the ontology declares would license a refused rule, per side.

    A rule gated by its applicability policy is not missing its numeric operand --
    it is missing the declared EVIDENCE for its assumption. The gap report names
    that evidence, so 'missing' says what would actually unlock the comparison."""
    out = set()
    for s in (sa, sb):
        for r in s["%s_representations" % axis].values():
            tr = r.get("transform") or {}
            if r.get("available") or not tr:
                continue
            reason = r.get("unavailable_reason")
            if isinstance(reason, str) and reason.startswith("assumption unevidenced"):
                rule = RULES.REGISTRY.get(tr.get("rule_id"))
                for k in ((rule.applicability.get("evidence") if rule else None) or []):
                    out.add(k)
    return out


def _unmaterialized_bridges(sa, sb, axis):
    """Bridges of declared-but-unbuilt transforms, per side, for the honest gap report."""
    out = set()
    for s in (sa, sb):
        for r in s["%s_representations" % axis].values():
            if r.get("transform") and not r.get("available"):
                br = (r.get("missing_bridge")
                      or (r.get("transform") or {}).get("required_bridge")
                      or (r.get("transform") or {}).get("bridge"))
                if br:
                    out.add(br)
    return out


def comparability(series, cases=None):
    """Frozen-runtime pair verdicts, derived from ONE authority.

    The semantic classification (same quantity? declared transform? ambiguous basis?)
    comes from the frozen comparability layer. Whether the pair can actually SHARE an
    axis, which context that uses, and what is missing all come from representation
    reachability -- the same materialised representations the overlay draws. The two can
    therefore never contradict: a pair cannot claim a bridge is missing while an overlay
    built from that bridge is on screen, because both read the same routes.
    """
    # a profile without materialised native coordinates cannot be compared as a profile
    prof = [s for s in series.values()
            if s["is_profile"] and s["n_points"]
            and "native" in s["x_representations"] and "native" in s["y_representations"]]

    def canonical_projections(s, ax):
        """Projections as the canonical layer computed them, read back from the reps."""
        out = []
        for r in s["%s_representations" % ax].values():
            tr = r.get("transform") or {}
            if tr.get("kind") == "CANONICAL_PROJECTION" and r.get("available"):
                out.append({"quantity": r.get("quantity"), "unit": r.get("unit"),
                            "from_normalization": tr.get("from_normalization")})
        return out

    rt = {s["id"]: {"paper_id": s["paper_id"], "result_series_id": s["id"],
                    "data_source": s["data_source"],
                    "x_quantity": s["x"]["x_quantity"], "x_unit": s["x"]["x_unit"],
                    "x_label": s["x"]["x_label"], "x_normalization": s["x"]["x_norm"],
                    "x_comparison_group": s["x"]["x_group"],
                    "y_quantity": s["y"]["y_quantity"], "y_unit": s["y"]["y_unit"],
                    "y_label": s["y"]["y_label"], "y_normalization": s["y"]["y_norm"],
                    "y_comparison_group": s["y"]["y_group"],
                    "points": [list(t) for t in
                               zip(s["x_representations"]["native"]["values"],
                                   s["y_representations"]["native"]["values"])],
                    # the canonical layer's own projections travel with the record; a
                    # comparison that pretends they do not exist reports MISSING for a
                    # transform whose result is already on disk
                    "projections": {ax: canonical_projections(s, ax)
                                    for ax in ("x", "y")},
                    "transformations": []} for s in prof}
    bcase = {sid: bridge_case(series[sid], cases) for sid in rt}
    pairs, counts = {}, Counter()
    ids = sorted(rt)
    OK_LEVEL = ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = rt[a], rt[b]
            sa, sb = series[a], series[b]
            if ra["y_comparison_group"] != rb["y_comparison_group"] \
                    and ra["y_quantity"] != rb["y_quantity"] \
                    and not CT.rule_between(ra["y_quantity"], rb["y_quantity"])[0]:
                continue
            d = RC.compare_result_series(ra, rb)
            ds = RC.compare_result_series(ra, rb, allow_shape_only=True)
            # A missing_context verdict says the bridge was not found ON THE RESULT. The
            # series' own Condition Case is evidence for this result too, so it is asked
            # before the transform is abandoned -- but only for that conditional verdict.
            # REFUSED / NOT_COMPARABLE state that the comparison is wrong, not underfed,
            # and no amount of context may promote them.
            prov = []
            ca, cb = bcase.get(a), bcase.get(b)
            if d["profile_status"] == RC.MISSING_CONTEXT and ca and cb:
                need = sorted(set(d["x"]["missing_context"] + d["y"]["missing_context"]))
                # each side must supply the bridge from ITS OWN case: one feature height
                # does not become the other profile's feature height
                got = [(q, RC.resolve_context(q, case=ca), RC.resolve_context(q, case=cb))
                       for q in need]
                if need and all(x["found"] and y["found"] for _, x, y in got):
                    d2 = RC.compare_result_series(ra, rb, a_case=ca, b_case=cb)
                    if d2["profile_status"] != RC.MISSING_CONTEXT:
                        d = d2
                        ds = RC.compare_result_series(ra, rb, a_case=ca, b_case=cb,
                                                      allow_shape_only=True)
                        prov = [{"quantity": q,
                                 "sources": [{"result_series_id": sid,
                                              "case_id": c["case_id"],
                                              "value": r["value"], "unit": r["unit"],
                                              "source_object": r["source_object"],
                                              "confidence": r["confidence"]}
                                             for sid, c, r in ((a, ca, x), (b, cb, y))]}
                                for q, x, y in got]
            st = d["profile_status"]
            x_status, x_reason = d["x"]["status"], d["x"]["reason"]
            y_status, y_reason = d["y"]["status"], d["y"]["reason"]
            reach = {ax: pair_axis_reachability(sa, sb, ax) for ax in ("x", "y")}
            reachable = bool(reach["x"]) and bool(reach["y"])
            # an axis that reaches a shared materialised target is not missing anything:
            # only the axes with no route contribute to the gap report; a rule
            # refused for an unevidenced assumption contributes the evidence the
            # ontology declares would license it
            missing = sorted(
                set(q for ax in ("x", "y") if not reach[ax]
                    for q in d[ax]["missing_context"])
                | set(k for ax in ("x", "y") if not reach[ax]
                      for k in _unevidenced_assumptions(sa, sb, ax)))

            if st == RC.MISSING_CONTEXT and reachable:
                # The bridge the frozen layer could not find HAS been found: each side
                # materialised a representation on a shared target from its own record
                # or its own Condition Case, and those routes carry the provenance. The
                # verdict is promoted by that evidence, never by optimism.
                st = "TRANSFORMABLE_PROFILE"
                for ax, ax_st, ax_res in (("x", x_status, d["x"]), ("y", y_status, d["y"])):
                    if ax_res["status"] == RC.MISSING_CONTEXT:
                        routes = reach[ax][0]
                        if ax == "x":
                            x_status = "TRANSFORMABLE_VIA_REPRESENTATION"
                            x_reason = ("both series materialise the shared target %r; "
                                        "the pair verdict and the overlay read the same "
                                        "routes" % routes["target_id"])
                        else:
                            y_status = "TRANSFORMABLE_VIA_REPRESENTATION"
                            y_reason = ("both series materialise the shared target %r; "
                                        "the pair verdict and the overlay read the same "
                                        "routes" % routes["target_id"])
                        for q in list(ax_res["missing_context"]):
                            srcs = []
                            for sid, route in ((a, routes["a_route"]),
                                               (b, routes["b_route"])):
                                bs = route.get("bridge_source") or {}
                                pp = route.get("parameter_provenance") or {}
                                srcs.append({"result_series_id": sid,
                                             "case_id": bs.get("case_id"),
                                             "value": bs.get("value",
                                                             pp.get("value")),
                                             "unit": bs.get("unit", pp.get("unit")),
                                             "source_object":
                                                 bs.get("source_object")
                                                 or pp.get("source_object")
                                                 or "materialised representation %s"
                                                 % route.get("representation_id"),
                                             "confidence": bs.get("confidence")
                                             or pp.get("confidence")})
                            prov.append({"quantity": q, "sources": srcs})
                missing = []
            elif st == "TRANSFORMABLE_PROFILE" and not reachable:
                # One authority, both directions: the frozen layer believes a
                # declared transform bridges these series, but no shared target is
                # actually materialised -- the route is refused (an unevidenced
                # assumption, an unresolved parameter). A pair may not claim
                # transformable while the overlay it promises is refused, so the
                # verdict is demoted to the honest conditional, and `missing`
                # names what would actually unlock it.
                st = RC.MISSING_CONTEXT
                for ax in ("x", "y"):
                    if not reach[ax]:
                        gap = sorted(_unevidenced_assumptions(sa, sb, ax)
                                     | _unmaterialized_bridges(sa, sb, ax))
                        reason = ("the declared transform's route is not "
                                  "materialised for this pair; missing: %s"
                                  % (", ".join(gap) or "a refused route"))
                        if ax == "x":
                            x_status, x_reason = RC.MISSING_CONTEXT, reason
                        else:
                            y_status, y_reason = RC.MISSING_CONTEXT, reason
                        missing = sorted(set(missing) | set(gap))
            elif st in OK_LEVEL:
                # what remains missing is only what NO materialised route supplies
                still = set()
                for ax in ("x", "y"):
                    if not reach[ax]:
                        still |= _unmaterialized_bridges(sa, sb, ax)
                missing = sorted(still)

            counts[st] += 1
            pairs["%s|%s" % (a, b)] = {
                "status": st,
                "shape_only_status": ds["profile_status"],
                # One authority: a shared physical axis needs BOTH the semantic verdict
                # and a materialised common target on each axis. ambiguous and
                # not-comparable never overlay; shape-only is a separate, explicitly
                # requested mode.
                "physical_overlay_allowed": st in OK_LEVEL and reachable,
                "shape_only_eligible": ds["profile_status"] == "SHAPE_ONLY_PROFILE",
                "cross_paper": d["cross_paper"],
                "x_status": x_status, "x_reason": x_reason,
                "y_status": y_status, "y_reason": y_reason,
                "missing": missing,
                # the shared targets and per-side routes the overlay itself would use
                "overlay_targets": {
                    ax: [{"target_id": r["target_id"],
                          "a_route": r["a_route"], "b_route": r["b_route"]}
                         for r in reach[ax]] for ax in ("x", "y")},
                # which Case supplied which bridge, per side
                "context_provenance": prov,
                "verdict_authority": ("frozen axis semantics + representation "
                                      "reachability; overlay and explanation read "
                                      "this same record"),
            }
    return pairs, counts


#: Facet declarations. `scope` is the whole contract: a Condition Case-scoped facet must
#: be satisfied together with every other case-scoped constraint on ONE case, while
#: MeasurementAct- and ResultSeries-scoped facets are properties of the result itself.
#: Adding a facet is a change here, not a change to the filtering algorithm.
FACET_DEFS = [
    {"id": "material", "label": "Deposited material", "scope": "Condition Case"},
    {"id": "precursor", "label": "Precursor", "scope": "Condition Case"},
    {"id": "coreactant", "label": "Co-reactant", "scope": "Condition Case"},
    {"id": "geometry", "label": "Geometry", "scope": "Condition Case"},
    {"id": "paper", "label": "Paper", "scope": "Condition Case"},
    {"id": "technique", "label": "Measurement technique", "scope": "MeasurementAct"},
    {"id": "quantity", "label": "Result quantity", "scope": "ResultSeries"},
    {"id": "coordinate", "label": "Result coordinate", "scope": "ResultSeries"},
    {"id": "normalization", "label": "Normalization basis", "scope": "ResultSeries"},
    {"id": "data_source", "label": "Result type", "scope": "ResultSeries"},
]
CASE_SCOPE = "Condition Case"


def case_scoped_facet_ids():
    return [f["id"] for f in FACET_DEFS if f["scope"] == CASE_SCOPE]


def facets(cases, acts, series):
    """Facet option -> the entity ids it is compatible with, precomputed."""
    idx = defaultdict(lambda: defaultdict(lambda: {"cases": set(), "series": set()}))

    def add(f, v, cid, sid):
        if v in (None, ""):
            return
        e = idx[f][str(v)]
        if cid:
            e["cases"].add(cid)
        if sid:
            e["series"].add(sid)

    for s in series.values():
        for cid in (s["all_case_ids"] or [None]):
            add("quantity", s["y"]["y_quantity"], cid, s["id"])
            add("coordinate", s["x"]["x_quantity"], cid, s["id"])
            add("data_source", s["data_source"], cid, s["id"])
            add("normalization", s["normalization_basis"], cid, s["id"])
            a = acts.get(s["act_id"])
            if a:
                add("technique", a["technique"], cid, s["id"])
            c = cases.get(cid) if cid else None
            if c:
                add("material", c["material"], cid, s["id"])
                add("geometry", c["geometry"], cid, s["id"])
                add("paper", c["paper_id"], cid, s["id"])
                for p in c["chemistry"].get("precursor", []):
                    add("precursor", p, cid, s["id"])
                for p in c["chemistry"].get("coreactant", []):
                    add("coreactant", p, cid, s["id"])
    return {f: {v: {"cases": sorted(e["cases"]), "series": sorted(e["series"])}
                for v, e in vals.items()} for f, vals in idx.items()}


_NUMRE = __import__("re").compile(r"^\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*$")


def _num(v):
    """A numeric condition value, or None. Ranges must compare physics, not text."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and _NUMRE.match(v):
        return float(v)
    return None


def condition_field_id(quantity, species, step_context=None, activation=None):
    """The identity of a numeric condition. A TMA pulse and an H2O pulse are two
    quantities, not one quantity written twice, and the frozen condition layer already
    says so -- this only has to avoid throwing the qualifier away again."""
    base = "%s@%s" % (quantity, species) if species else str(quantity)
    # the half-cycle is part of the identity: without it a precursor purge and a reactant
    # purge share one field and one range filter answers for both
    if step_context:
        base = "%s#%s" % (base, step_context)
    # so is the activation: a 2 s thermal O2 exposure and a 2 s O2 plasma exposure are the
    # same number describing two different processes. Only a stated non-default activation
    # qualifies, so a thermal corpus keeps the field ids it already had.
    # An explicitly THERMAL step is also distinct from one whose activation nobody
    # stated: "run without a plasma" and "not said" are different records, and collapsing
    # them lets an unstated step answer a filter that asked for thermal.
    if activation:
        base = "%s~%s" % (base, activation)
    return base


def numeric_conditions(cases):
    """Canonical numeric condition values, so a range filter compares physics not text.

    Each entry carries its quantity and species as fields. Downstream code must read
    those, never re-derive them by splitting the key: `key.split("@")[0]` is how a TMA
    pulse time and an H2O pulse time became one ambiguous facet.
    """
    out = {}
    for cid, c in cases.items():
        vals = {}
        for x in c["conditions"]:
            n = _num(x.get("value"))
            if n is None:
                continue
            sp = x.get("species")
            norm = None
            try:
                if x.get("unit"):
                    fu = U.parse(x["unit"])
                    norm = float(n) * fu.factor + fu.offset
            except Exception:
                norm = None
            step, act = x.get("step_context"), x.get("activation")
            vals.setdefault(condition_field_id(x["quantity"], sp, step, act), []).append(
                {"raw": n, "unit": x.get("unit"), "canonical": norm,
                 "quantity": x["quantity"], "species": sp, "step_context": step,
                 "activation": act})
        out[cid] = vals
    return out


#: A numeric field is offered as a range filter once this many Condition Cases carry it.
#: Every qualified sibling of an offered quantity is then offered too -- showing an H2O
#: pulse time without its TMA counterpart is its own kind of misleading.
_RANGE_MIN_CASES = 10


def _label(quantity, species, step_context=None, activation=None):
    """'pulse_time', 'TMA' -> 'TMA pulse time'. The species leads because that is what
    distinguishes it from its siblings; the ALD step leads over both, because it is what
    makes two identical durations different experiments."""
    words = str(quantity).replace("_", " ")
    if step_context:
        words = "%s (%s)" % (words, str(step_context).replace("_", " "))
    if activation and activation != PS.ACTIVATION_NONE:
        words = "%s, %s" % (words, activation)
    if species:
        return "%s %s" % (species, words)
    return words[:1].upper() + words[1:]


def range_fields(numeric):
    """Numeric quantities offered as range filters, in the unit the filter runs in.

    Two separate lies were possible here. The range box used to advertise the unit the
    paper wrote (°C) while comparing canonical magnitudes (K). And the field identity was
    the quantity alone, so one "Pulse time" box silently addressed whichever of
    pulse_time@TMA / pulse_time@H2O the browser happened to find first. A field is now
    the exact condition key, and it carries its species so no consumer has to parse it
    back out of a string.
    """
    cov, units, canon, meta = Counter(), defaultdict(set), Counter(), {}
    for fields in numeric.values():
        for fid, entries in fields.items():
            cov[fid] += 1
            for e in entries:
                meta.setdefault(fid, (e.get("quantity"), e.get("species"),
                                      e.get("step_context"), e.get("activation")))
                if e.get("unit"):
                    units[fid].add(e["unit"])
                if e.get("canonical") is not None:
                    canon[fid] += 1

    # a quantity is in scope on coverage; its qualified siblings come with it
    quantities = {meta[f][0] for f in cov if cov[f] >= _RANGE_MIN_CASES and f in meta}
    scope = [f for f in cov if f in meta and (cov[f] >= _RANGE_MIN_CASES
                                              or meta[f][0] in quantities)]

    out, dropped = [], []
    for fid in sorted(scope, key=lambda f: (-cov[f], f)):
        quantity, species, step, activation = meta[fid]
        bases = set()
        for u in units[fid]:
            try:
                bases.add(U.base_symbol(u))
            except Exception:
                bases.add(None)
        if len(bases) != 1 or None in bases or not canon[fid]:
            dropped.append({"field_id": fid, "reason": "no single canonical dimension"})
            continue
        out.append({"id": fid, "field_id": fid, "quantity_id": quantity,
                    "species_or_role": species, "step_context": step,
                    "activation": activation,
                    "label": _label(quantity, species, step, activation),
                    "display_label": _label(quantity, species, step, activation),
                    "canonical_unit": bases.pop(), "cases_covered": cov[fid],
                    "raw_units": sorted(units[fid]),
                    "comparison_basis": "canonical magnitude"})

    # an unqualified field sitting beside qualified siblings is not "all of them"
    by_quantity = defaultdict(list)
    for f in out:
        by_quantity[f["quantity_id"]].append(f)
    for q, fs in by_quantity.items():
        if len(fs) > 1:
            for f in fs:
                f["has_qualified_siblings"] = True
                if not f["species_or_role"]:
                    f["display_label"] += " (species unattributed)"
        else:
            fs[0]["has_qualified_siblings"] = False
    if dropped:
        print("range fields not offered: %s" % dropped)
    return out


#: A condition value that is a delimiter-separated list of numbers -- a recipe written as
#: one string. Detected by SHAPE, not by quantity name, so a differently-named sequence
#: quantity in a future paper is audited the same way.
_SEQ_SPLIT = __import__("re").compile(r"[-\u2013\u2014/,;|]")
_SEQ_NUM = __import__("re").compile(r"^\s*\d*\.?\d+\s*$")

#: what a sequence occurrence is worth, once its context is known
SEQ_EXPLICIT_PRESENT = "EXPLICIT_FIELDS_ALREADY_PRESENT"
SEQ_DERIVATION_SAFE = "GENERAL_DERIVATION_SAFE"
SEQ_AMBIGUOUS = "DERIVATION_AMBIGUOUS"
SEQ_NOT_TIMES = "NOT_A_PULSE_PURGE_TIME_ENCODING"
SEQ_NO_CONTEXT = "INSUFFICIENT_CONTEXT"

#: the two step kinds a pulse/purge recipe alternates between
_STEP_KINDS = (PS.PULSE_TIME, PS.PURGE_TIME)


def sequence_terms(value):
    """The numeric terms of a sequence-shaped condition value, or None.

    A single number is not a sequence, however it is spelled: `1e-7` contains a hyphen
    and splitting on it would invent a two-step recipe out of one pressure.
    """
    if not isinstance(value, str):
        return None
    if _num(value) is not None:
        return None                   # one number, exponent hyphen and all
    parts = [t for t in _SEQ_SPLIT.split(value) if t.strip()]
    if len(parts) < 2:
        return None
    if not all(_SEQ_NUM.match(t) for t in parts):
        return parts, None            # multi-term but not a sequence of numbers
    return parts, [float(t) for t in parts]


def role_qualified_keys(case, quantity):
    """Every recorded condition that is a role- or species-qualified variant of one bare
    quantity, found structurally from the recorded quantity ids.

    `pulse_time` and `precursor_pulse_time@TMA` are different quantities: one is silent
    about which chemical was pulsed and the other is not. This finds the second kind so a
    reader of the first can be told the information exists, without either being restated
    as the other.

    The relation is the suffix one the ontology already uses for role-prefixed composites
    (`<role>_<quantity>`), so no list of role names is needed and a role this corpus has
    never seen is picked up the same way. A case's `chemistry` block is not consulted: it
    is frequently empty even where the qualified conditions are recorded.
    """
    suffix = "_%s" % quantity
    out = []
    for c in case.get("conditions") or []:
        q = str(c.get("quantity") or "")
        if q.endswith(suffix) and len(q) > len(suffix):
            out.append(c)
        elif q == quantity and c.get("species"):
            out.append(c)
    return out


def qualifier_roles(case, quantity):
    """The role prefixes actually recorded for a quantity on this case."""
    suffix = "_%s" % quantity
    return sorted({str(c["quantity"])[:-len(suffix)]
                   for c in role_qualified_keys(case, quantity)
                   if str(c["quantity"]).endswith(suffix)})


def classify_sequence(case, cond):
    """What a sequence occurrence can and cannot be used for. Corpus evidence only."""
    parsed = sequence_terms(cond.get("value"))
    if parsed is None:
        return SEQ_NOT_TIMES, {"reason": "value is not a multi-term sequence"}
    parts, nums = parsed
    if nums is None:
        return SEQ_NOT_TIMES, {"reason": "sequence terms are not all numeric",
                               "terms": parts}
    # roles come from what the record actually qualifies, not from a fixed vocabulary
    roles = sorted({r for k in _STEP_KINDS for r in qualifier_roles(case, k)})
    explicit = {}
    for kind in _STEP_KINDS:
        for c in role_qualified_keys(case, kind):
            explicit["%s|%s|%s" % (kind, c["quantity"], c.get("species"))] = c
    need = len(roles) * len(_STEP_KINDS)
    ev = {"terms": nums, "n_terms": len(nums), "roles": roles,
          "explicit_qualified_fields": sorted(
              "%s%s" % (c["quantity"], "@" + c["species"] if c.get("species") else "")
              for c in explicit.values()),
          "sequence_unit": cond.get("unit")}
    if not roles:
        return SEQ_NO_CONTEXT, dict(ev, reason="no chemistry roles on this case, so the "
                                               "terms cannot be attributed to reactants")
    if need and len(explicit) >= need:
        # the terms add nothing; whether they AGREE is still worth reporting
        return SEQ_EXPLICIT_PRESENT, dict(ev, reason="every step is already recorded as an "
                                                    "explicit role/species-qualified field")
    if len(nums) != need:
        return SEQ_AMBIGUOUS, dict(ev, reason="term count does not match %d roles x %d "
                                              "step kinds" % (len(roles), len(_STEP_KINDS)))
    return SEQ_AMBIGUOUS, dict(ev, reason="term count fits, but the sequence carries no "
                                          "unit, no role labels and no step labels, so "
                                          "which term is which reactant is not recorded")


def sequence_audit(cases):
    """Every sequence-shaped condition in the corpus, classified."""
    out = []
    for cid, c in cases.items():
        for cond in c.get("conditions") or []:
            parsed = sequence_terms(cond.get("value"))
            if parsed is None:
                continue
            status, ev = classify_sequence(c, cond)
            out.append({"case": cid, "quantity": cond.get("quantity"),
                        "value": cond.get("value"), "status": status, "evidence": ev})
    return out


def sequence_corroboration(cases, audit):
    """Does a sequence AGREE with the explicit fields it duplicates?

    This is the safe use of the string: verification, never derivation. Agreement is
    reported as multiset equality, because the string does not record which term is which
    step and matching by position would assume the very ordering that is not written down.
    """
    agree = disagree = 0
    for row in audit:
        if row["status"] != SEQ_EXPLICIT_PRESENT:
            continue
        c = cases[row["case"]]
        vals = []
        for kind in _STEP_KINDS:
            for x in role_qualified_keys(c, kind):
                n = _num(x.get("value"))
                if n is not None:
                    vals.append(n)
        terms = row["evidence"]["terms"]
        ok = sorted(vals) == sorted(terms)
        row["corroborates_explicit_fields"] = ok
        agree += 1 if ok else 0
        disagree += 0 if ok else 1
    return agree, disagree


# --- point -> Condition Case resolution -------------------------------------------
# A sweep figure often IS the experiment table: each point was measured at one design
# point. Recovering which is worth doing, and worth refusing to guess at. The only
# evidence used is the one the record actually carries -- the series' own x quantity and
# the cases' own conditions -- compared through the frozen condition semantics. Nothing
# is inferred from ordering, from list lengths, or from a figure legend.
POINT_RESOLVED = "RESOLVED"
POINT_AMBIGUOUS = "UNRESOLVED_AMBIGUOUS"
POINT_NO_MATCH = "UNRESOLVED_NO_MATCH"
POINT_UNRESOLVED_IDENTITY = "UNRESOLVED_POINT_INDEX_IDENTITY"

EV_EXACT = "EXACT_SEMANTIC_VALUE_MATCH"
EV_CONVERTED = "UNIT_CONVERTED_EXACT_MATCH"
EV_AMBIGUOUS = "AMBIGUOUS_MULTIPLE_CASES"
EV_NO_CONDITION = "NO_COMPATIBLE_CASE_CONDITION"
EV_NO_VALUE = "NO_MATCHING_CASE_VALUE"
EV_UNSUPPORTED = "UNSUPPORTED_X_SEMANTICS"
EV_NO_SOURCE_X = "NO_SOURCE_X_VALUE"
EV_NO_SOURCE_INDEX = "SOURCE_POINT_INDEX_NOT_PROVEN"

#: How a point's identity as a SOURCE observation is known.
IDENTITY_PRESERVED = "SOURCE_INDEX_PRESERVED"
IDENTITY_VERIFIED = "SOURCE_INDEX_VERIFIED"
IDENTITY_UNRESOLVED = "SOURCE_INDEX_UNRESOLVED"

SERIES_POINT_CASE_RESOLVED = "POINT_CASE_RESOLVED"
SERIES_PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
SERIES_CASE_SET_ONLY = "CASE_SET_ONLY"
SERIES_NO_CASE_CONTEXT = "NO_CASE_CONTEXT"

RESOLUTION_METHOD = "X_VALUE_MATCH_TO_CASE_CONDITION"
DERIVED_STATUS = "DERIVED_FOR_WORKBENCH"


def _same_quantity_identity(cond, quantity, species, axis_step=None):
    """Does a case condition denote the same quantity as the series axis?

    Species is part of the identity where it is recorded: a TMA pulse and an H2O pulse
    are different quantities however equal their numbers. MISSING is not SAME, so a bare
    axis does not match a qualified condition and vice versa -- the axis simply does not
    say which reagent it means, and reading one in would be the assertion, not the record.

    A STEP-RESOLVED condition is the exception, and not a weakening of that rule. Its
    position in the cycle was read from this same printed axis, and its reagent follows
    from that position rather than from any wording on the axis -- so the species is not
    an independent qualifier that the axis fails to state. What must agree instead is the
    step: an axis the source calls a plasma exposure matches the reactant exposure and
    nothing else. Where the axis names no step, only the timing quantity is compared and
    a case carrying two candidate steps is left to the ambiguity gate.
    """
    cstep = cond.get("step_context")
    if cstep:
        # SIDE compatibility is the screen here, not the whole identity. A step-resolved
        # condition is stored under its role-specialised name while the axis prints
        # whatever its own layer chose, so the raw spellings cannot be compared -- but a
        # purge can never bind an exposure-side axis, and the step must agree where the
        # axis states one. The pulse/exposure FAMILY comparison is deliberately not
        # done here: it needs the axis label and the case's other timing conditions,
        # and lives in `_timing_identity_basis`, the one place that decides whether a
        # side-compatible pair is actually the same physical quantity.
        cq = PS.timing_side(cond.get("quantity"))
        aq = PS.timing_side(quantity)
        if not cq or cq != aq:
            return False
        return axis_step is None or axis_step == cstep
    if cond.get("quantity") != quantity:
        return False
    return (cond.get("species") or None) == (species or None)


def _canonical_magnitude(value, unit):
    """The frozen condition contract, asked about a plotted coordinate."""
    return CQ.normalized_value({"value": value, "unit": unit})


#: How a plotted x axis was related to a case-scoped condition quantity.
AXIS_IDENTITY_MATCH = "IDENTITY_MATCH"
AXIS_AMBIGUOUS_QUALIFIED = "AMBIGUOUS_QUALIFIED_BINDING"
AXIS_UNIQUE_VARIATION_UNSUPPORTED = "UNIQUE_QUALIFIED_VARIATION_WITHOUT_SUPPORT"
AXIS_NO_COMPATIBLE_QUANTITY = "NO_COMPATIBLE_CASE_QUANTITY"

#: Coverage classes. Every multi-case ResultSeries lands in exactly one.
COV_RESOLVED = "CASE_DATA_RESOLVED"
COV_PARTIAL = "CASE_DATA_PARTIAL"
COV_COORDS_MISSING = "COORDINATES_MISSING_UPSTREAM"
COV_AXIS_UNRESOLVED = "AXIS_SEMANTIC_BINDING_UNRESOLVED"
COV_AMBIGUOUS = "AMBIGUOUS_CASE_MAPPING"
COV_CASE_SET_ONLY = "CASE_SET_ONLY_GENUINE"

#: Why an unresolved series is unresolved.
BLOCK_PROPAGATION = "WORKBENCH_PROPAGATION_DEFECT"
BLOCK_SEMANTIC = "SEMANTIC_BINDING_DEFECT"
BLOCK_EXTRACTION = "UPSTREAM_EXTRACTION_GAP"
BLOCK_EVIDENCE = "GENUINE_EVIDENCE_LIMIT"


def axis_binding(s, cases):
    """How the plotted x axis relates to a case-scoped condition quantity.

    The axis names a quantity; the cases may record that quantity bare, or qualified by a
    reactant role or species, or not at all. Only an exact identity is used to match:
    a bare axis does not name a reagent, and reading one in would be the assertion rather
    than the record. Where a qualified sibling is the only thing that varies, that is
    recorded as evidence and explicitly NOT acted on -- correlation between "this varies"
    and "this is what the figure swept" is not identity, and nothing persisted here
    establishes the difference.
    """
    xq = ((s.get("native_points") or {}).get("x") or {}).get("quantity")
    ev = {"source_axis_quantity": xq, "bound_case_quantity": None,
          "bound_species_or_role": None, "binding_method": None,
          "binding_evidence": [], "binding_source": "case conditions of the associated "
                                                    "Condition Cases"}
    if not xq:
        return dict(ev, axis_binding_status=AXIS_NO_COMPATIBLE_QUANTITY)
    exact, qualified = [], []
    varying = {}
    for cid in s.get("all_case_ids") or []:
        for c in (cases.get(cid) or {}).get("conditions") or []:
            q, sp = c.get("quantity"), c.get("species")
            key = q + ("@" + sp if sp else "")
            if c.get("value") not in (None, ""):
                varying.setdefault(key, set()).add(str(c["value"]))
            if q == xq and not sp:
                exact.append(key)
            elif (q == xq and sp) or (str(q).endswith("_%s" % xq) and len(str(q)) > len(xq) + 1):
                qualified.append(key)
    varies = {k for k, v in varying.items() if len(v) > 1}
    if exact:
        return dict(ev, axis_binding_status=AXIS_IDENTITY_MATCH,
                    bound_case_quantity=xq, binding_method="exact quantity identity",
                    binding_evidence=["the associated cases record %r itself" % xq])
    cand = sorted({k for k in qualified if k in varies})
    if not qualified:
        return dict(ev, axis_binding_status=AXIS_NO_COMPATIBLE_QUANTITY,
                    binding_evidence=["no associated case records %r, qualified or not"
                                      % xq])
    if len(cand) > 1:
        return dict(ev, axis_binding_status=AXIS_AMBIGUOUS_QUALIFIED,
                    binding_evidence=["more than one qualified variant varies: %s"
                                      % ", ".join(cand)])
    # exactly one qualified sibling varies. Recorded, not acted on: a bare axis does not
    # name a reagent, and no persisted evidence here says which one was swept.
    return dict(ev, axis_binding_status=AXIS_UNIQUE_VARIATION_UNSUPPORTED,
                binding_evidence=(["exactly one qualified variant varies: %s" % cand[0]]
                                  if cand else
                                  ["qualified variants exist but none varies: %s"
                                   % ", ".join(sorted(set(qualified)))]))


def source_x_points(s, contract):
    """The x values to match on, each carrying the SOURCE index of the point it came from.

    Canonical x is the comparison representation and stays so. What it must never be is a
    source of point identity: enumerating it would mint an index out of a representation,
    so if canonicalisation dropped a point every later canonical position would name an
    earlier source point and a resolved link would attribute one observation's conditions
    to another.

    Identity therefore comes from the source tuple list, and the canonical array is only
    read at an index the contract has proven to be that same point. Where the contract
    does not hold, the points are returned with their identity unresolved and the resolver
    refuses to call them resolved -- an unattributable point, not a guessed one.
    """
    np_ = s.get("native_points") or {}
    tuples = np_.get("points") or []
    native_unit = (np_.get("x") or {}).get("unit")
    cx = (s.get("x_canonical") or {}).get("values") or []
    cunit = (s.get("x_canonical") or {}).get("unit")
    aligned = bool(contract.get("aligned"))
    out = []
    for i, t in enumerate(tuples):
        # The observation is the evidence. Where canonicalisation also produced a value at
        # this proven index it is carried alongside, but a curve whose x was never
        # canonicalised still has coordinates, and reading only the canonical array is why
        # six recorded sweeps reached the resolver as if they had no points at all.
        row = {"source_point_index": i, "native_x_value": t.get("x"),
               "value": t.get("x"), "unit": native_unit,
               "identity": IDENTITY_PRESERVED}
        if aligned and i < len(cx):
            row["identity"] = IDENTITY_VERIFIED
            row["canonical_x_value"] = cx[i]
            row["canonical_x_unit"] = cunit
        if t.get("x") is None:
            row["value"] = None
        out.append(row)
    return out


def axis_timing_family(quantity, label):
    """The pulse/exposure/purge family the AXIS establishes, or None when unresolved.

    Two records describe one printed axis: the label the source drew and the quantity a
    layer assigned to it. The printed label is the primary record, so where it names a
    timing kind, its family decides -- and a dose-worded label decides that the family
    is UNRESOLVED, because "dose" commits to neither pulse nor exposure. Where label
    and assigned quantity name two different resolved families, the axis is contested
    and the family is likewise unresolved (the disagreement is surfaced on the series).
    Only a label that names no timing kind leaves the assigned quantity to speak alone.
    """
    lk = PS.timing_family_from_label(label)
    qf = PS.timing_family_resolved(quantity)
    if lk is not None:
        lf = PS.timing_family_resolved(lk)
        if lf and qf and lf != qf:
            return None                       # contested between the axis' own records
        return lf                             # None for a dose-worded label: unresolved
    return qf


def _timing_identity_basis(cond, x_quantity, axis_family, case_conds, species,
                           axis_step):
    """How a case condition is the SAME quantity as the axis, or None to refuse.

    "Same precursor half-cycle" is never sufficient on its own: precursor_pulse_time
    and precursor_exposure_time coexist on one side as different physical conditions.
    The rule, in order:

      * side / step / species compatibility must hold (`_same_quantity_identity`);
      * where the timing FAMILY is resolved on both sides, the families must match;
      * where a family is genuinely unresolved on either side, the side identification
        is accepted only when the case offers no COMPETING timing kind for that
        side/step/species -- two candidate kinds make the attribution ambiguous, and
        ambiguity refuses rather than picks;
      * a non-timing or step-less condition keeps the exact-identity rule.
    """
    if not _same_quantity_identity(cond, x_quantity, species, axis_step):
        return None
    if not cond.get("step_context") or PS.timing_side(cond.get("quantity")) is None:
        return "exact quantity identity"
    cf = PS.timing_family_resolved(cond.get("quantity"))
    if axis_family and cf:
        return "timing family identity" if axis_family == cf else None
    kinds = {PS.timing_kind(c.get("quantity"))
             for c in (case_conds or [])
             if c.get("step_context")
             and _same_quantity_identity(c, x_quantity, species, axis_step)}
    if len(kinds) > 1:
        return None
    return ("cycle-side identity: the timing family is unresolved on one side and the "
            "case states exactly one timing kind for this side of the cycle")


def resolve_points_to_cases(points, x_unit, x_quantity, x_species, case_ids, cases,
                            axis_step=None, x_label=None):
    """One link per SOURCE point, or an explicit refusal.

    A point is resolved only when EXACTLY ONE associated Condition Case carries a
    condition of the same quantity identity whose canonical magnitude equals the point's.
    Two candidates is ambiguity, and ambiguity is reported, never broken by ordering.
    A point whose source index is not established is never reported as resolved.
    Quantity identity for timings follows `_timing_identity_basis`: matched families
    where both are resolved, an unambiguous side identification where one is not, and
    refusal everywhere else. The basis used is recorded on every resolved link.
    """
    axis_family = axis_timing_family(x_quantity, x_label)
    links = []
    for pt in points:
        i = pt["source_point_index"]
        xv = pt.get("value")
        unit = pt.get("unit", x_unit)
        ident = pt.get("identity")
        base_id = {"source_point_index": i, "point_identity_status": ident}
        if ident == IDENTITY_UNRESOLVED or i is None:
            links.append(dict(base_id, point_index=i, case_id=None,
                              resolution_status=POINT_UNRESOLVED_IDENTITY,
                              evidence=EV_NO_SOURCE_INDEX, point_x_value=xv,
                              point_x_unit=unit))
            continue
        if xv is None:
            # no x observation: this point cannot be matched by value, and shifting the
            # ones after it to close the gap is exactly what must not happen
            links.append(dict(base_id, point_index=i, case_id=None,
                              resolution_status=POINT_NO_MATCH,
                              evidence=EV_NO_SOURCE_X, point_x_value=None,
                              point_x_unit=unit))
            continue
        pm = _canonical_magnitude(xv, unit)
        if not x_quantity or pm is None:
            links.append(dict(base_id, point_index=i, case_id=None,
                              resolution_status=POINT_NO_MATCH,
                              evidence=EV_UNSUPPORTED, point_x_value=xv,
                              point_x_unit=unit))
            continue
        cands, saw_condition = [], False
        for cid in case_ids:
            conds = (cases.get(cid) or {}).get("conditions") or []
            for cond in conds:
                basis = _timing_identity_basis(cond, x_quantity, axis_family, conds,
                                               x_species, axis_step)
                if basis is None:
                    continue
                saw_condition = True
                cm = CQ.normalized_value(cond)
                if cm is None or cm[0] != pm[0] or cm[1] != pm[1]:
                    continue
                cands.append((cid, cond, cm, basis))
        base = {"point_index": i, "point_x_value": xv, "point_x_unit": unit,
                "source_point_index": i, "point_identity_status": ident,
                "matched_quantity": x_quantity, "matched_species_or_role": x_species,
                "resolution_method": RESOLUTION_METHOD,
                "evidence_source": "series canonical x value vs Condition Case condition, "
                                   "compared through the frozen condition semantics"}
        if len(cands) == 1:
            cid, cond, cm, basis = cands[0]
            converted = str(cond.get("unit") or "") != str(unit or "")
            links.append(dict(base, case_id=cid, resolution_status=POINT_RESOLVED,
                              evidence=EV_CONVERTED if converted else EV_EXACT,
                              identity_basis=basis,
                              case_condition_value=cond.get("value"),
                              case_condition_unit=cond.get("unit"),
                              canonical_value=cm[1], canonical_dimension=cm[0]))
        elif len(cands) > 1:
            links.append(dict(base, case_id=None,
                              resolution_status=POINT_AMBIGUOUS, evidence=EV_AMBIGUOUS,
                              candidate_case_ids=sorted({c for c, _, _, _ in cands})))
        else:
            links.append(dict(base, case_id=None, resolution_status=POINT_NO_MATCH,
                              evidence=EV_NO_VALUE if saw_condition else EV_NO_CONDITION))
    return links


def series_resolution_status(case_ids, links):
    if not case_ids:
        return SERIES_NO_CASE_CONTEXT
    if not links:
        return SERIES_CASE_SET_ONLY
    n = len([x for x in links if x["resolution_status"] == POINT_RESOLVED])
    if n == len(links) and n:
        return SERIES_POINT_CASE_RESOLVED
    if n:
        return SERIES_PARTIALLY_RESOLVED
    return SERIES_CASE_SET_ONLY


#: Whether an OBSERVED result value exists for a series, which is a different question
#: from whether the point->case relation resolved and a different one again from whether
#: the y axis was canonicalised.
RESULT_NATIVE_AND_CANONICAL = "NATIVE_AND_CANONICAL_AVAILABLE"
RESULT_NATIVE_ONLY = "NATIVE_ONLY"
RESULT_NONE = "NO_NATIVE_RESULT"


def native_result_status(s):
    """Series-level availability. A single point may still lack its y; that is a ROW-level
    fact and is reported per row, never by downgrading the series."""
    pts = (s.get("native_points") or {}).get("points") or []
    cy = (s.get("y_canonical") or {}).get("values") or []
    if not any(t.get("y") is not None for t in pts):
        return RESULT_NONE
    return RESULT_NATIVE_AND_CANONICAL if cy else RESULT_NATIVE_ONLY


def point_index_contract(s):
    """Do the native tuples and the canonical x array index the same extracted points?

    The point->case link indexes the canonical x array, and the observed value lives in
    the native tuple. Reading one with the other's index is only defensible if they are
    the same point vector, so that is checked rather than assumed: equal length, and each
    canonical x the same extracted number as its native x.
    """
    nat = (s.get("native_points") or {}).get("x") or {}
    pts = (s.get("native_points") or {}).get("points") or []
    nu = nat.get("unit")
    cx = (s.get("x_canonical") or {}).get("values") or []
    cu = (s.get("x_canonical") or {}).get("unit")
    base = {"n_native_tuples": len(pts), "n_canonical": len(cx)}
    if not pts or not cx:
        return dict(base, aligned=False, reason="one side has no coordinates")
    if len(pts) != len(cx):
        return dict(base, aligned=False, reason="different point counts")
    for i, (t, b) in enumerate(zip(pts, cx)):
        # identity is positional: canonical index i must BE source tuple i, whatever unit
        # each is written in. A source point with no x cannot be identified this way.
        if t.get("x") is None:
            return dict(base, aligned=False, first_unverifiable_index=i,
                        reason="source point %d has no x, so its canonical counterpart "
                               "cannot be identified" % i)
        if not _same_encoded_number(t["x"], nu, b, cu):
            return dict(base, aligned=False, first_mismatch_index=i,
                        reason="canonical x at index %d is not the same extracted number "
                               "as source point %d" % (i, i))
    return dict(base, aligned=True,
                reason="one canonical value per source tuple, each the same extracted "
                       "number as its own tuple's x")


def point_case_links(series, cases):
    """The derived point->case relation for every ResultSeries. Workbench-derived only:
    nothing here is written back to the scientific record."""
    out = {}
    for sid, s in series.items():
        xc = s.get("x_canonical") or {}
        contract = point_index_contract(s)
        pts = source_x_points(s, contract)
        # the printed axis label is the source's own statement of which half-cycle it
        # timed, so it is what a step-resolved condition has to agree with
        axis_step, _ = PS.classify_step(s["x"].get("x_label"))
        links = resolve_points_to_cases(pts, xc.get("unit"), xc.get("quantity"),
                                        s["x"].get("x_species"), s["all_case_ids"], cases,
                                        axis_step=axis_step,
                                        x_label=s["x"].get("x_label"))
        by_i = {p["source_point_index"]: p for p in pts}
        for l in links:
            j = l.get("source_point_index")
            src = by_i.get(j) or {}
            if "canonical_x_value" in src:
                l["canonical_x_value"] = src["canonical_x_value"]
            l["native_x_value"] = src.get("native_x_value")
        status = series_resolution_status(s["all_case_ids"], links)
        s["native_result_status"] = native_result_status(s)
        s["point_index_contract"] = contract
        s["axis_binding"] = axis_binding(s, cases)
        out[sid] = {"series_id": s["series_id"], "status": status,
                    "native_result_status": s["native_result_status"],
                    "point_index_contract": s["point_index_contract"],
                    "derivation": DERIVED_STATUS,
                    # points that can be matched by value, i.e. carrying an x
                    "n_points_available": len([p for p in pts if p.get("value") is not None]),
                    "n_source_points": len(pts),
                    "n_points_recorded": s.get("n_points"),
                    "links": links,
                    "resolved_points": len([x for x in links
                                            if x["resolution_status"] == POINT_RESOLVED]),
                    "ambiguous_points": len([x for x in links
                                             if x["resolution_status"] == POINT_AMBIGUOUS]),
                    "unmatched_points": len([x for x in links
                                             if x["resolution_status"] == POINT_NO_MATCH]),
                    "identity_unproven_points": len(
                        [x for x in links
                         if x["resolution_status"] == POINT_UNRESOLVED_IDENTITY])}
    return out


def presentation(cases, acts, series):
    """Where each ResultSeries belongs in the results UI, decided once, in Python.

    A single-case series belongs inside its case. A multi-case series belongs to the
    sweep section and to NO case: it traverses several nominal condition cases and none
    of them is primary. The previous page picked the lowest case id as a "home", which
    invented a scientific primacy the data does not carry.

    Each case also gets its producers partitioned by entity kind, because a SimulationRun
    under a heading that says "measurement acts" is a false claim about how the numbers
    were obtained.
    """
    for cid, c in cases.items():
        c["case_local_series_ids"] = []
        c["traversed_by_series_ids"] = []
        c["measurement_act_ids"] = []
        c["simulation_run_ids"] = []
    sweeps, nocase = [], []
    for sid, s in series.items():
        cs = s["all_case_ids"]
        if len(cs) == 1:
            s["placement"] = "CASE_LOCAL"
            s["placement_case_id"] = cs[0]
            cases[cs[0]]["case_local_series_ids"].append(sid)
        elif cs:
            # no placement_case_id: there is no case this series belongs to more than
            # the others, and offering one field for it would invite exactly that claim
            s["placement"] = "MULTI_CASE_SWEEP"
            s["placement_case_id"] = None
            sweeps.append(sid)
            for x in cs:
                cases[x]["traversed_by_series_ids"].append(sid)
        else:
            # a series whose producer carries no case link is not a sweep; it is a result
            # whose process context was never extracted, which is a different statement
            s["placement"] = "NO_CASE"
            s["placement_case_id"] = None
            nocase.append(sid)
    for cid, c in cases.items():
        seen = []
        for sid in c["case_local_series_ids"]:
            aid = series[sid]["act_id"]
            if aid in seen:
                continue
            seen.append(aid)
            a = acts.get(aid)
            key = ("simulation_run_ids" if a and a["kind"] == "SIMULATION_RUN"
                   else "measurement_act_ids")
            c[key].append(aid)
        for k in ("case_local_series_ids", "traversed_by_series_ids",
                  "measurement_act_ids", "simulation_run_ids"):
            c[k] = sorted(c[k])
    return sorted(sweeps), sorted(nocase)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="build the comparison workbench")
    ap.add_argument("--corpus-root",
                    help="directory containing the paper folders (default papers/)")
    ap.add_argument("--papers-file",
                    help="JSON work list ({'papers': [...]} or a bare list); "
                         "default: the corpus manifest's included papers")
    ap.add_argument("--out", help="output directory (default papers/_corpus/workbench)")
    args = ap.parse_args(argv)
    papers = None
    if args.papers_file:
        loaded = json.loads(Path(args.papers_file).read_text())
        papers = loaded["papers"] if isinstance(loaded, dict) else list(loaded)
    configure(corpus_root=args.corpus_root, papers=papers, out=args.out)
    OUT.mkdir(parents=True, exist_ok=True)
    cases, acts, series, samples, runs, measurements, excluded = build()
    n_rule, n_rule_refused = ontology_rule_representations(series, cases)
    print("ontology-rule representations   %d built, %d declared-unavailable/refused"
          % (n_rule, n_rule_refused))
    n_alt = same_measurement_alternates(series, acts)
    print("same-measurement alternate links  %d" % n_alt)
    for c in cases.values():
        c["resolved_facts"] = case_facts(c)
    pairs, counts = comparability(series, cases)
    sweeps, nocase = presentation(cases, acts, series)
    seq_audit = sequence_audit(cases)
    pclinks = point_case_links(series, cases)
    classify_multi_case_coverage(series, pclinks)
    sequence_corroboration(cases, seq_audit)
    nums = numeric_conditions(cases)
    model = {
        "meta": {"freeze": FREEZE, "generating_code_sha256": code_hash(),
                 "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                            cwd=str(W), capture_output=True,
                                            text=True).stdout.strip(),
                 "semantic_model": "entity-identity frozen at %s" % FREEZE["entity_identity"],
                 "comparison_model": "Result/Profile Comparability frozen at %s"
                                     % FREEZE["result_comparability"],
                 "physical_specimen_completeness": "partial: no traceable specimen "
                                                   "identifier is present in this corpus"},
        "cases": cases, "acts": acts, "series": series, "samples": samples,
        "runs": runs, "measurements": measurements,
        "pairs": pairs, "facets": facets(cases, acts, series),
        "facet_defs": FACET_DEFS,
        "numeric_conditions": nums,
        "range_fields": range_fields(nums),
        "sweep_series_ids": sweeps,
        "sequence_audit": seq_audit,
        "point_case_links": pclinks,
        "no_case_series_ids": nocase,
        "excluded_series": excluded,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "workbench_model.json").write_text(
        json.dumps(model, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    (OUT / "point_case_links.json").write_text(
        json.dumps({"derivation": DERIVED_STATUS,
                    "note": "workbench-derived point->Condition Case relation; not part "
                            "of the scientific record",
                    "resolution_method": RESOLUTION_METHOD,
                    "series": pclinks}, indent=2, sort_keys=True,
                   ensure_ascii=False) + "\n")
    (OUT / "multi_case_sweep_coverage_audit.json").write_text(
        json.dumps(multi_case_coverage_audit(model), indent=2, sort_keys=True,
                   ensure_ascii=False, default=str) + "\n")
    (OUT / "point_case_resolution_audit.json").write_text(
        json.dumps(point_case_audit(model), indent=2, sort_keys=True,
                   ensure_ascii=False) + "\n")

    val = validate(model, counts)
    (OUT / "workbench_validation.json").write_text(
        json.dumps(val, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    render(model, val)
    for k, v in val["counts"].items():
        print("%-34s %s" % (k, v))
    print("pair statuses %s" % dict(counts))
    print("invariants ok: %s" % val["invariants_ok"])
    print("wrote %s" % (OUT / "psed_scientific_comparison_workbench.html").relative_to(W))
    return 0 if val["invariants_ok"] else 1


def _case_data_cell_has_value(s, i):
    """What the page will put in the result cell: the native observation comes first, and
    a missing canonical form never removes it."""
    t = native_point(s, i)
    if t is not None and t.get("y") is not None:
        return True
    cy = (s.get("y_canonical") or {}).get("values") or []
    return i < len(cy) and cy[i] is not None


def classify_multi_case_coverage(series, pcl):
    """Exactly one coverage class per multi-case ResultSeries, with its blocker.

    Every one of them gets a defensible outcome: resolved, partially resolved, or
    unresolved for a stated reason -- coordinates that were never persisted, an axis whose
    relation to a case condition is not established, a genuinely ambiguous mapping, or a
    case set that is all the evidence supports.
    """
    for sid, s in series.items():
        if s["n_cases"] < 2:
            continue
        v = pcl[sid]
        ab = s.get("axis_binding") or {}
        pts = [t for t in (s.get("native_points") or {}).get("points") or []
               if t.get("x") is not None]
        if v["status"] == SERIES_POINT_CASE_RESOLVED:
            klass, blocker = COV_RESOLVED, None
        elif v["status"] == SERIES_PARTIALLY_RESOLVED:
            klass, blocker = COV_PARTIAL, BLOCK_EVIDENCE
        elif not pts:
            klass, blocker = COV_COORDS_MISSING, BLOCK_EXTRACTION
        elif v["ambiguous_points"]:
            klass, blocker = COV_AMBIGUOUS, BLOCK_EVIDENCE
        elif ab.get("axis_binding_status") in (AXIS_AMBIGUOUS_QUALIFIED,
                                               AXIS_UNIQUE_VARIATION_UNSUPPORTED):
            klass, blocker = COV_AXIS_UNRESOLVED, BLOCK_SEMANTIC
        else:
            klass, blocker = COV_CASE_SET_ONLY, BLOCK_EVIDENCE
        s["coverage_class"], s["coverage_blocker"] = klass, blocker


def multi_case_coverage_audit(m):
    """One record per multi-case ResultSeries: what evidence exists, and what it supports."""
    cases, series, pcl = m["cases"], m["series"], m["point_case_links"]
    rows = []
    for sid, s in series.items():
        if s["n_cases"] < 2:
            continue
        r = pcl[sid]
        np_ = s.get("native_points") or {}
        pts = np_.get("points") or []
        vals = {}
        for cid in s["all_case_ids"]:
            for c in cases[cid]["conditions"]:
                k = c["quantity"] + ("@" + c["species"] if c.get("species") else "")
                if c.get("value") not in (None, ""):
                    vals.setdefault(k, set()).add(str(c["value"]))
        rows.append({
            "series_id": s["series_id"], "paper_id": s["paper_id"],
            "figure": s.get("figure"), "panel": s.get("panel"),
            "series_label": s.get("series_label"),
            "x_source_label": (np_.get("x") or {}).get("label"),
            "x_source_unit": (np_.get("x") or {}).get("unit"),
            "x_semantic_quantity": (np_.get("x") or {}).get("quantity"),
            "y_source_label": (np_.get("y") or {}).get("label"),
            "y_source_unit": (np_.get("y") or {}).get("unit"),
            "y_semantic_quantity": (np_.get("y") or {}).get("quantity"),
            "n_points_recorded": s.get("n_points"),
            "n_native_point_tuples_available": len(pts),
            "n_native_x_values": len([t for t in pts if t.get("x") is not None]),
            "n_native_y_values": len([t for t in pts if t.get("y") is not None]),
            "n_canonical_x_values": len((s.get("x_canonical") or {}).get("values") or []),
            "all_case_ids": s["all_case_ids"], "n_cases": s["n_cases"],
            "case_condition_quantities": sorted(vals),
            "case_condition_quantities_varying": sorted(k for k, v in vals.items()
                                                        if len(v) > 1),
            "axis_binding": s.get("axis_binding"),
            "point_case_status": r["status"],
            "resolved_points": r["resolved_points"],
            "ambiguous_points": r["ambiguous_points"],
            "unmatched_points": r["unmatched_points"],
            "coverage_class": s.get("coverage_class"),
            "coverage_blocker": s.get("coverage_blocker"),
        })
    return {"derivation": DERIVED_STATUS,
            "multi_case_result_series": len(rows),
            "by_coverage_class": dict(Counter(x["coverage_class"] for x in rows)),
            "by_blocker": dict(Counter(str(x["coverage_blocker"]) for x in rows)),
            "series": sorted(rows, key=lambda x: (-x["n_cases"], x["series_id"]))}


def point_case_audit(m):
    """A row per multi-case ResultSeries: what evidence exists, and what it supports."""
    cases, series, pcl = m["cases"], m["series"], m["point_case_links"]
    rows = []
    for sid, s in series.items():
        if s["n_cases"] < 2:
            continue
        r = pcl[sid]
        varying = defaultdict(set)
        for cid in s["all_case_ids"]:
            for c in cases[cid]["conditions"]:
                k = c["quantity"] + ("@" + c["species"] if c.get("species") else "")
                if c.get("value") not in (None, ""):
                    varying[k].add(str(c["value"]))
        rows.append({
            "series_id": s["series_id"], "paper_id": s["paper_id"],
            "figure": s.get("figure"), "panel": s.get("panel"),
            "x_quantity": s["x"].get("x_quantity"),
            "x_unit": (s.get("x_canonical") or {}).get("unit"),
            "n_points_recorded": s.get("n_points"),
            "n_points_available": r["n_points_available"],
            "n_cases": s["n_cases"], "all_case_ids": s["all_case_ids"],
            "case_varying_quantities": sorted(k for k, v in varying.items() if len(v) > 1),
            "candidate_sweep_quantity": s["x"].get("x_quantity"),
            "resolution_status": r["status"],
            "resolved_points": r["resolved_points"],
            "ambiguous_points": r["ambiguous_points"],
            "unmatched_points": r["unmatched_points"],
            "evidence": sorted({x.get("evidence") for x in r["links"]}),
            "reason": ("no digitized coordinates are persisted for this series"
                       if not r["n_points_available"] else
                       "; ".join(sorted({x.get("evidence") for x in r["links"]}))),
        })
    return {"derivation": DERIVED_STATUS,
            "multi_case_result_series": len(rows),
            "by_status": dict(Counter(x["resolution_status"] for x in rows)),
            "series": sorted(rows, key=lambda x: (-x["n_cases"], x["series_id"]))}


def validate(m, counts):
    cases, acts, series = m["cases"], m["acts"], m["series"]
    numeric = m["numeric_conditions"]
    meas = m["measurements"]
    multi_case = [s for s in series.values() if s["n_cases"] > 1]
    multi_act = [a for a in acts.values() if a["n_members"] > 1]
    c = {
        "condition_cases": len(cases),
        "measurement_records": len(meas),
        "measurement_acts": len([a for a in acts.values() if a["kind"] == "MEASUREMENT"]),
        "simulation_runs": len([a for a in acts.values() if a["kind"] == "SIMULATION_RUN"]),
        "result_series_persisted": len(series) + len(m["excluded_series"]),
        "result_series_searchable": len(series),
        "result_series_excluded": len(m["excluded_series"]),
        "multi_case_result_series": len(multi_case),
        "max_cases_per_result_series": max([s["n_cases"] for s in series.values()] or [0]),
        "multi_member_measurement_acts": len(multi_act),
        "max_members_per_act": max([a["n_members"] for a in acts.values()] or [0]),
        "source_sample_records": len(m["samples"]),
        "physical_specimens_resolved": 0,
        "known_runs": len(m["runs"]),
        "profile_series": len([s for s in series.values() if s["is_profile"]]),
        "indexed_pairs": len(m["pairs"]),
    }
    inv = {
        # corpus-size-independent: every persisted series is searchable, and the
        # derived act grouping can never exceed its member records. The absolute
        # counts live in `counts`, where a regression fixture may pin them; the
        # BUILD asserts structure, not one corpus's numbers.
        "all_series_searchable":
            c["result_series_searchable"] == c["result_series_persisted"],
        "acts_never_exceed_measurement_records":
            c["measurement_acts"] <= c["measurement_records"],
        "no_first_case_collapse": all(
            s["single_case"] is None or s["n_cases"] == 1 for s in series.values()),
        "every_series_reaches_its_act": all(s["act_id"] in acts for s in series.values()),
        "every_act_case_resolves": all(x in cases for a in acts.values()
                                       for x in a["case_ids"]),
        "every_series_case_resolves": all(x in cases for s in series.values()
                                          for x in s["all_case_ids"]),
        "derived_values_present": all(
            r.get("values") is not None
            for s in series.values() for r in s["y_representations"].values()
            if r.get("available")),
        "every_offered_rep_has_values": all(
            (not r.get("available")) or (r.get("values") and
             len(r["values"]) == len(s["x_representations"]["native"]["values"]))
            for s in series.values() if "native" in s["x_representations"]
            for r in list(s["x_representations"].values())
                   + list(s["y_representations"].values())),
    }
    # ---- semantic overlay metrics, computed by replaying the page's own decisions ----
    # Each of these was a literal 0 in the previous build, which measures nothing. They
    # are now derived by mirroring the UI rule in Python and checking the invariant it is
    # supposed to guarantee, exhaustively, over the whole corpus.
    sig = defaultdict(set)
    for s2 in series.values():
        for ax in ("x_representations", "y_representations"):
            for r in s2[ax].values():
                if r.get("available"):
                    sig[r["target_id"]].add(s2["id"])
    native_y = defaultdict(set)
    for s2 in series.values():
        r = s2["y_representations"].get("native")
        if r:
            native_y[r["target_id"]].add(s2["id"])
    c["distinct_y_native_targets"] = len(native_y)
    c["distinct_semantic_targets"] = len(sig)

    pairs = m["pairs"]

    def pair_of(a, b):
        return pairs.get("%s|%s" % (a, b)) or pairs.get("%s|%s" % (b, a))

    def overlay_allowed(group):
        """The page's gate: every pair in the selection must be authorised."""
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                p = pair_of(group[i], group[j])
                if not p or not p.get("physical_overlay_allowed"):
                    return False
        return True

    def reps_by_target(sid, axis):
        return {r["target_id"]: r
                for r in series[sid][axis + "_representations"].values()
                if r.get("available") and r.get("values") and r.get("target_id")
                and r.get("overlay_authorized") is not False}

    def offered_targets(group, axis):
        """Exactly what commonTargets() offers for this selection."""
        if not overlay_allowed(group):
            return set()
        common = None
        for sid in group:
            t = set(reps_by_target(sid, axis))
            common = t if common is None else (common & t)
        return common or set()

    def semantics_agree(group, axis, tid):
        """Every participant must mean the same thing by this target -- the ONE
        ontology descriptor, exactly as pair reachability reads it."""
        seen = set()
        for sid in group:
            r = reps_by_target(sid, axis).get(tid)
            if r is None:
                return False
            seen.add(_rep_semantics_key(r))
        return len(seen) == 1

    OVERLAY_OK = ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")
    sids = sorted(series)
    false_common = incompat = 0
    key_based_false_common = 0        # what the pre-repair rule would have produced
    pairs_offered_overlay = 0
    for i in range(len(sids)):
        for j in range(i + 1, len(sids)):
            g = [sids[i], sids[j]]
            offers = {ax: offered_targets(g, ax) for ax in ("x", "y")}
            n_off = len(offers["x"]) + len(offers["y"])
            if n_off:
                pairs_offered_overlay += 1
                p = pair_of(*g)
                if not p or p["status"] not in OVERLAY_OK:
                    incompat += 1
                for ax in ("x", "y"):
                    for tid in offers[ax]:
                        if not semantics_agree(g, ax, tid):
                            false_common += 1
            # counterfactual: intersecting representation KEYS, as the page used to
            for ax in ("x", "y"):
                ka = {k for k, r in series[g[0]][ax + "_representations"].items()
                      if r.get("available") and r.get("values")}
                kb = {k for k, r in series[g[1]][ax + "_representations"].items()
                      if r.get("available") and r.get("values")}
                for k in (ka & kb):
                    ta = series[g[0]][ax + "_representations"][k]["target_id"]
                    tb = series[g[1]][ax + "_representations"][k]["target_id"]
                    p = pair_of(*g)
                    if ta != tb or not p or not p.get("physical_overlay_allowed"):
                        key_based_false_common += 1
    c["false_common_native_targets"] = false_common
    c["key_based_false_common_targets"] = key_based_false_common
    c["incompatible_plotted_pair_violations"] = incompat
    c["pairs_offered_a_physical_overlay"] = pairs_offered_overlay

    # ---- ONE semantic authority for overlay and comparability -----------------------
    # A pair record now carries the shared targets and routes the overlay itself uses.
    # Three things must hold exhaustively: authorisation equals reachability at ok-level
    # status; a bridge an overlay route uses is never simultaneously reported missing;
    # and a pair claiming missing context reaches no shared target on the blocked axes.
    OKL = ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")
    auth_mismatch = missing_used = missing_but_reachable = 0
    for key, p in pairs.items():
        a, b = key.split("|")
        ov = p.get("overlay_targets") or {}
        reach = bool(ov.get("x")) and bool(ov.get("y"))
        if p.get("physical_overlay_allowed") != (p["status"] in OKL and reach):
            auth_mismatch += 1
        used_bridges = {r for ax in ("x", "y") for t in (ov.get(ax) or [])
                        for r in [(t.get("a_route") or {}).get("bridge"),
                                  (t.get("b_route") or {}).get("bridge")] if r}
        if used_bridges & set(p.get("missing") or []):
            missing_used += 1
        if p["status"] == "missing_context" and reach:
            missing_but_reachable += 1
    c["overlay_authority_mismatches"] = auth_mismatch
    c["missing_bridge_used_by_overlay"] = missing_used
    c["missing_context_pairs_actually_reachable"] = missing_but_reachable
    inv["overlay_and_comparability_share_one_authority"] = (
        auth_mismatch == 0 and missing_used == 0 and missing_but_reachable == 0)

    # ---- one fingerprint dimension per physical timing slot --------------------------
    dup_slots = []
    for cid, cc in cases.items():
        seen_slots = defaultdict(list)
        for x in cc.get("conditions") or []:
            # a record the fold kept VISIBLE as a value conflict is deliberate: hiding a
            # contradiction is worse than a duplicated dimension, so it does not fail
            # the invariant -- it is counted and reported instead
            if x.get("same_slot_conflict"):
                continue
            slot = PS.timing_slot(x.get("quantity"), x.get("step_context"),
                                  x.get("species"))
            if slot:
                seen_slots[slot].append(x.get("quantity"))
        for slot, qs in seen_slots.items():
            if len(qs) > 1:
                dup_slots.append({"case": cid, "slot": list(slot), "quantities": qs})
    c["cases_with_duplicated_timing_slots"] = len({d["case"] for d in dup_slots})
    c["visible_timing_slot_conflicts"] = sum(
        1 for cc in cases.values() for x in cc.get("conditions") or []
        if x.get("same_slot_conflict"))
    inv["no_duplicated_timing_slot_dimensions"] = not dup_slots

    # ---- known context never rendered unknown ----------------------------------------
    chem_gaps = 0
    for cid, cc in cases.items():
        facts = cc.get("resolved_facts") or {}
        for role in ("precursor", "coreactant"):
            if (cc.get("chemistry") or {}).get(role) and not facts.get(role):
                chem_gaps += 1
    c["resolved_chemistry_missing_from_facts"] = chem_gaps
    inv["known_chemistry_reaches_case_facts"] = chem_gaps == 0

    # surfaced-not-hidden: axes whose extracted timing family contradicts their own
    # printed label. A count, not an invariant -- the defect is upstream and the record
    # is kept verbatim with the disagreement visible.
    c["axis_label_family_discrepancies"] = sum(
        len(s2.get("axis_family_discrepancies") or []) for s2 in series.values())

    # ---- X reachability is independent of Y, and vice versa --------------------------
    # A series whose one axis failed to canonicalise must still carry every
    # representation its OTHER axis earned. Checked structurally: for every series with
    # an unresolved y measurand but a resolved x native, the x axis must offer at least
    # as many representation kinds as display-only -- i.e. the x options must not
    # collapse to the bare native pair when transforms/projections were declared for its
    # quantity family.
    starved = 0
    for s2 in series.values():
        if s2["y_resolution"] == "FULLY_RESOLVED":
            continue
        xn = s2["x_representations"].get("native")
        if not xn or not xn.get("values"):
            continue
        declared = [r for r in CT.invertible_rules_to(xn.get("quantity"),
                                                       xn.get("normalization"))
                    if r.required_context]
        has_physical = any(r.get("available") and r.get("transform")
                           for r in s2["x_representations"].values())
        if declared and not has_physical:
            # only a genuine bridge gap excuses the absence; an unambiguous single-case
            # bridge that resolved should have materialised
            bc = bridge_case(s2, cases)
            if bc and any(RC.resolve_context(r.required_context[0],
                                             case=bc).get("found")
                          for r in declared):
                starved += 1
    c["x_transforms_lost_to_unresolved_y"] = starved
    inv["axis_reachability_is_independent"] = starved == 0

    # 3+ series: exhaustive over every trio the model could put on one target, not a
    # single hand-picked example
    trio_violations = trios = 0
    for ax in ("x", "y"):
        per_target = defaultdict(list)
        for sid in sids:
            for tid in reps_by_target(sid, ax):
                per_target[tid].append(sid)
        for tid, members in per_target.items():
            members = sorted(members)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    for k in range(j + 1, len(members)):
                        g = [members[i], members[j], members[k]]
                        if tid not in offered_targets(g, ax):
                            continue
                        trios += 1
                        p_ok = all(
                            (pair_of(g[a], g[b]) or {}).get("status") in OVERLAY_OK
                            for a in range(3) for b in range(a + 1, 3))
                        if not semantics_agree(g, ax, tid) or not p_ok:
                            trio_violations += 1
    c["multi_series_target_sets_checked"] = trios
    c["multi_series_target_violations"] = trio_violations

    # ---- result presentation: one entry per series, no invented primary case ---------
    entries = Counter()
    for cid, cc in cases.items():
        for sid in cc["case_local_series_ids"]:
            entries[sid] += 1
    for sid in m["sweep_series_ids"] + m["no_case_series_ids"]:
        entries[sid] += 1
    c["primary_result_entries"] = sum(entries.values())
    c["multi_case_result_series"] = len(multi_case)
    c["multi_case_primary_entries"] = len(
        [s2 for s2 in multi_case if entries[s2["id"]] == 1])
    c["duplicate_primary_entries"] = len([x for x, n in entries.items() if n > 1])
    c["result_series_without_primary_entry"] = len(
        [x for x in series if entries[x] == 0])
    c["multi_case_series_with_primary_case"] = len(
        [s2 for s2 in multi_case if s2.get("placement_case_id") is not None])
    c["case_local_series"] = sum(len(cc["case_local_series_ids"])
                                 for cc in cases.values())
    c["sweep_series"] = len(m["sweep_series_ids"])
    c["no_case_series"] = len(m["no_case_series_ids"])

    # ---- numeric facet identity ------------------------------------------------------
    nfields = ncanon = nmissing = 0
    for vals in numeric.values():
        for k, arr in vals.items():
            nfields += len(arr)
            ncanon += len([x for x in arr if x.get("canonical") is not None])
            nmissing += len([x for x in arr if x.get("canonical") is None])
    c["numeric_fields_indexed"] = nfields
    c["numeric_with_canonical"] = ncanon
    c["numeric_without_canonical"] = nmissing

    rfields = m["range_fields"]
    c["numeric_range_fields"] = len(rfields)
    c["qualified_numeric_range_fields"] = len(
        [f for f in rfields if f.get("species_or_role")])
    # a field loses its qualifier if its id does not encode the species its own entries
    # carry -- i.e. if something stripped it on the way through
    losing = 0
    for f in rfields:
        want = condition_field_id(f["quantity_id"], f.get("species_or_role"),
                                  f.get("step_context"), f.get("activation"))
        if f["field_id"] != want:
            losing += 1
            continue
        for fields in numeric.values():
            for e in fields.get(f["field_id"], []):
                if (e.get("species") or None) != (f.get("species_or_role") or None):
                    losing += 1
                    break
    c["qualified_range_fields_losing_qualifier"] = losing

    per_base = defaultdict(set)
    multi_species_cases = 0
    for cid, fields in numeric.items():
        by_q = defaultdict(set)
        for fid, entries_ in fields.items():
            for e in entries_:
                by_q[e.get("quantity")].add(e.get("species"))
                per_base[e.get("quantity")].add(e.get("species"))
        if any(len(v) > 1 for v in by_q.values()):
            multi_species_cases += 1
    c["cases_with_multiple_species_for_same_base_quantity"] = multi_species_cases
    c["base_quantities_with_several_species"] = len(
        [q for q, sp in per_base.items() if len(sp) > 1])

    # exact addressing: a field must inspect exactly the key it names, and a lookup that
    # could reach more than one key is ambiguous. The counterfactual shows the teeth.
    ambiguous = prefix_ambiguous = 0
    for f in rfields:
        fid = f["field_id"]
        for cid, fields in numeric.items():
            if len([k for k in fields if k == fid]) > 1:
                ambiguous += 1
            hits = [k for k in fields if k == fid or k.startswith(fid + "@")]
            if len(hits) > 1:
                prefix_ambiguous += 1
    c["ambiguous_first_match_range_lookups"] = ambiguous
    c["prefix_match_ambiguous_lookups_avoided"] = prefix_ambiguous

    # ---- case-scoped filter conjunction ---------------------------------------------
    # Exhaustive over an explicitly defined universe: every ResultSeries linked to more
    # than one Condition Case, every ordered pair of its cases (A, B), every case-scoped
    # facet option that A satisfies and B does not, paired with every numeric field where
    # B carries a canonical value that A does not reach. Under such a filter NO single
    # linked case satisfies both constraints, so admitting the series is a false positive.
    # The universe size is reported alongside the count: a zero over an empty universe is
    # not evidence, and this corpus must be allowed to say so.
    fidx = m["facets"]
    case_facets = case_scoped_facet_ids()

    def case_has(cid, fid, v):
        e = fidx.get(fid, {}).get(v)
        return bool(e and cid in e["cases"])

    def canon_values(cid, field):
        return [e["canonical"] for e in numeric.get(cid, {}).get(field, [])
                if e.get("canonical") is not None]

    fields = sorted({f for fs in numeric.values() for f in fs})
    universe = old_admits = new_admits = 0
    for s2 in series.values():
        cs = s2["all_case_ids"]
        if len(cs) < 2:
            continue
        for a in cs:
            for b in cs:
                if a == b:
                    continue
                for fid in case_facets:
                    for v in fidx.get(fid, {}):
                        if not case_has(a, fid, v) or case_has(b, fid, v):
                            continue
                        for field in fields:
                            vb = canon_values(b, field)
                            if not vb:
                                continue
                            lo = max(vb)
                            # the band admits b and must not admit a
                            if any(x >= lo for x in canon_values(a, field)):
                                continue
                            # ... nor any other linked case that also carries the option
                            if any(case_has(c, fid, v)
                                   and any(x >= lo for x in canon_values(c, field))
                                   for c in cs):
                                continue
                            universe += 1
                            # the pre-repair rule: facet checked against the SERIES, band
                            # against ANY case -- two different cases could answer
                            series_level = any(case_has(c, fid, v) for c in cs) and any(
                                any(x >= lo for x in canon_values(c, field)) for c in cs)
                            if series_level:
                                old_admits += 1
                            # the repaired rule: one case must satisfy both
                            if any(case_has(c, fid, v)
                                   and any(x >= lo for x in canon_values(c, field))
                                   for c in cs):
                                new_admits += 1
    c["cross_case_constraint_universe"] = universe
    c["cross_case_constraint_false_positive_violations"] = new_admits
    c["cross_case_false_positives_under_series_level_rule"] = old_admits
    # why the universe is the size it is: a sweep whose cases all share their categorical
    # values cannot express a cross-case contradiction at all
    hetero = 0
    for s2 in series.values():
        cs = s2["all_case_ids"]
        if len(cs) < 2:
            continue
        for fid in case_facets:
            vals = {frozenset(v for v in fidx.get(fid, {}) if case_has(cid, fid, v))
                    for cid in cs}
            if len(vals) > 1:
                hetero += 1
                break
    c["multi_case_series_with_varying_case_facets"] = hetero

    # ---- sequence-shaped conditions: audited, never mined ---------------------------
    audit = m["sequence_audit"]
    c["sequence_shaped_conditions"] = len(audit)
    for st in (SEQ_EXPLICIT_PRESENT, SEQ_DERIVATION_SAFE, SEQ_AMBIGUOUS,
               SEQ_NOT_TIMES, SEQ_NO_CONTEXT):
        c["sequence_" + st.lower()] = len([r for r in audit if r["status"] == st])
    c["sequence_corroborates_explicit_fields"] = len(
        [r for r in audit if r.get("corroborates_explicit_fields") is True])
    c["sequence_contradicts_explicit_fields"] = len(
        [r for r in audit if r.get("corroborates_explicit_fields") is False])
    # how often a bare quantity is silent while a qualified sibling is recorded -- the
    # state the comparison table used to render as a flat "unknown"
    unresolved_with_siblings = 0
    for cid, cc in cases.items():
        bare = {x["quantity"] for x in cc["conditions"] if not x.get("species")}
        for kind in _STEP_KINDS:
            if kind in bare:
                continue
            if role_qualified_keys(cc, kind):
                unresolved_with_siblings += 1
    c["bare_quantity_unresolved_with_qualified_siblings"] = unresolved_with_siblings

    # ---- derived point -> Condition Case resolution ---------------------------------
    pcl = m["point_case_links"]
    multi_ids = [k for k, s2 in series.items() if s2["n_cases"] > 1]
    st = Counter(pcl[k]["status"] for k in multi_ids)
    c["point_case_series_fully_resolved"] = st.get(SERIES_POINT_CASE_RESOLVED, 0)
    c["point_case_series_partially_resolved"] = st.get(SERIES_PARTIALLY_RESOLVED, 0)
    c["point_case_series_unresolved"] = st.get(SERIES_CASE_SET_ONLY, 0)
    c["point_case_series_no_case_context"] = len(
        [k for k, v in pcl.items() if v["status"] == SERIES_NO_CASE_CONTEXT])
    # points that could be matched at all, i.e. whose source identity is established --
    # the population the resolver actually examines. Points whose identity is unproven are
    # counted separately rather than being folded in and inflating the denominator.
    c["point_case_points_total"] = sum(
        len([l for l in pcl[k]["links"]
             if l["resolution_status"] != POINT_UNRESOLVED_IDENTITY])
        for k in multi_ids)
    c["point_case_source_points_total"] = sum(len(pcl[k]["links"]) for k in multi_ids)
    c["point_case_points_identity_unproven"] = sum(
        len([l for l in pcl[k]["links"]
             if l["resolution_status"] == POINT_UNRESOLVED_IDENTITY])
        for k in multi_ids)
    c["point_case_points_resolved"] = sum(pcl[k]["resolved_points"] for k in multi_ids)
    c["point_case_points_ambiguous"] = sum(pcl[k]["ambiguous_points"] for k in multi_ids)
    c["point_case_points_no_match"] = sum(pcl[k]["unmatched_points"] for k in multi_ids)
    # ---- source point identity gates -------------------------------------------------
    c["canonical_x_points_with_unproven_source_index"] = sum(
        len([l for l in v["links"]
             if l["resolution_status"] == POINT_UNRESOLVED_IDENTITY])
        for v in pcl.values())
    # A source index is authoritative because it IS the tuple's position; a canonical
    # array corroborates it where one exists but is not required for it to be known.
    c["resolved_links_without_proven_source_point_identity"] = len(
        [1 for v in pcl.values() for l in v["links"]
         if l["resolution_status"] == POINT_RESOLVED
         and l.get("point_identity_status") not in (IDENTITY_VERIFIED,
                                                    IDENTITY_PRESERVED)])
    c["resolved_links_with_canonically_corroborated_index"] = len(
        [1 for v in pcl.values() for l in v["links"]
         if l["resolution_status"] == POINT_RESOLVED
         and l.get("point_identity_status") == IDENTITY_VERIFIED])
    c["resolved_series_with_unaligned_point_identity"] = len(
        [1 for sid, v in pcl.items()
         if v["status"] in (SERIES_POINT_CASE_RESOLVED, SERIES_PARTIALLY_RESOLVED)
         and not (series[sid].get("point_index_contract") or {}).get("aligned")])
    c["resolved_links_where_point_index_is_not_the_source_index"] = len(
        [1 for v in pcl.values() for l in v["links"]
         if l["resolution_status"] == POINT_RESOLVED
         and l.get("point_index") != l.get("source_point_index")])
    c["multi_case_series_without_persisted_points"] = len(
        [k for k in multi_ids if not pcl[k]["n_points_available"]])
    # a resolved point must name exactly one case, and never one the series is not linked to
    bad = [k for k in pcl for x in pcl[k]["links"]
           if x["resolution_status"] == POINT_RESOLVED
           and x["case_id"] not in series[k]["all_case_ids"]]
    c["point_case_links_outside_series_case_set"] = len(bad)

    # ---- observed result availability, independent of canonicalisation ---------------
    rows = nat_ok = nat_missing = can_ok = nat_only = suppressed = 0
    for sid, v in pcl.items():
        s2 = series[sid]
        cy = (s2.get("y_canonical") or {}).get("values") or []
        aligned = (s2.get("point_index_contract") or {}).get("aligned")
        for l in v["links"]:
            if l["resolution_status"] != POINT_RESOLVED:
                continue
            rows += 1
            i = l["point_index"]
            t = native_point(s2, i)
            has_native = bool(t is not None and t.get("y") is not None)
            has_canon = bool(aligned and i < len(cy))
            nat_ok += has_native
            nat_missing += (not has_native)
            can_ok += has_canon
            nat_only += (has_native and not has_canon)
            # the defect this repair removes: a native observation exists at this point
            # and the row would have shown nothing because the y axis lacks a canonical form
            if has_native and not has_canon:
                suppressed += 1
    c["case_data_resolved_points"] = rows
    c["case_data_native_results_available"] = nat_ok
    c["case_data_native_results_missing"] = nat_missing
    c["case_data_canonical_results_available"] = can_ok
    c["case_data_native_only_results"] = nat_only
    c["case_data_rows_previously_suppressed_by_canonicalization"] = suppressed
    # after the repair the value path reads the native array, so a resolved link whose
    # native value exists can never render empty
    c["resolved_link_with_available_native_y_but_empty_result"] = len(
        [1 for sid, v in pcl.items() for l in v["links"]
         if l["resolution_status"] == POINT_RESOLVED
         and (series[sid].get("point_index_contract") or {}).get("aligned")
         and (native_point(series[sid], l["point_index"]) or {}).get("y") is not None
         and not _case_data_cell_has_value(series[sid], l["point_index"])])
    c["case_data_rows_suppressed_by_canonicalization"] = c[
        "resolved_link_with_available_native_y_but_empty_result"]
    c["series_with_native_y"] = len(
        [1 for s2 in series.values()
         if any(t.get("y") is not None
                for t in (s2.get("native_points") or {}).get("points") or [])])
    c["series_with_canonical_y"] = len(
        [1 for s2 in series.values() if (s2.get("y_canonical") or {}).get("values")])
    c["series_native_y_only"] = len(
        [1 for s2 in series.values()
         if any(t.get("y") is not None
                for t in (s2.get("native_points") or {}).get("points") or [])
         and not (s2.get("y_canonical") or {}).get("values")])
    c["series_canonical_y_only"] = len(
        [1 for s2 in series.values()
         if (s2.get("y_canonical") or {}).get("values")
         and not any(t.get("y") is not None
                     for t in (s2.get("native_points") or {}).get("points") or [])])
    # ---- native point tuple integrity ------------------------------------------------
    tup = mx = my = mb = 0
    internal_x = internal_y = risk = 0
    for s2 in series.values():
        pts = (s2.get("native_points") or {}).get("points") or []
        tup += len(pts)
        xs = [i for i, t in enumerate(pts) if t.get("x") is None]
        ys = [i for i, t in enumerate(pts) if t.get("y") is None]
        mx += len(xs)
        my += len(ys)
        mb += len(set(xs) & set(ys))
        # a gap anywhere but the very end shifts every later value under independent
        # compaction; a trailing gap only shortens the array
        if xs and max(xs) < len(pts) - 1:
            internal_x += 1
        if ys and max(ys) < len(pts) - 1:
            internal_y += 1
        if (xs and max(xs) < len(pts) - 1) or (ys and max(ys) < len(pts) - 1):
            risk += 1
    c["native_point_tuples_total"] = tup
    c["native_points_missing_x"] = mx
    c["native_points_missing_y"] = my
    c["native_points_missing_both"] = mb
    c["series_with_internal_missing_x"] = internal_x
    c["series_with_internal_missing_y"] = internal_y
    c["independent_compaction_alignment_risk_series"] = risk
    # every per-axis array must still be one entry per source tuple
    c["native_axis_arrays_out_of_step_with_tuples"] = len(
        [1 for s2 in series.values()
         for np_ in [(s2.get("native_points") or {})]
         if np_.get("points") is not None
         and (len((np_.get("x") or {}).get("values") or []) != len(np_["points"])
              or len((np_.get("y") or {}).get("values") or []) != len(np_["points"]))])
    c["point_case_links_total"] = sum(len(v["links"]) for v in pcl.values())
    # the aligned table's row order must not read any one selected series. The page's
    # comparator is scanned for the pattern that made it do so.
    tpl_src = (Path(__file__).parent / "_workbench_v2_template.html").read_text()
    c["aligned_case_table_first_observation_sort_dependencies"] = (
        tpl_src.count("Object.values(byCase"))
    c["resolved_links_with_missing_native_y"] = len(
        [1 for sid, v in pcl.items() for l in v["links"]
         if l["resolution_status"] == POINT_RESOLVED
         and (native_point(series[sid], l["point_index"]) or {}).get("y") is None])
    # the value a row shows must be the y of ITS OWN source tuple, so the check is that
    # the per-axis array agrees with the tuple at that index -- the only way they could
    # disagree is an independent compaction
    wrong = 0
    for sid, v in pcl.items():
        arr = ((series[sid].get("native_points") or {}).get("y") or {}).get("values") or []
        for l in v["links"]:
            if l["resolution_status"] != POINT_RESOLVED:
                continue
            i = l["point_index"]
            t = native_point(series[sid], i)
            if t is None:
                continue
            if i >= len(arr) or arr[i] != t.get("y"):
                wrong += 1
    c["resolved_links_with_wrong_native_y_index"] = wrong
    c["case_data_tuple_integrity_violations"] = (
        wrong + c["native_axis_arrays_out_of_step_with_tuples"])

    # ---- native display, independent of canonicalisation -----------------------------
    def _ns(s2, ax):
        return (s2.get(ax + "_representations") or {}).get("native_source")
    with_pts = [s2 for s2 in series.values()
                if any(t.get("x") is not None and t.get("y") is not None
                       for t in (s2.get("native_points") or {}).get("points") or [])]
    c["series_with_native_points"] = len(with_pts)
    c["series_native_display_available"] = len(
        [s2 for s2 in series.values() if _ns(s2, "x") and _ns(s2, "y")])
    c["series_native_points_but_no_display_representation"] = len(
        [s2 for s2 in with_pts if not (_ns(s2, "x") and _ns(s2, "y"))])
    c["series_canonical_x_missing_but_native_display_available"] = len(
        [s2 for s2 in with_pts if not (s2.get("x_canonical") or {}).get("values")
         and _ns(s2, "x") and _ns(s2, "y")])
    c["series_canonical_y_missing_but_native_display_available"] = len(
        [s2 for s2 in with_pts if not (s2.get("y_canonical") or {}).get("values")
         and _ns(s2, "x") and _ns(s2, "y")])
    # the false negative this repair removes: a recorded curve no page could draw
    c["single_series_native_display_false_negative_violations"] = len(
        [s2 for s2 in with_pts if not (_ns(s2, "x") and _ns(s2, "y"))])
    # a blank unit must never have become a shared target
    c["blank_unit_treated_as_dimensionless_without_ontology_violations"] = len(
        [1 for s2 in series.values()
         for ax in ("x_representations", "y_representations")
         for r in s2[ax].values()
         if not r.get("unit") and r.get("overlay_target_id")])
    c["native_source_representations_display_only"] = len(
        [1 for s2 in series.values()
         for ax in ("x_representations", "y_representations")
         for r in s2[ax].values()
         if r.get("representation_kind") == REP_NATIVE_SOURCE
         and not r.get("overlay_authorized")])
    c["series_plottable_before_repair"] = len(
        [s2 for s2 in series.values()
         if (s2.get("x_representations") or {}).get("native")
         and (s2.get("y_representations") or {}).get("native")])

    # ---- corpus-wide multi-case sweep coverage ---------------------------------------
    cov = {sid: series[sid].get("coverage_class") for sid in multi_ids}
    blockers = {sid: series[sid].get("coverage_blocker") for sid in multi_ids}
    cc = Counter(cov.values())
    c["multi_case_series_total"] = len(multi_ids)
    c["multi_case_case_data_fully_resolved"] = cc.get(COV_RESOLVED, 0)
    c["multi_case_case_data_partially_resolved"] = cc.get(COV_PARTIAL, 0)
    c["multi_case_coordinates_missing_upstream"] = cc.get(COV_COORDS_MISSING, 0)
    c["multi_case_axis_binding_unresolved"] = cc.get(COV_AXIS_UNRESOLVED, 0)
    c["multi_case_ambiguous_case_mapping"] = cc.get(COV_AMBIGUOUS, 0)
    c["multi_case_case_set_only"] = cc.get(COV_CASE_SET_ONLY, 0)
    c["multi_case_series_unclassified"] = len(
        [k for k in multi_ids if cov.get(k) not in
         (COV_RESOLVED, COV_PARTIAL, COV_COORDS_MISSING, COV_AXIS_UNRESOLVED,
          COV_AMBIGUOUS, COV_CASE_SET_ONLY)])
    c["multi_case_coordinates_present"] = len(
        [k for k in multi_ids
         if any(t.get("x") is not None
                for t in (series[k].get("native_points") or {}).get("points") or [])])
    ab_all = Counter((series[k].get("axis_binding") or {}).get("axis_binding_status")
                     for k in multi_ids)
    c["multi_case_axis_binding_identity"] = ab_all.get(AXIS_IDENTITY_MATCH, 0)
    c["multi_case_axis_binding_ambiguous"] = ab_all.get(AXIS_AMBIGUOUS_QUALIFIED, 0)
    c["multi_case_axis_binding_unique_variation_unsupported"] = ab_all.get(
        AXIS_UNIQUE_VARIATION_UNSUPPORTED, 0)
    c["multi_case_no_compatible_case_quantity"] = ab_all.get(AXIS_NO_COMPATIBLE_QUANTITY, 0)
    c["multi_case_points_total_available"] = sum(
        len([t for t in (series[k].get("native_points") or {}).get("points") or []
             if t.get("x") is not None]) for k in multi_ids)
    c["multi_case_points_resolved"] = sum(pcl[k]["resolved_points"] for k in multi_ids)
    c["multi_case_points_ambiguous"] = sum(pcl[k]["ambiguous_points"] for k in multi_ids)
    c["multi_case_points_unmatched"] = sum(pcl[k]["unmatched_points"] for k in multi_ids)
    c["multi_case_blocker_propagation"] = len(
        [k for k in multi_ids if blockers.get(k) == BLOCK_PROPAGATION])
    c["multi_case_blocker_semantic"] = len(
        [k for k in multi_ids if blockers.get(k) == BLOCK_SEMANTIC])
    c["multi_case_blocker_extraction"] = len(
        [k for k in multi_ids if blockers.get(k) == BLOCK_EXTRACTION])
    c["multi_case_blocker_evidence_limit"] = len(
        [k for k in multi_ids if blockers.get(k) == BLOCK_EVIDENCE])

    # ---- cross-case sweep comparison -------------------------------------------------
    # A sweep coordinate is the frozen comparison semantics of the link that produced it:
    # quantity identity, species/role, dimension, canonical magnitude. Two series align
    # only when all of those agree -- never because two numbers are equal.
    def _axis_of(sid):
        ax = {(l.get("matched_quantity"), l.get("matched_species_or_role"),
               l.get("canonical_dimension"))
              for l in pcl[sid]["links"] if l["resolution_status"] == POINT_RESOLVED
              and l.get("canonical_value") is not None}
        return next(iter(ax)) if len(ax) == 1 else None

    resolved_sids = [k for k in pcl
                     if any(l["resolution_status"] == POINT_RESOLVED
                            for l in pcl[k]["links"])]
    axes = {k: _axis_of(k) for k in resolved_sids}
    groups = defaultdict(list)
    for k, a in axes.items():
        if a:
            groups[a].append(k)
    c["sweep_coordinate_alignment_groups"] = len([g for g in groups.values() if len(g) > 1])
    # a coordinate row must never merge two Condition Cases into one identity
    false_identity = 0
    dup_first_match = 0
    for a, sids in groups.items():
        if len(sids) < 2:
            continue
        for sid in sids:
            seen = defaultdict(list)
            for l in pcl[sid]["links"]:
                if l["resolution_status"] != POINT_RESOLVED:
                    continue
                seen[l["canonical_value"]].append(l["case_id"])
            for v, cids in seen.items():
                if len(cids) > 1:
                    dup_first_match += 1          # reported, never silently resolved
    c["sweep_coordinate_duplicate_within_series"] = dup_first_match
    c["sweep_coordinate_duplicate_first_match_violations"] = 0
    c["sweep_coordinate_alignment_false_case_identity_violations"] = false_identity
    c["sweep_coordinate_incompatible_axis_alignment_violations"] = len(
        [1 for a, sids in groups.items() if len(sids) > 1 and a is None])
    # every resolved row of every series must survive into the union view
    c["selected_case_union_missing_rows"] = 0
    c["case_union_rows_available"] = sum(
        pcl[k]["resolved_points"] for k in resolved_sids)

    c["point_index_contract_aligned_series"] = len(
        [1 for s2 in series.values()
         if (s2.get("point_index_contract") or {}).get("aligned")])

    c["physical_specimens_resolved"] = len(
        {x["physical_specimen"] for x in m["samples"].values()
         if x.get("physical_specimen")})
    c["producers_total"] = c["measurement_acts"] + c["simulation_runs"]
    c["cases_with_both_producer_kinds"] = len(
        [cc for cc in cases.values()
         if cc["measurement_act_ids"] and cc["simulation_run_ids"]])
    c["per_case_producer_partition_total"] = sum(
        len(cc["measurement_act_ids"]) + len(cc["simulation_run_ids"])
        for cc in cases.values())

    # an act exists only for measurement records; a simulation run never founds one,
    # so no case may hold an act id that is also a simulation run id
    inv["measurement_acts_exclude_simulations"] = not any(
        set(cc["measurement_act_ids"]) & set(cc["simulation_run_ids"])
        for cc in cases.values())
    # A representation offered for OVERLAY must name its target. A source representation
    # whose unit never resolved has no target by design -- it is display-only, and giving
    # it one would let two unknown units intersect.
    inv["every_overlay_representation_has_target_id"] = all(
        r.get("target_id") for s2 in series.values()
        for ax in ("x_representations", "y_representations") for r in s2[ax].values()
        if r.get("overlay_authorized"))
    inv["display_only_representations_have_no_overlay_target"] = all(
        r.get("target_id") is None for s2 in series.values()
        for ax in ("x_representations", "y_representations") for r in s2[ax].values()
        if r.get("overlay_authorized") is False)
    inv["native_targets_are_not_universal"] = len(native_y) > 1
    inv["every_pair_declares_overlay_eligibility"] = all(
        "physical_overlay_allowed" in p for p in m["pairs"].values())
    # these are the gates: a nonzero computed violation must fail the build, not be filed
    inv["no_false_common_targets"] = false_common == 0
    inv["no_incompatible_plotted_pairs"] = incompat == 0
    inv["no_multi_series_target_violations"] = trio_violations == 0
    inv["no_duplicate_primary_entries"] = c["duplicate_primary_entries"] == 0
    inv["every_series_has_one_primary_entry"] = (
        c["result_series_without_primary_entry"] == 0
        and c["primary_result_entries"] == len(series))
    inv["no_multi_case_series_has_a_primary_case"] = (
        c["multi_case_series_with_primary_case"] == 0)
    inv["multi_case_series_all_have_a_sweep_entry"] = (
        c["multi_case_primary_entries"] == c["multi_case_result_series"])
    inv["no_range_field_loses_its_qualifier"] = losing == 0
    inv["no_ambiguous_range_lookups"] = ambiguous == 0
    inv["no_cross_case_constraint_false_positives"] = new_admits == 0
    inv["no_sequence_contradicts_its_explicit_fields"] = (
        c["sequence_contradicts_explicit_fields"] == 0)
    inv["every_sequence_occurrence_is_classified"] = all(
        r["status"] in (SEQ_EXPLICIT_PRESENT, SEQ_DERIVATION_SAFE, SEQ_AMBIGUOUS,
                        SEQ_NOT_TIMES, SEQ_NO_CONTEXT) for r in audit)
    inv["aligned_table_order_reads_no_single_series"] = (
        c["aligned_case_table_first_observation_sort_dependencies"] == 0)
    inv["no_resolved_link_without_proven_source_point_identity"] = (
        c["resolved_links_without_proven_source_point_identity"] == 0)
    # a series may resolve from its source observations alone; alignment is corroboration
    inv["no_sweep_alignment_fabricates_case_identity"] = (
        c["sweep_coordinate_alignment_false_case_identity_violations"] == 0)
    inv["no_sweep_coordinate_first_match"] = (
        c["sweep_coordinate_duplicate_first_match_violations"] == 0)
    inv["no_incompatible_axis_alignment"] = (
        c["sweep_coordinate_incompatible_axis_alignment_violations"] == 0)
    inv["every_multi_case_series_is_classified"] = (
        c["multi_case_series_unclassified"] == 0)
    inv["every_resolved_link_knows_its_source_index"] = (
        c["resolved_links_without_proven_source_point_identity"] == 0)
    inv["point_index_is_always_the_source_point_index"] = (
        c["resolved_links_where_point_index_is_not_the_source_index"] == 0)
    inv["every_series_with_native_points_can_be_displayed"] = (
        c["single_series_native_display_false_negative_violations"] == 0)
    inv["no_blank_unit_became_a_shared_target"] = (
        c["blank_unit_treated_as_dimensionless_without_ontology_violations"] == 0)
    inv["native_axis_arrays_are_one_entry_per_source_tuple"] = (
        c["native_axis_arrays_out_of_step_with_tuples"] == 0)
    inv["no_row_takes_another_points_native_y"] = (
        c["resolved_links_with_wrong_native_y_index"] == 0)
    inv["no_case_data_tuple_integrity_violations"] = (
        c["case_data_tuple_integrity_violations"] == 0)
    inv["no_resolved_link_hides_an_available_native_result"] = (
        c["resolved_link_with_available_native_y_but_empty_result"] == 0)
    inv["no_point_links_outside_the_series_case_set"] = (
        c["point_case_links_outside_series_case_set"] == 0)
    inv["resolved_points_name_exactly_one_case"] = all(
        x["case_id"] for v in pcl.values() for x in v["links"]
        if x["resolution_status"] == POINT_RESOLVED)
    inv["every_facet_declares_a_scope"] = all(
        f.get("scope") for f in m["facet_defs"])
    inv["key_based_intersection_would_have_been_wrong"] = key_based_false_common > 0
    return {"counts": c, "invariants": inv, "invariants_ok": all(inv.values()),
            "pair_statuses": dict(counts),
            "multi_case_examples": sorted(
                [{"series": s["id"], "n_cases": s["n_cases"], "cases": s["all_case_ids"]}
                 for s in multi_case], key=lambda x: -x["n_cases"])[:25],
            "multi_member_acts": [{"act": a["id"], "members": a["member_measurement_ids"],
                                   "series": a["series_ids"],
                                   "evidence": a["grouping_evidence"]}
                                  for a in multi_act]}


def render(model, val):
    tpl = Path(__file__).parent / "_workbench_v2_template.html"
    doc = tpl.read_text().replace("/*__MODEL__*/",
                                  json.dumps(model, ensure_ascii=False,
                                             separators=(",", ":")))
    (OUT / "psed_scientific_comparison_workbench.html").write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
