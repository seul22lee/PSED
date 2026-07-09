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
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
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
    # axis_role: coordinate / condition / output (drives experiment granularity)
    axis = qr.get("axis_role", {}) or {}
    coord, outp = set(axis.get("coordinate", [])), set(axis.get("output", []))
    for bad in (coord | outp) - qk_ids:
        print(f"  [warn] axis_role references unknown quantity: {bad}")
    for q in quantity_kinds:
        q["axis_role"] = ("coordinate" if q["id"] in coord
                          else "output" if q["id"] in outp else "condition")

    # ---- individuals: mint IRI, expand class ref ----------------------------
    individuals = {}
    for group, items in (core.get("individuals") or {}).items():
        out = []
        for it in items:
            it = dict(it)
            it["iri"] = ald + it["id"]
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

    compiled = {
        "meta": {**core["meta"], "compiled": True},
        "classes": classes,
        "relations": relations,
        "quantity_kinds": quantity_kinds,
        "quantity_relations": qr,
        "individuals": individuals,
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
    return compiled


if __name__ == "__main__":
    main()
