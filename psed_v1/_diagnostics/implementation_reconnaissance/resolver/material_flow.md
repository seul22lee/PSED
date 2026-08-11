# Material flow

## Producers

| stage | file:function | output |
|---|---|---|
| Scout | `pipeline/scout/scout.py` | `scout.json` `materials: [...]` — the paper's material list |
| Resolve, per record | `chemistry_scope.resolve_material` (`chemistry_scope.py:171-245`) | `{material, scope_level, evidence, candidates, ambiguity_reason, multi_material_paper}` |
| Resolve, write | `to_kb.py:1766-1771` onto `e{}`, `to_kb.py:1001-1006` onto the entity, `1394-1395` onto results | `material`, `material_raw`, `material_scope_level`, `material_evidence`, `material_candidates`, `material_ambiguity_reason`, `multi_material_paper` |
| KG | `build_kg.py:432` | `node("m::"+material, "Material")`, edge `deposits` from the Experiment node |
| Core KG | `build_core_kg.py` | `Material` node + `deposits` edge |

## The scope ladder (`resolve_material`, narrowest first)

| rung | level id | condition |
|---|---|---|
| 1 | `series_legend` | the legend names exactly one of the paper's materials (or the extraction stage already decided) |
| 2 | `panel_caption_clause` | this panel's own caption clause names exactly one |
| 3 | `figure_caption` | the caption names exactly one — **skipped entirely when the figure assigns materials per panel** |
| 4 | `figure_scout_note` | the scout's per-figure `why` names exactly one |
| 5 | `figure_body` | body text near the figure names exactly one |
| 6 | `paper_single_material` | the paper reports exactly one material |
| 7 | `unresolved` | refuses; `candidates` retained, `ambiguity_reason` set |

Rung 6 is a **fallback reached only when the paper has one material**, not an override. A
multi-material paper with no local evidence lands on rung 7 and gets `material = None`.

## Measured behaviour

```
material_scope_level over 1127 experiments (all 44 papers)
  series_legend         (rung 1)
  panel_caption_clause  (rung 2)
  figure_caption        (rung 3)
  figure_scout_note     (rung 4)
  figure_body           (rung 5)
  paper_single_material (rung 6)
  unresolved            (rung 7)
```

`10.1149_2.067203jes` (scout materials `["SiO2","Al2O3"]`, `multi_material_paper=True`):

```
entities   : SiO2 18, None 20
             scope: unresolved 20, panel_caption_clause 7, series_legend 6,
                    figure_caption 4, figure_scout_note 1
experiments: SiO2 21, None 11
             scope: series_legend 13, unresolved 11, figure_caption 4,
                    panel_caption_clause 4
```

**No paper-level broadcast occurs here.** The resolver refuses on 11 of 32 experiments
rather than assigning one of the two materials. The Al2O3 deposition yields no experiment
because the entities that would carry it resolve to `None`, not because SiO2 overwrote it.

`10.1039_c7ta03257a` (scout materials `["Pt"]`): all 4 entities carry `material = "Pt"`
(`figure_caption` 2, `panel_caption_clause` 2) even though the paper mints zero experiments.

## Implementation facts asked for

- **Where does paper-level material overwrite more local evidence?** Nowhere. Rung 6 fires
  only when `len(set(materials)) == 1`, in which case there is no competing local value.
- **Does local material evidence survive?** Yes — `material_scope_level`,
  `material_evidence` (the matched text, truncated to ~220 chars), `material_candidates`
  and `material_ambiguity_reason` are all persisted on both the entity and the experiment.
- **Are multiple materials per entity/result technically supported?** No. `resolve_material`
  returns one `material` string or `None`. `material_candidates` is a list but is
  documentation, not an assignment. Nothing consumes it.
- **Does the canonical schema accept multiple material contexts?** The canonical curve has
  no material field at all; material reaches canonical only through
  `source.linked_experiment_ids`.
- **Can the KG already encode multiple `Material` edges?** Yes structurally — `link()`
  appends to a list and `deposits` is emitted once per experiment from a single string, so
  emitting two edges would need only two calls. The ontology declares
  `deposits: Experiment -> Material` with no cardinality constraint.
- **Where could a material-role vocabulary technically attach?** On the `deposits` edge
  (`build_kg.py:432` — `links.append` accepts arbitrary extra keys, as `uses_precursor`
  already does with `reactant=lab`); on the entity dict as a sibling of `material`; and on
  the scout `materials` list. There is no `Substrate` role today, though the ontology
  declares an `on_substrate: Experiment -> Substrate` relation with **0 instances**.
- **Do validators require exactly one material?** No validator checks material at all.
  `pipeline/canonical/validate.py` validates curves, units and transformations;
  `ontology/validate.py` validates the ontology file, not instances.
