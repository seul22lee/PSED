# Evaluating the ALD Knowledge Base

The KB is not the deliverable — **inference is**. A pile of well-typed records is
worthless if a researcher cannot use it to learn something the individual papers
never state. So evaluation tests two different things, and the second is the one
that matters.

- **Intrinsic** — is each record well-formed and faithful to its source?
- **Extrinsic** — does the *corpus* support reasoning *across* papers to produce
  knowledge no single paper contains?

Run: `python3 0706_pipeline/evaluate_kb.py` → prints the scorecard below on the
live resolved corpus.

## The five axes

| # | Axis | Question it answers | Metric |
|---|------|--------------------|--------|
| 1 | **Conformance** | machine-readable under the shared ontology+schema? | % analysis-ready |
| 2 | **Accuracy** | does each value match the source figure/caption? | grounding rate vs captions (`c1_accuracy`) |
| 3 | **Coverage** | complete, and where are the gaps? | recall vs full-text silver std; corpus fill-density + frontier gap list |
| 4 | **Consistency** | internally + cross-paper coherent? | derivation integrity; real cross-experiment spread (CV) |
| 5 | **Inference** | can it answer cross-record research questions? | competency battery: % answerable × correctness |

Axes 1–2 are per-record (intrinsic). Axes 3–5 are corpus-level (extrinsic) and
are the real test — they **rise as the corpus scales** and are near-meaningless at
n=1 paper.

## Data-quality flags (the skeptic's job)

An evaluator that only reports high scores is useless. The KB must actively flag
patterns that a domain scientist would distrust:

- **Broadcast constants** — a value repeated *identically* across many records is
  a *model input parameter* swept over a curve, **not** independent observations.
  Pooling it as a "consensus ± spread" is the single most common way automated
  meta-analysis lies. → flag any quantity with 1 distinct value over ≥10 records.
- **Circular consistency** — checking a value against the formula it was *derived
  from* (exposure ≡ P·t, when we computed it that way) proves the code ran, not
  the physics. Report it as *derivation integrity*, never as validation.
- **Model vs. measured** — meta-analysis (consensus, spread, outliers) is only
  valid over `relevance=experimental` records. Model outputs/inputs must be
  segregated. This is why "consensus GPC" is correctly reported *unanswerable*
  when the only Al₂O₃ GPC values are a model's input constant.

## The competency battery (what a researcher actually asks)

Each question requires reasoning across records; a value that appears verbatim in
one paper does not count. Current results (3-paper corpus):

| Question | Research move | Result |
|----------|--------------|--------|
| consensus GPC(Al₂O₃), experimental only | benchmark / reproducibility | *unanswerable* (only model-input GPC present — correctly refused) |
| penetration ∝ pulse_time^n | **infer growth regime** | **n = 0.64** (vs 0.5 diffusion-limited → reaction-limited contribution) |
| PD50 from a coverage-vs-depth profile | **infer conformality metric** not in paper | demonstrated (needs richer profiles for a trusted number) |
| biggest data gap | **guide next experiment** | "measure pulse_time for Al₂O₃" |
| reaction_probability range | model-parameter spread | *unanswerable* (single broadcast value — correctly refused) |
| materials with both model & experiment | **enable model-vs-data cross-validation** | Al₂O₃, SiO₂, TiO₂ |

## The researcher-analysis roadmap (why the KB exists)

Four moves, increasing in value. The KB's job is to make each *cheaper and
corpus-wide* than reading PDFs:

1. **Compare / benchmark** — same material across reactors/precursors/coreactants
   → reproducibility & inter-lab spread; thermal vs plasma effects. *Needs shared
   ontology-node alignment (have it).*
2. **Infer unstated quantities** — the high-value move:
   - **PD50 / half-penetration** from coverage-vs-depth curves (conformality metric).
   - **Saturation dose & effective s₀** by fitting GPC-vs-exposure (Langmuir).
   - **Growth-regime exponent** from penetration-vs-exposure log-log slope.
   - **ALD window** boundaries from pooled GPC-vs-T.
3. **Cross-validate models against independent experiments** — the KB co-represents
   *equations + parameters* (Ylilammi's model) and *measured profiles* (Arts). Ask:
   does model A reproduce experiment B? No single paper can. *This is the payoff of
   a model-aware KB.*
4. **Map the frontier** — the material × structure × condition matrix has holes.
   Empty cells = what to measure next. Meta-analysis outputs a **to-do list for the
   field**.

## Current scorecard (3 papers, 188 experiments)

```
conformance 100%   accuracy 96%   coverage 59%   consistency 100%   inference 67%   → overall 84%
```

The honest read: intrinsic quality is high; the corpus is dominated by one
conformality model (Ylilammi Al₂O₃), so coverage and inference are gated by
**scale and by experimental/model balance**, not by machinery. Priorities that
move the needle: (a) add experimental papers with GPC-vs-exposure/T to unlock
saturation & window inference; (b) extract per-value uncertainty (error bars) to
make cross-paper spread meaningful; (c) segregate model-input parameters from
measured outputs at extraction time so meta-analysis never conflates them.
