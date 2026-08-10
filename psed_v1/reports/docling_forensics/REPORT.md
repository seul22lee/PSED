# Forensic audit — where the Docling-derived document artifacts went

Read-only. Nothing was modified, repaired or regenerated.

**Verdict up front: your memory is correct, and the loss is real but narrower
than "the artifacts disappeared".** `document.md` still exists for every paper
and is heavily used — 82 % of all condition assertions come from it. What was
lost is (a) the *richer* Docling artifact set (`document.json`, per-table
CSV/HTML, equation crops), and (b) an entire **text-derived record-extraction
chain** that once turned prose into structured measurements. Today no
experimental record can be created from text or tables — only from digitised
figure series.

---

## 1. Historical pipeline

Two generations existed before the current one.

### Generation 1 — `0226_kb/` and `0529_kg/` (Feb–Jun 2026)

`01_docling_extract.py` (`cd55090` 2026-02-27, still present under
`old/0226_kb/`, `old/0529_kg/`) wrote **per paper**:

```
<paper>/01_docling/
    document.md                    markdown export
    document.json                  the FULL docling document model
    tables/table-NNN.csv           each table as structured data
    tables/table-NNN.html
    tables/tables.json             captions + page provenance
    figures/figure-NNN.png         figure crops
    figures/figures.json           captions + page_nos + self_ref
    formulas/equation-NNNN.png     cropped equations
    formulas/formulas.json
```

It carried page numbers, bounding boxes and `self_ref` pointers
(`_safe_page_nos`, `_caption_text_from_item`, `_find_caption_from_layout`).

Downstream, a **text-first chain** consumed it:

```
document.md
  → 04_build_segment.py     → segments.json                    (segmentation)
  → 05_sentence_tagging.py  → geometry_tags.json               (LLM, per domain)
                              reaction_tags.json
                              transport_tags.json
  → 06_evidence_pools.py    → geometry_evidence.json  etc.     (evidence pools)
  → 07_schema_extraction.py → schema-filled JSON per model family
  → 08_KG*.py               → knowledge graph
```

This produced structured records **from prose**, independently of any figure.

### Generation 2 — `0706_pipeline` / `psed_v1/02_extraction/stages/`

`s06_study_profile → s07_experiment → s08_resolve → s09_kg`, with two
deterministic text readers: `methods_recipe.py` (recipe from `document.md`) and
`caption_params.py` (figure-level conditions from captions).

`docs/PIPELINE.md` already declares this generation **dead**; only `stages/lib.py`
is still imported. `methods_recipe.py` is imported **only** by `s08_resolve.py`,
which nothing calls — so that text→recipe reader is dead code.

---

## 2. Current pipeline (exact data flow)

```
papers/<doi>/paper.pdf
   │
   │  03_corpus/scripts/03_docling.py :: run()/main()          [docling 2.75, no LLM]
   ▼
   extracted/document.md          full markdown
   extracted/structure.json       {n_pages, sections[HEADINGS ONLY],
                                   figures[{index,caption,image}],
                                   tables[{index,caption,markdown}]}
   extracted/figures/fig_N.png    figure crops
   │
   ├─ 04_extract.py :: build_scout_input() → abstract_of(md) + section_text(md,["conclusion"…])
   │        + figure/table CAPTIONS  ──LLM──▶ extracted/scout.json
   │        (+ extracted/scout_input.txt, only via the separate dump_scout_input())
   │
   ├─ 05_figure_extract.py :: extract_paper()  ──VISION LLM on fig_N.png──▶
   │        extracted/figure_data.json   (panels, axes, series, points)
   │        extracted/records.json       (one flattened row per drawn curve)
   │
   ├─ 09_geometry.py  (document.md + structure.json tables, LLM) → extracted/geometry.json
   ├─ 10_pressure.py  (document.md + structure.json tables, LLM) → extracted/pressure.json
   │
   └─ 06_to_kb.py
          inputs : scout.json, records.json, card.json, document.md,
                   structure.json, geometry.json, pressure.json,
                   figure_data.json, recovery/*.json
          card   : get_card() → section_text(md,["experimental","methods",…])
                   + ALL table markdown  ──LLM──▶ extracted/card.json  (cached)
          loop   : to_experiments() ⟶  `for r in records:`      ◀── THE ONLY RECORD SOURCE
          ▼
   resolved/{entities,experiments,series,assertions,counts,results}.json
   resolved/review.json
   canonical/curves.json           (canonical/build_canonical.py)
   02_extraction/output/knowledge_graph_onto.json  (build_kg.py, corpus-level)
```

---

## 3. Artifact inventory

