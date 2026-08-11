# Repository reorganization — psed_v1 made standalone

The primary requirement was independence: `psed_v1` must run with no
pre-`psed_v1` directory present. Directory cleanup was secondary and served it.

**Result: the active dependency count on historical trees is 0**, enforced by
`tests/integration/test_standalone.py` (14 tests) rather than asserted in prose.

---

## A. BEFORE

```
psed_v1/
├── 00_paper/  01_ontology/  02_extraction/  03_corpus/  04_twin_mpc/  05_orchestration/
├── data/{pdfs,papers}/     tools/     docs/     reports/     papers/
└── paper_layout.py
```

Problems:

| problem | evidence |
|---|---|
| numbers implied an execution order they did not have | `03_corpus` ran *before* `02_extraction`; `00_paper` was a manuscript |
| overlapping responsibilities | `03_corpus/scripts/` held Docling parsing, scout, figure extraction, geometry, pressure and resolve — none of which is corpus discovery |
| two live pipelines | `02_extraction/stages/s06…s09` + `run_all.py` beside `03_corpus/scripts/0*.py`; nothing said which ran |
| split output path | `03_corpus/extracted/<doi>/` and `02_extraction/output/<doi>/` were both per-paper roots |
| half-finished migration | every stage had been repointed to `papers/` **except** `03_docling.py`, which still wrote to `03_corpus/extracted/` — parse output was silently orphaned |
| **runtime dependency on a historical tree** | `stages/lib.py`, imported live by `06_to_kb.py`, did `load_dotenv(REPO / "0604_kg" / ".env")` and indexed `0604_kg/output` |
| five entry points | `run_all.py`, numbered scripts by path, `python3 -m`, direct execution, a dead `pipeline.py` stage table |

Baseline audit: **212 references to historical trees across 54 files.**

---

## B. AFTER

```
psed_v1/
├── README.md  cli.py  paths.py  conftest.py  requirements.txt
├── papers/<id>/{paper.pdf, extracted/, resolved/, canonical/, review.json}
├── papers/_corpus/            corpus-level outputs (KG, recipes)
├── pipeline/{parse,scout,figures,text,resolve,canonical,review}/
├── ontology/                  ALD ontology: source, built JSON, vocab, validation
├── corpus/{discovery,references,acquisition}/
├── twin/                      digital twin / MPC
├── orchestration/             workflow commands
├── resources/config/          prompts, schemas, reference data, config
├── tests/{unit,integration,regression,canonical_layer}/
├── scripts/                   developer utilities
├── docs/                      current documentation
└── reports/                   generated audits and dashboards
```

| directory | responsibility |
|---|---|
| `papers/` | the single source of truth for per-paper artifacts |
| `pipeline/` | PDF → canonical, one subpackage per stage |
| `ontology/` | the ALD ontology and its vocabulary |
| `corpus/` | *which* papers PSED should contain and how to acquire them — owns no parsing |
| `twin/` | model / MPC code |
| `orchestration/` | high-level commands |
| `resources/` | static inputs |
| `tests/` | unit, integration (contract), regression, canonical layer |
| `scripts/` | maintenance utilities, never imported by runtime |
| `reports/` | generated only |

---

## C. MOVE MAP

