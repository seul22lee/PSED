# Geometry flow

## Chain

```
document.md  ->  geometry.classify_deterministic(sd)           geometry.py:~150-180
             ->  extracted/geometry.json {geometry_class, structure, method, evidence}
             ->  geometry.tag_experiments(only)                geometry.py:249-267
                     for e in experiments: e["geometry_class"] = gc; e["structure"] = st
             ->  resolved/experiments.json (rewritten in place)
             ->  build_core_kg.py:211-213  node("geo::<class>", "GeometryClass") + "geometry" edge
             ->  twin/twin_validation.py:_coverage / _commensurability
                 twin/m2_design.py:690-741, 798, 1257-1308
```

`to_kb.py` reads the same file independently: `_geom_for(mat)` (L398-435) returns
`(structure, geometry_class, controlled_conditions)` from `extracted/geometry.json`, and
L1021-1022 copies them onto the entity.

## The stamping site

```python
# geometry.py:249-267
def tag_experiments(only=None):
    for sd in (only or kb_dirs()):
        g  = json.loads(gf.read_text()) if gf.exists() else {}
        gc, st = g.get("geometry_class", "planar"), g.get("structure", "")
        exps = json.loads(f.read_text())
        for e in exps:
            e["geometry_class"] = gc          # <- one paper-level value, every experiment
            e["structure"] = st or e.get("structure")
        f.write_text(json.dumps(exps, indent=1))
```

One value per paper, applied to every experiment, with `"planar"` as the default when
`geometry.json` is missing or has no class. This is a post-hoc rewrite of an already
written `experiments.json`, run after resolve.

Measured: 1127 experiments -> `planar` 960, `vertical_structure` 71, `porous_material` 49,
`lateral_channel` 41 — exactly one distinct value per paper.

`10.1149_2.067203jes`: `geometry.json` = `planar / planar_wafer`, evidence
`"no 3D test structure found"`; all 32 experiments -> `planar`.

## Determinations

- **Does the Experiment schema already accept local geometry?** Yes. `geometry_class` and
  `structure` are ordinary dict keys; `to_kb.py:1021-1022` already writes them per entity
  from `_geom_for`. `tag_experiments` then overwrites the experiment records with the
  paper value. There is no schema to change.
- **Where is the paper value stamped?** `geometry.py:263-264`, and via `_geom_for` in
  `to_kb.py:398-435` (which also reads the paper-level file).
- **Does result/entity-specific geometry evidence exist?** In `geometry.json` only as
  `evidence` (one string per paper). `_geom_for` can also return controlled conditions
  (feature height/width, aspect ratio) which do become per-entity conditions. Per-figure
  geometry evidence is not extracted.
- **Does the resolver have hooks for local geometry?** Yes: `_geom_for(mat)` is already
  material-parameterised and called per record (`to_kb.py:1728`), and its output flows to
  the entity. Nothing downstream forces the paper value except `tag_experiments`.
- **Does canonical retain geometry?** No. `canonical/curves.json` has no geometry field.
- **Would case-level geometry require canonical changes?** No — canonical never reads it.
- **Which twin/model functions read it?**
  `twin_validation._coverage` (`by_geometry_class` census, `untested_regions`),
  `twin_validation._commensurability` (`geometry_out_of_domain` refusal),
  `m2_design.py:690-699` (`geometry_class`, `applicability`, `model_valid`),
  `m2_design.py:711,717,741,798,1257,1276,1281,1308`, and `m2_design.py:1548` (a fixed
  `geometry_class="lateral_channel"` in a self-test).
