# Current vs target semantics

Read-only. Every count below was recomputed from the live artifacts during this audit.

## 1. The two models side by side

TARGET (what the science requires)

```
Paper
 +-- StudySeries ............... an author-declared grouping ("Series A")
      +-- DepositionRun ........ one process execution
           +-- Sample .......... one physical specimen
                +-- Measurement . one observing act on that sample
                     +-- ResultSeries ....... the numbers
                          +-- Representation . as-measured / scaled / normalized / inset
```

CURRENT (what PSED builds)

```
Paper
 +-- Figure ............................ Docling PictureItem -> printed figure
      +-- entity (resolved) ............ one curve family in one panel
           +-- Experiment(s) ........... one per sweep point, minted from the entity
                +-- PlotSeries/Curve ... the numbers
```

The current tree is rooted in the **document**; the target tree is rooted in the
**laboratory**. Every mismatch in the gap matrix is a consequence of that one
substitution: `Figure/panel` stands in for `DepositionRun`, `Sample`, `Measurement`,
and `StudySeries` all at once.

## 2. Identity keys actually in use (audit item 18)

| level | key | literal form | what it encodes | what it should encode | consequence |
|---|---|---|---|---|---|
| resolved entity | `entity_id` | `10.1039_d0cp03358h__Fig3b` | paper + printed figure + panel | one measurement or one case | figure-local; nothing is shareable across figures |
| resolved entity | `entity_key` | `10.1039_d0cp03358h\|7\|3\|b\|experimental profile\|scaled` | paper, docling index, printed figure, panel, series label, representation | same | **the representation is already in the key** — so two views of one measurement are guaranteed distinct identities by construction |
| experiment | `exp_id` | `..__Fig3b`, `..__Fig1a__case00` | entity + sweep index | the deposition case | conditions never enter the key |
| entity | `physical_case_id` | opaque group id | co-panel curves sharing a measurement event | one physical specimen | 608 groups, **every one confined to a single printed figure**; 370 entities have `None` |
| entity | `measurement_event_id` | present on 1044/1044 | one plotting event | one observing act | never crosses a figure |
| entity | `experimental_series_id` | figure-local | author study series | author study series | 327 `ExperimentSeries`, all figure-scoped |
| canonical | `curve_id` | `{doi}::F{fig}::{panel}::{i}::f{fi}p{pi}` | source slice | source slice | correct — this one is honest about being a *source* identity |

The pattern: **every identity key in the pipeline is a document coordinate.** Not one of
them is a laboratory coordinate. `curve_id` is the only key whose name matches what it
actually identifies; `physical_case_id` is the worst offender, because its name promises
a physical specimen and it delivers a panel-local plotting group.

## 3. Evidence that is already captured but not used for identity (audit item 19)

This is the most consequential finding of the audit, because it changes the cost estimate
of any eventual repair. The resolver **already extracts** most of the evidence the target
model needs; it simply does not let that evidence participate in identity.

| evidence | field | instantiated | currently used for | not used for |
|---|---|---|---|---|
| view of a measurement | `entity.representation` | 1044/1044 — `primary` 960, `scaled` 33, `normalized` 30, `as_measured` 20, `inset` 1 | disambiguating `entity_key` | suppressing duplicate Experiments across views |
| is this a real case | `entity.experimental_case_status` | 1044/1044 — `supported` 500, `not_an_experiment` 312, `independent_process_sweep` 103, `shared_measurement_event` 66, `not_an_independent_sweep` 31, `unresolved_settings` 27, `single_setting_only` 5 | annotation | gating Experiment minting |
| how many cases | `entity.experimental_case_count` | 1044/1044 — 436 zeros, 505 ones, 103 greater | annotation | it *is* the mint count, but only within one entity |
| shared specimen | `entity.shares_physical_case_with` | 66/1044 | `physical_case_id` grouping | cross-figure grouping |
| what the points are | `entity.samples_are` | observations 732, simulated 112, model_predictions 95, fitted 23, unresolved 70, imported 10, derived 2 | entity class | measurement/run separation |
| material scope | `experiment.material_scope_level` | 1127/1127 | provenance note | it records `paper_single_material` vs `panel_caption_clause` but the paper-level value still wins |
| chemistry provenance | `experiment.chemistry_provenance` | 1127/1127, with `resolution_method`, `confidence`, `source_level` | audit trail | nothing downstream branches on confidence |

Read that table as: the pipeline knows that Yim Fig 9's nine panels are three measurements
in three representations — it stamps `scaled` and `normalized` on them — and then mints 18
Experiments anyway. The gap is not perception. It is that `representation` is an
*attribute of the identity string* instead of a *reason not to mint a second Experiment*.

## 4. Concepts represented at the wrong level

| concept | current level | correct level | evidence |
|---|---|---|---|
| Material | paper | deposition run / case | `2.067203jes` deposits SiO2 **and** Al2O3; all 32 experiments say SiO2 |
| Geometry | paper | deposition run / sample | `2.067203jes` has planar and AR~30 trench cases; all say `planar` |
| Experiment | printed panel | deposition condition case | `am.2016.182` Fig 2a/2b/2c are one temperature sweep, three panels, three families |
| Series | printed figure | author study | Yim's samples 8 and 12 appear in two series each; PSED has 0 cross-figure series |
| Measurement condition | fused with process conditions | separate axis | Yim Fig 7a's 10x/5x objective becomes 3 "experiments" |

## 5. Where the current design is already right

Not a gap; recorded so a future repair does not damage it.

- **Simulated vs measured.** `SimulationRun` (112) and `ModelSweep` (95) are separate
  classes, `data_source` is explicit on every canonical curve and is never defaulted
  (this was the B2 fix), and `Model`/`ModelFamily` individuals exist. Yim Fig 10 —
  a MATLAB re-implementation of Ylilammi's model — is classified correctly.
- **Imported literature.** `ImportedLiteratureObservation` (10) plus `originally_reported_in`,
  and the full KG carries `Arts 2019`, `Ylilammi 2018`, `Ylivaara 2020` as Paper nodes
  that are *not* corpus papers. A curve replotted from another paper is not attributed
  to the current one.
- **Transformation provenance.** 8 `TransformationRule` / 2126 `TransformationExecution`
  with `derived_from_value` back to 2084 `RawQuantityValue`. Every canonical number can be
  walked back to what was digitized.
- **`PlotSeries` is documented as "NEVER an Experiment".** The ontology already states the
  distinction the resolver violates.
- **Curve identity.** `curve_id` is unique 1042/1042 after the `f{fi}p{pi}` fix.
