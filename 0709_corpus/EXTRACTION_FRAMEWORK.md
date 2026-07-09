# Token-efficient, ontology-grounded extraction framework (for ~1000 papers)

The 4-paper pipeline (0604_kg → 0706_pipeline) works but assumes every paper is
relevant and processes every figure. At ~967 papers that is ~10⁷–10⁸ LLM tokens,
most of it wasted on irrelevant papers and non-data figures. This is the redesign.

**Governing principle — *coarse-to-fine, cheapest-capable-tool-first*:**
spend an LLM token only when (a) the paper is relevant, (b) the segment carries
data, and (c) no deterministic method can extract it. Everything is gated, cached,
tiered, and incremental.

```
DOI ──▶ [0 triage]──drop 60%──▶ [1 structure]──▶ [2 deterministic]──▶ [3 gated LLM]──▶ [4 resolve]──▶ KB
        no LLM                    docling,no LLM     regex/dict,no LLM    tiered+cached     no LLM
                                                                          +caption-gated figs
```

---

## Stage 0 — Triage (NO LLM) — *the biggest single lever*
Most of the 967 refs are not extractable ALD process/data papers (reviews, tangential
citations, instrument papers). Gate them out before any compute.

- **0a. Metadata enrichment** (Crossref `GET works/{doi}`, free): title + abstract +
  subject. Needed because only 244/967 reference entries carry a title. → `metadata.jsonl`.
- **0b. Relevance scoring** (deterministic, ontology-vocabulary): score title+abstract
  against the ontology's controlled terms — materials, precursors, coreactants (+aliases)
  and keyword sets (ALD-core, data-signals: *growth per cycle / saturation / conformality
  / penetration / sticking / step coverage*; property-signals: *density / refractive index
  / resistivity*; process-signals: *temperature / dose / pulse / purge / cycles*).
  → `triage.csv` with `relevance_score`, `tier` (high/med/low/reject), and a
  `predicted_content` flag set (has_saturation, has_conformality, has_properties, …).
- **Effect:** 967 → ~250–400 that proceed. **0 LLM tokens.**

## Stage 1 — Structure (docling, NO LLM)
PDF → `sections.json`, `tables/`, `figures/` + captions, `document.md`. Already built.
- **Segment router:** keep value-bearing segments (methods/experimental, results tables,
  data figures); discard intro/refs/acknowledgments. Extraction only ever sees value
  segments, never the whole PDF.

## Stage 2 — Deterministic extraction (NO LLM) — *second lever*
Most "process-card" fields need no model:
- **Process conditions** from methods text by rules (generalized `methods_recipe.py`):
  temperature, pressure, dose/pulse, purge, cycles, flow, reactor, precursor/coreactant.
- **Chemistry NER**: dictionary match of material/precursor/coreactant against ontology
  individuals + aliases.
- **Tables**: docling gives table structure → parse rows → map headers to ontology
  `quantity_kinds` by fuzzy dictionary match. Only **unmapped** headers escalate to LLM.
- **Effect:** the recipe/chemistry/process-window fields are filled at **0 tokens**; the
  LLM only sees the residual.

## Stage 3 — Gated LLM extraction (tiered · cached · batched · **caption-gated**)
Only now, and only on what's left.

- **Pass 0 — SCOUT (read the cheap parts first; decide depth).** One ontology-constrained
  call on **abstract + conclusion + figure/table captions only** (~1–2 k tokens, not the
  8–15 k full text) returns a *role-separated process card* (materials / precursors /
  coreactants / process_type / T-window / GPC), a **drill list** (exactly which figures/
  tables hold which data type), and a `go_deeper` flag. Deep work runs ONLY on the drill
  list. *Measured on 3 new-chemistry papers (BaO, Y₂O₃, Ir): ~2 k tokens/paper, correct
  chemistry incl. novel precursors, correct data routing, and — crucially — it leaves
  unknown fields empty + go_deeper=true rather than hallucinating.* Implemented in
  `scripts/04_extract.py`; this is the token-efficient front door that subsumes the old
  figure-by-figure extraction. It also fixes audit E1–E4 by construction (role-separated,
  caption-gated, no model/experiment conflation).