| artifact | location | producer | consumers | active |
|---|---|---|---|---|
| `paper.pdf` | `papers/<doi>/` | `02_fetch_pdfs.py` | `03_docling.py` | ✅ |
| `document.md` | `extracted/` | `03_docling.py` | `04_extract` (abstract/conclusion), `06_to_kb` (`_methods`, `_figure_body`, `_document`), `09_geometry`, `10_pressure`, `canonical/sources.py`, `recover_axis_semantics` | ✅ **heavily** |
| `structure.json` | `extracted/` | `03_docling.py` | `04_extract` (captions), `06_to_kb` (table markdown → card; table captions → classifier signal `T`), `09_geometry`, `10_pressure` | ✅ partial |
| `figures/fig_N.png` | `extracted/` | `03_docling.py` | `05_figure_extract` (vision) | ✅ |
| `scout.json` | `extracted/` | `04_extract.py` | `05_figure_extract`, `06_to_kb` | ✅ |
| `scout_input.txt` | `extracted/` | `04_extract.py::dump_scout_input()` | **nothing** — audit only | ⚠️ on-demand; absent for most papers |
| `card.json` | `extracted/` | `06_to_kb.py::get_card()` | `06_to_kb` | ✅ |
| `figure_data.json` | `extracted/` | `05_figure_extract.py` | `06_to_kb`, `canonical/sources.py` | ✅ |
| `records.json` | `extracted/` | `05_figure_extract.py` | `06_to_kb::to_experiments` | ✅ **sole record source** |
| `geometry.json` | `extracted/` | `09_geometry.py` | `06_to_kb::geometry_facts` | ✅ conditions only |
| `pressure.json` | `extracted/` | `10_pressure.py` | `06_to_kb` via `pressure10.pressure_facts` | ✅ conditions only |
| `raw/*.json` | `extracted/` | `_genai_shim.py` | **nothing** — raw LLM responses kept for audit | ⚠️ archival |
| `recovery/axis_semantics_v1.json` | `extracted/` | `canonical/recover_axis_semantics.py` | `canonical/sources.py` | ✅ |
| `recovery/figure_semantics_v1.json` | `extracted/` | `canonical/reextract_figures.py` | `06_to_kb::_axis_labels`, `sources.recovery_index` | ✅ |

All of the above are **tracked in git**, not ignored. `.gitignore` excludes only
`.env`, `__pycache__/`, `old/extract-line-chart-data/` and one HTML file.

---

## 4. Lost / moved / deprecated

| what | when | evidence |
|---|---|---|
| `document.json` (full docling model) | dropped at generation 2 | present in `old/0529_kg/output_old/*/01_docling/document.json`; `03_docling.py` never writes it |
| `tables/*.csv`, `tables/*.html` | dropped at generation 2 | `old/0529_kg/.../01_docling/tables/`; today tables survive only as markdown inside `structure.json` |
| `formulas/equation-*.png`, `formulas.json` | dropped at generation 2 | `old/0529_kg/.../01_docling/formulas/` |
| page numbers / bbox / `self_ref` provenance | dropped at generation 2 | `_safe_page_nos()` in the old script; `structure.json` has no page field per figure/table |
| **text-derived record chain** (`segments.json`, `*_tags.json`, `*_evidence.json`, schema extraction) | dropped at generation 3 (`psed_v1`) | files still on disk under `old/0226_kb/extracted/`, `old/0529_kg/output_old/`; **no successor in `psed_v1`** |
| `methods_recipe.py` text→recipe reader | orphaned at generation 3 | imported only by `s08_resolve.py`, which nothing calls |
| section **bodies** | never stored | `structure.json["sections"]` is a list of heading *strings*; bodies are re-derived on demand by `section_text(md, …)` |
| abstract | never stored as a file | computed on the fly by `abstract_of(md)` inside `build_scout_input()` |

Nothing was deleted from git history; the old trees live under `old/`.

**Live break introduced by the recent folder migration:** every stage was
repointed to `papers/` **except `03_docling.py`**, which still has
`OUT = ROOT / "extracted"` → `03_corpus/extracted/`, a directory that no longer
exists. Re-running stage 1 today would write into an orphaned tree that nothing
reads.

---

## 5. Three paper traces

| | pssa.201532305 | 1.5028178 | celc.201600139 |
|---|---:|---:|---:|
| `paper.pdf` | 669 KB | 1293 KB | 1326 KB |
| `document.md` | 32 650 chars | 32 017 | 28 469 |
| `structure.json` figures / tables | 17 / 1 | 16 / 0 | 20 / 0 |
| `figure_data.json` figures / series | 10 / 28 | 6 / 19 | 4 / 17 |
| `records.json` | **28** | **19** | **17** |
| `resolved/entities.json` | **28** | **19** | **17** |
| `resolved/results.json` | **28** | **19** | **17** |
| `resolved/experiments.json` (cases) | 47 | 2 | 17 |
| `resolved/assertions.json` | 992 | 298 | 227 |

Code responsible for each transition: `03_docling.py::main` → `04_extract.py::scout`
→ `05_figure_extract.py::extract_paper` → `06_to_kb.py::to_experiments` (the
`for r in records:` loop) → `resolve_source_entities` → `build_results_view` /
`write_review_manifest` → `canonical/build_canonical.py`.