| old | new | reason |
|---|---|---|
| `03_corpus/scripts/03_docling.py` | `pipeline/parse/docling_parse.py` | Docling parsing is not corpus discovery |
| `03_corpus/scripts/04_extract.py` | `pipeline/scout/scout.py` | it is the relevance selector |
| `03_corpus/scripts/05_figure_extract.py` | `pipeline/figures/figure_extract.py` | figure/panel/curve extraction |
| `03_corpus/scripts/09_geometry.py`, `10_pressure.py` | `pipeline/text/` | text + table extraction |
| `03_corpus/scripts/chemistry_propagation.py` | `pipeline/text/` | resolves chemistry from text |
| `03_corpus/scripts/06_to_kb.py` | `pipeline/resolve/to_kb.py` | entity/condition/case resolution |
| `02_extraction/canonical/*` | `pipeline/canonical/` | genuinely canonicalisation |
| `02_extraction/{build_kg,build_dashboard,build_analysis,build_recipes,viz_recipes}.py` | `pipeline/review/` | review/audit generation |
| `02_extraction/{kb_service,recipe,process_id}.py` | `pipeline/resolve/` | KB services |
| `02_extraction/similarity.py` | `pipeline/canonical/` | comparability |
| `01_ontology/*` | `ontology/` | ontology assets and code |
| `03_corpus/scripts/{07,08}_*ontology*.py` | `ontology/{propose,merge}.py` | ontology maintenance |
| `04_twin_mpc/*` | `twin/` | model code |
| `05_orchestration/*` | `orchestration/` | workflow |
| `03_corpus/scripts/{00_triage,01_refs_to_dois,02_fetch_pdfs}.py` | `corpus/{discovery,references,acquisition}/` | this *is* corpus work |
| `03_corpus/pdfs/` | `corpus/acquisition/pdf_inbox/` | un-parsed candidates, not papers |
| `02_extraction/output/{knowledge_graph,recipes}*` | `papers/_corpus/` | corpus-level outputs |
| `03_corpus/{extraction_calls,manifest,reextract_*}` | `reports/extraction_runs/` | generated run logs |
| `00_paper/` | `docs/paper/` | it is a manuscript |
| `data/papers/*.pdf` (3 unique) | `corpus/acquisition/pdf_inbox/` | un-parsed candidates |
| `tools/*` | `scripts/` + `tests/integration/` | utilities vs contract tests |
| `paper_layout.py` | `paths.py` | promoted to THE path API |
| **`02_extraction/stages/lib.py` (vocabulary half)** | **`ontology/vocab.py`** | **the port that removed the last runtime dependency on `0604_kg`** |

### Removed from the active tree (git history retains them)

| removed | why |
|---|---|
| `02_extraction/stages/{s06,s07,s08,s09,c1_accuracy,methods_recipe,caption_params}.py` | dead second pipeline; `docs/PIPELINE.md` already called it dead |
| `02_extraction/{run_all,pipeline,config,assess,evaluate_kb}.py` | dead orchestrators; `pipeline.py` pointed at `0604_kg` |
| `02_extraction/benchmark/` | resolved paths into `0604_kg` |
| `01_ontology/evaluate_relations.py` | read a `0604_kg` KG path |
| `02_extraction/output/_archive/` (33 files) | superseded snapshot, fully committed; the diff tool now takes `--before` as an argument |
| `scripts/run_reextract.py` | drove the numbered layout by subprocess; `cli.py` supersedes it |
| `twin/pid_controller.py` | imported a `deps` module that exists nowhere |
| `03_corpus/scripts/relabel_figures.py`, `tools/{migrate_to_paper_folders,repoint_paths}.py` | one-off migrations already applied |
| `data/pdfs/*.pdf` (4) | byte-identical duplicates of `papers/<id>/paper.pdf`, verified by SHA-256 |

---

## D. ACTIVE PIPELINE

```
python3 cli.py parse      -> pipeline/parse/docling_parse.py
python3 cli.py scout      -> pipeline/scout/scout.py
python3 cli.py figures    -> pipeline/figures/figure_extract.py
python3 cli.py geometry   -> pipeline/text/geometry.py
python3 cli.py pressure   -> pipeline/text/pressure.py
python3 cli.py resolve    -> pipeline/resolve/to_kb.py
python3 cli.py canonical  -> pipeline/canonical/build_canonical.py
python3 cli.py kg         -> pipeline/review/build_kg.py
python3 cli.py review     -> pipeline/review/{build_dashboard,build_analysis,
                                              build_recipes,viz_recipes,
                                              corpus_status,corpus_dashboard}.py
python3 cli.py ontology   -> ontology/build_ontology.py
python3 cli.py validate   -> tests/integration/*
```

`cli.py` is the only supported entry point.

---

## E. PATH CONTRACT

Every location comes from `paths.py`; no module builds a per-paper path itself
(asserted by `SinglePathContract.test_paths_module_is_the_only_root_definition`).

| artifact | authoritative location | accessor |
|---|---|---|
| PDF | `papers/<id>/paper.pdf` | `pdf_path(id)` |
| Docling output | `papers/<id>/extracted/{document.md,structure.json,figures/}` | `document_md`, `structure_json`, `figures_dir` |
| scout / card | `papers/<id>/extracted/{scout,card}.json` | `scout_json`, `card_json` |
| figure extraction | `papers/<id>/extracted/{figure_data,records}.json` | `figure_data_json`, `records_json` |
| text extraction | `papers/<id>/extracted/{geometry,pressure}.json` | `geometry_json`, `pressure_json` |
| resolved | `papers/<id>/resolved/*.json` | `resolved_json(id, name)` |
| canonical | `papers/<id>/canonical/curves.json` | `curves_json(id)` |
| review | `papers/<id>/review.json` | `review_path(id)` |
| corpus-level | `papers/_corpus/` | `CORPUS_OUT`, `knowledge_graph_json()` |

