"""
canonical/schema.py — data model for the canonical comparison layer.

Vocabularies (statuses, transformation types, comparison groups, normalization
definitions) are READ FROM THE COMPILED ONTOLOGY, never hard-coded here, so the
ontology stays the single source of truth. Anything this module cannot find in
the ontology is a build error, not a silent default.
"""
from __future__ import annotations
import paths as P

import json
import os
import subprocess
from pathlib import Path

ROOT = P.REPO                                          # psed_v1/
REPO = P.REPO                                          # psed_v1/
ONTOLOGY_PATH = P.ONTOLOGY_JSON

ONTO = json.loads(ONTOLOGY_PATH.read_text())
QR = ONTO.get("quantity_relations", {}) or {}

TRANSFORMATION_STATUSES = {s["id"]: s for s in QR.get("transformation_statuses", []) or []}
TRANSFORMATION_TYPES = {t["id"]: t for t in QR.get("transformation_types", []) or []}
NORMALIZATION_DEFINITIONS = {n["id"]: n for n in QR.get("normalization_definitions", []) or []}
COMPARISON_GROUPS = QR.get("comparison_groups", {}) or {}
RULE_DECLS = {r["id"]: r for r in QR.get("transformation_rules", []) or []}
QK_META = {q["id"]: q for q in ONTO["quantity_kinds"]}

if not (TRANSFORMATION_STATUSES and TRANSFORMATION_TYPES and COMPARISON_GROUPS):
    raise RuntimeError(
        "compiled ontology is missing the comparability layer; "
        "run: python3 -m ontology.build_ontology")


class Status(object):
    """Namespace of the ontology-declared statuses (validated at import)."""
    ALREADY_CANONICAL = "already_canonical"
    DIRECTLY_CONVERTIBLE = "directly_convertible"
    CONTEXTUALLY_CONVERTIBLE = "contextually_convertible"
    CONVERTED = "converted"
    AMBIGUOUS = "ambiguous"
    MISSING_CONTEXT = "missing_context"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    NOT_APPLICABLE = "not_applicable"


for _name in [v for k, v in vars(Status).items() if not k.startswith("_") and isinstance(v, str)]:
    if _name not in TRANSFORMATION_STATUSES:
        raise RuntimeError("status %r not declared in the ontology" % _name)

# Scopes, narrowest first. Context resolution walks this order.
SCOPE_ORDER = ["point", "curve", "series", "panel", "figure",
               "experiment", "method", "paper"]


def scope_rank(scope):
    try:
        return SCOPE_ORDER.index(scope)
    except ValueError:
        return len(SCOPE_ORDER)


# --- code version ---------------------------------------------------------
_CODE_VERSION = None


def code_version():
    """Git description of the working tree, used as the `code_version` stamp on
    every transformation execution. Falls back to 'unversioned' outside git."""
    global _CODE_VERSION
    if _CODE_VERSION is None:
        try:
            out = subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL).decode().strip()
            dirty = subprocess.call(
                ["git", "-C", str(REPO), "diff", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _CODE_VERSION = out + ("+dirty" if dirty else "")
        except Exception:
            _CODE_VERSION = "unversioned"
    return _CODE_VERSION


_BUILD_TS = None


def build_timestamp():
    """Deterministic build stamp. Never `now()`, and never a file mtime.

    Priority: SOURCE_DATE_EPOCH -> the git HEAD commit time -> the ontology
    file's mtime. The mtime fallback is last because recompiling the ontology
    touches the file even when its CONTENT is byte-identical, which made every
    canonical record change on an unrelated rebuild."""
    global _BUILD_TS
    if _BUILD_TS is not None:
        return _BUILD_TS
    ts = os.environ.get("SOURCE_DATE_EPOCH")
    if ts:
        _BUILD_TS = int(ts)
        return _BUILD_TS
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "show", "-s", "--format=%ct", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
        _BUILD_TS = int(out)
    except Exception:
        _BUILD_TS = int(ONTOLOGY_PATH.stat().st_mtime)
    return _BUILD_TS


# --- records --------------------------------------------------------------
class ContextBinding(dict):
    """A contextual quantity bound at a declared scope, with provenance."""

    @staticmethod
    def make(quantity, value, unit, scope, source_file, source_location,
             evidence=None, confidence=1.0, origin=None):
        return ContextBinding({
            "quantity": quantity,
            "value": value,
            "unit": unit,
            "scope": scope,
            "source_file": source_file,
            "source_location": source_location,
            "evidence": evidence,
            "confidence": confidence,
            "origin": origin or {},
        })


class Evidence(dict):
    @staticmethod
    def make(source, source_file=None, source_location=None, span=None,
             method=None, confidence=None, automatic=True):
        return Evidence({
            "source": source,                 # figure_label | figure_caption | document_text | ...
            "source_file": source_file,
            "source_location": source_location,
            "span": span,                     # the quoted text that justifies the assignment
            "method": method,                 # recovery method id
            "confidence": confidence,
            "automatic": bool(automatic),
        })


class TransformationRecord(dict):
    """One TransformationExecution. A canonical value without one of these fails
    provenance validation (validate.py)."""

    @staticmethod
    def make(axis, rule_id, rule_version, ttype, formula, status,
             original_value=None, original_unit=None,
             canonical_value=None, canonical_unit=None,
             context=None, unresolved_reason=None, confidence=None,
             assumptions=None, invertible=None, source=None,
             normalization_definition=None, comparison_group=None):
        return TransformationRecord({
            "axis": axis,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "type": ttype,
            "formula": formula,
            "status": status,
            "normalization_definition": normalization_definition,
            "comparison_group": comparison_group,
            "original_value": original_value,
            "original_unit": original_unit,
            "canonical_value": canonical_value,
            "canonical_unit": canonical_unit,
            "context": context or {},
            "unresolved_reason": unresolved_reason,
            "confidence": confidence,
            "assumptions": assumptions or [],
            "invertible": invertible,
            "source": source or {},
            "created_by": "pipeline/canonical/build_canonical.py",
            "code_version": code_version(),
            "created_at": build_timestamp(),
        })


def group_spec(group_id):
    return COMPARISON_GROUPS.get(group_id)


def normalization_spec(nd_id):
    return NORMALIZATION_DEFINITIONS.get(nd_id)


def canonical_unit_for_group(group_id):
    g = COMPARISON_GROUPS.get(group_id) or {}
    return g.get("canonical_unit")


def canonical_quantity_for_group(group_id):
    g = COMPARISON_GROUPS.get(group_id) or {}
    return g.get("canonical_quantity")
