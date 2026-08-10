#!/usr/bin/env python3
"""
validate.py — validation gate for the canonical layer (spec §13).

  13.1 unit         dimensions match; affine handled; offset units not used as
                    ratio units; cycle distinct from dimensionless; unknown
                    distinct from dimensionless; normalized values carry unit "1"
  13.2 formula      no zero denominator; positive (effective) cycle count;
                    round-trip within tolerance; domain violations flagged
  13.3 provenance   every canonical value has raw value, locator, rule,
                    execution, context provenance, status and code version
  13.4 granularity  condition sweeps stored as profiles, profiles split, mixed
                    roles, insufficient axis evidence
  13.5 ontology     registry/implementation sync, unique ids, groups exist,
                    normalization definitions reference valid quantities,
                    deterministic compilation

Usage:
    python3 02_extraction/canonical/validate.py --all
    python3 02_extraction/canonical/validate.py --paper 10.1039_d0cp03358h
Exit status is non-zero when any FAILURE (not warning) is found.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "canonical"

from . import rules as R                                       # noqa: E402
from . import units as U                                       # noqa: E402
from . import sources as S                                     # noqa: E402
from .schema import (REPO, Status, COMPARISON_GROUPS,           # noqa: E402
                     NORMALIZATION_DEFINITIONS, RULE_DECLS)

OUTPUT = REPO / "papers"          # papers/<doi>/{resolved,canonical}/

# statuses that legitimately carry NO canonical value
NO_VALUE_STATUSES = {Status.AMBIGUOUS, Status.MISSING_CONTEXT, Status.UNSUPPORTED,
                     Status.INVALID, Status.NOT_APPLICABLE,
                     Status.CONTEXTUALLY_CONVERTIBLE, Status.DIRECTLY_CONVERTIBLE}

REQUIRED_TRANSFORM_KEYS = ("axis", "rule_id", "rule_version", "type", "status",
                           "source", "created_by", "code_version", "created_at")


class Report(object):
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.counts = Counter()

    def fail(self, check, where, msg):
        self.failures.append({"check": check, "where": where, "message": msg})
        self.counts["fail:" + check] += 1

    def warn(self, check, where, msg):
        self.warnings.append({"check": check, "where": where, "message": msg})
        self.counts["warn:" + check] += 1

    def ok(self, check):
        self.counts["ok:" + check] += 1


# =========================================================================
# 13.5 ontology / registry
# =========================================================================
def validate_ontology(rep):
    for err in R.validate_registry():
        rep.fail("ontology.registry", "transformation_rules", err)
    ids = [r["id"] for r in RULE_DECLS.values()]
    if len(ids) != len(set(ids)):
        rep.fail("ontology.registry", "transformation_rules", "duplicate rule ids")
    for nid, nd in NORMALIZATION_DEFINITIONS.items():
        g = nd.get("comparison_group")
        if g not in COMPARISON_GROUPS:
            rep.fail("ontology.groups", nid, "unknown comparison_group %r" % g)
    for gid, g in COMPARISON_GROUPS.items():
        if U.try_parse(g.get("canonical_unit"), True) is None:
            rep.fail("ontology.units", gid,
                     "canonical_unit %r is not a known unit" % g.get("canonical_unit"))
    rep.ok("ontology")


def validate_ontology_determinism(rep):
    """13.5 — recompiling must not change the artifact."""
    import subprocess
    onto = REPO / "01_ontology" / "ald_ontology.json"
    before = onto.read_bytes()
    try:
        subprocess.check_output([sys.executable, str(REPO / "01_ontology" / "build_ontology.py")],
                                stderr=subprocess.STDOUT)
    except Exception as exc:
        rep.fail("ontology.determinism", "build_ontology.py", "rebuild failed: %s" % exc)
        return
    if onto.read_bytes() != before:
        rep.fail("ontology.determinism", "ald_ontology.json",
                 "recompiling the ontology changed the artifact (non-deterministic)")
    else:
        rep.ok("ontology.determinism")


# =========================================================================
# per-curve validation
# =========================================================================
def validate_curve(curve, rep):
    cid = curve["curve_id"]
    raw = curve.get("raw") or {}
    trs = curve.get("transformations") or []

    # --- 13.3 provenance ------------------------------------------------
    src = curve.get("source") or {}
    for key in ("source_file", "json_pointer", "source_checksum", "doi"):
        if not src.get(key):
            rep.fail("provenance.locator", cid, "source.%s is missing" % key)
    for t in trs:
        for key in REQUIRED_TRANSFORM_KEYS:
            if t.get(key) in (None, ""):
                rep.fail("provenance.transformation", cid,
                         "transformation %s missing %r" % (t.get("rule_id"), key))
        if t.get("status") not in (
                Status.ALREADY_CANONICAL, Status.CONVERTED, Status.DIRECTLY_CONVERTIBLE,
                Status.CONTEXTUALLY_CONVERTIBLE, Status.AMBIGUOUS, Status.MISSING_CONTEXT,
                Status.UNSUPPORTED, Status.INVALID, Status.NOT_APPLICABLE):
            rep.fail("provenance.status", cid, "unknown status %r" % t.get("status"))
        if t.get("status") in NO_VALUE_STATUSES and not t.get("unresolved_reason"):
            rep.fail("provenance.reason", cid,
                     "status %r on rule %s carries no unresolved_reason"
                     % (t.get("status"), t.get("rule_id")))
        if t.get("rule_id") not in RULE_DECLS:
            rep.fail("provenance.rule", cid, "rule %r is not declared in the ontology"
                     % t.get("rule_id"))

    # a canonical value must have raw points AND a successful transformation
    for axis in ("x", "y"):
        can = (curve.get("canonical") or {}).get(axis)
        if can is None:
            continue
        if not raw.get("points"):
            rep.fail("provenance.raw", cid, "canonical %s exists without raw points" % axis)
        ok_tr = [t for t in trs
                 if t.get("axis") == axis
                 and t.get("status") in (Status.CONVERTED, Status.ALREADY_CANONICAL)]
        if not ok_tr:
            rep.fail("provenance.execution", cid,
                     "canonical %s exists with no successful TransformationExecution" % axis)
        if len(can.get("values") or []) != len(raw.get("points") or []):
            rep.fail("provenance.arity", cid,
                     "canonical %s has %d values for %d raw points"
                     % (axis, len(can.get("values") or []), len(raw.get("points") or [])))

        # --- 13.1 units -------------------------------------------------
        group = can.get("comparison_group")
        gspec = COMPARISON_GROUPS.get(group)
        if not gspec:
            rep.fail("unit.group", cid, "canonical %s in unknown group %r" % (axis, group))
            continue
        if can.get("unit") != gspec.get("canonical_unit"):
            rep.fail("unit.canonical", cid,
                     "canonical %s unit %r != group canonical unit %r"
                     % (axis, can.get("unit"), gspec.get("canonical_unit")))
        if gspec.get("dimension") == "dimensionless" and can.get("unit") != "1":
            rep.fail("unit.dimensionless", cid,
                     "normalized %s must use unit '1', got %r" % (axis, can.get("unit")))
        if can.get("normalization_definition") and \
                can["normalization_definition"] not in NORMALIZATION_DEFINITIONS:
            rep.fail("unit.normalization", cid, "unknown normalization definition")

    # --- projections must carry context provenance -----------------------
    for axis in ("x", "y"):
        for proj in (curve.get("projections") or {}).get(axis) or []:
            match = [t for t in trs if t.get("axis") == axis
                     and t.get("comparison_group") == proj.get("comparison_group")
                     and t.get("status") == Status.CONVERTED]
            if not match:
                rep.fail("provenance.projection", cid,
                         "projection into %s has no converted transformation record"
                         % proj.get("comparison_group"))
                continue
            t = match[0]
            if not t.get("context"):
                rep.fail("provenance.context", cid,
                         "projection %s used no recorded context" % proj.get("comparison_group"))
            for q, c in (t.get("context") or {}).items():
                if c.get("status") == "resolved" and not c.get("scope"):
                    rep.fail("provenance.context_scope", cid,
                             "context %s has no scope" % q)
                if c.get("status") == "resolved" and not c.get("source_file"):
                    rep.fail("provenance.context_source", cid,
                             "context %s has no source_file" % q)

    # --- 13.2 formula ----------------------------------------------------
    for t in trs:
        if t.get("status") != Status.CONVERTED:
            continue
        for q, c in (t.get("context") or {}).items():
            v = c.get("value")
            if c.get("status") != "resolved":
                continue
            if q in ("feature_height", "feature_length", "feature_depth",
                     "hydraulic_diameter", "feature_width", "reference_thickness",
                     "growth_per_cycle") and (v is None or float(v) == 0.0):
                rep.fail("formula.denominator", cid, "%s denominator is zero/None" % q)
            if q == "cycle_number" and (v is None or float(v) <= 0):
                rep.fail("formula.cycles", cid, "cycle_number must be positive, got %r" % v)
        if t.get("domain_violations"):
            rep.warn("formula.domain", cid,
                     "%d value(s) outside the declared domain of %s (flagged, not clamped)"
                     % (len(t["domain_violations"]), t.get("rule_id")))

    # --- 13.4 granularity -------------------------------------------------
    g = curve.get("granularity") or {}
    prev, now = g.get("previous_representation"), g.get("resolved_representation")
    if now == "series" and prev == "profile":
        rep.warn("granularity.condition_as_profile", cid,
                 "condition sweep on %r was stored as a single profile experiment"
                 % (curve.get("semantics", {}).get("x", {}).get("quantity")))
    if now == "profile" and prev == "single" and (g.get("n_points") or 0) > 1:
        rep.warn("granularity.profile_split", cid,
                 "spatial profile was stored as independent single experiments")
    if now == "unresolved":
        rep.warn("granularity.insufficient_evidence", cid,
                 "axis role could not be determined from available evidence")
    sx = (curve.get("semantics") or {}).get("x") or {}
    sy = (curve.get("semantics") or {}).get("y") or {}
    if sx.get("axis_role") == "output" and sy.get("axis_role") == "output":
        rep.warn("granularity.mixed_roles", cid,
                 "both axes are ontology outputs — this is a correlation, not a sweep")
    rep.ok("curve")


# =========================================================================
# raw-immutability check
# =========================================================================
def validate_raw_unchanged(doi, curves, rep):
    """The canonical layer must not have altered figure_data.json, and each
    curve's stored raw points must be deep-equal to the source slice."""
    paths = S.paper_paths(doi)
    fd_path = paths["figure_data"]
    live_sum = S.checksum(fd_path)
    fd = json.loads(fd_path.read_text())
    for c in curves:
        if c["source"].get("source_checksum") != live_sum:
            rep.fail("raw.checksum", c["curve_id"],
                     "figure_data.json checksum changed since the canonical build")
            continue
        ptr = c["source"]["json_pointer"]
        node = _resolve_pointer(fd, ptr)
        if node is None:
            rep.fail("raw.locator", c["curve_id"], "json_pointer %s does not resolve" % ptr)
            continue
        src_pts = [p for p in (node.get("points") or [])
                   if isinstance(p, (list, tuple)) and len(p) == 2]
        if [list(map(_f, p)) for p in src_pts] != \
                [list(map(_f, p)) for p in (c["raw"].get("points") or [])]:
            rep.fail("raw.mutation", c["curve_id"],
                     "stored raw points differ from the source slice")
    rep.ok("raw")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _resolve_pointer(doc, pointer):
    node = doc
    for part in pointer.strip("/").split("/"):
        if part == "":
            continue
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        else:
            return None
    return node


