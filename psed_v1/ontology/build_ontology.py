"""
build_ontology.py
-----------------
Merge the two human-editable sources into one compiled ontology.

  core.yaml         classes, relations, seed individuals, quantity enrichment
  dictionary.json   canonical quantity names + symbols + aliases (reused as-is)
        |
        v
  ald_ontology.yaml  compiled ontology (human-readable)
  ald_ontology.json  same, for the extraction/KG pipeline to load

Every quantity in dictionary.json becomes a QuantityKind. Enrichment from
core.yaml (unit, QUDT IRIs, derived_from/couples) is folded in where present.
Prefixed IRIs (qk:Length, unit:NanoM, ald:Oxide) are expanded to full IRIs.
"""

import json
import sys
from pathlib import Path


def _molar_mass(formula):
    try:
        from molmass import Formula
        return round(Formula(formula).mass, 2)
    except Exception:
        return None

import yaml

# resolve() matters: the HTML regeneration at the end runs the viz generators with
# cwd=ROOT, so a RELATIVE ROOT (from `python3 -m ontology.build_ontology`) made the
# script path resolve against the new cwd and every regeneration silently warned out.
ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core.yaml"
DICT = ROOT / "dictionary.json"
OUT_YAML = ROOT / "ald_ontology.yaml"
OUT_JSON = ROOT / "ald_ontology.json"


def expand(value, ns: dict):
    """Expand a 'prefix:local' string to a full IRI using the namespace map."""
    if not isinstance(value, str) or ":" not in value:
        return value
    prefix, local = value.split(":", 1)
    if prefix in ns:
        return ns[prefix] + local
    return value  # already a full IRI or unknown prefix — leave as-is


