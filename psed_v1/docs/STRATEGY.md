# ALD Knowledge Base — Strategy & Roadmap

**Vision.** An ontology-grounded, model-aware knowledge base that turns ALD papers
into structured, linkable, FAIR experiment records — and eventually feeds a
stage-aware digital twin (design → develop → control), per
`0701_paper/ALD_perspective_stage_aware_revised.md`. Modeled on ATLAS (tribology)
but going further: the KB is *model-aware* (links data → equations → priors).

Legend: ✅ done · 🔶 partial · ⬜ pending

---

## Layer map (what the system is made of)

| Layer | Purpose | Status | Where |
|---|---|---|---|
| **0. Ontology** | Shared typed backbone (classes, relations, quantities, granularity) | ✅ v0.3 | `0706_ontology/` |
| **1. Extraction** | PDF → evidence scope → ontology-grounded experiments | 🔶 (0604 works; 0706 redesign proposed) | `0604_kg/`, `0706_pipeline/` |
| **2. Knowledge graph** | Instantiate experiments/links against the ontology | 🔶 (builder done) | `0604_kg/09_kg_onto.py` |
| **3. Knowledge tools** | Informatics, meta-analysis, RAG Q&A, lit-review agent | ⬜ | (ATLAS parity) |
| **4. Model-aware / twin** | Equations, assumptions, priors → contact-mechanics/MPC | ⬜ (v2) | `PSED_MPC/`, `aldmodeling_agent/` |

---

## Workstream status (what's been explored)

### Layer 0 — Ontology  (`0706_ontology/`)
- ✅ v0.1 backbone → v0.2 audited vs **Cremers 2019** + **Kessels 2025**: 200 classes, 34 relations, 121 quantities (93 QUDT-enriched), 164 individuals.
- ✅ **quantity_relations** layer: `specializes`, 13 `defined_by` equations, `qualifiers`, `same_as` (quantity-web 6→56 edges).
- ✅ **granularity model** (v0.3): `axis_role` (coordinate/condition/output), `varies`/`in_series`/`series_varies`, `ExperimentSeries`.
- ✅ Tooling: `build_ontology.py`, `validate.py`, `visualize_ontology.py`→`ontology.html`, `evaluate_relations.py`.
- ⬜ Relation cleanup (from `evaluate_relations.py`): declare characteristics (inverse/symmetric/transitive/acyclic); close 3 competency gaps (Structure→FlowRegime, Quantity→Method, Material→Application); wire 9 orphan branches; fix `governed_by` direction.
- ⬜ External alignment: resolve `emmo_todo`/`chebi_todo` to real IRIs.
- ⬜ FAIR export: `build_owl.py` (OWL/TTL, needs `rdflib`).

### Layer 1 — Extraction  (`0604_kg/`, `0706_pipeline/`)
- ✅ 0604 pipeline works: docling → figure filter → plot-to-data → formula → **enrich (evidence region)** → **per-series experiment schema** → normalize → match.
- ✅ **Scope benchmark** (`0706_pipeline/benchmark/`): **evidence scope wins** (mean recall 51% vs 24%; quantitative 69%; higher precision than full). `INPUT_SCOPE` set in `config.py`.
- ✅ Review of 0604 experiment extraction → **6 upgrades** identified (see below).
- ⬜ **Experiment-extraction redesign** (the core next build): ontology-generated schema, two-tier (study_profile + per-figure), granularity resolution, ontology-driven normalization, quantity enrichment, relevance filter.
- ⬜ Enrich evidence slice (full tables + results paragraphs) to lift quant recall past 69%.

### Layer 2 — Knowledge graph
- ✅ `09_kg_onto.py`: ontology-typed nodes, `QuantityValue`+role, exact shared-node linking (37 experiments, 0 flagged).
- ⬜ Re-run on redesigned extraction; formalize `ExperimentSeries`/`varies` links; demote `similar_to` to secondary.

### Layer 3 — Knowledge tools (ATLAS parity)  ⬜
- Informatics dashboards, meta-analysis (claim agreement/contradiction), RAG Q&A, literature-review agent. Building blocks exist in `aldmodeling_agent/`.

### Layer 4 — Model-aware / digital twin (v2)  ⬜
- Populate `Model` nodes with equations + assumptions + validity + parameter priors; connect to `PSED_MPC/` (contact mechanics / MPC). This is the perspective paper's payoff.

---

## The 6 extraction upgrades (Layer 1 redesign detail)
1. **Apply granularity** (`axis_role`): fixes 16/37 indep/controlled confusion; split condition-sweeps; group series.
2. **Ontology-driven normalization**: drop hardcoded `MATERIAL_MAP`/`STRUCTURE_MAP`/unit tables; use ontology aliases + QUDT units.
3. **Ontology-generated schema + canonical ids**: generate fields from the ontology; LLM emits canonical names.
4. **Two-tier + relevance filter**: paper `study_profile` (evidence scope) → per-figure experiments; tag background vs experimental (fixes intro `TiN`/`TaN`).
5. **Quantity enrichment**: `of_reactant`/`of_position` qualifiers, derive via `defined_by` (`exposure=P·t`), reconcile unit-variants.
6. **Link via ontology structure** (shared individuals + `ExperimentSeries`), `similar_to` secondary.

---

## Recommended execution order (dependencies → phases)

- **Phase A — Ontology cleanup** *(small, optional-now)*: relation characteristics + 3 competency gaps + orphans + `governed_by` fix. Cheap; makes the ontology clean/publishable. Can run anytime.
- **Phase B — Extraction redesign** *(core, unblocked)*: build the ontology-grounded experiment path in `0706_pipeline` — reuse 0604 stages 01–05, then new **s06 study_profile → s07 experiment (ontology schema) → s08 resolve (granularity+normalize+enrich+relevance) → s09 link/KG**. This is where "better" concentrates.
- **Phase C — Validate & scale**: run on the 3 papers, verify the 16/37 granularity fixes, then scale to the queued corpus.
- **Phase D — FAIR polish**: resolve EMMO/ChEBI IRIs; OWL/TTL export.
- **Phase E — Knowledge tools**: informatics, meta-analysis, RAG Q&A, lit-review agent; enrich evidence slice.
- **Phase F — Model-aware v2 / twin**: equations/assumptions/validity/priors → `PSED_MPC`.

Recommended immediate focus: **Phase B** (optionally do the quick Phase A cleanup first since it's cheap and everything downstream reads the ontology).

---

## Open decisions (yours to sequence)
1. Phase A now, or fold into Phase B as we touch the ontology?
2. Phase B build order: start with **s07 (experiment extractor)** or **s08 (resolve/granularity)**?
3. Scale target for Phase C (how many of the 300+ queued DOIs)?
4. Is the digital-twin/model-aware v2 (Phase F) in scope for the current paper, or a follow-on?