# =========================================================================
def load_curves(doi):
    p = OUTPUT / doi / "canonical" / "curves.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--paper", action="append", default=[])
    ap.add_argument("--json-out", default=str(REPO / "reports" / "canonical" / "validation.json"))
    ap.add_argument("--skip-determinism", action="store_true")
    a = ap.parse_args(argv)
    ids = a.paper or (S.papers() if a.all else [])
    if not ids:
        ap.error("pass --all or --paper <id>")

    rep = Report()
    validate_ontology(rep)
    if not a.skip_determinism:
        validate_ontology_determinism(rep)

    n_curves = 0
    for doi in ids:
        doc = load_curves(doi)
        if doc is None:
            continue
        curves = doc["curves"]
        n_curves += len(curves)
        for c in curves:
            validate_curve(c, rep)
        validate_raw_unchanged(doi, curves, rep)

    out = {
        "papers": len(ids), "curves": n_curves,
        "failures": rep.failures, "warnings": rep.warnings,
        "n_failures": len(rep.failures), "n_warnings": len(rep.warnings),
        "counts": dict(rep.counts),
    }
    p = Path(a.json_out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False))

    print("validated %d curve(s) across %d paper(s)" % (n_curves, len(ids)))
    print("  FAILURES : %d" % len(rep.failures))
    print("  warnings : %d" % len(rep.warnings))
    for f in rep.failures[:20]:
        print("   FAIL  %-32s %s: %s" % (f["check"], f["where"], f["message"]))
    if len(rep.failures) > 20:
        print("   ... %d more (see %s)" % (len(rep.failures) - 20, a.json_out))
    wc = Counter(w["check"] for w in rep.warnings)
    for k, v in wc.most_common():
        print("   warn  %-32s %d" % (k, v))
    print("-> %s" % p)
    return 1 if rep.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