def main():
    core = yaml.safe_load(CORE.read_text())
    dictionary = json.loads(DICT.read_text())

    ns = core["meta"]["namespaces"]
    ald = ns["ald"]

    # ---- classes: mint ald: IRI, expand external IRI slots ------------------
    classes = []
    for c in core["classes"]:
        c = dict(c)
        c["iri"] = ald + c["id"]
        classes.append(c)
    class_ids = {c["id"] for c in classes}

    # ---- relations ----------------------------------------------------------
    relations = []
    for r in core["relations"]:
        r = dict(r)
        r["iri"] = ald + r["id"]
        relations.append(r)

    # ---- quantity kinds: dictionary.json x enrichment -----------------------
    enrich = core.get("quantity_enrichment", {}) or {}
    quantity_kinds = []
    for entry in dictionary:
        name = entry["canonical_name"]
        qk = {
            "id": name,
            "iri": ald + name,
            "domain": entry.get("domain"),
            "symbols": entry.get("symbols", []),
            "aliases": entry.get("aliases", []),
            "qudt_quantitykind": None,
            "unit": None,
        }
        e = enrich.get(name)
        if e:
            qk["qudt_quantitykind"] = expand(e.get("qudt_qk"), ns)
            qk["unit"] = expand(e.get("unit"), ns)
            if "note" in e:
                qk["note"] = e["note"]
            if "derived_from" in e:
                qk["derived_from"] = e["derived_from"]
            if "couples" in e:
                qk["couples"] = e["couples"]
        quantity_kinds.append(qk)
    qk_ids = {q["id"] for q in quantity_kinds}
    qk_by_id = {q["id"]: q for q in quantity_kinds}

    # ---- quantity relations: specializes / defined_by / qualifiers / same_as
    qr = core.get("quantity_relations", {}) or {}
    for child, parent in (qr.get("specializes") or {}).items():
        if child in qk_by_id:
            qk_by_id[child]["specializes"] = parent
    for d in qr.get("defined_by") or []:
        q = qk_by_id.get(d["quantity"])
        if q:
            q["defined_by"] = {k: v for k, v in d.items() if k != "quantity"}
    for spec in qr.get("qualifiers") or []:
        q = qk_by_id.get(spec["quantity"])
        if q:
            q.setdefault("qualifiers", []).append({"by": spec["by"], "values": spec["values"]})
    for a, b in (qr.get("same_as") or {}).items():
        if a in qk_by_id:
            qk_by_id[a]["same_as"] = b
    for a, b in (qr.get("related") or {}).items():
        if a in qk_by_id:
            qk_by_id[a].setdefault("related", []).append(b)
    # families: tag each quantity with its measurand family (comparability class)
    fam = qr.get("families", {}) or {}
    for fid, spec in fam.items():
        for m in spec.get("members", []):
            if m in qk_by_id:
                qk_by_id[m]["family"] = fid
            else:
                print(f"  [warn] family '{fid}' references unknown quantity: {m}")
    # categories: coarse semantic grouping (material/process/geometry/observable/…)
    for cid, members in (qr.get("categories", {}) or {}).items():
        for m in members:
            if m in qk_by_id:
                qk_by_id[m]["category"] = cid
            else:
                print(f"  [warn] category '{cid}' references unknown quantity: {m}")
    # recipe_role: control_setting (=in recipe) vs structure/species/model/derived/…
    CAT2ROLE = {"process_parameter": "control_setting", "geometry": "structure",
                "material_property": "model_parameter", "observable": "observable",
                "coordinate": "coordinate", "dimensionless_number": "derived"}
    q2override = {}
    for role, qs in (qr.get("recipe_role_overrides", {}) or {}).items():
        for q in qs:
            q2override[q] = role
    for q in quantity_kinds:
        q["recipe_role"] = q2override.get(q["id"]) or CAT2ROLE.get(q.get("category"))
        can = spec.get("canonical")
        if can and can not in qk_ids:
            print(f"  [warn] family '{fid}' canonical is unknown quantity: {can}")
    # transforms: validate endpoints + bridge exist
    for t in qr.get("transforms", []) or []:
        for key in ("from", "to", "bridge"):
            q = t.get(key)
            if q and q not in qk_ids:
                print(f"  [warn] transform {t.get('from')}->{t.get('to')}: unknown {key} '{q}'")
    # --- comparability layer validation (transformation rules / normalization
    # definitions / comparison groups). Structural errors here are FATAL: the
    # canonical layer binds to these declarations, so a dangling reference would
    # silently disable a transformation instead of failing loudly.
    fatal = []
    STATUS_IDS = {s["id"] for s in qr.get("transformation_statuses", []) or []}
    TYPE_IDS = {t["id"] for t in qr.get("transformation_types", []) or []}
    groups = qr.get("comparison_groups", {}) or {}
    normdefs = qr.get("normalization_definitions", []) or []
    normdef_ids = set()
    for nd in normdefs:
        if nd["id"] in normdef_ids:
            fatal.append(f"duplicate normalization_definition id: {nd['id']}")
        normdef_ids.add(nd["id"])
        for key in ("numerator", "denominator"):
            if nd.get(key) and nd[key] not in qk_ids:
                fatal.append(f"normalization_definition '{nd['id']}': unknown {key} quantity '{nd[key]}'")
        for rc in nd.get("requires_context", []) or []:
            if rc not in qk_ids:
                fatal.append(f"normalization_definition '{nd['id']}': unknown required context '{rc}'")
        if nd.get("comparison_group") and nd["comparison_group"] not in groups:
            fatal.append(f"normalization_definition '{nd['id']}': unknown comparison_group '{nd['comparison_group']}'")
    for gid, g in groups.items():
        cq = g.get("canonical_quantity")
        if cq and cq not in qk_ids:
            fatal.append(f"comparison_group '{gid}': unknown canonical_quantity '{cq}'")
        if not g.get("canonical_unit"):
            fatal.append(f"comparison_group '{gid}': missing canonical_unit")
        nd = g.get("normalization_definition")
        if nd and nd not in normdef_ids:
            fatal.append(f"comparison_group '{gid}': unknown normalization_definition '{nd}'")
    rule_ids = set()
    for r in qr.get("transformation_rules", []) or []:
        rid = r.get("id")
        if rid in rule_ids:
            fatal.append(f"duplicate transformation_rule id: {rid}")
        rule_ids.add(rid)
        if not r.get("implementation_id"):
            fatal.append(f"transformation_rule '{rid}': missing implementation_id")
        if not r.get("version"):
            fatal.append(f"transformation_rule '{rid}': missing version")
        if r.get("type") not in TYPE_IDS:
            fatal.append(f"transformation_rule '{rid}': unknown type '{r.get('type')}'")
        if not r.get("output_unit"):
            fatal.append(f"transformation_rule '{rid}': missing output_unit")
        if not r.get("input_units"):
            fatal.append(f"transformation_rule '{rid}': missing input_units")
        for key in ("source_quantity_kind", "target_quantity_kind"):
            q = r.get(key)
            if q and q not in qk_ids:
                fatal.append(f"transformation_rule '{rid}': unknown {key} '{q}'")
        for rc in (r.get("required_context") or []) + (r.get("optional_context") or []):
            if rc not in qk_ids:
                fatal.append(f"transformation_rule '{rid}': unknown context quantity '{rc}'")
        nd = r.get("normalization_definition")
        if nd and nd not in normdef_ids:
            fatal.append(f"transformation_rule '{rid}': unknown normalization_definition '{nd}'")
        tspec = next((t for t in qr.get("transformation_types", []) or [] if t["id"] == r.get("type")), {})
        if r.get("invertible") and not tspec.get("invertible", True):
            fatal.append(f"transformation_rule '{rid}': claims invertible but type '{r.get('type')}' is not")
        if tspec.get("needs_context") and not r.get("required_context") and not r.get("self_contained"):
            fatal.append(f"transformation_rule '{rid}': type '{r.get('type')}' needs context but required_context is empty")
    if not STATUS_IDS:
        fatal.append("transformation_statuses is empty")
    if fatal:
        for m in fatal:
            print(f"  [FATAL] {m}")
        raise SystemExit(f"ontology compile failed: {len(fatal)} comparability-layer error(s)")

    # axis_role: coordinate / condition / output (drives experiment granularity)
    axis = qr.get("axis_role", {}) or {}
    coord, outp = set(axis.get("coordinate", [])), set(axis.get("output", []))
    for bad in (coord | outp) - qk_ids:
        print(f"  [warn] axis_role references unknown quantity: {bad}")
    for q in quantity_kinds:
        q["axis_role"] = ("coordinate" if q["id"] in coord
                          else "output" if q["id"] in outp else "condition")

    # ---- overlay: approved auto-proposed extensions (core_extensions.yaml) ----
    # merged into core so the hand-curated core.yaml is never edited by the pipeline.
    ext = {}
    extf = ROOT / "core_extensions.yaml"
    if extf.exists():
        ext = yaml.safe_load(extf.read_text()) or {}
        for group, items in (ext.get("individuals") or {}).items():
            core.setdefault("individuals", {}).setdefault(group, []).extend(items)
        for q in ext.get("quantity_kinds") or []:          # fully-formed qk entries
            qk = {"id": q["id"], "iri": ald + q["id"], "domain": q.get("domain"),
                  "symbols": q.get("symbols", []), "aliases": q.get("aliases", []),
                  "qudt_quantitykind": None, "unit": q.get("unit"),
                  "category": q.get("category"), "family": q.get("family") or None,
                  "recipe_role": q.get("recipe_role"),
                  "axis_role": q.get("axis_role", "output" if q.get("recipe_role") == "observable"
                               else "coordinate" if q.get("recipe_role") == "coordinate" else "condition"),
                  "source": "auto-proposed"}
            if qk["id"] in qk_by_id:
                # an approved extension SUPERSEDES the dictionary seed of the same
                # id, in place -- one id, one QuantityKind, never a duplicate
                qk_by_id[qk["id"]].clear()
                qk_by_id[qk["id"]].update(qk)
            else:
                quantity_kinds.append(qk); qk_ids.add(qk["id"]); qk_by_id[qk["id"]] = qk
        for cat, members in (ext.get("categories") or {}).items():
            qr.setdefault("categories", {}).setdefault(cat, []).extend(members)

    # ---- individuals: mint IRI, expand class ref ----------------------------
    individuals = {}
    for group, items in (core.get("individuals") or {}).items():
        out = []
        for it in items:
            it = dict(it)
            it["iri"] = ald + it["id"]
            if group in ("materials", "precursors", "coreactants"):
                f = it.get("formula")
                if f:
                    calc = _molar_mass(f)
                    if calc is not None:
                        if it.get("molar_mass") is None:
                            it["molar_mass"] = calc
                            it["molar_mass_src"] = "computed(formula, molmass-IUPAC)"
                        else:
                            # hand value wins; cross-check and warn on mismatch
                            if abs(it["molar_mass"] - calc) > 0.1:
                                print(f"  [mass WARN] {it['id']}: hand={it['molar_mass']} "
                                      f"calc={calc} (formula={f})")
            out.append(it)
        individuals[group] = out

    # ---- models: mint IRI, validate input quantity ids exist ----------------
    model_families = core.get("model_families", {}) or {}
    models = []
    for m in core.get("models", []) or []:
        m = dict(m)
        m["iri"] = ald + m["id"]
        for inp in m.get("inputs", []) or []:
            q = inp.get("quantity")
            if q and q not in qk_ids:
                print(f"  [warn] model '{m['id']}' input references unknown quantity: {q}")
        for out in m.get("outputs", []) or []:
            q = out.get("quantity")
            if q and q not in qk_ids:
                print(f"  [warn] model '{m['id']}' output references unknown quantity: {q}")
        fam = m.get("family")
        if fam and fam not in model_families:
            print(f"  [warn] model '{m['id']}' references unknown family: {fam}")
        models.append(m)
    model_ids = {m["id"] for m in models}
    for fid, spec in model_families.items():
        for mem in spec.get("members", []) or []:
            if mem not in model_ids:
                print(f"  [warn] model_family '{fid}' references unknown model: {mem}")

    # ---- geometry-class layer (geometry_classes.yaml overlay) ----------------
    # Under `geometry`, the first layer is the geometry_class (transport regime);
    # geometry quantities parameterise a class; structures instance a class; models
    # declare which classes they are valid for (used for geometry-scoped validation).
    geometry_classes = {}
    geof = ROOT / "geometry_classes.yaml"
    if geof.exists():
        gy = yaml.safe_load(geof.read_text()) or {}
        geometry_classes = gy.get("geometry_classes", {}) or {}
        struct2gc = {m: gc for gc, s in geometry_classes.items() for m in (s.get("members") or [])}
        for it in individuals.get("structures", []):
            if it["id"] in struct2gc:
                it["geometry_class"] = struct2gc[it["id"]]
            elif it["id"] not in struct2gc:
                print(f"  [warn] structure '{it['id']}' has no geometry_class")
        q2gc = {}
        for gc, s in geometry_classes.items():
            for q in (s.get("parameters") or []):
                q2gc.setdefault(q, []).append(gc)
                if q not in qk_ids:
                    print(f"  [warn] geometry_class '{gc}' parameter unknown quantity: {q}")
        for q in quantity_kinds:
            if q["id"] in q2gc:
                q["geometry_class"] = q2gc[q["id"]]
        mg = gy.get("model_geometry", {}) or {}
        for m in models:
            if m["id"] in mg:
                m["applies_to_geometry"] = mg[m["id"]]
        for mid in mg:
            if mid not in model_ids:
                print(f"  [warn] model_geometry references unknown model: {mid}")

    compiled = {
        "meta": {**core["meta"], "compiled": True},
        "classes": classes,
        "relations": relations,
        "quantity_kinds": quantity_kinds,
        "quantity_relations": qr,
        "individuals": individuals,
        "geometry_classes": geometry_classes,
        "model_families": model_families,
        "models": models,
        "_counts": {
            "classes": len(classes),
            "relations": len(relations),
            "quantity_kinds": len(quantity_kinds),
            "quantity_kinds_enriched": sum(1 for q in quantity_kinds if q["unit"]),
            "quantity_specializations": sum(1 for q in quantity_kinds if q.get("specializes")),
            "quantity_equations": sum(1 for q in quantity_kinds if q.get("defined_by")),
            "quantity_families": len(qr.get("families", {}) or {}),
            "quantity_in_family": sum(1 for q in quantity_kinds if q.get("family")),
            "quantity_categories": len(qr.get("categories", {}) or {}),
            "quantity_categorized": sum(1 for q in quantity_kinds if q.get("category")),
            "quantity_transforms": len(qr.get("transforms", []) or []),
            "transformation_rules": len(qr.get("transformation_rules", []) or []),
            "transformation_types": len(qr.get("transformation_types", []) or []),
            "transformation_statuses": len(qr.get("transformation_statuses", []) or []),
            "normalization_definitions": len(qr.get("normalization_definitions", []) or []),
            "comparison_groups": len(qr.get("comparison_groups", {}) or {}),
            "axis_coordinate": sum(1 for q in quantity_kinds if q.get("axis_role") == "coordinate"),
            "axis_condition": sum(1 for q in quantity_kinds if q.get("axis_role") == "condition"),
            "axis_output": sum(1 for q in quantity_kinds if q.get("axis_role") == "output"),
            "individuals": sum(len(v) for v in individuals.values()),
            "models": len(models),
            "model_families": len(model_families),
            "model_equations": sum(len(m.get("equations", []) or []) for m in models),
        },
    }

    OUT_YAML.write_text(yaml.safe_dump(compiled, sort_keys=False, allow_unicode=True))
    OUT_JSON.write_text(json.dumps(compiled, indent=2, ensure_ascii=False))

    print("Built ontology:")
    for k, v in compiled["_counts"].items():
        print(f"  {k:28s} {v}")
    print(f"  -> {OUT_YAML.name}, {OUT_JSON.name}")

    # Keep the rendered HTML in lock-step with the JSON. Previously build_ontology
    # rebuilt only the JSON/YAML, so ontology.html drifted (it missed ~11 commits of
    # ontology changes, incl. every pressure term). Regenerating here — via the same
    # canonical generators, never a hand-edit — means the artifact can no longer go
    # stale silently. Failures are non-fatal so the JSON build still succeeds headless.
    import subprocess
    for gen in ("visualize_ontology.py", "build_onto_viz.py"):
        try:
            subprocess.run([sys.executable, str(ROOT / gen)], check=True,
                           capture_output=True, cwd=str(ROOT))
            print(f"  -> regenerated {gen.replace('.py', '.html' if gen == 'visualize_ontology.py' else '')}")
        except Exception as e:
            print(f"  [warn] could not regenerate via {gen}: {e}")
    return compiled


if __name__ == "__main__":
    main()
