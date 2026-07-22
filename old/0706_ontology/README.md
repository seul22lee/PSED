# ALD Ontology (v0.1)

A model-aware ontology for atomic layer deposition, built to give the knowledge
graph a **shared, typed backbone** so that schema fields, KG nodes, papers, and
experiments all snap onto the same concepts instead of being minted ad-hoc.

This directly addresses why the current `0604_kg` graph is hard to read: it mints
only 4 node types (`experiment`, `paper`, `material`, `variable`) with generic
edges, so materials are bare strings, `variable` is overloaded, and cross-paper
links lean on a soft `similar_to` score. The ontology replaces that with a typed
class hierarchy + typed relations + a proper quantity system.

## Design decisions (this version)

| Decision | Choice |
|---|---|
| Scope | **Broad top-level skeleton across all of ALD, deep on the HAR-conformality core** |
| Model-aware layer | **Deferred to v2.** v1 ships the entity + quantity + relation ontology first |
| External standards | **Aligned broadly**: QUDT (units/quantitykinds) populated now; EMMO (materials) + ChEBI (chemicals) slots wired, IRIs staged as TODOs |
| Format | Human-editable **YAML** source → compiled ontology → (later) **OWL/TTL** export for FAIR/Protégé |

## Architecture: two sources → one compiled ontology

```
core.yaml         classes, relations, seed individuals, quantity enrichment   (edit this)
dictionary.json   canonical quantity names + symbols + aliases (reused from 0604_kg)  (edit this)
      │  build_ontology.py
      ▼
ald_ontology.yaml   compiled ontology, human-readable
ald_ontology.json   same, for the extraction / KG pipeline to load
```

- **TBox vs ABox.** `core.yaml` holds the *schema* (classes, relations, quantity
  kinds) plus canonical *reference individuals* (Al2O3, TMA, LHAR, ...). Per-
  experiment measured values stay in the KG (ABox), pointing at these IRIs.
- **The overloaded `variable` is split.** A `QuantityKind` (e.g. `temperature`)
  is context-free. Its role (independent / controlled / dependent) belongs to a
  `QuantityValue` inside one experiment — not to the global node. This is the
  single biggest fix for the messy graph.
- **Linking becomes exact.** Two experiments that use `TMA` reference the *same*
  `ald:TMA` individual; two that report `growth_per_cycle` share the same
  `QuantityKind`. Shared nodes replace `similar_to` as the primary link.

## What's in v0.1

- **72 classes** — full top-level taxonomy (Material, Chemical, Substrate,
  Reactor, Structure, ProcessType, CycleDesign, MeasurementMethod,
  ProcessRegime, Model) with the HAR-conformality branches (LHAR/Trench/Via/
  Pore, reaction-/transport-/recombination-limited regimes) populated deep.
- **18 typed relations** — `deposits`, `uses_precursor`, `in_reactor`,
  `has_geometry`, `exhibits_regime`, `reports`→`of_kind`, `derived_from`,
  `couples`, etc., each with domain/range.
- **71 quantity kinds** migrated from `dictionary.json`; **47 enriched** with SI
  unit + QUDT IRIs; dimensionless groups carry `derived_from` / `couples`
  (e.g. `knudsen_number derived_from mean_free_path, characteristic_length`).
- **39 seed individuals** — materials, precursors/co-reactants, ligand families,
  structures, regimes, methods, process types.

## Usage

```bash
python3 build_ontology.py     # core.yaml + dictionary.json -> ald_ontology.{yaml,json}
python3 validate.py           # integrity checks + coverage report vs 0604_kg KG
```

`validate.py` also reports **coverage**: which `variable`/`material` nodes in the
existing KG resolve to the ontology, and which don't (== gaps to fill next). It
already caught a real duplicate (`surface_coverage`) in the source dictionary.

## Honesty note on external IRIs

- **QUDT** IRIs follow a stable, predictable pattern (`unit:NanoM`,
  `qk:Temperature`) and are filled directly.
- **EMMO** IRIs are opaque UUIDs and **ChEBI** IRIs are numeric. These are **not
  invented** — inventing them would silently break interoperability. They are
  staged as `emmo_todo` / `chebi_todo` fields holding the human concept name, to
  be resolved in a verification pass against the real ontology browsers.

## Experiment granularity (v0.3)

A paper holds many experiments; the KB defines **one experiment = one unique
combination of controlled conditions**. Whether a plotted *line* is one
experiment or each *point* is a separate one is decided from the ontology, via
the `axis_role` tag on the independent (x-axis) quantity:

- `coordinate` (spatial_coordinate, dimensionless_distance, time) → within-run
  axis → **the line is ONE experiment** (`varies` that coordinate); its points
  are the profile/curve.
- `condition` (temperature, pulse_time, cycle_number, exposure, feature_height…)
  → varied across runs.

**Decision rule** (used by the extractor):
1. If the independents include a **coordinate**, that is the experiment's axis →
   one experiment per line. Any **condition** among the "independents" is really
   the *controlled series label* → group the lines into an `ExperimentSeries`
   (`series_varies` that condition).
2. If there is a condition axis and **no coordinate** → genuine sweep → **one
   experiment per point**.

Relations: `varies` (Experiment→QuantityKind), `in_series`
(Experiment→ExperimentSeries), `series_varies` (ExperimentSeries→QuantityKind).

Auditing the current 37 experiments with this rule flagged **16/37** with
independent/controlled confusion (e.g. a series labelled `"500 nm"` listing
`feature_height` as independent when it is the controlled series value) — the
model both surfaces the issue and prescribes the fix.

## Roadmap

- **v1.1 — rewrite the KG builder** (`0604_kg/09_kg.py`) to instantiate against
  this ontology: typed nodes with IRIs, `QuantityValue` carrying role, exact
  shared-node linking. This is where the messy graph actually gets fixed.
- **Verification pass** — resolve `emmo_todo` / `chebi_todo` to real IRIs.
- **OWL/TTL export** — add `build_owl.py` (needs `rdflib`) for FAIR publication
  and Protégé editing.
- **v2 — model-aware layer** — populate `Model`/`Equation` with equations,
  assumptions, validity ranges, and parameter priors (perspective paper §4),
  linking experiments via `fit`/`calibrate`/`validate`.
- **Grow the deep core** — expand quantity enrichment (currently 47/71) and add
  materials/precursors as the corpus scales beyond 3 papers.
