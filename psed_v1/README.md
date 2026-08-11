# PSED — Process–Structure Extraction Database

PSED turns published ALD papers into a structured, provenance-carrying knowledge
base: what was deposited, under which conditions, measured how, and with what
result — each record traceable to the figure, caption, table or sentence it came
from.

**This directory is self-contained.** Copy `psed_v1/` into an empty repository,
install `requirements.txt`, and every supported command runs. Nothing here
imports, reads or resolves a path into any pre-`psed_v1` tree; that is enforced
by `tests/integration/test_standalone.py`.

## Quick start

```bash
pip install -r requirements.txt
python3 cli.py --help                 # the supported entry point
python3 cli.py resolve --all --resolve-only   # rebuild the KB, no API key needed
python3 cli.py validate               # structural + standalone checks
```

Stages that call an LLM (`scout`, `figures`, `geometry`, `pressure`, and the
first `resolve` of a new paper) need `GOOGLE_API_KEY` in the environment or in
`resources/config/corpus/.env`. Everything downstream is deterministic.

## Execution order

```
        papers/<id>/paper.pdf
                 │
   parse         │  Docling: markdown, headings, captions, tables, figure crops
                 ▼
        extracted/document.md, structure.json, figures/
                 │
   scout         │  relevance + coverage: which figures/tables to inspect
                 ▼
        extracted/scout.json
                 │
   figures ──────┼────── geometry / pressure        (figure vision | text+tables)
                 ▼
        extracted/figure_data.json, records.json, geometry.json, pressure.json
                 │
   resolve       │  entity identity, granularity, conditions, chemistry
                 ▼
        resolved/{entities,experiments,series,assertions,results}.json
        review.json
                 │
   canonical     │  units, comparability, axis semantics
                 ▼
        canonical/curves.json
                 │
   kg / review   │  knowledge graph + dashboards
                 ▼
        papers/_corpus/knowledge_graph_onto.json, reports/*.html
```

Scout decides **coverage** ("which results should be inspected"), never
experiment identity. How many physical experiments a paper contains is resolved
in `pipeline/resolve` from paper-global evidence.

## Layout

| directory | responsibility |
|---|---|
| `papers/<id>/` | **the single source of truth** for every per-paper artifact |
| `papers/_corpus/` | corpus-level outputs (knowledge graph, recipes) — not per paper |
| `pipeline/` | the extraction pipeline: `parse`, `scout`, `figures`, `text`, `resolve`, `canonical`, `review` |
| `ontology/` | the ALD ontology: source YAML, built JSON, vocabulary, validation |
| `corpus/` | *which papers should PSED contain, and how do we get them* — discovery, references, acquisition. It owns no parsing |
| `twin/` | digital twin / MPC models |
| `orchestration/` | high-level workflow commands |
| `resources/` | prompts, schemas, reference data, config |
| `tests/` | `unit`, `integration`, `regression`, `canonical_layer`, `fixtures` |
| `scripts/` | developer and maintenance utilities |
| `docs/` | current documentation |
| `reports/` | generated audits and dashboards |
| `paths.py` | the ONE path API — every runtime module resolves locations through it |
| `cli.py` | the ONE entry point |

## Per-paper contract

```
papers/<paper_id>/
    paper.pdf              source
    extracted/             parse + scout + figure/text extraction   (generated)
    resolved/              entities, experiments, series, results   (generated)
    canonical/curves.json  comparability layer                      (generated)
    review.json            per-paper review manifest                (generated)
```

`<paper_id>` is the filesystem-safe DOI (`10.1063/1.5028178` →
`10.1063_1.5028178`), so the folder name follows from the DOI alone.

**Source vs generated:** `paper.pdf` and everything under `ontology/`,
`resources/`, `pipeline/`, `twin/`, `corpus/` is source. Everything under
`papers/<id>/extracted|resolved|canonical`, `papers/_corpus/`, and `reports/` is
generated and reproducible from the stages above.

## Adding a paper

```bash
python3 cli.py parse path/to/paper.pdf     # -> papers/<id>/extracted/
python3 cli.py scout <id>
python3 cli.py figures <id>
python3 cli.py geometry <id> && python3 cli.py pressure <id>
python3 cli.py resolve <id>
python3 cli.py canonical --paper <id>
```

## Tests

```bash
python3 -m unittest discover tests/canonical_layer   # 220 canonical-layer tests
python3 -m unittest discover tests/integration       # standalone + layout contract
for t in tests/regression/*.py; do python3 "$t"; done
```