- **Caption-gated figure processing (do figures only when the caption proves it):**
  a figure is expensive twice — vision **digitization** and a per-figure **LLM** call.
  Gate both on the caption (free docling text):
  1. **type**: data-plot vs schematic/micrograph/photo (keywords: *"vs" / "as a function
     of" / axis units*, vs *"schematic / cross-section / TEM / SEM / XRD"*). Non-plots skip.
  2. **relevance**: does the plotted y-quantity map to an ontology measurand we want
     (GPC, thickness, penetration, coverage, sticking, …)? If not → skip.
  3. only figures passing **both** get digitized + sent to the LLM.
  → a 10-figure paper typically drops to ~2–3 processed figures. A tiny caption classifier
  (keyword-first; Haiku only if ambiguous) decides; the caption is ~40 tokens, the figure
  pipeline it saves is thousands.

- **Pass A — process card** (cheap model, e.g. Haiku): ONE call per paper on
  abstract + methods *residual* (what Stage 2 missed) → fill the ontology-constrained
  recipe schema. ~2k in / 0.5k out.
- **Pass B — data association** (only caption-gated figures + unmapped tables): tie each
  digitized curve/table to its conditions + measurand, normalized to the ontology.
- **Efficiency mechanisms:**
  - **Prompt caching** — the ontology vocabulary + schema block (~3k tokens) is identical
    for every paper → cache once, ~0.1× on hits (the dominant fixed cost vanishes).
  - **Batch API** — Pass A and most of Pass B are async → 50% cost.
  - **Tiered models** — Haiku for slot-filling; escalate to Sonnet only on low confidence.
  - **Constrained output** — strict JSON schema → small, consistent output tokens; the
    model slot-fills, it doesn't write prose.
  - **Confidence gating** — low-confidence rows → a review queue, not more tokens.

## Stage 4 — Normalize + resolve (NO LLM)
Existing 07/08 + s08 logic: units, families, transforms, recipe_role, dedup. Deterministic.

## Stage 5 — Ingest (incremental)
Manifest diff (download_log vs already-processed DOIs) → run the pipeline on **new** PDFs
only; per-DOI log; batch, reproducible.

---

## Token budget (order-of-magnitude)
| | naive (all papers, all figures) | this framework |
|---|---|---|
| papers sent to any LLM | 967 | ~250–400 (triaged) |
| figures digitized+LLM'd | ~8/paper × 967 ≈ 7700 | ~2–3 × 300 ≈ 800 (caption-gated) |
| fixed schema tokens/call | resent every call | cached (~0.1×) |
| model | one tier | Haiku bulk, Sonnet only on hard |
| API | sync | Batch (0.5×) for bulk |
| **rough total** | **~50–80 M tokens** | **~2–4 M tokens (~20×↓)**, higher precision |

## Why this is also *higher quality*, not just cheaper
- Ontology-constrained slot-filling → consistent, resolvable records (fewer of the
  molecular_mass(N) / cycle_sequence bugs we hit).
- Deterministic-first → the reproducible fields never depend on a stochastic model.
- Provenance + confidence on every value; a review queue for the genuine tail.
- Incremental + cached → re-runs are cheap, so the corpus can grow continuously.

## Build order
1. Stage 0 `scripts/00_triage.py` (runnable now, no LLM) — the gate.
2. Caption classifier + segment router (needs PDFs; after Step 2 download).
3. Rules library for Stage 2 (generalize methods_recipe.py).
4. Ontology-constrained Pass A/B prompts with caching + Batch API (needs LLM key).
5. Wire into `make ingest` (Step 5), incremental.
