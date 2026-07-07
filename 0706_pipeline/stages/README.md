# Ontology-grounded extraction stages (Phase B)

The redesigned per-experiment path — same figure-anchored backbone as `0604_kg`,
but granularity-correct, ontology-normalised, relevance-filtered, and physics-aware.

```
s06_study_profile.py   paper profile on the EVIDENCE scope (reuses benchmark)   -> output/<pid>/profile.json
s07_experiment.py      per-figure LLM extraction, ONTOLOGY-generated schema,     -> output/<pid>/experiments/*.json
                       canonical ids, inherits the profile                        (LLM)
s08_resolve.py         GRANULARITY + normalise + enrich + relevance (no LLM)      -> output/<pid>/resolved/{experiments,series}.json
s09_kg.py              typed KG with varies/in_series/series_varies (no LLM)      -> output/knowledge_graph_onto.{json,graphml}
```

Reuses `0604_kg` stages 01–05 (docling → figure filter → plot → formula → enrich).

## The upgrades, and how they show up

- **Granularity from the plot x-axis (not LLM guesses).** `s08` reads the
  authoritative x-label, canonicalises it (`lib.resolve_axis_label`), and uses its
  `axis_role`: **coordinate → one profile experiment** (`varies` the coordinate,
  the y-curve is its data); **condition → split each point** into its own
  experiment (`series_varies`), grouped into an `ExperimentSeries`.
- **Ontology normalisation** (materials/structures/quantities via aliases; SI
  units) replaces `0604`'s hardcoded maps.
- **Relevance / provenance**: material inherited from series/profile; each record
  tagged `experimental` / `model` / `background`.
- **Enrichment**: `of_reactant` qualifiers kept; unit-variant reconciliation
  (`same_as`).

## Result (3 papers)

| paper | profiles | sweep-points | model | note |
|---|---:|---:|---:|---|
| arts2019 | 8 | 0 | 0 | experimental (conformality profiles) |
| yim2020 | 30 | 0 | 0 | experimental (saturation profiles) |
| ylilammi2018 | 24 | 122 | 134 | modeling paper (Gordon/Ylilammi curves) |

KG: **188 experiments, 2437 QuantityValues**, edges incl. `varies` (62),
`in_series` (122), `series_varies` (1). Example resolved profile: `HfO₂ (120 s)`
→ material `HfO2`, `varies=[dimensionless_distance]`, dependent `normalized_thickness`,
21-point curve — one clean experiment (vs 0604's role confusion).

## Run
```bash
cd stages
python3 s06_study_profile.py     # reuse evidence profiles (no LLM)
python3 s07_experiment.py        # per-figure extraction (LLM, resumable)
python3 s08_resolve.py           # granularity + normalise (no LLM)
python3 s09_kg.py                # build KG (no LLM)
```

## End-to-end (C4) & scaling (C5)

```bash
python3 ../run_all.py              # s06 -> s07(LLM) -> s08 -> s09 -> dashboard
python3 ../run_all.py --parse      # also run 0604_kg 01-05 (docling..enrich) for NEW pdfs
python3 ../run_all.py --from s08   # resume from a stage
```

Accuracy is checked separately by `c1_accuracy.py` (grounds fields vs source
captions: axis 96%, points 100%). Baseline: **188 experiments, 188/188
analysis-ready**, 138 derived `exposure=P·t` values.

**To scale (C5):** drop PDFs into `0604_kg/pdf/` and run `run_all.py --parse`.
Blocked only by `docling` (the `01` parser) not being installed in this env;
5 unprocessed ALD PDFs are already in the repo (Aguinsky 2023, Yanguas-Gil 2012,
Gonsalves 2024, Knehr 2021, Arts-sticking 2019). The ontology stages s06–s09 scale
unchanged. Install: `pip install docling` (pulls torch + models).

## Known follow-ups
- `s06` evidence profile can over-collect studied materials (e.g. `Ir` for an
  Al₂O₃ paper) — tighten the profile / relevance whitelist.
- 4 arts "single" records = figures whose x-label didn't resolve; add aliases.
- Wire `defined_by` derivations (e.g. `exposure = P·t`) in `s08` enrichment.
