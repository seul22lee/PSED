> **STALE — do not follow the commands in this file.**
>
> This README describes the old `0706_pipeline` / `0604_kg` layout. Those
> directories do not exist in this repository, so `pipeline.py`, `run_all.py` and
> `config.py` cannot run. The authoritative, working workflow is
> [`../docs/PIPELINE.md`](../docs/PIPELINE.md); the comparison layer is documented
> in [`../docs/CANONICALIZATION.md`](../docs/CANONICALIZATION.md).
>
> Kept for historical context on the stage design only.

# 0706_pipeline — ontology-first ALD knowledge-graph pipeline

A reorganization of `0604_kg` around the **ontology backbone** in
[`../0706_ontology`](../0706_ontology). Two structural changes:

1. **The ontology is stage 0.** Schema, normalization, and the KG all
   instantiate against `ald_ontology.json` instead of minting nodes ad-hoc.
2. **Input scope is a per-stage knob** (not one global choice), and
   **equations are a first-class stage**.

## Reorganized stage flow

| # | Stage | Input scope | Status | Ports from (0604_kg) |
|---|---|---|---|---|
| s00 | **ontology** build + validate | — | ✅ done | `0706_ontology/` |
| s01 | parse (text, sections, tables, figures, formulas) | full | port | `01_docling_extract.py` |
| s02 | figure filter | — | port | `02_figure_filter.py` |
| s03 | plot → data | figure_data (full) | port | `03_plot_to_data.py` |
| s04 | **equations** → structured + ontology-linked | equations (full) | **new** | promote `04_formula_to_data.py` |
| s05 | **scope select** (slice text per stage) | — | **new** | uses existing `sections.json` |
| s06 | schema extract (ontology-typed) | experiment_schema (full) | port | `06_experiment_schema.py` |
| s07 | normalize (QUDT units + dictionary names) | — | port | `07_normalize.py` |
| s08 | link (resolve → ontology individuals) | — | reframe | `08_match.py` |
| s09 | **KG (ontology-grounded)** | — | ✅ done | `09_kg_onto.py` |
| s10 | visualize | — | port | `10_visualize_matches.py` |

## The input-scope decision (your open question)

You asked whether to build the KG from **abstract only / abstract + conclusion /
whole manuscript**. Recommendation: **it's per-stage, not one global choice.**

- **Abstract only** — good for triage/classification, but abstracts almost never
  contain per-experiment conditions, figure data, or governing equations. Too
  sparse to populate the schema.
- **Abstract + conclusion** — enough for *study profiling* and *qualitative
  claims* (what the paper is, what it argues). Cheaper, less noisy, fewer
  hallucinated specifics.
- **Whole manuscript** — required for *quantitative* extraction: per-experiment
  conditions, figure/plot data, and equations. Your current KG uses this — which
  is correct for those stages, but wasteful for the light ones.

Default split lives in [`config.py`](config.py) → `INPUT_SCOPE`. Your parser
already isolates `abstract` / `conclusion` / full text in `sections.json`, so
this is directly implementable. **Don't decide a priori — benchmark it:**
`pipeline.py --benchmark-scope` runs the three scopes on the 3-paper set and
reports schema-field coverage + hallucination rate so the choice is empirical.

## Equations as first-class (s04)

Previously buried in `04_formula_to_data`. Now each equation →
`{latex, symbols, lhs, rhs, described_variables}` with symbols/variables **linked
to ontology QuantityKinds**. This is the attachment point for the v2 model-aware
layer (equation → model → assumptions / validity / parameter priors), per the
perspective paper §4.

## Run

```bash
python3 pipeline.py --list                 # show stages, scopes, status
python3 pipeline.py --stage s09            # run one stage (done stages are wired)
python3 pipeline.py --benchmark-scope      # settle the abstract-vs-full question
```

## Relationship to existing folders

- `0706_ontology/` — the ontology module (kept separate, reused). Source of
  truth for classes/relations/quantities/individuals.
- `0604_kg/` — the previous pipeline. Left intact; stages are ported here one at
  a time (see `PORT_FROM` in config.py). `09_kg_onto.py` already lives there and
  is the s09 implementation.