---

## F. LEGACY DEPENDENCY AUDIT

| | before | after |
|---|---:|---:|
| references to historical trees (source files) | 212 | **0** |
| imports from historical trees | 3 | **0** |
| runtime file reads from historical trees | 5 | **0** |
| `sys.path` escapes | 9 | **0** |
| subprocess calls into historical scripts | 2 | **0** |
| references to the old numbered layout | ~90 | **0** |

Remaining mentions and why they are allowed:

- `docs/` and `reports/` describe history (e.g. `reports/docling_forensics/REPORT.md`
  reconstructs the old Docling pipeline). These are prose, excluded by the audit,
  and give no instruction to run historical code.
- `tests/integration/test_standalone.py` and `validate_layout.py` contain the
  banned names **as the patterns they forbid**; they exempt themselves.
- `ontology/vocab.py` names `0604_kg` once, in the docstring explaining what the
  port removed. `tests/unit/test_vocab_port.py` asserts no such path is used.

---

## G. DATA-SAFETY CHECK

SHA-256 of every file under `papers/` before and after:

```
before: 1420 files      after: 1425 files
missing: 0     changed: 0     added: 5
added = papers/_corpus/{knowledge_graph_onto.json, .graphml,
                        recipes.json, recipe_accounting.json, kb_derived/}
```

No paper artifact was lost or altered. The five additions are corpus-level
outputs relocated from `02_extraction/output/`. The smoke test regenerated
`10.1063_1.5028178` and produced **byte-identical** output, which is the
strongest evidence the move changed no science. `data/pdfs` deletions were
verified as byte-identical duplicates before removal.

---

## H. TEST RESULTS

| suite | result |
|---|---|
| `tests/integration/test_standalone.py` | **14 / 14 pass** — the acceptance test |
| `tests/canonical_layer/` | **220 / 220 pass** |
| `tests/unit/test_vocab_port.py` | **5 / 5 pass** |
| `tests/regression/` (13 script suites) | 12 pass, 1 pre-existing failure |
| smoke test | `cli.py resolve 10.1063_1.5028178` → 19 entities, 2 cases, byte-identical |

The ten required structural checks are covered:
module imports (`test_every_active_module_imports`), path resolution
(`test_every_artifact_resolves_under_one_paper_root`), Docling output location
(`test_docling_writes_into_the_paper_folder`), scout/figures/resolve/canonical
reading the same folder (`test_stages_read_the_same_paper_folder`), no historical
paths (`test_no_runtime_reference_to_historical_trees`), no duplicate output root
(`test_no_second_active_paper_output_root`), existing JSON still loads (the
canonical suite), and the Scout assumption (`ScoutRole`, 3 tests).

**`tests/regression/test_m2_design.py` — 5 failures, pre-existing and unrelated.**
They date from the chemistry correction two tasks ago: the twin can no longer
design a 60 µm penetration depth for Al2O3 because it was previously using
TiO2's sticking coefficient, mislabelled Al2O3. Re-baselining the twin's expected
envelope is a scientific decision, still open.

---

## I. SCOUT ROLE CLEANUP

`pipeline/scout/scout.py` asserted twice that figures are experiments:

- *"different figures are different experiments (different samples, conditions,
  or channel geometries)"*
- *"Same-type figures are separate experiments (different samples/conditions)"*

Both are gone. The **coverage** rule is unchanged — every data-bearing panel is
still drilled — but its justification is now coverage, not identity, and the
prompt states explicitly that several figures may show one sample, one figure may
hold several process conditions, one case may span figures, and that measured /
calculated / fitted / model / simulation / characterization / derived curves are
different kinds. Physical experiment identity is resolved downstream.

Pinned by `ScoutRole` (3 tests).

---

## J. DEFERRED

Explicitly **not** addressed here, and unchanged by this refactor:

1. `10.1002/cnma.201700148` figure-selection / caption-recovery failure.
2. Broader figure-selector recall audit (422 of 561 Docling figures are never
   digitised — see `reports/docling_forensics/REPORT.md`).
3. Text/table-derived `PhysicalCase` creation — today no record can be created
   from prose or a table; 67 extracted tables contribute none.
4. Paper-global cross-figure `PhysicalCase` reconciliation.
5. Any corpus regeneration caused by the above.
6. Twin M2 re-baselining after the chemistry correction (see §H).
