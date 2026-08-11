# Characterization-only results — `10.1039_c7ta03257a`

## Evidence at each stage

### Scout (`extracted/scout.json`)

```
materials            ["Pt"]
precursors           []          coreactants  []
process_type, temperature_window_C, gpc_nm, study_type, is_ald_process_paper present
drill  F12  "plots cyclic voltammograms comparing bare and Pt replic..."
       F13a "plots impedance spectra of Pt electrode with and withou..."
       F13b "plots cyclic voltammetry curves to evaluate charge stor..."
```

### Records (`extracted/records.json`) — 4

| figure | panel | x | y | series |
|---|---|---|---|---|
| Fig 7 | a | `potential` | `current_density` | `uncoated` |
| Fig 7 | a | `potential` | `current_density` | `coated` |
| Fig 8 | a | `frequency` | `|Z|` | `uncoated` |
| Fig 8 | a | `frequency` | `|Z|` | `coated` |

### Resolved entities — 4, all `UnresolvedSourceEntity`

| entity | classification | `unresolved_reason` | material | scope | bound conditions |
|---|---|---|---|---|---|
| `Fig7a__exp01` | `unknown` | conflicting signals | `Pt` | `figure_caption` | `cycle_number = 250` |
| `Fig7a__exp02` | `unknown` | conflicting signals | `Pt` | `figure_caption` | `cycle_number = 250` |
| `Fig8a__exp01` | `unknown` | only one signal family (continuous_trace) | `Pt` | `panel_caption_clause` | `cycle_number = 250` |
| `Fig8a__exp02` | `unknown` | only one signal family (continuous_trace) | `Pt` | `panel_caption_clause` | `cycle_number = 250` |

### Resolved experiments — 0

## Determinations

- **What synthesis evidence exists before resolve?** The scout material list (`Pt`), the
  scout per-figure notes naming "Pt replica"/"Pt electrode", and the caption text that
  yields `cycle_number = 250` — the ALD cycle count of the synthesis.
- **Do source records contain enough material/process context?** The records themselves carry
  only axes, points and series labels. The material and the cycle count arrive during resolve
  from the caption/scout, and they **do** land on the entity.
- **Where is that context lost?** It is **not** lost. All four entities carry
  `material = "Pt"` and `cycle_number = 250`. What is missing is a *relation* from these
  entities to any deposition object — and there is no deposition object in this paper to
  relate to, because no entity mints a case.
- **Why does the resolver produce `UnresolvedSourceEntity`?** `entities.classify` returns
  `"unknown"` when the signal families conflict (Fig 7) or when only one family votes
  (Fig 8). `ENTITY_CLASS["unknown"] = "UnresolvedSourceEntity"` (`entities.py:667`) and
  `CLASS_MODEL["unknown"]["is_experiment"] = False`, so the L1127 gate rejects them.
- **Could `Measurement`/`Sample` relations be serialized today?** The relations are declared
  (`performed_on: Measurement -> Sample`, `measures_case: Measurement -> ExperimentalCase`)
  and `build_kg.link()` emits any `etype` string between two existing nodes. But no node of
  type `Measurement` or `Sample` is ever created, and `_ENTITY_NODE` (`build_kg.py:262-273`)
  has no entry for either, so an entity claiming `entity_class = "Sample"` would be typed
  `UnresolvedSourceEntity` by the fallback at L304.
- **Are characterization entities filtered from Experiment creation?** Yes, by
  `model["is_experiment"]` at L1039/L1127 — via the class, not via any characterization-specific rule.
- **Can `not_an_experiment` preserve them as scientific results?** It already does: all four
  entities are written to `entities.json` and `results.json`, appear as `PlotSeries` +
  `UnresolvedSourceEntity` nodes in the full KG with their `asserts_condition` edges, and
  their curves appear in `canonical/curves.json`. They are absent only from
  `experiments.json`, the core KG (which is built from experiments), and the twin.
- **Does the KG have any relation suitable for provenance back to synthesis?** Declared and
  unused: `measures_case`, `performed_on`, `produced_by_run`. Instantiated and generic:
  `depicted_by` (`Entity -> PlotSeries`), `from_paper`, `shown_in`,
  `derived_representation_of` (declared `DerivedRepresentation -> Entity`, 0 instances).