**`records.json` == `entities.json` == `results.json` in all three.** The entity
population is exactly the digitised-figure-series count.

---

## 6. Coverage gap — verified, not inferred

Which upstream sources can **create a record** vs only **decorate** one:

| downstream artifact | figure/plot | body text | abstract | tables | captions | manual recovery |
|---|---|---|---|---|---|---|
| `records.json` | **creates** | — | — | — | — | — |
| `entities.json` | **creates** | decorates | — | decorates | decorates | decorates |
| `experiments.json` | **creates** | decorates | — | decorates | decorates | — |
| `series.json` | **creates** | decorates | — | — | — | — |
| `results.json` | **creates** | decorates | — | decorates | decorates | decorates |
| `assertions.json` | series labels only | **creates** | — | — | **creates** | — |
| `canonical/curves.json` | **creates** | — | — | — | decorates | decorates |
| `review.json` | **creates** | decorates | — | decorates | decorates | — |

Evidence that text is alive but only as decoration — assertion `source_kind`
across the corpus:

```
methods        3652      ← document.md
body           1742      ← document.md
caption         939      ← structure.json / figure_data.json
series_label    236      ← figure extraction
```

82 % of condition assertions are text-derived. But every one of them is *bound to
an entity that a figure created*. There is no code path in which a sentence or a
table row produces an `ExperimentalCase`.

Unused Docling yield, corpus-wide:

| | count |
|---|---:|
| figures Docling found | 561 |
| figures with a caption | 242 |
| figures sent to figure extraction | **139** |
| **figures never digitised** | **422** |
| tables Docling extracted | **67** |
| records created from tables | **0** |
| records created from body text | **0** |

The abstract is read once (scout) and never stored. Section bodies are never
stored; only headings are.

---

## 7. Git evidence

| conclusion | evidence |
|---|---|
| richer Docling stage existed | `git show cff1ec8:0529_kg/01_docling_extract.py` — writes `document.json`, `tables/*.csv|html`, `figures/*.png`, `formulas/*.png` (lines 93–201) |
| text-derived record chain existed | `0226_kb/{03_section_splitter,04_build_segment,05_sentence_tagging,05_measurement_extraction,06_evidence_pools,07_schema_extraction}.py` in `git log --all --name-only` |
| its outputs still exist | `old/0226_kb/extracted/*/segments.json`, `old/0529_kg/output_old/*/05_sentence_tagging/*_tags.json` |
| current Docling stage is narrower | `03_corpus/scripts/03_docling.py` writes only `document.md` + `structure.json` (+ figure crops) |
| generation-2 stages are dead | `reports/docs__PIPELINE.md:145` marks `run_all.py`/`config.py` dead; `methods_recipe` imported only by `s08_resolve` |
| records come only from figures | `06_to_kb.py:1633` `for r in records:`; `records` loaded at `:1944` from `records.json`, written by `05_figure_extract.py:253` |
| stage 1 path is orphaned | `03_docling.py:15` `OUT = ROOT / "extracted"`; `ls 03_corpus/extracted` → does not exist |

Commit timeline: `cd55090` 2026-02-27 (gen 1) → `cff1ec8` 2026-06-05 → `e09b93f`
2026-07-09 (`0709_corpus/scripts/03_docling.py`) → `69fb99b` 2026-07-22
(`psed_v1`, gen 3).

---

## 8. Where your memory and the repository differ

- **Correct:** Docling ran first on each PDF; structured content (sections,
  captions, tables) was extracted and fed downstream.
- **Correct:** a richer artifact set existed and is no longer produced.
- **Partly different:** the abstract and section *bodies* were never stored as
  separate files even in generation 1 — they were always derived on demand from
  `document.md`. What was stored separately were tables, figures and equations.
- **Different:** the Docling text artifacts were not *lost*. `document.md` is
  intact for all 32 papers and is the single largest evidence source in the
  pipeline. What was lost is the **chain that turned text into records**.

---

## 9. Recommended next action (not implemented)

Three separable items, in order of value:

1. **Fix the orphaned stage-1 path** (one line, `03_docling.py`). Until then any
   new paper's Docling output lands where nothing reads it. This is a live break,
   not a design question.
2. **Decide whether text/table-derived records should exist again.** The honest
   framing: the corpus currently answers "what did the figures show?", not "what
   experiments does this paper report?". 67 extracted tables and every methods
   paragraph are available and unused for record creation. A minimal version
   would mint `ExperimentalCase` records from a conditions table when it
   enumerates runs, reusing the existing evidence/ambiguity machinery.
3. **Preserve richer Docling output** (`document.json`, per-table CSV, page
   provenance). Cheap to add back to `03_docling.py`; page numbers in particular
   would let a caption or table be tied to a figure without the printed-vs-docling
   index guessing that has already caused one collision bug.

I recommend doing (1) alone first, since it is unambiguous, and treating (2) as a
scoping decision for you rather than something to infer.
